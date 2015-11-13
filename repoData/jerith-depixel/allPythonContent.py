__FILENAME__ = bspline
# -*- test-case-name: depixel.tests.test_bspline -*-

"""
This is a limited quadratic B-spline library.

The mathematics mostly comes from some excellent course notes on the web:

http://www.cs.mtu.edu/~shene/COURSES/cs3621/NOTES/

More specifically, De Boor's Algorithm is at:

http://www.cs.mtu.edu/~shene/COURSES/cs3621/NOTES/spline/B-spline/de-Boor.html

Errors are likely due to my lack of understanding rather than any deficiency in
the source material. I don't completely understand the underlying theory, so I
may have done something silly. However, my tests seem to do the right thing.
"""

import random
from math import sqrt, sin, cos, pi


class Point(object):
    """More convenient than using tuples everywhere.

    This implementation uses complex numbers under the hood, but that shouldn't
    really matter anywhere else.
    """
    def __init__(self, value):
        if isinstance(value, complex):
            self.value = value
        elif isinstance(value, (tuple, list)):
            self.value = value[0] + value[1] * 1j
        elif isinstance(value, Point):
            self.value = value.value
        else:
            raise ValueError("Invalid value for Point: %r" % (value,))

    def __str__(self):
        return "<Point (%s, %s)>" % (self.x, self.y)

    def __repr__(self):
        return str(self)

    @property
    def x(self):
        return self.value.real

    @property
    def y(self):
        return self.value.imag

    @property
    def tuple(self):
        return (self.x, self.y)

    def _op(self, op, other):
        if isinstance(other, Point):
            other = other.value
        return Point(getattr(self.value, op)(other))

    def __eq__(self, other):
        try:
            other = Point(other).value
        except ValueError:
            pass
        return self.value.__eq__(other)

    def __add__(self, other):
        return self._op('__add__', other)

    def __radd__(self, other):
        return self._op('__radd__', other)

    def __sub__(self, other):
        return self._op('__sub__', other)

    def __rsub__(self, other):
        return self._op('__rsub__', other)

    def __mul__(self, other):
        return self._op('__mul__', other)

    def __rmul__(self, other):
        return self._op('__rmul__', other)

    def __div__(self, other):
        return self._op('__div__', other)

    def __rdiv__(self, other):
        return self._op('__rdiv__', other)

    def __abs__(self):
        return abs(self.value)

    def round(self, places=5):
        return Point((round(self.x, places), round(self.y, places)))


class BSpline(object):
    """
    This is made out of mathematics. You have been warned.

    A B-spline has:
      * n + 1 control points
      * m + 1 knots
      * degree p
      * m = n + p + 1
    """
    def __init__(self, knots, points, degree=None):
        self.knots = tuple(knots)
        self._points = [Point(p) for p in points]
        expected_degree = len(self.knots) - len(self._points) - 1
        if degree is None:
            degree = expected_degree
        if degree != expected_degree:
            raise ValueError("Expected degree %s, got %s." % (
                expected_degree, degree))
        self.degree = degree
        self._reset_cache()

    def _reset_cache(self):
        self._cache = {}

    def move_point(self, i, value):
        self._points[i] = value
        self._reset_cache()

    def __str__(self):
        return "<%s degree=%s, points=%s, knots=%s>" % (
            type(self).__name__,
            self.degree, len(self.points), len(self.knots))

    def copy(self):
        return type(self)(self.knots, self.points, self.degree)

    @property
    def domain(self):
        return (self.knots[self.degree],
                self.knots[len(self.knots) - self.degree - 1])

    @property
    def points(self):
        return tuple(self._points)

    @property
    def useful_points(self):
        return self.points

    def __call__(self, u):
        """
        De Boor's Algorithm. Made out of more maths.
        """
        s = len([uk for uk in self.knots if uk == u])
        for k, uk in enumerate(self.knots):
            if uk >= u:
                break
        if s == 0:
            k -= 1
        if self.degree == 0:
            if k == len(self.points):
                k -= 1
            return self.points[k]
        ps = [dict(zip(range(k - self.degree, k - s + 1),
                       self.points[k - self.degree:k - s + 1]))]

        for r in range(1, self.degree - s + 1):
            ps.append({})
            for i in range(k - self.degree + r, k - s + 1):
                a = (u - self.knots[i]) / (self.knots[i + self.degree - r + 1]
                                           - self.knots[i])
                ps[r][i] = (1 - a) * ps[r - 1][i - 1] + a * ps[r - 1][i]
        return ps[-1][k - s]

    def quadratic_bezier_segments(self):
        """
        Extract a sequence of quadratic Bezier curves making up this spline.

        NOTE: This assumes our spline is quadratic.
        """
        assert self.degree == 2
        control_points = self.points[1:-1]
        on_curve_points = [self(u) for u in self.knots[2:-2]]
        ocp0 = on_curve_points[0]
        for cp, ocp1 in zip(control_points, on_curve_points[1:]):
            yield (ocp0.tuple, cp.tuple, ocp1.tuple)
            ocp0 = ocp1

    def derivative(self):
        """
        Take the derivative.
        """
        cached = self._cache.get('derivative')
        if cached:
            return cached

        new_points = []
        p = self.degree
        for i in range(0, len(self.points) - 1):
            coeff = p / (self.knots[i + 1 + p] - self.knots[i + 1])
            new_points.append(coeff * (self.points[i + 1] - self.points[i]))

        cached = BSpline(self.knots[1:-1], new_points, p - 1)
        self._cache['derivative'] = cached
        return cached

    def _clamp_domain(self, value):
        return max(self.domain[0], min(self.domain[1], value))

    def _get_span(self, index):
        return (self._clamp_domain(self.knots[index]),
                self._clamp_domain(self.knots[index + 1]))

    def _get_point_spans(self, index):
        return [self._get_span(index + i) for i in range(self.degree)]

    def integrate_over_span(self, func, span, intervals):
        if span[0] == span[1]:
            return 0

        interval = (span[1] - span[0]) / intervals
        result = (func(span[0]) + func(span[1])) / 2
        for i in xrange(1, intervals):
            result += func(span[0] + i * interval)
        result *= interval

        return result

    def integrate_for(self, index, func, intervals):
        spans_ = self._get_point_spans(index)
        spans = [span for span in spans_ if span[0] != span[1]]
        return sum(self.integrate_over_span(func, span, intervals)
                   for span in spans)

    def curvature(self, u):
        d1 = self.derivative()(u)
        d2 = self.derivative().derivative()(u)
        num = d1.x * d2.y - d1.y * d2.x
        den = sqrt(d1.x ** 2 + d1.y ** 2) ** 3
        if den == 0:
            return 0
        return abs(num / den)

    def curvature_energy(self, index, intervals_per_span):
        return self.integrate_for(index, self.curvature, intervals_per_span)

    def reversed(self):
        return type(self)(
            (1 - k for k in reversed(self.knots)), reversed(self._points),
            self.degree)


class ClosedBSpline(BSpline):
    def __init__(self, knots, points, degree=None):
        super(ClosedBSpline, self).__init__(knots, points, degree)
        self._unwrapped_len = len(self._points) - self.degree
        self._check_wrapped()

    def _check_wrapped(self):
        if self._points[:self.degree] != self._points[-self.degree:]:
            raise ValueError(
                "Points not wrapped at degree %s." % (self.degree,))

    def move_point(self, index, value):
        if not 0 <= index < len(self._points):
            raise IndexError(index)
        index = index % self._unwrapped_len
        super(ClosedBSpline, self).move_point(index, value)
        if index < self.degree:
            super(ClosedBSpline, self).move_point(
                index + self._unwrapped_len, value)

    @property
    def useful_points(self):
        return self.points[:-self.degree]

    def _get_span(self, index):
        span = lambda i: (self.knots[i], self.knots[i + 1])
        d0, d1 = span(index)
        if d0 < self.domain[0]:
            d0, d1 = span(index + len(self.points) - self.degree)
        elif d1 > self.domain[1]:
            d0, d1 = span(index + self.degree - len(self.points))
        return self._clamp_domain(d0), self._clamp_domain(d1)


