__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import MySQLdb

from mosql.result import Model

# Enable the support of MySQL-specific SQL.
import mosql.mysql

# If SQLAlchemy is installed, use its connection pool.
try:
    import sqlalchemy.pool
    MySQLdb = sqlalchemy.pool.manage(MySQLdb, pool_size=5)
except ImportError:
    pass

# If you don't use utf-8 for connection, you need to use native escape function 
# for security:
#import mosql.MySQLdb_escape
#mosql.MySQLdb_escape.conn = MySQLdb.connect(user='root', db='mosky', charset='big5')

class MySQL(Model):

    @classmethod
    def getconn(cls):

        # The ``charset='utf8'`` is just to ensure we connect db with safe
        # encoding. If
        #     ``show variables where variable_name = 'character_set_connection';``
        # shows ``utf-8``, you can ignore that.

        # The ``use_unicode=False`` is just for the consistency with another example.

        return MySQLdb.connect(user='root', db='mosky', charset='utf8', use_unicode=False)

    @classmethod
    def putconn(cls, conn):
        conn.close()

########NEW FILE########
__FILENAME__ = detail
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base import MySQL

class Detail(MySQL):
    table      = 'detail'
    arrange_by = ('person_id', 'key')
    squashed   = set(arrange_by)
    ident_by   = ('detail_id', )
    clauses    = dict(order_by=arrange_by+ident_by)

if __name__ == '__main__':

    # If you want to see the SQLs it generates:
    #Detail.dump_sql = True

    print "# The Model of Mosky's Emails"
    print
    mosky_emails = Detail.where(person_id='mosky', key='email')
    print mosky_emails
    print

    print "# Show the Mosky's Emails"
    print
    print mosky_emails.val
    print

    print '# Show the Rows'
    print
    for row in mosky_emails.rows():
        print row
    print

    print '# Remove the First Email, and Show the Row Removed'
    print
    removal_email = mosky_emails.pop(0)
    mosky_emails.save()
    print removal_email
    print

    print "# Re-Select the Mosky's Emails"
    print
    print Detail.where(person_id='mosky', key='email')
    print

    print '# Add the Email Just Removed Back, and Re-Select'
    print
    mosky_emails.append(removal_email)
    mosky_emails.save()
    print Detail.where(person_id='mosky', key='email')
    print

    print '# Add a New Email for Andy, and Remove It'
    print
    andy_emails = Detail.where(person_id='andy', key='email')

    # The squashed columns are auto filled, and the other columns you ignored
    # are filled SQL's DEFAULT.
    andy_emails.append({'val': 'andy@hiscompany.com'})

    andy_emails.save()
    print andy_emails
    print

    # You can't remove it directly, because the `detail_id` in the row we just
    # appended is DEFAULT (unknown) now.
    #andy_emails.pop() # -> ValueError

    # You need to re-select to know the `detail_id`:
    andy_emails = Detail.where(person_id='andy', key='email')
    andy_emails.pop()
    andy_emails.save()
    print andy_emails
    print

    from person import Person

    d = {'person_id': 'tina', 'name': 'Tina Dico'}
    Person.insert(d, on_duplicate_key_update=d)

    print '# Create Emails for Tina'
    print

    tina_emails = Detail({'person_id': 'tina', 'key': 'email'})
    # or use ``Detail.new(person_id='tina', key='email')`` for short

    tina_emails.append({'val': 'tina@whatever.com'})
    tina_emails.append({'val': 'tina@whatever2.com'})
    tina_emails.save()
    print tina_emails
    print

    print '# Remove Tina'
    print
    tina_emails = Detail.where(person_id='tina', key='email')
    tina_emails.clear()
    tina_emails.save()
    print tina_emails
    print

    Person.delete(d)

########NEW FILE########
__FILENAME__ = join
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mosql import build

from detail import Detail

class PersonDetail(Detail):
    squashed   = Detail.squashed | set(['name'])
    clauses    = dict(
        order_by = Detail.arrange_by,
        joins    = build.join('person')
    )

if __name__ == '__main__':

    # If you want to see the SQLs it generates:
    #PersonDetail.dump_sql = True

    print "# Show the Mosky's Detail"
    print
    for pdetail in PersonDetail.find(person_id='mosky'):
        print pdetail
    print
    

########NEW FILE########
__FILENAME__ = person
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base import MySQL

class Person(MySQL):

    # the name of table
    table      = 'person'

    # The result set is converted to column-oriented model, so the columns are
    # lists. You can use this attribute to squash some of them into a single
    # value:
    #squashed = set(['person_id', 'name'])
    # set `squash_all` True to squash all of the columns
    squash_all = True

    # The class method, `arrange`, uses this attribute to arrange result set.
    arrange_by = ('person_id', )

    # It specifies the columns which will be use to prepare the conditions.
    ident_by   = arrange_by

    # the other clauses you want to put in the queries
    clauses    = dict(order_by=arrange_by)

if __name__ == '__main__':

    # If you want to see the SQLs it generates:
    #Person.dump_sql = True

    print '# The Model of Mosky'
    print
    mosky = Person.select({'person_id': 'mosky'})
    print mosky
    print

    print '# Access the Model, and Re-Select'
    print
    print mosky.person_id
    print mosky['name']
    print

    print '# Rename Mosky, and Re-Select'
    print

    mosky.name = 'Yiyu Lui'

    # The previous one has some typo.
    mosky.name = 'Yiyu Liu'

    # The two changes will be merged into only an update.
    mosky.save()

    # Re-selecting is not necessary. I just wanna show you the db is really
    # changed. Here I use where for short.
    print Person.where(person_id='mosky')
    print

    print '# Rename Her Back'
    print
    mosky['name'] = 'Mosky Liu'
    mosky.save()
    print Person.where(person_id='mosky')
    print

    print '# Arrange Rows into Models'
    print
    for person in Person.arrange({'person_id': ('mosky', 'andy')}):
        print person
    # or use ``Person.find(person_id=('mosky', 'andy'))`` in for-loop
    print

    print '# Insert a New Person'
    print
    d = {'person_id': 'new'}
    Person.insert(d, on_duplicate_key_update=d)
    new_person = Person.where(person_id='new')
    print new_person
    print

    print '# Delete the New Person'
    print
    new_person = Person.delete({'person_id': 'new'})
    print new_person
    print

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2.pool
from mosql.result import Model

# If you don't use utf-8 for connection, you need to use native escape function 
# for security:
#import mosql.psycopg2_escape
#mosql.psycopg2_escape.conn = psycopg2.connect(database='mosky', client_encoding='big5')

# The `client_encoding`='utf-8'`` is just to ensure we connect db with safe
# encoding. If ``show client_encoding;` shows ``utf-8``, you can ignore that.
pool = psycopg2.pool.SimpleConnectionPool(1, 5, database='mosky', client_encoding='utf-8')

class PostgreSQL(Model):

    getconn = pool.getconn
    putconn = pool.putconn


########NEW FILE########
__FILENAME__ = detail
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base import PostgreSQL

class Detail(PostgreSQL):
    table      = 'detail'
    arrange_by = ('person_id', 'key')
    squashed   = set(arrange_by)
    ident_by   = ('detail_id', )
    clauses    = dict(order_by=arrange_by+ident_by)

if __name__ == '__main__':

    # If you want to see the SQLs it generates:
    #Detail.dump_sql = True

    print "# The Model of Mosky's Emails"
    print
    mosky_emails = Detail.where(person_id='mosky', key='email')
    print mosky_emails
    print

    print "# Show the Mosky's Emails"
    print
    print mosky_emails.val
    print

    print '# Show the Rows'
    print
    for row in mosky_emails.rows():
        print row
    print

    print '# Remove the First Email, and Show the Row Removed'
    print
    removal_email = mosky_emails.pop(0)
    mosky_emails.save()
    print removal_email
    print

    print "# Re-Select the Mosky's Emails"
    print
    print Detail.where(person_id='mosky', key='email')
    print

    print '# Add the Email Just Removed Back, and Re-Select'
    print
    mosky_emails.append(removal_email)
    mosky_emails.save()
    print Detail.where(person_id='mosky', key='email')
    print

    print '# Add a New Email for Andy, and Remove It'
    print
    andy_emails = Detail.where(person_id='andy', key='email')

    # The squashed columns are auto filled, and the other columns you ignored
    # are filled SQL's DEFAULT.
    andy_emails.append({'val': 'andy@hiscompany.com'})

    andy_emails.save()
    print andy_emails
    print

    # You can't remove it directly, because the `detail_id` in the row we just
    # appended is DEFAULT (unknown) now.
    #andy_emails.pop() # -> ValueError

    # You need to re-select to know the `detail_id`:
    andy_emails = Detail.where(person_id='andy', key='email')
    andy_emails.pop()
    andy_emails.save()
    print andy_emails
    print

    from psycopg2 import IntegrityError
    from person import Person

    try:
        Person.insert({'person_id': 'tina', 'name': 'Tina Dico'})
    except IntegrityError:
        pass

    print '# Create Emails for Tina'
    print

    tina_emails = Detail({'person_id': 'tina', 'key': 'email'})
    # or use ``Detail.new(person_id='tina', key='email')`` for short

    tina_emails.append({'val': 'tina@whatever.com'})
    tina_emails.append({'val': 'tina@whatever2.com'})
    tina_emails.save()
    print tina_emails
    print

    print '# Remove Tina'
    print
    tina_emails = Detail.where(person_id='tina', key='email')
    tina_emails.clear()
    tina_emails.save()
    print tina_emails
    print

    Person.delete({'person_id': 'tina'})

########NEW FILE########
__FILENAME__ = join
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mosql import build

from detail import Detail

class PersonDetail(Detail):
    squashed   = Detail.squashed | set(['name'])
    clauses    = dict(
        order_by = Detail.arrange_by,
        joins    = build.join('person')
    )

if __name__ == '__main__':

    # If you want to see the SQLs it generates:
    #PersonDetail.dump_sql = True

    print "# Show the Mosky's Detail"
    print
    for pdetail in PersonDetail.find(person_id='mosky'):
        print pdetail
    print
    

########NEW FILE########
__FILENAME__ = perform
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base import PostgreSQL

PostgreSQL.dump_sql = True

PostgreSQL.perform(
    'INSERT INTO person VALUES (%s, %s)',
    params = [
        ('dara', 'Dara Torres'),
        ('eden', 'Eden Tseng'),
    ]
)

PostgreSQL.perform("DELETE FROM person WHERE person_id = 'dara'")
PostgreSQL.perform("DELETE FROM person WHERE person_id = %s", ('eden', ))

#print PostgreSQL.perform(proc='add', param=(1, 2)).fetchall()

########NEW FILE########
__FILENAME__ = person
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base import PostgreSQL

class Person(PostgreSQL):

    # the name of table
    table      = 'person'

    # The result set is converted to column-oriented model, so the columns are
    # lists. You can use this attribute to squash some of them into a single
    # value:
    #squashed = set(['person_id', 'name'])
    # set `squash_all` True to squash all of the columns
    squash_all = True

    # The class method, `arrange`, uses this attribute to arrange result set.
    arrange_by = ('person_id', )

    # It specifies the columns which will be use to prepare the conditions.
    ident_by   = arrange_by

    # the other clauses you want to put in the queries
    clauses    = dict(order_by=arrange_by)

