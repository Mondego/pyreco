__FILENAME__ = buffer
from matplotlib import pyplot
from shapely.geometry import LineString
from descartes import PolygonPatch

from figures import SIZE, BLUE, GRAY

def plot_line(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, color=GRAY, linewidth=3, solid_capstyle='round', zorder=1)

line = LineString([(0, 0), (1, 1), (0, 2), (2, 2), (3, 1), (1, 0)])

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 1
ax = fig.add_subplot(121)

plot_line(ax, line)

dilated = line.buffer(0.5, cap_style=3)
patch1 = PolygonPatch(dilated, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patch1)

ax.set_title('a) dilation, cap_style=3')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2
ax = fig.add_subplot(122)

patch2a = PolygonPatch(dilated, fc=GRAY, ec=GRAY, alpha=0.5, zorder=1)
ax.add_patch(patch2a)

eroded = dilated.buffer(-0.3)

# GeoJSON-like data works as well

polygon = eroded.__geo_interface__
# >>> geo['type']
# 'Polygon'
# >>> geo['coordinates'][0][:2]
# ((0.50502525316941682, 0.78786796564403572), (0.5247963548222736, 0.8096820147509064))
patch2b = PolygonPatch(polygon, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patch2b)

ax.set_title('b) erosion, join_style=1')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = cascaded_union
from matplotlib import pyplot
from shapely.geometry import Point
from shapely.ops import cascaded_union
from descartes import PolygonPatch

from figures import SIZE, BLUE, GRAY

polygons = [Point(i, 0).buffer(0.7) for i in range(5)]

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 1
ax = fig.add_subplot(121)

for ob in polygons:
    p = PolygonPatch(ob, fc=GRAY, ec=GRAY, alpha=0.5, zorder=1)
    ax.add_patch(p)

ax.set_title('a) polygons')

xrange = [-2, 6]
yrange = [-2, 2]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2
ax = fig.add_subplot(122)

u = cascaded_union(polygons)
patch2b = PolygonPatch(u, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patch2b)

ax.set_title('b) union')

xrange = [-2, 6]
yrange = [-2, 2]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = convex_hull
from matplotlib import pyplot
from shapely.geometry import MultiPoint

from descartes.patch import PolygonPatch

from figures import SIZE

fig = pyplot.figure(1, figsize=SIZE, dpi=90)
fig.set_frameon(True)

# 1
ax = fig.add_subplot(121)

points2 = MultiPoint([(0, 0), (2, 2)])
for p in points2:
    ax.plot(p.x, p.y, 'o', color='#999999')
hull2 = points2.convex_hull
x, y = hull2.xy
ax.plot(x, y, color='#6699cc', linewidth=3, alpha=0.5, zorder=2)

ax.set_title('a) N = 2')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2
ax = fig.add_subplot(122)

points1 = MultiPoint([(0, 0), (1, 1), (0, 2), (2, 2), (3, 1), (1, 0)])

for p in points1:
    ax.plot(p.x, p.y, 'o', color='#999999')
hull1 = points1.convex_hull
patch1 = PolygonPatch(hull1, facecolor='#6699cc', edgecolor='#6699cc', alpha=0.5, zorder=2)
ax.add_patch(patch1)

ax.set_title('b) N > 2')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()



########NEW FILE########
__FILENAME__ = difference
from matplotlib import pyplot
from shapely.geometry import Point
from descartes import PolygonPatch

from figures import SIZE, BLUE, GRAY

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

a = Point(1, 1).buffer(1.5)
b = Point(2, 1).buffer(1.5)

# 1
ax = fig.add_subplot(121)

patch1 = PolygonPatch(a, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch1)
patch2 = PolygonPatch(b, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch2)
c = a.difference(b)
patchc = PolygonPatch(c, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patchc)

ax.set_title('a.difference(b)')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2
ax = fig.add_subplot(122)

patch1 = PolygonPatch(a, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch1)
patch2 = PolygonPatch(b, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch2)
c = b.difference(a)
patchc = PolygonPatch(c, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patchc)

ax.set_title('b.difference(a)')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = figures
from math import sqrt

GM = (sqrt(5)-1.0)/2.0
W = 8.0
H = W*GM
SIZE = (W, H)

BLUE = '#6699cc'
GRAY = '#999999'

########NEW FILE########
__FILENAME__ = geometrycollection
from matplotlib import pyplot
from shapely.geometry import LineString
from figures import SIZE

BLUE =   '#6699cc'
YELLOW = '#ffcc33'
GREEN =  '#339933'
GRAY =   '#999999'

def plot_coords(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, 'o', color=GRAY, zorder=1)

fig = pyplot.figure(1, figsize=SIZE, dpi=90) #1, figsize=(10, 4), dpi=180)

a = LineString([(0, 0), (1, 1), (1,2), (2,2)])
b = LineString([(0, 0), (1, 1), (2,1), (2,2)])

# 1: disconnected multilinestring
ax = fig.add_subplot(121)

plot_coords(ax, a)
plot_coords(ax, b)

x, y = a.xy
ax.plot(x, y, color=YELLOW, alpha=0.5, linewidth=3, solid_capstyle='round', zorder=2)

x, y = b.xy
ax.plot(x, y, color=GREEN, alpha=0.5, linewidth=3, solid_capstyle='round', zorder=2)

ax.set_title('a) lines')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2: invalid self-touching ring
ax = fig.add_subplot(122)

x, y = a.xy
ax.plot(x, y, color=GRAY, alpha=0.7, linewidth=1, solid_capstyle='round', zorder=1)
x, y = b.xy
ax.plot(x, y, color=GRAY, alpha=0.7, linewidth=1, solid_capstyle='round', zorder=1)

for ob in a.intersection(b):
    x, y = ob.xy
    if len(x) == 1:
        ax.plot(x, y, 'o', color=BLUE, zorder=2)
    else:
        ax.plot(x, y, color=BLUE, alpha=0.7, linewidth=3, solid_capstyle='round', zorder=2)

ax.set_title('b) collection')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = intersection-sym-difference
from matplotlib import pyplot
from shapely.geometry import Point
from descartes import PolygonPatch

from figures import SIZE, BLUE, GRAY

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

a = Point(1, 1).buffer(1.5)
b = Point(2, 1).buffer(1.5)

# 1
ax = fig.add_subplot(121)

patch1 = PolygonPatch(a, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch1)
patch2 = PolygonPatch(b, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch2)
c = a.intersection(b)
patchc = PolygonPatch(c, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patchc)

ax.set_title('a.intersection(b)')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2
ax = fig.add_subplot(122)

patch1 = PolygonPatch(a, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch1)
patch2 = PolygonPatch(b, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch2)
c = a.symmetric_difference(b)

if c.geom_type == 'Polygon':
    patchc = PolygonPatch(c, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
    ax.add_patch(patchc)
elif c.geom_type == 'MultiPolygon':
    for p in c:
        patchp = PolygonPatch(p, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
        ax.add_patch(patchp)

ax.set_title('a.symmetric_difference(b)')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = linearring
from matplotlib import pyplot
from shapely.geometry.polygon import LinearRing

from figures import SIZE

COLOR = {
    True:  '#6699cc',
    False: '#ff3333'
    }

def v_color(ob):
    return COLOR[ob.is_valid]

def plot_coords(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, 'o', color='#999999', zorder=1)

def plot_line(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, color=v_color(ob), alpha=0.7, linewidth=3, solid_capstyle='round', zorder=2)

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 1: valid ring
ax = fig.add_subplot(121)
ring = LinearRing([(0, 0), (0, 2), (1, 1), (2, 2), (2, 0), (1, 0.8), (0, 0)])

plot_coords(ax, ring)
plot_line(ax, ring)

ax.set_title('a) valid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2: invalid self-touching ring
ax = fig.add_subplot(122)
ring2 = LinearRing([(0, 0), (0, 2), (1, 1), (2, 2), (2, 0), (1, 1), (0, 0)])

plot_coords(ax, ring2)
plot_line(ax, ring2)

ax.set_title('b) invalid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = linestring
from matplotlib import pyplot
from shapely.geometry import LineString

from figures import SIZE

COLOR = {
    True:  '#6699cc',
    False: '#ffcc33'
    }

def v_color(ob):
    return COLOR[ob.is_simple]

def plot_coords(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, 'o', color='#999999', zorder=1)

def plot_bounds(ax, ob):
    x, y = zip(*list((p.x, p.y) for p in ob.boundary))
    ax.plot(x, y, 'o', color='#000000', zorder=1)

def plot_line(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, color=v_color(ob), alpha=0.7, linewidth=3, solid_capstyle='round', zorder=2)

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 1: simple line
ax = fig.add_subplot(121)
line = LineString([(0, 0), (1, 1), (0, 2), (2, 2), (3, 1), (1, 0)])

plot_coords(ax, line)
plot_bounds(ax, line)
plot_line(ax, line)

ax.set_title('a) simple')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_ylim(*yrange)
ax.set_yticks(list(range(*yrange)) + [yrange[-1]])
ax.set_aspect(1)

#2: complex line
ax = fig.add_subplot(122)
line2 = LineString([(0, 0), (1, 1), (0, 2), (2, 2), (-1, 1), (1, 0)])

plot_coords(ax, line2)
plot_bounds(ax, line2)
plot_line(ax, line2)

ax.set_title('b) complex')

xrange = [-2, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_ylim(*yrange)
ax.set_yticks(list(range(*yrange)) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = multilinestring
from matplotlib import pyplot
from shapely.geometry import MultiLineString

from figures import SIZE

COLOR = {
    True:  '#6699cc',
    False: '#ffcc33'
    }

def v_color(ob):
    return COLOR[ob.is_simple]

def plot_coords(ax, ob):
    for line in ob:
        x, y = line.xy
        ax.plot(x, y, 'o', color='#999999', zorder=1)

def plot_bounds(ax, ob):
    x, y = zip(*list((p.x, p.y) for p in ob.boundary))
    ax.plot(x, y, 'o', color='#000000', zorder=1)

def plot_lines(ax, ob):
    for line in ob:
        x, y = line.xy
        ax.plot(x, y, color=v_color(ob), alpha=0.7, linewidth=3, solid_capstyle='round', zorder=2)

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 1: disconnected multilinestring
ax = fig.add_subplot(121)

mline1 = MultiLineString([((0, 0), (1, 1)), ((0, 2),  (1, 1.5), (1.5, 1), (2, 0))])

plot_coords(ax, mline1)
plot_bounds(ax, mline1)
plot_lines(ax, mline1)

ax.set_title('a) simple')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2: invalid self-touching ring
ax = fig.add_subplot(122)

mline2 = MultiLineString([((0, 0), (1, 1), (1.5, 1)), ((0, 2), (1, 1.5), (1.5, 1), (2, 0))])

plot_coords(ax, mline2)
plot_bounds(ax, mline2)
plot_lines(ax, mline2)

ax.set_title('b) complex')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = multipolygon
from matplotlib import pyplot
from shapely.geometry import MultiPolygon
from descartes.patch import PolygonPatch

from figures import SIZE

COLOR = {
    True:  '#6699cc',
    False: '#ff3333'
    }

def v_color(ob):
    return COLOR[ob.is_valid]

def plot_coords(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, 'o', color='#999999', zorder=1)
    
fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 1: valid multi-polygon
ax = fig.add_subplot(121)

a = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]
b = [(1, 1), (1, 2), (2, 2), (2, 1), (1, 1)]

multi1 = MultiPolygon([[a, []], [b, []]])

for polygon in multi1:
    plot_coords(ax, polygon.exterior)
    patch = PolygonPatch(polygon, facecolor=v_color(multi1), edgecolor=v_color(multi1), alpha=0.5, zorder=2)
    ax.add_patch(patch)

ax.set_title('a) valid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2: invalid self-touching ring
ax = fig.add_subplot(122)

c = [(0, 0), (0, 1.5), (1, 1.5), (1, 0), (0, 0)]
d = [(1, 0.5), (1, 2), (2, 2), (2, 0.5), (1, 0.5)]

multi2 = MultiPolygon([[c, []], [d, []]])

for polygon in multi2:
    plot_coords(ax, polygon.exterior)
    patch = PolygonPatch(polygon, facecolor=v_color(multi2), edgecolor=v_color(multi2), alpha=0.5, zorder=2)
    ax.add_patch(patch)

ax.set_title('b) invalid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = parallel_offset
from matplotlib import pyplot
from shapely.geometry import LineString
from descartes import PolygonPatch

from figures import SIZE, BLUE, GRAY

def plot_coords(ax, x, y, color='#999999', zorder=1):
    ax.plot(x, y, 'o', color=color, zorder=zorder)

def plot_line(ax, ob, color=GRAY):
    parts = hasattr(ob, 'geoms') and ob or [ob]
    for part in parts:
        x, y = part.xy
        ax.plot(x, y, color=color, linewidth=3, solid_capstyle='round', zorder=1)

def set_limits(ax, x_range, y_range):
    ax.set_xlim(*x_range)
    ax.set_xticks(range(*x_range) + [x_range[-1]])
    ax.set_ylim(*y_range)
    ax.set_yticks(range(*y_range) + [y_range[-1]])
    ax.set_aspect(1)

line = LineString([(0, 0), (1, 1), (0, 2), (2, 2), (3, 1), (1, 0)])
line_bounds = line.bounds
ax_range = [int(line_bounds[0] - 1.0), int(line_bounds[2] + 1.0)]
ay_range = [int(line_bounds[1] - 1.0), int(line_bounds[3] + 1.0)]

fig = pyplot.figure(1, figsize=(SIZE[0], 2 * SIZE[1]), dpi=90)

# 1
ax = fig.add_subplot(221)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)
offset = line.parallel_offset(0.5, 'left', join_style=1)
plot_line(ax, offset, color=BLUE)

ax.set_title('a) left, round')
set_limits(ax, ax_range, ay_range)

#2
ax = fig.add_subplot(222)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)

offset = line.parallel_offset(0.5, 'left', join_style=2)
plot_line(ax, offset, color=BLUE)

ax.set_title('b) left, mitred')
set_limits(ax, ax_range, ay_range)

#3
ax = fig.add_subplot(223)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)
offset = line.parallel_offset(0.5, 'left', join_style=3)
plot_line(ax, offset, color=BLUE)

ax.set_title('c) left, beveled')
set_limits(ax, ax_range, ay_range)

#4
ax = fig.add_subplot(224)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)
offset = line.parallel_offset(0.5, 'right', join_style=1)
plot_line(ax, offset, color=BLUE)

ax.set_title('d) right, round')
set_limits(ax, ax_range, ay_range)

pyplot.show()


########NEW FILE########
__FILENAME__ = parallel_offset_mitre
from matplotlib import pyplot
from shapely.geometry import LineString
from descartes import PolygonPatch

from figures import SIZE, BLUE, GRAY

def plot_coords(ax, x, y, color='#999999', zorder=1):
    ax.plot(x, y, 'o', color=color, zorder=zorder)

def plot_line(ax, ob, color=GRAY):
    parts = hasattr(ob, 'geoms') and ob or [ob]
    for part in parts:
        x, y = part.xy
        ax.plot(x, y, color=color, linewidth=3, solid_capstyle='round', zorder=1)

def set_limits(ax, x_range, y_range):
    ax.set_xlim(*x_range)
    ax.set_xticks(range(*x_range) + [x_range[-1]])
    ax.set_ylim(*y_range)
    ax.set_yticks(range(*y_range) + [y_range[-1]])
    ax.set_aspect(1)

line = LineString([(0, 0), (1, 1), (0, 2), (2, 2), (3, 1), (1, 0)])
line_bounds = line.bounds
ax_range = [int(line_bounds[0] - 1.0), int(line_bounds[2] + 1.0)]
ay_range = [int(line_bounds[1] - 1.0), int(line_bounds[3] + 1.0)]

fig = pyplot.figure(1, figsize=(SIZE[0], 2 * SIZE[1]), dpi=90)

# 1
ax = fig.add_subplot(221)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)
offset = line.parallel_offset(0.5, 'left', join_style=2, mitre_limit=0.1)
plot_line(ax, offset, color=BLUE)

ax.set_title('a) left, limit=0.1')
set_limits(ax, ax_range, ay_range)

#2
ax = fig.add_subplot(222)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)

offset = line.parallel_offset(0.5, 'left', join_style=2, mitre_limit=10.0)
plot_line(ax, offset, color=BLUE)

ax.set_title('b) left, limit=10.0')
set_limits(ax, ax_range, ay_range)

#3
ax = fig.add_subplot(223)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)
offset = line.parallel_offset(0.5, 'right', join_style=2, mitre_limit=0.1)
plot_line(ax, offset, color=BLUE)

ax.set_title('c) right, limit=0.1')
set_limits(ax, ax_range, ay_range)

#4
ax = fig.add_subplot(224)

plot_line(ax, line)
x, y = list(line.coords)[0]
plot_coords(ax, x, y)
offset = line.parallel_offset(0.5, 'right', join_style=2, mitre_limit=10.0)
plot_line(ax, offset, color=BLUE)

ax.set_title('d) right, limit=10.0')
set_limits(ax, ax_range, ay_range)

pyplot.show()


########NEW FILE########
__FILENAME__ = polygon
from matplotlib import pyplot
from shapely.geometry import Polygon
from descartes.patch import PolygonPatch

from figures import SIZE

COLOR = {
    True:  '#6699cc',
    False: '#ff3333'
    }

def v_color(ob):
    return COLOR[ob.is_valid]

def plot_coords(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, 'o', color='#999999', zorder=1)
    
fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 1: valid polygon
ax = fig.add_subplot(121)

ext = [(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)]
int = [(1, 0), (0.5, 0.5), (1, 1), (1.5, 0.5), (1, 0)][::-1]
polygon = Polygon(ext, [int])

plot_coords(ax, polygon.interiors[0])
plot_coords(ax, polygon.exterior)

patch = PolygonPatch(polygon, facecolor=v_color(polygon), edgecolor=v_color(polygon), alpha=0.5, zorder=2)
ax.add_patch(patch)

ax.set_title('a) valid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2: invalid self-touching ring
ax = fig.add_subplot(122)
ext = [(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)]
int = [(1, 0), (0, 1), (0.5, 1.5), (1.5, 0.5), (1, 0)][::-1]
polygon = Polygon(ext, [int])

plot_coords(ax, polygon.interiors[0])
plot_coords(ax, polygon.exterior)

patch = PolygonPatch(polygon, facecolor=v_color(polygon), edgecolor=v_color(polygon), alpha=0.5, zorder=2)
ax.add_patch(patch)

ax.set_title('b) invalid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = polygon2
from matplotlib import pyplot
from matplotlib.patches import Circle
from shapely.geometry import Polygon
from descartes.patch import PolygonPatch

from figures import SIZE

COLOR = {
    True:  '#6699cc',
    False: '#ff3333'
    }

def v_color(ob):
    return COLOR[ob.is_valid]

def plot_coords(ax, ob):
    x, y = ob.xy
    ax.plot(x, y, 'o', color='#999999', zorder=1)
    
fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# 3: invalid polygon, ring touch along a line
ax = fig.add_subplot(121)

ext = [(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)]
int = [(0.5, 0), (1.5, 0), (1.5, 1), (0.5, 1), (0.5, 0)]
polygon = Polygon(ext, [int])

plot_coords(ax, polygon.interiors[0])
plot_coords(ax, polygon.exterior)

patch = PolygonPatch(polygon, facecolor=v_color(polygon), edgecolor=v_color(polygon), alpha=0.5, zorder=2)
ax.add_patch(patch)

ax.set_title('c) invalid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#4: invalid self-touching ring
ax = fig.add_subplot(122)
ext = [(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)]
int_1 = [(0.5, 0.25), (1.5, 0.25), (1.5, 1.25), (0.5, 1.25), (0.5, 0.25)]
int_2 = [(0.5, 1.25), (1, 1.25), (1, 1.75), (0.5, 1.75)]
# int_2 = [
polygon = Polygon(ext, [int_1, int_2])

plot_coords(ax, polygon.interiors[0])
plot_coords(ax, polygon.interiors[1])
plot_coords(ax, polygon.exterior)

patch = PolygonPatch(polygon, facecolor=v_color(polygon), edgecolor=v_color(polygon), alpha=0.5, zorder=2)
ax.add_patch(patch)

ax.set_title('d) invalid')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = rotate
from matplotlib import pyplot
from shapely.geometry import LineString
from shapely import affinity

from figures import SIZE, BLUE, GRAY


def add_origin(ax, geom, origin):
    x, y = xy = affinity.interpret_origin(geom, origin, 2)
    ax.plot(x, y, 'o', color=GRAY, zorder=1)
    ax.annotate(str(xy), xy=xy, ha='center',
                textcoords='offset points', xytext=(0, 8))


def plot_line(ax, ob, color):
    x, y = ob.xy
    ax.plot(x, y, color=color, alpha=0.7, linewidth=3,
            solid_capstyle='round', zorder=2)

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

line = LineString([(1, 3), (1, 1), (4, 1)])

xrange = [0, 5]
yrange = [0, 4]

# 1
ax = fig.add_subplot(121)

plot_line(ax, line, GRAY)
plot_line(ax, affinity.rotate(line, 90, 'center'), BLUE)
add_origin(ax, line, 'center')

ax.set_title(u"90\N{DEGREE SIGN}, default origin (center)")

ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

# 2
ax = fig.add_subplot(122)

plot_line(ax, line, GRAY)
plot_line(ax, affinity.rotate(line, 90, 'centroid'), BLUE)
add_origin(ax, line, 'centroid')

ax.set_title(u"90\N{DEGREE SIGN}, origin='centroid'")

ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()

########NEW FILE########
__FILENAME__ = scale
from matplotlib import pyplot
from shapely.geometry import Polygon
from shapely import affinity
from descartes.patch import PolygonPatch

from figures import SIZE, BLUE, GRAY


def add_origin(ax, geom, origin):
    x, y = xy = affinity.interpret_origin(geom, origin, 2)
    ax.plot(x, y, 'o', color=GRAY, zorder=1)
    ax.annotate(str(xy), xy=xy, ha='center',
                textcoords='offset points', xytext=(0, 8))

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

triangle = Polygon([(1, 1), (2, 3), (3, 1)])

xrange = [0, 5]
yrange = [0, 4]

# 1
ax = fig.add_subplot(121)

patch = PolygonPatch(triangle, facecolor=GRAY, edgecolor=GRAY,
                     alpha=0.5, zorder=1)
triangle_a = affinity.scale(triangle, xfact=1.5, yfact=-1)
patch_a = PolygonPatch(triangle_a, facecolor=BLUE, edgecolor=BLUE,
                       alpha=0.5, zorder=2)
ax.add_patch(patch)
ax.add_patch(patch_a)

add_origin(ax, triangle, 'center')

ax.set_title("a) xfact=1.5, yfact=-1")

ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

# 2
ax = fig.add_subplot(122)

patch = PolygonPatch(triangle, facecolor=GRAY, edgecolor=GRAY,
                     alpha=0.5, zorder=1)
triangle_b = affinity.scale(triangle, xfact=2, origin=(1, 1))
patch_b = PolygonPatch(triangle_b, facecolor=BLUE, edgecolor=BLUE,
                       alpha=0.5, zorder=2)
ax.add_patch(patch)
ax.add_patch(patch_b)

add_origin(ax, triangle, (1, 1))

ax.set_title("b) xfact=2, origin=(1, 1)")

ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()

########NEW FILE########
__FILENAME__ = simplify
from matplotlib import pyplot
from shapely.geometry import MultiPoint, Point
from descartes.patch import PolygonPatch

from figures import SIZE, BLUE, GRAY

fig = pyplot.figure(1, figsize=SIZE, dpi=90) #1, figsize=SIZE, dpi=90)

p = Point(1, 1).buffer(1.5)

# 1
ax = fig.add_subplot(121)

q = p.simplify(0.2)

patch1a = PolygonPatch(p, facecolor=GRAY, edgecolor=GRAY, alpha=0.5, zorder=1)
ax.add_patch(patch1a)

patch1b = PolygonPatch(q, facecolor=BLUE, edgecolor=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patch1b)

ax.set_title('a) tolerance 0.2')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

#2
ax = fig.add_subplot(122)

r = p.simplify(0.5)

patch2a = PolygonPatch(p, facecolor=GRAY, edgecolor=GRAY, alpha=0.5, zorder=1)
ax.add_patch(patch2a)

patch2b = PolygonPatch(r, facecolor=BLUE, edgecolor=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patch2b)

ax.set_title('b) tolerance 0.5')

xrange = [-1, 3]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()



########NEW FILE########
__FILENAME__ = skew
from matplotlib import pyplot
from shapely.wkt import loads as load_wkt
from shapely import affinity
from descartes.patch import PolygonPatch

from figures import SIZE, BLUE, GRAY


def add_origin(ax, geom, origin):
    x, y = xy = affinity.interpret_origin(geom, origin, 2)
    ax.plot(x, y, 'o', color=GRAY, zorder=1)
    ax.annotate(str(xy), xy=xy, ha='center',
                textcoords='offset points', xytext=(0, 8))

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

# Geometry from JTS TestBuilder with fixed precision model of 100.0
# Using CreateShape > FontGlyphSanSerif and A = triangle.wkt from scale.py
R = load_wkt('''\
POLYGON((2.218 2.204, 2.273 2.18, 2.328 2.144, 2.435 2.042, 2.541 1.895,
  2.647 1.702, 3 1, 2.626 1, 2.298 1.659, 2.235 1.777, 2.173 1.873,
  2.112 1.948, 2.051 2.001, 1.986 2.038, 1.91 2.064, 1.823 2.08, 1.726 2.085,
  1.347 2.085, 1.347 1, 1 1, 1 3.567, 1.784 3.567, 1.99 3.556, 2.168 3.521,
  2.319 3.464, 2.441 3.383, 2.492 3.334, 2.536 3.279, 2.604 3.152,
  2.644 3.002, 2.658 2.828, 2.651 2.712, 2.63 2.606, 2.594 2.51, 2.545 2.425,
  2.482 2.352, 2.407 2.29, 2.319 2.241, 2.218 2.204),
 (1.347 3.282, 1.347 2.371, 1.784 2.371, 1.902 2.378, 2.004 2.4, 2.091 2.436,
  2.163 2.487, 2.219 2.552, 2.259 2.63, 2.283 2.722, 2.291 2.828, 2.283 2.933,
  2.259 3.025, 2.219 3.103, 2.163 3.167, 2.091 3.217, 2.004 3.253, 1.902 3.275,
  1.784 3.282, 1.347 3.282))''')

xrange = [0, 5]
yrange = [0, 4]

# 1
ax = fig.add_subplot(121)

patch1a = PolygonPatch(R, facecolor=GRAY, edgecolor=GRAY,
                       alpha=0.5, zorder=1)
skewR = affinity.skew(R, xs=20, origin=(1, 1))
patch1b = PolygonPatch(skewR, facecolor=BLUE, edgecolor=BLUE,
                       alpha=0.5, zorder=2)
ax.add_patch(patch1a)
ax.add_patch(patch1b)

add_origin(ax, R, (1, 1))

ax.set_title("a) xs=20, origin(1, 1)")

ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

# 2
ax = fig.add_subplot(122)

patch2a = PolygonPatch(R, facecolor=GRAY, edgecolor=GRAY,
                       alpha=0.5, zorder=1)
skewR = affinity.skew(R, ys=30)
patch2b = PolygonPatch(skewR, facecolor=BLUE, edgecolor=BLUE,
                       alpha=0.5, zorder=2)
ax.add_patch(patch2a)
ax.add_patch(patch2b)

add_origin(ax, R, 'center')

ax.set_title("b) ys=30")

ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()

########NEW FILE########
__FILENAME__ = union
from matplotlib import pyplot
from shapely.geometry import Point
from descartes import PolygonPatch

from figures import SIZE, BLUE, GRAY

fig = pyplot.figure(1, figsize=SIZE, dpi=90)

a = Point(1, 1).buffer(1.5)
b = Point(2, 1).buffer(1.5)

# 1
ax = fig.add_subplot(121)

patch1 = PolygonPatch(a, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch1)
patch2 = PolygonPatch(b, fc=GRAY, ec=GRAY, alpha=0.2, zorder=1)
ax.add_patch(patch2)
c = a.union(b)
patchc = PolygonPatch(c, fc=BLUE, ec=BLUE, alpha=0.5, zorder=2)
ax.add_patch(patchc)

ax.set_title('a.union(b)')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

def plot_line(ax, ob, color=GRAY):
    x, y = ob.xy
    ax.plot(x, y, color, linewidth=3, solid_capstyle='round', zorder=1)

#2
ax = fig.add_subplot(122)

plot_line(ax, a.exterior)
plot_line(ax, b.exterior)

u = a.exterior.union(b.exterior)
if u.geom_type in ['LineString', 'LinearRing', 'Point']:
    plot_line(ax, u, color=BLUE)
elif u.geom_type is 'MultiLineString':
    for p in u:
        plot_line(ax, p, color=BLUE)

ax.set_title('a.boundary.union(b.boundary)')

xrange = [-1, 4]
yrange = [-1, 3]
ax.set_xlim(*xrange)
ax.set_xticks(range(*xrange) + [xrange[-1]])
ax.set_ylim(*yrange)
ax.set_yticks(range(*yrange) + [yrange[-1]])
ax.set_aspect(1)

pyplot.show()


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Shapely documentation build configuration file, created by
# sphinx-quickstart on Mon Apr 12 11:07:08 2010.
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
sys.path.append(os.path.abspath('sphinxext'))

# Load latest source tree
sys.path.insert(0, os.path.abspath('..'))

import shapely

# For pyplots in code/, load functions here first, so they are visible
from shapely import geometry, affinity, wkt, wkb
from shapely.ops import cascaded_union

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'matplotlib.sphinxext.only_directives',
    'matplotlib.sphinxext.plot_directive',
    'sphinx.ext.autodoc',
    #'sphinx.ext.pngmath', # <----- pick one, not both
    'sphinx.ext.mathjax', # <--/
]

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Shapely'
copyright = '2011-2013, Sean Gillies, Aron Bierbaum, Kai Lautaportti ' \
            'and others'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = shapely.__version__
# The full version, including alpha/beta/rc tags.
release = shapely.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_theme = 'haiku'
html_theme = 'sphinxdoc'
# html_theme = 'shapely'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Shapely 1.2 and 1.3 documentation"

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
#html_static_path = ['_static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Shapelydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Shapely.tex', 'Shapely Documentation',
   'Sean Gillies', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = apigen
"""Attempt to generate templates for module reference with Sphinx

XXX - we exclude extension modules

To include extension modules, first identify them as valid in the
``_uri2path`` method, then handle them in the ``_parse_module`` script.

We get functions and classes by parsing the text of .py files.
Alternatively we could import the modules for discovery, and we'd have
to do that for extension modules.  This would involve changing the
``_parse_module`` method to work via import and introspection, and
might involve changing ``discover_modules`` (which determines which
files are modules, and therefore which module URIs will be passed to
``_parse_module``).

NOTE: this is a modified version of a script originally shipped with the
PyMVPA project, which we've adapted for NIPY use.  PyMVPA is an MIT-licensed
project."""

# Stdlib imports
import os
import re

# Functions and classes
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
        self.root_module = __import__(package_name)
        self.root_path = self.root_module.__path__[0]
        self.written_modules = None

    package_name = property(get_package_name, set_package_name, None,
                            'get/set package_name')

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
        path = uri.replace('.', os.path.sep)
        path = path.replace(self.package_name + os.path.sep, '')
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
        relpath = dirpath.replace(self.root_path, self.package_name)
        if relpath.startswith(os.path.sep):
            relpath = relpath[1:]
        return relpath.replace(os.path.sep, '.')

    def _parse_module(self, uri):
        ''' Parse module defined in *uri* '''
        filename = self._uri2path(uri)
        if filename is None:
            # nothing that we could handle here.
            return ([],[])
        f = open(filename, 'rt')
        functions, classes = self._parse_lines(f)
        f.close()
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
        functions, classes = self._parse_module(uri)
        if not len(functions) and not len(classes):
            print 'WARNING: Empty -',uri  # dbg
            return ''

        # Make a shorter version of the uri that omits the package name for
        # titles 
        uri_short = re.sub(r'^%s\.' % self.package_name,'',uri)
        
        ad = '.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n'

        chap_title = uri_short
        ad += (chap_title+'\n'+ self.rst_section_levels[1] * len(chap_title)
               + '\n\n')

        # Set the chapter title to read 'module' for all modules except for the
        # main packages
        if '.' in uri:
            title = 'Module: :mod:`' + uri_short + '`'
        else:
            title = ':mod:`' + uri_short + '`'
        ad += title + '\n' + self.rst_section_levels[2] * len(title)

        if len(classes):
            ad += '\nInheritance diagram for ``%s``:\n\n' % uri
            ad += '.. inheritance-diagram:: %s \n' % uri
            ad += '   :parts: 3\n'

        ad += '\n.. automodule:: ' + uri + '\n'
        ad += '\n.. currentmodule:: ' + uri + '\n'
        multi_class = len(classes) > 1
        multi_fx = len(functions) > 1
        if multi_class:
            ad += '\n' + 'Classes' + '\n' + \
                  self.rst_section_levels[2] * 7 + '\n'
        elif len(classes) and multi_fx:
            ad += '\n' + 'Class' + '\n' + \
                  self.rst_section_levels[2] * 5 + '\n'
        for c in classes:
            ad += '\n:class:`' + c + '`\n' \
                  + self.rst_section_levels[multi_class + 2 ] * \
                  (len(c)+9) + '\n\n'
            ad += '\n.. autoclass:: ' + c + '\n'
            # must NOT exclude from index to keep cross-refs working
            ad += '  :members:\n' \
                  '  :undoc-members:\n' \
                  '  :show-inheritance:\n' \
                  '  :inherited-members:\n' \
                  '\n' \
                  '  .. automethod:: __init__\n'
        if multi_fx:
            ad += '\n' + 'Functions' + '\n' + \
                  self.rst_section_levels[2] * 9 + '\n\n'
        elif len(functions) and multi_class:
            ad += '\n' + 'Function' + '\n' + \
                  self.rst_section_levels[2] * 8 + '\n\n'
        for f in functions:
            # must NOT exclude from index to keep cross-refs working
            ad += '\n.. autofunction:: ' + uri + '.' + f + '\n\n'
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
            relpath = outdir.replace(relative_to + os.path.sep, '')
        else:
            relpath = outdir
        idx = open(path,'wt')
        w = idx.write
        w('.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n')
        w('.. toctree::\n\n')
        for f in self.written_modules:
            w('   %s\n' % os.path.join(relpath,f))
        idx.close()

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
4
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
    def __init__(self,docstring):
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
    def __init__(self, func, role='func', doc=None):
        self._f = func
        self._role = role # e.g. "func" or "meth"
        if doc is None:
            doc = inspect.getdoc(func) or ''
        try:
            NumpyDocString.__init__(self, doc)
        except ValueError, e:
            print '*'*78
            print "ERROR: '%s' while parsing `%s`" % (e, self._f)
            print '*'*78
            #print "Docstring follows:"
            #print doclines
            #print '='*78

        if not self['Signature']:
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
    def __init__(self,cls,modulename='',func_doc=FunctionDoc,doc=None):
        if not inspect.isclass(cls):
            raise ValueError("Initialise using a class. Got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename
        self._name = cls.__name__
        self._func_doc = func_doc

        if doc is None:
            doc = pydoc.getdoc(cls)

        NumpyDocString.__init__(self, doc)

    @property
    def methods(self):
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and callable(func)]

    def __str__(self):
        out = ''
        out += super(ClassDoc, self).__str__()
        out += "\n\n"

        #for m in self.methods:
        #    print "Parsing `%s`" % m
        #    out += str(self._func_doc(getattr(self._cls,m), 'meth')) + '\n\n'
        #    out += '.. index::\n   single: %s; %s\n\n' % (self._name, m)

        return out



########NEW FILE########
__FILENAME__ = docscrape_sphinx
import re, inspect, textwrap, pydoc
from docscrape import NumpyDocString, FunctionDoc, ClassDoc

class SphinxDocString(NumpyDocString):
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
        return out

    def __str__(self, indent=0, func_role="obj"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Attributes', 'Methods',
                           'Returns','Raises'):
            out += self._str_param_list(param_list)
        out += self._str_warnings()
        out += self._str_see_also(func_role)
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_section('Examples')
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class SphinxFunctionDoc(SphinxDocString, FunctionDoc):
    pass

class SphinxClassDoc(SphinxDocString, ClassDoc):
    pass

def get_doc_object(obj, what=None, doc=None):
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
        return SphinxClassDoc(obj, '', func_doc=SphinxFunctionDoc, doc=doc)
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, '', doc=doc)
    else:
        if doc is None:
            doc = pydoc.getdoc(obj)
        return SphinxDocString(doc)


########NEW FILE########
__FILENAME__ = inheritance_diagram
"""
Defines a docutils directive for inserting inheritance diagrams.

Provide the directive with one or more classes or modules (separated
by whitespace).  For modules, all of the classes in that module will
be used.

Example::

   Given the following classes:

   class A: pass
   class B(A): pass
   class C(A): pass
   class D(B, C): pass
   class E(B): pass

   .. inheritance-diagram: D E

   Produces a graph like the following:

               A
              / \
             B   C
            / \ /
           E   D

The graph is inserted as a PNG+image map into HTML and a PDF in
LaTeX.
"""

import inspect
import os
import re
import subprocess
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from docutils.nodes import Body, Element
from docutils.parsers.rst import directives
from sphinx.roles import xfileref_role

def my_import(name):
    """Module importer - taken from the python documentation.

    This function allows importing names with dots in them."""
    
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

class DotException(Exception):
    pass

class InheritanceGraph(object):
    """
    Given a list of classes, determines the set of classes that
    they inherit from all the way to the root "object", and then
    is able to generate a graphviz dot graph from them.
    """
    def __init__(self, class_names, show_builtins=False):
        """
        *class_names* is a list of child classes to show bases from.

        If *show_builtins* is True, then Python builtins will be shown
        in the graph.
        """
        self.class_names = class_names
        self.classes = self._import_classes(class_names)
        self.all_classes = self._all_classes(self.classes)
        if len(self.all_classes) == 0:
            raise ValueError("No classes found for inheritance diagram")
        self.show_builtins = show_builtins

    py_sig_re = re.compile(r'''^([\w.]*\.)?    # class names
                           (\w+)  \s* $        # optionally arguments
                           ''', re.VERBOSE)

    def _import_class_or_module(self, name):
        """
        Import a class using its fully-qualified *name*.
        """
        try:
            path, base = self.py_sig_re.match(name).groups()
        except:
            raise ValueError(
                "Invalid class or module '%s' specified for inheritance diagram" % name)
        fullname = (path or '') + base
        path = (path and path.rstrip('.'))
        if not path:
            path = base
        try:
            module = __import__(path, None, None, [])
            # We must do an import of the fully qualified name.  Otherwise if a
            # subpackage 'a.b' is requested where 'import a' does NOT provide
            # 'a.b' automatically, then 'a.b' will not be found below.  This
            # second call will force the equivalent of 'import a.b' to happen
            # after the top-level import above.
            my_import(fullname)
            
        except ImportError:
            raise ValueError(
                "Could not import class or module '%s' specified for inheritance diagram" % name)

        try:
            todoc = module
            for comp in fullname.split('.')[1:]:
                todoc = getattr(todoc, comp)
        except AttributeError:
            raise ValueError(
                "Could not find class or module '%s' specified for inheritance diagram" % name)

        # If a class, just return it
        if inspect.isclass(todoc):
            return [todoc]
        elif inspect.ismodule(todoc):
            classes = []
            for cls in todoc.__dict__.values():
                if inspect.isclass(cls) and cls.__module__ == todoc.__name__:
                    classes.append(cls)
            return classes
        raise ValueError(
            "'%s' does not resolve to a class or module" % name)

    def _import_classes(self, class_names):
        """
        Import a list of classes.
        """
        classes = []
        for name in class_names:
            classes.extend(self._import_class_or_module(name))
        return classes

    def _all_classes(self, classes):
        """
        Return a list of all classes that are ancestors of *classes*.
        """
        all_classes = {}

        def recurse(cls):
            all_classes[cls] = None
            for c in cls.__bases__:
                if c not in all_classes:
                    recurse(c)

        for cls in classes:
            recurse(cls)

        return all_classes.keys()

    def class_name(self, cls, parts=0):
        """
        Given a class object, return a fully-qualified name.  This
        works for things I've tested in matplotlib so far, but may not
        be completely general.
        """
        module = cls.__module__
        if module == '__builtin__':
            fullname = cls.__name__
        else:
            fullname = "%s.%s" % (module, cls.__name__)
        if parts == 0:
            return fullname
        name_parts = fullname.split('.')
        return '.'.join(name_parts[-parts:])

    def get_all_class_names(self):
        """
        Get all of the class names involved in the graph.
        """
        return [self.class_name(x) for x in self.all_classes]

    # These are the default options for graphviz
    default_graph_options = {
        "rankdir": "LR",
        "size": '"8.0, 12.0"'
        }
    default_node_options = {
        "shape": "box",
        "fontsize": 10,
        "height": 0.25,
        "fontname": "Vera Sans, DejaVu Sans, Liberation Sans, Arial, Helvetica, sans",
        "style": '"setlinewidth(0.5)"'
        }
    default_edge_options = {
        "arrowsize": 0.5,
        "style": '"setlinewidth(0.5)"'
        }

    def _format_node_options(self, options):
        return ','.join(["%s=%s" % x for x in options.items()])
    def _format_graph_options(self, options):
        return ''.join(["%s=%s;\n" % x for x in options.items()])

    def generate_dot(self, fd, name, parts=0, urls={},
                     graph_options={}, node_options={},
                     edge_options={}):
        """
        Generate a graphviz dot graph from the classes that
        were passed in to __init__.

        *fd* is a Python file-like object to write to.

        *name* is the name of the graph

        *urls* is a dictionary mapping class names to http urls

        *graph_options*, *node_options*, *edge_options* are
        dictionaries containing key/value pairs to pass on as graphviz
        properties.
        """
        g_options = self.default_graph_options.copy()
        g_options.update(graph_options)
        n_options = self.default_node_options.copy()
        n_options.update(node_options)
        e_options = self.default_edge_options.copy()
        e_options.update(edge_options)

        fd.write('digraph %s {\n' % name)
        fd.write(self._format_graph_options(g_options))

        for cls in self.all_classes:
            if not self.show_builtins and cls in __builtins__.values():
                continue

            name = self.class_name(cls, parts)

            # Write the node
            this_node_options = n_options.copy()
            url = urls.get(self.class_name(cls))
            if url is not None:
                this_node_options['URL'] = '"%s"' % url
            fd.write('  "%s" [%s];\n' %
                     (name, self._format_node_options(this_node_options)))

            # Write the edges
            for base in cls.__bases__:
                if not self.show_builtins and base in __builtins__.values():
                    continue

                base_name = self.class_name(base, parts)
                fd.write('  "%s" -> "%s" [%s];\n' %
                         (base_name, name,
                          self._format_node_options(e_options)))
        fd.write('}\n')

    def run_dot(self, args, name, parts=0, urls={},
                graph_options={}, node_options={}, edge_options={}):
        """
        Run graphviz 'dot' over this graph, returning whatever 'dot'
        writes to stdout.

        *args* will be passed along as commandline arguments.

        *name* is the name of the graph

        *urls* is a dictionary mapping class names to http urls

        Raises DotException for any of the many os and
        installation-related errors that may occur.
        """
        try:
            dot = subprocess.Popen(['dot'] + list(args),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   close_fds=True)
        except OSError:
            raise DotException("Could not execute 'dot'.  Are you sure you have 'graphviz' installed?")
        except ValueError:
            raise DotException("'dot' called with invalid arguments")
        except:
            raise DotException("Unexpected error calling 'dot'")

        self.generate_dot(dot.stdin, name, parts, urls, graph_options,
                          node_options, edge_options)
        dot.stdin.close()
        result = dot.stdout.read()
        returncode = dot.wait()
        if returncode != 0:
            raise DotException("'dot' returned the errorcode %d" % returncode)
        return result

class inheritance_diagram(Body, Element):
    """
    A docutils node to use as a placeholder for the inheritance
    diagram.
    """
    pass

def inheritance_diagram_directive(name, arguments, options, content, lineno,
                                  content_offset, block_text, state,
                                  state_machine):
    """
    Run when the inheritance_diagram directive is first encountered.
    """
    node = inheritance_diagram()

    class_names = arguments

    # Create a graph starting with the list of classes
    graph = InheritanceGraph(class_names)

    # Create xref nodes for each target of the graph's image map and
    # add them to the doc tree so that Sphinx can resolve the
    # references to real URLs later.  These nodes will eventually be
    # removed from the doctree after we're done with them.
    for name in graph.get_all_class_names():
        refnodes, x = xfileref_role(
            'class', ':class:`%s`' % name, name, 0, state)
        node.extend(refnodes)
    # Store the graph object so we can use it to generate the
    # dot file later
    node['graph'] = graph
    # Store the original content for use as a hash
    node['parts'] = options.get('parts', 0)
    node['content'] = " ".join(class_names)
    return [node]

def get_graph_hash(node):
    return md5(node['content'] + str(node['parts'])).hexdigest()[-10:]

def html_output_graph(self, node):
    """
    Output the graph for HTML.  This will insert a PNG with clickable
    image map.
    """
    graph = node['graph']
    parts = node['parts']

    graph_hash = get_graph_hash(node)
    name = "inheritance%s" % graph_hash
    path = '_images'
    dest_path = os.path.join(setup.app.builder.outdir, path)
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    png_path = os.path.join(dest_path, name + ".png")
    path = setup.app.builder.imgpath

    # Create a mapping from fully-qualified class names to URLs.
    urls = {}
    for child in node:
        if child.get('refuri') is not None:
            urls[child['reftitle']] = child.get('refuri')
        elif child.get('refid') is not None:
            urls[child['reftitle']] = '#' + child.get('refid')

    # These arguments to dot will save a PNG file to disk and write
    # an HTML image map to stdout.
    image_map = graph.run_dot(['-Tpng', '-o%s' % png_path, '-Tcmapx'],
                              name, parts, urls)
    return ('<img src="%s/%s.png" usemap="#%s" class="inheritance"/>%s' %
            (path, name, name, image_map))

def latex_output_graph(self, node):
    """
    Output the graph for LaTeX.  This will insert a PDF.
    """
    graph = node['graph']
    parts = node['parts']

    graph_hash = get_graph_hash(node)
    name = "inheritance%s" % graph_hash
    dest_path = os.path.abspath(os.path.join(setup.app.builder.outdir, '_images'))
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    pdf_path = os.path.abspath(os.path.join(dest_path, name + ".pdf"))

    graph.run_dot(['-Tpdf', '-o%s' % pdf_path],
                  name, parts, graph_options={'size': '"6.0,6.0"'})
    return '\n\\includegraphics{%s}\n\n' % pdf_path

def visit_inheritance_diagram(inner_func):
    """
    This is just a wrapper around html/latex_output_graph to make it
    easier to handle errors and insert warnings.
    """
    def visitor(self, node):
        try:
            content = inner_func(self, node)
        except DotException, e:
            # Insert the exception as a warning in the document
            warning = self.document.reporter.warning(str(e), line=node.line)
            warning.parent = node
            node.children = [warning]
        else:
            source = self.document.attributes['source']
            self.body.append(content)
            node.children = []
    return visitor

def do_nothing(self, node):
    pass

def setup(app):
    setup.app = app
    setup.confdir = app.confdir

    app.add_node(
        inheritance_diagram,
        latex=(visit_inheritance_diagram(latex_output_graph), do_nothing),
        html=(visit_inheritance_diagram(html_output_graph), do_nothing))
    app.add_directive(
        'inheritance-diagram', inheritance_diagram_directive,
        False, (1, 100, 0), parts = directives.nonnegative_int)

########NEW FILE########
__FILENAME__ = ipython_console_highlighting
"""reST directive for syntax-highlighting ipython interactive sessions.

XXX - See what improvements can be made based on the new (as of Sept 2009)
'pycon' lexer for the python console.  At the very least it will give better
highlighted tracebacks.
"""

#-----------------------------------------------------------------------------
# Needed modules

# Standard library
import re

# Third party
from pygments.lexer import Lexer, do_insertions
from pygments.lexers.agile import (PythonConsoleLexer, PythonLexer, 
                                   PythonTracebackLexer)
from pygments.token import Comment, Generic

from sphinx import highlighting

#-----------------------------------------------------------------------------
# Global constants
line_re = re.compile('.*?\n')

#-----------------------------------------------------------------------------
# Code begins - classes and functions

class IPythonConsoleLexer(Lexer):
    """
    For IPython console output or doctests, such as:

    .. sourcecode:: ipython

      In [1]: a = 'foo'

      In [2]: a
      Out[2]: 'foo'

      In [3]: print a
      foo

      In [4]: 1 / 0

    Notes:

      - Tracebacks are not currently supported.

      - It assumes the default IPython prompts, not customized ones.
    """
    
    name = 'IPython console session'
    aliases = ['ipython']
    mimetypes = ['text/x-ipython-console']
    input_prompt = re.compile("(In \[[0-9]+\]: )|(   \.\.\.+:)")
    output_prompt = re.compile("(Out\[[0-9]+\]: )|(   \.\.\.+:)")
    continue_prompt = re.compile("   \.\.\.+:")
    tb_start = re.compile("\-+")

    def get_tokens_unprocessed(self, text):
        pylexer = PythonLexer(**self.options)
        tblexer = PythonTracebackLexer(**self.options)

        curcode = ''
        insertions = []
        for match in line_re.finditer(text):
            line = match.group()
            input_prompt = self.input_prompt.match(line)
            continue_prompt = self.continue_prompt.match(line.rstrip())
            output_prompt = self.output_prompt.match(line)
            if line.startswith("#"):
                insertions.append((len(curcode),
                                   [(0, Comment, line)]))
            elif input_prompt is not None:
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, input_prompt.group())]))
                curcode += line[input_prompt.end():]
            elif continue_prompt is not None:
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, continue_prompt.group())]))
                curcode += line[continue_prompt.end():]
            elif output_prompt is not None:
                # Use the 'error' token for output.  We should probably make
                # our own token, but error is typicaly in a bright color like
                # red, so it works fine for our output prompts.
                insertions.append((len(curcode),
                                   [(0, Generic.Error, output_prompt.group())]))
                curcode += line[output_prompt.end():]
            else:
                if curcode:
                    for item in do_insertions(insertions,
                                              pylexer.get_tokens_unprocessed(curcode)):
                        yield item
                        curcode = ''
                        insertions = []
                yield match.start(), Generic.Output, line
        if curcode:
            for item in do_insertions(insertions,
                                      pylexer.get_tokens_unprocessed(curcode)):
                yield item


