__FILENAME__ = blobgrid
import math
import itertools
from utils import pointwise


class BlobGrid(object):

    n_directions = 4
    # directions: left, down, right, up
    directions = range(0, n_directions)
    moves = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    neighbours = [(-1, -1), (-1, 0), (0, 0), (0, -1)]

    def __init__(self, size):
        self.size = size

    def get_value(self, x, y):
        """ overload with method returning pixel values """
        raise NotImplementedError

    def can_move(self, pos, direction):
        # we always keep the blob on the right

        n1 = self.neighbours[direction]
        n2 = self.neighbours[(direction + 1) % self.n_directions]

        value1 = self.get_value(*pointwise('add', pos, n1))
        value2 = self.get_value(*pointwise('add', pos, n2))

        return (value1 == 0 and value2 == 1)

    def find_direction(self, pos, prev_dir=None):
        available_directions = list(self.directions)  # make a copy
        if prev_dir:
            available_directions = (
                n % self.n_directions for n in range(prev_dir, prev_dir + 4))
        for d in available_directions:
            if self.can_move(pos, d):
                return d
        return None

    def move(self, pos, direction):
        offset = self.moves[direction]
        return pointwise('add', pos, offset)

    def corner(self, prev_dir, curr_dir):
        # bezier circle estimate
        kappa = 4 * (math.sqrt(2) - 1) / 3
        final = pointwise('add', self.moves[prev_dir], self.moves[curr_dir])
        control1 = pointwise('mul', kappa, self.moves[prev_dir])
        control2 = pointwise('sub', final,
            pointwise('mul', 1 - kappa, self.moves[curr_dir]))
        replacements = pointwise('div', control1 + control2 + final, 2.0)
        return 'c %s,%s %s,%s %s,%s ' % tuple(replacements)

    def draw(self, prev_dir, curr_dir):
        if prev_dir == curr_dir:
            return 'l %s %s ' % self.moves[curr_dir]
        else:
            return self.corner(prev_dir, curr_dir)

    def start_draw(self, pos, direction):
        start = pointwise('add', pos,
            pointwise('div', self.moves[direction], 2.0))

        return '<path d="M %s %s ' % start

    def draw_blobs(self):
        output = ''

        remaining = []
        for x, y in itertools.product(xrange(self.size + 1), repeat=2):
            remaining.append((x, y))

        # we remove each intersection when visited. some are visited twice
        # when finished with a blob we start at the next unvisited intersection
        while remaining:
            start_pos = remaining.pop(0)
            start_dir = self.find_direction(start_pos)
            if start_dir is None:
                continue

            # use the list of directions for any region to colour
            # singletons and the corner markers
            direction_history = [start_dir]

            output += self.start_draw(start_pos, start_dir)
            curr_pos = self.move(start_pos, start_dir)
            curr_dir = start_dir

            # 'holes' will have opposite turning number -
            # colour these white
            total_turns = 0

            while curr_pos != start_pos:
                if curr_pos in remaining:
                    remaining.remove(curr_pos)
                prev_dir = curr_dir
                curr_dir = self.find_direction(curr_pos, prev_dir)
                output += self.draw(prev_dir, curr_dir)
                turn = (curr_dir - prev_dir) % self.n_directions
                if turn == 1:
                    # left turn
                    total_turns += 1
                elif turn == 3:
                    # right turn
                    total_turns -= 1
                direction_history.append(curr_dir)
                curr_pos = self.move(curr_pos, curr_dir)

            output += self.draw(curr_dir, start_dir)
            if total_turns < 0:  # reverse
                klass = 'class="reverse" '
            else:
                square = [1, 1, 1, 2, 2, 2, 3, 3, 3, 0, 0, 0]
                if (sorted(direction_history) == self.directions or
                    direction_history == square):
                    klass = 'class="colour" '
                else:
                    klass = ''
            output += ' z" %s/>\n' % klass

        return output

########NEW FILE########
__FILENAME__ = logos
import itertools
import Image
from xml.dom import minidom
from xml.parsers.expat import ExpatError


def clear_logo_space(array, size, filename):
    if filename is None:
        return

    # remove any data where logo is
    try:
        logo = Image.open(filename)
        logo_size = logo.size
        logo_array = logo.load()

        if logo_size == (size, size):
            neighbour4 = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)]
            for x, y in itertools.product(xrange(size), repeat=2):
                if logo_array[x, y][3] != 0:
                    for offset in neighbour4:
                        array[x + offset[0], y + offset[1]] = 255
        else:
            print "Raster logo size mismatch, ignoring"
    except IOError, e:
        print "Error opening raster logo: [%s] Ignoring." % e.strerror


def get_svg_logo(filename):
    if filename is None:
        return ''

    try:
        with open(filename) as logo_svg:
            try:
                dom = minidom.parse(logo_svg)
                svg_node = dom.getElementsByTagName('svg')[0]
                ignored_nodes = ['metadata', 'defs', 'sodipodi:namedview']
                logo_xml = "\n".join([n.toxml() for n in svg_node.childNodes
                    if n.nodeName not in ignored_nodes])
                return logo_xml

            except ExpatError, e:
                print "Error parsing logo svg. [%s] Ignoring logo." % e

            except IndexError:
                print ("Error parsing logo svg: No <svg> node found. "
                    "Ignoring logo.")
    except IOError, e:
        print "Error opening logo: [%s] Ignoring." % e.strerror

    return ''

########NEW FILE########
__FILENAME__ = svg
def svg_start(size, colour):
    return '''<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
 "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="%(width)s" height="%(height)s">
    <defs>
        <style type="text/css"><![CDATA[
            .reverse {fill: white}
            .colour {fill: %(colour)s}
        ]]></style>
    </defs>
    <rect x="0" y="0" width="%(width)s" height="%(height)s" class="reverse"/>
''' % {
        'width': size,
        'height': size,
        'colour': colour
    }


