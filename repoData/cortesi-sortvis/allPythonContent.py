__FILENAME__ = bitonicsort
import math
ASCENDING = True
DESCENDING = False

def compare(lst, i, j, dir):
    if dir == (lst[i] > lst[j]):
        lst[i], lst[j] = lst[j], lst[i]
        lst.log()


def merge(lst, lo, n, dir):
    if n > 1: 
        k = n/2
        for i in range(lo, lo+k):
            compare(lst, i, i+k, dir)
        merge(lst, lo, k, dir)
        merge(lst, lo+k, k, dir)


def _bitonicsort(lst, lo, n, dir):
    if n > 1:
        k = n/2
        _bitonicsort(lst, lo, k, ASCENDING)
        _bitonicsort(lst, lo+k, k, DESCENDING)
        merge(lst, lo, n, dir)


def bitonicsort(lst):
    # Length of list must be 2**x, where x is an integer.
    assert math.modf(math.log(len(lst), 2))[0] == 0
    _bitonicsort(lst, 0, len(lst), ASCENDING)


########NEW FILE########
__FILENAME__ = bubblesort

def bubblesort(lst):
    bound = len(lst)-1
    while 1:
        t = 0
        for j in range(bound):
            if lst[j] > lst[j+1]:
                lst[j], lst[j+1] = lst[j+1], lst[j]
                lst.log()
                t = j
        if t == 0:
            break
        bound = t

########NEW FILE########
__FILENAME__ = cocktailsort

def cocktailsort(lst):
    begin, end = 0, len(lst) - 1
    finished = False
    while not finished:
        finished = True
        for i in xrange(begin, end):
            if lst[i] > lst[i + 1]:
                lst[i], lst[i + 1] = lst[i + 1], lst[i]
                lst.log()
                finished = False
        if finished:
            break
        finished = True
        end -= 1
        for i in reversed(xrange(begin, end)):
            if lst[i] > lst[i + 1]:
                lst[i], lst[i + 1] = lst[i + 1], lst[i]
                lst.log()
                finished = False
        begin += 1


########NEW FILE########
__FILENAME__ = combsort

def combsort(lst):
    gap = len(lst)
    swaps = False
    while 1:
        gap = int(gap / 1.25)
        swaps = False
        for i in xrange(len(lst) - gap):
            if lst[i] > lst[i + gap]:
                lst[i], lst[i + gap] = lst[i + gap], lst[i]
                lst.log()
                swaps = True
        if not swaps and gap <= 1:
            break


########NEW FILE########
__FILENAME__ = cyclesort


def cyclesort(lst):
    for i in range(len(lst)):
        if i != lst[i]:
            n = i
            while 1: 
                tmp = lst[int(n)]
                if n != i:
                    lst[int(n)] = last_value
                    lst.log()
                else:
                    lst[int(n)] = None
                    lst.log()
                last_value = tmp
                n = last_value
                if n == i:
                    lst[int(n)] = last_value
                    lst.log()
                    break



########NEW FILE########
__FILENAME__ = gnomesort

def gnomesort(lst):
    i = 0
    while i < len(lst):
        if i == 0 or lst[i] >= lst[i - 1]:
            i += 1
        else:
            lst[i], lst[i - 1] = lst[i - 1], lst[i]
            lst.log()
            i -= 1



########NEW FILE########
__FILENAME__ = heapsort

def sift(lst, start, count):
    root = start
    while (root * 2) + 1 < count:
        child = (root * 2) + 1
        if child < (count-1) and lst[child] < lst[child+1]:
            child += 1
        if lst[root] < lst[child]:
            lst[root], lst[child] = lst[child], lst[root]
            lst.log()
            root = child
        else:
            return

def heapsort(lst):
    start = (len(lst)/2)-1
    end = len(lst)-1
    while start >= 0:
        sift(lst, start, len(lst))
        start -= 1
    while end > 0:
        lst[end], lst[0] = lst[0], lst[end]
        lst.log()
        sift(lst, 0, end)
        end -= 1

########NEW FILE########
__FILENAME__ = insertionsort

def insertionsort(lst):
    for i in range(1, len(lst)):
        for j in range(i):
            if lst[i] < lst[j]:
                x = lst.pop(i)
                lst.insert(j, x)
                lst.log()

########NEW FILE########
__FILENAME__ = mergesort

