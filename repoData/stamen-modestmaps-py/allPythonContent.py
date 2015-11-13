__FILENAME__ = compose
# vim:et sts=4 sw=4:

import sys, math, optparse, ModestMaps

class BadComposure(Exception):
    pass

parser = optparse.OptionParser(usage="""compose.py [options] file

There are three ways to set a map coverage area.

1) Center, zoom, and dimensions: create a map of the specified size,
   centered on a given geographical point at a given zoom level:

   python compose.py -p OPENSTREETMAP -d 800 800 -c 37.8 -122.3 -z 11 out.jpg

2) Extent and dimensions: create a map of the specified size that
   adequately covers the given geographical extent:

   python compose.py -p MICROSOFT_ROAD -d 800 800 -e 36.9 -123.5 38.9 -121.2 out.png

3) Extent and zoom: create a map at the given zoom level that covers
   the precise geographical extent, at whatever pixel size is necessary:
   
   python compose.py -p BLUE_MARBLE -e 36.9 -123.5 38.9 -121.2 -z 9 out.jpg""")

parser.add_option('-v', '--verbose', dest='verbose',
                  help='Make a bunch of noise',
                  action='store_true')

parser.add_option('-c', '--center', dest='center', nargs=2,
                  help='Center. lat, lon, e.g.: 37.804 -122.263', type='float',
                  action='store')

parser.add_option('-e', '--extent', dest='extent', nargs=4,
                  help='Geographical extent. Two lat, lon pairs', type='float',
                  action='store')

parser.add_option('-z', '--zoom', dest='zoom',
                  help='Zoom level', type='int',
                  action='store')

parser.add_option('-d', '--dimensions', dest='dimensions', nargs=2,
                  help='Pixel dimensions of image', type='int',
                  action='store')

parser.add_option('-p', '--provider', dest='provider',
                  help='Map Provider, one of ' + ', '.join(ModestMaps.builtinProviders.keys()) + ' or URL template like "http://example.com/{Z}/{X}/{Y}.png".',
                  action='store')

parser.add_option('-k', '--apikey', dest='apikey',
                  help='API key for map providers that need one, e.g. CloudMade', type='str',
                  action='store')

parser.add_option('-f', '--fat-bits', dest='fatbits',
                  help='Optionally look to lower zoom levels if tiles at the requested level are unavailable',
                  action='store_true')

if __name__ == '__main__':

    (options, args) = parser.parse_args()
    
    try:
        try:
            outfile = args[0]
        except IndexError:
            raise BadComposure('Error: Missing output file.')
        
        try:
            if options.provider.startswith('CLOUDMADE_'):
                if not options.apikey:
                    raise BadComposure("Error: Cloudmade provider requires an API key. Register at http://developers.cloudmade.com/")

                provider = ModestMaps.builtinProviders[options.provider](options.apikey)
            elif options.provider.startswith('http://'):
                provider = ModestMaps.Providers.TemplatedMercatorProvider(options.provider)
            elif options.provider.startswith('https://'):
                provider = ModestMaps.Providers.TemplatedMercatorProvider(options.provider)
            elif options.provider.startswith('file://'):
                provider = ModestMaps.Providers.TemplatedMercatorProvider(options.provider)
            else:
                provider = ModestMaps.builtinProviders[options.provider]()
        except KeyError:
            raise BadComposure('Error: bad provider "%s".' % options.provider)
    
        if options.center and options.extent:
            raise BadComposure("Error: bad map coverage, center and extent can't both be set.")
        
        elif options.extent and options.dimensions and options.zoom:
            raise BadComposure("Error: bad map coverage, dimensions and zoom can't be set together with extent.")
        
        elif options.center and options.zoom and options.dimensions:
            lat, lon = options.center[0], options.center[1]
            width, height = options.dimensions[0], options.dimensions[1]

            dimensions = ModestMaps.Core.Point(width, height)
            center = ModestMaps.Geo.Location(lat, lon)
            zoom = options.zoom

            map = ModestMaps.mapByCenterZoom(provider, center, zoom, dimensions)
            
        elif options.extent and options.dimensions:
            latA, lonA = options.extent[0], options.extent[1]
            latB, lonB = options.extent[2], options.extent[3]
            width, height = options.dimensions[0], options.dimensions[1]

            dimensions = ModestMaps.Core.Point(width, height)
            locationA = ModestMaps.Geo.Location(latA, lonA)
            locationB = ModestMaps.Geo.Location(latB, lonB)

            map = ModestMaps.mapByExtent(provider, locationA, locationB, dimensions)
    
        elif options.extent and options.zoom:
            latA, lonA = options.extent[0], options.extent[1]
            latB, lonB = options.extent[2], options.extent[3]

            locationA = ModestMaps.Geo.Location(latA, lonA)
            locationB = ModestMaps.Geo.Location(latB, lonB)
            zoom = options.zoom

            map = ModestMaps.mapByExtentZoom(provider, locationA, locationB, zoom)
    
        else:
            raise BadComposure("Error: not really sure what's going on.")

    except BadComposure, e:
        print >> sys.stderr, parser.usage
        print >> sys.stderr, ''
        print >> sys.stderr, '%s --help for possible options.' % __file__
        print >> sys.stderr, ''
        print >> sys.stderr, e
        sys.exit(1)

    if options.verbose:
        print map.coordinate, map.offset, '->', outfile, (map.dimensions.x, map.dimensions.y)

    map.draw(options.verbose, options.fatbits).save(outfile)

########NEW FILE########
__FILENAME__ = BlueMarble
﻿"""
>>> p = Provider()
>>> p.getTileUrls(Coordinate(10, 13, 7))
('http://s3.amazonaws.com/com.modestmaps.bluemarble/7-r10-c13.jpg',)
>>> p.getTileUrls(Coordinate(13, 10, 7))
('http://s3.amazonaws.com/com.modestmaps.bluemarble/7-r13-c10.jpg',)
"""

from math import pi

from Core import Coordinate
from Geo import MercatorProjection, deriveTransformation
from Providers import IMapProvider

import Tiles

class Provider(IMapProvider):
    def __init__(self):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

    def getTileUrls(self, coordinate):
        return ('http://s3.amazonaws.com/com.modestmaps.bluemarble/%d-r%d-c%d.jpg' % (coordinate.zoom, coordinate.row, coordinate.column),)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = CloudMade
﻿"""
>>> p = OriginalProvider('example')
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.cloudmade.com/example/1/256/16/10507/25322.png',)

>>> p = FineLineProvider('example')
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.cloudmade.com/example/2/256/16/10507/25322.png',)

>>> p = TouristProvider('example')
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.cloudmade.com/example/7/256/16/10507/25322.png',)

>>> p = FreshProvider('example')
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.cloudmade.com/example/997/256/16/10507/25322.png',)

>>> p = PaleDawnProvider('example')
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.cloudmade.com/example/998/256/16/10507/25322.png',)

>>> p = MidnightCommanderProvider('example')
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.cloudmade.com/example/999/256/16/10507/25322.png',)

>>> p = BaseProvider('example', 510)
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.cloudmade.com/example/510/256/16/10507/25322.png',)
"""

from math import pi

from Core import Coordinate
from Geo import MercatorProjection, deriveTransformation
from Providers import IMapProvider

import random, Tiles

class BaseProvider(IMapProvider):
    def __init__(self, apikey, style=None):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)
        
        self.key = apikey
        
        if style:
            self.style = style

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

    def getTileUrls(self, coordinate):
        zoom, column, row = coordinate.zoom, coordinate.column, coordinate.row
        return ('http://tile.cloudmade.com/%s/%d/256/%d/%d/%d.png' % (self.key, self.style, zoom, column, row),)

class OriginalProvider(BaseProvider):
    style = 1

class FineLineProvider(BaseProvider):
    style = 2

class TouristProvider(BaseProvider):
    style = 7

class FreshProvider(BaseProvider):
    style = 997

class PaleDawnProvider(BaseProvider):
    style = 998

class MidnightCommanderProvider(BaseProvider):
    style = 999

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = Core
"""
>>> p = Point(0, 1)
>>> p
(0.000, 1.000)
>>> p.x
0
>>> p.y
1

>>> c = Coordinate(0, 1, 2)
>>> c
(0.000, 1.000 @2.000)
>>> c.row
0
>>> c.column
1
>>> c.zoom
2
>>> c.zoomTo(3)
(0.000, 2.000 @3.000)
>>> c.zoomTo(1)
(0.000, 0.500 @1.000)
>>> c.up()
(-1.000, 1.000 @2.000)
>>> c.right()
(0.000, 2.000 @2.000)
>>> c.down()
(1.000, 1.000 @2.000)
>>> c.left()
(0.000, 0.000 @2.000)
"""

import math

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return '(%(x).3f, %(y).3f)' % self.__dict__
    
class Coordinate:
    MAX_ZOOM = 25

    def __init__(self, row, column, zoom):
        self.row = row
        self.column = column
        self.zoom = zoom
    
    def __repr__(self):
        return '(%(row).3f, %(column).3f @%(zoom).3f)' % self.__dict__
        
    def __eq__(self, other):
        return self.zoom == other.zoom and self.row == other.row and self.column == other.column
        
    def __cmp__(self, other):
        return cmp((self.zoom, self.row, self.column), (other.zoom, other.row, other.column))

    def __hash__(self):
        return hash(('Coordinate', self.row, self.column, self.zoom))
        
    def copy(self):
        return self.__class__(self.row, self.column, self.zoom)
        
    def container(self):
        return self.__class__(math.floor(self.row), math.floor(self.column), self.zoom)

    def zoomTo(self, destination):
        return self.__class__(self.row * math.pow(2, destination - self.zoom),
                              self.column * math.pow(2, destination - self.zoom),
                              destination)
    
    def zoomBy(self, distance):
        return self.__class__(self.row * math.pow(2, distance),
                              self.column * math.pow(2, distance),
                              self.zoom + distance)

    def up(self, distance=1):
        return self.__class__(self.row - distance, self.column, self.zoom)

    def right(self, distance=1):
        return self.__class__(self.row, self.column + distance, self.zoom)

    def down(self, distance=1):
        return self.__class__(self.row + distance, self.column, self.zoom)

    def left(self, distance=1):
        return self.__class__(self.row, self.column - distance, self.zoom)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = Geo
"""
>>> t = Transformation(1, 0, 0, 0, 1, 0)
>>> p = Point(1, 1)
>>> p
(1.000, 1.000)
>>> p_ = t.transform(p)
>>> p_
(1.000, 1.000)
>>> p__ = t.untransform(p_)
>>> p__
(1.000, 1.000)

>>> t = Transformation(0, 1, 0, 1, 0, 0)
>>> p = Point(0, 1)
>>> p
(0.000, 1.000)
>>> p_ = t.transform(p)
>>> p_
(1.000, 0.000)
>>> p__ = t.untransform(p_)
>>> p__
(0.000, 1.000)

>>> t = Transformation(1, 0, 1, 0, 1, 1)
>>> p = Point(0, 0)
>>> p
(0.000, 0.000)
>>> p_ = t.transform(p)
>>> p_
(1.000, 1.000)
>>> p__ = t.untransform(p_)
>>> p__
(0.000, 0.000)

>>> m = MercatorProjection(10)
>>> m.locationCoordinate(Location(0, 0))
(-0.000, 0.000 @10.000)
>>> m.coordinateLocation(Coordinate(0, 0, 10))
(0.000, 0.000)
>>> m.locationCoordinate(Location(37, -122))
(0.696, -2.129 @10.000)
>>> m.coordinateLocation(Coordinate(0.696, -2.129, 10.000))
(37.001, -121.983)
"""

import math
from Core import Point, Coordinate

class Location:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        
    def __repr__(self):
        return '(%(lat).3f, %(lon).3f)' % self.__dict__

class Transformation:
    def __init__(self, ax, bx, cx, ay, by, cy):
        self.ax = ax
        self.bx = bx
        self.cx = cx
        self.ay = ay
        self.by = by
        self.cy = cy
    
    def transform(self, point):
        return Point(self.ax*point.x + self.bx*point.y + self.cx,
                     self.ay*point.x + self.by*point.y + self.cy)
                         
    def untransform(self, point):
        return Point((point.x*self.by - point.y*self.bx - self.cx*self.by + self.cy*self.bx) / (self.ax*self.by - self.ay*self.bx),
                     (point.x*self.ay - point.y*self.ax - self.cx*self.ay + self.cy*self.ax) / (self.bx*self.ay - self.by*self.ax))

def deriveTransformation(a1x, a1y, a2x, a2y, b1x, b1y, b2x, b2y, c1x, c1y, c2x, c2y):
    """ Generates a transform based on three pairs of points, a1 -> a2, b1 -> b2, c1 -> c2.
    """
    ax, bx, cx = linearSolution(a1x, a1y, a2x, b1x, b1y, b2x, c1x, c1y, c2x)
    ay, by, cy = linearSolution(a1x, a1y, a2y, b1x, b1y, b2y, c1x, c1y, c2y)
    
    return Transformation(ax, bx, cx, ay, by, cy)

