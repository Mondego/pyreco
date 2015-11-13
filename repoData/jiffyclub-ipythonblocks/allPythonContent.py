__FILENAME__ = ipythonblocks
"""
ipythonblocks provides a BlockGrid class that displays a colored grid in the
IPython Notebook. The colors can be manipulated, making it useful for
practicing control flow stuctures and quickly seeing the results.

"""

# This file is copyright 2013 by Matt Davis and covered by the license at
# https://github.com/jiffyclub/ipythonblocks/blob/master/LICENSE.txt

import copy
import collections
import json
import numbers
import os
import sys
import time
import uuid

from operator import iadd
from functools import reduce

from IPython.display import HTML, display, clear_output

__all__ = ('Block', 'BlockGrid', 'Pixel', 'ImageGrid',
           'InvalidColorSpec', 'ShapeMismatch', 'show_color',
           'embed_colorpicker', 'colors', 'fui_colors', '__version__')
__version__ = '1.7dev'

_TABLE = ('<style type="text/css">'
          'table.blockgrid {{border: none;}}'
          ' .blockgrid tr {{border: none;}}'
          ' .blockgrid td {{padding: 0px;}}'
          ' #blocks{0} td {{border: {1}px solid white;}}'
          '</style>'
          '<table id="blocks{0}" class="blockgrid"><tbody>{2}</tbody></table>')
_TR = '<tr>{0}</tr>'
_TD = ('<td title="{0}" style="width: {1}px; height: {1}px;'
       'background-color: {2};"></td>')
_RGB = 'rgb({0}, {1}, {2})'
_TITLE = 'Index: [{0}, {1}]&#10;Color: ({2}, {3}, {4})'

_SINGLE_ITEM = 'single item'
_SINGLE_ROW = 'single row'
_ROW_SLICE = 'row slice'
_DOUBLE_SLICE = 'double slice'

_SMALLEST_BLOCK = 1

_POST_URL = 'http://ipythonblocks.org/post'
_GET_URL_PUBLIC = 'http://ipythonblocks.org/get/{0}'
_GET_URL_SECRET = 'http://ipythonblocks.org/get/secret/{0}'


class InvalidColorSpec(Exception):
    """
    Error for a color value that is not a number.

    """
    pass


class ShapeMismatch(Exception):
    """
    Error for when a grid assigned to another doesn't have the same shape.

    """
    pass


def show_color(red, green, blue):
    """
    Show a given color in the IPython Notebook.

    Parameters
    ----------
    red, green, blue : int
        Integers on the range [0 - 255].

    """
    div = ('<div style="height: 60px; min-width: 200px; '
           'background-color: {0}"></div>')
    display(HTML(div.format(_RGB.format(red, green, blue))))


def embed_colorpicker():
    """
    Embed the web page www.colorpicker.com inside the IPython Notebook.

    """
    iframe = ('<iframe src="http://www.colorpicker.com/" '
              'width="100%" height="550px"></iframe>')
    display(HTML(iframe))


def _color_property(name):
    real_name = "_" + name

    @property
    def prop(self):
        return getattr(self, real_name)

    @prop.setter
    def prop(self, value):
        value = Block._check_value(value)
        setattr(self, real_name, value)

    return prop


def _flatten(thing, ignore_types=(str,)):
    """
    Yield a single item or str/unicode or recursively yield from iterables.

    Adapted from Beazley's Python Cookbook.

    """
    if isinstance(thing, collections.Iterable) and \
            not isinstance(thing, ignore_types):
        for i in thing:
            for x in _flatten(i):
                yield x
    else:
        yield thing


def _parse_str_cell_spec(cells, length):
    """
    Parse a single string cell specification representing either a single
    integer or a slice.

    Parameters
    ----------
    cells : str
        E.g. '5' for an int or '5:9' for a slice.
    length : int
        The number of items in the user's In history list. Used for
        normalizing slices.

    Returns
    -------
    cell_nos : list of int

    """
    if ':' not in cells:
        return _parse_cells_spec(int(cells), length)

    else:
        return _parse_cells_spec(slice(*[int(x) if x else None
                                         for x in cells.split(':')]),
                                 length)


def _parse_cells_spec(cells, length):
    """
    Used by _get_code_cells to parse a cell specification string into an
    ordered list of cell numbers.

    Parameters
    ----------
    cells : str, int, or slice
        Specification of which cells to retrieve. Can be a single number,
        a slice, or a combination of either separated by commas.
    length : int
        The number of items in the user's In history list. Used for
        normalizing slices.

    Returns
    -------
    cell_nos : list of int
        Ordered list of cell numbers derived from spec.

    """
    if isinstance(cells, int):
        return [cells]

    elif isinstance(cells, slice):
        return list(range(*cells.indices(length)))

    else:
        # string parsing
        return sorted(set(_flatten(_parse_str_cell_spec(s, length)
                                   for s in cells.split(','))))


def _get_code_cells(cells):
    """
    Get the inputs of the specified cells from the notebook.

    Parameters
    ----------
    cells : str, int, or slice
        Specification of which cells to retrieve. Can be a single number,
        a slice, or a combination of either separated by commas.

    Returns
    -------
    code : list of str
        Contents of cells as strings in chronological order.

    """
    In = get_ipython().user_ns['In']
    cells = _parse_cells_spec(cells, len(In))
    return [In[x] for x in cells]


class Block(object):
    """
    A colored square.

    Parameters
    ----------
    red, green, blue : int
        Integers on the range [0 - 255].
    size : int, optional
        Length of the sides of this block in pixels. One is the lower limit.

    Attributes
    ----------
    red, green, blue : int
        The color values for this `Block`. The color of the `Block` can be
        updated by assigning new values to these attributes.
    rgb : tuple of int
        Tuple of (red, green, blue) values. Can be used to set all the colors
        at once.
    row, col : int
        The zero-based grid position of this `Block`.
    size : int
        Length of the sides of this block in pixels. The block size can be
        changed by modifying this attribute. Note that one is the lower limit.

    """

    red = _color_property('red')
    green = _color_property('green')
    blue = _color_property('blue')

    def __init__(self, red, green, blue, size=20):
        self.red = red
        self.green = green
        self.blue = blue
        self.size = size

        self._row = None
        self._col = None

    @staticmethod
    def _check_value(value):
        """
        Check that a value is a number and constrain it to [0 - 255].

        """
        if not isinstance(value, numbers.Number):
            s = 'value must be a number. got {0}.'.format(value)
            raise InvalidColorSpec(s)

        return int(round(min(255, max(0, value))))

    @property
    def rgb(self):
        return (self._red, self._green, self._blue)

    @rgb.setter
    def rgb(self, colors):
        if len(colors) != 3:
            s = 'Setting colors requires three values: (red, green, blue).'
            raise ValueError(s)

        self.red, self.green, self.blue = colors

    @property
    def row(self):
        return self._row

    @property
    def col(self):
        return self._col

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = max(_SMALLEST_BLOCK, size)

    def set_colors(self, red, green, blue):
        """
        Updated block colors.

        Parameters
        ----------
        red, green, blue : int
            Integers on the range [0 - 255].

        """
        self.red = red
        self.green = green
        self.blue = blue

    def _update(self, other):
        if isinstance(other, Block):
            self.rgb = other.rgb
            self.size = other.size
        elif isinstance(other, collections.Sequence) and len(other) == 3:
            self.rgb = other
        else:
            errmsg = (
                'Value must be a Block or a sequence of 3 integers. '
                'Got {0!r}.'
            )
            raise ValueError(errmsg.format(other))

    @property
    def _td(self):
        """
        The HTML for a table cell with the background color of this Block.

        """
        title = _TITLE.format(self._row, self._col,
                              self._red, self._green, self._blue)
        rgb = _RGB.format(self._red, self._green, self._blue)
        return _TD.format(title, self._size, rgb)

    def _repr_html_(self):
        return _TABLE.format(uuid.uuid4(), 0, _TR.format(self._td))

    def show(self):
        display(HTML(self._repr_html_()))

    __hash__ = None

    def __eq__(self, other):
        if not isinstance(other, Block):
            return False
        return self.rgb == other.rgb and self.size == other.size

    def __str__(self):
        s = ['{0}'.format(self.__class__.__name__),
             'Color: ({0}, {1}, {2})'.format(self._red,
                                             self._green,
                                             self._blue)]

        # add position information if we have it
        if self._row is not None:
            s[0] += ' [{0}, {1}]'.format(self._row, self._col)

        return os.linesep.join(s)

    def __repr__(self):
        type_name = type(self).__name__
        return '{0}({1}, {2}, {3}, size={4})'.format(type_name,
                                                     self.red,
                                                     self.green,
                                                     self.blue,
                                                     self.size)