def setup(app):
    """Setup as a sphinx extension."""

    # This is only a lexer, so adding it below to pygments appears sufficient.
    # But if somebody knows that the right API usage should be to do that via
    # sphinx, by all means fix it here.  At least having this setup.py
    # suppresses the sphinx warning we'd get without it.
    pass

#-----------------------------------------------------------------------------
# Register the extension as a valid pygments lexer
highlighting.lexers['ipython'] = IPythonConsoleLexer()

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

.. [1] http://projects.scipy.org/scipy/numpy/wiki/CodingStyleGuidelines#docstring-standard

"""

import os, re, pydoc
from docscrape_sphinx import get_doc_object, SphinxDocString
import inspect

def mangle_docstrings(app, what, name, obj, options, lines,
                      reference_offset=[0]):
    if what == 'module':
        # Strip top title
        title_re = re.compile(r'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                              re.I|re.S)
        lines[:] = title_re.sub('', "\n".join(lines)).split("\n")
    else:
        doc = get_doc_object(obj, what, "\n".join(lines))
        lines[:] = str(doc).split("\n")

    if app.config.numpydoc_edit_link and hasattr(obj, '__name__') and \
           obj.__name__:
        if hasattr(obj, '__module__'):
            v = dict(full_name="%s.%s" % (obj.__module__, obj.__name__))
        else:
            v = dict(full_name=obj.__name__)
        lines += ['', '.. htmlonly::', '']
        lines += ['    %s' % x for x in
                  (app.config.numpydoc_edit_link % v).split("\n")]

    # replace reference numbers so that there are no duplicates
    references = []
    for l in lines:
        l = l.strip()
        if l.startswith('.. ['):
            try:
                references.append(int(l[len('.. ['):l.index(']')]))
            except ValueError:
                print "WARNING: invalid reference in %s docstring" % name

    # Start renaming from the biggest number, otherwise we may
    # overwrite references.
    references.sort()
    if references:
        for i, line in enumerate(lines):
            for r in references:
                new_r = reference_offset[0] + r
                lines[i] = lines[i].replace('[%d]_' % r,
                                            '[%d]_' % new_r)
                lines[i] = lines[i].replace('.. [%d]' % r,
                                            '.. [%d]' % new_r)

    reference_offset[0] += len(references)

def mangle_signature(app, what, name, obj, options, sig, retann):
    # Do not try to inspect classes that don't define `__init__`
    if (inspect.isclass(obj) and
        'initializes x; see ' in pydoc.getdoc(obj.__init__)):
        return '', ''

    if not (callable(obj) or hasattr(obj, '__argspec_is_invalid_')): return
    if not hasattr(obj, '__doc__'): return

    doc = SphinxDocString(pydoc.getdoc(obj))
    if doc['Signature']:
        sig = re.sub("^[^(]*", "", doc['Signature'])
        return sig, ''

def initialize(app):
    try:
        app.connect('autodoc-process-signature', mangle_signature)
    except:
        monkeypatch_sphinx_ext_autodoc()

def setup(app, get_doc_object_=get_doc_object):
    global get_doc_object
    get_doc_object = get_doc_object_
    
    app.connect('autodoc-process-docstring', mangle_docstrings)
    app.connect('builder-inited', initialize)
    app.add_config_value('numpydoc_edit_link', None, True)

#------------------------------------------------------------------------------
# Monkeypatch sphinx.ext.autodoc to accept argspecless autodocs (Sphinx < 0.5)
#------------------------------------------------------------------------------

def monkeypatch_sphinx_ext_autodoc():
    global _original_format_signature
    import sphinx.ext.autodoc

    if sphinx.ext.autodoc.format_signature is our_format_signature:
        return

    print "[numpydoc] Monkeypatching sphinx.ext.autodoc ..."
    _original_format_signature = sphinx.ext.autodoc.format_signature
    sphinx.ext.autodoc.format_signature = our_format_signature

def our_format_signature(what, obj):
    r = mangle_signature(None, what, None, obj, None, None, None)
    if r is not None:
        return r[0]
    else:
        return _original_format_signature(what, obj)

########NEW FILE########
__FILENAME__ = affinity
"""Affine transforms, both in general and specific, named transforms."""

from math import sin, cos, tan, pi

__all__ = ['affine_transform', 'rotate', 'scale', 'skew', 'translate']


def affine_transform(geom, matrix):
    """Returns a transformed geometry using an affine transformation matrix.

    The coefficient matrix is provided as a list or tuple with 6 or 12 items
    for 2D or 3D transformations, respectively.

    For 2D affine transformations, the 6 parameter matrix is:

        [a, b, d, e, xoff, yoff]

    which represents the augmented matrix:

                            / a  b xoff \ 
        [x' y' 1] = [x y 1] | d  e yoff |
                            \ 0  0   1  /

    or the equations for the transformed coordinates:

        x' = a * x + b * y + xoff
        y' = d * x + e * y + yoff

    For 3D affine transformations, the 12 parameter matrix is:

        [a, b, c, d, e, f, g, h, i, xoff, yoff, zoff]

    which represents the augmented matrix:

                                 / a  b  c xoff \ 
        [x' y' z' 1] = [x y z 1] | d  e  f yoff |
                                 | g  h  i zoff |
                                 \ 0  0  0   1  /

    or the equations for the transformed coordinates:

        x' = a * x + b * y + c * z + xoff
        y' = d * x + e * y + f * z + yoff
        z' = g * x + h * y + i * z + zoff
    """
    if geom.is_empty:
        return geom
    if len(matrix) == 6:
        ndim = 2
        a, b, d, e, xoff, yoff = matrix
        if geom.has_z:
            ndim = 3
            i = 1.0
            c = f = g = h = zoff = 0.0
            matrix = a, b, c, d, e, f, g, h, i, xoff, yoff, zoff
    elif len(matrix) == 12:
        ndim = 3
        a, b, c, d, e, f, g, h, i, xoff, yoff, zoff = matrix
        if not geom.has_z:
            ndim = 2
            matrix = a, b, d, e, xoff, yoff
    else:
        raise ValueError("'matrix' expects either 6 or 12 coefficients")

    def affine_pts(pts):
        """Internal function to yield affine transform of coordinate tuples"""
        if ndim == 2:
            for x, y in pts:
                xp = a * x + b * y + xoff
                yp = d * x + e * y + yoff
                yield (xp, yp)
        elif ndim == 3:
            for x, y, z in pts:
                xp = a * x + b * y + c * z + xoff
                yp = d * x + e * y + f * z + yoff
                zp = g * x + h * y + i * z + zoff
                yield (xp, yp, zp)

    # Process coordinates from each supported geometry type
    if geom.type in ('Point', 'LineString', 'LinearRing'):
        return type(geom)(list(affine_pts(geom.coords)))
    elif geom.type == 'Polygon':
        ring = geom.exterior
        shell = type(ring)(list(affine_pts(ring.coords)))
        holes = list(geom.interiors)
        for pos, ring in enumerate(holes):
            holes[pos] = type(ring)(list(affine_pts(ring.coords)))
        return type(geom)(shell, holes)
    elif geom.type.startswith('Multi') or geom.type == 'GeometryCollection':
        # Recursive call
        # TODO: fix GeometryCollection constructor
        return type(geom)([affine_transform(part, matrix)
                           for part in geom.geoms])
    else:
        raise ValueError('Type %r not recognized' % geom.type)


def interpret_origin(geom, origin, ndim):
    """Returns interpreted coordinate tuple for origin parameter.

    This is a helper function for other transform functions.

    The point of origin can be a keyword 'center' for the 2D bounding box
    center, 'centroid' for the geometry's 2D centroid, a Point object or a
    coordinate tuple (x0, y0, z0).
    """
    # get coordinate tuple from 'origin' from keyword or Point type
    if origin == 'center':
        # bounding box center
        minx, miny, maxx, maxy = geom.bounds
        origin = ((maxx + minx)/2.0, (maxy + miny)/2.0)
    elif origin == 'centroid':
        origin = geom.centroid.coords[0]
    elif isinstance(origin, str):
        raise ValueError("'origin' keyword %r is not recognized" % origin)
    elif hasattr(origin, 'type') and origin.type == 'Point':
        origin = origin.coords[0]

    # origin should now be tuple-like
    if len(origin) not in (2, 3):
        raise ValueError("Expected number of items in 'origin' to be "
                         "either 2 or 3")
    if ndim == 2:
        return origin[0:2]
    else:  # 3D coordinate
        if len(origin) == 2:
            return origin + (0.0,)
        else:
            return origin


def rotate(geom, angle, origin='center', use_radians=False):
    """Returns a rotated geometry on a 2D plane.

    The angle of rotation can be specified in either degrees (default) or
    radians by setting ``use_radians=True``. Positive angles are
    counter-clockwise and negative are clockwise rotations.

    The point of origin can be a keyword 'center' for the bounding box
    center (default), 'centroid' for the geometry's centroid, a Point object
    or a coordinate tuple (x0, y0).

    The affine transformation matrix for 2D rotation is:

      / cos(r) -sin(r) xoff \ 
      | sin(r)  cos(r) yoff |
      \   0       0      1  /

    where the offsets are calculated from the origin Point(x0, y0):

        xoff = x0 - x0 * cos(r) + y0 * sin(r)
        yoff = y0 - x0 * sin(r) - y0 * cos(r)
    """
    if not use_radians:  # convert from degrees
        angle *= pi/180.0
    cosp = cos(angle)
    sinp = sin(angle)
    if abs(cosp) < 2.5e-16:
        cosp = 0.0
    if abs(sinp) < 2.5e-16:
        sinp = 0.0
    x0, y0 = interpret_origin(geom, origin, 2)

    matrix = (cosp, -sinp, 0.0,
              sinp,  cosp, 0.0,
              0.0,    0.0, 1.0,
              x0 - x0 * cosp + y0 * sinp, y0 - x0 * sinp - y0 * cosp, 0.0)
    return affine_transform(geom, matrix)


def scale(geom, xfact=1.0, yfact=1.0, zfact=1.0, origin='center'):
    """Returns a scaled geometry, scaled by factors along each dimension.

    The point of origin can be a keyword 'center' for the 2D bounding box
    center (default), 'centroid' for the geometry's 2D centroid, a Point
    object or a coordinate tuple (x0, y0, z0).

    Negative scale factors will mirror or reflect coordinates.

    The general 3D affine transformation matrix for scaling is:

        / xfact  0    0   xoff \ 
        |   0  yfact  0   yoff |
        |   0    0  zfact zoff |
        \   0    0    0     1  /

    where the offsets are calculated from the origin Point(x0, y0, z0):

        xoff = x0 - x0 * xfact
        yoff = y0 - y0 * yfact
        zoff = z0 - z0 * zfact
    """
    x0, y0, z0 = interpret_origin(geom, origin, 3)

    matrix = (xfact, 0.0, 0.0,
              0.0, yfact, 0.0,
              0.0, 0.0, zfact,
              x0 - x0 * xfact, y0 - y0 * yfact, z0 - z0 * zfact)
    return affine_transform(geom, matrix)


def skew(geom, xs=0.0, ys=0.0, origin='center', use_radians=False):
    """Returns a skewed geometry, sheared by angles along x and y dimensions.

    The shear angle can be specified in either degrees (default) or radians
    by setting ``use_radians=True``.

    The point of origin can be a keyword 'center' for the bounding box
    center (default), 'centroid' for the geometry's centroid, a Point object
    or a coordinate tuple (x0, y0).

    The general 2D affine transformation matrix for skewing is:

        /   1    tan(xs) xoff \ 
        | tan(ys)  1     yoff |
        \   0      0       1  /

    where the offsets are calculated from the origin Point(x0, y0):

        xoff = -y0 * tan(xs)
        yoff = -x0 * tan(ys)
    """
    if not use_radians:  # convert from degrees
        xs *= pi/180.0
        ys *= pi/180.0
    tanx = tan(xs)
    tany = tan(ys)
    if abs(tanx) < 2.5e-16:
        tanx = 0.0
    if abs(tany) < 2.5e-16:
        tany = 0.0
    x0, y0 = interpret_origin(geom, origin, 2)

    matrix = (1.0, tanx, 0.0,
              tany, 1.0, 0.0,
              0.0,  0.0, 1.0,
              -y0 * tanx, -x0 * tany, 0.0)
    return affine_transform(geom, matrix)


def translate(geom, xoff=0.0, yoff=0.0, zoff=0.0):
    """Returns a translated geometry shifted by offsets along each dimension.

    The general 3D affine transformation matrix for translation is:

        / 1  0  0 xoff \ 
        | 0  1  0 yoff |
        | 0  0  1 zoff |
        \ 0  0  0   1  /
    """
    matrix = (1.0, 0.0, 0.0,
              0.0, 1.0, 0.0,
              0.0, 0.0, 1.0,
              xoff, yoff, zoff)
    return affine_transform(geom, matrix)

########NEW FILE########
__FILENAME__ = cga

def signed_area(ring):
    """Return the signed area enclosed by a ring in linear time using the 
    algorithm at: http://www.cgafaq.info/wiki/Polygon_Area.
    """
    xs, ys = ring.coords.xy
    xs.append(xs[1])
    ys.append(ys[1])
    return sum(xs[i]*(ys[i+1]-ys[i-1]) for i in range(1, len(ring.coords)))/2.0

def is_ccw_impl(name):
    """Predicate implementation"""
    def is_ccw_op(ring):
        return signed_area(ring) >= 0.0
    return is_ccw_op


########NEW FILE########
__FILENAME__ = coords
"""Coordinate sequence utilities
"""

import sys
from array import array
from ctypes import byref, c_double, c_uint

from shapely.geos import lgeos
from shapely.topology import Validating

if sys.version_info[0] < 3:
    range = xrange

try:
    import numpy
    has_numpy = True
except ImportError:
    has_numpy = False

def required(ob):
    """Return an object that meets Shapely requirements for self-owned
    C-continguous data, copying if necessary, or just return the original
    object."""
    if (hasattr(ob, '__array_interface__')
            and ob.__array_interface__.get('strides')):
        if has_numpy:
            return numpy.require(ob, numpy.float64, ["C", "OWNDATA"])
        else:
            # raise an error if strided. See issue #52.
            raise ValueError("C-contiguous data is required")
    else:
        return ob


class CoordinateSequence(object):
    """
    Iterative access to coordinate tuples from the parent geometry's coordinate
    sequence.

    Example:

      >>> from shapely.wkt import loads
      >>> g = loads('POINT (0.0 0.0)')
      >>> list(g.coords)
      [(0.0, 0.0)]

    """

    # Attributes
    # ----------
    # _cseq : c_void_p
    #     Ctypes pointer to GEOS coordinate sequence
    # _ndim : int
    #     Number of dimensions (2 or 3, generally)
    # __p__ : object
    #     Parent (Shapely) geometry
    _cseq = None
    _ndim = None
    __p__ = None

    def __init__(self, parent):
        self.__p__ = parent

    def _update(self):
        self._ndim = self.__p__._ndim
        self._cseq = lgeos.GEOSGeom_getCoordSeq(self.__p__._geom)

    def __len__(self):
        self._update()
        cs_len = c_uint(0)
        lgeos.GEOSCoordSeq_getSize(self._cseq, byref(cs_len))
        return cs_len.value

    def __iter__(self):
        self._update()
        dx = c_double()
        dy = c_double()
        dz = c_double()
        has_z = self._ndim == 3
        for i in range(self.__len__()):
            lgeos.GEOSCoordSeq_getX(self._cseq, i, byref(dx))
            lgeos.GEOSCoordSeq_getY(self._cseq, i, byref(dy))
            if has_z:
                lgeos.GEOSCoordSeq_getZ(self._cseq, i, byref(dz))
                yield (dx.value, dy.value, dz.value)
            else:
                yield (dx.value, dy.value)

    def __getitem__(self, key):
        self._update()
        dx = c_double()
        dy = c_double()
        dz = c_double()
        m = self.__len__()
        has_z = self._ndim == 3
        if isinstance(key, int):
            if key + m < 0 or key >= m:
                raise IndexError("index out of range")
            if key < 0:
                i = m + key
            else:
                i = key
            lgeos.GEOSCoordSeq_getX(self._cseq, i, byref(dx))
            lgeos.GEOSCoordSeq_getY(self._cseq, i, byref(dy))
            if has_z:
                lgeos.GEOSCoordSeq_getZ(self._cseq, i, byref(dz))
                return (dx.value, dy.value, dz.value)
            else:
                return (dx.value, dy.value)
        elif isinstance(key, slice):
            res = []
            start, stop, stride = key.indices(m)
            for i in range(start, stop, stride):
                lgeos.GEOSCoordSeq_getX(self._cseq, i, byref(dx))
                lgeos.GEOSCoordSeq_getY(self._cseq, i, byref(dy))
                if has_z:
                    lgeos.GEOSCoordSeq_getZ(self._cseq, i, byref(dz))
                    res.append((dx.value, dy.value, dz.value))
                else:
                    res.append((dx.value, dy.value))
            return res
        else:
            raise TypeError("key must be an index or slice")

    @property
    def ctypes(self):
        self._update()
        has_z = self._ndim == 3
        n = self._ndim
        m = self.__len__()
        array_type = c_double * (m * n)
        data = array_type()
        temp = c_double()
        for i in range(m):
            lgeos.GEOSCoordSeq_getX(self._cseq, i, byref(temp))
            data[n*i] = temp.value
            lgeos.GEOSCoordSeq_getY(self._cseq, i, byref(temp))
            data[n*i+1] = temp.value
            if has_z:
                lgeos.GEOSCoordSeq_getZ(self._cseq, i, byref(temp))
                data[n*i+2] = temp.value
        return data

    def array_interface(self):
        """Provide the Numpy array protocol."""
        if sys.byteorder == 'little':
            typestr = '<f8'
        elif sys.byteorder == 'big':
            typestr = '>f8'
        else:
            raise ValueError(
                "Unsupported byteorder: neither little nor big-endian")
        ai = {
            'version': 3,
            'typestr': typestr,
            'data': self.ctypes,
            }
        ai.update({'shape': (len(self), self._ndim)})
        return ai
    
    __array_interface__ = property(array_interface)
    
    @property
    def xy(self):
        """X and Y arrays"""
        self._update()
        m = self.__len__()
        x = array('d')
        y = array('d')
        temp = c_double()
        for i in range(m):
            lgeos.GEOSCoordSeq_getX(self._cseq, i, byref(temp))
            x.append(temp.value)
            lgeos.GEOSCoordSeq_getY(self._cseq, i, byref(temp))
            y.append(temp.value)
        return x, y


class BoundsOp(Validating):

    def __init__(self, *args):
        pass

    def __call__(self, this):
        self._validate(this)
        env = this.envelope
        if env.geom_type == 'Point':
            return env.bounds
        cs = lgeos.GEOSGeom_getCoordSeq(env.exterior._geom)
        cs_len = c_uint(0)
        lgeos.GEOSCoordSeq_getSize(cs, byref(cs_len))
        minx = 1.e+20
        maxx = -1e+20
        miny = 1.e+20
        maxy = -1e+20
        temp = c_double()
        for i in range(cs_len.value):
            lgeos.GEOSCoordSeq_getX(cs, i, byref(temp))
            x = temp.value
            if x < minx: minx = x
            if x > maxx: maxx = x
            lgeos.GEOSCoordSeq_getY(cs, i, byref(temp))
            y = temp.value
            if y < miny: miny = y
            if y > maxy: maxy = y
        return (minx, miny, maxx, maxy)

########NEW FILE########
__FILENAME__ = ctypes_declarations
'''Prototyping of the GEOS C API

See header file: geos-x.y.z/capi/geos_c.h
'''

from ctypes import CFUNCTYPE, POINTER, c_void_p, c_char_p, \
    c_size_t, c_byte, c_char, c_uint, c_int, c_double

# Derived pointer types
c_size_t_p = POINTER(c_size_t)


class allocated_c_char_p(c_char_p):
    '''char pointer return type'''
    pass

EXCEPTION_HANDLER_FUNCTYPE = CFUNCTYPE(None, c_char_p, c_char_p)


def prototype(lgeos, geos_version):
    '''Protype functions in geos_c.h for different version of GEOS

    Use the GEOS version, not the C API version.
    '''

    '''
    Initialization, cleanup, version
    '''

    lgeos.initGEOS.restype = None
    lgeos.initGEOS.argtypes = [EXCEPTION_HANDLER_FUNCTYPE, EXCEPTION_HANDLER_FUNCTYPE]

    lgeos.finishGEOS.restype = None
    lgeos.finishGEOS.argtypes = []

    lgeos.GEOSversion.restype = c_char_p
    lgeos.GEOSversion.argtypes = []

    '''
    NOTE - These functions are DEPRECATED.  Please use the new Reader and
    writer APIS!
    '''

    lgeos.GEOSGeomFromWKT.restype = c_void_p
    lgeos.GEOSGeomFromWKT.argtypes = [c_char_p]

    lgeos.GEOSGeomToWKT.restype = allocated_c_char_p
    lgeos.GEOSGeomToWKT.argtypes = [c_void_p]

    lgeos.GEOS_setWKBOutputDims.restype = c_int
    lgeos.GEOS_setWKBOutputDims.argtypes = [c_int]

    lgeos.GEOSGeomFromWKB_buf.restype = c_void_p
    lgeos.GEOSGeomFromWKB_buf.argtypes = [c_void_p, c_size_t]

    lgeos.GEOSGeomToWKB_buf.restype = allocated_c_char_p
    lgeos.GEOSGeomToWKB_buf.argtypes = [c_void_p, c_size_t_p]

    '''
    Coordinate sequence
    '''

    lgeos.GEOSCoordSeq_create.restype = c_void_p
    lgeos.GEOSCoordSeq_create.argtypes = [c_uint, c_uint]

    lgeos.GEOSCoordSeq_clone.restype = c_void_p
    lgeos.GEOSCoordSeq_clone.argtypes = [c_void_p]

    lgeos.GEOSCoordSeq_destroy.restype = None
    lgeos.GEOSCoordSeq_destroy.argtypes = [c_void_p]

    lgeos.GEOSCoordSeq_setX.restype = c_int
    lgeos.GEOSCoordSeq_setX.argtypes = [c_void_p, c_uint, c_double]

    lgeos.GEOSCoordSeq_setY.restype = c_int
    lgeos.GEOSCoordSeq_setY.argtypes = [c_void_p, c_uint, c_double]

    lgeos.GEOSCoordSeq_setZ.restype = c_int
    lgeos.GEOSCoordSeq_setZ.argtypes = [c_void_p, c_uint, c_double]

    lgeos.GEOSCoordSeq_setOrdinate.restype = c_int
    lgeos.GEOSCoordSeq_setOrdinate.argtypes = [c_void_p, c_uint, c_uint, c_double]

    lgeos.GEOSCoordSeq_getX.restype = c_int
    lgeos.GEOSCoordSeq_getX.argtypes = [c_void_p, c_uint, c_void_p]

    lgeos.GEOSCoordSeq_getY.restype = c_int
    lgeos.GEOSCoordSeq_getY.argtypes = [c_void_p, c_uint, c_void_p]

    lgeos.GEOSCoordSeq_getZ.restype = c_int
    lgeos.GEOSCoordSeq_getZ.argtypes = [c_void_p, c_uint, c_void_p]

    lgeos.GEOSCoordSeq_getSize.restype = c_int
    lgeos.GEOSCoordSeq_getSize.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSCoordSeq_getDimensions.restype = c_int
    lgeos.GEOSCoordSeq_getDimensions.argtypes = [c_void_p, c_void_p]

    '''
    Linear refeferencing
    '''

    if geos_version >= (3, 2, 0):

        lgeos.GEOSProject.restype = c_double
        lgeos.GEOSProject.argtypes = [c_void_p, c_void_p]

        lgeos.GEOSInterpolate.restype = c_void_p
        lgeos.GEOSInterpolate.argtypes = [c_void_p, c_double]

        lgeos.GEOSProjectNormalized.restype = c_double
        lgeos.GEOSProjectNormalized.argtypes = [c_void_p, c_void_p]

        lgeos.GEOSInterpolateNormalized.restype = c_void_p
        lgeos.GEOSInterpolateNormalized.argtypes = [c_void_p, c_double]

    '''
    Buffer related
    '''

    lgeos.GEOSBuffer.restype = c_void_p
    lgeos.GEOSBuffer.argtypes = [c_void_p, c_double, c_int]

    if geos_version >= (3, 2, 0):

        lgeos.GEOSBufferWithStyle.restype = c_void_p
        lgeos.GEOSBufferWithStyle.argtypes = [c_void_p, c_double, c_int, c_int, c_int, c_double]

        lgeos.GEOSSingleSidedBuffer.restype = c_void_p
        lgeos.GEOSSingleSidedBuffer.argtypes = [c_void_p, c_double, c_int, c_int, c_double, c_int]

    '''
    Geometry constructors
    '''

    lgeos.GEOSGeom_createPoint.restype = c_void_p
    lgeos.GEOSGeom_createPoint.argtypes = [c_void_p]

    lgeos.GEOSGeom_createLinearRing.restype = c_void_p
    lgeos.GEOSGeom_createLinearRing.argtypes = [c_void_p]

    lgeos.GEOSGeom_createLineString.restype = c_void_p
    lgeos.GEOSGeom_createLineString.argtypes = [c_void_p]

    lgeos.GEOSGeom_createPolygon.restype = c_void_p
    lgeos.GEOSGeom_createPolygon.argtypes = [c_void_p, c_void_p, c_uint]

    lgeos.GEOSGeom_createCollection.restype = c_void_p
    lgeos.GEOSGeom_createCollection.argtypes = [c_int, c_void_p, c_uint]

    lgeos.GEOSGeom_clone.restype = c_void_p
    lgeos.GEOSGeom_clone.argtypes = [c_void_p]

    '''
    Memory management
    '''

    lgeos.GEOSGeom_destroy.restype = None
    lgeos.GEOSGeom_destroy.argtypes = [c_void_p]

    '''
    Topology operations
    Return NULL on exception
    '''

    lgeos.GEOSEnvelope.restype = c_void_p
    lgeos.GEOSEnvelope.argtypes = [c_void_p]

    lgeos.GEOSIntersection.restype = c_void_p
    lgeos.GEOSIntersection.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSConvexHull.restype = c_void_p
    lgeos.GEOSConvexHull.argtypes = [c_void_p]

    lgeos.GEOSDifference.restype = c_void_p
    lgeos.GEOSDifference.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSSymDifference.restype = c_void_p
    lgeos.GEOSSymDifference.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSBoundary.restype = c_void_p
    lgeos.GEOSBoundary.argtypes = [c_void_p]

    lgeos.GEOSUnion.restype = c_void_p
    lgeos.GEOSUnion.argtypes = [c_void_p, c_void_p]

    if geos_version >= (3, 3, 0):
        lgeos.GEOSUnaryUnion.restype = c_void_p
        lgeos.GEOSUnaryUnion.argtypes = [c_void_p]

    if geos_version >= (3, 1, 0):
        '''deprecated in 3.3.0: use GEOSUnaryUnion instead'''
        lgeos.GEOSUnionCascaded.restype = c_void_p
        lgeos.GEOSUnionCascaded.argtypes = [c_void_p]

    lgeos.GEOSPointOnSurface.restype = c_void_p
    lgeos.GEOSPointOnSurface.argtypes = [c_void_p]

    lgeos.GEOSGetCentroid.restype = c_void_p
    lgeos.GEOSGetCentroid.argtypes = [c_void_p]

    lgeos.GEOSPolygonize.restype = c_void_p
    lgeos.GEOSPolygonize.argtypes = [c_void_p, c_uint]

    if geos_version >= (3, 3, 0):
        lgeos.GEOSPolygonize_full.restype = c_void_p
        lgeos.GEOSPolygonize_full.argtypes = [c_void_p, c_void_p, c_void_p, c_void_p]

    lgeos.GEOSLineMerge.restype = c_void_p
    lgeos.GEOSLineMerge.argtypes = [c_void_p]

    lgeos.GEOSSimplify.restype = c_void_p
    lgeos.GEOSSimplify.argtypes = [c_void_p, c_double]

    lgeos.GEOSTopologyPreserveSimplify.restype = c_void_p
    lgeos.GEOSTopologyPreserveSimplify.argtypes = [c_void_p, c_double]

    '''
    Binary predicates
    Return 2 on exception, 1 on true, 0 on false
    '''

    lgeos.GEOSDisjoint.restype = c_byte
    lgeos.GEOSDisjoint.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSTouches.restype = c_byte
    lgeos.GEOSTouches.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSIntersects.restype = c_byte
    lgeos.GEOSIntersects.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSCrosses.restype = c_byte
    lgeos.GEOSCrosses.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSWithin.restype = c_byte
    lgeos.GEOSWithin.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSContains.restype = c_byte
    lgeos.GEOSContains.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSOverlaps.restype = c_byte
    lgeos.GEOSOverlaps.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSEquals.restype = c_byte
    lgeos.GEOSEquals.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSEqualsExact.restype = c_byte
    lgeos.GEOSEqualsExact.argtypes = [c_void_p, c_void_p, c_double]

    '''
    Unary predicate
    Return 2 on exception, 1 on true, 0 on false
    '''

    lgeos.GEOSisEmpty.restype = c_byte
    lgeos.GEOSisEmpty.argtypes = [c_void_p]

    lgeos.GEOSisValid.restype = c_byte
    lgeos.GEOSisValid.argtypes = [c_void_p]

    if geos_version >= (3, 1, 0):
        lgeos.GEOSisValidReason.restype = allocated_c_char_p
        lgeos.GEOSisValidReason.argtypes = [c_void_p]

    lgeos.GEOSisSimple.restype = c_byte
    lgeos.GEOSisSimple.argtypes = [c_void_p]

    lgeos.GEOSisRing.restype = c_byte
    lgeos.GEOSisRing.argtypes = [c_void_p]

    lgeos.GEOSHasZ.restype = c_byte
    lgeos.GEOSHasZ.argtypes = [c_void_p]

    '''
    Dimensionally Extended 9 Intersection Model related
    '''

    lgeos.GEOSRelatePattern.restype = c_char
    lgeos.GEOSRelatePattern.argtypes = [c_void_p, c_void_p, c_char_p]

    lgeos.GEOSRelate.restype = allocated_c_char_p
    lgeos.GEOSRelate.argtypes = [c_void_p, c_void_p]

    '''
    Prepared Geometry Binary predicates
    Return 2 on exception, 1 on true, 0 on false
    '''

    if geos_version >= (3, 1, 0):

        lgeos.GEOSPrepare.restype = c_void_p
        lgeos.GEOSPrepare.argtypes = [c_void_p]

        lgeos.GEOSPreparedGeom_destroy.restype = None
        lgeos.GEOSPreparedGeom_destroy.argtypes = [c_void_p]

        lgeos.GEOSPreparedContains.restype = c_int
        lgeos.GEOSPreparedContains.argtypes = [c_void_p, c_void_p]

        lgeos.GEOSPreparedContainsProperly.restype = c_int
        lgeos.GEOSPreparedContainsProperly.argtypes = [c_void_p, c_void_p]

        lgeos.GEOSPreparedCovers.restype = c_int
        lgeos.GEOSPreparedCovers.argtypes = [c_void_p, c_void_p]

        lgeos.GEOSPreparedIntersects.restype = c_int
        lgeos.GEOSPreparedIntersects.argtypes = [c_void_p, c_void_p]

    '''
    Geometry info
    '''

    lgeos.GEOSGeomType.restype = c_char_p
    lgeos.GEOSGeomType.argtypes = [c_void_p]

    lgeos.GEOSGeomTypeId.restype = c_int
    lgeos.GEOSGeomTypeId.argtypes = [c_void_p]

    lgeos.GEOSGetSRID.restype = c_int
    lgeos.GEOSGetSRID.argtypes = [c_void_p]

    lgeos.GEOSSetSRID.restype = None
    lgeos.GEOSSetSRID.argtypes = [c_void_p, c_int]

    lgeos.GEOSGetNumGeometries.restype = c_int
    lgeos.GEOSGetNumGeometries.argtypes = [c_void_p]

    lgeos.GEOSGetGeometryN.restype = c_void_p
    lgeos.GEOSGetGeometryN.argtypes = [c_void_p, c_int]

    lgeos.GEOSGetNumInteriorRings.restype = c_int
    lgeos.GEOSGetNumInteriorRings.argtypes = [c_void_p]

    lgeos.GEOSGetInteriorRingN.restype = c_void_p
    lgeos.GEOSGetInteriorRingN.argtypes = [c_void_p, c_int]

    lgeos.GEOSGetExteriorRing.restype = c_void_p
    lgeos.GEOSGetExteriorRing.argtypes = [c_void_p]

    lgeos.GEOSGetNumCoordinates.restype = c_int
    lgeos.GEOSGetNumCoordinates.argtypes = [c_void_p]

    lgeos.GEOSGeom_getCoordSeq.restype = c_void_p
    lgeos.GEOSGeom_getCoordSeq.argtypes = [c_void_p]

    lgeos.GEOSGeom_getDimensions.restype = c_int
    lgeos.GEOSGeom_getDimensions.argtypes = [c_void_p]

    '''
    Misc functions
    '''

    lgeos.GEOSArea.restype = c_double
    lgeos.GEOSArea.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSLength.restype = c_int
    lgeos.GEOSLength.argtypes = [c_void_p, c_void_p]

    lgeos.GEOSDistance.restype = c_int
    lgeos.GEOSDistance.argtypes = [c_void_p, c_void_p, c_void_p]

    '''
    Reader and Writer APIs
    '''

    '''WKT Reader'''
    lgeos.GEOSWKTReader_create.restype = c_void_p
    lgeos.GEOSWKTReader_create.argtypes = []

    lgeos.GEOSWKTReader_destroy.restype = None
    lgeos.GEOSWKTReader_destroy.argtypes = [c_void_p]

    lgeos.GEOSWKTReader_read.restype = c_void_p
    lgeos.GEOSWKTReader_read.argtypes = [c_void_p, c_char_p]

    '''WKT Writer'''
    lgeos.GEOSWKTWriter_create.restype = c_void_p
    lgeos.GEOSWKTWriter_create.argtypes = []

    lgeos.GEOSWKTWriter_destroy.restype = None
    lgeos.GEOSWKTWriter_destroy.argtypes = [c_void_p]

    lgeos.GEOSWKTWriter_write.restype = allocated_c_char_p
    lgeos.GEOSWKTWriter_write.argtypes = [c_void_p, c_void_p]

    if geos_version >= (3, 3, 0):

        lgeos.GEOSWKTWriter_setTrim.restype = None
        lgeos.GEOSWKTWriter_setTrim.argtypes = [c_void_p, c_int]

        lgeos.GEOSWKTWriter_setRoundingPrecision.restype = None
        lgeos.GEOSWKTWriter_setRoundingPrecision.argtypes = [c_void_p, c_int]

        lgeos.GEOSWKTWriter_setOutputDimension.restype = None
        lgeos.GEOSWKTWriter_setOutputDimension.argtypes = [c_void_p, c_int]

        lgeos.GEOSWKTWriter_getOutputDimension.restype = c_int
        lgeos.GEOSWKTWriter_getOutputDimension.argtypes = [c_void_p]

        lgeos.GEOSWKTWriter_setOld3D.restype = None
        lgeos.GEOSWKTWriter_setOld3D.argtypes = [c_void_p, c_int]

    '''WKB Reader'''
    lgeos.GEOSWKBReader_create.restype = c_void_p
    lgeos.GEOSWKBReader_create.argtypes = []

    lgeos.GEOSWKBReader_destroy.restype = None
    lgeos.GEOSWKBReader_destroy.argtypes = [c_void_p]

    lgeos.GEOSWKBReader_read.restype = c_void_p
    lgeos.GEOSWKBReader_read.argtypes = [c_void_p, c_char_p, c_size_t]

    lgeos.GEOSWKBReader_readHEX.restype = c_void_p
    lgeos.GEOSWKBReader_readHEX.argtypes = [c_void_p, c_char_p, c_size_t]

    '''WKB Writer'''
    lgeos.GEOSWKBWriter_create.restype = c_void_p
    lgeos.GEOSWKBWriter_create.argtypes = []

    lgeos.GEOSWKBWriter_destroy.restype = None
    lgeos.GEOSWKBWriter_destroy.argtypes = [c_void_p]

    lgeos.GEOSWKBWriter_write.restype = allocated_c_char_p
    lgeos.GEOSWKBWriter_write.argtypes = [c_void_p, c_void_p, c_size_t_p]

    lgeos.GEOSWKBWriter_writeHEX.restype = allocated_c_char_p
    lgeos.GEOSWKBWriter_writeHEX.argtypes = [c_void_p, c_void_p, c_size_t_p]

    lgeos.GEOSWKBWriter_getOutputDimension.restype = c_int
    lgeos.GEOSWKBWriter_getOutputDimension.argtypes = [c_void_p]

    lgeos.GEOSWKBWriter_setOutputDimension.restype = None
    lgeos.GEOSWKBWriter_setOutputDimension.argtypes = [c_void_p, c_int]

    lgeos.GEOSWKBWriter_getByteOrder.restype = c_int
    lgeos.GEOSWKBWriter_getByteOrder.argtypes = [c_void_p]

    lgeos.GEOSWKBWriter_setByteOrder.restype = None
    lgeos.GEOSWKBWriter_setByteOrder.argtypes = [c_void_p, c_int]

    lgeos.GEOSWKBWriter_getIncludeSRID.restype = c_int
    lgeos.GEOSWKBWriter_getIncludeSRID.argtypes = [c_void_p]

    lgeos.GEOSWKBWriter_setIncludeSRID.restype = None
    lgeos.GEOSWKBWriter_setIncludeSRID.argtypes = [c_void_p, c_int]

    if geos_version >= (3, 1, 1):

        '''
        Free buffers returned by stuff like GEOSWKBWriter_write(),
        GEOSWKBWriter_writeHEX() and GEOSWKTWriter_write()
        '''

        lgeos.GEOSFree.restype = None
        lgeos.GEOSFree.argtypes = [c_void_p]

########NEW FILE########
__FILENAME__ = dissolve
# dissolve.py
#
# Demonstrate how Shapely can be used to build up a collection of patches by 
# dissolving circular regions and how Shapely supports plotting of the results.

from functools import partial
import random

import pylab

from shapely.geometry import Point
from shapely.ops import cascaded_union

# Use a partial function to make 100 points uniformly distributed in a 40x40 
# box centered on 0,0.
r = partial(random.uniform, -20.0, 20.0)
points = [Point(r(), r()) for i in range(100)]

# Buffer the points, producing 100 polygon spots
spots = [p.buffer(2.5) for p in points]

# Perform a cascaded union of the polygon spots, dissolving them into a 
# collection of polygon patches
patches = cascaded_union(spots)

if __name__ == "__main__":
    # Illustrate the results using matplotlib's pylab interface
    pylab.figure(num=None, figsize=(4, 4), dpi=180)
    
    for patch in patches.geoms:
        assert patch.geom_type in ['Polygon']
        assert patch.is_valid
    
        # Fill and outline each patch
        x, y = patch.exterior.xy
        pylab.fill(x, y, color='#cccccc', aa=True) 
        pylab.plot(x, y, color='#666666', aa=True, lw=1.0)
    
        # Do the same for the holes of the patch
        for hole in patch.interiors:
            x, y = hole.xy
            pylab.fill(x, y, color='#ffffff', aa=True) 
            pylab.plot(x, y, color='#999999', aa=True, lw=1.0)
    
    # Plot the original points
    pylab.plot([p.x for p in points], [p.y for p in points], 'b,', alpha=0.75)
    
    # Write the number of patches and the total patch area to the figure
    pylab.text(-25, 25, 
        "Patches: %d, total area: %.2f" % (len(patches.geoms), patches.area))
    
    pylab.savefig('dissolve.png')
    

########NEW FILE########
__FILENAME__ = geoms
from numpy import asarray
import pylab
from shapely.geometry import Point, LineString, Polygon

polygon = Polygon(((-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0), (1.0, -1.0)))

point_r = Point(-1.5, 1.2)
point_g = Point(-1.0, 1.0)
point_b = Point(-0.5, 0.5)

line_r = LineString(((-0.5, 0.5), (0.5, 0.5)))
line_g = LineString(((1.0, -1.0), (1.8, 0.5)))
line_b = LineString(((-1.8, -1.2), (1.8, 0.5)))

def plot_point(g, o, l):
    pylab.plot([g.x], [g.y], o, label=l)

def plot_line(g, o):
    a = asarray(g)
    pylab.plot(a[:,0], a[:,1], o)

def fill_polygon(g, o):
    a = asarray(g.exterior)
    pylab.fill(a[:,0], a[:,1], o, alpha=0.5)

def fill_multipolygon(g, o):
    for g in g.geoms:
        fill_polygon(g, o)

if __name__ == "__main__":
    from numpy import asarray
    import pylab
    
    fig = pylab.figure(1, figsize=(4, 3), dpi=150)
    #pylab.axis([-2.0, 2.0, -1.5, 1.5])
    pylab.axis('tight')

    a = asarray(polygon.exterior)
    pylab.fill(a[:,0], a[:,1], 'c')

    plot_point(point_r, 'ro', 'b')
    plot_point(point_g, 'go', 'c')
    plot_point(point_b, 'bo', 'd')

    plot_line(line_r, 'r')
    plot_line(line_g, 'g')
    plot_line(line_b, 'b')

    pylab.show()



########NEW FILE########
__FILENAME__ = intersect
# intersect.py
#
# Demonstrate how Shapely can be used to analyze and plot the intersection of
# a trajectory and regions in space.

from functools import partial
import random

import pylab

from shapely.geometry import LineString, Point
from shapely.ops import cascaded_union

# Build patches as in dissolved.py
r = partial(random.uniform, -20.0, 20.0)
points = [Point(r(), r()) for i in range(100)]
spots = [p.buffer(2.5) for p in points]
patches = cascaded_union(spots)

# Represent the following geolocation parameters
#
# initial position: -25, -25
# heading: 45.0
# speed: 50*sqrt(2)
#
# as a line
vector = LineString(((-25.0, -25.0), (25.0, 25.0)))

# Find intercepted and missed patches. List the former so we can count them
# later
intercepts = [patch for patch in patches.geoms if vector.intersects(patch)]
misses = (patch for patch in patches.geoms if not vector.intersects(patch))

# Plot the intersection
intersection = vector.intersection(patches)
assert intersection.geom_type in ['MultiLineString']

if __name__ == "__main__":
    # Illustrate the results using matplotlib's pylab interface
    pylab.figure(num=None, figsize=(4, 4), dpi=180)
    
    # Plot the misses
    for spot in misses:
        x, y = spot.exterior.xy
        pylab.fill(x, y, color='#cccccc', aa=True) 
        pylab.plot(x, y, color='#999999', aa=True, lw=1.0)
    
        # Do the same for the holes of the patch
        for hole in spot.interiors:
            x, y = hole.xy
            pylab.fill(x, y, color='#ffffff', aa=True) 
            pylab.plot(x, y, color='#999999', aa=True, lw=1.0)
    
    # Plot the intercepts
    for spot in intercepts:
        x, y = spot.exterior.xy
        pylab.fill(x, y, color='red', alpha=0.25, aa=True) 
        pylab.plot(x, y, color='red', alpha=0.5, aa=True, lw=1.0)
    
        # Do the same for the holes of the patch
        for hole in spot.interiors:
            x, y = hole.xy
            pylab.fill(x, y, color='#ffffff', aa=True) 
            pylab.plot(x, y, color='red', alpha=0.5, aa=True, lw=1.0)
    
    # Draw the projected trajectory
    pylab.arrow(-25, -25, 50, 50, color='#999999', aa=True,
        head_width=1.0, head_length=1.0)
    
    for segment in intersection.geoms:
        x, y = segment.xy
        pylab.plot(x, y, color='red', aa=True, lw=1.5)
    
    # Write the number of patches and the total patch area to the figure
    pylab.text(-28, 25, 
        "Patches: %d/%d (%d), total length: %.1f" \
         % (len(intercepts), len(patches.geoms), 
            len(intersection.geoms), intersection.length))
    
    pylab.savefig('intersect.png')
    

########NEW FILE########
__FILENAME__ = world
import ogr
import pylab
from numpy import asarray

from shapely.wkb import loads

source = ogr.Open("/var/gis/data/world/world_borders.shp")
borders = source.GetLayerByName("world_borders")

fig = pylab.figure(1, figsize=(4,2), dpi=300)

while 1:
    feature = borders.GetNextFeature()
    if not feature:
        break
    
    geom = loads(feature.GetGeometryRef().ExportToWkb())
    a = asarray(geom)
    pylab.plot(a[:,0], a[:,1])

pylab.show()

########NEW FILE########
__FILENAME__ = ftools
# Backport some of functools from Python 2.5 standard library for Shapely 
# on Python 2.4
#
# Python module wrapper for _functools C module
# to allow utilities written in Python to be added
# to the functools module.
# Written by Nick Coghlan <ncoghlan at gmail.com>
# Copyright (C) 2006 Python Software Foundation.
# See C source code for _functools credits/copyright
#
# _functools module written and maintained
# by Hye-Shik Chang <perky@FreeBSD.org>
# with adaptations by Raymond Hettinger <python@rcn.com>
# Copyright (c) 2004, 2005, 2006 Python Software Foundation.
# All rights reserved.

def _partial(func, *args, **keywords):
    def newfunc(*fargs, **fkeywords):
        newkeywords = keywords.copy()
        newkeywords.update(fkeywords)
        return func(
            *(args + fargs), **newkeywords)
    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc

# update_wrapper() and wraps() are tools to help write
# wrapper functions that can handle naive introspection

WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
WRAPPER_UPDATES = ('__dict__',)
def _update_wrapper(wrapper,
                   wrapped,
                   assigned = WRAPPER_ASSIGNMENTS,
                   updated = WRAPPER_UPDATES):
    """Update a wrapper function to look like the wrapped function

       wrapper is the function to be updated
       wrapped is the original function
       assigned is a tuple naming the attributes assigned directly
       from the wrapped function to the wrapper function (defaults to
       functools.WRAPPER_ASSIGNMENTS)
       updated is a tuple naming the attributes of the wrapper that
       are updated with the corresponding attribute from the wrapped
       function (defaults to functools.WRAPPER_UPDATES)
    """
    for attr in assigned:
        setattr(wrapper, attr, getattr(wrapped, attr))
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper

def _wraps(wrapped,
          assigned = WRAPPER_ASSIGNMENTS,
          updated = WRAPPER_UPDATES):
    """Decorator factory to apply update_wrapper() to a wrapper function

       Returns a decorator that invokes update_wrapper() with the decorated
       function as the wrapper argument and the arguments to wraps() as the
       remaining arguments. Default arguments are as for update_wrapper().
       This is a convenience function to simplify applying partial() to
       update_wrapper().
    """
    return _partial(_update_wrapper, wrapped=wrapped,
                   assigned=assigned, updated=updated)

# Use stdlib's functools if available
try:
    from functools import partial, update_wrapper, wraps
    have_functools = 1
except ImportError:
    partial = _partial
    update_wrapper = _update_wrapper
    wraps = _wraps
    have_functools = 0


########NEW FILE########
__FILENAME__ = base
"""Base geometry class and utilities
"""

import sys
from warnings import warn
from binascii import a2b_hex
from ctypes import pointer, c_size_t, c_char_p, c_void_p

from shapely.coords import CoordinateSequence
from shapely.ftools import wraps
from shapely.geos import lgeos, ReadingError
from shapely.geos import WKBWriter, WKTWriter
from shapely.impl import DefaultImplementation, delegated

if sys.version_info[0] < 3:
    range = xrange

GEOMETRY_TYPES = [
    'Point',
    'LineString',
    'LinearRing',
    'Polygon',
    'MultiPoint',
    'MultiLineString',
    'MultiPolygon',
    'GeometryCollection',
]


def dump_coords(geom):
    """Dump coordinates of a geometry in the same order as data packing"""
    if not isinstance(geom, BaseGeometry):
        raise ValueError('Must be instance of a geometry class; found ' +
                         geom.__class__.__name__)
    elif geom.type in ('Point', 'LineString', 'LinearRing'):
        return geom.coords[:]
    elif geom.type == 'Polygon':
        return geom.exterior.coords[:] + [i.coords[:] for i in geom.interiors]
    elif geom.type.startswith('Multi') or geom.type == 'GeometryCollection':
        # Recursive call
        return [dump_coords(part) for part in geom]
    else:
        raise ValueError('Unhandled geometry type: ' + repr(geom.type))


def geometry_type_name(g):
    if g is None:
        raise ValueError("Null geometry has no type")
    return GEOMETRY_TYPES[lgeos.GEOSGeomTypeId(g)]


def geom_factory(g, parent=None):
    # Abstract geometry factory for use with topological methods below
    if not g:
        raise ValueError("No Shapely geometry can be created from null value")
    ob = BaseGeometry()
    geom_type = geometry_type_name(g)
    # TODO: check cost of dynamic import by profiling
    mod = __import__(
        'shapely.geometry',
        globals(),
        locals(),
        [geom_type],
        )
    ob.__class__ = getattr(mod, geom_type)
    ob.__geom__ = g
    ob.__p__ = parent
    if lgeos.methods['has_z'](g):
        ob._ndim = 3
    else:
        ob._ndim = 2
    return ob


def geom_from_wkt(data):
    warn("`geom_from_wkt` is deprecated. Use `geos.wkt_reader.read(data)`.",
         DeprecationWarning)
    if sys.version_info[0] >= 3:
        data = data.encode('ascii')
    geom = lgeos.GEOSGeomFromWKT(c_char_p(data))
    if not geom:
        raise ReadingError(
            "Could not create geometry because of errors while reading input.")
    return geom_factory(geom)


def geom_to_wkt(ob):
    warn("`geom_to_wkt` is deprecated. Use `geos.wkt_writer.write(ob)`.",
         DeprecationWarning)
    if ob is None or ob._geom is None:
        raise ValueError("Null geometry supports no operations")
    return lgeos.GEOSGeomToWKT(ob._geom)


def deserialize_wkb(data):
    geom = lgeos.GEOSGeomFromWKB_buf(c_char_p(data), c_size_t(len(data)))
    if not geom:
        raise ReadingError(
            "Could not create geometry because of errors while reading input.")
    return geom


def geom_from_wkb(data):
    warn("`geom_from_wkb` is deprecated. Use `geos.wkb_reader.read(data)`.",
         DeprecationWarning)
    return geom_factory(deserialize_wkb(data))


def geom_to_wkb(ob):
    warn("`geom_to_wkb` is deprecated. Use `geos.wkb_writer.write(ob)`.",
         DeprecationWarning)
    if ob is None or ob._geom is None:
        raise ValueError("Null geometry supports no operations")
    size = c_size_t()
    return lgeos.GEOSGeomToWKB_buf(c_void_p(ob._geom), pointer(size))


def exceptNull(func):
    """Decorator which helps avoid GEOS operations on null pointers."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not args[0]._geom or args[0].is_empty:
            raise ValueError("Null/empty geometry supports no operations")
        return func(*args, **kwargs)
    return wrapper


class CAP_STYLE(object):
    round = 1
    flat = 2
    square = 3


class JOIN_STYLE(object):
    round = 1
    mitre = 2
    bevel = 3

EMPTY = deserialize_wkb(a2b_hex(b'010700000000000000'))


class BaseGeometry(object):
    """
    Provides GEOS spatial predicates and topological operations.

    """

    # Attributes
    # ----------
    # __geom__ : c_void_p
    #     Cached ctypes pointer to GEOS geometry. Not to be accessed.
    # _geom : c_void_p
    #     Property by which the GEOS geometry is accessed.
    # __p__ : object
    #     Parent (Shapely) geometry
    # _ctypes_data : object
    #     Cached ctypes data buffer
    # _ndim : int
    #     Number of dimensions (2 or 3, generally)
    # _crs : object
    #     Coordinate reference system. Available for Shapely extensions, but
    #     not implemented here.
    # _other_owned : bool
    #     True if this object's GEOS geometry is owned by another as in the
    #     case of a multipart geometry member.
    __geom__ = EMPTY
    __p__ = None
    _ctypes_data = None
    _ndim = None
    _crs = None
    _other_owned = False

    # Backend config
    impl = DefaultImplementation

    @property
    def _is_empty(self):
        return self.__geom__ in [EMPTY, None]

    # a reference to the so/dll proxy to preserve access during clean up
    _lgeos = lgeos

    def empty(self, val=EMPTY):
        # TODO: defer cleanup to the implementation. We shouldn't be
        # explicitly calling a lgeos method here.
        if not self._is_empty and not self._other_owned and self.__geom__:
            try:
                self._lgeos.GEOSGeom_destroy(self.__geom__)
            except AttributeError:
                pass  # _lgeos might be empty on shutdown
        self.__geom__ = val

    def __del__(self):
        self.empty(val=None)
        self.__p__ = None

    def __str__(self):
        return self.wkt

    # To support pickling
    def __reduce__(self):
        return (self.__class__, (), self.wkb)

    def __setstate__(self, state):
        self.empty()
        self.__geom__ = deserialize_wkb(state)
        if lgeos.methods['has_z'](self.__geom__):
            self._ndim = 3
        else:
            self._ndim = 2

    @property
    def _geom(self):
        return self.__geom__

    @_geom.setter
    def _geom(self, val):
        self.empty()
        self.__geom__ = val

    # Operators
    # ---------

    def __and__(self, other):
        return self.intersection(other)

    def __or__(self, other):
        return self.union(other)

    def __sub__(self, other):
        return self.difference(other)

    def __xor__(self, other):
        return self.symmetric_difference(other)

    # Array and ctypes interfaces
    # ---------------------------

    @property
    def ctypes(self):
        """Return ctypes buffer"""
        raise NotImplementedError

    @property
    def array_interface_base(self):
        if sys.byteorder == 'little':
            typestr = '<f8'
        elif sys.byteorder == 'big':
            typestr = '>f8'
        else:
            raise ValueError(
                "Unsupported byteorder: neither little nor big-endian")
        return {
            'version': 3,
            'typestr': typestr,
            'data': self.ctypes,
            }

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        raise NotImplementedError

    # Coordinate access
    # -----------------

    def _get_coords(self):
        """Access to geometry's coordinates (CoordinateSequence)"""
        if self.is_empty:
            return []
        return CoordinateSequence(self)

    def _set_coords(self, ob):
        raise NotImplementedError(
            "set_coords must be provided by derived classes")

    coords = property(_get_coords, _set_coords)

    @property
    def xy(self):
        """Separate arrays of X and Y coordinate values"""
        raise NotImplementedError

    # Python feature protocol

    @property
    def __geo_interface__(self):
        """Dictionary representation of the geometry"""
        raise NotImplementedError

    # Type of geometry and its representations
    # ----------------------------------------

    def geometryType(self):
        return geometry_type_name(self._geom)

    @property
    def type(self):
        return self.geometryType()

    def to_wkb(self):
        warn("`to_wkb` is deprecated. Use the `wkb` property.",
             DeprecationWarning)
        return geom_to_wkb(self)

    def to_wkt(self):
        warn("`to_wkt` is deprecated. Use the `wkt` property.",
             DeprecationWarning)
        return geom_to_wkt(self)

    @property
    def wkt(self, **kw):
        """WKT representation of the geometry"""
        return WKTWriter(lgeos, **kw).write(self)

    @property
    def wkb(self):
        """WKB representation of the geometry"""
        return WKBWriter(lgeos).write(self)

    @property
    def wkb_hex(self):
        """WKB hex representation of the geometry"""
        return WKBWriter(lgeos).write_hex(self)

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        raise NotImplementedError

    def _repr_svg_(self):
        """SVG representation for iPython notebook"""
        #Pick an arbitrary size for the SVG canvas


        xmin, ymin, xmax, ymax = self.buffer(1).bounds
        x_size = min([max([100., xmax - xmin]), 300])
        y_size = min([max([100., ymax - ymin]), 300])
        try:
            scale_factor = max([xmax - xmin, ymax - ymin]) / max([x_size, y_size])
        except ZeroDivisionError:
            scale_factor = 1
        buffered_box = "{0} {1} {2} {3}".format(xmin, ymin, xmax - xmin, ymax - ymin)
        return """<svg
            preserveAspectRatio="xMinYMin meet"
            viewBox="{0}"
            width="{1}"
            height="{2}"
            transform="translate(0, {1}),scale(1, -1)">
            {3}
            </svg>""".format(buffered_box, x_size, y_size, self.svg(scale_factor))

    @property
    def geom_type(self):
        """Name of the geometry's type, such as 'Point'"""
        return self.geometryType()

    # Real-valued properties and methods
    # ----------------------------------

    @property
    def area(self):
        """Unitless area of the geometry (float)"""
        return self.impl['area'](self)

    def distance(self, other):
        """Unitless distance to other geometry (float)"""
        return self.impl['distance'](self, other)

    @property
    def length(self):
        """Unitless length of the geometry (float)"""
        return self.impl['length'](self)

    # Topological properties
    # ----------------------

    @property
    def boundary(self):
        """Returns a lower dimension geometry that bounds the object

        The boundary of a polygon is a line, the boundary of a line is a
        collection of points. The boundary of a point is an empty (null)
        collection.
        """
        return geom_factory(self.impl['boundary'](self))

    @property
    def bounds(self):
        """Returns minimum bounding region (minx, miny, maxx, maxy)"""
        if self.is_empty:
            return ()
        else:
            return self.impl['bounds'](self)

    @property
    def centroid(self):
        """Returns the geometric center of the object"""
        return geom_factory(self.impl['centroid'](self))

    @delegated
    def representative_point(self):
        """Returns a point guaranteed to be within the object, cheaply."""
        return geom_factory(self.impl['representative_point'](self))

    @property
    def convex_hull(self):
        """Imagine an elastic band stretched around the geometry: that's a
        convex hull, more or less

        The convex hull of a three member multipoint, for example, is a
        triangular polygon.
        """
        return geom_factory(self.impl['convex_hull'](self))

    @property
    def envelope(self):
        """A figure that envelopes the geometry"""
        return geom_factory(self.impl['envelope'](self))

    def buffer(self, distance, resolution=16, quadsegs=None,
               cap_style=CAP_STYLE.round, join_style=JOIN_STYLE.round,
               mitre_limit=0):
        """Returns a geometry with an envelope at a distance from the object's
        envelope

        A negative distance has a "shrink" effect. A zero distance may be used
        to "tidy" a polygon. The resolution of the buffer around each vertex of
        the object increases by increasing the resolution keyword parameter
        or second positional parameter. Note: the use of a `quadsegs` parameter
        is deprecated and will be gone from the next major release.

        The styles of caps are: CAP_STYLE.round (1), CAP_STYLE.flat (2), and
        CAP_STYLE.square (3).

        The styles of joins between offset segments are: JOIN_STYLE.round (1),
        JOIN_STYLE.mitre (2), and JOIN_STYLE.bevel (3).

        The mitre limit ratio is used for very sharp corners. The mitre ratio
        is the ratio of the distance from the corner to the end of the mitred
        offset corner. When two line segments meet at a sharp angle, a miter
        join will extend the original geometry. To prevent unreasonable
        geometry, the mitre limit allows controlling the maximum length of the
        join corner. Corners with a ratio which exceed the limit will be
        beveled.

        Example:

          >>> from shapely.wkt import loads
          >>> g = loads('POINT (0.0 0.0)')
          >>> g.buffer(1.0).area        # 16-gon approx of a unit radius circle
          3.1365484905459389
          >>> g.buffer(1.0, 128).area   # 128-gon approximation
          3.1415138011443009
          >>> g.buffer(1.0, 3).area     # triangle approximation
          3.0
          >>> list(g.buffer(1.0, cap_style='square').exterior.coords)
          [(1.0, 1.0), (1.0, -1.0), (-1.0, -1.0), (-1.0, 1.0), (1.0, 1.0)]
          >>> g.buffer(1.0, cap_style='square').area
          4.0
        """

        if quadsegs is not None:
            warn(
                "The `quadsegs` argument is deprecated. Use `resolution`.",
                DeprecationWarning)
            res = quadsegs
        else:
            res = resolution

        if cap_style == CAP_STYLE.round and join_style == JOIN_STYLE.round:
            return geom_factory(self.impl['buffer'](self, distance, res))

        if 'buffer_with_style' not in self.impl:
            raise NotImplementedError("Styled buffering not available for "
                                      "GEOS versions < 3.2.")

        return geom_factory(self.impl['buffer_with_style'](self, distance, res,
                                                           cap_style,
                                                           join_style,
                                                           mitre_limit))

    @delegated
    def simplify(self, tolerance, preserve_topology=True):
        """Returns a simplified geometry produced by the Douglas-Puecker
        algorithm

        Coordinates of the simplified geometry will be no more than the
        tolerance distance from the original. Unless the topology preserving
        option is used, the algorithm may produce self-intersecting or
        otherwise invalid geometries.
        """
        if preserve_topology:
            op = self.impl['topology_preserve_simplify']
        else:
            op = self.impl['simplify']
        return geom_factory(op(self, tolerance))

    # Binary operations
    # -----------------

    def difference(self, other):
        """Returns the difference of the geometries"""
        return geom_factory(self.impl['difference'](self, other))

    def intersection(self, other):
        """Returns the intersection of the geometries"""
        return geom_factory(self.impl['intersection'](self, other))

    def symmetric_difference(self, other):
        """Returns the symmetric difference of the geometries
        (Shapely geometry)"""
        return geom_factory(self.impl['symmetric_difference'](self, other))

    def union(self, other):
        """Returns the union of the geometries (Shapely geometry)"""
        return geom_factory(self.impl['union'](self, other))

    # Unary predicates
    # ----------------

    @property
    def has_z(self):
        """True if the geometry's coordinate sequence(s) have z values (are
        3-dimensional)"""
        return bool(self.impl['has_z'](self))

    @property
    def is_empty(self):
        """True if the set of points in this geometry is empty, else False"""
        return (self._geom is None) or bool(self.impl['is_empty'](self))

    @property
    def is_ring(self):
        """True if the geometry is a closed ring, else False"""
        return bool(self.impl['is_ring'](self))

    @property
    def is_simple(self):
        """True if the geometry is simple, meaning that any self-intersections
        are only at boundary points, else False"""
        return bool(self.impl['is_simple'](self))

    @property
    def is_valid(self):
        """True if the geometry is valid (definition depends on sub-class),
        else False"""
        return bool(self.impl['is_valid'](self))

    # Binary predicates
    # -----------------

    def relate(self, other):
        """Returns the DE-9IM intersection matrix for the two geometries
        (string)"""
        return self.impl['relate'](self, other)

    def contains(self, other):
        """Returns True if the geometry contains the other, else False"""
        return bool(self.impl['contains'](self, other))

    def crosses(self, other):
        """Returns True if the geometries cross, else False"""
        return bool(self.impl['crosses'](self, other))

    def disjoint(self, other):
        """Returns True if geometries are disjoint, else False"""
        return bool(self.impl['disjoint'](self, other))

    def equals(self, other):
        """Returns True if geometries are equal, else False"""
        return bool(self.impl['equals'](self, other))

    def intersects(self, other):
        """Returns True if geometries intersect, else False"""
        return bool(self.impl['intersects'](self, other))

    def overlaps(self, other):
        """Returns True if geometries overlap, else False"""
        return bool(self.impl['overlaps'](self, other))

    def touches(self, other):
        """Returns True if geometries touch, else False"""
        return bool(self.impl['touches'](self, other))

    def within(self, other):
        """Returns True if geometry is within the other, else False"""
        return bool(self.impl['within'](self, other))

    def equals_exact(self, other, tolerance):
        """Returns True if geometries are equal to within a specified
        tolerance"""
        # return BinaryPredicateOp('equals_exact', self)(other, tolerance)
        return bool(self.impl['equals_exact'](self, other, tolerance))

    def almost_equals(self, other, decimal=6):
        """Returns True if geometries are equal at all coordinates to a
        specified decimal place"""
        return self.equals_exact(other, 0.5 * 10**(-decimal))

    # Linear referencing
    # ------------------

    @delegated
    def project(self, other, normalized=False):
        """Returns the distance along this geometry to a point nearest the
        specified point

        If the normalized arg is True, return the distance normalized to the
        length of the linear geometry.
        """
        if normalized:
            op = self.impl['project_normalized']
        else:
            op = self.impl['project']
        return op(self, other)

    @delegated
    def interpolate(self, distance, normalized=False):
        """Return a point at the specified distance along a linear geometry

        If the normalized arg is True, the distance will be interpreted as a
        fraction of the geometry's length.
        """
        if normalized:
            op = self.impl['interpolate_normalized']
        else:
            op = self.impl['interpolate']
        return geom_factory(op(self, distance))


class BaseMultipartGeometry(BaseGeometry):

    def shape_factory(self, *args):
        # Factory for part instances, usually a geometry class
        raise NotImplementedError("To be implemented by derived classes")

    @property
    def ctypes(self):
        raise NotImplementedError(
            "Multi-part geometries have no ctypes representations")

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        raise NotImplementedError("Multi-part geometries do not themselves "
                                  "provide the array interface")

    def _get_coords(self):
        raise NotImplementedError("Sub-geometries may have coordinate "
                                  "sequences, but collections do not")

    def _set_coords(self, ob):
        raise NotImplementedError("Sub-geometries may have coordinate "
                                  "sequences, but collections do not")

    @property
    def coords(self):
        raise NotImplementedError(
            "Multi-part geometries do not provide a coordinate sequence")

    @property
    def geoms(self):
        if self.is_empty:
            return []
        return GeometrySequence(self, self.shape_factory)

    def __iter__(self):
        if not self.is_empty:
            return iter(self.geoms)
        else:
            return iter([])

    def __len__(self):
        if not self.is_empty:
            return len(self.geoms)
        else:
            return 0

    def __getitem__(self, index):
        if not self.is_empty:
            return self.geoms[index]
        else:
            return ()[index]

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        return "\n".join([g.svg(scale_factor) for g in self])


class GeometrySequence(object):
    """
    Iterative access to members of a homogeneous multipart geometry.
    """

    # Attributes
    # ----------
    # _factory : callable
    #     Returns instances of Shapely geometries
    # _geom : c_void_p
    #     Ctypes pointer to the parent's GEOS geometry
    # _ndim : int
    #     Number of dimensions (2 or 3, generally)
    # __p__ : object
    #     Parent (Shapely) geometry
    shape_factory = None
    _geom = None
    __p__ = None
    _ndim = None

    def __init__(self, parent, type):
        self.shape_factory = type
        self.__p__ = parent

    def _update(self):
        self._geom = self.__p__._geom
        self._ndim = self.__p__._ndim

    def _get_geom_item(self, i):
        g = self.shape_factory()
        g._other_owned = True
        g._geom = lgeos.GEOSGetGeometryN(self._geom, i)
        g._ndim = self._ndim
        g.__p__ = self
        return g

    def __iter__(self):
        self._update()
        for i in range(self.__len__()):
            yield self._get_geom_item(i)

    def __len__(self):
        self._update()
        return lgeos.GEOSGetNumGeometries(self._geom)

    def __getitem__(self, key):
        self._update()
        m = self.__len__()
        if isinstance(key, int):
            if key + m < 0 or key >= m:
                raise IndexError("index out of range")
            if key < 0:
                i = m + key
            else:
                i = key
            return self._get_geom_item(i)
        elif isinstance(key, slice):
            if type(self) == HeterogeneousGeometrySequence:
                raise TypeError(
                    "Heterogenous geometry collections are not sliceable")
            res = []
            start, stop, stride = key.indices(m)
            for i in range(start, stop, stride):
                res.append(self._get_geom_item(i))
            return type(self.__p__)(res or None)
        else:
            raise TypeError("key must be an index or slice")

    @property
    def _longest(self):
        max = 0
        for g in iter(self):
            l = len(g.coords)
            if l > max:
                max = l


class HeterogeneousGeometrySequence(GeometrySequence):
    """
    Iterative access to a heterogeneous sequence of geometries.
    """

    def __init__(self, parent):
        super(HeterogeneousGeometrySequence, self).__init__(parent, None)

    def _get_geom_item(self, i):
        sub = lgeos.GEOSGetGeometryN(self._geom, i)
        g = geom_factory(sub, parent=self)
        g._other_owned = True
        return g


def _test():
    """Test runner"""
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = collection
"""Multi-part collections of geometries
"""

from shapely.geometry.base import BaseMultipartGeometry
from shapely.geometry.base import HeterogeneousGeometrySequence


class GeometryCollection(BaseMultipartGeometry):

    """A heterogenous collection of geometries

    Attributes
    ----------
    geoms : sequence
        A sequence of Shapely geometry instances
    """

    def __init__(self):
        BaseMultipartGeometry.__init__(self)

    @property
    def __geo_interface__(self):
        geometries = []
        for geom in self.geoms:
            geometries.append(geom.__geo_interface__)
        return dict(type='GeometryCollection', geometries=geometries)

    @property
    def geoms(self):
        if self.is_empty:
            return []
        return HeterogeneousGeometrySequence(self)


# Test runner
def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()


########NEW FILE########
__FILENAME__ = geo
"""
Geometry factories based on the geo interface
"""

from .point import Point, asPoint
from .linestring import LineString, asLineString
from .polygon import Polygon, asPolygon
from .multipoint import MultiPoint, asMultiPoint
from .multilinestring import MultiLineString, asMultiLineString
from .multipolygon import MultiPolygon, MultiPolygonAdapter


def box(minx, miny, maxx, maxy, ccw=True):
    """Returns a rectangular polygon with configurable normal vector"""
    coords = [(maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny)]
    if not ccw:
        coords = coords[::-1]
    return Polygon(coords)

def shape(context):
    """Returns a new, independent geometry with coordinates *copied* from the
    context.
    """
    if hasattr(context, "__geo_interface__"):
        ob = context.__geo_interface__
    else:
        ob = context
    geom_type = ob.get("type").lower()
    if geom_type == "point":
        return Point(ob["coordinates"])
    elif geom_type == "linestring":
        return LineString(ob["coordinates"])
    elif geom_type == "polygon":
        return Polygon(ob["coordinates"][0], ob["coordinates"][1:])
    elif geom_type == "multipoint":
        return MultiPoint(ob["coordinates"])
    elif geom_type == "multilinestring":
        return MultiLineString(ob["coordinates"])
    elif geom_type == "multipolygon":
        return MultiPolygon(ob["coordinates"], context_type='geojson')
    else:
        raise ValueError("Unknown geometry type: %s" % geom_type)

def asShape(context):
    """Adapts the context to a geometry interface. The coordinates remain
    stored in the context.
    """
    if hasattr(context, "__geo_interface__"):
        ob = context.__geo_interface__
    else:
        ob = context

    try:
        geom_type = ob.get("type").lower()
    except AttributeError:
        raise ValueError("Context does not provide geo interface")

    if geom_type == "point":
        return asPoint(ob["coordinates"])
    elif geom_type == "linestring":
        return asLineString(ob["coordinates"])
    elif geom_type == "polygon":
        return asPolygon(ob["coordinates"][0], ob["coordinates"][1:])
    elif geom_type == "multipoint":
        return asMultiPoint(ob["coordinates"])
    elif geom_type == "multilinestring":
        return asMultiLineString(ob["coordinates"])
    elif geom_type == "multipolygon":
        return MultiPolygonAdapter(ob["coordinates"], context_type='geojson')
    else:
        raise ValueError("Unknown geometry type: %s" % geom_type)

def mapping(ob):
    """Returns a GeoJSON-like mapping"""
    return ob.__geo_interface__

########NEW FILE########
__FILENAME__ = linestring
"""Line strings and related utilities
"""

import sys

if sys.version_info[0] < 3:
    range = xrange

from ctypes import c_double, cast, POINTER

from shapely.coords import required
from shapely.geos import lgeos, TopologicalError
from shapely.geometry.base import BaseGeometry, geom_factory, JOIN_STYLE
from shapely.geometry.proxy import CachingGeometryProxy
from shapely.geometry.point import Point

__all__ = ['LineString', 'asLineString']


class LineString(BaseGeometry):
    """
    A one-dimensional figure comprising one or more line segments

    A LineString has non-zero length and zero area. It may approximate a curve
    and need not be straight. Unlike a LinearRing, a LineString is not closed.
    """

    def __init__(self, coordinates=None):
        """
        Parameters
        ----------
        coordinates : sequence
            A sequence of (x, y [,z]) numeric coordinate pairs or triples or
            an object that provides the numpy array interface, including
            another instance of LineString.

        Example
        -------
        Create a line with two segments

          >>> a = LineString([[0, 0], [1, 0], [1, 1]])
          >>> a.length
          2.0
        """
        BaseGeometry.__init__(self)
        if coordinates is not None:
            self._set_coords(coordinates)

    @property
    def __geo_interface__(self):
        return {
            'type': 'LineString',
            'coordinates': tuple(self.coords)
            }

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        pnt_format = " ".join(["{0},{1}".format(*c) for c in self.coords])
        return """<polyline
            fill="none"
            stroke="{2}"
            stroke-width={1}
            points="{0}"
            opacity=".8"
            />""".format(
                pnt_format,
                2.*scale_factor, 
                "#66cc99" if self.is_valid else "#ff3333")

    @property
    def ctypes(self):
        if not self._ctypes_data:
            self._ctypes_data = self.coords.ctypes
        return self._ctypes_data

    def array_interface(self):
        """Provide the Numpy array protocol."""
        return self.coords.array_interface()

    __array_interface__ = property(array_interface)

    # Coordinate access
    def _set_coords(self, coordinates):
        self.empty()
        self._geom, self._ndim = geos_linestring_from_py(coordinates)

    coords = property(BaseGeometry._get_coords, _set_coords)

    @property
    def xy(self):
        """Separate arrays of X and Y coordinate values

        Example:

          >>> x, y = LineString(((0, 0), (1, 1))).xy
          >>> list(x)
          [0.0, 1.0]
          >>> list(y)
          [0.0, 1.0]
        """
        return self.coords.xy

    def parallel_offset(
            self, distance, side,
            resolution=16, join_style=JOIN_STYLE.round, mitre_limit=1.0):

        """Returns a LineString or MultiLineString geometry at a distance from
        the object on its right or its left side.

        Distance must be a positive float value. The side parameter may be
        'left' or 'right'. The resolution of the buffer around each vertex of
        the object increases by increasing the resolution keyword parameter or
        third positional parameter.

        The join style is for outside corners between line segments. Accepted
        values are JOIN_STYLE.round (1), JOIN_STYLE.mitre (2), and
        JOIN_STYLE.bevel (3).

        The mitre ratio limit is used for very sharp corners. It is the ratio
        of the distance from the corner to the end of the mitred offset corner.
        When two line segments meet at a sharp angle, a miter join will extend
        far beyond the original geometry. To prevent unreasonable geometry, the
        mitre limit allows controlling the maximum length of the join corner.
        Corners with a ratio which exceed the limit will be beveled."""

        try:
            return geom_factory(self.impl['parallel_offset'](
                self, distance, resolution, join_style, mitre_limit,
                bool(side == 'left')))
        except OSError:
            raise TopologicalError()


class LineStringAdapter(CachingGeometryProxy, LineString):

    def __init__(self, context):
        self.context = context
        self.factory = geos_linestring_from_py

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.context.__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.context[0])

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        try:
            return self.context.__array_interface__
        except AttributeError:
            return self.array_interface()

    _get_coords = BaseGeometry._get_coords

    def _set_coords(self, ob):
        raise NotImplementedError(
            "Adapters can not modify their coordinate sources")

    coords = property(_get_coords)


