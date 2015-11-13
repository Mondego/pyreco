__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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

$Id: bootstrap.py 102545 2009-08-06 14:49:47Z chrisw $
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser()
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=True,
                   help="Use Disribute rather than Setuptools.")

options, args = parser.parse_args()

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse(requirement)).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse(requirement)).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = column_guesser
"""
Splits tabular data in the form of a list of rows into columns;
makes guesses about the role of each column for plotting purposes
(X values, Y values, and text labels).
"""

class Column(list):
    'Store a column of tabular data; record its name and whether it is numeric'
    is_quantity = True
    name = ''
    def __init__(self, *arg, **kwarg):
        pass
        

def is_quantity(val):
    """Is ``val`` a quantity (int, float, datetime, etc) (not str, bool)?
    
    Relies on presence of __sub__.
    """
    return hasattr(val, '__sub__')

class ColumnGuesserMixin(object):
    """
    plot: [x, y, y...], y
    pie: ... y
    """
    def _build_columns(self):
        self.columns = [Column() for col in self.keys]
        for row in self:
            for (col_idx, col_val) in enumerate(row):
                col = self.columns[col_idx]
                col.append(col_val)
                if (col_val is not None) and (not is_quantity(col_val)):
                    col.is_quantity = False
            
        for (idx, key_name) in enumerate(self.keys):
            self.columns[idx].name = key_name
            
        self.x = Column()
        self.ys = []
            
    def _get_y(self):
        for idx in range(len(self.columns)-1,-1,-1):
            if self.columns[idx].is_quantity:
                self.ys.insert(0, self.columns.pop(idx))
                return True

    def _get_x(self):            
        for idx in range(len(self.columns)):
            if self.columns[idx].is_quantity:
                self.x = self.columns.pop(idx)
                return True
    
    def _get_xlabel(self, xlabel_sep=" "):
        self.xlabels = []
        if self.columns:
            for row_idx in range(len(self.columns[0])):
                self.xlabels.append(xlabel_sep.join(
                    str(c[row_idx]) for c in self.columns))
        self.xlabel = ", ".join(c.name for c in self.columns)
      
    def _guess_columns(self):
        self._build_columns()
        self._get_y()
        if not self.ys:
            raise AttributeError("No quantitative columns found for chart")
        
    def guess_pie_columns(self, xlabel_sep=" "):
        """
        Assigns x, y, and x labels from the data set for a pie chart.
        
        Pie charts simply use the last quantity column as 
        the pie slice size, and everything else as the
        pie slice labels.
        """
        self._guess_columns()
        self._get_xlabel(xlabel_sep)
        
    def guess_plot_columns(self):
        """
        Assigns ``x`` and ``y`` series from the data set for a plot.
        
        Plots use:
          the rightmost quantity column as a Y series
          optionally, the leftmost quantity column as the X series
          any other quantity columns as additional Y series
        """
        self._guess_columns()
        self._get_x()
        while self._get_y():
            pass
########NEW FILE########
__FILENAME__ = connection
import sqlalchemy

class Connection(object):
    current = None
    connections = {}
    @classmethod
    def tell_format(cls):
        return "Format: (postgresql|mysql)://username:password@hostname/dbname, or one of %s" \
               % str(cls.connections.keys())
    def __init__(self, connect_str=None):
        try:
            engine = sqlalchemy.create_engine(connect_str)
        except: # TODO: bare except; but what's an ArgumentError?
            print(self.tell_format())
            raise 
        self.metadata = sqlalchemy.MetaData(bind=engine)
        self.name = self.assign_name(engine)
        self.session = engine.connect() 
        self.connections[self.name] = self
        self.connections[str(self.metadata.bind.url)] = self
        Connection.current = self
    @classmethod
    def get(cls, descriptor):
        if isinstance(descriptor, Connection):
            cls.current = descriptor
        elif descriptor:
            conn = cls.connections.get(descriptor) or \
                   cls.connections.get(descriptor.lower()) 
            if conn:
                cls.current = conn
            else:
                cls.current = Connection(descriptor)
        if cls.current:
            return cls.current
        else:
            raise Exception(cls.tell_format())
    @classmethod
    def assign_name(cls, engine):
        core_name = '%s@%s' % (engine.url.username, engine.url.database)
        incrementer = 1
        name = core_name
        while name in cls.connections:
            name = '%s_%d' % (core_name, incrementer)
            incrementer += 1
        return name

