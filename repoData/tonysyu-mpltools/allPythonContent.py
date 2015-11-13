__FILENAME__ = plot_decaying_oscillation
#PLOT2RST: auto_plots = False
"""
====================
Decaying oscillation
====================

The animation module provides an ``Animation`` class to clean up the creation
of animated plots. This class is built on top of matplotlib's `animation
subpackage`_, which was introduced in matplotlib v.1.1.

.. _animation subpackage:
    http://matplotlib.sourceforge.net/examples/animation/index.html#animation-examples-index

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools.animation import Animation


class DecayingOscillation(Animation):

    def __init__(self, L=2*np.pi, npts=100, num_periods=5, decay_rate=0.1):
        self.fig, self.ax = plt.subplots(figsize=(4, 4))
        self.x = np.linspace(0, L, npts)
        self.num_periods = num_periods
        self.decay_rate = decay_rate
        # Note: If `num_frames` not defined, # of saved frames defaults to 100.
        self.num_frames = 500

    def update(self):
        self.line, = self.ax.plot(self.x, np.sin(self.x))
        tmax = self.num_periods * 2*np.pi
        for t in np.linspace(0, tmax, self.num_frames):
            amplitude = np.exp(-t * self.decay_rate) * np.cos(t)
            self.line.set_ydata(amplitude * np.sin(self.x))
            # must return list of artists if you want to use blit
            yield self.line,


osc = DecayingOscillation()
osc.animate(blit=True)

# Note: `save` and `show` don't play nice together. Use one at a time.
#osc.save('decaying_oscillation.avi', fps=30, bitrate=200)
plt.show()

"""
.. raw:: html

   <video controls="controls">
       <source src="../../_static/decaying_oscillation.webm"
               type="video/webm" />
       Video display requires video tag and webm support.
   </video>

"""

########NEW FILE########
__FILENAME__ = plot_slope_marker
"""
============
Slope marker
============

When viewing data, it's often helpful to add a marker representing the
predicted or measured slope. ``mpltools.annotation.slope_marker`` provides
a simple way of adding a slope marker by specifying the origin of the marker
(normally, the left-most corner of the marker, but, when ``invert=True``, it's
the right-most corner) and the slope---either as a float value or a (rise, run)
tuple.
"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import annotation


x = np.logspace(0, 2)
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)

ax1.plot([0, 2], [1, 0])
annotation.slope_marker((1, 0.6), (-1, 2), ax=ax1)
ax1.set_title('linear, negative slope')

ax2.loglog(x, x**0.5)
annotation.slope_marker((10, 2), (1, 2), ax=ax2,
                        text_kwargs={'color': 'cornflowerblue'},
                        poly_kwargs={'facecolor': (0.73, 0.8, 1)})
ax2.set_title('loglog, custom colors')

ax3.loglog(x, x**0.5)
annotation.slope_marker((10, 4), (1, 2), invert=True, ax=ax3)
ax3.set_title('loglog, `invert=True`')

ax4.loglog(x, x**0.5)
annotation.slope_marker((10, 2), 0.5, ax=ax4)
ax4.set_title('loglog, float slope')

plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_color_mapper
"""
==========================
Color from parameter value
==========================

Suppose you want to plot a series of curves, and each curve describes
a response to different values of a parameter. ``color_mapper`` returns
a function that maps a parameter value to an RGBA color in a color map.

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import layout
from mpltools import color


pvalues = np.logspace(-1, 0, 4)
parameter_range = (pvalues[0], pvalues[-1])
# Pass parameter range so that color mapper knows how to normalize the data.
map_color1 = color.color_mapper(parameter_range)
map_color2 = color.color_mapper(parameter_range, cmap='BuPu', start=0.2)

figsize = layout.figaspect(aspect_ratio=0.5)
fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=figsize)
x = np.linspace(0, 10)
for pval in pvalues:
    y = np.sin(x) * np.exp(-pval * x)
    ax1.plot(x, y, 's', color=map_color1(pval))
    ax2.plot(x, y, lw=3, color=map_color2(pval))

for ax in (ax1, ax2):
    leg = ax.legend(['%0.1f' % v for v in pvalues], loc='lower right', ncol=2)
    leg.set_title('decay rate')
    ax.set_ylim(-1.5, 1)

plt.show()


########NEW FILE########
__FILENAME__ = plot_cycle_cmap
"""
===========================
Color cycle from a colormap
===========================

``cycle_cmap`` provides a simple way to set the color cycle to evenly-spaced
intervals of a given colormap. By default, it alters the default color cycle,
but if you pass it a plot axes, only the color cycle for the axes is altered.

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import layout
from mpltools import color


n_lines = 10

# Change default color cycle for all new axes
color.cycle_cmap(n_lines)

figsize = layout.figaspect(aspect_ratio=0.5)
fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=figsize)

# Change color cycle specifically for `ax2`
color.cycle_cmap(n_lines, cmap='pink', ax=ax2)

x = np.linspace(0, 10)
for shift in np.linspace(0, np.pi, n_lines):
    ax1.plot(x, np.sin(x - shift), linewidth=2)
    ax2.plot(x, np.sin(x - shift), linewidth=2)

plt.show()


########NEW FILE########
__FILENAME__ = plot_linear_colormap
"""
==============
LinearColormap
==============

This class simplifies the creation of Matplotlib colormaps. To specify
a colormap, you can just specify key colors in the colormap, and
``LinearColormap`` will distribute those colors evenly in the colormap and
linearly interpolate in-between. In the example below, specifying two colors
defines the minimum and maximum color values of the colormap.
"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import color


x, y, z = np.random.uniform(size=(3, 100))

white_red = color.LinearColormap('white_red', [(1, 1, 1), (0.8, 0, 0)])
plt.scatter(x, y, c=z, cmap=white_red, s=200)

"""
.. image:: PLOT2RST.current_figure

To get more complicated, use the ``index`` argument to specify where the color
values map to in the colormap. Here, we repeat an index to get a segmented
colormap. This colormap is uniformly blue below the midpoint and red above the
midpoint. Alpha values are maximum at the edges and minimum in the middle.
"""

bcr_rgba = [(0.02, 0.2, 0.4, 1),    # grayish blue, opaque
            (0.02, 0.2, 0.4, 0.3),  # grayish blue, transparent
            (0.4,  0.0, 0.1, 0.3),  # dark red, transparent
            (0.4,  0.0, 0.1, 1)]    # dark red, opaque
blue_clear_red = color.LinearColormap('blue_clear_red', bcr_rgba,
                                      index=[0, 0.5, 0.5, 1])


plt.figure()
plt.scatter(x, y, c=z, cmap=blue_clear_red, s=200, edgecolors='none')

"""
.. image:: PLOT2RST.current_figure
"""
plt.show()

########NEW FILE########
__FILENAME__ = plot_cross_spines
"""
==============
Crossed spines
==============

