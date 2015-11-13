__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = cell_access
from xlrd import open_workbook,XL_CELL_TEXT

book = open_workbook('odd.xls')
sheet = book.sheet_by_index(1)

cell = sheet.cell(0,0)
print cell
print cell.value
print cell.ctype==XL_CELL_TEXT

for i in range(sheet.ncols):
    print sheet.cell_type(1,i),sheet.cell_value(1,i)

########NEW FILE########
__FILENAME__ = cell_types
from xlrd import open_workbook

def cell_contents(sheet,row_x):
    result = []
    for col_x in range(2,sheet.ncols):
        cell = sheet.cell(row_x,col_x)
        result.append((cell.ctype,cell,cell.value))
    return result

sheet = open_workbook('types.xls').sheet_by_index(0)

print 'XL_CELL_TEXT',cell_contents(sheet,1)
print 'XL_CELL_NUMBER',cell_contents(sheet,2)
print 'XL_CELL_DATE',cell_contents(sheet,3)
print 'XL_CELL_BOOLEAN',cell_contents(sheet,4)
print 'XL_CELL_ERROR',cell_contents(sheet,5)
print 'XL_CELL_BLANK',cell_contents(sheet,6)
print 'XL_CELL_EMPTY',cell_contents(sheet,7)

print
sheet = open_workbook(
            'types.xls',formatting_info=True
            ).sheet_by_index(0)

print 'XL_CELL_TEXT',cell_contents(sheet,1)
print 'XL_CELL_NUMBER',cell_contents(sheet,2)
print 'XL_CELL_DATE',cell_contents(sheet,3)
print 'XL_CELL_BOOLEAN',cell_contents(sheet,4)
print 'XL_CELL_ERROR',cell_contents(sheet,5)
print 'XL_CELL_BLANK',cell_contents(sheet,6)
print 'XL_CELL_EMPTY',cell_contents(sheet,7)


########NEW FILE########
__FILENAME__ = dates
from datetime import date,datetime,time
from xlrd import open_workbook,xldate_as_tuple

book = open_workbook('types.xls')
sheet = book.sheet_by_index(0)

date_value = xldate_as_tuple(sheet.cell(3,2).value,book.datemode)
print datetime(*date_value),date(*date_value[:3])
datetime_value = xldate_as_tuple(sheet.cell(3,3).value,book.datemode)
print datetime(*datetime_value)
time_value = xldate_as_tuple(sheet.cell(3,4).value,book.datemode)
print time(*time_value[3:])
print datetime(*time_value)

########NEW FILE########
__FILENAME__ = emptyblank
from xlrd import open_workbook,empty_cell

print empty_cell.value

book = open_workbook('types.xls')
sheet = book.sheet_by_index(0)
empty = sheet.cell(6,2)
blank = sheet.cell(7,2)
print empty is blank, empty is empty_cell, blank is empty_cell

book = open_workbook('types.xls',formatting_info=True)
sheet = book.sheet_by_index(0)
empty = sheet.cell(6,2)
blank = sheet.cell(7,2)
print empty.ctype,repr(empty.value)
print blank.ctype,repr(blank.value)

########NEW FILE########
__FILENAME__ = errors
from xlrd import open_workbook,error_text_from_code

book = open_workbook('types.xls')
sheet = book.sheet_by_index(0)

print error_text_from_code[sheet.cell(5,2).value]
print error_text_from_code[sheet.cell(5,3).value]


########NEW FILE########
__FILENAME__ = introspect_book
from xlrd import open_workbook

book = open_workbook('simple.xls')

print book.nsheets

for sheet_index in range(book.nsheets):
    print book.sheet_by_index(sheet_index)

print book.sheet_names()
for sheet_name in book.sheet_names():
    print book.sheet_by_name(sheet_name)

for sheet in book.sheets():
    print sheet

########NEW FILE########
__FILENAME__ = introspect_sheet
from xlrd import open_workbook,cellname

book = open_workbook('odd.xls')
sheet = book.sheet_by_index(0)

print sheet.name

print sheet.nrows
print sheet.ncols

for row_index in range(sheet.nrows):
    for col_index in range(sheet.ncols):
        print cellname(row_index,col_index),'-',
        print sheet.cell(row_index,col_index).value

