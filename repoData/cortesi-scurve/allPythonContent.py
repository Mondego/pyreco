__FILENAME__ = draw
import math
import cairo

class Canvas:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

    def ctx(self):
        return cairo.Context(self.surface)

    def background(self, r, g, b, a=1):
        c = self.ctx()
        c.set_source_rgba(r, g, b, a)
        c.rectangle(0, 0, self.width, self.height)
        c.fill()
        c.stroke()

    def save(self, fname):
        self.surface.write_to_png(fname)


def parseColor(c):
    """
        Parse an HTML-style color specification
    """
    if len(c) == 6:
        r = int(c[0:2], 16)/255.0
        g = int(c[2:4], 16)/255.0
        b = int(c[4:6], 16)/255.0
        return [r, g, b]
    elif len(c) == 3:
        return c


class Demo:
    """
        Draws a 2d curve within a specified square.
    """
    PAD = 5
    def __init__(self, curve, size, color, background, dotsize, *marks):
        self.curve = curve
        self.size, self.color, self.dotsize = size, color, dotsize
        self.background = background
        self.c = Canvas(size+self.PAD*2, size+self.PAD*2)
        self.c.background(*parseColor(self.background))
        self.ctx = self.c.ctx()
        self.ctx.set_line_width(1)
        # Assuming all dimension sizes are equal
        self.length = self.curve.dimensions()[0]
        self.marks = set(marks)
        self.scale = float(size)/(self.length-1)

    def func(self, i, o):
        return xy(i, o)

    def _coordinates(self):
        for x, y in self.curve:
            x *= self.scale
            y *= self.scale
            assert x <= self.size
            assert y <= self.size
            yield x+self.PAD, y+self.PAD

    def draw(self):
        self.ctx.move_to(self.PAD, self.PAD)
        off = 0
        lst = list(self._coordinates())
        for x, y in lst:
            if off in self.marks:
                self.ctx.set_source_rgba(1, 0, 0, 0.8)
                self.ctx.arc(x, y, self.dotsize*2, 0, math.pi*2)
                self.ctx.fill()
            else:
                self.ctx.set_source_rgba(1, 0, 0, 0.5)
                self.ctx.arc(x, y, self.dotsize, 0, math.pi*2)
                self.ctx.fill()
            off += 1

        self.ctx.set_source_rgb(*parseColor(self.color))
        self.ctx.move_to(self.PAD, self.PAD)
        for x, y in lst:
            self.ctx.line_to(x, y)
        self.ctx.stroke()

    def save(self, fname):
        self.c.save(fname)



class Curve:
    def __init__(self, curve, size, background="FFFFFF", color="000000"):
        """
            size:  X and Y dimensions of image.
        """
        self.curve, self.size = curve, size
        self.background = parseColor(background)
        self.color = color

        self.order = 1
        while (2**(2*(self.order+1)) <= len(curve)):
            self.order += 1

        self.c = Canvas(self.size, self.size)

        bkg = self.background + [1]
        self.c.background(*bkg)
        self.ctx = self.c.ctx()
        self.ctx.set_source_rgb(*parseColor(color))
        self.ctx.set_antialias(False)

        # Effective granularity
        self.bucket = len(curve)/((2**self.order)**2)

    def pixel(self, n, color=None):
        if color and color != self.color:
            self.ctx.set_source_rgb(*parseColor(color))
            self.color = color
        x, y = self.curve.point(int(n/float(self.bucket)))
        self.ctx.rectangle(x, y, 1, 1)
        self.ctx.fill()

    def pixelRange(self, start, end):
        x = start - start%self.bucket
        while 1:
            self.pixel(x)
            if x >= end:
                break
            x += self.bucket

    def save(self, fname):
        self.c.save(fname)



class Swatch:
    def __init__(self, curve, colorwidth, height):
        """
            Color swatches from the RGB color cube.

            curve: A curve with dimension 3.
            colorwidth: Width of an individual color. Image width will be
            len(curve)*colorwidth.
            height: Height of the image
        """
        self.curve, self.colorwidth, self.height = curve, colorwidth, height
        self.c = Canvas(len(self.curve) * colorwidth, self.height)
        self.ctx = self.c.ctx()
        self.ctx.set_antialias(False)

    def save(self, fname):
        d = float(self.curve.dimensions()[0])
        offset = 0
        for r, g, b in self.curve:
            self.ctx.set_source_rgb(
                r/d, g/d, b/d
            )
            self.ctx.rectangle(offset, 0, self.colorwidth, self.height)
            self.ctx.fill()
            offset += self.colorwidth
        self.c.save(fname)


