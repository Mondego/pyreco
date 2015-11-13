__FILENAME__ = boolean_timing
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

import sys
import timeit
import numpy

array_size = 1000*1000
iterations = 10

numpy_ttime = []
numpy_sttime = []
numpy_nttime = []
numexpr_ttime = []
numexpr_sttime = []
numexpr_nttime = []

def compare_times(expr, nexpr):
    global numpy_ttime
    global numpy_sttime
    global numpy_nttime
    global numexpr_ttime
    global numexpr_sttime
    global numexpr_nttime

    print "******************* Expression:", expr

    setup_contiguous = setupNP_contiguous
    setup_strided = setupNP_strided
    setup_unaligned = setupNP_unaligned

    numpy_timer = timeit.Timer(expr, setup_contiguous)
    numpy_time = round(numpy_timer.timeit(number=iterations), 4)
    numpy_ttime.append(numpy_time)
    print 'numpy:', numpy_time / iterations

    numpy_timer = timeit.Timer(expr, setup_strided)
    numpy_stime = round(numpy_timer.timeit(number=iterations), 4)
    numpy_sttime.append(numpy_stime)
    print 'numpy strided:', numpy_stime / iterations

    numpy_timer = timeit.Timer(expr, setup_unaligned)
    numpy_ntime = round(numpy_timer.timeit(number=iterations), 4)
    numpy_nttime.append(numpy_ntime)
    print 'numpy unaligned:', numpy_ntime / iterations

    evalexpr = 'evaluate("%s", optimization="aggressive")' % expr
    numexpr_timer = timeit.Timer(evalexpr, setup_contiguous)
    numexpr_time = round(numexpr_timer.timeit(number=iterations), 4)
    numexpr_ttime.append(numexpr_time)
    print "numexpr:", numexpr_time/iterations,
    print "Speed-up of numexpr over numpy:", round(numpy_time/numexpr_time, 4)

    evalexpr = 'evaluate("%s", optimization="aggressive")' % expr
    numexpr_timer = timeit.Timer(evalexpr, setup_strided)
    numexpr_stime = round(numexpr_timer.timeit(number=iterations), 4)
    numexpr_sttime.append(numexpr_stime)
    print "numexpr strided:", numexpr_stime/iterations,
    print "Speed-up of numexpr strided over numpy:", \
          round(numpy_stime/numexpr_stime, 4)

    evalexpr = 'evaluate("%s", optimization="aggressive")' % expr
    numexpr_timer = timeit.Timer(evalexpr, setup_unaligned)
    numexpr_ntime = round(numexpr_timer.timeit(number=iterations), 4)
    numexpr_nttime.append(numexpr_ntime)
    print "numexpr unaligned:", numexpr_ntime/iterations,
    print "Speed-up of numexpr unaligned over numpy:", \
          round(numpy_ntime/numexpr_ntime, 4)



setupNP = """\
from numpy import arange, where, arctan2, sqrt
from numpy import rec as records
from numexpr import evaluate

# Initialize a recarray of 16 MB in size
r=records.array(None, formats='a%s,i4,f8', shape=%s)
c1 = r.field('f0')%s
i2 = r.field('f1')%s
f3 = r.field('f2')%s
c1[:] = "a"
i2[:] = arange(%s)/1000
f3[:] = i2/2.
"""

setupNP_contiguous = setupNP % (4, array_size,
                                ".copy()", ".copy()", ".copy()",
                                array_size)
setupNP_strided = setupNP % (4, array_size, "", "", "", array_size)
setupNP_unaligned = setupNP % (1, array_size, "", "", "", array_size)


expressions = []
expressions.append('i2 > 0')
expressions.append('i2 < 0')
expressions.append('i2 < f3')
expressions.append('i2-10 < f3')
expressions.append('i2*f3+f3*f3 > i2')
expressions.append('0.1*i2 > arctan2(i2, f3)')
expressions.append('i2%2 > 3')
expressions.append('i2%10 < 4')
expressions.append('i2**2 + (f3+1)**-2.5 < 3')
expressions.append('(f3+1)**50 > i2')
expressions.append('sqrt(i2**2 + f3**2) > 1')
expressions.append('(i2>2) | ((f3**2>3) & ~(i2*f3<2))')

def compare(expression=False):
    if expression:
        compare_times(expression, 1)
        sys.exit(0)
    nexpr = 0
    for expr in expressions:
        nexpr += 1
        compare_times(expr, nexpr)
    print

if __name__ == '__main__':

    import numexpr
    numexpr.print_versions()

    if len(sys.argv) > 1:
        expression = sys.argv[1]
        print "expression-->", expression
        compare(expression)
    else:
        compare()

    tratios = numpy.array(numpy_ttime) / numpy.array(numexpr_ttime)
    stratios = numpy.array(numpy_sttime) / numpy.array(numexpr_sttime)
    ntratios = numpy.array(numpy_nttime) / numpy.array(numexpr_nttime)


    print "*************** Numexpr vs NumPy speed-ups *******************"
#     print "numpy total:", sum(numpy_ttime)/iterations
#     print "numpy strided total:", sum(numpy_sttime)/iterations
#     print "numpy unaligned total:", sum(numpy_nttime)/iterations
#     print "numexpr total:", sum(numexpr_ttime)/iterations
    print "Contiguous case:\t %s (mean), %s (min), %s (max)" % \
          (round(tratios.mean(), 2),
           round(tratios.min(), 2),
           round(tratios.max(), 2))
#    print "numexpr strided total:", sum(numexpr_sttime)/iterations
    print "Strided case:\t\t %s (mean), %s (min), %s (max)" % \
          (round(stratios.mean(), 2),
           round(stratios.min(), 2),
           round(stratios.max(), 2))
#    print "numexpr unaligned total:", sum(numexpr_nttime)/iterations
    print "Unaligned case:\t\t %s (mean), %s (min), %s (max)" % \
          (round(ntratios.mean(), 2),
           round(ntratios.min(), 2),
           round(ntratios.max(), 2))

########NEW FILE########
__FILENAME__ = issue-36
# Small benchmark to get the even point where the threading code
# performs better than the serial code.  See issue #36 for details.

import numpy as np
import numexpr as ne
from numpy.testing import assert_array_equal
from time import time

def bench(N):
    print "*** array length:", N
    a = np.arange(N)
    t0 = time()
    ntimes = (1000*2**15) // N
    for i in xrange(ntimes):
        ne.evaluate('a>1000')
    print "numexpr--> %.3g" % ((time()-t0)/ntimes,)

    t0 = time()
    for i in xrange(ntimes):
        eval('a>1000')
    print "numpy--> %.3g" % ((time()-t0)/ntimes,)

if __name__ == "__main__":
    print "****** Testing with 1 thread..."
    ne.set_num_threads(1)
    for N in range(10, 20):
        bench(2**N)

    print "****** Testing with 2 threads..."
    ne.set_num_threads(2)
    for N in range(10, 20):
        bench(2**N)


########NEW FILE########
__FILENAME__ = issue-47
import numpy
import numexpr

numexpr.set_num_threads(8)
x0,x1,x2,x3,x4,x5 = [0,1,2,3,4,5]
t = numpy.linspace(0,1,44100000).reshape(-1,1)
numexpr.evaluate('(x0+x1*t+x2*t**2)* cos(x3+x4*t+x5**t)')

########NEW FILE########
__FILENAME__ = multidim
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

# Script to check that multidimensional arrays are speed-up properly too
# Based on a script provided by Andrew Collette.

import numpy as np
import numexpr as nx
import time

test_shapes = [
    (100*100*100),
    (100*100,100),
    (100,100,100),
    ]

test_dtype = 'f4'
nruns = 10                   # Ensemble for timing

def chunkify(chunksize):
    """ Very stupid "chunk vectorizer" which keeps memory use down.
        This version requires all inputs to have the same number of elements,
        although it shouldn't be that hard to implement simple broadcasting.
    """

    def chunkifier(func):

        def wrap(*args):

            assert len(args) > 0
            assert all(len(a.flat) == len(args[0].flat) for a in args)

            nelements = len(args[0].flat)
            nchunks, remain = divmod(nelements, chunksize)

            out = np.ndarray(args[0].shape)

            for start in xrange(0, nelements, chunksize):
                #print start
                stop = start+chunksize
                if start+chunksize > nelements:
                    stop = nelements-start
                iargs = tuple(a.flat[start:stop] for a in args)
                out.flat[start:stop] = func(*iargs)
            return out

        return wrap

    return chunkifier

test_func_str = "63 + (a*b) + (c**2) + b"

def test_func(a, b, c):
    return 63 + (a*b) + (c**2) + b

test_func_chunked = chunkify(100*100)(test_func)

for test_shape in test_shapes:
    test_size = np.product(test_shape)
    # The actual data we'll use
    a = np.arange(test_size, dtype=test_dtype).reshape(test_shape)
    b = np.arange(test_size, dtype=test_dtype).reshape(test_shape)
    c = np.arange(test_size, dtype=test_dtype).reshape(test_shape)


    start1 = time.time()
    for idx in xrange(nruns):
        result1 = test_func(a, b, c)
    stop1 = time.time()

    start2 = time.time()
    for idx in xrange(nruns):
        result2 = nx.evaluate(test_func_str)
    stop2 = time.time()

    start3 = time.time()
    for idx in xrange(nruns):
        result3 = test_func_chunked(a, b, c)
    stop3 = time.time()

    print "%s %s (average of %s runs)" % (test_shape, test_dtype, nruns)
    print "Simple: ", (stop1-start1)/nruns
    print "Numexpr: ", (stop2-start2)/nruns
    print "Chunked: ", (stop3-start3)/nruns



########NEW FILE########
__FILENAME__ = poly
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

#######################################################################
# This script compares the speed of the computation of a polynomial
# for different (numpy and numexpr) in-memory paradigms.
#
# Author: Francesc Alted
# Date: 2010-07-06
#######################################################################

import sys
from time import time
import numpy as np
import numexpr as ne


#expr = ".25*x**3 + .75*x**2 - 1.5*x - 2"  # the polynomial to compute
expr = "((.25*x + .75)*x - 1.5)*x - 2"  # a computer-friendly polynomial
N = 10*1000*1000               # the number of points to compute expression
x = np.linspace(-1, 1, N)   # the x in range [-1, 1]

#what = "numpy"              # uses numpy for computations
what = "numexpr"           # uses numexpr for computations

def compute():
    """Compute the polynomial."""
    if what == "numpy":
        y = eval(expr)
    else:
        y = ne.evaluate(expr)
    return len(y)


if __name__ == '__main__':
    if len(sys.argv) > 1:  # first arg is the package to use
        what = sys.argv[1]
    if len(sys.argv) > 2:  # second arg is the number of threads to use
        nthreads = int(sys.argv[2])
        if "ncores" in dir(ne):
            ne.set_num_threads(nthreads)
    if what not in ("numpy", "numexpr"):
        print "Unrecognized module:", what
        sys.exit(0)
    print "Computing: '%s' using %s with %d points" % (expr, what, N)
    t0 = time()
    result = compute()
    ts = round(time() - t0, 3)
    print "*** Time elapsed:", ts

########NEW FILE########
__FILENAME__ = timing
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

import timeit, numpy

array_size = 1e6
iterations = 2

# Choose the type you want to benchmark
#dtype = 'int8'
#dtype = 'int16'
#dtype = 'int32'
#dtype = 'int64'
dtype = 'float32'
#dtype = 'float64'

def compare_times(setup, expr):
    print "Expression:", expr
    namespace = {}
    exec setup in namespace

    numpy_timer = timeit.Timer(expr, setup)
    numpy_time = numpy_timer.timeit(number=iterations)
    print 'numpy:', numpy_time / iterations

    try:
        weave_timer = timeit.Timer('blitz("result=%s")' % expr, setup)
        weave_time = weave_timer.timeit(number=iterations)
        print "Weave:", weave_time/iterations

        print "Speed-up of weave over numpy:", round(numpy_time/weave_time, 2)
    except:
        print "Skipping weave timing"

    numexpr_timer = timeit.Timer('evaluate("%s", optimization="aggressive")' % expr, setup)
    numexpr_time = numexpr_timer.timeit(number=iterations)
    print "numexpr:", numexpr_time/iterations

    tratio = numpy_time/numexpr_time
    print "Speed-up of numexpr over numpy:", round(tratio, 2)
    return tratio

setup1 = """\
from numpy import arange
try: from scipy.weave import blitz
except: pass
from numexpr import evaluate
result = arange(%f, dtype='%s')
b = arange(%f, dtype='%s')
c = arange(%f, dtype='%s')
d = arange(%f, dtype='%s')
e = arange(%f, dtype='%s')
""" % ((array_size, dtype)*5)
expr1 = 'b*c+d*e'

setup2 = """\
from numpy import arange
try: from scipy.weave import blitz
except: pass
from numexpr import evaluate
a = arange(%f, dtype='%s')
b = arange(%f, dtype='%s')
result = arange(%f, dtype='%s')
""" % ((array_size, dtype)*3)
expr2 = '2*a+3*b'


setup3 = """\
from numpy import arange, sin, cos, sinh
try: from scipy.weave import blitz
except: pass
from numexpr import evaluate
a = arange(2*%f, dtype='%s')[::2]
b = arange(%f, dtype='%s')
result = arange(%f, dtype='%s')
""" % ((array_size, dtype)*3)
expr3 = '2*a + (cos(3)+5)*sinh(cos(b))'


setup4 = """\
from numpy import arange, sin, cos, sinh, arctan2
try: from scipy.weave import blitz
except: pass
from numexpr import evaluate
a = arange(2*%f, dtype='%s')[::2]
b = arange(%f, dtype='%s')
result = arange(%f, dtype='%s')
""" % ((array_size, dtype)*3)
expr4 = '2*a + arctan2(a, b)'


setup5 = """\
from numpy import arange, sin, cos, sinh, arctan2, sqrt, where
try: from scipy.weave import blitz
except: pass
from numexpr import evaluate
a = arange(2*%f, dtype='%s')[::2]
b = arange(%f, dtype='%s')
result = arange(%f, dtype='%s')
""" % ((array_size, dtype)*3)
expr5 = 'where(0.1*a > arctan2(a, b), 2*a, arctan2(a,b))'

expr6 = 'where(a != 0.0, 2, b)'

expr7 = 'where(a-10 != 0.0, a, 2)'

expr8 = 'where(a%2 != 0.0, b+5, 2)'

expr9 = 'where(a%2 != 0.0, 2, b+5)'

expr10 = 'a**2 + (b+1)**-2.5'

expr11 = '(a+1)**50'

expr12 = 'sqrt(a**2 + b**2)'

def compare(check_only=False):
    experiments = [(setup1, expr1), (setup2, expr2), (setup3, expr3),
                   (setup4, expr4), (setup5, expr5), (setup5, expr6),
                   (setup5, expr7), (setup5, expr8), (setup5, expr9),
                   (setup5, expr10), (setup5, expr11), (setup5, expr12),
                   ]
    total = 0
    for params in experiments:
        total += compare_times(*params)
        print
    average = total / len(experiments)
    print "Average =", round(average, 2)
    return average

if __name__ == '__main__':
    import numexpr
    numexpr.print_versions()

    averages = []
    for i in range(iterations):
        averages.append(compare())
    print "Averages:", ', '.join("%.2f" % x for x in averages)

########NEW FILE########
__FILENAME__ = unaligned-simple
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

"""Very simple test that compares the speed of operating with
aligned vs unaligned arrays.
"""

from timeit import Timer
import numpy as np
import numexpr as ne

niter = 10
#shape = (1000*10000)   # unidimensional test
shape = (1000, 10000)   # multidimensional test

ne.print_versions()

Z_fast = np.zeros(shape, dtype=[('x',np.float64),('y',np.int64)])
Z_slow = np.zeros(shape, dtype=[('y1',np.int8),('x',np.float64),('y2',np.int8,(7,))])

x_fast = Z_fast['x']
t = Timer("x_fast * x_fast", "from __main__ import x_fast")
print "NumPy aligned:  \t", round(min(t.repeat(3, niter)), 3), "s"

