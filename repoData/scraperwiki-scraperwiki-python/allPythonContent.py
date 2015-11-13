__FILENAME__ = runlog
"""
Special module, if you import this, you will get a run log written
to scraperwiki.sqlite in a table named _sw_runlog on succesful exits
or exceptions.
"""

import atexit
import datetime
import inspect
import os
import sys
import traceback
import uuid
import functools

import scraperwiki

_successful_exit = True
_hook_installed = False

def make_excepthook(inner_excepthook, run_id):

    def sw_excepthook(type, value, tb):
        """Log uncaught exceptions to scraperwiki.sqlite file."""

        global _successful_exit
        _successful_exit = False

        try:
            first_frame_tuple = inspect.getouterframes(tb.tb_frame)[-1]
            (_frame, filename, _lineno, _where, _code, _) = first_frame_tuple

            type_name = type.__module__ + '.' + type.__name__

            message = repr(value)

            write_runlog(filename, ''.join(traceback.format_tb(tb)),
                type_name, message, False, run_id)

            scraperwiki.status('error')
        finally:
            inner_excepthook(type, value, tb)

    return sw_excepthook

def successful_exit(run_id=""):
    if _successful_exit:

        filename = sys.argv[0]

        # Invoking a seperate process because sqlite breaks if run
        # during an atexit hook
        os.system(("python -c 'from sys import argv; "
            "import scraperwiki.runlog as R; "
            "R.write_runlog(argv[-2], run_id=argv[-1])' -- '{0}' '{1}'")
            .format(filename, run_id))

def write_runlog(filename, traceback="", exception_type="", exception_value="",
    success=True, run_id=""):

    d = dict(
            time=datetime.datetime.now(),
            path=filename,
            pwd=os.getcwd(),
            traceback=traceback,
            exception_type=exception_type,
            exception_value=exception_value,
            success=bool(success),
            run_id=run_id
        )

    scraperwiki.sql.save([], d, table_name="_sw_runlog")

def setup():
    """
    Initialize scraperwiki exception/success hook. Idempotent.
    """

    global _hook_installed
    if _hook_installed:
        return

    run_id = str(uuid.uuid4())

    _hook_installed = True
    sys.excepthook = make_excepthook(sys.excepthook, run_id)
    atexit.register(functools.partial(successful_exit, run_id))

    return run_id

########NEW FILE########
__FILENAME__ = sqlite
from dumptruck import DumpTruck
import datetime
import re
import os

DATABASE_NAME = os.environ.get("SCRAPERWIKI_DATABASE_NAME", "scraperwiki.sqlite")
DATABASE_TIMEOUT = float(os.environ.get("SCRAPERWIKI_DATABASE_TIMEOUT", 300))

def _connect(dbname=DATABASE_NAME, timeout=DATABASE_TIMEOUT):
  'Initialize the database (again). This is mainly for testing'
  global dt
  dt = DumpTruck(dbname=dbname,
                 adapt_and_convert=False,
                 timeout=timeout)

_connect()

def execute(sqlquery, data=[], verbose=1):
    """ Emulate scraperwiki as much as possible by mangling dumptruck result """
    # Allow for a non-list to be passed as data.
    if type(data) != list and type(data) != tuple:
        data = [data]

    result = dt.execute(sqlquery, data, commit=False)
    # None (non-select) and empty list (select) results
    if not result:
        return {u'data': [], u'keys': []}
    dtos = lambda d: str(d) if isinstance(d, datetime.date) else d
    # Select statement with results
    return {u'data': map(lambda row: map(dtos, row.values()), result),
            u'keys': result[0].keys()}

def save(unique_keys, data, table_name="swdata", verbose=2, date=None):
    if not data:
        return
    dt.create_table(data, table_name = table_name, error_if_exists = False)
    if unique_keys != []:
        dt.create_index(unique_keys, table_name, unique = True, if_not_exists = True)
    return dt.upsert(data, table_name = table_name)

def commit(verbose=1):
    dt.commit()

