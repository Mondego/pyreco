__FILENAME__ = accesstests
#!/usr/bin/python

usage="""\
usage: %prog [options] filename

Unit tests for Microsoft Access

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

To run, pass the filename of an Access database on the command line:

  accesstests test.accdb

An empty Access 2000 database (empty.mdb) and an empty Access 2007 database
(empty.accdb), are provided.

To run a single test, use the -t option:

  accesstests test.accdb -t unicode_null

If you want to report an error, it would be helpful to include the driver information
by using the verbose flag and redirecting the output to a file:

 accesstests test.accdb -v >& results.txt

You can pass the verbose flag twice for more verbose output:

 accesstests test.accdb -vv
"""

# Access SQL data types: http://msdn2.microsoft.com/en-us/library/bb208866.aspx

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import abspath
from testutils import *

CNXNSTRING = None

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of composed of `seed` to make a string `length` characters long.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]


class AccessTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 254, 255 ] # text fields <= 255
    LARGE_FENCEPOST_SIZES = [ 256, 270, 304, 508, 510, 511, 512, 1023, 1024, 2047, 2048, 4000, 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ unicode(s) for s in ANSI_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name):
        unittest.TestCase.__init__(self, method_name)

    def setUp(self):
        self.cnxn   = pyodbc.connect(CNXNSTRING)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def _test_strtype(self, sqltype, value, resulttype=None, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value)), 'colsize=%s value=%s' % (colsize, (value is None) and 'none' or len(value))

        if colsize:
            sql = "create table t1(n1 int not null, s1 %s(%s), s2 %s(%s))" % (sqltype, colsize, sqltype, colsize)
        else:
            sql = "create table t1(n1 int not null, s1 %s, s2 %s)" % (sqltype, sqltype)

        if resulttype is None:
            # Access only uses Unicode, but strings might have been passed in to see if they can be written.  When we
            # read them back, they'll be unicode, so compare our results to a Unicode version of `value`.
            if type(value) is str:
                resulttype = unicode
            else:
                resulttype = type(value)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(1, ?, ?)", (value, value))
        v = self.cursor.execute("select s1, s2 from t1").fetchone()[0]
        
        if type(value) is not resulttype:
            # To allow buffer --> db --> bytearray tests, always convert the input to the expected result type before
            # comparing.
            value = resulttype(value)

        self.assertEqual(type(v), resulttype)

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

    #
    # unicode
    #

    def test_unicode_null(self):
        self._test_strtype('varchar', None, colsize=255)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, colsize=len(value))
        t.__doc__ = 'unicode %s' % len(value)
        return t
    for value in UNICODE_FENCEPOSTS:
        locals()['test_unicode_%s' % len(value)] = _maketest(value)

    #
    # ansi -> varchar
    #

    # Access only stores Unicode text but it should accept ASCII text.

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, colsize=len(value))
        t.__doc__ = 'ansi %s' % len(value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_ansivarchar_%s' % len(value)] = _maketest(value)

    #
    # binary
    #

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), colsize=len(value), resulttype=pyodbc.BINARY)
        t.__doc__ = 'binary %s' % len(value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_binary_%s' % len(value)] = _maketest(value)


    #
    # image
    #

    def test_null_image(self):
        self._test_strtype('image', None)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('image', buffer(value), resulttype=pyodbc.BINARY)
        t.__doc__ = 'image %s' % len(value)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_image_%s' % len(value)] = _maketest(value)

    #
    # memo
    #

    def test_null_memo(self):
        self._test_strtype('memo', None)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('memo', unicode(value))
        t.__doc__ = 'Unicode to memo %s' % len(value)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_memo_%s' % len(value)] = _maketest(value)

    # ansi -> memo
    def _maketest(value):
        def t(self):
            self._test_strtype('memo', value)
        t.__doc__ = 'ANSI to memo %s' % len(value)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_ansimemo_%s' % len(value)] = _maketest(value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)


    def test_unicode_query(self):
        self.cursor.execute(u"select 1")
        
    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(value, result)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_smallint(self):
        value = 32767
        self.cursor.execute("create table t1(n smallint)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_real(self):
        value = 1234.5
        self.cursor.execute("create table t1(n real)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_real(self):
        value = -200.5
        self.cursor.execute("create table t1(n real)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200.5
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)

    def test_tinyint(self):
        self.cursor.execute("create table t1(n tinyint)")
        value = 10
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(type(result), type(value))
        self.assertEqual(value, result)

    #
    # decimal & money
    #

    def test_decimal(self):
        value = Decimal('12345.6789')
        self.cursor.execute("create table t1(n numeric(10,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)

    def test_money(self):
        self.cursor.execute("create table t1(n money)")
        value = Decimal('1234.45')
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(type(result), type(value))
        self.assertEqual(value, result)

    def test_negative_decimal_scale(self):
        value = Decimal('-10.0010')
        self.cursor.execute("create table t1(d numeric(19,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)

    #
    # bit
    #

    def test_bit(self):
        self.cursor.execute("create table t1(b bit)")

        value = True
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(result), bool)
        self.assertEqual(value, result)

    def test_bit_null(self):
        self.cursor.execute("create table t1(b bit)")

        value = None
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(result), bool)
        self.assertEqual(False, result)

    def test_guid(self):
        # REVIEW: Python doesn't (yet) have a UUID type so the value is returned as a string.  Access, however, only
        # really supports Unicode.  For now, we'll have to live with this difference.  All strings in Python 3.x will
        # be Unicode -- pyodbc 3.x will have different defaults.
        value = "de2ac9c6-8676-4b0b-b8a6-217a8580cbee"
        self.cursor.execute("create table t1(g1 uniqueidentifier)")
        self.cursor.execute("insert into t1 values (?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))
        self.assertEqual(len(v), len(value))


    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount, but SQL Server 2005 returns -1 after a
        select statement, so we'll test for that behavior.  This is valid behavior according to the DB API
        specification, but people don't seem to like it.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, -1)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, -1)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, -1)

    #
    # Misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_concatenation(self):
        v2 = u'0123456789' * 25
        v3 = u'9876543210' * 25
        value = v2 + 'x' + v3

        self.cursor.execute("create table t1(c2 varchar(250), c3 varchar(250))")
        self.cursor.execute("insert into t1(c2, c3) values (?,?)", v2, v3)

        row = self.cursor.execute("select c2 + 'x' + c3 from t1").fetchone()

        self.assertEqual(row[0], value)


    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(CNXNSTRING, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('dbfile argument required')

    if args[0].endswith('.accdb'):
        driver = 'Microsoft Access Driver (*.mdb, *.accdb)'
    else:
        driver = 'Microsoft Access Driver (*.mdb)'

    global CNXNSTRING
    CNXNSTRING = 'DRIVER={%s};DBQ=%s;ExtendedAnsiSQL=1' % (driver, abspath(args[0]))

    cnxn = pyodbc.connect(CNXNSTRING)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(AccessTestCase, options.test)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.
    add_to_path()
    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = dbapi20
#!/usr/bin/env python
''' Python DB API 2.0 driver compliance unit test suite. 
    
    This software is Public Domain and may be used without restrictions.

 "Now we have booze and barflies entering the discussion, plus rumours of
  DBAs on drugs... and I won't tell you what flashes through my mind each
  time I read the subject line with 'Anal Compliance' in it.  All around
  this is turning out to be a thoroughly unwholesome unit test."

    -- Ian Bicking
'''

__rcs_id__  = '$Id: dbapi20.py,v 1.10 2003/10/09 03:14:14 zenzen Exp $'
__version__ = '$Revision: 1.10 $'[11:-2]
__author__ = 'Stuart Bishop <zen@shangri-la.dropbear.id.au>'

import unittest
import time

# $Log: dbapi20.py,v $
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that cursor.arraysize
# defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception heirarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#

class DatabaseAPI20Test(unittest.TestCase):
    ''' Test a database self.driver for DB API 2.0 compatibility.
        This implementation tests Gadfly, but the TestCase
        is structured so that other self.drivers can subclass this 
        test case to ensure compiliance with the DB-API. It is 
        expected that this TestCase may be expanded in the future
        if ambiguities or edge conditions are discovered.

        The 'Optional Extensions' are not yet being tested.

        self.drivers should subclass this test, overriding setUp, tearDown,
        self.driver, connect_args and connect_kw_args. Class specification
        should be as follows:

        import dbapi20 
        class mytest(dbapi20.DatabaseAPI20Test):
           [...] 

        Don't 'import DatabaseAPI20Test from dbapi20', or you will
        confuse the unit tester - just 'import dbapi20'.
    '''

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = () # List of arguments to pass to connect
    connect_kw_args = {} # Keyword arguments for connect
    table_prefix = 'dbapi20test_' # If you need to specify a prefix for tables

    ddl1 = 'create table %sbooze (name varchar(20))' % table_prefix
    ddl2 = 'create table %sbarflys (name varchar(20))' % table_prefix
    xddl1 = 'drop table %sbooze' % table_prefix
    xddl2 = 'drop table %sbarflys' % table_prefix

    lowerfunc = 'lower' # Name of stored procedure to convert string->lowercase
        
    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self,cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self,cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        ''' self.drivers should override this method to perform required setup
            if any is necessary, such as creating the database.
        '''
        pass

    def tearDown(self):
        ''' self.drivers should override this method to perform required cleanup
            if any is necessary, such as deleting the test database.
            The default drops the tables that may be created.
        '''
        con = self._connect()
        try:
            cur = con.cursor()
            for i, ddl in enumerate((self.xddl1,self.xddl2)):
                try: 
                    cur.execute(ddl)
                    con.commit()
                except self.driver.Error: 
                    # Assume table didn't exist. Other tests will check if
                    # execute is busted.
                    pass
        finally:
            con.close()

    def _connect(self):
        try:
            return self.driver.connect(
                *self.connect_args,**self.connect_kw_args
                )
        except AttributeError:
            self.fail("No connect method found in self.driver module")

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel,'2.0')
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.failUnless(threadsafety in (0,1,2,3))
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.failUnless(paramstyle in (
                'qmark','numeric','named','format','pyformat'
                ))
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        self.failUnless(issubclass(self.driver.Warning,StandardError))
        self.failUnless(issubclass(self.driver.Error,StandardError))
        self.failUnless(
            issubclass(self.driver.InterfaceError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.DatabaseError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.OperationalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.IntegrityError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.InternalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.ProgrammingError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.NotSupportedError,self.driver.Error)
            )

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        con = self._connect()
        drv = self.driver
        self.failUnless(con.Warning is drv.Warning)
        self.failUnless(con.Error is drv.Error)
        self.failUnless(con.InterfaceError is drv.InterfaceError)
        self.failUnless(con.DatabaseError is drv.DatabaseError)
        self.failUnless(con.OperationalError is drv.OperationalError)
        self.failUnless(con.IntegrityError is drv.IntegrityError)
        self.failUnless(con.InternalError is drv.InternalError)
        self.failUnless(con.ProgrammingError is drv.ProgrammingError)
        self.failUnless(con.NotSupportedError is drv.NotSupportedError)


    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con,'rollback'):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass
    
    def test_cursor(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze),1)
            self.assertEqual(len(booze[0]),1)
            self.assertEqual(booze[0][0],'Victoria Bitter')
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.description,None,
                'cursor.description should be none after executing a '
                'statement that can return no rows (such as DDL)'
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(len(cur.description),1,
                'cursor.description describes too many columns'
                )
            self.assertEqual(len(cur.description[0]),7,
                'cursor.description[x] tuples must have 7 elements'
                )
            self.assertEqual(cur.description[0][0].lower(),'name',
                'cursor.description[x][0] must return column name'
                )
            self.assertEqual(cur.description[0][1],self.driver.STRING,
                'cursor.description[x][1] must return column type. Got %r'
                    % cur.description[0][1]
                )

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(cur.description,None,
                'cursor.description not being set to None when executing '
                'no-result statements (eg. DDL)'
                )
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount should be -1 after executing no-result '
                'statements'
                )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement'
                )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount not being reset to -1 after executing '
                'no-result statements'
                )
        finally:
            con.close()

    lower_func = 'lower'
    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur,'callproc'):
                r = cur.callproc(self.lower_func,('FOO',))
                self.assertEqual(len(r),1)
                self.assertEqual(r[0],'FOO')
                r = cur.fetchall()
                self.assertEqual(len(r),1,'callproc produced no result set')
                self.assertEqual(len(r[0]),1,
                    'callproc produced invalid result set'
                    )
                self.assertEqual(r[0][0],'foo',
                    'callproc produced invalid results'
                    )
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error,self.executeDDL1,cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error,con.commit)

        # connection.close should raise an Error if called more than once
        self.assertRaises(self.driver.Error,con.close)

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self,cur):
        self.executeDDL1(cur)
        cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
            self.table_prefix
            ))
        self.failUnless(cur.rowcount in (-1,1))

        if self.driver.paramstyle == 'qmark':
            cur.execute(
                'insert into %sbooze values (?)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'numeric':
            cur.execute(
                'insert into %sbooze values (:1)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'named':
            cur.execute(
                'insert into %sbooze values (:beer)' % self.table_prefix, 
                {'beer':"Cooper's"}
                )
        elif self.driver.paramstyle == 'format':
            cur.execute(
                'insert into %sbooze values (%%s)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'pyformat':
            cur.execute(
                'insert into %sbooze values (%%(beer)s)' % self.table_prefix,
                {'beer':"Cooper's"}
                )
        else:
            self.fail('Invalid paramstyle')
        self.failUnless(cur.rowcount in (-1,1))

        cur.execute('select name from %sbooze' % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(len(res),2,'cursor.fetchall returned too few rows')
        beers = [res[0][0],res[1][0]]
        beers.sort()
        self.assertEqual(beers[0],"Cooper's",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )
        self.assertEqual(beers[1],"Victoria Bitter",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [ ("Cooper's",) , ("Boag's",) ]
            margs = [ {'beer': "Cooper's"}, {'beer': "Boag's"} ]
            if self.driver.paramstyle == 'qmark':
                cur.executemany(
                    'insert into %sbooze values (?)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'numeric':
                cur.executemany(
                    'insert into %sbooze values (:1)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'named':
                cur.executemany(
                    'insert into %sbooze values (:beer)' % self.table_prefix,
                    margs
                    )
            elif self.driver.paramstyle == 'format':
                cur.executemany(
                    'insert into %sbooze values (%%s)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'pyformat':
                cur.executemany(
                    'insert into %sbooze values (%%(beer)s)' % (
                        self.table_prefix
                        ),
                    margs
                    )
            else:
                self.fail('Unknown paramstyle')
            self.failUnless(cur.rowcount in (-1,2),
                'insert using cursor.executemany set cursor.rowcount to '
                'incorrect value %r' % cur.rowcount
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(len(res),2,
                'cursor.fetchall retrieved incorrect number of rows'
                )
            beers = [res[0][0],res[1][0]]
            beers.sort()
            self.assertEqual(beers[0],"Boag's",'incorrect data retrieved')
            self.assertEqual(beers[1],"Cooper's",'incorrect data retrieved')
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error,cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if no more rows available'
                )
            self.failUnless(cur.rowcount in (-1,1))
        finally:
            con.close()

    samples = [
        'Carlton Cold',
        'Carlton Draft',
        'Mountain Goat',
        'Redback',
        'Victoria Bitter',
        'XXXX'
        ]

    def _populate(self):
        ''' Return a list of sql commands to setup the DB for the fetch
            tests.
        '''
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix,s) 
                for s in self.samples
            ]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            #issuing a query
            self.assertRaises(self.driver.Error,cur.fetchmany,4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(len(r),1,
                'cursor.fetchmany retrieved incorrect number of rows, '
                'default of arraysize is one.'
                )
            cur.arraysize=10
            r = cur.fetchmany(3) # Should get 3 rows
            self.assertEqual(len(r),3,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should get 2 more
            self.assertEqual(len(r),2,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should be an empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence after '
                'results are exhausted'
            )
            self.failUnless(cur.rowcount in (-1,6))

            # Same as above, using cursor.arraysize
            cur.arraysize=4
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany() # Should get 4 rows
            self.assertEqual(len(r),4,
                'cursor.arraysize not being honoured by fetchmany'
                )
            r = cur.fetchmany() # Should get 2 more
            self.assertEqual(len(r),2)
            r = cur.fetchmany() # Should be an empty sequence
            self.assertEqual(len(r),0)
            self.failUnless(cur.rowcount in (-1,6))

            cur.arraysize=6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany() # Should get all rows
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows),6)
            self.assertEqual(len(rows),6)
            rows = [r[0] for r in rows]
            rows.sort()
          
            # Make sure we get the right data back out
            for i in range(0,6):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved by cursor.fetchmany'
                    )

            rows = cur.fetchmany() # Should return an empty list
            self.assertEqual(len(rows),0,
                'cursor.fetchmany should return an empty sequence if '
                'called after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,6))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany() # Should get empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,len(self.samples)))
            self.assertEqual(len(rows),len(self.samples),
                'cursor.fetchall did not retrieve all rows'
                )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                'cursor.fetchall retrieved incorrect rows'
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )
            
        finally:
            con.close()
    
    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows1  = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4  = cur.fetchone()
            rows56 = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows23),2,
                'fetchmany returned incorrect number of rows'
                )
            self.assertEqual(len(rows56),2,
                'fetchall returned incorrect number of rows'
                )

            rows = [rows1[0]]
            rows.extend([rows23[0][0],rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0],rows56[1][0]])
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved or inserted'
                    )
        finally:
            con.close()

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the 
	    number of rows in booze then "name from booze"
        '''
        raise NotImplementedError,'Helper not implemented'
        #sql="""
        #    create procedure deleteme as
        #    begin
        #        select count(*) from booze
        #        select name from booze
        #    end
        #"""
        #cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        raise NotImplementedError,'Helper not implemented'
        #cur.execute("drop procedure deleteme")

    def test_nextset(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur,'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql=self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows=cur.fetchone()
                assert numberofrows[0]== len(self.samples)
                assert cur.nextset()
                names=cur.fetchall()
                assert len(names) == len(self.samples)
                s=cur.nextset()
                assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    def test_nextset(self):
        raise NotImplementedError,'Drivers need to override this test'

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.failUnless(hasattr(cur,'arraysize'),
                'cursor.arraysize must be defined'
                )
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes( (25,) )
            self._paraminsert(cur) # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000,0)
            self._paraminsert(cur) # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError,'Driver need to override this test'

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute('insert into %sbooze values (NULL)' % self.table_prefix)
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r),1)
            self.assertEqual(len(r[0]),1)
            self.assertEqual(r[0][0],None,'NULL value not returned as None')
        finally:
            con.close()

    def test_Date(self):
        d1 = self.driver.Date(2002,12,25)
        d2 = self.driver.DateFromTicks(time.mktime((2002,12,25,0,0,0,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        t1 = self.driver.Time(13,45,30)
        t2 = self.driver.TimeFromTicks(time.mktime((2001,1,1,13,45,30,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        t1 = self.driver.Timestamp(2002,12,25,13,45,30)
        t2 = self.driver.TimestampFromTicks(
            time.mktime((2002,12,25,13,45,30,0,0,0))
            )
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        b = self.driver.Binary('Something')
        b = self.driver.Binary('')

    def test_STRING(self):
        self.failUnless(hasattr(self.driver,'STRING'),
            'module.STRING must be defined'
            )

    def test_BINARY(self):
        self.failUnless(hasattr(self.driver,'BINARY'),
            'module.BINARY must be defined.'
            )

    def test_NUMBER(self):
        self.failUnless(hasattr(self.driver,'NUMBER'),
            'module.NUMBER must be defined.'
            )

    def test_DATETIME(self):
        self.failUnless(hasattr(self.driver,'DATETIME'),
            'module.DATETIME must be defined.'
            )

    def test_ROWID(self):
        self.failUnless(hasattr(self.driver,'ROWID'),
            'module.ROWID must be defined.'
            )


########NEW FILE########
__FILENAME__ = dbapitests

import unittest
from testutils import *
import dbapi20

def main():
    add_to_path()
    import pyodbc

    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] connection_string")
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")

    (options, args) = parser.parse_args()
    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('dbapitests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    class test_pyodbc(dbapi20.DatabaseAPI20Test):
        driver = pyodbc
        connect_args = [ connection_string ]
        connect_kw_args = {}
    
        def test_nextset(self): pass
        def test_setoutputsize(self): pass
        def test_ExceptionsAsConnectionAttributes(self): pass
    
    suite = unittest.makeSuite(test_pyodbc, 'test')
    testRunner = unittest.TextTestRunner(verbosity=(options.verbose > 1) and 9 or 0)
    result = testRunner.run(suite)

if __name__ == '__main__':
    main()
    

########NEW FILE########
__FILENAME__ = exceltests
#!/usr/bin/python

# Tests for reading from Excel files.
#
# I have not been able to successfully create or modify Excel files.

import sys, os, re
import unittest
from os.path import abspath
from testutils import *

CNXNSTRING = None

class ExcelTestCase(unittest.TestCase):

    def __init__(self, method_name):
        unittest.TestCase.__init__(self, method_name)

    def setUp(self):
        self.cnxn   = pyodbc.connect(CNXNSTRING, autocommit=True)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))
     
    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))
     
    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))
     
    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))


    def test_read_sheet(self):
        # The first method of reading data is to access worksheets by name in this format [name$].
        #
        # Our second sheet is named Sheet2 and has two columns.  The first has values 10, 20, 30, etc.

        rows = self.cursor.execute("select * from [Sheet2$]").fetchall()
        self.assertEquals(len(rows), 5)

        for index, row in enumerate(rows):
            self.assertEquals(row.s2num, float(index + 1) * 10)

    def test_read_range(self):
        # The second method of reading data is to assign a name to a range of cells and access that as a table.
        #
        # Our first worksheet has a section named Table1.  The first column has values 1, 2, 3, etc.

        rows = self.cursor.execute("select * from Table1").fetchall()
        self.assertEquals(len(rows), 10)
     
        for index, row in enumerate(rows):
            self.assertEquals(row.num, float(index + 1))
            self.assertEquals(row.val, chr(ord('a') + index))

    def test_tables(self):
        # This is useful for figuring out what is available
        tables = [ row.table_name for row in self.cursor.tables() ]
        assert 'Sheet2$' in tables, 'tables: %s' % ' '.join(tables)


    # def test_append(self):
    #     rows = self.cursor.execute("select s2num, s2val from [Sheet2$]").fetchall()
    #  
    #     print rows
    #  
    #     nextnum = max([ row.s2num for row in rows ]) + 10
    #     
    #     self.cursor.execute("insert into [Sheet2$](s2num, s2val) values (?, 'z')", nextnum)
    #  
    #     row = self.cursor.execute("select s2num, s2val from [Sheet2$] where s2num=?", nextnum).fetchone()
    #     self.assertTrue(row)
    #  
    #     print 'added:', nextnum, len(rows), 'rows'
    #  
    #     self.assertEquals(row.s2num, nextnum)
    #     self.assertEquals(row.s2val, 'z')
    #  
    #     self.cnxn.commit()


def main():
    from optparse import OptionParser
    parser = OptionParser() #usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if args:
        parser.error('no arguments expected')
    
    global CNXNSTRING

    path = dirname(abspath(__file__))
    filename = join(path, 'test.xls')
    assert os.path.exists(filename)
    CNXNSTRING = 'Driver={Microsoft Excel Driver (*.xls)};DBQ=%s;READONLY=FALSE' % filename

    cnxn = pyodbc.connect(CNXNSTRING, autocommit=True)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(ExcelTestCase, options.test)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.
    add_to_path()
    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = freetdstests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for FreeTDS / SQL Server.  To use, pass a connection string as the parameter.
The tests will create and drop tables t1 and t2 as necessary.

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

You can also put the connection string into tmp/setup.cfg like so:

  [freetdstests]
  connection-string=DSN=xyz;UID=test;PWD=test
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class FreeTDSTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ unicode(s) for s in ANSI_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def get_sqlserver_version(self):
        """
        Returns the major version: 8-->2000, 9-->2005, 10-->2008
        """
        self.cursor.execute("exec master..xp_msver 'ProductVersion'")
        row = self.cursor.fetchone()
        return int(row.Character_Value.split('.', 1)[0])

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        for i in range(3):
            try:
                self.cursor.execute("drop procedure proc%d" % i)
                self.cnxn.commit()
            except:
                pass

        try:
            self.cursor.execute('drop function func1')
            self.cnxn.commit()
        except:
            pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_binary_type(self):
        if sys.hexversion >= 0x02060000:
            self.assertIs(pyodbc.BINARY, bytearray)
        else:
            self.assertIs(pyodbc.BINARY, buffer)

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def test_noscan(self):
        self.assertEqual(self.cursor.noscan, False)
        self.cursor.noscan = True
        self.assertEqual(self.cursor.noscan, True)

    def test_guid(self):
        self.cursor.execute("create table t1(g1 uniqueidentifier)")
        self.cursor.execute("insert into t1 values (newid())")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), 36)

    def test_nextset(self):
        self.cursor.execute("create table t1(i int)")
        for i in range(4):
            self.cursor.execute("insert into t1(i) values(?)", i)

        self.cursor.execute("select i from t1 where i < 2 order by i; select i from t1 where i >= 2 order by i")
        
        for i, row in enumerate(self.cursor):
            self.assertEqual(i, row.i)

        self.assertEqual(self.cursor.nextset(), True)

        for i, row in enumerate(self.cursor):
            self.assertEqual(i + 2, row.i)

    def test_fixed_unicode(self):
        value = u"t\xebsting"
        self.cursor.execute("create table t1(s nchar(7))")
        self.cursor.execute("insert into t1 values(?)", u"t\xebsting")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), unicode)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)


    def _test_strtype(self, sqltype, value, resulttype=None, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or isinstance(colsize, int), colsize
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        if resulttype is None:
            resulttype = type(value)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), resulttype)

        if value is not None:
            self.assertEqual(len(v), len(value))

        # To allow buffer --> db --> bytearray tests, always convert the input to the expected result type before
        # comparing.
        if type(value) is not resulttype:
            value = resulttype(value)

        self.assertEqual(v, value)


    def _test_strliketype(self, sqltype, value, resulttype=None, colsize=None):
        """
        The implementation for text, image, ntext, and binary.

        These types do not support comparison operators.
        """
        assert colsize is None or isinstance(colsize, int), colsize
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        if resulttype is None:
            resulttype = type(value)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), resulttype)

        if value is not None:
            self.assertEqual(len(v), len(value))

        # To allow buffer --> db --> bytearray tests, always convert the input to the expected result type before
        # comparing.
        if type(value) is not resulttype:
            value = resulttype(value)

        self.assertEqual(v, value)


    #
    # varchar
    #

    def test_varchar_null(self):
        self._test_strtype('varchar', None, colsize=100)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, colsize=len(value))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_varchar_%s' % len(value)] = _maketest(value)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3, len(c1) as l1, len(c2) as l2, len(c3) as l3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)

    def test_varchar_upperlatin(self):
        self._test_strtype('varchar', 'á')

    #
    # unicode
    #

    def test_unicode_null(self):
        self._test_strtype('nvarchar', None, colsize=100)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('nvarchar', value, colsize=len(value))
        return t
    for value in UNICODE_FENCEPOSTS:
        locals()['test_unicode_%s' % len(value)] = _maketest(value)

    def test_unicode_upperlatin(self):
        self._test_strtype('nvarchar', u'á')

    def test_unicode_longmax(self):
        # Issue 188:	Segfault when fetching NVARCHAR(MAX) data over 511 bytes

        ver = self.get_sqlserver_version()
        if ver < 9:            # 2005+
            return              # so pass / ignore
        self.cursor.execute("select cast(replicate(N'x', 512) as nvarchar(max))")

    def test_unicode_bind(self):
        value = u'test'
        v = self.cursor.execute("select ?", value).fetchone()[0]
        self.assertEqual(value, v)
        
    #
    # binary
    #

    def test_binary_null(self):
        # FreeTDS does not support SQLDescribeParam, so we must specifically tell it when we are inserting
        # a NULL into a binary column.
        self.cursor.execute("create table t1(n varbinary(10))")
        self.cursor.execute("insert into t1 values (?)", pyodbc.BinaryNull);

    # buffer

    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), resulttype=pyodbc.BINARY, colsize=len(value))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_binary_buffer_%s' % len(value)] = _maketest(value)

    # bytearray

    if sys.hexversion >= 0x02060000:
        def _maketest(value):
            def t(self):
                self._test_strtype('varbinary', bytearray(value), colsize=len(value))
            return t
        for value in ANSI_FENCEPOSTS:
            locals()['test_binary_bytearray_%s' % len(value)] = _maketest(value)

    #
    # image
    #

    def test_image_null(self):
        self._test_strliketype('image', None, type(None))

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('image', buffer(value), pyodbc.BINARY)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_image_buffer_%s' % len(value)] = _maketest(value)

    if sys.hexversion >= 0x02060000:
        # Python 2.6+ supports bytearray, which pyodbc considers varbinary.
        
        # Generate a test for each fencepost size: test_unicode_0, etc.
        def _maketest(value):
            def t(self):
                self._test_strtype('image', bytearray(value))
            return t
        for value in IMAGE_FENCEPOSTS:
            locals()['test_image_bytearray_%s' % len(value)] = _maketest(value)

    def test_image_upperlatin(self):
        self._test_strliketype('image', buffer('á'), pyodbc.BINARY)

    #
    # text
    #

    # def test_empty_text(self):
    #     self._test_strliketype('text', bytearray(''))

    def test_null_text(self):
        self._test_strliketype('text', None, type(None))

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('text', value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_text_buffer_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strliketype('text', 'á')

    #
    # bit
    #

    def test_bit(self):
        value = True
        self.cursor.execute("create table t1(b bit)")
        self.cursor.execute("insert into t1 values (?)", value)
        v = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(v), bool)
        self.assertEqual(v, value)

    #
    # decimal
    #

    def _decimal(self, precision, scale, negative):
        # From test provided by planders (thanks!) in Issue 91

        self.cursor.execute("create table t1(d decimal(%s, %s))" % (precision, scale))

        # Construct a decimal that uses the maximum precision and scale.
        decStr = '9' * (precision - scale)
        if scale:
            decStr = decStr + "." + '9' * scale
        if negative:
            decStr = "-" + decStr
        value = Decimal(decStr)

        self.cursor.execute("insert into t1 values(?)", value)

        v = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(v, value)

    def _maketest(p, s, n):
        def t(self):
            self._decimal(p, s, n)
        return t
    for (p, s, n) in [ (1,  0,  False),
                       (1,  0,  True),
                       (6,  0,  False),
                       (6,  2,  False),
                       (6,  4,  True),
                       (6,  6,  True),
                       (38, 0,  False),
                       (38, 10, False),
                       (38, 38, False),
                       (38, 0,  True),
                       (38, 10, True),
                       (38, 38, True) ]:
        locals()['test_decimal_%s_%s_%s' % (p, s, n and 'n' or 'p')] = _maketest(p, s, n)


    def test_decimal_e(self):
        """Ensure exponential notation decimals are properly handled"""
        value = Decimal((0, (1, 2, 3), 5)) # prints as 1.23E+7
        self.cursor.execute("create table t1(d decimal(10, 2))")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(result, value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_empty_unicode(self):
        self.cursor.execute("create table t1(s nvarchar(20))")
        self.cursor.execute("insert into t1 values(?)", u"")

    def test_unicode_query(self):
        self.cursor.execute(u"select 1")
        
    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    def test_datetime_fraction(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds, so the most granular datetime
        # supported is xxx000.

        value = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(result, value)

    def test_datetime_fraction_rounded(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds.  pyodbc rounds down to what the
        # database supports.

        full    = datetime(2007, 1, 15, 3, 4, 5, 123456)
        rounded = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", full)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(result), datetime)
        self.assertEquals(result, rounded)

    #
    # ints and floats
    #

    def test_int(self):
        # Issue 226: Failure if there is more than one int?
        value1 =  1234
        value2 = -1234
        self.cursor.execute("create table t1(n1 int, n2 int)")
        self.cursor.execute("insert into t1 values (?, ?)", value1, value2)
        row = self.cursor.execute("select n1, n2 from t1").fetchone()
        self.assertEquals(row.n1, value1)
        self.assertEquals(row.n2, value2)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):
        input = 3000000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    #
    # stored procedures
    #

    # def test_callproc(self):
    #     "callproc with a simple input-only stored procedure"
    #     pass

    def test_sp_results(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              select top 10 name, id, xtype, refdate
              from sysobjects
            """)
        rows = self.cursor.execute("exec proc1").fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_temp(self):

        # Note: I've used "set nocount on" so that we don't get the number of rows deleted from #tmptable.
        # If you don't do this, you'd need to call nextset() once to skip it.

        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              select top 10 name, id, xtype, refdate
              into #tmptable
              from sysobjects

              select * from #tmptable
            """)
        self.cursor.execute("exec proc1")
        self.assert_(self.cursor.description is not None)
        self.assert_(len(self.cursor.description) == 4)

        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_vartbl(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              declare @tmptbl table(name varchar(100), id int, xtype varchar(4), refdate datetime)

              insert into @tmptbl
              select top 10 name, id, xtype, refdate
              from sysobjects

              select * from @tmptbl
            """)
        self.cursor.execute("exec proc1")
        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)

    def test_sp_with_dates(self):
        # Reported in the forums that passing two datetimes to a stored procedure doesn't work.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@d1 datetime, @d2 datetime)
            AS
              declare @d as int
              set @d = datediff(year, @d1, @d2)
              select @d
            """)
        self.cursor.execute("exec test_sp ?, ?", datetime.now(), datetime.now())
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == 0)   # 0 years apart

    def test_sp_with_none(self):
        # Reported in the forums that passing None caused an error.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@x varchar(20))
            AS
              declare @y varchar(20)
              set @y = @x
              select @y
            """)
        self.cursor.execute("exec test_sp ?", None)
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == None)   # 0 years apart
        

    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount, but SQL Server 2005 returns -1 after a
        select statement, so we'll test for that behavior.  This is valid behavior according to the DB API
        specification, but people don't seem to like it.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, -1)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, -1)

    #
    # always return Cursor
    #

    # In the 2.0.x branch, Cursor.execute sometimes returned the cursor and sometimes the rowcount.  This proved very
    # confusing when things went wrong and added very little value even when things went right since users could always
    # use: cursor.execute("...").rowcount

    def test_retcursor_delete(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_select(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("select * from t1")
        self.assertEquals(v, self.cursor)

    #
    # misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()

        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_temp_select(self):
        # A project was failing to create temporary tables via select into.
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")

        self.cursor.execute("select s into t2 from t1")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")


    def test_money(self):
        d = Decimal('123456.78')
        self.cursor.execute("create table t1(i int identity(1,1), m money)")
        self.cursor.execute("insert into t1(m) values (?)", d)
        v = self.cursor.execute("select m from t1").fetchone()[0]
        self.assertEqual(v, d)


    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_concatenation(self):
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(300), c3 varchar(300))")
        self.cursor.execute("insert into t1(c2, c3) values (?,?)", v2, v3)

        row = self.cursor.execute("select c2, c3, c2 + c3 as both from t1").fetchone()

        self.assertEqual(row.both, v2 + v3)

    def test_view_select(self):
        # Reported in forum: Can't select from a view?  I think I do this a lot, but another test never hurts.

        # Create a table (t1) with 3 rows and a view (t2) into it.
        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(50))")
        for i in range(3):
            self.cursor.execute("insert into t1(c2) values (?)", "string%s" % i)
        self.cursor.execute("create view t2 as select * from t1")

        # Select from the view
        self.cursor.execute("select * from t2")
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(len(rows) == 3)

    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)

    def test_unicode_results(self):
        "Ensure unicode_results forces Unicode"
        othercnxn = pyodbc.connect(self.connection_string, unicode_results=True)
        othercursor = othercnxn.cursor()

        # ANSI data in an ANSI column ...
        othercursor.execute("create table t1(s varchar(20))")
        othercursor.execute("insert into t1 values(?)", 'test')

        # ... should be returned as Unicode
        value = othercursor.execute("select s from t1").fetchone()[0]
        self.assertEqual(value, u'test')


    def test_sqlserver_callproc(self):
        try:
            self.cursor.execute("drop procedure pyodbctest")
            self.cnxn.commit()
        except:
            pass

        self.cursor.execute("create table t1(s varchar(10))")
        self.cursor.execute("insert into t1 values(?)", "testing")

        self.cursor.execute("""
                            create procedure pyodbctest @var1 varchar(32)
                            as 
                            begin 
                              select s 
                              from t1 
                            return 
                            end
                            """)
        self.cnxn.commit()

        # for row in self.cursor.procedureColumns('pyodbctest'):
        #     print row.procedure_name, row.column_name, row.column_type, row.type_name

        self.cursor.execute("exec pyodbctest 'hi'")

        # print self.cursor.description
        # for row in self.cursor:
        #     print row.s

    def test_skip(self):
        # Insert 1, 2, and 3.  Fetch 1, skip 2, fetch 3.

        self.cursor.execute("create table t1(id int)");
        for i in range(1, 5):
            self.cursor.execute("insert into t1 values(?)", i)
        self.cursor.execute("select id from t1 order by id")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.cursor.skip(2)
        self.assertEqual(self.cursor.fetchone()[0], 4)

    def test_timeout(self):
        self.assertEqual(self.cnxn.timeout, 0) # defaults to zero (off)

        self.cnxn.timeout = 30
        self.assertEqual(self.cnxn.timeout, 30)

        self.cnxn.timeout = 0
        self.assertEqual(self.cnxn.timeout, 0)

    def test_sets_execute(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.execute("insert into t1 (word) VALUES (?)", [words])

        self.assertRaises(pyodbc.ProgrammingError, f)

    def test_sets_executemany(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.executemany("insert into t1 (word) values (?)", [words])
            
        self.assertRaises(TypeError, f)

    def test_row_execute(self):
        "Ensure we can use a Row object as a parameter to execute"
        self.cursor.execute("create table t1(n int, s varchar(10))")
        self.cursor.execute("insert into t1 values (1, 'a')")
        row = self.cursor.execute("select n, s from t1").fetchone()
        self.assertNotEqual(row, None)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.execute("insert into t2 values (?, ?)", row)
        
    def test_row_executemany(self):
        "Ensure we can use a Row object as a parameter to executemany"
        self.cursor.execute("create table t1(n int, s varchar(10))")

        for i in range(3):
            self.cursor.execute("insert into t1 values (?, ?)", i, chr(ord('a')+i))

        rows = self.cursor.execute("select n, s from t1").fetchall()
        self.assertNotEqual(len(rows), 0)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.executemany("insert into t2 values (?, ?)", rows)
        
    def test_description(self):
        "Ensure cursor.description is correct"

        self.cursor.execute("create table t1(n int, s varchar(8), d decimal(5,2))")
        self.cursor.execute("insert into t1 values (1, 'abc', '1.23')")
        self.cursor.execute("select * from t1")

        # (I'm not sure the precision of an int is constant across different versions, bits, so I'm hand checking the
        # items I do know.

        # int
        t = self.cursor.description[0]
        self.assertEqual(t[0], 'n')
        self.assertEqual(t[1], int)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # varchar(8)
        t = self.cursor.description[1]
        self.assertEqual(t[0], 's')
        self.assertEqual(t[1], str)
        self.assertEqual(t[4], 8)       # precision
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # decimal(5, 2)
        t = self.cursor.description[2]
        self.assertEqual(t[0], 'd')
        self.assertEqual(t[1], Decimal)
        self.assertEqual(t[4], 5)       # precision
        self.assertEqual(t[5], 2)       # scale
        self.assertEqual(t[6], True)    # nullable

        
    def test_none_param(self):
        "Ensure None can be used for params other than the first"
        # Some driver/db versions would fail if NULL was not the first parameter because SQLDescribeParam (only used
        # with NULL) could not be used after the first call to SQLBindParameter.  This means None always worked for the
        # first column, but did not work for later columns.
        #
        # If SQLDescribeParam doesn't work, pyodbc would use VARCHAR which almost always worked.  However,
        # binary/varbinary won't allow an implicit conversion.

        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'xyzzy')")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 1)
        self.assertEqual(type(row.s), str)

        self.cursor.execute("update t1 set n=?, s=?", 2, None)
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 2)
        self.assertEqual(row.s, None)


    def test_output_conversion(self):
        def convert(value):
            # `value` will be a string.  We'll simply add an X at the beginning at the end.
            return 'X' + value + 'X'
        self.cnxn.add_output_converter(pyodbc.SQL_VARCHAR, convert)
        self.cursor.execute("create table t1(n int, v varchar(10))")
        self.cursor.execute("insert into t1 values (1, '123.45')")
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, 'X123.45X')

        # Now clear the conversions and try again.  There should be no Xs this time.
        self.cnxn.clear_output_converters()
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, '123.45')


    def test_too_large(self):
        """Ensure error raised if insert fails due to truncation"""
        value = 'x' * 1000
        self.cursor.execute("create table t1(s varchar(800))")
        def test():
            self.cursor.execute("insert into t1 values (?)", value)
        self.assertRaises(pyodbc.DataError, test)

    def test_geometry_null_insert(self):
        def convert(value):
            return value

        self.cnxn.add_output_converter(-151, convert) # -151 is SQL Server's geometry
        self.cursor.execute("create table t1(n int, v geometry)")
        self.cursor.execute("insert into t1 values (?, ?)", 1, None)
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, None)
        self.cnxn.clear_output_converters()

    def test_login_timeout(self):
        # This can only test setting since there isn't a way to cause it to block on the server side.
        cnxns = pyodbc.connect(self.connection_string, timeout=2)

    def test_row_equal(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test')")
        row1 = self.cursor.execute("select n, s from t1").fetchone()
        row2 = self.cursor.execute("select n, s from t1").fetchone()
        b = (row1 == row2)
        self.assertEqual(b, True)

    def test_row_gtlt(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test1')")
        self.cursor.execute("insert into t1 values (1, 'test2')")
        rows = self.cursor.execute("select n, s from t1 order by s").fetchall()
        self.assert_(rows[0] < rows[1])
        self.assert_(rows[0] <= rows[1])
        self.assert_(rows[1] > rows[0])
        self.assert_(rows[1] >= rows[0])
        self.assert_(rows[0] != rows[1])

        rows = list(rows)
        rows.sort() # uses <
        
    def test_context_manager_success(self):

        self.cursor.execute("create table t1(n int)")
        self.cnxn.commit()

        try:
            with pyodbc.connect(self.connection_string) as cnxn:
                cursor = cnxn.cursor()
                cursor.execute("insert into t1 values (1)")
        except Exception:
            pass

        cnxn = None
        cursor = None

        rows = self.cursor.execute("select n from t1").fetchall()
        self.assertEquals(len(rows), 1)
        self.assertEquals(rows[0][0], 1)


    def test_untyped_none(self):
        # From issue 129
        value = self.cursor.execute("select ?", None).fetchone()[0]
        self.assertEqual(value, None)
        
    def test_large_update_nodata(self):
        self.cursor.execute('create table t1(a varbinary(max))')
        hundredkb = bytearray('x'*100*1024)
        self.cursor.execute('update t1 set a=? where 1=0', (hundredkb,))

    def test_func_param(self):
        self.cursor.execute('''
                            create function func1 (@testparam varchar(4)) 
                            returns @rettest table (param varchar(4))
                            as 
                            begin
                                insert @rettest
                                select @testparam
                                return
                            end
                            ''')
        self.cnxn.commit()
        value = self.cursor.execute("select * from func1(?)", 'test').fetchone()[0]
        self.assertEquals(value, 'test')
        
    def test_no_fetch(self):
        # Issue 89 with FreeTDS: Multiple selects (or catalog functions that issue selects) without fetches seem to
        # confuse the driver.
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')

def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('freetdstests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(FreeTDSTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = informixtests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for Informix DB.  To use, pass a connection string as the parameter.
The tests will create and drop tables t1 and t2 as necessary.

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

You can also put the connection string into a setup.cfg file in the root of the project
(the same one setup.py would use) like so:

  [informixtests]
  connection-string=DRIVER={IBM INFORMIX ODBC DRIVER (64-bit)};SERVER=localhost;UID=uid;PWD=pwd;DATABASE=db
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class InformixTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ unicode(s) for s in ANSI_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        for i in range(3):
            try:
                self.cursor.execute("drop procedure proc%d" % i)
                self.cnxn.commit()
            except:
                pass

        try:
            self.cursor.execute('drop function func1')
            self.cnxn.commit()
        except:
            pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def test_noscan(self):
        self.assertEqual(self.cursor.noscan, False)
        self.cursor.noscan = True
        self.assertEqual(self.cursor.noscan, True)

    def test_guid(self):
        self.cursor.execute("create table t1(g1 uniqueidentifier)")
        self.cursor.execute("insert into t1 values (newid())")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), 36)

    def test_nextset(self):
        self.cursor.execute("create table t1(i int)")
        for i in range(4):
            self.cursor.execute("insert into t1(i) values(?)", i)

        self.cursor.execute("select i from t1 where i < 2 order by i; select i from t1 where i >= 2 order by i")
        
        for i, row in enumerate(self.cursor):
            self.assertEqual(i, row.i)

        self.assertEqual(self.cursor.nextset(), True)

        for i, row in enumerate(self.cursor):
            self.assertEqual(i + 2, row.i)

    def test_fixed_unicode(self):
        value = u"t\xebsting"
        self.cursor.execute("create table t1(s nchar(7))")
        self.cursor.execute("insert into t1 values(?)", u"t\xebsting")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), unicode)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)


    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

        # Reported by Andy Hochhaus in the pyodbc group: In 2.1.7 and earlier, a hardcoded length of 255 was used to
        # determine whether a parameter was bound as a SQL_VARCHAR or SQL_LONGVARCHAR.  Apparently SQL Server chokes if
        # we bind as a SQL_LONGVARCHAR and the target column size is 8000 or less, which is considers just SQL_VARCHAR.
        # This means binding a 256 character value would cause problems if compared with a VARCHAR column under
        # 8001. We now use SQLGetTypeInfo to determine the time to switch.
        #
        # [42000] [Microsoft][SQL Server Native Client 10.0][SQL Server]The data types varchar and text are incompatible in the equal to operator.

        self.cursor.execute("select * from t1 where s=?", value)


    def _test_strliketype(self, sqltype, value, colsize=None):
        """
        The implementation for text, image, ntext, and binary.

        These types do not support comparison operators.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)


    #
    # varchar
    #

    def test_varchar_null(self):
        self._test_strtype('varchar', None, 100)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, len(value))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_varchar_%s' % len(value)] = _maketest(value)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3, len(c1) as l1, len(c2) as l2, len(c3) as l3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)

    def test_varchar_upperlatin(self):
        self._test_strtype('varchar', 'á')

    #
    # unicode
    #

    def test_unicode_null(self):
        self._test_strtype('nvarchar', None, 100)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('nvarchar', value, len(value))
        return t
    for value in UNICODE_FENCEPOSTS:
        locals()['test_unicode_%s' % len(value)] = _maketest(value)

    def test_unicode_upperlatin(self):
        self._test_strtype('varchar', 'á')

    #
    # binary
    #

    def test_null_binary(self):
        self._test_strtype('varbinary', None, 100)
     
    def test_large_null_binary(self):
        # Bug 1575064
        self._test_strtype('varbinary', None, 4000)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), len(value))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_binary_%s' % len(value)] = _maketest(value)

    #
    # image
    #

    def test_image_null(self):
        self._test_strliketype('image', None)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('image', buffer(value))
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_image_%s' % len(value)] = _maketest(value)

    def test_image_upperlatin(self):
        self._test_strliketype('image', buffer('á'))

    #
    # text
    #

    # def test_empty_text(self):
    #     self._test_strliketype('text', buffer(''))

    def test_null_text(self):
        self._test_strliketype('text', None)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('text', value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_text_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strliketype('text', 'á')

    #
    # bit
    #

    def test_bit(self):
        value = True
        self.cursor.execute("create table t1(b bit)")
        self.cursor.execute("insert into t1 values (?)", value)
        v = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(v), bool)
        self.assertEqual(v, value)

    #
    # decimal
    #

    def _decimal(self, precision, scale, negative):
        # From test provided by planders (thanks!) in Issue 91

        self.cursor.execute("create table t1(d decimal(%s, %s))" % (precision, scale))

        # Construct a decimal that uses the maximum precision and scale.
        decStr = '9' * (precision - scale)
        if scale:
            decStr = decStr + "." + '9' * scale
        if negative:
            decStr = "-" + decStr
        value = Decimal(decStr)

        self.cursor.execute("insert into t1 values(?)", value)

        v = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(v, value)

    def _maketest(p, s, n):
        def t(self):
            self._decimal(p, s, n)
        return t
    for (p, s, n) in [ (1,  0,  False),
                       (1,  0,  True),
                       (6,  0,  False),
                       (6,  2,  False),
                       (6,  4,  True),
                       (6,  6,  True),
                       (38, 0,  False),
                       (38, 10, False),
                       (38, 38, False),
                       (38, 0,  True),
                       (38, 10, True),
                       (38, 38, True) ]:
        locals()['test_decimal_%s_%s_%s' % (p, s, n and 'n' or 'p')] = _maketest(p, s, n)


    def test_decimal_e(self):
        """Ensure exponential notation decimals are properly handled"""
        value = Decimal((0, (1, 2, 3), 5)) # prints as 1.23E+7
        self.cursor.execute("create table t1(d decimal(10, 2))")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(result, value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_empty_unicode(self):
        self.cursor.execute("create table t1(s nvarchar(20))")
        self.cursor.execute("insert into t1 values(?)", u"")

    def test_unicode_query(self):
        self.cursor.execute(u"select 1")
        
    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    def test_datetime_fraction(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds, so the most granular datetime
        # supported is xxx000.

        value = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(result, value)

    def test_datetime_fraction_rounded(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds.  pyodbc rounds down to what the
        # database supports.

        full    = datetime(2007, 1, 15, 3, 4, 5, 123456)
        rounded = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", full)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(result), datetime)
        self.assertEquals(result, rounded)

    def test_date(self):
        value = date.today()
     
        self.cursor.execute("create table t1(d date)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEquals(type(value), date)
        self.assertEquals(value, result)

    def test_time(self):
        value = datetime.now().time()
        
        # We aren't yet writing values using the new extended time type so the value written to the database is only
        # down to the second.
        value = value.replace(microsecond=0)
         
        self.cursor.execute("create table t1(t time)")
        self.cursor.execute("insert into t1 values (?)", value)
         
        result = self.cursor.execute("select t from t1").fetchone()[0]
        self.assertEquals(type(value), time)
        self.assertEquals(value, result)

    def test_datetime2(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime2)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):
        input = 3000000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    #
    # stored procedures
    #

    # def test_callproc(self):
    #     "callproc with a simple input-only stored procedure"
    #     pass

    def test_sp_results(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              select top 10 name, id, xtype, refdate
              from sysobjects
            """)
        rows = self.cursor.execute("exec proc1").fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_temp(self):

        # Note: I've used "set nocount on" so that we don't get the number of rows deleted from #tmptable.
        # If you don't do this, you'd need to call nextset() once to skip it.

        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              select top 10 name, id, xtype, refdate
              into #tmptable
              from sysobjects

              select * from #tmptable
            """)
        self.cursor.execute("exec proc1")
        self.assert_(self.cursor.description is not None)
        self.assert_(len(self.cursor.description) == 4)

        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_vartbl(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              declare @tmptbl table(name varchar(100), id int, xtype varchar(4), refdate datetime)

              insert into @tmptbl
              select top 10 name, id, xtype, refdate
              from sysobjects

              select * from @tmptbl
            """)
        self.cursor.execute("exec proc1")
        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)

    def test_sp_with_dates(self):
        # Reported in the forums that passing two datetimes to a stored procedure doesn't work.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@d1 datetime, @d2 datetime)
            AS
              declare @d as int
              set @d = datediff(year, @d1, @d2)
              select @d
            """)
        self.cursor.execute("exec test_sp ?, ?", datetime.now(), datetime.now())
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == 0)   # 0 years apart

    def test_sp_with_none(self):
        # Reported in the forums that passing None caused an error.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@x varchar(20))
            AS
              declare @y varchar(20)
              set @y = @x
              select @y
            """)
        self.cursor.execute("exec test_sp ?", None)
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == None)   # 0 years apart
        

    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount, but SQL Server 2005 returns -1 after a
        select statement, so we'll test for that behavior.  This is valid behavior according to the DB API
        specification, but people don't seem to like it.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, -1)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, -1)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, -1)

    #
    # always return Cursor
    #

    # In the 2.0.x branch, Cursor.execute sometimes returned the cursor and sometimes the rowcount.  This proved very
    # confusing when things went wrong and added very little value even when things went right since users could always
    # use: cursor.execute("...").rowcount

    def test_retcursor_delete(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_select(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("select * from t1")
        self.assertEquals(v, self.cursor)

    #
    # misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()

        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_temp_select(self):
        # A project was failing to create temporary tables via select into.
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")

        self.cursor.execute("select s into t2 from t1")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")


    def test_money(self):
        d = Decimal('123456.78')
        self.cursor.execute("create table t1(i int identity(1,1), m money)")
        self.cursor.execute("insert into t1(m) values (?)", d)
        v = self.cursor.execute("select m from t1").fetchone()[0]
        self.assertEqual(v, d)


    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_concatenation(self):
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(300), c3 varchar(300))")
        self.cursor.execute("insert into t1(c2, c3) values (?,?)", v2, v3)

        row = self.cursor.execute("select c2, c3, c2 + c3 as both from t1").fetchone()

        self.assertEqual(row.both, v2 + v3)

    def test_view_select(self):
        # Reported in forum: Can't select from a view?  I think I do this a lot, but another test never hurts.

        # Create a table (t1) with 3 rows and a view (t2) into it.
        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(50))")
        for i in range(3):
            self.cursor.execute("insert into t1(c2) values (?)", "string%s" % i)
        self.cursor.execute("create view t2 as select * from t1")

        # Select from the view
        self.cursor.execute("select * from t2")
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(len(rows) == 3)

    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)

    def test_unicode_results(self):
        "Ensure unicode_results forces Unicode"
        othercnxn = pyodbc.connect(self.connection_string, unicode_results=True)
        othercursor = othercnxn.cursor()

        # ANSI data in an ANSI column ...
        othercursor.execute("create table t1(s varchar(20))")
        othercursor.execute("insert into t1 values(?)", 'test')

        # ... should be returned as Unicode
        value = othercursor.execute("select s from t1").fetchone()[0]
        self.assertEqual(value, u'test')


    def test_informix_callproc(self):
        try:
            self.cursor.execute("drop procedure pyodbctest")
            self.cnxn.commit()
        except:
            pass

        self.cursor.execute("create table t1(s varchar(10))")
        self.cursor.execute("insert into t1 values(?)", "testing")

        self.cursor.execute("""
                            create procedure pyodbctest @var1 varchar(32)
                            as 
                            begin 
                              select s 
                              from t1 
                            return 
                            end
                            """)
        self.cnxn.commit()

        # for row in self.cursor.procedureColumns('pyodbctest'):
        #     print row.procedure_name, row.column_name, row.column_type, row.type_name

        self.cursor.execute("exec pyodbctest 'hi'")

        # print self.cursor.description
        # for row in self.cursor:
        #     print row.s

    def test_skip(self):
        # Insert 1, 2, and 3.  Fetch 1, skip 2, fetch 3.

        self.cursor.execute("create table t1(id int)");
        for i in range(1, 5):
            self.cursor.execute("insert into t1 values(?)", i)
        self.cursor.execute("select id from t1 order by id")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.cursor.skip(2)
        self.assertEqual(self.cursor.fetchone()[0], 4)

    def test_timeout(self):
        self.assertEqual(self.cnxn.timeout, 0) # defaults to zero (off)

        self.cnxn.timeout = 30
        self.assertEqual(self.cnxn.timeout, 30)

        self.cnxn.timeout = 0
        self.assertEqual(self.cnxn.timeout, 0)

    def test_sets_execute(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.execute("insert into t1 (word) VALUES (?)", [words])

        self.assertRaises(pyodbc.ProgrammingError, f)

    def test_sets_executemany(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.executemany("insert into t1 (word) values (?)", [words])
            
        self.assertRaises(TypeError, f)

    def test_row_execute(self):
        "Ensure we can use a Row object as a parameter to execute"
        self.cursor.execute("create table t1(n int, s varchar(10))")
        self.cursor.execute("insert into t1 values (1, 'a')")
        row = self.cursor.execute("select n, s from t1").fetchone()
        self.assertNotEqual(row, None)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.execute("insert into t2 values (?, ?)", row)
        
    def test_row_executemany(self):
        "Ensure we can use a Row object as a parameter to executemany"
        self.cursor.execute("create table t1(n int, s varchar(10))")

        for i in range(3):
            self.cursor.execute("insert into t1 values (?, ?)", i, chr(ord('a')+i))

        rows = self.cursor.execute("select n, s from t1").fetchall()
        self.assertNotEqual(len(rows), 0)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.executemany("insert into t2 values (?, ?)", rows)
        
    def test_description(self):
        "Ensure cursor.description is correct"

        self.cursor.execute("create table t1(n int, s varchar(8), d decimal(5,2))")
        self.cursor.execute("insert into t1 values (1, 'abc', '1.23')")
        self.cursor.execute("select * from t1")

        # (I'm not sure the precision of an int is constant across different versions, bits, so I'm hand checking the
        # items I do know.

        # int
        t = self.cursor.description[0]
        self.assertEqual(t[0], 'n')
        self.assertEqual(t[1], int)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # varchar(8)
        t = self.cursor.description[1]
        self.assertEqual(t[0], 's')
        self.assertEqual(t[1], str)
        self.assertEqual(t[4], 8)       # precision
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # decimal(5, 2)
        t = self.cursor.description[2]
        self.assertEqual(t[0], 'd')
        self.assertEqual(t[1], Decimal)
        self.assertEqual(t[4], 5)       # precision
        self.assertEqual(t[5], 2)       # scale
        self.assertEqual(t[6], True)    # nullable

        
    def test_none_param(self):
        "Ensure None can be used for params other than the first"
        # Some driver/db versions would fail if NULL was not the first parameter because SQLDescribeParam (only used
        # with NULL) could not be used after the first call to SQLBindParameter.  This means None always worked for the
        # first column, but did not work for later columns.
        #
        # If SQLDescribeParam doesn't work, pyodbc would use VARCHAR which almost always worked.  However,
        # binary/varbinary won't allow an implicit conversion.

        self.cursor.execute("create table t1(n int, blob varbinary(max))")
        self.cursor.execute("insert into t1 values (1, newid())")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 1)
        self.assertEqual(type(row.blob), buffer)

        self.cursor.execute("update t1 set n=?, blob=?", 2, None)
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 2)
        self.assertEqual(row.blob, None)


    def test_output_conversion(self):
        def convert(value):
            # `value` will be a string.  We'll simply add an X at the beginning at the end.
            return 'X' + value + 'X'
        self.cnxn.add_output_converter(pyodbc.SQL_VARCHAR, convert)
        self.cursor.execute("create table t1(n int, v varchar(10))")
        self.cursor.execute("insert into t1 values (1, '123.45')")
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, 'X123.45X')

        # Now clear the conversions and try again.  There should be no Xs this time.
        self.cnxn.clear_output_converters()
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, '123.45')


    def test_too_large(self):
        """Ensure error raised if insert fails due to truncation"""
        value = 'x' * 1000
        self.cursor.execute("create table t1(s varchar(800))")
        def test():
            self.cursor.execute("insert into t1 values (?)", value)
        self.assertRaises(pyodbc.DataError, test)

    def test_geometry_null_insert(self):
        def convert(value):
            return value

        self.cnxn.add_output_converter(-151, convert) # -151 is SQL Server's geometry
        self.cursor.execute("create table t1(n int, v geometry)")
        self.cursor.execute("insert into t1 values (?, ?)", 1, None)
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, None)
        self.cnxn.clear_output_converters()

    def test_login_timeout(self):
        # This can only test setting since there isn't a way to cause it to block on the server side.
        cnxns = pyodbc.connect(self.connection_string, timeout=2)

    def test_row_equal(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test')")
        row1 = self.cursor.execute("select n, s from t1").fetchone()
        row2 = self.cursor.execute("select n, s from t1").fetchone()
        b = (row1 == row2)
        self.assertEqual(b, True)

    def test_row_gtlt(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test1')")
        self.cursor.execute("insert into t1 values (1, 'test2')")
        rows = self.cursor.execute("select n, s from t1 order by s").fetchall()
        self.assert_(rows[0] < rows[1])
        self.assert_(rows[0] <= rows[1])
        self.assert_(rows[1] > rows[0])
        self.assert_(rows[1] >= rows[0])
        self.assert_(rows[0] != rows[1])

        rows = list(rows)
        rows.sort() # uses <
        
    def test_context_manager(self):
        with pyodbc.connect(self.connection_string) as cnxn:
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)

        # The connection should be closed now.
        def test():
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assertRaises(pyodbc.ProgrammingError, test)

    def test_untyped_none(self):
        # From issue 129
        value = self.cursor.execute("select ?", None).fetchone()[0]
        self.assertEqual(value, None)
        
    def test_large_update_nodata(self):
        self.cursor.execute('create table t1(a varbinary(max))')
        hundredkb = buffer('x'*100*1024)
        self.cursor.execute('update t1 set a=? where 1=0', (hundredkb,))

    def test_func_param(self):
        self.cursor.execute('''
                            create function func1 (@testparam varchar(4)) 
                            returns @rettest table (param varchar(4))
                            as 
                            begin
                                insert @rettest
                                select @testparam
                                return
                            end
                            ''')
        self.cnxn.commit()
        value = self.cursor.execute("select * from func1(?)", 'test').fetchone()[0]
        self.assertEquals(value, 'test')
        
    def test_no_fetch(self):
        # Issue 89 with FreeTDS: Multiple selects (or catalog functions that issue selects) without fetches seem to
        # confuse the driver.
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')

    def test_drivers(self):
        drivers = pyodbc.drivers()
        self.assertEqual(list, type(drivers))
        self.assert_(len(drivers) > 1)

        m = re.search('DRIVER={([^}]+)}', self.connection_string, re.IGNORECASE)
        current = m.group(1)
        self.assert_(current in drivers)
            
    def test_prepare_cleanup(self):
        # When statement is prepared, it is kept in case the next execute uses the same statement.  This must be
        # removed when a non-execute statement is used that returns results, such as SQLTables.

        self.cursor.execute("select top 1 name from sysobjects where name = ?", "bogus")
        self.cursor.fetchone()

        self.cursor.tables("bogus")
        
        self.cursor.execute("select top 1 name from sysobjects where name = ?", "bogus")
        self.cursor.fetchone()


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('informixtests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(InformixTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = mysqltests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for MySQL.  To use, pass a connection string as the parameter.  The tests will create and drop tables t1 and
t2 as necessary.  The default installation of mysql allows you to connect locally with no password and already contains
a 'test' database, so you can probably use the following.  (Update the driver name as appropriate.)

  ./mysqltests DRIVER={MySQL};DATABASE=test

These tests use the pyodbc library from the build directory, not the version installed in your
Python directories.  You must run `python setup.py build` before running these tests.
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath, basename
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of composed of `seed` to make a string `length` characters long.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class MySqlTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ unicode(s) for s in ANSI_FENCEPOSTS ]
    BLOB_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        for i in range(3):
            try:
                self.cursor.execute("drop procedure proc%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        try:
            self.cursor.execute(sql)
        except:
            print '>>>>', sql
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]

        # Removing this check for now until I get the charset working properly.
        # If we use latin1, results are 'str' instead of 'unicode', which would be
        # correct.  Setting charset to ucs-2 causes a crash in SQLGetTypeInfo(SQL_DATETIME).
        # self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

    #
    # varchar
    #

    def test_varchar_null(self):
        self._test_strtype('varchar', None, 100)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, max(1, len(value)))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_varchar_%s' % len(value)] = _maketest(value)

    # Generate a test using Unicode.
    for value in UNICODE_FENCEPOSTS:
        locals()['test_wvarchar_%s' % len(value)] = _maketest(value)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)

    def test_varchar_upperlatin(self):
        self._test_strtype('varchar', 'á', colsize=3)

    #
    # binary
    #

    def test_null_binary(self):
        self._test_strtype('varbinary', None, 100)
     
    def test_large_null_binary(self):
        # Bug 1575064
        self._test_strtype('varbinary', None, 4000)

    # Generate a test for each fencepost size: test_binary_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', bytearray(value), max(1, len(value)))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_binary_%s' % len(value)] = _maketest(value)

    #
    # blob
    #

    def test_blob_null(self):
        self._test_strtype('blob', None)

    # Generate a test for each fencepost size: test_blob_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('blob', bytearray(value))
        return t
    for value in BLOB_FENCEPOSTS:
        locals()['test_blob_%s' % len(value)] = _maketest(value)

    def test_blob_upperlatin(self):
        self._test_strtype('blob', bytearray('á'))

    #
    # text
    #

    def test_null_text(self):
        self._test_strtype('text', None)

    # Generate a test for each fencepost size: test_text_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('text', value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_text_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strtype('text', 'á')

    #
    # unicode
    #

    def test_unicode_query(self):
        self.cursor.execute(u"select 1")

    #
    # bit
    #

    # The MySQL driver maps BIT colums to the ODBC bit data type, but they aren't behaving quite like a Boolean value
    # (which is what the ODBC bit data type really represents).  The MySQL BOOL data type is just an alias for a small
    # integer, so pyodbc can't recognize it and map it back to True/False.
    #
    # You can use both BIT and BOOL and they will act as you expect if you treat them as integers.  You can write 0 and
    # 1 to them and they will work.

    # def test_bit(self):
    #     value = True
    #     self.cursor.execute("create table t1(b bit)")
    #     self.cursor.execute("insert into t1 values (?)", value)
    #     v = self.cursor.execute("select b from t1").fetchone()[0]
    #     self.assertEqual(type(v), bool)
    #     self.assertEqual(v, value)
    #  
    # def test_bit_string_true(self):
    #     self.cursor.execute("create table t1(b bit)")
    #     self.cursor.execute("insert into t1 values (?)", "xyzzy")
    #     v = self.cursor.execute("select b from t1").fetchone()[0]
    #     self.assertEqual(type(v), bool)
    #     self.assertEqual(v, True)
    #  
    # def test_bit_string_false(self):
    #     self.cursor.execute("create table t1(b bit)")
    #     self.cursor.execute("insert into t1 values (?)", "")
    #     v = self.cursor.execute("select b from t1").fetchone()[0]
    #     self.assertEqual(type(v), bool)
    #     self.assertEqual(v, False)
    
    #
    # decimal
    #

    def test_small_decimal(self):
        # value = Decimal('1234567890987654321')
        value = Decimal('100010')       # (I use this because the ODBC docs tell us how the bytes should look in the C struct)
        self.cursor.execute("create table t1(d numeric(19))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_small_decimal_scale(self):
        # The same as small_decimal, except with a different scale.  This value exactly matches the ODBC documentation
        # example in the C Data Types appendix.
        value = '1000.10'
        value = Decimal(value)
        self.cursor.execute("create table t1(d numeric(20,6))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_negative_decimal_scale(self):
        value = Decimal('-10.0010')
        self.cursor.execute("create table t1(d numeric(19,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(value, result)

    def test_date(self):
        value = date(2001, 1, 1)

        self.cursor.execute("create table t1(dt date)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(result), type(value))
        self.assertEquals(result, value)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):

        # This fails on 64-bit Fedora with 5.1.
        # Should return 0x0123456789
        # Does return   0x0000000000
        #
        # Top 4 bytes are returned as 0x00 00 00 00.  If the input is high enough, they are returned as 0xFF FF FF FF.
        input = 0x123456789
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.5
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    def test_date(self):
        value = date.today()
     
        self.cursor.execute("create table t1(d date)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEquals(value, result)


    def test_time(self):
        value = datetime.now().time()
        
        # We aren't yet writing values using the new extended time type so the value written to the database is only
        # down to the second.
        value = value.replace(microsecond=0)
         
        self.cursor.execute("create table t1(t time)")
        self.cursor.execute("insert into t1 values (?)", value)
         
        result = self.cursor.execute("select t from t1").fetchone()[0]
        self.assertEquals(value, result)

    #
    # misc
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount.  Databases can return the actual rowcount
        or they can return -1 if it would help performance.  MySQL seems to always return the correct rowcount.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, count)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        # The Python DB API says that rowcount should be set to -1 and most ODBC drivers let us know there are no
        # records.  MySQL always returns 0, however.  Without parsing the SQL (which we are not going to do), I'm not
        # sure how we can tell the difference and set the value to -1.  For now, I'll have this test check for 0.

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    # REVIEW: The following fails.  Research.

    # def test_executemany_failure(self):
    #     """
    #     Ensure that an exception is raised if one query in an executemany fails.
    #     """
    #     self.cursor.execute("create table t1(a int, b varchar(10))")
    #  
    #     params = [ (1, 'good'),
    #                ('error', 'not an int'),
    #                (3, 'good') ]
    #     
    #     self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        filename = basename(sys.argv[0])
        assert filename.endswith('.py')
        connection_string = load_setup_connection_string(filename[:-3])

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(MySqlTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = pgtests
#!/usr/bin/python

# Unit tests for PostgreSQL on Linux (Fedora)
# This is a stripped down copy of the SQL Server tests.

import sys, os, re
import unittest
from decimal import Decimal
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of composed of `seed` to make a string `length` characters long.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class PGTestCase(unittest.TestCase):

    # These are from the C++ code.  Keep them up to date.

    # If we are reading a binary, string, or unicode value and do not know how large it is, we'll try reading 2K into a
    # buffer on the stack.  We then copy into a new Python object.
    SMALL_READ  = 2048

    # A read guaranteed not to fit in the MAX_STACK_STACK stack buffer, but small enough to be used for varchar (4K max).
    LARGE_READ = 4000

    SMALL_STRING = _generate_test_string(SMALL_READ)
    LARGE_STRING = _generate_test_string(LARGE_READ)

    def __init__(self, connection_string, ansi, unicode_results, method_name):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string
        self.ansi    = ansi
        self.unicode = unicode_results

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string, ansi=self.ansi)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()


    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))


    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        result = self.cursor.execute("select * from t1").fetchone()[0]

        if self.unicode and value != None:
            self.assertEqual(type(result), unicode)
        else:
            self.assertEqual(type(result), type(value))

        if value is not None:
            self.assertEqual(len(result), len(value))

        self.assertEqual(result, value)

    #
    # varchar
    #

    def test_empty_varchar(self):
        self._test_strtype('varchar', '', self.SMALL_READ)

    def test_null_varchar(self):
        self._test_strtype('varchar', None, self.SMALL_READ)

    def test_large_null_varchar(self):
        # There should not be a difference, but why not find out?
        self._test_strtype('varchar', None, self.LARGE_READ)

    def test_small_varchar(self):
        self._test_strtype('varchar', self.SMALL_STRING, self.SMALL_READ)

    def test_large_varchar(self):
        self._test_strtype('varchar', self.LARGE_STRING, self.LARGE_READ)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)



    def test_small_decimal(self):
        # value = Decimal('1234567890987654321')
        value = Decimal('100010')       # (I use this because the ODBC docs tell us how the bytes should look in the C struct)
        self.cursor.execute("create table t1(d numeric(19))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_small_decimal_scale(self):
        # The same as small_decimal, except with a different scale.  This value exactly matches the ODBC documentation
        # example in the C Data Types appendix.
        value = '1000.10'
        value = Decimal(value)
        self.cursor.execute("create table t1(d numeric(20,6))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_negative_decimal_scale(self):
        value = Decimal('-10.0010')
        self.cursor.execute("create table t1(d numeric(19,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def _exec(self):
        self.cursor.execute(self.sql)

    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()

        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), self.unicode and unicode or str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, 4)

    # PostgreSQL driver fails here?
    # def test_rowcount_reset(self):
    #     "Ensure rowcount is reset to -1"
    #
    #     self.cursor.execute("create table t1(i int)")
    #     count = 4
    #     for i in range(count):
    #         self.cursor.execute("insert into t1 values (?)", i)
    #     self.assertEquals(self.cursor.rowcount, 1)
    #
    #     self.cursor.execute("create table t2(i int)")
    #     self.assertEquals(self.cursor.rowcount, -1)

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False

    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(self.cursor.description, row.cursor_description)


    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        # REVIEW: Without the cast, we get the following error:
        # [07006] [unixODBC]Received an unsupported type from Postgres.;\nERROR:  table "t2" does not exist (14)

        count = self.cursor.execute("select cast(count(*) as int) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]

        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)


    def test_executemany_generator(self):
        self.cursor.execute("create table t1(a int)")

        self.cursor.executemany("insert into t1(a) values (?)", ((i,) for i in range(4)))

        row = self.cursor.execute("select min(a) mina, max(a) maxa from t1").fetchone()

        self.assertEqual(row.mina, 0)
        self.assertEqual(row.maxa, 3)


    def test_executemany_iterator(self):
        self.cursor.execute("create table t1(a int)")

        values = [ (i,) for i in range(4) ]

        self.cursor.executemany("insert into t1(a) values (?)", iter(values))

        row = self.cursor.execute("select min(a) mina, max(a) maxa from t1").fetchone()

        self.assertEqual(row.mina, 0)
        self.assertEqual(row.maxa, 3)


    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_pickling(self):
        row = self.cursor.execute("select 1 a, 'two' b").fetchone()

        import pickle
        s = pickle.dumps(row)

        other = pickle.loads(s)

        self.assertEqual(row, other)


    def test_int_limits(self):
        values = [ (-sys.maxint - 1), -1, 0, 1, 3230392212, sys.maxint ]

        self.cursor.execute("create table t1(a bigint)")

        for value in values:
            self.cursor.execute("delete from t1")
            self.cursor.execute("insert into t1 values(?)", value)
            v = self.cursor.execute("select a from t1").fetchone()[0]
            self.assertEqual(v, value)


def main():
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] connection_string")
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")
    parser.add_option('-a', '--ansi', help='ANSI only', default=False, action='store_true')
    parser.add_option('-u', '--unicode', help='Expect results in Unicode', default=False, action='store_true')

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('pgtests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    if options.verbose:
        cnxn = pyodbc.connect(connection_string, ansi=options.ansi)
        print 'library:', os.path.abspath(pyodbc.__file__)
        print 'odbc:    %s' % cnxn.getinfo(pyodbc.SQL_ODBC_VER)
        print 'driver:  %s %s' % (cnxn.getinfo(pyodbc.SQL_DRIVER_NAME), cnxn.getinfo(pyodbc.SQL_DRIVER_VER))
        print 'driver supports ODBC version %s' % cnxn.getinfo(pyodbc.SQL_DRIVER_ODBC_VER)
        print 'unicode:', pyodbc.UNICODE_SIZE, 'sqlwchar:', pyodbc.SQLWCHAR_SIZE
        cnxn.close()

    if options.test:
        # Run a single test
        if not options.test.startswith('test_'):
            options.test = 'test_%s' % (options.test)

        s = unittest.TestSuite([ PGTestCase(connection_string, options.ansi, options.unicode, options.test) ])
    else:
        # Run all tests in the class

        methods = [ m for m in dir(PGTestCase) if m.startswith('test_') ]
        methods.sort()
        s = unittest.TestSuite([ PGTestCase(connection_string, options.ansi, options.unicode, m) for m in methods ])

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(s)

if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = sqlitetests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for SQLite using the ODBC driver from http://www.ch-werner.de/sqliteodbc

To use, pass a connection string as the parameter. The tests will create and
drop tables t1 and t2 as necessary.  On Windows, use the 32-bit driver with
32-bit Python and the 64-bit driver with 64-bit Python (regardless of your
operating system bitness).

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

You can also put the connection string into a setup.cfg file in the root of the project
(the same one setup.py would use) like so:

  [sqlitetests]
  connection-string=Driver=SQLite3 ODBC Driver;Database=sqlite.db
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class SqliteTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ unicode(s) for s in ANSI_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def get_sqlite_version(self):
        """
        Returns the major version: 8-->2000, 9-->2005, 10-->2008
        """
        self.cursor.execute("exec master..xp_msver 'ProductVersion'")
        row = self.cursor.fetchone()
        return int(row.Character_Value.split('.', 1)[0])

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def test_fixed_unicode(self):
        value = u"t\xebsting"
        self.cursor.execute("create table t1(s nchar(7))")
        self.cursor.execute("insert into t1 values(?)", u"t\xebsting")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), unicode)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)


    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

        # Reported by Andy Hochhaus in the pyodbc group: In 2.1.7 and earlier, a hardcoded length of 255 was used to
        # determine whether a parameter was bound as a SQL_VARCHAR or SQL_LONGVARCHAR.  Apparently SQL Server chokes if
        # we bind as a SQL_LONGVARCHAR and the target column size is 8000 or less, which is considers just SQL_VARCHAR.
        # This means binding a 256 character value would cause problems if compared with a VARCHAR column under
        # 8001. We now use SQLGetTypeInfo to determine the time to switch.
        #
        # [42000] [Microsoft][SQL Server Native Client 10.0][SQL Server]The data types varchar and text are incompatible in the equal to operator.

        self.cursor.execute("select * from t1 where s=?", value)


    def _test_strliketype(self, sqltype, value, colsize=None):
        """
        The implementation for text, image, ntext, and binary.

        These types do not support comparison operators.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

    #
    # text
    #

    def test_text_null(self):
        self._test_strtype('text', None, 100)

    # Generate a test for each fencepost size: test_text_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('text', value, len(value))
        return t
    for value in UNICODE_FENCEPOSTS:
        locals()['test_text_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strtype('varchar', u'á')

    #
    # blob
    #

    def test_null_blob(self):
        self._test_strtype('blob', None, 100)
     
    def test_large_null_blob(self):
        # Bug 1575064
        self._test_strtype('blob', None, 4000)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('blob', buffer(value), len(value))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_blob_%s' % len(value)] = _maketest(value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_unicode(self):
        self.cursor.execute("create table t1(s nvarchar(20))")
        self.cursor.execute("insert into t1 values(?)", u"")

    def test_unicode_query(self):
        self.cursor.execute(u"select 1")
        
    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):
        input = 3000000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_negative_bigint(self):
        # Issue 186: BIGINT problem on 32-bit architeture
        input = -430000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)

    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, count)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, count)

    # Fails.  Not terribly important so I'm going to comment out for now and report to the ODBC driver writer.
    # def test_rowcount_reset(self):
    #     "Ensure rowcount is reset to -1"
    #     self.cursor.execute("create table t1(i int)")
    #     count = 4
    #     for i in range(count):
    #         self.cursor.execute("insert into t1 values (?)", i)
    #     self.assertEquals(self.cursor.rowcount, 1)
    #  
    #     self.cursor.execute("create table t2(i int)")
    #     self.assertEquals(self.cursor.rowcount, -1)

    #
    # always return Cursor
    #

    # In the 2.0.x branch, Cursor.execute sometimes returned the cursor and sometimes the rowcount.  This proved very
    # confusing when things went wrong and added very little value even when things went right since users could always
    # use: cursor.execute("...").rowcount

    def test_retcursor_delete(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_select(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("select * from t1")
        self.assertEquals(v, self.cursor)

    #
    # misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()

        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_view_select(self):
        # Reported in forum: Can't select from a view?  I think I do this a lot, but another test never hurts.

        # Create a table (t1) with 3 rows and a view (t2) into it.
        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(50))")
        for i in range(3):
            self.cursor.execute("insert into t1(c2) values (?)", "string%s" % i)
        self.cursor.execute("create view t2 as select * from t1")

        # Select from the view
        self.cursor.execute("select * from t2")
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(len(rows) == 3)

    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)

    def test_unicode_results(self):
        "Ensure unicode_results forces Unicode"
        othercnxn = pyodbc.connect(self.connection_string, unicode_results=True)
        othercursor = othercnxn.cursor()

        # ANSI data in an ANSI column ...
        othercursor.execute("create table t1(s varchar(20))")
        othercursor.execute("insert into t1 values(?)", 'test')

        # ... should be returned as Unicode
        value = othercursor.execute("select s from t1").fetchone()[0]
        self.assertEqual(value, u'test')

    def test_skip(self):
        # Insert 1, 2, and 3.  Fetch 1, skip 2, fetch 3.

        self.cursor.execute("create table t1(id int)");
        for i in range(1, 5):
            self.cursor.execute("insert into t1 values(?)", i)
        self.cursor.execute("select id from t1 order by id")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.cursor.skip(2)
        self.assertEqual(self.cursor.fetchone()[0], 4)

    def test_sets_execute(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.execute("insert into t1 (word) VALUES (?)", [words])

        self.assertRaises(pyodbc.ProgrammingError, f)

    def test_sets_executemany(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.executemany("insert into t1 (word) values (?)", [words])
            
        self.assertRaises(TypeError, f)

    def test_row_execute(self):
        "Ensure we can use a Row object as a parameter to execute"
        self.cursor.execute("create table t1(n int, s varchar(10))")
        self.cursor.execute("insert into t1 values (1, 'a')")
        row = self.cursor.execute("select n, s from t1").fetchone()
        self.assertNotEqual(row, None)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.execute("insert into t2 values (?, ?)", row)
        
    def test_row_executemany(self):
        "Ensure we can use a Row object as a parameter to executemany"
        self.cursor.execute("create table t1(n int, s varchar(10))")

        for i in range(3):
            self.cursor.execute("insert into t1 values (?, ?)", i, chr(ord('a')+i))

        rows = self.cursor.execute("select n, s from t1").fetchall()
        self.assertNotEqual(len(rows), 0)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.executemany("insert into t2 values (?, ?)", rows)
        
    def test_description(self):
        "Ensure cursor.description is correct"

        self.cursor.execute("create table t1(n int, s text)")
        self.cursor.execute("insert into t1 values (1, 'abc')")
        self.cursor.execute("select * from t1")

        # (I'm not sure the precision of an int is constant across different versions, bits, so I'm hand checking the
        # items I do know.

        # int
        t = self.cursor.description[0]
        self.assertEqual(t[0], 'n')
        self.assertEqual(t[1], int)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # text
        t = self.cursor.description[1]
        self.assertEqual(t[0], 's')
        self.assertEqual(t[1], unicode)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

    def test_none_param(self):
        "Ensure None can be used for params other than the first"
        # Some driver/db versions would fail if NULL was not the first parameter because SQLDescribeParam (only used
        # with NULL) could not be used after the first call to SQLBindParameter.  This means None always worked for the
        # first column, but did not work for later columns.
        #
        # If SQLDescribeParam doesn't work, pyodbc would use VARCHAR which almost always worked.  However,
        # binary/varbinary won't allow an implicit conversion.

        value = u'\x12abc'
        self.cursor.execute("create table t1(n int, b blob)")
        self.cursor.execute("insert into t1 values (1, ?)", value)
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 1)
        self.assertEqual(type(row.b), buffer)
        self.assertEqual(row.b, value)


    def test_row_equal(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test')")
        row1 = self.cursor.execute("select n, s from t1").fetchone()
        row2 = self.cursor.execute("select n, s from t1").fetchone()
        b = (row1 == row2)
        self.assertEqual(b, True)

    def test_row_gtlt(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test1')")
        self.cursor.execute("insert into t1 values (1, 'test2')")
        rows = self.cursor.execute("select n, s from t1 order by s").fetchall()
        self.assert_(rows[0] < rows[1])
        self.assert_(rows[0] <= rows[1])
        self.assert_(rows[1] > rows[0])
        self.assert_(rows[1] >= rows[0])
        self.assert_(rows[0] != rows[1])

        rows = list(rows)
        rows.sort() # uses <
        
    def test_context_manager(self):
        with pyodbc.connect(self.connection_string) as cnxn:
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)

        # The connection should be closed now.
        def test():
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assertRaises(pyodbc.ProgrammingError, test)

    def test_untyped_none(self):
        # From issue 129
        value = self.cursor.execute("select ?", None).fetchone()[0]
        self.assertEqual(value, None)
        
    def test_large_update_nodata(self):
        self.cursor.execute('create table t1(a blob)')
        hundredkb = buffer('x'*100*1024)
        self.cursor.execute('update t1 set a=? where 1=0', (hundredkb,))

    def test_no_fetch(self):
        # Issue 89 with FreeTDS: Multiple selects (or catalog functions that issue selects) without fetches seem to
        # confuse the driver.
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')

def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('sqlitetests')
        print 'connection_string:', connection_string

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(SqliteTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = sqlservertests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for SQL Server.  To use, pass a connection string as the parameter.
The tests will create and drop tables t1 and t2 as necessary.

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

You can also put the connection string into a setup.cfg file in the root of the project
(the same one setup.py would use) like so:

  [sqlservertests]
  connection-string=DRIVER={SQL Server};SERVER=localhost;UID=uid;PWD=pwd;DATABASE=db

The connection string above will use the 2000/2005 driver, even if SQL Server 2008
is installed:

  2000: DRIVER={SQL Server}
  2005: DRIVER={SQL Server}
  2008: DRIVER={SQL Server Native Client 10.0}
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class SqlServerTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]
    MAX_FENCEPOST_SIZES   = [ 5 * 1024 * 1024, 50 * 1024 * 1024 ]

    ANSI_SMALL_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_SMALL_FENCEPOSTS = [ unicode(s) for s in ANSI_SMALL_FENCEPOSTS ]
    ANSI_LARGE_FENCEPOSTS    = ANSI_SMALL_FENCEPOSTS    + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]
    UNICODE_LARGE_FENCEPOSTS = UNICODE_SMALL_FENCEPOSTS + [ unicode(s) for s in [_generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]]

    ANSI_MAX_FENCEPOSTS    = ANSI_LARGE_FENCEPOSTS + [ _generate_test_string(size) for size in MAX_FENCEPOST_SIZES ]
    UNICODE_MAX_FENCEPOSTS = UNICODE_LARGE_FENCEPOSTS + [ unicode(s) for s in [_generate_test_string(size) for size in MAX_FENCEPOST_SIZES ]]


    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def get_sqlserver_version(self):
        """
        Returns the major version: 8-->2000, 9-->2005, 10-->2008
        """
        self.cursor.execute("exec master..xp_msver 'ProductVersion'")
        row = self.cursor.fetchone()
        return int(row.Character_Value.split('.', 1)[0])

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        for i in range(3):
            try:
                self.cursor.execute("drop procedure proc%d" % i)
                self.cnxn.commit()
            except:
                pass

        try:
            self.cursor.execute('drop function func1')
            self.cnxn.commit()
        except:
            pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_binary_type(self):
        if sys.hexversion >= 0x02060000:
            self.assertIs(pyodbc.BINARY, bytearray)
        else:
            self.assertIs(pyodbc.BINARY, buffer)

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def test_noscan(self):
        self.assertEqual(self.cursor.noscan, False)
        self.cursor.noscan = True
        self.assertEqual(self.cursor.noscan, True)

    def test_guid(self):
        self.cursor.execute("create table t1(g1 uniqueidentifier)")
        self.cursor.execute("insert into t1 values (newid())")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), 36)

    def test_nextset(self):
        self.cursor.execute("create table t1(i int)")
        for i in range(4):
            self.cursor.execute("insert into t1(i) values(?)", i)

        self.cursor.execute("select i from t1 where i < 2 order by i; select i from t1 where i >= 2 order by i")
        
        for i, row in enumerate(self.cursor):
            self.assertEqual(i, row.i)

        self.assertEqual(self.cursor.nextset(), True)

        for i, row in enumerate(self.cursor):
            self.assertEqual(i + 2, row.i)

    def test_fixed_unicode(self):
        value = u"t\xebsting"
        self.cursor.execute("create table t1(s nchar(7))")
        self.cursor.execute("insert into t1 values(?)", u"t\xebsting")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), unicode)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)


    def _test_strtype(self, sqltype, value, resulttype=None, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize in (None, 'max') or isinstance(colsize, int), colsize
        assert colsize in (None, 'max') or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        if resulttype is None:
            resulttype = type(value)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), resulttype)

        if value is not None:
            self.assertEqual(len(v), len(value))

        # To allow buffer --> db --> bytearray tests, always convert the input to the expected result type before
        # comparing.
        if type(value) is not resulttype:
            value = resulttype(value)

        self.assertEqual(v, value)


    def _test_strliketype(self, sqltype, value, resulttype=None, colsize=None):
        """
        The implementation for text, image, ntext, and binary.

        These types do not support comparison operators.
        """
        assert colsize is None or isinstance(colsize, int), colsize
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        if resulttype is None:
            resulttype = type(value)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), resulttype)

        if value is not None:
            self.assertEqual(len(v), len(value))

        # To allow buffer --> db --> bytearray tests, always convert the input to the expected result type before
        # comparing.
        if type(value) is not resulttype:
            value = resulttype(value)

        self.assertEqual(v, value)


    #
    # varchar
    #

    def test_varchar_null(self):
        self._test_strtype('varchar', None, colsize=100)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, colsize=len(value))
        return t
    for value in ANSI_SMALL_FENCEPOSTS:
        locals()['test_varchar_%s' % len(value)] = _maketest(value)

    # Also test varchar(max)
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, colsize='max')
        return t
    for value in ANSI_MAX_FENCEPOSTS:
        locals()['test_varcharmax_%s' % len(value)] = _maketest(value)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3, len(c1) as l1, len(c2) as l2, len(c3) as l3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)

    def test_varchar_upperlatin(self):
        self._test_strtype('varchar', 'á')

    #
    # unicode
    #

    def test_unicode_null(self):
        self._test_strtype('nvarchar', None, colsize=100)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('nvarchar', value, colsize=len(value))
        return t
    for value in UNICODE_SMALL_FENCEPOSTS:
        locals()['test_unicode_%s' % len(value)] = _maketest(value)

    # Also test nvarchar(max)
    def _maketest(value):
        def t(self):
            self._test_strtype('nvarchar', value, colsize='max')
        return t
    for value in UNICODE_MAX_FENCEPOSTS:
        locals()['test_nvarcharmax_%s' % len(value)] = _maketest(value)

    def test_unicode_upperlatin(self):
        self._test_strtype('nvarchar', u'á')

    def test_unicode_longmax(self):
        # Issue 188:	Segfault when fetching NVARCHAR(MAX) data over 511 bytes

        ver = self.get_sqlserver_version()
        if ver < 9:            # 2005+
            return              # so pass / ignore
        self.cursor.execute("select cast(replicate(N'x', 512) as nvarchar(max))")

    #
    # binary
    #

    def test_binary_null(self):
        self._test_strtype('varbinary', None, colsize=100)
     
    def test_large_binary_null(self):
        # Bug 1575064
        self._test_strtype('varbinary', None, colsize=4000)

    def test_binaryNull_object(self):
        self.cursor.execute("create table t1(n varbinary(10))")
        self.cursor.execute("insert into t1 values (?)", pyodbc.BinaryNull);

    # buffer

    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), resulttype=pyodbc.BINARY, colsize=len(value))
        return t
    for value in ANSI_SMALL_FENCEPOSTS:
        locals()['test_binary_buffer_%s' % len(value)] = _maketest(value)

    # bytearray

    if sys.hexversion >= 0x02060000:
        def _maketest(value):
            def t(self):
                self._test_strtype('varbinary', bytearray(value), colsize=len(value))
            return t
        for value in ANSI_SMALL_FENCEPOSTS:
            locals()['test_binary_bytearray_%s' % len(value)] = _maketest(value)

    # varbinary(max)
    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), resulttype=pyodbc.BINARY, colsize='max')
        return t
    for value in ANSI_MAX_FENCEPOSTS:
        locals()['test_binarymax_buffer_%s' % len(value)] = _maketest(value)

    # bytearray

    if sys.hexversion >= 0x02060000:
        def _maketest(value):
            def t(self):
                self._test_strtype('varbinary', bytearray(value), colsize='max')
            return t
        for value in ANSI_MAX_FENCEPOSTS:
            locals()['test_binarymax_bytearray_%s' % len(value)] = _maketest(value)

    #
    # image
    #

    def test_image_null(self):
        self._test_strliketype('image', None, type(None))

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('image', buffer(value), pyodbc.BINARY)
        return t
    for value in ANSI_LARGE_FENCEPOSTS:
        locals()['test_image_buffer_%s' % len(value)] = _maketest(value)

    if sys.hexversion >= 0x02060000:
        # Python 2.6+ supports bytearray, which pyodbc considers varbinary.
        
        # Generate a test for each fencepost size: test_unicode_0, etc.
        def _maketest(value):
            def t(self):
                self._test_strtype('image', bytearray(value))
            return t
        for value in ANSI_LARGE_FENCEPOSTS:
            locals()['test_image_bytearray_%s' % len(value)] = _maketest(value)

    def test_image_upperlatin(self):
        self._test_strliketype('image', buffer('á'), pyodbc.BINARY)

    #
    # text
    #

    # def test_empty_text(self):
    #     self._test_strliketype('text', bytearray(''))

    def test_null_text(self):
        self._test_strliketype('text', None, type(None))

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('text', value)
        return t
    for value in ANSI_SMALL_FENCEPOSTS:
        locals()['test_text_buffer_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strliketype('text', 'á')

    #
    # xml
    #

    # def test_empty_xml(self):
    #     self._test_strliketype('xml', bytearray(''))

    def test_null_xml(self):
        self._test_strliketype('xml', None, type(None))

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('xml', value)
        return t
    for value in ANSI_SMALL_FENCEPOSTS:
        locals()['test_xml_buffer_%s' % len(value)] = _maketest(value)

    def test_xml_upperlatin(self):
        self._test_strliketype('xml', 'á')

    #
    # bit
    #

    def test_bit(self):
        value = True
        self.cursor.execute("create table t1(b bit)")
        self.cursor.execute("insert into t1 values (?)", value)
        v = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(v), bool)
        self.assertEqual(v, value)

    #
    # decimal
    #

    def _decimal(self, precision, scale, negative):
        # From test provided by planders (thanks!) in Issue 91

        self.cursor.execute("create table t1(d decimal(%s, %s))" % (precision, scale))

        # Construct a decimal that uses the maximum precision and scale.
        decStr = '9' * (precision - scale)
        if scale:
            decStr = decStr + "." + '9' * scale
        if negative:
            decStr = "-" + decStr
        value = Decimal(decStr)

        self.cursor.execute("insert into t1 values(?)", value)

        v = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(v, value)

    def _maketest(p, s, n):
        def t(self):
            self._decimal(p, s, n)
        return t
    for (p, s, n) in [ (1,  0,  False),
                       (1,  0,  True),
                       (6,  0,  False),
                       (6,  2,  False),
                       (6,  4,  True),
                       (6,  6,  True),
                       (38, 0,  False),
                       (38, 10, False),
                       (38, 38, False),
                       (38, 0,  True),
                       (38, 10, True),
                       (38, 38, True) ]:
        locals()['test_decimal_%s_%s_%s' % (p, s, n and 'n' or 'p')] = _maketest(p, s, n)


    def test_decimal_e(self):
        """Ensure exponential notation decimals are properly handled"""
        value = Decimal((0, (1, 2, 3), 5)) # prints as 1.23E+7
        self.cursor.execute("create table t1(d decimal(10, 2))")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(result, value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_empty_unicode(self):
        self.cursor.execute("create table t1(s nvarchar(20))")
        self.cursor.execute("insert into t1 values(?)", u"")

    def test_unicode_query(self):
        self.cursor.execute(u"select 1")
        
    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    def test_datetime_fraction(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds, so the most granular datetime
        # supported is xxx000.

        value = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(result, value)

    def test_datetime_fraction_rounded(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds.  pyodbc rounds down to what the
        # database supports.

        full    = datetime(2007, 1, 15, 3, 4, 5, 123456)
        rounded = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", full)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(result), datetime)
        self.assertEquals(result, rounded)

    def test_date(self):
        ver = self.get_sqlserver_version()
        if ver < 10:            # 2008 only
            return              # so pass / ignore

        value = date.today()
     
        self.cursor.execute("create table t1(d date)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEquals(type(value), date)
        self.assertEquals(value, result)

    def test_time(self):
        ver = self.get_sqlserver_version()
        if ver < 10:            # 2008 only
            return              # so pass / ignore

        value = datetime.now().time()
        
        # We aren't yet writing values using the new extended time type so the value written to the database is only
        # down to the second.
        value = value.replace(microsecond=0)
         
        self.cursor.execute("create table t1(t time)")
        self.cursor.execute("insert into t1 values (?)", value)
         
        result = self.cursor.execute("select t from t1").fetchone()[0]
        self.assertEquals(type(value), time)
        self.assertEquals(value, result)

    def test_datetime2(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime2)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):
        input = 3000000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    #
    # stored procedures
    #

    # def test_callproc(self):
    #     "callproc with a simple input-only stored procedure"
    #     pass

    def test_sp_results(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              select top 10 name, id, xtype, refdate
              from sysobjects
            """)
        rows = self.cursor.execute("exec proc1").fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_temp(self):

        # Note: I've used "set nocount on" so that we don't get the number of rows deleted from #tmptable.
        # If you don't do this, you'd need to call nextset() once to skip it.

        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              select top 10 name, id, xtype, refdate
              into #tmptable
              from sysobjects

              select * from #tmptable
            """)
        self.cursor.execute("exec proc1")
        self.assert_(self.cursor.description is not None)
        self.assert_(len(self.cursor.description) == 4)

        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_vartbl(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              declare @tmptbl table(name varchar(100), id int, xtype varchar(4), refdate datetime)

              insert into @tmptbl
              select top 10 name, id, xtype, refdate
              from sysobjects

              select * from @tmptbl
            """)
        self.cursor.execute("exec proc1")
        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)

    def test_sp_with_dates(self):
        # Reported in the forums that passing two datetimes to a stored procedure doesn't work.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@d1 datetime, @d2 datetime)
            AS
              declare @d as int
              set @d = datediff(year, @d1, @d2)
              select @d
            """)
        self.cursor.execute("exec test_sp ?, ?", datetime.now(), datetime.now())
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == 0)   # 0 years apart

    def test_sp_with_none(self):
        # Reported in the forums that passing None caused an error.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@x varchar(20))
            AS
              declare @y varchar(20)
              set @y = @x
              select @y
            """)
        self.cursor.execute("exec test_sp ?", None)
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == None)   # 0 years apart
        

    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount, but SQL Server 2005 returns -1 after a
        select statement, so we'll test for that behavior.  This is valid behavior according to the DB API
        specification, but people don't seem to like it.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, -1)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, -1)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, -1)

    #
    # always return Cursor
    #

    # In the 2.0.x branch, Cursor.execute sometimes returned the cursor and sometimes the rowcount.  This proved very
    # confusing when things went wrong and added very little value even when things went right since users could always
    # use: cursor.execute("...").rowcount

    def test_retcursor_delete(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_select(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("select * from t1")
        self.assertEquals(v, self.cursor)

    #
    # misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()

        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_temp_select(self):
        # A project was failing to create temporary tables via select into.
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")

        self.cursor.execute("select s into t2 from t1")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")


    def test_money(self):
        d = Decimal('123456.78')
        self.cursor.execute("create table t1(i int identity(1,1), m money)")
        self.cursor.execute("insert into t1(m) values (?)", d)
        v = self.cursor.execute("select m from t1").fetchone()[0]
        self.assertEqual(v, d)


    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_concatenation(self):
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(300), c3 varchar(300))")
        self.cursor.execute("insert into t1(c2, c3) values (?,?)", v2, v3)

        row = self.cursor.execute("select c2, c3, c2 + c3 as both from t1").fetchone()

        self.assertEqual(row.both, v2 + v3)

    def test_view_select(self):
        # Reported in forum: Can't select from a view?  I think I do this a lot, but another test never hurts.

        # Create a table (t1) with 3 rows and a view (t2) into it.
        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(50))")
        for i in range(3):
            self.cursor.execute("insert into t1(c2) values (?)", "string%s" % i)
        self.cursor.execute("create view t2 as select * from t1")

        # Select from the view
        self.cursor.execute("select * from t2")
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(len(rows) == 3)

    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)

    def test_cursorcommit(self):
        "Ensure cursor.commit works"
        othercnxn = pyodbc.connect(self.connection_string)
        othercursor = othercnxn.cursor()
        othercnxn = None

        othercursor.execute("create table t1(s varchar(20))")
        othercursor.execute("insert into t1 values(?)", 'test')
        othercursor.commit()

        value = self.cursor.execute("select s from t1").fetchone()[0]
        self.assertEqual(value, 'test')


    def test_unicode_results(self):
        "Ensure unicode_results forces Unicode"
        othercnxn = pyodbc.connect(self.connection_string, unicode_results=True)
        othercursor = othercnxn.cursor()

        # ANSI data in an ANSI column ...
        othercursor.execute("create table t1(s varchar(20))")
        othercursor.execute("insert into t1 values(?)", 'test')

        # ... should be returned as Unicode
        value = othercursor.execute("select s from t1").fetchone()[0]
        self.assertEqual(value, u'test')


    def test_sqlserver_callproc(self):
        try:
            self.cursor.execute("drop procedure pyodbctest")
            self.cnxn.commit()
        except:
            pass

        self.cursor.execute("create table t1(s varchar(10))")
        self.cursor.execute("insert into t1 values(?)", "testing")

        self.cursor.execute("""
                            create procedure pyodbctest @var1 varchar(32)
                            as 
                            begin 
                              select s 
                              from t1 
                            return 
                            end
                            """)
        self.cnxn.commit()

        # for row in self.cursor.procedureColumns('pyodbctest'):
        #     print row.procedure_name, row.column_name, row.column_type, row.type_name

        self.cursor.execute("exec pyodbctest 'hi'")

        # print self.cursor.description
        # for row in self.cursor:
        #     print row.s

    def test_skip(self):
        # Insert 1, 2, and 3.  Fetch 1, skip 2, fetch 3.

        self.cursor.execute("create table t1(id int)");
        for i in range(1, 5):
            self.cursor.execute("insert into t1 values(?)", i)
        self.cursor.execute("select id from t1 order by id")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.cursor.skip(2)
        self.assertEqual(self.cursor.fetchone()[0], 4)

    def test_timeout(self):
        self.assertEqual(self.cnxn.timeout, 0) # defaults to zero (off)

        self.cnxn.timeout = 30
        self.assertEqual(self.cnxn.timeout, 30)

        self.cnxn.timeout = 0
        self.assertEqual(self.cnxn.timeout, 0)

    def test_sets_execute(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.execute("insert into t1 (word) VALUES (?)", [words])

        self.assertRaises(pyodbc.ProgrammingError, f)

    def test_sets_executemany(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.executemany("insert into t1 (word) values (?)", [words])
            
        self.assertRaises(TypeError, f)

    def test_row_execute(self):
        "Ensure we can use a Row object as a parameter to execute"
        self.cursor.execute("create table t1(n int, s varchar(10))")
        self.cursor.execute("insert into t1 values (1, 'a')")
        row = self.cursor.execute("select n, s from t1").fetchone()
        self.assertNotEqual(row, None)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.execute("insert into t2 values (?, ?)", row)
        
    def test_row_executemany(self):
        "Ensure we can use a Row object as a parameter to executemany"
        self.cursor.execute("create table t1(n int, s varchar(10))")

        for i in range(3):
            self.cursor.execute("insert into t1 values (?, ?)", i, chr(ord('a')+i))

        rows = self.cursor.execute("select n, s from t1").fetchall()
        self.assertNotEqual(len(rows), 0)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.executemany("insert into t2 values (?, ?)", rows)
        
    def test_description(self):
        "Ensure cursor.description is correct"

        self.cursor.execute("create table t1(n int, s varchar(8), d decimal(5,2))")
        self.cursor.execute("insert into t1 values (1, 'abc', '1.23')")
        self.cursor.execute("select * from t1")

        # (I'm not sure the precision of an int is constant across different versions, bits, so I'm hand checking the
        # items I do know.

        # int
        t = self.cursor.description[0]
        self.assertEqual(t[0], 'n')
        self.assertEqual(t[1], int)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # varchar(8)
        t = self.cursor.description[1]
        self.assertEqual(t[0], 's')
        self.assertEqual(t[1], str)
        self.assertEqual(t[4], 8)       # precision
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # decimal(5, 2)
        t = self.cursor.description[2]
        self.assertEqual(t[0], 'd')
        self.assertEqual(t[1], Decimal)
        self.assertEqual(t[4], 5)       # precision
        self.assertEqual(t[5], 2)       # scale
        self.assertEqual(t[6], True)    # nullable

        
    def test_none_param(self):
        "Ensure None can be used for params other than the first"
        # Some driver/db versions would fail if NULL was not the first parameter because SQLDescribeParam (only used
        # with NULL) could not be used after the first call to SQLBindParameter.  This means None always worked for the
        # first column, but did not work for later columns.
        #
        # If SQLDescribeParam doesn't work, pyodbc would use VARCHAR which almost always worked.  However,
        # binary/varbinary won't allow an implicit conversion.

        self.cursor.execute("create table t1(n int, blob varbinary(max))")
        self.cursor.execute("insert into t1 values (1, newid())")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 1)
        self.assertEqual(type(row.blob), bytearray)

        self.cursor.execute("update t1 set n=?, blob=?", 2, None)
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 2)
        self.assertEqual(row.blob, None)


    def test_output_conversion(self):
        def convert(value):
            # `value` will be a string.  We'll simply add an X at the beginning at the end.
            return 'X' + value + 'X'
        self.cnxn.add_output_converter(pyodbc.SQL_VARCHAR, convert)
        self.cursor.execute("create table t1(n int, v varchar(10))")
        self.cursor.execute("insert into t1 values (1, '123.45')")
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, 'X123.45X')

        # Now clear the conversions and try again.  There should be no Xs this time.
        self.cnxn.clear_output_converters()
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, '123.45')


    def test_too_large(self):
        """Ensure error raised if insert fails due to truncation"""
        value = 'x' * 1000
        self.cursor.execute("create table t1(s varchar(800))")
        def test():
            self.cursor.execute("insert into t1 values (?)", value)
        self.assertRaises(pyodbc.DataError, test)

    def test_geometry_null_insert(self):
        def convert(value):
            return value

        self.cnxn.add_output_converter(-151, convert) # -151 is SQL Server's geometry
        self.cursor.execute("create table t1(n int, v geometry)")
        self.cursor.execute("insert into t1 values (?, ?)", 1, None)
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, None)
        self.cnxn.clear_output_converters()

    def test_login_timeout(self):
        # This can only test setting since there isn't a way to cause it to block on the server side.
        cnxns = pyodbc.connect(self.connection_string, timeout=2)

    def test_row_equal(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test')")
        row1 = self.cursor.execute("select n, s from t1").fetchone()
        row2 = self.cursor.execute("select n, s from t1").fetchone()
        b = (row1 == row2)
        self.assertEqual(b, True)

    def test_row_gtlt(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test1')")
        self.cursor.execute("insert into t1 values (1, 'test2')")
        rows = self.cursor.execute("select n, s from t1 order by s").fetchall()
        self.assert_(rows[0] < rows[1])
        self.assert_(rows[0] <= rows[1])
        self.assert_(rows[1] > rows[0])
        self.assert_(rows[1] >= rows[0])
        self.assert_(rows[0] != rows[1])

        rows = list(rows)
        rows.sort() # uses <
        
    def test_context_manager_success(self):
        """
        Ensure a successful with statement causes a commit.
        """
        self.cursor.execute("create table t1(n int)")
        self.cnxn.commit()

        with pyodbc.connect(self.connection_string) as cnxn:
            cursor = cnxn.cursor()
            cursor.execute("insert into t1 values (1)")

        cnxn = None
        cursor = None

        rows = self.cursor.execute("select n from t1").fetchall()
        self.assertEquals(len(rows), 1)
        self.assertEquals(rows[0][0], 1)


    def test_context_manager_fail(self):
        """
        Ensure an exception in a with statement causes a rollback.
        """
        self.cursor.execute("create table t1(n int)")
        self.cnxn.commit()

        try:
            with pyodbc.connect(self.connection_string) as cnxn:
                cursor = cnxn.cursor()
                cursor.execute("insert into t1 values (1)")
                raise Exception("Testing failure")
        except Exception:
            pass

        cnxn = None
        cursor = None

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEquals(count, 0)


    def test_cursor_context_manager_success(self):
        """
        Ensure a successful with statement using a cursor causes a commit.
        """
        self.cursor.execute("create table t1(n int)")
        self.cnxn.commit()

        with pyodbc.connect(self.connection_string).cursor() as cursor:
            cursor.execute("insert into t1 values (1)")

        cursor = None

        rows = self.cursor.execute("select n from t1").fetchall()
        self.assertEquals(len(rows), 1)
        self.assertEquals(rows[0][0], 1)


    def test_cursor_context_manager_fail(self):
        """
        Ensure an exception in a with statement using a cursor causes a rollback.
        """
        self.cursor.execute("create table t1(n int)")
        self.cnxn.commit()

        try:
            with pyodbc.connect(self.connection_string).cursor() as cursor:
                cursor.execute("insert into t1 values (1)")
                raise Exception("Testing failure")
        except Exception:
            pass

        cursor = None

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEquals(count, 0)


    def test_untyped_none(self):
        # From issue 129
        value = self.cursor.execute("select ?", None).fetchone()[0]
        self.assertEqual(value, None)
        
    def test_large_update_nodata(self):
        self.cursor.execute('create table t1(a varbinary(max))')
        hundredkb = bytearray('x'*100*1024)
        self.cursor.execute('update t1 set a=? where 1=0', (hundredkb,))

    def test_func_param(self):
        self.cursor.execute('''
                            create function func1 (@testparam varchar(4)) 
                            returns @rettest table (param varchar(4))
                            as 
                            begin
                                insert @rettest
                                select @testparam
                                return
                            end
                            ''')
        self.cnxn.commit()
        value = self.cursor.execute("select * from func1(?)", 'test').fetchone()[0]
        self.assertEquals(value, 'test')
        
    def test_no_fetch(self):
        # Issue 89 with FreeTDS: Multiple selects (or catalog functions that issue selects) without fetches seem to
        # confuse the driver.
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')

    def test_drivers(self):
        drivers = pyodbc.drivers()
        self.assertEqual(list, type(drivers))
        self.assert_(len(drivers) > 1)

        m = re.search('DRIVER={([^}]+)}', self.connection_string, re.IGNORECASE)
        current = m.group(1)
        self.assert_(current in drivers)
            
    def test_prepare_cleanup(self):
        # When statement is prepared, it is kept in case the next execute uses the same statement.  This must be
        # removed when a non-execute statement is used that returns results, such as SQLTables.

        self.cursor.execute("select top 1 name from sysobjects where name = ?", "bogus")
        self.cursor.fetchone()

        self.cursor.tables("bogus")
        
        self.cursor.execute("select top 1 name from sysobjects where name = ?", "bogus")
        self.cursor.fetchone()
 


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('sqlservertests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(SqlServerTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

from testutils import *

add_to_path()
import pyodbc

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('test')
        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)

    if options.verbose:
        print_library_info(cnxn)


if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = testbase

import unittest

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class TestBase(unittest.TestCase):

    

########NEW FILE########
__FILENAME__ = testutils

import os, sys, platform
from os.path import join, dirname, abspath, basename
import unittest

def add_to_path():
    """
    Prepends the build directory to the path so that newly built pyodbc libraries are used, allowing it to be tested
    without installing it.
    """
    # Put the build directory into the Python path so we pick up the version we just built.
    #
    # To make this cross platform, we'll search the directories until we find the .pyd file.

    import imp

    library_exts  = [ t[0] for t in imp.get_suffixes() if t[-1] == imp.C_EXTENSION ]
    library_names = [ 'pyodbc%s' % ext for ext in library_exts ]

    # Only go into directories that match our version number. 

    dir_suffix = '-%s.%s' % (sys.version_info[0], sys.version_info[1])

    build = join(dirname(dirname(abspath(__file__))), 'build')

    for root, dirs, files in os.walk(build):
        for d in dirs[:]:
            if not d.endswith(dir_suffix):
                dirs.remove(d)

        for name in library_names:
            if name in files:
                sys.path.insert(0, root)
                return
                
    print >>sys.stderr, 'Did not find the pyodbc library in the build directory.  Will use an installed version.'


def print_library_info(cnxn):
    import pyodbc
    print 'python:  %s' % sys.version
    print 'pyodbc:  %s %s' % (pyodbc.version, os.path.abspath(pyodbc.__file__))
    print 'odbc:    %s' % cnxn.getinfo(pyodbc.SQL_ODBC_VER)
    print 'driver:  %s %s' % (cnxn.getinfo(pyodbc.SQL_DRIVER_NAME), cnxn.getinfo(pyodbc.SQL_DRIVER_VER))
    print '         supports ODBC version %s' % cnxn.getinfo(pyodbc.SQL_DRIVER_ODBC_VER)
    print 'os:      %s' % platform.system()
    print 'unicode: Py_Unicode=%s SQLWCHAR=%s' % (pyodbc.UNICODE_SIZE, pyodbc.SQLWCHAR_SIZE)

    if platform.system() == 'Windows':
        print '         %s' % ' '.join([s for s in platform.win32_ver() if s])



def load_tests(testclass, name, *args):
    """
    Returns a TestSuite for tests in `testclass`.

    name
      Optional test name if you only want to run 1 test.  If not provided all tests in `testclass` will be loaded.

    args
      Arguments for the test class constructor.  These will be passed after the test method name.
    """
    if name:
        if not name.startswith('test_'):
            name = 'test_%s' % name
        names = [ name ]

    else:
        names = [ method for method in dir(testclass) if method.startswith('test_') ]

    return unittest.TestSuite([ testclass(name, *args) for name in names ])


def load_setup_connection_string(section):
    """
    Attempts to read the default connection string from the setup.cfg file.

    If the file does not exist or if it exists but does not contain the connection string, None is returned.  If the
    file exists but cannot be parsed, an exception is raised.
    """
    from os.path import exists, join, dirname, splitext, basename
    from ConfigParser import SafeConfigParser
    
    FILENAME = 'setup.cfg'
    KEY      = 'connection-string'

    path = join(dirname(dirname(abspath(__file__))), 'tmp', FILENAME)

    if exists(path):
        try:
            p = SafeConfigParser()
            p.read(path)
        except:
            raise SystemExit('Unable to parse %s: %s' % (path, sys.exc_info()[1]))

        if p.has_option(section, KEY):
            return p.get(section, KEY)

    return None

########NEW FILE########
__FILENAME__ = accesstests
#!/usr/bin/python

usage="""\
usage: %prog [options] filename

Unit tests for Microsoft Access

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

To run, pass the filename of an Access database on the command line:

  accesstests test.accdb

An empty Access 2000 database (empty.mdb) and an empty Access 2007 database
(empty.accdb), are provided.

To run a single test, use the -t option:

  accesstests test.accdb -t unicode_null

If you want to report an error, it would be helpful to include the driver information
by using the verbose flag and redirecting the output to a file:

 accesstests test.accdb -v >& results.txt

You can pass the verbose flag twice for more verbose output:

 accesstests test.accdb -vv
"""

# Access SQL data types: http://msdn2.microsoft.com/en-us/library/bb208866.aspx

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import abspath
from testutils import *

CNXNSTRING = None

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of composed of `seed` to make a string `length` characters long.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]


class AccessTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 254, 255 ] # text fields <= 255
    LARGE_FENCEPOST_SIZES = [ 256, 270, 304, 508, 510, 511, 512, 1023, 1024, 2047, 2048, 4000, 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ unicode(s) for s in ANSI_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name):
        unittest.TestCase.__init__(self, method_name)

    def setUp(self):
        self.cnxn   = pyodbc.connect(CNXNSTRING)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value)), 'colsize=%s value=%s' % (colsize, (value is None) and 'none' or len(value))

        if colsize:
            sql = "create table t1(n1 int not null, s1 %s(%s), s2 %s(%s))" % (sqltype, colsize, sqltype, colsize)
        else:
            sql = "create table t1(n1 int not null, s1 %s, s2 %s)" % (sqltype, sqltype)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(1, ?, ?)", (value, value))
        row = self.cursor.execute("select s1, s2 from t1").fetchone()

        # Access only uses Unicode, but strings might have been passed in to see if they can be written.  When we read
        # them back, they'll be unicode, so compare our results to a Unicode version of `value`.
        if type(value) is str:
            value = unicode(value)

        for i in range(2):
            v = row[i]

            self.assertEqual(type(v), type(value))

            if value is not None:
                self.assertEqual(len(v), len(value))

            self.assertEqual(v, value)

    #
    # unicode
    #

    def test_unicode_null(self):
        self._test_strtype('varchar', None, 255)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, len(value))
        t.__doc__ = 'unicode %s' % len(value)
        return t
    for value in UNICODE_FENCEPOSTS:
        locals()['test_unicode_%s' % len(value)] = _maketest(value)

    #
    # ansi -> varchar
    #

    # Access only stores Unicode text but it should accept ASCII text.

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, len(value))
        t.__doc__ = 'ansi %s' % len(value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_ansivarchar_%s' % len(value)] = _maketest(value)

    #
    # binary
    #

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), len(value))
        t.__doc__ = 'binary %s' % len(value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_binary_%s' % len(value)] = _maketest(value)


    #
    # image
    #

    def test_null_image(self):
        self._test_strtype('image', None)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('image', buffer(value))
        t.__doc__ = 'image %s' % len(value)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_image_%s' % len(value)] = _maketest(value)

    #
    # memo
    #

    def test_null_memo(self):
        self._test_strtype('memo', None)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('memo', unicode(value))
        t.__doc__ = 'Unicode to memo %s' % len(value)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_memo_%s' % len(value)] = _maketest(value)

    # ansi -> memo
    def _maketest(value):
        def t(self):
            self._test_strtype('memo', value)
        t.__doc__ = 'ANSI to memo %s' % len(value)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_ansimemo_%s' % len(value)] = _maketest(value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)


    def test_unicode_query(self):
        self.cursor.execute(u"select 1")
        
    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(value, result)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_smallint(self):
        value = 32767
        self.cursor.execute("create table t1(n smallint)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_real(self):
        value = 1234.5
        self.cursor.execute("create table t1(n real)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_real(self):
        value = -200.5
        self.cursor.execute("create table t1(n real)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200.5
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)

    def test_tinyint(self):
        self.cursor.execute("create table t1(n tinyint)")
        value = 10
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(type(result), type(value))
        self.assertEqual(value, result)

    #
    # decimal & money
    #

    def test_decimal(self):
        value = Decimal('12345.6789')
        self.cursor.execute("create table t1(n numeric(10,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)

    def test_money(self):
        self.cursor.execute("create table t1(n money)")
        value = Decimal('1234.45')
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(type(result), type(value))
        self.assertEqual(value, result)

    def test_negative_decimal_scale(self):
        value = Decimal('-10.0010')
        self.cursor.execute("create table t1(d numeric(19,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)

    #
    # bit
    #

    def test_bit(self):
        self.cursor.execute("create table t1(b bit)")

        value = True
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(result), bool)
        self.assertEqual(value, result)

    def test_bit_null(self):
        self.cursor.execute("create table t1(b bit)")

        value = None
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(result), bool)
        self.assertEqual(False, result)

    def test_guid(self):
        # REVIEW: Python doesn't (yet) have a UUID type so the value is returned as a string.  Access, however, only
        # really supports Unicode.  For now, we'll have to live with this difference.  All strings in Python 3.x will
        # be Unicode -- pyodbc 3.x will have different defaults.
        value = "de2ac9c6-8676-4b0b-b8a6-217a8580cbee"
        self.cursor.execute("create table t1(g1 uniqueidentifier)")
        self.cursor.execute("insert into t1 values (?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))
        self.assertEqual(len(v), len(value))


    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount, but SQL Server 2005 returns -1 after a
        select statement, so we'll test for that behavior.  This is valid behavior according to the DB API
        specification, but people don't seem to like it.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, -1)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, -1)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, -1)

    #
    # Misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_concatenation(self):
        v2 = u'0123456789' * 25
        v3 = u'9876543210' * 25
        value = v2 + 'x' + v3

        self.cursor.execute("create table t1(c2 varchar(250), c3 varchar(250))")
        self.cursor.execute("insert into t1(c2, c3) values (?,?)", v2, v3)

        row = self.cursor.execute("select c2 + 'x' + c3 from t1").fetchone()

        self.assertEqual(row[0], value)


    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(CNXNSTRING, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('dbfile argument required')

    if args[0].endswith('.accdb'):
        driver = 'Microsoft Access Driver (*.mdb, *.accdb)'
    else:
        driver = 'Microsoft Access Driver (*.mdb)'

    global CNXNSTRING
    CNXNSTRING = 'DRIVER={%s};DBQ=%s;ExtendedAnsiSQL=1' % (driver, abspath(args[0]))

    cnxn = pyodbc.connect(CNXNSTRING)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(AccessTestCase, options.test)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.
    add_to_path()
    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = dbapi20
#!/usr/bin/env python
''' Python DB API 2.0 driver compliance unit test suite. 
    
    This software is Public Domain and may be used without restrictions.

 "Now we have booze and barflies entering the discussion, plus rumours of
  DBAs on drugs... and I won't tell you what flashes through my mind each
  time I read the subject line with 'Anal Compliance' in it.  All around
  this is turning out to be a thoroughly unwholesome unit test."

    -- Ian Bicking
'''

__rcs_id__  = '$Id: dbapi20.py,v 1.10 2003/10/09 03:14:14 zenzen Exp $'
__version__ = '$Revision: 1.10 $'[11:-2]
__author__ = 'Stuart Bishop <zen@shangri-la.dropbear.id.au>'

import unittest
import time

# $Log: dbapi20.py,v $
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that cursor.arraysize
# defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception heirarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#

class DatabaseAPI20Test(unittest.TestCase):
    ''' Test a database self.driver for DB API 2.0 compatibility.
        This implementation tests Gadfly, but the TestCase
        is structured so that other self.drivers can subclass this 
        test case to ensure compiliance with the DB-API. It is 
        expected that this TestCase may be expanded in the future
        if ambiguities or edge conditions are discovered.

        The 'Optional Extensions' are not yet being tested.

        self.drivers should subclass this test, overriding setUp, tearDown,
        self.driver, connect_args and connect_kw_args. Class specification
        should be as follows:

        import dbapi20 
        class mytest(dbapi20.DatabaseAPI20Test):
           [...] 

        Don't 'import DatabaseAPI20Test from dbapi20', or you will
        confuse the unit tester - just 'import dbapi20'.
    '''

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = () # List of arguments to pass to connect
    connect_kw_args = {} # Keyword arguments for connect
    table_prefix = 'dbapi20test_' # If you need to specify a prefix for tables

    ddl1 = 'create table %sbooze (name varchar(20))' % table_prefix
    ddl2 = 'create table %sbarflys (name varchar(20))' % table_prefix
    xddl1 = 'drop table %sbooze' % table_prefix
    xddl2 = 'drop table %sbarflys' % table_prefix

    lowerfunc = 'lower' # Name of stored procedure to convert string->lowercase
        
    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self,cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self,cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        ''' self.drivers should override this method to perform required setup
            if any is necessary, such as creating the database.
        '''
        pass

    def tearDown(self):
        ''' self.drivers should override this method to perform required cleanup
            if any is necessary, such as deleting the test database.
            The default drops the tables that may be created.
        '''
        con = self._connect()
        try:
            cur = con.cursor()
            for i, ddl in enumerate((self.xddl1,self.xddl2)):
                try: 
                    cur.execute(ddl)
                    con.commit()
                except self.driver.Error: 
                    # Assume table didn't exist. Other tests will check if
                    # execute is busted.
                    pass
        finally:
            con.close()

    def _connect(self):
        try:
            return self.driver.connect(
                *self.connect_args,**self.connect_kw_args
                )
        except AttributeError:
            self.fail("No connect method found in self.driver module")

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel,'2.0')
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.failUnless(threadsafety in (0,1,2,3))
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.failUnless(paramstyle in (
                'qmark','numeric','named','format','pyformat'
                ))
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        self.failUnless(issubclass(self.driver.Warning,StandardError))
        self.failUnless(issubclass(self.driver.Error,StandardError))
        self.failUnless(
            issubclass(self.driver.InterfaceError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.DatabaseError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.OperationalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.IntegrityError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.InternalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.ProgrammingError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.NotSupportedError,self.driver.Error)
            )

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        con = self._connect()
        drv = self.driver
        self.failUnless(con.Warning is drv.Warning)
        self.failUnless(con.Error is drv.Error)
        self.failUnless(con.InterfaceError is drv.InterfaceError)
        self.failUnless(con.DatabaseError is drv.DatabaseError)
        self.failUnless(con.OperationalError is drv.OperationalError)
        self.failUnless(con.IntegrityError is drv.IntegrityError)
        self.failUnless(con.InternalError is drv.InternalError)
        self.failUnless(con.ProgrammingError is drv.ProgrammingError)
        self.failUnless(con.NotSupportedError is drv.NotSupportedError)


    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con,'rollback'):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass
    
    def test_cursor(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze),1)
            self.assertEqual(len(booze[0]),1)
            self.assertEqual(booze[0][0],'Victoria Bitter')
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.description,None,
                'cursor.description should be none after executing a '
                'statement that can return no rows (such as DDL)'
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(len(cur.description),1,
                'cursor.description describes too many columns'
                )
            self.assertEqual(len(cur.description[0]),7,
                'cursor.description[x] tuples must have 7 elements'
                )
            self.assertEqual(cur.description[0][0].lower(),'name',
                'cursor.description[x][0] must return column name'
                )
            self.assertEqual(cur.description[0][1],self.driver.STRING,
                'cursor.description[x][1] must return column type. Got %r'
                    % cur.description[0][1]
                )

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(cur.description,None,
                'cursor.description not being set to None when executing '
                'no-result statements (eg. DDL)'
                )
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount should be -1 after executing no-result '
                'statements'
                )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement'
                )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount not being reset to -1 after executing '
                'no-result statements'
                )
        finally:
            con.close()

    lower_func = 'lower'
    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur,'callproc'):
                r = cur.callproc(self.lower_func,('FOO',))
                self.assertEqual(len(r),1)
                self.assertEqual(r[0],'FOO')
                r = cur.fetchall()
                self.assertEqual(len(r),1,'callproc produced no result set')
                self.assertEqual(len(r[0]),1,
                    'callproc produced invalid result set'
                    )
                self.assertEqual(r[0][0],'foo',
                    'callproc produced invalid results'
                    )
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error,self.executeDDL1,cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error,con.commit)

        # connection.close should raise an Error if called more than once
        self.assertRaises(self.driver.Error,con.close)

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self,cur):
        self.executeDDL1(cur)
        cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
            self.table_prefix
            ))
        self.failUnless(cur.rowcount in (-1,1))

        if self.driver.paramstyle == 'qmark':
            cur.execute(
                'insert into %sbooze values (?)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'numeric':
            cur.execute(
                'insert into %sbooze values (:1)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'named':
            cur.execute(
                'insert into %sbooze values (:beer)' % self.table_prefix, 
                {'beer':"Cooper's"}
                )
        elif self.driver.paramstyle == 'format':
            cur.execute(
                'insert into %sbooze values (%%s)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'pyformat':
            cur.execute(
                'insert into %sbooze values (%%(beer)s)' % self.table_prefix,
                {'beer':"Cooper's"}
                )
        else:
            self.fail('Invalid paramstyle')
        self.failUnless(cur.rowcount in (-1,1))

        cur.execute('select name from %sbooze' % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(len(res),2,'cursor.fetchall returned too few rows')
        beers = [res[0][0],res[1][0]]
        beers.sort()
        self.assertEqual(beers[0],"Cooper's",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )
        self.assertEqual(beers[1],"Victoria Bitter",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [ ("Cooper's",) , ("Boag's",) ]
            margs = [ {'beer': "Cooper's"}, {'beer': "Boag's"} ]
            if self.driver.paramstyle == 'qmark':
                cur.executemany(
                    'insert into %sbooze values (?)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'numeric':
                cur.executemany(
                    'insert into %sbooze values (:1)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'named':
                cur.executemany(
                    'insert into %sbooze values (:beer)' % self.table_prefix,
                    margs
                    )
            elif self.driver.paramstyle == 'format':
                cur.executemany(
                    'insert into %sbooze values (%%s)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'pyformat':
                cur.executemany(
                    'insert into %sbooze values (%%(beer)s)' % (
                        self.table_prefix
                        ),
                    margs
                    )
            else:
                self.fail('Unknown paramstyle')
            self.failUnless(cur.rowcount in (-1,2),
                'insert using cursor.executemany set cursor.rowcount to '
                'incorrect value %r' % cur.rowcount
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(len(res),2,
                'cursor.fetchall retrieved incorrect number of rows'
                )
            beers = [res[0][0],res[1][0]]
            beers.sort()
            self.assertEqual(beers[0],"Boag's",'incorrect data retrieved')
            self.assertEqual(beers[1],"Cooper's",'incorrect data retrieved')
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error,cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if no more rows available'
                )
            self.failUnless(cur.rowcount in (-1,1))
        finally:
            con.close()

    samples = [
        'Carlton Cold',
        'Carlton Draft',
        'Mountain Goat',
        'Redback',
        'Victoria Bitter',
        'XXXX'
        ]

    def _populate(self):
        ''' Return a list of sql commands to setup the DB for the fetch
            tests.
        '''
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix,s) 
                for s in self.samples
            ]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            #issuing a query
            self.assertRaises(self.driver.Error,cur.fetchmany,4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(len(r),1,
                'cursor.fetchmany retrieved incorrect number of rows, '
                'default of arraysize is one.'
                )
            cur.arraysize=10
            r = cur.fetchmany(3) # Should get 3 rows
            self.assertEqual(len(r),3,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should get 2 more
            self.assertEqual(len(r),2,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should be an empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence after '
                'results are exhausted'
            )
            self.failUnless(cur.rowcount in (-1,6))

            # Same as above, using cursor.arraysize
            cur.arraysize=4
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany() # Should get 4 rows
            self.assertEqual(len(r),4,
                'cursor.arraysize not being honoured by fetchmany'
                )
            r = cur.fetchmany() # Should get 2 more
            self.assertEqual(len(r),2)
            r = cur.fetchmany() # Should be an empty sequence
            self.assertEqual(len(r),0)
            self.failUnless(cur.rowcount in (-1,6))

            cur.arraysize=6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany() # Should get all rows
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows),6)
            self.assertEqual(len(rows),6)
            rows = [r[0] for r in rows]
            rows.sort()
          
            # Make sure we get the right data back out
            for i in range(0,6):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved by cursor.fetchmany'
                    )

            rows = cur.fetchmany() # Should return an empty list
            self.assertEqual(len(rows),0,
                'cursor.fetchmany should return an empty sequence if '
                'called after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,6))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany() # Should get empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,len(self.samples)))
            self.assertEqual(len(rows),len(self.samples),
                'cursor.fetchall did not retrieve all rows'
                )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                'cursor.fetchall retrieved incorrect rows'
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )
            
        finally:
            con.close()
    
    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows1  = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4  = cur.fetchone()
            rows56 = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows23),2,
                'fetchmany returned incorrect number of rows'
                )
            self.assertEqual(len(rows56),2,
                'fetchall returned incorrect number of rows'
                )

            rows = [rows1[0]]
            rows.extend([rows23[0][0],rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0],rows56[1][0]])
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved or inserted'
                    )
        finally:
            con.close()

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the 
	    number of rows in booze then "name from booze"
        '''
        raise NotImplementedError,'Helper not implemented'
        #sql="""
        #    create procedure deleteme as
        #    begin
        #        select count(*) from booze
        #        select name from booze
        #    end
        #"""
        #cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        raise NotImplementedError,'Helper not implemented'
        #cur.execute("drop procedure deleteme")

    def test_nextset(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur,'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql=self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows=cur.fetchone()
                assert numberofrows[0]== len(self.samples)
                assert cur.nextset()
                names=cur.fetchall()
                assert len(names) == len(self.samples)
                s=cur.nextset()
                assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    def test_nextset(self):
        raise NotImplementedError,'Drivers need to override this test'

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.failUnless(hasattr(cur,'arraysize'),
                'cursor.arraysize must be defined'
                )
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes( (25,) )
            self._paraminsert(cur) # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000,0)
            self._paraminsert(cur) # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError,'Driver need to override this test'

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute('insert into %sbooze values (NULL)' % self.table_prefix)
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r),1)
            self.assertEqual(len(r[0]),1)
            self.assertEqual(r[0][0],None,'NULL value not returned as None')
        finally:
            con.close()

    def test_Date(self):
        d1 = self.driver.Date(2002,12,25)
        d2 = self.driver.DateFromTicks(time.mktime((2002,12,25,0,0,0,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        t1 = self.driver.Time(13,45,30)
        t2 = self.driver.TimeFromTicks(time.mktime((2001,1,1,13,45,30,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        t1 = self.driver.Timestamp(2002,12,25,13,45,30)
        t2 = self.driver.TimestampFromTicks(
            time.mktime((2002,12,25,13,45,30,0,0,0))
            )
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        b = self.driver.Binary('Something')
        b = self.driver.Binary('')

    def test_STRING(self):
        self.failUnless(hasattr(self.driver,'STRING'),
            'module.STRING must be defined'
            )

    def test_BINARY(self):
        self.failUnless(hasattr(self.driver,'BINARY'),
            'module.BINARY must be defined.'
            )

    def test_NUMBER(self):
        self.failUnless(hasattr(self.driver,'NUMBER'),
            'module.NUMBER must be defined.'
            )

    def test_DATETIME(self):
        self.failUnless(hasattr(self.driver,'DATETIME'),
            'module.DATETIME must be defined.'
            )

    def test_ROWID(self):
        self.failUnless(hasattr(self.driver,'ROWID'),
            'module.ROWID must be defined.'
            )


########NEW FILE########
__FILENAME__ = dbapitests

import unittest
from testutils import *
import dbapi20

def main():
    add_to_path()
    import pyodbc

    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] connection_string")
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")

    (options, args) = parser.parse_args()
    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('dbapitests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    class test_pyodbc(dbapi20.DatabaseAPI20Test):
        driver = pyodbc
        connect_args = [ connection_string ]
        connect_kw_args = {}
    
        def test_nextset(self): pass
        def test_setoutputsize(self): pass
        def test_ExceptionsAsConnectionAttributes(self): pass
    
    suite = unittest.makeSuite(test_pyodbc, 'test')
    testRunner = unittest.TextTestRunner(verbosity=(options.verbose > 1) and 9 or 0)
    result = testRunner.run(suite)

if __name__ == '__main__':
    main()
    

########NEW FILE########
__FILENAME__ = exceltests
#!/usr/bin/python

# Tests for reading from Excel files.
#
# I have not been able to successfully create or modify Excel files.

import sys, os, re
import unittest
from os.path import abspath
from testutils import *

CNXNSTRING = None

class ExcelTestCase(unittest.TestCase):

    def __init__(self, method_name):
        unittest.TestCase.__init__(self, method_name)

    def setUp(self):
        self.cnxn   = pyodbc.connect(CNXNSTRING, autocommit=True)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))
     
    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))
     
    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))
     
    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))


    def test_read_sheet(self):
        # The first method of reading data is to access worksheets by name in this format [name$].
        #
        # Our second sheet is named Sheet2 and has two columns.  The first has values 10, 20, 30, etc.

        rows = self.cursor.execute("select * from [Sheet2$]").fetchall()
        self.assertEquals(len(rows), 5)

        for index, row in enumerate(rows):
            self.assertEquals(row.s2num, float(index + 1) * 10)

    def test_read_range(self):
        # The second method of reading data is to assign a name to a range of cells and access that as a table.
        #
        # Our first worksheet has a section named Table1.  The first column has values 1, 2, 3, etc.

        rows = self.cursor.execute("select * from Table1").fetchall()
        self.assertEquals(len(rows), 10)
     
        for index, row in enumerate(rows):
            self.assertEquals(row.num, float(index + 1))
            self.assertEquals(row.val, chr(ord('a') + index))

    def test_tables(self):
        # This is useful for figuring out what is available
        tables = [ row.table_name for row in self.cursor.tables() ]
        assert 'Sheet2$' in tables, 'tables: %s' % ' '.join(tables)


    # def test_append(self):
    #     rows = self.cursor.execute("select s2num, s2val from [Sheet2$]").fetchall()
    #  
    #     print rows
    #  
    #     nextnum = max([ row.s2num for row in rows ]) + 10
    #     
    #     self.cursor.execute("insert into [Sheet2$](s2num, s2val) values (?, 'z')", nextnum)
    #  
    #     row = self.cursor.execute("select s2num, s2val from [Sheet2$] where s2num=?", nextnum).fetchone()
    #     self.assertTrue(row)
    #  
    #     print 'added:', nextnum, len(rows), 'rows'
    #  
    #     self.assertEquals(row.s2num, nextnum)
    #     self.assertEquals(row.s2val, 'z')
    #  
    #     self.cnxn.commit()


