__FILENAME__ = examples
from scipy.misc import lena
from pylab import imread
from scipy.ndimage import gaussian_filter
from stl_tools import numpy2stl, text2png


"""
Some quick examples
"""

A = lena()  # load Lena image, shrink in half
A = gaussian_filter(A, 1)  # smoothing
numpy2stl(A, "examples/Lena.stl", scale=0.1, solid=False)

A = 256 * imread("examples/example_data/NASA.png")
A = A[:, :, 2] + 1.0*A[:,:, 0] # Compose RGBA channels to give depth
A = gaussian_filter(A, 1)  # smoothing
numpy2stl(A, "examples/NASA.stl", scale=0.05, mask_val=5., solid=True)

A = 256 * imread("examples/example_data/openmdao.png")
A =  A[:, :, 0] + 1.*A[:,:, 3] # Compose some elements from RGBA to give depth
A = gaussian_filter(A, 2)  # smoothing
numpy2stl(A, "examples/OpenMDAO-logo.stl",
          scale=0.05, mask_val=1., min_thickness_percent=0.005, solid=True)

text = ("$\oint_{\Gamma} (A\, dx + B\, dy) = \iint_{U} \left(\\frac{\partial "
        "B}{\partial x} - \\frac{\partial A}{\partial y}\\right)\ dxdy$ \n\n "
        "$\\frac{\partial \\rho}{\partial t} + \\frac{\partial}{\partial x_j}"
        "\left[ \\rho u_j \\right] = 0$")
# save png
text2png(text, "examples/Greens-Theorem_Navier-Stokes", fontsize=50)
# read from rendered png
A = 256 * imread("examples/Greens-Theorem_Navier-Stokes.png")
A = A.mean(axis=2)  # grayscale projection
A = gaussian_filter(A.max() - A, 1.0)
numpy2stl(A, "examples/Greens-Theorem_Navier-Stokes.stl", scale=0.15,
                                                         mask_val=5.)

########NEW FILE########
__FILENAME__ = image2stl
from argparse import ArgumentParser

import numpy as np
from numpy2stl import numpy2stl
from pylab import imread
from scipy.ndimage import gaussian_filter


_float_args = ["scale", "mask_val", "max_width", "max_depth", "max_height"]
_bool_args = ["ascii", "calc_normals"]


def image2stl():
    """
    Provides a command-line interface to numpy2stl
    """

    parser = ArgumentParser()
    parser.add_argument("f", help='Source image filename')
    parser.add_argument("-o", default="", help='Output filename')

    parser.add_argument("-RGBA_weights", default=[""], nargs=4)
    parser.add_argument("-gaussian_filter", default="")

    float_group = parser.add_argument_group('float inputs:')
    for varname in _float_args:
        float_group.add_argument(''.join(["-", varname]), default="")

    bool_group = parser.add_argument_group('boolean inputs')
    for varname in _bool_args:
        bool_group.add_argument(''.join(["-", varname]), default="")

    args = vars(parser.parse_args())

    f_args = {f_arg: float(args[f_arg])
              for f_arg in _float_args if args[f_arg]}
    b_args = {b_arg: bool(int(args[b_arg]))
              for b_arg in _bool_args if args[b_arg]}

    kwargs = dict(f_args, **b_args)

    src = args['f']
    fn = args['o']
    if not fn:
        fn = '.'.join([src.split('.')[0], "stl"])

    A = 256. * imread(src)
    L = len(A.shape)
    w = args['RGBA_weights']
    if L > 2:
        if len(w) >= L:
            A = np.sum([float(w[i]) * A[:, :, i]
                       for i in range(A.shape[-1])], axis=0)
        else:
            A = A.mean(axis=2)

    if args['gaussian_filter']:
        A = gaussian_filter(A, float(args['gaussian_filter']))

    numpy2stl(A, fn, **kwargs)

if __name__ == "__main__":
    image2stl()

########NEW FILE########
__FILENAME__ = numpy2stl
import struct
import numpy as np
from itertools import product
try:
    from .cwrapped import tessellate
    c_lib = True
except ImportError:
    c_lib = False

ASCII_FACET = """  facet normal  {face[0]:e}  {face[1]:e}  {face[2]:e}
    outer loop
      vertex    {face[3]:e}  {face[4]:e}  {face[5]:e}
      vertex    {face[6]:e}  {face[7]:e}  {face[8]:e}
      vertex    {face[9]:e}  {face[10]:e}  {face[11]:e}
    endloop
  endfacet"""

BINARY_HEADER = "80sI"
BINARY_FACET = "12fH"


