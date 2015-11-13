__FILENAME__ = mandelplot
import numpy as np
import mandel
x = np.linspace(-1.7, 0.6, 1000)
y = np.linspace(-1.4, 1.4, 1000)
c = x[None,:] + 1j*y[:,None]
z = mandel.mandel(c, c)

import matplotlib.pyplot as plt
plt.imshow(abs(z)**2 < 1000, extent=[-1.7, 0.6, -1.4, 1.4])
plt.gray()
plt.show()

########NEW FILE########
__FILENAME__ = myobject_test
#
# Compile myobject.c first with
#
#    python3 setup_myobject.py build_ext -i
#
# If you are interested, play a bit with changing things in ``myobject.c``
#

import myobject

obj = myobject.MyObject()
view = memoryview(obj)

print("shape", view.shape)
print("strides", view.strides)
print("format", view.format)


#
# If you also have Numpy for Python 3 ...
#

import numpy as np

x = np.asarray(obj)
print(x)

# this prints
#
# [[1 2]
#  [3 4]]

########NEW FILE########
__FILENAME__ = pilbuffer-answer
import numpy as np
import Image

# Let's make a sample image, RGBA format

x = np.zeros((200, 200, 4), dtype=np.int8)

x[:,:,0] = 254 # red
x[:,:,3] = 255 # opaque

data = x.view(np.int32) # Check that you understand why this is OK!

img = Image.frombuffer("RGBA", (200, 200), data)
img.save('test.png')

#
# Modify the original data, and save again.
#
# It turns out that PIL, which knows next to nothing about Numpy,
# happily shares the same data.
#

x[:,:,1] = 254
img.save('test2.png')

########NEW FILE########
__FILENAME__ = pilbuffer
import numpy as np
import Image

# Let's make a sample image, RGBA format

x = np.zeros((200, 200, 4), dtype=np.int8)

TODO: fill `x` with fully opaque red [255, 0, 0, 255]

TODO: RGBA images consist of 32-bit integers whose bytes are [RR,GG,BB,AA]
      How to get that from ``x``?

data = ...

img = Image.frombuffer("RGBA", (200, 200), data)
img.save('test.png')

#
# Mini-exercise
#
# 1. Now, modify ``x`` and img.save() again. What happens?
#

########NEW FILE########
__FILENAME__ = stride-diagonals-answer
import numpy as np
from numpy.lib.stride_tricks import as_strided

#
# Part 1
#

x = np.array([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]], dtype=np.int32)

x_diag = as_strided(x, shape=(3,), strides=((3+1)*x.itemsize,))
x_supdiag = as_strided(x[0,1:], shape=(2,), strides=((3+1)*x.itemsize,))
x_subdiag = as_strided(x[1:,0], shape=(2,), strides=((3+1)*x.itemsize,))

print x_diag
print x_supdiag
print x_subdiag

#
# Mini-exercise: (assume C memory order)
#
# 0. How to pick diagonal entries of the matrix
#
# 1. How to pick the super-diagonal entries [2, 6]
#
# 2. The sub-diagonal entries [4, 8]
#
# 99. Can you generalize this for any stride and shape combinations
#     in the initial array?
#
#     If you can, tell me, and maybe numpy.trace can be made faster :)
#


#
# Part 2
#

# Compute the tensor trace

x = np.arange(5*5*5*5).reshape(5,5,5,5)

s = 0
for i in xrange(5):
    for j in xrange(5):
        s += x[j,i,j,i]

# by striding and using .sum()

y = as_strided(x, shape=(5, 5), strides=((5*5*5+5)*x.itemsize,
                                         (5*5+1)*x.itemsize))
s2 = y.sum()

assert s == s2

########NEW FILE########
__FILENAME__ = stride-diagonals
import numpy as np
from numpy.lib.stride_tricks import as_strided

#
# Part 1
#

x = np.array([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]], dtype=np.int32)

x_diag = as_strided(x, shape=(3,), strides=(TODO,))
x_supdiag = TODO
x_subdiag = TODO

#
# Mini-exercise: (assume C memory order)
#
# 0. How to pick diagonal entries of the matrix
#
# 1. How to pick the super-diagonal entries [2, 6]
#
# 2. The sub-diagonal entries [4, 8]
#
# 99. Can you generalize this for any stride and shape combinations
#     in the initial array?
#
#     If you can, tell me, and maybe numpy.trace can be made faster :)
#


#
# Part 2
#

# Compute the tensor trace

x = np.arange(5*5*5*5).reshape(5,5,5,5)

s = 0
for i in xrange(5):
    for j in xrange(5):
        s += x[j,i,j,i]

# by striding and using .sum()

y = as_strided(x, shape=(5, 5), strides=(TODO, TODO))
s2 = ...

assert s == s2

########NEW FILE########
__FILENAME__ = stride-fakedims
import numpy as np
from numpy.lib.stride_tricks import as_strided

x = np.array([1, 2, 3, 4], dtype=np.int8)

#
# Mini-exercise:
#
# 1. How to create a new array that shares the data, but looks like
#
#    array([[1, 2, 3, 4],
#           [1, 2, 3, 4],
#           [1, 2, 3, 4]], dtype=int8)
#

########NEW FILE########
__FILENAME__ = stride_tricks
"""
Utilities that manipulate strides to achieve desirable effects.














"""
import numpy as np

__all__ = ['broadcast_arrays']

class DummyArray(object):
    """ Dummy object that just exists to hang __array_interface__ dictionaries
    and possibly keep alive a reference to a base array.
    """
    def __init__(self, interface, base=None):
        self.__array_interface__ = interface
        self.base = base

def as_strided(x, shape=None, strides=None):
    """ Make an ndarray from the given array with the given shape and strides.
    """
    interface = dict(x.__array_interface__)
    if shape is not None:
        interface['shape'] = tuple(shape)
    if strides is not None:
        interface['strides'] = tuple(strides)
    return np.asarray(DummyArray(interface, base=x))

def broadcast_arrays(*args):
    """
    Broadcast any number of arrays against each other.

    Parameters
    ----------
    `*args` : arrays
        The arrays to broadcast.

    Returns
    -------
    broadcasted : list of arrays
        These arrays are views on the original arrays. They are typically not
        contiguous. Furthermore, more than one element of a broadcasted array
        may refer to a single memory location. If you need to write to the
        arrays, make copies first.

    Examples
    --------
    >>> x = np.array([[1,2,3]])
    >>> y = np.array([[1],[2],[3]])
    >>> np.broadcast_arrays(x, y)
    [array([[1, 2, 3],
           [1, 2, 3],
           [1, 2, 3]]), array([[1, 1, 1],
           [2, 2, 2],
           [3, 3, 3]])]

    Here is a useful idiom for getting contiguous copies instead of
    non-contiguous views.

    >>> map(np.array, np.broadcast_arrays(x, y))
    [array([[1, 2, 3],
           [1, 2, 3],
           [1, 2, 3]]), array([[1, 1, 1],
           [2, 2, 2],
           [3, 3, 3]])]

    """
    args = map(np.asarray, args)
    shapes = [x.shape for x in args]
    if len(set(shapes)) == 1:
        # Common case where nothing needs to be broadcasted.
        return args
    shapes = [list(s) for s in shapes]
    strides = [list(x.strides) for x in args]
    nds = [len(s) for s in shapes]
    biggest = max(nds)
    # Go through each array and prepend dimensions of length 1 to each of the
    # shapes in order to make the number of dimensions equal.
    for i in range(len(args)):
        diff = biggest - nds[i]
        if diff > 0:
            shapes[i] = [1] * diff + shapes[i]
            strides[i] = [0] * diff + strides[i]
    # Chech each dimension for compatibility. A dimension length of 1 is
    # accepted as compatible with any other length.
    common_shape = []
    for axis in range(biggest):
        lengths = [s[axis] for s in shapes]
        unique = set(lengths + [1])
        if len(unique) > 2:
            # There must be at least two non-1 lengths for this axis.
            raise ValueError("shape mismatch: two or more arrays have "
                "incompatible dimensions on axis %r." % (axis,))
        elif len(unique) == 2:
            # There is exactly one non-1 length. The common shape will take this
            # value.
            unique.remove(1)
            new_length = unique.pop()
            common_shape.append(new_length)
            # For each array, if this axis is being broadcasted from a length of
            # 1, then set its stride to 0 so that it repeats its data.
            for i in range(len(args)):
                if shapes[i][axis] == 1:
                    shapes[i][axis] = new_length
                    strides[i][axis] = 0
        else:
            # Every array has a length of 1 on this axis. Strides can be left
            # alone as nothing is broadcasted.
            common_shape.append(1)

    # Construct the new arrays.
    broadcasted = [as_strided(x, shape=sh, strides=st) for (x,sh,st) in
        zip(args, shapes, strides)]
    return broadcasted

########NEW FILE########
__FILENAME__ = view-colors
x = np.zeros((10, 10, 4), dtype=np.int8)
x[:,:,0] = 1
x[:,:,1] = 2
x[:,:,2] = 3
x[:,:,3] = 4

# How to make a (10, 10) structured array with fields 'r', 'g', 'b', 'a',
# without copying?

y = ...

assert (y['r'] == 1).all()
assert (y['g'] == 2).all()
assert (y['b'] == 3).all()
assert (y['a'] == 4).all()

########NEW FILE########
__FILENAME__ = wavreader
import sys
import numpy as np

wav_header_dtype = np.dtype([
     ("chunk_id", (str, 4)),   # flexible-sized scalar type, item size 4
     ("chunk_size", "<u4"),    # little-endian unsigned 32-bit integer
     ("format", "S4"),         # 4-byte string
     ("fmt_id", "S4"),
     ("fmt_size", "<u4"),
     ("audio_fmt", "<u2"),     #
     ("num_channels", "<u2"),  # .. more of the same ...
     ("sample_rate", "<u4"),   #
     ("byte_rate", "<u4"),
     ("block_align", "<u2"),
     ("bits_per_sample", "<u2"),
     ("data_id", ("S1", (2, 2))), # sub-array! **MUST** be fixed-size
     ("data_size", "u4"),
     #
     # the sound data itself cannot be represented here:
     # it does not have a fixed size
])

print wav_header_dtype.fields

# Mini-exercise: Rewrite the above by supplying only the ``sample_rate`` and 
#                ``num_channels`` fields.
#
#  wav_header_dtype = np.dtype(dict(
#      names=['format', 'sample_rate', 'data_id'],
#      offsets= list of offsets in bytes, from start of structure
#      formats= list of dtypes for each field,
#  ))


f = open(sys.argv[1], 'r')
wav_header = np.fromfile(f, dtype=wav_header_dtype, count=1)
f.close()

print "Sample rate: %d, channels: %d" % (
    wav_header['sample_rate'][0],
    wav_header['num_channels'][0]
    )

########NEW FILE########
__FILENAME__ = debug_file
"""Script to read in a column of numbers and calculate the min, max and sum.

Data is stored in data.txt.
"""

def parse_data(data_string):
    data = []
    for x in data_string.split('.'):
        data.append(x)
    return data

def load_data(filename):
    fp = open(filename)
    data_string = fp.read()
    fp.close()
    return parse_data(data_string)

if __name__ == '__main__':
    data = load_data('exercises/data.txt')
    print('min: %f' % min(data)) # 10.20
    print('max: %f' % max(data)) # 61.30

########NEW FILE########
__FILENAME__ = index_error
"""Small snippet to raise an IndexError."""

def index_error():
    lst = list('foobar')
    print lst[len(lst)]

if __name__ == '__main__':
    index_error()


########NEW FILE########
__FILENAME__ = segfault
""" Simple code that creates a segfault using numpy. Used to learn
debugging segfaults with GDB.
"""

import numpy as np
from numpy.lib import stride_tricks

def make_big_array(small_array):
    big_array = stride_tricks.as_strided(small_array,
                                         shape=(2e6, 2e6), strides=(32, 32))
    return big_array

def print_big_array(small_array):
    big_array = make_big_array(small_array)
    print big_array[-10:]
    return big_array


l = list()
for i in range(10):
    a = np.arange(8)
    l.append(print_big_array(a))

########NEW FILE########
__FILENAME__ = to_debug
"""
A script to compare different root-finding algorithms.

This version of the script is buggy and does not execute. It is your task
to find an fix these bugs.

The output of the script sould look like:

    Benching 1D root-finder optimizers from scipy.optimize:
                brenth:   604678 total function calls
                brentq:   594454 total function calls
                ridder:   778394 total function calls
                bisect:  2148380 total function calls
"""
from itertools import product

import numpy as np
from scipy import optimize

FUNCTIONS = (np.tan,  # Dilating map
             np.tanh, # Contracting map
             lambda x: x**3 + 1e-4*x, # Almost null gradient at the root
             lambda x: x+np.sin(2*x), # Non monotonous function
             lambda x: 1.1*x+np.sin(4*x), # Fonction with several local maxima
            )

OPTIMIZERS = (optimize.brenth, optimize.brentq, optimize.ridder,
              optimize.bisect)


def apply_optimizer(optimizer, func, a, b):
    """ Return the number of function calls given an root-finding optimizer, 
        a function and upper and lower bounds.
    """
    return optimizer(func, a, b, full_output=True)[1].function_calls,


def bench_optimizer(optimizer, param_grid):
    """ Find roots for all the functions, and upper and lower bounds
        given and return the total number of function calls.
    """
    return sum(apply_optimizer(optimizer, func, a, b)
               for func, a, b in param_grid)


def compare_optimizers(optimizers):
    """ Compare all the optimizers given on a grid of a few different
        functions all admitting a signle root in zero and a upper and
        lower bounds.
    """
    random_a = -1.3 + np.random.random(size=100)
    random_b =   .3 + np.random.random(size=100)
    param_grid = product(FUNCTIONS, random_a, random_b)
    print "Benching 1D root-finder optimizers from scipy.optimize:"
    for optimizer in OPTIMIZERS:
        print '% 20s: % 8i total function calls' % (
                    optimizer.__name__, 
                    bench_optimizer(optimizer, param_grid)
                )


if __name__ == '__main__':
    compare_optimizers(OPTIMIZERS)

########NEW FILE########
__FILENAME__ = wiener_filtering
""" Wiener filtering a noisy Lena: this module is buggy
"""

import numpy as np
import scipy as sp
import pylab as pl
from scipy import signal


def local_mean(img, size=3):
    """ Compute a image of the local average
    """
    structure_element = np.ones((size, size), dtype=img.dtype)
    l_mean = signal.correlate(img, structure_element, mode='same')
    l_mean /= size**2
    return l_mean


def local_var(img, size=3):
    """ Compute a image of the local variance
    """
    structure_element = np.ones((size, size), dtype=img.dtype)
    l_var = signal.correlate(img**2, structure_element, mode='same')
    l_var /= size**2
    l_var -= local_mean(img, size=size)**2
    return l_var


def iterated_wiener(noisy_img, size=3):
    """ Wiener filter with iterative computation of the noise variance.

        Do not use this: this is crappy code to demo bugs!
    """
    noisy_img = noisy_img
    denoised_img = local_mean(noisy_img, size=size)
    l_var = local_var(noisy_img, size=size)
    for i in range(3):
        res = noisy_img - denoised_img
        noise = (res**2).sum()/res.size
        noise_level = (1 - noise/l_var )
        noise_level[noise_level<0] = 0
        denoised_img += noise_level*res
    return denoised_img


################################################################################
cut = (slice(128, -128), slice(128, -128))

np.random.seed(7)

lena = sp.misc.lena()
noisy_lena = lena + 20*np.random.randint(3, size=lena.shape) - 30

pl.matshow(lena[cut], cmap=pl.cm.gray)
pl.matshow(noisy_lena[cut], cmap=pl.cm.gray)

denoised_lena = iterated_wiener(noisy_lena)
pl.matshow(denoised_lena[cut], cmap=pl.cm.gray)

pl.show()


########NEW FILE########
__FILENAME__ = image_source_canny
'''canny.py - Canny Edge detector

Reference: Canny, J., A Computational Approach To Edge Detection, IEEE Trans.
    Pattern Analysis and Machine Intelligence, 8:679-714, 1986

Originally part of CellProfiler, code licensed under both GPL and BSD licenses.
Website: http://www.cellprofiler.org
Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2011 Broad Institute
All rights reserved.
Original author: Lee Kamentsky

'''

import numpy as np
import scipy.ndimage as ndi
from scipy.ndimage import (gaussian_filter, convolve,
                           generate_binary_structure, binary_erosion, label)


def smooth_with_function_and_mask(image, function, mask):
    """Smooth an image with a linear function, ignoring masked pixels

    Parameters
    ----------
    image : array
      The image to smooth
    
    function : callable
      A function that takes an image and returns a smoothed image
    
    mask : array
      Mask with 1's for significant pixels, 0 for masked pixels

    Notes
    ------
    This function calculates the fractional contribution of masked pixels
    by applying the function to the mask (which gets you the fraction of
    the pixel data that's due to significant points). We then mask the image
    and apply the function. The resulting values will be lower by the bleed-over
    fraction, so you can recalibrate by dividing by the function on the mask
    to recover the effect of smoothing from just the significant pixels.
    """
    not_mask = np.logical_not(mask)
    bleed_over = function(mask.astype(float))
    masked_image = np.zeros(image.shape, image.dtype)
    masked_image[mask] = image[mask]
    smoothed_image = function(masked_image)
    output_image = smoothed_image / (bleed_over + np.finfo(float).eps)
    return output_image


def canny(image, sigma, low_threshold, high_threshold, mask=None):
    '''Edge filter an image using the Canny algorithm.

    Parameters
    -----------
    image : array_like, dtype=float
      The greyscale input image to detect edges on; should be normalized to 0.0
      to 1.0.
    
    sigma : float
      The standard deviation of the Gaussian filter
    
    low_threshold : float
      The lower bound for hysterisis thresholding (linking edges)

    high_threshold : float
      The upper bound for hysterisis thresholding (linking edges)

    mask : array, dtype=bool, optional
      An optional mask to limit the application of Canny to a certain area.

    Returns
    -------
    output : array (image)
      The binary edge map.

    References
    -----------
    Canny, J., A Computational Approach To Edge Detection, IEEE Trans.
    Pattern Analysis and Machine Intelligence, 8:679-714, 1986
    
    William Green's Canny tutorial
    http://www.pages.drexel.edu/~weg22/can_tut.html
    '''
    #
    # The steps involved:
    #
    # * Smooth using the Gaussian with sigma above.
    #
    # * Apply the horizontal and vertical Sobel operators to get the gradients
    #   within the image. The edge strength is the sum of the magnitudes
    #   of the gradients in each direction.
    #
    # * Find the normal to the edge at each point using the arctangent of the
    #   ratio of the Y sobel over the X sobel - pragmatically, we can
    #   look at the signs of X and Y and the relative magnitude of X vs Y
    #   to sort the points into 4 categories: horizontal, vertical,
    #   diagonal and antidiagonal.
    #
    # * Look in the normal and reverse directions to see if the values
    #   in either of those directions are greater than the point in question.
    #   Use interpolation to get a mix of points instead of picking the one
    #   that's the closest to the normal.
    #
    # * Label all points above the high threshold as edges.
    # * Recursively label any point above the low threshold that is 8-connected
    #   to a labeled point as an edge.
    #
    # Regarding masks, any point touching a masked point will have a gradient
    # that is "infected" by the masked point, so it's enough to erode the
    # mask by one and then mask the output. We also mask out the border points
    # because who knows what lies beyond the edge of the image?
    #
    if mask is None:
        mask = np.ones(image.shape, dtype=bool)
    fsmooth = lambda x: gaussian_filter(x, sigma, mode='constant')
    smoothed = smooth_with_function_and_mask(image, fsmooth, mask)
    jsobel = ndi.sobel(smoothed, axis=1)
    isobel = ndi.sobel(smoothed, axis=0)
    abs_isobel = np.abs(isobel)
    abs_jsobel = np.abs(jsobel)
    magnitude = np.hypot(isobel, jsobel)

    #
    # Make the eroded mask. Setting the border value to zero will wipe
    # out the image edges for us.
    #
    s = generate_binary_structure(2, 2)
    eroded_mask = binary_erosion(mask, s, border_value=0)
    eroded_mask = eroded_mask & (magnitude > 0)
    #
    #--------- Find local maxima --------------
    #
    # Assign each point to have a normal of 0-45 degrees, 45-90 degrees,
    # 90-135 degrees and 135-180 degrees.
    #
    local_maxima = np.zeros(image.shape,bool)
    #----- 0 to 45 degrees ------
    pts_plus = (isobel >= 0) & (jsobel >= 0) & (abs_isobel >= abs_jsobel)
    pts_minus = (isobel <= 0) & (jsobel <= 0) & (abs_isobel >= abs_jsobel)
    pts = pts_plus | pts_minus
    pts = eroded_mask & pts
    # Get the magnitudes shifted left to make a matrix of the points to the
    # right of pts. Similarly, shift left and down to get the points to the
    # top right of pts.
    c1 = magnitude[1:, :][pts[:-1, :]]
    c2 = magnitude[1:, 1:][pts[:-1, :-1]]
    m = magnitude[pts]
    w = abs_jsobel[pts] / abs_isobel[pts]
    c_plus = c2 * w + c1 * (1 - w) <= m
    c1 = magnitude[:-1, :][pts[1:, :]]
    c2 = magnitude[:-1, :-1][pts[1:, 1:]]
    c_minus = c2 * w + c1 * (1 - w) <= m
    local_maxima[pts] = c_plus & c_minus
    #----- 45 to 90 degrees ------
    # Mix diagonal and vertical
    #
    pts_plus = (isobel >= 0) & (jsobel >= 0) & (abs_isobel <= abs_jsobel)
    pts_minus = (isobel <= 0) & (jsobel <= 0) & (abs_isobel <= abs_jsobel)
    pts = pts_plus | pts_minus
    pts = eroded_mask & pts
    c1 = magnitude[:, 1:][pts[:, :-1]]
    c2 = magnitude[1:, 1:][pts[:-1, :-1]]
    m = magnitude[pts]
    w = abs_isobel[pts] / abs_jsobel[pts]
    c_plus = c2 * w + c1 * (1 - w) <= m
    c1 = magnitude[:, :-1][pts[:, 1:]]
    c2 = magnitude[:-1, :-1][pts[1:, 1:]]
    c_minus = c2 * w + c1 * (1 - w) <= m
    local_maxima[pts] = c_plus & c_minus
    #----- 90 to 135 degrees ------
    # Mix anti-diagonal and vertical
    #
    pts_plus = (isobel <= 0) & (jsobel >= 0) & (abs_isobel <= abs_jsobel)
    pts_minus = (isobel >= 0) & (jsobel <= 0) & (abs_isobel <= abs_jsobel)
    pts = pts_plus | pts_minus
    pts = eroded_mask & pts
    c1a = magnitude[:, 1:][pts[:, :-1]]
    c2a = magnitude[:-1, 1:][pts[1:, :-1]]
    m = magnitude[pts]
    w = abs_isobel[pts] / abs_jsobel[pts]
    c_plus = c2a * w + c1a * (1.0 - w) <= m
    c1 = magnitude[:, :-1][pts[:, 1:]]
    c2 = magnitude[1:, :-1][pts[:-1, 1:]]
    c_minus = c2 * w + c1 * (1.0 - w) <= m
    cc = np.logical_and(c_plus,c_minus)
    local_maxima[pts] = c_plus & c_minus
    #----- 135 to 180 degrees ------
    # Mix anti-diagonal and anti-horizontal
    #
    pts_plus = (isobel <= 0) & (jsobel >= 0) & (abs_isobel >= abs_jsobel)
    pts_minus = (isobel >= 0) & (jsobel <= 0) & (abs_isobel >= abs_jsobel)
    pts = pts_plus | pts_minus
    pts = eroded_mask & pts
    c1 = magnitude[:-1, :][pts[1:, :]]
    c2 = magnitude[:-1, 1:][pts[1:, :-1]]
    m = magnitude[pts]
    w = abs_jsobel[pts] / abs_isobel[pts]
    c_plus = c2 * w + c1 * (1 - w) <= m
    c1 = magnitude[1:, :][pts[:-1, :]]
    c2 = magnitude[1:,:-1][pts[:-1,1:]]
    c_minus = c2 * w + c1 * (1 - w) <= m
    local_maxima[pts] = c_plus & c_minus
    #
    #---- Create two masks at the two thresholds.
    #
    high_mask = local_maxima & (magnitude >= high_threshold)
    low_mask = local_maxima & (magnitude >= low_threshold)
    #
    # Segment the low-mask, then only keep low-segments that have
    # some high_mask component in them
    #
    labels,count = label(low_mask, np.ndarray((3, 3),bool))
    if count == 0:
        return low_mask
    
    sums = (np.array(ndi.sum(high_mask,labels,
                             np.arange(count,dtype=np.int32) + 1),
                     copy=False, ndmin=1))
    good_label = np.zeros((count + 1,),bool)
    good_label[1:] = sums > 0
    output_mask = good_label[labels]
    return output_mask

########NEW FILE########
__FILENAME__ = plot_block_mean
import numpy as np
import scipy
from scipy import ndimage
import matplotlib.pyplot as plt

l = scipy.misc.lena()
sx, sy = l.shape
X, Y = np.ogrid[0:sx, 0:sy]

regions = sy/6 * (X/4) + Y/6
block_mean = ndimage.mean(l, labels=regions,
                          index=np.arange(1, regions.max() +1))
block_mean.shape = (sx/4, sy/6)

plt.figure(figsize=(5, 5))
plt.imshow(block_mean, cmap=plt.cm.gray)
plt.axis('off')

plt.show()


########NEW FILE########
__FILENAME__ = plot_blur
import scipy
from scipy import ndimage
import matplotlib.pyplot as plt

lena = scipy.misc.lena()
blurred_lena = ndimage.gaussian_filter(lena, sigma=3)
very_blurred = ndimage.gaussian_filter(lena, sigma=5)
local_mean = ndimage.uniform_filter(lena, size=11)

plt.figure(figsize=(9, 3))
plt.subplot(131)
plt.imshow(blurred_lena, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(132)
plt.imshow(very_blurred, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(133)
plt.imshow(local_mean, cmap=plt.cm.gray)
plt.axis('off')

plt.subplots_adjust(wspace=0, hspace=0., top=0.99, bottom=0.01,
                    left=0.01, right=0.99)

plt.show()

########NEW FILE########
__FILENAME__ = plot_canny
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
#from scikits.image.filter import canny
from image_source_canny import canny

im = np.zeros((256, 256))
im[64:-64, 64:-64] = 1

im = ndimage.rotate(im, 15, mode='constant')
im = ndimage.gaussian_filter(im, 8)

im += 0.1*np.random.random(im.shape)

edges = canny(im, 1, 0.4, 0.2)

plt.figure(figsize=(12, 4))

plt.subplot(131)
plt.imshow(im, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(132)
plt.imshow(edges, cmap=plt.cm.gray)
plt.axis('off')


edges = canny(im, 3, 0.3, 0.2)
plt.subplot(133)
plt.imshow(edges, cmap=plt.cm.gray)
plt.axis('off')

plt.subplots_adjust(wspace=0.02, hspace=0.02, top=1, bottom=0, left=0, right=1)

plt.show()

########NEW FILE########
__FILENAME__ = plot_clean_morpho
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
from sklearn.mixture import GMM

np.random.seed(1)
n = 10
l = 256
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))

mask = (im > im.mean()).astype(np.float)


img = mask + 0.3*np.random.randn(*mask.shape)

binary_img = img > 0.5

# Remove small white regions
open_img = ndimage.binary_opening(binary_img)
# Remove small black hole
close_img = ndimage.binary_closing(open_img)

plt.figure(figsize=(12, 3))

l = 128

plt.subplot(141)
plt.imshow(binary_img[:l, :l], cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(142)
plt.imshow(open_img[:l, :l], cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(143)
plt.imshow(close_img[:l, :l], cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(144)
plt.imshow(mask[:l, :l], cmap=plt.cm.gray)
plt.contour(close_img[:l, :l], [0.5], linewidths=2, colors='r')
plt.axis('off')

plt.subplots_adjust(wspace=0.02, hspace=0.3, top=1, bottom=0.1, left=0, right=1)

plt.show()


########NEW FILE########
__FILENAME__ = plot_denoising
import numpy as np
import scipy
from scipy import ndimage
import matplotlib.pyplot as plt

im = np.zeros((20, 20))
im[5:-5, 5:-5] = 1
im = ndimage.distance_transform_bf(im)
im_noise = im + 0.2*np.random.randn(*im.shape)

im_med = ndimage.median_filter(im_noise, 3)

plt.figure(figsize=(16, 5))

plt.subplot(141)
plt.imshow(im, interpolation='nearest')
plt.axis('off')
plt.title('Original image', fontsize=20)
plt.subplot(142)
plt.imshow(im_noise, interpolation='nearest', vmin=0, vmax=5)
plt.axis('off')
plt.title('Noisy image', fontsize=20)
plt.subplot(143)
plt.imshow(im_med, interpolation='nearest', vmin=0, vmax=5)
plt.axis('off')
plt.title('Median filter', fontsize=20)
plt.subplot(144)
plt.imshow(np.abs(im - im_med), cmap=plt.cm.hot, interpolation='nearest')
plt.axis('off')
plt.title('Error', fontsize=20)


plt.subplots_adjust(wspace=0.02, hspace=0.02, top=0.9, bottom=0, left=0, right=1)

plt.show()

########NEW FILE########
__FILENAME__ = plot_display_lena
import scipy
import matplotlib.pyplot as plt

l = scipy.misc.lena()

plt.figure(figsize=(10, 3.6))

plt.subplot(131)
plt.imshow(l, cmap=plt.cm.gray)

plt.subplot(132)
plt.imshow(l, cmap=plt.cm.gray, vmin=30, vmax=200)
plt.axis('off')

plt.subplot(133)
plt.imshow(l, cmap=plt.cm.gray)
plt.contour(l, [60, 211])
plt.axis('off')

plt.subplots_adjust(wspace=0, hspace=0., top=0.99, bottom=0.01, left=0.05,
                    right=0.99)
plt.show()

########NEW FILE########
__FILENAME__ = plot_find_edges
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

im = np.zeros((256, 256))
im[64:-64, 64:-64] = 1

im = ndimage.rotate(im, 15, mode='constant')
im = ndimage.gaussian_filter(im, 8)

sx = ndimage.sobel(im, axis=0, mode='constant')
sy = ndimage.sobel(im, axis=1, mode='constant')
sob = np.hypot(sx, sy)

plt.figure(figsize=(16, 5))
plt.subplot(141)
plt.imshow(im, cmap=plt.cm.gray)
plt.axis('off')
plt.title('square', fontsize=20)
plt.subplot(142)
plt.imshow(sx)
plt.axis('off')
plt.title('Sobel (x direction)', fontsize=20)
plt.subplot(143)
plt.imshow(sob)
plt.axis('off')
plt.title('Sobel filter', fontsize=20)

im += 0.07*np.random.random(im.shape)

sx = ndimage.sobel(im, axis=0, mode='constant')
sy = ndimage.sobel(im, axis=1, mode='constant')
sob = np.hypot(sx, sy)

plt.subplot(144)
plt.imshow(sob)
plt.axis('off')
plt.title('Sobel for noisy image', fontsize=20)



plt.subplots_adjust(wspace=0.02, hspace=0.02, top=1, bottom=0, left=0, right=0.9)

plt.show()

########NEW FILE########
__FILENAME__ = plot_find_object
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

np.random.seed(1)
n = 10
l = 256
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))

mask = im > im.mean()

label_im, nb_labels = ndimage.label(mask)

sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
mask_size = sizes < 1000
remove_pixel = mask_size[label_im]
label_im[remove_pixel] = 0
labels = np.unique(label_im)
label_im = np.searchsorted(labels, label_im)

slice_x, slice_y = ndimage.find_objects(label_im==4)[0]
roi = im[slice_x, slice_y]

plt.figure(figsize=(4, 2))
plt.axes([0, 0, 1, 1])
plt.imshow(roi)
plt.axis('off')

plt.show()

########NEW FILE########
__FILENAME__ = plot_geom_lena
import numpy as np
import scipy
from scipy import ndimage
import matplotlib.pyplot as plt

lena = scipy.misc.lena()
lx, ly = lena.shape
# Copping
crop_lena = lena[lx/4:-lx/4, ly/4:-ly/4]
# up <-> down flip
flip_ud_lena = np.flipud(lena)
# rotation
rotate_lena = ndimage.rotate(lena, 45)
rotate_lena_noreshape = ndimage.rotate(lena, 45, reshape=False)

plt.figure(figsize=(12.5, 2.5))


plt.subplot(151)
plt.imshow(lena, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(152)
plt.imshow(crop_lena, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(153)
plt.imshow(flip_ud_lena, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(154)
plt.imshow(rotate_lena, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(155)
plt.imshow(rotate_lena_noreshape, cmap=plt.cm.gray)
plt.axis('off')

plt.subplots_adjust(wspace=0.02, hspace=0.3, top=1, bottom=0.1, left=0,
                    right=1)

plt.show()

########NEW FILE########
__FILENAME__ = plot_GMM
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
from sklearn.mixture import GMM

np.random.seed(1)
n = 10
l = 256
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))

mask = (im > im.mean()).astype(np.float)


img = mask + 0.3*np.random.randn(*mask.shape)

hist, bin_edges = np.histogram(img, bins=60)
bin_centers = 0.5*(bin_edges[:-1] + bin_edges[1:])

classif = GMM(n_components=2)
classif.fit(img.reshape((img.size, 1)))

threshold = np.mean(classif.means_)
binary_img = img > threshold


plt.figure(figsize=(11,4))

plt.subplot(131)
plt.imshow(img)
plt.axis('off')
plt.subplot(132)
plt.plot(bin_centers, hist, lw=2)
plt.axvline(0.5, color='r', ls='--', lw=2)
plt.text(0.57, 0.8, 'histogram', fontsize=20, transform = plt.gca().transAxes)
plt.yticks([])
plt.subplot(133)
plt.imshow(binary_img, cmap=plt.cm.gray, interpolation='nearest')
plt.axis('off')

plt.subplots_adjust(wspace=0.02, hspace=0.3, top=1, bottom=0.1, left=0, right=1)
plt.show()

########NEW FILE########
__FILENAME__ = plot_granulo
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

def disk_structure(n):
    struct = np.zeros((2 * n + 1, 2 * n + 1))
    x, y = np.indices((2 * n + 1, 2 * n + 1))
    mask = (x - n)**2 + (y - n)**2 <= n**2
    struct[mask] = 1
    return struct.astype(np.bool)


def granulometry(data, sizes=None):
    s = max(data.shape)
    if sizes == None:
        sizes = range(1, s/2, 2)
    granulo = [ndimage.binary_opening(data, \
            structure=disk_structure(n)).sum() for n in sizes]
    return granulo


np.random.seed(1)
n = 10
l = 256
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))

mask = im > im.mean()

granulo = granulometry(mask, sizes=np.arange(2, 19, 4))

plt.figure(figsize=(6, 2.2))

plt.subplot(121)
plt.imshow(mask, cmap=plt.cm.gray)
opened = ndimage.binary_opening(mask, structure=disk_structure(10))
opened_more = ndimage.binary_opening(mask, structure=disk_structure(14))
plt.contour(opened, [0.5], colors='b', linewidths=2)
plt.contour(opened_more, [0.5], colors='r', linewidths=2)
plt.axis('off')
plt.subplot(122)
plt.plot(np.arange(2, 19, 4), granulo, 'ok', ms=8)


plt.subplots_adjust(wspace=0.02, hspace=0.15, top=0.95, bottom=0.15, left=0, right=0.95)
plt.show()

########NEW FILE########
__FILENAME__ = plot_greyscale_dilation
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

im = np.zeros((64, 64))
np.random.seed(2)
x, y = (63*np.random.random((2, 8))).astype(np.int)
im[x, y] = np.arange(8)

bigger_points = ndimage.grey_dilation(im, size=(5, 5), structure=np.ones((5, 5)))

square = np.zeros((16, 16))
square[4:-4, 4:-4] = 1
dist = ndimage.distance_transform_bf(square)
dilate_dist = ndimage.grey_dilation(dist, size=(3, 3), \
        structure=np.ones((3, 3)))

plt.figure(figsize=(12.5, 3))
plt.subplot(141)
plt.imshow(im, interpolation='nearest', cmap=plt.cm.spectral)
plt.axis('off')
plt.subplot(142)
plt.imshow(bigger_points, interpolation='nearest', cmap=plt.cm.spectral)
plt.axis('off')
plt.subplot(143)
plt.imshow(dist, interpolation='nearest', cmap=plt.cm.spectral)
plt.axis('off')
plt.subplot(144)
plt.imshow(dilate_dist, interpolation='nearest', cmap=plt.cm.spectral)
plt.axis('off')

plt.subplots_adjust(wspace=0, hspace=0.02, top=0.99, bottom=0.01, left=0.01, right=0.99)
plt.show()

########NEW FILE########
__FILENAME__ = plot_histo_segmentation
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

np.random.seed(1)
n = 10
l = 256
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))

mask = (im > im.mean()).astype(np.float)

mask += 0.1 * im

img = mask + 0.2*np.random.randn(*mask.shape)

hist, bin_edges = np.histogram(img, bins=60)
bin_centers = 0.5*(bin_edges[:-1] + bin_edges[1:])

binary_img = img > 0.5

plt.figure(figsize=(11,4))

plt.subplot(131)
plt.imshow(img)
plt.axis('off')
plt.subplot(132)
plt.plot(bin_centers, hist, lw=2)
plt.axvline(0.5, color='r', ls='--', lw=2)
plt.text(0.57, 0.8, 'histogram', fontsize=20, transform = plt.gca().transAxes)
plt.yticks([])
plt.subplot(133)
plt.imshow(binary_img, cmap=plt.cm.gray, interpolation='nearest')
plt.axis('off')