def select(sqlquery, data=[], verbose=1):
    sqlquery = "select %s" % sqlquery   # maybe check if select or another command is there already?
    result = dt.execute(sqlquery, data, commit = False)
    # Convert dates to strings to conform to scraperwiki classic
    if result != []:
      keys = result[0].keys()
      for row in result:
        for key in keys:
          if isinstance(row[key], datetime.date):
            row[key] = str(row[key])
    return result

def show_tables(dbname=""):
    name = "sqlite_master"
    if dbname:
        name = "`%s`.%s" % (dbname, name)
    response = select('name, sql from %s where type = "table";' % name)
    return {row['name']: row['sql'] for row in response}

def save_var(name, value, verbose=2):
    data = dt.save_var(name, value)
    dt.execute(u"CREATE TABLE IF NOT EXISTS swvariables (`value_blob` blob, `type` text, `name` text PRIMARY KEY)", commit = False)
    dt.execute(u'INSERT OR REPLACE INTO swvariables SELECT `value`, `type`, `key` FROM `%s`' % dt._DumpTruck__vars_table, commit = False)
    dt.execute(u'DROP TABLE `%s`' % dt._DumpTruck__vars_table, commit = False)
    dt.commit()
    return data

def get_var(name, default=None, verbose=2):
    if 'swvariables' not in show_tables(): # this should be unecessary
        return default
    dt.execute(u"CREATE TABLE IF NOT EXISTS swvariables (`value_blob` blob, `type` text, `name` text PRIMARY KEY)", commit = False)
    dt.execute(u"CREATE TEMPORARY TABLE IF NOT EXISTS %s (`value` blob, `type` text, `key` text PRIMARY KEY)" % dt._DumpTruck__vars_table, commit = False)

    sql = u'INSERT INTO `%s` (value, type, key) SELECT `value_blob`, `type`, `name` FROM `swvariables`' % dt._DumpTruck__vars_table
    dt.execute(sql, commit = False)
    try:
        value = dt.get_var(name)
    except NameError:
        dt.connection.rollback()
        return default
    dt.execute(u'DROP TABLE `%s`' % dt._DumpTruck__vars_table, commit = False)
    dt.commit()
    return value

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python2
# utils.py
# David Jones, ScraperWiki Limited
# Thomas Levine, ScraperWiki Limited

'''
Local version of ScraperWiki Utils, documentation here:
https://scraperwiki.com/docs/python/python_help_documentation/
'''

import os
import sys
import warnings
import tempfile
import urllib, urllib2
import requests

def scrape(url, params = None, user_agent = None) :
    '''
    Scrape a URL optionally with parameters.
    This is effectively a wrapper around urllib2.orlopen.
    '''

    headers = {}

    if user_agent:
        headers['User-Agent'] = user_agent

    data = params and urllib.urlencode(params) or None
    req = urllib2.Request(url, data=data, headers=headers)
    f = urllib2.urlopen(req)

    text = f.read()
    f.close()

    return text

def pdftoxml(pdfdata):
    """converts pdf file to xml file"""
    pdffout = tempfile.NamedTemporaryFile(suffix='.pdf')
    pdffout.write(pdfdata)
    pdffout.flush()

    xmlin = tempfile.NamedTemporaryFile(mode='r', suffix='.xml')
    tmpxml = xmlin.name # "temph.xml"
    cmd = 'pdftohtml -xml -nodrm -zoom 1.5 -enc UTF-8 -noframes "%s" "%s"' % (pdffout.name, os.path.splitext(tmpxml)[0])
    cmd = cmd + " >/dev/null 2>&1" # can't turn off output, so throw away even stderr yeuch
    os.system(cmd)

    pdffout.close()
    #xmlfin = open(tmpxml)
    xmldata = xmlin.read()
    xmlin.close()
    return xmldata

def _in_box():
  return os.environ.get('HOME', None) == '/home'

def status(type, message=None):
    assert type in ['ok', 'error']

    # if not running in a ScraperWiki platform box, silently do nothing
    if not _in_box():
        return "Not in box"

    url = os.environ.get("SW_STATUS_URL", "https://scraperwiki.com/api/status")
    if url == "OFF":
        # For development mode
        return

    # send status update to the box
    r = requests.post(url, data={'type':type, 'message':message})
    r.raise_for_status()
    return r.content