########NEW FILE########
__FILENAME__ = graycurve
import math
import utils

class GrayCurve:
    def __init__(self, dimension, bits):
        """
            dimension: Number of dimensions
            bits: The number of bits per co-ordinate. Total number of points is
            2**(bits*dimension).
        """
        self.dimension, self.bits = dimension, bits

    @classmethod
    def fromSize(self, dimension, size):
        """
            size: total number of points in the curve.
        """
        x = math.log(size, 2)
        bits = x/dimension
        if not bits == int(bits):
            raise ValueError("Size does not fit a square Gray curve.")
        return GrayCurve(dimension, int(bits))

    def __len__(self):
        return 2**(self.bits*self.dimension)

    def __getitem__(self, idx):
        if idx >= len(self):
            raise IndexError
        return self.point(idx)

    def dimensions(self):
        """
            Size of this curve in each dimension.
        """
        return [2**self.bits]*self.dimension

    def index(self, p):
        idx = 0
        iwidth = self.bits * self.dimension
        for i in range(iwidth):
            bitoff = self.bits-(i/self.dimension)-1
            poff = self.dimension-(i%self.dimension)-1
            b = utils.bitrange(p[poff], self.bits, bitoff, bitoff+1) << i
            idx |= b
        return utils.igraycode(idx)

    def point(self, idx):
        idx = utils.graycode(idx)
        p = [0]*self.dimension
        iwidth = self.bits * self.dimension
        for i in range(iwidth):
            b = utils.bitrange(idx, iwidth, i, i+1) << (iwidth-i-1)/self.dimension
            p[i%self.dimension] |= b
        return p

########NEW FILE########
__FILENAME__ = hcurve
import math

class Hcurve:
    """
        The H-curve, described in "Towards Optimal Locality in Mesh-Indexings"
        by R. Niedermeier , K. Reinhardt  and P. Sanders.

        This code is a straight transliteration of the implementation by
        Reinhard, found here:

            http://www2-fs.informatik.uni-tuebingen.de/~reinhard/hcurve.html
    """
    def __init__(self, dimension, size):
        """
            dimension: Number of dimensions
            size: The size in each dimension
        """
        if dimension != 2:
            raise ValueError("Invalid dimension - we can only draw the H-curve in 2 dimensions.")
        x = math.log(size, 2)
        if not float(x) == int(x):
            raise ValueError("Invalid size - has to be a power of 2.")
        self.dimension, self.size = int(dimension), int(size)

    @classmethod
    def fromSize(self, dimension, size):
        """
            size: total number of points in the curve.
        """
        x = math.ceil(math.pow(size, 1/float(dimension)))
        if not x**dimension == size:
            raise ValueError("Size does not fit a square Hcurve.")
        return Hcurve(dimension, int(x))

    def __len__(self):
        return self.size**self.dimension

    def dimensions(self):
        """
            Size of this curve in each dimension.
        """
        return [self.size]*self.dimension

    def __getitem__(self, idx):
        if idx >= len(self):
            raise IndexError
        return self.point(idx)

    def cor(self, d, i, n):
        # Size of this sub-triangle
        tsize = n**self.dimension/2
        if i < 0:
            return 0
        elif i < d + 1:
            return d
        elif i >= tsize:
            return n - self.cor(d, i - tsize, n) - 1
        else:
            # Which of the four sub-triangles of this triangle are we in?
            x = 4*i/tsize
            f = 1 if i+1 == d else 0
            if x == 0: return self.cor(d, i, n/2) 
            if x == 1: return self.cor(d, tsize/2 - 1 - i, n/2) - 0
            if x == 2: return n/2 - self.cor(d, 3 * tsize/4 - 1 - i, n/2) - 1
            if x == 3: return n/2 + self.cor(d, i - 3 * tsize/4, n/2) - 0

    def xcor(self, i, n):
        # Size of this sub-triangle
        tsize = n**self.dimension/2
        if i < 1:
            return 0
        elif i >= tsize:
            return n - self.xcor(i - tsize, n) - 1
        else:
            # Which of the four sub-triangles of this triangle are we in?
            x = 4*i/tsize
            f = 0
            if x == 0: return self.xcor(i, n/2)
            if x == 1: return self.xcor(tsize/2 - 1 - i, n/2)
            if x == 2: return n/2 - self.xcor(3 * tsize/4 - 1 - i, n/2) - 1
            if x == 3: return n/2 + self.xcor(i - 3 * tsize/4, n/2)
                
    def ycor(self, i, n):
        tsize = n**self.dimension/2
        if i < 2:
            return i
        elif i >= tsize:
            return n - self.ycor(i - tsize, n) - 1
        else:
            x = 4*i/tsize
            if x == 0: return self.ycor(i, n/2)
            if x == 1: return n - self.ycor(tsize/2 - 1 - i, n/2) - 1
            if x == 2: return n/2 + self.ycor(3 * tsize/4 - 1 - i, n/2)
            if x == 3: return n/2 + self.ycor(i - 3 * tsize/4, n/2)

    def point(self, idx):
        return [self.cor(0, idx, self.size), self.ycor(idx, self.size)]