plt.subplots_adjust(wspace=0.02, hspace=0.3, top=1, bottom=0.1, left=0, right=1)
plt.show()

########NEW FILE########
__FILENAME__ = plot_interpolation_lena
import scipy
import matplotlib.pyplot as plt

l = scipy.misc.lena()

plt.figure(figsize=(8, 4))

plt.subplot(121)
plt.imshow(l[200:220, 200:220], cmap=plt.cm.gray)
plt.axis('off')

plt.subplot(122)
plt.imshow(l[200:220, 200:220], cmap=plt.cm.gray, interpolation='nearest')
plt.axis('off')

plt.subplots_adjust(wspace=0.02, hspace=0.02, top=1, bottom=0, left=0, right=1)
plt.show()

########NEW FILE########
__FILENAME__ = plot_lena
""" Small example to plot lena."""
from scipy import misc
l = misc.lena()
misc.imsave('lena.png', l) # uses the Image module (PIL)

import matplotlib.pyplot as plt
plt.imshow(l)
plt.show()

########NEW FILE########
__FILENAME__ = plot_lena_denoise
import numpy as np
import scipy
from scipy import ndimage
import matplotlib.pyplot as plt

l = scipy.misc.lena()
l = l[230:290, 220:320]

noisy = l + 0.4*l.std()*np.random.random(l.shape)

gauss_denoised = ndimage.gaussian_filter(noisy, 2)
med_denoised = ndimage.median_filter(noisy, 3)


plt.figure(figsize=(12,2.8))

plt.subplot(131)
plt.imshow(noisy, cmap=plt.cm.gray, vmin=40, vmax=220)
plt.axis('off')
plt.title('noisy', fontsize=20)
plt.subplot(132)
plt.imshow(gauss_denoised, cmap=plt.cm.gray, vmin=40, vmax=220)
plt.axis('off')
plt.title('Gaussian filter', fontsize=20)
plt.subplot(133)
plt.imshow(med_denoised, cmap=plt.cm.gray, vmin=40, vmax=220)
plt.axis('off')
plt.title('Median filter', fontsize=20)

plt.subplots_adjust(wspace=0.02, hspace=0.02, top=0.9, bottom=0, left=0,
                    right=1)
plt.show()

########NEW FILE########
__FILENAME__ = plot_lena_tv_denoise
import numpy as np
import scipy
import matplotlib.pyplot as plt
from skimage.filter import denoise_tv_chambolle

l = scipy.misc.lena()
l = l[230:290, 220:320]

noisy = l + 0.4*l.std()*np.random.random(l.shape)

tv_denoised = denoise_tv_chambolle(noisy, weight=10)


plt.figure(figsize=(12, 2.8))

plt.subplot(131)
plt.imshow(noisy, cmap=plt.cm.gray, vmin=40, vmax=220)
plt.axis('off')
plt.title('noisy', fontsize=20)
plt.subplot(132)
plt.imshow(tv_denoised, cmap=plt.cm.gray, vmin=40, vmax=220)
plt.axis('off')
plt.title('TV denoising', fontsize=20)

tv_denoised = denoise_tv_chambolle(noisy, weight=50)
plt.subplot(133)
plt.imshow(tv_denoised, cmap=plt.cm.gray, vmin=40, vmax=220)
plt.axis('off')
plt.title('(more) TV denoising', fontsize=20)

plt.subplots_adjust(wspace=0.02, hspace=0.02, top=0.9, bottom=0, left=0,
                    right=1)
plt.show()

########NEW FILE########
__FILENAME__ = plot_measure_data
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

np.random.seed(1)
n = 10
l = 256
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))

mask = im > im.mean()

label_im, nb_labels = ndimage.label(mask)

sizes = ndimage.sum(mask, label_im, range(nb_labels + 1))
mask_size = sizes < 1000
remove_pixel = mask_size[label_im]
label_im[remove_pixel] = 0
labels = np.unique(label_im)
label_clean = np.searchsorted(labels, label_im)


plt.figure(figsize=(6 ,3))

plt.subplot(121)
plt.imshow(label_im, cmap=plt.cm.spectral)
plt.axis('off')
plt.subplot(122)
plt.imshow(label_clean, vmax=nb_labels, cmap=plt.cm.spectral)
plt.axis('off')

plt.subplots_adjust(wspace=0.01, hspace=0.01, top=1, bottom=0, left=0, right=1)
plt.show()

########NEW FILE########
__FILENAME__ = plot_numpy_array
import numpy as np
import scipy
import matplotlib.pyplot as plt

lena = scipy.misc.lena()
lena[10:13, 20:23]
lena[100:120] = 255

lx, ly = lena.shape
X, Y = np.ogrid[0:lx, 0:ly]
mask = (X - lx/2)**2 + (Y - ly/2)**2 > lx*ly/4
lena[mask] = 0
lena[range(400), range(400)] = 255

plt.figure(figsize=(3, 3))
plt.axes([0, 0, 1, 1])
plt.imshow(lena, cmap=plt.cm.gray)
plt.axis('off')

plt.show()

########NEW FILE########
__FILENAME__ = plot_propagation
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

square = np.zeros((32, 32))
square[10:-10, 10:-10] = 1
np.random.seed(2)
x, y = (32*np.random.random((2, 20))).astype(np.int)
square[x, y] = 1

open_square = ndimage.binary_opening(square)

eroded_square = ndimage.binary_erosion(square)
reconstruction = ndimage.binary_propagation(eroded_square, mask=square)

plt.figure(figsize=(9.5, 3))
plt.subplot(131)
plt.imshow(square, cmap=plt.cm.gray, interpolation='nearest')
plt.axis('off')
plt.subplot(132)
plt.imshow(open_square, cmap=plt.cm.gray, interpolation='nearest')
plt.axis('off')
plt.subplot(133)
plt.imshow(reconstruction, cmap=plt.cm.gray, interpolation='nearest')
plt.axis('off')

plt.subplots_adjust(wspace=0, hspace=0.02, top=0.99, bottom=0.01, left=0.01, right=0.99)
plt.show()



########NEW FILE########
__FILENAME__ = plot_radial_mean
import numpy as np
import scipy
from scipy import ndimage
import matplotlib.pyplot as plt

l = scipy.misc.lena()
sx, sy = l.shape
X, Y = np.ogrid[0:sx, 0:sy]


r = np.hypot(X - sx/2, Y - sy/2)

rbin = (20* r/r.max()).astype(np.int)
radial_mean = ndimage.mean(l, labels=rbin, index=np.arange(1, rbin.max() +1))

plt.figure(figsize=(5, 5))
plt.axes([0, 0, 1, 1])
plt.imshow(rbin, cmap=plt.cm.spectral)
plt.axis('off')

plt.show()

########NEW FILE########
__FILENAME__ = plot_sharpen
import scipy
from scipy import ndimage
import matplotlib.pyplot as plt

l = scipy.misc.lena()
blurred_l = ndimage.gaussian_filter(l, 3)

filter_blurred_l = ndimage.gaussian_filter(blurred_l, 1)

alpha = 30
sharpened = blurred_l + alpha * (blurred_l - filter_blurred_l)

plt.figure(figsize=(12, 4))

plt.subplot(131)
plt.imshow(l, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(132)
plt.imshow(blurred_l, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(133)
plt.imshow(sharpened, cmap=plt.cm.gray)
plt.axis('off')

plt.show()

########NEW FILE########
__FILENAME__ = plot_spectral_clustering
import numpy as np
import matplotlib.pyplot as plt

from sklearn.feature_extraction import image
from sklearn.cluster import spectral_clustering

################################################################################
l = 100
x, y = np.indices((l, l))

center1 = (28, 24)
center2 = (40, 50)
center3 = (67, 58)
center4 = (24, 70)

radius1, radius2, radius3, radius4 = 16, 14, 15, 14

circle1 = (x - center1[0])**2 + (y - center1[1])**2 < radius1**2
circle2 = (x - center2[0])**2 + (y - center2[1])**2 < radius2**2
circle3 = (x - center3[0])**2 + (y - center3[1])**2 < radius3**2
circle4 = (x - center4[0])**2 + (y - center4[1])**2 < radius4**2

################################################################################
# 4 circles
img = circle1 + circle2 + circle3 + circle4
mask = img.astype(bool)
img = img.astype(float)

img += 1 + 0.2*np.random.randn(*img.shape)

# Convert the image into a graph with the value of the gradient on the
# edges.
graph = image.img_to_graph(img, mask=mask)

# Take a decreasing function of the gradient: we take it weakly
# dependant from the gradient the segmentation is close to a voronoi
graph.data = np.exp(-graph.data / graph.data.std())

# Force the solver to be arpack, since amg is numerically
# unstable on this example
labels = spectral_clustering(graph, n_clusters=4)
label_im = -np.ones(mask.shape)
label_im[mask] = labels

plt.figure(figsize=(6, 3))
plt.subplot(121)
plt.imshow(img, cmap=plt.cm.spectral, interpolation='nearest')
plt.axis('off')
plt.subplot(122)
plt.imshow(label_im, cmap=plt.cm.spectral, interpolation='nearest')
plt.axis('off')

plt.subplots_adjust(wspace=0, hspace=0., top=0.99, bottom=0.01, left=0.01, right=0.99)
plt.show()

########NEW FILE########
__FILENAME__ = plot_synthetic_data
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

np.random.seed(1)
n = 10
l = 256
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))

mask = im > im.mean()

label_im, nb_labels = ndimage.label(mask)

plt.figure(figsize=(9,3))

plt.subplot(131)
plt.imshow(im)
plt.axis('off')
plt.subplot(132)
plt.imshow(mask, cmap=plt.cm.gray)
plt.axis('off')
plt.subplot(133)
plt.imshow(label_im, cmap=plt.cm.spectral)
plt.axis('off')

plt.subplots_adjust(wspace=0.02, hspace=0.02, top=1, bottom=0, left=0, right=1)
plt.show()

########NEW FILE########
__FILENAME__ = plot_watershed_segmentation
import numpy as np
from skimage.morphology import watershed
from skimage.feature import peak_local_max
import matplotlib.pyplot as plt
from scipy import ndimage

# Generate an initial image with two overlapping circles
x, y = np.indices((80, 80))
x1, y1, x2, y2 = 28, 28, 44, 52
r1, r2 = 16, 20
mask_circle1 = (x - x1) ** 2 + (y - y1) ** 2 < r1 ** 2
mask_circle2 = (x - x2) ** 2 + (y - y2) ** 2 < r2 ** 2
image = np.logical_or(mask_circle1, mask_circle2)
# Now we want to separate the two objects in image
# Generate the markers as local maxima of the distance
# to the background
distance = ndimage.distance_transform_edt(image)
local_maxi = peak_local_max(
    distance, indices=False, footprint=np.ones((3, 3)), labels=image)
markers = ndimage.label(local_maxi)[0]
labels = watershed(-distance, markers, mask=image)

plt.figure(figsize=(9, 3.5))
plt.subplot(131)
plt.imshow(image, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.subplot(132)
plt.imshow(-distance, interpolation='nearest')
plt.axis('off')
plt.subplot(133)
plt.imshow(labels, cmap='spectral', interpolation='nearest')
plt.axis('off')

plt.subplots_adjust(hspace=0.01, wspace=0.01, top=1, bottom=0, left=0,
                    right=1)
plt.show()

########NEW FILE########
__FILENAME__ = tv_denoise
import numpy as np

def _tv_denoise_3d(im, weight=100, eps=2.e-4, keep_type=False, n_iter_max=200):
    """
    Perform total-variation denoising on 3-D arrays

    Parameters
    ----------
    im: ndarray
        3-D input data to be denoised

    weight: float, optional
        denoising weight. The greater ``weight``, the more denoising (at
        the expense of fidelity to ``input``)

    eps: float, optional
        relative difference of the value of the cost function that determines
        the stop criterion. The algorithm stops when:

            (E_(n-1) - E_n) < eps * E_0

    keep_type: bool, optional (False)
        whether the output has the same dtype as the input array.
        keep_type is False by default, and the dtype of the output
        is np.float

    n_iter_max: int, optional
        maximal number of iterations used for the optimization.

    Returns
    -------
    out: ndarray
        denoised array

    Notes
    -----
    Rudin, Osher and Fatemi algorithm

    Examples
    ---------
    First build synthetic noisy data
    >>> x, y, z = np.ogrid[0:40, 0:40, 0:40]
    >>> mask = (x -22)**2 + (y - 20)**2 + (z - 17)**2 < 8**2
    >>> mask = mask.astype(np.float)
    >>> mask += 0.2*np.random.randn(*mask.shape)
    >>> res = tv_denoise_3d(mask, weight=100)
    """
    im_type = im.dtype
    if im_type is not np.float:
        im = im.astype(np.float)
    px = np.zeros_like(im)
    py = np.zeros_like(im)
    pz = np.zeros_like(im)
    gx = np.zeros_like(im)
    gy = np.zeros_like(im)
    gz = np.zeros_like(im)
    d = np.zeros_like(im)
    i = 0
    while i < n_iter_max:
        d = - px - py - pz
        d[1:] += px[:-1] 
        d[:, 1:] += py[:, :-1] 
        d[:, :, 1:] += pz[:, :, :-1] 
        
        out = im + d
        E = (d**2).sum()

        gx[:-1] = np.diff(out, axis=0) 
        gy[:, :-1] = np.diff(out, axis=1) 
        gz[:, :, :-1] = np.diff(out, axis=2) 
        norm = np.sqrt(gx**2 + gy**2 + gz**2)
        E += weight * norm.sum()
        norm *= 0.5 / weight
        norm += 1.
        px -= 1./6.*gx
        px /= norm
        py -= 1./6.*gy
        py /= norm
        pz -= 1/6.*gz
        pz /= norm
        E /= float(im.size)
        if i == 0:
            E_init = E
            E_previous = E
        else:
            if np.abs(E_previous - E) < eps * E_init:
                break
            else:
                E_previous = E
        i += 1
    if keep_type:
        return out.astype(im_type)
    else:
        return out

def _tv_denoise_2d(im, weight=50, eps=2.e-4, keep_type=False, n_iter_max=200):
    """
    Perform total-variation denoising

    Parameters
    ----------
    im: ndarray
        input data to be denoised

    weight: float, optional
        denoising weight. The greater ``weight``, the more denoising (at 
        the expense of fidelity to ``input``) 

    eps: float, optional
        relative difference of the value of the cost function that determines
        the stop criterion. The algorithm stops when:

            (E_(n-1) - E_n) < eps * E_0

    keep_type: bool, optional (False)
        whether the output has the same dtype as the input array. 
        keep_type is False by default, and the dtype of the output
        is np.float

    n_iter_max: int, optional
        maximal number of iterations used for the optimization.

    Returns
    -------
    out: ndarray
        denoised array

    Notes
    -----
    The principle of total variation denoising is explained in
    http://en.wikipedia.org/wiki/Total_variation_denoising

    This code is an implementation of the algorithm of Rudin, Fatemi and Osher
    that was proposed by Chambolle in [1]_.

    References
    ----------

    .. [1] A. Chambolle, An algorithm for total variation minimization and
           applications, Journal of Mathematical Imaging and Vision,
           Springer, 2004, 20, 89-97.

    Examples
    ---------
    >>> import scipy
    >>> lena = scipy.misc.lena().astype(np.float)
    >>> lena += 0.5 * lena.std()*np.random.randn(*lena.shape)
    >>> denoised_lena = tv_denoise(lena, weight=60.0)
    """
    im_type = im.dtype
    if im_type is not np.float:
        im = im.astype(np.float)
    px = np.zeros_like(im)
    py = np.zeros_like(im)
    gx = np.zeros_like(im)
    gy = np.zeros_like(im)
    d = np.zeros_like(im)
    i = 0
    while i < n_iter_max:
        d = -px -py
        d[1:] += px[:-1]
        d[:, 1:] += py[:, :-1]

        out = im + d
        E = (d**2).sum()
        gx[:-1] = np.diff(out, axis=0)
        gy[:, :-1] = np.diff(out, axis=1)
        norm = np.sqrt(gx**2 + gy**2)
        E += weight * norm.sum()
        norm *= 0.5 / weight
        norm += 1
        px -= 0.25*gx
        px /= norm
        py -= 0.25*gy
        py /= norm
        E /= float(im.size)
        if i == 0:
            E_init = E
            E_previous = E
        else:
            if np.abs(E_previous - E) < eps * E_init:
                break
            else:
                E_previous = E
        i += 1
    if keep_type:
        return out.astype(im_type)
    else:
        return out

def tv_denoise(im, weight=50, eps=2.e-4, keep_type=False, n_iter_max=200):
    """
    Perform total-variation denoising on 2-d and 3-d images

    Parameters
    ----------
    im: ndarray (2d or 3d) of ints, uints or floats
        input data to be denoised. `im` can be of any numeric type,
        but it is cast into an ndarray of floats for the computation
        of the denoised image.

    weight: float, optional
        denoising weight. The greater ``weight``, the more denoising (at
        the expense of fidelity to ``input``)

    eps: float, optional
        relative difference of the value of the cost function that 
        determines the stop criterion. The algorithm stops when:

            (E_(n-1) - E_n) < eps * E_0

    keep_type: bool, optional (False)
        whether the output has the same dtype as the input array.
        keep_type is False by default, and the dtype of the output
        is np.float

    n_iter_max: int, optional
        maximal number of iterations used for the optimization.

    Returns
    -------
    out: ndarray
        denoised array


    Notes
    -----
    The principle of total variation denoising is explained in
    http://en.wikipedia.org/wiki/Total_variation_denoising

    The principle of total variation denoising is to minimize the
    total variation of the image, which can be roughly described as 
    the integral of the norm of the image gradient. Total variation 
    denoising tends to produce "cartoon-like" images, that is, 
    piecewise-constant images.

    This code is an implementation of the algorithm of Rudin, Fatemi and Osher 
    that was proposed by Chambolle in [1]_.

    References
    ----------

    .. [1] A. Chambolle, An algorithm for total variation minimization and 
           applications, Journal of Mathematical Imaging and Vision, 
           Springer, 2004, 20, 89-97.

    Examples
    ---------
    >>> import scipy
    >>> # 2D example using lena
    >>> lena = scipy.misc.lena().astype(np.float)
    >>> lena += 0.5 * lena.std()*np.random.randn(*lena.shape)
    >>> denoised_lena = tv_denoise(lena, weight=60)
    >>> # 3D example on synthetic data
    >>> x, y, z = np.ogrid[0:40, 0:40, 0:40]
    >>> mask = (x -22)**2 + (y - 20)**2 + (z - 17)**2 < 8**2
    >>> mask = mask.astype(np.float)
    >>> mask += 0.2*np.random.randn(*mask.shape)
    >>> res = tv_denoise_3d(mask, weight=100)
    """

    if im.ndim == 2:
        return _tv_denoise_2d(im, weight, eps, keep_type, n_iter_max)
    elif im.ndim == 3:
        return _tv_denoise_3d(im, weight, eps, keep_type, n_iter_max)
    else:
        raise ValueError('only 2-d and 3-d images may be denoised with this function')


########NEW FILE########
__FILENAME__ = cos_module
""" Example of wrapping cos function from math.h using ctypes. """

import ctypes
from ctypes.util import find_library

# find and load the library
libm = ctypes.cdll.LoadLibrary(find_library('m'))
# set the argument type
libm.cos.argtypes = [ctypes.c_double]
# set the return type
libm.cos.restype = ctypes.c_double


def cos_func(arg):
    ''' Wrapper for cos from math.h '''
    return libm.cos(arg)

########NEW FILE########
__FILENAME__ = cos_doubles
""" Example of wrapping a C library function that accepts a C double array as
    input using the numpy.ctypeslib. """

import numpy as np
import numpy.ctypeslib as npct
from ctypes import c_int

# input type for the cos_doubles function
# must be a double array, with single dimension that is contiguous
array_1d_double = npct.ndpointer(dtype=np.double, ndim=1, flags='CONTIGUOUS')

# load the library, using numpy mechanisms
libcd = npct.load_library("libcos_doubles", ".")

# setup the return typs and argument types
libcd.cos_doubles.restype = None
libcd.cos_doubles.argtypes = [array_1d_double, array_1d_double, c_int]


def cos_doubles_func(in_array, out_array):
    return libcd.cos_doubles(in_array, out_array, len(in_array))

########NEW FILE########
__FILENAME__ = test_cos_doubles
../numpy_shared/test_cos_doubles.py
########NEW FILE########
__FILENAME__ = test_cos_doubles
../numpy_shared/test_cos_doubles.py
########NEW FILE########
__FILENAME__ = test_cos_module_np
import cos_module_np
import numpy as np
import pylab

x = np.arange(0, 2 * np.pi, 0.1)
y = cos_module_np.cos_func_np(x)
pylab.plot(x, y)
pylab.show()

########NEW FILE########
__FILENAME__ = test_cos_doubles
import numpy as np
import pylab
import cos_doubles

x = np.arange(0, 2 * np.pi, 0.1)
y = np.empty_like(x)

cos_doubles.cos_doubles_func(x, y)
pylab.plot(x, y)
pylab.show()

########NEW FILE########
__FILENAME__ = test_cos_doubles
../numpy_shared/test_cos_doubles.py
########NEW FILE########
__FILENAME__ = compare_optimizers
"""
Comparison of optimizers on various problems.
"""
import functools
import pickle

import numpy as np
from scipy import optimize
from joblib import Memory

from cost_functions import mk_quad, mk_gauss, rosenbrock,\
    rosenbrock_prime, rosenbrock_hessian, LoggingFunction, \
    CountingFunction

def my_partial(function, **kwargs):
    f = functools.partial(function, **kwargs)
    functools.update_wrapper(f, function)
    return f

methods = {
    'Nelder-mead':          my_partial(optimize.fmin,
                                        ftol=1e-12, maxiter=5e3,
                                        xtol=1e-7, maxfun=1e6),
    'Powell':               my_partial(optimize.fmin_powell,
                                        ftol=1e-9, maxiter=5e3,
                                        maxfun=1e7),
    'BFGS':                 my_partial(optimize.fmin_bfgs,
                                        gtol=1e-9, maxiter=5e3),
    'Newton':               my_partial(optimize.fmin_ncg,
                                        avextol=1e-7, maxiter=5e3),
    'Conjugate gradient':   my_partial(optimize.fmin_cg,
                                        gtol=1e-7, maxiter=5e3),
    'L-BFGS':               my_partial(optimize.fmin_l_bfgs_b,
                                        approx_grad=1, factr=10.0,
                                        pgtol=1e-8, maxfun=1e7),
    "L-BFGS w f'":               my_partial(optimize.fmin_l_bfgs_b,
                                        factr=10.0,
                                        pgtol=1e-8, maxfun=1e7),
}

###############################################################################

def bencher(cost_name, ndim, method_name, x0):
    cost_function = mk_costs(ndim)[0][cost_name][0]
    method = methods[method_name]
    f = LoggingFunction(cost_function)
    method(f, x0)
    this_costs = np.array(f.all_f_i)
    return this_costs


# Bench with gradients
def bencher_gradient(cost_name, ndim, method_name, x0):
    cost_function, cost_function_prime, hessian = mk_costs(ndim)[0][cost_name]
    method = methods[method_name]
    f_prime = CountingFunction(cost_function_prime)
    f = LoggingFunction(cost_function, counter=f_prime.counter)
    method(f, x0, f_prime)
    this_costs = np.array(f.all_f_i)
    return this_costs, np.array(f.counts)


# Bench with the hessian
def bencher_hessian(cost_name, ndim, method_name, x0):
    cost_function, cost_function_prime, hessian = mk_costs(ndim)[0][cost_name]
    method = methods[method_name]
    f_prime = CountingFunction(cost_function_prime)
    hessian = CountingFunction(hessian, counter=f_prime.counter)
    f = LoggingFunction(cost_function, counter=f_prime.counter)
    method(f, x0, f_prime, fhess=hessian)
    this_costs = np.array(f.all_f_i)
    return this_costs, np.array(f.counts)


def mk_costs(ndim=2):
    costs = {
            'Well-conditioned quadratic':      mk_quad(.7, ndim=ndim),
            'Ill-conditioned quadratic':       mk_quad(.02, ndim=ndim),
            'Well-conditioned Gaussian':       mk_gauss(.7, ndim=ndim),
            'Ill-conditioned Gaussian':        mk_gauss(.02, ndim=ndim),
            'Rosenbrock  ':   (rosenbrock, rosenbrock_prime, rosenbrock_hessian),
        }

    rng = np.random.RandomState(0)
    starting_points = 4*rng.rand(20, ndim) - 2
    if ndim > 100:
        starting_points = starting_points[:10]
    return costs, starting_points

###############################################################################
# Compare methods without gradient
mem = Memory('.', verbose=3)

if 1:
    gradient_less_benchs = dict()

    for ndim in (2, 8, 32, 128):
        this_dim_benchs = dict()
        costs, starting_points = mk_costs(ndim)
        for cost_name, cost_function in costs.iteritems():
            # We don't need the derivative or the hessian
            cost_function = cost_function[0]
            function_bench = dict()
            for x0 in starting_points:
                all_bench = list()
                # Bench gradient-less
                for method_name, method in methods.iteritems():
                    if method_name in ('Newton', "L-BFGS w f'"):
                        continue
                    this_bench = function_bench.get(method_name, list())
                    this_costs = mem.cache(bencher)(cost_name, ndim,
                                                    method_name, x0)
                    if np.all(this_costs > .25*ndim**2*1e-9):
                        convergence = 2*len(this_costs)
                    else:
                        convergence = np.where(
                                        np.diff(this_costs > .25*ndim**2*1e-9)
                                    )[0].max() + 1
                    this_bench.append(convergence)
                    all_bench.append(convergence)
                    function_bench[method_name] = this_bench

                # Bench with gradients
                for method_name, method in methods.iteritems():
                    if method_name in ('Newton', 'Powell', 'Nelder-mead',
                                       "L-BFGS"):
                        continue
                    this_method_name = method_name
                    if method_name.endswith(" w f'"):
                        this_method_name = method_name[:-4]
                    this_method_name = this_method_name + "\nw f'"
                    this_bench = function_bench.get(this_method_name, list())
                    this_costs, this_counts = mem.cache(bencher_gradient)(
                                        cost_name, ndim, method_name, x0)
                    if np.all(this_costs > .25*ndim**2*1e-9):
                        convergence = 2*this_counts.max()
                    else:
                        convergence = np.where(
                                        np.diff(this_costs > .25*ndim**2*1e-9)
                                        )[0].max() + 1
                        convergence = this_counts[convergence]
                    this_bench.append(convergence)
                    all_bench.append(convergence)
                    function_bench[this_method_name] = this_bench

                # Bench Newton with Hessian
                method_name = 'Newton'
                this_bench = function_bench.get(method_name, list())
                this_costs = mem.cache(bencher_hessian)(cost_name, ndim,
                                                method_name, x0)
                if np.all(this_costs > .25*ndim**2*1e-9):
                    convergence = 2*len(this_costs)
                else:
                    convergence = np.where(
                                    np.diff(this_costs > .25*ndim**2*1e-9)
                                )[0].max() + 1
                this_bench.append(convergence)
                all_bench.append(convergence)
                function_bench[method_name + '\nw Hessian '] = this_bench

                # Normalize across methods
                x0_mean = np.mean(all_bench)
                for method_name in function_bench:
                    function_bench[method_name][-1] /= x0_mean
            this_dim_benchs[cost_name] = function_bench
        gradient_less_benchs[ndim] = this_dim_benchs
        print 80*'_'
        print 'Done cost %s, ndim %s' % (cost_name, ndim)
        print 80*'_'

    pickle.dump(gradient_less_benchs, file('compare_optimizers.pkl', 'w'))



########NEW FILE########
__FILENAME__ = cost_functions
"""
Example cost functions or objective functions to optimize.
"""
import numpy as np

###############################################################################
# Gaussian functions with varying conditionning

def gaussian(x):
    return np.exp(-np.sum(x**2))


def gaussian_prime(x):
    return -2*x*np.exp(-np.sum(x**2))


def gaussian_prime_prime(x):
    return -2*np.exp(-x**2) + 4*x**2*np.exp(-x**2)


def mk_gauss(epsilon, ndim=2):
    def f(x):
        x = np.asarray(x)
        y = x.copy()
        y *= np.power(epsilon, np.arange(ndim))
        return -gaussian(.5*y) + 1

    def f_prime(x):
        x = np.asarray(x)
        y = x.copy()
        scaling = np.power(epsilon, np.arange(ndim))
        y *= scaling
        return -.5*scaling*gaussian_prime(.5*y)

    def hessian(x):
        epsilon = .07
        x = np.asarray(x)
        y = x.copy()
        scaling = np.power(epsilon, np.arange(ndim))
        y *= .5*scaling
        H = -.25*np.ones((ndim, ndim))*gaussian(y)
        d = 4*y*y[:, np.newaxis]
        d.flat[::ndim+1] += -2
        H *= d
        return H

    return f, f_prime, hessian

###############################################################################
# Quadratic functions with varying conditionning

def mk_quad(epsilon, ndim=2):
    def f(x):
       x = np.asarray(x)
       y = x.copy()
       y *= np.power(epsilon, np.arange(ndim))
       return .33*np.sum(y**2)

    def f_prime(x):
       x = np.asarray(x)
       y = x.copy()
       scaling = np.power(epsilon, np.arange(ndim))
       y *= scaling
       return .33*2*scaling*y

    def hessian(x):
       scaling = np.power(epsilon, np.arange(ndim))
       return .33*2*np.diag(scaling)

    return f, f_prime, hessian


###############################################################################
# Super ill-conditionned problem: the Rosenbrock function

def rosenbrock(x):
    y = 4*x
    y[0] += 1
    y[1:] += 3
    return np.sum(.5*(1 - y[:-1])**2 + (y[1:] - y[:-1]**2)**2)


def rosenbrock_prime(x):
    y = 4*x
    y[0] += 1
    y[1:] += 3
    xm = y[1:-1]
    xm_m1 = y[:-2]
    xm_p1 = y[2:]
    der = np.zeros_like(y)
    der[1:-1] = 2*(xm - xm_m1**2) - 4*(xm_p1 - xm**2)*xm - .5*2*(1 - xm)
    der[0] = -4*y[0]*(y[1] - y[0]**2) - .5*2*(1 - y[0])
    der[-1] = 2*(y[-1] - y[-2]**2)
    return 4*der


def rosenbrock_hessian_(x):
    x, y = x
    x = 4*x + 1
    y = 4*y + 3
    return 4*4*np.array((
                    (1 - 4*y + 12*x**2, -4*x),
                    (             -4*x,    2),
                   ))


def rosenbrock_hessian(x):
    y = 4*x
    y[0] += 1
    y[1:] += 3

    H = np.diag(-4*y[:-1], 1) - np.diag(4*y[:-1], -1)
    diagonal = np.zeros_like(y)
    diagonal[0] = 12*y[0]**2 - 4*y[1] + 2*.5
    diagonal[-1] = 2
    diagonal[1:-1] = 3 + 12*y[1:-1]**2 - 4*y[2:]*.5
    H = H + np.diag(diagonal)
    return 4*4*H


###############################################################################
# Helpers to wrap the functions

class LoggingFunction(object):

    def __init__(self, function, counter=None):
        self.function = function
        if counter is None:
            counter = list()
        self.counter = counter
        self.all_x_i = list()
        self.all_y_i = list()
        self.all_f_i = list()
        self.counts = list()

    def __call__(self, x0):
        x_i, y_i = x0[:2]
        self.all_x_i.append(x_i)
        self.all_y_i.append(y_i)
        f_i = self.function(np.asarray(x0))
        self.all_f_i.append(f_i)
        self.counter.append('f')
        self.counts.append(len(self.counter))
        return f_i

class CountingFunction(object):

    def __init__(self, function, counter=None):
        self.function = function
        if counter is None:
            counter = list()
        self.counter = counter

    def __call__(self, x0):
        self.counter.append('f_prime')
        return self.function(x0)




########NEW FILE########
__FILENAME__ = plot_1d_optim
"""
Illustration of 1D optimization: Brent's method
"""

import numpy as np
import pylab as pl
from scipy import optimize

x = np.linspace(-1, 3, 100)
x_0 = np.exp(-1)

def f(x):
    return (x - x_0)**2 + epsilon*np.exp(-5*(x - .5 - x_0)**2)

for epsilon in (0, 1):
    pl.figure(figsize=(3, 2.5))
    pl.axes([0, 0, 1, 1])

    # A convex function
    pl.plot(x, f(x), linewidth=2)

    # Apply brent method. To have access to the iteration, do this in an
    # artificial way: allow the algorithm to iter only once
    all_x = list()
    all_y = list()
    for iter in range(30):
        out = optimize.brent(f, brack=(-5, 2.9, 4.5), maxiter=iter,
                             full_output=True,
                             tol=np.finfo(1.).eps)
        if iter != out[-2]:
            print 'Converged at ', iter
            break
        this_x = out[0]
        all_x.append(this_x)
        all_y.append(f(this_x))
        if iter < 6:
            pl.text(this_x - .05*np.sign(this_x) - .05,
                    f(this_x) + 1.2*(.3 - iter % 2), iter + 1,
                    size=12)

    pl.plot(all_x[:10], all_y[:10], 'k+', markersize=12, markeredgewidth=2)

    pl.plot(all_x[-1], all_y[-1], 'rx', markersize=12)
    pl.axis('off')
    pl.ylim(ymin=-1, ymax=8)

    pl.figure(figsize=(4, 3))
    pl.semilogy(np.abs(all_y - all_y[-1]), linewidth=2)
    pl.ylabel('Error on f(x)')
    pl.xlabel('Iteration')
    pl.tight_layout()

pl.show()


########NEW FILE########
__FILENAME__ = plot_compare_optimizers
import pickle

import numpy as np
import pylab as pl

results = pickle.load(file('compare_optimizers.pkl'))
#results = pickle.load(file('compare_optimizers_gradients.pkl'))
n_methods = len(results.values()[0]['Rosenbrock  '])
n_dims = len(results)

symbols = 'o>*Ds'

pl.figure(1, figsize=(10, 4))
pl.clf()

colors = pl.cm.Spectral(np.linspace(0, 1, n_dims))[:, :3]

method_names = results.values()[0]['Rosenbrock  '].keys()
method_names.sort(key=lambda x: x[::-1], reverse=True)

for n_dim_index, ((n_dim, n_dim_bench), color) in enumerate(
            zip(sorted(results.items()), colors)):
    for (cost_name, cost_bench), symbol in zip(sorted(n_dim_bench.items()),
                    symbols):
        for method_index, method_name, in enumerate(method_names):
            this_bench = cost_bench[method_name]
            bench = np.mean(this_bench)
            pl.semilogy([method_index + .1*n_dim_index, ], [bench, ],
                    marker=symbol, color=color)

# Create a legend for the problem type
for cost_name, symbol in zip(sorted(n_dim_bench.keys()),
            symbols):
    pl.semilogy([-10, ], [0, ], symbol, color='.5',
            label=cost_name)

pl.xticks(np.arange(n_methods), method_names, size=11)
pl.xlim(-.2, n_methods - .5)
pl.legend(loc='best', numpoints=1, handletextpad=0, prop=dict(size=12),
          frameon=False)
pl.ylabel('# function calls (a.u.)')

# Create a second legend for the problem dimensionality
pl.twinx()

for n_dim, color in zip(sorted(results.keys()), colors):
    pl.plot([-10, ], [0, ], 'o', color=color,
            label='# dim: %i' % n_dim)
pl.legend(loc=(.47, .07), numpoints=1, handletextpad=0, prop=dict(size=12),
          frameon=False, ncol=2)
pl.xlim(-.2, n_methods - .5)

pl.xticks(np.arange(n_methods), method_names)
pl.yticks(())

pl.tight_layout()
pl.show()



########NEW FILE########
__FILENAME__ = plot_constraints
"""
Optimization with constraints
"""
import numpy as np
import pylab as pl
from scipy import optimize

x, y = np.mgrid[-2.9:5.8:.05, -2.5:5:.05]
x = x.T
y = y.T

for i in (1, 2):
    # Create 2 figure: only the second one will have the optimization
    # path
    pl.figure(i, figsize=(3, 2.5))
    pl.clf()
    pl.axes([0, 0, 1, 1])

    contours = pl.contour(np.sqrt((x - 3)**2 + (y - 2)**2),
                        extent=[-3, 6, -2.5, 5],
                        cmap=pl.cm.gnuplot)
    pl.clabel(contours,
            inline=1,
            fmt='%1.1f',
            fontsize=14)
    pl.plot([-1.5, -1.5,  1.5,  1.5, -1.5],
            [-1.5,  1.5,  1.5, -1.5, -1.5], 'k', linewidth=2)
    pl.fill_between([ -1.5,  1.5],
                    [ -1.5, -1.5],
                    [  1.5,  1.5],
                    color='.8')
    pl.axvline(0, color='k')
    pl.axhline(0, color='k')

    pl.text(-.9, 4.4, '$x_2$', size=20)
    pl.text(5.6, -.6, '$x_1$', size=20)
    pl.axis('equal')
    pl.axis('off')

# And now plot the optimization path
accumulator = list()

def f(x):
    # Store the list of function calls
    accumulator.append(x)
    return np.sqrt((x[0] - 3)**2 + (x[1] - 2)**2)


# We don't use the gradient, as with the gradient, L-BFGS is too fast,
# and finds the optimum without showing us a pretty path
def f_prime(x):
    r = np.sqrt((x[0] - 3)**2 + (x[0] - 2)**2)
    return np.array(((x[0] - 3)/r, (x[0] - 2)/r))

optimize.fmin_l_bfgs_b(f, np.array([0, 0]), approx_grad=1,
                       bounds=((-1.5, 1.5), (-1.5, 1.5)))

accumulated = np.array(accumulator)
pl.plot(accumulated[:, 0], accumulated[:, 1])

pl.show()


########NEW FILE########
__FILENAME__ = plot_convex
"""
Definition of a convex function
"""

import numpy as np
import pylab as pl

x = np.linspace(-1, 2)

pl.figure(1, figsize=(3, 2.5))
pl.clf()

# A convex function
pl.plot(x, x**2, linewidth=2)
pl.text(-.7, -.6**2, '$f$', size=20)

# The tangent in one point
pl.plot(x, 2*x - 1)
pl.plot(1, 1, 'k+')
pl.text(.3, -.75, "Tangent to $f$", size=15)
pl.text(1, 1 - .5, 'C', size=15)

# Convexity as barycenter
pl.plot([.35, 1.85], [.35**2, 1.85**2])
pl.plot([.35, 1.85], [.35**2, 1.85**2], 'k+')
pl.text(.35 - .2, .35**2 + .1, 'A', size=15)
pl.text(1.85 - .2, 1.85**2, 'B', size=15)

pl.ylim(ymin=-1)
pl.axis('off')
pl.tight_layout()

# Convexity as barycenter
pl.figure(2, figsize=(3, 2.5))
pl.clf()
pl.plot(x, x**2 + np.exp(-5*(x - .5)**2), linewidth=2)
pl.text(-.7, -.6**2, '$f$', size=20)

pl.ylim(ymin=-1)
pl.axis('off')
pl.tight_layout()
pl.show()


########NEW FILE########
__FILENAME__ = plot_curve_fit
"""
A curve fitting example
"""

import numpy as np
from scipy import optimize
import pylab as pl

np.random.seed(0)

# Our test function
def f(t, omega, phi):
    return np.cos(omega * t + phi)

# Our x and y data
x = np.linspace(0, 3, 50)
y = f(x, 1.5, 1) + .1*np.random.normal(size=50)

# Fit the model: the parameters omega and phi can be found in the
# `params` vector
params, params_cov = optimize.curve_fit(f, x, y)

# plot the data and the fitted curve
t = np.linspace(0, 3, 1000)

pl.figure(1)
pl.clf()
pl.plot(x, y, 'bx')
pl.plot(t, f(t, *params), 'r-')
pl.show()


########NEW FILE########
__FILENAME__ = plot_exercise_flat_minimum
"""
Finding a minimum in a flat neighborhood
=========================================

An excercise of finding minimum. This excercise is hard because the
function is very flat around the minimum (all its derivatives are zero).
Thus gradient information is unreliable.

The function admits a minimum in [0, 0]. The challenge is to get within
1e-7 of this minimum, starting at x0 = [1, 1].

The solution that we adopt here is to give up on using gradient or
information based on local differences, and to rely on the Powell
algorithm. With 162 function evaluations, we get to 1e-8 of the
solution.
"""

import numpy as np
from scipy import optimize
import pylab as pl

def f(x):
    return np.exp(-1/(.01*x[0]**2 + x[1]**2))

# A well-conditionned version of f:
def g(x):
    return f([10*x[0], x[1]])

# The gradient of g. We won't use it here for the optimization.
def g_prime(x):
    r = np.sqrt(x[0]**2 + x[1]**2)
    return 2/r**3*g(x)*x/r

x_min = optimize.fmin_powell(g, [1, 1], xtol=1e-10)

###############################################################################
# Some pretty plotting

pl.figure(0)
pl.clf()
t = np.linspace(-1.1, 1.1, 100)
pl.plot(t, f([0, t]))

pl.figure(1)
pl.clf()
X, Y = np.mgrid[-1.5:1.5:100j, -1.1:1.1:100j]
pl.imshow(f([X, Y]).T, cmap=pl.cm.gray_r, extent=[-1.5, 1.5, -1.1, 1.1],
          origin='lower')
pl.contour(X, Y, f([X, Y]), cmap=pl.cm.gnuplot)

# Plot the gradient
dX, dY = g_prime([.1*X[::5, ::5], Y[::5, ::5]])
# Adjust for our preconditioning
dX *= .1
pl.quiver(X[::5, ::5], Y[::5, ::5], dX, dY, color='.5')

# Plot our solution
pl.plot(x_min[0], x_min[1], 'r+', markersize=15)

pl.show()


########NEW FILE########
__FILENAME__ = plot_exercise_ill_conditioned
"""
Alternating optimization
=========================

The challenge here is that Hessian of the problem is a very
ill-conditioned matrix. This can easily be seen, as the Hessian of the
first term in simply 2*np.dot(K.T, K). Thus the conditioning of the
problem can be judged from looking at the conditioning of K.
"""
import time

import numpy as np
from scipy import optimize
import pylab as pl

np.random.seed(0)

K = np.random.normal(size=(100, 100))

def f(x):
    return np.sum((np.dot(K, x - 1))**2) + np.sum(x**2)**2


def f_prime(x):
    return 2*np.dot(np.dot(K.T, K), x - 1) + 4*np.sum(x**2)*x


def hessian(x):
    H = 2*np.dot(K.T, K) + 4*2*x*x[:, np.newaxis]
    return H + 4*np.eye(H.shape[0])*np.sum(x**2)


###############################################################################
# Some pretty plotting

pl.figure(1)
pl.clf()
Z = X, Y = np.mgrid[-1.5:1.5:100j, -1.1:1.1:100j]
# Complete in the additional dimensions with zeros
Z = np.reshape(Z, (2, -1)).copy()
Z.resize((100, Z.shape[-1]))
Z = np.apply_along_axis(f, 0, Z)
Z = np.reshape(Z, X.shape)
pl.imshow(Z.T, cmap=pl.cm.gray_r, extent=[-1.5, 1.5, -1.1, 1.1],
          origin='lower')
pl.contour(X, Y, Z, cmap=pl.cm.gnuplot)

# A reference but slow solution:
t0 = time.time()
x_ref = optimize.fmin_powell(f, K[0], xtol=1e-10, ftol=1e-6, disp=0)
print '     Powell: time %.2fs' % (time.time() - t0)
f_ref = f(x_ref)

# Compare different approaches
t0 = time.time()
x_bfgs = optimize.fmin_bfgs(f, K[0], disp=0)[0]
print '       BFGS: time %.2fs, x error %.2f, f error %.2f' % (time.time() - t0,
    np.sqrt(np.sum((x_bfgs - x_ref)**2)), f(x_bfgs) - f_ref)

t0 = time.time()
x_l_bfgs = optimize.fmin_l_bfgs_b(f, K[0], approx_grad=1, disp=0)[0]
print '     L-BFGS: time %.2fs, x error %.2f, f error %.2f' % (time.time() - t0,
    np.sqrt(np.sum((x_l_bfgs - x_ref)**2)), f(x_l_bfgs) - f_ref)


t0 = time.time()
x_bfgs = optimize.fmin_bfgs(f, K[0], f_prime, disp=0)[0]
print "  BFGS w f': time %.2fs, x error %.2f, f error %.2f" % (
    time.time() - t0, np.sqrt(np.sum((x_bfgs - x_ref)**2)),
    f(x_bfgs) - f_ref)

t0 = time.time()
x_l_bfgs = optimize.fmin_l_bfgs_b(f, K[0], f_prime, disp=0)[0]
print "L-BFGS w f': time %.2fs, x error %.2f, f error %.2f" % (
    time.time() - t0, np.sqrt(np.sum((x_l_bfgs - x_ref)**2)),
    f(x_l_bfgs) - f_ref)

t0 = time.time()
x_newton = optimize.fmin_ncg(f, K[0], f_prime, fhess=hessian, disp=0)[0]
print "     Newton: time %.2fs, x error %.2f, f error %.2f" % (
    time.time() - t0, np.sqrt(np.sum((x_newton - x_ref)**2)),
    f(x_newton) - f_ref)

pl.show()


########NEW FILE########
__FILENAME__ = plot_gradient_descent
"""
Demo gradient descent
"""
import numpy as np
import pylab as pl
from scipy import optimize

from cost_functions import mk_quad, mk_gauss, rosenbrock,\
    rosenbrock_prime, rosenbrock_hessian, LoggingFunction,\
    CountingFunction

x_min, x_max = -1, 2
y_min, y_max = 2.25/3*x_min - .2, 2.25/3*x_max - .2

###############################################################################
# A formatter to print values on contours
def super_fmt(value):
    if value > 1:
        if np.abs(int(value) - value) < .1:
            out = '$10^{%.1i}$' % value
        else:
            out = '$10^{%.1f}$' % value
    else:
        value = np.exp(value - .01)
        if value > .1:
            out = '%1.1f' % value
        elif value > .01:
            out = '%.2f' % value
        else:
            out = '%.2e' % value
    return out

###############################################################################
# A gradient descent algorithm
# do not use: its a toy, use scipy's optimize.fmin_cg

def gradient_descent(x0, f, f_prime, hessian=None, adaptative=False):
    x_i, y_i = x0
    all_x_i = list()
    all_y_i = list()
    all_f_i = list()

    for i in range(1, 100):
        all_x_i.append(x_i)
        all_y_i.append(y_i)
        all_f_i.append(f([x_i, y_i]))
        dx_i, dy_i = f_prime(np.asarray([x_i, y_i]))
        if adaptative:
            # Compute a step size using a line_search to satisfy the Wolf
            # conditions
            step = optimize.line_search(f, f_prime,
                                np.r_[x_i, y_i], -np.r_[dx_i, dy_i],
                                np.r_[dx_i, dy_i], c2=.05)
            step = step[0]
        else:
            step = 1
        x_i += - step*dx_i
        y_i += - step*dy_i
        if np.abs(all_f_i[-1]) < 1e-16:
            break
    return all_x_i, all_y_i, all_f_i


def gradient_descent_adaptative(x0, f, f_prime, hessian=None):
    return gradient_descent(x0, f, f_prime, adaptative=True)


def conjugate_gradient(x0, f, f_prime, hessian=None):
    all_x_i = [x0[0]]
    all_y_i = [x0[1]]
    all_f_i = [f(x0)]
    def store(X):
        x, y = X
        all_x_i.append(x)
        all_y_i.append(y)
        all_f_i.append(f(X))
    optimize.fmin_cg(f, x0, f_prime, callback=store, gtol=1e-12)
    return all_x_i, all_y_i, all_f_i


def newton_cg(x0, f, f_prime, hessian):
    all_x_i = [x0[0]]
    all_y_i = [x0[1]]
    all_f_i = [f(x0)]
    def store(X):
        x, y = X
        all_x_i.append(x)
        all_y_i.append(y)
        all_f_i.append(f(X))
    optimize.fmin_ncg(f, x0, f_prime, fhess=hessian, callback=store,
                avextol=1e-12)
    return all_x_i, all_y_i, all_f_i


def bfgs(x0, f, f_prime, hessian=None):
    all_x_i = [x0[0]]
    all_y_i = [x0[1]]
    all_f_i = [f(x0)]
    def store(X):
        x, y = X
        all_x_i.append(x)
        all_y_i.append(y)
        all_f_i.append(f(X))
    optimize.fmin_bfgs(f, x0, f_prime, callback=store, gtol=1e-12)
    return all_x_i, all_y_i, all_f_i


def powell(x0, f, f_prime, hessian=None):
    all_x_i = [x0[0]]
    all_y_i = [x0[1]]
    all_f_i = [f(x0)]
    def store(X):
        x, y = X
        all_x_i.append(x)
        all_y_i.append(y)
        all_f_i.append(f(X))
    optimize.fmin_powell(f, x0, callback=store, ftol=1e-12)
    return all_x_i, all_y_i, all_f_i


def nelder_mead(x0, f, f_prime, hessian=None):
    all_x_i = [x0[0]]
    all_y_i = [x0[1]]
    all_f_i = [f(x0)]
    def store(X):
        x, y = X
        all_x_i.append(x)
        all_y_i.append(y)
        all_f_i.append(f(X))
    optimize.fmin(f, x0, callback=store, ftol=1e-12)
    return all_x_i, all_y_i, all_f_i




###############################################################################
# Run different optimizers on these problems
levels = dict()

for index, ((f, f_prime, hessian), optimizer) in enumerate((
                (mk_quad(.7), gradient_descent),
                (mk_quad(.7), gradient_descent_adaptative),
                (mk_quad(.02), gradient_descent),
                (mk_quad(.02), gradient_descent_adaptative),
                (mk_gauss(.02), gradient_descent_adaptative),
                ((rosenbrock, rosenbrock_prime, rosenbrock_hessian),
                                    gradient_descent_adaptative),
                (mk_gauss(.02), conjugate_gradient),
                ((rosenbrock, rosenbrock_prime, rosenbrock_hessian),
                                    conjugate_gradient),
                (mk_quad(.02), newton_cg),
                (mk_gauss(.02), newton_cg),
                ((rosenbrock, rosenbrock_prime, rosenbrock_hessian),
                                    newton_cg),
                (mk_quad(.02), bfgs),
                (mk_gauss(.02), bfgs),
                ((rosenbrock, rosenbrock_prime, rosenbrock_hessian),
                            bfgs),
                (mk_quad(.02), powell),
                (mk_gauss(.02), powell),
                ((rosenbrock, rosenbrock_prime, rosenbrock_hessian),
                            powell),
                (mk_gauss(.02), nelder_mead),
                ((rosenbrock, rosenbrock_prime, rosenbrock_hessian),
                            nelder_mead),
            )):

    # Compute a gradient-descent
    x_i, y_i = 1.6, 1.1
    counting_f_prime = CountingFunction(f_prime)
    counting_hessian = CountingFunction(hessian)
    logging_f = LoggingFunction(f, counter=counting_f_prime.counter)
    all_x_i, all_y_i, all_f_i = optimizer(np.array([x_i, y_i]),
                                          logging_f, counting_f_prime,
                                          hessian=counting_hessian)

    # Plot the contour plot
    if not max(all_y_i) < y_max:
        x_min *= 1.2
        x_max *= 1.2
        y_min *= 1.2
        y_max *= 1.2
    x, y = np.mgrid[x_min:x_max:100j, y_min:y_max:100j]
    x = x.T
    y = y.T

    pl.figure(index, figsize=(3, 2.5))
    pl.clf()
    pl.axes([0, 0, 1, 1])

    X = np.concatenate((x[np.newaxis, ...], y[np.newaxis, ...]), axis=0)
    z = np.apply_along_axis(f, 0, X)
    log_z = np.log(z + .01)
    pl.imshow(log_z,
            extent=[x_min, x_max, y_min, y_max],
            cmap=pl.cm.gray_r, origin='lower',
            vmax=log_z.min() + 1.5*log_z.ptp())
    contours = pl.contour(log_z,
                        levels=levels.get(f, None),
                        extent=[x_min, x_max, y_min, y_max],
                        cmap=pl.cm.gnuplot, origin='lower')
    levels[f] = contours.levels
    pl.clabel(contours, inline=1,
                fmt=super_fmt, fontsize=14)

    pl.plot(all_x_i, all_y_i, 'b-', linewidth=2)
    pl.plot(all_x_i, all_y_i, 'k+')

    pl.plot(logging_f.all_x_i, logging_f.all_y_i, 'k.', markersize=2)

    pl.plot([0], [0], 'rx', markersize=12)


    pl.xticks(())
    pl.yticks(())
    pl.xlim(x_min, x_max)
    pl.ylim(y_min, y_max)
    pl.draw()

    pl.figure(index + 100, figsize=(4, 3))
    pl.clf()
    pl.semilogy(np.maximum(np.abs(all_f_i), 1e-30), linewidth=2,
                label='# iterations')
    pl.ylabel('Error on f(x)')
    pl.semilogy(logging_f.counts,
                np.maximum(np.abs(logging_f.all_f_i), 1e-30),
                linewidth=2, color='g', label='# function calls')
    pl.legend(loc='upper right', frameon=True, prop=dict(size=11),
              borderaxespad=0, handlelength=1.5, handletextpad=.5)
    pl.tight_layout()
    pl.draw()


########NEW FILE########
__FILENAME__ = plot_noisy
"""
Noisy vs non-noisy
"""
import numpy as np
import pylab as pl

np.random.seed(0)

x = np.linspace(-5, 5, 101)
x_ = np.linspace(-5, 5, 31)

def f(x):
    return -np.exp(-x**2)

# A smooth function
pl.figure(1, figsize=(3, 2.5))
pl.clf()

pl.plot(x_, f(x_) + .2*np.random.normal(size=31), linewidth=2)
pl.plot(x, f(x), linewidth=2)

pl.ylim(ymin=-1.3)
pl.axis('off')
pl.tight_layout()
pl.show()


########NEW FILE########
__FILENAME__ = plot_non_bounds_constraints
"""
Optimization with general constraints using SLSQP and cobyla
"""
import numpy as np
import pylab as pl
from scipy import optimize

x, y = np.mgrid[-2.03:4.2:.04, -1.6:3.2:.04]
x = x.T
y = y.T

pl.figure(1, figsize=(3, 2.5))
pl.clf()
pl.axes([0, 0, 1, 1])

contours = pl.contour(np.sqrt((x - 3)**2 + (y - 2)**2),
                    extent=[-2.03, 4.2, -1.6, 3.2],
                    cmap=pl.cm.gnuplot)
pl.clabel(contours,
        inline=1,
        fmt='%1.1f',
        fontsize=14)
pl.plot([-1.5,    0,  1.5,    0, -1.5],
        [   0,  1.5,    0, -1.5,    0], 'k', linewidth=2)
pl.fill_between([ -1.5,    0,  1.5],
                [    0, -1.5,    0],
                [    0,  1.5,    0],
                color='.8')
pl.axvline(0, color='k')
pl.axhline(0, color='k')

pl.text(-.9, 2.8, '$x_2$', size=20)
pl.text(3.6, -.6, '$x_1$', size=20)
pl.axis('tight')
pl.axis('off')

# And now plot the optimization path
accumulator = list()

def f(x):
    # Store the list of function calls
    accumulator.append(x)
    return np.sqrt((x[0] - 3)**2 + (x[1] - 2)**2)


def constraint(x):
    return np.atleast_1d(1.5 - np.sum(np.abs(x)))

optimize.fmin_slsqp(f, np.array([0, 0]),
                       ieqcons=[constraint, ])

accumulated = np.array(accumulator)
pl.plot(accumulated[:, 0], accumulated[:, 1])

pl.show()


########NEW FILE########
__FILENAME__ = plot_smooth
"""
Smooth vs non-smooth
"""
import numpy as np
import pylab as pl

x = np.linspace(-1.5, 1.5, 101)

# A smooth function
pl.figure(1, figsize=(3, 2.5))
pl.clf()

pl.plot(x, np.sqrt(.2 + x**2), linewidth=2)
pl.text(-1, 0, '$f$', size=20)

pl.ylim(ymin=-.2)
pl.axis('off')
pl.tight_layout()

# A non-smooth function
pl.figure(2, figsize=(3, 2.5))
pl.clf()
pl.plot(x, np.abs(x), linewidth=2)
pl.text(-1, 0, '$f$', size=20)

pl.ylim(ymin=-.2)
pl.axis('off')
pl.tight_layout()
pl.show()


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# sphinx-quickstart on Fri Nov 28 22:10:09 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.abspath('sphinxext'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 
        #'matplotlib.sphinxext.plot_directive', 
        'plot_directive',
        'ipython_console_highlighting',
        'matplotlib.sphinxext.only_directives',
        ]#'sphinx.ext.intersphinx']

