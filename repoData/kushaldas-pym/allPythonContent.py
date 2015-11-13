__FILENAME__ = argvtest
#!/usr/bin/env python
import sys
print "First value", sys.argv[0]
print "All values"
for i, x  in enumerate(sys.argv):
    print i, x

########NEW FILE########
__FILENAME__ = averagen
#!/usr/bin/env python
N = 10
sum = 0
count = 0
while count < N:
    number = float(raw_input(""))
    sum = sum + number
    count = count + 1
average = float(sum)/N
print "N = %d , Sum = %f" % (N, sum)
print "Average = %f" % average

########NEW FILE########
__FILENAME__ = bars
"""
Bars Module
============

This is an example module which provides different ways to print bars.

"""

def starbar(num):
    """
    Prints a bar with *

    :arg num: Length of the bar

    """
    print '*' * num

def hashbar(num):
    """
    Prints a bar with #

    :arg num: Length of the bar

    """
    print '#' * num

def simplebar(num):
    """
    Prints a bar with -

    :arg num: Length of the bar
    
    """
    print '-' * num

########NEW FILE########
__FILENAME__ = continue
#!/usr/bin/env python

while True:
    n = int(raw_input("Please enter an Integer: "))
    if n < 0:
        continue #this will take the execution back to the starting of the loop
    elif n == 0:
        break
    print "Square is ", n ** 2
print "Goodbye"

########NEW FILE########
__FILENAME__ = copyfile
#!/usr/bin/env python
import sys
if len(sys.argv) < 3:
    print "Wrong parameter"
    print "./copyfile.py file1 file2"
    sys.exit(1)
f1 = open(sys.argv[1])
s = f1.read()
f1.close()
f2 = open(sys.argv[2], 'w')
f2.write(s)
f2.close()


########NEW FILE########
__FILENAME__ = countwords
#!/usr/bin/env python
s = raw_input("Enter a line: ")
print "The number of words in the line are %d" % (len(s.split(" ")))

########NEW FILE########
__FILENAME__ = design1
#!/usr/bin/env python
row = int(raw_input("Enter the number of rows: "))
n = row
while n >= 0:
    x =  "*" * n
    print x
    n -= 1

########NEW FILE########
__FILENAME__ = design2
#!/usr/bin/env python
n = int(raw_input("Enter the number of rows: "))
i = 1
while i <= n:
    print "*" * i
    i += 1

########NEW FILE########
__FILENAME__ = design3
#!/usr/bin/env python
row = int(raw_input("Enter the number of rows: "))
n = row
while n >= 0:
    x =  "*" * n
    y = " " * (row - n)
    print y + x
    n -= 1

########NEW FILE########
__FILENAME__ = evaluateequ
#!/usr/bin/env python
sum = 0.0
for i in range(1, 11):
    sum += 1.0 / i
    print "%2d %10.4f" % (i , sum)

########NEW FILE########
__FILENAME__ = evaluationexp
#!/usr/bin/env python
a = 9
b = 12
c = 3
x = a -b / 3 + c * 2 -1
y = a -b / (3 + c) * (2 -1)
z = a - (b / (3 +c) * 2) -1

print "X = ", x
print "Y = ", y
print "Z = ", z

########NEW FILE########
__FILENAME__ = fibonacci1
#!/usr/bin/env python
a, b = 0, 1
while b < 100:
    print b
    a, b = b, a + b

########NEW FILE########
__FILENAME__ = fibonacci2
#!/usr/bin/env python
a, b = 0, 1
while b < 100:
    print b,
    a, b = b, a + b

########NEW FILE########
__FILENAME__ = global
#!/usr/bin/env python
def change(b):
    global a
    a = 90
    print a

a = 9
print "Before the function call ", a
print "inside change function",
change(a)
print "After the function call ", a

########NEW FILE########
__FILENAME__ = integer
#!/usr/bin/env python
days = int(raw_input("Enter days: "))
months = days / 30
days = days % 30
print "Months = %d Days = %d" % (months, days)

########NEW FILE########
__FILENAME__ = integer2
#!/usr/bin/env python
days = int(raw_input("Enter days: "))
print "Months = %d Days = %d" % (divmod(days, 30))

