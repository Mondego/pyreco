__FILENAME__ = colors
from functools import wraps

import brewer2mpl
import numpy as np
import matplotlib as mpl
from matplotlib import cm



# Get Set2 from ColorBrewer, a set of colors deemed colorblind-safe and
# pleasant to look at by Drs. Cynthia Brewer and Mark Harrower of Pennsylvania
# State University. These colors look lovely together, and are less
# saturated than those colors in Set1. For more on ColorBrewer, see:
# - Flash-based interactive map:
#     http://colorbrewer2.org/
# - A quick visual reference to every ColorBrewer scale:
#     http://bl.ocks.org/mbostock/5577023

#class Common(object):
#    def __init__(self):
set2 = brewer2mpl.get_map('Set2', 'qualitative', 8).mpl_colors

# Another ColorBrewer scale. This one has nice "traditional" colors like
# reds and blues
set1 = brewer2mpl.get_map('Set1', 'qualitative', 9).mpl_colors

# A colormapcycle for stacked barplots
stackmaps = [brewer2mpl.get_map('YlGn', 'sequential', 8).mpl_colormap,
             brewer2mpl.get_map('YlOrRd', 'sequential', 8).mpl_colormap]

# This decorator makes it possible to change the color cycle inside
# prettyplotlib  without affecting pyplot
def pretty(func):
    rcParams = {'axes.color_cycle': set2, 'lines.linewidth': .75}

    @wraps(func)
    def wrapper(*args, **kwargs):
        with mpl.rc_context(rc=rcParams):
            return func(*args, **kwargs)
    return wrapper

# This function returns a colorlist for barplots
def getcolors(cmap, yvals, n):
    if isinstance(cmap, bool):
        cmap = stackmaps[n%len(stackmaps)]
    return [cmap( abs(int((float(yval)/np.max(yvals))*cmap.N) )) for yval in yvals]


# Set some commonly used colors
almost_black = '#262626'
light_grey = np.array([float(248) / float(255)] * 3)

reds = cm.Reds
reds.set_bad('white')
reds.set_under('white')

blues_r = cm.Blues_r
blues_r.set_bad('white')
blues_r.set_under('white')

# Need to 'reverse' red to blue so that blue=cold=small numbers,
# and red=hot=large numbers with '_r' suffix
blue_red = brewer2mpl.get_map('RdBu', 'Diverging', 11,
                              reverse=True).mpl_colormap

########NEW FILE########
__FILENAME__ = general
import matplotlib.pyplot as plt
from functools import wraps

from prettyplotlib.colors import pretty


@wraps(plt.subplots)
@pretty
def subplots(*args, **kwargs):
    return plt.subplots(*args, **kwargs)

@wraps(plt.subplot2grid)
@pretty
def subplot2grid(*args, **kwargs):
    return plt.subplot2grid(*args, **kwargs)

########NEW FILE########
__FILENAME__ = utils
__author__ = 'olga'

import matplotlib as mpl
import matplotlib.pyplot as plt


def remove_chartjunk(ax, spines, grid=None, ticklabels=None, show_ticks=False):
    '''
    Removes "chartjunk", such as extra lines of axes and tick marks.

    If grid="y" or "x", will add a white grid at the "y" or "x" axes,
    respectively

    If ticklabels="y" or "x", or ['x', 'y'] will remove ticklabels from that
    axis
    '''
    all_spines = ['top', 'bottom', 'right', 'left', 'polar']
    for spine in spines:
        # The try/except is for polar coordinates, which only have a 'polar'
        # spine and none of the others
        try:
            ax.spines[spine].set_visible(False)
        except KeyError:
            pass

    # For the remaining spines, make their line thinner and a slightly
    # off-black dark grey
    for spine in all_spines:
        if spine not in spines:
            # The try/except is for polar coordinates, which only have a 'polar'
            # spine and none of the others
            try:
                ax.spines[spine].set_linewidth(0.5)
            except KeyError:
                pass
                # ax.spines[spine].set_color(almost_black)
                #            ax.spines[spine].set_tick_params(color=almost_black)
                # Check that the axes are not log-scale. If they are, leave the ticks
                # because otherwise people assume a linear scale.
    x_pos = set(['top', 'bottom'])
    y_pos = set(['left', 'right'])
    xy_pos = [x_pos, y_pos]
    xy_ax_names = ['xaxis', 'yaxis']

    for ax_name, pos in zip(xy_ax_names, xy_pos):
        axis = ax.__dict__[ax_name]
        # axis.set_tick_params(color=almost_black)
        #print 'axis.get_scale()', axis.get_scale()
        if show_ticks or axis.get_scale() == 'log':
            # if this spine is not in the list of spines to remove
            for p in pos.difference(spines):
                #print 'p', p
                axis.set_tick_params(direction='out')
                axis.set_ticks_position(p)
                #                axis.set_tick_params(which='both', p)
        else:
            axis.set_ticks_position('none')

    if grid is not None:
        for g in grid:
            assert g in ('x', 'y')
            ax.grid(axis=grid, color='white', linestyle='-', linewidth=0.5)

    if ticklabels is not None:
        if type(ticklabels) is str:
            assert ticklabels in set(('x', 'y'))
            if ticklabels == 'x':
                ax.set_xticklabels([])
            if ticklabels == 'y':
                ax.set_yticklabels([])
        else:
            assert set(ticklabels) | set(('x', 'y')) > 0
            if 'x' in ticklabels:
                ax.set_xticklabels([])
            elif 'y' in ticklabels:
                ax.set_yticklabels([])