doctest_test_doctest_blocks = 'true'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Profiling'
copyright = u'2008, Gaël Varoquaux'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = '1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'fr' 

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Profiling"

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
html_static_path = ['_static']

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
html_use_index = False 

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Profiling'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Profiling.tex', ur'Profiling',
   ur'Gaël Varoquaux', 'manual'),
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

# Additional stuff for the LaTeX preamble.
latex_preamble = """
\definecolor{VerbatimColor}{rgb}{0.95,1,0.833}
\definecolor{VerbatimBorderColor}{rgb}{0.6,0.6,0.6}
"""

latex_elements = {
    'classoptions': ',oneside,openany',
    'babel': '\usepackage[french]{babel}',
    'tableofcontents': '%\\tableofcontents',
} 

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/dev': None}

########NEW FILE########
__FILENAME__ = demo
# For this example to run, you also need the 'ica.py' file

import numpy as np
from scipy import linalg

from ica import fastica


def test():
    data = np.random.random((5000, 100))
    u, s, v = linalg.svd(data)
    pca = np.dot(u[:, :10].T, data)
    results = fastica(pca.T, whiten=False)

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = demo_opt
# For this example to run, you also need the 'ica.py' file

import numpy as np
from scipy import linalg

from ica import fastica


def test():
    data = np.random.random((5000, 100))
    u, s, v = linalg.svd(data, full_matrices=False)
    pca = np.dot(u[:, :10].T, data)
    results = fastica(pca.T, whiten=False)

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = ica
# Author: Pierre Lafaye de Micheaux, Stefan van der Walt
# Python FastICA
# License: GPL unless permission obtained otherwise
# Look at algorithms in Tables 8.3 and 8.4 page 196 in the book: Independent Component Analysis, by Aapo et al.

import numpy as np
import types


__all__ = ['fastica']


def _gs_decorrelation(w, W, j):
    """ Gram-Schmidt-like decorrelation. """
    t = np.zeros_like(w)
    for u in range(j):
        t = t + np.dot(w, W[u]) * W[u]
        w -= t
    return w


def _ica_def(X, tol, g, gprime, fun_args, maxit, w_init):
    """Deflationary FastICA using fun approx to neg-entropy function

    Used internally by FastICA.
    """

    n_comp = w_init.shape[0]
    W = np.zeros((n_comp, n_comp), dtype=float)

    # j is the index of the extracted component
    for j in range(n_comp):
        w = w_init[j, :].copy()
        w /= np.sqrt((w**2).sum())

        n_iterations = 0
        # we set lim to tol+1 to be sure to enter at least once in next while
        lim = tol + 1 
        while ((lim > tol) & (n_iterations < (maxit-1))):
            wtx = np.dot(w.T, X)
            gwtx = g(wtx, fun_args)
            g_wtx = gprime(wtx, fun_args)
            w1 = (X * gwtx).mean(axis=1) - g_wtx.mean() * w
            
            _gs_decorrelation(w1, W, j)
            
            w1 /= np.sqrt((w1**2).sum())

            lim = np.abs(np.abs((w1 * w).sum()) - 1)
            w = w1
            n_iterations = n_iterations + 1
            
        W[j, :] = w

    return W


def _sym_decorrelation(W):
    """ Symmetric decorrelation """
    K = np.dot(W, W.T)
    s, u = np.linalg.eigh(K) 
    # u (resp. s) contains the eigenvectors (resp. square roots of 
    # the eigenvalues) of W * W.T 
    u, W = [np.asmatrix(e) for e in (u, W)]
    W = (u * np.diag(1.0/np.sqrt(s)) * u.T) * W  # W = (W * W.T) ^{-1/2} * W
    return W


def _ica_par(X, tol, g, gprime, fun_args, maxit, w_init):
    """Parallel FastICA.

    Used internally by FastICA.

    """
    n,p = X.shape
    
    W = _sym_decorrelation(w_init)

    # we set lim to tol+1 to be sure to enter at least once in next while
    lim = tol + 1 
    it = 0
    while ((lim > tol) and (it < (maxit-1))):
        wtx = np.dot(W, X).A  # .A transforms to array type
        gwtx = g(wtx, fun_args)
        g_wtx = gprime(wtx, fun_args)
        W1 = np.dot(gwtx, X.T)/float(p) - np.dot(np.diag(g_wtx.mean(axis=1)), W)
 
        W1 = _sym_decorrelation(W1)
        
        lim = max(abs(abs(np.diag(np.dot(W1, W.T))) - 1))
        W = W1
        it = it + 1

    return W


def fastica(X, n_comp=None,
            algorithm="parallel", whiten=True, fun="logcosh", fun_prime='', 
            fun_args={}, maxit=200, tol=1e-04, w_init=None):
    """Perform Fast Independent Component Analysis.

    Parameters
    ----------
    X : (n,p) array
        Array with n observations (statistical units) measured on p variables.
    n_comp : int, optional
        Number of components to extract. If None no dimension reduction
        is performed.
    algorithm : {'parallel','deflation'}
        Apply an parallel or deflational FASTICA algorithm.
    whiten: boolean, optional
        If true perform an initial whitening of the data. Do not set to 
        false unless the data is already white, as you will get incorrect 
        results.
        If whiten is true, the data is assumed to have already been
        preprocessed: it should be centered, normed and white.
    fun : String or Function
          The functional form of the G function used in the
          approximation to neg-entropy. Could be either 'logcosh', 'exp', 
          or 'cube'.
          You can also provide your own function but in this case, its 
          derivative should be provided via argument fun_prime
    fun_prime : Empty string ('') or Function
                See fun.
    fun_args : Optional dictionnary
               If empty and if fun='logcosh', fun_args will take value 
               {'alpha' : 1.0}
    maxit : int
            Maximum number of iterations to perform
    tol : float
          A positive scalar giving the tolerance at which the
          un-mixing matrix is considered to have converged
    w_init : (n_comp,n_comp) array
             Initial un-mixing array of dimension (n.comp,n.comp).
             If None (default) then an array of normal r.v.'s is used
    source_only: if True, only the sources matrix is returned

    Results
    -------
    K : (p,n_comp) array
        pre-whitening matrix that projects data onto th first n.comp
        principal components. Returned only if whiten is True
    W : (n_comp,n_comp) array
        estimated un-mixing matrix
        The mixing matrix can be obtained by::
            w = np.asmatrix(W) * K.T
            A = w.T * (w * w.T).I
    S : (n,n_comp) array
        estimated source matrix

    Examples
    --------

    >>> X = np.array(
    [[5.,1.4,1.9,0], \
    [2,5.4,8.,1.1], \
    [3,6.4,9,1.2]])
    >>> w_init = np.array([[1,4],[7,2]])
    >>> n_comp = 2
    >>> k, W, S = fastica(X, n_comp, algorithm='parallel', w_init=w_init)
    >>> print S
    [[-0.02387286 -1.41401205]
     [ 1.23650679  0.68633152]
     [-1.21263393  0.72768053]]

    Notes
    -----

    The data matrix X is considered to be a linear combination of
    non-Gaussian (independent) components i.e. X = SA where columns of S
    contain the independent components and A is a linear mixing
    matrix. In short ICA attempts to `un-mix' the data by estimating an
    un-mixing matrix W where XW = S.

    Implemented using FastICA:

      A. Hyvarinen and E. Oja, Independent Component Analysis:
      Algorithms and Applications, Neural Networks, 13(4-5), 2000,
      pp. 411-430

    """
    algorithm_funcs = {'parallel': _ica_par,
                       'deflation': _ica_def}

    alpha = fun_args.get('alpha',1.0)
    if (alpha < 1) or (alpha > 2):
        raise ValueError("alpha must be in [1,2]")

    if type(fun) is types.StringType:
        # Some standard nonlinear functions
        if fun == 'logcosh':
            def g(x, fun_args):
                alpha = fun_args.get('alpha', 1.0)
                return np.tanh(alpha * x)
            def gprime(x, fun_args):
                alpha = fun_args.get('alpha', 1.0)
                return alpha * (1 - (np.tanh(alpha * x))**2)
        elif fun == 'exp':
            def g(x, fun_args):
                return x * np.exp(-(x**2)/2)
            def gprime(x, fun_args):
                return (1 - x**2) * np.exp(-(x**2)/2)
        elif fun == 'cube':
            def g(x, fun_args):
                return x**3
            def gprime(x, fun_args):
                return 3*x**2
        else:
            raise ValueError(
                        'fun argument should be one of logcosh, exp or cube')
    elif type(fun) is not types.FunctionType:
        raise ValueError('fun argument should be either a string '
                         '(one of logcosh, exp or cube) or a function') 
    else:
        def g(x, fun_args):
            return fun(x, **fun_args)
        def gprime(x, fun_args):
            return fun_prime(x, **fun_args)

    n, p = X.shape

    if n_comp is None:
        n_comp = min(n, p)
    if (n_comp > min(n, p)):
        n_comp = min(n, p)
        print("n_comp is too large: it will be set to %s" % n_comp)


    if whiten:
        # Centering the columns (ie the variables)
        X = X - X.mean(axis=0)

        # Whitening and preprocessing by PCA
        _, d, v = np.linalg.svd(X, full_matrices=False)
        del _
        # XXX: Maybe we could provide a mean to estimate n_comp if it has not 
        # been provided ??? So that we do not have to perform another PCA 
        # before calling fastica ???
        K = (v*(np.sqrt(n)/d)[:, np.newaxis])[:n_comp]  # see (6.33) p.140
        del v, d
        X1 = np.dot(K, X.T) # see (13.6) p.267 Here X1 is white and data in X has been projected onto a subspace by PCA
    else:
        X1 = X.T

    if w_init is None:
        w_init = np.random.normal(size=(n_comp, n_comp))
    else:
        w_init = np.asarray(w_init)
        if w_init.shape != (n_comp,n_comp):
            raise ValueError("w_init has invalid shape -- should be %(shape)s"
                             % {'shape': (n_comp,n_comp)})

    kwargs = {'tol': tol,
              'g': g,
              'gprime': gprime,
              'fun_args': fun_args,
              'maxit': maxit,
              'w_init': w_init}

    func = algorithm_funcs.get(algorithm, 'parallel')

    W = func(X1, **kwargs)
    del X1

    if whiten:
        S = np.dot(np.asmatrix(W) * K, X.T)
        return [np.asarray(e.T) for e in (K, W, S)]
    else:
        S = np.dot(W, X.T)
        return [np.asarray(e.T) for e in (W, S)]



########NEW FILE########
__FILENAME__ = direct_solve
"""
Construct a 1000x1000 lil_matrix and add some values to it, convert it
to CSR format and solve A x = b for x:and solve a linear system with a
direct solver.
"""
import numpy as np
import scipy.sparse as sps
from matplotlib import pyplot as plt
from scipy.sparse.linalg.dsolve import linsolve

rand = np.random.rand

mtx = sps.lil_matrix((1000, 1000), dtype=np.float64)
mtx[0, :100] = rand(100)
mtx[1, 100:200] = mtx[0, :100]
mtx.setdiag(rand(1000))

plt.clf()
plt.spy(mtx, marker='.', markersize=2)
plt.show()

mtx = mtx.tocsr()
rhs = rand(1000)

x = linsolve.spsolve(mtx, rhs)

print 'rezidual:', np.linalg.norm(mtx * x - rhs)

########NEW FILE########
__FILENAME__ = lobpcg_sakurai
from scipy import array, arange, ones, sort, cos, pi, rand, \
     set_printoptions, r_
from scipy.sparse.linalg import lobpcg
from scipy import sparse
from pylab import loglog, show, xlabel, ylabel, title
set_printoptions(precision=8,linewidth=90)
import time

def sakurai(n):
    """ Example taken from
        T. Sakurai, H. Tadano, Y. Inadomi and U. Nagashima
        A moment-based method for large-scale generalized eigenvalue problems
        Appl. Num. Anal. Comp. Math. Vol. 1 No. 2 (2004) """

    A = sparse.eye( n, n )
    d0 = array(r_[5,6*ones(n-2),5])
    d1 = -4*ones(n)
    d2 =  ones(n)
    B = sparse.spdiags([d2,d1,d0,d1,d2],[-2,-1,0,1,2],n,n)

    k = arange(1,n+1)
    w_ex = sort(1./(16.*pow(cos(0.5*k*pi/(n+1)),4))) # exact eigenvalues

    return A,B, w_ex

m = 3  # Blocksize

#
# Large scale
#
n = 2500
A,B, w_ex = sakurai(n) # Mikota pair
X = rand(n,m)
data=[]
tt = time.clock()
eigs,vecs, resnh = lobpcg(A,X,B, tol=1e-6, maxiter=500, retResidualNormsHistory=1)
data.append(time.clock()-tt)
print 'Results by LOBPCG for n='+str(n)
print
print eigs
print
print 'Exact eigenvalues'
print
print w_ex[:m]
print
print 'Elapsed time',data[0]
loglog(arange(1,n+1),w_ex,'b.')
xlabel(r'Number $i$')
ylabel(r'$\lambda_i$')
title('Eigenvalue distribution')
show()

########NEW FILE########
__FILENAME__ = pyamg_with_lobpcg
"""
Compute eigenvectors and eigenvalues using a preconditioned eigensolver

In this example Smoothed Aggregation (SA) is used to precondition
the LOBPCG eigensolver on a two-dimensional Poisson problem with
Dirichlet boundary conditions.
"""

import scipy
from scipy.sparse.linalg import lobpcg

from pyamg import smoothed_aggregation_solver
from pyamg.gallery import poisson

N = 100
K = 9
A = poisson((N,N), format='csr')

# create the AMG hierarchy
ml = smoothed_aggregation_solver(A)

# initial approximation to the K eigenvectors
X = scipy.rand(A.shape[0], K) 

# preconditioner based on ml
M = ml.aspreconditioner()

# compute eigenvalues and eigenvectors with LOBPCG
W,V = lobpcg(A, X, M=M, tol=1e-8, largest=False)


#plot the eigenvectors
import pylab

pylab.figure(figsize=(9,9))

for i in range(K):
    pylab.subplot(3, 3, i+1)
    pylab.title('Eigenvector %d' % i)
    pylab.pcolor(V[:,i].reshape(N,N))
    pylab.axis('equal')
    pylab.axis('off')
pylab.show()    

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# sphinx-quickstart on Fri Nov 28 22:10:09 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import subprocess

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.abspath('sphinxext'))

# Try to override the matplotlib configuration as early as possible
try:
    import gen_rst
except:
    pass


# General configuration
# ---------------------

needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
        'gen_rst',
        'sphinx.ext.autodoc',
        'sphinx.ext.doctest',
        #'matplotlib.sphinxext.plot_directive',
        'plot_directive',
        'only_directives',
        'ipython_console_highlighting',
        #'matplotlib.sphinxext.only_directives',
        'sphinx.ext.pngmath',
        'sphinx.ext.intersphinx',
        'sphinx.ext.extlinks',
]

doctest_test_doctest_blocks = 'true'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u"Scipy lecture notes"
copyright = u'2012,2013'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

# The short X.Y version.
# we get this from git
# this WILL break if we are not in a git-repository
p = subprocess.Popen(['git', 'describe', '--tags'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
p.wait()
version = p.stdout.read().strip()

# The full version, including alpha/beta/rc tags.
release = '2013.2 beta (euroscipy 2013)'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'en'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'
today_fmt = '%B %d, %Y'
if version:
    today_fmt += ' ({%s})' % version

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['intro/image_processing']

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

# Monkey-patch sphinx to set the lineseparator option of pygment, to
# have indented line wrapping
from pygments import formatters

class MyHtmlFormatter(formatters.HtmlFormatter):
    def __init__(self, **options):
        options['lineseparator'] = '\n<div class="newline"></div>'
        formatters.HtmlFormatter.__init__(self, **options)

from sphinx import highlighting
highlighting.PygmentsBridge.html_formatter = MyHtmlFormatter

# Our substitutions
rst_epilog = """

.. |clear-floats| raw:: html

    <div style="clear: both"></div>

.. always clear floats at the bottom to avoid having stick out in the footer

|clear-floats|

"""

# Options for HTML output
# -----------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'scipy_lectures'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['themes']

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'default.css'

html_theme_options = {
                'nosidebar': 'true',
                'footerbgcolor': '#000000',
                'relbarbgcolor': '#000000',
                }


# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Scipy lecture notes"

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = "Scipy"

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
html_static_path = ['themes/scipy_lectures/static']

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
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'PythonScientic'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Latex references with page numbers (only Sphinx 1.0)
latex_show_pagerefs = True

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'PythonScientific.tex', ur'Python Scientific lecture notes',
   ur"""EuroScipy tutorial team \\\relax\normalfont Editors: Valentin Haenel, Emmanuelle Gouillart, Gaël Varoquaux"""
   + r"\\\relax ~\\\relax http://scipy-lectures.github.com",
   'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = 'euroscipy_back.pdf'

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
latex_use_parts = True

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
latex_use_modindex = False


# Additional stuff for the LaTeX preamble.
latex_preamble = """
\definecolor{VerbatimColor}{rgb}{0.95,1,0.833}
\definecolor{VerbatimBorderColor}{rgb}{0.6,0.6,0.6}
\setcounter{tocdepth}{1}
\usepackage{amssymb}
\usepackage{pifont}
\DeclareUnicodeCharacter{2460}{\ding{182}}
\DeclareUnicodeCharacter{2461}{\ding{183}}
\DeclareUnicodeCharacter{2462}{\ding{184}}
\DeclareUnicodeCharacter{2794}{\ding{229}}
"""

latex_elements = {
    'classoptions': ',oneside,openany',
    'babel': '\usepackage[english]{babel}',
    #'tableofcontents': '\\pagestyle{normal}\\pagenumbering{arabic} %\\tableofcontents',
}

_python_doc_base = 'http://docs.python.org/2.7'

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    _python_doc_base: None,
    'http://docs.scipy.org/doc/numpy': None,
    'http://docs.scipy.org/doc/scipy/reference': None,
    'http://matplotlib.org/': None,
    'http://scikit-learn.org/stable': None,
    'http://scikit-image.org/docs/0.8.0/': None,
    'http://docs.enthought.com/mayavi/mayavi/': None,
}

extlinks = {
    'simple': (_python_doc_base + '/reference/simple_stmts.html#%s', ''),
    'compound': (_python_doc_base + '/reference/compound_stmts.html#%s', ''),
}

# -- Options for pngmath ------------------------------------------------

pngmath_dvipng_args = ['-gamma 1.5', '-D 180', '-bg', 'Transparent']
pngmath_use_preview = True


# Add the 'copybutton' javascript, to hide/show the prompt in code
# examples
def setup(app):
    app.add_javascript('copybutton.js')

########NEW FILE########
__FILENAME__ = plot_simple
import numpy as np
import matplotlib.pyplot as plt

X = np.linspace(-np.pi,np.pi,100)
Y = np.sin(X)
plt.plot(X, Y, linewidth=2)
plt.show()

########NEW FILE########
__FILENAME__ = demo
"A demo module."

def print_b():
    "Prints b."
    print 'b'

def print_a():
    "Prints a."
    print 'a'


c = 2
d = 2

########NEW FILE########
__FILENAME__ = demo2
import sys

def print_a():
    "Prints a."
    print 'a'

print sys.argv

if __name__ == '__main__':
    print_a()

########NEW FILE########
__FILENAME__ = plot_aliased
import pylab as pl

size = 128, 16
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)

