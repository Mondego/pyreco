__FILENAME__ = cartogram

"""
computes a circle cartogram for a given svg map + data file
"""
import sys

class Cartogram:

    def generate(self, svg_src, attr, csv_src, key, value):
        regions = self.load_regions_from_svg(svg_src, attr)
        data = self.load_csv(csv_src, key, value)
        circles = []
        for id in regions:
            cx, cy = regions[id]
            val = data[id]
            circles.append(Circle(cx, cy, id, val))

        self.attr = attr
        self.key = value
        self.circles = circles
        self.compute_radii()
        self.layout(700)
        self.rescale()
        self.correct()
        self.layout(200, True)
        self.rescale()
        self.correct()
        self.layout(100, False)
        self.rescale()
        self.correct()
        self.to_svg()

    def load_regions_from_svg(self, url, attr):
        import svg as svgdoc
        svg = svgdoc.Document.load(url)
        self.svg = svg
        g = svg.doc.getElementsByTagName('g')[0]
        coords = {}
        for path in g.getElementsByTagName('path'):
            path_str = path.getAttribte('d')
            id = path.getAttribte('data-' + attr)
            poly = restore_poly_from_path_str(path_str)
            coords[id] = poly.center()
        return coords

    def load_csv(self, url, key='id', value='val'):
        import csv
        doc = csv.reader(open(url), dialect='excel-tab')
        head = None
        data = {}
        for row in doc:
            if not head:
                head = row
                sys.stderr.write(head)
            else:
                id = row[head.index(key)].strip()
                val = float(row[head.index(value)])
                data[id] = val
        return data

    def compute_radii(self):
        import sys, math
        minv = 0
        maxv = sys.maxint * -1
        for c in self.circles:
            minv = min(minv, c.value)
            maxv = max(maxv, c.value)

        for c in self.circles:
            c.r = math.pow((c.value - minv) / (maxv - minv), 0.50) * 60
            c.weight = c.value / maxv

    def layout(self, steps=100, correct=False):
        for i in range(steps):
            #if i % 100 == 0:
            #    self.toSVG()
            self.layout_step(correct)

    def layout_step(self, correct=False):
        import math
        pad = 0

        if correct:
            for C in self.circles:
                v = Vector(C.ox - C.x, C.oy - C.y)
                v.normalize()
                v.resize(0.5)
                C._move(v.x, v.y)

        for A in self.circles:
            for B in self.circles:
                if A != B:
                    radsq = (A.r + B.r) * (A.r + B.r)
                    d = A.sqdist(B)
                    if radsq + pad > d:
                        # move circles away from each other
                        v = Vector(B.x - A.x, B.y - A.y)
                        v.normalize()
                        m = (math.sqrt(radsq) - math.sqrt(d)) * 0.25
                        v.resize(m)
                        A._move(v.x * -1 * B.weight, v.y * -1 * B.weight)
                        B._move(v.x * A.weight, v.y * A.weight)

        for C in self.circles:
            C.move()

    def rescale(self):
        from geometry import BBox, View
        svg = self.svg
        svg_view = svg[1][0][0]
        vh = float(svg_view['h'])
        vw = float(svg_view['w'])

        bbox = BBox()
        for c in self.circles:
            r = c.r
            bbox.update((c.x + r, c.y + r))
            bbox.update((c.x + r, c.y - r))
            bbox.update((c.x - r, c.y + r))
            bbox.update((c.x - r, c.y - r))

        view = View(bbox, vw, vh)
        for c in self.circles:
            c.r *= view.scale
            x, y = view.project((c.x, c.y))
            c.x = x
            c.y = y

    def correct(self):
        for A in self.circles:
            intersects = False
            for B in self.circles:
                if A != B:
                    radsq = (A.r + B.r) * (A.r + B.r)
                    d = A.sqdist_o(B)
                    if radsq > d:
                        intersects = True
                        break
            if not intersects:
                A.x = A.ox
                A.y = A.oy

    def to_svg(self):
        svg = self.svg

        g = svg.node('g', svg.root, id="cartogram", fill="red", fill_opacity="0.5")

        for circle in self.circles:
            c = svg.node('circle', g, cx=circle.x, cy=circle.y, r=circle.r)
            c.setAttribute('data-' + self.attr, circle.id)
            c.setAttribute('data-' + self.key.lower(), circle.value)
            g.append(c)

        svg.preview()
        #svg.save('cartogram.svg')


class Circle:

    def __init__(self, x, y, id, value):
        self.x = self.ox = float(x)
        self.y = self.oy = float(y)
        self.id = id
        self.value = float(value)
        self.dx = 0
        self.dy = 0

    def _move(self, x, y):
        self.dx += x
        self.dy += y

    def move(self):
        self.x += self.dx
        self.y += self.dy
        self.dx = 0
        self.dy = 0

    def __repr__(self):
        return '<Circle x=%.1f, y=%.1f, id=%s, val=%f >' % (self.x, self.y, self.id, self.value)

    def sqdist(self, circ):
        dx = self.x - circ.x
        dy = self.y - circ.y
        return dx * dx + dy * dy

    def sqdist_o(self, circ):
        dx = self.ox - circ.x
        dy = self.oy - circ.y
        return dx * dx + dy * dy


"""
been too lazy to code this myself, instead I took code from here
http://www.kokkugia.com/wiki/index.php5?title=Python_vector_class
"""


class Vector:
    # Class properties
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    # represent as a string
    def __repr__(self):
        return 'Vector(%s, %s)' % (self.x, self.y)

    '''
       Class Methods / Behaviours
    '''

    def zero(self):
        self.x = 0.0
        self.y = 0.0
        return self

    def clone(self):
        return Vector(self.x, self.y)

    def normalize(self):
        from math import sqrt
        if self.x == 0 and self.y == 0:
            return self
        norm = float(1.0 / sqrt(self.x * self.x + self.y * self.y))
        self.x *= norm
        self.y *= norm
        # self.z *= norm
        return self

    def invert(self):
        self.x = -(self.x)
        self.y = -(self.y)
        return self

    def resize(self, sizeFactor):
        self.normalize
        self.scale(sizeFactor)
        return self

    def minus(self, t):
        self.x -= t.x
        self.y -= t.y
        # self.z -= t.z
        return self

    def plus(self, t):
        self.x += t.x
        self.y += t.y
        # self.z += t.z
        return self

    def roundToInt(self):
        self.x = int(self.x)
        self.y = int(self.y)
        return self

    # Returns the squared length of this vector.
    def lengthSquared(self):
        return float((self.x * self.x) + (self.y * self.y))

    # Returns the length of this vector.
    def length(self):
        from math import sqrt
        return float(sqrt(self.x * self.x + self.y * self.y))

    # Computes the dot product of this vector and vector v2
    def dot(self, v2):
        return (self.x * v2.x + self.y * v2.y)

    # Linearly interpolates between vectors v1 and v2 and returns the result point = (1-alpha)*v1 + alpha*v2.
    def interpolate(self, v2, alpha):
        self.x = float((1 - alpha) * self.x + alpha * v2.x)
        self.y = float((1 - alpha) * self.y + alpha * v2.y)
        return Vector(self.x, self.y)

    # Returns the angle in radians between this vector and the vector parameter;
    # the return value is constrained to the range [0,PI].
    def angle(self, v2):
        from math import acos
        vDot = self.dot(v2) / (self.length() * v2.length())
        if vDot < -1.0:
            vDot = -1.0
        if vDot > 1.0:
            vDot = 1.0
        return float(acos(vDot))

    # Limits this vector to a given size.
    # NODEBOX USERS: name should change as 'size' and 'scale' are reserved words in Nodebox!
    def limit(self, size):
        if (self.length() > size):
            self.normalize()
            self.scale(size)

    # Point Methods
    # Returns the square of the distance between this tuple and tuple t1.
    def distanceSquared(self, t1):
        dx = self.x - t1.x
        dy = self.y - t1.y
        return (dx * dx + dy * dy)

    # NODEBOX USERS: name should change as 'scale' is reserved word in Nodebox!
    def scale(self, s):
        self.x *= s
        self.y *= s
        return self

    # NODEBOX USERS: name should change as 'translate' is reserved word in Nodebox!
    def translate(self, vec):
        self.plus(vec)

    def distance(self, pt):
        from math import sqrt
        dx = self.x - pt.x
        dy = self.y - pt.y
        return float(sqrt(dx * dx + dy * dy))


def restore_poly_from_path_str(path_str):
    """
    restores a list of polygons from a SVG path string
    """
    contours = path_str.split('Z')  # last contour may be empty
    from Polygon import Polygon as Poly
    poly = Poly()
    for c_str in contours:
        if c_str.strip() != "":
            pts_str = c_str.strip()[1:].split("L")
            pts = []
            for pt_str in pts_str:
                x, y = map(float, pt_str.split(','))
                pts.append((x, y))
            poly.addContour(pts, is_clockwise(pts))
    return poly


def is_clockwise(pts):
    """
    returns true if a given polygon is in clockwise order
    """
    s = 0
    for i in range(len(pts) - 1):
        if 'x' in pts[i]:
            x1 = pts[i].x
            y1 = pts[i].y
            x2 = pts[i + 1].x
            y2 = pts[i + 1].y
        else:
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
        s += (x2 - x1) * (y2 + y1)
    return s >= 0

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
"""
command line interface for kartograph
"""

import argparse
import os
import os.path
from options import read_map_config
import sys


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


parser = argparse.ArgumentParser(prog='kartograph', description='Generates SVG maps from shapefiles')

parser.add_argument('config', type=argparse.FileType('r'), help='the configuration for the map. accepts json and yaml.')
parser.add_argument('--style', '-s', metavar='FILE', type=argparse.FileType('r'), help='map stylesheet')
parser.add_argument('--output', '-o', metavar='FILE', help='the file in which the map will be stored')
parser.add_argument('--verbose', '-v', nargs='?', metavar='', const=True, help='verbose mode')
parser.add_argument('--format', '-f', metavar='svg', help='output format, if not specified it will be guessed from output filename or default to svg')
parser.add_argument('--preview', '-p', nargs='?', metavar='', const=True, help='opens the generated svg for preview')
parser.add_argument('--pretty-print', '-P', dest='pretty_print', action='store_true', help='pretty print the svg file')

from kartograph import Kartograph
import time
import os


def render_map(args):
    cfg = read_map_config(args.config)
    K = Kartograph()
    if args.format:
        format = args.format
    elif args.output and args.output != '-':
        format = os.path.splitext(args.output)[1][1:]
    else:
        format = 'svg'
    try:

        # generate the map
        if args.style:
            css = args.style.read()
        else:
            css = None
        if args.output is None and not args.preview:
            args.output = '-'
        if args.output and args.output != '-':
            args.output = open(args.output, 'w')

        if args.pretty_print:
            if 'export' not in cfg:
                cfg['export'] = {}
            cfg['export']['prettyprint'] = True

        K.generate(cfg, args.output, preview=args.preview, format=format, stylesheet=css)
        if not args.output:
            # output to stdout
            # print str(r)
            pass

    except Exception, e:
        print_error(e)
        exit(-1)

parser.set_defaults(func=render_map)


def print_error(err):
    import traceback
    ignore_path_len = len(__file__) - 7
    exc = sys.exc_info()
    for (filename, line, func, code) in traceback.extract_tb(exc[2]):
        if filename[:len(__file__) - 7] == __file__[:-7]:
            sys.stderr.write('  \033[1;33;40m%s\033[0m, \033[0;37;40min\033[0m %s()\n  \033[1;31;40m%d:\033[0m \033[0;37;40m%s\033[0m' % (filename[ignore_path_len:], func, line, code))
        else:
            sys.stderr.write('  %s, in %s()\n  %d: %s' % (filename, func, line, code))
    sys.stderr.write('\n' + str(err))


def main():
    start = time.time()

    try:
        args = parser.parse_args()
    except IOError, e:
        # parser.print_help()
        sys.stderr.write('\n' + str(e) + '\n')
    except Exception, e:
        parser.print_help()
        print '\nError:', e
    else:
        args.func(args)
        elapsed = (time.time() - start)
        if args.output != '-':
            print 'execution time: %.3f secs' % elapsed

    sys.exit(0)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = errors
"""
error classes for kartograph
"""


class KartographError(Exception):
    """Base class for exceptions in this module."""
    def __str__(self):
        return '\033[0;31;40mKartograph-Error:\033[0m ' + super(KartographError, self).__str__()


class KartographOptionParseError(KartographError):
    pass


class KartographShapefileAttributesError(KartographError):
    pass


class KartographLayerSourceError(KartographError):
    pass

########NEW FILE########
__FILENAME__ = filter

"""
layer filter
"""

import re


def filter_record(filt, record):
    if isinstance(filt, dict):
        if 'and' in filt:
            res = True
            for sfilt in filt['and']:
                res = res and filter_record(sfilt, record)
        elif 'or' in filt:
            res = False
            for sfilt in filt['or']:
                res = res or filter_record(sfilt, record)
        else:
            res = True
            for key in filt:
                if isinstance(filt[key], (list, tuple)):
                    res = res and filter_record([key, 'in', filt[key]], record)
                else:
                    res = res and filter_record([key, '=', filt[key]], record)
    elif isinstance(filt, (list, tuple)):
        res = filter_single(filt, record)
    elif hasattr(filt, '__call__'):
        res = filt(record)
    return res


def filter_single(filt, record):
    key, comp, val = filt
    prop = record[key]
    comp = comp.lower().split(' ')

    if 'in' in comp:
        res = prop in val
    elif 'like' in comp:
        res = re.search('^' + _escape_regex(val).replace('%', '.*') + '$', prop) is not None
    elif 'matches' in comp:
        res = re.search(val, prop) is not None
    elif 'is' in comp or '=' in comp:
        res = prop == val
    elif 'greater' in comp or ('>' in comp):
        res = prop > val
    elif 'less' in comp or '<' in comp:
        res = prop < val
    if 'not' in comp:
        return not res
    else:
        return res


def _escape_regex(s):
    chars = ('.', '*', '?', '+', '(', ')', '[', ']', '-')
    for c in chars:
        s = s.replace(c, '\\' + c)
    return s

########NEW FILE########
__FILENAME__ = bbox

from point import Point


class BBox(object):
    """ 2D bounding box """
    def __init__(self, width=None, height=None, left=0, top=0):
        import sys
        if width == None:
            self.xmin = sys.maxint
            self.xmax = sys.maxint * -1
        else:
            self.xmin = self.left = left
            self.xmax = self.right = left + width
            self.width = width
        if height == None:
            self.ymin = sys.maxint
            self.ymax = sys.maxint * -1
        else:
            self.ymin = self.top = top
            self.ymax = self.bottom = height + top
            self.height = height

    def update(self, pt):
        if not isinstance(pt, Point):
            pt = Point(pt[0], pt[1])
        self.xmin = min(self.xmin, pt.x)
        self.ymin = min(self.ymin, pt.y)
        self.xmax = max(self.xmax, pt.x)
        self.ymax = max(self.ymax, pt.y)

        self.left = self.xmin
        self.top = self.ymin
        self.right = self.xmax
        self.bottom = self.ymax
        self.width = self.xmax - self.xmin
        self.height = self.ymax - self.ymin

    def intersects(self, bbox):
        """ returns true if two bounding boxes overlap """
        return bbox.left < self.right and bbox.right > self.left and bbox.top < self.bottom and bbox.bottom > self.top

    def check_point(self, pt):
        """ check if a point is inside the bbox """
        return pt[0] > self.xmin and pt[0] < self.xmax and pt[1] > self.ymin and pt[1] < self.ymax

    def __str__(self):
        return 'BBox(x=%.2f, y=%.2f, w=%.2f, h=%.2f)' % (self.left, self.top, self.width, self.height)

    def join(self, bbox):
        self.update(Point(bbox.left, bbox.top))
        self.update(Point(bbox.right, bbox.bottom))

    def inflate(self, amount=0, inflate=False):
        if inflate:
            d = min(self.width, self.height)
            amount += d * inflate
        self.xmin -= amount
        self.ymin -= amount
        self.xmax += amount
        self.ymax += amount

        self.left = self.xmin
        self.top = self.ymin
        self.right = self.xmax
        self.bottom = self.ymax
        self.width = self.xmax - self.xmin
        self.height = self.ymax - self.ymin

    def __getitem__(self, k):
        if k == 0:
            return self.xmin
        if k == 1:
            return self.ymin
        if k == 2:
            return self.xmax
        if k == 3:
            return self.ymax
        return None

########NEW FILE########
__FILENAME__ = Feature
from shapely.geos import TopologicalError
import sys

verbose = False

# # Feature
# Base class for map features. Each feature has a geometry (shapely.geometry.*)
# and a property dictionary


class Feature:
    def __init__(self, geometry, properties):
        self.geometry = geometry
        self.properties = properties

    def __repr__(self):
        return 'Feature(' + self.geometry.__class__.__name__ + ')'

    def project(self, proj):
        self.project_geometry(proj)

    def unify(self, point_store, precision=None):
        from kartograph.simplify import unify_polygons
        contours = self.contours
        contours = unify_polygons(contours, point_store, precision)
        self.apply_contours(contours)

    def project_view(self, view):
        if self.geometry:
            self.geometry = view.project_geometry(self.geometry)

    def crop_to(self, geometry):
        if self.geometry:
            if self.geometry.is_valid and geometry.is_valid:
                if self.geometry.intersects(geometry):
                    try:
                        self.geometry = self.geometry.intersection(geometry)
                    except TopologicalError:
                        self.geometry = None
                else:
                    self.geometry = None
            else:
                if verbose:
                    sys.stderr.write("warning: geometry is invalid")


    def subtract_geom(self, geom):
        if self.geometry:
            try:
                self.geometry = self.geometry.difference(geom)
            except TopologicalError:
                if verbose:
                    sys.stderr.write('warning: couldnt subtract from geometry')

    def project_geometry(self, proj):
        self.geometry = proj.plot(self.geometry)

    def is_empty(self):
        return self.geom is not None

    def is_simplifyable(self):
        return False

    @property
    def geom(self):
        return self.geometry

    @property
    def props(self):
        return self.properties

########NEW FILE########
__FILENAME__ = MultiLineFeature
from Feature import Feature
from kartograph.simplify.unify import unify_rings


class MultiLineFeature(Feature):
    """ wrapper around shapely.geometry.LineString """

    def __repr__(self):
        return 'MultiLineFeature(' + str(len(self.geometry.coords)) + ' pts)'

    def project_geometry(self, proj):
        """ project the geometry """
        self.geometry = proj.plot(self.geometry)

    def is_simplifyable(self):
        return True

    def compute_topology(self, point_store, precision=None):
        """
        converts the MultiLine geometry into a set of linear rings
        and 'unifies' the points in the rings in order to compute topology
        """
        rings = []
        for line in self._geoms:
            rings.append(line.coords)
        self._topology_rings = unify_rings(rings, point_store, precision=precision, feature=self)

    def break_into_lines(self):
        """
        temporarily stores the geometry in a custom representation in order
        to preserve topology during simplification
        """
        return self._topology_rings

    def restore_geometry(self, lines, minArea=0):
        """
        restores geometry from linear rings
        """
        from shapely.geometry import LineString, MultiLineString
        linestrings = []
        for line in lines:
            kept = []
            for pt in line:
                if not pt.deleted:
                    kept.append((pt[0], pt[1]))
            if len(kept) >= 2:
                linestrings.append(LineString(kept))

        if len(linestrings) > 0:
            self.geometry = MultiLineString(linestrings)
        else:
            self.geometry = None

    @property
    def _geoms(self):
        """ returns a list of geoms """
        return hasattr(self.geometry, 'geoms') and self.geometry.geoms or [self.geometry]

########NEW FILE########
__FILENAME__ = MultiPolygonFeature
from Feature import Feature
from kartograph.errors import KartographError
from kartograph.simplify.unify import unify_rings


class MultiPolygonFeature(Feature):
    """ wrapper around shapely.geometry.MultiPolygon """

    def __repr__(self):
        return 'MultiPolygonFeature()'

    def project_geometry(self, proj):
        """ project the geometry """
        self.geometry = proj.plot(self.geometry)

    def compute_topology(self, point_store, precision=None):
        """
        converts the MultiPolygon geometry into a set of linear rings
        and 'unifies' the points in the rings in order to compute topology
        """
        rings = []
        num_holes = []
        for polygon in self._geoms:
            num_holes.append(len(polygon.interiors))  # store number of holes per polygon
            ext = polygon.exterior.coords
            rings.append(ext)
            for hole in polygon.interiors:
                rings.append(hole.coords)
        self._topology_rings = unify_rings(rings, point_store, precision=precision, feature=self)
        self._topology_num_holes = num_holes

    def break_into_lines(self):
        """
        temporarily stores the geometry in a custom representation in order
        to preserve topology during simplification
        """
        # print '\n\n', self.props['NAME_1'],
        lines = []
        lines_per_ring = []
        for ring in self._topology_rings:
            l = 0  # store number of lines per ring
            s = 0
            i = s + 1
            K = len(ring)
            # print '\n\tnew ring (' + str(K) + ')',
            # find first break-point
            while i < K and ring[i].features == ring[i - 1].features:
                i += 1
            if i == len(ring):  # no break-point found at all
                line = ring  # so the entire ring is treated as one line
                # print len(line),
                lines.append(line)  # store it
                lines_per_ring.append(1)  # and remember that this ring has only 1 line
                continue  # proceed to next ring
            s = i  # store index of first break-point
            a = None
            # loop-entry conditions:
            # - 'a' holds the index of the break-point, equals to s
            # - 's' is the index of the first break-point in the entire ring
            while a != s:
                if a is None:
                    a = s  # if no break-point is set, start with the first one
                line = [a]  # add starting brak-point to line
                i = a + 1  # proceed to next point
                if i == K:
                    i = 0  # wrap around to first point if needed
                while i != s and ring[i].features == ring[((i - 1) + len(ring)) % len(ring)].features:  # look for end of this line
                    line.append(i)  # add point to line
                    i += 1  # proceed to next point
                    if i == K:
                        i = 0  # eventually wrap around
                #if i != s:
                #    line.append(i)  # add end point to line
                l += 1  # increase line-per-ring counter
                a = i  # set end point as next starting point
                #if a == s:  # if next starting point is the first break point..
                # line.append(s)  # append
                # print len(line),
                for ll in range(len(line)):
                    line[ll] = ring[line[ll]]  # replace point indices with actual points
                lines.append(line)  # store line
            lines_per_ring.append(l)

        self._topology_lines_per_ring = lines_per_ring
        return lines

    def restore_geometry(self, lines, minArea=0):
        """
        restores geometry from linear rings
        """
        from shapely.geometry import Polygon, MultiPolygon
        # at first we restore the rings
        rings = []
        isIslands = []
        p = 0
        for l in self._topology_lines_per_ring:
            ring = []
            island = True
            for k in range(p, p + l):
                line = []
                for pt in lines[k]:
                    if len(pt.features) > 1:
                        island = False
                    if not pt.deleted:
                        line.append((pt[0], pt[1]))
                ring += line
            p += l
            rings.append(ring)
            isIslands.append(island)
        # then we restore polygons from rings
        ring_iter = iter(rings)
        islands_iter = iter(isIslands)
        polygons = []
        holes_total = 0
        for num_hole in self._topology_num_holes:
            ext = ring_iter.next()
            island = islands_iter.next()
            holes = []
            while num_hole > 0:
                hole = ring_iter.next()
                islands_iter.next()  # skip island flag for holes
                if len(hole) > 3:
                    holes.append(hole)
                holes_total += 1
                num_hole -= 1
            if len(ext) > 3:
                poly = Polygon(ext, holes)
                if minArea == 0 or not island or poly.area > minArea:
                    polygons.append(poly)

        if len(polygons) > 0:
            self.geometry = MultiPolygon(polygons)
        else:
            self.geometry = None

    def is_simplifyable(self):
        return True

    @property
    def _geoms(self):
        """ returns a list of geoms """
        return hasattr(self.geometry, 'geoms') and self.geometry.geoms or [self.geometry]

