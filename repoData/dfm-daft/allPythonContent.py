__FILENAME__ = daft
__all__ = ["PGM", "Node", "Edge", "Plate"]


__version__ = "0.0.3"


import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.patches import FancyArrow
from matplotlib.patches import Rectangle as Rectangle

import numpy as np


class PGM(object):
    """
    The base object for building a graphical model representation.

    :param shape:
        The number of rows and columns in the grid.

    :param origin:
        The coordinates of the bottom left corner of the plot.

    :param grid_unit: (optional)
        The size of the grid spacing measured in centimeters.

    :param node_unit: (optional)
        The base unit for the node size. This is a number in centimeters that
        sets the default diameter of the nodes.

    :param observed_style: (optional)
        How should the "observed" nodes be indicated? This must be one of:
        ``"shaded"``, ``"inner"`` or ``"outer"`` where ``inner`` and
        ``outer`` nodes are shown as double circles with the second circle
        plotted inside or outside of the standard one, respectively.

    :param node_ec: (optional)
        The default edge color for the nodes.

    :param directed: (optional)
        Should the edges be directed by default?

    :param aspect: (optional)
        The default aspect ratio for the nodes.

    :param label_params: (optional)
        Default node label parameters.

    """
    def __init__(self, shape, origin=[0, 0],
                 grid_unit=2, node_unit=1,
                 observed_style="shaded",
                 line_width=1, node_ec="k",
                 directed=True, aspect=1.0,
                 label_params={}):
        self._nodes = {}
        self._edges = []
        self._plates = []

        self._ctx = _rendering_context(shape=shape, origin=origin,
                                       grid_unit=grid_unit,
                                       node_unit=node_unit,
                                       observed_style=observed_style,
                                       line_width=line_width,
                                       node_ec=node_ec, directed=directed,
                                       aspect=aspect,
                                       label_params=label_params)

    def add_node(self, node):
        """
        Add a :class:`Node` to the model.

        :param node:
            The :class:`Node` instance to add.

        """
        self._nodes[node.name] = node
        return node

    def add_edge(self, name1, name2, directed=None, **kwargs):
        """
        Construct an :class:`Edge` between two named :class:`Node` objects.

        :param name1:
            The name identifying the first node.

        :param name2:
            The name identifying the second node. If the edge is directed,
            the arrow will point to this node.

        :param directed: (optional)
            Should this be a directed edge?

        """
        if directed is None:
            directed = self._ctx.directed

        e = Edge(self._nodes[name1], self._nodes[name2], directed=directed,
                 plot_params=kwargs)
        self._edges.append(e)

        return e

    def add_plate(self, plate):
        """
        Add a :class:`Plate` object to the model.

        """
        self._plates.append(plate)
        return None

    def render(self):
        """
        Render the :class:`Plate`, :class:`Edge` and :class:`Node` objects in
        the model. This will create a new figure with the correct dimensions
        and plot the model in this area.

        """
        self.figure = self._ctx.figure()
        self.ax = self._ctx.ax()

        for plate in self._plates:
            plate.render(self._ctx)

        for edge in self._edges:
            edge.render(self._ctx)

        for name, node in self._nodes.iteritems():
            node.render(self._ctx)

        return self.ax


class Node(object):
    """
    The representation of a random variable in a :class:`PGM`.

    :param name:
        The plain-text identifier for the node.

    :param content:
        The display form of the variable.

    :param x:
        The x-coordinate of the node in *model units*.

    :param y:
        The y-coordinate of the node.

    :param scale: (optional)
        The diameter (or height) of the node measured in multiples of
        ``node_unit`` as defined by the :class:`PGM` object.

    :param aspect: (optional)
        The aspect ratio width/height for elliptical nodes; default 1.

    :param observed: (optional)
        Should this be a conditioned variable?

    :param fixed: (optional)
        Should this be a fixed (not permitted to vary) variable?
        If `True`, modifies or over-rides ``diameter``, ``offset``,
        ``facecolor``, and a few other ``plot_params`` settings.
        This setting conflicts with ``observed``.

    :param offset: (optional)
        The ``(dx, dy)`` offset of the label (in points) from the default
        centered position.

    :param plot_params: (optional)
        A dictionary of parameters to pass to the
        :class:`matplotlib.patches.Ellipse` constructor.

    """
    def __init__(self, name, content, x, y, scale=1, aspect=None,
                 observed=False, fixed=False,
                 offset=[0, 0], plot_params={}, label_params=None):
        # Node style.
        assert not (observed and fixed), \
            "A node cannot be both 'observed' and 'fixed'."
        self.observed = observed
        self.fixed = fixed

        # Metadata.
        self.name = name
        self.content = content

        # Coordinates and dimensions.
        self.x, self.y = x, y
        self.scale = scale
        if self.fixed:
            self.scale /= 6.0
        self.aspect = aspect

        # Display parameters.
        self.plot_params = dict(plot_params)

        # Text parameters.
        self.offset = list(offset)
        if label_params is not None:
            self.label_params = dict(label_params)
        else:
            self.label_params = None

    def render(self, ctx):
        """
        Render the node.

        :param ctx:
            The :class:`_rendering_context` object.

        """
        # Get the axes and default plotting parameters from the rendering
        # context.
        ax = ctx.ax()

        # Resolve the plotting parameters.
        p = dict(self.plot_params)
        p["lw"] = _pop_multiple(p, ctx.line_width, "lw", "linewidth")

        p["ec"] = p["edgecolor"] = _pop_multiple(p, ctx.node_ec,
                                                 "ec", "edgecolor")

        p["fc"] = _pop_multiple(p, "none", "fc", "facecolor")
        fc = p["fc"]

        p["alpha"] = p.get("alpha", 1)

        # And the label parameters.
        if self.label_params is None:
            l = dict(ctx.label_params)
        else:
            l = dict(self.label_params)

        l["va"] = _pop_multiple(l, "center", "va", "verticalalignment")
        l["ha"] = _pop_multiple(l, "center", "ha", "horizontalalignment")

        # Deal with ``fixed`` nodes.
        scale = self.scale
        if self.fixed:
            # MAGIC: These magic numbers should depend on the grid/node units.
            self.offset[1] += 6

            l["va"] = "baseline"
            l.pop("verticalalignment", None)
            l.pop("ma", None)

            if p["fc"] == "none":
                p["fc"] = "k"

        diameter = ctx.node_unit * scale
        if self.aspect is not None:
            aspect = self.aspect
        else:
            aspect = ctx.aspect

        # Set up an observed node. Note the fc INSANITY.
        if self.observed:
            # Update the plotting parameters depending on the style of
            # observed node.
            h = float(diameter)
            w = aspect * float(diameter)
            if ctx.observed_style == "shaded":
                p["fc"] = "0.7"
            elif ctx.observed_style == "outer":
                h = diameter + 0.1 * diameter
                w = aspect * diameter + 0.1 * diameter
            elif ctx.observed_style == "inner":
                h = diameter - 0.1 * diameter
                w = aspect * diameter - 0.1 * diameter
                p["fc"] = fc

            # Draw the background ellipse.
            bg = Ellipse(xy=ctx.convert(self.x, self.y),
                         width=w, height=h, **p)
            ax.add_artist(bg)

            # Reset the face color.
            p["fc"] = fc

        # Draw the foreground ellipse.
        if ctx.observed_style == "inner" and not self.fixed:
            p["fc"] = "none"
        el = Ellipse(xy=ctx.convert(self.x, self.y),
                     width=diameter * aspect, height=diameter, **p)
        ax.add_artist(el)

        # Reset the face color.
        p["fc"] = fc

        # Annotate the node.
        ax.annotate(self.content, ctx.convert(self.x, self.y),
                    xycoords="data",
                    xytext=self.offset, textcoords="offset points",
                    **l)

        return el


