__FILENAME__ = brewer2mpl
from __future__ import print_function

import os.path
import json
import webbrowser

try:
    from matplotlib.colors import LinearSegmentedColormap
except ImportError:     # pragma: no cover
    HAVE_MPL = False
else:
    HAVE_MPL = True


__all__ = ('COLOR_MAPS', 'print_maps', 'print_all_maps', 'print_maps_by_type',
           'get_map', 'MAP_TYPES', 'BrewerMap')

_DATADIR = os.path.join(os.path.dirname(__file__), 'data')
_DATAFILE = os.path.join(_DATADIR, 'colorbrewer_all_schemes.json')

with open(_DATAFILE, 'r') as f:
    COLOR_MAPS = json.load(f)

MAP_TYPES = ('Sequential', 'Diverging', 'Qualitative')


def print_maps(map_type=None, number=None):
    """
    Print maps by type and/or number of defined colors.

    Parameters
    ----------
    map_type : {'Sequential', 'Diverging', 'Qualitative'}, optional
        Filter output by map type. By default all maps are printed.
    number : int, optional
        Filter output by number of defined colors. By default there is
        no numeric filtering.

    """
    if not map_type and not number:
        print_all_maps()

    elif map_type:
        print_maps_by_type(map_type, number)

    else:
        s = ('Invalid parameter combination. '
             'number without map_type is not supported.')
        raise ValueError(s)


def print_all_maps():
    """
    Print the name and number of defined colors of all available color maps.

    """
    for t in MAP_TYPES:
        print_maps_by_type(t)


def print_maps_by_type(map_type, number=None):
    """
    Print all available maps of a given type.

    Parameters
    ----------
    map_type : {'Sequential', 'Diverging', 'Qualitative'}
        Select map type to print.
    number : int, optional
        Filter output by number of defined colors. By default there is
        no numeric filtering.

    """
    map_type = map_type.lower().capitalize()
    if map_type not in MAP_TYPES:
        s = 'Invalid map type, must be one of {0}'.format(MAP_TYPES)
        raise ValueError(s)

    print(map_type)

    map_keys = sorted(COLOR_MAPS[map_type].keys())

    format_str = '{0:8}  :  {1}'

    for mk in map_keys:
        num_keys = sorted(COLOR_MAPS[map_type][mk].keys(), key=int)

        if not number or str(number) in num_keys:
            num_str = '{' + ', '.join(num_keys) + '}'
            print(format_str.format(mk, num_str))


class _ColorMap(object):
    """
    Representation of a color map with matplotlib compatible
    views of the map.

    Parameters
    ----------
    name : str
    map_type : str
    colors : list
        Colors as list of 0-255 RGB triplets.

    Attributes
    ----------
    name : str
    map_type : str
    number : int
        Number of colors in color map.
    colors : list
        Colors as list of 0-255 RGB triplets.
    hex_colors : list
    mpl_colors : list
    mpl_colormap : matplotlib LinearSegmentedColormap

    """
    def __init__(self, name, map_type, colors):
        self.name = name
        self.type = map_type
        self.number = len(colors)
        self.colors = colors

    @property
    def hex_colors(self):
        """
        Colors as a tuple of hex strings. (e.g. '#A912F4')

        """
        hc = []

        for color in self.colors:
            h = '#' + ''.join('{0:>02}'.format(hex(c)[2:].upper())
                              for c in color)
            hc.append(h)

        return hc

    @property
    def mpl_colors(self):
        """
        Colors expressed on the range 0-1 as used by matplotlib.

        """
        mc = []

        for color in self.colors:
            mc.append(tuple([x / 255. for x in color]))

        return mc

    @property
    def mpl_colormap(self):
        """
        A basic matplotlib color map. If you want to specify keyword arguments
        use the `get_mpl_colormap` method.

        """
        return self.get_mpl_colormap()

    def get_mpl_colormap(self, **kwargs):
        """
        A color map that can be used in matplotlib plots. Requires matplotlib
        to be importable. Keyword arguments are passed to
        `matplotlib.colors.LinearSegmentedColormap.from_list`.

        """
        if not HAVE_MPL:    # pragma: no cover
            raise RuntimeError('matplotlib not available.')

        cmap = LinearSegmentedColormap.from_list(self.name,
                                                 self.mpl_colors, **kwargs)

        return cmap

    def show_as_blocks(self, block_size=100):
        """
        Show colors in the IPython Notebook using ipythonblocks.

        Parameters
        ----------
        block_size : int, optional
            Size of displayed blocks.

        """
        from ipythonblocks import BlockGrid

        grid = BlockGrid(self.number, 1, block_size=block_size)

        for block, color in zip(grid, self.colors):
            block.rgb = color

        grid.show()


