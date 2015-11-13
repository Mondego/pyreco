__FILENAME__ = cli
#!/usr/bin/env python

import argparse
import sys

import mapnik

import constants

class InvarUtility(object):
    description = ''
    epilog = ''
    override_flags = ''

    def __init__(self):
        """
        Perform argument processing and other setup for a InvarUtility.
        """
        self._init_common_parser()
        self.add_arguments()
        self.args = self.argparser.parse_args()
        self._install_exception_handler()

        if hasattr(self.args, 'font_paths'):
            for font_path in self.args.font_paths:
                mapnik.register_fonts(font_path)

    def add_arguments(self):
        """
        Called upon initialization once the parser for common arguments has been constructed.

        Should be overriden by individual utilities.
        """
        raise NotImplementedError('add_arguments must be provided by each subclass of InvarUtility.')

    def main(self):
        """
        Main loop of the utility.

        Should be overriden by individual utilities and explicitly called by the executing script.
        """
        raise NotImplementedError(' must be provided by each subclass of InvarUtility.')

    def _init_common_parser(self):
        """
        Prepare a base argparse argument parser so that flags are consistent across different shell command tools.
        """
        self.argparser = argparse.ArgumentParser(description=self.description, epilog=self.epilog)

        self.argparser.add_argument('config', help="Mapnik2 XML configuration file.")
        self.argparser.add_argument('output_dir', help="Destination directory for output.")
        self.argparser.add_argument('-p', '--process_count', help="Number of rendering processes to create.", type=int, default=constants.DEFAULT_PROCESS_COUNT)
        self.argparser.add_argument('-w', '--width', help="Width of images to render.", type=int, default=constants.DEFAULT_WIDTH)
        self.argparser.add_argument('-t', '--height', help="Height of images to render.", type=int, default=constants.DEFAULT_HEIGHT)
        self.argparser.add_argument('-b', '--buffer', type=int, help="The buffer drawn around the image during rendering. Defaults to the width or height, whichever is greater, however, it may not be increased when rendering large elements at small zoom levels.")
        self.argparser.add_argument('--font-path', help='Add a directory to the paths which Mapnik will search by fonts.', dest='font_paths', action='append', default=['/Library/Fonts/', '/usr/share/fonts'])
        self.argparser.add_argument('-s', '--skip-existing', dest='skip_existing', action='store_true', help='Skip rendering tiles which already exist.')
        self.argparser.add_argument('-v', '--verbose', action='store_true', help='Display detailed error messages.')

    def _install_exception_handler(self):
        """
        Installs a replacement for sys.excepthook, which handles pretty-printing uncaught exceptions.
        """
        def handler(t, value, traceback):
            if self.args.verbose:
                sys.__excepthook__(t, value, traceback)
            else:
                print value

        sys.excepthook = handler


########NEW FILE########
__FILENAME__ = constants
#!/usr/bin/env python

DEFAULT_WIDTH = 256
DEFAULT_HEIGHT = 256
DEFAULT_PROCESS_COUNT = 1 
DEFAULT_FILE_TYPE = 'png256'


########NEW FILE########
__FILENAME__ = projections
#!/usr/bin/env python

from math import pi, sin, log, exp, atan

DEG_TO_RAD = pi / 180
RAD_TO_DEG = 180 / pi

def minmax (a,b,c):
    a = max(a,b)
    a = min(a,c)
    return a

class GoogleProjection:
    """
    Google projection transformations. Sourced from the OSM.
    Have not taken the time to figure out how this works.
    """
    def __init__(self, levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        c = 256

        for d in range(levels + 1):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2
                
    def fromLLtoPixel(self, ll, zoom):
         d = self.zc[zoom]
         e = round(d[0] + ll[0] * self.Bc[zoom])
         f = minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
         g = round(d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom])
         return (e,g)
     
    def fromPixelToLL(self, px, zoom):
         e = self.zc[zoom]
         f = (px[0] - e[0])/self.Bc[zoom]
         g = (px[1] - e[1])/-self.Cc[zoom]
         h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
         return (f,h)


########NEW FILE########
__FILENAME__ = renderer
#!/usr/bin/env python

import json
import multiprocessing
import os
import Queue

import mapnik

import constants
import projections