########NEW FILE########
__FILENAME__ = PointFeature

from Feature import Feature


class PointFeature(Feature):
    """ wrapper around shapely.geometry.Point """

    def crop_to(self, geometry):
        if self.geometry:
            if self.geometry.is_valid:
                if not self.geometry.intersects(geometry):
                    self.geometry = None

########NEW FILE########
__FILENAME__ = point


class Point():
    """ base class for points, used by line and bbox """

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def project(self, proj):
        (x, y) = proj.project(self.x, self.y)
        self.x = x
        self.y = y

    """emulate python's container types"""
    def __len__(self):
        return 2

    def __getitem__(self, k):
        pt = (self.x, self.y)
        return pt[k]

    def __setitem__(self, k, value):
        if k == 0:
            self.x = value
        elif k == 1:
            self.y = value
        else:
            raise IndexError

    def __delitem__(self, key):
        raise TypeError('deletion not supported')

########NEW FILE########
__FILENAME__ = utils
"""
geometry utils
"""


def is_clockwise(pts):
    """ returns true if a given linear ring is in clockwise order """
    s = 0
    for i in range(len(pts) - 1):
        if 'x' in pts[i]:
            x1 = pts[i].x
            y1 = pts[i].y
            x2 = pts[i + 1].x
            y2 = pts[i + 1].y
        else:
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
        s += (x2 - x1) * (y2 + y1)
    return s >= 0


def bbox_to_polygon(bbox):
    from shapely.geometry import Polygon
    s = bbox
    poly = Polygon([(s.left, s.bottom), (s.left, s.top), (s.right, s.top), (s.right, s.bottom)])
    return poly


def geom_to_bbox(geom, min_area=0):
    from kartograph.geometry import BBox
    from shapely.geometry import MultiPolygon
    if min_area == 0 or not isinstance(geom, MultiPolygon):
        # if no minimum area ratio is set or the geometry
        # is not a multipart geometry, we simply use the
        # full bbox
        minx, miny, maxx, maxy = geom.bounds
        return BBox(width=maxx - minx, height=maxy - miny, left=minx, top=miny)
    else:
        # for multipart geometry we use only the bbox of
        # the 'biggest' sub-geometries, depending on min_area
        bbox = BBox()
        areas = []
        bb = []
        for polygon in geom.geoms:
            areas.append(polygon.area)
        max_a = max(areas)
        for i in range(len(geom.geoms)):
            a = areas[i]
            if a < max_a * min_area:
                # ignore this sub polygon since it is too small
                continue
            bb.append(geom.geoms[i].bounds)
    for b in bb:
        bbox.update((b[0], b[2]))
        bbox.update((b[1], b[2]))
        bbox.update((b[0], b[3]))
        bbox.update((b[1], b[3]))
    return bbox


def join_features(features, props, buf=False):
    """ joins polygonal features
    """
    from feature import MultiPolygonFeature, MultiLineFeature
    from shapely.ops import linemerge

    if len(features) == 0:
        return features

    joined = []
    polygons = []
    lines = []

    for feat in features:
        if isinstance(feat, MultiPolygonFeature):
            polygons.append(feat.geom)
        elif isinstance(feat, MultiLineFeature):
            lines.append(feat.geom)
        else:
            joined.append(feat)  # cannot join this

    polygons = filter(lambda x: x is not None, polygons)
    if len(polygons) > 0:
        poly = polygons[0]
        if buf is not False:
            poly = poly.buffer(buf, 4)
        for poly2 in polygons[1:]:
            if buf is not False:
                poly2 = poly2.buffer(buf, 4)
            poly = poly.union(poly2)
        joined.append(MultiPolygonFeature(poly, props))

    if len(lines) > 0:
        rings = []
        for line in lines:
            geoms = hasattr(line, 'geoms') and line.geoms or [line]
            rings += geoms
        joined.append(MultiLineFeature(linemerge(rings), props))
    return joined

########NEW FILE########
__FILENAME__ = view

from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, MultiPoint, Point
from kartograph.errors import KartographError


# # View

# Simple 2D coordinate transformation.

class View(object):
    """
    translates a point to a view
    """
    def __init__(self, bbox=None, width=None, height=None, padding=0):
        self.bbox = bbox
        self.width = width
        self.padding = padding
        self.height = height
        if bbox:
            self.scale = min((width - padding * 2) / bbox.width, (height - padding * 2) / bbox.height)

    def project(self, pt):
        bbox = self.bbox
        if not bbox:
            return pt
        s = self.scale
        h = self.height
        w = self.width
        px = pt[0]
        py = pt[1]
        x = (px - bbox.left) * s + (w - bbox.width * s) * .5
        y = (py - bbox.top) * s + (h - bbox.height * s) * .5
        return ((x, y), Point(x, y))[isinstance(pt, Point)]

    def project_inverse(self, pt):
        bbox = self.bbox
        if not bbox:
            return pt
        s = self.scale
        h = self.height
        w = self.width
        x = pt[0]
        y = pt[1]
        px = (x - (w - bbox.width * s) * .5) / s + bbox.left
        py = (y - (h - bbox.height * s) * .5) / s + bbox.top
        return ((px, py), Point(px, py))[isinstance(pt, Point)]

    def project_geometry(self, geometry):
        """ converts the given geometry to the view coordinates """
        geometries = hasattr(geometry, 'geoms') and geometry.geoms or [geometry]
        res = []

        # at first shift polygons
        #geometries = []
        #for geom in unshifted_geometries:
        #    geometries += self._shift_polygon(geom)

        for geom in geometries:
            if isinstance(geom, Polygon):
                res += self.project_polygon(geom)
            elif isinstance(geom, LineString):
                rings = self.project_linear_ring(geom)
                res += map(LineString, rings)
            elif isinstance(geom, Point):
                res.append(self.project((geom.x, geom.y)))
            else:
                raise KartographError('unknown geometry type %s' % geometry)

        if len(res) > 0:
            if isinstance(res[0], Polygon):
                if len(res) > 1:
                    return MultiPolygon(res)
                else:
                    return res[0]
            elif isinstance(res[0], LineString):
                if len(res) > 1:
                    return MultiLineString(res)
                else:
                    return LineString(res[0])
            else:
                if len(res) > 1:
                    return MultiPoint(res)
                else:
                    return Point(res[0])

    def project_polygon(self, polygon):
        ext = self.project_linear_ring(polygon.exterior)
        if len(ext) == 1:
            pts_int = []
            for interior in polygon.interiors:
                pts_int += self.project_linear_ring(interior)
            return [Polygon(ext[0], pts_int)]
        elif len(ext) == 0:
            return []
        else:
            raise KartographError('unhandled case: exterior is split into multiple rings')

    def project_linear_ring(self, ring):
        points = []
        for pt in ring.coords:
            x, y = self.project(pt)
            points.append((x, y))
        return [points]

    def __str__(self):
        return 'View(w=%f, h=%f, pad=%f, scale=%f, bbox=%s)' % (self.width, self.height, self.padding, self.scale, self.bbox)

########NEW FILE########
__FILENAME__ = kartograph

from options import parse_options
from shapely.geometry import Polygon, LineString, MultiPolygon
from errors import *
from copy import deepcopy
from renderer import SvgRenderer
from mapstyle import MapStyle
from map import Map
import os


# Kartograph
# ----------

verbose = False

# These renderers are currently available. See [renderer/svg.py](renderer/svg.html)

_known_renderer = {
    'svg': SvgRenderer
}


class Kartograph(object):
    def __init__(self):
        self.layerCache = {}
        pass

    def generate(self, opts, outfile=None, format='svg', preview=None, stylesheet=None):
        """
        Generates a the map and renders it using the specified output format.
        """
        if preview is None:
            preview = outfile is None

        # Create a deep copy of the options dictionary so our changes will not be
        # visible to the calling application.
        opts = deepcopy(opts)

        # Parse the options dictionary. See options.py for more details.
        parse_options(opts)

        # Create the map instance. It will do all the hard work for us, so you
        # definitely should check out [map.py](map.html) for all the fun stuff happending
        # there..
        _map = Map(opts, self.layerCache, format=format)

        # Check if the format is handled by a renderer.
        format = format.lower()
        if format in _known_renderer:
            # Create a stylesheet
            style = MapStyle(stylesheet)
            # Create a renderer instance and render the map.
            renderer = _known_renderer[format](_map)
            renderer.render(style, opts['export']['prettyprint'])

            if preview:
                if 'KARTOGRAPH_PREVIEW' in os.environ:
                    command = os.environ['KARTOGRAPH_PREVIEW']
                else:
                    commands = dict(win32='start', win64='start', darwin='open', linux2='xdg-open')
                    import sys
                    if sys.platform in commands:
                        command = commands[sys.platform]
                    else:
                        sys.stderr.write('don\'t know how to preview SVGs on your system. Try setting the KARTOGRAPH_PREVIEW environment variable.')
                        print renderer
                        return
                renderer.preview(command)
            # Write the map to a file or return the renderer instance.
            if outfile is None:
                return renderer
            elif outfile == '-':
                print renderer
            else:
                renderer.write(outfile)
        else:
            raise KartographError('unknown format: %s' % format)


# Here are some handy methods for debugging Kartograph. It will plot a given shapely
# geometry using matplotlib and descartes.
def _plot_geometry(geom, fill='#ffcccc', stroke='#333333', alpha=1, msg=None):
    from matplotlib import pyplot
    from matplotlib.figure import SubplotParams
    from descartes import PolygonPatch

    if isinstance(geom, (Polygon, MultiPolygon)):
        b = geom.bounds
        geoms = hasattr(geom, 'geoms') and geom.geoms or [geom]
        w, h = (b[2] - b[0], b[3] - b[1])
        ratio = w / h
        pad = 0.15
        fig = pyplot.figure(1, figsize=(5, 5 / ratio), dpi=110, subplotpars=SubplotParams(left=pad, bottom=pad, top=1 - pad, right=1 - pad))
        ax = fig.add_subplot(111, aspect='equal')
        for geom in geoms:
            patch1 = PolygonPatch(geom, linewidth=0.5, fc=fill, ec=stroke, alpha=alpha, zorder=0)
            ax.add_patch(patch1)
    p = (b[2] - b[0]) * 0.03  # some padding
    pyplot.axis([b[0] - p, b[2] + p, b[3] + p, b[1] - p])
    pyplot.grid(True)
    if msg:
        fig.suptitle(msg, y=0.04, fontsize=9)
    pyplot.show()


def _plot_lines(lines):
    from matplotlib import pyplot

    def plot_line(ax, line):
        filtered = []
        for pt in line:
            if not pt.deleted:
                filtered.append(pt)
        if len(filtered) < 2:
            return
        ob = LineString(line)
        x, y = ob.xy
        ax.plot(x, y, '-', color='#333333', linewidth=0.5, solid_capstyle='round', zorder=1)

    fig = pyplot.figure(1, figsize=(4, 5.5), dpi=90, subplotpars=SubplotParams(left=0, bottom=0.065, top=1, right=1))
    ax = fig.add_subplot(111, aspect='equal')
    for line in lines:
        plot_line(ax, line)
    pyplot.grid(False)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.set_frame_on(False)
    return (ax, fig)


def _debug_show_features(features, message=None):
    from descartes import PolygonPatch
    from matplotlib import pyplot
    from matplotlib.figure import SubplotParams

    fig = pyplot.figure(1, figsize=(9, 5.5), dpi=110, subplotpars=SubplotParams(left=0, bottom=0.065, top=1, right=1))
    ax = fig.add_subplot(111, aspect='equal')
    b = (100000, 100000, -100000, -100000)
    for feat in features:
        if feat.geom is None:
            continue
        c = feat.geom.bounds
        b = (min(c[0], b[0]), min(c[1], b[1]), max(c[2], b[2]), max(c[3], b[3]))
        geoms = hasattr(feat.geom, 'geoms') and feat.geom.geoms or [feat.geom]
        for geom in geoms:
            patch1 = PolygonPatch(geom, linewidth=0.25, fc='#ddcccc', ec='#000000', alpha=0.75, zorder=0)
            ax.add_patch(patch1)
    p = (b[2] - b[0]) * 0.05  # some padding
    pyplot.axis([b[0] - p, b[2] + p, b[3], b[1] - p])
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.set_frame_on(True)
    if message:
        fig.suptitle(message, y=0.04, fontsize=9)
    pyplot.show()

########NEW FILE########
__FILENAME__ = csvlayer

from layersource import LayerSource
from kartograph.errors import *
from kartograph.geometry import BBox, create_feature
from shapely.geometry import LineString, Point, Polygon

import csv
import pyproj


verbose = False


class CsvLayer(LayerSource):
    """
    this class handles csv layers
    """

    def __init__(self, src, mode, xfield, yfield, dialect, crs):
        """
        initialize shapefile reader
        """
        if isinstance(src, unicode):
            src = src.encode('ascii', 'ignore')
        self.cr = UnicodeReader(open(src), dialect=dialect)
        # read csv header
        self.header = h = self.cr.next()
        # initialize CRS
        self.proj = None
        self.mode = mode
        if crs is not None:
            if isinstance(crs, (str, unicode)):
                self.proj = pyproj.Proj(str(crs))
            elif isinstance(crs, dict):
                self.proj = pyproj.Proj(**crs)

        if xfield not in h or yfield not in h:
            raise KartographError('could not find csv column for coordinates (was looking for "%s" and "%s")' % (xfield, yfield))
        else:
            self.xfield = xfield
            self.yfield = yfield

    def get_features(self, filter=None, bbox=None, ignore_holes=False, charset='utf-8', min_area=0):
        # Eventually we convert the bbox list into a proper BBox instance
        if bbox is not None and not isinstance(bbox, BBox):
            bbox = BBox(bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1])
        mode = self.mode
        if mode in ('line', 'polygon'):
            coords = []
        features = []
        for row in self.cr:
            attrs = dict()
            for i in range(len(row)):
                key = self.header[i]
                if key == self.xfield:
                    x = float(row[i])
                elif key == self.yfield:
                    y = float(row[i])
                else:
                    attrs[key] = row[i]
            if self.proj is not None:
                # inverse project coord
                x, y = self.proj(x, y, inverse=True)
            if mode == 'points':
                features.append(create_feature(Point(x, y), attrs))
            else:
                coords.append((x, y))
        if mode == 'line':
            features.append(create_feature(LineString(coords), dict()))
        elif mode == 'polygon':
            features.append(create_feature(Polygon(coords), dict()))
        return features


import codecs


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self
########NEW FILE########
__FILENAME__ = layersource

import os.path
import os
from kartograph.errors import *


class LayerSource:
    """
    base class for layer source data providers (e.g. shapefiles)
    """
    def get_features(self, filter=None, bbox=None, ignore_holes=False, charset='utf-8'):
        raise NotImplementedError()

    def find_source(self, src):
        if not os.path.exists(src) and 'KARTOGRAPH_DATA' in os.environ:
            # try
            paths = os.environ['KARTOGRAPH_DATA'].split(os.pathsep)
            for path in paths:
                if path[:-1] != os.sep and src[0] != os.sep:
                    path = path + os.sep
                if os.path.exists(path + src):
                    src = path + src
                    break
            if not os.path.exists(src):
                raise KartographError('layer source not found: %s' % src)
        return src

########NEW FILE########
__FILENAME__ = postgislayer

from layersource import LayerSource
from kartograph.errors import *
from kartograph.geometry import create_feature
import shapely.wkb

verbose = False


class PostGISLayer(LayerSource):
    """
    This class handles PostGIS layers. You need a running PostgreSQL server
    with a PostGIS enabled database that stores your geodata.
    """

    def __init__(self, src, query='true', table='planet_osm_polygon'):
        """
        Initialize database connection
        """
        try:
            import psycopg2
        except ImportError:
            raise KartographError('You need to install psycopg2 (and PostgreSQL) if you want to render maps from PostGIS.\ne.g.\n    pip install psycopg2')
        self.conn = psycopg2.connect(src)
        self.query = query
        self.query_cache = dict()
        self.table = table

        cur = self.conn.cursor()

        # Read list of available properties
        self.fields = []
        cur.execute("SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = '%s';" % self.table)
        for rec in cur:
            self.fields.append(rec[0])

        # Find out which column stores the geoemtry data
        cur.execute("SELECT f_geometry_column FROM geometry_columns WHERE f_table_name = '%s'" % self.table)
        self.geom_col = cur.fetchone()[0]

    def get_features(self, filter=None, bbox=None, verbose=False, ignore_holes=False, min_area=False, charset='utf-8'):
        """
        ### Get features
        """
        # build query
        query = self.query
        if query == '':
            query = 'true'
        if bbox:
            # Check for intersection with bounding box
            bbox_coords = (bbox[0], bbox[2], bbox[1], bbox[2], bbox[1], bbox[3], bbox[0], bbox[3], bbox[0], bbox[2])
            bbox_poly = 'POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))' % bbox_coords
            query = "(%s) AND ST_Intersects( %s, ST_SetSRID(ST_GeomFromEWKT('%s'), 4326) )" % (query, self.geom_col, bbox_poly)

        # print "reading from postgis database / " + self.query

        # Open database connection
        cur = self.conn.cursor()
        fields = self.fields

        # Create a store for properties
        features = []
        # Query features
        cur.execute('SELECT "%s" FROM %s WHERE %s' % ('", "'.join(fields), self.table, query))

        for rec in cur:
            # Populate property dictionary
            meta = {}
            geom_wkb = None
            geom = None
            for f in range(len(fields)):
                if fields[f] != self.geom_col:
                    # but ignore null values
                    if rec[f]:
                        if isinstance(rec[f], (str, unicode)):
                            try:
                                meta[fields[f]] = rec[f].decode('utf-8')
                            except:
                                print 'decoding error', fields[f], rec[f]
                                meta[fields[f]] = '--decoding error--'
                        else:
                            meta[fields[f]] = rec[f]
                else:
                    # Store geometry
                    geom_wkb = rec[f]

            if filter is None or filter(meta):
                # construct geometry
                geom = shapely.wkb.loads(geom_wkb.decode('hex'))
                # Finally we construct the map feature and append it to the
                # result list
                features.append(create_feature(geom, meta))

        return features

########NEW FILE########
__FILENAME__ = shapefile
"""
shapefile.py
Provides read and write support for ESRI Shapefiles.
author: jlawhead<at>geospatialpython.com
date: 20110927
version: 1.1.4
Compatible with Python versions 2.4-3.x
"""

from struct import pack, unpack, calcsize, error
import os
import sys
import time
import array
#
# Constants for shape types
NULL = 0
POINT = 1
POLYLINE = 3
POLYGON = 5
MULTIPOINT = 8
POINTZ = 11
POLYLINEZ = 13
POLYGONZ = 15
MULTIPOINTZ = 18
POINTM = 21
POLYLINEM = 23
POLYGONM = 25
MULTIPOINTM = 28
MULTIPATCH = 31

PYTHON3 = sys.version_info[0] == 3

def b(v):
    if PYTHON3:
        if isinstance(v, str):
            # For python 3 encode str to bytes.
            return v.encode('utf-8')
        elif isinstance(v, bytes):
            # Already bytes.
            return v
        else:
            # Error.
            raise Exception('Unknown input type')
    else:
        # For python 2 assume str passed in and return str.
        return v

def u(v):
    if PYTHON3:
        if isinstance(v, bytes):
            # For python 3 decode bytes to str.
            return v.decode('utf-8')
        elif isinstance(v, str):
            # Already str.
            return v
        else:
            # Error.
            raise Exception('Unknown input type')
    else:
        # For python 2 assume str passed in and return str.
        return v

def is_string(v):
    if PYTHON3:
        return isinstance(v, str)
    else:
        return isinstance(v, basestring)

class _Array(array.array):
    """Converts python tuples to lits of the appropritate type.
    Used to unpack different shapefile header parts."""
    def __repr__(self):
        return str(self.tolist())

class _Shape:
    def __init__(self, shapeType=None):
        """Stores the geometry of the different shape types
        specified in the Shapefile spec. Shape types are
        usually point, polyline, or polygons. Every shape type
        except the "Null" type contains points at some level for
        example verticies in a polygon. If a shape type has
        multiple shapes containing points within a single
        geometry record then those shapes are called parts. Parts
        are designated by their starting index in geometry record's
        list of shapes."""
        self.shapeType = shapeType
        self.points = []

class _ShapeRecord:
    """A shape object of any type."""
    def __init__(self, shape=None, record=None):
        self.shape = shape
        self.record = record

class ShapefileException(Exception):
    """An exception to handle shapefile specific problems."""
    pass