class BlockGrid(object):
    """
    A grid of blocks whose colors can be individually controlled.

    Parameters
    ----------
    width : int
        Number of blocks wide to make the grid.
    height : int
        Number of blocks high to make the grid.
    fill : tuple of int, optional
        An optional initial color for the grid, defaults to black.
        Specified as a tuple of (red, green, blue). E.g.: (10, 234, 198)
    block_size : int, optional
        Length of the sides of grid blocks in pixels. One is the lower limit.
    lines_on : bool, optional
        Whether or not to display lines between blocks.

    Attributes
    ----------
    width : int
        Number of blocks along the width of the grid.
    height : int
        Number of blocks along the height of the grid.
    shape : tuple of int
        A tuple of (width, height).
    block_size : int
        Length of the sides of grid blocks in pixels. The block size can be
        changed by modifying this attribute. Note that one is the lower limit.
    lines_on : bool
        Whether lines are shown between blocks when the grid is displayed.
        This attribute can used to toggle the whether the lines appear.

    """

    def __init__(self, width, height, fill=(0, 0, 0),
                 block_size=20, lines_on=True):
        self._width = width
        self._height = height
        self._block_size = block_size
        self.lines_on = lines_on
        self._initialize_grid(fill)

    def _initialize_grid(self, fill):
        grid = [[Block(*fill, size=self._block_size)
                for col in range(self.width)]
                for row in range(self.height)]

        self._grid = grid

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def shape(self):
        return (self._width, self._height)

    @property
    def block_size(self):
        return self._block_size

    @block_size.setter
    def block_size(self, size):
        self._block_size = size

        for block in self:
            block.size = size

    @property
    def lines_on(self):
        return self._lines_on

    @lines_on.setter
    def lines_on(self, value):
        if value not in (0, 1):
            s = 'lines_on may only be True or False.'
            raise ValueError(s)

        self._lines_on = value

    def __eq__(self, other):
        if not isinstance(other, BlockGrid):
            return False
        else:
            # compare the underlying grids
            return self._grid == other._grid

    def _view_from_grid(self, grid):
        """
        Make a new grid from a list of lists of Block objects.

        """
        new_width = len(grid[0])
        new_height = len(grid)

        new_BG = self.__class__(new_width, new_height,
                                block_size=self._block_size,
                                lines_on=self._lines_on)
        new_BG._grid = grid

        return new_BG

    @staticmethod
    def _categorize_index(index):
        """
        Used by __getitem__ and __setitem__ to determine whether the user
        is asking for a single item, single row, or some kind of slice.

        """
        if isinstance(index, int):
            return _SINGLE_ROW

        elif isinstance(index, slice):
            return _ROW_SLICE

        elif isinstance(index, tuple):
            if len(index) > 2:
                s = 'Invalid index, too many dimensions.'
                raise IndexError(s)

            elif len(index) == 1:
                s = 'Single indices must be integers, not tuple.'
                raise TypeError(s)

            if isinstance(index[0], slice):
                if isinstance(index[1], (int, slice)):
                    return _DOUBLE_SLICE

            if isinstance(index[1], slice):
                if isinstance(index[0], (int, slice)):
                    return _DOUBLE_SLICE

            elif isinstance(index[0], int) and isinstance(index[0], int):
                return _SINGLE_ITEM

        raise IndexError('Invalid index.')

    def __getitem__(self, index):
        ind_cat = self._categorize_index(index)

        if ind_cat == _SINGLE_ROW:
            return self._view_from_grid([self._grid[index]])

        elif ind_cat == _SINGLE_ITEM:
            block = self._grid[index[0]][index[1]]
            block._row, block._col = index
            return block

        elif ind_cat == _ROW_SLICE:
            return self._view_from_grid(self._grid[index])

        elif ind_cat == _DOUBLE_SLICE:
            new_grid = self._get_double_slice(index)
            return self._view_from_grid(new_grid)

    def __setitem__(self, index, value):
        thing = self[index]

        if isinstance(value, BlockGrid):
            if isinstance(thing, BlockGrid):
                if thing.shape != value.shape:
                    raise ShapeMismatch('Both sides of grid assignment must '
                                        'have the same shape.')

                for a, b in zip(thing, value):
                    a._update(b)

            else:
                raise TypeError('Cannot assign grid to single block.')

        elif isinstance(value, (collections.Iterable, Block)):
            for b in _flatten(thing):
                b._update(value)

    def _get_double_slice(self, index):
        sl_height, sl_width = index

        if isinstance(sl_width, int):
            if sl_width == -1:
                sl_width = slice(sl_width, None)
            else:
                sl_width = slice(sl_width, sl_width + 1)

        if isinstance(sl_height, int):
            if sl_height == -1:
                sl_height = slice(sl_height, None)
            else:
                sl_height = slice(sl_height, sl_height + 1)

        rows = self._grid[sl_height]
        grid = [r[sl_width] for r in rows]

        return grid

    def __iter__(self):
        for r in range(self.height):
            for c in range(self.width):
                yield self[r, c]

    def animate(self, stop_time=0.2):
        """
        Call this method in a loop definition to have your changes to the grid
        animated in the IPython Notebook.

        Parameters
        ----------
        stop_time : float
            Amount of time to pause between loop steps.

        """
        for block in self:
            self.show()
            time.sleep(stop_time)
            yield block
            clear_output()
        self.show()

    def _repr_html_(self):
        rows = range(self._height)
        cols = range(self._width)

        html = reduce(iadd,
                      (_TR.format(reduce(iadd,
                                         (self[r, c]._td
                                          for c in cols)))
                       for r in rows))

        return _TABLE.format(uuid.uuid4(), int(self._lines_on), html)

    def __str__(self):
        s = ['{0}'.format(self.__class__.__name__),
             'Shape: {0}'.format(self.shape)]

        return os.linesep.join(s)

    def copy(self):
        """
        Returns an independent copy of this BlockGrid.

        """
        return copy.deepcopy(self)

    def show(self):
        """
        Display colored grid as an HTML table.

        """
        display(HTML(self._repr_html_()))

    def flash(self, display_time=0.2):
        """
        Display the grid for a time.

        Useful for making an animation or iteratively displaying changes.

        Parameters
        ----------
        display_time : float
            Amount of time, in seconds, to display the grid.

        """
        self.show()
        time.sleep(display_time)
        clear_output()

    def to_text(self, filename=None):
        """
        Write a text file containing the size and block color information
        for this grid.

        If no file name is given the text is sent to stdout.

        Parameters
        ----------
        filename : str, optional
            File into which data will be written. Will be overwritten if
            it already exists.

        """
        if filename:
            f = open(filename, 'w')
        else:
            f = sys.stdout

        s = ['# width height', '{0} {1}'.format(self.width, self.height),
             '# block size', '{0}'.format(self.block_size),
             '# initial color', '0 0 0',
             '# row column red green blue']
        f.write(os.linesep.join(s) + os.linesep)

        for block in self:
            things = [str(x) for x in (block.row, block.col) + block.rgb]
            f.write(' '.join(things) + os.linesep)

        if filename:
            f.close()

    def _to_simple_grid(self):
        """
        Make a simple representation of the table: nested lists of
        of the rows containing tuples of (red, green, blue, size)
        for each of the blocks.

        Returns
        -------
        grid : list of lists
            No matter the class this method is called on the returned
            grid will be Python-style: row oriented with the top-left
            block in the [0][0] position.

        """
        return [[(x.red, x.green, x.blue, x.size) for x in row]
                for row in self._grid]

    def _construct_post_request(self, code_cells, secret):
        """
        Construct the request dictionary that will be posted
        to ipythonblocks.org.

        Parameters
        ----------
        code_cells : int, str, slice, or None
            Specify any code cells to be sent and displayed with the grid.
            You can specify a single cell, a Python, slice, or a combination
            as a string separated by commas.

            For example, '3,5,8:10' would send cells 3, 5, 8, and 9.
        secret : bool
            If True, this grid will not be shown randomly on ipythonblocks.org.

        Returns
        -------
        request : dict

        """
        if code_cells is not None:
            code_cells = _get_code_cells(code_cells)

        req = {
            'python_version': tuple(sys.version_info),
            'ipb_version': __version__,
            'ipb_class': self.__class__.__name__,
            'code_cells': code_cells,
            'secret': secret,
            'grid_data': {
                'lines_on': self.lines_on,
                'width': self.width,
                'height': self.height,
                'blocks': self._to_simple_grid()
            }
        }

        return req

    def post_to_web(self, code_cells=None, secret=False):
        """
        Post this grid to ipythonblocks.org and return a URL to
        view the grid on the web.

        Parameters
        ----------
        code_cells : int, str, or slice, optional
            Specify any code cells to be sent and displayed with the grid.
            You can specify a single cell, a Python, slice, or a combination
            as a string separated by commas.

            For example, '3,5,8:10' would send cells 3, 5, 8, and 9.
        secret : bool, optional
            If True, this grid will not be shown randomly on ipythonblocks.org.

        Returns
        -------
        url : str
            URL to view your grid on ipythonblocks.org.

        """
        import requests

        req = self._construct_post_request(code_cells, secret)
        response = requests.post(_POST_URL, data=json.dumps(req))
        response.raise_for_status()

        return response.json()['url']

    def _load_simple_grid(self, block_data):
        """
        Modify the grid to reflect the data in `block_data`, which
        should be a nested list of tuples as produced by `_to_simple_grid`.

        Parameters
        ----------
        block_data : list of lists
            Nested list of tuples as produced by `_to_simple_grid`.

        """
        if len(block_data) != self.height or \
                len(block_data[0]) != self.width:
            raise ShapeMismatch('block_data must have same shape as grid.')

        for row in range(self.height):
            for col in range(self.width):
                self._grid[row][col].rgb = block_data[row][col][:3]
                self._grid[row][col].size = block_data[row][col][3]

    @classmethod
    def from_web(cls, grid_id, secret=False):
        """
        Make a new BlockGrid from a grid on ipythonblocks.org.

        Parameters
        ----------
        grid_id : str
            ID of a grid on ipythonblocks.org. This will be the part of the
            URL after 'ipythonblocks.org/'.
        secret : bool, optional
            Whether or not the grid on ipythonblocks.org is secret.

        Returns
        -------
        grid : BlockGrid

        """
        import requests

        get_url = _GET_URL_PUBLIC if not secret else _GET_URL_SECRET
        resp = requests.get(get_url.format(grid_id))
        resp.raise_for_status()
        grid_spec = resp.json()

        grid = cls(grid_spec['width'], grid_spec['height'],
                   lines_on=grid_spec['lines_on'])
        grid._load_simple_grid(grid_spec['blocks'])

        return grid