class BrewerMap(_ColorMap):
    """
    Representation of a colorbrewer2 color map with matplotlib compatible
    views of the map.

    Parameters
    ----------
    name : str
    map_type : str
    colors : list
        Colors as list of 0-255 RGB triplets.

    Attributes
    ----------
    name : str
    map_type : str
    number : int
        Number of colors in color map.
    colors : list
        Colors as list of 0-255 RGB triplets.
    colorbrewer2_url : str
    hex_colors : list
    mpl_colors : list
    mpl_colormap : matplotlib LinearSegmentedColormap

    """
    @property
    def colorbrewer2_url(self):
        """
        URL that can be used to view the color map at colorbrewer2.org.

        """
        url = 'http://colorbrewer2.org/index.html?type={0}&scheme={1}&n={2}'
        return url.format(self.type.lower(), self.name, self.number)

    def colorbrewer2(self):
        """
        View this color map at colorbrewer2.org. This will open
        colorbrewer2.org in your default web browser.

        """
        webbrowser.open_new_tab(self.colorbrewer2_url)  # pragma: no cover


def get_map(name, map_type, number, reverse=False):
    """
    Return a `BrewerMap` representation of the specified color map.

    Parameters
    ----------
    name : str
        Name of color map. Use `print_maps` to see available color maps.
    map_type : {'Sequential', 'Diverging', 'Qualitative'}
        Select color map type.
    number : int
        Number of defined colors in color map.
    reverse : bool, optional
        Set to True to get the reversed color map.

    """
    number = str(number)
    map_type = map_type.lower().capitalize()

    # check for valid type
    if map_type not in MAP_TYPES:
        s = 'Invalid map type, must be one of {0}'.format(MAP_TYPES)
        raise ValueError(s)

    # make a dict of lower case map name to map name so this can be
    # insensitive to case.
    # this would be a perfect spot for a dict comprehension but going to
    # wait on that to preserve 2.6 compatibility.
    # map_names = {k.lower(): k for k in COLOR_MAPS[map_type].iterkeys()}
    map_names = dict((k.lower(), k) for k in COLOR_MAPS[map_type].keys())

    # check for valid name
    if name.lower() not in map_names:
        s = 'Invalid color map name {0!r} for type {1!r}.\n'
        s = s.format(name, map_type)
        valid_names = [str(k) for k in COLOR_MAPS[map_type].keys()]
        valid_names.sort()
        s += 'Valid names are: {0}'.format(valid_names)
        raise ValueError(s)

    name = map_names[name.lower()]

    # check for valid number
    if number not in COLOR_MAPS[map_type][name]:
        s = 'Invalid number for map type {0!r} and name {1!r}.\n'
        s = s.format(map_type, str(name))
        valid_numbers = [int(k) for k in COLOR_MAPS[map_type][name].keys()]
        valid_numbers.sort()
        s += 'Valid numbers are : {0}'.format(valid_numbers)
        raise ValueError(s)

    colors = COLOR_MAPS[map_type][name][number]['Colors']

    if reverse:
        name += '_r'
        colors = [x for x in reversed(colors)]

    return BrewerMap(name, map_type, colors)