def asLineString(context):
    """Adapt an object the LineString interface"""
    return LineStringAdapter(context)


def geos_linestring_from_py(ob, update_geom=None, update_ndim=0):
    # If numpy is present, we use numpy.require to ensure that we have a
    # C-continguous array that owns its data. View data will be copied.
    ob = required(ob)
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 2
        m = array['shape'][0]
        if m < 2:
            raise ValueError(
                "LineStrings must have at least 2 coordinate tuples")
        try:
            n = array['shape'][1]
        except IndexError:
            raise ValueError(
                "Input %s is the wrong shape for a LineString" % str(ob))
        assert n == 2 or n == 3

        # Make pointer to the coordinate array
        if isinstance(array['data'], tuple):
            # numpy tuple (addr, read-only)
            cp = cast(array['data'][0], POINTER(c_double))
        else:
            cp = array['data']

        # Create a coordinate sequence
        if update_geom is not None:
            cs = lgeos.GEOSGeom_getCoordSeq(update_geom)
            if n != update_ndim:
                raise ValueError(
                    "Wrong coordinate dimensions; this geometry has "
                    "dimensions: %d" % update_ndim)
        else:
            cs = lgeos.GEOSCoordSeq_create(m, n)

        # add to coordinate sequence
        for i in range(m):
            dx = c_double(cp[n*i])
            dy = c_double(cp[n*i+1])
            dz = None
            if n == 3:
                try:
                    dz = c_double(cp[n*i+2])
                except IndexError:
                    raise ValueError("Inconsistent coordinate dimensionality")

            # Because of a bug in the GEOS C API,
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, i, dx)
            lgeos.GEOSCoordSeq_setY(cs, i, dy)
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, i, dz)

    except AttributeError:
        # Fall back on list
        try:
            m = len(ob)
        except TypeError:  # Iterators, e.g. Python 3 zip
            ob = list(ob)
            m = len(ob)

        if m < 2:
            raise ValueError(
                "LineStrings must have at least 2 coordinate tuples")

        def _coords(o):
            if isinstance(o, Point):
                return o.coords[0]
            else:
                return o

        try:
            n = len(_coords(ob[0]))
        except TypeError:
            raise ValueError(
                "Input %s is the wrong shape for a LineString" % str(ob))
        assert n == 2 or n == 3

        # Create a coordinate sequence
        if update_geom is not None:
            cs = lgeos.GEOSGeom_getCoordSeq(update_geom)
            if n != update_ndim:
                raise ValueError(
                    "Wrong coordinate dimensions; this geometry has "
                    "dimensions: %d" % update_ndim)
        else:
            cs = lgeos.GEOSCoordSeq_create(m, n)

        # add to coordinate sequence
        for i in range(m):
            coords = _coords(ob[i])
            # Because of a bug in the GEOS C API,
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, i, coords[0])
            lgeos.GEOSCoordSeq_setY(cs, i, coords[1])
            if n == 3:
                try:
                    lgeos.GEOSCoordSeq_setZ(cs, i, coords[2])
                except IndexError:
                    raise ValueError("Inconsistent coordinate dimensionality")

    if update_geom is not None:
        return None
    else:
        return lgeos.GEOSGeom_createLineString(cs), n


