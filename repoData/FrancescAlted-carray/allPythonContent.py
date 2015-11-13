__FILENAME__ = arange
import numpy as np
import carray as ca
from time import time

N = 1e8
dtype = 'i4'

start, stop, step = 5, N, 4

t0 = time()
a = np.arange(start, stop, step, dtype=dtype)
print "Time numpy.arange() --> %.3f" % (time()-t0)

t0 = time()
ac = ca.arange(start, stop, step, dtype=dtype)
print "Time carray.arange() --> %.3f" % (time()-t0)

print "ac-->", `ac`

#assert(np.all(a == ac))

########NEW FILE########
__FILENAME__ = concat
# Benchmark that compares the times for concatenating arrays with
# compressed arrays vs plain numpy arrays.  The 'numpy' and 'concat'
# styles are for regular numpy arrays, while 'carray' is for carrays.
#
# Call this benchmark as:
#
# python bench/concat.py style
#
# where `style` can be any of 'numpy', 'concat' or 'carray'
#
# You can modify other parameters from the command line if you want:
#
# python bench/concat.py style arraysize nchunks nrepeats clevel
#

import sys, math
import numpy
from numpy.testing import assert_array_equal, assert_array_almost_equal
import carray as ca
import time

def concat(data):
    tlen = sum(x.shape[0] for x in data)
    alldata = numpy.empty((tlen,))
    pos = 0
    for x in data:
        step = x.shape[0]
        alldata[pos:pos+step] = x
        pos += step

    return alldata

def append(data, clevel):
    alldata = ca.carray(data[0], cparams=ca.cparams(clevel))
    for carr in data[1:]:
        alldata.append(carr)

    return alldata

if len(sys.argv) < 2:
    print "Pass at least one of these styles: 'numpy', 'concat' or 'carray' "
    sys.exit(1)

style = sys.argv[1]
if len(sys.argv) == 2:
    N, K, T, clevel = (1000000, 10, 3, 1)
else:
    N,K,T = [int(arg) for arg in sys.argv[2:5]]
    if len(sys.argv) > 5:
        clevel = int(sys.argv[5])
    else:
        clevel = 0

# The next datasets allow for very high compression ratios
a = [numpy.arange(N, dtype='f8') for _ in range(K)]
print("problem size: (%d) x %d = 10^%g" % (N, K, math.log10(N*K)))

t = time.time()
if style == 'numpy':
    for _ in xrange(T):
        r = numpy.concatenate(a, 0)
elif style == 'concat':
    for _ in xrange(T):
        r = concat(a)
elif style == 'carray':
    for _ in xrange(T):
        r = append(a, clevel)

t = time.time() - t
print('time for concat: %.3fs' % (t / T))

if style == 'carray':
    size = r.cbytes
else:
    size = r.size*r.dtype.itemsize
print("size of the final container: %.3f MB" % (size / float(1024*1024)) )

########NEW FILE########
__FILENAME__ = ctable-query
# Benchmark to compare the times for querying ctable objects.  Numexpr
# is needed in order to execute this.  A comparison with SQLite3 and
# PyTables (if installed) is also done.

import sys, math
import os, os.path
import subprocess
import getopt

import sqlite3
import numpy as np
import carray as ca
from time import time

NR = 1e6      # the number of rows
NC = 1000     # the number of columns
mv = 1e10     # the mean value for entries (sig digits = 17 - log10(mv))
clevel = 3    # the compression level
show = False  # show statistics
# The query for a ctable
squery = "(f2>.9) & ((f8>.3) & (f8<.4))"  # the ctable query
# The query for a recarray
nquery = "(t['f2']>.9) & ((t['f8']>.3) & (t['f8']<.4))"  # for a recarray
# A time reference
tref = 0


def show_rss(explain):
    "Show the used time and RSS memory (only works for Linux 2.6.x)."
    global tref
    # Build the command to obtain memory info
    newtref = time()
    print "Time (%20s) --> %.3f" % (explain, newtref-tref),
    tref = newtref
    if show:
        cmd = "cat /proc/%s/status" % os.getpid()
        sout = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout
        for line in sout:
            if line.startswith("VmRSS:"):
                vmrss = int(line.split()[1]) // 1024
        print "\t(Resident memory: %d MB)" % vmrss
    else:
        print

def enter():
    global tref
    tref = time()

def after_create(mess=""):
    global tref
    if mess: mess = ", "+mess
    show_rss("creation"+mess)

def after_query(mess=""):
    global tref
    if mess: mess = ", "+mess
    show_rss("query"+mess)


def test_numpy():
    enter()
    t = np.fromiter((mv+np.random.rand(NC)-mv for i in xrange(int(NR))),
                    dtype=dt)
    after_create()
    out = np.fromiter(((row['f1'],row['f3']) for row in t[eval(nquery)]),
                      dtype="f8,f8")
    after_query()
    return out


def test_numexpr():
    import numexpr as ne
    enter()
    t = np.fromiter((mv+np.random.rand(NC)-mv for i in xrange(int(NR))),
                    dtype=dt)
    after_create()

    map_field = dict(("f%s"%i, t["f%s"%i]) for i in range(NC))
    out = np.fromiter(((row['f1'],row['f3']) for row in
                       t[ne.evaluate(squery, map_field)]),
                      dtype="f8,f8")
    after_query()
    return out


def test_ctable(clevel):
    enter()
    tc = ca.fromiter((mv+np.random.rand(NC)-mv for i in xrange(int(NR))),
                     dtype=dt,
                     cparams=ca.cparams(clevel),
                     count=int(NR))
    after_create()

    out = np.fromiter((row for row in tc.where(squery, 'f1,f3')),
                      dtype="f8,f8")
    after_query()
    return out


def test_sqlite():
    enter()
    sqlquery = "(f2>.9) and ((f8>.3) and (f8<.4))"  # the query

    con = sqlite3.connect(":memory:")

    # Create table
    fields = "(%s)" % ",".join(["f%d real"%i for i in range(NC)])
    con.execute("create table bench %s" % fields)

    # Insert a NR rows of data
    vals = "(%s)" % ",".join(["?" for i in range(NC)])
    with con:
        con.executemany("insert into bench values %s" % vals,
                        (mv+np.random.rand(NC)-mv for i in xrange(int(NR))))
    after_create()

    out = np.fromiter(
        (row for row in con.execute(
        "select f1, f3 from bench where %s" % sqlquery)),
        dtype="f8,f8")
    after_query("non-indexed")

    # Create indexes
    con.execute("create index f1idx on bench (f1)")
    con.execute("create index f2idx on bench (f8)")
    after_create("index")

    out = np.fromiter(
        (row for row in con.execute(
        "select f1, f3 from bench where %s" % sqlquery)),
        dtype="f8,f8")
    after_query("indexed")

    return out


if __name__=="__main__":
    global dt

    usage = """usage: %s [-s] [-m method] [-c ncols] [-r nrows] [-z clevel]
            -s show memory statistics (only for Linux)
            -m select the method: "ctable" (def.), "numpy", "numexpr", "sqlite"
            -c the number of columns in table (def. 100)
            -r the number of rows in table (def. 1e6)
            -z the compression level (def. 3)
            \n""" % sys.argv[0]

    try:
        opts, pargs = getopt.getopt(sys.argv[1:], 'sc:r:m:z:')
    except:
        sys.stderr.write(usage)
        sys.exit(1)

    method = "ctable"
    # Get the options
    for option in opts:
        if option[0] == '-s':
            if "linux" in sys.platform:
                show = True
        elif option[0] == '-m':
            method = option[1]
        elif option[0] == '-c':
            NC = int(option[1])
        elif option[0] == '-r':
            NR = float(option[1])
        elif option[0] == '-z':
            clevel = int(option[1])

    np.random.seed(12)  # so as to get reproducible results
    # The dtype for tables
    #dt = np.dtype("f8,"*NC)             # aligned fields
    dt = np.dtype("f8,"*(NC-1)+"i1")    # unaligned fields

    if method == "numexpr":
        mess = "numexpr (+numpy)"
    elif method == "ctable":
        mess = "ctable (clevel=%d)" % clevel
    elif method == "sqlite":
        mess = "sqlite (in-memory)"
    else:
        mess = method
    print "########## Checking method: %s ############" % mess

    print "Querying with %g rows and %d cols" % (NR, NC)
    print "Building database.  Wait please..."

    if method == "ctable":
        out = test_ctable(clevel)
    elif method == "numpy":
        out = test_numpy()
    elif method == "numexpr":
        out = test_numexpr()
    elif method == "sqlite":
        out = test_sqlite()
    print "Number of selected elements in query:", len(out)

########NEW FILE########
__FILENAME__ = eval-profile
# Benchmark to compare the times for computing expressions by using
# eval() on carray/numpy arrays.  Numexpr is needed in order to
# execute this.

import math
import numpy as np
import numexpr as ne
import carray as ca
from time import time

def compute_carray(sexpr, clevel, kernel):
    # Uncomment the next for disabling threading
    #ca.set_nthreads(1)
    #ca.blosc_set_nthreads(1)
    print("*** carray (using compression clevel = %d):" % clevel)
    x = cx  # comment this for using numpy arrays in inputs
    t0 = time()
    cout = ca.eval(sexpr, kernel=kernel, cparams=ca.cparams(clevel))
    print("Time for ca.eval (%s) --> %.3f" % (kernel, time()-t0,))
    #print(", cratio (out): %.1f" % (cout.nbytes / float(cout.cbytes)))
    #print "cout-->", repr(cout)


if __name__=="__main__":

    N = 1e8       # the number of elements in x
    clevel = 9    # the compression level
    sexpr = "(x+1)<0"
    sexpr = "(((.25*x + .75)*x - 1.5)*x - 2)<0"
    #sexpr = "(((.25*x + .75)*x - 1.5)*x - 2)"
    doprofile = 0

    print("Creating inputs...")
    x = np.arange(N)
    #x = np.linspace(0,100,N)
    cx = ca.carray(x, cparams=ca.cparams(clevel))

    print("Evaluating '%s' with 10^%d points" % (sexpr, int(math.log10(N))))

    t0 = time()
    cout = ne.evaluate(sexpr)
    print "Time for numexpr --> %.3f" % (time()-t0,)

    if doprofile:
        import pstats
        import cProfile as prof
        prof.run('compute_carray(sexpr, clevel=clevel, kernel="numexpr")',
        #prof.run('compute_carray(sexpr, clevel=clevel, kernel="python")',
                 'eval.prof')
        stats = pstats.Stats('eval.prof')
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(20)
    else:
        compute_carray(sexpr, clevel=clevel, kernel="numexpr")
        #compute_carray(sexpr, clevel=clevel, kernel="python")

########NEW FILE########
__FILENAME__ = eval
# Benchmark to compare the times for computing expressions by using
# eval() on carray/numpy arrays.  Numexpr is needed in order to
# execute this.

import math
import numpy as np
import numexpr as ne
import carray as ca
from time import time

N = 1e7       # the number of elements in x
clevel = 9    # the compression level
sexprs = [ "(x+1)<0",
           "(2*x**2+.3*y**2+z+1)<0",
           "((.25*x + .75)*x - 1.5)*x - 2",
           "(((.25*x + .75)*x - 1.5)*x - 2)<0",
           ]

# Initial dataset
#x = np.arange(N)
x = np.linspace(0,100,N)

doprofile = True

def compute_ref(sexpr):
    t0 = time()
    out = eval(sexpr)
    print "Time for plain numpy --> %.3f" % (time()-t0,)

    t0 = time()
    out = ne.evaluate(sexpr)
    print "Time for numexpr (numpy) --> %.3f" % (time()-t0,)

def compute_carray(sexpr, clevel, kernel):
    # Uncomment the next for disabling threading
    # Maybe due to some contention between Numexpr and Blosc?
    # ca.set_nthreads(ca.ncores//2)
    print "*** carray (using compression clevel = %d):" % clevel
    if clevel > 0:
        x, y, z = cx, cy, cz
    t0 = time()
    cout = ca.eval(sexpr, kernel=kernel, cparams=ca.cparams(clevel))
    print "Time for ca.eval (%s) --> %.3f" % (kernel, time()-t0,),
    print ", cratio (out): %.1f" % (cout.nbytes / float(cout.cbytes))
    #print "cout-->", repr(cout)


if __name__=="__main__":

    print "Creating inputs..."

    cparams = ca.cparams(clevel)

    y = x.copy()
    z = x.copy()
    cx = ca.carray(x, cparams=cparams)
    cy = ca.carray(y, cparams=cparams)
    cz = ca.carray(z, cparams=cparams)

    for sexpr in sexprs:
        print "Evaluating '%s' with 10^%d points" % (sexpr, int(math.log10(N)))
        compute_ref(sexpr)
        for kernel in "python", "numexpr":
            compute_carray(sexpr, clevel=0, kernel=kernel)
        if doprofile:
            import pstats
            import cProfile as prof
            #prof.run('compute_carray(sexpr, clevel=clevel, kernel="numexpr")',
            prof.run('compute_carray(sexpr, clevel=0, kernel="numexpr")',
            #prof.run('compute_carray(sexpr, clevel=clevel, kernel="python")',
            #prof.run('compute_carray(sexpr, clevel=0, kernel="python")',
                     'eval.prof')
            stats = pstats.Stats('eval.prof')
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            stats.print_stats(20)
        else:
            for kernel in "python", "numexpr":
                compute_carray(sexpr, clevel=clevel, kernel=kernel)

########NEW FILE########
__FILENAME__ = expression
# Benchmark to compare the times for computing expressions by using
# ctable objects.  Numexpr is needed in order to execute this.

import math
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import numexpr as ne
import carray as ca
from time import time

N = 1e7       # the number of elements in x
clevel = 9    # the compression level
#sexpr = "(x+1)<0"  # the expression to compute
#sexpr = "(2*x**3+.3*y**2+z+1)<0"  # the expression to compute
#sexpr = "((.25*x + .75)*x - 1.5)*x - 2"  # a computer-friendly polynomial
sexpr = "(((.25*x + .75)*x - 1.5)*x - 2)<0"  # a computer-friendly polynomial

print "Creating inputs..."

cparams = ca.cparams(clevel)

x = np.arange(N)
#x = np.linspace(0,100,N)
cx = ca.carray(x, cparams=cparams)
if 'y' not in sexpr:
    t = ca.ctable((cx,), names=['x'])
else:
    y = np.arange(N)
    z = np.arange(N)
    cy = ca.carray(y, cparams=cparams)
    cz = ca.carray(z, cparams=cparams)
    t = ca.ctable((cx, cy, cz), names=['x','y','z'])

print "Evaluating '%s' with 10^%d points" % (sexpr, int(math.log10(N)))

t0 = time()
out = eval(sexpr)
print "Time for plain numpy--> %.3f" % (time()-t0,)

t0 = time()
out = ne.evaluate(sexpr)
print "Time for numexpr (numpy)--> %.3f" % (time()-t0,)

# Uncomment the next for disabling threading
#ne.set_num_threads(1)
#ca.blosc_set_nthreads(1)
# Seems that this works better if we dividw the number of cores by 2.
# Maybe due to some contention between Numexpr and Blosc?
#ca.set_nthreads(ca.ncores//2)

for kernel in "python", "numexpr":
    t0 = time()
    #cout = t.eval(sexpr, kernel=kernel, cparams=cparams)
    cout = t.eval(sexpr, cparams=cparams)
    print "Time for ctable (%s) --> %.3f" % (kernel, time()-t0,)
    #print "cout-->", repr(cout)

#assert_array_equal(out, cout, "Arrays are not equal")

########NEW FILE########
__FILENAME__ = fill
import numpy as np
import carray as ca
from time import time

N = 1e8
dtype = 'i4'

t0 = time()
a = np.ones(N, dtype=dtype)
print "Time numpy.ones() --> %.4f" % (time()-t0)

t0 = time()
ac = ca.fill(N, dtype=dtype, dflt=1)
#ac = ca.carray(a)
print "Time carray.fill(dflt=1) --> %.4f" % (time()-t0)

print "ac-->", `ac`

t0 = time()
sa = a.sum()
print "Time a.sum() --> %.4f" % (time()-t0)

t0 = time()
sac = ac.sum()
print "Time ac.sum() --> %.4f" % (time()-t0)


assert(sa == sac)

########NEW FILE########
__FILENAME__ = fromiter
# Benchmark for assessing the `fromiter()` speed.

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import carray as ca
import itertools as it
from time import time

N = int(1e6)  # the number of elements in x
clevel = 2    # the compression level

print "Creating inputs with %d elements..." % N

x = xrange(N)    # not a true iterable, but can be converted
y = xrange(1,N+1)
z = xrange(2,N+2)

print "Starting benchmark now for creating arrays..."
# Create a ndarray
#x = (i for i in xrange(N))    # true iterable
t0 = time()
out = np.fromiter(x, dtype='f8', count=N)
print "Time for array--> %.3f" % (time()-t0,)
print "out-->", len(out)

#ca.set_num_threads(ca.ncores//2)

# Create a carray
#x = (i for i in xrange(N))    # true iterable
t0 = time()
cout = ca.fromiter(x, dtype='f8', count=N, cparams=ca.cparams(clevel))
print "Time for carray--> %.3f" % (time()-t0,)
print "cout-->", len(cout)
assert_array_equal(out, cout, "Arrays are not equal")

# Create a carray (with unknown size)
#x = (i for i in xrange(N))    # true iterable
t0 = time()
cout = ca.fromiter(x, dtype='f8', count=-1, cparams=ca.cparams(clevel))
print "Time for carray (count=-1)--> %.3f" % (time()-t0,)
print "cout-->", len(cout)
assert_array_equal(out, cout, "Arrays are not equal")

# Retrieve from a structured ndarray
gen = ((i,j,k) for i,j,k in it.izip(x,y,z))
t0 = time()
out = np.fromiter(gen, dtype="f8,f8,f8", count=N)
print "Time for structured array--> %.3f" % (time()-t0,)
print "out-->", len(out)

# Retrieve from a ctable
gen = ((i,j,k) for i,j,k in it.izip(x,y,z))
t0 = time()
cout = ca.fromiter(gen, dtype="f8,f8,f8", count=N)
print "Time for ctable--> %.3f" % (time()-t0,)
print "out-->", len(cout)
assert_array_equal(out, cout[:], "Arrays are not equal")

# Retrieve from a ctable (with unknown size)
gen = ((i,j,k) for i,j,k in it.izip(x,y,z))
t0 = time()
cout = ca.fromiter(gen, dtype="f8,f8,f8", count=-1)
print "Time for ctable (count=-1)--> %.3f" % (time()-t0,)
print "out-->", len(cout)
assert_array_equal(out, cout[:], "Arrays are not equal")

########NEW FILE########
__FILENAME__ = getitem
# Benchmark for getitem

import numpy as np
import carray as ca
from time import time

N = 1e7       # the number of elements in x
M = 100000    # the elements to get
clevel = 1    # the compression level

print "Creating inputs with %d elements..." % N

cparams = ca.cparams(clevel)

#x = np.arange(N)
x = np.zeros(N, dtype="f8")
y = x.copy()
z = x.copy()
cx = ca.carray(x, cparams=cparams)
cy = cx.copy()
cz = cx.copy()
ct = ca.ctable((cx, cy, cz), names=['x','y','z'])
t = ct[:]

print "Starting benchmark now for getting %d elements..." % M
# Retrieve from a ndarray
t0 = time()
vals = [x[i] for i in xrange(0, M, 3)]
print "Time for array--> %.3f" % (time()-t0,)
print "vals-->", len(vals)

#ca.set_num_threads(ca.ncores//2)

# Retrieve from a carray
t0 = time()
cvals = [cx[i] for i in xrange(0, M, 3)]
#cvals = cx[:M:3][:].tolist()
print "Time for carray--> %.3f" % (time()-t0,)
print "vals-->", len(cvals)
assert vals == cvals

# Retrieve from a structured ndarray
t0 = time()
vals = [t[i] for i in xrange(0, M, 3)]
print "Time for structured array--> %.3f" % (time()-t0,)
print "vals-->", len(vals)

# Retrieve from a ctable
t0 = time()
cvals = [ct[i] for i in xrange(0, M, 3)]
#cvals = ct[:M:3][:].tolist()
print "Time for ctable--> %.3f" % (time()-t0,)
print "vals-->", len(cvals)
assert vals == cvals

########NEW FILE########
__FILENAME__ = iter
# Benchmark to compare times for iterators in generator contexts by
# using carrays vs plain numpy arrays.

import numpy as np
import carray as ca
from time import time

N = 1e6

a = np.arange(N)
b = ca.carray(a)

t0 = time()
#sum1 = sum(a)
sum1 = sum((v for v in a[2::3] if v < 10))
t1 = time()-t0
print "Summing using numpy iterator: %.3f" % t1

t0 = time()
#sum2 = sum(b)
sum2 = sum((v for v in b.iter(2, None, 3) if v < 10))
t2 = time()-t0
print "Summing using carray iterator: %.3f  speedup: %.2f" % (t2, t1/t2)

assert sum1 == sum2, "Summations are not equal!"

########NEW FILE########
__FILENAME__ = iterator
# Benchmark for iterators

import numpy as np
import carray as ca
from time import time

N = 1e7       # the number of elements in x
clevel = 5    # the compression level
sexpr = "(x-1) < 10."  # the expression to compute
#sexpr = "((x-1) % 1000) == 0."  # the expression to compute
#sexpr = "(2*x**3+.3*y**2+z+1)<0"  # the expression to compute

cparams = ca.cparams(clevel)

print "Creating inputs..."

x = np.arange(N)
cx = ca.carray(x, cparams=cparams)
if 'y' not in sexpr:
    ct = ca.ctable((cx,), names=['x'])
else:
    y = np.arange(N)
    z = np.arange(N)
    cy = ca.carray(y, cparams=cparams)
    cz = ca.carray(z, cparams=cparams)
    ct = ca.ctable((cx, cy, cz), names=['x','y','z'])

print "Evaluating...", sexpr
t0 = time()
cbout = ct.eval(sexpr)
print "Time for evaluation--> %.3f" % (time()-t0,)
print "Converting to numy arrays"
bout = cbout[:]
t = ct[:]

t0 = time()
cbool = ca.carray(bout, cparams=cparams)
print "Time for converting boolean--> %.3f" % (time()-t0,)
print "cbool-->", repr(cbool)

t0 = time()
vals = [v for v in cbool.wheretrue()]
print "Time for wheretrue()--> %.3f" % (time()-t0,)
print "vals-->", len(vals)

print "Starting benchmark now..."
# Retrieve from a ndarray
t0 = time()
vals = [v for v in x[bout]]
print "Time for array--> %.3f" % (time()-t0,)
#print "vals-->", len(vals)

#ca.set_num_threads(ca.ncores//2)

# Retrieve from a carray
t0 = time()
#cvals = [v for v in cx[cbout]]
cvals = [v for v in cx.where(cbout)]
print "Time for carray--> %.3f" % (time()-t0,)
#print "vals-->", len(cvals)
assert vals == cvals

# Retrieve from a structured ndarray
t0 = time()
vals = [tuple(v) for v in t[bout]]
print "Time for structured array--> %.3f" % (time()-t0,)
#print "vals-->", len(vals)

# Retrieve from a ctable
t0 = time()
#cvals = [tuple(v) for v in ct[cbout]]
cvals = [v for v in ct.where(cbout)]
print "Time for ctable--> %.3f" % (time()-t0,)
#print "vals-->", len(cvals)
assert vals == cvals

########NEW FILE########
__FILENAME__ = large_carray
## Benchmark to check the creation of an array of length > 2**32 (5e9)

import carray as ca
from time import time

t0 = time()
#cn = ca.zeros(5e9, dtype="i1")
cn = ca.zeros(5e9, dtype="i1", rootdir='large_carray-bench', mode='w')
print "Creation time:", round(time() - t0, 3)
assert len(cn) == int(5e9)

t0 = time()
cn = ca.carray(rootdir='large_carray-bench', mode='a')
print "Re-open time:", round(time() - t0, 3)
print "len(cn)", len(cn)
assert len(cn) == int(5e9)

# Now check some accesses
cn[1] = 1
assert cn[1] == 1
cn[int(2e9)] = 2
assert cn[int(2e9)] == 2
cn[long(3e9)] = 3
assert cn[long(3e9)] == 3
cn[-1] = 4
assert cn[-1] == 4

t0 = time()
assert cn.sum() == 10
print "Sum time:", round(time() - t0, 3)

print "str(carray):", str(cn)
print "repr(carray):", repr(cn)

########NEW FILE########
__FILENAME__ = query
# Benchmark to compare the times for evaluating queries.
# Numexpr is needed in order to execute this.

import math
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import numexpr as ne
import carray as ca
from time import time

N = 1e7       # the number of elements in x
clevel = 5    # the compression level
sexpr = "(x+1)<10"                    # small number of items
#sexpr = "(x+1)<1000000"              # large number
sexpr = "(2*x*x*x+.3*y**2+z+1)<10"    # small number
#sexpr = "(2*x*x*x+.3*y**2+z+1)<1e15"  # medium number
#sexpr = "(2*x*x*x+.3*y**2+z+1)<1e20"  # large number

print "Creating inputs..."

cparams = ca.cparams(clevel)

x = np.arange(N)
cx = ca.carray(x, cparams=cparams)
if 'y' not in sexpr:
    t = ca.ctable((cx,), names=['x'])
else:
    y = np.arange(N)
    z = np.arange(N)
    cy = ca.carray(y, cparams=cparams)
    cz = ca.carray(z, cparams=cparams)
    t = ca.ctable((cx, cy, cz), names=['x','y','z'])
nt = t[:]

print "Querying '%s' with 10^%d points" % (sexpr, int(math.log10(N)))

t0 = time()
out = [r for r in x[eval(sexpr)]]
print "Time for numpy--> %.3f" % (time()-t0,)

t0 = time()
out = [r for r in t[eval(sexpr)]]
print "Time for structured array--> %.3f" % (time()-t0,)

t0 = time()
out = [r for r in cx[sexpr]]
print "Time for carray --> %.3f" % (time()-t0,)

# Uncomment the next for disabling threading
#ne.set_num_threads(1)
#ca.blosc_set_num_threads(1)
# Seems that this works better if we dividw the number of cores by 2.
# Maybe due to some contention between Numexpr and Blosc?
#ca.set_num_threads(ca.ncores//2)

t0 = time()
#cout = t[t.eval(sexpr, cparams=cparams)]
cout = [r for r in t.where(sexpr)]
#cout = [r['x'] for r in t.where(sexpr)]
#cout = [r['y'] for r in t.where(sexpr, colnames=['x', 'y'])]
print "Time for ctable--> %.3f" % (time()-t0,)
print "cout-->", len(cout), cout[:10]

#assert_array_equal(out, cout, "Arrays are not equal")

########NEW FILE########
__FILENAME__ = serialization
import numpy as np
import carray as ca
from time import time

N = 10 * 1000 * 1000
CLEVEL = 5

a = np.linspace(0, 1, N)

t0 = time()
ac = ca.carray(a, cparams=ca.cparams(clevel=CLEVEL))
print "time creation (memory) ->", round(time()-t0, 3)
print "data (memory):", repr(ac)

t0 = time()
b = ca.carray(a, cparams=ca.cparams(clevel=CLEVEL), rootdir='myarray')
b.flush()
print "time creation (disk) ->", round(time()-t0, 3)
#print "meta (disk):", b.read_meta()

t0 = time()
an = np.array(a)
print "time creation (numpy) ->", round(time()-t0, 3)

t0 = time()
c = ca.carray(rootdir='myarray')
print "time open (disk) ->", round(time()-t0, 3)
#print "meta (disk):", c.read_meta()
print "data (disk):", repr(c)

t0 = time()
print sum(ac)
print "time sum (memory, iter) ->", round(time()-t0, 3)

t0 = time()
print sum(c)
print "time sum (disk, iter) ->", round(time()-t0, 3)

t0 = time()
print ca.eval('sum(ac)')
print "time sum (memory, eval) ->", round(time()-t0, 3)

t0 = time()
print ca.eval('sum(c)')
print "time sum (disk, eval) ->", round(time()-t0, 3)

t0 = time()
print ac.sum()
print "time sum (memory, method) ->", round(time()-t0, 3)

t0 = time()
print c.sum()
print "time sum (disk, method) ->", round(time()-t0, 3)

t0 = time()
print a.sum()
print "time sum (numpy, method) ->", round(time()-t0, 3)

########NEW FILE########
__FILENAME__ = sum
import numpy as np
import carray as ca
from time import time

N = 1e8
#a = np.arange(N, dtype='f8')
a = np.random.randint(0,10,N).astype('bool')

t0 = time()
sa = a.sum()
print "Time sum() numpy --> %.3f" % (time()-t0)

t0 = time()
ac = ca.carray(a, cparams=ca.cparams(9))
print "Time carray conv --> %.3f" % (time()-t0)
print "ac-->", `ac`

t0 = time()
sac = ac.sum()
#sac = ac.sum(dtype=np.dtype('i8'))
print "Time sum() carray --> %.3f" % (time()-t0)

# t0 = time()
# sac = sum(i for i in ac)
# print "Time sum() carray (iter) --> %.3f" % (time()-t0)

print "sa, sac-->", sa, sac, type(sa), type(sac)
assert(sa == sac)

########NEW FILE########
__FILENAME__ = zeros
import numpy as np
import carray as ca
from time import time

N = 1e8
dtype = 'i4'

t0 = time()
a = np.zeros(N, dtype=dtype)
print "Time numpy.zeros() --> %.4f" % (time()-t0)

t0 = time()
ac = ca.zeros(N, dtype=dtype)
#ac = ca.carray(a)
print "Time carray.zeros() --> %.4f" % (time()-t0)

print "ac-->", `ac`

#assert(np.all(a == ac))

########NEW FILE########
__FILENAME__ = arrayprint
"""Array printing function

$Id: arrayprint.py,v 1.9 2005/09/13 13:58:44 teoliphant Exp $
"""
__all__ = ["array2string", "set_printoptions", "get_printoptions"]
__docformat__ = 'restructuredtext'

