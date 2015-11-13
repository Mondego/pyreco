__FILENAME__ = ndarray
# Benchmark for read of raster data to ndarray

import timeit

import rasterio
from osgeo import gdal

# GDAL
s = """
src = gdal.Open('rasterio/tests/data/RGB.byte.tif')
arr = src.GetRasterBand(1).ReadAsArray()
src = None
"""

n = 100

t = timeit.timeit(s, setup='from osgeo import gdal', number=n)
print("GDAL:")
print("%f msec\n" % (1000*t/n))

# Rasterio
s = """
with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    arr = src.read_band(1)
"""

t = timeit.timeit(s, setup='import rasterio', number=n)
print("Rasterio:")
print("%f msec\n" % (1000*t/n))

# GDAL Extras
s = """
src = gdal.Open('rasterio/tests/data/RGB.byte.tif')
transform = src.GetGeoTransform()
srs = osr.SpatialReference()
srs.ImportFromWkt(src.GetProjectionRef())
wkt = srs.ExportToWkt()
proj = srs.ExportToProj4()
arr = src.GetRasterBand(1).ReadAsArray()
src = None
"""

n = 1000

t = timeit.timeit(s, setup='from osgeo import gdal; from osgeo import osr', number=n)
print("GDAL + Extras:\n")
print("%f usec\n" % (t/n))

# Rasterio
s = """
with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    transform = src.transform
    proj = src.crs
    wkt = src.crs_wkt
    arr = src.read_band(1)
"""

t = timeit.timeit(s, setup='import rasterio', number=n)
print("Rasterio:\n")
print("%f usec\n" % (t/n))


import pstats, cProfile

s = """
with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    arr = src.read_band(1, window=(10, 10, 10, 10))
"""

cProfile.runctx(s, globals(), locals(), "Profile.prof")

s = pstats.Stats("Profile.prof")
s.strip_dirs().sort_stats("time").print_stats()

########NEW FILE########
__FILENAME__ = decimate
import os.path
import subprocess
import tempfile

import rasterio

with rasterio.drivers():

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        b, g, r = (src.read_band(k) for k in (1, 2, 3))
        meta = src.meta

    tmpfilename = os.path.join(tempfile.mkdtemp(), 'decimate.tif')

    meta.update(
        width=src.width/2,
        height=src.height/2)

    with rasterio.open(
            tmpfilename, 'w',
            **meta
            ) as dst:
        for k, a in [(1, b), (2, g), (3, r)]:
            dst.write_band(k, a)

    outfilename = os.path.join(tempfile.mkdtemp(), 'decimate.jpg')

    rasterio.copy(tmpfilename, outfilename, driver='JPEG', quality='30')

info = subprocess.call(['open', outfilename])


########NEW FILE########
__FILENAME__ = parallel
"""parallel.py

Operate on a raster dataset window-by-window using a pool of parallel
processes.

This example isn't the most efficient way to copy a small image, but
does illustrate a pattern that becomes efficient for large images
when the work done in the ``process_window()`` function is intensive.
"""

from multiprocessing import Pool

import rasterio

# process_window() is the function that the pool's workers will call
# with a tuple of args from the pool's queue.
def process_window(task):
    """Using a rasterio window, copy from source to destination.
    Returns None on success or returns the input task on failure so
    that the task can be re-tried.

    GDAL IO and Runtime errors occur in practice, so we catch those
    and signal that the window should be re-tried.
    """
    infile, outfile, ji, window = task
    try:
        with rasterio.open(outfile, 'r+') as dst:
            with rasterio.open(infile) as src:
                bands = [(k, src.read_band(k, window=window)) 
                            for k in src.indexes]
                for k, arr in bands:
                    dst.write_band(k, arr, window=window)
    except (IOError, RuntimeError):
        return task

def main(infile, outfile, num_workers=4, max_iterations=3):
    """Use process_window() to process a file in parallel."""
    with rasterio.open(infile) as src:
        meta = src.meta
        
        # We want a destination image with the same blocksize as the
        # source.
        block_shapes = set(src.block_shapes)
        assert len(block_shapes) == 1
        block_height, block_width = block_shapes.pop()
        meta.update(blockxsize=block_width, blockysize=block_height)
        
        if block_width != src.shape[1]:
          meta.update(tiled = 'yes')
        # Create an empty destination file on disk.
        with rasterio.open(outfile, 'w', **meta) as dst:
            pass
        
        # Make a list of windows to process.
        with rasterio.open(outfile) as dst:
            block_shapes = set(dst.block_shapes)
            assert len(block_shapes) == 1
            windows = list(dst.block_windows(1))

    # Make a pool of worker processes and task them, retrying if there
    # are failed windows.
    p = Pool(num_workers)
    tasks = ((infile, outfile, ij, window) for ij, window in windows)
    i = 0
    while len(windows) > 0 and i < max_iterations:
        results = p.imap_unordered(process_window, tasks, chunksize=10)
        tasks = filter(None, results)
        i += 1
    
    if len(tasks) > 0:
        raise ValueError(
            "Maximum iterations reached with %d tasks remaining" % len(tasks))
        return 1
    else:
        return 0

if __name__ == '__main__':
    infile = 'rasterio/tests/data/RGB.byte.tif'
    outfile = '/tmp/multiprocessed-RGB.byte.tif'
    main(infile, outfile)


########NEW FILE########
__FILENAME__ = polygonize
import pprint

import rasterio
import rasterio._features as ftrz

with rasterio.open('box.png') as src:
    image = src.read_band(1)

