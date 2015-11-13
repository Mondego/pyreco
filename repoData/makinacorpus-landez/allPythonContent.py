__FILENAME__ = cache
import os
import re
import logging
import shutil
from gettext import gettext as _
from util import flip_y

logger = logging.getLogger(__name__)


class Cache(object):
    def __init__(self, **kwargs):
        self.extension = kwargs.get('extension', '.png')
        self._scheme = 'tms'

    def tile_file(self, (z, x, y)):
        tile_dir = os.path.join("%s" % z, "%s" % x)
        y = flip_y(y, z)
        tile_name = "%s%s" % (y, self.extension)
        return tile_dir, tile_name

    @property
    def scheme(self):
        return self._scheme

    def read(self, (z, x, y)):
        raise NotImplementedError

    def save(self, body, (z, x, y)):
        raise NotImplementedError

    def remove(self, (z, x, y)):
        raise NotImplementedError

    def clean(self):
        raise NotImplementedError


class Dummy(Cache):
    def read(self, (z, x, y)):
        return None

    def save(self, body, (z, x, y)):
        pass

    def remove(self, (z, x, y)):
        pass

    def clean(self):
        pass


class Disk(Cache):
    def __init__(self, basename, folder, **kwargs):
        super(Disk, self).__init__(**kwargs)
        self._basename = None
        self._basefolder = folder
        self.folder = folder
        self.basename = basename

    @property
    def basename(self):
        return self._basename

    @basename.setter
    def basename(self, basename):
        self._basename = basename
        subfolder = re.sub(r'[^a-z^A-Z^0-9]+', '', basename.lower())
        self.folder = os.path.join(self._basefolder, subfolder)

    @Cache.scheme.setter
    def scheme(self, scheme):
        assert scheme in ('wmts', 'xyz', 'tms'), "Unknown scheme %s" % scheme
        self._scheme = 'xyz' if (scheme == 'wmts') else scheme

    def tile_file(self, (z, x, y)):
        tile_dir = os.path.join("%s" % z, "%s" % x)
        if (self.scheme != 'xyz'):
            y = flip_y(y, z)
        tile_name = "%s%s" % (y, self.extension)
        return tile_dir, tile_name

    def tile_fullpath(self, (z, x, y)):
        tile_dir, tile_name = self.tile_file((z, x, y))
        tile_abs_dir = os.path.join(self.folder, tile_dir)
        return os.path.join(tile_abs_dir, tile_name)

    def remove(self, (z, x, y)):
        tile_abs_uri = self.tile_fullpath((z, x, y))
        os.remove(tile_abs_uri)
        parent = os.path.dirname(tile_abs_uri)
        i = 0
        while i <= 3:  # try to remove 3 levels (cache/z/x/)
            try:
                os.rmdir(parent)
                parent = os.path.dirname(parent)
                i += 1
            except OSError:
                break

    def read(self, (z, x, y)):
        tile_abs_uri = self.tile_fullpath((z, x, y))
        if os.path.exists(tile_abs_uri):
            logger.debug(_("Found %s") % tile_abs_uri)
            return open(tile_abs_uri, 'rb').read()
        return None

    def save(self, body, (z, x, y)):
        tile_abs_uri = self.tile_fullpath((z, x, y))
        tile_abs_dir = os.path.dirname(tile_abs_uri)
        if not os.path.isdir(tile_abs_dir):
            os.makedirs(tile_abs_dir)
        logger.debug(_("Save %s bytes to %s") % (len(body), tile_abs_uri))
        open(tile_abs_uri, 'wb').write(body)

    def clean(self):
        logger.debug(_("Clean-up %s") % self.folder)
        try:
            shutil.rmtree(self.folder)
        except OSError:
            logger.warn(_("%s was missing or read-only.") % self.folder)

########NEW FILE########
__FILENAME__ = filters
class Filter(object):
    @property
    def basename(self):
        return self.__class__.__name__

    def process(self, image):
        return image

    @classmethod
    def string2rgba(cls, colorstring):
        """ Convert #RRGGBBAA to an (R, G, B, A) tuple """
        colorstring = colorstring.strip()
        if colorstring[0] == '#':
            colorstring = colorstring[1:]
        if len(colorstring) < 6:
            raise ValueError("input #%s is not in #RRGGBB format" % colorstring)
        r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:6]
        a = 'ff'
        if len(colorstring) > 6:
            a = colorstring[6:8]
        r, g, b, a = [int(n, 16) for n in (r, g, b, a)]
        return (r, g, b, a)


class GrayScale(Filter):
    def process(self, image):
        return image.convert('L')


class ColorToAlpha(Filter):
    def __init__(self, color):
        self.color = color

    @property
    def basename(self):
        return super(ColorToAlpha, self).basename + self.color

    def process(self, image):
        # Code taken from Phatch - Photo Batch Processor
        # Copyright (C) 2007-2010 www.stani.be

        from PIL import Image, ImageMath

        def difference1(source, color):
            """When source is bigger than color"""
            return (source - color) / (255.0 - color)

        def difference2(source, color):
            """When color is bigger than source"""
            return (color - source) / color

        def color_to_alpha(image, color=None):
            image = image.convert('RGBA')

            color = map(float, Filter.string2rgba(self.color))
            img_bands = [band.convert("F") for band in image.split()]

            # Find the maximum difference rate between source and color. I had to use two
            # difference functions because ImageMath.eval only evaluates the expression
            # once.
            alpha = ImageMath.eval(
                """float(
                    max(
                        max(
                            max(
                                difference1(red_band, cred_band),
                                difference1(green_band, cgreen_band)
                            ),
                            difference1(blue_band, cblue_band)
                        ),
                        max(
                            max(
                                difference2(red_band, cred_band),
                                difference2(green_band, cgreen_band)
                            ),
                            difference2(blue_band, cblue_band)
                        )
                    )
                )""",
                difference1=difference1,
                difference2=difference2,
                red_band = img_bands[0],
                green_band = img_bands[1],
                blue_band = img_bands[2],
                cred_band = color[0],
                cgreen_band = color[1],
                cblue_band = color[2]
            )
            # Calculate the new image colors after the removal of the selected color
            new_bands = [
                ImageMath.eval(
                    "convert((image - color) / alpha + color, 'L')",
                    image = img_bands[i],
                    color = color[i],
                    alpha = alpha
                )
                for i in xrange(3)
            ]
            # Add the new alpha band
            new_bands.append(ImageMath.eval(
                "convert(alpha_band * alpha, 'L')",
                alpha = alpha,
                alpha_band = img_bands[3]
            ))
            return Image.merge('RGBA', new_bands)

        return color_to_alpha(image, self.color)