def _load_maps_by_type(map_type):
    """
    Load all maps of a given type into a dictionary.

    Color maps are loaded as BrewerMap objects. Dictionary is
    keyed by map name and then integer numbers of defined
    colors. There is an additional 'max' key that points to the
    color map with the largest number of defined colors.

    Parameters
    ----------
    map_type : {'Sequential', 'Diverging', 'Qualitative'}

    Returns
    -------
    maps : dict of BrewerMap

    """
    seq_maps = COLOR_MAPS[map_type]

    loaded_maps = {}

    for map_name in seq_maps:
        loaded_maps[map_name] = {}

        for num in seq_maps[map_name]:
            inum = int(num)
            colors = seq_maps[map_name][num]['Colors']

            bmap = BrewerMap(map_name, map_type, colors)

            loaded_maps[map_name][inum] = bmap

        max_num = int(max(seq_maps[map_name].keys(), key=int))
        loaded_maps[map_name]['max'] = loaded_maps[map_name][max_num]

    return loaded_maps

########NEW FILE########
__FILENAME__ = colorbrewer_schemes_csv_to_json
"""
Color maps come from colorbrewer2.org as an Excel file. I've converted the
Excel file to CSV and here I convert it to JSON for easy reading into Python.

"""

import sys
from csv import DictReader
from collections import OrderedDict
import json


def new_sub_map(row, sm_dict):
    num_colors = int(row['NumOfColors'])
    sm_dict[num_colors] = OrderedDict()
    sub_map = sm_dict[num_colors]

    sub_map['NumOfColors'] = num_colors
    sub_map['Type'] = row['Type']
    sub_map['Colors'] = [(int(row['R']), int(row['G']), int(row['B']))]

    return sub_map


def read_csv_to_dict():
    color_maps = OrderedDict()

    for scheme_type in ('Sequential', 'Diverging', 'Qualitative'):
        color_maps[scheme_type] = OrderedDict()

    with open('colorbrewer_all_schemes.csv', 'r') as csvf:
        csv = DictReader(csvf)

        for row in csv:
            if row['SchemeType']:
                # first row of a new color map block
                color_maps[row['SchemeType']][row['ColorName']] = OrderedDict()
                current_map = color_maps[row['SchemeType']][row['ColorName']]

                current_submap = new_sub_map(row, current_map)

            elif row['ColorName']:
                # first row of a new sub-map block
                current_submap = new_sub_map(row, current_map)

            elif not row['ColorName']:
                # continuation of a sub-map block
                current_submap['Colors'].append((int(row['R']),
                                                 int(row['G']),
                                                 int(row['B'])))

    return color_maps


def save_to_json(color_maps):
    with open('colorbrewer_all_schemes.json', 'w') as f:
        json.dump(color_maps, f, indent=1)


def main():
    color_maps = read_csv_to_dict()
    save_to_json(color_maps)


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = diverging
from .brewer2mpl import _load_maps_by_type

globals().update(_load_maps_by_type('Diverging'))

########NEW FILE########
__FILENAME__ = qualitative
from .brewer2mpl import _load_maps_by_type

globals().update(_load_maps_by_type('Qualitative'))

########NEW FILE########
__FILENAME__ = sequential
from .brewer2mpl import _load_maps_by_type

globals().update(_load_maps_by_type('Sequential'))

########NEW FILE########
__FILENAME__ = test_brewer2mpl
"""
Miscellaneous tests of brewer2mpl functionality.

"""
try:
    import pytest
except ImportError:
    raise ImportError('Tests require pytest >= 2.2.')

from .. import brewer2mpl

@pytest.mark.parametrize('map_type', ['Sequential', 'Diverging', 'Qualitative'])
def test_load_maps_by_type(map_type):
    maps = brewer2mpl._load_maps_by_type(map_type)

    assert len(maps) == len(brewer2mpl.COLOR_MAPS[map_type])
    assert sorted(maps.keys()) == sorted(brewer2mpl.COLOR_MAPS[map_type].keys())

########NEW FILE########
__FILENAME__ = test_brewermap
"""
Test the BrewerMap class.

"""

try:
    import pytest
