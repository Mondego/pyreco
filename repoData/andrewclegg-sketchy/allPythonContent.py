__FILENAME__ = oldsketchy
#!/usr/bin/env python2.7

# Original sketchy demo by @andrew_clegg, May 2012, public domain.
#
# https://github.com/andrewclegg/sketchy

# See README for background. This will work fine on Python 2.5+, including
# Jython. Jython actually seems slightly faster, for larger datasets at
# least, but tends to use more memory.

import sys
import random
from collections import defaultdict
from itertools import izip, imap

# A few knobs you can tweak...

# Hash size in bits -- higher gives more accurate results, but is more expensive.
size = 32
assert(size <= 32) # Can't go higher than this unless you change or remove ham_dist

# Number of features (columns) in the demo data.
dim = 10

# Number of items (rows) in the demo data.
items = 1000000

# Some random demo data, just dim*items ints from 0-10.
test_data = [[random.randint(0, 10) for i in xrange(0, dim)] for j in xrange(0, items)]

# Size of the similar items neighbourhood for demo purposes (max number of bits different).
ham_neighbourhood = size / 8

# For testing only -- returns the product of the magnitude (length) of two vectors.
def magnitude_prod(vec1, vec2):
    tot1 = 0
    tot2 = 0
    for i in xrange(dim): # Beware global variable. These funcs get hit a lot.
        val1 = vec1[i]
        val2 = vec2[i]
        tot1 += val1**2
        tot2 += val2**2
    return (tot1 * tot2)**0.5

# For testing only -- returns the cosine similarity of two vectors.
def cos_sim(vec1, vec2):
    return dot_product(vec1, vec2) / magnitude_prod(vec1, vec2)

# For testing only -- returns the euclidean distance between two points.
def euc_dist(vec1, vec2):
    tot = 0
    for i in xrange(dim): # Beware global variable. These funcs get hit a lot.
        val = vec1[i] - vec2[i]
        tot += val**2
    return (tot)**0.5

# For testing only -- returns the hamming distance between two bitfields (as numbers).
# It's from here:
# http://stackoverflow.com/questions/109023/best-algorithm-to-count-the-number-of-set-bits-in-a-32-bit-integer#109025
# and I have no idea why it works.
def ham_dist(a, b):
    i = a ^ b
    i = i - ((i >> 1) & 0x55555555)
    i = (i & 0x33333333) + ((i >> 2) & 0x33333333)
    return (((i + (i >> 4) & 0xF0F0F0F) * 0x1010101) & 0xffffffff) >> 24

# In case you need it -- converts a list of 0s and 1s to a number. No sanity checking!
def to_int(bitlist):
    return sum([bit * 2**power for power, bit in enumerate(bitlist)])

################ HERE'S WHERE THE FUN STARTS ################

# Returns the dot product of two vectors.
def dot_product(vec1, vec2):
    tot = 0
    for i in xrange(len(vec1)):
        tot += vec1[i] * vec2[i]
    return tot

# Returns 'size' hyperplanes in a 'dim'-dimensional space.
def make_planes(size, dim):
    return [[random.choice((-1, 1)) for i in xrange(0, dim)]
        for j in xrange(0, size)]

# Calculates the hash for a vector of data, using one bit for each plane.
def lsh(vec, planes):
    dps = [dot_product(vec, plane) for plane in planes]
    return sum([2**i if dps[i] > 0 else 0 for i in xrange(0, len(dps))])

# Generate the required number of planes in a space of the right dimensionality.
planes = make_planes(size, dim)

# Calculate the hash for each row in the demo data.
sketch_table = [(lsh(row, planes), row) for row in test_data]
test_data = None

################# ALL THE REST IS TEST CODE #################

# Actually calculating the hashes (above) is fast compared to all the stuff
# below here for producing metrics. Chop it out and see it fly.

sketch_dict = defaultdict(list)
for (sketch, row) in sketch_table:
    sketch_dict[sketch].append(row)

in_bin_cos_tot = 0
in_bin_cos_cnt = 0
in_bin_euc_tot = 0
in_bin_euc_cnt = 0
singletons = 0

for sketch, rows in sketch_dict.items():
    bin_size = len(rows)
    if bin_size > 1:
        #print 'Bin %d has %d elements' % (sketch, bin_size)
        row0 = rows[0]
        cos = [cos_sim(row0, rows[i]) for i in xrange(1, bin_size)]
        euc = [euc_dist(row0, rows[i]) for i in xrange(1, bin_size)]
        #avg_sim = sum(sims) / len(sims)
        #print 'Average cosine similarity first -> rest = %f' % avg_sim
        in_bin_cos_tot += sum(cos)
        in_bin_cos_cnt += len(cos)
        in_bin_euc_tot += sum(euc)
        in_bin_euc_cnt += len(euc)
    else:
        singletons += 1