pl.axes([0, 0, 1, 1], frameon=False)

pl.rcParams['text.antialiased'] = False
pl.text(0.5, 0.5, "Aliased", ha='center', va='center')

pl.xlim(0, 1)
pl.ylim(0, 1)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_alpha
import pylab as pl

size = 256,16
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0.1, 1, .8], frameon=False)

for i in range(1, 11):
    pl.axvline(i, linewidth=1, color='blue', alpha= .25 + .75 * i / 10.)

pl.xlim(0, 11)
pl.xticks(())
pl.yticks(())
pl.show()

########NEW FILE########
__FILENAME__ = plot_antialiased
import pylab as pl

size = 128, 16
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

pl.rcParams['text.antialiased'] = True
pl.text(0.5, 0.5, "Anti-aliased", ha='center', va='center')

pl.xlim(0, 1)
pl.ylim(0, 1)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_axes-2
import pylab as pl

pl.axes([.1, .1, .5, .5])
pl.xticks(())
pl.yticks(())
pl.text(0.1, 0.1, 'axes([0.1,0.1,.8,.8])', ha='left', va='center',
        size=16, alpha=.5)

pl.axes([.2, .2, .5, .5])
pl.xticks(())
pl.yticks(())
pl.text(0.1, 0.1, 'axes([0.2,0.2,.5,.5])', ha='left', va='center',
        size=16, alpha=.5)

pl.axes([0.3, 0.3, .5, .5])
pl.xticks(())
pl.yticks(())
pl.text(0.1, 0.1, 'axes([0.3,0.3,.5,.5])', ha='left', va='center',
        size=16, alpha=.5)

pl.axes([.4, .4, .5, .5])
pl.xticks(())
pl.yticks(())
pl.text(0.1, 0.1, 'axes([0.4,0.4,.5,.5])', ha='left', va='center',
        size=16, alpha=.5)

pl.show()

########NEW FILE########
__FILENAME__ = plot_axes
import pylab as pl

pl.axes([.1, .1, .8, .8])
pl.xticks(())
pl.yticks(())
pl.text(.6, .6, 'axes([0.1,0.1,.8,.8])', ha='center', va='center',
        size=20, alpha=.5)

pl.axes([.2, .2, .3, .3])
pl.xticks(())
pl.yticks(())
pl.text(.5, .5, 'axes([0.2,0.2,.3,.3])', ha='center', va='center',
        size=16, alpha=.5)

pl.show()

########NEW FILE########
__FILENAME__ = plot_bad
import numpy as np
import matplotlib
matplotlib.use('Agg')
import pylab as pl

fig = pl.figure(figsize=(5, 4), dpi=72)
axes = fig.add_axes([0.01, 0.01, .98, 0.98])
X = np.linspace(0, 2, 200, endpoint=True)
Y = np.sin(2 * np.pi * X)
pl.plot(X, Y, lw=.25, c='k')
pl.xticks(np.arange(0.0, 2.0, 0.1))
pl.yticks(np.arange(-1.0, 1.0, 0.1))
pl.grid()
pl.show()

########NEW FILE########
__FILENAME__ = plot_bar
import pylab as pl
import numpy as np

n = 16
X = np.arange(n)
Y1 = (1 - X / float(n)) * np.random.uniform(0.5, 1.0, n)
Y2 = (1 - X / float(n)) * np.random.uniform(0.5, 1.0, n)
pl.bar(X, Y1, facecolor='#9999ff', edgecolor='white')
pl.bar(X, -Y2, facecolor='#ff9999', edgecolor='white')
pl.xlim(-.5, n)
pl.xticks(())
pl.ylim(-1, 1)
pl.yticks(())

pl.text(-0.05, 1.02, " Bar Plot:              pl.bar(...)\n",
      horizontalalignment='left',
      verticalalignment='top',
      size='xx-large',
      bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
      transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n   Make a bar plot with rectangles ",
      horizontalalignment='left',
      verticalalignment='top',
      size='large',
      transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_bar_ex
import pylab as pl
import numpy as np

n = 12
X = np.arange(n)
Y1 = (1 - X / float(n)) * np.random.uniform(0.5, 1.0, n)
Y2 = (1 - X / float(n)) * np.random.uniform(0.5, 1.0, n)

pl.axes([0.025, 0.025, 0.95, 0.95])
pl.bar(X, +Y1, facecolor='#9999ff', edgecolor='white')
pl.bar(X, -Y2, facecolor='#ff9999', edgecolor='white')

for x, y in zip(X, Y1):
    pl.text(x + 0.4, y + 0.05, '%.2f' % y, ha='center', va= 'bottom')

for x, y in zip(X, Y2):
    pl.text(x + 0.4, -y - 0.05, '%.2f' % y, ha='center', va= 'top')

pl.xlim(-.5, n)
pl.xticks(())
pl.ylim(-1.25, 1.25)
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_boxplot
import numpy as np
import matplotlib
matplotlib.use('Agg')
import pylab as pl

fig = pl.figure(figsize=(8, 5), dpi=72)
fig.patch.set_alpha(0.0)
axes = pl.subplot(111)

n = 5
Z = np.zeros((n, 4))
X = np.linspace(0, 2, n, endpoint=True)
Y = np.random.random((n, 4))
pl.boxplot(Y)

pl.xticks(()), pl.yticks(())

pl.text(-0.05, 1.02, " Box Plot:   pl.boxplot(...)\n",
        horizontalalignment='left',
        verticalalignment='top',
        size='xx-large',
        bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
        transform=axes.transAxes)

pl.text(-0.05, 1.01, " Make a box and whisker plot ",
        horizontalalignment='left',
        verticalalignment='top',
        size='large',
        transform=axes.transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_color
import pylab as pl

size = 256, 16
dpi = 72.0
figsize = size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0.1, 1, .8], frameon=False)

for i in range(1,11):
    pl.plot([i, i], [0, 1], lw=1.5)

pl.xlim(0, 11)
pl.xticks(())
pl.yticks(())
pl.show()

########NEW FILE########
__FILENAME__ = plot_colormaps
import pylab as pl
import numpy as np

pl.rc('text', usetex=False)
a = np.outer(np.arange(0, 1, 0.01), np.ones(10))

pl.figure(figsize=(10, 5))
pl.subplots_adjust(top=0.8, bottom=0.05, left=0.01, right=0.99)
maps = [m for m in pl.cm.datad if not m.endswith("_r")]
maps.sort()
l = len(maps) + 1

for i, m in enumerate(maps):
    pl.subplot(1, l, i+1)
    pl.axis("off")
    pl.imshow(a, aspect='auto', cmap=pl.get_cmap(m), origin="lower")
    pl.title(m, rotation=90, fontsize=10, va='bottom')

pl.show()

########NEW FILE########
__FILENAME__ = plot_contour
import pylab as pl
import numpy as np

def f(x,y):
    return (1 - x / 2 + x ** 5 + y ** 3) * np.exp(-x ** 2 - y ** 2)

n = 256
x = np.linspace(-3, 3, n)
y = np.linspace(-3, 3, n)
X, Y = np.meshgrid(x, y)

pl.contourf(X, Y, f(X, Y), 8, alpha=.75, cmap=pl.cm.hot)
C = pl.contour(X, Y, f(X,Y), 8, colors='black', linewidth=.5)
pl.clabel(C, inline=1, fontsize=10)
pl.xticks(())
pl.yticks(())

pl.text(-0.05, 1.02, " Contour Plot: pl.contour(..)\n",
      horizontalalignment='left',
      verticalalignment='top',
      size='xx-large',
      bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
      transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n  Draw contour lines and filled contours ",
      horizontalalignment='left',
      verticalalignment='top',
      size='large',
      transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_contour_ex
import pylab as pl
import numpy as np

def f(x,y):
    return (1 - x / 2 + x**5 + y**3) * np.exp(-x**2 -y**2)

n = 256
x = np.linspace(-3, 3, n)
y = np.linspace(-3, 3, n)
X,Y = np.meshgrid(x, y)

pl.axes([0.025, 0.025, 0.95, 0.95])

pl.contourf(X, Y, f(X, Y), 8, alpha=.75, cmap=pl.cm.hot)
C = pl.contour(X, Y, f(X, Y), 8, colors='black', linewidth=.5)
pl.clabel(C, inline=1, fontsize=10)

pl.xticks(())
pl.yticks(())
pl.show()

########NEW FILE########
__FILENAME__ = plot_dash_capstyle
import pylab as pl
import numpy as np

size = 256, 16
dpi = 72.0
figsize = size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

pl.plot(np.arange(4), np.ones(4), color="blue", dashes=[15, 15],
        linewidth=8, dash_capstyle='butt')

pl.plot(5 + np.arange(4), np.ones(4), color="blue", dashes=[15, 15],
        linewidth=8, dash_capstyle='round')

pl.plot(10 + np.arange(4), np.ones(4), color="blue", dashes=[15, 15],
        linewidth=8, dash_capstyle='projecting')

pl.xlim(0, 14)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_dash_joinstyle
import pylab as pl
import numpy as np

size = 256, 16
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

pl.plot(np.arange(3), [0, 1, 0], color="blue", dashes=[12, 5], linewidth=8,
        dash_joinstyle='miter')
pl.plot(4 + np.arange(3), [0, 1, 0], color="blue", dashes=[12, 5],
        linewidth=8, dash_joinstyle='bevel')
pl.plot(8 + np.arange(3), [0, 1, 0], color="blue", dashes=[12, 5],
        linewidth=8, dash_joinstyle='round')

pl.xlim(0, 12)
pl.ylim(-1, 2)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_1
import pylab as pl
import numpy as np

n = 256
X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
C,S = np.cos(X), np.sin(X)
pl.plot(X, C)
pl.plot(X,S)

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_10
import pylab as pl
import numpy as np

pl.figure(figsize=(8, 5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
C, S = np.cos(X), np.sin(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-", label="cosine")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-",  label="sine")

ax = pl.gca()
ax.spines['right'].set_color('none')
ax.spines['top'].set_color('none')
ax.xaxis.set_ticks_position('bottom')
ax.spines['bottom'].set_position(('data', 0))
ax.yaxis.set_ticks_position('left')
ax.spines['left'].set_position(('data', 0))

pl.xlim(X.min() * 1.1, X.max() * 1.1)
pl.xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi],
          [r'$-\pi$', r'$-\pi/2$', r'$0$', r'$+\pi/2$', r'$+\pi$'])

pl.ylim(C.min() * 1.1, C.max() * 1.1)
pl.yticks([-1, 1],
          [r'$-1$', r'$+1$'])

pl.legend(loc='upper left')

t = 2*np.pi/3
pl.plot([t, t], [0, np.cos(t)],
        color='blue', linewidth=1.5, linestyle="--")
pl.scatter([t, ], [np.cos(t), ], 50, color='blue')
pl.annotate(r'$sin(\frac{2\pi}{3})=\frac{\sqrt{3}}{2}$',
            xy=(t, np.sin(t)), xycoords='data',
            xytext=(10, 30), textcoords='offset points', fontsize=16,
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))

pl.plot([t, t], [0, np.sin(t)],
        color='red', linewidth=1.5, linestyle="--")
pl.scatter([t, ], [np.sin(t), ], 50, color ='red')
pl.annotate(r'$cos(\frac{2\pi}{3})=-\frac{1}{2}$', xy=(t, np.cos(t)),
            xycoords='data', xytext=(-90, -50),
            textcoords='offset points', fontsize=16,
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))

for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontsize(16)
    label.set_bbox(dict(facecolor='white', edgecolor='None', alpha=0.65 ))

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_2
import pylab as pl
import numpy as np

# Create a new figure of size 8x6 points, using 100 dots per inch
pl.figure(figsize=(8, 6), dpi=80)

# Create a new subplot from a grid of 1x1
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
C, S = np.cos(X), np.sin(X)

# Plot cosine using blue color with a continuous line of width 1 (pixels)
pl.plot(X, C, color="blue", linewidth=1.0, linestyle="-")

# Plot sine using green color with a continuous line of width 1 (pixels)
pl.plot(X, S, color="green", linewidth=1.0, linestyle="-")

# Set x limits
pl.xlim(-4., 4.)

# Set x ticks
pl.xticks(np.linspace(-4, 4, 9, endpoint=True))

# Set y limits
pl.ylim(-1.0, 1.0)

# Set y ticks
pl.yticks(np.linspace(-1, 1, 5, endpoint=True))

# Show result on screen
pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_3
import pylab as pl
import numpy as np

pl.figure(figsize=(8, 5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
C, S = np.cos(X), np.sin(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-")

pl.xlim(-4.0, 4.0)
pl.xticks(np.linspace(-4, 4, 9, endpoint=True))

pl.ylim(-1.0, 1.0)
pl.yticks(np.linspace(-1, 1, 5, endpoint=True))

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_4
import pylab as pl
import numpy as np

pl.figure(figsize=(8, 5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
S = np.sin(X)
C = np.cos(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-")

pl.xlim(X.min() * 1.1, X.max() * 1.1)
pl.ylim(C.min() * 1.1, C.max() * 1.1)

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_5
import pylab as pl
import numpy as np

pl.figure(figsize=(8, 5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
S = np.sin(X)
C = np.cos(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-")

pl.xlim(X.min() * 1.1, X.max() * 1.1)
pl.xticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi])

pl.ylim(C.min() * 1.1, C.max() * 1.1)
pl.yticks([-1, 0, +1])

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_6
import pylab as pl
import numpy as np

pl.figure(figsize=(8, 5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256, endpoint=True)
C = np.cos(X)
S = np.sin(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-")

pl.xlim(X.min() * 1.1, X.max() * 1.1)
pl.xticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi],
          [r'$-\pi$', r'$-\pi/2$', r'$0$', r'$+\pi/2$', r'$+\pi$'])

pl.ylim(C.min() * 1.1, C.max() * 1.1)
pl.yticks([-1, 0, +1],
          [r'$-1$', r'$0$', r'$+1$'])

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_7
import pylab as pl
import numpy as np

pl.figure(figsize=(8,5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256,endpoint=True)
C = np.cos(X)
S = np.sin(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-")

ax = pl.gca()
ax.spines['right'].set_color('none')
ax.spines['top'].set_color('none')
ax.xaxis.set_ticks_position('bottom')
ax.spines['bottom'].set_position(('data',0))
ax.yaxis.set_ticks_position('left')
ax.spines['left'].set_position(('data',0))

pl.xlim(X.min() * 1.1, X.max() * 1.1)
pl.xticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi],
          [r'$-\pi$', r'$-\pi/2$', r'$0$', r'$+\pi/2$', r'$+\pi$'])

pl.ylim(C.min() * 1.1, C.max() * 1.1)
pl.yticks([-1, 0, +1],
          [r'$-1$', r'$0$', r'$+1$'])

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_8
import pylab as pl
import numpy as np

pl.figure(figsize=(8,5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256,endpoint=True)
C = np.cos(X)
S = np.sin(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-", label="cosine")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-",  label="sine")

ax = pl.gca()
ax.spines['right'].set_color('none')
ax.spines['top'].set_color('none')
ax.xaxis.set_ticks_position('bottom')
ax.spines['bottom'].set_position(('data',0))
ax.yaxis.set_ticks_position('left')
ax.spines['left'].set_position(('data',0))

pl.xlim(X.min() * 1.1, X.max() * 1.1)
pl.xticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi],
          [r'$-\pi$', r'$-\pi/2$', r'$0$', r'$+\pi/2$', r'$+\pi$'])

pl.ylim(C.min() * 1.1, C.max() * 1.1)
pl.yticks([-1, +1],
          [r'$-1$', r'$+1$'])

pl.legend(loc='upper left')

pl.show()

########NEW FILE########
__FILENAME__ = plot_exercice_9
import pylab as pl
import numpy as np

pl.figure(figsize=(8, 5), dpi=80)
pl.subplot(111)

X = np.linspace(-np.pi, np.pi, 256,endpoint=True)
C = np.cos(X)
S = np.sin(X)

pl.plot(X, C, color="blue", linewidth=2.5, linestyle="-", label="cosine")
pl.plot(X, S, color="red", linewidth=2.5, linestyle="-",  label="sine")

ax = pl.gca()
ax.spines['right'].set_color('none')
ax.spines['top'].set_color('none')
ax.xaxis.set_ticks_position('bottom')
ax.spines['bottom'].set_position(('data',0))
ax.yaxis.set_ticks_position('left')
ax.spines['left'].set_position(('data',0))

pl.xlim(X.min() * 1.1, X.max() * 1.1)
pl.xticks([-np.pi, -np.pi/2, 0, np.pi/2, np.pi],
          [r'$-\pi$', r'$-\pi/2$', r'$0$', r'$+\pi/2$', r'$+\pi$'])

pl.ylim(C.min() * 1.1, C.max() * 1.1)
pl.yticks([-1, +1],
          [r'$-1$', r'$+1$'])

t = 2*np.pi/3
pl.plot([t, t], [0, np.cos(t)],
        color='blue', linewidth=1.5, linestyle="--")
pl.scatter([t, ], [np.cos(t), ], 50, color='blue')
pl.annotate(r'$sin(\frac{2\pi}{3})=\frac{\sqrt{3}}{2}$',
            xy=(t, np.sin(t)), xycoords='data',
            xytext=(+10, +30), textcoords='offset points', fontsize=16,
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))

pl.plot([t, t], [0, np.sin(t)],
        color='red', linewidth=1.5, linestyle="--")
pl.scatter([t, ], [np.sin(t), ], 50, color='red')
pl.annotate(r'$cos(\frac{2\pi}{3})=-\frac{1}{2}$', xy=(t, np.cos(t)),
            xycoords='data', xytext=(-90, -50), textcoords='offset points',
            fontsize=16,
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))

pl.legend(loc='upper left')

pl.show()

########NEW FILE########
__FILENAME__ = plot_good
import numpy as np
import matplotlib
matplotlib.use('Agg')
import pylab as pl

fig = pl.figure(figsize=(5, 4), dpi=72)
axes = fig.add_axes([0.01, 0.01, .98, 0.98])
X = np.linspace(0, 2, 200, endpoint=True)
Y = np.sin(2*np.pi*X)
pl.plot(X, Y, lw=2)
pl.ylim(-1.1, 1.1)
pl.grid()

pl.show()

########NEW FILE########
__FILENAME__ = plot_grid
import pylab as pl
from matplotlib.ticker import MultipleLocator

fig = pl.figure(figsize=(8, 6), dpi=72, facecolor="white")
axes = pl.subplot(111)
axes.set_xlim(0, 4)
axes.set_ylim(0, 3)

axes.xaxis.set_major_locator(MultipleLocator(1.0))
axes.xaxis.set_minor_locator(MultipleLocator(0.1))
axes.yaxis.set_major_locator(MultipleLocator(1.0))
axes.yaxis.set_minor_locator(MultipleLocator(0.1))
axes.grid(which='major', axis='x', linewidth=0.75, linestyle='-', color='0.75')
axes.grid(which='minor', axis='x', linewidth=0.25, linestyle='-', color='0.75')
axes.grid(which='major', axis='y', linewidth=0.75, linestyle='-', color='0.75')
axes.grid(which='minor', axis='y', linewidth=0.25, linestyle='-', color='0.75')
axes.set_xticklabels([])
axes.set_yticklabels([])

pl.text(-0.05, 1.02, " Grid:                  pl.grid(...)\n",
          horizontalalignment='left',
          verticalalignment='top',
          size='xx-large',
          bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
          transform=axes.transAxes)

pl.text(-0.05, 1.01, "\n\n    Draw ticks and grid ",
          horizontalalignment='left',
          verticalalignment='top',
          size='large',
          transform=axes.transAxes)


########NEW FILE########
__FILENAME__ = plot_gridspec
import pylab as pl
import matplotlib.gridspec as gridspec

pl.figure(figsize=(6, 4))
G = gridspec.GridSpec(3, 3)

axes_1 = pl.subplot(G[0, :])
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'Axes 1', ha='center', va='center', size=24, alpha=.5)

axes_2 = pl.subplot(G[1, :-1])
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'Axes 2', ha='center', va='center', size=24, alpha=.5)

axes_3 = pl.subplot(G[1:, -1])
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'Axes 3', ha='center', va='center', size=24, alpha=.5)

axes_4 = pl.subplot(G[-1, 0])
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'Axes 4', ha='center', va='center', size=24, alpha=.5)

axes_5 = pl.subplot(G[-1, -2])
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'Axes 5', ha='center', va='center', size=24, alpha=.5)

pl.tight_layout()
pl.show()

########NEW FILE########
__FILENAME__ = plot_grid_ex
import pylab as pl

ax = pl.axes([0.025, 0.025, 0.95, 0.95])

ax.set_xlim(0,4)
ax.set_ylim(0,3)
ax.xaxis.set_major_locator(pl.MultipleLocator(1.0))
ax.xaxis.set_minor_locator(pl.MultipleLocator(0.1))
ax.yaxis.set_major_locator(pl.MultipleLocator(1.0))
ax.yaxis.set_minor_locator(pl.MultipleLocator(0.1))
ax.grid(which='major', axis='x', linewidth=0.75, linestyle='-', color='0.75')
ax.grid(which='minor', axis='x', linewidth=0.25, linestyle='-', color='0.75')
ax.grid(which='major', axis='y', linewidth=0.75, linestyle='-', color='0.75')
ax.grid(which='minor', axis='y', linewidth=0.25, linestyle='-', color='0.75')
ax.set_xticklabels([])
ax.set_yticklabels([])

pl.show()

########NEW FILE########
__FILENAME__ = plot_imshow
import pylab as pl
import numpy as np

def f(x, y):
    return (1 - x / 2 + x ** 5 + y ** 3) * np.exp(-x ** 2 - y ** 2)

n = 10
x = np.linspace(-3, 3, 8 * n)
y = np.linspace(-3, 3, 6 * n)
X, Y = np.meshgrid(x, y)
Z = f(X, Y)
pl.imshow(Z, interpolation='nearest', cmap='bone', origin='lower')
pl.xticks(())
pl.yticks(())

pl.text(-0.05, 1.02, " Imshow:       pl.imshow(...)\n",
        horizontalalignment='left',
        verticalalignment='top',
        size='xx-large',
        bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
        transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n   Display an image to current axes ",
        horizontalalignment='left',
        verticalalignment='top',
        family='Lint McCree Intl BB',
        size='large',
        transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_imshow_ex
import pylab as pl
import numpy as np

def f(x, y):
    return (1 - x / 2 + x ** 5 + y ** 3 ) * np.exp(-x ** 2 - y ** 2)

n = 10
x = np.linspace(-3, 3, 3.5 * n)
y = np.linspace(-3, 3, 3.0 * n)
X, Y = np.meshgrid(x, y)
Z = f(X, Y)

pl.axes([0.025, 0.025, 0.95, 0.95])
pl.imshow(Z, interpolation='nearest', cmap='bone', origin='lower')
pl.colorbar(shrink=.92)

pl.xticks(())
pl.yticks(())
pl.show()

########NEW FILE########
__FILENAME__ = plot_linestyles
import pylab as pl
import numpy as np

def linestyle(ls, i):
    X = i * .5 * np.ones(11)
    Y = np.arange(11)
    pl.plot(X, Y, ls, color=(.0, .0, 1, 1), lw=3, ms=8,
            mfc=(.75, .75, 1, 1), mec=(0, 0, 1, 1))
    pl.text(.5 * i, 10.25, ls, rotation=90, fontsize=15, va='bottom')

linestyles = ['-', '--', ':', '-.', '.', ',', 'o', '^', 'v', '<', '>', 's',
              '+', 'x', 'd', '1', '2', '3', '4', 'h', 'p', '|', '_', 'D', 'H']
n_lines = len(linestyles)

size = 20 * n_lines, 300
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0.01, 1, .9], frameon=False)

for i, ls in enumerate(linestyles):
    linestyle(ls, i)

pl.xlim(-.2, .2 + .5*n_lines)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_linewidth
import pylab as pl

size = 256, 16
dpi = 72.0
figsize = size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, .1, 1, .8], frameon=False)

for i in range(1, 11):
    pl.plot([i, i], [0, 1], color='b', lw=i/2.)

pl.xlim(0, 11)
pl.ylim(0, 1)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_markers
import pylab as pl
import numpy as np

def marker(m, i):
    X = i * .5 * np.ones(11)
    Y = np.arange(11)

    pl.plot(X, Y, color='None', lw=1, marker=m, ms=10, mfc=(.75, .75, 1, 1),
            mec=(0, 0, 1, 1))
    pl.text(.5 * i, 10.25, repr(m), rotation=90, fontsize=15, va='bottom')

markers = [0, 1, 2, 3, 4, 5, 6, 7, 'o', 'h', '_', '1', '2', '3', '4',
          '8', 'p', '^', 'v', '<', '>', '|', 'd', ',', '+', 's', '*',
          '|', 'x', 'D', 'H', '.']

n_markers = len(markers)

size = 20 * n_markers, 300
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0.01, 1, .9], frameon=False)

for i, m in enumerate(markers):
    marker(m, i)

pl.xlim(-.2, .2 + .5 * n_markers)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_mec
import pylab as pl
import numpy as np

size = 256,16
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

for i in range(1, 11):
    r, g, b = np.random.uniform(0, 1, 3)
    pl.plot([i, ], [1, ], 's', markersize=5, markerfacecolor='w',
             markeredgewidth=1.5, markeredgecolor=(r, g, b, 1))

pl.xlim(0, 11)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_mew
import pylab as pl

size = 256, 16
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

for i in range(1,11):
    pl.plot([i, ], [1, ], 's', markersize=5,
         markeredgewidth=1 + i/10., markeredgecolor='k', markerfacecolor='w')
pl.xlim(0, 11)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_mfc
import pylab as pl
import numpy as np

size = 256, 16
dpi = 72.0
figsize = size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

for i in range(1, 11):
    r, g, b = np.random.uniform(0, 1, 3)
    pl.plot([i, ], [1, ], 's', markersize=8, markerfacecolor=(r, g, b, 1),
             markeredgewidth=.1,  markeredgecolor=(0, 0, 0, .5))
pl.xlim(0, 11)
pl.xticks(())
pl.yticks(())
pl.show()

########NEW FILE########
__FILENAME__ = plot_ms
import pylab as pl

size = 256, 16
dpi = 72.0
figsize = size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

for i in range(1, 11):
    pl.plot([i, ], [1, ], 's', markersize=i, markerfacecolor='w',
         markeredgewidth=.5, markeredgecolor='k')

pl.xlim(0, 11)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_multiplot
import pylab as pl

ax = pl.subplot(2, 1, 1)
ax.set_xticklabels([])
ax.set_yticklabels([])

pl.text(-0.05, 1.02, " Multiplot:     pl.subplot(...)\n",
      horizontalalignment='left',
      verticalalignment='top',
      size='xx-large',
      bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
      transform=ax.transAxes)
pl.text(-0.05, 1.01, "\n\n    Plot several plots at once ",
      horizontalalignment='left',
      verticalalignment='top',
      size='large',
      transform=ax.transAxes)

ax = pl.subplot(2, 2, 3)
ax.set_xticklabels([])
ax.set_yticklabels([])

ax = pl.subplot(2, 2, 4)
ax.set_xticklabels([])
ax.set_yticklabels([])

pl.show()

########NEW FILE########
__FILENAME__ = plot_multiplot_ex
import pylab as pl

fig = pl.figure()
fig.subplots_adjust(bottom=0.025, left=0.025, top = 0.975, right=0.975)

pl.subplot(2, 1, 1)
pl.xticks(()), pl.yticks(())

pl.subplot(2, 3, 4)
pl.xticks(())
pl.yticks(())

pl.subplot(2, 3, 5)
pl.xticks(())
pl.yticks(())

pl.subplot(2, 3, 6)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_pie
import pylab as pl
import numpy as np

n = 20
X = np.ones(n)
X[-1] *= 2
pl.pie(X, explode=X*.05, colors = ['%f' % (i/float(n)) for i in range(n)])

fig = pl.gcf()
w, h = fig.get_figwidth(), fig.get_figheight()
r = h / float(w)

pl.xlim(-1.5, 1.5)
pl.ylim(-1.5 * r, 1.5 * r)
pl.xticks(())
pl.yticks(())

pl.text(-0.05, 1.02, " Pie Chart:           pl.pie(...)\n",
        horizontalalignment='left',
        verticalalignment='top',
        size='xx-large',
        bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
        transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n   Make a pie chart of an array ",
        horizontalalignment='left',
        verticalalignment='top',
        size='large',
        transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_pie_ex
import pylab as pl
import numpy as np

n = 20
Z = np.ones(n)
Z[-1] *= 2

pl.axes([0.025, 0.025, 0.95, 0.95])

pl.pie(Z, explode=Z*.05, colors = ['%f' % (i/float(n)) for i in range(n)])
pl.axis('equal')
pl.xticks(())
pl.yticks()

pl.show()

########NEW FILE########
__FILENAME__ = plot_plot
import pylab as pl
import numpy as np

n = 256
X = np.linspace(0, 2, n)
Y = np.sin(2 * np.pi * X)

pl.plot (X, Y, lw=2, color='violet')
pl.xlim(-0.2, 2.2)
pl.xticks(())
pl.ylim(-1.2, 1.2)
pl.yticks(())

pl.text(-0.05, 1.02, " Regular Plot:      pl.plot(...)\n",
        horizontalalignment='left',
        verticalalignment='top',
        size='xx-large',
        bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
        transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n   Plot lines and/or markers ",
        horizontalalignment='left',
        verticalalignment='top',
        size='large',
        transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_plot3d-2
import pylab as pl
from mpl_toolkits.mplot3d import axes3d

ax = pl.gca(projection='3d')
X, Y, Z = axes3d.get_test_data(0.05)
cset = ax.contourf(X, Y, Z)
ax.clabel(cset, fontsize=9, inline=1)

pl.xticks(())
pl.yticks(())
ax.set_zticks(())

ax.text2D(-0.05, 1.05, " 3D plots \n\n",
          horizontalalignment='left',
          verticalalignment='top',
          family='Lint McCree Intl BB',
          size='x-large',
          bbox=dict(facecolor='white', alpha=1.0, width=350,height=60),
          transform=pl.gca().transAxes)

ax.text2D(-0.05, .975, " Plot 2D or 3D data",
          horizontalalignment='left',
          verticalalignment='top',
          family='Lint McCree Intl BB',
          size='medium',
          transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_plot3d
import pylab as pl
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

fig = pl.figure()
ax = Axes3D(fig)
X = np.arange(-4, 4, 0.25)
Y = np.arange(-4, 4, 0.25)
X, Y = np.meshgrid(X, Y)
R = np.sqrt(X ** 2 + Y ** 2)
Z = np.sin(R)

ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap=pl.cm.hot)
ax.contourf(X, Y, Z, zdir='z', offset=-2, cmap=pl.cm.hot)
ax.set_zlim(-2, 2)
pl.xticks(())
pl.yticks(())
ax.set_zticks(())

ax.text2D(0.05, .93, " 3D plots \n",
          horizontalalignment='left',
          verticalalignment='top',
          size='xx-large',
          bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
          transform=pl.gca().transAxes)

ax.text2D(0.05, .87, " Plot 2D or 3D data",
          horizontalalignment='left',
          verticalalignment='top',
          size='large',
          transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_plot3d_ex
import pylab as pl
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

fig = pl.figure()
ax = Axes3D(fig)
X = np.arange(-4, 4, 0.25)
Y = np.arange(-4, 4, 0.25)
X, Y = np.meshgrid(X, Y)
R = np.sqrt(X ** 2 + Y ** 2)
Z = np.sin(R)

ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap=pl.cm.hot)
ax.contourf(X, Y, Z, zdir='z', offset=-2, cmap=pl.cm.hot)
ax.set_zlim(-2, 2)

pl.show()

########NEW FILE########
__FILENAME__ = plot_plot_ex
import pylab as pl
import numpy as np

n = 256
X = np.linspace(-np.pi, np.pi, n, endpoint=True)
Y = np.sin(2 * X)

pl.axes([0.025, 0.025, 0.95, 0.95])

pl.plot(X, Y + 1, color='blue', alpha=1.00)
pl.fill_between(X, 1, Y + 1, color='blue', alpha=.25)

pl.plot(X, Y - 1, color='blue', alpha=1.00)
pl.fill_between(X, -1, Y - 1, (Y - 1) > -1, color='blue', alpha=.25)
pl.fill_between(X, -1, Y - 1, (Y - 1) < -1, color='red',  alpha=.25)

pl.xlim(-np.pi, np.pi)
pl.xticks(())
pl.ylim(-2.5, 2.5)
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_polar
import pylab as pl
import numpy as np

pl.subplot(1, 1, 1, polar=True)

N = 20
theta = np.arange(0.0, 2 * np.pi, 2 * np.pi / N)
radii = 10 * np.random.rand(N)
width = np.pi / 4 * np.random.rand(N)
bars = pl.bar(theta, radii, width=width, bottom=0.0)
for r, bar in zip(radii, bars):
    bar.set_facecolor(pl.cm.jet(r / 10.))
    bar.set_alpha(0.5)
pl.gca().set_xticklabels([])
pl.gca().set_yticklabels([])

pl.text(-0.2, 1.02, " Polar Axis\n",
      horizontalalignment='left',
      verticalalignment='top',
      size='xx-large',
      bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
      transform=pl.gca().transAxes)
pl.text(-0.2, 1.01, "\n\n Plot anything using polar axis ",
      horizontalalignment='left',
      verticalalignment='top',
      size='large',
      transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_polar_ex
import pylab as pl
import numpy as np

ax = pl.axes([0.025, 0.025, 0.95, 0.95], polar=True)

N = 20
theta = np.arange(0.0, 2 * np.pi, 2 * np.pi / N)
radii = 10 * np.random.rand(N)
width = np.pi / 4 * np.random.rand(N)
bars = pl.bar(theta, radii, width=width, bottom=0.0)

for r,bar in zip(radii, bars):
    bar.set_facecolor(pl.cm.jet(r/10.))
    bar.set_alpha(0.5)

ax.set_xticklabels([])
ax.set_yticklabels([])
pl.show()

########NEW FILE########
__FILENAME__ = plot_quiver
import pylab as pl
import numpy as np

n = 8
X, Y = np.mgrid[0:n, 0:n]
T = np.arctan2(Y - n/ 2., X - n / 2.)
R = 10 + np.sqrt((Y - n / 2.) ** 2 + (X - n / 2.) ** 2)
U, V = R * np.cos(T), R * np.sin(T)

pl.quiver(X, Y, U, V, R, alpha=.5)
pl.quiver(X, Y, U, V, edgecolor='k', facecolor='None', linewidth=.5)

pl.xlim(-1, n)
pl.xticks(())
pl.ylim(-1, n)
pl.yticks(())

pl.text(-0.05, 1.02, " Quiver Plot:    pl.quiver(...)\n",
      horizontalalignment='left',
      verticalalignment='top',
      size='xx-large',
      bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
      transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n    Plot a 2-D field of arrows ",
      horizontalalignment='left',
      verticalalignment='top',
      size='large',
      transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_quiver_ex
import pylab as pl
import numpy as np

n = 8
X, Y = np.mgrid[0:n, 0:n]
T = np.arctan2(Y - n / 2., X - n/2.)
R = 10 + np.sqrt((Y - n / 2.0) ** 2 + (X - n / 2.0) ** 2)
U, V = R * np.cos(T), R * np.sin(T)

pl.axes([0.025, 0.025, 0.95, 0.95])
pl.quiver(X, Y, U, V, R, alpha=.5)
pl.quiver(X, Y, U, V, edgecolor='k', facecolor='None', linewidth=.5)

pl.xlim(-1, n)
pl.xticks(())
pl.ylim(-1, n)
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_scatter
import pylab as pl
import numpy as np

n = 1024
X = np.random.normal(0, 1, n)
Y = np.random.normal(0, 1, n)

T = np.arctan2(Y,X)

pl.scatter(X, Y, s=75, c=T, alpha=.5)
pl.xlim(-1.5, 1.5)
pl.xticks(())
pl.ylim(-1.5, 1.5)
pl.yticks(())

pl.text(-0.05, 1.02, " Scatter Plot:  pl.scatter(...)\n",
      horizontalalignment='left',
      verticalalignment='top',
      size='xx-large',
      bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
      transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n   Make a scatter plot of x versus y ",
      horizontalalignment='left',
      verticalalignment='top',
      size='large',
      transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_scatter_ex
import pylab as pl
import numpy as np

n = 1024
X = np.random.normal(0, 1, n)
Y = np.random.normal(0, 1, n)
T = np.arctan2(Y, X)

pl.axes([0.025, 0.025, 0.95, 0.95])
pl.scatter(X, Y, s=75, c=T, alpha=.5)

pl.xlim(-1.5, 1.5)
pl.xticks(())
pl.ylim(-1.5, 1.5)
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_solid_capstyle
import pylab as pl
import numpy as np

size = 256, 16
dpi = 72.0
figsize= size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

pl.plot(np.arange(4), np.ones(4), color="blue", linewidth=8,
        solid_capstyle='butt')

pl.plot(5 + np.arange(4), np.ones(4), color="blue", linewidth=8,
        solid_capstyle='round')

pl.plot(10 + np.arange(4), np.ones(4), color="blue", linewidth=8,
        solid_capstyle='projecting')

pl.xlim(0, 14)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_solid_joinstyle
import pylab as pl
import numpy as np

size = 256, 16
dpi = 72.0
figsize = size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)
pl.axes([0, 0, 1, 1], frameon=False)

pl.plot(np.arange(3), [0, 1, 0], color="blue", linewidth=8,
        solid_joinstyle='miter')
pl.plot(4 + np.arange(3), [0, 1, 0], color="blue", linewidth=8,
        solid_joinstyle='bevel')
pl.plot(8 + np.arange(3), [0, 1, 0], color="blue", linewidth=8,
        solid_joinstyle='round')

pl.xlim(0, 12)
pl.ylim(-1, 2)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_subplot-grid
import pylab as pl

pl.figure(figsize=(6, 4))
pl.subplot(2, 2, 1)
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'subplot(2,2,1)', ha='center', va='center',
        size=20, alpha=.5)

pl.subplot(2, 2, 2)
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'subplot(2,2,2)', ha='center', va='center',
        size=20, alpha=.5)

pl.subplot(2, 2, 3)
pl.xticks(())
pl.yticks(())

pl.text(0.5, 0.5, 'subplot(2,2,3)', ha='center', va='center',
        size=20, alpha=.5)

pl.subplot(2, 2, 4)
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'subplot(2,2,4)', ha='center', va='center',
        size=20, alpha=.5)

pl.tight_layout()
pl.show()

########NEW FILE########
__FILENAME__ = plot_subplot-horizontal
import pylab as pl

pl.figure(figsize=(6, 4))
pl.subplot(2, 1, 1)
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'subplot(2,1,1)', ha='center', va='center',
        size=24, alpha=.5)