def _build_binary_stl(facets):
    """returns a string of binary binary data for the stl file"""

    lines = [struct.pack(BINARY_HEADER, b'Binary STL Writer', len(facets)), ]
    for facet in facets:
        facet = list(facet)
        facet.append(0)  # need to pad the end with a unsigned short byte
        lines.append(struct.pack(BINARY_FACET, *facet))
    return lines


def _build_ascii_stl(facets):
    """returns a list of ascii lines for the stl file """

    lines = ['solid ffd_geom', ]
    for facet in facets:
        lines.append(ASCII_FACET.format(face=facet))
    lines.append('endsolid ffd_geom')
    return lines


def writeSTL(facets, file_name, ascii=False):
    """writes an ASCII or binary STL file"""

    f = open(file_name, 'wb')
    if ascii:
        lines = _build_ascii_stl(facets)
        lines_ = "\n".join(lines).encode("UTF-8")
        f.write(lines_)
    else:
        data = _build_binary_stl(facets)
        data = b"".join(data)
        f.write(data)

    f.close()


def roll2d(image, shifts):
    return np.roll(np.roll(image, shifts[0], axis=0), shifts[1], axis=1)


def numpy2stl(A, fn, scale=0.1, mask_val=None, ascii=False,
              max_width=235.,
              max_depth=140.,
              max_height=150.,
              solid=False,
              min_thickness_percent=0.1,
              force_python=False):
    """
    Reads a numpy array, and outputs an STL file

    Inputs:
     A (ndarray) -  an 'm' by 'n' 2D numpy array
     fn (string) -  filename to use for STL file

    Optional input:
     scale (float)  -  scales the height (surface) of the
                       resulting STL mesh. Tune to match needs

     mask_val (float) - any element of the inputted array that is less
                        than this value will not be included in the mesh.
                        default renders all vertices (x > -inf for all float x)

     ascii (bool)  -  sets the STL format to ascii or binary (default)

     max_width, max_depth, max_height (floats) - maximum size of the stl
                                                object (in mm). Match this to
                                                the dimensions of a 3D printer
                                                platform
     solid (bool): sets whether to create a solid geometry (with sides and
                    a bottom) or not.
     min_thickness_percent (float) : when creating the solid bottom face, this
                                    multiplier sets the minimum thickness in
                                    the final geometry (shallowest interior
                                    point to bottom face), as a percentage of
                                    the thickness of the model computed up to
                                    that point.
    Returns: (None)
    """

    m, n = A.shape
    if n >= m:
        # rotate to best fit a printing platform
        A = np.rot90(A, k=3)
        m, n = n, m
    A = scale * (A - A.min())

    if not mask_val:
        mask_val = A.min() - 1.

    if c_lib and not force_python:  # try to use c library
        # needed for memoryviews
        A = np.ascontiguousarray(A, dtype=float)

        facets = np.asarray(tessellate(A, mask_val, min_thickness_percent,
                            solid))
        # center on platform
        facets[:, 3::3] += -m / 2
        facets[:, 4::3] += -n / 2

    else:  # use python + numpy
        facets = []
        mask = np.zeros((m, n))
        print("Creating top mesh...")
        for i, k in product(range(m - 1), range(n - 1)):

            this_pt = np.array([i - m / 2., k - n / 2., A[i, k]])
            top_right = np.array([i - m / 2., k + 1 - n / 2., A[i, k + 1]])
            bottom_left = np.array([i + 1. - m / 2., k - n / 2., A[i + 1, k]])
            bottom_right = np.array(
                [i + 1. - m / 2., k + 1 - n / 2., A[i + 1, k + 1]])

            n1, n2 = np.zeros(3), np.zeros(3)

            if (this_pt[-1] > mask_val and top_right[-1] > mask_val and
                    bottom_left[-1] > mask_val):

                facet = np.concatenate([n1, top_right, this_pt, bottom_right])
                mask[i, k] = 1
                mask[i, k + 1] = 1
                mask[i + 1, k] = 1
                facets.append(facet)

            if (this_pt[-1] > mask_val and bottom_right[-1] > mask_val and
                    bottom_left[-1] > mask_val):

                facet = np.concatenate(
                    [n2, bottom_right, this_pt, bottom_left])
                facets.append(facet)
                mask[i, k] = 1
                mask[i + 1, k + 1] = 1
                mask[i + 1, k] = 1
        facets = np.array(facets)

        if solid:
            print("Computed edges...")
            edge_mask = np.sum([roll2d(mask, (i, k))
                               for i, k in product([-1, 0, 1], repeat=2)],
                               axis=0)
            edge_mask[np.where(edge_mask == 9.)] = 0.
            edge_mask[np.where(edge_mask != 0.)] = 1.
            edge_mask[0::m - 1, :] = 1.
            edge_mask[:, 0::n - 1] = 1.
            X, Y = np.where(edge_mask == 1.)
            locs = zip(X - m / 2., Y - n / 2.)

            zvals = facets[:, 5::3]
            zmin, zthickness = zvals.min(), zvals.ptp()

            minval = zmin - min_thickness_percent * zthickness

            bottom = []
            print("Extending edges, creating bottom...")
            for i, facet in enumerate(facets):
                if (facet[3], facet[4]) in locs:
                    facets[i][5] = minval
                if (facet[6], facet[7]) in locs:
                    facets[i][8] = minval
                if (facet[9], facet[10]) in locs:
                    facets[i][11] = minval
                this_bottom = np.concatenate(
                    [facet[:3], facet[6:8], [minval], facet[3:5], [minval],
                     facet[9:11], [minval]])
                bottom.append(this_bottom)

            facets = np.concatenate([facets, bottom])

    xsize = facets[:, 3::3].ptp()
    if xsize > max_width:
        facets = facets * float(max_width) / xsize

    ysize = facets[:, 4::3].ptp()
    if ysize > max_depth:
        facets = facets * float(max_depth) / ysize

    zsize = facets[:, 5::3].ptp()
    if zsize > max_height:
        facets = facets * float(max_height) / zsize

    writeSTL(facets, fn, ascii=ascii)

