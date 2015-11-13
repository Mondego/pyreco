__FILENAME__ = angle_util
from __future__ import absolute_import, print_function, division

import math
import struct

import numpy as np
from . import math_util


def almost_equal(a, b):
    c = struct.pack("<dd", a, b)
    d = struct.unpack("<qq", c)
    diff = abs(d[1] - d[0])
    return diff < 100


class Angle(object):

    def __init__(self, degrees='none', sexagesimal='none', latitude=False):

        if degrees != 'none':

            # Find out if the angle is negative
            negative = degrees < 0

            # Treat angle as positive
            degrees = np.abs(degrees)

            # Decompose angle into degrees, minutes, seconds
            m, d = math.modf(degrees)
            s, m = math.modf(m * 60.)
            s = s * 60.

            # Express degrees and minutes as integers
            d, m = int(round(d)), int(round(m))

            # Put back minus sign if negative
            if negative:
                d, m, s = -d, -m, -s

            # Set angle to tuple of degrees/minutes/seconds
            self.angle = (d, m, s)

        elif sexagesimal != 'none':
            self.angle = sexagesimal

        # Whether to keep the angle between 0 and 360 or -90 and 90
        self.latitude = latitude

        self.negative = False

        self._simplify()

    def _simplify(self):

        # Decompose angle
        d, m, s = self.angle

        # Make sure seconds are between 0. (inclusive) and 60. (exclusive)
        r = np.mod(s, 60.)
        m = m + int(round(s - r)) / 60
        s = r

        # Make sure minutes are between 0 and 59 (both inclusive)
        r = np.mod(m, 60)
        d = d + (m - r) / 60
        m = r

        # Make sure degrees are between 0 and 359 (both inclusive)
        d = np.mod(d, 360)

        # If angle is latitude, then:
        # - if degrees are between 90 and 270, angle is invalid
        # - if angle is between 270 and 360, subtract 360 degrees

        if self.latitude and d > 90:
            if d >= 270:
                self.negative = True
                d, m, s = 359 - d, 59 - m, 60. - s
                if s == 60.:
                    s = s - 60.
                    m = m + 1
                if m == 60:
                    m = m - 60.
                    d = d + 1
            else:
                raise Exception("latitude should be between -90 and 90 \
                    degrees")

        # Set new angle
        self.angle = (d, m, s)

    def todegrees(self):
        d, m, s = self.angle
        degrees = d + m / 60. + s / 3600.
        if self.negative:
            degrees = - degrees
        return degrees

    def tohours(self):

        d, m, s = self.angle

        rd = np.mod(d, 15)
        h = (d - rd) / 15

        rm = np.mod(m, 15)
        m = (m - rm) / 15 + rd * 4

        s = s / 15. + rm * 4.

        a = Angle(sexagesimal=(h, m, s), latitude=self.latitude)
        a.negative = self.negative

        return a

    def toround(self, rval=3):

        # Decompose angle
        d, m, s = self.angle

        # Round numbers:
        # 1: degrees only
        # 2: degrees and minutes
        # 3: degrees, minutes, and seconds
        # 4.n: degrees, minutes, and decimal seconds with n decimal places

        if rval < 2:
            n = int(round((rval - 1.) * 100))
            d = round(d + m / 60. + s / 3600., n)
            if n == 0:
                d = int(d)
            return d
        elif rval < 3:
            m = int(round(m + s / 60.))
            if m == 60:
                m = 0
                d = d + 1
            return (d, m)
        elif rval < 4:
            s = int(round(s))
            if s == 60:
                s = 0
                m = m + 1
            if m == 60:
                m = 0
                d = d + 1
            return (d, m, s)
        else:
            n = int(round((rval - 4.) * 100))
            s = round(s, n)
            if s == 60.:
                s = 0.
                m = m + 1
            if m == 60:
                m = 0
                d = d + 1
            return (d, m, s)

    def tostringlist(self, format='ddd:mm:ss', sep=("d", "m", "s")):

        format = format.replace('h', 'd')

        r = 1
        if '.d' in format:
            r = 1
            pos = format.find('.')
            nd = len(format[pos + 1:])
            r = r + nd / 100.
        if 'mm' in format:
            r = 2
        if 'ss' in format:
            r = 3
        if '.s' in format:
            r = 4
            pos = format.find('.')
            ns = len(format[pos + 1:])
            r = r + ns / 100.

        tup = self.toround(rval=r)
        if type(tup) == tuple:
            tup = list(tup)
        else:
            tup = [tup]

        string = []

        if 'dd' in format:
            if '.d' in format:
                string.append(("%0" + str(nd + 3) + "." + str(nd) + "f") % \
                    tup[0] + sep[0])
            else:
                string.append("%i" % tup[0] + sep[0])
        if 'mm' in format:
            string.append("%02i" % tup[1] + sep[1])
        if 'ss' in format and not '.s' in format:
            string.append("%02i" % tup[2] + sep[2])
        if 'ss.s' in format:
            string.append(("%0" + str(ns + 3) + "." + str(ns) + "f") % tup[2] + sep[2])

        # If style is colons, need to remove trailing colon
        if len(string) >= 1 and sep[0] == ':' and not 'mm' in format:
            string[0] = string[0][:-1]
        if len(string) >= 2 and sep[1] == ':' and not 'ss' in format:
            string[1] = string[1][:-1]

        if self.latitude:
            if self.negative:
                string[0] = "-" + string[0]
            else:
                string[0] = "+" + string[0]

        return string

    def __str__(self):
        return self.angle.__str__()

    def __repr__(self):
        return self.angle.__repr__()

    def __add__(self, other):

        s = self.angle[2] + other.angle[2]
        m = self.angle[1] + other.angle[1]
        d = self.angle[0] + other.angle[0]

        s = Angle(sexagesimal=(d, m, s), latitude=self.latitude)
        s._simplify()

        return s

    def __mul__(self, other):

        d, m, s = self.angle
        s = s * other
        m = m * other
        d = d * other

        if self.latitude and self.negative:
            d, m, s = -d, -m, -s

        s = Angle(sexagesimal=(d, m, s), latitude=self.latitude)
        s._simplify()

        return s

    def __eq__(self, other):
        return self.angle[0] == other.angle[0] \
           and self.angle[1] == other.angle[1] \
           and almost_equal(self.angle[2], other.angle[2])

    def __div__(self, other):
        '''
        Divide an angle by another

        This method calculates the division using the angles in degrees, and
        then corrects for any rouding errors if the division should be exact.
        '''

        # Find division of angles in degrees
        div = self.todegrees() / other.todegrees()

        # Find the nearest integer
        divint = int(round(div))

        # Check whether the denominator multiplied by this number is exactly
        # the numerator
        if other * divint == self:
            return divint
        else:
            return div

    __truediv__ = __div__

def smart_round_angle_sexagesimal(x, latitude=False, hours=False):

    d, m, s = 0, 0, 0.

    divisors_360 = math_util.divisors(360)
    divisors_10 = math_util.divisors(10)
    divisors_60 = math_util.divisors(60)

    if hours:
        x /= 15.

    if x >= 1:
        d = math_util.closest(divisors_360, x)
    else:
        x = x * 60.
        if x >= 1:
            m = math_util.closest(divisors_60, x)
        else:
            x = x * 60.
            if x >= 1:
                s = math_util.closest(divisors_60, x)
            else:
                t = 1.
                while True:
                    t = t * 10.
                    x = x * 10.
                    if x >= 1:
                        s = math_util.closest(divisors_10, x) / t
                        break

    a = Angle(sexagesimal=(d, m, s), latitude=latitude)

    if hours:
        a *= 15

    return a


def smart_round_angle_decimal(x, latitude=False):

    divisors_360 = math_util.divisors(360)
    divisors_10 = math_util.divisors(10)

    if x >= 1:
        d = math_util.closest(divisors_360, x)
    else:
        t = 1.
        while True:
            t = t * 10.
            x = x * 10.
            if x >= 1:
                d = math_util.closest(divisors_10, x) / t
                break

    a = Angle(degrees=d, latitude=latitude)

    return a


def _get_label_precision(format, latitude=False):

    # Find base spacing
    if "mm" in format:
        if "ss" in format:
            if "ss.s" in format:
                n_decimal = len(format.split('.')[1])
                label_spacing = Angle(sexagesimal=(0, 0, 10 ** (-n_decimal)), latitude=latitude)
            else:
                label_spacing = Angle(sexagesimal=(0, 0, 1), latitude=latitude)
        else:
            label_spacing = Angle(sexagesimal=(0, 1, 0), latitude=latitude)
    elif "." in format:
        ns = len(format.split('.')[1])
        label_spacing = Angle(degrees=10 ** (-ns), latitude=latitude)
    else:
        label_spacing = Angle(sexagesimal=(1, 0, 0), latitude=latitude)

    # Check if hours are used instead of degrees
    if "hh" in format:
        label_spacing *= 15

    return label_spacing


class InconsistentSpacing(Exception):
    pass


def _check_format_spacing_consistency(format, spacing):
    '''
    Check whether the format can correctly show labels with the specified
    spacing.

    For example, if the tick spacing is set to 1 arcsecond, but the format is
    set to dd:mm, then the labels cannot be correctly shown. Similarly, if the
    spacing is set to 1/1000 of a degree, or 3.6", then a format of dd:mm:ss
    will cause rounding errors, because the spacing includes fractional
    arcseconds.

    This function will raise a warning if the format and spacing are
    inconsistent.
    '''

    label_spacing = _get_label_precision(format)

    if type(spacing / label_spacing) != int:
        raise InconsistentSpacing('Label format and tick spacing are inconsistent. Make sure that the tick spacing is a multiple of the smallest angle that can be represented by the specified format (currently %s). For example, if the format is dd:mm:ss.s, then the tick spacing has to be a multiple of 0.1". Similarly, if the format is hh:mm:ss, then the tick spacing has to be a multiple of 15". If you got this error as a result of interactively zooming in to a small region, this means that the default display format for the labels is not accurate enough, so you will need to increase the format precision.' % format)

########NEW FILE########
__FILENAME__ = aplpy
from __future__ import absolute_import, print_function, division

from distutils import version
import os
import operator

import matplotlib

if version.LooseVersion(matplotlib.__version__) < version.LooseVersion('1.0.0'):
    raise Exception("matplotlib 1.0.0 or later is required for APLpy")

import matplotlib.pyplot as mpl
import mpl_toolkits.axes_grid.parasite_axes as mpltk

WCS_TYPES = []
HDU_TYPES = []
HDULIST_TYPES = []

# We need to be able to accept PyFITS objects if users have old scripts that
# are reading FITS files with this instead of Astropy
try:
    import pyfits
    HDU_TYPES.append(pyfits.PrimaryHDU)
    HDU_TYPES.append(pyfits.ImageHDU)
    HDULIST_TYPES.append(pyfits.HDUList)
    del pyfits
except ImportError:
    pass

# Similarly, we need to accept PyWCS objects
try:
    import pywcs
    WCS_TYPES.append(pywcs.WCS)
    del pywcs
except ImportError:
    pass

from astropy.io import fits
HDU_TYPES.append(fits.PrimaryHDU)
HDU_TYPES.append(fits.ImageHDU)
HDULIST_TYPES.append(fits.HDUList)

from astropy.wcs import WCS
WCS_TYPES.append(WCS)
del WCS

# Convert to tuples so that these work when calling isinstance()
HDU_TYPES = tuple(HDU_TYPES)
HDULIST_TYPES = tuple(HDULIST_TYPES)
WCS_TYPES = tuple(WCS_TYPES)

import numpy as np

from matplotlib.patches import Circle, Rectangle, Ellipse, Polygon, FancyArrow
from matplotlib.collections import PatchCollection, LineCollection

from astropy import log
import astropy.utils.exceptions as aue

from . import contour_util
from . import convolve_util
from . import image_util
from . import header as header_util
from . import wcs_util
from . import slicer

from .layers import Layers
from .grid import Grid
from .ticks import Ticks
from .labels import TickLabels
from .axis_labels import AxisLabels
from .overlays import Beam, Scalebar
from .regions import Regions
from .colorbar import Colorbar
from .normalize import APLpyNormalize
from .frame import Frame

from .decorators import auto_refresh, fixdocstring

from .deprecated import Deprecated

class Parameters():
    '''
    A class to contain the current plotting parameters
    '''
    pass