########NEW FILE########
__FILENAME__ = investment
#!/usr/bin/env python
amount = float(raw_input("Enter amount: "))
inrate = float(raw_input("Enter Interest rate: "))
period = int(raw_input("Enter period: "))
value = 0
year = 1
while year <= period:
    value = amount + (inrate * amount)
    print "Year %d Rs. %.2f" %(year, value)
    amount = value
    year = year + 1

########NEW FILE########
__FILENAME__ = local
#!/usr/bin/env python
def change(a):
    a = 90
    print a

a = 9
print "Before the function call ", a
print "inside change function",
change(a)
print "After the function call ", a

########NEW FILE########
__FILENAME__ = matrixmul
#!/usr/bin/env python
n = int(raw_input("Enter the value of n: "))
print "Enter values for the Matrix A"
a = []
for i in range(0, n):
    a.append([int(x) for x in raw_input("").split(" ")])

print "Enter values for the Matrix B"
b = []
for i in range(0, n):
    b.append([int(x) for x in raw_input("").split(" ")])
c = []
for i in range(0, n):
    c.append([a[i][j] * b[j][i] for j in range(0,n)])
print "After matrix multiplication"
print "-" * 10 * n
for x in c:
    for y in x:
        print "%5d" % y,
    print ""
print "-" * 10 * n

########NEW FILE########
__FILENAME__ = multiplication
#!/usr/bin/env python
i = 1
print "-" * 50
while i < 11:
    n = 1
    while n <= 10:
        print "%4d" % (i * n),
        n += 1
    print ""
    i += 1
print "-" * 50

########NEW FILE########
__FILENAME__ = number100
#!/usr/bin/env python
number = int(raw_input("Enter a number: "))
if number < 100:
    print "The number is less than 100"
else:
    print "The number is greater than 100"

########NEW FILE########
__FILENAME__ = palindrome
#!/usr/bin/env python
s = raw_input("Please eneter a string: ")
z = [x for x in s]
z.reverse()
if s == "".join(z):
    print "The string is a palindrome"
else:
    print "The string is not a palindrome"

########NEW FILE########
__FILENAME__ = palindromefunc
#!/usr/bin/env python

def palindrome(s):
    z = s
    z = [x for x in z]
    z.reverse()
    if s == "".join(z):
        return True
    else:
        return False

s = raw_input("Enter a string: ")
if palindrome(s):
    print "Yay a palindrome"
else:
    print "Oh no, not a palindrome"

########NEW FILE########
__FILENAME__ = powerseries
#!/usr/bin/env python
x = float(raw_input("Enter the value of x: "))
n = term = num = 1
sum = 1.0
while n <= 100:
    term *= x / n
    sum += term
    n += 1
    if term < 0.0001:
        break
print "No of Times= %d and Sum= %f" % (n, sum)



########NEW FILE########
__FILENAME__ = quadraticequation
#!/usr/bin/env python
import math

a = int(raw_input("Enter value of a: "))
b = int(raw_input("Enter value of b: "))
c = int(raw_input("Enter value of c: "))
d = b * b - 4 * a * c
if d < 0:
    print "ROOTS are imaginary"
else:
    root1 = (-b + math.sqrt(d)) / (2.0 * a)
    root2 = (-b - math.sqrt(d)) / (2.0 * a)
    

########NEW FILE########
__FILENAME__ = salesmansalary
#!/usr/bin/env python
basic_salary = 1500
bonus_rate = 200
commision_rate = 0.02
numberofcamera = int(raw_input("Enter the number of inputs sold: "))
price = float(raw_input("Enter the total prices: "))
bonus = (bonus_rate * numberofcamera)
commision = (commision_rate * numberofcamera * price)

print "Bonus        = %6.2f" % bonus
print "Commision    = %6.2f" % commision
print "Gross salary = %6.2f" % ( basic_salary + bonus + commision)

########NEW FILE########
__FILENAME__ = shorthand
#!/usr/bin/env python
N = 100
a = 2
while a < N:
    print "%d" % a
    a *= a

########NEW FILE########
__FILENAME__ = showfile
#!/usr/bin/env python
name = raw_input("Enter the filename: ")
f = open(name)
print f.read()
f.close()