def maybe_get_ax(*args, **kwargs):
    """
    It used to be that the first argument of prettyplotlib had to be the 'ax'
    object, but that's not the case anymore.

    @param args:
    @type args:
    @param kwargs:
    @type kwargs:
    @return:
    @rtype:
    """

    if 'ax' in kwargs:
        ax = kwargs.pop('ax')
    elif len(args) == 0:
        fig = plt.gcf()
        ax = plt.gca()
    elif isinstance(args[0], mpl.axes.Axes):
        ax = args[0]
        args = args[1:]
    else:
        ax = plt.gca()
    return ax, args, dict(kwargs)


def maybe_get_fig_ax(*args, **kwargs):
    """
    It used to be that the first argument of prettyplotlib had to be the 'ax'
    object, but that's not the case anymore. This is specially made for
    pcolormesh.

    @param args:
    @type args:
    @param kwargs:
    @type kwargs:
    @return:
    @rtype:
    """
    if 'ax' in kwargs:
        ax = kwargs.pop('ax')
        if 'fig' in kwargs:
            fig = kwargs.pop('fig')
        else:
            fig = plt.gcf()
    elif len(args) == 0:
        fig = plt.gcf()
        ax = plt.gca()
    elif isinstance(args[0], mpl.figure.Figure) and \
            isinstance(args[1], mpl.axes.Axes):
        fig = args[0]
        ax = args[1]
        args = args[2:]
    else:
        fig, ax = plt.subplots(1)
    return fig, ax, args, dict(kwargs)


def maybe_get_linewidth(**kwargs):
    try:
        key = (set(["lw", "linewidth", 'linewidths']) & set(kwargs)).pop()
        lw = kwargs[key]
    except KeyError:
        lw = 0.15
    return lw

########NEW FILE########
__FILENAME__ = _bar
import collections

import numpy as np

from prettyplotlib.utils import remove_chartjunk, maybe_get_ax
from prettyplotlib.colors import set2, almost_black, getcolors

def bar(*args, **kwargs):
    """
    Creates a bar plot, with white outlines and a fill color that defaults to
     the first teal-ish green in ColorBrewer's Set2. Optionally accepts
     grid='y' or grid='x' to draw a white grid over the bars,
     to show the scale. Almost like "erasing" some of the plot,
     but it adds more information!

    Can also add an annotation of the height of the barplots directly onto
    the bars with the `annotate` parameter, which can either be True,
    which will annotate the values, or a list of strings, which will annotate
    with the supplied strings.

    Can support stacked bars with the value of each stack shown on the stack
    (Added by Salil Banerjee)

    @param ax: matplotlib.axes instance
    @param left: Vector of values of where to put the left side of the bar
    @param height: Vector of values of the bar heights
    @param kwargs: Besides xticklabels, which is a prettyplotlib-specific
    argument, any additional arguments to matplotlib.bar(): http://matplotlib
    .org/api/axes_api.html#matplotlib.axes.Axes.bar is accepted.
    """
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)
    kwargs.setdefault('color', set2[0])
    kwargs.setdefault('edgecolor', 'white')
    middle = 0.4 if 'width' not in kwargs else kwargs['width']/2.0

    # Check if data contains stacks
    stacked = kwargs.pop('stacked',False)
    # Check if stack text should be included
    stack_text = kwargs.pop('stack_text',False)
    # Get legend if available
    legend = kwargs.pop('legend',False)

    left = args[0]
    height = np.array(args[1])

    # Label each individual bar, if xticklabels is provided
    xtickabels = kwargs.pop('xticklabels', None)
    # left+0.4 is the center of the bar
    xticks = np.array(left) + middle

    # Whether or not to annotate each bar with the height value
    annotate = kwargs.pop('annotate', False)

    show_ticks = kwargs.pop('show_ticks', False)

    # If no grid specified, don't draw one.
    grid = kwargs.pop('grid', None)

    cmap = kwargs.pop('cmap', False)
    if cmap:
        kwargs['edgecolor'] = almost_black
        if not stacked:
            kwargs['color'] = getcolors(cmap, height, 0)

    # Check if stacked and plot data accordingly
    color = kwargs.get('color', None)
    if stacked:
        num_stacks, num_data = height.shape
        bottom = np.zeros(num_data)
        for i in np.arange(num_stacks):
            lst = list(args)
            lst[1] = height[i]
            args = tuple(lst)
            # make sure number of user specified colors equals to the stacks 
            if not color or len(color) != num_stacks:
                if cmap:
                    kwargs['color'] = getcolors(cmap, height[i], i)
                else:
                    kwargs['color'] = set2[i]
            else:
                kwargs['color'] = color[i]
            kwargs['bottom'] = bottom
            rectangles = ax.bar(*args, **kwargs)
            bottom += height[i]
    else:
        rectangles = ax.bar(*args, **kwargs)
   
    # add legend
    if isinstance(legend, collections.Iterable):
        ax.legend(legend,loc='upper center',bbox_to_anchor=(0.5,1.11), ncol=5)

    # add whitespace padding on left
    xmin, xmax = ax.get_xlim()
    xmin -= 0.2
    if stacked:
        xmax = num_data
    ax.set_xlim(xmin, xmax)

    # If the user is only plotting one bar, make it an iterable
    if not isinstance(height, collections.Iterable):
        height = [height]


    # If there are negative counts, remove the bottom axes
    # and add a line at y=0
    if any(h < 0 for h in height.tolist()):
        axes_to_remove = ['top', 'right', 'bottom']
        ax.hlines(y=0, xmin=xmin, xmax=xmax,
                      linewidths=0.75)
    else:
        axes_to_remove = ['top', 'right']

    # Remove excess axes
    remove_chartjunk(ax, axes_to_remove, grid=grid, show_ticks=show_ticks)

    if stacked:
        data = height
        height = height.sum(axis=0)

    # Add the xticklabels if they are there
    if xtickabels is not None:
        ax.set_xticks(xticks)
        ax.set_xticklabels(xtickabels)

    if annotate or isinstance(annotate, collections.Iterable):
        annotate_yrange_factor = 0.025
        ymin, ymax = ax.get_ylim()
        yrange = ymax - ymin

        # Reset ymax and ymin so there's enough room to see the annotation of
        # the top-most
        if ymax > 0:
            ymax += yrange * 0.1
        if ymin < 0:
            ymin -= yrange * 0.1
        ax.set_ylim(ymin, ymax)
        yrange = ymax - ymin

        offset_ = yrange * annotate_yrange_factor
        if isinstance(annotate, collections.Iterable):
            annotations = map(str, annotate)
        else:
            annotations = ['%.3f' % h if type(h) is np.float_ else str(h)
                               for h in height]

        for x, h, annotation in zip(xticks, height, annotations):
            # Adjust the offset to account for negative bars
            offset = offset_ if h >= 0 else -1 * offset_
            verticalalignment = 'bottom' if h >= 0 else 'top'

            # Finally, add the text to the axes
            ax.annotate(annotation, (x, h + offset),
                        verticalalignment=verticalalignment,
                        horizontalalignment='center',
                        color=almost_black)

    # Text for each block of stack
    # This was partially inspired by the following article by Tableau software
    # http://www.tableausoftware.com/about/blog/2014/1/new-whitepaper-survey-data-less-ugly-more-understandable-27812
    if stack_text:
        bottom = np.zeros(num_data)
        max_h = max(height)
        for i in np.arange(num_stacks):
            for x, d, b in zip(xticks, data[i], bottom):
                if (d*100.0/max_h) > 4.0:
                    ax.text(x,b+d/2.0,d, ha='center', va='center', color=almost_black)
            bottom += data[i]
    return rectangles