########NEW FILE########
__FILENAME__ = proj
from math import pi, sin, log, exp, atan, tan
from gettext import gettext as _

from . import DEFAULT_TILE_SIZE

DEG_TO_RAD = pi/180
RAD_TO_DEG = 180/pi
MAX_LATITUDE = 85.0511287798
EARTH_RADIUS = 6378137


def minmax (a,b,c):
    a = max(a,b)
    a = min(a,c)
    return a


class InvalidCoverageError(Exception):
    """ Raised when coverage bounds are invalid """
    pass


class GoogleProjection(object):

    NAME = 'EPSG:3857'

    """
    Transform Lon/Lat to Pixel within tiles
    Originally written by OSM team : http://svn.openstreetmap.org/applications/rendering/mapnik/generate_tiles.py
    """
    def __init__(self, tilesize=DEFAULT_TILE_SIZE, levels = [0], scheme='wmts'):
        if not levels:
            raise InvalidCoverageError(_("Wrong zoom levels."))
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        self.levels = levels
        self.maxlevel = max(levels) + 1
        self.tilesize = tilesize
        self.scheme = scheme
        c = tilesize
        for d in range(self.maxlevel):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2

    def project_pixels(self,ll,zoom):
        d = self.zc[zoom]
        e = round(d[0] + ll[0] * self.Bc[zoom])
        f = minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
        g = round(d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom])
        return (e,g)

    def unproject_pixels(self,px,zoom):
        e = self.zc[zoom]
        f = (px[0] - e[0])/self.Bc[zoom]
        g = (px[1] - e[1])/-self.Cc[zoom]
        h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
        if self.scheme == 'tms':
            h = - h
        return (f,h)

    def tile_at(self, zoom, position):
        """
        Returns a tuple of (z, x, y)
        """
        x, y = self.project_pixels(position, zoom)
        return (zoom, int(x/self.tilesize), int(y/self.tilesize))

    def tile_bbox(self, (z, x, y)):
        """
        Returns the WGS84 bbox of the specified tile
        """
        topleft = (x * self.tilesize, (y + 1) * self.tilesize)
        bottomright = ((x + 1) * self.tilesize, y * self.tilesize)
        nw = self.unproject_pixels(topleft, z)
        se = self.unproject_pixels(bottomright, z)
        return nw + se

    def project(self, (lng, lat)):
        """
        Returns the coordinates in meters from WGS84
        """
        x = lng * DEG_TO_RAD
        lat = max(min(MAX_LATITUDE, lat), -MAX_LATITUDE)
        y = lat * DEG_TO_RAD
        y = log(tan((pi / 4) + (y / 2)))
        return (x*EARTH_RADIUS, y*EARTH_RADIUS)

    def unproject(self, (x, y)):
        """
        Returns the coordinates from position in meters
        """
        lng = x/EARTH_RADIUS * RAD_TO_DEG
        lat = 2 * atan(exp(y/EARTH_RADIUS)) - pi/2 * RAD_TO_DEG
        return (lng, lat)

    def tileslist(self, bbox):
        if len(bbox) != 4:
            raise InvalidCoverageError(_("Wrong format of bounding box."))
        xmin, ymin, xmax, ymax = bbox
        if abs(xmin) > 180 or abs(xmax) > 180 or \
           abs(ymin) > 90 or abs(ymax) > 90:
            raise InvalidCoverageError(_("Some coordinates exceed [-180,+180], [-90, 90]."))

        if xmin >= xmax or ymin >= ymax:
            raise InvalidCoverageError(_("Bounding box format is (xmin, ymin, xmax, ymax)"))

        ll0 = (xmin, ymax)  # left top
        ll1 = (xmax, ymin)  # right bottom

        l = []
        for z in self.levels:
            px0 = self.project_pixels(ll0,z)
            px1 = self.project_pixels(ll1,z)

            for x in range(int(px0[0]/self.tilesize),
                           int(px1[0]/self.tilesize)+1):
                if (x < 0) or (x >= 2**z):
                    continue
                for y in range(int(px0[1]/self.tilesize),
                               int(px1[1]/self.tilesize)+1):
                    if (y < 0) or (y >= 2**z):
                        continue
                    if self.scheme == 'tms':
                        y = ((2**z-1) - y)
                    l.append((z, x, y))
        return l

########NEW FILE########
__FILENAME__ = sources
import os
import time
import zlib
import sqlite3
import logging
import json
from gettext import gettext as _
from pkg_resources import parse_version
import urllib
import urllib2
from urlparse import urlparse
from tempfile import NamedTemporaryFile
from util import flip_y


has_mapnik = False
try:
    import mapnik
    has_mapnik = True
except ImportError:
    pass


from . import DEFAULT_TILE_FORMAT, DEFAULT_TILE_SIZE, DOWNLOAD_RETRIES
from proj import GoogleProjection


logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """ Raised when extraction of tiles from specified MBTiles has failed """
    pass


class InvalidFormatError(Exception):
    """ Raised when reading of MBTiles content has failed """
    pass


class DownloadError(Exception):
    """ Raised when download at tiles URL fails DOWNLOAD_RETRIES times """
    pass


class TileSource(object):
    def __init__(self, tilesize=None):
        if tilesize is None:
            tilesize = DEFAULT_TILE_SIZE
        self.tilesize = tilesize
        self.basename = ''

    def tile(self, z, x, y):
        raise NotImplementedError

    def metadata(self):
        return dict()