#
# Written by Konrad Hinsen <hinsenk@ere.umontreal.ca>
# last revision: 1996-3-13
# modified by Jim Hugunin   1997-3-3 for repr's and str's (and other details)
# and by Perry Greenfield   2000-4-1 for numarray
# and by Travis Oliphant    2005-8-22 for numpy
# adapted by Francesc Alted 20012-8-18 for carray

import sys
import numpy as np
from numpy.core import numerictypes as _nt
from numpy import maximum, minimum, absolute, not_equal, isnan, isinf
from numpy.core.multiarray import format_longfloat
from numpy.core.fromnumeric import ravel

try:
    from numpy.core.multiarray import datetime_as_string, datetime_data
except ImportError:
    pass


def product(x, y): return x*y

_summaryEdgeItems = 3     # repr N leading and trailing items of each dimension
_summaryThreshold = 1000 # total items > triggers array summarization

_float_output_precision = 8
_float_output_suppress_small = False
_line_width = 75
_nan_str = 'nan'
_inf_str = 'inf'
_formatter = None  # formatting function for array elements

if sys.version_info[0] >= 3:
    from functools import reduce

def set_printoptions(precision=None, threshold=None, edgeitems=None,
                     linewidth=None, suppress=None,
                     nanstr=None, infstr=None,
                     formatter=None):
    """
    Set printing options.

    These options determine the way floating point numbers, arrays and
    other NumPy objects are displayed.

    Parameters
    ----------
    precision : int, optional
        Number of digits of precision for floating point output (default 8).
    threshold : int, optional
        Total number of array elements which trigger summarization
        rather than full repr (default 1000).
    edgeitems : int, optional
        Number of array items in summary at beginning and end of
        each dimension (default 3).
    linewidth : int, optional
        The number of characters per line for the purpose of inserting
        line breaks (default 75).
    suppress : bool, optional
        Whether or not suppress printing of small floating point values
        using scientific notation (default False).
    nanstr : str, optional
        String representation of floating point not-a-number (default nan).
    infstr : str, optional
        String representation of floating point infinity (default inf).
    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are::

            - 'bool'
            - 'int'
            - 'timedelta' : a `numpy.timedelta64`
            - 'datetime' : a `numpy.datetime64`
            - 'float'
            - 'longfloat' : 128-bit floats
            - 'complexfloat'
            - 'longcomplexfloat' : composed of two 128-bit floats
            - 'numpy_str' : types `numpy.string_` and `numpy.unicode_`
            - 'str' : all other strings

        Other keys that can be used to set a group of types at once are::

            - 'all' : sets all types
            - 'int_kind' : sets 'int'
            - 'float_kind' : sets 'float' and 'longfloat'
            - 'complex_kind' : sets 'complexfloat' and 'longcomplexfloat'
            - 'str_kind' : sets 'str' and 'numpystr'

    See Also
    --------
    get_printoptions, set_string_function, array2string

    Notes
    -----
    `formatter` is always reset with a call to `set_printoptions`.

    Examples
    --------
    Floating point precision can be set:

    >>> np.set_printoptions(precision=4)
    >>> print np.array([1.123456789])
    [ 1.1235]

    Long arrays can be summarised:

    >>> np.set_printoptions(threshold=5)
    >>> print np.arange(10)
    [0 1 2 ..., 7 8 9]

    Small results can be suppressed:

    >>> eps = np.finfo(float).eps
    >>> x = np.arange(4.)
    >>> x**2 - (x + eps)**2
    array([ -4.9304e-32,  -4.4409e-16,   0.0000e+00,   0.0000e+00])
    >>> np.set_printoptions(suppress=True)
    >>> x**2 - (x + eps)**2
    array([-0., -0.,  0.,  0.])

    A custom formatter can be used to display array elements as desired:

    >>> np.set_printoptions(formatter={'all':lambda x: 'int: '+str(-x)})
    >>> x = np.arange(3)
    >>> x
    array([int: 0, int: -1, int: -2])
    >>> np.set_printoptions()  # formatter gets reset
    >>> x
    array([0, 1, 2])

    To put back the default options, you can use:

    >>> np.set_printoptions(edgeitems=3,infstr='inf',
    ... linewidth=75, nanstr='nan', precision=8,
    ... suppress=False, threshold=1000, formatter=None)
    """

    global _summaryThreshold, _summaryEdgeItems, _float_output_precision, \
           _line_width, _float_output_suppress_small, _nan_str, _inf_str, \
           _formatter
    if linewidth is not None:
        _line_width = linewidth
    if threshold is not None:
        _summaryThreshold = threshold
    if edgeitems is not None:
        _summaryEdgeItems = edgeitems
    if precision is not None:
        _float_output_precision = precision
    if suppress is not None:
        _float_output_suppress_small = not not suppress
    if nanstr is not None:
        _nan_str = nanstr
    if infstr is not None:
        _inf_str = infstr
    _formatter = formatter

def get_printoptions():
    """
    Return the current print options.

    Returns
    -------
    print_opts : dict
        Dictionary of current print options with keys

          - precision : int
          - threshold : int
          - edgeitems : int
          - linewidth : int
          - suppress : bool
          - nanstr : str
          - infstr : str
          - formatter : dict of callables

        For a full description of these options, see `set_printoptions`.

    See Also
    --------
    set_printoptions, set_string_function

    """
    d = dict(precision=_float_output_precision,
             threshold=_summaryThreshold,
             edgeitems=_summaryEdgeItems,
             linewidth=_line_width,
             suppress=_float_output_suppress_small,
             nanstr=_nan_str,
             infstr=_inf_str,
             formatter=_formatter)
    return d

def _leading_trailing(a):
    import numpy.core.numeric as _nc
    if a.ndim == 1:
        if len(a) > 2*_summaryEdgeItems:
            b = _nc.concatenate((a[:_summaryEdgeItems],
                                     a[-_summaryEdgeItems:]))
        else:
            b = a
    else:
        if len(a) > 2*_summaryEdgeItems:
            l = [_leading_trailing(a[i]) for i in range(
                min(len(a), _summaryEdgeItems))]
            l.extend([_leading_trailing(a[-i]) for i in range(
                min(len(a), _summaryEdgeItems),0,-1)])
        else:
            l = [_leading_trailing(a[i]) for i in range(0, len(a))]
        b = _nc.concatenate(tuple(l))
    return b

def _boolFormatter(x):
    if x:
        return ' True'
    else:
        return 'False'


def repr_format(x):
    return repr(x)

def _array2string(a, max_line_width, precision, suppress_small, separator=' ',
                  prefix="", formatter=None):

    if max_line_width is None:
        max_line_width = _line_width

    if precision is None:
        precision = _float_output_precision

    if suppress_small is None:
        suppress_small = _float_output_suppress_small

    if formatter is None:
        formatter = _formatter

    if a.size > _summaryThreshold:
        summary_insert = "..., "
        data = _leading_trailing(a)
    else:
        summary_insert = ""
        data = ravel(a)

    formatdict = {'bool' : _boolFormatter,
                  'int' : IntegerFormat(data),
                  'float' : FloatFormat(data, precision, suppress_small),
                  'longfloat' : LongFloatFormat(precision),
                  'complexfloat' : ComplexFormat(data, precision,
                                                 suppress_small),
                  'longcomplexfloat' : LongComplexFormat(precision),
                  'datetime' : DatetimeFormat(data),
                  'timedelta' : TimedeltaFormat(data),
                  'numpystr' : repr_format,
                  'str' : str}

    if formatter is not None:
        fkeys = [k for k in formatter.keys() if formatter[k] is not None]
        if 'all' in fkeys:
            for key in formatdict.keys():
                formatdict[key] = formatter['all']
        if 'int_kind' in fkeys:
            for key in ['int']:
                formatdict[key] = formatter['int_kind']
        if 'float_kind' in fkeys:
            for key in ['float', 'longfloat']:
                formatdict[key] = formatter['float_kind']
        if 'complex_kind' in fkeys:
            for key in ['complexfloat', 'longcomplexfloat']:
                formatdict[key] = formatter['complex_kind']
        if 'str_kind' in fkeys:
            for key in ['numpystr', 'str']:
                formatdict[key] = formatter['str_kind']
        for key in formatdict.keys():
            if key in fkeys:
                formatdict[key] = formatter[key]

    try:
        format_function = a._format
        msg = "The `_format` attribute is deprecated in Numpy 2.0 and " \
              "will be removed in 2.1. Use the `formatter` kw instead."
        import warnings
        warnings.warn(msg, DeprecationWarning)
    except AttributeError:
        # find the right formatting function for the array
        dtypeobj = a.dtype.type
        if issubclass(dtypeobj, _nt.bool_):
            format_function = formatdict['bool']
        elif issubclass(dtypeobj, _nt.integer):
            if (hasattr(_nt, "timedelta64") and
                issubclass(dtypeobj, _nt.timedelta64)):
                format_function = formatdict['timedelta']
            else:
                format_function = formatdict['int']
        elif issubclass(dtypeobj, _nt.floating):
            if issubclass(dtypeobj, _nt.longfloat):
                format_function = formatdict['longfloat']
            else:
                format_function = formatdict['float']
        elif issubclass(dtypeobj, _nt.complexfloating):
            if issubclass(dtypeobj, _nt.clongfloat):
                format_function = formatdict['longcomplexfloat']
            else:
                format_function = formatdict['complexfloat']
        elif issubclass(dtypeobj, (_nt.unicode_, _nt.string_)):
            format_function = formatdict['numpystr']
        elif(hasattr(_nt, "datetime64") and
                issubclass(dtypeobj, _nt.datetime64)):
            format_function = formatdict['datetime']
        else:
            format_function = formatdict['str']

    # skip over "["
    next_line_prefix = " "
    # skip over array(
    next_line_prefix += " "*len(prefix)

    lst = _formatArray(a, format_function, len(a.shape), max_line_width,
                       next_line_prefix, separator,
                       _summaryEdgeItems, summary_insert)[:-1]
    return lst

def _convert_arrays(obj):
    import numpy.core.numeric as _nc
    newtup = []
    for k in obj:
        if isinstance(k, _nc.ndarray):
            k = k.tolist()
        elif isinstance(k, tuple):
            k = _convert_arrays(k)
        newtup.append(k)
    return tuple(newtup)


def array2string(a, max_line_width=None, precision=None,
                 suppress_small=None, separator=' ', prefix="",
                 style=repr, formatter=None):
    """
    Return a string representation of an array.

    Parameters
    ----------
    a : ndarray
        Input array.
    max_line_width : int, optional
        The maximum number of columns the string should span. Newline
        characters splits the string appropriately after array elements.
    precision : int, optional
        Floating point precision. Default is the current printing
        precision (usually 8), which can be altered using `set_printoptions`.
    suppress_small : bool, optional
        Represent very small numbers as zero. A number is "very small" if it
        is smaller than the current printing precision.
    separator : str, optional
        Inserted between elements.
    prefix : str, optional
        An array is typically printed as::

          'prefix(' + array2string(a) + ')'

        The length of the prefix string is used to align the
        output correctly.
    style : function, optional
        A function that accepts an ndarray and returns a string.  Used only
        when the shape of `a` is equal to ``()``, i.e. for 0-D arrays.
    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are::

            - 'bool'
            - 'int'
            - 'timedelta' : a `numpy.timedelta64`
            - 'datetime' : a `numpy.datetime64`
            - 'float'
            - 'longfloat' : 128-bit floats
            - 'complexfloat'
            - 'longcomplexfloat' : composed of two 128-bit floats
            - 'numpy_str' : types `numpy.string_` and `numpy.unicode_`
            - 'str' : all other strings

        Other keys that can be used to set a group of types at once are::

            - 'all' : sets all types
            - 'int_kind' : sets 'int'
            - 'float_kind' : sets 'float' and 'longfloat'
            - 'complex_kind' : sets 'complexfloat' and 'longcomplexfloat'
            - 'str_kind' : sets 'str' and 'numpystr'

    Returns
    -------
    array_str : str
        String representation of the array.

    Raises
    ------
    TypeError : if a callable in `formatter` does not return a string.

    See Also
    --------
    array_str, array_repr, set_printoptions, get_printoptions

    Notes
    -----
    If a formatter is specified for a certain type, the `precision` keyword is
    ignored for that type.

    Examples
    --------
    >>> x = np.array([1e-16,1,2,3])
    >>> print np.array2string(x, precision=2, separator=',',
    ...                       suppress_small=True)
    [ 0., 1., 2., 3.]

    >>> x  = np.arange(3.)
    >>> np.array2string(x, formatter={'float_kind':lambda x: "%.2f" % x})
    '[0.00 1.00 2.00]'

    >>> x  = np.arange(3)
    >>> np.array2string(x, formatter={'int':lambda x: hex(x)})
    '[0x0L 0x1L 0x2L]'

    """

    if a.shape == ():
        x = a.item()
        try:
            lst = a._format(x)
            msg = "The `_format` attribute is deprecated in Numpy " \
                  "2.0 and will be removed in 2.1. Use the " \
                  "`formatter` kw instead."
            import warnings
            warnings.warn(msg, DeprecationWarning)
        except AttributeError:
            if isinstance(x, tuple):
                x = _convert_arrays(x)
            lst = style(x)
    elif reduce(product, a.shape) == 0:
        # treat as a null array if any of shape elements == 0
        lst = "[]"
    else:
        lst = _array2string(a, max_line_width, precision, suppress_small,
                            separator, prefix, formatter=formatter)
    return lst

def _extendLine(s, line, word, max_line_len, next_line_prefix):
    if len(line.rstrip()) + len(word.rstrip()) >= max_line_len:
        s += line.rstrip() + "\n"
        line = next_line_prefix
    line += word
    return s, line


def _formatArray(a, format_function, rank, max_line_len,
                 next_line_prefix, separator, edge_items, summary_insert):
    """formatArray is designed for two modes of operation:

    1. Full output

    2. Summarized output

    """
    if rank == 0:
        obj = a.item()
        if isinstance(obj, tuple):
            obj = _convert_arrays(obj)
        return str(obj)

    if summary_insert and 2*edge_items < len(a):
        leading_items, trailing_items, summary_insert1 = \
                       edge_items, edge_items, summary_insert
    else:
        leading_items, trailing_items, summary_insert1 = 0, len(a), ""

    if rank == 1:
        s = ""
        line = next_line_prefix
        for i in xrange(leading_items):
            word = format_function(a[i]) + separator
            s, line = _extendLine(s, line, word, max_line_len, next_line_prefix)

        if summary_insert1:
            s, line = _extendLine(s, line, summary_insert1, max_line_len, next_line_prefix)

        for i in xrange(trailing_items, 1, -1):
            word = format_function(a[-i]) + separator
            s, line = _extendLine(s, line, word, max_line_len, next_line_prefix)

        word = format_function(a[-1])
        s, line = _extendLine(s, line, word, max_line_len, next_line_prefix)
        s += line + "]\n"
        s = '[' + s[len(next_line_prefix):]
    else:
        s = '['
        sep = separator.rstrip()
        for i in xrange(leading_items):
            if i > 0:
                s += next_line_prefix
            s += _formatArray(a[i], format_function, rank-1, max_line_len,
                              " " + next_line_prefix, separator, edge_items,
                              summary_insert)
            s = s.rstrip() + sep.rstrip() + '\n'*max(rank-1,1)

        if summary_insert1:
            s += next_line_prefix + summary_insert1 + "\n"

        for i in xrange(trailing_items, 1, -1):
            if leading_items or i != trailing_items:
                s += next_line_prefix
            s += _formatArray(a[-i], format_function, rank-1, max_line_len,
                              " " + next_line_prefix, separator, edge_items,
                              summary_insert)
            s = s.rstrip() + sep.rstrip() + '\n'*max(rank-1,1)
        if leading_items or trailing_items > 1:
            s += next_line_prefix
        s += _formatArray(a[-1], format_function, rank-1, max_line_len,
                          " " + next_line_prefix, separator, edge_items,
                          summary_insert).rstrip()+']\n'
    return s

class FloatFormat(object):
    def __init__(self, data, precision, suppress_small, sign=False):
        self.precision = precision
        self.suppress_small = suppress_small
        self.sign = sign
        self.exp_format = False
        self.large_exponent = False
        self.max_str_len = 0
        try:
            self.fillFormat(data)
        except (TypeError, NotImplementedError):
            # if reduce(data) fails, this instance will not be called, just
            # instantiated in formatdict.
            pass

    def fillFormat(self, data):
        import numpy.core.numeric as _nc
        errstate = _nc.seterr(all='ignore')
        try:
            special = isnan(data) | isinf(data)
            valid = not_equal(data, 0) & ~special
            non_zero = absolute(data.compress(valid))
            if len(non_zero) == 0:
                max_val = 0.
                min_val = 0.
            else:
                max_val = maximum.reduce(non_zero)
                min_val = minimum.reduce(non_zero)
                if max_val >= 1.e8:
                    self.exp_format = True
                if not self.suppress_small and (min_val < 0.0001
                                           or max_val/min_val > 1000.):
                    self.exp_format = True
        finally:
            _nc.seterr(**errstate)

        if self.exp_format:
            self.large_exponent = 0 < min_val < 1e-99 or max_val >= 1e100
            self.max_str_len = 8 + self.precision
            if self.large_exponent:
                self.max_str_len += 1
            if self.sign:
                format = '%+'
            else:
                format = '%'
            format = format + '%d.%de' % (self.max_str_len, self.precision)
        else:
            format = '%%.%df' % (self.precision,)
            if len(non_zero):
                precision = max([_digits(x, self.precision, format)
                                 for x in non_zero])
            else:
                precision = 0
            precision = min(self.precision, precision)
            self.max_str_len = len(str(int(max_val))) + precision + 2
            if _nc.any(special):
                self.max_str_len = max(self.max_str_len,
                                       len(_nan_str),
                                       len(_inf_str)+1)
            if self.sign:
                format = '%#+'
            else:
                format = '%#'
            format = format + '%d.%df' % (self.max_str_len, precision)

        self.special_fmt = '%%%ds' % (self.max_str_len,)
        self.format = format

    def __call__(self, x, strip_zeros=True):
        import numpy.core.numeric as _nc
        err = _nc.seterr(invalid='ignore')
        try:
            if isnan(x):
                if self.sign:
                    return self.special_fmt % ('+' + _nan_str,)
                else:
                    return self.special_fmt % (_nan_str,)
            elif isinf(x):
                if x > 0:
                    if self.sign:
                        return self.special_fmt % ('+' + _inf_str,)
                    else:
                        return self.special_fmt % (_inf_str,)
                else:
                    return self.special_fmt % ('-' + _inf_str,)
        finally:
            _nc.seterr(**err)

        s = self.format % x
        if self.large_exponent:
            # 3-digit exponent
            expsign = s[-3]
            if expsign == '+' or expsign == '-':
                s = s[1:-2] + '0' + s[-2:]
        elif self.exp_format:
            # 2-digit exponent
            if s[-3] == '0':
                s = ' ' + s[:-3] + s[-2:]
        elif strip_zeros:
            z = s.rstrip('0')
            s = z + ' '*(len(s)-len(z))
        return s


def _digits(x, precision, format):
    s = format % x
    z = s.rstrip('0')
    return precision - len(s) + len(z)


_MAXINT = sys.maxint
_MININT = -sys.maxint-1
class IntegerFormat(object):
    def __init__(self, data):
        try:
            max_str_len = max(len(str(maximum.reduce(data))),
                              len(str(minimum.reduce(data))))
            self.format = '%' + str(max_str_len) + 'd'
        except (TypeError, NotImplementedError):
            # if reduce(data) fails, this instance will not be called, just
            # instantiated in formatdict.
            pass
        except ValueError:
            # this occurs when everything is NA
            pass

    def __call__(self, x):
        if _MININT < x < _MAXINT:
            return self.format % x
        else:
            return "%s" % x

class LongFloatFormat(object):
    # XXX Have to add something to determine the width to use a la FloatFormat
    # Right now, things won't line up properly
    def __init__(self, precision, sign=False):
        self.precision = precision
        self.sign = sign

    def __call__(self, x):
        if isnan(x):
            if self.sign:
                return '+' + _nan_str
            else:
                return ' ' + _nan_str
        elif isinf(x):
            if x > 0:
                if self.sign:
                    return '+' + _inf_str
                else:
                    return ' ' + _inf_str
            else:
                return '-' + _inf_str
        elif x >= 0:
            if self.sign:
                return '+' + format_longfloat(x, self.precision)
            else:
                return ' ' + format_longfloat(x, self.precision)
        else:
            return format_longfloat(x, self.precision)


class LongComplexFormat(object):
    def __init__(self, precision):
        self.real_format = LongFloatFormat(precision)
        self.imag_format = LongFloatFormat(precision, sign=True)

    def __call__(self, x):
        r = self.real_format(x.real)
        i = self.imag_format(x.imag)
        return r + i + 'j'


class ComplexFormat(object):
    def __init__(self, x, precision, suppress_small):
        self.real_format = FloatFormat(x.real, precision, suppress_small)
        self.imag_format = FloatFormat(x.imag, precision, suppress_small,
                                       sign=True)

    def __call__(self, x):
        r = self.real_format(x.real, strip_zeros=False)
        i = self.imag_format(x.imag, strip_zeros=False)
        if not self.imag_format.exp_format:
            z = i.rstrip('0')
            i = z + 'j' + ' '*(len(i)-len(z))
        else:
            i = i + 'j'
        return r + i

class DatetimeFormat(object):
    def __init__(self, x, unit=None,
                timezone=None, casting='same_kind'):
        # Get the unit from the dtype
        if unit is None:
            if x.dtype.kind == 'M':
                unit = datetime_data(x.dtype)[0]
            else:
                unit = 's'

        # If timezone is default, make it 'local' or 'UTC' based on the unit
        if timezone is None:
            # Date units -> UTC, time units -> local
            if unit in ('Y', 'M', 'W', 'D'):
                self.timezone = 'UTC'
            else:
                self.timezone = 'local'
        else:
            self.timezone = timezone
        self.unit = unit
        self.casting = casting

    def __call__(self, x):
        return "'%s'" % datetime_as_string(x,
                                    unit=self.unit,
                                    timezone=self.timezone,
                                    casting=self.casting)

class TimedeltaFormat(object):
    def __init__(self, data):
        if data.dtype.kind == 'm':
            v = data.view('i8')
            max_str_len = max(len(str(maximum.reduce(v))),
                              len(str(minimum.reduce(v))))
            self.format = '%' + str(max_str_len) + 'd'

    def __call__(self, x):
        return self.format % x.astype('i8')


########NEW FILE########
__FILENAME__ = attrs
# -*- coding: utf-8 -*-
########################################################################
#
#       License: BSD
#       Created: August 16, 2012
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import os, os.path
import json


ATTRSDIR = "__attrs__"

class attrs(object):
    """Accessor for attributes in carray objects.

    This class behaves very similarly to a dictionary, and attributes
    can be appended in the typical way::

       attrs['myattr'] = value

    And can be retrieved similarly::

       value = attrs['myattr']

    Attributes can be removed with::

       del attrs['myattr']

    This class also honors the `__iter__` and `__len__` special
    functions.  Moreover, a `getall()` method returns all the
    attributes as a dictionary.

    CAVEAT: The values should be able to be serialized with JSON for
    persistence.

    """

    def __init__(self, rootdir, mode, _new=False):
        self.rootdir = rootdir
        self.mode = mode
        self.attrs = {}

        if self.rootdir:
            self.attrsfile = os.path.join(self.rootdir, ATTRSDIR)

        if self.rootdir:
            if _new:
                self._create()
            else:
                self._open()

    def _create(self):
        if self.mode != 'r':
            # Empty the underlying file
            with open(self.attrsfile, 'wb') as rfile:
                rfile.write(json.dumps({}))
                rfile.write("\n")

    def _open(self):
        if not os.path.isfile(self.attrsfile):
            if self.mode != 'r':
                # Create a new empty file
                with open(self.attrsfile, 'wb') as rfile:
                    rfile.write("\n")
        # Get the serialized attributes
        with open(self.attrsfile, 'rb') as rfile:
            try:
                data = json.loads(rfile.read())
            except:
                raise IOError(
                    "Attribute file is not readable")
        self.attrs = data

    def _update_meta(self):
        """Update attributes on-disk."""
        if not self.rootdir:
            return
        with open(self.attrsfile, 'wb') as rfile:
            rfile.write(json.dumps(self.attrs))
            rfile.write("\n")

    def getall(self):
        return self.attrs.copy()

    def __getitem__(self, name):
        return self.attrs[name]

    def __setitem__(self, name, carray):
        if self.rootdir and self.mode == 'r':
            raise IOError(
                "Cannot modify an attribute when in 'r'ead-only mode")
        self.attrs[name] = carray
        self._update_meta()

    def __delitem__(self, name):
        """Remove the `name` attribute."""
        if self.rootdir and self.mode == 'r':
            raise IOError(
                "Cannot remove an attribute when in 'r'ead-only mode")
        del self.attrs[name]
        self._update_meta()
    
    def __iter__(self):
        return self.attrs.iteritems()

    def __len__(self):
        return len(self.attrs)

    def __str__(self):
        if len(self.attrs) == 0:
            return "*no attrs*"
        fullrepr = ""
        for name in self.attrs:
            fullrepr += "%s : %s" % (name, self.attrs[name]) 
        return fullrepr

    def __repr__(self):
        if len(self.attrs) == 0:
            return str(self)
        fullrepr = ""
        for name in self.attrs:
            fullrepr += "%s : %r\n" % (name, self.attrs[name]) 
        return fullrepr

########NEW FILE########
__FILENAME__ = ctable
########################################################################
#
#       License: BSD
#       Created: September 01, 2010
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import sys, math

import numpy as np
import carray as ca
from carray import utils, attrs, array2string
import itertools as it
from collections import namedtuple
import json
import os, os.path
import shutil


ROOTDIRS = '__rootdirs__'

class cols(object):
    """Class for accessing the columns on the ctable object."""

    def __init__(self, rootdir, mode):
        self.rootdir = rootdir
        self.mode = mode
        self.names = []
        self._cols = {}

    def read_meta_and_open(self):
        """Read the meta-information and initialize structures."""
        # Get the directories of the columns
        rootsfile = os.path.join(self.rootdir, ROOTDIRS)
        with open(rootsfile, 'rb') as rfile:
            data = json.loads(rfile.read())
        # JSON returns unicode (?)
        self.names = [str(name) for name in data['names']]
        # Initialize the cols by instatiating the carrays
        for name, dir_ in data['dirs'].items():
            self._cols[str(name)] = ca.carray(rootdir=dir_, mode=self.mode)

    def update_meta(self):
        """Update metainfo about directories on-disk."""
        if not self.rootdir:
            return
        dirs = dict((n, o.rootdir) for n,o in self._cols.items())
        data = {'names': self.names, 'dirs': dirs}
        rootsfile = os.path.join(self.rootdir, ROOTDIRS)
        with open(rootsfile, 'wb') as rfile:
            rfile.write(json.dumps(data))
            rfile.write("\n")

    def __getitem__(self, name):
        return self._cols[name]

    def __setitem__(self, name, carray):
        self.names.append(name)
        self._cols[name] = carray
        self.update_meta()

    def __iter__(self):
        return iter(self._cols)

    def __len__(self):
        return len(self.names)

    def insert(self, name, pos, carray):
        """Insert carray in the specified pos and name."""
        self.names.insert(pos, name)
        self._cols[name] = carray
        self.update_meta()

    def pop(self, name):
        """Return the named column and remove it."""
        pos = self.names.index(name)
        name = self.names.pop(pos)
        col = self._cols[name]
        self.update_meta()
        return col
    
    def __str__(self):
        fullrepr = ""
        for name in self.names:
            fullrepr += "%s : %s" % (name, str(self._cols[name])) 
        return fullrepr

    def __repr__(self):
        fullrepr = ""
        for name in self.names:
            fullrepr += "%s : %s\n" % (name, repr(self._cols[name])) 
        return fullrepr