########NEW FILE########
__FILENAME__ = sticks
#!/usr/bin/env python

sticks = 21

print "There are 21 sticks, you can take 1-4 number of sticks at a time."
print "Whoever will take the last stick will loose"

while True:
    print "Sticks left: " , sticks
    sticks_taken = int(raw_input("Take sticks(1-4):"))
    if sticks == 1:
        print "You took the last stick, you loose"
        break
    if sticks_taken >=5 or sticks_taken <=0:
        print "Wrong choice"
        continue
    print "Computer took: " , (5 - sticks_taken) , "\n\n"
    sticks -= 5


########NEW FILE########
__FILENAME__ = students
#!/usr/bin/env python
n = int(raw_input("Enter the number of students:"))
data = {} # here we will store the data
languages = ('Physics', 'Maths', 'History') #all languages
for i in range(0, n): #for the n number of students
    name = raw_input('Enter the name of the student %d: ' % (i + 1)) #Get the name of the student
    marks = []
    for x in languages: 
        marks.append(int(raw_input('Enter marks of %s: ' % x))) #Get the marks for  languages
    data[name] = marks

for x, y in data.iteritems():
    total =  sum(y)
    print "%s 's  total marks %d" % (x, total)
    if total < 120:
        print "%s failed :(" % x
    else:
        print "%s passed :)" % y

    


########NEW FILE########
__FILENAME__ = student_teacher
#!/usr/bin/env python

class Person(object):
    """
    Returns a ```Person``` object with given name.

    """
    def __init__(self,name):
        self.name = name

    def get_details(self):
        "Returns a string containing name of the person"
        return self.name


class Student(Person):
    """
    Returns a ```Student``` object, takes 3 arguments, name, branch, year.
    
    """
    def __init__(self,name,branch,year):
        Person.__init__(self,name)
        self.branch = branch
        self.year = year

    def get_details(self):
        "Returns a string containing student's details."
        return "%s studies %s and is in %s year." % (self.name, self.branch, self.year)


class Teacher(Person):
    """
    Returns a ```Teacher``` object, takes a list of strings (list of papers) as
    argument.
    """    
    def __init__(self, name, papers):
        Person.__init__(self, name)
        self.papers = papers

    def get_details(self):
        return "%s teaches %s" % (self.name, ','.join(self.papers))


person1 = Person('Rahul')
student1 = Student('Kushal', 'CSE', 2005)
teacher1 = Teacher('Prashad', ['C', 'C++'])

print person1.get_details()
print student1.get_details()
print teacher1.get_details()


########NEW FILE########
__FILENAME__ = temperature
#!/usr/bin/env python
farenhite = 0.0
print "Farenhite Celcious"
while farenhite <= 250:
    celcious = ( farenhite - 32.0 ) / 1.8
    print "%5.1f %7.2f" % (farenhite , celcious)
    farenhite = farenhite + 25

########NEW FILE########
__FILENAME__ = testhundred
#!/usr/bin/env python
number = int(raw_input("Enter an integer: "))
if number < 100:
    print "Your number is smaller than 100"
else:
    print "Your number is greater than 100"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Python for you and me documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  9 14:32:48 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'kr'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.intersphinx', 'sphinx.ext.pngmath']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Python for you and me'
copyright = u'2008-2013, Kushal Das'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3.alpha1'

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
# html_theme = 'default'

html_sidebars = { 
    'index':    ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
    '**':       ['sidebarlogo.html', 'localtoc.html', 'relations.html',
                 'sourcelink.html', 'searchbox.html']
}

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
htmlhelp_basename = 'Pythonforyouandmedoc'


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
  ('index', 'Pythonforyouandme.tex', u'Python for you and me',
   u'Kushal Das', 'manual'),
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
    ('index', 'pythonforyouandme', u'Python for you and me Documentation',
     [u'Kushal Das'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Pythonforyouandme', u'Python for you and me Documentation',
   u'Kushal Das', 'Pythonforyouandme', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Python for you and me'
epub_author = u'Kushal Das'
epub_publisher = u'Kushal Das'
epub_copyright = u'2008-2013, Kushal Das'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}
latex_preamble = """
\usepackage{upquote}
"""

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