########NEW FILE########
__FILENAME__ = magic
from IPython.core.magic import Magics, magics_class, cell_magic, line_magic, needs_local_scope
from IPython.config.configurable import Configurable
from IPython.utils.traitlets import Bool, Int, Unicode

from sqlalchemy.exc import ProgrammingError, OperationalError

import sql.connection
import sql.parse
import sql.run


@magics_class
class SqlMagic(Magics, Configurable):
    """Runs SQL statement on a database, specified by SQLAlchemy connect string.

    Provides the %%sql magic."""

    autolimit = Int(0, config=True, help="Automatically limit the size of the returned result sets")
    style = Unicode('DEFAULT', config=True, help="Set the table printing style to any of prettytable's defined styles (currently DEFAULT, MSWORD_FRIENDLY, PLAIN_COLUMNS, RANDOM)")
    short_errors = Bool(True, config=True, help="Don't display the full traceback on SQL Programming Error")
    displaylimit = Int(0, config=True, help="Automatic,ally limit the number of rows displayed (full result set is still stored)")
    autopandas = Bool(False, config=True, help="Return Pandas DataFrames instead of regular result sets")
    feedback = Bool(True, config=True, help="Print number of rows affected by DML")

    def __init__(self, shell):
        Configurable.__init__(self, config=shell.config)
        Magics.__init__(self, shell=shell)

        # Add ourself to the list of module configurable via %config
        self.shell.configurables.append(self)

    @needs_local_scope
    @line_magic('sql')
    @cell_magic('sql')
    def execute(self, line, cell='', local_ns={}):
        """Runs SQL statement against a database, specified by SQLAlchemy connect string.

        If no database connection has been established, first word
        should be a SQLAlchemy connection string, or the user@db name
        of an established connection.

        Examples::

          %%sql postgresql://me:mypw@localhost/mydb
          SELECT * FROM mytable

          %%sql me@mydb
          DELETE FROM mytable

          %%sql
          DROP TABLE mytable

        SQLAlchemy connect string syntax examples:

          postgresql://me:mypw@localhost/mydb
          sqlite://
          mysql+pymysql://me:mypw@localhost/mydb

        """
        # save globals and locals so they can be referenced in bind vars
        user_ns = self.shell.user_ns
        user_ns.update(local_ns)

        parsed = sql.parse.parse('%s\n%s' % (line, cell))
        conn = sql.connection.Connection.get(parsed['connection'])
        try:
            result = sql.run.run(conn, parsed['sql'], self, user_ns)
            return result
        except (ProgrammingError, OperationalError) as e:
            # Sqlite apparently return all errors as OperationalError :/
            if self.short_errors:
                print(e)
            else:
                raise


def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(SqlMagic)

########NEW FILE########
__FILENAME__ = parse
import re

def parse(cell):
    parts = cell.split(None, 1)
    if not parts:
        return {'connection': '', 'sql': ''}
    if '@' in parts[0] or '://' in parts[0]:
        connection = parts[0]
        if len(parts) > 1:
            sql = parts[1]
        else:
            sql = ''
    else:
        connection = ''
        sql = cell
    return {'connection': connection.strip(),
            'sql': sql.strip()
            }
   
########NEW FILE########
__FILENAME__ = run
import functools
import operator
import types
import csv
import cStringIO
import codecs
import os.path
import sqlalchemy
import sqlparse
import prettytable
from .column_guesser import ColumnGuesserMixin


def unduplicate_field_names(field_names):
    """Append a number to duplicate field names to make them unique. """
    res = []
    for k in field_names:
        if k in res:
            i = 1
            while k + '_' + str(i) in res:
                i += 1
            k += '_' + str(i)
        res.append(k)
    return res