x_slow = Z_slow['x']
t = Timer("x_slow * x_slow", "from __main__ import x_slow")
print "NumPy unaligned:\t", round(min(t.repeat(3, niter)), 3), "s"

t = Timer("ne.evaluate('x_fast * x_fast')", "from __main__ import ne, x_fast")
print "Numexpr aligned:\t", round(min(t.repeat(3, niter)), 3), "s"

t = Timer("ne.evaluate('x_slow * x_slow')", "from __main__ import ne, x_slow")
print "Numexpr unaligned:\t", round(min(t.repeat(3, niter)), 3), "s"

########NEW FILE########
__FILENAME__ = varying-expr
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

# Benchmark for checking if numexpr leaks memory when evaluating
# expressions that changes continously.  It also serves for computing
# the latency of numexpr when working with small arrays.

import sys
from time import time
import numpy as np
import numexpr as ne

N = 100
M = 10

def timed_eval(eval_func, expr_func):
    t1 = time()
    for i in xrange(N):
        r = eval_func(expr_func(i))
        if i % 10 == 0:
            sys.stdout.write('.')
    print " done in %s seconds" % round(time() - t1, 3)

print "Number of iterations %s.  Length of the array: %s " % (N, M)

a = np.arange(M)

# lots of duplicates to collapse
#expr = '+'.join('(a + 1) * %d' % i for i in range(50))
# no duplicate to collapse
expr = '+'.join('(a + %d) * %d' % (i, i) for i in range(50))

def non_cacheable(i):
    return expr + '+ %d' % i

def cacheable(i):
    return expr + '+ i'

print "* Numexpr with non-cacheable expressions: ",
timed_eval(ne.evaluate, non_cacheable)
print "* Numexpr with cacheable expressions: ",
timed_eval(ne.evaluate, cacheable)
print "* Numpy with non-cacheable expressions: ",
timed_eval(eval, non_cacheable)
print "* Numpy with cacheable expressions: ",
timed_eval(eval, cacheable)

########NEW FILE########
__FILENAME__ = vml_timing
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

import sys
import timeit
import numpy
import numexpr

array_size = 1000*1000
iterations = 10

numpy_ttime = []
numpy_sttime = []
numpy_nttime = []
numexpr_ttime = []
numexpr_sttime = []
numexpr_nttime = []

def compare_times(expr, nexpr):
    global numpy_ttime
    global numpy_sttime
    global numpy_nttime
    global numexpr_ttime
    global numexpr_sttime
    global numexpr_nttime

    print "******************* Expression:", expr

    setup_contiguous = setupNP_contiguous
    setup_strided = setupNP_strided
    setup_unaligned = setupNP_unaligned

    numpy_timer = timeit.Timer(expr, setup_contiguous)
    numpy_time = round(numpy_timer.timeit(number=iterations), 4)
    numpy_ttime.append(numpy_time)
    print '%30s %.4f'%('numpy:', numpy_time / iterations)

    numpy_timer = timeit.Timer(expr, setup_strided)
    numpy_stime = round(numpy_timer.timeit(number=iterations), 4)
    numpy_sttime.append(numpy_stime)
    print '%30s %.4f'%('numpy strided:', numpy_stime / iterations)

    numpy_timer = timeit.Timer(expr, setup_unaligned)
    numpy_ntime = round(numpy_timer.timeit(number=iterations), 4)
    numpy_nttime.append(numpy_ntime)
    print '%30s %.4f'%('numpy unaligned:', numpy_ntime / iterations)

    evalexpr = 'evaluate("%s", optimization="aggressive")' % expr
    numexpr_timer = timeit.Timer(evalexpr, setup_contiguous)
    numexpr_time = round(numexpr_timer.timeit(number=iterations), 4)
    numexpr_ttime.append(numexpr_time)
    print '%30s %.4f'%("numexpr:", numexpr_time/iterations,),
    print "Speed-up of numexpr over numpy:", round(numpy_time/numexpr_time, 4)

    evalexpr = 'evaluate("%s", optimization="aggressive")' % expr
    numexpr_timer = timeit.Timer(evalexpr, setup_strided)
    numexpr_stime = round(numexpr_timer.timeit(number=iterations), 4)
    numexpr_sttime.append(numexpr_stime)
    print '%30s %.4f'%("numexpr strided:", numexpr_stime/iterations,),
    print "Speed-up of numexpr over numpy:", \
          round(numpy_stime/numexpr_stime, 4)

    evalexpr = 'evaluate("%s", optimization="aggressive")' % expr
    numexpr_timer = timeit.Timer(evalexpr, setup_unaligned)
    numexpr_ntime = round(numexpr_timer.timeit(number=iterations), 4)
    numexpr_nttime.append(numexpr_ntime)
    print '%30s %.4f'%("numexpr unaligned:", numexpr_ntime/iterations,),
    print "Speed-up of numexpr over numpy:", \
          round(numpy_ntime/numexpr_ntime, 4)

    print


setupNP = """\
from numpy import arange, linspace, arctan2, sqrt, sin, cos, exp, log
from numpy import rec as records
#from numexpr import evaluate
from numexpr import %s

# Initialize a recarray of 16 MB in size
r=records.array(None, formats='a%s,i4,f4,f8', shape=%s)
c1 = r.field('f0')%s
i2 = r.field('f1')%s
f3 = r.field('f2')%s
f4 = r.field('f3')%s
c1[:] = "a"
i2[:] = arange(%s)/1000
f3[:] = linspace(0,1,len(i2))
f4[:] = f3*1.23
"""

eval_method = "evaluate"
setupNP_contiguous = setupNP % ((eval_method, 4, array_size,) + \
                               (".copy()",)*4 + \
                               (array_size,))
setupNP_strided = setupNP % (eval_method, 4, array_size,
                             "", "", "", "", array_size)
setupNP_unaligned = setupNP % (eval_method, 1, array_size,
                               "", "", "", "", array_size)


expressions = []
expressions.append('i2 > 0')
expressions.append('f3+f4')
expressions.append('f3+i2')
expressions.append('exp(f3)')
expressions.append('log(exp(f3)+1)/f4')
expressions.append('0.1*i2 > arctan2(f3, f4)')
expressions.append('sqrt(f3**2 + f4**2) > 1')
expressions.append('sin(f3)>cos(f4)')
expressions.append('f3**f4')

def compare(expression=False):
    if expression:
        compare_times(expression, 1)
        sys.exit(0)
    nexpr = 0
    for expr in expressions:
        nexpr += 1
        compare_times(expr, nexpr)
    print

if __name__ == '__main__':
    import numexpr
    numexpr.print_versions()

    numpy.seterr(all='ignore')

    numexpr.set_vml_accuracy_mode('low')
    numexpr.set_vml_num_threads(2)

    if len(sys.argv) > 1:
        expression = sys.argv[1]
        print "expression-->", expression
        compare(expression)
    else:
        compare()

    tratios = numpy.array(numpy_ttime) / numpy.array(numexpr_ttime)
    stratios = numpy.array(numpy_sttime) / numpy.array(numexpr_sttime)
    ntratios = numpy.array(numpy_nttime) / numpy.array(numexpr_nttime)


    print "eval method: %s" % eval_method
    print "*************** Numexpr vs NumPy speed-ups *******************"
#     print "numpy total:", sum(numpy_ttime)/iterations
#     print "numpy strided total:", sum(numpy_sttime)/iterations
#     print "numpy unaligned total:", sum(numpy_nttime)/iterations
#     print "numexpr total:", sum(numexpr_ttime)/iterations
    print "Contiguous case:\t %s (mean), %s (min), %s (max)" % \
          (round(tratios.mean(), 2),
           round(tratios.min(), 2),
           round(tratios.max(), 2))
#    print "numexpr strided total:", sum(numexpr_sttime)/iterations
    print "Strided case:\t\t %s (mean), %s (min), %s (max)" % \
          (round(stratios.mean(), 2),
           round(stratios.min(), 2),
           round(stratios.max(), 2))
#    print "numexpr unaligned total:", sum(numexpr_nttime)/iterations
    print "Unaligned case:\t\t %s (mean), %s (min), %s (max)" % \
          (round(ntratios.mean(), 2),
           round(ntratios.min(), 2),
           round(ntratios.max(), 2))

########NEW FILE########
__FILENAME__ = vml_timing2
# References:
#
# http://software.intel.com/en-us/intel-mkl
# https://github.com/pydata/numexpr/wiki/NumexprMKL

from __future__ import print_function
import datetime
import sys
import numpy as np
import numexpr as ne
from time import time

N = 1e8

x = np.linspace(0, 1, N)
y = np.linspace(0, 1, N)
z = np.empty(N, dtype=np.float64)

# Our working set is 3 vectors of N doubles each
working_set_GB = 3 * N * 8 / 2**30

print("NumPy version: %s" % (np.__version__,))

t0 = time()
z = 2*y + 4*x
t1 = time()
gbs = working_set_GB / (t1-t0)
print("Time for an algebraic expression:     %.3f s / %.3f GB/s" % (t1-t0, gbs))

t0 = time()
z = np.sin(x)**2 + np.cos(y)**2
t1 = time()
gbs = working_set_GB / (t1-t0)
print("Time for a transcendental expression: %.3f s / %.3f GB/s" % (t1-t0, gbs))

print("Numexpr version: %s. Using MKL: %s" % (ne.__version__, ne.use_vml))

t0 = time()
ne.evaluate('2*y + 4*x', out = z)
t1 = time()
gbs = working_set_GB / (t1-t0)
print("Time for an algebraic expression:     %.3f s / %.3f GB/s" % (t1-t0, gbs))

t0 = time()
ne.evaluate('sin(x)**2 + cos(y)**2', out = z)
t1 = time()
gbs = working_set_GB / (t1-t0)
print("Time for a transcendental expression: %.3f s / %.3f GB/s" % (t1-t0, gbs))

########NEW FILE########
__FILENAME__ = cpuinfo
#!/usr/bin/env python

###################################################################
#  cpuinfo - Get information about CPU
#
#      License: BSD
#      Author:  Pearu Peterson <pearu@cens.ioc.ee>
#
#  See LICENSES/cpuinfo.txt for details about copyright and
#  rights to use.
####################################################################

"""
cpuinfo

Copyright 2002 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@cens.ioc.ee>
Permission to use, modify, and distribute this software is given under the
terms of the NumPy (BSD style) license.  See LICENSE.txt that came with
this distribution for specifics.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
Pearu Peterson
"""

__all__ = ['cpu']

import sys, re, types
import os
import subprocess
import warnings
import platform


def getoutput(cmd, successful_status=(0,), stacklevel=1):
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output, _ = p.communicate()
        status = p.returncode
    except EnvironmentError, e:
        warnings.warn(str(e), UserWarning, stacklevel=stacklevel)
        return False, ''
    if os.WIFEXITED(status) and os.WEXITSTATUS(status) in successful_status:
        return True, output
    return False, output


def command_info(successful_status=(0,), stacklevel=1, **kw):
    info = {}
    for key in kw:
        ok, output = getoutput(kw[key], successful_status=successful_status,
                               stacklevel=stacklevel + 1)
        if ok:
            info[key] = output.strip()
    return info


def command_by_line(cmd, successful_status=(0,), stacklevel=1):
    ok, output = getoutput(cmd, successful_status=successful_status,
                           stacklevel=stacklevel + 1)
    if not ok:
        return

    # XXX: check
    output = output.decode('ascii')

    for line in output.splitlines():
        yield line.strip()


def key_value_from_command(cmd, sep, successful_status=(0,),
                           stacklevel=1):
    d = {}
    for line in command_by_line(cmd, successful_status=successful_status,
                                stacklevel=stacklevel + 1):
        l = [s.strip() for s in line.split(sep, 1)]
        if len(l) == 2:
            d[l[0]] = l[1]
    return d


class CPUInfoBase(object):
    """Holds CPU information and provides methods for requiring
    the availability of various CPU features.
    """

    def _try_call(self, func):
        try:
            return func()
        except:
            pass

    def __getattr__(self, name):
        if not name.startswith('_'):
            if hasattr(self, '_' + name):
                attr = getattr(self, '_' + name)
                if type(attr) is types.MethodType:
                    return lambda func=self._try_call, attr=attr: func(attr)
            else:
                return lambda: None
        raise AttributeError, name

    def _getNCPUs(self):
        return 1

    def __get_nbits(self):
        abits = platform.architecture()[0]
        nbits = re.compile('(\d+)bit').search(abits).group(1)
        return nbits

    def _is_32bit(self):
        return self.__get_nbits() == '32'

    def _is_64bit(self):
        return self.__get_nbits() == '64'


class LinuxCPUInfo(CPUInfoBase):
    info = None

    def __init__(self):
        if self.info is not None:
            return
        info = [{}]
        ok, output = getoutput(['uname', '-m'])
        if ok:
            info[0]['uname_m'] = output.strip()
        try:
            fo = open('/proc/cpuinfo')
        except EnvironmentError, e:
            warnings.warn(str(e), UserWarning)
        else:
            for line in fo:
                name_value = [s.strip() for s in line.split(':', 1)]
                if len(name_value) != 2:
                    continue
                name, value = name_value
                if not info or name in info[-1]:  # next processor
                    info.append({})
                info[-1][name] = value
            fo.close()
        self.__class__.info = info

    def _not_impl(self):
        pass

    # Athlon

    def _is_AMD(self):
        return self.info[0]['vendor_id'] == 'AuthenticAMD'

    def _is_AthlonK6_2(self):
        return self._is_AMD() and self.info[0]['model'] == '2'

    def _is_AthlonK6_3(self):
        return self._is_AMD() and self.info[0]['model'] == '3'

    def _is_AthlonK6(self):
        return re.match(r'.*?AMD-K6', self.info[0]['model name']) is not None

    def _is_AthlonK7(self):
        return re.match(r'.*?AMD-K7', self.info[0]['model name']) is not None

    def _is_AthlonMP(self):
        return re.match(r'.*?Athlon\(tm\) MP\b',
                        self.info[0]['model name']) is not None

    def _is_AMD64(self):
        return self.is_AMD() and self.info[0]['family'] == '15'

    def _is_Athlon64(self):
        return re.match(r'.*?Athlon\(tm\) 64\b',
                        self.info[0]['model name']) is not None

    def _is_AthlonHX(self):
        return re.match(r'.*?Athlon HX\b',
                        self.info[0]['model name']) is not None

    def _is_Opteron(self):
        return re.match(r'.*?Opteron\b',
                        self.info[0]['model name']) is not None

    def _is_Hammer(self):
        return re.match(r'.*?Hammer\b',
                        self.info[0]['model name']) is not None

    # Alpha

    def _is_Alpha(self):
        return self.info[0]['cpu'] == 'Alpha'

    def _is_EV4(self):
        return self.is_Alpha() and self.info[0]['cpu model'] == 'EV4'

    def _is_EV5(self):
        return self.is_Alpha() and self.info[0]['cpu model'] == 'EV5'

    def _is_EV56(self):
        return self.is_Alpha() and self.info[0]['cpu model'] == 'EV56'

    def _is_PCA56(self):
        return self.is_Alpha() and self.info[0]['cpu model'] == 'PCA56'

    # Intel

    #XXX
    _is_i386 = _not_impl

    def _is_Intel(self):
        return self.info[0]['vendor_id'] == 'GenuineIntel'

    def _is_i486(self):
        return self.info[0]['cpu'] == 'i486'

    def _is_i586(self):
        return self.is_Intel() and self.info[0]['cpu family'] == '5'

    def _is_i686(self):
        return self.is_Intel() and self.info[0]['cpu family'] == '6'

    def _is_Celeron(self):
        return re.match(r'.*?Celeron',
                        self.info[0]['model name']) is not None

    def _is_Pentium(self):
        return re.match(r'.*?Pentium',
                        self.info[0]['model name']) is not None

    def _is_PentiumII(self):
        return re.match(r'.*?Pentium.*?II\b',
                        self.info[0]['model name']) is not None

    def _is_PentiumPro(self):
        return re.match(r'.*?PentiumPro\b',
                        self.info[0]['model name']) is not None

    def _is_PentiumMMX(self):
        return re.match(r'.*?Pentium.*?MMX\b',
                        self.info[0]['model name']) is not None

    def _is_PentiumIII(self):
        return re.match(r'.*?Pentium.*?III\b',
                        self.info[0]['model name']) is not None

    def _is_PentiumIV(self):
        return re.match(r'.*?Pentium.*?(IV|4)\b',
                        self.info[0]['model name']) is not None

    def _is_PentiumM(self):
        return re.match(r'.*?Pentium.*?M\b',
                        self.info[0]['model name']) is not None

    def _is_Prescott(self):
        return self.is_PentiumIV() and self.has_sse3()

    def _is_Nocona(self):
        return self.is_Intel() \
                   and (self.info[0]['cpu family'] == '6' \
                            or self.info[0]['cpu family'] == '15' ) \
                   and (self.has_sse3() and not self.has_ssse3()) \
            and re.match(r'.*?\blm\b', self.info[0]['flags']) is not None

    def _is_Core2(self):
        return self.is_64bit() and self.is_Intel() and \
               re.match(r'.*?Core\(TM\)2\b', \
                        self.info[0]['model name']) is not None

    def _is_Itanium(self):
        return re.match(r'.*?Itanium\b',
                        self.info[0]['family']) is not None

    def _is_XEON(self):
        return re.match(r'.*?XEON\b',
                        self.info[0]['model name'], re.IGNORECASE) is not None

    _is_Xeon = _is_XEON

    # Varia

    def _is_singleCPU(self):
        return len(self.info) == 1

    def _getNCPUs(self):
        return len(self.info)

    def _has_fdiv_bug(self):
        return self.info[0]['fdiv_bug'] == 'yes'

    def _has_f00f_bug(self):
        return self.info[0]['f00f_bug'] == 'yes'

    def _has_mmx(self):
        return re.match(r'.*?\bmmx\b', self.info[0]['flags']) is not None

    def _has_sse(self):
        return re.match(r'.*?\bsse\b', self.info[0]['flags']) is not None

    def _has_sse2(self):
        return re.match(r'.*?\bsse2\b', self.info[0]['flags']) is not None

    def _has_sse3(self):
        return re.match(r'.*?\bpni\b', self.info[0]['flags']) is not None

    def _has_ssse3(self):
        return re.match(r'.*?\bssse3\b', self.info[0]['flags']) is not None

    def _has_3dnow(self):
        return re.match(r'.*?\b3dnow\b', self.info[0]['flags']) is not None

    def _has_3dnowext(self):
        return re.match(r'.*?\b3dnowext\b', self.info[0]['flags']) is not None