pprint.pprint(
    list(ftrz.polygonize(image)))

########NEW FILE########
__FILENAME__ = rasterio_polygonize
# Emulates GDAL's gdal_polygonize.py

import argparse
import logging
import subprocess
import sys

import fiona
import numpy as np
import rasterio
from rasterio.features import shapes


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('rasterio_polygonize')


def main(raster_file, vector_file, driver, mask_value):
    
    with rasterio.drivers():
        
        with rasterio.open(raster_file) as src:
            image = src.read_band(1)
        
        if mask_value is not None:
            mask = image == mask_value
        else:
            mask = None
        
        results = (
            {'properties': {'raster_val': v}, 'geometry': s}
            for i, (s, v) 
            in enumerate(
                shapes(image, mask=mask, transform=src.transform)))

        with fiona.open(
                vector_file, 'w', 
                driver=driver,
                crs=src.crs,
                schema={'properties': [('raster_val', 'int')],
                        'geometry': 'Polygon'}) as dst:
            dst.writerecords(results)
    
    return dst.name

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Writes shapes of raster features to a vector file")
    parser.add_argument(
        'input', 
        metavar='INPUT', 
        help="Input file name")
    parser.add_argument(
        'output', 
        metavar='OUTPUT',
        help="Output file name")
    parser.add_argument(
        '--output-driver',
        metavar='OUTPUT DRIVER',
        help="Output vector driver name")
    parser.add_argument(
        '--mask-value',
        default=None,
        type=int,
        metavar='MASK VALUE',
        help="Value to mask")
    args = parser.parse_args()

    name = main(args.input, args.output, args.output_driver, args.mask_value)
    
    print subprocess.check_output(
            ['ogrinfo', '-so', args.output, name])


########NEW FILE########
__FILENAME__ = rasterize_geometry
import logging
import numpy
import sys
import rasterio
from rasterio.features import rasterize


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('rasterize_geometry')


rows = cols = 10
transform = [0, 1, 0, 0, 0, 1]
geometry = {'type':'Polygon','coordinates':[[(2,2),(2,4.25),(4.25,4.25),(4.25,2),(2,2)]]}
with rasterio.drivers():
    result = rasterize([geometry], out_shape=(rows, cols), transform=transform)
    with rasterio.open(
            "test.tif",
            'w',
            driver='GTiff',
            width=cols,
            height=rows,
            count=1,
            dtype=numpy.uint8,
            nodata=0,
            transform=transform,
            crs={'init': "EPSG:4326"}) as out:
        out.write_band(1, result.astype(numpy.uint8))

########NEW FILE########
__FILENAME__ = reproject
import os
import shutil
import subprocess
import tempfile

import numpy
import rasterio
from rasterio.warp import reproject, RESAMPLING

tempdir = '/tmp'
tiffname = os.path.join(tempdir, 'example.tif')

with rasterio.drivers():

    # Consider a 512 x 512 raster centered on 0 degrees E and 0 degrees N
    # with each pixel covering 15".
    src_shape = (512, 512)
    src_transform = [-256.0/240, 1.0/240, 0.0, 256.0/240, 0.0, -1.0/240]
    src_crs = {'init': 'EPSG:4326'}
    source = numpy.ones(src_shape, numpy.uint8)*255

    # Prepare to reproject this rasters to a 1024 x 1024 dataset in
    # Web Mercator (EPSG:3857) with origin at -8928592, 2999585.
    dst_shape = (1024, 1024)
    dst_transform = [-237481.5, 425.0, 0.0, 237536.4, 0.0, -425.0]
    dst_crs = {'init': 'EPSG:3857'}
    destination = numpy.zeros(dst_shape, numpy.uint8)

    reproject(
        source, 
        destination, 
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=RESAMPLING.nearest)

    # Assert that the destination is only partly filled.
    assert destination.any()
    assert not destination.all()

    # Write it out to a file.
    with rasterio.open(
            tiffname, 
            'w',
            driver='GTiff',
            width=dst_shape[1],
            height=dst_shape[0],
            count=1,
            dtype=numpy.uint8,
            nodata=0,
            transform=dst_transform,
            crs=dst_crs) as dst:
        dst.write_band(1, destination)

info = subprocess.call(['open', tiffname])


########NEW FILE########
__FILENAME__ = sieve
#!/usr/bin/env python
#
# sieve: demonstrate sieving and polygonizing of raster features.

import subprocess

import numpy
import rasterio
from rasterio.features import sieve, shapes


# Register GDAL and OGR drivers.
with rasterio.drivers():
    
    # Read a raster to be sieved.
    with rasterio.open('rasterio/tests/data/shade.tif') as src:
        shade = src.read_band(1)
    
    # Print the number of shapes in the source raster.
    print "Slope shapes: %d" % len(list(shapes(shade)))
    
    # Sieve out features 13 pixels or smaller.
    sieved = sieve(shade, 13)

    # Print the number of shapes in the sieved raster.
    print "Sieved (13) shapes: %d" % len(list(shapes(sieved)))

    # Write out the sieved raster.
    with rasterio.open('example-sieved.tif', 'w', **src.meta) as dst:
        dst.write_band(1, sieved)

# Dump out gdalinfo's report card and open (or "eog") the TIFF.
print subprocess.check_output(
    ['gdalinfo', '-stats', 'example-sieved.tif'])
subprocess.call(['open', 'example-sieved.tif'])


########NEW FILE########
__FILENAME__ = total
import numpy
import rasterio
import subprocess