########NEW FILE########
__FILENAME__ = test_stl
import logging
import os
import unittest
import os
import numpy as np
from stl_tools import text2array, numpy2stl, text2png

"""
Some basic tests for stl_tools
"""

logging.basicConfig(level=logging.DEBUG)


class TestSTL(unittest.TestCase):

    def test_text2png(self):
        """ Tests creation of an image array from a text expression.
        Covers the text2png and text2array functions.
        """

        text2png("TEST", fontsize=1000)
        assert os.path.exists("TEST.png")
        os.remove("TEST.png")

    def test_text2array(self):
        """ Tests creation of an image array from a text expression.
        Covers the text2png and text2array functions.
        """

        A = text2array("TEST", fontsize=1000)
        assert A[np.where(A != 0)].size / float(A.size) > 0.2

    def test_png(self):
        """ Tests creation of an STL from a PNG.
        Covers the numpy2stl function.
        """
        output_name = "OUT_.stl"
        # test ascii output
        A = 100 * np.random.randn(64, 64)
        numpy2stl(A, output_name, scale=0.05, mask_val=3., ascii=True)
        assert os.path.exists(output_name)
        assert os.stat(output_name).st_size > 1e5

        # test binary output
        numpy2stl(A, output_name, scale=0.05, mask_val=3.)
        assert os.path.exists(output_name)
        assert os.stat(output_name).st_size > 1e5
        os.remove(output_name)

    def test_png_force_py(self):
        """ Tests creation of an STL from a PNG.
        Covers the pure-python section of the numpy2stl function.
        """
        output_name = "OUT_.stl"
        # test ascii output
        A = 100 * np.random.randn(64, 64)
        numpy2stl(A, output_name, scale=0.05, mask_val=3., ascii=True,
                  force_python=True)
        assert os.path.exists(output_name)
        assert os.stat(output_name).st_size > 1e5

        # test binary output
        numpy2stl(A, output_name, scale=0.05, mask_val=3.,
                  force_python=True)
        assert os.path.exists(output_name)
        assert os.stat(output_name).st_size > 1e5
        os.remove(output_name)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = text2png
import os
import matplotlib as mpl
mpl.use('Agg', warn=False)
import matplotlib.pyplot as plt


def text2png(text, fn=None, fontsize=100):
    """
    Renders inputted text to a png image using matplotlib.

    Inputs:
     text (string) -  text to render

    Optional input:
     fn (string)  -  filename of png to be outputted.
                     defaults to the entered text

    Returns: (None)
    """

    f = plt.figure(frameon=False)
    ax = f.add_subplot(111)
    plt.text(0.5, 0.5, text,
             horizontalalignment='center',
             verticalalignment='center',
             transform=ax.transAxes,
             fontsize=fontsize)
    ax.set_axis_off()
    ax.autoscale_view(True, True, True)
    if not fn:
        fn = ''.join(e for e in text if e.isalnum())
    f.savefig(fn + '.png', bbox_inches='tight')
    plt.close()


def text2array(text, fontsize=100):
    """
    Renders inputted text, and returns array representation.

    Inputs:
     text (string) -  text to render

    Returns: A (ndarray) - 2D numpy array of rendered text
    """

    text2png(text, fn="_text", fontsize=fontsize)
    A = plt.imread("_text.png")[:, :, :3].mean(axis=2)
    os.remove("_text.png")
    return A.max() - A

########NEW FILE########