class ctable(object):
    """
    ctable(cols, names=None, **kwargs)

    This class represents a compressed, column-wise, in-memory table.

    Create a new ctable from `cols` with optional `names`.

    Parameters
    ----------
    columns : tuple or list of column objects
        The list of column data to build the ctable object.  This can also be
        a pure NumPy structured array.  A list of lists or tuples is valid
        too, as long as they can be converted into carray objects.
    names : list of strings or string
        The list of names for the columns.  The names in this list must be
        valid Python identifiers, must not start with an underscore, and has
        to be specified in the same order as the `cols`.  If not passed, the
        names will be chosen as 'f0' for the first column, 'f1' for the second
        and so on so forth (NumPy convention).
    kwargs : list of parameters or dictionary
        Allows to pass additional arguments supported by carray
        constructors in case new carrays need to be built.

    Notes
    -----
    Columns passed as carrays are not be copied, so their settings
    will stay the same, even if you pass additional arguments (cparams,
    chunklen...).

    """

    # Properties
    # ``````````

    @property
    def cbytes(self):
        "The compressed size of this object (in bytes)."
        return self._get_stats()[1]

    @property
    def cparams(self):
        "The compression parameters for this object."
        return self._cparams

    @property
    def dtype(self):
        "The data type of this object (numpy dtype)."
        names, cols = self.names, self.cols
        l = [(name, cols[name].dtype) for name in names]
        return np.dtype(l)

    @property
    def names(self):
        "The names of the object (list)."
        return self.cols.names

    @property
    def ndim(self):
        "The number of dimensions of this object."
        return len(self.shape)

    @property
    def nbytes(self):
        "The original (uncompressed) size of this object (in bytes)."
        return self._get_stats()[0]

    @property
    def shape(self):
        "The shape of this object."
        return (self.len,)

    @property
    def size(self):
        "The size of this object."
        return np.prod(self.shape)


    def __init__(self, columns=None, names=None, **kwargs):

        # Important optional params
        self._cparams = kwargs.get('cparams', ca.cparams())
        self.rootdir = kwargs.get('rootdir', None)
        "The directory where this object is saved."
        self.mode = kwargs.get('mode', 'a')
        "The mode in which the object is created/opened."
        
        # Setup the columns accessor
        self.cols = cols(self.rootdir, self.mode)
        "The ctable columns accessor."

        # The length counter of this array
        self.len = 0

        # Create a new ctable or open it from disk
        if columns is not None:
            self.create_ctable(columns, names, **kwargs)
            _new = True
        else:
            self.open_ctable()
            _new = False

        # Attach the attrs to this object
        self.attrs = attrs.attrs(self.rootdir, self.mode, _new=_new)
            
        # Cache a structured array of len 1 for ctable[int] acceleration
        self._arr1 = np.empty(shape=(1,), dtype=self.dtype)

    def create_ctable(self, columns, names, **kwargs):
        """Create a ctable anew."""

        # Create the rootdir if necessary
        if self.rootdir:
            self.mkdir_rootdir(self.rootdir, self.mode)

        # Get the names of the columns
        if names is None:
            if isinstance(columns, np.ndarray):  # ratype case
                names = list(columns.dtype.names)
            else:
                names = ["f%d"%i for i in range(len(columns))]
        else:
            if type(names) == tuple:
                names = list(names)
            if type(names) != list:
                raise ValueError(
                    "`names` can only be a list or tuple")
            if len(names) != len(columns):
                raise ValueError(
                    "`columns` and `names` must have the same length")
        # Check names validity
        nt = namedtuple('_nt', names, verbose=False)
        names = list(nt._fields)

        # Guess the kind of columns input
        calist, nalist, ratype = False, False, False
        if type(columns) in (tuple, list):
            calist = [type(v) for v in columns] == [ca.carray for v in columns]
            nalist = [type(v) for v in columns] == [np.ndarray for v in columns]
        elif isinstance(columns, np.ndarray):
            ratype = hasattr(columns.dtype, "names")
            if ratype:
                if len(columns.shape) != 1:
                    raise ValueError, "only unidimensional shapes supported"
        else:
            raise ValueError, "`columns` input is not supported"
        if not (calist or nalist or ratype):
            # Try to convert the elements to carrays
            try:
                columns = [ca.carray(col) for col in columns]
                calist = True
            except:
                raise ValueError, "`columns` input is not supported"

        # Populate the columns
        clen = -1
        for i, name in enumerate(names):
            if self.rootdir:
                # Put every carray under each own `name` subdirectory
                kwargs['rootdir'] = os.path.join(self.rootdir, name)
            if calist:
                column = columns[i]
                if self.rootdir:
                    # Store this in destination
                    column = column.copy(**kwargs)
            elif nalist:
                column = columns[i]
                if column.dtype == np.void:
                    raise ValueError,(
                        "`columns` elements cannot be of type void")
                column = ca.carray(column, **kwargs)
            elif ratype:
                column = ca.carray(columns[name], **kwargs)
            self.cols[name] = column
            if clen >= 0 and clen != len(column):
                raise ValueError, "all `columns` must have the same length"
            clen = len(column)
 
        self.len = clen

    def open_ctable(self):
        """Open an existing ctable on-disk."""

        if self.rootdir is None:
            raise ValueError(
                "you need to pass either a `columns` or a `rootdir` param")

        # Open the ctable by reading the metadata
        self.cols.read_meta_and_open()

        # Get the length out of the first column
        self.len = len(self.cols[self.names[0]])

    def mkdir_rootdir(self, rootdir, mode):
        """Create the `self.rootdir` directory safely."""
        if os.path.exists(rootdir):
            if mode != "w":
                raise RuntimeError(
                    "specified rootdir path '%s' already exists "
                    "and creation mode is '%s'" % (rootdir, mode))
            if os.path.isdir(rootdir):
                shutil.rmtree(rootdir)
            else:
                os.remove(rootdir)
        os.mkdir(rootdir)

    def append(self, rows):
        """
        append(rows)

        Append `rows` to this ctable.

        Parameters
        ----------
        rows : list/tuple of scalar values, NumPy arrays or carrays
            It also can be a NumPy record, a NumPy recarray, or
            another ctable.

        """

        # Guess the kind of rows input
        calist, nalist, sclist, ratype = False, False, False, False
        if type(rows) in (tuple, list):
            calist = [type(v) for v in rows] == [ca.carray for v in rows]
            nalist = [type(v) for v in rows] == [np.ndarray for v in rows]
            if not (calist or nalist):
                # Try with a scalar list
                sclist = True
        elif isinstance(rows, np.ndarray):
            ratype = hasattr(rows.dtype, "names")
        elif isinstance(rows, ca.ctable):
            # Convert int a list of carrays
            rows = [rows[name] for name in self.names]
            calist = True
        else:
            raise ValueError, "`rows` input is not supported"
        if not (calist or nalist or sclist or ratype):
            raise ValueError, "`rows` input is not supported"

        # Populate the columns
        clen = -1
        for i, name in enumerate(self.names):
            if calist or sclist:
                column = rows[i]
            elif nalist:
                column = rows[i]
                if column.dtype == np.void:
                    raise ValueError, "`rows` elements cannot be of type void"
                column = column
            elif ratype:
                column = rows[name]
            # Append the values to column
            self.cols[name].append(column)
            if sclist:
                clen2 = 1
            else:
                clen2 = len(column)
            if clen >= 0 and clen != clen2:
                raise ValueError, "all cols in `rows` must have the same length"
            clen = clen2
        self.len += clen

    def trim(self, nitems):
        """
        trim(nitems)

        Remove the trailing `nitems` from this instance.

        Parameters
        ----------
        nitems : int
            The number of trailing items to be trimmed.

        """

        for name in self.names:
            self.cols[name].trim(nitems)
        self.len -= nitems

    def resize(self, nitems):
        """
        resize(nitems)

        Resize the instance to have `nitems`.

        Parameters
        ----------
        nitems : int
            The final length of the instance.  If `nitems` is larger than the
            actual length, new items will appended using `self.dflt` as
            filling values.

        """

        for name in self.names:
            self.cols[name].resize(nitems)
        self.len = nitems

    def addcol(self, newcol, name=None, pos=None, **kwargs):
        """
        addcol(newcol, name=None, pos=None, **kwargs)

        Add a new `newcol` object as column.

        Parameters
        ----------
        newcol : carray, ndarray, list or tuple
            If a carray is passed, no conversion will be carried out.
            If conversion to a carray has to be done, `kwargs` will
            apply.
        name : string, optional
            The name for the new column.  If not passed, it will
            receive an automatic name.
        pos : int, optional
            The column position.  If not passed, it will be appended
            at the end.
        kwargs : list of parameters or dictionary
            Any parameter supported by the carray constructor.

        Notes
        -----
        You should not specificy both `name` and `pos` arguments,
        unless they are compatible.

        See Also
        --------
        delcol

        """

        # Check params
        if pos is None:
            pos = len(self.names)
        else:
            if pos and type(pos) != int:
                raise ValueError, "`pos` must be an int"
            if pos < 0 or pos > len(self.names):
                raise ValueError, "`pos` must be >= 0 and <= len(self.cols)"
        if name is None:
            name = "f%d" % pos
        else:
            if type(name) != str:
                raise ValueError, "`name` must be a string"
        if name in self.names:
            raise ValueError, "'%s' column already exists" % name
        if len(newcol) != self.len:
            raise ValueError, "`newcol` must have the same length than ctable"

        if isinstance(newcol, np.ndarray):
            if 'cparams' not in kwargs:
                kwargs['cparams'] = self.cparams
            newcol = ca.carray(newcol, **kwargs)
        elif type(newcol) in (list, tuple):
            if 'cparams' not in kwargs:
                kwargs['cparams'] = self.cparams
            newcol = ca.carray(newcol, **kwargs)
        elif type(newcol) != ca.carray:
            raise ValueError(
                """`newcol` type not supported""")

        # Insert the column
        self.cols.insert(name, pos, newcol)
        # Update _arr1
        self._arr1 = np.empty(shape=(1,), dtype=self.dtype)

    def delcol(self, name=None, pos=None):
        """
        delcol(name=None, pos=None)

        Remove the column named `name` or in position `pos`.

        Parameters
        ----------
        name: string, optional
            The name of the column to remove.
        pos: int, optional
            The position of the column to remove.

        Notes
        -----
        You must specify at least a `name` or a `pos`.  You should not
        specify both `name` and `pos` arguments, unless they are
        compatible.

        See Also
        --------
        addcol

        """

        if name is None and pos is None:
            raise ValueError, "specify either a `name` or a `pos`"
        if name is not None and pos is not None:
            raise ValueError, "you cannot specify both a `name` and a `pos`"
        if name:
            if type(name) != str:
                raise ValueError, "`name` must be a string"
            if name not in self.names:
                raise ValueError, "`name` not found in columns"
            pos = self.names.index(name)
        elif pos is not None:
            if type(pos) != int:
                raise ValueError, "`pos` must be an int"
            if pos < 0 or pos > len(self.names):
                raise ValueError, "`pos` must be >= 0 and <= len(self.cols)"
            name = self.names[pos]

        # Remove the column
        self.cols.pop(name)
        # Update _arr1
        self._arr1 = np.empty(shape=(1,), dtype=self.dtype)

    def copy(self, **kwargs):
        """
        copy(**kwargs)

        Return a copy of this ctable.

        Parameters
        ----------
        kwargs : list of parameters or dictionary
            Any parameter supported by the carray/ctable constructor.

        Returns
        -------
        out : ctable object
            The copy of this ctable.

        """

        # Check that origin and destination do not overlap
        rootdir = kwargs.get('rootdir', None)
        if rootdir and self.rootdir and  rootdir == self.rootdir:
                raise RuntimeError("rootdir cannot be the same during copies")

        # Remove possible unsupported args for columns
        names = kwargs.pop('names', self.names)

        # Copy the columns
        if rootdir:
            # A copy is always made during creation with a rootdir
            cols = [ self.cols[name] for name in self.names ]
        else:
            cols = [ self.cols[name].copy(**kwargs) for name in self.names ]
        # Create the ctable
        ccopy = ctable(cols, names, **kwargs)
        return ccopy

    def __len__(self):
        return self.len

    def __sizeof__(self):
        return self.cbytes

    def where(self, expression, outcols=None, limit=None, skip=0):
        """
        where(expression, outcols=None, limit=None, skip=0)

        Iterate over rows where `expression` is true.

        Parameters
        ----------
        expression : string or carray
            A boolean Numexpr expression or a boolean carray.
        outcols : list of strings or string
            The list of column names that you want to get back in results.
            Alternatively, it can be specified as a string such as 'f0 f1' or
            'f0, f1'.  If None, all the columns are returned.  If the special
            name 'nrow__' is present, the number of row will be included in
            output.
        limit : int
            A maximum number of elements to return.  The default is return
            everything.
        skip : int
            An initial number of elements to skip.  The default is 0.

        Returns
        -------
        out : iterable
            This iterable returns rows as NumPy structured types (i.e. they
            support being mapped either by position or by name).

        See Also
        --------
        iter

        """

        # Check input
        if type(expression) is str:
            # That must be an expression
            boolarr = self.eval(expression)
        elif hasattr(expression, "dtype") and expression.dtype.kind == 'b':
            boolarr = expression
        else:
            raise ValueError, "only boolean expressions or arrays are supported"

        # Check outcols
        if outcols is None:
            outcols = self.names
        else:
            if type(outcols) not in (list, tuple, str):
                raise ValueError, "only list/str is supported for outcols"
            # Check name validity
            nt = namedtuple('_nt', outcols, verbose=False)
            outcols = list(nt._fields)
            if set(outcols) - set(self.names+['nrow__']) != set():
                raise ValueError, "not all outcols are real column names"

        # Get iterators for selected columns
        icols, dtypes = [], []
        for name in outcols:
            if name == "nrow__":
                icols.append(boolarr.wheretrue(limit=limit, skip=skip))
                dtypes.append((name, np.int_))
            else:
                col = self.cols[name]
                icols.append(col.where(boolarr, limit=limit, skip=skip))
                dtypes.append((name, col.dtype))
        dtype = np.dtype(dtypes)
        return self._iter(icols, dtype)

    def __iter__(self):
        return self.iter(0, self.len, 1)

    def iter(self, start=0, stop=None, step=1, outcols=None,
             limit=None, skip=0):
        """
        iter(start=0, stop=None, step=1, outcols=None, limit=None, skip=0)

        Iterator with `start`, `stop` and `step` bounds.

        Parameters
        ----------
        start : int
            The starting item.
        stop : int
            The item after which the iterator stops.
        step : int
            The number of items incremented during each iteration.  Cannot be
            negative.
        outcols : list of strings or string
            The list of column names that you want to get back in results.
            Alternatively, it can be specified as a string such as 'f0 f1' or
            'f0, f1'.  If None, all the columns are returned.  If the special
            name 'nrow__' is present, the number of row will be included in
            output.
        limit : int
            A maximum number of elements to return.  The default is return
            everything.
        skip : int
            An initial number of elements to skip.  The default is 0.

        Returns
        -------
        out : iterable

        See Also
        --------
        where

        """

        # Check outcols
        if outcols is None:
            outcols = self.names
        else:
            if type(outcols) not in (list, tuple, str):
                raise ValueError, "only list/str is supported for outcols"
            # Check name validity
            nt = namedtuple('_nt', outcols, verbose=False)
            outcols = list(nt._fields)
            if set(outcols) - set(self.names+['nrow__']) != set():
                raise ValueError, "not all outcols are real column names"

        # Check limits
        if step <= 0:
            raise NotImplementedError, "step param can only be positive"
        start, stop, step = slice(start, stop, step).indices(self.len)

        # Get iterators for selected columns
        icols, dtypes = [], []
        for name in outcols:
            if name == "nrow__":
                istop = None
                if limit is not None:
                    istop = limit + skip
                icols.append(it.islice(xrange(start, stop, step), skip, istop))
                dtypes.append((name, np.int_))
            else:
                col = self.cols[name]
                icols.append(
                    col.iter(start, stop, step, limit=limit, skip=skip))
                dtypes.append((name, col.dtype))
        dtype = np.dtype(dtypes)
        return self._iter(icols, dtype)

    def _iter(self, icols, dtype):
        """Return a list of `icols` iterators with `dtype` names."""

        icols = tuple(icols)
        namedt = namedtuple('row', dtype.names)
        iterable = it.imap(namedt, *icols)
        return iterable

    def _where(self, boolarr, colnames=None):
        """Return rows where `boolarr` is true as an structured array.

        This is called internally only, so we can assum that `boolarr`
        is a boolean array.
        """

        if colnames is None:
            colnames = self.names
        cols = [self.cols[name][boolarr] for name in colnames]
        dtype = np.dtype([(name, self.cols[name].dtype) for name in colnames])
        result = np.rec.fromarrays(cols, dtype=dtype).view(np.ndarray)

        return result

    def __getitem__(self, key):
        """
        x.__getitem__(key) <==> x[key]

        Returns values based on `key`.  All the functionality of
        ``ndarray.__getitem__()`` is supported (including fancy
        indexing), plus a special support for expressions:

        Parameters
        ----------
        key : string
            The corresponding ctable column name will be returned.  If
            not a column name, it will be interpret as a boolean
            expression (computed via `ctable.eval`) and the rows where
            these values are true will be returned as a NumPy
            structured array.

        See Also
        --------
        ctable.eval

        """

        # First, check for integer
        if isinstance(key, (int, long)):
            # Get a copy of the len-1 array
            ra = self._arr1.copy()
            # Fill it
            ra[0] = tuple([self.cols[name][key] for name in self.names])
            return ra[0]
        # Slices
        elif type(key) == slice:
            (start, stop, step) = key.start, key.stop, key.step
            if step and step <= 0 :
                raise NotImplementedError("step in slice can only be positive")
        # Multidimensional keys
        elif isinstance(key, tuple):
            if len(key) != 1:
                raise IndexError, "multidimensional keys are not supported"
            return self[key[0]]
        # List of integers (case of fancy indexing), or list of column names
        elif type(key) is list:
            if len(key) == 0:
                return np.empty(0, self.dtype)
            strlist = [type(v) for v in key] == [str for v in key]
            # Range of column names
            if strlist:
                cols = [self.cols[name] for name in key]
                return ctable(cols, key)
            # Try to convert to a integer array
            try:
                key = np.array(key, dtype=np.int_)
            except:
                raise IndexError, \
                      "key cannot be converted to an array of indices"
            return np.fromiter((self[i] for i in key),
                               dtype=self.dtype, count=len(key))
        # A boolean array (case of fancy indexing)
        elif hasattr(key, "dtype"):
            if key.dtype.type == np.bool_:
                return self._where(key)
            elif np.issubsctype(key, np.int_):
                # An integer array
                return np.array([self[i] for i in key], dtype=self.dtype)
            else:
                raise IndexError, \
                      "arrays used as indices must be integer (or boolean)"
        # Column name or expression
        elif type(key) is str:
            if key not in self.names:
                # key is not a column name, try to evaluate
                arr = self.eval(key, depth=4)
                if arr.dtype.type != np.bool_:
                    raise IndexError, \
                          "`key` %s does not represent a boolean expression" %\
                          key
                return self._where(arr)
            return self.cols[key]
        # All the rest not implemented
        else:
            raise NotImplementedError, "key not supported: %s" % repr(key)

        # From now on, will only deal with [start:stop:step] slices

        # Get the corrected values for start, stop, step
        (start, stop, step) = slice(start, stop, step).indices(self.len)
        # Build a numpy container
        n = utils.get_len_of_range(start, stop, step)
        ra = np.empty(shape=(n,), dtype=self.dtype)
        # Fill it
        for name in self.names:
            ra[name][:] = self.cols[name][start:stop:step]

        return ra

    def __setitem__(self, key, value):
        """
        x.__setitem__(key, value) <==> x[key] = value

        Sets values based on `key`.  All the functionality of
        ``ndarray.__setitem__()`` is supported (including fancy
        indexing), plus a special support for expressions:

        Parameters
        ----------
        key : string
            The corresponding ctable column name will be set to `value`.  If
            not a column name, it will be interpret as a boolean expression
            (computed via `ctable.eval`) and the rows where these values are
            true will be set to `value`.

        See Also
        --------
        ctable.eval

        """

        # First, convert value into a structured array
        value = utils.to_ndarray(value, self.dtype)
        # Check if key is a condition actually
        if type(key) is bytes:
            # Convert key into a boolean array
            #key = self.eval(key)
            # The method below is faster (specially for large ctables)
            rowval = 0
            for nrow in self.where(key, outcols=["nrow__"]):
                nrow = nrow[0]
                if len(value) == 1:
                    for name in self.names:
                        self.cols[name][nrow] = value[name]
                else:
                    for name in self.names:
                        self.cols[name][nrow] = value[name][rowval]
                    rowval += 1
            return
        # Then, modify the rows
        for name in self.names:
            self.cols[name][key] = value[name]
        return

    def eval(self, expression, **kwargs):
        """
        eval(expression, **kwargs)

        Evaluate the `expression` on columns and return the result.

        Parameters
        ----------
        expression : string
            A string forming an expression, like '2*a+3*b'. The values
            for 'a' and 'b' are variable names to be taken from the
            calling function's frame.  These variables may be column
            names in this table, scalars, carrays or NumPy arrays.
        kwargs : list of parameters or dictionary
            Any parameter supported by the `eval()` first level function.

        Returns
        -------
        out : carray object
            The outcome of the expression.  You can tailor the
            properties of this carray by passing additional arguments
            supported by carray constructor in `kwargs`.

        See Also
        --------
        eval (first level function)

        """

        # Get the desired frame depth
        depth = kwargs.pop('depth', 3)
        # Call top-level eval with cols as user_dict
        return ca.eval(expression, user_dict=self.cols, depth=depth, **kwargs)

    def flush(self):
        """Flush data in internal buffers to disk.

        This call should typically be done after performing modifications
        (__settitem__(), append()) in persistence mode.  If you don't do this,
        you risk loosing part of your modifications.

        """
        for name in self.names:
            self.cols[name].flush()

    def _get_stats(self):
        """
        _get_stats()

        Get some stats (nbytes, cbytes and ratio) about this object.

        Returns
        -------
        out : a (nbytes, cbytes, ratio) tuple
            nbytes is the number of uncompressed bytes in ctable.
            cbytes is the number of compressed bytes.  ratio is the
            compression ratio.

        """

        nbytes, cbytes, ratio = 0, 0, 0.0
        names, cols = self.names, self.cols
        for name in names:
            column = cols[name]
            nbytes += column.nbytes
            cbytes += column.cbytes
        cratio = nbytes / float(cbytes)
        return (nbytes, cbytes, cratio)

    def __str__(self):
        return array2string(self)

    def __repr__(self):
        nbytes, cbytes, cratio = self._get_stats()
        snbytes = utils.human_readable_size(nbytes)
        scbytes = utils.human_readable_size(cbytes)
        header = "ctable(%s, %s)\n" % (self.shape, self.dtype)
        header += "  nbytes: %s; cbytes: %s; ratio: %.2f\n" % (
            snbytes, scbytes, cratio)
        header += "  cparams := %r\n" % self.cparams
        if self.rootdir:
            header += "  rootdir := '%s'\n" % self.rootdir
        fullrepr = header + str(self)
        return fullrepr


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 78
## End:

########NEW FILE########
__FILENAME__ = defaults
########################################################################
#
#       License: BSD
#       Created: February 1, 2011
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

"""
Default values for carray.

Feel free to change them for better adapting to your needs.

"""

import carray as ca


class Defaults(object):
    """Class to taylor the setters and getters of default values."""

    def __init__(self):
        self.choices = {}

        # Choices setup
        self.choices['eval_out_flavor'] = ("carray", "numpy")
        self.choices['eval_vm'] = ("numexpr", "python")

    def check_choices(self, name, value):
        if value not in self.choices[name]:
            raiseValue, "value must be either 'numexpr' or 'python'"

    #
    # Properties start here...
    #

    @property
    def eval_vm(self):
        return self.__eval_vm

    @eval_vm.setter
    def eval_vm(self, value):
        self.check_choices('eval_vm', value)
        if value == "numexpr" and not ca.numexpr_here:
            raise (ValueError,
                   "cannot use `numexpr` virtual machine "
                   "(minimum required version is probably not installed)")
        self.__eval_vm = value

    @property
    def eval_out_flavor(self):
        return self.__eval_out_flavor

    @eval_out_flavor.setter
    def eval_out_flavor(self, value):
        self.check_choices('eval_out_flavor', value)
        self.__eval_out_flavor = value


defaults = Defaults()


# Default values start here...

defaults.eval_out_flavor = "carray"
"""
The flavor for the output object in `eval()`.  It can be 'carray' or
'numpy'.  Default is 'carray'.

"""

defaults.eval_vm = "python"
"""
The virtual machine to be used in computations (via `eval`).  It can
be 'numexpr' or 'python'.  Default is 'numexpr', if installed.  If
not, then the default is 'python'.

"""

# If numexpr is available, use it as default
if ca.numexpr_here:
    defaults.eval_vm = "numexpr"


########NEW FILE########
__FILENAME__ = common
########################################################################
#
#       License: BSD
#       Created: August 15, 2012
#       Author:  Francesc Alted - faltet@pytables.org
#
########################################################################


import unittest
import tempfile
import os, os.path
import glob
import shutil


# Global variables for the tests
verbose = False
heavy = False


# Useful superclass for disk-based tests
class MayBeDiskTest(unittest.TestCase):

    disk = False

    def setUp(self):
        if self.disk:
            prefix = 'carray-' + self.__class__.__name__
            self.rootdir = tempfile.mkdtemp(prefix=prefix)
            os.rmdir(self.rootdir)  # tests needs this cleared
        else:
            self.rootdir = None

    def tearDown(self):
        if self.disk:
            # Remove every directory starting with rootdir
            for dir_ in glob.glob(self.rootdir+'*'):
                shutil.rmtree(dir_)



########NEW FILE########
__FILENAME__ = test_all
########################################################################
#
#       License: BSD
#       Created: August 5, 2010
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

"""
Run all test cases.
"""

import sys, os
import unittest

import numpy
import carray
from carray.tests import common


# Recommended minimum versions
min_numpy_version = "1.5"


def suite():
    test_modules = [
        'carray.tests.test_carray',
        'carray.tests.test_ctable',
        'carray.tests.test_ndcarray',
        'carray.tests.test_queries',
        'carray.tests.test_attrs',
        ]
    alltests = unittest.TestSuite()
    for name in test_modules:
        exec('from %s import suite as test_suite' % name)
        alltests.addTest(test_suite())
    return alltests


def print_versions():
    """Print all the versions of software that carray relies on."""
    print("-=" * 38)
    print("carray version:    %s" % carray.__version__)
    print("NumPy version:     %s" % numpy.__version__)
    tinfo = carray.blosc_version()
    print("Blosc version:     %s (%s)" % (tinfo[0], tinfo[1]))
    if carray.numexpr_here:
        print("Numexpr version:   %s" % carray.numexpr.__version__)
    else:
        print("Numexpr version:   not available "
              "(version >= %s not detected)" %  carray.min_numexpr_version)
    from Cython.Compiler.Main import Version as Cython_Version
    print("Cython version:    %s" % Cython_Version.version)
    print("Python version:    %s" % sys.version)
    if os.name == "posix":
        (sysname, nodename, release, version, machine) = os.uname()
        print("Platform:          %s-%s" % (sys.platform, machine))
    print("Byte-ordering:     %s" % sys.byteorder)
    print("Detected cores:    %s" % carray.detect_number_of_cores())
    print("-=" * 38)


def print_heavy(heavy):
    if heavy:
        print """\
Performing the complete test suite!"""
    else:
        print """\
Performing only a light (yet comprehensive) subset of the test suite.
If you want a more complete test, try passing the --heavy flag to this
script (or set the 'heavy' parameter in case you are using carray.test()
call).  The whole suite will take more than 30 seconds to complete on a
relatively modern CPU and around 300 MB of RAM and 500 MB of disk
[32-bit platforms will always run significantly more lightly].
"""
    print '-=' * 38

def test(verbose=False, heavy=False):
    """
    test(verbose=False, heavy=False)

    Run all the tests in the test suite.

    If `verbose` is set, the test suite will emit messages with full
    verbosity (not recommended unless you are looking into a certain
    problem).

    If `heavy` is set, the test suite will be run in *heavy* mode (you
    should be careful with this because it can take a lot of time and
    resources from your computer).
    """
    print_versions()
    print_heavy(heavy)

    # What a context this is!
    oldverbose, common.verbose = common.verbose, verbose
    oldheavy, common.heavy = common.heavy, heavy
    try:
        unittest.TextTestRunner().run(suite())
    finally:
        common.verbose = oldverbose
        common.heavy = oldheavy  # there are pretty young heavies, too ;)

if __name__ == '__main__':

    if numpy.__version__ < min_numpy_version:
        print("*Warning*: NumPy version is lower than recommended: %s < %s" % \
              (numpy.__version__, min_numpy_version))

    # Handle some global flags (i.e. only useful for test_all.py)
    only_versions = 0
    args = sys.argv[:]
    for arg in args:
        if arg in ['--print-versions']:
            only_versions = True
            sys.argv.remove(arg)
        if arg in ['--verbose']:
            common.verbose = True
            sys.argv.remove(arg)
        if arg in ['--heavy']:
            common.heavy = True
            sys.argv.remove(arg)

    print_versions()
    if not only_versions:
        print_heavy(common.heavy)
        unittest.main(defaultTest='carray.tests.suite')


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 72
## End:

########NEW FILE########
__FILENAME__ = test_attrs
# -*- coding: utf-8 -*-
########################################################################
#
#       License: BSD
#       Created: August 17, 2012
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import sys
import os, os.path
import struct

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import carray as ca
from carray.tests import common
from common import MayBeDiskTest
import unittest


class basicTest(MayBeDiskTest):

    def getobject(self):
        if self.flavor == 'carray':
            obj = ca.zeros(10, dtype="i1", rootdir=self.rootdir)
            assert type(obj) == ca.carray
        elif self.flavor == 'ctable':
            obj = ca.fromiter(((i,i*2) for i in range(10)), dtype='i2,f4',
                              count=10, rootdir=self.rootdir)
            assert type(obj) == ca.ctable
        return obj

    def test00a(self):
        """Creating attributes in a new carray."""

        cn = self.getobject()
        # Some attrs
        cn.attrs['attr1'] = 'val1'
        cn.attrs['attr2'] = 'val2'
        cn.attrs['attr3'] = 'val3'
        self.assert_(cn.attrs['attr1'] == 'val1')
        self.assert_(cn.attrs['attr2'] == 'val2')
        self.assert_(cn.attrs['attr3'] == 'val3')
        self.assert_(len(cn.attrs) == 3)

    def test00b(self):
        """Accessing attributes in a opened carray."""

        cn = self.getobject()
        # Some attrs
        cn.attrs['attr1'] = 'val1'
        cn.attrs['attr2'] = 'val2'
        cn.attrs['attr3'] = 'val3'
        # Re-open the carray
        if self.rootdir:
            cn = ca.open(rootdir=self.rootdir)
        self.assert_(cn.attrs['attr1'] == 'val1')
        self.assert_(cn.attrs['attr2'] == 'val2')
        self.assert_(cn.attrs['attr3'] == 'val3')
        self.assert_(len(cn.attrs) == 3)

    def test01a(self):
        """Removing attributes in a new carray."""

        cn = self.getobject()
        # Some attrs
        cn.attrs['attr1'] = 'val1'
        cn.attrs['attr2'] = 'val2'
        cn.attrs['attr3'] = 'val3'
        # Remove one of them
        del cn.attrs['attr2']
        self.assert_(cn.attrs['attr1'] == 'val1')
        self.assert_(cn.attrs['attr3'] == 'val3')
        self.assertRaises(KeyError, cn.attrs.__getitem__, 'attr2')
        self.assert_(len(cn.attrs) == 2)

    def test01b(self):
        """Removing attributes in a opened carray."""

        cn = self.getobject()
        # Some attrs
        cn.attrs['attr1'] = 'val1'
        cn.attrs['attr2'] = 'val2'
        cn.attrs['attr3'] = 'val3'
        # Reopen
        if self.rootdir:
            cn = ca.open(rootdir=self.rootdir)
        # Remove one of them
        del cn.attrs['attr2']
        self.assert_(cn.attrs['attr1'] == 'val1')
        self.assert_(cn.attrs['attr3'] == 'val3')
        self.assertRaises(KeyError, cn.attrs.__getitem__, 'attr2')
        self.assert_(len(cn.attrs) == 2)

    def test01c(self):
        """Appending attributes in a opened carray."""

        cn = self.getobject()
        # Some attrs
        cn.attrs['attr1'] = 'val1'
        # Reopen
        if self.rootdir:
            cn = ca.open(rootdir=self.rootdir)
        # Append attrs
        cn.attrs['attr2'] = 'val2'
        cn.attrs['attr3'] = 'val3'
        self.assert_(cn.attrs['attr1'] == 'val1')
        self.assert_(cn.attrs['attr2'] == 'val2')
        self.assert_(cn.attrs['attr3'] == 'val3')
        self.assert_(len(cn.attrs) == 3)

    def test02(self):
        """Checking iterator in attrs accessor."""

        cn = self.getobject()
        # Some attrs
        cn.attrs['attr1'] = 'val1'
        cn.attrs['attr2'] = 'val2'
        cn.attrs['attr3'] = 'val3'
        count = 0
        for key, val in cn.attrs:
            if key == 'attr1':
                self.assert_(val, 'val1')
            if key == 'attr2':
                self.assert_(val, 'val2')
            if key == 'attr3':
                self.assert_(val, 'val3')
            count += 1
        self.assert_(count, 3)