def linearSolution(r1, s1, t1, r2, s2, t2, r3, s3, t3):
    """ Solves a system of linear equations.

          t1 = (a * r1) + (b + s1) + c
          t2 = (a * r2) + (b + s2) + c
          t3 = (a * r3) + (b + s3) + c

        r1 - t3 are the known values.
        a, b, c are the unknowns to be solved.
        returns the a, b, c coefficients.
    """

    # make them all floats
    r1, s1, t1, r2, s2, t2, r3, s3, t3 = map(float, (r1, s1, t1, r2, s2, t2, r3, s3, t3))

    a = (((t2 - t3) * (s1 - s2)) - ((t1 - t2) * (s2 - s3))) \
      / (((r2 - r3) * (s1 - s2)) - ((r1 - r2) * (s2 - s3)))

    b = (((t2 - t3) * (r1 - r2)) - ((t1 - t2) * (r2 - r3))) \
      / (((s2 - s3) * (r1 - r2)) - ((s1 - s2) * (r2 - r3)))

    c = t1 - (r1 * a) - (s1 * b)
    
    return a, b, c

class IProjection:
    def __init__(self, zoom, transformation=Transformation(1, 0, 0, 0, 1, 0)):
        self.zoom = zoom
        self.transformation = transformation
        
    def rawProject(self, point):
        raise NotImplementedError("Abstract method not implemented by subclass.")
        
    def rawUnproject(self, point):
        raise NotImplementedError("Abstract method not implemented by subclass.")

    def project(self, point):
        point = self.rawProject(point)
        if(self.transformation):
            point = self.transformation.transform(point)
        return point
    
    def unproject(self, point):
        if(self.transformation):
            point = self.transformation.untransform(point)
        point = self.rawUnproject(point)
        return point
        
    def locationCoordinate(self, location):
        point = Point(math.pi * location.lon / 180.0, math.pi * location.lat / 180.0)
        point = self.project(point)
        return Coordinate(point.y, point.x, self.zoom)

    def coordinateLocation(self, coordinate):
        coordinate = coordinate.zoomTo(self.zoom)
        point = Point(coordinate.column, coordinate.row)
        point = self.unproject(point)
        return Location(180.0 * point.y / math.pi, 180.0 * point.x / math.pi)

class LinearProjection(IProjection):
    def rawProject(self, point):
        return Point(point.x, point.y)

    def rawUnproject(self, point):
        return Point(point.x, point.y)

class MercatorProjection(IProjection):
    def rawProject(self, point):
        return Point(point.x,
                     math.log(math.tan(0.25 * math.pi + 0.5 * point.y)))

    def rawUnproject(self, point):
        return Point(point.x,
                     2 * math.atan(math.pow(math.e, point.y)) - 0.5 * math.pi)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = MapQuest
﻿"""
>>> p = RoadProvider()
>>> p.getTileUrls(Coordinate(10, 13, 7)) #doctest: +ELLIPSIS
('http://otile....mqcdn.com/tiles/1.0.0/7/13/10.png',)
>>> p.getTileUrls(Coordinate(13, 10, 7)) #doctest: +ELLIPSIS
('http://otile....mqcdn.com/tiles/1.0.0/7/10/13.png',)

>>> p = AerialProvider()
>>> p.getTileUrls(Coordinate(10, 13, 7)) #doctest: +ELLIPSIS
('http://oatile....mqcdn.com/naip/7/13/10.png',)
>>> p.getTileUrls(Coordinate(13, 10, 7)) #doctest: +ELLIPSIS
('http://oatile....mqcdn.com/naip/7/10/13.png',)
"""

from math import pi

from Core import Coordinate
from Geo import MercatorProjection, deriveTransformation
from Providers import IMapProvider

import random, Tiles

class AbstractProvider(IMapProvider):
    def __init__(self):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

class RoadProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        return ('http://otile%d.mqcdn.com/tiles/1.0.0/%d/%d/%d.png' % (random.randint(1, 4), coordinate.zoom, coordinate.column, coordinate.row),)

class AerialProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        return ('http://oatile%d.mqcdn.com/naip/%d/%d/%d.png' % (random.randint(1, 4), coordinate.zoom, coordinate.column, coordinate.row),)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = Microsoft
﻿"""
>>> p = RoadProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://r....ortho.tiles.virtualearth.net/tiles/r0230102122203031.png?g=90&shading=hill',)
>>> p.getTileUrls(Coordinate(25333, 10482, 16)) #doctest: +ELLIPSIS
('http://r....ortho.tiles.virtualearth.net/tiles/r0230102033330212.png?g=90&shading=hill',)

>>> p = AerialProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://a....ortho.tiles.virtualearth.net/tiles/a0230102122203031.jpeg?g=90',)
>>> p.getTileUrls(Coordinate(25333, 10482, 16)) #doctest: +ELLIPSIS
('http://a....ortho.tiles.virtualearth.net/tiles/a0230102033330212.jpeg?g=90',)

>>> p = HybridProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://h....ortho.tiles.virtualearth.net/tiles/h0230102122203031.jpeg?g=90',)
>>> p.getTileUrls(Coordinate(25333, 10482, 16)) #doctest: +ELLIPSIS
('http://h....ortho.tiles.virtualearth.net/tiles/h0230102033330212.jpeg?g=90',)
"""

from math import pi

from Core import Coordinate
from Geo import MercatorProjection, deriveTransformation
from Providers import IMapProvider

import random, Tiles

class AbstractProvider(IMapProvider):
    def __init__(self):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)

    def getZoomString(self, coordinate):
        return Tiles.toMicrosoft(int(coordinate.column), int(coordinate.row), int(coordinate.zoom))

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

class RoadProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        return ('http://r%d.ortho.tiles.virtualearth.net/tiles/r%s.png?g=90&shading=hill' % (random.randint(0, 3), self.getZoomString(self.sourceCoordinate(coordinate))),)

class AerialProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        return ('http://a%d.ortho.tiles.virtualearth.net/tiles/a%s.jpeg?g=90' % (random.randint(0, 3), self.getZoomString(self.sourceCoordinate(coordinate))),)

class HybridProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        return ('http://h%d.ortho.tiles.virtualearth.net/tiles/h%s.jpeg?g=90' % (random.randint(0, 3), self.getZoomString(self.sourceCoordinate(coordinate))),)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = OpenStreetMap
﻿"""
>>> p = Provider()
>>> p.getTileUrls(Coordinate(10, 13, 7))
('http://tile.openstreetmap.org/7/13/10.png',)
>>> p.getTileUrls(Coordinate(13, 10, 7))
('http://tile.openstreetmap.org/7/10/13.png',)
"""

from math import pi

from Core import Coordinate
from Geo import MercatorProjection, deriveTransformation
from Providers import IMapProvider

import Tiles

class Provider(IMapProvider):
    def __init__(self):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

    def getTileUrls(self, coordinate):
        return ('http://tile.openstreetmap.org/%d/%d/%d.png' % (coordinate.zoom, coordinate.column, coordinate.row),)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = Providers
﻿import re
from math import pi, pow

from Core import Coordinate
from Geo import LinearProjection, MercatorProjection, deriveTransformation

ids = ('MICROSOFT_ROAD', 'MICROSOFT_AERIAL', 'MICROSOFT_HYBRID',
       'YAHOO_ROAD',     'YAHOO_AERIAL',     'YAHOO_HYBRID',
       'BLUE_MARBLE',
       'OPEN_STREET_MAP')

class IMapProvider:
    def __init__(self):
        raise NotImplementedError("Abstract method not implemented by subclass.")
        
    def getTileUrls(self, coordinate):
        raise NotImplementedError("Abstract method not implemented by subclass.")

    def getTileUrls(self, coordinate):
        raise NotImplementedError("Abstract method not implemented by subclass.")

    def tileWidth(self):
        raise NotImplementedError("Abstract method not implemented by subclass.")
    
    def tileHeight(self):
        raise NotImplementedError("Abstract method not implemented by subclass.")
    
    def locationCoordinate(self, location):
        return self.projection.locationCoordinate(location)

    def coordinateLocation(self, location):
        return self.projection.coordinateLocation(location)

    def sourceCoordinate(self, coordinate):
        raise NotImplementedError("Abstract method not implemented by subclass.")

    def sourceCoordinate(self, coordinate):
        wrappedColumn = coordinate.column % pow(2, coordinate.zoom)
        
        while wrappedColumn < 0:
            wrappedColumn += pow(2, coordinate.zoom)
            
        return Coordinate(coordinate.row, wrappedColumn, coordinate.zoom)

class TemplatedMercatorProvider(IMapProvider):
    """ Convert URI templates into tile URLs, using a tileUrlTemplate identical to:
        http://code.google.com/apis/maps/documentation/overlays.html#Custom_Map_Types
    """
    def __init__(self, template):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)
        
        self.templates = []
        
        while template:
            match = re.match(r'^((http|https|file)://\S+?)(,(http|https|file)://\S+)?$', template)
            first = match.group(1)
            
            if match:
                self.templates.append(first)
                template = template[len(first):].lstrip(',')
            else:
                break

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

    def getTileUrls(self, coordinate):
        x, y, z = str(int(coordinate.column)), str(int(coordinate.row)), str(int(coordinate.zoom))
        return [t.replace('{X}', x).replace('{Y}', y).replace('{Z}', z) for t in self.templates]

########NEW FILE########
__FILENAME__ = Stamen
﻿"""
>>> p = BaseProvider('toner')
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.stamen.com/toner/16/10507/25322.png',)

>>> p = TonerProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.stamen.com/toner/16/10507/25322.png',)

>>> p = TerrainProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.stamen.com/terrain/16/10507/25322.png',)

>>> p = WatercolorProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://tile.stamen.com/watercolor/16/10507/25322.png',)
"""

from math import pi

from Core import Coordinate
from Geo import MercatorProjection, deriveTransformation
from Providers import IMapProvider

import random, Tiles

class BaseProvider(IMapProvider):
    def __init__(self, style):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)
        
        self.style = style

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

    def getTileUrls(self, coordinate):
        zoom, column, row = coordinate.zoom, coordinate.column, coordinate.row
        return ('http://tile.stamen.com/%s/%d/%d/%d.png' % (self.style, zoom, column, row),)

class TonerProvider(BaseProvider):
    def __init__(self):
        BaseProvider.__init__(self, 'toner')

class TerrainProvider(BaseProvider):
    def __init__(self):
        BaseProvider.__init__(self, 'terrain')

class WatercolorProvider(BaseProvider):
    def __init__(self):
        BaseProvider.__init__(self, 'watercolor')

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = Tiles
"""
>>> toBinaryString(1)
'1'
>>> toBinaryString(2)
'10'
>>> toBinaryString(3)
'11'
>>> toBinaryString(4)
'100'

>>> fromBinaryString('1')
1
>>> fromBinaryString('11')
3
>>> fromBinaryString('101')
5
>>> fromBinaryString('1001')
9

>>> fromYahooRoad(0, 0, 17)
(0, 0, 1)
>>> fromYahooRoad(10507, 7445, 2)
(10507, 25322, 16)
>>> fromYahooRoad(10482, 7434, 2)
(10482, 25333, 16)

>>> toYahooRoad(0, 0, 1)
(0, 0, 17)
>>> toYahooRoad(10507, 25322, 16)
(10507, 7445, 2)
>>> toYahooRoad(10482, 25333, 16)
(10482, 7434, 2)

>>> fromYahooAerial(0, 0, 17)
(0, 0, 1)
>>> fromYahooAerial(10507, 7445, 2)
(10507, 25322, 16)
>>> fromYahooAerial(10482, 7434, 2)
(10482, 25333, 16)

>>> toYahooAerial(0, 0, 1)
(0, 0, 17)
>>> toYahooAerial(10507, 25322, 16)
(10507, 7445, 2)
>>> toYahooAerial(10482, 25333, 16)
(10482, 7434, 2)

>>> fromMicrosoftRoad('0')
(0, 0, 1)
>>> fromMicrosoftRoad('0230102122203031')
(10507, 25322, 16)
>>> fromMicrosoftRoad('0230102033330212')
(10482, 25333, 16)

>>> toMicrosoftRoad(0, 0, 1)
'0'
>>> toMicrosoftRoad(10507, 25322, 16)
'0230102122203031'
>>> toMicrosoftRoad(10482, 25333, 16)
'0230102033330212'

>>> fromMicrosoftAerial('0')
(0, 0, 1)
>>> fromMicrosoftAerial('0230102122203031')
(10507, 25322, 16)
>>> fromMicrosoftAerial('0230102033330212')
(10482, 25333, 16)

>>> toMicrosoftAerial(0, 0, 1)
'0'
>>> toMicrosoftAerial(10507, 25322, 16)
'0230102122203031'
>>> toMicrosoftAerial(10482, 25333, 16)
'0230102033330212'
"""

import math

octalStrings = ('000', '001', '010', '011', '100', '101', '110', '111')

def toBinaryString(i):
    """ Return a binary string for an integer.
    """
    return ''.join([octalStrings[int(c)]
                    for c
                    in oct(i)]).lstrip('0')

def fromBinaryString(s):
    """ Return an integer for a binary string.
    """
    s = list(s)
    e = 0
    i = 0
    while(len(s)):
        if(s[-1]) == '1':
            i += int(math.pow(2, e))
        e += 1
        s.pop()
    return i