class Pixel(Block):
    @property
    def x(self):
        """
        Horizontal coordinate of Pixel.

        """
        return self._col

    @property
    def y(self):
        """
        Vertical coordinate of Pixel.

        """
        return self._row

    @property
    def _td(self):
        """
        The HTML for a table cell with the background color of this Pixel.

        """
        title = _TITLE.format(self._col, self._row,
                              self._red, self._green, self._blue)
        rgb = _RGB.format(self._red, self._green, self._blue)
        return _TD.format(title, self._size, rgb)

    def __str__(self):
        s = ['{0}'.format(self.__class__.__name__),
             'Color: ({0}, {1}, {2})'.format(self._red,
                                             self._green,
                                             self._blue)]

        # add position information if we have it
        if self._row is not None:
            s[0] += ' [{0}, {1}]'.format(self._col, self._row)

        return os.linesep.join(s)


class ImageGrid(BlockGrid):
    """
    A grid of blocks whose colors can be individually controlled.

    Parameters
    ----------
    width : int
        Number of blocks wide to make the grid.
    height : int
        Number of blocks high to make the grid.
    fill : tuple of int, optional
        An optional initial color for the grid, defaults to black.
        Specified as a tuple of (red, green, blue). E.g.: (10, 234, 198)
    block_size : int, optional
        Length of the sides of grid blocks in pixels. One is the lower limit.
    lines_on : bool, optional
        Whether or not to display lines between blocks.
    origin : {'lower-left', 'upper-left'}, optional
        Set the location of the grid origin.

    Attributes
    ----------
    width : int
        Number of blocks along the width of the grid.
    height : int
        Number of blocks along the height of the grid.
    shape : tuple of int
        A tuple of (width, height).
    block_size : int
        Length of the sides of grid blocks in pixels.
    lines_on : bool
        Whether lines are shown between blocks when the grid is displayed.
        This attribute can used to toggle the whether the lines appear.
    origin : str
        The location of the grid origin.

    """

    def __init__(self, width, height, fill=(0, 0, 0),
                 block_size=20, lines_on=True, origin='lower-left'):
        super(ImageGrid, self).__init__(width, height, fill,
                                        block_size, lines_on)

        if origin not in ('lower-left', 'upper-left'):
            s = "origin keyword must be one of {'lower-left', 'upper-left'}."
            raise ValueError(s)

        self._origin = origin

    def _initialize_grid(self, fill):
        grid = [[Pixel(*fill, size=self._block_size)
                for col in range(self.width)]
                for row in range(self.height)]

        self._grid = grid

    @property
    def block_size(self):
        return self._block_size

    @property
    def origin(self):
        return self._origin

    def _transform_index(self, index):
        """
        Transform a single-item index from Python style coordinates to
        image style coordinates in which the first item refers to column and
        the second item refers to row. Also takes into account the
        location of the origin.

        """
        # in ImageGrid index is guaranteed to be a tuple.

        # first thing, switch the coordinates since ImageGrid is column
        # major and ._grid is row major.
        new_ind = [index[1], index[0]]

        # now take into account that the ImageGrid origin may be lower-left,
        # while the ._grid origin is upper-left.
        if self._origin == 'lower-left':
            if new_ind[0] >= 0:
                new_ind[0] = self._height - new_ind[0] - 1
            else:
                new_ind[0] = abs(new_ind[0]) - 1

        return tuple(new_ind)

    def __getitem__(self, index):
        ind_cat = self._categorize_index(index)

        # ImageGrid will only support single item indexing and 2D slices
        if ind_cat not in (_DOUBLE_SLICE, _SINGLE_ITEM):
            s = 'ImageGrid only supports 2D indexing.'
            raise IndexError(s)

        if ind_cat == _SINGLE_ITEM:
            # should be able to index ._grid with new_ind regardless of any
            # following coordinate transforms. let's just make sure.
            self._grid[index[1]][index[0]]

            real_index = self._transform_index(index)
            pixel = self._grid[real_index[0]][real_index[1]]
            pixel._col, pixel._row = index
            return pixel

        elif ind_cat == _DOUBLE_SLICE:
            new_grid = self._get_double_slice(index)
            return self._view_from_grid(new_grid)

    def _get_double_slice(self, index):
        cslice, rslice = index

        if isinstance(rslice, int):
            if rslice == -1:
                rslice = slice(rslice, None)
            else:
                rslice = slice(rslice, rslice + 1)

        if isinstance(cslice, int):
            if cslice == -1:
                cslice = slice(cslice, None)
            else:
                cslice = slice(cslice, cslice + 1)

        rows = range(self._height)[rslice]
        if self._origin == 'lower-left':
            rows = rows[::-1]

        cols = range(self._width)[cslice]

        new_grid = [[self[c, r] for c in cols] for r in rows]

        return new_grid

    def __iter__(self):
        for col in range(self.width):
            for row in range(self.height):
                yield self[col, row]

    def _repr_html_(self):
        rows = range(self._height)
        cols = range(self._width)

        if self._origin == 'lower-left':
            rows = rows[::-1]

        html = reduce(iadd,
                      (_TR.format(reduce(iadd,
                                         (self[c, r]._td
                                          for c in cols)))
                       for r in rows))

        return _TABLE.format(uuid.uuid4(), int(self._lines_on), html)

    @classmethod
    def from_web(cls, grid_id, secret=False, origin='lower-left'):
        """
        Make a new ImageGrid from a grid on ipythonblocks.org.

        Parameters
        ----------
        grid_id : str
            ID of a grid on ipythonblocks.org. This will be the part of the
            URL after 'ipythonblocks.org/'.
        secret : bool, optional
            Whether or not the grid on ipythonblocks.org is secret.
        origin : {'lower-left', 'upper-left'}, optional
            Set the location of the grid origin.

        Returns
        -------
        grid : ImageGrid

        """
        import requests

        get_url = _GET_URL_PUBLIC if not secret else _GET_URL_SECRET
        resp = requests.get(get_url.format(grid_id))
        resp.raise_for_status()
        grid_spec = resp.json()

        grid = cls(grid_spec['width'], grid_spec['height'],
                   lines_on=grid_spec['lines_on'], origin=origin)
        grid._load_simple_grid(grid_spec['blocks'])

        return grid