if __name__ == '__main__':

    # If you want to see the SQLs it generates:
    #Person.dump_sql = True

    print '# The Model of Mosky'
    print
    mosky = Person.select({'person_id': 'mosky'})
    print mosky
    print

    print '# Access the Model, and Re-Select'
    print
    print mosky.person_id
    print mosky['name']
    print

    print '# Rename Mosky, and Re-Select'
    print

    mosky.name = 'Yiyu Lui'

    # The previous one has some typo.
    mosky.name = 'Yiyu Liu'

    # The two changes will be merged into only an update.
    mosky.save()

    # Re-selecting is not necessary. I just wanna show you the db is really
    # changed. Here I use where for short.
    print Person.where(person_id='mosky')
    print

    print '# Rename Her Back'
    print
    mosky['name'] = 'Mosky Liu'
    mosky.save()
    print Person.where(person_id='mosky')
    print

    print '# Arrange Rows into Models'
    print
    for person in Person.arrange({'person_id': ('mosky', 'andy')}):
        print person
    # or use ``Person.find(person_id=('mosky', 'andy'))`` in for-loop
    print

    print '# Insert a New Person'
    print
    from psycopg2 import IntegrityError
    from mosql.util import star
    try:
        new_person = Person.insert({'person_id': 'new'}, returning=star)
    except IntegrityError:
        print '(skip it, because this person is existent.)'
    else:
        print new_person
    print

    print '# Delete the New Person'
    print
    new_person = Person.delete({'person_id': 'new'}, returning=star)
    print new_person
    print

########NEW FILE########
__FILENAME__ = benchmark
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2.pool
from mosql.result import Model

pool = psycopg2.pool.SimpleConnectionPool(1, 100, database='mosky')

class PostgreSQL(Model):
    getconn = pool.getconn
    putconn = pool.putconn

class Person(PostgreSQL):
    table = 'person'

def use_pure_sql():
    conn = pool.getconn()
    cur = conn.cursor()

    cur.execute("select * from person where person_id in ('mosky', 'andy') order by person_id")
    result = cur.fetchall()

    cur.close()
    pool.putconn(conn)

    return result

def use_mosql():
    return Person.select(
        where    = {'person_id': ('mosky', 'andy')},
        order_by = ('person_id',)
    )

if __name__ == '__main__':

    from timeit import timeit

    #print use_pure_sql()
    #print use_mosql()
    #print use_mosql()
    print timeit(use_pure_sql, number=100000)
    # -> 35.7427990437
    print timeit(use_mosql, number=100000)
    # -> 46.7011768818

########NEW FILE########
__FILENAME__ = mock
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mosql.result import Model

class Order(Model):
    arrange_by = ('order_id', )
    squashed = set(arrange_by)

col_names = ['order_id', 'product_id', 'price']

rows = [
    ('A001', 'A', 100, ),
    ('A001', 'B', 120, ),
    ('A001', 'C',  10, ),
    ('A002', 'D', 100, ),
    ('A002', 'E',  50, ),
]

########NEW FILE########
__FILENAME__ = test_escape
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# test PostgreSQL
import psycopg2 as db
from mosql.util import escape
conn = db.connect(database='mosky')

# or MySQL
#import MySQLdb as db
#from mosql.mysql import escape
#from mosql.mysql import fast_escape as escape
#conn = db.connect(user='root', db='mosky')

# or SQLite
#import sqlite3 as db
#from mosql.util import escape
#conn = db.connect('sqlite.db')
#
#cur = conn.cursor()
#cur.execute('''
#    CREATE TABLE IF NOT EXISTS person (
#        person_id TEXT PRIMARY KEY,
#        name      TEXT
#    );
#''')

# -- preparation --

cur = conn.cursor()

cur.execute("select * from person where person_id='dara'")
if cur.rowcount == 0:
    cur.execute("insert into person values ('dara', 'Dara Scully')")
    conn.commit()

cur.close()

# --- end of preparation ---

# --- main ---

cur = conn.cursor()

bytes = ''.join(unichr(i) for i in range(1, 128)).encode('utf-8')
bytes += ''.join(unichr(i) for i in range(28204, 28224)).encode('utf-8')

cur.execute("update person set name='%s' where person_id='dara'" % escape(bytes))
conn.commit()

cur.execute("select name from person where person_id='dara'")

for row in cur:
    name = row[0].decode('utf-8')

    print 'Check the Incontinuity:'
    count = 0
    for i in range(1, len(name)):
        diff = ord(name[i]) - ord(name[i-1])
        if 1 < diff < 20000:
            print '%s (%s) - %s (%s)' % (name[i], ord(name[i]), name[i-1], ord(name[i-1]))
            count += 1
    print 'count:', count,

    if not count:
        print 'passed!'
    else:
        print

cur.close()

# --- end of main ---

conn.close()

########NEW FILE########
__FILENAME__ = test_native_escape
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mosql.psycopg2_escape
from mosql.util import escape
s = "Hello, 'World'! and slash \me"

print escape(s)

import psycopg2
mosql.psycopg2_escape.conn = psycopg2.connect(dbname='mosky')

print escape(s)


import mosql.MySQLdb_escape
from mosql.util import escape
s = "Hello, 'World\xcc'! and slash \me"

print escape(s)

import MySQLdb
mosql.MySQLdb_escape.conn = MySQLdb.connect(user='root', db='mosky', charset='big5')

print escape(s)

########NEW FILE########
__FILENAME__ = test_rowproxy
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mock import Order, col_names, rows

print '# Order'
for order in Order.arrange_rows(col_names, rows):
    print order
print

print '# Rows in Order'
for row in order.rows():
    print row
print

print '# Modification'
row.price = 99
print 'This row  :', row
print 'This order:', order

########NEW FILE########
__FILENAME__ = unittest_all
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

def load_tests(loader, tests, ignore):

    from os.path import dirname, join, abspath
    itsdir = dirname(__file__)

    import sys
    sys.path.insert(0, abspath(join(itsdir, '..')))
    sys.path.insert(0, abspath(itsdir))

    import doctest

    # ValueError: (<module 'mosql.defi' from '/home/mosky/sql-helper/mosql/defi.pyc'>, 'has no tests')
    #import mosql.defi
    #tests.addTests(doctest.DocTestSuite(mosql.defi))

    import mosql.util
    tests.addTests(doctest.DocTestSuite(mosql.util))

    import mosql.build
    tests.addTests(doctest.DocTestSuite(mosql.build))

    #import mosql.ext
    #tests.addTests(doctest.DocTestSuite(mosql.ext))

    import mosql.result
    tests.addTests(doctest.DocTestSuite(mosql.result))

    import unittest_model
    tests.addTest(loader.loadTestsFromModule(unittest_model))

    return tests

if __name__ == '__main__':
    unittest.main(verbosity=2)

########NEW FILE########
__FILENAME__ = unittest_model
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

class TestModel(unittest.TestCase):

    def test_dummy(self):
        self.assertEqual(1, 1)

    def test_dummy2(self):
        self.assertEqual(1, 1)

    def test_dummy3(self):
        self.assertEqual(1, 1)

if __name__ == '__main__':
    unittest.main()



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# MoSQL documentation build configuration file, created by
# sphinx-quickstart on Thu Feb 14 22:47:45 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.popen('git rev-parse --show-toplevel 2> /dev/null').read().strip())

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.viewcode', 'sphinx.ext.autosummary', 'sphinx.ext.doctest']
doctest_global_setup = '''
import mosql.util
mosql.util.escape             = mosql.util.std_escape
mosql.util.format_param       = mosql.util.std_format_param
mosql.util.stringify_bool     = mosql.util.std_stringify_bool
mosql.util.delimit_identifier = mosql.util.std_delimit_identifier
mosql.util.escape_identifier  = mosql.util.std_escape_identifier
'''

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'MoSQL'
copyright = u'2013, Mosky Liu'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
from mosql import __version__