class IRIXCPUInfo(CPUInfoBase):
    info = None

    def __init__(self):
        if self.info is not None:
            return
        info = key_value_from_command('sysconf', sep=' ',
                                      successful_status=(0, 1))
        self.__class__.info = info

    def _not_impl(self):
        pass

    def _is_singleCPU(self):
        return self.info.get('NUM_PROCESSORS') == '1'

    def _getNCPUs(self):
        return int(self.info.get('NUM_PROCESSORS', 1))

    def __cputype(self, n):
        return self.info.get('PROCESSORS').split()[0].lower() == 'r%s' % (n)

    def _is_r2000(self):
        return self.__cputype(2000)

    def _is_r3000(self):
        return self.__cputype(3000)

    def _is_r3900(self):
        return self.__cputype(3900)

    def _is_r4000(self):
        return self.__cputype(4000)

    def _is_r4100(self):
        return self.__cputype(4100)

    def _is_r4300(self):
        return self.__cputype(4300)

    def _is_r4400(self):
        return self.__cputype(4400)

    def _is_r4600(self):
        return self.__cputype(4600)

    def _is_r4650(self):
        return self.__cputype(4650)

    def _is_r5000(self):
        return self.__cputype(5000)

    def _is_r6000(self):
        return self.__cputype(6000)

    def _is_r8000(self):
        return self.__cputype(8000)

    def _is_r10000(self):
        return self.__cputype(10000)

    def _is_r12000(self):
        return self.__cputype(12000)

    def _is_rorion(self):
        return self.__cputype('orion')

    def get_ip(self):
        try:
            return self.info.get('MACHINE')
        except:
            pass

    def __machine(self, n):
        return self.info.get('MACHINE').lower() == 'ip%s' % (n)

    def _is_IP19(self):
        return self.__machine(19)

    def _is_IP20(self):
        return self.__machine(20)

    def _is_IP21(self):
        return self.__machine(21)

    def _is_IP22(self):
        return self.__machine(22)

    def _is_IP22_4k(self):
        return self.__machine(22) and self._is_r4000()

    def _is_IP22_5k(self):
        return self.__machine(22) and self._is_r5000()

    def _is_IP24(self):
        return self.__machine(24)

    def _is_IP25(self):
        return self.__machine(25)

    def _is_IP26(self):
        return self.__machine(26)

    def _is_IP27(self):
        return self.__machine(27)

    def _is_IP28(self):
        return self.__machine(28)

    def _is_IP30(self):
        return self.__machine(30)

    def _is_IP32(self):
        return self.__machine(32)

    def _is_IP32_5k(self):
        return self.__machine(32) and self._is_r5000()

    def _is_IP32_10k(self):
        return self.__machine(32) and self._is_r10000()


class DarwinCPUInfo(CPUInfoBase):
    info = None

    def __init__(self):
        if self.info is not None:
            return
        info = command_info(arch='arch',
                            machine='machine')
        info['sysctl_hw'] = key_value_from_command(['sysctl', 'hw'], sep='=')
        self.__class__.info = info

    def _not_impl(self): pass

    def _getNCPUs(self):
        return int(self.info['sysctl_hw'].get('hw.ncpu', 1))

    def _is_Power_Macintosh(self):
        return self.info['sysctl_hw']['hw.machine'] == 'Power Macintosh'

    def _is_i386(self):
        return self.info['arch'] == 'i386'

    def _is_ppc(self):
        return self.info['arch'] == 'ppc'

    def __machine(self, n):
        return self.info['machine'] == 'ppc%s' % n

    def _is_ppc601(self): return self.__machine(601)

    def _is_ppc602(self): return self.__machine(602)

    def _is_ppc603(self): return self.__machine(603)

    def _is_ppc603e(self): return self.__machine('603e')

    def _is_ppc604(self): return self.__machine(604)

    def _is_ppc604e(self): return self.__machine('604e')

    def _is_ppc620(self): return self.__machine(620)

    def _is_ppc630(self): return self.__machine(630)

    def _is_ppc740(self): return self.__machine(740)

    def _is_ppc7400(self): return self.__machine(7400)

    def _is_ppc7450(self): return self.__machine(7450)

    def _is_ppc750(self): return self.__machine(750)

    def _is_ppc403(self): return self.__machine(403)

    def _is_ppc505(self): return self.__machine(505)

    def _is_ppc801(self): return self.__machine(801)

    def _is_ppc821(self): return self.__machine(821)

    def _is_ppc823(self): return self.__machine(823)

    def _is_ppc860(self): return self.__machine(860)


class SunOSCPUInfo(CPUInfoBase):
    info = None

    def __init__(self):
        if self.info is not None:
            return
        info = command_info(arch='arch',
                            mach='mach',
                            uname_i='uname_i',
                            isainfo_b=['isainfo', '-b'],
                            isainfo_n=['isainfo', '-n'],
        )
        info['uname_X'] = key_value_from_command('uname -X', sep='=')
        for line in command_by_line(['psrinfo', '-v', '0']):
            m = re.match(r'\s*The (?P<p>[\w\d]+) processor operates at', line)
            if m:
                info['processor'] = m.group('p')
                break
        self.__class__.info = info

    def _not_impl(self):
        pass

    def _is_i386(self):
        return self.info['isainfo_n'] == 'i386'

    def _is_sparc(self):
        return self.info['isainfo_n'] == 'sparc'

    def _is_sparcv9(self):
        return self.info['isainfo_n'] == 'sparcv9'

    def _getNCPUs(self):
        return int(self.info['uname_X'].get('NumCPU', 1))

    def _is_sun4(self):
        return self.info['arch'] == 'sun4'

    def _is_SUNW(self):
        return re.match(r'SUNW', self.info['uname_i']) is not None

    def _is_sparcstation5(self):
        return re.match(r'.*SPARCstation-5', self.info['uname_i']) is not None

    def _is_ultra1(self):
        return re.match(r'.*Ultra-1', self.info['uname_i']) is not None

    def _is_ultra250(self):
        return re.match(r'.*Ultra-250', self.info['uname_i']) is not None

    def _is_ultra2(self):
        return re.match(r'.*Ultra-2', self.info['uname_i']) is not None

    def _is_ultra30(self):
        return re.match(r'.*Ultra-30', self.info['uname_i']) is not None

    def _is_ultra4(self):
        return re.match(r'.*Ultra-4', self.info['uname_i']) is not None

    def _is_ultra5_10(self):
        return re.match(r'.*Ultra-5_10', self.info['uname_i']) is not None

    def _is_ultra5(self):
        return re.match(r'.*Ultra-5', self.info['uname_i']) is not None

    def _is_ultra60(self):
        return re.match(r'.*Ultra-60', self.info['uname_i']) is not None

    def _is_ultra80(self):
        return re.match(r'.*Ultra-80', self.info['uname_i']) is not None

    def _is_ultraenterprice(self):
        return re.match(r'.*Ultra-Enterprise', self.info['uname_i']) is not None

    def _is_ultraenterprice10k(self):
        return re.match(r'.*Ultra-Enterprise-10000', self.info['uname_i']) is not None

    def _is_sunfire(self):
        return re.match(r'.*Sun-Fire', self.info['uname_i']) is not None

    def _is_ultra(self):
        return re.match(r'.*Ultra', self.info['uname_i']) is not None

    def _is_cpusparcv7(self):
        return self.info['processor'] == 'sparcv7'

    def _is_cpusparcv8(self):
        return self.info['processor'] == 'sparcv8'

    def _is_cpusparcv9(self):
        return self.info['processor'] == 'sparcv9'


class Win32CPUInfo(CPUInfoBase):
    info = None
    pkey = r"HARDWARE\DESCRIPTION\System\CentralProcessor"
    # XXX: what does the value of
    #   HKEY_LOCAL_MACHINE\HARDWARE\DESCRIPTION\System\CentralProcessor\0
    # mean?

    def __init__(self):
        if self.info is not None:
            return
        info = []
        try:
            #XXX: Bad style to use so long `try:...except:...`. Fix it!
            import _winreg

            prgx = re.compile(r"family\s+(?P<FML>\d+)\s+model\s+(?P<MDL>\d+)" \
                              "\s+stepping\s+(?P<STP>\d+)", re.IGNORECASE)
            chnd = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, self.pkey)
            pnum = 0
            while 1:
                try:
                    proc = _winreg.EnumKey(chnd, pnum)
                except _winreg.error:
                    break
                else:
                    pnum += 1
                    info.append({"Processor": proc})
                    phnd = _winreg.OpenKey(chnd, proc)
                    pidx = 0
                    while True:
                        try:
                            name, value, vtpe = _winreg.EnumValue(phnd, pidx)
                        except _winreg.error:
                            break
                        else:
                            pidx = pidx + 1
                            info[-1][name] = value
                            if name == "Identifier":
                                srch = prgx.search(value)
                                if srch:
                                    info[-1]["Family"] = int(srch.group("FML"))
                                    info[-1]["Model"] = int(srch.group("MDL"))
                                    info[-1]["Stepping"] = int(srch.group("STP"))
        except:
            print
            sys.exc_value, '(ignoring)'
        self.__class__.info = info

    def _not_impl(self):
        pass

    # Athlon

    def _is_AMD(self):
        return self.info[0]['VendorIdentifier'] == 'AuthenticAMD'

    def _is_Am486(self):
        return self.is_AMD() and self.info[0]['Family'] == 4

    def _is_Am5x86(self):
        return self.is_AMD() and self.info[0]['Family'] == 4

    def _is_AMDK5(self):
        return self.is_AMD() and self.info[0]['Family'] == 5 \
            and self.info[0]['Model'] in [0, 1, 2, 3]

    def _is_AMDK6(self):
        return self.is_AMD() and self.info[0]['Family'] == 5 \
            and self.info[0]['Model'] in [6, 7]

    def _is_AMDK6_2(self):
        return self.is_AMD() and self.info[0]['Family'] == 5 \
            and self.info[0]['Model'] == 8

    def _is_AMDK6_3(self):
        return self.is_AMD() and self.info[0]['Family'] == 5 \
            and self.info[0]['Model'] == 9

    def _is_AMDK7(self):
        return self.is_AMD() and self.info[0]['Family'] == 6

    # To reliably distinguish between the different types of AMD64 chips
    # (Athlon64, Operton, Athlon64 X2, Semperon, Turion 64, etc.) would
    # require looking at the 'brand' from cpuid

    def _is_AMD64(self):
        return self.is_AMD() and self.info[0]['Family'] == 15

    # Intel

    def _is_Intel(self):
        return self.info[0]['VendorIdentifier'] == 'GenuineIntel'

    def _is_i386(self):
        return self.info[0]['Family'] == 3

    def _is_i486(self):
        return self.info[0]['Family'] == 4

    def _is_i586(self):
        return self.is_Intel() and self.info[0]['Family'] == 5

    def _is_i686(self):
        return self.is_Intel() and self.info[0]['Family'] == 6

    def _is_Pentium(self):
        return self.is_Intel() and self.info[0]['Family'] == 5

    def _is_PentiumMMX(self):
        return self.is_Intel() and self.info[0]['Family'] == 5 \
            and self.info[0]['Model'] == 4

    def _is_PentiumPro(self):
        return self.is_Intel() and self.info[0]['Family'] == 6 \
            and self.info[0]['Model'] == 1

    def _is_PentiumII(self):
        return self.is_Intel() and self.info[0]['Family'] == 6 \
            and self.info[0]['Model'] in [3, 5, 6]

    def _is_PentiumIII(self):
        return self.is_Intel() and self.info[0]['Family'] == 6 \
            and self.info[0]['Model'] in [7, 8, 9, 10, 11]

    def _is_PentiumIV(self):
        return self.is_Intel() and self.info[0]['Family'] == 15

    def _is_PentiumM(self):
        return self.is_Intel() and self.info[0]['Family'] == 6 \
            and self.info[0]['Model'] in [9, 13, 14]

    def _is_Core2(self):
        return self.is_Intel() and self.info[0]['Family'] == 6 \
            and self.info[0]['Model'] in [15, 16, 17]

    # Varia

    def _is_singleCPU(self):
        return len(self.info) == 1

    def _getNCPUs(self):
        return len(self.info)

    def _has_mmx(self):
        if self.is_Intel():
            return (self.info[0]['Family'] == 5 and self.info[0]['Model'] == 4) \
                or (self.info[0]['Family'] in [6, 15])
        elif self.is_AMD():
            return self.info[0]['Family'] in [5, 6, 15]
        else:
            return False

    def _has_sse(self):
        if self.is_Intel():
            return (self.info[0]['Family'] == 6 and \
                    self.info[0]['Model'] in [7, 8, 9, 10, 11]) \
                or self.info[0]['Family'] == 15
        elif self.is_AMD():
            return (self.info[0]['Family'] == 6 and \
                    self.info[0]['Model'] in [6, 7, 8, 10]) \
                or self.info[0]['Family'] == 15
        else:
            return False

    def _has_sse2(self):
        if self.is_Intel():
            return self.is_Pentium4() or self.is_PentiumM() \
                or self.is_Core2()
        elif self.is_AMD():
            return self.is_AMD64()
        else:
            return False

    def _has_3dnow(self):
        return self.is_AMD() and self.info[0]['Family'] in [5, 6, 15]

    def _has_3dnowext(self):
        return self.is_AMD() and self.info[0]['Family'] in [6, 15]


if sys.platform.startswith('linux'):  # variations: linux2,linux-i386 (any others?)
    cpuinfo = LinuxCPUInfo
