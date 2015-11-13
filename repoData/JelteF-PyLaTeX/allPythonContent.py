__FILENAME__ = example
#!/usr/bin/python

import numpy as np

from pylatex import Document, Section, Subsection, Table, Math, TikZ, Axis, \
    Plot
from pylatex.numpy import Matrix
from pylatex.utils import italic

doc = Document()
section = Section('Yaay the first section, it can even be ' + italic('italic'))

section.append('Some regular text')

math = Subsection('Math that is incorrect', data=[Math(data=['2*3', '=', 9])])

section.append(math)
table = Table('rc|cl')
table.add_hline()
table.add_row((1, 2, 3, 4))
table.add_hline(1, 2)
table.add_empty_row()
table.add_row((4, 5, 6, 7))

table = Subsection('Table of something', data=[table])

section.append(table)

a = np.array([[100, 10, 20]]).T
M = np.matrix([[2, 3, 4],
               [0, 0, 1],
               [0, 0, 2]])

math = Math(data=[Matrix(M), Matrix(a), '=', Matrix(M*a)])
equation = Subsection('Matrix equation', data=[math])

section.append(equation)

tikz = TikZ()

axis = Axis(options='height=6cm, width=6cm, grid=major')

plot1 = Plot(name='model', func='-x^5 - 242')
coordinates = [
    (-4.77778, 2027.60977),
    (-3.55556, 347.84069),
    (-2.33333, 22.58953),
    (-1.11111, -493.50066),
    (0.11111, 46.66082),
    (1.33333, -205.56286),
    (2.55556, -341.40638),
    (3.77778, -1169.24780),
    (5.00000, -3269.56775),
]

plot2 = Plot(name='estimate', coordinates=coordinates)

axis.append(plot1)
axis.append(plot2)

tikz.append(axis)

plot_section = Subsection('Random graph', data=[tikz])

section.append(plot_section)

doc.append(section)

doc.generate_pdf()

########NEW FILE########
__FILENAME__ = numpy_ex
#!/usr/bin/python

import numpy as np

from pylatex import Document, Section, Subsection, Table, Math
from pylatex.numpy import Matrix, format_vec


a = np.array([[100, 10, 20]]).T

doc = Document()
section = Section('Numpy tests')
subsection = Subsection('Array')

vec = Matrix(a)
vec_name = format_vec('a')
math = Math(data=[vec_name, '=', vec])

subsection.append(math)
section.append(subsection)

subsection = Subsection('Matrix')
M = np.matrix([[2, 3, 4],
               [0, 0, 1],
               [0, 0, 2]])
matrix = Matrix(M, mtype='b')
math = Math(data=['M=', matrix])

subsection.append(math)
section.append(subsection)


subsection = Subsection('Product')

math = Math(data=['M', vec_name, '=', Matrix(M*a)])
subsection.append(math)

section.append(subsection)

doc.append(section)
doc.generate_pdf()

########NEW FILE########
__FILENAME__ = base_classes
# -*- coding: utf-8 -*-
"""
    pylatex.base_classes
    ~~~~~~~~~~~~~~~~~~~~

    This module implements base classes with inheritable functions for other
    LaTeX classes.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from collections import UserList
from ordered_set import OrderedSet
from pylatex.utils import dumps_list


class BaseLaTeXClass:

    """A class that has some basic functions for LaTeX functions."""

    def __init__(self, packages=None):
        if packages is None:
            packages = []

        self.packages = OrderedSet(packages)

    def dumps(self):
        """Represents the class as a string in LaTeX syntax."""

    def dump(self, file_):
        """Writes the LaTeX representation of the class to a file."""
        file_.write(self.dumps())

    def dumps_packages(self):
        """Represents the packages needed as a string in LaTeX syntax."""
        return dumps_list(self.packages)

    def dump_packages(self, file_):
        """Writes the LaTeX representation of the packages to a file."""
        file_.write(self.dumps_packages())


class BaseLaTeXContainer(BaseLaTeXClass, UserList):

    """A base class that can cointain other LaTeX content."""

    def __init__(self, data=None, packages=None):
        if data is None:
            data = []

        self.data = data

        super().__init__(packages=packages)

    def dumps(self):
        """Represents the container as a string in LaTeX syntax."""
        self.propegate_packages()

    def propegate_packages(self):
        """Makes sure packages get propegated."""
        for item in self.data:
            if isinstance(item, BaseLaTeXClass):
                for p in item.packages:
                    self.packages.add(p)

    def dumps_packages(self):
        """Represents the packages needed as a string in LaTeX syntax."""
        self.propegate_packages()
        return dumps_list(self.packages)


class BaseLaTeXNamedContainer(BaseLaTeXContainer):

    """A base class for containers with one of a basic begin end syntax"""

    def __init__(self, name, data=None, packages=None, options=None):
        self.name = name
        self.options = options

        super().__init__(data=data, packages=packages)

    def dumps(self):
        """Represents the named container as a string in LaTeX syntax."""
        string = r'\begin{' + self.name + '}\n'

        if self.options is not None:
            string += '[' + self.options + ']'

        string += dumps_list(self)

        string += r'\end{' + self.name + '}\n'

        super().dumps()

        return string

########NEW FILE########
__FILENAME__ = document
# -*- coding: utf-8 -*-
"""
    pylatex.document
    ~~~~~~~

    This module implements the class that deals with the full document.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