# The short X.Y version.
version = 'v' + '.'.join(__version__.split('.')[:2])
# The full version, including alpha/beta/rc tags.
release = 'v' + __version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'MoSQLdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'MoSQL.tex', u'MoSQL Documentation',
   u'Mosky Liu', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'MoSQL', u'MoSQL Documentation',
     [u'Mosky Liu'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'MoSQL', u'MoSQL Documentation',
   u'Mosky Liu', 'MoSQL', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = 10_simplest
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
from mosql.util import star
from mosql.query import insert

conn = psycopg2.connect(host='127.0.0.1')
cur = conn.cursor()

dave = {
    'person_id': 'dave',
    'name'     : 'Dave',
}

# MoSQL is here! :)
cur.execute(insert('person', dave, returning=star))

person_id, name = cur.fetchone()
print person_id
print name

cur.close()
#conn.commit() # Actually we don't want to commit here.
conn.close()

########NEW FILE########
__FILENAME__ = 20_db_mod
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
from mosql.util import star
from mosql.query import insert
from mosql.db import Database, one_to_dict

dave = {
    'person_id': 'dave',
    'name'     : 'Dave',
}

db = Database(psycopg2, host='127.0.0.1')

with db as cur:

    cur.execute(insert('person', dave, returning=star))
    print one_to_dict(cur)
    print

    assert 0, 'Rollback!'

########NEW FILE########
__FILENAME__ = 30_breed
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
from mosql.util import star
from mosql.query import insert
from mosql.db import Database, one_to_dict

# We breed another insert with parital arguments.
person_insert = insert.breed({'table': 'person'})

dave = {
    'person_id': 'dave',
    'name'     : 'Dave',
}

db = Database(psycopg2, host='127.0.0.1')

with db as cur:

    cur.execute(person_insert(set=dave, returning=star))
    print one_to_dict(cur)
    print

    assert 0, 'Rollback!'

########NEW FILE########
__FILENAME__ = 40_join
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
from pprint import pprint
from mosql.query import select, left_join
from mosql.db import Database, all_to_dicts

db = Database(psycopg2, host='127.0.0.1')

with db as cur:

    cur.execute(select(
        'person',

        {'person_id': 'mosky'},
        # It is same as using keyword argument:
        #where = {'person_id': 'mosky'},

        joins = left_join('detail', using='person_id'),
        # You can also use tuple to add multiple join statements:
        #joins = (left_join('detail', using='person_id'), )
    ))

    pprint(all_to_dicts(cur))

########NEW FILE########
__FILENAME__ = 50_group_by
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
from mosql.util import raw
from mosql.query import select, left_join
from mosql.db import Database, group

db = Database(psycopg2, host='127.0.0.1')

with db as cur:

    ## Use PostgreSQL to group:

    cur.execute(select(
        'person',
        joins = left_join('detail', using='person_id'),
        where = {'key': 'email'},
        group_by = 'person_id',
        select = ('person_id', raw('array_agg(val)')),
        # It is optional here.
        order_by = 'person_id',
    ))

    print 'Group the rows in PostgreSQL:'
    for row in cur:
        print row
    print

    ## Use MoSQL (app-level) to group:

    cur.execute(select(
        'person',
        joins = left_join('detail', using='person_id'),
        where = {'key': 'email'},
        select = ('person_id', 'val'),
        # You have to order the rows!
        order_by = 'person_id',
    ))

    print 'Group the rows by MoSQL:'
    for row in group(['person_id'], cur):
        print row

########NEW FILE########
__FILENAME__ = 60_class
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
from mosql.query import insert, select, update, delete
from mosql.db import Database, one_to_dict

class Person(dict):

    db = Database(psycopg2, host='127.0.0.1')
    table_info = {'table': 'person'}
    select = select.breed(table_info)
    insert = insert.breed(table_info)

    def __init__(self, *args, **kargs):
        dict.__init__(self, *args, **kargs)
        row_info = self.table_info.copy()
        row_info['where'] = {'person_id': self['person_id']}
        self.update = update.breed(row_info)
        self.delete = delete.breed(row_info)

    @classmethod
    def create(cls, *args, **kargs):
        person = cls(*args, **kargs)
        with cls.db as cur:
            cur.execute(cls.insert(set=person))
        return person

    @classmethod
    def fetch(cls, person_id):
        with cls.db as cur:
            cur.execute(cls.select(where={'person_id': person_id}))
            if cur.rowcount:
                person = cls(one_to_dict(cur))
            else:
                person = None
        return person

    def save(self):
        with self.db as cur:
            cur.execute(self.update(set=self))

    def remove(self):
        with self.db as cur:
            cur.execute(self.delete())

if __name__ == '__main__':

    dave = {
        'person_id': 'dave',
        'name'     : 'Dave',
    }

    # insert
    p = Person.create(dave)
    print p

    # select
    p = Person.fetch('dave')
    print p

    # update
    p['name'] = 'dave'
    p.save()
    #p = Person.fetch('dave') # if you insist
    print p

    # delete
    p.remove()
    p = Person.fetch('dave')
    print p


########NEW FILE########
__FILENAME__ = 70_web
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Run this script, then try the following urls:
#
# 1. http://127.0.0.1:5000/?person_id=mosky
# 2. http://127.0.0.1:5000/?name=Mosky Liu
# 3. http://127.0.0.1:5000/?name like=%Mosky%
#

import psycopg2
from flask import Flask, request, jsonify
from mosql.query import select, left_join
from mosql.db import Database

db = Database(psycopg2, host='127.0.0.1')

app = Flask(__name__)

@app.route('/')
def index():
    with db as cur:
        cur.execute(select(
            'person',
            request.args or None,
            joins = left_join('detail', using=('person_id', )),
        ))
        return jsonify(data=list(cur))

if __name__ == '__main__':
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
.. deprecated:: 0.6
    Use :mod:`mosql.query` instead.

It contains the common SQL builders.

.. versionchanged:: 0.2
    It is renamed from ``common``.

.. versionchanged:: 0.1.6
    It is rewritten for using new :mod:`mosql.util`, but it is compatible with
    old version.

.. autosummary ::
    select
    insert
    update
    delete
    join
    or_

It is designed for building the standard SQL statement and tested in PostgreSQL.

.. note::
    If you use MySQL, here is a patch for MySQL --- :mod:`mosql.mysql`.
'''

__all__ = ['select', 'insert', 'delete', 'update', 'join', 'or_']

from .util import *

# defines formatting chains
single_value      = (value, )
single_identifier = (identifier, )
identifier_list   = (identifier, concat_by_comma)
column_list       = (identifier, concat_by_comma, paren)
value_list        = (value, concat_by_comma, paren)
where_list        = (build_where, )
set_list          = (build_set, )
statement_list    = (concat_by_space, )

# insert

insert    = Clause('insert into', single_identifier)
columns   = Clause('columns'    , column_list, hidden=True)
values    = Clause('values'     , value_list)
returning = Clause('returning'  , identifier_list)
on_duplicate_key_update = Clause('on duplicate key update', set_list)

insert_into_stat = Statement([insert, columns, values, returning, on_duplicate_key_update])

def insert(table, set=None, values=None, **clauses_args):
    '''It generates the SQL statement, ``insert into ...``.

    The following usages generate the same SQL statement:

    >>> print insert('person', {'person_id': 'mosky', 'name': 'Mosky Liu'})
    INSERT INTO "person" ("person_id", "name") VALUES ('mosky', 'Mosky Liu')

    >>> print insert('person', (('person_id', 'mosky'), ('name', 'Mosky Liu')))
    INSERT INTO "person" ("person_id", "name") VALUES ('mosky', 'Mosky Liu')

    >>> print insert('person', ('person_id', 'name'), ('mosky', 'Mosky Liu'))
    INSERT INTO "person" ("person_id", "name") VALUES ('mosky', 'Mosky Liu')

    The columns is ignorable:

    >>> print insert('person', values=('mosky', 'Mosky Liu'))
    INSERT INTO "person" VALUES ('mosky', 'Mosky Liu')

    The :func:`insert`, :func:`update` and :func:`delete` support ``returning``.

    >>> print insert('person', {'person_id': 'mosky', 'name': 'Mosky Liu'}, returning=raw('*'))
    INSERT INTO "person" ("person_id", "name") VALUES ('mosky', 'Mosky Liu') RETURNING *

    The MySQL-specific "on duplicate key update" is also supported:

    >>> print insert('person', values=('mosky', 'Mosky Liu'), on_duplicate_key_update={'name': 'Mosky Liu'})
    INSERT INTO "person" VALUES ('mosky', 'Mosky Liu') ON DUPLICATE KEY UPDATE "name"='Mosky Liu'
    '''

    clauses_args['insert into'] = table

    if values is None:
        if hasattr(set, 'items'):
            pairs = set.items()
        else:
            pairs = set
        clauses_args['columns'], clauses_args['values'] = zip(*pairs)
    else:
        clauses_args['columns'] = set
        clauses_args['values']  = values

    if 'on_duplicate_key_update' in clauses_args:
        clauses_args['on duplicate key update'] = clauses_args['on_duplicate_key_update']
        del clauses_args['on_duplicate_key_update']

    return insert_into_stat.format(clauses_args)

# select

select   = Clause('select'  , identifier_list)
from_    = Clause('from'    , identifier_list)
joins    = Clause('joins'   , statement_list, hidden=True)
where    = Clause('where'   , where_list)
group_by = Clause('group by', identifier_list)
having   = Clause('having'  , where_list)
order_by = Clause('order by', identifier_list)
limit    = Clause('limit'   , single_value)
offset   = Clause('offset'  , single_value)

select_stat = Statement([select, from_, joins, where, group_by, having, order_by, limit, offset])

def select(table, where=None, select=None, **clauses_args):
    '''It generates the SQL statement, ``select ...`` .

    .. versionchanged:: 0.1.6
        The clause argument, ``join``, is renamed to ``joins``.

    The following usages generate the same SQL statement.

    >>> print select('person', {'person_id': 'mosky'})
    SELECT * FROM "person" WHERE "person_id" = 'mosky'

    >>> print select('person', (('person_id', 'mosky'), ))
    SELECT * FROM "person" WHERE "person_id" = 'mosky'

    It detects the dot in an identifier:

    >>> print select('person', select=('person.person_id', 'person.name'))
    SELECT "person"."person_id", "person"."name" FROM "person"

    Building prepare statement with :class:`mosql.util.param`:

    >>> print select('table', {'custom_param': param('my_param'), 'auto_param': param, 'using_alias': ___})
    SELECT * FROM "table" WHERE "auto_param" = %(auto_param)s AND "using_alias" = %(using_alias)s AND "custom_param" = %(my_param)s

    You can also specify the ``group_by``, ``having``, ``order_by``, ``limit``
    and ``offset`` in the keyword arguments. Here are some examples:

    >>> print select('person', {'name like': 'Mosky%'}, group_by=('age', ))
    SELECT * FROM "person" WHERE "name" LIKE 'Mosky%' GROUP BY "age"

    >>> print select('person', {'name like': 'Mosky%'}, order_by=('age', ))
    SELECT * FROM "person" WHERE "name" LIKE 'Mosky%' ORDER BY "age"

    >>> print select('person', {'name like': 'Mosky%'}, order_by=('age desc', ))
    SELECT * FROM "person" WHERE "name" LIKE 'Mosky%' ORDER BY "age" DESC

    >>> print select('person', {'name like': 'Mosky%'}, order_by=('age ; DROP person; --', ))
    Traceback (most recent call last):
        ...
    OptionError: this option is not allowed: '; DROP PERSON; --'

    .. seealso ::
        The options allowed --- :attr:`mosql.util.allowed_options`.

    >>> print select('person', {'name like': 'Mosky%'}, limit=3, offset=1)
    SELECT * FROM "person" WHERE "name" LIKE 'Mosky%' LIMIT 3 OFFSET 1

    The operators are also supported:

    >>> print select('person', {'person_id': ('andy', 'bob')})
    SELECT * FROM "person" WHERE "person_id" IN ('andy', 'bob')

    >>> print select('person', {'name': None})
    SELECT * FROM "person" WHERE "name" IS NULL

    >>> print select('person', {'name like': 'Mosky%', 'age >': 20})
    SELECT * FROM "person" WHERE "age" > 20 AND "name" LIKE 'Mosky%'

    >>> print select('person', {"person_id = '' OR true; --": 'mosky'})
    Traceback (most recent call last):
        ...
    OperatorError: this operator is not allowed: "= '' OR TRUE; --"

    .. seealso ::
        The operators allowed --- :attr:`mosql.util.allowed_operators`.

    If you want to use functions, wrap it with :class:`mosql.util.raw`:

    >>> print select('person', select=raw('count(*)'), group_by=('age', ))
    SELECT count(*) FROM "person" GROUP BY "age"

    .. warning ::
        You have responsibility to ensure the security if you use :class:`mosql.util.raw`.

    .. seealso ::
        How it builds the where clause --- :func:`mosql.util.build_where`
    '''

    clauses_args['from']   = table
    clauses_args['where']  = where
    clauses_args['select'] = star if select is None else select

    if 'order_by' in clauses_args:
        clauses_args['order by'] = clauses_args['order_by']
        del clauses_args['order_by']

    if 'group_by' in clauses_args:
        clauses_args['group by'] = clauses_args['group_by']
        del clauses_args['group_by']

    return select_stat.format(clauses_args)

# update

update = Clause('update', single_identifier)
set    = Clause('set'   , set_list)

update_stat = Statement([update, set, where, returning])

def update(table, where=None, set=None, **clauses_args):
    '''It generates the SQL statement, ``update ...`` .

    The following usages generate the same SQL statement.

    >>> print update('person', {'person_id': 'mosky'}, {'name': 'Mosky Liu'})
    UPDATE "person" SET "name"='Mosky Liu' WHERE "person_id" = 'mosky'

    >>> print update('person', (('person_id', 'mosky'), ), (('name', 'Mosky Liu'),) )
    UPDATE "person" SET "name"='Mosky Liu' WHERE "person_id" = 'mosky'

    .. seealso ::
        How it builds the where clause --- :func:`mosql.util.build_set`
    '''

    clauses_args['update'] = table
    clauses_args['where']  = where
    clauses_args['set']    = set

    return update_stat.format(clauses_args)

# delete from

delete = Clause('delete from', single_identifier)

delete_stat = Statement([delete, where, returning])

def delete(table, where=None, **clauses_args):
    '''It generates the SQL statement, ``delete from ...`` .

    The following usages generate the same SQL statement.

    >>> print delete('person', {'person_id': 'mosky'})
    DELETE FROM "person" WHERE "person_id" = 'mosky'

    >>> print delete('person', (('person_id', 'mosky'), ))
    DELETE FROM "person" WHERE "person_id" = 'mosky'
    '''

    clauses_args['delete from'] = table
    clauses_args['where'] = where

    return delete_stat.format(clauses_args)

# join

join  = Clause('join' , single_identifier)
type  = Clause('type' , tuple(), hidden=True)
on    = Clause('on'   , (build_on, ))
using = Clause('using', column_list)

join_stat = Statement([type, join, on, using])

def join(table, using=None, on=None, type=None, **clauses_args):
    '''It generates the SQL statement, ``... join ...`` .

    .. versionadded :: 0.1.6

    >>> print select('person', joins=join('detail'))
    SELECT * FROM "person" NATURAL JOIN "detail"

    >>> print select('person', joins=join('detail', using=('person_id', )))
    SELECT * FROM "person" INNER JOIN "detail" USING ("person_id")

    >>> print select('person', joins=join('detail', on={'person.person_id': 'detail.person_id'}))
    SELECT * FROM "person" INNER JOIN "detail" ON "person"."person_id" = "detail"."person_id"

    >>> print select('person', joins=join('detail', type='cross'))
    SELECT * FROM "person" CROSS JOIN "detail"

    .. seealso ::
        How it builds the where clause --- :func:`mosql.util.build_on`
    '''

    clauses_args['join'] = table
    clauses_args['using'] = using
    clauses_args['on'] = on

    if not type:
        if using or on:
            clauses_args['type'] = 'INNER'
        else:
            clauses_args['type'] = 'NATURAL'
    else:
        clauses_args['type'] = type.upper()

    return join_stat.format(clauses_args)

# or

def or_(*conditions):
    '''It concats the conditions by ``OR``.

    .. versionadded :: 0.1.6

    >>> print or_({'person_id': 'andy'}, {'person_id': 'bob'})
    "person_id" = 'andy' OR "person_id" = 'bob'
    '''

    return concat_by_or(build_where(c) for c in conditions)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

    # benchmark

    #from timeit import timeit
    #from functools import partial
    #timeit = partial(timeit, number=100000)

    #import mosql.util

    #print timeit(lambda: select('person', {'name': 'Mosky Liu'}, ('person_id', 'name'), limit=10, order_by='person_id'))
    ## -> 4.97957897186

    #print timeit(lambda: select('person', {'name': 'Mosky Liu'}, ('person.person_id', 'person.name'), limit=10, order_by='person_id'))
    ## -> 5.33279800415

    #mosql.util.delimit_identifier = None
    #print timeit(lambda: select('person', {'name': 'Mosky Liu'}, ('person_id', 'name'), limit=10, order_by='person_id'))
    ## -> 3.94950485229

    ##from mosql.common import select as old_select

    ##print timeit(lambda: old_select('person', {'name': 'Mosky Liu'}, ('person_id', 'name'), limit=10, order_by='person_id'))
    ### -> 6.79131507874

########NEW FILE########
__FILENAME__ = chain
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It provides common formatting chain.'''

from .util import value, identifier, paren
from .util import concat_by_comma, concat_by_space, build_where, build_set, build_on

single_value      = (value, )
single_identifier = (identifier, )
identifier_list   = (identifier, concat_by_comma)
column_list       = (identifier, concat_by_comma, paren)
value_list        = (value, concat_by_comma, paren)
where_list        = (build_where, )
set_list          = (build_set, )
on_list           = (build_on, )
statement_list    = (concat_by_space, )


########NEW FILE########
__FILENAME__ = clause
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It provides common clauses.'''

from .util import star, Clause
from .chain import identifier_list, where_list
from .chain import single_identifier, column_list, value_list, set_list
from .chain import statement_list, single_value
from .chain import on_list

# common clauses
returning = Clause('returning' , identifier_list)
where     = Clause('where'     , where_list)

# for insert statement
insert    = Clause('insert into', single_identifier, alias='table')
columns   = Clause('columns'    , column_list, hidden=True)
values    = Clause('values'     , value_list)
on_duplicate_key_update = Clause('on duplicate key update', set_list)

# for select statement
select   = Clause('select'  , identifier_list, default=star, alias='columns')
from_    = Clause('from'    , identifier_list, alias='table')
joins    = Clause('joins'   , statement_list, hidden=True)
group_by = Clause('group by', identifier_list)
having   = Clause('having'  , where_list)
order_by = Clause('order by', identifier_list)
limit    = Clause('limit'   , single_value)
offset   = Clause('offset'  , single_value)

# for PostgreSQL-specific select
for_   = Clause('for')
of     = Clause('of'    , identifier_list)
nowait = Clause('nowait', no_argument=True)

# for MySQL-specific select
for_update = Clause('for update', no_argument=True)
lock_in_share_mode = Clause('lock in share mode', no_argument=True)

# for update statement
update = Clause('update', single_identifier, alias='table')
set_   = Clause('set'   , set_list)

# for delete statement
delete = Clause('delete from', single_identifier, alias='table')

# for join statement
join  = Clause('join' , single_identifier, alias='table')
type_ = Clause('type' , hidden=True)
on    = Clause('on'   , on_list)
using = Clause('using', column_list)

# for replace statement
replace = Clause('replace into', single_identifier, alias='table')

########NEW FILE########
__FILENAME__ = db
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It makes it easier to use the module which conforms Python DB API 2.0.

The context manager for both connection and cursor:

.. autosummary ::
    Database

The functions designed for cursor:

.. autosummary ::
    extact_col_names
    one_to_dict
    all_to_dicts
    group

'''

from itertools import groupby, izip
from collections import deque

class Database(object):
    '''It is a context manager which manages the creation and destruction of a
    connection and its cursors.

    :param module: a module which conforms Python DB API 2.0

    Initialize a :class:`Database` instance:

    ::

        import psycopg2
        db = Database(psycopg2, host='127.0.0.1')

    Note it just tells :class:`Database` how to connect to your database. No
    connection or cursor is created here.

    Then get a cursor to communicate with database:

    ::

        with db as cur:
            cur.execute('select 1')

    The connection and cursor are created when you enter the with-block, and
    they will be closed when you leave. Also, the changes will be committed when
    you leave, or be rollbacked if there is any exception.

    If you need multiple cursors, just say:

    ::

        with db as cur1, db as cur2:
            cur1.execute('select 1')
            cur2.execute('select 2')

    Each :class:`Database` instance at most has one connection. The cursors
    share a same connection no matter how many cursors you asked.

    It is possible to customize the creating of connection or cursor. If you
    want to customize, override the attributes you need:

    ::

        db = Database()
        db.getconn = lambda: pool.getconn()
        db.putconn = lambda conn: pool.putconn(conn)
        db.getcur  = lambda conn: conn.cursor('named-cusor')
        db.putcur  = lambda cur : cur.close()
    '''

    def __init__(self, module=None, *conn_args, **conn_kargs):

        if module is not None:
            self.getconn = lambda: module.connect(*conn_args, **conn_kargs)
        else:
            self.getconn = None

        self.putconn = lambda conn: conn.close()
        self.getcur  = lambda conn: conn.cursor()
        self.putcur  = lambda cur : cur.close()

        self._conn = None
        self._cur_stack = deque()

    def __enter__(self):

        # check if we need to create connection
        if not self._cur_stack:
            assert callable(self.getconn), "You must set getconn if you don't \
                specify a module."
            self._conn = self.getconn()

        # get the cursor
        cur = self.getcur(self._conn)

        # push it into stack
        self._cur_stack.append(cur)

        return cur

    def __exit__(self, exc_type, exc_val, exc_tb):

        # close the cursor
        cur = self._cur_stack.pop()
        self.putcur(cur)

        # rollback or commit
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()

        # close the connection if all cursors are closed
        if not self._cur_stack:
            self.putconn(self._conn)

def extact_col_names(cur):
    '''Extracts the column names from a cursor.

    :rtype: list
    '''
    return [desc[0] for desc in cur.description]

def one_to_dict(cur=None, row=None, col_names=None):
    '''Fetch one row from a cursor and make it as a dict.

    If `col_names` or `row` is provided, it will be used first.

    :rtype: dict
    '''

    if col_names is None:
        assert cur is not None, 'You must specify cur or col_names.'
        col_names = extact_col_names(cur)

    if row is None:
        assert cur is not None, 'You must specify cur or row.'
        row = cur.fetchone()

    return dict(izip(col_names, row))

def all_to_dicts(cur=None, rows=None, col_names=None):
    '''Fetch all rows from a cursor and make them as dicts in a list.

    If `col_names` or `rows` is provided, it will be used first.

    :rtype: dicts in list
    '''

    if col_names is None:
        assert cur is not None, 'You must specify cur or col_names.'
        col_names = extact_col_names(cur)

    if rows is None:
        assert cur is not None, 'You must specify cur or rows.'
        rows = cur

    return [dict(izip(col_names, row)) for row in rows]

def group(by_col_names, cur=None, rows=None, col_names=None, to_dict=False):
    '''Group the rows in application-level.

    If `col_names` or `rows` is provided, it will be used first.

    :rtype: row generator

    Assume we have a cursor named ``cur`` has the data:

    ::

        col_names = ['id', 'email']
        rows = [
            ('alice', 'alice@gmail.com'),
            ('mosky', 'mosky.tw@gmail.com'),
            ('mosky', 'mosky.liu@pinkoi.com')
        ]

    Group the rows in ``cur`` by id.

    ::

        for row in group(['id'], cur):
            print row

    The output:

    ::

        ('alice', ['alice@gmail.com'])
        ('mosky', ['mosky.tw@gmail.com', 'mosky.liu@pinkoi.com'])

    '''

    if col_names is None:
        assert cur is not None, 'You must specify cur or col_names.'
        col_names = extact_col_names(cur)

    if rows is None:
        assert cur is not None, 'You must specify cur or rows.'
        rows = cur

    name_index_map = dict((name,idx) for idx,name in enumerate(col_names))
    key_indexes = tuple(name_index_map.get(name) for name in by_col_names)
    key_func = lambda row: tuple(row[i] for i in key_indexes)

    for key_values, rows_islice in groupby(rows, key_func):

        # TODO: the performance

        row = [list(col) for col in izip(*rows_islice)]
        for key_index, key_value in izip(key_indexes, key_values):
            row[key_index] = key_value

        if to_dict:
            yield one_to_dict(row=row, col_names=col_names)
        else:
            yield tuple(row)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = func
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It provides common standard SQL functions.
'''

__all__ = [
    'avg', 'count', 'min', 'max', 'stddev', 'sum', 'variance'
]

from .util import raw, concat_by_comma, identifier

def _make_simple_function(name):

    def simple_function(*args):
        return raw('%s(%s)' % (
            name.upper(),
            concat_by_comma(identifier(x) for x in args)
        ))

    return simple_function

avg      = _make_simple_function('AVG')
count    = _make_simple_function('COUNT')
min      = _make_simple_function('MIN')
max      = _make_simple_function('MAX')
stddev   = _make_simple_function('STDDEV')
sum      = _make_simple_function('SUM')
variance = _make_simple_function('VARIANCE')

########NEW FILE########
__FILENAME__ = json
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
.. deprecated:: 0.6
    The :mod:`mosql.result` will be removed in a future release, so this module
    will not be needed once :mod:`~mosql.result` is removed.

An alternative of built-in `json`.

It is compatible with :py:mod:`mosql.result` and built-in `datetime`.

.. versionadded :: 0.2
    It supports the new :mod:`mosql.result`.

.. versionadded :: 0.1.1
'''

__all__ = ['dump', 'dumps', 'load', 'loads', 'ModelJSONEncoder']

import imp

try:
    # it imports module from built-in first, so it skipped this json.py
    json = imp.load_module('json', *imp.find_module('json'))
except ImportError:
    import simplejson as json

from datetime import datetime, date
from functools import partial

from .result import Model, ColProxy, RowProxy

class ModelJSONEncoder(json.JSONEncoder):
    '''It is compatible with :py:mod:`mosql.result` and built-in `datetime`.'''

    def default(self, obj):

        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError, e:
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, Model):
                return dict(obj)
            elif isinstance(obj, ColProxy):
                return list(obj)
            elif isinstance(obj, RowProxy):
                return dict(obj)
            else:
                raise e