class Edge(object):
    """
    An edge between two :class:`Node` objects.

    :param node1:
        The first :class:`Node`.

    :param node2:
        The second :class:`Node`. The arrow will point towards this node.

    :param directed: (optional)
        Should the edge be directed from ``node1`` to ``node2``? In other
        words: should it have an arrow?

    :param plot_params: (optional)
        A dictionary of parameters to pass to the plotting command when
        rendering.

    """
    def __init__(self, node1, node2, directed=True, plot_params={}):
        self.node1 = node1
        self.node2 = node2
        self.directed = directed
        self.plot_params = dict(plot_params)

    def _get_coords(self, ctx):
        """
        Get the coordinates of the line.

        :param conv:
            A callable coordinate conversion.

        :returns:
            * ``x0``, ``y0``: the coordinates of the start of the line.
            * ``dx0``, ``dy0``: the displacement vector.

        """
        # Scale the coordinates appropriately.
        x1, y1 = ctx.convert(self.node1.x, self.node1.y)
        x2, y2 = ctx.convert(self.node2.x, self.node2.y)

        # Aspect ratios.
        a1, a2 = self.node1.aspect, self.node2.aspect
        if a1 is None:
            a1 = ctx.aspect
        if a2 is None:
            a2 = ctx.aspect

        # Compute the distances.
        dx, dy = x2 - x1, y2 - y1
        dist1 = np.sqrt(dy * dy + dx * dx / float(a1 ** 2))
        dist2 = np.sqrt(dy * dy + dx * dx / float(a2 ** 2))

        # Compute the fractional effect of the radii of the nodes.
        alpha1 = 0.5 * ctx.node_unit * self.node1.scale / dist1
        alpha2 = 0.5 * ctx.node_unit * self.node2.scale / dist2

        # Get the coordinates of the starting position.
        x0, y0 = x1 + alpha1 * dx, y1 + alpha1 * dy

        # Get the width and height of the line.
        dx0 = dx * (1. - alpha1 - alpha2)
        dy0 = dy * (1. - alpha1 - alpha2)

        return x0, y0, dx0, dy0

    def render(self, ctx):
        """
        Render the edge in the given axes.

        :param ctx:
            The :class:`_rendering_context` object.

        """
        ax = ctx.ax()

        p = self.plot_params
        p["linewidth"] = _pop_multiple(p, ctx.line_width,
                                       "lw", "linewidth")

        # Add edge annotation.
        if "label" in self.plot_params:
            x, y, dx, dy = self._get_coords(ctx)
            ax.annotate(self.plot_params["label"],
                        [x + 0.5 * dx, y + 0.5 * dy], xycoords="data",
                        xytext=[0, 3], textcoords="offset points",
                        ha="center", va="center")

        if self.directed:
            p["ec"] = _pop_multiple(p, "k", "ec", "edgecolor")
            p["fc"] = _pop_multiple(p, "k", "fc", "facecolor")
            p["head_length"] = p.get("head_length", 0.25)
            p["head_width"] = p.get("head_width", 0.1)

            # Build an arrow.
            ar = FancyArrow(*self._get_coords(ctx), width=0,
                            length_includes_head=True,
                            **p)

            # Add the arrow to the axes.
            ax.add_artist(ar)
            return ar
        else:
            p["color"] = p.get("color", "k")

            # Get the right coordinates.
            x, y, dx, dy = self._get_coords(ctx)

            # Plot the line.
            line = ax.plot([x, x + dx], [y, y + dy], **p)
            return line


class Plate(object):
    """
    A plate to encapsulate repeated independent processes in the model.

    :param rect:
        The rectangle describing the plate bounds in model coordinates.

    :param label: (optional)
        A string to annotate the plate.

    :param label_offset: (optional)
        The x and y offsets of the label text measured in points.

    :param shift: (optional)
        The vertical "shift" of the plate measured in model units. This will
        move the bottom of the panel by ``shift`` units.

    :param position: (optional)
        One of ``"bottom left"`` or ``"bottom right"``.

    :param rect_params: (optional)
        A dictionary of parameters to pass to the
        :class:`matplotlib.patches.Rectangle` constructor.

    """
    def __init__(self, rect, label=None, label_offset=[5, 5], shift=0,
                 position="bottom left", rect_params={}):
        self.rect = rect
        self.label = label
        self.label_offset = label_offset
        self.shift = shift
        self.rect_params = dict(rect_params)
        self.position = position

    def render(self, ctx):
        """
        Render the plate in the given axes.

        :param ctx:
            The :class:`_rendering_context` object.

        """
        ax = ctx.ax()

        s = np.array([0, self.shift])
        r = np.atleast_1d(self.rect)
        bl = ctx.convert(*(r[:2] + s))
        tr = ctx.convert(*(r[:2] + r[2:]))
        r = np.concatenate([bl, tr - bl])

        p = self.rect_params
        p["ec"] = _pop_multiple(p, "k", "ec", "edgecolor")
        p["fc"] = _pop_multiple(p, "none", "fc", "facecolor")
        p["lw"] = _pop_multiple(p, ctx.line_width, "lw", "linewidth")

        rect = Rectangle(r[:2], *r[2:], **p)
        ax.add_artist(rect)

        if self.label is not None:
            offset = np.array(self.label_offset)
            if self.position == "bottom left":
                pos = r[:2]
                ha = "left"
            elif self.position == "bottom right":
                pos = r[:2]
                pos[0] += r[2]
                ha = "right"
                offset[0] -= 2 * offset[0]
            else:
                raise RuntimeError("Unknown positioning string: {0}"
                                   .format(self.position))

            ax.annotate(self.label, pos, xycoords="data",
                        xytext=offset, textcoords="offset points",
                        horizontalalignment=ha)

        return rect