class MBTilesReader(TileSource):
    def __init__(self, filename, tilesize=None):
        super(MBTilesReader, self).__init__(tilesize)
        self.filename = filename
        self.basename = os.path.basename(self.filename)
        self._con = None
        self._cur = None

    def _query(self, sql, *args):
        """ Executes the specified `sql` query and returns the cursor """
        if not self._con:
            logger.debug(_("Open MBTiles file '%s'") % self.filename)
            self._con = sqlite3.connect(self.filename)
            self._cur = self._con.cursor()
        sql = ' '.join(sql.split())
        logger.debug(_("Execute query '%s' %s") % (sql, args))
        try:
            self._cur.execute(sql, *args)
        except (sqlite3.OperationalError, sqlite3.DatabaseError), e:
            raise InvalidFormatError(_("%s while reading %s") % (e, self.filename))
        return self._cur

    def metadata(self):
        rows = self._query('SELECT name, value FROM metadata')
        rows = [(row[0], row[1]) for row in rows]
        return dict(rows)

    def zoomlevels(self):
        rows = self._query('SELECT DISTINCT(zoom_level) FROM tiles ORDER BY zoom_level')
        return [int(row[0]) for row in rows]

    def tile(self, z, x, y):
        logger.debug(_("Extract tile %s") % ((z, x, y),))
        tms_y = flip_y(int(y), int(z))
        rows = self._query('''SELECT tile_data FROM tiles
                              WHERE zoom_level=? AND tile_column=? AND tile_row=?;''', (z, x, tms_y))
        t = rows.fetchone()
        if not t:
            raise ExtractionError(_("Could not extract tile %s from %s") % ((z, x, y), self.filename))
        return t[0]

    def grid(self, z, x, y, callback=None):
        tms_y = flip_y(int(y), int(z))
        rows = self._query('''SELECT grid FROM grids
                              WHERE zoom_level=? AND tile_column=? AND tile_row=?;''', (z, x, tms_y))
        t = rows.fetchone()
        if not t:
            raise ExtractionError(_("Could not extract grid %s from %s") % ((z, x, y), self.filename))
        grid_json = json.loads(zlib.decompress(t[0]))

        rows = self._query('''SELECT key_name, key_json FROM grid_data
                              WHERE zoom_level=? AND tile_column=? AND tile_row=?;''', (z, x, tms_y))
        # join up with the grid 'data' which is in pieces when stored in mbtiles file
        grid_json['data'] = {}
        grid_data = rows.fetchone()
        while grid_data:
            grid_json['data'][grid_data[0]] = json.loads(grid_data[1])
            grid_data = rows.fetchone()
        serialized = json.dumps(grid_json)
        if callback is not None:
            return '%s(%s);' % (callback, serialized)
        return serialized

    def find_coverage(self, zoom):
        """
        Returns the bounding box (minx, miny, maxx, maxy) of an adjacent
        group of tiles at this zoom level.
        """
        # Find a group of adjacent available tiles at this zoom level
        rows = self._query('''SELECT tile_column, tile_row FROM tiles
                              WHERE zoom_level=?
                              ORDER BY tile_column, tile_row;''', (zoom,))
        t = rows.fetchone()
        xmin, ymin = t
        previous = t
        while t and t[0] - previous[0] <= 1:
            # adjacent, go on
            previous = t
            t = rows.fetchone()
        xmax, ymax = previous
        # Transform (xmin, ymin) (xmax, ymax) to pixels
        S = self.tilesize
        bottomleft = (xmin * S, (ymax + 1) * S)
        topright = ((xmax + 1) * S, ymin * S)
        # Convert center to (lon, lat)
        proj = GoogleProjection(S, [zoom])  # WGS84
        return proj.unproject_pixels(bottomleft, zoom) + proj.unproject_pixels(topright, zoom)


class TileDownloader(TileSource):
    def __init__(self, url, headers=None, subdomains=None, tilesize=None):
        super(TileDownloader, self).__init__(tilesize)
        self.tiles_url = url
        self.tiles_subdomains = subdomains or ['a', 'b', 'c']
        parsed = urlparse(self.tiles_url)
        self.basename = parsed.netloc
        self.headers = headers or {}

    def tile(self, z, x, y):
        """
        Download the specified tile from `tiles_url`
        """
        logger.debug(_("Download tile %s") % ((z, x, y),))
        # Render each keyword in URL ({s}, {x}, {y}, {z}, {size} ... )
        size = self.tilesize
        s = self.tiles_subdomains[(x + y) % len(self.tiles_subdomains)];
        try:
            url = self.tiles_url.format(**locals())
        except KeyError, e:
            raise DownloadError(_("Unknown keyword %s in URL") % e)

        logger.debug(_("Retrieve tile at %s") % url)
        r = DOWNLOAD_RETRIES
        sleeptime = 1
        while r > 0:
            try:
                request = urllib2.Request(url)
                for header, value in self.headers.items():
                    request.add_header(header, value)
                stream = urllib2.urlopen(request)
                assert stream.getcode() == 200
                return stream.read()
            except (AssertionError, IOError), e:
                logger.debug(_("Download error, retry (%s left). (%s)") % (r, e))
                r -= 1
                time.sleep(sleeptime)
                # progressivly sleep longer to wait for this tile
                if (sleeptime <= 10) and (r % 2 == 0):
                    sleeptime += 1  # increase wait
        raise DownloadError(_("Cannot download URL %s") % url)


class WMSReader(TileSource):
    def __init__(self, url, layers, tilesize=None, **kwargs):
        super(WMSReader, self).__init__(tilesize)
        self.basename = '-'.join(layers)
        self.url = url
        self.wmsParams = dict(
            service='WMS',
            request='GetMap',
            version='1.1.1',
            styles='',
            format=DEFAULT_TILE_FORMAT,
            transparent=False,
            layers=','.join(layers),
            width=self.tilesize,
            height=self.tilesize,
        )
        self.wmsParams.update(**kwargs)
        projectionKey = 'srs'
        if parse_version(self.wmsParams['version']) >= parse_version('1.3'):
            projectionKey = 'crs'
        self.wmsParams[projectionKey] = GoogleProjection.NAME

    def tile(self, z, x, y):
        logger.debug(_("Request WMS tile %s") % ((z, x, y),))
        proj = GoogleProjection(self.tilesize, [z])
        bbox = proj.tile_bbox((z, x, y))
        bbox = proj.project(bbox[:2]) + proj.project(bbox[2:])
        bbox = ','.join(map(str, bbox))
        # Build WMS request URL
        encodedparams = urllib.urlencode(self.wmsParams)
        url = "%s?%s" % (self.url, encodedparams)
        url += "&bbox=%s" % bbox   # commas are not encoded
        try:
            logger.debug(_("Download '%s'") % url)
            f = urllib2.urlopen(url)
            header = f.info().typeheader
            assert header == self.wmsParams['format'], "Invalid WMS response type : %s" % header
            return f.read()
        except (AssertionError, IOError):
            raise ExtractionError