########NEW FILE########
__FILENAME__ = hilbert
import utils, math


def transform(entry, direction, width, x):
    assert x < 2**width
    assert entry < 2**width
    return utils.rrot((x^entry), direction+1, width)


def itransform(entry, direction, width, x):
    """
        Inverse transform - we simply reverse the operations in transform.
    """
    assert x < 2**width
    assert entry < 2**width
    return utils.lrot(x, direction+1, width)^entry
    # There is an error in the Hamilton paper's formulation of the inverse
    # transform in Lemma 2.12. The correct restatement as a transform is as follows:
    #return transform(rrot(entry, direction+1, width), width-direction-2, width, x)


def direction(x, n):
    assert x < 2**n
    if x == 0:
        return 0
    elif x%2 == 0:
        return utils.tsb(x-1, n)%n
    else:
        return utils.tsb(x, n)%n


def entry(x):
    if x == 0:
        return 0
    else:
        return utils.graycode(2*((x-1)/2))


def hilbert_point(dimension, order, h):
    """
        Convert an index on the Hilbert curve of the specified dimension and
        order to a set of point coordinates.
    """
    #    The bit widths in this function are:
    #        p[*]  - order
    #        h     - order*dimension
    #        l     - dimension
    #        e     - dimension
    hwidth = order*dimension
    e, d = 0, 0
    p = [0]*dimension
    for i in range(order):
        w = utils.bitrange(h, hwidth, i*dimension, i*dimension+dimension)
        l = utils.graycode(w)
        l = itransform(e, d, dimension, l)
        for j in range(dimension):
            b = utils.bitrange(l, dimension, j, j+1)
            p[j] = utils.setbit(p[j], order, i, b)
        e = e ^ utils.lrot(entry(w), d+1, dimension)
        d = (d + direction(w, dimension) + 1)%dimension
    return p


def hilbert_index(dimension, order, p):
    h, e, d = 0, 0, 0
    for i in range(order):
        l = 0
        for x in range(dimension):
            b = utils.bitrange(p[dimension-x-1], order, i, i+1)
            l |= b<<x
        l = transform(e, d, dimension, l)
        w = utils.igraycode(l)
        e = e ^ utils.lrot(entry(w), d+1, dimension)
        d = (d + direction(w, dimension) + 1)%dimension
        h = (h<<dimension)|w
    return h


class Hilbert:
    def __init__(self, dimension, order):
        self.dimension, self.order = dimension, order

    @classmethod
    def fromSize(self, dimension, size):
        """
            Size is the total number of points in the curve.
        """
        x = math.log(size, 2)
        if not float(x)/dimension == int(x)/dimension:
            raise ValueError("Size does not fit Hilbert curve of dimension %s."%dimension)
        return Hilbert(dimension, int(x/dimension))

    def __len__(self):
        return 2**(self.dimension*self.order)

    def __getitem__(self, idx):
        if idx >= len(self):
            raise IndexError
        return self.point(idx)

    def dimensions(self):
        """
            Size of this curve in each dimension.
        """
        return [int(math.ceil(len(self)**(1/float(self.dimension))))]*self.dimension

    def index(self, p):
        return hilbert_index(self.dimension, self.order, p)

    def point(self, idx):
        return hilbert_point(self.dimension, self.order, idx)


########NEW FILE########
__FILENAME__ = natural
import math

class Natural:
    """
        A natural order traversal of the points in a cube. Each point is
        simply considered a digit in a number.
    """
    def __init__(self, dimension, size):
        """
            dimension: Number of dimensions
            size: The size in each dimension
        """
        self.dimension, self.size = int(dimension), int(size)

    @classmethod
    def fromSize(self, dimension, size):
        """
            size: total number of points in the curve.
        """
        x = math.ceil(math.pow(size, 1/float(dimension)))
        if not x**dimension == size:
            raise ValueError("Size does not fit a square curve.")
        return Natural(dimension, math.ceil(x))

    def __len__(self):
        return self.size**self.dimension

    def __getitem__(self, idx):
        if idx >= len(self):
            raise IndexError
        return self.point(idx)

    def dimensions(self):
        """
            Size of this curve in each dimension.
        """
        return [self.size]*self.dimension

    def index(self, p):
        idx = 0
        for power, i in enumerate(p):
            power = self.dimension-power-1
            idx += i * (self.size**power)
        return idx

    def point(self, idx):
        p = []
        for i in range(self.dimension-1, -1, -1):
            v = idx/(self.size**i)
            if i > 0:
                idx = idx - (self.size**i)*v
            p.append(v)
        return p