dump = partial(json.dump, cls=ModelJSONEncoder)
'''It uses the :py:class:`ModelJSONEncoder`.'''

dumps = partial(json.dumps, cls=ModelJSONEncoder)
'''It uses the :py:class:`ModelJSONEncoder`.'''

load = json.load
'''It is same as `json.load`.'''

loads = json.loads
'''It is same as `json.loads`.'''

########NEW FILE########
__FILENAME__ = mysql
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It applies the MySQL-specific stuff to :mod:`mosql.util`.

The usage:

::

    import mosql.mysql

It will replace the functions in :mod:`mosql.util` with its functions.
'''

char_escape_map = {
    # The following 7 chars is escaped in MySQL Connector/C (0.6.2)
    '\0' : r'\0',
    '\n' : r'\n',
    '\r' : r'\r',
    '\\' : r'\\',
    '\'' : r'\'',
    '\"' : r'\"',
    '\x1A' : r'\Z',
    # The following 4 chars is escaped in OWASP Enterprise Security API (1.0)
    '\b' : r'\b',
    '\t' : r'\t',
    #'%'  : r'\%',
    #'_'  : r'\_',
    # The above 2 chars shouldn't be escaped, because '\%' and '\_' evaluate
    # to string '\%' and '\_' outside of pattern-matching contexts. Programmers
    # should take responsibility for escaping them in pattern-matching contexts.
}

def escape(s):
    r'''This function escapes the `s` into a executable SQL.

    >>> print escape('\0\n\r\\\'\"\x1A\b\t')
    \0\n\r\\\'\"\Z\b\t

    >>> tmpl = "select * from person where person_id = '%s';"
    >>> evil_value = "' or true; --"

    >>> print tmpl % escape(evil_value)
    select * from person where person_id = '\' or true; --';
    '''
    global char_escape_map
    return ''.join(char_escape_map.get(c) or c for c in s)

def fast_escape(s):
    '''This function only escapes the ``'`` (single-quote) and ``\`` (backslash).

    It is enough for security and correctness, and it is faster 50x than using
    the :func:`escape`, so it is used for replacing the
    :func:`mosql.util.escape` after you import this moudle.
    '''
    return s.replace('\\', '\\\\').replace("'", r"\'")

def format_param(s=''):
    '''This function always returns '%s', so it makes you can use the prepare
    statement with MySQLdb.'''
    return '%s'

def delimit_identifier(s):
    '''It encloses the identifier, `s`, by ````` (back-quote).'''
    return '`%s`' % s

def escape_identifier(s):
    '''It escapes the ````` (back-quote) in the identifier, `s`.'''
    return s.replace('`', '``')

import mosql.util

mosql.util.escape = fast_escape
mosql.util.format_param = format_param
mosql.util.delimit_identifier = delimit_identifier
mosql.util.escape_identifier = escape_identifier

if __name__ == '__main__':
    import doctest
    doctest.testmod()

    #from timeit import timeit
    #from functools import partial

    #timeit = partial(timeit, number=100000)
    #bytes = ''.join(chr(i) for i in range(256))

    #def _escape(s):
    #    return s.replace("'", "''")

    #print timeit(lambda: _escape(bytes))
    ## -> 0.118767976761

    #print timeit(lambda: escape(bytes))
    ## -> 7.97847890854

    #print timeit(lambda: fast_escape(bytes))
    ## -> 0.155963897705

########NEW FILE########
__FILENAME__ = MySQLdb_escape
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
.. deprecated:: 0.6
    You should use safe connection encoding, such as utf-8. This module will be
    removed in a future release.

It applies the escape function in MySQLdb to :mod:`mosql.util`.

Usage:

::

    import mosql.MySQLdb_escape
    mosql.MySQLdb_escape.conn = CONNECTION

It will replace the escape functions in :mod:`mosql.util`.

.. versionadded :: 0.3
'''