pl.subplot(2, 1, 2)
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'subplot(2,1,2)', ha='center', va='center',
        size=24, alpha=.5)

pl.tight_layout()
pl.show()

########NEW FILE########
__FILENAME__ = plot_subplot-vertical
import pylab as pl

pl.figure(figsize=(6, 4))
pl.subplot(1, 2, 1)
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'subplot(1,2,1)', ha='center', va='center',
        size=24, alpha=.5)

pl.subplot(1, 2, 2)
pl.xticks(())
pl.yticks(())
pl.text(0.5, 0.5, 'subplot(1,2,2)', ha='center', va='center',
        size=24, alpha=.5)

pl.tight_layout()
pl.show()

########NEW FILE########
__FILENAME__ = plot_text
import pylab as pl
import numpy as np

fig = pl.figure()
pl.xticks(())
pl.yticks(())

eqs = []
eqs.append((r"$W^{3\beta}_{\delta_1 \rho_1 \sigma_2} = U^{3\beta}_{\delta_1 \rho_1} + \frac{1}{8 \pi 2} \int^{\alpha_2}_{\alpha_2} d \alpha^\prime_2 \left[\frac{ U^{2\beta}_{\delta_1 \rho_1} - \alpha^\prime_2U^{1\beta}_{\rho_1 \sigma_2} }{U^{0\beta}_{\rho_1 \sigma_2}}\right]$"))
eqs.append((r"$\frac{d\rho}{d t} + \rho \vec{v}\cdot\nabla\vec{v} = -\nabla p + \mu\nabla^2 \vec{v} + \rho \vec{g}$"))
eqs.append((r"$\int_{-\infty}^\infty e^{-x^2}dx=\sqrt{\pi}$"))
eqs.append((r"$E = mc^2 = \sqrt{{m_0}^2c^4 + p^2c^2}$"))
eqs.append((r"$F_G = G\frac{m_1m_2}{r^2}$"))

for i in range(24):
    index = np.random.randint(0,len(eqs))
    eq = eqs[index]
    size = np.random.uniform(12,32)
    x,y = np.random.uniform(0,1,2)
    alpha = np.random.uniform(0.25,.75)
    pl.text(x, y, eq, ha='center', va='center', color="#11557c", alpha=alpha,
         transform=pl.gca().transAxes, fontsize=size, clip_on=True)

pl.text(-0.05, 1.02, " Text:                   pl.text(...)\n",
        horizontalalignment='left',
        verticalalignment='top',
        size='xx-large',
        bbox=dict(facecolor='white', alpha=1.0, width=400, height=65),
        transform=pl.gca().transAxes)

pl.text(-0.05, 1.01, "\n\n     Draw any kind of text ",
        horizontalalignment='left',
        verticalalignment='top',
        size='large',
        transform=pl.gca().transAxes)

pl.show()

########NEW FILE########
__FILENAME__ = plot_text_ex
import pylab as pl
import numpy as np

eqs = []
eqs.append((r"$W^{3\beta}_{\delta_1 \rho_1 \sigma_2} = U^{3\beta}_{\delta_1 \rho_1} + \frac{1}{8 \pi 2} \int^{\alpha_2}_{\alpha_2} d \alpha^\prime_2 \left[\frac{ U^{2\beta}_{\delta_1 \rho_1} - \alpha^\prime_2U^{1\beta}_{\rho_1 \sigma_2} }{U^{0\beta}_{\rho_1 \sigma_2}}\right]$"))
eqs.append((r"$\frac{d\rho}{d t} + \rho \vec{v}\cdot\nabla\vec{v} = -\nabla p + \mu\nabla^2 \vec{v} + \rho \vec{g}$"))
eqs.append((r"$\int_{-\infty}^\infty e^{-x^2}dx=\sqrt{\pi}$"))
eqs.append((r"$E = mc^2 = \sqrt{{m_0}^2c^4 + p^2c^2}$"))
eqs.append((r"$F_G = G\frac{m_1m_2}{r^2}$"))

pl.axes([0.025, 0.025, 0.95, 0.95])

for i in range(24):
    index = np.random.randint(0, len(eqs))
    eq = eqs[index]
    size = np.random.uniform(12, 32)
    x,y = np.random.uniform(0, 1, 2)
    alpha = np.random.uniform(0.25, .75)
    pl.text(x, y, eq, ha='center', va='center', color="#11557c", alpha=alpha,
         transform=pl.gca().transAxes, fontsize=size, clip_on=True)
pl.xticks(())
pl.yticks(())

pl.show()

########NEW FILE########
__FILENAME__ = plot_ticks
import pylab as pl
import numpy as np


def tickline():
    pl.xlim(0, 10), pl.ylim(-1, 1), pl.yticks([])
    ax = pl.gca()
    ax.spines['right'].set_color('none')
    ax.spines['left'].set_color('none')
    ax.spines['top'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.spines['bottom'].set_position(('data',0))
    ax.yaxis.set_ticks_position('none')
    ax.xaxis.set_minor_locator(pl.MultipleLocator(0.1))
    ax.plot(np.arange(11), np.zeros(11), color='none')
    return ax

locators = [
                'pl.NullLocator()',
                'pl.MultipleLocator(1.0)',
                'pl.FixedLocator([0, 2, 8, 9, 10])',
                'pl.IndexLocator(3, 1)',
                'pl.LinearLocator(5)',
                'pl.LogLocator(2, [1.0])',
                'pl.AutoLocator()',
            ]

n_locators = len(locators)

size = 512, 40 * n_locators
dpi = 72.0
figsize = size[0] / float(dpi), size[1] / float(dpi)
fig = pl.figure(figsize=figsize, dpi=dpi)
fig.patch.set_alpha(0)


for i, locator in enumerate(locators):
    pl.subplot(n_locators, 1, i + 1)
    ax = tickline()
    ax.xaxis.set_major_locator(eval(locator))
    pl.text(5, 0.3, locator[3:], ha='center')

pl.subplots_adjust(bottom=.01, top=.99, left=.01, right=.99)
pl.show()

########NEW FILE########
__FILENAME__ = plot_ugly
import numpy as np
import matplotlib
matplotlib.use('Agg')
import pylab as pl

matplotlib.rc('grid', color='black', linestyle='-', linewidth=1)

fig = pl.figure(figsize=(5,4),dpi=72)
axes = fig.add_axes([0.01, 0.01, .98, 0.98], axisbg='.75')
X = np.linspace(0, 2, 40, endpoint=True)
Y = np.sin(2 * np.pi * X)
pl.plot(X, Y, lw=.05, c='b', antialiased=False)

pl.xticks(())
pl.yticks(np.arange(-1., 1., 0.2))
pl.grid()
ax = pl.gca()

pl.show()

########NEW FILE########
__FILENAME__ = 1_0_prime_sieve
"""
Computing prime numbers with the archimedean sieve.

(Of course, this is not an optimal way for computing prime numbers...)

"""

import numpy as np

eratosthenes = True

# maximum number
N = 10000

# mask for prime numbers
mask = np.ones([N], dtype=bool)

if not eratosthenes:
    # simple prime sieve
    mask[:2] = False
    for j in xrange(2, int(np.sqrt(N)) + 1):
        mask[j*j::j] = False

else:
    # Eratosthenes sieve
    mask[:2] = False
    for j in xrange(2, int(np.sqrt(N)) + 1):
        if mask[j]:
            mask[j*j::j] = False

# print indices where mask is True
print np.nonzero(mask)[0]

########NEW FILE########
__FILENAME__ = 1_1_array_creation
import numpy as np

a = np.ones((4, 4), dtype=int)
a[3,1] = 6
a[2,3] = 2

b = np.zeros((6, 5))
b[1:] = np.diag(np.arange(2, 7))

print a
print b

########NEW FILE########
__FILENAME__ = 1_2_text_data
import numpy as np

data = np.loadtxt('../../../data/populations.txt')
reduced_data = data[5:,:-1]
np.savetxt('pop2.txt', reduced_data)

########NEW FILE########
__FILENAME__ = 1_3_tiling
import numpy as np

block = np.array([[4, 3], [2, 1]])
a = np.tile(block, (2, 3))

print a

########NEW FILE########
__FILENAME__ = 2_1_matrix_manipulations
import numpy as np
from numpy import newaxis

# Part 1.

a = np.arange(1, 16).reshape(3, -1).T
print a

# Part 2.

########NEW FILE########
__FILENAME__ = 2_2_data_statistics
import numpy as np

data = np.loadtxt('../../../data/populations.txt')
year, hares, lynxes, carrots = data.T
populations = data[:,1:]

print "       Hares, Lynxes, Carrots"
print "Mean:", populations.mean(axis=0)
print "Std:", populations.std(axis=0)

j_max_years = np.argmax(populations, axis=0)
print "Max. year:", year[j_max_years]

max_species = np.argmax(populations, axis=1)
species = np.array(['Hare', 'Lynx', 'Carrot'])
print "Max species:"
print year
print species[max_species]

above_50000 = np.any(populations > 50000, axis=1)
print "Any above 50000:", year[above_50000]

j_top_2 = np.argsort(populations, axis=0)[:2]
print "Top 2 years with lowest populations for each:"
print year[j_top_2]

hare_grad = np.gradient(hares, 1.0)
print "diff(Hares) vs. Lynxes correlation", np.corrcoef(hare_grad, lynxes)[0,1]

import matplotlib.pyplot as plt
plt.plot(year, hare_grad, year, -lynxes)
plt.savefig('plot.png')

########NEW FILE########
__FILENAME__ = 2_3_crude_integration
import numpy as np
from numpy import newaxis

def f(a, b, c):
    return a**b - c

a = np.linspace(0, 1, 24)
b = np.linspace(0, 1, 12)
c = np.linspace(0, 1, 6)

samples = f(a[:,newaxis,newaxis],
            b[newaxis,:,newaxis],
            c[newaxis,newaxis,:])

# or,
#
# a, b, c = np.ogrid[0:1:24j, 0:1:12j, 0:1:6j]
# samples = f(a, b, c)

integral = samples.mean()

print "Approximation:", integral
print "Exact:", np.log(2) - 0.5

########NEW FILE########
__FILENAME__ = 2_4_mandelbrot
"""
Compute the Mandelbrot fractal
"""
import numpy as np
import matplotlib.pyplot as plt
from numpy import newaxis

def compute_mandelbrot(N_max, some_threshold, nx, ny):
    # A grid of c-values
    x = np.linspace(-2, 1, nx)
    y = np.linspace(-1.5, 1.5, ny)

    c = x[:,newaxis] + 1j*y[newaxis,:]

    # Mandelbrot iteration

    z = c
    for j in xrange(N_max):
        z = z**2 + c

    mandelbrot_set = (abs(z) < some_threshold)

    return mandelbrot_set

# Save

mandelbrot_set = compute_mandelbrot(50, 50., 601, 401)

plt.imshow(mandelbrot_set.T, extent=[-2, 1, -1.5, 1.5])
plt.gray()
plt.savefig('mandelbrot.png')

########NEW FILE########
__FILENAME__ = 2_5_markov_chain
import numpy as np

np.random.seed(1234)

n_states = 5
n_steps = 50
tolerance = 1e-5

# Random transition matrix and state vector
P = np.random.rand(n_states, n_states)
p = np.random.rand(n_states)

# Normalize rows in P
P /= P.sum(axis=1)[:,np.newaxis]

# Normalize p
p /= p.sum()

# Take steps
for k in xrange(n_steps):
    p = P.T.dot(p)

p_50 = p
print p_50

# Compute stationary state
w, v = np.linalg.eig(P.T)

j_stationary = np.argmin(abs(w - 1.0))
p_stationary = v[:,j_stationary].real
p_stationary /= p_stationary.sum()
print p_stationary

# Compare
if all(abs(p_50 - p_stationary) < tolerance):
    print "Tolerance satisfied in infty-norm"

if np.linalg.norm(p_50 - p_stationary) < tolerance:
    print "Tolerance satisfied in 2-norm"

########NEW FILE########
__FILENAME__ = 2_a_call_fortran
import numpy as np
import fortran_module

def some_function(input):
    """
    Call a Fortran routine, and preserve input shape
    """
    input = np.asarray(input)
    # fortran_module.some_function() only accepts 1-D arrays!
    output = fortran_module.some_function(input.ravel())
    return output.reshape(input.shape)

print some_function(np.array([1, 2, 3]))
print some_function(np.array([[1, 2], [3, 4]]))

########NEW FILE########
__FILENAME__ = curvefit_temperature_data
import numpy as np
import matplotlib.pyplot as plt
from scipy import optimize


temp_max = np.array([17,  19,  21,  28,  33,  38, 37,  37,  31,  23,  19,  18])
temp_min = np.array([-62, -59, -56, -46, -32, -18, -9, -13, -25, -46, -52, -58])

def yearly_temps(times, avg, ampl, time_offset):
    return avg + ampl * np.cos((times + time_offset) * 2 * np.pi / times.max())

months = np.arange(12)
res_max, cov_max = optimize.curve_fit(yearly_temps, months,
                                      temp_max, [20, 10, 0])
res_min, cov_min = optimize.curve_fit(yearly_temps, months,
                                      temp_min, [-40, 20, 0])

days = np.linspace(0, 12, num=365)
plt.plot(months, temp_max, 'ro')
plt.plot(days, yearly_temps(days, *res_max), 'r-')
plt.plot(months, temp_min, 'bo')
plt.plot(days, yearly_temps(days, *res_min), 'b-')
plt.xlabel('Month')
plt.ylabel('Temperature ($^\circ$C)')

plt.show()

########NEW FILE########
__FILENAME__ = data_file
"""Script to read in a column of numbers and calculate the min, max and sum.

Data is stored in data.txt.
"""

def load_data(filename):
    fp = open(filename)
    data_string = fp.read()
    fp.close()

    data = []
    for x in data_string.split():
        # Data is read in as a string. We need to convert it to floats
        data.append(float(x))

    # Could instead use the following one line with list comprehensions!
    # data = [float(x) for x in data_string.split()]
    return data

if __name__ == '__main__':
    data = load_data('data.txt')
    # Python provides these basic math functions
    print('min: %f' % min(data))
    print('max: %f' % max(data))
    print('sum: %f' % sum(data))

########NEW FILE########
__FILENAME__ = dir_sort
"""
Script to list all the '.py' files in a directory, in the order of file
name length.
"""

import os
import sys


def filter_and_sort(file_list):
    """ Out of a list of file names, returns only the ones ending by
        '.py', ordered with increasing file name length.
    """
    file_list = [filename for filename in file_list 
                          if filename.endswith('.py')]

    def key(item):
        return len(item)

    file_list.sort(key=key)
    return file_list


if __name__ == '__main__':
    file_list = os.listdir(sys.argv[-1])
    sorted_file_list = filter_and_sort(file_list)
    print sorted_file_list


########NEW FILE########
__FILENAME__ = fft_image_denoise
import numpy as np
from scipy import fftpack
import matplotlib.pyplot as plt


def plot_spectrum(F):
    plt.imshow(np.log(5 + np.abs(F)))


# read image
im = plt.imread('../../data/moonlanding.png').astype(float)

# Compute the 2d FFT of the input image
F = fftpack.fft2(im)

# In the lines following, we'll make a copy of the original spectrum and
# truncate coefficients.

# Define the fraction of coefficients (in each direction) we keep
keep_fraction = 0.1

# Call ff a copy of the original transform. Numpy arrays have a copy
# method for this purpose.
ff = F.copy()

# Set r and c to be the number of rows and columns of the array.
r, c = ff.shape

# Set to zero all rows with indices between r*keep_fraction and # r*(1-keep_fraction):
ff[r*keep_fraction:r*(1-keep_fraction)] = 0

# Similarly with the columns:
ff[:, c*keep_fraction:c*(1-keep_fraction)] = 0

# Reconstruct the denoised image from the filtered spectrum, keep only the
# real part for display.
im_new = fftpack.ifft2(ff).real

# Show the results
plt.figure(figsize=(12,8))
plt.subplot(221)
plt.title('Original image')
plt.imshow(im, plt.cm.gray)
plt.subplot(222)
plt.title('Fourier transform')
plot_spectrum(F)
plt.subplot(224)
plt.title('Filtered Spectrum')
plot_spectrum(ff)
plt.subplot(223)
plt.title('Reconstructed Image')
plt.imshow(im_new, plt.cm.gray)

# Adjust the spacing between subplots for readability
plt.subplots_adjust(hspace=0.4)

plt.show()

########NEW FILE########
__FILENAME__ = image_blur
"""
Simple image blur by convolution with a Gaussian kernel
"""

import numpy as np
from scipy import fftpack
import matplotlib.pyplot as plt

# read image
img = plt.imread('../../data/elephant.png')

# prepare an 1-D Gaussian convolution kernel
t = np.linspace(-10, 10, 30)
bump = np.exp(-0.1*t**2)
bump /= np.trapz(bump) # normalize the integral to 1

# make a 2-D kernel out of it
kernel = bump[:, np.newaxis] * bump[np.newaxis, :]

# padded fourier transform, with the same shape as the image
kernel_ft = fftpack.fft2(kernel, shape=img.shape[:2], axes=(0, 1))

# convolve
img_ft = fftpack.fft2(img, axes=(0, 1))
img2_ft = kernel_ft[:, :, np.newaxis] * img_ft
img2 = fftpack.ifft2(img2_ft, axes=(0, 1)).real

# clip values to range
img2 = np.clip(img2, 0, 1)

# plot output
plt.imshow(img2)
plt.show()

# Further exercise (only if you are familiar with this stuff):
#
# A "wrapped border" appears in the upper left and top edges of the
# image. This is because the padding is not done correctly, and does
# not take the kernel size into account (so the convolution "flows out
# of bounds of the image").  Try to remove this artifact.

########NEW FILE########
__FILENAME__ = path_site
"""Script to search the PYTHONPATH for the module site.py"""

import os
import sys
import glob

def find_module(module):
    result = []
    # Loop over the list of paths in sys.path
    for subdir in sys.path:
        # Join the subdir path with the module we're searching for
        pth = os.path.join(subdir, module)
        # Use glob to test if the pth is exists
        res = glob.glob(pth)
        # glob returns a list, if it is not empty, the pth exists
        if len(res) > 0:
            result.append(res)
    return result


if __name__ == '__main__':
    result = find_module('site.py')
    print result
    

########NEW FILE########
__FILENAME__ = periodicity_finder
"""
Discover the periods in ../../data/populations.txt
"""
import numpy as np
import matplotlib.pyplot as plt

data = np.loadtxt('../../data/populations.txt')
years = data[:, 0]
populations = data[:, 1:]

ft_populations = np.fft.fft(populations, axis=0)
frequencies = np.fft.fftfreq(populations.shape[0], years[1] - years[0])
periods = 1 / frequencies

plt.figure()
plt.plot(years, populations * 1e-3)
plt.xlabel('Year')
plt.ylabel('Population number ($\cdot10^3$)')
plt.legend(['hare', 'lynx', 'carrot'], loc=1)

plt.figure()
plt.plot(periods, abs(ft_populations) * 1e-3, 'o')
plt.xlim(0, 22)
plt.xlabel('Period')
plt.ylabel('Power ($\cdot10^3$)')

plt.show()

# There's probably a period of around 10 years (obvious from the
# plot), but for this crude a method, there's not enough data to say
# much more.

########NEW FILE########
__FILENAME__ = pi_wallis
"""
The correction for the calculation of pi using the Wallis formula.
"""
from __future__ import division

pi = 3.14159265358979312

my_pi = 1.

for i in range(1, 100000):
    my_pi *= 4 * i ** 2 / (4 * i ** 2 - 1.)

my_pi *= 2

print pi
print my_pi
print abs(pi - my_pi)

###############################################################################
num = 1
den = 1
for i in range(1, 100000):
    tmp = 4 * i * i
    num *= tmp
    den *= tmp - 1

better_pi = 2 * (num / den)

print pi
print better_pi
print abs(pi - better_pi)
print abs(my_pi - better_pi)

###############################################################################
# Solution in a single line using more adcanved constructs (reduce, lambda,
# list comprehensions
print 2 * reduce(lambda x, y: x * y,
                 [float((4 * (i ** 2))) / ((4 * (i ** 2)) - 1)
                 for i in range(1, 100000)])

########NEW FILE########
__FILENAME__ = quick_sort
"""
Implement the quick sort algorithm.
"""

def qsort(lst):
    """ Quick sort: returns a sorted copy of the list.
    """
    if len(lst) <= 1:
        return lst
    pivot, rest    = lst[0], lst[1:]

    # Could use list comprehension:
    # less_than      = [ lt for lt in rest if lt < pivot ]

    less_than = []
    for lt in rest:
        if lt < pivot:
            less_than.append(lt)

    # Could use list comprehension:
    # greater_equal  = [ ge for ge in rest if ge >= pivot ]

    greater_equal = []
    for ge in rest:
        if ge >= pivot:
            greater_equal.append(ge)
    return qsort(less_than) + [pivot] + qsort(greater_equal)

# And now check that qsort does sort:
assert qsort(range(10)) == range(10)
assert qsort(range(10)[::-1]) == range(10)
assert qsort([1, 4, 2, 5, 3]) == sorted([1, 4, 2, 5, 3])

########NEW FILE########
__FILENAME__ = test_dir_sort
"""
Test the dir_sort logic.
"""
import dir_sort

def test_filter_and_sort():
    # Test that non '.py' files are not filtered.
    file_list = ['a', 'aaa', 'aa', '', 'z', 'zzzzz']
    file_list2 = dir_sort.filter_and_sort(file_list)
    assert len(file_list2) == 0

    # Test that the otuput file list is ordered by length.
    file_list = [ n + '.py' for n in file_list]
    file_list2 = dir_sort.filter_and_sort(file_list)
    name1 = file_list2.pop(0)
    for name in file_list2:
        assert len(name1) <= len(name)


if __name__ == '__main__':
    test_filter_and_sort()


########NEW FILE########
__FILENAME__ = plot_cumulative_wind_speed_prediction
"""Generate the image cumulative-wind-speed-prediction.png
for the interpolate section of scipy.rst.
"""

import numpy as np
from scipy.interpolate import UnivariateSpline
import pylab as pl

max_speeds = np.load('max-speeds.npy')
years_nb = max_speeds.shape[0]

cprob = (np.arange(years_nb, dtype=np.float32) + 1)/(years_nb + 1)
sorted_max_speeds = np.sort(max_speeds)
speed_spline = UnivariateSpline(cprob, sorted_max_speeds)
nprob = np.linspace(0, 1, 1e2)
fitted_max_speeds = speed_spline(nprob)

fifty_prob = 1. - 0.02
fifty_wind = speed_spline(fifty_prob)

pl.figure()
pl.plot(sorted_max_speeds, cprob, 'o')
pl.plot(fitted_max_speeds, nprob, 'g--')
pl.plot([fifty_wind], [fifty_prob], 'o', ms=8., mfc='y', mec='y')
pl.text(30, 0.05, '$V_{50} = %.2f \, m/s$' % fifty_wind)
pl.plot([fifty_wind, fifty_wind], [pl.axis()[2], fifty_prob], 'k--')
pl.xlabel('Annual wind speed maxima [$m/s$]')
pl.ylabel('Cumulative probability')

########NEW FILE########
__FILENAME__ = plot_gumbell_wind_speed_prediction
"""Generate the exercise results on the Gumbell distribution
"""
import numpy as np
from scipy.interpolate import UnivariateSpline
import pylab as pl


def gumbell_dist(arr):
    return -np.log(-np.log(arr))

years_nb = 21
wspeeds = np.load('sprog-windspeeds.npy')
max_speeds = np.array([arr.max() for arr in np.array_split(wspeeds, years_nb)])
sorted_max_speeds = np.sort(max_speeds)

cprob = (np.arange(years_nb, dtype=np.float32) + 1)/(years_nb + 1)
gprob = gumbell_dist(cprob)
speed_spline = UnivariateSpline(gprob, sorted_max_speeds, k=1)
nprob = gumbell_dist(np.linspace(1e-3, 1-1e-3, 1e2))
fitted_max_speeds = speed_spline(nprob)

fifty_prob = gumbell_dist(49./50.)
fifty_wind = speed_spline(fifty_prob)

pl.figure()
pl.plot(sorted_max_speeds, gprob, 'o')
pl.plot(fitted_max_speeds, nprob, 'g--')
pl.plot([fifty_wind], [fifty_prob], 'o', ms=8., mfc='y', mec='y')
pl.plot([fifty_wind, fifty_wind], [pl.axis()[2], fifty_prob], 'k--')
pl.text(35, -1, r'$V_{50} = %.2f \, m/s$' % fifty_wind)
pl.xlabel('Annual wind speed maxima [$m/s$]')
pl.ylabel('Gumbell cumulative probability')
pl.show()

########NEW FILE########
__FILENAME__ = plot_sprog_annual_maxima

"""Generate the exercise results on the Gumbell distribution
"""
import numpy as np
from scipy.interpolate import UnivariateSpline
import pylab as pl


def gumbell_dist(arr):
    return -np.log(-np.log(arr))

years_nb = 21
wspeeds = np.load('sprog-windspeeds.npy')
max_speeds = np.array([arr.max() for arr in np.array_split(wspeeds, years_nb)])
sorted_max_speeds = np.sort(max_speeds)

cprob = (np.arange(years_nb, dtype=np.float32) + 1)/(years_nb + 1)
gprob = gumbell_dist(cprob)
speed_spline = UnivariateSpline(gprob, sorted_max_speeds, k=1)
nprob = gumbell_dist(np.linspace(1e-3, 1-1e-3, 1e2))
fitted_max_speeds = speed_spline(nprob)

fifty_prob = gumbell_dist(49./50.)
fifty_wind = speed_spline(fifty_prob)

pl.figure()
pl.bar(np.arange(years_nb) + 1, max_speeds)
pl.axis('tight')
pl.xlabel('Year')
pl.ylabel('Annual wind speed maxima [$m/s$]')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# sphinx-quickstart on Fri Nov 28 22:10:09 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.abspath('sphinxext'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 
              'sphinx.ext.doctest', 
              'sphinx.ext.todo',
              #'matplotlib.sphinxext.plot_directive', 
              'plot_directive',
              'ipython_console_highlighting',
              'matplotlib.sphinxext.only_directives',
              'matplotlib.sphinxext.mathmpl',
              ] #'sphinx.ext.intersphinx']

doctest_test_doctest_blocks = 'true'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Introduction to Python for Science'
copyright = u'2009, Gaël Varoquaux'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ''
# The full version, including alpha/beta/rc tags.
release = '1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'en' 

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

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

# Flag to show todo items in rendered output
todo_include_todos = True

# Options for HTML output
# -----------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'sphinxdoc'

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Python for science"

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
html_static_path = ['_static']

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
html_use_index = False 

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'python4science'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'python4science.tex', ur'Introduction to Python for Science',
   ur'Gaël Varoquaux', 'manual'),
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

# Additional stuff for the LaTeX preamble.
latex_preamble = """
\definecolor{VerbatimColor}{rgb}{0.95,1,0.833}
\definecolor{VerbatimBorderColor}{rgb}{0.6,0.6,0.6}
"""

latex_elements = {
    'classoptions': ',oneside,openany',
    'babel': '\usepackage[english]{babel}',
    'tableofcontents': '%\\tableofcontents',
} 

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/dev': None}

########NEW FILE########
__FILENAME__ = animate_data
"""
A small demo of data animation
"""
import numpy as np
from mayavi import mlab

# Create some simple data
x , y , z = np.ogrid[-5:5:100j ,-5:5:100j, -5:5:100j]
scalars = np.sin(x * y * z) / (x * y * z)

iso = mlab.contour3d(scalars, transparent=True, contours=[0.5])
for i in range(1, 20):
    scalars = np.sin(i * x * y * z) /(x * y * z)
    iso.mlab_source.scalars = scalars

# Start the event loop, if needed
mlab.show()

########NEW FILE########
__FILENAME__ = coil_application
"""
=================
Coil Application
=================

An application to visualize the field create by a list of
coils.

This code is fairly complex, but it is actuallty a very rich application,
and a full-blown example of what you might want to do
"""

import numpy as np
from scipy import linalg, special
from traits.api import HasTraits, Array, CFloat, Str, List, \
   Instance, on_trait_change
from traitsui.api import Item, View, HGroup, ListEditor, \
        HSplit, VSplit, spring
from mayavi.core.ui.api import EngineView, MlabSceneModel, \
        SceneEditor

##############################################################################
# A current loop

class Loop(HasTraits):
    """ A current loop.
    """
    direction = Array(float, value=(0, 0, 1), cols=3,
                    shape=(3,), desc='directing vector of the loop',
                    enter_set=True, auto_set=False)

    # CFloat tries to convert automatically to floats
    radius    = CFloat(0.1, desc='radius of the loop',
                    enter_set=True, auto_set=False)

    position  = Array(float, value=(0, 0, 0), cols=3,
                    shape=(3,), desc='position of the center of the loop',
                    enter_set=True, auto_set=False)

    plot      = None

    name      = Str

    view = View(HGroup(Item('name', style='readonly', show_label=False),
                       spring, 'radius'),
                'position', 'direction', '_')

    # For a Borg-like pattern
    __shared_state = {'number':0}

    def __init__(self, **traits):
        HasTraits.__init__(self, **traits)
        self.__shared_state['number'] += 1
        self.name =  'Coil %i' % self.__shared_state['number']

    def base_vectors(self):
        """ Returns 3 orthognal base vectors, the first one colinear to
            the axis of the loop.
        """
        # normalize n
        n = self.direction / (self.direction**2).sum(axis=-1)

        # choose two vectors perpendicular to n 
        # choice is arbitrary since the coil is symetric about n
        if  np.abs(n[0])==1 :
            l = np.r_[n[2], 0, -n[0]]
        else:
            l = np.r_[0, n[2], -n[1]]

        l /= (l**2).sum(axis=-1)
        m = np.cross(n, l)
        return n, l, m

    @on_trait_change('direction,radius,position')
    def redraw(self):
        if hasattr(self, 'app'):
            self.mk_B_field()
            if self.app.scene._renderer is not None:
                self.display()
                self.app.visualize_field()

    def display(self, half=False):
        """
        Display the coil in the 3D view.
        If half is True, display only one half of the coil.
        """
        n, l, m = self.base_vectors()
        theta = np.linspace(0, (2-half)*np.pi, 30)
        theta = theta[..., np.newaxis]
        coil = self.radius*(np.sin(theta)*l + np.cos(theta)*m)
        coil += self.position
        coil_x, coil_y, coil_z = coil.T
        if self.plot is None:
            self.plot = self.app.scene.mlab.plot3d(coil_x, coil_y, coil_z, 
                                    tube_radius=0.007, color=(0, 0, 1),
                                    name=self.name )
        else:
            self.plot.mlab_source.set(x=coil_x, y=coil_y, z=coil_z)

    def mk_B_field(self):
        """
        returns the magnetic field for the current loop calculated 
        from eqns (1) and (2) in Phys Rev A Vol. 35, N 4, pp. 1535-1546; 1987. 

        return: 
            B is a vector for the B field at point r in inverse units of 
        (mu I) / (2 pi d) 
        for I in amps and d in meters and mu = 4 pi * 10^-7 we get Tesla 
        """
        ### Translate the coordinates in the coil's frame
        n, l, m = self.base_vectors()
        R       = self.radius
        r0      = self.position
        r       = np.c_[np.ravel(self.app.X), np.ravel(self.app.Y),
                                                np.ravel(self.app.Z)]

        # transformation matrix coil frame to lab frame
        trans = np.vstack((l, m, n))

        r -= r0	  #point location from center of coil
        r = np.dot(r, linalg.inv(trans) ) 	    #transform vector to coil frame 

        #### calculate field

        # express the coordinates in polar form
        x = r[:, 0]
        y = r[:, 1]
        z = r[:, 2]
        rho = np.sqrt(x**2 + y**2)
        theta = np.arctan(x/y)

        E = special.ellipe((4 * R * rho)/( (R + rho)**2 + z**2))
        K = special.ellipk((4 * R * rho)/( (R + rho)**2 + z**2))
        Bz =  1/np.sqrt((R + rho)**2 + z**2) * ( 
                    K 
                  + E * (R**2 - rho**2 - z**2)/((R - rho)**2 + z**2) 
                )
        Brho = z/(rho*np.sqrt((R + rho)**2 + z**2)) * ( 
                -K 
                + E * (R**2 + rho**2 + z**2)/((R - rho)**2 + z**2) 
                )
        # On the axis of the coil we get a divided by zero here. This returns a
        # NaN, where the field is actually zero :
        Brho[np.isnan(Brho)] = 0

        B = np.c_[np.cos(theta)*Brho, np.sin(theta)*Brho, Bz ]

        # Rotate the field back in the lab's frame
        B = np.dot(B, trans)

        Bx, By, Bz = B.T
        Bx = np.reshape(Bx, self.app.X.shape)
        By = np.reshape(By, self.app.X.shape)
        Bz = np.reshape(Bz, self.app.X.shape)

        Bnorm = np.sqrt(Bx**2 + By**2 + Bz**2)

        # We need to threshold ourselves, rather than with VTK, to be able 
        # to use an ImageData
        Bmax = 10 * np.median(Bnorm)

        Bx[Bnorm > Bmax] = np.NAN 
        By[Bnorm > Bmax] = np.NAN
        Bz[Bnorm > Bmax] = np.NAN
        Bnorm[Bnorm > Bmax] = np.NAN

        self.Bx = Bx
        self.By = By
        self.Bz = Bz
        self.Bnorm = Bnorm


##############################################################################
# The application

class Application(HasTraits):

    scene = Instance(MlabSceneModel, (), editor=SceneEditor())

    # The mayavi engine view.
    engine_view = Instance(EngineView)

    # We use a traits List to be able to add coils to it
    coils = List(Loop,
                    value=( Loop(position=(0, 0, -0.05), ),
                            Loop(position=(0, 0,  0.05), ), ),
                    editor=ListEditor(use_notebook=True, deletable=False,
                                        style='custom'),
                 )

    # The grid of points on which we want to evaluate the field
    X, Y, Z = np.mgrid[-0.15:0.15:20j, -0.15:0.15:20j, -0.15:0.15:20j]

    # Avoid rounding issues:
    f = 1e4  # this gives the precision we are interested by :
    X = np.round(X * f) / f
    Y = np.round(Y * f) / f
    Z = np.round(Z * f) / f

    Bx    = Array(value=np.zeros_like(X))
    By    = Array(value=np.zeros_like(X))
    Bz    = Array(value=np.zeros_like(X))
    Bnorm = Array(value=np.zeros_like(X))

    field = None

    def __init__(self, **traits):
        HasTraits.__init__(self, **traits)
        self.engine_view = EngineView(engine=self.scene.engine)

    @on_trait_change('scene.activated')
    def init_view(self):
        # This gets fired when the viewer of the scene is created
        self.scene.scene_editor.background = (0, 0, 0)
        for coil in self.coils:
            coil.app = self
            coil.display()
            coil.mk_B_field()

        self.visualize_field()

    def visualize_field(self):
        self.Bx    = np.zeros_like(self.X)
        self.By    = np.zeros_like(self.X)
        self.Bz    = np.zeros_like(self.X)
        self.Bnorm = np.zeros_like(self.X)
        for coil in self.coils:
            if hasattr(coil, 'Bx'):
                self.Bx += coil.Bx
                self.By += coil.By
                self.Bz += coil.Bz
                self.Bnorm += coil.Bnorm

        if self.field is None:
            self.field = self.scene.mlab.pipeline.vector_field(
                            self.X, self.Y, self.Z, self.Bx, self.By, self.Bz, 
                            scalars = self.Bnorm,
                            name='B field')
            vectors = self.scene.mlab.pipeline.vectors(self.field,
                                    mode='arrow', resolution=10,
                                    mask_points=6, colormap='YlOrRd',
                                    scale_factor=2*np.abs(self.X[0,0,0]
                                                          -self.X[1,1,1]) )
            vectors.module_manager.vector_lut_manager.reverse_lut = True
            vectors.glyph.mask_points.random_mode = False
            self.scene.mlab.axes()
            self.scp = self.scene.mlab.pipeline.scalar_cut_plane(self.field,
                                                      colormap='hot')
        else:
            self.field.mlab_source.set(x=self.X,  y=self.Y,  z=self.Z,
                                       u=self.Bx, v=self.By, w=self.Bz,
                                       scalars=self.Bnorm)

    view = View(HSplit(
                    VSplit(Item(name='engine_view',
                                   style='custom',
                                   resizable=True),
                            Item('coils', springy=True),
                        show_labels=False),
                        'scene',
                        show_labels=False),
                    resizable=True,
                    title='Coils...',
                    height=0.8,
                    width=0.8,
                )

