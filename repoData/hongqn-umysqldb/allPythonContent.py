__FILENAME__ = test_cursors
from mock import patch, Mock
import umysqldb.cursors as M


def test_executemany_should_handle_on_duplicate_key_update_clause():
    with patch.object(M.Cursor, '_query') as mock_query:
        sql = 'INSERT INTO _test(id,val) VALUES(%s,%s) ' \
              'ON DUPLICATE KEY UPDATE id=VALUES(id),val=VALUES(val)'
        args = [(44495, 1), (44495, 2)]
        mock_conn = Mock()
        mock_conn.literal.side_effect = repr
        cursor = M.Cursor(mock_conn)
        cursor.executemany(sql, args)
        mock_query.assert_called_once_with(
            'INSERT INTO _test(id,val) VALUES\n(%s,%s),(%s,%s)\n '
            'ON DUPLICATE KEY UPDATE id=VALUES(id),val=VALUES(val)',
            (44495, 1, 44495, 2))

########NEW FILE########
__FILENAME__ = test_issues
def test_issue_8():
    """umysqldb.converters should be available since Django 1.6 requires them."""
    from umysqldb.converters import conversions, Thing2Literal

########NEW FILE########
__FILENAME__ = capabilities
#!/usr/bin/env python -O
""" Script to test database capabilities and the DB-API interface
    for functionality and memory leaks.

    Adapted from a script by M-A Lemburg.
    
"""
from time import time
import array
import unittest

from nose.plugins.skip import SkipTest