########NEW FILE########
__FILENAME__ = large_files
from xlrd import open_workbook

book = open_workbook('simple.xls',on_demand=True)

for name in book.sheet_names():
    if name.endswith('2'):
        sheet = book.sheet_by_name(name)
        print sheet.cell_value(0,0)
        book.unload_sheet(name)

########NEW FILE########
__FILENAME__ = open
from mmap import mmap,ACCESS_READ
from xlrd import open_workbook

print open_workbook('simple.xls')

with open('simple.xls', 'rb') as f:
    print open_workbook(
        file_contents=mmap(f.fileno(),0,access=ACCESS_READ)
        )

aString = open('simple.xls','rb').read()
print open_workbook(file_contents=aString)

    

########NEW FILE########
__FILENAME__ = sheet_iteration
from xlrd import open_workbook

book = open_workbook('odd.xls')
sheet0 = book.sheet_by_index(0)
sheet1 = book.sheet_by_index(1)

print sheet0.row(0)
print sheet0.col(0)
print
print sheet0.row_slice(0,1)
print sheet0.row_slice(0,1,2)
print sheet0.row_values(0,1)
print sheet0.row_values(0,1,2)
print sheet0.row_types(0,1)
print sheet0.row_types(0,1,2)
print
print sheet1.col_slice(0,1)
print sheet0.col_slice(0,1,2)
print sheet1.col_values(0,1)
print sheet0.col_values(0,1,2)
print sheet1.col_types(0,1)
print sheet0.col_types(0,1,2)

########NEW FILE########
__FILENAME__ = simple
from xlrd import open_workbook

wb = open_workbook('simple.xls')

for s in wb.sheets():
    print 'Sheet:',s.name
    for row in range(s.nrows):
        values = []
        for col in range(s.ncols):
            values.append(s.cell(row,col).value)
        print ','.join(values)
    print

########NEW FILE########
__FILENAME__ = utilities
from xlrd import cellname, cellnameabs, colname

print cellname(0,0),cellname(10,10),cellname(100,100)
print cellnameabs(3,1),cellnameabs(41,59),cellnameabs(265,358)
print colname(0),colname(10),colname(100)

########NEW FILE########
__FILENAME__ = copy
from xlrd import open_workbook
from xlwt import easyxf
from xlutils.copy import copy

rb = open_workbook('source.xls',formatting_info=True)
rs = rb.sheet_by_index(0)
wb = copy(rb)
ws = wb.get_sheet(0)

plain = easyxf('')
for i,cell in enumerate(rs.col(2)):
    if not i:
        continue
    ws.write(i,2,cell.value,plain)

for i,cell in enumerate(rs.col(4)):
    if not i:
        continue
    ws.write(i,4,cell.value-1000)

wb.save('output.xls')

########NEW FILE########
__FILENAME__ = display
from xlrd import open_workbook
from xlutils.display import quoted_sheet_name
from xlutils.display import cell_display

wb = open_workbook('source.xls')

print quoted_sheet_name(wb.sheet_names()[0])
print repr(quoted_sheet_name(u'Price(\xa3)','utf-8'))
print quoted_sheet_name(u'My Sheet')
print quoted_sheet_name(u"John's Sheet")

sheet = wb.sheet_by_index(0)
print cell_display(sheet.cell(1,1))
print cell_display(sheet.cell(1,3),wb.datemode)

########NEW FILE########
__FILENAME__ = filter
import os

from xlutils.filter import BaseReader,BaseFilter,BaseWriter,process

class Reader(BaseReader):
    def get_filepaths(self):
        return [os.path.abspath('source.xls')]

class Writer(BaseWriter):
    def get_stream(self,filename):
        return file(filename,'wb')

class Filter(BaseFilter):

    pending_row = None
    wtrowxi = 0
    
    def workbook(self,rdbook,wtbook_name):
        self.next.workbook(rdbook,'filtered-'+wtbook_name)
        
    def row(self,rdrowx,wtrowx):
        self.pending_row = (rdrowx,wtrowx)
        
    def cell(self,rdrowx,rdcolx,wtrowx,wtcolx):
        if rdcolx==0:
            value = self.rdsheet.cell(rdrowx,rdcolx).value
            if value.strip().lower()=='x':
                self.ignore_row = True
                self.wtrowxi -= 1
            else:
                self.ignore_row = False
                rdrowx, wtrowx = self.pending_row
                self.next.row(rdrowx,wtrowx+self.wtrowxi)
        elif not self.ignore_row:
            self.next.cell(
                rdrowx,rdcolx,wtrowx+self.wtrowxi,wtcolx-1
                )        