########NEW FILE########
__FILENAME__ = progress
#!/usr/local/bin/python
import sys, time, math, datetime

class Inplace:
    def __init__(self, title="", stream=sys.stderr):
        self.stream, self.title = stream, title
        self.last = 0

    def tick(self, s):
        if not self.stream:
            return
        w = "\r%s%s"%(self.title, s)
        self.last = len(w)
        self.stream.write(w)
        self.stream.flush()

    def inject(self, txt):
        self.stream.write("\n")
        self.clear()
        self.stream.write("%s\n"%txt)
        self.stream.flush()

    def clear(self):
        if not self.stream:
            return
        spaces = " "*self.last
        self.stream.write("\r%s\r"%spaces)


class Progress(Inplace):
    bookend = "|"
    done = "-"
    current = ">"
    todo = " "
    def __init__(self, target, title="", width=40, stream=sys.stderr):
        Inplace.__init__(self, title, stream=stream)
        self.width, self.target = width, target
        self.prev = -1
        self.startTime = None
        self.window = None

    def tick(self, val):
        if not self.stream:
            return
        if not self.startTime:
            self.startTime = datetime.datetime.now()
        pp = val/float(self.target)
        progress = int(pp * self.width)
        t = datetime.datetime.now() - self.startTime
        runsecs = t.days*86400 + t.seconds + t.microseconds/1000000.0
        if pp == 0:
            eta = "?:??:??"
        else:
            togo = runsecs * (1 - pp)/pp
            eta = datetime.timedelta(seconds = int(togo))
        if pp > self.prev:
            self.prev = pp
            l = self.done * progress
            r = self.todo * (self.width - progress)
            now = time.time()
            s = "%s%s%s%s%s %s" % (
                self.bookend, l,
                self.current,
                r, self.bookend, eta
            )
            Inplace.tick(self, s)

    def set_target(self, t):
        self.target = t

    def restoreTerm(self):
        if self.window:
            #begin nocover
            curses.echo()
            curses.nocbreak()
            curses.endwin()
            self.window = None
            #end nocover

    def clear(self):
        Inplace.clear(self)
        self.restoreTerm()

    def __del__(self):
        self.restoreTerm()

    def full(self):
        self.tick(self.target)


class Dummy:
    def __init__(self, *args, **kwargs): pass
    def tick(self, *args, **kwargs): pass
    def restoreTerm(self, *args, **kwargs): pass
    def clear(self, *args, **kwargs): pass
    def full(self, *args, **kwargs): pass
    def set_target(self, *args, **kwargs): pass


########NEW FILE########
__FILENAME__ = utils
"""
    A lot of these functions are written for clarity rather than speed. We'll
    fix that in time.
"""
import math

def graycode(x):
    return x^(x>>1)


def igraycode(x):
    """
        Inverse gray code.
    """
    if x == 0:
        return x
    m = int(math.ceil(math.log(x, 2)))+1
    i, j = x, 1
    while j < m:
        i = i ^ (x>>j)
        j += 1
    return i


def bits(n, width):
    """
        Convert n to a list of bits of length width.
    """
    assert n < 2**width
    bin = []
    for i in range(width):
        bin.insert(0, 1 if n&(1<<i) else 0)
    return bin


def bits2int(bits):
    """
        Convert a list of bits to an integer.
    """
    n = 0
    for p, i in enumerate(reversed(bits)):
        n += i*2**p
    return n


def rrot(x, i, width):
    """
        Right bit-rotation.

        width: the bit width of x.
    """
    assert x < 2**width
    i = i%width
    x = (x>>i) | (x<<width-i)
    return x&(2**width-1)


def lrot(x, i, width):
    """
        Left bit-rotation.

        width: the bit width of x.
    """
    assert x < 2**width
    i = i%width
    x = (x<<i) | (x>>width-i)
    return x&(2**width-1)


def tsb(x, width):
    """
        Trailing set bits.
    """
    assert x < 2**width
    i = 0
    while x&1 and i <= width:
        x = x >> 1
        i += 1
    return i


def setbit(x, w, i, b):
    """
        Sets bit i in an integer x of width w to b.
        b must be 1 or 0
    """
    assert b in [1, 0]
    assert i < w
    if b:
        return x | 2**(w-i-1)
    else:
        return x & ~2**(w-i-1)