class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        _row = [s.encode("utf-8")
                if hasattr(s, "encode")
                else s
                for s in row]
        self.writer.writerow(_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class CsvResultDescriptor(object):
    """Provides IPython Notebook-friendly output for the feedback after a ``.csv`` called."""
    def __init__(self, file_path):
        self.file_path = file_path
    def __repr__(self):
        return 'CSV results at %s' % os.path.join(os.path.abspath('.'), self.file_path)
    def _repr_html_(self):
        return '<a href="%s">CSV results</a>' % os.path.join('.', 'files', self.file_path)
    
class ResultSet(list, ColumnGuesserMixin):
    """
    Results of a SQL query.
    
    Can access rows listwise, or by string value of leftmost column.
    """
    def __init__(self, sqlaproxy, sql, config):
        self.keys = sqlaproxy.keys()
        self.sql = sql
        self.config = config
        self.limit = config.autolimit
        style_name = config.style
        self.style = prettytable.__dict__[style_name.upper()]
        if sqlaproxy.returns_rows:
            if self.limit:
                list.__init__(self, sqlaproxy.fetchmany(size=self.limit))
            else:
                list.__init__(self, sqlaproxy.fetchall())
            self.field_names = unduplicate_field_names(self.keys)
            self.pretty = prettytable.PrettyTable(self.field_names)
            if not config.autopandas:
                for row in self[:config.displaylimit or None]:
                    self.pretty.add_row(row)
            self.pretty.set_style(self.style)
        else:
            list.__init__(self, [])
            self.pretty = None
    def _repr_html_(self):
        if self.pretty:
            result = self.pretty.get_html_string()
            if self.config.displaylimit and len(self) > self.config.displaylimit:
                result = '%s\n<span style="font-style:italic;text-align:center;">%d rows, truncated to displaylimit of %d</span>' % (
                    result, len(self), self.config.displaylimit)
            return result
        else:
            return None
    def __str__(self, *arg, **kwarg):
        return str(self.pretty or '')
    def __getitem__(self, key):
        """
        Access by integer (row position within result set)
        or by string (value of leftmost column)
        """
        try:
            return list.__getitem__(self, key)
        except TypeError:
            result = [row for row in self if row[0] == key]
            if not result:
                raise KeyError(key)
            if len(result) > 1:
                raise KeyError('%d results for "%s"' % (len(result), key))
            return result[0]
    def DataFrame(self):
        "Returns a Pandas DataFrame instance built from the result set."
        import pandas as pd
        frame = pd.DataFrame(self, columns=(self and self.keys) or [])
        return frame
    def pie(self, key_word_sep=" ", title=None, **kwargs):
        """Generates a pylab pie chart from the result set.
       
        ``matplotlib`` must be installed, and in an
        IPython Notebook, inlining must be on::
        
            %%matplotlib inline
            
        Values (pie slice sizes) are taken from the 
        rightmost column (numerical values required).
        All other columns are used to label the pie slices.
        
        Parameters
        ----------
        key_word_sep: string used to separate column values
                      from each other in pie labels
        title: Plot title, defaults to name of value column

        Any additional keyword arguments will be passsed 
        through to ``matplotlib.pylab.pie``.
        """
        self.guess_pie_columns(xlabel_sep=key_word_sep)
        import matplotlib.pylab as plt
        pie = plt.pie(self.ys[0], labels=self.xlabels, **kwargs)
        plt.title(title or self.ys[0].name)
        return pie
  
    def plot(self, title=None, **kwargs):
        """Generates a pylab plot from the result set.
       
        ``matplotlib`` must be installed, and in an
        IPython Notebook, inlining must be on::
        
            %%matplotlib inline
           
        The first and last columns are taken as the X and Y
        values.  Any columns between are ignored.
        
        Parameters
        ----------
        title: Plot title, defaults to names of Y value columns

        Any additional keyword arguments will be passsed 
        through to ``matplotlib.pylab.plot``.
        """
        import matplotlib.pylab as plt
        self.guess_plot_columns()
        self.x = self.x or range(len(self.ys[0]))
        coords = reduce(operator.add, [(self.x, y) for y in self.ys])
        plot = plt.plot(*coords, **kwargs)
        if hasattr(self.x, 'name'):
            plt.xlabel(self.x.name)
        ylabel = ", ".join(y.name for y in self.ys)
        plt.title(title or ylabel)
        plt.ylabel(ylabel)
        return plot
    
    def bar(self, key_word_sep = " ", title=None, **kwargs):
        """Generates a pylab bar plot from the result set.
       
        ``matplotlib`` must be installed, and in an
        IPython Notebook, inlining must be on::
        
            %%matplotlib inline
           
        The last quantitative column is taken as the Y values;
        all other columns are combined to label the X axis. 
        
        Parameters
        ----------
        title: Plot title, defaults to names of Y value columns
        key_word_sep: string used to separate column values
                      from each other in labels
                      
        Any additional keyword arguments will be passsed 
        through to ``matplotlib.pylab.bar``.
        """
        import matplotlib.pylab as plt
        self.guess_pie_columns(xlabel_sep=key_word_sep)
        plot = plt.bar(range(len(self.ys[0])), self.ys[0], **kwargs)
        if self.xlabels:
            plt.xticks(range(len(self.xlabels)), self.xlabels,
                       rotation=45)
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ys[0].name)
        return plot        
    
    def csv(self, filename=None, **format_params):
        """Generate results in comma-separated form.  Write to ``filename`` if given.
           Any other parameterw will be passed on to csv.writer."""
        if not self.pretty:
            return None # no results
        if filename:
            outfile = open(filename, 'w')
        else:
            outfile = cStringIO.StringIO()
        writer = UnicodeWriter(outfile, **format_params)
        writer.writerow(self.field_names)
        for row in self:
            writer.writerow(row)
        if filename:
            outfile.close()
            return CsvResultDescriptor(filename)
        else:
            return outfile.getvalue()
        
    