def polyline_to_closed_bspline(path, degree=2):
    """
    Make a closed B-spline from a path through some nodes.
    """

    points = path + path[:degree]
    m = len(points) + degree
    knots = [float(i) / m for i in xrange(m + 1)]

    return ClosedBSpline(knots, points, degree)


def magnitude(point):
    return sqrt(point[0] ** 2 + point[2] ** 2)


class SplineSmoother(object):
    INTERVALS_PER_SPAN = 20
    POINT_GUESSES = 20
    GUESS_OFFSET = 0.05
    ITERATIONS = 20
    POSITIONAL_ENERGY_MULTIPLIER = 1

    # INTERVALS_PER_SPAN = 5
    # POINT_GUESSES = 1
    # ITERATIONS = 1

    def __init__(self, spline):
        self.orig = spline
        self.spline = spline.copy()

    def _e_curvature(self, index):
        return self.spline.curvature_energy(index, self.INTERVALS_PER_SPAN)

    def _e_positional(self, index):
        orig = self.orig.points[index]
        point = self.spline.points[index]
        e_positional = abs(point - orig) ** 4
        return e_positional * self.POSITIONAL_ENERGY_MULTIPLIER

    def point_energy(self, index):
        e_curvature = self._e_curvature(index)
        e_positional = self._e_positional(index)
        return e_positional + e_curvature

    def _rand(self):
        offset = random.random() * self.GUESS_OFFSET
        angle = random.random() * 2 * pi
        return offset * Point((cos(angle), sin(angle)))

    def smooth_point(self, index, start):
        energies = [(self.point_energy(index), start)]
        for _ in range(self.POINT_GUESSES):
            point = start + self._rand()
            self.spline.move_point(index, point)
            energies.append((self.point_energy(index), point))
        self.spline.move_point(index, min(energies)[1])

    def smooth(self):
        for _it in range(self.ITERATIONS):
            # print "IT:", _it
            for i, point in enumerate(self.spline.useful_points):
                self.smooth_point(i, point)


def smooth_spline(spline):
    smoother = SplineSmoother(spline)
    smoother.smooth()
    return smoother.spline

########NEW FILE########
__FILENAME__ = depixeler
# -*- test-case-name: depixel.tests.test_depixeler -*-

"""
An implementation of the Depixelizing Pixel Art algorithm.

The paper can be found online at:
    http://research.microsoft.com/en-us/um/people/kopf/pixelart/
"""

from math import sqrt

import networkx as nx

from depixel import bspline


def gen_coords(size):
    for y in xrange(size[1]):
        for x in xrange(size[0]):
            yield (x, y)


def within_bounds(coord, size, offset=(0, 0)):
    x, y = map(sum, zip(coord, offset))
    size_x, size_y = size
    return (0 <= x < size_x and 0 <= y < size_y)


def cn_edge(edge):
    return tuple(sorted(edge[:2]))