def fromYahoo(x, y, z):
    """ Return column, row, zoom for Yahoo x, y, z.
    """
    zoom = 18 - z
    row = int(math.pow(2, zoom - 1) - y - 1)
    col = x
    return col, row, zoom

def toYahoo(col, row, zoom):
    """ Return x, y, z for Yahoo tile column, row, zoom.
    """
    x = col
    y = int(math.pow(2, zoom - 1) - row - 1)
    z = 18 - zoom
    return x, y, z

def fromYahooRoad(x, y, z):
    """ Return column, row, zoom for Yahoo Road tile x, y, z.
    """
    return fromYahoo(x, y, z)

def toYahooRoad(col, row, zoom):
    """ Return x, y, z for Yahoo Road tile column, row, zoom.
    """
    return toYahoo(col, row, zoom)

def fromYahooAerial(x, y, z):
    """ Return column, row, zoom for Yahoo Aerial tile x, y, z.
    """
    return fromYahoo(x, y, z)

def toYahooAerial(col, row, zoom):
    """ Return x, y, z for Yahoo Aerial tile column, row, zoom.
    """
    return toYahoo(col, row, zoom)

microsoftFromCorners = {'0': '00', '1': '01', '2': '10', '3': '11'}
microsoftToCorners = {'00': '0', '01': '1', '10': '2', '11': '3'}

def fromMicrosoft(s):
    """ Return column, row, zoom for Microsoft tile string.
    """
    row, col = map(fromBinaryString, zip(*[list(microsoftFromCorners[c]) for c in s]))
    zoom = len(s)
    return col, row, zoom

def toMicrosoft(col, row, zoom):
    """ Return string for Microsoft tile column, row, zoom.
    """
    x = col
    y = row
    y, x = toBinaryString(y).rjust(zoom, '0'), toBinaryString(x).rjust(zoom, '0')
    string = ''.join([microsoftToCorners[y[c]+x[c]] for c in range(zoom)])
    return string

def fromMicrosoftRoad(s):
    """ Return column, row, zoom for Microsoft Road tile string.
    """
    return fromMicrosoft(s)

def toMicrosoftRoad(col, row, zoom):
    """ Return x, y, z for Microsoft Road tile column, row, zoom.
    """
    return toMicrosoft(col, row, zoom)

def fromMicrosoftAerial(s):
    """ Return column, row, zoom for Microsoft Aerial tile string.
    """
    return fromMicrosoft(s)

def toMicrosoftAerial(col, row, zoom):
    """ Return x, y, z for Microsoft Aerial tile column, row, zoom.
    """
    return toMicrosoft(col, row, zoom)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = Yahoo
﻿"""
>>> p = RoadProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://us.maps2.yimg.com/us.png.maps.yimg.com/png?v=...&t=m&x=10507&y=7445&z=2',)
>>> p.getTileUrls(Coordinate(25333, 10482, 16)) #doctest: +ELLIPSIS
('http://us.maps2.yimg.com/us.png.maps.yimg.com/png?v=...&t=m&x=10482&y=7434&z=2',)

>>> p = AerialProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://us.maps3.yimg.com/aerial.maps.yimg.com/tile?v=...&t=a&x=10507&y=7445&z=2',)
>>> p.getTileUrls(Coordinate(25333, 10482, 16)) #doctest: +ELLIPSIS
('http://us.maps3.yimg.com/aerial.maps.yimg.com/tile?v=...&t=a&x=10482&y=7434&z=2',)

>>> p = HybridProvider()
>>> p.getTileUrls(Coordinate(25322, 10507, 16)) #doctest: +ELLIPSIS
('http://us.maps3.yimg.com/aerial.maps.yimg.com/tile?v=...&t=a&x=10507&y=7445&z=2', 'http://us.maps3.yimg.com/aerial.maps.yimg.com/png?v=...&t=h&x=10507&y=7445&z=2')
>>> p.getTileUrls(Coordinate(25333, 10482, 16)) #doctest: +ELLIPSIS
('http://us.maps3.yimg.com/aerial.maps.yimg.com/tile?v=...&t=a&x=10482&y=7434&z=2', 'http://us.maps3.yimg.com/aerial.maps.yimg.com/png?v=...&t=h&x=10482&y=7434&z=2')
"""

from math import pi

from Core import Coordinate
from Geo import MercatorProjection, deriveTransformation
from Providers import IMapProvider

import Tiles

ROAD_VERSION = '3.52'
AERIAL_VERSION = '1.7'
HYBRID_VERSION = '2.2'

class AbstractProvider(IMapProvider):
    def __init__(self):
        # the spherical mercator world tile covers (-π, -π) to (π, π)
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)
        self.projection = MercatorProjection(0, t)

    def getZoomString(self, coordinate):
        return 'x=%d&y=%d&z=%d' % Tiles.toYahoo(int(coordinate.column), int(coordinate.row), int(coordinate.zoom))

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

class RoadProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        return ('http://us.maps2.yimg.com/us.png.maps.yimg.com/png?v=%s&t=m&%s' % (ROAD_VERSION, self.getZoomString(self.sourceCoordinate(coordinate))),)

class AerialProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        return ('http://us.maps3.yimg.com/aerial.maps.yimg.com/tile?v=%s&t=a&%s' % (AERIAL_VERSION, self.getZoomString(self.sourceCoordinate(coordinate))),)

class HybridProvider(AbstractProvider):
    def getTileUrls(self, coordinate):
        under = AerialProvider().getTileUrls(coordinate)[0]
        over = 'http://us.maps3.yimg.com/aerial.maps.yimg.com/png?v=%s&t=h&%s' % (HYBRID_VERSION, self.getZoomString(self.sourceCoordinate(coordinate)))
        return (under, over)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = ws-compose
import optparse
import wscompose

if __name__ == "__main__" :

    parser = optparse.OptionParser()
    parser.add_option("-p", "--port", dest="port", help="port number that the ws-compose HTTP server will listen on", default=9999)
    
    (opts, args) = parser.parse_args()
    
    app = wscompose.server(wscompose.handler, int(opts.port))
    app.loop()

########NEW FILE########
__FILENAME__ = ws-pinwin
import optparse
import wscompose
import wscompose.pinwin

if __name__ == "__main__" :

    parser = optparse.OptionParser()
    parser.add_option("-p", "--port", dest="port", help="port number that the ws-pinwin HTTP server will listen on", default=9999)
    
    (opts, args) = parser.parse_args()

    app = wscompose.server(wscompose.pinwin.handler, int(opts.port))
    app.loop()

########NEW FILE########
__FILENAME__ = client
# -*-python-*-

__package__    = "wscompose/client.py"
__version__    = "1.0"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/wscompose"
__date__       = "$Date: 2008/01/04 06:23:46 $"
__copyright__  = "Copyright (c) 2007-2008 Aaron Straup Cope. BSD license : http://www.modestmaps.com/license.txt"

import urllib
import httplib
import Image
import StringIO
import string
import re

class httpclient :

    def __init__ (self, host='127.0.0.1', port=9999) :
        self.__host__  = host
        self.__port__ = port

    # ##########################################################
    
    def fetch (self, args) :

        img = None
        meta = {}

        params = urllib.urlencode(args)
        url = "%s:%s" % (self.__host__, self.__port__)
        endpoint = "/?%s" % params

        # maybe always POST or at least add it as an option...
        
        try :
            conn = httplib.HTTPConnection(url)
            conn.request("GET", endpoint)
            res = conn.getresponse()
        except Exception, e :
            raise e

        if res.status != 200 :

            if res.status == 500 :
                errmsg = "(%s) %s" % (res.getheader('x-errorcode'), res.getheader('x-errormessage'))
                raise Exception, errmsg
            else :
                raise Exception, res.message   

        # fu.PYTHON ...
        re_xheader = re.compile(r"^x-wscompose-", re.IGNORECASE)
        
        for key, value in res.getheaders() :

            if re_xheader.match(key) :

                parts = key.split("-")
                parts = map(string.lower, parts)

                major = parts[2]
                minor = parts[3]
                
                if not meta.has_key(major) :
                    meta[major] = {}

                meta[major][minor] = value
                                    
        data = res.read()
        conn.close()

        try : 
            img = Image.open(StringIO.StringIO(data))
        except Exception, e :
            raise e
        
        return (img, meta)

    # ##########################################################

########NEW FILE########
__FILENAME__ = convexhull
__package__    = "wscompose/convexhull.py"
__version__    = "1.0"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/wscompose"
__date__       = "$Date: 2008/01/04 06:23:46 $"
__copyright__  = "Copyright (c) 2007-2008 Aaron Straup Cope. BSD license : http://www.modestmaps.com/license."

# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66527

"""convexhull.py

Calculate the convex hull of a set of n 2D-points in O(n log n) time.  
Taken from Berg et al., Computational Geometry, Springer-Verlag, 1997.
Prints output as EPS file.

When run from the command line it generates a random set of points
inside a square of given length and finds the convex hull for those,
printing the result as an EPS file.

Usage:

    convexhull.py <numPoints> <squareLength> <outFile>

Dinu C. Gherman
"""


import sys, string, random


######################################################################
# Helpers
######################################################################

def _myDet(p, q, r):
    """Calc. determinant of a special matrix with three 2D points.

    The sign, "-" or "+", determines the side, right or left,
    respectivly, on which the point r lies, when measured against
    a directed vector from p to q.
    """

    # We use Sarrus' Rule to calculate the determinant.
    # (could also use the Numeric package...)
    sum1 = q[0]*r[1] + p[0]*q[1] + r[0]*p[1]
    sum2 = q[0]*p[1] + r[0]*q[1] + p[0]*r[1]

    return sum1 - sum2


def _isRightTurn((p, q, r)):
    "Do the vectors pq:qr form a right turn, or not?"

    # assert p != q and q != r and p != r
            
    if _myDet(p, q, r) < 0:
	return 1
    else:
        return 0


def _isPointInPolygon(r, P):
    "Is point r inside a given polygon P?"

    # We assume the polygon is a list of points, listed clockwise!
    for i in xrange(len(P[:-1])):
        p, q = P[i], P[i+1]
        if not _isRightTurn((p, q, r)):
            return 0 # Out!        

    return 1 # It's within!


def _makeRandomData(numPoints=10, sqrLength=100, addCornerPoints=0):
    "Generate a list of random points within a square."
    
    # Fill a square with random points.
    min, max = 0, sqrLength
    P = []
    for i in xrange(numPoints):
	rand = random.randint
	x = rand(min+1, max-1)
	y = rand(min+1, max-1)
	P.append((x, y))

    # Add some "outmost" corner points.
    if addCornerPoints != 0:
	P = P + [(min, min), (max, max), (min, max), (max, min)]

    return P


######################################################################
# Output
######################################################################

epsHeader = """%%!PS-Adobe-2.0 EPSF-2.0
%%%%BoundingBox: %d %d %d %d

/r 2 def                %% radius

/circle                 %% circle, x, y, r --> -
{
    0 360 arc           %% draw circle
} def

/cross                  %% cross, x, y --> -
{
    0 360 arc           %% draw cross hair
} def

1 setlinewidth          %% thin line
newpath                 %% open page
0 setgray               %% black color

"""

def saveAsEps(P, H, boxSize, path):
    "Save some points and their convex hull into an EPS file."
    
    # Save header.
    f = open(path, 'w')
    f.write(epsHeader % (0, 0, boxSize, boxSize))

    format = "%3d %3d"

    # Save the convex hull as a connected path.
    if H:
        f.write("%s moveto\n" % format % H[0])
        for p in H:
            f.write("%s lineto\n" % format % p)
        f.write("%s lineto\n" % format % H[0])
        f.write("stroke\n\n")

    # Save the whole list of points as individual dots.
    for p in P:
        f.write("%s r circle\n" % format % p)
        f.write("stroke\n")
            
    # Save footer.
    f.write("\nshowpage\n")


######################################################################
# Public interface
######################################################################

def convexHull(P):
    "Calculate the convex hull of a set of points."

    # Get a local list copy of the points and sort them lexically.
    points = map(None, P)
    points.sort()

    # Build upper half of the hull.
    upper = [points[0], points[1]]
    for p in points[2:]:
	upper.append(p)
	while len(upper) > 2 and not _isRightTurn(upper[-3:]):
	    del upper[-2]

    # Build lower half of the hull.
    points.reverse()
    lower = [points[0], points[1]]
    for p in points[2:]:
	lower.append(p)
	while len(lower) > 2 and not _isRightTurn(lower[-3:]):
	    del lower[-2]

    # Remove duplicates.
    del lower[0]
    del lower[-1]

    # Concatenate both halfs and return.
    return tuple(upper + lower)


######################################################################
# Test
######################################################################

def test():
    a = 200
    p = _makeRandomData(30, a, 0)
    c = convexHull(p)
    saveAsEps(p, c, a, file)


######################################################################

if __name__ == '__main__':
    try:
        numPoints = string.atoi(sys.argv[1])
        squareLength = string.atoi(sys.argv[2])
        path = sys.argv[3]
    except IndexError:
        numPoints = 30
        squareLength = 200
        path = "sample.eps"

    p = _makeRandomData(numPoints, squareLength, addCornerPoints=0)

    print "WTF %s" % p
    
    c = convexHull(p)
    saveAsEps(p, c, squareLength, path)