########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
from unittest import TestCase, main
from json import loads, dumps
from subprocess import Popen, PIPE
from textwrap import dedent
import sqlite3
import os
import shutil
import datetime
import urllib2
import re

# This library
import scraperwiki


class TestDb(TestCase):
    DBNAME = 'scraperwiki.sqlite'

    def setUp(self):
        self.cleanUp()
        scraperwiki.sqlite._connect(self.DBNAME)

    def tearDown(self):
        self.cleanUp()

    def cleanUp(self):
        "Clean up temporary files, then reinitialize."
        if self.DBNAME != ':memory:':
            try:
                os.remove(self.DBNAME)
            except OSError:
                pass

class TestException(TestDb):
    def testExceptionSaved(self):
        script = dedent("""
            import scraperwiki.runlog
            print scraperwiki.runlog.setup()
            raise ValueError
        """)
        process = Popen(["python", "-c", script], stdout=PIPE, stderr=PIPE, stdin=open("/dev/null"))
        stdout, stderr = process.communicate()

        assert 'Traceback' in stderr, "stderr should contain the original Python traceback"
        match = re.match(r'^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}', stdout)
        assert match, "runlog.setup() should return a run_id"

        l = scraperwiki.sqlite.select("exception_type, run_id, time from _sw_runlog order by time desc limit 1")

        # Check that some record is stored.
        assert l
        # Check that the exception name appears.
        assert 'ValueError' in l[0]['exception_type'], "runlog should save exception types to the database"
        # Check that the run_id from earlier has been saved.
        assert match.group() == l[0].get('run_id'), "runlog should save a run_id to the database"
        # Check that the time recorded is relatively recent.
        time_str = l[0]['time']
        then = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
        assert (datetime.datetime.now() - then).total_seconds() < 5*60, "run log should save a time to the database"

    def testRunlogSuccess(self):
        script = dedent("""
            import scraperwiki.runlog
            print scraperwiki.runlog.setup()
        """)
        process = Popen(["python", "-c", script], stdout=PIPE, stderr=PIPE, stdin=open("/dev/null"))
        stdout, stderr = process.communicate()

        l = scraperwiki.sqlite.select("time, run_id, success from _sw_runlog order by time desc limit 1")

        # Check that some record is stored.
        assert l
        # Check that it has saved a success column.
        assert l[0]['success']
        # Check that a run_id has been saved.
        match = re.match(r'^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}', stdout)
        assert match.group() == l[0].get('run_id'), "runlog should save a run_id to the database"
        # Check that the time is relatively recent.
        then = datetime.datetime.strptime(l[0]['time'], '%Y-%m-%d %H:%M:%S.%f')
        assert (datetime.datetime.now() - then).total_seconds() < 5*60

class TestSaveGetVar(TestDb):

    def savegetvar(self, var):
        scraperwiki.sqlite.save_var("weird", var)
        self.assertEqual(scraperwiki.sqlite.get_var("weird"), var)

    def test_string(self):
        self.savegetvar("asdio")

    def test_int(self):
        self.savegetvar(1)

    # def test_list(self):
    #  self.savegetvar([1,2,3,4])

    # def test_dict(self):
    #  self.savegetvar({"abc":"def"})

    def test_date(self):
        date1 = datetime.datetime.now()
        date2 = datetime.date.today()
        scraperwiki.sqlite.save_var("weird", date1)
        self.assertEqual(scraperwiki.sqlite.get_var("weird"), unicode(date1))
        scraperwiki.sqlite.save_var("weird", date2)
        self.assertEqual(scraperwiki.sqlite.get_var("weird"), unicode(date2))

    def test_save_multiple_values(self):
        scraperwiki.sqlite.save_var('foo', 'hello')
        scraperwiki.sqlite.save_var('bar', 'goodbye')

        self.assertEqual('hello', scraperwiki.sqlite.get_var('foo'))
        self.assertEqual('goodbye', scraperwiki.sqlite.get_var('bar'))