class Reader:
    """Reads the three files of a shapefile as a unit or
    separately.  If one of the three files (.shp, .shx,
    .dbf) is missing no exception is thrown until you try
    to call a method that depends on that particular file.
    The .shx index file is used if available for efficiency
    but is not required to read the geometry from the .shp
    file. The "shapefile" argument in the constructor is the
    name of the file you want to open.

    You can instantiate a Reader without specifying a shapefile
    and then specify one later with the load() method.

    Only the shapefile headers are read upon loading. Content
    within each file is only accessed when required and as
    efficiently as possible. Shapefiles are usually not large
    but they can be.
    """
    def __init__(self, *args, **kwargs):
        self.shp = None
        self.shx = None
        self.dbf = None
        self.shapeName = "Not specified"
        self._offsets = []
        self.shpLength = None
        self.numRecords = None
        self.fields = []
        self.__dbfHdrLength = 0
        # See if a shapefile name was passed as an argument
        if len(args) > 0:
            if type(args[0]) is type("stringTest"):
                self.load(args[0])
                return
        if "shp" in kwargs.keys():
            if hasattr(kwargs["shp"], "read"):
                self.shp = kwargs["shp"]
                if hasattr(self.shp, "seek"):
                    self.shp.seek(0)
            if "shx" in kwargs.keys():
                if hasattr(kwargs["shx"], "read"):
                    self.shx = kwargs["shx"]
                    if hasattr(self.shx, "seek"):
                        self.shx.seek(0)
        if "dbf" in kwargs.keys():
            if hasattr(kwargs["dbf"], "read"):
                self.dbf = kwargs["dbf"]
                if hasattr(self.dbf, "seek"):
                    self.dbf.seek(0)
        if self.shp or self.dbf:        
            self.load()
        else:
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object.")

    def load(self, shapefile=None):
        """Opens a shapefile from a filename or file-like
        object. Normally this method would be called by the
        constructor with the file object or file name as an
        argument."""
        if shapefile:
            (shapeName, ext) = os.path.splitext(shapefile)
            self.shapeName = shapeName
            try:
                self.shp = open("%s.shp" % shapeName, "rb")
            except IOError:
                raise ShapefileException("Unable to open %s.shp" % shapeName)
            try:
                self.shx = open("%s.shx" % shapeName, "rb")
            except IOError:
                raise ShapefileException("Unable to open %s.shx" % shapeName)
            try:
                self.dbf = open("%s.dbf" % shapeName, "rb")
            except IOError:
                raise ShapefileException("Unable to open %s.dbf" % shapeName)
        if self.shp:
            self.__shpHeader()
        if self.dbf:
            self.__dbfHeader()

    def __getFileObj(self, f):
        """Checks to see if the requested shapefile file object is
        available. If not a ShapefileException is raised."""
        if not f:
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object.")
        if self.shp and self.shpLength is None:
            self.load()
        if self.dbf and len(self.fields) == 0:
            self.load()
        return f

    def __restrictIndex(self, i):
        """Provides list-like handling of a record index with a clearer
        error message if the index is out of bounds."""
        if self.numRecords:
            rmax = self.numRecords - 1
            if abs(i) > rmax:
                raise IndexError("Shape or Record index out of range.")
            if i < 0: i = range(self.numRecords)[i]
        return i

    def __shpHeader(self):
        """Reads the header information from a .shp or .shx file."""
        if not self.shp:
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object. (no shp file found")
        shp = self.shp
        # File length (16-bit word * 2 = bytes)
        shp.seek(24)
        self.shpLength = unpack(">i", shp.read(4))[0] * 2
        # Shape type
        shp.seek(32)
        self.shapeType= unpack("<i", shp.read(4))[0]
        # The shapefile's bounding box (lower left, upper right)
        self.bbox = _Array('d', unpack("<4d", shp.read(32)))
        # Elevation
        self.elevation = _Array('d', unpack("<2d", shp.read(16)))
        # Measure
        self.measure = _Array('d', unpack("<2d", shp.read(16)))

    def __shape(self):
        """Returns the header info and geometry for a single shape."""
        f = self.__getFileObj(self.shp)
        record = _Shape()
        nParts = nPoints = zmin = zmax = mmin = mmax = None
        (recNum, recLength) = unpack(">2i", f.read(8))
        shapeType = unpack("<i", f.read(4))[0]
        record.shapeType = shapeType
        # For Null shapes create an empty points list for consistency
        if shapeType == 0:
            record.points = []
        # All shape types capable of having a bounding box
        elif shapeType in (3,5,8,13,15,18,23,25,28,31):
            record.bbox = _Array('d', unpack("<4d", f.read(32)))
        # Shape types with parts
        if shapeType in (3,5,13,15,23,25,31):
            nParts = unpack("<i", f.read(4))[0]
        # Shape types with points
        if shapeType in (3,5,8,13,15,23,25,31):
            nPoints = unpack("<i", f.read(4))[0]
        # Read parts
        if nParts:
            record.parts = _Array('i', unpack("<%si" % nParts, f.read(nParts * 4)))
        # Read part types for Multipatch - 31
        if shapeType == 31:
            record.partTypes = _Array('i', unpack("<%si" % nParts, f.read(nParts * 4)))
        # Read points - produces a list of [x,y] values
        if nPoints:
            record.points = [_Array('d', unpack("<2d", f.read(16))) for p in range(nPoints)]
        # Read z extremes and values
        if shapeType in (13,15,18,31):
            (zmin, zmax) = unpack("<2d", f.read(16))
            record.z = _Array('d', unpack("<%sd" % nPoints, f.read(nPoints * 8)))
        # Read m extremes and values
        if shapeType in (18,23,25,28,31):
            (mmin, mmax) = unpack("<2d", f.read(16))
            # Measure values less than -10e38 are nodata values according to the spec
            record.m = []
            for m in _Array('d', unpack("%sd" % nPoints, f.read(nPoints * 8))):
                if m > -10e38:
                    record.m.append(m)
                else:
                    record.m.append(None)
        # Read a single point
        if shapeType in (1,11,21):
            record.points = [_Array('d', unpack("<2d", f.read(16)))]
        # Read a single Z value
        if shapeType == 11:
            record.z = unpack("<d", f.read(8))
        # Read a single M value
        if shapeType in (11,21):
            record.m = unpack("<d", f.read(8))
        return record

    def __shapeIndex(self, i=None):
        """Returns the offset in a .shp file for a shape based on information
        in the .shx index file."""
        shx = self.shx
        if not shx:
            return None
        if not self._offsets:
            # File length (16-bit word * 2 = bytes) - header length
            shx.seek(24)
            shxRecordLength = (unpack(">i", shx.read(4))[0] * 2) - 100
            numRecords = shxRecordLength // 8
            # Jump to the first record.
            shx.seek(100)
            for r in range(numRecords):
                # Offsets are 16-bit words just like the file length
                self._offsets.append(unpack(">i", shx.read(4))[0] * 2)
                shx.seek(shx.tell() + 4)
        if not i == None:
            return self._offsets[i]

    def shape(self, i=0):
        """Returns a shape object for a shape in the the geometry
        record file."""
        shp = self.__getFileObj(self.shp)
        i = self.__restrictIndex(i)
        offset = self.__shapeIndex(i)
        if not offset:
            # Shx index not available so use the full list.
            shapes = self.shapes()
            return shapes[i]
        shp.seek(offset)
        return self.__shape()

    def shapes(self):
        """Returns all shapes in a shapefile."""
        shp = self.__getFileObj(self.shp)
        shp.seek(100)
        shapes = []
        while shp.tell() < self.shpLength:
            shapes.append(self.__shape())
        return shapes

    def __dbfHeaderLength(self):
        """Retrieves the header length of a dbf file header."""
        if not self.__dbfHdrLength:
            if not self.dbf:
                raise ShapefileException("Shapefile Reader requires a shapefile or file-like object. (no dbf file found)")
            dbf = self.dbf
            (self.numRecords, self.__dbfHdrLength) = \
                    unpack("<xxxxLH22x", dbf.read(32))
        return self.__dbfHdrLength

    def __dbfHeader(self):
        """Reads a dbf header. Xbase-related code borrows heavily from ActiveState Python Cookbook Recipe 362715 by Raymond Hettinger"""
        if not self.dbf:
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object. (no dbf file found)")
        dbf = self.dbf
        headerLength = self.__dbfHeaderLength()
        numFields = (headerLength - 33) // 32
        for field in range(numFields):
            fieldDesc = list(unpack("<11sc4xBB14x", dbf.read(32)))
            name = 0
            idx = 0
            if b("\x00") in fieldDesc[name]:
                idx = fieldDesc[name].index(b("\x00"))
            else:
                idx = len(fieldDesc[name]) - 1
            fieldDesc[name] = fieldDesc[name][:idx]
            fieldDesc[name] = u(fieldDesc[name])
            fieldDesc[name] = fieldDesc[name].lstrip()
            fieldDesc[1] = u(fieldDesc[1])
            self.fields.append(fieldDesc)
        terminator = dbf.read(1)
        assert terminator == b("\r")
        self.fields.insert(0, ('DeletionFlag', 'C', 1, 0))

    def __recordFmt(self):
        """Calculates the size of a .shp geometry record."""
        if not self.numRecords:
            self.__dbfHeader()
        fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in self.fields])
        fmtSize = calcsize(fmt)
        return (fmt, fmtSize)

    def __record(self):
        """Reads and returns a dbf record row as a list of values."""
        f = self.__getFileObj(self.dbf)
        recFmt = self.__recordFmt()
        recordContents = unpack(recFmt[0], f.read(recFmt[1]))
        if recordContents[0] != b(' '):
            # deleted record
            return None
        record = []
        for (name, typ, size, deci), value in zip(self.fields, recordContents):
            if name == 'DeletionFlag':
                continue
            elif not value.strip():
                record.append(value)
                continue
            elif typ == "N":
                value = value.replace(b('\0'), b('')).strip()
                if value == b(''):
                    value = 0
                elif deci:
                    try:
                        value = float(value)
                    except:
                        value = 0
                else:
                    try:value = int(float(value))
                    except: value = 0
            elif typ == b('D'):
                try:
                    y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                    value = [y, m, d]
                except:
                    value = value.strip()
            elif typ == b('L'):
                value = (value in b('YyTt') and b('T')) or \
                                        (value in b('NnFf') and b('F')) or b('?')
            else:
                value = u(value)
                value = value.strip()
            record.append(value)
        return record

    def record(self, i=0):
        """Returns a specific dbf record based on the supplied index."""
        f = self.__getFileObj(self.dbf)
        if not self.numRecords:
            self.__dbfHeader()
        i = self.__restrictIndex(i)
        recSize = self.__recordFmt()[1]
        f.seek(0)
        f.seek(self.__dbfHeaderLength() + (i * recSize))
        return self.__record()

    def records(self):
        """Returns all records in a dbf file."""
        if not self.numRecords:
            self.__dbfHeader()
        records = []
        f = self.__getFileObj(self.dbf)
        f.seek(self.__dbfHeaderLength())
        for i in range(self.numRecords):
            r = self.__record()
            if r:
                records.append(r)
        return records

    def shapeRecord(self, i=0):
        """Returns a combination geometry and attribute record for the
        supplied record index."""
        i = self.__restrictIndex(i)
        return _ShapeRecord(shape=self.shape(i),
                                                        record=self.record(i))

    def shapeRecords(self):
        """Returns a list of combination geometry/attribute records for
        all records in a shapefile."""
        shapeRecords = []
        return [_ShapeRecord(shape=rec[0], record=rec[1]) \
                                for rec in zip(self.shapes(), self.records())]