import MySQLdb

conn = None

def escape(s):
    global conn
    if not conn:
        conn = MySQLdb.connect()
    return conn.escape_string(s)

import mosql.util
mosql.util.escape = escape

########NEW FILE########
__FILENAME__ = psycopg2_escape
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
.. deprecated:: 0.6
    You should use safe connection encoding, such as utf-8. This module will be
    removed in a future release.

It applies the escape function in psycopg2 to :mod:`mosql.util`.

Usage:

::

    import mosql.psycopg2_escape
    mosql.psycopg2_escape.conn = CONNECTION

It will replace the escape functions in :mod:`mosql.util`.

.. versionadded :: 0.3
'''

from psycopg2.extensions import QuotedString
import psycopg2

conn = None

def escape(s):
    qs = QuotedString(s)
    if conn:
        qs.prepare(conn)
    return qs.getquoted()[1:-1]

import mosql.util
mosql.util.escape = escape

########NEW FILE########
__FILENAME__ = query
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It provides common queies.'''

__all__ = [
    'insert', 'select', 'update', 'delete',
    'join', 'left_join', 'right_join', 'cross_join'
]

from .util import Query
from .stmt import insert, replace, select, update, delete, join

insert = Query(insert, ('table', 'set'))
select = Query(select, ('table', 'where'))
update = Query(update, ('table', 'where', 'set'))
delete = Query(delete, ('table', 'where'))

join       = Query(join, ('table', 'on'))
left_join  = join.breed({'type': 'left'})
right_join = join.breed({'type': 'right'})
cross_join = join.breed({'type': 'cross'})

replace = Query(replace, ('table', 'set'))

########NEW FILE########
__FILENAME__ = result
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
.. deprecated:: 0.6
    It will be removed because it is which MoSQL shouldn't do. If you need a
    model, just write a class with :mod:`mosql.query` instead.

It provides useful :class:`Model` which let you commuicate with database
smoothly.

.. versionchanged:: 0.2
    It is totally rewritten, and it does **not** provide the
    backward-compatibility.