# As a convenience, provide some colors as a custom hybrid
# dictionary and object with the color names as attributes
class _ColorBunch(dict):
    """
    Customized dictionary that exposes its keys as attributes.

    """
    def __init__(self, colors):
        super(_ColorBunch, self).__init__(colors)
        self.__dict__.update(colors)


# HTML colors
colors = _ColorBunch({
    'AliceBlue': (240, 248, 255),
    'AntiqueWhite': (250, 235, 215),
    'Aqua': (0, 255, 255),
    'Aquamarine': (127, 255, 212),
    'Azure': (240, 255, 255),
    'Beige': (245, 245, 220),
    'Bisque': (255, 228, 196),
    'Black': (0, 0, 0),
    'BlanchedAlmond': (255, 235, 205),
    'Blue': (0, 0, 255),
    'BlueViolet': (138, 43, 226),
    'Brown': (165, 42, 42),
    'BurlyWood': (222, 184, 135),
    'CadetBlue': (95, 158, 160),
    'Chartreuse': (127, 255, 0),
    'Chocolate': (210, 105, 30),
    'Coral': (255, 127, 80),
    'CornflowerBlue': (100, 149, 237),
    'Cornsilk': (255, 248, 220),
    'Crimson': (220, 20, 60),
    'Cyan': (0, 255, 255),
    'DarkBlue': (0, 0, 139),
    'DarkCyan': (0, 139, 139),
    'DarkGoldenrod': (184, 134, 11),
    'DarkGray': (169, 169, 169),
    'DarkGreen': (0, 100, 0),
    'DarkKhaki': (189, 183, 107),
    'DarkMagenta': (139, 0, 139),
    'DarkOliveGreen': (85, 107, 47),
    'DarkOrange': (255, 140, 0),
    'DarkOrchid': (153, 50, 204),
    'DarkRed': (139, 0, 0),
    'DarkSalmon': (233, 150, 122),
    'DarkSeaGreen': (143, 188, 143),
    'DarkSlateBlue': (72, 61, 139),
    'DarkSlateGray': (47, 79, 79),
    'DarkTurquoise': (0, 206, 209),
    'DarkViolet': (148, 0, 211),
    'DeepPink': (255, 20, 147),
    'DeepSkyBlue': (0, 191, 255),
    'DimGray': (105, 105, 105),
    'DodgerBlue': (30, 144, 255),
    'FireBrick': (178, 34, 34),
    'FloralWhite': (255, 250, 240),
    'ForestGreen': (34, 139, 34),
    'Fuchsia': (255, 0, 255),
    'Gainsboro': (220, 220, 220),
    'GhostWhite': (248, 248, 255),
    'Gold': (255, 215, 0),
    'Goldenrod': (218, 165, 32),
    'Gray': (128, 128, 128),
    'Green': (0, 128, 0),
    'GreenYellow': (173, 255, 47),
    'Honeydew': (240, 255, 240),
    'HotPink': (255, 105, 180),
    'IndianRed': (205, 92, 92),
    'Indigo': (75, 0, 130),
    'Ivory': (255, 255, 240),
    'Khaki': (240, 230, 140),
    'Lavender': (230, 230, 250),
    'LavenderBlush': (255, 240, 245),
    'LawnGreen': (124, 252, 0),
    'LemonChiffon': (255, 250, 205),
    'LightBlue': (173, 216, 230),
    'LightCoral': (240, 128, 128),
    'LightCyan': (224, 255, 255),
    'LightGoldenrodYellow': (250, 250, 210),
    'LightGray': (211, 211, 211),
    'LightGreen': (144, 238, 144),
    'LightPink': (255, 182, 193),
    'LightSalmon': (255, 160, 122),
    'LightSeaGreen': (32, 178, 170),
    'LightSkyBlue': (135, 206, 250),
    'LightSlateGray': (119, 136, 153),
    'LightSteelBlue': (176, 196, 222),
    'LightYellow': (255, 255, 224),
    'Lime': (0, 255, 0),
    'LimeGreen': (50, 205, 50),
    'Linen': (250, 240, 230),
    'Magenta': (255, 0, 255),
    'Maroon': (128, 0, 0),
    'MediumAquamarine': (102, 205, 170),
    'MediumBlue': (0, 0, 205),
    'MediumOrchid': (186, 85, 211),
    'MediumPurple': (147, 112, 219),
    'MediumSeaGreen': (60, 179, 113),
    'MediumSlateBlue': (123, 104, 238),
    'MediumSpringGreen': (0, 250, 154),
    'MediumTurquoise': (72, 209, 204),
    'MediumVioletRed': (199, 21, 133),
    'MidnightBlue': (25, 25, 112),
    'MintCream': (245, 255, 250),
    'MistyRose': (255, 228, 225),
    'Moccasin': (255, 228, 181),
    'NavajoWhite': (255, 222, 173),
    'Navy': (0, 0, 128),
    'OldLace': (253, 245, 230),
    'Olive': (128, 128, 0),
    'OliveDrab': (107, 142, 35),
    'Orange': (255, 165, 0),
    'OrangeRed': (255, 69, 0),
    'Orchid': (218, 112, 214),
    'PaleGoldenrod': (238, 232, 170),
    'PaleGreen': (152, 251, 152),
    'PaleTurquoise': (175, 238, 238),
    'PaleVioletRed': (219, 112, 147),
    'PapayaWhip': (255, 239, 213),
    'PeachPuff': (255, 218, 185),
    'Peru': (205, 133, 63),
    'Pink': (255, 192, 203),
    'Plum': (221, 160, 221),
    'PowderBlue': (176, 224, 230),
    'Purple': (128, 0, 128),
    'Red': (255, 0, 0),
    'RosyBrown': (188, 143, 143),
    'RoyalBlue': (65, 105, 225),
    'SaddleBrown': (139, 69, 19),
    'Salmon': (250, 128, 114),
    'SandyBrown': (244, 164, 96),
    'SeaGreen': (46, 139, 87),
    'Seashell': (255, 245, 238),
    'Sienna': (160, 82, 45),
    'Silver': (192, 192, 192),
    'SkyBlue': (135, 206, 235),
    'SlateBlue': (106, 90, 205),
    'SlateGray': (112, 128, 144),
    'Snow': (255, 250, 250),
    'SpringGreen': (0, 255, 127),
    'SteelBlue': (70, 130, 180),
    'Tan': (210, 180, 140),
    'Teal': (0, 128, 128),
    'Thistle': (216, 191, 216),
    'Tomato': (255, 99, 71),
    'Turquoise': (64, 224, 208),
    'Violet': (238, 130, 238),
    'Wheat': (245, 222, 179),
    'White': (255, 255, 255),
    'WhiteSmoke': (245, 245, 245),
    'Yellow': (255, 255, 0),
    'YellowGreen': (154, 205, 50)
})