########NEW FILE########
__FILENAME__ = _barh
__author__ = 'olga'

from prettyplotlib.utils import maybe_get_ax, remove_chartjunk
from prettyplotlib.colors import set2, almost_black, getcolors
import numpy as np
import collections

def barh(*args, **kwargs):
    """
    Creates a bar plot, with white outlines and a fill color that defaults to
     the first teal-ish green in ColorBrewer's Set2. Optionally accepts
     grid='y' or grid='x' to draw a white grid over the bars,
     to show the scale. Almost like "erasing" some of the plot,
     but it adds more information!

    Can also add an annotation of the width of the barplots directly onto
    the bars with the `annotate` parameter, which can either be True,
    which will annotate the values, or a list of strings, which will annotate
    with the supplied strings.

    Can support stacked bars with the value of each stack shown on the stack
    (Added by Salil Banerjee)

    @param ax: matplotlib.axes instance
    @param top: Vector of values of where to put the top side of the bar
    @param width: Vector of values of the bar widths
    @param ytickabels: Vector of labels of the bar widths
    @param kwargs: Any additional arguments to matplotlib.bar()
    """
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)
    kwargs.setdefault('color', set2[0])
    kwargs.setdefault('edgecolor', 'white')
    middle = 0.4 if 'width' not in kwargs else kwargs['width']/2.0

    # Check if data contains stacks
    stacked = kwargs.pop('stacked',False)
    # Check if stack text should be included
    stack_text = kwargs.pop('stack_text',False)
    # Get legend if available
    legend = kwargs.pop('legend',False)

    top = args[0]
    width = np.array(args[1])

    # Label each individual bar, if xticklabels is provided
    ytickabels = kwargs.pop('yticklabels', None)
    # left+0.4 is the center of the bar
    yticks = np.array(top) + middle

    # Whether or not to annotate each bar with the width value
    annotate = kwargs.pop('annotate', False)

    # If no grid specified, don't draw one.
    grid = kwargs.pop('grid', None)

    cmap = kwargs.pop('cmap', False)
    if cmap:
        kwargs['edgecolor'] = almost_black
        if not stacked:
            kwargs['color'] = getcolors(cmap, width, 0)

    # Check if stacked and plot data accordingly
    if stacked:
        num_stacks, num_data = width.shape
        left = np.zeros(num_data)
        for i in np.arange(num_stacks):
            lst = list(args)
            lst[1] = width[i]
            args = tuple(lst)
            if cmap:
                kwargs['color'] = getcolors(cmap, width[i], i)
            else:
                kwargs['color'] = set2[i]
            kwargs['left'] = left
            rectangles = ax.barh(*args, **kwargs)
            left += width[i]
    else:
        rectangles = ax.barh(*args, **kwargs)

    # add legend
    if isinstance(legend, collections.Iterable):
        ax.legend(legend,loc='upper center',bbox_to_anchor=(0.5,1.11), ncol=5)

    # add whitespace padding on left
    ymin, ymax = ax.get_ylim()
    ymin -= 0.2
    if stacked:
        ymax = num_data
    ax.set_ylim(ymin, ymax)

    # If there are negative counts, remove the bottom axes
    # and add a line at y=0
    if any(w < 0 for w in width.tolist()):
        axes_to_remove = ['top', 'right', 'bottom']
        ax.vlines(x=0, ymin=ymin, ymax=ymax,
                  linewidths=0.75)
       #ax.hlines(y=0, xmin=xmin, xmax=xmax,
       #       linewidths=0.75)
    else:
        axes_to_remove = ['top', 'right']

    #Remove excess axes
    remove_chartjunk(ax, axes_to_remove, grid=grid)

    if stacked:
        data = width
        width = width.sum(axis=0)

    # Add the yticklabels if they are there
    if ytickabels is not None:
        ax.set_yticks(yticks)
        ax.set_yticklabels(ytickabels)

    if annotate or isinstance(annotate, collections.Iterable):
        annotate_xrange_factor = 0.050
        xmin, xmax = ax.get_xlim()
        xrange = xmax - xmin

        # Reset ymax and ymin so there's enough room to see the annotation of
        # the top-most
        if xmax > 0:
            xmax += xrange * 0.1
        if xmin < 0:
            xmin -= xrange * 0.1
        ax.set_xlim(xmin, xmax)
        xrange = xmax - xmin

        offset_ = xrange * annotate_xrange_factor
        if isinstance(annotate, collections.Iterable):
            annotations = map(str, annotate)
        else:
            annotations = ['%.3f' % w if type(w) is np.float_ else str(w)
                           for w in width]
        for y, w, annotation in zip(yticks, width, annotations):
            # Adjust the offset to account for negative bars
            offset = offset_ if w >= 0 else -1 * offset_
            # Finally, add the text to the axes
            ax.annotate(annotation, (w + offset, y),
                        verticalalignment='center',
                        horizontalalignment='center',
                        color=almost_black)

    # Text for each block of stack
    # This was partially inspired by the following article by Tableau software
    # http://www.tableausoftware.com/about/blog/2014/1/new-whitepaper-survey-data-less-ugly-more-understandable-27812
    if stack_text:
        left = np.zeros(num_data)
        max_w = max(width)
        for i in np.arange(num_stacks):
            for y, d, l in zip(yticks, data[i], left):
                if (d*100.0/max_w) > 2.0:
                    ax.text(l+d/2.0,y,d, ha='center', va='center', color=almost_black)
            left += data[i]

    return rectangles