def mergesort(lst, left=0, right=None):
    if right is None:
        right = len(lst) - 1
    if left >= right:
        return
    middle = (left + right) // 2
    mergesort(lst, left, middle)
    mergesort(lst, middle + 1, right)
    i, end_i, j = left, middle, middle + 1
    while i <= end_i and j <= right:
        if lst[i] < lst[j]:
            i += 1
            continue
        lst[i], lst[i+1:j+1] = lst[j], lst[i:j]
        lst.log()
        i, end_i, j = i + 1, end_i + 1, j + 1

########NEW FILE########
__FILENAME__ = oddevensort

def oddevensort(lst, nloops=2):
    finished = False
    while not finished:
        finished = True
        for n in xrange(nloops):
            for i in xrange(n, len(lst) - 1, nloops):
                if lst[i] > lst[i + 1]:
                    lst[i], lst[i + 1] = lst[i + 1], lst[i]
                    lst.log()
                    finished = False



########NEW FILE########
__FILENAME__ = quicksort

def quicksort(lst, left=0, right=None):
    if right is None:
        right = len(lst) - 1
    l = left
    r = right
    if l <= r:
        mid = lst[(left+right)/2]
        while l <= r:
            while l <= right and lst[l] < mid:
                l += 1
            while r > left and lst[r] > mid:
                r -= 1
            if l <= r:
                lst[l], lst[r] = lst[r], lst[l]
                if l != r:
                    lst.log()
                l+=1
                r-=1
        if left < r:
            quicksort(lst, left, r)
        if l < right:
            quicksort(lst, l, right)


########NEW FILE########
__FILENAME__ = radixsort
from itertools import chain

def radixsort(lst):
    is_sorted = lambda l: all([a < b for a, b in zip(l[:-1], l[1:])])
    shift = 1
    zeroes = []
    ones = []
    while not is_sorted(lst.lst):
        orig = lst.lst[:]
        while len(orig) != 0:
            # take an item out of the list
            item = orig.pop(0)
            # put it in the right bucket
            if (item.i & shift) == 0:
                zeroes.append(item)
            else:
                ones.append(item)
            # copy the items back into the main list
            for j, item in enumerate(chain(zeroes, orig, ones)):
                lst[j] = item
            # for a more simple graph, comment out the line below
            lst.log()
            #
            if is_sorted(lst):
                return
        lst.log()
        shift = shift << 1
        zeroes[:] = []
        ones[:] = []

########NEW FILE########
__FILENAME__ = selectionsort

def selectionsort(lst):
    for j in range(len(lst)-1, -1, -1):
        m = lst.index(max(lst[:j+1]))  # No, this is not efficient ;)
        lst[m], lst[j] = lst[j], lst[m]
        if m != j:
            lst.log()


########NEW FILE########
__FILENAME__ = shellsort

def shellsort(lst):
    t = [5, 3, 1]
    for h in t:
        for j in range(h, len(lst)):
            i = j - h
            r = lst[j]
            flag = 0
            while i > -1:
                if r < lst[i]:
                    flag = 1
                    lst[i+h], lst[i] = lst[i], lst[i+h]
                    i -= h
                    lst.log()
                else:
                    break
            lst[i+h] = r


########NEW FILE########
__FILENAME__ = smoothsort

# Possibly replace with a generator that produces Leonardo numbers?
# That would be of limited utility since this is all of them up to 31 bits.
LP = [ 1, 1, 3, 5, 9, 15, 25, 41, 67, 109, 177, 287, 465, 753, 1219, 1973,
       3193, 5167, 8361, 13529, 21891, 35421, 57313, 92735, 150049, 242785,
       392835, 635621, 1028457, 1664079, 2692537, 4356617, 7049155,
       11405773, 18454929, 29860703, 48315633, 78176337, 126491971,
       204668309, 331160281, 535828591, 866988873 ]

# Solution for determining number of trailing zeroes of a number's binary representation.
# Taken from http://www.0xe3.com/text/ntz/ComputingTrailingZerosHOWTO.html
# I don't much like the magic numbers, but they really are magic.
MultiplyDeBruijnBitPosition = [ 0,  1, 28,  2, 29, 14, 24, 3,
                                30, 22, 20, 15, 25, 17,  4, 8,
                                31, 27, 13, 23, 21, 19, 16, 7,
                                26, 12, 18,  6, 11,  5, 10, 9]

def trailingzeroes(v):
    return MultiplyDeBruijnBitPosition[(((v & -v) * 0x077CB531L) >> 27) & 0b11111]