########NEW FILE########
__FILENAME__ = dithering
# -*-python-*-

__package__    = "wscompose/dithering.py"
__version__    = "1.0"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/wscompose"
__date__       = "$Date: 2008/01/04 06:23:46 $"
__copyright__  = "Copyright (c) 2007-2008 Aaron Straup Cope. BSD license : http://www.modestmaps.com/license."

import wscompose
import Image

# DEPRECATED
# TO BE REBLESSED AS A PROPER PROVIDER

class handler (wscompose.handler) :

    def draw_map (self) :

        img = wscompose.handler.draw_map(self)
        return self.atkinson_dithering(img)
    
    #
    # http://mike.teczno.com/notes/atkinson.html
    #
    
    def atkinson_dithering(self, img) :

        img = img.convert('L')

        threshold = 128*[0] + 128*[255]

        for y in range(img.size[1]):
            for x in range(img.size[0]):

                old = img.getpixel((x, y))
                new = threshold[old]
                err = (old - new) >> 3 # divide by 8
            
                img.putpixel((x, y), new)
        
                for nxy in [(x+1, y), (x+2, y), (x-1, y+1), (x, y+1), (x+1, y+1), (x, y+2)]:
                    try:
                        img.putpixel(nxy, img.getpixel(nxy) + err)
                    except IndexError:
                        pass

        return img.convert('RGBA')

########NEW FILE########
__FILENAME__ = pinwin
# -*-python-*-

__package__    = "wscompose/pinwin.py"
__version__    = "1.1"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/wscompose"
__date__       = "$Date: 2008/01/04 06:23:46 $"
__copyright__  = "Copyright (c) 2007-2008 Aaron Straup Cope. BSD license : http://www.modestmaps.com/license."

import wscompose
import convexhull

import wscompose.plotting
import wscompose.dithering

import re
import urllib
import Image
import ImageDraw
import StringIO
import ModestMaps
import validate

# TO DO (patches are welcome) :
#
# - figure out whether/what code here should be merged
#   with plotting.py

class handler (wscompose.plotting.handler, wscompose.dithering.handler) :

    def draw_map (self) :

        img = wscompose.handler.draw_map(self)

        if self.ctx.has_key('filter') and self.ctx['filter'] == 'atkinson' :
            img = self.atkinson_dithering(img)

        #

        if self.ctx.has_key('polylines') :
            img = self.draw_polylines(img)

        #

        if self.ctx.has_key('hulls') :
            img = self.draw_convex_hulls(img)
            
        #
        
        if self.ctx.has_key('dots') :
            img = self.draw_dots(img)

        #
        
        if self.ctx.has_key('markers') :

            self.reposition_markers()
            
            if self.ctx.has_key('bleed') :
                img = self.draw_markers_with_bleed(img)                
            else :
                img = self.draw_markers(img)            

        #
        
        return img

    # ##########################################################

    def send_x_headers (self, img) :

        wscompose.handler.send_x_headers(self, img)
        
        if self.ctx.has_key('markers') :
            
            for mrk_data in self.ctx['markers'] :
            
                # The first two numbers are the x/y coordinates for the lat/lon.
                # The second two are the x/y coordinates of the top left corner
                # where the actual pinwin content should be pasted. The last pair
                # are the dimensions of the pinwin content which is sort of redundant
                # unless you are opting for defaults and don't know what to expect.

                details = (mrk_data['x'], mrk_data['y'],
                           mrk_data['x_fill'], mrk_data['y_fill'],
                           mrk_data['width'], mrk_data['height'])
                
                details = map(str, details)
                header = "X-wscompose-Marker-%s" % mrk_data['label']
                sep = ","
                
                self.send_header(header, sep.join(details))

        #

        if self.ctx.has_key('dots') :
            for data in self.ctx['dots'] :

                pt = self.latlon_to_point(data['latitude'], data['longitude'])

                header = "X-wscompose-Dot-%s" % data['label']
                coords = "%s,%s,%s" % (int(pt.x), int(pt.y), int(data['radius']))
                
                self.send_header(header, coords)
        
    # ##########################################################

    def draw_polylines (self, img) :

        for poly in self.ctx['polylines'] :
            img = self.draw_polyline(img, poly)

        return img

    # ##########################################################
    
    def draw_polyline (self, img, poly) :
        
        dr = ImageDraw.Draw(img)
        cnt = len(poly)
        i = 0

        grey = (42, 42, 42)
        
        while i < cnt : 

            j = i + 1

            if j == cnt :
                break

            cur = self.latlon_to_point(poly[i]['latitude'], poly[i]['longitude'])
            next = self.latlon_to_point(poly[j]['latitude'], poly[j]['longitude'])            

            dr.line((cur.x, cur.y, next.x, next.y), fill=grey, width=4)
            i += 1

        #
                
        return img
            
    # ##########################################################

    def draw_convex_hulls(self, img) :

        dr = ImageDraw.Draw(img)

        for type in self.ctx['hulls'] :

            points = []

            # sigh...
            key = "%ss" % type
            
            for coord in self.ctx[key] : 
                pt = self.latlon_to_point(coord['latitude'], coord['longitude'])    
                points.append((pt.x, pt.y))

            hull = convexhull.convexHull(points)
            
            #
            # no way to assign width to polygon outlines in PIL...
            #
            
            pink = (255, 0, 132)
            cnt = len(hull)
            i = 0

            while i < cnt : 
                (x1, y1) = hull[i]
                
                j = i + 1

                if j == cnt :
                    (x2, y2) = hull[0]
                else :
                    (x2, y2) = hull[j]

                dr.line((x1, y1, x2, y2), fill=pink, width=6)
                i += 1

        return img
    
    # ##########################################################
    
    # To do : move this code in to methods that can be run
    # easily from unit tests and/or CLI tools...
    
    def draw_markers_with_bleed (self, img) :
            
        bleed_top = 0
        bleed_right = 0
        bleed_bottom = 0
        bleed_left = 0
        bleed = 0

        for data in self.ctx['markers'] :
            (top, right, bottom, left) = self.calculate_bleed(img, data)

            bleed_top = min(bleed_top, top)
            bleed_right = max(bleed_right, right)
            bleed_bottom = max(bleed_bottom, bottom)
            bleed_left = min(bleed_left, left)
            
            # print "%s : top: %s, right: %s, bottom: %s, left: %s" % (data['label'], bleed_top, bleed_right, bleed_bottom, bleed_left)
            
        #
        
        if bleed_top : 
            bleed_top -= bleed_top * 2
            
        if bleed_left :
            bleed_left -= bleed_left * 2
            
        #
        
        bleed_x = bleed_left
        bleed_y = bleed_top
        
        if bleed_top or bleed_right :

            old = img.copy()
            sz = old.size

            x = sz[0] + bleed_left + bleed_right
            y = sz[1] + bleed_top + bleed_bottom

            # print "new x: %s y: %s" % (x, y)
            # print "paste x: %s y: %s" % (bleed_x, bleed_y)
            
            img = Image.new('RGB', (x, y), 'white')
            img.paste(old, (bleed_x, bleed_y))
            
        #

        if self.ctx['shadows'] :
            for data in self.ctx['markers'] :
                self.draw_shadow(img, data, bleed_x, bleed_y)
        
        for data in self.ctx['markers'] :
            self.draw_marker(img, data, bleed_x, bleed_y)

        return img

    # ##########################################################

    def calculate_bleed (self, img, mrk_data) :

        w = mrk_data['width']
        h = mrk_data['height']
        a = mrk_data['adjust_cone_height']
        
        mrk = self.load_marker(w, h, a)
        mrk_sz = mrk.fh().size
        
        loc = ModestMaps.Geo.Location(mrk_data['latitude'], mrk_data['longitude'])
        pt = self.ctx['map'].locationPoint(loc)            

        #
        
        mrk_data['x'] = int(pt.x)
        mrk_data['y'] = int(pt.y)

        mx = mrk_data['x'] - int(mrk.x_offset)
        my = mrk_data['y'] - int(mrk.y_offset)

        dx = mx + mrk.x_padding
        dy = my + mrk.y_padding

        #

        top = my
        right = 0

        if self.ctx['shadows'] :
            right = (mx + mrk_sz[0]) - img.size[0]
        else :
            
            im_w = img.size[0]
            test = mrk_data['x']  + (mrk.canvas_w - int(mrk.pt_x))
            
            if test > im_w :
                right = test - im_w

        #
        
        left = mx
        bottom = my + mrk_sz[1] - img.size[1]

        # print "calc bleed %s, %s, %s, %s" % (top, right, bottom, left)
        return (top, right, bottom, left)

    # ##########################################################

    def draw_marker (self, img, mrk_data, bleed_x=0, bleed_y=0) :
        
        #
        # Dirty... hack to account for magic
        # center/zoom markers...
        #
        
        if mrk_data.has_key('fill') and mrk_data['fill'] == 'center' :
            if self.ctx['method'] == 'center' :
                mrk_data['latitude'] = self.ctx['latitude']
                mrk_data['longitude'] = self.ctx['longitude']
            else :
                offset_lat = (self.ctx['bbox'][2] - self.ctx['bbox'][0]) / 2
                offset_lon = (self.ctx['bbox'][3] - self.ctx['bbox'][1]) / 2
            
                mrk_data['latitude'] = self.ctx['bbox'][0] + offset_lat
                mrk_data['longitude'] = self.ctx['bbox'][1] + offset_lon

        wscompose.plotting.handler.draw_marker(self, img, mrk_data, bleed_x, bleed_y)

        #
        # Magic global fill in with a map hack
        #
        
        if self.ctx.has_key('fill') :
            mrk_data['fill'] = 'center'
            mrk_data['provider'] = self.ctx['fill']
            mrk_data['zoom'] = self.ctx['fill_zoom']

        try :
            fill = self.fetch_marker_fill(mrk_data)
        except Exception, e :
            return False

        #
        # Magic global fill in with a map hack
        #

        if self.ctx.has_key('fill') :
            # add centering dot
            # (flickr pink)
        
            pink = (255, 0, 132)

            (w, h) = fill.size
        
            h = h / 2
            w = w / 2
            
            x1 = int(w - 5)
            x2 = int(w + 5)
            y1 = int(h - 5)
            y2 = int(h + 5)
            
            dr = ImageDraw.Draw(fill)        
            dr.ellipse((x1, y1, x2, y2), outline=pink)
            
        # the offset to paste the filler content
        
        dx = mrk_data['x_fill']
        dy = mrk_data['y_fill']

        img.paste(fill, (dx, dy))
        return True
    
    # ##########################################################

    # share me with marker.py or add shapes.py (or something) ?
    
    def draw_dots (self, img) :

        dr = ImageDraw.Draw(img)
        pink = (255, 0, 132)
        grey = (42, 42, 42)
        
        for data in self.ctx['dots'] :

            pt = self.latlon_to_point(data['latitude'], data['longitude'])
            offset = float(data['radius']) / 2

            x1 = pt.x - offset
            y1 = pt.y - offset
            x2 = pt.x + offset
            y2 = pt.y + offset

            dr.ellipse((x1 + 1 , y1 + 2, x2 + 1, y2 + 2), fill=grey)
            dr.ellipse((x1, y1, x2, y2), fill=pink)            

        return img
    
    # ##########################################################
    
    def fetch_marker_fill (self, mrk_data) :
        
        if mrk_data.has_key('fill') and mrk_data['fill'] == 'center' :
                
            args = {'height': mrk_data['height'],
                    'width' : mrk_data['width'],
                    'latitude' : mrk_data['latitude'],
                    'longitude' : mrk_data['longitude'],
                    'zoom' : mrk_data['zoom'],
                    'provider' : mrk_data['provider'],
                    }

            (host, port) = self.server.server_address

            if host == '' :
                host = "127.0.0.1"
                
            params = urllib.urlencode(args)
            
            url = "http://%s:%s?%s" % (host, port, params)
            
        else :
            url = mrk_data['fill']
            
        #
        
        data = urllib.urlopen(url).read()
        return Image.open(StringIO.StringIO(data)).convert('RGBA')        
    
    # ##########################################################

    def validate_params (self, params) :

        valid = wscompose.handler.validate_params(self, params)
        
        if not valid :
            return False

        #

        validator = validate.validate()

        #
        # markers
        #

        if params.has_key('marker') :

            try :
                valid['markers'] = validator.markers(params['marker'])
            except Exception, e :
                self.error(141, e)
                return False

        #
        # magic!
        #
        
        if params.has_key('fill') :

            re_provider = re.compile(r"^(YAHOO|MICROSOFT)_(ROAD|HYBRID|AERIAL)$")
            re_num = re.compile(r"^\d+$")
                
            if not re_provider.match(params['fill'][0].upper()) :
                self.error(102, "Not a valid marker provider")
                return False

            valid['fill'] = unicode(params['fill'][0].upper())

            if params.has_key('fill_accuracy') :
                
                if not re_num.match(params['fill_accuracy'][0]) :
                    self.error(102, "Not a valid number %s" % 'accuracy')
                    return False

                valid['fill_zoom'] = float(params['fill_accuracy'])
                
            else :
                valid['fill_zoom'] = 15

        #

        if params.has_key('bleed') :
            valid['bleed'] = True
            
        #

        if params.has_key('filter') :

            valid_filters = ('atkinson')
            
            if not params['filter'][0] in valid_filters :
                self.error(104, "Not a valid marker filter")
                return False

            valid['filter'] = params['filter'][0]
            
        #
        # dots
        #

        if params.has_key('dot') :

            try :
                valid['dots'] = validator.dots(params['dot'])
            except Exception, e :
                self.error(141, e)
                return False

        #
        # polylines
        #

        if params.has_key('polyline') :

            try :
                valid['polylines'] = validator.polylines(params['polyline'])
            except Exception, e :
                self.error(142, e)
                return False

        #
        #
        #

        if params.has_key('convex') :

            try :
                valid['hulls'] = validator.convex(params['convex'])
            except Exception, e :
                self.error(143, e)
                return False

        #
        # shadows
        #

        if params.has_key('noshadow') :
            valid['shadows'] = False
        else :
            valid['shadows'] = True
            
        #
        # Happy happy
        #
        
        return valid

    # ##########################################################
    
    def help_synopsis (self) :
        self.help_para("ws-pinwin.py - an HTTP interface to the ModestMaps map tile composer with support for rendering and plotting markers.\n\n")

    # ##########################################################

    def help_example (self) :
        self.help_header("Example")
        self.help_para("http://127.0.0.1:9999/?provider=MICROSOFT_ROAD&method=extent&bbox=45.482882,%20-73.619899,%2045.532687,%20-73.547801&height=1024&width=1024&marker=roy,45.521375561025756,%20-73.57049345970154&marker=mileend,45.525825499457,%20-73.5989034175872,600,180&marker=cherrier,45.51978191639917,-73.56947422027588&bleed=1")
        self.help_para("Returns a PNG file of a map of Montreal at the appropriate zoom level to display the bounding box in a image 1024 pixels square, with (3) empty pinwin markers.")

    # ##########################################################

    def help_parameters (self) :
        wscompose.handler.help_parameters(self)

        self.help_option('dot', 'Draw a pinwin-style dot (but not the marker) at a given point. You may pass multiple dot arguments, each of which should contain the following comma separated values :', False)
        self.help_option('label', 'A unique string to identify the dot by', True, 1)
        self.help_option('point', 'A comma-separated string containing the latitude and longitude indicating the point where the dot should be placed', True, 1)
        self.help_option('radius', 'The radius, in pixels, of the dot - the default is 18', False, 1)    

        self.help_option('marker', 'Draw a pinwin-style marker at a given point. You may pass multiple marker arguments, each of which should contain the following comma separated values :', False)
        self.help_option('label', 'A unique string to identify the marker by', True, 1)
        self.help_option('point', 'A comma-separated string containing the latitude and longitude indicating the point where the marker should be placed', True, 1)
        self.help_option('dimensions', 'A comma-separated string containing the height and width of the marker canvas - the default is 75 x 75', False, 1)   

        self.help_option('polyline', 'Draw a polyline on the map. Polylines are passed as multiple coordinates (comma-separated latitude and longitude pairs) each separated by a single space. You may pass multiple \'polyline\' arguments. This option is currently experimental and arguments may change.', False)

        self.help_option('convex', 'Draw a polyline representing the convex hull of a collection of points passed in the \'marker\', \'dot\' or \'plot\' arguments (see above). Valid options are, not surprisingly : \'marker\', \'dot\' or \'plot\'; you may pass multiple \'convex\' arguments. This option is currently experimental and arguments may change.', False)
        
        self.help_option('fill', 'A helper argument which if present will cause each marker specified to be filled with the contents of map for the marker\'s coordinates at zoom level 15. The value should be a valid ModestMaps map tile provider.', False)
        
        self.help_option('adjust', 'Adjust the size of the bounding box argument by (n) kilometers; you may want to do this if you have markers positioned close to the sides of your bounding box', False)
        self.help_option('bleed', 'If true, the final image will be enlarged to ensure that all marker canvases are not clipped', False)
        self.help_option('noshadow', 'Do not draw shadows for pinwin markers', False)
        
        self.help_option('filter', 'Filter the map image before any markers are applied. Valid options are :', False)
        self.help_option('atkinson', 'Apply the Atkinson dithering algorithm to the map image', False, 1)        

    # ##########################################################

    def help_notes (self) :
        self.help_header("Notes")        
        self.help_para("The shadows for the markers are stylized by design; especially when they have been repositioned and have very long stems. Not only do they look funny, I've decided I like that they look funny.")
        self.help_para("\"Proper\" shadows rendered in correct perspective are on the list and if you want to help me with the math then they be added sooner still.")

    # ##########################################################

    def help_metadata (self) :
        self.help_header("Metadata")

        self.help_para("Metadata about an image is returned in HTTP headers prefixed with 'X-wscompose-'.")
        self.help_para("For example : ")
        
        self.help_pre("""	HTTP/1.x 200 OK
        Server: BaseHTTP/0.3 Python/2.5
        Date: Sun, 13 Jan 2008 01:08:37 GMT
        Content-Type: image/png
        Content-Length: 1946576
        X-wscompose-Image-Height: 1024
        X-wscompose-Image-Width: 1024
        X-wscompose-Map-Zoom: 14.0
        X-wscompose-Marker-mileend: 336,211,157,-131,600,180
        X-wscompose-Marker-roy: 667,285,629,165,75,75
        X-wscompose-Marker-cherrier: 679,312,641,192,75,75""")

        self.help_para("Most headers are self-explanatory. Markers, dots and plotting coordinates are a little more complicated.")

        self.help_para("The string after 'X-wscompose-darker-' is the label assigned to the marker when the API call was made. The value is a comma separated list interpreted as follows :")

        self.help_para("The first two numbers are the x/y coordinates for the lat/lon.")
        self.help_para("The second two are the x/y coordinates of the top left corner where the actual pinwin content should be pasted.")
        self.help_para("The last pair  are the dimensions of the pinwin content which is sort of redundant unless you are opting for defaults and don't know what to expect.")

        self.help_para("'X-wscompose-dot-' headers return x and y coordinates followed by the dot's radius, in pixels")
        self.help_para("'X-wscompose-plot-' headers return only x and y coordinates")
        
    # ##########################################################