class FITSFigure(Layers, Regions, Deprecated):

    "A class for plotting FITS files."

    _parameters = Parameters()

    @auto_refresh
    def __init__(self, data, hdu=0, figure=None, subplot=(1, 1, 1),
                 downsample=False, north=False, convention=None,
                 dimensions=[0, 1], slices=[], auto_refresh=True,
                 **kwargs):
        '''
        Create a FITSFigure instance.

        Parameters
        ----------

        data : see below

            The FITS file to open. The following data types can be passed:

                 string
                 astropy.io.fits.PrimaryHDU
                 astropy.io.fits.ImageHDU
                 pyfits.PrimaryHDU
                 pyfits.ImageHDU
                 astropy.wcs.WCS
                 np.ndarray
                 RGB image with AVM meta-data

        hdu : int, optional
            By default, the image in the primary HDU is read in. If a
            different HDU is required, use this argument.

        figure : ~matplotlib.figure.Figure, optional
            If specified, a subplot will be added to this existing
            matplotlib figure() instance, rather than a new figure
            being created from scratch.

        subplot : tuple or list, optional
            If specified, a subplot will be added at this position. If a tuple
            of three values, the tuple should contain the standard matplotlib
            subplot parameters, i.e. (ny, nx, subplot). If a list of four
            values, the list should contain [xmin, ymin, dx, dy] where xmin
            and ymin are the position of the bottom left corner of the
            subplot, and dx and dy are the width and height of the subplot
            respectively. These should all be given in units of the figure
            width and height. For example, [0.1, 0.1, 0.8, 0.8] will almost
            fill the entire figure, leaving a 10 percent margin on all sides.

        downsample : int, optional
            If this option is specified, the image will be downsampled
            by a factor *downsample* when reading in the data.

        north : str, optional
            Whether to rotate the image so that the North Celestial
            Pole is up. Note that this option requires Montage to be
            installed.

        convention : str, optional
            This is used in cases where a FITS header can be interpreted
            in multiple ways. For example, for files with a -CAR
            projection and CRVAL2=0, this can be set to 'wells' or
            'calabretta' to choose the appropriate convention.

        dimensions : tuple or list, optional
            The index of the axes to use if the data has more than three
            dimensions.

        slices : tuple or list, optional
            If a FITS file with more than two dimensions is specified,
            then these are the slices to extract. If all extra dimensions
            only have size 1, then this is not required.

        auto_refresh : str, optional
            Whether to refresh the figure automatically every time a
            plotting method is called. This can also be set using the
            set_auto_refresh method.

        kwargs
            Any additional arguments are passed on to matplotlib's Figure() class.
            For example, to set the figure size, use the figsize=(xsize, ysize)
            argument (where xsize and ysize are in inches). For more information
            on these additional arguments, see the *Optional keyword arguments*
            section in the documentation for `Figure
            <http://matplotlib.sourceforge.net/api/figure_api.html?
            #matplotlib.figure.Figure>`_
        '''

        # Set whether to automatically refresh the display
        self.set_auto_refresh(auto_refresh)

        if not 'figsize' in kwargs:
            kwargs['figsize'] = (10, 9)

        if isinstance(data, basestring) and data.split('.')[-1].lower() in ['png', 'jpg', 'tif']:

            try:
                from PIL import Image
            except ImportError:
                try:
                    import Image
                except ImportError:
                    raise ImportError("The Python Imaging Library (PIL) is required to read in RGB images")

            try:
                import pyavm
            except ImportError:
                raise ImportError("PyAVM is required to read in AVM meta-data from RGB images")

            if version.LooseVersion(pyavm.__version__) < version.LooseVersion('0.9.1'):
                raise ImportError("PyAVM installation is not recent enough "
                                  "(version 0.9.1 or later is required).")

            from pyavm import AVM

            # Remember image filename
            self._rgb_image = data

            # Find image size
            nx, ny = Image.open(data).size

            # Now convert AVM information to WCS
            data = AVM.from_image(data).to_wcs()

            # Need to scale CDELT values sometimes the AVM meta-data is only really valid for the full-resolution image
            data.wcs.cdelt = [data.wcs.cdelt[0] * nx / float(nx), data.wcs.cdelt[1] * ny / float(ny)]
            data.wcs.crpix = [data.wcs.crpix[0] / nx * float(nx), data.wcs.crpix[1] / ny * float(ny)]

            # Update the NAXIS values with the true dimensions of the RGB image
            data.nx = nx
            data.ny = ny

        if isinstance(data, WCS_TYPES):
            wcs = data
            if not hasattr(wcs, 'naxis1'):
                raise aue.AstropyDeprecationWarning('WCS no longer stores information about NAXISn '
                                                    'so it is not possibly to instantiate a FITSFigure '
                                                    'from WCS alone')

            if wcs.naxis != 2:
                raise ValueError("FITSFigure initialization via WCS objects can only be done with 2-dimensional WCS objects")
            header = wcs.to_header()
            header.update('NAXIS1', wcs.naxis1)
            header.update('NAXIS2', wcs.naxis2)
            nx = header['NAXIS%i' % (dimensions[0] + 1)]
            ny = header['NAXIS%i' % (dimensions[1] + 1)]
            self._data = np.zeros((ny, nx), dtype=float)
            self._header = header
            self._wcs = wcs_util.WCS(header, dimensions=dimensions, slices=slices, relax=True)
            self._wcs.nx = nx
            self._wcs.ny = ny
            if downsample:
                log.warning("downsample argument is ignored if data passed is a WCS object")
                downsample = False
            if north:
                log.warning("north argument is ignored if data passed is a WCS object")
                north = False
        else:
            self._data, self._header, self._wcs = self._get_hdu(data, hdu, north, \
                convention=convention, dimensions=dimensions, slices=slices)
            self._wcs.nx = self._header['NAXIS%i' % (dimensions[0] + 1)]
            self._wcs.ny = self._header['NAXIS%i' % (dimensions[1] + 1)]

        # Downsample if requested
        if downsample:
            nx_new = self._wcs.nx - np.mod(self._wcs.nx, downsample)
            ny_new = self._wcs.ny - np.mod(self._wcs.ny, downsample)
            self._data = self._data[0:ny_new, 0:nx_new]
            self._data = image_util.resample(self._data, downsample)
            self._wcs.nx, self._wcs.ny = nx_new, ny_new

        # Open the figure
        if figure:
            self._figure = figure
        else:
            self._figure = mpl.figure(**kwargs)

        # Create first axis instance
        if type(subplot) == list and len(subplot) == 4:
            self._ax1 = mpltk.HostAxes(self._figure, subplot, adjustable='datalim')
        elif type(subplot) == tuple and len(subplot) == 3:
            self._ax1 = mpltk.SubplotHost(self._figure, *subplot)
        else:
            raise ValueError("subplot= should be either a tuple of three values, or a list of four values")

        self._ax1.toggle_axisline(False)

        self._figure.add_axes(self._ax1)

        # Create second axis instance
        self._ax2 = self._ax1.twin()
        self._ax2.set_frame_on(False)

        self._ax2.toggle_axisline(False)

        # Turn off autoscaling
        self._ax1.set_autoscale_on(False)
        self._ax2.set_autoscale_on(False)

        # Force zorder of parasite axes
        self._ax2.xaxis.set_zorder(2.5)
        self._ax2.yaxis.set_zorder(2.5)

        # Store WCS in axes
        self._ax1._wcs = self._wcs
        self._ax2._wcs = self._wcs

        # Set view to whole FITS file
        self._initialize_view()

        # Initialize ticks
        self.ticks = Ticks(self)

        # Initialize labels
        self.axis_labels = AxisLabels(self)
        self.tick_labels = TickLabels(self)

        self.frame = Frame(self)

        self._ax1.format_coord = self.tick_labels._cursor_position

        # Initialize layers list
        self._initialize_layers()

        # Find generating function for vmin/vmax
        self._auto_v = image_util.percentile_function(self._data)

        # Set image holder to be empty
        self.image = None

        # Set default theme
        self.set_theme(theme='pretty')

    def _get_hdu(self, data, hdu, north, convention=None, dimensions=[0, 1], slices=[]):

        if isinstance(data, basestring):

            filename = data

            # Check file exists
            if not os.path.exists(filename):
                raise IOError("File not found: " + filename)

            # Read in FITS file
            try:
                hdulist = fits.open(filename)
            except:
                raise IOError("An error occured while reading the FITS file")

            # Check whether the HDU specified contains any data, otherwise
            # cycle through all HDUs to find one that contains valid image data
            if hdulist[hdu].data is None:
                found = False
                for alt_hdu in range(len(hdulist)):
                    if isinstance(hdulist[alt_hdu], HDU_TYPES):
                        if hdulist[alt_hdu].data is not None:
                            log.warning("hdu=%i does not contain any data, using hdu=%i instead" % (hdu, alt_hdu))
                            hdu = hdulist[alt_hdu]
                            found = True
                            break
                if not found:
                    raise Exception("FITS file does not contain any image data")

            else:
                hdu = hdulist[hdu]

        elif type(data) == np.ndarray:

            hdu = fits.ImageHDU(data)

        elif isinstance(data, HDU_TYPES):

            hdu = data

        elif isinstance(data, HDULIST_TYPES):

            hdu = data[hdu]

        else:

            raise Exception("data argument should either be a filename, an HDU object from astropy.io.fits or pyfits, a WCS object from astropy.wcs or pywcs, or a Numpy array.")

        # Check dimensions= argument
        if type(dimensions) not in [list, tuple]:
            raise ValueError('dimensions= should be a list or a tuple')
        if len(set(dimensions)) != 2 or len(dimensions) != 2:
            raise ValueError("dimensions= should be a tuple of two different values")
        if dimensions[0] < 0 or dimensions[0] > hdu.header['NAXIS'] - 1:
            raise ValueError('values of dimensions= should be between %i and %i' % (0, hdu.header['NAXIS'] - 1))
        if dimensions[1] < 0 or dimensions[1] > hdu.header['NAXIS'] - 1:
            raise ValueError('values of dimensions= should be between %i and %i' % (0, hdu.header['NAXIS'] - 1))

        # Reproject to face north if requested
        if north:
            try:
                import montage_wrapper as montage
            except ImportError:
                raise Exception("Both the Montage command-line tools and the"
                                " montage-wrapper Python module are required"
                                " to use the north= argument")
            hdu = montage.reproject_hdu(hdu, north_aligned=True)

        # Now copy the data and header to new objects, since in PyFITS the two
        # attributes are linked, which can lead to confusing behavior. We just
        # need to copy the header to avoid memory issues - as long as one item
        # is copied, the two variables are decoupled.
        data = hdu.data
        header = hdu.header.copy()
        del hdu

        # If slices wasn't specified, check if we can guess
        shape = data.shape
        if len(shape) > 2:
            n_total = reduce(operator.mul, shape)
            n_image = shape[len(shape) - 1 - dimensions[0]] \
                    * shape[len(shape) - 1 - dimensions[1]]
            if n_total == n_image:
                slices = [0 for i in range(1, len(shape) - 1)]
                log.info("Setting slices=%s" % str(slices))

        # Extract slices
        data = slicer.slice_hypercube(data, header, dimensions=dimensions, slices=slices)

        # Check header
        header = header_util.check(header, convention=convention, dimensions=dimensions)

        # Parse WCS info
        wcs = wcs_util.WCS(header, dimensions=dimensions, slices=slices, relax=True)

        return data, header, wcs

    @auto_refresh
    def set_xaxis_coord_type(self, coord_type):
        '''
        Set the type of x coordinate.

        Options are:

        * ``scalar``: treat the values are normal decimal scalar values
        * ``longitude``: treat the values as a longitude in the 0 to 360 range
        * ``latitude``: treat the values as a latitude in the -90 to 90 range
        '''
        self._wcs.set_xaxis_coord_type(coord_type)

    @auto_refresh
    def set_yaxis_coord_type(self, coord_type):
        '''
        Set the type of y coordinate.

        Options are:

        * ``scalar``: treat the values are normal decimal scalar values
        * ``longitude``: treat the values as a longitude in the 0 to 360 range
        * ``latitude``: treat the values as a latitude in the -90 to 90 range
        '''
        self._wcs.set_yaxis_coord_type(coord_type)

    @auto_refresh
    def set_system_latex(self, usetex):
        '''
        Set whether to use a real LaTeX installation or the built-in matplotlib LaTeX.

        Parameters
        ----------

        usetex : str
            Whether to use a real LaTex installation (True) or the built-in
            matplotlib LaTeX (False). Note that if the former is chosen, an
            installation of LaTex is required.
        '''
        mpl.rc('text', usetex=usetex)

    @auto_refresh
    def recenter(self, x, y, radius=None, width=None, height=None):
        '''
        Center the image on a given position and with a given radius.

        Either the radius or width/heigh arguments should be specified. The
        units of the radius or width/height should be the same as the world
        coordinates in the WCS. For images of the sky, this is often (but not
        always) degrees.

        Parameters
        ----------

        x, y : float
            Coordinates to center on

        radius : float, optional
            Radius of the region to view. This produces a square plot.

        width : float, optional
            Width of the region to view. This should be given in
            conjunction with the height argument.

        height : float, optional
            Height of the region to view. This should be given in
            conjunction with the width argument.
        '''

        xpix, ypix = wcs_util.world2pix(self._wcs, x, y)

        sx, sy = wcs_util.pixel_scale(self._wcs)

        if radius:
            dx_pix = radius / sx
            dy_pix = radius / sy
        elif width and height:
            dx_pix = width / sx * 0.5
            dy_pix = height / sy * 0.5
        else:
            raise Exception("Need to specify either radius= or width= and height= arguments")

        if xpix + dx_pix < self._extent[0] or \
           xpix - dx_pix > self._extent[1] or \
           ypix + dy_pix < self._extent[2] or \
           ypix - dy_pix > self._extent[3]:

            raise Exception("Zoom region falls outside the image")

        self._ax1.set_xlim(xpix - dx_pix, xpix + dx_pix)
        self._ax1.set_ylim(ypix - dy_pix, ypix + dy_pix)

    @auto_refresh
    def show_grayscale(self, vmin=None, vmid=None, vmax=None,
                       pmin=0.25, pmax=99.75,
                       stretch='linear', exponent=2, invert='default',
                       smooth=None, kernel='gauss', aspect='equal',
                       interpolation='nearest'):
        '''
        Show a grayscale image of the FITS file.

        Parameters
        ----------

        vmin : None or float, optional
            Minimum pixel value to use for the grayscale. If set to None,
            the minimum pixel value is determined using pmin (default).

        vmax : None or float, optional
            Maximum pixel value to use for the grayscale. If set to None,
            the maximum pixel value is determined using pmax (default).

        pmin : float, optional
            Percentile value used to determine the minimum pixel value to
            use for the grayscale if vmin is set to None. The default
            value is 0.25%.

        pmax : float, optional
            Percentile value used to determine the maximum pixel value to
            use for the grayscale if vmax is set to None. The default
            value is 99.75%.

        stretch : { 'linear', 'log', 'sqrt', 'arcsinh', 'power' }, optional
            The stretch function to use

        vmid : None or float, optional
            Baseline value used for the log and arcsinh stretches. If
            set to None, this is set to zero for log stretches and to
            vmin - (vmax - vmin) / 30. for arcsinh stretches

        exponent : float, optional
            If stretch is set to 'power', this is the exponent to use

        invert : str, optional
            Whether to invert the grayscale or not. The default is False,
            unless set_theme is used, in which case the default depends on
            the theme.

        smooth : int or tuple, optional
            Default smoothing scale is 3 pixels across. User can define
            whether they want an NxN kernel (integer), or NxM kernel
            (tuple). This argument corresponds to the 'gauss' and 'box'
            smoothing kernels.

        kernel : { 'gauss', 'box', numpy.array }, optional
            Default kernel used for smoothing is 'gauss'. The user can
            specify if they would prefer 'gauss', 'box', or a custom
            kernel. All kernels are normalized to ensure flux retention.

        aspect : { 'auto', 'equal' }, optional
            Whether to change the aspect ratio of the image to match that
            of the axes ('auto') or to change the aspect ratio of the axes
            to match that of the data ('equal'; default)

        interpolation : str, optional
            The type of interpolation to use for the image. The default is
            'nearest'. Other options include 'none' (no interpolation,
            meaning that if exported to a postscript file, the grayscale
            will be output at native resolution irrespective of the dpi
            setting), 'bilinear', 'bicubic', and many more (see the
            matplotlib documentation for imshow).
        '''

        if invert == 'default':
            invert = self._get_invert_default()

        if invert:
            cmap = 'gist_yarg'
        else:
            cmap = 'gray'

        self.show_colorscale(vmin=vmin, vmid=vmid, vmax=vmax,
                             pmin=pmin, pmax=pmax,
                             stretch=stretch, exponent=exponent, cmap=cmap,
                             smooth=smooth, kernel=kernel, aspect=aspect,
                             interpolation=interpolation)

    @auto_refresh
    def hide_grayscale(self, *args, **kwargs):
        self.hide_colorscale(*args, **kwargs)

    @auto_refresh
    def show_colorscale(self, vmin=None, vmid=None, vmax=None, \
                             pmin=0.25, pmax=99.75,
                             stretch='linear', exponent=2, cmap='default',
                             smooth=None, kernel='gauss', aspect='equal',
                             interpolation='nearest'):
        '''
        Show a colorscale image of the FITS file.

        Parameters
        ----------

        vmin : None or float, optional
            Minimum pixel value to use for the colorscale. If set to None,
            the minimum pixel value is determined using pmin (default).

        vmax : None or float, optional
            Maximum pixel value to use for the colorscale. If set to None,
            the maximum pixel value is determined using pmax (default).

        pmin : float, optional
            Percentile value used to determine the minimum pixel value to
            use for the colorscale if vmin is set to None. The default
            value is 0.25%.

        pmax : float, optional
            Percentile value used to determine the maximum pixel value to
            use for the colorscale if vmax is set to None. The default
            value is 99.75%.

        stretch : { 'linear', 'log', 'sqrt', 'arcsinh', 'power' }, optional
            The stretch function to use

        vmid : None or float, optional
            Baseline value used for the log and arcsinh stretches. If
            set to None, this is set to zero for log stretches and to
            vmin - (vmax - vmin) / 30. for arcsinh stretches

        exponent : float, optional
            If stretch is set to 'power', this is the exponent to use

        cmap : str, optional
            The name of the colormap to use

        smooth : int or tuple, optional
            Default smoothing scale is 3 pixels across. User can define
            whether they want an NxN kernel (integer), or NxM kernel
            (tuple). This argument corresponds to the 'gauss' and 'box'
            smoothing kernels.

        kernel : { 'gauss', 'box', numpy.array }, optional
            Default kernel used for smoothing is 'gauss'. The user can
            specify if they would prefer 'gauss', 'box', or a custom
            kernel. All kernels are normalized to ensure flux retention.

        aspect : { 'auto', 'equal' }, optional
            Whether to change the aspect ratio of the image to match that
            of the axes ('auto') or to change the aspect ratio of the axes
            to match that of the data ('equal'; default)

        interpolation : str, optional
            The type of interpolation to use for the image. The default is
            'nearest'. Other options include 'none' (no interpolation,
            meaning that if exported to a postscript file, the colorscale
            will be output at native resolution irrespective of the dpi
            setting), 'bilinear', 'bicubic', and many more (see the
            matplotlib documentation for imshow).
        '''

        if cmap == 'default':
            cmap = self._get_colormap_default()

        min_auto = np.equal(vmin, None)
        max_auto = np.equal(vmax, None)

        # The set of available functions
        cmap = mpl.cm.get_cmap(cmap)

        if min_auto:
            vmin = self._auto_v(pmin)

        if max_auto:
            vmax = self._auto_v(pmax)

        # Prepare normalizer object
        normalizer = APLpyNormalize(stretch=stretch, exponent=exponent,
                                    vmid=vmid, vmin=vmin, vmax=vmax)

        # Adjust vmin/vmax if auto
        if min_auto:
            if stretch == 'linear':
                vmin = -0.1 * (vmax - vmin) + vmin
            log.info("Auto-setting vmin to %10.3e" % vmin)

        if max_auto:
            if stretch == 'linear':
                vmax = 0.1 * (vmax - vmin) + vmax
            log.info("Auto-setting vmax to %10.3e" % vmax)

        # Update normalizer object
        normalizer.vmin = vmin
        normalizer.vmax = vmax

        if self.image:
            self.image.set_visible(True)
            self.image.set_norm(normalizer)
            self.image.set_cmap(cmap=cmap)
            self.image.origin = 'lower'
            self.image.set_interpolation(interpolation)
            self.image.set_data(convolve_util.convolve(self._data,
                                                       smooth=smooth,
                                                       kernel=kernel))
        else:
            self.image = self._ax1.imshow(
                convolve_util.convolve(self._data, smooth=smooth, kernel=kernel),
                cmap=cmap, interpolation=interpolation, origin='lower',
                extent=self._extent, norm=normalizer, aspect=aspect)

        xmin, xmax = self._ax1.get_xbound()
        if xmin == 0.0:
            self._ax1.set_xlim(0.5, xmax)

        ymin, ymax = self._ax1.get_ybound()
        if ymin == 0.0:
            self._ax1.set_ylim(0.5, ymax)

        if hasattr(self, 'colorbar'):
            self.colorbar.update()

    @auto_refresh
    def hide_colorscale(self):
        self.image.set_visible(False)

    @auto_refresh
    def set_nan_color(self, color):
        '''
        Set the color for NaN pixels.

        Parameters
        ----------
        color : str
            This can be any valid matplotlib color
        '''
        cm = self.image.get_cmap()
        cm.set_bad(color)
        self.image.set_cmap(cm)

    @auto_refresh
    def show_rgb(self, filename=None, interpolation='nearest', vertical_flip=False, horizontal_flip=False, flip=False):
        '''
        Show a 3-color image instead of the FITS file data.

        Parameters
        ----------

        filename, optional
            The 3-color image should have exactly the same dimensions
            as the FITS file, and will be shown with exactly the same
            projection. If FITSFigure was initialized with an
            AVM-tagged RGB image, the filename is not needed here.

        vertical_flip : str, optional
            Whether to vertically flip the RGB image

        horizontal_flip : str, optional
            Whether to horizontally flip the RGB image
        '''

        try:
            from PIL import Image
        except ImportError:
            try:
                import Image
            except ImportError:
                raise ImportError("The Python Imaging Library (PIL) is required to read in RGB images")

        if flip:
            log.warning("Note that show_rgb should now correctly flip RGB images, so the flip= argument is now deprecated. If you still need to flip an image vertically or horizontally, you can use the vertical_flip= and horizontal_flip arguments instead.")

        if filename is None:
            if hasattr(self, '_rgb_image'):
                image = Image.open(self._rgb_image)
            else:
                raise Exception("Need to specify the filename of an RGB image")
        else:
            image = Image.open(filename)

        if image_util._matplotlib_pil_bug_present():
            vertical_flip = True

        if vertical_flip:
            image = image.transpose(Image.FLIP_TOP_BOTTOM)

        if horizontal_flip:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)

        # We need to explicitly say origin='upper' to override any
        # matplotlibrc settings.
        self.image = self._ax1.imshow(image, extent=self._extent, interpolation=interpolation, origin='upper')

    @auto_refresh
    def show_contour(self, data=None, hdu=0, layer=None, levels=5, filled=False, cmap=None, colors=None, returnlevels=False, convention=None, dimensions=[0, 1], slices=[], smooth=None, kernel='gauss', overlap=False, **kwargs):
        '''
        Overlay contours on the current plot.

        Parameters
        ----------

        data : see below

            The FITS file to plot contours for. The following data types can be passed:

                 string
                 astropy.io.fits.PrimaryHDU
                 astropy.io.fits.ImageHDU
                 pyfits.PrimaryHDU
                 pyfits.ImageHDU
                 astropy.wcs.WCS
                 np.ndarray

        hdu : int, optional
            By default, the image in the primary HDU is read in. If a
            different HDU is required, use this argument.

        layer : str, optional
            The name of the contour layer. This is useful for giving
            custom names to layers (instead of contour_set_n) and for
            replacing existing layers.

        levels : int or list, optional
            This can either be the number of contour levels to compute
            (if an integer is provided) or the actual list of contours
            to show (if a list of floats is provided)

        filled : str, optional
            Whether to show filled or line contours

        cmap : str, optional
            The colormap to use for the contours

        colors : str or tuple, optional
            If a single string is provided, all contour levels will be
            shown in this color. If a tuple of strings is provided,
            each contour will be colored according to the corresponding
            tuple element.

        returnlevels : str, optional
            Whether to return the list of contours to the caller.

        convention : str, optional
            This is used in cases where a FITS header can be interpreted
            in multiple ways. For example, for files with a -CAR
            projection and CRVAL2=0, this can be set to 'wells' or
            'calabretta' to choose the appropriate convention.

        dimensions : tuple or list, optional
            The index of the axes to use if the data has more than three
            dimensions.

        slices : tuple or list, optional
            If a FITS file with more than two dimensions is specified,
            then these are the slices to extract. If all extra dimensions
            only have size 1, then this is not required.

        smooth : int or tuple, optional
            Default smoothing scale is 3 pixels across. User can define
            whether they want an NxN kernel (integer), or NxM kernel
            (tuple). This argument corresponds to the 'gauss' and 'box'
            smoothing kernels.

        kernel : { 'gauss' , 'box' , numpy.array }, optional
            Default kernel used for smoothing is 'gauss'. The user can
            specify if they would prefer 'gauss', 'box', or a custom
            kernel. All kernels are normalized to ensure flux retention.

        overlap str, optional
            Whether to include only contours that overlap with the image
            area. This significantly speeds up the drawing of contours and
            reduces file size when using a file for the contours covering
            a much larger area than the image.

        kwargs
            Additional keyword arguments (such as alpha, linewidths, or
            linestyles) will be passed on directly to Matplotlib's
            :meth:`~matplotlib.axes.Axes.contour` or
            :meth:`~matplotlib.axes.Axes.contourf` methods. For more
            information on these additional arguments, see the *Optional
            keyword arguments* sections in the documentation for those
            methods.
        '''
        if layer:
            self.remove_layer(layer, raise_exception=False)

        if cmap:
            cmap = mpl.cm.get_cmap(cmap)
        elif not colors:
            cmap = mpl.cm.get_cmap('jet')

        if data is not None:
            data_contour, header_contour, wcs_contour = self._get_hdu(data, \
                    hdu, False, convention=convention, dimensions=dimensions, \
                    slices=slices)
        else:
            data_contour = self._data
            header_contour = self._header
            wcs_contour = self._wcs

        wcs_contour.nx = header_contour['NAXIS%i' % (dimensions[0] + 1)]
        wcs_contour.ny = header_contour['NAXIS%i' % (dimensions[1] + 1)]

        image_contour = convolve_util.convolve(data_contour, smooth=smooth, kernel=kernel)
        extent_contour = (0.5, wcs_contour.nx + 0.5, 0.5, wcs_contour.ny + 0.5)

        if type(levels) == int:
            auto_levels = image_util.percentile_function(image_contour)
            vmin = auto_levels(0.25)
            vmax = auto_levels(99.75)
            levels = np.linspace(vmin, vmax, levels)

        if filled:
            c = self._ax1.contourf(image_contour, levels, extent=extent_contour, cmap=cmap, colors=colors, **kwargs)
        else:
            c = self._ax1.contour(image_contour, levels, extent=extent_contour, cmap=cmap, colors=colors, **kwargs)

        if layer:
            contour_set_name = layer
        else:
            self._contour_counter += 1
            contour_set_name = 'contour_set_' + str(self._contour_counter)

        contour_util.transform(c, wcs_contour, self._wcs, filled=filled, overlap=overlap)

        self._layers[contour_set_name] = c

        if returnlevels:
            return levels

    # This method plots markers. The input should be an Nx2 array with WCS coordinates
    # in degree format.

    @auto_refresh
    def show_markers(self, xw, yw, layer=False, **kwargs):
        '''
        Overlay markers on the current plot.

        Parameters
        ----------

        xw : list or `~numpy.ndarray`
            The x postions of the markers (in world coordinates)

        yw : list or `~numpy.ndarray`
            The y positions of the markers (in world coordinates)

        layer : str, optional
            The name of the scatter layer. This is useful for giving
            custom names to layers (instead of marker_set_n) and for
            replacing existing layers.

        kwargs
            Additional keyword arguments (such as marker, facecolor,
            edgecolor, alpha, or linewidth) will be passed on directly to
            Matplotlib's :meth:`~matplotlib.axes.Axes.scatter` method (in
            particular, have a look at the *Optional keyword arguments* in the
            documentation for that method).
        '''

        if not 'c' in kwargs:
            kwargs.setdefault('edgecolor', 'red')
            kwargs.setdefault('facecolor', 'none')

        kwargs.setdefault('s', 30)

        if layer:
            self.remove_layer(layer, raise_exception=False)

        xp, yp = wcs_util.world2pix(self._wcs, xw, yw)
        s = self._ax1.scatter(xp, yp, **kwargs)

        if layer:
            marker_set_name = layer
        else:
            self._scatter_counter += 1
            marker_set_name = 'marker_set_' + str(self._scatter_counter)

        self._layers[marker_set_name] = s

    # Show circles. Different from markers as this method allows more definitions
    # for the circles.
    @auto_refresh
    def show_circles(self, xw, yw, radius, layer=False, zorder=None, **kwargs):
        '''
        Overlay circles on the current plot.

        Parameters
        ----------

        xw : list or `~numpy.ndarray`
            The x positions of the centers of the circles (in world coordinates)

        yw : list or `~numpy.ndarray`
            The y positions of the centers of the circles (in world coordinates)

        radius : int or float or list or `~numpy.ndarray`
            The radii of the circles (in world coordinates)

        layer : str, optional
            The name of the circle layer. This is useful for giving
            custom names to layers (instead of circle_set_n) and for
            replacing existing layers.

        kwargs
            Additional keyword arguments (such as facecolor, edgecolor, alpha,
            or linewidth) are passed to Matplotlib
            :class:`~matplotlib.collections.PatchCollection` class, and can be
            used to control the appearance of the circles.
        '''

        if np.isscalar(xw):
            xw = np.array([xw])
        else:
            xw = np.array(xw)

        if np.isscalar(yw):
            yw = np.array([yw])
        else:
            yw = np.array(yw)

        if np.isscalar(radius):
            radius = np.repeat(radius, len(xw))
        else:
            radius = np.array(radius)

        if not 'facecolor' in kwargs:
            kwargs.setdefault('facecolor', 'none')

        if layer:
            self.remove_layer(layer, raise_exception=False)

        xp, yp = wcs_util.world2pix(self._wcs, xw, yw)
        rp = 3600.0 * radius / wcs_util.arcperpix(self._wcs)

        patches = []
        for i in range(len(xp)):
            patches.append(Circle((xp[i], yp[i]), radius=rp[i]))

        # Due to bugs in matplotlib, we need to pass the patch properties
        # directly to the PatchCollection rather than use match_original.
        p = PatchCollection(patches, **kwargs)

        if zorder is not None:
            p.zorder = zorder
        c = self._ax1.add_collection(p)

        if layer:
            circle_set_name = layer
        else:
            self._circle_counter += 1
            circle_set_name = 'circle_set_' + str(self._circle_counter)

        self._layers[circle_set_name] = c

    @auto_refresh
    def show_ellipses(self, xw, yw, width, height, angle=0, layer=False, zorder=None, **kwargs):
        '''
        Overlay ellipses on the current plot.

        Parameters
        ----------

        xw : list or `~numpy.ndarray`
            The x positions of the centers of the ellipses (in world coordinates)

        yw : list or `~numpy.ndarray`
            The y positions of the centers of the ellipses (in world coordinates)

        width : int or float or list or `~numpy.ndarray`
            The width of the ellipse (in world coordinates)

        height : int or float or list or `~numpy.ndarray`
            The height of the ellipse (in world coordinates)

        angle : int or float or list or `~numpy.ndarray`, optional
            rotation in degrees (anti-clockwise). Default
            angle is 0.0.

        layer : str, optional
            The name of the ellipse layer. This is useful for giving
            custom names to layers (instead of ellipse_set_n) and for
            replacing existing layers.

        kwargs
            Additional keyword arguments (such as facecolor, edgecolor, alpha,
            or linewidth) are passed to Matplotlib
            :class:`~matplotlib.collections.PatchCollection` class, and can be
            used to control the appearance of the ellipses.
        '''

        if np.isscalar(xw):
            xw = np.array([xw])
        else:
            xw = np.array(xw)

        if np.isscalar(yw):
            yw = np.array([yw])
        else:
            yw = np.array(yw)

        if np.isscalar(width):
            width = np.repeat(width, len(xw))
        else:
            width = np.array(width)

        if np.isscalar(angle):
            angle = np.repeat(angle, len(xw))
        else:
            angle = np.array(angle)

        if np.isscalar(height):
            height = np.repeat(height, len(xw))
        else:
            height = np.array(height)

        if not 'facecolor' in kwargs:
            kwargs.setdefault('facecolor', 'none')

        if layer:
            self.remove_layer(layer, raise_exception=False)

        xp, yp = wcs_util.world2pix(self._wcs, xw, yw)
        wp = 3600.0 * width / wcs_util.arcperpix(self._wcs)
        hp = 3600.0 * height / wcs_util.arcperpix(self._wcs)
        ap = angle

        patches = []
        for i in range(len(xp)):
            patches.append(Ellipse((xp[i], yp[i]), width=wp[i], height=hp[i], angle=ap[i]))

        # Due to bugs in matplotlib, we need to pass the patch properties
        # directly to the PatchCollection rather than use match_original.
        p = PatchCollection(patches, **kwargs)

        if zorder is not None:
            p.zorder = zorder
        c = self._ax1.add_collection(p)

        if layer:
            ellipse_set_name = layer
        else:
            self._ellipse_counter += 1
            ellipse_set_name = 'ellipse_set_' + str(self._ellipse_counter)

        self._layers[ellipse_set_name] = c

    @auto_refresh
    def show_rectangles(self, xw, yw, width, height, layer=False, zorder=None, **kwargs):
        '''
        Overlay rectangles on the current plot.

        Parameters
        ----------

        xw : list or `~numpy.ndarray`
            The x positions of the centers of the rectangles (in world coordinates)

        yw : list or `~numpy.ndarray`
            The y positions of the centers of the rectangles (in world coordinates)

        width : int or float or list or `~numpy.ndarray`
            The width of the rectangle (in world coordinates)

        height : int or float or list or `~numpy.ndarray`
            The height of the rectangle (in world coordinates)

        layer : str, optional
            The name of the rectangle layer. This is useful for giving
            custom names to layers (instead of rectangle_set_n) and for
            replacing existing layers.

        kwargs
            Additional keyword arguments (such as facecolor, edgecolor, alpha,
            or linewidth) are passed to Matplotlib
            :class:`~matplotlib.collections.PatchCollection` class, and can be
            used to control the appearance of the rectangles.
        '''

        if np.isscalar(xw):
            xw = np.array([xw])
        else:
            xw = np.array(xw)

        if np.isscalar(yw):
            yw = np.array([yw])
        else:
            yw = np.array(yw)

        if np.isscalar(width):
            width = np.repeat(width, len(xw))
        else:
            width = np.array(width)

        if np.isscalar(height):
            height = np.repeat(height, len(xw))
        else:
            height = np.array(height)

        if not 'facecolor' in kwargs:
            kwargs.setdefault('facecolor', 'none')

        if layer:
            self.remove_layer(layer, raise_exception=False)

        xp, yp = wcs_util.world2pix(self._wcs, xw, yw)
        wp = 3600.0 * width / wcs_util.arcperpix(self._wcs)
        hp = 3600.0 * height / wcs_util.arcperpix(self._wcs)

        patches = []
        xp = xp - wp / 2.
        yp = yp - hp / 2.
        for i in range(len(xp)):
            patches.append(Rectangle((xp[i], yp[i]), width=wp[i], height=hp[i]))

        # Due to bugs in matplotlib, we need to pass the patch properties
        # directly to the PatchCollection rather than use match_original.
        p = PatchCollection(patches, **kwargs)

        if zorder is not None:
            p.zorder = zorder
        c = self._ax1.add_collection(p)

        if layer:
            rectangle_set_name = layer
        else:
            self._rectangle_counter += 1
            rectangle_set_name = 'rectangle_set_' + str(self._rectangle_counter)

        self._layers[rectangle_set_name] = c

    @auto_refresh
    def show_lines(self, line_list, layer=False, zorder=None, **kwargs):
        '''
        Overlay lines on the current plot.

        Parameters
        ----------

        line_list : list
             A list of one or more 2xN numpy arrays which contain
             the [x, y] positions of the vertices in world coordinates.

        layer : str, optional
            The name of the line(s) layer. This is useful for giving
            custom names to layers (instead of line_set_n) and for
            replacing existing layers.

        kwargs
            Additional keyword arguments (such as color, offsets, linestyle,
            or linewidth) are passed to Matplotlib
            :class:`~matplotlib.collections.LineCollection` class, and can be used to
            control the appearance of the lines.
        '''

        if not 'color' in kwargs:
            kwargs.setdefault('color', 'none')

        if layer:
            self.remove_layer(layer, raise_exception=False)

        lines = []

        for line in line_list:
            xp, yp = wcs_util.world2pix(self._wcs, line[0, :], line[1, :])
            lines.append(np.column_stack((xp, yp)))

        l = LineCollection(lines, **kwargs)
        if zorder is not None:
            l.zorder = zorder
        c = self._ax1.add_collection(l)

        if layer:
            line_set_name = layer
        else:
            self._linelist_counter += 1
            line_set_name = 'line_set_' + str(self._linelist_counter)

        self._layers[line_set_name] = c

    @auto_refresh
    def show_arrows(self, x, y, dx, dy, width='auto', head_width='auto',
                    head_length='auto', length_includes_head=True, layer=False, zorder=None, **kwargs):
        '''
        Overlay arrows on the current plot.

        Parameters
        ----------

        x, y, dx, dy : float or list or `~numpy.ndarray`
            Origin and displacement of the arrows in world coordinates.
            These can either be scalars to plot a single arrow, or lists or
            arrays to plot multiple arrows.

        width : float, optional
            The width of the arrow body, in pixels (default: 2% of the
            arrow length)

        head_width : float, optional
            The width of the arrow head, in pixels (default: 5% of the
            arrow length)

        head_length : float, optional
            The length of the arrow head, in pixels (default: 5% of the
            arrow length)

        length_includes_head : bool, optional
            Whether the head includes the length

        layer : str, optional
            The name of the arrow(s) layer. This is useful for giving
            custom names to layers (instead of line_set_n) and for
            replacing existing layers.

        kwargs
            Additional keyword arguments (such as facecolor, edgecolor, alpha,
            or linewidth) are passed to Matplotlib
            :class:`~matplotlib.collections.PatchCollection` class, and can be
            used to control the appearance of the arrows.
        '''

        if layer:
            self.remove_layer(layer, raise_exception=False)

        arrows = []

        if np.isscalar(x):
            x, y, dx, dy = [x], [y], [dx], [dy]

        for i in range(len(x)):

            xp1, yp1 = wcs_util.world2pix(self._wcs, x[i], y[i])
            xp2, yp2 = wcs_util.world2pix(self._wcs, x[i] + dx[i], y[i] + dy[i])

            if width == 'auto':
                width = 0.02 * np.sqrt((xp2 - xp1) ** 2 + (yp2 - yp1) ** 2)

            if head_width == 'auto':
                head_width = 0.1 * np.sqrt((xp2 - xp1) ** 2 + (yp2 - yp1) ** 2)

            if head_length == 'auto':
                head_length = 0.1 * np.sqrt((xp2 - xp1) ** 2 + (yp2 - yp1) ** 2)

            arrows.append(FancyArrow(xp1, yp1, xp2 - xp1, yp2 - yp1,
                                     width=width, head_width=head_width,
                                     head_length=head_length,
                                     length_includes_head=length_includes_head)
                                     )

        # Due to bugs in matplotlib, we need to pass the patch properties
        # directly to the PatchCollection rather than use match_original.
        p = PatchCollection(arrows, **kwargs)

        if zorder is not None:
            p.zorder = zorder
        c = self._ax1.add_collection(p)

        if layer:
            line_set_name = layer
        else:
            self._linelist_counter += 1
            line_set_name = 'arrow_set_' + str(self._linelist_counter)

        self._layers[line_set_name] = c

    @auto_refresh
    def show_polygons(self, polygon_list, layer=False, zorder=None, **kwargs):
        '''
        Overlay polygons on the current plot.

        Parameters
        ----------

        polygon_list : list or tuple
            A list of one or more 2xN or Nx2 Numpy arrays which contain
            the [x, y] positions of the vertices in world coordinates.
            Note that N should be greater than 2.

        layer : str, optional
            The name of the circle layer. This is useful for giving
            custom names to layers (instead of circle_set_n) and for
            replacing existing layers.

        kwargs
            Additional keyword arguments (such as facecolor, edgecolor, alpha,
            or linewidth) are passed to Matplotlib
            :class:`~matplotlib.collections.PatchCollection` class, and can be
            used to control the appearance of the polygons.
        '''

        if not 'facecolor' in kwargs:
            kwargs.setdefault('facecolor', 'none')

        if layer:
            self.remove_layer(layer, raise_exception=False)

        if type(polygon_list) not in [list, tuple]:
            raise Exception("polygon_list should be a list or tuple of Numpy arrays")

        pix_polygon_list = []
        for polygon in polygon_list:

            if type(polygon) is not np.ndarray:
                raise Exception("Polygon should be given as a Numpy array")

            if polygon.shape[0] == 2 and polygon.shape[1] > 2:
                xw = polygon[0, :]
                yw = polygon[1, :]
            elif polygon.shape[0] > 2 and polygon.shape[1] == 2:
                xw = polygon[:, 0]
                yw = polygon[:, 1]
            else:
                raise Exception("Polygon should have dimensions 2xN or Nx2 with N>2")

            xp, yp = wcs_util.world2pix(self._wcs, xw, yw)
            pix_polygon_list.append(np.column_stack((xp, yp)))

        patches = []
        for i in range(len(pix_polygon_list)):
            patches.append(Polygon(pix_polygon_list[i], **kwargs))

        # Due to bugs in matplotlib, we need to pass the patch properties
        # directly to the PatchCollection rather than use match_original.
        p = PatchCollection(patches, **kwargs)

        if zorder is not None:
            p.zorder = zorder
        c = self._ax1.add_collection(p)

        if layer:
            poly_set_name = layer
        else:
            self._poly_counter += 1
            poly_set_name = 'poly_set_' + str(self._poly_counter)

        self._layers[poly_set_name] = c

    @auto_refresh
    @fixdocstring
    def add_label(self, x, y, text, relative=False, color='black',
                  family=None, style=None, variant=None, stretch=None,
                  weight=None, size=None, fontproperties=None,
                  horizontalalignment='center', verticalalignment='center',
                  layer=None, **kwargs):
        '''
        Add a text label.

        Parameters
        ----------

        x, y : float
            Coordinates of the text label

        text : str
            The label

        relative : str, optional
            Whether the coordinates are to be interpreted as world
            coordinates (e.g. RA/Dec or longitude/latitude), or
            coordinates relative to the axes (where 0.0 is left or bottom
            and 1.0 is right or top).

        common: color, family, style, variant, stretch, weight, size, fontproperties, horizontalalignment, verticalalignment
        '''

        if layer:
            self.remove_layer(layer, raise_exception=False)

        # Can't pass fontproperties=None to text. Only pass it if it is not None.
        if fontproperties:
            kwargs['fontproperties'] = fontproperties

        if not np.isscalar(x):
            raise Exception("x should be a single value")

        if not np.isscalar(y):
            raise Exception("y should be a single value")

        if not np.isscalar(text):
            raise Exception("text should be a single value")

        if relative:
            l = self._ax1.text(x, y, text, color=color,
                               family=family, style=style, variant=variant,
                               stretch=stretch, weight=weight, size=size,
                               horizontalalignment=horizontalalignment,
                               verticalalignment=verticalalignment,
                               transform=self._ax1.transAxes, **kwargs)
        else:
            xp, yp = wcs_util.world2pix(self._wcs, x, y)
            l = self._ax1.text(xp, yp, text, color=color,
                               family=family, style=style, variant=variant,
                               stretch=stretch, weight=weight, size=size,
                               horizontalalignment=horizontalalignment,
                               verticalalignment=verticalalignment, **kwargs)

        if layer:
            label_name = layer
        else:
            self._label_counter += 1
            label_name = 'label_' + str(self._label_counter)

        self._layers[label_name] = l

    def set_auto_refresh(self, refresh):
        '''
        Set whether the display should refresh after each method call.

        Parameters
        ----------
        refresh : str
            Whether to refresh the display every time a FITSFigure
            method is called. The default is True. If set to false,
            the display can be refreshed manually using the refresh()
            method
        '''
        self._parameters.auto_refresh = refresh

    def refresh(self, force=True):
        '''
        Refresh the display.

        Parameters
        ----------
        force : str, optional
            If set to False, refresh() will only have an effect if
            auto refresh is on. If set to True, the display will be
            refreshed whatever the auto refresh setting is set to.
            The default is True.
        '''
        if self._parameters.auto_refresh or force:
            self._figure.canvas.draw()

    def save(self, filename, dpi=None, transparent=False, adjust_bbox=True, max_dpi=300, format=None):
        '''
        Save the current figure to a file.

        Parameters
        ----------

        filename : str or fileobj
            The name of the file to save the plot to. This can be for
            example a PS, EPS, PDF, PNG, JPEG, or SVG file. Note that it
            is also possible to pass file-like object.

        dpi : float, optional
            The output resolution, in dots per inch. If the output file
            is a vector graphics format (such as PS, EPS, PDF or SVG) only
            the image itself will be rasterized. If the output is a PS or
            EPS file and no dpi is specified, the dpi is automatically
            calculated to match the resolution of the image. If this value is
            larger than max_dpi, then dpi is set to max_dpi.

        transparent : str, optional
            Whether to preserve transparency

        adjust_bbox : str, optional
            Auto-adjust the bounding box for the output

        max_dpi : float, optional
            The maximum resolution to output images at. If no maximum is
            wanted, enter None or 0.

        format : str, optional
            By default, APLpy tries to guess the file format based on the
            file extension, but the format can also be specified
            explicitly. Should be one of 'eps', 'ps', 'pdf', 'svg', 'png'.
        '''

        if isinstance(filename, basestring) and format is None:
            format = os.path.splitext(filename)[1].lower()[1:]

        if dpi is None and format in ['eps', 'ps', 'pdf']:
            width = self._ax1.get_position().width * self._figure.get_figwidth()
            interval = self._ax1.xaxis.get_view_interval()
            nx = interval[1] - interval[0]
            if max_dpi:
                dpi = np.minimum(nx / width, max_dpi)
            else:
                dpi = nx / width
            log.info("Auto-setting resolution to %g dpi" % dpi)

        artists = []
        if adjust_bbox:
            for artist in self._layers.values():
                if isinstance(artist, matplotlib.text.Text):
                    artists.append(artist)
            self._figure.savefig(filename, dpi=dpi, transparent=transparent, bbox_inches='tight', bbox_extra_artists=artists, format=format)
        else:
            self._figure.savefig(filename, dpi=dpi, transparent=transparent, format=format)

    def _initialize_view(self):

        self._ax1.xaxis.set_view_interval(+0.5, self._wcs.nx + 0.5, ignore=True)
        self._ax1.yaxis.set_view_interval(+0.5, self._wcs.ny + 0.5, ignore=True)
        self._ax2.xaxis.set_view_interval(+0.5, self._wcs.nx + 0.5, ignore=True)
        self._ax2.yaxis.set_view_interval(+0.5, self._wcs.ny + 0.5, ignore=True)

        # set the image extent to FITS pixel coordinates
        self._extent = (0.5, self._wcs.nx + 0.5, 0.5, self._wcs.ny + 0.5)

    def _get_invert_default(self):
        return self._figure.apl_grayscale_invert_default

    def _get_colormap_default(self):
        return self._figure.apl_colorscale_cmap_default

    @auto_refresh
    def set_theme(self, theme):
        '''
        Set the axes, ticks, grid, and image colors to a certain style (experimental).

        Parameters
        ----------

        theme : str
            The theme to use. At the moment, this can be 'pretty' (for
            viewing on-screen) and 'publication' (which makes the ticks
            and grid black, and displays the image in inverted grayscale)
       '''

        if theme == 'pretty':
            self.frame.set_color('black')
            self.frame.set_linewidth(1.0)
            self.ticks.set_color('white')
            self.ticks.set_length(7)
            self._figure.apl_grayscale_invert_default = False
            self._figure.apl_colorscale_cmap_default = 'jet'
            if self.image:
                self.image.set_cmap(cmap=mpl.cm.get_cmap('jet'))
        elif theme == 'publication':
            self.frame.set_color('black')
            self.frame.set_linewidth(1.0)
            self.ticks.set_color('black')
            self.ticks.set_length(7)
            self._figure.apl_grayscale_invert_default = True
            self._figure.apl_colorscale_cmap_default = 'gist_heat'
            if self.image:
                self.image.set_cmap(cmap=mpl.cm.get_cmap('gist_yarg'))

    def world2pixel(self, xw, yw):
        '''
        Convert world to pixel coordinates.

        Parameters
        ----------
        xw : float or list or `~numpy.ndarray`
            x world coordinate
        yw : float or list or `~numpy.ndarray`
            y world coordinate

        Returns
        -------
        xp : float or list or `~numpy.ndarray`
            x pixel coordinate
        yp : float or list or `~numpy.ndarray`
            y pixel coordinate
        '''

        return wcs_util.world2pix(self._wcs, xw, yw)

    def pixel2world(self, xp, yp):
        '''
        Convert pixel to world coordinates.

        Parameters
        ----------
        xp : float or list or `~numpy.ndarray`
            x pixel coordinate
        yp : float or list or `~numpy.ndarray`
            y pixel coordinate

        Returns
        -------
        xw : float or list or `~numpy.ndarray`
            x world coordinate
        yw : float or list or `~numpy.ndarray`
            y world coordinate
        '''

        return wcs_util.pix2world(self._wcs, xp, yp)

    @auto_refresh
    def add_grid(self, *args, **kwargs):
        '''
        Add a coordinate to the current figure.

        Once this method has been run, a grid attribute becomes available,
        and can be used to control the aspect of the grid::

            >>> f = aplpy.FITSFigure(...)
            >>> ...
            >>> f.add_grid()
            >>> f.grid.set_color('white')
            >>> f.grid.set_alpha(0.5)
            >>> ...
        '''
        if hasattr(self, 'grid'):
            raise Exception("Grid already exists")
        try:
            self.grid = Grid(self)
            self.grid.show(*args, **kwargs)
        except:
            del self.grid
            raise

    @auto_refresh
    def remove_grid(self):
        '''
        Removes the grid from the current figure.
        '''
        self.grid._remove()
        del self.grid

    @auto_refresh
    def add_beam(self, *args, **kwargs):
        '''
        Add a beam to the current figure.

        Once this method has been run, a beam attribute becomes available,
        and can be used to control the aspect of the beam::

            >>> f = aplpy.FITSFigure(...)
            >>> ...
            >>> f.add_beam()
            >>> f.beam.set_color('white')
            >>> f.beam.set_hatch('+')
            >>> ...

        If more than one beam is added, the beam object becomes a list. In
        this case, to control the aspect of one of the beams, you will need tp
        specify the beam index::

            >>> ...
            >>> f.beam[2].set_hatch('/')
            >>> ...
        '''

        # Initalize the beam and set parameters
        b = Beam(self)
        b.show(*args, **kwargs)

        if hasattr(self, 'beam'):
            if type(self.beam) is list:
                self.beam.append(b)
            else:
                self.beam = [self.beam, b]
        else:
            self.beam = b

    @auto_refresh
    def remove_beam(self, beam_index=None):
        '''
        Removes the beam from the current figure.

        If more than one beam is present, the index of the beam should be
        specified using beam_index=
        '''

        if type(self.beam) is list:

            if beam_index is None:
                raise Exception("More than one beam present - use beam_index= to specify which one to remove")
            else:
                b = self.beam.pop(beam_index)
                b._remove()
                del b

            # If only one beam is present, remove containing list
            if len(self.beam) == 1:
                self.beam = self.beam[0]

        else:

            self.beam._remove()
            del self.beam

    @auto_refresh
    def add_scalebar(self, length, *args, **kwargs):
        '''
        Add a scalebar to the current figure.

        Once this method has been run, a scalebar attribute becomes
        available, and can be used to control the aspect of the scalebar::

            >>> f = aplpy.FITSFigure(...)
            >>> ...
            >>> f.add_scalebar(0.01) # length has to be specified
            >>> f.scalebar.set_label('100 AU')
            >>> ...
        '''
        if hasattr(self, 'scalebar'):
            raise Exception("Scalebar already exists")
        try:
            self.scalebar = Scalebar(self)
            self.scalebar.show(length, *args, **kwargs)
        except:
            del self.scalebar
            raise

    @auto_refresh
    def remove_scalebar(self):
        '''
        Removes the scalebar from the current figure.
        '''
        self.scalebar._remove()
        del self.scalebar

    @auto_refresh
    def add_colorbar(self, *args, **kwargs):
        '''
        Add a colorbar to the current figure.

        Once this method has been run, a colorbar attribute becomes
        available, and can be used to control the aspect of the colorbar::

            >>> f = aplpy.FITSFigure(...)
            >>> ...
            >>> f.add_colorbar()
            >>> f.colorbar.set_width(0.3)
            >>> f.colorbar.set_location('top')
            >>> ...
        '''
        if hasattr(self, 'colorbar'):
            raise Exception("Colorbar already exists")
        if self.image is None:
            raise Exception("No image is shown, so a colorbar cannot be displayed")
        try:
            self.colorbar = Colorbar(self)
            self.colorbar.show(*args, **kwargs)
        except:
            del self.colorbar
            raise

    @auto_refresh
    def remove_colorbar(self):
        '''
        Removes the colorbar from the current figure.
        '''
        self.colorbar._remove()
        del self.colorbar

    def close(self):
        '''
        Close the figure and free up the memory.
        '''
        mpl.close(self._figure)

########NEW FILE########
__FILENAME__ = axis_labels
from __future__ import absolute_import, print_function, division

from matplotlib.font_manager import FontProperties

from . import wcs_util
from .decorators import auto_refresh, fixdocstring