class carrayTest(basicTest):
    flavor = "carray"
    disk = False

class carrayDiskTest(basicTest):
    flavor = "carray"
    disk = True

class ctableTest(basicTest):
    flavor = "ctable"
    disk = False

class ctableDiskTest(basicTest):
    flavor = "ctable"
    disk = True



def suite():
    theSuite = unittest.TestSuite()

    theSuite.addTest(unittest.makeSuite(carrayTest))
    theSuite.addTest(unittest.makeSuite(carrayDiskTest))
    theSuite.addTest(unittest.makeSuite(ctableTest))
    theSuite.addTest(unittest.makeSuite(ctableDiskTest))

    return theSuite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 72
## End:

########NEW FILE########
__FILENAME__ = test_carray
# -*- coding: utf-8 -*-
########################################################################
#
#       License: BSD
#       Created: August 5, 2010
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import sys
import os, os.path
import struct

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import carray as ca
from carray.tests import common
from common import MayBeDiskTest
from carray.carrayExtension import chunk
import unittest


is_64bit = (struct.calcsize("P") == 8)


class chunkTest(unittest.TestCase):

    def test01(self):
        """Testing `__getitem()__` method with scalars"""
        a = np.arange(1e3)
        b = chunk(a, atom=a.dtype, cparams=ca.cparams())
        #print "b[1]->", `b[1]`
        self.assert_(a[1] == b[1], "Values in key 1 are not equal")

    def test02(self):
        """Testing `__getitem()__` method with ranges"""
        a = np.arange(1e3)
        b = chunk(a, atom=a.dtype, cparams=ca.cparams())
        #print "b[1:3]->", `b[1:3]`
        assert_array_equal(a[1:3], b[1:3], "Arrays are not equal")

    def test03(self):
        """Testing `__getitem()__` method with ranges and steps"""
        a = np.arange(1e3)
        b = chunk(a, atom=a.dtype, cparams=ca.cparams())
        #print "b[1:8:3]->", `b[1:8:3]`
        assert_array_equal(a[1:8:3], b[1:8:3], "Arrays are not equal")

    def test04(self):
        """Testing `__getitem()__` method with long ranges"""
        a = np.arange(1e4)
        b = chunk(a, atom=a.dtype, cparams=ca.cparams())
        #print "b[1:8000]->", `b[1:8000]`
        assert_array_equal(a[1:8000], b[1:8000], "Arrays are not equal")


class getitemTest(MayBeDiskTest):

    def test01a(self):
        """Testing `__getitem()__` method with only a start"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(1)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test01b(self):
        """Testing `__getitem()__` method with only a (negative) start"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(-1)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test01c(self):
        """Testing `__getitem()__` method with only a (start,)"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        #print "b[(1,)]->", `b[(1,)]`
        self.assert_(a[(1,)] == b[(1,)], "Values with key (1,) are not equal")

    def test01d(self):
        """Testing `__getitem()__` method with only a (large) start"""
        a = np.arange(1e4)
        b = ca.carray(a, rootdir=self.rootdir)
        sl = -2   # second last element
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02a(self):
        """Testing `__getitem()__` method with ranges"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(1, 3)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02b(self):
        """Testing `__getitem()__` method with ranges (negative start)"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(-3)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02c(self):
        """Testing `__getitem()__` method with ranges (negative stop)"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(1, -3)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02d(self):
        """Testing `__getitem()__` method with ranges (negative start, stop)"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(-3, -1)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02e(self):
        """Testing `__getitem()__` method with start > stop"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(4, 3, 30)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03a(self):
        """Testing `__getitem()__` method with ranges and steps (I)"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(1, 80, 3)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03b(self):
        """Testing `__getitem()__` method with ranges and steps (II)"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(1, 80, 30)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03c(self):
        """Testing `__getitem()__` method with ranges and steps (III)"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(990, 998, 2)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03d(self):
        """Testing `__getitem()__` method with ranges and steps (IV)"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(4, 80, 3000)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04a(self):
        """Testing `__getitem()__` method with long ranges"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        sl = slice(1, 8000)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04b(self):
        """Testing `__getitem()__` method with no start"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        sl = slice(None, 8000)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04c(self):
        """Testing `__getitem()__` method with no stop"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        sl = slice(8000, None)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04d(self):
        """Testing `__getitem()__` method with no start and no stop"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        sl = slice(None, None, 2)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test05(self):
        """Testing `__getitem()__` method with negative steps"""
        a = np.arange(1e3)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        sl = slice(None, None, -3)
        #print "b[sl]->", `b[sl]`
        self.assertRaises(NotImplementedError, b.__getitem__, sl)

class getitemDiskTest(getitemTest):
    disk = True


class setitemTest(MayBeDiskTest):

    def test00a(self):
        """Testing `__setitem()__` method with only one element"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        b[1] = 10.
        a[1] = 10.
        #print "b->", `b`
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test00b(self):
        """Testing `__setitem()__` method with only one element (tuple)"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        b[(1,)] = 10.
        a[(1,)] = 10.
        #print "b->", `b`
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test01(self):
        """Testing `__setitem()__` method with a range"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        b[10:100] = np.arange(1e2 - 10.)
        a[10:100] = np.arange(1e2 - 10.)
        #print "b->", `b`
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test02(self):
        """Testing `__setitem()__` method with broadcasting"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        b[10:100] = 10.
        a[10:100] = 10.
        #print "b->", `b`
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test03(self):
        """Testing `__setitem()__` method with the complete range"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=10, rootdir=self.rootdir)
        b[:] = np.arange(10., 1e2 + 10.)
        a[:] = np.arange(10., 1e2 + 10.)
        #print "b->", `b`
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test04a(self):
        """Testing `__setitem()__` method with start:stop:step"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=1, rootdir=self.rootdir)
        sl = slice(10, 100, 3)
        b[sl] = 10.
        a[sl] = 10.
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test04b(self):
        """Testing `__setitem()__` method with start:stop:step (II)"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=1, rootdir=self.rootdir)
        sl = slice(10, 11, 3)
        b[sl] = 10.
        a[sl] = 10.
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test04c(self):
        """Testing `__setitem()__` method with start:stop:step (III)"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=1, rootdir=self.rootdir)
        sl = slice(96, 100, 3)
        b[sl] = 10.
        a[sl] = 10.
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test04d(self):
        """Testing `__setitem()__` method with start:stop:step (IV)"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=1, rootdir=self.rootdir)
        sl = slice(2, 99, 30)
        b[sl] = 10.
        a[sl] = 10.
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(a, b[:], "__setitem__ not working correctly")

    def test05(self):
        """Testing `__setitem()__` method with negative step"""
        a = np.arange(1e2)
        b = ca.carray(a, chunklen=1, rootdir=self.rootdir)
        sl = slice(2, 99, -30)
        self.assertRaises(NotImplementedError, b.__setitem__, sl, 3.)

class setitemDiskTest(setitemTest):
    disk = True


class appendTest(MayBeDiskTest):

    def test00(self):
        """Testing `append()` method"""
        a = np.arange(1000)
        b = ca.carray(a, rootdir=self.rootdir)
        b.append(a)
        #print "b->", `b`
        c = np.concatenate((a, a))
        assert_array_equal(c, b[:], "Arrays are not equal")

    def test01(self):
        """Testing `append()` method (small chunklen)"""
        a = np.arange(1000)
        b = ca.carray(a, chunklen=1, rootdir=self.rootdir)
        b.append(a)
        #print "b->", `b`
        c = np.concatenate((a, a))
        assert_array_equal(c, b[:], "Arrays are not equal")

    def test02a(self):
        """Testing `append()` method (large chunklen I)"""
        a = np.arange(1000)
        b = ca.carray(a, chunklen=10*1000, rootdir=self.rootdir)
        b.append(a)
        #print "b->", `b`
        c = np.concatenate((a, a))
        assert_array_equal(c, b[:], "Arrays are not equal")

    def test02b(self):
        """Testing `append()` method (large chunklen II)"""
        a = np.arange(100*1000)
        b = ca.carray(a, chunklen=10*1000, rootdir=self.rootdir)
        b.append(a)
        #print "b->", `b`
        c = np.concatenate((a, a))
        assert_array_equal(c, b[:], "Arrays are not equal")

    def test02c(self):
        """Testing `append()` method (large chunklen III)"""
        a = np.arange(1000*1000)
        b = ca.carray(a, chunklen=100*1000-1, rootdir=self.rootdir)
        b.append(a)
        #print "b->", `b`
        c = np.concatenate((a, a))
        assert_array_equal(c, b[:], "Arrays are not equal")

    def test03(self):
        """Testing `append()` method (large append)"""
        a = np.arange(1e4)
        c = np.arange(2e5)
        b = ca.carray(a, rootdir=self.rootdir)
        b.append(c)
        #print "b->", `b`
        d = np.concatenate((a, c))
        assert_array_equal(d, b[:], "Arrays are not equal")

class appendDiskTest(appendTest):
    disk = True


class trimTest(MayBeDiskTest):

    def test00(self):
        """Testing `trim()` method"""
        b = ca.arange(1e3, rootdir=self.rootdir)
        b.trim(3)
        a = np.arange(1e3-3)
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test01(self):
        """Testing `trim()` method (small chunklen)"""
        b = ca.arange(1e2, chunklen=2, rootdir=self.rootdir)
        b.trim(5)
        a = np.arange(1e2-5)
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test02(self):
        """Testing `trim()` method (large trim)"""
        a = np.arange(2)
        b = ca.arange(1e4, rootdir=self.rootdir)
        b.trim(1e4-2)
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test03(self):
        """Testing `trim()` method (complete trim)"""
        a = np.arange(0.)
        b = ca.arange(1e4, rootdir=self.rootdir)
        b.trim(1e4)
        #print "b->", `b`
        self.assert_(len(a) == len(b), "Lengths are not equal")

    def test04(self):
        """Testing `trim()` method (trimming more than available items)"""
        a = np.arange(0.)
        b = ca.arange(1e4, rootdir=self.rootdir)
        #print "b->", `b`
        self.assertRaises(ValueError, b.trim, 1e4+1)

    def test05(self):
        """Testing `trim()` method (trimming zero items)"""
        a = np.arange(1e1)
        b = ca.arange(1e1, rootdir=self.rootdir)
        b.trim(0)
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test06(self):
        """Testing `trim()` method (negative number of items)"""
        a = np.arange(2e1)
        b = ca.arange(1e1, rootdir=self.rootdir)
        b.trim(-10)
        a[10:] = 0
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

class trimDiskTest(trimTest):
    disk = True


class resizeTest(MayBeDiskTest):

    def test00a(self):
        """Testing `resize()` method (decrease)"""
        b = ca.arange(self.N, rootdir=self.rootdir)
        b.resize(self.N-3)
        a = np.arange(self.N-3)
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test00b(self):
        """Testing `resize()` method (increase)"""
        b = ca.arange(self.N, rootdir=self.rootdir)
        b.resize(self.N+3)
        a = np.arange(self.N+3)
        a[self.N:] = 0
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test01a(self):
        """Testing `resize()` method (decrease, large variation)"""
        b = ca.arange(self.N, rootdir=self.rootdir)
        b.resize(3)
        a = np.arange(3)
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test01b(self):
        """Testing `resize()` method (increase, large variation)"""
        b = ca.arange(self.N, dflt=1, rootdir=self.rootdir)
        b.resize(self.N*3)
        a = np.arange(self.N*3)
        a[self.N:] = 1
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test02(self):
        """Testing `resize()` method (zero size)"""
        b = ca.arange(self.N, rootdir=self.rootdir)
        b.resize(0)
        a = np.arange(0)
        #print "b->", `b`
        assert_array_equal(a, b[:], "Arrays are not equal")


class resize_smallTest(resizeTest):
    N = 10

class resize_smallDiskTest(resizeTest):
    N = 10
    disk = True

class resize_largeTest(resizeTest):
    N = 10000

class resize_largeDiskTest(resizeTest):
    N = 10000
    disk = True

class miscTest(MayBeDiskTest):

    def test00(self):
        """Testing __len__()"""
        a = np.arange(111)
        b = ca.carray(a, rootdir=self.rootdir)
        self.assert_(len(a) == len(b), "Arrays do not have the same length")

    def test01(self):
        """Testing __sizeof__() (big carrays)"""
        a = np.arange(2e5)
        b = ca.carray(a, rootdir=self.rootdir)
        #print "size b uncompressed-->", b.nbytes
        #print "size b compressed  -->", b.cbytes
        self.assert_(sys.getsizeof(b) < b.nbytes,
                     "carray does not seem to compress at all")

    def test02(self):
        """Testing __sizeof__() (small carrays)"""
        a = np.arange(111)
        b = ca.carray(a)
        #print "size b uncompressed-->", b.nbytes
        #print "size b compressed  -->", b.cbytes
        self.assert_(sys.getsizeof(b) > b.nbytes,
                     "carray compress too much??")

class miscDiskTest(miscTest):
    disk = True


class copyTest(MayBeDiskTest):

    def test00(self):
        """Testing copy() without params"""
        a = np.arange(111)
        b = ca.carray(a, rootdir=self.rootdir)
        c = b.copy()
        c.append(np.arange(111, 122))
        self.assert_(len(b) == 111, "copy() does not work well")
        self.assert_(len(c) == 122, "copy() does not work well")
        r = np.arange(122)
        assert_array_equal(c[:], r, "incorrect correct values after copy()")

    def test01(self):
        """Testing copy() with higher compression"""
        a = np.linspace(-1., 1., 1e4)
        b = ca.carray(a, rootdir=self.rootdir)
        c = b.copy(cparams=ca.cparams(clevel=9))
        #print "b.cbytes, c.cbytes:", b.cbytes, c.cbytes
        self.assert_(b.cbytes > c.cbytes, "clevel not changed")

    def test02(self):
        """Testing copy() with lesser compression"""
        a = np.linspace(-1., 1., 1e4)
        b = ca.carray(a, rootdir=self.rootdir)
        c = b.copy(cparams=ca.cparams(clevel=1))
        #print "b.cbytes, c.cbytes:", b.cbytes, c.cbytes
        self.assert_(b.cbytes < c.cbytes, "clevel not changed")

    def test03(self):
        """Testing copy() with no shuffle"""
        a = np.linspace(-1., 1., 1e4)
        b = ca.carray(a, rootdir=self.rootdir)
        c = b.copy(cparams=ca.cparams(shuffle=False))
        #print "b.cbytes, c.cbytes:", b.cbytes, c.cbytes
        self.assert_(b.cbytes < c.cbytes, "shuffle not changed")

class copyDiskTest(copyTest):
    disk = True


class iterTest(MayBeDiskTest):

    def test00(self):
        """Testing `iter()` method"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter1->", sum(b)
        #print "sum iter2->", sum((v for v in b))
        self.assert_(sum(a) == sum(b), "Sums are not equal")
        self.assert_(sum((v for v in a)) == sum((v for v in b)),
                     "Sums are not equal")

    def test01a(self):
        """Testing `iter()` method with a positive start"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter->", sum(b.iter(3))
        self.assert_(sum(a[3:]) == sum(b.iter(3)), "Sums are not equal")

    def test01b(self):
        """Testing `iter()` method with a negative start"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter->", sum(b.iter(-3))
        self.assert_(sum(a[-3:]) == sum(b.iter(-3)), "Sums are not equal")

    def test02a(self):
        """Testing `iter()` method with positive start, stop"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter->", sum(b.iter(3, 24))
        self.assert_(sum(a[3:24]) == sum(b.iter(3, 24)), "Sums are not equal")

    def test02b(self):
        """Testing `iter()` method with negative start, stop"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter->", sum(b.iter(-24, -3))
        self.assert_(sum(a[-24:-3]) == sum(b.iter(-24, -3)),
                     "Sums are not equal")

    def test02c(self):
        """Testing `iter()` method with positive start, negative stop"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter->", sum(b.iter(24, -3))
        self.assert_(sum(a[24:-3]) == sum(b.iter(24, -3)),
                     "Sums are not equal")

    def test03a(self):
        """Testing `iter()` method with only step"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter->", sum(b.iter(step=4))
        self.assert_(sum(a[::4]) == sum(b.iter(step=4)),
                     "Sums are not equal")

    def test03b(self):
        """Testing `iter()` method with start, stop, step"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        #print "sum iter->", sum(b.iter(3, 24, 4))
        self.assert_(sum(a[3:24:4]) == sum(b.iter(3, 24, 4)),
                     "Sums are not equal")

    def test03c(self):
        """Testing `iter()` method with negative step"""
        a = np.arange(101)
        b = ca.carray(a, chunklen=2, rootdir=self.rootdir)
        self.assertRaises(NotImplementedError, b.iter, 0, 1, -3)

    def test04(self):
        """Testing `iter()` method with large zero arrays"""
        a = np.zeros(1e4, dtype='f8')
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        c = ca.fromiter((v for v in b), dtype='f8', count=len(a))
        #print "c ->", repr(c)
        assert_array_equal(a, c[:], "iterator fails on zeros")

    def test05(self):
        """Testing `iter()` method with `limit`"""
        a = np.arange(1e4, dtype='f8')
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        c = ca.fromiter((v for v in b.iter(limit=1010)), dtype='f8',
                        count=1010)
        #print "c ->", repr(c)
        assert_array_equal(a[:1010], c, "iterator fails on zeros")

    def test06(self):
        """Testing `iter()` method with `skip`"""
        a = np.arange(1e4, dtype='f8')
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        c = ca.fromiter((v for v in b.iter(skip=1010)), dtype='f8',
                        count=10000-1010)
        #print "c ->", repr(c)
        assert_array_equal(a[1010:], c, "iterator fails on zeros")

    def test07(self):
        """Testing `iter()` method with `limit` and `skip`"""
        a = np.arange(1e4, dtype='f8')
        b = ca.carray(a, chunklen=100, rootdir=self.rootdir)
        c = ca.fromiter((v for v in b.iter(limit=1010, skip=1010)), dtype='f8',
                        count=1010)
        #print "c ->", repr(c)
        assert_array_equal(a[1010:2020], c, "iterator fails on zeros")

class iterDiskTest(iterTest):
    disk = True


class wheretrueTest(unittest.TestCase):

    def test00(self):
        """Testing `wheretrue()` iterator (all true values)"""
        a = np.arange(1, 11) > 0
        b = ca.carray(a)
        wt = a.nonzero()[0].tolist()
        cwt = [i for i in b.wheretrue()]
        #print "numpy ->", a.nonzero()[0].tolist()
        #print "where ->", [i for i in b.wheretrue()]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")

    def test01(self):
        """Testing `wheretrue()` iterator (all false values)"""
        a = np.arange(1, 11) < 0
        b = ca.carray(a)
        wt = a.nonzero()[0].tolist()
        cwt = [i for i in b.wheretrue()]
        #print "numpy ->", a.nonzero()[0].tolist()
        #print "where ->", [i for i in b.wheretrue()]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")

    def test02(self):
        """Testing `wheretrue()` iterator (all false values, large array)"""
        a = np.arange(1, 1e5) < 0
        b = ca.carray(a)
        wt = a.nonzero()[0].tolist()
        cwt = [i for i in b.wheretrue()]
        #print "numpy ->", a.nonzero()[0].tolist()
        #print "where ->", [i for i in b.wheretrue()]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")

    def test03(self):
        """Testing `wheretrue()` iterator (mix of true/false values)"""
        a = np.arange(1, 11) > 5
        b = ca.carray(a)
        wt = a.nonzero()[0].tolist()
        cwt = [i for i in b.wheretrue()]
        #print "numpy ->", a.nonzero()[0].tolist()
        #print "where ->", [i for i in b.wheretrue()]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")

    def test04(self):
        """Testing `wheretrue()` iterator with `limit`"""
        a = np.arange(1, 11) > 5
        b = ca.carray(a)
        wt = a.nonzero()[0].tolist()[:3]
        cwt = [i for i in b.wheretrue(limit=3)]
        #print "numpy ->", a.nonzero()[0].tolist()[:3]
        #print "where ->", [i for i in b.wheretrue(limit=3)]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")

    def test05(self):
        """Testing `wheretrue()` iterator with `skip`"""
        a = np.arange(1, 11) > 5
        b = ca.carray(a)
        wt = a.nonzero()[0].tolist()[2:]
        cwt = [i for i in b.wheretrue(skip=2)]
        #print "numpy ->", a.nonzero()[0].tolist()[2:]
        #print "where ->", [i for i in b.wheretrue(skip=2)]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")

    def test06(self):
        """Testing `wheretrue()` iterator with `limit` and `skip`"""
        a = np.arange(1, 11) > 5
        b = ca.carray(a)
        wt = a.nonzero()[0].tolist()[2:4]
        cwt = [i for i in b.wheretrue(skip=2, limit=2)]
        #print "numpy ->", a.nonzero()[0].tolist()[2:4]
        #print "where ->", [i for i in b.wheretrue(limit=2,skip=2)]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")

    def test07(self):
        """Testing `wheretrue()` iterator with `limit` and `skip` (zeros)"""
        a = np.arange(10000) > 5000
        b = ca.carray(a, chunklen=100)
        wt = a.nonzero()[0].tolist()[1020:2040]
        cwt = [i for i in b.wheretrue(skip=1020, limit=1020)]
        # print "numpy ->", a.nonzero()[0].tolist()[1020:2040]
        # print "where ->", [i for i in b.wheretrue(limit=1020,skip=1020)]
        self.assert_(wt == cwt, "wheretrue() does not work correctly")


class whereTest(unittest.TestCase):

    def test00(self):
        """Testing `where()` iterator (all true values)"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v>0]
        cwt = [v for v in b.where(a>0)]
        #print "numpy ->", [v for v in a if v>0]
        #print "where ->", [v for v in b.where(a>0)]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test01(self):
        """Testing `where()` iterator (all false values)"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<0]
        cwt = [v for v in b.where(a<0)]
        #print "numpy ->", [v for v in a if v<0]
        #print "where ->", [v for v in b.where(a<0)]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test02a(self):
        """Testing `where()` iterator (mix of true/false values, I)"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<=5]
        cwt = [v for v in b.where(a<=5)]
        #print "numpy ->", [v for v in a if v<=5]
        #print "where ->", [v for v in b.where(a<=5)]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test02b(self):
        """Testing `where()` iterator (mix of true/false values, II)"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<=5 and v>2]
        cwt = [v for v in b.where((a<=5) & (a>2))]
        #print "numpy ->", [v for v in a if v<=5 and v>2]
        #print "where ->", [v for v in b.where((a<=5) & (a>2))]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test02c(self):
        """Testing `where()` iterator (mix of true/false values, III)"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<=5 or v>8]
        cwt = [v for v in b.where((a<=5) | (a>8))]
        #print "numpy ->", [v for v in a if v<=5 or v>8]
        #print "where ->", [v for v in b.where((a<=5) | (a>8))]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test03(self):
        """Testing `where()` iterator (using a boolean carray)"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<=5]
        cwt = [v for v in b.where(ca.carray(a<=5))]
        #print "numpy ->", [v for v in a if v<=5]
        #print "where ->", [v for v in b.where(ca.carray(a<=5))]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test04(self):
        """Testing `where()` iterator using `limit`"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<=5][:3]
        cwt = [v for v in b.where(ca.carray(a<=5), limit=3)]
        #print "numpy ->", [v for v in a if v<=5][:3]
        #print "where ->", [v for v in b.where(ca.carray(a<=5), limit=3)]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test05(self):
        """Testing `where()` iterator using `skip`"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<=5][2:]
        cwt = [v for v in b.where(ca.carray(a<=5), skip=2)]
        #print "numpy ->", [v for v in a if v<=5][2:]
        #print "where ->", [v for v in b.where(ca.carray(a<=5), skip=2)]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test06(self):
        """Testing `where()` iterator using `limit` and `skip`"""
        a = np.arange(1, 11)
        b = ca.carray(a)
        wt = [v for v in a if v<=5][1:4]
        cwt = [v for v in b.where(ca.carray(a<=5), limit=3, skip=1)]
        #print "numpy ->", [v for v in a if v<=5][1:4]
        #print "where ->", [v for v in b.where(ca.carray(a<=5),
        #                                      limit=3, skip=1)]
        self.assert_(wt == cwt, "where() does not work correctly")

    def test07(self):
        """Testing `where()` iterator using `limit` and `skip` (zeros)"""
        a = np.arange(10000)
        b = ca.carray(a,)
        wt = [v for v in a if v<=5000][1010:2020]
        cwt = [v for v in b.where(ca.carray(a<=5000, chunklen=100),
                                  limit=1010, skip=1010)]
        # print "numpy ->", [v for v in a if v>=5000][1010:2020]
        # print "where ->", [v for v in b.where(ca.carray(a>=5000,chunklen=100),
        #                                       limit=1010, skip=1010)]
        self.assert_(wt == cwt, "where() does not work correctly")


class fancy_indexing_getitemTest(unittest.TestCase):

    def test00(self):
        """Testing fancy indexing (short list)"""
        a = np.arange(1,111)
        b = ca.carray(a)
        c = b[[3,1]]
        r = a[[3,1]]
        assert_array_equal(c, r, "fancy indexing does not work correctly")

    def test01(self):
        """Testing fancy indexing (large list, numpy)"""
        a = np.arange(1,1e4)
        b = ca.carray(a)
        idx = np.random.randint(1000, size=1000)
        c = b[idx]
        r = a[idx]
        assert_array_equal(c, r, "fancy indexing does not work correctly")

    def test02(self):
        """Testing fancy indexing (empty list)"""
        a = np.arange(101)
        b = ca.carray(a)
        c = b[[]]
        r = a[[]]
        assert_array_equal(c, r, "fancy indexing does not work correctly")

    def test03(self):
        """Testing fancy indexing (list of floats)"""
        a = np.arange(1,101)
        b = ca.carray(a)
        c = b[[1.1, 3.3]]
        r = a[[1.1, 3.3]]
        assert_array_equal(c, r, "fancy indexing does not work correctly")

    def test04(self):
        """Testing fancy indexing (list of floats, numpy)"""
        a = np.arange(1,101)
        b = ca.carray(a)
        idx = np.array([1.1, 3.3], dtype='f8')
        self.assertRaises(IndexError, b.__getitem__, idx)

    def test05(self):
        """Testing `where()` iterator (using bool in fancy indexing)"""
        a = np.arange(1, 110)
        b = ca.carray(a, chunklen=10)
        wt = a[a<5]
        cwt = b[a<5]
        #print "numpy ->", a[a<5]
        #print "where ->", b[a<5]
        assert_array_equal(wt, cwt, "where() does not work correctly")

    def test06(self):
        """Testing `where()` iterator (using carray bool in fancy indexing)"""
        a = np.arange(1, 110)
        b = ca.carray(a, chunklen=10)
        wt = a[(a<5)|(a>9)]
        cwt = b[ca.carray((a<5)|(a>9))]
        #print "numpy ->", a[(a<5)|(a>9)]
        #print "where ->", b[ca.carray((a<5)|(a>9))]
        assert_array_equal(wt, cwt, "where() does not work correctly")


class fancy_indexing_setitemTest(unittest.TestCase):

    def test00(self):
        """Testing fancy indexing with __setitem__ (small values)"""
        a = np.arange(1,111)
        b = ca.carray(a, chunklen=10)
        sl = [3, 1]
        b[sl] = (10, 20)
        a[sl] = (10, 20)
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(b[:], a, "fancy indexing does not work correctly")

    def test01(self):
        """Testing fancy indexing with __setitem__ (large values)"""
        a = np.arange(1,1e3)
        b = ca.carray(a, chunklen=10)
        sl = [0, 300, 998]
        b[sl] = (5, 10, 20)
        a[sl] = (5, 10, 20)
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(b[:], a, "fancy indexing does not work correctly")

    def test02(self):
        """Testing fancy indexing with __setitem__ (large list)"""
        a = np.arange(0,1000)
        b = ca.carray(a, chunklen=10)
        sl = np.random.randint(0, 1000, size=3*30)
        vals = np.random.randint(1, 1000, size=3*30)
        b[sl] = vals
        a[sl] = vals
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(b[:], a, "fancy indexing does not work correctly")

    def test03(self):
        """Testing fancy indexing with __setitem__ (bool array)"""
        a = np.arange(1,1e2)
        b = ca.carray(a, chunklen=10)
        sl = a > 5
        b[sl] = 3.
        a[sl] = 3.
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(b[:], a, "fancy indexing does not work correctly")

    def test04(self):
        """Testing fancy indexing with __setitem__ (bool carray)"""
        a = np.arange(1,1e2)
        b = ca.carray(a, chunklen=10)
        bc = (a > 5) & (a < 40)
        sl = ca.carray(bc)
        b[sl] = 3.
        a[bc] = 3.
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(b[:], a, "fancy indexing does not work correctly")

    def test05(self):
        """Testing fancy indexing with __setitem__ (bool, value not scalar)"""
        a = np.arange(1,1e2)
        b = ca.carray(a, chunklen=10)
        sl = a < 5
        b[sl] = range(6, 10)
        a[sl] = range(6, 10)
        #print "b[%s] -> %r" % (sl, b)
        assert_array_equal(b[:], a, "fancy indexing does not work correctly")


class fromiterTest(unittest.TestCase):

    def test00(self):
        """Testing fromiter (short iter)"""
        a = np.arange(1,111)
        b = ca.fromiter(iter(a), dtype='i4', count=len(a))
        assert_array_equal(b[:], a, "fromiter does not work correctly")

    def test01a(self):
        """Testing fromiter (long iter)"""
        N = 1e4
        a = (i for i in xrange(int(N)))
        b = ca.fromiter(a, dtype='f8', count=int(N))
        c = np.arange(N)
        assert_array_equal(b[:], c, "fromiter does not work correctly")

    def test01b(self):
        """Testing fromiter (long iter, chunk is multiple of iter length)"""
        N = 1e4
        a = (i for i in xrange(int(N)))
        b = ca.fromiter(a, dtype='f8', chunklen=1000, count=int(N))
        c = np.arange(N)
        assert_array_equal(b[:], c, "fromiter does not work correctly")

    def test02(self):
        """Testing fromiter (empty iter)"""
        a = np.array([], dtype="f8")
        b = ca.fromiter(iter(a), dtype='f8', count=-1)
        assert_array_equal(b[:], a, "fromiter does not work correctly")

    def test03(self):
        """Testing fromiter (dtype conversion)"""
        a = np.arange(101, dtype="f8")
        b = ca.fromiter(iter(a), dtype='f4', count=len(a))
        assert_array_equal(b[:], a, "fromiter does not work correctly")

    def test04a(self):
        """Testing fromiter method with large iterator"""
        N = 10*1000
        a = np.fromiter((i*2 for i in xrange(N)), dtype='f8')
        b = ca.fromiter((i*2 for i in xrange(N)), dtype='f8', count=len(a))
        assert_array_equal(b[:], a, "iterator with a hint fails")

    def test04b(self):
        """Testing fromiter method with large iterator with a hint"""
        N = 10*1000
        a = np.fromiter((i*2 for i in xrange(N)), dtype='f8', count=N)
        b = ca.fromiter((i*2 for i in xrange(N)), dtype='f8', count=N)
        assert_array_equal(b[:], a, "iterator with a hint fails")


class evalTest(MayBeDiskTest):

    vm = "python"

    def setUp(self):
        self.prev_vm = ca.defaults.eval_vm
        ca.defaults.eval_vm = self.vm
        MayBeDiskTest.setUp(self)

    def tearDown(self):
        ca.defaults.eval_vm = self.prev_vm
        MayBeDiskTest.tearDown(self)

    def test00(self):
        """Testing eval() with only scalars and constants"""
        a = 3
        cr = ca.eval("2 * a", rootdir=self.rootdir)
        #print "ca.eval ->", cr
        self.assert_(cr == 6, "eval does not work correctly")

    def test01(self):
        """Testing eval() with only carrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        if self.rootdir:
            dirc, dird = self.rootdir+'.c', self.rootdir+'.d'
        else:
            dirc, dird = None, None
        c = ca.carray(a, rootdir=dirc)
        d = ca.carray(b, rootdir=dird)
        cr = ca.eval("c * d")
        nr = a * b
        #print "ca.eval ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test02(self):
        """Testing eval() with only ndarrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        cr = ca.eval("a * b", rootdir=self.rootdir)
        nr = a * b
        #print "ca.eval ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test03(self):
        """Testing eval() with a mix of carrays and ndarrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        if self.rootdir:
            dirc, dird = self.rootdir+'.c', self.rootdir+'.d'
        else:
            dirc, dird = None, None
        c = ca.carray(a, rootdir=dirc)
        d = ca.carray(b, rootdir=dird)
        cr = ca.eval("a * d")
        nr = a * b
        #print "ca.eval ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test04(self):
        """Testing eval() with a mix of carray, ndarray and scalars"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        if self.rootdir:
            dirc, dird = self.rootdir+'.c', self.rootdir+'.d'
        else:
            dirc, dird = None, None
        c = ca.carray(a, rootdir=dirc)
        d = ca.carray(b, rootdir=dird)
        cr = ca.eval("a + 2 * d - 3")
        nr = a + 2 * b - 3
        #print "ca.eval ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test05(self):
        """Testing eval() with a mix of carray, ndarray and scalars"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c, d = ca.carray(a, rootdir=self.rootdir), b
        cr = ca.eval("a + 2 * d - 3")
        nr = a + 2 * b - 3
        #print "ca.eval ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test06(self):
        """Testing eval() with only scalars and arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c, d = ca.carray(a, rootdir=self.rootdir), b
        cr = ca.eval("d - 3")
        nr = b - 3
        #print "ca.eval ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test07(self):
        """Testing eval() via expression on __getitem__"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c, d = ca.carray(a, rootdir=self.rootdir), b
        cr = c["a + 2 * d - 3 > 0"]
        nr = a[(a + 2 * b - 3) > 0]
        #print "ca[expr] ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "carray[expr] does not work correctly")

    def test08(self):
        """Testing eval() via expression with lists (raise ValueError)"""
        a, b = range(int(self.N)), range(int(self.N))
        self.assertRaises(ValueError, ca.eval, "a*3", depth=3,
                          rootdir=self.rootdir)
        self.assertRaises(ValueError, ca.eval, "b*3", depth=3,
                          rootdir=self.rootdir)

    def test09(self):
        """Testing eval() via expression on __setitem__ (I)"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c, d = ca.carray(a, rootdir=self.rootdir), b
        c["a + 2 * d - 3 > 0"] = 3
        a[(a + 2 * b - 3) > 0] = 3
        #print "carray ->", c
        #print "numpy  ->", a
        assert_array_equal(c[:], a, "carray[expr] = v does not work correctly")

    def test10(self):
        """Testing eval() via expression on __setitem__ (II)"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c, d = ca.carray(a, rootdir=self.rootdir), b
        c["a + 2 * d - 3 > 1000"] = 0
        a[(a + 2 * b - 3) > 1000] = 0
        #print "carray ->", c
        #print "numpy  ->", a
        assert_array_equal(c[:], a, "carray[expr] = v does not work correctly")

    def test11(self):
        """Testing eval() with functions like `np.sin()`"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c, d = ca.carray(a, rootdir=self.rootdir), ca.carray(b)
        if self.vm == "python":
            cr = ca.eval("np.sin(c) + 2 * np.log(d) - 3")
        else:
            cr = ca.eval("sin(c) + 2 * log(d) - 3")
        nr = np.sin(a) + 2 * np.log(b) - 3
        #print "ca.eval ->", cr
        #print "numpy   ->", nr
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test12(self):
        """Testing eval() with `out_flavor` == 'numpy'"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c, d = ca.carray(a), ca.carray(b, rootdir=self.rootdir)
        cr = ca.eval("c + 2 * d - 3", out_flavor='numpy')
        nr = a + 2 * b - 3
        #print "ca.eval ->", cr, type(cr)
        #print "numpy   ->", nr
        self.assert_(type(cr) == np.ndarray)
        assert_array_equal(cr, nr, "eval does not work correctly")