########NEW FILE########
__FILENAME__ = plotting
# -*-python-*-

__package__    = "wscompose/plotting.py"
__version__    = "1.0"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/wscompose"
__date__       = "$Date: 2008/01/04 06:23:46 $"
__copyright__  = "Copyright (c) 2007-2008 Aaron Straup Cope. BSD license : http://www.modestmaps.com/license."

import wscompose
import wscompose.pwmarker
import string
import random
import re

import ModestMaps

# SEE COMMENTS IN markers.py ABOUT VARIABLE NAMES
#
# TO DO (patches are welcome) :
#
# - figure out whether/what code here should be merged
#   with pinwin.py
#
# - make the background for an image with bleeds transparent
#
# - adjust randomly (for overlaps) on the x-axis
#
# - allow for the marker canvas (and cone) to be rotated
#   360 degrees around a point (also to do in marker.py)

class handler (wscompose.handler) :

    def __init__ (self, request, client_address, server) :
        self.__markers__ = {}

        wscompose.handler.__init__(self, request, client_address, server)

    # ##########################################################
    
    def draw_map (self) :

        img = wscompose.handler.draw_map(self)
        img = self.draw_markers(img)

        return img
    
    # ##########################################################

    def sort_markers (self):

        def mysort (x, y) :
            return cmp (y['latitude'], x['latitude'])

        self.ctx['markers'].sort(mysort)
        
    # ##########################################################

    def reload_markers (self) :

        # it's called reload marker because it simply
        # calculates all the coordinates for a marker
        # but does not draw it
        
        for mrk_data in self.ctx['markers'] :

            # please reconcile me with the code
            # in __init__/draw_marker

            w = mrk_data['width']
            h = mrk_data['height']
            a = mrk_data['adjust_cone_height']
            
            mrk = self.load_marker(w, h, a)
            pt = self.latlon_to_point(mrk_data['latitude'], mrk_data['longitude'])
            
            # loc = ModestMaps.Geo.Location(mrk_data['latitude'], mrk_data['longitude'])
            # pt = self.ctx['map'].locationPoint(loc)            
            
            # argh...fix me!

            bleed_x = 0
            bleed_y = 0
            
            mrk_data['x'] = int(pt.x) + bleed_x
            mrk_data['y'] = int(pt.y) + bleed_y

            x1 = mrk_data['x'] - int(mrk.x_offset)
            y1 = mrk_data['y'] - int(mrk.y_offset)

            x2 = x1 + (w + (mrk.x_padding * 2))
            y2 = y1 + (h + (mrk.y_padding * 2))
            
            mrk_data['canvas'] = (x1, y1, x2, y2)
            
    # ##########################################################

    def reposition_markers (self) :
        self.sort_markers()
        return self.__reposition_markers()

    # ##########################################################
    
    def __reposition_markers (self, iterations=1, max_iterations=50) :

        # get some context
        self.reload_markers()
        
        # the number of markers
        count = len(self.ctx['markers'])

        # markers, accounting for 0-based index
        indexes = range(0, count)

        # start from the bottom
        indexes.reverse()

        # happy happy
        try_again = False

        for offset_mrk in range(0, count) : 

            mrk_idx = indexes[offset_mrk]
            current = self.ctx['markers'][mrk_idx]

            next = offset_mrk + 1

            for offset_test in range(next, count) :

                test_idx = indexes[offset_test]
                other = self.ctx['markers'][test_idx]

                overlap = self.does_marker_overlap_marker(current, other)
                
                if overlap != 0 :

                    self.ctx['markers'][test_idx]['adjust_cone_height'] += (overlap + random.randint(10, 100))
                    try_again = True
                    break
            
            if try_again :
                break

        if try_again :
            
            iterations += 1

            # if iterations == max_iterations :
            #     return False
            
            return self.__reposition_markers(iterations)

        return True
    
    # ##########################################################

    def does_marker_overlap_marker(self, current, test) :

        cur_label = current['label']
        test_label = test['label']

        # print "does %s overlap %s" % (cur_label, test_label)
        # print "current %s" % current
        
        # first, ensure that some part of 'current'
        # overlaps 'test' on the x axis

        cur_x1 = current['canvas'][0]
        cur_x2 = current['canvas'][2]
        test_x1 = test['canvas'][0]
        test_x2 = test['canvas'][2]

        # print "\t%s (X) : %s, %s" % (cur_label, cur_x1, cur_x2)
        # print "\t%s (X) : %s, %s" % (test_label, test_x1, test_x2)

        if test_x1 > cur_x2 :
            return 0
        
        if test_x2 < cur_x1 :
            return 0

        cur_y = current['y']
        test_y = test['y']

        cur_cy1 = current['canvas'][1]
        cur_cy2 = current['canvas'][3]

        test_cy1 = test['canvas'][1]
        test_cy2 = test['canvas'][3]

        # do both markers occupy the same space?

        if cur_cy1 == test_cy1 and test_cy2 == cur_cy2 : 
            return cur_cy2 - cur_cy1
        
        # print "%s\t%s\t%s\t%s" % (cur_cy1, cur_cy2, cur_y, cur_label)
        # print "%s\t%s\t%s\t%s" % (test_cy1, test_cy2, test_y, test_label)

        # is the y (lat) position of 'test' somewhere
        # in the space between the y position of 'current'
        # and the bottom of its pinwin canvas?
        
        if cur_cy2 >= test_y :            
            if cur_cy1 <= test_cy2 :

                return test_cy2 - cur_cy1

        # the y (or lat) position for 'test' falls between
        # the canvas of 'current'
        
        if test_y > cur_cy1 :
            if test_cy2 >= cur_cy1 : 
                return test_cy2 - cur_cy1

        # ensure at least a certain amount of
        # space between markers
        
        space = cur_cy1 - test_cy2
        
        if space <= 10 :
            return random.randint(10, 25)
        
        return 0
    
    # ##########################################################
    
    def draw_markers (self, img) :

        self.sort_markers()
            
        for data in self.ctx['markers'] :
            self.draw_shadow(img, data)

        for data in self.ctx['markers'] :
            self.draw_marker(img, data)

        return img
    
    # ##########################################################

    def draw_shadow (self, img, mrk_data, bleed_x=0, bleed_y=0) :

        w = mrk_data['width']
        h = mrk_data['height']
        a = mrk_data['adjust_cone_height']
        
        mrk = self.load_marker(w, h, a)
        
        loc = ModestMaps.Geo.Location(mrk_data['latitude'], mrk_data['longitude'])
        pt = self.ctx['map'].locationPoint(loc)            

        #
        
        mrk_data['x'] = int(pt.x) + bleed_x
        mrk_data['y'] = int(pt.y) + bleed_y

        mx = mrk_data['x'] - int(mrk.x_offset)
        my = mrk_data['y'] - int(mrk.y_offset)

        dx = mx + mrk.x_padding
        dy = my + mrk.y_padding

        #

        shadow = mrk.fh('shadow')

        img.paste(shadow, (mx, my), shadow)
        
        mrk_data['x_fill'] = dx
        mrk_data['y_fill'] = dy        

    # ##########################################################
    
    def draw_marker (self, img, mrk_data, bleed_x=0, bleed_y=0) :

        w = mrk_data['width']
        h = mrk_data['height']
        a = mrk_data['adjust_cone_height']
        
        mrk = self.load_marker(w, h, a)
        
        loc = ModestMaps.Geo.Location(mrk_data['latitude'], mrk_data['longitude'])
        pt = self.ctx['map'].locationPoint(loc)            

        #
        
        mrk_data['x'] = int(pt.x) + bleed_x
        mrk_data['y'] = int(pt.y) + bleed_y

        mx = mrk_data['x'] - int(mrk.x_offset)
        my = mrk_data['y'] - int(mrk.y_offset)
        
        dx = mx + mrk.x_padding
        dy = my + mrk.y_padding

        #

        pinwin = mrk.fh('pinwin')
        img.paste(pinwin, (mx, my), pinwin)
        
        mrk_data['x_fill'] = dx
        mrk_data['y_fill'] = dy        

           
    # ##########################################################
    
    def validate_params (self, params) :
        
        valid  = wscompose.handler.validate_params(self, params)
        
        if not valid :
            return False

        if not params.has_key('marker') :
            self.error(101, "Missing or incomplete parameter : %s" % 'marker')
            return False
            
        return valid

    # ##########################################################
    
    def load_marker (self, w, h, a) :

        key = "%s-%s-%s" % (w, h, a)
        
        if not self.__markers__.has_key(key) :
            mrk = wscompose.pwmarker.PinwinMarker(w, h, a)
            mrk.draw()
            
            self.__markers__[key] = mrk
            
        return self.__markers__[key]

    # ##########################################################