class Renderer(multiprocessing.Process):
    """
    A Mapnik renderer process.
    """
    def __init__(self, tile_queues, config, width=constants.DEFAULT_WIDTH, height=constants.DEFAULT_HEIGHT, filetype=constants.DEFAULT_FILE_TYPE, buffer_size=None, skip_existing=False):
        multiprocessing.Process.__init__(self)

        self.config = config
        self.tile_queues = tile_queues
        self.width = width
        self.height = height
        self.buffer_size = buffer_size if buffer_size else max(width, height)
        self.filetype = filetype
        self.skip_existing = skip_existing

    def run(self):
        self.mapnik_map = mapnik.Map(self.width, self.height)
        mapnik.load_map(self.mapnik_map, self.config, True)

        self.map_projection = mapnik.Projection(self.mapnik_map.srs)
        self.tile_projection = projections.GoogleProjection()  

        while True:
            tile_parameters = None

            # Try to fetch a tile from any queue
            for tile_queue in self.tile_queues:
                try:
                    tile_parameters = tile_queue.get_nowait()
                    break 
                except Queue.Empty:
                    pass

            # Couldn't get tile parameters from any queue--all done
            if not tile_parameters:
                return

            # Skip rendering existing tiles
            if self.skip_existing:
                filename = tile_parameters[0]

                if os.path.exists(filename):
                    print 'Skipping %s' % (filename)
                    tile_queue.task_done()

                    continue

            self.render(*tile_parameters)
            tile_queue.task_done()

    def render(self):
        """
        Render a segment from the queue. Must be overridden in subclasses.
        """
        raise NotImplementedError('You should not use Renderer directly, but rather one of its subclasses.')

class TileRenderer(Renderer):
    """
    Renderer for tiles. 
    """
    def __init__(self, tile_queues, config, width=constants.DEFAULT_WIDTH, height=constants.DEFAULT_HEIGHT, filetype=constants.DEFAULT_FILE_TYPE, buffer_size=None, skip_existing=False, **kwargs):
        super(TileRenderer, self).__init__(tile_queues, config, width, height, filetype, buffer_size, skip_existing)
        self.grid = kwargs.get('grid', False)
        self.key =  kwargs.get('key', None)
        self.fields =  kwargs.get('fields', None)

    def render(self, filename, tile_x, tile_y, zoom):
        """
        Render a single tile to a given filename.
        """
        print 'Rendering %s' % (filename)

        # Calculate pixel positions of bottom-left & top-right
        half_width = self.width / 2
        half_height = self.height / 2
        px0 = (tile_x * self.width, (tile_y + 1) * self.height)
        px1 = ((tile_x + 1) * self.width, tile_y * self.height)

        # Convert tile coords to LatLng
        ll0 = self.tile_projection.fromPixelToLL(px0, zoom);
        ll1 = self.tile_projection.fromPixelToLL(px1, zoom);
        
        # Convert LatLng to map coords
        c0 = self.map_projection.forward(mapnik.Coord(ll0[0], ll0[1]))
        c1 = self.map_projection.forward(mapnik.Coord(ll1[0], ll1[1]))

        # Create bounding box for the render
        bbox = mapnik.Box2d(c0.x, c0.y, c1.x, c1.y)

        self.mapnik_map.zoom_to_box(bbox)
        self.mapnik_map.buffer_size = self.buffer_size 

        # Render image with default renderer
        image = mapnik.Image(self.width, self.height)
        mapnik.render(self.mapnik_map, image)
        image.save(filename, self.filetype)
        
        if self.grid:
            if self.key:
                grid = mapnik.Grid(self.width, self.height)
            else:
                grid = mapnik.Grid(self.width, self.height, key=self.key)

            fields = []

            if self.fields:
                fields.extend(self.fields)

            mapnik.render_layer(self.mapnik_map,grid,layer=0,fields=fields)
            # then encode the grid array as utf, resample to 1/4 the size, and dump features
            # this comes from https://github.com/springmeyer/gridsforkids/blob/master/generate_tiles.py 
            # with little consideration
            grid_utf = grid.encode('utf', resolution=4, features=True)

            # client code uses jsonp, so fake by wrapping in grid() callback
            base, ext = os.path.splitext(filename)
            grid_filename = '%s.grid.json' % base
            print 'Rendering %s' % (grid_filename)

            with open(grid_filename,'wb') as f:
                f.write('grid(' + json.dumps(grid_utf) + ')')
            
            

class FrameRenderer(Renderer):
    """
    Renderer for frames (centered map fragments).
    """
    def render(self, filename, latitude, longitude, zoom):
        """
        Render a single tile to a given filename.
        """
        print 'Rendering %s' % (filename)
    
        x, y = self.tile_projection.fromLLtoPixel([longitude, latitude], zoom) 

        # Calculate pixel positions of bottom-left & top-right
        half_width = self.width / 2
        half_height = self.height / 2
        px0 = (x - half_width, y + half_height)
        px1 = (x + half_width, y - half_height)

        # Convert tile coords to LatLng
        ll0 = self.tile_projection.fromPixelToLL(px0, zoom);
        ll1 = self.tile_projection.fromPixelToLL(px1, zoom);
        
        # Convert LatLng to map coords
        c0 = self.map_projection.forward(mapnik.Coord(ll0[0], ll0[1]))
        c1 = self.map_projection.forward(mapnik.Coord(ll1[0], ll1[1]))

        # Create bounding box for the render
        bbox = mapnik.Box2d(c0.x, c0.y, c1.x, c1.y)

        self.mapnik_map.zoom_to_box(bbox)
        self.mapnik_map.buffer_size = self.buffer_size

        # Render image with default renderer
        image = mapnik.Image(self.width, self.height)
        mapnik.render(self.mapnik_map, image)
        image.save(filename, self.filetype)


########NEW FILE########