class Writer:
    """Provides write support for ESRI Shapefiles."""
    def __init__(self, shapeType=None):
        self._shapes = []
        self.fields = []
        self.records = []
        self.shapeType = shapeType
        self.shp = None
        self.shx = None
        self.dbf = None
        # Geometry record offsets and lengths for writing shx file.
        self._offsets = []
        self._lengths = []
        # Use deletion flags in dbf? Default is false (0).
        self.deletionFlag = 0

    def __getFileObj(self, f):
        """Safety handler to verify file-like objects"""
        if not f:
            raise ShapefileException("No file-like object available.")
        elif hasattr(f, "write"):
            return f
        else:
            pth = os.path.split(f)[0]
            if pth and not os.path.exists(pth):
                os.makedirs(pth)
            return open(f, "wb")

    def __shpFileLength(self):
        """Calculates the file length of the shp file."""
        # Start with header length
        size = 100
        # Calculate size of all shapes
        for s in self._shapes:
            # Add in record header and shape type fields
            size += 12
            # nParts and nPoints do not apply to all shapes
            #if self.shapeType not in (0,1):
            #       nParts = len(s.parts)
            #       nPoints = len(s.points)
            if hasattr(s,'parts'):
                nParts = len(s.parts)
            if hasattr(s,'points'):
                nPoints = len(s.points)
            # All shape types capable of having a bounding box
            if self.shapeType in (3,5,8,13,15,18,23,25,28,31):
                size += 32
            # Shape types with parts
            if self.shapeType in (3,5,13,15,23,25,31):
                # Parts count
                size += 4
                # Parts index array
                size += nParts * 4
            # Shape types with points
            if self.shapeType in (3,5,8,13,15,23,25,31):
                # Points count
                size += 4
                # Points array
                size += 16 * nPoints
            # Calc size of part types for Multipatch (31)
            if self.shapeType == 31:
                size += nParts * 4
            # Calc z extremes and values
            if self.shapeType in (13,15,18,31):
                # z extremes
                size += 16
                # z array
                size += 8 * nPoints
            # Calc m extremes and values
            if self.shapeType in (23,25,31):
                # m extremes
                size += 16
                # m array
                size += 8 * nPoints
            # Calc a single point
            if self.shapeType in (1,11,21):
                size += 16
            # Calc a single Z value
            if self.shapeType == 11:
                size += 8
            # Calc a single M value
            if self.shapeType in (11,21):
                size += 8
        # Calculate size as 16-bit words
        size //= 2
        return size

    def __bbox(self, shapes, shapeTypes=[]):
        x = []
        y = []
        for s in shapes:
            shapeType = self.shapeType
            if shapeTypes:
                shapeType = shapeTypes[shapes.index(s)]
            px, py = list(zip(*s.points))[:2]
            x.extend(px)
            y.extend(py)
        return [min(x), min(y), max(x), max(y)]

    def __zbox(self, shapes, shapeTypes=[]):
        z = []
        for s in shapes:
            try:
                for p in s.points:
                    z.append(p[2])
            except IndexError:
                pass
        if not z: z.append(0)
        return [min(z), max(z)]

    def __mbox(self, shapes, shapeTypes=[]):
        m = [0]
        for s in shapes:
            try:
                for p in s.points:
                    m.append(p[3])
            except IndexError:
                pass
        return [min(m), max(m)]

    def bbox(self):
        """Returns the current bounding box for the shapefile which is
        the lower-left and upper-right corners. It does not contain the
        elevation or measure extremes."""
        return self.__bbox(self._shapes)

    def zbox(self):
        """Returns the current z extremes for the shapefile."""
        return self.__zbox(self._shapes)

    def mbox(self):
        """Returns the current m extremes for the shapefile."""
        return self.__mbox(self._shapes)

    def __shapefileHeader(self, fileObj, headerType='shp'):
        """Writes the specified header type to the specified file-like object.
        Several of the shapefile formats are so similar that a single generic
        method to read or write them is warranted."""
        f = self.__getFileObj(fileObj)
        f.seek(0)
        # File code, Unused bytes
        f.write(pack(">6i", 9994,0,0,0,0,0))
        # File length (Bytes / 2 = 16-bit words)
        if headerType == 'shp':
            f.write(pack(">i", self.__shpFileLength()))
        elif headerType == 'shx':
            f.write(pack('>i', ((100 + (len(self._shapes) * 8)) // 2)))
        # Version, Shape type
        f.write(pack("<2i", 1000, self.shapeType))
        # The shapefile's bounding box (lower left, upper right)
        if self.shapeType != 0:
            try:
                f.write(pack("<4d", *self.bbox()))
            except error:
                raise ShapefileException("Failed to write shapefile bounding box. Floats required.")
        else:
            f.write(pack("<4d", 0,0,0,0))
        # Elevation
        z = self.zbox()
        # Measure
        m = self.mbox()
        try:
            f.write(pack("<4d", z[0], z[1], m[0], m[1]))
        except error:
            raise ShapefileException("Failed to write shapefile elevation and measure values. Floats required.")

    def __dbfHeader(self):
        """Writes the dbf header and field descriptors."""
        f = self.__getFileObj(self.dbf)
        f.seek(0)
        version = 3
        year, month, day = time.localtime()[:3]
        year -= 1900
        # Remove deletion flag placeholder from fields
        for field in self.fields:
            if field[0].startswith("Deletion"):
                self.fields.remove(field)
        numRecs = len(self.records)
        numFields = len(self.fields)
        headerLength = numFields * 32 + 33
        recordLength = sum([int(field[2]) for field in self.fields]) + 1
        header = pack('<BBBBLHH20x', version, year, month, day, numRecs,
                headerLength, recordLength)
        f.write(header)
        # Field descriptors
        for field in self.fields:
            name, fieldType, size, decimal = field
            name = b(name)
            name = name.replace(b(' '), b('_'))
            name = name.ljust(11).replace(b(' '), b('\x00'))
            fieldType = b(fieldType)
            size = int(size)
            fld = pack('<11sc4xBB14x', name, fieldType, size, decimal)
            f.write(fld)
        # Terminator
        f.write(b('\r'))

    def __shpRecords(self):
        """Write the shp records"""
        f = self.__getFileObj(self.shp)
        f.seek(100)
        recNum = 1
        for s in self._shapes:
            self._offsets.append(f.tell())
            # Record number, Content length place holder
            f.write(pack(">2i", recNum, 0))
            recNum += 1
            start = f.tell()
            # Shape Type
            f.write(pack("<i", s.shapeType))
            # All shape types capable of having a bounding box
            if s.shapeType in (3,5,8,13,15,18,23,25,28,31):
                try:
                    f.write(pack("<4d", *self.__bbox([s])))
                except error:
                    raise ShapefileException("Falied to write bounding box for record %s. Expected floats." % recNum)
            # Shape types with parts
            if s.shapeType in (3,5,13,15,23,25,31):
                # Number of parts
                f.write(pack("<i", len(s.parts)))
            # Shape types with multiple points per record
            if s.shapeType in (3,5,8,13,15,23,25,31):
                # Number of points
                f.write(pack("<i", len(s.points)))
            # Write part indexes
            if s.shapeType in (3,5,13,15,23,25,31):
                for p in s.parts:
                    f.write(pack("<i", p))
            # Part types for Multipatch (31)
            if s.shapeType == 31:
                for pt in s.partTypes:
                    f.write(pack("<i", pt))
            # Write points for multiple-point records
            if s.shapeType in (3,5,8,13,15,23,25,31):
                try:
                    [f.write(pack("<2d", *p[:2])) for p in s.points]
                except error:
                    raise ShapefileException("Failed to write points for record %s. Expected floats." % recNum)
            # Write z extremes and values
            if s.shapeType in (13,15,18,31):
                try:
                    f.write(pack("<2d", *self.__zbox([s])))
                except error:
                    raise ShapefileException("Failed to write elevation extremes for record %s. Expected floats." % recNum)
                try:
                    [f.write(pack("<d", p[2])) for p in s.points]
                except error:
                    raise ShapefileException("Failed to write elevation values for record %s. Expected floats." % recNum)
            # Write m extremes and values
            if s.shapeType in (23,25,31):
                try:
                    f.write(pack("<2d", *self.__mbox([s])))
                except error:
                    raise ShapefileException("Failed to write measure extremes for record %s. Expected floats" % recNum)
                try:
                    [f.write(pack("<d", p[3])) for p in s.points]
                except error:
                    raise ShapefileException("Failed to write measure values for record %s. Expected floats" % recNum)
            # Write a single point
            if s.shapeType in (1,11,21):
                try:
                    f.write(pack("<2d", s.points[0][0], s.points[0][1]))
                except error:
                    raise ShapefileException("Failed to write point for record %s. Expected floats." % recNum)
            # Write a single Z value
            if s.shapeType == 11:
                try:
                    f.write(pack("<1d", s.points[0][2]))
                except error:
                    raise ShapefileException("Failed to write elevation value for record %s. Expected floats." % recNum)
            # Write a single M value
            if s.shapeType in (11,21):
                try:
                    f.write(pack("<1d", s.points[0][3]))
                except error:
                    raise ShapefileException("Failed to write measure value for record %s. Expected floats." % recNum)
            # Finalize record length as 16-bit words
            finish = f.tell()
            length = (finish - start) // 2
            self._lengths.append(length)
            # start - 4 bytes is the content length field
            f.seek(start-4)
            f.write(pack(">i", length))
            f.seek(finish)

    def __shxRecords(self):
        """Writes the shx records."""
        f = self.__getFileObj(self.shx)
        f.seek(100)
        for i in range(len(self._shapes)):
            f.write(pack(">i", self._offsets[i] // 2))
            f.write(pack(">i", self._lengths[i]))

    def __dbfRecords(self):
        """Writes the dbf records."""
        f = self.__getFileObj(self.dbf)
        for record in self.records:
            if not self.fields[0][0].startswith("Deletion"):
                f.write(b(' ')) # deletion flag
            for (fieldName, fieldType, size, dec), value in zip(self.fields, record):
                fieldType = fieldType.upper()
                size = int(size)
                if fieldType.upper() == "N":
                    value = str(value).rjust(size)
                elif fieldType == 'L':
                    value = str(value)[0].upper()
                else:
                    value = str(value)[:size].ljust(size)
                assert len(value) == size
                value = b(value)
                f.write(value)

    def null(self):
        """Creates a null shape."""
        self._shapes.append(_Shape(NULL))

    def point(self, x, y, z=0, m=0):
        """Creates a point shape."""
        pointShape = _Shape(self.shapeType)
        pointShape.points.append([x, y, z, m])
        self._shapes.append(pointShape)

    def line(self, parts=[], shapeType=POLYLINE):
        """Creates a line shape. This method is just a convienience method
        which wraps 'poly()'.
        """
        self.poly(parts, shapeType, [])

    def poly(self, parts=[], shapeType=POLYGON, partTypes=[]):
        """Creates a shape that has multiple collections of points (parts)
        including lines, polygons, and even multipoint shapes. If no shape type
        is specified it defaults to 'polygon'. If no part types are specified
        (which they normally won't be) then all parts default to the shape type.
        """
        polyShape = _Shape(shapeType)
        polyShape.parts = []
        polyShape.points = []
        for part in parts:
            polyShape.parts.append(len(polyShape.points))
            for point in part:
                # Ensure point is list
                if not isinstance(point, list):
                    point = list(point)
                # Make sure point has z and m values
                while len(point) < 4:
                    point.append(0)
                polyShape.points.append(point)
        if polyShape.shapeType == 31:
            if not partTypes:
                for part in parts:
                    partTypes.append(polyShape.shapeType)
            polyShape.partTypes = partTypes
        self._shapes.append(polyShape)

    def field(self, name, fieldType="C", size="50", decimal=0):
        """Adds a dbf field descriptor to the shapefile."""
        self.fields.append((name, fieldType, size, decimal))

    def record(self, *recordList, **recordDict):
        """Creates a dbf attribute record. You can submit either a sequence of
        field values or keyword arguments of field names and values. Before
        adding records you must add fields for the record values using the
        fields() method. If the record values exceed the number of fields the
        extra ones won't be added. In the case of using keyword arguments to specify
        field/value pairs only fields matching the already registered fields
        will be added."""
        record = []
        fieldCount = len(self.fields)
        # Compensate for deletion flag
        if self.fields[0][0].startswith("Deletion"): fieldCount -= 1
        if recordList:
            [record.append(recordList[i]) for i in range(fieldCount)]
        elif recordDict:
            for field in self.fields:
                if field[0] in recordDict:
                    val = recordDict[field[0]]
                    if val:
                        record.append(val)
                    else:
                        record.append("")
        if record:
            self.records.append(record)

    def shape(self, i):
        return self._shapes[i]

    def shapes(self):
        """Return the current list of shapes."""
        return self._shapes

    def saveShp(self, target):
        """Save an shp file."""
        if not hasattr(target, "write"):
            target = os.path.splitext(target)[0] + '.shp'
        if not self.shapeType:
            self.shapeType = self._shapes[0].shapeType
        self.shp = self.__getFileObj(target)
        self.__shapefileHeader(self.shp, headerType='shp')
        self.__shpRecords()

    def saveShx(self, target):
        """Save an shx file."""
        if not hasattr(target, "write"):
            target = os.path.splitext(target)[0] + '.shx'
        if not self.shapeType:
            self.shapeType = self._shapes[0].shapeType
        self.shx = self.__getFileObj(target)
        self.__shapefileHeader(self.shx, headerType='shx')
        self.__shxRecords()

    def saveDbf(self, target):
        """Save a dbf file."""
        if not hasattr(target, "write"):
            target = os.path.splitext(target)[0] + '.dbf'
        self.dbf = self.__getFileObj(target)
        self.__dbfHeader()
        self.__dbfRecords()

    def save(self, target=None, shp=None, shx=None, dbf=None):
        """Save the shapefile data to three files or
        three file-like objects. SHP and DBF files can also
        be written exclusively using saveShp, saveShx, and saveDbf respectively."""
        # TODO: Create a unique filename for target if None.
        if shp:
            self.saveShp(shp)
        if shx:
            self.saveShx(shx)
        if dbf:
            self.saveDbf(dbf)
        elif target:
            self.saveShp(target)
            self.shp.close()
            self.saveShx(target)
            self.shx.close()
            self.saveDbf(target)
            self.dbf.close()

class Editor(Writer):
    def __init__(self, shapefile=None, shapeType=POINT, autoBalance=1):
        self.autoBalance = autoBalance
        if not shapefile:
            Writer.__init__(self, shapeType)
        elif is_string(shapefile):
            base = os.path.splitext(shapefile)[0]
            if os.path.isfile("%s.shp" % base):
                r = Reader(base)
                Writer.__init__(self, r.shapeType)
                self._shapes = r.shapes()
                self.fields = r.fields
                self.records = r.records()

    def select(self, expr):
        """Select one or more shapes (to be implemented)"""
        # TODO: Implement expressions to select shapes.
        pass

    def delete(self, shape=None, part=None, point=None):
        """Deletes the specified part of any shape by specifying a shape
        number, part number, or point number."""
        # shape, part, point
        if shape and part and point:
            del self._shapes[shape][part][point]
        # shape, part
        elif shape and part and not point:
            del self._shapes[shape][part]
        # shape
        elif shape and not part and not point:
            del self._shapes[shape]
        # point
        elif not shape and not part and point:
            for s in self._shapes:
                if s.shapeType == 1:
                    del self._shapes[point]
                else:
                    for part in s.parts:
                        del s[part][point]
        # part, point
        elif not shape and part and point:
            for s in self._shapes:
                del s[part][point]
        # part
        elif not shape and part and not point:
            for s in self._shapes:
                del s[part]

    def point(self, x=None, y=None, z=None, m=None, shape=None, part=None, point=None, addr=None):
        """Creates/updates a point shape. The arguments allows
        you to update a specific point by shape, part, point of any
        shape type."""
        # shape, part, point
        if shape and part and point:
            try: self._shapes[shape]
            except IndexError: self._shapes.append([])
            try: self._shapes[shape][part]
            except IndexError: self._shapes[shape].append([])
            try: self._shapes[shape][part][point]
            except IndexError: self._shapes[shape][part].append([])
            p = self._shapes[shape][part][point]
            if x: p[0] = x
            if y: p[1] = y
            if z: p[2] = z
            if m: p[3] = m
            self._shapes[shape][part][point] = p
        # shape, part
        elif shape and part and not point:
            try: self._shapes[shape]
            except IndexError: self._shapes.append([])
            try: self._shapes[shape][part]
            except IndexError: self._shapes[shape].append([])
            points = self._shapes[shape][part]
            for i in range(len(points)):
                p = points[i]
                if x: p[0] = x
                if y: p[1] = y
                if z: p[2] = z
                if m: p[3] = m
                self._shapes[shape][part][i] = p
        # shape
        elif shape and not part and not point:
            try: self._shapes[shape]
            except IndexError: self._shapes.append([])

        # point
        # part
        if addr:
            shape, part, point = addr
            self._shapes[shape][part][point] = [x, y, z, m]
        else:
            Writer.point(self, x, y, z, m)
        if self.autoBalance:
            self.balance()

    def validate(self):
        """An optional method to try and validate the shapefile
        as much as possible before writing it (not implemented)."""
        #TODO: Implement validation method
        pass

    def balance(self):
        """Adds a corresponding empty attribute or null geometry record depending
        on which type of record was created to make sure all three files
        are in synch."""
        if len(self.records) > len(self._shapes):
            self.null()
        elif len(self.records) < len(self._shapes):
            self.record()

    def __fieldNorm(self, fieldName):
        """Normalizes a dbf field name to fit within the spec and the
        expectations of certain ESRI software."""
        if len(fieldName) > 11: fieldName = fieldName[:11]
        fieldName = fieldName.upper()
        fieldName.replace(' ', '_')

# Begin Testing
def test():
    import doctest
    doctest.NORMALIZE_WHITESPACE = 1
    doctest.testfile("README.txt", verbose=1)

if __name__ == "__main__":
    """
    Doctests are contained in the module 'pyshp_usage.py'. This library was developed
    using Python 2.3. Python 2.4 and above have some excellent improvements in the built-in
    testing libraries but for now unit testing is done using what's available in
    2.3.
    """
    test()

########NEW FILE########
__FILENAME__ = shplayer

from layersource import LayerSource
from kartograph.errors import *
from kartograph.geometry import BBox, create_feature
from os.path import exists
from osgeo.osr import SpatialReference
import pyproj
import shapefile


verbose = False


class ShapefileLayer(LayerSource):
    """
    this class handles shapefile layers
    """

    def __init__(self, src):
        """
        initialize shapefile reader
        """
        if isinstance(src, unicode):
            src = src.encode('ascii', 'ignore')
        src = self.find_source(src)
        self.shpSrc = src
        self.sr = shapefile.Reader(src)
        self.recs = []
        self.shapes = {}
        self.load_records()
        self.proj = None
        # Check if there's a spatial reference
        prj_src = src[:-4] + '.prj'
        if exists(prj_src):
            prj_text = open(prj_src).read()
            srs = SpatialReference()
            if srs.ImportFromWkt(prj_text):
                raise ValueError("Error importing PRJ information from: %s" % prj_file)
            if srs.IsProjected():
                self.proj = pyproj.Proj(srs.ExportToProj4())
                #print srs.ExportToProj4()

    def load_records(self):
        """
        ### Load records
        Load shapefile records into memory (but not the shapes).
        """
        self.recs = self.sr.records()
        self.attributes = []
        for a in self.sr.fields[1:]:
            self.attributes.append(a[0])
        i = 0
        self.attrIndex = {}
        for attr in self.attributes:
            self.attrIndex[attr] = i
            i += 1

    def get_shape(self, i):
        """
        ### Get shape
        Returns a shape of this shapefile. If the shape is requested for the first time,
        it will be loaded from the shapefile. Otherwise it will loaded from cache.
        """
        if i in self.shapes:  # check cache
            shp = self.shapes[i]
        else:  # load shape from shapefile
            shp = self.shapes[i] = self.sr.shapeRecord(i).shape
        return shp


    def forget_shape(self, i):
        if i in self.shapes:
            self.shapes.pop(i)

    def get_features(self, attr=None, filter=None, bbox=None, ignore_holes=False, min_area=False, charset='utf-8'):
        """
        ### Get features
        """
        res = []
        # We will try these encodings..
        known_encodings = ['utf-8', 'latin-1', 'iso-8859-2', 'iso-8859-15']
        try_encodings = [charset]
        for enc in known_encodings:
            if enc != charset:
                try_encodings.append(enc)
        # Eventually we convert the bbox list into a proper BBox instance
        if bbox is not None and not isinstance(bbox, BBox):
            bbox = BBox(bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1])
        ignored = 0
        for i in range(0, len(self.recs)):
            # Read all record attributes
            drec = {}
            for j in range(len(self.attributes)):
                drec[self.attributes[j]] = self.recs[i][j]
            # For each record that is not filtered..
            if filter is None or filter(drec):
                props = {}
                # ..we try to decode the attributes (shapefile charsets are arbitrary)
                for j in range(len(self.attributes)):
                    val = self.recs[i][j]
                    decoded = False
                    if isinstance(val, str):
                        for enc in try_encodings:
                            try:
                                val = val.decode(enc)
                                decoded = True
                                break
                            except:
                                if verbose:
                                    print 'warning: could not decode "%s" to %s' % (val, enc)
                        if not decoded:
                            raise KartographError('having problems to decode the input data "%s"' % val)
                    if isinstance(val, (str, unicode)):
                        val = val.strip()
                    props[self.attributes[j]] = val

                # Read the shape from the shapefile (can take some time..)..
                shp = self.get_shape(i)

                # ..and convert the raw shape into a shapely.geometry
                geom = shape2geometry(shp, ignore_holes=ignore_holes, min_area=min_area, bbox=bbox, proj=self.proj)
                if geom is None:
                    ignored += 1
                    self.forget_shape(i)
                    continue

                # Finally we construct the map feature and append it to the
                # result list
                feature = create_feature(geom, props)
                res.append(feature)
        if bbox is not None and ignored > 0 and verbose:
            print "-ignoring %d shapes (not in bounds %s )" % (ignored, bbox)
        return res

# # shape2geometry


def shape2geometry(shp, ignore_holes=False, min_area=False, bbox=False, proj=None):
    if shp is None:
        return None
    if bbox and shp.shapeType != 1:
        if proj:
            left, top = proj(shp.bbox[0], shp.bbox[1], inverse=True)
            right, btm = proj(shp.bbox[2], shp.bbox[3], inverse=True)
        else:
            left, top, right, btm = shp.bbox
        sbbox = BBox(left=left, top=top, width=right - left, height=btm - top)
        if not bbox.intersects(sbbox):
            # ignore the shape if it's not within the bbox
            return None

    if shp.shapeType in (5, 15):  # multi-polygon
        geom = shape2polygon(shp, ignore_holes=ignore_holes, min_area=min_area, proj=proj)
    elif shp.shapeType in (3, 13):  # line
        geom = shape2line(shp, proj=proj)
    elif shp.shapeType == 1: # point
        geom = shape2point(shp, proj=proj)
    else:
        raise KartographError('unknown shape type (%d)' % shp.shapeType)
    return geom


def shape2polygon(shp, ignore_holes=False, min_area=False, proj=None):
    """
    converts a shapefile polygon to geometry.MultiPolygon
    """
    # from kartograph.geometry import MultiPolygon
    from shapely.geometry import Polygon, MultiPolygon
    from kartograph.geometry.utils import is_clockwise
    parts = shp.parts[:]
    parts.append(len(shp.points))
    exteriors = []
    holes = []
    for j in range(len(parts) - 1):
        pts = shp.points[parts[j]:parts[j + 1]]
        if shp.shapeType == 15:
            # remove z-coordinate from PolygonZ contours (not supported)
            for k in range(len(pts)):
                pts[k] = pts[k][:2]
        if proj:
            project_coords(pts, proj)
        cw = is_clockwise(pts)
        if cw:
            exteriors.append(pts)
        else:
            holes.append(pts)
    if ignore_holes:
        holes = None
    if len(exteriors) == 1:
        poly = Polygon(exteriors[0], holes)
    elif len(exteriors) > 1:
        # use multipolygon, but we need to assign the holes to the right
        # exteriors
        from kartograph.geometry import BBox
        used_holes = set()
        polygons = []
        for ext in exteriors:
            bbox = BBox()
            my_holes = []
            for pt in ext:
                bbox.update(pt)
            for h in range(len(holes)):
                if h not in used_holes:
                    hole = holes[h]
                    if bbox.check_point(hole[0]):
                        # this is a very weak test but it should be sufficient
                        used_holes.add(h)
                        my_holes.append(hole)
            polygons.append(Polygon(ext, my_holes))
        if min_area:
            # compute maximum area
            max_area = 0
            for poly in polygons:
                max_area = max(max_area, poly.area)
            # filter out polygons that are below min_area * max_area
            polygons = [poly for poly in polygons if poly.area >= min_area * max_area]
        poly = MultiPolygon(polygons)
    else:
        raise KartographError('shapefile import failed - no outer polygon found')
    return poly


def shape2line(shp, proj=None):
    """ converts a shapefile line to geometry.Line """
    from shapely.geometry import LineString, MultiLineString

    parts = shp.parts[:]
    parts.append(len(shp.points))
    lines = []
    for j in range(len(parts) - 1):
        pts = shp.points[parts[j]:parts[j + 1]]
        if shp.shapeType == 13:
            # remove z-coordinate from PolylineZ contours (not supported)
            for k in range(len(pts)):
                pts[k] = pts[k][:2]
        if proj:
            project_coords(pts, proj)
        lines.append(pts)
    if len(lines) == 1:
        return LineString(lines[0])
    elif len(lines) > 1:
        return MultiLineString(lines)
    else:
        raise KartographError('shapefile import failed - no line found')

def shape2point(shp, proj=None):
    from shapely.geometry import MultiPoint, Point
    points = shp.points[:]
    if len(points) == 1:
        return Point(points[0])
    elif len(points) > 1:
        return MultiPoint(points)
    else:
        raise KartographError('shapefile import failed - no points found')
    
  
def project_coords(pts, proj):
    for i in range(len(pts)):
        x, y = proj(pts[i][0], pts[i][1], inverse=True)
        pts[i][0] = x
        pts[i][1] = y

########NEW FILE########
__FILENAME__ = graticule

from kartograph.geometry import MultiLineFeature
from kartograph.layersource.layersource import LayerSource
from shapely.geometry import LineString


class GraticuleLayer(LayerSource):
    """
    special layer source for grid of longitudes and latitudes (graticule)
    """
    def get_features(self, latitudes, longitudes, proj, bbox=[-180, -90, 180, 90]):
        """
        returns a list of line features that make up
        the graticule
        """
        minLat = max(proj.minLat, bbox[1])
        maxLat = min(proj.maxLat, bbox[3])
        minLon = bbox[0]
        maxLon = bbox[2]

        def xfrange(start, stop, step):
            while (step > 0 and start < stop) or (step < 0 and start > step):
                yield start
                start += step

        line_features = []
        # latitudes
        for lat in latitudes:
            if lat < minLat or lat > maxLat:
                continue
            pts = []
            props = {'lat': lat}
            for lon in xfrange(-180, 181, 0.5):
                if lon < minLon or lon > maxLon:
                    continue
                #if isinstance(proj, Azimuthal):
                #    lon += proj.lon0
                #    if lon < -180:
                #        lon += 360
                #    if lon > 180:
                #        lon -= 360
                if proj._visible(lon, lat):
                    pts.append((lon, lat))
            if len(pts) > 1:
                line = MultiLineFeature(LineString(pts), props)
                line_features.append(line)
        # print line_features

        # longitudes
        for lon in longitudes:
            if lon < minLon or lon > maxLon:
                continue
            pts = []
            props = {'lon': lon}
            #lat_range = xfrange(step[0], 181-step[0],1)
            #if lon % 90 == 0:
            #    lat_range = xfrange(0, 181,1)
            for lat in xfrange(0, 181, 0.5):
                lat_ = lat - 90
                if lat_ < minLat or lat_ > maxLat:
                    continue
                if proj._visible(lon, lat_):
                    pts.append((lon, lat_))
            if len(pts) > 1:
                line = MultiLineFeature(LineString(pts), props)
                line_features.append(line)

        return line_features

########NEW FILE########
__FILENAME__ = sea

from kartograph.geometry import MultiPolygonFeature
from kartograph.layersource.layersource import LayerSource


class SeaLayer(LayerSource):
    """
    special layer source for grid of longitudes and latitudes (graticule)
    """

    def get_features(self, proj):
        #props = { '__color__':'#d0ddf0' }
        # geom = MultiPolygon(sea_poly)
        geom = proj.bounding_geometry(projected=True)
        return [MultiPolygonFeature(geom, {})]

########NEW FILE########
__FILENAME__ = map
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from maplayer import MapLayer
from geometry.utils import geom_to_bbox
from geometry import BBox, View
from proj import projections
from filter import filter_record
from errors import KartographError
import sys

# Map
# ---
#
# This class performs like 80% of the functionality of Kartograph. It
# loads the features for each layer, processes them and passes them
# to a renderer at the end.

verbose = False


class Map(object):

    def __init__(me, options, layerCache, format='svg', src_encoding=None):
        me.options = options
        me.format = format
        # List and dictionary references to the map layers.
        me.layers = []
        me.layersById = {}
        # We will cache the bounding geometry since we need it twice, eventually.
        me._bounding_geometry_cache = False
        me._unprojected_bounds = None
        # The **source encoding** will be used as first guess when Kartograph tries to decode
        # the meta data of shapefiles etc. We use Unicode as default source encoding.
        if not src_encoding:
            src_encoding = 'utf-8'
        me._source_encoding = src_encoding

        # Construct [MapLayer](maplayer.py) instances for every layer and store references
        # to the layers in a list and a dictionary.
        for layer_cfg in options['layers']:
            layer_id = layer_cfg['id']
            layer = MapLayer(layer_id, layer_cfg, me, layerCache)
            me.layers.append(layer)
            me.layersById[layer_id] = layer

        # Initialize the projection that will be used in this map. This sounds easier than
        # it is since we need to compute lot's of stuff here.
        me.proj = me._init_projection()
        # Compute the bounding geometry for the map.
        me.bounds_poly = me._init_bounds()
        # Set up the [view](geometry/view.py) which will transform from projected coordinates
        # (e.g. in meters) to screen coordinates in our map output.
        me.view = me._get_view()
        # Get the polygon (in fact it's a rectangle in most cases) that will be used
        # to clip away unneeded geometry unless *cfg['export']['crop-to-view']* is set to false.
        me.view_poly = me._init_view_poly()

        # Load all features that could be visible in each layer. The feature geometries will
        # be projected and transformed to screen coordinates.
        for layer in me.layers:
            layer.get_features()

        # In each layer we will join polygons.
        me._join_features()
        # Eventually we crop geometries to the map bounding rectangle.
        if options['export']['crop-to-view']:
            me._crop_layers_to_view()
        # Here's where we apply the simplification to geometries.
        me._simplify_layers()
        # Also we can crop layers to another layer, useful if we need to limit geological
        # geometries such as tree coverage to a political boundary of a country.
        me._crop_layers()
        # Or subtract one layer from another (or more), for instance to cut out lakes
        # from political boundaries.
        me._subtract_layers()

    def _init_projection(self):
        """
        ### Initializing the map projection
        """
        opts = self.options
        # If either *lat0* or *lon0* were set to "auto", we need to
        # compute a nice center of the projection and update the
        # projection configuration.
        autoLon = 'lon0' in opts['proj'] and opts['proj']['lon0'] == 'auto'
        autoLat = 'lat0' in opts['proj'] and opts['proj']['lat0'] == 'auto'
        if autoLon or autoLat:
            map_center = self.__get_map_center()
            if autoLon:
                opts['proj']['lon0'] = map_center[0]
            if autoLat:
                opts['proj']['lat0'] = map_center[1]

        # Load the projection class, if the id is known.
        if opts['proj']['id'] in projections:
            projC = projections[opts['proj']['id']]
        else:
            raise KartographError('projection unknown %s' % opts['proj']['id'])
        # Populate a dictionary of projection properties that
        # will be passed to the projection constructor as keyword
        # arguments.
        p_opts = {}
        for prop in opts['proj']:
            if prop != "id":
                p_opts[prop] = opts['proj'][prop]
        return projC(**p_opts)

    def __get_map_center(self):
        """
        ### Determining the projection center
        """
        # To find out where the map will be centered to we need to
        # know the geographical boundaries.
        opts = self.options
        mode = opts['bounds']['mode']
        data = opts['bounds']['data']

        # If the bound mode is set to *bbox* we simply
        # take the mean latitude and longitude as center.
        if mode == 'bbox':
            lon0 = data[0] + 0.5 * (data[2] - data[0])
            lat0 = data[1] + 0.5 * (data[3] - data[1])

        # If the bound mode is set to *point* we average
        # over all latitude and longitude coordinates.
        elif mode[:5] == 'point':
            lon0 = 0
            lat0 = 0
            m = 1 / len(data)
            for (lon, lat) in data:
                lon0 += m * lon
                lat0 += m * lat

        # The computationally worst case is the bound mode
        # *polygon* since we need to load the shapefile geometry
        # to compute its center of mass. However, we need
        # to load it anyway and cache the bounding geometry,
        # so this comes at low extra cost.
        elif mode[:4] == 'poly':
            features = self._get_bounding_geometry()
            if len(features) > 0:
                if isinstance(features[0].geom, BaseGeometry):
                    (lon0, lat0) = features[0].geom.representative_point().coords[0]
            else:
                lon0 = 0
                lat0 = 0
        else:
            if verbose:
                sys.stderr.write("unrecognized bound mode", mode)
        return (lon0, lat0)

    def _init_bounds(self):
        """
        ### Initialize bounding polygons and bounding box
        ### Compute the projected bounding box
        """
        from geometry.utils import bbox_to_polygon

        opts = self.options
        proj = self.proj
        mode = opts['bounds']['mode'][:]
        data = opts['bounds']['data']
        if 'padding' not in opts['bounds']:
            padding = 0
        else:
            padding = opts['bounds']['padding']

        # If the bound mode is set to *bbox* we simply project
        # a rectangle in lat/lon coordinates.
        if mode == "bbox":  # catch special case bbox
            sea = proj.bounding_geometry(data, projected=True)
            sbbox = geom_to_bbox(sea)
            sbbox.inflate(sbbox.width * padding)
            return bbox_to_polygon(sbbox)

        bbox = BBox()

        # If the bound mode is set to *points* we project all
        # points and compute the bounding box.
        if mode[:5] == "point":
            ubbox = BBox()
            for lon, lat in data:
                pt = proj.project(lon, lat)
                bbox.update(pt)
                ubbox.update((lon, lat))
            self._unprojected_bounds = ubbox

        # In bound mode *polygons*, which should correctly be
        # named gemetry, we compute the bounding boxes of every
        # geometry.
        if mode[:4] == "poly":
            features = self._get_bounding_geometry()
            ubbox = BBox()
            if len(features) > 0:
                for feature in features:
                    ubbox.join(geom_to_bbox(feature.geometry))
                    feature.project(proj)
                    fbbox = geom_to_bbox(feature.geometry, data["min-area"])
                    bbox.join(fbbox)
                # Save the unprojected bounding box for later to
                # determine what features can be skipped.
                ubbox.inflate(ubbox.width * padding)
                self._unprojected_bounds = ubbox
            else:
                raise KartographError('no features found for calculating the map bounds')
        # If we need some extra geometry around the map bounds, we inflate
        # the bbox according to the set *padding*.
        bbox.inflate(bbox.width * padding)
        # At the end we convert the bounding box to a Polygon because
        # we need it for clipping tasks.
        return bbox_to_polygon(bbox)

    def _get_bounding_geometry(self):
        """
        ### Get bounding geometry
        For bounds mode "*polygons*" this helper function
        returns a list of all geometry that the map should
        be cropped to.
        """
        # Use the cached geometry, if available.
        if self._bounding_geometry_cache:
            return self._bounding_geometry_cache

        opts = self.options
        features = []
        data = opts['bounds']['data']
        id = data['layer']

        # Check that the layer exists.
        if id not in self.layersById:
            raise KartographError('layer not found "%s"' % id)
        layer = self.layersById[id]

        # Construct the filter function of the layer, which specifies
        # what features should be excluded from the map completely.
        if layer.options['filter'] is False:
            layerFilter = lambda a: True
        else:
            layerFilter = lambda rec: filter_record(layer.options['filter'], rec)

        # Construct the filter function of the boundary, which specifies
        # what features should be excluded from the boundary calculation.
        # For instance, you often want to exclude Alaska and Hawaii from
        # the boundary computation of the map, although a part of Alaska
        # might be visible in the resulting map.
        if data['filter']:
            boundsFilter = lambda rec: filter_record(data['filter'], rec)
        else:
            boundsFilter = lambda a: True

        # Combine both filters to a single function.
        filter = lambda rec: layerFilter(rec) and boundsFilter(rec)
        # Load the features from the layer source (e.g. a shapefile).
        features = layer.source.get_features(
            filter=filter,
            min_area=data["min-area"],
            charset=layer.options['charset']
        )

        #if verbose:
            #print 'found %d bounding features' % len(features)

        # Omit tiny islands, if needed.
        if layer.options['filter-islands']:
            features = [f for f in features
                if f.geometry.area > layer.options['filter-islands']]

        # Store computed boundary in cache.
        self._bounding_geometry_cache = features
        return features

    def _get_view(self):
        """
        ### Initialize the view
        """
        # Compute the bounding box of the bounding polygons.
        self.src_bbox = bbox = geom_to_bbox(self.bounds_poly)
        exp = self.options["export"]
        w = exp["width"]
        h = exp["height"]
        ratio = exp["ratio"]

        # Compute ratio from width and height.
        if ratio == "auto":
            ratio = bbox.width / float(bbox.height)

        # Compute width or heights from ratio.
        if h == "auto":
            h = w / ratio
        elif w == "auto":
            w = h * ratio
        return View(bbox, w, h - 1)

    def _init_view_poly(self):
        """
        ### Initialize the output view polygon

        Creates a polygon that represents the rectangular view bounds
        used for cropping the geometries to not overlap the view
        """
        w = self.view.width
        h = self.view.height
        return Polygon([(0, 0), (0, h), (w, h), (w, 0)])

    def _simplify_layers(self):
        """
        ### Simplify geometries
        """
        from simplify import create_point_store, simplify_lines

        # We will use a glocal point cache for all layers. If the
        # same point appears in more than one layer, it will be
        # simplified only once.
        point_store = create_point_store()

        # Compute topology for all layers. That means that every point
        # is checked for duplicates, and eventually replaced with
        # an existing instance.
        for layer in self.layers:
            if layer.options['simplify'] is not False:
                for feature in layer.features:
                    if feature.is_simplifyable():
                        feature.compute_topology(point_store, layer.options['unify-precision'])

        # Now we break features into line segments, which makes them
        # easier to simplify.
        for layer in self.layers:
            if layer.options['simplify'] is not False:
                for feature in layer.features:
                    if feature.is_simplifyable():
                        feature.break_into_lines()

        # Finally, apply the chosen line simplification algorithm.
        total = 0
        kept = 0
        for layer in self.layers:
            if layer.options['simplify'] is not False:
                for feature in layer.features:
                    if feature.is_simplifyable():
                        lines = feature.break_into_lines()
                        lines = simplify_lines(lines, layer.options['simplify']['method'], layer.options['simplify']['tolerance'])
                        for line in lines:
                            total += len(line)
                            for pt in line:
                                if not pt.deleted:
                                    kept += 1
                        # ..and restore the geometries from the simplified line segments.
                        feature.restore_geometry(lines, layer.options['filter-islands'])
        return (total, kept)

    def _crop_layers_to_view(self):
        """
        cuts the layer features to the map view
        """
        for layer in self.layers:
            #out = []
            for feat in layer.features:
                if not feat.geometry.is_valid:
                    pass
                    #print feat.geometry
                    #_plot_geometry(feat.geometry)
                feat.crop_to(self.view_poly)
                #if not feat.is_empty():
                #    out.append(feat)
            #layer.features = out

    def _crop_layers(self):
        """
        handles crop-to
        """
        for layer in self.layers:
            if layer.options['crop-to'] is not False:
                cropped_features = []
                for tocrop in layer.features:
                    cbbox = geom_to_bbox(tocrop.geom)
                    crop_at_layer = layer.options['crop-to']
                    if crop_at_layer not in self.layersById:
                        raise KartographError('you want to substract '
                            + 'from layer "%s" which cannot be found'
                            % crop_at_layer)
                    for crop_at in self.layersById[crop_at_layer].features:
                        # Sometimes a bounding box may not exist, so get it
                        if not hasattr(crop_at.geom,'bbox'):
                            crop_at.geom.bbox = geom_to_bbox(crop_at.geom)
                        if crop_at.geom.bbox.intersects(cbbox):
                            tocrop.crop_to(crop_at.geom)
                            cropped_features.append(tocrop)
                layer.features = cropped_features

    def _subtract_layers(self):
        """
        ### Subtract geometry
        """
        # Substract geometry of a layer from the geometry
        # of one or more different layers. Added mainly
        # for excluding great lakes from country polygons.
        for layer in self.layers:
            if layer.options['subtract-from']:
                for feat in layer.features:
                    if feat.geom is None:
                        continue
                    cbbox = geom_to_bbox(feat.geom)
                    # We remove it from multiple layers, if wanted.
                    for subid in layer.options['subtract-from']:
                        if subid not in self.layersById:
                            raise KartographError('you want to subtract'
                                + ' from layer "%s" which cannot be found'
                                % subid)
                        for s in self.layersById[subid].features:
                            if s.geom and geom_to_bbox(s.geom).intersects(cbbox):
                                s.subtract_geom(feat.geom)
                # Finally, we don't want the subtracted features
                # to be included in our map.
                layer.features = []

    def _join_features(self):
        """
        ### Joins features within a layer.

        Sometimes you want to merge or join multiple features (say polygons) into
        a single feature. Kartograph uses the geometry.union() method of shapely
        to do that.
        """
        from geometry.utils import join_features

        for layer in self.layers:
            if layer.options['join'] is not False:
                unjoined = 0
                join = layer.options['join']
                # The property we want to group the features by.
                groupBy = join['group-by']
                groups = join['groups']
                if groupBy is not False and not groups:
                    # If no groups are defined, we'll create a group for each
                    # unique value of the ``group-by` property.
                    groups = {}
                    for feat in layer.features:
                        fid = feat.props[groupBy]
                        groups[fid] = [fid]

                groupFeatures = {}

                # Group all features into one group if no group-by is set
                if groupBy is False:
                    groupFeatures[layer.id] = []
                    groups = [layer.id]

                res = []
                # Find all features for each group.
                for feat in layer.features:
                    if groupBy is False:
                        groupFeatures[layer.id].append(feat)
                    else:
                        found_in_group = False
                        for g_id in groups:
                            if g_id not in groupFeatures:
                                groupFeatures[g_id] = []
                            if feat.props[groupBy] in groups[g_id] or str(feat.props[groupBy]) in groups[g_id]:
                                groupFeatures[g_id].append(feat)
                                found_in_group = True
                                break
                        if not found_in_group:
                            unjoined += 1
                            res.append(feat)

                for g_id in groups:
                    # Make a copy of the input features properties.
                    props = {}
                    for feat in groupFeatures[g_id]:
                        fprops = feat.props
                        for key in fprops:
                            if key not in props:
                                props[key] = fprops[key]
                            else:
                                if props[key] != fprops[key]:
                                    props[key] = "---"
                    # If ``group-as``was set, we store the group id as
                    # new property.
                    groupAs = join['group-as']
                    if groupAs is not False:
                        props[groupAs] = g_id

                    # group.attributes allows you to keep or define
                    # certain attributes for the joined features
                    #
                    # attributes:
                    #    FIPS_1: code    # use the value of 'code' stored in one of the grouped features
                    #    NAME:           # define values for each group-id
                    #       GO: Gorenjska
                    #       KO: Koroka
                    if 'attributes' in join:
                        attrs = join['attributes']
                        for key in attrs:
                            if key not in layer.options['attributes']:
                                # add key to layer attributes to ensure
                                # that it's being included in SVG
                                layer.options['attributes'].append({'src': key, 'tgt': key})
                            if isinstance(attrs[key], dict):
                                if g_id in attrs[key]:
                                    props[key] = attrs[key][g_id]
                            else:
                                props[key] = groupFeatures[g_id][0].props[attrs[key]]  # use first value

                    # Finally join (union) the feature geometries.
                    if g_id in groupFeatures:
                        if 'buffer' in join:
                            buffer_polygons = join['buffer']
                        else:
                            buffer_polygons = 0
                        res += join_features(groupFeatures[g_id], props, buf=buffer_polygons)

                # Export ids as JSON dict, if requested
                if join['export-ids']:
                    exp = {}
                    for g_id in groups:
                        exp[g_id] = []
                        for feat in groupFeatures[g_id]:
                            exp[g_id].append(feat.props[join['export-ids']])
                    import json
                    print json.dumps(exp)

                layer.features = res

    def compute_map_scale(me):
        """
        computes the width of the map (at the lower boundary) in projection units (typically meters)
        """
        p0 = (0, me.view.height)
        p1 = (me.view.width, p0[1])
        p0 = me.view.project_inverse(p0)
        p1 = me.view.project_inverse(p1)
        from math import sqrt
        dist = sqrt((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2)
        return dist / me.view.width

    def scale_bar_width(me):
        from math import log
        scale = me.compute_map_scale()
        w = (me.view.width * 0.2) * scale
        exp = int(log(w, 10))
        nice_w = round(w, -exp)
        bar_w = nice_w / scale
        return (nice_w, bar_w)

########NEW FILE########
__FILENAME__ = maplayer

from layersource import handle_layer_source
from filter import filter_record


_verbose = False


class MapLayer(object):

    """
    MapLayer
    --------

    Represents a layer in the map which contains a list of map features
    """

    def __init__(self, id, options, _map, cache):
        # Store layer properties as instance properties
        self.id = id
        self.options = options
        self.map = _map
        self.cache = cache
        if 'class' not in options:
            self.classes = []
        elif isinstance(options['class'], basestring):
            self.classes = options['class'].split(' ')
        elif isinstance(options['class'], list):
            self.classes = options['class']
        # Make sure that the layer id is unique within the map.
        while self.id in self.map.layersById:
            self.id += "_"
        # Instantiate the layer source which will generate features from the source
        # geo data such as shapefiles or virtual sources such as graticule lines.
        self.source = handle_layer_source(self.options, self.cache)

    def get_features(layer, filter=False, min_area=0):
        """
        ### get_features()
        Returns a list of projected and filtered features of a layer.
        """
        opts = layer.map.options
        is_projected = False

        # Let's see if theres a better bounding box than this..
        bbox = [-180, -90, 180, 90]

        # Use the clipping mode defined in the map configuration
        if opts['bounds']['mode'] == "bbox":
            bbox = opts['bounds']['data']
        # The 'crop' property overrides the clipping settings
        if 'crop' in opts['bounds'] and opts['bounds']['crop']:
            # If crop is set to "auto", which is the default behaviour, Kartograph
            # will use the actual bounding geometry to compute the bounding box
            if opts['bounds']['crop'] == "auto":
                if layer.map._unprojected_bounds:
                    bbox = layer.map._unprojected_bounds
                    bbox.inflate(inflate=opts['bounds']['padding'] * 2)
                elif _verbose:
                    pass
                    #print 'could not compute bounding box for auto-cropping'
            else:
                # otherwise it will use the user defined bbox in the format
                # [minLon, minLat, maxLon, maxLat]
                bbox = opts['bounds']['crop']

        # If the layer has the "src" property, it is a **regular map layer** source, which
        # means that there's an exernal file that we load the geometry and meta data from.
        if 'src' in layer.options:
            if layer.options['filter'] is False:
                filter = None
            else:
                filter = lambda rec: filter_record(layer.options['filter'], rec)

            # Now we ask the layer source to generate the features that will be displayed
            # in the map.
            features = layer.source.get_features(
                filter=filter,
                bbox=bbox,
                ignore_holes='ignore-holes' in layer.options and layer.options['ignore-holes'],
                charset=layer.options['charset']
            )
            if _verbose:
                #print 'loaded %d features from shapefile %s' % (len(features), layer.options['src'])
                pass

        # In contrast to regular layers, the geometry for **special (or virtual) layers** is generated
        # by Kartograph itself, based on some properties defined in the layer config.
        elif 'special' in layer.options:
            # The graticule layer generates line features for longitudes and latitudes
            if layer.options['special'] == "graticule":
                lats = layer.options['latitudes']
                lons = layer.options['longitudes']
                features = layer.source.get_features(lats, lons, layer.map.proj, bbox=bbox)

            # The "sea" layer generates a MultiPolygon that represents the entire boundary
            # of the map. Especially useful for non-cylindrical map projections.
            elif layer.options['special'] == "sea":
                features = layer.source.get_features(layer.map.proj)
                is_projected = True

        for feature in features:
            # If the features are not projected yet, we project them now.
            if not is_projected:
                feature.project(layer.map.proj)
            # Transform features to view coordinates.
            feature.project_view(layer.map.view)

        # Remove features that don't intersect our clipping polygon
        if layer.map.view_poly:
            features = [feature for feature in features
            if feature.geometry and feature.geometry.intersects(layer.map.view_poly)]
        layer.features = features

########NEW FILE########
__FILENAME__ = mapstyle

import tinycss


class MapStyle(object):

    def __init__(self, css):
        if css:
            parser = tinycss.make_parser()
            self.css = parser.parse_stylesheet(css)
        else:
            self.css = None

    def getStyle(self, layer_id, layer_classes=[], fprops=dict()):
        """
        Returns a dictionary of style rules for a given feature.
        """
        if self.css is None:
            return {}
        attrs = dict()
        for rule in self.css.rules:
            # Find out whether this rule matches
            if _checkRule(layer_id, layer_classes, fprops, rule):
                for decl in rule.declarations:
                    prop = ''
                    for val in decl.value:
                        if val.type == 'INTEGER':
                            prop += str(val.value)
                        elif val.type == 'DIMENSION':
                            prop += str(val.value) + val.unit
                        else:
                            prop += str(val.value)
                    attrs[decl.name] = prop
        return attrs

    def applyStyle(self, node, layer_id, layer_classes=[], fprops=dict()):
        style = self.getStyle(layer_id, layer_classes, fprops)
        for key in style:
            node.setAttribute(key, style[key])
        return style

    def applyFeatureStyle(self, node, layer_id, layer_classes, fprops=dict()):
        layer_style = self.getStyle(layer_id, layer_classes)
        feat_style = self.getStyle(layer_id, layer_classes, fprops)
        feat_style = style_diff(feat_style, layer_style)
        for key in feat_style:
            node.setAttribute(key, feat_style[key])


def _checkRule(layer_id, layer_classes, fprops, rule):
    parts = [[]]
    k = 0
    for sel in rule.selector:
        if sel.type == 'S':
            # Ignore white spaces
            continue
        if sel.type == 'DELIM' and sel.value == ',':
            # Proceed to next rule
            k += 1
            parts.append([])
            continue
        parts[k].append(sel)

    for p in parts:
        if len(p) > 0:
            o = _checkIdAndClass(p, layer_id, layer_classes)
            if o > 0:
                if len(p) == 1:
                    return True
                else:
                    match = True
                    for r in p[o:]:
                        if r.type == '[' and r.content[0].type == 'IDENT' and r.content[len(r.content) - 1].type in ('IDENT', 'INTEGER'):
                            key = r.content[0].value
                            val = r.content[len(r.content) - 1].value
                            comp = ''
                            for c in r.content[1:len(r.content) - 1]:
                                if c.type == 'DELIM':
                                    comp += c.value
                                else:
                                    raise ValueError('problem while parsing map stylesheet at ' + rule.selector.as_css())
                            if key not in fprops:
                                match = False
                            else:
                                if comp == '=':
                                    match = match and fprops[key] == val
                                elif comp == '~=':
                                    vals = val.split(' ')
                                    match = match and fprops[key] in vals
                                elif comp == '|=':
                                    # Matches if the attribute begins with the value
                                    # Note that this is a slightly different interpretation than
                                    # the one used in the CSS specs, since we don't require the '-'
                                    match = match and fprops[key][:len(val)] == val
                                elif comp == '=|':
                                    # Matches if the attribute ends with the value
                                    match = match and fprops[key][-len(val):] == val
                                elif comp == '>':
                                    match = match and fprops[key] > val
                                elif comp == '>=':
                                    match = match and fprops[key] >= val
                                elif comp == '<':
                                    match = match and fprops[key] < val
                                elif comp == '<=':
                                    match = match and fprops[key] <= val
                        else:
                            # print r
                            match = False
                    if match is True:
                        return True


def _checkIdAndClass(part, layer_id, layer_classes):
    """
    checks wether the part of a css rule matches a given layer id
    and/or a list of classes
    """
    # Match layer id
    if part[0].type == 'HASH' and part[0].value[1:] == layer_id:
        return 1
    # Match wildcard *
    if part[0].type == 'DELIM' and part[0].value == '*':
        return 1
    # Match class name
    if part[0].type == 'DELIM' and part[0].value == '.':
        # We only test the first class, so .foo.bar would match
        # any layer with the class 'foo' regardless of it also has
        # the class 'bar'
        if part[1].type == 'IDENT' and part[1].value in layer_classes:
            return 2
    return 0


def style_diff(d1, d2):
    res = dict()
    for key in d1:
        if key not in d2 or d2[key] != d1[key]:
            res[key] = d1[key]
    return res


def remove_unit(val):
    units = ('px', 'pt')
    if val is None or val == '':
        return None
    for unit in units:
        if val[-len(unit):] == unit:
            return float(val[:-len(unit)])
    return val


if __name__ == "__main__":
    css = '''
/*
 * map styles for berlin map
 */

#industry, #urban-1 , #urban-2 {
    opacity: 0.0156863;
    stroke: none;
    fill: #c8c3c3;
}

#lakes, #rivers {
    opacity: 0.4;
    stroke: none;
    fill: #15aee5;
}

#roads-bg {
    fill: none;
    stroke: #fff;
}

#roads {
    fill: none;
    stroke: #e5e1e1;
}

#roads[highway=motorway][administrative=4],
#roads [highway|=motorway] {
    stroke-width: 3pt;
    stroke-dasharray: 3,4,5;
    border: 1px solid #ccc;
}

*[highway=primary] {
    stroke-width: 4px;
}

'''
    mapstyle = MapStyle(css)
    layer_css = mapstyle.getStyle('roads')
    full_css = mapstyle.getStyle('roads', dict(highway='motorway_link'))

########NEW FILE########
__FILENAME__ = options

"""
API 2.0
helper methods for validating options dictionary
"""

import os.path
import proj
import errors
import sys

Error = errors.KartographError

try:
    # included in standard lib from Python 2.7
    from collections import OrderedDict
except ImportError:
    # try importing the backported drop-in replacement
    # it's available on PyPI
    from ordereddict import OrderedDict


def is_str(s):
    return isinstance(s, (str, unicode))


def read_map_config(f):
    content = f.read()
    ext = os.path.splitext(f.name)[1].lower()

    if ext == '.json':
        import json
        try:
            cfg = json.loads(content, object_pairs_hook=OrderedDict)
        except Exception:
            sys.stderr.write('Error: parsing of JSON configuration failed.\n\n')
            sys.stderr.write('Please check your JSON syntax (e.g. via http://jsonlint.com/).\n')
            exit(-1)
        else:
            return cfg
    elif ext in ('.yaml', '.yml'):
        import yaml
        from yaml_ordered_dict import OrderedDictYAMLLoader
        try:
            cfg = yaml.load(content, OrderedDictYAMLLoader)
        except Exception:
            sys.stderr.write('Error: parsing of YAML configuration failed.\n\n')
            sys.stderr.write('Please check your YAML syntax (e.g. via http://yamllint.com/).\n')
            sys.stderr.write('Check that you\'re using spaces for indentation as tabs are not allowed in YAML.\n')
            exit(-1)
        else:
            return cfg
    else:
        raise Error('supported config formats are .json and .yaml')


def parse_options(opts):
    """
    check out that the option dict is filled correctly
    """
    # projection
    parse_proj(opts)
    parse_layers(opts)
    parse_bounds(opts)
    parse_export(opts)


def parse_proj(opts):
    """
    checks projections
    """
    if 'proj' not in opts:
        opts['proj'] = {}
    prj = opts['proj']
    if 'id' not in prj:
        if 'bounds' not in opts:
            prj['id'] = 'robinson'
        else:
            prj['id'] = 'laea'
    if prj['id'] not in proj.projections:
        raise Error('unknown projection')
    prjClass = proj.projections[prj['id']]
    for attr in prjClass.attributes():
        if attr not in prj:
            prj[attr] = "auto"
        else:
            if prj[attr] != "auto":
                prj[attr] = prj[attr]


def parse_layers(opts):
    if 'layers' not in opts:
        opts['layers'] = []
    l_id = 0
    g_id = 0
    s_id = 0
    layers = []
    if isinstance(opts['layers'], list):
        for layer in opts['layers']:
            layers.append(layer)
    elif isinstance(opts['layers'], (dict, OrderedDict)):
        for layer_id in opts['layers']:
            layer = opts['layers'][layer_id]
            layer['id'] = layer_id
            layers.append(layer)
    opts['layers'] = layers

    for layer in opts['layers']:
        if 'render' not in layer:
            layer['render'] = True
        if 'src' not in layer and 'special' not in layer:
            raise Error('you need to define the source for your layers')
        if 'src' in layer:
            # We must not check if the file exists, since
            # we might deal with a database connection
            #if not os.path.exists(layer['src']):
            #    raise Error('layer source not found: ' + layer['src'])
            if 'id' not in layer:
                layer['id'] = 'layer_' + str(l_id)
                l_id += 1
            if 'charset' not in layer:
                layer['charset'] = 'utf-8'
        elif 'special' in layer:
            if layer['special'] == 'graticule':
                if 'id' not in layer:
                    layer['id'] = 'graticule'
                    if g_id > 0:
                        layer['id'] += '_' + str(g_id)
                    g_id += 1
                parse_layer_graticule(layer)
            elif layer['special'] == 'sea':
                if 'id' not in layer:
                    layer['id'] = 'sea'
                    if s_id > 0:
                        layer['id'] += '_' + str(s_id)
                    s_id += 1

        parse_layer_attributes(layer)
        parse_layer_labeling(layer)
        parse_layer_filter(layer)
        parse_layer_join(layer)
        parse_layer_simplify(layer)
        parse_layer_subtract(layer)
        parse_layer_cropping(layer)


def parse_layer_attributes(layer):
    if 'attributes' not in layer:
        layer['attributes'] = []
        return
    if layer['attributes'] == 'all':
        return
    attrs = []
    for attr in layer['attributes']:
        if is_str(attr):
            if isinstance(layer['attributes'], list):  # ["ISO_A3", "FIPS"]
                attrs.append({'src': attr, 'tgt': attr})
            elif isinstance(layer['attributes'], dict):  # { "iso": "ISO_A3" }
                attrs.append({'src': layer['attributes'][attr], 'tgt': attr})
        elif isinstance(attr, dict) and 'src' in attr and 'tgt' in attr:
            attrs.append(attr)
    layer['attributes'] = attrs


def parse_layer_labeling(layer):
    if 'labeling' not in layer:
        layer['labeling'] = False
        return
    lbl = layer['labeling']
    if 'position' not in lbl:
        lbl['position'] = 'centroid'
    if 'buffer' not in lbl:
        lbl['buffer'] = False
    if 'key' not in lbl:
        lbl['key'] = False


def parse_layer_filter(layer):
    if 'filter' not in layer:
        layer['filter'] = False
        return
    return  # todo: check valid filter syntax (recursivly, place code in filter.py)
    filter = layer['filter']
    if 'type' not in filter:
        filter['type'] = 'include'
    if 'attribute' not in filter:
        raise Error('layer filter must define an attribute to filter on')
    if 'equals' in filter:
        if isinstance(filter['equals'], (str, unicode, int, float)):
            filter['equals'] = [filter['equals']]
    elif 'greater-than' in filter:
        try:
            filter['greater-than'] = float(filter['greater-than'])
        except ValueError:
            raise Error('could not convert filter value "greater-than" to float')
    elif 'less-than' in filter:
        try:
            filter['less-than'] = float(filter['less-than'])
        except ValueError:
            raise Error('could not convert filter value "less-than" to float')
    else:
        raise Error('you must define either "equals", "greater-than" or "less-than" in the filter')


def parse_layer_join(layer):
    if 'join' not in layer:
        layer['join'] = False
        return
    if layer['join'] is False:
        return

    join = layer['join']
    if isinstance(join, bool):
        join = layer['join'] = {}
    if 'group-by' not in join:
        join['group-by'] = False
    if 'groups' not in join:
        join['groups'] = None
    if 'group-as' not in join:
        join['group-as'] = False
    if 'export-ids' not in join:
        join['export-ids'] = False


def parse_layer_simplify(layer):
    if 'filter-islands' not in layer:
        layer['filter-islands'] = False
    if 'unify-precision' not in layer:
        layer['unify-precision'] = None
    if 'simplify' not in layer:
        layer['simplify'] = False
        return
    if layer['simplify'] is False:
        return
    if isinstance(layer['simplify'], (int, float, str, unicode)):
        # default to visvalingam-whyatt
        layer['simplify'] = {"method": "visvalingam-whyatt", "tolerance": float(layer['simplify'])}
    try:
        layer['simplify']['tolerance'] = float(layer['simplify']['tolerance'])
    except ValueError:
        raise Error('could not convert simplification amount to float')


def parse_layer_subtract(layer):
    if 'subtract-from' not in layer:
        layer['subtract-from'] = False
        return
    if isinstance(layer['subtract-from'], (str, unicode)):
        layer['subtract-from'] = [layer['subtract-from']]


def parse_layer_cropping(layer):
    if 'crop-to' not in layer:
        layer['crop-to'] = False
        return


def parse_layer_graticule(layer):
    if 'latitudes' not in layer:
        layer['latitudes'] = []
    elif isinstance(layer['latitudes'], (int, float)):
        step = layer['latitudes']
        layer['latitudes'] = [0]
        for lat in _xfrange(step, 90, step):
            layer['latitudes'] += [lat, -lat]

    if 'longitudes' not in layer:
        layer['longitudes'] = []
    elif isinstance(layer['longitudes'], (int, float)):
        step = layer['longitudes']
        layer['longitudes'] = [0]
        for lon in _xfrange(step, 181, step):
            if lon == 180:
                p = [lon]
            else:
                p = [lon, -lon]
            layer['longitudes'] += p


def _xfrange(start, stop, step):
    while (step > 0 and start < stop) or (step < 0 and start > step):
        yield start
        start += step


def parse_bounds(opts):
    if 'bounds' not in opts:
        opts['bounds'] = {}
        #return
    bounds = opts['bounds']
    if 'mode' not in bounds:
        bounds['mode'] = 'polygons'

    if 'data' not in bounds:
        bounds['data'] = {}

    mode = bounds['mode']
    data = bounds['data']

    if 'crop' not in bounds:
        bounds['crop'] = 'auto'

    if "padding" not in bounds:
        bounds["padding"] = 0

    if mode == "bbox":
        try:
            if len(data) == 4:
                for i in range(0, 4):
                    data[i] = float(data[i])
            else:
                raise Error('bounds mode bbox requires array with exactly 4 values [lon0,lat0,lon1,lat]')
        except Error:
            raise
        except:
            raise Error('bounds mode bbox requires array with exactly 4 values [lon0,lat0,lon1,lat]')
    elif mode == "points":
        try:
            for i in range(0, len(data)):
                pt = data[i]
                if len(pt) == 2:
                    pt = map(float, pt)
                else:
                    raise Error('bounds mode points requires array with (lon,lat) tuples')
        except Error:
            raise
        except:
            raise Error('bounds mode points requires array with (lon,lat) tuples')
    elif mode[:4] == 'poly':
        bounds['mode'] = mode = "polygons"
        if "layer" not in data or not is_str(data["layer"]):
            # using the first layer for bound
            data["layer"] = opts['layers'][0]['id']
            # raise Error('you must specify a layer for bounds mode ' + mode)
        if "filter" not in data:
            data["filter"] = False
        if "attribute" not in data or not is_str(data["attribute"]):
            data["attribute"] = None
        if "values" not in data:
            if data["attribute"] is None:
                data["values"] = None
            else:
                raise Error('you must specify a list of values to match in bounds mode ' + mode)
        if is_str(data["values"]):
            data["values"] = [data["values"]]
        if "min-area" in data:
            try:
                data["min-area"] = float(data["min-area"])
            except:
                raise Error('min_area must be an integer or float')
        else:
            data['min-area'] = 0


def parse_export(opts):
    if "export" not in opts:
        opts["export"] = {}
    exp = opts["export"]
    if "width" not in exp and "height" not in exp:
        exp["width"] = 1000
        exp["height"] = "auto"
    elif "height" not in exp:
        exp["height"] = "auto"
    elif "width" not in exp:
        exp["width"] = "auto"

    if "ratio" not in exp:
        exp["ratio"] = "auto"
    if "round" not in exp:
        exp["round"] = False
    else:
        exp["round"] = int(exp["round"])
    if "crop-to-view" not in exp:
        exp['crop-to-view'] = True
    if "scalebar" not in exp:
        exp['scalebar'] = False
    elif exp['scalebar'] is True:
        exp['scalebar'] = dict()

    if 'prettyprint' not in exp:
        exp['prettyprint'] = False

########NEW FILE########
__FILENAME__ = azimuthal
"""
    kartograph - a svg mapping library
    Copyright (C) 2011,2012  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import math
from kartograph.proj.base import Proj


class Azimuthal(Proj):

    def __init__(self, lat0=0.0, lon0=0.0, rad=1000):
        self.lat0 = lat0
        self.phi0 = math.radians(lat0)
        self.lon0 = lon0
        self.lam0 = math.radians(lon0)
        self.r = rad
        self.elevation0 = self.to_elevation(lat0)
        self.azimuth0 = self.to_azimuth(lon0)

    def to_elevation(self, latitude):
        return ((latitude + 90.0) / 180.0) * math.pi - math.pi / 2.0

    def to_azimuth(self, longitude):
        return ((longitude + 180.0) / 360.0) * math.pi * 2 - math.pi

    def _visible(self, lon, lat):
        elevation = self.to_elevation(lat)
        azimuth = self.to_azimuth(lon)
        # work out if the point is visible
        cosc = math.sin(elevation) * math.sin(self.elevation0) + math.cos(self.elevation0) * math.cos(elevation) * math.cos(azimuth - self.azimuth0)
        return cosc >= 0.0

    def _truncate(self, x, y):
        theta = math.atan2(y - self.r, x - self.r)
        x1 = self.r + self.r * math.cos(theta)
        y1 = self.r + self.r * math.sin(theta)
        return (x1, y1)

    def world_bounds(self, bbox, llbbox=(-180, -90, 180, 90)):
        if llbbox == (-180, -90, 180, 90):
            d = self.r * 4
            bbox.update((0, 0))
            bbox.update((d, d))
        else:
            bbox = super(Azimuthal, self).world_bounds(bbox, llbbox)
        return bbox

    def sea_shape(self, llbbox=(-180, -90, 180, 90)):
        out = []
        if llbbox == (-180, -90, 180, 90) or llbbox == [-180, -90, 180, 90]:
            print "-> full extend"
            for phi in range(0, 360):
                x = self.r + math.cos(math.radians(phi)) * self.r
                y = self.r + math.sin(math.radians(phi)) * self.r
                out.append((x, y))
            out = [out]
        else:
            out = super(Azimuthal, self).sea_shape(llbbox)
        return out

    def attrs(self):
        p = super(Azimuthal, self).attrs()
        p['lon0'] = self.lon0
        p['lat0'] = self.lat0
        return p

    def __str__(self):
        return 'Proj(' + self.name + ', lon0=%s, lat0=%s)' % (self.lon0, self.lat0)

    @staticmethod
    def attributes():
        return ['lon0', 'lat0']

########NEW FILE########
__FILENAME__ = equi
"""
    kartograph - a svg mapping library
    Copyright (C) 2011,2012  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from azimuthal import Azimuthal
import math


class EquidistantAzimuthal(Azimuthal):
    """
    Equidistant Azimuthal projection

    implementation taken from
    Snyder, Map projections - A working manual
    """
    def __init__(self, lat0=0.0, lon0=0.0):
        Azimuthal.__init__(self, lat0, lon0)

    def project(self, lon, lat):
        from math import radians as rad, cos, sin

        phi = rad(lat)
        lam = rad(lon)

        cos_c = sin(self.phi0) * sin(phi) + cos(self.phi0) * cos(phi) * cos(lam - self.lam0)
        c = math.acos(cos_c)
        sin_c = sin(c)
        if sin_c == 0:
            k = 1
        else:
            k = 0.325 * c / sin(c)

        xo = self.r * k * cos(phi) * sin(lam - self.lam0)
        yo = -self.r * k * (cos(self.phi0) * sin(phi) - sin(self.phi0) * cos(phi) * cos(lam - self.lam0))

        x = self.r + xo
        y = self.r + yo

        return (x, y)

    def _visible(self, lon, lat):
        return True

########NEW FILE########
__FILENAME__ = laea
"""
    kartograph - a svg mapping library
    Copyright (C) 2011,2012  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from azimuthal import Azimuthal
import math
import pyproj


class LAEA(Azimuthal):
    """
    Lambert Azimuthal Equal-Area Projection

    implementation taken from
    Snyder, Map projections - A working manual
    """
    def __init__(self, lon0=0.0, lat0=0.0):
        self.scale = math.sqrt(2) * 0.5
        Azimuthal.__init__(self, lat0, lon0)

    def project(self, lon, lat):
        # old projection code
        from math import radians as rad, pow, cos, sin
        # lon,lat = self.ll(lon, lat)
        phi = rad(lat)
        lam = rad(lon)

        if abs(lon - self.lon0) == 180:
            xo = self.r * 2
            yo = 0
        else:
            k = pow(2 / (1 + sin(self.phi0) * sin(phi) + cos(self.phi0) * cos(phi) * cos(lam - self.lam0)), .5)
            k *= self.scale  # .70738033

            xo = self.r * k * cos(phi) * sin(lam - self.lam0)
            yo = -self.r * k * (cos(self.phi0) * sin(phi) - sin(self.phi0) * cos(phi) * cos(lam - self.lam0))

        x = self.r + xo
        y = self.r + yo

        return (x, y)


class LAEA_Alaska(LAEA):
    def __init__(self, lon0=0, lat0=0):
        self.scale = math.sqrt(2) * 0.5 * 0.33
        Azimuthal.__init__(self, 90, -150)

class LAEA_Hawaii(LAEA):
    def __init__(self, lon0=0, lat0=0):
        self.scale = math.sqrt(2) * 0.5
        Azimuthal.__init__(self, 20, -157)


class LAEA_USA(LAEA):

    def __init__(self, lon0=0.0, lat0=0.0):
        self.scale = math.sqrt(2) * 0.5
        Azimuthal.__init__(self, 45, -100)
        self.LAEA_Alaska = LAEA_Alaska()
        self.LAEA_Hawaii = LAEA_Hawaii()

    def project(self, lon, lat):
        alaska = lat > 44 and (lon < -127 or lon > 170)
        hawaii = lon < -127 and lat < 44

        if alaska:
            if lon > 170:
                lon -= 380
            x,y = self.LAEA_Alaska.project(lon, lat)
        elif hawaii:
            x,y = self.LAEA_Hawaii.project(lon, lat)
        else:
            x,y = LAEA.project(self, lon, lat)

        if alaska:
            x += -180
            y += 100
        if hawaii:
            y += 220
            x += -80
        return (x,y)


class P4_LAEA(Azimuthal):
    """
    Lambert Azimuthal Equal-Area Projection

    implementation taken from
    Snyder, Map projections - A working manual
    """
    def __init__(self, lon0=0.0, lat0=0.0):
        self.scale = math.sqrt(2) * 0.5
        self.proj = pyproj.Proj(proj='laea', lat_0=lat0, lon_0=lon0)
        Azimuthal.__init__(self, lat0, lon0)

    def project(self, lon, lat):
        return self.proj(lon, lat)

    def project_inverse(self, x, y):
        return self.proj(x, y, inverse=True)


########NEW FILE########
__FILENAME__ = ortho
"""
    kartograph - a svg mapping library
    Copyright (C) 2011,2012  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from azimuthal import Azimuthal
import math


class Orthographic(Azimuthal):
    """
    Orthographic Azimuthal Projection

    implementation taken from http://www.mccarroll.net/snippets/svgworld/
    """
    def __init__(self, lat0=0, lon0=0):
        self.r = 1000
        Azimuthal.__init__(self, lat0, lon0)

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        elevation = self.to_elevation(lat)
        azimuth = self.to_azimuth(lon)
        xo = self.r * math.cos(elevation) * math.sin(azimuth - self.azimuth0)
        yo = -self.r * (math.cos(self.elevation0) * math.sin(elevation) - math.sin(self.elevation0) * math.cos(elevation) * math.cos(azimuth - self.azimuth0))
        x = self.r + xo
        y = self.r + yo
        return (x, y)

########NEW FILE########
__FILENAME__ = satellite
"""
    kartograph - a svg mapping library
    Copyright (C) 2011,2012  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from azimuthal import Azimuthal
import math


class Satellite(Azimuthal):
    """
    General perspective projection, aka Satellite projection

    implementation taken from
    Snyder, Map projections - A working manual

    up .. angle the camera is turned away from north (clockwise)
    tilt .. angle the camera is tilted
    """
    def __init__(self, lat0=0.0, lon0=0.0, dist=1.6, up=0, tilt=0):
        import sys
        Azimuthal.__init__(self, 0, 0)

        self.dist = dist
        self.up = up
        self.up_ = math.radians(up)
        self.tilt = tilt
        self.tilt_ = math.radians(tilt)

        self.scale = 1
        xmin = sys.maxint
        xmax = sys.maxint * -1
        for lat in range(0, 180):
            for lon in range(0, 361):
                x, y = self.project(lon - 180, lat - 90)
                xmin = min(x, xmin)
                xmax = max(x, xmax)
        self.scale = (self.r * 2) / (xmax - xmin)

        Azimuthal.__init__(self, lat0, lon0)

    def project(self, lon, lat):
        from math import radians as rad, cos, sin
        lon, lat = self.ll(lon, lat)
        phi = rad(lat)
        lam = rad(lon)

        cos_c = sin(self.phi0) * sin(phi) + cos(self.phi0) * cos(phi) * cos(lam - self.lam0)
        k = (self.dist - 1) / (self.dist - cos_c)
        k = (self.dist - 1) / (self.dist - cos_c)

        k *= self.scale

        xo = self.r * k * cos(phi) * sin(lam - self.lam0)
        yo = -self.r * k * (cos(self.phi0) * sin(phi) - sin(self.phi0) * cos(phi) * cos(lam - self.lam0))

        # rotate
        tilt = self.tilt_

        cos_up = cos(self.up_)
        sin_up = sin(self.up_)
        cos_tilt = cos(tilt)
        # sin_tilt = sin(tilt)

        H = self.r * (self.dist - 1)
        A = ((yo * cos_up + xo * sin_up) * sin(tilt / H)) + cos_tilt
        xt = (xo * cos_up - yo * sin_up) * cos(tilt / A)
        yt = (yo * cos_up + xo * sin_up) / A

        x = self.r + xt
        y = self.r + yt

        return (x, y)

    def _visible(self, lon, lat):
        elevation = self.to_elevation(lat)
        azimuth = self.to_azimuth(lon)
        # work out if the point is visible
        cosc = math.sin(elevation) * math.sin(self.elevation0) + math.cos(self.elevation0) * math.cos(elevation) * math.cos(azimuth - self.azimuth0)
        return cosc >= (1.0 / self.dist)

    def attrs(self):
        p = super(Satellite, self).attrs()
        p['dist'] = self.dist
        p['up'] = self.up
        p['tilt'] = self.tilt
        return p

    def _truncate(self, x, y):
        theta = math.atan2(y - self.r, x - self.r)
        x1 = self.r + self.r * math.cos(theta)
        y1 = self.r + self.r * math.sin(theta)
        return (x1, y1)

########NEW FILE########
__FILENAME__ = stereo
"""
    kartograph - a svg mapping library
    Copyright (C) 2011,2012  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from azimuthal import Azimuthal


class Stereographic(Azimuthal):
    """
    Stereographic projection

    implementation taken from
    Snyder, Map projections - A working manual
    """
    def __init__(self, lat0=0.0, lon0=0.0):
        Azimuthal.__init__(self, lat0, lon0)

    def project(self, lon, lat):
        from math import radians as rad, cos, sin
        lon, lat = self.ll(lon, lat)
        phi = rad(lat)
        lam = rad(lon)

        k0 = 0.5
        k = 2 * k0 / (1 + sin(self.phi0) * sin(phi) + cos(self.phi0) * cos(phi) * cos(lam - self.lam0))

        xo = self.r * k * cos(phi) * sin(lam - self.lam0)
        yo = -self.r * k * (cos(self.phi0) * sin(phi) - sin(self.phi0) * cos(phi) * cos(lam - self.lam0))

        x = self.r + xo
        y = self.r + yo

        return (x, y)

########NEW FILE########
__FILENAME__ = base
"""
    kartograph - a svg mapping library
    Copyright (C) 2011  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import math
from kartograph.errors import KartographError
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, MultiLineString, MultiPoint


class Proj(object):
    """
    base class for projections
    """
    HALFPI = math.pi * .5
    QUARTERPI = math.pi * .25

    minLat = -90
    maxLat = 90
    minLon = -180
    maxLon = 180

    def _shift_polygon(self, polygon):
        return [polygon]  # no shifting

    def plot(self, geometry):
        geometries = hasattr(geometry, 'geoms') and geometry.geoms or [geometry]
        res = []

        # at first shift polygons
        #shifted = []
        #for geom in geometries:
        #    if isinstance(geom, Polygon):
        #        shifted += self._shift_polygon(geom)
        #    else:
        #        shifted += [geom]

        for geom in geometries:
            if isinstance(geom, Polygon):
                res += self.plot_polygon(geom)
            elif isinstance(geom, LineString):
                rings = self.plot_linear_ring(geom)
                res += map(LineString, rings)
            elif isinstance(geom, Point):
                if self._visible(geom.x, geom.y):
                    x, y = self.project(geom.x, geom.y)
                    res.append(Point(x, y))
            else:
                pass
                # raise KartographError('proj.plot(): unknown geometry type %s' % geom)

        if len(res) > 0:
            if isinstance(res[0], Polygon):
                if len(res) > 1:
                    return MultiPolygon(res)
                else:
                    return res[0]
            elif isinstance(res[0], LineString):
                if len(res) > 1:
                    return MultiLineString(res)
                else:
                    return LineString(res[0])
            else:
                if len(res) > 1:
                    return MultiPoint(res)
                else:
                    return Point(res[0].x, res[0].y)

    def plot_polygon(self, polygon):
        ext = self.plot_linear_ring(polygon.exterior, truncate=True)
        if len(ext) == 1:
            pts_int = []
            for interior in polygon.interiors:
                pts_int += self.plot_linear_ring(interior, truncate=True)
            return [Polygon(ext[0], pts_int)]
        elif len(ext) == 0:
            return []
        else:
            raise KartographError('unhandled case: exterior is split into multiple rings')

    def plot_linear_ring(self, ring, truncate=False):
        ignore = True
        points = []
        for (lon, lat) in ring.coords:
            vis = self._visible(lon, lat)
            if vis:
                ignore = False
            x, y = self.project(lon, lat)
            if not vis and truncate:
                points.append(self._truncate(x, y))
            else:
                points.append((x, y))
        if ignore:
            return []
        return [points]

    def ll(self, lon, lat):
        return (lon, lat)

    def project(self, lon, lat):
        assert False, 'Proj is an abstract class'

    def project_inverse(self, x, y):
        assert False, 'inverse projection is not supporte by %s' % self.name

    def _visible(self, lon, lat):
        assert False, 'Proj is an abstract class'

    def _truncate(self, x, y):
        assert False, 'truncation is not implemented'

    def world_bounds(self, bbox, llbbox=(-180, -90, 180, 90)):
        sea = self.sea_shape(llbbox)
        for x, y in sea[0]:
            bbox.update((x, y))
        return bbox

    def bounding_geometry(self, llbbox=(-180, -90, 180, 90), projected=False):
        """
        returns a WGS84 polygon that represents the limits of this projection
        points that lie outside this polygon will not be plotted
        this polygon will also be used to render the sea layer in world maps

        defaults to full WGS84 range
        """
        from shapely.geometry import Polygon
        sea = []

        minLon = llbbox[0]
        maxLon = llbbox[2]
        minLat = max(self.minLat, llbbox[1])
        maxLat = min(self.maxLat, llbbox[3])

        def xfrange(start, stop, step):
            if stop > start:
                while start < stop:
                    yield start
                    start += step
            else:
                while stop < start:
                    yield start
                    start -= step

        lat_step = abs((maxLat - minLat) / 180.0)
        lon_step = abs((maxLon - minLon) / 360.0)

        for lat in xfrange(minLat, maxLat, lat_step):
            sea.append((minLon, lat))
        for lon in xfrange(minLon, maxLon, lon_step):
            sea.append((lon, maxLat))
        for lat in xfrange(maxLat, minLat, lat_step):
            sea.append((maxLon, lat))
        for lon in xfrange(maxLon, minLon, lon_step):
            sea.append((lon, minLat))

        if projected:
            sea = [self.project(lon, lat) for (lon, lat) in sea]

        return Polygon(sea)

    def __str__(self):
        return 'Proj(' + self.name + ')'

    def attrs(self):
        return dict(id=self.name)

    @staticmethod
    def attributes():
        """
        returns array of attribute names of this projection
        """
        return []

    @staticmethod
    def fromXML(xml, projections):
        id = xml['id']
        if id in projections:
            ProjClass = projections[id]
            args = {}
            for (prop, val) in xml:
                if prop[0] != "id":
                    args[prop[0]] = float(val)
            return ProjClass(**args)
        raise Exception("could not restore projection from xml")

########NEW FILE########
__FILENAME__ = conic
"""
    kartograph - a svg mapping library
    Copyright (C) 2011  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


from base import Proj
import math
from math import radians as rad


class Conic(Proj):

    def __init__(self, lat0=0, lon0=0, lat1=0, lat2=0):
        self.lat0 = lat0
        self.phi0 = rad(lat0)
        self.lon0 = lon0
        self.lam0 = rad(lon0)
        self.lat1 = lat1
        self.phi1 = rad(lat1)
        self.lat2 = lat2
        self.phi2 = rad(lat2)

        if lon0 != 0.0:
            self.bounds = self.bounding_geometry()

    def _visible(self, lon, lat):
        return True

    def _truncate(self, x, y):
        return (x, y)

    def attrs(self):
        p = super(Conic, self).attrs()
        p['lon0'] = self.lon0
        p['lat0'] = self.lat0
        p['lat1'] = self.lat1
        p['lat2'] = self.lat2
        return p

    def _shift_polygon(self, polygon):
        """
        shifts a polygon according to the origin longitude
        """
        if self.lon0 == 0.0:
            return [polygon]  # no need to shift anything

        from shapely.geometry import Polygon
        # we need to split and join some polygons
        poly_coords = []
        holes = []
        for (lon, lat) in polygon.exterior.coords:
            poly_coords.append((lon - self.lon0, lat))
        for hole in polygon.interiors:
            hole_coords = []
            for (lon, lat) in hole.coords:
                hole_coords.append((lon - self.lon0, lat))
            holes.append(hole_coords)
        poly = Polygon(poly_coords, holes)

        polygons = []

        #print "shifted polygons", (time.time() - start)
        #start = time.time()

        try:
            p_in = poly.intersection(self.bounds)
            polygons += hasattr(p_in, 'geoms') and p_in.geoms or [p_in]
        except:
            pass

        #print "computed polygons inside bounds", (time.time() - start)
        #start = time.time()

        try:
            p_out = poly.symmetric_difference(self.bounds)
            out_geoms = hasattr(p_out, 'geoms') and p_out.geoms or [p_out]
        except:
            out_geoms = []
            pass

        #print "computed polygons outside bounds", (time.time() - start)
        #start = time.time()

        for polygon in out_geoms:
            ext_pts = []
            int_pts = []
            s = 0  # at first we compute the avg longitude
            c = 0
            for (lon, lat) in polygon.exterior.coords:
                s += lon
                c += 1
            left = s / float(c) < -180  # and use it to decide where to shift the polygon
            for (lon, lat) in polygon.exterior.coords:
                ext_pts.append((lon + (-360, 360)[left], lat))
            for interior in polygon.interiors:
                pts = []
                for (lon, lat) in interior.coords:
                    pts.append((lon + (-360, 360)[left], lat))
                int_pts.append(pts)
            polygons.append(Polygon(ext_pts, int_pts))

        # print "shifted outside polygons to inside", (time.time() - start)

        return polygons

    @staticmethod
    def attributes():
        return ['lon0', 'lat0', 'lat1', 'lat2']


class LCC(Conic):
    """
    Lambert Conformal Conic Projection (spherical)
    """
    def __init__(self, lat0=0, lon0=0, lat1=30, lat2=50):
        from math import sin, cos, tan, pow, log
        self.minLat = -60
        self.maxLat = 85
        Conic.__init__(self, lat0=lat0, lon0=lon0, lat1=lat1, lat2=lat2)
        self.n = n = sin(self.phi1)
        cosphi = cos(self.phi1)
        secant = abs(self.phi1 - self.phi2) >= 1e-10
        if secant:
            n = log(cosphi / cos(self.phi2)) / log(tan(self.QUARTERPI + .5 * self.phi2) / tan(self.QUARTERPI + .5 * self.phi1))
        self.c = c = cosphi * pow(tan(self.QUARTERPI + .5 * self.phi1), n) / n
        if abs(abs(self.phi0) - self.HALFPI) < 1e-10:
            self.rho0 = 0.
        else:
            self.rho0 = c * pow(tan(self.QUARTERPI + .5 * self.phi0), -n)


    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        phi = rad(lat)
        lam = rad(lon)
        n = self.n
        if abs(abs(phi) - self.HALFPI) < 1e-10:
            rho = 0.0
        else:
            rho = self.c * math.pow(math.tan(self.QUARTERPI + 0.5 * phi), -n)
        lam_ = (lam - self.lam0) * n
        x = 1000 * rho * math.sin(lam_)
        y = 1000 * (self.rho0 - rho * math.cos(lam_))

        return (x, y * -1)

########NEW FILE########
__FILENAME__ = cylindrical
"""
    kartograph - a svg mapping library
    Copyright (C) 2011  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from base import Proj
import math
from math import radians as rad


class Cylindrical(Proj):

    def __init__(self, lon0=0.0, flip=0):
        self.flip = flip
        self.lon0 = lon0
        self.bounds = self.bounding_geometry()

    def _shift_polygon(self, polygon):
        """
        shifts a polygon according to the origin longitude
        """
        if self.lon0 == 0.0:
            return [polygon]  # no need to shift anything

        from shapely.geometry import Polygon
        # we need to split and join some polygons
        poly_coords = []
        holes = []
        for (lon, lat) in polygon.exterior.coords:
            poly_coords.append((lon - self.lon0, lat))
        for hole in polygon.interiors:
            hole_coords = []
            for (lon, lat) in hole.coords:
                hole_coords.append((lon - self.lon0, lat))
            holes.append(hole_coords)
        poly = Polygon(poly_coords, holes)

        polygons = []

        #print "shifted polygons", (time.time() - start)
        #start = time.time()

        try:
            p_in = poly.intersection(self.bounds)
            polygons += hasattr(p_in, 'geoms') and p_in.geoms or [p_in]
        except:
            pass

        #print "computed polygons inside bounds", (time.time() - start)
        #start = time.time()

        try:
            p_out = poly.symmetric_difference(self.bounds)
            out_geoms = hasattr(p_out, 'geoms') and p_out.geoms or [p_out]
        except:
            out_geoms = []
            pass

        #print "computed polygons outside bounds", (time.time() - start)
        #start = time.time()

        for polygon in out_geoms:
            ext_pts = []
            int_pts = []
            s = 0  # at first we compute the avg longitude
            c = 0
            for (lon, lat) in polygon.exterior.coords:
                s += lon
                c += 1
            left = s / float(c) < -180  # and use it to decide where to shift the polygon
            for (lon, lat) in polygon.exterior.coords:
                ext_pts.append((lon + (-360, 360)[left], lat))
            for interior in polygon.interiors:
                pts = []
                for (lon, lat) in interior.coords:
                    pts.append((lon + (-360, 360)[left], lat))
                int_pts.append(pts)
            polygons.append(Polygon(ext_pts, int_pts))

        # print "shifted outside polygons to inside", (time.time() - start)

        return polygons

    def _visible(self, lon, lat):
        return True

    def _truncate(self, x, y):
        return (x, y)

    def attrs(self):
        a = super(Cylindrical, self).attrs()
        a['lon0'] = self.lon0
        a['flip'] = self.flip
        return a

    def __str__(self):
        return 'Proj(' + self.name + ', lon0=%s)' % self.lon0

    @staticmethod
    def attributes():
        return ['lon0', 'flip']

    def ll(self, lon, lat):
        if self.flip == 1:
            return (-lon, -lat)
        return (lon, lat)


class Equirectangular(Cylindrical):
    """
    Equirectangular Projection, aka lonlat, aka plate carree
    """
    def __init__(self, lon0=0.0, lat0=0.0, flip=0):
        self.lat0 = lat0
        self.phi0 = rad(lat0 * -1)
        Cylindrical.__init__(self, lon0=lon0, flip=flip)

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        return (lon * math.cos(self.phi0) * 1000, lat * -1 * 1000)


class CEA(Cylindrical):
    """
    Cylindrical Equal Area Projection
    """
    def __init__(self, lat0=0.0, lon0=0.0, lat1=0.0, flip=0):
        self.lat0 = lat0
        self.lat1 = lat1
        self.phi0 = rad(lat0 * -1)
        self.phi1 = rad(lat1 * -1)
        self.lam0 = rad(lon0)
        Cylindrical.__init__(self, lon0=lon0, flip=flip)

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat * -1)
        x = (lam) * math.cos(self.phi1) * 1000
        y = math.sin(phi) / math.cos(self.phi1) * 1000
        return (x, y)

    def attrs(self):
        p = super(CEA, self).attrs()
        p['lat1'] = self.lat1
        return p

    @staticmethod
    def attributes():
        return ['lon0', 'lat1', 'flip']

    def __str__(self):
        return 'Proj(' + self.name + ', lon0=%s, lat1=%s)' % (self.lon0, self.lat1)


class GallPeters(CEA):
    def __init__(self, lat0=0.0, lon0=0.0, flip=0):
        CEA.__init__(self, lon0=lon0, lat0=0, lat1=45, flip=flip)


class HoboDyer(CEA):
    def __init__(self, lat0=0.0, lon0=0.0, flip=0):
        CEA.__init__(self, lon0=lon0, lat0=lat0, lat1=37.5, flip=flip)


class Behrmann(CEA):
    def __init__(self, lat0=0.0, lon0=0.0, flip=0):
        CEA.__init__(self, lat1=30, lat0=lat0, lon0=lon0, flip=flip)


class Balthasart(CEA):
    def __init__(self, lat0=0.0, lon0=0.0, flip=0):
        CEA.__init__(self, lat1=50, lat0=lat0, lon0=lon0, flip=flip)


class Mercator(Cylindrical):
    def __init__(self, lon0=0.0, lat0=0.0, flip=0):
        Cylindrical.__init__(self, lon0=lon0, flip=flip)
        self.minLat = -85
        self.maxLat = 85

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat * -1)
        x = lam * 1000
        y = math.log((1 + math.sin(phi)) / math.cos(phi)) * 1000
        return (x, y)


class LonLat(Cylindrical):
    def project(self, lon, lat):
        return (lon, lat)

########NEW FILE########
__FILENAME__ = proj4

from kartograph.proj.base import Proj
import pyproj


class Proj4(Proj):
    """
    Generic wrapper around Proj.4 projections
    """
    def __init__(self, projstr):
        self.proj = pyproj.Proj(projstr)

    def project(self, lon, lat):
        x, y = self.proj(lon, lat)
        return x, y * -1

    def project_inverse(self, x, y):
        return self.proj(x, y * -1, inverse=True)

    def _visible(self, lon, lat):
        return True

    @staticmethod
    def attributes():
        """
        returns array of attribute names of this projection
        """
        return ['projstr']

########NEW FILE########
__FILENAME__ = pseudocylindrical
"""
    kartograph - a svg mapping library
    Copyright (C) 2011  Gregor Aisch

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from cylindrical import Cylindrical
import math
from math import radians as rad


class PseudoCylindrical(Cylindrical):
    def __init__(self, lon0=0.0, flip=0):
        Cylindrical.__init__(self, lon0=lon0, flip=flip)


class NaturalEarth(PseudoCylindrical):
    """
    src: http://www.shadedrelief.com/NE_proj/
    """
    def __init__(self, lat0=0.0, lon0=0.0, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)
        from math import pi
        s = self
        s.A0 = 0.8707
        s.A1 = -0.131979
        s.A2 = -0.013791
        s.A3 = 0.003971
        s.A4 = -0.001529
        s.B0 = 1.007226
        s.B1 = 0.015085
        s.B2 = -0.044475
        s.B3 = 0.028874
        s.B4 = -0.005916
        s.C0 = s.B0
        s.C1 = 3 * s.B1
        s.C2 = 7 * s.B2
        s.C3 = 9 * s.B3
        s.C4 = 11 * s.B4
        s.EPS = 1e-11
        s.MAX_Y = 0.8707 * 0.52 * pi

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lplam = rad(lon)
        lpphi = rad(lat * -1)
        phi2 = lpphi * lpphi
        phi4 = phi2 * phi2
        x = lplam * (self.A0 + phi2 * (self.A1 + phi2 * (self.A2 + phi4 * phi2 * (self.A3 + phi2 * self.A4)))) * 180 + 500
        y = lpphi * (self.B0 + phi2 * (self.B1 + phi4 * (self.B2 + self.B3 * phi2 + self.B4 * phi4))) * 180 + 270
        return (x, y)


class Robinson(PseudoCylindrical):

    def __init__(self, lat0=0.0, lon0=0.0, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)
        self.X = [1, -5.67239e-12, -7.15511e-05, 3.11028e-06,  0.9986, -0.000482241, -2.4897e-05, -1.33094e-06, 0.9954, -0.000831031, -4.4861e-05, -9.86588e-07, 0.99, -0.00135363, -5.96598e-05, 3.67749e-06, 0.9822, -0.00167442, -4.4975e-06, -5.72394e-06, 0.973, -0.00214869, -9.03565e-05, 1.88767e-08, 0.96, -0.00305084, -9.00732e-05, 1.64869e-06, 0.9427, -0.00382792, -6.53428e-05, -2.61493e-06, 0.9216, -0.00467747, -0.000104566, 4.8122e-06, 0.8962, -0.00536222, -3.23834e-05, -5.43445e-06, 0.8679, -0.00609364, -0.0001139, 3.32521e-06, 0.835, -0.00698325, -6.40219e-05, 9.34582e-07, 0.7986, -0.00755337, -5.00038e-05, 9.35532e-07, 0.7597, -0.00798325, -3.59716e-05, -2.27604e-06, 0.7186, -0.00851366, -7.0112e-05, -8.63072e-06, 0.6732, -0.00986209, -0.000199572, 1.91978e-05, 0.6213, -0.010418, 8.83948e-05, 6.24031e-06, 0.5722, -0.00906601, 0.000181999, 6.24033e-06, 0.5322,  0.,  0.,  0.]
        self.Y = [0, 0.0124, 3.72529e-10, 1.15484e-09, 0.062, 0.0124001, 1.76951e-08, -5.92321e-09, 0.124, 0.0123998, -7.09668e-08, 2.25753e-08, 0.186, 0.0124008, 2.66917e-07, -8.44523e-08, 0.248, 0.0123971, -9.99682e-07, 3.15569e-07, 0.31, 0.0124108, 3.73349e-06, -1.1779e-06, 0.372, 0.0123598, -1.3935e-05, 4.39588e-06, 0.434, 0.0125501, 5.20034e-05, -1.00051e-05, 0.4968, 0.0123198, -9.80735e-05, 9.22397e-06, 0.5571, 0.0120308, 4.02857e-05, -5.2901e-06, 0.6176, 0.0120369, -3.90662e-05, 7.36117e-07, 0.6769, 0.0117015, -2.80246e-05, -8.54283e-07, 0.7346, 0.0113572, -4.08389e-05, -5.18524e-07, 0.7903, 0.0109099, -4.86169e-05, -1.0718e-06, 0.8435, 0.0103433, -6.46934e-05, 5.36384e-09, 0.8936, 0.00969679, -6.46129e-05, -8.54894e-06, 0.9394, 0.00840949, -0.000192847, -4.21023e-06, 0.9761, 0.00616525, -0.000256001, -4.21021e-06, 1.,  0.,  0.,  0]
        self.NODES = 18
        self.FXC = 0.8487
        self.FYC = 1.3523
        self.C1 = 11.45915590261646417544
        self.RC1 = 0.08726646259971647884
        self.ONEEPS = 1.000001
        self.EPS = 1e-8

    def _poly(self, arr, off, z):
        return arr[off] + z * (arr[off + 1] + z * (arr[off + 2] + z * (arr[off + 3])))

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lplam = rad(lon)
        lpphi = rad(lat * -1)

        phi = abs(lpphi)
        i = int(phi * self.C1)
        if i >= self.NODES:
            i = self.NODES - 1
        phi = math.degrees(phi - self.RC1 * i)
        i *= 4
        x = 1000 * self._poly(self.X, i, phi) * self.FXC * lplam
        y = 1000 * self._poly(self.Y, i, phi) * self.FYC
        if lpphi < 0.0:
            y = -y

        return (x, y)


class EckertIV(PseudoCylindrical):

    def __init__(self, lon0=0.0, lat0=0, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)

        self.C_x = .42223820031577120149
        self.C_y = 1.32650042817700232218
        self.RC_y = .75386330736002178205
        self.C_p = 3.57079632679489661922
        self.RC_p = .28004957675577868795
        self.EPS = 1e-7
        self.NITER = 6

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lplam = rad(lon)
        lpphi = rad(lat * -1)

        p = self.C_p * math.sin(lpphi)
        V = lpphi * lpphi
        lpphi *= 0.895168 + V * (0.0218849 + V * 0.00826809)

        i = self.NITER
        while i > 0:
            c = math.cos(lpphi)
            s = math.sin(lpphi)
            V = (lpphi + s * (c + 2.) - p) / (1. + c * (c + 2.) - s * s)
            lpphi -= V
            if abs(V) < self.EPS:
                break
            i -= 1

        if i == 0:
            x = self.C_x * lplam
            y = (self.C_y, - self.C_y)[lpphi < 0]
        else:
            x = self.C_x * lplam * (1. + math.cos(lpphi))
            y = self.C_y * math.sin(lpphi)
        return (x, y)


class Sinusoidal(PseudoCylindrical):

    def __init__(self, lon0=0.0, lat0=0.0, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat * -1)
        x = 1032 * lam * math.cos(phi)
        y = 1032 * phi
        return (x, y)


class Mollweide(PseudoCylindrical):

    def __init__(self, p=1.5707963267948966, lon0=0.0, lat0=0.0, cx=None, cy=None, cp=None, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)
        self.MAX_ITER = 10
        self.TOLERANCE = 1e-7

        if p != None:
            p2 = p + p
            sp = math.sin(p)
            r = math.sqrt(math.pi * 2.0 * sp / (p2 + math.sin(p2)))
            self.cx = 2. * r / math.pi
            self.cy = r / sp
            self.cp = p2 + math.sin(p2)
        elif cx != None and cy != None and cp != None:
            self.cx = cx
            self.cy = cy
            self.cp = cp
        else:
            assert False, 'either p or cx,cy,cp must be defined'

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat)

        k = self.cp * math.sin(phi)
        i = self.MAX_ITER

        while i != 0:
            v = (phi + math.sin(phi) - k) / (1. + math.cos(phi))
            phi -= v
            if abs(v) < self.TOLERANCE:
                break
            i -= 1

        if i == 0:
            phi = (self.HALFPI, -self.HALFPI)[phi < 0]
        else:
            phi *= 0.5

        x = 1000 * self.cx * lam * math.cos(phi)
        y = 1000 * self.cy * math.sin(phi)
        return (x, y * -1)


class GoodeHomolosine(PseudoCylindrical):

    def __init__(self, lon0=0, flip=0):
        self.lat1 = 41.737
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)
        self.p1 = Mollweide()
        self.p0 = Sinusoidal()

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        #lon = me.clon(lon)
        if abs(lat) > self.lat1:
            return self.p1.project(lon, lat)
        else:
            return self.p0.project(lon, lat)


class WagnerIV(Mollweide):
    def __init__(self, lon0=0, lat0=0, flip=0):
        # p=math.pi/3
        Mollweide.__init__(self, p=1.0471975511965976, flip=flip)


class WagnerV(Mollweide):
    def __init__(self, lat0=0, lon0=0, flip=0):
        Mollweide.__init__(self, cx=0.90977, cy=1.65014, cp=3.00896, flip=flip)


class Loximuthal(PseudoCylindrical):

    minLat = -89
    maxLat = 89

    def __init__(self, lon0=0.0, lat0=0.0, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)
        if flip == 1:
            lat0 = -lat0
        self.lat0 = lat0
        self.phi0 = rad(lat0)

    def project(self, lon, lat):
        lon, lat = self.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat)
        if phi == self.phi0:
            x = lam * math.cos(self.phi0)
        else:
            try:
                x = lam * (phi - self.phi0) / (math.log(math.tan(self.QUARTERPI + phi * 0.5)) - math.log(math.tan(self.QUARTERPI + self.phi0 * 0.5)))
            except:
                return None
        x *= 1000
        y = 1000 * (phi - self.phi0)
        return (x, y * -1)

    def attrs(self):
        p = super(Loximuthal, self).attrs()
        p['lat0'] = self.lat0
        return p

    @staticmethod
    def attributes():
        return ['lon0', 'lat0', 'flip']


class CantersModifiedSinusoidalI(PseudoCylindrical):
    """
    Canters, F. (2002) Small-scale Map projection Design. p. 218-219.
    Modified Sinusoidal, equal-area.

    implementation borrowed from
    http://cartography.oregonstate.edu/temp/AdaptiveProjection/src/projections/Canters1.js
    """

    def __init__(self, lon0=0.0, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)
        self.C1 = 1.1966
        self.C3 = -0.1290
        self.C3x3 = 3 * self.C3
        self.C5 = -0.0076
        self.C5x5 = 5 * self.C5

    def project(self, lon, lat):
        me = self
        lon, lat = me.ll(lon, lat)

        lon = rad(lon)
        lat = rad(lat)

        y2 = lat * lat
        y4 = y2 * y2
        x = 1000 * lon * math.cos(lat) / (me.C1 + me.C3x3 * y2 + me.C5x5 * y4)
        y = 1000 * lat * (me.C1 + me.C3 * y2 + me.C5 * y4)
        return (x, y * -1)


class Hatano(PseudoCylindrical):

    def __init__(me, lon0=0, flip=0):
        PseudoCylindrical.__init__(me, lon0=lon0, flip=flip)
        me.NITER = 20
        me.EPS = 1e-7
        me.ONETOL = 1.000001
        me.CN = 2.67595
        me.CS = 2.43763
        me.RCN = 0.37369906014686373063
        me.RCS = 0.41023453108141924738
        me.FYCN = 1.75859
        me.FYCS = 1.93052
        me.RYCN = 0.56863737426006061674
        me.RYCS = 0.51799515156538134803
        me.FXC = 0.85
        me.RXC = 1.17647058823529411764

    def project(me, lon, lat):
        [lon, lat] = me.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat)
        c = math.sin(phi) * (me.CN, me.CS)[phi < 0.0]
        for i in range(me.NITER, 0, -1):
            th1 = (phi + math.sin(phi) - c) / (1.0 + math.cos(phi))
            phi -= th1
            if abs(th1) < me.EPS:
                break
        phi *= 0.5
        x = 1000 * me.FXC * lam * math.cos(phi)
        y = 1000 * math.sin(phi) * (me.FYCN, me.FYCS)[phi < 0.0]
        return (x, y * -1)


class Aitoff(PseudoCylindrical):
    """
    Aitoff projection

    implementation taken from
    Snyder, Map projections - A working manual
    """
    def __init__(self, lon0=0, flip=0):
        PseudoCylindrical.__init__(self, lon0=lon0, flip=flip)
        self.winkel = False
        self.COSPHI1 = 0.636619772367581343

    def project(me, lon, lat):
        [lon, lat] = me.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat)
        c = 0.5 * lam
        d = math.acos(math.cos(phi) * math.cos(c))
        if d != 0:
            y = 1.0 / math.sin(d)
            x = 2.0 * d * math.cos(phi) * math.sin(c) * y
            y *= d * math.sin(phi)
        else:
            x = y = 0
        if me.winkel:
            x = (x + lam * me.COSPHI1) * 0.5
            y = (y + phi) * 0.5
        return (x * 1000, y * -1000)