def sift(lst, pshift, head):
    while pshift > 1:
        rt = head - 1
        lf = head - 1 - LP[pshift - 2]
        if lst[head] >= lst[lf] and lst[head] >= lst[rt]:
            break
        if lst[lf] >= lst[rt]:
            lst[head], lst[lf] = lst[lf], lst[head]
            head = lf
            pshift -= 1
        else:
            lst[head], lst[rt] = lst[rt], lst[head]
            head = rt
            pshift -= 2
        lst.log()


def trinkle(lst, p, pshift, head, trusty):
    while p != 1:
        stepson = head - LP[pshift]
        if lst[stepson] <= lst[head]:
            break
        if not trusty and pshift > 1:
            rt = head - 1
            lf = head - 1 - LP[pshift - 2]
            if lst[rt] >= lst[stepson] or lst[lf] >= lst[stepson]:
                break
        lst[head], lst[stepson] = lst[stepson], lst[head]
        lst.log()
        head = stepson
        trail = trailingzeroes(p & ~1)
        p >>= trail
        pshift += trail
        trusty = False

    if not trusty:
        sift(lst, pshift, head)


def smoothsort(lst):
    p = 1
    pshift = 1
    head = 0
    while head < len(lst) - 1:
        if (p & 3) == 3:
            sift(lst, pshift, head)
            p >>= 2
            pshift += 2
        else:
            if LP[pshift - 1] >= len(lst) - 1 - head:
                trinkle(lst, p, pshift, head, False)
            else:
                sift(lst, pshift, head)

            if pshift == 1:
                p <<= 1
                pshift -= 1
            else:
                p <<= pshift - 1
                pshift = 1

        p |= 1
        head += 1
    trinkle(lst, p, pshift, head, False)
    while pshift != 1 or p != 1:
        if pshift <= 1:
            trail = trailingzeroes(p & ~1)
            p >>= trail
            pshift += trail
        else:
            p <<= 2
            p ^= 7
            pshift -= 2

            trinkle(lst, p >> 1, pshift + 1, head - LP[pshift] - 1, True)
            trinkle(lst, p, pshift, head - 1, True)
        head -= 1

########NEW FILE########
__FILENAME__ = stoogesort

def stoogesort(lst, i=0, j=None):
    if j is None:
        j = len(lst) - 1
    if lst[j] < lst[i]:
        lst[i], lst[j] = lst[j], lst[i]
        lst.log()
    if j - i > 1:
        t = (j - i + 1) // 3
        stoogesort(lst, i, j - t)
        stoogesort(lst, i + t, j)
        stoogesort(lst, i, j - t)



########NEW FILE########
__FILENAME__ = timsort

class TimBreak(Exception): pass


class TimWrapper:
    list = None
    comparisons = 0
    limit = 0
    def __init__(self, n):
        self.n = n

    def __cmp__(self, other):
        if TimWrapper.comparisons > TimWrapper.limit:
            raise TimBreak
        TimWrapper.comparisons += 1
        return cmp(self.n, other.n)

    def __getattr__(self, attr):
        return getattr(self.n, attr)
    

def timsort(lst):
    lst.wrap(TimWrapper)
    TimWrapper.list = lst
    prev = [i.n for i in lst]
    while 1:
        TimWrapper.comparisons = 0
        TimWrapper.limit += 1
        lst.reset()
        try:
            lst.sort()
        except TimBreak:
            if prev != [i.n for i in lst]:
                lst.log()
                prev = [i.n for i in lst]
        else:
            lst.log()
            break

########NEW FILE########
__FILENAME__ = graph
import cairo
import math

try:
    import scurve
except ImportError:
    scurve = None


def rgb(x):
    if isinstance(x, tuple) or isinstance(x, list):
        return (x[0]/255.0, x[1]/255.0, x[2]/255.0)
    elif isinstance(x, basestring):
        if len(x) != 6:
            raise ValueError("RGB specifier must be 6 characters long.")
        return rgb([int(i, 16) for i in (x[0:2], x[2:4], x[4:6])])
    raise ValueError("Invalid RGB specifier.")


class ColourGradient:
    """
        A straight line drawn through the colour cube from a start value to an
        end value.
    """
    name = "gradient"
    def __init__(self, start, end):
        self.start, self.end = start, end

    def colour(self, x, l):
        scale = x/float(l)
        parts = list(self.start)
        for i, v in enumerate(parts):
            parts[i] = parts[i] + (self.start[i]-self.end[i])*scale*-1
        return tuple(parts)