def svg_end():
    return '</svg>'

########NEW FILE########
__FILENAME__ = utils
import operator


def pointwise(op, list1, list2):
    # expand singletons
    if not isinstance(list1, (list, tuple)):
        list1 = [list1] * len(list2)
    if not isinstance(list2, (list, tuple)):
        list2 = [list2] * len(list1)

    function = getattr(operator, op)
    result = [function(*pair) for pair in zip(list1, list2)]

    if isinstance(list1, tuple) or isinstance(list2, tuple):
        return tuple(result)
    else:
        return result

########NEW FILE########
__FILENAME__ = prettyqr
import sys
from optparse import OptionParser
from qrencode import encode_scaled, QR_ECLEVEL_H
from prettyqr.blobgrid import BlobGrid
from prettyqr.logos import clear_logo_space, get_svg_logo
from prettyqr.svg import svg_start, svg_end


def main():
    parser = OptionParser(
        usage="usage: %prog [options] text")
    parser.add_option("-o", "--output", dest="output_filename",
        help="write output to FILE", metavar="FLIE", default="output.svg")
    parser.add_option("-l", "--logo", dest="logo_svg",
        help="load logo (partial svg file) from FILE", metavar="FILE")
    parser.add_option("-L", "--logo-raster", dest="logo_png",
        help="load rasterized logo (png) from FILE", metavar="FILE")
    parser.add_option("-c", "--color", dest="colour", default="#a54024",
        help="use COLOR as secondary color")
    parser.add_option("-m", "--min-size", type="int", dest="min_size",
        default="40", help="pad output to minimum size for final QR image")

    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit()

    qr = encode_scaled(args[0], options.min_size, level=QR_ECLEVEL_H)
    image = qr[-1]
    array = image.load()
    # assume squares
    size = image.size[0]

    class BlogGridQR(BlobGrid):
        def get_value(self, x, y):
            if not (0 <= x < size) or not (0 <= y < size):
                return 0
            return 1 - array[x, y] / 255

    clear_logo_space(array, size, options.logo_png)
    blob_grid = BlogGridQR(size)

    output = svg_start(size, options.colour)
    output += blob_grid.draw_blobs()
    output += get_svg_logo(options.logo_svg)
    output += svg_end()

    output_file = open(options.output_filename, 'w')
    output_file.write(output)
    output_file.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tests
import unittest
from prettyqr.blobgrid import BlobGrid
from prettyqr.utils import pointwise

LEFT = 0
DOWN = 1
RIGHT = 2
UP = 3


class TestPointwise(unittest.TestCase):

    def test_add(self):
        self.assertEqual(pointwise('add', [1, 1], [2, 2]), [3, 3])

    def test_tuple(self):
        self.assertEqual(pointwise('add', [1, 1], (2, 2)), (3, 3))

    def test_singleton(self):
        self.assertEqual(pointwise('add', [1, 1], 1), [2, 2])

    def test_empty(self):
        self.assertEqual(pointwise('add', [], []), [])

    def test_missing_operator(self):
        self.assertRaises(AttributeError, pointwise, 'noop', [], [])


class TestBlobGrid(unittest.TestCase):

    def setUp(self):
        test_data = [
            [1, 1, 0],
            [1, 1, 0],
            [0, 0, 1]]

        class BlobGridTest(BlobGrid):
            def get_value(self, x, y):
                size = len(test_data)
                if not (0 <= x < size) or not (0 <= y < size):
                    return 0
                return test_data[y][x]

        self.blob_grid = BlobGridTest(3)
        self.drawing = self.blob_grid.draw_blobs()

    def test_no_subclass(self):
        blob_grid = BlobGrid(0)
        self.assertRaises(NotImplementedError, blob_grid.draw_blobs)

    def test_can_move(self):
        # counter clockwise
        self.assertTrue(self.blob_grid.can_move((0, 0), DOWN))

    def test_cant_move(self):
        # clockwise
        self.assertFalse(self.blob_grid.can_move((0, 0), RIGHT))

        # outside
        self.assertFalse(self.blob_grid.can_move((0, 0), UP))
        self.assertFalse(self.blob_grid.can_move((0, 0), LEFT))

    def test_find_direction1(self):
        self.assertEquals(self.blob_grid.find_direction((0, 0)), DOWN)

    def test_find_direction2(self):
        self.assertEquals(
            self.blob_grid.find_direction((2, 2)), DOWN)

    def test_find_direction3(self):
        self.assertEquals(
            self.blob_grid.find_direction((2, 2), LEFT), DOWN)

    def test_find_direction4(self):
        self.assertEquals(
            self.blob_grid.find_direction((2, 2), RIGHT), UP)

    def test_move(self):
        self.assertEqual(
            self.blob_grid.move((0, 0), RIGHT), (1, 0))

    def test_draw(self):
        self.assertEqual(self.blob_grid.draw(LEFT, DOWN),
            'c -0.276142374915,0.0 -0.5,0.276142374915 -0.5,0.5 ')

    def test_draw_blobs_lines(self):
        self.assertEquals(
            self.drawing.count('\n'), 2)

    def test_draw_blobs_corners(self):
        self.assertEqual(
            self.drawing.count('c '), 8)

    def test_draw_blobs_lines(self):
        self.assertEqual(
            self.drawing.count('l '), 4)

    def test_draw_blobs_colour_singles(self):
        self.assertEqual(
            self.drawing.count('colour'), 1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