class Winkel3(Aitoff):

    def __init__(self, lon0=0, flip=0):
        Aitoff.__init__(self, lon0=lon0, flip=flip)
        self.winkel = True


class Nicolosi(PseudoCylindrical):

    def __init__(me, lon0=0, flip=0):
        me.EPS = 1e-10
        PseudoCylindrical.__init__(me, lon0=lon0, flip=flip)
        me.r = me.HALFPI * 100
        sea = []
        r = me.r
        for phi in range(0, 361):
            sea.append((math.cos(rad(phi)) * r, math.sin(rad(phi)) * r))
        me.sea = sea

    def _clon(me, lon):
        lon -= me.lon0
        if lon < -180:
            lon += 360
        elif lon > 180:
            lon -= 360
        return lon

    def _visible(me, lon, lat):
        #lon = me._clon(lon)
        return lon > -90 and lon < 90

    def _truncate(me, x, y):
        theta = math.atan2(y, x)
        x1 = me.r * math.cos(theta)
        y1 = me.r * math.sin(theta)
        return (x1, y1)

    def world_bounds(self, bbox, llbbox=(-180, -90, 180, 90)):
        if llbbox == (-180, -90, 180, 90):
            d = self.r * 2
            bbox.update((-d, -d))
            bbox.update((d, d))
        else:
            bbox = super(PseudoCylindrical, self).world_bounds(bbox, llbbox)
        return bbox

    def sea_shape(self, llbbox=(-180, -90, 180, 90)):
        out = []
        if llbbox == (-180, -90, 180, 90) or llbbox == [-180, -90, 180, 90]:
            for phi in range(0, 360):
                x = math.cos(math.radians(phi)) * self.r
                y = math.sin(math.radians(phi)) * self.r
                out.append((x, y))
            out = [out]
        else:
            out = super(PseudoCylindrical, self).sea_shape(llbbox)
        return out

    def project(me, lon, lat):
        [lon, lat] = me.ll(lon, lat)
        lam = rad(lon)
        phi = rad(lat)

        if abs(lam) < me.EPS:
            x = 0
            y = phi
        elif abs(phi) < me.EPS:
            x = lam
            y = 0
        elif abs(abs(lam) - me.HALFPI) < me.EPS:
            x = lam * math.cos(phi)
            y = me.HALFPI * math.sin(phi)
        elif abs(abs(phi) - me.HALFPI) < me.EPS:
            x = 0
            y = phi
        else:
            tb = me.HALFPI / lam - lam / me.HALFPI
            c = phi / me.HALFPI
            sp = math.sin(phi)
            d = (1 - c * c) / (sp - c)
            r2 = tb / d
            r2 *= r2
            m = (tb * sp / d - 0.5 * tb) / (1.0 + r2)
            n = (sp / r2 + 0.5 * d) / (1.0 + 1.0 / r2)
            x = math.cos(phi)
            x = math.sqrt(m * m + x * x / (1.0 + r2))
            x = me.HALFPI * (m + (x, -x)[lam < 0])
            f = n * n - (sp * sp / r2 + d * sp - 1.0) / (1.0 + 1.0 / r2)
            if f < 0:
                y = phi
            else:
                y = math.sqrt(f)
                y = me.HALFPI * (n + (-y, y)[phi < 0])
        return (x * 100, y * -100)

    def plot(self, polygon, truncate=True):
        polygons = self._shift_polygon(polygon)
        plotted = []
        for polygon in polygons:
            points = []
            ignore = True
            for (lon, lat) in polygon:
                vis = self._visible(lon, lat)
                if vis:
                    ignore = False
                x, y = self.project(lon, lat)
                if not vis and truncate:
                    points.append(self._truncate(x, y))
                else:
                    points.append((x, y))
            if ignore:
                continue
            plotted.append(points)
        return plotted

