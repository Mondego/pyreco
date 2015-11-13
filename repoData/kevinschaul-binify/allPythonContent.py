__FILENAME__ = binify
#!/usr/bin/env python

import os
import sys

try:
    from osgeo.gdalconst import GA_ReadOnly
    from osgeo import ogr, osr
except ImportError:
    from gdalconst import GA_ReadOnly
    import ogr, osr

import progressbar

import cli
from shapegrids import hexagon

class Binifier(object):
    """
    Main binify logic.
    """

    def __init__(self, args=None):
        """
        Get the options from cli or another source (in the future), and
        instantiate a ShapeGrid object.
        """
        self.cli = cli.CLI()
        self.args = self.cli.parse_arguments(args)
        self.grid = hexagon.HexagonGrid()

    def main(self):
        """
        Handle input shapefile, create grid (output) shapefile, do
        summary calculations.
        """
        driver = ogr.GetDriverByName('ESRI Shapefile')
        in_shapefile = driver.Open(self.args.infile, GA_ReadOnly)
        if in_shapefile is None:
            print('Could not open shapefile for read: %s' % self.args.infile)
            sys.exit(1)

        in_layer = in_shapefile.GetLayer()
        if not in_layer.GetGeomType() == ogr.wkbPoint \
                and not self.args.ignore_type:
            print('Input shapefile does not contain a point layer.')
            print('To force computation, use the --ignore-type option.')
            sys.exit(2)

        # If outfile exists and `--overwrite` is set, delete it first
        if os.path.exists(self.args.outfile):
            if not self.args.overwrite:
                print('Output file exists. To overwrite, use the --overwrite \
option.')
                sys.exit(3)
            driver.DeleteDataSource(self.args.outfile)

        out_shapefile = driver.CreateDataSource(self.args.outfile)
        out_layer = out_shapefile.CreateLayer('grid', geom_type=ogr.wkbPolygon)
        field_defn = ogr.FieldDefn('COUNT', ogr.OFTInteger)
        out_layer.CreateField(field_defn)

        # Write .prj file for output shapefile
        spatial_ref = in_layer.GetSpatialRef()
        with open(self.args.outfile[:-4] + '.prj', 'w') as proj_file:
            proj_file.write(spatial_ref.ExportToWkt())

        if self.args.extent:
          extent = self.args.extent
        else:
          extent = in_layer.GetExtent()

        self.grid.create_grid(out_layer, extent,
                num_across=self.args.num_across)
        self.count_intersections(out_layer, in_layer)

        if self.args.exclude_empty:
            self.remove_empty_shapes(out_layer)

        in_shapefile.Destroy()
        out_shapefile.Destroy()

    def count_intersections(self, target, source):
        """
        Counts the number of points in `source` that intersect each polygon of
        `target`.
        """
        # Set up progress bar
        num_points = source.GetFeatureCount()
        if not self.args.suppress_output:
            pbar = progressbar.ProgressBar(
                widgets=[
                    'Binning: ',
                    progressbar.Percentage(),
                    progressbar.Bar()
                ],
                maxval=num_points
            )
            pbar.start()

        pbar_count = 0
        another_point = True
        while (another_point):
            point = source.GetNextFeature()
            if point:
                point_geom = point.GetGeometryRef()
                another_polygon = True
                while (another_polygon):
                    polygon = target.GetNextFeature()
                    if polygon:
                        poly_geom = polygon.GetGeometryRef()
                        if point_geom.Intersects(poly_geom):
                            # Intersection
                            count = polygon.GetFieldAsInteger('COUNT')
                            polygon.SetField('COUNT', count + 1)
                            target.SetFeature(polygon)
                        polygon.Destroy()
                    else:
                        another_polygon = False
                        target.ResetReading()
                point.Destroy()
            else:
                another_point = False
                source.ResetReading()
            if not self.args.suppress_output:
                # Update progress bar
                pbar.update(pbar_count)
                pbar_count = pbar_count + 1
        if not self.args.suppress_output:
            pbar.finish()

    def remove_empty_shapes(self, target):
        """
        Remove any shapes that ended up binning zero points.
        """
        another_polygon = True
        while (another_polygon):
            polygon = target.GetNextFeature()
            if polygon:
                count = polygon.GetFieldAsInteger('COUNT')
                if count == 0:
                    target.DeleteFeature(polygon.GetFID())
                target.SetFeature(polygon)
                polygon.Destroy()
            else:
                another_polygon = False
                target.ResetReading()

def launch_new_instance():
    """
    Launch an instance of Binifier.

    This is the entry function of the command-line tool `binify`.
    """
    binifier = Binifier()
    binifier.main()

if __name__ == '__main__':
    launch_new_instance()


########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python

import argparse

class CLI(object):
    """
    Handles command-line interface options
    """

    def parse_arguments(self, args=None):
        """
        Implement command-line arguments
        """
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('infile', help='A point shapefile to create \
                bins from.')
        self.parser.add_argument('outfile', help='A shapefile to write to. \
                Will be created if it does not exist.')
        self.parser.add_argument('-n', '--num-across', type=int,
                dest='num_across', default=10, help='Number of hexagons for \
                the grid to have across (approximate)')
        self.parser.add_argument('-E', '--extent', nargs=4, type=float, \
                metavar=('EAST_LNG', 'WEST_LNG', 'SOUTH_LAT', 'NORTH_LAT'),
                help='Use a custom extent.')
        self.parser.add_argument('-e', '--exclude-empty', \
                dest='exclude_empty', action='store_true', \
                help='Exclude shapes that end up binning zero points.')
        self.parser.add_argument('-o', '--overwrite', action='store_true', \
                help='Overwrite output file.')
        self.parser.add_argument('--ignore-type', action='store_true', \
                dest='ignore_type', help='Ignore the geometry type of the \
                input shapefile.')
        self.parser.add_argument('--suppress-output', action='store_true', \
                dest='suppress_output', help='Supress console output \
                (excluding any warnings).')
        return self.parser.parse_args(args)