class AxisLabels(object):

    def __init__(self, parent):

        # Store references to axes
        self._ax1 = parent._ax1
        self._ax2 = parent._ax2
        self._wcs = parent._wcs
        self._figure = parent._figure

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

        # Set font
        self._label_fontproperties = FontProperties()

        self._ax2.yaxis.set_label_position('right')
        self._ax2.xaxis.set_label_position('top')

        system, equinox, units = wcs_util.system(self._wcs)

        if system['name'] == 'equatorial':

            if equinox == 'b1950':
                xtext = 'RA (B1950)'
                ytext = 'Dec (B1950)'
            else:
                xtext = 'RA (J2000)'
                ytext = 'Dec (J2000)'

        elif system['name'] == 'galactic':

            xtext = 'Galactic Longitude'
            ytext = 'Galactic Latitude'

        elif system['name'] == 'ecliptic':

            xtext = 'Ecliptic Longitude'
            ytext = 'Ecliptic Latitude'

        elif system['name'] == 'unknown':

            xunit = " (%s)" % self._wcs.cunit_x if self._wcs.cunit_x not in ["", None] else ""
            yunit = " (%s)" % self._wcs.cunit_y if self._wcs.cunit_y not in ["", None] else ""

            if len(self._wcs.cname_x) > 0:
                xtext = self._wcs.cname_x + xunit
            else:
                if len(self._wcs.ctype_x) == 8 and self._wcs.ctype_x[4] == '-':
                    xtext = self._wcs.ctype_x[:4].replace('-', '') + xunit
                else:
                    xtext = self._wcs.ctype_x + xunit

            if len(self._wcs.cname_y) > 0:
                ytext = self._wcs.cname_y + yunit
            else:
                if len(self._wcs.ctype_y) == 8 and self._wcs.ctype_y[4] == '-':
                    ytext = self._wcs.ctype_y[:4].replace('-', '') + yunit
                else:
                    ytext = self._wcs.ctype_y + yunit

        if system['inverted']:
            xtext, ytext = ytext, xtext

        self.set_xtext(xtext)
        self.set_ytext(ytext)

        self.set_xposition('bottom')
        self.set_yposition('left')

    @auto_refresh
    def set_xtext(self, label):
        """
        Set the x-axis label text.
        """
        self._xlabel1 = self._ax1.set_xlabel(label)
        self._xlabel2 = self._ax2.set_xlabel(label)

    @auto_refresh
    def set_ytext(self, label):
        """
        Set the y-axis label text.
        """
        self._ylabel1 = self._ax1.set_ylabel(label)
        self._ylabel2 = self._ax2.set_ylabel(label)

    @auto_refresh
    def set_xpad(self, pad):
        """
        Set the x-axis label displacement, in points.
        """
        self._xlabel1 = self._ax1.set_xlabel(self._xlabel1.get_text(), labelpad=pad)
        self._xlabel2 = self._ax2.set_xlabel(self._xlabel2.get_text(), labelpad=pad)

    @auto_refresh
    def set_ypad(self, pad):
        """
        Set the y-axis label displacement, in points.
        """
        self._ylabel1 = self._ax1.set_ylabel(self._ylabel1.get_text(), labelpad=pad)
        self._ylabel2 = self._ax2.set_ylabel(self._ylabel2.get_text(), labelpad=pad)

    @auto_refresh
    @fixdocstring
    def set_font(self, family=None, style=None, variant=None, stretch=None, weight=None, size=None, fontproperties=None):
        """
        Set the font of the axis labels.

        Parameters
        ----------

        common: family, style, variant, stretch, weight, size, fontproperties

        Notes
        -----

        Default values are set by matplotlib or previously set values if
        set_font has already been called. Global default values can be set by
        editing the matplotlibrc file.
        """

        if family:
            self._label_fontproperties.set_family(family)

        if style:
            self._label_fontproperties.set_style(style)

        if variant:
            self._label_fontproperties.set_variant(variant)

        if stretch:
            self._label_fontproperties.set_stretch(stretch)

        if weight:
            self._label_fontproperties.set_weight(weight)

        if size:
            self._label_fontproperties.set_size(size)

        if fontproperties:
            self._label_fontproperties = fontproperties

        self._xlabel1.set_fontproperties(self._label_fontproperties)
        self._xlabel2.set_fontproperties(self._label_fontproperties)
        self._ylabel1.set_fontproperties(self._label_fontproperties)
        self._ylabel2.set_fontproperties(self._label_fontproperties)

    @auto_refresh
    def show(self):
        """
        Show the x- and y-axis labels.
        """
        self.show_x()
        self.show_y()

    @auto_refresh
    def hide(self):
        """
        Hide the x- and y-axis labels.
        """
        self.hide_x()
        self.hide_y()

    @auto_refresh
    def show_x(self):
        """
        Show the x-axis label.
        """
        if self._xposition == 'bottom':
            self._xlabel1.set_visible(True)
        else:
            self._xlabel2.set_visible(True)

    @auto_refresh
    def hide_x(self):
        """
        Hide the x-axis label.
        """
        if self._xposition == 'bottom':
            self._xlabel1.set_visible(False)
        else:
            self._xlabel2.set_visible(False)

    @auto_refresh
    def show_y(self):
        """
        Show the y-axis label.
        """
        if self._yposition == 'left':
            self._ylabel1.set_visible(True)
        else:
            self._ylabel2.set_visible(True)

    @auto_refresh
    def hide_y(self):
        """
        Hide the y-axis label.
        """
        if self._yposition == 'left':
            self._ylabel1.set_visible(False)
        else:
            self._ylabel2.set_visible(False)

    @auto_refresh
    def set_xposition(self, position):
        "Set the position of the x-axis label ('top' or 'bottom')"
        if position == 'bottom':
            self._xlabel1.set_visible(True)
            self._xlabel2.set_visible(False)
        elif position == 'top':
            self._xlabel1.set_visible(False)
            self._xlabel2.set_visible(True)
        else:
            raise ValueError("position should be one of 'top' or 'bottom'")
        self._xposition = position

    @auto_refresh
    def set_yposition(self, position):
        "Set the position of the y-axis label ('left' or 'right')"
        if position == 'left':
            self._ylabel1.set_visible(True)
            self._ylabel2.set_visible(False)
        elif position == 'right':
            self._ylabel1.set_visible(False)
            self._ylabel2.set_visible(True)
        else:
            raise ValueError("position should be one of 'left' or 'right'")
        self._yposition = position

########NEW FILE########
__FILENAME__ = colorbar
from __future__ import absolute_import, print_function, division

import warnings

import matplotlib.axes as maxes
from mpl_toolkits.axes_grid import make_axes_locatable
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import LogFormatterMathtext

from .decorators import auto_refresh, fixdocstring

# As of matplotlib 0.99.1.1, any time a colorbar property is updated, the axes
# need to be removed and re-created. This has been fixed in svn r8213 but we
# should wait until we up the required version of matplotlib before changing the
# code here


class Colorbar(object):

    def __init__(self, parent):
        self._figure = parent._figure
        self._colorbar_axes = None
        self._parent = parent

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

        self._base_settings = {}
        self._ticklabel_fontproperties = FontProperties()
        self._axislabel_fontproperties = FontProperties()

    @auto_refresh
    def show(self, location='right', width=0.2, pad=0.05, ticks=None, labels=True, log_format=False,
             box=None, box_orientation='vertical', axis_label_text=None, axis_label_rotation=None,
             axis_label_pad=5):
        '''
        Show a colorbar on the side of the image.

        Parameters
        ----------

        location : str, optional
            Where to place the colorbar. Should be one of 'left', 'right', 'top', 'bottom'.

        width : float, optional
            The width of the colorbar relative to the canvas size.

        pad : float, optional
            The spacing between the colorbar and the image relative to the canvas size.

        ticks : list, optional
            The position of the ticks on the colorbar.

        labels : bool, optional
            Whether to show numerical labels.

        log_format : bool, optional
            Whether to format ticks in exponential notation

        box : list, optional
            A custom box within which to place the colorbar. This should
            be in the form [xmin, ymin, dx, dy] and be in relative figure
            units. This overrides the location argument.

        box_orientation str, optional
            The orientation of the colorbar within the box. Can be
            'horizontal' or 'vertical'

        axis_label_text str, optional
            Optional text label of the colorbar.
        '''

        self._base_settings['location'] = location
        self._base_settings['width'] = width
        self._base_settings['pad'] = pad
        self._base_settings['ticks'] = ticks
        self._base_settings['labels'] = labels
        self._base_settings['log_format'] = log_format
        self._base_settings['box'] = box
        self._base_settings['box_orientation'] = box_orientation
        self._base_settings['axis_label_text'] = axis_label_text
        self._base_settings['axis_label_rotation'] = axis_label_rotation
        self._base_settings['axis_label_pad'] = axis_label_pad

        if self._parent.image:

            if self._colorbar_axes:
                self._parent._figure.delaxes(self._colorbar_axes)

            if box is None:

                divider = make_axes_locatable(self._parent._ax1)

                if location == 'right':
                    self._colorbar_axes = divider.new_horizontal(size=width, pad=pad, axes_class=maxes.Axes)
                    orientation = 'vertical'
                elif location == 'top':
                    self._colorbar_axes = divider.new_vertical(size=width, pad=pad, axes_class=maxes.Axes)
                    orientation = 'horizontal'
                elif location == 'left':
                    warnings.warn("Left colorbar not fully implemented")
                    self._colorbar_axes = divider.new_horizontal(size=width, pad=pad, pack_start=True, axes_class=maxes.Axes)
                    locator = divider.new_locator(nx=0, ny=0)
                    self._colorbar_axes.set_axes_locator(locator)
                    orientation = 'vertical'
                elif location == 'bottom':
                    warnings.warn("Bottom colorbar not fully implemented")
                    self._colorbar_axes = divider.new_vertical(size=width, pad=pad, pack_start=True, axes_class=maxes.Axes)
                    locator = divider.new_locator(nx=0, ny=0)
                    self._colorbar_axes.set_axes_locator(locator)
                    orientation = 'horizontal'
                else:
                    raise Exception("location should be one of: right/top")

                self._parent._figure.add_axes(self._colorbar_axes)

            else:

                self._colorbar_axes = self._parent._figure.add_axes(box)
                orientation = box_orientation

            if log_format:
                format=LogFormatterMathtext()
            else:
                format=None
                
            self._colorbar = self._parent._figure.colorbar(self._parent.image, cax=self._colorbar_axes,
                                                           orientation=orientation, format=format,
                                                           ticks=ticks)
            if axis_label_text:
                if axis_label_rotation:
                    self._colorbar.set_label(axis_label_text, rotation=axis_label_rotation)
                else:
                    self._colorbar.set_label(axis_label_text)

            if location == 'right':
                for tick in self._colorbar_axes.yaxis.get_major_ticks():
                    tick.tick1On = True
                    tick.tick2On = True
                    tick.label1On = False
                    tick.label2On = labels
                self._colorbar_axes.yaxis.set_label_position('right')
                self._colorbar_axes.yaxis.labelpad = axis_label_pad
            elif location == 'top':
                for tick in self._colorbar_axes.xaxis.get_major_ticks():
                    tick.tick1On = True
                    tick.tick2On = True
                    tick.label1On = False
                    tick.label2On = labels
                self._colorbar_axes.xaxis.set_label_position('top')
                self._colorbar_axes.xaxis.labelpad = axis_label_pad
            elif location == 'left':
                for tick in self._colorbar_axes.yaxis.get_major_ticks():
                    tick.tick1On = True
                    tick.tick2On = True
                    tick.label1On = labels
                    tick.label2On = False
                self._colorbar_axes.yaxis.set_label_position('left')
                self._colorbar_axes.yaxis.labelpad = axis_label_pad
            elif location == 'bottom':
                for tick in self._colorbar_axes.xaxis.get_major_ticks():
                    tick.tick1On = True
                    tick.tick2On = True
                    tick.label1On = labels
                    tick.label2On = False
                self._colorbar_axes.xaxis.set_label_position('bottom')
                self._colorbar_axes.xaxis.labelpad = axis_label_pad

        else:

            warnings.warn("No image is shown, therefore, no colorbar will be plotted")

    @auto_refresh
    def update(self):
        if self._colorbar_axes:
            self.show(**self._base_settings)

    @auto_refresh
    def hide(self):
        self._parent._figure.delaxes(self._colorbar_axes)
        self._colorbar_axes = None

    @auto_refresh
    def _remove(self):
        self._parent._figure.delaxes(self._colorbar_axes)

    # LOCATION AND SIZE

    @auto_refresh
    def set_location(self, location):
        '''
        Set the location of the colorbar.
        
        Should be one of 'left', 'right', 'top', 'bottom'.
        '''
        self._base_settings['location'] = location
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_width(self, width):
        '''
        Set the width of the colorbar relative to the canvas size.
        '''
        self._base_settings['width'] = width
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_pad(self, pad):
        '''
        Set the spacing between the colorbar and the image relative to the canvas size.
        '''
        self._base_settings['pad'] = pad
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_ticks(self, ticks):
        '''
        Set the position of the ticks on the colorbar.
        '''
        self._base_settings['ticks'] = ticks
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_labels(self, labels):
        '''
        Set whether to show numerical labels.
        '''
        self._base_settings['labels'] = labels
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_box(self, box, box_orientation='vertical'):
        '''
        Set the box within which to place the colorbar.
        
        This should be in the form [xmin, ymin, dx, dy] and be in relative
        figure units. The orientation of the colorbar within the box can be
        controlled with the box_orientation argument.
        '''
        self._base_settings['box'] = box
        self._base_settings['box_orientation'] = box_orientation
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_axis_label_text(self, axis_label_text):
        '''
        Set the colorbar label text.
        '''
        self._base_settings['axis_label_text'] = axis_label_text
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_axis_label_rotation(self, axis_label_rotation):
        '''
        Set the colorbar label rotation.
        '''
        self._base_settings['axis_label_rotation'] = axis_label_rotation
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    @auto_refresh
    def set_axis_label_pad(self, axis_label_pad):
        '''
        Set the colorbar label displacement, in points.
        '''
        self._base_settings['axis_label_pad'] = axis_label_pad
        self.show(**self._base_settings)
        self.set_font(fontproperties=self._ticklabel_fontproperties)
        self.set_axis_label_font(fontproperties=self._axislabel_fontproperties)

    # FONT PROPERTIES

    @auto_refresh
    def set_label_properties(self, *args, **kwargs):
        warnings.warn("set_label_properties is deprecated - use set_font instead", DeprecationWarning)
        self.set_font(*args, **kwargs)

    @auto_refresh
    @fixdocstring
    def set_font(self, family=None, style=None, variant=None, stretch=None, weight=None, size=None, fontproperties=None):
        '''
        Set the font of the tick labels.

        Parameters
        ----------

        common: family, style, variant, stretch, weight, size, fontproperties

        Notes
        -----

        Default values are set by matplotlib or previously set values if
        set_font has already been called. Global default values can be set by
        editing the matplotlibrc file.
        '''

        if family:
            self._ticklabel_fontproperties.set_family(family)

        if style:
            self._ticklabel_fontproperties.set_style(style)

        if variant:
            self._ticklabel_fontproperties.set_variant(variant)

        if stretch:
            self._ticklabel_fontproperties.set_stretch(stretch)

        if weight:
            self._ticklabel_fontproperties.set_weight(weight)

        if size:
            self._ticklabel_fontproperties.set_size(size)

        if fontproperties:
            self._ticklabel_fontproperties = fontproperties

        # Update the tick label font properties
        for label in self._colorbar_axes.get_xticklabels():
            label.set_fontproperties(self._ticklabel_fontproperties)
        for label in self._colorbar_axes.get_yticklabels():
            label.set_fontproperties(self._ticklabel_fontproperties)

        # Also update the offset text font properties
        label = self._colorbar_axes.xaxis.get_offset_text()
        label.set_fontproperties(self._ticklabel_fontproperties)
        label = self._colorbar_axes.yaxis.get_offset_text()
        label.set_fontproperties(self._ticklabel_fontproperties)

    @auto_refresh
    @fixdocstring
    def set_axis_label_font(self, family=None, style=None, variant=None, stretch=None, weight=None, size=None, fontproperties=None):
        '''
        Set the font of the tick labels.

        Parameters
        ----------

        common: family, style, variant, stretch, weight, size, fontproperties

        Notes
        -----

        Default values are set by matplotlib or previously set values if
        set_font has already been called. Global default values can be set by
        editing the matplotlibrc file.
        '''

        if family:
            self._axislabel_fontproperties.set_family(family)

        if style:
            self._axislabel_fontproperties.set_style(style)

        if variant:
            self._axislabel_fontproperties.set_variant(variant)

        if stretch:
            self._axislabel_fontproperties.set_stretch(stretch)

        if weight:
            self._axislabel_fontproperties.set_weight(weight)

        if size:
            self._axislabel_fontproperties.set_size(size)

        if fontproperties:
            self._axislabel_fontproperties = fontproperties

        # Update the label font properties
        label = self._colorbar_axes.xaxis.get_label()
        label.set_fontproperties(self._axislabel_fontproperties)
        label = self._colorbar_axes.yaxis.get_label()
        label.set_fontproperties(self._axislabel_fontproperties)

    # FRAME PROPERTIES

    @auto_refresh
    def set_frame_linewidth(self, linewidth):
        '''
        Set the linewidth of the colorbar frame, in points.
        '''
        warnings.warn("This method is not functional at this time")
        for key in self._colorbar_axes.spines:
            self._colorbar_axes.spines[key].set_linewidth(linewidth)

    @auto_refresh
    def set_frame_color(self, color):
        '''
        Set the color of the colorbar frame, in points.
        '''
        warnings.warn("This method is not functional at this time")
        for key in self._colorbar_axes.spines:
            self._colorbar_axes.spines[key].set_edgecolor(color)

########NEW FILE########
__FILENAME__ = conftest
# this contains imports plugins that configure py.test for astropy tests.
# by importing them here in conftest.py they are discoverable by py.test
# no matter how it is invoked within the source tree.

from astropy.tests.pytest_plugins import *

########NEW FILE########
__FILENAME__ = contour_util
from __future__ import absolute_import, print_function, division

import numpy as np
from matplotlib.path import Path

from . import wcs_util


def transform(contours, wcs_in, wcs_out, filled=False, overlap=False):

    system_in, equinox_in, units_in = wcs_util.system(wcs_in)
    system_out, equinox_out, units_out = wcs_util.system(wcs_out)

    for contour in contours.collections:

        polygons_out = []
        for polygon in contour.get_paths():

            xp_in = polygon.vertices[:, 0]
            yp_in = polygon.vertices[:, 1]

            xw, yw = wcs_util.pix2world(wcs_in, xp_in, yp_in)

            xw, yw = wcs_util.convert_coords(xw, yw,
                input=(system_in, equinox_in),
                output=(system_out, equinox_out))

            xp_out, yp_out = wcs_util.world2pix(wcs_out, xw, yw)

            if overlap:
                if np.all(xp_out < 0) or np.all(yp_out < 0) or \
                   np.all(xp_out > wcs_out.nx) or np.all(yp_out > wcs_out.ny):
                    continue

            if filled:
                polygons_out.append(Path(np.array(zip(xp_out, yp_out)), codes=polygon.codes))
            else:
                polygons_out.append(zip(xp_out, yp_out))

        if filled:
            contour.set_paths(polygons_out)
        else:
            contour.set_verts(polygons_out)

        contour.apl_converted = True

########NEW FILE########
__FILENAME__ = convolve_util
from __future__ import absolute_import, print_function, division

import numpy as np
try:
    from astropy.convolution import convolve as astropy_convolve, Gaussian2DKernel, Box2DKernel
    make_kernel = None
except ImportError:
    from astropy.nddata import convolve as astropy_convolve, make_kernel


def convolve(image, smooth=3, kernel='gauss'):

    if smooth is None and kernel in ['box', 'gauss']:
        return image

    if smooth is not None and not np.isscalar(smooth):
        raise ValueError("smooth= should be an integer - for more complex "
                         "kernels, pass an array containing the kernel "
                         "to the kernel= option")

    # The Astropy convolution doesn't treat +/-Inf values correctly yet, so we
    # convert to NaN here.

    image_fixed = image.copy()
    image_fixed[np.isinf(image)] = np.nan

    if kernel == 'gauss':
        if make_kernel is None:
            kernel = Gaussian2DKernel(smooth, x_size=smooth * 5, y_size=smooth * 5)
        else:
            kernel = make_kernel((smooth * 5, smooth * 5), smooth, 'gaussian')
    elif kernel == 'box':
        if make_kernel is None:
            kernel = Box2DKernel(smooth, x_size=smooth * 5, y_size=smooth * 5)
        else:
            kernel = make_kernel((smooth * 5, smooth * 5), smooth, 'boxcar')
    else:
        kernel = kernel

    return astropy_convolve(image, kernel, boundary='extend')

########NEW FILE########
__FILENAME__ = decorator
from __future__ import print_function

##########################     LICENCE     ###############################

# Copyright (c) 2005-2012, Michele Simionato
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#   Redistributions of source code must retain the above copyright 
#   notice, this list of conditions and the following disclaimer.
#   Redistributions in bytecode form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution. 

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

"""
Decorator module, see http://pypi.python.org/pypi/decorator
for the documentation.
"""

__version__ = '3.4.0'

__all__ = ["decorator", "FunctionMaker", "contextmanager"]

import sys, re, inspect
if sys.version >= '3':
    from inspect import getfullargspec
    def get_init(cls):
        return cls.__init__
else:
    class getfullargspec(object):
        "A quick and dirty replacement for getfullargspec for Python 2.X"
        def __init__(self, f):
            self.args, self.varargs, self.varkw, self.defaults = \
                inspect.getargspec(f)
            self.kwonlyargs = []
            self.kwonlydefaults = None
        def __iter__(self):
            yield self.args
            yield self.varargs
            yield self.varkw
            yield self.defaults
    def get_init(cls):
        return cls.__init__.__func__

DEF = re.compile('\s*def\s*([_\w][_\w\d]*)\s*\(')

# basic functionality
class FunctionMaker(object):
    """
    An object with the ability to create functions with a given signature.
    It has attributes name, doc, module, signature, defaults, dict and
    methods update and make.
    """
    def __init__(self, func=None, name=None, signature=None,
                 defaults=None, doc=None, module=None, funcdict=None):
        self.shortsignature = signature
        if func:
            # func can be a class or a callable, but not an instance method
            self.name = func.__name__
            if self.name == '<lambda>': # small hack for lambda functions
                self.name = '_lambda_' 
            self.doc = func.__doc__
            self.module = func.__module__
            if inspect.isfunction(func):
                argspec = getfullargspec(func)
                self.annotations = getattr(func, '__annotations__', {})
                for a in ('args', 'varargs', 'varkw', 'defaults', 'kwonlyargs',
                          'kwonlydefaults'):
                    setattr(self, a, getattr(argspec, a))
                for i, arg in enumerate(self.args):
                    setattr(self, 'arg%d' % i, arg)
                if sys.version < '3': # easy way
                    self.shortsignature = self.signature = \
                        inspect.formatargspec(
                        formatvalue=lambda val: "", *argspec)[1:-1]
                else: # Python 3 way
                    allargs = list(self.args)
                    allshortargs = list(self.args)
                    if self.varargs:
                        allargs.append('*' + self.varargs)
                        allshortargs.append('*' + self.varargs)
                    elif self.kwonlyargs:
                        allargs.append('*') # single star syntax
                    for a in self.kwonlyargs:
                        allargs.append('%s=None' % a)
                        allshortargs.append('%s=%s' % (a, a))
                    if self.varkw:
                        allargs.append('**' + self.varkw)
                        allshortargs.append('**' + self.varkw)
                    self.signature = ', '.join(allargs)
                    self.shortsignature = ', '.join(allshortargs)
                self.dict = func.__dict__.copy()
        # func=None happens when decorating a caller
        if name:
            self.name = name
        if signature is not None:
            self.signature = signature
        if defaults:
            self.defaults = defaults
        if doc:
            self.doc = doc
        if module:
            self.module = module
        if funcdict:
            self.dict = funcdict
        # check existence required attributes
        assert hasattr(self, 'name')
        if not hasattr(self, 'signature'):
            raise TypeError('You are decorating a non function: %s' % func)

    def update(self, func, **kw):
        "Update the signature of func with the data in self"
        func.__name__ = self.name
        func.__doc__ = getattr(self, 'doc', None)
        func.__dict__ = getattr(self, 'dict', {})
        func.__defaults__ = getattr(self, 'defaults', ())
        func.__kwdefaults__ = getattr(self, 'kwonlydefaults', None)
        func.__annotations__ = getattr(self, 'annotations', None)
        callermodule = sys._getframe(3).f_globals.get('__name__', '?')
        func.__module__ = getattr(self, 'module', callermodule)
        func.__dict__.update(kw)

    def make(self, src_templ, evaldict=None, addsource=False, **attrs):
        "Make a new function from a given template and update the signature"
        src = src_templ % vars(self) # expand name and signature
        evaldict = evaldict or {}
        mo = DEF.match(src)
        if mo is None:
            raise SyntaxError('not a valid function template\n%s' % src)
        name = mo.group(1) # extract the function name
        names = set([name] + [arg.strip(' *') for arg in 
                             self.shortsignature.split(',')])
        for n in names:
            if n in ('_func_', '_call_'):
                raise NameError('%s is overridden in\n%s' % (n, src))
        if not src.endswith('\n'): # add a newline just for safety
            src += '\n' # this is needed in old versions of Python
        try:
            code = compile(src, '<string>', 'single')
            # print >> sys.stderr, 'Compiling %s' % src
            exec(code, evaldict)
        except:
            print('Error in generated code:', file=sys.stderr)
            print(src, file=sys.stderr)
            raise
        func = evaldict[name]
        if addsource:
            attrs['__source__'] = src
        self.update(func, **attrs)
        return func

    @classmethod
    def create(cls, obj, body, evaldict, defaults=None,
               doc=None, module=None, addsource=True, **attrs):
        """
        Create a function from the strings name, signature and body.
        evaldict is the evaluation dictionary. If addsource is true an attribute
        __source__ is added to the result. The attributes attrs are added,
        if any.
        """
        if isinstance(obj, str): # "name(signature)"
            name, rest = obj.strip().split('(', 1)
            signature = rest[:-1] #strip a right parens            
            func = None
        else: # a function
            name = None
            signature = None
            func = obj
        self = cls(func, name, signature, defaults, doc, module)
        ibody = '\n'.join('    ' + line for line in body.splitlines())
        return self.make('def %(name)s(%(signature)s):\n' + ibody, 
                        evaldict, addsource, **attrs)
  
def decorator(caller, func=None):
    """
    decorator(caller) converts a caller function into a decorator;
    decorator(caller, func) decorates a function using a caller.
    """
    if func is not None: # returns a decorated function
        evaldict = func.__globals__.copy()
        evaldict['_call_'] = caller
        evaldict['_func_'] = func
        return FunctionMaker.create(
            func, "return _call_(_func_, %(shortsignature)s)",
            evaldict, undecorated=func, __wrapped__=func)
    else: # returns a decorator
        if inspect.isclass(caller):
            name = caller.__name__.lower()
            callerfunc = get_init(caller)
            doc = 'decorator(%s) converts functions/generators into ' \
                'factories of %s objects' % (caller.__name__, caller.__name__)
            fun = getfullargspec(callerfunc).args[1] # second arg
        elif inspect.isfunction(caller):
            name = '_lambda_' if caller.__name__ == '<lambda>' \
                else caller.__name__
            callerfunc = caller
            doc = caller.__doc__
            fun = getfullargspec(callerfunc).args[0] # first arg
        else: # assume caller is an object with a __call__ method
            name = caller.__class__.__name__.lower()
            callerfunc = caller.__call__.__func__
            doc = caller.__call__.__doc__
            fun = getfullargspec(callerfunc).args[1] # second arg
        evaldict = callerfunc.__globals__.copy()
        evaldict['_call_'] = caller
        evaldict['decorator'] = decorator
        return FunctionMaker.create(
            '%s(%s)' % (name, fun), 
            'return decorator(_call_, %s)' % fun,
            evaldict, undecorated=caller, __wrapped__=caller,
            doc=doc, module=caller.__module__)

######################### contextmanager ########################

def __call__(self, func):
    'Context manager decorator'
    return FunctionMaker.create(
        func, "with _self_: return _func_(%(shortsignature)s)",
        dict(_self_=self, _func_=func), __wrapped__=func)

try: # Python >= 3.2

    from contextlib import _GeneratorContextManager 
    ContextManager = type(
        'ContextManager', (_GeneratorContextManager,), dict(__call__=__call__))

except ImportError: # Python >= 2.5

    from contextlib import GeneratorContextManager
    def __init__(self, f, *a, **k):
        return GeneratorContextManager.__init__(self, f(*a, **k))
    ContextManager = type(
        'ContextManager', (GeneratorContextManager,), 
        dict(__call__=__call__, __init__=__init__))
    
contextmanager = decorator(ContextManager)

########NEW FILE########
__FILENAME__ = decorators
from __future__ import absolute_import, print_function, division

import threading

from .decorator import decorator


mydata = threading.local()


def auto_refresh(f):
    return decorator(_auto_refresh, f)


def _auto_refresh(f, *args, **kwargs):
    if 'refresh' in kwargs:
        refresh = kwargs.pop('refresh')
    else:
        refresh = True
    # The following is necessary rather than using mydata.nesting = 0 at the
    # start of the file, because doing the latter caused issues with the Django
    # development server.
    mydata.nesting = getattr(mydata, 'nesting', 0) + 1
    try:
        return f(*args, **kwargs)
    finally:
        mydata.nesting -= 1
        if hasattr(args[0], '_figure'):
            if refresh and mydata.nesting == 0 and args[0]._parameters.auto_refresh:
                args[0]._figure.canvas.draw()


doc = {}

doc['size'] = '''size : str or int or float, optional
    The size of the font. This can either be a numeric value (e.g.
    12), giving the size in points, or one of 'xx-small', 'x-small',
    'small', 'medium', 'large', 'x-large', or 'xx-large'.
    '''

doc['weight'] = '''weight : str or int or float, optional
    The weight (or boldness) of the font. This can either be a numeric
    value in the range 0-1000 or one of 'ultralight', 'light', 'normal',
    'regular', 'book', 'medium', 'roman', 'semibold', 'demibold', 'demi',
    'bold', 'heavy', 'extra bold', 'black'.
    '''

doc['stretch'] = '''stretch : str or int or float, optional
    The stretching (spacing between letters) for the font. This can either
    be a numeric value in the range 0-1000 or one of 'ultra-condensed',
    'extra-condensed', 'condensed', 'semi-condensed', 'normal',
    'semi-expanded', 'expanded', 'extra-expanded' or 'ultra-expanded'.
    '''

doc['family'] = '''family : str, optional
    The family of the font to use. This can either be a generic font
    family name, either 'serif', 'sans-serif', 'cursive', 'fantasy', or
    'monospace', or a list of font names in decreasing order of priority.
    '''

doc['style'] = '''style : str, optional
    The font style. This can be 'normal', 'italic' or 'oblique'.
    '''

doc['variant'] = '''variant : str, optional
    The font variant. This can be 'normal' or 'small-caps'
    '''


def fixdocstring(func):

    lines = func.__doc__.split('\n')

    for i, line in enumerate(lines):
        if 'common:' in line:
            break

    header = lines[:i]

    footer = lines[i + 1:]

    indent = lines[i].index('common:')

    common = []
    for item in lines[i].split(':')[1].split(','):
        if item.strip() in doc:
            common.append(" " * indent + doc[item.strip()].replace('\n', '\n' + " " * indent))

    docstring = "\n".join(header + common + footer)

    func.__doc__ = docstring

    return func

########NEW FILE########
__FILENAME__ = deprecated
from __future__ import absolute_import, print_function, division

import warnings

from .decorators import auto_refresh