'''

__all__ = ['Model']

from itertools import groupby
from collections import Mapping, Sequence
from pprint import pformat

from . import build
from . import util

class ColProxy(Sequence):

    def __init__(self, model, col_name):
        self.model = model
        self.col_name = col_name

    def __len__(self):
        return self.model.cols[self.col_name].__len__()

    def __iter__(self):
        return self.model.cols[self.col_name].__iter__()

    def __contains__(self, elem):
        return self.model.cols[self.col_name].__contains__(elem)

    def __getitem__(self, row_idx):
        return self.model.cols[self.col_name][row_idx]

    def __setitem__(self, row_idx, val):
        self.model.set(self.col_name, row_idx, val)

    def __repr__(self):
        return pformat(list(self))

class RowProxy(Mapping):

    def __init__(self, model, row_idx):
        self.model = model
        self.row_idx = row_idx

    def __len__(self):
        return len(self.model.cols)

    def __iter__(self):
        return (col_name for col_name in self.model.cols)

    def __contains__(self, elem):
        return elem in self.model.cols

    def __getitem__(self, col_name):
        return self.model.cols[col_name][self.row_idx]

    def __setitem__(self, col_name, val):
        self.model.set(col_name, self.row_idx, val)

    def __getattr__(self, key):

        if key in self.model.cols:
            return self[key]
        else:
            raise AttributeError('%r object has no attribute %r' % (self.__class__.__name__, key))

    # It makes __setattr__ work.
    model = None

    def __setattr__(self, key, val):

        if self.model and key in self.model.cols:
            self[key] = val
        else:
            object.__setattr__(self, key, val)

    def __repr__(self):
        return pformat(dict(self))

def get_col_names(cur):
    return [row_desc[0] for row_desc in cur.description]

class Model(Mapping):
    '''The base model of result set.

    First, for creating connection, you need to override the two methods
    below:

    .. autosummary ::

        Model.getconn
        Model.putconn

    .. seealso ::

         Here are `examples
         <https://github.com/moskytw/mosql/tree/dev/examples>`_ which show how
         to use MoSQL with MySQL or PostgreSQL.

    Second, you may want to adjust the attributes :attr:`table`,
    :attr:`clauses`, :attr:`arrange_by`, :attr:`squashed` or :attr:`ident_by`.

    1. The :attr:`Model.table` is the name of table.
    2. The :attr:`Model.clauses` lets you customize the default clauses of this
       model, ex. order by, join statement, ... .
    3. The :attr:`Model.arrange_by` is need for :meth:`arrange` which arranges
       result set into models.
    4. The :attr:`Model.squashed` defines the columns you want to squash.
    5. The last one, :attr:`Model.ident_by`, makes the :meth:`save` more
       efficiently.

    Then, make some queries to database:

    .. autosummary ::

        Model.select
        Model.insert
        Model.update
        Model.delete
        Model.arrange

    The :meth:`arrange` is like :meth:`select`, but it uses the
    :attr:`arrange_by` to arrange the result set.

    The following two methods treat all of the keyword arguments as `where`. It
    makes statements simpler.

    .. autosummary ::

        Model.where
        Model.find

    If you want to know what arguments you can use, see :mod:`mosql.build`.

    After select, there is a model instance. You can access the data in a model
    instance by the below statements:

    ::

        m['col_name'][row_idx]
        m.col_name[row_idx]

        m[row_idx]['col_name']
        m[row_idx].col_name

        m['col_name']
        m.col_name

        m['col_name'][row_idx] = val
        m.col_name[row_idx] = val

        m[row_idx]['col_name'] = val
        m[row_idx].col_name = val

        # if this column is squashed
        m['col_name'] = val
        m.col_name = val

    .. versionchanged :: 0.4
        Added this format, ``m[row_idx]['col_name']``.

    The :meth:`Model.rows()` also works well:

    ::

        for row in m.rows():
            print row.col_name
            print row['col_name']
            row.col_name = val
            row['col_name'] = val

    .. versionadded:: 0.4

    When you finish your editing, use :meth:`save` to save the changes.

    You also have :meth:`pop` and :meth:`append` (or :meth:`add`) to maintain
    the rows in your model instance, or create a empty model by :meth:`new`.
    '''

    # --- connection-related ---

    @classmethod
    def getconn(cls):
        '''It should return a connection.'''
        raise NotImplementedError('This method should return a connection.')

    @classmethod
    def putconn(cls, conn):
        '''It should accept a connection.'''
        raise NotImplementedError('This method should accept a connection.')

    @classmethod
    def getcur(cls, conn):
        '''It lets you customize your cursor. By default, it return a cursor by the following code:

        ::

            return conn.cursor()

        .. versionadded :: 0.4
        '''
        return conn.cursor()

    dump_sql = False
    '''Set it True to make :meth:`Model.perform` dump the SQLs before it
    performs them.'''

    dry_run = False
    '''Set it True to make :meth:`Model.perform` rollback the changes after it
    performs them.'''

    @classmethod
    def perform(cls, sql=None, param=None, params=None, proc=None, sqls=None):
        '''It performs SQL, SQLs or/and procedure with parameter(s).

        .. versionchanged:: v0.5
            It supports to use parameter and call procedure.
        '''

        conn = cls.getconn()
        cur = cls.getcur(conn)

        if cls.dump_sql:
            if sql or sqls:
                print '--- SQL DUMP ---'
                for sql in (sqls or [sql]):
                    print sql
                print '--- END ---'
            if proc:
                print '--- SQL DUMP ---'
                print 'callproc: %r' % proc
                print '--- END ---'
            if param or params:
                print '--- PARAMETER DUMP ---'
                for param in (params or [param]):
                    print param
                print '--- END ---'

        _do = cur.execute
        _param = param
        if params:
            _do = cur.executemany
            _param = params

        try:
            if sql:
                _do(sql, _param)
            if sqls:
                for sql in sqls:
                    _do(sql, _param)
            if proc:
                cur.callproc(proc, _param)
        except:
            conn.rollback()
            raise
        else:
            if cls.dry_run:
                conn.rollback()
            else:
                conn.commit()

        cls.putconn(conn)

        return cur

    # --- translate result set to a model or models ---

    def __init__(self, defaults=None):
        self.row_len = 0
        self.cols = {}
        self.changes = []
        self.proxies = {}
        self.defaults = defaults or {}

    @classmethod
    def new(cls, **defaults):
        '''Create a empty model instance with the key arguments as the default
        values. It is a shortcut for initialization method.

        A typical usage:

        >>> m = Model.new(id='mosky')
        >>> m.add(email='mosky.tw@gmail.com')
        >>> m.add(email='mosky.liu@pinkoi.com')
        >>> print m
        {'email': ['mosky.tw@gmail.com', 'mosky.liu@pinkoi.com'],
         'id': ['mosky', 'mosky']}

        .. versionadded:: v0.5
        '''
        return cls(defaults)

    @classmethod
    def load_rows(cls, col_names, rows):

        m = cls()

        m.cols = dict((col_name, []) for col_name in col_names)

        for row in rows:
            for col_name, col_val in zip(col_names, row):
                m.cols[col_name].append(col_val)
                if m.squash_all or col_name in m.squashed:
                    m.defaults[col_name] = col_val
            m.row_len += 1

        return m

    @classmethod
    def load_cur(cls, cur):

        # The `description` is None if use an insert, update or delete without
        # `returning`.
        # The `rowcount` is 0 if no row returns from a select.
        if cur.rowcount == 0 or cur.description is None:
            return None
        else:
            return cls.load_rows(get_col_names(cur), cur)

    arrange_by = tuple()
    '''It defines how :meth:`Model.arrange` arrange result set. It should be
    column names in a tuple.'''

    @classmethod
    def arrange_rows(cls, col_names, rows):

        name_index_map = dict((name, i) for i, name  in enumerate(col_names))
        key_indexes = tuple(name_index_map.get(name) for name in cls.arrange_by)

        # use util.default as the hyper None
        key_func = lambda row: tuple(
            row[i] if i is not None else util.default
            for i in key_indexes
        )

        for _, rows in groupby(rows, key_func):
            yield cls.load_rows(col_names, rows)

    @classmethod
    def arrange_cur(cls, cur):
        return cls.arrange_rows(get_col_names(cur), cur)

    # --- shortcuts of Python data structure -> SQL -> result set -> model ---

    table = ''
    '''It is used as the first argument of SQL builder.'''

    clauses = {}
    '''The additional clauses arguments for :mod:`mosql.build`. For example:

    ::

        class Order(Model):
            ...
            table = 'order'
            clauses = dict(order_by=('created',))
            ...
    '''

    @classmethod
    def _query(cls, cur_handler, sql_builder, *args, **kargs):

        if cls.clauses:
            mixed_kargs = cls.clauses.copy()
            if kargs:
                mixed_kargs.update(kargs)
        else:
            mixed_kargs = kargs

        return cur_handler(cls.perform(sql_builder(cls.table, *args, **mixed_kargs)))

    @classmethod
    def select(cls, *args, **kargs):
        '''It performs a select query and load result set into a model.'''
        return cls._query(cls.load_cur, build.select, *args, **kargs)

    @classmethod
    def where(cls, **where):
        '''It uses keyword arguments as `where` and passes to :meth:`select`.'''
        return cls.select(where=where)

    @classmethod
    def arrange(cls, *args, **kargs):
        '''It performs a select query and arrange the result set into models.'''
        return cls._query(cls.arrange_cur, build.select, *args, **kargs)

    @classmethod
    def find(cls, **where):
        '''It uses keyword arguments as `where` and passes to :meth:`arrange`.'''
        return cls.arrange(where=where)

    @classmethod
    def insert(cls, *args, **kargs):
        '''It performs an insert query and load result set into a model (if any).'''
        return cls._query(cls.load_cur, build.insert, *args, **kargs)

    @classmethod
    def update(cls, *args, **kargs):
        '''It performs an update query and load result set into a model (if any).'''
        return cls._query(cls.load_cur, build.update, *args, **kargs)

    @classmethod
    def delete(cls, *args, **kargs):
        '''It performs a delete query and load result set into a model (if any).'''
        return cls._query(cls.load_cur, build.delete, *args, **kargs)

    # --- read this model ---

    def __iter__(self):
        return (name for name in self.cols)

    def __len__(self):
        return len(self.cols)

    def rows(self):
        '''It generates the proxy for each row.

        .. versionadded:: 0.4
        '''
        return (self[i] for i in xrange(self.row_len))

    def proxy(self, name_or_idx):

        if name_or_idx in self.proxies:
            return self.proxies[name_or_idx]
        else:
            Proxy = ColProxy if isinstance(name_or_idx, basestring) else RowProxy
            self.proxies[name_or_idx] = proxy = Proxy(self, name_or_idx)
            return proxy

    squashed = set()
    '''It defines which columns should be squashed. It is better to use a set to
    enumerate the names of columns.'''

    squash_all = False
    '''If you want to squash all of columns, set it True.

    .. versionadded :: 0.4
    '''

    def __getitem__(self, name_or_idx):

        if self.squash_all or name_or_idx in self.squashed:
            try:
                return self.cols[name_or_idx][0]
            except IndexError:
                return None
        else:
            return self.proxy(name_or_idx)

    def __getattr__(self, key):

        if key in self.cols:
            return self[key]
        else:
            raise AttributeError('%r object has no attribute %r' % (self.__class__.__name__, key))

    # It makes __setattr__ work.
    cols = None

    def __setattr__(self, key, val):

        if self.cols and key in self.cols:
            self[key] = val
        else:
            object.__setattr__(self, key, val)

    # --- modifiy this model --- 

    ident_by = None
    '''It defines how to identify a row. It should be column names in a tuple.'''

    def ident(self, row_idx=None):

        # use what columns to build where clause
        if row_idx is None:
            # change this value in all rows in this model
            cond_col_names = self.arrange_by or self.cols
            row_idx = 0
        else:
            cond_col_names = self.ident_by or self.cols

        # build the where
        cond = {}
        for cond_col_name in cond_col_names:

            try:
                cond_val = self.cols[cond_col_name][row_idx]
            except IndexError:
                raise IndexError('row index out of range')
            except KeyError:
                raise KeyError('the column is not existent: %r' % cond_col_name)

            if cond_val is util.default:
                raise ValueError('cond_value of column %r is unknown' % cond_col_name)

            cond[cond_col_name] = cond_val

        return cond

    def __setitem__(self, col_name, val):

        if self.squash_all or col_name in self.squashed:
            self.set(col_name, None, val)
        else:
            raise TypeError("column %r is not squashed." % col_name)

    def set(self, col_name, row_idx, val):

        self.changes.append((self.ident(row_idx), {col_name: val}))

        if row_idx is None:
            for row_idx in xrange(len(self.cols[col_name])):
                self.cols[col_name][row_idx] = val
        else:
            self.cols[col_name][row_idx] = val

    def pop(self, row_idx=-1):
        '''It pops the row you specified in this model.

        .. versionchanged :: v0.4
            It returns the row poped in a dict.
        '''

        self.changes.append((self.ident(row_idx), None))

        poped_row = {}
        for col_name in self.cols:
            poped_row[col_name] = self.cols[col_name].pop(row_idx)

        self.row_len -= 1

        return poped_row

    def append(self, row_map):
        '''It appends a row into model.

        The `row_map` should be a mapping which includes full or part values of
        a row. If you provide a part of row, the row will be filled with 1.
        defaults (by :meth:`__init__`, :meth:`new` or squashed columns) 2. :data:`~mosql.util.default` in order.

        See the :meth:`new` for the typical usage.
        '''

        row_map = row_map.copy()

        for col_name in set(row_map.keys()+self.cols.keys()+self.defaults.keys()):

            if col_name in row_map:
                val = row_map[col_name]
            elif col_name in self.defaults:
                val = row_map[col_name] = self.defaults[col_name]
            else:
                val = row_map[col_name] = util.default

            if col_name in self.cols:
                self.cols[col_name].append(val)
            else:
                self.cols[col_name] = [val]

        self.row_len += 1

        self.changes.append((None, row_map))

    def add(self, **row_map):
        '''It is a shortcut for :meth:`Model.append`.

        .. versionadded:: v0.5
        '''
        self.append(row_map)

    def save(self):
        '''It saves the changes.

        When it encounters an update, it uses :attr:`ident_by` to build where.
        If the column updated is squashed, it will use the :attr:`arrange_by`
        instead. But if the `ident_by` or `arrange_by` is not set, it will use
        all of the columns

        For efficiency, it will merge the updates which have same condition into
        a single update.

        .. versionchanged:: v0.5.1
            It uses `arrange_by` for the column squashed.
        '''

        if not self.changes:
            return

        sqls = []

        for i, (cond, val) in enumerate(self.changes):

            if cond is None:
                sqls.append(build.insert(self.table, set=val, **self.clauses))
            elif val is None:
                sqls.append(build.delete(self.table, where=cond, **self.clauses))
            else:

                # find other update changes which cond is target_cond
                target_cond = cond

                merged_val = val.copy()
                merged_idxs = []

                for j in range(i+1, len(self.changes)):

                    cond, val = self.changes[j]

                    # skip not update changes
                    if cond is None or val is None:
                        continue

                    if cond == target_cond:
                        merged_val.update(val)
                        merged_idxs.append(j)

                for j in reversed(merged_idxs):
                    self.changes.pop(j)

                sqls.append(build.update(self.table, where=target_cond, set=merged_val, **self.clauses))

        self.changes = []

        return self.perform(sqls=sqls)

    def clear(self):
        '''It pops all of the row in this model.

        .. versionchanged:: v0.5.1
            It doesn't call :meth:`pop` anymore. It clears this model directly.

        .. versionadded:: v0.5
        '''
        self.changes.append((self.ident(), None))
        self.cols.clear()

    def __repr__(self):
        return pformat(dict(self))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = sqlite
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It applies the sqlite-specific stuff to :mod:`mosql.util`.

The usage:

::

    import mosql.sqlite

It will replace the functions in :mod:`mosql.util` with its functions.
'''

def format_param(s=''):
    '''It formats the parameter of prepared statement.'''
    return ':%s' % s if s else '?'

import mosql.util
mosql.util.format_param = format_param

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = stmt
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It provides common statements.'''

from .util import Statement
from .clause import returning, where
from .clause import insert, columns, values, on_duplicate_key_update, replace
from .clause import select, from_, joins, group_by, having, order_by, limit, offset
from .clause import for_, of, nowait
from .clause import for_update, lock_in_share_mode
from .clause import update, set_
from .clause import delete
from .clause import type_, join, on, using

def insert_preprocessor(clause_args):

    if 'values' not in clause_args and 'set' in clause_args:

        if hasattr(clause_args['set'], 'items'):
            pairs = clause_args['set'].items()
        else:
            pairs = clause_args['set']

        if pairs:
            clause_args['columns'], clause_args['values'] = zip(*pairs)
        else:
            clause_args['columns'] = clause_args['values'] = tuple()

insert = Statement([insert, columns, values, returning, on_duplicate_key_update], preprocessor=insert_preprocessor)

def select_preprocessor(clause_args):

    if 'from_' in clause_args:
        clause_args['from'] = clause_args['from_']
        del clause_args['from_']

    if 'for_' in clause_args:
        clause_args['for'] = clause_args['for_']
        del clause_args['for_']

    if 'for' in clause_args:
        clause_args['for'] = clause_args['for'].upper()

select = Statement([
    select, from_, joins, where, group_by, having, order_by, limit, offset,
    for_, of, nowait,
    for_update, lock_in_share_mode
], preprocessor=select_preprocessor)

update = Statement([update, set_, where, returning])
delete = Statement([delete, where, returning])

def join_preprocessor(clause_args):

    if 'type' not in clause_args:
        if 'using' in clause_args or 'on' in clause_args:
            clause_args['type'] = 'INNER'
        else:
            clause_args['type'] = 'NATURAL'
    else:
        clause_args['type'] = clause_args['type'].upper()

join = Statement([type_, join, on, using], preprocessor=join_preprocessor)

replace = Statement([replace, columns, values], preprocessor=insert_preprocessor)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''It provides the basic bricks to build SQLs.

The classes or functions you may use frequently:

.. autosummary ::
    raw
    default
    star
    param
    or_
    and_

It is designed for standard SQL and tested in PostgreSQL. If your database uses
non-standard SQL, such as MySQL, you may need to customize and override the
following functions.

.. autosummary ::
    escape
    format_param
    stringify_bool
    delimit_identifier
    escape_identifier

.. note::

    For MySQL, an official patch is here - :doc:`/mysql`.

If you need to customize more, the following classes may help you.

.. autosummary ::
    Clause
    Statement
    Query

.. versionchanged:: 0.1.6
    It is rewritten and totally different from old version.
'''

__all__ = [
    'escape', 'format_param', 'stringify_bool',
    'delimit_identifier', 'escape_identifier',
    'raw', 'param', 'default', '___', 'star',
    'qualifier', 'paren', 'value',
    'OptionError', 'allowed_options', 'identifier',
    'joiner',
    'concat_by_comma', 'concat_by_and', 'concat_by_space', 'concat_by_or',
    'OperatorError', 'allowed_operators',
    'build_where', 'build_set', 'build_on',
    'or_', 'and_',
    'Clause', 'Statement', 'Query'
]