########NEW FILE########
__FILENAME__ = hexagon
#!/usr/bin/env python

import math

try:
    from osgeo import ogr
except ImportError:
    import ogr

from shapegrid import ShapeGrid

SQRT_3_DIV_4 = math.sqrt(3) / 4

class HexagonGrid(ShapeGrid):
    """
    Generic shape grid interface.
    """

    def __init__(self):
        pass

    def create_grid(self, layer, extent, num_across=10):
        """
        Creates a grid of hexagon features in `layer`.
        """
        definition = layer.GetLayerDefn()
        width = extent[1] - extent[0]
        height = extent[3] - extent[2]
        scale_width = width / num_across

        column = 0
        y = extent[2] - scale_width
        while y < extent[3] + scale_width:
            x = extent[0] - scale_width
            if column % 2 == 0:
                x += 0.75 * scale_width
            while x < extent[1] + scale_width:
                hexagon = self.create_hexagon(x, y, scale_width)
                feature = ogr.Feature(definition)
                feature.SetGeometry(hexagon)
                feature.SetField('COUNT', 0)
                layer.CreateFeature(feature)
                feature.Destroy()
                x += (1.5 * scale_width)
            y += SQRT_3_DIV_4 * scale_width
            column += 1

    def create_hexagon(self, center_x, center_y, width):
        """
        Returns a hexagon geometry around the center point.
        """
        h_val = SQRT_3_DIV_4 * width
        width_quarter = width / 4
        width_half = width / 2
        ring = ogr.Geometry(ogr.wkbLinearRing)

        # Draw hexagon clockwise, beginning with northwest vertice
        ring.AddPoint(center_x - width_quarter, center_y + h_val)
        ring.AddPoint(center_x + width_quarter, center_y + h_val)
        ring.AddPoint(center_x + width_half, center_y)
        ring.AddPoint(center_x + width_quarter, center_y - h_val)
        ring.AddPoint(center_x - width_quarter, center_y - h_val)
        ring.AddPoint(center_x - width_half, center_y)
        ring.AddPoint(center_x - width_quarter, center_y + h_val)

        hexagon = ogr.Geometry(type=ogr.wkbPolygon)
        hexagon.AddGeometry(ring)
        return hexagon


########NEW FILE########
__FILENAME__ = shapegrid
#!/usr/bin/env python

class ShapeGrid(object):
    """
    Generic shape grid interface. Should be subclassed by specific shapes.
    """

    def __init__(self):
        pass

    def create_grid(self, layer, extent, num_across=10):
        raise NotImplementedError('Provided by each subclass of ShapeGrid.')


########NEW FILE########
__FILENAME__ = test_binify
#!/usr/bin/env python

import unittest

from gdalconst import GA_ReadOnly
from osgeo import ogr, osr

from binify.binify import Binifier

class TestBinifySimple(unittest.TestCase):

    def setUp(self):
        self.args = [
            'tests/test-shapefiles/simple-points.shp',
            'tests/test-shapefiles/simple-points-grid.shp',
            '--overwrite',
            '--suppress-output',
        ]
        self.b = Binifier(self.args)
        self.b.main()

        self.driver = ogr.GetDriverByName('ESRI Shapefile')
        self.out_shapefile = self.driver.Open(
            'tests/test-shapefiles/simple-points-grid.shp',
            GA_ReadOnly
        )
        self.out_layer = self.out_shapefile.GetLayer()

    def test_extent(self):
        extent = self.out_layer.GetExtent()
        self.assertEqual(extent, (
            -0.7789222489017765,
            -0.03954617630398981,
            -0.3489926778373724,
            0.1998517180083852)
        )

    def test_count(self):
        count = 0
        another_feature = True
        while (another_feature):
            feature = self.out_layer.GetNextFeature()
            if feature:
                count += feature.GetFieldAsInteger('COUNT')
            else:
                another_feature = False
        self.assertEqual(count, 10)

    def test_feature_count(self):
        self.assertEqual(self.out_layer.GetFeatureCount(), 160)

    def tearDown(self):
        self.out_shapefile.Destroy()

class TestBinifyExcludeEmpty(unittest.TestCase):

    def setUp(self):
        self.args = [
            'tests/test-shapefiles/simple-points.shp',
            'tests/test-shapefiles/simple-points-grid-empty.shp',
            '--exclude-empty',
            '--overwrite',
            '--suppress-output',
        ]
        self.b = Binifier(self.args)
        self.b.main()

        self.driver = ogr.GetDriverByName('ESRI Shapefile')
        self.out_shapefile = self.driver.Open(
            'tests/test-shapefiles/simple-points-grid-empty.shp',
            GA_ReadOnly
        )
        self.out_layer = self.out_shapefile.GetLayer()

    def test_feature_count(self):
        # We must loop because features are marked for deletion, but are still
        # considered in layer.GetFeatureCount()
        count = 0
        another_feature = True
        while (another_feature):
            feature = self.out_layer.GetNextFeature()
            if feature:
                count += 1
                feature.Destroy()
            else:
                another_feature = False
                self.out_layer.ResetReading()
        self.assertEqual(count, 7)
 
    def tearDown(self):
        self.out_shapefile.Destroy()


########NEW FILE########