class ColourHilbert:
    """
        A Hilbert-order traversal of the colour cube. 
    """
    def __init__(self):
        self.size = None
        self.curve = None

    def findSize(self, n):
        """
            Return the smallest Hilbert curve size larger than n. 
        """
        for i in range(100):
            s = 2**(3*i)
            if s >= n:
                return s
        raise ValueError("Number of elements impossibly large.")

    def colour(self, x, n):
        if n != self.size:
            self.curve = scurve.fromSize("hilbert", 3, self.findSize(n))
        d = float(self.curve.dimensions()[0])
        # Scale X to sample evenly from the curve, if the list length isn't
        # an exact match for the Hilbert curve size.
        x = x*int(len(self.curve)/float(n))
        return tuple([i/d for i in self.curve.point(x)])
                
    
class NiceCtx(cairo.Context):
    defaultBorderColour = rgb((0x7d, 0x7d, 0x7d))
    def stroke_border(self, border):
        src = self.get_source()
        width = self.get_line_width()
        self.set_source_rgba(*self.defaultBorderColour)
        self.stroke_preserve()
        self.set_source(src)
        self.set_line_width(width - (border * 2))
        self.stroke()
        self.set_line_width(width)


class Canvas:
    def __init__(self, width, height, background):
        self.width, self.height = width, height
        self.background = background
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.set_background(background)

    def ctx(self):
        return NiceCtx(self.surface)

    def set_background(self, colour):
        c = self.ctx()
        c.set_source_rgb(*colour)
        c.rectangle(0, 0, self.width, self.height)
        c.fill()
        c.stroke()

    def save(self, fname, rotate):
        """
            Save the image to a file. If rotate is true, rotate by 90 degrees.
        """
        if rotate:
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.height, self.width)
            ctx = cairo.Context(surf)
            ctx.translate(self.height*0.5, self.width*0.5)
            ctx.rotate(math.pi/2)
            ctx.translate(-self.width*0.5, -self.height*0.5)
            ctx.set_source_surface(self.surface)
            ctx.paint()
        else:
            surf = self.surface
        surf.write_to_png(fname)
            

class _PathDrawer:
    TITLEGAP = 5
    def __init__(self, csource):
        """
            csource: A colour source
        """
        self.csource = csource

    def lineCoords(self, positions, length, edge=0.02):
        """
            Returns a list of proportional (x, y) co-ordinates for a given list
            of Y-offsets. Each co-ordinate value is a floating point number
            between 0 and 1, inclusive.
        """
        xscale = (1.0-(2*edge))/(len(positions)-1)
        yscale = 1.0/length
        coords = []
        coords.append((0, positions[0]*yscale))
        for i, v in enumerate(positions):
            coords.append(((xscale * i) + edge, v*yscale))
        coords.append((1, v*yscale))
        return coords

    def drawPaths(self, canvas, linewidth, borderwidth, width, height, lst):
        ctx = canvas.ctx()
        ctx.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(linewidth)
        for elem in lst:
            for i in self.lineCoords(elem.path, len(lst)):
                ctx.line_to(width * i[0], linewidth + height * i[1])
            c = self.csource.colour(elem.i, len(lst)) + (1,)
            ctx.set_source_rgba(*c)
            if borderwidth:
                ctx.stroke_border(borderwidth)
            else:
                ctx.stroke()

    def drawPixels(self, canvas, lst, unmoved):
        ctx = canvas.ctx()
        for elem in lst:
            ctx.set_source_rgb(*self.csource.colour(elem.i, len(lst)))
            moved = unmoved
            for x, y in enumerate(elem.path):
                if y != elem.path[0]:
                    moved = True
                if moved:
                    ctx.rectangle(x, y, 1, 1)
                    ctx.fill()

    def drawTitle(self, canvas, title, xpos, ypos, size, colour, font="Sans"):
        ctx = canvas.ctx()
        ctx.select_font_face(font)
        ctx.set_font_size(size)
        ctx.set_source_rgb(*colour)
        ctx.move_to(xpos, ypos)
        ctx.text_path(title)
        ctx.fill()


