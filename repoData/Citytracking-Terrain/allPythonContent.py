__FILENAME__ = tile-out
from sys import argv
from urlparse import urlparse
from os.path import splitext

from ModestMaps.Core import Coordinate, Point
from ModestMaps.OpenStreetMap import Provider
from TileStache.Geography import SphericalMercator

mercator = SphericalMercator()
zoom, scale = 6, 611.496226
output_dir = argv[1]

hrefs = ['http://b.tile.openstreetmap.org/6/0/20.png',
         'http://a.tile.openstreetmap.org/6/4/13.png',
         'http://a.tile.openstreetmap.org/6/20/28.png',
         'http://b.tile.openstreetmap.org/6/22/22.png',
         'http://c.tile.openstreetmap.org/6/15/28.png']

paths = [urlparse(href).path for href in hrefs]
tiles = [splitext(path)[0].lstrip('/') for path in paths]
values = [map(int, tile.split('/', 2)) for tile in tiles]
rows, cols = zip(*[(y, x) for (z, x, y) in values])

rows_cols = []

for row in range(min(rows), max(rows) + 1):
    for col in range(min(cols), max(cols) + 1):
        rows_cols.append((row, col))

for (index, (row, col)) in enumerate(rows_cols):
    coord = Coordinate(row, col, zoom)

    filename = '%(output_dir)s/%(zoom)d-%(col)d-%(row)d.tif' % locals()
    print 'echo', '-' * 80, index, 'of', len(rows_cols), filename

    ll = mercator.coordinateProj(coord.down())
    ur = mercator.coordinateProj(coord.right())
    
    print 'gdalwarp',
    print '-t_srs "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over"',
    print '-te', ll.x, ll.y, ur.x, ur.y,
    print '-tr', scale, scale,
    print '-tps -r cubicspline',
    print '-co COMPRESS=JPEG',
    print 'landcover-1km-to-merc.vrt',
    print filename

########NEW FILE########
__FILENAME__ = mapping
from imposm.mapping import Options, Polygons, LineStrings, PseudoArea, GeneralizedTable, meter_to_mapunit

def zoom_threshold(zoom):
    return meter_to_mapunit(20037508.0 * 2 / (2**(8 + zoom)))

db_conf = Options(
    db='terrain',
    host='localhost',
    port=5432,
    user='terrain',
    password='',
    sslmode='allow',
    prefix='osm_new_',
    proj='epsg:900913',
)



# WHERE leisure IN ('park', 'water_park', 'marina', 'nature_reserve',
# 	                                   'playground', 'garden', 'common')
# 	                    OR amenity IN ('graveyard')
# 	                    OR landuse IN ('cemetery')
# 	                    OR leisure IN ('sports_centre', 'golf_course', 'stadium',
# 	                                   'track', 'pitch')
# 	                    OR landuse IN ('recreation_ground')
# 	                    OR landuse IN ('forest', 'wood')
# 	                 
# 	                 ORDER BY ST_Area(way) DESC

green_areas = Polygons(
    name = 'green_areas',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'leisure': ('park', 'water_park', 'marina', 'nature_reserve', 'playground', 'garden', 'common', 'sports_centre', 'golf_course', 'stadium', 'track', 'pitch'),
        'landuse': ('cemetery', 'park', 'water_park', 'marina', 'nature_reserve', 'playground', 'garden', 'common', 'forest', 'wood'),
        'amenity': ('graveyard')
    }
)

green_areas_z13 = GeneralizedTable(
    name = 'green_areas_z13',
    tolerance = zoom_threshold(13),
    origin = green_areas,
)

green_areas_z10 = GeneralizedTable(
    name = 'green_areas_z10',
    tolerance = zoom_threshold(10),
    origin = green_areas_z13,
)



# WHERE amenity IN ('school', 'college', 'university', 'bus_station',
#                   'ferry_terminal', 'hospital', 'kindergarten',
#                   'place_of_worship', 'public_building', 'townhall')
#    OR landuse IN ('industrial', 'commercial')

grey_areas = Polygons(
    name = 'grey_areas',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'amenity': ('school', 'college', 'university', 'bus_station', 'ferry_terminal', 'hospital', 'kindergarten', 'place_of_worship', 'public_building', 'townhall'),
        'landuse': ('industrial', 'commercial')
    }
)

grey_areas_z13 = GeneralizedTable(
    name = 'grey_areas_z13',
    tolerance = zoom_threshold(13),
    origin = grey_areas,
)

grey_areas_z10 = GeneralizedTable(
    name = 'grey_areas_z10',
    tolerance = zoom_threshold(10),
    origin = grey_areas_z13,
)



# WHERE building IS NOT NULL

buildings = Polygons(
    name = 'buildings',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'building': ('__any__',)
    }
)

buildings_z13 = GeneralizedTable(
    name = 'buildings_z13',
    tolerance = zoom_threshold(13),
    origin = buildings,
)

buildings_z10 = GeneralizedTable(
    name = 'buildings_z10',
    tolerance = zoom_threshold(10),
    origin = buildings_z13,
)



# WHERE aeroway IS NOT NULL

aeroways = LineStrings(
    name = 'aeroways',
    mapping = {
        'aeroway': ('__any__',)
    }
)

aeroways_z13 = GeneralizedTable(
    name = 'aeroways_z13',
    tolerance = zoom_threshold(13),
    origin = aeroways,
)