class _rendering_context(object):
    """
    :param shape:
        The number of rows and columns in the grid.

    :param origin:
        The coordinates of the bottom left corner of the plot.

    :param grid_unit:
        The size of the grid spacing measured in centimeters.

    :param node_unit:
        The base unit for the node size. This is a number in centimeters that
        sets the default diameter of the nodes.

    :param observed_style:
        How should the "observed" nodes be indicated? This must be one of:
        ``"shaded"``, ``"inner"`` or ``"outer"`` where ``inner`` and
        ``outer`` nodes are shown as double circles with the second circle
        plotted inside or outside of the standard one, respectively.

    :param node_ec:
        The default edge color for the nodes.

    :param directed:
        Should the edges be directed by default?

    :param aspect:
        The default aspect ratio for the nodes.

    :param label_params:
        Default node label parameters.

    """
    def __init__(self, **kwargs):
        # Save the style defaults.
        self.line_width = kwargs.get("line_width", 1.0)

        # Make sure that the observed node style is one that we recognize.
        self.observed_style = kwargs.get("observed_style", "shaded").lower()
        styles = ["shaded", "inner", "outer"]
        assert self.observed_style in styles, \
            "Unrecognized observed node style: {0}\n".format(
                self.observed_style) \
            + "\tOptions are: {0}".format(", ".join(styles))

        # Set up the figure and grid dimensions.
        self.shape = np.array(kwargs.get("shape", [1, 1]))
        self.origin = np.array(kwargs.get("origin", [0, 0]))
        self.grid_unit = kwargs.get("grid_unit", 2.0)
        self.figsize = self.grid_unit * self.shape / 2.54

        self.node_unit = kwargs.get("node_unit", 1.0)
        self.node_ec = kwargs.get("node_ec", "k")
        self.directed = kwargs.get("directed", True)
        self.aspect = kwargs.get("aspect", 1.0)
        self.label_params = dict(kwargs.get("label_params", {}))

        # Initialize the figure to ``None`` to handle caching later.
        self._figure = None
        self._ax = None

    def figure(self):
        if self._figure is not None:
            return self._figure
        self._figure = plt.figure(figsize=self.figsize)
        return self._figure

    def ax(self):
        if self._ax is not None:
            return self._ax

        # Add a new axis object if it doesn't exist.
        self._ax = self.figure().add_axes((0, 0, 1, 1), frameon=False,
                                          xticks=[], yticks=[])

        # Set the bounds.
        l0 = self.convert(*self.origin)
        l1 = self.convert(*(self.origin + self.shape))
        self._ax.set_xlim(l0[0], l1[0])
        self._ax.set_ylim(l0[1], l1[1])

        return self._ax

    def convert(self, *xy):
        """
        Convert from model coordinates to plot coordinates.

        """
        assert len(xy) == 2
        return self.grid_unit * (np.atleast_1d(xy) - self.origin)


def _pop_multiple(d, default, *args):
    """
    A helper function for dealing with the way that matplotlib annoyingly
    allows multiple keyword arguments. For example, ``edgecolor`` and ``ec``
    are generally equivalent but no exception is thrown if they are both
    used.

    *Note: This function does throw a :class:`ValueError` if more than one
    of the equivalent arguments are provided.*

    :param d:
        A :class:`dict`-like object to "pop" from.

    :param default:
        The default value to return if none of the arguments are provided.

    :param *args:
        The arguments to try to retrieve.

    """
    assert len(args) > 0, "You must provide at least one argument to 'pop'."

    results = []
    for k in args:
        try:
            results.append((k, d.pop(k)))
        except KeyError:
            pass

    if len(results) > 1:
        raise TypeError("The arguments ({0}) are equivalent, you can only "
                        .format(", ".join([k for k, v in results]))
                        + "provide one of them.")

    if len(results) == 0:
        return default

    return results[0][1]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import daft


extensions = ["sphinx.ext.autodoc", "sphinx.ext.intersphinx",
              "sphinx.ext.mathjax"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = u"Daft"
copyright = u"2012, Dan Foreman-Mackey & David W. Hogg"
version = daft.__version__
release = daft.__version__

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "daft"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
        "tagline": "Beautifully rendered probabilistic graphical models.",
    }

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ["_themes"]

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
html_static_path = ["_static"]

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
            "**": ["relations.html", "searchbox.html"]
        }

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
html_show_sourcelink = False

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
htmlhelp_basename = 'Daftdoc'

# LaTeX Options.
latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
        ('index', 'Daft.tex', u'Daft Documentation',
         u'Dan Foreman-Mackey \\& David W. Hogg', 'manual'),
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


# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
        ('index', 'daft', u'Daft Documentation',
         [u'Dan Foreman-Mackey & David W. Hogg'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Daft', u'Daft Documentation',
   u'Dan Foreman-Mackey & David W. Hogg', 'Daft',
   'One line description of project.', 'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = gen_example
#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import json
from subprocess import check_call


this_path = os.path.dirname(os.path.abspath(__file__))
daft_path = os.path.dirname(this_path)
sys.path.insert(0, daft_path)

example_dir = os.path.join(daft_path, "examples")
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")
img_out_dir = os.path.join(this_path, "_static", "examples")

try:
    os.makedirs(out_dir)
except os.error:
    pass

try:
    os.makedirs(img_out_dir)
except os.error:
    pass

example_template = """.. _{example}:

{title}

.. figure:: /_static/examples/{example}.png

{doc}

::

{src}

"""


def main(fn, thumb_info):
    # Run the code.
    pyfn = os.path.join(example_dir, fn + ".py")
    src = open(pyfn).read()
    print("Executing: " + pyfn)

    ns = {}
    exec src in ns
    pgm = ns["pgm"]

    # Generate the RST source file.
    src = src.split("\n")
    if ns["__doc__"] is None:
        title = fn.title() + "\n" + "=" * len(fn)
        doc = ""
    else:
        doc = ns["__doc__"].split("\n")
        title = "\n".join(doc[:3])
        doc = "\n".join(doc)
        src = src[len(ns["__doc__"].split("\n")):]

    fmt_src = "\n".join(["    " + l for l in src])
    img_path = os.path.join(img_out_dir, fn + ".png")
    thumb_path = os.path.join(img_out_dir, fn + "-thumb.png")

    rst = example_template.format(title=title, doc=doc, example=fn,
            src=fmt_src, img_path=img_path)

    # Write the RST file.
    rstfn = os.path.join(out_dir, fn + ".rst")
    print("Writing: " + rstfn)
    with open(rstfn, "w") as f:
        f.write(rst)

    # Remove the generated plots.
    try:
        os.remove(fn + ".png")
    except os.error:
        pass
    try:
        os.remove(fn + ".pdf")
    except os.error:
        pass

    # Save the new figure.
    print("Saving: " + img_path)
    pgm.figure.savefig(img_path, dpi=150)

    # Crop the thumbnail.
    cmd = " ".join(["convert",
                    "-crop 190x190+{0[0]:d}+{0[1]:d}".format(thumb_info),
                    img_path, thumb_path])
    print(cmd)
    check_call(cmd, shell=True)


if __name__ == "__main__":
    m = json.load(open(os.path.join(this_path, "_static", "examples.json")))
    if len(sys.argv) == 1:
        # Build all the examples.
        argv = m.keys()
    else:
        argv = sys.argv[1:]

    for k in argv:
        assert k in m, "Add {0} to _static/examples.json".format(k)
        main(k, m[k])

########NEW FILE########
__FILENAME__ = astronomy
"""
Astronomical imaging
====================

This is a model for every pixel of every astronomical image ever
taken.  It is incomplete!

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

pgm = daft.PGM([8, 6.75], origin=[0.5, 0.5], grid_unit=4., node_unit=1.4)

# Start with the plates.
tweak=0.02
rect_params = {"lw": 2}
pgm.add_plate(daft.Plate([1.5+tweak, 0.5+tweak, 6.0-2*tweak, 3.75-2*tweak], label=r"\Large telescope+camera+filter multiplets", rect_params=rect_params))
pgm.add_plate(daft.Plate([2.5+tweak, 1.0+tweak, 4.0-2*tweak, 2.75-2*tweak], label=r"\Large images", rect_params=rect_params))
pgm.add_plate(daft.Plate([3.5+tweak, 1.5+tweak, 2.0-2*tweak, 1.75-2*tweak], label=r"\Large pixel patches", rect_params=rect_params))
pgm.add_plate(daft.Plate([1.0+tweak, 4.25+tweak, 3.5-2*tweak, 1.75-2*tweak], label=r"\Large stars", rect_params=rect_params))
pgm.add_plate(daft.Plate([5.5+tweak, 4.25+tweak, 2.5-2*tweak, 1.75-2*tweak], label=r"\Large galaxies", rect_params=rect_params))

# ONLY pixels are observed
asp = 2.3
pgm.add_node(daft.Node("true pixels", r"~\\noise-free\\pixel patch", 5.0, 2.5, aspect=asp))
pgm.add_node(daft.Node("pixels", r"pixel patch", 4.0, 2.0, observed=True, aspect=asp))
pgm.add_edge("true pixels", "pixels")

# The sky
pgm.add_node(daft.Node("sky", r"sky model", 6.0, 2.5, aspect=asp))
pgm.add_edge("sky", "true pixels")
pgm.add_node(daft.Node("sky prior", r"sky priors", 8.0, 2.5, fixed=True))
pgm.add_edge("sky prior", "sky")

# Stars
pgm.add_node(daft.Node("star patch", r"star patch", 4.0, 3.0, aspect=asp))
pgm.add_edge("star patch", "true pixels")
pgm.add_node(daft.Node("star SED", r"~\\spectral energy\\distribution", 2.5, 4.75, aspect=asp+0.2))
pgm.add_edge("star SED", "star patch")
pgm.add_node(daft.Node("star position", r"position", 4.0, 4.75, aspect=asp))
pgm.add_edge("star position", "star patch")
pgm.add_node(daft.Node("temperature", r"temperature", 1.5, 5.25, aspect=asp))
pgm.add_edge("temperature", "star SED")
pgm.add_node(daft.Node("luminosity", r"luminosity", 2.5, 5.25, aspect=asp))
pgm.add_edge("luminosity", "star SED")
pgm.add_node(daft.Node("metallicity", r"metallicity", 1.5, 5.75, aspect=asp))
pgm.add_edge("metallicity", "star SED")
pgm.add_edge("metallicity", "temperature")
pgm.add_edge("metallicity", "luminosity")
pgm.add_node(daft.Node("mass", r"mass", 2.5, 5.75, aspect=asp))
pgm.add_edge("mass", "temperature")
pgm.add_edge("mass", "luminosity")
pgm.add_node(daft.Node("age", r"age", 3.5, 5.75, aspect=asp))
pgm.add_edge("age", "temperature")
pgm.add_edge("age", "luminosity")
pgm.add_node(daft.Node("star models", r"star models", 1.0, 4.0, fixed=True))
pgm.add_edge("star models", "temperature")
pgm.add_edge("star models", "luminosity")
pgm.add_edge("star models", "star SED")

# Galaxies
pgm.add_node(daft.Node("galaxy patch", r"galaxy patch", 5.0, 3.0, aspect=asp))
pgm.add_edge("galaxy patch", "true pixels")
pgm.add_node(daft.Node("galaxy SED", r"~\\spectral energy\\distribution", 6.5, 4.75, aspect=asp+0.2))
pgm.add_edge("galaxy SED", "galaxy patch")
pgm.add_node(daft.Node("morphology", r"morphology", 7.5, 4.75, aspect=asp))
pgm.add_edge("morphology", "galaxy patch")
pgm.add_node(daft.Node("SFH", r"~\\star-formation\\history", 7.5, 5.25, aspect=asp))
pgm.add_edge("SFH", "galaxy SED")
pgm.add_edge("SFH", "morphology")
pgm.add_node(daft.Node("galaxy position", r"~\\redshift\\ \& position", 6.0, 5.25, aspect=asp))
pgm.add_edge("galaxy position", "galaxy SED")
pgm.add_edge("galaxy position", "morphology")
pgm.add_edge("galaxy position", "galaxy patch")
pgm.add_node(daft.Node("dynamics", r"orbit structure", 6.5, 5.75, aspect=asp))
pgm.add_edge("dynamics", "morphology")
pgm.add_edge("dynamics", "SFH")
pgm.add_node(daft.Node("galaxy mass", r"mass", 7.5, 5.75, aspect=asp))
pgm.add_edge("galaxy mass", "dynamics")
pgm.add_edge("galaxy mass", "galaxy SED")
pgm.add_edge("galaxy mass", "SFH")

# Universals
pgm.add_node(daft.Node("extinction model", r"~\\extinction\\model", 5.0, 4.75, aspect=asp))
pgm.add_edge("extinction model", "star patch")
pgm.add_edge("extinction model", "galaxy patch")
pgm.add_node(daft.Node("MW", r"~\\Milky Way\\formation", 4.0, 6.5, aspect=asp))
pgm.add_edge("MW", "metallicity")
pgm.add_edge("MW", "mass")
pgm.add_edge("MW", "age")
pgm.add_edge("MW", "star position")
pgm.add_edge("MW", "extinction model")
pgm.add_node(daft.Node("galaxy formation", r"~\\galaxy\\formation", 5.0, 6.5, aspect=asp))
pgm.add_edge("galaxy formation", "MW")
pgm.add_edge("galaxy formation", "dynamics")
pgm.add_edge("galaxy formation", "galaxy mass")
pgm.add_edge("galaxy formation", "extinction model")
pgm.add_node(daft.Node("LSS", r"~\\large-scale\\structure", 6.0, 6.5, aspect=asp))
pgm.add_edge("LSS", "galaxy position")
pgm.add_node(daft.Node("cosmology", r"~\\cosmological\\parameters", 6.0, 7.0, aspect=asp))
pgm.add_edge("cosmology", "LSS")
pgm.add_edge("cosmology", "galaxy formation")
pgm.add_node(daft.Node("god", r"God", 7.0, 7.0, fixed=True))
pgm.add_edge("god", "cosmology")

# Sensitivity
pgm.add_node(daft.Node("zeropoint", r"~\\zeropoint\\(photocal)", 3.0, 3.0, aspect=asp))
pgm.add_edge("zeropoint", "true pixels")
pgm.add_node(daft.Node("exposure time", r"exposure time", 3.0, 2.5, observed=True, aspect=asp))
pgm.add_edge("exposure time", "zeropoint")

# The PSF
pgm.add_node(daft.Node("WCS", r"~\\astrometric\\calibration", 3.0, 2.0, aspect=asp))
pgm.add_edge("WCS", "star patch")
pgm.add_edge("WCS", "galaxy patch")
pgm.add_node(daft.Node("psf", r"PSF model", 3.0, 3.5, aspect=asp))
pgm.add_edge("psf", "star patch")
pgm.add_edge("psf", "galaxy patch")
pgm.add_node(daft.Node("optics", r"optics", 2.0, 3.0, aspect=asp-1.2))
pgm.add_edge("optics", "psf")
pgm.add_edge("optics", "WCS")
pgm.add_node(daft.Node("atmosphere", r"~\\atmosphere\\model", 1.0, 3.5, aspect=asp))
pgm.add_edge("atmosphere", "psf")
pgm.add_edge("atmosphere", "WCS")
pgm.add_edge("atmosphere", "zeropoint")

# The device
pgm.add_node(daft.Node("flatfield", r"flat-field", 2.0, 1.5, aspect=asp))
pgm.add_edge("flatfield", "pixels")
pgm.add_node(daft.Node("nonlinearity", r"non-linearity", 2.0, 1.0, aspect=asp))
pgm.add_edge("nonlinearity", "pixels")
pgm.add_node(daft.Node("pointing", r"~\\telescope\\pointing etc.", 2.0, 2.0, aspect=asp))
pgm.add_edge("pointing", "WCS")
pgm.add_node(daft.Node("detector", r"detector priors", 1.0, 1.5, fixed=True))
pgm.add_edge("detector", "flatfield")
pgm.add_edge("detector", "nonlinearity")
pgm.add_node(daft.Node("hardware", r"hardware priors", 1.0, 2.5, fixed=True))
pgm.add_edge("hardware", "pointing")
pgm.add_edge("hardware", "exposure time")
pgm.add_edge("hardware", "optics")

# Noise
pgm.add_node(daft.Node("noise patch", r"noise patch", 5.0, 2.0, aspect=asp))
pgm.add_edge("noise patch", "pixels")
pgm.add_edge("true pixels", "noise patch")
pgm.add_node(daft.Node("noise model", r"noise model", 7.0, 2.0, aspect=asp))
pgm.add_edge("noise model", "noise patch")
pgm.add_node(daft.Node("noise prior", r"noise priors", 8.0, 2.0, fixed=True))
pgm.add_edge("noise prior", "noise model")
pgm.add_node(daft.Node("cosmic rays", r"~\\cosmic-ray\\model", 8.0, 1.5, aspect=asp))
pgm.add_edge("cosmic rays", "noise patch")

# Render and save.
pgm.render()
pgm.figure.savefig("astronomy.pdf")
pgm.figure.savefig("astronomy.png", dpi=150)

########NEW FILE########
__FILENAME__ = badfont
"""
You can use arbitrarily shitty fonts
====================================

Any fonts that LaTeX or matplotlib supports can be used. Do not take
this example as any kind of implied recommendation unless you plan on
announcing a *huge* discovery!

"""

from matplotlib import rc

ff = "comic sans ms"
# ff = "impact"
# ff = "times new roman"

rc("font", family=ff, size=12)
rc("text", usetex=False)

import daft

pgm = daft.PGM([3.6, 1.8], origin=[2.2, 1.6], aspect=2.1)
pgm.add_node(daft.Node("confused", r"confused", 3.0, 3.0))
pgm.add_node(daft.Node("ugly", r"ugly font", 3.0, 2.0, observed=True))
pgm.add_node(daft.Node("bad", r"bad talk", 5.0, 2.0, observed=True))
pgm.add_edge("confused", "ugly")
pgm.add_edge("ugly", "bad")
pgm.add_edge("confused", "bad")
pgm.render()
pgm.figure.savefig("badfont.pdf")
pgm.figure.savefig("badfont.png", dpi=150)

########NEW FILE########
__FILENAME__ = bca
from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)
import daft

if __name__ == "__main__":
    pgm = daft.PGM([1.1, 3.15], origin=[0.45, 2.2])
    pgm.add_node(daft.Node("a", r"$a$", 1, 5))
    pgm.add_node(daft.Node("b", r"$b$", 1, 4))
    pgm.add_node(daft.Node("c", r"$c_n$", 1, 3, observed=True))
    pgm.add_plate(daft.Plate([0.5, 2.25, 1, 1.25], label=r"data $n$"))
    pgm.add_edge("a", "b")
    pgm.add_edge("b", "c")
    pgm.render()
    pgm.figure.savefig("bca.pdf")
    pgm.figure.savefig("bca.png", dpi=150)

########NEW FILE########
__FILENAME__ = classic
"""
The Quintessential PGM
======================

This is a demonstration of a very common structure found in graphical models.
It has been rendered using Daft's default settings for all the parameters
and it shows off how much beauty is baked in by default.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

# Instantiate the PGM.
pgm = daft.PGM([2.3, 2.05], origin=[0.3, 0.3])

# Hierarchical parameters.
pgm.add_node(daft.Node("alpha", r"$\alpha$", 0.5, 2, fixed=True))
pgm.add_node(daft.Node("beta", r"$\beta$", 1.5, 2))

# Latent variable.
pgm.add_node(daft.Node("w", r"$w_n$", 1, 1))

# Data.
pgm.add_node(daft.Node("x", r"$x_n$", 2, 1, observed=True))

# Add in the edges.
pgm.add_edge("alpha", "beta")
pgm.add_edge("beta", "w")
pgm.add_edge("w", "x")
pgm.add_edge("beta", "x")

# And a plate.
pgm.add_plate(daft.Plate([0.5, 0.5, 2, 1], label=r"$n = 1, \cdots, N$",
    shift=-0.1))

# Render and save.
pgm.render()
pgm.figure.savefig("classic.pdf")
pgm.figure.savefig("classic.png", dpi=150)

########NEW FILE########
__FILENAME__ = exoplanets
"""
The Fergus model of exoplanet detection
=======================================

Besides being generally awesome, this example also demonstrates how you can
color the nodes and add arbitrary labels to the figure.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

# Colors.
p_color = {"ec": "#46a546"}
s_color = {"ec": "#f89406"}

pgm = daft.PGM([3.6, 3.5], origin=[0.7, 0])

n = daft.Node("phi", r"$\phi$", 1, 3, plot_params=s_color)
n.va = "baseline"
pgm.add_node(n)
pgm.add_node(daft.Node("speckle_coeff", r"$z_i$", 2, 3, plot_params=s_color))
pgm.add_node(daft.Node("speckle_img", r"$x_i$", 2, 2, plot_params=s_color))

pgm.add_node(daft.Node("spec", r"$s$", 4, 3, plot_params=p_color))
pgm.add_node(daft.Node("shape", r"$g$", 4, 2, plot_params=p_color))
pgm.add_node(daft.Node("planet_pos", r"$\mu_i$", 3, 3, plot_params=p_color))
pgm.add_node(daft.Node("planet_img", r"$p_i$", 3, 2, plot_params=p_color))

pgm.add_node(daft.Node("pixels", r"$y_i ^j$", 2.5, 1, observed=True))

# Edges.
pgm.add_edge("phi", "speckle_coeff")
pgm.add_edge("speckle_coeff", "speckle_img")
pgm.add_edge("speckle_img", "pixels")

pgm.add_edge("spec", "planet_img")
pgm.add_edge("shape", "planet_img")
pgm.add_edge("planet_pos", "planet_img")
pgm.add_edge("planet_img", "pixels")

# And a plate.
pgm.add_plate(daft.Plate([1.5, 0.2, 2, 3.2], label=r"exposure $i$",
    shift=-0.1))
pgm.add_plate(daft.Plate([2, 0.5, 1, 1], label=r"pixel $j$",
    shift=-0.1))

# Render and save.
pgm.render()
pgm.figure.savefig("exoplanets.pdf")
pgm.figure.savefig("exoplanets.png", dpi=150)

########NEW FILE########
__FILENAME__ = fixed
import daft

pgm = daft.PGM([2, 1], observed_style="outer", aspect=3.2)
pgm.add_node(daft.Node("fixed", r"Fixed!", 1, 0.5, observed=True))
pgm.render().figure.savefig("fixed.png", dpi=150)

########NEW FILE########
__FILENAME__ = gaia
from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)
import daft

if __name__ == "__main__":
    pgm = daft.PGM([3.7, 3.15], origin=[-0.35, 2.2])
    pgm.add_node(daft.Node("omega", r"$\omega$", 2, 5))
    pgm.add_node(daft.Node("true", r"$\tilde{X}_n$", 2, 4))
    pgm.add_node(daft.Node("obs", r"$X_n$", 2, 3, observed=True))
    pgm.add_node(daft.Node("alpha", r"$\alpha$", 3, 4))
    pgm.add_node(daft.Node("Sigma", r"$\Sigma$", 0, 3))
    pgm.add_node(daft.Node("sigma", r"$\sigma_n$", 1, 3))
    pgm.add_plate(daft.Plate([0.5, 2.25, 2, 2.25], label=r"stars $n$"))
    pgm.add_edge("omega", "true")
    pgm.add_edge("true", "obs")
    pgm.add_edge("alpha", "true")
    pgm.add_edge("Sigma", "sigma")
    pgm.add_edge("sigma", "obs")
    pgm.render()
    pgm.figure.savefig("gaia.pdf")
    pgm.figure.savefig("gaia.png", dpi=150)

########NEW FILE########
__FILENAME__ = galex
"""
The GALEX Photon Catalog
========================

This is the Hogg \& Schiminovich model for how photons turn into
counts in the GALEX satellite data stream.  Note the use of relative
positioning.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)
import daft
pgm = daft.PGM([5.4, 5.4], origin=[1.2, 1.2])
wide = 1.5
verywide = 1.5 * wide
dy = 0.75

# electrons
el_x, el_y = 2., 2.
pgm.add_plate(daft.Plate([el_x - 0.6, el_y - 0.6, 2.2, 2 * dy + 0.3], label="electrons $i$"))
pgm.add_node(daft.Node("xabc", r"xa$_i$,xabc$_i$,ya$_i$,\textit{etc}", el_x + 0.5, el_y + 0 * dy, aspect=2.3 * wide, observed=True))
pgm.add_node(daft.Node("xyti", r"$x_i,y_i,t_i$", el_x + 1., el_y + 1 * dy, aspect=wide))
pgm.add_edge("xyti", "xabc")

# intensity fields
ph_x, ph_y = el_x + 2.5, el_y + 3 * dy
pgm.add_node(daft.Node("Ixyt", r"$I_{\nu}(x,y,t)$", ph_x, ph_y, aspect=verywide))
pgm.add_edge("Ixyt", "xyti")
pgm.add_node(daft.Node("Ixnt", r"$I_{\nu}(\xi,\eta,t)$", ph_x, ph_y + 1 * dy, aspect=verywide))
pgm.add_edge("Ixnt", "Ixyt")
pgm.add_node(daft.Node("Iadt", r"$I_{\nu}(\alpha,\delta,t)$", ph_x, ph_y + 2 * dy, aspect=verywide))
pgm.add_edge("Iadt", "Ixnt")

# s/c
sc_x, sc_y = ph_x + 1.5, ph_y - 1.5 * dy
pgm.add_node(daft.Node("dark", r"dark", sc_x, sc_y - 1 * dy, aspect=wide))
pgm.add_edge("dark", "xyti")
pgm.add_node(daft.Node("flat", r"flat", sc_x, sc_y, aspect=wide))
pgm.add_edge("flat", "xyti")
pgm.add_node(daft.Node("att", r"att", sc_x, sc_y + 3 * dy))
pgm.add_edge("att", "Ixnt")
pgm.add_node(daft.Node("optics", r"optics", sc_x, sc_y + 2 * dy, aspect=wide))
pgm.add_edge("optics", "Ixyt")
pgm.add_node(daft.Node("psf", r"psf", sc_x, sc_y + 1 * dy))
pgm.add_edge("psf", "xyti")
pgm.add_node(daft.Node("fee", r"f.e.e.", sc_x, sc_y - 2 * dy, aspect=wide))
pgm.add_edge("fee", "xabc")

# sky
pgm.add_node(daft.Node("sky", r"sky", sc_x, sc_y + 4 * dy))
pgm.add_edge("sky", "Iadt")

# stars
star_x, star_y = el_x, el_y + 4 * dy
pgm.add_plate(daft.Plate([star_x - 0.6, star_y - 0.6, 2.2, 2 * dy + 0.3], label="stars $n$"))
pgm.add_node(daft.Node("star adt", r"$I_{\nu,n}(\alpha,\delta,t)$", star_x + 0.5, star_y + 1 * dy, aspect=verywide))
pgm.add_edge("star adt", "Iadt")
pgm.add_node(daft.Node("star L", r"$L_{\nu,n}(t)$", star_x + 1, star_y, aspect=wide))
pgm.add_edge("star L", "star adt")
pgm.add_node(daft.Node("star pos", r"$\vec{x_n}$", star_x, star_y))
pgm.add_edge("star pos", "star adt")

# done
pgm.render()
pgm.figure.savefig("galex.pdf")
pgm.figure.savefig("galex.png", dpi=150)

########NEW FILE########
__FILENAME__ = huey_p_newton
"""
n-body particle inference
=========================

Dude.
"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

pgm = daft.PGM([5.4, 2.0], origin=[0.65, 0.35])

kx, ky = 1.5, 1.
nx, ny = kx + 3., ky + 0.
hx, hy, dhx = kx - 0.5, ky + 1., 1.

pgm.add_node(daft.Node("dyn", r"$\theta_{\mathrm{dyn}}$", hx + 0. * dhx, hy + 0.))
pgm.add_node(daft.Node("ic", r"$\theta_{\mathrm{I.C.}}$", hx + 1. * dhx, hy + 0.))
pgm.add_node(daft.Node("sun", r"$\theta_{\odot}$",        hx + 2. * dhx, hy + 0.))
pgm.add_node(daft.Node("bg", r"$\theta_{\mathrm{bg}}$",   hx + 3. * dhx, hy + 0.))
pgm.add_node(daft.Node("Sigma", r"$\Sigma^2$",            hx + 4. * dhx, hy + 0.))

pgm.add_plate(daft.Plate([kx - 0.5, ky - 0.6, 2., 1.1], label=r"model points $k$"))
pgm.add_node(daft.Node("xk", r"$x_k$", kx + 0., ky + 0.))
pgm.add_edge("dyn", "xk")
pgm.add_edge("ic", "xk")
pgm.add_node(daft.Node("yk", r"$y_k$", kx + 1., ky + 0.))
pgm.add_edge("sun", "yk")
pgm.add_edge("xk", "yk")

pgm.add_plate(daft.Plate([nx - 0.5, ny - 0.6, 2., 1.1], label=r"data points $n$"))
pgm.add_node(daft.Node("sigman", r"$\sigma^2_n$", nx + 1., ny + 0., observed=True))
pgm.add_node(daft.Node("Yn", r"$Y_n$", nx + 0., ny + 0., observed=True))
pgm.add_edge("bg", "Yn")
pgm.add_edge("Sigma", "Yn")
pgm.add_edge("Sigma", "Yn")
pgm.add_edge("yk", "Yn")
pgm.add_edge("sigman", "Yn")

# Render and save.
pgm.render()
pgm.figure.savefig("huey_p_newton.pdf")
pgm.figure.savefig("huey_p_newton.png", dpi=150)

########NEW FILE########
__FILENAME__ = logo
#!/usr/bin/env python
"""
That's an awfully DAFT logo!

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import daft


if __name__ == "__main__":
    # Instantiate the PGM.
    pgm = daft.PGM((3.7, 0.7), origin=(0.15, 0.15))

    pgm.add_node(daft.Node("d", r"$D$", 0.5, 0.5))
    pgm.add_node(daft.Node("a", r"$a$", 1.5, 0.5, observed=True))
    pgm.add_node(daft.Node("f", r"$f$", 2.5, 0.5))
    pgm.add_node(daft.Node("t", r"$t$", 3.5, 0.5))

    pgm.add_edge("d", "a")
    pgm.add_edge("a", "f")
    pgm.add_edge("f", "t")

    pgm.render()
    pgm.figure.savefig("logo.pdf")
    pgm.figure.savefig("logo.png", dpi=200, transparent=True)

########NEW FILE########
__FILENAME__ = mrf
"""
An undirected graph
===================

This makes the simple point that you don't have to have directions on
your edges; you can have *undirected* graphs.  (Also, the nodes don't
need to have labels!)

"""

import itertools
import numpy as np

import daft

# Instantiate the PGM.
pgm = daft.PGM([3.6, 3.6], origin=[0.7, 0.7], node_unit=0.4, grid_unit=1,
        directed=False)

for i, (xi, yi) in enumerate(itertools.product(range(1, 5), range(1, 5))):
    pgm.add_node(daft.Node(str(i), "", xi, yi))


for e in [(4, 9), (6, 7), (3, 7), (10, 11), (10, 9), (10, 14),
        (10, 6), (10, 7), (1, 2), (1, 5), (1, 0), (1, 6), (8, 12), (12, 13),
        (13, 14), (15, 11)]:
    pgm.add_edge(str(e[0]), str(e[1]))

# Render and save.
pgm.render()
pgm.figure.savefig("mrf.pdf")
pgm.figure.savefig("mrf.png", dpi=150)

########NEW FILE########
__FILENAME__ = nocircles
"""
Nodes can go free
=================

You don't need to put ellipses or circles around your node contents,
if you don't want to.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

pgm = daft.PGM([3.6, 2.4], origin = [1.15, 0.8], node_ec="none")
pgm.add_node(daft.Node("cloudy", r"cloudy", 3, 3))
pgm.add_node(daft.Node("rain", r"rain", 2, 2))
pgm.add_node(daft.Node("sprinkler", r"sprinkler", 4, 2))
pgm.add_node(daft.Node("wet", r"grass wet", 3, 1))
pgm.add_edge("cloudy", "rain")
pgm.add_edge("cloudy", "sprinkler")
pgm.add_edge("rain", "wet")
pgm.add_edge("sprinkler", "wet")
pgm.render()
pgm.figure.savefig("nocircles.pdf")
pgm.figure.savefig("nocircles.png", dpi=150)

########NEW FILE########
__FILENAME__ = nogray
"""
Alternative Observed Node Styles
================================

.. module:: daft

This model is the same as `the classic </examples/classic>`_ model but the
"observed" :class:`Node` is indicated by a double outline instead of shading.
This particular example uses the ``inner`` style but ``outer`` is also an
option for a different look.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

pgm = daft.PGM([2.3, 2.05], origin=[0.3, 0.3], observed_style="inner")

# Hierarchical parameters.
pgm.add_node(daft.Node("alpha", r"$\alpha$", 0.5, 2, fixed=True))
pgm.add_node(daft.Node("beta", r"$\beta$", 1.5, 2))

# Latent variable.
pgm.add_node(daft.Node("w", r"$w_n$", 1, 1))

# Data.
pgm.add_node(daft.Node("x", r"$x_n$", 2, 1, observed=True))

# Add in the edges.
pgm.add_edge("alpha", "beta")
pgm.add_edge("beta", "w")
pgm.add_edge("w", "x")
pgm.add_edge("beta", "x")

# And a plate.
pgm.add_plate(daft.Plate([0.5, 0.5, 2, 1], label=r"$n = 1, \ldots, N$",
    shift=-0.1))

# Render and save.
pgm.render()
pgm.figure.savefig("nogray.pdf")
pgm.figure.savefig("nogray.png", dpi=150)

########NEW FILE########
__FILENAME__ = recursive
"""
Recursively generated graph
===========================

**Daft** is Python, so you can do anything Python can do.  This graph is
generated by recursive code.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

def recurse(pgm, nodename, level, c):
    if level > 4:
        return nodename
    r = c / 2
    r1nodename = "r{0:02d}{1:04d}".format(level, r)
    if 2 * r == c:
        print("adding {0}".format(r1nodename))
        pgm.add_node(daft.Node(r1nodename, r"reduce",
                               2 ** level * (r + 0.5) - 0.5,
                               3 - 0.7 * level, aspect=1.9))
    pgm.add_edge(nodename, r1nodename)
    if 2 * r == c:
        return recurse(pgm, r1nodename, level + 1, r)

pgm = daft.PGM([16.2, 8], origin=[-0.6, -1.5])

pgm.add_node(daft.Node("query", r'\texttt{"kittens?"}', 3, 6., aspect=3.,
                       plot_params={"ec": "none"}))
pgm.add_node(daft.Node("input", r"input", 7.5, 6., aspect=3.))
pgm.add_edge("query", "input")

for c in range(16):
    nodename = "map {0:02d}".format(c)
    pgm.add_node(daft.Node(nodename, str(nodename), c, 3., aspect=1.9))
    pgm.add_edge("input", nodename)
    level = 1
    recurse(pgm, nodename, level, c)

pgm.add_node(daft.Node("output", r"output", 7.5, -1., aspect=3.))
pgm.add_edge("r040000", "output")
pgm.add_node(daft.Node("answer", r'\texttt{"http://dwh.gg/"}', 12., -1.,
                       aspect=4.5, plot_params={"ec": "none"}))
pgm.add_edge("output", "answer")

pgm.render()
pgm.figure.savefig("recursive.pdf")
pgm.figure.savefig("recursive.png", dpi=200)

########NEW FILE########
__FILENAME__ = thicklines
"""
T-shirt style
=============

Don't like dainty thin lines?  Need to make graphical-model-themed
conference schwag?  Then `line_width` is the parameter for you.  Also
check out the `preamble` option in the `matplotlib.rc` command.

"""

from matplotlib import rc
rc("font", family="serif", size=14)
rc("text", usetex=True)
rc('text.latex',
   preamble="\usepackage{amssymb}\usepackage{amsmath}\usepackage{mathrsfs}")

import daft

# Instantiate the PGM.
pgm = daft.PGM([2.3, 2.05], origin=[0.3, 0.3], line_width=2.5)

# Hierarchical parameters.
pgm.add_node(daft.Node("alpha", r"$\boldsymbol{\alpha}$", 0.5, 2, fixed=True))
pgm.add_node(daft.Node("beta", r"$\boldsymbol{\beta}$", 1.5, 2))

# Latent variable.
pgm.add_node(daft.Node("w", r"$\boldsymbol{w_n}$", 1, 1))

# Data.
pgm.add_node(daft.Node("x", r"$\boldsymbol{x_n}$", 2, 1, observed=True))

# Add in the edges.
pgm.add_edge("alpha", "beta")
pgm.add_edge("beta", "w")
pgm.add_edge("w", "x")
pgm.add_edge("beta", "x")

# And a plate.
pgm.add_plate(daft.Plate([0.5, 0.5, 2, 1], label=r"$\boldsymbol{n = 1, \cdots, N}$",
    shift=-0.1))

# Render and save.
pgm.render()
pgm.figure.savefig("thicklines.pdf")
pgm.figure.savefig("thicklines.png", dpi=150)

########NEW FILE########
__FILENAME__ = weaklensing
"""
A model for weak lensing
========================

This is (**Daft** co-author) Hogg's model for the obsevational
cosmology method known as *weak gravitational lensing*, if that method
were properly probabilistic (which it usually isn't).  Hogg put the
model here for one very important reason: *Because he can*.  Oh, and
it demonstrates that you can represent non-trivial scientific projects
with **Daft**.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

pgm = daft.PGM([4.7, 2.35], origin=[-1.35, 2.2])
pgm.add_node(daft.Node("Omega", r"$\Omega$", -1, 4))
pgm.add_node(daft.Node("gamma", r"$\gamma$", 0, 4))
pgm.add_node(daft.Node("obs", r"$\epsilon^{\mathrm{obs}}_n$", 1, 4,
                       observed=True))
pgm.add_node(daft.Node("alpha", r"$\alpha$", 3, 4))
pgm.add_node(daft.Node("true", r"$\epsilon^{\mathrm{true}}_n$", 2, 4))
pgm.add_node(daft.Node("sigma", r"$\sigma_n$", 1, 3))
pgm.add_node(daft.Node("Sigma", r"$\Sigma$", 0, 3))
pgm.add_node(daft.Node("x", r"$x_n$", 2, 3, observed=True))
pgm.add_plate(daft.Plate([0.5, 2.25, 2, 2.25],
                         label=r"galaxies $n$"))
pgm.add_edge("Omega", "gamma")
pgm.add_edge("gamma", "obs")
pgm.add_edge("alpha", "true")
pgm.add_edge("true", "obs")
pgm.add_edge("x", "obs")
pgm.add_edge("Sigma", "sigma")
pgm.add_edge("sigma", "obs")
pgm.render()
pgm.figure.savefig("weaklensing.pdf")
pgm.figure.savefig("weaklensing.png", dpi=150)

########NEW FILE########
__FILENAME__ = wordy
"""
Nodes can contain words
=======================

We here at **Daft** headquarters tend to put symbols (variable
names) in our graph nodes.  But you don't have to if you don't
want to.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

pgm = daft.PGM([3.6, 2.7], origin=[1.15, 0.65])
pgm.add_node(daft.Node("cloudy", r"cloudy", 3, 3, aspect=1.8))
pgm.add_node(daft.Node("rain", r"rain", 2, 2, aspect=1.2))
pgm.add_node(daft.Node("sprinkler", r"sprinkler", 4, 2, aspect=2.1))
pgm.add_node(daft.Node("wet", r"grass wet", 3, 1, aspect=2.4, observed=True))
pgm.add_edge("cloudy", "rain")
pgm.add_edge("cloudy", "sprinkler")
pgm.add_edge("rain", "wet")
pgm.add_edge("sprinkler", "wet")
pgm.render()
pgm.figure.savefig("wordy.pdf")
pgm.figure.savefig("wordy.png", dpi=150)

########NEW FILE########
__FILENAME__ = yike
"""
Yike's model
============

This is Yike Tang's model for weak lensing.

"""

from matplotlib import rc
rc("font", family="serif", size=12)
rc("text", usetex=True)

import daft

pgm = daft.PGM([5.20, 2.95], origin=[-1.70, 1.65])
pgm.add_node(daft.Node("obs", r"$\epsilon^{\mathrm{obs}}_n$", 2, 3, observed=True))
pgm.add_node(daft.Node("true", r"$\epsilon^{\mathrm{true}}_n$", 1, 3))
pgm.add_edge("true", "obs")
pgm.add_node(daft.Node("alpha", r"$\alpha,\beta$", -0.25, 3))
pgm.add_edge("alpha", "true")
pgm.add_node(daft.Node("shape prior", r"$p(\alpha, \beta)$", -1.25, 3, fixed=True))
pgm.add_edge("shape prior", "alpha")
pgm.add_node(daft.Node("gamma", r"$\gamma_m$", 2, 4))
pgm.add_edge("gamma", "obs")
pgm.add_node(daft.Node("gamma prior", r"$p(\gamma)$", -0.25, 4, fixed=True))
pgm.add_edge("gamma prior", "gamma")
pgm.add_node(daft.Node("sigma", r"$\sigma_{\epsilon}$", 3.25, 3, fixed=True))
pgm.add_edge("sigma", "obs")
pgm.add_plate(daft.Plate([0.5, 2.25, 2, 1.25],
        label=r"galaxies $n$"))
pgm.add_plate(daft.Plate([0.25, 1.75, 2.5, 2.75],
        label=r"patches $m$"))
pgm.render()
pgm.figure.savefig("yike.pdf")
pgm.figure.savefig("yike.png", dpi=150)

########NEW FILE########