class evalSmall(evalTest):
    N = 10

class evalDiskSmall(evalTest):
    N = 10
    disk = True

class evalBig(evalTest):
    N = 1e4

class evalDiskBig(evalTest):
    N = 1e4
    disk = True

class evalSmallNE(evalTest):
    N = 10
    vm = "numexpr"

class evalDiskSmallNE(evalTest):
    N = 10
    vm = "numexpr"
    disk = True

class evalBigNE(evalTest):
    N = 1e4
    vm = "numexpr"

class evalDiskBigNE(evalTest):
    N = 1e4
    vm = "numexpr"
    disk = True


class computeMethodsTest(unittest.TestCase):

    def test00(self):
        """Testing sum()."""
        a = np.arange(1e5)
        sa = a.sum()
        ac = ca.carray(a)
        sac = ac.sum()
        #print "numpy sum-->", sa
        #print "carray sum-->", sac
        self.assert_(sa.dtype == sac.dtype, "sum() is not working correctly.")
        self.assert_(sa == sac, "sum() is not working correctly.")

    def test01(self):
        """Testing sum() with dtype."""
        a = np.arange(1e5)
        sa = a.sum(dtype='i8')
        ac = ca.carray(a)
        sac = ac.sum(dtype='i8')
        #print "numpy sum-->", sa
        #print "carray sum-->", sac
        self.assert_(sa.dtype == sac.dtype, "sum() is not working correctly.")
        self.assert_(sa == sac, "sum() is not working correctly.")

    def test02(self):
        """Testing sum() with strings (TypeError)."""
        ac = ca.zeros(10, 'S3')
        self.assertRaises(TypeError, ac.sum)


class arangeTest(unittest.TestCase):

    def test00(self):
        """Testing arange() with only a `stop`."""
        a = np.arange(self.N)
        ac = ca.arange(self.N)
        self.assert_(np.all(a == ac))

    def test01(self):
        """Testing arange() with a `start` and `stop`."""
        a = np.arange(3, self.N)
        ac = ca.arange(3, self.N)
        self.assert_(np.all(a == ac))

    def test02(self):
        """Testing arange() with a `start`, `stop` and `step`."""
        a = np.arange(3, self.N, 4)
        ac = ca.arange(3, self.N, 4)
        self.assert_(np.all(a == ac))

    def test03(self):
        """Testing arange() with a `dtype`."""
        a = np.arange(self.N, dtype="i1")
        ac = ca.arange(self.N, dtype="i1")
        self.assert_(np.all(a == ac))

class arange_smallTest(arangeTest):
    N = 10

class arange_bigTest(arangeTest):
    N = 1e4


class constructorTest(MayBeDiskTest):

    def test00(self):
        """Testing carray constructor with an int32 `dtype`."""
        a = np.arange(self.N)
        ac = ca.carray(a, dtype='i4', rootdir=self.rootdir)
        self.assert_(ac.dtype == np.dtype('i4'))
        a = a.astype('i4')
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test01a(self):
        """Testing zeros() constructor."""
        a = np.zeros(self.N)
        ac = ca.zeros(self.N, rootdir=self.rootdir)
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test01b(self):
        """Testing zeros() constructor, with a `dtype`."""
        a = np.zeros(self.N, dtype='i4')
        ac = ca.zeros(self.N, dtype='i4', rootdir=self.rootdir)
        #print "dtypes-->", a.dtype, ac.dtype
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test01c(self):
        """Testing zeros() constructor, with a string type."""
        a = np.zeros(self.N, dtype='S5')
        ac = ca.zeros(self.N, dtype='S5', rootdir=self.rootdir)
        #print "ac-->", `ac`
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test02a(self):
        """Testing ones() constructor."""
        a = np.ones(self.N)
        ac = ca.ones(self.N, rootdir=self.rootdir)
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test02b(self):
        """Testing ones() constructor, with a `dtype`."""
        a = np.ones(self.N, dtype='i4')
        ac = ca.ones(self.N, dtype='i4', rootdir=self.rootdir)
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test02c(self):
        """Testing ones() constructor, with a string type"""
        a = np.ones(self.N, dtype='S3')
        ac = ca.ones(self.N, dtype='S3', rootdir=self.rootdir)
        #print "a-->", a, ac
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test03a(self):
        """Testing fill() constructor."""
        a = np.ones(self.N)
        ac = ca.fill(self.N, 1, rootdir=self.rootdir)
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test03b(self):
        """Testing fill() constructor, with a `dtype`."""
        a = np.ones(self.N, dtype='i4')*3
        ac = ca.fill(self.N, 3, dtype='i4', rootdir=self.rootdir)
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))

    def test03c(self):
        """Testing fill() constructor, with a string type"""
        a = np.ones(self.N, dtype='S3')
        ac = ca.fill(self.N, "1", dtype='S3', rootdir=self.rootdir)
        #print "a-->", a, ac
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac[:]))


class constructorSmallTest(constructorTest):
    N = 10

class constructorSmallDiskTest(constructorTest):
    N = 10
    disk = True

class constructorBigTest(constructorTest):
    N = 50000

class constructorBigDiskTest(constructorTest):
    N = 50000
    disk = True


class dtypesTest(unittest.TestCase):

    def test00(self):
        """Testing carray constructor with a float32 `dtype`."""
        a = np.arange(10)
        ac = ca.carray(a, dtype='f4')
        self.assert_(ac.dtype == np.dtype('f4'))
        a = a.astype('f4')
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac))

    def test01(self):
        """Testing carray constructor with a `dtype` with an empty input."""
        a = np.array([], dtype='i4')
        ac = ca.carray([], dtype='f4')
        self.assert_(ac.dtype == np.dtype('f4'))
        a = a.astype('f4')
        self.assert_(a.dtype == ac.dtype)
        self.assert_(np.all(a == ac))

    def test02(self):
        """Testing carray constructor with a plain compound `dtype`."""
        dtype = np.dtype("f4,f8")
        a = np.ones(30000, dtype=dtype)
        ac = ca.carray(a, dtype=dtype)
        self.assert_(ac.dtype == dtype)
        self.assert_(a.dtype == ac.dtype)
        #print "ac-->", `ac`
        assert_array_equal(a, ac[:], "Arrays are not equal")

    def test03(self):
        """Testing carray constructor with a nested compound `dtype`."""
        dtype = np.dtype([('f1', [('f1', 'i2'), ('f2', 'i4')])])
        a = np.ones(3000, dtype=dtype)
        ac = ca.carray(a, dtype=dtype)
        self.assert_(ac.dtype == dtype)
        self.assert_(a.dtype == ac.dtype)
        #print "ac-->", `ac`
        assert_array_equal(a, ac[:], "Arrays are not equal")

    def test04(self):
        """Testing carray constructor with a string `dtype`."""
        a = np.array(["ale", "e", "aco"], dtype="S4")
        ac = ca.carray(a, dtype='S4')
        self.assert_(ac.dtype == np.dtype('S4'))
        self.assert_(a.dtype == ac.dtype)
        #print "ac-->", `ac`
        assert_array_equal(a, ac, "Arrays are not equal")

    def test05(self):
        """Testing carray constructor with a unicode `dtype`."""
        a = np.array([u"aŀle", u"eñe", u"açò"], dtype="U4")
        ac = ca.carray(a, dtype='U4')
        self.assert_(ac.dtype == np.dtype('U4'))
        self.assert_(a.dtype == ac.dtype)
        #print "ac-->", `ac`
        assert_array_equal(a, ac, "Arrays are not equal")

    def test06(self):
        """Testing carray constructor with an object `dtype`."""
        dtype = np.dtype("object")
        a = np.array(["ale", "e", "aco"], dtype=dtype)
        self.assertRaises(TypeError, ca.carray, a)


class largeCarrayTest(MayBeDiskTest):

    disk = True

    def test00(self):
        """Creating an extremely large carray (> 2**32) in memory."""

        cn = ca.zeros(5e9, dtype="i1")
        self.assert_(len(cn) == int(5e9))

        # Now check some accesses
        cn[1] = 1
        self.assert_(cn[1] == 1)
        cn[int(2e9)] = 2
        self.assert_(cn[int(2e9)] == 2)
        cn[long(3e9)] = 3
        self.assert_(cn[long(3e9)] == 3)
        cn[-1] = 4
        self.assert_(cn[-1] == 4)

        self.assert_(cn.sum() == 10)

    def test01(self):
        """Creating an extremely large carray (> 2**32) on disk."""

        cn = ca.zeros(5e9, dtype="i1", rootdir=self.rootdir)
        self.assert_(len(cn) == int(5e9))

        # Now check some accesses
        cn[1] = 1
        self.assert_(cn[1] == 1)
        cn[int(2e9)] = 2
        self.assert_(cn[int(2e9)] == 2)
        cn[long(3e9)] = 3
        self.assert_(cn[long(3e9)] == 3)
        cn[-1] = 4
        self.assert_(cn[-1] == 4)

        self.assert_(cn.sum() == 10)

    def test02(self):
        """Opening an extremely large carray (> 2**32) on disk."""

        # Create the array on-disk
        cn = ca.zeros(5e9, dtype="i1", rootdir=self.rootdir)
        self.assert_(len(cn) == int(5e9))
        # Reopen it from disk
        cn = ca.carray(rootdir=self.rootdir)
        self.assert_(len(cn) == int(5e9))

        # Now check some accesses
        cn[1] = 1
        self.assert_(cn[1] == 1)
        cn[int(2e9)] = 2
        self.assert_(cn[int(2e9)] == 2)
        cn[long(3e9)] = 3
        self.assert_(cn[long(3e9)] == 3)
        cn[-1] = 4
        self.assert_(cn[-1] == 4)

        self.assert_(cn.sum() == 10)


class persistenceTest(MayBeDiskTest):

    disk = True

    def test01a(self):
        """Creating a carray in "r" mode."""

        N = 10000
        self.assertRaises(RuntimeError, ca.zeros, 
                          N, dtype="i1", rootdir=self.rootdir, mode='r')

    def test01b(self):
        """Creating a carray in "w" mode."""

        N = 50000
        cn = ca.zeros(N, dtype="i1", rootdir=self.rootdir)
        self.assert_(len(cn) == N)

        cn = ca.zeros(N-2, dtype="i1", rootdir=self.rootdir, mode='w')
        self.assert_(len(cn) == N-2)

        # Now check some accesses (no errors should be raised)
        cn.append([1,1])
        self.assert_(len(cn) == N)
        cn[1] = 2
        self.assert_(cn[1] == 2)

    def test01c(self):
        """Creating a carray in "a" mode."""

        N = 30003
        cn = ca.zeros(N, dtype="i1", rootdir=self.rootdir)
        self.assert_(len(cn) == N)

        self.assertRaises(RuntimeError, ca.zeros, 
                          N-2, dtype="i1", rootdir=self.rootdir, mode='a')

    def test02a(self):
        """Opening a carray in "r" mode."""

        N = 10001
        cn = ca.zeros(N, dtype="i1", rootdir=self.rootdir)
        self.assert_(len(cn) == N)

        cn = ca.carray(rootdir=self.rootdir, mode='r')
        self.assert_(len(cn) == N)

        # Now check some accesses
        self.assertRaises(RuntimeError, cn.__setitem__, 1, 1)
        self.assertRaises(RuntimeError, cn.append, 1)

    def test02b(self):
        """Opening a carray in "w" mode."""

        N = 100001
        cn = ca.zeros(N, dtype="i1", rootdir=self.rootdir)
        self.assert_(len(cn) == N)

        cn = ca.carray(rootdir=self.rootdir, mode='w')
        self.assert_(len(cn) == 0)

        # Now check some accesses (no errors should be raised)
        cn.append([1,1])
        self.assert_(len(cn) == 2)
        cn[1] = 2
        self.assert_(cn[1] == 2)

    def test02c(self):
        """Opening a carray in "a" mode."""

        N = 1000-1
        cn = ca.zeros(N, dtype="i1", rootdir=self.rootdir)
        self.assert_(len(cn) == N)

        cn = ca.carray(rootdir=self.rootdir, mode='a')
        self.assert_(len(cn) == N)

        # Now check some accesses (no errors should be raised)
        cn.append([1,1])
        self.assert_(len(cn) == N+2)
        cn[1] = 2
        self.assert_(cn[1] == 2)
        cn[N+1] = 3
        self.assert_(cn[N+1] == 3)


def suite():
    theSuite = unittest.TestSuite()

    theSuite.addTest(unittest.makeSuite(chunkTest))
    theSuite.addTest(unittest.makeSuite(getitemTest))
    theSuite.addTest(unittest.makeSuite(getitemDiskTest))
    theSuite.addTest(unittest.makeSuite(setitemTest))
    theSuite.addTest(unittest.makeSuite(setitemDiskTest))
    theSuite.addTest(unittest.makeSuite(appendTest))
    theSuite.addTest(unittest.makeSuite(appendDiskTest))
    theSuite.addTest(unittest.makeSuite(trimTest))
    theSuite.addTest(unittest.makeSuite(trimDiskTest))
    theSuite.addTest(unittest.makeSuite(resize_smallTest))
    theSuite.addTest(unittest.makeSuite(resize_smallDiskTest))
    theSuite.addTest(unittest.makeSuite(resize_largeTest))
    theSuite.addTest(unittest.makeSuite(resize_largeDiskTest))
    theSuite.addTest(unittest.makeSuite(miscTest))
    theSuite.addTest(unittest.makeSuite(miscDiskTest))
    theSuite.addTest(unittest.makeSuite(copyTest))
    theSuite.addTest(unittest.makeSuite(copyDiskTest))
    theSuite.addTest(unittest.makeSuite(iterTest))
    theSuite.addTest(unittest.makeSuite(iterDiskTest))
    theSuite.addTest(unittest.makeSuite(wheretrueTest))
    theSuite.addTest(unittest.makeSuite(whereTest))
    theSuite.addTest(unittest.makeSuite(fancy_indexing_getitemTest))
    theSuite.addTest(unittest.makeSuite(fancy_indexing_setitemTest))
    theSuite.addTest(unittest.makeSuite(fromiterTest))
    theSuite.addTest(unittest.makeSuite(arange_smallTest))
    theSuite.addTest(unittest.makeSuite(arange_bigTest))
    theSuite.addTest(unittest.makeSuite(constructorSmallTest))
    theSuite.addTest(unittest.makeSuite(constructorSmallDiskTest))
    theSuite.addTest(unittest.makeSuite(constructorBigTest))
    theSuite.addTest(unittest.makeSuite(constructorBigDiskTest))
    theSuite.addTest(unittest.makeSuite(dtypesTest))
    theSuite.addTest(unittest.makeSuite(computeMethodsTest))
    theSuite.addTest(unittest.makeSuite(evalSmall))
    theSuite.addTest(unittest.makeSuite(evalDiskSmall))
    theSuite.addTest(unittest.makeSuite(evalBig))
    theSuite.addTest(unittest.makeSuite(evalDiskBig))
    theSuite.addTest(unittest.makeSuite(persistenceTest))
    if ca.numexpr_here:
        theSuite.addTest(unittest.makeSuite(evalSmallNE))
        theSuite.addTest(unittest.makeSuite(evalDiskSmallNE))
        theSuite.addTest(unittest.makeSuite(evalBigNE))
        theSuite.addTest(unittest.makeSuite(evalBigNE))

    # Only for 64-bit systems
    if is_64bit and common.heavy:
        theSuite.addTest(unittest.makeSuite(largeCarrayTest))

    return theSuite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 72
## End:

########NEW FILE########
__FILENAME__ = test_ctable
########################################################################
#
#       License: BSD
#       Created: September 1, 2010
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import sys

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import carray as ca
import unittest
from carray.tests import common
from common import MayBeDiskTest