with rasterio.drivers():

    # Read raster bands directly to Numpy arrays.
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        r, g, b = map(src.read_band, (1, 2, 3))

    # Combine arrays using the 'iadd' ufunc. Expecting that the sum will
    # exceed the 8-bit integer range, initialize it as 16-bit. Adding other
    # arrays to it in-place converts those arrays up and preserves the type
    # of the total array.
    total = numpy.zeros(r.shape, dtype=rasterio.uint16)
    for band in (r, g, b):
        total += band
    total /= 3
    assert total.dtype == rasterio.uint16

    # Write the product as a raster band to a new 8-bit file. For keyword
    # arguments, we start with the meta attributes of the source file, but
    # then change the band count to 1, set the dtype to uint8, and specify
    # LZW compression.
    kwargs = src.meta
    kwargs.update(
        dtype=rasterio.uint8,
        count=1,
        compress='lzw')

    with rasterio.open('example-total.tif', 'w', **kwargs) as dst:
        dst.write_band(1, total.astype(rasterio.uint8))

# Dump out gdalinfo's report card and open the image.
info = subprocess.check_output(
    ['gdalinfo', '-stats', 'example-total.tif'])
print(info)
subprocess.call(['open', 'example-total.tif'])


########NEW FILE########
__FILENAME__ = dtypes

import numpy

bool_ = numpy.bool_
ubyte = uint8 = numpy.uint8
uint16 = numpy.uint16
int16 = numpy.int16
uint32 = numpy.uint32
int32 = numpy.int32
float32 = numpy.float32
float64 = numpy.float64

# Not supported:
#  GDT_CInt16 = 8, GDT_CInt32 = 9, GDT_CFloat32 = 10, GDT_CFloat64 = 11

dtype_fwd = {
    0: None,      # GDT_Unknown
    1: ubyte,     # GDT_Byte
    2: uint16,    # GDT_UInt16
    3: int16,     # GDT_Int16
    4: uint32,    # GDT_UInt32
    5: int32,       # GDT_Int32
    6: float32,     # GDT_Float32
    7: float64 }   # GDT_Float64

dtype_rev = dict((v, k) for k, v in dtype_fwd.items())
dtype_rev[uint8] = 1

typename_fwd = {
    0: 'Unknown',
    1: 'Byte',
    2: 'UInt16',
    3: 'Int16',
    4: 'UInt32',
    5: 'Int32',
    6: 'Float32',
    7: 'Float64' }

typename_rev = dict((v, k) for k, v in typename_fwd.items())

def _gdal_typename(dtype):
    return typename_fwd[dtype_rev[dtype]]




########NEW FILE########
__FILENAME__ = features
"""Functions for working with features in a raster dataset."""

import json
import time
import numpy
import rasterio
from rasterio._features import _shapes, _sieve, _rasterize


DEFAULT_TRANSFORM = [0, 1, 0, 0, 0, 1]


def shapes(image, mask=None, connectivity=4, transform=DEFAULT_TRANSFORM):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.

    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type. If a mask is provided, pixels for which the
    mask is `False` will be excluded from feature generation.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    if mask is not None and mask.dtype.type != rasterio.bool_:
        raise ValueError("Mask must be dtype rasterio.bool_")

    if connectivity not in (4, 8):
        raise ValueError("Connectivity Option must be 4 or 8")

    with rasterio.drivers():
        for s, v in _shapes(image, mask, connectivity, transform):
            yield s, v