elif sys.platform.startswith('irix'):
    cpuinfo = IRIXCPUInfo
elif sys.platform == 'darwin':
    cpuinfo = DarwinCPUInfo
elif sys.platform.startswith('sunos'):
    cpuinfo = SunOSCPUInfo
elif sys.platform.startswith('win32'):
    cpuinfo = Win32CPUInfo
elif sys.platform.startswith('cygwin'):
    cpuinfo = LinuxCPUInfo
#XXX: other OS's. Eg. use _winreg on Win32. Or os.uname on unices.
else:
    cpuinfo = CPUInfoBase

cpu = cpuinfo()

if __name__ == "__main__":

    cpu.is_blaa()
    cpu.is_Intel()
    cpu.is_Alpha()

    print
    'CPU information:',
    for name in dir(cpuinfo):
        if name[0] == '_' and name[1] != '_':
            r = getattr(cpu, name[1:])()
            if r:
                if r != 1:
                    print
                    '%s=%s' % (name[1:], r),
                else:
                    print
                    name[1:],
    print

########NEW FILE########
__FILENAME__ = expressions
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

__all__ = ['E']

import operator
import sys
import threading

import numpy

# Declare a double type that does not exist in Python space
double = numpy.double

# The default kind for undeclared variables
default_kind = 'double'
if sys.version_info[0] < 3:
    int_ = int
    long_ = long
else:
    int_ = numpy.int32
    long_ = numpy.int64

type_to_kind = {bool: 'bool', int_: 'int', long_: 'long', float: 'float',
                double: 'double', complex: 'complex', bytes: 'bytes'}
kind_to_type = {'bool': bool, 'int': int_, 'long': long_, 'float': float,
                'double': double, 'complex': complex, 'bytes': bytes}
kind_rank = ['bool', 'int', 'long', 'float', 'double', 'complex', 'none']
scalar_constant_types = [bool, int_, long, float, double, complex, bytes]

# Final corrections for Python 3 (mainly for PyTables needs)
if sys.version_info[0] > 2:
    type_to_kind[str] = 'str'
    kind_to_type['str'] = str
    scalar_constant_types.append(str)
scalar_constant_types = tuple(scalar_constant_types)

from numexpr import interpreter


class Expression(object):
    def __init__(self):
        object.__init__(self)

    def __getattr__(self, name):
        if name.startswith('_'):
            return self.__dict__[name]
        else:
            return VariableNode(name, default_kind)


E = Expression()


class Context(threading.local):
    initialized = False

    def __init__(self, dict_):
        if self.initialized:
            raise SystemError('__init__ called too many times')
        self.initialized = True
        self.__dict__.update(dict_)

    def get(self, value, default):
        return self.__dict__.get(value, default)

    def get_current_context(self):
        return self.__dict__

    def set_new_context(self, dict_):
        self.__dict__.update(dict_)

# This will be called each time the local object is used in a separate thread
_context = Context({})


def get_optimization():
    return _context.get('optimization', 'none')


# helper functions for creating __magic__ methods
def ophelper(f):
    def func(*args):
        args = list(args)
        for i, x in enumerate(args):
            if isConstant(x):
                args[i] = x = ConstantNode(x)
            if not isinstance(x, ExpressionNode):
                raise TypeError("unsupported object type: %s" % type(x))
        return f(*args)

    func.__name__ = f.__name__
    func.__doc__ = f.__doc__
    func.__dict__.update(f.__dict__)
    return func


def allConstantNodes(args):
    "returns True if args are all ConstantNodes."
    for x in args:
        if not isinstance(x, ConstantNode):
            return False
    return True


def isConstant(ex):
    "Returns True if ex is a constant scalar of an allowed type."
    return isinstance(ex, scalar_constant_types)


def commonKind(nodes):
    node_kinds = [node.astKind for node in nodes]
    str_count = node_kinds.count('bytes') + node_kinds.count('str')
    if 0 < str_count < len(node_kinds):  # some args are strings, but not all
        raise TypeError("strings can only be operated with strings")
    if str_count > 0:  # if there are some, all of them must be
        return 'bytes'
    n = -1
    for x in nodes:
        n = max(n, kind_rank.index(x.astKind))
    return kind_rank[n]


max_int32 = 2147483647
min_int32 = -max_int32 - 1


def bestConstantType(x):
    # ``numpy.string_`` is a subclass of ``bytes``
    if isinstance(x, (bytes, str)):
        return bytes
    # Numeric conversion to boolean values is not tried because
    # ``bool(1) == True`` (same for 0 and False), so 0 and 1 would be
    # interpreted as booleans when ``False`` and ``True`` are already
    # supported.
    if isinstance(x, (bool, numpy.bool_)):
        return bool
    # ``long`` objects are kept as is to allow the user to force
    # promotion of results by using long constants, e.g. by operating
    # a 32-bit array with a long (64-bit) constant.
    if isinstance(x, (long_, numpy.int64)):
        return long_
    # ``double`` objects are kept as is to allow the user to force
    # promotion of results by using double constants, e.g. by operating
    # a float (32-bit) array with a double (64-bit) constant.
    if isinstance(x, double):
        return double
    if isinstance(x, (int, numpy.integer)):
        # Constants needing more than 32 bits are always
        # considered ``long``, *regardless of the platform*, so we
        # can clearly tell 32- and 64-bit constants apart.
        if not (min_int32 <= x <= max_int32):
            return long_
        return int_
    # The duality of float and double in Python avoids that we have to list
    # ``double`` too.
    for converter in float, complex:
        try:
            y = converter(x)
        except StandardError, err:
            continue
        if y == x:
            return converter


def getKind(x):
    converter = bestConstantType(x)
    return type_to_kind[converter]


def binop(opname, reversed=False, kind=None):
    # Getting the named method from self (after reversal) does not
    # always work (e.g. int constants do not have a __lt__ method).
    opfunc = getattr(operator, "__%s__" % opname)

    @ophelper
    def operation(self, other):
        if reversed:
            self, other = other, self
        if allConstantNodes([self, other]):
            return ConstantNode(opfunc(self.value, other.value))
        else:
            return OpNode(opname, (self, other), kind=kind)

    return operation


def func(func, minkind=None, maxkind=None):
    @ophelper
    def function(*args):
        if allConstantNodes(args):
            return ConstantNode(func(*[x.value for x in args]))
        kind = commonKind(args)
        if kind in ('int', 'long'):
            # Exception for following NumPy casting rules
            #FIXME: this is not always desirable. The following
            # functions which return ints (for int inputs) on numpy
            # but not on numexpr: copy, abs, fmod, ones_like
            kind = 'double'
        else:
            # Apply regular casting rules
            if minkind and kind_rank.index(minkind) > kind_rank.index(kind):
                kind = minkind
            if maxkind and kind_rank.index(maxkind) < kind_rank.index(kind):
                kind = maxkind
        return FuncNode(func.__name__, args, kind)

    return function


@ophelper
def where_func(a, b, c):
    if isinstance(a, ConstantNode):
        #FIXME: This prevents where(True, a, b)
        raise ValueError("too many dimensions")
    if allConstantNodes([a, b, c]):
        return ConstantNode(numpy.where(a, b, c))
    return FuncNode('where', [a, b, c])


def encode_axis(axis):
    if isinstance(axis, ConstantNode):
        axis = axis.value
    if axis is None:
        axis = interpreter.allaxes
    else:
        if axis < 0:
            raise ValueError("negative axis are not supported")
        if axis > 254:
            raise ValueError("cannot encode axis")
    return RawNode(axis)


def sum_func(a, axis=None):
    axis = encode_axis(axis)
    if isinstance(a, ConstantNode):
        return a
    if isinstance(a, (bool, int_, long_, float, double, complex)):
        a = ConstantNode(a)
    return FuncNode('sum', [a, axis], kind=a.astKind)


def prod_func(a, axis=None):
    axis = encode_axis(axis)
    if isinstance(a, (bool, int_, long_, float, double, complex)):
        a = ConstantNode(a)
    if isinstance(a, ConstantNode):
        return a
    return FuncNode('prod', [a, axis], kind=a.astKind)


@ophelper
def contains_func(a, b):
    return FuncNode('contains', [a, b], kind='bool')


@ophelper
def div_op(a, b):
    if get_optimization() in ('moderate', 'aggressive'):
        if (isinstance(b, ConstantNode) and
                (a.astKind == b.astKind) and
                    a.astKind in ('float', 'double', 'complex')):
            return OpNode('mul', [a, ConstantNode(1. / b.value)])
    return OpNode('div', [a, b])


@ophelper
def truediv_op(a, b):
    if get_optimization() in ('moderate', 'aggressive'):
        if (isinstance(b, ConstantNode) and
                (a.astKind == b.astKind) and
                    a.astKind in ('float', 'double', 'complex')):
            return OpNode('mul', [a, ConstantNode(1. / b.value)])
    kind = commonKind([a, b])
    if kind in ('bool', 'int', 'long'):
        kind = 'double'
    return OpNode('div', [a, b], kind=kind)


@ophelper
def rtruediv_op(a, b):
    return truediv_op(b, a)


@ophelper
def pow_op(a, b):
    if allConstantNodes([a, b]):
        return ConstantNode(a ** b)
    if isinstance(b, ConstantNode):
        x = b.value
        if get_optimization() == 'aggressive':
            RANGE = 50  # Approximate break even point with pow(x,y)
            # Optimize all integral and half integral powers in [-RANGE, RANGE]
            # Note: for complex numbers RANGE could be larger.
            if (int(2 * x) == 2 * x) and (-RANGE <= abs(x) <= RANGE):
                n = int_(abs(x))
                ishalfpower = int_(abs(2 * x)) % 2

                def multiply(x, y):
                    if x is None: return y
                    return OpNode('mul', [x, y])

                r = None
                p = a
                mask = 1
                while True:
                    if (n & mask):
                        r = multiply(r, p)
                    mask <<= 1
                    if mask > n:
                        break
                    p = OpNode('mul', [p, p])
                if ishalfpower:
                    kind = commonKind([a])
                    if kind in ('int', 'long'):
                        kind = 'double'
                    r = multiply(r, OpNode('sqrt', [a], kind))
                if r is None:
                    r = OpNode('ones_like', [a])
                if x < 0:
                    r = OpNode('div', [ConstantNode(1), r])
                return r
        if get_optimization() in ('moderate', 'aggressive'):
            if x == -1:
                return OpNode('div', [ConstantNode(1), a])
            if x == 0:
                return OpNode('ones_like', [a])
            if x == 0.5:
                kind = a.astKind
                if kind in ('int', 'long'): kind = 'double'
                return FuncNode('sqrt', [a], kind=kind)
            if x == 1:
                return a
            if x == 2:
                return OpNode('mul', [a, a])
    return OpNode('pow', [a, b])

# The functions and the minimum and maximum types accepted
functions = {
    'copy': func(numpy.copy),
    'ones_like': func(numpy.ones_like),
    'sqrt': func(numpy.sqrt, 'float'),

    'sin': func(numpy.sin, 'float'),
    'cos': func(numpy.cos, 'float'),
    'tan': func(numpy.tan, 'float'),
    'arcsin': func(numpy.arcsin, 'float'),
    'arccos': func(numpy.arccos, 'float'),
    'arctan': func(numpy.arctan, 'float'),

    'sinh': func(numpy.sinh, 'float'),
    'cosh': func(numpy.cosh, 'float'),
    'tanh': func(numpy.tanh, 'float'),
    'arcsinh': func(numpy.arcsinh, 'float'),
    'arccosh': func(numpy.arccosh, 'float'),
    'arctanh': func(numpy.arctanh, 'float'),

    'fmod': func(numpy.fmod, 'float'),
    'arctan2': func(numpy.arctan2, 'float'),

    'log': func(numpy.log, 'float'),
    'log1p': func(numpy.log1p, 'float'),
    'log10': func(numpy.log10, 'float'),
    'exp': func(numpy.exp, 'float'),
    'expm1': func(numpy.expm1, 'float'),

    'abs': func(numpy.absolute, 'float'),

    'where': where_func,

    'real': func(numpy.real, 'double', 'double'),
    'imag': func(numpy.imag, 'double', 'double'),
    'complex': func(complex, 'complex'),
    'conj': func(numpy.conj, 'complex'),

    'sum': sum_func,
    'prod': prod_func,
    'contains': contains_func,
}


class ExpressionNode(object):
    """An object that represents a generic number object.

    This implements the number special methods so that we can keep
    track of how this object has been used.
    """
    astType = 'generic'

    def __init__(self, value=None, kind=None, children=None):
        object.__init__(self)
        self.value = value
        if kind is None:
            kind = 'none'
        self.astKind = kind
        if children is None:
            self.children = ()
        else:
            self.children = tuple(children)

    def get_real(self):
        if self.astType == 'constant':
            return ConstantNode(complex(self.value).real)
        return OpNode('real', (self,), 'double')

    real = property(get_real)

    def get_imag(self):
        if self.astType == 'constant':
            return ConstantNode(complex(self.value).imag)
        return OpNode('imag', (self,), 'double')

    imag = property(get_imag)

    def __str__(self):
        return '%s(%s, %s, %s)' % (self.__class__.__name__, self.value,
                                   self.astKind, self.children)

    def __repr__(self):
        return self.__str__()

    def __neg__(self):
        return OpNode('neg', (self,))

    def __invert__(self):
        return OpNode('invert', (self,))

    def __pos__(self):
        return self

    # The next check is commented out. See #24 for more info.

    def __nonzero__(self):
        raise TypeError("You can't use Python's standard boolean operators in "
                        "NumExpr expressions. You should use their bitwise "
                        "counterparts instead: '&' instead of 'and', "
                        "'|' instead of 'or', and '~' instead of 'not'.")

    __add__ = __radd__ = binop('add')
    __sub__ = binop('sub')
    __rsub__ = binop('sub', reversed=True)
    __mul__ = __rmul__ = binop('mul')
    if sys.version_info[0] < 3:
        __div__ = div_op
        __rdiv__ = binop('div', reversed=True)
    __truediv__ = truediv_op
    __rtruediv__ = rtruediv_op
    __pow__ = pow_op
    __rpow__ = binop('pow', reversed=True)
    __mod__ = binop('mod')
    __rmod__ = binop('mod', reversed=True)

    __lshift__ = binop('lshift')
    __rlshift__ = binop('lshift', reversed=True)
    __rshift__ = binop('rshift')
    __rrshift__ = binop('rshift', reversed=True)

    # boolean operations

    __and__ = binop('and', kind='bool')
    __or__ = binop('or', kind='bool')

    __gt__ = binop('gt', kind='bool')
    __ge__ = binop('ge', kind='bool')
    __eq__ = binop('eq', kind='bool')
    __ne__ = binop('ne', kind='bool')
    __lt__ = binop('gt', reversed=True, kind='bool')
    __le__ = binop('ge', reversed=True, kind='bool')


class LeafNode(ExpressionNode):
    leafNode = True


class VariableNode(LeafNode):
    astType = 'variable'

    def __init__(self, value=None, kind=None, children=None):
        LeafNode.__init__(self, value=value, kind=kind)


class RawNode(object):
    """Used to pass raw integers to interpreter.
    For instance, for selecting what function to use in func1.
    Purposely don't inherit from ExpressionNode, since we don't wan't
    this to be used for anything but being walked.
    """
    astType = 'raw'
    astKind = 'none'

    def __init__(self, value):
        self.value = value
        self.children = ()

    def __str__(self):
        return 'RawNode(%s)' % (self.value,)

    __repr__ = __str__


class ConstantNode(LeafNode):
    astType = 'constant'

    def __init__(self, value=None, children=None):
        kind = getKind(value)
        # Python float constants are double precision by default
        if kind == 'float':
            kind = 'double'
        LeafNode.__init__(self, value=value, kind=kind)

    def __neg__(self):
        return ConstantNode(-self.value)

    def __invert__(self):
        return ConstantNode(~self.value)


class OpNode(ExpressionNode):
    astType = 'op'

    def __init__(self, opcode=None, args=None, kind=None):
        if (kind is None) and (args is not None):
            kind = commonKind(args)
        ExpressionNode.__init__(self, value=opcode, kind=kind, children=args)