process(Reader(),Filter(),Writer())

########NEW FILE########
__FILENAME__ = styles
from xlrd import open_workbook
from xlutils.styles import Styles

book = open_workbook('source.xls',formatting_info=True)
styles = Styles(book)
sheet = book.sheet_by_index(0)

print styles[sheet.cell(1,1)].name
print styles[sheet.cell(1,2)].name

A1_style = styles[sheet.cell(0,0)]
A1_font = book.font_list[A1_style.xf.font_index]
print book.colour_map[A1_font.colour_index]

########NEW FILE########
__FILENAME__ = borders
from xlwt import Workbook,easyxf
tl = easyxf('border: left thick, top thick')
t = easyxf('border: top thick')
tr = easyxf('border: right thick, top thick')
r = easyxf('border: right thick')
br = easyxf('border: right thick, bottom thick')
b = easyxf('border: bottom thick')
bl = easyxf('border: left thick, bottom thick')
l = easyxf('border: left thick')

w = Workbook()
ws = w.add_sheet('Border')
ws.write(1,1,style=tl)
ws.write(1,2,style=t)
ws.write(1,3,style=tr)
ws.write(2,3,style=r)
ws.write(3,3,style=br)
ws.write(3,2,style=b)
ws.write(3,1,style=bl)
ws.write(2,1,style=l)

w.save('borders.xls')

########NEW FILE########
__FILENAME__ = cell_types
from datetime import date,time,datetime
from decimal import Decimal
from xlwt import Workbook,Style

wb = Workbook()

ws = wb.add_sheet('Type examples')

ws.row(0).write(0,u'\xa3')
ws.row(0).write(1,'Text')

ws.row(1).write(0,3.1415)
ws.row(1).write(1,15)
ws.row(1).write(2,265L)
ws.row(1).write(3,Decimal('3.65'))
ws.row(2).set_cell_number(0,3.1415)
ws.row(2).set_cell_number(1,15)
ws.row(2).set_cell_number(2,265L)
ws.row(2).set_cell_number(3,Decimal('3.65'))

ws.row(3).write(0,date(2009,3,18))
ws.row(3).write(1,datetime(2009,3,18,17,0,1))
ws.row(3).write(2,time(17,1))
ws.row(4).set_cell_date(0,date(2009,3,18))
ws.row(4).set_cell_date(1,datetime(2009,3,18,17,0,1))
ws.row(4).set_cell_date(2,time(17,1))

ws.row(5).write(0,False)
ws.row(5).write(1,True)
ws.row(6).set_cell_boolean(0,False)
ws.row(6).set_cell_boolean(1,True)

ws.row(7).set_cell_error(0,0x17)
ws.row(7).set_cell_error(1,'#NULL!')

ws.row(8).write(
    0,'',Style.easyxf('pattern: pattern solid, fore_colour green;'))
ws.row(8).write(
    1,None,Style.easyxf('pattern: pattern solid, fore_colour blue;'))
ws.row(9).set_cell_blank(
    0,Style.easyxf('pattern: pattern solid, fore_colour yellow;'))

ws.row(10).set_cell_mulblanks(
    5,10,Style.easyxf('pattern: pattern solid, fore_colour red;')
    )

wb.save('types.xls')

########NEW FILE########
__FILENAME__ = easyxf_format
from datetime import date
from xlwt import Workbook, easyxf

book = Workbook()
sheet = book.add_sheet('A Date')

sheet.write(1,1,date(2009,3,18),easyxf(
    'font: name Arial;'
    'borders: left thick, right thick, top thick, bottom thick;'
    'pattern: pattern solid, fore_colour red;',
    num_format_str='YYYY-MM-DD'
    ))

book.save('date.xls')

########NEW FILE########
__FILENAME__ = format_rowscols
from xlwt import Workbook, easyxf
from xlwt.Utils import rowcol_to_cell