import subprocess
from .package import Package
from .utils import dumps_list
from .base_classes import BaseLaTeXContainer


class Document(BaseLaTeXContainer):

    """A class that contains a full latex document."""

    def __init__(self, filename='default_filename', documentclass='article',
                 fontenc='T1', inputenc='utf8', author=None, title=None,
                 date=None, data=None):
        self.filename = filename

        self.documentclass = documentclass

        fontenc = Package('fontenc', option=fontenc)
        inputenc = Package('inputenc', option=inputenc)
        packages = [fontenc, inputenc, Package('lmodern')]

        if title is not None:
            packages.append(Package(title, base='title'))
        if author is not None:
            packages.append(Package(author, base='author'))
        if date is not None:
            packages.append(Package(date, base='date'))

        super().__init__(data, packages=packages)

    def dumps(self):
        """Represents the document as a string in LaTeX syntax."""
        document = r'\begin{document}'

        document += dumps_list(self)

        document += r'\end{document}'

        super().dumps()

        head = r'\documentclass{' + self.documentclass + '}'

        head += self.dumps_packages()

        return head + document

    def generate_tex(self):
        """Generates a .tex file."""
        newf = open(self.filename + '.tex', 'w')
        self.dump(newf)
        newf.close()

    def generate_pdf(self, clean=True):
        """Generates a pdf"""
        self.generate_tex()

        command = 'pdflatex --jobname="' + self.filename + '" "' + \
            self.filename + '.tex"'

        subprocess.call(command, shell=True)

        if clean:
            subprocess.call('rm "' + self.filename + '.aux" "' +
                            self.filename + '.log" "' +
                            self.filename + '.tex"', shell=True)

########NEW FILE########
__FILENAME__ = math
from .utils import dumps_list
from .base_classes import BaseLaTeXContainer


class Math(BaseLaTeXContainer):
    def __init__(self, data=None, inline=False):
        self.inline = inline
        super().__init__(data)

    def dumps(self):
        if self.inline:
            string = '$' + dumps_list(self, token=' ') + '$'
        else:
            string = '$$' + dumps_list(self, token=' ') + '$$\n'

        super().dumps()
        return string

########NEW FILE########
__FILENAME__ = numpy
# -*- coding: utf-8 -*-
"""
    pylatex.numpy
    ~~~~~~~~~~~~~

    This module implements the classes that deals with numpy objects.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

import numpy as np
from pylatex.base_classes import BaseLaTeXClass
from pylatex.package import Package


def format_vec(name):
    return r'\mathbf{' + name + '}'


class Matrix(BaseLaTeXClass):
    def __init__(self, matrix, name='', mtype='p', alignment=None):
        self.mtype = mtype
        self.matrix = matrix
        self.alignment = alignment
        self.name = name

        super().__init__(packages=[Package('amsmath')])

    def dumps(self):
        string = r'\begin{'
        mtype = self.mtype + 'matrix'

        if self.alignment is not None:
            mtype += '*'
            alignment = '{' + self.alignment + '}'
        else:
            alignment = ''

        string += mtype + '}' + alignment
        string += '\n'

        shape = self.matrix.shape

        for (y, x), value in np.ndenumerate(self.matrix):
            if x:
                string += '&'
            string += str(value)

            if x == shape[1] - 1 and y != shape[0] - 1:
                string += r'\\' + '\n'

        string += '\n'

        string += r'\end{' + mtype + '}'

        super().dumps()
        return string

########NEW FILE########
__FILENAME__ = package
# -*- coding: utf-8 -*-
"""
    pylatex.package
    ~~~~~~~

    This module implements the class that deals with packages.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from .base_classes import BaseLaTeXClass