########NEW FILE########
__FILENAME__ = _boxplot
__author__ = 'olga'

import matplotlib.pyplot as plt
from prettyplotlib.utils import remove_chartjunk, maybe_get_ax
from prettyplotlib import colors

def boxplot(*args, **kwargs):
    """
    Create a box-and-whisker plot showing the mean, 25th percentile, and 75th
    percentile. The difference from matplotlib is only the left axis line is
    shown, and ticklabels labeling each category of data can be added.

    @param ax:
    @param x:
    @param kwargs: Besides xticklabels, which is a prettyplotlib-specific
    argument which will label each individual boxplot, any argument for
    matplotlib.pyplot.boxplot will be accepted:
    http://matplotlib.org/api/axes_api.html#matplotlib.axes.Axes.boxplot
    @return:
    """
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)
    # If no ticklabels are specified, don't draw any
    xticklabels = kwargs.pop('xticklabels', None)
    fontsize = kwargs.pop('fontsize', 10)

    kwargs.setdefault('widths', 0.15)

    bp = ax.boxplot(*args, **kwargs)

    if xticklabels:
        ax.xaxis.set_ticklabels(xticklabels, fontsize=fontsize)

    show_caps = kwargs.pop('show_caps', True)
    show_ticks = kwargs.pop('show_ticks', False)

    remove_chartjunk(ax, ['top', 'right', 'bottom'], show_ticks=show_ticks)
    linewidth = 0.75

    blue = colors.set1[1]
    red = colors.set1[0]
    plt.setp(bp['boxes'], color=blue, linewidth=linewidth)
    plt.setp(bp['medians'], color=red)
    plt.setp(bp['whiskers'], color=blue, linestyle='solid',
             linewidth=linewidth)
    plt.setp(bp['fliers'], color=blue)
    if show_caps:
        plt.setp(bp['caps'], color=blue, linewidth=linewidth)
    else:
        plt.setp(bp['caps'], color='none')
    ax.spines['left']._linewidth = 0.5
    return bp 

########NEW FILE########
__FILENAME__ = _eventplot
__author__ = 'jgosmann'

from matplotlib.cbook import iterable

from prettyplotlib.utils import remove_chartjunk, maybe_get_ax
from prettyplotlib.colors import set2


def eventplot(*args, **kwargs):
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)
    show_ticks = kwargs.pop('show_ticks', False)
    alpha = kwargs.pop('alpha', 1.0)

    if len(args) > 0:
        positions = args[0]
    else:
        positions = kwargs['positions']

    if any(iterable(p) for p in positions):
        size = len(positions)
    else:
        size = 1

    kwargs.setdefault('colors', [c + (alpha,) for c in set2[:size]])

    event_collections = ax.eventplot(*args, **kwargs)
    remove_chartjunk(ax, ['top', 'right'], show_ticks=show_ticks)
    return event_collections

########NEW FILE########
__FILENAME__ = _fill_between
from prettyplotlib.utils import remove_chartjunk, maybe_get_ax, maybe_get_linewidth
from prettyplotlib.colors import almost_black, pretty