row = easyxf('pattern: pattern solid, fore_colour blue')
col = easyxf('pattern: pattern solid, fore_colour green')
cell = easyxf('pattern: pattern solid, fore_colour red')

book = Workbook()

sheet = book.add_sheet('Precedence')
for i in range(0,10,2):
    sheet.row(i).set_style(row)
for i in range(0,10,2):
    sheet.col(i).set_style(col)
for i in range(10):
    sheet.write(i,i,None,cell)

sheet = book.add_sheet('Hiding')
for rowx in range(10):
    for colx in range(10):
        sheet.write(rowx,colx,rowcol_to_cell(rowx,colx))                    
for i in range(0,10,2):
    sheet.row(i).hidden = True
    sheet.col(i).hidden = True

sheet = book.add_sheet('Row height and Column width')
for i in range(10):
    sheet.write(0,i,0)
for i in range(10):
    sheet.row(i).set_style(easyxf('font:height '+str(200*i)))
    sheet.col(i).width = 256*i

book.save('format_rowscols.xls')

########NEW FILE########
__FILENAME__ = formulae
from xlwt import Workbook, Formula

book = Workbook()

sheet1 = book.add_sheet('Sheet 1')
sheet1.write(0,0,10)
sheet1.write(0,1,20)
sheet1.write(1,0,Formula('A1/B1'))

sheet2 = book.add_sheet('Sheet 2')
row = sheet2.row(0)
row.write(0,Formula('sum(1,2,3)'))
row.write(1,Formula('SuM(1;2;3)'))
row.write(2,Formula("$A$1+$B$1*SUM('ShEEt 1'!$A$1:$b$2)"))

book.save('formula.xls')

########NEW FILE########
__FILENAME__ = hyperlinks
from xlwt import Workbook,easyxf,Formula

style = easyxf('font: underline single')

book = Workbook()
sheet = book.add_sheet('Hyperlinks')

sheet.write(
    0, 0,
    Formula('HYPERLINK("http://www.python.org";"Python")'),
    style)

sheet.write(
    1,0,
    Formula('HYPERLINK("mailto:python-excel@googlegroups.com";"help")'),
    style)

book.save("hyperlinks.xls")

########NEW FILE########
__FILENAME__ = images
from xlwt import Workbook
w = Workbook()
ws = w.add_sheet('Image')
ws.insert_bitmap('python.bmp', 0, 0)
w.save('images.xls')

########NEW FILE########
__FILENAME__ = merged
from xlwt import Workbook,easyxf
style = easyxf(
    'pattern: pattern solid, fore_colour red;'
    'align: vertical center, horizontal center;'
    )
w = Workbook()
ws = w.add_sheet('Merged')
ws.write_merge(1,5,1,5,'Merged',style)
w.save('merged.xls')

########NEW FILE########
__FILENAME__ = outlines
from xlwt import Workbook

data = [
    ['','','2008','','2009'],
    ['','','Jan','Feb','Jan','Feb'],
    ['Company X'],
    ['','Division A'],
    ['','',100,200,300,400],
    ['','Division B'],
    ['','',100,99,98,50],
    ['Company Y'],
    ['','Division A'],
    ['','',100,100,100,100],
    ['','Division B'],
    ['','',100,101,102,103],
    ]

w = Workbook()
ws = w.add_sheet('Outlines')
for i,row in enumerate(data):
    for j,cell in enumerate(row):
        ws.write(i,j,cell)

ws.row(2).level = 1
ws.row(3).level = 2
ws.row(4).level = 3
ws.row(5).level = 2
ws.row(6).level = 3
ws.row(7).level = 1
ws.row(8).level = 2
ws.row(9).level = 3
ws.row(10).level = 2
ws.row(11).level = 3

ws.col(2).level = 1
ws.col(3).level = 2
ws.col(4).level = 1
ws.col(5).level = 2

w.save('outlines.xls')

########NEW FILE########
__FILENAME__ = overwriting
from xlwt import Workbook

book = Workbook()
sheet1 = book.add_sheet('Sheet 1',cell_overwrite_ok=True)
sheet1.write(0,0,'original')
sheet = book.get_sheet(0)
sheet.write(0,0,'new')

sheet2 = book.add_sheet('Sheet 2')
sheet2.write(0,0,'original')
sheet2.write(0,0,'new')