# Flat UI colors: http://flatuicolors.com/
fui_colors = _ColorBunch({
    'Alizarin': (231, 76, 60),
    'Pomegranate': (192, 57, 43),
    'Carrot': (230, 126, 34),
    'Pumpkin': (211, 84, 0),
    'SunFlower': (241, 196, 15),
    'Orange': (243, 156, 18),
    'Emerald': (46, 204, 113),
    'Nephritis': (39, 174, 96),
    'Turquoise': (26, 188, 156),
    'GreenSea': (22, 160, 133),
    'PeterRiver': (52, 152, 219),
    'BelizeHole': (41, 128, 185),
    'Amethyst': (155, 89, 182),
    'Wisteria': (142, 68, 173),
    'WetAsphalt': (52, 73, 94),
    'MidnightBlue': (44, 62, 80),
    'Concrete': (149, 165, 166),
    'Asbestos': (127, 140, 141),
    'Clouds': (236, 240, 241),
    'Silver': (189, 195, 199)
})

########NEW FILE########
__FILENAME__ = test_block
import os
import pytest

from .. import ipythonblocks


@pytest.fixture
def basic_block():
    return ipythonblocks.Block(5, 6, 7, size=20)


def test_basic_api(basic_block):
    """
    Check that inputs are going to the right attributes and that assignment
    works when it should and not when it shouldn't.

    """
    bb = basic_block

    assert bb.rgb == (5, 6, 7)

    assert bb.red == 5
    bb.red = 1
    assert bb.red == 1

    assert bb.green == 6
    bb.green = 2
    assert bb.green == 2

    assert bb.blue == 7
    bb.blue = 3
    assert bb.blue == 3

    assert bb.rgb == (1, 2, 3)

    assert bb.size == 20
    bb.size = 10
    assert bb.size == 10

    assert bb.row is None
    with pytest.raises(AttributeError):
        bb.row = 5

    assert bb.col is None
    with pytest.raises(AttributeError):
        bb.col = 5


def test_attribute_limits(basic_block):
    """
    Color and size attributes have some builtin limits, test that they
    are respected.

    """
    bb = basic_block

    bb.red = -50
    assert bb.red == 0

    bb.green = 1000
    assert bb.green == 255

    bb.size = -200
    assert bb.size == ipythonblocks._SMALLEST_BLOCK


def test_check_value(basic_block):
    """
    Test the Block._check_value method that enforces color limits,
    converts to int, and checks values are numbers.

    """
    bb = basic_block

    bb.red = 4.56
    assert isinstance(bb.red, int)
    assert bb.red == 5

    bb.blue = 200.1
    assert isinstance(bb.blue, int)
    assert bb.blue == 200

    with pytest.raises(ipythonblocks.InvalidColorSpec):
        bb.green = 'green'


def test_set_colors(basic_block):
    """
    Test the Block.set_colors method.

    """
    bb = basic_block

    bb.set_colors(200, 201, 202)

    assert bb.red == 200
    assert bb.green == 201
    assert bb.blue == 202


def test_rgb_attr(basic_block):
    """
    Test out the .rgb attribute.

    """
    bb = basic_block

    assert bb.rgb == (5, 6, 7)

    bb.rgb = (1, 2, 3)
    assert bb.rgb == (1, 2, 3)
    assert bb._red == 1
    assert bb._green == 2
    assert bb._blue == 3

    with pytest.raises(ValueError):
        bb.rgb = (1, 2)

    with pytest.raises(ValueError):
        bb.rgb = (4, 5, 6, 7, 8)


def test_td(basic_block):
    """
    Test the Block._td proerty that returns an HTML table cell.

    """
    bb = basic_block

    bb._row = 1
    bb._col = 2

    title = ipythonblocks._TITLE.format(bb._row, bb._col,
                                        bb.red, bb.green, bb.blue)
    rgb = ipythonblocks._RGB.format(bb.red, bb.green, bb.blue)
    td = ipythonblocks._TD.format(title, bb.size, rgb)

    assert bb._td == td


def test_repr_html(basic_block, monkeypatch):
    """
    Test the Block._repr_html_ method that returns a single cell HTML table.

    """
    from .test_blockgrid import uuid, fake_uuid

    bb = basic_block

    monkeypatch.setattr(uuid, 'uuid4', fake_uuid)

    table = ipythonblocks._TABLE.format(fake_uuid(), 0,
                                        ipythonblocks._TR.format(bb._td))

    assert bb._repr_html_() == table


def test_str1(basic_block):
    """
    Test the Block.__str__ method used with print.

    """
    bb = basic_block

    s = os.linesep.join(['Block', 'Color: (5, 6, 7)'])

    assert bb.__str__() == s


def test_str2(basic_block):
    """
    Test the Block.__str__ method used with print.

    """
    bb = basic_block
    bb._row = 8
    bb._col = 9

    s = os.linesep.join(['Block [8, 9]', 'Color: (5, 6, 7)'])

    assert bb.__str__() == s

def test_repr(basic_block):
    assert repr(basic_block) == "Block(5, 6, 7, size=20)"

def test_eq():
    b1 = ipythonblocks.Block(0, 0, 0)
    b2 = ipythonblocks.Block(0, 0, 0)
    b3 = ipythonblocks.Block(1, 1, 1)
    b4 = ipythonblocks.Block(0, 0, 0, size=30)

    assert b1 == b1
    assert b1 == b2
    assert b1 != b3
    assert b1 != b4
    assert b1 != 42

def test_hash(basic_block):
    with pytest.raises(TypeError):
        set([basic_block])

def test_update():
    b1 = ipythonblocks.Block(0, 0, 0)
    b2 = ipythonblocks.Block(1, 1, 1, size=30)

    b1._update((42, 42, 42))
    assert b1.rgb == (42, 42, 42)

    b1._update(b2)
    assert b1.rgb == b2.rgb
    assert b1.size == b2.size

    with pytest.raises(ValueError):
        b1._update((1, 2, 3, 4))

########NEW FILE########
__FILENAME__ = test_blockgrid
import os
import uuid
import pytest

from .. import ipythonblocks


def fake_uuid():
    return 'abc'


@pytest.fixture
def basic_grid():
    return ipythonblocks.BlockGrid(5, 6, (1, 2, 3), 20, True)


def test_basic_api(basic_grid):
    """
    Check that inputs are going to the right attributes and that assignment
    works when it should and not when it shouldn't.

    """
    bg = basic_grid

    assert bg.width == 5
    with pytest.raises(AttributeError):
        bg.width = 20

    assert bg.height == 6
    with pytest.raises(AttributeError):
        bg.height = 20

    assert bg.shape == (5, 6)
    assert bg.block_size == 20
    assert bg.lines_on is True