@pretty
def fill_between(*args, **kwargs):
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)

    lw = maybe_get_linewidth(**kwargs)
    kwargs['linewidths'] = lw

    if 'color' not in kwargs:
        # if no color is specified, cycle over the ones in this axis
        color_cycle = ax._get_lines.color_cycle
        kwargs['color'] = next(color_cycle)
    kwargs.setdefault('edgecolor', almost_black)

    show_ticks = kwargs.pop('show_ticks', False)

    lines = ax.fill_between(*args, **kwargs)
    remove_chartjunk(ax, ['top', 'right'], show_ticks=show_ticks)
    return lines 

########NEW FILE########
__FILENAME__ = _fill_betweenx
__author__ = 'olga'

from prettyplotlib.utils import remove_chartjunk, maybe_get_ax, maybe_get_linewidth
from prettyplotlib.colors import almost_black, pretty
from itertools import cycle
import matplotlib as mpl

@pretty
def fill_betweenx(*args, **kwargs):
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)

    lw = maybe_get_linewidth(**kwargs)
    kwargs['linewidths'] = lw

    if 'color' not in kwargs:
        # if no color is specified, cycle over the ones in this axis
        color_cycle = cycle(mpl.rcParams['axes.color_cycle'])
        kwargs['color'] = next(color_cycle)
    kwargs.setdefault('edgecolor', almost_black)

    show_ticks = kwargs.pop('show_ticks', False)

    lines = ax.fill_betweenx(*args, **kwargs)
    remove_chartjunk(ax, ['top', 'right'], show_ticks=show_ticks)
    return lines 

########NEW FILE########
__FILENAME__ = _hist
__author__ = 'olga'

from matplotlib.cbook import iterable

from prettyplotlib.utils import remove_chartjunk, maybe_get_ax
from prettyplotlib.colors import pretty


@pretty
def hist(*args, **kwargs):
    """
    Plots a histogram of the provided data. Can provide optional argument
    "grid='x'" or "grid='y'" to draw a white grid over the histogram. Almost like "erasing" some of the plot,
     but it adds more information!
    """
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)

    color_cycle = ax._get_lines.color_cycle
    # Reassign the default colors to Set2 by Colorbrewer
    if iterable(args[0]):
        if isinstance(args[0], list):
            ncolors = len(args[0])
        else:
            if len(args[0].shape) == 2:
                ncolors = args[0].shape[1]
            else:
                ncolors = 1
        kwargs.setdefault('color', [next(color_cycle) for _ in range(ncolors)])
    else:
        kwargs.setdefault('color', next(color_cycle))
    kwargs.setdefault('edgecolor', 'white')
    show_ticks = kwargs.pop('show_ticks', False)

    # If no grid specified, don't draw one.
    grid = kwargs.pop('grid', None)

    # print 'hist kwargs', kwargs
    patches = ax.hist(*args, **kwargs)
    remove_chartjunk(ax, ['top', 'right'], grid=grid, show_ticks=show_ticks)
    return patches

########NEW FILE########
__FILENAME__ = _legend
__author__ = 'olga'

from prettyplotlib.colors import light_grey, almost_black
from prettyplotlib.utils import maybe_get_ax


def legend(*args, **kwargs):
    """

    @param args:
    @type args:
    @param kwargs: Any keyword arguments to matplotlib's plt.legend()
    Optional 'facecolor' keyword to change the facecolor of the legend
    @type kwargs:
    @return:
    @rtype:
    """
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)
    facecolor = kwargs.pop('facecolor', light_grey)

    kwargs.setdefault('frameon', True)
    kwargs.setdefault('scatterpoints', True)

    legend = ax.legend(**kwargs)
    try:
        rect = legend.get_frame()
        rect.set_facecolor(facecolor)
        rect.set_linewidth(0.0)

        # Change the label colors in the legend to almost black
        # Change the legend label colors to almost black, too
        texts = legend.texts
        for t in texts:
            t.set_color(almost_black)
    except AttributeError:
        # There are no labled objects
        pass
    return legend

########NEW FILE########
__FILENAME__ = _pcolormesh
__author__ = 'olga'

import numpy as np

from prettyplotlib.colors import blue_red, blues_r, reds
from prettyplotlib.utils import remove_chartjunk, maybe_get_fig_ax