def bitrange(x, width, start, end):
    """
        Extract a bit range as an integer.
        (start, end) is inclusive lower bound, exclusive upper bound.
    """
    return x >> (width-end) & ((2**(end-start))-1)


def entropy(data, blocksize, offset, symbols=256):
    """
        Returns local byte entropy for a location in a file.
    """
    if len(data) < blocksize:
        raise ValueError, "Data length must be larger than block size."
    if offset < blocksize/2:
        start = 0
    elif offset > len(data)-blocksize/2:
        start = len(data)-blocksize/2
    else:
        start = offset-blocksize/2
    hist = {}
    for i in data[start:start+blocksize]:
        hist[i] = hist.get(i, 0) + 1
    base = min(blocksize, symbols)
    entropy = 0
    for i in hist.values():
        p = i/float(blocksize)
        # If blocksize < 256, the number of possible byte values is restricted.
        # In that case, we adjust the log base to make sure we get a value
        # between 0 and 1.
        entropy += (p * math.log(p, base))
    return -entropy

########NEW FILE########
__FILENAME__ = zigzag
import math

class ZigZag:
    """
        An n-dimensional zig-zag curve - it snakes through the n-cube, with
        each point differing from the previous point by exactly one. Not
        useful, but it's a good counterpoint to other space-filling curves.
    """
    def __init__(self, dimension, size):
        """
            dimension: Number of dimensions
            size: The size in each dimension
        """
        self.dimension, self.size = int(dimension), int(size)

    @classmethod
    def fromSize(self, dimension, size):
        """
            size: total number of points in the curve.
        """
        x = math.ceil(math.pow(size, 1/float(dimension)))
        if not x**dimension == size:
            raise ValueError("Size does not fit a square ZigZag curve.")
        return ZigZag(dimension, int(x))

    def __len__(self):
        return self.size**self.dimension

    def __getitem__(self, idx):
        if idx >= len(self):
            raise IndexError
        return self.point(idx)

    def dimensions(self):
        """
            Size of this curve in each dimension.
        """
        return [self.size]*self.dimension

    def index(self, p):
        idx = 0
        flip = False
        for power, i in enumerate(reversed(list(p))):
            power = self.dimension-power-1
            if flip:
                fi = self.size-i-1
            else:
                fi = i
            v = fi * (self.size**power)
            idx += v
            if i%2:
                flip = not flip
        return idx

    def point(self, idx):
        p = []
        flip = False
        for i in range(self.dimension-1, -1, -1):
            v = idx/(self.size**i)
            if i > 0:
                idx = idx - (self.size**i)*v
            if flip:
                v = self.size-1-v
            p.append(v)
            if v%2:
                flip = not flip
        return reversed(p)

########NEW FILE########
__FILENAME__ = zorder
import math
import utils


class ZOrder:
    """
        The Z-order curve is generated by interleaving the bits of an offset.
    """
    def __init__(self, dimension, bits):
        """
            dimension: Number of dimensions
            bits: The number of bits per co-ordinate. Total number of points is
            2**(bits*dimension).
        """
        self.dimension, self.bits = dimension, bits

    @classmethod
    def fromSize(self, dimension, size):
        """
            size: total number of points in the curve.
        """
        x = math.log(size, 2)
        bits = x/dimension
        if not bits == int(bits):
            raise ValueError("Size does not fit a square ZOrder curve.")
        return ZOrder(dimension, int(bits))

    def __len__(self):
        return 2**(self.bits*self.dimension)

    def __getitem__(self, idx):
        if idx >= len(self):
            raise IndexError
        return self.point(idx)

    def dimensions(self):
        """
            Size of this curve in each dimension.
        """
        return [2**self.bits]*self.dimension

    def index(self, p):
        p.reverse()
        idx = 0
        iwidth = self.bits * self.dimension
        for i in range(iwidth):
            bitoff = self.bits-(i/self.dimension)-1
            poff = self.dimension-(i%self.dimension)-1
            b = utils.bitrange(p[poff], self.bits, bitoff, bitoff+1) << i
            idx |= b
        return idx

    def point(self, idx):
        p = [0]*self.dimension
        iwidth = self.bits * self.dimension
        for i in range(iwidth):
            b = utils.bitrange(idx, iwidth, i, i+1) << (iwidth-i-1)/self.dimension
            p[i%self.dimension] |= b
        p.reverse()
        return p

########NEW FILE########
__FILENAME__ = test_hcurve
from scurve import hcurve