class MapnikRenderer(TileSource):
    def __init__(self, stylefile, tilesize=None):
        super(MapnikRenderer, self).__init__(tilesize)
        assert has_mapnik, _("Cannot render tiles without mapnik !")
        self.stylefile = stylefile
        self.basename = os.path.basename(self.stylefile)
        self._mapnik = None
        self._prj = None

    def tile(self, z, x, y):
        """
        Render the specified tile with Mapnik
        """
        logger.debug(_("Render tile %s") % ((z, x, y),))
        proj = GoogleProjection(self.tilesize, [z])
        return self.render(proj.tile_bbox((z, x, y)))

    def _prepare_rendering(self, bbox, width=None, height=None):
        if not self._mapnik:
            self._mapnik = mapnik.Map(width, height)
            # Load style XML
            mapnik.load_map(self._mapnik, self.stylefile, True)
            # Obtain <Map> projection
            self._prj = mapnik.Projection(self._mapnik.srs)

        # Convert to map projection
        assert len(bbox) == 4, _("Provide a bounding box tuple (minx, miny, maxx, maxy)")
        c0 = self._prj.forward(mapnik.Coord(bbox[0], bbox[1]))
        c1 = self._prj.forward(mapnik.Coord(bbox[2], bbox[3]))

        # Bounding box for the tile
        bbox = mapnik.Box2d(c0.x, c0.y, c1.x, c1.y)
        self._mapnik.resize(width, height)
        self._mapnik.zoom_to_box(bbox)
        self._mapnik.buffer_size = 128

    def render(self, bbox, width=None, height=None):
        """
        Render the specified tile with Mapnik
        """
        width = width or self.tilesize
        height = height or self.tilesize
        self._prepare_rendering(bbox, width=width, height=height)

        # Render image with default Agg renderer
        tmpfile = NamedTemporaryFile(delete=False)
        im = mapnik.Image(width, height)
        mapnik.render(self._mapnik, im)
        im.save(tmpfile.name, 'png256')  # TODO: mapnik output only to file?
        tmpfile.close()
        content = open(tmpfile.name).read()
        os.unlink(tmpfile.name)
        return content

    def grid(self, z, x, y, fields, layer):
        """
        Render the specified grid with Mapnik
        """
        logger.debug(_("Render grid %s") % ((z, x, y),))
        proj = GoogleProjection(self.tilesize, [z])
        return self.render_grid(proj.tile_bbox((z, x, y)), fields, layer)

    def render_grid(self, bbox, grid_fields, layer, width=None, height=None):
        """
        Render the specified grid with Mapnik
        """
        width = width or self.tilesize
        height = height or self.tilesize
        self._prepare_rendering(bbox, width=width, height=height)

        grid = mapnik.Grid(width, height)
        mapnik.render_layer(self._mapnik, grid, layer=layer, fields=grid_fields)
        grid = grid.encode()
        return json.dumps(grid)


########NEW FILE########
__FILENAME__ = tests
import os
import logging
import unittest
import shutil
import tempfile
import json
import sqlite3

from tiles import (TilesManager, MBTilesBuilder, ImageExporter,
                   EmptyCoverageError, DownloadError)
from proj import InvalidCoverageError
from cache import Disk
from sources import MBTilesReader