class Deprecated(object):

    @auto_refresh
    def set_tick_xspacing(self, *args, **kwargs):
        warnings.warn("set_tick_xspacing is deprecated - use ticks.set_xspacing instead", DeprecationWarning)
        self.ticks.set_xspacing(*args, **kwargs)

    @auto_refresh
    def set_tick_yspacing(self, *args, **kwargs):
        warnings.warn("set_tick_yspacing is deprecated - use ticks.set_yspacing instead", DeprecationWarning)
        self.ticks.set_yspacing(*args, **kwargs)

    @auto_refresh
    def set_tick_size(self, *args, **kwargs):
        warnings.warn("set_tick_size is deprecated - use ticks.set_length instead", DeprecationWarning)
        self.ticks.set_length(*args, **kwargs)

    @auto_refresh
    def set_tick_color(self, *args, **kwargs):
        warnings.warn("set_tick_color is deprecated - use ticks.set_color instead", DeprecationWarning)
        self.ticks.set_color(*args, **kwargs)

    @auto_refresh
    def show_grid(self, *args, **kwargs):
        warnings.warn("show_grid is deprecated - use add_grid instead", DeprecationWarning)
        self.add_grid(*args, **kwargs)

    @auto_refresh
    def hide_grid(self, *args, **kwargs):
        warnings.warn("hide_grid is deprecated - use remove_grid instead", DeprecationWarning)
        self.remove_grid(*args, **kwargs)

    @auto_refresh
    def show_beam(self, *args, **kwargs):
        warnings.warn("show_beam is deprecated - use add_beam instead", DeprecationWarning)
        self.add_beam(*args, **kwargs)

    @auto_refresh
    def hide_beam(self, *args, **kwargs):
        warnings.warn("hide_beam is deprecated - use remove_beam instead", DeprecationWarning)
        self.add_beam(*args, **kwargs)

    @auto_refresh
    def show_scalebar(self, *args, **kwargs):
        warnings.warn("show_scalebar is deprecated - use add_scalebar instead", DeprecationWarning)
        self.add_scalebar(*args, **kwargs)

    @auto_refresh
    def hide_scalebar(self, *args, **kwargs):
        warnings.warn("hide_scalebar is deprecated - use remove_scalebar instead", DeprecationWarning)
        self.add_scalebar(*args, **kwargs)

    @auto_refresh
    def show_colorbar(self, *args, **kwargs):
        warnings.warn("show_colorbar is deprecated - use add_colorbar instead", DeprecationWarning)
        self.add_colorbar(*args, **kwargs)

    @auto_refresh
    def hide_colorbar(self, *args, **kwargs):
        warnings.warn("hide_colorbar is deprecated - use remove_colorbar instead", DeprecationWarning)
        self.add_colorbar(*args, **kwargs)

    @auto_refresh
    def set_grid_alpha(self, *args, **kwargs):
        warnings.warn("set_grid_alpha is deprecated - use grid.set_alpha instead", DeprecationWarning)
        self.grid.set_alpha(*args, **kwargs)

    @auto_refresh
    def set_grid_color(self, *args, **kwargs):
        warnings.warn("set_grid_color is deprecated - use grid.set_color instead", DeprecationWarning)
        self.grid.set_color(*args, **kwargs)

    @auto_refresh
    def set_grid_xspacing(self, *args, **kwargs):
        warnings.warn("set_grid_xspacing is deprecated - use grid.set_xspacing instead", DeprecationWarning)
        self.grid.set_xspacing(*args, **kwargs)

    @auto_refresh
    def set_grid_yspacing(self, *args, **kwargs):
        warnings.warn("set_grid_yspacing is deprecated - use grid.set_yspacing instead", DeprecationWarning)
        self.grid.set_yspacing(*args, **kwargs)

    @auto_refresh
    def set_scalebar_properties(self, *args, **kwargs):
        warnings.warn("set_scalebar_properties is deprecated - use scalebar.set instead", DeprecationWarning)
        self.scalebar._set_scalebar_properties(*args, **kwargs)

    @auto_refresh
    def set_label_properties(self, *args, **kwargs):
        warnings.warn("set_label_properties is deprecated - use scalebar.set instead", DeprecationWarning)
        self.scalebar._set_label_properties(*args, **kwargs)

    @auto_refresh
    def set_beam_properties(self, *args, **kwargs):
        warnings.warn("set_beam_properties is deprecated - use beam.set instead", DeprecationWarning)
        self.beam.set(*args, **kwargs)

    @auto_refresh
    def set_labels_latex(self, usetex):
        warnings.warn("set_labels_latex has been deprecated - use set_system_latex instead", DeprecationWarning)
        self.set_system_latex(usetex)

    # TICK LABELS

    @auto_refresh
    def set_tick_labels_format(self, xformat=None, yformat=None):
        warnings.warn("set_tick_labels_format has been deprecated - use tick_labels.set_xformat() and tick_labels.set_yformat instead", DeprecationWarning)
        if xformat:
            self.tick_labels.set_xformat(xformat)
        if yformat:
            self.tick_labels.set_yformat(yformat)

    @auto_refresh
    def set_tick_labels_xformat(self, format):
        warnings.warn("set_tick_labels_xformat has been deprecated - use tick_labels.set_xformat() instead", DeprecationWarning)
        self.tick_labels.set_xformat(format)

    @auto_refresh
    def set_tick_labels_yformat(self, format):
        warnings.warn("set_tick_labels_yformat has been deprecated - use tick_labels.set_yformat() instead", DeprecationWarning)
        self.tick_labels.set_yformat(format)

    @auto_refresh
    def set_tick_labels_style(self, style):
        warnings.warn("set_tick_labels_style has been deprecated - use tick_labels.set_style instead", DeprecationWarning)
        self.tick_labels.set_style(style)

    @auto_refresh
    def set_tick_labels_size(self, size):
        warnings.warn("set_tick_labels_size has been deprecated - use tick_labels.set_font instead", DeprecationWarning)
        self.tick_labels.set_font(size=size)

    @auto_refresh
    def set_tick_labels_weight(self, weight):
        warnings.warn("set_tick_labels_weight has been deprecated - use tick_labels.set_font instead", DeprecationWarning)
        self.tick_labels.set_font(weight=weight)

    @auto_refresh
    def set_tick_labels_family(self, family):
        warnings.warn("set_tick_labels_family has been deprecated - use tick_labels.set_font instead", DeprecationWarning)
        self.tick_labels.set_font(family=family)

    @auto_refresh
    def set_tick_labels_font(self, *args, **kwargs):
        warnings.warn("set_tick_labels_font has been deprecated - use tick_labels.set_font instead", DeprecationWarning)
        self.tick_labels.set_font(*args, **kwargs)

    @auto_refresh
    def show_tick_labels(self):
        warnings.warn("show_tick_labels has been deprecated - use tick_labels.show instead", DeprecationWarning)
        self.tick_labels.show()

    @auto_refresh
    def hide_tick_labels(self):
        warnings.warn("hide_tick_labels has been deprecated - use tick_labels.hide instead", DeprecationWarning)
        self.tick_labels.hide()

    @auto_refresh
    def show_xtick_labels(self):
        warnings.warn("show_xtick_labels has been deprecated - use tick_labels.show_x instead", DeprecationWarning)
        self.tick_labels.show_x()

    @auto_refresh
    def hide_xtick_labels(self):
        warnings.warn("hide_xtick_labels has been deprecated - use tick_labels.hide_x instead", DeprecationWarning)
        self.tick_labels.hide_x()

    @auto_refresh
    def show_ytick_labels(self):
        warnings.warn("show_ytick_labels has been deprecated - use tick_labels.show_y instead", DeprecationWarning)
        self.tick_labels.show_y()

    @auto_refresh
    def hide_ytick_labels(self):
        warnings.warn("hide_ytick_labels has been deprecated - use tick_labels.hide_y instead", DeprecationWarning)
        self.tick_labels.hide_y()

    # AXIS LABELS

    @auto_refresh
    def set_axis_labels(self, xlabel='default', ylabel='default', xpad='default', ypad='default'):
        warnings.warn("set_axis_labels has been deprecated - use axis_labels.set_xtext, axis_labels.set_ytext, axis_labels.set_xpad, and axis_labels.set_ypad instead", DeprecationWarning)
        if xlabel != 'default':
            self.axis_labels.set_xtext(xlabel)
        if xpad != 'default':
            self.axis_labels.set_xpad(xpad)
        if ylabel != 'default':
            self.axis_labels.set_ytext(ylabel)
        if ypad != 'default':
            self.axis_labels.set_ypad(ypad)

    @auto_refresh
    def set_axis_labels_xdisp(self, xpad):
        warnings.warn("set_axis_labels_xdisk has been deprecated - use axis_labels.set_xpad instead", DeprecationWarning)
        self.axis_labels.set_xpad(xpad)

    @auto_refresh
    def set_axis_labels_ydisp(self, ypad):
        warnings.warn("set_axis_labels_xdisp has been deprecated - use axis_labels.set_ypad instead", DeprecationWarning)
        self.axis_labels.set_ypad(ypad)

    @auto_refresh
    def set_axis_labels_size(self, size):
        warnings.warn("set_axis_labels_size has been deprecated - use axis_labels.set_font instead", DeprecationWarning)
        self.axis_labels.set_font(size=size)

    @auto_refresh
    def set_axis_labels_weight(self, weight):
        warnings.warn("set_axis_labels_weight has been deprecated - use axis_labels.set_font instead", DeprecationWarning)
        self.axis_labels.set_font(weight=weight)

    @auto_refresh
    def set_axis_labels_family(self, family):
        warnings.warn("set_axis_labels_family has been deprecated - use axis_labels.set_font instead", DeprecationWarning)
        self.axis_labels.set_font(family=family)

    @auto_refresh
    def set_axis_labels_font(self, *args, **kwargs):
        warnings.warn("set_axis_labels_font has been deprecated - use axis_labels.set_font instead", DeprecationWarning)
        self.axis_labels.set_font(*args, **kwargs)

    @auto_refresh
    def show_axis_labels(self):
        warnings.warn("show_axis_labels has been deprecated - use axis_labels.show instead", DeprecationWarning)
        self.axis_labels.show()

    @auto_refresh
    def hide_axis_labels(self):
        warnings.warn("hide_axis_labels has been deprecated - use axis_labels.hide instead", DeprecationWarning)
        self.axis_labels.hide()

    @auto_refresh
    def show_xaxis_label(self):
        warnings.warn("show_xaxis_label has been deprecated - use axis_labels.show_x instead", DeprecationWarning)
        self.axis_labels.show_x()

    @auto_refresh
    def hide_xaxis_label(self):
        warnings.warn("hide_xaxis_label has been deprecated - use axis_labels.hide_x instead", DeprecationWarning)
        self.axis_labels.hide_x()

    @auto_refresh
    def show_yaxis_label(self):
        warnings.warn("show_yaxis_label has been deprecated - use axis_labels.show_y instead", DeprecationWarning)
        self.axis_labels.show_y()

    @auto_refresh
    def hide_yaxis_label(self):
        warnings.warn("hide_yaxis_label has been deprecated - use axis_labels.hide_y instead", DeprecationWarning)
        self.axis_labels.hide_y()

    # FRAME

    @auto_refresh
    def set_frame_color(self, *args, **kwargs):
        warnings.warn("set_frame_color has been deprecated - use frame.set_color instead", DeprecationWarning)
        self.frame.set_color(*args, **kwargs)

    @auto_refresh
    def set_frame_linewidth(self, *args, **kwargs):
        warnings.warn("set_frame_linewidth has been deprecated - use frame.set_linewidth instead", DeprecationWarning)
        self.frame.set_linewidth(*args, **kwargs)

########NEW FILE########
__FILENAME__ = frame
from __future__ import absolute_import, print_function, division

from .decorators import auto_refresh


class Frame(object):

    @auto_refresh
    def __init__(self, parent):

        self._ax1 = parent._ax1
        self._ax2 = parent._ax2
        self._figure = parent._figure

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

    @auto_refresh
    def set_linewidth(self, linewidth):
        '''
        Set line width of the frame.

        Parameters
        ----------
        linewidth:
            The linewidth to use for the frame.
        '''
        for key in self._ax1.spines:
            self._ax1.spines[key].set_linewidth(linewidth)
        for key in self._ax2.spines:
            self._ax2.spines[key].set_linewidth(linewidth)

    @auto_refresh
    def set_color(self, color):
        '''
        Set color of the frame.

        Parameters
        ----------
        color:
            The color to use for the frame.
        '''
        for key in self._ax1.spines:
            self._ax1.spines[key].set_edgecolor(color)
        for key in self._ax2.spines:
            self._ax2.spines[key].set_edgecolor(color)

########NEW FILE########
__FILENAME__ = grid
from __future__ import absolute_import, print_function, division

import warnings

import numpy as np
from matplotlib.collections import LineCollection

from . import math_util
from . import wcs_util
from . import angle_util as au
from .ticks import tick_positions, default_spacing
from .decorators import auto_refresh


class Grid(object):

    @auto_refresh
    def __init__(self, parent):

        # Save axes and wcs information
        self.ax = parent._ax1
        self._wcs = parent._wcs
        self._figure = parent._figure

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

        # Initialize grid container
        self._grid = None
        self._active = False

        # Set defaults
        self.x_auto_spacing = True
        self.y_auto_spacing = True
        self.default_color = 'white'
        self.default_alpha = 0.5

        # Set grid event handler
        self.ax.callbacks.connect('xlim_changed', self._update_norefresh)
        self.ax.callbacks.connect('ylim_changed', self._update_norefresh)

    @auto_refresh
    def _remove(self):
        self._grid.remove()

    @auto_refresh
    def set_xspacing(self, xspacing):
        '''
        Set the grid line spacing in the longitudinal direction

        Parameters
        ----------
        xspacing : { float, str }
            The spacing in the longitudinal direction. To set the spacing
            to be the same as the ticks, set this to 'tick'
        '''
        if xspacing == 'tick':
            self.x_auto_spacing = True
        elif np.isreal(xspacing):
            self.x_auto_spacing = False
            if self._wcs.xaxis_coord_type in ['longitude', 'latitude']:
                self.x_grid_spacing = au.Angle(
                    degrees=xspacing,
                    latitude=self._wcs.xaxis_coord_type == 'latitude')
            else:
                self.x_grid_spacing = xspacing
        else:
            raise ValueError("Grid spacing should be a scalar or 'tick'")

        self._update()

    @auto_refresh
    def set_yspacing(self, yspacing):
        '''
        Set the grid line spacing in the latitudinal direction

        Parameters
        ----------
        yspacing : { float, str }
            The spacing in the latitudinal direction. To set the spacing
            to be the same as the ticks, set this to 'tick'
        '''

        if yspacing == 'tick':
            self.y_auto_spacing = True
        elif np.isreal(yspacing):
            self.y_auto_spacing = False
            if self._wcs.yaxis_coord_type in ['longitude', 'latitude']:
                self.y_grid_spacing = au.Angle(
                    degrees=yspacing,
                    latitude=self._wcs.yaxis_coord_type == 'latitude')
            else:
                self.y_grid_spacing = yspacing
        else:
            raise ValueError("Grid spacing should be a scalar or 'tick'")

        self._update()

    @auto_refresh
    def set_color(self, color):
        '''
        Set the color of the grid lines

        Parameters
        ----------
        color : str
            The color of the grid lines
        '''
        if self._grid:
            self._grid.set_edgecolor(color)
        else:
            self.default_color = color

    @auto_refresh
    def set_alpha(self, alpha):
        '''
        Set the alpha (transparency) of the grid lines

        Parameters
        ----------
        alpha : float
            The alpha value of the grid. This should be a floating
            point value between 0 and 1, where 0 is completely
            transparent, and 1 is completely opaque.
        '''
        if self._grid:
            self._grid.set_alpha(alpha)
        else:
            self.default_alpha = alpha

    @auto_refresh
    def set_linewidth(self, linewidth):
        self._grid.set_linewidth(linewidth)

    @auto_refresh
    def set_linestyle(self, linestyle):
        self._grid.set_linestyle(linestyle)

    @auto_refresh
    def show(self):
        if self._grid:
            self._grid.set_visible(True)
        else:
            self._active = True
            self._update()
            self.set_color(self.default_color)
            self.set_alpha(self.default_alpha)

    @auto_refresh
    def hide(self):
        self._grid.set_visible(False)

    @auto_refresh
    def _update(self, *args):
        self._update_norefresh(*args)

    def _update_norefresh(self, *args):

        if not self._active:
            return self.ax

        if len(args) == 1:
            if id(self.ax) != id(args[0]):
                raise Exception("ax ids should match")

        lines = []

        # Set x grid spacing
        if self.x_auto_spacing:
            if self.ax.xaxis.apl_auto_tick_spacing:
                xspacing = default_spacing(self.ax, 'x',
                                           self.ax.xaxis.apl_label_form)
            else:
                xspacing = self.ax.xaxis.apl_tick_spacing
        else:
            xspacing = self.x_grid_spacing

        if xspacing is None:
            warnings.warn("Could not determine x tick spacing - grid cannot be drawn")
            return

        if self._wcs.xaxis_coord_type in ['longitude', 'latitude']:
            xspacing = xspacing.todegrees()

        # Set y grid spacing
        if self.y_auto_spacing:
            if self.ax.yaxis.apl_auto_tick_spacing:
                yspacing = default_spacing(self.ax, 'y',
                                           self.ax.yaxis.apl_label_form)
            else:
                yspacing = self.ax.yaxis.apl_tick_spacing
        else:
            yspacing = self.y_grid_spacing

        if yspacing is None:
            warnings.warn("Could not determine y tick spacing - grid cannot be drawn")
            return

        if self._wcs.yaxis_coord_type in ['longitude', 'latitude']:
            yspacing = yspacing.todegrees()

        # Find x lines that intersect with axes
        grid_x_i, grid_y_i = find_intersections(self.ax, 'x', xspacing)

        # Ensure that longitudes are between 0 and 360, and latitudes between
        # -90 and 90
        if self._wcs.xaxis_coord_type == 'longitude':
            grid_x_i = np.mod(grid_x_i, 360.)
        elif self._wcs.xaxis_coord_type == 'latitude':
            grid_x_i = np.mod(grid_x_i + 90., 180.) - 90.

        if self._wcs.yaxis_coord_type == 'longitude':
            grid_y_i = np.mod(grid_y_i, 360.)
        elif self._wcs.yaxis_coord_type == 'latitude':
            grid_y_i = np.mod(grid_y_i + 90., 180.) - 90.

        # If we are dealing with longitude/latitude then can search all
        # neighboring grid lines to see if there are any closed longitude
        # lines
        if self._wcs.xaxis_coord_type == 'latitude' and self._wcs.yaxis_coord_type == 'longitude' and len(grid_x_i) > 0:

            gx = grid_x_i.min()

            while True:
                gx -= xspacing
                xpix, ypix = wcs_util.world2pix(self._wcs, gx, 0.)
                if in_plot(self.ax, xpix, ypix) and gx >= -90.:
                    grid_x_i = np.hstack([grid_x_i, gx, gx])
                    grid_y_i = np.hstack([grid_y_i, 0., 360.])
                else:
                    break

            gx = grid_x_i.max()

            while True:
                gx += xspacing
                xpix, ypix = wcs_util.world2pix(self._wcs, gx, 0.)
                if in_plot(self.ax, xpix, ypix) and gx <= +90.:
                    grid_x_i = np.hstack([grid_x_i, gx, gx])
                    grid_y_i = np.hstack([grid_y_i, 0., 360.])
                else:
                    break

        # Plot those lines
        for gx in np.unique(grid_x_i):
            for line in plot_grid_x(self.ax, grid_x_i, grid_y_i, gx):
                lines.append(line)

        # Find y lines that intersect with axes
        grid_x_i, grid_y_i = find_intersections(self.ax, 'y', yspacing)

        if self._wcs.xaxis_coord_type == 'longitude':
            grid_x_i = np.mod(grid_x_i, 360.)
        elif self._wcs.xaxis_coord_type == 'latitude':
            grid_x_i = np.mod(grid_x_i + 90., 180.) - 90.

        if self._wcs.yaxis_coord_type == 'longitude':
            grid_y_i = np.mod(grid_y_i, 360.)
        elif self._wcs.yaxis_coord_type == 'latitude':
            grid_y_i = np.mod(grid_y_i + 90., 180.) - 90.

        # If we are dealing with longitude/latitude then can search all
        # neighboring grid lines to see if there are any closed longitude
        # lines
        if (self._wcs.xaxis_coord_type == 'longitude' and
           self._wcs.yaxis_coord_type == 'latitude' and len(grid_y_i) > 0):

            gy = grid_y_i.min()

            while True:
                gy -= yspacing
                xpix, ypix = wcs_util.world2pix(self._wcs, 0., gy)
                if in_plot(self.ax, xpix, ypix) and gy >= -90.:
                    grid_x_i = np.hstack([grid_x_i, 0., 360.])
                    grid_y_i = np.hstack([grid_y_i, gy, gy])
                else:
                    break

            gy = grid_y_i.max()

            while True:
                gy += yspacing
                xpix, ypix = wcs_util.world2pix(self._wcs, 0., gy)
                if in_plot(self.ax, xpix, ypix) and gy <= +90.:
                    grid_x_i = np.hstack([grid_x_i, 0., 360.])
                    grid_y_i = np.hstack([grid_y_i, gy, gy])
                else:
                    break

        # Plot those lines
        for gy in np.unique(grid_y_i):
            for line in plot_grid_y(self.ax, grid_x_i, grid_y_i, gy):
                lines.append(line)

        if self._grid:
            self._grid.set_verts(lines)
        else:
            self._grid = LineCollection(lines, transOffset=self.ax.transData)
            self.ax.add_collection(self._grid, False)

        return self.ax


def plot_grid_y(ax, grid_x, grid_y, gy, alpha=0.5):
    '''Plot a single grid line in the y direction'''

    wcs = ax._wcs
    lines_out = []

    # Find intersections that correspond to latitude lat0
    index = np.where(grid_y == gy)

    # Produce sorted array of the longitudes of all intersections
    grid_x_sorted = np.sort(grid_x[index])

    # If coordinate type is a latitude or longitude, also need to check if
    # end-points fall inside the plot
    if wcs.xaxis_coord_type == 'latitude':
        if not np.any(grid_x_sorted == -90):
            xpix, ypix = wcs_util.world2pix(wcs, max(grid_x_sorted[0] - 1., -90.), gy)
            if in_plot(ax, xpix, ypix):
                grid_x_sorted = np.hstack([-90., grid_x_sorted])
        if not np.any(grid_x_sorted == +90):
            xpix, ypix = wcs_util.world2pix(wcs, min(grid_x_sorted[-1] + 1., +90.), gy)
            if in_plot(ax, xpix, ypix):
                grid_x_sorted = np.hstack([grid_x_sorted, +90.])
    elif wcs.xaxis_coord_type == 'longitude':
        if not np.any(grid_x_sorted == 0.):
            xpix, ypix = wcs_util.world2pix(wcs, max(grid_x_sorted[0] - 1., 0.), gy)
            if in_plot(ax, xpix, ypix):
                grid_x_sorted = np.hstack([0., grid_x_sorted])
        if not np.any(grid_x_sorted == 360.):
            xpix, ypix = wcs_util.world2pix(wcs, min(grid_x_sorted[-1] + 1., 360.), gy)
            if in_plot(ax, xpix, ypix):
                grid_x_sorted = np.hstack([grid_x_sorted, 360.])

    # Check if the first mid-point with coordinates is inside the viewport
    xpix, ypix = wcs_util.world2pix(wcs, (grid_x_sorted[0] + grid_x_sorted[1]) / 2., gy)

    if not in_plot(ax, xpix, ypix):
        grid_x_sorted = np.roll(grid_x_sorted, 1)

    # Check that number of grid points is even
    if len(grid_x_sorted) % 2 == 1:
        warnings.warn("Unexpected number of grid points - x grid lines cannot be drawn")
        return []

    # Cycle through intersections
    for i in range(0, len(grid_x_sorted), 2):

        grid_x_min = grid_x_sorted[i]
        grid_x_max = grid_x_sorted[i + 1]

        x_world = math_util.complete_range(grid_x_min, grid_x_max, 100)
        y_world = np.repeat(gy, len(x_world))
        x_pix, y_pix = wcs_util.world2pix(wcs, x_world, y_world)
        lines_out.append(zip(x_pix, y_pix))

    return lines_out


def plot_grid_x(ax, grid_x, grid_y, gx, alpha=0.5):
    '''Plot a single longitude line'''

    wcs = ax._wcs
    lines_out = []

    # Find intersections that correspond to longitude gx
    index = np.where(grid_x == gx)

    # Produce sorted array of the latitudes of all intersections
    grid_y_sorted = np.sort(grid_y[index])

    # If coordinate type is a latitude or longitude, also need to check if
    # end-points fall inside the plot
    if wcs.yaxis_coord_type == 'latitude':
        if not np.any(grid_y_sorted == -90):
            xpix, ypix = wcs_util.world2pix(wcs, gx, max(grid_y_sorted[0] - 1., -90.))
            if in_plot(ax, xpix, ypix):
                grid_y_sorted = np.hstack([-90., grid_y_sorted])
        if not np.any(grid_y_sorted == +90):
            xpix, ypix = wcs_util.world2pix(wcs, gx, min(grid_y_sorted[-1] + 1., +90.))
            if in_plot(ax, xpix, ypix):
                grid_y_sorted = np.hstack([grid_y_sorted, +90.])
    elif wcs.yaxis_coord_type == 'longitude':
        if not np.any(grid_y_sorted == 0.):
            xpix, ypix = wcs_util.world2pix(wcs, gx, max(grid_y_sorted[0] - 1., 0.))
            if in_plot(ax, xpix, ypix):
                grid_y_sorted = np.hstack([0., grid_y_sorted])
        if not np.any(grid_y_sorted == 360.):
            xpix, ypix = wcs_util.world2pix(wcs, gx, min(grid_y_sorted[-1] + 1., 360.))
            if in_plot(ax, xpix, ypix):
                grid_y_sorted = np.hstack([grid_y_sorted, 360.])

    # Check if the first mid-point with coordinates is inside the viewport
    xpix, ypix = wcs_util.world2pix(wcs, gx, (grid_y_sorted[0] + grid_y_sorted[1]) / 2.)

    if not in_plot(ax, xpix, ypix):
        grid_y_sorted = np.roll(grid_y_sorted, 1)

    # Check that number of grid points is even
    if len(grid_y_sorted) % 2 == 1:
        warnings.warn("Unexpected number of grid points - y grid lines cannot be drawn")
        return []

    # Cycle through intersections
    for i in range(0, len(grid_y_sorted), 2):

        grid_y_min = grid_y_sorted[i]
        grid_y_max = grid_y_sorted[i + 1]

        y_world = math_util.complete_range(grid_y_min, grid_y_max, 100)
        x_world = np.repeat(gx, len(y_world))
        x_pix, y_pix = wcs_util.world2pix(wcs, x_world, y_world)
        lines_out.append(zip(x_pix, y_pix))

    return lines_out


def in_plot(ax, x_pix, y_pix):
    '''Check whether a given point is in a plot'''

    xmin, xmax = ax.xaxis.get_view_interval()
    ymin, ymax = ax.yaxis.get_view_interval()

    return (x_pix > xmin + 0.5 and x_pix < xmax + 0.5 and
            y_pix > ymin + 0.5 and y_pix < ymax + 0.5)


def find_intersections(ax, coord, spacing):
    '''
    Find intersections of a given coordinate with all axes

    Parameters
    ----------

    ax :
       The matplotlib axis instance for the figure.

    coord : { 'x', 'y' }
       The coordinate for which we are looking for ticks.

    spacing : float
       The spacing along the axis.

    '''

    wcs = ax._wcs

    xmin, xmax = ax.xaxis.get_view_interval()
    ymin, ymax = ax.yaxis.get_view_interval()

    options = dict(mode='xy', xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)

    # Initialize arrays
    x, y = [], []

    # Bottom X axis
    (labels_x, labels_y, world_x, world_y) = tick_positions(
        wcs, spacing, 'x', coord, farside=False, **options)

    x.extend(world_x)
    y.extend(world_y)

    # Top X axis
    (labels_x, labels_y, world_x, world_y) = tick_positions(
        wcs, spacing, 'x', coord, farside=True, **options)

    x.extend(world_x)
    y.extend(world_y)

    # Left Y axis
    (labels_x, labels_y, world_x, world_y) = tick_positions(
        wcs, spacing, 'y', coord, farside=False, **options)

    x.extend(world_x)
    y.extend(world_y)

    # Right Y axis
    (labels_x, labels_y, world_x, world_y) = tick_positions(
        wcs, spacing, 'y', coord, farside=True, **options)

    x.extend(world_x)
    y.extend(world_y)

    return np.array(x), np.array(y)

########NEW FILE########
__FILENAME__ = header
from __future__ import absolute_import, print_function, division

from astropy import log


def check(header, convention=None, dimensions=[0, 1]):

    ix = dimensions[0] + 1
    iy = dimensions[1] + 1

    # If header does not contain CTYPE keywords, assume that the WCS is
    # missing or incomplete, and replace it with a 1-to-1 pixel mapping
    if 'CTYPE%i' % ix not in header or 'CTYPE%i' % iy not in header:
        log.warning("No WCS information found in header - using pixel coordinates")
        header.update('CTYPE%i' % ix, 'PIXEL')
        header.update('CTYPE%i' % iy, 'PIXEL')
        header.update('CRVAL%i' % ix, 0.)
        header.update('CRVAL%i' % iy, 0.)
        header.update('CRPIX%i' % ix, 0.)
        header.update('CRPIX%i' % iy, 0.)
        header.update('CDELT%i' % ix, 1.)
        header.update('CDELT%i' % iy, 1.)

    if header['CTYPE%i' % ix][4:] == '-CAR' and header['CTYPE%i' % iy][4:] == '-CAR':

        if header['CTYPE%i' % ix][:4] == 'DEC-' or header['CTYPE%i' % ix][1:4] == 'LAT':
            ilon = iy
            ilat = ix
        elif header['CTYPE%i' % iy][:4] == 'DEC-' or header['CTYPE%i' % iy][1:4] == 'LAT':
            ilon = ix
            ilat = iy
        else:
            ilon = None
            ilat = None

        if ilat is not None and header['CRVAL%i' % ilat] != 0:

            if convention == 'calabretta':
                pass  # we don't need to do anything
            elif convention == 'wells':
                if 'CDELT%i' % ilat not in header:
                    raise Exception("Need CDELT%i to be present for wells convention" % ilat)
                crpix = header['CRPIX%i' % ilat]
                crval = header['CRVAL%i' % ilat]
                cdelt = header['CDELT%i' % ilat]
                crpix = crpix - crval / cdelt
                try:
                    header['CRPIX%i' % ilat] = crpix
                    header['CRVAL%i' % ilat] = 0.
                except:  # older versions of PyFITS
                    header.update('CRPIX%i' % ilat, crpix)
                    header.update('CRVAL%i' % ilon, 0.)

            else:
                raise Exception('''WARNING: projection is Plate Caree (-CAR) and
                CRVALy is not zero. This can be intepreted either according to
                Wells (1981) or Calabretta (2002). The former defines the
                projection as rectilinear regardless of the value of CRVALy,
                whereas the latter defines the projection as rectilinear only when
                CRVALy is zero. You will need to specify the convention to assume
                by setting either convention='wells' or convention='calabretta'
                when initializing the FITSFigure instance. ''')

    return header

########NEW FILE########
__FILENAME__ = image_util
from __future__ import absolute_import, print_function, division

import numpy as np
from astropy import log

from . import math_util as m


class interp1d(object):

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dy = np.zeros(y.shape, dtype=y.dtype)
        self.dy[:-1] = (self.y[1:] - self.y[:-1]) / (self.x[1:] - self.x[:-1])
        self.dy[-1] = self.dy[-2]

    def __call__(self, x_new):

        ipos = np.searchsorted(self.x, x_new)

        if m.isnumeric(x_new):
            if ipos == 0:
                ipos = 1
            if ipos == len(self.x):
                ipos = len(self.x) - 1
        else:
            ipos[ipos == 0] = 1
            ipos[ipos == len(self.x)] = len(self.x) - 1

        ipos = ipos - 1

        return (x_new - self.x[ipos]) * self.dy[ipos] + self.y[ipos]


def resample(array, factor):

    nx, ny = np.shape(array)

    nx_new = nx // factor
    ny_new = ny // factor

    array2 = np.zeros((nx_new, ny))
    for i in range(nx_new):
        array2[i, :] = np.mean(array[i * factor:(i + 1) * factor, :], axis=0)

    array3 = np.zeros((nx_new, ny_new))
    for j in range(ny_new):
        array3[:, j] = np.mean(array2[:, j * factor:(j + 1) * factor], axis=1)

    return array3


def percentile_function(array):

    if np.all(np.isnan(array) | np.isinf(array)):
        log.warning("Image contains only NaN or Inf values")
        return lambda x: 0

    array = array.ravel()
    array = array[np.where(np.isnan(array) == False)]
    array = array[np.where(np.isinf(array) == False)]

    n_total = np.shape(array)[0]
    array = np.sort(array)

    x = np.linspace(0., 100., num=n_total)

    spl = interp1d(x=x, y=array)

    if n_total > 10000:
        x = np.linspace(0., 100., num=10000)
        spl = interp1d(x=x, y=spl(x))

    array = None

    return spl


def stretch(array, function, exponent=2, midpoint=None):

    if function == 'linear':
        return array
    elif function == 'log':
        if not m.isnumeric(midpoint):
            midpoint = 0.05
        return np.log10(array / midpoint + 1.) / np.log10(1. / midpoint + 1.)
    elif function == 'sqrt':
        return np.sqrt(array)
    elif function == 'arcsinh':
        if not m.isnumeric(midpoint):
            midpoint = -0.033
        return np.arcsinh(array / midpoint) / np.arcsinh(1. / midpoint)
    elif function == 'power':
        return np.power(array, exponent)
    else:
        raise Exception("Unknown function : " + function)


def _matplotlib_pil_bug_present():
    """
    Determine whether PIL images should be pre-flipped due to a bug in Matplotlib.

    Prior to Matplotlib 1.2.0, RGB images provided as PIL objects were
    oriented wrongly. This function tests whether the bug is present.
    """

    from matplotlib.image import pil_to_array

    try:
        from PIL import Image
    except:
        import Image

    from astropy import log

    array1 = np.array([[1,2],[3,4]], dtype=np.uint8)
    image = Image.fromarray(array1)
    array2 = pil_to_array(image)

    if np.all(array1 == array2):
        log.debug("PIL Image flipping bug not present in Matplotlib")
        return False
    elif np.all(array1 == array2[::-1,:]):
        log.debug("PIL Image flipping bug detected in Matplotlib")
        return True
    else:
        log.warning("Could not properly determine Matplotlib behavior for RGB images - image may be flipped incorrectly")
        return False

########NEW FILE########
__FILENAME__ = labels
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

import warnings

import numpy as np
import matplotlib.pyplot as mpl
from matplotlib.font_manager import FontProperties

from . import wcs_util
from . import angle_util as au
from .decorators import auto_refresh, fixdocstring