aeroways_z10 = GeneralizedTable(
    name = 'aeroways_z10',
    tolerance = zoom_threshold(10),
    origin = aeroways_z13,
)



# WHERE waterway IS NOT NULL

waterways = LineStrings(
    name = 'waterways',
    mapping = {
        'waterway': ('__any__',)
    }
)

waterways_z13 = GeneralizedTable(
    name = 'waterways_z13',
    tolerance = zoom_threshold(13),
    origin = waterways,
)

waterways_z10 = GeneralizedTable(
    name = 'waterways_z10',
    tolerance = zoom_threshold(10),
    origin = waterways_z13,
)

########NEW FILE########
__FILENAME__ = water-mapping
from imposm.mapping import Options, Polygons, LineStrings, PseudoArea, GeneralizedTable, meter_to_mapunit

def zoom_threshold(zoom):
    return meter_to_mapunit(20037508.0 * 2 / (2**(8 + zoom)))

db_conf = Options(
    db='terrain',
    host='localhost',
    port=5432,
    user='terrain',
    password='',
    sslmode='allow',
    prefix='osm_new_',
    proj='epsg:900913',
)



# WHERE "natural" IN ('water', 'bay')
# 	 OR waterway = 'riverbank'
# 	 OR landuse = 'reservoir'

water_areas = Polygons(
    name = 'water_areas',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'natural': ('water', 'bay'),
        'waterway': ('riverbank',),
        'landuse': ('reservoir',)
    }
)

water_areas_z13 = GeneralizedTable(
    name = 'water_areas_z13',
    tolerance = zoom_threshold(13),
    origin = water_areas,
)

water_areas_z10 = GeneralizedTable(
    name = 'water_areas_z10',
    tolerance = zoom_threshold(10),
    origin = water_areas_z13,
)

########NEW FILE########
__FILENAME__ = mapnik-render
import sys
import glob
import os.path
import mapnik
import pyproj
import PIL.Image
import ModestMaps
import optparse

optparser = optparse.OptionParser(usage="""%prog [options]
""")

defaults = {
    'fonts': 'fonts',
    'stylesheet': 'style.xml',
    'location': (37.804325, -122.271169),
    'zoom': 10,
    'size': (1024, 768),
    'output': 'out.png'
}

optparser.set_defaults(**defaults)

optparser.add_option('-f', '--fonts', dest='fonts',
                     type='string', help='Directory name for fonts. Default value is "%(fonts)s".' % defaults)

optparser.add_option('-s', '--stylesheet', dest='stylesheet',
                     type='string', help='File name of mapnik XML file. Default value is "%(stylesheet)s".' % defaults)

optparser.add_option('-l', '--location', dest='location',
                     nargs=2, type='float', help='Latitude and longitude of map center. Default value is %.6f, %.6f.' % defaults['location'])

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Zoom level of rendered map. Default value is %(zoom)d.' % defaults)

optparser.add_option('-d', '--dimensions', dest='size',
                     nargs=2, type='int', help='Width and height of rendered map. Default value is %d, %d.' % defaults['size'])

optparser.add_option('-o', '--output', dest='output',
                     type='string', help='File name of rendered map. Default value is "%(output)s".' % defaults)

if __name__ == '__main__':

    opts, args = optparser.parse_args()

    try:
        fonts = opts.fonts
        stylesheet = opts.stylesheet
        zoom = opts.zoom
        output = opts.output
    
        center = ModestMaps.Geo.Location(*opts.location)
        dimensions = ModestMaps.Core.Point(*opts.size)
        format = output[-4:]
        
        assert zoom >= 0 and zoom <= 18
        assert format in ('.png', '.jpg')
    
        for ttf in glob.glob(os.path.join(fonts, '*.ttf')):
            mapnik.FontEngine.register_font(ttf)

    except Exception, e:
        print >> sys.stderr, e
        print >> sys.stderr, 'Usage: python mapnik-render.py <fonts dir> <stylesheet> <lat> <lon> <zoom> <width> <height> <output jpg/png>'
        sys.exit(1)

    osm = ModestMaps.OpenStreetMap.Provider()
    map = ModestMaps.mapByCenterZoom(osm, center, zoom, dimensions)
    
    srs = {'proj': 'merc', 'a': 6378137, 'b': 6378137, 'lat_0': 0, 'lon_0': 0, 'k': 1.0, 'units': 'm', 'nadgrids': '@null', 'no_defs': True}
    gym = pyproj.Proj(srs)

    northwest = map.pointLocation(ModestMaps.Core.Point(0, 0))
    southeast = map.pointLocation(dimensions)
    
    left, top = gym(northwest.lon, northwest.lat)
    right, bottom = gym(southeast.lon, southeast.lat)
    
    map = mapnik.Map(dimensions.x, dimensions.y)
    mapnik.load_map(map, stylesheet)
    map.zoom_to_box(mapnik.Envelope(left, top, right, bottom))
    
    img = mapnik.Image(dimensions.x, dimensions.y)
    
    mapnik.render(map, img)
    
    img = PIL.Image.fromstring('RGBA', (dimensions.x, dimensions.y), img.tostring())
    
    if format == '.jpg':
        img.save(output, quality=85)
    else:
        img.save(output)

########NEW FILE########