import sys
if sys.version_info >= (3,):
    unicode = str
    basestring = str

from functools import wraps
from datetime import datetime, date, time

def escape(s):
    '''It escapes the value.

    By default, it just replaces ``'`` (single-quote) with ``''`` (two single-quotes).

    It aims at avoiding SQL injection. Here are some examples:

    >>> tmpl = "select * from person where person_id = '%s';"
    >>> evil_value = "' or true; -- "

    >>> print tmpl % evil_value
    select * from person where person_id = '' or true; -- ';

    >>> print tmpl % escape(evil_value)
    select * from person where person_id = '\'' or true; -- ';

    .. warning ::
        If you don't use utf-8 for your connection, such as big5, gbk, please
        use native escape function to ensure the security. See
        :mod:`mosql.psycopg2_escape` or :mod:`mosql.MySQLdb_escape` for more
        information.
    '''
    return s.replace("'", "''")

std_escape = escape

def format_param(s=''):
    '''It formats the parameter of prepared statement.

    By default, it formats the parameter in `pyformat
    <http://www.python.org/dev/peps/pep-0249/#paramstyle>`_.

    >>> format_param('name')
    '%(name)s'

    >>> format_param()
    '%s'
    '''
    return '%%(%s)s' % s if s else '%s'

std_format_param = format_param

def stringify_bool(b):
    '''It stringifies the bool.

    By default, it returns ``'TRUE'`` if `b` is true, otherwise it returns
    ``'FALSE'``.
    '''
    return 'TRUE' if b else 'FALSE'

std_stringify_bool = stringify_bool

def delimit_identifier(s):
    '''It delimits the identifier.

    By default, it conforms the standard to encloses the identifier, `s`, by
    ``"`` (double quote).

    .. note ::
        It is disableable. Set it ``None`` to disable the feature of delimiting
        identifiers. But you have responsibility to ensure the security if you
        disable it.
    '''
    return '"%s"' % s

std_delimit_identifier = delimit_identifier

def escape_identifier(s):
    r'''It escapes the identifier.

    By default, it just replaces ``"`` (double-quote) with ``""`` (two double-quotes).

    It also aims at avoid SQL injection. Here are some examples:

    >>> tmpl = 'select * from person where "%s" = \'mosky\';'
    >>> evil_identifier = 'person_id" = \'\' or true; -- '

    >>> print tmpl % evil_identifier
    select * from person where "person_id" = '' or true; -- " = 'mosky';

    >>> print tmpl % escape_identifier(evil_identifier)
    select * from person where "person_id"" = '' or true; -- " = 'mosky';
    '''
    return s.replace('"', '""')

std_escape_identifier = escape_identifier

class raw(str):
    '''The qualifier function does nothing when the input is an instance of this
    class. This is a subclass of built-in `str` type.

    .. warning ::
        You have responsibility to ensure the security if you use this class.
    '''

    def __repr__(self):
        return 'raw(%r)' % str(self)

default = raw('DEFAULT')
'The ``DEFAULT`` keyword in SQL.'

star = raw('*')
'The ``*`` keyword in SQL.'

class param(str):
    '''The :func:`value` builds this type as a parameter for the prepared statement.

    >>> value(param(''))
    '%s'
    >>> value(param('name'))
    '%(name)s'

    This is just a subclass of built-in `str` type.

    The :class:`___` is an alias of it.
    '''

    def __repr__(self):
        return 'param(%r)' % self

___ = param

def _is_iterable_not_str(x):
    return not isinstance(x, basestring) and hasattr(x, '__iter__')

def qualifier(f):
    '''A decorator which makes all items in an `iterable` apply a qualifier
    function, `f`, or simply apply the qualifier function to the input if the
    input is not an `iterable`.

    The `iterable` here means the iterable except string.

    It also makes a qualifier function returns the input without changes if the
    input is an instance of :class:`raw`.
    '''

    @wraps(f)
    def qualifier_wrapper(x):
        if isinstance(x, raw):
            return x
        elif _is_iterable_not_str(x):
            return [item if isinstance(item, raw) else f(item) for item in x]
        else:
            return f(x)

    return qualifier_wrapper

def _is_select(x):
    return isinstance(x, basestring) and x.startswith('SELECT ')

@qualifier
def value(x):
    '''A qualifier function for values.

    >>> print value('normal string')
    'normal string'

    >>> print value(u'normal unicode')
    'normal unicode'

    >>> print value(True)
    TRUE

    >>> print value(datetime(2013, 4, 19, 14, 41, 10))
    '2013-04-19 14:41:10'

    >>> print value(date(2013, 4, 19))
    '2013-04-19'

    >>> print value(time(14, 41, 10))
    '14:41:10'

    >>> print value(raw('count(person_id) > 1'))
    count(person_id) > 1

    >>> print value(param('myparam'))
    %(myparam)s
    '''

    # NOTE: 1. raw, 2. param is subclass of str and the 3. _is_select tests a
    # kind of str, so the three types must be first than str.

    if x is None:
        return 'NULL'
    elif isinstance(x, raw):
        return x
    elif isinstance(x, param):
        return format_param(x)
    elif _is_select(x):
        return paren(x)
    elif isinstance(x, basestring):
        return "'%s'" % escape(x)
    elif isinstance(x, (datetime, date, time)):
        return "'%s'" % x
    elif isinstance(x, bool):
        return stringify_bool(x)
    else:
        return str(x)

class OptionError(Exception):
    '''The instance of it will be raised when :func:`identifier` detects an
    invalid option.

    .. seealso ::
        The operators allowed --- :attr:`allowed_options`.'''

    def __init__(self, op):
        self.op = op

    def __str__(self):
        return 'this option is not allowed: %r' % self.op

allowed_options = set(['DESC', 'ASC'])
'''The options which are allowed by :func:`identifier`.

An :exc:`OptionError` is raised if an option not allowed is found.

.. note ::
    It is disableable. Set it ``None`` to disable the feature of checking the
    option. But you have responsibility to ensure the security if you disable
    it.
'''

def _is_pair(x):
    return _is_iterable_not_str(x) and len(x) == 2

@qualifier
def identifier(s):
    '''A qualifier function for identifiers.

    It uses the :func:`delimit_identifier` and :func:`escape_identifier` to
    qualifiy the input.

    It returns the input with no changes if :func:`delimit_identifier` is
    ``None``.

    >>> print identifier('column_name')
    "column_name"

    >>> print identifier('column_name desc')
    "column_name" DESC

    >>> print identifier('table_name.column_name')
    "table_name"."column_name"

    >>> print identifier('table_name.column_name DESC')
    "table_name"."column_name" DESC
    '''

    if _is_select(s):
        return paren(s)
    elif _is_pair(s):
        return '%s AS %s' % (identifier(s[0]), identifier(s[1]))
    elif delimit_identifier is None:
        return s
    elif s.find('.') == -1 and s.find(' ') == -1:
        return delimit_identifier(escape_identifier(s))
    else:

        t, _, c = s.rpartition('.')
        c, _, op = c.partition(' ')

        r = ''

        if t:
            t = delimit_identifier(escape_identifier(t))
            r += t+'.'

        if c:
            c = delimit_identifier(escape_identifier(c))
            r += c

        if op:
            op = op.upper()
            if allowed_options is not None and op not in allowed_options:
                raise OptionError(op)
            r += ' '+op

        return r

@qualifier
def paren(s):
    '''A qualifier function which encloses the input with ``()`` (paren).'''
    return '(%s)' % s

def joiner(f):
    '''A decorator which makes the input apply this function only if the input
    is an `iterable`, otherwise it just returns the same input.

    The `iterable` here means the iterable except string.
    '''

    @wraps(f)
    def joiner_wrapper(x):
        if _is_iterable_not_str(x):
            return f(x)
        else:
            return x

    return joiner_wrapper

@joiner
def concat_by_and(i):
    '''A joiner function which concats the iterable by ``'AND'``.'''
    return ' AND '.join(i)

@joiner
def concat_by_or(i):
    '''A joiner function which concats the iterable by ``'OR'``.'''
    return ' OR '.join(i)

@joiner
def concat_by_space(i):
    '''A joiner function which concats the iterable by a space.'''
    return ' '.join(i)

@joiner
def concat_by_comma(i):
    '''A joiner function which concats the iterable by ``,`` (comma).'''
    return ', '.join(i)

class OperatorError(Exception):
    '''The instance of it will be raised when :func:`build_where` detects an
    invalid operator.

    .. seealso ::
        The operators allowed --- :attr:`allowed_operators`.'''

    def __init__(self, op):
        self.op = op

    def __str__(self):
        return 'this operator is not allowed: %r' % self.op

allowed_operators = set([
    '<', '>', '<=', '>=', '=', '<>', '!=',
    'IS', 'IS NOT',
    'IN', 'NOT IN',
    'LIKE', 'NOT LIKE',
    'SIMILAR TO', 'NOT SIMILAR TO',
    '~', '~*', '!~', '!~*',
])
'''The operators which are allowed by :func:`build_where`.

An :exc:`OperatorError` is raised if an operator not allowed is found.

.. note ::
    It is disableable. Set it ``None`` to disable the feature of checking the
    operator. But you have responsibility to ensure the security if you disable
    it.
'''

def _to_pairs(x):

    if hasattr(x, 'iteritems'):
        x = x.iteritems()
    elif hasattr(x, 'items'):
        x = x.items()

    return x

def _build_condition(x, key_qualifier=identifier, value_qualifier=value):

    ps = _to_pairs(x)

    pieces = []

    for k, v in ps:

        # find the op

        op = ''

        # TODO: let user use subquery with operator in first (key) part
        if not isinstance(k, raw):

            # split the op out
            space_pos = k.find(' ')
            if space_pos != -1:
                k, op = k[:space_pos], k[space_pos+1:].strip()

            if not op:
                if _is_iterable_not_str(v):
                    op = 'IN'
                elif v is None:
                    op = 'IS'
                else:
                    op = '='
            else:
                op = op.upper()
                if allowed_operators is not None and op not in allowed_operators:
                    raise OperatorError(op)

        # feature of autoparam
        if isinstance(v, type) and v.__name__ == 'param':
            v = param(k)

        # qualify the v
        v = value_qualifier(v)
        if _is_iterable_not_str(v):
            v = paren(concat_by_comma(v))

        # qualify the k
        k = key_qualifier(k)

        if op:
            pieces.append('%s %s %s' % (k, op, v))
        else:
            pieces.append('%s %s' % (k, v))

    return concat_by_and(pieces)

@joiner
def build_where(x):
    r'''A joiner function which builds the where-list of SQL from a `dict` or
    `pairs`.

    If input is a `dict` or `pairs`:

    >>> print build_where({'detail_id': 1, 'age >= ': 20, 'created': date(2013, 4, 16)})
    "created" = '2013-04-16' AND "detail_id" = 1 AND "age" >= 20

    >>> print build_where((('detail_id', 1), ('age >= ', 20), ('created', date(2013, 4, 16))))
    "detail_id" = 1 AND "age" >= 20 AND "created" = '2013-04-16'

    Building prepared where:

    >>> print build_where({'custom_param': param('my_param'), 'auto_param': param, 'using_alias': ___})
    "auto_param" = %(auto_param)s AND "using_alias" = %(using_alias)s AND "custom_param" = %(my_param)s

    It does noting if input is a string:

    >>> print build_where('"detail_id" = 1 AND "age" >= 20 AND "created" = \'2013-04-16\'')
    "detail_id" = 1 AND "age" >= 20 AND "created" = '2013-04-16'

    The default operator will be changed by the value.

    >>> print build_where({'name': None})
    "name" IS NULL

    >>> print build_where({'person_id': ['andy', 'bob']})
    "person_id" IN ('andy', 'bob')

    It is possible to customize your operators:

    >>> print build_where({'email like': '%@gmail.com%'})
    "email" LIKE '%@gmail.com%'

    >>> print build_where({raw('count(person_id) >'): 10})
    count(person_id) > 10

    .. seealso ::
        By default, the operators are limited. Check the :attr:`allowed_operators`
        for more information.
    '''
    return _build_condition(x, identifier, value)