class TickLabels(object):

    def __init__(self, parent):

        # Store references to axes
        self._ax1 = parent._ax1
        self._ax2 = parent._ax2
        self._wcs = parent._wcs
        self._figure = parent._figure

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

        # Set font
        self._label_fontproperties = FontProperties()

        self.set_style('plain')

        system, equinox, units = wcs_util.system(self._wcs)

        # Set default label format
        if self._wcs.xaxis_coord_type in ['longitude', 'latitude']:
            if system['name'] == 'equatorial':
                if self._wcs.xaxis_coord_type == 'longitude':
                    self.set_xformat("hh:mm:ss.ss")
                else:
                    self.set_xformat("dd:mm:ss.s")
            else:
                self.set_xformat("ddd.dddd")
        else:
            self.set_xformat('%g')

        if self._wcs.yaxis_coord_type in ['longitude', 'latitude']:
            if system['name'] == 'equatorial':
                if self._wcs.yaxis_coord_type == 'longitude':
                    self.set_yformat("hh:mm:ss.ss")
                else:
                    self.set_yformat("dd:mm:ss.s")
            else:
                self.set_yformat("ddd.dddd")
        else:
            self.set_yformat('%g')

        # Set major tick formatters
        fx1 = WCSFormatter(wcs=self._wcs, coord='x')
        fy1 = WCSFormatter(wcs=self._wcs, coord='y')
        self._ax1.xaxis.set_major_formatter(fx1)
        self._ax1.yaxis.set_major_formatter(fy1)

        fx2 = mpl.NullFormatter()
        fy2 = mpl.NullFormatter()
        self._ax2.xaxis.set_major_formatter(fx2)
        self._ax2.yaxis.set_major_formatter(fy2)

        # Cursor display
        self._ax1._cursor_world = True
        self._figure.canvas.mpl_connect('key_press_event', self._set_cursor_prefs)

    @auto_refresh
    def set_xformat(self, format):
        '''
        Set the format of the x-axis tick labels.

        If the x-axis type is ``longitude`` or ``latitude``, then the options
        are:

            * ``ddd.ddddd`` - decimal degrees, where the number of decimal places can be varied
            * ``hh`` or ``dd`` - hours (or degrees)
            * ``hh:mm`` or ``dd:mm`` - hours and minutes (or degrees and arcminutes)
            * ``hh:mm:ss`` or ``dd:mm:ss`` - hours, minutes, and seconds (or degrees, arcminutes, and arcseconds)
            * ``hh:mm:ss.ss`` or ``dd:mm:ss.ss`` - hours, minutes, and seconds (or degrees, arcminutes, and arcseconds), where the number of decimal places can be varied.

        If the x-axis type is ``scalar``, then the format should be a valid
        python string format beginning with a ``%``.

        If one of these arguments is not specified, the format for that axis
        is left unchanged.
        '''
        if self._wcs.xaxis_coord_type in ['longitude', 'latitude']:
            if format.startswith('%'):
                raise Exception("Cannot specify Python format for longitude or latitude")
            try:
                if not self._ax1.xaxis.apl_auto_tick_spacing:
                    au._check_format_spacing_consistency(format, self._ax1.xaxis.apl_tick_spacing)
            except au.InconsistentSpacing:
                warnings.warn("WARNING: Requested label format is not accurate enough to display ticks. The label format will not be changed.")
                return
        else:
            if not format.startswith('%'):
                raise Exception("For scalar tick labels, format should be a Python format beginning with %")

        self._ax1.xaxis.apl_label_form = format
        self._ax2.xaxis.apl_label_form = format

    @auto_refresh
    def set_yformat(self, format):
        '''
        Set the format of the y-axis tick labels.

        If the y-axis type is ``longitude`` or ``latitude``, then the options
        are:

            * ``ddd.ddddd`` - decimal degrees, where the number of decimal places can be varied
            * ``hh`` or ``dd`` - hours (or degrees)
            * ``hh:mm`` or ``dd:mm`` - hours and minutes (or degrees and arcminutes)
            * ``hh:mm:ss`` or ``dd:mm:ss`` - hours, minutes, and seconds (or degrees, arcminutes, and arcseconds)
            * ``hh:mm:ss.ss`` or ``dd:mm:ss.ss`` - hours, minutes, and seconds (or degrees, arcminutes, and arcseconds), where the number of decimal places can be varied.

        If the y-axis type is ``scalar``, then the format should be a valid
        python string format beginning with a ``%``.

        If one of these arguments is not specified, the format for that axis
        is left unchanged.
        '''
        if self._wcs.yaxis_coord_type in ['longitude', 'latitude']:
            if format.startswith('%'):
                raise Exception("Cannot specify Python format for longitude or latitude")
            try:
                if not self._ax1.yaxis.apl_auto_tick_spacing:
                    au._check_format_spacing_consistency(format, self._ax1.yaxis.apl_tick_spacing)
            except au.InconsistentSpacing:
                warnings.warn("WARNING: Requested label format is not accurate enough to display ticks. The label format will not be changed.")
                return
        else:
            if not format.startswith('%'):
                raise Exception("For scalar tick labels, format should be a Python format beginning with %")

        self._ax1.yaxis.apl_label_form = format
        self._ax2.yaxis.apl_label_form = format

    @auto_refresh
    def set_style(self, style):
        """
        Set the format of the x-axis tick labels.

        This can be 'colons' or 'plain':

            * 'colons' uses colons as separators, for example 31:41:59.26 +27:18:28.1
            * 'plain' uses letters and symbols as separators, for example 31h41m59.26s +27º18'28.1"
        """

        if style == 'latex':
            warnings.warn("latex has now been merged with plain - whether or not to use LaTeX is controled through set_system_latex")
            style = 'plain'

        if not style in ['colons', 'plain']:
            raise Exception("Label style should be one of colons/plain")

        self._ax1.xaxis.apl_labels_style = style
        self._ax1.yaxis.apl_labels_style = style
        self._ax2.xaxis.apl_labels_style = style
        self._ax2.yaxis.apl_labels_style = style

    @auto_refresh
    @fixdocstring
    def set_font(self, family=None, style=None, variant=None, stretch=None, weight=None, size=None, fontproperties=None):
        """
        Set the font of the tick labels.

        Parameters
        ----------

        common: family, style, variant, stretch, weight, size, fontproperties

        Notes
        -----

        Default values are set by matplotlib or previously set values if
        set_font has already been called. Global default values can be set by
        editing the matplotlibrc file.
        """

        if family:
            self._label_fontproperties.set_family(family)

        if style:
            self._label_fontproperties.set_style(style)

        if variant:
            self._label_fontproperties.set_variant(variant)

        if stretch:
            self._label_fontproperties.set_stretch(stretch)

        if weight:
            self._label_fontproperties.set_weight(weight)

        if size:
            self._label_fontproperties.set_size(size)

        if fontproperties:
            self._label_fontproperties = fontproperties

        for tick in self._ax1.get_xticklabels():
            tick.set_fontproperties(self._label_fontproperties)
        for tick in self._ax1.get_yticklabels():
            tick.set_fontproperties(self._label_fontproperties)
        for tick in self._ax2.get_xticklabels():
            tick.set_fontproperties(self._label_fontproperties)
        for tick in self._ax2.get_yticklabels():
            tick.set_fontproperties(self._label_fontproperties)

    @auto_refresh
    def show(self):
        """
        Show the x- and y-axis tick labels.
        """
        self.show_x()
        self.show_y()

    @auto_refresh
    def hide(self):
        """
        Hide the x- and y-axis tick labels.
        """
        self.hide_x()
        self.hide_y()

    @auto_refresh
    def show_x(self):
        """
        Show the x-axis tick labels.
        """

        for tick in self._ax1.get_xticklabels():
            tick.set_visible(True)
        for tick in self._ax2.get_xticklabels():
            tick.set_visible(True)

    @auto_refresh
    def hide_x(self):
        """
        Hide the x-axis tick labels.
        """

        for tick in self._ax1.get_xticklabels():
            tick.set_visible(False)
        for tick in self._ax2.get_xticklabels():
            tick.set_visible(False)

    @auto_refresh
    def show_y(self):
        """
        Show the y-axis tick labels.
        """

        for tick in self._ax1.get_yticklabels():
            tick.set_visible(True)
        for tick in self._ax2.get_yticklabels():
            tick.set_visible(True)

    @auto_refresh
    def hide_y(self):
        """
        Hide the y-axis tick labels.
        """

        for tick in self._ax1.get_yticklabels():
            tick.set_visible(False)
        for tick in self._ax2.get_yticklabels():
            tick.set_visible(False)

    @auto_refresh
    def set_xposition(self, position):
        """
        Set the position of the x-axis tick labels ('top' or 'bottom')
        """
        if position == 'bottom':
            fx1 = WCSFormatter(wcs=self._wcs, coord='x')
            self._ax1.xaxis.set_major_formatter(fx1)
            fx2 = mpl.NullFormatter()
            self._ax2.xaxis.set_major_formatter(fx2)
        elif position == 'top':
            fx1 = mpl.NullFormatter()
            self._ax1.xaxis.set_major_formatter(fx1)
            fx2 = WCSFormatter(wcs=self._wcs, coord='x')
            self._ax2.xaxis.set_major_formatter(fx2)
        else:
            raise ValueError("position should be one of 'top' or 'bottom'")

    @auto_refresh
    def set_yposition(self, position):
        """
        Set the position of the y-axis tick labels ('left' or 'right')
        """
        if position == 'left':
            fy1 = WCSFormatter(wcs=self._wcs, coord='y')
            self._ax1.yaxis.set_major_formatter(fy1)
            fy2 = mpl.NullFormatter()
            self._ax2.yaxis.set_major_formatter(fy2)
        elif position == 'right':
            fy1 = mpl.NullFormatter()
            self._ax1.yaxis.set_major_formatter(fy1)
            fy2 = WCSFormatter(wcs=self._wcs, coord='y')
            self._ax2.yaxis.set_major_formatter(fy2)
        else:
            raise ValueError("position should be one of 'left' or 'right'")

    def _set_cursor_prefs(self, event, **kwargs):
        if event.key == 'c':
            self._ax1._cursor_world = not self._ax1._cursor_world

    def _cursor_position(self, x, y):

        xaxis = self._ax1.xaxis
        yaxis = self._ax1.yaxis

        if self._ax1._cursor_world:

            xw, yw = wcs_util.pix2world(self._wcs, x, y)

            if self._wcs.xaxis_coord_type in ['longitude', 'latitude']:

                xw = au.Angle(degrees=xw, latitude=self._wcs.xaxis_coord_type == 'latitude')

                hours = 'h' in xaxis.apl_label_form

                if hours:
                    xw = xw.tohours()

                if xaxis.apl_labels_style in ['plain', 'latex']:
                    sep = ('d', 'm', 's')
                    if hours:
                        sep = ('h', 'm', 's')
                elif xaxis.apl_labels_style == 'colons':
                    sep = (':', ':', '')

                xlabel = xw.tostringlist(format=xaxis.apl_label_form, sep=sep)
                xlabel = "".join(xlabel)

            else:

                xlabel = xaxis.apl_label_form % xw

            if self._wcs.yaxis_coord_type in ['longitude', 'latitude']:

                yw = au.Angle(degrees=yw, latitude=self._wcs.yaxis_coord_type == 'latitude')

                hours = 'h' in yaxis.apl_label_form

                if hours:
                    yw = yw.tohours()

                if yaxis.apl_labels_style in ['plain', 'latex']:
                    sep = ('d', 'm', 's')
                    if hours:
                        sep = ('h', 'm', 's')
                elif yaxis.apl_labels_style == 'colons':
                    sep = (':', ':', '')

                ylabel = yw.tostringlist(format=yaxis.apl_label_form, sep=sep)
                ylabel = "".join(ylabel)

            else:

                ylabel = yaxis.apl_label_form % yw

            return  "%s %s (world)" % (xlabel, ylabel)

        else:

            return "%g %g (pixel)" % (x, y)


class WCSFormatter(mpl.Formatter):

    def __init__(self, wcs=False, coord='x'):
        self._wcs = wcs
        self.coord = coord

    def __call__(self, x, pos=None):
        """
        Return the format for tick val x at position pos; pos=None indicated
        unspecified
        """
        self.coord_type = self._wcs.xaxis_coord_type if self.coord == 'x' else self._wcs.yaxis_coord_type

        if self.coord_type in ['longitude', 'latitude']:

            au._check_format_spacing_consistency(self.axis.apl_label_form, self.axis.apl_tick_spacing)

            hours = 'h' in self.axis.apl_label_form

            if self.axis.apl_labels_style == 'plain':
                if mpl.rcParams['text.usetex']:
                    label_style = 'plain_tex'
                else:
                    label_style = 'plain_notex'
            else:
                label_style = self.axis.apl_labels_style

            if label_style == 'plain_notex':
                sep = ('\u00b0', "'", '"')
                if hours:
                    sep = ('h', 'm', 's')
            elif label_style == 'colons':
                sep = (':', ':', '')
            elif label_style == 'plain_tex':
                if hours:
                    sep = ('^{h}', '^{m}', '^{s}')
                else:
                    sep = ('^{\circ}', '^{\prime}', '^{\prime\prime}')

            ipos = np.argmin(np.abs(self.axis.apl_tick_positions_pix - x))

            label = self.axis.apl_tick_spacing * self.axis.apl_tick_positions_world[ipos]
            if hours:
                label = label.tohours()
            label = label.tostringlist(format=self.axis.apl_label_form, sep=sep)

            # Check if neighboring label is similar and if so whether some
            # elements of the current label are redundant and can be dropped.
            # This should only be done for sexagesimal coordinates

            if len(label) > 1:

                if self.coord == x or self.axis.apl_tick_positions_world[ipos] > 0:
                    comp_ipos = ipos - 1
                else:
                    comp_ipos = ipos + 1

                if comp_ipos >= 0 and comp_ipos <= len(self.axis.apl_tick_positions_pix) - 1:

                    comp_label = self.axis.apl_tick_spacing * self.axis.apl_tick_positions_world[comp_ipos]
                    if hours:
                        comp_label = comp_label.tohours()
                    comp_label = comp_label.tostringlist(format=self.axis.apl_label_form, sep=sep)

                    for iter in range(len(label)):
                        if comp_label[0] == label[0]:
                            label.pop(0)
                            comp_label.pop(0)
                        else:
                            break

        else:

            ipos = np.argmin(np.abs(self.axis.apl_tick_positions_pix - x))
            label = self.axis.apl_tick_spacing * self.axis.apl_tick_positions_world[ipos]
            label = self.axis.apl_label_form % label

        if mpl.rcParams['text.usetex']:
            return "$" + "".join(label) + "$"
        else:
            return "".join(label)

########NEW FILE########
__FILENAME__ = layers
from __future__ import absolute_import, print_function, division

from matplotlib.contour import ContourSet
from matplotlib.collections import RegularPolyCollection, \
    PatchCollection, CircleCollection, LineCollection

from .regions import ArtistCollection
from .decorators import auto_refresh


class Layers(object):

    def __init__(self):
        pass

    def _layer_type(self, layer):
        if isinstance(self._layers[layer], ContourSet):
            return 'contour'
        elif isinstance(self._layers[layer], RegularPolyCollection):
            return 'collection'
        elif isinstance(self._layers[layer], PatchCollection):
            return 'collection'
        elif isinstance(self._layers[layer], CircleCollection):
            return 'collection'
        elif isinstance(self._layers[layer], LineCollection):
            return 'collection'
        elif isinstance(self._layers[layer], ArtistCollection):
            return 'collection'
        elif hasattr(self._layers[layer], 'remove') and hasattr(self._layers[layer], 'get_visible') and hasattr(self._layers[layer], 'set_visible'):
            return 'collection'
        else:
            raise Exception("Unknown layer type: " + \
                str(type(self._layers[layer])))

    def _initialize_layers(self):

        self._layers = {}
        self._contour_counter = 0
        self._scatter_counter = 0
        self._circle_counter = 0
        self._ellipse_counter = 0
        self._rectangle_counter = 0
        self._linelist_counter = 0
        self._region_counter = 0
        self._label_counter = 0
        self._poly_counter = 0

    def list_layers(self):
        '''
        Print a list of layers to standard output.
        '''

        layers_list = []

        for layer in self._layers:

            layer_type = self._layer_type(layer)

            if layer_type == 'contour':
                visible = self._layers[layer].collections[0].get_visible()
            elif layer_type == 'collection':
                visible = self._layers[layer].get_visible()

            layers_list.append({'name': layer, 'visible': visible})

        n_layers = len(layers_list)
        if n_layers == 0:
            print("\n  There are no layers in this figure")
        else:
            if n_layers == 1:
                print("\n  There is one layer in this figure:\n")
            else:
                print("\n  There are " + str(n_layers) + \
                    " layers in this figure:\n")
            for layer in layers_list:
                if layer['visible']:
                    print("   -> " + layer['name'])
                else:
                    print("   -> " + layer['name'] + " (hidden)")

    @auto_refresh
    def remove_layer(self, layer, raise_exception=True):
        '''
        Remove a layer.

        Parameters
        ----------
        layer : str
            The name of the layer to remove
        '''

        if layer in self._layers:

            layer_type = self._layer_type(layer)

            if layer_type == 'contour':
                for contour in self._layers[layer].collections:
                    contour.remove()
                self._layers.pop(layer)
            elif layer_type == 'collection':
                self._layers[layer].remove()
                self._layers.pop(layer)
                if (layer + '_txt') in self._layers:
                    self._layers[layer + '_txt'].remove()
                    self._layers.pop(layer + '_txt')

        else:

            if raise_exception:
                raise Exception("Layer " + layer + " does not exist")

    @auto_refresh
    def hide_layer(self, layer, raise_exception=True):
        '''
        Hide a layer.

        This differs from remove_layer in that if a layer is hidden
        it can be shown again using show_layer.

        Parameters
        ----------
        layer : str
            The name of the layer to hide
        '''
        if layer in self._layers:

            layer_type = self._layer_type(layer)

            if layer_type == 'contour':
                for contour in self._layers[layer].collections:
                    contour.set_visible(False)
            elif layer_type == 'collection':
                self._layers[layer].set_visible(False)

        else:

            if raise_exception:
                raise Exception("Layer " + layer + " does not exist")

    @auto_refresh
    def show_layer(self, layer, raise_exception=True):
        '''
        Show a layer.

        This shows a layer previously hidden with hide_layer

        Parameters
        ----------
        layer : str
            The name of the layer to show
        '''
        if layer in self._layers:

            layer_type = self._layer_type(layer)

            if layer_type == 'contour':
                for contour in self._layers[layer].collections:
                    contour.set_visible(True)
            elif layer_type == 'collection':
                self._layers[layer].set_visible(True)

        else:
            if raise_exception:
                raise Exception("Layer " + layer + " does not exist")

    def get_layer(self, layer, raise_exception=True):
        '''
        Return a layer object.

        Parameters
        ----------
        layer : str
            The name of the layer to return
        '''
        if layer in self._layers:
            return self._layers[layer]
        else:
            if raise_exception:
                raise Exception("Layer " + layer + " does not exist")

########NEW FILE########
__FILENAME__ = math_util
from __future__ import absolute_import, print_function, division

import numpy as np


def isnumeric(value):
    return type(value) in [float, int, np.int8, np.int16, np.int32, \
        np.float32, np.float64]


def smart_range(array):

    array.sort()

    minval = 360.
    i1 = 0
    i2 = 0

    for i in range(0, np.size(array) - 1):
        if 360. - abs(array[i + 1] - array[i]) < minval:
            minval = 360. - abs(array[i + 1] - array[i])
            i1 = i + 1
            i2 = i

    if(max(array) - min(array) < minval):
        i1 = 0
        i2 = np.size(array) - 1

    x_min = array[i1]
    x_max = array[i2]

    if(x_min > x_max):
        x_min = x_min - 360.

    return x_min, x_max


def complete_range(xmin, xmax, spacing):
    if(xmax - xmin < 1):
        spacing = 10
    xstep = (xmax - xmin) / float(spacing)
    r = np.arange(xmin, xmax, xstep)
    if(np.any(r >= xmax)):
        return r
    else:
        return np.hstack([r, xmax])


def closest(array, a):
    ipos = np.argmin(np.abs(a - array))
    return array[ipos]


def divisors(n, dup=False):
    divisors = []
    i = 0
    if n == 1:
        return {1: 1}
    while 1:
        i += 1
        if dup:
            break
        if i == n + 1:
            break
        if n % i == 0:
            divisors[i:i + 1] = [i]
    return np.array(divisors)

########NEW FILE########
__FILENAME__ = normalize
from __future__ import absolute_import, print_function, division

# The APLpyNormalize class is largely based on code provided by Sarah Graves.

import numpy as np
import numpy.ma as ma

import matplotlib.cbook as cbook
from matplotlib.colors import Normalize


class APLpyNormalize(Normalize):
    '''
    A Normalize class for imshow that allows different stretching functions
    for astronomical images.
    '''

    def __init__(self, stretch='linear', exponent=5, vmid=None, vmin=None,
                 vmax=None, clip=False):
        '''
        Initalize an APLpyNormalize instance.

        Parameters
        ----------

        vmin : None or float, optional
            Minimum pixel value to use for the scaling.

        vmax : None or float, optional
            Maximum pixel value to use for the scaling.

        stretch : { 'linear', 'log', 'sqrt', 'arcsinh', 'power' }, optional
            The stretch function to use (default is 'linear').

        vmid : None or float, optional
            Mid-pixel value used for the log and arcsinh stretches. If
            set to None, a default value is picked.

        exponent : float, optional
            if self.stretch is set to 'power', this is the exponent to use.

        clip : str, optional
            If clip is True and the given value falls outside the range,
            the returned value will be 0 or 1, whichever is closer.
        '''

        if vmax < vmin:
            raise Exception("vmax should be larger than vmin")

        # Call original initalization routine
        Normalize.__init__(self, vmin=vmin, vmax=vmax, clip=clip)

        # Save parameters
        self.stretch = stretch
        self.exponent = exponent

        if stretch == 'power' and np.equal(self.exponent, None):
            raise Exception("For stretch=='power', an exponent should be specified")

        if np.equal(vmid, None):
            if stretch == 'log':
                if vmin > 0:
                    self.midpoint = vmax / vmin
                else:
                    raise Exception("When using a log stretch, if vmin < 0, then vmid has to be specified")
            elif stretch == 'arcsinh':
                self.midpoint = -1. / 30.
            else:
                self.midpoint = None
        else:
            if stretch == 'log':
                if vmin < vmid:
                    raise Exception("When using a log stretch, vmin should be larger than vmid")
                self.midpoint = (vmax - vmid) / (vmin - vmid)
            elif stretch == 'arcsinh':
                self.midpoint = (vmid - vmin) / (vmax - vmin)
            else:
                self.midpoint = None

    def __call__(self, value, clip=None):

        #read in parameters
        method = self.stretch
        exponent = self.exponent
        midpoint = self.midpoint

        # ORIGINAL MATPLOTLIB CODE

        if clip is None:
            clip = self.clip

        if cbook.iterable(value):
            vtype = 'array'
            val = ma.asarray(value).astype(np.float)
        else:
            vtype = 'scalar'
            val = ma.array([value]).astype(np.float)

        self.autoscale_None(val)
        vmin, vmax = self.vmin, self.vmax
        if vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        elif vmin == vmax:
            return 0.0 * val
        else:
            if clip:
                mask = ma.getmask(val)
                val = ma.array(np.clip(val.filled(vmax), vmin, vmax),
                                mask=mask)
            result = (val - vmin) * (1.0 / (vmax - vmin))

            # CUSTOM APLPY CODE

            # Keep track of negative values
            negative = result < 0.

            if self.stretch == 'linear':

                pass

            elif self.stretch == 'log':

                result = ma.log10(result * (self.midpoint - 1.) + 1.) \
                       / ma.log10(self.midpoint)

            elif self.stretch == 'sqrt':

                result = ma.sqrt(result)

            elif self.stretch == 'arcsinh':

                result = ma.arcsinh(result / self.midpoint) \
                       / ma.arcsinh(1. / self.midpoint)

            elif self.stretch == 'power':

                result = ma.power(result, exponent)

            else:

                raise Exception("Unknown stretch in APLpyNormalize: %s" %
                                self.stretch)

            # Now set previously negative values to 0, as these are
            # different from true NaN values in the FITS image
            result[negative] = -np.inf

        if vtype == 'scalar':
            result = result[0]

        return result

    def inverse(self, value):

        # ORIGINAL MATPLOTLIB CODE

        if not self.scaled():
            raise ValueError("Not invertible until scaled")

        vmin, vmax = self.vmin, self.vmax

        # CUSTOM APLPY CODE

        if cbook.iterable(value):
            val = ma.asarray(value)
        else:
            val = value

        if self.stretch == 'linear':

            pass

        elif self.stretch == 'log':

            val = (ma.power(10., val * ma.log10(self.midpoint)) - 1.) / (self.midpoint - 1.)

        elif self.stretch == 'sqrt':

            val = val * val

        elif self.stretch == 'arcsinh':

            val = self.midpoint * \
                  ma.sinh(val * ma.arcsinh(1. / self.midpoint))

        elif self.stretch == 'power':

            val = ma.power(val, (1. / self.exponent))

        else:

            raise Exception("Unknown stretch in APLpyNormalize: %s" %
                            self.stretch)

        return vmin + val * (vmax - vmin)

########NEW FILE########
__FILENAME__ = overlays
from __future__ import absolute_import, print_function, division

import warnings

from mpl_toolkits.axes_grid.anchored_artists \
    import AnchoredEllipse, AnchoredSizeBar

import numpy as np
from matplotlib.patches import FancyArrowPatch
from matplotlib.font_manager import FontProperties

from . import wcs_util
from .decorators import auto_refresh

corners = {}
corners['top right'] = 1
corners['top left'] = 2
corners['bottom left'] = 3
corners['bottom right'] = 4
corners['right'] = 5
corners['left'] = 6
corners['bottom'] = 8
corners['top'] = 9


class Compass(object):

    def _initialize_compass(self):

        # Initialize compass holder
        self._compass = None

        self._compass_show = False

        # Set grid event handler
        self._ax1.callbacks.connect('xlim_changed', self.update_compass)
        self._ax1.callbacks.connect('ylim_changed', self.update_compass)

    @auto_refresh
    def show_compass(self, color='red', length=0.1, corner=4, frame=True):
        '''
        Display a scalebar.

        Parameters
        ----------

        length : float, optional
            The length of the scalebar

        label : str, optional
            Label to place above the scalebar

        corner : int, optional
            Where to place the scalebar. Acceptable values are:, 'left', 'right', 'top', 'bottom', 'top left', 'top right', 'bottom left' (default), 'bottom right'

        frame : str, optional
            Whether to display a frame behind the scalebar (default is False)

        kwargs
            Additional keyword arguments can be used to control the appearance
            of the scalebar, which is made up of an instance of the matplotlib
            Rectangle class and a an instance of the Text class. For more
            information on available arguments, see

        `Rectangle <http://matplotlib.sourceforge.net/api/artist_api.html#matplotlib.patches.Rectangle>`_

        and

        `Text <http://matplotlib.sourceforge.net/api/artist_api.html#matplotlib.text.Text>`_`.

        In cases where the same argument exists for the two objects, the
        argument is passed to both the Text and Rectangle instance

        '''

        w = 2 * length

        pos = {1: (1 - w, 1 - w),
               2: (w, 1 - w),
               3: (w, w),
               4: (1 - w, w),
               5: (1 - w, 0.5),
               6: (w, 0.5),
               7: (1 - w, 0.5),
               8: (0.5, w),
               9: (0.5, 1 - w)}

        self._compass_position = pos[corner]
        self._compass_length = length
        self._compass_color = color
        self._compass = None
        self._compass_show = True

        self.update_compass()

    @auto_refresh
    def update_compass(self, *args, **kwargs):

        if not self._compass_show:
            return

        rx, ry = self._compass_position
        length = self._compass_length
        color = self._compass_color

        xmin, xmax = self._ax1.get_xlim()
        ymin, ymax = self._ax1.get_ylim()

        x0 = rx * (xmax - xmin) + xmin
        y0 = ry * (ymax - ymin) + ymin

        xw, yw = self.pixel2world(x0, y0)

        len_pix = length * (ymax - ymin)

        degrees_per_pixel = wcs_util.degperpix(self._wcs)

        len_deg = len_pix * degrees_per_pixel

        # Should really only do tiny displacement then magnify the vectors - important if there is curvature

        x1, y1 = self.world2pixel(xw + len_deg / np.cos(np.radians(yw)), yw)
        x2, y2 = self.world2pixel(xw, yw + len_deg)

        if self._compass:
            self._compass[0].remove()
            self._compass[1].remove()

        arrow1 = FancyArrowPatch(posA=(x0, y0), posB=(x1, y1), arrowstyle='-|>', mutation_scale=20., fc=color, ec=color, shrinkA=0., shrinkB=0.)
        arrow2 = FancyArrowPatch(posA=(x0, y0), posB=(x2, y2), arrowstyle='-|>', mutation_scale=20., fc=color, ec=color, shrinkA=0., shrinkB=0.)

        self._compass = (arrow1, arrow2)

        self._ax1.add_patch(arrow1)
        self._ax1.add_patch(arrow2)

    @auto_refresh
    def hide_compass(self):
        pass


class Scalebar(object):

    def __init__(self, parent):

        # Retrieve info from parent figure
        self._ax = parent._ax1
        self._wcs = parent._wcs
        self._figure = parent._figure

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

        # Initialize settings
        self._base_settings = {}
        self._scalebar_settings = {}
        self._label_settings = {}
        self._label_settings['fontproperties'] = FontProperties()

    # LAYOUT

    @auto_refresh
    def show(self, length, label=None, corner='bottom right', frame=False, borderpad=0.4, pad=0.5, **kwargs):
        '''
        Overlay a scale bar on the image.

        Parameters
        ----------

        length : float
            The length of the scalebar

        label : str, optional
            Label to place below the scalebar

        corner : int, optional
            Where to place the scalebar. Acceptable values are:, 'left',
            'right', 'top', 'bottom', 'top left', 'top right', 'bottom
            left' (default), 'bottom right'

        frame : str, optional
            Whether to display a frame behind the scalebar (default is False)

        kwargs
            Additional arguments are passed to the matplotlib Rectangle and
            Text classes. See the matplotlib documentation for more details.
            In cases where the same argument exists for the two objects, the
            argument is passed to both the Text and Rectangle instance.
        '''

        self._length = length
        self._base_settings['corner'] = corner
        self._base_settings['frame'] = frame
        self._base_settings['borderpad'] = borderpad
        self._base_settings['pad'] = pad

        degrees_per_pixel = wcs_util.degperpix(self._wcs)

        length = length / degrees_per_pixel

        try:
            self._scalebar.remove()
        except:
            pass

        if isinstance(corner, basestring):
            corner = corners[corner]

        self._scalebar = AnchoredSizeBar(self._ax.transData, length, label, corner, \
                              pad=pad, borderpad=borderpad, sep=5, frameon=frame)

        self._ax.add_artist(self._scalebar)

        self.set(**kwargs)

    @auto_refresh
    def _remove(self):
        self._scalebar.remove()

    @auto_refresh
    def hide(self):
        '''
        Hide the scalebar.
        '''
        try:
            self._scalebar.remove()
        except:
            pass

    @auto_refresh
    def set_length(self, length):
        '''
        Set the length of the scale bar.
        '''
        self.show(length, **self._base_settings)
        self._set_scalebar_properties(**self._scalebar_settings)
        self._set_label_properties(**self._scalebar_settings)

    @auto_refresh
    def set_label(self, label):
        '''
        Set the label of the scale bar.
        '''
        self._set_label_properties(text=label)

    @auto_refresh
    def set_corner(self, corner):
        '''
        Set where to place the scalebar.

        Acceptable values are 'left', 'right', 'top', 'bottom', 'top left',
        'top right', 'bottom left' (default), and 'bottom right'.
        '''
        self._base_settings['corner'] = corner
        self.show(self._length, **self._base_settings)
        self._set_scalebar_properties(**self._scalebar_settings)
        self._set_label_properties(**self._scalebar_settings)

    @auto_refresh
    def set_frame(self, frame):
        '''
        Set whether to display a frame around the scalebar.
        '''
        self._base_settings['frame'] = frame
        self.show(self._length, **self._base_settings)
        self._set_scalebar_properties(**self._scalebar_settings)
        self._set_label_properties(**self._scalebar_settings)

    # APPEARANCE

    @auto_refresh
    def set_linewidth(self, linewidth):
        '''
        Set the linewidth of the scalebar, in points.
        '''
        self._set_scalebar_properties(linewidth=linewidth)

    @auto_refresh
    def set_linestyle(self, linestyle):
        '''
        Set the linestyle of the scalebar.

        Should be one of 'solid', 'dashed', 'dashdot', or 'dotted'.
        '''
        self._set_scalebar_properties(linestyle=linestyle)

    @auto_refresh
    def set_alpha(self, alpha):
        '''
        Set the alpha value (transparency).

        This should be a floating point value between 0 and 1.
        '''
        self._set_scalebar_properties(alpha=alpha)
        self._set_label_properties(alpha=alpha)

    @auto_refresh
    def set_color(self, color):
        '''
        Set the label and scalebar color.
        '''
        self._set_scalebar_properties(color=color)
        self._set_label_properties(color=color)

    @auto_refresh
    def set_font(self, family=None, style=None, variant=None, stretch=None, weight=None, size=None, fontproperties=None):
        '''
        Set the font of the tick labels

        Parameters
        ----------

        common: family, style, variant, stretch, weight, size, fontproperties

        Notes
        -----

        Default values are set by matplotlib or previously set values if
        set_font has already been called. Global default values can be set by
        editing the matplotlibrc file.
        '''

        if family:
            self._label_settings['fontproperties'].set_family(family)

        if style:
            self._label_settings['fontproperties'].set_style(style)

        if variant:
            self._label_settings['fontproperties'].set_variant(variant)

        if stretch:
            self._label_settings['fontproperties'].set_stretch(stretch)

        if weight:
            self._label_settings['fontproperties'].set_weight(weight)

        if size:
            self._label_settings['fontproperties'].set_size(size)

        if fontproperties:
            self._label_settings['fontproperties'] = fontproperties

        self._set_label_properties(fontproperties=self._label_settings['fontproperties'])

    @auto_refresh
    def _set_label_properties(self, **kwargs):
        '''
        Modify the scalebar label properties.

        All arguments are passed to the matplotlib Text class. See the
        matplotlib documentation for more details.
        '''
        for kwarg in kwargs:
            self._label_settings[kwarg] = kwargs[kwarg]
        self._scalebar.txt_label.get_children()[0].set(**kwargs)

    @auto_refresh
    def _set_scalebar_properties(self, **kwargs):
        '''
        Modify the scalebar properties.

        All arguments are passed to the matplotlib Rectangle class. See the
        matplotlib documentation for more details.
        '''
        for kwarg in kwargs:
            self._scalebar_settings[kwarg] = kwargs[kwarg]
        self._scalebar.size_bar.get_children()[0].set(**kwargs)

    @auto_refresh
    def set(self, **kwargs):
        '''
        Modify the scalebar and scalebar properties.

        All arguments are passed to the matplotlib Rectangle and Text classes.
        See the matplotlib documentation for more details. In cases where the
        same argument exists for the two objects, the argument is passed to
        both the Text and Rectangle instance.
        '''
        for kwarg in kwargs:
            kwargs_single = {kwarg: kwargs[kwarg]}
            try:
                self._set_label_properties(**kwargs_single)
            except AttributeError:
                pass
            try:
                self._set_scalebar_properties(**kwargs_single)
            except AttributeError:
                pass

    # DEPRECATED

    @auto_refresh
    def set_font_family(self, family):
        warnings.warn("scalebar.set_font_family is deprecated - use scalebar.set_font instead", DeprecationWarning)
        self.set_font(family=family)

    @auto_refresh
    def set_font_weight(self, weight):
        warnings.warn("scalebar.set_font_weight is deprecated - use scalebar.set_font instead", DeprecationWarning)
        self.set_font(weight=weight)

    @auto_refresh
    def set_font_size(self, size):
        warnings.warn("scalebar.set_font_size is deprecated - use scalebar.set_font instead", DeprecationWarning)
        self.set_font(size=size)

    @auto_refresh
    def set_font_style(self, style):
        warnings.warn("scalebar.set_font_style is deprecated - use scalebar.set_font instead", DeprecationWarning)
        self.set_font(style=style)

# For backward-compatibility
ScaleBar = Scalebar