class FuncNode(OpNode):
    def __init__(self, opcode=None, args=None, kind=None):
        if (kind is None) and (args is not None):
            kind = commonKind(args)
        OpNode.__init__(self, opcode, args, kind)

########NEW FILE########
__FILENAME__ = necompiler
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

import __future__
import sys
import numpy

from numexpr import interpreter, expressions, use_vml, is_cpu_amd_intel
from numexpr.utils import CacheDict

# Declare a double type that does not exist in Python space
double = numpy.double
if sys.version_info[0] < 3:
    int_ = int
    long_ = long
else:
    int_ = numpy.int32
    long_ = numpy.int64

typecode_to_kind = {'b': 'bool', 'i': 'int', 'l': 'long', 'f': 'float',
                    'd': 'double', 'c': 'complex', 's': 'bytes', 'n': 'none'}
kind_to_typecode = {'bool': 'b', 'int': 'i', 'long': 'l', 'float': 'f',
                    'double': 'd', 'complex': 'c', 'bytes': 's', 'none': 'n'}
type_to_typecode = {bool: 'b', int_: 'i', long_: 'l', float: 'f',
                    double: 'd', complex: 'c', bytes: 's'}
type_to_kind = expressions.type_to_kind
kind_to_type = expressions.kind_to_type
default_type = kind_to_type[expressions.default_kind]

# Final addtions for Python 3 (mainly for PyTables needs)
if sys.version_info[0] > 2:
    typecode_to_kind['s'] = 'str'
    kind_to_typecode['str'] = 's'
    type_to_typecode[str] = 's'

scalar_constant_kinds = kind_to_typecode.keys()


class ASTNode(object):
    """Abstract Syntax Tree node.

    Members:

    astType      -- type of node (op, constant, variable, raw, or alias)
    astKind      -- the type of the result (bool, float, etc.)
    value        -- value associated with this node.
                    An opcode, numerical value, a variable name, etc.
    children     -- the children below this node
    reg          -- the register assigned to the result for this node.
    """
    cmpnames = ['astType', 'astKind', 'value', 'children']

    def __init__(self, astType='generic', astKind='unknown',
                 value=None, children=()):
        object.__init__(self)
        self.astType = astType
        self.astKind = astKind
        self.value = value
        self.children = tuple(children)
        self.reg = None

    def __eq__(self, other):
        if self.astType == 'alias':
            self = self.value
        if other.astType == 'alias':
            other = other.value
        if not isinstance(other, ASTNode):
            return False
        for name in self.cmpnames:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __hash__(self):
        if self.astType == 'alias':
            self = self.value
        return hash((self.astType, self.astKind, self.value, self.children))

    def __str__(self):
        return 'AST(%s, %s, %s, %s, %s)' % (self.astType, self.astKind,
                                            self.value, self.children, self.reg)

    def __repr__(self):
        return '<AST object at %s>' % id(self)

    def key(self):
        return (self.astType, self.astKind, self.value, self.children)

    def typecode(self):
        return kind_to_typecode[self.astKind]

    def postorderWalk(self):
        for c in self.children:
            for w in c.postorderWalk():
                yield w
        yield self

    def allOf(self, *astTypes):
        astTypes = set(astTypes)
        for w in self.postorderWalk():
            if w.astType in astTypes:
                yield w


def expressionToAST(ex):
    """Take an expression tree made out of expressions.ExpressionNode,
    and convert to an AST tree.

    This is necessary as ExpressionNode overrides many methods to act
    like a number.
    """
    return ASTNode(ex.astType, ex.astKind, ex.value,
                   [expressionToAST(c) for c in ex.children])


def sigPerms(s):
    """Generate all possible signatures derived by upcasting the given
    signature.
    """
    codes = 'bilfdc'
    if not s:
        yield ''
    elif s[0] in codes:
        start = codes.index(s[0])
        for x in codes[start:]:
            for y in sigPerms(s[1:]):
                yield x + y
    elif s[0] == 's':  # numbers shall not be cast to strings
        for y in sigPerms(s[1:]):
            yield 's' + y
    else:
        yield s


def typeCompileAst(ast):
    """Assign appropiate types to each node in the AST.

    Will convert opcodes and functions to appropiate upcast version,
    and add "cast" ops if needed.
    """
    children = list(ast.children)
    if ast.astType == 'op':
        retsig = ast.typecode()
        basesig = ''.join(x.typecode() for x in list(ast.children))
        # Find some operation that will work on an acceptable casting of args.
        for sig in sigPerms(basesig):
            value = (ast.value + '_' + retsig + sig).encode('ascii')
            if value in interpreter.opcodes:
                break
        else:
            for sig in sigPerms(basesig):
                funcname = (ast.value + '_' + retsig + sig).encode('ascii')
                if funcname in interpreter.funccodes:
                    value = ('func_%sn' % (retsig + sig)).encode('ascii')
                    children += [ASTNode('raw', 'none',
                                         interpreter.funccodes[funcname])]
                    break
            else:
                raise NotImplementedError(
                    "couldn't find matching opcode for '%s'"
                    % (ast.value + '_' + retsig + basesig))
        # First just cast constants, then cast variables if necessary:
        for i, (have, want) in enumerate(zip(basesig, sig)):
            if have != want:
                kind = typecode_to_kind[want]
                if children[i].astType == 'constant':
                    children[i] = ASTNode('constant', kind, children[i].value)
                else:
                    opname = "cast"
                    children[i] = ASTNode('op', kind, opname, [children[i]])
    else:
        value = ast.value
        children = ast.children
    return ASTNode(ast.astType, ast.astKind, value,
                   [typeCompileAst(c) for c in children])


class Register(object):
    """Abstraction for a register in the VM.

    Members:
    node          -- the AST node this corresponds to
    temporary     -- True if this isn't an input or output
    immediate     -- not a register, but an immediate value
    n             -- the physical register number.
                     None if no number assigned yet.
    """

    def __init__(self, astnode, temporary=False):
        self.node = astnode
        self.temporary = temporary
        self.immediate = False
        self.n = None

    def __str__(self):
        if self.temporary:
            name = 'Temporary'
        else:
            name = 'Register'
        return '%s(%s, %s, %s)' % (name, self.node.astType,
                                   self.node.astKind, self.n,)

    def __repr__(self):
        return self.__str__()


class Immediate(Register):
    """Representation of an immediate (integer) operand, instead of
    a register.
    """

    def __init__(self, astnode):
        Register.__init__(self, astnode)
        self.immediate = True

    def __str__(self):
        return 'Immediate(%d)' % (self.node.value,)


def stringToExpression(s, types, context):
    """Given a string, convert it to a tree of ExpressionNode's.
    """
    old_ctx = expressions._context.get_current_context()
    try:
        expressions._context.set_new_context(context)
        # first compile to a code object to determine the names
        if context.get('truediv', False):
            flags = __future__.division.compiler_flag
        else:
            flags = 0
        c = compile(s, '<expr>', 'eval', flags)
        # make VariableNode's for the names
        names = {}
        for name in c.co_names:
            if name == "None":
                names[name] = None
            elif name == "True":
                names[name] = True
            elif name == "False":
                names[name] = False
            else:
                t = types.get(name, default_type)
                names[name] = expressions.VariableNode(name, type_to_kind[t])
        names.update(expressions.functions)
        # now build the expression
        ex = eval(c, names)
        if expressions.isConstant(ex):
            ex = expressions.ConstantNode(ex, expressions.getKind(ex))
        elif not isinstance(ex, expressions.ExpressionNode):
            raise TypeError("unsupported expression type: %s" % type(ex))
    finally:
        expressions._context.set_new_context(old_ctx)
    return ex


def isReduction(ast):
    return ast.value.startswith(b'sum_') or ast.value.startswith(b'prod_')


def getInputOrder(ast, input_order=None):
    """Derive the input order of the variables in an expression.
    """
    variables = {}
    for a in ast.allOf('variable'):
        variables[a.value] = a
    variable_names = set(variables.keys())

    if input_order:
        if variable_names != set(input_order):
            raise ValueError(
                "input names (%s) don't match those found in expression (%s)"
                % (input_order, variable_names))

        ordered_names = input_order
    else:
        ordered_names = list(variable_names)
        ordered_names.sort()
    ordered_variables = [variables[v] for v in ordered_names]
    return ordered_variables


def convertConstantToKind(x, kind):
    # Exception for 'float' types that will return the NumPy float32 type
    if kind == 'float':
        return numpy.float32(x)
    return kind_to_type[kind](x)


def getConstants(ast):
    const_map = {}
    for a in ast.allOf('constant'):
        const_map[(a.astKind, a.value)] = a
    ordered_constants = const_map.keys()
    ordered_constants.sort()
    constants_order = [const_map[v] for v in ordered_constants]
    constants = [convertConstantToKind(a.value, a.astKind)
                 for a in constants_order]
    return constants_order, constants


def sortNodesByOrder(nodes, order):
    order_map = {}
    for i, (_, v, _) in enumerate(order):
        order_map[v] = i
    dec_nodes = [(order_map[n.value], n) for n in nodes]
    dec_nodes.sort()
    return [a[1] for a in dec_nodes]


def assignLeafRegisters(inodes, registerMaker):
    """Assign new registers to each of the leaf nodes.
    """
    leafRegisters = {}
    for node in inodes:
        key = node.key()
        if key in leafRegisters:
            node.reg = leafRegisters[key]
        else:
            node.reg = leafRegisters[key] = registerMaker(node)


def assignBranchRegisters(inodes, registerMaker):
    """Assign temporary registers to each of the branch nodes.
    """
    for node in inodes:
        node.reg = registerMaker(node, temporary=True)


def collapseDuplicateSubtrees(ast):
    """Common subexpression elimination.
    """
    seen = {}
    aliases = []
    for a in ast.allOf('op'):
        if a in seen:
            target = seen[a]
            a.astType = 'alias'
            a.value = target
            a.children = ()
            aliases.append(a)
        else:
            seen[a] = a
    # Set values and registers so optimizeTemporariesAllocation
    # doesn't get confused
    for a in aliases:
        while a.value.astType == 'alias':
            a.value = a.value.value
    return aliases


def optimizeTemporariesAllocation(ast):
    """Attempt to minimize the number of temporaries needed, by
    reusing old ones.
    """
    nodes = [n for n in ast.postorderWalk() if n.reg.temporary]
    users_of = dict((n.reg, set()) for n in nodes)

    node_regs = dict((n, set(c.reg for c in n.children if c.reg.temporary))
                     for n in nodes)
    if nodes and nodes[-1] is not ast:
        nodes_to_check = nodes + [ast]
    else:
        nodes_to_check = nodes
    for n in nodes_to_check:
        for c in n.children:
            if c.reg.temporary:
                users_of[c.reg].add(n)

    unused = dict([(tc, set()) for tc in scalar_constant_kinds])
    for n in nodes:
        for c in n.children:
            reg = c.reg
            if reg.temporary:
                users = users_of[reg]
                users.discard(n)
                if not users:
                    unused[reg.node.astKind].add(reg)
        if unused[n.astKind]:
            reg = unused[n.astKind].pop()
            users_of[reg] = users_of[n.reg]
            n.reg = reg


def setOrderedRegisterNumbers(order, start):
    """Given an order of nodes, assign register numbers.
    """
    for i, node in enumerate(order):
        node.reg.n = start + i
    return start + len(order)


def setRegisterNumbersForTemporaries(ast, start):
    """Assign register numbers for temporary registers, keeping track of
    aliases and handling immediate operands.
    """
    seen = 0
    signature = ''
    aliases = []
    for node in ast.postorderWalk():
        if node.astType == 'alias':
            aliases.append(node)
            node = node.value
        if node.reg.immediate:
            node.reg.n = node.value
            continue
        reg = node.reg
        if reg.n is None:
            reg.n = start + seen
            seen += 1
            signature += reg.node.typecode()
    for node in aliases:
        node.reg = node.value.reg
    return start + seen, signature


def convertASTtoThreeAddrForm(ast):
    """Convert an AST to a three address form.

    Three address form is (op, reg1, reg2, reg3), where reg1 is the
    destination of the result of the instruction.

    I suppose this should be called three register form, but three
    address form is found in compiler theory.
    """
    return [(node.value, node.reg) + tuple([c.reg for c in node.children])
            for node in ast.allOf('op')]


def compileThreeAddrForm(program):
    """Given a three address form of the program, compile it a string that
    the VM understands.
    """

    def nToChr(reg):
        if reg is None:
            return b'\xff'
        elif reg.n < 0:
            raise ValueError("negative value for register number %s" % reg.n)
        else:
            if sys.version_info[0] < 3:
                return chr(reg.n)
            else:
                # int.to_bytes is not available in Python < 3.2
                #return reg.n.to_bytes(1, sys.byteorder)
                return bytes([reg.n])

    def quadrupleToString(opcode, store, a1=None, a2=None):
        cop = chr(interpreter.opcodes[opcode]).encode('ascii')
        cs = nToChr(store)
        ca1 = nToChr(a1)
        ca2 = nToChr(a2)
        return cop + cs + ca1 + ca2

    def toString(args):
        while len(args) < 4:
            args += (None,)
        opcode, store, a1, a2 = args[:4]
        s = quadrupleToString(opcode, store, a1, a2)
        l = [s]
        args = args[4:]
        while args:
            s = quadrupleToString(b'noop', *args[:3])
            l.append(s)
            args = args[3:]
        return b''.join(l)

    prog_str = b''.join([toString(t) for t in program])
    return prog_str


context_info = [
    ('optimization', ('none', 'moderate', 'aggressive'), 'aggressive'),
    ('truediv', (False, True, 'auto'), 'auto')
]


def getContext(kwargs, frame_depth=1):
    d = kwargs.copy()
    context = {}
    for name, allowed, default in context_info:
        value = d.pop(name, default)
        if value in allowed:
            context[name] = value
        else:
            raise ValueError("'%s' must be one of %s" % (name, allowed))

    if d:
        raise ValueError("Unknown keyword argument '%s'" % d.popitem()[0])
    if context['truediv'] == 'auto':
        caller_globals = sys._getframe(frame_depth + 1).f_globals
        context['truediv'] = \
            caller_globals.get('division', None) == __future__.division

    return context


def precompile(ex, signature=(), context={}):
    """Compile the expression to an intermediate form.
    """
    types = dict(signature)
    input_order = [name for (name, type_) in signature]

    if isinstance(ex, (str, unicode)):
        ex = stringToExpression(ex, types, context)

    # the AST is like the expression, but the node objects don't have
    # any odd interpretations

    ast = expressionToAST(ex)

    if ex.astType != 'op':
        ast = ASTNode('op', value='copy', astKind=ex.astKind, children=(ast,))

    ast = typeCompileAst(ast)

    aliases = collapseDuplicateSubtrees(ast)

    assignLeafRegisters(ast.allOf('raw'), Immediate)
    assignLeafRegisters(ast.allOf('variable', 'constant'), Register)
    assignBranchRegisters(ast.allOf('op'), Register)

    # assign registers for aliases
    for a in aliases:
        a.reg = a.value.reg

    input_order = getInputOrder(ast, input_order)
    constants_order, constants = getConstants(ast)

    if isReduction(ast):
        ast.reg.temporary = False

    optimizeTemporariesAllocation(ast)

    ast.reg.temporary = False
    r_output = 0
    ast.reg.n = 0

    r_inputs = r_output + 1
    r_constants = setOrderedRegisterNumbers(input_order, r_inputs)
    r_temps = setOrderedRegisterNumbers(constants_order, r_constants)
    r_end, tempsig = setRegisterNumbersForTemporaries(ast, r_temps)

    threeAddrProgram = convertASTtoThreeAddrForm(ast)
    input_names = tuple([a.value for a in input_order])
    signature = ''.join(type_to_typecode[types.get(x, default_type)]
                        for x in input_names)
    return threeAddrProgram, signature, tempsig, constants, input_names