########NEW FILE########
__FILENAME__ = svg

from kartograph.renderer import MapRenderer
from kartograph.errors import KartographError
from kartograph.mapstyle import style_diff, remove_unit

# This script contains everything that is needed by Kartograph to finally
# render the processed maps into SVG files.
#

# The SVG renderer is based on xml.dom.minidom.
from xml.dom import minidom
from xml.dom.minidom import parse
import re


class SvgRenderer(MapRenderer):

    def render(self, style, pretty_print=False):
        """
        The render() method prepares a new empty SVG document and
        stores all the layer features into SVG groups.
        """
        self.style = style
        self.pretty_print = pretty_print
        self._init_svg_doc()
        self._store_layers_to_svg()
        if self.map.options['export']['scalebar'] != False:
            self._render_scale_bar(self.map.options['export']['scalebar'])

    def _init_svg_doc(self):
        # Load width and height of the map view
        # We add two pixels to the height to ensure that
        # the map fits.
        w = self.map.view.width
        h = self.map.view.height + 2

        # SvgDocument is a handy wrapper around xml.dom.minidom. It is defined below.
        svg = SvgDocument(
            width='%dpx' % w,
            height='%dpx' % h,
            viewBox='0 0 %d %d' % (w, h),
            enable_background='new 0 0 %d %d' % (w, h),
            style='stroke-linejoin: round; stroke:#000; fill: none;',
            pretty_print=self.pretty_print)

        defs = svg.node('defs', svg.root)
        style = svg.node('style', defs, type='text/css')
        css = 'path { fill-rule: evenodd; }'
        svg.cdata(css, style)
        metadata = svg.node('metadata', svg.root)
        views = svg.node('views', metadata)
        view = svg.node('view', views,
            padding=str(self.map.options['bounds']['padding']), w=w, h=h)

        svg.node('proj', view, **self.map.proj.attrs())
        svg.node('bbox', view,
            x=round(self.map.src_bbox.left, 2),
            y=round(self.map.src_bbox.top, 2),
            w=round(self.map.src_bbox.width, 2),
            h=round(self.map.src_bbox.height, 2))
        self.svg = svg

    def _render_feature(self, feature, attributes=[], labelOpts=False):
        node = self._render_geometry(feature.geometry)
        if node is None:
            return None

        if attributes == 'all':
            attributes = []
            for k in feature.props:
                attributes.append(dict(src=k, tgt=k))

        for cfg in attributes:
            if 'src' in cfg:
                tgt = re.sub('(\W|_)+', '-', cfg['tgt'].lower())
                if cfg['src'] not in feature.props:
                    continue
                    #raise KartographError(('attribute not found "%s"'%cfg['src']))
                val = feature.props[cfg['src']]
                if isinstance(val, (int, float)):
                    val = str(val)
                node.setAttribute('data-' + tgt, val)
                if tgt == "id":
                    node.setAttribute('id', val)

            elif 'where' in cfg:
                # can be used to replace attributes...
                src = cfg['where']
                tgt = cfg['set']
                if len(cfg['equals']) != len(cfg['to']):
                    raise KartographError('attributes: "equals" and "to" arrays must be of same length')
                for i in range(len(cfg['equals'])):
                    if feature.props[src] == cfg['equals'][i]:
                        node.setAttribute('data-' + tgt, cfg['to'][i])

        return node

    def _render_geometry(self, geometry):
        from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point
        if geometry is None:
            return
        if isinstance(geometry, (Polygon, MultiPolygon)):
            return self._render_polygon(geometry)
        elif isinstance(geometry, (LineString, MultiLineString)):
            return self._render_line(geometry)
        elif isinstance(geometry, (Point)):
            return self._render_point(geometry)
        else:
            raise KartographError('svg renderer doesn\'t know how to handle ' + str(type(geometry)))

    def _render_polygon(self, geometry):
        """ constructs a svg representation of a polygon """
        _round = self.map.options['export']['round']
        path_str = ""
        if _round is False:
            fmt = '%f,%f'
        else:
            fmt = '%.' + str(_round) + 'f'
            fmt = fmt + ',' + fmt

        geoms = hasattr(geometry, 'geoms') and geometry.geoms or [geometry]
        for polygon in geoms:
            if polygon is None:
                continue
            for ring in [polygon.exterior] + list(polygon.interiors):
                cont_str = ""
                kept = []
                for pt in ring.coords:
                    kept.append(pt)
                if len(kept) <= 3:
                    continue
                for pt in kept:
                    if cont_str == "":
                        cont_str = "M"
                    else:
                        cont_str += "L"
                    cont_str += fmt % pt
                cont_str += "Z "
                path_str += cont_str
        if path_str == "":
            return None
        path = self.svg.node('path', d=path_str)
        return path

    def _render_line(self, geometry):
        """ constructs a svg representation of this line """
        _round = self.map.options['export']['round']
        path_str = ""
        if _round is False:
            fmt = '%f,%f'
        else:
            fmt = '%.' + str(_round) + 'f'
            fmt = fmt + ',' + fmt

        geoms = hasattr(geometry, 'geoms') and geometry.geoms or [geometry]
        for line in geoms:
            if line is None:
                continue
            cont_str = ""
            kept = []
            for pt in line.coords:
                kept.append(pt)
            for pt in kept:
                if cont_str == "":
                    cont_str = "M"
                else:
                    cont_str += "L"
                cont_str += fmt % pt
            cont_str += " "
            if kept[0] == kept[-1]:
                cont_str += "Z "
            path_str += cont_str
        if path_str == "":
            return None
        path = self.svg.node('path', d=path_str)
        return path

    def _store_layers_to_svg(self):
        """
        store features in svg
        """
        svg = self.svg
        # label_groups = []
        for layer in self.map.layers:
            if len(layer.features) == 0:
                # print "ignoring empty layer", layer.id
                continue  # ignore empty layers
            if layer.options['render']:
                g = svg.node('g', svg.root, id=layer.id)
                g.setAttribute('class', ' '.join(layer.classes))
                layer_css = self.style.applyStyle(g, layer.id, layer.classes)

            # Create an svg group for labels of this layer
            lbl = layer.options['labeling']
            if lbl is not False:
                if lbl['buffer'] is not False:
                    lgbuf = svg.node('g', svg.root, id=layer.id + '-label-buffer')
                    self.style.applyStyle(lgbuf, layer.id + '-label', ['label'])
                    self.style.applyStyle(lgbuf, layer.id + '-label-buffer', ['label-buffer'])
                    _apply_default_label_styles(lgbuf)
                    lbl['lg-buffer'] = lgbuf
                lg = svg.node('g', svg.root, id=layer.id + '-label', stroke='none')
                self.style.applyStyle(lg, layer.id + '-label', ['label'])
                _apply_default_label_styles(lg)
                lbl['lg'] = lg
            else:
                lg = None

            for feat in layer.features:
                if layer.options['render']:
                    node = self._render_feature(feat, layer.options['attributes'])
                    if node is not None:
                        feat_css = self.style.getStyle(layer.id, layer.classes, feat.props)
                        feat_css = style_diff(feat_css, layer_css)
                        for prop in feat_css:
                            node.setAttribute(prop, str(feat_css[prop]))
                        g.appendChild(node)
                    else:
                        pass
                        #sys.stderr.write("feature.to_svg is None", feat)
                if lbl is not False:
                    self._render_label(layer, feat, lbl)

        # Finally add label groups on top of all other groups
        # for lg in label_groups:
        #    svg.root.appendChild(lg)

    def _render_point(self, geometry):
        dot = self.svg.node('circle', cx=geometry.x, cy=geometry.y, r=2)
        return dot

    def _render_label(self, layer, feature, labelOpts):
        #if feature.geometry.area < 20:
        #    return
        try:
            cx, cy = _get_label_position(feature.geometry, labelOpts['position'])
        except KartographError:
            return

        key = labelOpts['key']
        if not key:
            key = feature.props.keys()[0]
        if key not in feature.props:
            #sys.stderr.write('could not find feature property "%s" for labeling\n' % key)
            return
        if 'min-area' in labelOpts and feature.geometry.area < float(labelOpts['min-area']):
            return
        text = feature.props[key]
        if labelOpts['buffer'] is not False:
            l = self._label(text, cx, cy, labelOpts['lg-buffer'], labelOpts)
            self.style.applyFeatureStyle(l, layer.id + '-label', ['label'], feature.props)
            self.style.applyFeatureStyle(l, layer.id + '-label-buffer', ['label-buffer'], feature.props)
        l = self._label(text, cx, cy, labelOpts['lg'], labelOpts)
        self.style.applyFeatureStyle(l, layer.id + '-label', ['label'], feature.props)

    def _label(self, text, x, y, group, opts):
        # split text into ines
        if 'split-chars' not in opts:
            lines = [text]
        else:
            if 'split-at' not in opts:
                opts['split-at'] = 10
            lines = split_at(text, opts['split-chars'], opts['split-at'])
        lh = remove_unit(group.getAttribute('font-size'))
        if lh is None:
            lh = 12
        line_height = remove_unit(group.getAttribute('line-height'))
        if line_height:
            lh = line_height
        h = len(lines) * lh
        lbl = self.svg.node('text', group, y=y - h * 0.5, text__anchor='middle')
        yo = 0
        for line in lines:
            tspan = self.svg.node('tspan', lbl, x=x, dy=yo)
            yo += lh
            self.svg.cdata(line, tspan)
        return lbl

    def _render_scale_bar(self, opts):

        def format(m):
            if m > 1000:
                if m % 1000 == 0:
                    return (str(int(m / 1000)), 'km')
                else:
                    return (str(round(m / 1000, 1)), 'km')
            return (str(m), 'm')

        svg = self.svg
        meters, pixel = self.map.scale_bar_width()
        if 'align' not in opts:
            opts['align'] = 'bl'  # default to bottom left
        if 'offset' not in opts:
            opts['offset'] = 20  # 20px offset
        g = svg.node('g', svg.root, id='scalebar', shape__rendering='crispEdges',  text__anchor='middle', stroke='none', fill='#000', font__size=13)
        left = (opts['offset'], self.map.view.width - pixel - opts['offset'])[opts['align'][1] != 'l']
        top = (opts['offset'] + 20, self.map.view.height - opts['offset'])[opts['align'][0] != 't']
        dy = -8
        paths = []
        paths.append((left, top + dy, left, top, left + pixel, top, left + pixel, top + dy))
        for i in (1.25, 2.5, 3.75, 5, 6.25, 7.5, 8.75):
            _dy = dy
            if i != 5:
                _dy *= 0.5
            paths.append((left + pixel * i / 10.0, top + dy, left + pixel * i / 10.0, top))

        def path(pts, stroke, strokeWidth):
            d = ('M%d,%d' + ('L%d,%d' * (len(pts[2:]) / 2))) % pts
            svg.node('path', g, d=d, fill='none', stroke=stroke, stroke__width=strokeWidth)

        for pts in paths:
            path(pts, '#fff', 5)
        for pts in paths:
            path(pts, '#000', 1)

        def lbl(txt, x=0, y=0):
            # buffer
            lbl = svg.node('text', g, x=x, y=y, stroke='#fff', stroke__width='4px')
            svg.cdata(txt, lbl)
            self.style.applyStyle(lbl, 'scalebar', [])
            self.style.applyStyle(lbl, 'scalebar-buffer', [])
            # text
            lbl = svg.node('text', g, x=x, y=y)
            svg.cdata(txt, lbl)
            self.style.applyStyle(lbl, 'scalebar', [])

        lbl('%s%s' % format(meters), x=int(left + pixel), y=(top + dy - 7))
        lbl('%s' % format(meters * 0.5)[0], x=int(left + pixel * 0.5), y=(top + dy - 7))
        lbl('%s' % format(meters * 0.25)[0], x=int(left + pixel * 0.25), y=(top + dy - 7))
        lbl('0', x=int(left), y=(top + dy - 7))

    def write(self, filename):
        self.svg.write(filename, self.pretty_print)

    def preview(self, command):
        self.svg.preview(command, self.pretty_print)

    def __str__(self):
        return self.svg.tostring(self.pretty_print)