########NEW FILE########
__FILENAME__ = panes
from xlwt import Workbook
from xlwt.Utils import rowcol_to_cell

w = Workbook()
sheet = w.add_sheet('Freeze')
sheet.panes_frozen = True
sheet.remove_splits = True
sheet.vert_split_pos = 2
sheet.horz_split_pos = 10
sheet.vert_split_first_visible = 5
sheet.horz_split_first_visible = 40

for col in range(20):
    for row in range(80):
        sheet.write(row,col,rowcol_to_cell(row,col))

w.save('panes.xls')

########NEW FILE########
__FILENAME__ = simple
from tempfile import TemporaryFile
from xlwt import Workbook

book = Workbook()
sheet1 = book.add_sheet('Sheet 1')
book.add_sheet('Sheet 2')

sheet1.write(0,0,'A1')
sheet1.write(0,1,'B1')
row1 = sheet1.row(1)
row1.write(0,'A2')
row1.write(1,'B2')
sheet1.col(0).width = 10000

sheet2 = book.get_sheet(1)
sheet2.row(0).write(0,'Sheet 2 A1')
sheet2.row(0).write(1,'Sheet 2 B1')
sheet2.flush_row_data()
sheet2.write(1,0,'Sheet 2 A3')
sheet2.col(0).width = 5000
sheet2.col(0).hidden = True

book.save('simple.xls')
book.save(TemporaryFile())

########NEW FILE########
__FILENAME__ = stylecompression
from xlwt import Workbook, easyxf

style1 = easyxf('font: name Times New Roman')
style2 = easyxf('font: name Times New Roman')
style3 = easyxf('font: name Times New Roman')

def write_cells(book):
    sheet = book.add_sheet('Content')
    sheet.write(0,0,'A1',style1)
    sheet.write(0,1,'B1',style2)
    sheet.write(0,2,'C1',style3)
    
book = Workbook()
write_cells(book)
book.save('3xf3fonts.xls')

book = Workbook(style_compression=1)
write_cells(book)
book.save('3xf1font.xls')

book = Workbook(style_compression=2)
write_cells(book)
book.save('1xf1font.xls')

########NEW FILE########
__FILENAME__ = utilities
from xlwt import Utils

print 'AA ->',Utils.col_by_name('AA')
print 'A ->',Utils.col_by_name('A')

print 'A1 ->',Utils.cell_to_rowcol('A1')
print '$A$1 ->',Utils.cell_to_rowcol('$A$1')

print 'A1 ->',Utils.cell_to_rowcol2('A1')

print (0,0),'->',Utils.rowcol_to_cell(0,0)
print (0,0,False,True),'->',
print Utils.rowcol_to_cell(0,0,False,True)
print (0,0,True,True),'->',
print Utils.rowcol_to_cell(
          row=0,col=0,row_abs=True,col_abs=True
          )

print '1:3 ->',Utils.cellrange_to_rowcol_pair('1:3')
print 'B:G ->',Utils.cellrange_to_rowcol_pair('B:G')
print 'A2:B7 ->',Utils.cellrange_to_rowcol_pair('A2:B7')
print 'A1 ->',Utils.cellrange_to_rowcol_pair('A1')

print (0,0,100,100),'->',
print Utils.rowcol_pair_to_cellrange(0,0,100,100)
print (0,0,100,100,True,False,False,False),'->',
print Utils.rowcol_pair_to_cellrange(
          row1=0,col1=0,row2=100,col2=100,
          row1_abs=True,col1_abs=False,
          row2_abs=False,col2_abs=True
          )

for name in (
    '',"'quoted'","O'hare","X"*32,"[]:\\?/*\x00"
    ):
    print 'Is %r a valid sheet name?' % name,
    if Utils.valid_sheet_name(name):
        print "Yes"
    else:
        print "No"

########NEW FILE########
__FILENAME__ = xfstyle_format
from datetime import date
from xlwt import Workbook, XFStyle, Borders, Pattern, Font

fnt = Font()
fnt.name = 'Arial'

borders = Borders()
borders.left = Borders.THICK
borders.right = Borders.THICK
borders.top = Borders.THICK
borders.bottom = Borders.THICK