########NEW FILE########
__FILENAME__ = pwcairo
__package__    = "pwmarker/pwcairo.py"
__version__    = "1.0"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/pwmarker"
__date__       = "$Date: 2008/07/24 05:52:38 $"
__copyright__  = "Copyright (c) 2008 Aaron Straup Cope. All rights reserved."
__license__    = "http://www.modestmaps.com/license.txt"

import array
import math
import random
import cairo
import PIL.Image

# http://www.cairographics.org/pycairo/tutorial/
# http://www.tortall.net/mu/wiki/CairoTutorial
# http://www.cairographics.org/manual/cairo-Paths.html#cairo-arc
# http://www.cairographics.org/matrix_transform/

class CairoMarker :

    #
    
    def c__dot (self, ctx='pinwin', *args) :
    
        cr = cairo.Context(self.surface)
        
        cx = self.pt_x
        cy = self.pt_y

        if ctx == 'pinwin' :
            sh_c = (.3, .3, .3)
            dot_c = self.dot_c
        else :
            sh_c = (255, 255, 255)
            dot_c = (255, 255, 255)

        # mock shadow
                
        cr.arc (cx + 1, cy + 1, self.dot_r, 0, 360)            
        cr.set_source_rgb(sh_c[0], sh_c[1], sh_c[2])
        cr.fill()
        
        # dot proper
        
        cr.arc (cx, cy, self.dot_r, 0, 360)                
        cr.set_source_rgb(dot_c[0], dot_c[1], dot_c[2])
        cr.fill()
        
        # donut hole
        
        if ctx == 'pinwin' :
            cr.arc (cx, cy, 2, 0, 360)
            cr.set_source_rgb(255, 255, 255)
            cr.fill()

    #
    
    def crop_marks (self) :

        cr = cairo.Context(self.surface)

        nw_x = self.offset_x
        nw_y = self.offset_y

        ne_x = self.offset_x + self.img_w
        ne_y = self.offset_y

        se_x = self.offset_x + self.img_w
        se_y = self.offset_y + self.img_h

        sw_x = self.offset_x
        sw_y = self.offset_y + self.img_h

        guide = self.padding
        lead = int(guide / 2)
        
        cr.move_to(nw_x - lead, nw_y)
        cr.line_to((nw_x + guide), nw_y)

        cr.move_to(nw_x, (nw_y - lead))
        cr.line_to(nw_x, (nw_y + guide))

        cr.move_to((ne_x + lead), ne_y)
        cr.line_to((ne_x - guide), ne_y)

        cr.move_to(ne_x, (ne_y - lead))
        cr.line_to(ne_x, (ne_y + guide))

        cr.move_to((se_x + lead), se_y)
        cr.line_to((se_x - guide), se_y)

        cr.move_to(se_x, (se_y + lead))
        cr.line_to(se_x, (se_y - guide))

        cr.move_to((sw_x - lead), sw_y)
        cr.line_to((sw_x + guide), sw_y)

        cr.move_to(sw_x, (sw_y + lead))
        cr.line_to(sw_x, (sw_y - guide))

        #

        cr.move_to((self.pt_x - self.dot_r), (self.pt_y - self.dot_r))
        cr.line_to((self.pt_x + self.dot_r), (self.pt_y + self.dot_r))

        cr.move_to((self.pt_x - self.dot_r), (self.pt_y + self.dot_r))
        cr.line_to((self.pt_x + self.dot_r), (self.pt_y - self.dot_r))
        
        #
        
        cr.set_source_rgb(0, 0, 1)
        cr.set_line_width(1)   
        cr.stroke()   
        
    # 
    
    def c__pinwin (self, anchor='bottom', dot_ctx='pinwin', c=(0, 0, 0)) :
        
        self.c__setup(anchor, 'pinwin')
        
        if self.add_dot :
            dot = self.dot(dot_ctx)
                            
        background = self.c__draw(anchor, 'pinwin')
        background.set_source_rgb(255, 255, 255)
        background.fill()

        border = self.c__draw(anchor, 'pinwin')    
        border.set_source_rgb(c[0], c[1], c[2])
        border.set_line_width(self.border_w)

        # to prevent thick borders from exceeding
        # the center of a dot or just spilling off
        # it altogether...
        # http://www.cairographics.org/manual/cairo-cairo-t.html#cairo-set-miter-limit

        border.set_miter_limit(2);
        
        border.stroke()

        if dot_ctx == 'pinwin' and self.add_cropmarks :
            self.crop_marks()

        #

        return self.surface

    #

    def c__shadow (self, anchor='bottom', ctx='shadow', c=(0, 0, 0)) :

        self.c__setup(anchor, ctx)
        
        background = self.c__draw(anchor, ctx)
        background.set_source_rgba(c[0], c[1], c[2])    
        background.fill()

        plain = self.c__cairo2pil(self.surface)
        
        tilted = self.tilt(plain, self.blurry_shadows)
        return self.c__pil2cairo(tilted)

    #

    def c__cartoon_shadow (self, anchor='bottom', dot_ctx='shadow', c=(0, 0, 0)) :

        w = self.offset + self.img_w + (self.padding * 2)
        h = self.offset + self.img_h + (self.padding * 2)
        
        mode = cairo.FORMAT_ARGB32
        self.surface = cairo.ImageSurface (mode, w, h)

        # first draw the canvas and tilt it
        
        background = self.c__draw_canvas()
        background.set_source_rgba(c[0], c[1], c[2])    
        background.fill()

        blur = False

        #
        
        cnv = self.c__cairo2pil(self.surface)
        cnv = self.tilt(cnv, False)
        
        coords = self.calculate_cartoon_anchor_coords(cnv)

        (tmp_w, tmp_h, sh_offset) = coords[0]
        (sha_left, cnv_h) = coords[1]
        (bottom_x, bottom_y) = coords[2]
        (sha_right, cnv_h) = coords[3]
        
        mode = cairo.FORMAT_ARGB32
        self.surface = cairo.ImageSurface (mode, tmp_w, tmp_h)
        cr = cairo.Context(self.surface)
            
        # draw the anchor

        cr.move_to(sha_left, cnv_h)

        cr.line_to(bottom_x, bottom_y)            
        cr.line_to(sha_right, cnv_h)
        cr.line_to(sha_left, cnv_h)

        cr.set_source_rgba(c[0], c[1], c[2])    
        cr.fill()

        # combine the canvas and the anchor
        
        sh = self.c__cairo2pil(self.surface)
        sh.paste(cnv, (sh_offset, 0), cnv)

        # blur

        if not self.blurry_shadows :
            return sh
        
        sh = self.blur(sh)
        return sh
    
    #

    def c__setup (self, anchor, ctx='pinwin') :

        (w, h) = self.calculate_dimensions(anchor, ctx)
        
        mode = cairo.FORMAT_ARGB32
        self.surface = cairo.ImageSurface (mode, w, h)

    #

    def c__draw (self, anchor, ctx):
        return self.c__draw_vertical(ctx)

    #
    
    def c__draw_vertical(self, ctx) :

        # to do : investigate the 'curve_to' method...

        cr = cairo.Context(self.surface)
            
        # top right arc
        # 
        #   *------------------------
        #  *                         \
        # *                           \
        
        x = (self.offset + self.padding)
        y = (self.offset + 0)
        cx = (self.offset + self.img_w + self.padding)
        cy = (self.offset + self.padding)

        cr.move_to(x, y)
        cr.arc(cx, cy, self.corner_r, -math.pi/2, 0)

        # bottom right arc
        # 
        #                                |
        #                                |
        #                               /
        #                              /

        x = (self.offset + self.img_w + (self.padding * 2))
        y = (self.offset + self.img_h + self.padding)
        cx = (self.offset + self.img_w + self.padding)
        cy = (self.offset + self.img_h + self.padding)

        cr.line_to(x, y)
        cr.arc (cx, cy, self.corner_r, 0, math.pi/2)

        # cone
        #
        #                -----------------------------
        #               
        #             
        
        x = (self.offset + self.offset_cone + int(self.anchor_w * .5))
        y = (self.offset + self.img_h + (self.padding * 2))
        cr.line_to(x, y)

        # cone
        #
        #           ==== 
        #          /
        #         /

        x = (self.offset + self.offset_cone)
        y = (self.offset + self.canvas_h)            
        cr.line_to(x, y)

        # cone
        #
        #  ***\
        #      \
        
        x = (self.offset + self.offset_cone - int(self.anchor_w * .5))
        y = (self.offset + self.img_h + (self.padding * 2))
        cr.line_to(x, y)
        
        # bottom left arc
        #
        # \
        #  \
        #   -----
        
        x = (self.offset + self.padding)
        y = (self.offset + self.img_h + (self.padding * 2))
        cx = (self.offset + self.padding)
        cy = (self.offset + self.img_h + self.padding)

        cr.line_to(x, y)
        cr.arc (cx, cy, self.corner_r, math.pi/2, math.pi)
    
        # top left arc
        #
        #    /
        #   /
        #   |
        #   |
        
        x = (self.offset + 0)
        y = (self.offset + self.padding)
        cx = (self.offset + self.padding)
        cy = (self.offset + self.padding)

        cr.line_to(x, y)
        cr.arc (cx, cy, self.corner_r, math.pi, -math.pi/2)

        #

        return cr

    #

    def c__draw_canvas(self) :

        cr = cairo.Context(self.surface)
            
        # top right arc
        # 
        #   *------------------------
        #  *                         \
        # *                           \
        
        x = (self.offset + self.padding)
        y = (self.offset + 0)
        cx = (self.offset + self.img_w + self.padding)
        cy = (self.offset + self.padding)

        cr.move_to(x, y)
        cr.arc(cx, cy, self.corner_r, -math.pi/2, 0)

        # bottom right arc
        # 
        #                                |
        #                                |
        #                               /
        #                              /

        x = (self.offset + self.img_w + (self.padding * 2))
        y = (self.offset + self.img_h + self.padding)
        cx = (self.offset + self.img_w + self.padding)
        cy = (self.offset + self.img_h + self.padding)

        cr.line_to(x, y)
        cr.arc (cx, cy, self.corner_r, 0, math.pi/2)

        # bottom
        #
        #  -----------------------------
        
        x = (self.offset + self.padding)
        y = (self.offset + self.img_h + (self.padding * 2))        
        cr.line_to(x, y)
        
        # bottom left arc
        #
        # \
        #  \
        #   -----
        
        x = (self.offset + self.padding)
        y = (self.offset + self.img_h + (self.padding * 2))
        cx = (self.offset + self.padding)
        cy = (self.offset + self.img_h + self.padding)

        cr.line_to(x, y)
        cr.arc (cx, cy, self.corner_r, math.pi/2, math.pi)
    
        # top left arc
        #
        #    /
        #   /
        #   |
        #   |
        
        x = (self.offset + 0)
        y = (self.offset + self.padding)
        cx = (self.offset + self.padding)
        cy = (self.offset + self.padding)

        cr.line_to(x, y)
        cr.arc (cx, cy, self.corner_r, math.pi, -math.pi/2)

        #

        return cr

    #        
    
    def c__pil2cairo(self, im, mode=None) :

        if not mode :
            mode = cairo.FORMAT_ARGB32
            
        data = im.tostring()
        a = array.array('B', data)

        (w,h) = im.size
        return cairo.ImageSurface.create_for_data (a, mode, w, h)

    #
    
    def c__cairo2pil(self, surface, mode='RGBA') :

        width = surface.get_width()
        height = surface.get_height()
        
        return PIL.Image.frombuffer(mode, (width, height), surface.get_data(), "raw", mode, 0, 1)

########NEW FILE########
__FILENAME__ = pwcommon
__package__    = "pwmarker/pwcommon.py"
__version__    = "1.0"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/pwmarker"
__date__       = "$Date: 2008/07/23 16:28:26 $"
__copyright__  = "Copyright (c) 2008 Aaron Straup Cope. All rights reserved."
__license__    = "http://www.modestmaps.com/license.txt"