class createTest(MayBeDiskTest):

    def test00a(self):
        """Testing ctable creation from a tuple of carrays"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir)
        #print "t->", `t`
        ra = np.rec.fromarrays([a[:],b[:]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test00b(self):
        """Testing ctable creation from a tuple of lists"""
        t = ca.ctable(([1,2,3],[4,5,6]), ('f0', 'f1'), rootdir=self.rootdir)
        #print "t->", `t`
        ra = np.rec.fromarrays([[1,2,3],[4,5,6]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test00c(self):
        """Testing ctable creation from a tuple of carrays (single column)"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        self.assertRaises(ValueError, ca.ctable, a, 'f0', rootdir=self.rootdir)

    def test01(self):
        """Testing ctable creation from a tuple of numpy arrays"""
        N = 1e1
        a = np.arange(N, dtype='i4')
        b = np.arange(N, dtype='f8')+1
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir)
        #print "t->", `t`
        ra = np.rec.fromarrays([a,b]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test02(self):
        """Testing ctable creation from an structured array"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test03a(self):
        """Testing ctable creation from large iterator"""
        N = 10*1000
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8',
                        count=N, rootdir=self.rootdir)
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test03b(self):
        """Testing ctable creation from large iterator (with a hint)"""
        N = 10*1000
        ra = np.fromiter(((i, i*2.) for i in xrange(N)),
                         dtype='i4,f8', count=N)
        t = ca.fromiter(((i, i*2.) for i in xrange(N)),
                        dtype='i4,f8', count=N, rootdir=self.rootdir)
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

class createDiskTest(createTest):
    disk = True


class persistentTest(MayBeDiskTest):

    disk = True

    def test00a(self):
        """Testing ctable opening in "r" mode"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir)
        # Open t
        t = ca.open(rootdir=self.rootdir, mode='r')
        #print "t->", `t`
        ra = np.rec.fromarrays([a[:],b[:]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

        # Now check some accesses
        self.assertRaises(RuntimeError, t.__setitem__, 1, (0, 0.0))
        self.assertRaises(RuntimeError, t.append, (0, 0.0))

    def test00b(self):
        """Testing ctable opening in "w" mode"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir)
        # Open t
        t = ca.open(rootdir=self.rootdir, mode='w')
        #print "t->", `t`
        N = 0
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        ra = np.rec.fromarrays([a[:],b[:]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

        # Now check some accesses
        t.append((0, 0.0))
        t.append((0, 0.0))
        t[1] = (1, 2.0)
        ra = np.rec.fromarrays([(0,1),(0.0, 2.0)], 'i4,f8').view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test00c(self):
        """Testing ctable opening in "a" mode"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir)
        # Open t
        t = ca.open(rootdir=self.rootdir, mode='a')
        #print "t->", `t`

        # Check values
        ra = np.rec.fromarrays([a[:],b[:]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

        # Now check some accesses
        t.append((10, 11.0))
        t.append((10, 11.0))
        t[-1] = (11, 12.0)

        # Check values
        N = 12
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        ra = np.rec.fromarrays([a[:],b[:]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01a(self):
        """Testing ctable creation in "r" mode"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        self.assertRaises(RuntimeError, ca.ctable, (a, b), ('f0', 'f1'),
                          rootdir=self.rootdir, mode='r')

    def test01b(self):
        """Testing ctable creation in "w" mode"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir)
        # Overwrite the last ctable
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir, mode='w')
        #print "t->", `t`
        ra = np.rec.fromarrays([a[:],b[:]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

        # Now check some accesses
        t.append((10, 11.0))
        t.append((10, 11.0))
        t[11] = (11, 12.0)

        # Check values
        N = 12
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        ra = np.rec.fromarrays([a[:],b[:]]).view(np.ndarray)
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01c(self):
        """Testing ctable creation in "a" mode"""
        N = 1e1
        a = ca.carray(np.arange(N, dtype='i4'))
        b = ca.carray(np.arange(N, dtype='f8')+1)
        t = ca.ctable((a, b), ('f0', 'f1'), rootdir=self.rootdir)
        # Overwrite the last ctable
        self.assertRaises(RuntimeError, ca.ctable, (a, b), ('f0', 'f1'),
                          rootdir=self.rootdir, mode='a')


class add_del_colTest(MayBeDiskTest):

    def test00a(self):
        """Testing adding a new column (list flavor)"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c = np.arange(N, dtype='i8')*3
        t.addcol(c.tolist(), 'f2')
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test00(self):
        """Testing adding a new column (carray flavor)"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c = np.arange(N, dtype='i8')*3
        t.addcol(ca.carray(c), 'f2')
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01a(self):
        """Testing adding a new column (numpy flavor)"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c = np.arange(N, dtype='i8')*3
        t.addcol(c, 'f2')
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01b(self):
        """Testing cparams when adding a new column (numpy flavor)"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, cparams=ca.cparams(1), rootdir=self.rootdir)
        c = np.arange(N, dtype='i8')*3
        t.addcol(c, 'f2')
        self.assert_(t['f2'].cparams.clevel == 1, "Incorrect clevel")

    def test02(self):
        """Testing adding a new column (default naming)"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c = np.arange(N, dtype='i8')*3
        t.addcol(ca.carray(c))
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test03(self):
        """Testing inserting a new column (at the beginning)"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c = np.arange(N, dtype='i8')*3
        t.addcol(c, name='c0', pos=0)
        ra = np.fromiter(((i*3, i, i*2.) for i in xrange(N)), dtype='i8,i4,f8')
        ra.dtype.names = ('c0', 'f0', 'f1')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test04(self):
        """Testing inserting a new column (in the middle)"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c = np.arange(N, dtype='i8')*3
        t.addcol(c, name='c0', pos=1)
        ra = np.fromiter(((i, i*3, i*2.) for i in xrange(N)), dtype='i4,i8,f8')
        ra.dtype.names = ('f0', 'c0', 'f1')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test05(self):
        """Testing removing an existing column (at the beginning)"""
        N = 10
        ra = np.fromiter(((i, i*3, i*2.) for i in xrange(N)), dtype='i4,i8,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        t.delcol(pos=0)
        # The next gives a segfault.  See:
        # http://projects.scipy.org/numpy/ticket/1598
        #ra = np.fromiter(((i*3, i*2) for i in xrange(N)), dtype='i8,f8')
        #ra.dtype.names = ('f1', 'f2')
        dt = np.dtype([('f1', 'i8'), ('f2', 'f8')])
        ra = np.fromiter(((i*3, i*2) for i in xrange(N)), dtype=dt)
        #print "t->", `t`
        #print "ra", ra
        #assert_array_equal(t[:], ra, "ctable values are not correct")

    def test06(self):
        """Testing removing an existing column (at the end)"""
        N = 10
        ra = np.fromiter(((i, i*3, i*2.) for i in xrange(N)), dtype='i4,i8,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        t.delcol(pos=2)
        ra = np.fromiter(((i, i*3) for i in xrange(N)), dtype='i4,i8')
        ra.dtype.names = ('f0', 'f1')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test07(self):
        """Testing removing an existing column (in the middle)"""
        N = 10
        ra = np.fromiter(((i, i*3, i*2.) for i in xrange(N)), dtype='i4,i8,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        t.delcol(pos=1)
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        ra.dtype.names = ('f0', 'f2')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test08(self):
        """Testing removing an existing column (by name)"""
        N = 10
        ra = np.fromiter(((i, i*3, i*2.) for i in xrange(N)), dtype='i4,i8,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        t.delcol('f1')
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        ra.dtype.names = ('f0', 'f2')
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[:], ra, "ctable values are not correct")

class add_del_colDiskTest(add_del_colTest):
    disk = True


class getitemTest(MayBeDiskTest):

    def test00(self):
        """Testing __getitem__ with only a start"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        start = 9
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[start], ra[start], "ctable values are not correct")

    def test01(self):
        """Testing __getitem__ with start, stop"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        start, stop = 3, 9
        #print "t->", `t`
        #print "ra[:]", ra[:]
        assert_array_equal(t[start:stop], ra[start:stop],
                           "ctable values are not correct")

    def test02(self):
        """Testing __getitem__ with start, stop, step"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        start, stop, step = 3, 9, 2
        #print "t->", `t[start:stop:step]`
        #print "ra->", ra[start:stop:step]
        assert_array_equal(t[start:stop:step], ra[start:stop:step],
                           "ctable values are not correct")

    def test03(self):
        """Testing __getitem__ with a column name"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        colname = "f1"
        #print "t->", `t[colname]`
        #print "ra->", ra[colname]
        assert_array_equal(t[colname][:], ra[colname],
                           "ctable values are not correct")

    def test04(self):
        """Testing __getitem__ with a list of column names"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        colnames = ["f0", "f2"]
        # For some version of NumPy (> 1.7) I cannot make use of
        # ra[colnames]   :-/
        ra2 = np.fromiter(((i, i*3) for i in xrange(N)), dtype='i4,i8')
        ra2.dtype.names = ('f0', 'f2')
        #print "t->", `t[colnames]`
        #print "ra2->", ra2
        assert_array_equal(t[colnames][:], ra2,
                           "ctable values are not correct")

class getitemDiskTest(getitemTest):
    disk = True


class setitemTest(MayBeDiskTest):

    def test00(self):
        """Testing __setitem__ with only a start"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, chunklen=10, rootdir=self.rootdir)
        sl = slice(9, None)
        t[sl] = (0, 1)
        ra[sl] = (0, 1)
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01(self):
        """Testing __setitem__ with only a stop"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, chunklen=10, rootdir=self.rootdir)
        sl = slice(None, 9, None)
        t[sl] = (0, 1)
        ra[sl] = (0, 1)
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test02(self):
        """Testing __setitem__ with a start, stop"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, chunklen=10, rootdir=self.rootdir)
        sl = slice(1,90, None)
        t[sl] = (0, 1)
        ra[sl] = (0, 1)
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test03(self):
        """Testing __setitem__ with a start, stop, step"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, chunklen=10, rootdir=self.rootdir)
        sl = slice(1,90, 2)
        t[sl] = (0, 1)
        ra[sl] = (0, 1)
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test04(self):
        """Testing __setitem__ with a large step"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, chunklen=10, rootdir=self.rootdir)
        sl = slice(1,43, 20)
        t[sl] = (0, 1)
        ra[sl] = (0, 1)
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

class setitemDiskTest(setitemTest):
    disk = True


class appendTest(MayBeDiskTest):

    def test00(self):
        """Testing append() with scalar values"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        t.append((N, N*2))
        ra = np.fromiter(((i, i*2.) for i in xrange(N+1)), dtype='i4,f8')
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01(self):
        """Testing append() with numpy arrays"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        a = np.arange(N, N+10, dtype='i4')
        b = np.arange(N, N+10, dtype='f8')*2.
        t.append((a, b))
        ra = np.fromiter(((i, i*2.) for i in xrange(N+10)), dtype='i4,f8')
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test02(self):
        """Testing append() with carrays"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        a = np.arange(N, N+10, dtype='i4')
        b = np.arange(N, N+10, dtype='f8')*2.
        t.append((ca.carray(a), ca.carray(b)))
        ra = np.fromiter(((i, i*2.) for i in xrange(N+10)), dtype='i4,f8')
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test03(self):
        """Testing append() with structured arrays"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        ra2 = np.fromiter(((i, i*2.) for i in xrange(N, N+10)), dtype='i4,f8')
        t.append(ra2)
        ra = np.fromiter(((i, i*2.) for i in xrange(N+10)), dtype='i4,f8')
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test04(self):
        """Testing append() with another ctable"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        ra2 = np.fromiter(((i, i*2.) for i in xrange(N, N+10)), dtype='i4,f8')
        t2 = ca.ctable(ra2)
        t.append(t2)
        ra = np.fromiter(((i, i*2.) for i in xrange(N+10)), dtype='i4,f8')
        assert_array_equal(t[:], ra, "ctable values are not correct")

class appendDiskTest(appendTest):
    disk = True


class trimTest(MayBeDiskTest):

    def test00(self):
        """Testing trim() with Python scalar values"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N-2)), dtype='i4,f8')
        t = ca.fromiter(((i, i*2.) for i in xrange(N)), 'i4,f8', N,
                       rootdir=self.rootdir)
        t.trim(2)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01(self):
        """Testing trim() with NumPy scalar values"""
        N = 10000
        ra = np.fromiter(((i, i*2.) for i in xrange(N-200)), dtype='i4,f8')
        t = ca.fromiter(((i, i*2.) for i in xrange(N)), 'i4,f8', N,
                        rootdir=self.rootdir)
        t.trim(np.int(200))
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test02(self):
        """Testing trim() with a complete trim"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(0)), dtype='i4,f8')
        t = ca.fromiter(((i, i*2.) for i in xrange(N)), 'i4,f8', N,
                        rootdir=self.rootdir)
        t.trim(N)
        self.assert_(len(ra) == len(t), "Lengths are not equal")

class trimDiskTest(trimTest):
    disk = True


class resizeTest(MayBeDiskTest):

    def test00(self):
        """Testing resize() (decreasing)"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N-2)), dtype='i4,f8')
        t = ca.fromiter(((i, i*2.) for i in xrange(N)), 'i4,f8', N,
                        rootdir=self.rootdir)
        t.resize(N-2)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01(self):
        """Testing resize() (increasing)"""
        N = 100
        ra = np.fromiter(((i, i*2.) for i in xrange(N+4)), dtype='i4,f8')
        t = ca.fromiter(((i, i*2.) for i in xrange(N)), 'i4,f8', N,
                        rootdir=self.rootdir)
        t.resize(N+4)
        ra['f0'][N:] = np.zeros(4)
        ra['f1'][N:] = np.zeros(4)
        assert_array_equal(t[:], ra, "ctable values are not correct")

class resizeDiskTest(resizeTest):
    disk=True


class copyTest(MayBeDiskTest):

    def test00(self):
        """Testing copy() without params"""
        N = 10
        ra = np.fromiter(((i, i*2.) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        if self.disk:
            rootdir = self.rootdir + "-test00"
        else:
            rootdir = self.rootdir
        t2 = t.copy(rootdir=rootdir, mode='w')
        a = np.arange(N, N+10, dtype='i4')
        b = np.arange(N, N+10, dtype='f8')*2.
        t2.append((a, b))
        ra = np.fromiter(((i, i*2.) for i in xrange(N+10)), dtype='i4,f8')
        self.assert_(len(t) == N, "copy() does not work correctly")
        self.assert_(len(t2) == N+10, "copy() does not work correctly")
        assert_array_equal(t2[:], ra, "ctable values are not correct")

    def test01(self):
        """Testing copy() with higher clevel"""
        N = 10*1000
        ra = np.fromiter(((i, i**2.2) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        if self.disk:
            # Copy over the same location should give an error
            self.assertRaises(RuntimeError,
                              t.copy,cparams=ca.cparams(clevel=9),
                              rootdir=self.rootdir, mode='w')
            return
        else:
            t2 = t.copy(cparams=ca.cparams(clevel=9),
                        rootdir=self.rootdir, mode='w')
        #print "cbytes in f1, f2:", t['f1'].cbytes, t2['f1'].cbytes
        self.assert_(t.cparams.clevel == ca.cparams().clevel)
        self.assert_(t2.cparams.clevel == 9)
        self.assert_(t['f1'].cbytes > t2['f1'].cbytes, "clevel not changed")

    def test02(self):
        """Testing copy() with lower clevel"""
        N = 10*1000
        ra = np.fromiter(((i, i**2.2) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        t2 = t.copy(cparams=ca.cparams(clevel=1))
        self.assert_(t.cparams.clevel == ca.cparams().clevel)
        self.assert_(t2.cparams.clevel == 1)
        #print "cbytes in f1, f2:", t['f1'].cbytes, t2['f1'].cbytes
        self.assert_(t['f1'].cbytes < t2['f1'].cbytes, "clevel not changed")

    def test03(self):
        """Testing copy() with no shuffle"""
        N = 10*1000
        ra = np.fromiter(((i, i**2.2) for i in xrange(N)), dtype='i4,f8')
        t = ca.ctable(ra)
        # print "t:", t, t.rootdir
        t2 = t.copy(cparams=ca.cparams(shuffle=False), rootdir=self.rootdir)
        #print "cbytes in f1, f2:", t['f1'].cbytes, t2['f1'].cbytes
        self.assert_(t['f1'].cbytes < t2['f1'].cbytes, "clevel not changed")

class copyDiskTest(copyTest):
    disk = True


class specialTest(unittest.TestCase):

    def test00(self):
        """Testing __len__()"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra)
        self.assert_(len(t) == len(ra), "Objects do not have the same length")

    def test01(self):
        """Testing __sizeof__() (big ctables)"""
        N = int(1e4)
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra)
        #print "size t uncompressed ->", t.nbytes
        #print "size t compressed   ->", t.cbytes
        self.assert_(sys.getsizeof(t) < t.nbytes,
                     "ctable does not seem to compress at all")

    def test02(self):
        """Testing __sizeof__() (small ctables)"""
        N = int(111)
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra)
        #print "size t uncompressed ->", t.nbytes
        #print "size t compressed   ->", t.cbytes
        self.assert_(sys.getsizeof(t) > t.nbytes,
                     "ctable compress too much??")


class evalTest(MayBeDiskTest):

    vm = "python"

    def setUp(self):
        self.prev_vm = ca.defaults.eval_vm
        ca.defaults.eval_vm = self.vm
        MayBeDiskTest.setUp(self)

    def tearDown(self):
        ca.defaults.eval_vm = self.prev_vm
        MayBeDiskTest.tearDown(self)

    def test00a(self):
        """Testing eval() with only columns"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        ctr = t.eval("f0 * f1 * f2")
        rar = ra['f0'] * ra['f1'] * ra['f2']
        #print "ctable ->", ctr
        #print "numpy  ->", rar
        assert_array_equal(ctr[:], rar, "ctable values are not correct")

    def test00b(self):
        """Testing eval() with only constants"""
        f0, f1, f2 = 1, 2, 3
        # Populate the name space with functions from math
        from math import sin
        ctr = ca.eval("f0 * f1 * sin(f2)")
        rar = f0 * f1 * sin(f2)
        #print "ctable ->", ctr
        #print "python ->", rar
        self.assert_(ctr == rar, "values are not correct")

    def test01(self):
        """Testing eval() with columns and constants"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        ctr = t.eval("f0 * f1 * 3")
        rar = ra['f0'] * ra['f1'] * 3
        #print "ctable ->", ctr
        #print "numpy  ->", rar
        assert_array_equal(ctr[:], rar, "ctable values are not correct")

    def test02(self):
        """Testing eval() with columns, constants and other variables"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        var_ = 10.
        ctr = t.eval("f0 * f2 * var_")
        rar = ra['f0'] * ra['f2'] * var_
        #print "ctable ->", ctr
        #print "numpy  ->", rar
        assert_array_equal(ctr[:], rar, "ctable values are not correct")

    def test03(self):
        """Testing eval() with columns and numexpr functions"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        if not ca.defaults.eval_vm == "numexpr":
            # Populate the name space with functions from numpy
            from numpy import sin
        ctr = t.eval("f0 * sin(f1)")
        rar = ra['f0'] * np.sin(ra['f1'])
        #print "ctable ->", ctr
        #print "numpy  ->", rar
        assert_array_almost_equal(ctr[:], rar, decimal=15,
                                  err_msg="ctable values are not correct")

    def test04(self):
        """Testing eval() with a boolean as output"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        ctr = t.eval("f0 >= f1")
        rar = ra['f0'] >= ra['f1']
        #print "ctable ->", ctr
        #print "numpy  ->", rar
        assert_array_equal(ctr[:], rar, "ctable values are not correct")

    def test05(self):
        """Testing eval() with a mix of columns and numpy arrays"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        a = np.arange(N)
        b = np.arange(N)
        ctr = t.eval("f0 + f1 - a + b")
        rar = ra['f0'] + ra['f1'] - a + b
        #print "ctable ->", ctr
        #print "numpy  ->", rar
        assert_array_equal(ctr[:], rar, "ctable values are not correct")

    def test06(self):
        """Testing eval() with a mix of columns, numpy arrays and carrays"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        a = np.arange(N)
        b = ca.arange(N)
        ctr = t.eval("f0 + f1 - a + b")
        rar = ra['f0'] + ra['f1'] - a + b
        #print "ctable ->", ctr
        #print "numpy  ->", rar
        assert_array_equal(ctr[:], rar, "ctable values are not correct")

class evalDiskTest(evalTest):
    disk = True

class eval_ne(evalTest):
    vm = "numexpr"

class eval_neDisk(evalTest):
    vm = "numexpr"
    disk = True


class fancy_indexing_getitemTest(unittest.TestCase):

    def test00(self):
        """Testing fancy indexing with a small list"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra)
        rt = t[[3,1]]
        rar = ra[[3,1]]
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test01(self):
        """Testing fancy indexing with a large numpy array"""
        N = 10*1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra)
        idx = np.random.randint(1000, size=1000)
        rt = t[idx]
        rar = ra[idx]
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test02(self):
        """Testing fancy indexing with an empty list"""
        N = 10*1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra)
        rt = t[[]]
        rar = ra[[]]
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test03(self):
        """Testing fancy indexing (list of floats)"""
        N = 101
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra)
        rt = t[[2.3, 5.6]]
        rar = ra[[2.3, 5.6]]
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test04(self):
        """Testing fancy indexing (list of floats, numpy)"""
        a = np.arange(1,101)
        b = ca.carray(a)
        idx = np.array([1.1, 3.3], dtype='f8')
        self.assertRaises(IndexError, b.__getitem__, idx)


class fancy_indexing_setitemTest(unittest.TestCase):

    def test00a(self):
        """Testing fancy indexing (setitem) with a small list"""
        N = 100
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = [3,1]
        t[sl] = (-1, -2, -3)
        ra[sl] = (-1, -2, -3)
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test00b(self):
        """Testing fancy indexing (setitem) with a small list (II)"""
        N = 100
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = [3,1]
        t[sl] = [(-1, -2, -3), (-3, -2, -1)]
        ra[sl] = [(-1, -2, -3), (-3, -2, -1)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test01(self):
        """Testing fancy indexing (setitem) with a large array"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = np.random.randint(N, size=100)
        t[sl] = (-1, -2, -3)
        ra[sl] = (-1, -2, -3)
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test02a(self):
        """Testing fancy indexing (setitem) with a boolean array (I)"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = np.random.randint(2, size=1000).astype('bool')
        t[sl] = [(-1, -2, -3)]
        ra[sl] = [(-1, -2, -3)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test02b(self):
        """Testing fancy indexing (setitem) with a boolean array (II)"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = np.random.randint(10, size=1000).astype('bool')
        t[sl] = [(-1, -2, -3)]
        ra[sl] = [(-1, -2, -3)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test03a(self):
        """Testing fancy indexing (setitem) with a boolean array (all false)"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = np.zeros(N, dtype="bool")
        t[sl] = [(-1, -2, -3)]
        ra[sl] = [(-1, -2, -3)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test03b(self):
        """Testing fancy indexing (setitem) with a boolean array (all true)"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = np.ones(N, dtype="bool")
        t[sl] = [(-1, -2, -3)]
        ra[sl] = [(-1, -2, -3)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test04a(self):
        """Testing fancy indexing (setitem) with a condition (all false)"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = "f0<0"
        sl2 = ra['f0'] < 0
        t[sl] = [(-1, -2, -3)]
        ra[sl2] = [(-1, -2, -3)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl2, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test04b(self):
        """Testing fancy indexing (setitem) with a condition (all true)"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = "f0>=0"
        sl2 = ra['f0'] >= 0
        t[sl] = [(-1, -2, -3)]
        ra[sl2] = [(-1, -2, -3)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl2, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test04c(self):
        """Testing fancy indexing (setitem) with a condition (mixed values)"""
        N = 1000
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = "(f0>0) & (f1 < 10)"
        sl2 = (ra['f0'] > 0) & (ra['f1'] < 10)
        t[sl] = [(-1, -2, -3)]
        ra[sl2] = [(-1, -2, -3)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl2, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")

    def test04d(self):
        """Testing fancy indexing (setitem) with a condition (diff values)"""
        N = 100
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=10)
        sl = "(f0>0) & (f1 < 10)"
        sl2 = (ra['f0'] > 0) & (ra['f1'] < 10)
        l = len(np.where(sl2)[0])
        t[sl] = [(-i, -i*2., -i*3) for i in xrange(l)]
        ra[sl2] = [(-i, -i*2., -i*3) for i in xrange(l)]
        #print "t[%s] -> %r" % (sl, t)
        #print "ra[%s] -> %r" % (sl2, ra)
        assert_array_equal(t[:], ra, "ctable values are not correct")


class iterTest(MayBeDiskTest):

    def test00(self):
        """Testing ctable.__iter__"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [r.f1 for r in t]
        nl = [r['f1'] for r in ra]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

    def test01(self):
        """Testing ctable.iter() without params"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [r.f1 for r in t.iter()]
        nl = [r['f1'] for r in ra]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

    def test02(self):
        """Testing ctable.iter() with start,stop,step"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [r.f1 for r in t.iter(1,9,3)]
        nl = [r['f1'] for r in ra[1:9:3]]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

    def test03(self):
        """Testing ctable.iter() with outcols"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [tuple(r) for r in t.iter(outcols='f2, nrow__, f0')]
        nl = [(r['f2'], i, r['f0']) for i, r in enumerate(ra)]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

    def test04(self):
        """Testing ctable.iter() with start,stop,step and outcols"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [r for r in t.iter(1,9,3, 'f2, nrow__ f0')]
        nl = [(r['f2'], r['f0'], r['f0']) for r in ra[1:9:3]]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

    def test05(self):
        """Testing ctable.iter() with start, stop, step and limit"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [r.f1 for r in t.iter(1,9,2, limit=3)]
        nl = [r['f1'] for r in ra[1:9:2][:3]]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

    def test06(self):
        """Testing ctable.iter() with start, stop, step and skip"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [r.f1 for r in t.iter(1,9,2, skip=3)]
        nl = [r['f1'] for r in ra[1:9:2][3:]]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

    def test07(self):
        """Testing ctable.iter() with start, stop, step and limit, skip"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, chunklen=4, rootdir=self.rootdir)
        cl = [r.f1 for r in t.iter(1,9,2, limit=2, skip=1)]
        nl = [r['f1'] for r in ra[1:9:2][1:3]]
        #print "cl ->", cl
        #print "nl ->", nl
        self.assert_(cl == nl, "iter not working correctily")

class iterDiskTest(iterTest):
    disk = True


class eval_getitemTest(MayBeDiskTest):

    def test00(self):
        """Testing __getitem__ with an expression (all false values)"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = t['f1 > f2']
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i > i*2.),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test01(self):
        """Testing __getitem__ with an expression (all true values)"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = t['f1 <= f2']
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i <= i*2.),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test02(self):
        """Testing __getitem__ with an expression (true/false values)"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = t['f1*4 >= f2*2']
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i*4 >= i*2.*2),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test03(self):
        """Testing __getitem__ with an invalid expression"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        # In t['f1*4 >= ppp'], 'ppp' variable name should be found
        self.assertRaises(NameError, t.__getitem__, 'f1*4 >= ppp')

    def test04a(self):
        """Testing __getitem__ with an expression with columns and ndarrays"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c2 = t['f2'][:]
        rt = t['f1*4 >= c2*2']
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i*4 >= i*2.*2),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test04b(self):
        """Testing __getitem__ with an expression with columns and carrays"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        c2 = t['f2']
        rt = t['f1*4 >= c2*2']
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i*4 >= i*2.*2),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test05(self):
        """Testing __getitem__ with an expression with overwritten vars"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        f1 = t['f2']
        f2 = t['f1']
        rt = t['f2*4 >= f1*2']
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i*4 >= i*2.*2),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

class eval_getitemDiskTest(eval_getitemTest):
    disk = True


class bool_getitemTest(MayBeDiskTest):

    def test00(self):
        """Testing __getitem__ with a boolean array (all false values)"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        barr = t.eval('f1 > f2')
        rt = t[barr]
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i > i*2.),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test01(self):
        """Testing __getitem__ with a boolean array (mixed values)"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        barr = t.eval('f1*4 >= f2*2')
        rt = t[barr]
        rar = np.fromiter(((i, i*2., i*3) for i in xrange(N) if i*4 >= i*2.*2),
                          dtype='i4,f8,i8')
        #print "rt->", rt
        #print "rar->", rar
        assert_array_equal(rt, rar, "ctable values are not correct")

    def test02(self):
        """Testing __getitem__ with a short boolean array"""
        N = 10
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        barr = np.zeros(len(t)-1, dtype=np.bool_)
        self.assertRaises(IndexError, t.__getitem__, barr)

class bool_getitemDiskTest(bool_getitemTest):
    disk = True


class whereTest(MayBeDiskTest):

    def test00a(self):
        """Testing where() with a boolean array (all false values)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        barr = t.eval('f1 > f2')
        rt = [r.f0 for r in t.where(barr)]
        rl = [i for i in xrange(N) if i > i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test00b(self):
        """Testing where() with a boolean array (all true values)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        barr = t.eval('f1 <= f2')
        rt = [r.f0 for r in t.where(barr)]
        rl = [i for i in xrange(N) if i <= i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test00c(self):
        """Testing where() with a boolean array (mix values)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        barr = t.eval('4+f1 > f2')
        rt = [r.f0 for r in t.where(barr)]
        rl = [i for i in xrange(N) if 4+i > i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test01a(self):
        """Testing where() with an expression (all false values)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r.f0 for r in t.where('f1 > f2')]
        rl = [i for i in xrange(N) if i > i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test01b(self):
        """Testing where() with an expression (all true values)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r.f0 for r in t.where('f1 <= f2')]
        rl = [i for i in xrange(N) if i <= i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test01c(self):
        """Testing where() with an expression (mix values)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r.f0 for r in t.where('4+f1 > f2')]
        rl = [i for i in xrange(N) if 4+i > i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test02a(self):
        """Testing where() with an expression (with outcols)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r.f1 for r in t.where('4+f1 > f2', outcols='f1')]
        rl = [i*2. for i in xrange(N) if 4+i > i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test02b(self):
        """Testing where() with an expression (with outcols II)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [(r.f1, r.f2) for r in t.where('4+f1 > f2', outcols=['f1','f2'])]
        rl = [(i*2., i*3) for i in xrange(N) if 4+i > i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test02c(self):
        """Testing where() with an expression (with outcols III)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [(f2, f0) for f0,f2 in t.where('4+f1 > f2', outcols='f0,f2')]
        rl = [(i*3, i) for i in xrange(N) if 4+i > i*2]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    # This does not work anymore because of the nesting of ctable._iter
    def _test02d(self):
        """Testing where() with an expression (with outcols IV)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        where = t.where('f1 > f2', outcols='f3,  f0')
        self.assertRaises(ValueError, where.next)

    def test03(self):
        """Testing where() with an expression (with nrow__ in outcols)"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r for r in t.where('4+f1 > f2', outcols=['nrow__','f2','f0'])]
        rl = [(i, i*3, i) for i in xrange(N) if 4+i > i*2]
        #print "rt->", rt, type(rt[0][0])
        #print "rl->", rl, type(rl[0][0])
        self.assert_(rt == rl, "where not working correctly")

    def test04(self):
        """Testing where() after an iter()"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        tmp = [r for r in t.iter(1,10,3)]
        rt = [tuple(r) for r in t.where('4+f1 > f2',
                                        outcols=['nrow__','f2','f0'])]
        rl = [(i, i*3, i) for i in xrange(N) if 4+i > i*2]
        #print "rt->", rt, type(rt[0][0])
        #print "rl->", rl, type(rl[0][0])
        self.assert_(rt == rl, "where not working correctly")

    def test05(self):
        """Testing where() with limit"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r for r in t.where('4+f1 > f2', outcols=['nrow__','f2','f0'],
                                 limit=3)]
        rl = [(i, i*3, i) for i in xrange(N) if 4+i > i*2][:3]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test06(self):
        """Testing where() with skip"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r for r in t.where('4+f1 > f2', outcols=['nrow__','f2','f0'],
                                 skip=3)]
        rl = [(i, i*3, i) for i in xrange(N) if 4+i > i*2][3:]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

    def test07(self):
        """Testing where() with limit & skip"""
        N = self.N
        ra = np.fromiter(((i, i*2., i*3) for i in xrange(N)), dtype='i4,f8,i8')
        t = ca.ctable(ra, rootdir=self.rootdir)
        rt = [r for r in t.where('4+f1 > f2', outcols=['nrow__','f2','f0'],
                                 limit=1, skip=2)]
        rl = [(i, i*3, i) for i in xrange(N) if 4+i > i*2][2:3]
        #print "rt->", rt
        #print "rl->", rl
        self.assert_(rt == rl, "where not working correctly")

class where_smallTest(whereTest):
    N = 10

class where_largeTest(whereTest):
    N = 10*1000

class where_smallDiskTest(whereTest):
    N = 10
    disk = True

class where_largeDiskTest(whereTest):
    N = 10*1000
    disk = True


# This test goes here until a new test_toplevel.py would be created
class walkTest(MayBeDiskTest):
    disk = True
    ncas = 3  # the number of carrays per level
    ncts = 4  # the number of ctables per level
    nlevels = 5 # the number of levels

    def setUp(self):
        import os, os.path
        N = 10

        MayBeDiskTest.setUp(self)
        base = self.rootdir
        os.mkdir(base)

        # Create a small object hierarchy on-disk
        for nlevel in range(self.nlevels):
            newdir = os.path.join(base, 'level%s' % nlevel) 
            os.mkdir(newdir)
            for nca in range(self.ncas):
                newca = os.path.join(newdir, 'ca%s' % nca) 
                ca.zeros(N, rootdir=newca)
            for nct in range(self.ncts):
                newca = os.path.join(newdir, 'ct%s' % nct) 
                ca.fromiter(((i, i*2) for i in range(N)), count=N,
                            dtype='i2,f4',
                            rootdir=newca)
            base = newdir

    def test00(self):
        """Checking the walk toplevel function (no classname)"""

        ncas_, ncts_, others = (0, 0, 0)
        for node in ca.walk(self.rootdir):
            if type(node) == ca.carray:
                ncas_ += 1
            elif type(node) == ca.ctable:
                ncts_ += 1
            else:
                others += 1

        self.assert_(ncas_ == self.ncas * self.nlevels)
        self.assert_(ncts_ == self.ncts * self.nlevels)
        self.assert_(others == 0)

    def test01(self):
        """Checking the walk toplevel function (classname='carray')"""

        ncas_, ncts_, others = (0, 0, 0)
        for node in ca.walk(self.rootdir, classname='carray'):
            if type(node) == ca.carray:
                ncas_ += 1
            elif type(node) == ca.ctable:
                ncts_ += 1
            else:
                others += 1

        self.assert_(ncas_ == self.ncas * self.nlevels)
        self.assert_(ncts_ == 0)
        self.assert_(others == 0)

    def test02(self):
        """Checking the walk toplevel function (classname='ctable')"""

        ncas_, ncts_, others = (0, 0, 0)
        for node in ca.walk(self.rootdir, classname='ctable'):
            if type(node) == ca.carray:
                ncas_ += 1
            elif type(node) == ca.ctable:
                ncts_ += 1
            else:
                others += 1

        self.assert_(ncas_ == 0)
        self.assert_(ncts_ == self.ncts * self.nlevels)
        self.assert_(others == 0)



def suite():
    theSuite = unittest.TestSuite()

    theSuite.addTest(unittest.makeSuite(createTest))
    theSuite.addTest(unittest.makeSuite(createDiskTest))
    theSuite.addTest(unittest.makeSuite(persistentTest))
    theSuite.addTest(unittest.makeSuite(add_del_colTest))
    theSuite.addTest(unittest.makeSuite(add_del_colDiskTest))
    theSuite.addTest(unittest.makeSuite(getitemTest))
    theSuite.addTest(unittest.makeSuite(getitemDiskTest))
    theSuite.addTest(unittest.makeSuite(setitemTest))
    theSuite.addTest(unittest.makeSuite(setitemDiskTest))
    theSuite.addTest(unittest.makeSuite(appendTest))
    theSuite.addTest(unittest.makeSuite(appendDiskTest))
    theSuite.addTest(unittest.makeSuite(trimTest))
    theSuite.addTest(unittest.makeSuite(trimDiskTest))
    theSuite.addTest(unittest.makeSuite(resizeTest))
    theSuite.addTest(unittest.makeSuite(resizeDiskTest))
    theSuite.addTest(unittest.makeSuite(copyTest))
    theSuite.addTest(unittest.makeSuite(copyDiskTest))
    theSuite.addTest(unittest.makeSuite(specialTest))
    theSuite.addTest(unittest.makeSuite(fancy_indexing_getitemTest))
    theSuite.addTest(unittest.makeSuite(fancy_indexing_setitemTest))
    theSuite.addTest(unittest.makeSuite(iterTest))
    theSuite.addTest(unittest.makeSuite(iterDiskTest))
    theSuite.addTest(unittest.makeSuite(evalTest))
    theSuite.addTest(unittest.makeSuite(evalDiskTest))
    if ca.numexpr_here:
        theSuite.addTest(unittest.makeSuite(eval_ne))
        theSuite.addTest(unittest.makeSuite(eval_neDisk))
    theSuite.addTest(unittest.makeSuite(eval_getitemTest))
    theSuite.addTest(unittest.makeSuite(eval_getitemDiskTest))
    theSuite.addTest(unittest.makeSuite(bool_getitemTest))
    theSuite.addTest(unittest.makeSuite(bool_getitemDiskTest))
    theSuite.addTest(unittest.makeSuite(where_smallTest))
    theSuite.addTest(unittest.makeSuite(where_smallDiskTest))
    theSuite.addTest(unittest.makeSuite(where_largeTest))
    theSuite.addTest(unittest.makeSuite(where_largeDiskTest))
    theSuite.addTest(unittest.makeSuite(walkTest))

    return theSuite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 72
## End:

########NEW FILE########
__FILENAME__ = test_ndcarray
# -*- coding: utf-8 -*-
########################################################################
#
#       License: BSD
#       Created: January 11, 2011
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import sys
import struct

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import carray as ca
from carray.carrayExtension import chunk
from carray.tests import common
from common import MayBeDiskTest
import unittest


class constructorTest(MayBeDiskTest):

    open = False

    def test00a(self):
        """Testing `carray` reshape"""
        a = np.arange(16).reshape((2,2,4))
        b = ca.arange(16, rootdir=self.rootdir).reshape((2,2,4))
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test00b(self):
        """Testing `carray` reshape (large shape)"""
        a = np.arange(16000).reshape((20,20,40))
        b = ca.arange(16000, rootdir=self.rootdir).reshape((20,20,40))
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test01a(self):
        """Testing `zeros` constructor (I)"""
        a = np.zeros((2,2,4), dtype='i4')
        b = ca.zeros((2,2,4), dtype='i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test01b(self):
        """Testing `zeros` constructor (II)"""
        a = np.zeros(2, dtype='(2,4)i4')
        b = ca.zeros(2, dtype='(2,4)i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test01c(self):
        """Testing `zeros` constructor (III)"""
        a = np.zeros((2,2), dtype='(4,)i4')
        b = ca.zeros((2,2), dtype='(4,)i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test02(self):
        """Testing `ones` constructor"""
        a = np.ones((2,2), dtype='(4,)i4')
        b = ca.ones((2,2), dtype='(4,)i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test03a(self):
        """Testing `fill` constructor (scalar default)"""
        a = np.ones((2,200), dtype='(4,)i4')*3
        b = ca.fill((2,200), 3, dtype='(4,)i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test03b(self):
        """Testing `fill` constructor (array default)"""
        a = np.ones((2,2), dtype='(4,)i4')*3
        b = ca.fill((2,2), [3,3,3,3], dtype='(4,)i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test04(self):
        """Testing `fill` constructor with open and resize (array default)"""
        a = np.ones((3,200), dtype='(4,)i4')*3
        b = ca.fill((2,200), [3,3,3,3], dtype='(4,)i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        c = np.ones((1,200), dtype='(4,)i4')*3
        b.append(c)
        #print "b->", `b`, len(b), b[1]
        assert_array_equal(a, b, "Arrays are not equal")

    def test05(self):
        """Testing `fill` constructor with open and resize (nchunks>1)"""
        a = np.ones((3,2000), dtype='(4,)i4')*3
        b = ca.fill((2,2000), [3,3,3,3], dtype='(4,)i4', rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        c = np.ones((1,2000), dtype='(4,)i4')*3
        b.append(c)
        #print "b->", `b`
        # We need to use the b[:] here to overcome a problem with the
        # assert_array_equal() function
        assert_array_equal(a, b[:], "Arrays are not equal")

class constructorDiskTest(constructorTest):
    disk = True
    open = False

class constructorOpenTest(constructorTest):
    disk = True
    open = True

class getitemTest(MayBeDiskTest):

    open = False

    def test00a(self):
        """Testing `__getitem()__` method with only a start (scalar)"""
        a = np.ones((2,3), dtype="i4")*3
        b = ca.fill((2,3), 3, dtype="i4", rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = 1
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test00b(self):
        """Testing `__getitem()__` method with only a start (slice)"""
        a = np.ones((27,2700), dtype="i4")*3
        b = ca.fill((27,2700), 3, dtype="i4", rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = slice(1)
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test01(self):
        """Testing `__getitem()__` method with a start and a stop"""
        a = np.ones((5,2), dtype="i4")*3
        b = ca.fill((5,2), 3, dtype="i4", rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = slice(1,4)
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02(self):
        """Testing `__getitem()__` method with a start, stop, step"""
        a = np.ones((10,2), dtype="i4")*3
        b = ca.fill((10,2), 3, dtype="i4", rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = slice(1,9,2)
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03a(self):
        """Testing `__getitem()__` method with several slices (I)"""
        a = np.arange(12).reshape((4,3))
        b = ca.carray(a, rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = (slice(1,3,1), slice(1,4,2))
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03b(self):
        """Testing `__getitem()__` method with several slices (II)"""
        a = np.arange(24*1000).reshape((4*1000,3,2))
        b = ca.carray(a, rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = (slice(1,3,2), slice(1,4,2), slice(None))
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03c(self):
        """Testing `__getitem()__` method with several slices (III)"""
        a = np.arange(120*1000).reshape((5*1000,4,3,2))
        b = ca.carray(a, rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = (slice(None,None,3), slice(1,3,2), slice(1,4,2))
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04a(self):
        """Testing `__getitem()__` method with shape reduction (I)"""
        a = np.arange(12000).reshape((40,300))
        b = ca.carray(a, rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = (1,1)
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04b(self):
        """Testing `__getitem()__` method with shape reduction (II)"""
        a = np.arange(12000).reshape((400,30))
        b = ca.carray(a, rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = (1,slice(1,4,2))
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04c(self):
        """Testing `__getitem()__` method with shape reduction (III)"""
        a = np.arange(6000).reshape((50,40,3))
        b = ca.carray(a, rootdir=self.rootdir)
        if self.open:
            b = ca.open(rootdir=self.rootdir)
        sl = (1,slice(1,4,2),2)
        #print "b[sl]->", `b[sl]`
        self.assert_(a[sl].shape == b[sl].shape, "Shape is not equal")
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

class getitemDiskTest(getitemTest):
    disk = True
    open = False

class getitemOpenTest(getitemTest):
    disk = True
    open = True


class setitemTest(MayBeDiskTest):

    open = False

    def test00a(self):
        """Testing `__setitem()__` method with only a start (scalar)"""
        a = np.ones((2,3), dtype="i4")*3
        b = ca.fill((2,3), 3, dtype="i4", rootdir=self.rootdir)
        sl = slice(1)
        a[sl,:] = 0
        b[sl] = 0
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test00b(self):
        """Testing `__setitem()__` method with only a start (vector)"""
        a = np.ones((200,300), dtype="i4")*3
        b = ca.fill((200,300), 3, dtype="i4", rootdir=self.rootdir)
        sl = slice(1)
        a[sl,:] = range(300)
        b[sl] = range(300)
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test01a(self):
        """Testing `__setitem()__` method with start,stop (scalar)"""
        a = np.ones((500,200), dtype="i4")*3
        b = ca.fill((500,200), 3, dtype="i4", rootdir=self.rootdir,
                    cparams=ca.cparams())
        sl = slice(100,400)
        a[sl,:] = 0
        b[sl] = 0
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")
        #assert_array_equal(a[:], b[:], "Arrays are not equal")

    def test01b(self):
        """Testing `__setitem()__` method with start,stop (vector)"""
        a = np.ones((5,2), dtype="i4")*3
        b = ca.fill((5,2), 3, dtype="i4", rootdir=self.rootdir)
        sl = slice(1,4)
        a[sl,:] = range(2)
        b[sl] = range(2)
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02a(self):
        """Testing `__setitem()__` method with start,stop,step (scalar)"""
        a = np.ones((1000,200), dtype="i4")*3
        b = ca.fill((1000,200), 3, dtype="i4", rootdir=self.rootdir)
        sl = slice(100,800,3)
        a[sl,:] = 0
        b[sl] = 0
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "b[sl]->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test02b(self):
        """Testing `__setitem()__` method with start,stop,step (scalar)"""
        a = np.ones((10,2), dtype="i4")*3
        b = ca.fill((10,2), 3, dtype="i4", rootdir=self.rootdir)
        sl = slice(1,8,3)
        a[sl,:] = range(2)
        b[sl] = range(2)
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "b[sl]->", `b[sl]`, `b`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test03a(self):
        """Testing `__setitem()__` method with several slices (I)"""
        a = np.arange(12000).reshape((400,30))
        b = ca.carray(a, rootdir=self.rootdir)
        sl = (slice(1,3,1), slice(1,None,2))
        #print "before->", `b[sl]`
        a[sl] = [[1],[2]]
        b[sl] = [[1],[2]]
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "after->", `b[sl]`
        assert_array_equal(a[:], b[:], "Arrays are not equal")

    def test03b(self):
        """Testing `__setitem()__` method with several slices (II)"""
        a = np.arange(24000).reshape((400,3,20))
        b = ca.carray(a, rootdir=self.rootdir)
        sl = (slice(1,3,1), slice(1,None,2), slice(1))
        #print "before->", `b[sl]`
        a[sl] = [[[1]],[[2]]]
        b[sl] = [[[1]],[[2]]]
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "after->", `b[sl]`
        assert_array_equal(a[:], b[:], "Arrays are not equal")

    def test03c(self):
        """Testing `__setitem()__` method with several slices (III)"""
        a = np.arange(120).reshape((5,4,3,2))
        b = ca.carray(a, rootdir=self.rootdir)
        sl = (slice(1,3), slice(1,3,1), slice(1,None,2), slice(1))
        #print "before->", `b[sl]`
        a[sl] = [[[[1]],[[2]]]]*2
        b[sl] = [[[[1]],[[2]]]]*2
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "after->", `b[sl]`
        assert_array_equal(a[:], b[:], "Arrays are not equal")

    def test03d(self):
        """Testing `__setitem()__` method with several slices (IV)"""
        a = np.arange(120).reshape((5,4,3,2))
        b = ca.carray(a, rootdir=self.rootdir)
        sl = (slice(1,3), slice(1,3,1), slice(1,None,2), slice(1))
        #print "before->", `b[sl]`
        a[sl] = 2
        b[sl] = 2
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "after->", `b[sl]`
        assert_array_equal(a[:], b[:], "Arrays are not equal")

    def test04a(self):
        """Testing `__setitem()__` method with shape reduction (I)"""
        a = np.arange(12).reshape((4,3))
        b = ca.carray(a, rootdir=self.rootdir)
        sl = (1,1)
        #print "before->", `b[sl]`
        a[sl] = 2
        b[sl] = 2
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "after->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04b(self):
        """Testing `__setitem()__` method with shape reduction (II)"""
        a = np.arange(12).reshape((4,3))
        b = ca.carray(a, rootdir=self.rootdir)
        sl = (1,slice(1,4,2))
        #print "before->", `b[sl]`
        a[sl] = 2
        b[sl] = 2
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "after->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

    def test04c(self):
        """Testing `__setitem()__` method with shape reduction (III)"""
        a = np.arange(24).reshape((4,3,2))
        b = ca.carray(a, rootdir=self.rootdir)
        sl = (1,2,slice(None,None,None))
        #print "before->", `b[sl]`
        a[sl] = 2
        b[sl] = 2
        if self.open:
            b.flush()
            b = ca.open(rootdir=self.rootdir)
        #print "after->", `b[sl]`
        assert_array_equal(a[sl], b[sl], "Arrays are not equal")

class setitemDiskTest(setitemTest):
    disk = True

class setitemOpenTest(setitemTest):
    disk = True
    open = True


class appendTest(MayBeDiskTest):

    def test00a(self):
        """Testing `append()` method (correct shape)"""
        a = np.ones((2,300), dtype="i4")*3
        b = ca.fill((1,300), 3, dtype="i4", rootdir=self.rootdir)
        b.append([(3,)*300])
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test00b(self):
        """Testing `append()` method (correct shape, single row)"""
        a = np.ones((2,300), dtype="i4")*3
        b = ca.fill((1,300), 3, dtype="i4", rootdir=self.rootdir)
        b.append((3,)*300)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test01(self):
        """Testing `append()` method (incorrect shape)"""
        a = np.ones((2,3), dtype="i4")*3
        b = ca.fill((1,3), 3, dtype="i4", rootdir=self.rootdir)
        self.assertRaises(ValueError, b.append, [(3,3)])

    def test02(self):
        """Testing `append()` method (several rows)"""
        a = np.ones((4,3), dtype="i4")*3
        b = ca.fill((1,3), 3, dtype="i4", rootdir=self.rootdir)
        b.append([(3,3,3)]*3)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

class appendDiskTest(appendTest):
    disk = True


class resizeTest(MayBeDiskTest):

    def test00a(self):
        """Testing `resize()` (trim)"""
        a = np.ones((2,3), dtype="i4")
        b = ca.ones((3,3), dtype="i4", rootdir=self.rootdir)
        b.resize(2)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test00b(self):
        """Testing `resize()` (trim to zero)"""
        a = np.ones((0,3), dtype="i4")
        b = ca.ones((3,3), dtype="i4", rootdir=self.rootdir)
        b.resize(0)
        #print "b->", `b`
        # The next does not work well for carrays with shape (0,)
        #assert_array_equal(a, b, "Arrays are not equal")
        self.assert_("a.dtype.base == b.dtype.base")
        self.assert_("a.shape == b.shape+b.dtype.shape")

    def test01(self):
        """Testing `resize()` (enlarge)"""
        a = np.ones((4,3), dtype="i4")
        b = ca.ones((3,3), dtype="i4", rootdir=self.rootdir)
        b.resize(4)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

class resizeDiskTest(resizeTest):
    disk = True


class iterTest(unittest.TestCase):

    def test00(self):
        """Testing `iter()` (no start, stop, step)"""
        a = np.ones((3,), dtype="i4")
        b = ca.ones((1000,3), dtype="i4")
        #print "b->", `b`
        for r in b.iter():
            assert_array_equal(a, r, "Arrays are not equal")

    def test01(self):
        """Testing `iter()` (w/ start, stop)"""
        a = np.ones((3,), dtype="i4")
        b = ca.ones((1000,3), dtype="i4")
        #print "b->", `b`
        for r in b.iter(start=10):
            assert_array_equal(a, r, "Arrays are not equal")

    def test02(self):
        """Testing `iter()` (w/ start, stop, step)"""
        a = np.ones((3,), dtype="i4")
        b = ca.ones((1000,3), dtype="i4")
        #print "b->", `b`
        for r in b.iter(15, 100, 3):
            assert_array_equal(a, r, "Arrays are not equal")


class reshapeTest(unittest.TestCase):

    def test00a(self):
        """Testing `reshape()` (unidim -> ndim)"""
        a = np.ones((3,4), dtype="i4")
        b = ca.ones(12, dtype="i4").reshape((3,4))
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test00b(self):
        """Testing `reshape()` (unidim -> ndim, -1 in newshape (I))"""
        a = np.ones((3,4), dtype="i4")
        b = ca.ones(12, dtype="i4").reshape((-1,4))
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test00c(self):
        """Testing `reshape()` (unidim -> ndim, -1 in newshape (II))"""
        a = np.ones((3,4), dtype="i4")
        b = ca.ones(12, dtype="i4").reshape((3,-1))
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test01(self):
        """Testing `reshape()` (ndim -> unidim)"""
        a = np.ones(12, dtype="i4")
        c = ca.ones(12, dtype="i4").reshape((3,4))
        b = c.reshape(12)
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test02a(self):
        """Testing `reshape()` (ndim -> ndim, I)"""
        a = np.arange(12, dtype="i4").reshape((3,4))
        c = ca.arange(12, dtype="i4").reshape((4,3))
        b = c.reshape((3,4))
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test02b(self):
        """Testing `reshape()` (ndim -> ndim, II)"""
        a = np.arange(24, dtype="i4").reshape((2,3,4))
        c = ca.arange(24, dtype="i4").reshape((4,3,2))
        b = c.reshape((2,3,4))
        #print "b->", `b`
        assert_array_equal(a, b, "Arrays are not equal")

    def test03(self):
        """Testing `reshape()` (0-dim)"""
        a = np.ones((0,4), dtype="i4")
        b = ca.ones(0, dtype="i4").reshape((0,4))
        #print "b->", `b`
        # The next does not work well for carrays with shape (0,)
        #assert_array_equal(a, b, "Arrays are not equal")
        self.assert_(a.dtype.base == b.dtype.base)
        self.assert_(a.shape == b.shape+b.dtype.shape)


class compoundTest(unittest.TestCase):

    def test00(self):
        """Testing compound types (creation)"""
        a = np.ones((300,4), dtype=self.dtype)
        b = ca.ones((300,4), dtype=self.dtype)
        #print "b.dtype-->", b.dtype
        #print "b->", `b`
        self.assert_(a.dtype == b.dtype.base)
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test01(self):
        """Testing compound types (append)"""
        a = np.ones((300,4), dtype=self.dtype)
        b = ca.carray([], dtype=self.dtype).reshape((0,4))
        b.append(a)
        #print "b.dtype-->", b.dtype
        #print "b->", `b`
        self.assert_(a.dtype == b.dtype.base)
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test02(self):
        """Testing compound types (iter)"""
        a = np.ones((3,), dtype=self.dtype)
        b = ca.ones((1000,3), dtype=self.dtype)
        #print "b->", `b`
        for r in b.iter():
            #print "r-->", r
            assert_array_equal(a, r, "Arrays are not equal")


class plainCompoundTest(compoundTest):
    dtype = np.dtype("i4,i8")

class nestedCompoundTest(compoundTest):
    dtype = np.dtype([('f1', [('f1', 'i2'), ('f2', 'i4')])])


class stringTest(unittest.TestCase):

    def test00(self):
        """Testing string types (creation)"""
        a = np.array([["ale", "ene"], ["aco", "ieie"]], dtype="S4")
        b = ca.carray(a)
        #print "b.dtype-->", b.dtype
        #print "b->", `b`
        self.assert_(a.dtype == b.dtype.base)
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test01(self):
        """Testing string types (append)"""
        a = np.ones((300,4), dtype="S4")
        b = ca.carray([], dtype="S4").reshape((0,4))
        b.append(a)
        #print "b.dtype-->", b.dtype
        #print "b->", `b`
        self.assert_(a.dtype == b.dtype.base)
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test02(self):
        """Testing string types (iter)"""
        a = np.ones((3,), dtype="S40")
        b = ca.ones((1000,3), dtype="S40")
        #print "b->", `b`
        for r in b.iter():
            #print "r-->", r
            assert_array_equal(a, r, "Arrays are not equal")


class unicodeTest(unittest.TestCase):

    def test00(self):
        """Testing unicode types (creation)"""
        a = np.array([[u"aŀle", u"eñe"], [u"açò", u"áèâë"]], dtype="U4")
        b = ca.carray(a)
        #print "b.dtype-->", b.dtype
        #print "b->", `b`
        self.assert_(a.dtype == b.dtype.base)
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test01(self):
        """Testing unicode types (append)"""
        a = np.ones((300,4), dtype="U4")
        b = ca.carray([], dtype="U4").reshape((0,4))
        b.append(a)
        #print "b.dtype-->", b.dtype
        #print "b->", `b`
        self.assert_(a.dtype == b.dtype.base)
        assert_array_equal(a, b[:], "Arrays are not equal")

    def test02(self):
        """Testing unicode types (iter)"""
        a = np.ones((3,), dtype="U40")
        b = ca.ones((1000,3), dtype="U40")
        #print "b->", `b`
        for r in b.iter():
            #print "r-->", r
            assert_array_equal(a, r, "Arrays are not equal")


class evalTest(unittest.TestCase):

    vm = "python"

    def setUp(self):
        self.prev_vm = ca.defaults.eval_vm
        ca.defaults.eval_vm = self.vm

    def tearDown(self):
        ca.defaults.eval_vm = self.prev_vm

    def test00a(self):
        """Testing evaluation of ndcarrays (bool out)"""
        a = np.arange(np.prod(self.shape)).reshape(self.shape)
        b = ca.arange(np.prod(self.shape)).reshape(self.shape)
        outa = eval("a>0")
        outb = ca.eval("b>0")
        assert_array_equal(outa, outb, "Arrays are not equal")

    def test00b(self):
        """Testing evaluation of ndcarrays (bool out, NumPy)"""
        a = np.arange(np.prod(self.shape)).reshape(self.shape)
        b = ca.arange(np.prod(self.shape)).reshape(self.shape)
        outa = eval("a>0")
        outb = ca.eval("b>0", out_flavor='numpy')
        assert_array_equal(outa, outb, "Arrays are not equal")

    def test01(self):
        """Testing evaluation of ndcarrays (int out)"""
        a = np.arange(np.prod(self.shape)).reshape(self.shape)
        b = ca.arange(np.prod(self.shape)).reshape(self.shape)
        outa = eval("a*2.+1")
        outb = ca.eval("b*2.+1")
        assert_array_equal(outa, outb, "Arrays are not equal")

    def test02(self):
        """Testing evaluation of ndcarrays (reduction, no axis)"""
        a = np.arange(np.prod(self.shape)).reshape(self.shape)
        b = ca.arange(np.prod(self.shape)).reshape(self.shape)
        if ca.defaults.eval_vm == "python":
            assert_array_equal(sum(a), ca.eval("sum(b)"),
                               "Arrays are not equal")
        else:
            self.assertEqual(a.sum(), ca.eval("sum(b)"))

    def test02b(self):
        """Testing evaluation of ndcarrays (reduction, with axis)"""
        a = np.arange(np.prod(self.shape)).reshape(self.shape)
        b = ca.arange(np.prod(self.shape)).reshape(self.shape)
        if ca.defaults.eval_vm == "python":
            # The Python VM does not have support for `axis` param
            assert_array_equal(sum(a), ca.eval("sum(b)"),
                               "Arrays are not equal")
        else:
            assert_array_equal(a.sum(axis=1), ca.eval("sum(b, axis=1)"),
                               "Arrays are not equal")

class d2eval_python(evalTest):
    shape = (3,4)

class d2eval_ne(evalTest):
    shape = (3,4)
    vm = "numexpr"

class d3eval_python(evalTest):
    shape = (3,4,5)

class d3eval_ne(evalTest):
    shape = (3,4,5)
    vm = "numexpr"

class d4eval_python(evalTest):
    shape = (3,40,50,2)

class d4eval_ne(evalTest):
    shape = (3,40,50,2)
    vm = "numexpr"


class computeMethodsTest(unittest.TestCase):

    def test00(self):
        """Testing sum()."""
        a = np.arange(1e5).reshape(10, 1e4)
        sa = a.sum()
        ac = ca.carray(a)
        sac = ac.sum()
        #print "numpy sum-->", sa
        #print "carray sum-->", sac
        self.assert_(sa.dtype == sac.dtype, "sum() is not working correctly.")
        self.assert_(sa == sac, "sum() is not working correctly.")



def suite():
    theSuite = unittest.TestSuite()

    theSuite.addTest(unittest.makeSuite(constructorTest))
    theSuite.addTest(unittest.makeSuite(constructorDiskTest))
    theSuite.addTest(unittest.makeSuite(constructorOpenTest))
    theSuite.addTest(unittest.makeSuite(getitemTest))
    theSuite.addTest(unittest.makeSuite(getitemDiskTest))
    theSuite.addTest(unittest.makeSuite(getitemOpenTest))
    theSuite.addTest(unittest.makeSuite(setitemTest))
    theSuite.addTest(unittest.makeSuite(setitemDiskTest))
    theSuite.addTest(unittest.makeSuite(setitemOpenTest))
    theSuite.addTest(unittest.makeSuite(appendTest))
    theSuite.addTest(unittest.makeSuite(appendDiskTest))
    theSuite.addTest(unittest.makeSuite(resizeTest))
    theSuite.addTest(unittest.makeSuite(resizeDiskTest))
    theSuite.addTest(unittest.makeSuite(iterTest))
    theSuite.addTest(unittest.makeSuite(reshapeTest))
    theSuite.addTest(unittest.makeSuite(plainCompoundTest))
    theSuite.addTest(unittest.makeSuite(nestedCompoundTest))
    theSuite.addTest(unittest.makeSuite(stringTest))
    theSuite.addTest(unittest.makeSuite(unicodeTest))
    theSuite.addTest(unittest.makeSuite(d2eval_python))
    theSuite.addTest(unittest.makeSuite(d3eval_python))
    theSuite.addTest(unittest.makeSuite(d4eval_python))
    theSuite.addTest(unittest.makeSuite(computeMethodsTest))
    if ca.numexpr_here:
        theSuite.addTest(unittest.makeSuite(d2eval_ne))
        theSuite.addTest(unittest.makeSuite(d3eval_ne))
        theSuite.addTest(unittest.makeSuite(d4eval_ne))


    return theSuite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 72
## End:

########NEW FILE########
__FILENAME__ = test_queries
########################################################################
#
#       License: BSD
#       Created: January 18, 2011
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import sys

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
import carray as ca
from carray.tests import common
import unittest


class with_listTest(unittest.TestCase):

    def test00a(self):
        """Testing wheretrue() in combination with a list constructor"""
        a = ca.zeros(self.N, dtype="bool")
        a[30:40] = ca.ones(10, dtype="bool")
        alist = list(a)
        blist1 = [r for r in a.wheretrue()]
        self.assert_(blist1 == range(30,40))
        alist2 = list(a)
        self.assert_(alist == alist2, "wheretrue() not working correctly")

    def test00b(self):
        """Testing wheretrue() with a multidimensional array"""
        a = ca.zeros((self.N, 10), dtype="bool")
        a[30:40] = ca.ones(10, dtype="bool")
        self.assertRaises(NotImplementedError, a.wheretrue)

    def test01a(self):
        """Testing where() in combination with a list constructor"""
        a = ca.zeros(self.N, dtype="bool")
        a[30:40] = ca.ones(10, dtype="bool")
        b = ca.arange(self.N, dtype="f4")
        blist = list(b)
        blist1 = [r for r in b.where(a)]
        self.assert_(blist1 == range(30,40))
        blist2 = list(b)
        self.assert_(blist == blist2, "where() not working correctly")

    def test01b(self):
        """Testing where() with a multidimensional array"""
        a = ca.zeros((self.N, 10), dtype="bool")
        a[30:40] = ca.ones(10, dtype="bool")
        b = ca.arange(self.N*10, dtype="f4").reshape((self.N, 10))
        self.assertRaises(NotImplementedError, b.where, a)

    def test02(self):
        """Testing iter() in combination with a list constructor"""
        b = ca.arange(self.N, dtype="f4")
        blist = list(b)
        blist1 = [r for r in b.iter(3,10)]
        self.assert_(blist1 == range(3,10))
        blist2 = list(b)
        self.assert_(blist == blist2, "iter() not working correctly")


class small_with_listTest(with_listTest):
    N = 100

class big_with_listTest(with_listTest):
    N = 10000


def suite():
    theSuite = unittest.TestSuite()

    theSuite.addTest(unittest.makeSuite(small_with_listTest))
    theSuite.addTest(unittest.makeSuite(big_with_listTest))

    return theSuite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 72
## End:

########NEW FILE########
__FILENAME__ = toplevel
########################################################################
#
#       License: BSD
#       Created: September 10, 2010
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

"""Top level functions and classes.
"""

import sys
import os, os.path
import glob
import itertools as it
import numpy as np
import carray as ca
import math

if ca.numexpr_here:
    from numexpr.expressions import functions as numexpr_functions


def detect_number_of_cores():
    """
    detect_number_of_cores()

    Return the number of cores in this system.

    """
    # Linux, Unix and MacOS:
    if hasattr(os, "sysconf"):
        if os.sysconf_names.has_key("SC_NPROCESSORS_ONLN"):
            # Linux & Unix:
            ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
            if isinstance(ncpus, int) and ncpus > 0:
                return ncpus
        else: # OSX:
            return int(os.popen2("sysctl -n hw.ncpu")[1].read())
    # Windows:
    if os.environ.has_key("NUMBER_OF_PROCESSORS"):
        ncpus = int(os.environ["NUMBER_OF_PROCESSORS"]);
        if ncpus > 0:
            return ncpus
    return 1 # Default

def set_nthreads(nthreads):
    """
    set_nthreads(nthreads)

    Sets the number of threads to be used during carray operation.

    This affects to both Blosc and Numexpr (if available).  If you want to
    change this number only for Blosc, use `blosc_set_nthreads` instead.

    Parameters
    ----------
    nthreads : int
        The number of threads to be used during carray operation.

    Returns
    -------
    out : int
        The previous setting for the number of threads.

    See Also
    --------
    blosc_set_nthreads

    """
    nthreads_old = ca.blosc_set_nthreads(nthreads)
    if ca.numexpr_here:
        ca.numexpr.set_num_threads(nthreads)
    return nthreads_old

def open(rootdir, mode='a'):
    """
    open(rootdir, mode='a')

    Open a disk-based carray/ctable.

    Parameters
    ----------
    rootdir : pathname (string)
        The directory hosting the carray/ctable object.
    mode : the open mode (string)
        Specifies the mode in which the object is opened.  The supported
        values are:

          * 'r' for read-only
          * 'w' for emptying the previous underlying data
          * 'a' for allowing read/write on top of existing data

    Returns
    -------
    out : a carray/ctable object or None (if not objects are found)

    """
    # First try with a carray
    obj = None
    try:
        obj = ca.carray(rootdir=rootdir, mode=mode)
    except IOError:
        # Not a carray.  Now with a ctable
        try:
            obj = ca.ctable(rootdir=rootdir, mode=mode)
        except IOError:
            # Not a ctable
            pass
    return obj

def fromiter(iterable, dtype, count, **kwargs):
    """
    fromiter(iterable, dtype, count, **kwargs)

    Create a carray/ctable from an `iterable` object.

    Parameters
    ----------
    iterable : iterable object
        An iterable object providing data for the carray.
    dtype : numpy.dtype instance
        Specifies the type of the outcome object.
    count : int
        The number of items to read from iterable. If set to -1, means that
        the iterable will be used until exhaustion (not recommended, see note
        below).
    kwargs : list of parameters or dictionary
        Any parameter supported by the carray/ctable constructors.

    Returns
    -------
    out : a carray/ctable object

    Notes
    -----
    Please specify `count` to both improve performance and to save memory.  It
    allows `fromiter` to avoid looping the iterable twice (which is slooow).
    It avoids memory leaks to happen too (which can be important for large
    iterables).

    """

    # Check for a true iterable
    if not hasattr(iterable, "next"):
        iterable = iter(iterable)

    # Try to guess the final length
    expected = count
    if count == -1:
        # Try to guess the size of the iterable length
        if hasattr(iterable, "__length_hint__"):
            count = iterable.__length_hint__()
            expected = count
        else:
            # No guess
            count = sys.maxint
            # If we do not have a hint on the iterable length then
            # create a couple of iterables and use the second when the
            # first one is exhausted (ValueError will be raised).
            iterable, iterable2 = it.tee(iterable)
            expected = 1000*1000   # 1 million elements

    # First, create the container
    expectedlen = kwargs.pop("expectedlen", expected)
    dtype = np.dtype(dtype)
    if dtype.kind == "V":
        # A ctable
        obj = ca.ctable(np.array([], dtype=dtype),
                        expectedlen=expectedlen,
                        **kwargs)
        chunklen = sum(obj.cols[name].chunklen
                       for name in obj.names) // len(obj.names)
    else:
        # A carray
        obj = ca.carray(np.array([], dtype=dtype),
                        expectedlen=expectedlen,
                        **kwargs)
        chunklen = obj.chunklen

    # Then fill it
    nread, blen = 0, 0
    while nread < count:
        if nread + chunklen > count:
            blen = count - nread
        else:
            blen = chunklen
        if count != sys.maxint:
            chunk = np.fromiter(iterable, dtype=dtype, count=blen)
        else:
            try:
                chunk = np.fromiter(iterable, dtype=dtype, count=blen)
            except ValueError:
                # Positionate in second iterable
                iter2 = it.islice(iterable2, nread, None, 1)
                # We are reaching the end, use second iterable now
                chunk = np.fromiter(iter2, dtype=dtype, count=-1)
        obj.append(chunk)
        nread += len(chunk)
        # Check the end of the iterable
        if len(chunk) < chunklen:
            break
    obj.flush()
    return obj

def fill(shape, dflt=None, dtype=np.float, **kwargs):
    """
    fill(shape, dtype=float, dflt=None, **kwargs)

    Return a new carray object of given shape and type, filled with `dflt`.

    Parameters
    ----------
    shape : int
        Shape of the new array, e.g., ``(2,3)``.
    dflt : Python or NumPy scalar
        The value to be used during the filling process.  If None, values are
        filled with zeros.  Also, the resulting carray will have this value as
        its `dflt` value.
    dtype : data-type, optional
        The desired data-type for the array, e.g., `numpy.int8`.  Default is
        `numpy.float64`.
    kwargs : list of parameters or dictionary
        Any parameter supported by the carray constructor.

    Returns
    -------
    out : carray
        Array filled with `dflt` values with the given shape and dtype.

    See Also
    --------
    ones, zeros

    """

    dtype = np.dtype(dtype)
    if type(shape) in (int, long, float):
        shape = (int(shape),)
    else:
        shape = tuple(shape)
        if len(shape) > 1:
            # Multidimensional shape.
            # The atom will have shape[1:] dims (+ the dtype dims).
            dtype = np.dtype((dtype.base, shape[1:]+dtype.shape))
    length = shape[0]

    # Create the container
    expectedlen = kwargs.pop("expectedlen", length)
    if dtype.kind == "V" and dtype.shape == ():
        raise ValueError, "fill does not support ctables objects"
    obj = ca.carray([], dtype=dtype, dflt=dflt, expectedlen=expectedlen,
                    **kwargs)
    chunklen = obj.chunklen

    # Then fill it
    # We need an array for the defaults so as to keep the atom info
    dflt = np.array(obj.dflt, dtype=dtype)
    # Making strides=(0,) below is a trick to create the array fast and
    # without memory consumption
    chunk = np.ndarray(length, dtype=dtype, buffer=dflt, strides=(0,))
    obj.append(chunk)
    obj.flush()
    return obj

def zeros(shape, dtype=np.float, **kwargs):
    """
    zeros(shape, dtype=float, **kwargs)

    Return a new carray object of given shape and type, filled with zeros.

    Parameters
    ----------
    shape : int
        Shape of the new array, e.g., ``(2,3)``.
    dtype : data-type, optional
        The desired data-type for the array, e.g., `numpy.int8`.  Default is
        `numpy.float64`.
    kwargs : list of parameters or dictionary
        Any parameter supported by the carray constructor.

    Returns
    -------
    out : carray
        Array of zeros with the given shape and dtype.

    See Also
    --------
    fill, ones

    """
    dtype = np.dtype(dtype)
    return fill(shape=shape, dflt=np.zeros((), dtype), dtype=dtype, **kwargs)

def ones(shape, dtype=np.float, **kwargs):
    """
    ones(shape, dtype=float, **kwargs)

    Return a new carray object of given shape and type, filled with ones.

    Parameters
    ----------
    shape : int
        Shape of the new array, e.g., ``(2,3)``.
    dtype : data-type, optional
        The desired data-type for the array, e.g., `numpy.int8`.  Default is
        `numpy.float64`.
    kwargs : list of parameters or dictionary
        Any parameter supported by the carray constructor.

    Returns
    -------
    out : carray
        Array of ones with the given shape and dtype.

    See Also
    --------
    fill, zeros

    """
    dtype = np.dtype(dtype)
    return fill(shape=shape, dflt=np.ones((), dtype), dtype=dtype, **kwargs)

def arange(start=None, stop=None, step=None, dtype=None, **kwargs):
    """
    arange([start,] stop[, step,], dtype=None, **kwargs)

    Return evenly spaced values within a given interval.

    Values are generated within the half-open interval ``[start, stop)``
    (in other words, the interval including `start` but excluding `stop`).
    For integer arguments the function is equivalent to the Python built-in
    `range <http://docs.python.org/lib/built-in-funcs.html>`_ function,
    but returns a carray rather than a list.

    Parameters
    ----------
    start : number, optional
        Start of interval.  The interval includes this value.  The default
        start value is 0.
    stop : number
        End of interval.  The interval does not include this value.
    step : number, optional
        Spacing between values.  For any output `out`, this is the distance
        between two adjacent values, ``out[i+1] - out[i]``.  The default
        step size is 1.  If `step` is specified, `start` must also be given.
    dtype : dtype
        The type of the output array.  If `dtype` is not given, infer the data
        type from the other input arguments.
    kwargs : list of parameters or dictionary
        Any parameter supported by the carray constructor.

    Returns
    -------
    out : carray
        Array of evenly spaced values.

        For floating point arguments, the length of the result is
        ``ceil((stop - start)/step)``.  Because of floating point overflow,
        this rule may result in the last element of `out` being greater
        than `stop`.

    """

    # Check start, stop, step values
    if (start, stop) == (None, None):
        raise ValueError, "You must pass a `stop` value at least."
    elif stop is None:
        start, stop = 0, start
    elif start is None:
        start, stop = 0, stop
    if step is None:
        step = 1

    # Guess the dtype
    if dtype is None:
        if type(stop) in (int, long):
            dtype = np.dtype(np.int_)
    dtype = np.dtype(dtype)
    stop = int(stop)

    # Create the container
    expectedlen = kwargs.pop("expectedlen", stop)
    if dtype.kind == "V":
        raise ValueError, "arange does not support ctables yet."
    else:
        obj = ca.carray(np.array([], dtype=dtype),
                        expectedlen=expectedlen,
                        **kwargs)
        chunklen = obj.chunklen

    # Then fill it
    incr = chunklen * step        # the increment for each chunk
    incr += step - (incr % step)  # make it match step boundary
    bstart, bstop = start, start + incr
    while bstart < stop:
        if bstop > stop:
            bstop = stop
        chunk = np.arange(bstart, bstop, step, dtype=dtype)
        obj.append(chunk)
        bstart = bstop
        bstop += incr
    obj.flush()
    return obj

def _getvars(expression, user_dict, depth, vm):
    """Get the variables in `expression`.

    `depth` specifies the depth of the frame in order to reach local
    or global variables.
    """

    cexpr = compile(expression, '<string>', 'eval')
    if vm == "python":
        exprvars = [ var for var in cexpr.co_names
                     if var not in ['None', 'False', 'True'] ]
    else:
        # Check that var is not a numexpr function here.  This is useful for
        # detecting unbound variables in expressions.  This is not necessary
        # for the 'python' engine.
        exprvars = [ var for var in cexpr.co_names
                     if var not in ['None', 'False', 'True']
                     and var not in numexpr_functions ]


    # Get the local and global variable mappings of the user frame
    user_locals, user_globals = {}, {}
    user_frame = sys._getframe(depth)
    user_locals = user_frame.f_locals
    user_globals = user_frame.f_globals

    # Look for the required variables
    reqvars = {}
    for var in exprvars:
        # Get the value.
        if var in user_dict:
            val = user_dict[var]
        elif var in user_locals:
            val = user_locals[var]
        elif var in user_globals:
            val = user_globals[var]
        else:
            if vm == "numexpr":
                raise NameError("variable name ``%s`` not found" % var)
            val = None
        # Check the value.
        if (vm == "numexpr" and
            hasattr(val, 'dtype') and hasattr(val, "__len__") and
            val.dtype.str[1:] == 'u8'):
            raise NotImplementedError(
                "variable ``%s`` refers to "
                "a 64-bit unsigned integer object, that is "
                "not yet supported in numexpr expressions; "
                "rather, use the 'python' vm." % var )
        if val is not None:
            reqvars[var] = val
    return reqvars


# Assign function `eval` to a variable because we are overriding it
_eval = eval

def eval(expression, vm=None, out_flavor=None, user_dict={}, **kwargs):
    """
    eval(expression, vm=None, out_flavor=None, user_dict=None, **kwargs)

    Evaluate an `expression` and return the result.

    Parameters
    ----------
    expression : string
        A string forming an expression, like '2*a+3*b'. The values for 'a' and
        'b' are variable names to be taken from the calling function's frame.
        These variables may be scalars, carrays or NumPy arrays.
    vm : string
        The virtual machine to be used in computations.  It can be 'numexpr'
        or 'python'.  The default is to use 'numexpr' if it is installed.
    out_flavor : string
        The flavor for the `out` object.  It can be 'carray' or 'numpy'.
    user_dict : dict
        An user-provided dictionary where the variables in expression
        can be found by name.    
    kwargs : list of parameters or dictionary
        Any parameter supported by the carray constructor.

    Returns
    -------
    out : carray object
        The outcome of the expression.  You can tailor the
        properties of this carray by passing additional arguments
        supported by carray constructor in `kwargs`.

    """

    if vm is None:
        vm = ca.defaults.eval_vm
    if vm not in ("numexpr", "python"):
        raiseValue, "`vm` must be either 'numexpr' or 'python'"

    if out_flavor is None:
        out_flavor = ca.defaults.eval_out_flavor
    if out_flavor not in ("carray", "numpy"):
        raiseValue, "`out_flavor` must be either 'carray' or 'numpy'"

    # Get variables and column names participating in expression
    depth = kwargs.pop('depth', 2)
    vars = _getvars(expression, user_dict, depth, vm=vm)

    # Gather info about sizes and lengths
    typesize, vlen = 0, 1
    for name in vars.iterkeys():
        var = vars[name]
        if hasattr(var, "__len__") and not hasattr(var, "dtype"):
            raise ValueError, "only numpy/carray sequences supported"
        if hasattr(var, "dtype") and not hasattr(var, "__len__"):
            continue
        if hasattr(var, "dtype"):  # numpy/carray arrays
            if isinstance(var, np.ndarray):  # numpy array
                typesize += var.dtype.itemsize * np.prod(var.shape[1:])
            elif isinstance(var, ca.carray):  # carray array
                typesize += var.dtype.itemsize
            else:
                raise ValueError, "only numpy/carray objects supported"
        if hasattr(var, "__len__"):
            if vlen > 1 and vlen != len(var):
                raise ValueError, "arrays must have the same length"
            vlen = len(var)

    if typesize == 0:
        # All scalars
        if vm == "python":
            return _eval(expression, vars)
        else:
            return ca.numexpr.evaluate(expression, local_dict=vars)

    return _eval_blocks(expression, vars, vlen, typesize, vm, out_flavor,
                        **kwargs)

def _eval_blocks(expression, vars, vlen, typesize, vm, out_flavor,
                 **kwargs):
    """Perform the evaluation in blocks."""

    # Compute the optimal block size (in elements)
    # The next is based on experiments with bench/ctable-query.py
    if vm == "numexpr":
        # If numexpr, make sure that operands fits in L3 chache
        bsize = 2**20  # 1 MB is common for L3
    else:
        # If python, make sure that operands fits in L2 chache
        bsize = 2**17  # 256 KB is common for L2
    bsize //= typesize
    # Evaluation seems more efficient if block size is a power of 2
    bsize = 2 ** (int(math.log(bsize, 2)))
    if vlen < 100*1000:
        bsize //= 8
    elif vlen < 1000*1000:
        bsize //= 4
    elif vlen < 10*1000*1000:
        bsize //= 2
    # Protection against too large atomsizes
    if bsize == 0:
        bsize = 1

    vars_ = {}
    # Get temporaries for vars
    maxndims = 0
    for name in vars.iterkeys():
        var = vars[name]
        if hasattr(var, "__len__"):
            ndims = len(var.shape) + len(var.dtype.shape)
            if ndims > maxndims:
                maxndims = ndims
            if len(var) > bsize and hasattr(var, "_getrange"):
                vars_[name] = np.empty(bsize, dtype=var.dtype)

    for i in xrange(0, vlen, bsize):
        # Get buffers for vars
        for name in vars.iterkeys():
            var = vars[name]
            if hasattr(var, "__len__") and len(var) > bsize:
                if hasattr(var, "_getrange"):
                    if i+bsize < vlen:
                        var._getrange(i, bsize, vars_[name])
                    else:
                        vars_[name] = var[i:]
                else:
                    vars_[name] = var[i:i+bsize]
            else:
                if hasattr(var, "__getitem__"):
                    vars_[name] = var[:]
                else:
                    vars_[name] = var

        # Perform the evaluation for this block
        if vm == "python":
            res_block = _eval(expression, vars_)
        else:
            res_block = ca.numexpr.evaluate(expression, local_dict=vars_)

        if i == 0:
            # Detection of reduction operations
            scalar = False
            dim_reduction = False
            if len(res_block.shape) == 0:
                scalar = True
                result = res_block
                continue
            elif len(res_block.shape) < maxndims:
                dim_reduction = True
                result = res_block
                continue
            # Get a decent default for expectedlen
            if out_flavor == "carray":
                nrows = kwargs.pop('expectedlen', vlen)
                result = ca.carray(res_block, expectedlen=nrows, **kwargs)
            else:
                out_shape = list(res_block.shape)
                out_shape[0] = vlen
                result = np.empty(out_shape, dtype=res_block.dtype)
                result[:bsize] = res_block
        else:
            if scalar or dim_reduction:
                result += res_block
            elif out_flavor == "carray":
                result.append(res_block)
            else:
                result[i:i+bsize] = res_block

    if isinstance(result, ca.carray):
        result.flush()
    if scalar:
        return result[()]
    return result


def walk(dir, classname=None, mode='a'):
    """walk(dir, classname=None, mode='a')

    Recursively iterate over carray/ctable objects hanging from `dir`.

    Parameters
    ----------
    dir : string
        The directory from which the listing starts.
    classname : string
        If specified, only object of this class are returned.  The values
        supported are 'carray' and 'ctable'.
    mode : string
        The mode in which the object should be opened.

    Returns
    -------
    out : iterator
        Iterator over the objects found.

    """

    # First, iterate over the carray objects in current dir
    names = os.path.join(dir, '*')
    dirs = []
    for node in glob.glob(names):
        if os.path.isdir(node):
            try:
                obj = ca.carray(rootdir=node, mode=mode)
            except:
                try:
                    obj = ca.ctable(rootdir=node, mode=mode)
                except:
                    obj = None
                    dirs.append(node)
            if obj:
                if classname:
                    if obj.__class__.__name__ == classname:
                        yield obj
                else:
                    yield obj

    # Then recurse into the true directories
    for dir_ in dirs:
        for node in walk(dir_, classname, mode):
            yield node


class cparams(object):
    """
    cparams(clevel=5, shuffle=True)

    Class to host parameters for compression and other filters.

    Parameters
    ----------
    clevel : int (0 <= clevel < 10)
        The compression level.
    shuffle : bool
        Whether the shuffle filter is active or not.

    Notes
    -----
    The shuffle filter may be automatically disable in case it is
    non-sense to use it (e.g. itemsize == 1).

    """

    @property
    def clevel(self):
        """The compression level."""
        return self._clevel

    @property
    def shuffle(self):
        """Shuffle filter is active?"""
        return self._shuffle

    def __init__(self, clevel=5, shuffle=True):
        if not isinstance(clevel, int):
            raise ValueError, "`clevel` must an int."
        if not isinstance(shuffle, (bool, int)):
            raise ValueError, "`shuffle` must a boolean."
        shuffle = bool(shuffle)
        if clevel < 0:
            raiseValueError, "clevel must be a positive integer"
        self._clevel = clevel
        self._shuffle = shuffle

    def __repr__(self):
        args = ["clevel=%d"%self._clevel, "shuffle=%s"%self._shuffle]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(args))




## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 78
## End:

########NEW FILE########
__FILENAME__ = utils
########################################################################
#
#       License: BSD
#       Created: August 5, 2010
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

"""Utility functions (mostly private).
"""

import sys, os, os.path, subprocess, math
from time import time, clock
import numpy as np
import carray as ca


def show_stats(explain, tref):
    "Show the used memory (only works for Linux 2.6.x)."
    # Build the command to obtain memory info
    cmd = "cat /proc/%s/status" % os.getpid()
    sout = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout
    for line in sout:
        if line.startswith("VmSize:"):
            vmsize = int(line.split()[1])
        elif line.startswith("VmRSS:"):
            vmrss = int(line.split()[1])
        elif line.startswith("VmData:"):
            vmdata = int(line.split()[1])
        elif line.startswith("VmStk:"):
            vmstk = int(line.split()[1])
        elif line.startswith("VmExe:"):
            vmexe = int(line.split()[1])
        elif line.startswith("VmLib:"):
            vmlib = int(line.split()[1])
    sout.close()
    print "Memory usage: ******* %s *******" % explain
    print "VmSize: %7s kB\tVmRSS: %7s kB" % (vmsize, vmrss)
    print "VmData: %7s kB\tVmStk: %7s kB" % (vmdata, vmstk)
    print "VmExe:  %7s kB\tVmLib: %7s kB" % (vmexe, vmlib)
    tnow = time()
    print "WallClock time:", round(tnow - tref, 3)
    return tnow


##### Code for computing optimum chunksize follows  #####

def csformula(expectedsizeinMB):
    """Return the fitted chunksize for expectedsizeinMB."""
    # For a basesize of 1 KB, this will return:
    # 4 KB for datasets <= .1 KB
    # 64 KB for datasets == 1 MB
    # 1 MB for datasets >= 10 GB
    basesize = 1024
    return basesize * int(2**(math.log10(expectedsizeinMB)+6))

def limit_es(expectedsizeinMB):
    """Protection against creating too small or too large chunks."""
    if expectedsizeinMB < 1e-4:     # < .1 KB
        expectedsizeinMB = 1e-4
    elif expectedsizeinMB > 1e4:    # > 10 GB
        expectedsizeinMB = 1e4
    return expectedsizeinMB

def calc_chunksize(expectedsizeinMB):
    """Compute the optimum chunksize for memory I/O in carray/ctable.

    carray stores the data in chunks and there is an optimal length for
    this chunk for compression purposes (it is around 1 MB for modern
    processors).  However, due to the implementation, carray logic needs
    to always reserve all this space in-memory.  Booking 1 MB is not a
    drawback for large carrays (>> 1 MB), but for smaller ones this is
    too much overhead.

    The tuning of the chunksize parameter affects the performance and
    the memory consumed.  This is based on my own experiments and, as
    always, your mileage may vary.
    """

    expectedsizeinMB = limit_es(expectedsizeinMB)
    zone = int(math.log10(expectedsizeinMB))
    expectedsizeinMB = 10**zone
    chunksize = csformula(expectedsizeinMB)
    return chunksize

def get_len_of_range(start, stop, step):
    """Get the length of a (start, stop, step) range."""
    n = 0
    if start < stop:
        n = ((stop - start - 1) // step + 1);
    return n

def to_ndarray(array, dtype, arrlen=None):
    """Convert object to a ndarray."""

    if dtype is None:
        return np.array(array)

    # Arrays with a 0 stride are special
    if type(array) == np.ndarray and array.strides[0] == 0:
        if array.dtype != dtype.base:
            raise TypeError, "dtypes do not match"
        return array

    # Ensure that we have an ndarray of the correct dtype
    if type(array) != np.ndarray or array.dtype != dtype.base:
        try:
            array = np.array(array, dtype=dtype.base)
        except ValueError:
            raise ValueError, "cannot convert to an ndarray object"

    # We need a contiguous array
    if not array.flags.contiguous:
        array = array.copy()
    if len(array.shape) == 0:
        # We treat scalars like undimensional arrays
        array.shape = (1,)

    # Check if we need a broadcast
    if arrlen is not None and arrlen != len(array):
        array2 = np.empty(shape=(arrlen,), dtype=dtype)
        array2[:] = array   # broadcast
        array = array2

    return array

def human_readable_size(size):
    """Return a string for better assessing large number of bytes."""
    if size < 2**10:
        return "%s" % size
    elif size < 2**20:
        return "%.2f KB" % (size / float(2**10))
    elif size < 2**30:
        return "%.2f MB" % (size / float(2**20))
    elif size < 2**40:
        return "%.2f GB" % (size / float(2**30))
    else:
        return "%.2f TB" % (size / float(2**40))


# Main part
# =========
if __name__ == '__main__':
    print human_readable_size(1023)
    print human_readable_size(10234)
    print human_readable_size(10234*100)
    print human_readable_size(10234*10000)
    print human_readable_size(10234*1000000)
    print human_readable_size(10234*100000000)
    print human_readable_size(10234*1000000000)


## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## fill-column: 72
## End:

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# carray documentation build configuration file, created by
# sphinx-quickstart on Mon Dec 13 13:54:01 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
#extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']
# `viewcode` dona alguns problemes:
# http://bitbucket.org/birkenfeld/sphinx/issue/515/keyerror-while-building
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.ifconfig']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'carray'
copyright = u'2010,2011 Francesc Alted / 2012 Continuum Analytics, Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'carraydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'carray.tex', u'carray Documentation',
   u'Francesc Alted', 'manual'),
]

# Appendices only appear in the latex output, so bad luck
#latex_appendices = ['defaults']

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'carray', u'carray Documentation',
     [u'Francesc Alted'], 1)
]

########NEW FILE########
__FILENAME__ = pavement
########################################################################
#
#       License: BSD
#       Created: December 14, 2010
#       Author:  Francesc Alted - francesc@continuum.io
#
########################################################################

import sys, os, glob
import textwrap
import subprocess

from paver.easy import *
from paver.setuputils import setup, install_distutils_tasks
from distutils.core import Extension
from distutils.dep_util import newer

# Some functions for showing errors and warnings.
def _print_admonition(kind, head, body):
    tw = textwrap.TextWrapper(
        initial_indent='   ', subsequent_indent='   ')

    print(".. %s:: %s" % (kind.upper(), head))
    for line in tw.wrap(body):
        print line

def exit_with_error(head, body=''):
    _print_admonition('error', head, body)
    sys.exit(1)

def print_warning(head, body=''):
    _print_admonition('warning', head, body)

def check_import(pkgname, pkgver):
    try:
        mod = __import__(pkgname)
    except ImportError:
            exit_with_error(
                "You need %(pkgname)s %(pkgver)s or greater to run carray!"
                % {'pkgname': pkgname, 'pkgver': pkgver} )
    else:
        if mod.__version__ < pkgver:
            exit_with_error(
                "You need %(pkgname)s %(pkgver)s or greater to run carray!"
                % {'pkgname': pkgname, 'pkgver': pkgver} )

    print ( "* Found %(pkgname)s %(pkgver)s package installed."
            % {'pkgname': pkgname, 'pkgver': mod.__version__} )
    globals()[pkgname] = mod


########### Check versions ##########

# Check for Python
if not (sys.version_info[0] >= 2 and sys.version_info[1] >= 6):
    exit_with_error("You need Python 2.6 or greater to install carray!")

# The minimum version of Cython required for generating extensions
min_cython_version = '0.16'
# The minimum version of NumPy required
min_numpy_version = '1.5'
# The minimum version of Numexpr (optional)
min_numexpr_version = '1.4.1'

# Check for Cython
cython = False
try:
    from Cython.Compiler.Main import Version
    if Version.version < min_cython_version:
        cython = False
    else:
        cython = True
except:
    pass

# Check for NumPy
check_import('numpy', min_numpy_version)

# Check for Numexpr
numexpr_here = False
try:
    import numexpr
except ImportError:
    print_warning(
        "Numexpr is not installed.  For faster carray operation, "
        "please consider installing it.")
else:
    if numexpr.__version__ >= min_numexpr_version:
        numexpr_here = True
        print ( "* Found %(pkgname)s %(pkgver)s package installed."
                % {'pkgname': 'numexpr', 'pkgver': numexpr.__version__} )
    else:
        print_warning(
            "Numexpr %s installed, but version is not >= %s.  "
            "Disabling support for it." % (
            numexpr.__version__, min_numexpr_version))

########### End of version checks ##########

# carray version
VERSION = open('VERSION').read().strip()
# Create the version.py file
open('carray/version.py', 'w').write('__version__ = "%s"\n' % VERSION)


# Global variables
CFLAGS = os.environ.get('CFLAGS', '').split()
LFLAGS = os.environ.get('LFLAGS', '').split()
lib_dirs = []
libs = []
inc_dirs = ['carray', 'blosc']
# Include NumPy header dirs
from numpy.distutils.misc_util import get_numpy_include_dirs
inc_dirs.extend(get_numpy_include_dirs())
cython_pyxfiles = glob.glob('carray/*.pyx')
cython_cfiles = [fn.split('.')[0] + '.c' for fn in cython_pyxfiles]
blosc_files = glob.glob('blosc/*.c')

# Handle --lflags=[FLAGS] --cflags=[FLAGS]
args = sys.argv[:]
for arg in args:
    if arg.find('--lflags=') == 0:
        LFLAGS = arg.split('=')[1].split()
        sys.argv.remove(arg)
    elif arg.find('--cflags=') == 0:
        CFLAGS = arg.split('=')[1].split()
        sys.argv.remove(arg)

# Add -msse2 flag for optimizing shuffle in Blosc
if os.name == 'posix':
    CFLAGS.append("-msse2")


# Paver tasks
@task
def cythonize():
    for fn in glob.glob('carray/*.pyx'):
         dest = fn.split('.')[0] + '.c'
         if newer(fn, dest):
             if not cython:
                 exit_with_error(
                     "Need Cython >= %s to generate extensions."
                     % min_cython_version)
             sh("cython " + fn)

@task
@needs('html', 'setuptools.command.sdist')
def sdist():
    """Generate a source distribution for the package."""
    pass

@task
@needs(['cythonize', 'setuptools.command.build'])
def build():
     pass

@task
@needs(['cythonize', 'setuptools.command.build_ext'])
def build_ext():
     pass

@task
@needs('paver.doctools.html')
def html(options):
    """Build the docs in HTML format."""
    destdir = path("doc/html")
    destdir.rmtree()
    builtdocs = path("doc") / options.builddir / "html"
    builtdocs.move(destdir)

@task
def pdf(options):
    """Build the docs in PDF format."""
    dest = path("doc") / "carray-manual.pdf"
    sh("cd doc; make latexpdf")
    builtdocs = path("doc") / options.builddir / "latex" / "carray.pdf"
    builtdocs.move(dest)


# Options for Paver tasks
options(

    sphinx = Bunch(
        docroot = "doc",
        builddir = "_build"
    ),

)


classifiers = """\
Development Status :: 4 - Beta
Intended Audience :: Developers
Intended Audience :: Information Technology
Intended Audience :: Science/Research
License :: OSI Approved :: BSD License
Programming Language :: Python
Topic :: Software Development :: Libraries :: Python Modules
Operating System :: Microsoft :: Windows
Operating System :: Unix
"""

# Package options
setup(
    name = 'carray',
    version = VERSION,
    description = "A chunked data container that can be compressed in-memory.",
    long_description = """\
carray is a chunked container for numerical data.  Chunking allows for
efficient enlarging/shrinking of data container.  In addition, it can
also be compressed for reducing memory needs.  The compression process
is carried out internally by Blosc, a high-performance compressor that
is optimized for binary data.""",
    classifiers = filter(None, classifiers.split("\n")),
    author = 'Francesc Alted',
    author_email = 'francesc@continuum.io',
    url = "https://github.com/FrancescAlted/carray",
    license = 'http://www.opensource.org/licenses/bsd-license.php',
    download_url = "http://carray.pytables.org/download/carray-%s/carray-%s.tar.gz" % (VERSION, VERSION),
    platforms = ['any'],
    ext_modules = [
    Extension( "carray.carrayExtension",
               include_dirs=inc_dirs,
               sources = cython_cfiles + blosc_files,
               depends = ["carray/definitions.pxd"] + blosc_files,
               library_dirs=lib_dirs,
               libraries=libs,
               extra_link_args=LFLAGS,
               extra_compile_args=CFLAGS ),
    ],
    packages = ['carray', 'carray.tests'],
    include_package_data = True,

)


########NEW FILE########