class Beam(object):

    def __init__(self, parent):

        # Retrieve info from parent figure
        self._figure = parent._figure
        self._header = parent._header
        self._ax = parent._ax1
        self._wcs = parent._wcs

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

        # Initialize settings
        self._base_settings = {}
        self._beam_settings = {}

    # LAYOUT

    @auto_refresh
    def show(self, major='BMAJ', minor='BMIN', \
        angle='BPA', corner='bottom left', frame=False, borderpad=0.4, pad=0.5, **kwargs):

        '''
        Display the beam shape and size for the primary image.

        By default, this method will search for the BMAJ, BMIN, and BPA
        keywords in the FITS header to set the major and minor axes and the
        position angle on the sky.

        Parameters
        ----------

        major : float, optional
            Major axis of the beam in degrees (overrides BMAJ if present)

        minor : float, optional
            Minor axis of the beam in degrees (overrides BMIN if present)

        angle : float, optional
            Position angle of the beam on the sky in degrees (overrides
            BPA if present) in the anticlockwise direction.

        corner : int, optional
            The beam location. Acceptable values are 'left', 'right',
            'top', 'bottom', 'top left', 'top right', 'bottom left'
            (default), and 'bottom right'.

        frame : str, optional
            Whether to display a frame behind the beam (default is False)

        kwargs
            Additional arguments are passed to the matplotlib Ellipse classe.
            See the matplotlib documentation for more details.
        '''

        if isinstance(major, basestring):
            major = self._header[major]

        if isinstance(minor, basestring):
            minor = self._header[minor]

        if isinstance(angle, basestring):
            angle = self._header[angle]

        degrees_per_pixel = wcs_util.degperpix(self._wcs)

        self._base_settings['minor'] = minor
        self._base_settings['major'] = major
        self._base_settings['angle'] = angle
        self._base_settings['corner'] = corner
        self._base_settings['frame'] = frame
        self._base_settings['borderpad'] = borderpad
        self._base_settings['pad'] = pad

        minor /= degrees_per_pixel
        major /= degrees_per_pixel

        try:
            self._beam.remove()
        except:
            pass

        if isinstance(corner, basestring):
            corner = corners[corner]

        self._beam = AnchoredEllipse(self._ax.transData, \
            width=minor, height=major, angle=angle, \
            loc=corner, pad=pad, borderpad=borderpad, frameon=frame)

        self._ax.add_artist(self._beam)

        self.set(**kwargs)

    @auto_refresh
    def _remove(self):
        self._beam.remove()

    @auto_refresh
    def hide(self):
        '''
        Hide the beam
        '''
        try:
            self._beam.remove()
        except:
            pass

    @auto_refresh
    def set_major(self, major):
        '''
        Set the major axis of the beam, in degrees.
        '''
        self._base_settings['major'] = major
        self.show(**self._base_settings)
        self.set(**self._beam_settings)

    @auto_refresh
    def set_minor(self, minor):
        '''
        Set the minor axis of the beam, in degrees.
        '''
        self._base_settings['minor'] = minor
        self.show(**self._base_settings)
        self.set(**self._beam_settings)

    @auto_refresh
    def set_angle(self, angle):
        '''
        Set the position angle of the beam on the sky, in degrees.
        '''
        self._base_settings['angle'] = angle
        self.show(**self._base_settings)
        self.set(**self._beam_settings)

    @auto_refresh
    def set_corner(self, corner):
        '''
        Set the beam location.

        Acceptable values are 'left', 'right', 'top', 'bottom', 'top left',
        'top right', 'bottom left' (default), and 'bottom right'.
        '''
        self._base_settings['corner'] = corner
        self.show(**self._base_settings)
        self.set(**self._beam_settings)

    @auto_refresh
    def set_frame(self, frame):
        '''
        Set whether to display a frame around the beam.
        '''
        self._base_settings['frame'] = frame
        self.show(**self._base_settings)
        self.set(**self._beam_settings)

    @auto_refresh
    def set_borderpad(self, borderpad):
        '''
        Set the amount of padding within the beam object, relative to the
        canvas size.
        '''
        self._base_settings['borderpad'] = borderpad
        self.show(**self._base_settings)
        self.set(**self._beam_settings)

    @auto_refresh
    def set_pad(self, pad):
        '''
        Set the amount of padding between the beam object and the image
        corner/edge, relative to the canvas size.
        '''
        self._base_settings['pad'] = pad
        self.show(**self._base_settings)
        self.set(**self._beam_settings)

    # APPEARANCE

    @auto_refresh
    def set_alpha(self, alpha):
        '''
        Set the alpha value (transparency).

        This should be a floating point value between 0 and 1.
        '''
        self.set(alpha=alpha)

    @auto_refresh
    def set_color(self, color):
        '''
        Set the beam color.
        '''
        self.set(color=color)

    @auto_refresh
    def set_edgecolor(self, edgecolor):
        '''
        Set the color for the edge of the beam.
        '''
        self.set(edgecolor=edgecolor)

    @auto_refresh
    def set_facecolor(self, facecolor):
        '''
        Set the color for the interior of the beam.
        '''
        self.set(facecolor=facecolor)

    @auto_refresh
    def set_linestyle(self, linestyle):
        '''
        Set the line style for the edge of the beam.

        This should be one of 'solid', 'dashed', 'dashdot', or 'dotted'.
        '''
        self.set(linestyle=linestyle)

    @auto_refresh
    def set_linewidth(self, linewidth):
        '''
        Set the line width for the edge of the beam, in points.
        '''
        self.set(linewidth=linewidth)

    @auto_refresh
    def set_hatch(self, hatch):
        '''
        Set the hatch pattern.

        This should be one of '/', '\', '|', '-', '+', 'x', 'o', 'O', '.', or
        '*'.
        '''
        self.set(hatch=hatch)

    @auto_refresh
    def set(self, **kwargs):
        '''
        Modify the beam properties. All arguments are passed to the matplotlib
        Ellipse classe. See the matplotlib documentation for more details.
        '''
        for kwarg in kwargs:
            self._beam_settings[kwarg] = kwargs[kwarg]
        self._beam.ellipse.set(**kwargs)

########NEW FILE########
__FILENAME__ = regions
from __future__ import absolute_import, print_function, division

from astropy import log

from .decorators import auto_refresh


class Regions:
    """
    Regions sub-class of APLpy

    Used for overplotting various shapes and annotations on APLpy
    fitsfigures

    Example:
    # DS9 region file called "test.reg"
    # (the coordinates are around l=28 in the Galactic Plane)
    # Filename: test.fits
    fk5
    box(18:42:48.262,-04:01:17.91,505.668",459.714",0) # color=red dash=1
    point(18:42:51.797,-03:59:44.82) # point=x color=red dash=1
    point(18:42:50.491,-04:03:09.39) # point=box color=red dash=1
    # vector(18:42:37.433,-04:02:10.77,107.966",115.201) vector=1 color=red dash=1
    ellipse(18:42:37.279,-04:02:11.92,26.4336",40.225",0) # color=red dash=1
    polygon(18:42:59.016,-03:58:22.06,18:42:58.219,-03:58:11.30,18:42:57.403,-03:58:35.86,18:42:58.094,-03:58:57.69,18:42:59.861,-03:58:41.60,18:42:59.707,-03:58:23.21) # color=red dash=1
    point(18:42:52.284,-04:00:02.80) # point=diamond color=red dash=1
    point(18:42:46.561,-03:58:01.57) # point=circle color=red dash=1
    point(18:42:42.615,-03:58:25.84) # point=cross color=red dash=1
    point(18:42:42.946,-04:01:44.74) # point=arrow color=red dash=1
    point(18:42:41.961,-03:57:26.16) # point=boxcircle color=red dash=1
    # text(18:42:41.961,-03:57:26.16) text={This is text} color=red

    Code:
    import aplpy
    import regions

    ff = aplpy.FITSFigure("test.fits")
    ff.show_grayscale()
    ff.show_regions('test.reg')

    """

    @auto_refresh
    def show_regions(self, region_file, layer=False, **kwargs):
        """
        Overplot regions as specified in the region file.

        Parameters
        ----------

        region_file: string or pyregion.ShapeList
            Path to a ds9 regions file or a ShapeList already read
            in by pyregion.

        layer: str, optional
            The name of the layer

        kwargs
            Additional keyword arguments, e.g. zorder, will be passed to the
            ds9 call and onto the patchcollections.
        """

        PC, TC = ds9(region_file, self._header, **kwargs)

        #ffpc = self._ax1.add_collection(PC)
        PC.add_to_axes(self._ax1)
        TC.add_to_axes(self._ax1)

        if layer:
            region_set_name = layer
        else:
            self._region_counter += 1
            region_set_name = 'region_set_' + str(self._region_counter)

        self._layers[region_set_name] = PC
        self._layers[region_set_name + "_txt"] = TC


def ds9(region_file, header, zorder=3, **kwargs):
    """
    Wrapper to return a PatchCollection given a ds9 region file
    and a fits header.

    zorder - defaults to 3 so that regions are on top of contours
    """

    try:
        import pyregion
    except:
        raise ImportError("The pyregion package is required to load region files")

    # read region file
    if isinstance(region_file, basestring):
        rr = pyregion.open(region_file)
    elif isinstance(region_file, pyregion.ShapeList):
        rr = region_file
    else:
        raise Exception("Invalid type for region_file: %s - should be string or pyregion.ShapeList" % type(region_file))

    # convert coordinates to image coordinates
    rrim = rr.as_imagecoord(header)

    # pyregion and aplpy both correct for the FITS standard origin=1,1
    # need to avoid double-correcting. Also, only some items in `coord_list`
    # are pixel coordinates, so which ones should be corrected depends on the
    # shape.
    for r in rrim:
        if r.name == 'polygon':
            correct = range(len(r.coord_list))
        elif r.name == 'line':
            correct = range(4)
        elif r.name in ['rotbox', 'box', 'ellipse', 'annulus', 'circle', 'panda', 'pie', 'epanda', 'text', 'point', 'vector']:
            correct = range(2)
        else:
            log.warning("Unknown region type '{0}' - please report to the developers")
            correct = range(2)
        for i in correct:
            r.coord_list[i] += 1

    if 'text_offset' in kwargs:
        text_offset = kwargs['text_offset']
        del kwargs['text_offset']
    else:
        text_offset = 5.0

    # grab the shapes to overplot
    pp, aa = rrim.get_mpl_patches_texts(text_offset=text_offset)

    PC = ArtistCollection(pp, **kwargs)  # preserves line style (dashed)
    TC = ArtistCollection(aa, **kwargs)
    PC.set_zorder(zorder)
    TC.set_zorder(zorder)

    return PC, TC


class ArtistCollection():
    """
    Matplotlib collections can't handle Text.
    This is a barebones collection for text objects
    that supports removing and making (in)visible
    """

    def __init__(self, artistlist):
        """
        Pass in a list of matplotlib.text.Text objects
        (or possibly any matplotlib Artist will work)
        """
        self.artistlist = artistlist

    def remove(self):
        for T in self.artistlist:
            T.remove()

    def add_to_axes(self, ax):
        for T in self.artistlist:
            ax.add_artist(T)

    def get_visible(self):
        visible = True
        for T in self.artistlist:
            if not T.get_visible():
                visible = False
        return visible

    def set_visible(self, visible=True):
        for T in self.artistlist:
            T.set_visible(visible)

    def set_zorder(self, zorder):
        for T in self.artistlist:
            T.set_zorder(zorder)

########NEW FILE########
__FILENAME__ = rgb
from __future__ import absolute_import, print_function, division

from distutils import version
import os
import warnings

import tempfile
import shutil

import numpy as np
from astropy import log
from astropy.io import fits

from . import image_util
from . import math_util


def _data_stretch(image, vmin=None, vmax=None, pmin=0.25, pmax=99.75, \
                  stretch='linear', vmid=None, exponent=2):

    min_auto = not math_util.isnumeric(vmin)
    max_auto = not math_util.isnumeric(vmax)

    if min_auto or max_auto:
        auto_v = image_util.percentile_function(image)
        vmin_auto, vmax_auto = auto_v(pmin), auto_v(pmax)

    if min_auto:
        log.info("vmin = %10.3e (auto)" % vmin_auto)
        vmin = vmin_auto
    else:
        log.info("vmin = %10.3e" % vmin)

    if max_auto:
        log.info("vmax = %10.3e (auto)" % vmax_auto)
        vmax = vmax_auto
    else:
        log.info("vmax = %10.3e" % vmax)

    image = (image - vmin) / (vmax - vmin)

    data = image_util.stretch(image, stretch, exponent=exponent, midpoint=vmid)

    data = np.nan_to_num(data)
    data = np.clip(data * 255., 0., 255.)

    return data.astype(np.uint8)


def make_rgb_image(data, output, indices=(0, 1, 2), \
                   vmin_r=None, vmax_r=None, pmin_r=0.25, pmax_r=99.75, \
                   stretch_r='linear', vmid_r=None, exponent_r=2, \
                   vmin_g=None, vmax_g=None, pmin_g=0.25, pmax_g=99.75, \
                   stretch_g='linear', vmid_g=None, exponent_g=2, \
                   vmin_b=None, vmax_b=None, pmin_b=0.25, pmax_b=99.75, \
                   stretch_b='linear', vmid_b=None, exponent_b=2, \
                   make_nans_transparent=False, \
                   embed_avm_tags=True):
    '''
    Make an RGB image from a FITS RGB cube or from three FITS files.

    Parameters
    ----------

    data : str or tuple or list
        If a string, this is the filename of an RGB FITS cube. If a tuple
        or list, this should give the filename of three files to use for
        the red, green, and blue channel.

    output : str
        The output filename. The image type (e.g. PNG, JPEG, TIFF, ...)
        will be determined from the extension. Any image type supported by
        the Python Imaging Library can be used.

    indices : tuple, optional
        If data is the filename of a FITS cube, these indices are the
        positions in the third dimension to use for red, green, and
        blue respectively. The default is to use the first three
        indices.

    vmin_r, vmin_g, vmin_b : float, optional
        Minimum pixel value to use for the red, green, and blue channels.
        If set to None for a given channel, the minimum pixel value for
        that channel is determined using the corresponding pmin_x argument
        (default).

    vmax_r, vmax_g, vmax_b : float, optional
        Maximum pixel value to use for the red, green, and blue channels.
        If set to None for a given channel, the maximum pixel value for
        that channel is determined using the corresponding pmax_x argument
        (default).

    pmin_r, pmin_r, pmin_g : float, optional
        Percentile values used to determine for a given channel the
        minimum pixel value to use for that channel if the corresponding
        vmin_x is set to None. The default is 0.25% for all channels.

    pmax_r, pmax_g, pmax_b : float, optional
        Percentile values used to determine for a given channel the
        maximum pixel value to use for that channel if the corresponding
        vmax_x is set to None. The default is 99.75% for all channels.

    stretch_r, stretch_g, stretch_b : { 'linear', 'log', 'sqrt', 'arcsinh', 'power' }
        The stretch function to use for the different channels.

    vmid_r, vmid_g, vmid_b : float, optional
        Baseline values used for the log and arcsinh stretches. If
        set to None, this is set to zero for log stretches and to
        vmin - (vmax - vmin) / 30. for arcsinh stretches

    exponent_r, exponent_g, exponent_b : float, optional
        If stretch_x is set to 'power', this is the exponent to use.

    make_nans_transparent : bool, optional
        If set AND output is png, will add an alpha layer that sets pixels 
        containing a NaN to transparent.

    embed_avm_tags : bool, optional
        Whether to embed AVM tags inside the image - this can only be done for
        JPEG and PNG files, and only if PyAVM is installed.
    '''

    try:
        from PIL import Image
    except ImportError:
        try:
            import Image
        except ImportError:
            raise ImportError("The Python Imaging Library (PIL) is required to make an RGB image")

    if isinstance(data, basestring):

        image = fits.getdata(data)
        image_r = image[indices[0], :, :]
        image_g = image[indices[1], :, :]
        image_b = image[indices[2], :, :]

        # Read in header
        header = fits.getheader(data)

        # Remove information about third dimension
        header['NAXIS'] = 2
        for key in ['NAXIS', 'CTYPE', 'CRPIX', 'CRVAL', 'CUNIT', 'CDELT', 'CROTA']:
            for coord in range(3, 6):
                name = key + str(coord)
                if name in header:
                    header.__delitem__(name)

    elif (type(data) == list or type(data) == tuple) and len(data) == 3:

        filename_r, filename_g, filename_b = data
        image_r = fits.getdata(filename_r)
        image_g = fits.getdata(filename_g)
        image_b = fits.getdata(filename_b)

        # Read in header
        header = fits.getheader(filename_r)

    else:
        raise Exception("data should either be the filename of a FITS cube or a list/tuple of three images")

    # are we making a transparent layer?
    do_alpha = make_nans_transparent and output.lower().endswith('.png')

    if do_alpha:
        log.info("Making alpha layer")

        # initialize alpha layer
        image_alpha = np.empty_like(image_r, dtype=np.uint8)
        image_alpha[:] = 255

        # look for nans in images
        for im in [image_r, image_g, image_b]:
            image_alpha[np.isnan(im)] = 0

    log.info("Red:")
    image_r = Image.fromarray(_data_stretch(image_r, \
                                            vmin=vmin_r, vmax=vmax_r, \
                                            pmin=pmin_r, pmax=pmax_r, \
                                            stretch=stretch_r, \
                                            vmid=vmid_r, \
                                            exponent=exponent_r))

    log.info("Green:")
    image_g = Image.fromarray(_data_stretch(image_g, \
                                            vmin=vmin_g, vmax=vmax_g, \
                                            pmin=pmin_g, pmax=pmax_g, \
                                            stretch=stretch_g, \
                                            vmid=vmid_g, \
                                            exponent=exponent_g))

    log.info("Blue:")
    image_b = Image.fromarray(_data_stretch(image_b, \
                                            vmin=vmin_b, vmax=vmax_b, \
                                            pmin=pmin_b, pmax=pmax_b, \
                                            stretch=stretch_b, \
                                            vmid=vmid_b, \
                                            exponent=exponent_b))

    img = Image.merge("RGB", (image_r, image_g, image_b))

    if do_alpha:
        # convert to RGBA and add alpha layer
        image_alpha = Image.fromarray(image_alpha)
        img.convert("RGBA")
        img.putalpha(image_alpha)

    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    img.save(output)

    if embed_avm_tags:

        try:
            import pyavm
        except ImportError:
            warnings.warn("PyAVM 0.9.1 or later is not installed, so AVM tags will not be embedded in RGB image")
            return

        if version.LooseVersion(pyavm.__version__) < version.LooseVersion('0.9.1'):
            warnings.warn("PyAVM 0.9.1 or later is not installed, so AVM tags will not be embedded in RGB image")
            return

        from pyavm import AVM

        if output.lower().endswith(('.jpg', '.jpeg', '.png')):
            avm = AVM.from_header(header)
            avm.embed(output, output)
        else:
            warnings.warn("AVM tags will not be embedded in RGB image, as only JPEG and PNG files are supported")


def make_rgb_cube(files, output, north=False, system=None, equinox=None):
    '''
    Make an RGB data cube from a list of three FITS images.

    This method can read in three FITS files with different
    projections/sizes/resolutions and uses Montage to reproject
    them all to the same projection.

    Two files are produced by this function. The first is a three-dimensional
    FITS cube with a filename give by `output`, where the third dimension
    contains the different channels. The second is a two-dimensional FITS
    image with a filename given by `output` with a `_2d` suffix. This file
    contains the mean of the different channels, and is required as input to
    FITSFigure if show_rgb is subsequently used to show a color image
    generated from the FITS cube (to provide the correct WCS information to
    FITSFigure).

    Parameters
    ----------

    files : tuple or list
       A list of the filenames of three FITS filename to reproject.
       The order is red, green, blue.

    output : str
       The filename of the output RGB FITS cube.

    north : bool, optional
       By default, the FITS header generated by Montage represents the
       best fit to the images, often resulting in a slight rotation. If
       you want north to be straight up in your final mosaic, you should
       use this option.

    system : str, optional
       Specifies the system for the header (default is EQUJ).
       Possible values are: EQUJ EQUB ECLJ ECLB GAL SGAL

    equinox : str, optional
       If a coordinate system is specified, the equinox can also be given
       in the form YYYY. Default is J2000.
    '''

    # Check whether the Python montage module is installed. The Python module
    # checks itself whether the Montage command-line tools are available, and
    # if they are not then importing the Python module will fail.
    try:
        import montage_wrapper as montage
    except ImportError:
        raise Exception("Both the Montage command-line tools and the"
                        " montage-wrapper Python module are required"
                        " for this function")

    # Check that input files exist
    for f in files:
        if not os.path.exists(f):
            raise Exception("File does not exist : " + f)

    # Create work directory
    work_dir = tempfile.mkdtemp()

    raw_dir = '%s/raw' % work_dir
    final_dir = '%s/final' % work_dir

    images_raw_tbl = '%s/images_raw.tbl' % work_dir
    header_hdr = '%s/header.hdr' % work_dir

    # Create raw and final directory in work directory
    os.mkdir(raw_dir)
    os.mkdir(final_dir)

    # Create symbolic links to input files
    for i, f in enumerate(files):
        os.symlink(os.path.abspath(f), '%s/image_%i.fits' % (raw_dir, i))

    # List files and create optimal header
    montage.mImgtbl(raw_dir, images_raw_tbl, corners=True)
    montage.mMakeHdr(images_raw_tbl, header_hdr, north_aligned=north, system=system, equinox=equinox)

    # Read header in with astropy.io.fits
    header = fits.Header.fromtextfile(header_hdr)

    # Find image dimensions
    nx = int(header['NAXIS1'])
    ny = int(header['NAXIS2'])

    # Generate emtpy datacube
    image_cube = np.zeros((len(files), ny, nx), dtype=np.float32)

    # Loop through files
    for i in range(len(files)):

        # Reproject channel to optimal header
        montage.reproject('%s/image_%i.fits' % (raw_dir, i),
                          '%s/image_%i.fits' % (final_dir, i),
                          header=header_hdr, exact_size=True, bitpix=-32)

        # Read in and add to datacube
        image_cube[i, :, :] = fits.getdata('%s/image_%i.fits' % (final_dir, i))

    # Write out final cube
    fits.writeto(output, image_cube, header, clobber=True)

    # Write out collapsed version of cube
    fits.writeto(output.replace('.fits', '_2d.fits'), \
                   np.mean(image_cube, axis=0), header, clobber=True)

    # Remove work directory
    shutil.rmtree(work_dir)

########NEW FILE########
__FILENAME__ = scalar_util
from __future__ import absolute_import, print_function, division

import numpy as np

from . import math_util


def smart_round_angle_decimal(x, latitude=False):

    x = np.log10(x)
    e = np.floor(x)
    x -= e
    x = 10. ** x
    divisors_10 = math_util.divisors(10)
    x = math_util.closest(divisors_10, x)
    x = x * 10. ** e

    return x


def _get_label_precision(format):

    if format[0] == "%":
        if "i" in format:
            return 1
        elif "f" in format:
            return 10. ** (-len((format % 1).split('.')[1]))
        elif "e" in format:
            return None  # need to figure this out
        else:
            return None  # need to figure this out
    elif "." in format:
        return 10 ** (-len(format.split('.')[1]))
    else:
        return 1


class InconsistentSpacing(Exception):
    pass


def _check_format_spacing_consistency(format, spacing):
    '''
    Check whether the format can correctly show labels with the specified
    spacing.

    For example, if the tick spacing is set to 1 arcsecond, but the format is
    set to dd:mm, then the labels cannot be correctly shown. Similarly, if the
    spacing is set to 1/1000 of a degree, or 3.6", then a format of dd:mm:ss
    will cause rounding errors, because the spacing includes fractional
    arcseconds.

    This function will raise a warning if the format and spacing are
    inconsistent.
    '''

    label_spacing = _get_label_precision(format)

    if label_spacing is None:
        return  # can't determine minimum spacing, so can't check

    if spacing % label_spacing != 0.:
        raise InconsistentSpacing('Label format and tick spacing are inconsistent. Make sure that the tick spacing is a multiple of the smallest angle that can be represented by the specified format (currently %s). For example, if the format is dd:mm:ss.s, then the tick spacing has to be a multiple of 0.1". Similarly, if the format is hh:mm:ss, then the tick spacing has to be a multiple of 15". If you got this error as a result of interactively zooming in to a small region, this means that the default display format for the labels is not accurate enough, so you will need to increase the format precision.' % format)

########NEW FILE########
__FILENAME__ = slicer
from __future__ import absolute_import, print_function, division


def slice_hypercube(data, header, dimensions=[0, 1], slices=[]):
    '''
    Extract a slice from an n-dimensional HDU data/header pair, and return the
    new data (without changing the header).
    '''

    if type(slices) == int:
        slices = (slices, )
    else:
        slices = slices[:]

    shape = data.shape

    if len(shape) < 2:

        raise Exception("FITS file does not have enough dimensions")

    elif len(shape) == 2:

        if dimensions[1] < dimensions[0]:
            data = data.transpose()

        return data

    else:

        if slices:

            if dimensions[0] < dimensions[1]:
                slices.insert(dimensions[0], slice(None, None, None))
                slices.insert(dimensions[1], slice(None, None, None))
            else:
                slices.insert(dimensions[1], slice(None, None, None))
                slices.insert(dimensions[0], slice(None, None, None))

            if type(slices) == list:
                slices = tuple(slices)

            data = data[slices[::-1]]

            if dimensions[1] < dimensions[0]:
                data = data.transpose()

        else:

            message = '''
    Attempted to read in %i-dimensional FITS cube, but
    dimensions and slices were not specified. Please specify these
    using the dimensions= and slices= argument. The cube dimensions
    are:\n\n''' % len(shape)

            for i in range(1, len(shape) + 1):

                message += " " * 10
                message += " %i %s %i\n" % (i - 1,
                                            header["CTYPE%i" % i],
                                            header["NAXIS%i" % i])

            raise Exception(message)

        return data

########NEW FILE########
__FILENAME__ = helpers
import string
import random
import os

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


def random_id():
    return ''.join(random.sample(string.ascii_letters + string.digits, 16))


def generate_header(header_file):

    # Read in header
    header = fits.Header()
    header.fromTxtFile(header_file)

    return header


def generate_data(header_file):

    # Read in header
    header = generate_header(header_file)

    # Find shape of array
    shape = []
    for i in range(header['NAXIS']):
        shape.append(header['NAXIS%i' % (i + 1)])

    # Generate data array
    data = np.zeros(shape[::-1])

    return data


def generate_hdu(header_file):

    # Read in header
    header = generate_header(header_file)

    # Generate data array
    data = generate_data(header_file)

    # Generate primary HDU
    hdu = fits.PrimaryHDU(data=data, header=header)

    return hdu


def generate_wcs(header_file):

    # Read in header
    header = generate_header(header_file)

    # Compute WCS object
    wcs = WCS(header)

    return wcs


def generate_file(header_file, directory):

    # Generate HDU object
    hdu = generate_hdu(header_file)

    # Write out to a temporary file in the specified directory
    filename = os.path.join(directory, random_id() + '.fits')
    hdu.writeto(filename)

    return filename

########NEW FILE########
__FILENAME__ = test_axis_labels
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure


def test_axis_labels_show_hide():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.axis_labels.hide()
    f.axis_labels.show()
    f.axis_labels.hide_x()
    f.axis_labels.show_x()
    f.axis_labels.hide_y()
    f.axis_labels.show_y()
    f.close()


def test_axis_labels_text():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.axis_labels.set_xtext('x')
    f.axis_labels.set_ytext('y')
    f.close()


def test_axis_labels_pad():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.axis_labels.set_xpad(-1.)
    f.axis_labels.set_ypad(0.5)
    f.close()


def test_axis_labels_position():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.axis_labels.set_xposition('top')
    f.axis_labels.set_xposition('bottom')
    f.axis_labels.set_yposition('right')
    f.axis_labels.set_yposition('left')
    f.close()


def test_axis_labels_position_invalid():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    with pytest.raises(ValueError):
        f.axis_labels.set_xposition('right')
    with pytest.raises(ValueError):
        f.axis_labels.set_xposition('left')
    with pytest.raises(ValueError):
        f.axis_labels.set_yposition('top')
    with pytest.raises(ValueError):
        f.axis_labels.set_yposition('bottom')
    f.close()


def test_axis_labels_font():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.axis_labels.set_font(size='small', weight='bold', stretch='normal',
                           family='serif', style='normal', variant='normal')
    f.close()

########NEW FILE########
__FILENAME__ = test_beam
import matplotlib
matplotlib.use('Agg')

import numpy as np

from .. import FITSFigure


def test_beam_addremove():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.remove_beam()
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.remove_beam()
    f.close()


def test_beam_showhide():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.hide()
    f.beam.show(major=0.1, minor=0.04, angle=10.)
    f.close()


def test_beam_major():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_major(0.5)
    f.beam.set_major(1.0)
    f.close()


def test_beam_minor():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_minor(0.05)
    f.beam.set_minor(0.08)
    f.close()


def test_beam_angle():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_angle(0.)
    f.beam.set_angle(55.)
    f.close()


def test_beam_corner():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    for corner in ['top', 'bottom', 'left', 'right', 'top left', 'top right',
                   'bottom left', 'bottom right']:
        f.beam.set_corner(corner)
    f.close()


def test_beam_frame():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_frame(True)
    f.beam.set_frame(False)
    f.close()


def test_beam_borderpad():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_borderpad(0.1)
    f.beam.set_borderpad(0.3)
    f.close()


def test_beam_pad():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_pad(0.1)
    f.beam.set_pad(0.3)
    f.close()


def test_beam_alpha():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_alpha(0.1)
    f.beam.set_alpha(0.2)
    f.beam.set_alpha(0.5)
    f.close()


def test_beam_color():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_color('black')
    f.beam.set_color('#003344')
    f.beam.set_color((1.0, 0.4, 0.3))
    f.close()


def test_beam_facecolor():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_facecolor('black')
    f.beam.set_facecolor('#003344')
    f.beam.set_facecolor((1.0, 0.4, 0.3))
    f.close()


def test_beam_edgecolor():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_edgecolor('black')
    f.beam.set_edgecolor('#003344')
    f.beam.set_edgecolor((1.0, 0.4, 0.3))
    f.close()


def test_beam_linestyle():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_linestyle('solid')
    f.beam.set_linestyle('dotted')
    f.beam.set_linestyle('dashed')
    f.close()


def test_beam_linewidth():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    f.beam.set_linewidth(0)
    f.beam.set_linewidth(1)
    f.beam.set_linewidth(5)
    f.close()


def test_beam_hatch():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_beam(major=0.1, minor=0.04, angle=10.)
    for hatch in ['/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*']:
        f.beam.set_hatch(hatch)
    f.close()

########NEW FILE########
__FILENAME__ = test_colorbar
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure


def test_colorbar_invalid():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    with pytest.raises(Exception):
        f.add_colorbar()  # no grayscale/colorscale was shown


def test_colorbar_addremove():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_colorbar()
    f.remove_colorbar()
    f.add_colorbar()
    f.close()


def test_colorbar_showhide():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_colorbar()
    f.colorbar.hide()
    f.colorbar.show()
    f.close()


def test_colorbar_location():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_colorbar()
    f.colorbar.set_location('top')
    f.colorbar.set_location('bottom')
    f.colorbar.set_location('left')
    f.colorbar.set_location('right')
    f.close()


def test_colorbar_width():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_colorbar()
    f.colorbar.set_width(0.1)
    f.colorbar.set_width(0.2)
    f.colorbar.set_width(0.5)
    f.close()


def test_colorbar_pad():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_colorbar()
    f.colorbar.set_pad(0.1)
    f.colorbar.set_pad(0.2)
    f.colorbar.set_pad(0.5)
    f.close()


def test_colorbar_font():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_colorbar()
    f.colorbar.set_font(size='small', weight='bold', stretch='normal',
                        family='serif', style='normal', variant='normal')
    f.close()


def test_colorbar_axis_label():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.add_colorbar()
    f.colorbar.set_axis_label_text('Flux (MJy/sr)')
    f.colorbar.set_axis_label_rotation(45.)
    f.colorbar.set_axis_label_font(size='small', weight='bold', stretch='normal',
                                   family='serif', style='normal', variant='normal')
    f.colorbar.set_axis_label_pad(5.)
    f.close()
########NEW FILE########
__FILENAME__ = test_contour
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure

# Test simple contour generation with Numpy example