def interpret_rowcount(rowcount):
    if rowcount < 0:
        result = 'Done.'
    else:
        result = '%d rows affected.' % rowcount
    return result


def run(conn, sql, config, user_namespace):
    if sql.strip():
        for statement in sqlparse.split(sql):
            txt = sqlalchemy.sql.text(statement)
            result = conn.session.execute(txt, user_namespace)
            if result and config.feedback:
                print(interpret_rowcount(result.rowcount))
        resultset = ResultSet(result, statement, config)
        if config.autopandas:
            return resultset.DataFrame()
        else:
            return resultset
        #returning only last result, intentionally
    else:
        return 'Connected: %s' % conn.name
     
########NEW FILE########
__FILENAME__ = test_column_guesser
import re
import sys
from nose.tools import with_setup, raises
from sql.magic import SqlMagic

ip = get_ipython()

class SqlEnv(object):
    def __init__(self, connectstr):
        self.connectstr = connectstr
    def query(self, txt):
        return ip.run_line_magic('sql', "%s %s" % (self.connectstr, txt))

sql_env = SqlEnv('sqlite://')

def setup():
    sqlmagic = SqlMagic(shell=ip)
    ip.register_magics(sqlmagic)
    creator = """
        DROP TABLE IF EXISTS manycoltbl;
        CREATE TABLE manycoltbl 
                     (name TEXT, y1 REAL, y2 REAL, name2 TEXT, y3 INT);
        INSERT INTO manycoltbl VALUES 
                     ('r1-txt1', 1.01, 1.02, 'r1-txt2', 1.04);
        INSERT INTO manycoltbl VALUES 
                     ('r2-txt1', 2.01, 2.02, 'r2-txt2', 2.04);
        INSERT INTO manycoltbl VALUES ('r3-txt1', 3.01, 3.02, 'r3-txt2', 3.04);
        """
    for qry in creator.split(";"):
        sql_env.query(qry)

def teardown():
    sql_env.query("DROP TABLE manycoltbl")

class Harness(object):
    def run_query(self):
        return sql_env.query(self.query)