pattern = Pattern()
pattern.pattern = Pattern.SOLID_PATTERN
pattern.pattern_fore_colour = 0x0A

style = XFStyle()
style.num_format_str='YYYY-MM-DD'
style.font = fnt
style.borders = borders
style.pattern = pattern

book = Workbook()
sheet = book.add_sheet('A Date')
sheet.write(1,1,date(2009,3,18),style)

book.save('date.xls')

########NEW FILE########
__FILENAME__ = zoom
from xlwt import Workbook

w = Workbook()

ws = w.add_sheet('Normal')
ws.write(0,0,'Some text')
ws.normal_magn = 75

ws = w.add_sheet('Page Break Preview')
ws.write(0,0,'Some text')
ws.preview_magn = 150
ws.page_preview = True

w.save('zoom.xls')

########NEW FILE########
__FILENAME__ = test_examples
from __future__ import with_statement

import os

from cStringIO import StringIO
from glob import glob
from os import path, environ
from os.path import abspath
from re import compile
from shutil import copy
from subprocess import call, STDOUT
from tempfile import TemporaryFile
from testfixtures import TempDirectory, compare
from xlrd import Book, biff_dump

initial = os.getcwd()
base = abspath(path.join(path.dirname(abspath(__file__)), os.pardir))
runner = abspath(path.join(base, 'bin', 'py'))
examples = path.join(base, 'students')
expected = path.join(base, 'tests', 'expected')

sub_res = [
    (compile('0+x[0-9A-Fa-f]+'), '...'),
    (compile('".+'+os.sep.replace('\\','\\\\')+'(.+.py)"'), '"\\1"'),
    ]

def get_biff_records(data):
    outfile = StringIO()
    bk = Book()
    bk.biff2_8_load(file_contents=data, logfile=outfile, )
    biff_dump(bk.mem, bk.base, bk.stream_len, 0, outfile, unnumbered=True)
    return outfile.getvalue()
    
def check_example(package, filename):
    example_dir = path.join(examples, package)
    expected_dir = path.join(expected, package)
    expected_base = path.join(expected_dir, path.splitext(filename)[0])
        
    try:
        
        with TempDirectory() as actual:
            # copy files to the directory
            copy(path.join(example_dir, filename), actual.path)
            for pattern in ('*.xls', '*.bmp'):
                for fixture in glob(path.join(example_dir, pattern)):
                    copy(fixture, actual.path)

            os.chdir(actual.path)
            output = TemporaryFile('w+')

            # run the example
            before_listing = set(os.listdir(actual.path))
            call([runner, filename], stdout=output, stderr=STDOUT)
            after_listing = set(os.listdir(actual.path))

            # check the console output
            output.seek(0)
            actual_output = output.read().strip().replace('\r', '')
            for re, rp in sub_res:
                actual_output = re.sub(rp, actual_output)
            expected_path = expected_base+'.txt'
            if not path.exists(expected_path):
                expected_output = ''
            else:
                expected_output = open(expected_path).read().strip().replace('\r', '')
            compare(expected_output, actual_output)

            # check the files created
            created = after_listing.difference(before_listing)

            expected_names = set()
            if os.path.exists(expected_base):
                expected_names = set(os.listdir(expected_base))
                
            for name in created:
                with open(path.join(actual.path, name), 'rb') as af:
                    actual_data = af.read()

                if name in expected_names:
                    expected_path = path.join(expected_base, name)
                    expected_data = open(expected_path, 'rb').read()
                    expected_names.remove(name)
                    if actual_data != expected_data:
                        if environ.get('REPLACE_EXAMPLES'):
                            with open(expected_path, 'wb') as new_expected:
                                new_expected.write(actual_data)
                        compare(
                            get_biff_records(expected_data),
                            get_biff_records(actual_data),
                            )
                else:
                    raise AssertionError("unexpected output: %s" % name)
            
            for name in expected_names:
                if name != '.svn':
                    print created
                    raise AssertionError("expected output missing: %s" % name)
        
            
    finally:
        os.chdir(initial)
    
def test_examples():
    for package in ('xlrd', 'xlwt', 'xlutils'):
        for py in glob(path.join(examples, package, '*.py')):
            yield check_example, package, path.split(py)[1]
        

########NEW FILE########