class TestHcurve:
    def test_xycor(self):
        n = 4
        h = hcurve.Hcurve(2, n)
        for i in range(n*n):
            assert h.xcor(i, n) < n
            assert h.ycor(i, n) < n

    def test_fromSize(self):
        h = hcurve.Hcurve.fromSize(2, 16)
        assert h.size == 4
        assert len(h) == 16

    def test_traversal(self):
        h = hcurve.Hcurve.fromSize(2, 16)
        assert [i for i in h]

########NEW FILE########
__FILENAME__ = test_hilbert
import math
from scurve import hilbert, utils
import tutils


class TestFunctions:
    def ispow2(self, i):
        """
            Is i a power of two?
        """
        l = math.log(i, 2)
        return l == int(l)
    
    def is_hilbertcube(self, lst):
        """
            Does this list visit every vertex on the n-dimensional unit cube
            once, with each value differing from the previous value by exactly
            one bit?
        """
        lst = lst[:]
        assert len(lst) == len(set(lst))
        assert self.ispow2(len(lst))
        # We also want to test that start and end positions are adjacent
        lst.append(lst[0])
        prev = 0
        for i in lst:
            if prev > 0:
                assert self.ispow2(prev^i)
            prev = i

    def transform_pair(self, a, entry, direction, width):
        r = transform(entry, direction, width, a)
        assert a == itransform(entry, direction, width, r)
    
    def test_transform(self):
        for width in range(2, 5):
            g = [utils.graycode(i) for i in range(2**width)]
            # Sanity: the gray sequence should be a Hilbert cube too
            self.is_hilbertcube(g)

            for e in range(2**width):
                for d in range(width):
                    x = [hilbert.transform(e, d, width, i) for i in g]

                    # From Lemma 2.11 of Hamilton
                    assert hilbert.transform(e, d, width, e) == 0
                    assert hilbert.itransform(e, d, width, 0) == e

                    # The base gray code starts at 0, and has a direction of width-1:
                    if e == 0 and d == width-1:
                        assert x == g
                    self.is_hilbertcube(x)
                    assert [hilbert.itransform(e, d, width, i) for i in x] == g

        # These values are from the example on p 18 of Hamilton
        assert hilbert.transform(0, 1, 2, 3) == 3
        assert hilbert.transform(3, 0, 2, 2) == 2
        assert hilbert.transform(3, 0, 2, 1) == 1

    def test_hilbert_point(self):
        for n in [2, 3, 4]:
            m = 3
            for i in range(2**(n*m)):
                v = hilbert.hilbert_point(n, m, i)
                assert i == hilbert.hilbert_index(n, m, v)

    def test_hilbert_index(self):
        # From the example on p 18 of Hamilton
        assert hilbert.hilbert_index(2, 3, [5, 6]) == 45

    def test_direction(self):
        assert hilbert.direction(2, 2) == 1
        assert hilbert.direction(3, 2) == 0
        assert hilbert.direction(1, 2) == 1

    def test_entry(self):
        assert hilbert.entry(2) == 0
        assert hilbert.entry(3) == 3
        assert hilbert.entry(1) == 0


class TestHilbert:
    def test_index(self):
        h = hilbert.Hilbert(2, 3)
        assert h.index(h.point(4)) ==  4

    def test_len(self):
        assert len(hilbert.Hilbert(2, 1)) == 4
        assert len(hilbert.Hilbert(2, 2)) == 16
        assert len(hilbert.Hilbert(3, 1)) == 8

    def test_getitem(self):
        assert len(list(hilbert.Hilbert(2, 1))) == 4

    def test_fromSize(self):
        h = hilbert.Hilbert.fromSize(2, 256*256)
        assert h.dimensions() == [256, 256]
        h = hilbert.Hilbert(3, 1)
        h2 = hilbert.Hilbert.fromSize(3, len(h))
        assert h.dimension == h2.dimension
        assert h.order == h2.order
        tutils.raises(ValueError, hilbert.Hilbert.fromSize, 3, 3)

    def ttest_bench(self):
        h = hilbert.Hilbert(2, 7)
        for i in h:
            h.index(i)



########NEW FILE########
__FILENAME__ = test_natural
from scurve import natural, utils
import tutils