except ImportError:
    raise ImportError('Tests require pytest >= 2.2.')

# figure out which URL lib to import
import sys
if sys.version_info[0] == 2:
    import urllib2 as urllib
else:
    import urllib.request as urllib

try:
    from matplotlib.colors import LinearSegmentedColormap
except ImportError:
    HAVE_MPL = False
else:
    HAVE_MPL = True

import mock
from ipythonblocks import BlockGrid

from .. import brewer2mpl


class TestBrewerMap(object):
    @classmethod
    def setup_class(cls):
        name = 'TestMap'
        map_type = 'TestType'
        colors = [(0, 0, 0), (12, 134, 245), (255, 255, 255)]

        cls.bmap = brewer2mpl.BrewerMap(name, map_type, colors)

        cls.name = name
        cls.map_type = map_type
        cls.colors = colors

    def test_init(self):
        assert self.bmap.name == self.name
        assert self.bmap.type == self.map_type
        assert self.bmap.colors == self.colors
        assert self.bmap.number == len(self.colors)

    def test_colorbrewer2_url(self):
        url = 'http://colorbrewer2.org/index.html?type=testtype&scheme=TestMap&n=3'
        assert self.bmap.colorbrewer2_url == url

    def test_colorbrewer2_url_exists(self):
        '''Simple check to ensure a URL is valid. Thanks to
        http://stackoverflow.com/questions/4041443'''
        try:
            urllib.urlopen(self.bmap.colorbrewer2_url)
            assert True
        except:
            assert False

    def test_hex_colors(self):
        hex_colors = ['#000000', '#0C86F5', '#FFFFFF']
        assert self.bmap.hex_colors == hex_colors

    def test_mpl_colors(self):
        mpl_colors = [(0, 0, 0), (12/255., 134/255., 245/255.), (1, 1, 1)]
        assert self.bmap.mpl_colors == mpl_colors

    @pytest.mark.skipif('not HAVE_MPL')
    def test_mpl_colormap(self):
        mpl_colormap = self.bmap.mpl_colormap
        assert isinstance(mpl_colormap, LinearSegmentedColormap)

    @mock.patch.object(BlockGrid, 'show')
    def test_show_as_blocks(self, mock_show):
        self.bmap.show_as_blocks()
        mock_show.assert_called_with()

########NEW FILE########
__FILENAME__ = test_get_map
"""
Test the get_map function.

"""
try:
    import pytest
except ImportError:
    raise ImportError('Tests require pytest >= 2.2.')

from .. import brewer2mpl


def reverse(sequence):
    return [x for x in reversed(sequence)]


def test_get_map_reverse():
    bmap = brewer2mpl.get_map('Greens', 'Sequential', 8)
    bmap_r = brewer2mpl.get_map('Greens', 'Sequential', 8, reverse=True)

    assert bmap.type == bmap_r.type
    assert bmap.name + '_r' == bmap_r.name
    assert bmap.number == bmap_r.number
    assert bmap.colors == reverse(bmap_r.colors)


def test_get_map_raises_bad_type():
    with pytest.raises(ValueError):
        brewer2mpl.get_map('Greens', 'FakeType', 8)


def test_get_map_raises_bad_name():
    with pytest.raises(ValueError):
        brewer2mpl.get_map('FakeName', 'Sequential', 8)


def test_get_map_raises_bad_number():
    with pytest.raises(ValueError):
        brewer2mpl.get_map('Greens', 'Sequential', 99)


