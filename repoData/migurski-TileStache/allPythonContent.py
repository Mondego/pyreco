__FILENAME__ = tilestache-clean
#!/usr/bin/env python
"""tilestache-clean.py will flush your cache.

This script is intended to be run directly. This example cleans the area around
West Oakland (http://sta.mn/ck) in the "osm" layer, for zoom levels 12-15:

    tilestache-clean.py -c ./config.json -l osm -b 37.79 -122.35 37.83 -122.25 -e png 12 13 14 15

See `tilestache-clean.py --help` for more information.
"""

from sys import stderr, path
from optparse import OptionParser

try:
    from json import dump as json_dump
except ImportError:
    from simplejson import dump as json_dump

#
# Most imports can be found below, after the --include-path option is known.
#

parser = OptionParser(usage="""%prog [options] [zoom...]

Cleans a single layer in your TileStache configuration - no images are returned,
and TileStache ends up with an empty in selected areas cache. Bounding box is
given as a pair of lat/lon coordinates, e.g. "37.788 -122.349 37.833 -122.246".
Output is a list of tile paths as they are created.

Configuration, bbox, and layer options are required; see `%prog --help` for info.""")

defaults = dict(extension='png', padding=0, verbose=True, bbox=(37.777, -122.352, 37.839, -122.226))

parser.set_defaults(**defaults)

parser.add_option('-c', '--config', dest='config',
                  help='Path to configuration file.')

parser.add_option('-l', '--layer', dest='layer',
                  help='Layer name from configuration. "ALL" is a special value that will clean all layers in turn. If you have an actual layer named "ALL", use "ALL LAYERS" instead.')

parser.add_option('-b', '--bbox', dest='bbox',
                  help='Bounding box in floating point geographic coordinates: south west north east.',
                  type='float', nargs=4)

parser.add_option('-p', '--padding', dest='padding',
                  help='Extra margin of tiles to add around bounded area. Default value is %s (no extra tiles).' % repr(defaults['padding']),
                  type='int')

parser.add_option('-e', '--extension', dest='extension',
                  help='Optional file type for rendered tiles. Default value is %s.' % repr(defaults['extension']))

parser.add_option('-f', '--progress-file', dest='progressfile',
                  help="Optional JSON progress file that gets written on each iteration, so you don't have to pay close attention.")

parser.add_option('-q', action='store_false', dest='verbose',
                  help='Suppress chatty output, --progress-file works well with this.')

parser.add_option('-i', '--include-path', dest='include',
                  help="Add the following colon-separated list of paths to Python's include path (aka sys.path)")

parser.add_option('--tile-list', dest='tile_list',
                  help='Optional file of tile coordinates, a simple text list of Z/X/Y coordinates. Overrides --bbox and --padding.')

def generateCoordinates(ul, lr, zooms, padding):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Flood-fill coordinates based on two corners, a list of zooms and padding.
    """
    # start with a simple total of all the coordinates we will need.
    count = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)
        
        rows = lr_.row + 1 - ul_.row
        cols = lr_.column + 1 - ul_.column
        
        count += int(rows * cols)

    # now generate the actual coordinates.
    # offset starts at zero
    offset = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)

        for row in range(int(ul_.row), int(lr_.row + 1)):
            for column in range(int(ul_.column), int(lr_.column + 1)):
                coord = Coordinate(row, column, zoom)
                
                yield (offset, count, coord)
                
                offset += 1

def listCoordinates(filename):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Read coordinates from a file with one Z/X/Y coordinate per line.
    """
    coords = (line.strip().split('/') for line in open(filename, 'r'))
    coords = (map(int, (row, column, zoom)) for (zoom, column, row) in coords)
    coords = [Coordinate(*args) for args in coords]
    
    count = len(coords)
    
    for (offset, coord) in enumerate(coords):
        yield (offset, count, coord)

if __name__ == '__main__':
    options, zooms = parser.parse_args()

    if options.include:
        for p in options.include.split(':'):
            path.insert(0, p)

    from TileStache import parseConfigfile, getTile
    from TileStache.Core import KnownUnknown
    from TileStache.Caches import Disk, Multi
    
    from ModestMaps.Core import Coordinate
    from ModestMaps.Geo import Location

    try:
        if options.config is None:
            raise KnownUnknown('Missing required configuration (--config) parameter.')

        if options.layer is None:
            raise KnownUnknown('Missing required layer (--layer) parameter.')

        config = parseConfigfile(options.config)

        if options.layer in ('ALL', 'ALL LAYERS') and options.layer not in config.layers:
            # clean every layer in the config
            layers = config.layers.values()

        elif options.layer not in config.layers:
            raise KnownUnknown('"%s" is not a layer I know about. Here are some that I do know about: %s.' % (options.layer, ', '.join(sorted(config.layers.keys()))))

        else:
            # clean just one layer in the config
            layers = [config.layers[options.layer]]
        
        verbose = options.verbose
        extension = options.extension
        progressfile = options.progressfile
        
        lat1, lon1, lat2, lon2 = options.bbox
        south, west = min(lat1, lat2), min(lon1, lon2)
        north, east = max(lat1, lat2), max(lon1, lon2)

        northwest = Location(north, west)
        southeast = Location(south, east)

        for (i, zoom) in enumerate(zooms):
            if not zoom.isdigit():
                raise KnownUnknown('"%s" is not a valid numeric zoom level.' % zoom)

            zooms[i] = int(zoom)
        
        if options.padding < 0:
            raise KnownUnknown('A negative padding will not work.')

        padding = options.padding
        tile_list = options.tile_list

    except KnownUnknown, e:
        parser.error(str(e))

    for layer in layers:

        if tile_list:
            coordinates = listCoordinates(tile_list)
        else:
            ul = layer.projection.locationCoordinate(northwest)
            lr = layer.projection.locationCoordinate(southeast)
    
            coordinates = generateCoordinates(ul, lr, zooms, padding)
        
        for (offset, count, coord) in coordinates:
            path = '%s/%d/%d/%d.%s' % (layer.name(), coord.zoom, coord.column, coord.row, extension)
    
            progress = {"tile": path,
                        "offset": offset + 1,
                        "total": count}
    
            if options.verbose:
                print >> stderr, '%(offset)d of %(total)d...' % progress,
    
            try:
                mimetype, format = layer.getTypeByExtension(extension)
            except:
                #
                # It's not uncommon for layers to lack support for certain
                # extensions, so just don't attempt to remove a cached tile
                # for an unsupported format.
                #
                pass
            else:
                config.cache.remove(layer, coord, format)
    
            if options.verbose:
                print >> stderr, '%(tile)s' % progress
                    
            if progressfile:
                fp = open(progressfile, 'w')
                json_dump(progress, fp)
                fp.close()

########NEW FILE########
__FILENAME__ = tilestache-compose
#!/usr/bin/env python
from sys import stderr, path
from tempfile import mkstemp
from thread import allocate_lock
from os import close, write, unlink
from optparse import OptionParser
from os.path import abspath

import ModestMaps

mmaps_version = tuple(map(int, getattr(ModestMaps, '__version__', '0.0.0').split('.')))

if mmaps_version < (1, 3, 0):
    raise ImportError('tilestache-compose.py requires ModestMaps 1.3.0 or newer.')

#
# More imports can be found below, after the --include-path option is known.
#

class Provider (ModestMaps.Providers.IMapProvider):
    """ Wrapper for TileStache Layer objects that makes them behave like ModestMaps Provider objects.
    
        Requires ModestMaps 1.3.0 or better to support "file://" URLs.
    """
    def __init__(self, layer, verbose=False, ignore_cached=None):
        self.projection = layer.projection
        self.layer = layer
        self.files = []

        self.verbose = bool(verbose)
        self.ignore_cached = bool(ignore_cached)
        self.lock = allocate_lock()
        
        #
        # It's possible that Mapnik is not thread-safe, best to be cautious.
        #
        self.threadsafe = self.layer.provider is not TileStache.Providers.Mapnik

    def tileWidth(self):
        return 256

    def tileHeight(self):
        return 256

    def getTileUrls(self, coord):
        """ Return tile URLs that start with file://, by first retrieving them.
        """
        if self.threadsafe or self.lock.acquire():
            mime_type, tile_data = TileStache.getTile(self.layer, coord, 'png', self.ignore_cached)
            
            handle, filename = mkstemp(prefix='tilestache-compose-', suffix='.png')
            write(handle, tile_data)
            close(handle)
            
            self.files.append(filename)
            
            if not self.threadsafe:
                # must be locked, right?
                self.lock.release()
    
            if self.verbose:
                size = len(tile_data) / 1024.
                printlocked(self.lock, self.layer.name() + '/%(zoom)d/%(column)d/%(row)d.png' % coord.__dict__, '(%dKB)' % size)
            
            return ('file://' + abspath(filename), )
    
    def __del__(self):
        """ Delete any tile that was saved in self.getTileUrls().
        """
        for filename in self.files:
            unlink(filename)

class BadComposure(Exception):
    pass

def printlocked(lock, *stuff):
    """
    """
    if lock.acquire():
        print ' '.join([str(thing) for thing in stuff])
        lock.release()

parser = OptionParser(usage="""tilestache-compose.py [options] file

There are three ways to set a map coverage area.

1) Center, zoom, and dimensions: create a map of the specified size,
   centered on a given geographical point at a given zoom level:

   tilestache-compose.py -c config.json -l layer-name -d 800 800 -n 37.8 -122.3 -z 11 out.jpg

2) Extent and dimensions: create a map of the specified size that
   adequately covers the given geographical extent:

   tilestache-compose.py -c config.json -l layer-name -d 800 800 -e 36.9 -123.5 38.9 -121.2 out.png

3) Extent and zoom: create a map at the given zoom level that covers
   the precise geographical extent, at whatever pixel size is necessary:
   
   tilestache-compose.py -c config.json -l layer-name -e 36.9 -123.5 38.9 -121.2 -z 9 out.jpg""")

defaults = dict(center=(37.8044, -122.2712), zoom=14, dimensions=(900, 600), verbose=True)

parser.set_defaults(**defaults)

parser.add_option('-c', '--config', dest='config',
                  help='Path to configuration file.')

parser.add_option('-l', '--layer', dest='layer',
                  help='Layer name from configuration.')

parser.add_option('-n', '--center', dest='center', nargs=2,
                  help='Geographic center of map. Default %.4f, %.4f.' % defaults['center'], type='float',
                  action='store')

parser.add_option('-e', '--extent', dest='extent', nargs=4,
                  help='Geographic extent of map. Two lat, lon pairs', type='float',
                  action='store')

parser.add_option('-z', '--zoom', dest='zoom',
                  help='Zoom level. Default %(zoom)d.' % defaults, type='int',
                  action='store')

parser.add_option('-d', '--dimensions', dest='dimensions', nargs=2,
                  help='Pixel width, height of output image. Default %d, %d.' % defaults['dimensions'], type='int',
                  action='store')

parser.add_option('-v', '--verbose', dest='verbose',
                  help='Make a bunch of noise.',
                  action='store_true')

parser.add_option('-i', '--include-path', dest='include_paths',
                  help="Add the following colon-separated list of paths to Python's include path (aka sys.path)")

parser.add_option('-x', '--ignore-cached', action='store_true', dest='ignore_cached',
                  help='Re-render every tile, whether it is in the cache already or not.')

if __name__ == '__main__':

    (options, args) = parser.parse_args()

    if options.include_paths:
        for p in options.include_paths.split(':'):
            path.insert(0, p)

    import TileStache
    
    try:
        if options.config is None:
            raise TileStache.Core.KnownUnknown('Missing required configuration (--config) parameter.')

        if options.layer is None:
            raise TileStache.Core.KnownUnknown('Missing required layer (--layer) parameter.')

        config = TileStache.parseConfigfile(options.config)

        if options.layer not in config.layers:
            raise TileStache.Core.KnownUnknown('"%s" is not a layer I know about. Here are some that I do know about: %s.' % (options.layer, ', '.join(sorted(config.layers.keys()))))

        provider = Provider(config.layers[options.layer], options.verbose, options.ignore_cached)
        
        try:
            outfile = args[0]
        except IndexError:
            raise BadComposure('Error: Missing output file.')
        
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
        print >> stderr, parser.usage
        print >> stderr, ''
        print >> stderr, '%s --help for possible options.' % __file__
        print >> stderr, ''
        print >> stderr, e
        exit(1)

    if options.verbose:
        print map.coordinate, map.offset, '->', outfile, (map.dimensions.x, map.dimensions.y)

    map.draw(False).save(outfile)

########NEW FILE########
__FILENAME__ = tilestache-list
#!/usr/bin/env python
"""tilestache-list.py will list your tiles.

This script is intended to be run directly. This example lists tiles in the area
around West Oakland (http://sta.mn/ck) in the "osm" layer, for zoom levels 12-15:

    tilestache-list.py -b 37.79 -122.35 37.83 -122.25 12 13 14 15

See `tilestache-list.py --help` for more information.
"""

from sys import stderr, path
from optparse import OptionParser

from TileStache.Core import KnownUnknown
from TileStache import MBTiles

from ModestMaps.Core import Coordinate
from ModestMaps.Geo import Location
from ModestMaps.OpenStreetMap import Provider

parser = OptionParser(usage="""%prog [options] [zoom...]

Generates a list of tiles based on geographic or other criteria. No images are
created and no Tilestache configuration is read, but a list of tile coordinates
in Z/X/Y form compatible with `tilestache-seed --tile-list` is output.

Example:

    tilestache-list.py -b 52.55 13.28 52.46 13.51 11 12 13

Protip: seed a cache in parallel on 8 CPUs with split and xargs like this:

    tilestache-list.py 12 13 14 15 | split -l 20 - tiles/list-
    ls -1 tiles/list-* | xargs -n1 -P8 tilestache-seed.py -c tilestache.cfg -l osm --tile-list

See `%prog --help` for info.""")

defaults = dict(padding=0, bbox=(37.777, -122.352, 37.839, -122.226))

parser.set_defaults(**defaults)

parser.add_option('-b', '--bbox', dest='bbox',
                  help='Bounding box in floating point geographic coordinates: south west north east. Default value is %.3f, %.3f, %.3f, %.3f.' % defaults['bbox'],
                  type='float', nargs=4)

parser.add_option('-p', '--padding', dest='padding',
                  help='Extra margin of tiles to add around bounded area. Default value is %s (no extra tiles).' % repr(defaults['padding']),
                  type='int')

parser.add_option('--from-mbtiles', dest='mbtiles_input',
                  help='Optional input file for tiles, will be read as an MBTiles 1.1 tileset. See http://mbtiles.org for more information. Overrides --bbox and --padding.')

def generateCoordinates(ul, lr, zooms, padding):
    """ Generate a stream of coordinates for seeding.
    
        Flood-fill coordinates based on two corners, a list of zooms and padding.
    """
    # start with a simple total of all the coordinates we will need.
    count = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)
        
        rows = lr_.row + 1 - ul_.row
        cols = lr_.column + 1 - ul_.column
        
        count += int(rows * cols)

    # now generate the actual coordinates.
    # offset starts at zero
    offset = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)

        for row in range(int(ul_.row), int(lr_.row + 1)):
            for column in range(int(ul_.column), int(lr_.column + 1)):
                coord = Coordinate(row, column, zoom)
                
                yield coord
                offset += 1

def tilesetCoordinates(filename):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Read coordinates from an MBTiles tileset filename.
    """
    coords = MBTiles.list_tiles(filename)
    count = len(coords)
    
    for (offset, coord) in enumerate(coords):
        yield coord

if __name__ == '__main__':
    options, zooms = parser.parse_args()

    if bool(options.mbtiles_input):
        coordinates = MBTiles.list_tiles(options.mbtiles_input)

    else:
        lat1, lon1, lat2, lon2 = options.bbox
        south, west = min(lat1, lat2), min(lon1, lon2)
        north, east = max(lat1, lat2), max(lon1, lon2)

        northwest = Location(north, west)
        southeast = Location(south, east)
        
        osm = Provider()

        ul = osm.locationCoordinate(northwest)
        lr = osm.locationCoordinate(southeast)

        for (i, zoom) in enumerate(zooms):
            if not zoom.isdigit():
                raise KnownUnknown('"%s" is not a valid numeric zoom level.' % zoom)

            zooms[i] = int(zoom)
        
        if options.padding < 0:
            raise KnownUnknown('A negative padding will not work.')

        coordinates = generateCoordinates(ul, lr, zooms, options.padding)
    
    for coord in coordinates:
        print '%(zoom)d/%(column)d/%(row)d' % coord.__dict__

########NEW FILE########
__FILENAME__ = tilestache-render
#!/usr/bin/env python
"""tilestache-render.py will warm your cache.

This script is *deprecated* and will be removed in a future TileStache 2.0.

This script is intended to be run directly. This example will save two tiles
for San Francisco and Oakland to local temporary files:

    tilestache-render.py -c ./config.json -l osm 12/655/1582.png 12/656/1582.png

Output for this sample might look like this:

    /tmp/tile-_G3uHX.png
    /tmp/tile-pWNfQQ.png

...where each line corresponds to one of the given coordinates, in order.
You are expected to use these files and then dispose of them.

See `tilestache-render.py --help` for more information.
"""


import re
import os
from tempfile import mkstemp
from optparse import OptionParser

from TileStache import parseConfigfile, getTile
from TileStache.Core import KnownUnknown

from ModestMaps.Core import Coordinate

parser = OptionParser(usage="""%prog [options] [coord...]

Each coordinate in the argument list should look like "12/656/1582.png", similar
to URL paths in web server usage. Coordinates are processed in order, each one
rendered to an image file in a temporary location and output to stdout in order.

Configuration and layer options are required; see `%prog --help` for info.""")

parser.add_option('-c', '--config', dest='config',
                  help='Path to configuration file.')

parser.add_option('-l', '--layer', dest='layer',
                  help='Layer name from configuration.')

pathinfo_pat = re.compile(r'^(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)\.(?P<e>\w+)$')

if __name__ == '__main__':
    options, paths = parser.parse_args()
    
    try:
        if options.config is None:
            raise KnownUnknown('Missing required configuration (--config) parameter.')
    
        if options.layer is None:
            raise KnownUnknown('Missing required layer (--layer) parameter.')
    
        config = parseConfigfile(options.config)
        
        if options.layer not in config.layers:
            raise KnownUnknown('"%s" is not a layer I know about. Here are some that I do know about: %s.' % (options.layer, ', '.join(sorted(config.layers.keys()))))
        
        layer = config.layers[options.layer]
        
        coords = []
        
        for path in paths:
            path_ = pathinfo_pat.match(path)
            
            if path_ is None:
                raise KnownUnknown('"%s" is not a path I understand. I was expecting something more like "0/0/0.png".' % path)
            
            row, column, zoom, extension = [path_.group(p) for p in 'yxze']
            coord = Coordinate(int(row), int(column), int(zoom))

            coords.append(coord)

    except KnownUnknown, e:
        parser.error(str(e))
    
    for coord in coords:
        # render
        mimetype, content = getTile(layer, coord, extension)
        
        # save
        handle, filename = mkstemp(prefix='tile-', suffix='.'+extension)
        os.write(handle, content)
        os.close(handle)
        
        # inform
        print filename

########NEW FILE########
__FILENAME__ = tilestache-seed
#!/usr/bin/env python
"""tilestache-seed.py will warm your cache.

This script is intended to be run directly. This example seeds the area around
West Oakland (http://sta.mn/ck) in the "osm" layer, for zoom levels 12-15:

    tilestache-seed.py -c ./config.json -l osm -b 37.79 -122.35 37.83 -122.25 -e png 12 13 14 15

See `tilestache-seed.py --help` for more information.
"""

from sys import stderr, path
from os.path import realpath, dirname
from optparse import OptionParser
from urlparse import urlparse
from urllib import urlopen

try:
    from json import dump as json_dump
    from json import load as json_load
except ImportError:
    from simplejson import dump as json_dump
    from simplejson import load as json_load

#
# Most imports can be found below, after the --include-path option is known.
#

parser = OptionParser(usage="""%prog [options] [zoom...]

Seeds a single layer in your TileStache configuration - no images are returned,
but TileStache ends up with a pre-filled cache. Bounding box is given as a pair
of lat/lon coordinates, e.g. "37.788 -122.349 37.833 -122.246". Output is a list
of tile paths as they are created.

Example:

    tilestache-seed.py -b 52.55 13.28 52.46 13.51 -c tilestache.cfg -l osm 11 12 13

Protip: extract tiles from an MBTiles tileset to a directory like this:

    tilestache-seed.py --from-mbtiles filename.mbtiles --output-directory dirname

Configuration, bbox, and layer options are required; see `%prog --help` for info.""")

defaults = dict(padding=0, verbose=True, enable_retries=False, bbox=(37.777, -122.352, 37.839, -122.226))

parser.set_defaults(**defaults)

parser.add_option('-c', '--config', dest='config',
                  help='Path to configuration file, typically required.')

parser.add_option('-l', '--layer', dest='layer',
                  help='Layer name from configuration, typically required.')

parser.add_option('-b', '--bbox', dest='bbox',
                  help='Bounding box in floating point geographic coordinates: south west north east. Default value is %.3f, %.3f, %.3f, %.3f.' % defaults['bbox'],
                  type='float', nargs=4)

parser.add_option('-p', '--padding', dest='padding',
                  help='Extra margin of tiles to add around bounded area. Default value is %s (no extra tiles).' % repr(defaults['padding']),
                  type='int')

parser.add_option('-e', '--extension', dest='extension',
                  help='Optional file type for rendered tiles. Default value is "png" for most image layers and some variety of JSON for Vector or Mapnik Grid providers.')

parser.add_option('-f', '--progress-file', dest='progressfile',
                  help="Optional JSON progress file that gets written on each iteration, so you don't have to pay close attention.")

parser.add_option('-q', action='store_false', dest='verbose',
                  help='Suppress chatty output, --progress-file works well with this.')

parser.add_option('-i', '--include-path', dest='include_paths',
                  help="Add the following colon-separated list of paths to Python's include path (aka sys.path)")

parser.add_option('-d', '--output-directory', dest='outputdirectory',
                  help='Optional output directory for tiles, to override configured cache with the equivalent of: {"name": "Disk", "path": <output directory>, "dirs": "portable", "gzip": []}. More information in http://tilestache.org/doc/#caches.')

parser.add_option('--to-mbtiles', dest='mbtiles_output',
                  help='Optional output file for tiles, will be created as an MBTiles 1.1 tileset. See http://mbtiles.org for more information.')

parser.add_option('--to-s3', dest='s3_output',
                  help='Optional output bucket for tiles, will be populated with tiles in a standard Z/X/Y layout. Three required arguments: AWS access-key, secret, and bucket name.',
                  nargs=3)

parser.add_option('--from-mbtiles', dest='mbtiles_input',
                  help='Optional input file for tiles, will be read as an MBTiles 1.1 tileset. See http://mbtiles.org for more information. Overrides --extension, --bbox and --padding (this may change).')

parser.add_option('--tile-list', dest='tile_list',
                  help='Optional file of tile coordinates, a simple text list of Z/X/Y coordinates. Overrides --bbox and --padding.')

parser.add_option('--error-list', dest='error_list',
                  help='Optional file of failed tile coordinates, a simple text list of Z/X/Y coordinates. If provided, failed tiles will be logged to this file instead of stopping tilestache-seed.')

parser.add_option('--enable-retries', dest='enable_retries',
                  help='If true this will cause tilestache-seed to retry failed tile renderings up to (3) times. Default value is %s.' % repr(defaults['enable_retries']),
                  action='store_true')

parser.add_option('-x', '--ignore-cached', action='store_true', dest='ignore_cached',
                  help='Re-render every tile, whether it is in the cache already or not.')

parser.add_option('--jsonp-callback', dest='callback',
                  help='Add a JSONP callback for tiles with a json mime-type, causing "*.js" tiles to be written to the cache wrapped in the callback function. Ignored for non-JSON tiles.')

def generateCoordinates(ul, lr, zooms, padding):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Flood-fill coordinates based on two corners, a list of zooms and padding.
    """
    # start with a simple total of all the coordinates we will need.
    count = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)
        
        rows = lr_.row + 1 - ul_.row
        cols = lr_.column + 1 - ul_.column
        
        count += int(rows * cols)

    # now generate the actual coordinates.
    # offset starts at zero
    offset = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)

        for row in xrange(int(ul_.row), int(lr_.row + 1)):
            for column in xrange(int(ul_.column), int(lr_.column + 1)):
                coord = Coordinate(row, column, zoom)
                
                yield (offset, count, coord)
                
                offset += 1

def listCoordinates(filename):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Read coordinates from a file with one Z/X/Y coordinate per line.
    """
    coords = (line.strip().split('/') for line in open(filename, 'r'))
    coords = (map(int, (row, column, zoom)) for (zoom, column, row) in coords)
    coords = [Coordinate(*args) for args in coords]
    
    count = len(coords)
    
    for (offset, coord) in enumerate(coords):
        yield (offset, count, coord)

def tilesetCoordinates(filename):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Read coordinates from an MBTiles tileset filename.
    """
    coords = MBTiles.list_tiles(filename)
    count = len(coords)
    
    for (offset, coord) in enumerate(coords):
        yield (offset, count, coord)

def parseConfigfile(configpath):
    """ Parse a configuration file and return a raw dictionary and dirpath.
    
        Return value can be passed to TileStache.Config.buildConfiguration().
    """
    config_dict = json_load(urlopen(configpath))
    
    scheme, host, path, p, q, f = urlparse(configpath)
    
    if scheme == '':
        scheme = 'file'
        path = realpath(path)
    
    dirpath = '%s://%s%s' % (scheme, host, dirname(path).rstrip('/') + '/')
    
    return config_dict, dirpath

if __name__ == '__main__':
    options, zooms = parser.parse_args()

    if options.include_paths:
        for p in options.include_paths.split(':'):
            path.insert(0, p)

    from TileStache import getTile, Config
    from TileStache.Core import KnownUnknown
    from TileStache.Config import buildConfiguration
    from TileStache import MBTiles
    import TileStache
    
    from ModestMaps.Core import Coordinate
    from ModestMaps.Geo import Location

    try:
        # determine if we have enough information to prep a config and layer
        
        has_fake_destination = bool(options.outputdirectory or options.mbtiles_output)
        has_fake_source = bool(options.mbtiles_input)
        
        if has_fake_destination and has_fake_source:
            config_dict, config_dirpath = dict(layers={}), '' # parseConfigfile(options.config)
            layer_dict = dict()
            
            config_dict['cache'] = dict(name='test')
            config_dict['layers'][options.layer or 'tiles-layer'] = layer_dict
        
        elif options.config is None:
            raise KnownUnknown('Missing required configuration (--config) parameter.')
        
        elif options.layer is None:
            raise KnownUnknown('Missing required layer (--layer) parameter.')
    
        else:
            config_dict, config_dirpath = parseConfigfile(options.config)
            
            if options.layer not in config_dict['layers']:
                raise KnownUnknown('"%s" is not a layer I know about. Here are some that I do know about: %s.' % (options.layer, ', '.join(sorted(config_dict['layers'].keys()))))
            
            layer_dict = config_dict['layers'][options.layer]
            layer_dict['write_cache'] = True # Override to make seeding guaranteed useful.
        
        # override parts of the config and layer if needed
        
        extension = options.extension

        if options.mbtiles_input:
            layer_dict['provider'] = dict(name='mbtiles', tileset=options.mbtiles_input)
            n, t, v, d, format, b = MBTiles.tileset_info(options.mbtiles_input)
            extension = format or extension
        
        # determine or guess an appropriate tile extension
        
        if extension is None:
            provider_name = layer_dict['provider'].get('name', '').lower()
            
            if provider_name == 'mapnik grid':
                extension = 'json'
            elif provider_name == 'vector':
                extension = 'geojson'
            else:
                extension = 'png'
        
        # override parts of the config and layer if needed
        
        tiers = []
        
        if options.mbtiles_output:
            tiers.append({'class': 'TileStache.MBTiles:Cache',
                          'kwargs': dict(filename=options.mbtiles_output,
                                         format=extension,
                                         name=options.layer)})
        
        if options.outputdirectory:
            tiers.append(dict(name='disk', path=options.outputdirectory,
                              dirs='portable', gzip=[]))

        if options.s3_output:
            access, secret, bucket = options.s3_output
            tiers.append(dict(name='S3', bucket=bucket,
                              access=access, secret=secret))
        
        if len(tiers) > 1:
            config_dict['cache'] = dict(name='multi', tiers=tiers)
        elif len(tiers) == 1:
            config_dict['cache'] = tiers[0]
        else:
            # Leave config_dict['cache'] as-is
            pass
        
        # create a real config object
        
        config = buildConfiguration(config_dict, config_dirpath)
        layer = config.layers[options.layer or 'tiles-layer']
        
        # do the actual work
        
        lat1, lon1, lat2, lon2 = options.bbox
        south, west = min(lat1, lat2), min(lon1, lon2)
        north, east = max(lat1, lat2), max(lon1, lon2)

        northwest = Location(north, west)
        southeast = Location(south, east)

        ul = layer.projection.locationCoordinate(northwest)
        lr = layer.projection.locationCoordinate(southeast)

        for (i, zoom) in enumerate(zooms):
            if not zoom.isdigit():
                raise KnownUnknown('"%s" is not a valid numeric zoom level.' % zoom)

            zooms[i] = int(zoom)
        
        if options.padding < 0:
            raise KnownUnknown('A negative padding will not work.')

        padding = options.padding
        tile_list = options.tile_list
        error_list = options.error_list

    except KnownUnknown, e:
        parser.error(str(e))

    if tile_list:
        coordinates = listCoordinates(tile_list)
    elif options.mbtiles_input:
        coordinates = tilesetCoordinates(options.mbtiles_input)
    else:
        coordinates = generateCoordinates(ul, lr, zooms, padding)
    
    for (offset, count, coord) in coordinates:
        path = '%s/%d/%d/%d.%s' % (layer.name(), coord.zoom, coord.column, coord.row, extension)

        progress = {"tile": path,
                    "offset": offset + 1,
                    "total": count}

        #
        # Fetch a tile.
        #
        
        attempts = options.enable_retries and 3 or 1
        rendered = False
        
        while not rendered:
            if options.verbose:
                print >> stderr, '%(offset)d of %(total)d...' % progress,
    
            try:
                mimetype, content = getTile(layer, coord, extension, options.ignore_cached)
                
                if mimetype and 'json' in mimetype and options.callback:
                    js_path = '%s/%d/%d/%d.js' % (layer.name(), coord.zoom, coord.column, coord.row)
                    js_body = '%s(%s);' % (options.callback, content)
                    js_size = len(js_body) / 1024
                    
                    layer.config.cache.save(js_body, layer, coord, 'JS')
                    print >> stderr, '%s (%dKB)' % (js_path, js_size),
            
                elif options.callback:
                    print >> stderr, '(callback ignored)',
            
            except:
                #
                # Something went wrong: try again? Log the error?
                #
                attempts -= 1

                if options.verbose:
                    print >> stderr, 'Failed %s, will try %s more.' % (progress['tile'], ['no', 'once', 'twice'][attempts])
                
                if attempts == 0:
                    if not error_list:
                        raise
                    
                    fp = open(error_list, 'a')
                    fp.write('%(zoom)d/%(column)d/%(row)d\n' % coord.__dict__)
                    fp.close()
                    break
            
            else:
                #
                # Successfully got the tile.
                #
                rendered = True
                progress['size'] = '%dKB' % (len(content) / 1024)
        
                if options.verbose:
                    print >> stderr, '%(tile)s (%(size)s)' % progress
                
        if options.progressfile:
            fp = open(options.progressfile, 'w')
            json_dump(progress, fp)
            fp.close()

########NEW FILE########
__FILENAME__ = tilestache-server
#!/usr/bin/env python
"""tilestache-server.py will serve your cache.

This script is intended to be run directly from the command line.

It is intended for direct use only during development or for debugging TileStache.

For the proper way to configure TileStach for serving tiles see the docs at:

http://tilestache.org/doc/#serving-tiles

To use this built-in server, install werkzeug and then run tilestache-server.py:

    tilestache-server.py

By default the script looks for a config file named tilestache.cfg in the current directory and then serves tiles on http://127.0.0.1:8080/. 

You can then open your browser and view a url like:

    http://localhost:8080/osm/0/0/0.png

The above layer of 'osm' (defined in the tilestache.cfg) will display an OpenStreetMap
tile proxied from http://tile.osm.org/0/0/0.png
   
Check tilestache-server.py --help to change these defaults.
"""

if __name__ == '__main__':
    from datetime import datetime
    from optparse import OptionParser, OptionValueError
    import os, sys

    parser = OptionParser()
    parser.add_option("-c", "--config", dest="file", default="tilestache.cfg",
        help="the path to the tilestache config")
    parser.add_option("-i", "--ip", dest="ip", default="127.0.0.1",
        help="the IP address to listen on")
    parser.add_option("-p", "--port", dest="port", type="int", default=8080,
        help="the port number to listen on")
    parser.add_option('--include-path', dest='include',
        help="Add the following colon-separated list of paths to Python's include path (aka sys.path)")
    (options, args) = parser.parse_args()

    if options.include:
        for p in options.include.split(':'):
            sys.path.insert(0, p)

    from werkzeug.serving import run_simple
    import TileStache

    if not os.path.exists(options.file):
        print >> sys.stderr, "Config file not found. Use -c to pick a tilestache config file."
        sys.exit(1)

    app = TileStache.WSGITileServer(config=options.file, autoreload=True)
    run_simple(options.ip, options.port, app)


########NEW FILE########
__FILENAME__ = cache_tests
from unittest import TestCase
from . import utils
import memcache

class CacheTests(TestCase):
    '''Tests various Cache configurations that reads from cfg file'''

    def setUp(self):
        self.mc = memcache.Client(['127.0.0.1:11211'], debug=0)
        self.mc.flush_all()

    def test_memcache(self):
        '''Fetch tile and check the existence in memcached'''

        config_file_content = '''
        {
           "layers":{
              "memcache_osm":{
                 "provider":{
                    "name":"proxy",
                    "url": "http://tile.openstreetmap.org/{Z}/{X}/{Y}.png"
                 }
              }
            },
            "cache": {
                "name": "Memcache",
                "servers": ["127.0.0.1:11211"],
                "revision": 4
            }
        }
        '''

        tile_mimetype, tile_content = utils.request(config_file_content, "memcache_osm", "png", 0, 0, 0)
        self.assertEqual(tile_mimetype, "image/png")

        self.assertEqual(self.mc.get('/4/memcache_osm/0/0/0.PNG'), tile_content,
            'Contents of memcached and value returned from TileStache do not match')

    def test_memcache_keyprefix(self):
        '''Fetch tile and check the existence of key with prefix in memcached'''

        config_file_content = '''
        {
           "layers":{
              "memcache_osm":{
                 "provider":{
                    "name":"proxy",
                    "url": "http://tile.openstreetmap.org/{Z}/{X}/{Y}.png"
                 }
              }
            },
            "cache": {
                "name": "Memcache",
                "servers": ["127.0.0.1:11211"],
                "revision": 1,
                "key prefix" : "cool_prefix"
            }
        }
        '''

        tile_mimetype, tile_content = utils.request(config_file_content, "memcache_osm", "png", 0, 0, 0)
        self.assertEqual(tile_mimetype, "image/png")

        self.assertEqual(self.mc.get('cool_prefix/1/memcache_osm/0/0/0.PNG'), tile_content,
            'Contents of memcached and value returned from TileStache do not match')

        self.assertEqual(self.mc.get('/1/memcache_osm/0/0/0.PNG'), None,
            'Memcache returned a value even though it should have been empty')






########NEW FILE########
__FILENAME__ = provider_tests
# This Python file uses the following encoding: utf-8

from unittest import TestCase
from . import utils

class ProviderTests(TestCase):
    '''Tests Proxy Provider that reads from cfg file'''

    def test_proxy_mercator(self):
        '''Fetch tile from OSM using Proxy provider (web mercator)'''

        config_file_content = '''
        {
           "layers":{
              "osm":{
                 "provider":{
                    "name":"proxy",
                    "url": "http://tile.openstreetmap.org/{Z}/{X}/{Y}.png"
                 }
              }
            },
            "cache": {
                "name": "Test"
            }
        }
        '''

        tile_mimetype, tile_content = utils.request(config_file_content, "osm", "png", 0, 0, 0)
        self.assertEqual(tile_mimetype, "image/png")
        self.assertTrue(tile_content[:4] in '\x89\x50\x4e\x47') #check it is a png based on png magic number


    def test_url_template_wgs84(self):
        '''Fetch two WGS84 tiles from WMS using bbox'''

        config_file_content = '''
        {
           "layers":{
              "osgeo_wms":{
                 "projection":"WGS84",
                 "provider":{
                    "name":"url template",
                    "template":"http://vmap0.tiles.osgeo.org/wms/vmap0?LAYERS=basic&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image%2Fpng&SRS=EPSG%3A4326&BBOX=$xmin,$ymin,$xmax,$ymax&WIDTH=256&HEIGHT=256"
                 }
              }
            },
            "cache": {
                "name": "Test"
            }
        }
        '''

        tile_mimetype, tile_content = utils.request(config_file_content, "osgeo_wms", "png", 0, 0, 0)
        self.assertEqual(tile_mimetype, "image/png")
        self.assertTrue(tile_content[:4] in '\x89\x50\x4e\x47') #check it is a png based on png magic number

        #in WGS84 we typically have two tiles at zoom level 0. Get the second tile
        tile_mimetype, tile_content = utils.request(config_file_content, "osgeo_wms", "png", 0, 1, 0)
        self.assertEqual(tile_mimetype, "image/png")
        self.assertTrue(tile_content[:4] in '\x89\x50\x4e\x47') #check it is a png based on png magic number


class ProviderWithDummyResponseServer(TestCase):
    '''
    The following test starts a new Dummy Response Server and does some checks.
    The reason it is in a separate class is because we want to make sure that the setup and teardown
    methods - ***which are specific to this test*** - get called.
    '''

    def setUp(self):
        #create custom binary file that pretends to be a png and a server that always returns the same response
        self.response_content = '\x89\x50\x4e\x47Meh, I am a custom file that loves utf8 chars like éøæ®!!!'
        self.response_mimetype = 'image/png'

        self.temp_file_name = utils.create_temp_file(self.response_content)
        self.server_process, self.server_port = utils.create_dummy_server(self.temp_file_name, self.response_mimetype)

    def tearDown(self):
        self.server_process.kill()

    def test_url_template_custom_binary(self):
        '''Fetch custom binary result using URL Template(result should not be modified)'''

        config_file_content = '''
        {
           "layers":{
              "local_layer":{
                 "projection":"WGS84",
                 "provider":{
                    "name":"url template",
                    "template":"http://localhost:<<port>>/&BBOX=$xmin,$ymin,$xmax,$ymax"
                 }
              }
            },
            "cache": {
                "name": "Test"
            }
        }
        '''.replace('<<port>>', str(self.server_port))

        tile_mimetype, tile_content = utils.request(config_file_content, "local_layer", "png", 0, 0, 0)

        self.assertEquals(tile_mimetype, self.response_mimetype)
        self.assertEquals(tile_content, self.response_content)

########NEW FILE########
__FILENAME__ = dummy-response-server
import argparse
from werkzeug.wrappers import Request, Response

global response_mimetype
global response_content

@Request.application
def application(request):
    return Response(response_content, mimetype=response_mimetype)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Starts an http server that blindly responds whatever it was initialized with.")
    parser.add_argument("port", help="port number")
    parser.add_argument("response_file", help="file that contains response content")
    parser.add_argument("response_mimetype", help="mimetype to use for response")
    args = parser.parse_args()

    #read file into buffer
    print 'Response Content: ' + args.response_file
    global response_content
    f = open(args.response_file, 'rb')
    response_content = f.read()
    f.close()

    #set mimetype
    print 'Response Mimetype: ' + args.response_mimetype
    global response_mimetype
    response_mimetype = args.response_mimetype

    from werkzeug.serving import run_simple
    run_simple('localhost', int(args.port), application)
########NEW FILE########
__FILENAME__ = utils
from tempfile import mkstemp
import os
import inspect
import socket
from subprocess import Popen, PIPE, STDOUT
import shlex
import sys
from time import sleep
from threading  import Thread
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x


from ModestMaps.Core import Coordinate
from TileStache import getTile, parseConfigfile
from TileStache.Core import KnownUnknown

def request(config_file_content, layer_name, format, row, column, zoom):
    '''
    Helper method to write config_file_content to disk and do
    request
    '''

    absolute_file_name = create_temp_file(config_file_content)
    config = parseConfigfile(absolute_file_name)
    layer = config.layers[layer_name]
    coord = Coordinate(int(row), int(column), int(zoom))
    mime_type, tile_content = getTile(layer, coord, format)

    os.remove(absolute_file_name)

    return mime_type, tile_content

def create_temp_file(buffer):
    '''
    Helper method to create temp file on disk. Caller is responsible
    for deleting file once done
    '''
    fd, absolute_file_name = mkstemp(text=True)
    file = os.fdopen(fd, 'w+b')
    file.write(buffer)
    file.close()
    return absolute_file_name

def create_dummy_server(file_with_content, mimetype):
    '''
    Helper method that creates a dummy server that always
    returns the contents of the file specified with the
    mimetype specified
    '''

    # see http://stackoverflow.com/questions/50499/in-python-how-do-i-get-the-path-and-name-of-the-file-that-is-currently-executin
    current_script_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    #start new process using our dummy-response-server.py script
    dummy_server_file = os.path.join(current_script_dir, 'servers', 'dummy-response-server.py')
    port = find_open_port()
    cmd = 'python %s %s "%s" "%s" ' % (dummy_server_file, str(port), file_with_content, mimetype)

    ON_POSIX = 'posix' in sys.builtin_module_names

    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, bufsize=1, close_fds=ON_POSIX)

    # Read the stdout and look for Werkzeug's "Running on" string to indicate the server is ready for action.
    # Otherwise, keep reading. We are using a Queue and a Thread to create a non-blocking read of the other
    # process as described in http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
    # I wanted to use communicate() originally, but it was causing a blocking read and this way will also
    # work on Windows

    q = Queue()
    t = Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True # thread dies with the program
    t.start()

    server_output = ''

    # read line and enter busy loop until the server says it is ok
    while True:
        retcode = p.poll()
        if retcode is not None:
            # process has terminated abruptly
            raise Exception('The test dummy server failed to run. code:[%s] cmd:[%s]'%(str(retcode),cmd))

        try:
            line = q.get_nowait()
        except Empty:
            sleep(0.01)
            continue
        else: # got line
            server_output += line
            if "Running on http://" in server_output:
                break; #server is running, get out of here
            else:
                continue

    return p, port


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def find_open_port():
    '''
    Ask the OS for an open port
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("",0))
    port = s.getsockname()[1]
    s.close()
    return port
########NEW FILE########
__FILENAME__ = vectiles_tests
from unittest import TestCase
from math import hypot
import json

from osgeo import ogr
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, asShape

from . import utils

# Note these tests rely on the fact that Travis CI created a postgis db.
# If you want to run them locally, create a similar PostGIS database.
# Look at .travis.yml for details.

def get_topo_transform(topojson):
    '''
    '''
    def xform((x, y)):
        lon = topojson['transform']['scale'][0] * x + topojson['transform']['translate'][0]
        lat = topojson['transform']['scale'][1] * y + topojson['transform']['translate'][1]
        
        return lon, lat
    
    return xform

def topojson_dediff(points):
    '''
    '''
    out = [points[0]]
    
    for (x, y) in points[1:]:
        out.append((out[-1][0] + x, out[-1][1] + y))
    
    return out

class PostGISVectorTestBase(object):
    '''
    Base Class for VecTiles tests. Has methods to:

      - CREATE and DROP a single table (self.testTableName) that has a field called name
      - Define a geometry field
      - INSERT a record using a WKT
    '''

    def initTestTable(self, testTableName):
        self.conn = ogr.Open("PG: dbname='test_tilestache' user='postgres'")
        self.testTableName = testTableName
        
        self.cleanTestTable()

        sql = 'CREATE TABLE %s (gid serial PRIMARY KEY, name VARCHAR)' % (self.testTableName,)
        self.conn.ExecuteSQL(sql)

    def defineGeometry(self, geom_type, geom_name = '__geometry__', srid=900913):
        self.srid = srid
        self.geom_name = geom_name
        
        sql = "SELECT AddGeometryColumn('public', '%s', '%s', %s, '%s', 2)" % \
        (self.testTableName, geom_name, srid, geom_type)

        self.conn.ExecuteSQL(sql)

    def insertTestRow(self, wkt, name=''):
        sql = "INSERT INTO %s (%s, name) VALUES(ST_Transform(ST_GeomFromText('%s', 4326), %s), '%s')" % \
        (self.testTableName, self.geom_name, wkt, self.srid, name)

        self.conn.ExecuteSQL(sql)

    def cleanTestTable(self):
        self.conn.ExecuteSQL('DROP TABLE if exists %s' % (self.testTableName,))


class VectorProviderTest(PostGISVectorTestBase, TestCase):
    '''Various vectiles tests on top of PostGIS'''

    def setUp(self):
        self.initTestTable('dummy_table')

        self.config_file_content = '''
        {
           "layers":{
              "vectile_test":
              {
                 "provider":
                 {
                     "class": "TileStache.Goodies.VecTiles:Provider",
                     "kwargs":
                     {
                         "clip": false,
                         "dbinfo":
                         {
                             "user": "postgres",
                             "password": "",
                             "database": "test_tilestache"
                         },
                         "queries":
                         [
                             "SELECT * FROM dummy_table"
                         ]
                     }
                 }
              },
              "vectile_copy":
              {
                 "provider":
                 {
                     "class": "TileStache.Goodies.VecTiles:Provider",
                     "kwargs":
                     {
                         "dbinfo":
                         {
                             "user": "postgres",
                             "password": "",
                             "database": "test_tilestache"
                         },
                         "queries":
                         [
                             "SELECT * FROM dummy_table"
                         ]
                     }
                 }
              },
              "vectile_multi":
              {
                 "provider":
                 {
                     "class": "TileStache.Goodies.VecTiles:MultiProvider",
                     "kwargs": { "names": [ "vectile_test", "vectile_copy" ] }
                 }
              }
            },
            "cache": {
                "name": "Test"
            }
        }
        '''

    def tearDown(self):
        self.cleanTestTable()
    
    def test_points_geojson(self):
        '''
        Create 3 points (2 on west, 1 on east hemisphere) and retrieve as geojson.
        2 points should be returned in western hemisphere and 1 on eastern at zoom level 1
        (clip on)
        '''
        
        self.defineGeometry('POINT')

        point_sf = Point(-122.42, 37.78)
        point_berlin = Point(13.41, 52.52)
        point_lima = Point(-77.03, 12.04)

        self.insertTestRow(point_sf.wkt, 'San Francisco')
        self.insertTestRow(point_berlin.wkt, 'Berlin')
        self.insertTestRow(point_lima.wkt, 'Lima')

        ########
        # northwest quadrant should return San Francisco and Lima

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "json", 0, 0, 1)
        geojson_result = json.loads(tile_content)

        self.assertTrue(tile_mimetype.endswith('/json'))
        self.assertEqual(geojson_result['type'], 'FeatureCollection')
        self.assertEqual(len(geojson_result['features']), 2)

        cities = []

        # Make sure that the right cities have been returned and that the geometries match

        for feature in geojson_result['features']:
            if feature['properties']['name'] == 'San Francisco':
                cities.append(feature['properties']['name'])
                self.assertTrue(point_sf.almost_equals(asShape(feature['geometry'])))

            elif feature['properties']['name'] == 'Lima':
                cities.append(feature['properties']['name'])
                self.assertTrue(point_lima.almost_equals(asShape(feature['geometry'])))

        self.assertTrue('San Francisco' in cities)
        self.assertTrue('Lima' in cities)

        ##########
        # northeast quadrant should return Berlin

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "json", 0, 1, 1)
        geojson_result = json.loads(tile_content)

        self.assertTrue(tile_mimetype.endswith('/json'))
        self.assertEqual(geojson_result['type'], 'FeatureCollection')
        self.assertEqual(len(geojson_result['features']), 1)
        self.assertTrue('Berlin' in geojson_result['features'][0]['properties']['name'])


    def test_linestring_geojson(self):
        '''Create a line that goes from west to east (clip on)'''
        
        self.defineGeometry('LINESTRING')

        geom = LineString( [(-180, 32), (180, 32)] )

        self.insertTestRow(geom.wkt)

        # we should have a line that clips at 0...

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "json", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        geojson_result = json.loads(tile_content)
        west_hemisphere_geometry = asShape(geojson_result['features'][0]['geometry'])
        expected_geometry = LineString([(-180, 32), (180, 32)])
        self.assertTrue(expected_geometry.almost_equals(west_hemisphere_geometry))


    def test_polygon_geojson(self):
        '''
        Create a polygon to cover the world and make sure it is "similar" (clip on)
        '''
        
        self.defineGeometry('POLYGON')

        geom = Polygon( [(-180, -85.05),
                         ( 180, -85.05),
                         ( 180, 85.05), 
                         (-180, 85.05), 
                         (-180, -85.05)])

        self.insertTestRow(geom.wkt)
        
        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "json", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        geojson_result = json.loads(tile_content)
        
        result_geom = asShape(geojson_result['features'][0]['geometry'])
        expected_geom = Polygon( [(-180, -85.05), (180, -85.05), (180, 85.05), (-180, 85.05), (-180, -85.05)])

        # What is going on here is a bit unorthodox, but let me explain. The clipping
        # code inside TileStache relies on GEOS Intersection alongside some TileStache code
        # that creates a clipping geometry based on the tile perimeter. The tile perimeter
        # is made out of 17 (x,y) coordinates and not a box. Hence, the GEOS::Intersection
        # os that perimeter with the geometry of the vector we get back from the data provider
        # can end with extra vertices. Although it is the right shape, we cannot do a straight
        # comparisson because the expected geometry and the returned geometry *may* have extra
        # vertices. Simplify() will not do much because the distance of the vertices can clearly
        # be bigger than the tolerance. 
        #
        # To add to this, because of double precision, the vertices may not be exact.
        # An optional way to find out if two shapes are close enough, is to buffer the two features
        # by just a little bit and then subtract each other like so:
        #
        #             geometry1.difference(geometry2) == empty set?
        #             geometry2.difference(geometry1) == empty set?
        # 
        # If both geometries are empty, then they are similar. Hence what you see below
        
        self.assertTrue(result_geom.difference(expected_geom.buffer(0.001)).is_empty)
        self.assertTrue(expected_geom.difference(result_geom.buffer(0.001)).is_empty)
    

    def test_linestring_multi_geojson(self):
        '''Create a line that goes from west to east (clip on), and test it in MultiProvider'''
        
        self.defineGeometry('LINESTRING')

        geom = LineString( [(-180, 32), (180, 32)] )

        self.insertTestRow(geom.wkt)

        # we should have a line that clips at 0...

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_multi", "json", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        geojson_result = json.loads(tile_content)
        
        feature1, feature2 = geojson_result['vectile_test'], geojson_result['vectile_copy']
        self.assertEqual(feature1['type'], 'FeatureCollection')
        self.assertEqual(feature2['type'], 'FeatureCollection')
        self.assertEqual(feature1['features'][0]['type'], 'Feature')
        self.assertEqual(feature2['features'][0]['type'], 'Feature')
        self.assertEqual(feature1['features'][0]['geometry']['type'], 'LineString')
        self.assertEqual(feature2['features'][0]['geometry']['type'], 'LineString')
        self.assertEqual(feature1['features'][0]['id'], feature2['features'][0]['id'])
        
        self.assertTrue('clipped' not in feature1['features'][0])
        self.assertTrue(feature2['features'][0]['clipped'])


    def test_points_topojson(self):
        '''
        Create 3 points (2 on west, 1 on east hemisphere) and retrieve as topojson.
        2 points should be returned in western hemisphere and 1 on eastern at zoom level 1
        (clip on)
        '''
        
        self.defineGeometry('POINT')

        point_sf = Point(-122.4183, 37.7750)
        point_berlin = Point(13.4127, 52.5233)
        point_lima = Point(-77.0283, 12.0433)

        self.insertTestRow(point_sf.wkt, 'San Francisco')
        self.insertTestRow(point_berlin.wkt, 'Berlin')
        self.insertTestRow(point_lima.wkt, 'Lima')

        ########
        # northwest quadrant should return San Francisco and Lima

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "topojson", 0, 0, 1)
        topojson_result = json.loads(tile_content)

        self.assertTrue(tile_mimetype.endswith('/json'))
        print topojson_result
        self.assertEqual(topojson_result['type'], 'Topology')
        self.assertEqual(len(topojson_result['objects']['vectile']['geometries']), 2)

        cities = []

        # Make sure that the right cities have been returned and that the geometries match
        
        topojson_xform = get_topo_transform(topojson_result)

        for feature in topojson_result['objects']['vectile']['geometries']:
            lon, lat = topojson_xform(feature['coordinates'])
            
            if feature['properties']['name'] == 'San Francisco':
                cities.append(feature['properties']['name'])
                self.assertTrue(hypot(point_sf.x - lon, point_sf.y - lat) < 1)

            elif feature['properties']['name'] == 'Lima':
                cities.append(feature['properties']['name'])
                print feature['coordinates']
                self.assertTrue(hypot(point_lima.x - lon, point_lima.y - lat) < 1)

        self.assertTrue('San Francisco' in cities)
        self.assertTrue('Lima' in cities)

        ##########
        # northeast quadrant should return Berlin

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "topojson", 0, 1, 1)
        topojson_result = json.loads(tile_content)

        self.assertTrue(tile_mimetype.endswith('/json'))
        self.assertEqual(topojson_result['type'], 'Topology')
        self.assertEqual(len(topojson_result['objects']['vectile']['geometries']), 1)
        self.assertTrue('Berlin' in topojson_result['objects']['vectile']['geometries'][0]['properties']['name'])


    def test_linestring_topojson(self):
        '''Create a line that goes from west to east (clip on)'''
        
        self.defineGeometry('LINESTRING')

        geom = LineString( [(-180, 32), (180, 32)] )

        self.insertTestRow(geom.wkt)

        # we should have a line that clips at 0...

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "topojson", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        topojson_result = json.loads(tile_content)
        topojson_xform = get_topo_transform(topojson_result)
        
        parts = [topojson_result['arcs'][arc] for arc in topojson_result['objects']['vectile']['geometries'][0]['arcs']]
        parts = [map(topojson_xform, topojson_dediff(part)) for part in parts]
        
        west_hemisphere_geometry = LineString(*parts)
        
        # Close enough?
        self.assertTrue(abs(west_hemisphere_geometry.coords[0][0] + 180) < 2)
        self.assertTrue(abs(west_hemisphere_geometry.coords[1][0] - 180) < 2)
        self.assertTrue(abs(west_hemisphere_geometry.coords[0][1] - 32) < 2)
        self.assertTrue(abs(west_hemisphere_geometry.coords[1][1] - 32) < 2)


    def test_polygon_topojson(self):
        '''
        Create a polygon to cover the world and make sure it is "similar" (clip on)
        '''
        
        self.defineGeometry('POLYGON')

        geom = Polygon( [(-180, -85.0511),
                         ( 180, -85.0511),
                         ( 180, 85.0511), 
                         (-180, 85.0511), 
                         (-180, -85.0511)])

        self.insertTestRow(geom.wkt)
        
        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_test", "topojson", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        topojson_result = json.loads(tile_content)
        topojson_xform = get_topo_transform(topojson_result)
        
        parts = [topojson_result['arcs'][arc[0]] for arc in topojson_result['objects']['vectile']['geometries'][0]['arcs']]
        parts = [map(topojson_xform, topojson_dediff(part)) for part in parts]
        
        result_geom = Polygon(*parts)
        expected_geom = Polygon( [(-180, -85.0511), (180, -85.0511), (180, 85.0511), (-180, 85.0511), (-180, -85.0511)])

        # What is going on here is a bit unorthodox, but let me explain. The clipping
        # code inside TileStache relies on GEOS Intersection alongside some TileStache code
        # that creates a clipping geometry based on the tile perimeter. The tile perimeter
        # is made out of 17 (x,y) coordinates and not a box. Hence, the GEOS::Intersection
        # os that perimeter with the geometry of the vector we get back from the data provider
        # can end with extra vertices. Although it is the right shape, we cannot do a straight
        # comparisson because the expected geometry and the returned geometry *may* have extra
        # vertices. Simplify() will not do much because the distance of the vertices can clearly
        # be bigger than the tolerance. 
        #
        # To add to this, because of double precision, the vertices may not be exact.
        # An optional way to find out if two shapes are close enough, is to buffer the two features
        # by just a little bit and then subtract each other like so:
        #
        #             geometry1.difference(geometry2) == empty set?
        #             geometry2.difference(geometry1) == empty set?
        # 
        # If both geometries are empty, then they are similar. Hence what you see below
        
        # Close enough?
        self.assertTrue(result_geom.difference(expected_geom.buffer(1)).is_empty)
        self.assertTrue(expected_geom.difference(result_geom.buffer(1)).is_empty)


    def test_linestring_multi_topojson(self):
        '''Create a line that goes from west to east (clip on), and test it in MultiProvider'''
        
        self.defineGeometry('LINESTRING')

        geom = LineString( [(-180, 32), (180, 32)] )

        self.insertTestRow(geom.wkt)

        # we should have a line that clips at 0...

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vectile_multi", "topojson", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        topojson_result = json.loads(tile_content)
        
        self.assertEqual(topojson_result['type'], 'Topology')
        self.assertEqual(topojson_result['objects']['vectile_test']['type'], 'GeometryCollection')
        self.assertEqual(topojson_result['objects']['vectile_copy']['type'], 'GeometryCollection')
        
        geom1 = topojson_result['objects']['vectile_test']['geometries'][0]
        geom2 = topojson_result['objects']['vectile_copy']['geometries'][0]
        self.assertEqual(geom1['type'], 'LineString')
        self.assertEqual(geom2['type'], 'LineString')
        self.assertEqual(geom1['id'], geom2['id'])
        
        self.assertTrue('clipped' not in geom1)
        self.assertTrue(geom2['clipped'])

########NEW FILE########
__FILENAME__ = vector_tests
from unittest import TestCase
import json

from osgeo import ogr
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, asShape

from . import utils


# Note these tests rely on the fact that Travis CI created a postgis db.
# If you want to run them locally, create a similar PostGIS database.
# Look at .travis.yml for details.

class PostGISVectorTestBase(object):
    '''
    Base Class for PostGIS Vector tests. Has methods to:

      - CREATE and DROP a single table (self.testTableName) that has a field called name
      - Define a geometry field
      - INSERT a record using a WKT
    '''

    def initTestTable(self, testTableName):
        self.conn = ogr.Open("PG: dbname='test_tilestache' user='postgres'")
        self.testTableName = testTableName
        
        self.cleanTestTable()

        sql = 'CREATE TABLE %s (gid serial PRIMARY KEY, name VARCHAR)' % (self.testTableName,)
        self.conn.ExecuteSQL(sql)

    def defineGeometry(self, geom_type, geom_name = 'geom', srid=4326):
        self.srid = srid
        self.geom_name = geom_name
        
        sql = "SELECT AddGeometryColumn('public', '%s', '%s', %s, '%s', 2)" % \
        (self.testTableName, geom_name, srid, geom_type)

        self.conn.ExecuteSQL(sql)

    def insertTestRow(self, wkt, name=''):
        sql = "INSERT INTO %s (%s, name) VALUES(ST_GeomFromText('%s',%s),'%s')" % \
        (self.testTableName, self.geom_name, wkt, self.srid, name)

        self.conn.ExecuteSQL(sql)

    def cleanTestTable(self):
        self.conn.ExecuteSQL('DROP TABLE if exists %s' % (self.testTableName,))


class VectorProviderTest(PostGISVectorTestBase, TestCase):
    '''Various vector tests on top of PostGIS'''

    def setUp(self):
        self.initTestTable('dummy_table')

        self.config_file_content = '''
        {
           "layers":{
              "vector_test":{
                 "provider":{
                    "name": "vector",
                    "driver" : "PostgreSQL",
                    "parameters": {
                                    "dbname": "test_tilestache", 
                                    "user": "postgres",
                                    "table": "dummy_table"
                    }                    
                 },
                 "projection" : "WGS84"
              }
            },
            "cache": {
                "name": "Test"
            }
        }
        '''

    def tearDown(self):
        self.cleanTestTable()

    def test_points_geojson(self):
        '''
        Create 3 points (2 on west, 1 on east hemisphere) and retrieve as geojson.
        2 points should be returned in western hemisphere and 1 on eastern at zoom level 0
        (clip on)
        '''
        
        self.defineGeometry('POINT')

        point_sf = Point(-122.4183, 37.7750)
        point_berlin = Point(13.4127, 52.5233)
        point_lima = Point(-77.0283, 12.0433)

        self.insertTestRow(point_sf.wkt, 'San Francisco')
        self.insertTestRow(point_berlin.wkt, 'Berlin')
        self.insertTestRow(point_lima.wkt, 'Lima')

        ########
        # western hemisphere should return San Francisco and Lima

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vector_test", "geojson", 0, 0, 0)
        geojson_result = json.loads(tile_content)

        self.assertTrue(tile_mimetype.endswith('/json'))
        self.assertEqual(geojson_result['type'], 'FeatureCollection')
        self.assertEqual(len(geojson_result['features']), 2)

        cities = []

        # Make sure that the right cities have been returned and that the geometries match

        for feature in geojson_result['features']:
            if feature['properties']['name'] == 'San Francisco':
                cities.append(feature['properties']['name'])
                self.assertTrue(point_sf.almost_equals(asShape(feature['geometry'])))

            elif feature['properties']['name'] == 'Lima':
                cities.append(feature['properties']['name'])
                self.assertTrue(point_lima.almost_equals(asShape(feature['geometry'])))

        self.assertTrue('San Francisco' in cities)
        self.assertTrue('Lima' in cities)

        ##########
        # eastern hemisphere should return Berlin

        tile_mimetype, tile_content = utils.request(self.config_file_content, "vector_test", "geojson", 0, 1, 0)
        geojson_result = json.loads(tile_content)

        self.assertTrue(tile_mimetype.endswith('/json'))
        self.assertEqual(geojson_result['type'], 'FeatureCollection')
        self.assertEqual(len(geojson_result['features']), 1)
        self.assertTrue('Berlin' in geojson_result['features'][0]['properties']['name'])


    def test_linestring_geojson(self):
        '''Create a line that goes from west to east (clip on)'''
        
        self.defineGeometry('LINESTRING')

        geom = LineString( [(-180, 32), (180, 32)] )

        self.insertTestRow(geom.wkt)

        # we should have a line that clips at 0...

        # for western hemisphere....
        tile_mimetype, tile_content = utils.request(self.config_file_content, "vector_test", "geojson", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        geojson_result = json.loads(tile_content)
        west_hemisphere_geometry = asShape(geojson_result['features'][0]['geometry'])
        expected_geometry = LineString([(-180, 32), (0, 32)])
        self.assertTrue(expected_geometry.almost_equals(west_hemisphere_geometry))

        # for eastern hemisphere....
        tile_mimetype, tile_content = utils.request(self.config_file_content, "vector_test", "geojson", 0, 1, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        geojson_result = json.loads(tile_content)
        east_hemisphere_geometry = asShape(geojson_result['features'][0]['geometry'])
        expected_geometry = LineString([(0, 32), (180, 32)])
        self.assertTrue(expected_geometry.almost_equals(east_hemisphere_geometry))


    def test_polygon_geojson(self):
        '''
        Create a polygon to cover the world and make sure it is "similar" (clip on)
        '''
        
        self.defineGeometry('POLYGON')

        geom = Polygon( [(-180, -90),
                         ( 180, -90),
                         ( 180, 90), 
                         (-180, 90), 
                         (-180, -90)])

        self.insertTestRow(geom.wkt)
        
        tile_mimetype, tile_content = utils.request(self.config_file_content, "vector_test", "geojson", 0, 0, 0)
        self.assertTrue(tile_mimetype.endswith('/json'))
        geojson_result = json.loads(tile_content)
        
        result_geom = asShape(geojson_result['features'][0]['geometry'])
        expected_geom = Polygon( [(-180, -90), (0, -90), (0, 90), (-180, 90), (-180, -90)])

        # What is going on here is a bit unorthodox, but let me explain. The clipping
        # code inside TileStache relies on GEOS Intersection alongside some TileStache code
        # that creates a clipping geometry based on the tile perimeter. The tile perimeter
        # is made out of 17 (x,y) coordinates and not a box. Hence, the GEOS::Intersection
        # os that perimeter with the geometry of the vector we get back from the data provider
        # can end with extra vertices. Although it is the right shape, we cannot do a straight
        # comparisson because the expected geometry and the returned geometry *may* have extra
        # vertices. Simplify() will not do much because the distance of the vertices can clearly
        # be bigger than the tolerance. 
        #
        # To add to this, because of double precision, the vertices may not be exact.
        # An optional way to find out if two shapes are close enough, is to buffer the two features
        # by just a little bit and then subtract each other like so:
        #
        #             geometry1.difference(geometry2) == empty set?
        #             geometry2.difference(geometry1) == empty set?
        # 
        # If both geometries are empty, then they are similar. Hence what you see below
        
        self.assertTrue(result_geom.difference(expected_geom.buffer(0.001)).is_empty)
        self.assertTrue(expected_geom.difference(result_geom.buffer(0.001)).is_empty)



########NEW FILE########
__FILENAME__ = Caches
""" The cache bits of TileStache.

A Cache is the part of TileStache that stores static files to speed up future
requests. A few default caches are found here, but it's possible to define your
own and pull them into TileStache dynamically by class name.

Built-in providers:
- test
- disk
- multi
- memcache
- s3

Example built-in cache, for JSON configuration file:

    "cache": {
      "name": "Disk",
      "path": "/tmp/stache",
      "umask": "0000"
    }

Example external cache, for JSON configuration file:

    "cache": {
      "class": "Module:Classname",
      "kwargs": {"frob": "yes"}
    }

- The "class" value is split up into module and classname, and dynamically
  included. If this doesn't work for some reason, TileStache will fail loudly
  to let you know.
- The "kwargs" value is fed to the class constructor as a dictionary of keyword
  args. If your defined class doesn't accept any of these keyword arguments,
  TileStache will throw an exception.

A cache must provide these methods: lock(), unlock(), read(), and save().
Each method accepts three arguments:

- layer: instance of a Layer.
- coord: single Coordinate that represents a tile.
- format: string like "png" or "jpg" that is used as a filename extension.

The save() method accepts an additional argument before the others:

- body: raw content to save to the cache.

TODO: add stale_lock_timeout and cache_lifespan to cache API in v2.
"""

import os
import sys
import time
import gzip

from tempfile import mkstemp
from os.path import isdir, exists, dirname, basename, join as pathjoin

from .Core import KnownUnknown
from . import Memcache
from . import Redis
from . import S3

def getCacheByName(name):
    """ Retrieve a cache object by name.
    
        Raise an exception if the name doesn't work out.
    """
    if name.lower() == 'test':
        return Test

    elif name.lower() == 'disk':
        return Disk

    elif name.lower() == 'multi':
        return Multi

    elif name.lower() == 'memcache':
        return Memcache.Cache

    elif name.lower() == 'redis':
        return Redis.Cache

    elif name.lower() == 's3':
        return S3.Cache

    raise Exception('Unknown cache name: "%s"' % name)

class Test:
    """ Simple cache that doesn't actually cache anything.
    
        Activity is optionally logged, though.
    
        Example configuration:

            "cache": {
              "name": "Test",
              "verbose": true
            }

        Extra configuration parameters:
        - verbose: optional boolean flag to write cache activities to a logging
          function, defaults to False if omitted.
    """
    def __init__(self, logfunc=None):
        self.logfunc = logfunc

    def _description(self, layer, coord, format):
        """
        """
        name = layer.name()
        tile = '%(zoom)d/%(column)d/%(row)d' % coord.__dict__

        return ' '.join( (name, tile, format) )
    
    def lock(self, layer, coord, format):
        """ Pretend to acquire a cache lock for this tile.
        """
        name = self._description(layer, coord, format)
        
        if self.logfunc:
            self.logfunc('Test cache lock: ' + name)
    
    def unlock(self, layer, coord, format):
        """ Pretend to release a cache lock for this tile.
        """
        name = self._description(layer, coord, format)

        if self.logfunc:
            self.logfunc('Test cache unlock: ' + name)
    
    def remove(self, layer, coord, format):
        """ Pretend to remove a cached tile.
        """
        name = self._description(layer, coord, format)

        if self.logfunc:
            self.logfunc('Test cache remove: ' + name)
    
    def read(self, layer, coord, format):
        """ Pretend to read a cached tile.
        """
        name = self._description(layer, coord, format)
        
        if self.logfunc:
            self.logfunc('Test cache read: ' + name)

        return None
    
    def save(self, body, layer, coord, format):
        """ Pretend to save a cached tile.
        """
        name = self._description(layer, coord, format)
        
        if self.logfunc:
            self.logfunc('Test cache save: %d bytes to %s' % (len(body), name))

class Disk:
    """ Caches files to disk.
    
        Example configuration:

            "cache": {
              "name": "Disk",
              "path": "/tmp/stache",
              "umask": "0000",
              "dirs": "portable"
            }

        Extra parameters:
        - path: required local directory path where files should be stored.
        - umask: optional string representation of octal permission mask
          for stored files. Defaults to 0022.
        - dirs: optional string saying whether to create cache directories that
          are safe, portable or quadtile. For an example tile 12/656/1582.png,
          "portable" creates matching directory trees while "safe" guarantees
          directories with fewer files, e.g. 12/000/656/001/582.png.
          Defaults to safe.
        - gzip: optional list of file formats that should be stored in a
          compressed form. Defaults to "txt", "text", "json", and "xml".
          Provide an empty list in the configuration for no compression.

        If your configuration file is loaded from a remote location, e.g.
        "http://example.com/tilestache.cfg", the path *must* be an unambiguous
        filesystem path, e.g. "file:///tmp/cache"
    """
    def __init__(self, path, umask=0022, dirs='safe', gzip='txt text json xml'.split()):
        self.cachepath = path
        self.umask = int(umask)
        self.dirs = dirs
        self.gzip = [format.lower() for format in gzip]

    def _is_compressed(self, format):
        return format.lower() in self.gzip
    
    def _filepath(self, layer, coord, format):
        """
        """
        l = layer.name()
        z = '%d' % coord.zoom
        e = format.lower()
        e += self._is_compressed(format) and '.gz' or ''
        
        if self.dirs == 'safe':
            x = '%06d' % coord.column
            y = '%06d' % coord.row

            x1, x2 = x[:3], x[3:]
            y1, y2 = y[:3], y[3:]
            
            filepath = os.sep.join( (l, z, x1, x2, y1, y2 + '.' + e) )
            
        elif self.dirs == 'portable':
            x = '%d' % coord.column
            y = '%d' % coord.row

            filepath = os.sep.join( (l, z, x, y + '.' + e) )
            
        elif self.dirs == 'quadtile':
            pad, length = 1 << 31, 1 + coord.zoom

            # two binary strings, one per dimension
            xs = bin(pad + int(coord.column))[-length:]
            ys = bin(pad + int(coord.row))[-length:]
            
            # interleave binary bits into plain digits, 0-3.
            # adapted from ModestMaps.Tiles.toMicrosoft()
            dirpath = ''.join([str(int(y+x, 2)) for (x, y) in zip(xs, ys)])
            
            # built a list of nested directory names and a file basename
            parts = [dirpath[i:i+3] for i in range(0, len(dirpath), 3)]
            
            filepath = os.sep.join([l] + parts[:-1] + [parts[-1] + '.' + e])
        
        else:
            raise KnownUnknown('Please provide a valid "dirs" parameter to the Disk cache, either "safe", "portable" or "quadtile" but not "%s"' % self.dirs)

        return filepath

    def _fullpath(self, layer, coord, format):
        """
        """
        filepath = self._filepath(layer, coord, format)
        fullpath = pathjoin(self.cachepath, filepath)

        return fullpath

    def _lockpath(self, layer, coord, format):
        """
        """
        return self._fullpath(layer, coord, format) + '.lock'
    
    def lock(self, layer, coord, format):
        """ Acquire a cache lock for this tile.
        
            Returns nothing, but blocks until the lock has been acquired.
            Lock is implemented as an empty directory next to the tile file.
        """
        lockpath = self._lockpath(layer, coord, format)
        due = time.time() + layer.stale_lock_timeout
        
        while True:
            # try to acquire a directory lock, repeating if necessary.
            try:
                umask_old = os.umask(self.umask)
                
                if time.time() > due:
                    # someone left the door locked.
                    try:
                        os.rmdir(lockpath)
                    except OSError:
                        # Oh - no they didn't.
                        pass
                
                os.makedirs(lockpath, 0777&~self.umask)
                break
            except OSError, e:
                if e.errno != 17:
                    raise
                time.sleep(.2)
            finally:
                os.umask(umask_old)
    
    def unlock(self, layer, coord, format):
        """ Release a cache lock for this tile.

            Lock is implemented as an empty directory next to the tile file.
        """
        lockpath = self._lockpath(layer, coord, format)

        try:
            os.rmdir(lockpath)
        except OSError:
            # Ok, someone else deleted it already
            pass
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile.
        """
        fullpath = self._fullpath(layer, coord, format)
        
        try:
            os.remove(fullpath)
        except OSError, e:
            # errno=2 means that the file does not exist, which is fine
            if e.errno != 2:
                raise
        
    def read(self, layer, coord, format):
        """ Read a cached tile.
        """
        fullpath = self._fullpath(layer, coord, format)
        
        if not exists(fullpath):
            return None

        age = time.time() - os.stat(fullpath).st_mtime
        
        if layer.cache_lifespan and age > layer.cache_lifespan:
            return None
    
        elif self._is_compressed(format):
            return gzip.open(fullpath, 'r').read()

        else:
            body = open(fullpath, 'rb').read()
            return body
    
    def save(self, body, layer, coord, format):
        """ Save a cached tile.
        """
        fullpath = self._fullpath(layer, coord, format)
        
        try:
            umask_old = os.umask(self.umask)
            os.makedirs(dirname(fullpath), 0777&~self.umask)
        except OSError, e:
            if e.errno != 17:
                raise
        finally:
            os.umask(umask_old)

        suffix = '.' + format.lower()
        suffix += self._is_compressed(format) and '.gz' or ''

        fh, tmp_path = mkstemp(dir=self.cachepath, suffix=suffix)
        
        if self._is_compressed(format):
            os.close(fh)
            tmp_file = gzip.open(tmp_path, 'w')
            tmp_file.write(body)
            tmp_file.close()
        else:
            os.write(fh, body)
            os.close(fh)
        
        try:
            os.rename(tmp_path, fullpath)
        except OSError:
            os.unlink(fullpath)
            os.rename(tmp_path, fullpath)

        os.chmod(fullpath, 0666&~self.umask)

class Multi:
    """ Caches tiles to multiple, ordered caches.
        
        Multi cache is well-suited for a speed-to-capacity gradient, for
        example a combination of Memcache and S3 to take advantage of the high
        speed of memcache and the high capacity of S3. Each tier of caching is
        checked sequentially when reading from the cache, while all tiers are
        used together for writing. Locks are only used with the first cache.
        
        Example configuration:
        
            "cache": {
              "name": "Multi",
              "tiers": [
                  {
                     "name": "Memcache",
                     "servers": ["127.0.0.1:11211"]
                  },
                  {
                     "name": "Disk",
                     "path": "/tmp/stache"
                  }
              ]
            }

        Multi cache parameters:
        
          tiers
            Required list of cache configurations. The fastest, most local
            cache should be at the beginning of the list while the slowest or
            most remote cache should be at the end. Memcache and S3 together
            make a great pair.

    """
    def __init__(self, tiers):
        self.tiers = tiers

    def lock(self, layer, coord, format):
        """ Acquire a cache lock for this tile in the first tier.
        
            Returns nothing, but blocks until the lock has been acquired.
        """
        return self.tiers[0].lock(layer, coord, format)
    
    def unlock(self, layer, coord, format):
        """ Release a cache lock for this tile in the first tier.
        """
        return self.tiers[0].unlock(layer, coord, format)
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile from every tier.
        """
        for (index, cache) in enumerate(self.tiers):
            cache.remove(layer, coord, format)
        
    def read(self, layer, coord, format):
        """ Read a cached tile.
        
            Start at the first tier and work forwards until a cached tile
            is found. When found, save it back to the earlier tiers for faster
            access on future requests.
        """
        for (index, cache) in enumerate(self.tiers):
            body = cache.read(layer, coord, format)
            
            if body:
                # save the body in earlier tiers for speedier access
                for cache in self.tiers[:index]:
                    cache.save(body, layer, coord, format)
                
                return body
        
        return None
    
    def save(self, body, layer, coord, format):
        """ Save a cached tile.
        
            Every tier gets a saved copy.
        """
        for (index, cache) in enumerate(self.tiers):
            cache.save(body, layer, coord, format)

########NEW FILE########
__FILENAME__ = Config
""" The configuration bits of TileStache.

TileStache configuration is stored in JSON files, and is composed of two main
top-level sections: "cache" and "layers". There are examples of both in this
minimal sample configuration:

    {
      "cache": {"name": "Test"},
      "layers": {
        "example": {
            "provider": {"name": "mapnik", "mapfile": "examples/style.xml"},,
            "projection": "spherical mercator"
        } 
      }
    }

The contents of the "cache" section are described in greater detail in the
TileStache.Caches module documentation. Here is a different sample:

    "cache": {
      "name": "Disk",
      "path": "/tmp/stache",
      "umask": "0000"
    }

The "layers" section is a dictionary of layer names which are specified in the
URL of an individual tile. More detail on the configuration of individual layers
can be found in the TileStache.Core module documentation. Another sample:

    {
      "cache": ...,
      "layers": 
      {
        "example-name":
        {
            "provider": { ... },
            "metatile": { ... },
            "preview": { ... },
            "stale lock timeout": ...,
            "projection": ...
        }
      }
    }

Configuration also supports these additional settings:

- "logging": one of "debug", "info", "warning", "error" or "critical", as
  described in Python's logging module: http://docs.python.org/howto/logging.html

- "index": configurable index pages for the front page of an instance.
  A custom index can be specified as a filename relative to the configuration
  location. Typically an HTML document would be given here, but other kinds of
  files such as images can be used, with MIME content-type headers determined
  by mimetypes.guess_type. A simple text greeting is displayed if no index
  is provided.

In-depth explanations of the layer components can be found in the module
documentation for TileStache.Providers, TileStache.Core, and TileStache.Geography.
"""

import sys
import logging
from sys import stderr, modules
from os.path import realpath, join as pathjoin
from urlparse import urljoin, urlparse
from mimetypes import guess_type
from urllib import urlopen
from json import dumps

try:
    from json import dumps as json_dumps
except ImportError:
    from simplejson import dumps as json_dumps

from ModestMaps.Geo import Location
from ModestMaps.Core import Coordinate

import Core
import Caches
import Providers
import Geography

class Configuration:
    """ A complete site configuration, with a collection of Layer objects.
    
        Attributes:
        
          cache:
            Cache instance, e.g. TileStache.Caches.Disk etc.
            See TileStache.Caches for details on what makes
            a usable cache.
        
          layers:
            Dictionary of layers keyed by name.
            
            When creating a custom layers dictionary, e.g. for dynamic
            layer collections backed by some external configuration,
            these dictionary methods must be provided for a complete
            collection of layers:
            
              keys():
                Return list of layer name strings.

              items():
                Return list of (name, layer) pairs.

              __contains__(key):
                Return boolean true if given key is an existing layer.
                
              __getitem__(key):
                Return existing layer object for given key or raise KeyError.
        
          dirpath:
            Local filesystem path for this configuration,
            useful for expanding relative paths.
          
        Optional attribute:
        
          index:
            Mimetype, content tuple for default index response.
    """
    def __init__(self, cache, dirpath):
        self.cache = cache
        self.dirpath = dirpath
        self.layers = {}
        
        self.index = 'text/plain', 'TileStache bellows hello.'

class Bounds:
    """ Coordinate bounding box for tiles.
    """
    def __init__(self, upper_left_high, lower_right_low):
        """ Two required Coordinate objects defining tile pyramid bounds.
        
            Boundaries are inclusive: upper_left_high is the left-most column,
            upper-most row, and highest zoom level; lower_right_low is the
            right-most column, furthest-dwn row, and lowest zoom level.
        """
        self.upper_left_high = upper_left_high
        self.lower_right_low = lower_right_low
    
    def excludes(self, tile):
        """ Check a tile Coordinate against the bounds, return true/false.
        """
        if tile.zoom > self.upper_left_high.zoom:
            # too zoomed-in
            return True
        
        if tile.zoom < self.lower_right_low.zoom:
            # too zoomed-out
            return True

        # check the top-left tile corner against the lower-right bound
        _tile = tile.zoomTo(self.lower_right_low.zoom)
        
        if _tile.column > self.lower_right_low.column:
            # too far right
            return True
        
        if _tile.row > self.lower_right_low.row:
            # too far down
            return True

        # check the bottom-right tile corner against the upper-left bound
        __tile = tile.right().down().zoomTo(self.upper_left_high.zoom)
        
        if __tile.column < self.upper_left_high.column:
            # too far left
            return True
        
        if __tile.row < self.upper_left_high.row:
            # too far up
            return True
        
        return False
    
    def __str__(self):
        return 'Bound %s - %s' % (self.upper_left_high, self.lower_right_low)

class BoundsList:
    """ Multiple coordinate bounding boxes for tiles.
    """
    def __init__(self, bounds):
        """ Single argument is a list of Bounds objects.
        """
        self.bounds = bounds
    
    def excludes(self, tile):
        """ Check a tile Coordinate against the bounds, return false if none match.
        """
        for bound in self.bounds:
            if not bound.excludes(tile):   
                return False
        
        # Nothing worked.
        return True

def buildConfiguration(config_dict, dirpath='.'):
    """ Build a configuration dictionary into a Configuration object.
    
        The second argument is an optional dirpath that specifies where in the
        local filesystem the parsed dictionary originated, to make it possible
        to resolve relative paths. It might be a path or more likely a full
        URL including the "file://" prefix.
    """
    scheme, h, path, p, q, f = urlparse(dirpath)
    
    if scheme in ('', 'file'):
        sys.path.insert(0, path)
    
    cache_dict = config_dict.get('cache', {})
    cache = _parseConfigfileCache(cache_dict, dirpath)
    
    config = Configuration(cache, dirpath)
    
    for (name, layer_dict) in config_dict.get('layers', {}).items():
        config.layers[name] = _parseConfigfileLayer(layer_dict, config, dirpath)

    if 'index' in config_dict:
        index_href = urljoin(dirpath, config_dict['index'])
        index_body = urlopen(index_href).read()
        index_type = guess_type(index_href)
        
        config.index = index_type[0], index_body
    
    if 'logging' in config_dict:
        level = config_dict['logging'].upper()
    
        if hasattr(logging, level):
            logging.basicConfig(level=getattr(logging, level))
    
    return config

def enforcedLocalPath(relpath, dirpath, context='Path'):
    """ Return a forced local path, relative to a directory.
    
        Throw an error if the combination of path and directory seems to
        specify a remote path, e.g. "/path" and "http://example.com".
    
        Although a configuration file can be parsed from a remote URL, some
        paths (e.g. the location of a disk cache) must be local to the server.
        In cases where we mix a remote configuration location with a local
        cache location, e.g. "http://example.com/tilestache.cfg", the disk path
        must include the "file://" prefix instead of an ambiguous absolute
        path such as "/tmp/tilestache".
    """
    parsed_dir = urlparse(dirpath)
    parsed_rel = urlparse(relpath)
    
    if parsed_rel.scheme not in ('file', ''):
        raise Core.KnownUnknown('%s path must be a local file path, absolute or "file://", not "%s".' % (context, relpath))
    
    if parsed_dir.scheme not in ('file', '') and parsed_rel.scheme != 'file':
        raise Core.KnownUnknown('%s path must start with "file://" in a remote configuration ("%s" relative to %s)' % (context, relpath, dirpath))
    
    if parsed_rel.scheme == 'file':
        # file:// is an absolute local reference for the disk cache.
        return parsed_rel.path

    if parsed_dir.scheme == 'file':
        # file:// is an absolute local reference for the directory.
        return urljoin(parsed_dir.path, parsed_rel.path)
    
    # nothing has a scheme, it's probably just a bunch of
    # dumb local paths, so let's see what happens next.
    return pathjoin(dirpath, relpath)

def _parseConfigfileCache(cache_dict, dirpath):
    """ Used by parseConfigfile() to parse just the cache parts of a config.
    """
    if 'name' in cache_dict:
        _class = Caches.getCacheByName(cache_dict['name'])
        kwargs = {}
        
        def add_kwargs(*keys):
            """ Populate named keys in kwargs from cache_dict.
            """
            for key in keys:
                if key in cache_dict:
                    kwargs[key] = cache_dict[key]
        
        if _class is Caches.Test:
            if cache_dict.get('verbose', False):
                kwargs['logfunc'] = lambda msg: stderr.write(msg + '\n')
    
        elif _class is Caches.Disk:
            kwargs['path'] = enforcedLocalPath(cache_dict['path'], dirpath, 'Disk cache path')
            
            if 'umask' in cache_dict:
                kwargs['umask'] = int(cache_dict['umask'], 8)
            
            add_kwargs('dirs', 'gzip')
        
        elif _class is Caches.Multi:
            kwargs['tiers'] = [_parseConfigfileCache(tier_dict, dirpath)
                               for tier_dict in cache_dict['tiers']]
    
        elif _class is Caches.Memcache.Cache:
            if 'key prefix' in cache_dict:
                kwargs['key_prefix'] = cache_dict['key prefix']
        
            add_kwargs('servers', 'lifespan', 'revision')

        elif _class is Caches.Redis.Cache:
            if 'key prefix' in cache_dict:
                kwargs['key_prefix'] = cache_dict['key prefix']

            add_kwargs('host', 'port', 'db')
    
        elif _class is Caches.S3.Cache:
            add_kwargs('bucket', 'access', 'secret', 'use_locks', 'path', 'reduced_redundancy')
    
        else:
            raise Exception('Unknown cache: %s' % cache_dict['name'])
        
    elif 'class' in cache_dict:
        _class = loadClassPath(cache_dict['class'])
        kwargs = cache_dict.get('kwargs', {})
        kwargs = dict( [(str(k), v) for (k, v) in kwargs.items()] )

    else:
        raise Exception('Missing required cache name or class: %s' % json_dumps(cache_dict))

    cache = _class(**kwargs)

    return cache

def _parseLayerBounds(bounds_dict, projection):
    """
    """
    north, west = bounds_dict.get('north', 89), bounds_dict.get('west', -180)
    south, east = bounds_dict.get('south', -89), bounds_dict.get('east', 180)
    high, low = bounds_dict.get('high', 31), bounds_dict.get('low', 0)
    
    try:
        ul_hi = projection.locationCoordinate(Location(north, west)).zoomTo(high)
        lr_lo = projection.locationCoordinate(Location(south, east)).zoomTo(low)
    except TypeError:
        raise Core.KnownUnknown('Bad bounds for layer, need north, south, east, west, high, and low: ' + dumps(bounds_dict))
    
    return Bounds(ul_hi, lr_lo)

def _parseConfigfileLayer(layer_dict, config, dirpath):
    """ Used by parseConfigfile() to parse just the layer parts of a config.
    """
    projection = layer_dict.get('projection', 'spherical mercator')
    projection = Geography.getProjectionByName(projection)
    
    #
    # Add cache lock timeouts and preview arguments
    #
    
    layer_kwargs = {}
    
    if 'cache lifespan' in layer_dict:
        layer_kwargs['cache_lifespan'] = int(layer_dict['cache lifespan'])
    
    if 'stale lock timeout' in layer_dict:
        layer_kwargs['stale_lock_timeout'] = int(layer_dict['stale lock timeout'])
    
    if 'write cache' in layer_dict:
        layer_kwargs['write_cache'] = bool(layer_dict['write cache'])
    
    if 'allowed origin' in layer_dict:
        layer_kwargs['allowed_origin'] = str(layer_dict['allowed origin'])
    
    if 'maximum cache age' in layer_dict:
        layer_kwargs['max_cache_age'] = int(layer_dict['maximum cache age'])
    
    if 'redirects' in layer_dict:
        layer_kwargs['redirects'] = dict(layer_dict['redirects'])
    
    if 'tile height' in layer_dict:
        layer_kwargs['tile_height'] = int(layer_dict['tile height'])
    
    if 'preview' in layer_dict:
        preview_dict = layer_dict['preview']
        
        for (key, func) in zip(('lat', 'lon', 'zoom', 'ext'), (float, float, int, str)):
            if key in preview_dict:
                layer_kwargs['preview_' + key] = func(preview_dict[key])
    
    #
    # Do the bounds
    #
    
    if 'bounds' in layer_dict:
        if type(layer_dict['bounds']) is dict:
            layer_kwargs['bounds'] = _parseLayerBounds(layer_dict['bounds'], projection)
    
        elif type(layer_dict['bounds']) is list:
            bounds = [_parseLayerBounds(b, projection) for b in layer_dict['bounds']]
            layer_kwargs['bounds'] = BoundsList(bounds)
    
        else:
            raise Core.KnownUnknown('Layer bounds must be a dictionary, not: ' + dumps(layer_dict['bounds']))
    
    #
    # Do the metatile
    #

    meta_dict = layer_dict.get('metatile', {})
    metatile_kwargs = {}

    for k in ('buffer', 'rows', 'columns'):
        if k in meta_dict:
            metatile_kwargs[k] = int(meta_dict[k])
    
    metatile = Core.Metatile(**metatile_kwargs)
    
    #
    # Do the per-format options
    #
    
    jpeg_kwargs = {}
    png_kwargs = {}

    if 'jpeg options' in layer_dict:
        jpeg_kwargs = dict([(str(k), v) for (k, v) in layer_dict['jpeg options'].items()])

    if 'png options' in layer_dict:
        png_kwargs = dict([(str(k), v) for (k, v) in layer_dict['png options'].items()])

    #
    # Do the provider
    #

    provider_dict = layer_dict['provider']

    if 'name' in provider_dict:
        _class = Providers.getProviderByName(provider_dict['name'])
        provider_kwargs = _class.prepareKeywordArgs(provider_dict)
        
    elif 'class' in provider_dict:
        _class = loadClassPath(provider_dict['class'])
        provider_kwargs = provider_dict.get('kwargs', {})
        provider_kwargs = dict( [(str(k), v) for (k, v) in provider_kwargs.items()] )

    else:
        raise Exception('Missing required provider name or class: %s' % json_dumps(provider_dict))
    
    #
    # Finish him!
    #

    layer = Core.Layer(config, projection, metatile, **layer_kwargs)
    layer.provider = _class(layer, **provider_kwargs)
    layer.setSaveOptionsJPEG(**jpeg_kwargs)
    layer.setSaveOptionsPNG(**png_kwargs)
    
    return layer

def loadClassPath(classpath):
    """ Load external class based on a path.
        
        Example classpath: "Module.Submodule:Classname".
    
        Equivalent soon-to-be-deprecated classpath: "Module.Submodule.Classname".
    """
    if ':' in classpath:
        #
        # Just-added support for "foo:blah"-style classpaths.
        #
        modname, objname = classpath.split(':', 1)

        try:
            __import__(modname)
            module = modules[modname]
            _class = eval(objname, module.__dict__)
            
            if _class is None:
                raise Exception('eval(%(objname)s) in %(modname)s came up None' % locals())

        except Exception, e:
            raise Core.KnownUnknown('Tried to import %s, but: %s' % (classpath, e))
    
    else:
        #
        # Support for "foo.blah"-style classpaths, TODO: deprecate this in v2.
        #
        classpath = classpath.split('.')
    
        try:
            module = __import__('.'.join(classpath[:-1]), fromlist=str(classpath[-1]))
        except ImportError, e:
            raise Core.KnownUnknown('Tried to import %s, but: %s' % ('.'.join(classpath), e))
    
        try:
            _class = getattr(module, classpath[-1])
        except AttributeError, e:
            raise Core.KnownUnknown('Tried to import %s, but: %s' % ('.'.join(classpath), e))

    return _class

########NEW FILE########
__FILENAME__ = Core
""" The core class bits of TileStache.

Two important classes can be found here.

Layer represents a set of tiles in TileStache. It keeps references to
providers, projections, a Configuration instance, and other details required
for to the storage and rendering of a tile set. Layers are represented in the
configuration file as a dictionary:

    {
      "cache": ...,
      "layers": 
      {
        "example-name":
        {
          "provider": { ... },
          "metatile": { ... },
          "preview": { ... },
          "projection": ...,
          "stale lock timeout": ...,
          "cache lifespan": ...,
          "write cache": ...,
          "bounds": { ... },
          "allowed origin": ...,
          "maximum cache age": ...,
          "redirects": ...,
          "tile height": ...,
          "jpeg options": ...,
          "png options": ...
        }
      }
    }

- "provider" refers to a Provider, explained in detail in TileStache.Providers.
- "metatile" optionally makes it possible for multiple individual tiles to be
  rendered at one time, for greater speed and efficiency. This is commonly used
  for the Mapnik provider. See below for more information on metatiles.
- "preview" optionally overrides the starting point for the built-in per-layer
  slippy map preview, useful for image-based layers where appropriate.
  See below for more information on the preview.
- "projection" names a geographic projection, explained in TileStache.Geography.
  If omitted, defaults to spherical mercator.
- "stale lock timeout" is an optional number of seconds to wait before forcing
  a lock that might be stuck. This is defined on a per-layer basis, rather than
  for an entire cache at one time, because you may have different expectations
  for the rendering speeds of different layer configurations. Defaults to 15.
- "cache lifespan" is an optional number of seconds that cached tiles should
  be stored. This is defined on a per-layer basis. Defaults to forever if None,
  0 or omitted.
- "write cache" is an optional boolean value to allow skipping cache write
  altogether. This is defined on a per-layer basis. Defaults to true if omitted.
- "bounds" is an optional dictionary of six tile boundaries to limit the
  rendered area: low (lowest zoom level), high (highest zoom level), north,
  west, south, and east (all in degrees).
- "allowed origin" is an optional string that shows up in the response HTTP
  header Access-Control-Allow-Origin, useful for when you need to provide
  javascript direct access to response data such as GeoJSON or pixel values.
  The header is part of a W3C working draft (http://www.w3.org/TR/cors/).
- "maximum cache age" is an optional number of seconds used to control behavior
  of downstream caches. Causes TileStache responses to include Cache-Control
  and Expires HTTP response headers. Useful when TileStache is itself hosted
  behind an HTTP cache such as Squid, Cloudfront, or Akamai.
- "redirects" is an optional dictionary of per-extension HTTP redirects,
  treated as lowercase. Useful in cases where your tile provider can support
  many formats but you want to enforce limits to save on cache usage.
  If a request is made for a tile with an extension in the dictionary keys,
  a response can be generated that redirects the client to the same tile
  with another extension.
- "tile height" gives the height of the image tile in pixels. You almost always
  want to leave this at the default value of 256, but you can use a value of 512
  to create double-size, double-resolution tiles for high-density phone screens.
- "jpeg options" is an optional dictionary of JPEG creation options, passed
  through to PIL: http://effbot.org/imagingbook/format-jpeg.htm.
- "png options" is an optional dictionary of PNG creation options, passed
  through to PIL: http://effbot.org/imagingbook/format-png.htm.

The public-facing URL of a single tile for this layer might look like this:

    http://example.com/tilestache.cgi/example-name/0/0/0.png

Sample JPEG creation options:

    {
      "quality": 90,
      "progressive": true,
      "optimize": true
    }

Sample PNG creation options:

    {
      "optimize": true,
      "palette": "filename.act"
    }

Sample bounds:

    {
        "low": 9, "high": 15,
        "south": 37.749, "west": -122.358,
        "north": 37.860, "east": -122.113
    }

Metatile represents a larger area to be rendered at one time. Metatiles are
represented in the configuration file as a dictionary:

    {
      "rows": 4,
      "columns": 4,
      "buffer": 64
    }

- "rows" and "columns" are the height and width of the metatile measured in
  tiles. This example metatile is four rows tall and four columns wide, so it
  will render sixteen tiles simultaneously.
- "buffer" is a buffer area around the metatile, measured in pixels. This is
  useful for providers with labels or icons, where it's necessary to draw a
  bit extra around the edges to ensure that text is not cut off. This example
  metatile has a buffer of 64 pixels, so the resulting metatile will be 1152
  pixels square: 4 rows x 256 pixels + 2 x 64 pixel buffer.

The preview can be accessed through a URL like /<layer name>/preview.html:

    {
      "lat": 33.9901,
      "lon": -116.1637,
      "zoom": 16,
      "ext": "jpg"
    }

- "lat" and "lon" are the starting latitude and longitude in degrees.
- "zoom" is the starting zoom level.
- "ext" is the filename extension, e.g. "png".
"""

import logging
from wsgiref.headers import Headers
from StringIO import StringIO
from urlparse import urljoin
from time import time

from Pixels import load_palette, apply_palette, apply_palette256

try:
    from PIL import Image
except ImportError:
    import Image

from ModestMaps.Core import Coordinate

_recent_tiles = dict(hash={}, list=[])

def _addRecentTile(layer, coord, format, body, age=300):
    """ Add the body of a tile to _recent_tiles with a timeout.
    """
    key = (layer, coord, format)
    due = time() + age
    
    _recent_tiles['hash'][key] = body, due
    _recent_tiles['list'].append((key, due))
    
    logging.debug('TileStache.Core._addRecentTile() added tile to recent tiles: %s', key)
    
    # now look at the oldest keys and remove them if needed
    for (key, due_by) in _recent_tiles['list']:
        # new enough?
        if time() < due_by:
            break
        
        logging.debug('TileStache.Core._addRecentTile() removed tile from recent tiles: %s', key)
        
        try:
            _recent_tiles['list'].remove((key, due_by))
        except ValueError:
            pass
        
        try:
            del _recent_tiles['hash'][key]
        except KeyError:
            pass

def _getRecentTile(layer, coord, format):
    """ Return the body of a recent tile, or None if it's not there.
    """
    key = (layer, coord, format)
    body, use_by = _recent_tiles['hash'].get(key, (None, 0))
    
    # non-existent?
    if body is None:
        return None
    
    # new enough?
    if time() < use_by:
        logging.debug('TileStache.Core._addRecentTile() found tile in recent tiles: %s', key)
        return body
    
    # too old
    try:
        del _recent_tiles['hash'][key]
    except KeyError:
        pass
    
    return None

class Metatile:
    """ Some basic characteristics of a metatile.
    
        Properties:
        - rows: number of tile rows this metatile covers vertically.
        - columns: number of tile columns this metatile covers horizontally.
        - buffer: pixel width of outer edge.
    """
    def __init__(self, buffer=0, rows=1, columns=1):
        assert rows >= 1
        assert columns >= 1
        assert buffer >= 0

        self.rows = rows
        self.columns = columns
        self.buffer = buffer

    def isForReal(self):
        """ Return True if this is really a metatile with a buffer or multiple tiles.
        
            A default 1x1 metatile with buffer=0 is not for real.
        """
        return self.buffer > 0 or self.rows > 1 or self.columns > 1

    def firstCoord(self, coord):
        """ Return a new coordinate for the upper-left corner of a metatile.
        
            This is useful as a predictable way to refer to an entire metatile
            by one of its sub-tiles, currently needed to do locking correctly.
        """
        return self.allCoords(coord)[0]

    def allCoords(self, coord):
        """ Return a list of coordinates for a complete metatile.
        
            Results are guaranteed to be ordered left-to-right, top-to-bottom.
        """
        rows, columns = int(self.rows), int(self.columns)
        
        # upper-left corner of coord's metatile
        row = rows * (int(coord.row) / rows)
        column = columns * (int(coord.column) / columns)
        
        coords = []
        
        for r in range(rows):
            for c in range(columns):
                coords.append(Coordinate(row + r, column + c, coord.zoom))

        return coords

class Layer:
    """ A Layer.
    
        Required attributes:

          provider:
            Render provider, see Providers module.

          config:
            Configuration instance, see Config module.

          projection:
            Geographic projection, see Geography module.

          metatile:
            Some information for drawing many tiles at once.

        Optional attributes:

          stale_lock_timeout:
            Number of seconds until a cache lock is forced, default 15.

          cache_lifespan:
            Number of seconds that cached tiles should be stored, default 15.

          write_cache:
            Allow skipping cache write altogether, default true.

          bounds:
            Instance of Config.Bounds for limiting rendered tiles.
          
          allowed_origin:
            Value for the Access-Control-Allow-Origin HTTP response header.

          max_cache_age:
            Number of seconds that tiles from this layer may be cached by downstream clients.

          redirects:
            Dictionary of per-extension HTTP redirects, treated as lowercase.

          preview_lat:
            Starting latitude for slippy map layer preview, default 37.80.

          preview_lon:
            Starting longitude for slippy map layer preview, default -122.26.

          preview_zoom:
            Starting zoom for slippy map layer preview, default 10.

          preview_ext:
            Tile name extension for slippy map layer preview, default "png".

          tile_height:
            Height of tile in pixels, as a single integer. Tiles are generally
            assumed to be square, and Layer.render() will respond with an error
            if the rendered image is not this height.
    """
    def __init__(self, config, projection, metatile, stale_lock_timeout=15, cache_lifespan=None, write_cache=True, allowed_origin=None, max_cache_age=None, redirects=None, preview_lat=37.80, preview_lon=-122.26, preview_zoom=10, preview_ext='png', bounds=None, tile_height=256):
        self.provider = None
        self.config = config
        self.projection = projection
        self.metatile = metatile
        
        self.stale_lock_timeout = stale_lock_timeout
        self.cache_lifespan = cache_lifespan
        self.write_cache = write_cache
        self.allowed_origin = allowed_origin
        self.max_cache_age = max_cache_age
        self.redirects = redirects or dict()
        
        self.preview_lat = preview_lat
        self.preview_lon = preview_lon
        self.preview_zoom = preview_zoom
        self.preview_ext = preview_ext
        
        self.bounds = bounds
        self.dim = tile_height
        
        self.bitmap_palette = None
        self.jpeg_options = {}
        self.png_options = {}

    def name(self):
        """ Figure out what I'm called, return a name if there is one.
        
            Layer names are stored in the Configuration object, so
            config.layers must be inspected to find a matching name.
        """
        for (name, layer) in self.config.layers.items():
            if layer is self:
                return name

        return None

    def getTileResponse(self, coord, extension, ignore_cached=False):
        """ Get status code, headers, and a tile binary for a given request layer tile.
        
            Arguments:
            - coord: one ModestMaps.Core.Coordinate corresponding to a single tile.
            - extension: filename extension to choose response type, e.g. "png" or "jpg".
            - ignore_cached: always re-render the tile, whether it's in the cache or not.
        
            This is the main entry point, after site configuration has been loaded
            and individual tiles need to be rendered.
        """
        start_time = time()
        
        mimetype, format = self.getTypeByExtension(extension)

        # default response values
        status_code = 200
        headers = Headers([('Content-Type', mimetype)])
        body = None

        cache = self.config.cache

        if not ignore_cached:
            # Start by checking for a tile in the cache.
            try:
                body = cache.read(self, coord, format)
            except TheTileLeftANote, e:
                headers = e.headers
                status_code = e.status_code
                body = e.content

                if e.emit_content_type:
                    headers.setdefault('Content-Type', mimetype)

            tile_from = 'cache'

        else:
            # Then look in the bag of recent tiles.
            body = _getRecentTile(self, coord, format)
            tile_from = 'recent tiles'
        
        # If no tile was found, dig deeper
        if body is None:
            try:
                lockCoord = None

                if self.write_cache:
                    # this is the coordinate that actually gets locked.
                    lockCoord = self.metatile.firstCoord(coord)
                    
                    # We may need to write a new tile, so acquire a lock.
                    cache.lock(self, lockCoord, format)
                
                if not ignore_cached:
                    # There's a chance that some other process has
                    # written the tile while the lock was being acquired.
                    body = cache.read(self, coord, format)
                    tile_from = 'cache after all'
        
                if body is None:
                    # No one else wrote the tile, do it here.
                    buff = StringIO()

                    try:
                        tile = self.render(coord, format)
                        save = True
                    except NoTileLeftBehind, e:
                        tile = e.tile
                        save = False

                    if not self.write_cache:
                        save = False
                    
                    if format.lower() == 'jpeg':
                        save_kwargs = self.jpeg_options
                    elif format.lower() == 'png':
                        save_kwargs = self.png_options
                    else:
                        save_kwargs = {}
                    
                    tile.save(buff, format, **save_kwargs)
                    body = buff.getvalue()
                    
                    if save:
                        cache.save(body, self, coord, format)

                    tile_from = 'layer.render()'

            except TheTileLeftANote, e:
                headers = e.headers
                status_code = e.status_code
                body = e.content
                
                if e.emit_content_type:
                    headers.setdefault('Content-Type', mimetype)

            finally:
                if lockCoord:
                    # Always clean up a lock when it's no longer being used.
                    cache.unlock(self, lockCoord, format)
        
        _addRecentTile(self, coord, format, body)
        logging.info('TileStache.Core.Layer.getTileResponse() %s/%d/%d/%d.%s via %s in %.3f', self.name(), coord.zoom, coord.column, coord.row, extension, tile_from, time() - start_time)
        
        return status_code, headers, body

    def doMetatile(self):
        """ Return True if we have a real metatile and the provider is OK with it.
        """
        return self.metatile.isForReal() and hasattr(self.provider, 'renderArea')
    
    def render(self, coord, format):
        """ Render a tile for a coordinate, return PIL Image-like object.
        
            Perform metatile slicing here as well, if required, writing the
            full set of rendered tiles to cache as we go.

            Note that metatiling and pass-through mode of a Provider
            are mutually exclusive options
        """
        if self.bounds and self.bounds.excludes(coord):
            raise NoTileLeftBehind(Image.new('RGB', (self.dim, self.dim), (0x99, 0x99, 0x99)))
        
        srs = self.projection.srs
        xmin, ymin, xmax, ymax = self.envelope(coord)
        width, height = self.dim, self.dim
        
        provider = self.provider
        metatile = self.metatile
        pass_through = provider.pass_through if hasattr(provider, 'pass_through') else False

        
        if self.doMetatile():

            if pass_through:
                raise KnownUnknown('Your provider is configured for metatiling and pass_through mode. That does not work')

            # adjust render size and coverage for metatile
            xmin, ymin, xmax, ymax = self.metaEnvelope(coord)
            width, height = self.metaSize(coord)

            subtiles = self.metaSubtiles(coord)
        
        if self.doMetatile() or hasattr(provider, 'renderArea'):
            # draw an area, defined in projected coordinates
            tile = provider.renderArea(width, height, srs, xmin, ymin, xmax, ymax, coord.zoom)
        
        elif hasattr(provider, 'renderTile'):
            # draw a single tile
            width, height = self.dim, self.dim
            tile = provider.renderTile(width, height, srs, coord)

        else:
            raise KnownUnknown('Your provider lacks renderTile and renderArea methods.')

        if not hasattr(tile, 'save'):
            raise KnownUnknown('Return value of provider.renderArea() must act like an image; e.g. have a "save" method.')

        if hasattr(tile, 'size') and tile.size[1] != height:
            raise KnownUnknown('Your provider returned the wrong image size: %s instead of %d pixels tall.' % (repr(tile.size), self.dim))
        
        if self.bitmap_palette:
            # this is where we apply the palette if there is one

            if pass_through:
                raise KnownUnknown('Cannot apply palette in pass_through mode')

            if format.lower() == 'png':
                t_index = self.png_options.get('transparency', None)
                tile = apply_palette(tile, self.bitmap_palette, t_index)
        
        if self.doMetatile():
            # tile will be set again later
            tile, surtile = None, tile
            
            for (other, x, y) in subtiles:
                buff = StringIO()
                bbox = (x, y, x + self.dim, y + self.dim)
                subtile = surtile.crop(bbox)
                if self.palette256:
                    # this is where we have PIL optimally palette our image
                    subtile = apply_palette256(subtile)
                
                subtile.save(buff, format)
                body = buff.getvalue()

                if self.write_cache:
                    self.config.cache.save(body, self, other, format)
                
                if other == coord:
                    # the one that actually gets returned
                    tile = subtile
                
                _addRecentTile(self, other, format, body)
        
        return tile
    
    def envelope(self, coord):
        """ Projected rendering envelope (xmin, ymin, xmax, ymax) for a Coordinate.
        """
        ul = self.projection.coordinateProj(coord)
        lr = self.projection.coordinateProj(coord.down().right())
        
        return min(ul.x, lr.x), min(ul.y, lr.y), max(ul.x, lr.x), max(ul.y, lr.y)
    
    def metaEnvelope(self, coord):
        """ Projected rendering envelope (xmin, ymin, xmax, ymax) for a metatile.
        """
        # size of buffer expressed as fraction of tile size
        buffer = float(self.metatile.buffer) / self.dim
        
        # full set of metatile coordinates
        coords = self.metatile.allCoords(coord)
        
        # upper-left and lower-right expressed as fractional coordinates
        ul = coords[0].left(buffer).up(buffer)
        lr = coords[-1].right(1 + buffer).down(1 + buffer)

        # upper-left and lower-right expressed as projected coordinates
        ul = self.projection.coordinateProj(ul)
        lr = self.projection.coordinateProj(lr)
        
        # new render area coverage in projected coordinates
        return min(ul.x, lr.x), min(ul.y, lr.y), max(ul.x, lr.x), max(ul.y, lr.y)
    
    def metaSize(self, coord):
        """ Pixel width and height of full rendered image for a metatile.
        """
        # size of buffer expressed as fraction of tile size
        buffer = float(self.metatile.buffer) / self.dim
        
        # new master image render size
        width = int(self.dim * (buffer * 2 + self.metatile.columns))
        height = int(self.dim * (buffer * 2 + self.metatile.rows))
        
        return width, height

    def metaSubtiles(self, coord):
        """ List of all coords in a metatile and their x, y offsets in a parent image.
        """
        subtiles = []

        coords = self.metatile.allCoords(coord)

        for other in coords:
            r = other.row - coords[0].row
            c = other.column - coords[0].column
            
            x = c * self.dim + self.metatile.buffer
            y = r * self.dim + self.metatile.buffer
            
            subtiles.append((other, x, y))

        return subtiles

    def getTypeByExtension(self, extension):
        """ Get mime-type and PIL format by file extension.
        """
        if hasattr(self.provider, 'getTypeByExtension'):
            return self.provider.getTypeByExtension(extension)
        
        elif extension.lower() == 'png':
            return 'image/png', 'PNG'
    
        elif extension.lower() == 'jpg':
            return 'image/jpeg', 'JPEG'
    
        else:
            raise KnownUnknown('Unknown extension in configuration: "%s"' % extension)

    def setSaveOptionsJPEG(self, quality=None, optimize=None, progressive=None):
        """ Optional arguments are added to self.jpeg_options for pickup when saving.
        
            More information about options:
                http://effbot.org/imagingbook/format-jpeg.htm
        """
        if quality is not None:
            self.jpeg_options['quality'] = int(quality)

        if optimize is not None:
            self.jpeg_options['optimize'] = bool(optimize)

        if progressive is not None:
            self.jpeg_options['progressive'] = bool(progressive)

    def setSaveOptionsPNG(self, optimize=None, palette=None, palette256=None):
        """ Optional arguments are added to self.png_options for pickup when saving.
        
            Palette argument is a URL relative to the configuration file,
            and it implies bits and optional transparency options.
        
            More information about options:
                http://effbot.org/imagingbook/format-png.htm
        """
        if optimize is not None:
            self.png_options['optimize'] = bool(optimize)
        
        if palette is not None:
            palette = urljoin(self.config.dirpath, palette)
            palette, bits, t_index = load_palette(palette)
            
            self.bitmap_palette, self.png_options['bits'] = palette, bits
            
            if t_index is not None:
                self.png_options['transparency'] = t_index

        if palette256 is not None:
            self.palette256 = bool(palette256)
        else:
            self.palette256 = None

class KnownUnknown(Exception):
    """ There are known unknowns. That is to say, there are things that we now know we don't know.
    
        This exception gets thrown in a couple places where common mistakes are made.
    """
    pass

class NoTileLeftBehind(Exception):
    """ Leave no tile in the cache.
    
        This exception can be thrown in a provider to signal to
        TileStache.getTile() that the result tile should be returned,
        but not saved in a cache. Useful in cases where a full tileset
        is being rendered for static hosting, and you don't want millions
        of identical ocean tiles.
        
        The one constructor argument is an instance of PIL.Image or
        some other object with a save() method, as would be returned
        by provider renderArea() or renderTile() methods.
    """
    def __init__(self, tile):
        self.tile = tile
        Exception.__init__(self, tile)

class TheTileLeftANote(Exception):
    """ A tile exists, but it shouldn't be returned to the client. Headers
        and/or a status code are provided in its stead.

        This exception can be thrown in a provider or a cache to signal to
        upstream servers where a tile can be found or to clients that a tile
        is empty (or solid).
    """
    def __init__(self, headers=None, status_code=200, content='', emit_content_type=True):
        self.headers = headers or Headers([])
        self.status_code = status_code
        self.content = content
        self.emit_content_type = bool(emit_content_type)

        Exception.__init__(self, self.headers, self.status_code,
                           self.content, self.emit_content_type)

def _preview(layer):
    """ Get an HTML response for a given named layer.
    """
    layername = layer.name()
    lat, lon = layer.preview_lat, layer.preview_lon
    zoom = layer.preview_zoom
    ext = layer.preview_ext
    
    return """<!DOCTYPE html>
<html>
<head>
    <title>TileStache Preview: %(layername)s</title>
    <script src="http://code.modestmaps.com/tilestache/modestmaps.min.js" type="text/javascript"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0;">
    <style type="text/css">
        html, body, #map {
            position: absolute;
            width: 100%%;
            height: 100%%;
            margin: 0;
            padding: 0;
        }

        #map img {
            width: 256px;
            height: 256px;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <script type="text/javascript" defer>
    <!--
        var template = '{Z}/{X}/{Y}.%(ext)s';
        var provider = new com.modestmaps.TemplatedMapProvider(template);
        var map = new MM.Map('map', provider, null, [
            new MM.TouchHandler(),
            new MM.DragHandler(),
            new MM.DoubleClickHandler()
        ]);
        map.setCenterZoom(new com.modestmaps.Location(%(lat).6f, %(lon).6f), %(zoom)d);
        // hashify it
        new MM.Hash(map);
    //-->
    </script>
</body>
</html>
""" % locals()

def _rummy():
    """ Draw Him.
    """
    return ['------------------------------------------------------------------------------------------------------------',
            'MB###BHHHBBMBBBB#####MBBHHHHBBBBHHAAA&GG&AAAHB###MHAAAAAAAAAHHAGh&&&AAAAH#@As;;shM@@@@@@@@@@@@@@@@@@@@@@@@@@',
            'MGBMHAGG&&AAA&&AAM##MHAGG&GG&&GGGG93X5SS2XX9hh3255X2issii5X3h9X22555XXXX9H@A.   rA@@@@@@@@@@@@@@@@@@@@@@@@@@',
            'BAM#BAAAAAAHHAAAHM##MBHAAAAAAAAAAAAG9X2X3hGXiii5X9hG3X9Xisi29B##BA33hGGhGB@@r   ;9@@@@@@@@@@@@@@@@@@@@@@@@@@',
            'BAM#MHAAAHHHAAAAHM###BHAAAAAAAAAAAAGhXX3h2iSX&A&&AAHAGGAGs;rrri2r;rSiXGA&B@@9.  ,2#@@@@@@@@@@@@@@@@@@@@@@@@@',
            'B&B#MHAAAAHHHAAAHM##MBHAAAAAAAAAAHAG93XSrs5Xh93h3XXX93529Xr;:,,:;;s25223AB@@@;   sB@@@@@@@@@@@@@@@@@@@@@@@@@',
            'B&B#BAAAAAHHHAAAHB##MBAAAAAAAAAAAHHAh5rs2AGGAhXisiissSsr;r;::,:riiiisrr,s#@@@9.  ,2#@@@@@@@@@@@@@@@@@@@@@@@@',
            'B&B#BAAAAAAHAAAAHM###BHA&AAAAAA&AAHA2S&#@MBHGX22s;;;;r;;:,:,,:;;rrr:,,:,.X@@@@r   :9@@@@@@@@@@@@@@@@@@@@@@@@',
            'BAM#MAAAAAAAAAAAAB##MBAA&AAAAAAA&AH929AHA9XhXirrir::;r;;:::,:,,:,;rsr;,.,;2@@@#,   :G@@@@@@@@@@@@@@@@@@@@@@B',
            'B&B#MAAAAAAHAAAAABM#MHAA&&&&&&&&&H&ss3AXisisisr;;r;::;::::,..,,,,::;rir;,;,A@@@G.   ;9@@@@@@@@@@@@@@@@@@@@@#',
            'B&B#MHAAAAHHAAAAABM#MHAAA&G&A&&&AG2rr2X; .:;;;;::::::::::,,,,,:,.,;::;;,;rr:@@@@X    :2#@@@@@@@@@@@@@@@@@@@@',
            'B&B##HAAAAHHAAAAABMMMHAA&&&&&AAA&h2:r2r..:,,,,,,,,,,,,:;:,,,,,,. ,;;;::, ;2rr@@@@2    :SB@@@@@@@@@@@@@@@@@@@',
            'BGB##HAAAAAAAAAAABMMMBAA&&&&&&&&AHr ir:;;;;:,,,,,,::::,,:,:,,,,...;:;:,:,:2Xr&@@@@3.   .rG@@@@@@@@@@@@@@@@@@',
            'B&B@#B&&AAAAAA&&AHMMMBAA&&&&&&&&AH,.i;;rrr;::,,:::::::,,::::::,,..;,:;.;;iXGSs#@@@@A,    :5#@@@@@@@@@@@@@@@@',
            'B&M@@B&&AAAHAA&&AHMMMBAA&&&&&&&&AA;,;rrrrr;;::::::::::::::::::::.:;.::,:5A9r,.9@@@@@M;    .;G@@@@@@@@@@@@@@@',
            'B&M@@B&&AAHAAA&&AHMMMBAA&G&GG&&&AM3;rrr;rr;;;;;;:::::;;,:,::,,,..,:;;:,;2r:.:;r@@##@@@i     .sH@@@@@@@@@@@@@',
            'BGM@@B&&AAAHAA&&AHMMMBHAGGGG&&&&AMHs;srrr;r:;;;;::::::,..,,,,,,...,;rrrsi, . :,#@####@@A;     ,iB@@@@@@@@@@@',
            'B&#@@B&&AAAAAA&&AHMMMBAA&GGGGG&&&BHr,rirr;;;::::::::::,,,,,::,,::,.,SS;r:.;r .,A#HHMBB#@@2,     :iA@@@@@@@@@',
            'B&#@@B&&AAAAAA&&AHBMBBAAGGGGGGG&&H#2:sis;;;::,,:::r;rsrr23HMAXr:::,:;...,,,5s,,#BGGAAAAB@@#i.     ,rG@@@@@@@',
            'B&#@@BG&AAAAAA&&AHHBMHAAGGhhGGGGGA#Hrs9s;;;;r;:;s5Xrrh@@@@@@@@&5rr;. .,,;. ;;.;@Bh39hhhAM#@@Ar.     ,rG#@@@@',
            'BA#@@BG&AAAAAA&&AHBMMBA&GGGGGGGGGAM#3r5SsiSSX@@@#@@i. 2h5ir;;:;r;:...,,:,.,;,,3@HG99XX23&H#MMBAS,     .;2H@@',
            'BA#@@B&&AAAAAA&&&AHBMBAA&GGGGGGGhABMhsrirrS9#@Mh5iG&::r;..:;:,,.,...,::,,,...,A@A&h9X255XGAA93B#MX;      .:X',
            'BH@@@B&&AAAAAA&G&ABM#BHAGGGGGGGGG&HBAXiir;s2r;;:rrsi.,,.   .....,,,,::,.,,:: :2@H&Gh9X2523AG253AM@@Ai,     ,',
            'MB@@@B&&AAAAAAGGAA###@#H&GGGGGGG&AHBAXXi;,. .:,,, .;:,.,;:;..,::::;;;:,,,:,srs5@B&hhh32229AG2S29GAB#@#A2;  .',
            'MB@@@BGGAAAAA&&GAHr  ,sH#AGGhhGGG&AH&X22s:..,. .  ;S:,. .,i9r;::,,:;:::,:::,,5A#BAhhhX22X9AG2i2X9hG&AB#@@B3r',
            'MB@@@B&&AAAAAA&AM#;..   ;AAGhhGGG&AHGX2XXis::,,,,,Xi,.:.ri;Xir;:,...,:::;::,.:S9#AGh9X2229A&2i52X39hhG&AM@@&',
            'MM@@@B&GAAAHBHBhsiGhhGi. 3MGGhGGG&HH&X52GXshh2r;;rXiB25sX2r;;:ii;,...:;:;:;:.., r#G33X2223AG2i52XX3339hGAA&&',
            '#M@@@B&GAM#A3hr  .;S5;:, ;MAGhGGG&ABAX55X9rS93s::i::i52X;,::,,,;5r:,,,::;;;:,.i  @@AXX222X&G2S52XXXX3399hhh&',
            '#M@@@BAB&S;  .:, .,,;,;;. rBGhhGG&ABAXSS29G5issrrS,,,,,:,...,;i;rr:,:,,::;::,,r  #@@B25523&G2iS2XXX3X33999h&',
            '#M@@@MH;  ,. .;i::::;rr;, ,M&GGGh&AHAXSS2X3hXirss5;r;:;;;2#@@H9Ai;::,,,,:;:;::   ,@@@#Xi23&G2iS2XXX3X33339h&',
            '#M#@@#i  .:;,.,::,::;&ii;.;#AGhGG&AHAXSS2XX3&hir;;s9GG@@@@@h;,,riirr;:,.:;;;.    i@##@@AS2hh5iS222XXXX3999hG',
            '#M@@@@:.;,,:r,,;r,,..h#sr: rHAGhG&AHAXSi52X39AAir::is;::,,. .::,sssrr;,,;r:     ,@@MM#@@#HBA2iiSS5522XX39hhG',
            '#M@@@@r.sr,:rr::r;,, ,As:,  :B&hh&ABAXSiSS5229HHS3r;rSSsiiSSr;:,,,:;;r;;;       @@#BMM#@@@@@@@@#MH&93XXXXX3G',
            '#M@@@@A,:r:,:i,,rr,,. ;;;,. ;BGhhGAHAX5529hAAAM#AH#2i25Ss;;;:.....,rSi2r       M@@MMMM##@#@@@@@@@@@@@@@@#MHA',
            '#M@@@@M::rr::SS,;r;::.:;;r:rHAh9h&ABM##@@@@@@@@ABAAA25i;::;;;:,,,,:r32:       H@@#MM######@@@@@@@@@@@@@@@@@#',
            '#M@@@@@5:;sr;;9r:i;,.,sr;;iMHhGABM#####@@@@@@@BHH&H@#AXr;;r;rsr;;ssS;        H@@##########@@@##@@@@@@@@@@@@#',
            '#M@@@@##r;;s;:3&;rsSrrisr:h#AHM#######BM#@@@#HHH9hM@@@X&92XX9&&G2i,     .,:,@@@##M########@@@####@@@@@@@@@##',
            '#M#@@@M@2,:;s;;2s:rAX5SirS#BB##@@@##MAAHB#@#BBH93GA@@@2 2@@@MAAHA  .,,:,,. G@@#M#################@@@@@@#####',
            '#M#@@#M@;,;:,,,;h52iX33sX@@#@@@@@@@#Ah&&H####HhA@@@@@@@;s@@@@H5@@  .      r@@##M###########@###@@@@@@#######',
            '#M#@@@#r.:;;;;rrrrrri5iA@@#@@@@@@@@#HHAH##MBA&#@@@@@@@@3i@@@@@3:,        ,@@#M############@@###@@@@@########',
            '#M@@@@r r::::;;;;;;rirA@#@@@@@@@@@@@#MGAMMHBAB@@@@@@@@@#2@@@@#i ..       #@##M#####@###@@@@###@@@@##########',
            '#M#@@@  2;;;;;;rr;rish@@#@#@@@@@@@@@@B&hGM#MH#@@@@@@@@@@3;,h@.   ..     :@@MM#######@@@@#####@@@@###########',
            '#M@@#A  ;r;riirrrr;:2S@###@@@@@@@@@@@#AH#@#HB#@@@@@@@@@@@@2A9           @@#BMMM############@#@@@####M#######',
            '#M@MM#      ,:,:;;,5ir@B#@@@@@@@@@@@@@@@@@#MMH#@@@@@@@@@@@@r Ms        B@#MMMMMM####@###@@#@@@@#####M######@',
            '##Mh@M  .    ...:;;,:@A#@@@@@@@@@@@#@@@@@@#MMHAB@@@@#G#@@#: i@@       r@@#MMM#######@@@@#@@@@@@#####M#####@@',
            '#H3#@3. ,.    ...  :@@&@@@@@@@@@@@@@#@@#@@@MMBHGA@H&;:@@i :B@@@B     .@@#MM####@@@##@@@#@@@@@#######M##M#@@@',
            'M&AM5i;.,.   ..,,rA@@MH@@@@@@@@@@@@@##@@@@@MMMBB#@h9hH#s;3######,   .A@#MMM#####@@@@@##@@@#@@#####M#####M39B']

########NEW FILE########
__FILENAME__ = Geography
""" The geography bits of TileStache.

A Projection defines the relationship between the rendered tiles and the
underlying geographic data. Generally, just one popular projection is used
for most web maps, "spherical mercator".

Built-in projections:
- spherical mercator
- WGS84

Example use projection in a layer definition:

    "layer-name": {
        "projection": "spherical mercator",
        ...
    }

You can define your own projection, with a module and object name as arguments:

    "layer-name": {
        ...
        "projection": "Module:Object"
    }

The object must include methods that convert between coordinates, points, and
locations. See the included mercator and WGS84 implementations for example.
You can also instantiate a projection class using this syntax:

    "layer-name": {
        ...
        "projection": "Module:Object()"
    }
"""

from ModestMaps.Core import Point, Coordinate
from ModestMaps.Geo import deriveTransformation, MercatorProjection, LinearProjection, Location
from math import log as _log, pi as _pi

import Core
import Config

class SphericalMercator(MercatorProjection):
    """ Spherical mercator projection for most commonly-used web map tile scheme.
    
        This projection is identified by the name "spherical mercator" in the
        TileStache config. The simplified projection used here is described in
        greater detail at: http://trac.openlayers.org/wiki/SphericalMercator
    """
    srs = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over'
    
    def __init__(self):
        pi = _pi

        # Transform from raw mercator projection to tile coordinates
        t = deriveTransformation(-pi, pi, 0, 0, pi, pi, 1, 0, -pi, -pi, 0, 1)

        MercatorProjection.__init__(self, 0, t)

    def coordinateProj(self, coord):
        """ Convert from Coordinate object to a Point object in EPSG:900913
        """
        # the zoom at which we're dealing with meters on the ground
        diameter = 2 * _pi * 6378137
        zoom = _log(diameter) / _log(2)
        coord = coord.zoomTo(zoom)
        
        # global offsets
        point = Point(coord.column, coord.row)
        point.x = point.x - diameter/2
        point.y = diameter/2 - point.y

        return point

    def projCoordinate(self, point):
        """ Convert from Point object in EPSG:900913 to a Coordinate object
        """
        # the zoom at which we're dealing with meters on the ground
        diameter = 2 * _pi * 6378137
        zoom = _log(diameter) / _log(2)

        # global offsets
        coord = Coordinate(point.y, point.x, zoom)
        coord.column = coord.column + diameter/2
        coord.row = diameter/2 - coord.row
        
        return coord

    def locationProj(self, location):
        """ Convert from Location object to a Point object in EPSG:900913
        """
        return self.coordinateProj(self.locationCoordinate(location))

    def projLocation(self, point):
        """ Convert from Point object in EPSG:900913 to a Location object
        """
        return self.coordinateLocation(self.projCoordinate(point))

class WGS84(LinearProjection):
    """ Unprojected projection for the other commonly-used web map tile scheme.
    
        This projection is identified by the name "WGS84" in the TileStache config.
    """
    srs = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
    
    def __init__(self):
        p = _pi

        # Transform from geography in radians to tile coordinates
        t = deriveTransformation(-p, p/2, 0, 0, p, p/2, 2, 0, -p, -p/2, 0, 1)

        LinearProjection.__init__(self, 0, t)

    def coordinateProj(self, coord):
        """ Convert from Coordinate object to a Point object in EPSG:4326
        """
        return self.locationProj(self.coordinateLocation(coord))

    def projCoordinate(self, point):
        """ Convert from Point object in EPSG:4326 to a Coordinate object
        """
        return self.locationCoordinate(self.projLocation(point))

    def locationProj(self, location):
        """ Convert from Location object to a Point object in EPSG:4326
        """
        return Point(location.lon, location.lat)

    def projLocation(self, point):
        """ Convert from Point object in EPSG:4326 to a Location object
        """
        return Location(point.y, point.x)

def getProjectionByName(name):
    """ Retrieve a projection object by name.
    
        Raise an exception if the name doesn't work out.
    """
    if name.lower() == 'spherical mercator':
        return SphericalMercator()
        
    elif name.lower() == 'wgs84':
        return WGS84()
        
    else:
        try:
            return Config.loadClassPath(name)
        except Exception, e:
            raise Core.KnownUnknown('Failed projection in configuration: "%s" - %s' % (name, e))

########NEW FILE########
__FILENAME__ = AreaServer
""" AreaServer supplies a tiny image server for use with TileStache providers
    that implement renderArea() (http://tilestache.org/doc/#custom-providers).
    The built-in Mapnik provider (http://tilestache.org/doc/#mapnik-provider)
    is one example.
    
    There are no tiles here, just a quick & dirty way of getting variously-sized
    images out of a codebase that's ordinarily oriented toward tile generation.

    Example usage, with gunicorn (http://gunicorn.org):
    
      gunicorn --bind localhost:8888 "TileStache.Goodies.AreaServer:WSGIServer('tilestache.cfg')"
    
    AreaServer URLs are compatible with the built-in URL Template provider
    (http://tilestache.org/doc/#url-template-provider) and implement a generic
    kind of WMS (http://en.wikipedia.org/wiki/Web_Map_Service).
    
    All six URL parameters shown in this example are required; any other
    URL parameter is ignored:

      http://localhost:8888/layer-name?width=600&height=600&xmin=-100&ymin=-100&xmax=100&ymax=100
"""

from urlparse import parse_qsl
from datetime import timedelta
from datetime import datetime
from StringIO import StringIO

from TileStache import WSGITileServer
from TileStache.Core import KnownUnknown

class WSGIServer (WSGITileServer):
    """ WSGI Application that can handle WMS-style requests for static images.
        
        Inherits the constructor from TileStache WSGI, which just loads
        a TileStache configuration file into self.config.
        
        WSGITileServer autoreload argument is ignored, though. For now.
    """
    def __call__(self, environ, start_response):
        """ Handle a request, using PATH_INFO and QUERY_STRING from environ.
        
            There are six required query string parameters: width, height,
            xmin, ymin, xmax and ymax. Layer name must be supplied in PATH_INFO.
        """
        try:
            for var in 'QUERY_STRING PATH_INFO'.split():
                if var not in environ:
                    raise KnownUnknown('Missing "%s" environment variable' % var)
            
            query = dict(parse_qsl(environ['QUERY_STRING']))
            
            for param in 'width height xmin ymin xmax ymax'.split():
                if param not in query:
                    raise KnownUnknown('Missing "%s" parameter' % param)
            
            layer = environ['PATH_INFO'].strip('/')
            layer = self.config.layers[layer]
            provider = layer.provider
            
            if not hasattr(provider, 'renderArea'):
                raise KnownUnknown('Layer "%s" provider %s has no renderArea() method' % (layer.name(), provider.__class__))
            
            width, height = [int(query[p]) for p in 'width height'.split()]
            xmin, ymin, xmax, ymax = [float(query[p]) for p in 'xmin ymin xmax ymax'.split()]
            
            #
            # Don't supply srs or zoom parameters, which may cause problems for
            # some providers. TODO: add optional support for these two parameters.
            #
            
            output = StringIO()
            image = provider.renderArea(width, height, None, xmin, ymin, xmax, ymax, None)
            image.save(output, format='PNG')
            
            headers = [('Content-Type', 'image/png')]
            
            if layer.allowed_origin:
                headers.append(('Access-Control-Allow-Origin', layer.allowed_origin))
            
            if layer.max_cache_age is not None:
                expires = datetime.utcnow() + timedelta(seconds=layer.max_cache_age)
                headers.append(('Expires', expires.strftime('%a %d %b %Y %H:%M:%S GMT')))
                headers.append(('Cache-Control', 'public, max-age=%d' % layer.max_cache_age))

            start_response('200 OK', headers)
            return output.getvalue()
        
        except KnownUnknown, e:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return str(e)

########NEW FILE########
__FILENAME__ = GoogleCloud
#!/usr/bin/env python
""" Caches tiles to Google Cloud Storage.

Requires boto (2.0+):
  http://pypi.python.org/pypi/boto

Example configuration:

  "cache": {
    "name": "TileStache.Goodies.Caches.GoogleCloud:Cache",
    "kwargs": {
      "bucket": "<bucket name>",
      "access": "<access key>",
      "secret": "<secret key>"
    }
  }

cache parameters:

  bucket
    Required bucket name for GS. If it doesn't exist, it will be created.

  access
    Required access key ID for your GS account.

  secret
    Required secret access key for your GS account.

"""
from time import time
from mimetypes import guess_type


# URI scheme for Google Cloud Storage.
GOOGLE_STORAGE = 'gs'
# URI scheme for accessing local files.
LOCAL_FILE = 'file'

try:
    import boto
except ImportError:
    # at least we can build the documentation
    pass

def tile_key(layer, coord, format):
    """ Return a tile key string.
    """
    name = layer.name()
    tile = '%(zoom)d/%(column)d/%(row)d' % coord.__dict__
    ext = format.lower()

    return str('%(name)s/%(tile)s.%(ext)s' % locals())

class Cache:
    """
    """
    def __init__(self, bucket, access, secret):
        config = boto.config
        config.add_section('Credentials')
        config.set('Credentials', 'gs_access_key_id', access)
        config.set('Credentials', 'gs_secret_access_key', secret)

        uri = boto.storage_uri('', GOOGLE_STORAGE)
        for b in uri.get_all_buckets():
          if b.name == bucket:
            self.bucket = b
        #TODO: create bucket if not found

    def lock(self, layer, coord, format):
        """ Acquire a cache lock for this tile.
        
            Returns nothing, but blocks until the lock has been acquired.
        """
        key_name = tile_key(layer, coord, format)
        due = time() + layer.stale_lock_timeout
        
        while time() < due:
            if not self.bucket.get_key(key_name+'-lock'):
                break
            
            _sleep(.2)
        
        key = self.bucket.new_key(key_name+'-lock')
        key.set_contents_from_string('locked.', {'Content-Type': 'text/plain'})
        
    def unlock(self, layer, coord, format):
        """ Release a cache lock for this tile.
        """
        key_name = tile_key(layer, coord, format)
        try:
          self.bucket.delete_key(key_name+'-lock')
        except:
          pass
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile.
        """
        key_name = tile_key(layer, coord, format)
        self.bucket.delete_key(key_name)
        
    def read(self, layer, coord, format):
        """ Read a cached tile.
        """
        key_name = tile_key(layer, coord, format)
        key = self.bucket.get_key(key_name)
        
        if key is None:
            return None
        
        if layer.cache_lifespan:
            t = timegm(strptime(key.last_modified, '%a, %d %b %Y %H:%M:%S %Z'))

            if (time() - t) > layer.cache_lifespan:
                return None
        
        return key.get_contents_as_string()
        
    def save(self, body, layer, coord, format):
        """ Save a cached tile.
        """
        key_name = tile_key(layer, coord, format)
        key = self.bucket.new_key(key_name)
        
        content_type, encoding = guess_type('example.'+format)
        headers = content_type and {'Content-Type': content_type} or {}
        
        key.set_contents_from_string(body, headers, policy='public-read')

########NEW FILE########
__FILENAME__ = LimitedDisk
""" Cache that stores a limited amount of data.

This is an example cache that uses a SQLite database to track sizes and last-read
times for cached tiles, and removes least-recently-used tiles whenever the total
size of the cache exceeds a set limit.

Example TileStache cache configuration, with a 16MB limit:

"cache":
{
    "class": "TileStache.Goodies.Caches.LimitedDisk.Cache",
    "kwargs": {
        "path": "/tmp/limited-cache",
        "limit": 16777216
    }
}
"""

import os
import sys
import time

from math import ceil as _ceil
from tempfile import mkstemp
from os.path import isdir, exists, dirname, basename, join as pathjoin
from sqlite3 import connect, OperationalError, IntegrityError

_create_tables = """
    CREATE TABLE IF NOT EXISTS locks (
        row     INTEGER,
        column  INTEGER,
        zoom    INTEGER,
        format  TEXT,
        
        PRIMARY KEY (row, column, zoom, format)
    )
    """, """
    CREATE TABLE IF NOT EXISTS tiles (
        path    TEXT PRIMARY KEY,
        used    INTEGER,
        size    INTEGER
    )
    """, """
    CREATE INDEX IF NOT EXISTS tiles_used ON tiles (used)
    """

class Cache:

    def __init__(self, path, limit, umask=0022):
        self.cachepath = path
        self.dbpath = pathjoin(self.cachepath, 'stache.db')
        self.umask = umask
        self.limit = limit

        db = connect(self.dbpath).cursor()
        
        for create_table in _create_tables:
            db.execute(create_table)

        db.connection.close()

    def _filepath(self, layer, coord, format):
        """
        """
        l = layer.name()
        z = '%d' % coord.zoom
        e = format.lower()
        
        x = '%06d' % coord.column
        y = '%06d' % coord.row

        x1, x2 = x[:3], x[3:]
        y1, y2 = y[:3], y[3:]
        
        filepath = os.sep.join( (l, z, x1, x2, y1, y2 + '.' + e) )

        return filepath

    def lock(self, layer, coord, format):
        """ Acquire a cache lock for this tile.
        
            Returns nothing, but (TODO) blocks until the lock has been acquired.
            Lock is implemented as a row in the "locks" table.
        """
        sys.stderr.write('lock %d/%d/%d, %s' % (coord.zoom, coord.column, coord.row, format))

        due = time.time() + layer.stale_lock_timeout
        
        while True:
            if time.time() > due:
                # someone left the door locked.
                sys.stderr.write('...force %d/%d/%d, %s' % (coord.zoom, coord.column, coord.row, format))
                self.unlock(layer, coord, format)
            
            # try to acquire a lock, repeating if necessary.
            db = connect(self.dbpath, isolation_level='EXCLUSIVE').cursor()

            try:
                db.execute("""INSERT INTO locks
                              (row, column, zoom, format)
                              VALUES (?, ?, ?, ?)""",
                           (coord.row, coord.column, coord.zoom, format))
            except IntegrityError:
                db.connection.close()
                time.sleep(.2)
                continue
            else:
                db.connection.commit()
                db.connection.close()
                break

    def unlock(self, layer, coord, format):
        """ Release a cache lock for this tile.

            Lock is implemented as a row in the "locks" table.
        """
        sys.stderr.write('unlock %d/%d/%d, %s' % (coord.zoom, coord.column, coord.row, format))

        db = connect(self.dbpath, isolation_level='EXCLUSIVE').cursor()
        db.execute("""DELETE FROM locks
                      WHERE row=? AND column=? AND zoom=? AND format=?""",
                   (coord.row, coord.column, coord.zoom, format))
        db.connection.commit()
        db.connection.close()
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile.
        """
        # TODO: write me
        raise NotImplementedError('LimitedDisk Cache does not yet implement the .remove() method.')
        
    def read(self, layer, coord, format):
        """ Read a cached tile.
        
            If found, update the used column in the tiles table with current time.
        """
        sys.stderr.write('read %d/%d/%d, %s' % (coord.zoom, coord.column, coord.row, format))

        path = self._filepath(layer, coord, format)
        fullpath = pathjoin(self.cachepath, path)
        
        if exists(fullpath):
            body = open(fullpath, 'r').read()

            sys.stderr.write('...hit %s, set used=%d' % (path, time.time()))

            db = connect(self.dbpath).cursor()
            db.execute("""UPDATE tiles
                          SET used=?
                          WHERE path=?""",
                       (int(time.time()), path))
            db.connection.commit()
            db.connection.close()
        
        else:
            sys.stderr.write('...miss')
            body = None

        return body

    def _write(self, body, path, format):
        """ Actually write the file to the cache directory, return its size.
        
            If filesystem block size is known, try to return actual disk space used.
        """
        fullpath = pathjoin(self.cachepath, path)

        try:
            umask_old = os.umask(self.umask)
            os.makedirs(dirname(fullpath), 0777&~self.umask)
        except OSError, e:
            if e.errno != 17:
                raise
        finally:
            os.umask(umask_old)

        fh, tmp_path = mkstemp(dir=self.cachepath, suffix='.' + format.lower())
        os.write(fh, body)
        os.close(fh)
        
        try:
            os.rename(tmp_path, fullpath)
        except OSError:
            os.unlink(fullpath)
            os.rename(tmp_path, fullpath)

        os.chmod(fullpath, 0666&~self.umask)
        
        stat = os.stat(fullpath)
        size = stat.st_size
        
        if hasattr(stat, 'st_blksize'):
            blocks = _ceil(size / float(stat.st_blksize))
            size = int(blocks * stat.st_blksize)

        return size

    def _remove(self, path):
        """
        """
        fullpath = pathjoin(self.cachepath, path)

        os.unlink(fullpath)
    
    def save(self, body, layer, coord, format):
        """
        """
        sys.stderr.write('save %d/%d/%d, %s' % (coord.zoom, coord.column, coord.row, format))
        
        path = self._filepath(layer, coord, format)
        size = self._write(body, path, format)

        db = connect(self.dbpath).cursor()
        
        try:
            db.execute("""INSERT INTO tiles
                          (size, used, path)
                          VALUES (?, ?, ?)""",
                       (size, int(time.time()), path))
        except IntegrityError:
            db.execute("""UPDATE tiles
                          SET size=?, used=?
                          WHERE path=?""",
                       (size, int(time.time()), path))
        
        row = db.execute('SELECT SUM(size) FROM tiles').fetchone()
        
        if row and (row[0] > self.limit):
            over = row[0] - self.limit
            
            while over > 0:
                row = db.execute('SELECT path, size FROM tiles ORDER BY used ASC LIMIT 1').fetchone()
                
                if row is None:
                    break

                path, size = row
                db.execute('DELETE FROM tiles WHERE path=?', (path, ))
                self._remove(path)
                over -= size
                sys.stderr.write('delete ' + path)
        
        db.connection.commit()
        db.connection.close()

########NEW FILE########
__FILENAME__ = ExternalConfigServer
""" ExternalConfigServer is a replacement for WSGITileServer that uses external
    configuration fetched via HTTP to service all config requests.
    
    Example usage, with gunicorn (http://gunicorn.org):
      
      gunicorn --bind localhost:8888 "TileStache.Goodies.ExternalConfigServer:WSGIServer(url)"
"""

from urllib import urlopen
import logging

try:
	from json import load as json_load
except ImportError:
	from simplejson import load as json_load

import TileStache

class DynamicLayers:
	
	def __init__(self, config, url_root, cache_responses, dirpath):
		self.config = config
		self.url_root = url_root
		self.dirpath = dirpath
		self.cache_responses = cache_responses;
		self.seen_layers = {}
		self.lookup_failures = set()
	
	def keys(self):
		return self.seen_layers.keys()
	
	def items(self):
		return self.seen_layers.items()

	def parse_layer(self, layer_json):
		layer_dict = json_load(layer_json)
		return TileStache.Config._parseConfigfileLayer(layer_dict, self.config, self.dirpath)
	
	def __contains__(self, key):
		# If caching is enabled and we've seen a request for this layer before, return True unless
		# the prior lookup failed to find this layer.
		if self.cache_responses:
			if key in self.seen_layers:
				return True
			elif key in self.lookup_failures:
				return False
		
		res = urlopen(self.url_root + "/layer/" + key)
		
		if self.cache_responses:
			if res.getcode() != 200:
				# Cache a failed lookup
				self.lookup_failures.add(key)
			else :
				# If lookup succeeded and we are caching, parse the layer now so that a subsequent
				# call to __getitem__ doesn't require a call to the config server.  If we aren't
				# caching, we skip this step to avoid an unnecessary json parse.
				try:
					self.seen_layers[key] = self.parse_layer(res)
				except ValueError:
					# The JSON received by the config server was invalid.  Treat this layer as a
					# failure.  We don't want to raise ValueError from here because other parts
					# of TileStache are just expecting a boolean response from __contains__
					logging.error("Invalid JSON response seen for %s", key)
					self.lookup_failures.add(key)
					return False

		if res.getcode() != 200:
			logging.info("Config response code %s for %s", res.getcode(), key)		
		return res.getcode() == 200
	
	def __getitem__(self, key):
		if self.cache_responses:
			if key in self.seen_layers:
				return self.seen_layers[key]
			elif key in self.lookup_failures:
				# If we are caching, raise KnownUnknown if we have previously failed to find this layer
				raise TileStache.KnownUnknown("Layer %s previously not found", key)
		
		logging.debug("Requesting layer %s", self.url_root + "/layer/" + key)
		res = urlopen(self.url_root + "/layer/" + key)
		if (res.getcode() != 200) :
			logging.info("Config response code %s for %s", res.getcode(), key)
			if (self.cache_responses) :
				self.lookup_failures.add(key)
			raise TileStache.KnownUnknown("Layer %s not found", key)
		
		try :
			layer = self.parse_layer(res)
			self.seen_layers[key] = layer
			return layer
		except ValueError:
			logging.error("Invalid JSON response seen for %s", key)
			if (self.cache_responses) :
				# If caching responses, cache this failure
				self.lookup_failures.add(key)
			# KnownUnknown seems like the appropriate thing to raise here since this is akin
			# to a missing configuration.
			raise TileStache.KnownUnknown("Failed to parse JSON configuration for %s", key)

class ExternalConfiguration:
	
	def __init__(self, url_root, cache_dict, cache_responses, dirpath):
		self.cache = TileStache.Config._parseConfigfileCache(cache_dict, dirpath)
		self.dirpath = dirpath
		self.layers = DynamicLayers(self, url_root, cache_responses, dirpath)

class WSGIServer (TileStache.WSGITileServer):
	
	"""
		Wrap WSGI application, passing it a custom configuration.
		
		The WSGI application is an instance of TileStache:WSGITileServer.
		
		This method is initiated with a url_root that contains the scheme, host, port
		and path that must prefix the API calls on our local server.  Any valid http
		or https urls should work.
		
		The cache_responses parameter tells TileStache to cache all responses from
		the configuration server.
	"""
	
	def __init__(self, url_root, cache_responses=True, debug_level="DEBUG"):
		logging.basicConfig(level=debug_level)
		
		# Call API server at url to grab cache_dict
		cache_dict = json_load(urlopen(url_root + "/cache"))
		
		dirpath = '/tmp/stache'
		
		config = ExternalConfiguration(url_root, cache_dict, cache_responses, dirpath)
		
		TileStache.WSGITileServer.__init__(self, config, False)
	
	def __call__(self, environ, start_response):
		response = TileStache.WSGITileServer.__call__(self, environ, start_response)
		return response

########NEW FILE########
__FILENAME__ = Proj4Projection
""" Projection that supports any projection that can be expressed in Proj.4 format.

    The projection is configured by a projection definition in the Proj.4
    format, the resolution of the zoom levels that the projection should
    support, the tile size, and a transformation that defines how to tile
    coordinates are calculated.
    
    An example, instantiating a projection for EPSG:2400 (RT90 2.5 gon W):
    
      Proj4Projection('+proj=tmerc +lat_0=0 +lon_0=15.80827777777778 +k=1'
                      +' +x_0=1500000 +y_0=0 +ellps=bessel +units=m +no_defs',
                      [8192, 4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1],
                      transformation=Transformation(1, 0, 0, 0, -1, 0))
                        
    This example defines 14 zoom levels, where each level doubles the
    resolution, where the most zoomed out level uses 8192 projected units
    (meters, in this case) per pixel. The tiles are adressed using XYZ scheme,
    with the origin at (0, 0): the x component of the transformation is 1, the
    y component is -1 (tile rows increase from north to south). Tile size
    defaults to 256x256 pixels.
    
    The same projection, included in a TileStache configuration file:
    
      "example":
      {
        "provider": {"name": "mapnik", "mapfile": "examples/style.xml"},
        "projection": "TileStache.Goodies.Proj4Projection:Proj4Projection('+proj=tmerc +lat_0=0 +lon_0=15.80827777777778 +k=1 +x_0=1500000 +y_0=0 +ellps=bessel +units=m +no_defs', [8192, 4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1], transformation=Transformation(1, 0, 0, 0, -1, 0))"
      }
    
    "Module:Class()" syntax described in http://tilestache.org/doc/#projections.
    
    For more details about tiling, projections, zoom levels and transformations,
    see http://blog.kartena.se/local-projections-in-a-world-of-spherical-mercator/
"""

import TileStache
from pyproj import Proj
from ModestMaps.Core import Point, Coordinate
from ModestMaps.Geo import Location, LinearProjection, Transformation

_grid_threshold = 1e-3

class Proj4Projection(LinearProjection):
    """ Projection that supports any projection that can be expressed in Proj.4 format.
    
        Required attributes:
          
          srs:
            The Proj.4 definition of the projection to use, as a string
          
          resolutions:
            An array of the zoom levels' resolutions, expressed as the number
            of projected units per pixel on each zoom level. The array is ordered
            with outermost zoom level first (0 is most zoomed out).
            
        Optional attributes:
          
          tile_size:
            The size of a tile in pixels, default is 256.
            
          transformation:
            Transformation to apply to the projected coordinates to convert them
            to tile coordinates. Defaults to Transformation(1, 0, 0, 1, 0), which
            gives row = projected_y * scale, column = projected_x * scale
    """
    def __init__(self, srs, resolutions, tile_size=256, transformation=Transformation(1, 0, 0, 0, 1, 0)):
        """
        Creates a new instance with the projection specified in srs, which is in Proj4
        format.
        """
        
        self.resolutions = resolutions
        self.tile_size = tile_size
        self.proj = Proj(srs)
        self.srs = srs
        self.tile_dimensions = \
            [self.tile_size * r for r in self.resolutions]

        try:
             self.base_zoom = self.resolutions.index(1.0)
        except ValueError:
            raise TileStache.Core.KnownUnknown('No zoom level with resolution 1.0')

        LinearProjection.__init__(self, self.base_zoom, transformation)
        
    def project(self, point, scale):
        p = LinearProjection.project(self, point)
        p.x = p.x * scale
        p.y = p.y * scale
        return p

    def unproject(self, point, scale):
        p = LinearProjection.unproject(self, point)
        p.x = p.x / scale
        p.y = p.y / scale
        return p

    def locationCoordinate(self, location):
        point = self.locationProj(location)
        point = self.project(point, 1.0 / self.tile_dimensions[self.zoom])
        return Coordinate(point.y, point.x, self.zoom)
        
    def coordinateLocation(self, coord):
        ''' TODO: write me.
        '''
        raise NotImplementedError('Missing Proj4Projection.coordinateLocation(), see https://github.com/migurski/TileStache/pull/127')
        
    def coordinateProj(self, coord):
        """Convert from Coordinate object to a Point object in the defined projection"""
        if coord.zoom >= len(self.tile_dimensions):
            raise TileStache.Core.KnownUnknown('Requested zoom level %d outside defined resolutions.' % coord.zoom)
        p = self.unproject(Point(coord.column, coord.row), 1.0 / self.tile_dimensions[coord.zoom])
        return p

    def locationProj(self, location):
        """Convert from Location object to a Point object in the defined projection"""
        x,y = self.proj(location.lon, location.lat)
        return Point(x, y)

    def projCoordinate(self, point, zoom=None):
        """Convert from Point object in the defined projection to a Coordinate object"""
        if zoom == None:
            zoom = self.base_zoom
        if zoom >= len(self.tile_dimensions):
            raise TileStache.Core.KnownUnknown('Requested zoom level %d outside defined resolutions.' % zoom)

        td = self.tile_dimensions[zoom]
        p = self.project(point, 1.0 / td)
        
        row = round(p.y)
        col = round(p.x)

        if abs(p.y - row) > _grid_threshold \
                or abs(p.x - col) > _grid_threshold:
            raise TileStache.Core.KnownUnknown(('Point(%f, %f) does not align with grid '
                                               + 'for zoom level %d '
                                               + '(resolution=%f, difference: %f, %f).') %
                                               (point.x, point.y, zoom, self.resolutions[zoom],
                                                p.y - row, p.x - col))

        c = Coordinate(int(row), int(col), zoom)
        return c

    def projLocation(self, point):
        """Convert from Point object in the defined projection to a Location object"""
        x,y = self.proj(point.x, point.y, inverse=True)
        return Location(y, x)

    def findZoom(self, resolution):
        try:
            return self.resolutions.index(resolution)
        except ValueError:
            raise TileStache.Core.KnownUnknown("No zoom level with resolution %f defined." % resolution)

########NEW FILE########
__FILENAME__ = Cascadenik
''' Cascadenik Provider.

Simple wrapper for TileStache Mapnik provider that parses Cascadenik MML files
directly, skipping the typical compilation to XML step.

More information on Cascadenik:
- https://github.com/mapnik/Cascadenik/wiki/Cascadenik

Requires Cascadenik 2.x+.
'''
from tempfile import gettempdir

try:
    from ...Mapnik import ImageProvider, mapnik
    from cascadenik import load_map
except ImportError:
    # can still build documentation
    pass

class Provider (ImageProvider):
    """ Renders map images from Cascadenik MML files.
    
        Arguments:
        
        - mapfile (required)
            Local file path to Mapnik XML file.
    
        - fonts (optional)
            Local directory path to *.ttf font files.
    
        - workdir (optional)
            Directory path for working files, tempfile.gettempdir() by default.
    """
    def __init__(self, layer, mapfile, fonts=None, workdir=None):
        """ Initialize Cascadenik provider with layer and mapfile.
        """
        self.workdir = workdir or gettempdir()
        self.mapnik = None

        ImageProvider.__init__(self, layer, mapfile, fonts)

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        """ Mostly hand off functionality to Mapnik.ImageProvider.renderArea()
        """
        if self.mapnik is None:
            self.mapnik = mapnik.Map(0, 0)
            load_map(self.mapnik, str(self.mapfile), self.workdir, cache_dir=self.workdir)
        
        return ImageProvider.renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom)

########NEW FILE########
__FILENAME__ = Composite
""" Layered, composite rendering for TileStache.

NOTE: This code is currently in heavy progress. I'm finishing the addition
of the new JSON style of layer configuration, while the original XML form
is *deprecated* and will be removed in the future TileStache 2.0.

The Composite Provider provides a Photoshop-like rendering pipeline, making it
possible to use the output of other configured tile layers as layers or masks
to create a combined output. Composite is modeled on Lars Ahlzen's TopOSM.

The "stack" configuration parameter describes a layer or stack of layers that
can be combined to create output. A simple stack that merely outputs a single
color orange tile looks like this:

    {"color" "#ff9900"}

Other layers in the current TileStache configuration can be reference by name,
as in this example stack that simply echoes another layer:

    {"src": "layer-name"}

Layers can be limited to appear at certain zoom levels, given either as a range
or as a single number:

    {"src": "layer-name", "zoom": "12"}
    {"src": "layer-name", "zoom": "12-18"}

Layers can also be used as masks, as in this example that uses one layer
to mask another layer:

    {"mask": "layer-name", "src": "other-layer"}

Many combinations of "src", "mask", and "color" can be used together, but it's
an error to provide all three.

Layers can be combined through the use of opacity and blend modes. Opacity is
specified as a value from 0.0-1.0, and blend mode is specified as a string.
This example layer is blended using the "hard light" mode at 50% opacity:

    {"src": "hillshading", "mode": "hard light", "opacity": 0.5}

Currently-supported blend modes include "screen", "multiply", "linear light",
and "hard light".

Layers can also be affected by adjustments. Adjustments are specified as an
array of names and parameters. This example layer has been slightly darkened
using the "curves" adjustment, moving the input value of 181 (light gray)
to 50% gray while leaving black and white alone:

    {"src": "hillshading", "adjustments": [ ["curves", [0, 181, 255]] ]}

Available adjustments:
  "threshold" - apply_threshold_adjustment()
  "curves" - apply_curves_adjustment()
  "curves2" - apply_curves2_adjustment()

Finally, the stacking feature allows layers to combined in more complex ways.
This example stack combines a background color and foreground layer:

    [
      {"color": "#ff9900"},
      {"src": "layer-name"}
    ]

Stacks can be nested as well, such as this combination of two background layers
and two foreground layers:

    [
      [
        {"color"" "#0066ff"},
        {"src": "continents"}
      ],
      [
        {"src": "streets"},
        {"src": "labels"}
      ]
    ]

A complete example configuration might look like this:

    {
      "cache":
      {
        "name": "Test"
      },
      "layers": 
      {
        "base":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-base.xml"}
        },
        "halos":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-halos.xml"},
          "metatile": {"buffer": 128}
        },
        "outlines":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-outlines.xml"},
          "metatile": {"buffer": 16}
        },
        "streets":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-streets.xml"},
          "metatile": {"buffer": 128}
        },
        "composite":
        {
          "provider":
          {
            "class": "TileStache.Goodies.Providers.Composite:Provider",
            "kwargs":
            {
              "stack":
              [
                {"src": "base"},
                [
                  {"src": "outlines", "mask": "halos"},
                  {"src": "streets"}
                ]
              ]
            }
          }
        }
      }
    }

It's also possible to provide an equivalent "stackfile" argument that refers to
an XML file, but this feature is *deprecated* and will be removed in the future
release of TileStache 2.0.

Corresponding example stackfile XML:

  <?xml version="1.0"?>
  <stack>
    <layer src="base" />
  
    <stack>
      <layer src="outlines">
        <mask src="halos" />
      </layer>
      <layer src="streets" />
    </stack>
  </stack>

Note that each layer in this file refers to a TileStache layer by name.
This complete example can be found in the included examples directory.
"""

import sys
import re

from urllib import urlopen
from urlparse import urljoin
from os.path import join as pathjoin
from xml.dom.minidom import parse as parseXML
from StringIO import StringIO

try:
    from json import loads as jsonload
except ImportError:
    from simplejson import loads as jsonload

import TileStache

try:
    import numpy
    import sympy
except ImportError:
    # At least we can build the docs
    pass

try:
    from PIL import Image
except ImportError:
    # On some systems, PIL.Image is known as Image.
    import Image

from TileStache.Core import KnownUnknown

class Provider:
    """ Provides a Photoshop-like rendering pipeline, making it possible to use
        the output of other configured tile layers as layers or masks to create
        a combined output.
    """
    def __init__(self, layer, stack=None, stackfile=None):
        """ Make a new Composite.Provider.
            
            Arguments:
            
              layer:
                The current TileStache.Core.Layer
                
              stack:
                A list or dictionary with configuration for the image stack, parsed
                by build_stack(). Also acceptable is a URL to a JSON file.
              
              stackfile:
                *Deprecated* filename for an XML representation of the image stack.
        """
        self.layer = layer
        
        if type(stack) in (str, unicode):
            stack = jsonload(urlopen(urljoin(layer.config.dirpath, stack)).read())
        
        if type(stack) in (list, dict):
            self.stack = build_stack(stack)

        elif stack is None and stackfile:
            #
            # The stackfile argument is super-deprecated.
            #
            stackfile = pathjoin(self.layer.config.dirpath, stackfile)
            stack = parseXML(stackfile).firstChild
            
            assert stack.tagName == 'stack', \
                   'Expecting root element "stack" but got "%s"' % stack.tagName
    
            self.stack = makeStack(stack)
        
        else:
            raise Exception('Note sure what to do with this stack argument: %s' % repr(stack))
        
    def renderTile(self, width, height, srs, coord):
    
        rgba = [numpy.zeros((width, height), float) for chan in range(4)]
        
        rgba = self.stack.render(self.layer.config, rgba, coord)
        
        return _rgba2img(rgba)

class Composite(Provider):
    """ An old name for the Provider class, deprecated for the next version.
    """
    pass

def build_stack(obj):
    """ Build up a data structure of Stack and Layer objects from lists of dictionaries.
    
        Normally, this is applied to the "stack" parameter to Composite.Provider.
    """
    if type(obj) is list:
        layers = map(build_stack, obj)
        return Stack(layers)
    
    elif type(obj) is dict:
        keys = (('src', 'layername'), ('color', 'colorname'),
                ('mask', 'maskname'), ('opacity', 'opacity'),
                ('mode', 'blendmode'), ('adjustments', 'adjustments'),
                ('zoom', 'zoom'))

        args = [(arg, obj[key]) for (key, arg) in keys if key in obj]
        
        return Layer(**dict(args))

    else:
        raise Exception('Uh oh')

class Layer:
    """ A single image layer in a stack.
    
        Can include a reference to another layer for the source image, a second
        reference to another layer for the mask, and a color name for the fill.
    """
    def __init__(self, layername=None, colorname=None, maskname=None, opacity=1.0,
                       blendmode=None, adjustments=None, zoom=""):
        """ A new image layer.

            Arguments:
            
              layername:
                Name of the primary source image layer.
              
              colorname:
                Fill color, passed to make_color().
              
              maskname:
                Name of the mask image layer.
        """
        self.layername = layername
        self.colorname = colorname
        self.maskname = maskname
        self.opacity = opacity
        self.blendmode = blendmode
        self.adjustments = adjustments
        
        zooms = re.search("^(\d+)-(\d+)$|^(\d+)$", zoom) if zoom else None
        
        if zooms:
            min_zoom, max_zoom, at_zoom = zooms.groups()
            
            if min_zoom is not None and max_zoom is not None:
                self.min_zoom, self.max_zoom = int(min_zoom), int(max_zoom)
            elif at_zoom is not None:
                self.min_zoom, self.max_zoom = int(at_zoom), int(at_zoom)
        
        else:
            self.min_zoom, self.max_zoom = 0, float('inf')

    def in_zoom(self, zoom):
        """ Return true if the requested zoom level is valid for this layer.
        """
        return self.min_zoom <= zoom and zoom <= self.max_zoom
    
    def render(self, config, input_rgba, coord):
        """ Render this image layer.

            Given a configuration object, starting image, and coordinate,
            return an output image with the contents of this image layer.
        """
        has_layer, has_color, has_mask = False, False, False
        
        output_rgba = [chan.copy() for chan in input_rgba]
    
        if self.layername:
            layer = config.layers[self.layername]
            mime, body = TileStache.getTile(layer, coord, 'png')
            layer_img = Image.open(StringIO(body)).convert('RGBA')
            layer_rgba = _img2rgba(layer_img)

            has_layer = True
        
        if self.maskname:
            layer = config.layers[self.maskname]
            mime, body = TileStache.getTile(layer, coord, 'png')
            mask_img = Image.open(StringIO(body)).convert('L')
            mask_chan = _img2arr(mask_img).astype(numpy.float32) / 255.

            has_mask = True

        if self.colorname:
            color = make_color(self.colorname)
            color_rgba = [numpy.zeros(output_rgba[0].shape, numpy.float32) + band/255.0 for band in color]

            has_color = True

        if has_layer:
            layer_rgba = apply_adjustments(layer_rgba, self.adjustments)
        
        if has_layer and has_color and has_mask:
            raise KnownUnknown("You can't specify src, color and mask together in a Composite Layer: %s, %s, %s" % (repr(self.layername), repr(self.colorname), repr(self.maskname)))
        
        elif has_layer and has_color:
            # color first, then layer
            output_rgba = blend_images(output_rgba, color_rgba[:3], color_rgba[3], self.opacity, self.blendmode)
            output_rgba = blend_images(output_rgba, layer_rgba[:3], layer_rgba[3], self.opacity, self.blendmode)

        elif has_layer and has_mask:
            # need to combine the masks here
            layermask_chan = layer_rgba[3] * mask_chan
            output_rgba = blend_images(output_rgba, layer_rgba[:3], layermask_chan, self.opacity, self.blendmode)

        elif has_color and has_mask:
            output_rgba = blend_images(output_rgba, color_rgba[:3], mask_chan, self.opacity, self.blendmode)
        
        elif has_layer:
            output_rgba = blend_images(output_rgba, layer_rgba[:3], layer_rgba[3], self.opacity, self.blendmode)
        
        elif has_color:
            output_rgba = blend_images(output_rgba, color_rgba[:3], color_rgba[3], self.opacity, self.blendmode)

        elif has_mask:
            raise KnownUnknown("You have to provide more than just a mask to Composite Layer: %s" % repr(self.maskname))

        else:
            raise KnownUnknown("You have to provide at least some combination of src, color and mask to Composite Layer")

        return output_rgba

    def __str__(self):
        return self.layername

class Stack:
    """ A stack of image layers.
    """
    def __init__(self, layers):
        """ A new image stack.
        
            Argument:
            
              layers:
                List of Layer instances.
        """
        self.layers = layers

    def in_zoom(self, level):
        """
        """
        return True
    
    def render(self, config, input_rgba, coord):
        """ Render this image stack.

            Given a configuration object, starting image, and coordinate,
            return an output image with the results of all the layers in
            this stack pasted on in turn.
        """
        stack_rgba = [numpy.zeros(chan.shape, chan.dtype) for chan in input_rgba]
        
        for layer in self.layers:
            try:
                if layer.in_zoom(coord.zoom):
                    stack_rgba = layer.render(config, stack_rgba, coord)

            except IOError:
                # Be permissive of I/O errors getting sub-layers, for example if a
                # proxy layer referenced here doesn't have an image for a zoom level.
                # TODO: regret this later.
                pass

        return blend_images(input_rgba, stack_rgba[:3], stack_rgba[3], 1, None)

def make_color(color):
    """ Convert colors expressed as HTML-style RGB(A) strings to tuples.
        
        Returns four-element RGBA tuple, e.g. (0xFF, 0x99, 0x00, 0xFF).
    
        Examples:
          white: "#ffffff", "#fff", "#ffff", "#ffffffff"
          black: "#000000", "#000", "#000f", "#000000ff"
          null: "#0000", "#00000000"
          orange: "#f90", "#ff9900", "#ff9900ff"
          transparent orange: "#f908", "#ff990088"
    """
    if type(color) not in (str, unicode):
        raise KnownUnknown('Color must be a string: %s' % repr(color))

    if color[0] != '#':
        raise KnownUnknown('Color must start with hash: "%s"' % color)

    if len(color) not in (4, 5, 7, 9):
        raise KnownUnknown('Color must have three, four, six or seven hex chars: "%s"' % color)

    if len(color) == 4:
        color = ''.join([color[i] for i in (0, 1, 1, 2, 2, 3, 3)])

    elif len(color) == 5:
        color = ''.join([color[i] for i in (0, 1, 1, 2, 2, 3, 3, 4, 4)])
    
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        a = len(color) == 7 and 0xFF or int(color[7:9], 16)

    except ValueError:
        raise KnownUnknown('Color must be made up of valid hex chars: "%s"' % color)

    return r, g, b, a

def _arr2img(ar):
    """ Convert Numeric array to PIL Image.
    """
    return Image.fromstring('L', (ar.shape[1], ar.shape[0]), ar.astype(numpy.ubyte).tostring())

def _img2arr(im):
    """ Convert PIL Image to Numeric array.
    """
    assert im.mode == 'L'
    return numpy.reshape(numpy.fromstring(im.tostring(), numpy.ubyte), (im.size[1], im.size[0]))

def _rgba2img(rgba):
    """ Convert four Numeric array objects to PIL Image.
    """
    assert type(rgba) is list
    return Image.merge('RGBA', [_arr2img(numpy.round(band * 255.0).astype(numpy.ubyte)) for band in rgba])

def _img2rgba(im):
    """ Convert PIL Image to four Numeric array objects.
    """
    assert im.mode == 'RGBA'
    return [_img2arr(band).astype(numpy.float32) / 255.0 for band in im.split()]

def apply_adjustments(rgba, adjustments):
    """ Apply image adjustments one by one and return a modified image.
    
        Working adjustments:
        
          threshold:
            Calls apply_threshold_adjustment()
        
          curves:
            Calls apply_curves_adjustment()
        
          curves2:
            Calls apply_curves2_adjustment()
    """
    if not adjustments:
        return rgba

    for adjustment in adjustments:
        name, args = adjustment[0], adjustment[1:]

        if name == 'threshold':
            rgba = apply_threshold_adjustment(rgba, *args)
        
        elif name == 'curves':
            rgba = apply_curves_adjustment(rgba, *args)
        
        elif name == 'curves2':
            rgba = apply_curves2_adjustment(rgba, *args)
        
        else:
            raise KnownUnknown('Unrecognized composite adjustment: "%s" with args %s' % (name, repr(args)))
    
    return rgba

def apply_threshold_adjustment(rgba, red_value, green_value=None, blue_value=None):
    """
    """
    if green_value is None or blue_value is None:
        # if there aren't three provided, use the one
        green_value, blue_value = red_value, red_value

    # channels
    red, green, blue, alpha = rgba
    
    # knowns are given in 0-255 range, need to be converted to floats
    red_value, green_value, blue_value = red_value / 255.0, green_value / 255.0, blue_value / 255.0
    
    red[red > red_value] = 1
    red[red <= red_value] = 0
    
    green[green > green_value] = 1
    green[green <= green_value] = 0
    
    blue[blue > blue_value] = 1
    blue[blue <= blue_value] = 0
    
    return red, green, blue, alpha

def apply_curves_adjustment(rgba, black_grey_white):
    """ Adjustment inspired by Photoshop "Curves" feature.
    
        Arguments are three integers that are intended to be mapped to black,
        grey, and white outputs. Curves2 offers more flexibility, see
        apply_curves2_adjustment().
        
        Darken a light image by pushing light grey to 50% grey, 0xCC to 0x80:
    
          [
            "curves",
            [0, 204, 255]
          ]
    """
    # channels
    red, green, blue, alpha = rgba
    black, grey, white = black_grey_white
    
    # coefficients
    a, b, c = [sympy.Symbol(n) for n in 'abc']
    
    # knowns are given in 0-255 range, need to be converted to floats
    black, grey, white = black / 255.0, grey / 255.0, white / 255.0
    
    # black, gray, white
    eqs = [a * black**2 + b * black + c - 0.0,
           a *  grey**2 + b *  grey + c - 0.5,
           a * white**2 + b * white + c - 1.0]
    
    co = sympy.solve(eqs, a, b, c)
    
    # arrays for each coefficient
    a, b, c = [float(co[n]) * numpy.ones(red.shape, numpy.float32) for n in (a, b, c)]
    
    # arithmetic
    red   = numpy.clip(a * red**2   + b * red   + c, 0, 1)
    green = numpy.clip(a * green**2 + b * green + c, 0, 1)
    blue  = numpy.clip(a * blue**2  + b * blue  + c, 0, 1)
    
    return red, green, blue, alpha

def apply_curves2_adjustment(rgba, map_red, map_green=None, map_blue=None):
    """ Adjustment inspired by Photoshop "Curves" feature.
    
        Arguments are given in the form of three value mappings, typically
        mapping black, grey and white input and output values. One argument
        indicates an effect applicable to all channels, three arguments apply
        effects to each channel separately.
    
        Simple monochrome inversion:
    
          [
            "curves2",
            [[0, 255], [128, 128], [255, 0]]
          ]
    
        Darken a light image by pushing light grey down by 50%, 0x99 to 0x66:
    
          [
            "curves2",
            [[0, 255], [153, 102], [255, 0]]
          ]
    
        Shaded hills, with Imhof-style purple-blue shadows and warm highlights: 
        
          [
            "curves2",
            [[0, 22], [128, 128], [255, 255]],
            [[0, 29], [128, 128], [255, 255]],
            [[0, 65], [128, 128], [255, 228]]
          ]
    """
    if map_green is None or map_blue is None:
        # if there aren't three provided, use the one
        map_green, map_blue = map_red, map_red

    # channels
    red, green, blue, alpha = rgba
    out = []
    
    for (chan, input) in ((red, map_red), (green, map_green), (blue, map_blue)):
        # coefficients
        a, b, c = [sympy.Symbol(n) for n in 'abc']
        
        # parameters given in 0-255 range, need to be converted to floats
        (in_1, out_1), (in_2, out_2), (in_3, out_3) \
            = [(in_ / 255.0, out_ / 255.0) for (in_, out_) in input]
        
        # quadratic function
        eqs = [a * in_1**2 + b * in_1 + c - out_1,
               a * in_2**2 + b * in_2 + c - out_2,
               a * in_3**2 + b * in_3 + c - out_3]
        
        co = sympy.solve(eqs, a, b, c)
        
        # arrays for each coefficient
        a, b, c = [float(co[n]) * numpy.ones(chan.shape, numpy.float32) for n in (a, b, c)]
        
        # arithmetic
        out.append(numpy.clip(a * chan**2 + b * chan + c, 0, 1))
    
    return out + [alpha]

def blend_images(bottom_rgba, top_rgb, mask_chan, opacity, blendmode):
    """ Blend images using a given mask, opacity, and blend mode.
    
        Working blend modes:
        None for plain pass-through, "screen", "multiply", "linear light", and "hard light".
    """
    if opacity == 0 or not mask_chan.any():
        # no-op for zero opacity or empty mask
        return [numpy.copy(chan) for chan in bottom_rgba]
    
    # prepare unitialized output arrays
    output_rgba = [numpy.empty_like(chan) for chan in bottom_rgba]
    
    if not blendmode:
        # plain old paste
        output_rgba[:3] = [numpy.copy(chan) for chan in top_rgb]

    else:
        blend_functions = {'screen': blend_channels_screen,
                           'multiply': blend_channels_multiply,
                           'linear light': blend_channels_linear_light,
                           'hard light': blend_channels_hard_light}

        if blendmode in blend_functions:
            for c in (0, 1, 2):
                blend_function = blend_functions[blendmode]
                output_rgba[c] = blend_function(bottom_rgba[c], top_rgb[c])
        
        else:
            raise KnownUnknown('Unrecognized blend mode: "%s"' % blendmode)
    
    # comined effective mask channel
    if opacity < 1:
        mask_chan = mask_chan * opacity

    # pixels from mask that aren't full-white
    gr = mask_chan < 1
    
    if gr.any():
        # we have some shades of gray to take care of
        for c in (0, 1, 2):
            #
            # Math borrowed from Wikipedia; C0 is the variable alpha_denom:
            # http://en.wikipedia.org/wiki/Alpha_compositing#Analytical_derivation_of_the_over_operator
            #
            
            alpha_denom = 1 - (1 - mask_chan) * (1 - bottom_rgba[3])
            nz = alpha_denom > 0 # non-zero alpha denominator
            
            alpha_ratio = mask_chan[nz] / alpha_denom[nz]
            
            output_rgba[c][nz] = output_rgba[c][nz] * alpha_ratio \
                               + bottom_rgba[c][nz] * (1 - alpha_ratio)
            
            # let the zeros perish
            output_rgba[c][~nz] = 0
    
    # output mask is the screen of the existing and overlaid alphas
    output_rgba[3] = blend_channels_screen(bottom_rgba[3], mask_chan)

    return output_rgba

def blend_channels_screen(bottom_chan, top_chan):
    """ Return combination of bottom and top channels.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=screen_blending
    """
    return 1 - (1 - bottom_chan[:,:]) * (1 - top_chan[:,:])

def blend_channels_multiply(bottom_chan, top_chan):
    """ Return combination of bottom and top channels.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=multiply_blending
    """
    return bottom_chan[:,:] * top_chan[:,:]

def blend_channels_linear_light(bottom_chan, top_chan):
    """ Return combination of bottom and top channels.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=linear_light_blending
    """
    return numpy.clip(bottom_chan[:,:] + 2 * top_chan[:,:] - 1, 0, 1)

def blend_channels_hard_light(bottom_chan, top_chan):
    """ Return combination of bottom and top channels.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=hard_light_blending
    """
    # different pixel subsets for dark and light parts of overlay
    dk, lt = top_chan < .5, top_chan >= .5
    
    output_chan = numpy.empty(bottom_chan.shape, bottom_chan.dtype)
    output_chan[dk] = 2 * bottom_chan[dk] * top_chan[dk]
    output_chan[lt] = 1 - 2 * (1 - bottom_chan[lt]) * (1 - top_chan[lt])
    
    return output_chan

def makeColor(color):
    """ An old name for the make_color function, deprecated for the next version.
    """
    return make_color(color)
    
def makeLayer(element):
    """ Build a Layer object from an XML element, deprecated for the next version.
    """
    kwargs = {}
    
    if element.hasAttribute('src'):
        kwargs['layername'] = element.getAttribute('src')

    if element.hasAttribute('color'):
        kwargs['colorname'] = element.getAttribute('color')
    
    for child in element.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            if child.tagName == 'mask' and child.hasAttribute('src'):
                kwargs['maskname'] = child.getAttribute('src')

    print >> sys.stderr, 'Making a layer from', kwargs
    
    return Layer(**kwargs)

def makeStack(element):
    """ Build a Stack object from an XML element, deprecated for the next version.
    """
    layers = []
    
    for child in element.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            if child.tagName == 'stack':
                stack = makeStack(child)
                layers.append(stack)
            
            elif child.tagName == 'layer':
                layer = makeLayer(child)
                layers.append(layer)

            else:
                raise Exception('Unknown element "%s"' % child.tagName)

    print >> sys.stderr, 'Making a stack with %d layers' % len(layers)

    return Stack(layers)

if __name__ == '__main__':

    import unittest
    
    import TileStache.Core
    import TileStache.Caches
    import TileStache.Geography
    import TileStache.Config
    import ModestMaps.Core
    
    class SizelessImage:
        """ Wrap an image without wrapping the size() method, for Layer.render().
        """
        def __init__(self, img):
            self.img = img
        
        def save(self, out, format):
            self.img.save(out, format)
    
    class TinyBitmap:
        """ A minimal provider that only returns 3x3 bitmaps from strings.
        """
        def __init__(self, string):
            self.img = Image.fromstring('RGBA', (3, 3), string)

        def renderTile(self, *args, **kwargs):
            return SizelessImage(self.img)

    def tinybitmap_layer(config, string):
        """ Gin up a fake layer with a TinyBitmap provider.
        """
        meta = TileStache.Core.Metatile()
        proj = TileStache.Geography.SphericalMercator()
        layer = TileStache.Core.Layer(config, proj, meta)
        layer.provider = TinyBitmap(string)

        return layer

    def minimal_stack_layer(config, stack):
        """
        """
        meta = TileStache.Core.Metatile()
        proj = TileStache.Geography.SphericalMercator()
        layer = TileStache.Core.Layer(config, proj, meta)
        layer.provider = Provider(layer, stack=stack)

        return layer
    
    class ColorTests(unittest.TestCase):
        """
        """
        def testColors(self):
            assert make_color('#ffffff') == (0xFF, 0xFF, 0xFF, 0xFF), 'white'
            assert make_color('#fff') == (0xFF, 0xFF, 0xFF, 0xFF), 'white again'
            assert make_color('#ffff') == (0xFF, 0xFF, 0xFF, 0xFF), 'white again again'
            assert make_color('#ffffffff') == (0xFF, 0xFF, 0xFF, 0xFF), 'white again again again'

            assert make_color('#000000') == (0x00, 0x00, 0x00, 0xFF), 'black'
            assert make_color('#000') == (0x00, 0x00, 0x00, 0xFF), 'black again'
            assert make_color('#000f') == (0x00, 0x00, 0x00, 0xFF), 'black again'
            assert make_color('#000000ff') == (0x00, 0x00, 0x00, 0xFF), 'black again again'

            assert make_color('#0000') == (0x00, 0x00, 0x00, 0x00), 'null'
            assert make_color('#00000000') == (0x00, 0x00, 0x00, 0x00), 'null again'

            assert make_color('#f90') == (0xFF, 0x99, 0x00, 0xFF), 'orange'
            assert make_color('#ff9900') == (0xFF, 0x99, 0x00, 0xFF), 'orange again'
            assert make_color('#ff9900ff') == (0xFF, 0x99, 0x00, 0xFF), 'orange again again'

            assert make_color('#f908') == (0xFF, 0x99, 0x00, 0x88), 'transparent orange'
            assert make_color('#ff990088') == (0xFF, 0x99, 0x00, 0x88), 'transparent orange again'
        
        def testErrors(self):

            # it has to be a string
            self.assertRaises(KnownUnknown, make_color, True)
            self.assertRaises(KnownUnknown, make_color, None)
            self.assertRaises(KnownUnknown, make_color, 1337)
            self.assertRaises(KnownUnknown, make_color, [93])
            
            # it has to start with a hash
            self.assertRaises(KnownUnknown, make_color, 'hello')
            
            # it has to have 3, 4, 6 or 7 hex chars
            self.assertRaises(KnownUnknown, make_color, '#00')
            self.assertRaises(KnownUnknown, make_color, '#00000')
            self.assertRaises(KnownUnknown, make_color, '#0000000')
            self.assertRaises(KnownUnknown, make_color, '#000000000')
            
            # they have to actually hex chars
            self.assertRaises(KnownUnknown, make_color, '#foo')
            self.assertRaises(KnownUnknown, make_color, '#bear')
            self.assertRaises(KnownUnknown, make_color, '#monkey')
            self.assertRaises(KnownUnknown, make_color, '#dedboeuf')
    
    class CompositeTests(unittest.TestCase):
        """
        """
        def setUp(self):
    
            cache = TileStache.Caches.Test()
            self.config = TileStache.Config.Configuration(cache, '.')
            
            # Sort of a sw/ne diagonal street, with a top-left corner halo:
            # 
            # +------+   +------+   +------+   +------+   +------+
            # |\\\\\\|   |++++--|   |  ////|   |    ''|   |\\//''|
            # |\\\\\\| + |++++--| + |//////| + |  ''  | > |//''\\|
            # |\\\\\\|   |------|   |////  |   |''    |   |''\\\\|
            # +------+   +------+   +------+   +------+   +------+
            # base       halos      outlines   streets    output
            #
            # Just trust the tests.
            #
            _fff, _ccc, _999, _000, _nil = '\xFF\xFF\xFF\xFF', '\xCC\xCC\xCC\xFF', '\x99\x99\x99\xFF', '\x00\x00\x00\xFF', '\x00\x00\x00\x00'
            
            self.config.layers = \
            {
                'base':     tinybitmap_layer(self.config, _ccc * 9),
                'halos':    tinybitmap_layer(self.config, _fff + _fff + _000 + _fff + _fff + (_000 * 4)),
                'outlines': tinybitmap_layer(self.config, _nil + (_999 * 7) + _nil),
                'streets':  tinybitmap_layer(self.config, _nil + _nil + _fff + _nil + _fff + _nil + _fff + _nil + _nil)
            }
            
            self.start_img = Image.new('RGBA', (3, 3), (0x00, 0x00, 0x00, 0x00))
        
        def test0(self):
    
            stack = \
                [
                    {"src": "base"},
                    [
                        {"src": "outlines"},
                        {"src": "streets"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0xCC, 0xCC, 0xCC, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0x99, 0x99, 0x99, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
        
        def test1(self):
    
            stack = \
                [
                    {"src": "base"},
                    [
                        {"src": "outlines", "mask": "halos"},
                        {"src": "streets"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0xCC, 0xCC, 0xCC, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0xCC, 0xCC, 0xCC, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
        
        def test2(self):
    
            stack = \
                [
                    {"color": "#ccc"},
                    [
                        {"src": "outlines", "mask": "halos"},
                        {"src": "streets"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0xCC, 0xCC, 0xCC, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0xCC, 0xCC, 0xCC, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
        
        def test3(self):
            
            stack = \
                [
                    {"color": "#ccc"},
                    [
                        {"color": "#999", "mask": "halos"},
                        {"src": "streets"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0xCC, 0xCC, 0xCC, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
        
        def test4(self):
    
            stack = \
                [
                    [
                        {"color": "#999", "mask": "halos"},
                        {"src": "streets"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0x00, 0x00, 0x00, 0x00), 'center right pixel'
            assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0x00, 0x00, 0x00, 0x00), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0x00, 0x00, 0x00, 0x00), 'bottom right pixel'
        
        def test5(self):

            stack = {"src": "streets", "color": "#999", "mask": "halos"}
            layer = minimal_stack_layer(self.config, stack)
            
            # it's an error to specify scr, color, and mask all together
            self.assertRaises(KnownUnknown, layer.provider.renderTile, 3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))

            stack = {"mask": "halos"}
            layer = minimal_stack_layer(self.config, stack)
            
            # it's also an error to specify just a mask
            self.assertRaises(KnownUnknown, layer.provider.renderTile, 3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))

            stack = {}
            layer = minimal_stack_layer(self.config, stack)
            
            # an empty stack is not so great
            self.assertRaises(KnownUnknown, layer.provider.renderTile, 3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))

    class AlphaTests(unittest.TestCase):
        """
        """
        def setUp(self):
    
            cache = TileStache.Caches.Test()
            self.config = TileStache.Config.Configuration(cache, '.')
            
            _808f = '\x80\x80\x80\xFF'
            _fff0, _fff8, _ffff = '\xFF\xFF\xFF\x00', '\xFF\xFF\xFF\x80', '\xFF\xFF\xFF\xFF'
            _0000, _0008, _000f = '\x00\x00\x00\x00', '\x00\x00\x00\x80', '\x00\x00\x00\xFF'
            
            self.config.layers = \
            {
                # 50% gray all over
                'gray':       tinybitmap_layer(self.config, _808f * 9),
                
                # nothing anywhere
                'nothing':    tinybitmap_layer(self.config, _0000 * 9),
                
                # opaque horizontal gradient, black to white
                'h gradient': tinybitmap_layer(self.config, (_000f + _808f + _ffff) * 3),
                
                # transparent white at top to opaque white at bottom
                'white wipe': tinybitmap_layer(self.config, _fff0 * 3 + _fff8 * 3 + _ffff * 3),
                
                # transparent black at top to opaque black at bottom
                'black wipe': tinybitmap_layer(self.config, _0000 * 3 + _0008 * 3 + _000f * 3)
            }
            
            self.start_img = Image.new('RGBA', (3, 3), (0x00, 0x00, 0x00, 0x00))
        
        def test0(self):
            
            stack = \
                [
                    [
                        {"src": "gray"},
                        {"src": "white wipe"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
        
        def test1(self):
            
            stack = \
                [
                    [
                        {"src": "gray"},
                        {"src": "black wipe"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x40, 0x40, 0x40, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0x40, 0x40, 0x40, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0x40, 0x40, 0x40, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom right pixel'
        
        def test2(self):
        
            stack = \
                [
                    [
                        {"src": "gray"},
                        {"src": "white wipe", "mask": "h gradient"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x80, 0x80, 0x80, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xA0, 0xA0, 0xA0, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0x80, 0x80, 0x80, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0xC0, 0xC0, 0xC0, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
        
        def test3(self):
            
            stack = \
                [
                    [
                        {"src": "gray"},
                        {"src": "black wipe", "mask": "h gradient"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
            assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
            assert img.getpixel((0, 1)) == (0x80, 0x80, 0x80, 0xFF), 'center left pixel'
            assert img.getpixel((1, 1)) == (0x60, 0x60, 0x60, 0xFF), 'middle pixel'
            assert img.getpixel((2, 1)) == (0x40, 0x40, 0x40, 0xFF), 'center right pixel'
            assert img.getpixel((0, 2)) == (0x80, 0x80, 0x80, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0x40, 0x40, 0x40, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom right pixel'
        
        def test4(self):
            
            stack = \
                [
                    [
                        {"src": "nothing"},
                        {"src": "white wipe"}
                    ]
                ]
            
            layer = minimal_stack_layer(self.config, stack)
            img = layer.provider.renderTile(3, 3, None, ModestMaps.Core.Coordinate(0, 0, 0))
            
            assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0x00), 'top left pixel'
            assert img.getpixel((1, 0)) == (0x00, 0x00, 0x00, 0x00), 'top center pixel'
            assert img.getpixel((2, 0)) == (0x00, 0x00, 0x00, 0x00), 'top right pixel'
            assert img.getpixel((0, 1)) == (0xFF, 0xFF, 0xFF, 0x80), 'center left pixel'
            assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0x80), 'middle pixel'
            assert img.getpixel((2, 1)) == (0xFF, 0xFF, 0xFF, 0x80), 'center right pixel'
            assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
            assert img.getpixel((1, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom center pixel'
            assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    unittest.main()

########NEW FILE########
__FILENAME__ = GDAL
""" Minimally-tested GDAL image provider.

Based on existing work in OAM (https://github.com/oam/oam), this GDAL provider
is the bare minimum necessary to do simple output of GDAL data sources.

Sample configuration:

    "provider":
    {
      "class": "TileStache.Goodies.Providers.GDAL:Provider",
      "kwargs": { "filename": "landcover-1km.tif", "resample": "linear", "maskband": 2 }
    }

Valid values for resample are "cubic", "cubicspline", "linear", and "nearest".

The maskband argument is optional. If present and greater than 0, it specifies
the GDAL dataset band whose mask should be used as an alpha channel. If maskband
is 0 (the default), do not create an alpha channel.

With a bit more work, this provider will be ready for fully-supported inclusion
in TileStache proper. Until then, it will remain here in the Goodies package.
"""
from urlparse import urlparse, urljoin

try:
    from PIL import Image
except ImportError:
    import Image

try:
    from osgeo import gdal
    from osgeo import osr
except ImportError:
    # well it won't work but we can still make the documentation.
    pass

resamplings = {'cubic': gdal.GRA_Cubic, 'cubicspline': gdal.GRA_CubicSpline, 'linear': gdal.GRA_Bilinear, 'nearest': gdal.GRA_NearestNeighbour}

class Provider:

    def __init__(self, layer, filename, resample='cubic', maskband=0):
        """
        """
        self.layer = layer
        
        fileurl = urljoin(layer.config.dirpath, filename)
        scheme, h, file_path, p, q, f = urlparse(fileurl)
        
        if scheme not in ('', 'file'):
            raise Exception('GDAL file must be on the local filesystem, not: '+fileurl)
        
        if resample not in resamplings:
            raise Exception('Resample must be "cubic", "linear", or "nearest", not: '+resample)
        
        self.filename = file_path
        self.resample = resamplings[resample]
        self.maskband = maskband
    
    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        """
        """
        src_ds = gdal.Open(str(self.filename))
        driver = gdal.GetDriverByName('GTiff')
        
        if src_ds.GetGCPs():
            src_ds.SetProjection(src_ds.GetGCPProjection())
        
        grayscale_src = (src_ds.RasterCount == 1)

        try:
            # Prepare output gdal datasource -----------------------------------
            
            area_ds = driver.Create('/vsimem/output', width, height, 3)
            
            if area_ds is None:
                raise Exception('uh oh.')
            
            # If we are using a mask band, create a data set which possesses a 'NoData' value enabling us to create a
            # mask for validity.
            mask_ds = None
            if self.maskband > 0:
                # We have to create a mask dataset with the same number of bands as the input since there isn't an
                # efficient way to extract a single band from a dataset which doesn't risk attempting to copy the entire
                # dataset.
                mask_ds = driver.Create('/vsimem/alpha', width, height, src_ds.RasterCount, gdal.GDT_Float32)
            
                if mask_ds is None:
                    raise Exception('Failed to create dataset mask.')

                [mask_ds.GetRasterBand(i).SetNoDataValue(float('nan')) for i in xrange(1, src_ds.RasterCount+1)]
            
            merc = osr.SpatialReference()
            merc.ImportFromProj4(srs)
            area_ds.SetProjection(merc.ExportToWkt())
            if mask_ds is not None:
                mask_ds.SetProjection(merc.ExportToWkt())
            
            # note that 900913 points north and east
            x, y = xmin, ymax
            w, h = xmax - xmin, ymin - ymax
            
            gtx = [x, w/width, 0, y, 0, h/height]
            area_ds.SetGeoTransform(gtx)
            if mask_ds is not None:
                mask_ds.SetGeoTransform(gtx)
            
            # Adjust resampling method -----------------------------------------
            
            resample = self.resample
            
            if resample == gdal.GRA_CubicSpline:
                #
                # I've found through testing that when ReprojectImage is used
                # on two same-scaled datasources, GDAL will visibly darken the
                # output and the results look terrible. Switching resampling
                # from cubic spline to bicubic in these cases fixes the output.
                #
                xscale = area_ds.GetGeoTransform()[1] / src_ds.GetGeoTransform()[1]
                yscale = area_ds.GetGeoTransform()[5] / src_ds.GetGeoTransform()[5]
                diff = max(abs(xscale - 1), abs(yscale - 1))
                
                if diff < .001:
                    resample = gdal.GRA_Cubic
            
            # Create rendered area ---------------------------------------------
            
            src_sref = osr.SpatialReference()
            src_sref.ImportFromWkt(src_ds.GetProjection())
            
            gdal.ReprojectImage(src_ds, area_ds, src_ds.GetProjection(), area_ds.GetProjection(), resample)
            if mask_ds is not None:
                # Interpolating validity makes no sense and so we can use nearest neighbour resampling here no matter
                # what is requested.
                gdal.ReprojectImage(src_ds, mask_ds, src_ds.GetProjection(), mask_ds.GetProjection(), gdal.GRA_NearestNeighbour)
            
            channel = grayscale_src and (1, 1, 1) or (1, 2, 3)
            r, g, b = [area_ds.GetRasterBand(i).ReadRaster(0, 0, width, height) for i in channel]

            if mask_ds is None:
                data = ''.join([''.join(pixel) for pixel in zip(r, g, b)])
                area = Image.fromstring('RGB', (width, height), data)
            else:
                a = mask_ds.GetRasterBand(self.maskband).GetMaskBand().ReadRaster(0, 0, width, height)
                data = ''.join([''.join(pixel) for pixel in zip(r, g, b, a)])
                area = Image.fromstring('RGBA', (width, height), data)

        finally:
            driver.Delete('/vsimem/output')
            if self.maskband > 0:
                driver.Delete('/vsimem/alpha')
        
        return area

########NEW FILE########
__FILENAME__ = Grid
""" Grid rendering for TileStache.

UTM provider found here draws gridlines in tiles, in transparent images suitable
for use as map overlays.

Example TileStache provider configuration:

"grid":
{
    "provider": {"class": "TileStache.Goodies.Providers.Grid:UTM",
                 "kwargs": {"display": "MGRS", "spacing": 200, "tick": 10}}
}
"""

import sys

from math import log as _log, pow as _pow, hypot as _hypot, ceil as _ceil
from os.path import dirname, join as pathjoin, abspath

try:
    import PIL
except ImportError:
    # On some systems, PIL's modules are imported from their own modules.
    import Image
    import ImageDraw
    import ImageFont
else:
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageFont

import TileStache

try:
    from pyproj import Proj
except ImportError:
    # well I guess we can't do any more things now.
    pass

def lat2hemi(lat):
    """ Convert latitude to single-letter hemisphere, "N" or "S".
    """
    return lat >= 0 and 'N' or 'S'

def lon2zone(lon):
    """ Convert longitude to numeric UTM zone, 1-60.
    """
    zone = int(round(lon / 6. + 30.5))
    return ((zone - 1) % 60) + 1

def lat2zone(lat):
    """ Convert longitude to single-letter UTM zone.
    """
    zone = int(round(lat / 8. + 9.5))
    return 'CDEFGHJKLMNPQRSTUVWX'[zone]

def lonlat2grid(lon, lat):
    """ Convert lat/lon pair to alphanumeric UTM zone.
    """
    return '%d%s' % (lon2zone(lon), lat2zone(lat))

def utm2mgrs(e, n, grid, zeros=0):
    """ Convert UTM easting/northing pair and grid zone
        to MGRS-style grid reference, e.g. "18Q YF 80 52".
        
        Adapted from http://haiticrisismap.org/js/usng2.js
    """
    square_set = int(grid[:-1]) % 6
    
    ew_idx = int(e / 100000) - 1            # should be [100000, 9000000]
    ns_idx = int((n % 2000000) / 100000)    # should [0, 10000000) => [0, 2000000)
    
    ns_letters_135 = 'ABCDEFGHJKLMNPQRSTUV'
    ns_letters_246 = 'FGHJKLMNPQRSTUVABCDE'
    
    ew_letters_14 = 'ABCDEFGH'
    ew_letters_25 = 'JKLMNPQR'
    ew_letters_36 = 'STUVWXYZ'

    if square_set == 1:
        square = ew_letters_14[ew_idx] + ns_letters_135[ns_idx]

    elif square_set == 2:
        square = ew_letters_25[ew_idx] + ns_letters_246[ns_idx]

    elif square_set == 3:
        square = ew_letters_36[ew_idx] + ns_letters_135[ns_idx]

    elif square_set == 4:
        square = ew_letters_14[ew_idx] + ns_letters_246[ns_idx]

    elif square_set == 5:
        square = ew_letters_25[ew_idx] + ns_letters_135[ns_idx]

    else:
        square = ew_letters_36[ew_idx] + ns_letters_246[ns_idx]

    easting = '%05d' % (e % 100000)
    northing = '%05d' % (n % 100000)
    
    return ' '.join( [grid, square, easting[:-zeros], northing[:-zeros]] )

def transform(w, h, xmin, ymin, xmax, ymax):
    """
    """
    xspan, yspan = (xmax - xmin), (ymax - ymin)

    xm = w / xspan
    ym = h / yspan
    
    xb = w - xm * xmax
    yb = h - ym * ymax
    
    return lambda x, y: (int(xm * x + xb), int(ym * y + yb))

class UTM:
    """ UTM Grid provider, renders transparent gridlines.
    
        Example configuration:
    
        "grid":
        {
            "provider": {"class": "TileStache.Goodies.Providers.Grid.UTM",
                         "kwargs": {"display": "MGRS", "spacing": 200, "tick": 10}}
        }
    
        Additional arguments:
        
        - display (optional, default: "UTM")
            Label display style. UTM: "18Q 0780 2052", MGRS: "18Q YF 80 52".
        - spacing (optional, default: 128)
            Minimum number of pixels between grid lines.
        - tick (optional, default 8)
            Pixel length of 1/10 grid tick marks.
    """
    
    def __init__(self, layer, display='UTM', spacing=128, tick=8):
        self.display = display.lower()
        self.spacing = int(spacing)
        self.tick = int(tick)

        file = 'DejaVuSansMono-alphanumeric.ttf'
        dirs = [dirname(__file__),
                abspath(pathjoin(dirname(__file__), '../../../share/tilestache')),
                sys.prefix + '/local/share/tilestache',
                sys.prefix + '/share/tilestache']

        for dir in dirs:
            try:
                font = ImageFont.truetype(pathjoin(dir, file), 14)
            except IOError:
                font = None
            else:
                break

        if font is None:
            raise Exception("Couldn't find %s after looking in %s." % (file, ', '.join(dirs)))

        self.font = font
        
    def renderArea(self, width_, height_, srs, xmin_, ymin_, xmax_, ymax_, zoom):
        """
        """
        merc = Proj(srs)
        
        # use the center to figure out our UTM zone
        lon, lat = merc((xmin_ + xmax_)/2, (ymin_ + ymax_)/2, inverse=True)
        zone = lon2zone(lon)
        hemi = lat2hemi(lat)

        utm = Proj(proj='utm', zone=zone, datum='WGS84')
        
        # get to UTM coords
        (minlon, minlat), (maxlon, maxlat) = merc(xmin_, ymin_, inverse=1), merc(xmax_, ymax_, inverse=1)
        (xmin, ymin), (xmax, ymax) = utm(minlon, minlat), utm(maxlon, maxlat)

        # figure out how widely-spaced they should be
        pixels = _hypot(width_, height_)            # number of pixels across the image
        units = _hypot(xmax - xmin, ymax - ymin)    # number of UTM units across the image
        
        tick = self.tick * units/pixels             # desired tick length in UTM units
        
        count = pixels / self.spacing               # approximate number of lines across the image
        bound = units / count                       # too-precise step between lines in UTM units
        zeros = int(_ceil(_log(bound) / _log(10)))  # this value gets used again to format numbers
        step = int(_pow(10, zeros))                 # a step that falls right on the 10^n
        
        # and the outer UTM bounds
        xbot, xtop = int(xmin - xmin % step), int(xmax - xmax % step) + 2 * step
        ybot, ytop = int(ymin - ymin % step), int(ymax - xmax % step) + 2 * step
    
        # start doing things in pixels
        img = Image.new('RGBA', (width_, height_), (0xEE, 0xEE, 0xEE, 0x00))
        draw = ImageDraw.ImageDraw(img)
        xform = transform(width_, height_, xmin_, ymax_, xmax_, ymin_)
        
        lines = []
        labels = []
        
        for col in range(xbot, xtop, step):
            # set up the verticals
            utms = [(col, y) for y in range(ybot, ytop, step/10)]
            mercs = [merc(*utm(x, y, inverse=1)) for (x, y) in utms]
            lines.append( [xform(x, y) for (x, y) in mercs] )
            
            # and the tick marks
            for row in range(ybot, ytop, step/10):
                mercs = [merc(*utm(x, y, inverse=1)) for (x, y) in ((col, row), (col - tick, row))]
                lines.append( [xform(x, y) for (x, y) in mercs] )
        
        for row in range(ybot, ytop, step):
            # set up the horizontals
            utms = [(x, row) for x in range(xbot, xtop, step/10)]
            mercs = [merc(*utm(x, y, inverse=1)) for (x, y) in utms]
            lines.append( [xform(x, y) for (x, y) in mercs] )
            
            # and the tick marks
            for col in range(xbot, xtop, step/10):
                mercs = [merc(*utm(x, y, inverse=1)) for (x, y) in ((col, row), (col, row - tick))]
                lines.append( [xform(x, y) for (x, y) in mercs] )

        # set up the intersection labels
        for x in range(xbot, xtop, step):
            for y in range(ybot, ytop, step):
                lon, lat = utm(x, y, inverse=1)
                grid = lonlat2grid(lon, lat)
                point = xform(*merc(lon, lat))
                
                if self.display == 'utm':
                    e = ('%07d' % x)[:-zeros]
                    n = ('%07d' % y)[:-zeros]
                    text = ' '.join( [grid, e, n] )

                elif self.display == 'mgrs':
                    e, n = Proj(proj='utm', zone=lon2zone(lon), datum='WGS84')(lon, lat)
                    text = utm2mgrs(round(e), round(n), grid, zeros)
                
                labels.append( (point, text) )

        # do the drawing bits
        for ((x, y), text) in labels:
            x, y = x + 2, y - 18
            w, h = self.font.getsize(text)
            draw.rectangle((x - 2, y, x + w + 2, y + h), fill=(0xFF, 0xFF, 0xFF, 0x99))

        for line in lines:
            draw.line(line, fill=(0xFF, 0xFF, 0xFF))

        for line in lines:
            draw.line([(x-1, y-1) for (x, y) in line], fill=(0x00, 0x00, 0x00))

        for ((x, y), text) in labels:
            x, y = x + 2, y - 18
            draw.text((x, y), text, fill=(0x00, 0x00, 0x00), font=self.font)

        return img

########NEW FILE########
__FILENAME__ = MapnikGrid
""" Mapnik UTFGrid Provider.

Takes the first layer from the given mapnik xml file and renders it as UTFGrid
https://github.com/mapbox/utfgrid-spec/blob/master/1.2/utfgrid.md
It can then be used for this:
http://mapbox.github.com/wax/interaction-leaf.html
Only works with mapnik>=2.0 (Where the Grid functionality was introduced)

Use Sperical Mercator projection and the extension "json"

Sample configuration:

    "provider":
    {
      "class": "TileStache.Goodies.Providers.MapnikGrid:Provider",
      "kwargs":
      {
        "mapfile": "mymap.xml", 
        "fields":["name", "address"],
        "layer_index": 0,
        "wrapper": "grid",
        "scale": 4
      }
    }

mapfile: the mapnik xml file to load the map from
fields: The fields that should be added to the resulting grid json.
layer_index: The index of the layer you want from your map xml to be rendered
wrapper: If not included the json will be output raw, if included the json will be wrapped in "wrapper(JSON)" (for use with wax)
scale: What to divide the tile pixel size by to get the resulting grid size. Usually this is 4.
buffer: buffer around the queried features, in px, default 0. Use this to prevent problems on tile boundaries.
"""
import json
from TileStache.Core import KnownUnknown
from TileStache.Geography import getProjectionByName
from urlparse import urlparse, urljoin

try:
    import mapnik
except ImportError:
    pass

class Provider:

    def __init__(self, layer, mapfile, fields, layer_index=0, wrapper=None, scale=4, buffer=0):
        """
        """
        self.mapnik = None
        self.layer = layer

        maphref = urljoin(layer.config.dirpath, mapfile)
        scheme, h, path, q, p, f = urlparse(maphref)
        
        if scheme in ('file', ''):
            self.mapfile = path
        else:
            self.mapfile = maphref
        
        self.layer_index = layer_index
        self.wrapper = wrapper
        self.scale = scale
        self.buffer = buffer
        #De-Unicode the strings or mapnik gets upset
        self.fields = list(str(x) for x in fields)

        self.mercator = getProjectionByName('spherical mercator')

    def renderTile(self, width, height, srs, coord):
        """
        """
        if self.mapnik is None:
            self.mapnik = mapnik.Map(0, 0)
            mapnik.load_map(self.mapnik, str(self.mapfile))

        # buffer as fraction of tile size
        buffer = float(self.buffer) / 256

        nw = self.layer.projection.coordinateLocation(coord.left(buffer).up(buffer))
        se = self.layer.projection.coordinateLocation(coord.right(1 + buffer).down(1 + buffer))
        ul = self.mercator.locationProj(nw)
        lr = self.mercator.locationProj(se)

        self.mapnik.width = width + 2 * self.buffer
        self.mapnik.height = height + 2 * self.buffer
        self.mapnik.zoom_to_box(mapnik.Box2d(ul.x, ul.y, lr.x, lr.y))

        # create grid as same size as map/image
        grid = mapnik.Grid(width + 2 * self.buffer, height + 2 * self.buffer)
        # render a layer to that grid array
        mapnik.render_layer(self.mapnik, grid, layer=self.layer_index, fields=self.fields)
        # extract a gridview excluding the buffer
        grid_view = grid.view(self.buffer, self.buffer, width, height)
        # then encode the grid array as utf, resample to 1/scale the size, and dump features
        grid_utf = grid_view.encode('utf', resolution=self.scale, add_features=True)

        if self.wrapper is None:
            return SaveableResponse(json.dumps(grid_utf))
        else:
            return SaveableResponse(self.wrapper + '(' + json.dumps(grid_utf) + ')')

    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.

            This only accepts "json".
        """
        if extension.lower() != 'json':
            raise KnownUnknown('MapnikGrid only makes .json tiles, not "%s"' % extension)

        return 'application/json; charset=utf-8', 'JSON'

class SaveableResponse:
    """ Wrapper class for JSON response that makes it behave like a PIL.Image object.

        TileStache.getTile() expects to be able to save one of these to a buffer.
    """
    def __init__(self, content):
        self.content = content

    def save(self, out, format):
        if format != 'JSON':
            raise KnownUnknown('MapnikGrid only saves .json tiles, not "%s"' % format)

        out.write(self.content)

########NEW FILE########
__FILENAME__ = MirrorOSM
""" Populate an OSM rendering database using tiled data requests.

This provider is unusual in that requests for tiles have the side effect of
running osm2pgsql to populate a PostGIS database of OSM data from a remote API
source. Returned tiles are just text confirmations that the process has been
successful, while the stored data is expected to be used in other providers
to render OSM data. It would be normal to use this provider outside the regular
confines of a web server, perhaps with a call to tilestache-seed.py governed
by a cron job or some other out-of-band process.

MirrorOSM is made tenable by MapQuest's hosting of the XAPI service:
  http://open.mapquestapi.com/xapi/

Osm2pgsql is an external utility:
  http://wiki.openstreetmap.org/wiki/Osm2pgsql

Example configuration:

  "mirror-osm":
  {
    "provider":
    {
      "class": "TileStache.Goodies.Providers.MirrorOSM:Provider",
      "kwargs":
      {
        "username": "osm",
        "database": "planet",
        "api_base": "http://open.mapquestapi.com/xapi/"
      }
    }
  }

Provider parameters:

  database:
    Required Postgres database name.
  
  username:
    Required Postgres user name.
  
  password:
    Optional Postgres password.
  
  hostname:
    Optional Postgres host name.
  
  table_prefix:
    Optional table prefix for osm2pgsql. Defaults to "mirrorosm" if omitted.
    Four tables will be created with this prefix: <prefix>_point, <prefix>_line,
    <prefix>_polygon, and <prefix>_roads. Must result in valid table names!
  
  api_base:
    Optional OSM API base URL. Because we don't want to overtax the main OSM
    API, this defaults to MapQuest's XAPI, "http://open.mapquestapi.com/xapi/".
    The trailing slash must be included, up to but not including the "api/0.6"
    portion of a URL. If you're careful to limit your usage, the primary
    OSM API can be specified with "http://api.openstreetmap.org/".
  
  osm2pgsql:
    Optional filesystem path to osm2pgsql, just in case it's someplace outside
    /usr/bin or /usr/local/bin. Defaults to "osm2pgsql --utf8-sanitize".
    Additional arguments such as "--keep-coastlines" can be added to this string,
    e.g. "/home/user/bin/osm2pgsql --keep-coastlines --utf8-sanitize".
"""
from sys import stderr
from os import write, close, unlink
from tempfile import mkstemp
from subprocess import Popen, PIPE
from httplib import HTTPConnection
from os.path import basename, join
from StringIO import StringIO
from datetime import datetime
from urlparse import urlparse
from base64 import b16encode
from urllib import urlopen
from gzip import GzipFile
from time import time

from TileStache.Core import KnownUnknown, NoTileLeftBehind
from TileStache.Geography import getProjectionByName

try:
    from psycopg2 import connect as _connect, ProgrammingError
except ImportError:
    # well it won't work but we can still make the documentation.
    pass

try:
    from PIL import Image
    from PIL.ImageDraw import ImageDraw
except ImportError:
    # On some systems, PIL.Image is known as Image.
    import Image
    from ImageDraw import ImageDraw

_thumbs_up_bytes = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x03\x00\x00\x00\x9d\xb7\x81\xec\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x00\x0fPLTEy\xb3yn\xa2n\x91\xd6\x91\x85\xc5\x85\x9d\xe8\x9d\xfd\'\x17\xea\x00\x00\x01\x93IDATx\xda\xec\xd6A\x8e\xc3 \x0c\x05P\xf3\xcd\xfd\xcf<\t4\x80\x8d\r\xa6YU\x1aoZE\xe2\xf5\x03.\x84\xf2T`\xe4x\xd1\xfc\x88\x19x\x03\x80\xf0\x0e\xe0;\x01\xde\x01\xfc\x1a8\x10\x1c\xe0\xaa\xb7\x00\xe1k\x80*\x10\x14\xacm\xe4\x13\xc1j\xa4\'BH0\x80\x1e!"\x18\xc0\x99`\x01\xcf$B{A\xf6Sn\x85\xaf\x00\xc4\x05\xca\xbb\x08\x9b\x9et\x00\x0e\x0b\x0e0\xcea\xddR\x11`)\xb8\x80\x8c\xe0\x0b\xee\x1aha\x0b\xa0\x1d"\xd7\x81\xc6S\x11\xaf\x81+r\xf9Msp\x15\x96\x00\xea\xf0{\xbcO\xac\x80q\xb8K\xc0\x07\xa0\xc6\xe3 \x02\xf5]\xc7V\x80;\x05V\t\xdcu\x00\xa7\xab\xee\x19?{F\xe3m\x12\x10\x98\xcaxJ\x15\xe2\xd6\x07\x1c\x8cp\x0b\xfd\xb8\xa1\x84\xa7\x0f\xb8\xa4\x8aE\x18z\xb4\x01\xd3\x0cb@O@3\x80\x05@\xb5\xae\xef\xb9\x01\xb0\xca\x02\xea">\xb5\x01\xb0\x01\x12\xf5m\x04\x82\x84\x00\xda6\xc2\x05`\xf7\xc1\x07@\xeb\x83\x85\x00\x15\xa0\x03)\xe5\x01\xe0( f0t""\x11@"\x00\x82\x00\xc4\x0c\x86\xcaQ\x00\xe2\xcf\xd8\x8a\xe3\xc0\xc7\x00\xe9\x00}\x11\x89\x03\x80\x0c@\xeaX\x0fLB\x06\x80\xbcX\x10\xd8\x889\xc0x3\x05\xdayZ\x81\x10 \xdaXn\x81\x04\xecnVm\xac\x03\x88\xcb\x95x\xfb7P+\xa8\x00\xefX\xeb\xad\xabWP_\xef\xce\xc1|\x7f\xcf\x94\xac\t\xe8\xf7\x031\xba|t\xdc\x9c\x80\xfb\x82a\xdda\xe6\xf8\x03\xa0\x04\xe4\xb2\x12\x9c\xbf\x04\x0e\xde\x91\xfe\x81\xdf\x02\xfe\x04\x18\x00\\_2;\x7fBc\xdd\x00\x00\x00\x00IEND\xaeB`\x82'
_thumbs_up_color = 0x9d, 0xe8, 0x9d

_thumbs_down_bytes = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x03\x00\x00\x00\x9d\xb7\x81\xec\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x00\x0fPLTE\xc4\x8c\x8c\xb1~~\xeb\xa7\xa7\xd8\x9a\x9a\xfe\xb5\xb5\xc9\xe5\xcd\n\x00\x00\x01\x8aIDATx\xda\xec\x97\xd1\xb2\x84 \x0cCc\xe2\xff\x7f\xf3U\x14\x04,P\xf0ign\x1fw&\xc7\xa4\xad.`\xffX\xf8\x07\xfc"\x80\x14\xb8\x068\x94\xd8\xaeb\x1f\xc0T\xf9\xaf[^-\x80\xf4\x88\x15*QX\x00`\x03r\xfd\xc3\xb8*\xd9\xbfJ\x16\xa0\xd6\xe7\x08@*\x08\xf4\x01\n\x13\xb2\xda\x80\xbc\xcb\xb4*\x8fa\x84\x18\x03r\x86\x11\xc2\x05H\x08c\x12p\xe9m\x02\x0b\x00\xd5\x05\xdc\x88\xb7\x85\x08 \x06\xfa\x00 ^\x16\x90F\xa8\xf1\xf3\xc5\xb7\x05tv\xc0\x98C\xb9\xd0\x9b\x1b\x90\xe6xf@\xac\x90\x01\x9e\x1eV\xdb\xf8\x10\x90M\xc1\x0b(-\xf8"\xa8\x05\xc0\x91\x01\xc3)\xaa\xaa\x02\xa0\x08P\x0b u\x01x\x00^\xfd\x91\x01\x19\xa1\xef@2\x01\x9b\xb2&t\x00R\x13\xf0\xe4\xd1\xd3D\xf9\xf4g\x13\x0c\xc0~~\xf4V\x00@ZD9\x01w\x84k\x91\xa2\x833A\x05h??\xbe\x8ag\xea\xb8\x89\x82O\xcf\xf0\xde+\xff\xcf\xba?l5\xc0\xd6\xb7\xff\x9dQE\xf0\xebS\x84\xc2C\xd3\x7f\xfb|\x10\x9a\xaa~\xf5\x0f\x18\x0c&\x8e\xe6\xb4\x9e\x0f\xce\x9cP\xa8\xda\x0e4w\xc4a\x99\x08\xc0\xec\x19\xa9\xd6\xf3#\x80\xb3\xa74\xc2\x93\xdf\x0b\xd0\xc29q\xbc@\x831\xc2\xabo\x00\xfcz\x1b\x90\xd6\xa8\xdb\xbe6 \xea\xe1\xd0[\x00\xce\xe8-\xc0m\xc0\xa7\xb7\x00\xc9\xc0\xe2}\x81\x98\xd1\x1b\x80\x98\x80\xcb\x00\xdf\xfc\xfb\x80\xea\xae\xb1\x02\xf8p\xe9\xba\x0e+_nmS\x06\xccM\xfc\n\xd8g\xf4\xfb\x9f\x00\x03\x00\x0eA2jW\xf7\x1bk\x00\x00\x00\x00IEND\xaeB`\x82'
_thumbs_down_color = 0xfe, 0xb5, 0xb5

def coordinate_latlon_bbox(coord, projection):
    """ Return an (xmin, ymin, xmax, ymax) bounding box for a projected tile.
    """
    ul = projection.coordinateLocation(coord)
    ur = projection.coordinateLocation(coord.right())
    ll = projection.coordinateLocation(coord.down())
    lr = projection.coordinateLocation(coord.down().right())
    
    n = max(ul.lat, ur.lat, ll.lat, lr.lat)
    s = min(ul.lat, ur.lat, ll.lat, lr.lat)
    e = max(ul.lon, ur.lon, ll.lon, lr.lon)
    w = min(ul.lon, ur.lon, ll.lon, lr.lon)
    
    return w, s, e, n

def download_api_data(filename, coord, api_base, projection):
    """ Download API data for a tile to a named file, return size in kilobytes.
    """
    s, host, path, p, q, f = urlparse(api_base)
    bbox = coordinate_latlon_bbox(coord, projection)
    path = join(path, 'api/0.6/map?bbox=%.6f,%.6f,%.6f,%.6f' % bbox)
    
    conn = HTTPConnection(host)
    conn.request('GET', path, headers={'Accept-Encoding': 'compress, gzip'})
    resp = conn.getresponse()
    
    assert resp.status == 200, (resp.status, resp.read())
    
    if resp.getheader('Content-Encoding') == 'gzip':
        disk = open(filename, 'w')
    else:
        raise Exception((host, path))
        disk = GzipFile(filename, 'w')

    bytes = resp.read()
    disk.write(bytes)
    disk.close()
    
    return len(bytes) / 1024.

def prepare_data(filename, tmp_prefix, dbargs, osm2pgsql, projection):
    """ Stage OSM data into a temporary set of tables using osm2pgsql.
    """
    args = osm2pgsql.split() + ['--create', '--merc', '--prefix', tmp_prefix]
    
    for (flag, key) in [('-d', 'database'), ('-U', 'user'), ('-W', 'password'), ('-H', 'host')]:
        if key in dbargs:
            args += flag, dbargs[key]
    
    args += [filename]

    create = Popen(args, stderr=PIPE, stdout=PIPE)
    create.wait()
    
    assert create.returncode == 0, \
        "It's important that osm2pgsql actually worked." + create.stderr.read()

def create_tables(db, prefix, tmp_prefix):
    """ Create permanent tables for OSM data. No-op if they already exist.
    """
    for table in ('point', 'line', 'roads', 'polygon'):
        db.execute('BEGIN')
        
        try:
            db.execute('CREATE TABLE %(prefix)s_%(table)s ( LIKE %(tmp_prefix)s_%(table)s )' % locals())

        except ProgrammingError, e:
            db.execute('ROLLBACK')

            if e.pgcode != '42P07':
                # 42P07 is a duplicate table, the only error we expect.
                raise

        else:
            db.execute("""INSERT INTO geometry_columns
                          (f_table_catalog, f_table_schema, f_table_name, f_geometry_column, coord_dimension, srid, type)
                          SELECT f_table_catalog, f_table_schema, '%(prefix)s_%(table)s', f_geometry_column, coord_dimension, srid, type
                          FROM geometry_columns WHERE f_table_name = '%(tmp_prefix)s_%(table)s'""" \
                        % locals())

            db.execute('COMMIT')

def populate_tables(db, prefix, tmp_prefix, bounds):
    """ Move prepared OSM data from temporary to permanent tables.
    
        Replace existing data and work within a single transaction.
    """
    bbox = 'ST_SetSRID(ST_MakeBox2D(ST_MakePoint(%.6f, %.6f), ST_MakePoint(%.6f, %.6f)), 900913)' % bounds
    
    db.execute('BEGIN')
    
    for table in ('point', 'line', 'roads', 'polygon'):
        db.execute('DELETE FROM %(prefix)s_%(table)s WHERE ST_Intersects(way, %(bbox)s)' % locals())

        db.execute("""INSERT INTO %(prefix)s_%(table)s
                      SELECT * FROM %(tmp_prefix)s_%(table)s
                      WHERE ST_Intersects(way, %(bbox)s)""" \
                    % locals())
    
    db.execute('COMMIT')

def clean_up_tables(db, tmp_prefix):
    """ Drop all temporary tables created by prepare_data().
    """
    db.execute('BEGIN')
    
    for table in ('point', 'line', 'roads', 'polygon'):
        db.execute('DROP TABLE %(tmp_prefix)s_%(table)s' % locals())
        db.execute("DELETE FROM geometry_columns WHERE f_table_name = '%(tmp_prefix)s_%(table)s'" % locals())
    
    db.execute('COMMIT')

class ConfirmationResponse:
    """ Wrapper class for confirmation responses.
    
        TileStache.getTile() expects to be able to save one of these to a buffer.
    """
    def __init__(self, coord, content, success):
        self.coord = coord
        self.content = content
        self.success = success
        
    def do_I_have_to_draw_you_a_picture(self):
        """ Return a little thumbs-up / thumbs-down image with text in it.
        """
        if self.success:
            bytes, color = _thumbs_up_bytes, _thumbs_up_color
        else:
            bytes, color = _thumbs_down_bytes, _thumbs_down_color
        
        thumb = Image.open(StringIO(bytes))
        image = Image.new('RGB', (256, 256), color)
        image.paste(thumb.resize((128, 128)), (64, 80))
        
        mapnik_url = 'http://tile.openstreetmap.org/%(zoom)d/%(column)d/%(row)d.png' % self.coord.__dict__
        mapnik_img = Image.open(StringIO(urlopen(mapnik_url).read()))
        mapnik_img = mapnik_img.convert('L').convert('RGB')
        image = Image.blend(image, mapnik_img, .15)
        
        draw = ImageDraw(image)
        margin, leading = 8, 12
        x, y = margin, margin
        
        for word in self.content.split():
            w, h = draw.textsize(word)
            
            if x > margin and x + w > 250:
                x, y = margin, y + leading
            
            draw.text((x, y), word, fill=(0x33, 0x33, 0x33))
            x += draw.textsize(word + ' ')[0]
        
        return image
    
    def save(self, out, format):
        if format == 'TXT':
            out.write(self.content)
        
        elif format == 'PNG':
            image = self.do_I_have_to_draw_you_a_picture()
            image.save(out, format)

        else:
            raise KnownUnknown('MirrorOSM only saves .txt and .png tiles, not "%s"' % format)

class Provider:
    """
    """
    def __init__(self, layer, database, username, password=None, hostname=None, table_prefix='mirrorosm', api_base='http://open.mapquestapi.com/xapi/', osm2pgsql='osm2pgsql --utf8-sanitize'):
        """
        """
        self.layer = layer
        self.dbkwargs = {'database': database}
        
        self.api_base = api_base
        self.prefix = table_prefix
        self.osm2pgsql = osm2pgsql
        
        if hostname:
            self.dbkwargs['host'] = hostname
        
        if username:
            self.dbkwargs['user'] = username
        
        if password:
            self.dbkwargs['password'] = password

    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.
        
            This only accepts "txt".
        """
        if extension.lower() == 'txt':
            return 'text/plain', 'TXT'
        
        elif extension.lower() == 'png':
            return 'image/png', 'PNG'
        
        else:
            raise KnownUnknown('MirrorOSM only makes .txt and .png tiles, not "%s"' % extension)

    def renderTile(self, width, height, srs, coord):
        """ Render a single tile, return a ConfirmationResponse instance.
        """
        if coord.zoom < 12:
            raise KnownUnknown('MirrorOSM provider only handles data at zoom 12 or higher, not %d.' % coord.zoom)
        
        start = time()
        garbage = []
        
        handle, filename = mkstemp(prefix='mirrorosm-', suffix='.tablename')
        tmp_prefix = 'mirrorosm_' + b16encode(basename(filename)[10:-10]).lower()
        garbage.append(filename)
        close(handle)
        
        handle, filename = mkstemp(prefix='mirrorosm-', suffix='.osm.gz')
        garbage.append(filename)
        close(handle)
        
        try:
            length = download_api_data(filename, coord, self.api_base, self.layer.projection)
            prepare_data(filename, tmp_prefix, self.dbkwargs, self.osm2pgsql, self.layer.projection)
    
            db = _connect(**self.dbkwargs).cursor()
            
            ul = self.layer.projection.coordinateProj(coord)
            lr = self.layer.projection.coordinateProj(coord.down().right())
            
            create_tables(db, self.prefix, tmp_prefix)
            populate_tables(db, self.prefix, tmp_prefix, (ul.x, ul.y, lr.x, lr.y))
            clean_up_tables(db, tmp_prefix)
            
            db.close()
            
            message = 'Retrieved %dK of OpenStreetMap data for tile %d/%d/%d in %.2fsec from %s (%s).\n' \
                    % (length, coord.zoom, coord.column, coord.row,
                       (time() - start), self.api_base, datetime.now())

            return ConfirmationResponse(coord, message, True)
        
        except Exception, e:
            message = 'Error in tile %d/%d/%d: %s' % (coord.zoom, coord.column, coord.row, e)
            
            raise NoTileLeftBehind(ConfirmationResponse(coord, message, False))
        
        finally:
            for filename in garbage:
                unlink(filename)

########NEW FILE########
__FILENAME__ = Monkeycache
""" Monkeycache is a tile provider that reads data from an existing cache.

    Normally, TileStache creates new tiles at request-time and saves them to a
    cache for later visitors. Monkeycache supports a different workflow, where
    a cache is seeded ahead of time, and then only existing tiles are served
    from this cache.
    
    For example, you might have a TileStache configuration with a Mapnik
    provider, which requires PostGIS and other software to be installed on your
    system. Monkeycache would allow you to seed that cache into a directory of
    files or an MBTiles file on a system with a fast processor and I/O, and then
    serve the contents of the cache from another system with a faster network
    connection but no Mapnik or PostGIS.
    
    Two sample configurations:

    {
      "cache": {"name": "Disk", "path": "/var/cache"},
      "layers": 
      {
        "expensive-layer":
        {
          "provider": {"name": "Mapnik", "mapfile": "style.xml"}
        }
      }
    }
    
    {
      "cache": {"name": "Test"},
      "layers": 
      {
        "cheap-layer":
        {
          "provider":
          {
            "class": "TileStache.Goodies.Providers.Monkeycache:Provider",
            "kwargs":
            {
              "layer_name": "expensive-layer",
              "cache_config": {"name": "Disk", "path": "/var/cache"},
              "format": "PNG"
            }
          }
        }
      }
    }
"""

from TileStache.Config import buildConfiguration
from TileStache.Core import KnownUnknown

class CacheResponse:
    """ Wrapper class for Cache response that makes it behave like a PIL.Image object.
    
        TileStache.getTile() expects to be able to save one of these to a buffer.
        
        Constructor arguments:
        - body: Raw data pulled from cache.
        - format: File format to check against.
    """
    def __init__(self, body, format):
        self.body = body
        self.format = format
    
    def save(self, out, format):
        if format != self.format:
            raise KnownUnknown('Monkeycache only knows how to make %s tiles, not %s' % (self.format, format))
        
        out.write(self.body)

class Provider:
    """ Monkeycache Provider with source_layer, source_cache and tile_format attributes.
    
        Source_layer is an instance of TileStache.Core.Layer.
        Source_cache is a valid TileStache Cache provider.
        Tile_format is a string.
    """
    def __init__(self, layer, cache_config, layer_name, format='PNG'):
        """ Initialize the Monkeycache Provider.
        
            Cache_config is a complete cache configuration dictionary that you
            might use in a TileStache setup (http://tilestache.org/doc/#caches).
            This is where Monkeycache will look for already-rendered tiles.
            
            Layer_name is the name of a layer saved in that cache.
        
            Format should match the second return value of your original
            layer's getTypeByExtention() method, e.g. "PNG", "JPEG", or for
            the Vector provider "GeoJSON" and others. This might not necessarily
            match the file name extension, though common cases like "jpg"/"JPEG"
            are accounted for.
        """
        fake_layer_dict = {'provider': {'name': 'Proxy', 'url': 'http://localhost/{Z}/{X}/{Y}.png'}}
        fake_config_dict = {'cache': cache_config, 'layers': {layer_name: fake_layer_dict}}
        fake_config = buildConfiguration(fake_config_dict, layer.config.dirpath)
        
        self.source_layer = fake_config.layers[layer_name]
        self.source_cache = fake_config.cache
        
        formats = dict(png='PNG', jpg='JPEG', jpeg='JPEG')
        self.tile_format = formats.get(format.lower(), format)

    def renderTile(self, width, height, srs, coord):
        """ Pull a single tile from self.source_cache.
        """
        body = self.source_cache.read(self.source_layer, coord, self.tile_format)
        return ResponseWrapper(body, self.tile_format)

########NEW FILE########
__FILENAME__ = PostGeoJSON
""" Provider that returns GeoJSON data responses from PostGIS queries.

Note:

The built-in TileStache Vector provider (new in version 1.9.0) offers a more
complete method of generating vector tiles, and supports many kinds of data
sources not avilable in PostGeoJSON such as shapefiles. PostGeoJSON will
continue to be provided and supported in TileStache, but future development
of vector support will be contentrated on the mainline Vector provider, not
this one.

More information:
  http://tilestache.org/doc/TileStache.Vector.html

Anyway.

This is an example of a provider that does not return an image, but rather
queries a database for raw data and replies with a string of GeoJSON. For
example, it's possible to retrieve data for locations of OpenStreetMap points
of interest based on a query with a bounding box intersection.

Read more about the GeoJSON spec at: http://geojson.org/geojson-spec.html

Many Polymaps (http://polymaps.org) examples use GeoJSON vector data tiles,
which can be effectively created using this provider.

Keyword arguments:

  dsn:
    Database connection string suitable for use in psycopg2.connect().
    See http://initd.org/psycopg/docs/module.html#psycopg2.connect for more.
  
  query:
    PostGIS query with a "!bbox!" placeholder for the tile bounding box.
    Note that the table *must* use the web spherical mercaotr projection
    900913. Query should return an id column, a geometry column, and other
    columns to be placed in the GeoJSON "properties" dictionary.
    See below for more on 900913.
  
  clipping:
    Boolean flag for optionally clipping the output geometries to the bounds
    of the enclosing tile. Defaults to fales. This results in incomplete
    geometries, dramatically smaller file sizes, and improves performance
    and compatibility with Polymaps (http://polymaps.org).
  
  id_column:
    Name of id column in output, detaults to "id". This determines which query
    result column is placed in the GeoJSON "id" field.
  
  geometry_column:
    Name of geometry column in output, defaults to "geometry". This determines
    which query result column is reprojected to lat/lon and output as a list
    of geographic coordinates.
  
  indent:
    Number of spaces to indent output GeoJSON response. Defaults to 2.
    Skip all indenting with a value of zero.
  
  precision:
    Number of decimal places of precision for output geometry. Defaults to 6.
    Default should be appropriate for almost all street-mapping situations.
    A smaller value can help cut down on output file size for lower-zoom maps.

Example TileStache provider configuration:

  "points-of-interest":
  {
    "provider":
    {
      "class": "TileStache.Goodies.Providers.PostGeoJSON.Provider",
      "kwargs":
      {
        "dsn": "dbname=geodata user=postgres",
        "query": "SELECT osm_id, name, way FROM planet_osm_point WHERE way && !bbox! AND name IS NOT NULL",
        "id_column": "osm_id", "geometry_column": "way",
        "indent": 2
      }
    }
  }

Caveats:

Currently only databases in the 900913 (google) projection are usable,
though this is the default setting for OpenStreetMap imports from osm2pgsql.
The "!bbox!" query placeholder (see example below) must be lowercase, and
expands to:
    
    ST_SetSRID(ST_MakeBox2D(ST_MakePoint(ulx, uly), ST_MakePoint(lrx, lry)), 900913)
    
You must support the "900913" SRID in your PostGIS database for now.
For populating the internal PostGIS spatial_ref_sys table of projections,
this seems to work:

  INSERT INTO spatial_ref_sys
    (srid, auth_name, auth_srid, srtext, proj4text)
    VALUES
    (
      900913, 'spatialreference.org', 900913,
      'PROJCS["Popular Visualisation CRS / Mercator",GEOGCS["Popular Visualisation CRS",DATUM["Popular_Visualisation_Datum",SPHEROID["Popular Visualisation Sphere",6378137,0,AUTHORITY["EPSG","7059"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6055"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4055"]],UNIT["metre",1,AUTHORITY["EPSG","9001"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],AUTHORITY["EPSG","3785"],AXIS["X",EAST],AXIS["Y",NORTH]]',
      '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over'
    );
"""

from re import compile
from copy import copy as _copy
from binascii import unhexlify as _unhexlify

try:
    from json import JSONEncoder
except ImportError:
    from simplejson import JSONEncoder

try:
    from shapely.wkb import loads as _loadshape
    from shapely.geometry import Polygon
    from shapely.geos import TopologicalError
    from psycopg2 import connect as _connect
    from psycopg2.extras import RealDictCursor
except ImportError:
    # At least it should be possible to build the documentation.
    pass


from TileStache.Core import KnownUnknown
from TileStache.Geography import getProjectionByName

def row2feature(row, id_field, geometry_field):
    """ Convert a database row dict to a feature dict.
    """
    feature = {'type': 'Feature', 'properties': _copy(row)}

    geometry = feature['properties'].pop(geometry_field)
    feature['geometry'] = _loadshape(_unhexlify(geometry))
    feature['id'] = feature['properties'].pop(id_field)
    
    return feature

def _p2p(xy, projection):
    """ Convert a simple (x, y) coordinate to a (lon, lat) position.
    """
    loc = projection.projLocation(_Point(*xy))
    return loc.lon, loc.lat

class _InvisibleBike(Exception): pass

def shape2geometry(shape, projection, clip):
    """ Convert a Shapely geometry object to a GeoJSON-suitable geometry dict.
    """
    if clip:
        try:
            shape = shape.intersection(clip)
        except TopologicalError:
            raise _InvisibleBike("Clipping shape resulted in a topological error")
        
        if shape.is_empty:
            raise _InvisibleBike("Clipping shape resulted in a null geometry")
    
    geom = shape.__geo_interface__
    
    if geom['type'] == 'Point':
        geom['coordinates'] = _p2p(geom['coordinates'], projection)
    
    elif geom['type'] in ('MultiPoint', 'LineString'):
        geom['coordinates'] = [_p2p(c, projection)
                               for c in geom['coordinates']]
    
    elif geom['type'] in ('MultiLineString', 'Polygon'):
        geom['coordinates'] = [[_p2p(c, projection)
                                for c in cs]
                               for cs in geom['coordinates']]
    
    elif geom['type'] == 'MultiPolygon':
        geom['coordinates'] = [[[_p2p(c, projection)
                                 for c in cs]
                                for cs in ccs]
                               for ccs in geom['coordinates']]
    
    return geom

class _Point:
    """ Local duck for (x, y) points.
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

class SaveableResponse:
    """ Wrapper class for JSON response that makes it behave like a PIL.Image object.
    
        TileStache.getTile() expects to be able to save one of these to a buffer.
    """
    def __init__(self, content, indent=2, precision=2):
        self.content = content
        self.indent = indent
        self.precision = precision

    def save(self, out, format):
        if format != 'JSON':
            raise KnownUnknown('PostGeoJSON only saves .json tiles, not "%s"' % format)

        indent = None
        
        if int(self.indent) > 0:
            indent = self.indent
        
        encoded = JSONEncoder(indent=indent).iterencode(self.content)
        float_pat = compile(r'^-?\d+\.\d+$')

        precision = 6

        if int(self.precision) > 0:
            precision = self.precision

        format = '%.' + str(precision) +  'f'

        for atom in encoded:
            if float_pat.match(atom):
                out.write(format % float(atom))
            else:
                out.write(atom)

class Provider:
    """
    """
    def __init__(self, layer, dsn, query, clipping=False, id_column='id', geometry_column='geometry', indent=2, precision=6):
        self.layer = layer
        self.dbdsn = dsn
        self.query = query
        self.mercator = getProjectionByName('spherical mercator')
        self.geometry_field = geometry_column
        self.id_field = id_column
        self.indent = indent
        self.precision = precision
        self.clipping = clipping

    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.
        
            This only accepts "json".
        """
        if extension.lower() != 'json':
            raise KnownUnknown('PostGeoJSON only makes .json tiles, not "%s"' % extension)
    
        return 'application/json', 'JSON'

    def renderTile(self, width, height, srs, coord):
        """ Render a single tile, return a SaveableResponse instance.
        """
        nw = self.layer.projection.coordinateLocation(coord)
        se = self.layer.projection.coordinateLocation(coord.right().down())

        ul = self.mercator.locationProj(nw)
        lr = self.mercator.locationProj(se)
        
        bbox = 'ST_SetSRID(ST_MakeBox2D(ST_MakePoint(%.6f, %.6f), ST_MakePoint(%.6f, %.6f)), 900913)' % (ul.x, ul.y, lr.x, lr.y)
        clip = self.clipping and Polygon([(ul.x, ul.y), (lr.x, ul.y), (lr.x, lr.y), (ul.x, lr.y)]) or None

        db = _connect(self.dbdsn).cursor(cursor_factory=RealDictCursor)

        db.execute(self.query.replace('!bbox!', bbox))
        rows = db.fetchall()
        
        db.close()
        
        response = {'type': 'FeatureCollection', 'features': []}
        
        for row in rows:
            feature = row2feature(row, self.id_field, self.geometry_field)
            
            try:
                geom = shape2geometry(feature['geometry'], self.mercator, clip)
            except _InvisibleBike:
                # don't output this geometry because it's empty
                pass
            else:
                feature['geometry'] = geom
                response['features'].append(feature)
    
        return SaveableResponse(response, self.indent, self.precision)

########NEW FILE########
__FILENAME__ = SolrGeoJSON
""" Provider that returns GeoJSON data responses from Solr spatial queries.

This is an example of a provider that does not return an image, but rather
queries a Solr instance for raw data and replies with a string of GeoJSON.

Read more about the GeoJSON spec at: http://geojson.org/geojson-spec.html

Caveats:

Example TileStache provider configuration:

"solr": {
    "provider": {"class": "TileStache.Goodies.Providers.SolrGeoJSON.Provider",
                 "kwargs": {
                    "solr_endpoint": "http://localhost:8983/solr/example",
                    "solr_query": "*:*",
                 }}
}

The following optional parameters are also supported:

latitude_field: The name of the latitude field associated with your query parser;
the default is 'latitude'

longitude_field: The name of the longitude field associated with your query
parser, default is 'longitude

response_fields: A comma-separated list of fields with which to filter the Solr
response; the default is '' (or: include all fields)

id_field: The name name of your Solr instance's unique ID field; the default is ''.

By default queries are scoped to the bounding box of a given tile. Radial queries
are also supported if you supply a 'radius' kwarg to your provider and have installed
the JTeam spatial plugin: http://www.jteam.nl/news/spatialsolr.html.

For example:

"solr": {
    "provider": {"class": "TileStache.Goodies.Providers.SolrGeoJSON.Provider",
                 "kwargs": {
                    "solr_endpoint": "http://localhost:8983/solr/example",
                    "solr_query": 'foo:bar',
                    "radius": "1",
                 }}
}

Radial queries are begin at the center of the tile being rendered and distances are
measured in kilometers.

The following optional parameters are also supported for radial queries:

query_parser: The name of the Solr query parser associated with your spatial
plugin; the default is 'spatial'.

"""

from math import log, tan, pi, atan, pow, e

from re import compile
from json import JSONEncoder

from TileStache.Core import KnownUnknown
from TileStache.Geography import getProjectionByName

try:
    import pysolr
except ImportError:
    # well it won't work but we can still make the documentation.
    pass

class SaveableResponse:
    """ Wrapper class for JSON response that makes it behave like a PIL.Image object.

        TileStache.getTile() expects to be able to save one of these to a buffer.
    """
    def __init__(self, content):
        self.content = content

    def save(self, out, format):
        if format != 'JSON':
            raise KnownUnknown('SolrGeoJSON only saves .json tiles, not "%s"' % format)

        encoded = JSONEncoder(indent=2).iterencode(self.content)
        float_pat = compile(r'^-?\d+\.\d+$')

        for atom in encoded:
            if float_pat.match(atom):
                out.write('%.6f' % float(atom))
            else:
                out.write(atom)

class Provider:
    """
    """
    def __init__(self, layer, solr_endpoint, solr_query, **kwargs):
        self.projection = getProjectionByName('spherical mercator')
        self.layer = layer

        self.endpoint = str(solr_endpoint)
        self.query = solr_query

        self.solr = pysolr.Solr(self.endpoint)

        self.query_parser = kwargs.get('query_parser', 'spatial')
        self.lat_field = kwargs.get('latitude_column', 'latitude')
        self.lon_field = kwargs.get('longitude_column', 'longitude')
        self.id_field = kwargs.get('id_column', '')

        self.solr_radius = kwargs.get('radius', None)
        self.solr_fields = kwargs.get('response_fields', None)

    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.

            This only accepts "json".
        """
        if extension.lower() != 'json':
            raise KnownUnknown('PostGeoJSON only makes .json tiles, not "%s"' % extension)

        return 'application/json', 'JSON'

    def unproject(self, x, y):
        x, y = x / 6378137, y / 6378137 # dimensions of the earth
        lat, lon = 2 * atan(pow(e, y)) - .5 * pi, x # basic spherical mercator
        lat, lon = lat * 180/pi, lon * 180/pi # radians to degrees
        return lat, lon

    def renderTile(self, width, height, srs, coord):
        """ Render a single tile, return a SaveableResponse instance.
        """

        minx, miny, maxx, maxy = self.layer.envelope(coord)

        y = miny + ((maxy - miny) / 2)
        x = minx + ((maxx - minx) / 2)

        sw_lat, sw_lon = self.unproject(minx, miny)
        ne_lat, ne_lon = self.unproject(maxx, maxy)
        center_lat, center_lon = self.unproject(x, y)

        bbox = "%s:[%s TO %s] AND %s:[%s TO %s]" % (self.lon_field, sw_lon, ne_lon, self.lat_field, sw_lat, ne_lat)
        query = bbox

        # for example:
        # {!spatial lat=51.500152 long=-0.126236 radius=10 calc=arc unit=km}*:*

        if self.solr_radius:
            query = "{!%s lat=%s long=%s radius=%s calc=arc unit=km}%s" % (self.query_parser, center_lat, center_lon, self.solr_radius, bbox)

        kwargs = {}

        if self.query != '*:*':
            kwargs['fq'] = self.query

        kwargs['omitHeader'] = 'true'
        rsp_fields = []

        if self.solr_fields:

            rsp_fields = self.solr_fields.split(',')

            if not self.lat_field in rsp_fields:
                rsp_fields.append(self.lat_field)

            if not self.lon_field in rsp_fields:
                rsp_fields.append(self.lon_field)

            kwargs['fl'] = ','.join(rsp_fields)

        response = {'type': 'FeatureCollection', 'features': []}

        total = None
        start = 0
        rows = 1000

        while not total or start < total:

            kwargs['start'] = start
            kwargs['rows'] = rows

            rsp = self.solr.search(query, **kwargs)

            if not total:
                total = rsp.hits

            if total == 0:
                break

            for row in rsp:

                # hack until I figure out why passing &fl in a JSON
                # context does not actually limit the fields returned

                if len(rsp_fields):
                    for key, ignore in row.items():
                        if not key in rsp_fields:
                            del(row[key])

                row['geometry'] = {
                    'type': 'Point',
                    'coordinates': (row[ self.lon_field ], row[ self.lat_field ])
                    }

                del(row[ self.lat_field ])
                del(row[ self.lon_field ])

                if self.id_field != '':
                    row['id'] = row[ self.id_field ]

                response['features'].append(row)

            start += rows

        return SaveableResponse(response)

# -*- indent-tabs-mode:nil tab-width:4 -*-

########NEW FILE########
__FILENAME__ = TileDataOSM
from sys import stderr
from time import strftime, gmtime
from xml.dom.minidom import getDOMImplementation

from TileStache.Core import KnownUnknown

try:
    from psycopg2 import connect as _connect, ProgrammingError
except ImportError:
    # well it won't work but we can still make the documentation.
    pass

class Node:
    def __init__(self, id, version, timestamp, uid, user, changeset, lat, lon):
        self.id = id
        self.version = version
        self.timestamp = timestamp
        self.uid = uid
        self.user = user
        self.changeset = changeset
        self.lat = lat
        self.lon = lon
        
        self._tags = {}

    def tag(self, k, v):
        self._tags[k] = v

    def tags(self):
        return sorted(self._tags.items())

class Way:
    def __init__(self, id, version, timestamp, uid, user, changeset):
        self.id = id
        self.version = version
        self.timestamp = timestamp
        self.uid = uid
        self.user = user
        self.changeset = changeset
        
        self._nodes = []
        self._tags = {}

    def node(self, id):
        self._nodes.append(id)

    def nodes(self):
        return self._nodes[:]

    def tag(self, k, v):
        self._tags[k] = v

    def tags(self):
        return sorted(self._tags.items())

def coordinate_bbox(coord, projection):
    """
    """
    ul = projection.coordinateLocation(coord)
    ur = projection.coordinateLocation(coord.right())
    ll = projection.coordinateLocation(coord.down())
    lr = projection.coordinateLocation(coord.down().right())
    
    n = max(ul.lat, ur.lat, ll.lat, lr.lat)
    s = min(ul.lat, ur.lat, ll.lat, lr.lat)
    e = max(ul.lon, ur.lon, ll.lon, lr.lon)
    w = min(ul.lon, ur.lon, ll.lon, lr.lon)
    
    return n, s, e, w

class SaveableResponse:
    """ Wrapper class for XML response that makes it behave like a PIL.Image object.
    
        TileStache.getTile() expects to be able to save one of these to a buffer.
    """
    def __init__(self, nodes, ways):
        self.nodes = nodes
        self.ways = ways
        
    def save(self, out, format):
        if format != 'XML':
            raise KnownUnknown('TileDataOSM only saves .xml tiles, not "%s"' % format)

        imp = getDOMImplementation()
        doc = imp.createDocument(None, 'osm', None)
        
        osm_el = doc.documentElement
        osm_el.setAttribute('version', '0.6')
        osm_el.setAttribute('generator', 'TileDataOSM (TileStache.org)')
        
        for node in self.nodes:
            # <node id="53037501" version="6" timestamp="2010-09-06T23:16:03Z" uid="14293" user="dahveed76" changeset="5703401" lat="37.8024307" lon="-122.2634983"/>
        
            node_el = doc.createElement('node')
            
            node_el.setAttribute('id', '%d' % node.id)
            node_el.setAttribute('version', '%d' % node.version)
            node_el.setAttribute('timestamp', strftime('%Y-%m-%dT%H:%M:%SZ', gmtime(node.timestamp)))
            node_el.setAttribute('uid', '%d' % node.uid)
            node_el.setAttribute('user', node.user.encode('utf-8'))
            node_el.setAttribute('changeset', '%d' % node.changeset)
            node_el.setAttribute('lat', '%.7f' % node.lat)
            node_el.setAttribute('lon', '%.7f' % node.lon)
            
            for (key, value) in node.tags():
                tag_el = doc.createElement('tag')
                
                tag_el.setAttribute('k', key.encode('utf-8'))
                tag_el.setAttribute('v', value.encode('utf-8'))
                
                node_el.appendChild(tag_el)
            
            osm_el.appendChild(node_el)
        
        for way in self.ways:
            # <way id="6332386" version="2" timestamp="2010-03-27T09:42:04Z" uid="20587" user="balrog-kun" changeset="4244079">
        
            way_el = doc.createElement('way')
            
            way_el.setAttribute('id', '%d' % way.id)
            way_el.setAttribute('version', '%d' % way.version)
            way_el.setAttribute('timestamp', strftime('%Y-%m-%dT%H:%M:%SZ', gmtime(way.timestamp)))
            way_el.setAttribute('uid', '%d' % way.uid)
            way_el.setAttribute('user', way.user.encode('utf-8'))
            way_el.setAttribute('changeset', '%d' % way.changeset)
            
            for (node_id) in way.nodes():
                nd_el = doc.createElement('nd')
                nd_el.setAttribute('ref', '%d' % node_id)
                way_el.appendChild(nd_el)
            
            for (key, value) in way.tags():
                tag_el = doc.createElement('tag')
                tag_el.setAttribute('k', key.encode('utf-8'))
                tag_el.setAttribute('v', value.encode('utf-8'))
                way_el.appendChild(tag_el)
            
            osm_el.appendChild(way_el)
        
        out.write(doc.toxml('UTF-8'))

def prepare_database(db, coord, projection):
    """
    """
    db.execute('CREATE TEMPORARY TABLE box_node_list (id bigint PRIMARY KEY) ON COMMIT DROP')
    db.execute('CREATE TEMPORARY TABLE box_way_list (id bigint PRIMARY KEY) ON COMMIT DROP')
    db.execute('CREATE TEMPORARY TABLE box_relation_list (id bigint PRIMARY KEY) ON COMMIT DROP')
    
    n, s, e, w = coordinate_bbox(coord, projection)
    
    bbox = 'ST_SetSRID(ST_MakeBox2D(ST_MakePoint(%.7f, %.7f), ST_MakePoint(%.7f, %.7f)), 4326)' % (w, s, e, n)

    # Collect all node ids inside bounding box.

    db.execute("""INSERT INTO box_node_list
                  SELECT id
                  FROM nodes
                  WHERE (geom && %(bbox)s)""" \
                % locals())

    # Collect all way ids inside bounding box using already selected nodes.

    db.execute("""INSERT INTO box_way_list
                  SELECT wn.way_id
                  FROM way_nodes wn
                  INNER JOIN box_node_list n
                  ON wn.node_id = n.id
                  GROUP BY wn.way_id""")

    # Collect all relation ids containing selected nodes or ways.

    db.execute("""INSERT INTO box_relation_list
                  (
                    SELECT rm.relation_id AS relation_id
                    FROM relation_members rm
                    INNER JOIN box_node_list n
                    ON rm.member_id = n.id
                    WHERE rm.member_type = 'N'
                  UNION
                    SELECT rm.relation_id AS relation_id
                    FROM relation_members rm
                    INNER JOIN box_way_list w
                    ON rm.member_id = w.id
                    WHERE rm.member_type = 'W'
                  )""")

    # Collect parent relations of selected relations.

    db.execute("""INSERT INTO box_relation_list
                  SELECT rm.relation_id AS relation_id
                  FROM relation_members rm
                  INNER JOIN box_relation_list r
                  ON rm.member_id = r.id
                  WHERE rm.member_type = 'R'
                  EXCEPT
                  SELECT id AS relation_id
                  FROM box_relation_list""")

    db.execute('ANALYZE box_node_list')
    db.execute('ANALYZE box_way_list')
    db.execute('ANALYZE box_relation_list')

class Provider:
    """
    """
    
    def __init__(self, layer, database=None, username=None, password=None, hostname=None):
        """
        """
        self.layer = layer
        self.dbkwargs = {}
        
        if hostname:
            self.dbkwargs['host'] = hostname
        
        if username:
            self.dbkwargs['user'] = username
        
        if database:
            self.dbkwargs['database'] = database
        
        if password:
            self.dbkwargs['password'] = password

    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.
        
            This only accepts "xml".
        """
        if extension.lower() != 'xml':
            raise KnownUnknown('TileDataOSM only makes .xml tiles, not "%s"' % extension)
    
        return 'text/xml', 'XML'

    def renderTile(self, width, height, srs, coord):
        """ Render a single tile, return a SaveableResponse instance.
        """
        db = _connect(**self.dbkwargs).cursor()
        
        prepare_database(db, coord, self.layer.projection)
        
        counts = []
        
        # Select core node information

        db.execute("""SELECT n.id, n.version, EXTRACT(epoch FROM n.tstamp),
                             u.id, u.name, n.changeset_id,
                             ST_Y(n.geom), ST_X(n.geom)
                      FROM nodes n
                      LEFT OUTER JOIN users u
                        ON n.user_id = u.id
                      INNER JOIN box_node_list b
                        ON b.id = n.id
                      ORDER BY n.id""")

        nodes = [Node(*row) for row in db.fetchall()]
        nodes_dict = dict([(node.id, node) for node in nodes])
        
        # Select all node tags

        db.execute("""SELECT n.id, t.k, t.v
                      FROM node_tags t
                      INNER JOIN box_node_list n
                        ON n.id = t.node_id
                      ORDER BY n.id""")

        for (node_id, key, value) in db.fetchall():
            nodes_dict[node_id].tag(key, value)
        
        # Select core way information

        db.execute("""SELECT w.id, w.version, EXTRACT(epoch FROM w.tstamp),
                             u.id, u.name, w.changeset_id
                      FROM ways w
                      LEFT OUTER JOIN users u
                        ON w.user_id = u.id
                      INNER JOIN box_way_list b
                        ON b.id = w.id
                      ORDER BY w.id""")

        ways = [Way(*row) for row in db.fetchall()]
        ways_dict = dict([(way.id, way) for way in ways])

        # Select all way tags

        db.execute("""SELECT w.id, t.k, t.v
                      FROM way_tags t
                      INNER JOIN box_way_list w
                        ON w.id = t.way_id
                      ORDER BY w.id""")

        for (way_id, key, value) in db.fetchall():
            ways_dict[way_id].tag(key, value)

        # Select all way nodes in order

        db.execute("""SELECT w.id, n.node_id, n.sequence_id
                      FROM way_nodes n
                      INNER JOIN box_way_list w
                      ON n.way_id = w.id
                      ORDER BY w.id, n.sequence_id""")

        for (way_id, node_id, sequence_id) in db.fetchall():
            ways_dict[way_id].node(node_id)

        # Looks like: select core relation information

        db.execute("""SELECT e.id, e.version, e.user_id, u.name AS user_name, e.tstamp, e.changeset_id
                      FROM relations e
                      LEFT OUTER JOIN users u
                      ON e.user_id = u.id
                      INNER JOIN box_relation_list c
                      ON e.id = c.id
                      ORDER BY e.id""")

        counts.append(len(db.fetchall()))

        # Looks like: select all relation tags

        db.execute("""SELECT relation_id AS entity_id, k, v
                      FROM relation_tags f
                      INNER JOIN box_relation_list c
                      ON f.relation_id = c.id
                      ORDER BY entity_id""")

        counts.append(len(db.fetchall()))

        # Looks like: select all relation members in order

        db.execute("""SELECT relation_id AS entity_id, member_id, member_type, member_role, sequence_id
                      FROM relation_members f
                      INNER JOIN box_relation_list c
                      ON f.relation_id = c.id
                      ORDER BY entity_id, sequence_id""")

        counts.append(len(db.fetchall()))
        
        return SaveableResponse(nodes, ways)
        
        raise Exception(counts)

########NEW FILE########
__FILENAME__ = UtfGridComposite
""" Composite Provider for UTFGrid layers
https://github.com/mapbox/utfgrid-spec/blob/master/1.2/utfgrid.md

Combines multiple UTFGrid layers to create a single result.
The given layers will be added to the result in the order they are given.
Therefore the last one will have the highest priority.

Sample configuration:
	"provider":
	{
		"class": "TileStache.Goodies.Providers.UtfGridComposite:Provider",
		"kwargs":
		{
			"stack":
			[
				{ "layer_id": "layer1", "src": "my_utf_layer1", "wrapper": "grid" },
				{ "layer_id": "layer2", "src": "my_utf_layer2", "wrapper": "grid" }
			],
			"layer_id": "l",
			"wrapper": "grid"
		}
	}

stack: list of layers (and properties) to composite together
	layer_id: an id attribute that will be added to each json data object for this layer: { "layer_id": "layer1", "name": "blah", "address": "something"}
	src: layer name of the layer to composite
	wrapper: the wrapper definition of this layer if there is one (so we can remove it)
layer_id: the key for the layer_id attribute that is added to each data object: { "l": "layer1", ...}
wrapper: wrapper to add to the resulting utfgrid "WRAPPER({...})". Usually "grid"

if layer_id is not set in the layer or the provider config then it will not be set on data objects
"""

import json
import TileStache
from TileStache.Core import KnownUnknown

class Provider:
	
	def __init__(self, layer, stack, layer_id=None, wrapper=None):

		#Set up result storage
		self.resultGrid = []
		self.gridKeys = []
		self.gridData = {}
		
		self.layer = layer
		self.stack = stack
		self.layer_id = layer_id
		self.wrapper = wrapper
	
	def renderTile(self, width, height, srs, coord):
	
		for l in self.stack:
			self.addLayer(l, coord)
		return SaveableResponse(self.writeResult())

	def getTypeByExtension(self, extension):
		""" Get mime-type and format by file extension.
			This only accepts "json".
		"""
		if extension.lower() != 'json':
			raise KnownUnknown('UtfGridComposite only makes .json tiles, not "%s"' % extension)
		
		return 'text/json', 'JSON'

	def addLayer( self, layerDef, coord ):
		
		mime, layer = TileStache.getTile(self.layer.config.layers[layerDef['src']], coord, 'JSON')[1]
#		raise KnownUnknown(layer)
		if layerDef['wrapper'] == None:
			layer = json.loads(layer)
		else:
			layer = json.loads(layer[(len(layerDef['wrapper'])+1):-1]) #Strip "Wrapper(...)"
		
		gridSize = len(layer['grid'])

		#init resultGrid based on given layers (if required)
		if len(self.resultGrid) == 0:
			for i in xrange(gridSize):
				self.resultGrid.append([])
				for j in xrange(gridSize):
					self.resultGrid[i].append(-1)
	
		keys = layer['keys']
		
		keyRemap = {}
		for k in keys:
			if k in self.gridKeys:
				for ext in xrange(ord('a'), ord('z')+1):
					if not k+chr(ext) in self.gridKeys:
						keyRemap[k] = (k+chr(ext))
						break
				if not k in keyRemap:
					raise Error("Couldn't remap")
		
		addedKeys = [] #FIXME: HashSet<string>?
		
		for y in xrange(gridSize):
			line = layer['grid'][y]
			for x in xrange(gridSize):
				idNo = self.decodeId(line[x])
				
				if keys[idNo] == "":
					continue
				
				key = keys[idNo]
				if keys[idNo] in keyRemap:
					key = keyRemap[keys[idNo]]
				
				if not key in addedKeys:
					self.gridKeys.append(key)
					addedKeys.append(key)
					if layerDef['layer_id'] != None and self.layer_id != None: #Add layer name attribute
						layer['data'][keys[idNo]][self.layer_id] = layerDef['layer_id']
					self.gridData[key] = layer['data'][keys[idNo]]
						
						
				newId = self.gridKeys.index(key)
				
				self.resultGrid[x][y] = newId

	def writeResult( self ):
		gridSize = len(self.resultGrid)
	
		finalKeys = []
		finalData = {}
		finalGrid = []
		for i in xrange(gridSize):
			finalGrid.append("")
		
		finalIdCounter = 0
		idToFinalId = {}
		
		for y in xrange(gridSize):
			for x in xrange(gridSize):
				id = self.resultGrid[x][y]
				
				if not id in idToFinalId:
					idToFinalId[id] = finalIdCounter
					finalIdCounter = finalIdCounter + 1
					
					if id == -1:
						finalKeys.append("")
					else:
						finalKeys.append(self.gridKeys[id])
						finalData[self.gridKeys[id]] = self.gridData[self.gridKeys[id]]
				
				finalId = idToFinalId[id]
				finalGrid[y] = finalGrid[y] + self.encodeId(finalId)
	
		result = "{\"keys\": ["
		for i in xrange(len(finalKeys)):
			if i > 0:
				result += ","
			result += "\"" + finalKeys[i] + "\""
	
		result += "], \"data\": { "
		
		first = True
		for entry in self.gridData:
			if not first:
				result += ","
			first = False
			result += "\"" + entry + "\": " + json.dumps(self.gridData[entry]) + ""
		
		result += "}, \"grid\": ["
		
		for i in xrange(gridSize):
			line = finalGrid[i]
			result += json.dumps(line)
			if i < gridSize - 1:
				result += ","
		
		if self.wrapper == None:
			return result + "]}"
		else:
			return self.wrapper + "(" + result + "]})"

	def encodeId ( self, id ):
		id += 32
		if id >= 34:
			id = id + 1
		if id >= 92:
			id = id + 1
		if id > 127:
			return unichr(id)
		return chr(id)

	def decodeId( self, id ):
		id = ord(id)
		
		if id >= 93:
			id = id - 1
		if id >= 35:
			id = id - 1
		return id - 32


class SaveableResponse:
	""" Wrapper class for JSON response that makes it behave like a PIL.Image object.
		TileStache.getTile() expects to be able to save one of these to a buffer.
	"""
	def __init__(self, content):
		self.content = content
	def save(self, out, format):
		if format != 'JSON':
			raise KnownUnknown('MapnikGrid only saves .json tiles, not "%s"' % format)
		out.write(self.content)

########NEW FILE########
__FILENAME__ = UtfGridCompositeOverlap
import json
import TileStache
from TileStache.Core import KnownUnknown

class Provider:
  
  def __init__(self, layer, stack, layer_id=None, wrapper=None):
    #Set up result storage
    self.resultGrid = []
    self.gridKeys = []
    self.gridData = {}
    
    self.layer = layer
    self.stack = stack
    self.layer_id = layer_id
    self.wrapper = wrapper
    self.curId = 0

  def renderTile(self, width, height, srs, coord):
    for l in self.stack:
      self.addLayer(l, coord)
    return SaveableResponse(self.writeResult())

  def getTypeByExtension(self, extension):
    """ Get mime-type and format by file extension.
      This only accepts "json".
    """
    if extension.lower() != 'json':
      raise KnownUnknown('UtfGridComposite only makes .json tiles, not "%s"' % extension)
    
    return 'text/json', 'JSON'

  def addLayer( self, layerDef, coord ):
    layer = TileStache.getTile(self.layer.config.layers[layerDef['src']], coord, 'JSON')[1]

    if layerDef['wrapper'] == None:
      layer = json.loads(layer)
    else:
      # Strip "Wrapper(...)"
      layer = json.loads(layer[(len(layerDef['wrapper'])+1):-1])

    grid_size = len(layer['grid'])

    # Init resultGrid based on given layers (if required)
    if len(self.resultGrid) == 0:
      for i in xrange(grid_size):
        self.resultGrid.append([])
        for j in xrange(grid_size):
          self.resultGrid[i].append(-1)

    layer_keys = layer['keys']

    for y in xrange(grid_size):
      line = layer['grid'][y]
      for x in xrange(grid_size):
        src_id = self.decodeId(line[x])
        
        if layer_keys[src_id] == "":
          continue

        src_key = layer_keys[src_id]

        # Add layer name attribute
        if layerDef['layer_id'] != None and self.layer_id != None:
          layer['data'][src_key][self.layer_id] = layerDef['layer_id']

        if self.resultGrid[x][y] == -1:
          cur_id = self.curId
          self.curId += 1
          cur_key = json.dumps(cur_id)

          # Set key for current point.
          self.resultGrid[x][y] = self.encodeId(cur_id)
          self.gridKeys.insert(cur_id + 1, cur_key)

          # Initialize data bucket.
          self.gridData[cur_key] = []

        else:
          cur_id = self.decodeId(self.resultGrid[x][y])
          cur_key = json.dumps(cur_id)

        self.gridData[cur_key].append(layer['data'][src_key])

  def writeResult( self ):
    result = "{\"keys\": ["
    for i in xrange(len(self.gridKeys)):
      if i > 0:
        result += ","
      result += "\"" + self.gridKeys[i] + "\""
  
    result += "], \"data\": { "
    
    first = True
    for key in self.gridData:
      if not first:
        result += ","
      first = False
      result += "\"" + key + "\": " + json.dumps(self.gridData[key]) + ""
    
    result += "}, \"grid\": ["
    
    grid_size = len(self.resultGrid)
    first = True
    for y in xrange(grid_size):
      line = ""

      for x in xrange(grid_size):
        if self.resultGrid[x][y] == -1:
          self.resultGrid[x][y] = ' '

        line = line + self.resultGrid[x][y]

      if not first:
        result += ","
      first = False

      result += json.dumps(line)

    if self.wrapper == None:
      return result + "]}"
    else:
      return self.wrapper + "(" + result + "]})"

  def encodeId ( self, id ):
    id += 32
    if id >= 34:
      id = id + 1
    if id >= 92:
      id = id + 1
    if id > 127:
      return unichr(id)
    return chr(id)

  def decodeId( self, id ):
    id = ord(id)
    
    if id >= 93:
      id = id - 1
    if id >= 35:
      id = id - 1
    return id - 32


class SaveableResponse:
  """ Wrapper class for JSON response that makes it behave like a PIL.Image object.
    TileStache.getTile() expects to be able to save one of these to a buffer.
  """
  def __init__(self, content):
    self.content = content
  def save(self, out, format):
    if format != 'JSON':
      raise KnownUnknown('UtfGridCompositeOverlap only saves .json tiles, not "%s"' % format)
    out.write(self.content)


########NEW FILE########
__FILENAME__ = StatusServer
""" StatusServer is a replacement for WSGITileServer that saves per-process
    events to Redis and displays them in a chronological stream at /status.
    
    The internal behaviors of a running WSGI server can be hard to inspect,
    and StatusServer is designed to output data relevant to tile serving out
    to Redis where it can be gathered and inspected.
    
    Example usage, with gunicorn (http://gunicorn.org):
    
      gunicorn --bind localhost:8888 "TileStache.Goodies.StatusServer:WSGIServer('tilestache.cfg')"

    Example output, showing vertical alignment based on process ID:

      13235 Attempted cache lock, 2 minutes ago
      13235 Got cache lock in 0.001 seconds, 2 minutes ago
      13235 Started /osm/15/5255/12664.png, 2 minutes ago
      13235 Finished /osm/15/5255/12663.png in 0.724 seconds, 2 minutes ago
                         13233 Got cache lock in 0.001 seconds, 2 minutes ago
                         13233 Attempted cache lock, 2 minutes ago
                         13233 Started /osm/15/5249/12664.png, 2 minutes ago
                         13233 Finished /osm/15/5255/12661.png in 0.776 seconds, 2 minutes ago
                                     13234 Got cache lock in 0.001 seconds, 2 minutes ago
                                     13234 Attempted cache lock, 2 minutes ago
                                     13234 Started /osm/15/5254/12664.png, 2 minutes ago
                                     13234 Finished /osm/15/5249/12663.png in 0.466 seconds, 2 minutes ago
      13235 Attempted cache lock, 2 minutes ago
      13235 Got cache lock in 0.001 seconds, 2 minutes ago
      13235 Started /osm/15/5255/12663.png, 2 minutes ago
      13235 Finished /osm/15/5250/12664.png in 0.502 seconds, 2 minutes ago
                         13233 Got cache lock in 0.001 seconds, 2 minutes ago
                         13233 Attempted cache lock, 2 minutes ago
                         13233 Started /osm/15/5255/12661.png, 2 minutes ago
"""
from os import getpid
from time import time
from hashlib import md5

try:
    from redis import StrictRedis

except ImportError:
    #
    # Changes to the Redis API have led to incompatibilities between clients
    # and servers. Older versions of redis-py might be needed to communicate
    # with older server versions, such as the 1.2.0 that ships on Ubuntu Lucid.
    #
    # Ensure your Redis client and server match, potentially using pip
    # to specify a version number of the Python package to use, e.g.:
    #
    #   pip install -I "redis<=1.2.0"
    #
    from redis import Redis
    
    class StrictRedis (Redis):
        """ Compatibility class for older versions of Redis.
        """
        def lpush(self, name, value):
            # old Redis uses a boolean argument to name the list head.
            self.push(name, value, True)

        def expire(self, name, seconds):
            # old Redis expire can't be repeatedly updated.
            pass

import TileStache

_keep = 20

def update_status(msg, **redis_kwargs):
    """ Updated Redis with a message, prefix it with the current timestamp.
    
        Keyword args are passed directly to redis.StrictRedis().
    """
    pid = getpid()
    red = StrictRedis(**redis_kwargs)
    key = 'pid-%d-statuses' % pid
    msg = '%.6f %s' % (time(), msg)
    
    red.lpush(key, msg)
    red.expire(key, 60 * 60)
    red.ltrim(key, 0, _keep)

def delete_statuses(pid, **redis_kwargs):
    """
    """
    red = StrictRedis(**redis_kwargs)
    key = 'pid-%d-statuses' % pid
    red.delete(key)

def get_recent(**redis_kwargs):
    """ Retrieve recent messages from Redis, in reverse chronological order.
        
        Two lists are returned: one a single most-recent status message from
        each process, the other a list of numerous messages from each process.
        
        Each message is a tuple with floating point seconds elapsed, integer
        process ID that created it, and an associated text message such as
        "Got cache lock in 0.001 seconds" or "Started /osm/12/656/1582.png".
    
        Keyword args are passed directly to redis.StrictRedis().
    """
    pid = getpid()
    red = StrictRedis(**redis_kwargs)
    
    processes = []
    messages = []

    for key in red.keys('pid-*-statuses'):
        try:
            now = time()
            pid = int(key.split('-')[1])
            msgs = [msg.split(' ', 1) for msg in red.lrange(key, 0, _keep)]
            msgs = [(now - float(t), pid, msg) for (t, msg) in msgs]
        except:
            continue
        else:
            messages += msgs
            processes += msgs[:1]
    
    messages.sort() # youngest-first
    processes.sort() # youngest-first

    return processes, messages

def nice_time(time):
    """ Format a time in seconds to a string like "5 minutes".
    """
    if time < 15:
        return 'moments'
    if time < 90:
        return '%d seconds' % time
    if time < 60 * 60 * 1.5:
        return '%d minutes' % (time / 60.)
    if time < 24 * 60 * 60 * 1.5:
        return '%d hours' % (time / 3600.)
    if time < 7 * 24 * 60 * 60 * 1.5:
        return '%d days' % (time / 86400.)
    if time < 30 * 24 * 60 * 60 * 1.5:
        return '%d weeks' % (time / 604800.)

    return '%d months' % (time / 2592000.)

def pid_indent(pid):
    """ Get an MD5-based indentation for a process ID.
    """
    hash = md5(str(pid))
    number = int(hash.hexdigest(), 16)
    indent = number % 32
    return indent

def status_response(**redis_kwargs):
    """ Retrieve recent messages from Redis and 
    """
    processes, messages = get_recent(**redis_kwargs)
    
    lines = ['%d' % time(), '----------']
    
    for (index, (elapsed, pid, message)) in enumerate(processes):
        if elapsed > 6 * 60 * 60:
            # destroy the process if it hasn't been heard from in 6+ hours
            delete_statuses(pid, **redis_kwargs)
            continue
    
        if elapsed > 10 * 60:
            # don't show the process if it hasn't been heard from in ten+ minutes
            continue
    
        line = '%03s. %05s %s, %s ago' % (str(index + 1), pid, message, nice_time(elapsed))
        lines.append(line)
    
    lines.append('----------')
    
    for (elapsed, pid, message) in messages[:250]:
        line = [' ' * pid_indent(pid)]
        line += [str(pid), message + ',']
        line += [nice_time(elapsed), 'ago']
        lines.append(' '.join(line))
    
    return str('\n'.join(lines))

class WSGIServer (TileStache.WSGITileServer):
    """ Create a WSGI application that can handle requests from any server that talks WSGI.
    
        Notable moments in the tile-making process such as time elapsed
        or cache lock events are sent as messages to Redis. Inherits the
        constructor from TileStache WSGI, which just loads a TileStache
        configuration file into self.config.
    """
    def __init__(self, config, redis_host='localhost', redis_port=6379):
        """
        """
        TileStache.WSGITileServer.__init__(self, config)

        self.redis_kwargs = dict(host=redis_host, port=redis_port)
        self.config.cache = CacheWrap(self.config.cache, self.redis_kwargs)

        update_status('Created', **self.redis_kwargs)
        
    def __call__(self, environ, start_response):
        """
        """
        start = time()

        if environ['PATH_INFO'] == '/status':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return status_response(**self.redis_kwargs)

        if environ['PATH_INFO'] == '/favicon.ico':
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return ''

        try:
            update_status('Started %s' % environ['PATH_INFO'], **self.redis_kwargs)
            response = TileStache.WSGITileServer.__call__(self, environ, start_response)
    
            update_status('Finished %s in %.3f seconds' % (environ['PATH_INFO'], time() - start), **self.redis_kwargs)
            return response
        
        except Exception, e:
            update_status('Error: %s after %.3f seconds' % (str(e), time() - start), **self.redis_kwargs)
            raise
        
    def __del__(self):
        """
        """
        update_status('Destroyed', **self.redis_kwargs)

class CacheWrap:
    """ Wraps up a TileStache cache object and reports events to Redis.
    
        Implements a cache provider: http://tilestache.org/doc/#custom-caches.
    """
    def __init__(self, cache, redis_kwargs):
        self.cache = cache
        self.redis_kwargs = redis_kwargs
    
    def lock(self, layer, coord, format):
        start = time()
        update_status('Attempted cache lock', **self.redis_kwargs)

        self.cache.lock(layer, coord, format)
        update_status('Got cache lock in %.3f seconds' % (time() - start), **self.redis_kwargs)
    
    def unlock(self, layer, coord, format):
        return self.cache.unlock(layer, coord, format)
    
    def remove(self, layer, coord, format):
        return self.cache.remove(layer, coord, format)
    
    def read(self, layer, coord, format):
        return self.cache.read(layer, coord, format)
      
    def save(self, body, layer, coord, format):
        return self.cache.save(body, layer, coord, format)

########NEW FILE########
__FILENAME__ = client
''' Datasource for Mapnik that consumes vector tiles in GeoJSON or MVT format.

VecTiles provides Mapnik with a Datasource that can read remote tiles of vector
data in spherical mercator projection, providing for rendering of data without
the use of a local PostGIS database.

Sample usage in Mapnik configuration XML:
    
 <Layer name="test" srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs">
     <StyleName>...</StyleName>
     <Datasource>
         <Parameter name="type">python</Parameter>
         <Parameter name="factory">TileStache.Goodies.VecTiles:Datasource</Parameter>
         <Parameter name="template">http://example.com/{z}/{x}/{y}.mvt</Parameter>
         <Parameter name="sort_key">sort_key ascending</Parameter>
     </Datasource>
 </Layer>

From http://github.com/mapnik/mapnik/wiki/Python-Plugin:

  The Mapnik Python plugin allows you to write data sources in the Python
  programming language. This is useful if you want to rapidly prototype a
  plugin, perform some custom manipulation on data or if you want to bind
  mapnik to a datasource which is most conveniently accessed through Python.

  The plugin may be used from the existing mapnik Python bindings or it can
  embed the Python interpreter directly allowing it to be used from C++, XML
  or even JavaScript.

See also:
    http://mapnik.org/docs/v2.1.0/api/python/mapnik.PythonDatasource-class.html
'''
from math import pi, log as _log
from threading import Thread, Lock as _Lock
from httplib import HTTPConnection
from itertools import product
from StringIO import StringIO
from urlparse import urlparse
from gzip import GzipFile

import logging

from . import mvt, geojson

try:
    from mapnik import PythonDatasource, Box2d
except ImportError:
    # can still build documentation
    PythonDatasource = object

# earth's diameter in meters
diameter = 2 * pi * 6378137

# zoom of one-meter pixels
meter_zoom = _log(diameter) / _log(2) - 8

def utf8_keys(dictionary):
    ''' Convert dictionary keys to utf8-encoded strings for Mapnik.
    
        By default, json.load() returns dictionaries with unicode keys
        but Mapnik is ultra-whiny about these and rejects them.
    '''
    return dict([(key.encode('utf8'), val) for (key, val) in dictionary.items()])

def list_tiles(query, zoom_adjust):
    ''' Return a list of tiles (z, x, y) dicts for a mapnik Query object.
    
        Query is assumed to be in spherical mercator projection.
        Zoom_adjust is an integer delta to subtract from the calculated zoom.
    '''
    # relative zoom from one-meter pixels to query pixels
    resolution = sum(query.resolution) / 2
    diff = _log(resolution) / _log(2) - zoom_adjust
    
    # calculated zoom level for this query
    zoom = round(meter_zoom + diff)
    
    scale = 2**zoom
    
    mincol = int(scale * (query.bbox.minx/diameter + .5))
    maxcol = int(scale * (query.bbox.maxx/diameter + .5))
    minrow = int(scale * (.5 - query.bbox.maxy/diameter))
    maxrow = int(scale * (.5 - query.bbox.miny/diameter))
    
    cols, rows = range(mincol, maxcol+1), range(minrow, maxrow+1)
    return [dict(z=zoom, x=col, y=row) for (col, row) in product(cols, rows)]

def load_features(jobs, host, port, path, tiles):
    ''' Load data from tiles to features.
    
        Calls load_tile_features() in a thread pool to speak HTTP.
    '''
    features = []
    lock = _Lock()
    
    args = (lock, host, port, path, tiles, features)
    threads = [Thread(target=load_tile_features, args=args) for i in range(jobs)]
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    logging.debug('Loaded %d features' % len(features))
    return features

def load_tile_features(lock, host, port, path_fmt, tiles, features):
    ''' Load data from tiles to features.
    
        Called from load_features(), in a thread.
        
        Returns a list of (WKB, property dict) pairs.
    '''
    while True:
        try:
            tile = tiles.pop()
            
        except IndexError:
            # All done.
            break
        
        #
        # Request tile data from remote server.
        #
        conn = HTTPConnection(host, port)
        head = {'Accept-Encoding': 'gzip'}
        path = path_fmt % tile

        conn.request('GET', path, headers=head)
        resp = conn.getresponse()
        file = StringIO(resp.read())
        
        if resp.getheader('Content-Encoding') == 'gzip':
            file = GzipFile(fileobj=file, mode='r')

        #
        # Convert data to feature list, which
        # benchmarked slightly faster in a lock.
        #
        with lock:
            mime_type = resp.getheader('Content-Type')
            
            if mime_type in ('text/json', 'application/json'):
                file_features = geojson.decode(file)
            
            elif mime_type == 'application/octet-stream+mvt':
                file_features = mvt.decode(file)
            
            else:
                logging.error('Unknown MIME-Type "%s" from %s:%d%s' % (mime_type, host, port, path))
                return
                
            logging.debug('%d features in %s:%d%s' % (len(file_features), host, port, path))
            features.extend(file_features)

class Datasource (PythonDatasource):
    ''' Mapnik datasource to read tiled vector data in GeoJSON or MVT formats.

        Sample usage in Mapnik configuration XML:
        
        <Layer name="test" srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs">
            <StyleName>...</StyleName>
            <Datasource>
                <Parameter name="type">python</Parameter>
                <Parameter name="factory">TileStache.Goodies.VecTiles:Datasource</Parameter>
                <Parameter name="template">http://example.com/{z}/{x}/{y}.mvt</Parameter>
                <Parameter name="sort_key">sort_key ascending</Parameter>
            </Datasource>
        </Layer>
    '''
    def __init__(self, template, sort_key=None, clipped='true', zoom_data='single'):
        ''' Make a new Datasource.
        
            Parameters:
        
              template:
                Required URL template with placeholders for tile zoom, x and y,
                e.g. "http://example.com/layer/{z}/{x}/{y}.json".
        
              sort_key:
                Optional field name to use when sorting features for rendering.
                E.g. "name" or "name ascending" to sort ascending by name,
                "name descending" to sort descending by name.
              
              clipped:
                Optional boolean flag to determine correct behavior for
                duplicate geometries. When tile data is not clipped, features()
                will check geometry uniqueness and throw out duplicates.

                Setting clipped to false for actually-clipped geometries has no
                effect but wastes time. Setting clipped to false for unclipped
                geometries will result in possibly wrong-looking output.

                Default is "true".
              
              zoom_data:
                Optional keyword specifying single or double zoom data tiles.
                Works especially well with relatively sparse label layers.
                
                When set to "double", tiles will be requested at one zoom level
                out from the map view, e.g. double-sized z13 tiles will be used
                to render a normal z14 map.

                Default is "single".
        '''
        scheme, host, path, p, query, f = urlparse(template)
        
        self.host = host
        self.port = 443 if scheme == 'https' else 80
        
        if ':' in host:
            self.host = host.split(':', 1)[0]
            self.port = int(host.split(':', 1)[1])
        
        self.path = path + ('?' if query else '') + query
        self.path = self.path.replace('%', '%%')
        self.path = self.path.replace('{Z}', '{z}').replace('{z}', '%(z)d')
        self.path = self.path.replace('{X}', '{x}').replace('{x}', '%(x)d')
        self.path = self.path.replace('{Y}', '{y}').replace('{y}', '%(y)d')
        
        if sort_key is None:
            self.sort, self.reverse = None, None
        
        elif sort_key.lower().endswith(' descending'):
            logging.debug('Will sort by %s descending' % sort_key)
            self.sort, self.reverse = sort_key.split()[0], True
        
        else:
            logging.debug('Will sort by %s ascending' % sort_key)
            self.sort, self.reverse = sort_key.split()[0], False
        
        self.clipped = clipped.lower() not in ('false', 'no', '0')
        self.zoom_adjust = {'double': 1}.get(zoom_data.lower(), 0)
        
        bbox = Box2d(-diameter/2, -diameter/2, diameter/2, diameter/2)
        PythonDatasource.__init__(self, envelope=bbox)

    def features(self, query):
        '''
        '''
        logging.debug('Rendering %s' % str(query.bbox))
        
        tiles = list_tiles(query, self.zoom_adjust)
        features = []
        seen = set()
        
        for (wkb, props) in load_features(8, self.host, self.port, self.path, tiles):
            if not self.clipped:
                # not clipped means get rid of inevitable dupes
                key = (wkb, tuple(sorted(props.items())))
                
                if key in seen:
                    continue

                seen.add(key)
            
            features.append((wkb, utf8_keys(props)))
            
        if self.sort:
            logging.debug('Sorting by %s %s' % (self.sort, 'descending' if self.reverse else 'ascending'))
            key_func = lambda (wkb, props): props.get(self.sort, None)
            features.sort(reverse=self.reverse, key=key_func)
        
        if len(features) == 0:
            return PythonDatasource.wkb_features(keys=[], features=[])
        
        # build a set of shared keys
        props = zip(*features)[1]
        keys = [set(prop.keys()) for prop in props]
        keys = reduce(lambda a, b: a & b, keys)

        return PythonDatasource.wkb_features(keys=keys, features=features)

########NEW FILE########
__FILENAME__ = geojson
from re import compile
from math import pi, log, tan, ceil

import json

from shapely.wkb import loads
from shapely.geometry import asShape

from ... import getTile
from ...Core import KnownUnknown
from .ops import transform

float_pat = compile(r'^-?\d+\.\d+(e-?\d+)?$')
charfloat_pat = compile(r'^[\[,\,]-?\d+\.\d+(e-?\d+)?$')

# floating point lat/lon precision for each zoom level, good to ~1/4 pixel.
precisions = [int(ceil(log(1<<zoom + 8+2) / log(10)) - 2) for zoom in range(23)]

def get_tiles(names, config, coord):
    ''' Retrieve a list of named GeoJSON layer tiles from a TileStache config.
    
        Check integrity and compatibility of each, looking at known layers,
        correct JSON mime-types and "FeatureCollection" in the type attributes.
    '''
    unknown_layers = set(names) - set(config.layers.keys())
    
    if unknown_layers:
        raise KnownUnknown("%s.get_tiles didn't recognize %s when trying to load %s." % (__name__, ', '.join(unknown_layers), ', '.join(names)))
    
    layers = [config.layers[name] for name in names]
    mimes, bodies = zip(*[getTile(layer, coord, 'json') for layer in layers])
    bad_mimes = [(name, mime) for (mime, name) in zip(mimes, names) if not mime.endswith('/json')]
    
    if bad_mimes:
        raise KnownUnknown('%s.get_tiles encountered a non-JSON mime-type in %s sub-layer: "%s"' % ((__name__, ) + bad_mimes[0]))
    
    geojsons = map(json.loads, bodies)
    bad_types = [(name, topo['type']) for (topo, name) in zip(geojsons, names) if topo['type'] != 'FeatureCollection']
    
    if bad_types:
        raise KnownUnknown('%s.get_tiles encountered a non-FeatureCollection type in %s sub-layer: "%s"' % ((__name__, ) + bad_types[0]))
    
    return geojsons

def mercator((x, y)):
    ''' Project an (x, y) tuple to spherical mercator.
    '''
    x, y = pi * x/180, pi * y/180
    y = log(tan(0.25 * pi + 0.5 * y))
    return 6378137 * x, 6378137 * y

def decode(file):
    ''' Decode a GeoJSON file into a list of (WKB, property dict) features.
    
        Result can be passed directly to mapnik.PythonDatasource.wkb_features().
    '''
    data = json.load(file)
    features = []
    
    for feature in data['features']:
        if feature['type'] != 'Feature':
            continue
        
        if feature['geometry']['type'] == 'GeometryCollection':
            continue
        
        prop = feature['properties']
        geom = transform(asShape(feature['geometry']), mercator)
        features.append((geom.wkb, prop))
    
    return features

def encode(file, features, zoom, is_clipped):
    ''' Encode a list of (WKB, property dict) features into a GeoJSON stream.
    
        Also accept three-element tuples as features: (WKB, property dict, id).
    
        Geometries in the features list are assumed to be unprojected lon, lats.
        Floating point precision in the output is truncated to six digits.
    '''
    try:
        # Assume three-element features
        features = [dict(type='Feature', properties=p, geometry=loads(g).__geo_interface__, id=i) for (g, p, i) in features]

    except ValueError:
        # Fall back to two-element features
        features = [dict(type='Feature', properties=p, geometry=loads(g).__geo_interface__) for (g, p) in features]
    
    if is_clipped:
        for feature in features:
            feature.update(dict(clipped=True))
    
    geojson = dict(type='FeatureCollection', features=features)
    encoder = json.JSONEncoder(separators=(',', ':'))
    encoded = encoder.iterencode(geojson)
    flt_fmt = '%%.%df' % precisions[zoom]
    
    for token in encoded:
        if charfloat_pat.match(token):
            # in python 2.7, we see a character followed by a float literal
            file.write(token[0] + flt_fmt % float(token[1:]))
        
        elif float_pat.match(token):
            # in python 2.6, we see a simple float literal
            file.write(flt_fmt % float(token))
        
        else:
            file.write(token)

def merge(file, names, config, coord):
    ''' Retrieve a list of GeoJSON tile responses and merge them into one.
    
        get_tiles() retrieves data and performs basic integrity checks.
    '''
    inputs = get_tiles(names, config, coord)
    output = dict(zip(names, inputs))

    encoder = json.JSONEncoder(separators=(',', ':'))
    encoded = encoder.iterencode(output)
    flt_fmt = '%%.%df' % precisions[coord.zoom]
    
    for token in encoded:
        if charfloat_pat.match(token):
            # in python 2.7, we see a character followed by a float literal
            file.write(token[0] + flt_fmt % float(token[1:]))
        
        elif float_pat.match(token):
            # in python 2.6, we see a simple float literal
            file.write(flt_fmt % float(token))
        
        else:
            file.write(token)

########NEW FILE########
__FILENAME__ = mvt
''' Implementation of MVT (Mapnik Vector Tiles) data format.

Mapnik's PythonDatasource.features() method can return a list of WKB features,
pairs of WKB format geometry and dictionaries of key-value pairs that are
rendered by Mapnik directly. PythonDatasource is new in Mapnik as of version
2.1.0.

More information:
    http://mapnik.org/docs/v2.1.0/api/python/mapnik.PythonDatasource-class.html

The MVT file format is a simple container for Mapnik-compatible vector tiles
that minimizes the amount of conversion performed by the renderer, in contrast
to other file formats such as GeoJSON.

An MVT file starts with 8 bytes.

    4 bytes "\\x89MVT"
    uint32  Length of body
    bytes   zlib-compressed body

The following body is a zlib-compressed bytestream. When decompressed,
it starts with four bytes indicating the total feature count.

    uint32  Feature count
    bytes   Stream of feature data

Each feature has two parts, a raw WKB (well-known binary) representation of
the geometry in spherical mercator and a JSON blob for feature properties.

    uint32  Length of feature WKB
    bytes   Raw bytes of WKB
    uint32  Length of properties JSON
    bytes   JSON dictionary of feature properties

By default, encode() approximates the floating point precision of WKB geometry
to 26 bits for a significant compression improvement and no visible impact on
rendering at zoom 18 and lower.
'''
from StringIO import StringIO
from zlib import decompress as _decompress, compress as _compress
from struct import unpack as _unpack, pack as _pack
import json

from .wkb import approximate_wkb

def decode(file):
    ''' Decode an MVT file into a list of (WKB, property dict) features.
    
        Result can be passed directly to mapnik.PythonDatasource.wkb_features().
    '''
    head = file.read(4)
    
    if head != '\x89MVT':
        raise Exception('Bad head: "%s"' % head)
    
    body = StringIO(_decompress(file.read(_next_int(file))))
    features = []
    
    for i in range(_next_int(body)):
        wkb = body.read(_next_int(body))
        raw = body.read(_next_int(body))

        props = json.loads(raw)
        features.append((wkb, props))
    
    return features

def encode(file, features):
    ''' Encode a list of (WKB, property dict) features into an MVT stream.
    
        Geometries in the features list are assumed to be in spherical mercator.
        Floating point precision in the output is approximated to 26 bits.
    '''
    parts = []
    
    for feature in features:
        wkb = approximate_wkb(feature[0])
        prop = json.dumps(feature[1])
        
        parts.extend([_pack('>I', len(wkb)), wkb, _pack('>I', len(prop)), prop])
    
    body = _compress(_pack('>I', len(features)) + ''.join(parts))
    
    file.write('\x89MVT')
    file.write(_pack('>I', len(body)))
    file.write(body)

def _next_int(file):
    ''' Read the next big-endian 4-byte unsigned int from a file.
    '''
    return _unpack('!I', file.read(4))[0]

########NEW FILE########
__FILENAME__ = ops
''' Per-coordinate transformation function for shapely geometries.

To be replaced with shapely.ops.transform in Shapely 1.2.18.

See also:
    https://github.com/Toblerity/Shapely/issues/46

>>> from shapely.geometry import *

>>> coll0 = GeometryCollection()
>>> coll1 = transform(coll0, lambda (x, y): (x+1, y+1))
>>> print coll1                                                                 # doctest: +ELLIPSIS
GEOMETRYCOLLECTION EMPTY

>>> point0 = Point(0, 0)
>>> point1 = transform(point0, lambda (x, y): (x+1, y+1))
>>> print point1                                                                # doctest: +ELLIPSIS
POINT (1.00... 1.00...)

>>> mpoint0 = MultiPoint(((0, 0), (1, 1), (2, 2)))
>>> mpoint1 = transform(mpoint0, lambda (x, y): (x+1, y+1))
>>> print mpoint1                                                               # doctest: +ELLIPSIS
MULTIPOINT (1.00... 1.00..., 2.00... 2.00..., 3.00... 3.00...)

>>> line0 = LineString(((0, 0), (1, 1), (2, 2)))
>>> line1 = transform(line0, lambda (x, y): (x+1, y+1))
>>> print line1                                                                 # doctest: +ELLIPSIS
LINESTRING (1.00... 1.00..., 2.00... 2.00..., 3.00... 3.00...)

>>> mline0 = MultiLineString((((0, 0), (1, 1), (2, 2)), ((3, 3), (4, 4), (5, 5))))
>>> mline1 = transform(mline0, lambda (x, y): (x+1, y+1))
>>> print mline1                                                                # doctest: +ELLIPSIS
MULTILINESTRING ((1.00... 1.00..., 2.00... 2.00..., 3.00... 3.00...), (4.00... 4.00..., 5.00... 5.00..., 6.00... 6.00...))

>>> poly0 = Polygon(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)))
>>> poly1 = transform(poly0, lambda (x, y): (x+1, y+1))
>>> print poly1                                                                 # doctest: +ELLIPSIS
POLYGON ((1.00... 1.00..., 2.00... 1.00..., 2.00... 2.00..., 1.00... 2.00..., 1.00... 1.00...))

>>> poly0 = Polygon(((0, 0), (3, 0), (3, 3), (0, 3), (0, 0)), [((1, 1), (2, 1), (2, 2), (1, 2), (1, 1))])
>>> poly1 = transform(poly0, lambda (x, y): (x+1, y+1))
>>> print poly1                                                                 # doctest: +ELLIPSIS
POLYGON ((1.00... 1.00..., 4.00... 1.00..., 4.00... 4.00..., 1.00... 4.00..., 1.00... 1.00...), (2.00... 2.00..., 3.00... 2.00..., 3.00... 3.00..., 2.00... 3.00..., 2.00... 2.00...))

>>> mpoly0 = MultiPolygon(((((0, 0), (3, 0), (3, 3), (0, 3), (0, 0)), [((1, 1), (2, 1), (2, 2), (1, 2), (1, 1))]), (((10, 10), (13, 10), (13, 13), (10, 13), (10, 10)), [((11, 11), (12, 11), (12, 12), (11, 12), (11, 11))])))
>>> mpoly1 = transform(mpoly0, lambda (x, y): (x+1, y+1))
>>> print mpoly1                                                                # doctest: +ELLIPSIS
MULTIPOLYGON (((1.00... 1.00..., 4.00... 1.00..., 4.00... 4.00..., 1.00... 4.00..., 1.00... 1.00...), (2.00... 2.00..., 3.00... 2.00..., 3.00... 3.00..., 2.00... 3.00..., 2.00... 2.00...)), ((11.00... 11.00..., 14.00... 11.00..., 14.00... 14.00..., 11.00... 14.00..., 11.00... 11.00...), (12.00... 12.00..., 13.00... 12.00..., 13.00... 13.00..., 12.00... 13.00..., 12.00... 12.00...)))
'''

def transform(shape, func):
    ''' Apply a function to every coordinate in a geometry.
    '''
    construct = shape.__class__
    
    if shape.type.startswith('Multi'):
        parts = [transform(geom, func) for geom in shape.geoms]
        return construct(parts)
    
    if shape.type in ('Point', 'LineString'):
        return construct(map(func, shape.coords))
        
    if shape.type == 'Polygon':
        exterior = map(func, shape.exterior.coords)
        rings = [map(func, ring.coords) for ring in shape.interiors]
        return construct(exterior, rings)
    
    if shape.type == 'GeometryCollection':
        return construct()
    
    raise ValueError('Unknown geometry type, "%s"' % shape.type)

if __name__ == '__main__':
    from doctest import testmod
    testmod()

########NEW FILE########
__FILENAME__ = server
''' Provider that returns PostGIS vector tiles in GeoJSON or MVT format.

VecTiles is intended for rendering, and returns tiles with contents simplified,
precision reduced and often clipped. The MVT format in particular is designed
for use in Mapnik with the VecTiles Datasource, which can read binary MVT tiles.

For a more general implementation, try the Vector provider:
    http://tilestache.org/doc/#vector-provider
'''
from math import pi
from urlparse import urljoin, urlparse
from urllib import urlopen
from os.path import exists

try:
    from psycopg2.extras import RealDictCursor
    from psycopg2 import connect

except ImportError, err:
    # Still possible to build the documentation without psycopg2

    def connect(*args, **kwargs):
        raise err

from . import mvt, geojson, topojson
from ...Geography import SphericalMercator
from ModestMaps.Core import Point

tolerances = [6378137 * 2 * pi / (2 ** (zoom + 8)) for zoom in range(20)]

class Provider:
    ''' VecTiles provider for PostGIS data sources.
    
        Parameters:
        
          dbinfo:
            Required dictionary of Postgres connection parameters. Should
            include some combination of 'host', 'user', 'password', and 'database'.
        
          queries:
            Required list of Postgres queries, one for each zoom level. The
            last query in the list is repeated for higher zoom levels, and null
            queries indicate an empty response.
            
            Query must use "__geometry__" for a column name, and must be in
            spherical mercator (900913) projection. A query may include an
            "__id__" column, which will be used as a feature ID in GeoJSON
            instead of a dynamically-generated hash of the geometry. A query
            can additionally be a file name or URL, interpreted relative to
            the location of the TileStache config file.
            
            If the query contains the token "!bbox!", it will be replaced with
            a constant bounding box geomtry like this:
            "ST_SetSRID(ST_MakeBox2D(ST_MakePoint(x, y), ST_MakePoint(x, y)), <srid>)"
            
            This behavior is modeled on Mapnik's similar bbox token feature:
            https://github.com/mapnik/mapnik/wiki/PostGIS#bbox-token
          
          clip:
            Optional boolean flag determines whether geometries are clipped to
            tile boundaries or returned in full. Default true: clip geometries.
        
          srid:
            Optional numeric SRID used by PostGIS for spherical mercator.
            Default 900913.
        
          simplify:
            Optional floating point number of pixels to simplify all geometries.
            Useful for creating double resolution (retina) tiles set to 0.5, or
            set to 0.0 to prevent any simplification. Default 1.0.
        
          simplify_until:
            Optional integer specifying a zoom level where no more geometry
            simplification should occur. Default 16.
        
        Sample configuration, for a layer with no results at zooms 0-9, basic
        selection of lines with names and highway tags for zoom 10, a remote
        URL containing a query for zoom 11, and a local file for zooms 12+:
        
          "provider":
          {
            "class": "TileStache.Goodies.VecTiles:Provider",
            "kwargs":
            {
              "dbinfo":
              {
                "host": "localhost",
                "user": "gis",
                "password": "gis",
                "database": "gis"
              },
              "queries":
              [
                null, null, null, null, null,
                null, null, null, null, null,
                "SELECT way AS __geometry__, highway, name FROM planet_osm_line -- zoom 10+ ",
                "http://example.com/query-z11.pgsql",
                "query-z12-plus.pgsql"
              ]
            }
          }
    '''
    def __init__(self, layer, dbinfo, queries, clip=True, srid=900913, simplify=1.0, simplify_until=16):
        '''
        '''
        self.layer = layer
        
        keys = 'host', 'user', 'password', 'database', 'port', 'dbname'
        self.dbinfo = dict([(k, v) for (k, v) in dbinfo.items() if k in keys])

        self.clip = bool(clip)
        self.srid = int(srid)
        self.simplify = float(simplify)
        self.simplify_until = int(simplify_until)
        
        self.queries = []
        self.columns = {}
        
        for query in queries:
            if query is None:
                self.queries.append(None)
                continue
        
            #
            # might be a file or URL?
            #
            url = urljoin(layer.config.dirpath, query)
            scheme, h, path, p, q, f = urlparse(url)
            
            if scheme in ('file', '') and exists(path):
                query = open(path).read()
            
            elif scheme == 'http' and ' ' not in url:
                query = urlopen(url).read()
        
            self.queries.append(query)
        
    def renderTile(self, width, height, srs, coord):
        ''' Render a single tile, return a Response instance.
        '''
        try:
            query = self.queries[coord.zoom]
        except IndexError:
            query = self.queries[-1]

        ll = self.layer.projection.coordinateProj(coord.down())
        ur = self.layer.projection.coordinateProj(coord.right())
        bounds = ll.x, ll.y, ur.x, ur.y
        
        if not query:
            return EmptyResponse(bounds)
        
        if query not in self.columns:
            self.columns[query] = query_columns(self.dbinfo, self.srid, query, bounds)
        
        tolerance = self.simplify * tolerances[coord.zoom] if coord.zoom < self.simplify_until else None
        
        return Response(self.dbinfo, self.srid, query, self.columns[query], bounds, tolerance, coord.zoom, self.clip)

    def getTypeByExtension(self, extension):
        ''' Get mime-type and format by file extension, one of "mvt", "json" or "topojson".
        '''
        if extension.lower() == 'mvt':
            return 'application/octet-stream+mvt', 'MVT'
        
        elif extension.lower() == 'json':
            return 'application/json', 'JSON'
        
        elif extension.lower() == 'topojson':
            return 'application/json', 'TopoJSON'
        
        else:
            raise ValueError(extension)

class MultiProvider:
    ''' VecTiles provider to gather PostGIS tiles into a single multi-response.
        
        Returns a MultiResponse object for GeoJSON or TopoJSON requests.
    
        names:
          List of names of vector-generating layers from elsewhere in config.
        
        Sample configuration, for a layer with combined data from water
        and land areas, both assumed to be vector-returning layers:
        
          "provider":
          {
            "class": "TileStache.Goodies.VecTiles:MultiProvider",
            "kwargs":
            {
              "names": ["water-areas", "land-areas"]
            }
          }
    '''
    def __init__(self, layer, names):
        self.layer = layer
        self.names = names
        
    def renderTile(self, width, height, srs, coord):
        ''' Render a single tile, return a Response instance.
        '''
        return MultiResponse(self.layer.config, self.names, coord)

    def getTypeByExtension(self, extension):
        ''' Get mime-type and format by file extension, "json" or "topojson" only.
        '''
        if extension.lower() == 'json':
            return 'application/json', 'JSON'
        
        elif extension.lower() == 'topojson':
            return 'application/json', 'TopoJSON'
        
        else:
            raise ValueError(extension)

class Connection:
    ''' Context manager for Postgres connections.
    
        See http://www.python.org/dev/peps/pep-0343/
        and http://effbot.org/zone/python-with-statement.htm
    '''
    def __init__(self, dbinfo):
        self.dbinfo = dbinfo
    
    def __enter__(self):
        self.db = connect(**self.dbinfo).cursor(cursor_factory=RealDictCursor)
        return self.db
    
    def __exit__(self, type, value, traceback):
        self.db.connection.close()

class Response:
    '''
    '''
    def __init__(self, dbinfo, srid, subquery, columns, bounds, tolerance, zoom, clip):
        ''' Create a new response object with Postgres connection info and a query.
        
            bounds argument is a 4-tuple with (xmin, ymin, xmax, ymax).
        '''
        self.dbinfo = dbinfo
        self.bounds = bounds
        self.zoom = zoom
        self.clip = clip
        
        bbox = 'ST_MakeBox2D(ST_MakePoint(%.2f, %.2f), ST_MakePoint(%.2f, %.2f))' % bounds
        geo_query = build_query(srid, subquery, columns, bbox, tolerance, True, clip)
        merc_query = build_query(srid, subquery, columns, bbox, tolerance, False, clip)
        self.query = dict(TopoJSON=geo_query, JSON=geo_query, MVT=merc_query)
    
    def save(self, out, format):
        '''
        '''
        with Connection(self.dbinfo) as db:
            db.execute(self.query[format])
            
            features = []
            
            for row in db.fetchall():
                if row['__geometry__'] is None:
                    continue
            
                wkb = bytes(row['__geometry__'])
                prop = dict([(k, v) for (k, v) in row.items()
                             if k not in ('__geometry__', '__id__')])
                
                if '__id__' in row:
                    features.append((wkb, prop, row['__id__']))
                
                else:
                    features.append((wkb, prop))

        if format == 'MVT':
            mvt.encode(out, features)
        
        elif format == 'JSON':
            geojson.encode(out, features, self.zoom, self.clip)
        
        elif format == 'TopoJSON':
            ll = SphericalMercator().projLocation(Point(*self.bounds[0:2]))
            ur = SphericalMercator().projLocation(Point(*self.bounds[2:4]))
            topojson.encode(out, features, (ll.lon, ll.lat, ur.lon, ur.lat), self.clip)
        
        else:
            raise ValueError(format)

class EmptyResponse:
    ''' Simple empty response renders valid MVT or GeoJSON with no features.
    '''
    def __init__(self, bounds):
        self.bounds = bounds
    
    def save(self, out, format):
        '''
        '''
        if format == 'MVT':
            mvt.encode(out, [])
        
        elif format == 'JSON':
            geojson.encode(out, [], 0, False)
        
        elif format == 'TopoJSON':
            ll = SphericalMercator().projLocation(Point(*self.bounds[0:2]))
            ur = SphericalMercator().projLocation(Point(*self.bounds[2:4]))
            topojson.encode(out, [], (ll.lon, ll.lat, ur.lon, ur.lat), False)
        
        else:
            raise ValueError(format)

class MultiResponse:
    '''
    '''
    def __init__(self, config, names, coord):
        ''' Create a new response object with TileStache config and layer names.
        '''
        self.config = config
        self.names = names
        self.coord = coord
    
    def save(self, out, format):
        '''
        '''
        if format == 'TopoJSON':
            topojson.merge(out, self.names, self.config, self.coord)
        
        elif format == 'JSON':
            geojson.merge(out, self.names, self.config, self.coord)
        
        else:
            raise ValueError(format)

def query_columns(dbinfo, srid, subquery, bounds):
    ''' Get information about the columns returned for a subquery.
    '''
    with Connection(dbinfo) as db:
        #
        # While bounds covers less than the full planet, look for just one feature.
        #
        while (abs(bounds[2] - bounds[0]) * abs(bounds[2] - bounds[0])) < 1.61e15:
            bbox = 'ST_MakeBox2D(ST_MakePoint(%f, %f), ST_MakePoint(%f, %f))' % bounds
            bbox = 'ST_SetSRID(%s, %d)' % (bbox, srid)
        
            query = subquery.replace('!bbox!', bbox)
        
            db.execute(query + '\n LIMIT 1') # newline is important here, to break out of comments.
            row = db.fetchone()
            
            if row is None:
                #
                # Try zooming out three levels (8x) to look for features.
                #
                bounds = (bounds[0] - (bounds[2] - bounds[0]) * 3.5,
                          bounds[1] - (bounds[3] - bounds[1]) * 3.5,
                          bounds[2] + (bounds[2] - bounds[0]) * 3.5,
                          bounds[3] + (bounds[3] - bounds[1]) * 3.5)
                
                continue
            
            column_names = set(row.keys())
            return column_names
        
def build_query(srid, subquery, subcolumns, bbox, tolerance, is_geo, is_clipped):
    ''' Build and return an PostGIS query.
    '''
    bbox = 'ST_SetSRID(%s, %d)' % (bbox, srid)
    geom = 'q.__geometry__'
    
    if is_clipped:
        geom = 'ST_Intersection(%s, %s)' % (geom, bbox)
    
    if tolerance is not None:
        geom = 'ST_SimplifyPreserveTopology(%s, %.2f)' % (geom, tolerance)
    
    if is_geo:
        geom = 'ST_Transform(%s, 4326)' % geom
    
    subquery = subquery.replace('!bbox!', bbox)
    columns = ['q."%s"' % c for c in subcolumns if c not in ('__geometry__', )]
    
    if '__geometry__' not in subcolumns:
        raise Exception("There's supposed to be a __geometry__ column.")
    
    if '__id__' not in subcolumns:
        columns.append('Substr(MD5(ST_AsBinary(q.__geometry__)), 1, 10) AS __id__')
    
    columns = ', '.join(columns)
    
    return '''SELECT %(columns)s,
                     ST_AsBinary(%(geom)s) AS __geometry__
              FROM (
                %(subquery)s
                ) AS q
              WHERE ST_IsValid(q.__geometry__)
                AND q.__geometry__ && %(bbox)s
                AND ST_Intersects(q.__geometry__, %(bbox)s)''' \
            % locals()

########NEW FILE########
__FILENAME__ = topojson
from shapely.wkb import loads
import json

from ... import getTile
from ...Core import KnownUnknown

def get_tiles(names, config, coord):
    ''' Retrieve a list of named TopoJSON layer tiles from a TileStache config.
    
        Check integrity and compatibility of each, looking at known layers,
        correct JSON mime-types, "Topology" in the type attributes, and
        matching affine transformations.
    '''
    unknown_layers = set(names) - set(config.layers.keys())
    
    if unknown_layers:
        raise KnownUnknown("%s.get_tiles didn't recognize %s when trying to load %s." % (__name__, ', '.join(unknown_layers), ', '.join(names)))
    
    layers = [config.layers[name] for name in names]
    mimes, bodies = zip(*[getTile(layer, coord, 'topojson') for layer in layers])
    bad_mimes = [(name, mime) for (mime, name) in zip(mimes, names) if not mime.endswith('/json')]
    
    if bad_mimes:
        raise KnownUnknown('%s.get_tiles encountered a non-JSON mime-type in %s sub-layer: "%s"' % ((__name__, ) + bad_mimes[0]))
    
    topojsons = map(json.loads, bodies)
    bad_types = [(name, topo['type']) for (topo, name) in zip(topojsons, names) if topo['type'] != 'Topology']
    
    if bad_types:
        raise KnownUnknown('%s.get_tiles encountered a non-Topology type in %s sub-layer: "%s"' % ((__name__, ) + bad_types[0]))
    
    transforms = [topo['transform'] for topo in topojsons]
    unique_xforms = set([tuple(xform['scale'] + xform['translate']) for xform in transforms])
    
    if len(unique_xforms) > 1:
        raise KnownUnknown('%s.get_tiles encountered incompatible transforms: %s' % (__name__, list(unique_xforms)))
    
    return topojsons

def update_arc_indexes(geometry, merged_arcs, old_arcs):
    ''' Updated geometry arc indexes, and add arcs to merged_arcs along the way.
    
        Arguments are modified in-place, and nothing is returned.
    '''
    if geometry['type'] in ('Point', 'MultiPoint'):
        return
    
    elif geometry['type'] == 'LineString':
        for (arc_index, old_arc) in enumerate(geometry['arcs']):
            geometry['arcs'][arc_index] = len(merged_arcs)
            merged_arcs.append(old_arcs[old_arc])
    
    elif geometry['type'] == 'Polygon':
        for ring in geometry['arcs']:
            for (arc_index, old_arc) in enumerate(ring):
                ring[arc_index] = len(merged_arcs)
                merged_arcs.append(old_arcs[old_arc])
    
    elif geometry['type'] == 'MultiLineString':
        for part in geometry['arcs']:
            for (arc_index, old_arc) in enumerate(part):
                part[arc_index] = len(merged_arcs)
                merged_arcs.append(old_arcs[old_arc])
    
    elif geometry['type'] == 'MultiPolygon':
        for part in geometry['arcs']:
            for ring in part:
                for (arc_index, old_arc) in enumerate(ring):
                    ring[arc_index] = len(merged_arcs)
                    merged_arcs.append(old_arcs[old_arc])
    
    else:
        raise NotImplementedError("Can't do %s geometries" % geometry['type'])

def get_transform(bounds, size=1024):
    ''' Return a TopoJSON transform dictionary and a point-transforming function.
    
        Size is the tile size in pixels and sets the implicit output resolution.
    '''
    tx, ty = bounds[0], bounds[1]
    sx, sy = (bounds[2] - bounds[0]) / size, (bounds[3] - bounds[1]) / size
    
    def forward(lon, lat):
        ''' Transform a longitude and latitude to TopoJSON integer space.
        '''
        return int(round((lon - tx) / sx)), int(round((lat - ty) / sy))
    
    return dict(translate=(tx, ty), scale=(sx, sy)), forward

def diff_encode(line, transform):
    ''' Differentially encode a shapely linestring or ring.
    '''
    coords = [transform(x, y) for (x, y) in line.coords]
    
    pairs = zip(coords[:], coords[1:])
    diffs = [(x2 - x1, y2 - y1) for ((x1, y1), (x2, y2)) in pairs]
    
    return coords[:1] + [(x, y) for (x, y) in diffs if (x, y) != (0, 0)]

def decode(file):
    ''' Stub function to decode a TopoJSON file into a list of features.
    
        Not currently implemented, modeled on geojson.decode().
    '''
    raise NotImplementedError('topojson.decode() not yet written')

def encode(file, features, bounds, is_clipped):
    ''' Encode a list of (WKB, property dict) features into a TopoJSON stream.
    
        Also accept three-element tuples as features: (WKB, property dict, id).
    
        Geometries in the features list are assumed to be unprojected lon, lats.
        Bounds are given in geographic coordinates as (xmin, ymin, xmax, ymax).
    '''
    transform, forward = get_transform(bounds)
    geometries, arcs = list(), list()
    
    for feature in features:
        shape = loads(feature[0])
        geometry = dict(properties=feature[1])
        geometries.append(geometry)
        
        if is_clipped:
            geometry.update(dict(clipped=True))
        
        if len(feature) >= 2:
            # ID is an optional third element in the feature tuple
            geometry.update(dict(id=feature[2]))
        
        if shape.type == 'GeometryCollection':
            geometries.pop()
            continue
    
        elif shape.type == 'Point':
            geometry.update(dict(type='Point', coordinates=forward(shape.x, shape.y)))
    
        elif shape.type == 'LineString':
            geometry.update(dict(type='LineString', arcs=[len(arcs)]))
            arcs.append(diff_encode(shape, forward))
    
        elif shape.type == 'Polygon':
            geometry.update(dict(type='Polygon', arcs=[]))

            rings = [shape.exterior] + list(shape.interiors)
            
            for ring in rings:
                geometry['arcs'].append([len(arcs)])
                arcs.append(diff_encode(ring, forward))
        
        elif shape.type == 'MultiPoint':
            geometry.update(dict(type='MultiPoint', coordinates=[]))
            
            for point in shape.geoms:
                geometry['coordinates'].append(forward(point.x, point.y))
        
        elif shape.type == 'MultiLineString':
            geometry.update(dict(type='MultiLineString', arcs=[]))
            
            for line in shape.geoms:
                geometry['arcs'].append([len(arcs)])
                arcs.append(diff_encode(line, forward))
        
        elif shape.type == 'MultiPolygon':
            geometry.update(dict(type='MultiPolygon', arcs=[]))
            
            for polygon in shape.geoms:
                rings = [polygon.exterior] + list(polygon.interiors)
                polygon_arcs = []
                
                for ring in rings:
                    polygon_arcs.append([len(arcs)])
                    arcs.append(diff_encode(ring, forward))
            
                geometry['arcs'].append(polygon_arcs)
        
        else:
            raise NotImplementedError("Can't do %s geometries" % shape.type)
    
    result = {
        'type': 'Topology',
        'transform': transform,
        'objects': {
            'vectile': {
                'type': 'GeometryCollection',
                'geometries': geometries
                }
            },
        'arcs': arcs
        }
    
    json.dump(result, file, separators=(',', ':'))

def merge(file, names, config, coord):
    ''' Retrieve a list of TopoJSON tile responses and merge them into one.
    
        get_tiles() retrieves data and performs basic integrity checks.
    '''
    inputs = get_tiles(names, config, coord)
    
    output = {
        'type': 'Topology',
        'transform': inputs[0]['transform'],
        'objects': dict(),
        'arcs': list()
        }
    
    for (name, input) in zip(names, inputs):
        for (index, object) in enumerate(input['objects'].values()):
            if len(input['objects']) > 1:
                output['objects']['%(name)s-%(index)d' % locals()] = object
            else:
                output['objects'][name] = object
            
            for geometry in object['geometries']:
                update_arc_indexes(geometry, output['arcs'], input['arcs'])
    
    json.dump(output, file, separators=(',', ':'))

########NEW FILE########
__FILENAME__ = wkb
''' Shapeless handling of WKB geometries.

Use approximate_wkb() to copy an approximate well-known binary representation of
a geometry. Along the way, reduce precision of double floating point coordinates
by replacing their three least-significant bytes with nulls. The resulting WKB
will match the original at up to 26 bits of precision, close enough for
spherical mercator zoom 18 street scale geography.

Reduced-precision WKB geometries will compress as much as 50% smaller with zlib.

See also:
    http://edndoc.esri.com/arcsde/9.0/general_topics/wkb_representation.htm
    http://en.wikipedia.org/wiki/Double-precision_floating-point_format
'''

from struct import unpack
from StringIO import StringIO

#
# wkbByteOrder
#
wkbXDR = 0 # Big Endian
wkbNDR = 1 # Little Endian

#
# wkbGeometryType
#
wkbPoint = 1
wkbLineString = 2
wkbPolygon = 3
wkbMultiPoint = 4
wkbMultiLineString = 5
wkbMultiPolygon = 6
wkbGeometryCollection = 7

wkbMultis = wkbMultiPoint, wkbMultiLineString, wkbMultiPolygon, wkbGeometryCollection

def copy_byte(src, dest):
    ''' Copy an unsigned byte between files, and return it.
    '''
    byte = src.read(1)
    dest.write(byte)

    (val, ) = unpack('B', byte)
    return val

def copy_int_little(src, dest):
    ''' Copy a little-endian unsigned 4-byte int between files, and return it.
    '''
    word = src.read(4)
    dest.write(word)
    
    (val, ) = unpack('<I', word)
    return val

def copy_int_big(src, dest):
    ''' Copy a big-endian unsigned 4-byte int between files, and return it.
    '''
    word = src.read(4)
    dest.write(word)
    
    (val, ) = unpack('>I', word)
    return val

def approx_point_little(src, dest):
    ''' Copy a pair of little-endian doubles between files, truncating significands.
    '''
    xy = src.read(2 * 8)
    dest.write('\x00\x00\x00')
    dest.write(xy[-13:-8])
    dest.write('\x00\x00\x00')
    dest.write(xy[-5:])

def approx_point_big(src, dest):
    ''' Copy a pair of big-endian doubles between files, truncating significands.
    '''
    xy = src.read(2 * 8)
    dest.write(xy[:5])
    dest.write('\x00\x00\x00')
    dest.write(xy[8:13])
    dest.write('\x00\x00\x00')

def approx_line(src, dest, copy_int, approx_point):
    '''
    '''
    points = copy_int(src, dest)
    
    for i in range(points):
        approx_point(src, dest)

def approx_polygon(src, dest, copy_int, approx_point):
    '''
    '''
    rings = copy_int(src, dest)
    
    for i in range(rings):
        approx_line(src, dest, copy_int, approx_point)

def approx_geometry(src, dest):
    '''
    '''
    end = copy_byte(src, dest)
    
    if end == wkbNDR:
        copy_int = copy_int_little
        approx_point = approx_point_little
    
    elif end == wkbXDR:
        copy_int = copy_int_big
        approx_point = approx_point_big
    
    else:
        raise ValueError(end)
    
    type = copy_int(src, dest)
    
    if type == wkbPoint:
        approx_point(src, dest)
            
    elif type == wkbLineString:
        approx_line(src, dest, copy_int, approx_point)
            
    elif type == wkbPolygon:
        approx_polygon(src, dest, copy_int, approx_point)
            
    elif type in wkbMultis:
        parts = copy_int(src, dest)
        
        for i in range(parts):
            approx_geometry(src, dest)
            
    else:
        raise ValueError(type)

def approximate_wkb(wkb_in):
    ''' Return an approximation of the input WKB with lower-precision geometry.
    '''
    input, output = StringIO(wkb_in), StringIO()
    approx_geometry(input, output)
    wkb_out = output.getvalue()

    assert len(wkb_in) == input.tell(), 'The whole WKB was not processed'
    assert len(wkb_in) == len(wkb_out), 'The output WKB is the wrong length'
    
    return wkb_out

if __name__ == '__main__':

    from random import random
    from math import hypot

    from shapely.wkb import loads
    from shapely.geometry import *
    
    point1 = Point(random(), random())
    point2 = loads(approximate_wkb(point1.wkb))
    
    assert hypot(point1.x - point2.x, point1.y - point2.y) < 1e-8
    
    
    
    point1 = Point(random(), random())
    point2 = Point(random(), random())
    point3 = point1.union(point2)
    point4 = loads(approximate_wkb(point3.wkb))
    
    assert hypot(point3.geoms[0].x - point4.geoms[0].x, point3.geoms[0].y - point4.geoms[0].y) < 1e-8
    assert hypot(point3.geoms[1].x - point4.geoms[1].x, point3.geoms[1].y - point4.geoms[1].y) < 1e-8
    
    
    
    line1 = Point(random(), random()).buffer(1 + random(), 3).exterior
    line2 = loads(approximate_wkb(line1.wkb))
    
    assert abs(1. - line2.length / line1.length) < 1e-8
    
    
    
    line1 = Point(random(), random()).buffer(1 + random(), 3).exterior
    line2 = Point(random(), random()).buffer(1 + random(), 3).exterior
    line3 = MultiLineString([line1, line2])
    line4 = loads(approximate_wkb(line3.wkb))
    
    assert abs(1. - line4.length / line3.length) < 1e-8
    
    
    
    poly1 = Point(random(), random()).buffer(1 + random(), 3)
    poly2 = loads(approximate_wkb(poly1.wkb))
    
    assert abs(1. - poly2.area / poly1.area) < 1e-8
    
    
    
    poly1 = Point(random(), random()).buffer(2 + random(), 3)
    poly2 = Point(random(), random()).buffer(1 + random(), 3)
    poly3 = poly1.difference(poly2)
    poly4 = loads(approximate_wkb(poly3.wkb))
    
    assert abs(1. - poly4.area / poly3.area) < 1e-8
    
    
    
    poly1 = Point(random(), 2 + random()).buffer(1 + random(), 3)
    poly2 = Point(2 + random(), random()).buffer(1 + random(), 3)
    poly3 = poly1.union(poly2)
    poly4 = loads(approximate_wkb(poly3.wkb))
    
    assert abs(1. - poly4.area / poly3.area) < 1e-8

########NEW FILE########
__FILENAME__ = Mapnik
""" Mapnik Providers.

ImageProvider is known as "mapnik" in TileStache config, GridProvider is
known as "mapnik grid". Both require Mapnik to be installed; Grid requires
Mapnik 2.0.0 and above.
"""
from __future__ import absolute_import
from time import time
from os.path import exists
from thread import allocate_lock
from urlparse import urlparse, urljoin
from itertools import count
from glob import glob
from tempfile import mkstemp
from urllib import urlopen

import os
import logging
import json

# We enabled absolute_import because case insensitive filesystems
# cause this file to be loaded twice (the name of this file
# conflicts with the name of the module we want to import).
# Forcing absolute imports fixes the issue.

try:
    import mapnik
except ImportError:
    # can still build documentation
    pass

from TileStache.Core import KnownUnknown
from TileStache.Geography import getProjectionByName

try:
    from PIL import Image
except ImportError:
    # On some systems, PIL.Image is known as Image.
    import Image

if 'mapnik' in locals():
    _version = hasattr(mapnik, 'mapnik_version') and mapnik.mapnik_version() or 701
    
    if _version >= 20000:
        Box2d = mapnik.Box2d
    else:
        Box2d = mapnik.Envelope

global_mapnik_lock = allocate_lock()

class ImageProvider:
    """ Built-in Mapnik provider. Renders map images from Mapnik XML files.
    
        This provider is identified by the name "mapnik" in the TileStache config.
        
        Arguments:
        
        - mapfile (required)
            Local file path to Mapnik XML file.
    
        - fonts (optional)
            Local directory path to *.ttf font files.
    
        More information on Mapnik and Mapnik XML:
        - http://mapnik.org
        - http://trac.mapnik.org/wiki/XMLGettingStarted
        - http://trac.mapnik.org/wiki/XMLConfigReference
    """
    
    def __init__(self, layer, mapfile, fonts=None):
        """ Initialize Mapnik provider with layer and mapfile.
            
            XML mapfile keyword arg comes from TileStache config,
            and is an absolute path by the time it gets here.
        """
        maphref = urljoin(layer.config.dirpath, mapfile)
        scheme, h, path, q, p, f = urlparse(maphref)
        
        if scheme in ('file', ''):
            self.mapfile = path
        else:
            self.mapfile = maphref
        
        self.layer = layer
        self.mapnik = None
        
        engine = mapnik.FontEngine.instance()
        
        if fonts:
            fontshref = urljoin(layer.config.dirpath, fonts)
            scheme, h, path, q, p, f = urlparse(fontshref)
            
            if scheme not in ('file', ''):
                raise Exception('Fonts from "%s" can\'t be used by Mapnik' % fontshref)
        
            for font in glob(path.rstrip('/') + '/*.ttf'):
                engine.register_font(str(font))

    @staticmethod
    def prepareKeywordArgs(config_dict):
        """ Convert configured parameters to keyword args for __init__().
        """
        kwargs = {'mapfile': config_dict['mapfile']}

        if 'fonts' in config_dict:
            kwargs['fonts'] = config_dict['fonts']
        
        return kwargs
    
    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        """
        """
        start_time = time()
        
        #
        # Mapnik can behave strangely when run in threads, so place a lock on the instance.
        #
        if global_mapnik_lock.acquire():
            try:
                if self.mapnik is None:
                    self.mapnik = get_mapnikMap(self.mapfile)
                    logging.debug('TileStache.Mapnik.ImageProvider.renderArea() %.3f to load %s', time() - start_time, self.mapfile)

                self.mapnik.width = width
                self.mapnik.height = height
                self.mapnik.zoom_to_box(Box2d(xmin, ymin, xmax, ymax))
            
                img = mapnik.Image(width, height)
                mapnik.render(self.mapnik, img) 
            except:
                self.mapnik = None
                raise
            finally:
                # always release the lock
                global_mapnik_lock.release()

        img = Image.fromstring('RGBA', (width, height), img.tostring())
        
        logging.debug('TileStache.Mapnik.ImageProvider.renderArea() %dx%d in %.3f from %s', width, height, time() - start_time, self.mapfile)
    
        return img

class GridProvider:
    """ Built-in UTF Grid provider. Renders JSON raster objects from Mapnik.
    
        This provider is identified by the name "mapnik grid" in the
        Tilestache config, and uses Mapnik 2.0 (and above) to generate
        JSON UTF grid responses.
        
        Sample configuration for a single grid layer:

          "provider":
          {
            "name": "mapnik grid",
            "mapfile": "world_merc.xml", 
            "fields": ["NAME", "POP2005"]
          }
    
        Sample configuration for multiple overlaid grid layers:

          "provider":
          {
            "name": "mapnik grid",
            "mapfile": "world_merc.xml",
            "layers":
            [
              [1, ["NAME"]],
              [0, ["NAME", "POP2005"]],
              [0, null],
              [0, []]
            ]
          }
    
        Arguments:
        
        - mapfile (required)
          Local file path to Mapnik XML file.
        
        - fields (optional)
          Array of field names to return in the response, defaults to all.
          An empty list will return no field names, while a value of null is
          equivalent to all.
        
        - layer index (optional)
          Which layer from the mapfile to render, defaults to 0 (first layer).
        
        - layers (optional)
          Ordered list of (layer index, fields) to combine; if provided
          layers overrides both layer index and fields arguments.
          An empty fields list will return no field names, while a value of null 
          is equivalent to all fields.
 
        - scale (optional)
          Scale factor of output raster, defaults to 4 (64x64).
        
        - layer id key (optional)
          If set, each item in the 'data' property will have its source mapnik
          layer name added, keyed by this value. Useful for distingushing
          between data items.
        
        Information and examples for UTF Grid:
        - https://github.com/mapbox/utfgrid-spec/blob/master/1.2/utfgrid.md
        - http://mapbox.github.com/wax/interaction-leaf.html
    """
    def __init__(self, layer, mapfile, fields=None, layers=None, layer_index=0, scale=4, layer_id_key=None):
        """ Initialize Mapnik grid provider with layer and mapfile.
            
            XML mapfile keyword arg comes from TileStache config,
            and is an absolute path by the time it gets here.
        """
        self.mapnik = None
        self.layer = layer

        maphref = urljoin(layer.config.dirpath, mapfile)
        scheme, h, path, q, p, f = urlparse(maphref)

        if scheme in ('file', ''):
            self.mapfile = path
        else:
            self.mapfile = maphref

        self.scale = scale
        self.layer_id_key = layer_id_key
        
        if layers:
            self.layers = layers
        else:
            self.layers = [[layer_index or 0, fields]]

    @staticmethod
    def prepareKeywordArgs(config_dict):
        """ Convert configured parameters to keyword args for __init__().
        """
        kwargs = {'mapfile': config_dict['mapfile']}

        for key in ('fields', 'layers', 'layer_index', 'scale', 'layer_id_key'):
            if key in config_dict:
                kwargs[key] = config_dict[key]
        
        return kwargs
    
    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        """
        """
        start_time = time()
        
        #
        # Mapnik can behave strangely when run in threads, so place a lock on the instance.
        #
        if global_mapnik_lock.acquire():
            try:
                if self.mapnik is None:
                    self.mapnik = get_mapnikMap(self.mapfile)
                    logging.debug('TileStache.Mapnik.GridProvider.renderArea() %.3f to load %s', time() - start_time, self.mapfile)

                self.mapnik.width = width
                self.mapnik.height = height
                self.mapnik.zoom_to_box(Box2d(xmin, ymin, xmax, ymax))
            
                if self.layer_id_key is not None:
                    grids = []
    
                    for (index, fields) in self.layers:
                        datasource = self.mapnik.layers[index].datasource
                        fields = (type(fields) is list) and map(str, fields) or datasource.fields()
                    
                        grid = mapnik.render_grid(self.mapnik, index, resolution=self.scale, fields=fields)
    
                        for key in grid['data']:
                            grid['data'][key][self.layer_id_key] = self.mapnik.layers[index].name
    
                        grids.append(grid)
        
                    # global_mapnik_lock.release()
                    outgrid = reduce(merge_grids, grids)
           
                else:
                    grid = mapnik.Grid(width, height)
    
                    for (index, fields) in self.layers:
                        datasource = self.mapnik.layers[index].datasource
                        fields = (type(fields) is list) and map(str, fields) or datasource.fields()
    
                        mapnik.render_layer(self.mapnik, grid, layer=index, fields=fields)
    
                    # global_mapnik_lock.release()
                    outgrid = grid.encode('utf', resolution=self.scale, features=True)
            except:
                self.mapnik = None
                raise
            finally:
                global_mapnik_lock.release()

        logging.debug('TileStache.Mapnik.GridProvider.renderArea() %dx%d at %d in %.3f from %s', width, height, self.scale, time() - start_time, self.mapfile)

        return SaveableResponse(outgrid, self.scale)

    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.

            This only accepts "json".
        """
        if extension.lower() != 'json':
            raise KnownUnknown('MapnikGrid only makes .json tiles, not "%s"' % extension)

        return 'application/json; charset=utf-8', 'JSON'

class SaveableResponse:
    """ Wrapper class for JSON response that makes it behave like a PIL.Image object.

        TileStache.getTile() expects to be able to save one of these to a buffer.
    """
    def __init__(self, content, scale):
        self.content = content
        self.scale = scale

    def save(self, out, format):
        if format != 'JSON':
            raise KnownUnknown('MapnikGrid only saves .json tiles, not "%s"' % format)

        bytes = json.dumps(self.content, ensure_ascii=False).encode('utf-8')
        out.write(bytes)
    
    def crop(self, bbox):
        """ Return a cropped grid response.
        """
        minchar, minrow, maxchar, maxrow = [v/self.scale for v in bbox]

        keys, data = self.content['keys'], self.content.get('data', None)
        grid = [row[minchar:maxchar] for row in self.content['grid'][minrow:maxrow]]
        
        cropped = dict(keys=keys, data=data, grid=grid)
        return SaveableResponse(cropped, self.scale)

def merge_grids(grid1, grid2):
    """ Merge two UTF Grid objects.
    """
    #
    # Concatenate keys and data, assigning new indexes along the way.
    #

    keygen, outkeys, outdata = count(1), [], dict()
    
    for ingrid in [grid1, grid2]:
        for (index, key) in enumerate(ingrid['keys']):
            if key not in ingrid['data']:
                outkeys.append('')
                continue
        
            outkey = '%d' % keygen.next()
            outkeys.append(outkey)
    
            datum = ingrid['data'][key]
            outdata[outkey] = datum
    
    #
    # Merge the two grids, one on top of the other.
    #
    
    offset, outgrid = len(grid1['keys']), []
    
    def newchar(char1, char2):
        """ Return a new encoded character based on two inputs.
        """
        id1, id2 = decode_char(char1), decode_char(char2)
        
        if grid2['keys'][id2] == '':
            # transparent pixel, use the bottom character
            return encode_id(id1)
        
        else:
            # opaque pixel, use the top character
            return encode_id(id2 + offset)
    
    for (row1, row2) in zip(grid1['grid'], grid2['grid']):
        outrow = [newchar(c1, c2) for (c1, c2) in zip(row1, row2)]
        outgrid.append(''.join(outrow))
    
    return dict(keys=outkeys, data=outdata, grid=outgrid)

def encode_id(id):
    id += 32
    if id >= 34:
        id = id + 1
    if id >= 92:
        id = id + 1
    if id > 127:
        return unichr(id)
    return chr(id)

def decode_char(char):
    id = ord(char)
    if id >= 93:
        id = id - 1
    if id >= 35:
        id = id - 1
    return id - 32

def get_mapnikMap(mapfile):
    """ Get a new mapnik.Map instance for a mapfile
    """
    mmap = mapnik.Map(0, 0)
    
    if exists(mapfile):
        mapnik.load_map(mmap, str(mapfile))
    
    else:
        handle, filename = mkstemp()
        os.write(handle, urlopen(mapfile).read())
        os.close(handle)

        mapnik.load_map(mmap, filename)
        os.unlink(filename)
    
    return mmap

########NEW FILE########
__FILENAME__ = MBTiles
""" Support for MBTiles file format, version 1.1.

MBTiles (http://mbtiles.org) is a specification for storing tiled map data in
SQLite databases for immediate use and for transfer. The files are designed for
portability of thousands, hundreds of thousands, or even millions of standard
map tile images in a single file.

This makes it easy to manage and share map tiles.

Read the spec:
    https://github.com/mapbox/mbtiles-spec/blob/master/1.1/spec.md

MBTiles files generated by other applications such as Tilemill or Arc2Earth
can be used as data sources for the MBTiles Provider.

Example configuration:

  {
    "cache": { ... }.
    "layers":
    {
      "roads":
      {
        "provider":
        {
          "name": "mbtiles",
          "tileset": "collection.mbtiles"
        }
      }
    }
  }

MBTiles provider parameters:

  tileset:
    Required local file path to MBTiles tileset file, a SQLite 3 database file.
"""
from urlparse import urlparse, urljoin
from os.path import exists

# Heroku is missing standard python's sqlite3 package, so this will ImportError.
from sqlite3 import connect as _connect

from ModestMaps.Core import Coordinate

def create_tileset(filename, name, type, version, description, format, bounds=None):
    """ Create a tileset 1.1 with the given filename and metadata.
    
        From the specification:

        The metadata table is used as a key/value store for settings.
        Five keys are required:

          name:
            The plain-english name of the tileset.
    
          type:
            overlay or baselayer
          
          version:
            The version of the tileset, as a plain number.
    
          description:
            A description of the layer as plain text.
          
          format:
            The image file format of the tile data: png or jpg or json
        
        One row in metadata is suggested and, if provided, may enhance performance:

          bounds:
            The maximum extent of the rendered map area. Bounds must define
            an area covered by all zoom levels. The bounds are represented in
            WGS:84 - latitude and longitude values, in the OpenLayers Bounds
            format - left, bottom, right, top. Example of the full earth:
            -180.0,-85,180,85.
    """
    if format not in ('png', 'jpg',' json'):
        raise Exception('Format must be one of "png" or "jpg" or "json", not "%s"' % format)
    
    db = _connect(filename)
    
    db.execute('CREATE TABLE metadata (name TEXT, value TEXT, PRIMARY KEY (name))')
    db.execute('CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)')
    db.execute('CREATE UNIQUE INDEX coord ON tiles (zoom_level, tile_column, tile_row)')
    
    db.execute('INSERT INTO metadata VALUES (?, ?)', ('name', name))
    db.execute('INSERT INTO metadata VALUES (?, ?)', ('type', type))
    db.execute('INSERT INTO metadata VALUES (?, ?)', ('version', version))
    db.execute('INSERT INTO metadata VALUES (?, ?)', ('description', description))
    db.execute('INSERT INTO metadata VALUES (?, ?)', ('format', format))
    
    if bounds is not None:
        db.execute('INSERT INTO metadata VALUES (?, ?)', ('bounds', bounds))
    
    db.commit()
    db.close()

def tileset_exists(filename):
    """ Return true if the tileset exists and appears to have the right tables.
    """
    if not exists(filename):
        return False
    
    # this always works
    db = _connect(filename)
    db.text_factory = bytes
    
    try:
        db.execute('SELECT name, value FROM metadata LIMIT 1')
        db.execute('SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles LIMIT 1')
    except:
        return False
    
    return True

def tileset_info(filename):
    """ Return name, type, version, description, format, and bounds for a tileset.
    
        Returns None if tileset does not exist.
    """
    if not tileset_exists(filename):
        return None
    
    db = _connect(filename)
    db.text_factory = bytes
    
    info = []
    
    for key in ('name', 'type', 'version', 'description', 'format', 'bounds'):
        value = db.execute('SELECT value FROM metadata WHERE name = ?', (key, )).fetchone()
        info.append(value and value[0] or None)
    
    return info

def list_tiles(filename):
    """ Get a list of tile coordinates.
    """
    db = _connect(filename)
    db.text_factory = bytes
    
    tiles = db.execute('SELECT tile_row, tile_column, zoom_level FROM tiles')
    tiles = (((2**z - 1) - y, x, z) for (y, x, z) in tiles) # Hello, Paul Ramsey.
    tiles = [Coordinate(row, column, zoom) for (row, column, zoom) in tiles]
    
    return tiles

def get_tile(filename, coord):
    """ Retrieve the mime-type and raw content of a tile by coordinate.
    
        If the tile does not exist, None is returned for the content.
    """
    db = _connect(filename)
    db.text_factory = bytes
    
    formats = {'png': 'image/png', 'jpg': 'image/jpeg', 'json': 'application/json', None: None}
    format = db.execute("SELECT value FROM metadata WHERE name='format'").fetchone()
    format = format and format[0] or None
    mime_type = formats[format]
    
    tile_row = (2**coord.zoom - 1) - coord.row # Hello, Paul Ramsey.
    q = 'SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?'
    content = db.execute(q, (coord.zoom, coord.column, tile_row)).fetchone()
    content = content and content[0] or None

    return mime_type, content

def delete_tile(filename, coord):
    """ Delete a tile by coordinate.
    """
    db = _connect(filename)
    db.text_factory = bytes
    
    tile_row = (2**coord.zoom - 1) - coord.row # Hello, Paul Ramsey.
    q = 'DELETE FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?'
    db.execute(q, (coord.zoom, coord.column, tile_row))

def put_tile(filename, coord, content):
    """
    """
    db = _connect(filename)
    db.text_factory = bytes
    
    tile_row = (2**coord.zoom - 1) - coord.row # Hello, Paul Ramsey.
    q = 'REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?, ?, ?, ?)'
    db.execute(q, (coord.zoom, coord.column, tile_row, buffer(content)))

    db.commit()
    db.close()

class Provider:
    """ MBTiles provider.
    
        See module documentation for explanation of constructor arguments.
    """
    def __init__(self, layer, tileset):
        """
        """
        sethref = urljoin(layer.config.dirpath, tileset)
        scheme, h, path, q, p, f = urlparse(sethref)
        
        if scheme not in ('file', ''):
            raise Exception('Bad scheme in MBTiles provider, must be local file: "%s"' % scheme)
        
        self.tileset = path
        self.layer = layer
    
    @staticmethod
    def prepareKeywordArgs(config_dict):
        """ Convert configured parameters to keyword args for __init__().
        """
        return {'tileset': config_dict['tileset']}
    
    def renderTile(self, width, height, srs, coord):
        """ Retrieve a single tile, return a TileResponse instance.
        """
        mime_type, content = get_tile(self.tileset, coord)
        formats = {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'application/json': 'JSON', None: None}
        return TileResponse(formats[mime_type], content)

    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.
        
            This only accepts "png" or "jpg" or "json".
        """
        if extension.lower() == 'json':
            return 'application/json', 'JSON'
        
        elif extension.lower() == 'png':
            return 'image/png', 'PNG'

        elif extension.lower() == 'jpg':
            return 'image/jpg', 'JPEG'
        
        else:
            raise KnownUnknown('MBTiles only makes .png and .jpg and .json tiles, not "%s"' % extension)

class TileResponse:
    """ Wrapper class for tile response that makes it behave like a PIL.Image object.
    
        TileStache.getTile() expects to be able to save one of these to a buffer.
        
        Constructor arguments:
        - format: 'PNG' or 'JPEG'.
        - content: Raw response bytes.
    """
    def __init__(self, format, content):
        self.format = format
        self.content = content
    
    def save(self, out, format):
        if self.format is not None and format != self.format:
            raise Exception('Requested format "%s" does not match tileset format "%s"' % (format, self.format))

        out.write(self.content)

class Cache:
    """ Cache provider for writing to MBTiles files.
    
        This class is not exposed as a normal cache provider for TileStache,
        because MBTiles has restrictions on file formats that aren't quite
        compatible with some of the looser assumptions made by TileStache.
        Instead, this cache provider is provided for use with the script
        tilestache-seed.py, which can be called with --to-mbtiles option
        to write cached tiles to a new tileset.
    """
    def __init__(self, filename, format, name):
        """
        """
        self.filename = filename
        
        if not tileset_exists(filename):
            create_tileset(filename, name, 'baselayer', '0', '', format.lower())
    
    def lock(self, layer, coord, format):
        return
    
    def unlock(self, layer, coord, format):
        return
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile.
        """
        delete_tile(self.filename, coord)
        
    def read(self, layer, coord, format):
        """ Return raw tile content from tileset.
        """
        return get_tile(self.filename, coord)[1]
    
    def save(self, body, layer, coord, format):
        """ Write raw tile content to tileset.
        """
        put_tile(self.filename, coord, body)

########NEW FILE########
__FILENAME__ = Memcache
""" Caches tiles to Memcache.

Requires python-memcached:
  http://pypi.python.org/pypi/python-memcached

Example configuration:

  "cache": {
    "name": "Memcache",
    "servers": ["127.0.0.1:11211"],
    "revision": 0,
    "key prefix": "unique-id"
  }

Memcache cache parameters:

  servers
    Optional array of servers, list of "{host}:{port}" pairs.
    Defaults to ["127.0.0.1:11211"] if omitted.

  revision
    Optional revision number for mass-expiry of cached tiles
    regardless of lifespan. Defaults to 0.

  key prefix
    Optional string to prepend to Memcache generated key.
    Useful when running multiple instances of TileStache
    that share the same Memcache instance to avoid key
    collisions. The key prefix will be prepended to the
    key name. Defaults to "".
    

"""
from __future__ import absolute_import
from time import time as _time, sleep as _sleep

# We enabled absolute_import because case insensitive filesystems
# cause this file to be loaded twice (the name of this file
# conflicts with the name of the module we want to import).
# Forcing absolute imports fixes the issue.

try:
    from memcache import Client
except ImportError:
    # at least we can build the documentation
    pass

def tile_key(layer, coord, format, rev, key_prefix):
    """ Return a tile key string.
    """
    name = layer.name()
    tile = '%(zoom)d/%(column)d/%(row)d' % coord.__dict__
    return str('%(key_prefix)s/%(rev)s/%(name)s/%(tile)s.%(format)s' % locals())

class Cache:
    """
    """
    def __init__(self, servers=['127.0.0.1:11211'], revision=0, key_prefix=''):
        self.servers = servers
        self.revision = revision
        self.key_prefix = key_prefix

    def lock(self, layer, coord, format):
        """ Acquire a cache lock for this tile.
        
            Returns nothing, but blocks until the lock has been acquired.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, format, self.revision, self.key_prefix)
        due = _time() + layer.stale_lock_timeout
        
        try:
            while _time() < due:
                if mem.add(key+'-lock', 'locked.', layer.stale_lock_timeout):
                    return
                
                _sleep(.2)
            
            mem.set(key+'-lock', 'locked.', layer.stale_lock_timeout)
            return

        finally:
            mem.disconnect_all()
        
    def unlock(self, layer, coord, format):
        """ Release a cache lock for this tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, format, self.revision, self.key_prefix)
        
        mem.delete(key+'-lock')
        mem.disconnect_all()
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, format, self.revision, self.key_prefix)
        
        mem.delete(key)
        mem.disconnect_all()
        
    def read(self, layer, coord, format):
        """ Read a cached tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, format, self.revision, self.key_prefix)
        
        value = mem.get(key)
        mem.disconnect_all()
        
        return value
        
    def save(self, body, layer, coord, format):
        """ Save a cached tile.
        """
        mem = Client(self.servers)
        key = tile_key(layer, coord, format, self.revision, self.key_prefix)
        
        mem.set(key, body, layer.cache_lifespan or 0)
        mem.disconnect_all()

########NEW FILE########
__FILENAME__ = Pixels
""" Support for 8-bit image palettes in PNG output.

PNG images can be significantly cut down in size by using a color look-up table.
TileStache layers support Adobe Photoshop's .act file format for PNG output,
and can be referenced in a layer configuration file like this:

    "osm":
    {
      "provider": {"name": "proxy", "provider": "OPENSTREETMAP"},
      "png options": {"palette": "http://tilestache.org/example-palette-openstreetmap-mapnik.act"}
    }

The example OSM palette above is a real file with a 32 color (5 bit) selection
of colors appropriate for use with OpenStreetMap's default Mapnik cartography.

To generate an .act file, convert an existing image in Photoshop to indexed
color, and access the color table under Image -> Mode -> Color Table. Saving
the color table results in a usable .act file, internally structured as a
fixed-size 772-byte table with 256 3-byte RGB triplets, followed by a two-byte
unsigned int with the number of defined colors (may be less than 256) and a
finaly two-byte unsigned int with the optional index of a transparent color
in the lookup table. If the final byte is 0xFFFF, there is no transparency.
"""
from struct import unpack, pack
from math import sqrt, ceil, log
from urllib import urlopen
from operator import add

try:
    from PIL import Image
except ImportError:
    # On some systems, PIL.Image is known as Image.
    import Image

def load_palette(file_href):
    """ Load colors from a Photoshop .act file, return palette info.
    
        Return tuple is an array of [ (r, g, b), (r, g, b), ... ],
        bit depth of the palette, and a numeric transparency index
        or None if not defined.
    """
    bytes = urlopen(file_href).read()
    count, t_index = unpack('!HH', bytes[768:768+4])
    t_index = (t_index <= 0xff) and t_index or None
    
    palette = []
    
    for offset in range(0, count):
        if offset == t_index:
            rgb = 0xff, 0x99, 0x00
        else:
            rgb = unpack('!BBB', bytes[offset*3:(offset + 1)*3])
        
        palette.append(rgb)
    
    bits = int(ceil(log(len(palette)) / log(2)))
    
    return palette, bits, t_index

def palette_color(r, g, b, palette, t_index):
    """ Return best palette match index.

        Find the closest color in the palette based on dumb euclidian distance,
        assign its index in the palette to a mapping from 24-bit color tuples.
    """
    distances = [(r - _r)**2 + (g - _g)**2 + (b - _b)**2 for (_r, _g, _b) in palette]
    distances = map(sqrt, distances)
    
    if t_index is not None:
        distances = distances[:t_index] + distances[t_index+1:]
    
    return distances.index(min(distances))

def apply_palette(image, palette, t_index):
    """ Apply a palette array to an image, return a new image.
    """
    image = image.convert('RGBA')
    pixels = image.tostring()
    t_value = (t_index in range(256)) and pack('!B', t_index) or None
    mapping = {}
    indexes = []
    
    for offset in range(0, len(pixels), 4):
        r, g, b, a = unpack('!BBBB', pixels[offset:offset+4])
        
        if a < 0x80 and t_value is not None:
            # Sufficiently transparent
            indexes.append(t_value)
            continue
        
        try:
            indexes.append(mapping[(r, g, b)])

        except KeyError:
            # Never seen this color
            mapping[(r, g, b)] = pack('!B', palette_color(r, g, b, palette, t_index))
        
        else:
            continue
        
        indexes.append(mapping[(r, g, b)])

    output = Image.fromstring('P', image.size, ''.join(indexes))
    bits = int(ceil(log(len(palette)) / log(2)))
    
    palette += [(0, 0, 0)] * (256 - len(palette))
    palette = reduce(add, palette)
    output.putpalette(palette)
    
    return output

def apply_palette256(image):
    """ Get PIL to generate and apply an optimum 256 color palette to the given image and return it
    """
    return image.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=256, dither=Image.NONE)

########NEW FILE########
__FILENAME__ = Providers
""" The provider bits of TileStache.

A Provider is the part of TileStache that actually renders imagery. A few default
providers are found here, but it's possible to define your own and pull them into
TileStache dynamically by class name.

Built-in providers:
- mapnik (Mapnik.ImageProvider)
- proxy (Proxy)
- vector (TileStache.Vector.Provider)
- url template (UrlTemplate)
- mbtiles (TileStache.MBTiles.Provider)
- mapnik grid (Mapnik.GridProvider)

Example built-in provider, for JSON configuration file:

    "layer-name": {
        "provider": {"name": "mapnik", "mapfile": "style.xml"},
        ...
    }

Example external provider, for JSON configuration file:

    "layer-name": {
        "provider": {"class": "Module:Classname", "kwargs": {"frob": "yes"}},
        ...
    }

- The "class" value is split up into module and classname, and dynamically
  included. If this doesn't work for some reason, TileStache will fail loudly
  to let you know.
- The "kwargs" value is fed to the class constructor as a dictionary of keyword
  args. If your defined class doesn't accept any of these keyword arguments,
  TileStache will throw an exception.

A provider must offer one of two methods for rendering map areas.

The renderTile() method draws a single tile at a time, and has these arguments:

- width, height: in pixels
- srs: projection as Proj4 string.
  "+proj=longlat +ellps=WGS84 +datum=WGS84" is an example, 
  see http://spatialreference.org for more.
- coord: Coordinate object representing a single tile.

The renderArea() method draws a variably-sized area, and is used when drawing
metatiles. It has these arguments:

- width, height: in pixels
- srs: projection as Proj4 string.
  "+proj=longlat +ellps=WGS84 +datum=WGS84" is an example, 
  see http://spatialreference.org for more.
- xmin, ymin, xmax, ymax: coordinates of bounding box in projected coordinates.
- zoom: zoom level of final map. Technically this can be derived from the other
  arguments, but that's a hassle so we'll pass it in explicitly.
  
A provider may offer a method for custom response type, getTypeByExtension().
This method accepts a single argument, a filename extension string (e.g. "png",
"json", etc.) and returns a tuple with twon strings: a mime-type and a format.
Note that for image and non-image tiles alike, renderArea() and renderTile()
methods on a provider class must return a object with a save() method that
can accept a file-like object and a format name, e.g. this should word:
    
    provder.renderArea(...).save(fp, "TEXT")

... if "TEXT" is a valid response format according to getTypeByExtension().

Non-image providers and metatiles do not mix.

For an example of a non-image provider, see TileStache.Vector.Provider.
"""

import os
import logging

from StringIO import StringIO
from string import Template
import urllib2
import urllib

try:
    from PIL import Image
except ImportError:
    # On some systems, PIL.Image is known as Image.
    import Image

import ModestMaps
from ModestMaps.Core import Point, Coordinate

import Geography

# This import should happen inside getProviderByName(), but when testing
# on Mac OS X features are missing from output. Wierd-ass C libraries...
try:
    from . import Vector
except ImportError:
    pass

# Already deprecated; provided for temporary backward-compatibility with
# old location of Mapnik provider. TODO: remove in next major version.
try:
    from .Mapnik import ImageProvider as Mapnik
except ImportError:
    pass

def getProviderByName(name):
    """ Retrieve a provider object by name.
    
        Raise an exception if the name doesn't work out.
    """
    if name.lower() == 'mapnik':
        from . import Mapnik
        return Mapnik.ImageProvider

    elif name.lower() == 'proxy':
        return Proxy

    elif name.lower() == 'url template':
        return UrlTemplate

    elif name.lower() == 'vector':
        from . import Vector
        return Vector.Provider

    elif name.lower() == 'mbtiles':
        from . import MBTiles
        return MBTiles.Provider

    elif name.lower() == 'mapnik grid':
        from . import Mapnik
        return Mapnik.GridProvider

    elif name.lower() == 'sandwich':
        from . import Sandwich
        return Sandwich.Provider

    raise Exception('Unknown provider name: "%s"' % name)

class Verbatim:
    ''' Wrapper for PIL.Image that saves raw input bytes if modes and formats match.
    '''
    def __init__(self, bytes):
        self.buffer = StringIO(bytes)
        self.format = None
        self._image = None
        
        #
        # Guess image format based on magic number, if possible.
        # http://www.astro.keele.ac.uk/oldusers/rno/Computing/File_magic.html
        #
        magic = {
            '\x89\x50\x4e\x47': 'PNG',
            '\xff\xd8\xff\xe0': 'JPEG',
            '\x47\x49\x46\x38': 'GIF',
            '\x47\x49\x46\x38': 'GIF',
            '\x4d\x4d\x00\x2a': 'TIFF',
            '\x49\x49\x2a\x00': 'TIFF'
            }
        
        if bytes[:4] in magic:
            self.format = magic[bytes[:4]]

        else:
            self.format = self.image().format
    
    def image(self):
        ''' Return a guaranteed instance of PIL.Image.
        '''
        if self._image is None:
            self._image = Image.open(self.buffer)
        
        return self._image
    
    def convert(self, mode):
        if mode == self.image().mode:
            return self
        else:
            return self.image().convert(mode)

    def crop(self, bbox):
        return self.image().crop(bbox)
    
    def save(self, output, format):
        if format == self.format:
            output.write(self.buffer.getvalue())
        else:
            self.image().save(output, format)

class Proxy:
    """ Proxy provider, to pass through and cache tiles from other places.
    
        This provider is identified by the name "proxy" in the TileStache config.
        
        Additional arguments:
        
        - url (optional)
            URL template for remote tiles, for example:
            "http://tile.openstreetmap.org/{Z}/{X}/{Y}.png"
        - provider (optional)
            Provider name string from Modest Maps built-ins.
            See ModestMaps.builtinProviders.keys() for a list.
            Example: "OPENSTREETMAP".
        - timeout (optional)
            Defines a timeout in seconds for the request.
            If not defined, the global default timeout setting will be used.


        Either url or provider is required. When both are present, url wins.
        
        Example configuration:
        
        {
            "name": "proxy",
            "url": "http://tile.openstreetmap.org/{Z}/{X}/{Y}.png"
        }
    """
    def __init__(self, layer, url=None, provider_name=None, timeout=None):
        """ Initialize Proxy provider with layer and url.
        """
        if url:
            self.provider = ModestMaps.Providers.TemplatedMercatorProvider(url)

        elif provider_name:
            if provider_name in ModestMaps.builtinProviders:
                self.provider = ModestMaps.builtinProviders[provider_name]()
            else:
                raise Exception('Unkown Modest Maps provider: "%s"' % provider_name)

        else:
            raise Exception('Missing required url or provider parameter to Proxy provider')

        self.timeout = timeout

    @staticmethod
    def prepareKeywordArgs(config_dict):
        """ Convert configured parameters to keyword args for __init__().
        """
        kwargs = dict()

        if 'url' in config_dict:
            kwargs['url'] = config_dict['url']

        if 'provider' in config_dict:
            kwargs['provider_name'] = config_dict['provider']

        if 'timeout' in config_dict:
            kwargs['timeout'] = config_dict['timeout']

        return kwargs

    def renderTile(self, width, height, srs, coord):
        """
        """
        img = None
        urls = self.provider.getTileUrls(coord)

        # Explicitly tell urllib2 to get no proxies
        proxy_support = urllib2.ProxyHandler({})
        url_opener = urllib2.build_opener(proxy_support)

        for url in urls:
            body = url_opener.open(url, timeout=self.timeout).read()
            tile = Verbatim(body)

            if len(urls) == 1:
                #
                # if there is only one URL, don't bother
                # with PIL's non-Porter-Duff alpha channeling.
                #
                return tile
            elif img is None:
                #
                # for many URLs, paste them to a new image.
                #
                img = Image.new('RGBA', (width, height))

            img.paste(tile, (0, 0), tile)

        return img

class UrlTemplate:
    """ Built-in URL Template provider. Proxies map images from WMS servers.
        
        This provider is identified by the name "url template" in the TileStache config.
        
        Additional arguments:
        
        - template (required)
            String with substitutions suitable for use in string.Template.

        - referer (optional)
            String to use in the "Referer" header when making HTTP requests.

        - source projection (optional)
            Projection to transform coordinates into before making request
        - timeout (optional)
            Defines a timeout in seconds for the request.
            If not defined, the global default timeout setting will be used.

        More on string substitutions:
        - http://docs.python.org/library/string.html#template-strings
    """

    def __init__(self, layer, template, referer=None, source_projection=None,
                 timeout=None):
        """ Initialize a UrlTemplate provider with layer and template string.
        
            http://docs.python.org/library/string.html#template-strings
        """
        self.layer = layer
        self.template = Template(template)
        self.referer = referer
        self.source_projection = source_projection
        self.timeout = timeout

    @staticmethod
    def prepareKeywordArgs(config_dict):
        """ Convert configured parameters to keyword args for __init__().
        """
        kwargs = {'template': config_dict['template']}

        if 'referer' in config_dict:
            kwargs['referer'] = config_dict['referer']

        if 'source projection' in config_dict:
            kwargs['source_projection'] = Geography.getProjectionByName(config_dict['source projection'])

        if 'timeout' in config_dict:
            kwargs['timeout'] = config_dict['timeout']

        return kwargs

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        """ Return an image for an area.
        
            Each argument (width, height, etc.) is substituted into the template.
        """
        if self.source_projection is not None:
            ne_location = self.layer.projection.projLocation(Point(xmax, ymax))
            ne_point = self.source_projection.locationProj(ne_location)
            ymax = ne_point.y
            xmax = ne_point.x
            sw_location = self.layer.projection.projLocation(Point(xmin, ymin))
            sw_point = self.source_projection.locationProj(sw_location)
            ymin = sw_point.y
            xmin = sw_point.x
            srs = self.source_projection.srs

        mapping = {'width': width, 'height': height, 'srs': srs, 'zoom': zoom}
        mapping.update({'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax})

        href = self.template.safe_substitute(mapping)
        req = urllib2.Request(href)

        if self.referer:
            req.add_header('Referer', self.referer)

        body = urllib2.urlopen(req, timeout=self.timeout).read()
        tile = Verbatim(body)

        return tile

########NEW FILE########
__FILENAME__ = Redis
""" Caches tiles to Redis

Requires redis-py and redis-server
  https://pypi.python.org/pypi/redis/
  http://redis.io/

  sudo apt-get install redis-server
  pip install redis


Example configuration:

  "cache": {
    "name": "Redis",
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "key prefix": "unique-id"
  }

Redis cache parameters:

  host
    Defaults to "localhost" if omitted.

  port
    Integer; Defaults to 6379 if omitted.

  db
    Integer; Redis database number, defaults to 0 if omitted.

  key prefix
    Optional string to prepend to generated key.
    Useful when running multiple instances of TileStache
    that share the same Redis database to avoid key
    collisions (though the prefered solution is to use a different
    db number). The key prefix will be prepended to the
    key name. Defaults to "".
    

"""
from __future__ import absolute_import
from time import time as _time, sleep as _sleep

# We enabled absolute_import because case insensitive filesystems
# cause this file to be loaded twice (the name of this file
# conflicts with the name of the module we want to import).
# Forcing absolute imports fixes the issue.

try:
    import redis
except ImportError:
    # at least we can build the documentation
    pass


def tile_key(layer, coord, format, key_prefix):
    """ Return a tile key string.
    """
    name = layer.name()
    tile = '%(zoom)d/%(column)d/%(row)d' % coord.__dict__
    key = str('%(key_prefix)s/%(name)s/%(tile)s.%(format)s' % locals())
    return key


class Cache:
    """
    """
    def __init__(self, host="localhost", port=6379, db=0, key_prefix=''):
        self.host = host
        self.port = port
        self.db = db
        self.conn = redis.Redis(host=self.host, port=self.port, db=self.db)
        self.key_prefix = key_prefix


    def lock(self, layer, coord, format):
        """ Acquire a cache lock for this tile.
            Returns nothing, but blocks until the lock has been acquired.
        """
        key = tile_key(layer, coord, format, self.key_prefix) + "-lock" 
        due = _time() + layer.stale_lock_timeout

        while _time() < due:
            if self.conn.setnx(key, 'locked.'):
                return

            _sleep(.2)

        self.conn.set(key, 'locked.')
        return
        
    def unlock(self, layer, coord, format):
        """ Release a cache lock for this tile.
        """
        key = tile_key(layer, coord, format, self.key_prefix)
        self.conn.delete(key+'-lock')
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile.
        """
        key = tile_key(layer, coord, format, self.key_prefix)
        self.conn.delete(key)
        
    def read(self, layer, coord, format):
        """ Read a cached tile.
        """
        key = tile_key(layer, coord, format, self.key_prefix)
        value = self.conn.get(key)
        return value
        
    def save(self, body, layer, coord, format):
        """ Save a cached tile.
        """
        key = tile_key(layer, coord, format, self.key_prefix)
        self.conn.set(key, body)

########NEW FILE########
__FILENAME__ = S3
""" Caches tiles to Amazon S3.

Requires boto (2.0+):
  http://pypi.python.org/pypi/boto

Example configuration:

  "cache": {
    "name": "S3",
    "bucket": "<bucket name>",
    "access": "<access key>",
    "secret": "<secret key>"
  }

S3 cache parameters:

  bucket
    Required bucket name for S3. If it doesn't exist, it will be created.

  access
    Optional access key ID for your S3 account.

  secret
    Optional secret access key for your S3 account.

  use_locks
    Optional boolean flag for whether to use the locking feature on S3.
    True by default. A good reason to set this to false would be the
    additional price and time required for each lock set in S3.
    
  path
    Optional path under bucket to use as the cache dir. ex. 'cache' will 
    put tiles under <bucket>/cache/

  reduced_redundancy
    If set to true, use S3's Reduced Redundancy Storage feature. Storage is
    cheaper but has lower redundancy on Amazon's servers. Defaults to false.

Access and secret keys are under "Security Credentials" at your AWS account page:
  http://aws.amazon.com/account/
  
When access or secret are not provided, the environment variables
AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY will be used
    http://docs.pythonboto.org/en/latest/s3_tut.html#creating-a-connection
"""
from time import time as _time, sleep as _sleep
from mimetypes import guess_type
from time import strptime, time
from calendar import timegm

try:
    from boto.s3.bucket import Bucket as S3Bucket
    from boto.s3.connection import S3Connection
except ImportError:
    # at least we can build the documentation
    pass

def tile_key(layer, coord, format, path = ''):
    """ Return a tile key string.
    """
    path = path.strip('/')
    name = layer.name()
    tile = '%(zoom)d/%(column)d/%(row)d' % coord.__dict__
    ext = format.lower()

    return str('%(path)s/%(name)s/%(tile)s.%(ext)s' % locals())

class Cache:
    """
    """
    def __init__(self, bucket, access=None, secret=None, use_locks=True, path='', reduced_redundancy=False):
        self.bucket = S3Bucket(S3Connection(access, secret), bucket)
        self.use_locks = bool(use_locks)
        self.path = path
        self.reduced_redundancy = reduced_redundancy

    def lock(self, layer, coord, format):
        """ Acquire a cache lock for this tile.
        
            Returns nothing, but blocks until the lock has been acquired.
            Does nothing and returns immediately if `use_locks` is false.
        """
        if not self.use_locks:
            return
        
        key_name = tile_key(layer, coord, format, self.path)
        due = _time() + layer.stale_lock_timeout
        
        while _time() < due:
            if not self.bucket.get_key(key_name+'-lock'):
                break
            
            _sleep(.2)
        
        key = self.bucket.new_key(key_name+'-lock')
        key.set_contents_from_string('locked.', {'Content-Type': 'text/plain'}, reduced_redundancy=self.reduced_redundancy)
        
    def unlock(self, layer, coord, format):
        """ Release a cache lock for this tile.
        """
        key_name = tile_key(layer, coord, format, self.path)
        self.bucket.delete_key(key_name+'-lock')
        
    def remove(self, layer, coord, format):
        """ Remove a cached tile.
        """
        key_name = tile_key(layer, coord, format, self.path)
        self.bucket.delete_key(key_name)
        
    def read(self, layer, coord, format):
        """ Read a cached tile.
        """
        key_name = tile_key(layer, coord, format, self.path)
        key = self.bucket.get_key(key_name)

        if key is None:
            return None
        
        if layer.cache_lifespan:
            t = timegm(strptime(key.last_modified, '%a, %d %b %Y %H:%M:%S %Z'))

            if (time() - t) > layer.cache_lifespan:
                return None
        
        return key.get_contents_as_string()
        
    def save(self, body, layer, coord, format):
        """ Save a cached tile.
        """
        key_name = tile_key(layer, coord, format, self.path)
        key = self.bucket.new_key(key_name)
        
        content_type, encoding = guess_type('example.'+format)
        headers = content_type and {'Content-Type': content_type} or {}
        
        key.set_contents_from_string(body, headers, policy='public-read', reduced_redundancy=self.reduced_redundancy)

########NEW FILE########
__FILENAME__ = Sandwich
""" Layered, composite rendering for TileStache.

The Sandwich Provider supplies a Photoshop-like rendering pipeline, making it
possible to use the output of other configured tile layers as layers or masks
to create a combined output. Sandwich is modeled on Lars Ahlzen's TopOSM.

The external "Blit" library is required by Sandwich, and can be installed
via Pip, easy_install, or directly from Github:

    https://github.com/migurski/Blit

The "stack" configuration parameter describes a layer or stack of layers that
can be combined to create output. A simple stack that merely outputs a single
color orange tile looks like this:

    {"color" "#ff9900"}

Other layers in the current TileStache configuration can be reference by name,
as in this example stack that simply echoes another layer:

    {"src": "layer-name"}

Bitmap images can also be referenced by local filename or URL, and will be
tiled seamlessly, assuming 256x256 parent tiles:

    {"src": "image.png"}
    {"src": "http://example.com/image.png"}

Layers can be limited to appear at certain zoom levels, given either as a range
or as a single number:

    {"src": "layer-name", "zoom": "12"}
    {"src": "layer-name", "zoom": "12-18"}

Layers can also be used as masks, as in this example that uses one layer
to mask another layer:

    {"mask": "layer-name", "src": "other-layer"}

Many combinations of "src", "mask", and "color" can be used together, but it's
an error to provide all three.

Layers can be combined through the use of opacity and blend modes. Opacity is
specified as a value from 0.0-1.0, and blend mode is specified as a string.
This example layer is blended using the "hard light" mode at 50% opacity:

    {"src": "hillshading", "mode": "hard light", "opacity": 0.5}

Currently-supported blend modes include "screen", "add", "multiply", "subtract",
"linear light", and "hard light".

Layers can also be affected by adjustments. Adjustments are specified as an
array of names and parameters. This example layer has been slightly darkened
using the "curves" adjustment, moving the input value of 181 (light gray)
to 50% gray while leaving black and white alone:

    {"src": "hillshading", "adjustments": [ ["curves", [0, 181, 255]] ]}

Available adjustments:
  "threshold" - Blit.adjustments.threshold()
  "curves" - Blit.adjustments.curves()
  "curves2" - Blit.adjustments.curves2()

See detailed information about adjustments in Blit documentation:

    https://github.com/migurski/Blit#readme

Finally, the stacking feature allows layers to combined in more complex ways.
This example stack combines a background color and foreground layer:

    [
      {"color": "#ff9900"},
      {"src": "layer-name"}
    ]

A complete example configuration might look like this:

    {
      "cache":
      {
        "name": "Test"
      },
      "layers": 
      {
        "base":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-base.xml"}
        },
        "halos":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-halos.xml"},
          "metatile": {"buffer": 128}
        },
        "outlines":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-outlines.xml"},
          "metatile": {"buffer": 16}
        },
        "streets":
        {
          "provider": {"name": "mapnik", "mapfile": "mapnik-streets.xml"},
          "metatile": {"buffer": 128}
        },
        "sandwiches":
        {
          "provider":
          {
            "name": "Sandwich",
            "stack":
            [
              {"src": "base"},
              {"src": "outlines", "mask": "halos"},
              {"src": "streets"}
            ]
          }
        }
      }
    }
"""
from re import search
from StringIO import StringIO
from itertools import product
from urlparse import urljoin
from urllib import urlopen

from . import Core

try:
    import Image
except ImportError:
    try:
        from Pillow import Image
    except ImportError:
        from PIL import Image

try:
    import Blit

    blend_modes = {
        'screen': Blit.blends.screen,
        'add': Blit.blends.add,
        'multiply': Blit.blends.multiply,
        'subtract': Blit.blends.subtract,
        'linear light': Blit.blends.linear_light,
        'hard light': Blit.blends.hard_light
        }

    adjustment_names = {
        'threshold': Blit.adjustments.threshold,
        'curves': Blit.adjustments.curves,
        'curves2': Blit.adjustments.curves2
        }

except ImportError:
    # Well, this will not work.
    pass

class Provider:
    """ Sandwich Provider.
    
        Stack argument is a list of layer dictionaries described in module docs.
    """
    def __init__(self, layer, stack):
        self.layer = layer
        self.config = layer.config
        self.stack = stack
    
    @staticmethod
    def prepareKeywordArgs(config_dict):
        """ Convert configured parameters to keyword args for __init__().
        """
        return {'stack': config_dict['stack']}
    
    def renderTile(self, width, height, srs, coord):
        
        rendered = self.draw_stack(coord, dict())
        
        if rendered.size() == (width, height):
            return rendered.image()
        else:
            return rendered.image().resize((width, height))

    def draw_stack(self, coord, tiles):
        """ Render this image stack.

            Given a coordinate, return an output image with the results of all the
            layers in this stack pasted on in turn.
        
            Final argument is a dictionary used to temporarily cache results
            of layers retrieved from layer_bitmap(), to speed things up in case
            of repeatedly-used identical images.
        """
        # start with an empty base
        rendered = Blit.Color(0, 0, 0, 0)
    
        for layer in self.stack:
            if 'zoom' in layer and not in_zoom(coord, layer['zoom']):
                continue

            #
            # Prepare pixels from elsewhere.
            #
        
            source_name, mask_name, color_name = [layer.get(k, None) for k in ('src', 'mask', 'color')]
    
            if source_name and color_name and mask_name:
                raise Core.KnownUnknown("You can't specify src, color and mask together in a Sandwich Layer: %s, %s, %s" % (repr(source_name), repr(color_name), repr(mask_name)))
        
            if source_name and source_name not in tiles:
                if source_name in self.config.layers:
                    tiles[source_name] = layer_bitmap(self.config.layers[source_name], coord)
                else:
                    tiles[source_name] = local_bitmap(source_name, self.config, coord, self.layer.dim)
        
            if mask_name and mask_name not in tiles:
                tiles[mask_name] = layer_bitmap(self.config.layers[mask_name], coord)
        
            #
            # Build up the foreground layer.
            #
        
            if source_name and color_name:
                # color first, then layer
                foreground = make_color(color_name).blend(tiles[source_name])
        
            elif source_name:
                foreground = tiles[source_name]
        
            elif color_name:
                foreground = make_color(color_name)

            elif mask_name:
                raise Core.KnownUnknown("You have to provide more than just a mask to Sandwich Layer: %s" % repr(mask_name))

            else:
                raise Core.KnownUnknown("You have to provide at least some combination of src, color and mask to Sandwich Layer")
        
            #
            # Do the final composition with adjustments and blend modes.
            #
        
            for (name, args) in layer.get('adjustments', []):
                adjustfunc = adjustment_names.get(name)(*args)
                foreground = foreground.adjust(adjustfunc)
        
            opacity = float(layer.get('opacity', 1.0))
            blendfunc = blend_modes.get(layer.get('mode', None), None)
        
            if mask_name:
                rendered = rendered.blend(foreground, tiles[mask_name], opacity, blendfunc)
            else:
                rendered = rendered.blend(foreground, None, opacity, blendfunc)
    
        return rendered

def local_bitmap(source, config, coord, dim):
    """ Return Blit.Bitmap representation of a raw image.
    """
    address = urljoin(config.dirpath, source)
    bytes = urlopen(address).read()
    image = Image.open(StringIO(bytes)).convert('RGBA')
    
    coord = coord.zoomBy(8)
    w, h, col, row = image.size[0], image.size[1], int(coord.column), int(coord.row)
    
    x = w * (col / w) - col
    y = h * (row / h) - row
    
    output = Image.new('RGBA', (dim, dim))
    
    for (x, y) in product(range(x, dim, w), range(y, dim, h)):
        # crop the top-left if needed
        xmin = 0 if x > 0 else -x
        ymin = 0 if y > 0 else -y
        
        # don't paste up and to the left
        x = x if x >= 0 else 0
        y = y if y >= 0 else 0
        
        output.paste(image.crop((xmin, ymin, w, h)), (x, y))
    
    return Blit.Bitmap(output)

def layer_bitmap(layer, coord):
    """ Return Blit.Bitmap representation of tile from a given layer.
    
        Uses TileStache.getTile(), so caches are read and written as normal.
    """
    from . import getTile

    mime, body = getTile(layer, coord, 'png')
    image = Image.open(StringIO(body)).convert('RGBA')

    return Blit.Bitmap(image)

def in_zoom(coord, range):
    """ Return True if the coordinate zoom is within the textual range.
    
        Range might look like "1-10" or just "5".
    """
    zooms = search("^(\d+)-(\d+)$|^(\d+)$", range)
    
    if not zooms:
        raise Core.KnownUnknown("Bad zoom range in a Sandwich Layer: %s" % repr(range))
    
    min_zoom, max_zoom, at_zoom = zooms.groups()
    
    if min_zoom is not None and max_zoom is not None:
        min_zoom, max_zoom = int(min_zoom), int(max_zoom)

    elif at_zoom is not None:
        min_zoom, max_zoom = int(at_zoom), int(at_zoom)

    else:
        min_zoom, max_zoom = 0, float('inf')
    
    return min_zoom <= coord.zoom and coord.zoom <= max_zoom

def make_color(color):
    """ Convert colors expressed as HTML-style RGB(A) strings to Blit.Color.
        
        Examples:
          white: "#ffffff", "#fff", "#ffff", "#ffffffff"
          black: "#000000", "#000", "#000f", "#000000ff"
          null: "#0000", "#00000000"
          orange: "#f90", "#ff9900", "#ff9900ff"
          transparent orange: "#f908", "#ff990088"
    """
    if type(color) not in (str, unicode):
        raise Core.KnownUnknown('Color must be a string: %s' % repr(color))

    if color[0] != '#':
        raise Core.KnownUnknown('Color must start with hash: "%s"' % color)

    if len(color) not in (4, 5, 7, 9):
        raise Core.KnownUnknown('Color must have three, four, six or eight hex chars: "%s"' % color)

    if len(color) == 4:
        color = ''.join([color[i] for i in (0, 1, 1, 2, 2, 3, 3)])

    elif len(color) == 5:
        color = ''.join([color[i] for i in (0, 1, 1, 2, 2, 3, 3, 4, 4)])
    
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        a = len(color) == 7 and 0xFF or int(color[7:9], 16)

    except ValueError:
        raise Core.KnownUnknown('Color must be made up of valid hex chars: "%s"' % color)

    return Blit.Color(r, g, b, a)

########NEW FILE########
__FILENAME__ = Arc
""" Arc-specific Vector provider helpers.
"""
from operator import add

from TileStache.Core import KnownUnknown

geometry_types = {
    'Point': 'esriGeometryPoint',
    'LineString': 'esriGeometryPolyline',
    'Polygon': 'esriGeometryPolygon',
    'MultiPoint': 'esriGeometryMultipoint',
    'MultiLineString': 'esriGeometryPolyline',
    'MultiPolygon': 'esriGeometryPolygon'
  }

class _amfFeatureSet(dict):
    """ Registered PyAMF class for com.esri.ags.tasks.FeatureSet
    
        http://help.arcgis.com/en/webapi/flex/apiref/com/esri/ags/FeatureSet.html
    """
    def __init__(self, spatial_reference, geometry_type, features):
        self.spatialReference = spatial_reference
        self.geometryType = geometry_type
        self.features = features
        dict.__init__(self, {'geometryType': geometry_type,
                             'spatialReference': spatial_reference,
                             'features': features})

class _amfSpatialReference(dict):
    """ Registered PyAMF class for com.esri.ags.SpatialReference
    
        http://help.arcgis.com/en/webapi/flex/apiref/com/esri/ags/SpatialReference.html
    """
    def __init__(self, wkid, wkt):
        if wkid:
            self.wkid = wkid
            dict.__init__(self, {'wkid': wkid})
        elif wkt:
            self.wkt = wkt
            dict.__init__(self, {'wkt': wkt})

class _amfFeature(dict):
    """ Registered PyAMF class for com.esri.ags.Feature
    
        No URL for class information - this class shows up in AMF responses
        from ESRI webservices but does not seem to be otherwise documented.
    """
    def __init__(self, attributes, geometry):
        self.attributes = attributes
        self.geometry = geometry
        dict.__init__(self, {'attributes': attributes, 'geometry': geometry})

class _amfGeometryMapPoint(dict):
    """ Registered PyAMF class for com.esri.ags.geometry.MapPoint
    
        http://help.arcgis.com/en/webapi/flex/apiref/com/esri/ags/geometry/MapPoint.html
    """
    def __init__(self, sref, x, y):
        self.x = x
        self.y = y
        self.spatialReference = sref
        dict.__init__(self, {'spatialReference': sref, 'x': x, 'y': y})

class _amfGeometryPolyline(dict):
    """ Registered PyAMF class for com.esri.ags.geometry.Polyline
    
        http://help.arcgis.com/en/webapi/flex/apiref/com/esri/ags/geometry/Polyline.html
    """
    def __init__(self, sref, paths):
        self.paths = paths
        self.spatialReference = sref
        dict.__init__(self, {'spatialReference': sref, 'paths': paths})

class _amfGeometryPolygon(dict):
    """ Registered PyAMF class for com.esri.ags.geometry.Polygon
    
        http://help.arcgis.com/en/webapi/flex/apiref/com/esri/ags/geometry/Polygon.html
    """
    def __init__(self, sref, rings):
        self.rings = rings
        self.spatialReference = sref
        dict.__init__(self, {'spatialReference': sref, 'rings': rings})

pyamf_classes = {
    _amfFeatureSet: 'com.esri.ags.tasks.FeatureSet',
    _amfSpatialReference: 'com.esri.ags.SpatialReference',
    _amfGeometryMapPoint: 'com.esri.ags.geometry.MapPoint',
    _amfGeometryPolyline: 'com.esri.ags.geometry.Polyline',
    _amfGeometryPolygon: 'com.esri.ags.geometry.Polygon',
    _amfFeature: 'com.esri.ags.Feature'
  }

def reserialize_to_arc(content, point_objects):
    """ Convert from "geo" (GeoJSON) to ESRI's GeoServices REST serialization.
    
        Second argument is a boolean flag for whether to use the class
        _amfGeometryMapPoint for points in ring and path arrays, or tuples.
        The formal class is needed for AMF responses, plain tuples otherwise.
        
        Much of this cribbed from sample server queries and page 191+ of:
          http://www.esri.com/library/whitepapers/pdfs/geoservices-rest-spec.pdf
    """
    mapPointList = point_objects and _amfGeometryMapPoint or (lambda s, x, y: (x, y))
    mapPointDict = point_objects and _amfGeometryMapPoint or (lambda s, x, y: {'x': x, 'y': y})
    
    found_geometry_types = set([feat['geometry']['type'] for feat in content['features']])
    found_geometry_types = set([geometry_types.get(type) for type in found_geometry_types])
    
    if len(found_geometry_types) > 1:
        raise KnownUnknown('Arc serialization needs a single geometry type, not ' + ', '.join(found_geometry_types))
    
    crs = content['crs']
    sref = _amfSpatialReference(crs.get('wkid', None), crs.get('wkt', None))
    geometry_type, features = None, []
    
    for feature in content['features']:
        geometry = feature['geometry']

        if geometry['type'] == 'Point':
            arc_geometry = mapPointDict(sref, *geometry['coordinates'])
        
        elif geometry['type'] == 'LineString':
            path = geometry['coordinates']
            paths = [[mapPointList(sref, *xy) for xy in path]]
            arc_geometry = _amfGeometryPolyline(sref, paths)

        elif geometry['type'] == 'Polygon':
            rings = geometry['coordinates']
            rings = [[mapPointList(sref, *xy) for xy in ring] for ring in rings]
            arc_geometry = _amfGeometryPolygon(sref, rings)

        elif geometry['type'] == 'MultiPoint':
            points = geometry['coordinates']
            points = [mapPointList(sref, *xy) for xy in points]
            arc_geometry = {'points': points}

        elif geometry['type'] == 'MultiLineString':
            paths = geometry['coordinates']
            paths = [[mapPointList(sref, *xy) for xy in path] for path in paths]
            arc_geometry = _amfGeometryPolyline(sref, paths)

        elif geometry['type'] == 'MultiPolygon':
            rings = reduce(add, geometry['coordinates'])
            rings = [[mapPointList(sref, *xy) for xy in ring] for ring in rings]
            arc_geometry = _amfGeometryPolygon(sref, rings)

        else:
            raise Exception(geometry['type'])
        
        arc_feature = _amfFeature(feature['properties'], arc_geometry)
        geometry_type = geometry_types[geometry['type']]
        features.append(arc_feature)
    
    return _amfFeatureSet(sref, geometry_type, features)

########NEW FILE########