class TestNatural:
    def test_point(self):
        tutils.is_complete(natural.Natural(1, 1))
        tutils.is_complete(natural.Natural(1, 3))
        tutils.is_complete(natural.Natural(2, 3))
        tutils.is_complete(natural.Natural(3, 3))
        tutils.is_complete(natural.Natural(3, 12))
        tutils.is_complete(natural.Natural(4, 3))
        tutils.is_complete(natural.Natural(4, 4))

    def test_index(self):
        tutils.symmetry(natural.Natural(1, 1))
        tutils.symmetry(natural.Natural(2, 3))
        tutils.symmetry(natural.Natural(2, 4))
        tutils.symmetry(natural.Natural(3, 2))
        tutils.symmetry(natural.Natural(3, 12))
        tutils.symmetry(natural.Natural(4, 4))

    def test_fromSize(self):
        z = natural.Natural(2, 3)
        z2 = natural.Natural.fromSize(2, len(z))
        assert z.dimension == z2.dimension
        assert z.size == z2.size

        z = natural.Natural(3, 256)
        z2 = natural.Natural.fromSize(3, len(z))
        assert z.dimension == z2.dimension
        assert z.size == z2.size



########NEW FILE########
__FILENAME__ = test_progress
import scurve.progress as progress
import StringIO

class TestInplace:
    def test_basic(self):
        s = StringIO.StringIO()
        c = progress.Inplace(stream=s)
        assert s.getvalue() ==  ''
        c.tick(10)
        assert s.getvalue() ==  '\r10'
        c.tick(10000)
        assert s.getvalue() ==  '\r10\r10000'
        c.inject("foo")
        c.clear()

    def test_nostream(self):
        c = progress.Inplace(stream=None)
        c.tick(10)
        c.clear()


class TestProgress:
    def test_basic(self):
        s = StringIO.StringIO()
        p = progress.Progress(100, stream=s)
        p.tick(25)
        assert p.prev == 0.25
        p.tick(50)
        assert p.prev == 0.5
        p.full()
        assert p.prev == 1.0

########NEW FILE########
__FILENAME__ = test_utils
from scurve import utils
import tutils

class TestFunctions:
    def test_bits2int(self):
        assert utils.bits2int([0, 0, 1]) == 1
        assert utils.bits2int([0, 1, 1]) == 3
        assert utils.bits2int([1, 1, 1]) == 7
        assert utils.bits2int([1, 0, 1]) == 5

    def test_graycode(self):
        assert utils.graycode(3) == 2
        assert utils.graycode(4) == 6

    def test_igraycode(self):
        for i in range(10):
            assert utils.igraycode(utils.graycode(i)) == i
            assert utils.graycode(utils.igraycode(i)) == i

    def rotpair(self, left, right, i, width):
        assert utils.rrot(left, i, width) == right
        assert utils.lrot(right, i, width) == left
        assert utils.lrot(left, i, width) == utils.rrot(left, width-i, width)

    def test_rot(self):
        self.rotpair(2, 1, 1, 2)
        self.rotpair(1, 2, 1, 2)
        self.rotpair(0, 0, 1, 2)
        self.rotpair(3, 3, 1, 2)
        self.rotpair(4, 2, 1, 3)
        self.rotpair(4, 1, 2, 3)
        self.rotpair(1, 2, 2, 3)
        self.rotpair(1, 1, 3, 3)

    def test_tsb(self):
        assert utils.tsb(1, 5) == 1
        assert utils.tsb(2, 5) == 0
        assert utils.tsb(3, 5) == 2
        assert utils.tsb((2**5)-1, 5) == 5
        assert utils.tsb(0, 5) == 0

    def test_setbit(self):
        assert utils.setbit(0, 3, 0, 1) == 4
        assert utils.setbit(4, 3, 2, 1) == 5
        assert utils.setbit(4, 3, 0, 0) == 0

    def test_bitrange(self):
        def checkbit(i, width, start, end, expected):
            e = utils.bitrange(i, width, start, end)
            assert e == expected
            assert e == utils.bits2int(utils.bits(i, width)[start:end])

        checkbit(1, 5, 4, 5, 1)
        checkbit(2, 5, 4, 5, 0)
        checkbit(2, 5, 3, 5, 2)
        checkbit(2, 5, 3, 4, 1)
        checkbit(3, 5, 3, 5, 3)
        checkbit(3, 5, 0, 5, 3)
        checkbit(4, 5, 2, 3, 1)
        checkbit(4, 5, 2, 4, 2)
        checkbit(4, 5, 2, 2, 0)

    def test_entropy(self):
        tutils.raises(ValueError, utils.entropy, "foo", 64, 0)
        assert utils.entropy("a"*64, 64, 1) == 0
        d = "".join([chr(i) for i in range(256)])
        assert utils.entropy(d, 64, 1) == 1


########NEW FILE########
__FILENAME__ = test_zigzag
from scurve import zigzag, utils
import tutils