def update_linestring_from_py(geom, ob):
    geos_linestring_from_py(ob, geom._geom, geom._ndim)


# Test runner
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = multilinestring
"""Collections of linestrings and related utilities
"""

import sys

if sys.version_info[0] < 3:
    range = xrange

from ctypes import c_double, c_void_p, cast, POINTER

from shapely.geos import lgeos
from shapely.geometry.base import BaseMultipartGeometry
from shapely.geometry.linestring import LineString, geos_linestring_from_py
from shapely.geometry.proxy import CachingGeometryProxy

__all__ = ['MultiLineString', 'asMultiLineString']


class MultiLineString(BaseMultipartGeometry):
    """
    A collection of one or more line strings
    
    A MultiLineString has non-zero length and zero area.

    Attributes
    ----------
    geoms : sequence
        A sequence of LineStrings
    """

    def __init__(self, lines=None):
        """
        Parameters
        ----------
        lines : sequence
            A sequence of line-like coordinate sequences or objects that
            provide the numpy array interface, including instances of
            LineString.

        Example
        -------
        Construct a collection containing one line string.

          >>> lines = MultiLineString( [[[0.0, 0.0], [1.0, 2.0]]] )
        """
        super(MultiLineString, self).__init__()

        if not lines:
            # allow creation of empty multilinestrings, to support unpickling
            pass
        else:
            self._geom, self._ndim = geos_multilinestring_from_py(lines)

    def shape_factory(self, *args):
        return LineString(*args)

    @property
    def __geo_interface__(self):
        return {
            'type': 'MultiLineString',
            'coordinates': tuple(tuple(c for c in g.coords) for g in self.geoms)
            }

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        parts = []
        for part in self.geoms:
            pnt_format = " ".join(["{0},{1}".format(*c) for c in part.coords])
            parts.append("""<polyline
                fill="none"
                stroke="{2}"
                stroke-width={1}
                points="{0}"
                opacity=".8"
                />""".format(
                    pnt_format,
                    2.*scale_factor,
                    "#66cc99" if self.is_valid else "#ff3333"))
        return "\n".join(parts)


class MultiLineStringAdapter(CachingGeometryProxy, MultiLineString):
    
    context = None
    _other_owned = False

    def __init__(self, context):
        self.context = context
        self.factory = geos_multilinestring_from_py

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.context[0].__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.context[0][0])


def asMultiLineString(context):
    """Adapts a sequence of objects to the MultiLineString interface"""
    return MultiLineStringAdapter(context)


def geos_multilinestring_from_py(ob):
    # ob must be either a sequence or array of sequences or arrays
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 1
        L = array['shape'][0]
        assert L >= 1

        # Array of pointers to sub-geometries
        subs = (c_void_p * L)()

        for l in range(L):
            geom, ndims = geos_linestring_from_py(array['data'][l])
            subs[i] = cast(geom, c_void_p)
        N = lgeos.GEOSGeom_getDimensions(subs[0])
    except (NotImplementedError, AttributeError):
        obs = getattr(ob, 'geoms', ob)
        L = len(obs)
        exemplar = obs[0]
        try:
            N = len(exemplar[0])
        except TypeError:
            N = exemplar._ndim
        assert L >= 1
        assert N == 2 or N == 3

        # Array of pointers to point geometries
        subs = (c_void_p * L)()
        
        # add to coordinate sequence
        for l in range(L):
            geom, ndims = geos_linestring_from_py(obs[l])
            subs[l] = cast(geom, c_void_p)
            
    return (lgeos.GEOSGeom_createCollection(5, subs, L), N)

# Test runner
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = multipoint
"""Collections of points and related utilities
"""

import sys

if sys.version_info[0] < 3:
    range = xrange

from ctypes import byref, c_double, c_void_p, cast, POINTER
from ctypes import ArgumentError

from shapely.coords import required
from shapely.geos import lgeos
from shapely.geometry.base import BaseMultipartGeometry, exceptNull
from shapely.geometry.point import Point, geos_point_from_py
from shapely.geometry.proxy import CachingGeometryProxy

__all__ = ['MultiPoint', 'asMultiPoint']


class MultiPoint(BaseMultipartGeometry):

    """A collection of one or more points

    A MultiPoint has zero area and zero length.

    Attributes
    ----------
    geoms : sequence
        A sequence of Points
    """

    def __init__(self, points=None):
        """
        Parameters
        ----------
        points : sequence
            A sequence of (x, y [,z]) numeric coordinate pairs or triples or a
            sequence of objects that implement the numpy array interface,
            including instaces of Point.

        Example
        -------
        Construct a 2 point collection

          >>> ob = MultiPoint([[0.0, 0.0], [1.0, 2.0]])
          >>> len(ob.geoms)
          2
          >>> type(ob.geoms[0]) == Point
          True
        """
        super(MultiPoint, self).__init__()

        if points is None:
            # allow creation of empty multipoints, to support unpickling
            pass
        else:
            self._geom, self._ndim = geos_multipoint_from_py(points)

    def shape_factory(self, *args):
        return Point(*args)

    @property
    def __geo_interface__(self):
        return {
            'type': 'MultiPoint',
            'coordinates': tuple([g.coords[0] for g in self.geoms])
            }

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        
        parts = []
        for part in self.geoms:
            parts.append("""<circle
            cx="{0.x}"
            cy="{0.y}"
            r="{1}"
            stroke="#555555"
            stroke-width="{2}"
            fill="{3}"
            opacity=".6"
            />""".format(
                part,
                3*scale_factor,
                1*scale_factor, "#66cc99" if self.is_valid else "#ff3333"))
        return "\n".join(parts)

    @property
    @exceptNull
    def ctypes(self):
        if not self._ctypes_data:
            temp = c_double()
            n = self._ndim
            m = len(self.geoms)
            array_type = c_double * (m * n)
            data = array_type()
            for i in range(m):
                g = self.geoms[i]._geom    
                cs = lgeos.GEOSGeom_getCoordSeq(g)
                lgeos.GEOSCoordSeq_getX(cs, 0, byref(temp))
                data[n*i] = temp.value
                lgeos.GEOSCoordSeq_getY(cs, 0, byref(temp))
                data[n*i+1] = temp.value
                if n == 3: # TODO: use hasz
                    lgeos.GEOSCoordSeq_getZ(cs, 0, byref(temp))
                    data[n*i+2] = temp.value
            self._ctypes_data = data
        return self._ctypes_data

    @exceptNull
    def array_interface(self):
        """Provide the Numpy array protocol."""
        ai = self.array_interface_base
        ai.update({'shape': (len(self.geoms), self._ndim)})
        return ai
    __array_interface__ = property(array_interface)


class MultiPointAdapter(CachingGeometryProxy, MultiPoint):

    context = None
    _other_owned = False

    def __init__(self, context):
        self.context = context
        self.factory = geos_multipoint_from_py

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.context.__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.context[0])

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        try:
            return self.context.__array_interface__
        except AttributeError:
            return self.array_interface()


def asMultiPoint(context):
    """Adapt a sequence of objects to the MultiPoint interface"""
    return MultiPointAdapter(context)


def geos_multipoint_from_py(ob):
    # If numpy is present, we use numpy.require to ensure that we have a
    # C-continguous array that owns its data. View data will be copied.
    ob = required(ob)
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 2
        m = array['shape'][0]
        n = array['shape'][1]
        assert m >= 1
        assert n == 2 or n == 3

        # Make pointer to the coordinate array
        if isinstance(array['data'], tuple):
            # numpy tuple (addr, read-only)
            cp = cast(array['data'][0], POINTER(c_double))
        else:
            cp = array['data']

        # Array of pointers to sub-geometries
        subs = (c_void_p * m)()

        for i in range(m):
            geom, ndims = geos_point_from_py(cp[n*i:n*i+2])
            subs[i] = cast(geom, c_void_p)

    except AttributeError:
        # Fall back on list
        m = len(ob)
        try:
            n = len(ob[0])
        except TypeError:
            n = ob[0]._ndim
        assert n == 2 or n == 3

        # Array of pointers to point geometries
        subs = (c_void_p * m)()
        
        # add to coordinate sequence
        for i in range(m):
            coords = ob[i]
            geom, ndims = geos_point_from_py(coords)
            subs[i] = cast(geom, c_void_p)
            
    return lgeos.GEOSGeom_createCollection(4, subs, m), n

# Test runner
def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = multipolygon
"""Collections of polygons and related utilities
"""

import sys

if sys.version_info[0] < 3:
    range = xrange

from ctypes import c_void_p, cast

from shapely.geos import lgeos
from shapely.geometry.base import BaseMultipartGeometry
from shapely.geometry.polygon import Polygon, geos_polygon_from_py
from shapely.geometry.proxy import CachingGeometryProxy

__all__ = ['MultiPolygon', 'asMultiPolygon']


class MultiPolygon(BaseMultipartGeometry):

    """A collection of one or more polygons
    
    If component polygons overlap the collection is `invalid` and some
    operations on it may fail.
    
    Attributes
    ----------
    geoms : sequence
        A sequence of `Polygon` instances
    """

    def __init__(self, polygons=None, context_type='polygons'):
        """
        Parameters
        ----------
        polygons : sequence
            A sequence of (shell, holes) tuples where shell is the sequence
            representation of a linear ring (see linearring.py) and holes is
            a sequence of such linear rings

        Example
        -------
        Construct a collection from a sequence of coordinate tuples

          >>> ob = MultiPolygon( [
          ...     (
          ...     ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)), 
          ...     [((0.1,0.1), (0.1,0.2), (0.2,0.2), (0.2,0.1))]
          ...     )
          ... ] )
          >>> len(ob.geoms)
          1
          >>> type(ob.geoms[0]) == Polygon
          True
        """
        super(MultiPolygon, self).__init__()

        if not polygons:
            # allow creation of empty multipolygons, to support unpickling
            pass
        elif context_type == 'polygons':
            self._geom, self._ndim = geos_multipolygon_from_polygons(polygons)
        elif context_type == 'geojson':
            self._geom, self._ndim = geos_multipolygon_from_py(polygons)

    def shape_factory(self, *args):
        return Polygon(*args)

    @property
    def __geo_interface__(self):
        allcoords = []
        for geom in self.geoms:
            coords = []
            coords.append(tuple(geom.exterior.coords))
            for hole in geom.interiors:
                coords.append(tuple(hole.coords))
            allcoords.append(tuple(coords))
        return {
            'type': 'MultiPolygon',
            'coordinates': allcoords
            }

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        parts = []
        for part in self.geoms:
            exterior_coords = [["{0},{1}".format(*c) for c in part.exterior.coords]]
            interior_coords = [
                ["{0},{1}".format(*c) for c in interior.coords]
                for interior in part.interiors ]
            path = " ".join([
                "M {0} L {1} z".format(coords[0], " L ".join(coords[1:]))
                for coords in exterior_coords + interior_coords ])
            parts.append(
                """<g fill-rule="evenodd" fill="{2}" stroke="#555555"
                stroke-width="{0}" opacity="0.6">
                <path d="{1}" /></g>""".format(
                    2. * scale_factor,
                    path,
                    "#66cc99" if self.is_valid else "#ff3333"))
        return "\n".join(parts)


class MultiPolygonAdapter(CachingGeometryProxy, MultiPolygon):
    
    context = None
    _other_owned = False

    def __init__(self, context, context_type='polygons'):
        self.context = context
        if context_type == 'geojson':
            self.factory = geos_multipolygon_from_py
        elif context_type == 'polygons':
            self.factory = geos_multipolygon_from_polygons

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.context[0][0].__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.context[0][0][0])


def asMultiPolygon(context):
    """Adapts a sequence of objects to the MultiPolygon interface"""
    return MultiPolygonAdapter(context)


def geos_multipolygon_from_py(ob):
    """ob must provide Python geo interface coordinates."""
    L = len(ob)
    assert L >= 1
    
    N = len(ob[0][0][0])
    assert N == 2 or N == 3

    subs = (c_void_p * L)()
    for l in range(L):
        geom, ndims = geos_polygon_from_py(ob[l][0], ob[l][1:])
        subs[l] = cast(geom, c_void_p)
            
    return (lgeos.GEOSGeom_createCollection(6, subs, L), N)

def geos_multipolygon_from_polygons(ob):
    """ob must be either a sequence or array of sequences or arrays."""
    obs = getattr(ob, 'geoms', None) or ob
    L = len(obs)
    assert L >= 1
    
    exemplar = obs[0]
    try:
        N = len(exemplar[0][0])
    except TypeError:
        N = exemplar._ndim
    
    assert N == 2 or N == 3

    subs = (c_void_p * L)()
    for l in range(L):
        shell = getattr(obs[l], 'exterior', None)
        if shell is None:
            shell = obs[l][0]
        holes = getattr(obs[l], 'interiors', None)
        if holes is None:
            holes =  obs[l][1]
        geom, ndims = geos_polygon_from_py(shell, holes)
        subs[l] = cast(geom, c_void_p)
            
    return (lgeos.GEOSGeom_createCollection(6, subs, L), N)

# Test runner
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = point
"""Points and related utilities
"""

from ctypes import c_double
from ctypes import cast, POINTER

from shapely.coords import required
from shapely.geos import lgeos, DimensionError
from shapely.geometry.base import BaseGeometry
from shapely.geometry.proxy import CachingGeometryProxy

__all__ = ['Point', 'asPoint']


class Point(BaseGeometry):
    """
    A zero dimensional feature

    A point has zero length and zero area.

    Attributes
    ----------
    x, y, z : float
        Coordinate values

    Example
    -------
      >>> p = Point(1.0, -1.0)
      >>> print(p)
      POINT (1.0000000000000000 -1.0000000000000000)
      >>> p.y
      -1.0
      >>> p.x
      1.0
    """

    def __init__(self, *args):
        """
        Parameters
        ----------
        There are 2 cases:

        1) 1 parameter: this must satisfy the numpy array protocol.
        2) 2 or more parameters: x, y, z : float
            Easting, northing, and elevation.
        """
        BaseGeometry.__init__(self)
        if len(args) > 0:
            self._set_coords(*args)

    # Coordinate getters and setters

    @property
    def x(self):
        """Return x coordinate."""
        return self.coords[0][0]

    @property
    def y(self):
        """Return y coordinate."""
        return self.coords[0][1]

    @property
    def z(self):
        """Return z coordinate."""
        if self._ndim != 3:
            raise DimensionError("This point has no z coordinate.")
        return self.coords[0][2]

    @property
    def __geo_interface__(self):
        return {
            'type': 'Point',
            'coordinates': self.coords[0]
            }

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        return """<circle
            cx="{0.x}"
            cy="{0.y}"
            r="{1}"
            stroke="#555555"
            stroke-width="{2}"
            fill="{3}"
            opacity=".6"
            />""".format(
                self,
                3 * scale_factor,
                1 * scale_factor,
                "#66cc99" if self.is_valid else "#ff3333")

    @property
    def ctypes(self):
        if not self._ctypes_data:
            array_type = c_double * self._ndim
            array = array_type()
            xy = self.coords[0]
            array[0] = xy[0]
            array[1] = xy[1]
            if self._ndim == 3:
                array[2] = xy[2]
            self._ctypes_data = array
        return self._ctypes_data

    def array_interface(self):
        """Provide the Numpy array protocol."""
        ai = self.array_interface_base
        ai.update({'shape': (self._ndim,)})
        return ai
    __array_interface__ = property(array_interface)

    @property
    def bounds(self):
        xy = self.coords[0]
        return (xy[0], xy[1], xy[0], xy[1])

    # Coordinate access

    def _set_coords(self, *args):
        self.empty()
        if len(args) == 1:
            self._geom, self._ndim = geos_point_from_py(args[0])
        else:
            self._geom, self._ndim = geos_point_from_py(tuple(args))

    coords = property(BaseGeometry._get_coords, _set_coords)

    @property
    def xy(self):
        """Separate arrays of X and Y coordinate values

        Example:
          >>> x, y = Point(0, 0).xy
          >>> list(x)
          [0.0]
          >>> list(y)
          [0.0]
        """
        return self.coords.xy


class PointAdapter(CachingGeometryProxy, Point):

    _other_owned = False

    def __init__(self, context):
        self.context = context
        self.factory = geos_point_from_py

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.context.__array_interface__
            n = array['shape'][0]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.context)

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        try:
            return self.context.__array_interface__
        except AttributeError:
            return self.array_interface()

    _get_coords = BaseGeometry._get_coords

    def _set_coords(self, ob):
        raise NotImplementedError("Adapters can not modify their sources")

    coords = property(_get_coords)


def asPoint(context):
    """Adapt an object to the Point interface"""
    return PointAdapter(context)