def pcolormesh(*args, **kwargs):
    """
    Use for large datasets

    Non-traditional `pcolormesh` kwargs are:
    - xticklabels, which will put x tick labels exactly in the center of the
    heatmap block
    - yticklables, which will put y tick labels exactly aligned in the center
     of the heatmap block
     - xticklabels_rotation, which can be either 'horizontal' or 'vertical'
     depending on how you want the xticklabels rotated. The default is
     'horizontal', but if you have xticklabels that are longer, you may want
     to do 'vertical' so they don't overlap.
     - yticklabels_rotation, which can also be either 'horizontal' or
     'vertical'. The default is 'horizontal' and in most cases,
     that's what you'll want to stick with. But the option is there if you
     want.
    - center_value, which will be the centered value for a divergent
    colormap, for example if you have data above and below zero, but you want
    the white part of the colormap to be equal to 10 rather than 0,
    then specify 'center_value=10'.
    """
    # Deal with arguments in kwargs that should be there, or need to be taken
    #  out
    fig, ax, args, kwargs = maybe_get_fig_ax(*args, **kwargs)

    x = args[0]

    kwargs.setdefault('vmax', x.max())
    kwargs.setdefault('vmin', x.min())

    center_value = kwargs.pop('center_value', 0)

    # If
    divergent_data = False
    if kwargs['vmax'] > 0 and kwargs['vmin'] < 0:
        divergent_data = True
        kwargs['vmax'] += center_value
        kwargs['vmin'] += center_value

    # If we have both negative and positive values, use a divergent colormap
    if 'cmap' not in kwargs:
        # Check if this is divergent
        if divergent_data:
            kwargs['cmap'] = blue_red
        elif kwargs['vmax'] <= 0:
                kwargs['cmap'] = blues_r
        elif kwargs['vmax'] > 0:
            kwargs['cmap'] = reds

    if 'xticklabels' in kwargs:
        xticklabels = kwargs['xticklabels']
        kwargs.pop('xticklabels')
    else:
        xticklabels = None
    if 'yticklabels' in kwargs:
        yticklabels = kwargs['yticklabels']
        kwargs.pop('yticklabels')
    else:
        yticklabels = None

    if 'xticklabels_rotation' in kwargs:
        xticklabels_rotation = kwargs['xticklabels_rotation']
        kwargs.pop('xticklabels_rotation')
    else:
        xticklabels_rotation = 'horizontal'
    if 'yticklabels_rotation' in kwargs:
        yticklabels_rotation = kwargs['yticklabels_rotation']
        kwargs.pop('yticklabels_rotation')
    else:
        yticklabels_rotation = 'horizontal'

    ax_colorbar = kwargs.pop('ax_colorbar', None)
    orientation_colorbar = kwargs.pop('orientation_colorbar', 'vertical')

    p = ax.pcolormesh(*args, **kwargs)
    ax.set_ylim(0, x.shape[0])

    # Get rid of ALL axes
    remove_chartjunk(ax, ['top', 'right', 'left', 'bottom'])

    if xticklabels is not None and any(xticklabels):
        xticks = np.arange(0.5, x.shape[1] + 0.5)
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels, rotation=xticklabels_rotation)
    if yticklabels is not None and any(yticklabels):
        yticks = np.arange(0.5, x.shape[0] + 0.5)
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels, rotation=yticklabels_rotation)

    # Show the scale of the colorbar
    fig.colorbar(p, cax=ax_colorbar, use_gridspec=True,
                 orientation=orientation_colorbar)
    return p

########NEW FILE########
__FILENAME__ = _plot
__author__ = 'olga'

from prettyplotlib.utils import remove_chartjunk, maybe_get_ax
from prettyplotlib.colors import pretty


@pretty
def plot(*args, **kwargs):
    ax, args, kwargs = maybe_get_ax(*args, **kwargs)
    show_ticks = kwargs.pop('show_ticks', False)

    lines = ax.plot(*args, **kwargs)
    remove_chartjunk(ax, ['top', 'right'], show_ticks=show_ticks)
    return lines

########NEW FILE########
__FILENAME__ = _scatter
__author__ = 'olga'

from prettyplotlib import utils
from prettyplotlib.colors import almost_black, pretty


@pretty
def scatter(*args, **kwargs):
    """
    This will plot a scatterplot of x and y, iterating over the ColorBrewer
    "Set2" color cycle unless a color is specified. The symbols produced are
    empty circles, with the outline in the color specified by either 'color'
    or 'edgecolor'. If you want to fill the circle, specify 'facecolor'.

    Besides the matplotlib scatter(), will also take the parameter
    @param show_ticks: Whether or not to show the x and y axis ticks
    """
    # Force 'color' to indicate the edge color, so the middle of the
    # scatter patches are empty. Can specify
    ax, args, kwargs = utils.maybe_get_ax(*args, **kwargs)

    if 'color' not in kwargs:
        # Assume that color means the edge color. You can assign the
        color_cycle = ax._get_lines.color_cycle
        kwargs['color'] = next(color_cycle)
    kwargs.setdefault('edgecolor', almost_black)
    kwargs.setdefault('alpha', 0.5)

    lw = utils.maybe_get_linewidth(**kwargs)
    kwargs['lw'] = lw

    show_ticks = kwargs.pop('show_ticks', False)

    scatterpoints = ax.scatter(*args, **kwargs)
    utils.remove_chartjunk(ax, ['top', 'right'], show_ticks=show_ticks)
    return scatterpoints 

########NEW FILE########
__FILENAME__ = test_bar
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import prettyplotlib as ppl
import numpy as np
import os
import string
import six

if six.PY3:
    UPPERCASE_CHARS = string.ascii_uppercase
else:
    UPPERCASE_CHARS = string.uppercase


@image_comparison(baseline_images=['bar'], extensions=['png'])
def test_bar():
    np.random.seed(14)
    ppl.bar(np.arange(10), np.abs(np.random.randn(10)))
    # fig.savefig('%s/baseline_images/test_bar/bar.png' %
    #             os.path.dirname(__file__))

@image_comparison(baseline_images=['bar_grid'], extensions=['png'])
def test_bar_grid():
    np.random.seed(14)
    ppl.bar(np.arange(10), np.abs(np.random.randn(10)), grid='y')
    # fig.savefig('%s/baseline_images/test_bar/bar_grid.png' %
    #             os.path.dirname(__file__))


@image_comparison(baseline_images=['bar_annotate'], extensions=['png'])
def test_bar_annotate():
    np.random.seed(14)
    ppl.bar(np.arange(10), np.abs(np.random.randn(10)), annotate=True)
    # fig.savefig('%s/baseline_images/test_bar/bar_annotate.png' %
    #             os.path.dirname(__file__))

@image_comparison(baseline_images=['bar_annotate_user'], extensions=['png'])
def test_bar_annotate_user():
    np.random.seed(14)
    ppl.bar(np.arange(10), np.abs(np.random.randn(10)),
            annotate=range(10,20))
    # fig.savefig('%s/baseline_images/test_bar/bar_annotate_user.png' %
    #             os.path.dirname(__file__))