@pytest.mark.parametrize(('filled'), [True, False])
def test_numpy_contour(filled):
    data = np.arange(256).reshape((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.show_contour(data, levels=np.linspace(1., 254., 10), filled=filled)
    f.close()

########NEW FILE########
__FILENAME__ = test_convolve
import os

import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest
from astropy.io import fits
from astropy.wcs import WCS as AstropyWCS

from .helpers import generate_file, generate_hdu, generate_wcs
from .. import FITSFigure


def test_convolve_default():
    data = np.random.random((16, 16))
    hdu = fits.PrimaryHDU(data)
    f = FITSFigure(hdu)
    f.show_grayscale(smooth=3)
    f.close()


def test_convolve_gauss():
    data = np.random.random((16, 16))
    hdu = fits.PrimaryHDU(data)
    f = FITSFigure(hdu)
    f.show_grayscale(kernel='gauss', smooth=3)
    f.close()


def test_convolve_box():
    data = np.random.random((16, 16))
    hdu = fits.PrimaryHDU(data)
    f = FITSFigure(hdu)
    f.show_grayscale(kernel='box', smooth=3)
    f.close()


def test_convolve_custom():
    data = np.random.random((16, 16))
    hdu = fits.PrimaryHDU(data)
    f = FITSFigure(hdu)
    f.show_grayscale(kernel=np.ones((3,3)))
    f.close()


########NEW FILE########
__FILENAME__ = test_downsample
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure

# Test simple contour generation with Numpy example


def test_numpy_downsample():
    data = np.arange(256).reshape((16, 16))
    f = FITSFigure(data, downsample=2)
    f.show_grayscale()
    f.close()

########NEW FILE########
__FILENAME__ = test_frame
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure


def test_frame_linewidth():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.frame.set_linewidth(0)
    f.frame.set_linewidth(1)
    f.frame.set_linewidth(10)
    f.close()


def test_frame_color():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.frame.set_color('black')
    f.frame.set_color('#003344')
    f.frame.set_color((1.0, 0.4, 0.3))
    f.close()

########NEW FILE########
__FILENAME__ = test_grid
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure


def test_grid_addremove():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_grid()
    f.remove_grid()
    f.add_grid()
    f.close()


def test_grid_showhide():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_grid()
    f.grid.hide()
    f.grid.show()
    f.close()


def test_grid_spacing():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_grid()
    f.grid.set_xspacing(1.)
    f.grid.set_xspacing('tick')
    with pytest.raises(ValueError):
        f.grid.set_xspacing('auto')
    f.grid.set_yspacing(2.)
    f.grid.set_yspacing('tick')
    with pytest.raises(ValueError):
        f.grid.set_yspacing('auto')
    f.close()


def test_grid_color():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_grid()
    f.grid.set_color('black')
    f.grid.set_color('#003344')
    f.grid.set_color((1.0, 0.4, 0.3))
    f.close()


def test_grid_alpha():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_grid()
    f.grid.set_alpha(0.0)
    f.grid.set_alpha(0.3)
    f.grid.set_alpha(1.0)
    f.close()


def test_grid_linestyle():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_grid()
    f.grid.set_linestyle('solid')
    f.grid.set_linestyle('dashed')
    f.grid.set_linestyle('dotted')
    f.close()


def test_grid_linewidth():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_grid()
    f.grid.set_linewidth(0)
    f.grid.set_linewidth(2)
    f.grid.set_linewidth(5)
    f.close()

########NEW FILE########
__FILENAME__ = test_init_cube
import os

import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest
from astropy.io import fits
import astropy.utils.exceptions as aue

from .helpers import generate_file, generate_hdu, generate_wcs
from .. import FITSFigure

# The tests in this file check that the initialization and basic plotting do
# not crash for FITS files with 3+ dimensions. No reference images are
# required here.

header_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/3d_fits')

HEADERS = [os.path.join(header_dir, 'cube.hdr')]

REFERENCE = os.path.join(header_dir, 'cube.hdr')

VALID_DIMENSIONS = [(0, 1), (1, 0), (0, 2), (2, 0), (1, 2), (2, 1)]
INVALID_DIMENSIONS = [None, (1,), (0, 3), (-4, 2), (1, 1), (2, 2), (3, 3),
                      (1, 2, 3), (3, 5, 3, 2)]


# Test initialization through a filename
def test_file_init(tmpdir):
    filename = generate_file(REFERENCE, str(tmpdir))
    f = FITSFigure(filename, slices=[5])
    f.show_grayscale()
    f.close()


# Test initialization through an HDU object
def test_hdu_init():
    hdu = generate_hdu(REFERENCE)
    f = FITSFigure(hdu, slices=[5])
    f.show_grayscale()
    f.close()


# Test initialization through a WCS object (should not work)
def test_wcs_init():
    wcs = generate_wcs(REFERENCE)
    exc = ValueError if hasattr(wcs,'naxis1') else aue.AstropyDeprecationWarning
    with pytest.raises(exc):
        FITSFigure(wcs, slices=[5])


# Test initialization through an HDU object (no WCS)
def test_hdu_nowcs_init():
    data = np.zeros((16, 16, 16))
    hdu = fits.PrimaryHDU(data)
    f = FITSFigure(hdu, slices=[5])
    f.show_grayscale()
    f.close()


# Test initalization through a Numpy array (no WCS)
def test_numpy_nowcs_init():
    data = np.zeros((16, 16, 16))
    f = FITSFigure(data, slices=[5])
    f.show_grayscale()
    f.close()


# Test that initialization without specifying slices raises an exception for a
# true 3D cube
def test_hdu_noslices():
    hdu = generate_hdu(REFERENCE)
    with pytest.raises(Exception):
        FITSFigure(hdu)

# Test that initialization without specifying slices does *not* raise an
# exception if the remaining dimensions have size 1.
def test_hdu_noslices_2d():
    data = np.zeros((1, 16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.close()

# Now check initialization with valid and invalid dimensions. We just need to
# tes with HDU objects since we already tested that reading from files is ok.


# Test initialization with valid dimensions
@pytest.mark.parametrize(('dimensions'), VALID_DIMENSIONS)
def test_init_dimensions_valid(dimensions):
    hdu = generate_hdu(REFERENCE)
    f = FITSFigure(hdu, dimensions=dimensions, slices=[5])
    f.show_grayscale()
    f.close()


# Test initialization with invalid dimensions
@pytest.mark.parametrize(('dimensions'), INVALID_DIMENSIONS)
def test_init_dimensions_invalid(dimensions):
    hdu = generate_hdu(REFERENCE)
    with pytest.raises(ValueError):
        FITSFigure(hdu, dimensions=dimensions, slices=[5])


# Now check initialization of different WCS projections, and we check only
# valid dimensions

valid_parameters = []
for h in HEADERS:
    for d in VALID_DIMENSIONS:
        valid_parameters.append((h, d))


@pytest.mark.parametrize(('header', 'dimensions'), valid_parameters)
def test_init_extensive_wcs(tmpdir, header, dimensions):
    filename = generate_file(header, str(tmpdir))
    f = FITSFigure(filename, dimensions=dimensions, slices=[5])
    f.show_grayscale()
    f.close()

# Test that recenter works for cube slices
def test_hdu_nowcs_init():
    data = np.zeros((16, 16, 16))
    hdu = fits.PrimaryHDU(data)
    f = FITSFigure(hdu, slices=[5])
    f.show_grayscale()
    f.recenter(5., 5., width=3., height=3.)
    f.close()

########NEW FILE########
__FILENAME__ = test_init_image
import os

import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest
from astropy.io import fits
from astropy.wcs import WCS as AstropyWCS
import astropy.utils.exceptions as aue

from .helpers import generate_file, generate_hdu, generate_wcs
from .. import FITSFigure

# The tests in this file check that the initialization and basic plotting do
# not crash for FITS files with 2 dimensions. No reference images are
# required here.

header_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/2d_fits')

HEADERS = [os.path.join(header_dir, '1904-66_AIR.hdr'),
           os.path.join(header_dir, '1904-66_AIT.hdr'),
           os.path.join(header_dir, '1904-66_ARC.hdr'),
           os.path.join(header_dir, '1904-66_AZP.hdr'),
           os.path.join(header_dir, '1904-66_BON.hdr'),
           os.path.join(header_dir, '1904-66_CAR.hdr'),
           os.path.join(header_dir, '1904-66_CEA.hdr'),
           os.path.join(header_dir, '1904-66_COD.hdr'),
           os.path.join(header_dir, '1904-66_COE.hdr'),
           os.path.join(header_dir, '1904-66_COO.hdr'),
           os.path.join(header_dir, '1904-66_COP.hdr'),
           os.path.join(header_dir, '1904-66_CSC.hdr'),
           os.path.join(header_dir, '1904-66_CYP.hdr'),
           os.path.join(header_dir, '1904-66_HPX.hdr'),
           os.path.join(header_dir, '1904-66_MER.hdr'),
           os.path.join(header_dir, '1904-66_MOL.hdr'),
           os.path.join(header_dir, '1904-66_NCP.hdr'),
           os.path.join(header_dir, '1904-66_PAR.hdr'),
           os.path.join(header_dir, '1904-66_PCO.hdr'),
           os.path.join(header_dir, '1904-66_QSC.hdr'),
           os.path.join(header_dir, '1904-66_SFL.hdr'),
           os.path.join(header_dir, '1904-66_SIN.hdr'),
           os.path.join(header_dir, '1904-66_STG.hdr'),
           os.path.join(header_dir, '1904-66_SZP.hdr'),
           os.path.join(header_dir, '1904-66_TAN.hdr'),
           os.path.join(header_dir, '1904-66_TSC.hdr'),
           os.path.join(header_dir, '1904-66_ZEA.hdr'),
           os.path.join(header_dir, '1904-66_ZPN.hdr')]

REFERENCE = os.path.join(header_dir, '1904-66_TAN.hdr')

CAR_REFERENCE = os.path.join(header_dir, '1904-66_CAR.hdr')

VALID_DIMENSIONS = [(0, 1), (1, 0)]
INVALID_DIMENSIONS = [None, (1,), (0, 2), (-4, 2), (1, 1), (2, 2), (1, 2, 3)]


# Test initialization through a filename
def test_file_init(tmpdir):
    filename = generate_file(REFERENCE, str(tmpdir))
    f = FITSFigure(filename)
    f.show_grayscale()
    f.close()


# Test initialization through an HDU object
def test_hdu_init():
    hdu = generate_hdu(REFERENCE)
    f = FITSFigure(hdu)
    f.show_grayscale()
    f.close()


# Test initialization through a WCS object
def test_wcs_init():
    wcs = generate_wcs(REFERENCE)
    if hasattr(wcs,'naxis1'):
        f = FITSFigure(wcs)
        f.show_grayscale()
        f.close()
    else:
        with pytest.raises(aue.AstropyDeprecationWarning):
            f = FITSFigure(wcs)


# Test initialization through a WCS object with wcs.to_header() as a go-between
# specifically for testing the cd -> pc -> cd hack, and has particular importance
# for AVM-generated headers
def test_wcs_toheader_init():
    wcs = generate_wcs(REFERENCE)
    header_ = fits.Header.fromtextfile(REFERENCE)
    header = wcs.to_header()
    wcs2 = AstropyWCS(header)
    wcs2.naxis1 = wcs.naxis1 = header_['NAXIS1']
    wcs2.naxis2 = wcs.naxis2 = header_['NAXIS2']
    f = FITSFigure(wcs2)
    f.show_grayscale()
    f.add_grid()
    f.close()


# Test initialization through an HDU object (no WCS)
def test_hdu_nowcs_init():
    data = np.zeros((16, 16))
    hdu = fits.PrimaryHDU(data)
    f = FITSFigure(hdu)
    f.show_grayscale()
    f.close()


# Test initalization through a Numpy array (no WCS)
def test_numpy_nowcs_init():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    f.close()


# Now check initialization with valid and invalid dimensions. We just need to
# tes with HDU objects since we already tested that reading from files is ok.

# Test initialization with valid dimensions
@pytest.mark.parametrize(('dimensions'), VALID_DIMENSIONS)
def test_init_dimensions_valid(dimensions):
    hdu = generate_hdu(REFERENCE)
    f = FITSFigure(hdu, dimensions=dimensions)
    f.show_grayscale()
    f.close()

# Test initialization with invalid dimensions


@pytest.mark.parametrize(('dimensions'), INVALID_DIMENSIONS)
def test_init_dimensions_invalid(dimensions):
    hdu = generate_hdu(REFERENCE)
    with pytest.raises(ValueError):
        FITSFigure(hdu, dimensions=dimensions)

# Now check initialization of different WCS projections, and we check only
# valid dimensions

valid_parameters = []
for h in HEADERS:
    for d in VALID_DIMENSIONS:
        valid_parameters.append((h, d))


@pytest.mark.parametrize(('header', 'dimensions'), valid_parameters)
def test_init_extensive_wcs(header, dimensions):
    hdu = generate_hdu(header)
    if 'CAR' in header:
        f = FITSFigure(hdu, dimensions=dimensions, convention='calabretta')
    else:
        f = FITSFigure(hdu, dimensions=dimensions)
    f.show_grayscale()
    f.add_grid()
    f.close()

# Check that for CAR projections, an exception is raised if no convention is specified


@pytest.mark.parametrize(('dimensions'), VALID_DIMENSIONS)
def test_init_car_invalid(dimensions):
    hdu = generate_hdu(CAR_REFERENCE)
    with pytest.raises(Exception):
        FITSFigure(hdu, dimensions=dimensions)

# Check that images containing only NaN or Inf values don't crash FITSFigure
def test_init_only_naninf():
    data = np.ones((10,10)) * np.nan
    data[::2,::2] = np.inf
    f = FITSFigure(data)
    f.show_grayscale()
    f.show_colorscale()

########NEW FILE########
__FILENAME__ = test_pixworld
import os

import matplotlib
matplotlib.use('Agg')

import numpy as np

from astropy.table import Table
from astropy.tests.helper import pytest
from .helpers import generate_wcs
from .. import wcs_util


HEADER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/2d_fits', '1904-66_TAN.hdr')

tab = Table({'RA':[347.,349.], 'DEC':[-68.,-68]})

GOOD_INPUT = [ [1.,2.],
               [[1.,2.],[3,4]],
               [np.arange(2), np.arange(2)],
               [tab['RA'], tab['DEC']]
             ]

BAD_INPUT = [ [1,['s','w']],
              [np.arange(2), np.sum],
              [tab['RA'], 'ewr']
            ]

@pytest.mark.parametrize(('inputval'), GOOD_INPUT)
def test_pixworld_input_and_consistency(inputval):
    wcs = generate_wcs(HEADER)
    ra, dec = wcs_util.pix2world(wcs, inputval[0], inputval[1])
    x, y = wcs_util.world2pix(wcs, ra, dec)
    # For some inputs (e.g. list) a-b is not defined
    # so change them all to np.ndarrays here to make sure
    assert np.all(np.abs(np.array(x) - np.array(inputval[0])) < 1e-5)
    assert np.all(np.abs(np.array(y) - np.array(inputval[1])) < 1e-5)

def test_returntypes():
    wcs = generate_wcs(HEADER)
    ra, dec = wcs_util.pix2world(wcs, 1.,2.)
    assert np.isscalar(ra) and np.isscalar(dec)
    ra, dec = wcs_util.pix2world(wcs, [1.],[2.])
    assert (type(ra) == list) and (type(dec) == list)
    # Astropy.table.Column objects get donwconverted np.ndarray
    ra, dec = wcs_util.pix2world(wcs, np.arange(2), tab['DEC'])
    assert isinstance(ra, np.ndarray) and isinstance(dec, np.ndarray)


@pytest.mark.parametrize(('inputval'), BAD_INPUT)
def test_pix2world_fail(inputval):
    wcs = generate_wcs(HEADER)
    with pytest.raises(Exception) as exc:
        wcs_util.pix2world(wcs, inputval[0], inputval[1])
    assert exc.value.args[0] == "pix2world should be provided either with two scalars, two lists, or two numpy arrays"

@pytest.mark.parametrize(('inputval'), BAD_INPUT)
def test_world2pix_fail(inputval):
    wcs = generate_wcs(HEADER)
    with pytest.raises(Exception) as exc:
        wcs_util.world2pix(wcs, inputval[0], inputval[1])
    assert exc.value.args[0] == "world2pix should be provided either with two scalars, two lists, or two numpy arrays"


########NEW FILE########
__FILENAME__ = test_pixworldmarkers
import os

import matplotlib
matplotlib.use('Agg')

import numpy as np

from astropy.table import Table
from astropy.tests.helper import pytest
from astropy.io import fits
from .helpers import generate_wcs
from .. import FITSFigure

HEADER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/2d_fits', '1904-66_TAN.hdr')

tab = Table({'RA':[347.,349.], 'DEC':[-68.,-68]})

GOOD_INPUT = [ [1,2],
               [[1,2],[3,4]],
               [np.arange(2), np.arange(2)],
               [tab['RA'], tab['DEC']]
             ]

BAD_INPUT = [ [1,['s', 'e']],
              [np.arange(2), np.sum],
              [tab['RA'], 'ewr']
            ]

@pytest.mark.parametrize(('inputval'), GOOD_INPUT)
def test_pixel_coords(inputval):
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_markers(inputval[0], inputval[1])
    f.close()

@pytest.mark.parametrize(('inputval'), GOOD_INPUT)
def test_wcs_coords(inputval):
    wcs = generate_wcs(HEADER)
    header = fits.Header.fromtextfile(HEADER)
    wcs.naxis1 = header['NAXIS1']
    wcs.naxis2 = header['NAXIS2']
    f = FITSFigure(wcs)
    f.show_markers(inputval[0], inputval[1])
    f.close()

@pytest.mark.parametrize(('inputval'), BAD_INPUT)
def test_pixel_coords_bad(inputval):
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    with pytest.raises(Exception) as exc:
        f.show_markers(inputval[0], inputval[1])
    assert exc.value.args[0] == "world2pix should be provided either with two scalars, two lists, or two numpy arrays"
    f.close()

@pytest.mark.parametrize(('inputval'), BAD_INPUT)
def test_wcs_coords_bad(inputval):
    wcs = generate_wcs(HEADER)
    header = fits.Header.fromtextfile(HEADER)
    wcs.naxis1 = header['NAXIS1']
    wcs.naxis2 = header['NAXIS2']
    f = FITSFigure(wcs)
    with pytest.raises(Exception) as exc:
        f.show_markers(inputval[0], inputval[1])
    f.close()
    assert exc.value.args[0] == "world2pix should be provided either with two scalars, two lists, or two numpy arrays"



########NEW FILE########
__FILENAME__ = test_save
import os
import sys

if sys.version_info[0] > 2:
    from io import BytesIO as StringIO
else:
    from StringIO import StringIO

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure

FORMATS = [None, 'png', 'pdf', 'eps', 'ps', 'svg']


def is_format(filename, format):
    if isinstance(filename, basestring):
        f = open(filename, 'rb')
    else:
        f = filename
    if format == 'png':
        return f.read(8) == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'
    elif format == 'pdf':
        return f.read(4) == b'\x25\x50\x44\x46'
    elif format == 'eps':
        return f.read(23) == b'%!PS-Adobe-3.0 EPSF-3.0'
    elif format == 'ps':
        return f.read(14) == b'%!PS-Adobe-3.0'
    elif format == 'svg':
        from xml.dom import minidom
        return minidom.parse(f).childNodes[2].attributes['xmlns'].value == u'http://www.w3.org/2000/svg'
    else:
        raise Exception("Unknown format: %s" % format)


@pytest.mark.parametrize(('format'), FORMATS)
def test_write_png(tmpdir, format):
    filename = os.path.join(str(tmpdir), 'test_output.png')
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    try:
        f.save(filename, format=format)
    except TypeError:
        pytest.xfail()
    finally:
        f.close()
    if format is None:
        assert is_format(filename, 'png')
    else:
        assert is_format(filename, format)


@pytest.mark.parametrize(('format'), FORMATS)
def test_write_pdf(tmpdir, format):
    filename = os.path.join(str(tmpdir), 'test_output.pdf')
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    try:
        f.save(filename, format=format)
    except TypeError:
        pytest.xfail()
    finally:
        f.close()
    if format is None:
        assert is_format(filename, 'pdf')
    else:
        assert is_format(filename, format)


@pytest.mark.parametrize(('format'), FORMATS)
def test_write_eps(tmpdir, format):
    filename = os.path.join(str(tmpdir), 'test_output.eps')
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    try:
        f.save(filename, format=format)
    except TypeError:
        pytest.xfail()
    finally:
        f.close()
    if format is None:
        assert is_format(filename, 'eps')
    else:
        assert is_format(filename, format)


@pytest.mark.parametrize(('format'), FORMATS)
def test_write_stringio(tmpdir, format):
    s = StringIO()
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.show_grayscale()
    try:
        f.save(s, format=format)
    except TypeError:
        pytest.xfail()
    finally:
        f.close()
    s.seek(0)
    if format is None:
        assert is_format(s, 'png')
    else:
        assert is_format(s, format)

########NEW FILE########
__FILENAME__ = test_scalebar
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure


def test_scalebar_add_invalid():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    with pytest.raises(TypeError):
        f.add_scalebar()


def test_scalebar_addremove():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.remove_scalebar()
    f.add_scalebar(0.1)
    f.close()


def test_scalebar_showhide():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.scalebar.hide()
    f.scalebar.show(0.1)
    f.close()


def test_scalebar_length():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.scalebar.set_length(0.01)
    f.scalebar.set_length(0.1)
    f.close()


def test_scalebar_label():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.scalebar.set_label('1 pc')
    f.scalebar.set_label('5 AU')
    f.scalebar.set_label('2"')
    f.close()


def test_scalebar_corner():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    for corner in ['top', 'bottom', 'left', 'right', 'top left', 'top right',
                   'bottom left', 'bottom right']:
        f.scalebar.set_corner(corner)
    f.close()


def test_scalebar_frame():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.scalebar.set_frame(True)
    f.scalebar.set_frame(False)
    f.close()


def test_scalebar_color():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.scalebar.set_color('black')
    f.scalebar.set_color('#003344')
    f.scalebar.set_color((1.0, 0.4, 0.3))
    f.close()


def test_scalebar_alpha():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.scalebar.set_alpha(0.1)
    f.scalebar.set_alpha(0.2)
    f.scalebar.set_alpha(0.5)
    f.close()


def test_scalebar_font():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.add_scalebar(0.1)
    f.scalebar.set_font(size='small', weight='bold', stretch='normal',
                        family='serif', style='normal', variant='normal')
    f.close()

########NEW FILE########
__FILENAME__ = test_subplot
import pytest
import numpy as np

from .. import FITSFigure


def test_subplot_grid():
    f = FITSFigure(np.zeros((10, 10)), subplot=(2, 2, 1))
    f.show_grayscale()
    f.close()


def test_subplot_box():
    f = FITSFigure(np.zeros((10, 10)), subplot=[0.1, 0.1, 0.8, 0.8])
    f.show_grayscale()
    f.close()


@pytest.mark.parametrize('subplot', [(1, 2, 3, 4), [1, 2, 3], '111', 1.2])
def test_subplot_invalid(subplot):
    with pytest.raises(ValueError) as exc:
        FITSFigure(np.zeros((10, 10)), subplot=subplot)
    assert exc.value.args[0] == "subplot= should be either a tuple of three values, or a list of four values"

########NEW FILE########
__FILENAME__ = test_ticks
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure


def test_ticks_show_hide():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.ticks.hide()
    f.ticks.show()
    f.ticks.hide_x()
    f.ticks.show_x()
    f.ticks.hide_y()
    f.ticks.show_y()
    f.close()


def test_ticks_spacing():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.ticks.set_xspacing(0.5)
    f.ticks.set_xspacing(1.)
    f.ticks.set_yspacing(0.5)
    f.ticks.set_yspacing(1.)
    f.close()


def test_ticks_length():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.ticks.set_length(0)
    f.ticks.set_length(1)
    f.ticks.set_length(10)
    f.close()


def test_ticks_color():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.ticks.set_color('black')
    f.ticks.set_color('#003344')
    f.ticks.set_color((1.0, 0.4, 0.3))
    f.close()


def test_ticks_linewidth():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.ticks.set_linewidth(1)
    f.ticks.set_linewidth(3)
    f.ticks.set_linewidth(10)
    f.close()


def test_ticks_minor_frequency():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.ticks.set_minor_frequency(1)
    f.ticks.set_minor_frequency(5)
    f.ticks.set_minor_frequency(10)
    f.close()

########NEW FILE########
__FILENAME__ = test_tick_labels
import matplotlib
matplotlib.use('Agg')

import numpy as np
from astropy.tests.helper import pytest

from .. import FITSFigure


def test_tick_labels_show_hide():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.tick_labels.hide()
    f.tick_labels.show()
    f.tick_labels.hide_x()
    f.tick_labels.show_x()
    f.tick_labels.hide_y()
    f.tick_labels.show_y()
    f.close()


def test_tick_labels_format_scalar():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.tick_labels.set_xformat('%i')
    f.tick_labels.set_yformat('%i')
    f.close()


def test_tick_labels_position():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.tick_labels.set_xposition('top')
    f.tick_labels.set_xposition('bottom')
    f.tick_labels.set_yposition('right')
    f.tick_labels.set_yposition('left')
    f.close()


def test_tick_labels_position_invalid():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    with pytest.raises(ValueError):
        f.tick_labels.set_xposition('right')
    with pytest.raises(ValueError):
        f.tick_labels.set_xposition('left')
    with pytest.raises(ValueError):
        f.tick_labels.set_yposition('top')
    with pytest.raises(ValueError):
        f.tick_labels.set_yposition('bottom')
    f.close()


def test_tick_labels_font():
    data = np.zeros((16, 16))
    f = FITSFigure(data)
    f.tick_labels.set_font(size='small', weight='bold', stretch='normal',
                           family='serif', style='normal', variant='normal')
    f.close()

########NEW FILE########
__FILENAME__ = ticks
from __future__ import absolute_import, print_function, division

import warnings

import numpy as np
from matplotlib.pyplot import Locator

from . import wcs_util
from . import angle_util as au
from . import scalar_util as su
from . import math_util
from .decorators import auto_refresh


class Ticks(object):

    @auto_refresh
    def __init__(self, parent):

        # Store references to axes
        self._ax1 = parent._ax1
        self._ax2 = parent._ax2
        self._wcs = parent._wcs
        self._figure = parent._figure
        self._parent = parent

        # Save plotting parameters (required for @auto_refresh)
        self._parameters = parent._parameters

        # Set tick positions
        self._ax1.yaxis.tick_left()
        self._ax1.xaxis.tick_bottom()
        self._ax2.yaxis.tick_right()
        self._ax2.xaxis.tick_top()

        # Set tick spacing to default
        self.set_xspacing('auto')
        self.set_yspacing('auto')

        # Set major tick locators
        lx = WCSLocator(wcs=self._wcs, coord='x')
        self._ax1.xaxis.set_major_locator(lx)
        ly = WCSLocator(wcs=self._wcs, coord='y')
        self._ax1.yaxis.set_major_locator(ly)
        lxt = WCSLocator(wcs=self._wcs, coord='x', farside=True)
        self._ax2.xaxis.set_major_locator(lxt)
        lyt = WCSLocator(wcs=self._wcs, coord='y', farside=True)
        self._ax2.yaxis.set_major_locator(lyt)

        # Set minor tick locators
        lx = WCSLocator(wcs=self._wcs, coord='x', minor=True)
        self._ax1.xaxis.set_minor_locator(lx)
        ly = WCSLocator(wcs=self._wcs, coord='y', minor=True)
        self._ax1.yaxis.set_minor_locator(ly)
        lxt = WCSLocator(wcs=self._wcs, coord='x', farside=True, minor=True)
        self._ax2.xaxis.set_minor_locator(lxt)
        lyt = WCSLocator(wcs=self._wcs, coord='y', farside=True, minor=True)
        self._ax2.yaxis.set_minor_locator(lyt)

    @auto_refresh
    def set_xspacing(self, spacing):
        '''
        Set the x-axis tick spacing, in degrees. To set the tick spacing to be
        automatically determined, set this to 'auto'.
        '''

        if spacing == 'auto':
            self._ax1.xaxis.apl_auto_tick_spacing = True
            self._ax2.xaxis.apl_auto_tick_spacing = True
        else:

            self._ax1.xaxis.apl_auto_tick_spacing = False
            self._ax2.xaxis.apl_auto_tick_spacing = False

            if self._wcs.xaxis_coord_type in ['longitude', 'latitude']:
                try:
                    au._check_format_spacing_consistency(self._ax1.xaxis.apl_label_form, au.Angle(degrees=spacing, latitude=self._wcs.xaxis_coord_type == 'latitude'))
                except au.InconsistentSpacing:
                    warnings.warn("WARNING: Requested tick spacing format cannot be shown by current label format. The tick spacing will not be changed.")
                    return
                self._ax1.xaxis.apl_tick_spacing = au.Angle(degrees=spacing, latitude=self._wcs.xaxis_coord_type == 'latitude')
                self._ax2.xaxis.apl_tick_spacing = au.Angle(degrees=spacing, latitude=self._wcs.xaxis_coord_type == 'latitude')
            else:
                try:
                    su._check_format_spacing_consistency(self._ax1.xaxis.apl_label_form, spacing)
                except au.InconsistentSpacing:
                    warnings.warn("WARNING: Requested tick spacing format cannot be shown by current label format. The tick spacing will not be changed.")
                    return
                self._ax1.xaxis.apl_tick_spacing = spacing
                self._ax2.xaxis.apl_tick_spacing = spacing

        if hasattr(self._parent, 'grid'):
            self._parent.grid._update()

    @auto_refresh
    def set_yspacing(self, spacing):
        '''
        Set the y-axis tick spacing, in degrees. To set the tick spacing to be
        automatically determined, set this to 'auto'.
        '''

        if spacing == 'auto':
            self._ax1.yaxis.apl_auto_tick_spacing = True
            self._ax2.yaxis.apl_auto_tick_spacing = True
        else:

            self._ax1.yaxis.apl_auto_tick_spacing = False
            self._ax2.yaxis.apl_auto_tick_spacing = False

            if self._wcs.yaxis_coord_type in ['longitude', 'latitude']:
                try:
                    au._check_format_spacing_consistency(self._ax1.yaxis.apl_label_form, au.Angle(degrees=spacing, latitude=self._wcs.yaxis_coord_type == 'latitude'))
                except au.InconsistentSpacing:
                    warnings.warn("WARNING: Requested tick spacing format cannot be shown by current label format. The tick spacing will not be changed.")
                    return
                self._ax1.yaxis.apl_tick_spacing = au.Angle(degrees=spacing, latitude=self._wcs.yaxis_coord_type == 'latitude')
                self._ax2.yaxis.apl_tick_spacing = au.Angle(degrees=spacing, latitude=self._wcs.yaxis_coord_type == 'latitude')
            else:
                try:
                    su._check_format_spacing_consistency(self._ax1.yaxis.apl_label_form, spacing)
                except au.InconsistentSpacing:
                    warnings.warn("WARNING: Requested tick spacing format cannot be shown by current label format. The tick spacing will not be changed.")
                    return
                self._ax1.yaxis.apl_tick_spacing = spacing
                self._ax2.yaxis.apl_tick_spacing = spacing

        if hasattr(self._parent, 'grid'):
            self._parent.grid._update()

    @auto_refresh
    def set_color(self, color):
        '''
        Set the color of the ticks
        '''

        # Major ticks
        for line in self._ax1.xaxis.get_ticklines():
            line.set_color(color)
        for line in self._ax1.yaxis.get_ticklines():
            line.set_color(color)
        for line in self._ax2.xaxis.get_ticklines():
            line.set_color(color)
        for line in self._ax2.yaxis.get_ticklines():
            line.set_color(color)

        # Minor ticks
        for line in self._ax1.xaxis.get_minorticklines():
            line.set_color(color)
        for line in self._ax1.yaxis.get_minorticklines():
            line.set_color(color)
        for line in self._ax2.xaxis.get_minorticklines():
            line.set_color(color)
        for line in self._ax2.yaxis.get_minorticklines():
            line.set_color(color)

    @auto_refresh
    def set_length(self, length, minor_factor=0.5):
        '''
        Set the length of the ticks (in points)
        '''

        # Major ticks
        for line in self._ax1.xaxis.get_ticklines():
            line.set_markersize(length)
        for line in self._ax1.yaxis.get_ticklines():
            line.set_markersize(length)
        for line in self._ax2.xaxis.get_ticklines():
            line.set_markersize(length)
        for line in self._ax2.yaxis.get_ticklines():
            line.set_markersize(length)

        # Minor ticks
        for line in self._ax1.xaxis.get_minorticklines():
            line.set_markersize(length * minor_factor)
        for line in self._ax1.yaxis.get_minorticklines():
            line.set_markersize(length * minor_factor)
        for line in self._ax2.xaxis.get_minorticklines():
            line.set_markersize(length * minor_factor)
        for line in self._ax2.yaxis.get_minorticklines():
            line.set_markersize(length * minor_factor)

    @auto_refresh
    def set_linewidth(self, linewidth):
        '''
        Set the linewidth of the ticks (in points)
        '''

        # Major ticks
        for line in self._ax1.xaxis.get_ticklines():
            line.set_mew(linewidth)
        for line in self._ax1.yaxis.get_ticklines():
            line.set_mew(linewidth)
        for line in self._ax2.xaxis.get_ticklines():
            line.set_mew(linewidth)
        for line in self._ax2.yaxis.get_ticklines():
            line.set_mew(linewidth)

        # Minor ticks
        for line in self._ax1.xaxis.get_minorticklines():
            line.set_mew(linewidth)
        for line in self._ax1.yaxis.get_minorticklines():
            line.set_mew(linewidth)
        for line in self._ax2.xaxis.get_minorticklines():
            line.set_mew(linewidth)
        for line in self._ax2.yaxis.get_minorticklines():
            line.set_mew(linewidth)

    @auto_refresh
    def set_minor_frequency(self, frequency):
        '''
        Set the number of subticks per major tick. Set to one to hide minor
        ticks.
        '''
        self._ax1.xaxis.get_minor_locator().subticks = frequency
        self._ax1.yaxis.get_minor_locator().subticks = frequency
        self._ax2.xaxis.get_minor_locator().subticks = frequency
        self._ax2.yaxis.get_minor_locator().subticks = frequency

    @auto_refresh
    def show(self):
        """
        Show the x- and y-axis ticks
        """
        self.show_x()
        self.show_y()

    @auto_refresh
    def hide(self):
        """
        Hide the x- and y-axis ticks
        """
        self.hide_x()
        self.hide_y()

    @auto_refresh
    def show_x(self):
        """
        Show the x-axis ticks
        """
        for line in self._ax1.xaxis.get_ticklines():
            line.set_visible(True)
        for line in self._ax2.xaxis.get_ticklines():
            line.set_visible(True)
        for line in self._ax1.xaxis.get_minorticklines():
            line.set_visible(True)
        for line in self._ax2.xaxis.get_minorticklines():
            line.set_visible(True)

    @auto_refresh
    def hide_x(self):
        """
        Hide the x-axis ticks
        """
        for line in self._ax1.xaxis.get_ticklines():
            line.set_visible(False)
        for line in self._ax2.xaxis.get_ticklines():
            line.set_visible(False)
        for line in self._ax1.xaxis.get_minorticklines():
            line.set_visible(False)
        for line in self._ax2.xaxis.get_minorticklines():
            line.set_visible(False)

    @auto_refresh
    def show_y(self):
        """
        Show the y-axis ticks
        """
        for line in self._ax1.yaxis.get_ticklines():
            line.set_visible(True)
        for line in self._ax2.yaxis.get_ticklines():
            line.set_visible(True)
        for line in self._ax1.yaxis.get_minorticklines():
            line.set_visible(True)
        for line in self._ax2.yaxis.get_minorticklines():
            line.set_visible(True)

    @auto_refresh
    def hide_y(self):
        """
        Hide the y-axis ticks
        """
        for line in self._ax1.yaxis.get_ticklines():
            line.set_visible(False)
        for line in self._ax2.yaxis.get_ticklines():
            line.set_visible(False)
        for line in self._ax1.yaxis.get_minorticklines():
            line.set_visible(False)
        for line in self._ax2.yaxis.get_minorticklines():
            line.set_visible(False)


class WCSLocator(Locator):

    def __init__(self, presets=None, wcs=False, coord='x', farside=False, minor=False, subticks=5):
        if presets is None:
            self.presets = {}
        else:
            self.presets = presets
        self._wcs = wcs
        self.coord = coord
        self.farside = farside
        self.minor = minor
        self.subticks = subticks

    def __call__(self):

        self.coord_type = self._wcs.xaxis_coord_type if self.coord == 'x' else self._wcs.yaxis_coord_type

        ymin, ymax = self.axis.get_axes().yaxis.get_view_interval()
        xmin, xmax = self.axis.get_axes().xaxis.get_view_interval()

        if self.axis.apl_auto_tick_spacing:
            self.axis.apl_tick_spacing = default_spacing(self.axis.get_axes(), self.coord, self.axis.apl_label_form)
            if self.axis.apl_tick_spacing is None:
                self.axis.apl_tick_positions_pix = []
                self.axis.apl_tick_positions_world = []
                return []

        if self.coord_type in ['longitude', 'latitude']:
            tick_spacing = self.axis.apl_tick_spacing.todegrees()
        else:
            tick_spacing = self.axis.apl_tick_spacing

        if self.minor:
            tick_spacing /= float(self.subticks)

        px, py, wx = tick_positions(self._wcs, tick_spacing, self.coord, self.coord, farside=self.farside, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, mode='xscaled')
        px, py, wx = np.array(px, float), np.array(py, float), np.array(wx, int)

        if self.minor:
            keep = np.mod(wx, self.subticks) > 0
            px, py, wx = px[keep], py[keep], wx[keep] / float(self.subticks)

        self.axis.apl_tick_positions_world = np.array(wx, int)

        if self.coord == 'x':
            self.axis.apl_tick_positions_pix = px
        else:
            self.axis.apl_tick_positions_pix = py

        return self.axis.apl_tick_positions_pix


def default_spacing(ax, coord, format):

    wcs = ax._wcs

    xmin, xmax = ax.xaxis.get_view_interval()
    ymin, ymax = ax.yaxis.get_view_interval()

    px, py, wx, wy = axis_positions(wcs, coord, False, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)

    # Keep only pixels that fall inside the sky. This will only really work
    # for PyWCS 0.11 or more recent
    keep = ~np.isnan(wx) & ~np.isnan(wy)

    if np.sum(keep) == 0:
        return None
    else:
        px = px[keep]
        py = py[keep]
        wx = wx[keep]
        wy = wy[keep]

    coord_type = wcs.xaxis_coord_type if coord == 'x' else wcs.yaxis_coord_type

    if coord == 'x':

        # The following is required because PyWCS 0.10 and earlier did not return
        # NaNs for positions outside the sky, but instead returned an array with
        # all the same world coordinates regardless of input pixel coordinates.
        if len(wx) > 1 and len(np.unique(wx)) == 1:
            return None

        if coord_type in ['longitude', 'latitude']:
            if coord_type == 'longitude':
                wxmin, wxmax = math_util.smart_range(wx)
            else:
                wxmin, wxmax = min(wx), max(wx)
            if 'd.' in format:
                spacing = au.smart_round_angle_decimal((wxmax - wxmin) / 5., latitude=coord_type == 'latitude')
            else:
                spacing = au.smart_round_angle_sexagesimal((wxmax - wxmin) / 5., latitude=coord_type == 'latitude', hours='hh' in format)
        else:
            wxmin, wxmax = np.min(wx), np.max(wx)
            spacing = su.smart_round_angle_decimal((wxmax - wxmin) / 5.)
    else:

        # The following is required because PyWCS 0.10 and earlier did not return
        # NaNs for positions outside the sky, but instead returned an array with
        # all the same world coordinates regardless of input pixel coordinates.
        if len(wy) > 1 and len(np.unique(wy)) == 1:
            return None

        if coord_type in ['longitude', 'latitude']:
            if coord_type == 'longitude':
                wymin, wymax = math_util.smart_range(wy)
            else:
                wymin, wymax = min(wy), max(wy)
            if 'd.' in format:
                spacing = au.smart_round_angle_decimal((wymax - wymin) / 5., latitude=coord_type == 'latitude')
            else:
                spacing = au.smart_round_angle_sexagesimal((wymax - wymin) / 5., latitude=coord_type == 'latitude', hours='hh' in format)
        else:
            wymin, wymax = np.min(wy), np.max(wy)
            spacing = su.smart_round_angle_decimal((wymax - wymin) / 5.)

    # Find minimum spacing allowed by labels
    if coord_type in ['longitude', 'latitude']:
        min_spacing = au._get_label_precision(format, latitude=coord_type == 'latitude')
        if min_spacing.todegrees() > spacing.todegrees():
            return min_spacing
        else:
            return spacing
    else:
        min_spacing = su._get_label_precision(format)
        if min_spacing is not None and min_spacing > spacing:
            return min_spacing
        else:
            return spacing


def tick_positions(wcs, spacing, axis, coord, farside=False,
                   xmin=False, xmax=False, ymin=False, ymax=False,
                   mode='xscaled'):
    '''
    Find positions of ticks along a given axis.

    Parameters
    ----------

    wcs : ~aplpy.wcs_util.WCS
       The WCS instance for the image.

    spacing : float
       The spacing along the axis.

    axis : { 'x', 'y' }
       The axis along which we are looking for ticks.

    coord : { 'x', 'y' }
       The coordinate for which we are looking for ticks.

    farside : bool, optional
       Whether we are looking on the left or bottom axes (False) or the
       right or top axes (True).

    xmin, xmax, ymin, ymax : float, optional
       The range of pixel values covered by the image.

    mode : { 'xy', 'xscaled' }, optional
       If set to 'xy' the function returns the world coordinates of the
       ticks. If 'xscaled', then only the coordinate requested is
       returned, in units of the tick spacing.
    '''

    (px, py, wx, wy) = axis_positions(wcs, axis, farside, xmin, xmax, ymin, ymax)

    if coord == 'x':
        warr, walt = wx, wy
    else:
        warr, walt = wy, wx

    # Check for 360 degree transition, and if encountered,
    # change the values so that there is continuity

    if (coord == 'x' and wcs.xaxis_coord_type == 'longitude') or \
       (coord == 'y' and wcs.yaxis_coord_type == 'longitude'):
        for i in range(0, len(warr) - 1):
            if(abs(warr[i] - warr[i + 1]) > 180.):
                if(warr[i] > warr[i + 1]):
                    warr[i + 1:] = warr[i + 1:] + 360.
                else:
                    warr[i + 1:] = warr[i + 1:] - 360.

    # Convert warr to units of the spacing, then ticks are at integer values
    warr = warr / spacing

    # Create empty arrays for tick positions
    iall = []
    wall = []

    # Loop over ticks which lie in the range covered by the axis
    for w in np.arange(np.floor(min(warr)), np.ceil(max(warr)), 1.):

        # Find all the positions at which to interpolate
        inter = np.where(((warr[:-1] <= w) & (warr[1:] > w)) | ((warr[:-1] > w) & (warr[1:] <= w)))[0]

        # If there are any intersections, keep the indices, and the position
        # of the interpolation
        if len(inter) > 0:
            iall.append(inter.astype(int))
            wall.append(np.repeat(w, len(inter)).astype(float))

    if len(iall) > 0:
        iall = np.hstack(iall)
        wall = np.hstack(wall)
    else:
        if mode == 'xscaled':
            return [], [], []
        else:
            return [], [], [], []

    # Now we can interpolate as needed
    dwarr = warr[1:] - warr[:-1]
    px_out = px[:-1][iall] + (px[1:][iall] - px[:-1][iall]) * (wall - warr[:-1][iall]) / dwarr[iall]
    py_out = py[:-1][iall] + (py[1:][iall] - py[:-1][iall]) * (wall - warr[:-1][iall]) / dwarr[iall]

    if mode == 'xscaled':
        warr_out = wall
        return px_out, py_out, warr_out
    elif mode == 'xy':
        warr_out = wall * spacing
        walt_out = walt[:-1][iall] + (walt[1:][iall] - walt[:-1][iall]) * (wall - warr[:-1][iall]) / dwarr[iall]
        if coord == 'x':
            return px_out, py_out, warr_out, walt_out
        else:
            return px_out, py_out, walt_out, warr_out


def axis_positions(wcs, axis, farside, xmin=False, xmax=False,
                                       ymin=False, ymax=False):
    '''
    Find the world coordinates of all pixels along an axis.

    Parameters
    ----------

    wcs : ~aplpy.wcs_util.WCS
       The WCS instance for the image.

    axis : { 'x', 'y' }
       The axis along which we are computing world coordinates.

    farside : bool
       Whether we are looking on the left or bottom axes (False) or the
       right or top axes (True).

    xmin, xmax, ymin, ymax : float, optional
       The range of pixel values covered by the image
    '''

    if not xmin:
        xmin = 0.5
    if not xmax:
        xmax = 0.5 + wcs.nx
    if not ymin:
        ymin = 0.5
    if not ymax:
        ymax = 0.5 + wcs.ny

    # Check options
    assert axis == 'x' or axis == 'y', "The axis= argument should be set to x or y"

    # Generate an array of pixel values for the x-axis
    if axis == 'x':
        x_pix = np.linspace(xmin, xmax, 512)
        y_pix = np.ones(np.shape(x_pix))
        if(farside):
            y_pix = y_pix * ymax
        else:
            y_pix = y_pix * ymin
    else:
        y_pix = np.linspace(ymin, ymax, 512)
        x_pix = np.ones(np.shape(y_pix))
        if(farside):
            x_pix = x_pix * xmax
        else:
            x_pix = x_pix * xmin

    # Convert these to world coordinates
    x_world, y_world = wcs_util.pix2world(wcs, x_pix, y_pix)

    return x_pix, y_pix, x_world, y_world


def coord_range(wcs):
    '''
    Find the range of coordinates that intersect the axes.

    Parameters
    ----------

    wcs : ~aplpy.wcs_util.WCS
        The WCS instance for the image.
    '''

    x_pix, y_pix, x_world_1, y_world_1 = axis_positions(wcs, 'x', farside=False)
    x_pix, y_pix, x_world_2, y_world_2 = axis_positions(wcs, 'x', farside=True)
    x_pix, y_pix, x_world_3, y_world_3 = axis_positions(wcs, 'y', farside=False)
    x_pix, y_pix, x_world_4, y_world_4 = axis_positions(wcs, 'y', farside=True)

    x_world = np.hstack([x_world_1, x_world_2, x_world_3, x_world_4])
    y_world = np.hstack([y_world_1, y_world_2, y_world_3, y_world_4])

    x_min = min(x_world)
    x_max = max(x_world)
    y_min = min(y_world)
    y_max = max(y_world)

    return x_min, x_max, y_min, y_max

########NEW FILE########
__FILENAME__ = wcs_util
from __future__ import absolute_import, print_function, division

import numpy as np


from astropy import log
from astropy.wcs import WCS as AstropyWCS


def decode_ascii(string):
    try:
        return string.decode('ascii')
    except AttributeError:
        return string


class WCS(AstropyWCS):

    def __init__(self, *args, **kwargs):

        if 'slices' in kwargs:
            self._slices = kwargs.pop('slices')

        if 'dimensions' in kwargs:
            self._dimensions = kwargs.pop('dimensions')

        AstropyWCS.__init__(self, *args, **kwargs)

        # Fix common non-standard units
        self.wcs.unitfix()

        # Now find the values of the coordinates in the slices - only needed if
        # data has more than two dimensions
        if len(self._slices) > 0:

            self.nx = args[0]['NAXIS%i' % (self._dimensions[0] + 1)]
            self.ny = args[0]['NAXIS%i' % (self._dimensions[1] + 1)]
            xpix = np.arange(self.nx) + 1.
            ypix = np.arange(self.ny) + 1.
            xpix, ypix = np.meshgrid(xpix, ypix)
            xpix, ypix = xpix.reshape(self.nx * self.ny), ypix.reshape(self.nx * self.ny)
            s = 0
            coords = []
            for dim in range(self.naxis):
                if dim == self._dimensions[0]:
                    coords.append(xpix)
                elif dim == self._dimensions[1]:
                    coords.append(ypix)
                else:
                    coords.append(np.repeat(self._slices[s], xpix.shape))
                    s += 1
            coords = np.vstack(coords).transpose()
            result = AstropyWCS.wcs_pix2world(self, coords, 1)
            self._mean_world = np.mean(result, axis=0)
            # result = result.transpose()
            # result = result.reshape((result.shape[0],) + (self.ny, self.nx))

        # Now guess what 'type' of values are on each axis
        if self.ctype_x[:4] == 'RA--' or \
           self.ctype_x[1:4] == 'LON':
            self.set_xaxis_coord_type('longitude')
            self.set_xaxis_coord_type('longitude')
        elif self.ctype_x[:4] == 'DEC-' or \
           self.ctype_x[1:4] == 'LAT':
            self.set_xaxis_coord_type('latitude')
            self.set_xaxis_coord_type('latitude')
        else:
            self.set_xaxis_coord_type('scalar')
            self.set_xaxis_coord_type('scalar')

        if self.ctype_y[:4] == 'RA--' or \
           self.ctype_y[1:4] == 'LON':
            self.set_yaxis_coord_type('longitude')
            self.set_yaxis_coord_type('longitude')
        elif self.ctype_y[:4] == 'DEC-' or \
           self.ctype_y[1:4] == 'LAT':
            self.set_yaxis_coord_type('latitude')
            self.set_yaxis_coord_type('latitude')
        else:
            self.set_yaxis_coord_type('scalar')
            self.set_yaxis_coord_type('scalar')

    def get_pixel_scales(self):
        cdelt = np.matrix(self.wcs.get_cdelt())
        pc = np.matrix(self.wcs.get_pc())
        scale = np.array(cdelt * pc)[0,:]
        return scale[self._dimensions[0]], scale[self._dimensions[1]]

    def set_xaxis_coord_type(self, coord_type):
        if coord_type in ['longitude', 'latitude', 'scalar']:
            self.xaxis_coord_type = coord_type
        else:
            raise Exception("coord_type should be one of longitude/latitude/scalar")

    def set_yaxis_coord_type(self, coord_type):
        if coord_type in ['longitude', 'latitude', 'scalar']:
            self.yaxis_coord_type = coord_type
        else:
            raise Exception("coord_type should be one of longitude/latitude/scalar")

    def __getattr__(self, attribute):

        if attribute[-2:] == '_x':
            axis = self._dimensions[0]
        elif attribute[-2:] == '_y':
            axis = self._dimensions[1]
        else:
            raise AttributeError("Attribute %s does not exist" % attribute)

        if attribute[:5] == 'ctype':
            return decode_ascii(self.wcs.ctype[axis])
        elif attribute[:5] == 'cname':
            return decode_ascii(self.wcs.cname[axis])
        elif attribute[:5] == 'cunit':
            return str(self.wcs.cunit[axis])
        elif attribute[:5] == 'crval':
            return decode_ascii(self.wcs.crval[axis])
        elif attribute[:5] == 'crpix':
            return decode_ascii(self.wcs.crpix[axis])
        else:
            raise AttributeError("Attribute %s does not exist" % attribute)

    def wcs_world2pix(self, x, y, origin):
        if self.naxis == 2:
            if self._dimensions[1] < self._dimensions[0]:
                xp, yp = AstropyWCS.wcs_world2pix(self, y, x, origin)
                return yp, xp
            else:
                return AstropyWCS.wcs_world2pix(self, x, y, origin)
        else:
            coords = []
            s = 0
            for dim in range(self.naxis):
                if dim == self._dimensions[0]:
                    coords.append(x)
                elif dim == self._dimensions[1]:
                    coords.append(y)
                else:
                    # The following is an approximation, and will break down if
                    # the world coordinate changes significantly over the slice
                    coords.append(np.repeat(self._mean_world[dim], x.shape))
                    s += 1
            coords = np.vstack(coords).transpose()

            # Due to a bug in pywcs, we need to loop over each coordinate
            # result = AstropyWCS.wcs_world2pix(self, coords, origin)
            result = np.zeros(coords.shape)
            for i in range(result.shape[0]):
                result[i:i + 1, :] = AstropyWCS.wcs_world2pix(self, coords[i:i + 1, :], origin)

            return result[:, self._dimensions[0]], result[:, self._dimensions[1]]

    def wcs_pix2world(self, x, y, origin):
        if self.naxis == 2:
            if self._dimensions[1] < self._dimensions[0]:
                xw, yw = AstropyWCS.wcs_pix2world(self, y, x, origin)
                return yw, xw
            else:
                return AstropyWCS.wcs_pix2world(self, x, y, origin)
        else:
            coords = []
            s = 0
            for dim in range(self.naxis):
                if dim == self._dimensions[0]:
                    coords.append(x)
                elif dim == self._dimensions[1]:
                    coords.append(y)
                else:
                    coords.append(np.repeat(self._slices[s] + 0.5, x.shape))
                    s += 1
            coords = np.vstack(coords).transpose()
            result = AstropyWCS.wcs_pix2world(self, coords, origin)
            return result[:, self._dimensions[0]], result[:, self._dimensions[1]]


def convert_coords(x, y, input, output):

    system_in, equinox_in = input
    system_out, equinox_out = output

    if input == output:
        return x, y

    # Need to take into account inverted coords

    if system_in['name'] == 'galactic' and system_out['name'] == 'equatorial':

        if equinox_out == 'j2000':
            x, y = gal2fk5(x, y)
        elif equinox_out == 'b1950':
            x, y = gal2fk5(x, y)
            x, y = j2000tob1950(x, y)
        else:
            raise Exception("Cannot convert from galactic to equatorial coordinates for equinox=%s" % equinox_out)

    elif system_in['name'] == 'equatorial' and system_out['name'] == 'galactic':

        if equinox_in == 'j2000':
            x, y = fk52gal(x, y)
        elif equinox_in == 'b1950':
            x, y = b1950toj2000(x, y)
            x, y = fk52gal(x, y)
        else:
            raise Exception("Cannot convert from equatorial to equatorial coordinates for equinox=%s" % equinox_in)

    elif system_in['name'] == 'equatorial' and system_out['name'] == 'equatorial':

        if equinox_in == 'b1950' and equinox_out == 'j2000':
            x, y = b1950toj2000(x, y)
        elif equinox_in == 'j2000' and equinox_out == 'b1950':
            x, y = j2000tob1950(x, y)
        elif equinox_in == equinox_out:
            pass
        else:
            raise Exception("Cannot convert between equatorial coordinates for equinoxes %s and %s" % (equinox_in, equinox_out))

    else:
        raise Exception("Cannot (yet) convert between %s, %s and %s, %s" % (system_in['name'], equinox_in, system_out['name'], equinox_out))

    # Take into account inverted coordinates
    if system_in['inverted'] is system_out['inverted']:
        return x, y
    else:
        return y, x


def precession_matrix(equinox1, equinox2, fk4=False):
    "Adapted from the IDL astronomy library"

    deg_to_rad = np.pi / 180.
    sec_to_rad = deg_to_rad / 3600.

    t = 0.001 * (equinox2 - equinox1)

    if not fk4:

        st = 0.001 * (equinox1 - 2000.)

        # Compute 3 rotation angles
        a = sec_to_rad * t * (23062.181 + st * (139.656 + 0.0139 * st) + t * (30.188 - 0.344 * st + 17.998 * t))
        b = sec_to_rad * t * t * (79.280 + 0.410 * st + 0.205 * t) + a
        c = sec_to_rad * t * (20043.109 - st * (85.33 + 0.217 * st) + t * (- 42.665 - 0.217 * st - 41.833 * t))

    else:

        st = 0.001 * (equinox1 - 1900.)

        # Compute 3 rotation angles
        a = sec_to_rad * t * (23042.53 + st * (139.75 + 0.06 * st) + t * (30.23 - 0.27 * st + 18.0 * t))
        b = sec_to_rad * t * t * (79.27 + 0.66 * st + 0.32 * t) + a
        c = sec_to_rad * t * (20046.85 - st * (85.33 + 0.37 * st) + t * (- 42.67 - 0.37 * st - 41.8 * t))

    sina = np.sin(a)
    sinb = np.sin(b)
    sinc = np.sin(c)
    cosa = np.cos(a)
    cosb = np.cos(b)
    cosc = np.cos(c)

    r = np.matrix([[cosa * cosb * cosc - sina * sinb, sina * cosb + cosa * sinb * cosc,  cosa * sinc],
                   [- cosa * sinb - sina * cosb * cosc, cosa * cosb - sina * sinb * cosc, - sina * sinc],
                   [- cosb * sinc, - sinb * sinc, cosc]])

    return r

P1 = precession_matrix(1950., 2000.)
P2 = precession_matrix(2000., 1950.)


def b1950toj2000(ra, dec):
    '''
    Convert B1950 to J2000 coordinates.

    This routine is based on the technique described at
    http://www.stargazing.net/kepler/b1950.html
    '''

    # Convert to radians
    ra = np.radians(ra)
    dec = np.radians(dec)

    # Convert RA, Dec to rectangular coordinates
    x = np.cos(ra) * np.cos(dec)
    y = np.sin(ra) * np.cos(dec)
    z = np.sin(dec)

    # Apply the precession matrix
    x2 = P1[0, 0] * x + P1[1, 0] * y + P1[2, 0] * z
    y2 = P1[0, 1] * x + P1[1, 1] * y + P1[2, 1] * z
    z2 = P1[0, 2] * x + P1[1, 2] * y + P1[2, 2] * z

    # Convert the new rectangular coordinates back to RA, Dec
    ra = np.arctan2(y2, x2)
    dec = np.arcsin(z2)

    # Convert to degrees
    ra = np.degrees(ra)
    dec = np.degrees(dec)

    # Make sure ra is between 0. and 360.
    ra = np.mod(ra, 360.)
    dec = np.mod(dec + 90., 180.) - 90.

    return ra, dec


def j2000tob1950(ra, dec):
    '''
    Convert J2000 to B1950 coordinates.

    This routine was derived by taking the inverse of the b1950toj2000 routine
    '''

    # Convert to radians
    ra = np.radians(ra)
    dec = np.radians(dec)

    # Convert RA, Dec to rectangular coordinates
    x = np.cos(ra) * np.cos(dec)
    y = np.sin(ra) * np.cos(dec)
    z = np.sin(dec)

    # Apply the precession matrix
    x2 = P2[0, 0] * x + P2[1, 0] * y + P2[2, 0] * z
    y2 = P2[0, 1] * x + P2[1, 1] * y + P2[2, 1] * z
    z2 = P2[0, 2] * x + P2[1, 2] * y + P2[2, 2] * z

    # Convert the new rectangular coordinates back to RA, Dec
    ra = np.arctan2(y2, x2)
    dec = np.arcsin(z2)

    # Convert to degrees
    ra = np.degrees(ra)
    dec = np.degrees(dec)

    # Make sure ra is between 0. and 360.
    ra = np.mod(ra, 360.)
    dec = np.mod(dec + 90., 180.) - 90.

    return ra, dec

# Galactic conversion constants
RA_NGP = np.radians(192.859508333333)
DEC_NGP = np.radians(27.1283361111111)
L_CP = np.radians(122.932)
L_0 = L_CP - np.pi / 2.
RA_0 = RA_NGP + np.pi / 2.
DEC_0 = np.pi / 2. - DEC_NGP


def gal2fk5(l, b):

    l = np.radians(l)
    b = np.radians(b)

    sind = np.sin(b) * np.sin(DEC_NGP) + np.cos(b) * np.cos(DEC_NGP) * np.sin(l - L_0)

    dec = np.arcsin(sind)

    cosa = np.cos(l - L_0) * np.cos(b) / np.cos(dec)
    sina = (np.cos(b) * np.sin(DEC_NGP) * np.sin(l - L_0) - np.sin(b) * np.cos(DEC_NGP)) / np.cos(dec)

    dec = np.degrees(dec)

    ra = np.arccos(cosa)
    ra[np.where(sina < 0.)] = -ra[np.where(sina < 0.)]

    ra = np.degrees(ra + RA_0)

    ra = np.mod(ra, 360.)
    dec = np.mod(dec + 90., 180.) - 90.

    return ra, dec


def fk52gal(ra, dec):

    ra, dec = np.radians(ra), np.radians(dec)

    np.sinb = np.sin(dec) * np.cos(DEC_0) - np.cos(dec) * np.sin(ra - RA_0) * np.sin(DEC_0)

    b = np.arcsin(np.sinb)

    cosl = np.cos(dec) * np.cos(ra - RA_0) / np.cos(b)
    sinl = (np.sin(dec) * np.sin(DEC_0) + np.cos(dec) * np.sin(ra - RA_0) * np.cos(DEC_0)) / np.cos(b)

    b = np.degrees(b)

    l = np.arccos(cosl)
    l[np.where(sinl < 0.)] = - l[np.where(sinl < 0.)]

    l = np.degrees(l + L_0)

    l = np.mod(l, 360.)
    b = np.mod(b + 90., 180.) - 90.

    return l, b


def system(wcs):

    xcoord = wcs.ctype_x[0:4]
    ycoord = wcs.ctype_y[0:4]
    equinox = wcs.wcs.equinox

    system = {}

    if xcoord == 'RA--' and ycoord == 'DEC-':
        system['name'] = 'equatorial'
        system['inverted'] = False
    elif ycoord == 'RA--' and xcoord == 'DEC-':
        system['name'] = 'equatorial'
        system['inverted'] = True
    elif xcoord == 'GLON' and ycoord == 'GLAT':
        system['name'] = 'galactic'
        system['inverted'] = False
    elif ycoord == 'GLON' and xcoord == 'GLAT':
        system['name'] = 'galactic'
        system['inverted'] = True
    elif xcoord == 'ELON' and ycoord == 'ELAT':
        system['name'] = 'ecliptic'
        system['inverted'] = False
    elif ycoord == 'ELON' and xcoord == 'ELAT':
        system['name'] = 'ecliptic'
        system['inverted'] = True
    else:
        system['name'] = 'unknown'
        system['inverted'] = False

    if system['name'] == 'equatorial':
        if equinox == '' or np.isnan(equinox) or equinox == 0.:
            log.warning("Cannot determine equinox. Assuming J2000.")
            equinox = 'j2000'
        elif equinox == 1950.:
            equinox = 'b1950'
        elif equinox == 2000.:
            equinox = 'j2000'
        else:
            raise Exception("Cannot use equinox %s" % equinox)
    else:
        equinox = 'none'

    units = 'degrees'

    return system, equinox, units


def arcperpix(wcs):
    return degperpix(wcs) * 3600.


def degperpix(wcs):
    sx, sy = pixel_scale(wcs)
    return 0.5 * (sx + sy)


def pixel_scale(wcs):
    return np.abs(wcs.get_pixel_scales())


def world2pix(wcs, x_world, y_world):
    if np.isscalar(x_world) and np.isscalar(y_world):
        x_pix, y_pix = wcs.wcs_world2pix(np.array([x_world]), np.array([y_world]), 1)
        return x_pix[0], y_pix[0]
    elif (type(x_world) == list) and (type(y_world) == list):
        x_pix, y_pix = wcs.wcs_world2pix(np.array(x_world), np.array(y_world), 1)
        return x_pix.tolist(), y_pix.tolist()
    elif isinstance(x_world, np.ndarray) and isinstance(y_world, np.ndarray):
        return wcs.wcs_world2pix(x_world, y_world, 1)
    else:
        raise Exception("world2pix should be provided either with two scalars, two lists, or two numpy arrays")


def pix2world(wcs, x_pix, y_pix):
    if np.isscalar(x_pix) and np.isscalar(y_pix):
        x_world, y_world = wcs.wcs_pix2world(np.array([x_pix]), np.array([y_pix]), 1)
        return x_world[0], y_world[0]
    elif (type(x_pix) == list) and (type(y_pix) == list):
        x_world, y_world = wcs.wcs_pix2world(np.array(x_pix), np.array(y_pix), 1)
        return x_world.tolist(), y_world.tolist()
    elif isinstance(x_pix, np.ndarray) and isinstance(y_pix, np.ndarray):
        return wcs.wcs_pix2world(x_pix, y_pix, 1)
    else:
        raise Exception("pix2world should be provided either with two scalars, two lists, or two numpy arrays")

########NEW FILE########
__FILENAME__ = _astropy_init
# Licensed under a 3-clause BSD style license - see LICENSE.rst

__all__ = ['__version__', '__githash__', 'test']

#this indicates whether or not we are in the package's setup.py
try:
    _ASTROPY_SETUP_
except NameError:
    from sys import version_info
    if version_info[0] >= 3:
        import builtins
    else:
        import __builtin__ as builtins
    builtins._ASTROPY_SETUP_ = False

try:
    from .version import version as __version__
except ImportError:
    __version__ = ''
try:
    from .version import githash as __githash__
except ImportError:
    __githash__ = ''

# set up the test command
def _get_test_runner():
    import os
    from astropy.tests.helper import TestRunner
    return TestRunner(os.path.dirname(__file__))

def test(package=None, test_path=None, args=None, plugins=None,
         verbose=False, pastebin=None, remote_data=False, pep8=False,
         pdb=False, coverage=False, open_files=False, **kwargs):
    """
    Run the tests using py.test. A proper set of arguments is constructed and
    passed to `pytest.main`.

    Parameters
    ----------
    package : str, optional
        The name of a specific package to test, e.g. 'io.fits' or 'utils'.
        If nothing is specified all default tests are run.

    test_path : str, optional
        Specify location to test by path. May be a single file or
        directory. Must be specified absolutely or relative to the
        calling directory.

    args : str, optional
        Additional arguments to be passed to `pytest.main` in the `args`
        keyword argument.

    plugins : list, optional
        Plugins to be passed to `pytest.main` in the `plugins` keyword
        argument.

    verbose : bool, optional
        Convenience option to turn on verbose output from py.test. Passing
        True is the same as specifying `-v` in `args`.

    pastebin : {'failed','all',None}, optional
        Convenience option for turning on py.test pastebin output. Set to
        'failed' to upload info for failed tests, or 'all' to upload info
        for all tests.

    remote_data : bool, optional
        Controls whether to run tests marked with @remote_data. These
        tests use online data and are not run by default. Set to True to
        run these tests.

    pep8 : bool, optional
        Turn on PEP8 checking via the pytest-pep8 plugin and disable normal
        tests. Same as specifying `--pep8 -k pep8` in `args`.

    pdb : bool, optional
        Turn on PDB post-mortem analysis for failing tests. Same as
        specifying `--pdb` in `args`.

    coverage : bool, optional
        Generate a test coverage report.  The result will be placed in
        the directory htmlcov.

    open_files : bool, optional
        Fail when any tests leave files open.  Off by default, because
        this adds extra run time to the test suite.  Works only on
        platforms with a working `lsof` command.

    parallel : int, optional
        When provided, run the tests in parallel on the specified
        number of CPUs.  If parallel is negative, it will use the all
        the cores on the machine.  Requires the `pytest-xdist` plugin
        is installed. Only available when using Astropy 0.3 or later.

    kwargs
        Any additional keywords passed into this function will be passed
        on to the astropy test runner.  This allows use of test-related
        functionality implemented in later versions of astropy without
        explicitly updating the package template.

    See Also
    --------
    pytest.main : py.test function wrapped by `run_tests`.

    """
    test_runner = _get_test_runner()
    return test_runner.run_tests(
        package=package, test_path=test_path, args=args,
        plugins=plugins, verbose=verbose, pastebin=pastebin,
        remote_data=remote_data, pep8=pep8, pdb=pdb,
        coverage=coverage, open_files=open_files, **kwargs)

if not _ASTROPY_SETUP_:

    import os
    from warnings import warn
    from astropy import config

    # add these here so we only need to cleanup the namespace at the end
    config_dir = None

    if not os.environ.get('ASTROPY_SKIP_CONFIG_UPDATE', False):
        config_dir = os.path.dirname(__file__)
        try:
            config.configuration.update_default_config(__package__, config_dir)
        except config.configuration.ConfigurationDefaultMissingError as e:
            wmsg = (e.args[0] + " Cannot install default profile. If you are "
                    "importing from source, this is expected.")
            warn(config.configuration.ConfigurationDefaultMissingWarning(wmsg))
            del e

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst
#
# Astropy documentation build configuration file.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this file.
#
# All configuration values have a default. Some values are defined in
# the global Astropy configuration which is loaded here before anything else.
# See astropy.sphinx.conf for which values are set there.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('..'))
# IMPORTANT: the above commented section was generated by sphinx-quickstart, but
# is *NOT* appropriate for astropy or Astropy affiliated packages. It is left
# commented out with this explanation to make it clear why this should not be
# done. If the sys.path entry above is added, when the astropy.sphinx.conf
# import occurs, it will import the *source* version of astropy instead of the
# version installed (if invoked as "make html" or directly with sphinx), or the
# version in the build directory (if "python setup.py build_sphinx" is used).
# Thus, any C-extensions that are needed to build the documentation will *not*
# be accessible, and the documentation will not build correctly.

import datetime
import os
import sys

# Load all of the global Astropy configuration
from astropy.sphinx.conf import *

# Get configuration information from setup.cfg
from distutils import config
conf = config.ConfigParser()
conf.read([os.path.join(os.path.dirname(__file__), '..', 'setup.cfg')])
setup_cfg = dict(conf.items('metadata'))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.1'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns.append('_templates')

# This is added to the end of RST files - a good place to put substitutions to
# be used globally.
rst_epilog += """
"""

# -- Project information ------------------------------------------------------

# This does not *have* to match the package name, but typically does
project = setup_cfg['package_name']
author = setup_cfg['author']
copyright = '{0}, {1}'.format(
    datetime.datetime.now().year, setup_cfg['author'])

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

__import__(setup_cfg['package_name'])
package = sys.modules[setup_cfg['package_name']]

# The short X.Y version.
version = package.__version__.split('-', 1)[0]
# The full version, including alpha/beta/rc tags.
release = package.__version__


# -- Options for HTML output ---------------------------------------------------

# A NOTE ON HTML THEMES
# The global astropy configuration uses a custom theme, 'bootstrap-astropy',
# which is installed along with astropy. A different theme can be used or
# the options for this theme can be modified by overriding some of the
# variables set in the global configuration. The variables set in the
# global configuration are listed below, commented out.

# Add any paths that contain custom themes here, relative to this directory.
# To use a different custom theme, add the directory containing the theme.
#html_theme_path = []

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes. To override the custom theme, set this to the
# name of a builtin theme or the name of a custom theme in html_theme_path.
#html_theme = None

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = ''

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = ''

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = '{0} v{1}'.format(project, release)

# Output file base name for HTML help builder.
htmlhelp_basename = project + 'doc'

html_logo = 'aplpy_logo.png'


# -- Options for LaTeX output --------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [('index', project + '.tex', project + u' Documentation',
                    author, 'manual')]


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [('index', project.lower(), project + u' Documentation',
              [author], 1)]


## -- Options for the edit_on_github extension ----------------------------------------

if eval(setup_cfg.get('edit_on_github')):
    extensions += ['astropy.sphinx.ext.edit_on_github']

    versionmod = __import__(setup_cfg['package_name'] + '.version')
    edit_on_github_project = setup_cfg['github_project']
    if versionmod.release:
        edit_on_github_branch = "v" + versionmod.version
    else:
        edit_on_github_branch = "master"

    edit_on_github_source_root = ""
    edit_on_github_doc_root = "docs"

########NEW FILE########