def geos_point_from_py(ob, update_geom=None, update_ndim=0):
    """Create a GEOS geom from an object that is a coordinate sequence
    or that provides the array interface.

    Returns the GEOS geometry and the number of its dimensions.
    """
    # If numpy is present, we use numpy.require to ensure that we have a
    # C-continguous array that owns its data. View data will be copied.
    ob = required(ob)
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 1
        n = array['shape'][0]
        assert n == 2 or n == 3

        dz = None
        da = array['data']
        if isinstance(da, tuple):
            cdata = da[0]
            # If we had numpy, we would do
            # from numpy.ctypeslib import as_ctypes
            # cp = as_ctypes(ob) - check that code?
            cp = cast(cdata, POINTER(c_double))
            dx = c_double(cp[0])
            dy = c_double(cp[1])
            if n == 3:
                dz = c_double(cp[2])
        else:
            dx, dy = da[0:2]
            if n == 3:
                dz = da[2]

    except AttributeError:
        # Fall back on the case of Python sequence data
        # Accept either (x, y) or [(x, y)]
        if not hasattr(ob, '__getitem__'):  # Iterators, e.g. Python 3 zip
            ob = list(ob)

        if isinstance(ob[0], tuple):
            coords = ob[0]
        else:
            coords = ob
        n = len(coords)
        dx = c_double(coords[0])
        dy = c_double(coords[1])
        dz = None
        if n == 3:
            dz = c_double(coords[2])

    if update_geom:
        cs = lgeos.GEOSGeom_getCoordSeq(update_geom)
        if n != update_ndim:
            raise ValueError(
                "Wrong coordinate dimensions; this geometry has dimensions: "
                "%d" % update_ndim)
    else:
        cs = lgeos.GEOSCoordSeq_create(1, n)

    # Because of a bug in the GEOS C API, always set X before Y
    lgeos.GEOSCoordSeq_setX(cs, 0, dx)
    lgeos.GEOSCoordSeq_setY(cs, 0, dy)
    if n == 3:
        lgeos.GEOSCoordSeq_setZ(cs, 0, dz)

    if update_geom:
        return None
    else:
        return lgeos.GEOSGeom_createPoint(cs), n


def update_point_from_py(geom, ob):
    geos_point_from_py(ob, geom._geom, geom._ndim)


# Test runner
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = polygon
"""Polygons and their linear ring components
"""

import sys

if sys.version_info[0] < 3:
    range = xrange

from ctypes import c_double, c_void_p, cast, POINTER
from ctypes import ArgumentError
import weakref

from shapely.algorithms.cga import signed_area
from shapely.coords import required
from shapely.geos import lgeos
from shapely.geometry.base import BaseGeometry
from shapely.geometry.linestring import LineString, LineStringAdapter
from shapely.geometry.proxy import PolygonProxy

__all__ = ['Polygon', 'asPolygon', 'LinearRing', 'asLinearRing']


class LinearRing(LineString):
    """
    A closed one-dimensional feature comprising one or more line segments

    A LinearRing that crosses itself or touches itself at a single point is
    invalid and operations on it may fail.
    """
    
    def __init__(self, coordinates=None):
        """
        Parameters
        ----------
        coordinates : sequence
            A sequence of (x, y [,z]) numeric coordinate pairs or triples

        Rings are implicitly closed. There is no need to specific a final
        coordinate pair identical to the first.

        Example
        -------
        Construct a square ring.

          >>> ring = LinearRing( ((0, 0), (0, 1), (1 ,1 ), (1 , 0)) )
          >>> ring.is_closed
          True
          >>> ring.length
          4.0
        """
        BaseGeometry.__init__(self)
        if coordinates is not None:
            self._set_coords(coordinates)

    @property
    def __geo_interface__(self):
        return {
            'type': 'LinearRing',
            'coordinates': tuple(self.coords)
            }

    # Coordinate access

    _get_coords = BaseGeometry._get_coords

    def _set_coords(self, coordinates):
        self.empty()
        self._geom, self._ndim = geos_linearring_from_py(coordinates)

    coords = property(_get_coords, _set_coords)

    @property
    def is_ccw(self):
        """True is the ring is oriented counter clock-wise"""
        return bool(self.impl['is_ccw'](self))

    @property
    def is_simple(self):
        """True if the geometry is simple, meaning that any self-intersections
        are only at boundary points, else False"""
        return LineString(self).is_simple


class LinearRingAdapter(LineStringAdapter):

    __p__ = None

    def __init__(self, context):
        self.context = context
        self.factory = geos_linearring_from_py

    @property
    def __geo_interface__(self):
        return {
            'type': 'LinearRing',
            'coordinates': tuple(self.coords)
            }

    coords = property(BaseGeometry._get_coords)


def asLinearRing(context):
    """Adapt an object to the LinearRing interface"""
    return LinearRingAdapter(context)


class InteriorRingSequence(object):

    _factory = None
    _geom = None
    __p__ = None
    _ndim = None
    _index = 0
    _length = 0
    __rings__ = None
    _gtag = None

    def __init__(self, parent):
        self.__p__ = parent
        self._geom = parent._geom
        self._ndim = parent._ndim

    def __iter__(self):
        self._index = 0
        self._length = self.__len__()
        return self

    def __next__(self):
        if self._index < self._length:
            ring = self._get_ring(self._index)
            self._index += 1
            return ring
        else:
            raise StopIteration 

    if sys.version_info[0] < 3:
        next = __next__

    def __len__(self):
        return lgeos.GEOSGetNumInteriorRings(self._geom)

    def __getitem__(self, key):
        m = self.__len__()
        if isinstance(key, int):
            if key + m < 0 or key >= m:
                raise IndexError("index out of range")
            if key < 0:
                i = m + key
            else:
                i = key
            return self._get_ring(i)
        elif isinstance(key, slice):
            res = []
            start, stop, stride = key.indices(m)
            for i in range(start, stop, stride):
                res.append(self._get_ring(i))
            return res
        else:
            raise TypeError("key must be an index or slice")

    @property
    def _longest(self):
        max = 0
        for g in iter(self):
            l = len(g.coords)
            if l > max:
                max = l

    def gtag(self):
        return hash(repr(self.__p__))

    def _get_ring(self, i):
        gtag = self.gtag()
        if gtag != self._gtag:
            self.__rings__ = {}
        if i not in self.__rings__:
            g = lgeos.GEOSGetInteriorRingN(self._geom, i)
            ring = LinearRing()
            ring.__geom__ = g
            ring.__p__ = self
            ring._other_owned = True
            ring._ndim = self._ndim
            self.__rings__[i] = weakref.ref(ring)
        return self.__rings__[i]()
        

class Polygon(BaseGeometry):
    """
    A two-dimensional figure bounded by a linear ring

    A polygon has a non-zero area. It may have one or more negative-space
    "holes" which are also bounded by linear rings. If any rings cross each
    other, the feature is invalid and operations on it may fail.

    Attributes
    ----------
    exterior : LinearRing
        The ring which bounds the positive space of the polygon.
    interiors : sequence
        A sequence of rings which bound all existing holes.
    """

    _exterior = None
    _interiors = []
    _ndim = 2

    def __init__(self, shell=None, holes=None):
        """
        Parameters
        ----------
        shell : sequence
            A sequence of (x, y [,z]) numeric coordinate pairs or triples
        holes : sequence
            A sequence of objects which satisfy the same requirements as the
            shell parameters above

        Example
        -------
        Create a square polygon with no holes

          >>> coords = ((0., 0.), (0., 1.), (1., 1.), (1., 0.), (0., 0.))
          >>> polygon = Polygon(coords)
          >>> polygon.area
          1.0
        """
        BaseGeometry.__init__(self)

        if shell is not None:
            self._geom, self._ndim = geos_polygon_from_py(shell, holes)

    @property
    def exterior(self):
        if self.is_empty:
            return None
        elif self._exterior is None or self._exterior() is None:
            g = lgeos.GEOSGetExteriorRing(self._geom)
            ring = LinearRing()
            ring.__geom__ = g
            ring.__p__ = self
            ring._other_owned = True
            ring._ndim = self._ndim
            self._exterior = weakref.ref(ring)
        return self._exterior()

    @property
    def interiors(self):
        if self.is_empty:
            return []
        return InteriorRingSequence(self)

    @property
    def ctypes(self):
        if not self._ctypes_data:
            self._ctypes_data = self.exterior.ctypes
        return self._ctypes_data

    @property
    def __array_interface__(self):
        raise NotImplementedError(
        "A polygon does not itself provide the array interface. Its rings do.")

    def _get_coords(self):
        raise NotImplementedError(
        "Component rings have coordinate sequences, but the polygon does not")

    def _set_coords(self, ob):
        raise NotImplementedError(
        "Component rings have coordinate sequences, but the polygon does not")

    @property
    def coords(self):
        raise NotImplementedError(
        "Component rings have coordinate sequences, but the polygon does not")

    @property
    def __geo_interface__(self):
        coords = [tuple(self.exterior.coords)]
        for hole in self.interiors:
            coords.append(tuple(hole.coords))
        return {
            'type': 'Polygon',
            'coordinates': tuple(coords)
            }

    def svg(self, scale_factor=1.):
        """
        SVG representation of the geometry. Scale factor is multiplied by
        the size of the SVG symbol so it can be scaled consistently for a
        consistent appearance based on the canvas size.
        """
        exterior_coords = [["{0},{1}".format(*c) for c in self.exterior.coords]]
        interior_coords = [
            ["{0},{1}".format(*c) for c in interior.coords]
            for interior in self.interiors ]
        path = " ".join([
            "M {0} L {1} z".format(coords[0], " L ".join(coords[1:]))
            for coords in exterior_coords + interior_coords ])
        return """
            <g fill-rule="evenodd" fill="{2}" stroke="#555555" 
            stroke-width="{0}" opacity="0.6">
            <path d="{1}" />
            </g>""".format(
                2.*scale_factor, path, "#66cc99" if self.is_valid else "#ff3333")


class PolygonAdapter(PolygonProxy, Polygon):
    
    def __init__(self, shell, holes=None):
        self.shell = shell
        self.holes = holes
        self.context = (shell, holes)
        self.factory = geos_polygon_from_py

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.shell.__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.shell[0])


def asPolygon(shell, holes=None):
    """Adapt objects to the Polygon interface"""
    return PolygonAdapter(shell, holes)

def orient(polygon, sign=1.0):
    s = float(sign)
    rings = []
    ring = polygon.exterior
    if signed_area(ring)/s >= 0.0:
        rings.append(ring)
    else:
        rings.append(list(ring.coords)[::-1])
    for ring in polygon.interiors:
        if signed_area(ring)/s <= 0.0:
            rings.append(ring)
        else:
            rings.append(list(ring.coords)[::-1])
    return Polygon(rings[0], rings[1:])

def geos_linearring_from_py(ob, update_geom=None, update_ndim=0):
    # If numpy is present, we use numpy.require to ensure that we have a
    # C-continguous array that owns its data. View data will be copied.
    ob = required(ob)
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 2
        m = array['shape'][0]
        n = array['shape'][1]
        if m < 3:
            raise ValueError(
                "A LinearRing must have at least 3 coordinate tuples")
        assert n == 2 or n == 3

        # Make pointer to the coordinate array
        if isinstance(array['data'], tuple):
            # numpy tuple (addr, read-only)
            cp = cast(array['data'][0], POINTER(c_double))
        else:
            cp = array['data']

        # Add closing coordinates to sequence?
        if cp[0] != cp[m*n-n] or cp[1] != cp[m*n-n+1]:
            M = m + 1
        else:
            M = m

        # Create a coordinate sequence
        if update_geom is not None:
            cs = lgeos.GEOSGeom_getCoordSeq(update_geom)
            if n != update_ndim:
                raise ValueError(
                "Wrong coordinate dimensions; this geometry has dimensions: %d" \
                % update_ndim)
        else:
            cs = lgeos.GEOSCoordSeq_create(M, n)

        # add to coordinate sequence
        for i in range(m):
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, i, cp[n*i])
            lgeos.GEOSCoordSeq_setY(cs, i, cp[n*i+1])
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, i, cp[n*i+2])

        # Add closing coordinates to sequence?
        if M > m:        
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, M-1, cp[0])
            lgeos.GEOSCoordSeq_setY(cs, M-1, cp[1])
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, M-1, cp[2])
            
    except AttributeError:
        # Fall back on list
        try:
            m = len(ob)
        except TypeError:  # Iterators, e.g. Python 3 zip
            ob = list(ob)
            m = len(ob)

        n = len(ob[0])
        if m < 3:
            raise ValueError(
                "A LinearRing must have at least 3 coordinate tuples")
        assert (n == 2 or n == 3)

        # Add closing coordinates if not provided
        if m == 3 or ob[0][0] != ob[-1][0] or ob[0][1] != ob[-1][1]:
            M = m + 1
        else:
            M = m

        # Create a coordinate sequence
        if update_geom is not None:
            cs = lgeos.GEOSGeom_getCoordSeq(update_geom)
            if n != update_ndim:
                raise ValueError(
                "Wrong coordinate dimensions; this geometry has dimensions: %d" \
                % update_ndim)
        else:
            cs = lgeos.GEOSCoordSeq_create(M, n)
        
        # add to coordinate sequence
        for i in range(m):
            coords = ob[i]
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, i, coords[0])
            lgeos.GEOSCoordSeq_setY(cs, i, coords[1])
            if n == 3:
                try:
                    lgeos.GEOSCoordSeq_setZ(cs, i, coords[2])
                except IndexError:
                    raise ValueError("Inconsistent coordinate dimensionality")

        # Add closing coordinates to sequence?
        if M > m:
            coords = ob[0]
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, M-1, coords[0])
            lgeos.GEOSCoordSeq_setY(cs, M-1, coords[1])
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, M-1, coords[2])

    if update_geom is not None:
        return None
    else:
        return lgeos.GEOSGeom_createLinearRing(cs), n

def update_linearring_from_py(geom, ob):
    geos_linearring_from_py(ob, geom._geom, geom._ndim)

def geos_polygon_from_py(shell, holes=None):
    if shell is not None:
        geos_shell, ndim = geos_linearring_from_py(shell)
        if holes is not None and len(holes) > 0:
            ob = holes
            L = len(ob)
            exemplar = ob[0]
            try:
                N = len(exemplar[0])
            except TypeError:
                N = exemplar._ndim
            if not L >= 1:
                raise ValueError("number of holes must be non zero")
            if not N in (2, 3):
                raise ValueError("insufficiant coordinate dimension")

            # Array of pointers to ring geometries
            geos_holes = (c_void_p * L)()
    
            # add to coordinate sequence
            for l in range(L):
                geom, ndim = geos_linearring_from_py(ob[l])
                geos_holes[l] = cast(geom, c_void_p)
        else:
            geos_holes = POINTER(c_void_p)()
            L = 0
        return (
            lgeos.GEOSGeom_createPolygon(
                        c_void_p(geos_shell),
                        geos_holes,
                        L
                        ),
            ndim
            )

# Test runner
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = proxy
"""Proxy for coordinates stored outside Shapely geometries
"""

from shapely.geometry.base import deserialize_wkb, EMPTY
from shapely.geos import lgeos


class CachingGeometryProxy(object):

    context = None
    factory = None
    __geom__ = EMPTY
    _gtag = None

    def __init__(self, context):
        self.context = context

    @property
    def _is_empty(self):
        return self.__geom__ in [EMPTY, None]

    def empty(self, val=EMPTY):
        if not self._is_empty and self.__geom__:
            lgeos.GEOSGeom_destroy(self.__geom__)
        self.__geom__ = val

    @property
    def _geom(self):
        """Keeps the GEOS geometry in synch with the context."""
        gtag = self.gtag()
        if gtag != self._gtag or self._is_empty:
            self.empty()
            self.__geom__, n = self.factory(self.context)
        self._gtag = gtag
        return self.__geom__
        
    def gtag(self):
        return hash(repr(self.context))


class PolygonProxy(CachingGeometryProxy):

    @property
    def _geom(self):
        """Keeps the GEOS geometry in synch with the context."""
        gtag = self.gtag()
        if gtag != self._gtag or self._is_empty:
            self.empty()
            self.__geom__, n = self.factory(self.context[0], self.context[1])
        self._gtag = gtag
        return self.__geom__

########NEW FILE########
__FILENAME__ = geos
"""
Proxies for the libgeos_c shared lib, GEOS-specific exceptions, and utilities
"""

import os
import re
import sys
import atexit
import logging
import threading
from ctypes import CDLL, cdll, pointer, c_void_p, c_size_t, c_char_p, string_at
from ctypes.util import find_library

from . import ftools
from .ctypes_declarations import prototype, EXCEPTION_HANDLER_FUNCTYPE


# Add message handler to this module's logger
LOG = logging.getLogger(__name__)

if 'all' in sys.warnoptions:
    # show GEOS messages in console with: python -W all
    logging.basicConfig()
else:
    # no handler messages shown
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

    LOG.addHandler(NullHandler())


# Find and load the GEOS and C libraries
# If this ever gets any longer, we'll break it into separate modules

def load_dll(libname, fallbacks=None):
    lib = find_library(libname)
    if lib is not None:
        try:
            return CDLL(lib)
        except OSError:
            pass
    if fallbacks is not None:
        for name in fallbacks:
            try:
                return CDLL(name)
            except OSError:
                # move on to the next fallback
                pass
    # No shared library was loaded. Raise OSError.
    raise OSError(
        "Could not find library %s or load any of its variants %s" % (
            libname, fallbacks or []))


if sys.platform.startswith('linux'):
    _lgeos = load_dll('geos_c', fallbacks=['libgeos_c.so.1', 'libgeos_c.so'])
    free = load_dll('c').free
    free.argtypes = [c_void_p]
    free.restype = None

elif sys.platform == 'darwin':
    if hasattr(sys, 'frozen'):
        # .app file from py2app
        alt_paths = [os.path.join(os.environ['RESOURCEPATH'],
                     '..', 'Frameworks', 'libgeos_c.dylib')]
    else:
        alt_paths = [
            # The Framework build from Kyng Chaos:
            "/Library/Frameworks/GEOS.framework/Versions/Current/GEOS",
            # macports
            '/opt/local/lib/libgeos_c.dylib',
        ]
    _lgeos = load_dll('geos_c', fallbacks=alt_paths)
    free = load_dll('c').free
    free.argtypes = [c_void_p]
    free.restype = None

elif sys.platform == 'win32':
    try:
        egg_dlls = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   "DLLs"))
        wininst_dlls = os.path.abspath(os.__file__ + "../../../DLLs")
        original_path = os.environ['PATH']
        os.environ['PATH'] = "%s;%s;%s" % \
            (egg_dlls, wininst_dlls, original_path)
        _lgeos = CDLL("geos.dll")
    except (ImportError, WindowsError, OSError):
        raise

    def free(m):
        try:
            cdll.msvcrt.free(m)
        except WindowsError:
            # XXX: See http://trac.gispython.org/projects/PCL/ticket/149
            pass

elif sys.platform == 'sunos5':
    _lgeos = load_dll('geos_c', fallbacks=['libgeos_c.so.1', 'libgeos_c.so'])
    free = CDLL('libc.so.1').free
    free.argtypes = [c_void_p]
    free.restype = None
else:  # other *nix systems
    _lgeos = load_dll('geos_c', fallbacks=['libgeos_c.so.1', 'libgeos_c.so'])
    free = load_dll('c', fallbacks=['libc.so.6']).free
    free.argtypes = [c_void_p]
    free.restype = None


def _geos_version():
    # extern const char GEOS_DLL *GEOSversion();
    GEOSversion = _lgeos.GEOSversion
    GEOSversion.restype = c_char_p
    GEOSversion.argtypes = []
    #define GEOS_CAPI_VERSION "@VERSION@-CAPI-@CAPI_VERSION@"
    geos_version_string = GEOSversion()
    if sys.version_info[0] >= 3:
        geos_version_string = geos_version_string.decode('ascii')
    res = re.findall(r'(\d+)\.(\d+)\.(\d+)', geos_version_string)
    assert len(res) == 2, res
    geos_version = tuple(int(x) for x in res[0])
    capi_version = tuple(int(x) for x in res[1])
    return geos_version_string, geos_version, capi_version

geos_version_string, geos_version, geos_capi_version = _geos_version()

# If we have the new interface, then record a baseline so that we know what
# additional functions are declared in ctypes_declarations.
if geos_version >= (3, 1, 0):
    start_set = set(_lgeos.__dict__)

# Apply prototypes for the libgeos_c functions
prototype(_lgeos, geos_version)

# If we have the new interface, automatically detect all function
# declarations, and declare their re-entrant counterpart.
if geos_version >= (3, 1, 0):
    end_set = set(_lgeos.__dict__)
    new_func_names = end_set - start_set

    for func_name in new_func_names:
        new_func_name = "%s_r" % func_name
        if hasattr(_lgeos, new_func_name):
            new_func = getattr(_lgeos, new_func_name)
            old_func = getattr(_lgeos, func_name)
            new_func.restype = old_func.restype
            if old_func.argtypes is None:
                # Handle functions that didn't take an argument before,
                # finishGEOS.
                new_func.argtypes = [c_void_p]
            else:
                new_func.argtypes = [c_void_p] + old_func.argtypes
            if old_func.errcheck is not None:
                new_func.errcheck = old_func.errcheck

    # Handle special case.
    _lgeos.initGEOS_r.restype = c_void_p
    _lgeos.initGEOS_r.argtypes = \
        [EXCEPTION_HANDLER_FUNCTYPE, EXCEPTION_HANDLER_FUNCTYPE]
    _lgeos.finishGEOS_r.argtypes = [c_void_p]

# Exceptions


class ReadingError(Exception):
    pass


class DimensionError(Exception):
    pass


class TopologicalError(Exception):
    pass


class PredicateError(Exception):
    pass


def error_handler(fmt, *args):
    if sys.version_info[0] >= 3:
        fmt = fmt.decode('ascii')
        args = [arg.decode('ascii') for arg in args]
    LOG.error(fmt, *args)


def notice_handler(fmt, args):
    if sys.version_info[0] >= 3:
        fmt = fmt.decode('ascii')
        args = args.decode('ascii')
    LOG.warning(fmt, args)

error_h = EXCEPTION_HANDLER_FUNCTYPE(error_handler)
notice_h = EXCEPTION_HANDLER_FUNCTYPE(notice_handler)


class WKTReader(object):

    _lgeos = None
    _reader = None

    def __init__(self, lgeos):
        """Create WKT Reader"""
        self._lgeos = lgeos
        self._reader = self._lgeos.GEOSWKTReader_create()

    def __del__(self):
        """Destroy WKT Reader"""
        if self._lgeos is not None:
            self._lgeos.GEOSWKTReader_destroy(self._reader)
            self._reader = None
            self._lgeos = None

    def read(self, text):
        """Returns geometry from WKT"""
        if sys.version_info[0] >= 3:
            text = text.encode('ascii')
        geom = self._lgeos.GEOSWKTReader_read(self._reader, c_char_p(text))
        if not geom:
            raise ReadingError("Could not create geometry because of errors "
                               "while reading input.")
        # avoid circular import dependency
        from shapely.geometry.base import geom_factory
        return geom_factory(geom)


class WKTWriter(object):

    _lgeos = None
    _writer = None

    # Establish default output settings
    defaults = {}

    if geos_version >= (3, 3, 0):

        defaults['trim'] = True
        defaults['output_dimension'] = 3

        # GEOS' defaults for methods without "get"
        _trim = False
        _rounding_precision = -1
        _old_3d = False

        @property
        def trim(self):
            """Trimming of unnecessary decimals (default: True)"""
            return getattr(self, '_trim')

        @trim.setter
        def trim(self, value):
            self._trim = bool(value)
            self._lgeos.GEOSWKTWriter_setTrim(self._writer, self._trim)

        @property
        def rounding_precision(self):
            """Rounding precision when writing the WKT.
            A precision of -1 (default) disables it."""
            return getattr(self, '_rounding_precision')

        @rounding_precision.setter
        def rounding_precision(self, value):
            self._rounding_precision = int(value)
            self._lgeos.GEOSWKTWriter_setRoundingPrecision(
                self._writer, self._rounding_precision)

        @property
        def output_dimension(self):
            """Output dimension, either 2 or 3 (default)"""
            return self._lgeos.GEOSWKTWriter_getOutputDimension(
                self._writer)

        @output_dimension.setter
        def output_dimension(self, value):
            self._lgeos.GEOSWKTWriter_setOutputDimension(
                self._writer, int(value))

        @property
        def old_3d(self):
            """Show older style for 3D WKT, without 'Z' (default: False)"""
            return getattr(self, '_old_3d')

        @old_3d.setter
        def old_3d(self, value):
            self._old_3d = bool(value)
            self._lgeos.GEOSWKTWriter_setOld3D(self._writer, self._old_3d)

    def __init__(self, lgeos, **settings):
        """Create WKT Writer

        Note: writer defaults are set differently for GEOS 3.3.0 and up.
        For example, with 'POINT Z (1 2 3)':

            newer: POINT Z (1 2 3)
            older: POINT (1.0000000000000000 2.0000000000000000)

        The older formatting can be achieved for GEOS 3.3.0 and up by setting
        the properties:
            trim = False
            output_dimension = 2
        """
        self._lgeos = lgeos
        self._writer = self._lgeos.GEOSWKTWriter_create()

        applied_settings = self.defaults.copy()
        applied_settings.update(settings)
        for name in applied_settings:
            setattr(self, name, applied_settings[name])

    def __setattr__(self, name, value):
        """Limit setting attributes"""
        if hasattr(self, name):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError('%r object has no attribute %r' %
                                 (self.__class__.__name__, name))

    def __del__(self):
        """Destroy WKT Writer"""
        if self._lgeos is not None:
            self._lgeos.GEOSWKTWriter_destroy(self._writer)
            self._writer = None
            self._lgeos = None

    def write(self, geom):
        """Returns WKT string for geometry"""
        if geom is None or geom._geom is None:
            raise ValueError("Null geometry supports no operations")
        result = self._lgeos.GEOSWKTWriter_write(self._writer, geom._geom)
        text = string_at(result)
        lgeos.GEOSFree(result)
        if sys.version_info[0] >= 3:
            return text.decode('ascii')
        else:
            return text


class WKBReader(object):

    _lgeos = None
    _reader = None

    def __init__(self, lgeos):
        """Create WKB Reader"""
        self._lgeos = lgeos
        self._reader = self._lgeos.GEOSWKBReader_create()

    def __del__(self):
        """Destroy WKB Reader"""
        if self._lgeos is not None:
            self._lgeos.GEOSWKBReader_destroy(self._reader)
            self._reader = None
            self._lgeos = None

    def read(self, data):
        """Returns geometry from WKB"""
        geom = self._lgeos.GEOSWKBReader_read(
            self._reader, c_char_p(data), c_size_t(len(data)))
        if not geom:
            raise ReadingError("Could not create geometry because of errors "
                               "while reading input.")
        # avoid circular import dependency
        from shapely import geometry
        return geometry.base.geom_factory(geom)

    def read_hex(self, data):
        """Returns geometry from WKB hex"""
        if sys.version_info[0] >= 3:
            data = data.encode('ascii')
        geom = self._lgeos.GEOSWKBReader_readHEX(
            self._reader, c_char_p(data), c_size_t(len(data)))
        if not geom:
            raise ReadingError("Could not create geometry because of errors "
                               "while reading input.")
        # avoid circular import dependency
        from shapely import geometry
        return geometry.base.geom_factory(geom)


class WKBWriter(object):

    _lgeos = None
    _writer = None

    # Establish default output setting
    defaults = {'output_dimension': 3}

    @property
    def output_dimension(self):
        """Output dimension, either 2 or 3 (default)"""
        return self._lgeos.GEOSWKBWriter_getOutputDimension(self._writer)

    @output_dimension.setter
    def output_dimension(self, value):
        self._lgeos.GEOSWKBWriter_setOutputDimension(
            self._writer, int(value))

    @property
    def big_endian(self):
        """Byte order is big endian, True (default) or False"""
        return bool(self._lgeos.GEOSWKBWriter_getByteOrder(self._writer))

    @big_endian.setter
    def big_endian(self, value):
        self._lgeos.GEOSWKBWriter_setByteOrder(self._writer, bool(value))

    @property
    def include_srid(self):
        """Include SRID, True or False (default)"""
        return bool(self._lgeos.GEOSWKBWriter_getIncludeSRID(self._writer))

    @include_srid.setter
    def include_srid(self, value):
        self._lgeos.GEOSWKBWriter_setIncludeSRID(self._writer, bool(value))

    def __init__(self, lgeos, **settings):
        """Create WKB Writer"""
        self._lgeos = lgeos
        self._writer = self._lgeos.GEOSWKBWriter_create()

        applied_settings = self.defaults.copy()
        applied_settings.update(settings)
        for name in applied_settings:
            setattr(self, name, applied_settings[name])

    def __setattr__(self, name, value):
        """Limit setting attributes"""
        if hasattr(self, name):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError('%r object has no attribute %r' %
                                 (self.__class__.__name__, name))

    def __del__(self):
        """Destroy WKB Writer"""
        if self._lgeos is not None:
            self._lgeos.GEOSWKBWriter_destroy(self._writer)
            self._writer = None
            self._lgeos = None

    def write(self, geom):
        """Returns WKB byte string for geometry"""
        if geom is None or geom._geom is None:
            raise ValueError("Null geometry supports no operations")
        size = c_size_t()
        result = self._lgeos.GEOSWKBWriter_write(
            self._writer, geom._geom, pointer(size))
        data = string_at(result, size.value)
        lgeos.GEOSFree(result)
        return data

    def write_hex(self, geom):
        """Returns WKB hex string for geometry"""
        if geom is None or geom._geom is None:
            raise ValueError("Null geometry supports no operations")
        size = c_size_t()
        result = self._lgeos.GEOSWKBWriter_writeHEX(
            self._writer, geom._geom, pointer(size))
        data = string_at(result, size.value)
        lgeos.GEOSFree(result)
        if sys.version_info[0] >= 3:
            return data.decode('ascii')
        else:
            return data


# Errcheck functions for ctypes

def errcheck_wkb(result, func, argtuple):
    '''Returns bytes from a C pointer'''
    if not result:
        return None
    size_ref = argtuple[-1]
    size = size_ref.contents
    retval = string_at(result, size.value)[:]
    lgeos.GEOSFree(result)
    return retval


def errcheck_just_free(result, func, argtuple):
    '''Returns string from a C pointer'''
    retval = string_at(result)
    lgeos.GEOSFree(result)
    if sys.version_info[0] >= 3:
        return retval.decode('ascii')
    else:
        return retval


def errcheck_predicate(result, func, argtuple):
    '''Result is 2 on exception, 1 on True, 0 on False'''
    if result == 2:
        raise PredicateError("Failed to evaluate %s" % repr(func))
    return result


class LGEOSBase(threading.local):
    """Proxy for GEOS C API

    This is a base class. Do not instantiate.
    """
    methods = {}

    def __init__(self, dll):
        self._lgeos = dll
        self.geos_handle = None

    def __del__(self):
        """Cleanup GEOS related processes"""
        if self._lgeos is not None:
            self._lgeos.finishGEOS()
            self._lgeos = None
            self.geos_handle = None


class LGEOS300(LGEOSBase):
    """Proxy for GEOS 3.0.0-CAPI-1.4.1
    """
    geos_version = (3, 0, 0)
    geos_capi_version = (1, 4, 0)

    def __init__(self, dll):
        super(LGEOS300, self).__init__(dll)
        self.geos_handle = self._lgeos.initGEOS(notice_h, error_h)
        keys = list(self._lgeos.__dict__.keys())
        for key in keys:
            setattr(self, key, getattr(self._lgeos, key))
        self.GEOSFree = self._lgeos.free
        # Deprecated
        self.GEOSGeomToWKB_buf.errcheck = errcheck_wkb
        self.GEOSGeomToWKT.errcheck = errcheck_just_free
        self.GEOSRelate.errcheck = errcheck_just_free
        for pred in (
                self.GEOSDisjoint,
                self.GEOSTouches,
                self.GEOSIntersects,
                self.GEOSCrosses,
                self.GEOSWithin,
                self.GEOSContains,
                self.GEOSOverlaps,
                self.GEOSEquals,
                self.GEOSEqualsExact,
                self.GEOSisEmpty,
                self.GEOSisValid,
                self.GEOSisSimple,
                self.GEOSisRing,
                self.GEOSHasZ):
            pred.errcheck = errcheck_predicate

        self.methods['area'] = self.GEOSArea
        self.methods['boundary'] = self.GEOSBoundary
        self.methods['buffer'] = self.GEOSBuffer
        self.methods['centroid'] = self.GEOSGetCentroid
        self.methods['representative_point'] = self.GEOSPointOnSurface
        self.methods['convex_hull'] = self.GEOSConvexHull
        self.methods['distance'] = self.GEOSDistance
        self.methods['envelope'] = self.GEOSEnvelope
        self.methods['length'] = self.GEOSLength
        self.methods['has_z'] = self.GEOSHasZ
        self.methods['is_empty'] = self.GEOSisEmpty
        self.methods['is_ring'] = self.GEOSisRing
        self.methods['is_simple'] = self.GEOSisSimple
        self.methods['is_valid'] = self.GEOSisValid
        self.methods['disjoint'] = self.GEOSDisjoint
        self.methods['touches'] = self.GEOSTouches
        self.methods['intersects'] = self.GEOSIntersects
        self.methods['crosses'] = self.GEOSCrosses
        self.methods['within'] = self.GEOSWithin
        self.methods['contains'] = self.GEOSContains
        self.methods['overlaps'] = self.GEOSOverlaps
        self.methods['equals'] = self.GEOSEquals
        self.methods['equals_exact'] = self.GEOSEqualsExact
        self.methods['relate'] = self.GEOSRelate
        self.methods['difference'] = self.GEOSDifference
        self.methods['symmetric_difference'] = self.GEOSSymDifference
        self.methods['union'] = self.GEOSUnion
        self.methods['intersection'] = self.GEOSIntersection
        self.methods['simplify'] = self.GEOSSimplify
        self.methods['topology_preserve_simplify'] = \
            self.GEOSTopologyPreserveSimplify


class LGEOS310(LGEOSBase):
    """Proxy for GEOS 3.1.0-CAPI-1.5.0
    """
    geos_version = (3, 1, 0)
    geos_capi_version = (1, 5, 0)

    def __init__(self, dll):
        super(LGEOS310, self).__init__(dll)
        self.geos_handle = self._lgeos.initGEOS_r(notice_h, error_h)
        keys = list(self._lgeos.__dict__.keys())
        for key in [x for x in keys if not x.endswith('_r')]:
            if key + '_r' in keys:
                reentr_func = getattr(self._lgeos, key + '_r')
                attr = ftools.partial(reentr_func, self.geos_handle)
                attr.__name__ = reentr_func.__name__
                setattr(self, key, attr)
            else:
                setattr(self, key, getattr(self._lgeos, key))
        if not hasattr(self, 'GEOSFree'):
            # GEOS < 3.1.1
            self.GEOSFree = self._lgeos.free
        # Deprecated
        self.GEOSGeomToWKB_buf.func.errcheck = errcheck_wkb
        self.GEOSGeomToWKT.func.errcheck = errcheck_just_free
        self.GEOSRelate.func.errcheck = errcheck_just_free
        for pred in (
                self.GEOSDisjoint,
                self.GEOSTouches,
                self.GEOSIntersects,
                self.GEOSCrosses,
                self.GEOSWithin,
                self.GEOSContains,
                self.GEOSOverlaps,
                self.GEOSEquals,
                self.GEOSEqualsExact,
                self.GEOSisEmpty,
                self.GEOSisValid,
                self.GEOSisSimple,
                self.GEOSisRing,
                self.GEOSHasZ):
            pred.func.errcheck = errcheck_predicate

        self.GEOSisValidReason.func.errcheck = errcheck_just_free

        self.methods['area'] = self.GEOSArea
        self.methods['boundary'] = self.GEOSBoundary
        self.methods['buffer'] = self.GEOSBuffer
        self.methods['centroid'] = self.GEOSGetCentroid
        self.methods['representative_point'] = self.GEOSPointOnSurface
        self.methods['convex_hull'] = self.GEOSConvexHull
        self.methods['distance'] = self.GEOSDistance
        self.methods['envelope'] = self.GEOSEnvelope
        self.methods['length'] = self.GEOSLength
        self.methods['has_z'] = self.GEOSHasZ
        self.methods['is_empty'] = self.GEOSisEmpty
        self.methods['is_ring'] = self.GEOSisRing
        self.methods['is_simple'] = self.GEOSisSimple
        self.methods['is_valid'] = self.GEOSisValid
        self.methods['disjoint'] = self.GEOSDisjoint
        self.methods['touches'] = self.GEOSTouches
        self.methods['intersects'] = self.GEOSIntersects
        self.methods['crosses'] = self.GEOSCrosses
        self.methods['within'] = self.GEOSWithin
        self.methods['contains'] = self.GEOSContains
        self.methods['overlaps'] = self.GEOSOverlaps
        self.methods['equals'] = self.GEOSEquals
        self.methods['equals_exact'] = self.GEOSEqualsExact
        self.methods['relate'] = self.GEOSRelate
        self.methods['difference'] = self.GEOSDifference
        self.methods['symmetric_difference'] = self.GEOSSymDifference
        self.methods['union'] = self.GEOSUnion
        self.methods['intersection'] = self.GEOSIntersection
        self.methods['prepared_intersects'] = self.GEOSPreparedIntersects
        self.methods['prepared_contains'] = self.GEOSPreparedContains
        self.methods['prepared_contains_properly'] = \
            self.GEOSPreparedContainsProperly
        self.methods['prepared_covers'] = self.GEOSPreparedCovers
        self.methods['simplify'] = self.GEOSSimplify
        self.methods['topology_preserve_simplify'] = \
            self.GEOSTopologyPreserveSimplify
        self.methods['cascaded_union'] = self.GEOSUnionCascaded