class TestCaseSensitivity(object):
    def test_type1(self):
        bmap = brewer2mpl.get_map('Greens', 'SEQUENTIAL', 8)
        assert bmap.name == 'Greens'
        assert bmap.type == 'Sequential'
        assert bmap.number == 8

    def test_type2(self):
        bmap = brewer2mpl.get_map('Greens', 'sequential', 8)
        assert bmap.name == 'Greens'
        assert bmap.type == 'Sequential'
        assert bmap.number == 8

    def test_type3(self):
        bmap = brewer2mpl.get_map('Greens', 'SeQuEnTiAl', 8)
        assert bmap.name == 'Greens'
        assert bmap.type == 'Sequential'
        assert bmap.number == 8

    def test_name1(self):
        bmap = brewer2mpl.get_map('GREENS', 'Sequential', 8)
        assert bmap.name == 'Greens'
        assert bmap.type == 'Sequential'
        assert bmap.number == 8

    def test_name2(self):
        bmap = brewer2mpl.get_map('greens', 'Sequential', 8)
        assert bmap.name == 'Greens'
        assert bmap.type == 'Sequential'
        assert bmap.number == 8

    def test_name3(self):
        bmap = brewer2mpl.get_map('GrEeNs', 'Sequential', 8)
        assert bmap.name == 'Greens'
        assert bmap.type == 'Sequential'
        assert bmap.number == 8

    def test_name4(self):
        bmap = brewer2mpl.get_map('piyg', 'Diverging', 8)
        assert bmap.name == 'PiYG'
        assert bmap.type == 'Diverging'
        assert bmap.number == 8

########NEW FILE########
__FILENAME__ = test_print_functions
"""
Test the brewer2mpl print functions. The output is not actually tested,
but the functions are fully exercised to catch errors.

"""

try:
    import pytest
except ImportError:
    raise ImportError('Tests require pytest >= 2.2.')

from .. import brewer2mpl


def test_print_maps1(capsys):
    # just make sure there are no errors
    brewer2mpl.print_maps()
    out, err = capsys.readouterr()
    assert out


def test_print_maps2(capsys):
    # just make sure there are no errors
    brewer2mpl.print_maps('sequential')
    out, err = capsys.readouterr()
    assert out


def test_print_maps3(capsys):
    # just make sure there are no errors
    brewer2mpl.print_maps('sequential', 6)
    out, err = capsys.readouterr()
    assert out


def test_print_maps_raises():
    with pytest.raises(ValueError):
        brewer2mpl.print_maps(number=6)


def test_print_all_maps(capsys):
    # just make sure there are no errors
    brewer2mpl.print_all_maps()
    out, err = capsys.readouterr()
    assert out


def test_print_maps_by_type1(capsys):
    # just make sure there are no errors
    brewer2mpl.print_maps_by_type('qualitative')
    out, err = capsys.readouterr()
    assert out


def test_print_maps_by_type2(capsys):
    # just make sure there are no errors
    brewer2mpl.print_maps_by_type('qualitative', number=6)
    out, err = capsys.readouterr()
    assert out


def test_print_maps_by_type_raises():
    with pytest.raises(ValueError):
        brewer2mpl.print_maps_by_type('notarealtype')

########NEW FILE########
__FILENAME__ = test_wesanderson
from ... import wesanderson as wap


def test_print_maps(capsys):
    wap.print_maps()
    out, err = capsys.readouterr()
    lines = out.split('\n')
    assert lines[0] == 'Cavalcanti        Qualitative     5'


def test_get_map():
    palette = wap.get_map('cavalcanTi')
    assert isinstance(palette, wap._WesAndersonMap)
    assert palette.name == 'Cavalcanti'
    assert len(palette.colors) == 5
    assert palette.wap_url == \
        ('http://wesandersonpalettes.tumblr.com/post/'
         '79348553036/castello-cavalcanti-how-can-i-help')


def test_get_map_reversed():
    palette = wap.get_map('cavalcanTi', reverse=True)
    assert isinstance(palette, wap._WesAndersonMap)
    assert palette.name == 'Cavalcanti_r'
    assert len(palette.colors) == 5
    assert palette.wap_url == \
        ('http://wesandersonpalettes.tumblr.com/post/'
         '79348553036/castello-cavalcanti-how-can-i-help')


def test_palettes_loaded():
    assert isinstance(wap.Cavalcanti, wap._WesAndersonMap)

########NEW FILE########
__FILENAME__ = wesanderson
from __future__ import print_function
"""
Color palettes derived from http://wesandersonpalettes.tumblr.com/.

"""