def NumExpr(ex, signature=(), **kwargs):
    """
    Compile an expression built using E.<variable> variables to a function.

    ex can also be specified as a string "2*a+3*b".

    The order of the input variables and their types can be specified using the
    signature parameter, which is a list of (name, type) pairs.

    Returns a `NumExpr` object containing the compiled function.
    """
    # NumExpr can be called either directly by the end-user, in which case
    # kwargs need to be sanitized by getContext, or by evaluate,
    # in which case kwargs are in already sanitized.
    # In that case frame_depth is wrong (it should be 2) but it doesn't matter
    # since it will not be used (because truediv='auto' has already been
    # translated to either True or False).

    context = getContext(kwargs, frame_depth=1)
    threeAddrProgram, inputsig, tempsig, constants, input_names = \
        precompile(ex, signature, context)
    program = compileThreeAddrForm(threeAddrProgram)
    return interpreter.NumExpr(inputsig.encode('ascii'),
                               tempsig.encode('ascii'),
                               program, constants, input_names)


def disassemble(nex):
    """
    Given a NumExpr object, return a list which is the program disassembled.
    """
    rev_opcodes = {}
    for op in interpreter.opcodes:
        rev_opcodes[interpreter.opcodes[op]] = op
    r_constants = 1 + len(nex.signature)
    r_temps = r_constants + len(nex.constants)

    def getArg(pc, offset):
        if sys.version_info[0] < 3:
            arg = ord(nex.program[pc + offset])
            op = rev_opcodes.get(ord(nex.program[pc]))
        else:
            arg = nex.program[pc + offset]
            op = rev_opcodes.get(nex.program[pc])
        try:
            code = op.split(b'_')[1][offset - 1]
        except IndexError:
            return None
        if sys.version_info[0] > 2:
            # int.to_bytes is not available in Python < 3.2
            #code = code.to_bytes(1, sys.byteorder)
            code = bytes([code])
        if arg == 255:
            return None
        if code != b'n':
            if arg == 0:
                return b'r0'
            elif arg < r_constants:
                return ('r%d[%s]' % (arg, nex.input_names[arg - 1])).encode('ascii')
            elif arg < r_temps:
                return ('c%d[%s]' % (arg, nex.constants[arg - r_constants])).encode('ascii')
            else:
                return ('t%d' % (arg,)).encode('ascii')
        else:
            return arg

    source = []
    for pc in range(0, len(nex.program), 4):
        if sys.version_info[0] < 3:
            op = rev_opcodes.get(ord(nex.program[pc]))
        else:
            op = rev_opcodes.get(nex.program[pc])
        dest = getArg(pc, 1)
        arg1 = getArg(pc, 2)
        arg2 = getArg(pc, 3)
        source.append((op, dest, arg1, arg2))
    return source


def getType(a):
    kind = a.dtype.kind
    if kind == 'b':
        return bool
    if kind in 'iu':
        if a.dtype.itemsize > 4:
            return long_  # ``long`` is for integers of more than 32 bits
        if kind == 'u' and a.dtype.itemsize == 4:
            return long_  # use ``long`` here as an ``int`` is not enough
        return int_
    if kind == 'f':
        if a.dtype.itemsize > 4:
            return double  # ``double`` is for floats of more than 32 bits
        return float
    if kind == 'c':
        return complex
    if kind == 'S':
        return bytes
    raise ValueError("unkown type %s" % a.dtype.name)


def getExprNames(text, context):
    ex = stringToExpression(text, {}, context)
    ast = expressionToAST(ex)
    input_order = getInputOrder(ast, None)
    #try to figure out if vml operations are used by expression
    if not use_vml:
        ex_uses_vml = False
    else:
        for node in ast.postorderWalk():
            if node.astType == 'op' \
                    and node.value in ['sin', 'cos', 'exp', 'log',
                                       'expm1', 'log1p',
                                       'pow', 'div',
                                       'sqrt', 'inv',
                                       'sinh', 'cosh', 'tanh',
                                       'arcsin', 'arccos', 'arctan',
                                       'arccosh', 'arcsinh', 'arctanh',
                                       'arctan2', 'abs']:
                ex_uses_vml = True
                break
        else:
            ex_uses_vml = False

    return [a.value for a in input_order], ex_uses_vml


# Dictionaries for caching variable names and compiled expressions
_names_cache = CacheDict(256)
_numexpr_cache = CacheDict(256)


def evaluate(ex, local_dict=None, global_dict=None,
             out=None, order='K', casting='safe', **kwargs):
    """Evaluate a simple array expression element-wise, using the new iterator.

    ex is a string forming an expression, like "2*a+3*b". The values for "a"
    and "b" will by default be taken from the calling function's frame
    (through use of sys._getframe()). Alternatively, they can be specifed
    using the 'local_dict' or 'global_dict' arguments.

    Parameters
    ----------

    local_dict : dictionary, optional
        A dictionary that replaces the local operands in current frame.

    global_dict : dictionary, optional
        A dictionary that replaces the global operands in current frame.

    out : NumPy array, optional
        An existing array where the outcome is going to be stored.  Care is
        required so that this array has the same shape and type than the
        actual outcome of the computation.  Useful for avoiding unnecessary
        new array allocations.

    order : {'C', 'F', 'A', or 'K'}, optional
        Controls the iteration order for operands. 'C' means C order, 'F'
        means Fortran order, 'A' means 'F' order if all the arrays are
        Fortran contiguous, 'C' order otherwise, and 'K' means as close to
        the order the array elements appear in memory as possible.  For
        efficient computations, typically 'K'eep order (the default) is
        desired.

    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur when making a copy or
        buffering.  Setting this to 'unsafe' is not recommended, as it can
        adversely affect accumulations.

          * 'no' means the data types should not be cast at all.
          * 'equiv' means only byte-order changes are allowed.
          * 'safe' means only casts which can preserve values are allowed.
          * 'same_kind' means only safe casts or casts within a kind,
            like float64 to float32, are allowed.
          * 'unsafe' means any data conversions may be done.
    """
    if not isinstance(ex, (str, unicode)):
        raise ValueError("must specify expression as a string")
    # Get the names for this expression
    context = getContext(kwargs, frame_depth=1)
    expr_key = (ex, tuple(sorted(context.items())))
    if expr_key not in _names_cache:
        _names_cache[expr_key] = getExprNames(ex, context)
    names, ex_uses_vml = _names_cache[expr_key]
    # Get the arguments based on the names.
    call_frame = sys._getframe(1)
    if local_dict is None:
        local_dict = call_frame.f_locals
    if global_dict is None:
        global_dict = call_frame.f_globals

    arguments = []
    for name in names:
        try:
            a = local_dict[name]
        except KeyError:
            a = global_dict[name]
        arguments.append(numpy.asarray(a))

    # Create a signature
    signature = [(name, getType(arg)) for (name, arg) in zip(names, arguments)]

    # Look up numexpr if possible.
    numexpr_key = expr_key + (tuple(signature),)
    try:
        compiled_ex = _numexpr_cache[numexpr_key]
    except KeyError:
        compiled_ex = _numexpr_cache[numexpr_key] = \
            NumExpr(ex, signature, **context)
    kwargs = {'out': out, 'order': order, 'casting': casting,
              'ex_uses_vml': ex_uses_vml}
    return compiled_ex(*arguments, **kwargs)

########NEW FILE########
__FILENAME__ = test_numexpr
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################
from __future__ import absolute_import, print_function

import os
import sys
import platform
import warnings

import numpy
from numpy import (
    array, arange, empty, zeros, int32, int64, uint16, complex_, float64, rec,
    copy, ones_like, where, alltrue, linspace,
    sum, prod, sqrt, fmod,
    sin, cos, tan, arcsin, arccos, arctan, arctan2,
    sinh, cosh, tanh, arcsinh, arccosh, arctanh,
    log, log1p, log10, exp, expm1, conj)
from numpy.testing import (assert_equal, assert_array_equal,
                           assert_array_almost_equal, assert_allclose)
from numpy import shape, allclose, array_equal, ravel, isnan, isinf

import numexpr
from numexpr import E, NumExpr, evaluate, disassemble, use_vml

import unittest

TestCase = unittest.TestCase

double = numpy.double


# Recommended minimum versions
minimum_numpy_version = "1.6"


class test_numexpr(TestCase):
    """Testing with 1 thread"""
    nthreads = 1

    def setUp(self):
        numexpr.set_num_threads(self.nthreads)

    def test_simple(self):
        ex = 2.0 * E.a + 3.0 * E.b * E.c
        sig = [('a', double), ('b', double), ('c', double)]
        func = NumExpr(ex, signature=sig)
        x = func(array([1., 2, 3]), array([4., 5, 6]), array([7., 8, 9]))
        assert_array_equal(x, array([86., 124., 168.]))

    def test_simple_expr_small_array(self):
        func = NumExpr(E.a)
        x = arange(100.0)
        y = func(x)
        assert_array_equal(x, y)

    def test_simple_expr(self):
        func = NumExpr(E.a)
        x = arange(1e6)
        y = func(x)
        assert_array_equal(x, y)

    def test_rational_expr(self):
        func = NumExpr((E.a + 2.0 * E.b) / (1 + E.a + 4 * E.b * E.b))
        a = arange(1e6)
        b = arange(1e6) * 0.1
        x = (a + 2 * b) / (1 + a + 4 * b * b)
        y = func(a, b)
        assert_array_almost_equal(x, y)

    def test_reductions(self):
        # Check that they compile OK.
        assert_equal(disassemble(
            NumExpr("sum(x**2+2, axis=None)", [('x', double)])),
                     [(b'mul_ddd', b't3', b'r1[x]', b'r1[x]'),
                      (b'add_ddd', b't3', b't3', b'c2[2.0]'),
                      (b'sum_ddn', b'r0', b't3', None)])
        assert_equal(disassemble(
            NumExpr("sum(x**2+2, axis=1)", [('x', double)])),
                     [(b'mul_ddd', b't3', b'r1[x]', b'r1[x]'),
                      (b'add_ddd', b't3', b't3', b'c2[2.0]'),
                      (b'sum_ddn', b'r0', b't3', 1)])
        assert_equal(disassemble(
            NumExpr("prod(x**2+2, axis=2)", [('x', double)])),
                     [(b'mul_ddd', b't3', b'r1[x]', b'r1[x]'),
                      (b'add_ddd', b't3', b't3', b'c2[2.0]'),
                      (b'prod_ddn', b'r0', b't3', 2)])
        # Check that full reductions work.
        x = zeros(1e5) + .01  # checks issue #41
        assert_allclose(evaluate("sum(x+2,axis=None)"), sum(x + 2, axis=None))
        assert_allclose(evaluate("sum(x+2,axis=0)"), sum(x + 2, axis=0))
        assert_allclose(evaluate("prod(x,axis=0)"), prod(x, axis=0))

        x = arange(10.0)
        assert_allclose(evaluate("sum(x**2+2,axis=0)"), sum(x ** 2 + 2, axis=0))
        assert_allclose(evaluate("prod(x**2+2,axis=0)"), prod(x ** 2 + 2, axis=0))

        x = arange(100.0)
        assert_allclose(evaluate("sum(x**2+2,axis=0)"), sum(x ** 2 + 2, axis=0))
        assert_allclose(evaluate("prod(x-1,axis=0)"), prod(x - 1, axis=0))
        x = linspace(0.1, 1.0, 2000)
        assert_allclose(evaluate("sum(x**2+2,axis=0)"), sum(x ** 2 + 2, axis=0))
        assert_allclose(evaluate("prod(x-1,axis=0)"), prod(x - 1, axis=0))

        # Check that reductions along an axis work
        y = arange(9.0).reshape(3, 3)
        assert_allclose(evaluate("sum(y**2, axis=1)"), sum(y ** 2, axis=1))
        assert_allclose(evaluate("sum(y**2, axis=0)"), sum(y ** 2, axis=0))
        assert_allclose(evaluate("sum(y**2, axis=None)"), sum(y ** 2, axis=None))
        assert_allclose(evaluate("prod(y**2, axis=1)"), prod(y ** 2, axis=1))
        assert_allclose(evaluate("prod(y**2, axis=0)"), prod(y ** 2, axis=0))
        assert_allclose(evaluate("prod(y**2, axis=None)"), prod(y ** 2, axis=None))
        # Check integers
        x = arange(10.)
        x = x.astype(int)
        assert_allclose(evaluate("sum(x**2+2,axis=0)"), sum(x ** 2 + 2, axis=0))
        assert_allclose(evaluate("prod(x**2+2,axis=0)"), prod(x ** 2 + 2, axis=0))
        # Check longs
        x = x.astype(long)
        assert_allclose(evaluate("sum(x**2+2,axis=0)"), sum(x ** 2 + 2, axis=0))
        assert_allclose(evaluate("prod(x**2+2,axis=0)"), prod(x ** 2 + 2, axis=0))
        # Check complex
        x = x + .1j
        assert_allclose(evaluate("sum(x**2+2,axis=0)"), sum(x ** 2 + 2, axis=0))
        assert_allclose(evaluate("prod(x-1,axis=0)"), prod(x - 1, axis=0))

    def test_in_place(self):
        x = arange(10000.).reshape(1000, 10)
        evaluate("x + 3", out=x)
        assert_equal(x, arange(10000.).reshape(1000, 10) + 3)
        y = arange(10)
        evaluate("(x - 3) * y + (x - 3)", out=x)
        assert_equal(x, arange(10000.).reshape(1000, 10) * (arange(10) + 1))

    def test_axis(self):
        y = arange(9.0).reshape(3, 3)
        try:
            evaluate("sum(y, axis=2)")
        except ValueError:
            pass
        else:
            raise ValueError("should raise exception!")
        try:
            evaluate("sum(y, axis=-3)")
        except ValueError:
            pass
        else:
            raise ValueError("should raise exception!")
        try:
            # Negative axis are not supported
            evaluate("sum(y, axis=-1)")
        except ValueError:
            pass
        else:
            raise ValueError("should raise exception!")

    def test_r0_reuse(self):
        assert_equal(disassemble(NumExpr("x * x + 2", [('x', double)])),
                     [(b'mul_ddd', b'r0', b'r1[x]', b'r1[x]'),
                      (b'add_ddd', b'r0', b'r0', b'c2[2.0]')])

    def test_str_contains_basic0(self):
        res = evaluate('contains(b"abc", b"ab")')
        assert_equal(res, True)

    def test_str_contains_basic1(self):
        haystack = array([b'abc', b'def', b'xyz', b'x11', b'za'])
        res = evaluate('contains(haystack, b"ab")')
        assert_equal(res, [True, False, False, False, False])

    def test_str_contains_basic2(self):
        haystack = array([b'abc', b'def', b'xyz', b'x11', b'za'])
        res = evaluate('contains(b"abcd", haystack)')
        assert_equal(res, [True, False, False, False, False])

    def test_str_contains_basic3(self):
        haystacks = array(
            [b'abckkk', b'adef', b'xyz', b'x11abcp', b'za', b'abc'])
        needles = array(
            [b'abc', b'def', b'aterr', b'oot', b'zu', b'ab'])
        res = evaluate('contains(haystacks, needles)')
        assert_equal(res, [True, True, False, False, False, True])

    def test_str_contains_basic4(self):
        needles = array(
            [b'abc', b'def', b'aterr', b'oot', b'zu', b'ab c', b' abc',
             b'abc '])
        res = evaluate('contains(b"test abc here", needles)')
        assert_equal(res, [True, False, False, False, False, False, True, True])

    def test_str_contains_basic5(self):
        needles = array(
            [b'abc', b'ab c', b' abc', b' abc ', b'\tabc', b'c h'])
        res = evaluate('contains(b"test abc here", needles)')
        assert_equal(res, [True, False, True, True, False, True])

        # Compare operation of Python 'in' operator with 'contains' using a
        # product of two lists of strings.

    def test_str_contains_listproduct(self):
        from itertools import product

        small = [
            'It w', 'as th', 'e Whit', 'e Rab', 'bit,', ' tro', 'tting',
            ' sl', 'owly', ' back ', 'again,', ' and', ' lo', 'okin', 'g a',
            'nxious', 'ly a', 'bou', 't a', 's it w', 'ent,', ' as i', 'f it',
            ' had l', 'ost', ' some', 'thi', 'ng; a', 'nd ', 'she ', 'heard ',
            'it mut', 'terin', 'g to ', 'its', 'elf ', "'The",
            ' Duch', 'ess! T', 'he ', 'Duches', 's! Oh ', 'my dea', 'r paws',
            '! Oh ', 'my f', 'ur ', 'and ', 'whiske', 'rs! ', 'She', "'ll g",
            'et me', ' ex', 'ecu', 'ted, ', 'as su', 're a', 's f', 'errets',
            ' are f', 'errets', '! Wh', 'ere ', 'CAN', ' I hav', 'e d',
            'roppe', 'd t', 'hem,', ' I wo', 'nder?', "' A", 'lice',
            ' gu', 'essed', ' in a', ' mom', 'ent ', 'tha', 't it w', 'as ',
            'looki', 'ng f', 'or ', 'the fa', 'n and ', 'the', ' pai',
            'r of w', 'hit', 'e kid', ' glo', 'ves', ', and ', 'she ',
            'very g', 'ood', '-na', 'turedl', 'y be', 'gan h', 'unt', 'ing',
            ' about', ' for t', 'hem', ', but', ' they ', 'wer', 'e nowh',
            'ere to', ' be', ' se', 'en--', 'ever', 'ythin', 'g seem', 'ed ',
            'to ', 'have c', 'hang', 'ed ', 'since', ' he', 'r swim', ' in',
            ' the', ' pool,', ' and', ' the g', 'reat ', 'hal', 'l, w', 'ith',
            ' th', 'e gl', 'ass t', 'abl', 'e and ', 'the', ' li', 'ttle',
            ' doo', 'r, ha', 'd v', 'ani', 'shed c', 'omp', 'lete', 'ly.']
        big = [
            'It wa', 's the', ' W', 'hit', 'e ', 'Ra', 'bb', 'it, t', 'ro',
            'tting s', 'lowly', ' back ', 'agai', 'n, and', ' l', 'ookin',
            'g ', 'an', 'xiously', ' about ', 'as it w', 'ent, as', ' if ',
            'it had', ' los', 't ', 'so', 'mething', '; and', ' she h',
            'eard ', 'it ', 'mutteri', 'ng to', ' itself', " 'The ",
            'Duchess', '! ', 'Th', 'e ', 'Duchess', '! Oh m', 'y de',
            'ar paws', '! ', 'Oh my ', 'fu', 'r and w', 'hiskers', "! She'",
            'll ', 'get', ' me ', 'execute', 'd,', ' a', 's ', 'su', 're as ',
            'fe', 'rrets', ' are f', 'errets!', ' Wher', 'e CAN', ' I ha',
            've dro', 'pped t', 'hem', ', I ', 'won', "der?' A",
            'lice g', 'uess', 'ed ', 'in a m', 'omen', 't that', ' i',
            't was l', 'ook', 'ing f', 'or th', 'e ', 'fan and', ' th', 'e p',
            'air o', 'f whit', 'e ki', 'd glove', 's, and ', 'she v', 'ery ',
            'good-na', 'tu', 'redl', 'y be', 'gan hun', 'ti', 'ng abou',
            't for t', 'he', 'm, bu', 't t', 'hey ', 'were n', 'owhere',
            ' to b', 'e s', 'een-', '-eve', 'rythi', 'ng see', 'me', 'd ',
            'to ha', 've', ' c', 'hanged', ' sinc', 'e her s', 'wim ',
            'in the ', 'pool,', ' an', 'd the g', 'rea', 't h', 'all, wi',
            'th the ', 'glas', 's t', 'able an', 'd th', 'e littl', 'e door,',
            ' had va', 'ni', 'shed co', 'mpletel', 'y.']
        p = list(product(small, big))
        python_in = [x[0] in x[1] for x in p]
        a = [x[0].encode() for x in p]
        b = [x[1].encode() for x in p]
        res = [bool(x) for x in evaluate('contains(b, a)')]
        assert_equal(res, python_in)

    def test_str_contains_withemptystr1(self):
        withemptystr = array([b'abc', b'def', b''])
        res = evaluate('contains(b"abcd", withemptystr)')
        assert_equal(res, [True, False, True])

    def test_str_contains_withemptystr2(self):
        withemptystr = array([b'abc', b'def', b''])
        res = evaluate('contains(withemptystr, b"")')
        assert_equal(res, [True, True, True])