def distance(p0, p1):
    return sqrt((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2)


def gradient(p0, p1):
    # Assume the constant below is big enough. Bleh.
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if dx == 0:
        return dy * 99999999999999
    return 1.0 * dy / dx


def remove_from_set(things, thing):
    things.add(thing)
    things.remove(thing)


class DiagonalResolutionHeuristics(object):
    SPARSE_WINDOW_SIZE = (8, 8)

    def __init__(self, pixel_graph):
        self.pixel_graph = pixel_graph

    def sparse_window_offset(self, edge):
        return (
            self.SPARSE_WINDOW_SIZE[0] / 2 - 1 - min((edge[0][0], edge[1][0])),
            self.SPARSE_WINDOW_SIZE[1] / 2 - 1 - min((edge[0][1], edge[1][1])))

    def apply(self, blocks):
        raise NotImplementedError()


class FullyConnectedHeuristics(DiagonalResolutionHeuristics):
    def apply(self, diagonal_pairs):
        """
        Iterate over the set of ambiguous diagonals and resolve them.
        """
        for edges in diagonal_pairs:
            self.weight_diagonals(*edges)

        for edges in diagonal_pairs:
            min_weight = min(e[2]['h_weight'] for e in edges)
            for edge in edges:
                if edge[2]['h_weight'] == min_weight:
                    self.pixel_graph.remove_edge(*edge[:2])
                else:
                    edge[2].pop('h_weight')

    def weight_diagonals(self, edge1, edge2):
        """
        Apply heuristics to ambiguous diagonals.
        """
        for edge in (edge1, edge2):
            self.weight_diagonal(edge)

    def weight_diagonal(self, edge):
        """
        Apply heuristics to an ambiguous diagonal.
        """
        weights = [
            self.weight_curve(edge),
            self.weight_sparse(edge),
            self.weight_island(edge),
            ]
        edge[2]['h_weight'] = sum(weights)

    def weight_curve(self, edge):
        """
        Weight diagonals based on curve length.

        Edges that are part of long single-pixel-wide features are
        more likely to be important.
        """
        seen_edges = set([cn_edge(edge)])
        nodes = list(edge[:2])

        while nodes:
            node = nodes.pop()
            edges = self.pixel_graph.edges(node, data=True)
            if len(edges) != 2:
                # This node is not part of a curve
                continue
            for edge in edges:
                edge = cn_edge(edge)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    nodes.extend(n for n in edge if n != node)
        return len(seen_edges)

    def weight_sparse(self, edge):
        """
        Weight diagonals based on feature sparseness.

        Sparse features are more likely to be seen as "foreground"
        rather than "background", and are therefore likely to be more
        important.
        """

        nodes = list(edge[:2])
        seen_nodes = set(nodes)
        offset = self.sparse_window_offset(edge)

        while nodes:
            node = nodes.pop()
            for n in self.pixel_graph.neighbors(node):
                if n in seen_nodes:
                    continue
                if within_bounds(n, self.SPARSE_WINDOW_SIZE, offset=offset):
                    seen_nodes.add(n)
                    nodes.append(n)

        return -len(seen_nodes)

    def weight_island(self, edge):
        """
        Weight diagonals connected to "islands".

        Single pixels connected to nothing except the edge being
        examined are likely to be more important.
        """
        if (len(self.pixel_graph[edge[0]]) == 1
            or len(self.pixel_graph[edge[1]]) == 1):
            return 5
        return 0


class IterativeFinalShapeHeuristics(DiagonalResolutionHeuristics):
    def apply(self, diagonal_pairs):
        """
        Iterate over the set of ambiguous diagonals and resolve them.
        """
        new_pairs = []

        for edges in diagonal_pairs:
            for edge in edges:
                edge[2]['ambiguous'] = True

        for edges in diagonal_pairs:
            removals = self.weight_diagonals(*edges)
            if removals is None:
                # Nothing to remove, so we're still ambiguous.
                new_pairs.append(edges)
                continue

            for edge in edges:
                if edge in removals:
                    # Remove this edge
                    self.pixel_graph.remove_edge(edge[0], edge[1])
                else:
                    # Clean up other edges
                    edge[2].pop('h_weight')
                    edge[2].pop('ambiguous')

        # Reiterate if necessary.
        if not new_pairs:
            # Nothing more to do, let's go home.
            return
        elif new_pairs == diagonal_pairs:
            # No more unambiguous pairs.
            # TODO: Handle this gracefully.
            raise ValueError("No more unambiguous blocks.")
        else:
            # Try again.
            self.apply(new_pairs)

    def weight_diagonals(self, edge1, edge2):
        """
        Apply heuristics to ambiguous diagonals.
        """
        for edge in (edge1, edge2):
            self.weight_diagonal(edge)

        favour1 = edge1[2]['h_weight'][1] - edge2[2]['h_weight'][0]
        favour2 = edge1[2]['h_weight'][0] - edge2[2]['h_weight'][1]

        if favour1 == 0 and favour2 == 0:
            # Unambiguous, remove both.
            return (edge1, edge2)
        if favour1 >= 0 and favour2 >= 0:
            # Unambiguous, edge1 wins.
            return (edge2,)
        if favour1 <= 0 and favour2 <= 0:
            # Unambiguous, edge2 wins.
            return (edge1,)
        # We have an ambiguous result.
        return None

    def weight_diagonal(self, edge):
        """
        Apply heuristics to an ambiguous diagonal.
        """
        weights = [
            self.weight_curve(edge),
            self.weight_sparse(edge),
            self.weight_island(edge),
            ]
        edge[2]['h_weight'] = tuple(sum(w) for w in zip(*weights))

    def weight_curve(self, edge):
        """
        Weight diagonals based on curve length.

        Edges that are part of long single-pixel-wide features are
        more likely to be important.
        """
        seen_edges = set([cn_edge(edge)])
        nodes = list(edge[:2])

        values = list(self._weight_curve(nodes, seen_edges))
        retvals = (min(values), max(values))
        return retvals

    def _weight_curve(self, nodes, seen_edges):
        while nodes:
            node = nodes.pop()
            edges = self.pixel_graph.edges(node, data=True)
            if len(edges) != 2:
                # This node is not part of a curve
                continue
            for edge in edges:
                ambiguous = ('ambiguous' in edge[2])
                edge = cn_edge(edge)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    if ambiguous:
                        for v in self._weight_curve(
                                nodes[:], seen_edges.copy()):
                            yield v
                    nodes.extend(n for n in edge if n != node)
        yield len(seen_edges)

    def weight_sparse(self, edge):
        """
        Weight diagonals based on feature sparseness.

        Sparse features are more likely to be seen as "foreground"
        rather than "background", and are therefore likely to be more
        important.
        """
        offset = self.sparse_window_offset(edge)
        nodes = list(edge[:2])
        seen_nodes = set(nodes)

        values = list(self._weight_sparse(offset, nodes, seen_nodes))
        retvals = (min(values), max(values))
        return retvals

    def _weight_sparse(self, offset, nodes, seen_nodes):
        while nodes:
            node = nodes.pop()
            for n in self.pixel_graph.neighbors(node):
                if n in seen_nodes:
                    continue
                if 'ambiguous' in self.pixel_graph[node][n]:
                    for v in self._weight_sparse(
                            offset, nodes[:], seen_nodes.copy()):
                        yield v
                if within_bounds(n, self.SPARSE_WINDOW_SIZE, offset):
                    seen_nodes.add(n)
                    nodes.append(n)

        yield -len(seen_nodes)

    def weight_island(self, edge):
        """
        Weight diagonals connected to "islands".

        Single pixels connected to nothing except the edge being
        examined are likely to be more important.
        """
        if (len(self.pixel_graph[edge[0]]) == 1
            or len(self.pixel_graph[edge[1]]) == 1):
            return (5, 5)
        return (0, 0)


class PixelData(object):
    """
    A representation of a pixel image that knows how to depixel it.

    :param data: A 2d array of pixel values. It is assumed to be rectangular.
    """

    HEURISTICS = FullyConnectedHeuristics
    # HEURISTICS = IterativeFinalShapeHeuristics

    def __init__(self, pixels):
        self.pixels = pixels
        self.size_x = len(pixels[0])
        self.size_y = len(pixels)
        self.size = (self.size_x, self.size_y)

    def depixel(self):
        """
        Depixel the image.

        TODO: document.
        """
        self.make_pixel_graph()
        self.remove_diagonals()
        self.make_grid_graph()
        self.deform_grid()
        self.make_shapes()
        self.isolate_outlines()
        self.add_shape_outlines()
        self.smooth_splines()

    def pixel(self, x, y):
        """
        Convenience method for getting a pixel value.
        """
        return self.pixels[y][x]

    def make_grid_graph(self):
        """
        Build a graph representing the pixel grid.
        """
        self.grid_graph = nx.grid_2d_graph(self.size_x + 1, self.size_y + 1)

    def make_pixel_graph(self):
        """
        Build a graph representing the pixel data.
        """
        self.pixel_graph = nx.Graph()

        for x, y in gen_coords(self.size):
            # While the nodes are created by adding edges, adding them
            # again is safe and lets us easily update metadata.
            corners = set([(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)])
            self.pixel_graph.add_node((x, y),
                                      value=self.pixel(x, y), corners=corners)
            # This gets called on each node, so we don't have to duplicate
            # edges.
            self._add_pixel_edge((x, y), (x + 1, y))
            self._add_pixel_edge((x, y), (x, y + 1))
            self._add_pixel_edge((x, y), (x + 1, y - 1))
            self._add_pixel_edge((x, y), (x + 1, y + 1))

    def _add_pixel_edge(self, pix0, pix1):
        """
        Add an edge to the pixel graph, checking bounds and tagging diagonals.
        """
        if within_bounds(pix1, self.size) and self.match(pix0, pix1):
            attrs = {'diagonal': pix0[0] != pix1[0] and pix0[1] != pix1[1]}
            self.pixel_graph.add_edge(pix0, pix1, **attrs)

    def match(self, pix0, pix1):
        """
        Check if two pixels match. By default, this tests equality.
        """
        return self.pixel(*pix0) == self.pixel(*pix1)

    def remove_diagonals(self):
        """
        Remove all unnecessary diagonals and resolve checkerboard features.

        We examine all 2x2 pixel blocks and check for overlapping diagonals.
        The only cases in which diagonals will overlap are fully-connected
        blocks (in which both diagonals can be removed) and checkerboard blocks
        (in which we need to apply heuristics to determine which diagonal to
        remove). See the paper for details.
        """
        ambiguous_diagonal_pairs = []

        for nodes in self.walk_pixel_blocks(2):
            edges = [e for e in self.pixel_graph.edges(nodes, data=True)
                     if e[0] in nodes and e[1] in nodes]

            diagonals = [e for e in edges if e[2]['diagonal']]
            if len(diagonals) == 2:
                if len(edges) == 6:
                    # We have a fully-connected block, so remove all diagonals.
                    for edge in diagonals:
                        self.pixel_graph.remove_edge(edge[0], edge[1])
                elif len(edges) == 2:
                    # We have an ambiguous pair to resolve.
                    ambiguous_diagonal_pairs.append(edges)
                else:
                    # If we get here, we have an invalid graph, possibly due to
                    # a faulty match function.
                    assert False, "Unexpected diagonal layout"

        self.apply_diagonal_heuristics(ambiguous_diagonal_pairs)

    def apply_diagonal_heuristics(self, ambiguous_diagonal_pairs):
        self.HEURISTICS(self.pixel_graph).apply(ambiguous_diagonal_pairs)

    def walk_pixel_blocks(self, size):
        """
        Walk the pixel graph in block of NxN pixels.

        This is useful for operating on a group of nodes at once.
        """
        for x, y in gen_coords((self.size_x - size + 1,
                                self.size_y - size + 1)):
            yield [(x + dx, y + dy)
                   for dx in range(size) for dy in range(size)]

    def deform_grid(self):
        """
        Deform the pixel grid based on the connections between similar pixels.
        """
        for node in self.pixel_graph.nodes_iter():
            self.deform_pixel(node)

        # Collapse all valence-2 nodes.
        removals = []
        for node in self.grid_graph.nodes_iter():
            if node in ((0, 0), (0, self.size[1]),
                        (self.size[0], 0), self.size):
                # Skip corner nodes.
                continue
            neighbors = self.grid_graph.neighbors(node)
            if len(neighbors) == 2:
                self.grid_graph.add_edge(*neighbors)
            if len(neighbors) <= 2:
                removals.append(node)

        # We can't do this above, because it would modify the dict
        # we're iterating.
        for node in removals:
            self.grid_graph.remove_node(node)

        # Update pixel corner sets.
        for node, attrs in self.pixel_graph.nodes_iter(data=True):
            corners = attrs['corners']
            for corner in corners.copy():
                if corner not in self.grid_graph:
                    corners.remove(corner)

    def deform_pixel(self, node):
        """
        Deform an individual pixel.
        """
        for neighbor in self.pixel_graph.neighbors(node):
            if node[0] == neighbor[0] or node[1] == neighbor[1]:
                # We only care about diagonals.
                continue
            px_x = max(neighbor[0], node[0])
            px_y = max(neighbor[1], node[1])
            pixnode = (px_x, px_y)
            offset_x = neighbor[0] - node[0]
            offset_y = neighbor[1] - node[1]
            # There's probably a better way to do this.
            adj_node = (neighbor[0], node[1])
            if not self.match(node, adj_node):
                pn = (px_x, px_y - offset_y)
                mpn = (px_x, px_y - 0.5 * offset_y)
                npn = (px_x + 0.25 * offset_x, px_y - 0.25 * offset_y)
                remove_from_set(self.pixel_corners(adj_node), pixnode)
                self.pixel_corners(adj_node).add(npn)
                self.pixel_corners(node).add(npn)
                self._deform(pixnode, pn, mpn, npn)
            adj_node = (node[0], neighbor[1])
            if not self.match(node, adj_node):
                pn = (px_x - offset_x, px_y)
                mpn = (px_x - 0.5 * offset_x, px_y)
                npn = (px_x - 0.25 * offset_x, px_y + 0.25 * offset_y)
                remove_from_set(self.pixel_corners(adj_node), pixnode)
                self.pixel_corners(adj_node).add(npn)
                self.pixel_corners(node).add(npn)
                self._deform(pixnode, pn, mpn, npn)

    def pixel_corners(self, pixel):
        return self.pixel_graph.node[pixel]['corners']

    def _deform(self, pixnode, pn, mpn, npn):
        # Do the node and edge shuffling.
        if mpn in self.grid_graph:
            self.grid_graph.remove_edge(mpn, pixnode)
        else:
            self.grid_graph.remove_edge(pn, pixnode)
            self.grid_graph.add_edge(pn, mpn)
        self.grid_graph.add_edge(mpn, npn)
        self.grid_graph.add_edge(npn, pixnode)

    def make_shapes(self):
        self.shapes = set()

        for pcg in nx.connected_component_subgraphs(self.pixel_graph):
            pixels = set()
            value = None
            corners = set()
            for pixel, attrs in pcg.nodes_iter(data=True):
                pixels.add(pixel)
                corners.update(attrs['corners'])
                value = attrs['value']
            self.shapes.add(Shape(pixels, value, corners))

    def isolate_outlines(self):
        # Remove internal edges from a copy of our pixgrid graph.
        self.outlines_graph = nx.Graph(self.grid_graph)
        for pixel, attrs in self.pixel_graph.nodes_iter(data=True):
            corners = attrs['corners']
            for neighbor in self.pixel_graph.neighbors(pixel):
                edge = corners & self.pixel_graph.node[neighbor]['corners']
                if len(edge) != 2:
                    print edge
                if self.outlines_graph.has_edge(*edge):
                    self.outlines_graph.remove_edge(*edge)
        for node in nx.isolates(self.outlines_graph):
            self.outlines_graph.remove_node(node)

    def make_path(self, graph):
        path = Path(graph)
        key = path.key()
        if key not in self.paths:
            self.paths[key] = path
            path.make_spline()
        return self.paths[key]

    def add_shape_outlines(self):
        self.paths = {}

        for shape in self.shapes:
            sg = self.outlines_graph.subgraph(shape.corners)
            for graph in nx.connected_component_subgraphs(sg):
                path = self.make_path(graph)
                if (min(graph.nodes()) == min(sg.nodes())):
                    shape.add_outline(path, True)
                else:
                    shape.add_outline(path)

    def smooth_splines(self):
        print "Smoothing splines..."
        for i, path in enumerate(self.paths.values()):
            print " * %s/%s (%s, %s)..." % (
                i + 1, len(self.paths), len(path.shapes), len(path.path))
            if len(path.shapes) == 1:
                path.smooth = path.spline.copy()
                continue
            path.smooth_spline()


class Shape(object):
    def __init__(self, pixels, value, corners):
        self.pixels = pixels
        self.value = value
        self.corners = corners
        self._outside_path = None
        self._inside_paths = []

    def _paths_attr(self, attr):
        paths = [list(reversed(getattr(self._outside_path, attr)))]
        paths.extend(getattr(path, attr) for path in self._inside_paths)

    @property
    def paths(self):
        paths = [list(reversed(self._outside_path.path))]
        paths.extend(path.path for path in self._inside_paths)
        return paths

    @property
    def splines(self):
        paths = [self._outside_path.spline.reversed()]
        paths.extend(path.spline for path in self._inside_paths)
        return paths

    @property
    def smooth_splines(self):
        paths = [self._outside_path.smooth.reversed()]
        paths.extend(path.smooth for path in self._inside_paths)
        return paths

    def add_outline(self, path, outside=False):
        if outside:
            self._outside_path = path
        else:
            self._inside_paths.append(path)
        path.shapes.add(self)


class Path(object):
    def __init__(self, shape_graph):
        self.path = self._make_path(shape_graph)
        self.shapes = set()

    def key(self):
        return tuple(self.path)

    def _make_path(self, shape_graph):
        # Find initial nodes.
        nodes = set(shape_graph.nodes())
        path = [min(nodes)]
        neighbors = sorted(shape_graph.neighbors(path[0]),
                           key=lambda p: gradient(path[0], p))
        path.append(neighbors[0])
        nodes.difference_update(path)

        # Walk rest of nodes.
        while nodes:
            for neighbor in shape_graph.neighbors(path[-1]):
                if neighbor in nodes:
                    nodes.remove(neighbor)
                    path.append(neighbor)
                    break
        return path

    def make_spline(self):
        self.spline = bspline.polyline_to_closed_bspline(self.path)

    def smooth_spline(self):
        self.smooth = bspline.smooth_spline(self.spline)

########NEW FILE########
__FILENAME__ = io_data
"""
Unified I/O module for reading and writing various formats.
"""

import os.path
from itertools import product


def gradient(p0, p1):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if dx == 0:
        return dy * 99999999999999
    return 1.0 * dy / dx


class PixelDataWriter(object):
    PIXEL_SCALE = 40
    GRID_COLOUR = (255, 127, 0)

    FILE_EXT = 'out'

    def __init__(self, pixel_data, name, scale=None, gridcolour=None):
        self.name = name
        self.pixel_data = pixel_data
        if scale:
            self.PIXEL_SCALE = scale
        if gridcolour:
            self.GRID_COLOUR = gridcolour

    def scale_pt(self, pt, offset=(0, 0)):
        return tuple(int((n + o) * self.PIXEL_SCALE)
                     for n, o in zip(pt, offset))

    def export_pixels(self, outdir):
        filename = self.mkfn(outdir, 'pixels')
        drawing = self.make_drawing('pixels', filename)
        for pt in product(range(self.pixel_data.size_x),
                          range(self.pixel_data.size_y)):
            self.draw_pixel(drawing, pt, self.pixel_data.pixel(*pt))
        self.save_drawing(drawing, filename)

    def export_grid(self, outdir, node_graph=True):
        filename = self.mkfn(outdir, 'grid')
        drawing = self.make_drawing('grid', filename)
        self.draw_pixgrid(drawing)
        if node_graph:
            self.draw_nodes(drawing)
        self.save_drawing(drawing, filename)

    def export_shapes(self, outdir, node_graph=True):
        filename = self.mkfn(outdir, 'shapes')
        drawing = self.make_drawing('shapes', filename)
        self.draw_shapes(drawing, 'splines')
        if node_graph:
            self.draw_nodes(drawing)
        self.save_drawing(drawing, filename)

    def export_smooth(self, outdir, node_graph=True):
        filename = self.mkfn(outdir, 'smooth')
        drawing = self.make_drawing('smooth', filename)
        self.draw_shapes(drawing, 'smooth_splines')
        if node_graph:
            self.draw_nodes(drawing)
        self.save_drawing(drawing, filename)

    def draw_pixgrid(self, drawing):
        for pixel, attrs in self.pixel_data.pixel_graph.nodes_iter(data=True):
            nodes = attrs['corners'].copy()
            path = [nodes.pop()]
            while nodes:
                for neighbor in self.pixel_data.grid_graph.neighbors(path[-1]):
                    if neighbor in nodes:
                        nodes.remove(neighbor)
                        path.append(neighbor)
                        break
            self.draw_polygon(drawing, [self.scale_pt(p) for p in path],
                              self.GRID_COLOUR, attrs['value'])

    def draw_shapes(self, drawing, element='smooth_splines'):
        for shape in self.pixel_data.shapes:
            paths = getattr(shape, element)
            self.draw_spline_shape(
                drawing, paths, self.GRID_COLOUR, shape.value)

    def draw_nodes(self, drawing):
        for edge in self.pixel_data.pixel_graph.edges_iter():
            self.draw_line(drawing,
                           self.scale_pt(edge[0], (0.5, 0.5)),
                           self.scale_pt(edge[1], (0.5, 0.5)),
                           self.edge_colour(edge[0]))

    def edge_colour(self, node):
        return {
            0: (0, 191, 0),
            0.5: (191, 0, 0),
            1: (0, 0, 255),
            (0, 0, 0): (0, 191, 0),
            (127, 127, 127): (191, 0, 0),
            (255, 255, 255): (0, 0, 255),
            }[self.pixel_data.pixel_graph.node[node]['value']]

    def mkfn(self, outdir, drawing_type):
        return os.path.join(
            outdir, "%s_%s.%s" % (drawing_type, self.name, self.FILE_EXT))

    def make_drawing(self, drawing_type, filename):
        raise NotImplementedError("This Writer cannot make a drawing.")

    def save_drawing(self, filename):
        raise NotImplementedError("This Writer cannot save a drawing.")

    def draw_pixel(self, drawing, pt, colour):
        raise NotImplementedError("This Writer cannot draw a pixel.")

    def draw_rect(self, drawing, p0, size, colour, fill):
        raise NotImplementedError("This Writer cannot draw a rect.")

    def draw_line(self, drawing, p0, p1, colour):
        raise NotImplementedError("This Writer cannot draw a line.")

    def draw_path_shape(self, drawing, paths, colour, fill):
        raise NotImplementedError("This Writer cannot draw a path shape.")

    def draw_spline_shape(self, drawing, paths, colour, fill):
        raise NotImplementedError("This Writer cannot draw a spline shape.")


def get_writer(data, basename, filetype):
    # Circular imports, but they're safe because they're in this function.
    if filetype == 'png':
        from depixel import io_png
        return io_png.PixelDataPngWriter(data, basename)

    if filetype == 'svg':
        from depixel import io_svg
        return io_svg.PixelDataSvgWriter(data, basename)

    raise NotImplementedError(
        "I don't recognise '%s' as a file type." % (filetype,))


def read_pixels(filename, filetype=None):
    if filetype is None:
        filetype = os.path.splitext(filename)[-1].lstrip('.')

    if filetype == 'png':
        from depixel.io_png import read_png
        return read_png(filename)

########NEW FILE########
__FILENAME__ = io_png
import png

from depixel.io_data import PixelDataWriter


class Bitmap(object):
    mode = 'RGB'
    bgcolour = (127, 127, 127)

    def __init__(self, size, bgcolour=None, mode=None):
        if bgcolour is not None:
            self.bgcolour = bgcolour
        if mode is not None:
            self.mode = mode
        self.size = size
        self.pixels = []
        for _ in range(self.size[1]):
            self.pixels.append([bgcolour] * self.size[0])

    def set_pixel(self, x, y, value):
        self.pixels[y][x] = value

    def pixel(self, x, y):
        return self.pixels[y][x]

    def set_data(self, data):
        assert len(data) == self.size[1]
        new_pixels = []
        for row in data:
            assert len(row) == self.size[0]
            new_pixels.append(row[:])
        self.pixels = new_pixels

    def set_block(self, x, y, data):
        assert 0 <= x <= (self.size[0] - len(data[0]))
        assert 0 <= y <= (self.size[1] - len(data))
        for dy, row in enumerate(data):
            for dx, value in enumerate(row):
                self.set_pixel(x + dx, y + dy, value)

    def flat_pixels(self):
        flat_pixels = []
        for row in self.pixels:
            frow = []
            for value in row:
                frow.extend(value)
            flat_pixels.append(frow)
        return flat_pixels

    def write_png(self, filename):
        png.from_array(self.flat_pixels(), mode=self.mode).save(filename)

    def draw_line(self, p0, p1, colour):
        """Bresenham's line algorithm."""

        x0, y0 = p0
        x1, y1 = p1
        dx = abs(x0 - x1)
        dy = abs(y0 - y1)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while (x0, y0) != (x1, y1):
            self.set_pixel(x0, y0, colour)
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += + sx
            if e2 < dx:
                err += dx
                y0 += sy
        self.set_pixel(x1, y1, colour)

    def fill(self, point, colour):
        old_colour = self.pixels[point[1]][point[0]]
        if old_colour == colour:
            return
        self.fill_scan(point, old_colour, colour)

    def fill_pix(self, point, old_colour, colour):
        """
        Pixel flood-fill. Reliable, but slow.
        """
        to_fill = [point]
        while to_fill:
            x, y = to_fill.pop()
            self.set_pixel(x, y, colour)
            for nx, ny in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
                if 0 <= nx < self.size[0] and 0 <= ny < self.size[1]:
                    if self.pixels[ny][nx] == old_colour:
                        to_fill.append((nx, ny))

    def fill_scan(self, point, old_colour, colour):
        """
        Scanline flood-fill. Fast, but I'm not entirely sure what it's doing.
        """
        to_fill = [point]
        while to_fill:
            x, y = to_fill.pop()
            while y > 0 and self.pixel(x, y - 1) == old_colour:
                y -= 1
            lspan = False
            rspan = False
            while y < self.size[1] and self.pixel(x, y) == old_colour:
                self.set_pixel(x, y, colour)

                if not lspan and x > 0 and self.pixel(x - 1, y) == old_colour:
                    to_fill.append((x - 1, y))
                    lspan = True
                elif lspan and x > 0 and self.pixel(x - 1, y) == old_colour:
                    lspan = False

                if (not rspan and x < self.size[0] - 1
                      and self.pixel(x + 1, y) == old_colour):
                    to_fill.append((x + 1, y))
                    rspan = True
                elif (rspan and x < self.size[0] - 1
                      and self.pixel(x + 1, y) == old_colour):
                    rspan = False

                y += 1


class PixelDataPngWriter(PixelDataWriter):
    FILE_EXT = 'png'

    def translate_pixel(self, pixel):
        if not isinstance(pixel, (list, tuple)):
            # Assume monochrome values normalised to [0, 1].
            return (int(255 * pixel),) * 3
        return pixel

    def make_drawing(self, drawing_type, _filename):
        if drawing_type == 'pixels':
            return Bitmap(self.pixel_data.size)
        return Bitmap((self.pixel_data.size_x * self.PIXEL_SCALE + 1,
                       self.pixel_data.size_y * self.PIXEL_SCALE + 1),
                      bgcolour=(127, 127, 127))

    def save_drawing(self, drawing, filename):
        drawing.write_png(filename)

    def draw_pixel(self, drawing, pt, colour):
        drawing.set_pixel(pt[0], pt[1], self.translate_pixel(colour))

    def draw_line(self, drawing, pt0, pt1, colour):
        drawing.draw_line(pt0, pt1, self.translate_pixel(colour))

    def draw_polygon(self, drawing, path, colour, fill):
        pt0 = path[-1]
        for pt1 in path:
            self.draw_line(drawing, pt0, pt1, colour)
            pt0 = pt1
        middle = (sum([p[0] for p in path]) / len(path),
                  sum([p[1] for p in path]) / len(path))
        drawing.fill(middle, fill)

    def draw_path_shape(self, drawing, paths, colour, fill):
        for path in paths:
            pt0 = path[-1]
            for pt1 in path:
                self.draw_line(drawing, pt0, pt1, colour)
                pt0 = pt1
        drawing.fill(self.find_point_within(paths, fill), fill)

    def find_point_within(self, paths, colour):
        for node, attrs in self.pixel_data.pixel_graph.nodes_iter(data=True):
            if colour == attrs['value']:
                pt = self.scale_pt(node, (0.5, 0.5))
                if self.is_inside(pt, paths):
                    return pt

    def is_inside(self, pt, paths):
        if not self._is_inside(pt, paths[0]):
            # Must be inside the "outside" path.
            return False
        for path in paths[1:]:
            if self._is_inside(pt, path):
                # Must be outside the "inside" paths.
                return False
        return True

    def _is_inside(self, pt, path):
        inside = False
        x, y = pt
        x0, y0 = path[-1]
        for x1, y1 in path:
            if (y0 <= y < y1 or y1 <= y < y0) and (x0 <= x or x1 <= x):
                # This crosses our ray.
                if (x1 + float(y - y1) / (y0 - y1) * (x0 - x1)) < x:
                    inside = not inside
            x0, y0 = x1, y1
        return inside

    def draw_shapes(self, drawing, element=None):
        for shape in self.pixel_data.shapes:
            paths = [[self.scale_pt(p) for p in path]
                     for path in shape['paths']]
            self.draw_path_shape(
                drawing, paths, self.GRID_COLOUR, shape['value'])


def read_png(filename):
    _w, _h, pixels, _meta = png.Reader(filename=filename).asRGB8()
    data = []
    for row in pixels:
        d_row = []
        while row:
            d_row.append((row.pop(0), row.pop(0), row.pop(0)))
        data.append(d_row)
    return data

########NEW FILE########
__FILENAME__ = io_svg
from svgwrite import Drawing

from depixel.io_data import PixelDataWriter


def rgb(rgb):
    return "rgb(%s,%s,%s)" % rgb


class PixelDataSvgWriter(PixelDataWriter):
    FILE_EXT = 'svg'
    PIXEL_BORDER = None

    def make_drawing(self, _drawing_type, filename):
        return Drawing(filename)

    def save_drawing(self, drawing, _drawing_type):
        drawing.save()

    def draw_pixel(self, drawing, pt, colour):
        pixel_border = self.PIXEL_BORDER
        if pixel_border is None:
            pixel_border = colour
        drawing.add(drawing.rect(self.scale_pt(pt), self.scale_pt((1, 1)),
                                 stroke=rgb(pixel_border), fill=rgb(colour)))

    def draw_line(self, drawing, pt0, pt1, colour):
        drawing.add(drawing.line(pt0, pt1, stroke=rgb(colour)))

    def draw_polygon(self, drawing, path, colour, fill):
        drawing.add(drawing.polygon(path, stroke=rgb(colour), fill=rgb(fill)))

    def draw_path_shape(self, drawing, paths, colour, fill):
        dpath = []
        for path in paths:
            dpath.append('M')
            dpath.extend(path)
            dpath.append('Z')
        drawing.add(drawing.path(dpath, stroke=rgb(colour), fill=rgb(fill)))

    def draw_spline_shape(self, drawing, splines, colour, fill):
        if fill == (255, 255, 255):
            # Don't draw plain white shapes.
            return
        dpath = []
        for spline in splines:
            bcurves = list(spline.quadratic_bezier_segments())
            dpath.append('M')
            dpath.append(self.scale_pt(bcurves[0][0]))
            for bcurve in bcurves:
                dpath.append('Q')
                dpath.append(self.scale_pt(bcurve[1]))
                dpath.append(self.scale_pt(bcurve[2]))
            dpath.append('Z')
        drawing.add(drawing.path(dpath, stroke=rgb(colour), fill=rgb(fill)))

    def draw_shape(self, drawing, shape):
        self.draw_curve_shape(drawing, shape['splines'],
                              self.GRID_COLOUR, shape['value'])

########NEW FILE########
__FILENAME__ = depixel_png
#!/usr/bin/env python

from optparse import OptionParser
import os.path

from depixel import io_data
from depixel.depixeler import PixelData


def parse_options():
    parser = OptionParser(usage="usage: %prog [options] file [file [...]]")
    parser.add_option('--write-grid', help="Write pixel grid file.",
                      dest="write_grid", action="store_true", default=False)
    parser.add_option('--write-shapes', help="Write object shapes file.",
                      dest="write_shapes", action="store_true", default=False)
    parser.add_option('--write-smooth', help="Write smooth shapes file.",
                      dest="write_smooth", action="store_true", default=False)
    parser.add_option('--no-nodes', help="Suppress pixel node graph output.",
                      dest="draw_nodes", action="store_false", default=True)
    parser.add_option('--write-pixels', help="Write pixel file.",
                      dest="write_pixels", action="store_true", default=False)
    parser.add_option('--to-png', help="Write PNG output.",
                      dest="to_png", action="store_true", default=False)
    parser.add_option('--to-svg', help="Write SVG output.",
                      dest="to_svg", action="store_true", default=False)
    parser.add_option('--output-dir', metavar='DIR', default=".",
                      help="Directory for output files. [%default]",
                      dest="output_dir", action="store")

    options, args = parser.parse_args()
    if not args:
        parser.error("You must provide at least one input file.")

    return options, args


def process_file(options, filename):
    print "Processing %s..." % (filename,)
    data = PixelData(io_data.read_pixels(filename, 'png'))
    base_filename = os.path.splitext(os.path.split(filename)[-1])[0]
    outdir = options.output_dir

    filetypes = []
    if options.to_png:
        filetypes.append('PNG')
    if options.to_svg:
        filetypes.append('SVG')

    if options.write_pixels:
        for ft in filetypes:
            print "    Writing pixels %s..." % (ft,)
            writer = io_data.get_writer(data, base_filename, ft.lower())
            writer.export_pixels(outdir)

    data.depixel()

    if options.write_grid:
        for ft in filetypes:
            print "    Writing grid %s..." % (ft,)
            writer = io_data.get_writer(data, base_filename, ft.lower())
            writer.export_grid(outdir, options.draw_nodes)

    if options.write_shapes:
        for ft in filetypes:
            print "    Writing shapes %s..." % (ft,)
            writer = io_data.get_writer(data, base_filename, ft.lower())
            writer.export_shapes(outdir, options.draw_nodes)

    if options.write_smooth:
        for ft in filetypes:
            print "    Writing smooth shapes %s..." % (ft,)
            writer = io_data.get_writer(data, base_filename, ft.lower())
            writer.export_smooth(outdir, options.draw_nodes)


def main():
    options, args = parse_options()
    for filename in args:
        process_file(options, filename)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = export_test_image
#!/usr/bin/env python

from optparse import OptionParser

from depixel import io_data
from depixel.depixeler import PixelData
from depixel.tests import test_depixeler


def parse_options():
    parser = OptionParser(usage="usage: %prog [options] name")
    parser.add_option('--output-dir', metavar='DIR', default=".",
                      help="Directory for output files. [%default]",
                      dest="output_dir", action="store")

    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("You must provide exactly one test image name.")

    return options, args


def export_image(options, name):
    name = name.upper()
    print "Processing %s..." % (name,)
    data = PixelData(test_depixeler.mkpixels(getattr(test_depixeler, name)))
    base_filename = name.lower()
    outdir = options.output_dir

    print "    Writing pixels PNG..."
    writer = io_data.get_writer(data, base_filename, 'png')
    writer.export_pixels(outdir)


def main():
    options, args = parse_options()
    export_image(options, args[0])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_bspline
from unittest import TestCase

from depixel.bspline import Point, BSpline


def make_oct_spline(p=2, offset_x=0, offset_y=0, scale=50):
    base = [(2, 2), (4, 2), (5, 3), (5, 5), (4, 6), (2, 6), (1, 5), (1, 3)]
    points = [(x * scale + offset_x, y * scale + offset_y) for x, y in base]
    points = points + points[:p]
    m = len(points) + p
    knots = [float(i) / m for i in range(m + 1)]
    return BSpline(knots, points, p)


class TestBSpline(TestCase):
    def test_spline_degree(self):
        knots = [0, 0.25, 0.5, 0.75, 1]
        points = [(0, 0), (1, 1)]
        self.assertEqual(2, BSpline(knots, points).degree)
        self.assertEqual(2, BSpline(knots, points, 2).degree)
        try:
            BSpline(knots, points, 3)
            self.fail("Expected ValueError.")
        except ValueError, e:
            self.assertEqual("Expected degree 2, got 3.", e.args[0])

    def test_spline_domain(self):
        spline = make_oct_spline()
        self.assertEqual((0.5 / 3, 1 - 0.5 / 3), spline.domain)
        self.assertEqual((spline.knots[2], spline.knots[-3]), spline.domain)

    def test_spline_point_at_knot(self):
        spline = make_oct_spline()
        self.assertEqual(Point((150, 300)), spline(0.5).round())

    def test_spline_derivative(self):
        spline = make_oct_spline()
        deriv = spline.derivative()
        self.assertEqual(deriv.degree, spline.degree - 1)
        self.assertEqual(deriv.knots, spline.knots[1:-1])
        self.assertEqual(len(deriv.points), len(spline.points) - 1)

    def test_curvature(self):
        spline = make_oct_spline()
        self.assertEqual(0.005, round(spline.curvature(0.5), 5))

########NEW FILE########
__FILENAME__ = test_depixeler
from unittest import TestCase

import networkx as nx

from depixel.depixeler import PixelData
from depixel.depixeler import (
    FullyConnectedHeuristics, IterativeFinalShapeHeuristics)


BAR = """
XXXX
X..X
XXXX
"""

EAR = """
......
..XX..
.X..X.
.X..X.
....X.
....X.
......
"""

CIRCLE = """
......
..XX..
.X..X.
.X..X.
..XX..
......
"""

PLUS = """
..X..
..X..
XXXXX
..X..
..X..
"""

ISLAND = """
....
.X..
..XX
"""

CEE = """
...............
......XXXX..XX.
....XXooooXXoX.
...XoooXXXoooX.
..XoooX...XooX.
..XooX.....XoX.
.XoooX......XX.
.XoooX.........
.XoooX.........
.XoooX.........
.XoooX.........
..XooX......XX.
..XoooX....XoX.
...XoooXXXXoX..
....XXoooooX...
......XXXXX....
...............
"""

INVADER = """
..............
.....XXXX.....
..XXXXXXXXXX..
.XXXXXXXXXXXX.
.XXX..XX..XXX.
.XXXXXXXXXXXX.
....XX..XX....
...XX.XX.XX...
.XX........XX.
..............
"""

BIGINVADER = """
....................
....................
....................
....................
........XXXX........
.....XXXXXXXXXX.....
....XXXXXXXXXXXX....
....XXX..XX..XXX....
....XXXXXXXXXXXX....
.......XX..XX.......
......XX.XX.XX......
....XX........XX....
....................
....................
....................
....................
"""


def mkpixels(txt_data):
    pixels = []
    for line in txt_data.splitlines():
        line = line.strip()
        if line:
            pixels.append([{'.': 1, 'o': 0.5, 'X': 0}[c] for c in line])
            # pixels.append([{'.': 0, 'o': 0, 'X': 1}[c] for c in line])
    return pixels


def sort_edges(edges):
    return sorted(tuple(sorted(e[:2])) + e[2:] for e in edges)


class TestUtils(TestCase):
    def test_mkpixels(self):
        ear_pixels = [
            [1, 1, 1, 1, 1, 1],
            [1, 1, 0, 0, 1, 1],
            [1, 0, 1, 1, 0, 1],
            [1, 0, 1, 1, 0, 1],
            [1, 1, 1, 1, 0, 1],
            [1, 1, 1, 1, 0, 1],
            [1, 1, 1, 1, 1, 1],
            ]
        self.assertEqual(ear_pixels, mkpixels(EAR))


class TestFullyConnectedHeuristics(TestCase):
    def get_heuristics(self, txt_data):
        pd = PixelData(mkpixels(txt_data))
        pd.make_pixel_graph()
        return FullyConnectedHeuristics(pd.pixel_graph)

    def test_weight_curve(self):
        hh = self.get_heuristics(EAR)
        self.assertEqual(1, hh.weight_curve(((0, 0), (1, 1))))
        self.assertEqual(1, hh.weight_curve(((1, 1), (2, 2))))
        self.assertEqual(7, hh.weight_curve(((1, 2), (2, 1))))

        hh = self.get_heuristics(CIRCLE)
        self.assertEqual(1, hh.weight_curve(((0, 0), (1, 1))))
        self.assertEqual(1, hh.weight_curve(((1, 1), (2, 2))))
        self.assertEqual(8, hh.weight_curve(((1, 2), (2, 1))))

    def test_weight_sparse(self):
        # EAR = """
        # ..... .
        # ..XX. .
        # .X..X .
        # .X..X .
        # ....X .

        # ....X .
        # ..... .
        # """
        hh = self.get_heuristics(EAR)
        self.assertEqual(-18, hh.weight_sparse(((0, 0), (1, 1))))
        self.assertEqual(-28, hh.weight_sparse(((1, 1), (2, 2))))
        self.assertEqual(-8, hh.weight_sparse(((1, 2), (2, 1))))

        hh = self.get_heuristics(PLUS)
        self.assertEqual(-4, hh.weight_sparse(((0, 0), (1, 1))))
        self.assertEqual(-9, hh.weight_sparse(((1, 2), (2, 1))))

    def test_weight_island(self):
        hh = self.get_heuristics(ISLAND)
        self.assertEqual(5, hh.weight_island(((1, 1), (2, 2))))
        self.assertEqual(0, hh.weight_island(((1, 2), (2, 1))))


class TestIterativeFinalShapeHeuristics(TestCase):
    def get_heuristics(self, txt_data):
        pd = PixelData(mkpixels(txt_data))
        pd.make_pixel_graph()
        return IterativeFinalShapeHeuristics(pd.pixel_graph)

    def test_weight_curve(self):
        hh = self.get_heuristics(EAR)
        self.assertEqual((1, 1), hh.weight_curve(((0, 0), (1, 1))))
        self.assertEqual((1, 1), hh.weight_curve(((1, 1), (2, 2))))
        self.assertEqual((7, 7), hh.weight_curve(((1, 2), (2, 1))))

        hh = self.get_heuristics(CIRCLE)
        self.assertEqual((1, 1), hh.weight_curve(((0, 0), (1, 1))))
        self.assertEqual((1, 1), hh.weight_curve(((1, 1), (2, 2))))
        self.assertEqual((8, 8), hh.weight_curve(((1, 2), (2, 1))))

    def test_weight_sparse(self):
        hh = self.get_heuristics(EAR)
        self.assertEqual((-18, -18), hh.weight_sparse(((0, 0), (1, 1))))
        self.assertEqual((-28, -28), hh.weight_sparse(((1, 1), (2, 2))))
        self.assertEqual((-8, -8), hh.weight_sparse(((1, 2), (2, 1))))

        hh = self.get_heuristics(PLUS)
        self.assertEqual((-4, -4), hh.weight_sparse(((0, 0), (1, 1))))
        self.assertEqual((-9, -9), hh.weight_sparse(((1, 2), (2, 1))))

    def test_weight_island(self):
        hh = self.get_heuristics(ISLAND)
        self.assertEqual((5, 5), hh.weight_island(((1, 1), (2, 2))))
        self.assertEqual((0, 0), hh.weight_island(((1, 2), (2, 1))))


class TestPixelData(TestCase):
    def test_size(self):
        pd = PixelData([[1, 1], [1, 1], [1, 1]])
        self.assertEqual((2, 3), pd.size)
        self.assertEqual((pd.size_x, pd.size_y), pd.size)

        pd = PixelData([[1, 1, 1], [1, 1, 1]])
        self.assertEqual((3, 2), pd.size)
        self.assertEqual((pd.size_x, pd.size_y), pd.size)

        pd = PixelData(mkpixels(EAR))
        self.assertEqual((6, 7), pd.size)
        self.assertEqual((pd.size_x, pd.size_y), pd.size)

    def test_pixel_graph(self):
        tg = nx.Graph()
        tg.add_nodes_from([
                ((0, 0), {'value': 1,
                          'corners': set([(0, 0), (0, 1), (1, 0), (1, 1)])}),
                ((0, 1), {'value': 1,
                          'corners': set([(0, 1), (0, 2), (1, 1), (1, 2)])}),
                ((0, 2), {'value': 1,
                          'corners': set([(0, 2), (0, 3), (1, 2), (1, 3)])}),
                ((1, 0), {'value': 1,
                          'corners': set([(1, 0), (1, 1), (2, 0), (2, 1)])}),
                ((1, 1), {'value': 0,
                          'corners': set([(1, 1), (1, 2), (2, 1), (2, 2)])}),
                ((1, 2), {'value': 1,
                          'corners': set([(1, 2), (1, 3), (2, 2), (2, 3)])}),
                ((2, 0), {'value': 1,
                          'corners': set([(2, 0), (2, 1), (3, 0), (3, 1)])}),
                ((2, 1), {'value': 1,
                          'corners': set([(2, 1), (2, 2), (3, 1), (3, 2)])}),
                ((2, 2), {'value': 0,
                          'corners': set([(2, 2), (2, 3), (3, 2), (3, 3)])}),
                ((3, 0), {'value': 1,
                          'corners': set([(3, 0), (3, 1), (4, 0), (4, 1)])}),
                ((3, 1), {'value': 1,
                          'corners': set([(3, 1), (3, 2), (4, 1), (4, 2)])}),
                ((3, 2), {'value': 0,
                          'corners': set([(3, 2), (3, 3), (4, 2), (4, 3)])}),
                ])
        tg.add_edges_from([
                ((0, 0), (1, 0), {'diagonal': False}),
                ((0, 1), (0, 0), {'diagonal': False}),
                ((0, 1), (0, 2), {'diagonal': False}),
                ((0, 1), (1, 0), {'diagonal': True}),
                ((0, 1), (1, 2), {'diagonal': True}),
                ((1, 1), (2, 2), {'diagonal': True}),
                ((1, 2), (0, 2), {'diagonal': False}),
                ((1, 2), (2, 1), {'diagonal': True}),
                ((2, 0), (1, 0), {'diagonal': False}),
                ((2, 1), (1, 0), {'diagonal': True}),
                ((2, 1), (2, 0), {'diagonal': False}),
                ((3, 0), (2, 0), {'diagonal': False}),
                ((3, 0), (2, 1), {'diagonal': True}),
                ((3, 0), (3, 1), {'diagonal': False}),
                ((3, 1), (2, 0), {'diagonal': True}),
                ((3, 1), (2, 1), {'diagonal': False}),
                ((3, 2), (2, 2), {'diagonal': False}),
                ])

        pd = PixelData(mkpixels(ISLAND))
        pd.make_pixel_graph()
        self.assertEqual(sorted(tg.nodes(data=True)),
                         sorted(pd.pixel_graph.nodes(data=True)))
        self.assertEqual(sort_edges(tg.edges(data=True)),
                         sort_edges(pd.pixel_graph.edges(data=True)))

    def test_remove_diagonals(self):
        tg = nx.Graph()
        tg.add_nodes_from([
                ((0, 0), {'value': 1,
                          'corners': set([(0, 0), (0, 1), (1, 0), (1, 1)])}),
                ((0, 1), {'value': 1,
                          'corners': set([(0, 1), (0, 2), (1, 1), (1, 2)])}),
                ((0, 2), {'value': 1,
                          'corners': set([(0, 2), (0, 3), (1, 2), (1, 3)])}),
                ((1, 0), {'value': 1,
                          'corners': set([(1, 0), (1, 1), (2, 0), (2, 1)])}),
                ((1, 1), {'value': 0,
                          'corners': set([(1, 1), (1, 2), (2, 1), (2, 2)])}),
                ((1, 2), {'value': 1,
                          'corners': set([(1, 2), (1, 3), (2, 2), (2, 3)])}),
                ((2, 0), {'value': 1,
                          'corners': set([(2, 0), (2, 1), (3, 0), (3, 1)])}),
                ((2, 1), {'value': 1,
                          'corners': set([(2, 1), (2, 2), (3, 1), (3, 2)])}),
                ((2, 2), {'value': 0,
                          'corners': set([(2, 2), (2, 3), (3, 2), (3, 3)])}),
                ((3, 0), {'value': 1,
                          'corners': set([(3, 0), (3, 1), (4, 0), (4, 1)])}),
                ((3, 1), {'value': 1,
                          'corners': set([(3, 1), (3, 2), (4, 1), (4, 2)])}),
                ((3, 2), {'value': 0,
                          'corners': set([(3, 2), (3, 3), (4, 2), (4, 3)])}),
                ])
        tg.add_edges_from([
                ((0, 0), (1, 0), {'diagonal': False}),
                ((0, 1), (0, 0), {'diagonal': False}),
                ((0, 1), (0, 2), {'diagonal': False}),
                ((0, 1), (1, 0), {'diagonal': True}),
                ((0, 1), (1, 2), {'diagonal': True}),
                ((1, 1), (2, 2), {'diagonal': True}),
                ((1, 2), (0, 2), {'diagonal': False}),
                # ((1, 2), (2, 1), {'diagonal': True}),
                ((2, 0), (1, 0), {'diagonal': False}),
                ((2, 1), (1, 0), {'diagonal': True}),
                ((2, 1), (2, 0), {'diagonal': False}),
                ((3, 0), (2, 0), {'diagonal': False}),
                # ((3, 0), (2, 1), {'diagonal': True}),
                ((3, 0), (3, 1), {'diagonal': False}),
                # ((3, 1), (2, 0), {'diagonal': True}),
                ((3, 1), (2, 1), {'diagonal': False}),
                ((3, 2), (2, 2), {'diagonal': False}),
                ])

        pd = PixelData(mkpixels(ISLAND))
        pd.make_pixel_graph()
        pd.remove_diagonals()
        self.assertEqual(sorted(tg.nodes(data=True)),
                         sorted(pd.pixel_graph.nodes(data=True)))
        self.assertEqual(sort_edges(tg.edges(data=True)),
                         sort_edges(pd.pixel_graph.edges(data=True)))

    def test_deform_grid(self):
        tg = nx.Graph()
        tg.add_nodes_from([
                (0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3),
                (1.25, 1.25), (1.25, 1.75), (1.75, 1.25), (1.75, 2.25), (2, 0),
                (2, 1), (2, 3), (2.25, 1.75), (3, 0), (3, 1), (3, 2), (3, 3),
                (4, 0), (4, 1), (4, 2), (4, 3),
                ])
        tg.add_edges_from([
                ((0, 0), (0, 1)), ((0, 1), (0, 2)), ((0, 3), (0, 2)),
                ((1, 0), (0, 0)), ((1, 0), (1, 1)), ((1, 0), (2, 0)),
                ((1, 1), (0, 1)), ((1, 2), (0, 2)), ((1, 3), (0, 3)),
                ((1, 3), (1, 2)), ((1, 3), (2, 3)), ((1.25, 1.25), (1, 1)),
                ((1.25, 1.25), (1.75, 1.25)), ((1.25, 1.75), (1, 2)),
                ((1.25, 1.75), (1.25, 1.25)), ((1.25, 1.75), (1.75, 2.25)),
                ((2, 1), (1.75, 1.25)), ((2, 1), (2, 0)), ((2, 1), (3, 1)),
                ((2, 3), (1.75, 2.25)), ((2.25, 1.75), (1.75, 1.25)),
                ((2.25, 1.75), (1.75, 2.25)), ((2.25, 1.75), (3, 2)),
                ((3, 0), (2, 0)), ((3, 0), (3, 1)), ((3, 0), (4, 0)),
                ((3, 2), (3, 1)), ((3, 2), (4, 2)), ((3, 3), (2, 3)),
                ((3, 3), (3, 2)), ((3, 3), (4, 3)), ((4, 0), (4, 1)),
                ((4, 1), (3, 1)), ((4, 1), (4, 2)), ((4, 2), (4, 3)),
                ])

        pd = PixelData(mkpixels(ISLAND))
        pd.depixel()

        self.assertEqual(sorted(tg.nodes()), sorted(pd.grid_graph.nodes()))
        self.assertEqual(sort_edges(tg.edges()),
                         sort_edges(pd.grid_graph.edges()))

########NEW FILE########