@image_comparison(baseline_images=['bar_xticklabels'], extensions=['png'])
def test_bar_xticklabels():
    np.random.seed(14)
    n = 10
    ppl.bar(np.arange(n), np.abs(np.random.randn(n)),
            xticklabels=UPPERCASE_CHARS[:n])
    # fig.savefig('%s/baseline_images/test_bar/bar_xticklabels.png' %
    #             os.path.dirname(__file__))

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])

########NEW FILE########
__FILENAME__ = test_barh
__author__ = 'jan'

from matplotlib.testing.decorators import image_comparison
import prettyplotlib as ppl
import numpy as np
import os
import string
import six

if six.PY3:
    UPPERCASE_CHARS = string.ascii_uppercase
else:
    UPPERCASE_CHARS = string.uppercase


@image_comparison(baseline_images=['barh'], extensions=['png'])
def test_barh():
    np.random.seed(14)
    ppl.barh(np.arange(10), np.abs(np.random.randn(10)))
    # fig.savefig('%s/baseline_images/test_barh/bar.png' %
    #             os.path.dirname(os.path.abspath(__file__)))

@image_comparison(baseline_images=['barh_grid'], extensions=['png'])
def test_barh_grid():
    np.random.seed(14)
    ppl.barh(np.arange(10), np.abs(np.random.randn(10)), grid='x')
    # fig.savefig('%s/baseline_images/test_barh/bar_grid.png' %
    #              os.path.dirname(os.path.abspath(__file__)))


@image_comparison(baseline_images=['barh_annotate'], extensions=['png'])
def test_barh_annotate():
    np.random.seed(14)
    ppl.barh(np.arange(10), np.abs(np.random.randn(10)), annotate=True)
    # fig.savefig('%s/baseline_images/test_barh/bar_annotate.png' %
    #             os.path.dirname(os.path.abspath(__file__)))

@image_comparison(baseline_images=['barh_annotate_user'], extensions=['png'])
def test_barh_annotate_user():
    np.random.seed(14)
    ppl.barh(np.arange(10), np.abs(np.random.randn(10)),
            annotate=range(10,20))
    # fig.savefig('%s/baseline_images/test_barh/bar_annotate_user.png' %
    #             os.path.dirname(os.path.abspath(__file__)))


@image_comparison(baseline_images=['barh_xticklabels'], extensions=['png'])
def test_barh_xticklabels():
    np.random.seed(14)
    n = 10
    ppl.barh(np.arange(n), np.abs(np.random.randn(n)),
            yticklabels=UPPERCASE_CHARS[:n])
    # fig.savefig('%s/baseline_images/test_barh/bar_xticklabels.png' %
    #              os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])


########NEW FILE########
__FILENAME__ = test_boxplot
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import matplotlib.pyplot as plt
import numpy as np
import prettyplotlib as ppl
import os


@image_comparison(baseline_images=['boxplot'], extensions=['png'])
def test_boxplot():
    # Set the random seed for consistency
    np.random.seed(10)

    data = np.random.randn(8, 4)
    labels = ['A', 'B', 'C', 'D']

    fig, ax = plt.subplots()
    ppl.boxplot(ax, data, xticklabels=labels)
    # fig.savefig('%s/baseline_images/test_boxplot/boxplot.png' %
    #             os.path.dirname(__file__))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])

########NEW FILE########
__FILENAME__ = test_eventplot
__author__ = 'jgosmann'

from matplotlib.testing.decorators import image_comparison
import prettyplotlib as ppl
import numpy as np


@image_comparison(baseline_images=['eventplot'], extensions=['png'])
def test_plot():
    # Set the random seed for consistency
    np.random.seed(12)

    alpha = 0.5
    events = np.random.rand(10)
    ppl.eventplot(events, alpha=alpha)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])

########NEW FILE########
__FILENAME__ = test_hist
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import prettyplotlib as ppl
import numpy as np

@image_comparison(baseline_images=['hist'], extensions=['png'])
def test_scatter():
    # Set the random seed for consistency
    np.random.seed(12)

    # Show some color range
    for i in range(2):
        x = np.random.randn(1000)
        ppl.hist(x)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])
########NEW FILE########
__FILENAME__ = test_legend
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import numpy as np

import prettyplotlib as ppl


@image_comparison(baseline_images=['legend'], extensions=['png'])
def test_legend():
    # Set the random seed for consistency
    np.random.seed(12)

    # Show the whole color range
    for i in range(8):
        x = np.random.normal(loc=i, size=1000)
        y = np.random.normal(loc=i, size=1000)
        ppl.scatter(x, y, label=str(i))
    ppl.legend()
    # fig.savefig('%s/baseline_images/test_legend/legend.png' %
    #             os.path.dirname(__file__))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])
########NEW FILE########
__FILENAME__ = test_pcolormesh
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import prettyplotlib as ppl
import numpy as np
import os
import string
from prettyplotlib import brewer2mpl
from matplotlib.colors import LogNorm

import six

if six.PY3:
    LOWERCASE_CHARS = string.ascii_lowercase
    UPPERCASE_CHARS = string.ascii_uppercase
else:
    LOWERCASE_CHARS = string.lowercase
    UPPERCASE_CHARS = string.uppercase