##############################################################################
if __name__ == '__main__':
    app = Application()
    app.configure_traits()


########NEW FILE########
__FILENAME__ = compute_field
"""
A script that computes the magnetic field generated by a pair of Helmoltz
coils.
"""

import numpy as np
from scipy import special, linalg

##############################################################################
# Function to caculate the field of a loop

def base_vectors(n):
    """ Returns 3 orthognal base vectors, the first one colinear to n.
    """
    # normalize n
    n = n / np.sqrt(np.square(n).sum(axis=-1))

    # choose two vectors perpendicular to n
    # choice is arbitrary since the coil is symetric about n
    if abs(n[0]) == 1 :
        l = np.r_[n[2], 0, -n[0]]
    else:
        l = np.r_[0, n[2], -n[1]]

    l = l / np.sqrt(np.square(l).sum(axis=-1))
    m = np.cross(n, l)
    return n, l, m


def B_field(r, n, r0, R):
    """
    returns the magnetic field from an arbitrary current loop calculated from
    eqns (1) and (2) in Phys Rev A Vol. 35, N 4, pp. 1535-1546; 1987.

    Parameters
    ----------
        n is normal vector to the plane of the loop at the center, current
            is oriented by the right-hand-rule.
        r is a position vector where the Bfield is evaluated:
            [x1 y2 z3 ; x2 y2 z2 ; ... ]
        r is in units of d
        r0 is the location of the center of the loop in units of d: [x y z]
        R is the radius of the loop

    Returns
    -------
        B is a vector for the B field at point r in inverse units of
    (mu I) / (2 pi d)
    for I in amps and d in meters and mu = 4 pi * 10^-7 we get Tesla
    """
    ### Translate the coordinates in the coil's frame
    n, l, m = base_vectors(n)

    # transformation matrix coil frame to lab frame
    trans = np.vstack((l, m, n))
    # transformation matrix to lab frame to coil frame
    inv_trans = linalg.inv(trans)

    r = r - r0	  #point location from center of coil
    r = np.dot(r, inv_trans) 	    #transform vector to coil frame

    #### calculate field

    # express the coordinates in polar form
    x = r[:, 0]
    y = r[:, 1]
    z = r[:, 2]
    rho = np.sqrt(x**2 + y**2)
    theta = np.arctan(x / y)
    # NaNs are generated where y is zero.
    theta[y == 0] = np.pi / 2

    E = special.ellipe((4 * R * rho)/( (R + rho)**2 + z**2))
    K = special.ellipk((4 * R * rho)/( (R + rho)**2 + z**2))
    dist = ((R - rho)**2 + z**2)
    Bz = 1 / np.sqrt((R + rho)**2 + z**2) * (
                K
              + E * (R**2 - rho**2 - z**2) / dist
              )
    Brho = z / (rho*np.sqrt((R + rho)**2 + z**2)) * (
               -K
              + E * (R**2 + rho**2 + z**2)/ dist
              )
    # On the axis of the coil we get a divided by zero here. This returns a
    # NaN, where the field is actually zero :
    Brho[dist == 0] = 0
    Brho[rho == 0] = 0
    Bz[dist == 0] = 0

    B = np.c_[np.cos(theta)*Brho, np.sin(theta)*Brho, Bz ]

    # Rotate the field back in the lab's frame
    B = np.dot(B, trans)
    return B


##############################################################################
# The grid of points on which we want to evaluate the field
X, Y, Z = np.mgrid[-0.15:0.15:31j, -0.15:0.15:31j, -0.15:0.15:31j]
# Avoid rounding issues :
f = 1e4  # this gives the precision we are interested in:
X = np.round(X * f) / f
Y = np.round(Y * f) / f
Z = np.round(Z * f) / f

# The (x, y, z) position vector
r = np.c_[np.ravel(X), np.ravel(Y), np.ravel(Z)]


##############################################################################
# The coil positions

# The center of the coil
r0  = np.r_[0, 0, 0.1]
# The normal to the coils
n  = np.r_[0, 0, 1]
# The radius
R  = 0.1

# Add the mirror image of this coils relatively to the xy plane :
r0 = np.vstack((r0, -r0 ))
R = np.r_[R, R]
n = np.vstack((n, n))	    # Helmoltz like configuration

##############################################################################
# Calculate field
# First initialize a container matrix for the field vector :
B = np.zeros_like(r)
# Then loop through the different coils and sum the fields :
for this_n, this_r0, this_R in zip(n, r0, R):
  this_n    = np.array(this_n)
  this_r0   = np.array(this_r0)
  this_R    = np.array(this_R)
  B += B_field(r, this_n, this_r0, this_R)


########NEW FILE########
__FILENAME__ = generate_figures
"""
Example generating the figures for the tutorial.
"""
import numpy as np
from mayavi import mlab

# Seed the random number generator, for reproducibility
np.random.seed(0)

mlab.figure(1, bgcolor=(1, 1, 1), fgcolor=(0, 0, 0), size=(400, 300))
mlab.clf()

### begin points3d example
x, y, z, value = np.random.random((4, 40))
mlab.points3d(x, y, z, value)
### end points3d example

mlab.view(distance='auto')
mlab.text(.02, .9, 'points3d', width=.35)
mlab.savefig('points3d.png')


### begin plot3d example
mlab.clf()  # Clear the figure
t = np.linspace(0, 20, 200)
mlab.plot3d(np.sin(t), np.cos(t), 0.1*t, t)
### end plot3d example

mlab.view(distance='auto')
mlab.text(.02, .9, 'plot3d', width=.25)
mlab.savefig('plot3d.png')


### begin surf example
mlab.clf()
x, y = np.mgrid[-10:10:100j, -10:10:100j]
r = np.sqrt(x**2 + y**2)
z = np.sin(r)/r
mlab.surf(z, warp_scale='auto')
### end surf example

mlab.view(distance='auto')
mlab.text(.02, .9, 'surf', width=.15)
mlab.savefig('surf.png')

### begin mesh example
mlab.clf()
phi, theta = np.mgrid[0:np.pi:11j, 0:2*np.pi:11j]
x = np.sin(phi) * np.cos(theta)
y = np.sin(phi) * np.sin(theta)
z = np.cos(phi)
mlab.mesh(x, y, z)
mlab.mesh(x, y, z, representation='wireframe', color=(0, 0, 0))
### end mesh example

mlab.view(distance='auto')
mlab.text(.02, .9, 'mesh', width=.2)
mlab.savefig('mesh.png')

### begin contour3d example
mlab.clf()
x, y, z = np.mgrid[-5:5:64j, -5:5:64j, -5:5:64j]
values = x*x*0.5 + y*y + z*z*2.0
mlab.contour3d(values)
### end contour3d example

mlab.view(distance='auto')
mlab.text(.02, .9, 'contour3d', width=.45)
mlab.savefig('contour3d.png')


########NEW FILE########
__FILENAME__ = mlab_dialog
"""
Simple example demoing a dialog with Mayavi
"""

import numpy as np
from traits.api import HasTraits, Instance
from traitsui.api import View, Item, HGroup
from mayavi.core.ui.api import SceneEditor, MlabSceneModel

def curve(n_turns):
    "The function creating the x, y, z coordinates needed to plot"
    phi = np.linspace(0, 2*np.pi, 2000)
    return [np.cos(phi) * (1 + 0.5*np.cos(n_turns*phi)),
            np.sin(phi) * (1 + 0.5*np.cos(n_turns*phi)),
            0.5*np.sin(n_turns*phi)]


class Visualization(HasTraits):
    "The class that contains the dialog"
    scene   = Instance(MlabSceneModel, ())

    def __init__(self):
        HasTraits.__init__(self)
        x, y, z = curve(n_turns=2)
        # Populating our plot
        self.plot = self.scene.mlab.plot3d(x, y, z)

    # Describe the dialog
    view = View(Item('scene', height=300, show_label=False,
                    editor=SceneEditor()),
                HGroup('n_turns'), resizable=True)

# Fire up the dialog
Visualization().configure_traits()

########NEW FILE########
__FILENAME__ = mlab_interactive_dialog
"""
Example demoing an interactive dialog with Mayavi
"""

import numpy as np
from traits.api import HasTraits, Instance
from traitsui.api import View, Item, HGroup
from mayavi.core.ui.api import SceneEditor, MlabSceneModel

def curve(n_turns):
    phi = np.linspace(0, 2*np.pi, 2000)
    return [np.cos(phi) * (1 + 0.5*np.cos(n_turns*phi)),
            np.sin(phi) * (1 + 0.5*np.cos(n_turns*phi)),
            0.5*np.sin(n_turns*phi)]


# The class that contains the dialog
from traits.api import Range, on_trait_change

class Visualization(HasTraits):
    n_turns = Range(0, 30, 11)
    scene   = Instance(MlabSceneModel, ())

    def __init__(self):
        HasTraits.__init__(self)
        x, y, z = curve(self.n_turns)
        self.plot = self.scene.mlab.plot3d(x, y, z)

    @on_trait_change('n_turns')
    def update_plot(self):
        x, y, z = curve(self.n_turns)
        self.plot.mlab_source.set(x=x, y=y, z=z)

    view = View(Item('scene', height=300, show_label=False,
                    editor=SceneEditor()),
                HGroup('n_turns'), resizable=True)

# Fire up the dialog
Visualization().configure_traits()

########NEW FILE########
__FILENAME__ = simple_example
import numpy as np

x, y = np.mgrid[-10:10:100j, -10:10:100j]
r = np.sqrt(x**2 + y**2)
z = np.sin(r)/r

from enthought.mayavi import mlab
mlab.surf(z, warp_scale='auto')

mlab.outline()
mlab.axes()

########NEW FILE########
__FILENAME__ = visualize_field
"""
Visualize the field created by a pair of Helmoltz coils
"""

import numpy as np
from scipy import stats

from mayavi import mlab

# "import" our data from our previous script (the import actually runs
# the script and computes B)
from compute_field import B, X, Y, Z

###############################################################################
# Data massaging

# Reshape the data to put it in a form that can be fed in Mayavi
Bx = B[:, 0]
By = B[:, 1]
Bz = B[:, 2]
Bx = np.reshape(Bx, X.shape)
By = np.reshape(By, X.shape)
Bz = np.reshape(Bz, X.shape)

Bnorm = np.sqrt(Bx**2 + By**2 + Bz**2)

# Threshold, to avoid the very high values
Bmax = stats.scoreatpercentile(Bnorm.ravel(), 99)

Bx[Bnorm > Bmax] = Bmax * (Bx / Bnorm)[Bnorm > Bmax]
By[Bnorm > Bmax] = Bmax * (By / Bnorm)[Bnorm > Bmax]
Bz[Bnorm > Bmax] = Bmax * (Bz / Bnorm)[Bnorm > Bmax]
Bnorm[Bnorm > Bmax] = Bmax

###############################################################################
# Visualization proper

# Create a mayavi figure black on white
mlab.figure(bgcolor=(0., 0., 0.), fgcolor=(1., 1., 1.), size=(640, 480))

# Create a vector_field: a data source that we can slice and dice
field = mlab.pipeline.vector_field(X, Y, Z, Bx, By, Bz,
                                   scalars=Bnorm,
                                   name='B field')
# Plot the vectors
vectors = mlab.pipeline.vectors(field,
                                scale_factor=abs(X[0, 0, 0] - X[1, 1, 1]),
                                colormap='hot')
mlab.axes()

# Mask 7 data points out of 8
vectors.glyph.mask_input_points = True
vectors.glyph.mask_points.on_ratio = 8

mlab.pipeline.vector_cut_plane(field, scale_factor=.1, colormap='hot')

# Add an iso_surface of the norm of the field
mlab.pipeline.iso_surface(mlab.pipeline.extract_vector_norm(field),
                          contours=[0.1*Bmax, 0.4*Bmax],
                          opacity=0.5, transparent=True)

mlab.view(28, 84, 0.71)
mlab.savefig('visualize_field.png')

########NEW FILE########
__FILENAME__ = viz_volume_structure
"""
Use Mayavi to visualize the structure of a VolumeImg
"""

from mayavi import mlab
import numpy as np

x, y, z = np.mgrid[-5:5:64j, -5:5:64j, -5:5:64j]

data = x*x*0.5 + y*y + z*z*2.0

mlab.figure(1, fgcolor=(0, 0, 0), bgcolor=(1, 1, 1))
mlab.clf()

src = mlab.pipeline.scalar_field(x, y, z, data)

mlab.pipeline.surface(src, opacity=0.4)

src2 = mlab.pipeline.scalar_field(x[::9, ::9, ::9],
                                  y[::9, ::9, ::9],
                                  z[::9, ::9, ::9],
                                  data[::9, ::9, ::9])
mlab.pipeline.surface(mlab.pipeline.extract_edges(src2), color=(0, 0, 0))
mlab.pipeline.glyph(src2, mode='cube', scale_factor=0.4, scale_mode='none')
mlab.savefig('viz_volume_structure.png')
mlab.show()



########NEW FILE########
__FILENAME__ = plot_boundaries
"""
Visiualize segmentation contours on original grayscale image.
"""

from skimage import data, segmentation, filter, color
import matplotlib.pyplot as plt

coins = data.coins()
mask = coins > filter.threshold_otsu(coins)
clean_border = segmentation.clear_border(mask)

coins_edges = segmentation.visualize_boundaries(color.gray2rgb(coins),
                            clean_border)

plt.figure(figsize=(8, 3.5))
plt.subplot(121)
plt.imshow(clean_border, cmap='gray')
plt.axis('off')
plt.subplot(122)
plt.imshow(coins_edges)
plt.axis('off')

plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_camera
"""
Load and display an image
"""

import matplotlib.pyplot as plt
from skimage import data

camera = data.camera()


plt.figure(figsize=(4, 4))
plt.imshow(camera, cmap='gray', interpolation='nearest')
plt.axis('off')

plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_camera_uint
"""
An illustration of overflow problem arising when working with integers
"""

import matplotlib.pyplot as plt
from skimage import data

camera = data.camera()
camera_multiply = 3 * camera