import webbrowser

from ..brewer2mpl import _ColorMap


_tumblr_template = 'http://wesandersonpalettes.tumblr.com/post/{0}'

# Tumblr palettes in chronological order
_palettes = {
    'Chevalier': {
        'colors': [
            (53, 82, 67), (254, 202, 73), (201, 213, 213), (187, 162, 137)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format('79263620764/hotel-chevalier')
    },
    'Moonrise1': {
        'colors': [
            (114, 202, 221), (240, 165, 176), (140, 133, 54), (195, 180, 119),
            (250, 208, 99)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '79263667140/sam-i-love-you-but-you-dont-know-what-youre')
    },
    'Mendl': {
        'colors': [
            (222, 141, 185), (184, 192, 246), (207, 147, 135), (92, 128, 204)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format('79348206200/mendls-heaven')
    },
    'Margot1': {
        'colors': [
            (137, 119, 18), (243, 194, 164), (246, 159, 151), (254, 214, 140),
            (98, 144, 117)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format('79348364517/margot-takes-a-bath')
    },
    'Cavalcanti': {
        'colors': [
            (209, 170, 0), (8, 50, 19), (146, 148, 96), (111, 152, 121),
            (132, 33, 17)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '79348553036/castello-cavalcanti-how-can-i-help')
    },
    'Moonrise2': {
        'colors': [
            (102, 124, 116), (181, 106, 39), (194, 186, 124), (31, 25, 23)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '79641731527/sam-why-do-you-always-use-binoculars-suzy-it')
    },
    'Margot2': {
        'colors': [
            (118, 139, 147), (188, 36, 15), (249, 236, 197), (212, 115, 41)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format('79641785036/margot-takes-a-break')
    },
    'Moonrise3': {
        'colors': [
            (242, 218, 82), (197, 157, 0), (203, 203, 201), (27, 30, 20)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '79783357790/suzy-ive-always-wanted-to-be-an-orphan-most-of')
    },
    'GrandBudapest1': {
        'colors': [
            (238, 174, 101), (251, 79, 85), (72, 19, 19), (204, 95, 39)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format('79784389334/the-grand-budapest-hotel')
    },
    'Moonrise4': {
        'colors': [
            (123, 135, 97), (193, 166, 46), (79, 143, 107), (59, 69, 60),
            (159, 50, 8)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format('79956897654/coming-soon')
    },
    'Zissou': {
        'colors': [
            (0, 153, 230), (18, 37, 90), (242, 56, 20), (223, 183, 139),
            (182, 195, 197)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '79956949771/steve-zissou-dont-point-that-gun-at-him-hes-an')
    },
    'Royal1': {
        'colors': [
            (121, 164, 58), (242, 214, 175), (94, 72, 41), (24, 20, 1)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '79957796915/royal-o-reilly-tenenbaum-1932-2001')
    },
    'Darjeeling1': {
        'colors': [
            (158, 151, 151), (194, 142, 0), (131, 102, 89), (156, 90, 51)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '80149649946/jack-i-wonder-if-the-three-of-us-wouldve-been')
    },
    'FantasticFox1': {
        'colors': [
            (249, 219, 32), (147, 75, 78), (66, 23, 13), (194, 121, 34),
            (226, 200, 167)
        ],
        'type': 'Qualitative',
        'url': _tumblr_template.format(
            '80149872170/mrs-fox-you-know-you-really-are-fantastic-mr')
    }
}

_map_names = {}
for k in _palettes:
    _map_names[k.lower()] = k


class WesAndersonMap(_ColorMap):
    """
    Representation of a color map with matplotlib compatible
    views of the map.

    Parameters
    ----------
    name : str
    map_type : str
    colors : list
        Colors as list of 0-255 RGB triplets.
    url : str
        URL on the web where this color map can be viewed.

    Attributes
    ----------
    name : str
    map_type : str
    number : int
        Number of colors in color map.
    colors : list
        Colors as list of 0-255 RGB triplets.
    hex_colors : list
    mpl_colors : list
    mpl_colormap : matplotlib LinearSegmentedColormap
    wap_url : str
        URL on the web where this color map can be viewed.

    """
    def __init__(self, name, map_type, colors, url):
        super(WesAndersonMap, self).__init__(name, map_type, colors)
        self.wap_url = url

    def wap(self):
        """
        View this color palette on the web.
        Will open a new tab in your web browser.

        """
        webbrowser.open_new_tab(self.wap_url)  # pragma: no cover


def print_maps():
    """
    Print a list of Wes Anderson palettes.

    """
    namelen = max(len(k) for k in _palettes)
    fmt = '{0:' + str(namelen + 4) + '}{1:16}{2:}'

    for k in sorted(_palettes.keys()):
        print(fmt.format(k, _palettes[k]['type'], len(_palettes[k]['colors'])))


def get_map(name, reverse=False):
    """
    Get a Wes Anderson palette by name.

    Parameters
    ----------
    name : str
        Name of map. Use brewer2mpl.wap.print_maps to see available names.
    reverse : bool, optional
        If True reverse colors from their default order.

    Returns
    -------
    palette : WesAndersonMap

    """
    name = _map_names[name.lower()]
    palette = _palettes[name]

    if reverse:
        name += '_r'
        palette['colors'] = list(reversed(palette['colors']))

    return WesAndersonMap(
        name, palette['type'], palette['colors'], palette['url'])

########NEW FILE########
__FILENAME__ = make_demo_figures
"""
Make color map figures for the web page.

Three figures are made, one each for the sequential, diverging, and qualitative
color maps. For each named color map the one with the most defined colors
is shown.

"""

import math

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.colorbar import ColorbarBase
from mpl_toolkits.axes_grid1 import ImageGrid

import brewer2mpl


# for each named color map, get the one with the most colors
def filter_maps():
    all_maps = brewer2mpl.COLOR_MAPS

    max_maps = {}

    for map_type in all_maps:
        max_maps[map_type] = {}

        for map_name in all_maps[map_type]:
            max_num = max(all_maps[map_type][map_name].iterkeys(), key=int)
            max_maps[map_type][map_name] = \
                brewer2mpl.get_map(map_name, map_type, int(max_num))

    return max_maps


# show the color maps on axes ala
# http://matplotlib.sourceforge.net/examples/api/colorbar_only.html
def make_figure(map_type, bmaps):
    fig = plt.figure(figsize=(8, 2 * len(bmaps)))
    fig.suptitle(map_type,
                 x=0.5, y=0.98,                     # top middle
                 verticalalignment='top',
                 horizontalalignment='center',
                 fontsize=20)

    grid = ImageGrid(fig, (0.15, 0.01, 0.82, 0.94),
                     nrows_ncols=(2 * len(bmaps), 1),
                     aspect=False, axes_pad=0.1)

    map_names = sorted(bmaps.keys())

    for i, ax in enumerate(grid):
        map_name = map_names[int(math.floor(i / 2.))]
        ax.set_axis_off()

        if i % 2 == 0:
            # make the smooth, interpolated color map
            ColorbarBase(ax, cmap=bmaps[map_name].mpl_colormap,
                         orientation='horizontal')
            ax.set_title(map_name,
                         position=(-0.01,0.5),          # on the left side
                         size=15,
                         verticalalignment='center',
                         horizontalalignment='right')
        else:
            # make a bounded color map showing only the defined colors
            ncolors = bmaps[map_name].number
            norm = BoundaryNorm(range(ncolors + 1), ncolors=ncolors)
            cmap = ListedColormap(bmaps[map_name].mpl_colors)
            ColorbarBase(ax, cmap=cmap, norm=norm, orientation='horizontal')

    fig.savefig(map_type + '.png')


def main():
    bmaps = filter_maps()

    for map_type in brewer2mpl.MAP_TYPES:
        make_figure(map_type, bmaps[map_type])


if __name__ == '__main__':
    main()

########NEW FILE########