neighbourhood_cos_tot = 0
neighbourhood_cos_cnt = 0
neighbourhood_euc_tot = 0
neighbourhood_euc_cnt = 0
global_cos_tot = 0
global_cos_cnt = 0
global_euc_tot = 0
global_euc_cnt = 0

subset = random.sample(sketch_table, min(500, items / 1000))
for sketch1, vec1 in subset:
    for sketch2, vec2 in subset:
        if vec1 is not vec2:
            cos = cos_sim(vec1, vec2)
            global_cos_tot += cos
            global_cos_cnt += 1
            euc = euc_dist(vec1, vec2)
            global_euc_tot += euc
            global_euc_cnt += 1
            ham = ham_dist(sketch1, sketch2)
            if ham_dist(sketch1, sketch2) <= ham_neighbourhood:
                neighbourhood_cos_tot += cos
                neighbourhood_cos_cnt += 1
                neighbourhood_euc_tot += euc
                neighbourhood_euc_cnt += 1

bin_sizes = map(len, sketch_dict.values())
print '%d items in %d bins' % (items, len(sketch_dict.values()))
print 'Largest bin: %d items' % max(bin_sizes)
print 'Smallest bin: %d items' % min(bin_sizes)
print 'Singleton bins: %d' % singletons

if in_bin_cos_cnt > 0:
    print 'Average within-bin first->rest cosine similarity = %f' \
        % (in_bin_cos_tot / in_bin_cos_cnt)
if in_bin_euc_cnt > 0:
    print 'Average within-bin first->rest euclidean distance = %f' \
        % (in_bin_euc_tot / in_bin_euc_cnt)
if neighbourhood_cos_cnt > 0:
    print 'Average neighbourhood cosine similarity = %f (pairs = %d, max hamming = %d)' \
        % (neighbourhood_cos_tot / neighbourhood_cos_cnt, neighbourhood_cos_cnt, ham_neighbourhood)
if neighbourhood_euc_cnt > 0:
    print 'Average neighbourhood euclidean distance = %f (pairs = %d, max hamming = %d)' \
        % (neighbourhood_euc_tot / neighbourhood_euc_cnt, neighbourhood_euc_cnt, ham_neighbourhood)
if global_cos_cnt > 0:
    print 'Average global cosine similarity = %f (pairs = %d)' \
        % (global_cos_tot / global_cos_cnt, global_cos_cnt)
if global_euc_cnt > 0:
    print 'Average global euclidean distance = %f (pairs = %d)' \
        % (global_euc_tot / global_euc_cnt, global_euc_cnt)



########NEW FILE########
__FILENAME__ = sketchy
# Tools for locality-sensitive hashing.
#
# https://github.com/andrewclegg/sketchy
#
# Tested on Jython 2.5.2, should work on cpython 2.5+ except for the
# Hamming distance methods which need bit() from 2.6. Feel free to
# add your own retro versions. Haven't tested it on Python 3 yet.

import random
import sys
from array import array # Consider some sort of bitfield instead?


# Kludge around the function decorator that Pig injects, with a dummy.
if 'outputSchema' not in globals():
    def outputSchema(x):
        return lambda(y): y


planes = None

""" Create 'size' planes in a 'dim'-dimensional space, with a new random
    number generator using 'seed'. """
def make_planes(size, dim, seed):
    random.seed(seed)
    p = []
    for i in xrange(size):
        p.append(array('b', (random.choice((-1, 1)) for i in xrange(0, dim))))
    return p

""" Calculate cosine similarity of two sparse vectors. """
def sparse_cos_sim(sv1, sv2):
    mag_prod = sparse_magnitude(sv1) * sparse_magnitude(sv2)
    if mag_prod == 0:
        return 0
    return sparse_dot_product(sv1, sv2) / mag_prod

""" Calculate dot product of two sparse vectors. """
def sparse_dot_product(sv1, sv2):
    d1 = dict(sv1)
    d2 = dict(sv2)
    tot = 0
    for key in set(d1.keys()).intersection(set(d2.keys())):
        tot += d1[key] * d2[key]
    return tot