class Weave(_PathDrawer):
    def __init__(self, csource, width, height, titleHeight, titleColour, background,
                       rotate, linewidth, borderwidth):
        _PathDrawer.__init__(self, csource)
        self.width, self.height, self.titleHeight = width, height, titleHeight
        self.titleColour = titleColour
        self.background = background
        self.rotate, self.linewidth, self.borderwidth = rotate, linewidth, borderwidth

    def getColor(self, x, n):
        v = 1 - (float(x)/n*0.7)
        return (v, v, v)

    def draw(self, lst, title, fname):
        c = Canvas(self.width, self.height, self.background)
        # Clearer when drawn in this order
        lst.reverse()
        if title:
            self.drawPaths(
                c,
                self.linewidth,
                self.borderwidth,
                self.width,
                self.height-self.titleHeight,
                lst
            )
        else:
            self.drawPaths(c, self.linewidth, self.borderwidth, self.width, self.height, lst)
        if title:
            self.drawTitle(
                c,
                title,
                5,
                self.height-self.TITLEGAP,
                self.titleHeight-self.TITLEGAP,
                self.titleColour
            )
        c.save(fname, self.rotate)


class Dense(_PathDrawer):
    def __init__(self, csource, titleHeight, titleColour, background, unmoved):
        _PathDrawer.__init__(self, csource)
        self.titleColour = titleColour
        self.titleHeight = titleHeight
        self.background = background
        self.unmoved = unmoved

    def draw(self, lst, title, fname):
        height = len(lst)
        width = len(lst[0].path)
        c = Canvas(width, height + (self.titleHeight if title else 0), self.background)
        # Clearer when drawn in this order
        lst.reverse()
        self.drawPixels(c, lst, not self.unmoved)
        if title:
            self.drawTitle(
                c,
                title,
                5,
                height+self.titleHeight-self.TITLEGAP,
                self.titleHeight-self.TITLEGAP,
                self.titleColour
            )
        c.save(fname, False)



########NEW FILE########
__FILENAME__ = sortable

class Sortable:
    def __init__(self, tracklist, i):
        self.tracklist, self.i = tracklist, i
        self.path = []

    def __cmp__(self, other):
        """ Counts each comparison between two elements and redirects
            to the underlying __cmp__ method of the i's wrapped in this."""
        self.tracklist.total_comparisons += 1
        try:
            return cmp(self.i, other.i)
        except AttributeError:
            return cmp(self.i, other)

    def __int__(self):
        return self.i

    def __repr__(self):
        return str(self.i)


class TrackList:
    """
        A list-like object that logs the positions of its elements every time
        the log() method is called.
    """
    def __init__(self, itms):
        self.lst = [Sortable(self, i) for i in itms]
        self.start = self.lst[:]
        self.total_comparisons = 0
        self.log()

    def wrap(self, wrapper):
        """ Allows an additional wrapping of the inner list with the given
            wrapper. See algos.timsort as an example. """
        self.lst = [wrapper(i) for i in self.lst]
        self.start = self.lst[:]

    def reset(self):
        self.total_comparisons = 0
        self.lst = self.start[:]

    def __getattr__(self, attr):
        """ Redirecting every lookup on this object that didn't succeed to
            the internal list (e.g., iterating over self iterates over list)."""
        return getattr(self.lst, attr)
    
    def log(self):
        for i, v in enumerate(self):
            if v is not None:
                v.path.append(i)


class DummySortable(object):
    def __init__(self, i):
        self.i = i
        self.path = []

    def __int__(self):
        return self.i



def read_paths(fp):
    """
        Reads a sorting history from a filepointer, and returns a list of Sortables.

        The sorting history is specified as a set of newline-terminated lists,
        with each list consisting of space-separated numbers.
    """
    sortables = {}
    for i in fp.readlines():
        n = i.split()
        if not sortables:
            for j in n:
                j = int(j)
                sortables[j] = DummySortable(j)
        for offset, j in enumerate(n):
            sortables[int(j)].path.append(offset)
    return sortables.values()


########NEW FILE########
__FILENAME__ = test_graph
import os.path
from libsortvis import graph, sortable, algos
import libpry


OUTDIR = "tmp"
class _GraphTest(libpry.AutoTree):
    def setUpAll(self):
        if not os.path.exists(OUTDIR):
            os.mkdir(OUTDIR)