class TestOneNum(Harness):
    query = "SELECT y1 FROM manycoltbl"
    
    @with_setup(setup, teardown)
    def test_pie(self):
        results = self.run_query()
        results.guess_pie_columns(xlabel_sep="//")
        assert results.ys[0].is_quantity
        assert results.ys == [[1.01, 2.01, 3.01]]
        assert results.x == []
        assert results.xlabels == []
        assert results.xlabel == ''

    @with_setup(setup, teardown)
    def test_plot(self):
        results = self.run_query()
        results.guess_plot_columns()
        assert results.ys == [[1.01, 2.01, 3.01]]
        assert results.x == []
        assert results.x.name == ''

class TestOneStrOneNum(Harness):
    query = "SELECT name, y1 FROM manycoltbl"
    
    @with_setup(setup, teardown)
    def test_pie(self):
        results = self.run_query()
        results.guess_pie_columns(xlabel_sep="//")
        assert results.ys[0].is_quantity
        assert results.ys == [[1.01, 2.01, 3.01]]
        assert results.xlabels == ['r1-txt1', 'r2-txt1', 'r3-txt1']
        assert results.xlabel == 'name'

    @with_setup(setup, teardown)
    def test_plot(self):
        results = self.run_query()
        results.guess_plot_columns()
        assert results.ys == [[1.01, 2.01, 3.01]]
        assert results.x == []


class TestTwoStrTwoNum(Harness):
    query = "SELECT name2, y3, name, y1 FROM manycoltbl"
    
    @with_setup(setup, teardown)
    def test_pie(self):
        results = self.run_query()
        results.guess_pie_columns(xlabel_sep="//")
        assert results.ys[0].is_quantity
        assert results.ys == [[1.01, 2.01, 3.01]]
        assert results.xlabels == ['r1-txt2//1.04//r1-txt1',
                                  'r2-txt2//2.04//r2-txt1',
                                  'r3-txt2//3.04//r3-txt1']
        assert results.xlabel == 'name2, y3, name'

    @with_setup(setup, teardown)
    def test_plot(self):
        results = self.run_query()
        results.guess_plot_columns()
        assert results.ys == [[1.01, 2.01, 3.01]]
        assert results.x == [1.04, 2.04, 3.04]


class TestTwoStrThreeNum(Harness):
    query = "SELECT name, y1, name2, y2, y3 FROM manycoltbl"
    
    @with_setup(setup, teardown)
    def test_pie(self):
        results = self.run_query()
        results.guess_pie_columns(xlabel_sep="//")
        assert results.ys[0].is_quantity
        assert results.ys == [[1.04, 2.04, 3.04]]
        assert results.xlabels == ['r1-txt1//1.01//r1-txt2//1.02',
                                  'r2-txt1//2.01//r2-txt2//2.02',
                                  'r3-txt1//3.01//r3-txt2//3.02']

    @with_setup(setup, teardown)
    def test_plot(self):
        results = self.run_query()
        results.guess_plot_columns()
        assert results.ys == [[1.02, 2.02, 3.02], [1.04, 2.04, 3.04]]
        assert results.x == [1.01, 2.01, 3.01]
        

########NEW FILE########
__FILENAME__ = test_magic
from nose import with_setup
from sql.magic import SqlMagic
import re

ip = get_ipython()

def setup():
    sqlmagic = SqlMagic(shell=ip)
    ip.register_magics(sqlmagic)

def _setup():
    ip.run_line_magic('sql', 'sqlite:// CREATE TABLE test (n INT, name TEXT)')
    ip.run_line_magic('sql', "sqlite:// INSERT INTO test VALUES (1, 'foo');")
    ip.run_line_magic('sql', "sqlite:// INSERT INTO test VALUES (2, 'bar');")

def _teardown():
    ip.run_line_magic('sql', 'sqlite:// DROP TABLE test')
  
@with_setup(_setup, _teardown) 
def test_memory_db():
    assert ip.run_line_magic('sql', "sqlite:// SELECT * FROM test;")[0][0] == 1
    assert ip.run_line_magic('sql', "sqlite:// SELECT * FROM test;")[1]['name'] == 'bar'

@with_setup(_setup, _teardown) 
def test_html():
    result = ip.run_line_magic('sql',  "sqlite:// SELECT * FROM test;")
    assert '<td>foo</td>' in result._repr_html_().lower()