class TestGetNonexistantVar(TestDb):

    def test_get(self):
        self.assertIsNone(scraperwiki.sqlite.get_var('meatball'))


class TestSaveVar(TestDb):

    def setUp(self):
        super(TestSaveVar, self).setUp()
        scraperwiki.sqlite.save_var("birthday", "November 30, 1888")
        connection = sqlite3.connect(self.DBNAME)
        self.cursor = connection.cursor()

    def test_insert(self):
        self.cursor.execute("SELECT name, value_blob, type FROM `swvariables`")
        observed = self.cursor.fetchall()
        expected = [("birthday", "November 30, 1888", "text",)]
        self.assertEqual(observed, expected)


class SaveAndCheck(TestDb):

    def save_and_check(self, dataIn, tableIn, dataOut, tableOut=None, twice=True):
        if tableOut == None:
            tableOut = '[' + tableIn + ']'

        # Insert
        scraperwiki.sqlite.save([], dataIn, tableIn)

        # Observe with pysqlite
        connection = sqlite3.connect(self.DBNAME)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM %s" % tableOut)
        observed1 = cursor.fetchall()
        connection.close()

        if twice:
            # Observe with DumpTruck
            observed2 = scraperwiki.sqlite.select('* FROM %s' % tableOut)

            # Check
            expected1 = dataOut
            expected2 = [dataIn] if type(dataIn) == dict else dataIn

            self.assertListEqual(observed1, expected1)
            self.assertListEqual(observed2, expected2)


class SaveAndSelect(TestDb):

    def save_and_select(self, d):
        scraperwiki.sqlite.save([], {"foo": d})

        observed = scraperwiki.sqlite.select('* from swdata')[0]['foo']
        self.assertEqual(d, observed)


class TestUniqueKeys(SaveAndSelect):

    def test_empty(self):
        scraperwiki.sqlite.save([], {"foo": 3}, u'Chico')
        observed = scraperwiki.sqlite.execute(u'PRAGMA index_list(Chico)')
        self.assertEqual(observed, {u'data': [], u'keys': []})

    def test_two(self):
        scraperwiki.sqlite.save(['foo', 'bar'], {"foo": 3, 'bar': 9}, u'Harpo')
        observed = scraperwiki.sqlite.execute(
            u'PRAGMA index_info(Harpo_foo_bar)')

        # Indexness
        self.assertIsNotNone(observed)

        # Indexed columns
        expected = {
            'keys': [u'seqno', u'cid', u'name'],
            'data': [
                [0, 0, u'foo'],
                [1, 1, u'bar'],
            ]
        }
        self.assertDictEqual(observed, expected)

        # Uniqueness
        indices = scraperwiki.sqlite.execute('PRAGMA index_list(Harpo)')
        namecol = indices[u"keys"].index(u'name')
        for index in indices[u"data"]:
            if index[namecol] == u'Harpo_foo_bar':
                break
        else:
            index = {}

        uniquecol = indices[u"keys"].index(u'unique')
        self.assertEqual(index[uniquecol], 1)


class Nest(SaveAndCheck):

    'This needs to be verified with actual ScraperWiki.'

    def _casting(self, thething):
        self.save_and_check(
            {"almonds": thething},
            'almonds',
            [(repr(thething),)]
        )

# class TestList(Nest):
#  def test_list(self):
#    self._casting(['a', 'b', 'c'])

# class TestDict(Nest):
#  def test_dict(self):
#    self._casting({'a': 3, 5:'b', 'c': []})

# class TestMultipleColumns(SaveAndSelect):
#  def test_save(self):
#    self.save_and_select({"firstname":"Robert","lastname":"LeTourneau"})