plt.figure(figsize=(8, 4))
plt.subplot(121)
plt.imshow(camera, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.subplot(122)
plt.imshow(camera_multiply, cmap='gray', interpolation='nearest')
plt.axis('off')

plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_check
"""
How to create an image with basic NumPy commands : ``np.zeros``, slicing...

This examples show how to create a simple checkerboard.
"""

import numpy as np
import matplotlib.pyplot as plt

check = np.zeros((9, 9))
check[::2, 1::2] = 1
check[1::2, ::2] = 1
plt.matshow(check, cmap='gray')
plt.show()

########NEW FILE########
__FILENAME__ = plot_equalize_hist
"""

"""

from skimage import data, exposure
import matplotlib.pyplot as plt

camera = data.camera()
camera_equalized = exposure.equalize(camera) 



plt.figure(figsize=(7, 3))

plt.subplot(121)
plt.imshow(camera, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.subplot(122)
plt.imshow(camera_equalized, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_features
from matplotlib import pyplot as plt

from skimage import data
from skimage.feature import corner_harris, corner_subpix, corner_peaks
from skimage.transform import warp, AffineTransform


tform = AffineTransform(scale=(1.3, 1.1), rotation=1, shear=0.7,
                        translation=(210, 50))
image = warp(data.checkerboard(), tform.inverse, output_shape=(350, 350))

coords = corner_peaks(corner_harris(image), min_distance=5)
coords_subpix = corner_subpix(image, coords, window_size=13)

plt.gray()
plt.imshow(image, interpolation='nearest')
plt.plot(coords_subpix[:, 1], coords_subpix[:, 0], '+r', markersize=15, mew=5)
plt.plot(coords[:, 1], coords[:, 0], '.b', markersize=7)
plt.axis('off')
plt.show()

########NEW FILE########
__FILENAME__ = plot_filter_coins
"""
This example compares several denoising filters available in scikit-image:
a Gaussian filter, a median filter, and total variation denoising.
"""

import matplotlib.pyplot as plt
from skimage import data
from skimage import filter
from scipy import ndimage

coins = data.coins()
gaussian_filter_coins = ndimage.gaussian_filter(coins, sigma=2)
med_filter_coins = filter.median_filter(coins)
tv_filter_coins = filter.denoise_tv_chambolle(coins, weight=0.1)

plt.figure(figsize=(16, 4))
plt.subplot(141)
plt.imshow(coins[10:80, 300:370], cmap='gray', interpolation='nearest')
plt.axis('off')
plt.title('Image')
plt.subplot(142)
plt.imshow(gaussian_filter_coins[10:80, 300:370], cmap='gray',
           interpolation='nearest')
plt.axis('off')
plt.title('Gaussian filter')
plt.subplot(143)
plt.imshow(med_filter_coins[10:80, 300:370], cmap='gray',
           interpolation='nearest')
plt.axis('off')
plt.title('Median filter')
plt.subplot(144)
plt.imshow(tv_filter_coins[10:80, 300:370], cmap='gray',
           interpolation='nearest')
plt.axis('off')
plt.title('TV filter')
plt.show()

########NEW FILE########
__FILENAME__ = plot_labels
"""
This example shows how to label connected components of a binary image, using
the dedicated skimage.morphology.label function.
"""

from skimage import morphology
import matplotlib.pyplot as plt
from scipy import ndimage
import numpy as np

n = 12
l = 256
np.random.seed(1)
im = np.zeros((l, l))
points = l*np.random.random((2, n**2))
im[(points[0]).astype(np.int), (points[1]).astype(np.int)] = 1
im = ndimage.gaussian_filter(im, sigma=l/(4.*n))
blobs = im > 0.7 * im.mean()

all_labels = morphology.label(blobs)
blobs_labels = morphology.label(blobs, background=0)

plt.figure(figsize=(9, 3.5))
plt.subplot(131)
plt.imshow(blobs, cmap='gray')
plt.axis('off')
plt.subplot(132)
plt.imshow(all_labels)
plt.axis('off')
plt.subplot(133)
plt.imshow(blobs_labels)
plt.axis('off')

plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_segmentations
"""
This example compares two segmentation methods in order to separate two
connected disks: the watershed algorithm, and the random walker algorithm.

Both segmentation methods require seeds, that are pixels belonging
unambigusouly to a reagion. Here, local maxima of the distance map to the
background are used as seeds.
"""

import numpy as np
from skimage.morphology import watershed
from skimage.feature import peak_local_max
from skimage import morphology
from skimage.segmentation import random_walker
import matplotlib.pyplot as plt
from scipy import ndimage

# Generate an initial image with two overlapping circles
x, y = np.indices((80, 80))
x1, y1, x2, y2 = 28, 28, 44, 52
r1, r2 = 16, 20
mask_circle1 = (x - x1) ** 2 + (y - y1) ** 2 < r1 ** 2
mask_circle2 = (x - x2) ** 2 + (y - y2) ** 2 < r2 ** 2
image = np.logical_or(mask_circle1, mask_circle2)
# Now we want to separate the two objects in image
# Generate the markers as local maxima of the distance
# to the background
distance = ndimage.distance_transform_edt(image)
local_maxi = peak_local_max(
    distance, indices=False, footprint=np.ones((3, 3)), labels=image)
markers = morphology.label(local_maxi)
labels_ws = watershed(-distance, markers, mask=image)

markers[~image] = -1
labels_rw = random_walker(image, markers)

plt.figure(figsize=(12, 3.5))
plt.subplot(141)
plt.imshow(image, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.title('image')
plt.subplot(142)
plt.imshow(-distance, interpolation='nearest')
plt.axis('off')
plt.title('distance map')
plt.subplot(143)
plt.imshow(labels_ws, cmap='spectral', interpolation='nearest')
plt.axis('off')
plt.title('watershed segmentation')
plt.subplot(144)
plt.imshow(labels_rw, cmap='spectral', interpolation='nearest')
plt.axis('off')
plt.title('random walker segmentation')

plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_sobel
"""
This example illustrates the use of the horizontal Sobel filter, to compute
horizontal gradients.
"""

from skimage import data, filter
import matplotlib.pyplot as plt

text = data.text()
hsobel_text = filter.hsobel(text)

plt.figure(figsize=(12, 3))

plt.subplot(121)
plt.imshow(text, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.subplot(122)
plt.imshow(hsobel_text, cmap='jet', interpolation='nearest')
plt.axis('off')
plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = plot_threshold
"""
This example illustrates automatic Otsu thresholding.
"""

import matplotlib.pyplot as plt
from skimage import data
from skimage import filter
from skimage import exposure

camera = data.camera()
val = filter.threshold_otsu(camera)

hist, bins_center = exposure.histogram(camera)

plt.figure(figsize=(9, 4))
plt.subplot(131)
plt.imshow(camera, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.subplot(132)
plt.imshow(camera < val, cmap='gray', interpolation='nearest')
plt.axis('off')
plt.subplot(133)
plt.plot(bins_center, hist, lw=2)
plt.axvline(val, color='k', ls='--')

plt.tight_layout()
plt.show()

########NEW FILE########
__FILENAME__ = digits_svm
from sklearn import datasets, svm

digits = datasets.load_digits()
clf = svm.SVC(kernel='linear')
n_train = int(.9 * digits.target.shape[0])
clf.fit(digits.data[:n_train], digits.target[:n_train])
print clf.score(digits.data[n_train:], digits.target[n_train:])

########NEW FILE########
__FILENAME__ = faces
"""
Stripped-down version of the face recognition example by Olivier Grisel

http://scikit-learn.org/dev/auto_examples/applications/face_recognition.html

## original shape of images: 50, 37
"""

import numpy as np
from sklearn import cross_val, datasets, decomposition, svm

# ..
# .. load data ..
lfw_people = datasets.fetch_lfw_people(min_faces_per_person=70, resize=0.4)
faces = np.reshape(lfw_people.data, (lfw_people.target.shape[0], -1))
train, test = iter(cross_val.StratifiedKFold(lfw_people.target, k=4)).next()
X_train, X_test = faces[train], faces[test]
y_train, y_test = lfw_people.target[train], lfw_people.target[test]

# ..
# .. dimension reduction ..
pca = decomposition.RandomizedPCA(n_components=150, whiten=True)
pca.fit(X_train)
X_train_pca = pca.transform(X_train)
X_test_pca = pca.transform(X_test)

# ..
# .. classification ..
clf = svm.SVC(C=5., gamma=0.001)
clf.fit(X_train_pca, y_train)

print 'Score on unseen data: '
print clf.score(X_test_pca, y_test)



########NEW FILE########
__FILENAME__ = show_digit
from sklearn import datasets
import pylab as pl

digits = datasets.load_digits()

for i in range(8):
    pl.subplot(2, 4, 1 + i)
    pl.imshow(digits.images[3 * i], cmap=pl.cm.gray_r, interpolation='nearest')
#    pl.axis('off')
pl.show()

pl.imshow(digits.images[8], cmap=pl.cm.gray_r, interpolation='nearest')
pl.show()

pl.imshow(digits.images[8].reshape(1, -1), cmap=pl.cm.gray_r, interpolation='nearest')
pl.axis('off')
pl.show()

########NEW FILE########
__FILENAME__ = show_ica
from sklearn import datasets, decomposition
import pylab as pl
import numpy as np

digits = datasets.load_digits()

digits.data += .2 * np.random.normal(size=digits.data.shape)
ica = decomposition.FastICA(n_components=10)
tt = ica.fit(digits.data.T).transform(digits.data.T).T

for i in range(8):
    pl.subplot(2, 4, 1 + i)
    pl.imshow(tt[i].reshape(8, 8), cmap=pl.cm.gray_r, interpolation='nearest')
#    pl.axis('off')
pl.show()

########NEW FILE########
__FILENAME__ = show_pca
from sklearn import datasets, decomposition
import pylab as pl

iris = datasets.load_iris()

pca = decomposition.PCA(n_components=2)
iris_2D = pca.fit(iris.data).transform(iris.data)

pl.scatter(iris_2D[:, 0], iris_2D[:, 1], c=iris.target)
pl.show()

########NEW FILE########
__FILENAME__ = reservoir
from traits.api import HasTraits, Str, Float, Range

class Reservoir(HasTraits):
    name = Str
    max_storage = Float(1e6, desc='Maximal storage [hm3]')
    max_release = Float(10, desc='Maximal release [m3/s]')
    head = Float(10, desc='Hydraulic head [m]')
    efficiency = Range(0, 1.)

    def energy_production(self, release):
        ''' Returns the energy production [Wh] for the given release [m3/s]
        '''
        power = 1000 * 9.81 * self.head * release * self.efficiency
        return power * 3600


if __name__ == '__main__':
    reservoir = Reservoir(
                        name = 'Project A',
                        max_storage = 30,
                        max_release = 100.0,
                        head = 60,
                        efficiency = 0.8
                    )

    release = 80
    print 'Releasing {} m3/s produces {} kWh'.format(
                        release, reservoir.energy_production(release)
                    )

########NEW FILE########
__FILENAME__ = reservoir_evolution
import numpy as np

from traits.api import HasTraits, Array, Instance, Float, Property
from traits.api import DelegatesTo
from traitsui.api import View, Item, Group
from chaco.chaco_plot_editor import ChacoPlotItem

from reservoir import Reservoir


class ReservoirEvolution(HasTraits):
    reservoir = Instance(Reservoir)

    name = DelegatesTo('reservoir')

    inflows = Array(dtype=np.float64, shape=(None))
    releass = Array(dtype=np.float64, shape=(None))

    initial_stock = Float
    stock = Property(depends_on='inflows, releases, initial_stock')

    month = Property(depends_on='stock')

    ### Traits view ##########################################################
    traits_view = View(
        Item('name'),
        Group(
            ChacoPlotItem('month', 'stock', show_label=False),
        ),
        width = 500,
        resizable = True
    )

    ### Traits properties ####################################################
    def _get_stock(self):
        """
        fixme: should handle cases where we go over the max storage
        """
        return  self.initial_stock + (self.inflows - self.releases).cumsum()

    def _get_month(self):
        return np.arange(self.stock.size)

if __name__ == '__main__':
    reservoir = Reservoir(
                            name = 'Project A',
                            max_storage = 30,
                            max_release = 100.0,
                            head = 60,
                            efficiency = 0.8
                        )

    initial_stock = 10.
    inflows_ts = np.array([6., 6, 4, 4, 1, 2, 0, 0, 3, 1, 5, 3])
    releases_ts = np.array([4., 5, 3, 5, 3, 5, 5, 3, 2, 1, 3, 3])

    view = ReservoirEvolution(
                                reservoir = reservoir,
                                inflows = inflows_ts,
                                releases = releases_ts
                            )
    view.configure_traits()

########NEW FILE########
__FILENAME__ = reservoir_simple_view
from traits.api import HasTraits, Str, Float, Range
from traitsui.api import View

class Reservoir(HasTraits):
    name = Str
    max_storage = Float(1e6, desc='Maximal storage [hm3]')
    max_release = Float(10, desc='Maximal release [m3/s]')
    head = Float(10, desc='Hydraulic head [m]')
    efficiency = Range(0, 1.)

    traits_view = View(
        'name', 'max_storage', 'max_release', 'head', 'efficiency',
        title = 'Reservoir',
        resizable = True,
    )

    def energy_production(self, release):
        ''' Returns the energy production [Wh] for the given release [m3/s]
        '''
        power = 1000 * 9.81 * self.head * release * self.efficiency 
        return power * 3600


if __name__ == '__main__':
    reservoir = Reservoir(
                        name = 'Project A',
                        max_storage = 30,
                        max_release = 100.0,
                        head = 60,
                        efficiency = 0.8
                    )

    reservoir.configure_traits()

########NEW FILE########
__FILENAME__ = reservoir_state
from traits.api import HasTraits, Instance, DelegatesTo, Float, Range

from reservoir import Reservoir

class ReservoirState(HasTraits):
    """Keeps track of the reservoir state given the initial storage.
    """
    reservoir = Instance(Reservoir, ())
    min_storage = Float
    max_storage = DelegatesTo('reservoir')
    min_release = Float
    max_release = DelegatesTo('reservoir')

    # state attributes
    storage = Range(low='min_storage', high='max_storage')

    # control attributes
    inflows =  Float(desc='Inflows [hm3]')
    release = Range(low='min_release', high='max_release')
    spillage = Float(desc='Spillage [hm3]')

    def print_state(self):
        print 'Storage\tRelease\tInflows\tSpillage'
        str_format = '\t'.join(['{:7.2f}'for i in range(4)])
        print str_format.format(self.storage, self.release, self.inflows,
                self.spillage)
        print '-' * 79


if __name__ == '__main__':
    projectA = Reservoir(
            name = 'Project A',
            max_storage = 30,
            max_release = 100.0,
            hydraulic_head = 60,
            efficiency = 0.8
        )

    state = ReservoirState(reservoir=projectA, storage=10)
    state.release = 90
    state.inflows = 0
    state.print_state()

    print 'How do we update the current storage ?'

########NEW FILE########
__FILENAME__ = reservoir_state_dynamic_listener
from reservoir import Reservoir
from reservoir_state_property import ReservoirState

def wake_up_watchman_if_spillage(new_value):
    if new_value > 0:
        print 'Wake up watchman! Spilling {} hm3'.format(new_value)

if __name__ == '__main__':
    projectA = Reservoir(
                        name = 'Project A',
                        max_storage = 30,
                        max_release = 100.0,
                        hydraulic_head = 60,
                        efficiency = 0.8
                    )

    state = ReservoirState(reservoir=projectA, storage=10)

    #register the dynamic listener
    state.on_trait_change(wake_up_watchman_if_spillage, name='spillage')

    state.release = 90
    state.inflows = 0
    state.print_state()

    print 'Forcing spillage'
    state.inflows = 100
    state.release = 0

    print 'Why do we have two executions of the callback ?'

########NEW FILE########
__FILENAME__ = reservoir_state_event
from traits.api import HasTraits, Instance, DelegatesTo, Float, Range, Event

from reservoir import Reservoir

class ReservoirState(HasTraits):
    """Keeps track of the reservoir state given the initial storage.

    For the simplicity of the example, the release is considered in
    hm3/timestep and not in m3/s.
    """
    reservoir = Instance(Reservoir, ())
    min_storage = Float
    max_storage = DelegatesTo('reservoir')
    min_release = Float
    max_release = DelegatesTo('reservoir')

    # state attributes
    storage = Range(low='min_storage', high='max_storage')

    # control attributes
    inflows =  Float(desc='Inflows [hm3]')
    release = Range(low='min_release', high='max_release')
    spillage = Float(desc='Spillage [hm3]')

    update_storage = Event(desc='Updates the storage to the next time step')

    def _update_storage_fired(self):
        # update storage state
        new_storage = self.storage - self.release  + self.inflows
        self.storage = min(new_storage, self.max_storage)
        overflow = new_storage - self.max_storage
        self.spillage = max(overflow, 0)

    def print_state(self):
        print 'Storage\tRelease\tInflows\tSpillage'
        str_format = '\t'.join(['{:7.2f}'for i in range(4)])
        print str_format.format(self.storage, self.release, self.inflows,
                self.spillage)
        print '-' * 79


if __name__ == '__main__':
    projectA = Reservoir(
        name = 'Project A',
        max_storage = 30,
        max_release = 5.0,
        hydraulic_head = 60,
        efficiency = 0.8
    )

    state = ReservoirState(reservoir=projectA, storage=15)
    state.release = 5
    state.inflows = 0

    # release the maximum amount of water during 3 time steps
    state.update_storage = True
    state.print_state()
    state.update_storage = True
    state.print_state()
    state.update_storage = True
    state.print_state()

########NEW FILE########
__FILENAME__ = reservoir_state_property
from traits.api import HasTraits, Instance, DelegatesTo, Float, Range
from traits.api import Property

from reservoir import Reservoir

class ReservoirState(HasTraits):
    """Keeps track of the reservoir state given the initial storage.

    For the simplicity of the example, the release is considered in
    hm3/timestep and not in m3/s.
    """
    reservoir = Instance(Reservoir, ())
    max_storage = DelegatesTo('reservoir')
    min_release = Float
    max_release = DelegatesTo('reservoir')

    # state attributes
    storage = Property(depends_on='inflows, release')

    # control attributes
    inflows =  Float(desc='Inflows [hm3]')
    release = Range(low='min_release', high='max_release')
    spillage = Property(
            desc='Spillage [hm3]', depends_on=['storage', 'inflows', 'release']
        )

    ### Private traits. ######################################################
    _storage = Float

    ### Traits property implementation. ######################################
    def _get_storage(self):
        new_storage = self._storage - self.release + self.inflows
        return min(new_storage, self.max_storage)

    def _set_storage(self, storage_value):
        self._storage = storage_value

    def _get_spillage(self):
        new_storage = self._storage - self.release  + self.inflows
        overflow = new_storage - self.max_storage
        return max(overflow, 0)

    def print_state(self):
        print 'Storage\tRelease\tInflows\tSpillage'
        str_format = '\t'.join(['{:7.2f}'for i in range(4)])
        print str_format.format(self.storage, self.release, self.inflows,
                self.spillage)
        print '-' * 79

if __name__ == '__main__':
    projectA = Reservoir(
                    name = 'Project A',
                    max_storage = 30,
                    max_release = 5,
                    hydraulic_head = 60,
                    efficiency = 0.8
                )

    state = ReservoirState(reservoir=projectA, storage=25)
    state.release = 4
    state.inflows = 0

    state.print_state()

########NEW FILE########
__FILENAME__ = reservoir_state_property_ontraitchange
from traits.api import HasTraits, Instance, DelegatesTo, Float, Range
from traits.api import Property, on_trait_change

from reservoir import Reservoir

class ReservoirState(HasTraits):
    """Keeps track of the reservoir state given the initial storage.

    For the simplicity of the example, the release is considered in
    hm3/timestep and not in m3/s.
    """
    reservoir = Instance(Reservoir, ())
    max_storage = DelegatesTo('reservoir')
    min_release = Float
    max_release = DelegatesTo('reservoir')

    # state attributes
    storage = Property(depends_on='inflows, release')

    # control attributes
    inflows =  Float(desc='Inflows [hm3]')
    release = Range(low='min_release', high='max_release')
    spillage = Property(
            desc='Spillage [hm3]', depends_on=['storage', 'inflows', 'release']
        )


    ### Private traits. ######################################################
    _storage = Float

    ### Traits property implementation. ######################################
    def _get_storage(self):
        new_storage = self._storage - self.release + self.inflows
        return min(new_storage, self.max_storage)

    def _set_storage(self, storage_value):
        self._storage = storage_value

    def _get_spillage(self):
        new_storage = self._storage - self.release  + self.inflows
        overflow = new_storage - self.max_storage
        return max(overflow, 0)

    @on_trait_change('storage')
    def print_state(self):
        print 'Storage\tRelease\tInflows\tSpillage'
        str_format = '\t'.join(['{:7.2f}'for i in range(4)])
        print str_format.format(self.storage, self.release, self.inflows,
                self.spillage)
        print '-' * 79

if __name__ == '__main__':
    projectA = Reservoir(
                        name = 'Project A',
                        max_storage = 30,
                        max_release = 5,
                        hydraulic_head = 60,
                        efficiency = 0.8
                    )

    state = ReservoirState(reservoir=projectA, storage=25)
    state.release = 4
    state.inflows = 0

########NEW FILE########
__FILENAME__ = reservoir_state_property_view
from traits.api import HasTraits, Instance, DelegatesTo, Float, Range, Property
from traitsui.api import View, Item, Group, VGroup

from reservoir import Reservoir

class ReservoirState(HasTraits):
    """Keeps track of the reservoir state given the initial storage.

    For the simplicity of the example, the release is considered in
    hm3/timestep and not in m3/s.
    """
    reservoir = Instance(Reservoir, ())
    name = DelegatesTo('reservoir')
    max_storage = DelegatesTo('reservoir')
    max_release = DelegatesTo('reservoir')
    min_release = Float

    # state attributes
    storage = Property(depends_on='inflows, release')

    # control attributes
    inflows =  Float(desc='Inflows [hm3]')
    release = Range(low='min_release', high='max_release')
    spillage = Property(
            desc='Spillage [hm3]', depends_on=['storage', 'inflows', 'release']
        )

    ### Traits view ##########################################################
    traits_view = View(
        Group(
            VGroup(Item('name'), Item('storage'), Item('spillage'),
                label = 'State', style = 'readonly'
            ),
            VGroup(Item('inflows'), Item('release'), label='Control'),
        )
    )

    ### Private traits. ######################################################
    _storage = Float

    ### Traits property implementation. ######################################
    def _get_storage(self):
        new_storage = self._storage - self.release + self.inflows
        return min(new_storage, self.max_storage)

    def _set_storage(self, storage_value):
        self._storage = storage_value

    def _get_spillage(self):
        new_storage = self._storage - self.release  + self.inflows
        overflow = new_storage - self.max_storage
        return max(overflow, 0)

    def print_state(self):
        print 'Storage\tRelease\tInflows\tSpillage'
        str_format = '\t'.join(['{:7.2f}'for i in range(4)])
        print str_format.format(self.storage, self.release, self.inflows,
                self.spillage)
        print '-' * 79

if __name__ == '__main__':
    projectA = Reservoir(
        name = 'Project A',
        max_storage = 30,
        max_release = 5,
        hydraulic_head = 60,
        efficiency = 0.8
    )

    state = ReservoirState(reservoir=projectA, storage=25)
    state.release = 4
    state.inflows = 0

    state.print_state()
    state.configure_traits()

########NEW FILE########
__FILENAME__ = reservoir_state_static_listener
from traits.api import HasTraits, Instance, DelegatesTo, Float, Range

from reservoir import Reservoir

class ReservoirState(HasTraits):
    """Keeps track of the reservoir state given the initial storage.
    """
    reservoir = Instance(Reservoir, ())
    min_storage = Float
    max_storage = DelegatesTo('reservoir')
    min_release = Float
    max_release = DelegatesTo('reservoir')

    # state attributes
    storage = Range(low='min_storage', high='max_storage')

    # control attributes
    inflows =  Float(desc='Inflows [hm3]')
    release = Range(low='min_release', high='max_release')
    spillage = Float(desc='Spillage [hm3]')

    def print_state(self):
        print 'Storage\tRelease\tInflows\tSpillage'
        str_format = '\t'.join(['{:7.2f}'for i in range(4)])
        print str_format.format(self.storage, self.release, self.inflows,
                self.spillage)
        print '-' * 79

    ### Traits listeners #####################################################
    def _release_changed(self, new):
        """When the release is higher than zero, warn all the inhabitants of
        the valley.
        """

        if new > 0:
            print 'Warning, we are releasing {} hm3 of water'.format(new)


if __name__ == '__main__':
    projectA = Reservoir(
            name = 'Project A',
            max_storage = 30,
            max_release = 100.0,
            hydraulic_head = 60,
            efficiency = 0.8
        )

    state = ReservoirState(reservoir=projectA, storage=10)
    state.release = 90
    state.inflows = 0
    state.print_state()

########NEW FILE########
__FILENAME__ = reservoir_turbine_prototype_from
from traits.api import HasTraits, Str, Float, Range, PrototypedFrom, Instance

class Turbine(HasTraits):
    turbine_type = Str
    power = Float(1.0, desc='Maximal power delivered by the turbine [Mw]')


class Reservoir(HasTraits):
    name = Str
    max_storage = Float(1e6, desc='Maximal storage [hm3]')
    max_release = Float(10, desc='Maximal release [m3/s]')
    head = Float(10, desc='Hydraulic head [m]')
    efficiency = Range(0, 1.)

    turbine = Instance(Turbine)
    installed_capacity = PrototypedFrom('turbine', 'power')


if __name__ == '__main__':
    turbine = Turbine(turbine_type='type1', power=5.0)

    reservoir = Reservoir(
            name = 'Project A',
            max_storage = 30,
            max_release = 100.0,
            head = 60,
            efficiency = 0.8,
            turbine = turbine,
        )

    print 'installed capacity is initialised with turbine.power'
    print reservoir.installed_capacity

    print '-' * 15
    print 'updating the turbine power updates the installed capacity'
    turbine.power = 10
    print reservoir.installed_capacity

    print '-' * 15
    print 'setting the installed capacity breaks the link between turbine.power'
    print 'and the installed_capacity trait'

    reservoir.installed_capacity = 8
    print turbine.power, reservoir.installed_capacity

########NEW FILE########
__FILENAME__ = reservoir_with_irrigation
from traits.api import HasTraits, Str, Float, Range, Enum, List
from traitsui.api import View, Item

class IrrigationArea(HasTraits):
    name = Str
    surface = Float(desc='Surface [ha]')
    crop = Enum('Alfalfa', 'Wheat', 'Cotton')


class Reservoir(HasTraits):
    name = Str
    max_storage = Float(1e6, desc='Maximal storage [hm3]')
    max_release = Float(10, desc='Maximal release [m3/s]')
    head = Float(10, desc='Hydraulic head [m]')
    efficiency = Range(0, 1.)
    irrigated_areas = List(IrrigationArea)

    def energy_production(self, release):
        ''' Returns the energy production [Wh] for the given release [m3/s]
        '''
        power = 1000 * 9.81 * self.head * release * self.efficiency
        return power * 3600

    traits_view = View(
        Item('name'),
        Item('max_storage'),
        Item('max_release'),
        Item('head'),
        Item('efficiency'),
        Item('irrigated_areas'),
        resizable = True
    )

if __name__ == '__main__':
    upper_block = IrrigationArea(name='Section C', surface=2000, crop='Wheat')

    reservoir = Reservoir(
                    name='Project A',
                    max_storage=30,
                    max_release=100.0,
                    head=60,
                    efficiency=0.8,
                    irrigated_areas=[upper_block]
                )

    release = 80
    print 'Releasing {} m3/s produces {} kWh'.format(
        release, reservoir.energy_production(release)
    )

########NEW FILE########
__FILENAME__ = reservoir_with_irrigation_listener
from traits.api import HasTraits, Str, Float, Range, Enum, List, Property
from traitsui.api import View, Item

class IrrigationArea(HasTraits):
    name = Str
    surface = Float(desc='Surface [ha]')
    crop = Enum('Alfalfa', 'Wheat', 'Cotton')


class Reservoir(HasTraits):
    name = Str
    max_storage = Float(1e6, desc='Maximal storage [hm3]')
    max_release = Float(10, desc='Maximal release [m3/s]')
    head = Float(10, desc='Hydraulic head [m]')
    efficiency = Range(0, 1.)

    irrigated_areas = List(IrrigationArea)


    total_crop_surface = Property(depends_on='irrigated_areas.surface')

    def _get_total_crop_surface(self):
        return sum([iarea.surface for iarea in self.irrigated_areas])

    def energy_production(self, release):
        ''' Returns the energy production [Wh] for the given release [m3/s]
        '''
        power = 1000 * 9.81 * self.head * release * self.efficiency 
        return power * 3600

    traits_view = View(
        Item('name'),
        Item('max_storage'),
        Item('max_release'),
        Item('head'),
        Item('efficiency'),
        Item('irrigated_areas'),
        Item('total_crop_surface'),
        resizable = True
    )

if __name__ == '__main__':
    upper_block = IrrigationArea(name='Section C', surface=2000, crop='Wheat')

    reservoir = Reservoir(
                        name='Project A',
                        max_storage=30,
                        max_release=100.0,
                        head=60,
                        efficiency=0.8,
                        irrigated_areas=[upper_block],
                    )

    release = 80
    print 'Releasing {} m3/s produces {} kWh'.format(
        release, reservoir.energy_production(release)
    )

########NEW FILE########
__FILENAME__ = demo_detrend
import numpy as np
import pylab as pl
from scipy import signal
t = np.linspace(0, 5, 100)
x = t + np.random.normal(size=100)

pl.plot(t, x, linewidth=3)
pl.plot(t, signal.detrend(x), linewidth=3)


########NEW FILE########
__FILENAME__ = demo_resample
import numpy as np
import pylab as pl
from scipy import signal
t = np.linspace(0, 5, 100)
x = np.sin(t)

pl.plot(t, x, linewidth=3)
pl.plot(t[::2], signal.resample(x, 50), 'ko')


########NEW FILE########
__FILENAME__ = fftpack_frequency
import numpy as np
from scipy import fftpack
import pylab as pl


np.random.seed(1234)

time_step = 0.02
period = 5.

time_vec = np.arange(0, 20, time_step)
sig = np.sin(2 * np.pi / period * time_vec) + \
      0.5 * np.random.randn(time_vec.size)

sample_freq = fftpack.fftfreq(sig.size, d=time_step)
sig_fft = fftpack.fft(sig)
pidxs = np.where(sample_freq > 0)
freqs, power = sample_freq[pidxs], np.abs(sig_fft)[pidxs]
freq = freqs[power.argmax()]

pl.figure()
pl.plot(freqs, power)
pl.xlabel('Frequency [Hz]')
pl.ylabel('plower')
axes = pl.axes([0.3, 0.3, 0.5, 0.5])
pl.title('Peak frequency')
pl.plot(freqs[:8], power[:8])
pl.setp(axes, yticks=[])



########NEW FILE########
__FILENAME__ = fftpack_signals
import numpy as np
from scipy import fftpack
import pylab as pl

np.random.seed(1234)

time_step = 0.02
period = 5.

time_vec = np.arange(0, 20, time_step)
sig = np.sin(2 * np.pi / period * time_vec) + \
      0.5 * np.random.randn(time_vec.size)

sample_freq = fftpack.fftfreq(sig.size, d=time_step)
sig_fft = fftpack.fft(sig)
pidxs = np.where(sample_freq > 0)
freqs, power = sample_freq[pidxs], np.abs(sig_fft)[pidxs]
freq = freqs[power.argmax()]

sig_fft[np.abs(sample_freq) > freq] = 0
main_sig = fftpack.ifft(sig_fft)

pl.figure()
pl.plot(time_vec, sig)
pl.plot(time_vec, main_sig, linewidth=3)
pl.xlabel('Time [s]')
pl.ylabel('Amplitude')


########NEW FILE########
__FILENAME__ = normal_distribution
from scipy import stats
import numpy as np
import pylab as pl
a = np.random.normal(size=10000)
bins = np.linspace(-5, 5, 30)
histogram, bins = np.histogram(a, bins=bins, normed=True)
bins = 0.5*(bins[1:] + bins[:-1])
from scipy import stats
b = stats.norm.pdf(bins)
pl.plot(bins, histogram)
pl.plot(bins, b)


########NEW FILE########
__FILENAME__ = numpy_intro_1
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 3, 20)
y = np.linspace(0, 9, 20)
plt.plot(x, y)       # line plot
plt.plot(x, y, 'o')  # dot plot
plt.show()           # <-- shows the plot (not needed with Ipython)

########NEW FILE########
__FILENAME__ = numpy_intro_10
import numpy as np

x = np.linspace(-1, 1, 2000)
y = np.cos(x) + 0.3*np.random.rand(2000)
p = np.polynomial.Chebyshev.fit(x, y, 90)

t = np.linspace(-1, 1, 200)
plt.plot(x, y, 'r.')
plt.plot(t, p(t), 'k-', lw=3)
plt.show()

########NEW FILE########
__FILENAME__ = numpy_intro_2
import numpy as np
import matplotlib.pyplot as plt

image = np.random.rand(30, 30)
plt.imshow(image, cmap=plt.cm.hot)
plt.colorbar()
plt.show()

########NEW FILE########
__FILENAME__ = numpy_intro_3
import numpy as np
import matplotlib.pyplot as plt

img = plt.imread('../data/elephant.png')
print img.shape, img.dtype
# (200, 300, 3)  dtype('float32')

plt.imshow(img)
plt.savefig('plot.png')
plt.show()

plt.imsave('red_elephant', img[:,:,0], cmap=plt.cm.gray)

# This saved only one channel (of RGB)

plt.imshow(plt.imread('red_elephant.png'))
plt.show()

# Other libraries:

from scipy.misc import imsave
imsave('tiny_elephant.png', img[::6,::6])
plt.imshow(plt.imread('tiny_elephant.png'), interpolation='nearest')
plt.show()

########NEW FILE########
__FILENAME__ = numpy_intro_4
import numpy as np
import matplotlib.pyplot as plt

# We can first plot the data:

data = np.loadtxt('../data/populations.txt')
year, hares, lynxes, carrots = data.T  # trick: columns to variables

plt.axes([0.2, 0.1, 0.5, 0.8])
plt.plot(year, hares, year, lynxes, year, carrots)
plt.legend(('Hare', 'Lynx', 'Carrot'), loc=(1.05, 0.5))
plt.show()

# The mean populations over time:
populations = data[:,1:]
print populations.mean(axis=0)
# [ 34080.95238095,  20166.66666667,  42400.        ]

# The sample standard deviations:
print populations.std(axis=0, ddof=1)
# [ 21413.98185877,  16655.99991995,   3404.55577132]

# Which species has the highest population each year?
print np.argmax(populations, axis=1)
# [2, 2, 0, 0, 1, 1, 2, 2, 2, 2, 2, 2, 0, 0, 0, 1, 2, 2, 2, 2, 2]

########NEW FILE########
__FILENAME__ = numpy_intro_5
import numpy as np
import matplotlib.pyplot as plt

n_stories = 1000 # number of walkers
t_max = 200      # time during which we follow the walker

# We randomly choose all the steps 1 or -1 of the walk

t = np.arange(t_max)
steps = 2 * np.random.random_integers(0, 1, (n_stories, t_max)) - 1
print np.unique(steps) # Verification: all steps are 1 or -1
# [-1,  1]

# We build the walks by summing steps along the time

positions = np.cumsum(steps, axis=1) # axis = 1: dimension of time
sq_distance = positions**2

# We get the mean in the axis of the stories

mean_sq_distance = np.mean(sq_distance, axis=0)

# Plot the results:

plt.figure(figsize=(4, 3))
plt.plot(t, np.sqrt(mean_sq_distance), 'g.', t, np.sqrt(t), 'y-')
plt.xlabel(r"$t$")
plt.ylabel(r"$\sqrt{\langle (\delta x)^2 \rangle}$")
plt.show()

########NEW FILE########
__FILENAME__ = numpy_intro_6
import numpy as np
import matplotlib.pyplot as plt

x, y = np.arange(5), np.arange(5)
distance = np.sqrt(x**2 + y[:, np.newaxis]**2)
print distance
# [[ 0.        ,  1.        ,  2.        ,  3.        ,  4.        ],
#  [ 1.        ,  1.41421356,  2.23606798,  3.16227766,  4.12310563],
#  [ 2.        ,  2.23606798,  2.82842712,  3.60555128,  4.47213595],
#  [ 3.        ,  3.16227766,  3.60555128,  4.24264069,  5.        ],
#  [ 4.        ,  4.12310563,  4.47213595,  5.        ,  5.65685425]]


# Or in color:

plt.pcolor(distance)
plt.colorbar()
plt.axis('equal')
plt.show()            # <-- again, not needed in interactive Python

########NEW FILE########
__FILENAME__ = numpy_intro_7
import numpy as np
import matplotlib.pyplot as plt

data = np.loadtxt('../data/populations.txt')
year, hares, lynxes, carrots = data.T  # trick: columns to variables

plt.axes([0.2, 0.1, 0.5, 0.8])
plt.plot(year, hares, year, lynxes, year, carrots)
plt.legend(('Hare', 'Lynx', 'Carrot'), loc=(1.05, 0.5))
plt.show()

########NEW FILE########
__FILENAME__ = numpy_intro_8
import numpy as np
import matplotlib.pyplot as plt

data = np.loadtxt('../data/populations.txt')
populations = np.ma.masked_array(data[:,1:])
year = data[:,0]

bad_years = (((year >= 1903) & (year <= 1910))
           | ((year >= 1917) & (year <= 1918)))
populations[bad_years,0] = np.ma.masked
populations[bad_years,1] = np.ma.masked

print populations.mean(axis=0)
# [40472.7272727 18627.2727273 42400.0]

print populations.std(axis=0)
# [21087.656489 15625.7998142 3322.50622558]

# Note that Matplotlib knows about masked arrays:

plt.plot(year, populations, 'o-')
plt.show()

########NEW FILE########
__FILENAME__ = numpy_intro_9
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 1, 20)
y = np.cos(x) + 0.3*np.random.rand(20)
p = np.poly1d(np.polyfit(x, y, 3))

t = np.linspace(0, 1, 200)
plt.plot(x, y, 'o', t, p(t), '-')
plt.show()

########NEW FILE########
__FILENAME__ = odeint_damped_spring_mass
"""Damped spring-mass oscillator
"""

import numpy as np
from scipy.integrate import odeint
import pylab as pl

mass = 0.5
kspring = 4
cviscous = 0.4

nu_coef = cviscous / mass
om_coef = kspring / mass

def calc_deri(yvec, time, nuc, omc):
    return (yvec[1], -nuc * yvec[1] - omc * yvec[0])

time_vec = np.linspace(0, 10, 100)
yarr = odeint(calc_deri, (1, 0), time_vec, args=(nu_coef, om_coef))

pl.plot(time_vec, yarr[:, 0], label='y')
pl.plot(time_vec, yarr[:, 1], label="y'")
pl.legend()


########NEW FILE########
__FILENAME__ = odeint_introduction
"""Solve the ODE dy/dt = -2y between t = 0..4, with the
initial condition y(t=0) = 1.
"""

import numpy as np
from scipy.integrate import odeint
import pylab as pl

def calc_derivative(ypos, time):
    return -2*ypos

time_vec = np.linspace(0, 4, 40)
yvec = odeint(calc_derivative, 1, time_vec)

pl.plot(time_vec, yvec)
pl.xlabel('Time [s]')
pl.ylabel('y position [m]')


########NEW FILE########
__FILENAME__ = scipy_interpolation
"""Generate the interpolation.png image for the interpolate
section of the Scipy tutorial
"""

import numpy as np
from scipy.interpolate import interp1d
import pylab as pl

measured_time = np.linspace(0, 1, 10)
noise = (np.random.random(10)*2 - 1) * 1e-1
measures = np.sin(2 * np.pi * measured_time) + noise

linear_interp = interp1d(measured_time, measures)
computed_time = np.linspace(0, 1, 50)
linear_results = linear_interp(computed_time)
cubic_interp = interp1d(measured_time, measures, kind='cubic')
cubic_results = cubic_interp(computed_time)

pl.plot(measured_time, measures, 'o', ms=6, label='measures')
pl.plot(computed_time, linear_results, label='linear interp')
pl.plot(computed_time, cubic_results, label='cubic interp')
pl.legend()

########NEW FILE########
__FILENAME__ = scipy_optimize_example1
import numpy as np
import matplotlib.pyplot as plt

def f(x):
    return x**2 + 10*np.sin(x)


x = np.arange(-10, 10, 0.1)
plt.plot(x, f(x))

########NEW FILE########
__FILENAME__ = scipy_optimize_example2
import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt

x = np.arange(-10, 10, 0.1)
def f(x):
    return x**2 + 10*np.sin(x)


grid = (-10, 10, 0.1)
xmin_global = optimize.brute(f, (grid,))
xmin_local = optimize.fminbound(f, 0, 10)
root = optimize.fsolve(f, 1)  # our initial guess is 1
root2 = optimize.fsolve(f, -2.5)

xdata = np.linspace(-10, 10, num=20)
np.random.seed(1234)
ydata = f(xdata) + np.random.randn(xdata.size)

def f2(x, a, b):
    return a*x**2 + b*np.sin(x)

guess = [2, 2]
params, params_covariance = optimize.curve_fit(f2, xdata, ydata, guess)


fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(x, f(x), 'b-', label="f(x)")
ax.plot(x, f2(x, *params), 'r--', label="Curve fit result")
xmins = np.array([xmin_global[0], xmin_local])
ax.plot(xmins, f(xmins), 'go', label="Minima")
roots = np.array([root, root2])
ax.plot(roots, f(roots), 'kv', label="Roots")
ax.legend()
ax.set_xlabel('x')
ax.set_ylabel('f(x)')

########NEW FILE########
__FILENAME__ = scipy_optimize_sixhump
import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def sixhump(x):
    return (4 - 2.1*x[0]**2 + x[0]**4 / 3.) * x[0]**2 + x[0] * x[1] + (-4 + \
        4*x[1]**2) * x[1] **2

x = np.linspace(-2, 2)
y = np.linspace(-1, 1)
xg, yg = np.meshgrid(x, y)

#plt.figure()  # simple visualization for use in tutorial
#plt.imshow(sixhump([xg, yg]))
#plt.colorbar()

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_surface(xg, yg, sixhump([xg, yg]), rstride=1, cstride=1,
                       cmap=plt.cm.jet, linewidth=0, antialiased=False)

ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_zlabel('f(x, y)')
ax.set_title('Six-hump Camelback function')

########NEW FILE########
__FILENAME__ = gen_rst
"""
Example generation for the scikit learn

Generate the rst files for the examples by iterating over the python
example files.

Files that generate images should start with 'plot'

"""
import os
import sys
import shutil
import traceback
import glob

import matplotlib
matplotlib.use('Agg')

import token, tokenize

rst_template = """

.. _example_%(short_fname)s:

%(docstring)s

**Python source code:** :download:`%(fname)s <%(fname)s>`

.. literalinclude:: %(fname)s
    :lines: %(end_row)s-
    """

plot_rst_template = """

.. _example_%(short_fname)s:

%(docstring)s

%(image_list)s

**Python source code:** :download:`%(fname)s <%(fname)s>`

.. literalinclude:: %(fname)s
    :lines: %(end_row)s-
    """

# The following strings are used when we have several pictures: we use
# an html div tag that our CSS uses to turn the lists into horizontal
# lists.
HLIST_HEADER = """
.. rst-class:: horizontal

"""

HLIST_IMAGE_TEMPLATE = """
    *

      .. image:: images/%s
            :scale: 50
"""

SINGLE_IMAGE = """
.. image:: images/%s
    :align: center
"""

def extract_docstring(filename):
    """ Extract a module-level docstring, if any
    """
    lines = file(filename).readlines()
    start_row = 0
    if lines[0].startswith('#!'):
        lines.pop(0)
        start_row = 1

    docstring = ''
    first_par = ''
    tokens = tokenize.generate_tokens(lines.__iter__().next)
    for tok_type, tok_content, _, (erow, _), _ in tokens:
        tok_type = token.tok_name[tok_type]
        if tok_type in ('NEWLINE', 'COMMENT', 'NL', 'INDENT', 'DEDENT'):
            continue
        elif tok_type == 'STRING':
            docstring = eval(tok_content)
            # If the docstring is formatted with several paragraphs, extract
            # the first one:
            paragraphs = '\n'.join(line.rstrip()
                                for line in docstring.split('\n')).split('\n\n')
            if len(paragraphs) > 0:
                first_par = paragraphs[0]
        break
    return docstring, first_par, erow+1+start_row


def generate_all_example_rst(app):
    """ Generate the list of examples, as well as the contents of
        examples.
    """
    input_dir = os.path.abspath(app.builder.srcdir)
    try:
        plot_gallery = eval(app.builder.config.plot_gallery)
    except TypeError:
        plot_gallery = bool(app.builder.config.plot_gallery)
    # Walk all our source tree to find examples and generate them
    for dir_path, dir_names, file_names in os.walk(input_dir):
        if ('build' in dir_path.split(os.sep)
                    or 'auto_examples' in dir_path.split(os.sep)):
            continue
        if 'examples' in dir_names:
            generate_example_rst(
                            os.path.join(dir_path, 'examples'),
                            os.path.join(dir_path, 'auto_examples'),
                            plot_gallery=plot_gallery)


def generate_example_rst(example_dir, out_dir, plot_gallery=False):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    # we create an index.rst with all examples
    fhindex = file(os.path.join(out_dir, 'index.rst'), 'w')
    fhindex.write("""\

.. raw:: html

    <style type="text/css">
    .figure {
        float: left;
        margin: 10px;
        width: auto;
        height: 200px;
        width: 180px;
    }

    .figure img {
        display: inline;
        }

    .figure .caption {
        width: 170px;
        text-align: center !important;
    }
    </style>

Examples
========

.. _examples-index:
""")
    generate_dir_rst('.', fhindex, example_dir, out_dir, plot_gallery)
    fhindex.flush()


def generate_dir_rst(dir, fhindex, example_dir, out_dir, plot_gallery):
    """ Generate the rst file for an example directory.
    """
    if not dir == '.':
        target_dir = os.path.join(out_dir, dir)
        src_dir = os.path.join(example_dir, dir)
    else:
        target_dir = out_dir
        src_dir = example_dir

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for fname in sorted(os.listdir(src_dir)):
        if fname.endswith('.py'):
            generate_file_rst(fname, target_dir, src_dir, plot_gallery)
            thumb = os.path.join(dir, 'images', 'thumb', fname[:-3] + '.png')
            link_name = os.path.join(dir, fname).replace(os.path.sep, '_')
            fhindex.write('.. figure:: %s\n' % thumb)
            if link_name.startswith('._'):
                link_name = link_name[2:]
            if dir != '.':
                fhindex.write('   :target: ./%s/%s.html\n\n' % (dir, fname[:-3]))
            else:
                fhindex.write('   :target: ./%s.html\n\n' % link_name[:-3])
            fhindex.write('   :ref:`example_%s`\n\n' % link_name)
    fhindex.write("""
.. raw:: html

    <div style="clear: both"></div>
    """) # clear at the end of the section


def generate_file_rst(fname, target_dir, src_dir, plot_gallery):
    """ Generate the rst file for a given example.
    """
    base_image_name = os.path.splitext(fname)[0]
    image_fname = '%s_%%s.png' % base_image_name

    this_template = rst_template
    last_dir = os.path.split(src_dir)[-1]
    # to avoid leading . in file names, and wrong names in links
    if last_dir == '.' or last_dir == 'examples':
        last_dir = ''
    else:
        last_dir += '_'
    short_fname = last_dir + fname
    src_file = os.path.join(src_dir, fname)
    example_file = os.path.join(target_dir, fname)
    shutil.copyfile(src_file, example_file)

    # The following is a list containing all the figure names
    figure_list = []

    image_dir = os.path.join(target_dir, 'images')
    thumb_dir = os.path.join(image_dir, 'thumb')
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir)
    image_path = os.path.join(image_dir, image_fname)
    thumb_file = os.path.join(thumb_dir, fname[:-3] + '.png')
    if plot_gallery and fname.startswith('plot'):
        # generate the plot as png image if file name
        # starts with plot and if it is more recent than an
        # existing image.
        first_image_file = image_path % 1

        if (not os.path.exists(first_image_file) or
                os.stat(first_image_file).st_mtime <=
                                    os.stat(src_file).st_mtime):
            # We need to execute the code
            print 'plotting %s' % fname
            import matplotlib.pyplot as plt
            plt.close('all')
            cwd = os.getcwd()
            try:
                # First CD in the original example dir, so that any file created
                # by the example get created in this directory
                src_file_dir = os.path.dirname(src_file)
                os.chdir(src_file_dir)
                # Add source directory to sys.path for local import
                sys.path.append(src_file_dir)
                execfile(os.path.basename(src_file), {'pl' : plt})
                sys.path.pop()
                os.chdir(cwd)

                # In order to save every figure we have two solutions :
                # * iterate from 1 to infinity and call plt.fignum_exists(n)
                #   (this requires the figures to be numbered
                #    incrementally: 1, 2, 3 and not 1, 2, 5)
                # * iterate over [fig_mngr.num for fig_mngr in
                #   matplotlib._pylab_helpers.Gcf.get_all_fig_managers()]
                for fig_num in (fig_mngr.num for fig_mngr in
                          matplotlib._pylab_helpers.Gcf.get_all_fig_managers()):
                    # Set the fig_num figure as the current figure as we can't
                    # save a figure that's not the current figure.
                    plt.figure(fig_num)
                    plt.savefig(image_path % fig_num)
                    figure_list.append(image_fname % fig_num)
            except:
                print 80*'_'
                print '%s is not compiling:' % fname
                traceback.print_exc()
                print 80*'_'
            finally:
                os.chdir(cwd)
        else:
            figure_list = [f[len(image_dir):]
                            for f in glob.glob(image_path % '[1-9]')]
                            #for f in glob.glob(image_path % '*')]

        # generate thumb file
        this_template = plot_rst_template
        from matplotlib import image
        if os.path.exists(first_image_file):
            image.thumbnail(first_image_file, thumb_file, 0.2)

    if not os.path.exists(thumb_file):
        # create something not to replace the thumbnail
        shutil.copy('blank_image.png', thumb_file)

    docstring, short_desc, end_row = extract_docstring(example_file)

    # Depending on whether we have one or more figures, we're using a
    # horizontal list or a single rst call to 'image'.
    if len(figure_list) == 1:
        figure_name = figure_list[0]
        image_list = SINGLE_IMAGE % figure_name.lstrip('/')
    else:
        image_list = HLIST_HEADER
        for figure_name in figure_list:
            image_list += HLIST_IMAGE_TEMPLATE % figure_name.lstrip('/')

    f = open(os.path.join(target_dir, fname[:-2] + 'rst'),'w')
    f.write(this_template % locals())
    f.flush()


def setup(app):
    app.connect('builder-inited', generate_all_example_rst)
    app.add_config_value('plot_gallery', True, 'html')

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
__FILENAME__ = mathml
from docutils import nodes
from docutils.writers.html4css1 import HTMLTranslator
from sphinx.latexwriter import LaTeXTranslator

# Define LaTeX math node:
class latex_math(nodes.General, nodes.Element):
    pass

def math_role(role, rawtext, text, lineno, inliner,
              options={}, content=[]):
    i = rawtext.find('`')
    latex = rawtext[i+1:-1]
    try:
        mathml_tree = parse_latex_math(latex, inline=True)
    except SyntaxError, msg:
        msg = inliner.reporter.error(msg, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    node = latex_math(rawtext)
    node['latex'] = latex
    node['mathml_tree'] = mathml_tree
    return [node], []


try:
    from docutils.parsers.rst import Directive
except ImportError:
    # Register directive the old way:
    from docutils.parsers.rst.directives import _directives
    def math_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
        latex = ''.join(content)
        try:
            mathml_tree = parse_latex_math(latex, inline=False)
        except SyntaxError, msg:
            error = state_machine.reporter.error(
                msg, nodes.literal_block(block_text, block_text), line=lineno)
            return [error]
        node = latex_math(block_text)
        node['latex'] = latex
        node['mathml_tree'] = mathml_tree
        return [node]
    math_directive.arguments = None
    math_directive.options = {}
    math_directive.content = 1
    _directives['math'] = math_directive
else:
    class math_directive(Directive):
        has_content = True
        def run(self):
            latex = ' '.join(self.content)
            try:
                mathml_tree = parse_latex_math(latex, inline=False)
            except SyntaxError, msg:
                error = self.state_machine.reporter.error(
                    msg, nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
                return [error]
            node = latex_math(self.block_text)
            node['latex'] = latex
            node['mathml_tree'] = mathml_tree
            return [node]
    from docutils.parsers.rst import directives
    directives.register_directive('math', math_directive)

def setup(app):
    app.add_node(latex_math)
    app.add_role('math', math_role)

    # Add visit/depart methods to HTML-Translator:
    def visit_latex_math_html(self, node):
        mathml = ''.join(node['mathml_tree'].xml())
        self.body.append(mathml)
    def depart_latex_math_html(self, node):
            pass
    HTMLTranslator.visit_latex_math = visit_latex_math_html
    HTMLTranslator.depart_latex_math = depart_latex_math_html

    # Add visit/depart methods to LaTeX-Translator:
    def visit_latex_math_latex(self, node):
        inline = isinstance(node.parent, nodes.TextElement)
        if inline:
            self.body.append('$%s$' % node['latex'])
        else:
            self.body.extend(['\\begin{equation}',
                              node['latex'],
                              '\\end{equation}'])
    def depart_latex_math_latex(self, node):
            pass
    LaTeXTranslator.visit_latex_math = visit_latex_math_latex
    LaTeXTranslator.depart_latex_math = depart_latex_math_latex


# LaTeX to MathML translation stuff:
class math:
    """Base class for MathML elements."""

    nchildren = 1000000
    """Required number of children"""

    def __init__(self, children=None, inline=None):
        """math([children]) -> MathML element

        children can be one child or a list of children."""

        self.children = []
        if children is not None:
            if type(children) is list:
                for child in children:
                    self.append(child)
            else:
                # Only one child:
                self.append(children)

        if inline is not None:
            self.inline = inline

    def __repr__(self):
        if hasattr(self, 'children'):
            return self.__class__.__name__ + '(%s)' % \
                   ','.join([repr(child) for child in self.children])
        else:
            return self.__class__.__name__

    def full(self):
        """Room for more children?"""

        return len(self.children) >= self.nchildren

    def append(self, child):
        """append(child) -> element

        Appends child and returns self if self is not full or first
        non-full parent."""

        assert not self.full()
        self.children.append(child)
        child.parent = self
        node = self
        while node.full():
            node = node.parent
        return node

    def delete_child(self):
        """delete_child() -> child

        Delete last child and return it."""

        child = self.children[-1]
        del self.children[-1]
        return child

    def close(self):
        """close() -> parent

        Close element and return first non-full element."""

        parent = self.parent
        while parent.full():
            parent = parent.parent
        return parent

    def xml(self):
        """xml() -> xml-string"""

        return self.xml_start() + self.xml_body() + self.xml_end()

    def xml_start(self):
        if not hasattr(self, 'inline'):
            return ['<%s>' % self.__class__.__name__]
        xmlns = 'http://www.w3.org/1998/Math/MathML'
        if self.inline:
            return ['<math xmlns="%s">' % xmlns]
        else:
            return ['<math xmlns="%s" mode="display">' % xmlns]

    def xml_end(self):
        return ['</%s>' % self.__class__.__name__]

    def xml_body(self):
        xml = []
        for child in self.children:
            xml.extend(child.xml())
        return xml

class mrow(math): pass
class mtable(math): pass
class mtr(mrow): pass
class mtd(mrow): pass

class mx(math):
    """Base class for mo, mi, and mn"""

    nchildren = 0
    def __init__(self, data):
        self.data = data

    def xml_body(self):
        return [self.data]

class mo(mx):
    translation = {'<': '&lt;', '>': '&gt;'}
    def xml_body(self):
        return [self.translation.get(self.data, self.data)]

class mi(mx): pass
class mn(mx): pass

class msub(math):
    nchildren = 2

class msup(math):
    nchildren = 2

class msqrt(math):
    nchildren = 1

class mroot(math):
    nchildren = 2

class mfrac(math):
    nchildren = 2

class msubsup(math):
    nchildren = 3
    def __init__(self, children=None, reversed=False):
        self.reversed = reversed
        math.__init__(self, children)

    def xml(self):
        if self.reversed:
##            self.children[1:3] = self.children[2:0:-1]
            self.children[1:3] = [self.children[2], self.children[1]]
            self.reversed = False
        return math.xml(self)

class mfenced(math):
    translation = {'\\{': '{', '\\langle': u'\u2329',
                   '\\}': '}', '\\rangle': u'\u232A',
                   '.': ''}
    def __init__(self, par):
        self.openpar = par
        math.__init__(self)

    def xml_start(self):
        open = self.translation.get(self.openpar, self.openpar)
        close = self.translation.get(self.closepar, self.closepar)
        return ['<mfenced open="%s" close="%s">' % (open, close)]

class mspace(math):
    nchildren = 0

class mstyle(math):
    def __init__(self, children=None, nchildren=None, **kwargs):
        if nchildren is not None:
            self.nchildren = nchildren
        math.__init__(self, children)
        self.attrs = kwargs

    def xml_start(self):
        return ['<mstyle '] + ['%s="%s"' % item
                               for item in self.attrs.items()] + ['>']

class mover(math):
    nchildren = 2
    def __init__(self, children=None, reversed=False):
        self.reversed = reversed
        math.__init__(self, children)

    def xml(self):
        if self.reversed:
            self.children.reverse()
            self.reversed = False
        return math.xml(self)

class munder(math):
    nchildren = 2

class munderover(math):
    nchildren = 3
    def __init__(self, children=None):
        math.__init__(self, children)

class mtext(math):
    nchildren = 0
    def __init__(self, text):
        self.text = text

    def xml_body(self):
        return [self.text]


over = {'tilde': '~',
        'hat': '^',
        'bar': '_',
        'vec': u'\u2192'}

Greek = {
    # Upper case greek letters:
    'Phi': u'\u03a6', 'Xi': u'\u039e', 'Sigma': u'\u03a3', 'Psi': u'\u03a8', 'Delta': u'\u0394', 'Theta': u'\u0398', 'Upsilon': u'\u03d2', 'Pi': u'\u03a0', 'Omega': u'\u03a9', 'Gamma': u'\u0393', 'Lambda': u'\u039b'}
greek = {
    # Lower case greek letters:
    'tau': u'\u03c4', 'phi': u'\u03d5', 'xi': u'\u03be', 'iota': u'\u03b9', 'epsilon': u'\u03f5', 'varrho': u'\u03f1', 'varsigma': u'\u03c2', 'beta': u'\u03b2', 'psi': u'\u03c8', 'rho': u'\u03c1', 'delta': u'\u03b4', 'alpha': u'\u03b1', 'zeta': u'\u03b6', 'omega': u'\u03c9', 'varepsilon': u'\u03b5', 'kappa': u'\u03ba', 'vartheta': u'\u03d1', 'chi': u'\u03c7', 'upsilon': u'\u03c5', 'sigma': u'\u03c3', 'varphi': u'\u03c6', 'varpi': u'\u03d6', 'mu': u'\u03bc', 'eta': u'\u03b7', 'theta': u'\u03b8', 'pi': u'\u03c0', 'varkappa': u'\u03f0', 'nu': u'\u03bd', 'gamma': u'\u03b3', 'lambda': u'\u03bb'}

special = {
    # Binary operation symbols:
    'wedge': u'\u2227', 'diamond': u'\u22c4', 'star': u'\u22c6', 'amalg': u'\u2a3f', 'ast': u'\u2217', 'odot': u'\u2299', 'triangleleft': u'\u25c1', 'bigtriangleup': u'\u25b3', 'ominus': u'\u2296', 'ddagger': u'\u2021', 'wr': u'\u2240', 'otimes': u'\u2297', 'sqcup': u'\u2294', 'oplus': u'\u2295', 'bigcirc': u'\u25cb', 'oslash': u'\u2298', 'sqcap': u'\u2293', 'bullet': u'\u2219', 'cup': u'\u222a', 'cdot': u'\u22c5', 'cap': u'\u2229', 'bigtriangledown': u'\u25bd', 'times': u'\xd7', 'setminus': u'\u2216', 'circ': u'\u2218', 'vee': u'\u2228', 'uplus': u'\u228e', 'mp': u'\u2213', 'dagger': u'\u2020', 'triangleright': u'\u25b7', 'div': u'\xf7', 'pm': u'\xb1',
    # Relation symbols:
    'subset': u'\u2282', 'propto': u'\u221d', 'geq': u'\u2265', 'ge': u'\u2265', 'sqsubset': u'\u228f', 'Join': u'\u2a1d', 'frown': u'\u2322', 'models': u'\u22a7', 'supset': u'\u2283', 'in': u'\u2208', 'doteq': u'\u2250', 'dashv': u'\u22a3', 'gg': u'\u226b', 'leq': u'\u2264', 'succ': u'\u227b', 'vdash': u'\u22a2', 'cong': u'\u2245', 'simeq': u'\u2243', 'subseteq': u'\u2286', 'parallel': u'\u2225', 'equiv': u'\u2261', 'ni': u'\u220b', 'le': u'\u2264', 'approx': u'\u2248', 'precsim': u'\u227e', 'sqsupset': u'\u2290', 'll': u'\u226a', 'sqsupseteq': u'\u2292', 'mid': u'\u2223', 'prec': u'\u227a', 'succsim': u'\u227f', 'bowtie': u'\u22c8', 'perp': u'\u27c2', 'sqsubseteq': u'\u2291', 'asymp': u'\u224d', 'smile': u'\u2323', 'supseteq': u'\u2287', 'sim': u'\u223c', 'neq': u'\u2260',
    # Arrow symbols:
    'searrow': u'\u2198', 'updownarrow': u'\u2195', 'Uparrow': u'\u21d1', 'longleftrightarrow': u'\u27f7', 'Leftarrow': u'\u21d0', 'longmapsto': u'\u27fc', 'Longleftarrow': u'\u27f8', 'nearrow': u'\u2197', 'hookleftarrow': u'\u21a9', 'downarrow': u'\u2193', 'Leftrightarrow': u'\u21d4', 'longrightarrow': u'\u27f6', 'rightharpoondown': u'\u21c1', 'longleftarrow': u'\u27f5', 'rightarrow': u'\u2192', 'Updownarrow': u'\u21d5', 'rightharpoonup': u'\u21c0', 'Longleftrightarrow': u'\u27fa', 'leftarrow': u'\u2190', 'mapsto': u'\u21a6', 'nwarrow': u'\u2196', 'uparrow': u'\u2191', 'leftharpoonup': u'\u21bc', 'leftharpoondown': u'\u21bd', 'Downarrow': u'\u21d3', 'leftrightarrow': u'\u2194', 'Longrightarrow': u'\u27f9', 'swarrow': u'\u2199', 'hookrightarrow': u'\u21aa', 'Rightarrow': u'\u21d2',
    # Miscellaneous symbols:
    'infty': u'\u221e', 'surd': u'\u221a', 'partial': u'\u2202', 'ddots': u'\u22f1', 'exists': u'\u2203', 'flat': u'\u266d', 'diamondsuit': u'\u2662', 'wp': u'\u2118', 'spadesuit': u'\u2660', 'Re': u'\u211c', 'vdots': u'\u22ee', 'aleph': u'\u2135', 'clubsuit': u'\u2663', 'sharp': u'\u266f', 'angle': u'\u2220', 'prime': u'\u2032', 'natural': u'\u266e', 'ell': u'\u2113', 'neg': u'\xac', 'top': u'\u22a4', 'nabla': u'\u2207', 'bot': u'\u22a5', 'heartsuit': u'\u2661', 'cdots': u'\u22ef', 'Im': u'\u2111', 'forall': u'\u2200', 'imath': u'\u0131', 'hbar': u'\u210f', 'emptyset': u'\u2205',
    # Variable-sized symbols:
    'bigotimes': u'\u2a02', 'coprod': u'\u2210', 'int': u'\u222b', 'sum': u'\u2211', 'bigodot': u'\u2a00', 'bigcup': u'\u22c3', 'biguplus': u'\u2a04', 'bigcap': u'\u22c2', 'bigoplus': u'\u2a01', 'oint': u'\u222e', 'bigvee': u'\u22c1', 'bigwedge': u'\u22c0', 'prod': u'\u220f',
    # Braces:
    'langle': u'\u2329', 'rangle': u'\u232A'}

sumintprod = ''.join([special[symbol] for symbol in
                      ['sum', 'int', 'oint', 'prod']])

functions = ['arccos', 'arcsin', 'arctan', 'arg', 'cos',  'cosh',
             'cot',    'coth',   'csc',    'deg', 'det',  'dim',
             'exp',    'gcd',    'hom',    'inf', 'ker',  'lg',
             'lim',    'liminf', 'limsup', 'ln',  'log',  'max',
             'min',    'Pr',     'sec',    'sin', 'sinh', 'sup',
             'tan',    'tanh',
             'injlim',  'varinjlim', 'varlimsup',
             'projlim', 'varliminf', 'varprojlim']


def parse_latex_math(string, inline=True):
    """parse_latex_math(string [,inline]) -> MathML-tree

    Returns a MathML-tree parsed from string.  inline=True is for
    inline math and inline=False is for displayed math.

    tree is the whole tree and node is the current element."""

    # Normalize white-space:
    string = ' '.join(string.split())

    if inline:
        node = mrow()
        tree = math(node, inline=True)
    else:
        node = mtd()
        tree = math(mtable(mtr(node)), inline=False)

    while len(string) > 0:
        n = len(string)
        c = string[0]
        skip = 1  # number of characters consumed
        if n > 1:
            c2 = string[1]
        else:
            c2 = ''
##        print n, string, c, c2, node.__class__.__name__
        if c == ' ':
            pass
        elif c == '\\':
            if c2 in '{}':
                node = node.append(mo(c2))
                skip = 2
            elif c2 == ' ':
                node = node.append(mspace())
                skip = 2
            elif c2.isalpha():
                # We have a LaTeX-name:
                i = 2
                while i < n and string[i].isalpha():
                    i += 1
                name = string[1:i]
                node, skip = handle_keyword(name, node, string[i:])
                skip += i
            elif c2 == '\\':
                # End of a row:
                entry = mtd()
                row = mtr(entry)
                node.close().close().append(row)
                node = entry
                skip = 2
            else:
                raise SyntaxError('Syntax error: "%s%s"' % (c, c2))
        elif c.isalpha():
            node = node.append(mi(c))
        elif c.isdigit():
            node = node.append(mn(c))
        elif c in "+-/()[]|=<>,.!'":
            node = node.append(mo(c))
        elif c == '_':
            child = node.delete_child()
            if isinstance(child, msup):
                sub = msubsup(child.children, reversed=True)
            elif isinstance(child, mo) and child.data in sumintprod:
                sub = munder(child)
            else:
                sub = msub(child)
            node.append(sub)
            node = sub
        elif c == '^':
            child = node.delete_child()
            if isinstance(child, msub):
                sup = msubsup(child.children)
            elif isinstance(child, mo) and child.data in sumintprod:
                sup = mover(child)
            elif (isinstance(child, munder) and
                  child.children[0].data in sumintprod):
                sup = munderover(child.children)
            else:
                sup = msup(child)
            node.append(sup)
            node = sup
        elif c == '{':
            row = mrow()
            node.append(row)
            node = row
        elif c == '}':
            node = node.close()
        elif c == '&':
            entry = mtd()
            node.close().append(entry)
            node = entry
        else:
            raise SyntaxError('Illegal character: "%s"' % c)
        string = string[skip:]
    return tree


mathbb = {'A': u'\U0001D538',
          'B': u'\U0001D539',
          'C': u'\u2102',
          'D': u'\U0001D53B',
          'E': u'\U0001D53C',
          'F': u'\U0001D53D',
          'G': u'\U0001D53E',
          'H': u'\u210D',
          'I': u'\U0001D540',
          'J': u'\U0001D541',
          'K': u'\U0001D542',
          'L': u'\U0001D543',
          'M': u'\U0001D544',
          'N': u'\u2115',
          'O': u'\U0001D546',
          'P': u'\u2119',
          'Q': u'\u211A',
          'R': u'\u211D',
          'S': u'\U0001D54A',
          'T': u'\U0001D54B',
          'U': u'\U0001D54C',
          'V': u'\U0001D54D',
          'W': u'\U0001D54E',
          'X': u'\U0001D54F',
          'Y': u'\U0001D550',
          'Z': u'\u2124'}

negatables = {'=': u'\u2260',
              '\in': u'\u2209',
              '\equiv': u'\u2262'}


def handle_keyword(name, node, string):
    skip = 0
    if len(string) > 0 and string[0] == ' ':
        string = string[1:]
        skip = 1
    if name == 'begin':
        if not string.startswith('{matrix}'):
            raise SyntaxError('Expected "\begin{matrix}"!')
        skip += 8
        entry = mtd()
        table = mtable(mtr(entry))
        node.append(table)
        node = entry
    elif name == 'end':
        if not string.startswith('{matrix}'):
            raise SyntaxError('Expected "\end{matrix}"!')
        skip += 8
        node = node.close().close().close()
    elif name == 'text':
        if string[0] != '{':
            raise SyntaxError('Expected "\text{...}"!')
        i = string.find('}')
        if i == -1:
            raise SyntaxError('Expected "\text{...}"!')
        node = node.append(mtext(string[1:i]))
        skip += i + 1
    elif name == 'sqrt':
        sqrt = msqrt()
        node.append(sqrt)
        node = sqrt
    elif name == 'frac':
        frac = mfrac()
        node.append(frac)
        node = frac
    elif name == 'left':
        for par in ['(', '[', '|', '\\{', '\\langle', '.']:
            if string.startswith(par):
                break
        else:
            raise SyntaxError('Missing left-brace!')
        fenced = mfenced(par)
        node.append(fenced)
        row = mrow()
        fenced.append(row)
        node = row
        skip += len(par)
    elif name == 'right':
        for par in [')', ']', '|', '\\}', '\\rangle', '.']:
            if string.startswith(par):
                break
        else:
            raise SyntaxError('Missing right-brace!')
        node = node.close()
        node.closepar = par
        node = node.close()
        skip += len(par)
    elif name == 'not':
        for operator in negatables:
            if string.startswith(operator):
                break
        else:
            raise SyntaxError('Expected something to negate: "\\not ..."!')
        node = node.append(mo(negatables[operator]))
        skip += len(operator)
    elif name == 'mathbf':
        style = mstyle(nchildren=1, fontweight='bold')
        node.append(style)
        node = style
    elif name == 'mathbb':
        if string[0] != '{' or not string[1].isupper() or string[2] != '}':
            raise SyntaxError('Expected something like "\mathbb{A}"!')
        node = node.append(mi(mathbb[string[1]]))
        skip += 3
    elif name in greek:
        node = node.append(mi(greek[name]))
    elif name in Greek:
        node = node.append(mo(Greek[name]))
    elif name in special:
        node = node.append(mo(special[name]))
    elif name in functions:
        node = node.append(mo(name))
    else:
        chr = over.get(name)
        if chr is not None:
            ovr = mover(mo(chr), reversed=True)
            node.append(ovr)
            node = ovr
        else:
            raise SyntaxError('Unknown LaTeX command: ' + name)

    return node, skip

########NEW FILE########
__FILENAME__ = mathmpl
import os
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.writers.html4css1 import HTMLTranslator
from sphinx.latexwriter import LaTeXTranslator
import warnings

# Define LaTeX math node:
class latex_math(nodes.General, nodes.Element):
    pass

def fontset_choice(arg):
    return directives.choice(arg, ['cm', 'stix', 'stixsans'])

options_spec = {'fontset': fontset_choice}

def math_role(role, rawtext, text, lineno, inliner,
              options={}, content=[]):
    i = rawtext.find('`')
    latex = rawtext[i+1:-1]
    node = latex_math(rawtext)
    node['latex'] = latex
    node['fontset'] = options.get('fontset', 'cm')
    return [node], []
math_role.options = options_spec

def math_directive_run(content, block_text, options):
    latex = ''.join(content)
    node = latex_math(block_text)
    node['latex'] = latex
    node['fontset'] = options.get('fontset', 'cm')
    return [node]

try:
    from docutils.parsers.rst import Directive
except ImportError:
    # Register directive the old way:
    from docutils.parsers.rst.directives import _directives
    def math_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
        return math_directive_run(content, block_text, options)
    math_directive.arguments = None
    math_directive.options = options_spec
    math_directive.content = 1
    _directives['math'] = math_directive
else:
    class math_directive(Directive):
        has_content = True
        option_spec = options_spec

        def run(self):
            return math_directive_run(self.content, self.block_text,
                                      self.options)
    from docutils.parsers.rst import directives
    directives.register_directive('math', math_directive)

def setup(app):
    app.add_node(latex_math)
    app.add_role('math', math_role)

    # Add visit/depart methods to HTML-Translator:
    def visit_latex_math_html(self, node):
        source = self.document.attributes['source']
        self.body.append(latex2html(node, source))
    def depart_latex_math_html(self, node):
            pass
    HTMLTranslator.visit_latex_math = visit_latex_math_html
    HTMLTranslator.depart_latex_math = depart_latex_math_html

    # Add visit/depart methods to LaTeX-Translator:
    def visit_latex_math_latex(self, node):
        inline = isinstance(node.parent, nodes.TextElement)
        if inline:
            self.body.append('$%s$' % node['latex'])
        else:
            self.body.extend(['\\begin{equation}',
                              node['latex'],
                              '\\end{equation}'])
    def depart_latex_math_latex(self, node):
            pass
    LaTeXTranslator.visit_latex_math = visit_latex_math_latex
    LaTeXTranslator.depart_latex_math = depart_latex_math_latex

from matplotlib import rcParams
from matplotlib.mathtext import MathTextParser
rcParams['mathtext.fontset'] = 'cm'
mathtext_parser = MathTextParser("Bitmap")


# This uses mathtext to render the expression
def latex2png(latex, filename, fontset='cm'):
    latex = "$%s$" % latex
    orig_fontset = rcParams['mathtext.fontset']
    rcParams['mathtext.fontset'] = fontset
    if os.path.exists(filename):
        depth = mathtext_parser.get_depth(latex, dpi=100)
    else:
        try:
            depth = mathtext_parser.to_png(filename, latex, dpi=100)
        except:
            warnings.warn("Could not render math expression %s" % latex,
                          Warning)
            depth = 0
    rcParams['mathtext.fontset'] = orig_fontset
    return depth

# LaTeX to HTML translation stuff:
def latex2html(node, source):
    inline = isinstance(node.parent, nodes.TextElement)
    latex = node['latex']
    name = 'math-%s' % md5(latex).hexdigest()[-10:]
    dest = '_static/%s.png' % name
    depth = latex2png(latex, dest, node['fontset'])

    path = '_static'
    count = source.split('/doc/')[-1].count('/')
    for i in range(count):
        if os.path.exists(path): break
        path = '../'+path
    path = '../'+path #specifically added for matplotlib
    if inline:
        cls = ''
    else:
        cls = 'class="center" '
    if inline and depth != 0:
        style = 'style="position: relative; bottom: -%dpx"' % (depth + 1)
    else:
        style = ''

    return '<img src="%s/%s.png" %s%s/>' % (path, name, cls, style)


########NEW FILE########
__FILENAME__ = math_symbol_table
symbols = [
    ["Lower-case Greek",
     5,
     r"""\alpha \beta \gamma \chi \delta \epsilon \eta \iota \kappa
         \lambda \mu \nu \omega \phi \pi \psi \rho \sigma \tau \theta
         \upsilon \xi \zeta \digamma \varepsilon \varkappa \varphi
         \varpi \varrho \varsigma \vartheta"""],
    ["Upper-case Greek",
     6,
     r"""\Delta \Gamma \Lambda \Omega \Phi \Pi \Psi \Sigma \Theta
     \Upsilon \Xi \mho \nabla"""],
    ["Hebrew",
     4,
     r"""\aleph \beth \daleth \gimel"""],
    ["Delimiters",
     6,
     r"""| \{ \lfloor / \Uparrow \llcorner \vert \} \rfloor \backslash
         \uparrow \lrcorner \| \langle \lceil [ \Downarrow \ulcorner
         \Vert \rangle \rceil ] \downarrow \urcorner"""],
    ["Big symbols",
     5,
     r"""\bigcap \bigcup \bigodot \bigoplus \bigotimes \biguplus
         \bigvee \bigwedge \coprod \oint \prod \sum \int"""],
    ["Standard function names",
     4,
     r"""\arccos \csc \ker \min \arcsin \deg \lg \Pr \arctan \det \lim
         \gcd \ln \sup \cot \hom \log \tan \coth \inf \max \tanh
         \sec \arg \dim \liminf \sin \cos \exp \limsup \sinh \cosh"""],
    ["Binary operation and relation symbols",
     3,
     r"""\ast \pm \slash \cap \star \mp \cup \cdot \uplus
     \triangleleft \circ \odot \sqcap \triangleright \bullet \ominus
     \sqcup \bigcirc \oplus \wedge \diamond \oslash \vee
     \bigtriangledown \times \otimes \dag \bigtriangleup \div \wr
     \ddag \barwedge \veebar \boxplus \curlywedge \curlyvee \boxminus
     \Cap \Cup \boxtimes \bot \top \dotplus \boxdot \intercal
     \rightthreetimes \divideontimes \leftthreetimes \equiv \leq \geq
     \perp \cong \prec \succ \mid \neq \preceq \succeq \parallel \sim
     \ll \gg \bowtie \simeq \subset \supset \Join \approx \subseteq
     \supseteq \ltimes \asymp \sqsubset \sqsupset \rtimes \doteq
     \sqsubseteq \sqsupseteq \smile \propto \dashv \vdash \frown
     \models \in \ni \notin \approxeq \leqq \geqq \lessgtr \leqslant
     \geqslant \lesseqgtr \backsim \lessapprox \gtrapprox \lesseqqgtr
     \backsimeq \lll \ggg \gtreqqless \triangleq \lessdot \gtrdot
     \gtreqless \circeq \lesssim \gtrsim \gtrless \bumpeq \eqslantless
     \eqslantgtr \backepsilon \Bumpeq \precsim \succsim \between
     \doteqdot \precapprox \succapprox \pitchfork \Subset \Supset
     \fallingdotseq \subseteqq \supseteqq \risingdotseq \sqsubset
     \sqsupset \varpropto \preccurlyeq \succcurlyeq \Vdash \therefore
     \curlyeqprec \curlyeqsucc \vDash \because \blacktriangleleft
     \blacktriangleright \Vvdash \eqcirc \trianglelefteq
     \trianglerighteq \neq \vartriangleleft \vartriangleright \ncong
     \nleq \ngeq \nsubseteq \nmid \nsupseteq \nparallel \nless \ngtr
     \nprec \nsucc \subsetneq \nsim \supsetneq \nVDash \precnapprox
     \succnapprox \subsetneqq \nvDash \precnsim \succnsim \supsetneqq
     \nvdash \lnapprox \gnapprox \ntriangleleft \ntrianglelefteq
     \lneqq \gneqq \ntriangleright \lnsim \gnsim \ntrianglerighteq
     \coloneq \eqsim \nequiv \napprox \nsupset \doublebarwedge \nVdash
     \Doteq \nsubset \eqcolon \ne
     """],
    ["Arrow symbols",
     2,
     r"""\leftarrow \longleftarrow \uparrow \Leftarrow \Longleftarrow
     \Uparrow \rightarrow \longrightarrow \downarrow \Rightarrow
     \Longrightarrow \Downarrow \leftrightarrow \updownarrow
     \longleftrightarrow \updownarrow \Leftrightarrow
     \Longleftrightarrow \Updownarrow \mapsto \longmapsto \nearrow
     \hookleftarrow \hookrightarrow \searrow \leftharpoonup
     \rightharpoonup \swarrow \leftharpoondown \rightharpoondown
     \nwarrow \rightleftharpoons \leadsto \dashrightarrow
     \dashleftarrow \leftleftarrows \leftrightarrows \Lleftarrow
     \Rrightarrow \twoheadleftarrow \leftarrowtail \looparrowleft
     \leftrightharpoons \curvearrowleft \circlearrowleft \Lsh
     \upuparrows \upharpoonleft \downharpoonleft \multimap
     \leftrightsquigarrow \rightrightarrows \rightleftarrows
     \rightrightarrows \rightleftarrows \twoheadrightarrow
     \rightarrowtail \looparrowright \rightleftharpoons
     \curvearrowright \circlearrowright \Rsh \downdownarrows
     \upharpoonright \downharpoonright \rightsquigarrow \nleftarrow
     \nrightarrow \nLeftarrow \nRightarrow \nleftrightarrow
     \nLeftrightarrow \to \Swarrow \Searrow \Nwarrow \Nearrow
     \leftsquigarrow
     """],
    ["Miscellaneous symbols",
     3,
     r"""\neg \infty \forall \wp \exists \bigstar \angle \partial
     \nexists \measuredangle \eth \emptyset \sphericalangle \clubsuit
     \varnothing \complement \diamondsuit \imath \Finv \triangledown
     \heartsuit \jmath \Game \spadesuit \ell \hbar \vartriangle \cdots
     \hslash \vdots \blacksquare \ldots \blacktriangle \ddots \sharp
     \prime \blacktriangledown \Im \flat \backprime \Re \natural
     \circledS \P \copyright \ss \circledR \S \yen \AA \checkmark \$
     \iiint \iint \iint \oiiint"""]
]

def run(state_machine):
    def get_n(n, l):
        part = []
        for x in l:
            part.append(x)
            if len(part) == n:
                yield part
                part = []
        yield part

    lines = []
    for category, columns, syms in symbols:
        syms = syms.split()
        syms.sort()
        lines.append("**%s**" % category)
        lines.append('')
        max_width = 0
        for sym in syms:
            max_width = max(max_width, len(sym))
        max_width = max_width * 2 + 16
        header = "    " + (('=' * max_width) + ' ') * columns
        format = '%%%ds' % max_width
        for chunk in get_n(20, get_n(columns, syms)):
            lines.append(header)
            for part in chunk:
                line = []
                for sym in part:
                    line.append(format % (":math:`%s` ``%s``" % (sym, sym)))
                lines.append("    " + " ".join(line))
            lines.append(header)
            lines.append('')

    state_machine.insert_input(lines, "Symbol table")
    return []

try:
    from docutils.parsers.rst import Directive
except ImportError:
    from docutils.parsers.rst.directives import _directives
    def math_symbol_table_directive(name, arguments, options, content, lineno,
                                    content_offset, block_text, state, state_machine):
        return run(state_machine)
    math_symbol_table_directive.arguments = None
    math_symbol_table_directive.options = {}
    math_symbol_table_directive.content = False
    _directives['math_symbol_table'] = math_symbol_table_directive
else:
    class math_symbol_table_directive(Directive):
        has_content = False
        def run(self):
            return run(self.state_machine)
    from docutils.parsers.rst import directives
    directives.register_directive('math_symbol_table',
                                  math_symbol_table_directive)

if __name__ == "__main__":
    # Do some verification of the tables
    from matplotlib import _mathtext_data

    print "SYMBOLS NOT IN STIX:"
    all_symbols = {}
    for category, columns, syms in symbols:
        if category == "Standard Function Names":
            continue
        syms = syms.split()
        for sym in syms:
            if len(sym) > 1:
                all_symbols[sym[1:]] = None
                if sym[1:] not in _mathtext_data.tex2uni:
                    print sym

    print "SYMBOLS NOT IN TABLE:"
    for sym in _mathtext_data.tex2uni:
        if sym not in all_symbols:
            print sym

########NEW FILE########
__FILENAME__ = only_directives
#
# A pair of directives for inserting content that will only appear in
# either html or latex.
#

from docutils.nodes import Body, Element
from docutils.writers.html4css1 import HTMLTranslator
try:
    from sphinx.writers.latex import LaTeXTranslator
except ImportError:
    # Old Sphinx versions
    from sphinx.latexwriter import LaTeXTranslator
    
from docutils.parsers.rst import directives

class html_only(Body, Element):
    pass

class latex_only(Body, Element):
    pass

def run(content, node_class, state, content_offset):
    text = '\n'.join(content)
    node = node_class(text)
    state.nested_parse(content, content_offset, node)
    return [node]

try:
    from docutils.parsers.rst import Directive
except ImportError:
    from docutils.parsers.rst.directives import _directives

    def html_only_directive(name, arguments, options, content, lineno,
                            content_offset, block_text, state, state_machine):
        return run(content, html_only, state, content_offset)

    def latex_only_directive(name, arguments, options, content, lineno,
                             content_offset, block_text, state, state_machine):
        return run(content, latex_only, state, content_offset)

    for func in (html_only_directive, latex_only_directive):
        func.content = 1
        func.options = {}
        func.arguments = None

    _directives['htmlonly'] = html_only_directive
    _directives['latexonly'] = latex_only_directive
else:
    class OnlyDirective(Directive):
        has_content = True
        required_arguments = 0
        optional_arguments = 0
        final_argument_whitespace = True
        option_spec = {}

        def run(self):
            self.assert_has_content()
            return run(self.content, self.node_class,
                       self.state, self.content_offset)

    class HtmlOnlyDirective(OnlyDirective):
        node_class = html_only

    class LatexOnlyDirective(OnlyDirective):
        node_class = latex_only

    directives.register_directive('htmlonly', HtmlOnlyDirective)
    directives.register_directive('latexonly', LatexOnlyDirective)

def setup(app):
    app.add_node(html_only)
    app.add_node(latex_only)

    # Add visit/depart methods to HTML-Translator:
    def visit_perform(self, node):
        pass
    def depart_perform(self, node):
        pass
    def visit_ignore(self, node):
        node.children = []
    def depart_ignore(self, node):
        node.children = []

    HTMLTranslator.visit_html_only = visit_perform
    HTMLTranslator.depart_html_only = depart_perform
    HTMLTranslator.visit_latex_only = visit_ignore
    HTMLTranslator.depart_latex_only = depart_ignore

    LaTeXTranslator.visit_html_only = visit_ignore
    LaTeXTranslator.depart_html_only = depart_ignore
    LaTeXTranslator.visit_latex_only = visit_perform
    LaTeXTranslator.depart_latex_only = depart_perform

########NEW FILE########
__FILENAME__ = plot_directive
"""A special directive for including a matplotlib plot.

Given a path to a .py file, it includes the source code inline, then:

- On HTML, will include a .png with a link to a high-res .png.

- On LaTeX, will include a .pdf

This directive supports all of the options of the `image` directive,
except for `target` (since plot will add its own target).

Additionally, if the :include-source: option is provided, the literal
source will be included inline, as well as a link to the source.

The set of file formats to generate can be specified with the
plot_formats configuration variable.
"""

import sys, os, glob, shutil, hashlib, imp, warnings, cStringIO
import traceback
import re
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
from docutils.parsers.rst import directives
try:
    # docutils 0.4
    from docutils.parsers.rst.directives.images import align
except ImportError:
    # docutils 0.5
    from docutils.parsers.rst.directives.images import Image
    align = Image.align
from docutils import nodes
import sphinx

sphinx_version = sphinx.__version__.split(".")
# The split is necessary for sphinx beta versions where the string is
# '6b1'
sphinx_version = tuple([int(re.split('[a-z]', x)[0])
                        for x in sphinx_version[:2]])

import matplotlib
import matplotlib.cbook as cbook
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as image
from matplotlib import _pylab_helpers

import only_directives

if hasattr(os.path, 'relpath'):
    relpath = os.path.relpath
else:
    def relpath(target, base=os.curdir):
        """
        Return a relative path to the target from either the current dir or an optional base dir.
        Base can be a directory specified either as absolute or relative to current dir.
        """

        if not os.path.exists(target):
            raise OSError, 'Target does not exist: '+target

        if not os.path.isdir(base):
            raise OSError, 'Base is not a directory or does not exist: '+base

        base_list = (os.path.abspath(base)).split(os.sep)
        target_list = (os.path.abspath(target)).split(os.sep)

        # On the windows platform the target may be on a completely different drive from the base.
        if os.name in ['nt','dos','os2'] and base_list[0] <> target_list[0]:
            raise OSError, 'Target is on a different drive to base. Target: '+target_list[0].upper()+', base: '+base_list[0].upper()

        # Starting from the filepath root, work out how much of the filepath is
        # shared by base and target.
        for i in range(min(len(base_list), len(target_list))):
            if base_list[i] <> target_list[i]: break
        else:
            # If we broke out of the loop, i is pointing to the first differing path elements.
            # If we didn't break out of the loop, i is pointing to identical path elements.
            # Increment i so that in all cases it points to the first differing path elements.
            i+=1

        rel_list = [os.pardir] * (len(base_list)-i) + target_list[i:]
        if rel_list:
            return os.path.join(*rel_list)
        else:
            return ""

def write_char(s):
    sys.stdout.write(s)
    sys.stdout.flush()

options = {'alt': directives.unchanged,
           'height': directives.length_or_unitless,
           'width': directives.length_or_percentage_or_unitless,
           'scale': directives.nonnegative_int,
           'align': align,
           'class': directives.class_option,
           'include-source': directives.flag,
           'encoding': directives.encoding}

template = """
.. htmlonly::

   [%(links)s]

   .. image:: %(prefix)s%(tmpdir)s/%(outname)s.png
   %(options)s

.. latexonly::
   .. image:: %(prefix)s%(tmpdir)s/%(outname)s.pdf
   %(options)s
"""

exception_template = """
.. htmlonly::

   [`source code <%(linkdir)s/%(basename)s.py>`__]

Exception occurred rendering plot.

"""

def out_of_date(original, derived):
    """
    Returns True if derivative is out-of-date wrt original,
    both of which are full file paths.
    """
    return (not os.path.exists(derived))
    # or os.stat(derived).st_mtime < os.stat(original).st_mtime)

def runfile(fullpath):
    """
    Import a Python module from a path.
    """
    # Change the working directory to the directory of the example, so
    # it can get at its data files, if any.
    pwd = os.getcwd()
    path, fname = os.path.split(fullpath)
    sys.path.insert(0, os.path.abspath(path))
    stdout = sys.stdout
    sys.stdout = cStringIO.StringIO()
    os.chdir(path)
    try:
        fd = open(fname)
        module = imp.load_module("__main__", fd, fname, ('py', 'r', imp.PY_SOURCE))
    finally:
        del sys.path[0]
        os.chdir(pwd)
        sys.stdout = stdout
    return module

def makefig(fullpath, code, outdir):
    """
    run a pyplot script and save the low and high res PNGs and a PDF in _static
    """
    formats = [('png', 80), ('hires.png', 200), ('pdf', 50)]

    fullpath = str(fullpath)  # todo, why is unicode breaking this
    basedir, fname = os.path.split(fullpath)
    basename, ext = os.path.splitext(fname)

    if str(basename) == "None":
        import pdb
        pdb.set_trace()

    all_exists = True

    # Look for single-figure output files first
    for format, dpi in formats:
        outname = os.path.join(outdir, '%s.%s' % (basename, format))
        if out_of_date(fullpath, outname):
            all_exists = False
            break

    if all_exists:
        write_char('.' * len(formats))
        return 1

    # Then look for multi-figure output files, assuming
    # if we have some we have all...
    i = 0
    while True:
        all_exists = True
        for format, dpi in formats:
            outname = os.path.join(outdir, '%s_%02d.%s' % (basename, i, format))
            if out_of_date(fullpath, outname):
                all_exists = False
                break
        if all_exists:
            i += 1
        else:
            break

    if i != 0:
        write_char('.' * i * len(formats))
        return i

    # We didn't find the files, so build them

    plt.close('all')    # we need to clear between runs
    matplotlib.rcdefaults()
    # Set a figure size that doesn't overflow typical browser windows
    matplotlib.rcParams['figure.figsize'] = (5.5, 4.5)

    if code is not None:
        exec(code)
    else:
        try:
            runfile(fullpath)
        except:
            traceback.print_exc()
            s = ("Exception running plot %s" % fullpath)
            warnings.warn(s)
            return 0

    fig_managers = _pylab_helpers.Gcf.get_all_fig_managers()
    for i, figman in enumerate(fig_managers):
        for format, dpi in formats:
            if len(fig_managers) == 1:
                outname = basename
            else:
                outname = "%s_%02d" % (basename, i)
            outpath = os.path.join(outdir, '%s.%s' % (outname, format))
            try:
                figman.canvas.figure.savefig(outpath, dpi=dpi)
            except:
                s = cbook.exception_to_str("Exception running plot %s" % fullpath)
                warnings.warn(s)
                return 0

            write_char('*')

    return len(fig_managers)

def plot_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    """
    Handle the plot directive.
    """
    formats = setup.config.plot_formats
    if type(formats) == str:
        formats = eval(formats)

    # The user may provide a filename *or* Python code content, but not both
    if len(arguments) == 1:
        reference = directives.uri(arguments[0])
        basedir, fname = os.path.split(reference)
        basename, ext = os.path.splitext(fname)
        basedir = relpath(basedir, setup.app.builder.srcdir)
        if len(content):
            raise ValueError("plot directive may not specify both a filename and inline content")
        content = None
    else:
        basedir = "inline"
        content = '\n'.join(content)
        # Since we don't have a filename, use a hash based on the content
        reference = basename = md5(content).hexdigest()[-10:]
        fname = None

    # Get the directory of the rst file, and determine the relative
    # path from the resulting html file to the plot_directive links
    # (linkdir).  This relative path is used for html links *only*,
    # and not the embedded image.  That is given an absolute path to
    # the temporary directory, and then sphinx moves the file to
    # build/html/_images for us later.
    rstdir, rstfile = os.path.split(state_machine.document.attributes['source'])
    outdir = os.path.join('plot_directive', basedir)
    reldir = relpath(setup.confdir, rstdir)
    linkdir = os.path.join(reldir, outdir)

    # tmpdir is where we build all the output files.  This way the
    # plots won't have to be redone when generating latex after html.

    # Prior to Sphinx 0.6, absolute image paths were treated as
    # relative to the root of the filesystem.  0.6 and after, they are
    # treated as relative to the root of the documentation tree.  We need
    # to support both methods here.
    tmpdir = os.path.join('build', outdir)
    tmpdir = os.path.abspath(tmpdir)
    if sphinx_version < (0, 6):
        prefix = ''
    else:
        prefix = '/'
    if not os.path.exists(tmpdir):
        cbook.mkdirs(tmpdir)

    # destdir is the directory within the output to store files
    # that we'll be linking to -- not the embedded images.
    destdir = os.path.abspath(os.path.join(setup.app.builder.outdir, outdir))
    if not os.path.exists(destdir):
        cbook.mkdirs(destdir)

    # Generate the figures, and return the number of them
    num_figs = makefig(reference, content, tmpdir)

    if options.has_key('include-source'):
        if content is None:
            lines = [
                '.. include:: %s' % os.path.join(setup.app.builder.srcdir, reference),
                '    :literal:']
            if options.has_key('encoding'):
                lines.append('    :encoding: %s' % options['encoding'])
                del options['encoding']
        else:
            lines = ['::', ''] + ['    %s'%row.rstrip() for row in content.split('\n')]
        lines.append('')
        del options['include-source']
    else:
        lines = []

    if num_figs > 0:
        options = ['      :%s: %s' % (key, val) for key, val in
                   options.items()]
        options = "\n".join(options)
        if fname is not None:
            shutil.copyfile(reference, os.path.join(destdir, fname))

        for i in range(num_figs):
            if num_figs == 1:
                outname = basename
            else:
                outname = "%s_%02d" % (basename, i)

            # Copy the linked-to files to the destination within the build tree,
            # and add a link for them
            links = []
            if fname is not None:
                links.append('`source code <%(linkdir)s/%(basename)s.py>`__')
            for format in formats[1:]:
                shutil.copyfile(os.path.join(tmpdir, outname + "." + format),
                                os.path.join(destdir, outname + "." + format))
                links.append('`%s <%s/%s.%s>`__' % (format, linkdir, outname, format))
            links = ', '.join(links) % locals()

            # Output the resulting reST
            lines.extend((template % locals()).split('\n'))
    else:
        lines.extend((exception_template % locals()).split('\n'))

    if len(lines):
        state_machine.insert_input(
            lines, state_machine.input_lines.source(0))

    return []

def mark_plot_labels(app, document):
    """
    To make plots referenceable, we need to move the reference from
    the "htmlonly" (or "latexonly") node to the actual figure node
    itself.
    """
    for name, explicit in document.nametypes.iteritems():
        if not explicit:
            continue
        labelid = document.nameids[name]
        if labelid is None:
            continue
        node = document.ids[labelid]
        if node.tagname in ('html_only', 'latex_only'):
            for n in node:
                if n.tagname == 'figure':
                    sectname = name
                    for c in n:
                        if c.tagname == 'caption':
                            sectname = c.astext()
                            break

                    node['ids'].remove(labelid)
                    node['names'].remove(name)
                    n['ids'].append(labelid)
                    n['names'].append(name)
                    document.settings.env.labels[name] = \
                        document.settings.env.docname, labelid, sectname
                    break

def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir

    app.add_directive('plot', plot_directive, True, (0, 1, 0), **options)
    app.add_config_value(
        'plot_formats',
        ['png', 'hires.png', 'pdf'],
        True)

    app.connect('doctree-read', mark_plot_labels)

########NEW FILE########
__FILENAME__ = suites
def fib(n):
    "return nth term of Fibonacci sequence"
    a, b = 0, 1
    i = 0
    while i<n:
        a, b = b, a+b
        i += 1 
    return b

def linear_recurrence(n, (a,b)=(2,0), (u0, u1)=(1,1)):
    """return nth term of the sequence defined by the
    linear recurrence
        u(n+2) = a*u(n+1) + b*u(n)"""
    i = 0
    u, v = u0, u1
    while i<n:
        w = a*v + b*u
        u, v = v, w
        i +=1
    return w
        
        

########NEW FILE########
__FILENAME__ = testing
"""
A file to ease a bit the testing framework
"""
import doctest
doctest.set_unittest_reportflags(doctest.REPORT_NDIFF)


########NEW FILE########