import math

import PIL.Image
import PIL.ImageDraw

class Common :

    def draw (self, anchor='bottom') :

        pw = self.generate_pinwin(anchor)
        sh = self.generate_shadow(anchor)

        sh = self.position_shadow(pw, sh)
        
        for ctx in self.rendered.keys() :
            mask = self.generate_mask(anchor, ctx)
        
            if ctx == 'pinwin' :
                im = self.render_pinwin(pw, mask)
            elif ctx == 'shadow' :
                im = self.render_shadow(pw, sh, mask)        
            else :
                im = self.render_all(pw, sh, mask)   

            if self.render_engine == 'pil' :
                im = self.p__antialias(im)
                
            self.rendered[ctx] = im

    # 
    
    def generate_pinwin (self, anchor='bottom', dot_ctx='pinwin', *args) :

        key = "%s-%s-%s" % (anchor, dot_ctx, str(args))

        if self.pinwin_cache.has_key(key) :
            return self.pinwin_cache[key]

        #
        
        if self.render_engine == 'cairo' :

            pw = self.c__pinwin(anchor, dot_ctx, *args)       
            pw = self.c__cairo2pil(pw)        
        else :
            pw = self.p__pinwin(anchor, dot_ctx, *args)

        #
        
        self.pinwin_cache[key] = pw
        return pw
        
    #
    
    def generate_shadow (self, anchor='bottom', dot_ctx='shadow', *args) :

        # not clear whether caching is actually
        # necessary or useful here ...
        
        key = "%s-%s-%s" % (anchor, dot_ctx, str(args))

        if self.cartoon_shadows :
            key += "-cartoon"

        if self.shadow_cache.has_key(key) :
            return self.shadow_cache[key]

        #
        
        if self.render_engine == 'cairo' :

            if self.cartoon_shadows :
                sh = self.c__cartoon_shadow(anchor, dot_ctx, *args)
            else :
                sh = self.c__shadow(anchor, dot_ctx, *args)
                sh = self.c__cairo2pil(sh)

        else :
            if self.cartoon_shadows :
                sh = self.p__cartoon_shadow(anchor, dot_ctx, *args)
            else :
                sh = self.p__shadow(anchor, dot_ctx, *args)            

        #
        
        self.shadow_cache[key] = sh
	return sh

    #

    def generate_mask (self, anchor='bottom', ctx='all') :

        dot_ctx = "mask-%s" % ctx

        pw_c = (255, 255, 255)

        if self.render_engine == 'cairo' :
            sh_c = (.65, .65, .65)
        else :
            sh_c = (130, 130, 130)
        
        pw = self.generate_pinwin(anchor, dot_ctx, pw_c)
        sh = self.generate_shadow(anchor, dot_ctx, sh_c)
        
        (pww, pwh) = pw.size
        (shw, shh) = sh.size
        
        w = max(pww, shw)
        h = max(pwh, shh)

        if ctx == 'pinwin' :
            w = pww
            h = pwh

        im = PIL.Image.new('L', (w, h))
        dr = PIL.ImageDraw.Draw(im)

        if ctx != 'pinwin' : 
            shx = 3
            shy = h - shh

            # ugly ugly hack...please to track down
            # how not to need to do this...
            
            if self.add_dot :
                if self.cartoon_shadows :
                    shy -= int(self.dot_r * 1)
                else :
                    shy -= int(self.dot_r * 1.5)
                    shx -= int(self.dot_r * .5)
                    
            im.paste(sh, (shx, shy), sh)
            
        if ctx != 'shadow' :
            im.paste(pw, (1, 1), pw)
                
        return im

    #

    def tilt(self, pil_im, blur=True):

        sh = self.p__tilt(pil_im, blur)

        if blur == True :
            sh = self.blur(sh)

        return sh

    #
    
    def blur(self, pil_im) :
        return self.p__blur(pil_im)
    
    #

    def dot (self, ctx='pinwin', *args) :

        if self.render_engine == 'cairo' :
            return self.c__dot(ctx, args)
        else :
            return self.p__dot(ctx, *args)
        
    #
    
    def calculate_dimensions (self, anchor='bottom', ctx='pinwin') :

        if not self.border_c :
            self.border_c = (0, 0, 0)
            
        if not self.border_w :
            self.border_w = 2

        self.offset = int(math.ceil(self.border_w / 2))
        
        self.padding = int(min(self.img_w, self.img_h) * .1)

        if self.padding < 15 :
            self.padding = 15
        elif self.padding > 25 : 
            self.padding = 20
        else :
            pass

        self.corner_r = self.padding
        
        self.canvas_w = self.offset + self.border_w + self.img_w + (self.padding * 2)
        self.canvas_h = self.offset + self.img_h + (self.padding * 2) + self.anchor_h

        self.offset_x = self.offset + self.padding
        self.offset_y = self.offset + self.padding
            
        self.offset_cone = int(self.canvas_w * .35)

        if self.anchor_w > int(self.canvas_w / 2) :
            self.anchor_w = int(self.canvas_w / 3)

        h = self.canvas_h

        if ctx == 'pinwin' and self.add_dot :
            h += int(self.dot_r * 2)
            
        self.pt_x = self.offset + self.offset_cone
        self.pt_y = self.offset + self.img_h + (self.padding * 2) + self.anchor_h

        # legacy crap (see above)
        # note the +1 ... not sure, but it's necessary
        
        self.x_padding = self.offset + self.padding + 1
        self.y_padding = self.offset + self.padding + 1
        self.x_offset = self.pt_x
        self.y_offset = self.pt_y

        return (self.canvas_w, h)

    #

    def calculate_cartoon_anchor_coords (self, tilted_cnv) :

        (cnv_w,cnv_h) = tilted_cnv.size

        key = "%s-%s" % (cnv_w, cnv_h)

        if self.cartoon_anchor_cache.has_key(key) :
            return self.cartoon_anchor_cache[key]
        
        #
        
        w = self.offset + self.img_w + (self.padding * 2)
        h = self.offset + self.img_h + (self.padding * 2)

        sh_offset = int(w * .2)
        sh_anchor_h = int(self.anchor_h * .9)

        sh_anchor_w = int(self.anchor_w * .9)
        
        diff = self.anchor_h - sh_anchor_h
        cnv_half = int(cnv_h / 2)

        # for pinwins with insanely tall anchors
        # 90% may be larger than the canvas' height
        # which just looks weird

        if sh_anchor_h > cnv_h :
            sh_anchor_h = self.anchor_h - cnv_half

        # but we also want to make sure that shadows
        # for pinwins with short stubby anchors don't
        # start flush with the bottom of the canvas...
        # these are "cartoon" shadows after all so a
        # certain amount of artistic license is allowed
        
        elif diff < int(cnv_h / 4) :

            pw_cnv_h = (self.img_h + (self.padding * 2))
            
            if self.anchor_h < int(pw_cnv_h / 2) :
                sh_anchor_h = int(self.anchor_h / 2)
            else :
                sh_anchor_h = self.anchor_h - int(cnv_h / 4)
            
        else :
            pass
            
        # set up the dimensions for the image we're going to
        # combine the tilted canvas and anchor on
        
        tmp_w = cnv_w + sh_offset
        tmp_h = cnv_h + sh_anchor_h

        # figure out the coordinates for the anchor
        
        pwa_left = (self.offset + self.offset_cone - int(self.anchor_w * .5))
        pwa_right = pwa_left + self.anchor_w
        
        sha_left = pwa_left + sh_offset
        sha_right = sha_left + sh_anchor_w
        
        bottom_x = self.offset + self.offset_cone - self.border_w
        bottom_y = tmp_h

        # we don't draw the do because we'll never see it
        # but we do need to consider it

        if self.add_dot :
            bottom_y = bottom_y - self.dot_r

        if self.blurry_shadows :
            bottom_y += int(self.dot_r * 2.5)
            
        coords = ((tmp_w, tmp_h, sh_offset),
                  (sha_left, cnv_h),
                  (bottom_x, bottom_y),
                  (sha_right, cnv_h))
        
        self.cartoon_anchor_cache[key] = coords
        return coords
    
    #
    
    def position_shadow (self, pw, sh) :

        (pww, pwh) = pw.size
        (shw, shh) = sh.size

        w = max(pww, shw)
        h = max(pwh, shh)

        im = PIL.Image.new('RGBA', (w, h))
        dr = PIL.ImageDraw.Draw(im)

        shx = 3
        shy = h - shh

        if self.add_dot :
            shy -= int(self.dot_r)
        
        im.paste(sh, (shx, shy), sh)
        return im
    
    #

    def render_all (self, pw, sh, mask) :

        im = self.position_shadow(pw, sh)
        im.paste(pw, (1, 1), pw)
        
        im.putalpha(mask)
    	return im

    #
    
    def render_pinwin (self, pw, mask) :

	(w, h) = pw.size
        
        im = PIL.Image.new('RGBA', (w, h))
        dr = PIL.ImageDraw.Draw(im)

        im.paste(pw, (1, 1), pw)
        im.putalpha(mask)
    	return im

    #

    def render_shadow (self, pw, sh, mask) :

        im = self.position_shadow(pw, sh)
        im.putalpha(mask)
    	return im
            
    #

    def save (self, path, ctx='all') :
        if not self.rendered.has_key(ctx) :
            return None
        
        self.rendered[ctx].save(path)

    # backwards compatibility with (ws-modestmaps/markers.py)
    
    def fh (self, ctx='all') :
        if not self.rendered.has_key(ctx) :
            return None
        
        return self.rendered[ctx]

    # 

########NEW FILE########
__FILENAME__ = pwpil
__package__    = "pwmarker/pwpil.py"
__version__    = "1.0"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/pwmarker"
__date__       = "$Date: 2008/07/24 05:52:38 $"
__copyright__  = "Copyright (c) 2008 Aaron Straup Cope. All rights reserved."
__license__    = "http://www.modestmaps.com/license.txt"

import math

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFilter

class PILMarker :

    #
    
    def p__dot (self, ctx='pinwin', dr=None) :
    
        # dr should never be None, it's just a
        # hack to make python stop whinging...
        
        x = self.pt_x + 1
        y = self.pt_y + 1
        
        x1 = x - self.dot_r
        y1 = y - self.dot_r
        x2 = x + self.dot_r
        y2 = y + self.dot_r

        if ctx.startswith('mask-') :
            sh_c = (255, 255, 255)
            dot_c = (255, 255, 255)
        else :
            sh_c = (42, 42, 42)            
            dot_c = (255, 0, 132)

	# mock shadow
        dr.ellipse((x1 + 1 , y1 + 2, x2 + 1, y2 + 2), fill=sh_c)        

	# the dot
        dr.ellipse((x1, y1, x2, y2), fill=dot_c)

        # no donut hole for PIL

    # 
    
    def p__pinwin(self, anchor='bottom', dot_ctx='pinwin', fill='white') :

        (w, h) = self.calculate_dimensions(anchor)

        # to prevent the de-facto border (artifacting)
        # from being cropped when a pinwin is rendered
        # without its shadow
        
        w += 1
        
        im = PIL.Image.new('RGBA', (w, h))
        
        coords = self.p__coords()
        return self.p__draw_pinwin(im, coords, dot_ctx, fill)
        
    #

    def p__draw_pinwin (self, im, coords, dot_ctx='pinwin', fill='white') :

        dr = PIL.ImageDraw.Draw(im)
        
        if self.add_dot and (dot_ctx != 'shadow' and dot_ctx != 'mask-shadow') :
            self.dot(dot_ctx, dr)

        dr.polygon(coords, fill=fill)

        # top left
        
        x1 = self.offset
        y1 = self.offset
        x2 = self.offset + self.padding * 2
        y2 = self.offset + self.padding * 2
        
        dr.pieslice((x1, y1, x2, y2), 180, 270, fill=fill)

        # bottom left
        
        x1 = self.offset
        y1 = self.offset + self.img_h 
        x2 = self.offset + self.padding * 2
        y2 = self.offset + (self.padding * 2) + self.img_h 
        
        dr.pieslice((x1, y1, x2, y2), 90, 180, fill=fill)

        # top right
        
        x1 = self.offset + self.img_w
        y1 = self.offset
        x2 = self.offset + self.img_w + (self.padding * 2)
        y2 = self.offset + (self.padding * 2)

        dr.pieslice((x1, y1, x2, y2), 270, 0, fill=fill)

        # bottom right
        
        x1 = self.offset + self.img_w
        y1 = self.offset + self.img_h
        x2 = self.offset + self.img_w + (self.padding * 2)
        y2 = self.offset + self.img_h + (self.padding * 2)

        dr.pieslice((x1, y1, x2, y2), 0, 90, fill=fill)
        return im
        
    #
    
    def p__shadow (self, anchor, dot_ctx, fill='black') :
        sh = self.p__pinwin(anchor, dot_ctx, fill)
        return self.tilt(sh, self.blurry_shadows)

    #
    
    def p__cartoon_shadow (self, anchor, dot_ctx, fill='black') :

        # make the canvas

        w = self.offset + self.img_w + (self.padding * 2)
        h = self.offset + self.img_h + (self.padding * 2)
        
        cnv = PIL.Image.new('RGBA', (w, h))
        coords = self.p__cartoon_shadow_coords()

        blur = False
        
        cnv = self.p__draw_pinwin(cnv, coords, dot_ctx, fill)
        cnv = self.tilt(cnv, blur)    
        
        coords = self.calculate_cartoon_anchor_coords(cnv)

        (w, h, sh_offset) = coords[0]
        (sha_left, cnv_h) = coords[1]
        (bottom_x, bottom_y) = coords[2]
        (sha_right, cnv_h) = coords[3]
                
        sh = PIL.Image.new('RGBA', (w, h))
        sh.paste(cnv, (sh_offset, 0), cnv)
        
        dr = PIL.ImageDraw.Draw(sh)
                
        anchor = [
            (sha_left, cnv_h),
            (bottom_x, bottom_y),        
            (sha_right, cnv_h),
            (sha_left, cnv_h),            
            ]

        dr.polygon(anchor, fill=fill)
        
        # dot

        self.dot('shadow', dr)
    
        # blur!

        if not self.blurry_shadows :
            return sh
        
        return self.p__blur(sh)
    
    #

    def p__coords (self) :

        #
        #    startx, starty
        #
        #      nwa ------------- nea
        #      /                   \ 
        #    nwb                   neb   
        #    |                       |
        #    |                       |
        #    swb                   seb
        #      \   cna   cnc       /
        #      swa --/ | /------ sea
        #             |
        #            |
        #           |
        #          |
        #         cnb
        #
        #                  endx, endy
        #
        # The rounded corners get bolted on after the
        # fact - this is dumb and if I can ever find
        # docs/examples for PIL's ImagePath stuff then
        # I will use that instead...
        
        nwa_x = self.offset + self.padding
        nwa_y = self.offset

        nea_x = self.offset + self.padding + self.img_w
        nea_y = self.offset

        neb_x = self.offset + self.img_w + (self.padding * 2)
        neb_y = self.offset + self.padding

        seb_x = self.offset + self.img_w + (self.padding * 2)
        seb_y = self.offset + self.img_h + self.padding

        sea_x = self.offset + self.img_w + self.padding
        sea_y = self.offset + self.img_h + (self.padding * 2)

        cnc_x = self.offset + self.offset_cone + int(self.anchor_w * .5)
        cnc_y = self.offset + self.img_h + (self.padding * 2)

        cnb_x = self.offset + self.offset_cone
        cnb_y = self.offset + self.canvas_h

        cna_x = self.offset + self.offset_cone - int(self.anchor_w * .5)
        cna_y = self.offset + self.img_h + (self.padding * 2)
        
        swa_x = self.offset + self.padding
        swa_y = self.offset + self.img_h + (self.padding * 2)

        swb_x = self.offset
        swb_y = self.offset + self.img_h + self.padding

        nwb_x = self.offset
        nwb_y = self.offset + self.padding

        frame = [(nwa_x, nwa_y),
                  (nea_x, nea_y), (neb_x, neb_y),
                  (seb_x, seb_y), (sea_x, sea_y),
                  (cnc_x, cnc_y), (cnb_x, cnb_y),
                  (cna_x, cna_y), (swa_x, swa_y),
                  (swb_x, swb_y), (nwb_x, nwb_y),
                  (nwa_x, nwa_y)]

        return frame

    #
    
    def p__cartoon_shadow_coords (self) :
        
        nwa_x = self.offset + self.padding
        nwa_y = self.offset

        nea_x = self.offset + self.padding + self.img_w
        nea_y = self.offset

        neb_x = self.offset + self.img_w + (self.padding * 2)
        neb_y = self.offset + self.padding

        seb_x = self.offset + self.img_w + (self.padding * 2)
        seb_y = self.offset + self.img_h + self.padding

        sea_x = self.offset + self.img_w + self.padding
        sea_y = self.offset + self.img_h + (self.padding * 2)
        
        swa_x = self.offset + self.padding
        swa_y = self.offset + self.img_h + (self.padding * 2)

        swb_x = self.offset
        swb_y = self.offset + self.img_h + self.padding

        nwb_x = self.offset
        nwb_y = self.offset + self.padding

        frame = [(nwa_x, nwa_y),
                 (nea_x, nea_y),
                 (neb_x, neb_y),
                 (seb_x, seb_y),
                 (sea_x, sea_y),
                 (swa_x, swa_y),                 
                 (swb_x, swb_y),
                 (nwb_x, nwb_y),
                 (nwa_x, nwa_y)]

        return frame
    
    #
    
    def p__tilt(self, pil_im, blur=True) :

        # foo is to remind me that math is hard...
        
        foo = 3.75
        
        (iw, ih) = pil_im.size

        iw2 = int(float(ih) * .45) + iw
        ih2 = int(ih / foo)

        bar = int(float(ih2) * 1.6)

        a = 1
        b = math.tan(45)
        c = -bar
        d = 0
        e = foo
        f = 0
        g = 0
        h = 0
        
        data = (a, b, c, d, e, f, g, h)

        return pil_im.transform ((iw2,ih2), PIL.Image.PERSPECTIVE, data, PIL.Image.BILINEAR)

    #
    
    def p__blur(self, pil_im, iterations=5) :

        (w, h) = pil_im.size

        # ensure some empty padding so the blurring
        # doesn't create butt ugly lines at the top
        # and bottom
        
        h+= 20
        
        im = PIL.Image.new('RGBA', (w, h))
        dr = PIL.ImageDraw.Draw(im)

        im.paste(pil_im, (0, 10), pil_im)
        
        for i in range(1, iterations) :
            im = im.filter(PIL.ImageFilter.BLUR)

        return im    

    #

    def p__antialias(self, im) :

        scale = 4
        sz = im.size
        im = im.resize((sz[0] * scale, sz[1] * scale),  PIL.Image.NEAREST)
        im = im.resize(sz, PIL.Image.ANTIALIAS)

        return im

########NEW FILE########
__FILENAME__ = validate
# -*-python-*-

__version__    = "1.1"
__author__     = "Aaron Straup Cope"
__url__        = "http://www.aaronland.info/python/wscompose"
__date__       = "$Date: 2008/01/04 06:23:46 $"
__copyright__  = "Copyright (c) 2007-2008 Aaron Straup Cope. BSD license : http://www.modestmaps.com/license."

import re
import string
import urlparse

class validate :

    def __init__ (self) :

        self.re = {
            'coord' : re.compile(r"^-?\d+(?:\.\d+)?$"),
            'adjust' : re.compile(r"^(\d+(?:\.\d*)?|\d*?\.\d+)$"),
            'num' : re.compile(r"^\d+$"),
            'provider' : re.compile(r"^(\w+)$"),
            'label' : re.compile(r"^(?:[a-z0-9-_\.]+)$"),
            'hull' : re.compile(r"^(marker|dot|plot)$")   
            }

    # ##########################################################
    
    def regexp (self, label, string) :

        if not self.re.has_key(label) :
            return False

        return self.re[label].match(string)

    # ##########################################################

    def ensure_args (self, args, required) :

        for i in required :

            if not args.has_key(i) :
                raise Exception, "Required argument %s missing" % i
            
        return True

    # ##########################################################
    
    def bbox (self, input) :

        bbox = input.split(",")
        
        if len(bbox) != 4 :
            raise Exception, "Missing or incomplete %s parameter" % 'bbox'
        
        bbox = map(string.strip, bbox)
        
        for pt in bbox :
            if not self.regexp('coord', pt) :
                raise Exception, "Not a valid lat/long : %s" % pt
            
        return map(float, bbox)

    # ##########################################################

    def bbox_adjustment (self, input) :

        if not self.regexp('adjust', str(input)) :
            raise Exception, "Not a valid adjustment %s " % input

        return float(input)
    
    # ##########################################################

    def latlon (self, input) :

        if not self.regexp('coord', input) :
            raise Exception, "Not a valid lat/long : %s" % input

        return float(input)

    # ##########################################################

    def zoom (self, input) :
        return self.__num(input)

    # ##########################################################

    def dimension (self, input) :
        return self.__num(input)

    # ##########################################################

    def radius (self, input) :
        return self.__num(input)

    # ##########################################################

    def provider (self, input) :

        if input.startswith('http://'):
            # probably a URI template thing, let it slide
            return input
        
        input = input.upper()

        if not self.regexp('provider', input) :
            raise Exception, "Not a valid provider : %s" % input

        return input

    # ###########################################################
    
    def marker_label (self, input) :

        if not self.regexp('label', input) :
            raise Exception, "Not a valid marker label"

        return unicode(input)
    
    # ##########################################################

    def markers (self, markers) :

        valid = []

        for pos in markers :

            marker_data = {'width':75, 'height':75, 'adjust_cone_height' : 0}
            
            details = pos.split(",")
            details = map(string.strip, details)
            
            if len(details) < 3 :
                raise Exception, "Missing or incomplete %s parameter : %s" % ('marker', pos)

            #
            # Magic center/zoom markers
            #
            
            if details[0] == 'center' :

                marker_data['fill'] = 'center'
                marker_data['label'] = 'center'
                
                try : 
                    marker_data['provider'] = self.provider(details[1])
                except Exception, e :
                    raise Exception, e 

                try : 
                    marker_data['zoom'] = self.zoom(details[2])
                except Exception, e :
                    raise Exception, e 

            #
            # Pinwin name/label
            #
            
            else :
            
                try :
                    marker_data['label'] = self.marker_label(details[0])
                except Exception, e :
                    raise Exception, e

                # Pinwin location
            
                try :
                    marker_data['latitude'] = self.latlon(details[1])
                except Exception, e :
                    raise Exception, e

                try :
                    marker_data['longitude'] = self.latlon(details[2])
                except Exception, e :
                    raise Exception, e

            #
            # Shared
            #
            
            #
            # Pinwin size
            #
            
            if len(details) > 3 :

                if len(details) < 4 :
                    raise Exception, "Missing height parameter"
                
                try :
                    marker_data['width'] = self.dimension(details[3])
                except Exception, e :
                    raise Exception, e
                
                try : 
                    marker_data['height'] = self.dimension(details[4])
                except Exception, e :
                    raise Exception, e
            
            # URI for content to fill the pinwin with
            
            if len(details) > 5 :

                try :
                    parts = urlparse.urlparse(details[5])
                except Exception, e :
                    raise Exception, e

                if parts[1] == '' and parts[0] != 'file' :
                    raise Exception, "Unknown URL"
                
                marker_data['fill'] = details[5]

            # Done

            valid.append(marker_data)

        return valid

    # ##########################################################

    def plots (self, plots) :

        valid = []

        for pos in plots :

            details = pos.split(",")
            details = map(string.strip, details)
            
            if len(details) < 3 :
                raise Exception, "Missing or incomplete %s parameter : %s" % ('plot', pos)

            data = {}
            
            try :
                data['label'] = self.marker_label(details[0])
            except Exception, e :
                raise Exception, e

            # Pinwin location
            
            try :
                data['latitude'] = self.latlon(details[1])
            except Exception, e :
                raise Exception, e

            try :
                data['longitude'] = self.latlon(details[2])
            except Exception, e :
                raise Exception, e

            valid.append(data)

        return valid
            
    # ##########################################################

    def dots (self, dots) :

        valid = []

        for pos in dots :

            details = pos.split(",")
            details = map(string.strip, details)
            cnt = len(details)
            
            if cnt < 3 :
                raise Exception, "Missing or incomplete %s parameter : %s" % ('dot', pos)

            data = {}
            
            try :
                data['label'] = self.marker_label(details[0])
            except Exception, e :
                raise Exception, e

            # Pinwin location
            
            try :
                data['latitude'] = self.latlon(details[1])
            except Exception, e :
                raise Exception, e

            try :
                data['longitude'] = self.latlon(details[2])
            except Exception, e :
                raise Exception, e

            #
            
            if cnt > 3 :
                try :
                    data['radius'] = self.radius(details[3])
                except Exception, e :
                    raise Exception, e

            else :
                data['radius'] = 18

            #
            
            if cnt > 4 :
                #  fix me
                pass
            else :
                data['colour'] = 'red'

            #

            valid.append(data)

        return valid
            
    # ##########################################################

    def polylines (self, lines) :

        valid = []
        
        for poly in lines :

            points = []
            
            for pt in poly.split(" ") :
            
                coord = pt.split(",")

                if len(coord) != 2 :
                    raise Exception, "Polyline coordinate missing data"
                
                (lat, lon) = map(string.strip, coord) 
                
                lat = self.latlon(lat)
                lon = self.latlon(lon)

                points.append({'latitude':lat, 'longitude':lon})

            valid.append(points)
            
        return valid
    
    # ##########################################################    

    def convex (self, hulls) :
        
        valid = []

        for label in hulls :
            
            if not self.regexp('hull', label)  :
                raise Exception, "Unknown marker type for convex hulls"

            valid.append(label)

        return valid

    # ##########################################################

    def json_callback(self, func) :

        if not self.re['label'].match(func) :
            raise Exception, "Invalid JSON callback name"
        
        return func
    
    # ##########################################################
    
    def __num (self, input) :

        if not self.regexp('num', input) :
            raise Exception, "Not a valid number : %s" % p

        return int(input)

    # ##########################################################

########NEW FILE########