class Package(BaseLaTeXClass):

    """A class that represents a package."""

    def __init__(self, name, base='usepackage', option=None):
        self.base = base
        self.name = name
        self.option = option

    def __key(self):
        return (self.base, self.name, self.option)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    def dumps(self):
        """Represents the package as a string in LaTeX syntax."""
        if self.option is None:
            option = ''
        else:
            option = '[' + self.option + ']'

        return '\\' + self.base + option + '{' + self.name + '}\n'

########NEW FILE########
__FILENAME__ = pgfplots
# -*- coding: utf-8 -*-
"""
    pylatex.pgfplots
    ~~~~~~~~~~~~~~~~

    This module implements the classes used to show plots.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""


from pylatex.base_classes import BaseLaTeXClass, BaseLaTeXNamedContainer
from pylatex.package import Package


class TikZ(BaseLaTeXNamedContainer):

    """Basic TikZ container class."""

    def __init__(self, data=None):
        packages = [Package('tikz')]
        super().__init__('tikzpicture', data=data, packages=packages)


class Axis(BaseLaTeXNamedContainer):

    """PGFPlots axis container class, this contains plots."""

    def __init__(self, data=None, options=None):
        packages = [Package('pgfplots'), Package('compat=newest',
                                                 base='pgfplotsset')]

        super().__init__('axis', data=data, options=options, packages=packages)


class Plot(BaseLaTeXClass):

    """PGFPlot normal plot."""

    def __init__(self, name=None, func=None, coordinates=None, options=None):
        self.name = name
        self.func = func
        self.coordinates = coordinates
        self.options = options

        packages = [Package('pgfplots'), Package('compat=newest',
                                                 base='pgfplotsset')]

        super().__init__(packages=packages)

    def dumps(self):
        """Represents the plot as a string in LaTeX syntax."""
        string = r'\addplot'

        if self.options is not None:
            string += '[' + self.options + ']'

        if self.coordinates is not None:
            string += ' coordinates {\n'

            for c in self.coordinates:
                string += '(' + str(c[0]) + ',' + str(c[1]) + ')\n'
            string += '};\n\n'

        elif self.func is not None:
            string += '{' + self.func + '};\n\n'

        if self.name is not None:
            string += r'\addlegendentry{' + self.name + '}\n'

        super().dumps()

        return string

########NEW FILE########
__FILENAME__ = section
# -*- coding: utf-8 -*-
"""
    pylatex.section
    ~~~~~~~

    This module implements the class that deals with sections.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from .utils import dumps_list
from .base_classes import BaseLaTeXContainer


class SectionBase(BaseLaTeXContainer):

    """A class that is the base for all section type classes"""

    def __init__(self, title, numbering=True, data=None):
        self.title = title
        self.numbering = numbering

        super().__init__(data)

    def dumps(self):
        """Represents the section as a string in LaTeX syntax."""

        if not self.numbering:
            num = '*'
        else:
            num = ''

        base = '\\' + self.__class__.__name__.lower() + num
        string = base + '{' + self.title + '}\n' + dumps_list(self)

        super().dumps()
        return string


class Section(SectionBase):

    """A class that represents a section."""


class Subsection(SectionBase):

    """A class that represents a subsection."""


class Subsubsection(SectionBase):

    """A class that represents a subsubsection."""