class DatabaseTest(unittest.TestCase):

    db_module = None
    connect_args = ()
    connect_kwargs = dict()
    create_table_extra = ''
    rows = 10
    debug = False
    
    def setUp(self):
        import gc
        db = self.db_module.connect(*self.connect_args, **self.connect_kwargs)
        self.connection = db
        self.cursor = db.cursor()
        self.BLOBText = ''.join([chr(i) for i in range(256)] * 100);
        self.BLOBUText = u''.join([unichr(i) for i in range(16384)])
        self.BLOBBinary = self.db_module.Binary(''.join([chr(i) for i in range(256)] * 16))

    leak_test = True
    
    def tearDown(self):
        if self.leak_test:
            import gc
            del self.cursor
            orphans = gc.collect()
            self.failIf(orphans, "%d orphaned objects found after deleting cursor" % orphans)
            
            del self.connection
            orphans = gc.collect()
            self.failIf(orphans, "%d orphaned objects found after deleting connection" % orphans)
            
    def table_exists(self, name):
        try:
            self.cursor.execute('select * from %s where 1=0' % name)
        except:
            return False
        else:
            return True

    def quote_identifier(self, ident):
        return '"%s"' % ident
    
    def new_table_name(self):
        i = id(self.cursor)
        while True:
            name = self.quote_identifier('tb%08x' % i)
            if not self.table_exists(name):
                return name
            i = i + 1

    def create_table(self, columndefs):

        """ Create a table using a list of column definitions given in
            columndefs.
        
            generator must be a function taking arguments (row_number,
            col_number) returning a suitable data object for insertion
            into the table.

        """
        self.table = self.new_table_name()
        self.cursor.execute('CREATE TABLE %s (%s) %s' % 
                            (self.table,
                             ',\n'.join(columndefs),
                             self.create_table_extra))

    def check_data_integrity(self, columndefs, generator):
        # insert
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' % 
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))
        data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                 for i in range(self.rows) ]
        if self.debug:
            print data
        self.cursor.executemany(insert_statement, data)
        self.connection.commit()
        # verify
        self.cursor.execute('select * from %s' % self.table)
        l = self.cursor.fetchall()
        if self.debug:
            print l
        self.assertEquals(len(l), self.rows)
        try:
            for i in range(self.rows):
                for j in range(len(columndefs)):
                    self.assertEquals(l[i][j], generator(i,j))
        finally:
            if not self.debug:
                self.cursor.execute('drop table %s' % (self.table))

    def test_transactions(self):
        columndefs = ( 'col1 INT', 'col2 VARCHAR(255)')
        def generator(row, col):
            if col == 0: return row
            else: return ('%i' % (row%10))*255
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' % 
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))
        data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                 for i in range(self.rows) ]
        self.cursor.executemany(insert_statement, data)
        # verify
        self.connection.commit()
        self.cursor.execute('select * from %s' % self.table)
        l = self.cursor.fetchall()
        self.assertEquals(len(l), self.rows)
        for i in range(self.rows):
            for j in range(len(columndefs)):
                self.assertEquals(l[i][j], generator(i,j))
        delete_statement = 'delete from %s where col1=%%s' % self.table
        self.cursor.execute(delete_statement, (0,))
        self.cursor.execute('select col1 from %s where col1=%s' % \
                            (self.table, 0))
        l = self.cursor.fetchall()
        self.assertFalse(l, "DELETE didn't work")
        self.connection.rollback()
        self.cursor.execute('select col1 from %s where col1=%s' % \
                            (self.table, 0))
        l = self.cursor.fetchall()
        self.assertTrue(len(l) == 1, "ROLLBACK didn't work")
        self.cursor.execute('drop table %s' % (self.table))

    def test_truncation(self):
        columndefs = ( 'col1 INT', 'col2 VARCHAR(255)')
        def generator(row, col):
            if col == 0: return row
            else: return ('%i' % (row%10))*((255-self.rows/2)+row)
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' % 
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))

        try:
            self.cursor.execute(insert_statement, (0, '0'*256))
        except Warning:
            if self.debug: print self.cursor.messages
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long column did not generate warnings/exception with single insert")

        self.connection.rollback()
        
        try:
            for i in range(self.rows):
                data = []
                for j in range(len(columndefs)):
                    data.append(generator(i,j))
                self.cursor.execute(insert_statement,tuple(data))
        except Warning:
            if self.debug: print self.cursor.messages
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long columns did not generate warnings/exception with execute()")

        self.connection.rollback()
        
        try:
            data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                     for i in range(self.rows) ]
            self.cursor.executemany(insert_statement, data)
        except Warning:
            if self.debug: print self.cursor.messages
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long columns did not generate warnings/exception with executemany()")

        self.connection.rollback()
        self.cursor.execute('drop table %s' % (self.table))

    def test_CHAR(self):
        # Character data
        def generator(row,col):
            return ('%i' % ((row+col) % 10)) * 255
        self.check_data_integrity(
            ('col1 char(255)','col2 char(255)'),
            generator)

    def test_INT(self):
        # Number data
        def generator(row,col):
            return row*row
        self.check_data_integrity(
            ('col1 INT',),
            generator)

    def test_DECIMAL(self):
        # DECIMAL
        def generator(row,col):
            from decimal import Decimal
            return Decimal("%d.%02d" % (row, col))
        self.check_data_integrity(
            ('col1 DECIMAL(5,2)',),
            generator)

    def test_DATE(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.DateFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 DATE',),
                 generator)

    def test_TIME(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimeFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 TIME',),
                 generator)

    def test_DATETIME(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 DATETIME',),
                 generator)

    def test_TIMESTAMP(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 TIMESTAMP',),
                 generator)

    def test_fractional_TIMESTAMP(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313+row*0.7*col/3.0)
        self.check_data_integrity(
                 ('col1 TIMESTAMP',),
                 generator)

    def test_LONG(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBUText # 'BLOB Text ' * 1024
        self.check_data_integrity(
                 ('col1 INT','col2 LONG'),
                 generator)

    def test_TEXT(self):
        def generator(row,col):
            return self.BLOBUText # 'BLOB Text ' * 1024
        self.check_data_integrity(
                 ('col2 TEXT',),
                 generator)

    def test_LONG_BYTE(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBBinary # 'BLOB\000Binary ' * 1024
        self.check_data_integrity(
                 ('col1 INT','col2 LONG BYTE'),
                 generator)

    def test_BLOB(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBBinary # 'BLOB\000Binary ' * 1024
        self.check_data_integrity(
                 ('col1 INT','col2 BLOB'),
                 generator)


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

__rcs_id__  = '$Id: dbapi20.py,v 1.11 2005/01/02 02:41:01 zenzen Exp $'
__version__ = '$Revision: 1.12 $'[11:-2]
__author__ = 'Stuart Bishop <stuart@stuartbishop.net>'

import unittest
import time
import sys


# Revision 1.12  2009/02/06 03:35:11  kf7xm
# Tested okay with Python 3.0, includes last minute patches from Mark H.
#
# Revision 1.1.1.1.2.1  2008/09/20 19:54:59  rupole
# Include latest changes from main branch
# Updates for py3k
#
# Revision 1.11  2005/01/02 02:41:01  zenzen
# Update author email address
#
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
def str2bytes(sval):
    if sys.version_info < (3,0) and isinstance(sval, str):
        sval = sval.decode("latin1")
    return sval.encode("latin1")

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
            for ddl in (self.xddl1,self.xddl2):
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
            import traceback; traceback.print_exc()
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
            self.assertTrue(threadsafety in (0,1,2,3))
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.assertTrue(paramstyle in (
                'qmark','numeric','named','format','pyformat'
                ))
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        self.assertTrue(issubclass(self.driver.Warning,Exception))
        self.assertTrue(issubclass(self.driver.Error,Exception))
        self.assertTrue(
            issubclass(self.driver.InterfaceError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.DatabaseError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.OperationalError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.IntegrityError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.InternalError,self.driver.Error)
            )
        self.assertTrue(
            issubclass(self.driver.ProgrammingError,self.driver.Error)
            )
        self.assertTrue(
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
        self.assertTrue(con.Warning is drv.Warning)
        self.assertTrue(con.Error is drv.Error)
        self.assertTrue(con.InterfaceError is drv.InterfaceError)
        self.assertTrue(con.DatabaseError is drv.DatabaseError)
        self.assertTrue(con.OperationalError is drv.OperationalError)
        self.assertTrue(con.IntegrityError is drv.IntegrityError)
        self.assertTrue(con.InternalError is drv.InternalError)
        self.assertTrue(con.ProgrammingError is drv.ProgrammingError)
        self.assertTrue(con.NotSupportedError is drv.NotSupportedError)


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
            self.assertTrue(cur.rowcount in (-1,1),
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement'
                )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertTrue(cur.rowcount in (-1,1),
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
        self.assertTrue(cur.rowcount in (-1,1))

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
        self.assertTrue(cur.rowcount in (-1,1))

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
            self.assertTrue(cur.rowcount in (-1,2),
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
            self.assertTrue(cur.rowcount in (-1,0))

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
            self.assertTrue(cur.rowcount in (-1,1))
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
            self.assertTrue(cur.rowcount in (-1,6))

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
            self.assertTrue(cur.rowcount in (-1,6))

            cur.arraysize=6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany() # Should get all rows
            self.assertTrue(cur.rowcount in (-1,6))
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
            self.assertTrue(cur.rowcount in (-1,6))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany() # Should get empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows'
                )
            self.assertTrue(cur.rowcount in (-1,0))

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
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))
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
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,0))
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
            self.assertTrue(cur.rowcount in (-1,6))
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
        raise NotImplementedError('Helper not implemented')
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
        raise NotImplementedError('Helper not implemented')
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
        raise NotImplementedError('Drivers need to override this test')

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.assertTrue(hasattr(cur,'arraysize'),
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
        raise NotImplementedError('Driver needed to override this test')

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
        b = self.driver.Binary(str2bytes('Something'))
        b = self.driver.Binary(str2bytes(''))

    def test_STRING(self):
        self.assertTrue(hasattr(self.driver,'STRING'),
            'module.STRING must be defined'
            )

    def test_BINARY(self):
        self.assertTrue(hasattr(self.driver,'BINARY'),
            'module.BINARY must be defined.'
            )

    def test_NUMBER(self):
        self.assertTrue(hasattr(self.driver,'NUMBER'),
            'module.NUMBER must be defined.'
            )

    def test_DATETIME(self):
        self.assertTrue(hasattr(self.driver,'DATETIME'),
            'module.DATETIME must be defined.'
            )

    def test_ROWID(self):
        self.assertTrue(hasattr(self.driver,'ROWID'),
            'module.ROWID must be defined.'
            )


########NEW FILE########
__FILENAME__ = test_oursql_capabilities
#!/usr/bin/env python
import capabilities
import unittest
import umysqldb
import warnings

from nose.plugins.skip import SkipTest

warnings.filterwarnings('error')

class test_umysqldb(capabilities.DatabaseTest):

    db_module = umysqldb 
    connect_args = ()
    connect_kwargs = dict(db='test',
                           host='127.0.0.1',
                           user='test',
                           passwd='',
                           charset='utf8',
                           sql_mode="ANSI,STRICT_TRANS_TABLES,TRADITIONAL")
    create_table_extra = "ENGINE=INNODB CHARACTER SET UTF8"
    leak_test = False
    
    def quote_identifier(self, ident):
        return "`%s`" % ident

    def test_TIME(self):
        from datetime import timedelta
        def generator(row,col):
            return timedelta(0, row*8000)
        self.check_data_integrity(
                 ('col1 TIME',),
                 generator)

    def test_TINYINT(self):
        # Number data
        def generator(row,col):
            v = (row*row) % 256
            if v > 127:
                v = v-256
            return v
        self.check_data_integrity(
            ('col1 TINYINT',),
            generator)
        
    def test_stored_procedures(self):
        raise SkipTest("umysql does not support procedures")
        db = self.connection
        c = self.cursor
        self.create_table(('pos INT', 'tree CHAR(20)'))
        c.executemany("INSERT INTO %s (pos,tree) VALUES (%%s,%%s)" % self.table,
                      list(enumerate('ash birch cedar larch pine'.split())))
        db.commit()
        
        c.execute("""
        CREATE PROCEDURE test_sp(IN t VARCHAR(255))
        BEGIN
            SELECT pos FROM %s WHERE tree = t;
        END
        """ % self.table)
        db.commit()

        c.callproc('test_sp', ('larch',))
        rows = c.fetchall()
        self.assertEquals(len(rows), 1)
        self.assertEquals(rows[0][0], 3)
        c.nextset()
        
        c.execute("DROP PROCEDURE test_sp")
        c.execute('drop table %s' % (self.table))

    def test_small_CHAR(self):
        # Character data
        def generator(row,col):
            i = (row*col+62)%256
            if i == 62: return ''
            if i == 63: return None
            return chr(i)
        self.check_data_integrity(
            ('col1 char(1)','col2 char(1)'),
            generator)
    
    def test_bug_2671682(self):
        from umysqldb.constants import ER
        try:
            self.cursor.execute("describe some_non_existent_table");
        except self.connection.ProgrammingError, msg:
            self.assertTrue(msg[0] == ER.NO_SUCH_TABLE)
    
    def test_ping(self):
        raise SkipTest("umysql does not support PING command")
        self.connection.ping()

########NEW FILE########
__FILENAME__ = test_oursql_dbapi20
#!/usr/bin/env python
import dbapi20
import unittest

from nose.plugins.skip import SkipTest

import umysqldb

class test_umysqldb(dbapi20.DatabaseAPI20Test):
    driver = umysqldb
    connect_args = ()
    connect_kw_args = dict(db='test',
                           host='127.0.0.1',
                           user='test',
                           passwd='',
                           charset='utf8',
                           sql_mode="ANSI,STRICT_TRANS_TABLES,TRADITIONAL")

    def test_setoutputsize(self): pass
    def test_setoutputsize_basic(self): pass
    def test_nextset(self): pass

    """The tests on fetchone and fetchall and rowcount bogusly
    test for an exception if the statement cannot return a
    result set. MySQL always returns a result set; it's just that
    some things return empty result sets."""
    
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
##             self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))
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
            self.assertTrue(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )
            
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
##             self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.assertTrue(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
##             self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
##             self.assertEqual(cur.fetchone(),None,
##                 'cursor.fetchone should return None if no more rows available'
##                 )
            self.assertTrue(cur.rowcount in (-1,1))
        finally:
            con.close()

    # Same complaint as for fetchall and fetchone
    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
##             self.assertEqual(cur.rowcount,-1,
##                 'cursor.rowcount should be -1 after executing no-result '
##                 'statements'
##                 )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
##             self.assertTrue(cur.rowcount in (-1,1),
##                 'cursor.rowcount should == number or rows inserted, or '
##                 'set to -1 after executing an insert statement'
##                 )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertTrue(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
##             self.assertEqual(cur.rowcount,-1,
##                 'cursor.rowcount not being reset to -1 after executing '
##                 'no-result statements'
##                 )
        finally:
            con.close()

    def test_callproc(self):
        pass # performed in test_MySQL_capabilities

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the 
            number of rows in booze then "name from booze"
        '''
        sql="""
           create procedure deleteme()
           begin
               select count(*) from %(tp)sbooze;
               select name from %(tp)sbooze;
           end
        """ % dict(tp=self.table_prefix)
        cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        cur.execute("drop procedure deleteme")

    def test_nextset(self):
        raise SkipTest("umysql does not support calling procedure")
        from warnings import warn
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
                if s:
                    empty = cur.fetchall()
                    self.assertEquals(len(empty), 0,
                                      "non-empty result set after other result sets")
                    #warn("Incompatibility: MySQL returns an empty result set for the CALL itself",
                    #     Warning)
                #assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    
if __name__ == '__main__':
    unittest.main()
    print '''"Huh-huh, he said 'unit'." -- Butthead'''

########NEW FILE########
__FILENAME__ = test_oursql_nonstandard
import unittest

import umysqldb
_mysql = umysqldb
from umysqldb.constants import FIELD_TYPE

from nose.plugins.skip import SkipTest


class TestDBAPISet(unittest.TestCase):
    def test_set_equality(self):
        self.assertTrue(umysqldb.STRING == umysqldb.STRING)

    def test_set_inequality(self):
        self.assertTrue(umysqldb.STRING != umysqldb.NUMBER)

    def test_set_equality_membership(self):
        self.assertTrue(FIELD_TYPE.VAR_STRING == umysqldb.STRING)

    def test_set_inequality_membership(self):
        self.assertTrue(FIELD_TYPE.DATE != umysqldb.STRING)


class CoreModule(unittest.TestCase):
    """Core _mysql module features."""

    def test_NULL(self):
        """Should have a NULL constant."""
        self.assertEqual(_mysql.NULL, 'NULL')

    def test_version(self):
        """Version information sanity."""
        self.assertTrue(isinstance(_mysql.__version__, str))

        self.assertTrue(isinstance(_mysql.version_info, tuple))
        self.assertEqual(len(_mysql.version_info), 5)

    def test_client_info(self):
        self.assertTrue(isinstance(_mysql.get_client_info(), str))

    def test_thread_safe(self):
        self.assertTrue(isinstance(_mysql.thread_safe(), int))


class CoreAPI(unittest.TestCase):
    """Test _mysql interaction internals."""

    def setUp(self):
        self.conn = _mysql.connect(db='test', read_default_file="~/.my.cnf")

    def tearDown(self):
        self.conn.close()

    def test_thread_id(self):
        raise SkipTest("umysql does not supporting retrieving thread id")
        tid = self.conn.thread_id()
        self.assertTrue(isinstance(tid, int),
                        "thread_id didn't return an int.")

        self.assertRaises(TypeError, self.conn.thread_id, ('evil',),
                          "thread_id shouldn't accept arguments.")

    def test_affected_rows(self):
        self.assertEquals(self.conn.affected_rows(), 0,
                          "Should return 0 before we do anything.")


    #def test_debug(self):
        ## FIXME Only actually tests if you lack SUPER
        #self.assertRaises(umysqldb.OperationalError,
                          #self.conn.dump_debug_info)

    def test_charset_name(self):
        self.assertTrue(isinstance(self.conn.character_set_name(), str),
                        "Should return a string.")

    def test_host_info(self):
        self.assertTrue(isinstance(self.conn.get_host_info(), str),
                        "Should return a string.")

    def test_proto_info(self):
        raise SkipTest("umysql does not support retrieving protocol version")
        self.assertTrue(isinstance(self.conn.get_proto_info(), int),
                        "Should return an int.")

    def test_server_info(self):
        raise SkipTest("umysql does not support retrieving server version")
        self.assertTrue(isinstance(self.conn.get_server_info(), str),
                        "Should return an str.")


########NEW FILE########
__FILENAME__ = base
import umysqldb
import unittest

class UMySQLdbTestCase(unittest.TestCase):
    # Edit this to suit your test environment.
    databases = [
        {"host":"127.0.0.1","user":"test",
         "passwd":"","db":"test_umysqldb", "use_unicode": True},
        {"host":"127.0.0.1","user":"test","passwd":"","db":"test_umysqldb2"}]

    def setUp(self):
        self.connections = []

        for params in self.databases:
            self.connections.append(umysqldb.connect(**params))

    def tearDown(self):
        for connection in self.connections:
            connection.close()


########NEW FILE########
__FILENAME__ = test_basic
import time
import datetime
import struct

from nose.plugins.skip import SkipTest

from umysqldb import util
from . import base

def int2byte(i):
    return struct.pack("!B", i)

class TestConversion(base.UMySQLdbTestCase):
    def test_datatypes(self):
        """ test every data type """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_datatypes (b bit, i int, l bigint, f real, s varchar(32), u varchar(32), bb blob, d date, dt datetime, ts timestamp, td time, t time, st datetime)")
        try:
            # insert values
            v = (True, -3, 123456789012, 5.7, "hello'\" world", u"Espa\xc3\xb1ol", "binary\x00data".encode(conn.charset), datetime.date(1988,2,2), datetime.datetime.now(), datetime.timedelta(5,6), datetime.time(16,32), time.localtime())
            c.execute("insert into test_datatypes (b,i,l,f,s,u,bb,d,dt,td,t,st) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", v)
            c.execute("select b,i,l,f,s,u,bb,d,dt,td,t,st from test_datatypes")
            r = c.fetchone()
            self.assertEqual(int2byte(1), r[0])
            self.assertEqual(v[1:8], r[1:8])
            # mysql throws away microseconds so we need to check datetimes
            # specially. additionally times are turned into timedeltas.
            self.assertEqual(datetime.datetime(*v[8].timetuple()[:6]), r[8])
            self.assertEqual(v[9], r[9]) # just timedeltas
            self.assertEqual(datetime.timedelta(0, 60 * (v[10].hour * 60 + v[10].minute)), r[10])
            self.assertEqual(datetime.datetime(*v[-1][:6]), r[-1])

            c.execute("delete from test_datatypes")

            # check nulls
            c.execute("insert into test_datatypes (b,i,l,f,s,u,bb,d,dt,td,t,st) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", [None] * 12)
            c.execute("select b,i,l,f,s,u,bb,d,dt,td,t,st from test_datatypes")
            r = c.fetchone()
            self.assertEqual(tuple([None] * 12), r)

            c.execute("delete from test_datatypes")

            # check sequence type
            c.execute("insert into test_datatypes (i, l) values (2,4), (6,8), (10,12)")
            c.execute("select l from test_datatypes where i in %s order by i", ((2,6),))
            r = c.fetchall()
            self.assertEqual(((4,),(8,)), r)
        finally:
            c.execute("drop table test_datatypes")

    def test_dict(self):
        """ test dict escaping """
        raise SkipTest("umysql does not support dict escaping")
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_dict (a integer, b integer, c integer)")
        try:
            c.execute("insert into test_dict (a,b,c) values (%(a)s, %(b)s, %(c)s)", {"a":1,"b":2,"c":3})
            c.execute("select a,b,c from test_dict")
            self.assertEqual((1,2,3), c.fetchone())
        finally:
            c.execute("drop table test_dict")

    def test_string(self):
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_dict (a text)")
        test_value = "I am a test string"
        try:
            c.execute("insert into test_dict (a) values (%s)", test_value)
            c.execute("select a from test_dict")
            self.assertEqual((test_value,), c.fetchone())
        finally:
            c.execute("drop table test_dict")

    def test_integer(self):
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_dict (a integer)")
        test_value = 12345
        try:
            c.execute("insert into test_dict (a) values (%s)", test_value)
            c.execute("select a from test_dict")
            self.assertEqual((test_value,), c.fetchone())
        finally:
            c.execute("drop table test_dict")


    def test_big_blob(self):
        """ test tons of data """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_big_blob (b blob)")
        try:
            data = "umysqldb" * 1024
            c.execute("insert into test_big_blob (b) values (%s)", (data,))
            c.execute("select b from test_big_blob")
            self.assertEqual(data.encode(conn.charset), c.fetchone()[0])
        finally:
            c.execute("drop table test_big_blob")
    
    def test_untyped(self):
        """ test conversion of null, empty string """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("select null,''")
        self.assertEqual((None,u''), c.fetchone())
        c.execute("select '',null")
        self.assertEqual((u'',None), c.fetchone())
    
    def test_datetime(self):
        """ test conversion of null, empty string """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("select time('12:30'), time('23:12:59'), time('23:12:59.05100')")
        self.assertEqual((datetime.timedelta(0, 45000),
                          datetime.timedelta(0, 83579),
                          datetime.timedelta(0, 83579, 51000)),
                         c.fetchone())


class TestCursor(base.UMySQLdbTestCase):
    # this test case does not work quite right yet, however,
    # we substitute in None for the erroneous field which is
    # compatible with the DB-API 2.0 spec and has not broken
    # any unit tests for anything we've tried.

    #def test_description(self):
    #    """ test description attribute """
    #    # result is from MySQLdb module
    #    r = (('Host', 254, 11, 60, 60, 0, 0),
    #         ('User', 254, 16, 16, 16, 0, 0),
    #         ('Password', 254, 41, 41, 41, 0, 0),
    #         ('Select_priv', 254, 1, 1, 1, 0, 0),
    #         ('Insert_priv', 254, 1, 1, 1, 0, 0),
    #         ('Update_priv', 254, 1, 1, 1, 0, 0),
    #         ('Delete_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_priv', 254, 1, 1, 1, 0, 0),
    #         ('Drop_priv', 254, 1, 1, 1, 0, 0),
    #         ('Reload_priv', 254, 1, 1, 1, 0, 0),
    #         ('Shutdown_priv', 254, 1, 1, 1, 0, 0),
    #         ('Process_priv', 254, 1, 1, 1, 0, 0),
    #         ('File_priv', 254, 1, 1, 1, 0, 0),
    #         ('Grant_priv', 254, 1, 1, 1, 0, 0),
    #         ('References_priv', 254, 1, 1, 1, 0, 0),
    #         ('Index_priv', 254, 1, 1, 1, 0, 0),
    #         ('Alter_priv', 254, 1, 1, 1, 0, 0),
    #         ('Show_db_priv', 254, 1, 1, 1, 0, 0),
    #         ('Super_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_tmp_table_priv', 254, 1, 1, 1, 0, 0),
    #         ('Lock_tables_priv', 254, 1, 1, 1, 0, 0),
    #         ('Execute_priv', 254, 1, 1, 1, 0, 0),
    #         ('Repl_slave_priv', 254, 1, 1, 1, 0, 0),
    #         ('Repl_client_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_view_priv', 254, 1, 1, 1, 0, 0),
    #         ('Show_view_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_routine_priv', 254, 1, 1, 1, 0, 0),
    #         ('Alter_routine_priv', 254, 1, 1, 1, 0, 0),
    #         ('Create_user_priv', 254, 1, 1, 1, 0, 0),
    #         ('Event_priv', 254, 1, 1, 1, 0, 0),
    #         ('Trigger_priv', 254, 1, 1, 1, 0, 0),
    #         ('ssl_type', 254, 0, 9, 9, 0, 0),
    #         ('ssl_cipher', 252, 0, 65535, 65535, 0, 0),
    #         ('x509_issuer', 252, 0, 65535, 65535, 0, 0),
    #         ('x509_subject', 252, 0, 65535, 65535, 0, 0),
    #         ('max_questions', 3, 1, 11, 11, 0, 0),
    #         ('max_updates', 3, 1, 11, 11, 0, 0),
    #         ('max_connections', 3, 1, 11, 11, 0, 0),
    #         ('max_user_connections', 3, 1, 11, 11, 0, 0))
    #    conn = self.connections[0]
    #    c = conn.cursor()
    #    c.execute("select * from mysql.user")
    #
    #    self.assertEqual(r, c.description)

    def test_fetch_no_result(self):
        """ test a fetchone() with no rows """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table test_nr (b varchar(32))")
        try:
            data = "umysqldb"
            c.execute("insert into test_nr (b) values (%s)", (data,))
            self.assertEqual(None, c.fetchone())
        finally:
            c.execute("drop table test_nr")

    def test_aggregates(self):
        """ test aggregate functions """
        conn = self.connections[0]
        c = conn.cursor()
        try:
            c.execute('create table test_aggregates (i integer)')
            for i in xrange(0, 10):
                c.execute('insert into test_aggregates (i) values (%s)', (i,))
            c.execute('select sum(i) from test_aggregates')
            r, = c.fetchone()
            self.assertEqual(sum(range(0,10)), r)
        finally:
            c.execute('drop table test_aggregates')


__all__ = ["TestConversion","TestCursor"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_DictCursor
import datetime
import umysqldb.cursors
from . import base


class TestDictCursor(base.UMySQLdbTestCase):

    def test_DictCursor(self):
        #all assert test compare to the structure as would come out from MySQLdb 
        conn = self.connections[0]
        c = conn.cursor(umysqldb.cursors.DictCursor)
        # create a table ane some data to query
        c.execute("""CREATE TABLE dictcursor (name char(20), age int , DOB datetime)""")
        data = (("bob",21,"1990-02-06 23:04:56"),
                ("jim",56,"1955-05-09 13:12:45"),
                ("fred",100,"1911-09-12 01:01:01"))
        bob =  {'name':'bob','age':21,'DOB':datetime.datetime(1990, 02, 6, 23, 04, 56)}
        jim =  {'name':'jim','age':56,'DOB':datetime.datetime(1955, 05, 9, 13, 12, 45)}
        fred = {'name':'fred','age':100,'DOB':datetime.datetime(1911, 9, 12, 1, 1, 1)}
        try:
            c.executemany("insert into dictcursor values (%s,%s,%s)", data)
            # try an update which should return no rows
            c.execute("update dictcursor set age=20 where name='bob'")
            bob['age'] = 20
            # pull back the single row dict for bob and check
            c.execute("SELECT * from dictcursor where name='bob'")
            r = c.fetchone()
            self.assertEqual(bob,r,"fetchone via DictCursor failed")
            # same again, but via fetchall => tuple)
            c.execute("SELECT * from dictcursor where name='bob'")
            r = c.fetchall()
            self.assertEqual((bob,),r,"fetch a 1 row result via fetchall failed via DictCursor")
            # same test again but iterate over the 
            c.execute("SELECT * from dictcursor where name='bob'")
            for r in c:
                self.assertEqual(bob, r,"fetch a 1 row result via iteration failed via DictCursor")
            # get all 3 row via fetchall
            c.execute("SELECT * from dictcursor")
            r = c.fetchall()
            self.assertEqual((bob,jim,fred), r, "fetchall failed via DictCursor")
            #same test again but do a list comprehension
            c.execute("SELECT * from dictcursor")
            r = [x for x in c]
            self.assertEqual([bob,jim,fred], r, "list comprehension failed via DictCursor")
            # get all 2 row via fetchmany
            c.execute("SELECT * from dictcursor")
            r = c.fetchmany(2)
            self.assertEqual((bob,jim), r, "fetchmany failed via DictCursor")
        finally:
            c.execute("drop table dictcursor")

__all__ = ["TestDictCursor"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_example
import umysqldb
from . import base

class TestExample(base.UMySQLdbTestCase):
    def test_example(self):
        conn = umysqldb.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='mysql')
   

        cur = conn.cursor()

        cur.execute("SELECT Host,User FROM user")

        # print cur.description

        # r = cur.fetchall()
        # print r
        # ...or...
        u = False

        for r in cur.fetchall():
            u = u or conn.user in r

        self.assertTrue(u)

        cur.close()
        conn.close()

__all__ = ["TestExample"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_issues
import umysqldb
from . import base
import unittest

import sys

try:
    import imp
    reload = imp.reload
except AttributeError:
    pass

import datetime

from nose.plugins.skip import SkipTest

# backwards compatibility:
if not hasattr(unittest, "skip"):
    unittest.skip = lambda message: lambda f: f

class TestOldIssues(base.UMySQLdbTestCase):
    def test_issue_3(self):
        """ undefined methods datetime_or_None, date_or_None """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table issue3 (d date, t time, dt datetime, ts timestamp)")
        try:
            c.execute("insert into issue3 (d, t, dt, ts) values (%s,%s,%s,%s)", (None, None, None, None))
            c.execute("select d from issue3")
            self.assertEqual(None, c.fetchone()[0])
            c.execute("select t from issue3")
            self.assertEqual(None, c.fetchone()[0])
            c.execute("select dt from issue3")
            self.assertEqual(None, c.fetchone()[0])
            c.execute("select ts from issue3")
            self.assertTrue(isinstance(c.fetchone()[0], datetime.datetime))
        finally:
            c.execute("drop table issue3")

    def test_issue_4(self):
        """ can't retrieve TIMESTAMP fields """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table issue4 (ts timestamp)")
        try:
            c.execute("insert into issue4 (ts) values (now())")
            c.execute("select ts from issue4")
            self.assertTrue(isinstance(c.fetchone()[0], datetime.datetime))
        finally:
            c.execute("drop table issue4")

    def test_issue_5(self):
        """ query on information_schema.tables fails """
        con = self.connections[0]
        cur = con.cursor()
        cur.execute("select * from information_schema.tables")

    def test_issue_6(self):
        """ exception: TypeError: ord() expected a character, but string of length 0 found """
        conn = umysqldb.connect(host="localhost",user="root",passwd="",db="mysql")
        c = conn.cursor()
        c.execute("select * from user")
        conn.close()

    def test_issue_8(self):
        """ Primary Key and Index error when selecting data """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("""CREATE TABLE `test` (`station` int(10) NOT NULL DEFAULT '0', `dh`
datetime NOT NULL DEFAULT '0000-00-00 00:00:00', `echeance` int(1) NOT NULL
DEFAULT '0', `me` double DEFAULT NULL, `mo` double DEFAULT NULL, PRIMARY
KEY (`station`,`dh`,`echeance`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;""")
        try:
            self.assertEqual(0, c.execute("SELECT * FROM test"))
            c.execute("ALTER TABLE `test` ADD INDEX `idx_station` (`station`)")
            self.assertEqual(0, c.execute("SELECT * FROM test"))
        finally:
            c.execute("drop table test")

    def test_issue_9(self):
        """ sets DeprecationWarning in Python 2.6 """
        try:
            reload(umysqldb)
        except DeprecationWarning:
            self.fail()

    def test_issue_13(self):
        """ can't handle large result fields """
        conn = self.connections[0]
        cur = conn.cursor()
        try:
            cur.execute("create table issue13 (t text)")
            # ticket says 18k
            size = 18*1024
            cur.execute("insert into issue13 (t) values (%s)", ("x" * size,))
            cur.execute("select t from issue13")
            # use assertTrue so that obscenely huge error messages don't print
            r = cur.fetchone()[0]
            self.assertTrue("x" * size == r)
        finally:
            cur.execute("drop table issue13")

    def test_issue_15(self):
        """ query should be expanded before perform character encoding """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table issue15 (t varchar(32))")
        try:
            c.execute("insert into issue15 (t) values (%s)", (u'\xe4\xf6\xfc',))
            c.execute("select t from issue15")
            self.assertEqual(u'\xe4\xf6\xfc', c.fetchone()[0])
        finally:
            c.execute("drop table issue15")

    def test_issue_16(self):
        """ Patch for string and tuple escaping """
        conn = self.connections[0]
        c = conn.cursor()
        c.execute("create table issue16 (name varchar(32) primary key, email varchar(32))")
        try:
            c.execute("insert into issue16 (name, email) values ('pete', 'floydophone')")
            c.execute("select email from issue16 where name=%s", ("pete",))
            self.assertEqual("floydophone", c.fetchone()[0])
        finally:
            c.execute("drop table issue16")

    @unittest.skip("test_issue_17() requires a custom, legacy MySQL configuration and will not be run.")
    def test_issue_17(self):
        """ could not connect mysql use passwod """
        conn = self.connections[0]
        host = self.databases[0]["host"]
        db = self.databases[0]["db"]
        c = conn.cursor()
        # grant access to a table to a user with a password
        try:
            c.execute("create table issue17 (x varchar(32) primary key)")
            c.execute("insert into issue17 (x) values ('hello, world!')")
            c.execute("grant all privileges on %s.issue17 to 'issue17user'@'%%' identified by '1234'" % db)
            conn.commit()
            
            conn2 = umysqldb.connect(host=host, user="issue17user", passwd="1234", db=db)
            c2 = conn2.cursor()
            c2.execute("select x from issue17")
            self.assertEqual("hello, world!", c2.fetchone()[0])
        finally:
            c.execute("drop table issue17")

def _uni(s, e):
    # hack for py3
    if sys.version_info[0] > 2:
        return unicode(bytes(s, sys.getdefaultencoding()), e)
    else:
        return unicode(s, e)

class TestNewIssues(base.UMySQLdbTestCase):
    def test_issue_34(self):
        try:
            umysqldb.connect(host="localhost", port=1237, user="root")
            self.fail()
        except umysqldb.OperationalError, e:
            self.assertEqual(2003, e.args[0])
        except:
            self.fail()

    def test_issue_33(self):
        conn = umysqldb.connect(host="localhost", user="root", db=self.databases[0]["db"], charset="utf8")
        c = conn.cursor()
        try:
            c.execute(_uni("create table hei\xc3\x9fe (name varchar(32))", "utf8"))
            c.execute(_uni("insert into hei\xc3\x9fe (name) values ('Pi\xc3\xb1ata')", "utf8"))
            c.execute(_uni("select name from hei\xc3\x9fe", "utf8"))
            self.assertEqual(_uni("Pi\xc3\xb1ata","utf8"), c.fetchone()[0])
        finally:
            c.execute(_uni("drop table hei\xc3\x9fe", "utf8"))

    @unittest.skip("This test requires manual intervention")
    def test_issue_35(self):
        conn = self.connections[0]
        c = conn.cursor()
        print "sudo killall -9 mysqld within the next 10 seconds"
        try:
            c.execute("select sleep(10)")
            self.fail()
        except umysqldb.OperationalError, e:
            self.assertEqual(2013, e.args[0])

    def test_issue_36(self):
        raise SkipTest("umysql does not support kill command")
        conn = self.connections[0]
        c = conn.cursor()
        # kill connections[0]
        c.execute("show processlist")
        kill_id = None
        for id,user,host,db,command,time,state,info in c.fetchall():
            if info == "show processlist":
                kill_id = id
                break
        # now nuke the connection
        conn.kill(kill_id)
        # make sure this connection has broken
        try:
            c.execute("show tables")
            self.fail()
        except:
            pass
        # check the process list from the other connection
        try:
            c = self.connections[1].cursor()
            c.execute("show processlist")
            ids = [row[0] for row in c.fetchall()]
            self.assertFalse(kill_id in ids)
        finally:
            del self.connections[0]

    def test_issue_37(self):
        conn = self.connections[0]
        c = conn.cursor()
        self.assertEqual(1, c.execute("SELECT @foo"))
        self.assertEqual((None,), c.fetchone())
        self.assertEqual(0, c.execute("SET @foo = 'bar'"))
        c.execute("set @foo = 'bar'")

    def test_issue_38(self):
        conn = self.connections[0]
        c = conn.cursor()
        datum = "a" * 1024 * 1023 # reduced size for most default mysql installs
        
        try:
            c.execute("create table issue38 (id integer, data mediumblob)")
            c.execute("insert into issue38 values (1, %s)", (datum,))
        finally:
            c.execute("drop table issue38")

class TestGitHubIssues(base.UMySQLdbTestCase):
    def test_issue_66(self):
        conn = self.connections[0]
        c = conn.cursor()
        self.assertEqual(0, conn.insert_id())
        try:
            c.execute("create table issue66 (id integer primary key auto_increment, x integer)")
            c.execute("insert into issue66 (x) values (1)")
            c.execute("insert into issue66 (x) values (1)")
            self.assertEqual(2, conn.insert_id())
        finally:
            c.execute("drop table issue66")

__all__ = ["TestOldIssues", "TestNewIssues", "TestGitHubIssues"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_SSCursor
from . import base
import umysqldb.cursors

from nose.plugins.skip import SkipTest

raise SkipTest("umysql does not support server-side cursor")

class TestSSCursor(base.UMySQLdbTestCase):

    def test_SSCursor(self):
        affected_rows = 18446744073709551615
    
        conn = self.connections[0]
        data = [
            ('America', '', 'America/Jamaica'),
            ('America', '', 'America/Los_Angeles'),
            ('America', '', 'America/Lima'),
            ('America', '', 'America/New_York'),
            ('America', '', 'America/Menominee'),
            ('America', '', 'America/Havana'),
            ('America', '', 'America/El_Salvador'),
            ('America', '', 'America/Costa_Rica'),
            ('America', '', 'America/Denver'),
            ('America', '', 'America/Detroit'),]
    
        try:
            cursor = conn.cursor(umysqldb.cursors.SSCursor)
        
            # Create table
            cursor.execute(('CREATE TABLE tz_data ('
                'region VARCHAR(64),'
                'zone VARCHAR(64),'
                'name VARCHAR(64))'))
            
            # Test INSERT
            for i in data:
                cursor.execute('INSERT INTO tz_data VALUES (%s, %s, %s)', i)
                self.assertEqual(conn.affected_rows(), 1, 'affected_rows does not match')
            conn.commit()
            
            # Test fetchone()
            iter = 0
            cursor.execute('SELECT * FROM tz_data')
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                iter += 1
                
                # Test cursor.rowcount
                self.assertEqual(cursor.rowcount, affected_rows,
                    'cursor.rowcount != %s' % (str(affected_rows)))
                
                # Test cursor.rownumber
                self.assertEqual(cursor.rownumber, iter,
                    'cursor.rowcount != %s' % (str(iter)))
                
                # Test row came out the same as it went in
                self.assertEqual((row in data), True,
                    'Row not found in source data')
            
            # Test fetchall
            cursor.execute('SELECT * FROM tz_data')
            self.assertEqual(len(cursor.fetchall()), len(data),
                'fetchall failed. Number of rows does not match')
            
            # Test fetchmany
            cursor.execute('SELECT * FROM tz_data')
            self.assertEqual(len(cursor.fetchmany(2)), 2,
                'fetchmany failed. Number of rows does not match')
            
            # So MySQLdb won't throw "Commands out of sync"
            while True:
                res = cursor.fetchone()
                if res is None:
                    break
            
            # Test update, affected_rows()
            cursor.execute('UPDATE tz_data SET zone = %s', ['Foo'])
            conn.commit()
            self.assertEqual(cursor.rowcount, len(data),
                'Update failed. affected_rows != %s' % (str(len(data))))
            
            # Test executemany
            cursor.executemany('INSERT INTO tz_data VALUES (%s, %s, %s)', data)
            self.assertEqual(cursor.rowcount, len(data),
                'executemany failed. cursor.rowcount != %s' % (str(len(data))))
            
        finally:
            cursor.execute('DROP TABLE tz_data')
            cursor.close()

__all__ = ["TestSSCursor"]

if __name__ == "__main__":
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_umysqldb
from nose.tools import raises

import umysqldb
import umysqldb.err


@raises(umysqldb.err.OperationalError)
def test_access_denied_should_raise_OperationalError():
    umysqldb.connect(host='127.0.0.1', user='asdf', passwd='fdsa')

########NEW FILE########
__FILENAME__ = connections
import sys
import time
import datetime
import socket

import umysql
import pymysql.connections
from pymysql.constants import FIELD_TYPE

from .util import setdocstring
from .cursors import Cursor
from .err import (
    map_umysql_error_to_umysqldb_exception,
    map_runtime_error_to_umysqldb_exception,
    Error,
    OperationalError,
)
from .times import (
    encode_struct_time,
    encode_timedelta,
    encode_time,
    TimeDelta_or_None,
)


encoders = {
    time.struct_time: encode_struct_time,
    datetime.timedelta: encode_timedelta,
    datetime.time: encode_time,
}

decoders = {
    FIELD_TYPE.TIME: TimeDelta_or_None,
    FIELD_TYPE.NEWDECIMAL: float,
}


def notouch(x):
    return x


class ResultSet(object):

    def __init__(self, affected_rows=None, insert_id=None, description=None,
                 rows=None):
        self.affected_rows = affected_rows
        self.insert_id = insert_id
        self.description = description
        self.rows = rows


class Connection(pymysql.connections.Connection):

    """MySQL Database Connection Object"""

    @setdocstring(pymysql.connections.Connection.__init__)
    def __init__(self, *args, **kwargs):
        if 'cursorclass' not in kwargs:
            kwargs['cursorclass'] = Cursor
        if 'conv' not in kwargs:
            kwargs['conv'] = decoders
        if 'charset' not in kwargs:
            kwargs['charset'] = 'utf8'
        self._umysql_conn = umysql.Connection()
        super(Connection, self).__init__(*args, **kwargs)

    @setdocstring(pymysql.connections.Connection.set_charset)
    def set_charset(self, charset):
        if charset:
            self._umysql_conn.query("SET NAMES %s", (charset,))
            self.charset = charset

    @setdocstring(pymysql.connections.Connection.autocommit)
    def autocommit(self, value):
        self._umysql_conn.query("SET AUTOCOMMIT = %s", (value,))

    @setdocstring(pymysql.connections.Connection.commit)
    def commit(self):
        self.query('COMMIT')

    @setdocstring(pymysql.connections.Connection.rollback)
    def rollback(self):
        self.query("ROLLBACK")

    @setdocstring(pymysql.connections.Connection.close)
    def close(self):
        if not self._umysql_conn.is_connected():
            raise Error("Already closed")
        self._umysql_conn.close()

    def _connect(self):
        try:
            self._umysql_conn.connect(self.host, self.port, self.user,
                                      self.password, self.db or '', False, self.charset)
            if self.sql_mode is not None:
                c = self.cursor()
                c.execute("SET sql_mode=%s", (self.sql_mode,))
            if self.init_command is not None:
                c = self.cursor()
                c.execute(self.init_command)
                self.commit()
            if self.autocommit_mode is not None:
                self.autocommit(self.autocommit_mode)
        except socket.error, e:
            raise OperationalError(2003, "Can't connect to MySQL server on %r (%s)" % (
                self.host, e.args[0]))
        except umysql.Error, exc:
            traceback = sys.exc_info()[2]
            exc = map_umysql_error_to_umysqldb_exception(exc)
            raise exc, None, traceback

    # internal use only (called from cursor)
    def query(self, sql, args=()):
        args = self._convert_args(args)
        try:
            result_set = self._umysql_conn.query(sql, args)
        except umysql.Error, exc:
            traceback = sys.exc_info()[2]
            exc = map_umysql_error_to_umysqldb_exception(exc)
            raise exc, None, traceback
        except RuntimeError, exc:
            traceback = sys.exc_info()[2]
            exc = map_runtime_error_to_umysqldb_exception(exc)
            raise exc, None, traceback
        else:
            self._result = self._convert_result_set(result_set)
            return self._result.affected_rows

    def _convert_args(self, args):
        args = tuple(encoders.get(type(arg), notouch)(arg)
                     for arg in args)
        return args

    def _convert_result_set(self, result_set):
        if isinstance(result_set, tuple):
            rs = ResultSet(affected_rows=result_set[0],
                           insert_id=result_set[1])
        else:
            converters = [self.decoders.get(field[1]) for field in
                          result_set.fields]
            rows = tuple(tuple(conv(data) if conv and data is not None else data
                               for data, conv in zip(row, converters))
                         for row in result_set.rows)
            description = tuple(f + (None,) * (7 - len(f))
                                for f in result_set.fields)
            rs = ResultSet(description=description, rows=rows,
                           affected_rows=len(rows))
        return rs

    # _mysql support
    def get_proto_info(self):
        raise NotImplementedError("umysql has no proto info")

    def get_server_info(self):
        raise NotImplementedError("umysql has no server info")

    def thread_id(self):
        raise NotImplementedError("umysql has no thread info")

    def ping(self, reconnect=False):
        flag = False
        if self._umysql_conn.is_connected():
            try:
                self._umysql_conn.query("select 1;")
            except:
                self._umysql_conn.close()
                flag = True
        else:
            flag = True
        if flag:
            if reconnect:
                self._connect()
            else:
                raise OperationalError(2006, 'MySQL server has gone away')

########NEW FILE########
__FILENAME__ = constants
from pymysql.constants import *

########NEW FILE########
__FILENAME__ = converters
from pymysql.converters import *

########NEW FILE########
__FILENAME__ = cursors
import re
import pymysql.cursors
from .util import setdocstring

# Thank you MySQLdb for the kind regex
restr = r"""
    \s
    values
    \s*
    (
        \(
            [^()']*
            (?:
                (?:
                        (?:\(
                            # ( - editor hightlighting helper
                            [^)]*
                        \))
                    |
                        '
                            [^\\']*
                            (?:\\.[^\\']*)*
                        '
                )
                [^()']*
            )*
        \)
    )
"""

insert_values = re.compile(restr, re.S | re.I | re.X)


def _flatten(alist):
    result = []
    map(result.extend, alist)
    return tuple(result)


class Cursor(pymysql.cursors.Cursor):

    @setdocstring(pymysql.cursors.Cursor.execute)
    def execute(self, query, args=None):
        if args is None:
            args = ()
        elif not isinstance(args, (tuple, list, dict)):
            args = (args,)

        result = 0
        result = self._query(query, args)
        self._executed = query
        return result

    @setdocstring(pymysql.cursors.Cursor.executemany)
    def executemany(self, query, args):
        if not args:
            return
        db = self._get_db()
        charset = db.charset
        if isinstance(query, unicode):
            query = query.encode(charset)

        m = insert_values.search(query)
        if not m:
            self.rowcount = sum([self.execute(query, arg) for arg in args])
            return self.rowcount

        # Speed up a bulk insert MySQLdb style
        p = m.start(1)
        e = m.end(1)
        qv = m.group(1)
        sql_params = (qv for i in range(len(args)))
        multirow_query = '\n'.join([query[:p], ','.join(sql_params), query[e:]])
        return self.execute(multirow_query, _flatten(args))

    def _query(self, query, args=()):
        conn = self._get_db()
        conn.query(query, args)
        self.rowcount = conn._result.affected_rows
        self.rownumber = 0
        self.description = conn._result.description
        self.lastrowid = conn._result.insert_id
        self._rows = conn._result.rows
        self._has_next = 0
        return self.rowcount


class DictCursor(Cursor):

    """A cursor which returns results as a dictionary"""

    def execute(self, query, args=None):
        result = super(DictCursor, self).execute(query, args)
        if self.description:
            self._fields = [field[0] for field in self.description]
        return result

    def fetchone(self):
        ''' Fetch the next row '''
        self._check_executed()
        if self._rows is None or self.rownumber >= len(self._rows):
            return None
        result = dict(zip(self._fields, self._rows[self.rownumber]))
        self.rownumber += 1
        return result

    def fetchmany(self, size=None):
        ''' Fetch several rows '''
        self._check_executed()
        if self._rows is None:
            return None
        end = self.rownumber + (size or self.arraysize)
        result = [dict(zip(self._fields, r))
                  for r in self._rows[self.rownumber:end]]
        self.rownumber = min(end, len(self._rows))
        return tuple(result)

    def fetchall(self):
        ''' Fetch all the rows '''
        self._check_executed()
        if self._rows is None:
            return None
        if self.rownumber:
            result = [dict(zip(self._fields, r))
                      for r in self._rows[self.rownumber:]]
        else:
            result = [dict(zip(self._fields, r)) for r in self._rows]
        self.rownumber = len(self._rows)
        return tuple(result)

########NEW FILE########
__FILENAME__ = err
from pymysql.err import *

def map_umysql_error_to_umysqldb_exception(umysql_exc):
    errorclass = error_map.get(umysql_exc.args[0])
    if errorclass:
        return errorclass(*umysql_exc.args)

    # couldn't find the right error number
    code, message  = umysql_exc.args[:2]
    if code == 0 and message.startswith("Connection reset by peer"):
        return OperationalError(2013, "Lost connection to MySQL server during query")

    return InternalError(*umysql_exc.args)

def map_runtime_error_to_umysqldb_exception(exc):
    if exc.args == ('Not connected',):
        return ProgrammingError("cursor closed")
    return exc

########NEW FILE########
__FILENAME__ = times
import time
from datetime import datetime, date, timedelta
import math

Timestamp = datetime

def encode_struct_time(obj):
    return time.strftime("%Y-%m-%d %H:%M:%S", obj)

def encode_timedelta(delta):
    seconds = int(delta.seconds) % 60
    minutes = int(delta.seconds // 60) % 60
    hours = int(delta.seconds // 3600) % 24 + int(delta.days) * 24
    return "%02d:%02d:%02d" % (hours, minutes, seconds)

def encode_time(obj):
    s = "%02d:%02d:%02d" % (int(obj.hour), int(obj.minute), int(obj.second))
    if obj.microsecond:
        s += ".%f" % obj.microsecond
    return s

def Date_or_None(s):
    try: return date(*[ int(x) for x in s.split('-',2)])
    except: return None


def DateTime_or_None(s):
    if ' ' in s:
        sep = ' '
    elif 'T' in s:
        sep = 'T'
    else:
        return Date_or_None(s)

    try:
        d, t = s.split(sep, 1)
        return datetime(*[ int(x) for x in d.split('-')+t.split(':') ])
    except:
        return Date_or_None(s)

def TimeDelta_or_None(s):
    try:
        h, m, s = s.split(':')
        h, m, s = int(h), int(m), float(s)
        td = timedelta(hours=abs(h), minutes=m, seconds=int(s),
                       microseconds=int(math.modf(s)[0] * 1000000))
        if h < 0:
            return -td
        else:
            return td
    except ValueError:
        # unpacking or int/float conversion failed
        return None

def mysql_timestamp_converter(s):
    """Convert a MySQL TIMESTAMP to a Timestamp object."""
    # MySQL>4.1 returns TIMESTAMP in the same format as DATETIME
    if s[4] == '-': return DateTime_or_None(s)
    s += "0"*(14-len(s))
    parts = [int(x) for x in (s[:4],s[4:6],s[6:8],s[8:10],s[10:12],s[12:14])
             if x]
    try:
        return Timestamp(*parts)
    except Exception:
        return None

########NEW FILE########
__FILENAME__ = util
def setdocstring(src):
    def deco(func):
        func.__doc__ = src.__doc__
        return func
    return deco

########NEW FILE########