@joiner
def build_set(x):
    r'''A joiner function which builds the set-list of SQL from a `dict` or
    pairs.

    If input is a `dict` or `pairs`:

    >>> print build_set({'a': 1, 'b': True, 'c': date(2013, 4, 16)})
    "a"=1, "c"='2013-04-16', "b"=TRUE

    >>> print build_set((('a', 1), ('b', True), ('c', date(2013, 4, 16))))
    "a"=1, "b"=TRUE, "c"='2013-04-16'

    Building prepared set:

    >>> print build_set({'custom_param': param('myparam'), 'auto_param': param})
    "auto_param"=%(auto_param)s, "custom_param"=%(myparam)s

    It does noting if input is a string:

    >>> print build_set('"a"=1, "b"=TRUE, "c"=\'2013-04-16\'')
    "a"=1, "b"=TRUE, "c"='2013-04-16'
    '''

    ps = _to_pairs(x)

    pieces = []
    for k, v in ps:

        # feature of autoparam
        if isinstance(v, type) and v.__name__ == 'param':
            v = param(k)

        pieces.append('%s=%s' % (identifier(k), value(v)))

    return concat_by_comma(pieces)

@joiner
def build_on(x):
    '''A joiner function which builds the on-list of SQL from a `dict` or pairs.
    The difference from :func:`build_where` is the value here will be treated as
    an identifier.

    >>> print build_on({'person_id': 'friend_id'})
    "person_id" = "friend_id"

    >>> print build_on((('person.person_id', 'detail.person_id'), ))
    "person"."person_id" = "detail"."person_id"

    >>> print build_on({'person.age >': raw(20)})
    "person"."age" > 20
    '''
    return _build_condition(x, identifier, identifier)

def or_(conditions):
    '''It concats the conditions by ``OR``.

    .. versionchanged:: 0.7.2
        It helps you to add parens now.

    .. versionadded :: 0.6

    >>> print or_(({'person_id': 'andy'}, {'person_id': 'bob'}))
    ("person_id" = 'andy') OR ("person_id" = 'bob')
    '''

    return concat_by_or(paren(build_where(c)) for c in conditions)

def and_(conditions):
    '''It concats the conditions by ``AND``.

    .. versionadded :: 0.7.3

    >>> print and_(({'person_id': 'andy'}, {'name': 'Andy'}))
    ("person_id" = 'andy') AND ("name" = 'Andy')
    '''

    return concat_by_and(paren(build_where(c)) for c in conditions)

# NOTE: To keep simple, the below classes shouldn't rely on the above functions

class Clause(object):
    '''It represents a clause of SQL.

    :param prefix: the lead word(s) of this clause
    :type prefix: str
    :param formatters: the qualifier or joiner functions
    :type formatters: sequence
    :param hidden: it decides the prefix will be hidden or not
    :type hidden: bool
    :param alias: another name of this clause
    :type alias: str
    :param default: it will be used if you pass ``None`` to :meth:`format`
    :type default: str
    :param no_argument: set ``True`` if this clause doesn't have any argument
    :type no_argument: bool

    The :func:`qualifier` functions:

    .. autosummary ::

        value
        identifier
        paren

    The :func:`joiner` functions:

    .. autosummary ::
        build_where
        build_set
        build_on
        concat_by_comma
        concat_by_and
        concat_by_space
        concat_by_or

    Here is an example of using :class:`Clause`:

    >>> values = Clause('values', (value, concat_by_comma, paren))

    >>> print values.format(('a', 'b', 'c'))
    VALUES ('a', 'b', 'c')

    >>> print values.format((default, 'b', 'c'))
    VALUES (DEFAULT, 'b', 'c')

    >>> print values.format((raw('r'), 'b', 'c'))
    VALUES (r, 'b', 'c')

    .. versionchanged :: 0.9
        Added `no_argument` and made `formatters` has default.

    .. versionchanged :: 0.6
        Added two arguments, `alias` and `default`.
    '''

    def __init__(self, name, formatters=tuple(), hidden=False, alias=None, default=None, no_argument=False):

        self.prefix = name.upper()
        self.formatters = formatters
        self.hidden = hidden
        self.no_argument = no_argument

        # the default and possibles both are used by Statement
        self.default = default
        self.possibles = []

        if alias:
            self.possibles.append(alias)

        lower_name = name.lower()
        underscore_lower_name = lower_name.replace(' ', '_')
        self.possibles.append(underscore_lower_name)

        if lower_name != underscore_lower_name:
            self.possibles.append(lower_name)

    def format(self, x):
        '''Apply `x` to this clause template.

        :rtype: str
        '''

        if self.no_argument and x:
            return self.prefix

        for formatter in self.formatters:
            x = formatter(x)

        if _is_iterable_not_str(x):
            x = ''.join(x)

        if self.hidden:
            return '%s' % x
        else:
            return '%s %s' % (self.prefix, x)

    def __repr__(self):
        return 'Clause(%r, %r)' % (self.prefix, self.formatters)

class Statement(object):
    '''It represents a statement of SQL.

    :param clauses: the clauses which consist this statement
    :type clauses: :class:`Clause`
    :param preprocessor: a preprocessor for the argument, `clause_args`, of the :meth:`format`
    :type preprocessor: function

    Here is an example of using :class:`Statement`:

    >>> insert_into = Clause('insert into', (identifier, ))
    >>> columns     = Clause('columns'    , (identifier, concat_by_comma, paren), hidden=True)
    >>> values      = Clause('values'     , (value, concat_by_comma, paren))

    >>> insert_into_stat = Statement((insert_into, columns, values))

    >>> print insert_into_stat.format({
    ...     'insert into': 'person',
    ...     'columns'    : ('person_id', 'name'),
    ...     'values'     : ('daniel', 'Diane Leonard'),
    ... })
    INSERT INTO "person" ("person_id", "name") VALUES ('daniel', 'Diane Leonard')

    .. versionchanged :: 0.6
        Added `preprocessor`.
    '''

    def __init__(self, clauses, preprocessor=None):
        self.clauses = clauses
        self.preprocessor = preprocessor

    def format(self, clause_args):
        '''Apply the `clause_args` to each clauses.

        :param clause_args: the arguments for the clauses
        :type clause_args: dict

        :rtype: str
        '''

        if self.preprocessor:
            clause_args = clause_args.copy()
            self.preprocessor(clause_args)

        pieces = []
        for clause in self.clauses:

            arg = None
            for possible in clause.possibles:
                try:
                    arg = clause_args[possible]
                except KeyError:
                    continue
                else:
                    break

            if arg is None and clause.default:
                arg = clause.default

            if arg is not None:
                pieces.append(clause.format(arg))

        return ' '.join(pieces)

    def __repr__(self):
        return 'Statement(%r)' % self.clauses

def _merge_dicts(default, *updates):
    result = default.copy()
    for update in updates:
        result.update(update)
    return result

class Query(object):
    '''It makes a partial :class:`Statement`.

    :param statement: a statement
    :type statement: :class:`Statement`
    :param positional_keys: the positional arguments accepted by :meth:`stringify`.
    :type positional_keys: sequence
    :param clause_args: the arguments of the clauses you want to predefine
    :type clause_args: dict

    .. versionadded :: 0.6
    '''

    def __init__(self, statement, positional_keys=None, clause_args=None):

        self.statement = statement
        self.positional_keys = positional_keys

        if clause_args is None:
            self.clause_args = {}
        else:
            self.clause_args = clause_args

    def breed(self, clause_args=None):
        '''It merges the `clause_args` from both this instance and the argument,
        and then create new :class:`Query` instance by that.'''
        return Query(
            self.statement,
            self.positional_keys,
            _merge_dicts(self.clause_args, clause_args)
        )

    def format(self, clause_args=None):
        '''It merges the `clause_args` from both this instance and the
        arguments, and then apply to the statement.'''
        clause_args = _merge_dicts(self.clause_args, clause_args)
        return self.statement.format(clause_args)

    def stringify(self, *positional_values, **clause_args):
        '''It is same as the :meth:`format`, but it let you use keyword
        arguments.

        A :class:`Query` instance is callable. When you call it, it uses this
        method to handle.
        '''

        if self.positional_keys and positional_values:
            for k, v in zip(self.positional_keys, positional_values):
                clause_args.setdefault(k, v)

        return self.format(clause_args)

    def __call__(self, *positional_values, **clause_args):
        '''It is same as the :meth:`stringify`. It is for backward-compatibility, and not encourage to use.'''
        return self.stringify(*positional_values, **clause_args)

    def __repr__(self):
        return 'Query(%r, %r, %r)' % (self.statement, self.positional_keys, self.clause_args)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = test_sqlite
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sqlite3
import mosql.sqlite
from mosql.util import param
from mosql.query import insert, select, update, delete, replace
from mosql.db import Database,all_to_dicts

class TestSQLite(unittest.TestCase):

    def setUp(self):

        self.db = Database(sqlite3, 'test_sqlite.db')

        with self.db as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS person (
                    person_id TEXT PRIMARY KEY,
                    name      TEXT
                );
            ''')

    def test_insert(self):
        with self.db as cur:
            cur.execute(insert('person', {
                'person_id': 'mosky',
                'name'     : 'Mosky Liu'
            }))
            self.db._conn.rollback()

    def test_replace(self):
        with self.db as cur:
            cur.execute(replace('person', {
                'person_id': 'mosky',
                'name'     : 'Mosky Liu'
            }))
            self.db._conn.rollback()

    def test_update(self):
        with self.db as cur:
            cur.execute(update('person', {'person_id': 'mosky'}, {'name': 'Mosky Liu'}))
            self.db._conn.rollback()

    def test_delete(self):
        with self.db as cur:
            cur.execute(delete('person', {'person_id': 'mosky'}))
            self.db._conn.rollback()

    def test_select(self):
        with self.db as cur:
            cur.execute(select('person', {'person_id': 'mosky'}))
            self.db._conn.rollback()

    def test_param_query(self):

        with self.db as cur:
            cur.execute(
                select(
                    'person',
                    {'person_id': param('person_id')}
                ),
                {'person_id': 'mosky'}
            )
            self.db._conn.rollback()

    def test_native_escape(self):

        # NOTE: \0 will eat all following chars
        strange_name =  '\n\r\\\'\"\x1A\b\t'

        with self.db as cur:

            cur.execute(
                'insert into person (person_id, name) values (?, ?)',
                ('native', strange_name)
            )

            cur.execute('select name from person where person_id = ?', ('native', ))
            name, = cur.fetchone()

            self.db._conn.rollback()

        assert strange_name == name

    def test_escape(self):

        # NOTE: \0 will cause an OperationalError of MoSQL
        strange_name =  '\n\r\\\'\"\x1A\b\t'

        with self.db as cur:

            cur.execute(insert('person', {
                'person_id': 'mosql',
                'name'     : strange_name
            }))

            cur.execute('select name from person where person_id = ?', ('mosql',))
            name, = cur.fetchone()

            self.db._conn.rollback()

        assert strange_name == name

    def test_fetch_all_data(self):
        with self.db as cur:
            cur.execute(insert('person', {
                'person_id': 'mosky',
                'name'     : 'Mosky Liu'
            }))

            cur.execute(select('person'))
            results = all_to_dicts(cur)
            self.db._conn.rollback()

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from .test_sqlite import TestSQLite

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