By default, matplotlib surrounds plot axes with borders. ``cross_spines` uses
the axes ``spines`` (the names ``axes`` and ``axis`` were already taken)
attribute to eliminate the top and right spines from the plot.

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import layout


figsize = layout.figaspect(aspect_ratio=0.5)
fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=figsize)

x, y = np.random.normal(size=(2, 20))

layout.cross_spines(ax=ax1)
ax1.plot(x, y, 'ro')

layout.cross_spines(zero_cross=True, ax=ax2)
ax2.plot(x, y, 'ro')

plt.show()

########NEW FILE########
__FILENAME__ = plot_figaspect
"""
============
Figure shape
============

Often, you want to adjust the shape (or aspect ratio) of a figure, but you
don't want to explicitly calculate its size. Matplotlib provides a function
called ``figaspect`` to fill this role. To adjust the aspect ratio of the
figure, ``plt.figaspect`` will change the *width* of the figure.  In contrast,
``layout.figaspect`` will change the *height* of the figure.  This behavior is
convenient if you have a fixed-width requirement (e.g., the width of columns in
a journal page or the width of a web page).

In this example, ``layout.figaspect`` creates a figure that fits comfortably
onto the page, while ``plt.figaspect`` does not.

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import layout


x, y = np.random.normal(size=(2, 20))

aspect_functions = {'mpltools.layout.figaspect': layout.figaspect,
                    'matplotlib.pyplot.figaspect': plt.figaspect}

for label, figaspect in aspect_functions.items():
    figsize = figaspect(0.5)
    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(x, y, 'ro')
    ax.set_title(label)

plt.show()

########NEW FILE########
__FILENAME__ = plot_errorfill
"""
================
Plot `errorfill`
================

When you have continuous data measurement and errors associated with every data point, plotting error bars can get really noisy. `special.errorfill` plots a filled region to represent the error values instead of using individual bars.
"""

import numpy as np
import matplotlib.pyplot as plt

from mpltools import special

x = np.linspace(0, 2 * np.pi)
y_sin = np.sin(x)
y_cos = np.cos(x)

y_err = 0.2
special.errorfill(x, y_sin, y_err, label='sin', label_fill='sin error')
special.errorfill(x, y_cos, y_err, label='cos', label_fill='cos error',
                  alpha_fill=0.1)
plt.legend()

plt.show()


########NEW FILE########
__FILENAME__ = plot_hinton
"""
==============
Hinton diagram
==============

Hinton diagrams are useful for visualizing the values of a 2D array: Positive
and negative values are represented by white and black squares, respectively,
and the size of each square represents the magnitude of each value.

``special.hinton`` is based off of the `Hinton demo`_ in the matplotlib gallery. This implementation, however, uses a ``RegularPolyCollection`` to draw
squares, which is much more efficient than drawing individual rectangles.

Obscure example use: For my Ph.D., I wrote a numerical solver using
finite-differences. For speed, the Jacobian matrices were calculated
analytically, which was incredibly-prone to bugs. To debug my code,
I calculated the numerical Jacobian (calculated using
``scipy.optimize.slsqp.approx_jacobian``) and plotted the Hinton diagram for
the difference of the numerical and analytical results. That allowed me to
narrow down where the bugs were (boundary conditions!) instead of blindly
checking every equation. You could, of course, use ``pcolor`` or ``imshow`` in
a similar situation.

.. _Hinton demo: http://matplotlib.sourceforge.net/examples/api/hinton_demo.html

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import special


A = np.random.uniform(-1, 1, size=(20, 20))
special.hinton(A)
plt.show()

########NEW FILE########
__FILENAME__ = plot_plot2rst
#!/usr/bin/env python
"""
====================
`plot2rst` extension
====================

`plot2rst` is a sphinx extension that converts a normal python file into
reStructuredText. All strings in the python file are converted into regular
reStructuredText, while all python code is converted into code blocks.

This extension is named `plot2rst` because the conversion also intelligently
handles plots. In particular, you can write a block of code that creates
a plot, and then follow that up with a discussion that has the plot added
inline. To do so, you just need to add a call to the Sphinx image directive and
set the image link to a special tag::

    .. image:: PLOT2RST. current_figure

**Note** that there shouldn't be a space after the period in a real call---it's
added here to prevent `plot2rst` from replacing the tag with an image path.

All the code that runs before this call will be executed, the current figure
will be saved, and the tag will be replaced with the path to that figure.

So here's a line plot:
"""
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 2*np.pi)
plt.plot(x, np.sin(x))

"""
This plot can be displayed inline with a call the ``current_figure`` tag:

.. image:: PLOT2RST.current_figure


And here's a second plot in a *new figure*:
"""

plt.figure()
plt.imshow(np.random.random(size=(20, 20)))

"""
which gets displayed as:

.. image:: PLOT2RST.current_figure

You can also add to plots created in previous code blocks:
"""
x = np.linspace(0, 19)
plt.plot(x, 5 * np.sin(x) + 10, alpha=0.5, lw=5)
plt.margins(0)

"""
.. image:: PLOT2RST.current_figure

There's some subtle differences between strings and comments which I'll
demonstrate below. (Some of this only makes sense if you look at the raw python
file.)

# Comments in text blocks remain nested in the text.

"""

def dummy():
    """Dummy function to make sure docstrings don't get rendered as text"""
    pass

# Code comments are not strings and are left in code blocks.

"Any string that's not saved to a variable is converted to text"

string = """
Triple-quoted string which tries to break parser but doesn't.
"""

"""
Finally, I'll call ``show`` at the end just so someone running the python code
directly will see the plots; this is not necessary for creating the docs.
"""
plt.show()


########NEW FILE########
__FILENAME__ = plot_dark_background
"""
================
Dark backgrounds
================

A key feature of ``mpltools`` is the ability to set "styles"---essentially,
stylesheets that are similar to matplotlibrc files. This example demonstrates
the "dark_background" style, which uses white for elements that are typically
black (text, borders, etc). Note, however, that not all plot elements default
to colors defined by an rc parameter.

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import style
style.use('dark_background')


L = 6
x = np.linspace(0, L)
ncolors = len(plt.rcParams['axes.color_cycle'])
shift = np.linspace(0, L, ncolors, endpoint=False)
for s in shift:
    plt.plot(x, np.sin(x + s), 'o-')
plt.xlabel('x-axis')
plt.ylabel('y-axis')
plt.title('title')

plt.show()

########NEW FILE########
__FILENAME__ = plot_ggplot
"""
================
``ggplot`` style
================

A key feature of ``mpltools`` is the ability to set "styles"---essentially,
stylesheets that are similar to matplotlibrc files. This example demonstrates
the "ggplot" style, which adjusts the style to emulate ggplot_ (a popular
plotting package for R_).

These settings were shamelessly stolen from [1]_.

.. [1] http://www.huyng.com/posts/sane-color-scheme-for-matplotlib/

.. _ggplot: http://had.co.nz/ggplot/
.. _R: http://www.r-project.org/

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import style
from mpltools import layout

style.use('ggplot')

figsize = layout.figaspect(scale=1.2)
fig, axes = plt.subplots(ncols=2, nrows=2, figsize=figsize)
ax1, ax2, ax3, ax4 = axes.ravel()

# scatter plot (Note: `plt.scatter` doesn't use default colors)
x, y = np.random.normal(size=(2, 200))
ax1.plot(x, y, 'o')

# sinusoidal lines with colors from default color cycle
L = 2*np.pi
x = np.linspace(0, L)
ncolors = len(plt.rcParams['axes.color_cycle'])
shift = np.linspace(0, L, ncolors, endpoint=False)
for s in shift:
    ax2.plot(x, np.sin(x + s), '-')
ax2.margins(0)

# bar graphs
x = np.arange(5)
y1, y2 = np.random.randint(1, 25, size=(2, 5))
width = 0.25
ax3.bar(x, y1, width)
ax3.bar(x+width, y2, width, color=plt.rcParams['axes.color_cycle'][2])
ax3.set_xticks(x+width)
ax3.set_xticklabels(['a', 'b', 'c', 'd', 'e'])

# circles with colors from default color cycle
for i, color in enumerate(plt.rcParams['axes.color_cycle']):
    xy = np.random.normal(size=2)
    ax4.add_patch(plt.Circle(xy, radius=0.3, color=color))
ax4.axis('equal')
ax4.margins(0)

# Remove ticks on top and right sides of plot
for ax in axes.ravel():
    layout.cross_spines(ax=ax)

plt.show()

########NEW FILE########
__FILENAME__ = plot_grayscale
"""
===============
Grayscale plots
===============

A key feature of ``mpltools`` is the ability to set "styles"---essentially,
stylesheets that are similar to matplotlibrc files. This example demonstrates
the "grayscale" style, which changes all colors that are defined as rc
parameters to grayscale. Note, however, that not all plot elements default to
colors defined by an rc parameter.

"""
import numpy as np
import matplotlib.pyplot as plt

from mpltools import style
from mpltools import layout


def color_cycle_example(ax):
    L = 6
    x = np.linspace(0, L)
    ncolors = len(plt.rcParams['axes.color_cycle'])
    shift = np.linspace(0, L, ncolors, endpoint=False)
    for s in shift:
        ax.plot(x, np.sin(x + s), 'o-')

def image_and_patch_example(ax):
    ax.imshow(np.random.random(size=(20, 20)), interpolation='none')
    c = plt.Circle((5, 5), radius=5, label='patch')
    ax.add_patch(c)


style.use('grayscale')

figsize = layout.figaspect(0.5)
fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=figsize)

color_cycle_example(ax1)
image_and_patch_example(ax2)

plt.show()

########NEW FILE########
__FILENAME__ = plot_multiple_styles
"""
===============
Multiple styles
===============

You can specify multiple plot styles by passing a list of style names to
`style.use`. The styles are evaluated from the first to last element of the
list, so if there are settings that are defined in multiple styles, the
settings in the later style files will override those in the earlier files.

In this example, the 'ggplot' style alters the colors of elements to make the plot pretty, and the 'pof' style (Physics of Fluids journal) alters the figure size so that it fits in a column, alters line and text sizes, etc.
"""

import numpy as np
import matplotlib.pyplot as plt

from mpltools import style

style.use(['ggplot', 'pof'])

x = np.linspace(0, 2 * np.pi)
plt.plot(x, np.cos(x))
plt.xlabel('x label')
plt.ylabel('y label')
plt.title('title')

plt.show()

########NEW FILE########
__FILENAME__ = docscrape
"""Extract reference documentation from the NumPy source tree.

"""

import inspect
import textwrap
import re
import pydoc
from StringIO import StringIO
from warnings import warn

class Reader(object):
    """A line-based string reader.

    """
    def __init__(self, data):
        """
        Parameters
        ----------
        data : str
           String with lines separated by '\n'.

        """
        if isinstance(data,list):
            self._str = data
        else:
            self._str = data.split('\n') # store string as list of lines

        self.reset()

    def __getitem__(self, n):
        return self._str[n]

    def reset(self):
        self._l = 0 # current line nr

    def read(self):
        if not self.eof():
            out = self[self._l]
            self._l += 1
            return out
        else:
            return ''

    def seek_next_non_empty_line(self):
        for l in self[self._l:]:
            if l.strip():
                break
            else:
                self._l += 1

    def eof(self):
        return self._l >= len(self._str)

    def read_to_condition(self, condition_func):
        start = self._l
        for line in self[start:]:
            if condition_func(line):
                return self[start:self._l]
            self._l += 1
            if self.eof():
                return self[start:self._l+1]
        return []

    def read_to_next_empty_line(self):
        self.seek_next_non_empty_line()
        def is_empty(line):
            return not line.strip()
        return self.read_to_condition(is_empty)

    def read_to_next_unindented_line(self):
        def is_unindented(line):
            return (line.strip() and (len(line.lstrip()) == len(line)))
        return self.read_to_condition(is_unindented)

    def peek(self,n=0):
        if self._l + n < len(self._str):
            return self[self._l + n]
        else:
            return ''

    def is_empty(self):
        return not ''.join(self._str).strip()


class NumpyDocString(object):
    def __init__(self, docstring, config={}):
        docstring = textwrap.dedent(docstring).split('\n')

        self._doc = Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': [''],
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'Other Parameters': [],
            'Attributes': [],
            'Methods': [],
            'See Also': [],
            'Notes': [],
            'Warnings': [],
            'References': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def __getitem__(self,key):
        return self._parsed_data[key]

    def __setitem__(self,key,val):
        if not self._parsed_data.has_key(key):
            warn("Unknown section %s" % key)
        else:
            self._parsed_data[key] = val

    def _is_at_section(self):
        self._doc.seek_next_non_empty_line()

        if self._doc.eof():
            return False

        l1 = self._doc.peek().strip()  # e.g. Parameters

        if l1.startswith('.. index::'):
            return True

        l2 = self._doc.peek(1).strip() #    ---------- or ==========
        return l2.startswith('-'*len(l1)) or l2.startswith('='*len(l1))

    def _strip(self,doc):
        i = 0
        j = 0
        for i,line in enumerate(doc):
            if line.strip(): break

        for j,line in enumerate(doc[::-1]):
            if line.strip(): break

        return doc[i:len(doc)-j]

    def _read_to_next_section(self):
        section = self._doc.read_to_next_empty_line()

        while not self._is_at_section() and not self._doc.eof():
            if not self._doc.peek(-1).strip(): # previous line was empty
                section += ['']

            section += self._doc.read_to_next_empty_line()

        return section

    def _read_sections(self):
        while not self._doc.eof():
            data = self._read_to_next_section()
            name = data[0].strip()

            if name.startswith('..'): # index section
                yield name, data[1:]
            elif len(data) < 2:
                yield StopIteration
            else:
                yield name, self._strip(data[2:])

    def _parse_param_list(self,content):
        r = Reader(content)
        params = []
        while not r.eof():
            header = r.read().strip()
            if ' : ' in header:
                arg_name, arg_type = header.split(' : ')[:2]
            else:
                arg_name, arg_type = header, ''

            desc = r.read_to_next_unindented_line()
            desc = dedent_lines(desc)

            params.append((arg_name,arg_type,desc))

        return params


    _name_rgx = re.compile(r"^\s*(:(?P<role>\w+):`(?P<name>[a-zA-Z0-9_.-]+)`|"
                           r" (?P<name2>[a-zA-Z0-9_.-]+))\s*", re.X)
    def _parse_see_also(self, content):
        """
        func_name : Descriptive text
            continued text
        another_func_name : Descriptive text
        func_name1, func_name2, :meth:`func_name`, func_name3

        """
        items = []

        def parse_item_name(text):
            """Match ':role:`name`' or 'name'"""
            print text
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None
                else:
                    return g[2], g[1]
            raise ValueError("%s is not a item name" % text)

        def push_item(name, rest):
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        current_func = None
        rest = []

        for line in content:
            if not line.strip(): continue

            m = self._name_rgx.match(line)
            if m and line[m.end():].strip().startswith(':'):
                push_item(current_func, rest)
                current_func, line = line[:m.end()], line[m.end():]
                rest = [line.split(':', 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(' '):
                push_item(current_func, rest)
                current_func = None
                if ',' in line:
                    for func in line.split(','):
                        push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)
        return items

    def _parse_index(self, section, content):
        """
        .. index: default
           :refguide: something, else, and more

        """
        def strip_each_in(lst):
            return [s.strip() for s in lst]

        out = {}
        section = section.split('::')
        if len(section) > 1:
            out['default'] = strip_each_in(section[1].split(','))[0]
        for line in content:
            line = line.split(':')
            if len(line) > 2:
                out[line[1]] = strip_each_in(line[2].split(','))
        return out

    def _parse_summary(self):
        """Grab signature (if given) and summary"""
        if self._is_at_section():
            return

        summary = self._doc.read_to_next_empty_line()
        summary_str = " ".join([s.strip() for s in summary]).strip()
        if re.compile('^([\w., ]+=)?\s*[\w\.]+\(.*\)$').match(summary_str):
            self['Signature'] = summary_str
            if not self._is_at_section():
                self['Summary'] = self._doc.read_to_next_empty_line()
        else:
            self['Summary'] = summary

        if not self._is_at_section():
            self['Extended Summary'] = self._read_to_next_section()

    def _parse(self):
        self._doc.reset()
        self._parse_summary()

        for (section,content) in self._read_sections():
            if not section.startswith('..'):
                section = ' '.join([s.capitalize() for s in section.split(' ')])
            if section in ('Parameters', 'Attributes', 'Methods',
                           'Returns', 'Raises', 'Warns'):
                self[section] = self._parse_param_list(content)
            elif section.startswith('.. index::'):
                self['index'] = self._parse_index(section, content)
            elif section == 'See Also':
                self['See Also'] = self._parse_see_also(content)
            else:
                self[section] = content

    # string conversion routines

    def _str_header(self, name, symbol='-'):
        return [name, len(name)*symbol]

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        if self['Signature']:
            return [self['Signature'].replace('*','\*')] + ['']
        else:
            return ['']

    def _str_summary(self):
        if self['Summary']:
            return self['Summary'] + ['']
        else:
            return []

    def _str_extended_summary(self):
        if self['Extended Summary']:
            return self['Extended Summary'] + ['']
        else:
            return []

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            for param,param_type,desc in self[name]:
                out += ['%s : %s' % (param, param_type)]
                out += self._str_indent(desc)
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += self[name]
            out += ['']
        return out

    def _str_see_also(self, func_role):
        if not self['See Also']: return []
        out = []
        out += self._str_header("See Also")
        last_had_desc = True
        for func, desc, role in self['See Also']:
            if role:
                link = ':%s:`%s`' % (role, func)
            elif func_role:
                link = ':%s:`%s`' % (func_role, func)
            else:
                link = "`%s`_" % func
            if desc or last_had_desc:
                out += ['']
                out += [link]
            else:
                out[-1] += ", %s" % link
            if desc:
                out += self._str_indent([' '.join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        out += ['']
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            out += ['   :%s: %s' % (section, ', '.join(references))]
        return out

    def __str__(self, func_role=''):
        out = []
        out += self._str_signature()
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters','Returns','Raises'):
            out += self._str_param_list(param_list)
        out += self._str_section('Warnings')
        out += self._str_see_also(func_role)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
        for param_list in ('Attributes', 'Methods'):
            out += self._str_param_list(param_list)
        out += self._str_index()
        return '\n'.join(out)


def indent(str,indent=4):
    indent_str = ' '*indent
    if str is None:
        return indent_str
    lines = str.split('\n')
    return '\n'.join(indent_str + l for l in lines)

def dedent_lines(lines):
    """Deindent a list of lines maximally"""
    return textwrap.dedent("\n".join(lines)).split("\n")

def header(text, style='-'):
    return text + '\n' + style*len(text) + '\n'


class FunctionDoc(NumpyDocString):
    def __init__(self, func, role='func', doc=None, config={}):
        self._f = func
        self._role = role # e.g. "func" or "meth"

        if doc is None:
            if func is None:
                raise ValueError("No function or docstring given")
            doc = inspect.getdoc(func) or ''
        NumpyDocString.__init__(self, doc)

        if not self['Signature'] and func is not None:
            func, func_name = self.get_func()
            try:
                # try to read signature
                argspec = inspect.getargspec(func)
                argspec = inspect.formatargspec(*argspec)
                argspec = argspec.replace('*','\*')
                signature = '%s%s' % (func_name, argspec)
            except TypeError, e:
                signature = '%s()' % func_name
            self['Signature'] = signature

    def get_func(self):
        func_name = getattr(self._f, '__name__', self.__class__.__name__)
        if inspect.isclass(self._f):
            func = getattr(self._f, '__call__', self._f.__init__)
        else:
            func = self._f
        return func, func_name

    def __str__(self):
        out = ''

        func, func_name = self.get_func()
        signature = self['Signature'].replace('*', '\*')

        roles = {'func': 'function',
                 'meth': 'method'}

        if self._role:
            if not roles.has_key(self._role):
                print "Warning: invalid role %s" % self._role
            out += '.. %s:: %s\n    \n\n' % (roles.get(self._role,''),
                                             func_name)

        out += super(FunctionDoc, self).__str__(func_role=self._role)
        return out


class ClassDoc(NumpyDocString):
    def __init__(self, cls, doc=None, modulename='', func_doc=FunctionDoc,
                 config={}):
        if not inspect.isclass(cls) and cls is not None:
            raise ValueError("Expected a class or None, but got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename

        if doc is None:
            if cls is None:
                raise ValueError("No class or documentation string given")
            doc = pydoc.getdoc(cls)

        NumpyDocString.__init__(self, doc)

        if config.get('show_class_members', True):
            if not self['Methods']:
                self['Methods'] = [(name, '', '')
                                   for name in sorted(self.methods)]
            if not self['Attributes']:
                self['Attributes'] = [(name, '', '')
                                      for name in sorted(self.properties)]

    @property
    def methods(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and callable(func)]

    @property
    def properties(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and func is None]

########NEW FILE########
__FILENAME__ = docscrape_sphinx
import re, inspect, textwrap, pydoc
import sphinx
from docscrape import NumpyDocString, FunctionDoc, ClassDoc

class SphinxDocString(NumpyDocString):
    def __init__(self, docstring, config={}):
        self.use_plots = config.get('use_plots', False)
        NumpyDocString.__init__(self, docstring, config=config)

    # string conversion routines
    def _str_header(self, name, symbol='`'):
        return ['.. rubric:: ' + name, '']

    def _str_field_list(self, name):
        return [':' + name + ':']

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        return ['']
        if self['Signature']:
            return ['``%s``' % self['Signature']] + ['']
        else:
            return ['']

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Extended Summary'] + ['']

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_field_list(name)
            out += ['']
            for param,param_type,desc in self[name]:
                out += self._str_indent(['**%s** : %s' % (param.strip(),
                                                          param_type)])
                out += ['']
                out += self._str_indent(desc,8)
                out += ['']
        return out

    @property
    def _obj(self):
        if hasattr(self, '_cls'):
            return self._cls
        elif hasattr(self, '_f'):
            return self._f
        return None

    def _str_member_list(self, name):
        """
        Generate a member listing, autosummary:: table where possible,
        and a table where not.

        """
        out = []
        if self[name]:
            out += ['.. rubric:: %s' % name, '']
            prefix = getattr(self, '_name', '')

            if prefix:
                prefix = '~%s.' % prefix

            autosum = []
            others = []
            for param, param_type, desc in self[name]:
                param = param.strip()
                if not self._obj or hasattr(self._obj, param):
                    autosum += ["   %s%s" % (prefix, param)]
                else:
                    others.append((param, param_type, desc))

            if autosum:
                out += ['.. autosummary::', '   :toctree:', '']
                out += autosum

            if others:
                maxlen_0 = max([len(x[0]) for x in others])
                maxlen_1 = max([len(x[1]) for x in others])
                hdr = "="*maxlen_0 + "  " + "="*maxlen_1 + "  " + "="*10
                fmt = '%%%ds  %%%ds  ' % (maxlen_0, maxlen_1)
                n_indent = maxlen_0 + maxlen_1 + 4
                out += [hdr]
                for param, param_type, desc in others:
                    out += [fmt % (param.strip(), param_type)]
                    out += self._str_indent(desc, n_indent)
                out += [hdr]
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += ['']
            content = textwrap.dedent("\n".join(self[name])).split("\n")
            out += content
            out += ['']
        return out

    def _str_see_also(self, func_role):
        out = []
        if self['See Also']:
            see_also = super(SphinxDocString, self)._str_see_also(func_role)
            out = ['.. seealso::', '']
            out += self._str_indent(see_also[2:])
        return out

    def _str_warnings(self):
        out = []
        if self['Warnings']:
            out = ['.. warning::', '']
            out += self._str_indent(self['Warnings'])
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        if len(idx) == 0:
            return out

        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            elif section == 'refguide':
                out += ['   single: %s' % (', '.join(references))]
            else:
                out += ['   %s: %s' % (section, ','.join(references))]
        return out

    def _str_references(self):
        out = []
        if self['References']:
            out += self._str_header('References')
            if isinstance(self['References'], str):
                self['References'] = [self['References']]
            out.extend(self['References'])
            out += ['']
            # Latex collects all references to a separate bibliography,
            # so we need to insert links to it
            if sphinx.__version__ >= "0.6":
                out += ['.. only:: latex','']
            else:
                out += ['.. latexonly::','']
            items = []
            for line in self['References']:
                m = re.match(r'.. \[([a-z0-9._-]+)\]', line, re.I)
                if m:
                    items.append(m.group(1))
            out += ['   ' + ", ".join(["[%s]_" % item for item in items]), '']
        return out

    def _str_examples(self):
        examples_str = "\n".join(self['Examples'])

        if (self.use_plots and 'import matplotlib' in examples_str
                and 'plot::' not in examples_str):
            out = []
            out += self._str_header('Examples')
            out += ['.. plot::', '']
            out += self._str_indent(self['Examples'])
            out += ['']
            return out
        else:
            return self._str_section('Examples')

    def __str__(self, indent=0, func_role="obj"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Raises'):
            out += self._str_param_list(param_list)
        out += self._str_warnings()
        out += self._str_see_also(func_role)
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_examples()
        for param_list in ('Attributes', 'Methods'):
            out += self._str_member_list(param_list)
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class SphinxFunctionDoc(SphinxDocString, FunctionDoc):
    def __init__(self, obj, doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        FunctionDoc.__init__(self, obj, doc=doc, config=config)

class SphinxClassDoc(SphinxDocString, ClassDoc):
    def __init__(self, obj, doc=None, func_doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        ClassDoc.__init__(self, obj, doc=doc, func_doc=None, config=config)

class SphinxObjDoc(SphinxDocString):
    def __init__(self, obj, doc=None, config={}):
        self._f = obj
        SphinxDocString.__init__(self, doc, config=config)

def get_doc_object(obj, what=None, doc=None, config={}):
    if what is None:
        if inspect.isclass(obj):
            what = 'class'
        elif inspect.ismodule(obj):
            what = 'module'
        elif callable(obj):
            what = 'function'
        else:
            what = 'object'
    if what == 'class':
        return SphinxClassDoc(obj, func_doc=SphinxFunctionDoc, doc=doc,
                              config=config)
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, doc=doc, config=config)
    else:
        if doc is None:
            doc = pydoc.getdoc(obj)
        return SphinxObjDoc(obj, doc, config=config)

########NEW FILE########
__FILENAME__ = numpydoc
"""
========
numpydoc
========

Sphinx extension that handles docstrings in the Numpy standard format. [1]

It will:

- Convert Parameters etc. sections to field lists.
- Convert See Also section to a See also entry.
- Renumber references.
- Extract the signature from the docstring, if it can't be determined otherwise.

.. [1] http://projects.scipy.org/numpy/wiki/CodingStyleGuidelines#docstring-standard

"""

import re
import pydoc
import inspect
from docscrape_sphinx import get_doc_object, SphinxDocString

def mangle_docstrings(app, what, name, obj, options, lines,
                      reference_offset=[0]):

    cfg = dict(use_plots=app.config.numpydoc_use_plots,
               show_class_members=app.config.numpydoc_show_class_members)

    if what == 'module':
        # Strip top title
        title_re = re.compile(ur'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                              re.I|re.S)
        lines[:] = title_re.sub(u'', u"\n".join(lines)).split(u"\n")
    else:
        doc = get_doc_object(obj, what, u"\n".join(lines), config=cfg)
        lines[:] = unicode(doc).split(u"\n")

    if app.config.numpydoc_edit_link and hasattr(obj, '__name__') and \
           obj.__name__:
        if hasattr(obj, '__module__'):
            v = dict(full_name=u"%s.%s" % (obj.__module__, obj.__name__))
        else:
            v = dict(full_name=obj.__name__)
        lines += [u'', u'.. htmlonly::', '']
        lines += [u'    %s' % x for x in
                  (app.config.numpydoc_edit_link % v).split("\n")]

    # replace reference numbers so that there are no duplicates
    references = []
    for line in lines:
        line = line.strip()
        m = re.match(ur'^.. \[([a-z0-9_.-])\]', line, re.I)
        if m:
            references.append(m.group(1))

    # start renaming from the longest string, to avoid overwriting parts
    references.sort(key=lambda x: -len(x))
    if references:
        for i, line in enumerate(lines):
            for r in references:
                if re.match(ur'^\d+$', r):
                    new_r = u"R%d" % (reference_offset[0] + int(r))
                else:
                    new_r = u"%s%d" % (r, reference_offset[0])
                lines[i] = lines[i].replace(u'[%s]_' % r,
                                            u'[%s]_' % new_r)
                lines[i] = lines[i].replace(u'.. [%s]' % r,
                                            u'.. [%s]' % new_r)

    reference_offset[0] += len(references)

def mangle_signature(app, what, name, obj, options, sig, retann):
    # Do not try to inspect classes that don't define `__init__`
    if (inspect.isclass(obj) and
        (not hasattr(obj, '__init__') or
        'initializes x; see ' in pydoc.getdoc(obj.__init__))):
        return '', ''

    if not (callable(obj) or hasattr(obj, '__argspec_is_invalid_')): return
    if not hasattr(obj, '__doc__'): return

    doc = SphinxDocString(pydoc.getdoc(obj))
    if doc['Signature']:
        sig = re.sub(u"^[^(]*", u"", doc['Signature'])
        return sig, u''

def setup(app, get_doc_object_=get_doc_object):
    global get_doc_object
    get_doc_object = get_doc_object_

    app.connect('autodoc-process-docstring', mangle_docstrings)
    app.connect('autodoc-process-signature', mangle_signature)
    app.add_config_value('numpydoc_edit_link', None, False)
    app.add_config_value('numpydoc_use_plots', None, False)
    app.add_config_value('numpydoc_show_class_members', True, True)

    # Extra mangling domains
    app.add_domain(NumpyPythonDomain)
    app.add_domain(NumpyCDomain)

#------------------------------------------------------------------------------
# Docstring-mangling domains
#------------------------------------------------------------------------------

from docutils.statemachine import ViewList
from sphinx.domains.c import CDomain
from sphinx.domains.python import PythonDomain

class ManglingDomainBase(object):
    directive_mangling_map = {}

    def __init__(self, *a, **kw):
        super(ManglingDomainBase, self).__init__(*a, **kw)
        self.wrap_mangling_directives()

    def wrap_mangling_directives(self):
        for name, objtype in self.directive_mangling_map.items():
            self.directives[name] = wrap_mangling_directive(
                self.directives[name], objtype)

class NumpyPythonDomain(ManglingDomainBase, PythonDomain):
    name = 'np'
    directive_mangling_map = {
        'function': 'function',
        'class': 'class',
        'exception': 'class',
        'method': 'function',
        'classmethod': 'function',
        'staticmethod': 'function',
        'attribute': 'attribute',
    }

class NumpyCDomain(ManglingDomainBase, CDomain):
    name = 'np-c'
    directive_mangling_map = {
        'function': 'function',
        'member': 'attribute',
        'macro': 'function',
        'type': 'class',
        'var': 'object',
    }

def wrap_mangling_directive(base_directive, objtype):
    class directive(base_directive):
        def run(self):
            env = self.state.document.settings.env

            name = None
            if self.arguments:
                m = re.match(r'^(.*\s+)?(.*?)(\(.*)?', self.arguments[0])
                name = m.group(2).strip()

            if not name:
                name = self.arguments[0]

            lines = list(self.content)
            mangle_docstrings(env.app, objtype, name, None, None, lines)
            self.content = ViewList(lines, self.content.parent)

            return base_directive.run(self)

    return directive


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# mpltools documentation build configuration file, created by
# sphinx-quickstart on Wed Feb 15 21:16:13 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

curpath = os.path.dirname(__file__)
sys.path.append(os.path.join(curpath, '..', 'ext'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosummary',
              'sphinx.ext.todo', 'sphinx.ext.coverage',
              'sphinx.ext.pngmath', 'sphinx.ext.mathjax',
              'sphinx.ext.viewcode', 'numpydoc', 'mpltools.sphinx.plot2rst']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'mpltools'
copyright = u'2012, Tony S. Yu'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2dev'
# The full version, including alpha/beta/rc tags.
release = '0.2dev'

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
exclude_patterns = []

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
html_theme = 'mpltools'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['../theme/']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'mpltools docs'

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = '_static/mpltools_logo_100.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static', 'videos']

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
htmlhelp_basename = 'mpltoolsdoc'


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
  ('index', 'mpltools.tex', u'mpltools Documentation',
   u'Tony S. Yu', 'manual'),
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
    ('index', 'mpltools', u'mpltools Documentation',
     [u'Tony S. Yu'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'mpltools', u'mpltools Documentation',
   u'Tony S. Yu', 'mpltools', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# -- Options for plot2rst
plot2rst_paths = [('../examples', 'auto_examples'),
                  ('../tutorials', 'auto_tutorials')]
plot2rst_default_thumb = 'examples/default_thumb.png'
plot2rst_thumb_scale = 0.4
plot2rst_rcparams = {'font.size': 9,
                     'font.family': 'serif',
                     'legend.loc': 'best',
                     'legend.numpoints': 1,
                     'figure.figsize': (6, 5),
                     'axes.color_cycle' : ['r', 'k', 'b', 'y', 'g', 'm', 'c'],
                     'image.cmap' : 'gray',
                     'image.interpolation' : 'none'}


########NEW FILE########
__FILENAME__ = apigen
"""
Attempt to generate templates for module reference with Sphinx

To include extension modules, first identify them as valid in the
``_uri2path`` method, then handle them in the ``_parse_module_with_import``
script.

Notes
-----
This parsing is based on import and introspection of modules.
Previously functions and classes were found by parsing the text of .py files.

Extension modules should be discovered and included as well.

This is a modified version of a script originally shipped with the PyMVPA
project, then adapted for use first in NIPY, then in skimage, and then in
mpltools.
"""

# Stdlib imports
import os
import re

from types import BuiltinFunctionType

# suppress print statements (warnings for empty files)
DEBUG = True


class ApiDocWriter(object):
    ''' Class for automatic detection and parsing of API docs
    to Sphinx-parsable reST format'''

    # only separating first two levels
    rst_section_levels = ['*', '=', '-', '~', '^']

    def __init__(self,
                 package_name,
                 rst_extension='.rst',
                 package_skip_patterns=None,
                 module_skip_patterns=None,
                 ):
        ''' Initialize package for parsing

        Parameters
        ----------
        package_name : string
            Name of the top-level package.  *package_name* must be the
            name of an importable package
        rst_extension : string, optional
            Extension for reST files, default '.rst'
        package_skip_patterns : None or sequence of {strings, regexps}
            Sequence of strings giving URIs of packages to be excluded
            Operates on the package path, starting at (including) the
            first dot in the package path, after *package_name* - so,
            if *package_name* is ``sphinx``, then ``sphinx.util`` will
            result in ``.util`` being passed for earching by these
            regexps.  If is None, gives default. Default is:
            ['\.tests$']
        module_skip_patterns : None or sequence
            Sequence of strings giving URIs of modules to be excluded
            Operates on the module name including preceding URI path,
            back to the first dot after *package_name*.  For example
            ``sphinx.util.console`` results in the string to search of
            ``.util.console``
            If is None, gives default. Default is:
            ['\.setup$', '\._']
        '''
        if package_skip_patterns is None:
            package_skip_patterns = ['\\.tests$']
        if module_skip_patterns is None:
            module_skip_patterns = ['\\.setup$', '\\._']
        self.package_name = package_name
        self.rst_extension = rst_extension
        self.package_skip_patterns = package_skip_patterns
        self.module_skip_patterns = module_skip_patterns

    def get_package_name(self):
        return self._package_name

    def set_package_name(self, package_name):
        ''' Set package_name

        >>> docwriter = ApiDocWriter('sphinx')
        >>> import sphinx
        >>> docwriter.root_path == sphinx.__path__[0]
        True
        >>> docwriter.package_name = 'docutils'
        >>> import docutils
        >>> docwriter.root_path == docutils.__path__[0]
        True
        '''
        # It's also possible to imagine caching the module parsing here
        self._package_name = package_name
        root_module = self._import(package_name)
        self.root_path = root_module.__path__[-1]
        self.written_modules = None

    package_name = property(get_package_name, set_package_name, None,
                            'get/set package_name')

    def _import(self, name):
        ''' Import namespace package '''
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod

    def _get_object_name(self, line):
        ''' Get second token in line
        >>> docwriter = ApiDocWriter('sphinx')
        >>> docwriter._get_object_name("  def func():  ")
        'func'
        >>> docwriter._get_object_name("  class Klass(object):  ")
        'Klass'
        >>> docwriter._get_object_name("  class Klass:  ")
        'Klass'
        '''
        name = line.split()[1].split('(')[0].strip()
        # in case we have classes which are not derived from object
        # ie. old style classes
        return name.rstrip(':')

    def _uri2path(self, uri):
        ''' Convert uri to absolute filepath

        Parameters
        ----------
        uri : string
            URI of python module to return path for

        Returns
        -------
        path : None or string
            Returns None if there is no valid path for this URI
            Otherwise returns absolute file system path for URI

        Examples
        --------
        >>> docwriter = ApiDocWriter('sphinx')
        >>> import sphinx
        >>> modpath = sphinx.__path__[0]
        >>> res = docwriter._uri2path('sphinx.builder')
        >>> res == os.path.join(modpath, 'builder.py')
        True
        >>> res = docwriter._uri2path('sphinx')
        >>> res == os.path.join(modpath, '__init__.py')
        True
        >>> docwriter._uri2path('sphinx.does_not_exist')

        '''
        if uri == self.package_name:
            return os.path.join(self.root_path, '__init__.py')
        path = uri.replace(self.package_name + '.', '')
        path = path.replace('.', os.path.sep)
        path = os.path.join(self.root_path, path)
        # XXX maybe check for extensions as well?
        if os.path.exists(path + '.py'): # file
            path += '.py'
        elif os.path.exists(os.path.join(path, '__init__.py')):
            path = os.path.join(path, '__init__.py')
        else:
            return None
        return path

    def _path2uri(self, dirpath):
        ''' Convert directory path to uri '''
        package_dir = self.package_name.replace('.', os.path.sep)
        relpath = dirpath.replace(self.root_path, package_dir)
        if relpath.startswith(os.path.sep):
            relpath = relpath[1:]
        return relpath.replace(os.path.sep, '.')

    def _parse_module(self, uri):
        ''' Parse module defined in *uri* '''
        filename = self._uri2path(uri)
        if filename is None:
            print filename, 'erk'
            # nothing that we could handle here.
            return ([],[])
        f = open(filename, 'rt')
        functions, classes = self._parse_lines(f)
        f.close()
        return functions, classes

    def _parse_module_with_import(self, uri):
        """Look for functions and classes in an importable module.

        Parameters
        ----------
        uri : str
            The name of the module to be parsed. This module needs to be
            importable.

        Returns
        -------
        functions : list of str
            A list of (public) function names in the module.
        classes : list of str
            A list of (public) class names in the module.
        """
        mod = __import__(uri, fromlist=[uri])
        # find all public objects in the module.
        obj_strs = [obj for obj in dir(mod) if not obj.startswith('_')]
        functions = []
        classes = []
        for obj_str in obj_strs:
            # find the actual object from its string representation
            if obj_str not in mod.__dict__:
                continue
            obj = mod.__dict__[obj_str]
            # figure out if obj is a function or class
            if hasattr(obj, 'func_name') or \
               isinstance(obj, BuiltinFunctionType):
                functions.append(obj_str)
            else:
                try:
                    issubclass(obj, object)
                    classes.append(obj_str)
                except TypeError:
                    # not a function or class
                    pass
        return functions, classes

    def _parse_lines(self, linesource):
        ''' Parse lines of text for functions and classes '''
        functions = []
        classes = []
        for line in linesource:
            if line.startswith('def ') and line.count('('):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    functions.append(name)
            elif line.startswith('class '):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    classes.append(name)
            else:
                pass
        functions.sort()
        classes.sort()
        return functions, classes

    def generate_api_doc(self, uri):
        '''Make autodoc documentation template string for a module

        Parameters
        ----------
        uri : string
            python location of module - e.g 'sphinx.builder'

        Returns
        -------
        S : string
            Contents of API doc
        '''
        # get the names of all classes and functions
        functions, classes = self._parse_module_with_import(uri)
        if not len(functions) and not len(classes) and DEBUG:
            print 'WARNING: Empty -', uri  # dbg
            return ''

        # Make a shorter version of the uri that omits the package name for
        # titles
        uri_short = re.sub(r'^%s\.' % self.package_name,'',uri)

        ad = '.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n'

        chap_title = uri_short
        #ad += (chap_title+'\n'+ self.rst_section_levels[1] * len(chap_title)
        #       + '\n\n')

        # Set the chapter title to read 'module' for all modules except for the
        # main packages
        if '.' in uri:
            title = 'Module: :mod:`' + uri_short + '`'
        else:
            title = ':mod:`' + uri_short + '`'
        ad += title + '\n' + self.rst_section_levels[1] * len(title)

        if len(classes):
            ad += '\nInheritance diagram for ``%s``:\n\n' % uri
            ad += '.. inheritance-diagram:: %s \n' % uri
            ad += '   :parts: 3\n'

        ad += '\n.. automodule:: ' + uri + '\n'
        ad += '\n.. currentmodule:: ' + uri + '\n'
#        multi_class = len(classes) > 1
#        multi_fx = len(functions) > 1
#        if multi_class:
#            ad += '\n' + 'Classes' + '\n' + \
#                  self.rst_section_levels[2] * 7 + '\n'
#        elif len(classes) and multi_fx:
#            ad += '\n' + 'Class' + '\n' + \
#                  self.rst_section_levels[2] * 5 + '\n'
        for c in classes:
            ad += '\n:class:`' + c + '`\n' \
                  + self.rst_section_levels[2] * \
                  (len(c)+9) + '\n\n'
            ad += '\n.. autoclass:: ' + c + '\n'
            # must NOT exclude from index to keep cross-refs working
            ad += '  :members:\n' \
                  '  :undoc-members:\n' \
                  '  :show-inheritance:\n' \
                  '  :inherited-members:\n' \
                  '\n' \
                  '  .. automethod:: __init__\n'
#        if multi_fx:
#        ad += '\n' + 'Functions' + '\n' + \
#              self.rst_section_levels[2] * 9 + '\n\n'
#        elif len(functions) and multi_class:
#            ad += '\n' + 'Function' + '\n' + \
#                  self.rst_section_levels[2] * 8 + '\n\n'
        ad += '.. autosummary::\n\n'
        for f in functions:
            ad += '   ' + uri + '.' + f + '\n'
        ad += '\n'

        for f in functions:
            # must NOT exclude from index to keep cross-refs working
            full_f = uri + '.' + f
            ad += f + '\n'
            ad += self.rst_section_levels[2] * len(f) + '\n'
            ad += '\n.. autofunction:: ' + full_f + '\n\n'
        return ad

    def _survives_exclude(self, matchstr, match_type):
        ''' Returns True if *matchstr* does not match patterns

        ``self.package_name`` removed from front of string if present

        Examples
        --------
        >>> dw = ApiDocWriter('sphinx')
        >>> dw._survives_exclude('sphinx.okpkg', 'package')
        True
        >>> dw.package_skip_patterns.append('^\\.badpkg$')
        >>> dw._survives_exclude('sphinx.badpkg', 'package')
        False
        >>> dw._survives_exclude('sphinx.badpkg', 'module')
        True
        >>> dw._survives_exclude('sphinx.badmod', 'module')
        True
        >>> dw.module_skip_patterns.append('^\\.badmod$')
        >>> dw._survives_exclude('sphinx.badmod', 'module')
        False
        '''
        if match_type == 'module':
            patterns = self.module_skip_patterns
        elif match_type == 'package':
            patterns = self.package_skip_patterns
        else:
            raise ValueError('Cannot interpret match type "%s"'
                             % match_type)
        # Match to URI without package name
        L = len(self.package_name)
        if matchstr[:L] == self.package_name:
            matchstr = matchstr[L:]
        for pat in patterns:
            try:
                pat.search
            except AttributeError:
                pat = re.compile(pat)
            if pat.search(matchstr):
                return False
        return True

    def discover_modules(self):
        ''' Return module sequence discovered from ``self.package_name``


        Parameters
        ----------
        None

        Returns
        -------
        mods : sequence
            Sequence of module names within ``self.package_name``

        Examples
        --------
        >>> dw = ApiDocWriter('sphinx')
        >>> mods = dw.discover_modules()
        >>> 'sphinx.util' in mods
        True
        >>> dw.package_skip_patterns.append('\.util$')
        >>> 'sphinx.util' in dw.discover_modules()
        False
        >>>
        '''
        modules = [self.package_name]
        # raw directory parsing
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Check directory names for packages
            root_uri = self._path2uri(os.path.join(self.root_path,
                                                   dirpath))
            for dirname in dirnames[:]: # copy list - we modify inplace
                package_uri = '.'.join((root_uri, dirname))
                if (self._uri2path(package_uri) and
                    self._survives_exclude(package_uri, 'package')):
                    modules.append(package_uri)
                else:
                    dirnames.remove(dirname)
            # Check filenames for modules
            for filename in filenames:
                module_name = filename[:-3]
                module_uri = '.'.join((root_uri, module_name))
                if (self._uri2path(module_uri) and
                    self._survives_exclude(module_uri, 'module')):
                    modules.append(module_uri)
        return sorted(modules)

    def write_modules_api(self, modules,outdir):
        # write the list
        written_modules = []
        for m in modules:
            api_str = self.generate_api_doc(m)
            if not api_str:
                continue
            # write out to file
            outfile = os.path.join(outdir,
                                   m + self.rst_extension)
            fileobj = open(outfile, 'wt')
            fileobj.write(api_str)
            fileobj.close()
            written_modules.append(m)
        self.written_modules = written_modules

    def write_api_docs(self, outdir):
        """Generate API reST files.

        Parameters
        ----------
        outdir : string
            Directory name in which to store files
            We create automatic filenames for each module

        Returns
        -------
        None

        Notes
        -----
        Sets self.written_modules to list of written modules
        """
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        # compose list of modules
        modules = self.discover_modules()
        # group modules so we have one less level
        module_depth = max([len(item.split('.')) for item in modules])
        # modifying modules in-place, so make a copy
        for item in modules[:]:
            # Do not treat the .py files all as separate modules.
            # Like this, only the objects exported in __all__ get picked up.
            if not (len(item.split('.')) < module_depth):
                modules.remove(item)
        self.write_modules_api(modules,outdir)

    def write_index(self, outdir, froot='gen', relative_to=None):
        """Make a reST API index file from written files

        Parameters
        ----------
        path : string
            Filename to write index to
        outdir : string
            Directory to which to write generated index file
        froot : string, optional
            root (filename without extension) of filename to write to
            Defaults to 'gen'.  We add ``self.rst_extension``.
        relative_to : string
            path to which written filenames are relative.  This
            component of the written file path will be removed from
            outdir, in the generated index.  Default is None, meaning,
            leave path as it is.
        """
        if self.written_modules is None:
            raise ValueError('No modules written')
        # Get full filename path
        path = os.path.join(outdir, froot+self.rst_extension)
        # Path written into index is relative to rootpath
        if relative_to is not None:
            relpath = (outdir + os.path.sep).replace(relative_to + os.path.sep, '')
        else:
            relpath = outdir
        print "outdir: ", relpath
        idx = open(path,'wt')
        w = idx.write
        w('.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n')

        title = "API Reference"
        w(title + "\n")
        w("=" * len(title) + "\n\n")
        w('.. toctree::\n\n')
        for f in self.written_modules:
            w('   %s\n' % os.path.join(relpath,f))
        idx.close()

########NEW FILE########
__FILENAME__ = build_modref_templates
#!/usr/bin/env python
"""Script to auto-generate our API docs.
"""
# stdlib imports
import os, sys

# local imports
from apigen import ApiDocWriter

# version comparison
from distutils.version import LooseVersion as V

#*****************************************************************************

def abort(error):
    print '*WARNING* API documentation not generated: %s'%error
    exit()


def assert_source_and_install_match(package):
    """
    Check that the source version is equal to the installed
    version. If the versions mismatch the API documentation sources
    are not (re)generated. This avoids automatic generation of documentation
    for older or newer versions if such versions are installed on the system.
    """
    module = sys.modules[package]

    installed_version = V(module.version.version)

    setup_lines = open('../setup.py').readlines()
    for l in setup_lines:
        if l.startswith('VERSION'):
            source_version = V(l.split("'")[1])
            break

    if source_version != installed_version:
        abort("Installed version does not match source version")


if __name__ == '__main__':
    package = 'mpltools'

    # Check that the 'image' package is available. If not, the API
    # documentation is not (re)generated and existing API documentation
    # sources will be used.

    try:
        __import__(package)
    except ImportError, e:
        abort("Cannot import mpltools")

    #assert_source_and_install_match(package)

    outdir = 'source/api'
    docwriter = ApiDocWriter(package)
    docwriter.package_skip_patterns += [r'\.fixes$',
                                        r'\.externals$',
                                        ]
    docwriter.write_api_docs(outdir)
    docwriter.write_index(outdir, 'api', relative_to='source/api')
    print '%d files written' % len(docwriter.written_modules)

########NEW FILE########
__FILENAME__ = plot_all_styles
"""
Save test plots for all styles defined in `mpltools.style`.

Note that `test_artists_plot` calls `matplotlib.pyplot.tight_layout` so subplot
spacing is not tested for this plot.
"""

import os
import os.path as pth

import numpy as np

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

from mpltools import style


PATH = pth.abspath(pth.dirname(__file__))

TEST_DIRS = ('test_artists_png', 'test_artists_pdf',
            'test_simple_png', 'test_simple_pdf')
for d in TEST_DIRS:
    test_dir = pth.join(PATH, d)
    if not pth.exists(test_dir):
        os.mkdir(test_dir)


def test_artists_plot():
    fig, axes = plt.subplots(2, 2)
    axes = axes.ravel()

    x = np.linspace(0, 1)
    axes[0].plot(x, np.sin(2*np.pi*x), label='line')
    c = plt.Circle((0.25, 0), radius=0.1, label='patch')
    axes[0].add_patch(c)
    axes[0].grid()
    axes[0].legend()

    img = axes[1].imshow(np.random.random(size=(20, 20)))
    axes[1].set_title('image')

    ncolors = len(plt.rcParams['axes.color_cycle'])
    phi = np.linspace(0, 2*np.pi, ncolors + 1)[:-1]
    for p in phi:
        axes[2].plot(x, np.sin(2*np.pi*x + p))
    axes[2].set_title('color cycle')

    axes[3].text(0, 0, 'hello world')
    axes[3].set_xlabel('x-label')
    axes[3].set_ylabel('y-label')
    axes[3].set_title('title')

    try:
        fig.tight_layout()
    except AttributeError:
        pass
    # `colorbar` should be called after `tight_layout`.
    fig.colorbar(img, ax=axes[1])
    return fig

def test_simple_plot():
    fig, ax = plt.subplots()

    ax.plot([0, 1])
    ax.set_xlabel('x-label')
    ax.set_ylabel('y-label')
    ax.set_title('title')

    return fig


# Only show styles defined by package, not by user.
base_styles = style.baselib.keys()
for sty in base_styles:
    # reset matplotlib defaults before applying new style
    plt.rcdefaults()

    style.use(sty, use_baselib=True)
    print "Plotting tests for '%s' style" % sty

    fig = test_artists_plot()
    fig.savefig(pth.join(PATH, 'test_artists_png', sty + '.png'))
    fig.savefig(pth.join(PATH, 'test_artists_pdf', sty + '.pdf'))

    fig = test_simple_plot()
    fig.savefig(pth.join(PATH, 'test_simple_png', sty + '.png'))
    fig.savefig(pth.join(PATH, 'test_simple_pdf', sty + '.pdf'))


########NEW FILE########
__FILENAME__ = animation
"""
Animation class.

This implementation is a interface for Matplotlib's FuncAnimation class, but
with different interface for:

* Easy reuse of animation code.

* Logical separation of setup parameter (passed to `__init__`) and animation
  parameters (passed to `animate`).

* Unlike Matplotlib's animation class, this Animation class clearly must be
  assigned to a variable (in order to call the `animate` method). The
  FuncAnimation object needs to be assigned to a variable so that it isn't
  garbage-collected, but this requirement is confusing, and easily forgotten,
  because the user never uses the animation object directly.


"""
import warnings
import matplotlib.animation as _animation


__all__ = ['Animation']


class Animation(object):
    """Base class to create animation objects.

    To create an animation, simply subclass `Animation` and override the
    `__init__` method to create a plot (`self.fig` needs to be assigned to the
    figure object here), and override `update` with a generator that updates
    the plot:

    .. code-block:: python

       class RandomPoints(Animation):

           def __init__(self, width=10):
               self.fig, self.ax = plt.subplots()
               self.width = width
               self.ax.axis([0, width, 0, width])
               self.num_frames = 20

           def update(self):
               artists = []
               self.ax.lines = [] # Clean up plot when repeating animation.
               for i in np.arange(self.num_frames):
                   x, y = np.random.uniform(0, self.width, size=2)
                   artists.append(self.ax.plot(x, y, 'ro'))
                   yield artists

       pts = RandomPoints()
       pts.animate()

    Note: if you want to use blitting (see docstring for `Animation.animate`),
    You must yield a sequence of artists in `update`.

    This Animation class does not subclass any of Matplotlib's animation
    classes because the `__init__` method takes arguments for creating the
    plot, while `animate` method is what accepts arguments that alter the
    animation.

    """
    def __init__(self):
        """Initialize plot for animation.

        Replace this method to initialize the plot. The only requirement is
        that you must create a figure object assigned to `self.fig`.
        """
        raise NotImplementedError

    def init_background(self):
        """Initialize background artists.

        Note: This method is passed to `FuncAnimation` as `init_func`.
        """
        pass

    def update(self):
        """Update frame.

        Replace this method to with a generator that updates artists and calls
        an empty `yield` when updates are complete.
        """
        raise NotImplementedError

    def animate(self, **kwargs):
        """Run animation.

        Parameters
        ----------
        interval : float, defaults to 200
            Time delay, in milliseconds, between frames.

        repeat : {True | False}
            If True, repeat animation when the sequence of frames is completed.

        repeat_delay : None
            Delay in milliseconds before repeating the animation.

        blit : {False | True}
            If True, use blitting to optimize drawing. Unsupported by some
            backends.

        init_background : function
            If None, the results of drawing
            from the first item in the frames sequence will be used. This can
            also be added as a class method instead of passing to `animate`.

        save_count : int
            If saving a movie, `save_count` determines number of frames saved.
            If not defined, use `num_frames` attribute (if defined); otherwise,
            set to 100 frames.
        """
        reusable_generator = lambda: iter(self.update())
        kwargs['init_background'] = self.init_background

        self._warn_num_frames = False
        if hasattr(self, 'num_frames') and 'save_count' not in kwargs:
            kwargs['save_count'] = self.num_frames
        if 'save_count' not in kwargs:
            kwargs['save_count'] = 100
            self._warn_num_frames = True

        self._ani = _GenAnimation(self.fig, reusable_generator, **kwargs)

    def save(self, filename, **kwargs):
        """Saves a movie file by drawing every frame.

        Parameters
        ----------
        filename : str
            The output filename.

        writer : :class:`matplotlib.animation.MovieWriter` or str
            Class for writing movie from animation. If string, must be 'ffmpeg'
            or 'mencoder', which identifies the MovieWriter class used.
            If None, use 'animation.writer' rcparam.

        fps : float
            The frames per second in the movie. If None, use the animation's
            specified `interval` to set the frames per second.

        dpi : int
            Dots per inch for the movie frames.

        codec :
            Video codec to be used. Not all codecs are supported by a given
            writer. If None, use 'animation.codec' rcparam.

        bitrate : int
            Kilobits per seconds in the movie compressed movie. A higher
            value gives a higher quality movie, but at the cost of increased
            file size. If None, use `animation.bitrate` rcparam.

        extra_args : list
            List of extra string arguments passed to the underlying movie
            utility. If None, use 'animation.extra_args' rcParam.

        metadata : dict
            Metadata to include in the output file. Some keys that may be of
            use include: title, artist, genre, subject, copyright, comment.

        """

        if not hasattr(self, '_ani'):
            raise RuntimeError("Run `animate` method before calling `save`!")
            return
        if self._warn_num_frames:
            msg = "%s `num_frames` attribute. Animation may be truncated."
            warnings.warn(msg % self.__class__.__name__)
        self._ani.save(filename, **kwargs)


class _GenAnimation(_animation.FuncAnimation):

    def __init__(self, fig, frames, init_background=None, save_count=None,
                 **kwargs):
        self._iter_gen = frames

        self._init_func = init_background
        self.save_count = save_count if save_count is not None else 100

        # Dummy args and function for compatibility with FuncAnimation
        self._args = ()
        self._func = lambda args: args

        self._save_seq = []
        _animation.TimedAnimation.__init__(self, fig, **kwargs)
        # Clear saved seq since TimedAnimation.__init__ adds a single frame.
        self._save_seq = []


########NEW FILE########
__FILENAME__ = _slopemarker
import numpy as np
import matplotlib.pyplot as plt


__all__ = ['slope_marker']


def slope_marker(origin, slope, invert=False, size_frac=0.1, pad_frac=0.2,
                 text_kwargs=None, poly_kwargs=None, ax=None):
    """Plot triangular slope marker labeled with slope.

    Parameters
    ----------
    origin : 2-tuple
        (x, y) coordinates for the slope.
    slope : float or 2-tuple
        Slope of marker. If float, a single slope label is printed; if tuple,
        you can specify the (rise, run) of the slope and 2 labels are printed.
    invert : bool
        If True, hypotenuse is on the left (i.e. \| or /|).
        If False, hypotenuse is on the right (i.e. |/ or |\).
    size_frac : float
        Fraction of the xaxis length used to determine the size of the slope
        marker. Should be less than 1.
    pad_frac : float
        Fraction of the slope marker size used to pad text labels.
    fontsize : float
        Font size of slope labels.
    text_kwargs : dict
        Keyword arguments passed to `matplotlib.text.Text`.
    poly_kwargs : dict
        Keyword arguments passed to `matplotlib.patches.Polygon`.
    """
    ax = ax if ax is not None else plt.gca()
    text_kwargs = {} if text_kwargs is None else text_kwargs
    poly_kwargs = {} if poly_kwargs is None else poly_kwargs

    if np.iterable(slope):
        rise, run = slope
        slope = float(rise) / run
    else:
        rise = run = None

    x0, y0 = origin
    xlim = ax.get_xlim()
    dx_linear = size_frac * (xlim[1] - xlim[0])
    dx_decades = size_frac * (np.log10(xlim[1]) - np.log10(xlim[0]))

    if invert:
        dx_linear = -dx_linear
        dx_decades = -dx_decades

    if ax.get_xscale() == 'log':
        log_size = dx_decades
        dx = log_displace(x0, log_size) - x0
        x_run = _text_position(x0, log_size/2., scale='log')
        x_rise = _text_position(x0+dx, dx_decades*pad_frac, scale='log')
    else:
        dx = dx_linear
        x_run = _text_position(x0, dx/2.)
        x_rise = _text_position(x0+dx, pad_frac * dx)

    if ax.get_yscale() == 'log':
        log_size = dx_decades * slope
        dy = log_displace(y0, log_size) - y0
        y_run = _text_position(y0, -dx_decades*slope*pad_frac, scale='log')
        y_rise = _text_position(y0, log_size/2., scale='log')
    else:
        dy = dx_linear * slope
        y_run = _text_position(y0, -(pad_frac * dy))
        y_rise = _text_position(y0, dy/2.)

    x_pad = pad_frac * dx
    y_pad = pad_frac * dy

    va = 'top' if y_pad > 0 else 'bottom'
    ha = 'left' if x_pad > 0 else 'right'
    if rise is not None:
        ax.text(x_run, y_run, str(run), va=va, ha='center', **text_kwargs)
        ax.text(x_rise, y_rise, str(rise), ha=ha, va='center', **text_kwargs)
    else:
        ax.text(x_rise, y_rise, str(slope), ha=ha, va='center', **text_kwargs)

    ax.add_patch(_slope_triangle(origin, dx, dy, **poly_kwargs))


def log_displace(x0, dx_log):
    """Return point displaced by a logarithmic value.

    For example, if you want to move 1 decade away from `x0`, set `dx_log` = 1,
    such that for `x0` = 10, we have `log_displace(10, 1)` = 100

    Parameters
    ----------
    x0 : float
        reference point
    dx_log : float
        displacement in decades.
    """
    return 10**(np.log10(x0) + dx_log)


def _text_position(x0, dx, scale='linear'):
    if scale == 'linear':
        return x0 + dx
    elif scale == 'log':
        return log_displace(x0, dx)
    else:
        raise ValueError('Unknown value for `scale`: %s' % scale)


def _slope_triangle(origin, dx, dy, fc='0.8', **poly_kwargs):
    """Return Polygon representing slope.
          /|
         / | dy
        /__|
         dx
    """
    if 'ec' not in poly_kwargs and 'edgecolor' not in poly_kwargs:
        poly_kwargs['edgecolor'] = 'none'
    if 'fc' not in poly_kwargs and 'facecolor' not in poly_kwargs:
        poly_kwargs['facecolor'] = '0.8'
    verts = [np.asarray(origin)]
    verts.append(verts[0] + (dx, 0))
    verts.append(verts[0] + (dx, dy))
    return plt.Polygon(verts, **poly_kwargs)


########NEW FILE########
__FILENAME__ = color
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from ._config import config


__all__ = ['color_mapper', 'colors_from_cmap', 'cycle_cmap', 'LinearColormap']


class LinearColormap(LinearSegmentedColormap):
    """Create Matplotlib colormap with color values specified at key points.

    This class simplifies the call signature of LinearSegmentedColormap. By
    default, colors specified by `color_data` are equally spaced along the
    colormap.

    Parameters
    ----------
    name : str
        Name of colormap.
    color_data : list or dict
        Colors at each index value. Two input types are supported:

            List of RGB or RGBA tuples. For example, red and blue::

                color_data = [(1, 0, 0), (0, 0, 1)]

            Dict of 'red', 'green', 'blue', and (optionally) 'alpha' values.
            For example, the following would give a red-to-blue gradient::

                color_data = {'red': [1, 0], 'green': [0, 0], 'blue': [0, 1]}

    index : list of floats (0, 1)
        Note that these indices must match the length of `color_data`.
        If None, colors in `color_data` are equally spaced in colormap.

    Examples
    --------
    Linear colormap going from white to red

    >>> white_red = LinearColormap('white_red', [(1, 1, 1), (0.8, 0, 0)])

    Colormap going from blue to white to red

    >>> bwr = LinearColormap('blue_white_red', [(0.0, 0.2, 0.4),    # blue
    ...                                         (1.0, 1.0, 1.0),    # white
    ...                                         (0.4, 0.0, 0.1)])   # red

    You can use a repeated index to get a segmented color.
    - Blue below midpoint of colormap, red above mid point.
    - Alpha maximum at the edges, minimum in the middle.

    >>> bcr_rgba = [(0.02, 0.2, 0.4, 1),    # grayish blue, opaque
    ...             (0.02, 0.2, 0.4, 0.3),  # grayish blue, transparent
    ...             (0.4,  0.0, 0.1, 0.3),  # dark red, transparent
    ...             (0.4,  0.0, 0.1, 1)]    # dark red, opaque
    >>> blue_clear_red = color.LinearColormap('blue_clear_red', bcr_rgba,
    ...                                       index=[0, 0.5, 0.5, 1])

    """

    def __init__(self, name, color_data, index=None, **kwargs):
        if not hasattr(color_data, 'keys'):
            color_data = rgb_list_to_colordict(color_data)

        if index is None:
            # If index not given, RGB colors are evenly-spaced in colormap.
            index = np.linspace(0, 1, len(color_data['red']))

        # Adapt color_data to the form expected by LinearSegmentedColormap.
        color_data = dict((key, [(x, y, y) for x, y in zip(index, value)])
                          for key, value in color_data.iteritems())
        LinearSegmentedColormap.__init__(self, name, color_data, **kwargs)


def rgb_list_to_colordict(rgb_list):
    colors_by_channel = zip(*rgb_list)
    channels = ('red', 'green', 'blue', 'alpha')
    return dict((color, value)
                for color, value in zip(channels, colors_by_channel))


CMAP_RANGE = config['color']['cmap_range']


def color_mapper(parameter_range, cmap=None, start=None, stop=None):
    """Return color mapper, which returns color based on parameter value.

    Parameters
    ----------
    parameter_range : tuple of floats
        Minimum and maximum value of parameter.

    cmap : str or colormap
        A matplotlib colormap (see matplotlib.pyplot.cm) or the name of one.

    start, stop: 0 <= float <= 1
        Limit colormap to this range (start < stop 1). You should limit the
        range of colormaps with light values (assuming a white background).

    Returns
    -------
    map_color : function
        Function that returns an RGBA color from a parameter value.

    """
    if cmap is None:
        cmap = config['color']['cmap']
    if isinstance(cmap, basestring):
        cmap = getattr(plt.cm, cmap)

    crange = list(CMAP_RANGE.get(cmap.name, (0, 1)))
    if start is None:
        start = crange[0]
    if stop is None:
        stop = crange[1]

    assert 0 <= start <= 1
    assert 0 <= stop <= 1

    pmin, pmax = parameter_range
    def map_color(val):
        """Return color based on parameter value `val`."""
        assert pmin <= val <= pmax
        val_norm = (val - pmin) * float(stop - start) / (pmax - pmin)
        idx = val_norm + start
        return cmap(idx)

    return map_color


def colors_from_cmap(length=50, cmap=None, start=None, stop=None):
    """Return color cycle from a given colormap.

    Parameters
    ----------
    length : int
        The number of colors in the cycle. When `length` is large (> ~10), it
        is difficult to distinguish between successive lines because successive
        colors are very similar.

    cmap : str
        Name of a matplotlib colormap (see matplotlib.pyplot.cm).

    start, stop: 0 <= float <= 1
        Limit colormap to this range (start < stop 1). You should limit the
        range of colormaps with light values (assuming a white background).
        Some colors have default start/stop values (see `CMAP_RANGE`).

    Returns
    -------
    colors : list
        List of RGBA colors.

    See Also
    --------
    cycle_cmap

    """
    if cmap is None:
        cmap = config['color']['cmap']
    if isinstance(cmap, basestring):
        cmap = getattr(plt.cm, cmap)

    crange = CMAP_RANGE.get(cmap.name, (0, 1))
    if start is not None:
        crange[0] = start
    if stop is not None:
        crange[1] = stop

    assert 0 <= crange[0] <= 1
    assert 0 <= crange[1] <= 1

    idx = np.linspace(crange[0], crange[1], num=length)
    return cmap(idx)


def cycle_cmap(length=50, cmap=None, start=None, stop=None, ax=None):
    """Set default color cycle of matplotlib based on colormap.

    Note that the default color cycle is **not changed** if `ax` parameter
    is set; only the axes's color cycle will be changed.

    Parameters
    ----------
    length : int
        The number of colors in the cycle. When `length` is large (> ~10), it
        is difficult to distinguish between successive lines because successive
        colors are very similar.

    cmap : str
        Name of a matplotlib colormap (see matplotlib.pyplot.cm).

    start, stop: 0 <= float <= 1
        Limit colormap to this range (start < stop 1). You should limit the
        range of colormaps with light values (assuming a white background).
        Some colors have default start/stop values (see `CMAP_RANGE`).

    ax : matplotlib axes
        If ax is not None, then change the axes's color cycle instead of the
        default color cycle.

    See Also
    --------
    colors_from_cmap, color_mapper

    """
    color_cycle = colors_from_cmap(length, cmap, start, stop)

    if ax is None:
        plt.rc('axes', color_cycle=color_cycle.tolist())
    else:
        ax.set_color_cycle(color_cycle)


########NEW FILE########
__FILENAME__ = core
import os
import matplotlib.pyplot as plt


def save_all_figs(directory='./', fmt='png', default_name='untitled%i'):
    """Save all open figures.

    Each figure is saved with the title of the plot, if possible, and multiple
    file formats can be saved by specifying a list of extensions.

    Parameters
    ------------
    directory : str
        Path where figures are saved.
    fmt : str, list of str
        Image format(s) of saved figures.
    default_name : str
        Default filename to use if plot has no title. Must contain '%i' for the
        figure number.

    Examples
    --------
    >>> save_all_figs('plots/', fmt=['pdf','png'])

    """
    if isinstance(fmt, basestring):
        fmt = [fmt]

    for fignum in plt.get_fignums():
        try:
            filename = plt.figure(fignum).get_axes()[0].get_title()
        except IndexError:
            continue

        if filename == '':
            filename = default_name % fignum

        savepath = os.path.join(directory, filename)

        for a_fmt in fmt:
            savename = '%s.%s' % (savepath, a_fmt)
            plt.savefig(savename)
            print("Saved '%s'" % savename)


########NEW FILE########
__FILENAME__ = layout
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


__all__ = ['figure', 'figaspect', 'figimage',
           'clear_frame', 'cross_spines', 'pad_limits']


def figure(aspect_ratio=0.75, scale=1, width=None, **kwargs):
    """Return matplotlib figure window.

    Calculate figure height using `aspect_ratio` and *default* figure width.

    Parameters
    ----------
    aspect_ratio : float
        Aspect ratio, height / width, of figure.
    scale : float
        Scale default size of the figure.
    width : float
        Figure width in inches. If None, default to rc parameters.

    See Also
    --------
    figaspect

    """
    size = figaspect(aspect_ratio, scale=scale, width=width)
    return plt.figure(figsize=size, **kwargs)


def figaspect(aspect_ratio=0.75, scale=1, width=None):
    """Return figure size (width, height) in inches.

    Calculate figure height using `aspect_ratio` and *default* figure width.
    For example, `figaspect(2)` gives a size that's twice as tall as it is
    wide.

    Note that `figaspect` uses the default figure width, or a specified
    `width`, and adjusts the height; this is the opposite of
    `pyplot.figaspect`, which constrains the figure height and adjusts the
    width. This function's behavior is preferred when you have a constraint on
    the figure width (e.g. in a journal article or a web page with a set
    body-width).

    Parameters
    ----------
    aspect_ratio : float
        Aspect ratio, height / width, of figure.
    scale : float
        Scale default size of the figure.
    width : float
        Figure width in inches. If None, default to rc parameters.

    Returns
    -------
    width, height : float
        Width and height of figure.
    """
    if width is None:
        width, h = plt.rcParams['figure.figsize']
    height = width * aspect_ratio
    return width * scale, height * scale


def clear_frame(ax=None):
    """Remove the frame (ticks and spines) from an axes.

    This differs from turning off the axis (`plt.axis('off')` or
    `ax.set_axis_off()`) in that only the ticks and spines are removed. Turning
    off the axis also removes the axes background and axis labels.

    Parameters
    ----------
    ax : :class:`~matplotlib.axes.Axes`
        Axes to modify. If None, use current axes.
    """
    ax = ax if ax is not None else plt.gca()

    ax.xaxis.set_ticks([])
    ax.yaxis.set_ticks([])
    for spine in ax.spines.itervalues():
        spine.set_visible(False)


def figimage(img, scale=1, dpi=None):
    """Return figure and axes with figure tightly surrounding image.

    Unlike pyplot.figimage, this actually plots onto an axes object, which
    fills the figure. Plotting the image onto an axes allows for subsequent
    overlays.

    Parameters
    ----------
    img : array
        image to plot
    scale : float
        If scale is 1, the figure and axes have the same dimension as the
        image.  Smaller values of `scale` will shrink the figure.
    dpi : int
        Dots per inch for figure. If None, use the default rcParam.
    """
    dpi = dpi if dpi is not None else plt.rcParams['figure.dpi']

    h, w = img.shape
    figsize = np.array((w, h), dtype=float) / dpi * scale

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.subplots_adjust(left=0, bottom=0, right=1, top=1)

    ax.set_axis_off()
    ax.imshow(img)
    ax.autoscale(enable=False)
    return fig, ax


def clip_zero_formatter(tick_val, tick_pos):
    """Tick formatter that returns empty string for zero values."""
    if tick_val == 0:
        return ''
    return tick_val


def cross_spines(zero_cross=False, remove_zeros=True, ax=None):
    """Remove top and right spines from an axes.

    Parameters
    ----------
    zero_cross : bool
        If True, the spines are set so that they cross at zero.
    remove_zeros : bool
        If True **and `zero_cross` is True**, remove zero ticks.
    ax : :class:`~matplotlib.axes.Axes`
        Axes to modify. If None, use current axes.
    """
    ax = ax if ax is not None else plt.gca()

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    if zero_cross:
        ax.spines['bottom'].set_position('zero')
        ax.spines['left'].set_position('zero')
        if remove_zeros:
            formatter = mticker.FuncFormatter(clip_zero_formatter)
            ax.xaxis.set_major_formatter(formatter)
            ax.yaxis.set_major_formatter(formatter)
    return ax


def pad_limits(pad_frac=0.05, ax=None):
    """Pad data limits to nicely accomodate data.

    Padding is useful when you use markers, which often get cropped by tight
    data limits since only their center-positions are used to calculate limits.

    Parameters
    ----------
    pad_frac : float
        Padding is calculated as a fraction of the data span. `pad_frac = 0`
        is equivalent to calling plt.axis('tight').
    ax : :class:`~matplotlib.axes.Axes`
        Axes to modify. If None, use current axes.
    """
    ax = ax if ax is not None else plt.gca()
    ax.set_xlim(_calc_limits(ax.xaxis, pad_frac))
    ax.set_ylim(_calc_limits(ax.yaxis, pad_frac))


def _calc_limits(axis, frac):
    limits = axis.get_data_interval()
    if axis.get_scale() == 'log':
        log_limits = np.log10(limits)
        mag = np.diff(log_limits)[0]
        pad = np.array([-mag*frac, mag*frac])
        return 10**(log_limits + pad)
    elif axis.get_scale() == 'linear':
        mag = np.diff(limits)[0]
        pad = np.array([-mag*frac, mag*frac])
        return limits + pad


if __name__ == '__main__':
    from yutils.mpl.core import demo_plot

    f, ax = plt.subplots()
    demo_plot(ax)
    cross_spines(ax)
    ax.set_title('cross_spines')

    f, ax = plt.subplots()
    demo_plot(ax)
    pad_limits(ax=ax)
    ax.set_title('floating_yaxis with pad_limits')

    plt.show()


########NEW FILE########
__FILENAME__ = errorfill
import warnings

import numpy as np
import matplotlib.pyplot as plt


__all__ = ['errorfill']


def errorfill(x, y, yerr=None, xerr=None, color=None, ls=None, lw=None,
              alpha=1, alpha_fill=0.3, label='', label_fill='', ax=None):
    """Plot data with errors marked by a filled region.

    Parameters
    ----------
    x, y : arrays
        Coordinates of data.
    yerr, xerr: [scalar | N, (N, 1), or (2, N) array]
        Error for the input data.
        - If scalar, then filled region spans `y +/- yerr` or `x +/- xerr`.
    color : Matplotlib color
        Color of line and fill region.
    ls : Matplotlib line style
        Style of the line
    lw : Matplotlib line width, float value in points
        Width of the line
    alpha : float
        Opacity used for plotting.
    alpha_fill : float
        Opacity of filled region. Note: the actual opacity of the fill is
        `alpha * alpha_fill`.
    label : str
        Label for line.
    label_fill : str
        Label for filled region.
    ax : Axis instance
        The plot is drawn on axis `ax`. If `None` the current axis is used
    """
    ax = ax if ax is not None else plt.gca()

    alpha_fill *= alpha

    if color is None:
        color = ax._get_lines.color_cycle.next()
    if ls is None:
        ls = plt.rcParams['lines.linestyle']
    if lw is None:
        lw = plt.rcParams['lines.linewidth']
    ax.plot(x, y, color, linestyle=ls, linewidth=lw, alpha=alpha, label=label)

    if yerr is not None and xerr is not None:
        msg = "Setting both `yerr` and `xerr` is not supported. Ignore `xerr`."
        warnings.warn(msg)

    kwargs_fill = dict(color=color, alpha=alpha_fill, label=label_fill)
    if yerr is not None:
        ymin, ymax = extrema_from_error_input(y, yerr)
        fill_between(x, ymax, ymin, ax=ax, **kwargs_fill)
    elif xerr is not None:
        xmin, xmax = extrema_from_error_input(x, xerr)
        fill_between_x(y, xmax, xmin, ax=ax, **kwargs_fill)


def extrema_from_error_input(z, zerr):
    if np.isscalar(zerr) or len(zerr) == len(z):
        zmin = z - zerr
        zmax = z + zerr
    elif len(zerr) == 2:
        zmin, zmax = z - zerr[0], z + zerr[1]
    return zmin, zmax


# Wrappers around `fill_between` and `fill_between_x` that create proxy artists
# so that filled regions show up correctly legends.

def fill_between(x, y1, y2=0, ax=None, **kwargs):
    ax = ax if ax is not None else plt.gca()
    ax.fill_between(x, y1, y2, **kwargs)
    ax.add_patch(plt.Rectangle((0, 0), 0, 0, **kwargs))

def fill_between_x(x, y1, y2=0, ax=None, **kwargs):
    ax = ax if ax is not None else plt.gca()
    ax.fill_betweenx(x, y1, y2, **kwargs)
    ax.add_patch(plt.Rectangle((0, 0), 0, 0, **kwargs))


if __name__ == '__main__':
    x = np.linspace(0, 2 * np.pi)
    y_sin = np.sin(x)
    y_cos = np.cos(x)

    errorfill(x, y_sin, 0.2)
    errorfill(x, y_cos, 0.2)

    plt.show()

########NEW FILE########
__FILENAME__ = hinton
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import collections
from matplotlib import transforms
from matplotlib import ticker

__all__ = ['hinton']


# TOOD: Add yutils.mpl._coll to mpltools and use that for square collection.
class SquareCollection(collections.RegularPolyCollection):
    """Return a collection of squares."""

    def __init__(self, **kwargs):
        super(SquareCollection, self).__init__(4, rotation=np.pi/4., **kwargs)

    def get_transform(self):
        """Return transform scaling circle areas to data space."""
        ax = self.axes
        pts2pixels = 72.0 / ax.figure.dpi
        scale_x = pts2pixels * ax.bbox.width / ax.viewLim.width
        scale_y = pts2pixels * ax.bbox.height / ax.viewLim.height
        return transforms.Affine2D().scale(scale_x, scale_y)


def hinton(inarray, max_value=None, use_default_ticks=True):
    """Plot Hinton diagram for visualizing the values of a 2D array.

    Plot representation of an array with positive and negative values
    represented by white and black squares, respectively. The size of each
    square represents the magnitude of each value.

    Unlike the hinton demo in the matplotlib gallery [1]_, this implementation
    uses a RegularPolyCollection to draw squares, which is much more efficient
    than drawing individual Rectangles.

    .. note::
        This function inverts the y-axis to match the origin for arrays.

    .. [1] http://matplotlib.sourceforge.net/examples/api/hinton_demo.html

    Parameters
    ----------
    inarray : array
        Array to plot.
    max_value : float
        Any *absolute* value larger than `max_value` will be represented by a
        unit square.
    use_default_ticks: boolean
        Disable tick-generation and generate them outside this function.
    """

    ax = plt.gca()
    ax.set_axis_bgcolor('gray')
    # make sure we're working with a numpy array, not a numpy matrix
    inarray = np.asarray(inarray)
    height, width = inarray.shape
    if max_value is None:
        max_value = 2**np.ceil(np.log(np.max(np.abs(inarray)))/np.log(2))
    values = np.clip(inarray/max_value, -1, 1)
    rows, cols = np.mgrid[:height, :width]

    pos = np.where(values > 0)
    neg = np.where(values < 0)
    for idx, color in zip([pos, neg], ['white', 'black']):
        if len(idx[0]) > 0:
            xy = zip(cols[idx], rows[idx])
            circle_areas = np.pi / 2 * np.abs(values[idx])
            squares = SquareCollection(sizes=circle_areas,
                                       offsets=xy, transOffset=ax.transData,
                                       facecolor=color, edgecolor=color)
            ax.add_collection(squares, autolim=True)

    ax.axis('scaled')
    # set data limits instead of using xlim, ylim.
    ax.set_xlim(-0.5, width-0.5)
    ax.set_ylim(height-0.5, -0.5)

    if use_default_ticks:
        ax.xaxis.set_major_locator(IndexLocator())
        ax.yaxis.set_major_locator(IndexLocator())


class IndexLocator(ticker.Locator):

    def __init__(self, max_ticks=10):
        self.max_ticks = max_ticks

    def __call__(self):
        """Return the locations of the ticks."""
        dmin, dmax = self.axis.get_data_interval()
        if dmax < self.max_ticks:
            step = 1
        else:
            step = np.ceil(dmax / self.max_ticks)
        return self.raise_if_exceeds(np.arange(0, dmax, step))

########NEW FILE########
__FILENAME__ = plot2rst
"""
Generate reStructuredText example from python files.

Generate the rst files for the examples by iterating over the python
example files. Files that generate images should start with 'plot'.

To generate your own examples, add ``'mpltools.sphinx.plot2rst'`` to the list
of ``extensions`` in your Sphinx configuration file. In addition, make sure the
example directory(ies) in `plot2rst_paths` (see below) points to a directory
with examples named `plot_*.py` and include an `index.rst` file.

This code was adapted from scikits-image, which took it from scikits-learn.


Options
-------
The ``plot2rst`` extension accepts the following options:

plot2rst_paths : length-2 tuple, or list of tuples
    Tuple or list of tuples of paths to (python plot, generated rst) files,
    i.e. (source, destination).  Note that both paths are relative to Sphinx
    'source' directory. Defaults to ('../examples', 'auto_examples')

plot2rst_rcparams : dict
    Matplotlib configuration parameters. See
    http://matplotlib.sourceforge.net/users/customizing.html for details.

plot2rst_default_thumb : str
    Path (relative to doc root) of default thumbnail image.

plot2rst_thumb_scale : float
    Scale factor for thumbnail. Defaults to 0.2, which scales the thumbnail to
    1/5th the original size.

plot2rst_plot_tag : str
    When this tag is found in the example file, the current plot is saved and
    tag is replaced with plot path. Defaults to 'PLOT2RST.current_figure'.

plot2rst_index_name : str
    The basename for gallery index file. Each example directory should have an
    index file---typically containing nothing more than a simple header. Note
    that the reStructuredText extension (e.g., 'txt', 'rst') is taken from the
    default extension set for the Sphinx project, so you should not specify
    the extension as part of this name. Defaults to 'index'.

plot2rst_flags : dict
    Flags that can be set in gallery indexes or python example files. See
    Flags_ section below for details.

Flags
-----
You can add flags to example files by added a code comment with the prefix ``#PLOT2RST:`. Flags are specified as key-value pairs; for example::

    #PLOT2RST: auto_plots = False

There are also reStructuredText flags, which can be added like::

    .. plot2rst_gallery_style:: list

Some flags can only be defined in the python example file, while others can only be defined in the gallery index. The following flags are defined:

auto_plots : bool
    If no plot tags are found in the example, `auto_plots` adds all figures to
    the end of the example. Defaults to True.

plot2rst_gallery_style : {'thumbnail' | 'list'}
    Display examples as a thumbnail gallery or as a list of titles. This option
    can also be set at the directory-level by adding::

        .. plot2rst_gallery_style:: list

    to the gallery index. Defaults to 'thumbnail'.


Note: If flags are added at the top of the file, then they are stripped from
the resulting reStructureText output. If they appear after the first text or
code block, then will show up in the generated example.


Suggested CSS definitions
-------------------------

    div.body h2 {
        border-bottom: 1px solid #BBB;
        clear: left;
    }

    /*---- example gallery ----*/

    .gallery.figure {
        float: left;
        width: 200px;
        height: 200px;
    }

    .gallery.figure img{
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 180px;
    }

    .gallery.figure .caption {
        text-align: center !important;
    }

"""
import os
import shutil
import token
import tokenize

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import image


CODE_LINK = """

**Python source code:** :download:`download <{0}>`
(generated using ``mpltools`` |version|)

"""

TOCTREE_TEMPLATE = """
.. toctree::
   :hidden:

   %s

"""

IMAGE_TEMPLATE = """
.. image:: images/%s
    :align: center

"""

GALLERY_IMAGE_TEMPLATE = """
.. figure:: %(thumb)s
   :figclass: gallery
   :target: ./%(source)s.html

   :ref:`example_%(link_name)s`

"""

GALLERY_LIST_TEMPLATE = """
* :ref:`example_%(link_name)s`
"""


FLAG_PREFIX = '#PLOT2RST:'

class Path(str):
    """Path object for manipulating directory and file paths."""

    def __init__(self, path):
        super(Path, self).__init__(path)

    @property
    def isdir(self):
        return os.path.isdir(self)

    @property
    def exists(self):
        """Return True if path exists"""
        return os.path.exists(self)

    def pjoin(self, *args):
        """Join paths. `p` prefix prevents confusion with string method."""
        return self.__class__(os.path.join(self, *args))

    def psplit(self):
        """Split paths. `p` prefix prevents confusion with string method."""
        return [self.__class__(p) for p in os.path.split(self)]

    def makedirs(self):
        if not self.exists:
            os.makedirs(self)

    def listdir(self):
        return os.listdir(self)

    def format(self, *args, **kwargs):
        return self.__class__(super(Path, self).format(*args, **kwargs))

    def __add__(self, other):
        return self.__class__(super(Path, self).__add__(other))

    def __iadd__(self, other):
        return self.__add__(other)


def setup(app):
    app.connect('builder-inited', generate_example_galleries)

    app.add_config_value('plot2rst_paths',
                         ('../examples', 'auto_examples'), True)
    app.add_config_value('plot2rst_rcparams', {}, True)
    app.add_config_value('plot2rst_default_thumb', None, True)
    app.add_config_value('plot2rst_thumb_scale', 0.2, True)
    app.add_config_value('plot2rst_plot_tag', 'PLOT2RST.current_figure', True)
    app.add_config_value('plot2rst_index_name', 'index', True)
    app.add_config_value('plot2rst_gallery_style', 'thumbnail', True)
    # NOTE: plot2rst_flags gets set with defaults later so that keys that are
    # not set in config file still get set to the desired defaults.
    app.add_config_value('plot2rst_flags', {}, True)


def generate_example_galleries(app):
    cfg = app.builder.config

    default_flags = {'auto_plots': True,
                     'gallery_style': 'thumbnail'}
    default_flags.update(cfg.plot2rst_flags)
    cfg.plot2rst_flags = default_flags

    doc_src = Path(os.path.abspath(app.builder.srcdir)) # path/to/doc/source

    if isinstance(cfg.plot2rst_paths, tuple):
        cfg.plot2rst_paths = [cfg.plot2rst_paths]
    for src_dest in cfg.plot2rst_paths:
        plot_path, rst_path = [Path(p) for p in src_dest]
        example_dir = doc_src.pjoin(plot_path)
        rst_dir = doc_src.pjoin(rst_path)
        generate_examples_and_gallery(example_dir, rst_dir, cfg)


def generate_examples_and_gallery(example_dir, rst_dir, cfg):
    """Generate rst from examples and create gallery to showcase examples."""
    if not example_dir.exists:
        print "No example directory found at", example_dir
        return
    rst_dir.makedirs()

    # we create an index.rst with all examples
    gallery_index = file(rst_dir.pjoin('index'+cfg.source_suffix), 'w')

    # Here we don't use an os.walk, but we recurse only twice: flat is
    # better than nested.
    write_gallery(gallery_index, example_dir, rst_dir, cfg)
    for d in sorted(example_dir.listdir()):
        example_sub = example_dir.pjoin(d)
        if example_sub.isdir:
            rst_sub = rst_dir.pjoin(d)
            rst_sub.makedirs()
            write_gallery(gallery_index, example_sub, rst_sub, cfg, depth=1)
    gallery_index.flush()


def write_gallery(gallery_index, src_dir, rst_dir, cfg, depth=0):
    """Generate the rst files for an example directory, i.e. gallery.

    Write rst files from python examples and add example links to gallery.

    Parameters
    ----------
    gallery_index : file
        Index file for plot gallery.
    src_dir : 'str'
        Source directory for python examples.
    rst_dir : 'str'
        Destination directory for rst files generated from python examples.
    cfg : config object
        Sphinx config object created by Sphinx.
    """
    index_name = cfg.plot2rst_index_name + cfg.source_suffix
    gallery_template = src_dir.pjoin(index_name)
    if not os.path.exists(gallery_template):
        print src_dir
        print 80*'_'
        print ('Example directory %s does not have a %s file'
                        % (src_dir, index_name))
        print 'Skipping this directory'
        print 80*'_'
        return
    flags = get_flags_from_rst(gallery_template)

    gallery_description = file(gallery_template).read()
    gallery_index.write('\n\n%s\n\n' % gallery_description)

    rst_dir.makedirs()
    examples = [fname for fname in sorted(src_dir.listdir(), key=_plots_first)
                      if fname.endswith('py')]
    ex_names = [ex[:-3] for ex in examples] # strip '.py' extension
    if depth == 0:
        sub_dir = Path('')
    else:
        sub_dir_list = src_dir.psplit()[-depth:]
        sub_dir = Path('/'.join(sub_dir_list) + '/')
    gallery_index.write(TOCTREE_TEMPLATE % (sub_dir + '\n   '.join(ex_names)))

    for src_name in examples:
        write_example(src_name, src_dir, rst_dir, cfg)

        link_name = sub_dir.pjoin(src_name)
        link_name = link_name.replace(os.path.sep, '_')
        if link_name.startswith('._'):
            link_name = link_name[2:]

        info = {}
        info['source'] = sub_dir + src_name[:-3]
        info['link_name'] = link_name

        gallery_style = flags.get('plot2rst_gallery_style',
                                  cfg.plot2rst_flags['gallery_style'])
        if gallery_style == 'thumbnail':
            thumb_name = src_name[:-3] + '.png'
            info['thumb'] = sub_dir.pjoin('images/thumb', thumb_name)
            gallery_index.write(GALLERY_IMAGE_TEMPLATE % info)
        elif gallery_style == 'list':
            gallery_index.write(GALLERY_LIST_TEMPLATE % info)


def get_flags_from_rst(rst_file):
    """Return dict of plot2rst flags found in reStructuredText file.

    Flags should have the form:

        .. plot2rst_*:: value

    """
    flags = {}
    with open(rst_file) as f:
        for line in f:
            if line.startswith('.. plot2rst'):
                line = line.lstrip('.. ')
                k, v = [word.strip() for word in line.split('::')]
                flags[k] = v
    return flags


def _plots_first(fname):
    """Decorate filename so that examples with plots are displayed first."""
    if not (fname.startswith('plot') and fname.endswith('.py')):
        return 'zz' + fname
    return fname


def write_example(src_name, src_dir, rst_dir, cfg):
    """Write rst file from a given python example.

    Parameters
    ----------
    src_name : str
        Name of example file.
    src_dir : 'str'
        Source directory for python examples.
    rst_dir : 'str'
        Destination directory for rst files generated from python examples.
    cfg : config object
        Sphinx config object created by Sphinx.
    """
    last_dir = src_dir.psplit()[-1]
    # to avoid leading . in file names, and wrong names in links
    if last_dir == '.' or last_dir == 'examples':
        last_dir = Path('')
    else:
        last_dir += '_'

    src_path = src_dir.pjoin(src_name)
    example_file = rst_dir.pjoin(src_name)
    shutil.copyfile(src_path, example_file)

    image_dir = rst_dir.pjoin('images')
    thumb_dir = image_dir.pjoin('thumb')
    image_dir.makedirs()
    thumb_dir.makedirs()

    base_image_name = os.path.splitext(src_name)[0]
    image_path = image_dir.pjoin(base_image_name + '_{0}.png')

    basename, py_ext = os.path.splitext(src_name)
    rst_path = rst_dir.pjoin(basename + cfg.source_suffix)

    if _plots_are_current(src_path, image_path) and rst_path.exists:
        return

    flags = cfg.plot2rst_flags.copy()
    blocks, new_flags = split_code_and_text_blocks(example_file)
    flags.update(new_flags)

    while True:
        head = blocks[0][2]
        if head.startswith('#!') or head.startswith(FLAG_PREFIX):
            blocks.pop(0) # don't add shebangs or flags to rst file.
        else:
            break

    # Note that `process_blocks` executes the source, so plots are now 'active'
    figure_list, rst = process_blocks(blocks, src_path, image_path, cfg)

    rst_link = '.. _example_%s:\n\n' % (last_dir + src_name)
    example_rst = ''.join([rst_link, rst])

    has_inline_plots = any(cfg.plot2rst_plot_tag in b[2] for b in blocks)
    if not has_inline_plots and flags['auto_plots']:
        # Show all plots at the end of the example
        if len(plt.get_fignums()) > 0:
            figure_list = save_all_figures(image_path)
            img_blocks = [IMAGE_TEMPLATE % f.lstrip('/') for f in figure_list]
            example_rst += ''.join(img_blocks)
    plt.close('all')

    example_rst += CODE_LINK.format(src_name)

    f = open(rst_path,'w')
    f.write(example_rst)
    f.flush()

    thumb_path = thumb_dir.pjoin(src_name[:-3] + '.png')
    if figure_list:
        first_image_file = image_dir.pjoin(figure_list[0].lstrip('/'))
        if first_image_file.exists:
            thumb_scale = cfg.plot2rst_thumb_scale
            image.thumbnail(first_image_file, thumb_path, thumb_scale)

    if not thumb_path.exists:
        if cfg.plot2rst_default_thumb is None:
            print "WARNING: No plots found and default thumbnail not defined."
            print "Specify 'plot2rst_default_thumb' in Sphinx config file."
        else:
            shutil.copy(cfg.plot2rst_default_thumb, thumb_path)


def _plots_are_current(src_path, image_path):
    first_image_file = Path(image_path.format(1))
    needs_replot = (not first_image_file.exists or
                    _mod_time(first_image_file) <= _mod_time(src_path))
    return not needs_replot


def _mod_time(file_path):
    return os.stat(file_path).st_mtime


def split_code_and_text_blocks(source_file):
    """Return list with source file separated into code and text blocks.

    Returns
    -------
    blocks : list of (label, (start, end+1), content)
        List where each element is a tuple with the label ('text' or 'code'),
        the (start, end+1) line numbers, and content string of block.
    flags : dict
        Option flags for plot2rst that were found in the source file.
    """
    block_edges, idx_first_text_block, flags = analyze_blocks(source_file)

    with open(source_file) as f:
        source_lines = f.readlines()

    if idx_first_text_block is None:
        blocks = [('code', (1, len(source_lines)), ''.join(source_lines))]
        return blocks, flags

    # Every other block should be a text block
    idx_text_block = np.arange(idx_first_text_block, len(block_edges), 2)
    blocks = []
    slice_ranges = zip(block_edges[:-1], block_edges[1:])
    for i, (start, end) in enumerate(slice_ranges):
        block_label = 'text' if i in idx_text_block else 'code'
        # subtract 1 from indices b/c line numbers start at 1, not 0
        content = ''.join(source_lines[start-1:end-1])
        blocks.append((block_label, (start, end), content))
    return blocks, flags


def analyze_blocks(source_file):
    """Return starting line numbers of code and text blocks

    Returns
    -------
    block_edges : list of int
        Line number for the start of each block. Note the
    idx_first_text_block : {0 | 1}
        0 if first block is text then, else 1 (second block better be text).
    flags : dict
        Option flags for plot2rst that were found in the source file.
    """
    flags = {}
    block_edges = []
    with open(source_file) as f:
        token_iter = tokenize.generate_tokens(f.readline)
        for token_tuple in token_iter:
            t_id, t_str, (srow, scol), (erow, ecol), src_line = token_tuple
            tok_name = token.tok_name[t_id]
            if tok_name == 'STRING' and scol == 0:
                # Add one point to line after text (for later slicing)
                block_edges.extend((srow, erow+1))
            elif tok_name == 'COMMENT' and t_str.startswith(FLAG_PREFIX):
                flag_args = t_str.lstrip(FLAG_PREFIX).split('=')
                if not len(flag_args) == 2:
                    raise ValueError("Flags must be key-value pairs.")
                key = flag_args[0].strip()
                flags[key] = eval(flag_args[1])
    idx_first_text_block = 0
    if not block_edges: # no text blocks
        idx_first_text_block = None
    else:
        # when example doesn't start with text block.
        if not block_edges[0] == 1:
            block_edges.insert(0, 1)
            idx_first_text_block = 1
        # when example doesn't end with text block.
        if not block_edges[-1] == erow: # iffy: I'm using end state of loop
            block_edges.append(erow)
    return block_edges, idx_first_text_block, flags


def process_blocks(blocks, src_path, image_path, cfg):
    """Run source, save plots as images, and convert blocks to rst.

    Parameters
    ----------
    blocks : list of block tuples
        Code and text blocks from example. See `split_code_and_text_blocks`.
    src_path : str
        Path to example file.
    image_path : str
        Path where plots are saved (format string which accepts figure number).
    cfg : config object
        Sphinx config object created by Sphinx.

    Returns
    -------
    figure_list : list
        List of figure names saved by the example.
    rst_text : str
        Text with code wrapped code-block directives.
    """
    src_dir, src_name = src_path.psplit()
    if not src_name.startswith('plot'):
        convert_func = dict(code=codestr2rst, text=docstr2rst)
        rst_blocks = [convert_func[blabel](bcontent)
                      for i, (blabel, brange, bcontent) in enumerate(blocks)]
        return [], '\n'.join(rst_blocks)

    # index of blocks which have inline plots
    inline_tag = cfg.plot2rst_plot_tag
    idx_inline_plot = [i for i, b in enumerate(blocks)
                       if inline_tag in b[2]]

    image_dir, image_fmt_str = image_path.psplit()

    figure_list = []
    plt.rcdefaults()
    plt.rcParams.update(cfg.plot2rst_rcparams)
    plt.close('all')

    example_globals = {}
    rst_blocks = []
    fig_num = 1
    for i, (blabel, brange, bcontent) in enumerate(blocks):
        if blabel == 'code':
            exec(bcontent, example_globals)
            rst_blocks.append(codestr2rst(bcontent))
        else:
            if i in idx_inline_plot:
                plt.savefig(image_path.format(fig_num))
                figure_name = image_fmt_str.format(fig_num)
                fig_num += 1
                figure_list.append(figure_name)
                figure_link = os.path.join('images', figure_name)
                bcontent = bcontent.replace(inline_tag, figure_link)
            rst_blocks.append(docstr2rst(bcontent))
    return figure_list, '\n'.join(rst_blocks)


def codestr2rst(codestr):
    """Return reStructuredText code block from code string"""
    code_directive = ".. code-block:: python\n\n"
    indented_block = '\t' + codestr.replace('\n', '\n\t')
    return code_directive + indented_block


def docstr2rst(docstr):
    """Return reStructuredText from docstring"""
    idx_whitespace = len(docstr.rstrip()) - len(docstr)
    whitespace = docstr[idx_whitespace:]
    return eval(docstr) + whitespace


def save_all_figures(image_path):
    """Save all matplotlib figures.

    Parameters
    ----------
    image_path : str
        Path where plots are saved (format string which accepts figure number).
    """
    figure_list = []
    image_dir, image_fmt_str = image_path.psplit()
    fig_mngr = matplotlib._pylab_helpers.Gcf.get_all_fig_managers()
    for fig_num in (m.num for m in fig_mngr):
        # Set the fig_num figure as the current figure as we can't
        # save a figure that's not the current figure.
        plt.figure(fig_num)
        plt.savefig(image_path.format(fig_num))
        figure_list.append(image_fmt_str.format(fig_num))
    return figure_list


########NEW FILE########
__FILENAME__ = core
import os
import glob
import copy

import numpy as np
import matplotlib.pyplot as plt

from .. import _config


__all__ = ['use', 'available', 'lib', 'baselib']


def use(name=None, use_baselib=False):
    """Use matplotlib rc parameters from a pre-defined name or from a file.

    Parameters
    ----------
    name : str or list of str
        Name of style. For list of available styles see `style.available`.
        If given a list, each style is applied from first to last in the list.

    use_baselib : bool
        If True, only use styles defined in `mpltools/style` (without user's
        customization).
    """
    if np.isscalar(name):
        name = [name]
    for s in name:
        if use_baselib:
            plt.rcParams.update(baselib[s])
        else:
            plt.rcParams.update(lib[s])


def load_base_library():
    """Load style library from package"""
    library = dict()
    style_dir = os.path.abspath(os.path.dirname(__file__))
    library.update(read_style_directory(style_dir))
    return library


def update_user_library(base_library):
    """Update style library with user-defined rc files"""

    library = copy.deepcopy(base_library)

    stylelib_path = os.path.expanduser('~/.mplstylelib')
    if os.path.exists(stylelib_path) and os.path.isdir(stylelib_path):
        styles = read_style_directory(stylelib_path)
        update_nested_dict(library, styles)

    for cfg in _config.iter_paths(['~/.mplstyle', './mplstyle']):
        styles = read_style_dict(cfg)
        update_nested_dict(library, styles)
    return library



def read_style_directory(style_dir):
    styles = dict()
    library_glob = os.path.join(style_dir, '*.rc')
    style_files = glob.glob(library_glob)

    for style_path in style_files:
        filename = os.path.basename(style_path)
        cfg = _config.read(style_path)
        # remove last three letters, which are '.rc'
        styles[filename[:-3]] = cfg.dict()

    return styles


def read_style_dict(cfg):
    """Return dict of styles read from config dict.

    Sections in style file are set as top-level keys of the returned dict.
    """
    style = {}
    # update all settings with any global settings.
    if 'global' in cfg:
        cfg_global = cfg.pop('global')
        for rc_dict in style.itervalues():
            rc_dict.update(cfg_global)
    return update_nested_dict(style, cfg)


def update_nested_dict(main_dict, new_dict):
    """Update nested dict (only level of nesting) with new values.


    Unlike dict.update, this assumes that the values of the parent dict are
    dicts, so you shouldn't replace the nested dict if it already exists.
    Instead you should update the sub-dict.
    """
    # update named styles specified by user
    for name, rc_dict in new_dict.iteritems():
        if name in main_dict:
            main_dict[name].update(rc_dict)
        else:
            main_dict[name] = rc_dict
    return main_dict


# Load style libraries
# ====================
baselib = load_base_library()
lib = update_user_library(baselib)
available = lib.keys()


########NEW FILE########
__FILENAME__ = util
import functools
import warnings

from . import layout


__all__ = ['deprecated', 'figure', 'figaspect', 'figsize']


class deprecated(object):
    """Decorator to mark deprecated functions with warning.

    Adapted from <http://wiki.python.org/moin/PythonDecoratorLibrary>.

    Parameters
    ----------
    alt_func : str
        If given, tell user what function to use instead.
    behavior : {'warn', 'raise'}
        Behavior during call to deprecated function: 'warn' = warn user that
        function is deprecated; 'raise' = raise error.
    """

    def __init__(self, alt_func=None, behavior='warn'):
        self.alt_func = alt_func
        self.behavior = behavior

    def __call__(self, func):

        msg = "Call to deprecated function ``%s``." % func.__name__
        alt_msg = ''
        if self.alt_func is not None:
            alt_msg = " Use ``%s`` instead." % self.alt_func
            msg = msg + alt_msg
        func.__doc__ = "Deprecated." + alt_msg

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if self.behavior == 'warn':
                warnings.warn_explicit(msg,
                    category=DeprecationWarning,
                    filename=func.func_code.co_filename,
                    lineno=func.func_code.co_firstlineno + 1)
            elif self.behavior == 'raise':
                raise DeprecationWarning(msg)
            return func(*args, **kwargs)

        return wrapped


@deprecated('layout.figure')
def figure(aspect_ratio=1.3, **kwargs):
    print "NOTE: `layout.figure` uses inverse definition of `aspect_ratio`."
    aspect_ratio = 1.0 / aspect_ratio
    return layout.figure(aspect_ratio, **kwargs)


@deprecated('layout.figaspect')
def figaspect(*args, **kwargs):
    return layout.figaspect(*args, **kwargs)


@deprecated('layout.figaspect')
def figsize(aspect_ratio=1.3, **kwargs):
    print "NOTE: `layout.figaspect` uses inverse definition of `aspect_ratio`."
    return layout.figaspect(1./aspect_ratio, **kwargs)


########NEW FILE########
__FILENAME__ = rectangle_selector
import numpy as np

import matplotlib.widgets as mwidgets
from matplotlib import lines


class RectangleSelector(mwidgets.RectangleSelector):
    """Widget widget for selecting a rectangular region in a plot.

    Unlike :class:`matplotlib.widgets.RectangleSelector`, this widget remains
    visible after selection and can be resized using corner and edge handles.

    After making the desired selection, press "Enter" to accept the selection
    and call the `onselect` callback function.

    Note the difference from :class:`matplotlib.widgets.RectangleSelector`:
    The callback method `onselect` is called on "Enter", *not* after release of
    the mouse button.  In addition, the `onselect` function now takes a single
    argument `extents`, which is a tuple specifying (xmin, xmax, ymin, ymax) of
    the rectangle.

    TODO: Allow rectangle to flip over itself when resizing.

    Parameters
    ----------
    ax : :class:`matplotlib.axes.Axes

    onselect : function
        Function accepting rectangle extents as the only argument. If None,
        print extents of rectangle.

    mindist : float
        Minimum distance in pixels for selection of a control (i.e. corner or
        edge) handle.

    rectprops : dict
        Properties for :class:`matplotlib.patches.Rectangle`. This class
        redefines defaults in :class:`matplotlib.widgets.RectangleSelector`.

    kwargs : see :class:`matplotlib.widgets.RectangleSelector`.

    Attributes
    ----------
    extents : tuple
        Rectangle extents: (xmin, xmax, ymin, ymax).
    """

    def __init__(self, ax, onselect=None, rectprops=None, mindist=10, **kwargs):

        if 'drawtype' in kwargs and not kwargs['drawtype'] == 'box':
            raise ValueError('"drawtype" must be "box"')

        self.mindist = mindist
        self.active_handle = None

        rectprops_defaults = dict(edgecolor='k', facecolor='r', alpha=0.2)
        if rectprops is None:
            rectprops = {}
        rectprops.update(rectprops_defaults)

        mwidgets.RectangleSelector.__init__(self, ax,
                                            self._on_mouse_release,
                                            rectprops=rectprops,
                                            **kwargs)
        # Alias rectangle attribute.
        self._rect = self.to_draw

        if onselect is None:
            def onselect(extents):
                print "(xmin=%.3g, xmax=%.3g, ymin=%.3g, ymax=%.3g)" % extents
        self.onenter = onselect

        handle_props = dict(mfc='none', mec='k', ls='none', alpha=0.7,
                            visible=False)

        self._corner_order = ['NW', 'NE', 'SE', 'SW']
        xc, yc = self.corner_coords
        self._corner_handles = lines.Line2D(xc, yc, marker='o', **handle_props)
        # replace with widget method for clean up
        self.ax.add_line(self._corner_handles)

        self._edge_order = ['W', 'N', 'E', 'S']
        xe, ye = self.edge_coords
        self._edge_handles = lines.Line2D(xe, ye, marker='s', **handle_props)
        self.ax.add_line(self._edge_handles)

        self.connect_event('key_press_event', self.onkeypress)


    @property
    def _rect_bbox(self):
        x0 = self._rect.get_x()
        y0 = self._rect.get_y()
        width = self._rect.get_width()
        height = self._rect.get_height()
        return x0, y0, width, height

    @property
    def corner_coords(self):
        """Corners of rectangle from lower left, moving clockwise."""
        x0, y0, width, height = self._rect_bbox
        xc = x0, x0 + width, x0 + width, x0
        yc = y0, y0, y0 + height, y0 + height
        return xc, yc

    @property
    def edge_coords(self):
        """Midpoint of rectangle edges from lower left, moving clockwise."""
        x0, y0, width, height = self._rect_bbox
        w = width / 2.
        h = height / 2.
        xe = x0, x0 + w, x0 + width, x0 + w
        ye = y0 + h, y0, y0 + h, y0 + height
        return xe, ye

    @property
    def extents(self):
        xmin = min(self.x0, self.x1)
        xmax = max(self.x0, self.x1)
        ymin = min(self.y0, self.y1)
        ymax = max(self.y0, self.y1)
        return xmin, xmax, ymin, ymax

    def _on_mouse_release(self, epress=None, erelease=None):
        """Method called by widgets.RectangleSelector when mouse released."""
        x0, y0, width, height = self._rect_bbox
        self.x0 = x0
        self.x1 = x0 + width
        self.y0 = y0
        self.y1 = y0 + height

    def release(self, event):
        mwidgets.RectangleSelector.release(self, event)
        # Undo hiding of rectangle and redraw.
        self.set_visible(True)
        self.update()
        self.set_animated(False)

    def press(self, event):
        p = event.x, event.y # cursor coords

        dist = []
        for h in (self._corner_handles, self._edge_handles):
            pts = np.transpose((h.get_xdata(), h.get_ydata()))
            pts = self.ax.transData.transform(pts)
            diff = pts - ((event.x, event.y))
            dist.append(np.sqrt(np.sum(diff**2, axis=1)))

        dist = np.asarray(dist)
        idx = np.argmin(dist)

        close_to_handle = dist.flat[idx] < self.mindist
        if idx < 4:
            handle = 'corner'
        else:
            handle = 'edge'
            idx -= 4

        if close_to_handle and handle == 'corner':
            self.active_handle = self._corner_order[idx]
        elif close_to_handle and handle == 'edge':
            self.active_handle = self._edge_order[idx]
        else:
            self.active_handle = None

        # Clear previous rectangle before drawing new rectangle.
        self.set_animated(True)
        if not close_to_handle:
            self.set_visible(False)
            self.update()
            self.set_visible(True)

        mwidgets.RectangleSelector.press(self, event)

    def onkeypress(self, event):
        if event.key == 'enter':
            self.onenter(self.extents)
            self.set_visible(False)
            self.update()

    def onmove(self, event):

        if self.eventpress is None or self.ignore(event):
            return

        if self.active_handle == None:
            xmin, ymin = event.xdata, event.ydata
            xmax = self.eventpress.xdata
            ymax = self.eventpress.ydata
        else:
            xmin, ymin, width, height = self._rect_bbox
            xmax = xmin + width
            ymax = ymin + height

            if self.active_handle in ('W', 'SW', 'NW'):
                xmin = event.xdata
            if self.active_handle in ('E', 'SE', 'NE'):
                xmax = event.xdata
            if self.active_handle in ('N', 'NW', 'NE'):
                ymin = event.ydata
            if self.active_handle in ('S', 'SW', 'SE'):
                ymax = event.ydata

        # Order by value instead of time.
        if xmin > xmax:
            xmin, xmax = xmax, xmin
        if ymin>ymax:
            ymin, ymax = ymax, ymin

        self._rect.set_x(xmin)
        self._rect.set_y(ymin)
        self._rect.set_width(xmax-xmin)
        self._rect.set_height(ymax-ymin)

        xc, yc = self.corner_coords
        self._corner_handles.set_xdata(xc)
        self._corner_handles.set_ydata(yc)
        xe, ye = self.edge_coords
        self._edge_handles.set_xdata(xe)
        self._edge_handles.set_ydata(ye)

        self.update()
        return False

    def set_visible(self, val):
        self._rect.set_visible(val)
        self._corner_handles.set_visible(val)
        self._edge_handles.set_visible(val)

    def set_animated(self, val):
        self._rect.set_animated(val)
        self._corner_handles.set_animated(val)
        self._edge_handles.set_animated(val)


    def update(self):
        if self.useblit:
            if self.background is not None:
                self.canvas.restore_region(self.background)
            self.ax.draw_artist(self._rect)
            self.ax.draw_artist(self._edge_handles)
            self.ax.draw_artist(self._corner_handles)
            self.canvas.blit(self.ax.bbox)
        else:
            self.canvas.draw_idle()
        return False


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    f, ax = plt.subplots()
    ax.imshow(np.random.random((20, 20)), interpolation='nearest')

    rect_select = RectangleSelector(ax, useblit=True)
    plt.show()
    print "Final selection:",
    rect_select.onenter(rect_select.extents)


########NEW FILE########
__FILENAME__ = slider
import matplotlib.widgets as mwidgets


class Slider(mwidgets.Slider):
    """Slider widget to select a value from a floating point range.

    Parameters
    ----------
    ax : :class:`~matplotlib.axes.Axes` instance
        The parent axes for the widget
    value_range : (float, float)
        (min, max) value allowed for value.
    label : str
        The slider label.
    value : float
        Initial value. If None, set to value in middle of value range.
    on_slide : function
        Callback function for slide event. Function should expect slider value.
    value_fmt : str
        Format string for formatting the slider text.
    slidermin, slidermax : float
        Used to contrain the value of this slider to the values
        of other sliders.
    dragging : bool
        If True, slider is responsive to mouse.
    pad : float
        Padding (in axes coordinates) between `label`/`value_fmt` and slider.

    Attributes
    ----------
    value : float
        Current slider value.

    """

    def __init__(self, ax, value_range, label='', value=None, on_slide=None,
                 value_fmt='%1.2f', slidermin=None, slidermax=None,
                 dragging=True, pad=0.02):

        mwidgets.AxesWidget.__init__(self, ax)

        self.valmin, self.valmax = value_range
        if value is None:
            value = 0.5 * (self.valmin + self.valmax)
        self.val = value
        self.valinit = value
        self.valfmt = value_fmt

        y0 = 0.5
        x_low = [self.valmin, value]
        x_high = [value, self.valmax]

        self.line_low, = ax.plot(x_low, [y0, y0], color='0.5', lw=2)
        self.line_high, = ax.plot(x_high, [y0, y0], color='0.7', lw=2)
        self.val_handle, = ax.plot(value, y0, 'o',
                                   mec='0.4', mfc='0.6', markersize=8)

        ax.set_xlim(value_range)
        ax.set_navigate(False)
        ax.set_axis_off()

        self.connect_event('button_press_event', self._update)
        self.connect_event('button_release_event', self._update)
        if dragging:
            self.connect_event('motion_notify_event', self._update)

        self.label = ax.text(-pad, y0, label, transform=ax.transAxes,
                             verticalalignment='center',
                             horizontalalignment='right')

        self.show_value = False if value_fmt is None else True
        if self.show_value:
            self.valtext = ax.text(1 + pad, y0, value_fmt%value,
                                   transform=ax.transAxes,
                                   verticalalignment='center',
                                   horizontalalignment='left')

        self.slidermin = slidermin
        self.slidermax = slidermax
        self.drag_active  = False

        self.cnt = 0
        self.observers = {}
        if on_slide is not None:
            self.on_changed(on_slide)

        # Attributes for matplotlib.widgets.Slider compatibility
        self.closedmin = self.closedmax = True

    @property
    def value(self):
        return self.val

    @value.setter
    def value(self, value):
        self.val = value
        self.line_low.set_xdata([self.valmin, value])
        self.line_high.set_xdata([value, self.valmax])
        self.val_handle.set_xdata([value])
        if self.show_value:
            self.valtext.set_text(self.valfmt % value)

    def set_val(self, value):
        """Set value of slider."""
        # Override matplotlib.widgets.Slider to update graphics objects.

        self.value = value

        if self.drawon:
            self.ax.figure.canvas.draw()
        if not self.eventson:
            return

        for cid, func in self.observers.iteritems():
            func(value)


if __name__ == '__main__':
    import numpy as np
    import matplotlib.pyplot as plt

    ax = plt.subplot2grid((10, 1), (0, 0), rowspan=8)
    ax_slider = plt.subplot2grid((10, 1), (9, 0))

    a0 = 5
    x = np.arange(0.0, 1.0, 0.001)
    y = np.sin(6 * np.pi * x)

    line, = ax.plot(x, a0 * y, lw=2, color='red')
    ax.axis([x.min(), x.max(), -10, 10])

    def update(val):
        amp = samp.value
        line.set_ydata(amp * y)

    samp = Slider(ax_slider, (0.1, 10.0), on_slide=update,
                  label='Amplitude:', value=a0)

    plt.show()


########NEW FILE########
__FILENAME__ = _config
"""
Configuration utilities.
"""
import os
from configobj import ConfigObj


__all__ = ['iter_paths', 'read', 'config']


def iter_paths(config_paths):
    for path in config_paths:
        path = os.path.expanduser(path)

        if not os.path.exists(path):
            continue

        yield read(path)


def read(path):
    """Return dict-like object of config parameters from file path."""
    return ConfigObj(path, unrepr=True)


# Set mpltools specific properties (i.e., not matplotlib properties).
config = {}
pkgdir = os.path.abspath(os.path.dirname(__file__))
for cfg in iter_paths([os.path.join(pkgdir, 'mpltoolsrc'),
                       '~/.mpltoolsrc',
                       './mpltoolsrc']):
    config.update(cfg)



########NEW FILE########