@image_comparison(baseline_images=['pcolormesh'], extensions=['png'])
def test_pcolormesh():
    np.random.seed(10)

    ppl.pcolormesh(np.random.randn(10, 10))
    # fig.savefig('%s/baseline_images/test_pcolormesh/pcolormesh.png' %
    #             os.path.dirname(__file__))


@image_comparison(baseline_images=['pcolormesh_labels'], extensions=['png'])
def test_pcolormesh_labels():
    np.random.seed(10)

    ppl.pcolormesh(np.random.randn(10, 10),
                   xticklabels=UPPERCASE_CHARS[:10],
                   yticklabels=LOWERCASE_CHARS[-10:])
    # fig.savefig('%s/baseline_images/test_pcolormesh/pcolormesh_labels.png' %
    #             os.path.dirname(__file__))


@image_comparison(baseline_images=['pcolormesh_positive'], extensions=['png'])
def test_pcolormesh_positive():
    np.random.seed(10)

    ppl.pcolormesh(np.random.uniform(size=(10, 10)),
                   xticklabels=UPPERCASE_CHARS[:10],
                   yticklabels=LOWERCASE_CHARS[-10:])
    # fig.savefig('%s/baseline_images/test_pcolormesh/pcolormesh_positive.png' %
    #             os.path.dirname(__file__))

@image_comparison(baseline_images=['pcolormesh_negative'], extensions=['png'])
def test_pcolormesh_negative():
    np.random.seed(10)

    ppl.pcolormesh(-np.random.uniform(size=(10, 10)),
                   xticklabels=UPPERCASE_CHARS[:10],
                   yticklabels=LOWERCASE_CHARS[-10:])
    # fig.savefig('%s/baseline_images/test_pcolormesh/pcolormesh_negative.png' %
    #             os.path.dirname(__file__))


@image_comparison(baseline_images=['pcolormesh_other_cmap'], extensions=['png'])
def test_pcolormesh_other_cmap():
    purple_green = brewer2mpl.get_map('PRGn', 'diverging', 11).mpl_colormap
    np.random.seed(10)

    ppl.pcolormesh(np.random.randn(10, 10), cmap=purple_green)
    # fig.savefig('%s/baseline_images/test_pcolormesh/pcolormesh_other_cmap.png' %
    #             os.path.dirname(__file__))


@image_comparison(baseline_images=['pcolormesh_positive_other_cmap'],
                  extensions=['png'])
def test_pcolormesh_positive_other_cmap():
    red_purple = brewer2mpl.get_map('RdPu', 'sequential', 8).mpl_colormap
    np.random.seed(10)

    ppl.pcolormesh(np.random.uniform(size=(10, 10)),
                   xticklabels=UPPERCASE_CHARS[:10],
                   yticklabels=LOWERCASE_CHARS[-10:],
                   cmap=red_purple)
    # fig.savefig(
    #     '%s/baseline_images/test_pcolormesh/pcolormesh_positive_other_cmap.png' %
    #     os.path.dirname(__file__))

@image_comparison(baseline_images=['pcolormesh_lognorm'],
                  extensions=['png'])
def test_pcolormesh_lognorm():
    np.random.seed(10)

    x = np.abs(np.random.randn(10, 10))
    ppl.pcolormesh(x,
                   norm=LogNorm(vmin=x.min().min(), vmax=x.max().max()))
    # fig.savefig('%s/baseline_images/test_pcolormesh/test_pcolormesh_lognorm.png' %
    #             os.path.dirname(__file__))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])

########NEW FILE########
__FILENAME__ = test_plot
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import prettyplotlib as ppl
import numpy as np
import os


@image_comparison(baseline_images=['plot'], extensions=['png'])
def test_plot():
    # Set the random seed for consistency
    np.random.seed(12)

    # Show the whole color range
    for i in range(8):
        y = np.random.normal(size=1000).cumsum()
        x = np.arange(1000)

        # For now, you need to specify both x and y :(
        # Still figuring out how to specify just one
        ppl.plot(x, y, label=str(i))
    # fig.savefig('%s/baseline_images/test_plot/plot.png' %
    #             os.path.dirname(__file__))

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])
########NEW FILE########
__FILENAME__ = test_remove_chartjunk
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import numpy as np
import prettyplotlib as ppl
import matplotlib.pyplot as plt
from prettyplotlib.utils import remove_chartjunk
from prettyplotlib.colors import set2
import os

@image_comparison(baseline_images=['remove_chartjunk'], extensions=['png'])
def test_remove_chartjunk():
    fig, ax = plt.subplots(1)
    np.random.seed(14)
    ax.bar(np.arange(10), np.abs(np.random.randn(10)), color=set2[0],
           edgecolor='white')
    remove_chartjunk(ax, ['top', 'right'], grid='y', ticklabels='x')
    # fig.savefig('%s/baseline_images/test_remove_chartjunk/remove_chartjunk.png' %
    #             os.path.dirname(__file__))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])
########NEW FILE########
__FILENAME__ = test_scatter
__author__ = 'olga'

from matplotlib.testing.decorators import image_comparison
import prettyplotlib as ppl
import numpy as np
import os


@image_comparison(baseline_images=['scatter'], extensions=['png'])
def test_scatter():
    # Set the random seed for consistency
    np.random.seed(12)

    # Show the whole color range
    for i in range(8):
        x = np.random.normal(loc=i, size=1000)
        y = np.random.normal(loc=i, size=1000)
        ppl.scatter(x, y, label=str(i))
    # fig.savefig('%s/baseline_images/test_scatter/scatter.png' %
    #             os.path.dirname(__file__))


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=['-s', '--with-doctest'])
########NEW FILE########