class TestZigZag:
    def test_point(self):
        tutils.is_traversal(zigzag.ZigZag(1, 1))
        tutils.is_traversal(zigzag.ZigZag(1, 3))
        tutils.is_traversal(zigzag.ZigZag(2, 3))
        tutils.is_traversal(zigzag.ZigZag(3, 3))
        tutils.is_traversal(zigzag.ZigZag(3, 12))
        tutils.is_traversal(zigzag.ZigZag(4, 3))
        tutils.is_traversal(zigzag.ZigZag(4, 4))

    def test_index(self):
        tutils.symmetry(zigzag.ZigZag(1, 1))
        tutils.symmetry(zigzag.ZigZag(2, 3))
        tutils.symmetry(zigzag.ZigZag(2, 4))
        tutils.symmetry(zigzag.ZigZag(3, 2))
        tutils.symmetry(zigzag.ZigZag(3, 12))
        tutils.symmetry(zigzag.ZigZag(4, 4))

    def test_fromSize(self):
        z = zigzag.ZigZag(2, 3)
        z2 = zigzag.ZigZag.fromSize(2, len(z))
        assert z.dimension == z2.dimension
        assert z.size == z2.size

        z = zigzag.ZigZag(3, 256)
        z2 = zigzag.ZigZag.fromSize(3, len(z))
        assert z.dimension == z2.dimension
        assert z.size == z2.size


########NEW FILE########
__FILENAME__ = test_zorder
from scurve import zorder, utils
import tutils


class TestZOrder:
    def test_dimensions(self):
        z = zorder.ZOrder(2, 2)
        assert z.dimensions()[0] == (2**2)

    def test_point(self):
        z = zorder.ZOrder(2, 2)
        assert z.point(utils.bits2int([0, 1, 0, 1])) == [3, 0]
        assert z.point(utils.bits2int([0, 0, 0, 0])) == [0, 0]
        assert z.point(utils.bits2int([1, 0, 0, 0])) == [0, 2]
        assert z.point(utils.bits2int([1, 0, 1, 0])) == [0, 3]
        assert z.point(utils.bits2int([1, 1, 1, 1])) == [3, 3]

        z = zorder.ZOrder(2, 3)
        assert z.point(utils.bits2int([1, 1, 1, 1, 1, 1])) == [7, 7]

    def test_index(self):
        z = zorder.ZOrder(2, 3)
        tutils.symmetry(zorder.ZOrder(1, 1))
        tutils.symmetry(zorder.ZOrder(2, 3))
        tutils.symmetry(zorder.ZOrder(2, 4))
        tutils.symmetry(zorder.ZOrder(3, 2))
        tutils.symmetry(zorder.ZOrder(4, 3))

    def test_fromSize(self):
        z = zorder.ZOrder(2, 3)
        z2 = zorder.ZOrder.fromSize(2, len(z))
        assert z.dimension == z2.dimension
        assert z.bits == z2.bits


########NEW FILE########
__FILENAME__ = tutils
"""
    Some common test routines.
"""

def raises(exc, obj, *args, **kwargs):
    """
        Assert that a callable raises a specified exception.

        :exc An exception class or a string. If a class, assert that an
        exception of this type is raised. If a string, assert that the string
        occurs in the string representation of the exception, based on a
        case-insenstivie match.

        :obj A callable object.

        :args Arguments to be passsed to the callable.

        :kwargs Arguments to be passed to the callable.
    """
    try:
        apply(obj, args, kwargs)
    except Exception, v:
        if isinstance(exc, basestring):
            if exc.lower() in str(v).lower():
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s"%(
                        repr(str(exc)), v
                    )
                )
        else:
            if isinstance(v, exc):
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s %s"%(
                        exc.__name__, v.__class__.__name__, str(v)
                    )
                )
    raise AssertionError("No exception raised.")


def is_complete(lst):
    """
        Does this list of points visit every vertex on the n-dimensional
        cube once?
    """
    lst = [tuple(i) for i in lst]
    assert len(lst) == len(set(lst))


def is_traversal(lst):
    """
        Does this list of points visit every vertex on the n-dimensional
        cube once, with each value differing from the previous value by
        exactly one bit?
    """
    lst = [tuple(i) for i in lst]
    assert len(lst) == len(set(lst))
    prev = None
    for i in lst:
        if prev is not None:
            diff = 0
            for x, y in zip(i, prev):
                if x != y:
                    if abs(x-y) != 1:
                        raise AssertionError("%s and %s differ by more than 1."%(i, prev))
                    diff += 1
            assert diff == 1
        prev = i


def symmetry(c):
    l1 = list(c)
    l2 = [c.index(i) for i in l1]
    assert l2 == range(len(c))





########NEW FILE########