def test_grid_init(basic_grid):
    """
    Test that the grid is properly initialized.

    """
    bg = basic_grid

    for r in range(bg.height):
        for c in range(bg.width):
            assert bg[r, c].size == 20
            assert bg[r, c].red == 1
            assert bg[r, c].green == 2
            assert bg[r, c].blue == 3
            assert bg[r, c].row == r
            assert bg[r, c].col == c


def test_change_block_size(basic_grid):
    """
    Test that all blocks are properly resized when changing the
    BlockGrid.block_size attribute.

    """
    bg = basic_grid

    bg.block_size = 10
    assert bg.block_size == 10

    for block in bg:
        assert block.size == 10


def test_change_lines_on(basic_grid):
    """
    Test changing the BlockGrid.lines_on attribute.

    """
    bg = basic_grid

    assert bg.lines_on is True

    bg.lines_on = False
    assert bg.lines_on is False

    with pytest.raises(ValueError):
        bg.lines_on = 5

    with pytest.raises(ValueError):
        bg.lines_on = 'asdf'


def test_view(basic_grid):
    """
    Check that getting a new BlockGrid object via slicing returns a view
    and not a copy.

    """
    bg = basic_grid
    ng = bg[:2, :2]

    ng[1, 1].set_colors(200, 201, 202)

    for block in (ng[1, 1], bg[1, 1]):
        assert block.red == 200
        assert block.green == 201
        assert block.blue == 202


def test_view_coords(basic_grid):
    """
    Make sure that when we get a view that it has its own appropriate
    coordinates.

    """
    ng = basic_grid[-2:, -2:]

    coords = ((0, 0), (0, 1), (1, 0), (1, 1))

    for b, c in zip(ng, coords):
        assert b.row == c[0]
        assert b.col == c[1]


def test_copy(basic_grid):
    """
    Check that getting a new BlockGrid via BlockGrid.copy returns a totally
    independent copy and not a view.

    """
    bg = basic_grid
    ng = bg[:2, :2].copy()

    ng[1, 1].set_colors(200, 201, 202)

    assert ng[1, 1].red == 200
    assert ng[1, 1].green == 201
    assert ng[1, 1].blue == 202
    assert bg[1, 1].red == 1
    assert bg[1, 1].green == 2
    assert bg[1, 1].blue == 3


def test_str(basic_grid):
    """
    Test the BlockGrid.__str__ method used with print.

    """
    bg = basic_grid

    s = os.linesep.join(['BlockGrid', 'Shape: (5, 6)'])

    assert bg.__str__() == s


def test_repr_html(monkeypatch):
    """
    HTML repr should be the same for a 1, 1 BlockGrid as for a single Block.
    (As long as the BlockGrid border is off.)

    """
    bg = ipythonblocks.BlockGrid(1, 1, lines_on=False)

    monkeypatch.setattr(uuid, 'uuid4', fake_uuid)

    assert bg._repr_html_() == bg[0, 0]._repr_html_()


def test_iter():
    """
    Test that we do complete, row first iteration.

    """
    bg = ipythonblocks.BlockGrid(2, 2)

    coords = ((0, 0), (0, 1), (1, 0), (1, 1))

    for b, c in zip(bg, coords):
        assert b.row == c[0]
        assert b.col == c[1]


def test_bad_index(basic_grid):
    """
    Test for the correct errors with bad indices.

    """
    bg = basic_grid

    with pytest.raises(IndexError):
        bg[1, 2, 3, 4]

    with pytest.raises(IndexError):
        bg[{4: 5}]

    with pytest.raises(TypeError):
        bg[1, ]

    with pytest.raises(IndexError):
        bg[0, 5]

    with pytest.raises(IndexError):
        bg[6, 0]


def test_bad_colors(basic_grid):
    """
    Make sure this gets the right error when trying to assign something
    other than three integers.

    """
    with pytest.raises(ValueError):
        basic_grid[0, 0] = (1, 2, 3, 4)


def test_getitem(basic_grid):
    """
    Exercise a bunch of different indexing.

    """
    bg = basic_grid

    # single block
    block = bg[1, 2]

    assert isinstance(block, ipythonblocks.Block)
    assert block.row == 1
    assert block.col == 2

    # single row
    ng = bg[2]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (bg.width, 1)

    # two rows
    ng = bg[1:3]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (bg.width, 2)

    # one row via a slice
    ng = bg[2, :]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (bg.width, 1)

    # one column
    ng = bg[:, 2]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (1, bg.height)

    # 2 x 2 subgrid
    ng = bg[:2, :2]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (2, 2)

    # strided slicing
    ng = bg[::3, ::3]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (2, 2)

    # one column / one row with a -1 index
    # testing fix for #7
    ng = bg[-1, :]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (bg.width, 1)

    ng = bg[1:4, -1]

    assert isinstance(ng, ipythonblocks.BlockGrid)
    assert ng.shape == (1, 3)


def test_setitem(basic_grid):
    """
    Test assigning colors to blocks.

    """
    bg = basic_grid
    colors = (21, 22, 23)

    # single block
    bg[0, 0] = colors
    assert bg[0, 0].rgb == colors

    # single row
    bg[2] = colors
    for block in bg[2]:
        assert block.rgb == colors

    # two rows
    bg[3:5] = colors
    for block in bg[3:5]:
        assert block.rgb == colors

    # one row via a slice
    bg[1, :] = colors
    for block in bg[1, :]:
        assert block.rgb == colors

    # one column
    bg[:, 5] = colors
    for block in bg[:, 5]:
        assert block.rgb == colors

    # 2 x 2 subgrid
    bg[:2, :2] = colors
    for block in bg[:2, :2]:
        assert block.rgb == colors

    # strided slicing
    bg[::3, ::3] = colors
    for block in bg[::3, ::3]:
        assert block.rgb == colors


def test_setitem_to_block(basic_grid):
    """
    Test assigning a Block to a BlockGrid.
    """
    bg = basic_grid
    bg[0, 0] = (0, 0, 0)
    bg[1, 1] = bg[0, 0]
    assert bg[0, 0] == bg[1, 1]
    assert bg[1, 1].rgb == (0, 0, 0)


def test_setitem_with_grid(basic_grid):
    og = basic_grid.copy()
    og[:] = (4, 5, 6)

    basic_grid[:1, :2] = og[-1:, -2:]

    for b in basic_grid:
        if b.row < 1 and b.col < 2:
            assert b.rgb == (4, 5, 6)
        else:
            assert b.rgb == (1, 2, 3)


def test_setitem_raises(basic_grid):
    og = basic_grid.copy()

    with pytest.raises(ipythonblocks.ShapeMismatch):
        basic_grid[:, :] = og[:2, :2]

    with pytest.raises(TypeError):
        basic_grid[0, 0] = og[:2, :2]


def test_to_text(capsys):
    """
    Test using the BlockGrid.to_text method.

    """
    bg = ipythonblocks.BlockGrid(2, 1, block_size=20)

    bg[0, 0].rgb = (1, 2, 3)
    bg[0, 1].rgb = (4, 5, 6)

    ref = ['# width height',
           '2 1',
           '# block size',
           '20',
           '# initial color',
           '0 0 0',
           '# row column red green blue',
           '0 0 1 2 3',
           '0 1 4 5 6']
    ref = os.linesep.join(ref) + os.linesep

    bg.to_text()
    out, err = capsys.readouterr()

    assert out == ref

########NEW FILE########
__FILENAME__ = test_imagegrid
import pytest

from .. import ipythonblocks


@pytest.fixture
def upper_left():
    return ipythonblocks.ImageGrid(2, 3, (7, 8, 9), 20, True, 'upper-left')


@pytest.fixture
def lower_left():
    return ipythonblocks.ImageGrid(2, 3, (7, 8, 9), 20, True, 'lower-left')