class LGEOS311(LGEOS310):
    """Proxy for GEOS 3.1.1-CAPI-1.6.0
    """
    geos_version = (3, 1, 1)
    geos_capi_version = (1, 6, 0)

    def __init__(self, dll):
        super(LGEOS311, self).__init__(dll)


class LGEOS320(LGEOS311):
    """Proxy for GEOS 3.2.0-CAPI-1.6.0
    """
    geos_version = (3, 2, 0)
    geos_capi_version = (1, 6, 0)

    def __init__(self, dll):
        super(LGEOS320, self).__init__(dll)

        self.methods['parallel_offset'] = self.GEOSSingleSidedBuffer
        self.methods['project'] = self.GEOSProject
        self.methods['project_normalized'] = self.GEOSProjectNormalized
        self.methods['interpolate'] = self.GEOSInterpolate
        self.methods['interpolate_normalized'] = \
            self.GEOSInterpolateNormalized
        self.methods['buffer_with_style'] = self.GEOSBufferWithStyle


class LGEOS330(LGEOS320):
    """Proxy for GEOS 3.3.0-CAPI-1.7.0
    """
    geos_version = (3, 3, 0)
    geos_capi_version = (1, 7, 0)

    def __init__(self, dll):
        super(LGEOS330, self).__init__(dll)

        # GEOS 3.3.8 from homebrew has, but doesn't advertise
        # GEOSPolygonize_full. We patch it in explicitly here.
        key = 'GEOSPolygonize_full'
        func = getattr(self._lgeos, key + '_r')
        attr = ftools.partial(func, self.geos_handle)
        attr.__name__ = func.__name__
        setattr(self, key, attr)

        self.methods['unary_union'] = self.GEOSUnaryUnion
        self.methods['cascaded_union'] = self.methods['unary_union']


if geos_version >= (3, 3, 0):
    L = LGEOS330
elif geos_version >= (3, 2, 0):
    L = LGEOS320
elif geos_version >= (3, 1, 1):
    L = LGEOS311
elif geos_version >= (3, 1, 0):
    L = LGEOS310
else:
    L = LGEOS300

lgeos = L(_lgeos)

def cleanup(proxy):
    del proxy

atexit.register(cleanup, lgeos)

########NEW FILE########
__FILENAME__ = impl
"""Implementation of the intermediary layer between Shapely and GEOS

This is layer number 2 from the list below.

1) geometric objects: the Python OO API.
2) implementation map: an abstraction that permits different backends.
3) backend: callable objects that take Shapely geometric objects as arguments
   and, with GEOS as a backend, translate them to C data structures.
4) GEOS library: algorithms implemented in C++.

Shapely 1.2 includes a GEOS backend and it is the default.
"""

from .ftools import wraps

from shapely.algorithms import cga
from shapely.coords import BoundsOp
from shapely.geos import lgeos
from shapely.linref import ProjectOp, InterpolateOp
from shapely.predicates import BinaryPredicate, UnaryPredicate
from shapely.topology import BinaryRealProperty, BinaryTopologicalOp
from shapely.topology import UnaryRealProperty, UnaryTopologicalOp