def sieve(image, size, connectivity=4, output=None):
    """Returns a copy of the image, but with smaller features removed.

    Features smaller than the specified size have their pixel value
    replaced by that of the largest neighboring features.
    
    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    if output is not None and output.dtype.type != rasterio.ubyte:
        raise ValueError("Output must be dtype uint8/ubyte")

    with rasterio.drivers():
        return _sieve(image, size, connectivity)


def rasterize(
        shapes, 
        out_shape=None, fill=0, output=None,
        transform=DEFAULT_TRANSFORM,
        all_touched=False,
        default_value=255):
    """Returns an image array with points, lines, or polygons burned in.

    A different value may be specified for each shape.  The shapes may
    be georeferenced or may have image coordinates. An existing image
    array may be provided, or one may be created. By default, the center
    of image elements determines whether they are updated, but all
    touched elements may be optionally updated.

    :param shapes: an iterator over Fiona style geometry objects (with
    a default value of 255) or an iterator over (geometry, value) pairs.
    Values must be unsigned integer type (uint8).

    :param transform: GDAL style geotransform to be applied to the
    image.

    :param out_shape: shape of created image array
    :param fill: fill value for created image array
    :param output: alternatively, an existing image array

    :param all_touched: if True, will rasterize all pixels touched, 
    otherwise will use GDAL default method.
    :param default_value: value burned in for shapes if not provided as part of shapes.  Must be unsigned integer type (uint8).
    """

    if not isinstance(default_value, int) or default_value > 255 or default_value < 0:
        raise ValueError("default_value %s is not uint8/ubyte" % default_value)

    geoms = []
    for index, entry in enumerate(shapes):
        if isinstance(entry, (tuple, list)):
            geometry, value = entry
            if not isinstance(value, int) or value > 255 or value < 0:
                raise ValueError(
                    "Shape number %i, value '%s' is not uint8/ubyte" % (
                        index, value))
            geoms.append((geometry, value))
        else:
            geoms.append((entry, default_value))
    
    if out_shape is not None:
        out = numpy.empty(out_shape, dtype=rasterio.ubyte)
        out.fill(fill)
    elif output is not None:
        if output.dtype.type != rasterio.ubyte:
            raise ValueError("Output image must be dtype uint8/ubyte")
        out = output
    else:
        raise ValueError("An output image must be provided or specified")

    with rasterio.drivers():
        _rasterize(geoms, out, transform, all_touched)
    
    return out


########NEW FILE########
__FILENAME__ = five
# Python 2-3 compatibility

import sys
if sys.version_info[0] >= 3:
    string_types = str,
    text_type = str
    integer_types = int,
else:
    string_types = basestring,
    text_type = unicode
    integer_types = int, long

########NEW FILE########
__FILENAME__ = test_band
import rasterio

def test_band():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        b = rasterio.band(src, 1)
        assert b.ds == src
        assert b.bidx == 1
        assert b.dtype in src.dtypes
        assert b.shape == src.shape


########NEW FILE########
__FILENAME__ = test_blocks
import logging
import os.path
import unittest
import shutil
import subprocess
import sys
import tempfile

import numpy

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

class WindowTest(unittest.TestCase):
    def test_window_shape_errors(self):
        # Positive height and width are needed when stop is None.
        self.assertRaises(
            ValueError,
            rasterio.window_shape, 
            (((10, 20),(10, None)),) )
        self.assertRaises(
            ValueError,
            rasterio.window_shape, 
            (((None, 10),(10, 20)),) )
    def test_window_shape_None_start(self):
        self.assertEqual(
            rasterio.window_shape(((None,4),(None,102))),
            (4, 102))
    def test_window_shape_None_stop(self):
        self.assertEqual(
            rasterio.window_shape(((10, None),(10, None)), 100, 90),
            (90, 80))
    def test_window_shape_positive(self):
        self.assertEqual(
            rasterio.window_shape(((0,4),(1,102))),
            (4, 101))
    def test_window_shape_negative(self):
        self.assertEqual(
            rasterio.window_shape(((-10, None),(-10, None)), 100, 90),
            (10, 10))
        self.assertEqual(
            rasterio.window_shape(((~0, None),(~0, None)), 100, 90),
            (1, 1))
        self.assertEqual(
            rasterio.window_shape(((None, ~0),(None, ~0)), 100, 90),
            (99, 89))
    def test_eval(self):
        self.assertEqual(
            rasterio.eval_window(((-10, None), (-10, None)), 100, 90),
            ((90, 100), (80, 90)))
        self.assertEqual(
            rasterio.eval_window(((None, -10), (None, -10)), 100, 90),
            ((0, 90), (0, 80)))

def test_window_index():
    idx = rasterio.window_index(((0,4),(1,12)))
    assert len(idx) == 2
    r, c = idx
    assert r.start == 0
    assert r.stop == 4
    assert c.start == 1
    assert c.stop == 12
    arr = numpy.ones((20,20))
    assert arr[idx].shape == (4, 11)

class RasterBlocksTest(unittest.TestCase):
    def test_blocks(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(len(s.block_shapes), 3)
            self.assertEqual(s.block_shapes, [(3, 791), (3, 791), (3, 791)])
            windows = s.block_windows(1)
            (j,i), first = next(windows)
            self.assertEqual((j,i), (0, 0))
            self.assertEqual(first, ((0, 3), (0, 791)))
            (j, i), second = next(windows)
            self.assertEqual((j,i), (1, 0))
            self.assertEqual(second, ((3, 6), (0, 791)))
            (j, i), last = list(windows)[~0]
            self.assertEqual((j,i), (239, 0))
            self.assertEqual(last, ((717, 718), (0, 791)))
    def test_block_coverage(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(
                s.width*s.height,
                sum((w[0][1]-w[0][0])*(w[1][1]-w[1][0]) 
                    for ji, w in s.block_windows(1)))

class WindowReadTest(unittest.TestCase):
    def test_read_window(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            windows = s.block_windows(1)
            ji, first_window = next(windows)
            first_block = s.read_band(1, window=first_window)
            self.assertEqual(first_block.dtype, rasterio.ubyte)
            self.assertEqual(
                first_block.shape, 
                rasterio.window_shape(first_window))

class WindowWriteTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.tempdir)
    def test_write_window(self):
        name = os.path.join(self.tempdir, "test_write_window.tif")
        a = numpy.ones((50, 50), dtype=rasterio.ubyte) * 127
        with rasterio.open(
                name, 'w', 
                driver='GTiff', width=100, height=100, count=1, 
                dtype=a.dtype) as s:
            s.write_band(1, a, window=((30, 80), (10, 60)))
        # subprocess.call(["open", name])
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assert_(
            "Minimum=0.000, Maximum=127.000, "
            "Mean=31.750, StdDev=54.993" in info.decode('utf-8'),
            info)


########NEW FILE########
__FILENAME__ = test_colormap
import logging
import pytest
import subprocess
import sys

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_write_colormap(tmpdir):

    with rasterio.drivers():

        with rasterio.open('rasterio/tests/data/shade.tif') as src:
            shade = src.read_band(1)
            meta = src.meta

        tiffname = str(tmpdir.join('foo.tif'))
        
        with rasterio.open(tiffname, 'w', **meta) as dst:
            dst.write_band(1, shade)
            dst.write_colormap(1, {0: (255, 0, 0, 255), 255: (0, 0, 255, 255)})
            cmap = dst.colormap(1)
            assert cmap[0] == (255, 0, 0, 255)
            assert cmap[255] == (0, 0, 255, 255)

        with rasterio.open(tiffname) as src:
            cmap = src.colormap(1)
            assert cmap[0] == (255, 0, 0, 255)
            assert cmap[255] == (0, 0, 255, 255)

    # subprocess.call(['open', tiffname])


########NEW FILE########
__FILENAME__ = test_coords

import rasterio

def test_bounds():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.bounds == (101985.0, 2611485.0, 339315.0, 2826915.0)

def test_ul():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.ul(0, 0) == (101985.0, 2826915.0)
        assert src.ul(1, 0) == (101985.0, 2826614.95821727)
        assert src.ul(src.height, src.width) == (339315.0, 2611485.0)
        assert tuple(
            round(v, 6) for v in src.ul(~0, ~0)
            ) == (339014.962073, 2611785.041783)

def test_res():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert tuple(round(v, 6) for v in src.res) == (300.037927, 300.041783)

def test_index():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.index(101985.0, 2826915.0) == (0, 0)
        assert src.index(101985.0+400.0, 2826915.0) == (0, 1)
        assert src.index(101985.0+400.0, 2826915.0+700.0) == (2, 1)


########NEW FILE########
__FILENAME__ = test_copy
import logging
import os.path
import unittest
import shutil
import subprocess
import sys
import tempfile

import numpy

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

class CopyTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.tempdir)
    def test_copy(self):
        name = os.path.join(self.tempdir, 'test_copy.tif')
        rasterio.copy(
            'rasterio/tests/data/RGB.byte.tif', 
            name)
        info = subprocess.check_output(["gdalinfo", name])
        self.assert_("GTiff" in info.decode('utf-8'))

########NEW FILE########
__FILENAME__ = test_driver_management
import logging
import sys

import rasterio
from rasterio._drivers import driver_count, GDALEnv

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_drivers():
    with rasterio.drivers() as m:
        assert driver_count() > 0
        assert type(m) == GDALEnv
        
        n = rasterio.drivers()
        assert driver_count() > 0
        assert type(n) == GDALEnv

def test_options(tmpdir):
    """Test that setting CPL_DEBUG=True results in GDAL debug messages.
    """
    logger = logging.getLogger('GDAL')
    logger.setLevel(logging.DEBUG)
    logfile1 = str(tmpdir.join('test_options1.log'))
    fh = logging.FileHandler(logfile1)
    logger.addHandler(fh)
    
    # With CPL_DEBUG=True, expect debug messages from GDAL in
    # logfile1
    with rasterio.drivers(CPL_DEBUG=True):
        with rasterio.open("rasterio/tests/data/RGB.byte.tif") as src:
            pass

    log = open(logfile1).read()
    assert "GDAL: GDALOpen(rasterio/tests/data/RGB.byte.tif" in log
    
    # The GDAL env above having exited, CPL_DEBUG should be OFF.
    logfile2 = str(tmpdir.join('test_options2.log'))
    fh = logging.FileHandler(logfile2)
    logger.addHandler(fh)

    with rasterio.open("rasterio/tests/data/RGB.byte.tif") as src:
        pass
    
    # Expect no debug messages from GDAL.
    log = open(logfile2).read()
    assert "GDAL: GDALOpen(rasterio/tests/data/RGB.byte.tif" not in log


########NEW FILE########
__FILENAME__ = test_dtypes
import numpy

import rasterio
import rasterio.dtypes

def test_np_dt_uint8():
    assert rasterio.check_dtype(numpy.dtype(numpy.uint8))

def test_dt_ubyte():
    assert rasterio.check_dtype(numpy.dtype(rasterio.ubyte))

def test_gdal_name():
    assert rasterio.dtypes._gdal_typename(rasterio.ubyte) == 'Byte'
    assert rasterio.dtypes._gdal_typename(numpy.uint8) == 'Byte'
    assert rasterio.dtypes._gdal_typename(numpy.uint16) == 'UInt16'


########NEW FILE########
__FILENAME__ = test_features_rasterize
import logging
import sys
import numpy
import pytest
import rasterio
from rasterio.features import shapes, rasterize

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_rasterize_geometries():
    rows = cols = 10
    transform = [0, 1, 0, 0, 0, 1]
    geometry = {'type':'Polygon','coordinates':[[(2,2),(2,4.25),(4.25,4.25),(4.25,2),(2,2)]]}

    with rasterio.drivers():
        # we expect a subset of the pixels using default mode
        result = rasterize([geometry], out_shape=(rows, cols), transform=transform)
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = 255
        assert (result == truth).min() == True

        # we expect all touched pixels
        result = rasterize([geometry], out_shape=(rows, cols), transform=transform, all_touched=True)
        truth = numpy.zeros((rows, cols))
        truth[2:5, 2:5] = 255
        assert (result == truth).min() == True

        # we expect the pixel value to match the one we pass in
        value = 5
        result = rasterize([(geometry, value)], out_shape=(rows, cols), transform=transform)
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = value
        assert (result == truth).min() == True
        
        # Check the fill and default transform.
        # we expect the pixel value to match the one we pass in
        value = 5
        result = rasterize(
            [(geometry, value)], 
            out_shape=(rows, cols), 
            fill=1 )
        truth = numpy.ones((rows, cols))
        truth[2:4, 2:4] = value
        assert (result == truth).min() == True

        # we expect a ValueError if pixel value is not in 8 bit unsigned range
        value = 500
        with pytest.raises(ValueError):
            rasterize([(geometry, value)], out_shape=(rows, cols), transform=transform)


def test_rasterize_geometries_symmetric():
    """Make sure that rasterize is symmetric with shapes"""
    rows = cols = 10
    transform = [0, 1, 0, 0, 0, 1]
    truth = numpy.zeros((rows, cols), dtype=rasterio.ubyte)
    truth[2:5, 2:5] = 1
    with rasterio.drivers():
        s = shapes(truth, transform=transform)
        result = rasterize(s, out_shape=(rows, cols), transform=transform)
        assert (result == truth).min() == True

########NEW FILE########
__FILENAME__ = test_features_shapes
import logging
import sys

import numpy
import pytest

import rasterio
import rasterio.features as ftrz

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_shapes():
    """Access to shapes of labeled features"""
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15,5:15] = 127
    with rasterio.drivers():
        shapes = ftrz.shapes(image)
        shape, val = next(shapes)
        assert shape['type'] == 'Polygon'
        assert len(shape['coordinates']) == 2 # exterior and hole
        assert val == 0
        shape, val = next(shapes)
        assert shape['type'] == 'Polygon'
        assert len(shape['coordinates']) == 1 # no hole
        assert val == 127
        try:
            shape, val = next(shapes)
        except StopIteration:
            assert True
        else:
            assert False

def test_shapes_band_shortcut():
    """Access to shapes of labeled features"""
    with rasterio.drivers():
        with rasterio.open('rasterio/tests/data/shade.tif') as src:
            shapes = ftrz.shapes(rasterio.band(src, 1))
            shape, val = next(shapes)
            assert shape['type'] == 'Polygon'
            assert len(shape['coordinates']) == 1
            assert val == 255

def test_shapes_internal_driver_manager():
    """Access to shapes of labeled features"""
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15,5:15] = 127
    shapes = ftrz.shapes(image)
    shape, val = next(shapes)
    assert shape['type'] == 'Polygon'


def test_shapes_connectivity():
    """Test connectivity options"""
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:11,5:11] = 1
    image[11,11] = 1

    shapes = ftrz.shapes(image, connectivity=8)
    shape, val = next(shapes)
    assert len(shape['coordinates'][0]) == 9
    #Note: geometry is not technically valid at this point, it has a self intersection at 11,11

########NEW FILE########
__FILENAME__ = test_features_sieve
import logging
import sys

import numpy

import rasterio
import rasterio.features as ftrz

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_sieve():
    """Test sieving a 10x10 feature from an ndarray."""
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15,5:15] = 127
    # There should be some True pixels.
    assert image.any()
    # An attempt to sieve out features smaller than 100 should not change the
    # image.
    with rasterio.drivers():
        sieved_image = ftrz.sieve(image, 100)
        assert (
            list(map(list, numpy.where(sieved_image==127))) == 
            list(map(list, numpy.where(image==127))))
    # Setting the size to 100 should leave us an empty, False image.
    with rasterio.drivers():
        sieved_image = ftrz.sieve(image, 101)
        assert not sieved_image.any()

########NEW FILE########
__FILENAME__ = test_read
import unittest

import numpy

import rasterio

class ReaderContextTest(unittest.TestCase):
    def test_context(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(s.name, 'rasterio/tests/data/RGB.byte.tif')
            self.assertEqual(s.driver, 'GTiff')
            self.assertEqual(s.closed, False)
            self.assertEqual(s.count, 3)
            self.assertEqual(s.width, 791)
            self.assertEqual(s.height, 718)
            self.assertEqual(s.shape, (718, 791))
            self.assertEqual(s.dtypes, [rasterio.ubyte]*3)
            self.assertEqual(s.nodatavals, [0]*3)
            self.assertEqual(s.indexes, [1,2,3])
            self.assertEqual(s.crs['proj'], 'utm')
            self.assertEqual(s.crs['zone'], 18)
            self.assert_(s.crs_wkt.startswith('PROJCS'), s.crs_wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            self.assertEqual(
                s.transform, 
                [101985.0, 300.0379266750948, 0.0, 
                 2826915.0, 0.0, -300.041782729805])
            self.assertEqual(s.meta['crs'], s.crs)
            self.assertEqual(
                repr(s), 
                "<open RasterReader name='rasterio/tests/data/RGB.byte.tif' "
                "mode='r'>")
        self.assertEqual(s.closed, True)
        self.assertEqual(s.count, 3)
        self.assertEqual(s.width, 791)
        self.assertEqual(s.height, 718)
        self.assertEqual(s.shape, (718, 791))
        self.assertEqual(s.dtypes, [rasterio.ubyte]*3)
        self.assertEqual(s.nodatavals, [0]*3)
        self.assertEqual(s.crs['proj'], 'utm')
        self.assertEqual(s.crs['zone'], 18)
        self.assertEqual(
            s.transform, 
            [101985.0, 300.0379266750948, 0.0, 
             2826915.0, 0.0, -300.041782729805])
        self.assertEqual(
            repr(s),
            "<closed RasterReader name='rasterio/tests/data/RGB.byte.tif' "
            "mode='r'>")
    def test_derived_spatial(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assert_(s.crs_wkt.startswith('PROJCS'), s.crs_wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            for a, b in zip(s.ul(0, 0), (101985.0, 2826915.0)):
                self.assertAlmostEqual(a, b)
    def test_read_ubyte(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = s.read_band(1)
            self.assertEqual(a.dtype, rasterio.ubyte)
    def test_read_ubyte_bad_index(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertRaises(IndexError, s.read_band, 0)
    def test_read_ubyte_out(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((718, 791), dtype=rasterio.ubyte)
            a = s.read_band(1, a)
            self.assertEqual(a.dtype, rasterio.ubyte)
    def test_read_out_dtype_fail(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((718, 791), dtype=rasterio.float32)
            try:
                s.read_band(1, a)
            except ValueError as e:
                assert "the array's dtype 'float32' does not match the file's dtype" in str(e)
            except:
                assert "failed to catch exception" is False
    def test_read_out_shape_resample(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((7, 8), dtype=rasterio.ubyte)
            s.read_band(1, a)
            self.assert_(
                repr(a) == """array([[  0,   8,   5,   7,   0,   0,   0,   0],
       [  0,   6,  61,  15,  27,  15,  24, 128],
       [  0,  20, 152,  23,  15,  19,  28,   0],
       [  0,  17, 255,  25, 255,  22,  32,   0],
       [  9,   7,  14,  16,  19,  18,  36,   0],
       [  6,  27,  43, 207,  38,  31,  73,   0],
       [  0,   0,   0,   0,  74,  23,   0,   0]], dtype=uint8)""", a)


########NEW FILE########
__FILENAME__ = test_revolvingdoor
# Test of opening and closing and opening

import logging
import os.path
import shutil
import subprocess
import sys
import tempfile
import unittest

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
log = logging.getLogger('rasterio.tests')

class RevolvingDoorTest(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_write_colormap_revolving_door(self):

        with rasterio.open('rasterio/tests/data/shade.tif') as src:
            shade = src.read_band(1)
            meta = src.meta

        tiffname = os.path.join(self.tempdir, 'foo.tif')
        
        with rasterio.open(tiffname, 'w', **meta) as dst:
            dst.write_band(1, shade)

        with rasterio.open(tiffname) as src:
            pass


########NEW FILE########
__FILENAME__ = test_tags
#-*- coding: utf-8 -*-

import pytest
import rasterio

def test_tags_read():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.tags() == {'AREA_OR_POINT': 'Area'}
        assert src.tags(ns='IMAGE_STRUCTURE') == {'INTERLEAVE': 'PIXEL'}
        assert src.tags(ns='bogus') == {}
        assert 'STATISTICS_MAXIMUM' in src.tags(1)
        with pytest.raises(ValueError):
            tags = src.tags(4)

def test_tags_update(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(
            tiffname, 
            'w', 
            driver='GTiff', 
            count=1, 
            dtype=rasterio.uint8, 
            width=10, 
            height=10) as dst:

        dst.update_tags(a='1', b='2')
        dst.update_tags(1, c=3)
        with pytest.raises(ValueError):
            dst.update_tags(4, d=4)

        assert dst.tags() == {'a': '1', 'b': '2'}
        assert dst.tags(1) == {'c': '3' }
        
        # Assert that unicode tags work.
        # Russian text appropriated from pytest issue #319
        # https://bitbucket.org/hpk42/pytest/issue/319/utf-8-output-in-assertion-error-converted
        dst.update_tags(ns='rasterio_testing', rus=u'другая строка')
        assert dst.tags(ns='rasterio_testing') == {'rus': u'другая строка'}

    with rasterio.open(tiffname) as src:
        assert src.tags() == {'a': '1', 'b': '2'}
        assert src.tags(1) == {'c': '3'}
        assert src.tags(ns='rasterio_testing') == {'rus': u'другая строка'}


########NEW FILE########
__FILENAME__ = test_update

import shutil
import subprocess
import re
import numpy
import pytest

import rasterio

def test_update_tags(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    shutil.copy('rasterio/tests/data/RGB.byte.tif', tiffname)
    with rasterio.open(tiffname, 'r+') as f:
        f.update_tags(a='1', b='2')
        f.update_tags(1, c=3)
        with pytest.raises(ValueError):
            f.update_tags(4, d=4)
        assert f.tags() == {'AREA_OR_POINT': 'Area', 'a': '1', 'b': '2'}
        assert ('c', '3') in f.tags(1).items()
    info = subprocess.check_output(["gdalinfo", tiffname]).decode('utf-8')
    assert re.search("Metadata:\W+a=1\W+AREA_OR_POINT=Area\W+b=2", info)

def test_update_band(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    shutil.copy('rasterio/tests/data/RGB.byte.tif', tiffname)
    with rasterio.open(tiffname, 'r+') as f:
        f.write_band(1, numpy.zeros(f.shape, dtype=f.dtypes[0]))
    with rasterio.open(tiffname) as f:
        assert not f.read_band(1).any()

def test_update_spatial(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    shutil.copy('rasterio/tests/data/RGB.byte.tif', tiffname)
    with rasterio.open(tiffname, 'r+') as f:
        f.transform = [1.0, 1.0, 0.0, 0.0, 0.0, -1.0]
        f.crs = {'+init': 'epsg:4326'}
    with rasterio.open(tiffname) as f:
        assert f.transform == [1.0, 1.0, 0.0, 0.0, 0.0, -1.0]
        assert f.crs == {
            u'datum': u'WGS84', u'no_defs': True, u'proj': u'longlat'}

########NEW FILE########
__FILENAME__ = test_warp

import logging
import subprocess
import sys

import numpy

import rasterio
from rasterio._warp import reproject, RESAMPLING

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_reproject():
    """Ndarry to ndarray"""
    with rasterio.drivers():
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            source = src.read_band(1)
        dst_transform = [-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0]
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        destin = numpy.empty(src.shape, dtype=numpy.uint8)
        reproject(
            source, 
            destin,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform, 
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest )
    assert destin.any()
    try:
        import matplotlib.pyplot as plt
        plt.imshow(destin)
        plt.gray()
        plt.savefig('test_reproject.png')
    except:
        pass

def test_warp_from_file():
    """File to ndarray"""
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = [-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0]
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        destin = numpy.empty(src.shape, dtype=numpy.uint8)
        reproject(
            rasterio.band(src, 1), 
            destin, 
            dst_transform=dst_transform, 
            dst_crs=dst_crs)
    assert destin.any()
    try:
        import matplotlib.pyplot as plt
        plt.imshow(destin)
        plt.gray()
        plt.savefig('test_warp_from_filereproject.png')
    except:
        pass

def test_warp_from_to_file(tmpdir):
    """File to file"""
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = [-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0]
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        kwargs = src.meta.copy()
        kwargs.update(
            transform=dst_transform,
            crs=dst_crs)
        with rasterio.open(tiffname, 'w', **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(rasterio.band(src, i), rasterio.band(dst, i))
    # subprocess.call(['open', tiffname])

def test_warp_from_to_file_multi(tmpdir):
    """File to file"""
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = [-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0]
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        kwargs = src.meta.copy()
        kwargs.update(
            transform=dst_transform,
            crs=dst_crs)
        with rasterio.open(tiffname, 'w', **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(
                    rasterio.band(src, i), 
                    rasterio.band(dst, i),
                    num_threads=2)
    # subprocess.call(['open', tiffname])


########NEW FILE########
__FILENAME__ = test_write
import logging
import subprocess
import sys
import re
import numpy
import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_context(tmpdir):
    name = str(tmpdir.join("test_context.tif"))
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=1, 
            dtype=rasterio.ubyte) as s:
        assert s.name == name
        assert s.driver == 'GTiff'
        assert s.closed == False
        assert s.count == 1
        assert s.width == 100
        assert s.height == 100
        assert s.shape == (100, 100)
        assert s.indexes == [1]
        assert repr(s) == "<open RasterUpdater name='%s' mode='w'>" % name
    assert s.closed == True
    assert s.count == 1
    assert s.width == 100
    assert s.height == 100
    assert s.shape == (100, 100)
    assert repr(s) == "<closed RasterUpdater name='%s' mode='w'>" % name
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert "GTiff" in info
    assert "Size is 100, 100" in info
    assert "Band 1 Block=100x81 Type=Byte, ColorInterp=Gray" in info
    
def test_write_ubyte(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_ubyte.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=1, 
            dtype=a.dtype) as s:
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info
    
def test_write_float(tmpdir):
    name = str(tmpdir.join("test_write_float.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.float32) * 42.0
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=2,
            dtype=rasterio.float32) as s:
        assert s.dtypes == [rasterio.float32]*2
        s.write_band(1, a)
        s.write_band(2, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=42.000, Maximum=42.000, Mean=42.000, StdDev=0.000" in info
    
def test_write_crs_transform(tmpdir):
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = [101985.0, 300.0379266750948, 0.0,
                       2826915.0, 0.0, -300.041782729805]
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=1,
            crs={'units': 'm', 'no_defs': True, 'ellps': 'WGS84', 
                 'proj': 'utm', 'zone': 18},
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'PROJCS["UTM Zone 18, Northern Hemisphere",' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search("Pixel Size = \(300.03792\d+,-300.04178\d+\)", info)

def test_write_meta(tmpdir):
    name = str(tmpdir.join("test_write_meta.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    meta = dict(driver='GTiff', width=100, height=100, count=1)
    with rasterio.open(name, 'w', dtype=a.dtype, **meta) as s:
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info
    
def test_write_nodata(tmpdir):
    name = str(tmpdir.join("test_write_nodata.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=2, 
            dtype=a.dtype, nodata=0) as s:
        s.write_band(1, a)
        s.write_band(2, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "NoData Value=0" in info

def test_write_lzw(tmpdir):
    name = str(tmpdir.join("test_write_lzw.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w', 
            driver='GTiff', 
            width=100, height=100, count=1, 
            dtype=a.dtype,
            compress='LZW') as s:
        assert ('compress', 'LZW') in s.kwds.items()
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert "LZW" in info


########NEW FILE########
__FILENAME__ = tool

import code
import collections
import logging
import sys

import numpy

import rasterio


logger = logging.getLogger('rasterio')

Stats = collections.namedtuple('Stats', ['min', 'max', 'mean'])

def main(banner, dataset):

    def show(source, cmap='gray'):
        """Show a raster using matplotlib.

        The raster may be either an ndarray or a (dataset, bidx)
        tuple.
        """
        import matplotlib.pyplot as plt
        if isinstance(source, tuple):
            arr = source[0].read_band(source[1])
        else:
            arr = source
        plt.imshow(arr, cmap=cmap)
        plt.show()

    def stats(source):
        """Return a tuple with raster min, max, and mean.
        """
        if isinstance(source, tuple):
            arr = source[0].read_band(source[1])
        else:
            arr = source
        return Stats(numpy.min(arr), numpy.max(arr), numpy.mean(arr))

    code.interact(
        banner, local=dict(locals(), src=dataset, np=numpy, rio=rasterio))

    return 0

########NEW FILE########
__FILENAME__ = warp
"""Raster warping and reprojection"""

import rasterio
from rasterio._warp import reproject, RESAMPLING

########NEW FILE########