########NEW FILE########
__FILENAME__ = table
# -*- coding: utf-8 -*-
"""
    pylatex.table
    ~~~~~~~

    This module implements the class that deals with tables.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

from .utils import dumps_list
from .base_classes import BaseLaTeXContainer
from .package import Package

from collections import Counter
import re


def get_table_width(table_spec):
    column_letters = ['l', 'c', 'r', 'p', 'm', 'b']

    # Remove things like {\bfseries}
    cleaner_spec = re.sub(r'{[^}]*}', '', table_spec)
    spec_counter = Counter(cleaner_spec)

    return sum(spec_counter[l] for l in column_letters)


class Table(BaseLaTeXContainer):

    """A class that represents a table."""

    def __init__(self, table_spec, data=None, pos=None, packages=None):
        self.table_type = 'tabular'
        self.table_spec = table_spec
        self.pos = pos

        self.width = get_table_width(table_spec)

        super().__init__(data=data, packages=packages)

    def add_hline(self, start=None, end=None):
        """Add a horizontal line to the table"""
        if start is None and end is None:
            self.append(r'\hline')
        else:
            if start is None:
                start = 1
            elif end is None:
                end = self.width
            self.append(r'\cline{' + str(start) + '-' + str(end) + '}')

    def add_empty_row(self):
        """Add an empty row to the table"""
        self.append((self.width - 1) * '&' + r'\\')

    def add_row(self, cells, escape=False):
        """Add a row of cells to the table"""
        self.append(dumps_list(cells, escape=escape, token='&') + r'\\')

    def add_multicolumn(self, size, align, content, cells=None, escape=False):
        """
        Add a multicolumn of width size to the table, with cell content content
        """
        self.append(r'\multicolumn{%d}{%s}{%s}' % (size, align, content))
        if cells is not None:
            self.add_row(cells)
        else:
            self.append(r'\\')

    def add_multirow(self, size, align, content, hlines=True, cells=None,
                     escape=False):
        """
        Add a multirow of height size to the table, with cell content content
        """
        self.append(r'\multirow{%d}{%s}{%s}' % (size, align, content))
        self.packages.add(Package('multirow'))
        if cells is not None:
            for i, row in enumerate(cells):
                if hlines and i:
                    self.add_hline(2)
                self.append('&')
                self.add_row(row)
        else:
            for i in range(size):
                self.add_empty_row()

    def dumps(self):
        """Represents the document as a string in LaTeX syntax."""
        string = r'\begin{' + self.table_type + '}'

        if self.pos is not None:
            string += '[' + self.pos + ']'

        string += '{' + self.table_spec + '}\n'

        string += dumps_list(self)

        string += r'\end{' + self.table_type + '}'

        super().dumps()
        return string


class Tabu(Table):

    """A class that represents a tabu (more flexible table)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, packages=[Package('tabu')], **kwargs)
        self.table_type = 'tabu'


class LongTable(Table):

    """A class that represents a longtable (multipage table)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, packages=[Package('longtable')], **kwargs)
        self.table_type = 'longtable'


class LongTabu(Table):

    """A class that represents a longtabu (more flexible multipage table)"""

    def __init__(self, *args, **kwargs):
        packages = [Package('tabu'), Package('longtable')]
        super().__init__(*args, packages=packages, **kwargs)
        self.table_type = 'longtabu'

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
    pylatex.utils
    ~~~~~~~

    This module implements some simple functions with all kinds of
    functionality.

    :copyright: (c) 2014 by Jelte Fennema.
    :license: MIT, see License for more details.
"""

_latex_special_chars = {
    '&':  r'\&',
    '%':  r'\%',
    '$':  r'\$',
    '#':  r'\#',
    '_':  r'\_',
    '{':  r'\{',
    '}':  r'\}',
    '~':  r'\lettertilde{}',
    '^':  r'\letterhat{}',
    '\\': r'\letterbackslash{}',
    '\n': r'\\\\',
}


def escape_latex(s):
    """Escape characters that are special in latex.

    Sources:
        * http://tex.stackexchange.com/a/34586/43228
        * http://stackoverflow.com/a/16264094/2570866
    """
    return ''.join(_latex_special_chars.get(c, c) for c in s)


def dumps_list(l, escape=False, token='\n'):
    """Dumps a list that can contain anything"""
    return token.join(_latex_item_to_string(i, escape) for i in l)


def _latex_item_to_string(i, escape=False):
    """Use the render method when possible, otherwise use str."""
    if hasattr(i, 'dumps'):
        return i.dumps()
    elif escape:
        return str(escape_latex(i))
    return str(i)


def bold(s):
    """Returns the string bold.

    Source: http://stackoverflow.com/a/16264094/2570866
    """
    return r'\textbf{' + s + '}'


def italic(s):
    """Returns the string italicized.

    Source: http://stackoverflow.com/a/16264094/2570866
    """
    return r'\textit{' + s + '}'

########NEW FILE########
__FILENAME__ = multirow_test
#!/usr/bin/python

from pylatex import Document, Section, Subsection, Table

doc = Document(filename="multirow")
section = Section('Multirow Test')

test1 = Subsection('Multicol')
test2 = Subsection('Multirow')

table1 = Table('|c|c|')
table1.add_hline()
table1.add_multicolumn(2, '|c|', 'Multicol')
table1.add_hline()
table1.add_row((1, 2))
table1.add_hline()
table1.add_row((3, 4))
table1.add_hline()

table2 = Table('|c|c|c|')
table2.add_hline()
table2.add_multirow(3, '*', 'Multirow', cells=((1, 2), (3, 4), (5, 6)))
table2.add_hline()
table2.add_multirow(3, '*', 'Multirow2')
table2.add_hline()

test1.append(table1)
test2.append(table2)

section.append(test1)
section.append(test2)

doc.append(section)
doc.generate_pdf()

########NEW FILE########