def main():
    from optparse import OptionParser
    parser = OptionParser() #usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if args:
        parser.error('no arguments expected')
    
    global CNXNSTRING

    path = dirname(abspath(__file__))
    filename = join(path, 'test.xls')
    assert os.path.exists(filename)
    CNXNSTRING = 'Driver={Microsoft Excel Driver (*.xls)};DBQ=%s;READONLY=FALSE' % filename

    cnxn = pyodbc.connect(CNXNSTRING, autocommit=True)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(ExcelTestCase, options.test)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.
    add_to_path()
    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = informixtests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for Informix DB.  To use, pass a connection string as the parameter.
The tests will create and drop tables t1 and t2 as necessary.

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

You can also put the connection string into a setup.cfg file in the root of the project
(the same one setup.py would use) like so:

  [informixtests]
  connection-string=DRIVER={IBM INFORMIX ODBC DRIVER (64-bit)};SERVER=localhost;UID=uid;PWD=pwd;DATABASE=db
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class InformixTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ unicode(s) for s in ANSI_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        for i in range(3):
            try:
                self.cursor.execute("drop procedure proc%d" % i)
                self.cnxn.commit()
            except:
                pass

        try:
            self.cursor.execute('drop function func1')
            self.cnxn.commit()
        except:
            pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def test_noscan(self):
        self.assertEqual(self.cursor.noscan, False)
        self.cursor.noscan = True
        self.assertEqual(self.cursor.noscan, True)

    def test_guid(self):
        self.cursor.execute("create table t1(g1 uniqueidentifier)")
        self.cursor.execute("insert into t1 values (newid())")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), 36)

    def test_nextset(self):
        self.cursor.execute("create table t1(i int)")
        for i in range(4):
            self.cursor.execute("insert into t1(i) values(?)", i)

        self.cursor.execute("select i from t1 where i < 2 order by i; select i from t1 where i >= 2 order by i")
        
        for i, row in enumerate(self.cursor):
            self.assertEqual(i, row.i)

        self.assertEqual(self.cursor.nextset(), True)

        for i, row in enumerate(self.cursor):
            self.assertEqual(i + 2, row.i)

    def test_fixed_unicode(self):
        value = u"t\xebsting"
        self.cursor.execute("create table t1(s nchar(7))")
        self.cursor.execute("insert into t1 values(?)", u"t\xebsting")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), unicode)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)


    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

        # Reported by Andy Hochhaus in the pyodbc group: In 2.1.7 and earlier, a hardcoded length of 255 was used to
        # determine whether a parameter was bound as a SQL_VARCHAR or SQL_LONGVARCHAR.  Apparently SQL Server chokes if
        # we bind as a SQL_LONGVARCHAR and the target column size is 8000 or less, which is considers just SQL_VARCHAR.
        # This means binding a 256 character value would cause problems if compared with a VARCHAR column under
        # 8001. We now use SQLGetTypeInfo to determine the time to switch.
        #
        # [42000] [Microsoft][SQL Server Native Client 10.0][SQL Server]The data types varchar and text are incompatible in the equal to operator.

        self.cursor.execute("select * from t1 where s=?", value)


    def _test_strliketype(self, sqltype, value, colsize=None):
        """
        The implementation for text, image, ntext, and binary.

        These types do not support comparison operators.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)


    #
    # varchar
    #

    def test_varchar_null(self):
        self._test_strtype('varchar', None, 100)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, len(value))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_varchar_%s' % len(value)] = _maketest(value)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3, len(c1) as l1, len(c2) as l2, len(c3) as l3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)

    def test_varchar_upperlatin(self):
        self._test_strtype('varchar', 'á')

    #
    # unicode
    #

    def test_unicode_null(self):
        self._test_strtype('nvarchar', None, 100)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('nvarchar', value, len(value))
        return t
    for value in UNICODE_FENCEPOSTS:
        locals()['test_unicode_%s' % len(value)] = _maketest(value)

    def test_unicode_upperlatin(self):
        self._test_strtype('varchar', 'á')

    #
    # binary
    #

    def test_null_binary(self):
        self._test_strtype('varbinary', None, 100)
     
    def test_large_null_binary(self):
        # Bug 1575064
        self._test_strtype('varbinary', None, 4000)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), len(value))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_binary_%s' % len(value)] = _maketest(value)

    #
    # image
    #

    def test_image_null(self):
        self._test_strliketype('image', None)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('image', buffer(value))
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_image_%s' % len(value)] = _maketest(value)

    def test_image_upperlatin(self):
        self._test_strliketype('image', buffer('á'))

    #
    # text
    #

    # def test_empty_text(self):
    #     self._test_strliketype('text', buffer(''))

    def test_null_text(self):
        self._test_strliketype('text', None)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strliketype('text', value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_text_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strliketype('text', 'á')

    #
    # bit
    #

    def test_bit(self):
        value = True
        self.cursor.execute("create table t1(b bit)")
        self.cursor.execute("insert into t1 values (?)", value)
        v = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(v), bool)
        self.assertEqual(v, value)

    #
    # decimal
    #

    def _decimal(self, precision, scale, negative):
        # From test provided by planders (thanks!) in Issue 91

        self.cursor.execute("create table t1(d decimal(%s, %s))" % (precision, scale))

        # Construct a decimal that uses the maximum precision and scale.
        decStr = '9' * (precision - scale)
        if scale:
            decStr = decStr + "." + '9' * scale
        if negative:
            decStr = "-" + decStr
        value = Decimal(decStr)

        self.cursor.execute("insert into t1 values(?)", value)

        v = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(v, value)

    def _maketest(p, s, n):
        def t(self):
            self._decimal(p, s, n)
        return t
    for (p, s, n) in [ (1,  0,  False),
                       (1,  0,  True),
                       (6,  0,  False),
                       (6,  2,  False),
                       (6,  4,  True),
                       (6,  6,  True),
                       (38, 0,  False),
                       (38, 10, False),
                       (38, 38, False),
                       (38, 0,  True),
                       (38, 10, True),
                       (38, 38, True) ]:
        locals()['test_decimal_%s_%s_%s' % (p, s, n and 'n' or 'p')] = _maketest(p, s, n)


    def test_decimal_e(self):
        """Ensure exponential notation decimals are properly handled"""
        value = Decimal((0, (1, 2, 3), 5)) # prints as 1.23E+7
        self.cursor.execute("create table t1(d decimal(10, 2))")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(result, value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_empty_unicode(self):
        self.cursor.execute("create table t1(s nvarchar(20))")
        self.cursor.execute("insert into t1 values(?)", u"")

    def test_unicode_query(self):
        self.cursor.execute(u"select 1")
        
    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    def test_datetime_fraction(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds, so the most granular datetime
        # supported is xxx000.

        value = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(result, value)

    def test_datetime_fraction_rounded(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds.  pyodbc rounds down to what the
        # database supports.

        full    = datetime(2007, 1, 15, 3, 4, 5, 123456)
        rounded = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", full)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(result), datetime)
        self.assertEquals(result, rounded)

    def test_date(self):
        value = date.today()
     
        self.cursor.execute("create table t1(d date)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEquals(type(value), date)
        self.assertEquals(value, result)

    def test_time(self):
        value = datetime.now().time()
        
        # We aren't yet writing values using the new extended time type so the value written to the database is only
        # down to the second.
        value = value.replace(microsecond=0)
         
        self.cursor.execute("create table t1(t time)")
        self.cursor.execute("insert into t1 values (?)", value)
         
        result = self.cursor.execute("select t from t1").fetchone()[0]
        self.assertEquals(type(value), time)
        self.assertEquals(value, result)

    def test_datetime2(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime2)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):
        input = 3000000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    #
    # stored procedures
    #

    # def test_callproc(self):
    #     "callproc with a simple input-only stored procedure"
    #     pass

    def test_sp_results(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              select top 10 name, id, xtype, refdate
              from sysobjects
            """)
        rows = self.cursor.execute("exec proc1").fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_temp(self):

        # Note: I've used "set nocount on" so that we don't get the number of rows deleted from #tmptable.
        # If you don't do this, you'd need to call nextset() once to skip it.

        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              select top 10 name, id, xtype, refdate
              into #tmptable
              from sysobjects

              select * from #tmptable
            """)
        self.cursor.execute("exec proc1")
        self.assert_(self.cursor.description is not None)
        self.assert_(len(self.cursor.description) == 4)

        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_vartbl(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              declare @tmptbl table(name varchar(100), id int, xtype varchar(4), refdate datetime)

              insert into @tmptbl
              select top 10 name, id, xtype, refdate
              from sysobjects

              select * from @tmptbl
            """)
        self.cursor.execute("exec proc1")
        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)

    def test_sp_with_dates(self):
        # Reported in the forums that passing two datetimes to a stored procedure doesn't work.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@d1 datetime, @d2 datetime)
            AS
              declare @d as int
              set @d = datediff(year, @d1, @d2)
              select @d
            """)
        self.cursor.execute("exec test_sp ?, ?", datetime.now(), datetime.now())
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == 0)   # 0 years apart

    def test_sp_with_none(self):
        # Reported in the forums that passing None caused an error.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@x varchar(20))
            AS
              declare @y varchar(20)
              set @y = @x
              select @y
            """)
        self.cursor.execute("exec test_sp ?", None)
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == None)   # 0 years apart
        

    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount, but SQL Server 2005 returns -1 after a
        select statement, so we'll test for that behavior.  This is valid behavior according to the DB API
        specification, but people don't seem to like it.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, -1)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, -1)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, -1)

    #
    # always return Cursor
    #

    # In the 2.0.x branch, Cursor.execute sometimes returned the cursor and sometimes the rowcount.  This proved very
    # confusing when things went wrong and added very little value even when things went right since users could always
    # use: cursor.execute("...").rowcount

    def test_retcursor_delete(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_select(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("select * from t1")
        self.assertEquals(v, self.cursor)

    #
    # misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()

        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_temp_select(self):
        # A project was failing to create temporary tables via select into.
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")

        self.cursor.execute("select s into t2 from t1")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")


    def test_money(self):
        d = Decimal('123456.78')
        self.cursor.execute("create table t1(i int identity(1,1), m money)")
        self.cursor.execute("insert into t1(m) values (?)", d)
        v = self.cursor.execute("select m from t1").fetchone()[0]
        self.assertEqual(v, d)


    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_concatenation(self):
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(300), c3 varchar(300))")
        self.cursor.execute("insert into t1(c2, c3) values (?,?)", v2, v3)

        row = self.cursor.execute("select c2, c3, c2 + c3 as both from t1").fetchone()

        self.assertEqual(row.both, v2 + v3)

    def test_view_select(self):
        # Reported in forum: Can't select from a view?  I think I do this a lot, but another test never hurts.

        # Create a table (t1) with 3 rows and a view (t2) into it.
        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(50))")
        for i in range(3):
            self.cursor.execute("insert into t1(c2) values (?)", "string%s" % i)
        self.cursor.execute("create view t2 as select * from t1")

        # Select from the view
        self.cursor.execute("select * from t2")
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(len(rows) == 3)

    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)

    def test_unicode_results(self):
        "Ensure unicode_results forces Unicode"
        othercnxn = pyodbc.connect(self.connection_string, unicode_results=True)
        othercursor = othercnxn.cursor()

        # ANSI data in an ANSI column ...
        othercursor.execute("create table t1(s varchar(20))")
        othercursor.execute("insert into t1 values(?)", 'test')

        # ... should be returned as Unicode
        value = othercursor.execute("select s from t1").fetchone()[0]
        self.assertEqual(value, u'test')


    def test_informix_callproc(self):
        try:
            self.cursor.execute("drop procedure pyodbctest")
            self.cnxn.commit()
        except:
            pass

        self.cursor.execute("create table t1(s varchar(10))")
        self.cursor.execute("insert into t1 values(?)", "testing")

        self.cursor.execute("""
                            create procedure pyodbctest @var1 varchar(32)
                            as 
                            begin 
                              select s 
                              from t1 
                            return 
                            end
                            """)
        self.cnxn.commit()

        # for row in self.cursor.procedureColumns('pyodbctest'):
        #     print row.procedure_name, row.column_name, row.column_type, row.type_name

        self.cursor.execute("exec pyodbctest 'hi'")

        # print self.cursor.description
        # for row in self.cursor:
        #     print row.s

    def test_skip(self):
        # Insert 1, 2, and 3.  Fetch 1, skip 2, fetch 3.

        self.cursor.execute("create table t1(id int)");
        for i in range(1, 5):
            self.cursor.execute("insert into t1 values(?)", i)
        self.cursor.execute("select id from t1 order by id")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.cursor.skip(2)
        self.assertEqual(self.cursor.fetchone()[0], 4)

    def test_timeout(self):
        self.assertEqual(self.cnxn.timeout, 0) # defaults to zero (off)

        self.cnxn.timeout = 30
        self.assertEqual(self.cnxn.timeout, 30)

        self.cnxn.timeout = 0
        self.assertEqual(self.cnxn.timeout, 0)

    def test_sets_execute(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.execute("insert into t1 (word) VALUES (?)", [words])

        self.assertRaises(pyodbc.ProgrammingError, f)

    def test_sets_executemany(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.executemany("insert into t1 (word) values (?)", [words])
            
        self.assertRaises(TypeError, f)

    def test_row_execute(self):
        "Ensure we can use a Row object as a parameter to execute"
        self.cursor.execute("create table t1(n int, s varchar(10))")
        self.cursor.execute("insert into t1 values (1, 'a')")
        row = self.cursor.execute("select n, s from t1").fetchone()
        self.assertNotEqual(row, None)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.execute("insert into t2 values (?, ?)", row)
        
    def test_row_executemany(self):
        "Ensure we can use a Row object as a parameter to executemany"
        self.cursor.execute("create table t1(n int, s varchar(10))")

        for i in range(3):
            self.cursor.execute("insert into t1 values (?, ?)", i, chr(ord('a')+i))

        rows = self.cursor.execute("select n, s from t1").fetchall()
        self.assertNotEqual(len(rows), 0)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.executemany("insert into t2 values (?, ?)", rows)
        
    def test_description(self):
        "Ensure cursor.description is correct"

        self.cursor.execute("create table t1(n int, s varchar(8), d decimal(5,2))")
        self.cursor.execute("insert into t1 values (1, 'abc', '1.23')")
        self.cursor.execute("select * from t1")

        # (I'm not sure the precision of an int is constant across different versions, bits, so I'm hand checking the
        # items I do know.

        # int
        t = self.cursor.description[0]
        self.assertEqual(t[0], 'n')
        self.assertEqual(t[1], int)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # varchar(8)
        t = self.cursor.description[1]
        self.assertEqual(t[0], 's')
        self.assertEqual(t[1], str)
        self.assertEqual(t[4], 8)       # precision
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # decimal(5, 2)
        t = self.cursor.description[2]
        self.assertEqual(t[0], 'd')
        self.assertEqual(t[1], Decimal)
        self.assertEqual(t[4], 5)       # precision
        self.assertEqual(t[5], 2)       # scale
        self.assertEqual(t[6], True)    # nullable

        
    def test_none_param(self):
        "Ensure None can be used for params other than the first"
        # Some driver/db versions would fail if NULL was not the first parameter because SQLDescribeParam (only used
        # with NULL) could not be used after the first call to SQLBindParameter.  This means None always worked for the
        # first column, but did not work for later columns.
        #
        # If SQLDescribeParam doesn't work, pyodbc would use VARCHAR which almost always worked.  However,
        # binary/varbinary won't allow an implicit conversion.

        self.cursor.execute("create table t1(n int, blob varbinary(max))")
        self.cursor.execute("insert into t1 values (1, newid())")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 1)
        self.assertEqual(type(row.blob), buffer)

        self.cursor.execute("update t1 set n=?, blob=?", 2, None)
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 2)
        self.assertEqual(row.blob, None)


    def test_output_conversion(self):
        def convert(value):
            # `value` will be a string.  We'll simply add an X at the beginning at the end.
            return 'X' + value + 'X'
        self.cnxn.add_output_converter(pyodbc.SQL_VARCHAR, convert)
        self.cursor.execute("create table t1(n int, v varchar(10))")
        self.cursor.execute("insert into t1 values (1, '123.45')")
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, 'X123.45X')

        # Now clear the conversions and try again.  There should be no Xs this time.
        self.cnxn.clear_output_converters()
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, '123.45')


    def test_too_large(self):
        """Ensure error raised if insert fails due to truncation"""
        value = 'x' * 1000
        self.cursor.execute("create table t1(s varchar(800))")
        def test():
            self.cursor.execute("insert into t1 values (?)", value)
        self.assertRaises(pyodbc.DataError, test)

    def test_geometry_null_insert(self):
        def convert(value):
            return value

        self.cnxn.add_output_converter(-151, convert) # -151 is SQL Server's geometry
        self.cursor.execute("create table t1(n int, v geometry)")
        self.cursor.execute("insert into t1 values (?, ?)", 1, None)
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, None)
        self.cnxn.clear_output_converters()

    def test_login_timeout(self):
        # This can only test setting since there isn't a way to cause it to block on the server side.
        cnxns = pyodbc.connect(self.connection_string, timeout=2)

    def test_row_equal(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test')")
        row1 = self.cursor.execute("select n, s from t1").fetchone()
        row2 = self.cursor.execute("select n, s from t1").fetchone()
        b = (row1 == row2)
        self.assertEqual(b, True)

    def test_row_gtlt(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test1')")
        self.cursor.execute("insert into t1 values (1, 'test2')")
        rows = self.cursor.execute("select n, s from t1 order by s").fetchall()
        self.assert_(rows[0] < rows[1])
        self.assert_(rows[0] <= rows[1])
        self.assert_(rows[1] > rows[0])
        self.assert_(rows[1] >= rows[0])
        self.assert_(rows[0] != rows[1])

        rows = list(rows)
        rows.sort() # uses <
        
    def test_context_manager(self):
        with pyodbc.connect(self.connection_string) as cnxn:
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)

        # The connection should be closed now.
        def test():
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assertRaises(pyodbc.ProgrammingError, test)

    def test_untyped_none(self):
        # From issue 129
        value = self.cursor.execute("select ?", None).fetchone()[0]
        self.assertEqual(value, None)
        
    def test_large_update_nodata(self):
        self.cursor.execute('create table t1(a varbinary(max))')
        hundredkb = buffer('x'*100*1024)
        self.cursor.execute('update t1 set a=? where 1=0', (hundredkb,))

    def test_func_param(self):
        self.cursor.execute('''
                            create function func1 (@testparam varchar(4)) 
                            returns @rettest table (param varchar(4))
                            as 
                            begin
                                insert @rettest
                                select @testparam
                                return
                            end
                            ''')
        self.cnxn.commit()
        value = self.cursor.execute("select * from func1(?)", 'test').fetchone()[0]
        self.assertEquals(value, 'test')
        
    def test_no_fetch(self):
        # Issue 89 with FreeTDS: Multiple selects (or catalog functions that issue selects) without fetches seem to
        # confuse the driver.
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')

    def test_drivers(self):
        drivers = pyodbc.drivers()
        self.assertEqual(list, type(drivers))
        self.assert_(len(drivers) > 1)

        m = re.search('DRIVER={([^}]+)}', self.connection_string, re.IGNORECASE)
        current = m.group(1)
        self.assert_(current in drivers)
            


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('informixtests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(InformixTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = mysqltests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for MySQL.  To use, pass a connection string as the parameter.  The tests will create and drop tables t1 and
t2 as necessary.  The default installation of mysql allows you to connect locally with no password and already contains
a 'test' database, so you can probably use the following.  (Update the driver name as appropriate.)

  ./mysqltests DRIVER={MySQL};DATABASE=test

These tests use the pyodbc library from the build directory, not the version installed in your
Python directories.  You must run `python setup.py build` before running these tests.
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath, basename
from testutils import *

_TESTSTR = b'0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of composed of `seed` to make a string `length` characters long.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = int((length + len(_TESTSTR)-1) / len(_TESTSTR))
    v = _TESTSTR * c
    return v[:length]

class MySqlTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    ANSI_FENCEPOSTS    = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    UNICODE_FENCEPOSTS = [ s.decode('utf8') for s in ANSI_FENCEPOSTS ]
    BLOB_FENCEPOSTS   = ANSI_FENCEPOSTS + [ _generate_test_string(size) for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        for i in range(3):
            try:
                self.cursor.execute("drop procedure proc%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        try:
            self.cursor.execute(sql)
        except:
            print('>>>>', sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]

        # Removing this check for now until I get the charset working properly.
        # If we use latin1, results are 'str' instead of 'unicode', which would be
        # correct.  Setting charset to ucs-2 causes a crash in SQLGetTypeInfo(SQL_DATETIME).
        # self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

    #
    # varchar
    #

    def test_varchar_null(self):
        self._test_strtype('varchar', None, 100)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, max(1, len(value)))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_varchar_%s' % len(value)] = _maketest(value)

    # Generate a test using Unicode.
    for value in UNICODE_FENCEPOSTS:
        locals()['test_wvarchar_%s' % len(value)] = _maketest(value)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)

    def test_varchar_upperlatin(self):
        self._test_strtype('varchar', 'á', colsize=3)

    #
    # binary
    #

    def test_null_binary(self):
        self._test_strtype('varbinary', None, 100)
     
    def test_large_null_binary(self):
        # Bug 1575064
        self._test_strtype('varbinary', None, 4000)

    # Generate a test for each fencepost size: test_binary_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varbinary', buffer(value), max(1, len(value)))
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_binary_%s' % len(value)] = _maketest(value)

    #
    # blob
    #

    def test_blob_null(self):
        self._test_strtype('blob', None)

    # Generate a test for each fencepost size: test_blob_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('blob', buffer(value))
        return t
    for value in BLOB_FENCEPOSTS:
        locals()['test_blob_%s' % len(value)] = _maketest(value)

    def test_blob_upperlatin(self):
        self._test_strtype('blob', buffer('á'))

    #
    # text
    #

    def test_null_text(self):
        self._test_strtype('text', None)

    # Generate a test for each fencepost size: test_text_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('text', value)
        return t
    for value in ANSI_FENCEPOSTS:
        locals()['test_text_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strtype('text', 'á')

    #
    # unicode
    #

    def test_unicode_query(self):
        self.cursor.execute(u"select 1")

    #
    # bit
    #

    # The MySQL driver maps BIT colums to the ODBC bit data type, but they aren't behaving quite like a Boolean value
    # (which is what the ODBC bit data type really represents).  The MySQL BOOL data type is just an alias for a small
    # integer, so pyodbc can't recognize it and map it back to True/False.
    #
    # You can use both BIT and BOOL and they will act as you expect if you treat them as integers.  You can write 0 and
    # 1 to them and they will work.

    # def test_bit(self):
    #     value = True
    #     self.cursor.execute("create table t1(b bit)")
    #     self.cursor.execute("insert into t1 values (?)", value)
    #     v = self.cursor.execute("select b from t1").fetchone()[0]
    #     self.assertEqual(type(v), bool)
    #     self.assertEqual(v, value)
    #  
    # def test_bit_string_true(self):
    #     self.cursor.execute("create table t1(b bit)")
    #     self.cursor.execute("insert into t1 values (?)", "xyzzy")
    #     v = self.cursor.execute("select b from t1").fetchone()[0]
    #     self.assertEqual(type(v), bool)
    #     self.assertEqual(v, True)
    #  
    # def test_bit_string_false(self):
    #     self.cursor.execute("create table t1(b bit)")
    #     self.cursor.execute("insert into t1 values (?)", "")
    #     v = self.cursor.execute("select b from t1").fetchone()[0]
    #     self.assertEqual(type(v), bool)
    #     self.assertEqual(v, False)
    
    #
    # decimal
    #

    def test_small_decimal(self):
        # value = Decimal('1234567890987654321')
        value = Decimal('100010')       # (I use this because the ODBC docs tell us how the bytes should look in the C struct)
        self.cursor.execute("create table t1(d numeric(19))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_small_decimal_scale(self):
        # The same as small_decimal, except with a different scale.  This value exactly matches the ODBC documentation
        # example in the C Data Types appendix.
        value = '1000.10'
        value = Decimal(value)
        self.cursor.execute("create table t1(d numeric(20,6))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_negative_decimal_scale(self):
        value = Decimal('-10.0010')
        self.cursor.execute("create table t1(d numeric(19,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(value, result)

    def test_date(self):
        value = date(2001, 1, 1)

        self.cursor.execute("create table t1(dt date)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(result), type(value))
        self.assertEquals(result, value)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):

        # This fails on 64-bit Fedora with 5.1.
        # Should return 0x0123456789
        # Does return   0x0000000000
        #
        # Top 4 bytes are returned as 0x00 00 00 00.  If the input is high enough, they are returned as 0xFF FF FF FF.
        input = 0x123456789
        print('writing %x' % input)
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.5
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    def test_date(self):
        value = date.today()
     
        self.cursor.execute("create table t1(d date)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEquals(value, result)


    def test_time(self):
        value = datetime.now().time()
        
        # We aren't yet writing values using the new extended time type so the value written to the database is only
        # down to the second.
        value = value.replace(microsecond=0)
         
        self.cursor.execute("create table t1(t time)")
        self.cursor.execute("insert into t1 values (?)", value)
         
        result = self.cursor.execute("select t from t1").fetchone()[0]
        self.assertEquals(value, result)

    #
    # misc
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount.  Databases can return the actual rowcount
        or they can return -1 if it would help performance.  MySQL seems to always return the correct rowcount.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, count)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        # The Python DB API says that rowcount should be set to -1 and most ODBC drivers let us know there are no
        # records.  MySQL always returns 0, however.  Without parsing the SQL (which we are not going to do), I'm not
        # sure how we can tell the difference and set the value to -1.  For now, I'll have this test check for 0.

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    # REVIEW: The following fails.  Research.

    # def test_executemany_failure(self):
    #     """
    #     Ensure that an exception is raised if one query in an executemany fails.
    #     """
    #     self.cursor.execute("create table t1(a int, b varchar(10))")
    #  
    #     params = [ (1, 'good'),
    #                ('error', 'not an int'),
    #                (3, 'good') ]
    #     
    #     self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", default=0, action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        filename = basename(sys.argv[0])
        assert filename.endswith('.py')
        connection_string = load_setup_connection_string(filename[:-3])

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(MySqlTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = pgtests
#!/usr/bin/python

# Unit tests for PostgreSQL on Linux (Fedora)
# This is a stripped down copy of the SQL Server tests.

from __future__ import print_function

import sys, os, re
import unittest
from decimal import Decimal
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of composed of `seed` to make a string `length` characters long.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = int((length + len(_TESTSTR)-1) / len(_TESTSTR))
    v = _TESTSTR * c
    return v[:length]

class PGTestCase(unittest.TestCase):

    # These are from the C++ code.  Keep them up to date.

    # If we are reading a binary, string, or unicode value and do not know how large it is, we'll try reading 2K into a
    # buffer on the stack.  We then copy into a new Python object.
    SMALL_READ  = 2048

    # A read guaranteed not to fit in the MAX_STACK_STACK stack buffer, but small enough to be used for varchar (4K max).
    LARGE_READ = 4000

    SMALL_STRING = _generate_test_string(SMALL_READ)
    LARGE_STRING = _generate_test_string(LARGE_READ)

    def __init__(self, connection_string, ansi, method_name):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string
        self.ansi = ansi

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string, ansi=self.ansi)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass
        
        self.cnxn.rollback()


    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, long)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))


    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

    #
    # varchar
    #

    def test_empty_varchar(self):
        self._test_strtype('varchar', '', self.SMALL_READ)

    def test_null_varchar(self):
        self._test_strtype('varchar', None, self.SMALL_READ)

    def test_large_null_varchar(self):
        # There should not be a difference, but why not find out?
        self._test_strtype('varchar', None, self.LARGE_READ)

    def test_small_varchar(self):
        self._test_strtype('varchar', self.SMALL_STRING, self.SMALL_READ)

    def test_large_varchar(self):
        self._test_strtype('varchar', self.LARGE_STRING, self.LARGE_READ)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)



    def test_small_decimal(self):
        # value = Decimal('1234567890987654321')
        value = Decimal('100010')       # (I use this because the ODBC docs tell us how the bytes should look in the C struct)
        self.cursor.execute("create table t1(d numeric(19))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_small_decimal_scale(self):
        # The same as small_decimal, except with a different scale.  This value exactly matches the ODBC documentation
        # example in the C Data Types appendix.
        value = '1000.10'
        value = Decimal(value)
        self.cursor.execute("create table t1(d numeric(20,6))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def test_negative_decimal_scale(self):
        value = Decimal('-10.0010')
        self.cursor.execute("create table t1(d numeric(19,4))")
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), Decimal)
        self.assertEqual(v, value)


    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, 4)

    # PostgreSQL driver fails here?
    # def test_rowcount_reset(self):
    #     "Ensure rowcount is reset to -1"
    # 
    #     self.cursor.execute("create table t1(i int)")
    #     count = 4
    #     for i in range(count):
    #         self.cursor.execute("insert into t1 values (?)", i)
    #     self.assertEquals(self.cursor.rowcount, 1)
    # 
    #     self.cursor.execute("create table t2(i int)")
    #     self.assertEquals(self.cursor.rowcount, -1)

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        # REVIEW: Without the cast, we get the following error:
        # [07006] [unixODBC]Received an unsupported type from Postgres.;\nERROR:  table "t2" does not exist (14)

        count = self.cursor.execute("select cast(count(*) as int) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


def main():
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog [options] connection_string")
    parser.add_option("-v", "--verbose", default=0, action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")
    parser.add_option('-a', '--ansi', help='ANSI only', default=False, action='store_true')

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('pgtests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    if options.verbose:
        cnxn = pyodbc.connect(connection_string, ansi=options.ansi)
        print_library_info(cnxn)
        # print 'library:', os.path.abspath(pyodbc.__file__)
        # print 'odbc:    %s' % cnxn.getinfo(pyodbc.SQL_ODBC_VER)
        # print 'driver:  %s %s' % (cnxn.getinfo(pyodbc.SQL_DRIVER_NAME), cnxn.getinfo(pyodbc.SQL_DRIVER_VER))
        # print 'driver supports ODBC version %s' % cnxn.getinfo(pyodbc.SQL_DRIVER_ODBC_VER)
        # print 'unicode:', pyodbc.UNICODE_SIZE, 'sqlwchar:', pyodbc.SQLWCHAR_SIZE
        cnxn.close()

    if options.test:
        # Run a single test
        if not options.test.startswith('test_'):
            options.test = 'test_%s' % (options.test)

        s = unittest.TestSuite([ PGTestCase(connection_string, options.ansi, options.test) ])
    else:
        # Run all tests in the class

        methods = [ m for m in dir(PGTestCase) if m.startswith('test_') ]
        methods.sort()
        s = unittest.TestSuite([ PGTestCase(connection_string, options.ansi, m) for m in methods ])

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(s)

if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = sqlitetests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for SQLite using the ODBC driver from http://www.ch-werner.de/sqliteodbc

To use, pass a connection string as the parameter. The tests will create and
drop tables t1 and t2 as necessary.  On Windows, use the 32-bit driver with
32-bit Python and the 64-bit driver with 64-bit Python (regardless of your
operating system bitness).

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

You can also put the connection string into a setup.cfg file in the root of the project
(the same one setup.py would use) like so:

  [sqlitetests]
  connection-string=Driver=SQLite3 ODBC Driver;Database=sqlite.db
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) // len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class SqliteTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    STR_FENCEPOSTS = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    BYTE_FENCEPOSTS    = [ bytes(s, 'ascii') for s in STR_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = BYTE_FENCEPOSTS + [ bytes(_generate_test_string(size), 'ascii') for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def get_sqlite_version(self):
        """
        Returns the major version: 8-->2000, 9-->2005, 10-->2008
        """
        self.cursor.execute("exec master..xp_msver 'ProductVersion'")
        row = self.cursor.fetchone()
        return int(row.Character_Value.split('.', 1)[0])

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, int))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def _test_strtype(self, sqltype, value, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

        # Reported by Andy Hochhaus in the pyodbc group: In 2.1.7 and earlier, a hardcoded length of 255 was used to
        # determine whether a parameter was bound as a SQL_VARCHAR or SQL_LONGVARCHAR.  Apparently SQL Server chokes if
        # we bind as a SQL_LONGVARCHAR and the target column size is 8000 or less, which is considers just SQL_VARCHAR.
        # This means binding a 256 character value would cause problems if compared with a VARCHAR column under
        # 8001. We now use SQLGetTypeInfo to determine the time to switch.
        #
        # [42000] [Microsoft][SQL Server Native Client 10.0][SQL Server]The data types varchar and text are incompatible in the equal to operator.

        self.cursor.execute("select * from t1 where s=?", value)


    def _test_strliketype(self, sqltype, value, colsize=None):
        """
        The implementation for text, image, ntext, and binary.

        These types do not support comparison operators.
        """
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), type(value))

        if value is not None:
            self.assertEqual(len(v), len(value))

        self.assertEqual(v, value)

    #
    # text
    #

    def test_text_null(self):
        self._test_strtype('text', None, 100)

    # Generate a test for each fencepost size: test_text_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('text', value, len(value))
        return t
    for value in STR_FENCEPOSTS:
        locals()['test_text_%s' % len(value)] = _maketest(value)

    def test_text_upperlatin(self):
        self._test_strtype('varchar', 'á')

    #
    # blob
    #

    def test_null_blob(self):
        self._test_strtype('blob', None, 100)
     
    def test_large_null_blob(self):
        # Bug 1575064
        self._test_strtype('blob', None, 4000)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('blob', bytearray(value), len(value))
        return t
    for value in BYTE_FENCEPOSTS:
        locals()['test_blob_%s' % len(value)] = _maketest(value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):
        input = 3000000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_negative_bigint(self):
        # Issue 186: BIGINT problem on 32-bit architeture
        input = -430000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)

    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, count)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, count)

    # Fails.  Not terribly important so I'm going to comment out for now and report to the ODBC driver writer.
    # def test_rowcount_reset(self):
    #     "Ensure rowcount is reset to -1"
    #     self.cursor.execute("create table t1(i int)")
    #     count = 4
    #     for i in range(count):
    #         self.cursor.execute("insert into t1 values (?)", i)
    #     self.assertEquals(self.cursor.rowcount, 1)
    #  
    #     self.cursor.execute("create table t2(i int)")
    #     self.assertEquals(self.cursor.rowcount, -1)

    #
    # always return Cursor
    #

    # In the 2.0.x branch, Cursor.execute sometimes returned the cursor and sometimes the rowcount.  This proved very
    # confusing when things went wrong and added very little value even when things went right since users could always
    # use: cursor.execute("...").rowcount

    def test_retcursor_delete(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_select(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("select * from t1")
        self.assertEquals(v, self.cursor)

    #
    # misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()

        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_view_select(self):
        # Reported in forum: Can't select from a view?  I think I do this a lot, but another test never hurts.

        # Create a table (t1) with 3 rows and a view (t2) into it.
        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(50))")
        for i in range(3):
            self.cursor.execute("insert into t1(c2) values (?)", "string%s" % i)
        self.cursor.execute("create view t2 as select * from t1")

        # Select from the view
        self.cursor.execute("select * from t2")
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(len(rows) == 3)

    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)

        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)

        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)

    def test_skip(self):
        # Insert 1, 2, and 3.  Fetch 1, skip 2, fetch 3.

        self.cursor.execute("create table t1(id int)");
        for i in range(1, 5):
            self.cursor.execute("insert into t1 values(?)", i)
        self.cursor.execute("select id from t1 order by id")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.cursor.skip(2)
        self.assertEqual(self.cursor.fetchone()[0], 4)

    def test_sets_execute(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.execute("insert into t1 (word) VALUES (?)", [words])

        self.assertRaises(pyodbc.ProgrammingError, f)

    def test_sets_executemany(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.executemany("insert into t1 (word) values (?)", [words])
            
        self.assertRaises(TypeError, f)

    def test_row_execute(self):
        "Ensure we can use a Row object as a parameter to execute"
        self.cursor.execute("create table t1(n int, s varchar(10))")
        self.cursor.execute("insert into t1 values (1, 'a')")
        row = self.cursor.execute("select n, s from t1").fetchone()
        self.assertNotEqual(row, None)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.execute("insert into t2 values (?, ?)", row)
        
    def test_row_executemany(self):
        "Ensure we can use a Row object as a parameter to executemany"
        self.cursor.execute("create table t1(n int, s varchar(10))")

        for i in range(3):
            self.cursor.execute("insert into t1 values (?, ?)", i, chr(ord('a')+i))

        rows = self.cursor.execute("select n, s from t1").fetchall()
        self.assertNotEqual(len(rows), 0)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.executemany("insert into t2 values (?, ?)", rows)
        
    def test_description(self):
        "Ensure cursor.description is correct"

        self.cursor.execute("create table t1(n int, s text)")
        self.cursor.execute("insert into t1 values (1, 'abc')")
        self.cursor.execute("select * from t1")

        # (I'm not sure the precision of an int is constant across different versions, bits, so I'm hand checking the
        # items I do know.

        # int
        t = self.cursor.description[0]
        self.assertEqual(t[0], 'n')
        self.assertEqual(t[1], int)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # text
        t = self.cursor.description[1]
        self.assertEqual(t[0], 's')
        self.assertEqual(t[1], str)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

    def test_row_equal(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test')")
        row1 = self.cursor.execute("select n, s from t1").fetchone()
        row2 = self.cursor.execute("select n, s from t1").fetchone()
        b = (row1 == row2)
        self.assertEqual(b, True)

    def test_row_gtlt(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test1')")
        self.cursor.execute("insert into t1 values (1, 'test2')")
        rows = self.cursor.execute("select n, s from t1 order by s").fetchall()
        self.assert_(rows[0] < rows[1])
        self.assert_(rows[0] <= rows[1])
        self.assert_(rows[1] > rows[0])
        self.assert_(rows[1] >= rows[0])
        self.assert_(rows[0] != rows[1])

        rows = list(rows)
        rows.sort() # uses <
        
    def test_context_manager(self):
        with pyodbc.connect(self.connection_string) as cnxn:
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)

        # The connection should be closed now.
        def test():
            cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assertRaises(pyodbc.ProgrammingError, test)

    def test_untyped_none(self):
        # From issue 129
        value = self.cursor.execute("select ?", None).fetchone()[0]
        self.assertEqual(value, None)
        
    def test_large_update_nodata(self):
        self.cursor.execute('create table t1(a blob)')
        hundredkb = bytearray('x'*100*1024)
        self.cursor.execute('update t1 set a=? where 1=0', (hundredkb,))

    def test_no_fetch(self):
        # Issue 89 with FreeTDS: Multiple selects (or catalog functions that issue selects) without fetches seem to
        # confuse the driver.
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')

def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('sqlitetests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(SqliteTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = sqlservertests
#!/usr/bin/python
# -*- coding: latin-1 -*-

usage = """\
usage: %prog [options] connection_string

Unit tests for SQL Server.  To use, pass a connection string as the parameter.
The tests will create and drop tables t1 and t2 as necessary.

These run using the version from the 'build' directory, not the version
installed into the Python directories.  You must run python setup.py build
before running the tests.

You can also put the connection string into a setup.cfg file in the root of the project
(the same one setup.py would use) like so:

  [sqlservertests]
  connection-string=DRIVER={SQL Server};SERVER=localhost;UID=uid;PWD=pwd;DATABASE=db

The connection string above will use the 2000/2005 driver, even if SQL Server 2008
is installed:

  2000: DRIVER={SQL Server}
  2005: DRIVER={SQL Server}
  2008: DRIVER={SQL Server Native Client 10.0}
"""

import sys, os, re
import unittest
from decimal import Decimal
from datetime import datetime, date, time
from os.path import join, getsize, dirname, abspath
from testutils import *

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = int((length + len(_TESTSTR)-1) / len(_TESTSTR))
    v = _TESTSTR * c
    return v[:length]

class SqlServerTestCase(unittest.TestCase):

    SMALL_FENCEPOST_SIZES = [ 0, 1, 255, 256, 510, 511, 512, 1023, 1024, 2047, 2048, 4000 ]
    LARGE_FENCEPOST_SIZES = [ 4095, 4096, 4097, 10 * 1024, 20 * 1024 ]

    STR_FENCEPOSTS = [ _generate_test_string(size) for size in SMALL_FENCEPOST_SIZES ]
    BYTE_FENCEPOSTS    = [ bytes(s, 'ascii') for s in STR_FENCEPOSTS ]
    IMAGE_FENCEPOSTS   = BYTE_FENCEPOSTS + [ bytes(_generate_test_string(size), 'ascii') for size in LARGE_FENCEPOST_SIZES ]

    def __init__(self, method_name, connection_string):
        unittest.TestCase.__init__(self, method_name)
        self.connection_string = connection_string

    def get_sqlserver_version(self):
        """
        Returns the major version: 8-->2000, 9-->2005, 10-->2008
        """
        self.cursor.execute("exec master..xp_msver 'ProductVersion'")
        row = self.cursor.fetchone()
        return int(row.Character_Value.split('.', 1)[0])

    def setUp(self):
        self.cnxn   = pyodbc.connect(self.connection_string)
        self.cursor = self.cnxn.cursor()

        for i in range(3):
            try:
                self.cursor.execute("drop table t%d" % i)
                self.cnxn.commit()
            except:
                pass

        for i in range(3):
            try:
                self.cursor.execute("drop procedure proc%d" % i)
                self.cnxn.commit()
            except:
                pass

        try:
            self.cursor.execute('drop function func1')
            self.cnxn.commit()
        except:
            pass

        self.cnxn.rollback()

    def tearDown(self):
        try:
            self.cursor.close()
            self.cnxn.close()
        except:
            # If we've already closed the cursor or connection, exceptions are thrown.
            pass

    def test_multiple_bindings(self):
        "More than one bind and select on a cursor"
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t1 values (?)", 2)
        self.cursor.execute("insert into t1 values (?)", 3)
        for i in range(3):
            self.cursor.execute("select n from t1 where n < ?", 10)
            self.cursor.execute("select n from t1 where n < 3")
        

    def test_different_bindings(self):
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("create table t2(d datetime)")
        self.cursor.execute("insert into t1 values (?)", 1)
        self.cursor.execute("insert into t2 values (?)", datetime.now())

    def test_datasources(self):
        p = pyodbc.dataSources()
        self.assert_(isinstance(p, dict))

    def test_getinfo_string(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CATALOG_NAME_SEPARATOR)
        self.assert_(isinstance(value, str))

    def test_getinfo_bool(self):
        value = self.cnxn.getinfo(pyodbc.SQL_ACCESSIBLE_TABLES)
        self.assert_(isinstance(value, bool))

    def test_getinfo_int(self):
        value = self.cnxn.getinfo(pyodbc.SQL_DEFAULT_TXN_ISOLATION)
        self.assert_(isinstance(value, (int, int)))

    def test_getinfo_smallint(self):
        value = self.cnxn.getinfo(pyodbc.SQL_CONCAT_NULL_BEHAVIOR)
        self.assert_(isinstance(value, int))

    def test_noscan(self):
        self.assertEqual(self.cursor.noscan, False)
        self.cursor.noscan = True
        self.assertEqual(self.cursor.noscan, True)

    def test_guid(self):
        self.cursor.execute("create table t1(g1 uniqueidentifier)")
        self.cursor.execute("insert into t1 values (newid())")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), 36)

    def test_nextset(self):
        self.cursor.execute("create table t1(i int)")
        for i in range(4):
            self.cursor.execute("insert into t1(i) values(?)", i)

        self.cursor.execute("select i from t1 where i < 2 order by i; select i from t1 where i >= 2 order by i")
        
        for i, row in enumerate(self.cursor):
            self.assertEqual(i, row.i)

        self.assertEqual(self.cursor.nextset(), True)

        for i, row in enumerate(self.cursor):
            self.assertEqual(i + 2, row.i)

    def test_fixed_unicode(self):
        value = "t\xebsting"
        self.cursor.execute("create table t1(s nchar(7))")
        self.cursor.execute("insert into t1 values(?)", "t\xebsting")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)


    def _test_strtype(self, sqltype, value, resulttype=None, colsize=None):
        """
        The implementation for string, Unicode, and binary tests.
        """
        assert colsize is None or isinstance(colsize, int), colsize
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        if resulttype is None:
            resulttype = type(value)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), resulttype)

        if value is not None:
            self.assertEqual(len(v), len(value))

        # To allow buffer --> db --> bytearray tests, always convert the input to the expected result type before
        # comparing.
        if type(value) is not resulttype:
            value = resulttype(value)

        self.assertEqual(v, value)


    def _test_strliketype(self, sqltype, value, resulttype=None, colsize=None):
        """
        The implementation for text, image, ntext, and binary.

        These types do not support comparison operators.
        """
        assert colsize is None or isinstance(colsize, int), colsize
        assert colsize is None or (value is None or colsize >= len(value))

        if colsize:
            sql = "create table t1(s %s(%s))" % (sqltype, colsize)
        else:
            sql = "create table t1(s %s)" % sqltype

        if resulttype is None:
            resulttype = type(value)

        self.cursor.execute(sql)
        self.cursor.execute("insert into t1 values(?)", value)
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), resulttype)

        if value is not None:
            self.assertEqual(len(v), len(value))

        # To allow buffer --> db --> bytearray tests, always convert the input to the expected result type before
        # comparing.
        if type(value) is not resulttype:
            value = resulttype(value)

        self.assertEqual(v, value)


    #
    # varchar
    #

    def test_varchar_null(self):
        self._test_strtype('varchar', None, colsize=100)

    # Generate a test for each fencepost size: test_varchar_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('varchar', value, colsize=len(value))
        return t
    for value in STR_FENCEPOSTS:
        locals()['test_varchar_%s' % len(value)] = _maketest(value)

    def test_varchar_many(self):
        self.cursor.execute("create table t1(c1 varchar(300), c2 varchar(300), c3 varchar(300))")

        v1 = 'ABCDEFGHIJ' * 30
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("insert into t1(c1, c2, c3) values (?,?,?)", v1, v2, v3);
        row = self.cursor.execute("select c1, c2, c3, len(c1) as l1, len(c2) as l2, len(c3) as l3 from t1").fetchone()

        self.assertEqual(v1, row.c1)
        self.assertEqual(v2, row.c2)
        self.assertEqual(v3, row.c3)

    #
    # unicode
    #

    def test_unicode_null(self):
        self._test_strtype('nvarchar', None, colsize=100)

    # Generate a test for each fencepost size: test_unicode_0, etc.
    def _maketest(value):
        def t(self):
            self._test_strtype('nvarchar', value, colsize=len(value))
        return t
    for value in STR_FENCEPOSTS:
        locals()['test_unicode_%s' % len(value)] = _maketest(value)

    def test_unicode_longmax(self):
        # Issue 188:	Segfault when fetching NVARCHAR(MAX) data over 511 bytes

        ver = self.get_sqlserver_version()
        if ver < 9:            # 2005+
            return              # so pass / ignore
        self.cursor.execute("select cast(replicate(N'x', 512) as nvarchar(max))")

    #
    # binary
    #

    def test_binary_null(self):
        self._test_strtype('varbinary', None, colsize=100)
     
    # bytearray
        
    def _maketest(value):
        def t(self):
                self._test_strtype('varbinary', bytearray(value), colsize=len(value))
        return t
    for value in BYTE_FENCEPOSTS:
        locals()['test_binary_bytearray_%s' % len(value)] = _maketest(value)

    # bytes
        
    def _maketest(value):
        def t(self):
                self._test_strtype('varbinary', bytes(value), resulttype=bytearray, colsize=len(value))
        return t
    for value in BYTE_FENCEPOSTS:
        locals()['test_binary_bytes_%s' % len(value)] = _maketest(value)

    #
    # image
    #

    def test_image_null(self):
        self._test_strliketype('image', None)

    # bytearray

    def _maketest(value):
        def t(self):
            self._test_strliketype('image', bytearray(value))
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_image_bytearray_%s' % len(value)] = _maketest(value)

    # bytes

    def _maketest(value):
        def t(self):
            self._test_strliketype('image', bytes(value), resulttype=bytearray)
        return t
    for value in IMAGE_FENCEPOSTS:
        locals()['test_image_bytes_%s' % len(value)] = _maketest(value)

    #
    # text
    #

    def test_null_text(self):
        self._test_strliketype('text', None)

    def _maketest(value):
        def t(self):
            self._test_strliketype('text', value)
        return t
    for value in STR_FENCEPOSTS:
        locals()['test_text_%s' % len(value)] = _maketest(value)

    #
    # bit
    #

    def test_bit(self):
        value = True
        self.cursor.execute("create table t1(b bit)")
        self.cursor.execute("insert into t1 values (?)", value)
        v = self.cursor.execute("select b from t1").fetchone()[0]
        self.assertEqual(type(v), bool)
        self.assertEqual(v, value)

    #
    # decimal
    #

    def _decimal(self, precision, scale, negative):
        # From test provided by planders (thanks!) in Issue 91

        self.cursor.execute("create table t1(d decimal(%s, %s))" % (precision, scale))

        # Construct a decimal that uses the maximum precision and scale.
        decStr = '9' * (precision - scale)
        if scale:
            decStr = decStr + "." + '9' * scale
        if negative:
            decStr = "-" + decStr

        value = Decimal(decStr)

        self.cursor.execute("insert into t1 values(?)", value)

        v = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(v, value)

    def _maketest(p, s, n):
        def t(self):
            self._decimal(p, s, n)
        return t
    for (p, s, n) in [ (1,  0,  False),
                       (1,  0,  True),
                       (6,  0,  False),
                       (6,  2,  False),
                       (6,  4,  True),
                       (6,  6,  True),
                       (38, 0,  False),
                       (38, 10, False),
                       (38, 38, False),
                       (38, 0,  True),
                       (38, 10, True),
                       (38, 38, True) ]:
        locals()['test_decimal_%s_%s_%s' % (p, s, n and 'n' or 'p')] = _maketest(p, s, n)


    def test_decimal_e(self):
        """Ensure exponential notation decimals are properly handled"""
        value = Decimal((0, (1, 2, 3), 5)) # prints as 1.23E+7
        self.cursor.execute("create table t1(d decimal(10, 2))")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(result, value)

    def test_subquery_params(self):
        """Ensure parameter markers work in a subquery"""
        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        row = self.cursor.execute("""
                                  select x.id
                                  from (
                                    select id
                                    from t1
                                    where s = ?
                                      and id between ? and ?
                                   ) x
                                   """, 'test', 1, 10).fetchone()
        self.assertNotEqual(row, None)
        self.assertEqual(row[0], 1)

    def _exec(self):
        self.cursor.execute(self.sql)
        
    def test_close_cnxn(self):
        """Make sure using a Cursor after closing its connection doesn't crash."""

        self.cursor.execute("create table t1(id integer, s varchar(20))")
        self.cursor.execute("insert into t1 values (?,?)", 1, 'test')
        self.cursor.execute("select * from t1")

        self.cnxn.close()
        
        # Now that the connection is closed, we expect an exception.  (If the code attempts to use
        # the HSTMT, we'll get an access violation instead.)
        self.sql = "select * from t1"
        self.assertRaises(pyodbc.ProgrammingError, self._exec)

    def test_empty_string(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_fixed_str(self):
        value = "testing"
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(len(v), len(value)) # If we alloc'd wrong, the test below might work because of an embedded NULL
        self.assertEqual(v, value)

    def test_empty_unicode(self):
        self.cursor.execute("create table t1(s nvarchar(20))")
        self.cursor.execute("insert into t1 values(?)", "")

    def test_negative_row_index(self):
        self.cursor.execute("create table t1(s varchar(20))")
        self.cursor.execute("insert into t1 values(?)", "1")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEquals(row[0], "1")
        self.assertEquals(row[-1], "1")

    def test_version(self):
        self.assertEquals(3, len(pyodbc.version.split('.'))) # 1.3.1 etc.

    #
    # date, time, datetime
    #

    def test_datetime(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    def test_datetime_fraction(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds, so the most granular datetime
        # supported is xxx000.

        value = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(result, value)

    def test_datetime_fraction_rounded(self):
        # SQL Server supports milliseconds, but Python's datetime supports nanoseconds.  pyodbc rounds down to what the
        # database supports.

        full    = datetime(2007, 1, 15, 3, 4, 5, 123456)
        rounded = datetime(2007, 1, 15, 3, 4, 5, 123000)
     
        self.cursor.execute("create table t1(dt datetime)")
        self.cursor.execute("insert into t1 values (?)", full)
     
        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(result), datetime)
        self.assertEquals(result, rounded)

    def test_date(self):
        ver = self.get_sqlserver_version()
        if ver < 10:            # 2008 only
            return              # so pass / ignore

        value = date.today()
     
        self.cursor.execute("create table t1(d date)")
        self.cursor.execute("insert into t1 values (?)", value)
     
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEquals(type(value), date)
        self.assertEquals(value, result)

    def test_time(self):
        ver = self.get_sqlserver_version()
        if ver < 10:            # 2008 only
            return              # so pass / ignore

        value = datetime.now().time()
        
        # We aren't yet writing values using the new extended time type so the value written to the database is only
        # down to the second.
        value = value.replace(microsecond=0)
         
        self.cursor.execute("create table t1(t time)")
        self.cursor.execute("insert into t1 values (?)", value)
         
        result = self.cursor.execute("select t from t1").fetchone()[0]
        self.assertEquals(type(value), time)
        self.assertEquals(value, result)

    def test_datetime2(self):
        value = datetime(2007, 1, 15, 3, 4, 5)

        self.cursor.execute("create table t1(dt datetime2)")
        self.cursor.execute("insert into t1 values (?)", value)

        result = self.cursor.execute("select dt from t1").fetchone()[0]
        self.assertEquals(type(value), datetime)
        self.assertEquals(value, result)

    #
    # ints and floats
    #

    def test_int(self):
        value = 1234
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_int(self):
        value = -1
        self.cursor.execute("create table t1(n int)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_bigint(self):
        input = 3000000000
        self.cursor.execute("create table t1(d bigint)")
        self.cursor.execute("insert into t1 values (?)", input)
        result = self.cursor.execute("select d from t1").fetchone()[0]
        self.assertEqual(result, input)

    def test_float(self):
        value = 1234.567
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEquals(result, value)

    def test_negative_float(self):
        value = -200
        self.cursor.execute("create table t1(n float)")
        self.cursor.execute("insert into t1 values (?)", value)
        result  = self.cursor.execute("select n from t1").fetchone()[0]
        self.assertEqual(value, result)


    #
    # stored procedures
    #

    # def test_callproc(self):
    #     "callproc with a simple input-only stored procedure"
    #     pass

    def test_sp_results(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              select top 10 name, id, xtype, refdate
              from sysobjects
            """)
        rows = self.cursor.execute("exec proc1").fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_temp(self):

        # Note: I've used "set nocount on" so that we don't get the number of rows deleted from #tmptable.
        # If you don't do this, you'd need to call nextset() once to skip it.

        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              select top 10 name, id, xtype, refdate
              into #tmptable
              from sysobjects

              select * from #tmptable
            """)
        self.cursor.execute("exec proc1")
        self.assert_(self.cursor.description is not None)
        self.assert_(len(self.cursor.description) == 4)

        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)


    def test_sp_results_from_vartbl(self):
        self.cursor.execute(
            """
            Create procedure proc1
            AS
              set nocount on
              declare @tmptbl table(name varchar(100), id int, xtype varchar(4), refdate datetime)

              insert into @tmptbl
              select top 10 name, id, xtype, refdate
              from sysobjects

              select * from @tmptbl
            """)
        self.cursor.execute("exec proc1")
        rows = self.cursor.fetchall()
        self.assertEquals(type(rows), list)
        self.assertEquals(len(rows), 10) # there has to be at least 10 items in sysobjects
        self.assertEquals(type(rows[0].refdate), datetime)

    def test_sp_with_dates(self):
        # Reported in the forums that passing two datetimes to a stored procedure doesn't work.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@d1 datetime, @d2 datetime)
            AS
              declare @d as int
              set @d = datediff(year, @d1, @d2)
              select @d
            """)
        self.cursor.execute("exec test_sp ?, ?", datetime.now(), datetime.now())
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == 0)   # 0 years apart

    def test_sp_with_none(self):
        # Reported in the forums that passing None caused an error.
        self.cursor.execute(
            """
            if exists (select * from dbo.sysobjects where id = object_id(N'[test_sp]') and OBJECTPROPERTY(id, N'IsProcedure') = 1)
              drop procedure [dbo].[test_sp]
            """)
        self.cursor.execute(
            """
            create procedure test_sp(@x varchar(20))
            AS
              declare @y varchar(20)
              set @y = @x
              select @y
            """)
        self.cursor.execute("exec test_sp ?", None)
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(rows[0][0] == None)   # 0 years apart
        

    #
    # rowcount
    #

    def test_rowcount_delete(self):
        self.assertEquals(self.cursor.rowcount, -1)
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, count)

    def test_rowcount_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.  On the other hand, we could hardcode a
        zero return value.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        self.cursor.execute("delete from t1")
        self.assertEquals(self.cursor.rowcount, 0)

    def test_rowcount_select(self):
        """
        Ensure Cursor.rowcount is set properly after a select statement.

        pyodbc calls SQLRowCount after each execute and sets Cursor.rowcount, but SQL Server 2005 returns -1 after a
        select statement, so we'll test for that behavior.  This is valid behavior according to the DB API
        specification, but people don't seem to like it.
        """
        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.cursor.execute("select * from t1")
        self.assertEquals(self.cursor.rowcount, -1)

        rows = self.cursor.fetchall()
        self.assertEquals(len(rows), count)
        self.assertEquals(self.cursor.rowcount, -1)

    def test_rowcount_reset(self):
        "Ensure rowcount is reset to -1"

        self.cursor.execute("create table t1(i int)")
        count = 4
        for i in range(count):
            self.cursor.execute("insert into t1 values (?)", i)
        self.assertEquals(self.cursor.rowcount, 1)

        self.cursor.execute("create table t2(i int)")
        self.assertEquals(self.cursor.rowcount, -1)

    #
    # always return Cursor
    #

    # In the 2.0.x branch, Cursor.execute sometimes returned the cursor and sometimes the rowcount.  This proved very
    # confusing when things went wrong and added very little value even when things went right since users could always
    # use: cursor.execute("...").rowcount

    def test_retcursor_delete(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_nodata(self):
        """
        This represents a different code path than a delete that deleted something.

        The return value is SQL_NO_DATA and code after it was causing an error.  We could use SQL_NO_DATA to step over
        the code that errors out and drop down to the same SQLRowCount code.
        """
        self.cursor.execute("create table t1(i int)")
        # This is a different code path internally.
        v = self.cursor.execute("delete from t1")
        self.assertEquals(v, self.cursor)

    def test_retcursor_select(self):
        self.cursor.execute("create table t1(i int)")
        self.cursor.execute("insert into t1 values (1)")
        v = self.cursor.execute("select * from t1")
        self.assertEquals(v, self.cursor)

    #
    # misc
    #

    def test_lower_case(self):
        "Ensure pyodbc.lowercase forces returned column names to lowercase."

        # Has to be set before creating the cursor, so we must recreate self.cursor.

        pyodbc.lowercase = True
        self.cursor = self.cnxn.cursor()

        self.cursor.execute("create table t1(Abc int, dEf int)")
        self.cursor.execute("select * from t1")

        names = [ t[0] for t in self.cursor.description ]
        names.sort()

        self.assertEquals(names, [ "abc", "def" ])

        # Put it back so other tests don't fail.
        pyodbc.lowercase = False
        
    def test_row_description(self):
        """
        Ensure Cursor.description is accessible as Row.cursor_description.
        """
        self.cursor = self.cnxn.cursor()
        self.cursor.execute("create table t1(a int, b char(3))")
        self.cnxn.commit()
        self.cursor.execute("insert into t1 values(1, 'abc')")

        row = self.cursor.execute("select * from t1").fetchone()

        self.assertEquals(self.cursor.description, row.cursor_description)
        

    def test_temp_select(self):
        # A project was failing to create temporary tables via select into.
        self.cursor.execute("create table t1(s char(7))")
        self.cursor.execute("insert into t1 values(?)", "testing")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")

        self.cursor.execute("select s into t2 from t1")
        v = self.cursor.execute("select * from t1").fetchone()[0]
        self.assertEqual(type(v), str)
        self.assertEqual(v, "testing")


    def test_money(self):
        d = Decimal('123456.78')
        self.cursor.execute("create table t1(i int identity(1,1), m money)")
        self.cursor.execute("insert into t1(m) values (?)", d)
        v = self.cursor.execute("select m from t1").fetchone()[0]
        self.assertEqual(v, d)


    def test_executemany(self):
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (i, str(i)) for i in range(1, 6) ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])


    def test_executemany_one(self):
        "Pass executemany a single sequence"
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, "test") ]

        self.cursor.executemany("insert into t1(a, b) values (?,?)", params)

        count = self.cursor.execute("select count(*) from t1").fetchone()[0]
        self.assertEqual(count, len(params))

        self.cursor.execute("select a, b from t1 order by a")
        rows = self.cursor.fetchall()
        self.assertEqual(count, len(rows))

        for param, row in zip(params, rows):
            self.assertEqual(param[0], row[0])
            self.assertEqual(param[1], row[1])
        

    def test_executemany_failure(self):
        """
        Ensure that an exception is raised if one query in an executemany fails.
        """
        self.cursor.execute("create table t1(a int, b varchar(10))")

        params = [ (1, 'good'),
                   ('error', 'not an int'),
                   (3, 'good') ]
        
        self.failUnlessRaises(pyodbc.Error, self.cursor.executemany, "insert into t1(a, b) value (?, ?)", params)

        
    def test_row_slicing(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = row[:]
        self.failUnless(result is row)

        result = row[:-1]
        self.assertEqual(result, (1,2,3))

        result = row[0:4]
        self.failUnless(result is row)


    def test_row_repr(self):
        self.cursor.execute("create table t1(a int, b int, c int, d int)");
        self.cursor.execute("insert into t1 values(1,2,3,4)")

        row = self.cursor.execute("select * from t1").fetchone()

        result = str(row)
        self.assertEqual(result, "(1, 2, 3, 4)")

        result = str(row[:-1])
        self.assertEqual(result, "(1, 2, 3)")

        result = str(row[:1])
        self.assertEqual(result, "(1,)")


    def test_concatenation(self):
        v2 = '0123456789' * 30
        v3 = '9876543210' * 30

        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(300), c3 varchar(300))")
        self.cursor.execute("insert into t1(c2, c3) values (?,?)", v2, v3)

        row = self.cursor.execute("select c2, c3, c2 + c3 as both from t1").fetchone()

        self.assertEqual(row.both, v2 + v3)

    def test_view_select(self):
        # Reported in forum: Can't select from a view?  I think I do this a lot, but another test never hurts.

        # Create a table (t1) with 3 rows and a view (t2) into it.
        self.cursor.execute("create table t1(c1 int identity(1, 1), c2 varchar(50))")
        for i in range(3):
            self.cursor.execute("insert into t1(c2) values (?)", "string%s" % i)
        self.cursor.execute("create view t2 as select * from t1")

        # Select from the view
        self.cursor.execute("select * from t2")
        rows = self.cursor.fetchall()
        self.assert_(rows is not None)
        self.assert_(len(rows) == 3)

    def test_autocommit(self):
        self.assertEqual(self.cnxn.autocommit, False)
        othercnxn = pyodbc.connect(self.connection_string, autocommit=True)
        self.assertEqual(othercnxn.autocommit, True)
        othercnxn.autocommit = False
        self.assertEqual(othercnxn.autocommit, False)

    def test_unicode_results(self):
        "Ensure unicode_results forces Unicode"
        othercnxn = pyodbc.connect(self.connection_string, unicode_results=True)
        othercursor = othercnxn.cursor()

        # ANSI data in an ANSI column ...
        othercursor.execute("create table t1(s varchar(20))")
        othercursor.execute("insert into t1 values(?)", 'test')

        # ... should be returned as Unicode
        value = othercursor.execute("select s from t1").fetchone()[0]
        self.assertEqual(value, 'test')


    def test_sqlserver_callproc(self):
        try:
            self.cursor.execute("drop procedure pyodbctest")
            self.cnxn.commit()
        except:
            pass

        self.cursor.execute("create table t1(s varchar(10))")
        self.cursor.execute("insert into t1 values(?)", "testing")

        self.cursor.execute("""
                            create procedure pyodbctest @var1 varchar(32)
                            as 
                            begin 
                              select s 
                              from t1 
                            return 
                            end
                            """)
        self.cnxn.commit()

        # for row in self.cursor.procedureColumns('pyodbctest'):
        #     print row.procedure_name, row.column_name, row.column_type, row.type_name

        self.cursor.execute("exec pyodbctest 'hi'")

        # print self.cursor.description
        # for row in self.cursor:
        #     print row.s

    def test_skip(self):
        # Insert 1, 2, and 3.  Fetch 1, skip 2, fetch 3.

        self.cursor.execute("create table t1(id int)");
        for i in range(1, 5):
            self.cursor.execute("insert into t1 values(?)", i)
        self.cursor.execute("select id from t1 order by id")
        self.assertEqual(self.cursor.fetchone()[0], 1)
        self.cursor.skip(2)
        self.assertEqual(self.cursor.fetchone()[0], 4)

    def test_timeout(self):
        self.assertEqual(self.cnxn.timeout, 0) # defaults to zero (off)

        self.cnxn.timeout = 30
        self.assertEqual(self.cnxn.timeout, 30)

        self.cnxn.timeout = 0
        self.assertEqual(self.cnxn.timeout, 0)

    def test_sets_execute(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.execute("insert into t1 (word) VALUES (?)", [words])

        self.assertRaises(pyodbc.ProgrammingError, f)

    def test_sets_executemany(self):
        # Only lists and tuples are allowed.
        def f():
            self.cursor.execute("create table t1 (word varchar (100))")
            words = set (['a'])
            self.cursor.executemany("insert into t1 (word) values (?)", [words])
            
        self.assertRaises(TypeError, f)

    def test_row_execute(self):
        "Ensure we can use a Row object as a parameter to execute"
        self.cursor.execute("create table t1(n int, s varchar(10))")
        self.cursor.execute("insert into t1 values (1, 'a')")
        row = self.cursor.execute("select n, s from t1").fetchone()
        self.assertNotEqual(row, None)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.execute("insert into t2 values (?, ?)", row)
        
    def test_row_executemany(self):
        "Ensure we can use a Row object as a parameter to executemany"
        self.cursor.execute("create table t1(n int, s varchar(10))")

        for i in range(3):
            self.cursor.execute("insert into t1 values (?, ?)", i, chr(ord('a')+i))

        rows = self.cursor.execute("select n, s from t1").fetchall()
        self.assertNotEqual(len(rows), 0)

        self.cursor.execute("create table t2(n int, s varchar(10))")
        self.cursor.executemany("insert into t2 values (?, ?)", rows)
        
    def test_description(self):
        "Ensure cursor.description is correct"

        self.cursor.execute("create table t1(n int, s varchar(8), d decimal(5,2))")
        self.cursor.execute("insert into t1 values (1, 'abc', '1.23')")
        self.cursor.execute("select * from t1")

        # (I'm not sure the precision of an int is constant across different versions, bits, so I'm hand checking the
        # items I do know.

        # int
        t = self.cursor.description[0]
        self.assertEqual(t[0], 'n')
        self.assertEqual(t[1], int)
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # varchar(8)
        t = self.cursor.description[1]
        self.assertEqual(t[0], 's')
        self.assertEqual(t[1], str)
        self.assertEqual(t[4], 8)       # precision
        self.assertEqual(t[5], 0)       # scale
        self.assertEqual(t[6], True)    # nullable

        # decimal(5, 2)
        t = self.cursor.description[2]
        self.assertEqual(t[0], 'd')
        self.assertEqual(t[1], Decimal)
        self.assertEqual(t[4], 5)       # precision
        self.assertEqual(t[5], 2)       # scale
        self.assertEqual(t[6], True)    # nullable

        
    def test_none_param(self):
        "Ensure None can be used for params other than the first"
        # Some driver/db versions would fail if NULL was not the first parameter because SQLDescribeParam (only used
        # with NULL) could not be used after the first call to SQLBindParameter.  This means None always worked for the
        # first column, but did not work for later columns.
        #
        # If SQLDescribeParam doesn't work, pyodbc would use VARCHAR which almost always worked.  However,
        # binary/varbinary won't allow an implicit conversion.

        self.cursor.execute("create table t1(n int, blob varbinary(max))")
        self.cursor.execute("insert into t1 values (1, newid())")
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 1)
        self.assertEqual(type(row.blob), bytearray)

        self.cursor.execute("update t1 set n=?, blob=?", 2, None)
        row = self.cursor.execute("select * from t1").fetchone()
        self.assertEqual(row.n, 2)
        self.assertEqual(row.blob, None)


    def test_output_conversion(self):
        def convert(value):
            # `value` will be a string.  We'll simply add an X at the beginning at the end.
            return 'X' + value + 'X'
        self.cnxn.add_output_converter(pyodbc.SQL_VARCHAR, convert)
        self.cursor.execute("create table t1(n int, v varchar(10))")
        self.cursor.execute("insert into t1 values (1, '123.45')")
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, 'X123.45X')

        # Now clear the conversions and try again.  There should be no Xs this time.
        self.cnxn.clear_output_converters()
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, '123.45')


    def test_too_large(self):
        """Ensure error raised if insert fails due to truncation"""
        value = 'x' * 1000
        self.cursor.execute("create table t1(s varchar(800))")
        def test():
            self.cursor.execute("insert into t1 values (?)", value)
        self.assertRaises(pyodbc.DataError, test)

    def test_geometry_null_insert(self):
        def convert(value):
            return value

        self.cnxn.add_output_converter(-151, convert) # -151 is SQL Server's geometry
        self.cursor.execute("create table t1(n int, v geometry)")
        self.cursor.execute("insert into t1 values (?, ?)", 1, None)
        value = self.cursor.execute("select v from t1").fetchone()[0]
        self.assertEqual(value, None)
        self.cnxn.clear_output_converters()

    def test_login_timeout(self):
        # This can only test setting since there isn't a way to cause it to block on the server side.
        cnxns = pyodbc.connect(self.connection_string, timeout=2)

    def test_row_equal(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test')")
        row1 = self.cursor.execute("select n, s from t1").fetchone()
        row2 = self.cursor.execute("select n, s from t1").fetchone()
        b = (row1 == row2)
        self.assertEqual(b, True)

    def test_row_gtlt(self):
        self.cursor.execute("create table t1(n int, s varchar(20))")
        self.cursor.execute("insert into t1 values (1, 'test1')")
        self.cursor.execute("insert into t1 values (1, 'test2')")
        rows = self.cursor.execute("select n, s from t1 order by s").fetchall()
        self.assert_(rows[0] < rows[1])
        self.assert_(rows[0] <= rows[1])
        self.assert_(rows[1] > rows[0])
        self.assert_(rows[1] >= rows[0])
        self.assert_(rows[0] != rows[1])

        rows = list(rows)
        rows.sort() # uses <
        
    def test_context_manager_success(self):

        self.cursor.execute("create table t1(n int)")
        self.cnxn.commit()

        try:
            with pyodbc.connect(self.connection_string) as cnxn:
                cursor = cnxn.cursor()
                cursor.execute("insert into t1 values (1)")
        except Exception:
            pass

        cnxn = None
        cursor = None

        rows = self.cursor.execute("select n from t1").fetchall()
        self.assertEquals(len(rows), 1)
        self.assertEquals(rows[0][0], 1)


    def test_untyped_none(self):
        # From issue 129
        value = self.cursor.execute("select ?", None).fetchone()[0]
        self.assertEqual(value, None)
        
    def test_large_update_nodata(self):
        self.cursor.execute('create table t1(a varbinary(max))')
        hundredkb = b'x'*100*1024
        self.cursor.execute('update t1 set a=? where 1=0', (hundredkb,))

    def test_func_param(self):
        self.cursor.execute('''
                            create function func1 (@testparam varchar(4)) 
                            returns @rettest table (param varchar(4))
                            as 
                            begin
                                insert @rettest
                                select @testparam
                                return
                            end
                            ''')
        self.cnxn.commit()
        value = self.cursor.execute("select * from func1(?)", 'test').fetchone()[0]
        self.assertEquals(value, 'test')
        
    def test_no_fetch(self):
        # Issue 89 with FreeTDS: Multiple selects (or catalog functions that issue selects) without fetches seem to
        # confuse the driver.
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')
        self.cursor.execute('select 1')

    def test_drivers(self):
        drivers = pyodbc.drivers()
        self.assertEqual(list, type(drivers))
        self.assert_(len(drivers) > 1)

        m = re.search('DRIVER={([^}]+)}', self.connection_string, re.IGNORECASE)
        current = m.group(1)
        self.assert_(current in drivers)
            


def main():
    from optparse import OptionParser
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", default=0, help="Increment test verbosity (can be used multiple times)")
    parser.add_option("-d", "--debug", action="store_true", default=False, help="Print debugging items")
    parser.add_option("-t", "--test", help="Run only the named test")

    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Only one argument is allowed.  Do you need quotes around the connection string?')

    if not args:
        connection_string = load_setup_connection_string('sqlservertests')

        if not connection_string:
            parser.print_help()
            raise SystemExit()
    else:
        connection_string = args[0]

    cnxn = pyodbc.connect(connection_string)
    print_library_info(cnxn)
    cnxn.close()

    suite = load_tests(SqlServerTestCase, options.test, connection_string)

    testRunner = unittest.TextTestRunner(verbosity=options.verbose)
    result = testRunner.run(suite)


if __name__ == '__main__':

    # Add the build directory to the path so we're testing the latest build, not the installed version.

    add_to_path()

    import pyodbc
    main()

########NEW FILE########
__FILENAME__ = test

from testutils import *
add_to_path()

import pyodbc

cnxn = pyodbc.connect("DRIVER={SQL Server Native Client 10.0};SERVER=localhost;DATABASE=test;Trusted_Connection=yes")
print('cnxn:', cnxn)

cursor = cnxn.cursor()
print('cursor:', cursor)

cursor.execute("select 1")
row = cursor.fetchone()
print('row:', row)



########NEW FILE########
__FILENAME__ = testbase

import unittest

_TESTSTR = '0123456789-abcdefghijklmnopqrstuvwxyz-'

def _generate_test_string(length):
    """
    Returns a string of `length` characters, constructed by repeating _TESTSTR as necessary.

    To enhance performance, there are 3 ways data is read, based on the length of the value, so most data types are
    tested with 3 lengths.  This function helps us generate the test data.

    We use a recognizable data set instead of a single character to make it less likely that "overlap" errors will
    be hidden and to help us manually identify where a break occurs.
    """
    if length <= len(_TESTSTR):
        return _TESTSTR[:length]

    c = (length + len(_TESTSTR)-1) / len(_TESTSTR)
    v = _TESTSTR * c
    return v[:length]

class TestBase(unittest.TestCase):

    

########NEW FILE########
__FILENAME__ = testutils

import os, sys, platform
from os.path import join, dirname, abspath, basename
import unittest

def add_to_path():
    """
    Prepends the build directory to the path so that newly built pyodbc libraries are used, allowing it to be tested
    without installing it.
    """
    # Put the build directory into the Python path so we pick up the version we just built.
    #
    # To make this cross platform, we'll search the directories until we find the .pyd file.

    import imp

    library_exts  = [ t[0] for t in imp.get_suffixes() if t[-1] == imp.C_EXTENSION ]
    library_names = [ 'pyodbc%s' % ext for ext in library_exts ]

    # Only go into directories that match our version number. 

    dir_suffix = '-%s.%s' % (sys.version_info[0], sys.version_info[1])

    build = join(dirname(dirname(abspath(__file__))), 'build')

    for root, dirs, files in os.walk(build):
        for d in dirs[:]:
            if not d.endswith(dir_suffix):
                dirs.remove(d)

        for name in library_names:
            if name in files:
                sys.path.insert(0, root)
                return
                
    print('Did not find the pyodbc library in the build directory.  Will use an installed version.')


def print_library_info(cnxn):
    import pyodbc
    print('python:  %s' % sys.version)
    print('pyodbc:  %s %s' % (pyodbc.version, os.path.abspath(pyodbc.__file__)))
    print('odbc:    %s' % cnxn.getinfo(pyodbc.SQL_ODBC_VER))
    print('driver:  %s %s' % (cnxn.getinfo(pyodbc.SQL_DRIVER_NAME), cnxn.getinfo(pyodbc.SQL_DRIVER_VER)))
    print('         supports ODBC version %s' % cnxn.getinfo(pyodbc.SQL_DRIVER_ODBC_VER))
    print('os:      %s' % platform.system())
    print('unicode: Py_Unicode=%s SQLWCHAR=%s' % (pyodbc.UNICODE_SIZE, pyodbc.SQLWCHAR_SIZE))

    if platform.system() == 'Windows':
        print('         %s' % ' '.join([s for s in platform.win32_ver() if s]))



def load_tests(testclass, name, *args):
    """
    Returns a TestSuite for tests in `testclass`.

    name
      Optional test name if you only want to run 1 test.  If not provided all tests in `testclass` will be loaded.

    args
      Arguments for the test class constructor.  These will be passed after the test method name.
    """
    if name:
        if not name.startswith('test_'):
            name = 'test_%s' % name
        names = [ name ]

    else:
        names = [ method for method in dir(testclass) if method.startswith('test_') ]

    return unittest.TestSuite([ testclass(name, *args) for name in names ])


def load_setup_connection_string(section):
    """
    Attempts to read the default connection string from the setup.cfg file.

    If the file does not exist or if it exists but does not contain the connection string, None is returned.  If the
    file exists but cannot be parsed, an exception is raised.
    """
    from os.path import exists, join, dirname, splitext, basename
    from configparser import SafeConfigParser
    
    FILENAME = 'setup.cfg'
    KEY      = 'connection-string'

    path = join(dirname(dirname(abspath(__file__))), 'tmp', FILENAME)

    if exists(path):
        try:
            p = SafeConfigParser()
            p.read(path)
        except:
            raise SystemExit('Unable to parse %s: %s' % (path, sys.exc_info()[1]))

        if p.has_option(section, KEY):
            return p.get(section, KEY)

    return None

########NEW FILE########