class test_numexpr2(test_numexpr):
    """Testing with 2 threads"""
    nthreads = 2


class test_evaluate(TestCase):
    def test_simple(self):
        a = array([1., 2., 3.])
        b = array([4., 5., 6.])
        c = array([7., 8., 9.])
        x = evaluate("2*a + 3*b*c")
        assert_array_equal(x, array([86., 124., 168.]))

    def test_simple_expr_small_array(self):
        x = arange(100.0)
        y = evaluate("x")
        assert_array_equal(x, y)

    def test_simple_expr(self):
        x = arange(1e6)
        y = evaluate("x")
        assert_array_equal(x, y)

    # Test for issue #37
    if sys.version_info[0] < 3:
        # In python 3 '/' perforns true division, not integer division.
        # Integer division '//' is still not suppoerted by numexpr
        def test_zero_div(self):
            x = arange(100, dtype='i4')
            y = evaluate("1/x")
            x2 = zeros(100, dtype='i4')
            x2[1] = 1
            assert_array_equal(x2, y)

    # Test for issue #22
    def test_true_div(self):
        x = arange(10, dtype='i4')
        assert_array_equal(evaluate("x/2"), x / 2)
        assert_array_equal(evaluate("x/2", truediv=False), x / 2)
        assert_array_equal(evaluate("x/2", truediv='auto'), x / 2)
        assert_array_equal(evaluate("x/2", truediv=True), x / 2.0)

    def test_left_shift(self):
        x = arange(10, dtype='i4')
        assert_array_equal(evaluate("x<<2"), x << 2)

    def test_right_shift(self):
        x = arange(10, dtype='i4')
        assert_array_equal(evaluate("x>>2"), x >> 2)

    # PyTables uses __nonzero__ among ExpressionNode objects internally
    # so this should be commented out for the moment.  See #24.
    def test_boolean_operator(self):
        x = arange(10, dtype='i4')
        try:
            evaluate("(x > 1) and (x < 9)")
        except TypeError:
            pass
        else:
            raise ValueError("should raise exception!")

    def test_rational_expr(self):
        a = arange(1e6)
        b = arange(1e6) * 0.1
        x = (a + 2 * b) / (1 + a + 4 * b * b)
        y = evaluate("(a + 2*b) / (1 + a + 4*b*b)")
        assert_array_almost_equal(x, y)

    def test_complex_expr(self):
        def complex(a, b):
            c = zeros(a.shape, dtype=complex_)
            c.real = a
            c.imag = b
            return c

        a = arange(1e4)
        b = arange(1e4) ** 1e-5
        z = a + 1j * b
        x = z.imag
        x = sin(complex(a, b)).real + z.imag
        y = evaluate("sin(complex(a, b)).real + z.imag")
        assert_array_almost_equal(x, y)

    def test_complex_strides(self):
        a = arange(100).reshape(10, 10)[::2]
        b = arange(50).reshape(5, 10)
        assert_array_equal(evaluate("a+b"), a + b)
        c = empty([10], dtype=[('c1', int32), ('c2', uint16)])
        c['c1'] = arange(10)
        c['c2'].fill(0xaaaa)
        c1 = c['c1']
        a0 = a[0]
        assert_array_equal(evaluate("c1"), c1)
        assert_array_equal(evaluate("a0+c1"), a0 + c1)

    def test_broadcasting(self):
        a = arange(100).reshape(10, 10)[::2]
        c = arange(10)
        d = arange(5).reshape(5, 1)
        assert_array_equal(evaluate("a+c"), a + c)
        assert_array_equal(evaluate("a+d"), a + d)
        expr = NumExpr("2.0*a+3.0*c", [('a', double), ('c', double)])
        assert_array_equal(expr(a, c), 2.0 * a + 3.0 * c)

    def test_all_scalar(self):
        a = 3.
        b = 4.
        assert_allclose(evaluate("a+b"), a + b)
        expr = NumExpr("2*a+3*b", [('a', double), ('b', double)])
        assert_equal(expr(a, b), 2 * a + 3 * b)

    def test_run(self):
        a = arange(100).reshape(10, 10)[::2]
        b = arange(10)
        expr = NumExpr("2*a+3*b", [('a', double), ('b', double)])
        assert_array_equal(expr(a, b), expr.run(a, b))

    def test_illegal_value(self):
        a = arange(3)
        try:
            evaluate("a < [0, 0, 0]")
        except TypeError:
            pass
        else:
            self.fail()

    if 'sparc' not in platform.machine():
        # Execution order set here so as to not use too many threads
        # during the rest of the execution.  See #33 for details.
        def test_changing_nthreads_00_inc(self):
            a = linspace(-1, 1, 1e6)
            b = ((.25 * a + .75) * a - 1.5) * a - 2
            for nthreads in range(1, 7):
                numexpr.set_num_threads(nthreads)
                c = evaluate("((.25*a + .75)*a - 1.5)*a - 2")
                assert_array_almost_equal(b, c)

        def test_changing_nthreads_01_dec(self):
            a = linspace(-1, 1, 1e6)
            b = ((.25 * a + .75) * a - 1.5) * a - 2
            for nthreads in range(6, 1, -1):
                numexpr.set_num_threads(nthreads)
                c = evaluate("((.25*a + .75)*a - 1.5)*a - 2")
                assert_array_almost_equal(b, c)


tests = [
    ('MISC', ['b*c+d*e',
              '2*a+3*b',
              '-a',
              'sinh(a)',
              '2*a + (cos(3)+5)*sinh(cos(b))',
              '2*a + arctan2(a, b)',
              'arcsin(0.5)',
              'where(a != 0.0, 2, a)',
              'where(a > 10, b < a, b > a)',
              'where((a-10).real != 0.0, a, 2)',
              '0.25 * (a < 5) + 0.33 * (a >= 5)',
              'cos(1+1)',
              '1+1',
              '1',
              'cos(a2)',
    ])]

optests = []
for op in list('+-*/%') + ['**']:
    optests.append("(a+1) %s (b+3)" % op)
    optests.append("3 %s (b+3)" % op)
    optests.append("(a+1) %s 4" % op)
    optests.append("2 %s (b+3)" % op)
    optests.append("(a+1) %s 2" % op)
    optests.append("(a+1) %s -1" % op)
    optests.append("(a+1) %s 0.5" % op)
    # Check divisions and modulus by zero (see ticket #107)
    optests.append("(a+1) %s 0" % op)
tests.append(('OPERATIONS', optests))

cmptests = []
for op in ['<', '<=', '==', '>=', '>', '!=']:
    cmptests.append("a/2+5 %s b" % op)
    cmptests.append("a/2+5 %s 7" % op)
    cmptests.append("7 %s b" % op)
    cmptests.append("7.0 %s 5" % op)
tests.append(('COMPARISONS', cmptests))

func1tests = []
for func in ['copy', 'ones_like', 'sqrt',
             'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan',
             'sinh', 'cosh', 'tanh', 'arcsinh', 'arccosh', 'arctanh',
             'log', 'log1p', 'log10', 'exp', 'expm1', 'abs', 'conj']:
    func1tests.append("a + %s(b+c)" % func)
tests.append(('1_ARG_FUNCS', func1tests))

func2tests = []
for func in ['arctan2', 'fmod']:
    func2tests.append("a + %s(b+c, d+1)" % func)
    func2tests.append("a + %s(b+c, 1)" % func)
    func2tests.append("a + %s(1, d+1)" % func)
tests.append(('2_ARG_FUNCS', func2tests))

powtests = []
# n = -1, 0.5, 2, 4 already handled in section "OPERATIONS"
for n in (-7, -2.5, -1.5, -1.3, -.5, 0, 0.0, 1, 2.3, 2.5, 3):
    powtests.append("(a+1)**%s" % n)
tests.append(('POW_TESTS', powtests))


def equal(a, b, exact):
    if array_equal(a, b):
        return True

    if hasattr(a, 'dtype') and a.dtype in ['f4', 'f8']:
        nnans = isnan(a).sum()
        if nnans > 0:
            # For results containing NaNs, just check that the number
            # of NaNs is the same in both arrays.  This check could be
            # made more exhaustive, but checking element by element in
            # python space is very expensive in general.
            return nnans == isnan(b).sum()
        ninfs = isinf(a).sum()
        if ninfs > 0:
            # Ditto for Inf's
            return ninfs == isinf(b).sum()
    if exact:
        return (shape(a) == shape(b)) and alltrue(ravel(a) == ravel(b), axis=0)
    else:
        if hasattr(a, 'dtype') and a.dtype == 'f4':
            atol = 1e-5  # Relax precission for special opcodes, like fmod
        else:
            atol = 1e-8
        return (shape(a) == shape(b) and
                allclose(ravel(a), ravel(b), atol=atol))


class Skip(Exception): pass