class TestSave(SaveAndCheck):

    def test_save_int(self):
        self.save_and_check(
            {"model-number": 293}, "model-numbers", [(293,)]
        )

    def test_save_string(self):
        self.save_and_check(
            {"lastname": "LeTourneau"}, "diesel-engineers", [
                (u'LeTourneau',)]
        )

    def test_save_twice(self):
        self.save_and_check(
            {"modelNumber": 293}, "model-numbers", [(293,)]
        )
        self.save_and_check(
            {"modelNumber": 293}, "model-numbers", [(293,), (293,)], twice=False
        )

    def test_save_true(self):
        self.save_and_check(
            {"a": True}, "a", [(1,)]
        )

    def test_save_true(self):
        self.save_and_check(
            {"a": False}, "a", [(0,)]
        )


class TestQuestionMark(TestDb):

    def test_one_question_mark_with_nonlist(self):
        scraperwiki.sqlite.execute('create table zhuozi (a text);')
        scraperwiki.sqlite.execute('insert into zhuozi values (?)', 'apple')
        observed = scraperwiki.sqlite.select('* from zhuozi')
        self.assertListEqual(observed, [{'a': 'apple'}])

    def test_one_question_mark_with_list(self):
        scraperwiki.sqlite.execute('create table zhuozi (a text);')
        scraperwiki.sqlite.execute('insert into zhuozi values (?)', ['apple'])
        observed = scraperwiki.sqlite.select('* from zhuozi')
        self.assertListEqual(observed, [{'a': 'apple'}])

    def test_multiple_question_marks(self):
        scraperwiki.sqlite.execute('create table zhuozi (a text, b text);')
        scraperwiki.sqlite.execute(
            'insert into zhuozi values (?, ?)', ['apple', 'banana'])
        observed = scraperwiki.sqlite.select('* from zhuozi')
        self.assertListEqual(observed, [{'a': 'apple', 'b': 'banana'}])


class TestDateTime(TestDb):

    def rawdate(self, table="swdata", column="datetime"):
        connection = sqlite3.connect(self.DBNAME)
        cursor = connection.cursor()
        cursor.execute("SELECT %s FROM %s LIMIT 1" % (column, table))
        rawdate = cursor.fetchall()[0][0]
        connection.close()
        return rawdate

    def test_save_date(self):
        d = datetime.datetime.strptime('1990-03-30', '%Y-%m-%d').date()
        scraperwiki.sqlite.save([], {"birthday": d})
        self.assertEqual(str(d), self.rawdate(column="birthday"))
        self.assertEqual(
            [{u'birthday': str(d)}], scraperwiki.sqlite.select("* from swdata"))
        self.assertEqual(
            {u'keys': [u'birthday'], u'data': [[str(d)]]}, scraperwiki.sqlite.execute("select * from swdata"))

    def test_save_datetime(self):
        d = datetime.datetime.strptime('1990-03-30', '%Y-%m-%d')
        scraperwiki.sqlite.save([], {"birthday": d})
        self.assertEqual(str(d), self.rawdate(column="birthday"))
        self.assertEqual(
            [{u'birthday': str(d)}], scraperwiki.sqlite.select("* from swdata"))
        self.assertEqual(
            {u'keys': [u'birthday'], u'data': [[str(d)]]}, scraperwiki.sqlite.execute("select * from swdata"))


class TestStatus(TestCase):

    'Test that the status endpoint works.'

    def test_does_nothing_if_called_outside_box(self):
        scraperwiki.status('ok')

    def test_raises_exception_with_invalid_type_field(self):
        self.assertRaises(AssertionError, scraperwiki.status, 'hello')

    # XXX neeed some mocking tests for case of run inside a box


class TestImports(TestCase):

    'Test that all module contents are imported.'

    def setUp(self):
        self.sw = __import__('scraperwiki')

    def test_import_scraperwiki_root(self):
        self.sw.scrape

    def test_import_scraperwiki_sqlite(self):
        self.sw.sqlite

    def test_import_scraperwiki_sql(self):
        self.sw.sql

    def test_import_scraperwiki_status(self):
        self.sw.status

    def test_import_scraperwiki_utils(self):
        self.sw.utils

    def test_import_scraperwiki_special_utils(self):
        self.sw.pdftoxml

if __name__ == '__main__':
    main()

########NEW FILE########