@with_setup(_setup, _teardown) 
def test_print():
    result = ip.run_line_magic('sql',  "sqlite:// SELECT * FROM test;")
    assert re.search(r'1\s+\|\s+foo', str(result))

@with_setup(_setup, _teardown) 
def test_plain_style():
    ip.run_line_magic('config',  "SqlMagic.style = 'PLAIN_COLUMNS'")
    result = ip.run_line_magic('sql',  "sqlite:// SELECT * FROM test;")
    assert re.search(r'1\s+foo', str(result))

   
def _setup_writer():
    ip.run_line_magic('sql', 'sqlite:// CREATE TABLE writer (first_name, last_name, year_of_death)')
    ip.run_line_magic('sql', "sqlite:// INSERT INTO writer VALUES ('William', 'Shakespeare', 1616)")
    ip.run_line_magic('sql', "sqlite:// INSERT INTO writer VALUES ('Bertold', 'Brecht', 1956)")
    
def _teardown_writer():
    ip.run_line_magic('sql', "sqlite:// DROP TABLE writer")
    
@with_setup(_setup_writer, _teardown_writer) 
def test_multi_sql():
    result = ip.run_cell_magic('sql', '', """
        sqlite://
        SELECT last_name FROM writer;
        """)
    assert 'Shakespeare' in str(result) and 'Brecht' in str(result)
   
    
@with_setup(_setup_writer, _teardown_writer) 
def test_access_results_by_keys():
    assert ip.run_line_magic('sql', "sqlite:// SELECT * FROM writer;")['William'] == (u'William', u'Shakespeare', 1616)
    
@with_setup(_setup_writer, _teardown_writer) 
def test_duplicate_column_names_accepted():
    result = ip.run_cell_magic('sql', '', """
        sqlite://
        SELECT last_name, last_name FROM writer;
        """)
    assert (u'Brecht', u'Brecht') in result

@with_setup(_setup, _teardown) 
def test_autolimit():
    ip.run_line_magic('config',  "SqlMagic.autolimit = 0")
    result = ip.run_line_magic('sql',  "sqlite:// SELECT * FROM test;")
    assert len(result) == 2
    ip.run_line_magic('config',  "SqlMagic.autolimit = 1")
    result = ip.run_line_magic('sql',  "sqlite:// SELECT * FROM test;")
    assert len(result) == 1


@with_setup(_setup_writer, _teardown_writer) 
def test_displaylimit():
    ip.run_line_magic('config',  "SqlMagic.autolimit = 0")
    ip.run_line_magic('config',  "SqlMagic.displaylimit = 0")
    result = ip.run_line_magic('sql',  "sqlite:// SELECT * FROM writer;")
    assert result._repr_html_().count("<tr>") == 3
    ip.run_line_magic('config',  "SqlMagic.displaylimit = 1")
    result = ip.run_line_magic('sql',  "sqlite:// SELECT * FROM writer;")
    assert result._repr_html_().count("<tr>") == 2

"""
def test_control_feedback():
    ip.run_line_magic('config',  "SqlMagic.feedback = False")

def test_local_over_global():
    ip.run_line_magic('', "x = 22")
    result = ip.run_line_magic('sql', "sqlite:// SELECT :x")
    assert result[0][0] == 22
"""
########NEW FILE########
__FILENAME__ = test_parse
from sql.parse import parse

def test_parse_no_sql():
    assert parse("will:longliveliz@localhost/shakes") == \
           {'connection': "will:longliveliz@localhost/shakes",
            'sql': ''}
    
def test_parse_with_sql():
    assert parse("postgresql://will:longliveliz@localhost/shakes SELECT * FROM work") == \
           {'connection': "postgresql://will:longliveliz@localhost/shakes",
            'sql': 'SELECT * FROM work'}    
    
def test_parse_sql_only():
    assert parse("SELECT * FROM work") == \
           {'connection': "",
            'sql': 'SELECT * FROM work'} 
    
def test_parse_postgresql_socket_connection():
    assert parse("postgresql:///shakes SELECT * FROM work") == \
           {'connection': "postgresql:///shakes",
            'sql': 'SELECT * FROM work'}            
########NEW FILE########