def test_expressions():
    test_no = [0]

    def make_test_method(a, a2, b, c, d, e, x, expr,
                         test_scalar, dtype, optimization, exact, section):
        this_locals = locals()

        def method():
            # We don't want to listen at RuntimeWarnings like
            # "overflows" or "divide by zero" in plain eval().
            warnings.simplefilter("ignore")
            npval = eval(expr, globals(), this_locals)
            warnings.simplefilter("always")
            npval = eval(expr, globals(), this_locals)
            try:
                neval = evaluate(expr, local_dict=this_locals,
                                 optimization=optimization)
                assert equal(npval, neval, exact), """%r
(test_scalar=%r, dtype=%r, optimization=%r, exact=%r,
 npval=%r (%r - %r)\n neval=%r (%r - %r))""" % (expr, test_scalar, dtype.__name__,
                                                optimization, exact,
                                                npval, type(npval), shape(npval),
                                                neval, type(neval), shape(neval))
            except AssertionError:
                raise
            except NotImplementedError:
                print('%r not implemented for %s (scalar=%d, opt=%s)'
                      % (expr, dtype.__name__, test_scalar, optimization))
            except:
                print('numexpr error for expression %r' % (expr,))
                raise

        method.description = ('test_expressions(%s, test_scalar=%r, '
                              'dtype=%r, optimization=%r, exact=%r)') \
                             % (expr, test_scalar, dtype.__name__, optimization, exact)
        test_no[0] += 1
        method.__name__ = 'test_scalar%d_%s_%s_%s_%04d' % (test_scalar,
                                                           dtype.__name__,
                                                           optimization.encode('ascii'),
                                                           section.encode('ascii'),
                                                           test_no[0])
        return method

    x = None
    for test_scalar in (0, 1, 2):
        for dtype in (int, long, numpy.float32, double, complex):
            array_size = 100
            a = arange(2 * array_size, dtype=dtype)[::2]
            a2 = zeros([array_size, array_size], dtype=dtype)
            b = arange(array_size, dtype=dtype) / array_size
            c = arange(array_size, dtype=dtype)
            d = arange(array_size, dtype=dtype)
            e = arange(array_size, dtype=dtype)
            if dtype == complex:
                a = a.real
                for x in [a2, b, c, d, e]:
                    x += 1j
                    x *= 1 + 1j
            if test_scalar == 1:
                a = a[array_size // 2]
            if test_scalar == 2:
                b = b[array_size // 2]
            for optimization, exact in [
                ('none', False), ('moderate', False), ('aggressive', False)]:
                for section_name, section_tests in tests:
                    for expr in section_tests:
                        if (dtype == complex and
                            ('<' in expr or '>' in expr or '%' in expr
                             or "arctan2" in expr or "fmod" in expr)):
                            # skip complex comparisons or functions not
                            # defined in complex domain.
                            continue
                        if (dtype in (int, long) and test_scalar and
                                    expr == '(a+1) ** -1'):
                            continue

                        m = make_test_method(a, a2, b, c, d, e, x,
                                             expr, test_scalar, dtype,
                                             optimization, exact,
                                             section_name)
                        yield m


class test_int64(TestCase):
    def test_neg(self):
        a = array([2 ** 31 - 1, 2 ** 31, 2 ** 32, 2 ** 63 - 1], dtype=int64)
        res = evaluate('-a')
        assert_array_equal(res, [1 - 2 ** 31, -(2 ** 31), -(2 ** 32), 1 - 2 ** 63])
        self.assertEqual(res.dtype.name, 'int64')


class test_int32_int64(TestCase):
    if sys.version_info[0] < 2:
        # no long literals in python 3
        def test_small_long(self):
            # Small longs should not be downgraded to ints.
            res = evaluate('42L')
            assert_array_equal(res, 42)
            self.assertEqual(res.dtype.name, 'int64')

    def test_small_int(self):
        # Small ints (32-bit ones) should not be promoted to longs.
        res = evaluate('2')
        assert_array_equal(res, 2)
        self.assertEqual(res.dtype.name, 'int32')

    def test_big_int(self):
        # Big ints should be promoted to longs.
        res = evaluate('2**40')
        assert_array_equal(res, 2 ** 40)
        self.assertEqual(res.dtype.name, 'int64')

    def test_long_constant_promotion(self):
        int32array = arange(100, dtype='int32')
        itwo = numpy.int32(2)
        ltwo = numpy.int64(2)
        res = int32array * 2
        res32 = evaluate('int32array * itwo')
        res64 = evaluate('int32array * ltwo')
        assert_array_equal(res, res32)
        assert_array_equal(res, res64)
        self.assertEqual(res32.dtype.name, 'int32')
        self.assertEqual(res64.dtype.name, 'int64')

    def test_int64_array_promotion(self):
        int32array = arange(100, dtype='int32')
        int64array = arange(100, dtype='int64')
        respy = int32array * int64array
        resnx = evaluate('int32array * int64array')
        assert_array_equal(respy, resnx)
        self.assertEqual(resnx.dtype.name, 'int64')


class test_uint32_int64(TestCase):
    def test_small_uint32(self):
        # Small uint32 should not be downgraded to ints.
        a = numpy.uint32(42)
        res = evaluate('a')
        assert_array_equal(res, 42)
        self.assertEqual(res.dtype.name, 'int64')

    def test_uint32_constant_promotion(self):
        int32array = arange(100, dtype='int32')
        stwo = numpy.int32(2)
        utwo = numpy.uint32(2)
        res = int32array * utwo
        res32 = evaluate('int32array * stwo')
        res64 = evaluate('int32array * utwo')
        assert_array_equal(res, res32)
        assert_array_equal(res, res64)
        self.assertEqual(res32.dtype.name, 'int32')
        self.assertEqual(res64.dtype.name, 'int64')

    def test_int64_array_promotion(self):
        uint32array = arange(100, dtype='uint32')
        int64array = arange(100, dtype='int64')
        respy = uint32array * int64array
        resnx = evaluate('uint32array * int64array')
        assert_array_equal(respy, resnx)
        self.assertEqual(resnx.dtype.name, 'int64')


class test_strings(TestCase):
    BLOCK_SIZE1 = 128
    BLOCK_SIZE2 = 8
    str_list1 = [b'foo', b'bar', b'', b'  ']
    str_list2 = [b'foo', b'', b'x', b' ']
    str_nloops = len(str_list1) * (BLOCK_SIZE1 + BLOCK_SIZE2 + 1)
    str_array1 = array(str_list1 * str_nloops)
    str_array2 = array(str_list2 * str_nloops)
    str_constant = b'doodoo'

    def test_null_chars(self):
        str_list = [
            b'\0\0\0', b'\0\0foo\0', b'\0\0foo\0b', b'\0\0foo\0b\0',
            b'foo\0', b'foo\0b', b'foo\0b\0', b'foo\0bar\0baz\0\0']
        for s in str_list:
            r = evaluate('s')
            self.assertEqual(s, r.tostring())  # check *all* stored data

    def test_compare_copy(self):
        sarr = self.str_array1
        expr = 'sarr'
        res1 = eval(expr)
        res2 = evaluate(expr)
        assert_array_equal(res1, res2)

    def test_compare_array(self):
        sarr1 = self.str_array1
        sarr2 = self.str_array2
        expr = 'sarr1 >= sarr2'
        res1 = eval(expr)
        res2 = evaluate(expr)
        assert_array_equal(res1, res2)

    def test_compare_variable(self):
        sarr = self.str_array1
        svar = self.str_constant
        expr = 'sarr >= svar'
        res1 = eval(expr)
        res2 = evaluate(expr)
        assert_array_equal(res1, res2)

    def test_compare_constant(self):
        sarr = self.str_array1
        expr = 'sarr >= %r' % self.str_constant
        res1 = eval(expr)
        res2 = evaluate(expr)
        assert_array_equal(res1, res2)

    def test_add_string_array(self):
        sarr1 = self.str_array1
        sarr2 = self.str_array2
        expr = 'sarr1 + sarr2'
        self.assert_missing_op('add_sss', expr, locals())

    def test_add_numeric_array(self):
        sarr = self.str_array1
        narr = arange(len(sarr), dtype='int32')
        expr = 'sarr >= narr'
        self.assert_missing_op('ge_bsi', expr, locals())

    def assert_missing_op(self, op, expr, local_dict):
        msg = "expected NotImplementedError regarding '%s'" % op
        try:
            evaluate(expr, local_dict)
        except NotImplementedError, nie:
            if "'%s'" % op not in nie.args[0]:
                self.fail(msg)
        else:
            self.fail(msg)

    def test_compare_prefix(self):
        # Check comparing two strings where one is a prefix of the
        # other.
        for s1, s2 in [(b'foo', b'foobar'), (b'foo', b'foo\0bar'),
                       (b'foo\0a', b'foo\0bar')]:
            self.assertTrue(evaluate('s1 < s2'))
            self.assertTrue(evaluate('s1 <= s2'))
            self.assertTrue(evaluate('~(s1 == s2)'))
            self.assertTrue(evaluate('~(s1 >= s2)'))
            self.assertTrue(evaluate('~(s1 > s2)'))

        # Check for NumPy array-style semantics in string equality.
        s1, s2 = b'foo', b'foo\0\0'
        self.assertTrue(evaluate('s1 == s2'))


# Case for testing selections in fields which are aligned but whose
# data length is not an exact multiple of the length of the record.
# The following test exposes the problem only in 32-bit machines,
# because in 64-bit machines 'c2' is unaligned.  However, this should
# check most platforms where, while not unaligned, 'len(datatype) >
# boundary_alignment' is fullfilled.
class test_irregular_stride(TestCase):
    def test_select(self):
        f0 = arange(10, dtype=int32)
        f1 = arange(10, dtype=float64)

        irregular = rec.fromarrays([f0, f1])

        f0 = irregular['f0']
        f1 = irregular['f1']

        i0 = evaluate('f0 < 5')
        i1 = evaluate('f1 < 5')

        assert_array_equal(f0[i0], arange(5, dtype=int32))
        assert_array_equal(f1[i1], arange(5, dtype=float64))


# Cases for testing arrays with dimensions that can be zero.
class test_zerodim(TestCase):
    def test_zerodim1d(self):
        a0 = array([], dtype=int32)
        a1 = array([], dtype=float64)

        r0 = evaluate('a0 + a1')
        r1 = evaluate('a0 * a1')

        assert_array_equal(r0, a1)
        assert_array_equal(r1, a1)

    def test_zerodim3d(self):
        a0 = array([], dtype=int32).reshape(0, 2, 4)
        a1 = array([], dtype=float64).reshape(0, 2, 4)

        r0 = evaluate('a0 + a1')
        r1 = evaluate('a0 * a1')

        assert_array_equal(r0, a1)
        assert_array_equal(r1, a1)


# Case test for threads
class test_threading(TestCase):
    def test_thread(self):
        import threading

        class ThreadTest(threading.Thread):
            def run(self):
                a = arange(3)
                assert_array_equal(evaluate('a**3'), array([0, 1, 8]))

        test = ThreadTest()
        test.start()


# The worker function for the subprocess (needs to be here because Windows
# has problems pickling nested functions with the multiprocess module :-/)
def _worker(qout=None):
    ra = numpy.arange(1e3)
    rows = evaluate('ra > 0')
    #print "Succeeded in evaluation!\n"
    if qout is not None:
        qout.put("Done")


# Case test for subprocesses (via multiprocessing module)
class test_subprocess(TestCase):
    def test_multiprocess(self):
        try:
            import multiprocessing as mp
        except ImportError:
            return
        # Check for two threads at least
        numexpr.set_num_threads(2)
        #print "**** Running from main process:"
        _worker()
        #print "**** Running from subprocess:"
        qout = mp.Queue()
        ps = mp.Process(target=_worker, args=(qout,))
        ps.daemon = True
        ps.start()

        result = qout.get()
        #print result


def print_versions():
    """Print the versions of software that numexpr relies on."""
    if numpy.__version__ < minimum_numpy_version:
        print("*Warning*: NumPy version is lower than recommended: %s < %s" % \
              (numpy.__version__, minimum_numpy_version))
    print('-=' * 38)
    print("Numexpr version:   %s" % numexpr.__version__)
    print("NumPy version:     %s" % numpy.__version__)
    print('Python version:    %s' % sys.version)
    if os.name == 'posix':
        (sysname, nodename, release, version, machine) = os.uname()
        print('Platform:          %s-%s' % (sys.platform, machine))
    print("AMD/Intel CPU?     %s" % numexpr.is_cpu_amd_intel)
    print("VML available?     %s" % use_vml)
    if use_vml:
        print("VML/MKL version:   %s" % numexpr.get_vml_version())
    print("Number of threads used by default: %d "
          "(out of %d detected cores)" % (numexpr.nthreads, numexpr.ncores))
    print('-=' * 38)


def test():
    """
    Run all the tests in the test suite.
    """

    print_versions()
    return unittest.TextTestRunner().run(suite())


test.__test__ = False


def suite():
    import unittest
    import platform as pl

    theSuite = unittest.TestSuite()
    niter = 1

    class TestExpressions(TestCase):
        pass

    def add_method(func):
        def method(self):
            return func()

        setattr(TestExpressions, func.__name__,
                method.__get__(None, TestExpressions))

    for func in test_expressions():
        add_method(func)

    for n in range(niter):
        theSuite.addTest(unittest.makeSuite(test_numexpr))
        if 'sparc' not in platform.machine():
            theSuite.addTest(unittest.makeSuite(test_numexpr2))
        theSuite.addTest(unittest.makeSuite(test_evaluate))
        theSuite.addTest(unittest.makeSuite(TestExpressions))
        theSuite.addTest(unittest.makeSuite(test_int32_int64))
        theSuite.addTest(unittest.makeSuite(test_uint32_int64))
        theSuite.addTest(unittest.makeSuite(test_strings))
        theSuite.addTest(
            unittest.makeSuite(test_irregular_stride))
        theSuite.addTest(unittest.makeSuite(test_zerodim))

        # multiprocessing module is not supported on Hurd/kFreeBSD
        if (pl.system().lower() not in ('gnu', 'gnu/kfreebsd')):
            theSuite.addTest(unittest.makeSuite(test_subprocess))

        # I need to put this test after test_subprocess because
        # if not, the test suite locks immediately before test_subproces.
        # This only happens with Windows, so I suspect of a subtle bad
        # interaction with threads and subprocess :-/
        theSuite.addTest(unittest.makeSuite(test_threading))

    return theSuite


if __name__ == '__main__':
    print_versions()
    unittest.main(defaultTest='suite')
#    suite = suite()
#    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = utils
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

import os
import subprocess

from numexpr.interpreter import _set_num_threads
from numexpr import use_vml

if use_vml:
    from numexpr.interpreter import (
        _get_vml_version, _set_vml_accuracy_mode, _set_vml_num_threads)


def get_vml_version():
    """Get the VML/MKL library version."""
    if use_vml:
        return _get_vml_version()
    else:
        return None


def set_vml_accuracy_mode(mode):
    """
    Set the accuracy mode for VML operations.

    The `mode` parameter can take the values:
    - 'high': high accuracy mode (HA), <1 least significant bit
    - 'low': low accuracy mode (LA), typically 1-2 least significant bits
    - 'fast': enhanced performance mode (EP)
    - None: mode settings are ignored

    This call is equivalent to the `vmlSetMode()` in the VML library.
    See:

    http://www.intel.com/software/products/mkl/docs/webhelp/vml/vml_DataTypesAccuracyModes.html

    for more info on the accuracy modes.

    Returns old accuracy settings.
    """
    if use_vml:
        acc_dict = {None: 0, 'low': 1, 'high': 2, 'fast': 3}
        acc_reverse_dict = {1: 'low', 2: 'high', 3: 'fast'}
        if mode not in acc_dict.keys():
            raise ValueError(
                "mode argument must be one of: None, 'high', 'low', 'fast'")
        retval = _set_vml_accuracy_mode(acc_dict.get(mode, 0))
        return acc_reverse_dict.get(retval)
    else:
        return None


def set_vml_num_threads(nthreads):
    """
    Suggests a maximum number of threads to be used in VML operations.

    This function is equivalent to the call
    `mkl_domain_set_num_threads(nthreads, MKL_VML)` in the MKL
    library.  See:

    http://www.intel.com/software/products/mkl/docs/webhelp/support/functn_mkl_domain_set_num_threads.html

    for more info about it.
    """
    if use_vml:
        _set_vml_num_threads(nthreads)


def set_num_threads(nthreads):
    """
    Sets a number of threads to be used in operations.

    Returns the previous setting for the number of threads.

    During initialization time Numexpr sets this number to the number
    of detected cores in the system (see `detect_number_of_cores()`).

    If you are using Intel's VML, you may want to use
    `set_vml_num_threads(nthreads)` to perform the parallel job with
    VML instead.  However, you should get very similar performance
    with VML-optimized functions, and VML's parallelizer cannot deal
    with common expresions like `(x+1)*(x-2)`, while Numexpr's one
    can.
    """
    old_nthreads = _set_num_threads(nthreads)
    return old_nthreads


def detect_number_of_cores():
    """
    Detects the number of cores on a system. Cribbed from pp.
    """
    # Linux, Unix and MacOS:
    if hasattr(os, "sysconf"):
        if "SC_NPROCESSORS_ONLN" in os.sysconf_names:
            # Linux & Unix:
            ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
            if isinstance(ncpus, int) and ncpus > 0:
                return ncpus
        else:  # OSX:
            return int(subprocess.check_output(["sysctl", "-n", "hw.ncpu"]))
    # Windows:
    if os.environ.has_key("NUMBER_OF_PROCESSORS"):
        ncpus = int(os.environ["NUMBER_OF_PROCESSORS"]);
        if ncpus > 0:
            return ncpus
    return 1  # Default


class CacheDict(dict):
    """
    A dictionary that prevents itself from growing too much.
    """

    def __init__(self, maxentries):
        self.maxentries = maxentries
        super(CacheDict, self).__init__(self)

    def __setitem__(self, key, value):
        # Protection against growing the cache too much
        if len(self) > self.maxentries:
            # Remove a 10% of (arbitrary) elements from the cache
            entries_to_remove = self.maxentries // 10
            for k in self.keys()[:entries_to_remove]:
                super(CacheDict, self).__delitem__(k)
        super(CacheDict, self).__setitem__(key, value)


########NEW FILE########
__FILENAME__ = version
###################################################################
#  Numexpr - Fast numerical array expression evaluator for NumPy.
#
#      License: MIT
#      Author:  See AUTHORS.txt
#
#  See LICENSE.txt and LICENSES/*.txt for details about copyright and
#  rights to use.
####################################################################

version = '2.4.1'
release = False

if not release:
    version += '.dev'
    import os

    svn_version_file = os.path.join(os.path.dirname(__file__),
                                    '__svn_version__.py')
    if os.path.isfile(svn_version_file):
        import imp

        svn = imp.load_module('numexpr.__svn_version__',
                              open(svn_version_file),
                              svn_version_file,
                              ('.py', 'U', 1))
        version += svn.version

########NEW FILE########