def split_at(text, chars, minLen):
    res = [text]
    for char in chars:
        tmp = []
        for text in res:
            parts = text.split(char)
            for p in range(len(parts) - 1):
                if char != '(':
                    parts[p] += char
                else:
                    parts[p + 1] = char + parts[p + 1]
            tmp += parts
        res = tmp
    o = []
    keep = ''
    for token in res:
        if len(keep) > minLen:
            o.append(keep)
            keep = ''
        keep += token
    o.append(keep)
    return o

# SvgDocument
# -----------
#
# SVGDocument is a handy wrapper around xml.dom.minidom which allows us
# to quickly build XML structures. It is largely inspired by the SVG class
# of the [svgfig](http://code.google.com/p/svgfig/) project, which was
# used by one of the earlier versions of Kartograph.
#


class SvgDocument(object):

    # Of course, we need to create and XML document with all this
    # boring SVG header stuff added to it.
    def __init__(self, **kwargs):
        imp = minidom.getDOMImplementation('')
        dt = imp.createDocumentType('svg',
            '-//W3C//DTD SVG 1.1//EN',
            'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd')
        self.doc = imp.createDocument('http://www.w3.org/2000/svg', 'svg', dt)
        self.root = svg = self.doc.getElementsByTagName('svg')[0]
        svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
        svg.setAttribute('version', '1.1')
        svg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
        _add_attrs(self.root, kwargs)

    # This is the magic of SvgDocument. Instead of having to do appendChild()
    # and addAttribute() for every node we create, we just call svgdoc.node()
    # which is smart enough to append itself to the parent if we specify one,
    # and also sets all attributes we pass as keyword arguments.
    def node(self, name, parent=None, **kwargs):
        el = self.doc.createElement(name)
        _add_attrs(el, kwargs)
        if parent is not None:
            parent.appendChild(el)
        return el

    # Sometimes we also need a <[CDATA]> block, for instance if we embed
    # CSS code in the SVG document.
    def cdata(self, data, parent=None):
        cd = minidom.CDATASection()
        cd.data = data
        if parent is not None:
            parent.appendChild(cd)
        return cd

    # Here we finally write the SVG file, and we're brave enough
    # to try to write it in Unicode.
    def write(self, outfile, pretty_print=False):
        if isinstance(outfile, (str, unicode)):
            outfile = open(outfile, 'w')
        if pretty_print:
            raw = self.doc.toprettyxml('utf-8')
        else:
            raw = self.doc.toxml('utf-8')
        try:
            raw = raw.encode('utf-8')
        except:
            print 'warning: could not encode to unicode'

        outfile.write(raw)
        outfile.close()

    # Don't blame me if you don't have a command-line shortcut to
    # simply the best free browser of the world.
    def preview(self, command, pretty_print=False):
        import tempfile
        tmpfile = tempfile.NamedTemporaryFile(suffix='.svg', delete=False)
        self.write(tmpfile, pretty_print)
        print 'map stored to', tmpfile.name
        from subprocess import call
        call([command, tmpfile.name])

    def tostring(self, pretty_print=False):
        if pretty_print:
            return self.doc.toprettyxml()
        return self.doc.toxml()

    # This is an artifact of an older version of Kartograph, but
    # maybe we'll need it later. It will load an SVG document from
    # a file.
    @staticmethod
    def load(filename):
        svg = SvgDocument()
        dom = parse(filename)
        svg.doc = dom
        svg.root = dom.getElementsByTagName('svg')[0]
        return svg