""" Calculate magnitude of a sparse vector. """
def sparse_magnitude(sv):
    return sum(v**2 for (a, v) in sv)**0.5

""" Calculate dot product of a sparse vector 'sv' against a dense vector 'dv'.
    The sparse vector format is described below. No bounds checking is done,
    so make sure it doesn't exceed the size of 'dv'. """
def mixed_dot_product(sv, dv):
    tot = 0
    for (idx, val) in sv:
        tot += val * dv[idx]
    return tot

""" Calculates the Random Projection hash for a sparse vector 'sv' against a
    set of random planes defined by the other variables, using one bit for each
    plane. The vector should pe provided as a bag of (dimension, value) tuples.
    Only numeric values are supported, so you need to map words, categories etc.
    yourself first. """
@outputSchema('lsh:long') # TODO make this dynamic based on size
def sparse_random_projection(sv, size, dim, seed):
    # Create the planes if they don't already exist in this process
    global planes
    if planes is None:
        planes = make_planes(size, dim, seed)
    dps = [mixed_dot_product(sv, plane) for plane in planes]
    return sum([2**i if dps[i] > 0 else 0 for i in xrange(0, len(dps))])




if 'Java' in sys.version:
    import java.lang.Integer as Integer
    import java.lang.Long as Long
    # TODO hamming8 and hamming16
    def hamming32(i1, i2):
        return Integer.bitCount(i1^i2)
    def hamming64(l1, l2):
        return Long.bitCount(l1^l2)
else:
    def hamming8(i1, i2):
        return bin(i1^i2).count('1')
    hamming16 = hamming8
    hamming32 = hamming8
    hamming64 = hamming8


########NEW FILE########
__FILENAME__ = sketchytest
import unittest
import random
from array import array
import sketchy


def random_sparse_vector(dim, lbound, ubound):
    set_count = random.randint(0, dim - 1)
    set_idxs = random.sample(xrange(dim), set_count)
    sv = []
    for i in set_idxs:
        sv.append((i, random.randint(lbound, ubound)))
    return sv


class TestSketchy(unittest.TestCase):
    
    def test_make_planes(self):
        size = 32
        dim = 10
        seed = 23
        planes = sketchy.make_planes(size, dim, seed)

        # For checking that results are consistent
        planes2 = sketchy.make_planes(size, dim, seed)

        self.assertEqual(size, len(planes))
        for i in xrange(len(planes)):
            plane = planes[i]
            self.assertEqual(dim, len(plane))
            for j in xrange(len(plane)):
                val = plane[j]
                self.assert_(val in [1, -1])
                self.assertEqual(val, planes2[i][j])

    def test_mixed_dot_product(self):
        dim = 10
        sv = [(1, 0.4), (3, -0.1), (6, 0.8), (9, 0)]

        dv = array('b', [1, 1, 1, 1, 1, -1, -1, -1, -1, -1])
        dp1 = sketchy.mixed_dot_product(sv, dv)
        # 0.4 * 1 + -0.1 * 1 + 0.8 * -1 + 0 * -1
        self.assertEqual(-0.5, dp1)

        array.reverse(dv)
        dp2 = sketchy.mixed_dot_product(sv, dv)
        # 0.4 * -1 + -0.1 * -1 + 0.8 * 1 + 0 * 1
        self.assertEqual(0.5, dp2)

    def test_sparse_random_projection_binary_vector(self):
        size = 31
        dim = 100
        seed = 42
        instances = 1000
        vectors = []
        hashes = []
        ham1_cos_sims = []
        ham2_cos_sims = []
        for i in xrange(instances):
            sv = random_sparse_vector(dim, 0, 1)
            h = sketchy.sparse_random_projection(sv, size, dim, seed)
            vectors.append(sv)
            hashes.append(h)
        for i in xrange(instances):
            for j in xrange(i + 1, instances):
                ham_dist = sketchy.hamming32(hashes[i], hashes[j])
                if ham_dist == 1:
                    ham1_cos_sims.append(sketchy.sparse_cos_sim(vectors[i], vectors[j]))
                elif ham_dist == 2:
                    ham2_cos_sims.append(sketchy.sparse_cos_sim(vectors[i], vectors[j]))
        ham1_mean = sum(ham1_cos_sims) / len(ham1_cos_sims)
        ham2_mean = sum(ham2_cos_sims) / len(ham2_cos_sims)
        self.assert_(ham1_mean > ham2_mean)

 
# TODO: no unsigned ints in Java makes conversion slightly annoying, hmmm.


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