def delegated(func):
    """A delegated method raises AttributeError in the absence of backend
    support."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            raise AttributeError("Method %r is not supported by %r" %
                                 (func.__name__, args[0].impl))
    return wrapper

# Map geometry methods to their GEOS delegates

class BaseImpl(object):
    def __init__(self, values):
        self.map = dict(values)
    def update(self, values):
        self.map.update(values)
    def __getitem__(self, key):
        return self.map[key]
    def __contains__(self, key):
        return key in self.map

class GEOSImpl(BaseImpl):
    def __repr__(self):
        return '<GEOSImpl object: GEOS C API version %s>' % (
            lgeos.geos_capi_version,)

IMPL300 = {
    'area': (UnaryRealProperty, 'area'),
    'distance': (BinaryRealProperty, 'distance'),
    'length': (UnaryRealProperty, 'length'),
    #
    'boundary': (UnaryTopologicalOp, 'boundary'),
    'bounds': (BoundsOp, None),
    'centroid': (UnaryTopologicalOp, 'centroid'),
    'representative_point': (UnaryTopologicalOp, 'representative_point'),
    'envelope': (UnaryTopologicalOp, 'envelope'),
    'convex_hull': (UnaryTopologicalOp, 'convex_hull'),
    'buffer': (UnaryTopologicalOp, 'buffer'),
    #
    'difference': (BinaryTopologicalOp, 'difference'),
    'intersection': (BinaryTopologicalOp, 'intersection'),
    'symmetric_difference': (BinaryTopologicalOp, 'symmetric_difference'),
    'union': (BinaryTopologicalOp, 'union'),
    #
    'has_z': (UnaryPredicate, 'has_z'),
    'is_empty': (UnaryPredicate, 'is_empty'),
    'is_ring': (UnaryPredicate, 'is_ring'),
    'is_simple': (UnaryPredicate, 'is_simple'),
    'is_valid': (UnaryPredicate, 'is_valid'),
    #
    'relate': (BinaryPredicate, 'relate'),
    'contains': (BinaryPredicate, 'contains'),
    'crosses': (BinaryPredicate, 'crosses'),
    'disjoint': (BinaryPredicate, 'disjoint'),
    'equals': (BinaryPredicate, 'equals'),
    'intersects': (BinaryPredicate, 'intersects'),
    'overlaps': (BinaryPredicate, 'overlaps'),
    'touches': (BinaryPredicate, 'touches'),
    'within': (BinaryPredicate, 'within'),
    'equals_exact': (BinaryPredicate, 'equals_exact'),

    # First pure Python implementation
    'is_ccw': (cga.is_ccw_impl, 'is_ccw'),
    }

IMPL310 = {
    'simplify': (UnaryTopologicalOp, 'simplify'),
    'topology_preserve_simplify':
        (UnaryTopologicalOp, 'topology_preserve_simplify'),
    'prepared_intersects': (BinaryPredicate, 'prepared_intersects'),
    'prepared_contains': (BinaryPredicate, 'prepared_contains'),
    'prepared_contains_properly':
        (BinaryPredicate, 'prepared_contains_properly'),
    'prepared_covers': (BinaryPredicate, 'prepared_covers'),
    }

IMPL311 = {
    }

IMPL320 = {
    'parallel_offset': (UnaryTopologicalOp, 'parallel_offset'),
    'project_normalized': (ProjectOp, 'project_normalized'),
    'project': (ProjectOp, 'project'),
    'interpolate_normalized': (InterpolateOp, 'interpolate_normalized'),
    'interpolate': (InterpolateOp, 'interpolate'),
    'buffer_with_style': (UnaryTopologicalOp, 'buffer_with_style'),
    }

def impl_items(defs):
    return [(k, v[0](v[1])) for k, v in list(defs.items())]

imp = GEOSImpl(dict(impl_items(IMPL300)))
if lgeos.geos_version >= (3, 1, 0):
    imp.update(impl_items(IMPL310))
if lgeos.geos_version >= (3, 1, 1):
    imp.update(impl_items(IMPL311))
if lgeos.geos_version >= (3, 2, 0):
    imp.update(impl_items(IMPL320))

DefaultImplementation = imp

########NEW FILE########
__FILENAME__ = iterops
"""
Iterative forms of operations
"""
from warnings import warn
from ctypes import c_char_p, c_size_t
from shapely.geos import lgeos, PredicateError


def geos_from_geometry(geom):
    warn("`geos_from_geometry` is deprecated. Use geometry's `wkb` property "
         "instead.", DeprecationWarning)
    data = geom.to_wkb()
    return lgeos.GEOSGeomFromWKB_buf(
                        c_char_p(data),
                        c_size_t(len(data))
                        )


class IterOp(object):
    
    """A generating non-data descriptor.
    """
    
    def __init__(self, fn):
        self.fn = fn
    
    def __call__(self, context, iterator, value=True):
        if context._geom is None:
            raise ValueError("Null geometry supports no operations")
        for item in iterator:
            try:
                this_geom, ob = item
            except TypeError:
                this_geom = item
                ob = this_geom
            if not this_geom._geom:
                raise ValueError("Null geometry supports no operations")
            retval = self.fn(context._geom, this_geom._geom)
            if retval == 2:
                raise PredicateError(
                    "Failed to evaluate %s" % repr(self.fn))
            elif bool(retval) == value:
                yield ob


# utilities
disjoint = IterOp(lgeos.GEOSDisjoint)
touches = IterOp(lgeos.GEOSTouches)
intersects = IterOp(lgeos.GEOSIntersects)
crosses = IterOp(lgeos.GEOSCrosses)
within = IterOp(lgeos.GEOSWithin)
contains = IterOp(lgeos.GEOSContains)
overlaps = IterOp(lgeos.GEOSOverlaps)
equals = IterOp(lgeos.GEOSEquals)


########NEW FILE########
__FILENAME__ = linref
"""Linear referencing
"""

from shapely.topology import Delegating


class LinearRefBase(Delegating):
    def _validate_line(self, ob):
        super(LinearRefBase, self)._validate(ob)
        try:
            assert ob.geom_type in ['LineString', 'MultiLineString']
        except AssertionError:
            raise TypeError("Only linear types support this operation")

class ProjectOp(LinearRefBase):
    def __call__(self, this, other):
        self._validate_line(this)
        self._validate(other)
        return self.fn(this._geom, other._geom)

class InterpolateOp(LinearRefBase):
    def __call__(self, this, distance):
        self._validate_line(this)
        return self.fn(this._geom, distance)



########NEW FILE########
__FILENAME__ = ops
"""Support for various GEOS geometry operations
"""

import sys

if sys.version_info[0] < 3:
    from itertools import izip
else:
    izip = zip

from ctypes import byref, c_void_p

from shapely.geos import lgeos
from shapely.geometry.base import geom_factory, BaseGeometry
from shapely.geometry import asShape, asLineString, asMultiLineString

__all__ = ['cascaded_union', 'linemerge', 'operator', 'polygonize',
           'polygonize_full', 'transform', 'unary_union']


class CollectionOperator(object):

    def shapeup(self, ob):
        if isinstance(ob, BaseGeometry):
            return ob
        else:
            try:
                return asShape(ob)
            except ValueError:
                return asLineString(ob)

    def polygonize(self, lines):
        """Creates polygons from a source of lines

        The source may be a MultiLineString, a sequence of LineString objects,
        or a sequence of objects than can be adapted to LineStrings.
        """
        source = getattr(lines, 'geoms', None) or lines
        obs = [self.shapeup(l) for l in source]
        geom_array_type = c_void_p * len(obs)
        geom_array = geom_array_type()
        for i, line in enumerate(obs):
            geom_array[i] = line._geom
        product = lgeos.GEOSPolygonize(byref(geom_array), len(obs))
        collection = geom_factory(product)
        for g in collection.geoms:
            clone = lgeos.GEOSGeom_clone(g._geom)
            g = geom_factory(clone)
            g._owned = False
            yield g

    def polygonize_full(self, lines):
        """Creates polygons from a source of lines, returning the polygons
        and leftover geometries.

        The source may be a MultiLineString, a sequence of LineString objects,
        or a sequence of objects than can be adapted to LineStrings.

        Returns a tuple of objects: (polygons, dangles, cut edges, invalid ring
        lines). Each are a geometry collection.

        Dangles are edges which have one or both ends which are not incident on
        another edge endpoint. Cut edges are connected at both ends but do not
        form part of polygon. Invalid ring lines form rings which are invalid
        (bowties, etc).
        """
        source = getattr(lines, 'geoms', None) or lines
        obs = [self.shapeup(l) for l in source]

        L = len(obs)
        subs = (c_void_p * L)()
        for i, g in enumerate(obs):
            subs[i] = g._geom
        collection = lgeos.GEOSGeom_createCollection(5, subs, L)
        dangles = c_void_p()
        cuts = c_void_p()
        invalids = c_void_p()
        product = lgeos.GEOSPolygonize_full(
            collection, byref(dangles), byref(cuts), byref(invalids))
        return (
            geom_factory(product),
            geom_factory(dangles),
            geom_factory(cuts),
            geom_factory(invalids)
            )

    def linemerge(self, lines):
        """Merges all connected lines from a source

        The source may be a MultiLineString, a sequence of LineString objects,
        or a sequence of objects than can be adapted to LineStrings.  Returns a
        LineString or MultiLineString when lines are not contiguous.
        """
        source = None
        if hasattr(lines, 'type') and lines.type == 'MultiLineString':
            source = lines
        elif hasattr(lines, '__iter__'):
            try:
                source = asMultiLineString([ls.coords for ls in lines])
            except AttributeError:
                source = asMultiLineString(lines)
        if source is None:
            raise ValueError("Cannot linemerge %s" % lines)
        result = lgeos.GEOSLineMerge(source._geom)
        return geom_factory(result)

    def cascaded_union(self, geoms):
        """Returns the union of a sequence of geometries

        This is the most efficient method of dissolving many polygons.
        """
        L = len(geoms)
        subs = (c_void_p * L)()
        for i, g in enumerate(geoms):
            subs[i] = g._geom
        collection = lgeos.GEOSGeom_createCollection(6, subs, L)
        return geom_factory(lgeos.methods['cascaded_union'](collection))

    def unary_union(self, geoms):
        """Returns the union of a sequence of geometries

        This method replaces :meth:`cascaded_union` as the
        prefered method for dissolving many polygons.

        """
        L = len(geoms)
        subs = (c_void_p * L)()
        for i, g in enumerate(geoms):
            subs[i] = g._geom
        collection = lgeos.GEOSGeom_createCollection(6, subs, L)
        return geom_factory(lgeos.methods['unary_union'](collection))

operator = CollectionOperator()
polygonize = operator.polygonize
polygonize_full = operator.polygonize_full
linemerge = operator.linemerge
cascaded_union = operator.cascaded_union
unary_union = operator.unary_union


class ValidateOp(object):
    def __call__(self, this):
        return lgeos.GEOSisValidReason(this._geom)

validate = ValidateOp()


def transform(func, geom):
    """Applies `func` to all coordinates of `geom` and returns a new
    geometry of the same type from the transformed coordinates.

    `func` maps x, y, and optionally z to output xp, yp, zp. The input
    parameters may iterable types like lists or arrays or single values.
    The output shall be of the same type. Scalars in, scalars out.
    Lists in, lists out.

    For example, here is an identity function applicable to both types
    of input.

      def id_func(x, y, z=None):
          return tuple(filter(None, [x, y, z]))

      g2 = transform(id_func, g1)

    A partially applied transform function from pyproj satisfies the
    requirements for `func`.

      from functools import partial
      import pyproj

      project = partial(
          pyproj.transform,
          pyproj.Proj(init='espg:4326'),
          pyproj.Proj(init='epsg:26913'))

      g2 = transform(project, g1)

    Lambda expressions such as the one in

      g2 = transform(lambda x, y, z=None: (x+1.0, y+1.0), g1)

    also satisfy the requirements for `func`.
    """
    if geom.is_empty:
        return geom
    if geom.type in ('Point', 'LineString', 'LinearRing', 'Polygon'):

        # First we try to apply func to x, y, z sequences. When func is
        # optimized for sequences, this is the fastest, though zipping
        # the results up to go back into the geometry constructors adds
        # extra cost.
        try:
            if geom.type in ('Point', 'LineString', 'LinearRing'):
                return type(geom)(zip(*func(*izip(*geom.coords))))
            elif geom.type == 'Polygon':
                shell = type(geom.exterior)(
                    zip(*func(*izip(*geom.exterior.coords))))
                holes = list(type(ring)(zip(*func(*izip(*ring.coords))))
                             for ring in geom.interiors)
                return type(geom)(shell, holes)

        # A func that assumes x, y, z are single values will likely raise a
        # TypeError, in which case we'll try again.
        except TypeError:
            if geom.type in ('Point', 'LineString', 'LinearRing'):
                return type(geom)([func(*c) for c in geom.coords])
            elif geom.type == 'Polygon':
                shell = type(geom.exterior)(
                    [func(*c) for c in geom.exterior.coords])
                holes = list(type(ring)([func(*c) for c in ring.coords])
                             for ring in geom.interiors)
                return type(geom)(shell, holes)

    elif geom.type.startswith('Multi') or geom.type == 'GeometryCollection':
        return type(geom)([transform(func, part) for part in geom.geoms])
    else:
        raise ValueError('Type %r not recognized' % geom.type)
########NEW FILE########
__FILENAME__ = predicates
"""
Support for GEOS spatial predicates
"""

from shapely.topology import Delegating

class BinaryPredicate(Delegating):
    def __call__(self, this, other, *args):
        self._validate(this)
        self._validate(other, stop_prepared=True)
        return self.fn(this._geom, other._geom, *args)

class RelateOp(Delegating):
    def __call__(self, this, other):
        self._validate(this)
        self._validate(other, stop_prepared=True)
        return self.fn(this._geom, other._geom)

class UnaryPredicate(Delegating):
    def __call__(self, this):
        self._validate(this)
        return self.fn(this._geom)


########NEW FILE########
__FILENAME__ = prepared
"""
Support for GEOS prepared geometry operations.
"""

from shapely.geos import lgeos
from shapely.impl import DefaultImplementation, delegated


class PreparedGeometry(object):
    """
    A geometry prepared for efficient comparison to a set of other geometries.
    
    Example:
      
      >>> from shapely.geometry import Point, Polygon
      >>> triangle = Polygon(((0.0, 0.0), (1.0, 1.0), (1.0, -1.0)))
      >>> p = prep(triangle)
      >>> p.intersects(Point(0.5, 0.5))
      True
    """
   
    impl = DefaultImplementation
    
    def __init__(self, context):
        self.context = context
        self.__geom__ = lgeos.GEOSPrepare(self.context._geom)
    
    def __del__(self):
        if self.__geom__ is not None:
            try:
                lgeos.GEOSPreparedGeom_destroy(self.__geom__)
            except AttributeError:
                pass # lgeos might be empty on shutdown
        self.__geom__ = None
        self.context = None
    
    @property
    def _geom(self):
        return self.__geom__
   
    @delegated
    def intersects(self, other):
        return bool(self.impl['prepared_intersects'](self, other))

    @delegated
    def contains(self, other):
        return bool(self.impl['prepared_contains'](self, other))

    @delegated
    def contains_properly(self, other):
        return bool(self.impl['prepared_contains_properly'](self, other))

    @delegated
    def covers(self, other):
        return bool(self.impl['prepared_covers'](self, other))


def prep(ob):
    """Creates and returns a prepared geometric object."""
    return PreparedGeometry(ob)


########NEW FILE########
__FILENAME__ = test_affinity
from . import unittest
from math import pi
from shapely import affinity
from shapely.wkt import loads as load_wkt
from shapely.geometry import Point


class AffineTestCase(unittest.TestCase):

    def test_affine_params(self):
        g = load_wkt('LINESTRING(2.4 4.1, 2.4 3, 3 3)')
        self.assertRaises(
            TypeError, affinity.affine_transform, g, None)
        self.assertRaises(
            TypeError, affinity.affine_transform, g, '123456')
        self.assertRaises(ValueError, affinity.affine_transform, g,
                          [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertRaises(AttributeError, affinity.affine_transform, None,
                          [1, 2, 3, 4, 5, 6])

    def test_affine_geom_types(self):

        # identity matrices, which should result with no transformation
        matrix2d = (1, 0,
                    0, 1,
                    0, 0)
        matrix3d = (1, 0, 0,
                    0, 1, 0,
                    0, 0, 1,
                    0, 0, 0)

        # empty in, empty out
        empty2d = load_wkt('MULTIPOLYGON EMPTY')
        self.assertTrue(affinity.affine_transform(empty2d, matrix2d).is_empty)

        def test_geom(g2, g3=None):
            self.assertFalse(g2.has_z)
            a2 = affinity.affine_transform(g2, matrix2d)
            self.assertFalse(a2.has_z)
            self.assertTrue(g2.equals(a2))
            if g3 is not None:
                self.assertTrue(g3.has_z)
                a3 = affinity.affine_transform(g3, matrix3d)
                self.assertTrue(a3.has_z)
                self.assertTrue(g3.equals(a3))
            return

        pt2d = load_wkt('POINT(12.3 45.6)')
        pt3d = load_wkt('POINT(12.3 45.6 7.89)')
        test_geom(pt2d, pt3d)
        ls2d = load_wkt('LINESTRING(0.9 3.4, 0.7 2, 2.5 2.7)')
        ls3d = load_wkt('LINESTRING(0.9 3.4 3.3, 0.7 2 2.3, 2.5 2.7 5.5)')
        test_geom(ls2d, ls3d)
        lr2d = load_wkt('LINEARRING(0.9 3.4, 0.7 2, 2.5 2.7, 0.9 3.4)')
        lr3d = load_wkt(
            'LINEARRING(0.9 3.4 3.3, 0.7 2 2.3, 2.5 2.7 5.5, 0.9 3.4 3.3)')
        test_geom(lr2d, lr3d)
        test_geom(load_wkt('POLYGON((0.9 2.3, 0.5 1.1, 2.4 0.8, 0.9 2.3), '
                           '(1.1 1.7, 0.9 1.3, 1.4 1.2, 1.1 1.7), '
                           '(1.6 1.3, 1.7 1, 1.9 1.1, 1.6 1.3))'))
        test_geom(load_wkt(
            'MULTIPOINT ((-300 300), (700 300), (-800 -1100), (200 -300))'))
        test_geom(load_wkt(
            'MULTILINESTRING((0 0, -0.7 -0.7, 0.6 -1), '
            '(-0.5 0.5, 0.7 0.6, 0 -0.6))'))
        test_geom(load_wkt(
            'MULTIPOLYGON(((900 4300, -1100 -400, 900 -800, 900 4300)), '
            '((1200 4300, 2300 4400, 1900 1000, 1200 4300)))'))
        # GeometryCollection fails, since it does not have a good constructor
        gc = load_wkt('GEOMETRYCOLLECTION(POINT(20 70),'
                      ' POLYGON((60 70, 13 35, 60 -30, 60 70)),'
                      ' LINESTRING(60 70, 50 100, 80 100))')
        self.assertRaises(TypeError, test_geom, gc)  # TODO: fix this

    def test_affine_2d(self):
        g = load_wkt('LINESTRING(2.4 4.1, 2.4 3, 3 3)')
        # custom scale and translate
        expected2d = load_wkt('LINESTRING(-0.2 14.35, -0.2 11.6, 1 11.6)')
        matrix2d = (2, 0,
                    0, 2.5,
                    -5, 4.1)
        a2 = affinity.affine_transform(g, matrix2d)
        self.assertTrue(a2.almost_equals(expected2d))
        self.assertFalse(a2.has_z)
        # Make sure a 3D matrix does not make a 3D shape from a 2D input
        matrix3d = (2, 0, 0,
                    0, 2.5, 0,
                    0, 0, 10,
                    -5, 4.1, 100)
        a3 = affinity.affine_transform(g, matrix3d)
        self.assertTrue(a3.almost_equals(expected2d))
        self.assertFalse(a3.has_z)

    def test_affine_3d(self):
        g2 = load_wkt('LINESTRING(2.4 4.1, 2.4 3, 3 3)')
        g3 = load_wkt('LINESTRING(2.4 4.1 100.2, 2.4 3 132.8, 3 3 128.6)')
        # custom scale and translate
        matrix2d = (2, 0,
                    0, 2.5,
                    -5, 4.1)
        matrix3d = (2, 0, 0,
                    0, 2.5, 0,
                    0, 0, 0.3048,
                    -5, 4.1, 100)
        # Combinations of 2D and 3D geometries and matrices
        a22 = affinity.affine_transform(g2, matrix2d)
        a23 = affinity.affine_transform(g2, matrix3d)
        a32 = affinity.affine_transform(g3, matrix2d)
        a33 = affinity.affine_transform(g3, matrix3d)
        # Check dimensions
        self.assertFalse(a22.has_z)
        self.assertFalse(a23.has_z)
        self.assertTrue(a32.has_z)
        self.assertTrue(a33.has_z)
        # 2D equality checks
        expected2d = load_wkt('LINESTRING(-0.2 14.35, -0.2 11.6, 1 11.6)')
        expected3d = load_wkt('LINESTRING(-0.2 14.35 130.54096, '
                              '-0.2 11.6 140.47744, 1 11.6 139.19728)')
        expected32 = load_wkt('LINESTRING(-0.2 14.35 100.2, '
                              '-0.2 11.6 132.8, 1 11.6 128.6)')
        self.assertTrue(a22.almost_equals(expected2d))
        self.assertTrue(a23.almost_equals(expected2d))
        # Do explicit 3D check of coordinate values
        for a, e in zip(a32.coords, expected32.coords):
            for ap, ep in zip(a, e):
                self.assertAlmostEqual(ap, ep)
        for a, e in zip(a33.coords, expected3d.coords):
            for ap, ep in zip(a, e):
                self.assertAlmostEqual(ap, ep)


class TransformOpsTestCase(unittest.TestCase):

    def test_rotate(self):
        ls = load_wkt('LINESTRING(240 400, 240 300, 300 300)')
        # counter-clockwise degrees
        rls = affinity.rotate(ls, 90)
        els = load_wkt('LINESTRING(220 320, 320 320, 320 380)')
        self.assertTrue(rls.equals(els))
        # retest with named parameters for the same result
        rls = affinity.rotate(geom=ls, angle=90, origin='center')
        self.assertTrue(rls.equals(els))
        # clockwise radians
        rls = affinity.rotate(ls, -pi/2, use_radians=True)
        els = load_wkt('LINESTRING(320 380, 220 380, 220 320)')
        self.assertTrue(rls.equals(els))
        ## other `origin` parameters
        # around the centroid
        rls = affinity.rotate(ls, 90, origin='centroid')
        els = load_wkt('LINESTRING(182.5 320, 282.5 320, 282.5 380)')
        self.assertTrue(rls.equals(els))
        # around the second coordinate tuple
        rls = affinity.rotate(ls, 90, origin=ls.coords[1])
        els = load_wkt('LINESTRING(140 300, 240 300, 240 360)')
        self.assertTrue(rls.equals(els))
        # around the absolute Point of origin
        rls = affinity.rotate(ls, 90, origin=Point(0, 0))
        els = load_wkt('LINESTRING(-400 240, -300 240, -300 300)')
        self.assertTrue(rls.equals(els))

    def test_scale(self):
        ls = load_wkt('LINESTRING(240 400 10, 240 300 30, 300 300 20)')
        # test defaults of 1.0
        sls = affinity.scale(ls)
        self.assertTrue(sls.equals(ls))
        # different scaling in different dimensions
        sls = affinity.scale(ls, 2, 3, 0.5)
        els = load_wkt('LINESTRING(210 500 5, 210 200 15, 330 200 10)')
        self.assertTrue(sls.equals(els))
        # Do explicit 3D check of coordinate values
        for a, b in zip(sls.coords, els.coords):
            for ap, bp in zip(a, b):
                self.assertEqual(ap, bp)
        # retest with named parameters for the same result
        sls = affinity.scale(geom=ls, xfact=2, yfact=3, zfact=0.5,
                             origin='center')
        self.assertTrue(sls.equals(els))
        ## other `origin` parameters
        # around the centroid
        sls = affinity.scale(ls, 2, 3, 0.5, origin='centroid')
        els = load_wkt('LINESTRING(228.75 537.5, 228.75 237.5, 348.75 237.5)')
        self.assertTrue(sls.equals(els))
        # around the second coordinate tuple
        sls = affinity.scale(ls, 2, 3, 0.5, origin=ls.coords[1])
        els = load_wkt('LINESTRING(240 600, 240 300, 360 300)')
        self.assertTrue(sls.equals(els))
        # around some other 3D Point of origin
        sls = affinity.scale(ls, 2, 3, 0.5, origin=Point(100, 200, 1000))
        els = load_wkt('LINESTRING(380 800 505, 380 500 515, 500 500 510)')
        self.assertTrue(sls.equals(els))
        # Do explicit 3D check of coordinate values
        for a, b in zip(sls.coords, els.coords):
            for ap, bp in zip(a, b):
                self.assertEqual(ap, bp)

    def test_skew(self):
        ls = load_wkt('LINESTRING(240 400 10, 240 300 30, 300 300 20)')
        # test default shear angles of 0.0
        sls = affinity.skew(ls)
        self.assertTrue(sls.equals(ls))
        # different shearing in x- and y-directions
        sls = affinity.skew(ls, 15, -30)
        els = load_wkt('LINESTRING (253.39745962155615 417.3205080756888, '
                       '226.60254037844385 317.3205080756888, '
                       '286.60254037844385 282.67949192431126)')
        self.assertTrue(sls.almost_equals(els))
        # retest with radians for the same result
        sls = affinity.skew(ls, pi/12, -pi/6, use_radians=True)
        self.assertTrue(sls.almost_equals(els))
        # retest with named parameters for the same result
        sls = affinity.skew(geom=ls, xs=15, ys=-30,
                            origin='center', use_radians=False)
        self.assertTrue(sls.almost_equals(els))
        ## other `origin` parameters
        # around the centroid
        sls = affinity.skew(ls, 15, -30, origin='centroid')
        els = load_wkt('LINESTRING(258.42150697963973 406.49519052838332, '
                       '231.6265877365273980 306.4951905283833185, '
                       '291.6265877365274264 271.8541743770057337)')
        self.assertTrue(sls.almost_equals(els))
        # around the second coordinate tuple
        sls = affinity.skew(ls, 15, -30, origin=ls.coords[1])
        els = load_wkt('LINESTRING(266.7949192431123038 400, 240 300, '
                       '300 265.3589838486224153)')
        self.assertTrue(sls.almost_equals(els))
        # around the absolute Point of origin
        sls = affinity.skew(ls, 15, -30, origin=Point(0, 0))
        els = load_wkt('LINESTRING(347.179676972449101 261.435935394489832, '
                       '320.3847577293367976 161.4359353944898317, '
                       '380.3847577293367976 126.7949192431122754)')
        self.assertTrue(sls.almost_equals(els))

    def test_translate(self):
        ls = load_wkt('LINESTRING(240 400 10, 240 300 30, 300 300 20)')
        # test default offset of 0.0
        tls = affinity.translate(ls)
        self.assertTrue(tls.equals(ls))
        # test all offsets
        tls = affinity.translate(ls, 100, 400, -10)
        els = load_wkt('LINESTRING(340 800 0, 340 700 20, 400 700 10)')
        self.assertTrue(tls.equals(els))
        # Do explicit 3D check of coordinate values
        for a, b in zip(tls.coords, els.coords):
            for ap, bp in zip(a, b):
                self.assertEqual(ap, bp)
        # retest with named parameters for the same result
        tls = affinity.translate(geom=ls, xoff=100, yoff=400, zoff=-10)
        self.assertTrue(tls.equals(els))


def test_suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(AffineTestCase),
        loader.loadTestsFromTestCase(TransformOpsTestCase)])

########NEW FILE########
__FILENAME__ = test_box
from . import unittest
from shapely import geometry


class BoxTestCase(unittest.TestCase):

    def test_ccw(self):
        b = geometry.box(0, 0, 1, 1, ccw=True)
        self.assertEqual(b.exterior.coords[0], (1.0, 0.0))
        self.assertEqual(b.exterior.coords[1], (1.0, 1.0))

    def test_ccw_default(self):
        b = geometry.box(0, 0, 1, 1)
        self.assertEqual(b.exterior.coords[0], (1.0, 0.0))
        self.assertEqual(b.exterior.coords[1], (1.0, 1.0))

    def test_cw(self):
        b = geometry.box(0, 0, 1, 1, ccw=False)
        self.assertEqual(b.exterior.coords[0], (0.0, 0.0))
        self.assertEqual(b.exterior.coords[1], (0.0, 1.0))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(BoxTestCase)

########NEW FILE########
__FILENAME__ = test_cga
from . import unittest
from shapely.geometry.polygon import LinearRing, orient, Polygon


class RingOrientationTestCase(unittest.TestCase):
    def test_ccw(self):
        ring = LinearRing([(1, 0), (0, 1), (0, 0)])
        self.assertTrue(ring.is_ccw)

    def test_cw(self):
        ring = LinearRing([(0, 0), (0, 1), (1, 0)])
        self.assertFalse(ring.is_ccw)


class PolygonOrienterTestCase(unittest.TestCase):
    def test_no_holes(self):
        ring = LinearRing([(0, 0), (0, 1), (1, 0)])
        polygon = Polygon(ring)
        self.assertFalse(polygon.exterior.is_ccw)
        polygon = orient(polygon, 1)
        self.assertTrue(polygon.exterior.is_ccw)

    def test_holes(self):
        polygon = Polygon([(0, 0), (0, 1), (1, 0)],
                          [[(0.5, 0.25), (0.25, 0.5), (0.25, 0.25)]])
        self.assertFalse(polygon.exterior.is_ccw)
        self.assertTrue(polygon.interiors[0].is_ccw)
        polygon = orient(polygon, 1)
        self.assertTrue(polygon.exterior.is_ccw)
        self.assertFalse(polygon.interiors[0].is_ccw)


def test_suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(RingOrientationTestCase),
        loader.loadTestsFromTestCase(PolygonOrienterTestCase)])

########NEW FILE########
__FILENAME__ = test_collection
from . import unittest
from shapely.geometry import LineString
from shapely.geometry.collection import GeometryCollection


class CollectionTestCase(unittest.TestCase):

    def test_array_interface(self):
        m = GeometryCollection()
        self.assertEqual(len(m), 0)
        self.assertEqual(m.geoms, [])

    def test_child_with_deleted_parent(self):
        # test that we can remove a collection while having
        # childs around
        a = LineString([(0, 0), (1, 1), (1, 2), (2, 2)])
        b = LineString([(0, 0), (1, 1), (2, 1), (2, 2)])
        collection = a.intersection(b)

        child = collection.geoms[0]
        # delete parent of child
        del collection

        # access geometry, this should not seg fault as 1.2.15 did
        self.assertIsNotNone(child.wkt)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(CollectionTestCase)

########NEW FILE########
__FILENAME__ = test_delegated
from . import unittest
from shapely.geometry import Point
from shapely.impl import BaseImpl
from shapely.geometry.base import delegated


class Geometry(object):

    impl = BaseImpl({})

    @property
    @delegated
    def foo(self):
        return self.impl['foo']()


class WrapperTestCase(unittest.TestCase):
    """When the backend has no support for a method, we get an AttributeError
    """

    def test_delegated(self):
        self.assertRaises(AttributeError, getattr, Geometry(), 'foo')

    def test_defaultimpl(self):
        project_impl = Point.impl.map.pop('project', None)
        try:
            self.assertRaises(AttributeError, Point(0, 0).project, 1.0)
        finally:
            if project_impl is not None:
                Point.impl.map['project'] = project_impl


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(WrapperTestCase)

########NEW FILE########
__FILENAME__ = test_dlls
from . import unittest

from shapely.geos import load_dll


class LoadingTestCase(unittest.TestCase):

    def test_load(self):
        self.assertRaises(OSError, load_dll, 'geosh_c')

    def test_fallbacks(self):
        load_dll('geos_c', fallbacks=[
            '/opt/local/lib/libgeos_c.dylib',  # MacPorts
            '/usr/local/lib/libgeos_c.dylib',  # homebrew (Mac OS X)
            'libgeos_c.so.1',
            'libgeos_c.so'])


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(LoadingTestCase)

########NEW FILE########
__FILENAME__ = test_doctests
import os
import doctest
from . import unittest
from glob import glob

optionflags = (doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.NORMALIZE_WHITESPACE |
               doctest.ELLIPSIS)


def list_doctests():
    print(__file__)
    source_files = glob(os.path.join(os.path.dirname(__file__), '*.txt'))
    return [filename for filename in source_files]


def open_file(filename, mode='r'):
    """Helper function to open files from within the tests package."""
    return open(os.path.join(os.path.dirname(__file__), filename), mode)


def setUp(test):
    test.globs.update(dict(open_file=open_file,))


def test_suite():
    return unittest.TestSuite(
        [doctest.DocFileSuite(os.path.basename(filename),
                              optionflags=optionflags,
                              setUp=setUp)
         for filename
         in list_doctests()])

if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(test_suite())

########NEW FILE########
__FILENAME__ = test_emptiness
from . import unittest
from shapely.geometry.base import BaseGeometry
import shapely.geometry as sgeom
from shapely.geometry.polygon import LinearRing


class EmptinessTestCase(unittest.TestCase):

    def test_empty_base(self):
        g = BaseGeometry()
        self.assertTrue(g._is_empty)

    def test_emptying_point(self):
        p = sgeom.Point(0, 0)
        self.assertFalse(p._is_empty)
        p.empty()
        self.assertTrue(p._is_empty)

    def test_none_geom(self):
        p = BaseGeometry()
        p._geom = None
        self.assertTrue(p.is_empty)

    def test_empty_point(self):
        self.assertTrue(sgeom.Point().is_empty)

    def test_empty_multipoint(self):
        self.assertTrue(sgeom.MultiPoint().is_empty)

    def test_empty_geometry_collection(self):
        self.assertTrue(sgeom.GeometryCollection().is_empty)

    def test_empty_linestring(self):
        self.assertTrue(sgeom.LineString().is_empty)

    def test_empty_multilinestring(self):
        self.assertTrue(sgeom.MultiLineString([]).is_empty)

    def test_empty_polygon(self):
        self.assertTrue(sgeom.Polygon().is_empty)

    def test_empty_multipolygon(self):
        self.assertTrue(sgeom.MultiPolygon([]).is_empty)

    def test_empty_linear_ring(self):
        self.assertTrue(LinearRing().is_empty)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(EmptinessTestCase)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_equality
from . import unittest
from shapely import geometry


class PointEqualityTestCase(unittest.TestCase):

    def test_equals_exact(self):
        p1 = geometry.Point(1.0, 1.0)
        p2 = geometry.Point(2.0, 2.0)
        self.assertFalse(p1.equals(p2))
        self.assertFalse(p1.equals_exact(p2, 0.001))

    def test_almost_equals_default(self):
        p1 = geometry.Point(1.0, 1.0)
        p2 = geometry.Point(1.0+1e-7, 1.0+1e-7)  # almost equal to 6 places
        p3 = geometry.Point(1.0+1e-6, 1.0+1e-6)  # not almost equal
        self.assertTrue(p1.almost_equals(p2))
        self.assertFalse(p1.almost_equals(p3))

    def test_almost_equals(self):
        p1 = geometry.Point(1.0, 1.0)
        p2 = geometry.Point(1.1, 1.1)
        self.assertFalse(p1.equals(p2))
        self.assertTrue(p1.almost_equals(p2, 0))
        self.assertFalse(p1.almost_equals(p2, 1))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PointEqualityTestCase)

########NEW FILE########
__FILENAME__ = test_geointerface
from . import unittest
from shapely.geometry import asShape
from shapely.geometry.multipoint import MultiPointAdapter
from shapely.geometry.linestring import LineStringAdapter
from shapely.geometry.multilinestring import MultiLineStringAdapter
from shapely.geometry.polygon import PolygonAdapter
from shapely.geometry.multipolygon import MultiPolygonAdapter


class GeoThing(object):
    def __init__(self, d):
        self.__geo_interface__ = d


class GeoInterfaceTestCase(unittest.TestCase):

    def test_geointerface(self):
        # Adapt a dictionary
        d = {"type": "Point", "coordinates": (0.0, 0.0)}
        shape = asShape(d)
        self.assertEqual(shape.geom_type, 'Point')
        self.assertEqual(tuple(shape.coords), ((0.0, 0.0),))

        # Adapt an object that implements the geo protocol
        shape = None
        thing = GeoThing({"type": "Point", "coordinates": (0.0, 0.0)})
        shape = asShape(thing)
        self.assertEqual(shape.geom_type, 'Point')
        self.assertEqual(tuple(shape.coords), ((0.0, 0.0),))

        # Check line string
        shape = asShape(
            {'type': 'LineString', 'coordinates': ((-1.0, -1.0), (1.0, 1.0))})
        self.assertIsInstance(shape, LineStringAdapter)
        self.assertEqual(tuple(shape.coords), ((-1.0, -1.0), (1.0, 1.0)))

        # polygon
        shape = asShape(
            {'type': 'Polygon',
             'coordinates':
                (((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, -1.0), (0.0, 0.0)),
                 ((0.1, 0.1), (0.1, 0.2), (0.2, 0.2), (0.2, 0.1), (0.1, 0.1)))}
        )
        self.assertIsInstance(shape, PolygonAdapter)
        self.assertEqual(
            tuple(shape.exterior.coords),
            ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, -1.0), (0.0, 0.0)))
        self.assertEqual(len(shape.interiors), 1)

        # multi point
        shape = asShape({'type': 'MultiPoint',
                         'coordinates': ((1.0, 2.0), (3.0, 4.0))})
        self.assertIsInstance(shape, MultiPointAdapter)
        self.assertEqual(len(shape.geoms), 2)

        # multi line string
        shape = asShape({'type': 'MultiLineString',
                         'coordinates': (((0.0, 0.0), (1.0, 2.0)),)})
        self.assertIsInstance(shape, MultiLineStringAdapter)
        self.assertEqual(len(shape.geoms), 1)

        # multi polygon
        shape = asShape(
            {'type': 'MultiPolygon',
             'coordinates':
                [(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)),
                  ((0.1, 0.1), (0.1, 0.2), (0.2, 0.2), (0.2, 0.1), (0.1, 0.1))
                  )]})
        self.assertIsInstance(shape, MultiPolygonAdapter)
        self.assertEqual(len(shape.geoms), 1)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(GeoInterfaceTestCase)

########NEW FILE########
__FILENAME__ = test_geomseq
from . import unittest
from shapely import geometry


class MultiLineTestCase(unittest.TestCase):
    def test_array_interface(self):
        m = geometry.MultiLineString([((0, 0), (1, 1)), ((2, 2), (3, 3))])
        ai = m.geoms[0].__array_interface__
        self.assertEqual(ai['shape'], (2, 2))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(MultiLineTestCase)

########NEW FILE########
__FILENAME__ = test_getitem
from . import unittest
from shapely import geometry


class CoordsGetItemTestCase(unittest.TestCase):

    def test_index_2d_coords(self):
        c = [(float(x), float(-x)) for x in range(4)]
        g = geometry.LineString(c)
        for i in range(-4, 4):
            self.assertTrue(g.coords[i] == c[i])
        self.assertRaises(IndexError, lambda: g.coords[4])
        self.assertRaises(IndexError, lambda: g.coords[-5])

    def test_index_3d_coords(self):
        c = [(float(x), float(-x), float(x*2)) for x in range(4)]
        g = geometry.LineString(c)
        for i in range(-4, 4):
            self.assertTrue(g.coords[i] == c[i])
        self.assertRaises(IndexError, lambda: g.coords[4])
        self.assertRaises(IndexError, lambda: g.coords[-5])

    def test_index_coords_misc(self):
        g = geometry.LineString()  # empty
        self.assertRaises(IndexError, lambda: g.coords[0])
        self.assertRaises(TypeError, lambda: g.coords[0.0])

    def test_slice_2d_coords(self):
        c = [(float(x), float(-x)) for x in range(4)]
        g = geometry.LineString(c)
        self.assertTrue(g.coords[1:] == c[1:])
        self.assertTrue(g.coords[:-1] == c[:-1])
        self.assertTrue(g.coords[::-1] == c[::-1])
        self.assertTrue(g.coords[::2] == c[::2])
        self.assertTrue(g.coords[:4] == c[:4])
        self.assertTrue(g.coords[4:] == c[4:] == [])

    def test_slice_3d_coords(self):
        c = [(float(x), float(-x), float(x*2)) for x in range(4)]
        g = geometry.LineString(c)
        self.assertTrue(g.coords[1:] == c[1:])
        self.assertTrue(g.coords[:-1] == c[:-1])
        self.assertTrue(g.coords[::-1] == c[::-1])
        self.assertTrue(g.coords[::2] == c[::2])
        self.assertTrue(g.coords[:4] == c[:4])
        self.assertTrue(g.coords[4:] == c[4:] == [])


class MultiGeomGetItemTestCase(unittest.TestCase):

    def test_index_multigeom(self):
        c = [(float(x), float(-x)) for x in range(4)]
        g = geometry.MultiPoint(c)
        for i in range(-4, 4):
            self.assertTrue(g[i].equals(geometry.Point(c[i])))
        self.assertRaises(IndexError, lambda: g[4])
        self.assertRaises(IndexError, lambda: g[-5])

    def test_index_multigeom_misc(self):
        g = geometry.MultiLineString()  # empty
        self.assertRaises(IndexError, lambda: g[0])
        self.assertRaises(TypeError, lambda: g[0.0])

    def test_slice_multigeom(self):
        c = [(float(x), float(-x)) for x in range(4)]
        g = geometry.MultiPoint(c)
        self.assertEqual(type(g[:]), type(g))
        self.assertEqual(len(g[:]), len(g))
        self.assertTrue(g[1:].equals(geometry.MultiPoint(c[1:])))
        self.assertTrue(g[:-1].equals(geometry.MultiPoint(c[:-1])))
        self.assertTrue(g[::-1].equals(geometry.MultiPoint(c[::-1])))
        self.assertTrue(g[4:].is_empty)


class LinearRingGetItemTestCase(unittest.TestCase):

    def test_index_linearring(self):
        shell = geometry.polygon.LinearRing([(0.0, 0.0), (70.0, 120.0),
                                             (140.0, 0.0), (0.0, 0.0)])
        holes = [geometry.polygon.LinearRing([(60.0, 80.0), (80.0, 80.0),
                                              (70.0, 60.0), (60.0, 80.0)]),
                 geometry.polygon.LinearRing([(30.0, 10.0), (50.0, 10.0),
                                              (40.0, 30.0), (30.0, 10.0)]),
                 geometry.polygon.LinearRing([(90.0, 10), (110.0, 10.0),
                                              (100.0, 30.0), (90.0, 10.0)])]
        g = geometry.Polygon(shell, holes)
        for i in range(-3, 3):
            self.assertTrue(g.interiors[i].equals(holes[i]))
        self.assertRaises(IndexError, lambda: g.interiors[3])
        self.assertRaises(IndexError, lambda: g.interiors[-4])

    def test_index_linearring_misc(self):
        g = geometry.Polygon()  # empty
        self.assertRaises(IndexError, lambda: g.interiors[0])
        self.assertRaises(TypeError, lambda: g.interiors[0.0])

    def test_slice_linearring(self):
        shell = geometry.polygon.LinearRing([(0.0, 0.0), (70.0, 120.0),
                                             (140.0, 0.0), (0.0, 0.0)])
        holes = [geometry.polygon.LinearRing([(60.0, 80.0), (80.0, 80.0),
                                              (70.0, 60.0), (60.0, 80.0)]),
                 geometry.polygon.LinearRing([(30.0, 10.0), (50.0, 10.0),
                                              (40.0, 30.0), (30.0, 10.0)]),
                 geometry.polygon.LinearRing([(90.0, 10), (110.0, 10.0),
                                              (100.0, 30.0), (90.0, 10.0)])]
        g = geometry.Polygon(shell, holes)
        t = [a.equals(b) for (a, b) in zip(g.interiors[1:], holes[1:])]
        self.assertTrue(all(t))
        t = [a.equals(b) for (a, b) in zip(g.interiors[:-1], holes[:-1])]
        self.assertTrue(all(t))
        t = [a.equals(b) for (a, b) in zip(g.interiors[::-1], holes[::-1])]
        self.assertTrue(all(t))
        t = [a.equals(b) for (a, b) in zip(g.interiors[::2], holes[::2])]
        self.assertTrue(all(t))
        t = [a.equals(b) for (a, b) in zip(g.interiors[:3], holes[:3])]
        self.assertTrue(all(t))
        self.assertTrue(g.interiors[3:] == holes[3:] == [])


def test_suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(CoordsGetItemTestCase),
        loader.loadTestsFromTestCase(MultiGeomGetItemTestCase),
        loader.loadTestsFromTestCase(LinearRingGetItemTestCase)])

########NEW FILE########
__FILENAME__ = test_invalid_geometries
'''Test recovery from operation on invalid geometries
'''

from . import unittest
from shapely.geometry import Polygon
from shapely.topology import TopologicalError


class InvalidGeometriesTestCase(unittest.TestCase):

    def test_invalid_intersection(self):
        # Make a self-intersecting polygon
        polygon_invalid = Polygon(((0, 0), (1, 1), (1, -1), (0, 1), (0, 0)))
        self.assertFalse(polygon_invalid.is_valid)

        # Intersect with a valid polygon
        polygon = Polygon(((-.5, -.5), (-.5, .5), (.5, .5), (.5, -5)))
        self.assertTrue(polygon.is_valid)
        self.assertTrue(polygon_invalid.intersects(polygon))
        self.assertRaises(TopologicalError,
                          polygon_invalid.intersection, polygon)
        self.assertRaises(TopologicalError,
                          polygon.intersection, polygon_invalid)
        return


def test_suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(InvalidGeometriesTestCase)])

########NEW FILE########
__FILENAME__ = test_iterops
"""Test operator iterations
"""
from . import unittest
from shapely import iterops
from shapely.geometry import Point, Polygon


class IterOpsTestCase(unittest.TestCase):

    def test_iterops(self):

        coords = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))
        polygon = Polygon(coords)
        points = [Point(0.5, 0.5), Point(2.0, 2.0)]

        # List of the points contained by the polygon
        self.assertTrue(
            all([isinstance(x, Point)
                 for x in iterops.contains(polygon, points, True)]))

        # 'True' is the default value
        self.assertTrue(
            all([isinstance(x, Point)
                 for x in iterops.contains(polygon, points)]))

        # Test a false value
        self.assertTrue(
            all([isinstance(x, Point)
                 for x in iterops.contains(polygon, points, False)]))

        # If the provided iterator yields tuples, the second value will be
        # yielded
        self.assertEqual(
            list(iterops.contains(polygon, [(p, p.coords[:])
                 for p in points], False)),
            [[(2.0, 2.0)]])

        # Just to demonstrate that the important thing is that the second
        # parameter is an iterator:
        self.assertEqual(
            list(iterops.contains(polygon, iter((p, p.coords[:])
                 for p in points))),
            [[(0.5, 0.5)]])


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(IterOpsTestCase)

########NEW FILE########
__FILENAME__ = test_linear_referencing
from . import unittest
from shapely.geos import geos_version
from shapely.geometry import Point, LineString, MultiLineString


class LinearReferencingTestCase(unittest.TestCase):

    def setUp(self):
        self.point = Point(1, 1)
        self.line1 = LineString(([0, 0], [2, 0]))
        self.line2 = LineString(([3, 0], [3, 6]))
        self.multiline = MultiLineString([
            list(self.line1.coords), list(self.line2.coords)
        ])

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_line1_project(self):
        self.assertEqual(self.line1.project(self.point), 1.0)
        self.assertEqual(self.line1.project(self.point, normalized=True), 0.5)

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_line2_project(self):
        self.assertEqual(self.line2.project(self.point), 1.0)
        self.assertAlmostEqual(
            self.line2.project(self.point, normalized=True), 0.16666666666, 8)

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_multiline_project(self):
        self.assertEqual(self.multiline.project(self.point), 1.0)
        self.assertEqual(
            self.multiline.project(self.point, normalized=True), 0.125)

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_not_supported_project(self):
        with self.assertRaises(TypeError):
            self.point.buffer(1.0).project(self.point)

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_not_on_line_project(self):
        # Points that aren't on the line project to 0.
        self.assertEqual(self.line1.project(Point(-10, -10)), 0.0)

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_line1_interpolate(self):
        self.assertTrue(self.line1.interpolate(0.5).equals(Point(0.5, 0.0)))
        self.assertTrue(
            self.line1.interpolate(0.5, normalized=True).equals(Point(1, 0)))

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_line2_interpolate(self):
        self.assertTrue(self.line2.interpolate(0.5).equals(Point(3.0, 0.5)))
        self.assertTrue(
            self.line2.interpolate(0.5, normalized=True).equals(Point(3, 3)))

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_multiline_interpolate(self):
        self.assertTrue(self.multiline.interpolate(0.5).equals(Point(0.5, 0)))
        self.assertTrue(
            self.multiline.interpolate(0.5, normalized=True).equals(
                Point(3.0, 2.0)))

    @unittest.skipIf(geos_version < (3, 2, 0), 'GEOS 3.2.0 required')
    def test_line_ends_interpolate(self):
        # Distances greater than length of the line or less than
        # zero yield the line's ends.
        self.assertTrue(self.line1.interpolate(-1000).equals(Point(0.0, 0.0)))
        self.assertTrue(self.line1.interpolate(1000).equals(Point(2.0, 0.0)))


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(LinearReferencingTestCase)

########NEW FILE########
__FILENAME__ = test_linemerge
from . import unittest
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge


class LineMergeTestCase(unittest.TestCase):

    def test_linemerge(self):

        lines = MultiLineString(
            [((0, 0), (1, 1)),
             ((2, 0), (2, 1), (1, 1))])
        result = linemerge(lines)
        self.assertIsInstance(result, LineString)
        self.assertFalse(result.is_ring)
        self.assertEqual(len(result.coords), 4)
        self.assertEqual(result.coords[0], (0.0, 0.0))
        self.assertEqual(result.coords[3], (2.0, 0.0))

        lines2 = MultiLineString(
            [((0, 0), (1, 1)),
             ((0, 0), (2, 0), (2, 1), (1, 1))])
        result = linemerge(lines2)
        self.assertTrue(result.is_ring)
        self.assertEqual(len(result.coords), 5)

        lines3 = [
            LineString(((0, 0), (1, 1))),
            LineString(((0, 0), (0, 1))),
        ]
        result = linemerge(lines3)
        self.assertFalse(result.is_ring)
        self.assertEqual(len(result.coords), 3)
        self.assertEqual(result.coords[0], (0.0, 1.0))
        self.assertEqual(result.coords[2], (1.0, 1.0))

        lines4 = [
            ((0, 0), (1, 1)),
            ((0, 0), (0, 1)),
        ]
        self.assertTrue(result.equals(linemerge(lines4)))

        lines5 = [
            ((0, 0), (1, 1)),
            ((1, 0), (0, 1)),
        ]
        result = linemerge(lines5)
        self.assertEqual(result.type, 'MultiLineString')


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(LineMergeTestCase)

########NEW FILE########
__FILENAME__ = test_linestring
from . import unittest, numpy
from shapely.geometry import LineString, asLineString, Point


class LineStringTestCase(unittest.TestCase):

    def test_linestring(self):

        # From coordinate tuples
        line = LineString(((1.0, 2.0), (3.0, 4.0)))
        self.assertEqual(len(line.coords), 2)
        self.assertEqual(line.coords[:], [(1.0, 2.0), (3.0, 4.0)])

        # From Points
        line2 = LineString((Point(1.0, 2.0), Point(3.0, 4.0)))
        self.assertEqual(len(line2.coords), 2)
        self.assertEqual(line2.coords[:], [(1.0, 2.0), (3.0, 4.0)])

        # From mix of tuples and Points
        line3 = LineString((Point(1.0, 2.0), (2.0, 3.0), Point(3.0, 4.0)))
        self.assertEqual(len(line3.coords), 3)
        self.assertEqual(line3.coords[:], [(1.0, 2.0), (2.0, 3.0), (3.0, 4.0)])

        # From lines
        copy = LineString(line)
        self.assertEqual(len(copy.coords), 2)
        self.assertEqual(copy.coords[:], [(1.0, 2.0), (3.0, 4.0)])

        # Bounds
        self.assertEqual(line.bounds, (1.0, 2.0, 3.0, 4.0))

        # Coordinate access
        self.assertEqual(tuple(line.coords), ((1.0, 2.0), (3.0, 4.0)))
        self.assertEqual(line.coords[0], (1.0, 2.0))
        self.assertEqual(line.coords[1], (3.0, 4.0))
        with self.assertRaises(IndexError):
            line.coords[2]  # index out of range

        # Geo interface
        self.assertEqual(line.__geo_interface__,
                         {'type': 'LineString',
                          'coordinates': ((1.0, 2.0), (3.0, 4.0))})

        # Coordinate modification
        line.coords = ((-1.0, -1.0), (1.0, 1.0))
        self.assertEqual(line.__geo_interface__,
                         {'type': 'LineString',
                          'coordinates': ((-1.0, -1.0), (1.0, 1.0))})

        # Adapt a coordinate list to a line string
        coords = [[5.0, 6.0], [7.0, 8.0]]
        la = asLineString(coords)
        self.assertEqual(la.coords[:], [(5.0, 6.0), (7.0, 8.0)])

        # Test Non-operability of Null geometry
        l_null = LineString()
        self.assertEqual(l_null.wkt, 'GEOMETRYCOLLECTION EMPTY')
        self.assertEqual(l_null.length, 0.0)

        # Check that we can set coordinates of a null geometry
        l_null.coords = [(0, 0), (1, 1)]
        self.assertAlmostEqual(l_null.length, 1.4142135623730951)

    @unittest.skipIf(not numpy, 'Numpy required')
    def test_numpy(self):

        from numpy import array, asarray
        from numpy.testing import assert_array_equal

        # Construct from a numpy array
        line = LineString(array([[0.0, 0.0], [1.0, 2.0]]))
        self.assertEqual(len(line.coords), 2)
        self.assertEqual(line.coords[:], [(0.0, 0.0), (1.0, 2.0)])

        line = LineString(((1.0, 2.0), (3.0, 4.0)))
        la = asarray(line)
        expected = array([[1.0, 2.0], [3.0, 4.0]])
        assert_array_equal(la, expected)

        # Coordinate sequences can be adapted as well
        la = asarray(line.coords)
        assert_array_equal(la, expected)

        # Adapt a Numpy array to a line string
        a = array([[1.0, 2.0], [3.0, 4.0]])
        la = asLineString(a)
        assert_array_equal(la.context, a)
        self.assertEqual(la.coords[:], [(1.0, 2.0), (3.0, 4.0)])

        # Now, the inverse
        self.assertEqual(la.__array_interface__,
                         la.context.__array_interface__)

        pas = asarray(la)
        assert_array_equal(pas, array([[1.0, 2.0], [3.0, 4.0]]))

        # From Array.txt
        a = asarray([[0.0, 0.0], [2.0, 2.0], [1.0, 1.0]])
        line = LineString(a)
        self.assertEqual(line.coords[:], [(0.0, 0.0), (2.0, 2.0), (1.0, 1.0)])

        data = line.ctypes
        self.assertEqual(data[0], 0.0)
        self.assertEqual(data[5], 1.0)

        b = asarray(line)
        assert_array_equal(b, array([[0., 0.], [2., 2.], [1., 1.]]))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(LineStringTestCase)

########NEW FILE########
__FILENAME__ = test_locale
'''Test locale independence of WKT
'''
from . import unittest
import sys
import locale
from shapely.wkt import loads, dumps

# Set locale to one that uses a comma as decimal seperator
# TODO: try a few other common locales
if sys.platform == 'win32':
    test_locales = {
        'Portuguese': 'portuguese_brazil',
    }
else:
    test_locales = {
        'Portuguese': 'pt_BR.UTF-8',
    }

do_test_locale = False


def setUpModule():
    global do_test_locale
    for name in test_locales:
        try:
            test_locale = test_locales[name]
            locale.setlocale(locale.LC_ALL, test_locale)
            do_test_locale = True
            break
        except:
            pass
    if not do_test_locale:
        raise unittest.SkipTest('test locale not found')


def tearDownModule():
    locale.resetlocale()


class LocaleTestCase(unittest.TestCase):

    #@unittest.skipIf(not do_test_locale, 'test locale not found')

    def test_wkt_locale(self):

        # Test reading and writing
        p = loads('POINT (0.0 0.0)')
        self.assertEqual(p.x, 0.0)
        self.assertEqual(p.y, 0.0)
        wkt = dumps(p)
        self.assertTrue(wkt.startswith('POINT'))
        self.assertFalse(',' in wkt)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(LocaleTestCase)

########NEW FILE########
__FILENAME__ = test_mapping
from . import unittest
from shapely.geometry import Point, mapping


class MappingTestCase(unittest.TestCase):
    def test_point(self):
        m = mapping(Point(0, 0))
        self.assertEqual(m['type'], 'Point')
        self.assertEqual(m['coordinates'], (0.0, 0.0))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(MappingTestCase)

########NEW FILE########
__FILENAME__ = test_multilinestring
from . import unittest, numpy
from shapely.geometry import LineString, MultiLineString, asMultiLineString
from shapely.geometry.base import dump_coords


class MultiLineStringTestCase(unittest.TestCase):

    def test_multipoint(self):

        # From coordinate tuples
        geom = MultiLineString((((1.0, 2.0), (3.0, 4.0)),))
        self.assertIsInstance(geom, MultiLineString)
        self.assertEqual(len(geom.geoms), 1)
        self.assertEqual(dump_coords(geom), [[(1.0, 2.0), (3.0, 4.0)]])

        # From lines
        a = LineString(((1.0, 2.0), (3.0, 4.0)))
        ml = MultiLineString([a])
        self.assertEqual(len(ml.geoms), 1)
        self.assertEqual(dump_coords(ml), [[(1.0, 2.0), (3.0, 4.0)]])

        # From another multi-line
        ml2 = MultiLineString(ml)
        self.assertEqual(len(ml2.geoms), 1)
        self.assertEqual(dump_coords(ml2), [[(1.0, 2.0), (3.0, 4.0)]])

        # Sub-geometry Access
        geom = MultiLineString([(((0.0, 0.0), (1.0, 2.0)))])
        self.assertIsInstance(geom[0], LineString)
        self.assertEqual(dump_coords(geom[0]), [(0.0, 0.0), (1.0, 2.0)])
        with self.assertRaises(IndexError):  # index out of range
            geom.geoms[1]

        # Geo interface
        self.assertEqual(geom.__geo_interface__,
                         {'type': 'MultiLineString',
                          'coordinates': (((0.0, 0.0), (1.0, 2.0)),)})

    @unittest.skipIf(not numpy, 'Numpy required')
    def test_numpy(self):

        from numpy import array
        from numpy.testing import assert_array_equal

        # Construct from a numpy array
        geom = MultiLineString([array(((0.0, 0.0), (1.0, 2.0)))])
        self.assertIsInstance(geom, MultiLineString)
        self.assertEqual(len(geom.geoms), 1)
        self.assertEqual(dump_coords(geom), [[(0.0, 0.0), (1.0, 2.0)]])

        # Adapt a sequence of Numpy arrays to a multilinestring
        a = [array(((1.0, 2.0), (3.0, 4.0)))]
        geoma = asMultiLineString(a)
        assert_array_equal(geoma.context, [array([[1., 2.], [3., 4.]])])
        self.assertEqual(dump_coords(geoma), [[(1.0, 2.0), (3.0, 4.0)]])

        # TODO: is there an inverse?


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(MultiLineStringTestCase)

########NEW FILE########
__FILENAME__ = test_multipoint
from . import unittest, numpy
from shapely.geometry import Point, MultiPoint, asMultiPoint
from shapely.geometry.base import dump_coords


class MultiPointTestCase(unittest.TestCase):

    def test_multipoint(self):

        # From coordinate tuples
        geom = MultiPoint(((1.0, 2.0), (3.0, 4.0)))
        self.assertEqual(len(geom.geoms), 2)
        self.assertEqual(dump_coords(geom), [[(1.0, 2.0)], [(3.0, 4.0)]])

        # From points
        geom = MultiPoint((Point(1.0, 2.0), Point(3.0, 4.0)))
        self.assertEqual(len(geom.geoms), 2)
        self.assertEqual(dump_coords(geom), [[(1.0, 2.0)], [(3.0, 4.0)]])

        # From another multi-point
        geom2 = MultiPoint(geom)
        self.assertEqual(len(geom2.geoms), 2)
        self.assertEqual(dump_coords(geom2), [[(1.0, 2.0)], [(3.0, 4.0)]])

        # Sub-geometry Access
        self.assertIsInstance(geom.geoms[0], Point)
        self.assertEqual(geom.geoms[0].x, 1.0)
        self.assertEqual(geom.geoms[0].y, 2.0)
        with self.assertRaises(IndexError):  # index out of range
            geom.geoms[2]

        # Geo interface
        self.assertEqual(geom.__geo_interface__,
                         {'type': 'MultiPoint',
                          'coordinates': ((1.0, 2.0), (3.0, 4.0))})

        # Adapt a coordinate list to a line string
        coords = [[5.0, 6.0], [7.0, 8.0]]
        geoma = asMultiPoint(coords)
        self.assertEqual(dump_coords(geoma), [[(5.0, 6.0)], [(7.0, 8.0)]])

    @unittest.skipIf(not numpy, 'Numpy required')
    def test_numpy(self):

        from numpy import array, asarray
        from numpy.testing import assert_array_equal

        # Construct from a numpy array
        geom = MultiPoint(array([[0.0, 0.0], [1.0, 2.0]]))
        self.assertIsInstance(geom, MultiPoint)
        self.assertEqual(len(geom.geoms), 2)
        self.assertEqual(dump_coords(geom), [[(0.0, 0.0)], [(1.0, 2.0)]])

        # Geo interface (cont.)
        geom = MultiPoint((Point(1.0, 2.0), Point(3.0, 4.0)))
        assert_array_equal(array(geom), array([[1., 2.], [3., 4.]]))

        # Adapt a Numpy array to a multipoint
        a = array([[1.0, 2.0], [3.0, 4.0]])
        geoma = asMultiPoint(a)
        assert_array_equal(geoma.context, array([[1., 2.], [3., 4.]]))
        self.assertEqual(dump_coords(geoma), [[(1.0, 2.0)], [(3.0, 4.0)]])

        # Now, the inverse
        self.assertEqual(geoma.__array_interface__,
                         geoma.context.__array_interface__)

        pas = asarray(geoma)
        assert_array_equal(pas, array([[1., 2.], [3., 4.]]))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(MultiPointTestCase)

########NEW FILE########
__FILENAME__ = test_multipolygon
from . import unittest
from shapely.geometry import Polygon, MultiPolygon, asMultiPolygon
from shapely.geometry.base import dump_coords


class MultiPolygonTestCase(unittest.TestCase):

    def test_multipolygon(self):

        # From coordinate tuples
        geom = MultiPolygon(
            [(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)),
              [((0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25))])])
        self.assertIsInstance(geom, MultiPolygon)
        self.assertEqual(len(geom.geoms), 1)
        self.assertEqual(
            dump_coords(geom),
            [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0),
              [(0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25),
               (0.25, 0.25)]]])

        # Or from polygons
        p = Polygon(((0, 0), (0, 1), (1, 1), (1, 0)),
                    [((0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25))])
        geom = MultiPolygon([p])
        self.assertEqual(len(geom.geoms), 1)
        self.assertEqual(
            dump_coords(geom),
            [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0),
              [(0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25),
               (0.25, 0.25)]]])

        # Or from another multi-polygon
        geom2 = MultiPolygon(geom)
        self.assertEqual(len(geom2.geoms), 1)
        self.assertEqual(
            dump_coords(geom2),
            [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0),
              [(0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25),
               (0.25, 0.25)]]])

        # Sub-geometry Access
        self.assertIsInstance(geom.geoms[0], Polygon)
        self.assertEqual(
            dump_coords(geom.geoms[0]),
            [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0),
             [(0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25),
              (0.25, 0.25)]])
        with self.assertRaises(IndexError):  # index out of range
            geom.geoms[1]

        # Geo interface
        self.assertEqual(
            geom.__geo_interface__,
            {'type': 'MultiPolygon',
             'coordinates': [(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0),
                               (1.0, 0.0), (0.0, 0.0)),
                              ((0.25, 0.25), (0.25, 0.5), (0.5, 0.5),
                               (0.5, 0.25), (0.25, 0.25)))]})

        # Adapter
        coords = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
        holes_coords = [((0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25))]
        mpa = asMultiPolygon([(coords, holes_coords)])
        self.assertEqual(len(mpa.geoms), 1)
        self.assertEqual(len(mpa.geoms[0].exterior.coords), 5)
        self.assertEqual(len(mpa.geoms[0].interiors), 1)
        self.assertEqual(len(mpa.geoms[0].interiors[0].coords), 5)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(MultiPolygonTestCase)

########NEW FILE########
__FILENAME__ = test_ndarrays
# Tests of support for Numpy ndarrays. See
# https://github.com/sgillies/shapely/issues/26 for discussion.
# Requires numpy.

import sys

if sys.version_info[0] >= 3:
    from functools import reduce

from . import unittest
from shapely import geometry

try:
    import numpy
except ImportError:
    numpy = False


class TransposeTestCase(unittest.TestCase):

    @unittest.skipIf(not numpy, 'numpy not installed')
    def test_multipoint(self):
        a = numpy.array([[1.0, 1.0, 2.0, 2.0, 1.0], [3.0, 4.0, 4.0, 3.0, 3.0]])
        t = a.T
        s = geometry.asMultiPoint(t)
        coords = reduce(lambda x, y: x + y, [list(g.coords) for g in s])
        self.assertEqual(
            coords,
            [(1.0, 3.0), (1.0, 4.0), (2.0, 4.0), (2.0, 3.0), (1.0, 3.0)]
        )

    @unittest.skipIf(not numpy, 'numpy not installed')
    def test_linestring(self):
        a = numpy.array([[1.0, 1.0, 2.0, 2.0, 1.0], [3.0, 4.0, 4.0, 3.0, 3.0]])
        t = a.T
        s = geometry.asLineString(t)
        self.assertEqual(
            list(s.coords),
            [(1.0, 3.0), (1.0, 4.0), (2.0, 4.0), (2.0, 3.0), (1.0, 3.0)]
        )

    @unittest.skipIf(not numpy, 'numpy not installed')
    def test_polygon(self):
        a = numpy.array([[1.0, 1.0, 2.0, 2.0, 1.0], [3.0, 4.0, 4.0, 3.0, 3.0]])
        t = a.T
        s = geometry.asPolygon(t)
        self.assertEqual(
            list(s.exterior.coords),
            [(1.0, 3.0), (1.0, 4.0), (2.0, 4.0), (2.0, 3.0), (1.0, 3.0)]
        )


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TransposeTestCase)

########NEW FILE########
__FILENAME__ = test_operations
from . import unittest
from shapely.geometry import Point, Polygon, MultiPoint, GeometryCollection
from shapely.wkt import loads


class OperationsTestCase(unittest.TestCase):

    def test_operations(self):
        point = Point(0.0, 0.0)

        # General geometry
        self.assertEqual(point.area, 0.0)
        self.assertEqual(point.length, 0.0)
        self.assertAlmostEqual(point.distance(Point(-1.0, -1.0)),
                               1.4142135623730951)

        # Topology operations

        # Envelope
        self.assertIsInstance(point.envelope, Point)

        # Intersection
        self.assertIsInstance(point.intersection(Point(-1, -1)),
                              GeometryCollection)

        # Buffer
        self.assertIsInstance(point.buffer(10.0), Polygon)
        self.assertIsInstance(point.buffer(10.0, 32), Polygon)

        # Simplify
        p = loads('POLYGON ((120 120, 121 121, 122 122, 220 120, 180 199, '
                  '160 200, 140 199, 120 120))')
        expected = loads('POLYGON ((120 120, 140 199, 160 200, 180 199, '
                         '220 120, 120 120))')
        s = p.simplify(10.0, preserve_topology=False)
        self.assertTrue(s.equals_exact(expected, 0.001))

        p = loads('POLYGON ((80 200, 240 200, 240 60, 80 60, 80 200),'
                  '(120 120, 220 120, 180 199, 160 200, 140 199, 120 120))')
        expected = loads(
            'POLYGON ((80 200, 240 200, 240 60, 80 60, 80 200),'
            '(120 120, 220 120, 180 199, 160 200, 140 199, 120 120))')
        s = p.simplify(10.0, preserve_topology=True)
        self.assertTrue(s.equals_exact(expected, 0.001))

        # Convex Hull
        self.assertIsInstance(point.convex_hull, Point)

        # Differences
        self.assertIsInstance(point.difference(Point(-1, 1)), Point)

        self.assertIsInstance(point.symmetric_difference(Point(-1, 1)),
                              MultiPoint)

        # Boundary
        self.assertIsInstance(point.boundary, GeometryCollection)

        # Union
        self.assertIsInstance(point.union(Point(-1, 1)), MultiPoint)

        self.assertIsInstance(point.representative_point(), Point)

        self.assertIsInstance(point.centroid, Point)

        # Relate
        self.assertEqual(point.relate(Point(-1, -1)), 'FF0FFF0F2')


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(OperationsTestCase)

########NEW FILE########
__FILENAME__ = test_operators
from . import unittest
from shapely.geometry import Point


class OperatorsTestCase(unittest.TestCase):

    def test_point(self):
        point = Point(0, 0)
        point2 = Point(-1, 1)
        self.assertTrue(point.union(point2).equals(point | point2))
        self.assertTrue((point & point2).is_empty)
        self.assertTrue(point.equals(point - point2))
        self.assertTrue(
            point.symmetric_difference(point2).equals(point ^ point2))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(OperatorsTestCase)

########NEW FILE########
__FILENAME__ = test_persist
"""Persistence tests
"""
from . import unittest
import pickle
from shapely import wkb, wkt
from shapely.geometry import Point


class PersistTestCase(unittest.TestCase):

    def test_pickle(self):

        p = Point(0.0, 0.0)
        data = pickle.dumps(p)
        q = pickle.loads(data)
        self.assertTrue(q.equals(p))

    def test_wkb(self):

        p = Point(0.0, 0.0)
        bytes = wkb.dumps(p)
        pb = wkb.loads(bytes)
        self.assertTrue(pb.equals(p))

    def test_wkt(self):
        p = Point(0.0, 0.0)
        text = wkt.dumps(p)
        self.assertTrue(text.startswith('POINT'))
        pt = wkt.loads(text)
        self.assertTrue(pt.equals(p))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PersistTestCase)

########NEW FILE########
__FILENAME__ = test_pickle
from . import unittest
from shapely import geometry

import sys
if sys.version_info[0] >= 3:
    from pickle import dumps, loads, HIGHEST_PROTOCOL
else:
    from cPickle import dumps, loads, HIGHEST_PROTOCOL


class TwoDeeTestCase(unittest.TestCase):

    def test_linestring(self):
        l = geometry.LineString(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0)))
        self.assertEqual(l._ndim, 2)
        s = dumps(l, HIGHEST_PROTOCOL)
        t = loads(s)
        self.assertEqual(t._ndim, 2)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TwoDeeTestCase)

########NEW FILE########
__FILENAME__ = test_point
from . import unittest, numpy
from shapely.geometry import Point, asPoint
from shapely.geos import DimensionError


class LineStringTestCase(unittest.TestCase):

    def test_point(self):

        # Test 2D points
        p = Point(1.0, 2.0)
        self.assertEqual(p.x, 1.0)
        self.assertEqual(p.y, 2.0)
        self.assertEqual(p.coords[:], [(1.0, 2.0)])
        self.assertEqual(str(p), p.wkt)
        self.assertFalse(p.has_z)
        with self.assertRaises(DimensionError):
            p.z

        # Check 3D
        p = Point(1.0, 2.0, 3.0)
        self.assertEqual(p.coords[:], [(1.0, 2.0, 3.0)])
        self.assertEqual(str(p), p.wkt)
        self.assertTrue(p.has_z)
        self.assertEqual(p.z, 3.0)

        # From coordinate sequence
        p = Point((3.0, 4.0))
        self.assertEqual(p.coords[:], [(3.0, 4.0)])

        # From another point
        q = Point(p)
        self.assertEqual(q.coords[:], [(3.0, 4.0)])

        # Coordinate access
        self.assertEqual(p.x, 3.0)
        self.assertEqual(p.y, 4.0)
        self.assertEqual(tuple(p.coords), ((3.0, 4.0),))
        self.assertEqual(p.coords[0], (3.0, 4.0))
        with self.assertRaises(IndexError):  # index out of range
            p.coords[1]

        # Bounds
        self.assertEqual(p.bounds, (3.0, 4.0, 3.0, 4.0))

        # Geo interface
        self.assertEqual(p.__geo_interface__,
                         {'type': 'Point', 'coordinates': (3.0, 4.0)})

        # Modify coordinates
        p.coords = (2.0, 1.0)
        self.assertEqual(p.__geo_interface__,
                         {'type': 'Point', 'coordinates': (2.0, 1.0)})

        # Alternate method
        p.coords = ((0.0, 0.0),)
        self.assertEqual(p.__geo_interface__,
                         {'type': 'Point', 'coordinates': (0.0, 0.0)})

        # Adapt a coordinate list to a point
        coords = [3.0, 4.0]
        pa = asPoint(coords)
        self.assertEqual(pa.coords[0], (3.0, 4.0))
        self.assertEqual(pa.distance(p), 5.0)

        # Move the coordinates and watch the distance change
        coords[0] = 1.0
        self.assertEqual(pa.coords[0], (1.0, 4.0))
        self.assertAlmostEqual(pa.distance(p), 4.123105625617661)

        # Test Non-operability of Null geometry
        p_null = Point()
        self.assertEqual(p_null.wkt, 'GEOMETRYCOLLECTION EMPTY')
        self.assertEqual(p_null.coords[:], [])
        self.assertEqual(p_null.area, 0.0)

        # Check that we can set coordinates of a null geometry
        p_null.coords = (1, 2)
        self.assertEqual(p_null.coords[:], [(1.0, 2.0)])

    @unittest.skipIf(not numpy, 'Numpy required')
    def test_numpy(self):

        from numpy import array, asarray
        from numpy.testing import assert_array_equal

        # Construct from a numpy array
        p = Point(array([1.0, 2.0]))
        self.assertEqual(p.coords[:], [(1.0, 2.0)])

        # Adapt a Numpy array to a point
        a = array([1.0, 2.0])
        pa = asPoint(a)
        assert_array_equal(pa.context, array([1.0, 2.0]))
        self.assertEqual(pa.coords[:], [(1.0, 2.0)])

        # Now, the inverse
        self.assertEqual(pa.__array_interface__,
                         pa.context.__array_interface__)

        pas = asarray(pa)
        assert_array_equal(pas, array([1.0, 2.0]))

        # Adapt a coordinate list to a point
        coords = [3.0, 4.0]
        pa = asPoint(coords)
        coords[0] = 1.0

        # Now, the inverse (again?)
        self.assertIsNotNone(pa.__array_interface__)
        pas = asarray(pa)
        assert_array_equal(pas, array([1.0, 4.0]))

        # From Array.txt
        p = Point(0.0, 0.0, 1.0)
        coords = p.coords[0]
        self.assertEqual(coords, (0.0, 0.0, 1.0))
        self.assertIsNotNone(p.ctypes)

        # Convert to Numpy array, passing through Python sequence
        a = asarray(coords)
        self.assertEqual(a.ndim, 1)
        self.assertEqual(a.size, 3)
        self.assertEqual(a.shape, (3,))

        # Convert to Numpy array, passing through a ctypes array
        b = asarray(p)
        self.assertEqual(b.size, 3)
        self.assertEqual(b.shape, (3,))
        assert_array_equal(b, array([0.0, 0.0, 1.0]))

        # Make a point from a Numpy array
        a = asarray([1.0, 1.0, 0.0])
        p = Point(*list(a))
        self.assertEqual(p.coords[:], [(1.0, 1.0, 0.0)])


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(LineStringTestCase)

########NEW FILE########
__FILENAME__ = test_polygon
"""Polygons and Linear Rings
"""
from . import unittest, numpy
from shapely.wkb import loads as load_wkb
from shapely.geometry import Point, Polygon, asPolygon
from shapely.geometry.polygon import LinearRing, asLinearRing
from shapely.geometry.base import dump_coords


class PolygonTestCase(unittest.TestCase):

    def test_polygon(self):

        # Initialization
        # Linear rings won't usually be created by users, but by polygons
        coords = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
        ring = LinearRing(coords)
        self.assertEqual(len(ring.coords), 5)
        self.assertEqual(ring.coords[0], ring.coords[4])
        self.assertEqual(ring.coords[0], ring.coords[-1])
        self.assertTrue(ring.is_ring)

        # Coordinate modification
        ring.coords = ((0.0, 0.0), (0.0, 2.0), (2.0, 2.0), (2.0, 0.0))
        self.assertEqual(
            ring.__geo_interface__,
            {'type': 'LinearRing',
             'coordinates': ((0.0, 0.0), (0.0, 2.0), (2.0, 2.0), (2.0, 0.0),
                             (0.0, 0.0))})

        # Test ring adapter
        coords = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]]
        ra = asLinearRing(coords)
        self.assertTrue(ra.wkt.upper().startswith('LINEARRING'))
        self.assertEqual(dump_coords(ra),
                         [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0),
                          (0.0, 0.0)])
        coords[3] = [2.0, -1.0]
        self.assertEqual(dump_coords(ra),
                         [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, -1.0),
                          (0.0, 0.0)])

        # Construct a polygon, exterior ring only
        polygon = Polygon(coords)
        self.assertEqual(len(polygon.exterior.coords), 5)

        # Ring Access
        self.assertIsInstance(polygon.exterior, LinearRing)
        ring = polygon.exterior
        self.assertEqual(len(ring.coords), 5)
        self.assertEqual(ring.coords[0], ring.coords[4])
        self.assertEqual(ring.coords[0], (0., 0.))
        self.assertTrue(ring.is_ring)
        self.assertEqual(len(polygon.interiors), 0)

        # Create a new polygon from WKB
        data = polygon.wkb
        polygon = None
        ring = None
        polygon = load_wkb(data)
        ring = polygon.exterior
        self.assertEqual(len(ring.coords), 5)
        self.assertEqual(ring.coords[0], ring.coords[4])
        self.assertEqual(ring.coords[0], (0., 0.))
        self.assertTrue(ring.is_ring)
        polygon = None

        # Interior rings (holes)
        polygon = Polygon(coords, [((0.25, 0.25), (0.25, 0.5),
                                    (0.5, 0.5), (0.5, 0.25))])
        self.assertEqual(len(polygon.exterior.coords), 5)
        self.assertEqual(len(polygon.interiors[0].coords), 5)
        with self.assertRaises(IndexError):  # index out of range
            polygon.interiors[1]

        # Coordinate getters and setters raise exceptions
        self.assertRaises(NotImplementedError, polygon._get_coords)
        with self.assertRaises(NotImplementedError):
            polygon.coords

        # Geo interface
        self.assertEqual(
            polygon.__geo_interface__,
            {'type': 'Polygon',
             'coordinates': (((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, -1.0),
                             (0.0, 0.0)), ((0.25, 0.25), (0.25, 0.5),
                             (0.5, 0.5), (0.5, 0.25), (0.25, 0.25)))})

        # Adapter
        hole_coords = [((0.25, 0.25), (0.25, 0.5), (0.5, 0.5), (0.5, 0.25))]
        pa = asPolygon(coords, hole_coords)
        self.assertEqual(len(pa.exterior.coords), 5)
        self.assertEqual(len(pa.interiors), 1)
        self.assertEqual(len(pa.interiors[0].coords), 5)

        # Test Non-operability of Null rings
        r_null = LinearRing()
        self.assertEqual(r_null.wkt, 'GEOMETRYCOLLECTION EMPTY')
        self.assertEqual(r_null.length, 0.0)

        # Check that we can set coordinates of a null geometry
        r_null.coords = [(0, 0), (1, 1), (1, 0)]
        self.assertAlmostEqual(r_null.length, 3.414213562373095)

        # Error handling
        with self.assertRaises(ValueError):
            # A LinearRing must have at least 3 coordinate tuples
            Polygon([[1, 2], [2, 3]])

    @unittest.skipIf(not numpy, 'Numpy required')
    def test_numpy(self):

        from numpy import array, asarray
        from numpy.testing import assert_array_equal

        a = asarray(((0., 0.), (0., 1.), (1., 1.), (1., 0.), (0., 0.)))
        polygon = Polygon(a)
        self.assertEqual(len(polygon.exterior.coords), 5)
        self.assertEqual(dump_coords(polygon.exterior),
                         [(0., 0.), (0., 1.), (1., 1.), (1., 0.), (0., 0.)])
        self.assertEqual(len(polygon.interiors), 0)
        b = asarray(polygon.exterior)
        self.assertEqual(b.shape, (5, 2))
        assert_array_equal(
            b, array([(0., 0.), (0., 1.), (1., 1.), (1., 0.), (0., 0.)]))

    def test_dimensions(self):

        # Background: see http://trac.gispython.org/lab/ticket/168
    # http://lists.gispython.org/pipermail/community/2008-August/001859.html

        coords = ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0),
                  (1.0, 0.0, 0.0))
        polygon = Polygon(coords)
        self.assertEqual(polygon._ndim, 3)
        gi = polygon.__geo_interface__
        self.assertEqual(
            gi['coordinates'],
            (((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0),
              (1.0, 0.0, 0.0), (0.0, 0.0, 0.0)),))

        e = polygon.exterior
        self.assertEqual(e._ndim, 3)
        gi = e.__geo_interface__
        self.assertEqual(
            gi['coordinates'],
            ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0),
             (1.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_attribute_chains(self):

        # Attribute Chaining
        # See also ticket #151.
        p = Polygon(((0.0, 0.0), (0.0, 1.0), (-1.0, 1.0), (-1.0, 0.0)))
        self.assertEqual(
            list(p.boundary.coords),
            [(0.0, 0.0), (0.0, 1.0), (-1.0, 1.0), (-1.0, 0.0), (0.0, 0.0)])

        ec = list(Point(0.0, 0.0).buffer(1.0, 1).exterior.coords)
        self.assertIsInstance(ec, list)  # TODO: this is a poor test

        # Test chained access to interiors
        p = Polygon(
            ((0.0, 0.0), (0.0, 1.0), (-1.0, 1.0), (-1.0, 0.0)),
            [((-0.25, 0.25), (-0.25, 0.75), (-0.75, 0.75), (-0.75, 0.25))]
        )
        self.assertEqual(p.area, 0.75)

        """Not so much testing the exact values here, which are the
        responsibility of the geometry engine (GEOS), but that we can get
        chain functions and properties using anonymous references.
        """
        self.assertEqual(
            list(p.interiors[0].coords),
            [(-0.25, 0.25), (-0.25, 0.75), (-0.75, 0.75), (-0.75, 0.25),
             (-0.25, 0.25)])
        xy = list(p.interiors[0].buffer(1).exterior.coords)[0]
        self.assertEqual(len(xy), 2)

        # Test multiple operators, boundary of a buffer
        ec = list(p.buffer(1).boundary.coords)
        self.assertIsInstance(ec, list)  # TODO: this is a poor test


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PolygonTestCase)

########NEW FILE########
__FILENAME__ = test_polygonize
from . import unittest
from shapely.geos import geos_version
from shapely.geometry import Point, LineString, Polygon
from shapely.geometry.base import dump_coords
from shapely.ops import polygonize, polygonize_full


class PolygonizeTestCase(unittest.TestCase):

    def test_polygonize(self):
        lines = [
            LineString(((0, 0), (1, 1))),
            LineString(((0, 0), (0, 1))),
            LineString(((0, 1), (1, 1))),
            LineString(((1, 1), (1, 0))),
            LineString(((1, 0), (0, 0))),
            LineString(((5, 5), (6, 6))),
            Point(0, 0),
            ]
        result = list(polygonize(lines))
        self.assertTrue(all([isinstance(x, Polygon) for x in result]))

    @unittest.skipIf(geos_version < (3, 3, 0), 'GEOS 3.3.0 required')
    def test_polygonize_full(self):

        lines2 = [
            ((0, 0), (1, 1)),
            ((0, 0), (0, 1)),
            ((0, 1), (1, 1)),
            ((1, 1), (1, 0)),
            ((1, 0), (0, 0)),
            ((5, 5), (6, 6)),
            ((1, 1), (100, 100)),
            ]

        result2, dangles, cuts, invalids = polygonize_full(lines2)
        self.assertEqual(len(result2), 2)
        self.assertTrue(all([isinstance(x, Polygon) for x in result2]))
        self.assertEqual(list(dangles.geoms), [])
        self.assertTrue(all([isinstance(x, LineString) for x in cuts.geoms]))

        self.assertEqual(
            dump_coords(cuts),
            [[(1.0, 1.0), (100.0, 100.0)], [(5.0, 5.0), (6.0, 6.0)]])
        self.assertEqual(list(invalids.geoms), [])


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PolygonizeTestCase)

########NEW FILE########
__FILENAME__ = test_predicates
"""Test GEOS predicates
"""
from . import unittest
from shapely.geometry import Point


class PredicatesTestCase(unittest.TestCase):

    def test_binary_predicates(self):

        point = Point(0.0, 0.0)

        self.assertTrue(point.disjoint(Point(-1.0, -1.0)))
        self.assertFalse(point.touches(Point(-1.0, -1.0)))
        self.assertFalse(point.crosses(Point(-1.0, -1.0)))
        self.assertFalse(point.within(Point(-1.0, -1.0)))
        self.assertFalse(point.contains(Point(-1.0, -1.0)))
        self.assertFalse(point.equals(Point(-1.0, -1.0)))
        self.assertFalse(point.touches(Point(-1.0, -1.0)))
        self.assertTrue(point.equals(Point(0.0, 0.0)))

    def test_unary_predicates(self):

        point = Point(0.0, 0.0)

        self.assertFalse(point.is_empty)
        self.assertTrue(point.is_valid)
        self.assertTrue(point.is_simple)
        self.assertFalse(point.is_ring)
        self.assertFalse(point.has_z)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PredicatesTestCase)

########NEW FILE########
__FILENAME__ = test_prepared
from . import unittest
from shapely.geos import geos_version
from shapely import prepared
from shapely import geometry


class PreparedGeometryTestCase(unittest.TestCase):

    @unittest.skipIf(geos_version < (3, 1, 0), 'GEOS 3.1.0 required')
    def test_prepared(self):
        polygon = geometry.Polygon([
            (0, 0), (1, 0), (1, 1), (0, 1)
        ])
        p = prepared.PreparedGeometry(polygon)
        self.assertTrue(p.contains(geometry.Point(0.5, 0.5)))
        self.assertFalse(p.contains(geometry.Point(0.5, 1.5)))

    @unittest.skipIf(geos_version < (3, 1, 0), 'GEOS 3.1.0 required')
    def test_op_not_allowed(self):
        p = prepared.PreparedGeometry(geometry.Point(0.0, 0.0).buffer(1.0))
        self.assertRaises(ValueError, geometry.Point(0.0, 0.0).union, p)

    @unittest.skipIf(geos_version < (3, 1, 0), 'GEOS 3.1.0 required')
    def test_predicate_not_allowed(self):
        p = prepared.PreparedGeometry(geometry.Point(0.0, 0.0).buffer(1.0))
        self.assertRaises(ValueError, geometry.Point(0.0, 0.0).contains, p)


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(PreparedGeometryTestCase)

########NEW FILE########
__FILENAME__ = test_products_z
from . import unittest
from shapely.geometry import LineString


class ProductZTestCase(unittest.TestCase):

    def test_line_intersection(self):
        line1 = LineString([(0, 0, 0), (1, 1, 1)])
        line2 = LineString([(0, 1, 1), (1, 0, 0)])
        interxn = line1.intersection(line2)
        self.assertTrue(interxn.has_z)
        self.assertEqual(interxn._ndim, 3)
        self.assertTrue(0.0 <= interxn.z <= 1.0)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(ProductZTestCase)

########NEW FILE########
__FILENAME__ = test_singularity
from . import unittest
from shapely.geometry import Polygon


class PolygonTestCase(unittest.TestCase):

    def test_polygon_3(self):
        p = (1.0, 1.0)
        poly = Polygon([p, p, p])
        self.assertEqual(poly.bounds, (1.0, 1.0, 1.0, 1.0))

    def test_polygon_5(self):
        p = (1.0, 1.0)
        poly = Polygon([p, p, p, p, p])
        self.assertEqual(poly.bounds, (1.0, 1.0, 1.0, 1.0))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(PolygonTestCase)

########NEW FILE########
__FILENAME__ = test_speedups
from . import unittest

from shapely import speedups
from shapely.geometry import LineString, Polygon


class SpeedupsTestCase(unittest.TestCase):

    def setUp(self):
        self.assertFalse(speedups._orig)
        if speedups.available:
            speedups.enable()
            self.assertTrue(speedups._orig)

    def tearDown(self):
        if speedups.available:
            self.assertTrue(speedups._orig)
        speedups.disable()
        self.assertFalse(speedups._orig)

    @unittest.skipIf(not speedups.available, 'speedups not available')
    def test_create_linestring(self):
        ls = LineString([(0, 0), (1, 0), (1, 2)])
        self.assertEqual(ls.length, 3)

    @unittest.skipIf(not speedups.available, 'speedups not available')
    def test_create_polygon(self):
        p = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
        self.assertEqual(p.length, 8)

    @unittest.skipIf(not speedups.available, 'speedups not available')
    def test_create_polygon_from_linestring(self):
        ls = LineString([(0, 0), (2, 0), (2, 2), (0, 2)])
        p = Polygon(ls)
        self.assertEqual(p.length, 8)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(SpeedupsTestCase)

########NEW FILE########
__FILENAME__ = test_styles
from . import unittest
from shapely.geometry import CAP_STYLE, JOIN_STYLE


class StylesTest(unittest.TestCase):

    def test_cap(self):
        self.assertEqual(CAP_STYLE.round, 1)
        self.assertEqual(CAP_STYLE.flat, 2)
        self.assertEqual(CAP_STYLE.square, 3)

    def test_join(self):
        self.assertEqual(JOIN_STYLE.round, 1)
        self.assertEqual(JOIN_STYLE.mitre, 2)
        self.assertEqual(JOIN_STYLE.bevel, 3)


def test_suite():
    return unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(StylesTest)])

########NEW FILE########
__FILENAME__ = test_transform
from . import unittest
from shapely import geometry
from shapely.ops import transform


class IdentityTestCase(unittest.TestCase):
    """New geometry/coordseq method 'xy' makes numpy interop easier"""

    def func(self, x, y, z=None):
        return tuple([c for c in [x, y, z] if c])

    def test_empty(self):
        g = geometry.Point()
        h = transform(self.func, g)
        self.assertTrue(h.is_empty)

    def test_point(self):
        g = geometry.Point(0, 1)
        h = transform(self.func, g)
        self.assertEqual(h.geom_type, 'Point')
        self.assertEqual(list(h.coords), [(0, 1)])

    def test_line(self):
        g = geometry.LineString(((0, 1), (2, 3)))
        h = transform(self.func, g)
        self.assertEqual(h.geom_type, 'LineString')
        self.assertEqual(list(h.coords), [(0, 1), (2, 3)])

    def test_linearring(self):
        g = geometry.LinearRing(((0, 1), (2, 3), (2, 2), (0, 1)))
        h = transform(self.func, g)
        self.assertEqual(h.geom_type, 'LinearRing')
        self.assertEqual(list(h.coords), [(0, 1), (2, 3), (2, 2), (0, 1)])

    def test_polygon(self):
        g = geometry.Point(0, 1).buffer(1.0)
        h = transform(self.func, g)
        self.assertEqual(h.geom_type, 'Polygon')
        self.assertAlmostEqual(g.area, h.area)

    def test_multipolygon(self):
        g = geometry.MultiPoint([(0, 1), (0, 4)]).buffer(1.0)
        h = transform(self.func, g)
        self.assertEqual(h.geom_type, 'MultiPolygon')
        self.assertAlmostEqual(g.area, h.area)


class LambdaTestCase(unittest.TestCase):
    """New geometry/coordseq method 'xy' makes numpy interop easier"""

    def test_point(self):
        g = geometry.Point(0, 1)
        h = transform(lambda x, y, z=None: (x+1.0, y+1.0), g)
        self.assertEqual(h.geom_type, 'Point')
        self.assertEqual(list(h.coords), [(1.0, 2.0)])

    def test_line(self):
        g = geometry.LineString(((0, 1), (2, 3)))
        h = transform(lambda x, y, z=None: (x+1.0, y+1.0), g)
        self.assertEqual(h.geom_type, 'LineString')
        self.assertEqual(list(h.coords), [(1.0, 2.0), (3.0, 4.0)])

    def test_polygon(self):
        g = geometry.Point(0, 1).buffer(1.0)
        h = transform(lambda x, y, z=None: (x+1.0, y+1.0), g)
        self.assertEqual(h.geom_type, 'Polygon')
        self.assertAlmostEqual(g.area, h.area)
        self.assertAlmostEqual(h.centroid.x, 1.0)
        self.assertAlmostEqual(h.centroid.y, 2.0)

    def test_multipolygon(self):
        g = geometry.MultiPoint([(0, 1), (0, 4)]).buffer(1.0)
        h = transform(lambda x, y, z=None: (x+1.0, y+1.0), g)
        self.assertEqual(h.geom_type, 'MultiPolygon')
        self.assertAlmostEqual(g.area, h.area)
        self.assertAlmostEqual(h.centroid.x, 1.0)
        self.assertAlmostEqual(h.centroid.y, 3.5)


def test_suite():
    loader = unittest.TestLoader()
    return unittest.TestSuite([
        loader.loadTestsFromTestCase(IdentityTestCase),
        loader.loadTestsFromTestCase(LambdaTestCase)])

########NEW FILE########
__FILENAME__ = test_union
from . import unittest
import random
from itertools import islice
from shapely.geos import geos_version
from shapely.ftools import partial
from shapely.geometry import Point, MultiPolygon
from shapely.ops import cascaded_union, unary_union


def halton(base):
    """Returns an iterator over an infinite Halton sequence"""
    def value(index):
        result = 0.0
        f = 1.0 / base
        i = index
        while i > 0:
            result += f * (i % base)
            i = i // base
            f = f / base
        return result
    i = 1
    while i > 0:
        yield value(i)
        i += 1


class UnionTestCase(unittest.TestCase):

    def test_cascaded_union(self):

        # Use a partial function to make 100 points uniformly distributed
        # in a 40x40 box centered on 0,0.

        r = partial(random.uniform, -20.0, 20.0)
        points = [Point(r(), r()) for i in range(100)]

        # Buffer the points, producing 100 polygon spots
        spots = [p.buffer(2.5) for p in points]

        # Perform a cascaded union of the polygon spots, dissolving them
        # into a collection of polygon patches
        u = cascaded_union(spots)
        self.assertTrue(u.geom_type in ('Polygon', 'MultiPolygon'))

    def setUp(self):
        # Instead of random points, use deterministic, pseudo-random Halton
        # sequences for repeatability sake.
        self.coords = zip(
            list(islice(halton(5), 20, 120)),
            list(islice(halton(7), 20, 120)),
        )

    @unittest.skipIf(geos_version < (3, 3, 0), 'GEOS 3.3.0 required')
    def test_unary_union(self):
        patches = [Point(xy).buffer(0.05) for xy in self.coords]
        u = unary_union(patches)
        self.assertEqual(u.geom_type, 'MultiPolygon')
        self.assertAlmostEqual(u.area, 0.71857254056)

    @unittest.skipIf(geos_version < (3, 3, 0), 'GEOS 3.3.0 required')
    def test_unary_union_multi(self):
        # Test of multipart input based on comment by @schwehr at
        # https://github.com/Toblerity/Shapely/issues/47#issuecomment-21809308
        patches = MultiPolygon([Point(xy).buffer(0.05) for xy in self.coords])
        self.assertAlmostEqual(unary_union(patches).area,
                               0.71857254056)
        self.assertAlmostEqual(unary_union([patches, patches]).area,
                               0.71857254056)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(UnionTestCase)

########NEW FILE########
__FILENAME__ = test_validation
from . import unittest
from shapely.geometry import Point
from shapely.validation import explain_validity


class ValidationTestCase(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(explain_validity(Point(0, 0)), 'Valid Geometry')


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(ValidationTestCase)

########NEW FILE########
__FILENAME__ = test_vectorized
from . import unittest, numpy
from shapely.geometry import Point, box, MultiPolygon
from shapely.vectorized import contains, touches

try:
    import numpy as np
except ImportError:
    pass


@unittest.skipIf(not numpy, 'numpy required')
class VectorizedContainsTestCase(unittest.TestCase):
    def assertContainsResults(self, geom, x, y):
        result = contains(geom, x, y)
        x = np.asanyarray(x)
        y = np.asanyarray(y) 

        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.dtype, np.bool)

        result_flat = result.flat
        x_flat, y_flat = x.flat, y.flat

        # Do the equivalent operation, only slowly, comparing the result
        # as we go.
        for idx in range(x.size):
            self.assertEqual(result_flat[idx], geom.contains(Point(x_flat[idx],
                                                                   y_flat[idx])))
        return result

    def construct_torus(self):
        point = Point(0, 0)
        return point.buffer(5).symmetric_difference(point.buffer(2.5))

    def test_contains_poly(self):
        y, x = np.mgrid[-10:10:5j], np.mgrid[-5:15:5j]
        self.assertContainsResults(self.construct_torus(), x, y)

    def test_contains_point(self):
        y, x = np.mgrid[-10:10:5j], np.mgrid[-5:15:5j]
        self.assertContainsResults(Point(x[0], y[0]), x, y)
    
    def test_contains_linestring(self):
        y, x = np.mgrid[-10:10:5j], np.mgrid[-5:15:5j]
        self.assertContainsResults(Point(x[0], y[0]), x, y)
    
    def test_contains_multipoly(self):
        y, x = np.mgrid[-10:10:5j], np.mgrid[-5:15:5j]
        # Construct a geometry of the torus cut in half vertically.
        cut_poly = box(-1, -10, -2.5, 10)
        geom = self.construct_torus().difference(cut_poly)
        self.assertIsInstance(geom, MultiPolygon)
        self.assertContainsResults(geom, x, y)

    def test_y_array_order(self):
        y, x = np.mgrid[-10:10:5j, -5:15:5j]
        y = y.copy(order='f')
        self.assertContainsResults(self.construct_torus(), x, y)
    
    def test_x_array_order(self):
        y, x = np.mgrid[-10:10:5j, -5:15:5j]
        x = x.copy(order='f')
        self.assertContainsResults(self.construct_torus(), x, y)
    
    def test_xy_array_order(self):
        y, x = np.mgrid[-10:10:5j, -5:15:5j]
        x = x.copy(order='f')
        y = y.copy(order='f')
        result = self.assertContainsResults(self.construct_torus(), x, y)
        # We always return a C_CONTIGUOUS array.
        self.assertTrue(result.flags['C_CONTIGUOUS'])
    
    def test_array_dtype(self):
        y, x = np.mgrid[-10:10:5j], np.mgrid[-5:15:5j]
        x = x.astype(np.int16)
        self.assertContainsResults(self.construct_torus(), x, y)
    
    def test_array_2d(self):
        y, x = np.mgrid[-10:10:15j, -5:15:16j]
        result = self.assertContainsResults(self.construct_torus(), x, y)
        self.assertEqual(result.shape, x.shape)

    def test_shapely_xy_attr_contains(self):
        g = Point(0, 0).buffer(10.0)
        self.assertContainsResults(self.construct_torus(), *g.exterior.xy)


@unittest.skipIf(not numpy, 'numpy required')
class VectorizedTouchesTestCase(unittest.TestCase):
    def test_touches(self):
        y, x = np.mgrid[-2:3:6j, -1:3:5j]
        geom = box(0, -1, 2, 2)
        result = touches(geom, x, y)
        expected = np.array([[False, False, False, False, False],
                             [False,  True,  True,  True, False],
                             [False,  True, False,  True, False],
                             [False,  True, False,  True, False],
                             [False,  True,  True,  True, False],
                             [False, False, False, False, False]], dtype=bool)
        from numpy.testing import assert_array_equal
        assert_array_equal(result, expected)
        
        


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(VectorizedContainsTestCase)

########NEW FILE########
__FILENAME__ = test_xy
from . import unittest
from shapely import geometry


class XYTestCase(unittest.TestCase):
    """New geometry/coordseq method 'xy' makes numpy interop easier"""

    def test_arrays(self):
        x, y = geometry.LineString(((0, 0), (1, 1))).xy
        self.assertEqual(len(x), 2)
        self.assertEqual(list(x), [0.0, 1.0])
        self.assertEqual(len(y), 2)
        self.assertEqual(list(y), [0.0, 1.0])


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(XYTestCase)

########NEW FILE########
__FILENAME__ = threading_test
import threading
from binascii import b2a_hex


def main():
    num_threads = 10
    use_threads = True

    if not use_threads:
        # Run core code
        runShapelyBuilding()
    else:
        threads = [threading.Thread(target=runShapelyBuilding, name=str(i),
                                    args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


def runShapelyBuilding(num):
    print("%s: Running shapely tests on wkb" % num)
    import shapely.geos
    print("%s GEOS Handle: %s" % (num, shapely.geos.lgeos.geos_handle))
    import shapely.wkt
    import shapely.wkb
    p = shapely.wkt.loads("POINT (0 0)")
    print("%s WKT: %s" % (num, shapely.wkt.dumps(p)))
    wkb = shapely.wkb.dumps(p)
    print("%s WKB: %s" % (num, b2a_hex(wkb)))

    for i in range(10):
        shapely.wkb.loads(wkb)

    print("%s GEOS Handle: %s" % (num, shapely.geos.lgeos.geos_handle))
    print("Done %s" % num)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = topology
"""
Intermediaries supporting GEOS topological operations