def _add_attrs(node, attrs):
    for key in attrs:
        node.setAttribute(key.replace('__', '-'), str(attrs[key]))


def _get_label_position(geometry, pos):
    if pos == 'centroid' and not (geometry is None):
        pt = geometry.centroid
        return (pt.x, pt.y)
    else:
        raise KartographError('unknown label positioning mode ' + pos)


def _apply_default_label_styles(lg):
    if not lg.getAttribute('font-size'):
        lg.setAttribute('font-size', '12px')
    if not lg.getAttribute('font-family'):
        lg.setAttribute('font-family', 'Arial')
    if not lg.getAttribute('fill'):
        lg.setAttribute('fill', '#000')

########NEW FILE########
__FILENAME__ = distance


def simplify_distance(points, dist):
    """
    simplifies a line segment using a very simple algorithm that checks the distance
    to the last non-deleted point. the algorithm operates on line segments.

    in order to preserve topology of the original polygons the algorithm
    - never removes the first or the last point of a line segment
    - flags all points as simplified after processing (so it won't be processed twice)
    """
    dist_sq = dist * dist
    n = len(points)

    kept = []
    deleted = 0
    if n < 4:
        return points

    for i in range(0, n):
        pt = points[i]
        if i == 0 or i == n - 1:
            # never remove first or last point of line
            pt.simplified = True
            lpt = pt
            kept.append(pt)
        else:
            d = (pt.x - lpt.x) * (pt.x - lpt.x) + (pt.y - lpt.y) * (pt.y - lpt.y)  # compute distance to last point
            if pt.simplified or d > dist_sq:  # if point already handled or distance exceeds threshold..
                kept.append(pt)  # ..keep the point
                lpt = pt
            else:  # otherwise remove it
                deleted += 1
                pt.deleted = True
            pt.simplified = True

    if len(kept) < 4:
        for pt in points:
            pt.deleted = False
        return points

    return kept
    #print 'kept %d   deleted %d' % (kept, deleted)

########NEW FILE########
__FILENAME__ = douglas_peucker


def simplify_douglas_peucker(points, epsilon):
    """
    simplifies a line segment using the Douglas-Peucker algorithm.

    taken from
    http://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm#Pseudocode

    in order to preserve topology of the original polygons the algorithm
    - never removes the first or the last point of a line segment
    - flags all points as simplified after processing (so it won't be processed twice)
    """
    n = len(points)
    kept = []
    if n < 4:
        return points  # skip short lines

    if not points[0].simplified:
        _douglas_peucker(points, 0, n - 1, epsilon)

    return kept
    #print 'kept %d   deleted %d' % (kept, deleted)


def _douglas_peucker(points, start, end, epsilon):
    """ inner part of Douglas-Peucker algorithm, called recursively """
    dmax = 0
    index = 0

    # Find the point with the maximum distance
    for i in range(start + 1, end):
        x1, y1 = points[start]
        x2, y2 = points[end]
        if x1 == x2 and y1 == y2:
            return
        x3, y3 = points[i]
        d = _min_distance(x1, y1, x2, y2, x3, y3)
        if d > dmax:
            index = i
            dmax = d

    # If max distance is greater than epsilon, recursively simplify
    if dmax >= epsilon and start < index < end:
        # recursivly call
        _douglas_peucker(points, start, index, epsilon)
        _douglas_peucker(points, index, end, epsilon)
    else:
        # remove any point but the first and last
        for i in range(start, end + 1):
            points[i].deleted = i == start or i == end
            points[i].simplified = True


def _min_distance(x1, y1, x2, y2, x3, y3):
    """
    the perpendicular distance from a point (x3,y3) to the line from (x1,y1) to (x2,y2)
    taken from http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/
    """
    d = _dist(x1, y1, x2, y2)
    u = (x3 - x1) * (x2 - x1) + (y3 - y1) * (y2 - y1) / (d * d)
    x = x1 + u * (x2 - x1)
    y = y1 + u * (y2 - y1)
    return _dist(x, y, x3, y3)


def _dist(x1, y1, x2, y2):
    """ eucledian distance between two points """
    import math
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)

########NEW FILE########
__FILENAME__ = mpoint


class MPoint:
    """
    Point class used for polygon simplification
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.simplified = False
        self.deleted = False
        self.keep = False
        self.features = set()

    def isDeletable(self):
        if self.keep or self.simplified or self.three:
            return False
        return True

    def __repr__(self):
        return 'Pt(%.2f,%.2f)' % (self.x, self.y)

    def __len__(self):
        return 2

    def __getitem__(self, key):
        if key == 0:
            return self.x
        if key == 1:
            return self.y
        raise IndexError()

    def __contains__(self, key):
        if key == "deleted":
            return True
        return False

########NEW FILE########
__FILENAME__ = unify

from mpoint import MPoint

"""
the whole point of the unification step is to convert all points into unique MPoint instances
"""


def create_point_store():
    """ creates a new point_store """
    point_store = {'kept': 0, 'removed': 0}
    return point_store


def unify_rings(rings, point_store, precision=None, feature=None):
    out = []
    for ring in rings:
        out.append(unify_ring(ring, point_store, precision=precision, feature=feature))
    return out


def unify_ring(ring, point_store, precision=None, feature=None):
    """
    Replaces duplicate points with MPoint instances
    """
    out_ring = []
    lptid = ''
    for pt in ring:
        if 'deleted' not in pt:
            pt = MPoint(pt[0], pt[1])  # eventually convert to MPoint
        # generate hash for point
        if precision is not None:
            fmt = '%' + precision + 'f-%' + precision + 'f'
        else:
            fmt = '%f-%f'
        pid = fmt % (pt.x, pt.y)
        if pid == lptid:
            continue  # skip double points
        lptid = pid
        if pid in point_store:
            # load existing point from point store
            point = point_store[pid]
            point_store['removed'] += 1
        else:
            point = pt
            point_store['kept'] += 1
            point_store[pid] = pt

        point.features.add(feature)
        out_ring.append(point)
    return out_ring

########NEW FILE########
__FILENAME__ = visvalingam


def simplify_visvalingam_whyatt(points, tolerance):
    """ Visvalingam-Whyatt simplification
    implementation borrowed from @migurski:
    https://github.com/migurski/Bloch/blob/master/Bloch/__init__.py#L133
    """
    if len(points) < 3:
        return
    if points[1].simplified:
        return

    min_area = tolerance ** 2

    pts = range(len(points))  # pts stores an index of all non-deleted points

    while len(pts) > 4:
        preserved, popped = set(), []
        areas = []

        for i in range(1, len(pts) - 1):
            x1, y1 = points[pts[i - 1]]
            x2, y2 = points[pts[i]]
            x3, y3 = points[pts[i + 1]]
            # compute and store triangle area
            areas.append((_tri_area(x1, y1, x2, y2, x3, y3), i))

        areas = sorted(areas)

        if not areas or areas[0][0] > min_area:
            # there's nothing to be done
            for pt in points:
                pt.simplified = True
            break

        # Reduce any segments that makes a triangle whose area is below
        # the minimum threshold, starting with the smallest and working up.
        # Mark segments to be preserved until the next iteration.

        for (area, i) in areas:

            if area > min_area:
                # there won't be any more points to remove.
                break

            if i - 1 in preserved or i + 1 in preserved:
                # the current segment is too close to a previously-preserved one.
                #print "-pre", preserved
                continue

            points[pts[i]].deleted = True
            popped.append(i)

            # make sure that the adjacent points
            preserved.add(i - 1)
            preserved.add(i + 1)

        if len(popped) == 0:
            # no points removed, so break out of loop
            break

        popped = sorted(popped, reverse=True)
        for i in popped:
            # remove point from index list
            pts = pts[:i] + pts[i + 1:]

    for pt in points:
        pt.simplified = True


def _tri_area(x1, y1, x2, y2, x3, y3):
    """
    computes the area of a triangle given by three points
    implementation taken from:
    http://www.btinternet.com/~se16/hgb/triangle.htm
    """
    return abs((x2*y1-x1*y2)+(x3*y2-x2*y3)+(x1*y3-x3*y1))/2.0

########NEW FILE########
__FILENAME__ = yaml_ordered_dict
import yaml
import yaml.constructor

try:
    # included in standard lib from Python 2.7
    from collections import OrderedDict
except ImportError:
    # try importing the backported drop-in replacement
    # it's available on PyPI
    from ordereddict import OrderedDict


class OrderedDictYAMLLoader(yaml.Loader):
    """
    A YAML loader that loads mappings into ordered dictionaries
    (taken from: https://gist.github.com/844388)
    """

    def __init__(self, *args, **kwargs):
        yaml.Loader.__init__(self, *args, **kwargs)

        self.add_constructor(u'tag:yaml.org,2002:map', type(self).construct_yaml_map)
        self.add_constructor(u'tag:yaml.org,2002:omap', type(self).construct_yaml_map)

    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(None, None,
                'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise yaml.constructor.ConstructorError('while constructing a mapping',
                    node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

if __name__ == '__main__':
    import textwrap

    sample = """
one:
    two: fish
    red: fish
    blue: fish
two:
    a: yes
    b: no
    c: null
"""

    data = yaml.load(textwrap.dedent(sample), OrderedDictYAMLLoader)
    assert type(data) is OrderedDict
    print data
########NEW FILE########
__FILENAME__ = run_tests
from kartograph import Kartograph
import sys
from os import mkdir, remove
from os.path import exists, splitext, basename
from glob import glob
from kartograph.options import read_map_config

for path in ('data', 'results'):
    if not exists(path):
        mkdir(path)

if not exists('data/ne_50m_admin_0_countries.shp'):
    # download natural earth shapefile
    print 'I need a shapefile to test with. Will download one from naturalearthdata.com\n'
    from subprocess import call
    call(['wget', 'http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/50m/cultural/ne_50m_admin_0_countries.zip'])
    print '\nUnzipping...\n'
    call(['unzip', 'ne_50m_admin_0_countries.zip', '-d', 'data'])

passed = 0
failed = 0

log = open('log.txt', 'w')

for fn in glob('configs/*.*'):
    fn_parts = splitext(basename(fn))
    print 'running text', basename(fn), '...',
    try:
        cfg = read_map_config(open(fn))
        K = Kartograph()
        css_url = 'styles/' + fn_parts[0] + '.css'
        css = None
        if exists(css_url):
            css = open(css_url).read()
        svg_url = 'results/' + fn_parts[0] + '.svg'
        if exists(svg_url):
            remove(svg_url)
        K.generate(cfg, 'results/' + fn_parts[0] + '.svg', preview=False, format='svg', stylesheet=css)
        print 'ok.'
        passed += 1
    except Exception, e:
        import traceback
        ignore_path_len = len(__file__) - 7
        exc = sys.exc_info()
        log.write('\n\nError in test %s' % fn)
        for (filename, line, func, code) in traceback.extract_tb(exc[2]):
            log.write('  %s, in %s()\n  %d: %s\n' % (filename, func, line, code))
        log.write('\n')
        log.write(str(e))
        print 'failed.'
        failed += 1

print 'passed: %d\nfailed: %d' % (passed, failed)

########NEW FILE########