class uWeave(_GraphTest):
    def test_lineCoords(self):
        csource = graph.ColourGradient((1, 1, 1), (0, 0, 0))
        p = graph.Weave(
            csource, 100, 100, 20, graph.rgb("ffffff"), graph.rgb("000000"),
            False, 6, 1
        )
        r = p.lineCoords([1, 2, 3, 4, 5], 5, 0.02)
        assert r[-1] == (1, 1)
        # Lead-in
        assert r[0][1] == r[1][1]
        assert r[0][0] != r[1][0]
        # Lead-out
        assert r[-1][1] == r[-2][1]
        assert r[-1][0] != r[-2][0]

    def test_draw(self):
        csource = graph.ColourGradient((1, 1, 1), (0, 0, 0))
        p = graph.Weave(
            csource, 100, 100, 20,
            graph.rgb("ffffff"),
            graph.rgb("000000"),
            False, 6, 1
        )
        l = range(10)
        l.reverse()
        track = sortable.TrackList(l)
        a = algos.insertionsort.insertionsort(track)
        p.draw(track, "test", os.path.join(OUTDIR, "test_grayscale.png"))


class uDense(_GraphTest):
    def test_draw(self):
        csource = graph.ColourGradient((1, 1, 1), (0, 0, 0))
        p = graph.Dense(csource, 20, graph.rgb("ffffff"), graph.rgb("000000"), False)
        l = range(8)
        l.reverse()
        track = sortable.TrackList(l)
        a = algos.insertionsort.insertionsort(track)
        p.draw(track, "test", os.path.join(OUTDIR, "test_weave.png"))


class uUtils(libpry.AutoTree):
    def test_rgb(self):
        assert graph.rgb((255, 255, 255)) == (1, 1, 1)
        assert graph.rgb("ffffff") == (1, 1, 1)
        assert graph.rgb("000000") == (0, 0, 0)


class uColourSource(libpry.AutoTree):
    def test_gradient(self):
        g = graph.ColourGradient((1, 1, 1), (0, 0, 0))
        assert g.colour(0, 10) == (1.0, 1.0, 1.0)
        assert g.colour(10, 10) == (0, 0, 0)
        assert g.colour(5, 10) == (0.5, 0.5, 0.5)

        g = graph.ColourGradient((0, 0, 0), (1, 1, 1))
        assert g.colour(0, 10) == (0, 0, 0)
        assert g.colour(10, 10) == (1.0, 1.0, 1.0)
        assert g.colour(5, 10) == (0.5, 0.5, 0.5)

    def test_hilbert(self):
        g = graph.ColourHilbert()
        assert g.colour(50, 200)
        assert g.colour(50, 200)



tests = [
    uWeave(),
    uDense(),
    uUtils(),
    uColourSource()
]

########NEW FILE########
__FILENAME__ = test_sortable
import random
import libpry
import cStringIO
from libsortvis import sortable, algos


class uTrackList(libpry.AutoTree):
    def test_simple(self):
        l = [1, 2, 3]
        t = sortable.TrackList(l)
        assert t[0].path == [0]
        t[0], t[1] = t[1], t[0]
        t.log()
        assert t[1].path == [0, 1]


class uAlgorithms(libpry.AutoTree):
    # This value needs to be a power of 2, because bitonic sort requires it.
    N = 2**5
    def test_bitonicsort(self):
        algos.bitonicsort.bitonicsort(sortable.TrackList(range(2**1)))
        algos.bitonicsort.bitonicsort(sortable.TrackList(range(2**3)))
        libpry.raises(AssertionError, algos.bitonicsort.bitonicsort, range(3))
        libpry.raises(AssertionError, algos.bitonicsort.bitonicsort, range(9))

    def test_all(self):
        seqs = [
            range(self.N),
            list(reversed(range(self.N))),
        ]

        l = range(self.N)
        l[0], l[-1] = l[-1], l[0]
        seqs.append(l)

        for i in range(5):
            l = range(self.N)
            random.shuffle(l)
            seqs.append(l)

        for seq in seqs:
            for (k, v) in algos.algorithms.items():
                l = sortable.TrackList(seq)
                v(l)
                if not [x.i for x in l] == range(self.N):
                    print l
                    raise AssertionError("%s failed to sort."%k)


class uReadPaths(libpry.AutoTree):
    def test_read_paths(self):
        s = cStringIO.StringIO(
            "1 2 3\n"
            "2 1 3\n"
        )
        r = sortable.read_paths(s)
        for i in r:
            if i.i == 1:
                assert i.path == [0, 1]
            elif i.i == 2:
                assert i.path == [1, 0]
            elif i.i == 3:
                assert i.path == [2, 2]


tests = [
    uTrackList(),
    uAlgorithms(),
    uReadPaths()
]


########NEW FILE########