These methods all take Shapely geometries and other Python objects and delegate
to GEOS functions via ctypes.

These methods return ctypes objects that should be recast by the caller.
"""

from ctypes import byref, c_double
from shapely.geos import TopologicalError, lgeos

class Validating(object):
    def _validate(self, ob, stop_prepared=False):
        if ob is None or ob._geom is None:
            raise ValueError("Null geometry supports no operations")
        if stop_prepared and not hasattr(ob, 'type'):
            raise ValueError("Prepared geometries cannot be operated on")

class Delegating(Validating):
    def __init__(self, name):
        self.fn = lgeos.methods[name]

class BinaryRealProperty(Delegating):
    def __call__(self, this, other):
        self._validate(this)
        self._validate(other, stop_prepared=True)
        d = c_double()
        retval = self.fn(this._geom, other._geom, byref(d))
        return d.value

class UnaryRealProperty(Delegating):
    def __call__(self, this):
        self._validate(this)
        d = c_double()
        retval = self.fn(this._geom, byref(d))
        return d.value

class BinaryTopologicalOp(Delegating):
    def __call__(self, this, other, *args):
        self._validate(this)
        self._validate(other, stop_prepared=True)
        product = self.fn(this._geom, other._geom, *args)
        if product is None:
            if not this.is_valid:
                raise TopologicalError(
                    "The operation '%s' produced a null geometry. Likely cause is invalidity of the geometry %s" % (self.fn.__name__, repr(this)))
            elif not other.is_valid:
                raise TopologicalError(
                    "The operation '%s' produced a null geometry. Likely cause is invalidity of the 'other' geometry %s" % (self.fn.__name__, repr(other)))
            else:
                raise TopologicalError(
                    "This operation produced a null geometry. Reason: unknown")
        return product

class UnaryTopologicalOp(Delegating):
    def __call__(self, this, *args):
        self._validate(this)
        return self.fn(this._geom, *args)


########NEW FILE########
__FILENAME__ = validation
# TODO: allow for implementations using other than GEOS

import sys

from shapely.geos import lgeos

def explain_validity(ob):
    return lgeos.GEOSisValidReason(ob._geom)

########NEW FILE########
__FILENAME__ = wkb
"""Load/dump geometries using the well-known binary (WKB) format
"""

from shapely import geos

# Pickle-like convenience functions

def loads(data, hex=False):
    """Load a geometry from a WKB byte string, or hex-encoded string if
    ``hex=True``.
    """
    reader = geos.WKBReader(geos.lgeos)
    if hex:
        return reader.read_hex(data)
    else:
        return reader.read(data)

def load(fp, hex=False):
    """Load a geometry from an open file."""
    data = fp.read()
    return loads(data, hex=hex)

def dumps(ob, hex=False, **kw):
    """Dump a WKB representation of a geometry to a byte string, or a
    hex-encoded string if ``hex=True``.

    See available keyword output settings in ``shapely.geos.WKBWriter``."""
    writer = geos.WKBWriter(geos.lgeos, **kw)
    if hex:
        return writer.write_hex(ob)
    else:
        return writer.write(ob)


def dump(ob, fp, hex=False, **kw):
    """Dump a geometry to an open file."""
    fp.write(dumps(ob, hex=hex, **kw))

########NEW FILE########
__FILENAME__ = wkt
"""Load/dump geometries using the well-known text (WKT) format
"""

from shapely import geos

# Pickle-like convenience functions

def loads(data):
    """Load a geometry from a WKT string."""
    return geos.WKTReader(geos.lgeos).read(data)

def load(fp):
    """Load a geometry from an open file."""
    data = fp.read()
    return loads(data)

def dumps(ob, **kw):
    """Dump a WKT representation of a geometry to a string.

    See available keyword output settings in ``shapely.geos.WKTWriter``.
    """
    return geos.WKTWriter(geos.lgeos, **kw).write(ob)

def dump(ob, fp, **settings):
    """Dump a geometry to an open file."""
    fp.write(dumps(ob, **settings))

########NEW FILE########