class TestTilesManager(unittest.TestCase):
    def test_format(self):
        mb = TilesManager()
        self.assertEqual(mb.tile_format, 'image/png')
        self.assertEqual(mb.cache.extension, '.png')
        # Format from WMS options
        mb = TilesManager(wms_server='dumb', wms_layers=['dumber'],
                          wms_options={'format': 'image/jpeg'})
        self.assertEqual(mb.tile_format, 'image/jpeg')
        self.assertEqual(mb.cache.extension, '.jpeg')
        # Format from URL extension
        mb = TilesManager(tiles_url='http://tileserver/{z}/{x}/{y}.jpg')
        self.assertEqual(mb.tile_format, 'image/jpeg')
        self.assertEqual(mb.cache.extension, '.jpeg')
        mb = TilesManager(tiles_url='http://tileserver/{z}/{x}/{y}.png')
        self.assertEqual(mb.tile_format, 'image/png')
        self.assertEqual(mb.cache.extension, '.png')
        # No extension in URL
        mb = TilesManager(tiles_url='http://tileserver/tiles/')
        self.assertEqual(mb.tile_format, 'image/png')
        self.assertEqual(mb.cache.extension, '.png')
        mb = TilesManager(tile_format='image/gif',
                          tiles_url='http://tileserver/tiles/')
        self.assertEqual(mb.tile_format, 'image/gif')
        self.assertEqual(mb.cache.extension, '.gif')

    def test_tileslist(self):
        mb = TilesManager()
        # World at level 0
        l = mb.tileslist((-180.0, -90.0, 180.0, 90.0), [0])
        self.assertEqual(l, [(0, 0, 0)])
        # World at levels [0, 1]
        l = mb.tileslist((-180.0, -90.0, 180.0, 90.0), [0, 1])
        self.assertEqual(l, [(0, 0, 0),
                             (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)])
        # Incorrect bounds
        self.assertRaises(InvalidCoverageError, mb.tileslist, (-91.0, -180.0), [0])
        self.assertRaises(InvalidCoverageError, mb.tileslist, (-90.0, -180.0, 180.0, 90.0), [])
        self.assertRaises(InvalidCoverageError, mb.tileslist, (-91.0, -180.0, 180.0, 90.0), [0])
        self.assertRaises(InvalidCoverageError, mb.tileslist, (-91.0, -180.0, 181.0, 90.0), [0])
        self.assertRaises(InvalidCoverageError, mb.tileslist, (-90.0, 180.0, 180.0, 90.0), [0])
        self.assertRaises(InvalidCoverageError, mb.tileslist, (-30.0, -90.0, -50.0, 90.0), [0])

    def test_tileslist_at_z1_x0_y0(self):
        mb = TilesManager()
        l = mb.tileslist((-180.0, 1, -1, 90.0), [1])
        self.assertEqual(l, [(1, 0, 0)])

    def test_tileslist_at_z1_x0_y0_tms(self):
        mb = TilesManager()
        l = mb.tileslist((-180.0, 1, -1, 90.0), [1], scheme='tms')

        self.assertEqual(l, [(1, 0, 1)])

    def test_download_tile(self):
        mb = TilesManager(cache=False)
        tile = (1, 1, 1)
        # Unknown URL keyword
        mb = TilesManager(tiles_url="http://{X}.tile.openstreetmap.org/{z}/{x}/{y}.png")
        self.assertRaises(DownloadError, mb.tile, (1, 1, 1))
        # With subdomain keyword
        mb = TilesManager(tiles_url="http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
        content = mb.tile(tile)
        self.assertTrue(content is not None)
        # No subdomain keyword
        mb = TilesManager(tiles_url="http://tile.cloudmade.com/f1fe9c2761a15118800b210c0eda823c/1/{size}/{z}/{x}/{y}.png")
        content = mb.tile(tile)
        self.assertTrue(content is not None)
        # Subdomain in available range
        mb = TilesManager(tiles_url="http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                          tiles_subdomains=list("abc"))
        for y in range(3):
            content = mb.tile((10, 0, y))
            self.assertTrue(content is not None)
        # Subdomain out of range
        mb = TilesManager(tiles_subdomains=list("abcz"))
        self.assertRaises(DownloadError, mb.tile, (10, 1, 2))
        # Invalid URL
        mb = TilesManager(tiles_url="http://{s}.osm.com")
        self.assertRaises(DownloadError, mb.tile, (10, 1, 2))


class TestMBTilesBuilder(unittest.TestCase):
    temp_cache = os.path.join(tempfile.gettempdir(), 'landez/stileopenstreetmaporg')
    temp_dir = os.path.join(tempfile.gettempdir(), 'landez/tiles')

    def tearDown(self):
        try:
            shutil.rmtree(self.temp_cache)
            shutil.rmtree(self.temp_dir)
            os.remove('foo.mbtiles')
        except OSError:
            pass

    def test_init(self):
        mb = MBTilesBuilder()
        self.assertEqual(mb.filepath, os.path.join(os.getcwd(), 'tiles.mbtiles'))
        self.assertEqual(mb.cache.folder, self.temp_cache)
        self.assertEqual(mb.tmp_dir, self.temp_dir)

        mb = MBTilesBuilder(filepath='/foo/bar/toto.mb')
        self.assertEqual(mb.cache.folder, self.temp_cache)
        self.assertEqual(mb.tmp_dir, os.path.join(tempfile.gettempdir(), 'landez/toto'))

    def test_run(self):
        mb = MBTilesBuilder(filepath='big.mbtiles')
        # Fails if no coverage
        self.assertRaises(EmptyCoverageError, mb.run, True)
        # Runs well from web tiles
        mb.add_coverage(bbox=(-180.0, -90.0, 180.0, 90.0), zoomlevels=[0, 1])
        mb.run(force=True)
        self.assertEqual(mb.nbtiles, 5)
        # Read from other mbtiles
        mb2 = MBTilesBuilder(filepath='small.mbtiles', mbtiles_file=mb.filepath, cache=False)
        mb2.add_coverage(bbox=(-180.0, 1, -1, 90.0), zoomlevels=[1])
        mb2.run(force=True)
        self.assertEqual(mb2.nbtiles, 1)
        os.remove('small.mbtiles')
        os.remove('big.mbtiles')

    def test_run_jpeg(self):
        output = 'mq.mbtiles'
        mb = MBTilesBuilder(filepath=output,
                            tiles_url='http://oatile1.mqcdn.com/tiles/1.0.0/sat/{z}/{x}/{y}.jpg')
        mb.add_coverage(bbox=(1.3, 43.5, 1.6, 43.7), zoomlevels=[10])
        mb.run(force=True)
        self.assertEqual(mb.nbtiles, 4)
        # Check result
        reader = MBTilesReader(output)
        self.assertEqual(reader.metadata().get('format'), 'jpeg')
        os.remove(output)

    def test_clean_gather(self):
        mb = MBTilesBuilder()
        self.assertEqual(mb.tmp_dir, self.temp_dir)
        self.assertFalse(os.path.exists(mb.tmp_dir))
        mb._gather((1, 1, 1))
        self.assertTrue(os.path.exists(mb.tmp_dir))
        mb._clean_gather()
        self.assertFalse(os.path.exists(mb.tmp_dir))

    def test_grid_content(self):
        here = os.path.abspath(os.path.dirname(__file__))
        mb = MBTilesBuilder(
            stylefile=os.path.join(here, "data_test", "stylesheet.xml"),
            grid_fields=["NAME"],
            grid_layer=0,
            filepath='foo.mbtiles',
            cache=False
        )

        mb.add_coverage(bbox=(-180, -90, 180, 90), zoomlevels=[2])
        mb.run()

        mbtiles_path = os.path.join(os.getcwd(), 'foo.mbtiles')
        mbtiles = sqlite3.connect(mbtiles_path).cursor()
        grid = mbtiles.execute("SELECT grid FROM grids WHERE zoom_level=2 AND tile_column=1 AND tile_row=1")
        produced_data = json.loads(mb.grid((2, 1, 1)))['data']['39']['NAME']
        expected_data = 'Costa Rica'
        os.remove('foo.mbtiles')
        self.assertEqual(produced_data, expected_data)


class TestImageExporter(unittest.TestCase):
    def test_gridtiles(self):
        mb = ImageExporter()
        # At zoom level 0
        grid = mb.grid_tiles((-180.0, -90.0, 180.0, 90.0), 0)
        self.assertEqual(grid, [[(0, 0)]])
        # At zoom level 1
        grid = mb.grid_tiles((-180.0, -90.0, 180.0, 90.0), 1)
        self.assertEqual(grid, [[(0, 0), (1, 0)],
                                [(0, 1), (1, 1)]])

    def test_exportimage(self):
        from PIL import Image
        output = "image.png"
        ie = ImageExporter()
        ie.export_image((-180.0, -90.0, 180.0, 90.0), 2, output)
        i = Image.open(output)
        self.assertEqual((1024, 1024), i.size)
        os.remove(output)
        # Test from other mbtiles
        mb = MBTilesBuilder(filepath='toulouse.mbtiles')
        mb.add_coverage(bbox=(1.3, 43.5, 1.6, 43.7), zoomlevels=[12])
        mb.run()
        ie = ImageExporter(mbtiles_file=mb.filepath)
        ie.export_image((1.3, 43.5, 1.6, 43.7), 12, output)
        os.remove('toulouse.mbtiles')
        i = Image.open(output)
        self.assertEqual((1280, 1024), i.size)
        os.remove(output)


class TestCache(unittest.TestCase):
    temp_path = os.path.join(tempfile.gettempdir(), 'landez/stileopenstreetmaporg')

    def clean(self):
        try:
            shutil.rmtree(self.temp_path)
        except OSError:
            pass

    def test_folder(self):
        c = Disk('foo', '/tmp/')
        self.assertEqual(c.folder, '/tmp/foo')
        c.basename = 'bar'
        self.assertEqual(c.folder, '/tmp/bar')

    def test_clean(self):
        mb = TilesManager()
        self.assertEqual(mb.cache.folder, self.temp_path)
        # Missing dir
        self.assertFalse(os.path.exists(mb.cache.folder))
        mb.cache.clean()
        # Empty dir
        os.makedirs(mb.cache.folder)
        self.assertTrue(os.path.exists(mb.cache.folder))
        mb.cache.clean()
        self.assertFalse(os.path.exists(mb.cache.folder))

    def test_cache_scheme_WMTS(self):
        tm = TilesManager(tiles_url="http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", cache=True, cache_scheme='wmts')
        self.assertEqual(tm.cache.scheme, 'xyz')

    def test_cache_with_bad_scheme(self):
        with self.assertRaises(AssertionError):
            TilesManager(tiles_url="http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", cache=True, cache_scheme='badscheme')

    def test_cache_is_stored_at_WMTS_format(self):
        tm = TilesManager(tiles_url="http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", cache=True, cache_scheme='wmts')
        tilecontent = tm.tile((12, 2064, 1495))
        self.assertTrue(os.path.exists(os.path.join(self.temp_path, '12', '2064', '1495.png')))

    def test_cache_is_stored_at_TMS_format(self):
        tm = TilesManager(tiles_url="http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", cache=True, cache_scheme='tms')
        tilecontent = tm.tile((12, 2064, 1495))
        self.assertTrue(os.path.exists(os.path.join(self.temp_path, '12', '2064', '2600.png')))

    def setUp(self):
        self.clean()

    def tearDown(self):
        self.clean()


class TestLayers(unittest.TestCase):
    def test_cache_folder(self):
        mb = TilesManager(tiles_url='http://server')
        self.assertEqual(mb.cache.folder, '/tmp/landez/server')
        over = TilesManager(tiles_url='http://toto')
        self.assertEqual(over.cache.folder, '/tmp/landez/toto')
        mb.add_layer(over)
        self.assertEqual(mb.cache.folder, '/tmp/landez/servertoto10')
        mb.add_layer(over, 0.5)
        self.assertEqual(mb.cache.folder, '/tmp/landez/servertoto10toto05')


class TestFilters(unittest.TestCase):
    def test_cache_folder(self):
        from filters import ColorToAlpha
        mb = TilesManager(tiles_url='http://server')
        self.assertEqual(mb.cache.folder, '/tmp/landez/server')
        mb.add_filter(ColorToAlpha('#ffffff'))
        self.assertEqual(mb.cache.folder, '/tmp/landez/servercolortoalphaffffff')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

########NEW FILE########
__FILENAME__ = tiles
import os
import shutil
import logging
from gettext import gettext as _
import json
import mimetypes
import string

from StringIO import StringIO

from mbutil import disk_to_mbtiles

from . import (DEFAULT_TILES_URL, DEFAULT_TILES_SUBDOMAINS,
               DEFAULT_TMP_DIR, DEFAULT_FILEPATH, DEFAULT_TILE_SIZE,
               DEFAULT_TILE_FORMAT)
from proj import GoogleProjection
from cache import Disk, Dummy
from sources import (MBTilesReader, TileDownloader, WMSReader,
                     MapnikRenderer, ExtractionError, DownloadError)

has_pil = False
try:
    import Image
    import ImageEnhance
    has_pil = True
except ImportError:
    try:
        from PIL import Image, ImageEnhance
        has_pil = True
    except ImportError:
        pass


logger = logging.getLogger(__name__)



class EmptyCoverageError(Exception):
    """ Raised when coverage (tiles list) is empty """
    pass


class TilesManager(object):

    def __init__(self, **kwargs):
        """
        Manipulates tiles in general. Gives ability to list required tiles on a
        bounding box, download them, render them, extract them from other mbtiles...

        Keyword arguments:
        cache -- use a local cache to share tiles between runs (default True)

        tiles_dir -- Local folder containing existing tiles if cache is
                     True, or where temporary tiles will be written otherwise
                     (default DEFAULT_TMP_DIR)

        tiles_url -- remote URL to download tiles (*default DEFAULT_TILES_URL*)
        tiles_headers -- HTTP headers to send (*default empty*)

        stylefile -- mapnik stylesheet file (*to render tiles locally*)

        mbtiles_file -- A MBTiles file providing tiles (*to extract its tiles*)

        wms_server -- A WMS server url (*to request tiles*)
        wms_layers -- The list of layers to be requested
        wms_options -- WMS parameters to be requested (see ``landez.reader.WMSReader``)

        tile_size -- default tile size (default DEFAULT_TILE_SIZE)
        tile_format -- default tile format (default DEFAULT_TILE_FORMAT)
        """
        self.tile_size = kwargs.get('tile_size', DEFAULT_TILE_SIZE)
        self.tile_format = kwargs.get('tile_format', DEFAULT_TILE_FORMAT)

        # Tiles Download
        self.tiles_url = kwargs.get('tiles_url', DEFAULT_TILES_URL)
        self.tiles_subdomains = kwargs.get('tiles_subdomains', DEFAULT_TILES_SUBDOMAINS)
        self.tiles_headers = kwargs.get('tiles_headers')

        # Tiles rendering
        self.stylefile = kwargs.get('stylefile')

        # Grids rendering
        self.grid_fields = kwargs.get('grid_fields', [])
        self.grid_layer = kwargs.get('grid_layer', 0)

        # MBTiles reading
        self.mbtiles_file = kwargs.get('mbtiles_file')

        # WMS requesting
        self.wms_server = kwargs.get('wms_server')
        self.wms_layers = kwargs.get('wms_layers', [])
        self.wms_options = kwargs.get('wms_options', {})

        if self.mbtiles_file:
            self.reader = MBTilesReader(self.mbtiles_file, self.tile_size)
        elif self.wms_server:
            assert self.wms_layers, _("Requires at least one layer (see ``wms_layers`` parameter)")
            self.reader = WMSReader(self.wms_server, self.wms_layers,
                                    self.tile_size, **self.wms_options)
            if 'format' in self.wms_options:
                self.tile_format = self.wms_options['format']
                logger.info(_("Tile format set to %s") % self.tile_format)
        elif self.stylefile:
            self.reader = MapnikRenderer(self.stylefile, self.tile_size)
        else:
            mimetype, encoding = mimetypes.guess_type(self.tiles_url)
            if mimetype and mimetype != self.tile_format:
                self.tile_format = mimetype
                logger.info(_("Tile format set to %s") % self.tile_format)
            self.reader = TileDownloader(self.tiles_url, headers=self.tiles_headers,
                                         subdomains=self.tiles_subdomains, tilesize=self.tile_size)

        # Tile files extensions
        self._tile_extension = mimetypes.guess_extension(self.tile_format, strict=False)
        assert self._tile_extension, _("Unknown format %s") % self.tile_format
        if self._tile_extension == '.jpe':
            self._tile_extension = '.jpeg'

        # Cache
        tiles_dir = kwargs.get('tiles_dir', DEFAULT_TMP_DIR)
        if kwargs.get('cache', True):
            self.cache = Disk(self.reader.basename, tiles_dir, extension=self._tile_extension)
            if kwargs.get('cache_scheme'):
                self.cache.scheme = kwargs.get('cache_scheme')
        else:
            self.cache = Dummy(extension=self._tile_extension)

        # Overlays
        self._layers = []
        # Filters
        self._filters = []
        # Number of tiles rendered/downloaded here
        self.rendered = 0

    def tileslist(self, bbox, zoomlevels, scheme='wmts'):
        """
        Build the tiles list within the bottom-left/top-right bounding
        box (minx, miny, maxx, maxy) at the specified zoom levels.
        Return a list of tuples (z,x,y)
        """
        proj = GoogleProjection(self.tile_size, zoomlevels, scheme)
        return proj.tileslist(bbox)

    def add_layer(self, tilemanager, opacity=1.0):
        """
        Add a layer to be blended (alpha-composite) on top of the tile.
        tilemanager -- a `TileManager` instance
        opacity -- transparency factor for compositing
        """
        assert has_pil, _("Cannot blend layers without python PIL")
        assert self.tile_size == tilemanager.tile_size, _("Cannot blend layers whose tile size differs")
        assert 0 <= opacity <= 1, _("Opacity should be between 0.0 (transparent) and 1.0 (opaque)")
        self.cache.basename += '%s%.1f' % (tilemanager.cache.basename, opacity)
        self._layers.append((tilemanager, opacity))

    def add_filter(self, filter_):
        """ Add an image filter for post-processing """
        assert has_pil, _("Cannot add filters without python PIL")
        self.cache.basename += filter_.basename
        self._filters.append(filter_)

    def tile(self, (z, x, y)):
        """
        Return the tile (binary) content of the tile and seed the cache.
        """
        logger.debug(_("tile method called with %s") % ([z, x, y]))

        output = self.cache.read((z, x, y))
        if output is None:
            output = self.reader.tile(z, x, y)
            # Blend layers
            if len(self._layers) > 0:
                logger.debug(_("Will blend %s layer(s)") % len(self._layers))
                output = self._blend_layers(output, (z, x, y))
            # Apply filters
            for f in self._filters:
                image = f.process(self._tile_image(output))
                output = self._image_tile(image)
            # Save result to cache
            self.cache.save(output, (z, x, y))

            self.rendered += 1
        return output

    def grid(self, (z, x, y)):
        """ Return the UTFGrid content """
        # sources.py -> MapnikRenderer -> grid
        content = self.reader.grid(z, x, y, self.grid_fields, self.grid_layer)
        return content


    def _blend_layers(self, imagecontent, (z, x, y)):
        """
        Merge tiles of all layers into the specified tile path
        """
        result = self._tile_image(imagecontent)
        # Paste each layer
        for (layer, opacity) in self._layers:
            try:
                # Prepare tile of overlay, if available
                overlay = self._tile_image(layer.tile((z, x, y)))
            except (DownloadError, ExtractionError), e:
                logger.warn(e)
                continue
            # Extract alpha mask
            overlay = overlay.convert("RGBA")
            r, g, b, a = overlay.split()
            overlay = Image.merge("RGB", (r, g, b))
            a = ImageEnhance.Brightness(a).enhance(opacity)
            overlay.putalpha(a)
            mask = Image.merge("L", (a,))
            result.paste(overlay, (0, 0), mask)
        # Read result
        return self._image_tile(result)

    def _tile_image(self, data):
        """
        Tile binary content as PIL Image.
        """
        image = Image.open(StringIO(data))
        return image.convert('RGBA')

    def _image_tile(self, image):
        out = StringIO()
        image.save(out, self._tile_extension[1:])
        return out.getvalue()


class MBTilesBuilder(TilesManager):
    def __init__(self, **kwargs):
        """
        A MBTiles builder for a list of bounding boxes and zoom levels.

        filepath -- output MBTiles file (default DEFAULT_FILEPATH)
        tmp_dir -- temporary folder for gathering tiles (default DEFAULT_TMP_DIR/filepath)
        """
        super(MBTilesBuilder, self).__init__(**kwargs)
        self.filepath = kwargs.get('filepath', DEFAULT_FILEPATH)
        # Gather tiles for mbutil
        basename, ext = os.path.splitext(os.path.basename(self.filepath))
        self.tmp_dir = kwargs.get('tmp_dir', DEFAULT_TMP_DIR)
        self.tmp_dir = os.path.join(self.tmp_dir, basename)
        self.tile_format = kwargs.get('tile_format', DEFAULT_TILE_FORMAT)

        # Number of tiles in total
        self.nbtiles = 0
        self._bboxes = []

    def add_coverage(self, bbox, zoomlevels):
        """
        Add a coverage to be included in the resulting mbtiles file.
        """
        self._bboxes.append((bbox, zoomlevels))

    @property
    def zoomlevels(self):
        """
        Return the list of covered zoom levels
        """
        return self._bboxes[0][1]  #TODO: merge all coverages

    @property
    def bounds(self):
        """
        Return the bounding box of covered areas
        """
        return self._bboxes[0][0]  #TODO: merge all coverages

    def run(self, force=False):
        """
        Build a MBTile file.

        force -- overwrite if MBTiles file already exists.
        """
        if os.path.exists(self.filepath):
            if force:
                logger.warn(_("%s already exists. Overwrite.") % self.filepath)
                os.remove(self.filepath)
            else:
                # Already built, do not do anything.
                logger.info(_("%s already exists. Nothing to do.") % self.filepath)
                return

        # Clean previous runs
        self._clean_gather()

        # If no coverage added, use bottom layer metadata
        if len(self._bboxes) == 0 and len(self._layers) > 0:
            bottomlayer = self._layers[0]
            metadata = bottomlayer.reader.metadata()
            if 'bounds' in metadata:
                logger.debug(_("Use bounds of bottom layer %s") % bottomlayer)
                bbox = map(float, metadata.get('bounds', '').split(','))
                zoomlevels = range(int(metadata.get('minzoom', 0)), int(metadata.get('maxzoom', 0)))
                self.add_coverage(bbox=bbox, zoomlevels=zoomlevels)

        # Compute list of tiles
        tileslist = set()
        for bbox, levels in self._bboxes:
            logger.debug(_("Compute list of tiles for bbox %s on zooms %s.") % (bbox, levels))
            bboxlist = self.tileslist(bbox, levels)
            logger.debug(_("Add %s tiles.") % len(bboxlist))
            tileslist = tileslist.union(bboxlist)
            logger.debug(_("%s tiles in total.") % len(tileslist))
        self.nbtiles = len(tileslist)
        if not self.nbtiles:
            raise EmptyCoverageError(_("No tiles are covered by bounding boxes : %s") % self._bboxes)
        logger.debug(_("%s tiles to be packaged.") % self.nbtiles)

        # Go through whole list of tiles and gather them in tmp_dir
        self.rendered = 0
        for (z, x, y) in tileslist:
            self._gather((z, x, y))

        logger.debug(_("%s tiles were missing.") % self.rendered)

        # Some metadata
        middlezoom = self.zoomlevels[len(self.zoomlevels)/2]
        lat = self.bounds[1] + (self.bounds[3] - self.bounds[1])/2
        lon = self.bounds[0] + (self.bounds[2] - self.bounds[0])/2
        metadata = {}
        metadata['format'] = self._tile_extension[1:]
        metadata['minzoom'] = self.zoomlevels[0]
        metadata['maxzoom'] = self.zoomlevels[-1]
        metadata['bounds'] = '%s,%s,%s,%s' % tuple(self.bounds)
        metadata['center'] = '%s,%s,%s' % (lon, lat, middlezoom)
        #display informations from the grids on hover
        content_to_display = ''
        for field_name in self.grid_fields:
            content_to_display += "{{{ %s }}}<br>" % field_name
        metadata['template'] = '{{#__location__}}{{/__location__}} {{#__teaser__}} \
        %s {{/__teaser__}}{{#__full__}}{{/__full__}}' % content_to_display
        metadatafile = os.path.join(self.tmp_dir, 'metadata.json')
        with open(metadatafile, 'w') as output:
            json.dump(metadata, output)

        # TODO: add UTF-Grid of last layer, if any

        # Package it!
        logger.info(_("Build MBTiles file '%s'.") % self.filepath)
        extension = self.tile_format.split("image/")[-1]
        disk_to_mbtiles(
            self.tmp_dir,
            self.filepath,
            format=extension,
            scheme=self.cache.scheme
        )

        try:
            os.remove("%s-journal" % self.filepath)  # created by mbutil
        except OSError, e:
            pass
        self._clean_gather()

    def _gather(self, (z, x, y)):
        files_dir, tile_name = self.cache.tile_file((z, x, y))
        tmp_dir = os.path.join(self.tmp_dir, files_dir)
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)
        tilecontent = self.tile((z, x, y))
        tilepath = os.path.join(tmp_dir, tile_name)
        with open(tilepath, 'wb') as f:
            f.write(tilecontent)
        if len(self.grid_fields) > 0:
            gridcontent = self.grid((z, x, y))
            gridpath = "%s.%s" % (os.path.splitext(tilepath)[0], 'grid.json')
            with open(gridpath, 'w') as f:
                f.write(gridcontent)

    def _clean_gather(self):
        logger.debug(_("Clean-up %s") % self.tmp_dir)
        try:
            shutil.rmtree(self.tmp_dir)
            #Delete parent folder only if empty
            try:
                parent = os.path.dirname(self.tmp_dir)
                os.rmdir(parent)
                logger.debug(_("Clean-up parent %s") % parent)
            except OSError:
                pass
        except OSError:
            pass


class ImageExporter(TilesManager):
    def __init__(self, **kwargs):
        """
        Arrange the tiles and join them together to build a single big image.
        """
        super(ImageExporter, self).__init__(**kwargs)

    def grid_tiles(self, bbox, zoomlevel):
        """
        Return a grid of (x, y) tuples representing the juxtaposition
        of tiles on the specified ``bbox`` at the specified ``zoomlevel``.
        """
        tiles = self.tileslist(bbox, [zoomlevel])
        grid = {}
        for (z, x, y) in tiles:
            if not grid.get(y):
                grid[y] = []
            grid[y].append(x)
        sortedgrid = []
        for y in sorted(grid.keys()):
            sortedgrid.append([(x, y) for x in sorted(grid[y])])
        return sortedgrid

    def export_image(self, bbox, zoomlevel, imagepath):
        """
        Writes to ``imagepath`` the tiles for the specified bounding box and zoomlevel.
        """
        assert has_pil, _("Cannot export image without python PIL")
        grid = self.grid_tiles(bbox, zoomlevel)
        width = len(grid[0])
        height = len(grid)
        widthpix = width * self.tile_size
        heightpix = height * self.tile_size

        result = Image.new("RGBA", (widthpix, heightpix))
        offset = (0, 0)
        for i, row in enumerate(grid):
            for j, (x, y) in enumerate(row):
                offset = (j * self.tile_size, i * self.tile_size)
                img = self._tile_image(self.tile((zoomlevel, x, y)))
                result.paste(img, offset)
        logger.info(_("Save resulting image to '%s'") % imagepath)
        result.save(imagepath)

########NEW FILE########
__FILENAME__ = util
def flip_y(y, z):
    return 2 ** z - 1 - y

########NEW FILE########