def test_init_bad_origin():
    """
    Test for an error with a bad origin keyword.

    """
    with pytest.raises(ValueError):
        ipythonblocks.ImageGrid(5, 6, origin='nowhere')


def test_basic_api(upper_left, lower_left):
    """
    Test basic interfaces different from BlockGrid.

    """
    ul = upper_left
    ll = lower_left

    assert ul.origin == 'upper-left'
    assert ll.origin == 'lower-left'

    with pytest.raises(AttributeError):
        ul.block_size = 50


def test_getitem_bad_index_ul(upper_left):
    ul = upper_left

    with pytest.raises(IndexError):
        ul[1]

    with pytest.raises(IndexError):
        ul[1:]

    with pytest.raises(IndexError):
        ul[0, 3]

    with pytest.raises(IndexError):
        ul[2, 0]


def test_getitem_bad_index_ll(lower_left):
    ll = lower_left

    with pytest.raises(IndexError):
        ll[1]

    with pytest.raises(IndexError):
        ll[1:]

    with pytest.raises(IndexError):
        ll[0, 3]

    with pytest.raises(IndexError):
        ll[2, 0]


def test_setitem_bad_index(upper_left):
    ul = upper_left

    with pytest.raises(IndexError):
        ul[1] = (4, 5, 6)

    with pytest.raises(IndexError):
        ul[1:] = (4, 5, 6)


def test_getitem_upper_left_single(upper_left):
    ul = upper_left

    for row in range(ul.height):
        for col in range(ul.width):
            assert ul[col, row] is ul._grid[row][col]


def test_getitem_upper_left_slice(upper_left):
    ul = upper_left

    ng = ul[:1, :2]

    assert ng.width == 1
    assert ng.height == 2
    assert ng._grid == [[ul._grid[0][0]], [ul._grid[1][0]]]


def test_getitem_lower_left_single(lower_left):
    ll = lower_left

    for row in range(ll.height):
        for col in range(ll.width):
            trow = ll.height - row - 1
            assert ll[col, row] is ll._grid[trow][col]


def test_getitem_lower_left_single_neg(lower_left):
    ll = lower_left

    ll[1, 2] = (1, 2, 3)

    pix = ll[-1, -1]

    assert pix.red == 1
    assert pix.green == 2
    assert pix.blue == 3


def test_getitem_lower_left_slice(lower_left):
    ll = lower_left

    ng = ll[:1, :2]

    assert ng.width == 1
    assert ng.height == 2
    assert ng._grid == [[ll._grid[-2][0]], [ll._grid[-1][0]]]


def test_setitem_lower_left_single(lower_left):
    ll = lower_left

    ll[0, 1].set_colors(201, 202, 203)

    assert ll._grid[-2][0].red == 201
    assert ll._grid[-2][0].green == 202
    assert ll._grid[-2][0].blue == 203


def test_setitem_lower_left_slice(lower_left):
    ll = lower_left

    ll[:, ::2] = (201, 202, 203)

    for pix in ll._grid[0]:
        assert pix.red == 201
        assert pix.green == 202
        assert pix.blue == 203

    for pix in ll._grid[2]:
        assert pix.red == 201
        assert pix.green == 202
        assert pix.blue == 203


def test_slice_assignment(lower_left):
    ll = lower_left

    ll[1, 1] = (42, 42, 42)
    ll[0, 0] = ll[1, 1]
    assert ll[0, 0].rgb == (42, 42, 42)


def test_setitem_with_grid_ul(upper_left):
    og = upper_left.copy()
    og[:, :] = (4, 5, 6)

    upper_left[:1, :2] = og[-1:, -2:]

    for b in upper_left:
        if b.col < 1 and b.row < 2:
            assert b.rgb == (4, 5, 6)
        else:
            assert b.rgb == (7, 8, 9)


def test_setitem_with_grid_ll(lower_left):
    og = lower_left.copy()
    og[:, :] = (4, 5, 6)

    lower_left[:1, :2] = og[-1:, -2:]

    for b in lower_left:
        if b.col < 1 and b.row < 2:
            assert b.rgb == (4, 5, 6)
        else:
            assert b.rgb == (7, 8, 9)

########NEW FILE########
__FILENAME__ = test_ipborg
"""
Tests for ipythonblocks communication with ipythonblocks.org.

"""

import json
import string
import sys

import mock
import pytest
import responses

from .. import ipythonblocks as ipb

A10 = [a for a in string.ascii_lowercase[:10]]


def setup_module(module):
    """
    mock out the get_ipython() function for the tests.

    """
    def get_ipython():
        class ip(object):
            user_ns = {'In': A10}
        return ip()
    ipb.get_ipython = get_ipython


def teardown_module(module):
    del ipb.get_ipython


@pytest.fixture
def data_2x2():
    return [[(1, 2, 3, 4), (5, 6, 7, 8)],
            [(9, 10, 11, 12), (13, 14, 15, 16)]]


@pytest.fixture
def block_grid(data_2x2):
    bg = ipb.BlockGrid(2, 2)
    bg[0, 0].rgb = data_2x2[0][0][:3]
    bg[0, 0].size = data_2x2[0][0][3]
    bg[0, 1].rgb = data_2x2[0][1][:3]
    bg[0, 1].size = data_2x2[0][1][3]
    bg[1, 0].rgb = data_2x2[1][0][:3]
    bg[1, 0].size = data_2x2[1][0][3]
    bg[1, 1].rgb = data_2x2[1][1][:3]
    bg[1, 1].size = data_2x2[1][1][3]
    return bg


@pytest.fixture
def image_grid_ll(data_2x2):
    ig = ipb.ImageGrid(2, 2, origin='lower-left')
    ig[0, 0].rgb = data_2x2[1][0][:3]
    ig[0, 0].size = data_2x2[1][0][3]
    ig[0, 1].rgb = data_2x2[0][0][:3]
    ig[0, 1].size = data_2x2[0][0][3]
    ig[1, 0].rgb = data_2x2[1][1][:3]
    ig[1, 0].size = data_2x2[1][1][3]
    ig[1, 1].rgb = data_2x2[0][1][:3]
    ig[1, 1].size = data_2x2[0][1][3]
    return ig


@pytest.fixture
def image_grid_ul(data_2x2):
    ig = ipb.ImageGrid(2, 2, origin='upper-left')
    ig[0, 0].rgb = data_2x2[0][0][:3]
    ig[0, 0].size = data_2x2[0][0][3]
    ig[0, 1].rgb = data_2x2[1][0][:3]
    ig[0, 1].size = data_2x2[1][0][3]
    ig[1, 0].rgb = data_2x2[0][1][:3]
    ig[1, 0].size = data_2x2[0][1][3]
    ig[1, 1].rgb = data_2x2[1][1][:3]
    ig[1, 1].size = data_2x2[1][1][3]
    return ig


class Test_parse_cells_spec(object):
    def test_single_int(self):
        assert ipb._parse_cells_spec(5, 100) == [5]

    def test_single_int_str(self):
        assert ipb._parse_cells_spec('5', 100) == [5]

    def test_multi_int_str(self):
        assert ipb._parse_cells_spec('2,9,4', 100) == [2, 4, 9]

    def test_slice(self):
        assert ipb._parse_cells_spec(slice(2, 5), 100) == [2, 3, 4]

    def test_slice_str(self):
        assert ipb._parse_cells_spec('2:5', 100) == [2, 3, 4]

    def test_slice_and_int(self):
        assert ipb._parse_cells_spec('4,9:12', 100) == [4, 9, 10, 11]
        assert ipb._parse_cells_spec('9:12,4', 100) == [4, 9, 10, 11]
        assert ipb._parse_cells_spec('4,9:12,16', 100) == [4, 9, 10, 11, 16]
        assert ipb._parse_cells_spec('10,9:12', 100) == [9, 10, 11]


class Test_get_code_cells(object):
    def test_single_int(self):
        assert ipb._get_code_cells(5) == [A10[5]]

    def test_single_int_str(self):
        assert ipb._get_code_cells('5') == [A10[5]]

    def test_multi_int_str(self):
        assert ipb._get_code_cells('2,9,4') == [A10[x] for x in [2, 4, 9]]

    def test_slice(self):
        assert ipb._get_code_cells(slice(2, 5)) == [A10[x] for x in [2, 3, 4]]

    def test_slice_str(self):
        assert ipb._get_code_cells('2:5') == [A10[x] for x in [2, 3, 4]]

    def test_slice_and_int(self):
        assert ipb._get_code_cells('1,3:6') == [A10[x] for x in [1, 3, 4, 5]]
        assert ipb._get_code_cells('3:6,1') == [A10[x] for x in [1, 3, 4, 5]]
        assert ipb._get_code_cells('1,3:6,8') == [A10[x] for x in [1, 3, 4, 5, 8]]
        assert ipb._get_code_cells('4,3:6') == [A10[x] for x in [3, 4, 5]]


@pytest.mark.parametrize('fixture',
    [block_grid, image_grid_ll, image_grid_ul])
def test_to_simple_grid(fixture, data_2x2):
    grid = fixture(data_2x2)
    assert grid._to_simple_grid() == data_2x2


@pytest.mark.parametrize('test_grid, ref_grid',
    [(ipb.BlockGrid(2, 2), block_grid),
     (ipb.ImageGrid(2, 2, origin='upper-left'), image_grid_ul),
     (ipb.ImageGrid(2, 2, origin='lower-left'), image_grid_ll)])
def test_load_simple_grid(test_grid, ref_grid, data_2x2):
    ref_grid = ref_grid(data_2x2)
    test_grid._load_simple_grid(data_2x2)
    assert test_grid == ref_grid


@responses.activate
@mock.patch('sys.version_info', ('python', 'version'))
@mock.patch.object(ipb, '__version__', 'ipb_version')
@mock.patch.object(ipb, '_POST_URL', 'http://ipythonblocks.org/post_url')
def test_BlockGrid_post_to_web():
    data = data_2x2()
    grid = block_grid(data)

    expected = {
        'python_version': tuple(sys.version_info),
        'ipb_version': ipb.__version__,
        'ipb_class': 'BlockGrid',
        'code_cells': None,
        'secret': False,
        'grid_data': {
            'lines_on': grid.lines_on,
            'width': grid.width,
            'height': grid.height,
            'blocks': data
        }
    }
    expected = json.dumps(expected)

    responses.add(responses.POST, ipb._POST_URL,
                  body=json.dumps({'url': 'url'}).encode('utf-8'),
                  status=200, content_type='application/json')

    url = grid.post_to_web()

    assert url == 'url'
    assert len(responses.calls) == 1

    req = responses.calls[0].request
    assert req.url == ipb._POST_URL
    assert req.body == expected


@responses.activate
@mock.patch('sys.version_info', ('python', 'version'))
@mock.patch.object(ipb, '__version__', 'ipb_version')
@mock.patch.object(ipb, '_POST_URL', 'http://ipythonblocks.org/post_url')
def test_ImageGrid_ul_post_to_web():
    data = data_2x2()
    grid = image_grid_ul(data)

    expected = {
        'python_version': tuple(sys.version_info),
        'ipb_version': ipb.__version__,
        'ipb_class': 'ImageGrid',
        'code_cells': None,
        'secret': False,
        'grid_data': {
            'lines_on': grid.lines_on,
            'width': grid.width,
            'height': grid.height,
            'blocks': data
        }
    }
    expected = json.dumps(expected)

    responses.add(responses.POST, ipb._POST_URL,
                  body=json.dumps({'url': 'url'}).encode('utf-8'),
                  status=200, content_type='application/json')

    url = grid.post_to_web()

    assert url == 'url'
    assert len(responses.calls) == 1

    req = responses.calls[0].request
    assert req.url == ipb._POST_URL
    assert req.body == expected


@responses.activate
@mock.patch.object(ipb, '_GET_URL_PUBLIC', 'http://ipythonblocks.org/get_url/{0}')
def test_BlockGrid_from_web():
    data = data_2x2()
    grid_id = 'abc'
    get_url = ipb._GET_URL_PUBLIC.format(grid_id)
    resp = {
        'lines_on': True,
        'width': 2,
        'height': 2,
        'blocks': data
    }

    responses.add(responses.GET, get_url,
                  body=json.dumps(resp).encode('utf-8'), status=200,
                  content_type='application/json')

    grid = ipb.BlockGrid.from_web(grid_id)

    assert grid.height == resp['height']
    assert grid.width == resp['width']
    assert grid.lines_on == resp['lines_on']
    assert grid._to_simple_grid() == data

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == get_url


@responses.activate
@mock.patch.object(ipb, '_GET_URL_SECRET', 'http://ipythonblocks.org/get_url/{0}')
def test_ImageGrid_ul_from_web():
    data = data_2x2()
    grid_id = 'abc'
    get_url = ipb._GET_URL_SECRET.format(grid_id)
    resp = {
        'lines_on': True,
        'width': 2,
        'height': 2,
        'blocks': data
    }

    responses.add(responses.GET, get_url,
                  body=json.dumps(resp).encode('utf-8'), status=200,
                  content_type='application/json')

    origin = 'upper-left'
    grid = ipb.ImageGrid.from_web(grid_id, secret=True, origin=origin)

    assert grid.height == resp['height']
    assert grid.width == resp['width']
    assert grid.lines_on == resp['lines_on']
    assert grid._to_simple_grid() == data
    assert grid.origin == origin

    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == get_url

########NEW FILE########
__FILENAME__ = test_misc
"""
Test miscellaneous utility functions in the ipythonblocks module.

"""

from .. import ipythonblocks


def test_flatten():
    # single thing
    for x in ipythonblocks._flatten(1):
        assert x == 1

    # simple list
    thing = range(5)
    for i, x in enumerate(ipythonblocks._flatten(thing)):
        assert x == i

    # nested lists
    thing = [[0], [1, 2], [3], [4, 5, [6]]]
    for i, x in enumerate(ipythonblocks._flatten(thing)):
        assert x == i


########NEW FILE########
__FILENAME__ = test_pixel
import os
import pytest

from .. import ipythonblocks


@pytest.fixture
def basic_pixel():
    return ipythonblocks.Pixel(5, 6, 7, size=20)


def test_xy(basic_pixel):
    """
    Test the .x and .y attributes.

    """
    bp = basic_pixel

    assert bp.x is None
    assert bp.y is None

    bp._row = 1
    bp._col = 2

    assert bp.x == 2
    assert bp.y == 1


def test_td(basic_pixel):
    """
    Test the Pixel._td proerty that returns an HTML table cell.

    """
    bp = basic_pixel

    bp._row = 1
    bp._col = 2

    title = ipythonblocks._TITLE.format(bp._col, bp._row,
                                        bp.red, bp.green, bp.blue)
    rgb = ipythonblocks._RGB.format(bp.red, bp.green, bp.blue)
    td = ipythonblocks._TD.format(title, bp.size, rgb)

    assert bp._td == td


def test_str1(basic_pixel):
    """
    Test the Block.__str__ method used with print.

    """
    bp = basic_pixel

    s = os.linesep.join(['Pixel', 'Color: (5, 6, 7)'])

    assert bp.__str__() == s


def test_str2(basic_pixel):
    """
    Test the Block.__str__ method used with print.

    """
    bp = basic_pixel
    bp._row = 8
    bp._col = 9

    s = os.linesep.join(['Pixel [9, 8]', 'Color: (5, 6, 7)'])

    assert bp.__str__() == s

########NEW FILE########
