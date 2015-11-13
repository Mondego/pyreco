__FILENAME__ = branin
import numpy as np
import sys
import math
import time

def branin(x):

  x[0] = x[0]*15
  x[1] = (x[1]*15)-5

  y = np.square(x[1] - (5.1/(4*np.square(math.pi)))*np.square(x[0]) + (5/math.pi)*x[0] - 6) + 10*(1-(1./(8*math.pi)))*np.cos(x[0]) + 10;

  result = y

  print result
  return result

# Write a function like this called 'main'
def main(job_id, params):
  print 'Anything printed here will end up in the output directory for job #:', str(job_id)
  print params
  return branin(params['X'])

########NEW FILE########
__FILENAME__ = dejong
def dejong(x,y):
    return x*x + y*y

# Write a function like this called 'main'
def main(job_id, params):
  x = params['X'][0]
  y = params['Y'][0]
  res = dejong(x, y)
  print "De Jong's function in 2D:"
  print "\tf(%.2f, %0.2f) = %f" % (x, y, res)
  return dejong(x, y)


if __name__ == "__main__":
    main(23, {'X': [1.2], 'Y': [4.3]})

########NEW FILE########
__FILENAME__ = faker
import sys
import math
import time
import random


# A fake task that sleeps and returns a random result so we can test and debug
# spearmint without wasting CPU and energy computing real functions.

def main(job_id, params):
    time.sleep(random.random() * 2)
    return random.random() * 100

########NEW FILE########
__FILENAME__ = rosenbrock
import math

def rosenbrocks_valley(xs):
    sum = 0
    last_x = xs[0]

    for i in xrange(1, len(xs)):
        sum += (100 * math.pow((xs[i] - math.pow(last_x, 2)), 2)) + math.pow(1 - last_x, 2)

    return sum

def main(job_id, params):
  xs = params['X']
  res = rosenbrocks_valley(xs)

  print "Rosenbrock's Valley in %d dimensions" % (len(xs))
  print "\tf(",
  print xs,
  print ") = %f" % (res)

  return rosenbrocks_valley(xs)


if __name__ == "__main__":
    main(3, {'X': [1.73, 0.2]})

########NEW FILE########
__FILENAME__ = camel
import math

def camel(x,y):
    x2 = math.pow(x,2)
    x4 = math.pow(x,4)
    y2 = math.pow(y,2)

    return (4.0 - 2.1 * x2 + (x4 / 3.0)) * x2 + x*y + (-4.0 + 4.0 * y2) * y2


def main(job_id, params):
  x = params['X'][0]
  y = params['Y'][0]
  res = camel(x, y)
  print "The Six hump camel back function:"
  print "\tf(%.4f, %0.4f) = %f" % (x, y, res)
  return camel(x, y)


if __name__ == "__main__":
    main(23, {'X': [0.0898], 'Y': [-0.7126]})

########NEW FILE########
__FILENAME__ = cma
#!/usr/bin/env python
"""Module cma implements the CMA-ES, Covariance Matrix Adaptation Evolution
Strategy, a stochastic optimizer for robust non-linear non-convex
derivative-free function minimization for Python versions 2.6, 2.7, 3.x
(for Python 2.5 class SolutionDict would need to be re-implemented, because
it depends on collections.MutableMapping, since version 0.91.01).

CMA-ES searches for a minimizer (a solution x in R**n) of an
objective function f (cost function), such that f(x) is
minimal. Regarding f, only function values for candidate solutions
need to be available, gradients are not necessary. Even less
restrictive, only a passably reliable ranking of the candidate
solutions in each iteration is necessary, the function values
itself do not matter. Some termination criteria however depend
on actual f-values.

Two interfaces are provided:

  - function `fmin(func, x0, sigma0,...)`
        runs a complete minimization
        of the objective function func with CMA-ES.

  - class `CMAEvolutionStrategy`
      allows for minimization such that the
      control of the iteration loop remains with the user.


Used packages:

    - unavoidable: `numpy` (see `barecmaes2.py` if `numpy` is not
      available),
    - avoidable with small changes: `time`, `sys`
    - optional: `matplotlib.pylab` (for `plot` etc., highly
      recommended), `pprint` (pretty print), `pickle` (in class
      `Sections`), `doctest`, `inspect`, `pygsl` (never by default)

Testing
-------
The code can be tested on a given system. Typing::

    python cma.py --test

or in the Python shell ``ipython -pylab``::

    run cma.py --test

runs ``doctest.testmod(cma)`` showing only exceptions (and not the
tests that fail due to small differences in the output) and should
run without complaints in about under two minutes. On some systems,
the pop up windows must be closed manually to continue and finish
the test.

Install
-------
The code can be installed by::

    python cma.py --install

which solely calls the ``setup`` function from the ``distutils.core``
package for installation.

Example
-------
::

    import cma
    help(cma)  # "this" help message, use cma? in ipython
    help(cma.fmin)
    help(cma.CMAEvolutionStrategy)
    help(cma.Options)
    cma.Options('tol')  # display 'tolerance' termination options
    cma.Options('verb') # display verbosity options
    res = cma.fmin(cma.Fcts.tablet, 15 * [1], 1)
    res[0]  # best evaluated solution
    res[5]  # mean solution, presumably better with noise

:See: `fmin()`, `Options`, `CMAEvolutionStrategy`

:Author: Nikolaus Hansen, 2008-2012

:License: GPL 2 and 3

"""
from __future__ import division  # future is >= 3.0, this code has mainly been used with 2.6 & 2.7
from __future__ import with_statement  # only necessary for python 2.5 and not in heavy use
# from __future__ import collections.MutableMapping # does not exist in future, otherwise 2.5 would work
from __future__ import print_function  # for cross-checking, available from python 2.6
import sys
if sys.version.startswith('3'):  # in python 3.x
    xrange = range
    raw_input = input

__version__ = "0.92.04 $Revision: 3322 $ $Date: 2012-11-22 18:05:10 +0100 (Thu, 22 Nov 2012) $"
#    bash: svn propset svn:keywords 'Date Revision' cma.py

#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 or 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# for testing:
#   pyflakes cma.py   # finds bugs by static analysis
#   pychecker --limit 60 cma.py  # also executes, gives 60 warnings (all checked)
#   python cma.py -t -quiet # executes implemented tests based on doctest

# to create a html documentation file:
#    pydoc -w cma  # edit the header (remove local pointers)
#    epydoc cma.py  # comes close to javadoc but does not find the
#                   # links of function references etc
#    doxygen needs @package cma as first line in the module docstring
#       some things like class attributes are not interpreted correctly
#    sphinx: doc style of doc.python.org, could not make it work

# TODO: make those options that are only used in fmin an error in init of CMA, but still Options() should
#       work as input to CMA.
# TODO: add a default logger in CMAEvolutionStrategy, see fmin() and optimize() first
#        tell() should probably not add data, but optimize() should handle even an after_iteration_handler.
# TODO: CMAEvolutionStrategy(ones(10), 1).optimize(cma.fcts.elli)  # should work like fmin
#       one problem: the data logger is not default and seemingly cannot be attached in one line
# TODO: check combination of boundary handling and transformation: penalty must be computed
#       on gp.pheno(x_geno, bounds=None), but without bounds, check/remove usage of .geno everywhere
# TODO: check whether all new solutions are put into self.sent_solutions
# TODO: separate initialize==reset_state from __init__
# TODO: introduce Zpos == diffC which makes the code more consistent and the active update "exact"
# TODO: split tell into a variable transformation part and the "pure" functionality
#       usecase: es.tell_geno(X, [func(es.pheno(x)) for x in X])
#       genotypic repair is not part of tell_geno
# TODO: read settable "options" from a (properties) file, see myproperties.py
#
# typical parameters in scipy.optimize: disp, xtol, ftol, maxiter, maxfun, callback=None
#         maxfev, diag (A sequency of N positive entries that serve as
#                 scale factors for the variables.)
#           full_output -- non-zero to return all optional outputs.
#   If xtol < 0.0, xtol is set to sqrt(machine_precision)
#    'infot -- a dictionary of optional outputs with the keys:
#                      'nfev': the number of function calls...
#
#    see eg fmin_powell
# typical returns
#        x, f, dictionary d
#        (xopt, {fopt, gopt, Hopt, func_calls, grad_calls, warnflag}, <allvecs>)
#
# TODO: keep best ten solutions
# TODO: implement constraints handling
# TODO: option full_output -- non-zero to return all optional outputs.
# TODO: extend function unitdoctest, or use unittest?
# TODO: implement equal-fitness termination, covered by stagnation?
# TODO: apply style guide: no capitalizations!?
# TODO: check and test dispdata()
# TODO: eigh(): thorough testing would not hurt
#
# TODO (later): implement readSignals from a file like properties file (to be called after tell())

import time  # not really essential
import collections, numpy as np # arange, cos, size, eye, inf, dot, floor, outer, zeros, linalg.eigh, sort, argsort, random, ones,...
from numpy import inf, array, dot, exp, log, sqrt, sum   # to access the built-in sum fct:  __builtins__.sum or del sum removes the imported sum and recovers the shadowed
try:
    import matplotlib.pylab as pylab  # also: use ipython -pylab
    show = pylab.show
    savefig = pylab.savefig   # we would like to be able to use cma.savefig() etc
    closefig = pylab.close
except:
    pylab = None
    print('  Could not import matplotlib.pylab, therefore ``cma.plot()`` etc. is not available')
    def show():
        pass

__docformat__ = "reStructuredText"  # this hides some comments entirely?

sys.py3kwarning = True  # TODO: out-comment from version 2.6

# why not package math?

# TODO: check scitools.easyviz and how big the adaptation would be

# changes:
# 12/10/25: removed useless check_points from fmin interface
# 12/10/17: bug fix printing number of infeasible samples, moved not-in-use methods
#           timesCroot and divCroot to the right class
# 12/10/16 (0.92.00): various changes commit: bug bound[0] -> bounds[0], more_to_write fixed,
#   sigma_vec introduced, restart from elitist, trace normalization, max(mu,popsize/2)
#   is used for weight calculation.
# 12/07/23: (bug:) BoundPenalty.update respects now genotype-phenotype transformation
# 12/07/21: convert value True for noisehandling into 1 making the output compatible
# 12/01/30: class Solution and more old stuff removed r3101
# 12/01/29: class Solution is depreciated, GenoPheno and SolutionDict do the job (v0.91.00, r3100)
# 12/01/06: CMA_eigenmethod option now takes a function (integer still works)
# 11/09/30: flat fitness termination checks also history length
# 11/09/30: elitist option (using method clip_or_fit_solutions)
# 11/09/xx: method clip_or_fit_solutions for check_points option for all sorts of
#           injected or modified solutions and even reliable adaptive encoding
# 11/08/19: fixed: scaling and typical_x type clashes 1 vs array(1) vs ones(dim) vs dim * [1]
# 11/07/25: fixed: fmin wrote first and last line even with verb_log==0
#           fixed: method settableOptionsList, also renamed to versatileOptions
#           default seed depends on time now
# 11/07/xx (0.9.92): added: active CMA, selective mirrored sampling, noise/uncertainty handling
#           fixed: output argument ordering in fmin, print now only used as function
#           removed: parallel option in fmin
# 11/07/01: another try to get rid of the memory leak by replacing self.unrepaired = self[:]
# 11/07/01: major clean-up and reworking of abstract base classes and of the documentation,
#           also the return value of fmin changed and attribute stop is now a method.
# 11/04/22: bug-fix: option fixed_variables in combination with scaling
# 11/04/21: stopdict is not a copy anymore
# 11/04/15: option fixed_variables implemented
# 11/03/23: bug-fix boundary update was computed even without boundaries
# 11/03/12: bug-fix of variable annotation in plots
# 11/02/05: work around a memory leak in numpy
# 11/02/05: plotting routines improved
# 10/10/17: cleaning up, now version 0.9.30
# 10/10/17: bug-fix: return values of fmin now use phenotyp (relevant
#           if input scaling_of_variables is given)
# 08/10/01: option evalparallel introduced,
#           bug-fix for scaling being a vector
# 08/09/26: option CMAseparable becomes CMA_diagonal
# 08/10/18: some names change, test functions go into a class
# 08/10/24: more refactorizing
# 10/03/09: upper bound exp(min(1,...)) for step-size control


# TODO: this would define the visible interface
# __all__ = ['fmin', 'CMAEvolutionStrategy', 'plot', ...]
#


# emptysets = ('', (), [], {}) # array([]) does not work but also np.size(.) == 0
# "x in emptysets" cannot be well replaced by "not x"
# which is also True for array([]) and None, but also for 0 and False, and False for NaN

use_sent_solutions = True  # 5-30% CPU slower, particularly for large lambda, will be mandatory soon

#____________________________________________________________
#____________________________________________________________
#
def unitdoctest():
    """is used to describe test cases and might in future become helpful
    as an experimental tutorial as well. The main testing feature at the
    moment is by doctest with ``cma._test()`` or conveniently by
    ``python cma.py --test``. With the ``--verbose`` option added, the
    results will always slightly differ and many "failed" test cases
    might be reported.

    A simple first overall test:
        >>> import cma
        >>> res = cma.fmin(cma.fcts.elli, 3*[1], 1, CMA_diagonal=2, seed=1, verb_time=0)
        (3_w,7)-CMA-ES (mu_w=2.3,w_1=58%) in dimension 3 (seed=1)
           Covariance matrix is diagonal for 2 iterations (1/ccov=7.0)
        Iterat #Fevals   function value     axis ratio  sigma   minstd maxstd min:sec
            1       7 1.453161670768570e+04 1.2e+00 1.08e+00  1e+00  1e+00
            2      14 3.281197961927601e+04 1.3e+00 1.22e+00  1e+00  2e+00
            3      21 1.082851071704020e+04 1.3e+00 1.24e+00  1e+00  2e+00
          100     700 8.544042012075362e+00 1.4e+02 3.18e-01  1e-03  2e-01
          200    1400 5.691152415221861e-12 1.0e+03 3.82e-05  1e-09  1e-06
          220    1540 3.890107746209078e-15 9.5e+02 4.56e-06  8e-11  7e-08
        termination on tolfun : 1e-11
        final/bestever f-value = 3.89010774621e-15 2.52273602735e-15
        mean solution:  [ -4.63614606e-08  -3.42761465e-10   1.59957987e-11]
        std deviation: [  6.96066282e-08   2.28704425e-09   7.63875911e-11]

    Test on the Rosenbrock function with 3 restarts. The first trial only
    finds the local optimum, which happens in about 20% of the cases.
        >>> import cma
        >>> res = cma.fmin(cma.fcts.rosen, 4*[-1],1, ftarget=1e-6, restarts=3, verb_time=0, verb_disp=500, seed=3)
        (4_w,8)-CMA-ES (mu_w=2.6,w_1=52%) in dimension 4 (seed=3)
        Iterat #Fevals   function value     axis ratio  sigma   minstd maxstd min:sec
            1       8 4.875315645656848e+01 1.0e+00 8.43e-01  8e-01  8e-01
            2      16 1.662319948123120e+02 1.1e+00 7.67e-01  7e-01  8e-01
            3      24 6.747063604799602e+01 1.2e+00 7.08e-01  6e-01  7e-01
          184    1472 3.701428610430019e+00 4.3e+01 9.41e-07  3e-08  5e-08
        termination on tolfun : 1e-11
        final/bestever f-value = 3.70142861043 3.70142861043
        mean solution:  [-0.77565922  0.61309336  0.38206284  0.14597202]
        std deviation: [  2.54211502e-08   3.88803698e-08   4.74481641e-08   3.64398108e-08]
        (8_w,16)-CMA-ES (mu_w=4.8,w_1=32%) in dimension 4 (seed=4)
        Iterat #Fevals   function value     axis ratio  sigma   minstd maxstd min:sec
            1    1489 2.011376859371495e+02 1.0e+00 8.90e-01  8e-01  9e-01
            2    1505 4.157106647905128e+01 1.1e+00 8.02e-01  7e-01  7e-01
            3    1521 3.548184889359060e+01 1.1e+00 1.02e+00  8e-01  1e+00
          111    3249 6.831867555502181e-07 5.1e+01 2.62e-02  2e-04  2e-03
        termination on ftarget : 1e-06
        final/bestever f-value = 6.8318675555e-07 1.18576673231e-07
        mean solution:  [ 0.99997004  0.99993938  0.99984868  0.99969505]
        std deviation: [ 0.00018973  0.00038006  0.00076479  0.00151402]
        >>> assert res[1] <= 1e-6

    Notice the different termination conditions. Termination on the target
    function value ftarget prevents further restarts.

    Test of scaling_of_variables option
        >>> import cma
        >>> opts = cma.Options()
        >>> opts['seed'] = 456
        >>> opts['verb_disp'] = 0
        >>> opts['CMA_active'] = 1
        >>> # rescaling of third variable: for searching in  roughly
        >>> #   x0 plus/minus 1e3*sigma0 (instead of plus/minus sigma0)
        >>> opts.scaling_of_variables = [1, 1, 1e3, 1]
        >>> res = cma.fmin(cma.fcts.rosen, 4 * [0.1], 0.1, **opts)
        termination on tolfun : 1e-11
        final/bestever f-value = 2.68096173031e-14 1.09714829146e-14
        mean solution:  [ 1.00000001  1.00000002  1.00000004  1.00000007]
        std deviation: [  3.00466854e-08   5.88400826e-08   1.18482371e-07   2.34837383e-07]

    The printed std deviations reflect the actual true value (not the one
    in the internal representation which would be different).
        >>> import cma
        >>> r = cma.fmin(cma.fcts.diffpow, 15 * [1], 1, CMA_dampsvec_fac=0.5, ftarget=1e-9)
        >>> assert(r[1] < 1e-9)
        >>> assert(r[2] < 13000)  # only passed with CMA_dampsvec_fac


	:See: cma.main(), cma._test()

    """

    pass


#____________________________________________________________
#____________________________________________________________
#
class BlancClass(object):
    """blanc container class for having a collection of attributes"""

#_____________________________________________________________________
#_____________________________________________________________________
#
class DerivedDictBase(collections.MutableMapping):
    """for conveniently adding features to a dictionary. The actual
    dictionary is in ``self.data``. Copy-paste
    and modify setitem, getitem, and delitem, if necessary"""
    def __init__(self, *args, **kwargs):
        # collections.MutableMapping.__init__(self)
        super(DerivedDictBase, self).__init__()
        # super(SolutionDict, self).__init__()  # the same
        self.data = dict(*args, **kwargs)
    def __len__(self):
        return len(self.data)
    def __contains__(self, value):
        return value in self.data
    def __iter__(self):
        return iter(self.data)
    def __setitem__(self, key, value):
        """defines self[key] = value"""
        self.data[key] = value
    def __getitem__(self, key):
        """defines self[key]"""
        return self.data[key]
    def __delitem__(self, key):
        del self.data[key]

class SolutionDict(DerivedDictBase):
    """dictionary with computation of an hash key for the inserted solutions and
    a stack of previously inserted same solutions.
    Each entry is meant to store additional information related to the solution.

        >>> import cma, numpy as np
        >>> d = cma.SolutionDict()
        >>> x = np.array([1,2,4])
        >>> d[x] = {'x': x, 'iteration': 1}
        >>> d.get(x) == (d[x] if d.key(x) in d.keys() else None)

    The last line is always true.

    TODO: data_with_same_key behaves like a stack (see setitem and delitem), but rather should behave like a queue?!
    A queue is less consistent with the operation self[key] = ..., if self.data_with_same_key[key] is not empty.

    """
    def __init__(self, *args, **kwargs):
        DerivedDictBase.__init__(self, *args, **kwargs)
        self.data_with_same_key = {}
    def key(self, x):
        try:
            return tuple(x)
        except TypeError:
            return x
    def __setitem__(self, key, value):
        """defines self[key] = value"""
        key = self.key(key)
        if key in self.data_with_same_key:
            self.data_with_same_key[key] += [self.data[key]]
        elif key in self.data:
            self.data_with_same_key[key] = [self.data[key]]
        self.data[key] = value
    def __getitem__(self, key):
        """defines self[key]"""
        return self.data[self.key(key)]
    def __delitem__(self, key):
        """remove only most current key-entry"""
        key = self.key(key)
        if key in self.data_with_same_key:
            if len(self.data_with_same_key[key]) == 1:
                self.data[key] = self.data_with_same_key.pop(key)[0]
            else:
                self.data[key] = self.data_with_same_key[key].pop(-1)
        else:
            del self.data[key]
    def truncate(self, max_len, min_iter):
        if len(self) > max_len:
            for k in list(self.keys()):
                if self[k]['iteration'] < min_iter:
                    del self[k]  # only deletes one item with k as key, should delete all?

class SolutionDictOld(dict):
    """depreciated, SolutionDict should do, to be removed after SolutionDict
    has been successfully applied.
    dictionary with computation of an hash key for the inserted solutions and
    stack of previously inserted same solutions.
    Each entry is meant to store additional information related to the solution.
    Methods ``pop`` and ``get`` are modified accordingly.

        d = SolutionDict()
        x = array([1,2,4])
        d.insert(x, {'x': x, 'iteration': 1})
        d.get(x) == d[d.key(x)] if d.key(x) in d.keys() else d.get(x) is None

    TODO: not yet tested
    TODO: behaves like a stack (see _pop_derived), but rather should behave like a queue?!
    A queue is less consistent with the operation self[key] = ..., if self.more[key] is not empty.

    """
    def __init__(self):
        self.more = {}  # previously inserted same solutions
        self._pop_base = self.pop
        self.pop = self._pop_derived
        self._get_base = self.get
        self.get = self._get_derived
    def key(self, x):
        """compute the hash key of ``x``"""
        return tuple(x)
    def insert(self, x, datadict):
        key = self.key(x)
        if key in self.more:
            self.more[key] += [self[key]]
        elif key in self:
            self.more[key] = [self[key]]
        self[key] = datadict
    def _get_derived(self, x, default=None):
        return self._get_base(self.key(x), default)
    def _pop_derived(self, x):
        key = self.key(x)
        res = self[key]
        if key in self.more:
            if len(self.more[key]) == 1:
                self[key] = self.more.pop(key)[0]
            else:
                self[key] = self.more[key].pop(-1)
        return res
class BestSolution(object):
    """container to keep track of the best solution seen"""
    def __init__(self, x=None, f=np.inf, evals=None):
        """initialize the best solution with `x`, `f`, and `evals`.
        Better solutions have smaller `f`-values.

        """
        self.x = x
        self.x_geno = None
        self.f = f if f is not None and f is not np.nan else np.inf
        self.evals = evals
        self.evalsall = evals
        self.last = BlancClass()
        self.last.x = x
        self.last.f = f
    def update(self, arx, xarchive=None, arf=None, evals=None):
        """checks for better solutions in list `arx`, based on the smallest
        corresponding value in `arf`, alternatively, `update` may be called
        with a `BestSolution` instance like ``update(another_best_solution)``
        in which case the better solution becomes the current best.

        `xarchive` is used to retrieve the genotype of a solution.

        """
        if arf is not None:  # find failsave minimum
            minidx = np.nanargmin(arf)
            if minidx is np.nan:
                return
            minarf = arf[minidx]
            # minarf = reduce(lambda x, y: y if y and y is not np.nan and y < x else x, arf, np.inf)
        if type(arx) == BestSolution:
            if self.evalsall is None:
                self.evalsall = arx.evalsall
            elif arx.evalsall is not None:
                self.evalsall = max((self.evalsall, arx.evalsall))
            if arx.f is not None and arx.f < np.inf:
                self.update([arx.x], xarchive, [arx.f], arx.evals)
            return self
        elif minarf < np.inf and (minarf < self.f or self.f is None):
            self.x, self.f = arx[minidx], arf[minidx]
            self.x_geno = xarchive[self.x]['geno'] if xarchive is not None else None
            self.evals = None if not evals else evals - len(arf) + minidx+1
            self.evalsall = evals
        elif evals:
            self.evalsall = evals
        self.last.x = arx[minidx]
        self.last.f = minarf
    def get(self):
        """return ``(x, f, evals)`` """
        return self.x, self.f, self.evals, self.x_geno

#____________________________________________________________
#____________________________________________________________
#
class BoundPenalty(object):
    """Computes the boundary penalty. Must be updated each iteration,
    using the `update` method.

    Details
    -------
    The penalty computes like ``sum(w[i] * (x[i]-xfeas[i])**2)``,
    where `xfeas` is the closest feasible (in-bounds) solution from `x`.
    The weight `w[i]` should be updated during each iteration using
    the update method.

    This class uses `GenoPheno.into_bounds` in method `update` to access
    domain boundary values and repair. This inconsistency is going to be
    removed in future.

    """
    def __init__(self, bounds=None):
        """Argument bounds can be `None` or ``bounds[0]`` and ``bounds[1]``
        are lower  and upper domain boundaries, each is either `None` or
        a scalar or a list or array of appropriate size.
        """
        ##
        # bounds attribute reminds the domain boundary values
        self.bounds = bounds

        self.gamma = 1  # a very crude assumption
        self.weights_initialized = False  # gamma becomes a vector after initialization
        self.hist = []  # delta-f history

    def has_bounds(self):
        """return True, if any variable is bounded"""
        bounds = self.bounds
        if bounds in (None, [None, None]):
            return False
        for i in xrange(bounds[0]):
            if bounds[0][i] is not None and bounds[0][i] > -np.inf:
                return True
        for i in xrange(bounds[1]):
            if bounds[1][i] is not None and bounds[1][i] < np.inf:
                return True
        return False

    def repair(self, x, bounds=None, copy=False, copy_always=False):
        """sets out-of-bounds components of ``x`` on the bounds.

        Arguments
        ---------
            `bounds`
                can be `None`, in which case the "default" bounds are used,
                or ``[lb, ub]``, where `lb` and `ub`
                represent lower and upper domain bounds respectively that
                can be `None` or a scalar or a list or array of length ``len(self)``

        code is more or less copy-paste from Solution.repair, but never tested

        """
        # TODO (old data): CPU(N,lam,iter=20,200,100): 3.3s of 8s for two bounds, 1.8s of 6.5s for one bound
        # TODO: test whether np.max([bounds[0], x], axis=0) etc is speed relevant

        if bounds is None:
            bounds = self.bounds
        if copy_always:
            x_out = array(x, copy=True)
        if bounds not in (None, [None, None], (None, None)):  # solely for effiency
            x_out = array(x, copy=True) if copy and not copy_always else x
            if bounds[0] is not None:
                if np.isscalar(bounds[0]):
                    for i in xrange(len(x)):
                        x_out[i] = max([bounds[0], x[i]])
                else:
                    for i in xrange(len(x)):
                        if bounds[0][i] is not None:
                            x_out[i] = max([bounds[0][i], x[i]])
            if bounds[1] is not None:
                if np.isscalar(bounds[1]):
                    for i in xrange(len(x)):
                        x_out[i] = min([bounds[1], x[i]])
                else:
                    for i in xrange(len(x)):
                        if bounds[1][i] is not None:
                            x_out[i] = min([bounds[1][i], x[i]])
        return x_out  # convenience return

    #____________________________________________________________
    #
    def __call__(self, x, archive, gp):
        """returns the boundary violation penalty for `x` ,where `x` is a
        single solution or a list or array of solutions.
        If `bounds` is not `None`, the values in `bounds` are used, see `__init__`"""
        if x in (None, (), []):
            return x
        if gp.bounds in (None, [None, None], (None, None)):
            return 0.0 if np.isscalar(x[0]) else [0.0] * len(x) # no penalty

        x_is_single_vector = np.isscalar(x[0])
        x = [x] if x_is_single_vector else x

        pen = []
        for xi in x:
            # CAVE: this does not work with already repaired values!!
            # CPU(N,lam,iter=20,200,100)?: 3s of 10s, array(xi): 1s (check again)
            # remark: one deep copy can be prevented by xold = xi first
            xpheno = gp.pheno(archive[xi]['geno'])
            xinbounds = gp.into_bounds(xpheno)
            fac = 1  # exp(0.1 * (log(self.scal) - np.mean(self.scal)))
            pen.append(sum(self.gamma * ((xinbounds - xpheno) / fac)**2) / len(xi))

        return pen[0] if x_is_single_vector else pen

    #____________________________________________________________
    #
    def feasible_ratio(self, solutions):
        """counts for each coordinate the number of feasible values in
        ``solutions`` and returns an array of length ``len(solutions[0])``
        with the ratios.

        `solutions` is a list or array of repaired `Solution` instances

        """
        count = np.zeros(len(solutions[0]))
        for x in solutions:
            count += x.unrepaired == x
        return count / float(len(solutions))

    #____________________________________________________________
    #
    def update(self, function_values, es, bounds=None):
        """updates the weights for computing a boundary penalty.

        Arguments
        ---------
        `function_values`
            all function values of recent population of solutions
        `es`
            `CMAEvolutionStrategy` object instance, in particular the
            method `into_bounds` of the attribute `gp` of type `GenoPheno`
            is used.
        `bounds`
            not (yet) in use other than for ``bounds == [None, None]`` nothing
            is updated.

        Reference: Hansen et al 2009, A Method for Handling Uncertainty...
        IEEE TEC, with addendum at http://www.lri.fr/~hansen/TEC2009online.pdf

        """
        if bounds is None:
            bounds = self.bounds
        if bounds is None or (bounds[0] is None and bounds[1] is None):  # no bounds ==> no penalty
            return self  # len(function_values) * [0.0]  # case without voilations

        N = es.N
        ### prepare
        # compute varis = sigma**2 * C_ii
        varis = es.sigma**2 * array(N * [es.C] if np.isscalar(es.C) else (  # scalar case
                                es.C if np.isscalar(es.C[0]) else  # diagonal matrix case
                                [es.C[i][i] for i in xrange(N)]))  # full matrix case

        # dmean = (es.mean - es.gp.into_bounds(es.mean)) / varis**0.5
        dmean = (es.mean - es.gp.geno(es.gp.into_bounds(es.gp.pheno(es.mean)))) / varis**0.5

        ### Store/update a history of delta fitness value
        fvals = sorted(function_values)
        l = 1 + len(fvals)
        val = fvals[3*l // 4] - fvals[l // 4] # exact interquartile range apart interpolation
        val = val / np.mean(varis)  # new: val is normalized with sigma of the same iteration
        # insert val in history
        if np.isfinite(val) and val > 0:
            self.hist.insert(0, val)
        elif val == inf and len(self.hist) > 1:
            self.hist.insert(0, max(self.hist))
        else:
            pass  # ignore 0 or nan values
        if len(self.hist) > 20 + (3*N) / es.popsize:
            self.hist.pop()

        ### prepare
        dfit = np.median(self.hist)  # median interquartile range
        damp = min(1, es.sp.mueff/10./N)

        ### set/update weights
        # Throw initialization error
        if len(self.hist) == 0:
            raise _Error('wrongful initialization, no feasible solution sampled. ' +
                'Reasons can be mistakenly set bounds (lower bound not smaller than upper bound) or a too large initial sigma0 or... ' +
                'See description of argument func in help(cma.fmin) or an example handling infeasible solutions in help(cma.CMAEvolutionStrategy). ')
        # initialize weights
        if (dmean.any() and (not self.weights_initialized or es.countiter == 2)):  # TODO
            self.gamma = array(N * [2*dfit])
            self.weights_initialized = True
        # update weights gamma
        if self.weights_initialized:
            edist = array(abs(dmean) - 3 * max(1, N**0.5/es.sp.mueff))
            if 1 < 3:  # this is better, around a factor of two
                # increase single weights possibly with a faster rate than they can decrease
                #     value unit of edst is std dev, 3==random walk of 9 steps
                self.gamma *= exp((edist>0) * np.tanh(edist/3) / 2.)**damp
                # decrease all weights up to the same level to avoid single extremely small weights
                #    use a constant factor for pseudo-keeping invariance
                self.gamma[self.gamma > 5 * dfit] *= exp(-1./3)**damp
                #     self.gamma[idx] *= exp(5*dfit/self.gamma[idx] - 1)**(damp/3)
            elif 1 < 3 and (edist>0).any():  # previous method
                # CAVE: min was max in TEC 2009
                self.gamma[edist>0] *= 1.1**min(1, es.sp.mueff/10./N)
                # max fails on cigtab(N=12,bounds=[0.1,None]):
                # self.gamma[edist>0] *= 1.1**max(1, es.sp.mueff/10./N) # this was a bug!?
                # self.gamma *= exp((edist>0) * np.tanh(edist))**min(1, es.sp.mueff/10./N)
            else:  # alternative version, but not better
                solutions = es.pop  # this has not been checked
                r = self.feasible_ratio(solutions)  # has to be the averaged over N iterations
                self.gamma *= exp(np.max([N*[0], 0.3 - r], axis=0))**min(1, es.sp.mueff/10/N)
        es.more_to_write += list(self.gamma) if self.weights_initialized else N * [1.0]
        ### return penalty
        # es.more_to_write = self.gamma if not np.isscalar(self.gamma) else N*[1]
        return self  # bound penalty values

#____________________________________________________________
#____________________________________________________________
#
class GenoPhenoBase(object):
    """depreciated, abstract base class for genotyp-phenotype transformation,
    to be implemented.

    See (and rather use) option ``transformation`` of ``fmin`` or ``CMAEvolutionStrategy``.

    Example
    -------
    ::

        import cma
        class Mygpt(cma.GenoPhenoBase):
            def pheno(self, x):
                return x  # identity for the time being
        gpt = Mygpt()
        optim = cma.CMAEvolutionStrategy(...)
        while not optim.stop():
            X = optim.ask()
            f = [func(gpt.pheno(x)) for x in X]
            optim.tell(X, f)

    In case of a repair, we might pass the repaired solution into `tell()`
    (with check_points being True).

    TODO: check usecases in `CMAEvolutionStrategy` and implement option GenoPhenoBase

    """
    def pheno(self, x):
        raise NotImplementedError()
        return x

#____________________________________________________________
#____________________________________________________________
#
class GenoPheno(object):
    """Genotype-phenotype transformation.

    Method `pheno` provides the transformation from geno- to phenotype,
    that is from the internal representation to the representation used
    in the objective function. Method `geno` provides the "inverse" pheno-
    to genotype transformation. The geno-phenotype transformation comprises,
    in this order:

       - insert fixed variables (with the phenotypic and therefore quite
         possibly "wrong" values)
       - affine linear transformation (scaling and shift)
       - user-defined transformation
       - projection into feasible domain (boundaries)
       - assign fixed variables their original phenotypic value

    By default all transformations are the identity. The boundary
    transformation is only applied, if the boundaries are given as argument to
    the method `pheno` or `geno` respectively.

    ``geno`` is not really necessary and might disappear in future.

    """
    def __init__(self, dim, scaling=None, typical_x=None, bounds=None, fixed_values=None, tf=None):
        """return `GenoPheno` instance with fixed dimension `dim`.

        Keyword Arguments
        -----------------
            `scaling`
                the diagonal of a scaling transformation matrix, multipliers
                in the genotyp-phenotyp transformation, see `typical_x`
            `typical_x`
                ``pheno = scaling*geno + typical_x``
            `bounds` (obsolete, might disappear)
                list with two elements,
                lower and upper bounds both can be a scalar or a "vector"
                of length dim or `None`. Without effect, as `bounds` must
                be given as argument to `pheno()`.
            `fixed_values`
                a dictionary of variable indices and values, like ``{0:2.0, 2:1.1}``,
                that are not subject to change, negative indices are ignored
                (they act like incommenting the index), values are phenotypic
                values.
            `tf`
                list of two user-defined transformation functions, or `None`.

                ``tf[0]`` is a function that transforms the internal representation
                as used by the optimizer into a solution as used by the
                objective function. ``tf[1]`` does the back-transformation.
                For example ::

                    tf_0 = lambda x: [xi**2 for xi in x]
                    tf_1 = lambda x: [abs(xi)**0.5 fox xi in x]

                or "equivalently" without the `lambda` construct ::

                    def tf_0(x):
                        return [xi**2 for xi in x]
                    def tf_1(x):
                        return [abs(xi)**0.5 fox xi in x]

                ``tf=[tf_0, tf_1]`` is a reasonable way to guaranty that only positive
                values are used in the objective function.

        Details
        -------
        If ``tf_1`` is ommitted, the initial x-value must be given as genotype (as the
        phenotype-genotype transformation is unknown) and injection of solutions
        might lead to unexpected results.

        """
        self.N = dim
        self.bounds = bounds
        self.fixed_values = fixed_values
        if tf is not None:
            self.tf_pheno = tf[0]
            self.tf_geno = tf[1]  # TODO: should not necessarily be needed
            # r = np.random.randn(dim)
            # assert all(tf[0](tf[1](r)) - r < 1e-7)
            # r = np.random.randn(dim)
            # assert all(tf[0](tf[1](r)) - r > -1e-7)
            print("WARNING in class GenoPheno: user defined transformations have not been tested thoroughly")
        else:
            self.tf_geno = None
            self.tf_pheno = None

        if fixed_values:
            if type(fixed_values) is not dict:
                raise _Error("fixed_values must be a dictionary {index:value,...}")
            if max(fixed_values.keys()) >= dim:
                raise _Error("max(fixed_values.keys()) = " + str(max(fixed_values.keys())) +
                    " >= dim=N=" + str(dim) + " is not a feasible index")
            # convenience commenting functionality: drop negative keys
            for k in list(fixed_values.keys()):
                if k < 0:
                    fixed_values.pop(k)
        if bounds:
            if len(bounds) != 2:
                raise _Error('len(bounds) must be 2 for lower and upper bounds')
            for i in (0,1):
                if bounds[i] is not None:
                    bounds[i] = array(dim * [bounds[i]] if np.isscalar(bounds[i]) else
                                        [b for b in bounds[i]])

        def vec_is_default(vec, default_val=0):
            """return True if `vec` has the value `default_val`,
            None or [None] are also recognized as default"""
            try:
                if len(vec) == 1:
                    vec = vec[0]  # [None] becomes None and is always default
                else:
                    return False
            except TypeError:
                pass  # vec is a scalar

            if vec is None or vec == array(None) or vec == default_val:
                return True
            return False

        self.scales = array(scaling)
        if vec_is_default(self.scales, 1):
            self.scales = 1  # CAVE: 1 is not array(1)
        elif self.scales.shape is not () and len(self.scales) != self.N:
            raise _Error('len(scales) == ' + str(len(self.scales)) +
                         ' does not match dimension N == ' + str(self.N))

        self.typical_x = array(typical_x)
        if vec_is_default(self.typical_x, 0):
            self.typical_x = 0
        elif self.typical_x.shape is not () and len(self.typical_x) != self.N:
            raise _Error('len(typical_x) == ' + str(len(self.typical_x)) +
                         ' does not match dimension N == ' + str(self.N))

        if (self.scales is 1 and
                self.typical_x is 0 and
                self.bounds in (None, [None, None]) and
                self.fixed_values is None and
                self.tf_pheno is None):
            self.isidentity = True
        else:
            self.isidentity = False

    def into_bounds(self, y, bounds=None, copy_never=False, copy_always=False):
        """Argument `y` is a phenotypic vector,
        return `y` put into boundaries, as a copy iff ``y != into_bounds(y)``.

        Note: this code is duplicated in `Solution.repair` and might
        disappear in future.

        """
        bounds = bounds if bounds is not None else self.bounds
        if bounds in (None, [None, None]):
            return y if not copy_always else array(y, copy=True)
        if bounds[0] is not None:
            if len(bounds[0]) not in (1, len(y)):
                raise ValueError('len(bounds[0]) = ' + str(len(bounds[0])) +
                                 ' and len of initial solution (' + str(len(y)) + ') disagree')
            if copy_never:  # is rather slower
                for i in xrange(len(y)):
                    y[i] = max(bounds[0][i], y[i])
            else:
                y = np.max([bounds[0], y], axis=0)
        if bounds[1] is not None:
            if len(bounds[1]) not in (1, len(y)):
                raise ValueError('len(bounds[1]) = ' + str(len(bounds[1])) +
                                    ' and initial solution (' + str(len(y)) + ') disagree')
            if copy_never:
                for i in xrange(len(y)):
                    y[i] = min(bounds[1][i], y[i])
            else:
                y = np.min([bounds[1], y], axis=0)
        return y

    def pheno(self, x, bounds=None, copy=True, copy_always=False):
        """maps the genotypic input argument into the phenotypic space,
        boundaries are only applied if argument ``bounds is not None``, see
        help for class `GenoPheno`

        """
        if copy_always and not copy:
            raise ValueError('arguments copy_always=' + str(copy_always) +
                             ' and copy=' + str(copy) + ' have inconsistent values')
        if self.isidentity and bounds in (None, [None, None], (None, None)):
            return x if not copy_always else array(x, copy=copy_always)

        if self.fixed_values is None:
            y = array(x, copy=copy)  # make a copy, in case
        else:  # expand with fixed values
            y = list(x)  # is a copy
            for i in sorted(self.fixed_values.keys()):
                y.insert(i, self.fixed_values[i])
            y = array(y, copy=False)

        if self.scales is not 1:  # just for efficiency
            y *= self.scales

        if self.typical_x is not 0:
            y += self.typical_x

        if self.tf_pheno is not None:
            y = array(self.tf_pheno(y), copy=False)

        if bounds is not None:
            y = self.into_bounds(y, bounds)

        if self.fixed_values is not None:
            for i, k in list(self.fixed_values.items()):
                y[i] = k

        return y

    def geno(self, y, bounds=None, copy=True, copy_always=False, archive=None):
        """maps the phenotypic input argument into the genotypic space.
        If `bounds` are given, first `y` is projected into the feasible
        domain. In this case ``copy==False`` leads to a copy.

        by default a copy is made only to prevent to modify ``y``

        method geno is only needed if external solutions are injected
        (geno(initial_solution) is depreciated and will disappear)

        TODO: arg copy=True should become copy_never=False

        """
        if archive is not None and bounds is not None:
            try:
                return archive[y]['geno']
            except:
                pass

        x = array(y, copy=(copy and not self.isidentity) or copy_always)

        # bounds = self.bounds if bounds is None else bounds
        if bounds is not None:  # map phenotyp into bounds first
            x = self.into_bounds(x, bounds)

        if self.isidentity:
            return x

        # user-defined transformation
        if self.tf_geno is not None:
            x = array(self.tf_geno(x), copy=False)
        else:
            _Error('t1 of options transformation was not defined but is needed as being the inverse of t0')

        # affine-linear transformation: shift and scaling
        if self.typical_x is not 0:
            x -= self.typical_x
        if self.scales is not 1:  # just for efficiency
            x /= self.scales

        # kick out fixed_values
        if self.fixed_values is not None:
            # keeping the transformed values does not help much
            # therefore it is omitted
            if 1 < 3:
                keys = sorted(self.fixed_values.keys())
                x = array([x[i] for i in range(len(x)) if i not in keys], copy=False)
            else:  # TODO: is this more efficient?
                x = list(x)
                for key in sorted(list(self.fixed_values.keys()), reverse=True):
                    x.remove(key)
                x = array(x, copy=False)
        return x
#____________________________________________________________
#____________________________________________________________
# check out built-in package abc: class ABCMeta, abstractmethod, abstractproperty...
# see http://docs.python.org/whatsnew/2.6.html PEP 3119 abstract base classes
#
class OOOptimizer(object):
    """"abstract" base class for an OO optimizer interface with methods
    `__init__`, `ask`, `tell`, `stop`, `result`, and `optimize`. Only
    `optimize` is fully implemented in this base class.

    Examples
    --------
    All examples minimize the function `elli`, the output is not shown.
    (A preferred environment to execute all examples is ``ipython -pylab``.)
    First we need ::

        from cma import CMAEvolutionStrategy, CMADataLogger  # CMAEvolutionStrategy derives from the OOOptimizer class
        elli = lambda x: sum(1e3**((i-1.)/(len(x)-1.)*x[i])**2 for i in range(len(x)))

    The shortest example uses the inherited method `OOOptimizer.optimize()`::

        res = CMAEvolutionStrategy(8 * [0.1], 0.5).optimize(elli)

    The input parameters to `CMAEvolutionStrategy` are specific to this
    inherited class. The remaining functionality is based on interface
    defined by `OOOptimizer`. We might have a look at the result::

        print(res[0])  # best solution and
        print(res[1])  # its function value

    `res` is the return value from method
    `CMAEvolutionStrategy.result()` appended with `None` (no logger).
    In order to display more exciting output we rather do ::

        logger = CMADataLogger()  # derives from the abstract BaseDataLogger class
        res = CMAEvolutionStrategy(9 * [0.5], 0.3).optimize(elli, logger)
        logger.plot()  # if matplotlib is available, logger == res[-1]

    or even shorter ::

        res = CMAEvolutionStrategy(9 * [0.5], 0.3).optimize(elli, CMADataLogger())
        res[-1].plot()  # if matplotlib is available

    Virtually the same example can be written with an explicit loop
    instead of using `optimize()`. This gives the necessary insight into
    the `OOOptimizer` class interface and gives entire control over the
    iteration loop::

        optim = CMAEvolutionStrategy(9 * [0.5], 0.3)  # a new CMAEvolutionStrategy instance calling CMAEvolutionStrategy.__init__()
        logger = CMADataLogger(optim)  # get a logger instance

        # this loop resembles optimize()
        while not optim.stop(): # iterate
            X = optim.ask()     # get candidate solutions
            f = [elli(x) for x in X]  # evaluate solutions
            #  maybe do something else that needs to be done
            optim.tell(X, f)    # do all the real work: prepare for next iteration
            optim.disp(20)      # display info every 20th iteration
            logger.add()        # log another "data line"

        # final output
        print('termination by', optim.stop())
        print('best f-value =', optim.result()[1])
        print('best solution =', optim.result()[0])
        logger.plot()  # if matplotlib is available
        raw_input('press enter to continue')  # prevents exiting and closing figures

    Details
    -------
    Most of the work is done in the method `tell(...)`. The method `result()` returns
    more useful output.

    """
    def __init__(self, xstart, **more_args):
        """``xstart`` is a mandatory argument"""
        self.xstart = xstart
        self.more_args = more_args
        self.initialize()
    def initialize(self):
        """(re-)set to the initial state"""
        self.countiter = 0
        self.xcurrent = self.xstart[:]
        raise NotImplementedError('method initialize() must be implemented in derived class')
    def ask(self):
        """abstract method, AKA "get" or "sample_distribution", deliver new candidate solution(s), a list of "vectors"
        """
        raise NotImplementedError('method ask() must be implemented in derived class')
    def tell(self, solutions, function_values):
        """abstract method, AKA "update", prepare for next iteration"""
        self.countiter += 1
        raise NotImplementedError('method tell() must be implemented in derived class')
    def stop(self):
        """abstract method, return satisfied termination conditions in a dictionary like
        ``{'termination reason': value, ...}``, for example ``{'tolfun': 1e-12}``, or the empty
        dictionary ``{}``. The implementation of `stop()` should prevent an infinite loop.
        """
        raise NotImplementedError('method stop() is not implemented')
    def disp(self, modulo=None):
        """abstract method, display some iteration infos if ``self.iteration_counter % modulo == 0``"""
        raise NotImplementedError('method disp() is not implemented')
    def result(self):
        """abstract method, return ``(x, f(x), ...)``, that is, the minimizer, its function value, ..."""
        raise NotImplementedError('method result() is not implemented')

    def optimize(self, objectivefct, logger=None, verb_disp=20, iterations=None):
        """find minimizer of `objectivefct` by iterating over `OOOptimizer` `self`
        with verbosity `verb_disp`, using `BaseDataLogger` `logger` with at
        most `iterations` iterations. ::

            return self.result() + (self.stop(), self, logger)

        Example
        -------
        >>> import cma
        >>> res = cma.CMAEvolutionStrategy(7 * [0.1], 0.5).optimize(cma.fcts.rosen, cma.CMADataLogger(), 100)
        (4_w,9)-CMA-ES (mu_w=2.8,w_1=49%) in dimension 7 (seed=630721393)
        Iterat #Fevals   function value     axis ratio  sigma   minstd maxstd min:sec
            1       9 3.163954777181882e+01 1.0e+00 4.12e-01  4e-01  4e-01 0:0.0
            2      18 3.299006223906629e+01 1.0e+00 3.60e-01  3e-01  4e-01 0:0.0
            3      27 1.389129389866704e+01 1.1e+00 3.18e-01  3e-01  3e-01 0:0.0
          100     900 2.494847340045985e+00 8.6e+00 5.03e-02  2e-02  5e-02 0:0.3
          200    1800 3.428234862999135e-01 1.7e+01 3.77e-02  6e-03  3e-02 0:0.5
          300    2700 3.216640032470860e-04 5.6e+01 6.62e-03  4e-04  9e-03 0:0.8
          400    3600 6.155215286199821e-12 6.6e+01 7.44e-06  1e-07  4e-06 0:1.1
          438    3942 1.187372505161762e-14 6.0e+01 3.27e-07  4e-09  9e-08 0:1.2
          438    3942 1.187372505161762e-14 6.0e+01 3.27e-07  4e-09  9e-08 0:1.2
        ('termination by', {'tolfun': 1e-11})
        ('best f-value =', 1.1189867885201275e-14)
        ('solution =', array([ 1.        ,  1.        ,  1.        ,  0.99999999,  0.99999998,
                0.99999996,  0.99999992]))
        >>> print(res[0])
        [ 1.          1.          1.          0.99999999  0.99999998  0.99999996
          0.99999992]

        """
        if logger is None:
            if hasattr(self, 'logger'):
                logger = self.logger

        citer = 0
        while not self.stop():
            if iterations is not None and citer >= iterations:
                return self.result()
            citer += 1

            X = self.ask()         # deliver candidate solutions
            fitvals = [objectivefct(x) for x in X]
            self.tell(X, fitvals)  # all the work is done here

            self.disp(verb_disp)
            logger.add(self) if logger else None

        logger.add(self, modulo=bool(logger.modulo)) if logger else None
        if verb_disp:
            self.disp(1)
        if verb_disp in (1, True):
            print('termination by', self.stop())
            print('best f-value =', self.result()[1])
            print('solution =', self.result()[0])

        return self.result() + (self.stop(), self, logger)

#____________________________________________________________
#____________________________________________________________
#
class CMAEvolutionStrategy(OOOptimizer):
    """CMA-ES stochastic optimizer class with ask-and-tell interface.

    See `fmin` for the one-line-call functional interface.

    Calling sequence
    ================
    ``optim = CMAEvolutionStrategy(x0, sigma0, opts)``
    returns a class instance.

    Arguments
    ---------
        `x0`
            initial solution, starting point (phenotype).
        `sigma0`
            initial standard deviation.  The problem
            variables should have been scaled, such that a single
            standard deviation on all variables is useful and the
            optimum is expected to lie within about `x0` +- ``3*sigma0``.
            See also options `scaling_of_variables`.
            Often one wants to check for solutions close to the initial
            point. This allows for an easier check for consistency of
            the objective function and its interfacing with the optimizer.
            In this case, a much smaller `sigma0` is advisable.
        `opts`
            options, a dictionary with optional settings,
            see class `Options`.

    Main interface / usage
    ======================
    The ask-and-tell interface is inherited from the generic `OOOptimizer`
    interface for iterative optimization algorithms (see there). With ::

        optim = CMAEvolutionStrategy(8 * [0.5], 0.2)

    an object instance is generated. In each iteration ::

        solutions = optim.ask()

    is used to ask for new candidate solutions (possibly several times) and ::

        optim.tell(solutions, func_values)

    passes the respective function values to `optim`. Instead of `ask()`,
    the class `CMAEvolutionStrategy` also provides ::

        (solutions, func_values) = optim.ask_and_eval(objective_func)

    Therefore, after initialization, an entire optimization can be written
    in two lines like ::

        while not optim.stop():
            optim.tell(*optim.ask_and_eval(objective_func))

    Without the freedom of executing additional lines within the iteration,
    the same reads in a single line as ::

        optim.optimize(objective_func)

    Besides for termination criteria, in CMA-ES only
    the ranks of the `func_values` are relevant.

    Attributes and Properties
    =========================
        - `inputargs` -- passed input arguments
        - `inopts` -- passed options
        - `opts` -- actually used options, some of them can be changed any
          time, see class `Options`
        - `popsize` -- population size lambda, number of candidate solutions
          returned by `ask()`

    Details
    =======
    The following two enhancements are turned off by default.

    **Active CMA** is implemented with option ``CMA_active`` and conducts
    an update of the covariance matrix with negative weights. The
    exponential update is implemented, where from a mathematical
    viewpoint positive definiteness is guarantied. The update is applied
    after the default update and only before the covariance matrix is
    decomposed, which limits the additional computational burden to be
    at most a factor of three (typically smaller). A typical speed up
    factor (number of f-evaluations) is between 1.1 and two.

    References: Jastrebski and Arnold, CEC 2006, Glasmachers et al, GECCO 2010.

    **Selective mirroring** is implemented with option ``CMA_mirrors`` in
    the method ``get_mirror()``. Only the method `ask_and_eval()` will
    then sample selectively mirrored vectors. In selective mirroring, only
    the worst solutions are mirrored. With the default small number of mirrors,
    *pairwise selection* (where at most one of the two mirrors contribute to the
    update of the distribution mean) is implicitely guarantied under selective
    mirroring and therefore not explicitly implemented.

    References: Brockhoff et al, PPSN 2010, Auger et al, GECCO 2011.

    Examples
    ========
    Super-short example, with output shown:

    >>> import cma
    >>> # construct an object instance in 4-D, sigma0=1
    >>> es = cma.CMAEvolutionStrategy(4 * [1], 1, {'seed':234})
    (4_w,8)-CMA-ES (mu_w=2.6,w_1=52%) in dimension 4 (seed=234)
    >>>
    >>> # iterate until termination
    >>> while not es.stop():
    ...    X = es.ask()
    ...    es.tell(X, [cma.fcts.elli(x) for x in X])
    ...    es.disp()  # by default sparse, see option verb_disp
    Iterat #Fevals   function value     axis ratio  sigma   minstd maxstd min:sec
        1       8 2.093015112685775e+04 1.0e+00 9.27e-01  9e-01  9e-01 0:0.0
        2      16 4.964814235917688e+04 1.1e+00 9.54e-01  9e-01  1e+00 0:0.0
        3      24 2.876682459926845e+05 1.2e+00 1.02e+00  9e-01  1e+00 0:0.0
      100     800 6.809045875281943e-01 1.3e+02 1.41e-02  1e-04  1e-02 0:0.2
      200    1600 2.473662150861846e-10 8.0e+02 3.08e-05  1e-08  8e-06 0:0.5
      233    1864 2.766344961865341e-14 8.6e+02 7.99e-07  8e-11  7e-08 0:0.6
    >>>
    >>> cma.pprint(es.result())
    (Solution([ -1.98546755e-09,  -1.10214235e-09,   6.43822409e-11,
            -1.68621326e-11]),
     4.5119610261406537e-16,
     1666,
     1672,
     209,
     array([ -9.13545269e-09,  -1.45520541e-09,  -6.47755631e-11,
            -1.00643523e-11]),
     array([  3.20258681e-08,   3.15614974e-09,   2.75282215e-10,
             3.27482983e-11]))
    >>>
    >>> # help(es.result) shows
    result(self) method of cma.CMAEvolutionStrategy instance
       return ``(xbest, f(xbest), evaluations_xbest, evaluations, iterations, pheno(xmean), effective_stds)``

    Using the multiprocessing module, we can evaluate the function in parallel with a simple
    modification of the example ::

        import multiprocessing
        # prepare es = ...
        pool = multiprocessing.Pool(es.popsize)
        while not es.stop():
            X = es.ask()
            es.tell(X, pool.map_async(cma.felli, X).get()) # use chunksize parameter as popsize/len(pool)?

    Example with a data logger, lower bounds (at zero) and handling infeasible solutions:

    >>> import cma
    >>> import numpy as np
    >>> es = cma.CMAEvolutionStrategy(10 * [0.2], 0.5, {'bounds': [0, np.inf]})
    >>> logger = cma.CMADataLogger().register(es)
    >>> while not es.stop():
    ...     fit, X = [], []
    ...     while len(X) < es.popsize:
    ...         curr_fit = np.NaN
    ...         while curr_fit is np.NaN:
    ...             x = es.ask(1)[0]
    ...             curr_fit = cma.fcts.somenan(x, cma.fcts.elli) # might return np.NaN
    ...         X.append(x)
    ...         fit.append(curr_fit)
    ...     es.tell(X, fit)
    ...     logger.add()
    ...     es.disp()
    <output omitted>
    >>>
    >>> assert es.result()[1] < 1e-9
    >>> assert es.result()[2] < 9000  # by internal termination
    >>> logger.plot()  # plot data
    >>> cma.show()
    >>> print('  *** if execution stalls close the figure window to continue (and check out ipython --pylab) ***')

    Example implementing restarts with increasing popsize (IPOP), output is not displayed:

    >>> import cma, numpy as np
    >>>
    >>> # restart with increasing population size (IPOP)
    >>> bestever = cma.BestSolution()
    >>> for lam in 10 * 2**np.arange(7):  # 10, 20, 40, 80, ..., 10 * 2**6
    ...     es = cma.CMAEvolutionStrategy('6 - 8 * np.random.rand(9)',  # 9-D
    ...                                   5,         # initial std sigma0
    ...                                   {'popsize': lam,
    ...                                    'verb_append': bestever.evalsall})   # pass options
    ...     logger = cma.CMADataLogger().register(es, append=bestever.evalsall)
    ...     while not es.stop():
    ...         X = es.ask()    # get list of new solutions
    ...         fit = [cma.fcts.rastrigin(x) for x in X]  # evaluate each solution
    ...         es.tell(X, fit) # besides for termination only the ranking in fit is used
    ...
    ...         # display some output
    ...         logger.add()  # add a "data point" to the log, writing in files
    ...         es.disp()  # uses option verb_disp with default 100
    ...
    ...     print('termination:', es.stop())
    ...     cma.pprint(es.best.__dict__)
    ...
    ...     bestever.update(es.best)
    ...
    ...     # show a plot
    ...     logger.plot();
    ...     if bestever.f < 1e-8:  # global optimum was hit
    ...         break
    <output omitted>
    >>> assert es.result()[1] < 1e-8

    On the Rastrigin function, usually after five restarts the global optimum
    is located.

    The final example shows how to resume:

    >>> import cma, pickle
    >>>
    >>> es = cma.CMAEvolutionStrategy(12 * [0.1],  # a new instance, 12-D
    ...                               0.5)         # initial std sigma0
    >>> logger = cma.CMADataLogger().register(es)
    >>> es.optimize(cma.fcts.rosen, logger, iterations=100)
    >>> logger.plot()
    >>> pickle.dump(es, open('saved-cma-object.pkl', 'wb'))
    >>> print('saved')
    >>> del es, logger  # let's start fresh
    >>>
    >>> es = pickle.load(open('saved-cma-object.pkl', 'rb'))
    >>> print('resumed')
    >>> logger = cma.CMADataLogger(es.opts['verb_filenameprefix']  # use same name
    ...                           ).register(es, True)  # True: append to old log data
    >>> es.optimize(cma.fcts.rosen, logger, verb_disp=200)
    >>> assert es.result()[2] < 15000
    >>> cma.pprint(es.result())
    >>> logger.plot()

    Missing Features
    ================
    Option ``randn`` to pass a random number generator.

    :See: `fmin()`, `Options`, `plot()`, `ask()`, `tell()`, `ask_and_eval()`

    """

    # __all__ = ()  # TODO this would be the interface

    #____________________________________________________________
    @property  # read only attribute decorator for a method
    def popsize(self):
        """number of samples by default returned by` ask()`
        """
        return self.sp.popsize

    # this is not compatible with python2.5:
    #     @popsize.setter
    #     def popsize(self, p):
    #         """popsize cannot be set (this might change in future)
    #         """
    #         raise _Error("popsize cannot be changed (this might change in future)")

    #____________________________________________________________
    #____________________________________________________________
    def stop(self, check=True):
        """return a dictionary with the termination status.
        With ``check==False``, the termination conditions are not checked and
        the status might not reflect the current situation.
        """

        if (check and self.countiter > 0 and self.opts['termination_callback'] and
                self.opts['termination_callback'] != str(self.opts['termination_callback'])):
            self.callbackstop = self.opts['termination_callback'](self)

        return self.stopdict(self if check else None)  # update the stopdict and return a Dict

    #____________________________________________________________
    #____________________________________________________________
    def __init__(self, x0, sigma0, inopts = {}):
        """see class `CMAEvolutionStrategy`

        """
        self.inputargs = dict(locals()) # for the record
        del self.inputargs['self'] # otherwise the instance self has a cyclic reference
        self.inopts = inopts
        opts = Options(inopts).complement()  # Options() == fmin([],[]) == defaultOptions()

        if opts['noise_handling'] and eval(opts['noise_handling']):
            raise ValueError('noise_handling not available with class CMAEvolutionStrategy, use function fmin')
        if opts['restarts'] and eval(opts['restarts']):
            raise ValueError('restarts not available with class CMAEvolutionStrategy, use function fmin')

        if x0 == str(x0):
            x0 = eval(x0)
        self.mean = array(x0)  # should not have column or row, is just 1-D
        if self.mean.ndim == 2:
            print('WARNING: input x0 should be a list or 1-D array, trying to flatten ' +
                    str(self.mean.shape) + '-array')
            if self.mean.shape[0] == 1:
                self.mean = self.mean[0]
            elif self.mean.shape[1] == 1:
                self.mean = array([x[0] for x in self.mean])
        if self.mean.ndim != 1:
            raise _Error('x0 must be 1-D array')
        if len(self.mean) <= 1:
            raise _Error('optimization in 1-D is not supported (code was never tested)')

        self.N = self.mean.shape[0]
        N = self.N
        self.mean.resize(N) # 1-D array, not really necessary?!
        self.x0 = self.mean
        self.mean = self.x0.copy()  # goes to initialize

        self.sigma0 = sigma0
        if isinstance(sigma0, str):  # TODO: no real need here (do rather in fmin)
            self.sigma0 = eval(sigma0)  # like '1./N' or 'np.random.rand(1)[0]+1e-2'
        if np.size(self.sigma0) != 1 or np.shape(self.sigma0):
            raise _Error('input argument sigma0 must be (or evaluate to) a scalar')
        self.sigma = self.sigma0  # goes to inialize

        # extract/expand options
        opts.evalall(locals())  # using only N
        self.opts = opts

        self.randn = opts['randn']
        self.gp = GenoPheno(N, opts['scaling_of_variables'], opts['typical_x'],
            opts['bounds'], opts['fixed_variables'], opts['transformation'])
        self.boundPenalty = BoundPenalty(self.gp.bounds)
        s = self.gp.geno(self.mean)
        self.mean = self.gp.geno(self.mean, bounds=self.gp.bounds)
        self.N = len(self.mean)
        N = self.N
        if (self.mean != s).any():
            print('WARNING: initial solution is out of the domain boundaries:')
            print('  x0   = ' + str(self.inputargs['x0']))
            print('  ldom = ' + str(self.gp.bounds[0]))
            print('  udom = ' + str(self.gp.bounds[1]))
        self.fmean = np.NaN             # TODO name should change? prints nan (OK with matlab&octave)
        self.fmean_noise_free = 0.  # for output only

        self.sp = CMAParameters(N, opts)
        self.sp0 = self.sp  # looks useless, as it is not a copy

        # initialization of state variables
        self.countiter = 0
        self.countevals = max((0, opts['verb_append'])) if type(opts['verb_append']) is not bool else 0
        self.ps = np.zeros(N)
        self.pc = np.zeros(N)

        stds = np.ones(N)
        self.sigma_vec = np.ones(N) if np.isfinite(self.sp.dampsvec) else 1
        if np.all(self.opts['CMA_teststds']):  # also 0 would not make sense
            stds = self.opts['CMA_teststds']
            if np.size(stds) != N:
                raise _Error('CMA_teststds option must have dimension = ' + str(N))
        if self.opts['CMA_diagonal']:  # is True or > 0
            # linear time and space complexity
            self.B = array(1) # works fine with np.dot(self.B, anything) and self.B.T
            self.C = stds**2  # TODO: remove this!?
            self.dC = self.C
        else:
            self.B = np.eye(N) # identity(N), do not from matlib import *, as eye is a matrix there
            # prevent equal eigenvals, a hack for np.linalg:
            self.C = np.diag(stds**2 * exp(1e-6*(np.random.rand(N)-0.5)))
            self.dC = np.diag(self.C)
            self.Zneg = np.zeros((N, N))
        self.D = stds

        self.flgtelldone = True
        self.itereigenupdated = self.countiter
        self.noiseS = 0  # noise "signal"
        self.hsiglist = []

        if not opts['seed']:
            np.random.seed()
            six_decimals = (time.time() - 1e6 * (time.time() // 1e6))
            opts['seed'] = 1e5 * np.random.rand() + six_decimals + 1e5 * (time.time() % 1)
        opts['seed'] = int(opts['seed'])
        np.random.seed(opts['seed'])

        self.sent_solutions = SolutionDict()
        self.best = BestSolution()

        out = {}  # TODO: obsolete, replaced by method results()?
        out['best'] = self.best
        # out['hsigcount'] = 0
        out['termination'] = {}
        self.out = out

        self.const = BlancClass()
        self.const.chiN = N**0.5*(1-1./(4.*N)+1./(21.*N**2)) # expectation of norm(randn(N,1))

        # attribute for stopping criteria in function stop
        self.stopdict = CMAStopDict()
        self.callbackstop = 0

        self.fit = BlancClass()
        self.fit.fit = []   # not really necessary
        self.fit.hist = []  # short history of best
        self.fit.histbest = []   # long history of best
        self.fit.histmedian = [] # long history of median

        self.more_to_write = []  #[1, 1, 1, 1]  #  N*[1]  # needed when writing takes place before setting

        # say hello
        if opts['verb_disp'] > 0:
            sweighted = '_w' if self.sp.mu > 1 else ''
            smirr = 'mirr%d' % (self.sp.lam_mirr) if self.sp.lam_mirr else ''
            print('(%d' % (self.sp.mu) + sweighted + ',%d' % (self.sp.popsize) + smirr + ')-CMA-ES' +
                  ' (mu_w=%2.1f,w_1=%d%%)' % (self.sp.mueff, int(100*self.sp.weights[0])) +
                  ' in dimension %d (seed=%d, %s)' % (N, opts['seed'], time.asctime())) # + func.__name__
            if opts['CMA_diagonal'] and self.sp.CMA_on:
                s = ''
                if opts['CMA_diagonal'] is not True:
                    s = ' for '
                    if opts['CMA_diagonal'] < np.inf:
                        s += str(int(opts['CMA_diagonal']))
                    else:
                        s += str(np.floor(opts['CMA_diagonal']))
                    s += ' iterations'
                    s += ' (1/ccov=' + str(round(1./(self.sp.c1+self.sp.cmu))) + ')'
                print('   Covariance matrix is diagonal' + s)

    #____________________________________________________________
    #____________________________________________________________
    def ask(self, number=None, xmean=None, sigma_fac=1):
        """get new candidate solutions, sampled from a multi-variate
        normal distribution and transformed to f-representation
        (phenotype) to be evaluated.

        Arguments
        ---------
            `number`
                number of returned solutions, by default the
                population size ``popsize`` (AKA ``lambda``).
            `xmean`
                distribution mean
            `sigma`
                multiplier for internal sample width (standard
                deviation)

        Return
        ------
        A list of N-dimensional candidate solutions to be evaluated

        Example
        -------
        >>> import cma
        >>> es = cma.CMAEvolutionStrategy([0,0,0,0], 0.3)
        >>> while not es.stop() and es.best.f > 1e-6:  # my_desired_target_f_value
        ...     X = es.ask()  # get list of new solutions
        ...     fit = [cma.fcts.rosen(x) for x in X]  # call function rosen with each solution
        ...     es.tell(X, fit)  # feed values

        :See: `ask_and_eval`, `ask_geno`, `tell`

        """
        pop_geno = self.ask_geno(number, xmean, sigma_fac)


        # N,lambda=20,200: overall CPU 7s vs 5s == 40% overhead, even without bounds!
        #                  new data: 11.5s vs 9.5s == 20%
        # TODO: check here, whether this is necessary?
        # return [self.gp.pheno(x, copy=False, bounds=self.gp.bounds) for x in pop]  # probably fine
        # return [Solution(self.gp.pheno(x, copy=False), copy=False) for x in pop]  # here comes the memory leak, now solved
        # pop_pheno = [Solution(self.gp.pheno(x, copy=False), copy=False).repair(self.gp.bounds) for x in pop_geno]
        pop_pheno = [self.gp.pheno(x, copy=True, bounds=self.gp.bounds) for x in pop_geno]

        if not self.gp.isidentity or use_sent_solutions:  # costs 25% in CPU performance with N,lambda=20,200
            # archive returned solutions, first clean up archive
            if self.countiter % 30/self.popsize**0.5 < 1:
                self.sent_solutions.truncate(0, self.countiter - 1 - 3 * self.N/self.popsize**0.5)
            # insert solutions
            for i in xrange(len(pop_geno)):
                self.sent_solutions[pop_pheno[i]] = {'geno': pop_geno[i],
                                            'pheno': pop_pheno[i],
                                            'iteration': self.countiter}
        return pop_pheno

    #____________________________________________________________
    #____________________________________________________________
    def ask_geno(self, number=None, xmean=None, sigma_fac=1):
        """get new candidate solutions in genotyp, sampled from a
        multi-variate normal distribution.

        Arguments are
            `number`
                number of returned solutions, by default the
                population size `popsize` (AKA lambda).
            `xmean`
                distribution mean
            `sigma_fac`
                multiplier for internal sample width (standard
                deviation)

        `ask_geno` returns a list of N-dimensional candidate solutions
        in genotyp representation and is called by `ask`.

        :See: `ask`, `ask_and_eval`

        """

        if number is None or number < 1:
            number = self.sp.popsize
        if xmean is None:
            xmean = self.mean

        if self.countiter == 0:
            self.tic = time.clock()  # backward compatible
            self.elapsed_time = ElapsedTime()

        if self.opts['CMA_AII']:
            if self.countiter == 0:
                self.aii = AII(self.x0, self.sigma0)
            self.flgtelldone = False
            pop = self.aii.ask(number)
            return pop

        sigma = sigma_fac * self.sigma

        # update parameters for sampling the distribution
        #        fac  0      1      10
        # 150-D cigar:
        #           50749  50464   50787
        # 200-D elli:               == 6.9
        #                  99900   101160
        #                 100995   103275 == 2% loss
        # 100-D elli:               == 6.9
        #                 363052   369325  < 2% loss
        #                 365075   365755

        # update distribution
        if self.sp.CMA_on and (
                (self.opts['updatecovwait'] is None and
                 self.countiter >=
                     self.itereigenupdated + 1./(self.sp.c1+self.sp.cmu)/self.N/10
                 ) or
                (self.opts['updatecovwait'] is not None and
                 self.countiter > self.itereigenupdated + self.opts['updatecovwait']
                 )):
            self.updateBD()

        # sample distribution
        if self.flgtelldone:  # could be done in tell()!?
            self.flgtelldone = False
            self.ary = []

        # each row is a solution
        arz = self.randn((number, self.N))
        if 11 < 3:  # mutate along the principal axes only
            perm = np.random.permutation(self.N) # indices for mutated principal component
            for i in xrange(min((len(arz), self.N))):
                # perm = np.random.permutation(self.N)  # random principal component, should be much worse
                l = sum(arz[i]**2)**0.5
                arz[i] *= 0
                if 11 < 3: # mirrored sampling
                    arz[i][perm[int(i/2)]] = l * (2 * (i % 2) - 1)
                else:
                    arz[i][perm[i % self.N]] = l * np.sign(np.random.rand(1) - 0.5)
        if number == self.sp.popsize:
            self.arz = arz  # is never used
        else:
            pass

        if 11 < 3:  # normalize the length to chiN
            for i in xrange(len(arz)):
                # arz[i] *= exp(self.randn(1)[0] / 8)
                ss = sum(arz[i]**2)**0.5
                arz[i] *= self.const.chiN / ss
            # or to average
            # arz *= 1 * self.const.chiN / np.mean([sum(z**2)**0.5 for z in arz])

        # fac = np.mean(sum(arz**2, 1)**0.5)
        # print fac
        # arz *= self.const.chiN / fac
        self.ary = self.sigma_vec * np.dot(self.B, (self.D * arz).T).T
        pop = xmean + sigma * self.ary
        self.evaluations_per_f_value = 1

        return pop

    def get_mirror(self, x):
        """return ``pheno(self.mean - (geno(x) - self.mean))``.

        TODO: this implementation is yet experimental.

        Selectively mirrored sampling improves to a moderate extend but
        overadditively with active CMA for quite understandable reasons.

        Optimal number of mirrors are suprisingly small: 1,2,3 for maxlam=7,13,20
        however note that 3,6,10 are the respective maximal possible mirrors that
        must be clearly suboptimal.

        """
        try:
            # dx = x.geno - self.mean, repair or boundary handling is not taken into account
            dx = self.sent_solutions[x]['geno'] - self.mean
        except:
            print('WARNING: use of geno is depreciated')
            dx = self.gp.geno(x, copy=True) - self.mean
        dx *= sum(self.randn(self.N)**2)**0.5 / self.mahalanobisNorm(dx)
        x = self.mean - dx
        y = self.gp.pheno(x, bounds=self.gp.bounds)
        if not self.gp.isidentity or use_sent_solutions:  # costs 25% in CPU performance with N,lambda=20,200
            self.sent_solutions[y] = {'geno': x,
                                        'pheno': y,
                                        'iteration': self.countiter}
        return y

    def mirror_penalized(self, f_values, idx):
        """obsolete and subject to removal (TODO),
        return modified f-values such that for each mirror one becomes worst.

        This function is useless when selective mirroring is applied with no
        more than (lambda-mu)/2 solutions.

        Mirrors are leading and trailing values in ``f_values``.

        """
        assert len(f_values) >= 2 * len(idx)
        m = np.max(np.abs(f_values))
        for i in len(idx):
            if f_values[idx[i]] > f_values[-1-i]:
                f_values[idx[i]] += m
            else:
                f_values[-1-i] += m
        return f_values

    def mirror_idx_cov(self, f_values, idx1):  # will most likely be removed
        """obsolete and subject to removal (TODO),
        return indices for negative ("active") update of the covariance matrix
        assuming that ``f_values[idx1[i]]`` and ``f_values[-1-i]`` are
        the corresponding mirrored values

        computes the index of the worse solution sorted by the f-value of the
        better solution.

        TODO: when the actual mirror was rejected, it is better
        to return idx1 instead of idx2.

        Remark: this function might not be necessary at all: if the worst solution
        is the best mirrored, the covariance matrix updates cancel (cave: weights
        and learning rates), which seems what is desirable. If the mirror is bad,
        as strong negative update is made, again what is desirable.
        And the fitness--step-length correlation is in part addressed by
        using flat weights.

        """
        idx2 = np.arange(len(f_values) - 1, len(f_values) - 1 - len(idx1), -1)
        f = []
        for i in xrange(len(idx1)):
            f.append(min((f_values[idx1[i]], f_values[idx2[i]])))
            # idx.append(idx1[i] if f_values[idx1[i]] > f_values[idx2[i]] else idx2[i])
        return idx2[np.argsort(f)][-1::-1]

    #____________________________________________________________
    #____________________________________________________________
    #
    def ask_and_eval(self, func, args=(), number=None, xmean=None, sigma_fac=1,
                     evaluations=1, aggregation=np.median):
        """samples `number` solutions and evaluates them on `func`, where
        each solution `s` is resampled until ``func(s) not in (numpy.NaN, None)``.

        Arguments
        ---------
            `func`
                objective function
            `args`
                additional parameters for `func`
            `number`
                number of solutions to be sampled, by default
                population size ``popsize`` (AKA lambda)
            `xmean`
                mean for sampling the solutions, by default ``self.mean``.
            `sigma_fac`
                multiplier for sampling width, standard deviation, for example
                to get a small perturbation of solution `xmean`
            `evaluations`
                number of evaluations for each sampled solution
            `aggregation`
                function that aggregates `evaluations` values to
                as single value.

        Return
        ------
        ``(X, fit)``, where
            X -- list of solutions
            fit -- list of respective function values

        Details
        -------
        When ``func(x)`` returns `NaN` or `None` a new solution is sampled until
        ``func(x) not in (numpy.NaN, None)``.  The argument to `func` can be
        freely modified within `func`.

        Depending on the ``CMA_mirrors`` option, some solutions are not sampled
        independently but as mirrors of other bad solutions. This is a simple
        derandomization that can save 10-30% of the evaluations in particular
        with small populations, for example on the cigar function.

        Example
        -------
        >>> import cma
        >>> x0, sigma0 = 8*[10], 1  # 8-D
        >>> es = cma.CMAEvolutionStrategy(x0, sigma0)
        >>> while not es.stop():
        ...     X, fit = es.ask_and_eval(cma.fcts.elli)  # handles NaN with resampling
        ...     es.tell(X, fit)  # pass on fitness values
        ...     es.disp(20) # print every 20-th iteration
        >>> print('terminated on ' + str(es.stop()))
        <output omitted>

        A single iteration step can be expressed in one line, such that
        an entire optimization after initialization becomes
        ::

            while not es.stop():
                es.tell(*es.ask_and_eval(cma.fcts.elli))

        """
        # initialize
        popsize = self.sp.popsize
        if number is not None:
            popsize = number
        selective_mirroring = True
        nmirrors = self.sp.lam_mirr
        if popsize != self.sp.popsize:
            nmirrors = Mh.sround(popsize * self.sp.lam_mirr / self.sp.popsize)
            # TODO: now selective mirroring might be impaired
        assert nmirrors <= popsize // 2
        self.mirrors_idx = np.arange(nmirrors)  # might never be used
        self.mirrors_rejected_idx = []  # might never be used
        if xmean is None:
            xmean = self.mean

        # do the work
        fit = []  # or np.NaN * np.empty(number)
        X_first = self.ask(popsize)
        X = []
        for k in xrange(int(popsize)):
            nreject = -1
            f = np.NaN
            while f in (np.NaN, None):  # rejection sampling
                nreject += 1
                if k < popsize - nmirrors or nreject:
                    if nreject:
                        x = self.ask(1, xmean, sigma_fac)[0]
                    else:
                        x = X_first.pop(0)
                else:  # mirrored sample
                    if k == popsize - nmirrors and selective_mirroring:
                        self.mirrors_idx = np.argsort(fit)[-1:-1-nmirrors:-1]
                    x = self.get_mirror(X[self.mirrors_idx[popsize - 1 - k]])
                if nreject == 1 and k >= popsize - nmirrors:
                    self.mirrors_rejected_idx.append(k)

                # contraints handling test hardwired ccccccccccc
                if 11 < 3 and self.opts['vv'] and nreject < 2:  # trying out negative C-update as constraints handling
                    if not hasattr(self, 'constraints_paths'):
                        k = 1
                        self.constraints_paths = [np.zeros(self.N) for _i in xrange(k)]
                    Izero = np.zeros([self.N, self.N])
                    for i in xrange(self.N):
                        if x[i] < 0:
                            Izero[i][i] = 1
                            self.C -= self.opts['vv'] * Izero
                            Izero[i][i] = 0
                    if 1 < 3 and sum([ (9 + i + 1) * x[i] for i in xrange(self.N)]) > 50e3:
                        self.constraints_paths[0] = 0.9 * self.constraints_paths[0] + 0.1 * (x - self.mean) / self.sigma
                        self.C -= (self.opts['vv'] / self.N) * np.outer(self.constraints_paths[0], self.constraints_paths[0])

                f = func(x, *args)
                if f not in (np.NaN, None) and evaluations > 1:
                    f = aggregation([f] + [func(x, *args) for _i in xrange(int(evaluations-1))])
                if nreject + 1 % 1000 == 0:
                    print('  %d solutions rejected (f-value NaN or None) at iteration %d' %
                          (nreject, self.countiter))
            fit.append(f)
            X.append(x)
        self.evaluations_per_f_value = int(evaluations)
        return X, fit


    #____________________________________________________________
    def tell(self, solutions, function_values, check_points=None, copy=False):
        """pass objective function values to prepare for next
        iteration. This core procedure of the CMA-ES algorithm updates
        all state variables, in particular the two evolution paths, the
        distribution mean, the covariance matrix and a step-size.

        Arguments
        ---------
            `solutions`
                list or array of candidate solution points (of
                type `numpy.ndarray`), most presumably before
                delivered by method `ask()` or `ask_and_eval()`.
            `function_values`
                list or array of objective function values
                corresponding to the respective points. Beside for termination
                decisions, only the ranking of values in `function_values`
                is used.
            `check_points`
                If ``check_points is None``, only solutions that are not generated
                by `ask()` are possibly clipped (recommended). ``False`` does not clip
                any solution (not recommended).
                If ``True``, clips solutions that realize long steps (i.e. also
                those that are unlikely to be generated with `ask()`). `check_points`
                can be a list of indices to be checked in solutions.
            `copy`
                ``solutions`` can be modified in this routine, if ``copy is False``

        Details
        -------
        `tell()` updates the parameters of the multivariate
        normal search distribution, namely covariance matrix and
        step-size and updates also the attributes `countiter` and
        `countevals`. To check the points for consistency is quadratic
        in the dimension (like sampling points).

        Bugs
        ----
        The effect of changing the solutions delivered by `ask()` depends on whether
        boundary handling is applied. With boundary handling, modifications are
        disregarded. This is necessary to apply the default boundary handling that
        uses unrepaired solutions but might change in future.

        Example
        -------
        ::

            import cma
            func = cma.fcts.elli  # choose objective function
            es = cma.CMAEvolutionStrategy(cma.np.random.rand(10), 1)
            while not es.stop():
               X = es.ask()
               es.tell(X, [func(x) for x in X])
            es.result()  # where the result can be found

        :See: class `CMAEvolutionStrategy`, `ask()`, `ask_and_eval()`, `fmin()`

        """
    #____________________________________________________________
    # TODO: consider an input argument that flags injected trust-worthy solutions (which means
    #       that they can be treated "absolut" rather than "relative")
        if self.flgtelldone:
            raise _Error('tell should only be called once per iteration')

        lam = len(solutions)
        if lam != array(function_values).shape[0]:
            raise _Error('for each candidate solution '
                        + 'a function value must be provided')
        if lam + self.sp.lam_mirr < 3:
            raise _Error('population size ' + str(lam) + ' is too small when option CMA_mirrors * popsize < 0.5')

        if not np.isscalar(function_values[0]):
            if np.isscalar(function_values[0][0]):
                if self.countiter <= 1:
                    print('WARNING: function values are not a list of scalars (further warnings are suppressed)')
                function_values = [val[0] for val in function_values]
            else:
                raise _Error('objective function values must be a list of scalars')


        ### prepare
        N = self.N
        sp = self.sp
        if 11 < 3 and lam != sp.popsize:  # turned off, because mu should stay constant, still not desastrous
            print('WARNING: population size has changed, recomputing parameters')
            self.sp.set(self.opts, lam)  # not really tested
        if lam < sp.mu:  # rather decrease cmean instead of having mu > lambda//2
            raise _Error('not enough solutions passed to function tell (mu>lambda)')

        self.countiter += 1  # >= 1 now
        self.countevals += sp.popsize * self.evaluations_per_f_value
        self.best.update(solutions, self.sent_solutions, function_values, self.countevals)

        flgseparable = self.opts['CMA_diagonal'] is True \
                       or self.countiter <= self.opts['CMA_diagonal']
        if not flgseparable and len(self.C.shape) == 1:  # C was diagonal ie 1-D
            # enter non-separable phase (no easy return from here)
            self.B = np.eye(N) # identity(N)
            self.C = np.diag(self.C)
            idx = np.argsort(self.D)
            self.D = self.D[idx]
            self.B = self.B[:,idx]
            self.Zneg = np.zeros((N, N))

        ### manage fitness
        fit = self.fit  # make short cut

        # CPU for N,lam=20,200: this takes 10s vs 7s
        fit.bndpen = self.boundPenalty.update(function_values, self)(solutions, self.sent_solutions, self.gp)
        # for testing:
        # fit.bndpen = self.boundPenalty.update(function_values, self)([s.unrepaired for s in solutions])
        fit.idx = np.argsort(array(fit.bndpen) + array(function_values))
        fit.fit = array(function_values, copy=False)[fit.idx]

        # update output data TODO: this is obsolete!? However: need communicate current best x-value?
        # old: out['recent_x'] = self.gp.pheno(pop[0])
        self.out['recent_x'] = array(solutions[fit.idx[0]])  # TODO: change in a data structure(?) and use current as identify
        self.out['recent_f'] = fit.fit[0]

        # fitness histories
        fit.hist.insert(0, fit.fit[0])
        # if len(self.fit.histbest) < 120+30*N/sp.popsize or  # does not help, as tablet in the beginning is the critical counter-case
        if ((self.countiter % 5) == 0):  # 20 percent of 1e5 gen.
            fit.histbest.insert(0, fit.fit[0])
            fit.histmedian.insert(0, np.median(fit.fit) if len(fit.fit) < 21
                                    else fit.fit[self.popsize // 2])
        if len(fit.histbest) > 2e4: # 10 + 30*N/sp.popsize:
            fit.histbest.pop()
            fit.histmedian.pop()
        if len(fit.hist) > 10 + 30*N/sp.popsize:
            fit.hist.pop()

        if self.opts['CMA_AII']:
            self.aii.tell(solutions, function_values)
            self.flgtelldone = True
            # for output:
            self.mean = self.aii.mean
            self.dC = self.aii.sigmai**2
            self.sigma = self.aii.sigma
            self.D = 1e-11 + (self.aii.r**2)**0.5
            self.more_to_write += [self.aii.sigma_r]
            return

        # TODO: clean up inconsistency when an unrepaired solution is available and used
        pop = []  # create pop from input argument solutions
        for s in solutions:  # use phenotype before Solution.repair()
            if use_sent_solutions:
                x = self.sent_solutions.pop(s, None)  # 12.7s vs 11.3s with N,lambda=20,200
                if x is not None:
                    pop.append(x['geno'])
                    # TODO: keep additional infos or don't pop s from sent_solutions in the first place
                else:
                    # print 'WARNING: solution not found in ``self.sent_solutions`` (is expected for injected solutions)'
                    pop.append(self.gp.geno(s, copy=copy))  # cannot recover the original genotype with boundary handling
                    if check_points in (None, True, 1):
                        self.repair_genotype(pop[-1])  # necessary if pop[-1] was changed or injected by the user.
            else:  # TODO: to be removed?
                # print 'WARNING: ``geno`` mapping depreciated'
                pop.append(self.gp.geno(s, copy=copy))
                if check_points in (None, True, 1):
                    self.repair_genotype(pop[-1])  # necessary or not?
                # print 'repaired'

        mold = self.mean
        sigma_fac = 1

        # check and normalize each x - m
        # check_points is a flag (None is default: check non-known solutions) or an index list
        # should also a number possible (first check_points points)?
        if check_points not in (None, False, 0, [], ()):  # useful in case of injected solutions and/or adaptive encoding, however is automatic with use_sent_solutions
            try:
                if len(check_points):
                    idx = check_points
            except:
                idx = xrange(sp.popsize)

            for k in idx:
                self.repair_genotype(pop[k])

        # sort pop
        if type(pop) is not array: # only arrays can be multiple indexed
            pop = array(pop, copy=False)

        pop = pop[fit.idx]

        if self.opts['CMA_elitist'] and self.best.f < fit.fit[0]:
            if self.best.x_geno is not None:
                xp = [self.best.x_geno]
                # xp = [self.best.xdict['geno']]
                # xp = [self.gp.geno(self.best.x[:])]  # TODO: remove
                # print self.mahalanobisNorm(xp[0]-self.mean)
                self.clip_or_fit_solutions(xp, [0])
                pop = array([xp[0]] + list(pop))
            else:
                print('genotype for elitist not found')

        # compute new mean
        self.mean = mold + self.sp.cmean * \
                    (sum(sp.weights * pop[0:sp.mu].T, 1) - mold)


        # check Delta m (this is not default, but could become at some point)
        # CAVE: upper_length=sqrt(2)+2 is too restrictive, test upper_length = sqrt(2*N) thoroughly.
        # simple test case injecting self.mean:
        # self.mean = 1e-4 * self.sigma * np.random.randn(N)
        if 11 < 3 and self.opts['vv'] and check_points:  # TODO: check_points might be an index-list
            cmean = self.sp.cmean / min(1, (sqrt(self.opts['vv']*N)+2) / ( # abuse of cmean
                (sqrt(self.sp.mueff) / self.sp.cmean) *
                self.mahalanobisNorm(self.mean - mold)))
        else:
            cmean = self.sp.cmean

        if 11 < 3:  # plot length of mean - mold
            self.more_to_write += [sqrt(sp.mueff) *
                sum(((1./self.D) * dot(self.B.T, self.mean - mold))**2)**0.5 /
                       self.sigma / sqrt(N) / cmean]

        # get learning rate constants
        cc, c1, cmu = sp.cc, sp.c1, sp.cmu
        if flgseparable:
            cc, c1, cmu = sp.cc_sep, sp.c1_sep, sp.cmu_sep

        # now the real work can start

        # evolution paths
        self.ps = (1-sp.cs) * self.ps + \
                  (sqrt(sp.cs*(2-sp.cs)*sp.mueff)  / self.sigma / cmean) * \
                  dot(self.B, (1./self.D) * dot(self.B.T, (self.mean - mold) / self.sigma_vec))

        # "hsig", correction with self.countiter seems not necessary, also pc starts with zero
        hsig = sum(self.ps**2) / (1-(1-sp.cs)**(2*self.countiter)) / self.N < 2 + 4./(N+1)
        if 11 < 3:
            # hsig = 1
            # sp.cc = 4 / (N + 4)
            # sp.cs = 4 / (N + 4)
            # sp.cc = 1
            # sp.damps = 2  #
            # sp.CMA_on = False
            # c1 = 0  # 2 / ((N + 1.3)**2 + 0 * sp.mu) # 1 / N**2
            # cmu = min([1 - c1, cmu])
            if self.countiter == 1:
                print('parameters modified')
        # hsig = sum(self.ps**2) / self.N < 2 + 4./(N+1)
        # adjust missing variance due to hsig, in 4-D with damps=1e99 and sig0 small
        #       hsig leads to premature convergence of C otherwise
        #hsiga = (1-hsig**2) * c1 * cc * (2-cc)  # to be removed in future
        c1a = c1 - (1-hsig**2) * c1 * cc * (2-cc)  # adjust for variance loss

        if 11 < 3:  # diagnostic data
            self.out['hsigcount'] += 1 - hsig
            if not hsig:
                self.hsiglist.append(self.countiter)
        if 11 < 3:  # diagnostic message
            if not hsig:
                print(str(self.countiter) + ': hsig-stall')
        if 11 < 3:  # for testing purpose
            hsig = 1 # TODO:
            #       put correction term, but how?
            if self.countiter == 1:
                print('hsig=1')

        self.pc = (1-cc) * self.pc + \
                  hsig * (sqrt(cc*(2-cc)*sp.mueff) / self.sigma / cmean) * \
                  (self.mean - mold)  / self.sigma_vec

        # covariance matrix adaptation/udpate
        if sp.CMA_on:
            # assert sp.c1 + sp.cmu < sp.mueff / N  # ??
            assert c1 + cmu <= 1

            # default full matrix case
            if not flgseparable:
                Z = (pop[0:sp.mu] - mold) / (self.sigma * self.sigma_vec)
                Z = dot((cmu * sp.weights) * Z.T, Z)  # learning rate integrated
                if self.sp.neg.cmuexp:
                    tmp = (pop[-sp.neg.mu:] - mold) / (self.sigma * self.sigma_vec)
                    self.Zneg *= 1 - self.sp.neg.cmuexp  # for some reason necessary?
                    self.Zneg += dot(sp.neg.weights * tmp.T, tmp) - self.C
                    # self.update_exponential(dot(sp.neg.weights * tmp.T, tmp) - 1 * self.C, -1*self.sp.neg.cmuexp)

                if 11 < 3: # ?3 to 5 times slower??
                    Z = np.zeros((N,N))
                    for k in xrange(sp.mu):
                        z = (pop[k]-mold)
                        Z += np.outer((cmu * sp.weights[k] / (self.sigma * self.sigma_vec)**2) * z, z)

                self.C *= 1 - c1a - cmu
                self.C += np.outer(c1 * self.pc, self.pc) + Z
                self.dC = np.diag(self.C)  # for output and termination checking

            else: # separable/diagonal linear case
                assert(c1+cmu <= 1)
                Z = np.zeros(N)
                for k in xrange(sp.mu):
                    z = (pop[k]-mold) / (self.sigma * self.sigma_vec) # TODO see above
                    Z += sp.weights[k] * z * z  # is 1-D
                self.C = (1-c1a-cmu) * self.C + c1 * self.pc * self.pc + cmu * Z
                # TODO: self.C *= exp(cmuneg * (N - dot(sp.neg.weights,  **2)
                self.dC = self.C
                self.D = sqrt(self.C)  # C is a 1-D array
                self.itereigenupdated = self.countiter

                # idx = self.mirror_idx_cov()  # take half of mirrored vectors for negative update

        # qqqqqqqqqqq
        if 1 < 3 and np.isfinite(sp.dampsvec):
            if self.countiter == 1:
                print("WARNING: CMA_dampsvec option is experimental")
            sp.dampsvec *= np.exp(sp.dampsvec_fading/self.N)
            # TODO: rank-lambda update: *= (1 + sum(z[z>1]**2-1) * exp(sum(z[z<1]**2-1))
            self.sigma_vec *= np.exp((sp.cs/sp.dampsvec/2) * (self.ps**2 - 1))
            # self.sigma_vec *= np.exp((sp.cs/sp.dampsvec) * (abs(self.ps) - (2/np.pi)**0.5))
            self.more_to_write += [exp(np.mean((self.ps**2 - 1)**2))]
            # TODO: rank-mu update

        # step-size adaptation, adapt sigma
        if 1 < 3:  #
            self.sigma *= sigma_fac * \
                            np.exp((min((1, (sp.cs/sp.damps) *
                                    (sqrt(sum(self.ps**2))/self.const.chiN - 1)))))
        else:
            self.sigma *= sigma_fac * \
                            np.exp((min((1000, (sp.cs/sp.damps/2) *
                                    (sum(self.ps**2)/N - 1)))))
        if 11 < 3:
            # derandomized MSR = natural gradient descent using mean(z**2) instead of mu*mean(z)**2
            lengths = array([sum(z**2)**0.5 for z in self.arz[fit.idx[:self.sp.mu]]])
            # print lengths[0::int(self.sp.mu/5)]
            self.sigma *= np.exp(self.sp.mueff**0.5 * dot(self.sp.weights, lengths / self.const.chiN - 1))**(2/(N+1))

        if 11 < 3 and self.opts['vv']:
            if self.countiter < 2:
                print('constant sigma applied')
                print(self.opts['vv'])  # N=10,lam=10: 0.8 is optimal
            self.sigma = self.opts['vv'] * self.sp.mueff * sum(self.mean**2)**0.5 / N

        if self.sigma * min(self.dC)**0.5 < self.opts['minstd']:
            self.sigma = self.opts['minstd'] / min(self.dC)**0.5
        # g = self.countiter
        # N = self.N
        mindx = eval(self.opts['mindx']) if type(self.opts['mindx']) == type('') else self.opts['mindx']
        if self.sigma * min(self.D) < mindx:  # TODO: sigma_vec is missing here
            self.sigma = mindx / min(self.D)

        if self.sigma > 1e9 * self.sigma0:
            alpha = self.sigma / max(self.D)
            self.multiplyC(alpha)
            self.sigma /= alpha**0.5
            self.opts['tolupsigma'] /= alpha**0.5  # to be compared with sigma

        # TODO increase sigma in case of a plateau?

        # Uncertainty noise measurement is done on an upper level

        # output, has moved up, e.g. as part of fmin, TODO to be removed
        if 11 < 3 and self.opts['verb_log'] > 0 and (self.countiter < 4 or
                                          self.countiter % self.opts['verb_log'] == 0):
            # this assumes that two logger with the same name access the same data!
            CMADataLogger(self.opts['verb_filenameprefix']).register(self, append=True).add()
            # self.writeOutput(solutions[fit.idx[0]])

        self.flgtelldone = True
    # end tell()

    def result(self):
        """return ``(xbest, f(xbest), evaluations_xbest, evaluations, iterations, pheno(xmean), effective_stds)``"""
        # TODO: how about xcurrent?
        return self.best.get() + (
            self.countevals, self.countiter, self.gp.pheno(self.mean), self.gp.scales * self.sigma * self.sigma_vec * self.dC**0.5)

    def clip_or_fit_solutions(self, pop, idx):
        """make sure that solutions fit to sample distribution, this interface will probably change.

        In particular the frequency of long vectors appearing in pop[idx] - self.mean is limited.

        """
        for k in idx:
            self.repair_genotype(pop[k])

    def repair_genotype(self, x):
        """make sure that solutions fit to sample distribution, this interface will probably change.

        In particular the frequency of x - self.mean being long is limited.

        """
        mold = self.mean
        if 1 < 3:  # hard clip at upper_length
            upper_length = self.N**0.5 + 2 * self.N / (self.N+2)  # should become an Option, but how? e.g. [0, 2, 2]
            fac = self.mahalanobisNorm(x - mold) / upper_length

            if fac > 1:
                x = (x - mold) / fac + mold
                # print self.countiter, k, fac, self.mahalanobisNorm(pop[k] - mold)
                # adapt also sigma: which are the trust-worthy/injected solutions?
            elif 11 < 3:
                return exp(np.tanh(((upper_length*fac)**2/self.N-1)/2) / 2)
        else:
            if 'checktail' not in self.__dict__:  # hasattr(self, 'checktail')
                raise NotImplementedError
                # from check_tail_smooth import CheckTail  # for the time being
                # self.checktail = CheckTail()
                # print('untested feature checktail is on')
            fac = self.checktail.addchin(self.mahalanobisNorm(x - mold))

            if fac < 1:
                x = fac * (x - mold) + mold

        return 1.0  # sigma_fac, not in use


    #____________________________________________________________
    #____________________________________________________________
    #
    def updateBD(self):
        """update internal variables for sampling the distribution with the
        current covariance matrix C. This method is O(N^3), if C is not diagonal.

        """
        # itereigenupdated is always up-to-date in the diagonal case
        # just double check here
        if self.itereigenupdated == self.countiter:
            return

        if self.sp.neg.cmuexp:  # cave:
            self.update_exponential(self.Zneg, -self.sp.neg.cmuexp)
            # self.C += self.Zpos  # pos update after Zneg would be the correct update, overall:
            # self.C = self.Zpos + Cs * Mh.expms(-self.sp.neg.cmuexp*Csi*self.Zneg*Csi) * Cs
            self.Zneg = np.zeros((self.N, self.N))

        if self.sigma_vec is not 1 and not np.all(self.sigma_vec == 1):
            self.C = dot(dot(np.diag(self.sigma_vec), self.C), np.diag(self.sigma_vec))
            self.sigma_vec[:] = 1

        if self.opts['CMA_const_trace'] in (True, 1, 2):  # normalize trace of C
            if self.opts['CMA_const_trace'] == 2:
                s = np.exp(np.mean(np.log(self.dC)))
            else:
                s = np.mean(self.dC)
            self.C /= s
            self.dC /= s
        self.C = (self.C + self.C.T) / 2
        # self.C = np.triu(self.C) + np.triu(self.C,1).T  # should work as well
        # self.D, self.B = eigh(self.C) # hermitian, ie symmetric C is assumed

        if type(self.opts['CMA_eigenmethod']) == type(1):
            print('WARNING: option CMA_eigenmethod should be a function, not an integer')
            if self.opts['CMA_eigenmethod'] == -1:
                # pygsl
                # easy to install (well, in Windows install gsl binaries first,
                # set system path to respective libgsl-0.dll (or cp the dll to
                # python\DLLS ?), in unzipped pygsl edit
                # gsl_dist/gsl_site_example.py into gsl_dist/gsl_site.py
                # and run "python setup.py build" and "python setup.py install"
                # in MINGW32)
                if 1 < 3:  # import pygsl on the fly
                    try:
                        import pygsl.eigen.eigenvectors  # TODO efficient enough?
                    except ImportError:
                        print('WARNING: could not find pygsl.eigen module, either install pygsl \n' +
                              '  or set option CMA_eigenmethod=1 (is much slower), option set to 1')
                        self.opts['CMA_eigenmethod'] = 0  # use 0 if 1 is too slow

                    self.D, self.B = pygsl.eigen.eigenvectors(self.C)

            elif self.opts['CMA_eigenmethod'] == 0:
                # TODO: thoroughly test np.linalg.eigh
                #       numpy.linalg.eig crashes in 200-D
                #       and EVecs with same EVals are not orthogonal
                self.D, self.B = np.linalg.eigh(self.C)  # self.B[i] is a row and not an eigenvector
            else:  # is overall two;ten times slower in 10;20-D
                self.D, self.B = Misc.eig(self.C)  # def eig, see below
        else:
            self.D, self.B = self.opts['CMA_eigenmethod'](self.C)


        # assert(sum(self.D-DD) < 1e-6)
        # assert(sum(sum(np.dot(BB, BB.T)-np.eye(self.N))) < 1e-6)
        # assert(sum(sum(np.dot(BB * DD, BB.T) - self.C)) < 1e-6)
        idx = np.argsort(self.D)
        self.D = self.D[idx]
        self.B = self.B[:,idx]  # self.B[i] is a row, columns self.B[:,i] are eigenvectors
        # assert(all(self.B[self.countiter % self.N] == self.B[self.countiter % self.N,:]))

        # qqqqqqqqqq
        if 11 < 3:  # limit condition number to 1e13
            climit = 1e13  # cave: conditioncov termination is 1e14
            if self.D[-1] / self.D[0] > climit:
                self.D += self.D[-1] / climit
            for i in xrange(self.N):
                self.C[i][i] += self.D[-1] / climit

        if 11 < 3 and any(abs(sum(self.B[:,0:self.N-1] * self.B[:,1:], 0)) > 1e-6):
            print('B is not orthogonal')
            print(self.D)
            print(sum(self.B[:,0:self.N-1] * self.B[:,1:], 0))
        else:
            # is O(N^3)
            # assert(sum(abs(self.C - np.dot(self.D * self.B,  self.B.T))) < N**2*1e-11)
            pass
        self.D **= 0.5
        self.itereigenupdated = self.countiter

    def multiplyC(self, alpha):
        """multiply C with a scalar and update all related internal variables (dC, D,...)"""
        self.C *= alpha
        if self.dC is not self.C:
            self.dC *= alpha
        self.D *= alpha**0.5
    def update_exponential(self, Z, eta, BDpair=None):
        """exponential update of C that guarantees positive definiteness, that is,
        instead of the assignment ``C = C + eta * Z``,
        C gets C**.5 * exp(eta * C**-.5 * Z * C**-.5) * C**.5.

        Parameter Z should have expectation zero, e.g. sum(w[i] * z[i] * z[i].T) - C
        if E z z.T = C.

        This function conducts two eigendecompositions, assuming that
        B and D are not up to date, unless `BDpair` is given. Given BDpair,
        B is the eigensystem and D is the vector of sqrt(eigenvalues), one
        eigendecomposition is omitted.

        Reference: Glasmachers et al 2010, Exponential Natural Evolution Strategies

        """
        if eta == 0:
            return
        if BDpair:
            B, D = BDpair
        else:
            D, B = self.opts['CMA_eigenmethod'](self.C)
            D **= 0.5
        Csi = dot(B, (B / D).T)
        Cs = dot(B, (B * D).T)
        self.C = dot(Cs, dot(Mh.expms(eta * dot(Csi, dot(Z, Csi)), self.opts['CMA_eigenmethod']), Cs))

    #____________________________________________________________
    #____________________________________________________________
    #
    def _updateCholesky(self, A, Ainv, p, alpha, beta):
        """not yet implemented"""
        # BD is A, p is A*Normal(0,I) distributed
        # input is assumed to be numpy arrays
        # Ainv is needed to compute the evolution path
        # this is a stump and is not tested

        raise _Error("not yet implemented")
        # prepare
        alpha = float(alpha)
        beta = float(beta)
        y = np.dot(Ainv, p)
        y_sum = sum(y**2)

        # compute scalars
        tmp = sqrt(1 + beta * y_sum / alpha)
        fac = (sqrt(alpha) / sum(y**2)) * (tmp - 1)
        facinv = (1. / (sqrt(alpha) * sum(y**2))) * (1 - 1. / tmp)

        # update matrices
        A *= sqrt(alpha)
        A += np.outer(fac * p, y)
        Ainv /= sqrt(alpha)
        Ainv -= np.outer(facinv * y, np.dot(y.T, Ainv))

    #____________________________________________________________
    #____________________________________________________________
    def feedForResume(self, X, function_values):
        """Given all "previous" candidate solutions and their respective
        function values, the state of a `CMAEvolutionStrategy` object
        can be reconstructed from this history. This is the purpose of
        function `feedForResume`.

        Arguments
        ---------
            `X`
              (all) solution points in chronological order, phenotypic
              representation. The number of points must be a multiple
              of popsize.
            `function_values`
              respective objective function values

        Details
        -------
        `feedForResume` can be called repeatedly with only parts of
        the history. The part must have the length of a multiple
        of the population size.
        `feedForResume` feeds the history in popsize-chunks into `tell`.
        The state of the random number generator might not be
        reconstructed, but this would be only relevant for the future.

        Example
        -------
        ::

            import cma

            # prepare
            (x0, sigma0) = ... # initial values from previous trial
            X = ... # list of generated solutions from a previous trial
            f = ... # respective list of f-values

            # resume
            es = cma.CMAEvolutionStrategy(x0, sigma0)
            es.feedForResume(X, f)

            # continue with func as objective function
            while not es.stop():
               X = es.ask()
               es.tell(X, [func(x) for x in X])

        Credits to Dirk Bueche and Fabrice Marchal for the feeding idea.

        :See: class `CMAEvolutionStrategy` for a simple dump/load to resume

        """
        if self.countiter > 0:
            print('WARNING: feed should generally be used with a new object instance')
        if len(X) != len(function_values):
            raise _Error('number of solutions ' + str(len(X)) +
                ' and number function values ' +
                str(len(function_values))+' must not differ')
        popsize = self.sp.popsize
        if (len(X) % popsize) != 0:
            raise _Error('number of solutions ' + str(len(X)) +
                    ' must be a multiple of popsize (lambda) ' +
                    str(popsize))
        for i in xrange(len(X) / popsize):
            # feed in chunks of size popsize
            self.ask()  # a fake ask, mainly for a conditioned calling of updateBD
                        # and secondary to get possibly the same random state
            self.tell(X[i*popsize:(i+1)*popsize], function_values[i*popsize:(i+1)*popsize])

    #____________________________________________________________
    #____________________________________________________________
    def readProperties(self):
        """reads dynamic parameters from property file (not implemented)
        """
        print('not yet implemented')

    #____________________________________________________________
    #____________________________________________________________
    def mahalanobisNorm(self, dx):
        """
        compute the Mahalanobis norm that is induced by the adapted covariance
        matrix C times sigma**2.

        Argument
        --------
        A *genotype* difference `dx`.

        Example
        -------
        >>> import cma, numpy
        >>> es = cma.CMAEvolutionStrategy(numpy.ones(10), 1)
        >>> xx = numpy.random.randn(2, 10)
        >>> d = es.mahalanobisNorm(es.gp.geno(xx[0]-xx[1]))

        `d` is the distance "in" the true sample distribution,
        sampled points have a typical distance of ``sqrt(2*es.N)``,
        where `N` is the dimension. In the example, `d` is the
        Euclidean distance, because C = I and sigma = 1.

        """
        return sqrt(sum((self.D**-1 * np.dot(self.B.T, dx))**2)) / self.sigma

    #____________________________________________________________
    #____________________________________________________________
    #
    def timesCroot(self, mat):
        """return C**0.5 times mat, where mat can be a vector or matrix.
        Not functional, because _Croot=C**0.5 is never computed (should be in updateBD)
        """
        print("WARNING: timesCroot is not yet tested")
        if self.opts['CMA_diagonal'] is True \
                       or self.countiter <= self.opts['CMA_diagonal']:
            res = (self._Croot * mat.T).T
        else:
            res = np.dot(self._Croot, mat)
        return res
    def divCroot(self, mat):
        """return C**-1/2 times mat, where mat can be a vector or matrix"""
        print("WARNING: divCroot is not yet tested")
        if self.opts['CMA_diagonal'] is True \
                       or self.countiter <= self.opts['CMA_diagonal']:
            res = (self._Crootinv * mat.T).T
        else:
            res = np.dot(self._Crootinv, mat)
        return res

    #____________________________________________________________
    #____________________________________________________________
    def disp_annotation(self):
        """print annotation for `disp()`"""
        print('Iterat #Fevals   function value     axis ratio  sigma   minstd maxstd min:sec')
        sys.stdout.flush()

    #____________________________________________________________
    #____________________________________________________________
    def disp(self, modulo=None):  # TODO: rather assign opt['verb_disp'] as default?
        """prints some infos according to `disp_annotation()`, if
        ``iteration_counter % modulo == 0``

        """
        if modulo is None:
            modulo = self.opts['verb_disp']

        # console display
        if modulo:
            if (self.countiter-1) % (10 * modulo) < 1:
                self.disp_annotation()
            if self.countiter > 0 and (self.stop() or self.countiter < 4
                              or self.countiter % modulo < 1):
                if self.opts['verb_time']:
                    toc = self.elapsed_time()
                    stime = str(int(toc//60))+':'+str(round(toc%60,1))
                else:
                    stime = ''
                print(' '.join((repr(self.countiter).rjust(5),
                                repr(self.countevals).rjust(7),
                                '%.15e' % (min(self.fit.fit)),
                                '%4.1e' % (self.D.max()/self.D.min()),
                                '%6.2e' % self.sigma,
                                '%6.0e' % (self.sigma * sqrt(min(self.dC))),
                                '%6.0e' % (self.sigma * sqrt(max(self.dC))),
                                stime)))
                # if self.countiter < 4:
                sys.stdout.flush()

class Options(dict):
    """``Options()`` returns a dictionary with the available options and their
    default values for function fmin and for class CMAEvolutionStrategy.

    ``Options(opts)`` returns the subset of recognized options in dict(opts).

    ``Options('pop')`` returns a subset of recognized options that contain
    'pop' in there keyword name, value or description.

    Option values can be "written" in a string and, when passed to fmin
    or CMAEvolutionStrategy, are evaluated using "N" and "popsize" as
    known values for dimension and population size (sample size, number
    of new solutions per iteration). All default option values are such
    a string.

    Details
    -------
    All Options are originally defined via the input arguments of
    `fmin()`.

    Options starting with ``tol`` are termination "tolerances".

    For `tolstagnation`, the median over the first and the second half
    of at least `tolstagnation` iterations are compared for both, the
    per-iteration best and per-iteration median function value.
    Some options are, as mentioned (`restarts`,...), only used with `fmin`.

    Example
    -------
    ::

        import cma
        cma.Options('tol')

    is a shortcut for cma.Options().match('tol') that returns all options
    that contain 'tol' in their name or description.

    :See: `fmin`(), `CMAEvolutionStrategy`, `CMAParameters`

    """

    # @classmethod # self is the class, not the instance
    # @property
    # def default(self):
    #     """returns all options with defaults"""
    #     return fmin([],[])

    @staticmethod
    def defaults():
        """return a dictionary with default option values and description,
        calls `fmin([], [])`"""
        return fmin([], [])

    @staticmethod
    def versatileOptions():
        """return list of options that can be changed at any time (not only be
        initialized), however the list might not be entirely up to date. The
        string ' #v ' in the default value indicates a 'versatile' option
        that can be changed any time.

        """
        return tuple(sorted(i[0] for i in list(Options.defaults().items()) if i[1].find(' #v ') > 0))

    def __init__(self, s=None, unchecked=False):
        """return an `Options` instance, either with the default options,
        if ``s is None``, or with all options whose name or description
        contains `s`, if `s` is a string (case is disregarded),
        or with entries from dictionary `s` as options, not complemented
        with default options or settings

        Returns: see above.

        """
        # if not Options.defaults:  # this is different from self.defaults!!!
        #     Options.defaults = fmin([],[])
        if s is None:
            super(Options, self).__init__(Options.defaults())
            # self = Options.defaults()
        elif type(s) is str:
            super(Options, self).__init__(Options().match(s))
            # we could return here
        else:
            super(Options, self).__init__(s)

        if not unchecked:
            for key in list(self.keys()):
                if key not in Options.defaults():
                    print('Warning in cma.Options.__init__(): invalid key ``' + str(key) + '`` popped')
                    self.pop(key)
        # self.evaluated = False  # would become an option entry

    def init(self, dict_or_str, val=None, warn=True):
        """initialize one or several options.

        Arguments
        ---------
            `dict_or_str`
                a dictionary if ``val is None``, otherwise a key.
                If `val` is provided `dict_or_str` must be a valid key.
            `val`
                value for key

        Details
        -------
        Only known keys are accepted. Known keys are in `Options.defaults()`

        """
        #dic = dict_or_key if val is None else {dict_or_key:val}
        dic = dict_or_str
        if val is not None:
            dic = {dict_or_str:val}

        for key, val in list(dic.items()):
            if key not in Options.defaults():
                # TODO: find a better solution?
                if warn:
                    print('Warning in cma.Options.init(): key ' +
                        str(key) + ' ignored')
            else:
                self[key] = val

        return self

    def set(self, dic, val=None, warn=True):
        """set can assign versatile options from `Options.versatileOptions()`
        with a new value, use `init()` for the others.

        Arguments
        ---------
            `dic`
                either a dictionary or a key. In the latter
                case, val must be provided
            `val`
                value for key
            `warn`
                bool, print a warning if the option cannot be changed
                and is therefore omitted

        This method will be most probably used with the ``opts`` attribute of
        a `CMAEvolutionStrategy` instance.

        """
        if val is not None:  # dic is a key in this case
            dic = {dic:val}  # compose a dictionary
        for key, val in list(dic.items()):
            if key in Options.versatileOptions():
                self[key] = val
            elif warn:
                print('Warning in cma.Options.set(): key ' + str(key) + ' ignored')
        return self  # to allow o = Options(o).set(new)

    def complement(self):
        """add all missing options with their default values"""

        for key in Options.defaults():
            if key not in self:
                self[key] = Options.defaults()[key]
        return self

    def settable(self):
        """return the subset of those options that are settable at any
        time.

        Settable options are in `versatileOptions()`, but the
        list might be incomlete.

        """
        return Options([i for i in list(self.items())
                                if i[0] in Options.versatileOptions()])

    def __call__(self, key, default=None, loc=None):
        """evaluate and return the value of option `key` on the fly, or
        returns those options whose name or description contains `key`,
        case disregarded.

        Details
        -------
        Keys that contain `filename` are not evaluated.
        For ``loc==None``, `self` is used as environment
        but this does not define `N`.

        :See: `eval()`, `evalall()`

        """
        try:
            val = self[key]
        except:
            return self.match(key)

        if loc is None:
            loc = self  # TODO: this hack is not so useful: popsize could be there, but N is missing
        try:
            if type(val) is str:
                val = val.split('#')[0].strip()  # remove comments
                if type(val) == type('') and key.find('filename') < 0 and key.find('mindx') < 0:
                    val = eval(val, globals(), loc)
            # invoke default
            # TODO: val in ... fails with array type, because it is applied element wise!
            # elif val in (None,(),[],{}) and default is not None:
            elif val is None and default is not None:
                val = eval(str(default), globals(), loc)
        except:
            pass  # slighly optimistic: the previous is bug-free
        return val

    def eval(self, key, default=None, loc=None):
        """Evaluates and sets the specified option value in
        environment `loc`. Many options need `N` to be defined in
        `loc`, some need `popsize`.

        Details
        -------
        Keys that contain 'filename' are not evaluated.
        For `loc` is None, the self-dict is used as environment

        :See: `evalall()`, `__call__`

        """
        self[key] = self(key, default, loc)
        return self[key]

    def evalall(self, loc=None):
        """Evaluates all option values in environment `loc`.

        :See: `eval()`

        """
        # TODO: this needs rather the parameter N instead of loc
        if 'N' in list(loc.keys()):  # TODO: __init__ of CMA can be simplified
            popsize = self('popsize', Options.defaults()['popsize'], loc)
            for k in list(self.keys()):
                self.eval(k, Options.defaults()[k],
                          {'N':loc['N'], 'popsize':popsize})
        return self

    def match(self, s=''):
        """return all options that match, in the name or the description,
        with string `s`, case is disregarded.

        Example: ``cma.Options().match('verb')`` returns the verbosity options.

        """
        match = s.lower()
        res = {}
        for k in sorted(self):
            s = str(k) + '=\'' + str(self[k]) + '\''
            if match in s.lower():
                res[k] = self[k]
        return Options(res)

    def pp(self):
        pprint(self)

    def printme(self, linebreak=80):
        for i in sorted(Options.defaults().items()):
            s = str(i[0]) + "='" + str(i[1]) + "'"
            a = s.split(' ')

            # print s in chunks
            l = ''  # start entire to the left
            while a:
                while a and len(l) + len(a[0]) < linebreak:
                    l += ' ' + a.pop(0)
                print(l)
                l = '        '  # tab for subsequent lines

#____________________________________________________________
#____________________________________________________________
class CMAParameters(object):
    """strategy parameters like population size and learning rates.

    Note:
        contrary to `Options`, `CMAParameters` is not (yet) part of the
        "user-interface" and subject to future changes (it might become
        a `collections.namedtuple`)

    Example
    -------
    >>> import cma
    >>> es = cma.CMAEvolutionStrategy(20 * [0.1], 1)
    (6_w,12)-CMA-ES (mu_w=3.7,w_1=40%) in dimension 20 (seed=504519190)  # the seed is "random" by default
    >>>
    >>> type(es.sp)  # sp contains the strategy parameters
    <class 'cma.CMAParameters'>
    >>>
    >>> es.sp.disp()
    {'CMA_on': True,
     'N': 20,
     'c1': 0.004181139918745593,
     'c1_sep': 0.034327992810300939,
     'cc': 0.17176721127681213,
     'cc_sep': 0.25259494835857677,
     'cmean': 1.0,
     'cmu': 0.0085149624979034746,
     'cmu_sep': 0.057796356229390715,
     'cs': 0.21434997799189287,
     'damps': 1.2143499779918929,
     'mu': 6,
     'mu_f': 6.0,
     'mueff': 3.7294589343030671,
     'popsize': 12,
     'rankmualpha': 0.3,
     'weights': array([ 0.40240294,  0.25338908,  0.16622156,  0.10437523,  0.05640348,
            0.01720771])}
    >>>
    >> es.sp == cma.CMAParameters(20, 12, cma.Options().evalall({'N': 20}))
    True

    :See: `Options`, `CMAEvolutionStrategy`

    """
    def __init__(self, N, opts, ccovfac=1, verbose=True):
        """Compute strategy parameters, mainly depending on
        dimension and population size, by calling `set`

        """
        self.N = N
        if ccovfac == 1:
            ccovfac = opts['CMA_on']  # that's a hack
        self.set(opts, ccovfac=ccovfac, verbose=verbose)

    def set(self, opts, popsize=None, ccovfac=1, verbose=True):
        """Compute strategy parameters as a function
        of dimension and population size """

        alpha_cc = 1.0  # cc-correction for mueff, was zero before

        def cone(df, mu, N, alphacov=2.0):
            """rank one update learning rate, ``df`` is disregarded and obsolete, reduce alphacov on noisy problems, say to 0.5"""
            return alphacov / ((N + 1.3)**2 + mu)

        def cmu(df, mu, alphamu=0.0, alphacov=2.0):
            """rank mu learning rate, disregarding the constrant cmu <= 1 - cone"""
            c = alphacov * (alphamu + mu - 2 + 1/mu) / ((N + 2)**2 + alphacov * mu / 2)
            # c = alphacov * (alphamu + mu - 2 + 1/mu) / (2 * (N + 2)**1.5 + alphacov * mu / 2)
            # print 'cmu =', c
            return c

        def conedf(df, mu, N):
            """used for computing separable learning rate"""
            return 1. / (df + 2.*sqrt(df) + float(mu)/N)

        def cmudf(df, mu, alphamu):
            """used for computing separable learning rate"""
            return (alphamu + mu - 2. + 1./mu) / (df + 4.*sqrt(df) + mu/2.)

        sp = self
        N = sp.N
        if popsize:
            opts.evalall({'N':N, 'popsize':popsize})
        else:
            popsize = opts.evalall({'N':N})['popsize']  # the default popsize is computed in Options()
        sp.popsize = popsize
        if opts['CMA_mirrors'] < 0.5:
            sp.lam_mirr = int(0.5 + opts['CMA_mirrors'] * popsize)
        elif opts['CMA_mirrors'] > 1:
            sp.lam_mirr = int(0.5 + opts['CMA_mirrors'])
        else:
            sp.lam_mirr = int(0.5 + 0.16 * min((popsize, 2 * N + 2)) + 0.29)  # 0.158650... * popsize is optimal
            # lam = arange(2,22)
            # mirr = 0.16 + 0.29/lam
            # print(lam); print([int(0.5 + l) for l in mirr*lam])
            # [ 2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21]
            # [1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4]

        sp.mu_f = sp.popsize / 2.0  # float value of mu
        if opts['CMA_mu'] is not None:
            sp.mu_f = opts['CMA_mu']
        sp.mu = int(sp.mu_f + 0.499999) # round down for x.5
        # in principle we have mu_opt = popsize/2 + lam_mirr/2,
        # which means in particular weights should only be negative for q > 0.5+mirr_frac/2
        if sp.mu > sp.popsize - 2 * sp.lam_mirr + 1:
            print("WARNING: pairwise selection is not implemented, therefore " +
                  " mu = %d > %d = %d - 2*%d + 1 = popsize - 2*mirr + 1 can produce a bias" % (
                    sp.mu, sp.popsize - 2 * sp.lam_mirr + 1, sp.popsize, sp.lam_mirr))
        if sp.lam_mirr > sp.popsize // 2:
            raise _Error("fraction of mirrors in the population as read from option CMA_mirrors cannot be larger 0.5, " +
                         "theoretically optimal is 0.159")
        sp.weights = log(max([sp.mu, sp.popsize / 2.0]) + 0.5) - log(1 + np.arange(sp.mu))
        if 11 < 3:  # equal recombination weights
            sp.mu = sp.popsize // 4
            sp.weights = np.ones(sp.mu)
            print(sp.weights[:10])
        sp.weights /= sum(sp.weights)
        sp.mueff = 1 / sum(sp.weights**2)
        sp.cs = (sp.mueff + 2) / (N + sp.mueff + 3)
        # TODO: clean up (here the cumulation constant is shorter if sigma_vec is used)
        sp.dampsvec = opts['CMA_dampsvec_fac'] * (N + 2) if opts['CMA_dampsvec_fac'] else np.Inf
        sp.dampsvec_fading = opts['CMA_dampsvec_fade']
        if np.isfinite(sp.dampsvec):
            sp.cs = ((sp.mueff + 2) / (N + sp.mueff + 3))**0.5
        # sp.cs = (sp.mueff + 2) / (N + 1.5*sp.mueff + 1)
        sp.cc = (4 + alpha_cc * sp.mueff / N) / (N + 4 + alpha_cc * 2 * sp.mueff / N)
        sp.cc_sep = (1 + 1/N + alpha_cc * sp.mueff / N) / (N**0.5 + 1/N + alpha_cc * 2 * sp.mueff / N) # \not\gg\cc
        sp.rankmualpha = opts['CMA_rankmualpha']
        # sp.rankmualpha = _evalOption(opts['CMA_rankmualpha'], 0.3)
        sp.c1 = ccovfac * min(1, sp.popsize/6) * cone((N**2 + N) / 2, sp.mueff, N) # 2. / ((N+1.3)**2 + sp.mucov)
        sp.c1_sep = ccovfac * conedf(N, sp.mueff, N)
        if 11 < 3:
            sp.c1 = 0.
            print('c1 is zero')
        if opts['CMA_rankmu'] != 0:  # also empty
            sp.cmu = min(1 - sp.c1, ccovfac * cmu((N**2+N)/2, sp.mueff, sp.rankmualpha))
            sp.cmu_sep = min(1 - sp.c1_sep, ccovfac * cmudf(N, sp.mueff, sp.rankmualpha))
        else:
            sp.cmu = sp.cmu_sep = 0

        sp.neg = BlancClass()
        if opts['CMA_active']:
            # in principle we have mu_opt = popsize/2 + lam_mirr/2,
            # which means in particular weights should only be negative for q > 0.5+mirr_frac/2
            sp.neg.mu_f = popsize - (popsize + sp.lam_mirr) / 2  if popsize > 2 else 1
            sp.neg.weights = log(sp.mu_f + 0.5) - log(1 + np.arange(sp.popsize - int(sp.neg.mu_f), sp.popsize))
            sp.neg.mu = len(sp.neg.weights)  # maybe never useful?
            sp.neg.weights /= sum(sp.neg.weights)
            sp.neg.mueff = 1 / sum(sp.neg.weights**2)
            sp.neg.cmuexp = opts['CMA_activefac'] * 0.25 * sp.neg.mueff / ((N+2)**1.5 + 2 * sp.neg.mueff)
            assert sp.neg.mu >= sp.lam_mirr  # not really necessary
            # sp.neg.minresidualvariance = 0.66  # not it use, keep at least 0.66 in all directions, small popsize is most critical
        else:
            sp.neg.cmuexp = 0

        sp.CMA_on = sp.c1 + sp.cmu > 0
        # print(sp.c1_sep / sp.cc_sep)

        if not opts['CMA_on'] and opts['CMA_on'] not in (None,[],(),''):
            sp.CMA_on = False
            # sp.c1 = sp.cmu = sp.c1_sep = sp.cmu_sep = 0

        sp.damps = opts['CMA_dampfac'] * (0.5 +
                                          0.5 * min([1, (sp.lam_mirr/(0.159*sp.popsize) - 1)**2])**1 +
                                          2 * max([0, ((sp.mueff-1) / (N+1))**0.5 - 1]) + sp.cs
                                          )
        if 11 < 3:
            # this is worse than damps = 1 + sp.cs for the (1,10000)-ES on 40D parabolic ridge
            sp.damps = 0.3 + 2 * max([sp.mueff/sp.popsize, ((sp.mueff-1)/(N+1))**0.5 - 1]) + sp.cs
        if 11 < 3:
            # this does not work for lambda = 4*N^2 on the parabolic ridge
            sp.damps = opts['CMA_dampfac'] * (2 - 0*sp.lam_mirr/sp.popsize) * sp.mueff/sp.popsize + 0.3 + sp.cs  # nicer future setting
            print('damps =', sp.damps)
        if 11 < 3:
            sp.damps = 10 * sp.damps  # 1e99 # (1 + 2*max(0,sqrt((sp.mueff-1)/(N+1))-1)) + sp.cs;
            # sp.damps = 20 # 1. + 20 * sp.cs**-1  # 1e99 # (1 + 2*max(0,sqrt((sp.mueff-1)/(N+1))-1)) + sp.cs;
            print('damps is %f' % (sp.damps))

        sp.cmean = float(opts['CMA_cmean'])
        # sp.kappa = 1  # 4-D, lam=16, rank1, kappa < 4 does not influence convergence rate
                        # in larger dim it does, 15-D with defaults, kappa=8 factor 2
        if sp.cmean != 1:
            print('  cmean = %f' % (sp.cmean))

        if verbose:
            if not sp.CMA_on:
                print('covariance matrix adaptation turned off')
            if opts['CMA_mu'] != None:
                print('mu = %f' % (sp.mu_f))

        # return self  # the constructor returns itself

    def disp(self):
        pprint(self.__dict__)

#____________________________________________________________
#____________________________________________________________
class CMAStopDict(dict):
    """keep and update a termination condition dictionary, which is
    "usually" empty and returned by `CMAEvolutionStrategy.stop()`.

    Details
    -------
    This could be a nested class, but nested classes cannot be serialized.

    :See: `stop()`

    """
    def __init__(self, d={}):
        update = (type(d) == CMAEvolutionStrategy)
        inherit = (type(d) == CMAStopDict)
        super(CMAStopDict, self).__init__({} if update else d)
        self._stoplist = d._stoplist if inherit else []    # multiple entries
        self.lastiter = d.lastiter if inherit else 0  # probably not necessary
        if update:
            self._update(d)

    def __call__(self, es):
        """update the dictionary"""
        return self._update(es)

    def _addstop(self, key, cond, val=None):
        if cond:
            self.stoplist.append(key)  # can have the same key twice
            if key in list(self.opts.keys()):
                val = self.opts[key]
            self[key] = val

    def _update(self, es):
        """Test termination criteria and update dictionary.

        """
        if es.countiter == self.lastiter:
            if es.countiter == 0:
                self.__init__()
                return self
            try:
                if es == self.es:
                    return self
            except: # self.es not yet assigned
                pass

        self.lastiter = es.countiter
        self.es = es

        self.stoplist = []

        N = es.N
        opts = es.opts
        self.opts = opts  # a hack to get _addstop going

        # fitness: generic criterion, user defined w/o default
        self._addstop('ftarget',
                     es.best.f < opts['ftarget'])
        # maxiter, maxfevals: generic criteria
        self._addstop('maxfevals',
                     es.countevals - 1 >= opts['maxfevals'])
        self._addstop('maxiter',
                     es.countiter >= opts['maxiter'])
        # tolx, tolfacupx: generic criteria
        # tolfun, tolfunhist (CEC:tolfun includes hist)
        self._addstop('tolx',
                     all([es.sigma*xi < opts['tolx'] for xi in es.pc]) and \
                     all([es.sigma*xi < opts['tolx'] for xi in sqrt(es.dC)]))
        self._addstop('tolfacupx',
                     any([es.sigma * sig > es.sigma0 * opts['tolfacupx']
                          for sig in sqrt(es.dC)]))
        self._addstop('tolfun',
                     es.fit.fit[-1] - es.fit.fit[0] < opts['tolfun'] and \
                     max(es.fit.hist) - min(es.fit.hist) < opts['tolfun'])
        self._addstop('tolfunhist',
                     len(es.fit.hist) > 9 and \
                     max(es.fit.hist) - min(es.fit.hist) <  opts['tolfunhist'])

        # worst seen false positive: table N=80,lam=80, getting worse for fevals=35e3 \approx 50 * N**1.5
        # but the median is not so much getting worse
        # / 5 reflects the sparsity of histbest/median
        # / 2 reflects the left and right part to be compared
        l = int(max(opts['tolstagnation'] / 5. / 2, len(es.fit.histbest) / 10));
        # TODO: why max(..., len(histbest)/10) ???
        # TODO: the problem in the beginning is only with best ==> ???
        if 11 < 3:  #
            print(es.countiter, (opts['tolstagnation'], es.countiter > N * (5 + 100 / es.popsize),
                        len(es.fit.histbest) > 100,
                        np.median(es.fit.histmedian[:l]) >= np.median(es.fit.histmedian[l:2*l]),
                        np.median(es.fit.histbest[:l]) >= np.median(es.fit.histbest[l:2*l])))
        # equality should handle flat fitness
        self._addstop('tolstagnation', # leads sometimes early stop on ftablet, fcigtab, N>=50?
                    1 < 3 and opts['tolstagnation'] and es.countiter > N * (5 + 100 / es.popsize) and
                    len(es.fit.histbest) > 100 and 2*l < len(es.fit.histbest) and
                    np.median(es.fit.histmedian[:l]) >= np.median(es.fit.histmedian[l:2*l]) and
                    np.median(es.fit.histbest[:l]) >= np.median(es.fit.histbest[l:2*l]))
        # iiinteger: stagnation termination can prevent to find the optimum

        self._addstop('tolupsigma', opts['tolupsigma'] and
                      es.sigma / es.sigma0 / np.max(es.D) > opts['tolupsigma'])

        if 11 < 3 and 2*l < len(es.fit.histbest):  # TODO: this might go wrong, because the nb of written columns changes
            tmp = np.array((-np.median(es.fit.histmedian[:l]) + np.median(es.fit.histmedian[l:2*l]),
                        -np.median(es.fit.histbest[:l]) + np.median(es.fit.histbest[l:2*l])))
            es.more_to_write += [(10**t if t < 0 else t + 1) for t in tmp] # the latter to get monotonicy

        if 1 < 3:
            # non-user defined, method specific
            # noeffectaxis (CEC: 0.1sigma), noeffectcoord (CEC:0.2sigma), conditioncov
            self._addstop('noeffectcoord',
                         any([es.mean[i] == es.mean[i] + 0.2*es.sigma*sqrt(es.dC[i])
                              for i in xrange(N)]))
            if opts['CMA_diagonal'] is not True and es.countiter > opts['CMA_diagonal']:
                i = es.countiter % N
                self._addstop('noeffectaxis',
                             sum(es.mean == es.mean + 0.1 * es.sigma * es.D[i] * es.B[:, i]) == N)
            self._addstop('conditioncov',
                         es.D[-1] > 1e7 * es.D[0], 1e14)  # TODO

            self._addstop('callback', es.callbackstop)  # termination_callback
        if len(self):
            self._addstop('flat fitness: please (re)consider how to compute the fitness more elaborate',
                         len(es.fit.hist) > 9 and \
                         max(es.fit.hist) == min(es.fit.hist))
        if 11 < 3 and opts['vv'] == 321:
            self._addstop('||xmean||^2<ftarget', sum(es.mean**2) <= opts['ftarget'])

        return self

#_____________________________________________________________________
#_____________________________________________________________________
#
class BaseDataLogger2(DerivedDictBase):
    """"abstract" base class for a data logger that can be used with an `OOOptimizer`"""
    def add(self, optim=None, more_data=[]):
        """abstract method, add a "data point" from the state of `optim` into the
        logger, the argument `optim` can be omitted if it was `register()`-ed before,
        acts like an event handler"""
        raise NotImplementedError()
    def register(self, optim):
        """abstract method, register an optimizer `optim`, only needed if `add()` is
        called without a value for the `optim` argument"""
        self.optim = optim
    def disp(self):
        """display some data trace (not implemented)"""
        print('method BaseDataLogger.disp() not implemented, to be done in subclass ' + str(type(self)))
    def plot(self):
        """plot data (not implemented)"""
        print('method BaseDataLogger.plot() is not implemented, to be done in subclass ' + str(type(self)))
    def data(self):
        """return logged data in a dictionary (not implemented)"""
        print('method BaseDataLogger.data() is not implemented, to be done in subclass ' + str(type(self)))
class BaseDataLogger(object):
    """"abstract" base class for a data logger that can be used with an `OOOptimizer`"""
    def add(self, optim=None, more_data=[]):
        """abstract method, add a "data point" from the state of `optim` into the
        logger, the argument `optim` can be omitted if it was `register()`-ed before,
        acts like an event handler"""
        raise NotImplementedError()
    def register(self, optim):
        """abstract method, register an optimizer `optim`, only needed if `add()` is
        called without a value for the `optim` argument"""
        self.optim = optim
    def disp(self):
        """display some data trace (not implemented)"""
        print('method BaseDataLogger.disp() not implemented, to be done in subclass ' + str(type(self)))
    def plot(self):
        """plot data (not implemented)"""
        print('method BaseDataLogger.plot() is not implemented, to be done in subclass ' + str(type(self)))
    def data(self):
        """return logged data in a dictionary (not implemented)"""
        print('method BaseDataLogger.data() is not implemented, to be done in subclass ' + str(type(self)))

#_____________________________________________________________________
#_____________________________________________________________________
#
class CMADataLogger(BaseDataLogger):  # might become a dict at some point
    """data logger for class `CMAEvolutionStrategy`. The logger is
    identified by its name prefix and writes or reads according
    data files.

    Examples
    ========
    ::

        import cma
        es = cma.CMAEvolutionStrategy(...)
        data = cma.CMADataLogger().register(es)
        while not es.stop():
            ...
            data.add()  # add can also take an argument

        data.plot() # or a short cut can be used:
        cma.plot()  # plot data from logger with default name


        data2 = cma.CMADataLogger(another_filename_prefix).load()
        data2.plot()
        data2.disp()

    ::

        import cma
        from pylab import *
        res = cma.fmin(cma.Fcts.sphere, rand(10), 1e-0)
        dat = res[-1]  # the CMADataLogger
        dat.load()  # by "default" data are on disk
        semilogy(dat.f[:,0], dat.f[:,5])  # plot f versus iteration, see file header
        show()

    Details
    =======
    After loading data, the logger has the attributes `xmean`, `xrecent`, `std`, `f`, and `D`,
    corresponding to xmean, xrecentbest, stddev, fit, and axlen filename trails.

    :See: `disp()`, `plot()`

    """
    default_prefix = 'outcmaes'
    # names = ('axlen','fit','stddev','xmean','xrecentbest')
    # key_names_with_annotation = ('std', 'xmean', 'xrecent')

    def __init__(self, name_prefix=default_prefix, modulo=1, append=False):
        """initialize logging of data from a `CMAEvolutionStrategy` instance,
        default modulo expands to 1 == log with each call

        """
        # super(CMAData, self).__init__({'iter':[], 'stds':[], 'D':[], 'sig':[], 'fit':[], 'xm':[]})
        # class properties:
        self.file_names = ('axlen','fit','stddev','xmean','xrecentbest') # used in load, however hard-coded in add
        self.key_names = ('D', 'f', 'std', 'xmean', 'xrecent') # used in load, however hard-coded in plot
        self.key_names_with_annotation = ('std', 'xmean', 'xrecent') # used in load
        self.modulo = modulo  # allows calling with None
        self.append = append
        self.counter = 0  # number of calls of add, should initial value depend on `append`?
        self.name_prefix = name_prefix if name_prefix else CMADataLogger.default_prefix
        if type(self.name_prefix) == CMAEvolutionStrategy:
            self.name_prefix = self.name_prefix.opts.eval('verb_filenameprefix')
        self.registered = False

    def register(self, es, append=None, modulo=None):
        """register a `CMAEvolutionStrategy` instance for logging,
        ``append=True`` appends to previous data logged under the same name,
        by default previous data are overwritten.

        """
        if type(es) != CMAEvolutionStrategy:
            raise TypeError("only class CMAEvolutionStrategy can be registered for logging")
        self.es = es
        if append is not None:
            self.append = append
        if modulo is not None:
            self.modulo = modulo
        if not self.append and self.modulo != 0:
            self.initialize()  # write file headers
        self.registered = True
        return self

    def initialize(self, modulo=None):
        """reset logger, overwrite original files, `modulo`: log only every modulo call"""
        if modulo is not None:
            self.modulo = modulo
        try:
            es = self.es  # must have been registered
        except AttributeError:
            pass  # TODO: revise usage of es... that this can pass
            raise _Error('call register() before initialize()')

        self.counter = 0  # number of calls of add

        # write headers for output
        fn = self.name_prefix + 'fit.dat'
        strseedtime = 'seed=%d, %s' % (es.opts['seed'], time.asctime())

        try:
            with open(fn, 'w') as f:
                f.write('% # columns="iteration, evaluation, sigma, axis ratio, ' +
                        'bestever, best, median, worst objective function value, ' +
                        'further objective values of best", ' +
                        strseedtime +
                        # strftime("%Y/%m/%d %H:%M:%S", localtime()) + # just asctime() would do
                        '\n')
        except (IOError, OSError):
            print('could not open file ' + fn)

        fn = self.name_prefix + 'axlen.dat'
        try:
            f = open(fn, 'w')
            f.write('%  columns="iteration, evaluation, sigma, max axis length, ' +
                    ' min axis length, all principle axes lengths ' +
                    ' (sorted square roots of eigenvalues of C)", ' +
                    strseedtime +
                    '\n')
            f.close()
        except (IOError, OSError):
            print('could not open file ' + fn)
        finally:
            f.close()
        fn = self.name_prefix + 'stddev.dat'
        try:
            f = open(fn, 'w')
            f.write('% # columns=["iteration, evaluation, sigma, void, void, ' +
                    ' stds==sigma*sqrt(diag(C))", ' +
                    strseedtime +
                    '\n')
            f.close()
        except (IOError, OSError):
            print('could not open file ' + fn)
        finally:
            f.close()

        fn = self.name_prefix + 'xmean.dat'
        try:
            with open(fn, 'w') as f:
                f.write('% # columns="iteration, evaluation, void, void, void, xmean", ' +
                        strseedtime)
                f.write(' # scaling_of_variables: ')
                if np.size(es.gp.scales) > 1:
                    f.write(' '.join(map(str, es.gp.scales)))
                else:
                    f.write(str(es.gp.scales))
                f.write(', typical_x: ')
                if np.size(es.gp.typical_x) > 1:
                    f.write(' '.join(map(str, es.gp.typical_x)))
                else:
                    f.write(str(es.gp.typical_x))
                f.write('\n')
                f.close()
        except (IOError, OSError):
            print('could not open/write file ' + fn)

        fn = self.name_prefix + 'xrecentbest.dat'
        try:
            with open(fn, 'w') as f:
                f.write('% # iter+eval+sigma+0+fitness+xbest, ' +
                        strseedtime +
                        '\n')
        except (IOError, OSError):
            print('could not open/write file ' + fn)

        return self
    # end def __init__

    def load(self, filenameprefix=None):
        """loads data from files written and return a data dictionary, *not*
        a prerequisite for using `plot()` or `disp()`.

        Argument `filenameprefix` is the filename prefix of data to be loaded (five files),
        by default ``'outcmaes'``.

        Return data dictionary with keys `xrecent`, `xmean`, `f`, `D`, `std`

        """
        if not filenameprefix:
            filenameprefix = self.name_prefix
        for i in xrange(len(self.file_names)):
            fn = filenameprefix + self.file_names[i] + '.dat'
            try:
                self.__dict__[self.key_names[i]] = _fileToMatrix(fn)
            except:
                print('WARNING: reading from file "' + fn + '" failed')
            if self.key_names[i] in self.key_names_with_annotation:
                self.__dict__[self.key_names[i]].append(self.__dict__[self.key_names[i]][-1])  # copy last row to later fill in annotation position for display
            self.__dict__[self.key_names[i]] = array(self.__dict__[self.key_names[i]], copy=False)
        return self

    def add(self, es=None, more_data=[], modulo=None): # TODO: find a different way to communicate current x and f
        """append some logging data from `CMAEvolutionStrategy` class instance `es`,
        if ``number_of_times_called % modulo`` equals to zero, never if ``modulo==0``.

        The sequence ``more_data`` must always have the same length.

        When used for a different optimizer class, this function can be
        (easily?) adapted by changing the assignments under INTERFACE
        in the implemention.

        """
        self.counter += 1
        mod = modulo if modulo is not None else self.modulo
        if mod == 0 or (self.counter > 3 and self.counter % mod):
            return
        if es is None:
            try:
                es = self.es  # must have been registered
            except AttributeError :
                raise _Error('call `add` with argument `es` or ``register(es)`` before ``add()``')
        elif not self.registered:
            self.register(es) # calls initialize

        # --- INTERFACE, can be changed if necessary ---
        if type(es) is not CMAEvolutionStrategy: # not necessary
            print('WARNING: <type \'CMAEvolutionStrategy\'> expected, found '
                            + str(type(es)) + ' in method CMADataLogger.add')
        evals = es.countevals
        iteration = es.countiter
        sigma = es.sigma
        axratio = es.D.max()/es.D.min()
        xmean = es.mean # TODO: should be optionally phenotype?
        fmean_noise_free = es.fmean_noise_free
        fmean = es.fmean
        try:
            besteverf = es.best.f
            bestf = es.fit.fit[0]
            medianf = es.fit.fit[es.sp.popsize//2]
            worstf = es.fit.fit[-1]
        except:
            if self.counter > 1: # first call without f-values is OK
                raise
        try:
            xrecent = es.best.last.x
        except:
            xrecent = None
        maxD = es.D.max()
        minD = es.D.min()
        diagD = es.D
        diagC = es.sigma*es.sigma_vec*sqrt(es.dC)
        more_to_write = es.more_to_write
        es.more_to_write = []
        # --- end interface ---

        try:

            # fit
            if self.counter > 1:
                fn = self.name_prefix + 'fit.dat'
                with open(fn, 'a') as f:
                    f.write(str(iteration) + ' '
                            + str(evals) + ' '
                            + str(sigma) + ' '
                            + str(axratio) + ' '
                            + str(besteverf) + ' '
                            + '%.16e' % bestf + ' '
                            + str(medianf) + ' '
                            + str(worstf) + ' '
                            # + str(es.sp.popsize) + ' '
                            # + str(10**es.noiseS) + ' '
                            # + str(es.sp.cmean) + ' '
                            + ' '.join(str(i) for i in more_to_write)
                            + ' '.join(str(i) for i in more_data)
                            + '\n')
            # axlen
            fn = self.name_prefix + 'axlen.dat'
            with open(fn, 'a') as f:  # does not rely on reference counting
                f.write(str(iteration) + ' '
                        + str(evals) + ' '
                        + str(sigma) + ' '
                        + str(maxD) + ' '
                        + str(minD) + ' '
                        + ' '.join(map(str, diagD))
                        + '\n')
            # stddev
            fn = self.name_prefix + 'stddev.dat'
            with open(fn, 'a') as f:
                f.write(str(iteration) + ' '
                        + str(evals) + ' '
                        + str(sigma) + ' '
                        + '0 0 '
                        + ' '.join(map(str, diagC))
                        + '\n')
            # xmean
            fn = self.name_prefix + 'xmean.dat'
            with open(fn, 'a') as f:
                if iteration < 1: # before first iteration
                    f.write('0 0 0 0 0 '
                            + ' '.join(map(str, xmean))
                            + '\n')
                else:
                    f.write(str(iteration) + ' '
                            + str(evals) + ' '
                            # + str(sigma) + ' '
                            + '0 '
                            + str(fmean_noise_free) + ' '
                            + str(fmean) + ' '  # TODO: this does not make sense
                            # TODO should be optional the phenotyp?
                            + ' '.join(map(str, xmean))
                            + '\n')
            # xrecent
            fn = self.name_prefix + 'xrecentbest.dat'
            if iteration > 0 and xrecent is not None:
                with open(fn, 'a') as f:
                    f.write(str(iteration) + ' '
                            + str(evals) + ' '
                            + str(sigma) + ' '
                            + '0 '
                            + str(bestf) + ' '
                            + ' '.join(map(str, xrecent))
                            + '\n')

        except (IOError, OSError):
            if iteration <= 1:
                print('could not open/write file')

    def closefig(self):
        pylab.close(self.fighandle)

    def save(self, nameprefix, switch=False):
        """saves logger data to a different set of files, for
        ``switch=True`` also the loggers name prefix is switched to
        the new value

        """
        if not nameprefix or type(nameprefix) is not str:
            _Error('filename prefix must be a nonempty string')

        if nameprefix == self.default_prefix:
            _Error('cannot save to default name "' + nameprefix + '...", chose another name')

        if nameprefix == self.name_prefix:
            return

        for name in CMADataLogger.names:
            open(nameprefix+name+'.dat', 'w').write(open(self.name_prefix+name+'.dat').read())

        if switch:
            self.name_prefix = nameprefix

    def plot(self, fig=None, iabscissa=1, iteridx=None, plot_mean=True,  # TODO: plot_mean default should be False
             foffset=1e-19, x_opt = None, fontsize=10):
        """
        plot data from a `CMADataLogger` (using the files written by the logger).

        Arguments
        ---------
            `fig`
                figure number, by default 325
            `iabscissa`
                ``0==plot`` versus iteration count,
                ``1==plot`` versus function evaluation number
            `iteridx`
                iteration indices to plot

        Return `CMADataLogger` itself.

        Examples
        --------
        ::

            import cma
            logger = cma.CMADataLogger()  # with default name
            # try to plot the "default logging" data (e.g. from previous fmin calls)
            logger.plot() # to continue you might need to close the pop-up window
                          # once and call plot() again.
                          # This behavior seems to disappear in subsequent
                          # calls of plot(). Also using ipython with -pylab
                          # option might help.
            cma.savefig('fig325.png')  # save current figure
            logger.closefig()

        Dependencies: matlabplotlib/pylab.

        """

        dat = self.load(self.name_prefix)

        try:
            # pylab: prodedural interface for matplotlib
            from  matplotlib.pylab import figure, ioff, ion, subplot, semilogy, hold, plot, grid, \
                 axis, title, text, xlabel, isinteractive, draw, gcf

        except ImportError:
            ImportError('could not find matplotlib.pylab module, function plot() is not available')
            return

        if fontsize and pylab.rcParams['font.size'] != fontsize:
            print('global variable pylab.rcParams[\'font.size\'] set (from ' +
                  str(pylab.rcParams['font.size']) + ') to ' + str(fontsize))
            pylab.rcParams['font.size'] = fontsize  # subtracted in the end, but return can happen inbetween

        if fig:
            figure(fig)
        else:
            figure(325)
            # show()  # should not be necessary
        self.fighandle = gcf()  # fighandle.number

        if iabscissa not in (0,1):
            iabscissa = 1
        interactive_status = isinteractive()
        ioff() # prevents immediate drawing

        dat.x = dat.xmean    # this is the genotyp
        if not plot_mean:
            try:
                dat.x = dat.xrecent
            except:
                pass
        if len(dat.x) < 2:
            print('not enough data to plot')
            return {}

        if iteridx is not None:
            dat.f = dat.f[np.where([x in iteridx for x in dat.f[:,0]])[0],:]
            dat.D = dat.D[np.where([x in iteridx for x in dat.D[:,0]])[0],:]
            iteridx.append(dat.x[-1,1])  # last entry is artificial
            dat.x = dat.x[np.where([x in iteridx for x in dat.x[:,0]])[0],:]
            dat.std = dat.std[np.where([x in iteridx for x in dat.std[:,0]])[0],:]

        if iabscissa == 0:
            xlab = 'iterations'
        elif iabscissa == 1:
            xlab = 'function evaluations'

        # use fake last entry in x and std for line extension-annotation
        if dat.x.shape[1] < 100:
            minxend = int(1.06*dat.x[-2, iabscissa])
            # write y-values for individual annotation into dat.x
            dat.x[-1, iabscissa] = minxend  # TODO: should be ax[1]
            idx = np.argsort(dat.x[-2,5:])
            idx2 = np.argsort(idx)
            if x_opt is None:
                dat.x[-1,5+idx] = np.linspace(np.min(dat.x[:,5:]),
                            np.max(dat.x[:,5:]), dat.x.shape[1]-5)
            else:
                dat.x[-1,5+idx] = np.logspace(np.log10(np.min(abs(dat.x[:,5:]))),
                            np.log10(np.max(abs(dat.x[:,5:]))), dat.x.shape[1]-5)
        else:
            minxend = 0

        if len(dat.f) == 0:
            print('nothing to plot')
            return

        # not in use anymore, see formatter above
        # xticklocs = np.arange(5) * np.round(minxend/4., -int(np.log10(minxend/4.)))

        # dfit(dfit<1e-98) = NaN;

        ioff() # turns update off

        # TODO: if abscissa==0 plot in chunks, ie loop over subsets where dat.f[:,0]==countiter is monotonous

        subplot(2,2,1)
        self.plotdivers(dat, iabscissa, foffset)

        # TODO: modularize also the remaining subplots
        subplot(2,2,2)
        hold(False)
        if x_opt is not None:  # TODO: differentate neg and pos?
            semilogy(dat.x[:, iabscissa], abs(dat.x[:,5:]) - x_opt, '-')
        else:
            plot(dat.x[:, iabscissa], dat.x[:,5:],'-')
        hold(True)
        grid(True)
        ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        axis(ax)
        ax[1] -= 1e-6
        if dat.x.shape[1] < 100:
            yy = np.linspace(ax[2]+1e-6, ax[3]-1e-6, dat.x.shape[1]-5)
            #yyl = np.sort(dat.x[-1,5:])
            idx = np.argsort(dat.x[-1,5:])
            idx2 = np.argsort(idx)
            if x_opt is not None:
                semilogy([dat.x[-1, iabscissa], ax[1]], [abs(dat.x[-1,5:]), yy[idx2]], 'k-') # line from last data point
                semilogy(np.dot(dat.x[-2, iabscissa],[1,1]), array([ax[2]+1e-6, ax[3]-1e-6]), 'k-')
            else:
                # plot([dat.x[-1, iabscissa], ax[1]], [dat.x[-1,5:], yy[idx2]], 'k-') # line from last data point
                plot(np.dot(dat.x[-2, iabscissa],[1,1]), array([ax[2]+1e-6, ax[3]-1e-6]), 'k-')
            # plot(array([dat.x[-1, iabscissa], ax[1]]),
            #      reshape(array([dat.x[-1,5:], yy[idx2]]).flatten(), (2,4)), '-k')
            for i in range(len(idx)):
                # TODOqqq: annotate phenotypic value!?
                # text(ax[1], yy[i], 'x(' + str(idx[i]) + ')=' + str(dat.x[-2,5+idx[i]]))
                text(dat.x[-1,iabscissa], dat.x[-1,5+i], 'x(' + str(i) + ')=' + str(dat.x[-2,5+i]))

        i = 2  # find smallest i where iteration count differs (in case the same row appears twice)
        while i < len(dat.f) and dat.f[-i][0] == dat.f[-1][0]:
            i += 1
        title('Object Variables (' + ('mean' if plot_mean else 'curr best') +
                ', ' + str(dat.x.shape[1]-5) + '-D, popsize~' +
                (str(int((dat.f[-1][1] - dat.f[-i][1]) / (dat.f[-1][0] - dat.f[-i][0])))
                    if len(dat.f.T[0]) > 1 and dat.f[-1][0] > dat.f[-i][0] else 'NA')
                + ')')
        # pylab.xticks(xticklocs)

        # Scaling
        subplot(2,2,3)
        hold(False)
        semilogy(dat.D[:, iabscissa], dat.D[:,5:], '-b')
        hold(True)
        grid(True)
        ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        axis(ax)
        title('Scaling (All Main Axes)')
        # pylab.xticks(xticklocs)
        xlabel(xlab)

        # standard deviations
        subplot(2,2,4)
        hold(False)
        # remove sigma from stds (graphs become much better readible)
        dat.std[:,5:] = np.transpose(dat.std[:,5:].T / dat.std[:,2].T)
        # ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        # axis(ax)
        if 1 < 2 and dat.std.shape[1] < 100:
            # use fake last entry in x and std for line extension-annotation
            minxend = int(1.06*dat.x[-2, iabscissa])
            dat.std[-1, iabscissa] = minxend  # TODO: should be ax[1]
            idx = np.argsort(dat.std[-2,5:])
            idx2 = np.argsort(idx)
            dat.std[-1,5+idx] = np.logspace(np.log10(np.min(dat.std[:,5:])),
                            np.log10(np.max(dat.std[:,5:])), dat.std.shape[1]-5)

            dat.std[-1, iabscissa] = minxend  # TODO: should be ax[1]
            yy = np.logspace(np.log10(ax[2]), np.log10(ax[3]), dat.std.shape[1]-5)
            #yyl = np.sort(dat.std[-1,5:])
            idx = np.argsort(dat.std[-1,5:])
            idx2 = np.argsort(idx)
            # plot(np.dot(dat.std[-2, iabscissa],[1,1]), array([ax[2]+1e-6, ax[3]-1e-6]), 'k-') # vertical separator
            # vertical separator
            plot(np.dot(dat.std[-2, iabscissa],[1,1]), array([np.min(dat.std[-2,5:]), np.max(dat.std[-2,5:])]), 'k-')
            hold(True)
            # plot([dat.std[-1, iabscissa], ax[1]], [dat.std[-1,5:], yy[idx2]], 'k-') # line from last data point
            for i in xrange(len(idx)):
                # text(ax[1], yy[i], ' '+str(idx[i]))
                text(dat.std[-1, iabscissa], dat.std[-1, 5+i], ' '+str(i))
        semilogy(dat.std[:, iabscissa], dat.std[:,5:], '-')
        grid(True)
        title('Standard Deviations in All Coordinates')
        # pylab.xticks(xticklocs)
        xlabel(xlab)
        draw()  # does not suffice
        if interactive_status:
            ion()  # turns interactive mode on (again)
            draw()
        show()

        return self


    #____________________________________________________________
    #____________________________________________________________
    #
    @staticmethod
    def plotdivers(dat, iabscissa, foffset):
        """helper function for `plot()` that plots all what is
        in the upper left subplot like fitness, sigma, etc.

        Arguments
        ---------
            `iabscissa` in ``(0,1)``
                0==versus fevals, 1==versus iteration
            `foffset`
                offset to fitness for log-plot

         :See: `plot()`

        """
        from  matplotlib.pylab import semilogy, hold, grid, \
                 axis, title, text
        fontsize = pylab.rcParams['font.size']

        hold(False)

        dfit = dat.f[:,5]-min(dat.f[:,5])
        dfit[dfit<1e-98] = np.NaN

        if dat.f.shape[1] > 7:
            # semilogy(dat.f[:, iabscissa], abs(dat.f[:,[6, 7, 10, 12]])+foffset,'-k')
            semilogy(dat.f[:, iabscissa], abs(dat.f[:,[6, 7]])+foffset,'-k')
            hold(True)

        # (larger indices): additional fitness data, for example constraints values
        if dat.f.shape[1] > 8:
            # dd = abs(dat.f[:,7:]) + 10*foffset
            # dd = np.where(dat.f[:,7:]==0, np.NaN, dd) # cannot be
            semilogy(dat.f[:, iabscissa], np.abs(dat.f[:,8:]) + 10*foffset, 'm')
            hold(True)

        idx = np.where(dat.f[:,5]>1e-98)[0]  # positive values
        semilogy(dat.f[idx, iabscissa], dat.f[idx,5]+foffset, '.b')
        hold(True)
        grid(True)

        idx = np.where(dat.f[:,5] < -1e-98)  # negative values
        semilogy(dat.f[idx, iabscissa], abs(dat.f[idx,5])+foffset,'.r')

        semilogy(dat.f[:, iabscissa],abs(dat.f[:,5])+foffset,'-b')
        semilogy(dat.f[:, iabscissa], dfit, '-c')

        if 11 < 3:  # delta-fitness as points
            dfit = dat.f[1:, 5] - dat.f[:-1,5]  # should be negative usually
            semilogy(dat.f[1:,iabscissa],  # abs(fit(g) - fit(g-1))
                np.abs(dfit)+foffset, '.c')
            i = dfit > 0
            # print(np.sum(i) / float(len(dat.f[1:,iabscissa])))
            semilogy(dat.f[1:,iabscissa][i],  # abs(fit(g) - fit(g-1))
                np.abs(dfit[i])+foffset, '.r')

        # overall minimum
        i = np.argmin(dat.f[:,5])
        semilogy(dat.f[i, iabscissa]*np.ones(2), dat.f[i,5]*np.ones(2), 'rd')
        # semilogy(dat.f[-1, iabscissa]*np.ones(2), dat.f[-1,4]*np.ones(2), 'rd')

        # AR and sigma
        semilogy(dat.f[:, iabscissa], dat.f[:,3], '-r') # AR
        semilogy(dat.f[:, iabscissa], dat.f[:,2],'-g') # sigma
        semilogy(dat.std[:-1, iabscissa], np.vstack([list(map(max, dat.std[:-1,5:])), list(map(min, dat.std[:-1,5:]))]).T,
                     '-m', linewidth=2)
        text(dat.std[-2, iabscissa], max(dat.std[-2, 5:]), 'max std', fontsize=fontsize)
        text(dat.std[-2, iabscissa], min(dat.std[-2, 5:]), 'min std', fontsize=fontsize)
        ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        axis(ax)
        text(ax[0]+0.01, ax[2], # 10**(log10(ax[2])+0.05*(log10(ax[3])-log10(ax[2]))),
             '.f_recent=' + repr(dat.f[-1,5]) )

        # title('abs(f) (blue), f-min(f) (cyan), Sigma (green), Axis Ratio (red)')
        title('blue:abs(f), cyan:f-min(f), green:sigma, red:axis ratio', fontsize=fontsize-1)
        # pylab.xticks(xticklocs)


    def downsampling(self, factor=10, first=3, switch=True):
        """
        rude downsampling of a `CMADataLogger` data file by `factor`, keeping
        also the first `first` entries. This function is a stump and subject
        to future changes.

        Arguments
        ---------
           - `factor` -- downsampling factor
           - `first` -- keep first `first` entries
           - `switch` -- switch the new logger name to oldname+'down'

        Details
        -------
        ``self.name_prefix+'down'`` files are written

        Example
        -------
        ::

            import cma
            cma.downsampling()  # takes outcmaes* files
            cma.plot('outcmaesdown')

        """
        newprefix = self.name_prefix + 'down'
        for name in CMADataLogger.names:
            f = open(newprefix+name+'.dat','w')
            iline = 0
            cwritten = 0
            for line in open(self.name_prefix+name+'.dat'):
                if iline < first or iline % factor == 0:
                    f.write(line)
                    cwritten += 1
                iline += 1
            f.close()
            print('%d' % (cwritten) + ' lines written in ' + newprefix+name+'.dat')
        if switch:
            self.name_prefix += 'down'
        return self

    #____________________________________________________________
    #____________________________________________________________
    #
    def disp(self, idx=100):  # r_[0:5,1e2:1e9:1e2,-10:0]):
        """displays selected data from (files written by) the class `CMADataLogger`.

        Arguments
        ---------
           `idx`
               indices corresponding to rows in the data file;
               if idx is a scalar (int), the first two, then every idx-th,
               and the last three rows are displayed. Too large index values are removed.

        Example
        -------
        >>> import cma, numpy as np
        >>> res = cma.fmin(cma.fcts.elli, 7 * [0.1], 1, verb_disp=1e9)  # generate data
        >>> assert res[1] < 1e-9
        >>> assert res[2] < 4400
        >>> l = cma.CMADataLogger()  # == res[-1], logger with default name, "points to" above data
        >>> l.disp([0,-1])  # first and last
        >>> l.disp(20)  # some first/last and every 20-th line
        >>> l.disp(np.r_[0:999999:100, -1]) # every 100-th and last
        >>> l.disp(np.r_[0, -10:0]) # first and ten last
        >>> cma.disp(l.name_prefix, np.r_[0::100, -10:])  # the same as l.disp(...)

        Details
        -------
        The data line with the best f-value is displayed as last line.

        :See: `disp()`

        """

        filenameprefix=self.name_prefix

        def printdatarow(dat, iteration):
            """print data of iteration i"""
            i = np.where(dat.f[:, 0] == iteration)[0][0]
            j = np.where(dat.std[:, 0] == iteration)[0][0]
            print('%5d' % (int(dat.f[i,0])) + ' %6d' % (int(dat.f[i,1])) + ' %.14e' % (dat.f[i,5]) +
                  ' %5.1e' % (dat.f[i,3]) +
                  ' %6.2e' % (max(dat.std[j,5:])) + ' %6.2e' % min(dat.std[j,5:]))

        dat = CMADataLogger(filenameprefix).load()
        ndata = dat.f.shape[0]

        # map index to iteration number, is difficult if not all iteration numbers exist
        # idx = idx[np.where(map(lambda x: x in dat.f[:,0], idx))[0]] # TODO: takes pretty long
        # otherwise:
        if idx is None:
            idx = 100
        if np.isscalar(idx):
            # idx = np.arange(0, ndata, idx)
            if idx:
                idx = np.r_[0, 1, idx:ndata-3:idx, -3:0]
            else:
                idx = np.r_[0, 1, -3:0]

        idx = array(idx)
        idx = idx[idx<ndata]
        idx = idx[-idx<=ndata]
        iters = dat.f[idx, 0]
        idxbest = np.argmin(dat.f[:,5])
        iterbest = dat.f[idxbest, 0]

        if len(iters) == 1:
            printdatarow(dat, iters[0])
        else:
            self.disp_header()
            for i in iters:
                printdatarow(dat, i)
            self.disp_header()
            printdatarow(dat, iterbest)
        sys.stdout.flush()
    def disp_header(self):
        heading = 'Iterat Nfevals  function value    axis ratio maxstd   minstd'
        print(heading)

# end class CMADataLogger

#____________________________________________________________
#____________________________________________________________
#
#_____________________________________________________________________
#_____________________________________________________________________
#
class DEAPCMADataLogger(BaseDataLogger):  # might become a dict at some point
    """data logger for class `Strategy`. The logger is
    identified by its name prefix and writes or reads according
    data files.

    Examples
    ========
    ::

        import cma_logger
        es = deap.cma.Strategy(...)
        data = cma_logger.DEAPCMADataLogger().register(es)
        while not es.stop():
            ...
            data.add(fitness_values)  # add can also take `es` as additional argument

        data.plot() # or a short cut can be used:
        cma.plot()  # plot data from logger with default name


        data2 = cma_logger.DEAPCMADataLogger(another_filename_prefix).load()
        data2.plot()
        data2.disp()

    ::

        import cma
        from pylab import *
        res = cma.fmin(cma.Fcts.sphere, rand(10), 1e-0)
        dat = res[-1]  # the CMADataLogger
        dat.load()  # by "default" data are on disk
        semilogy(dat.f[:,0], dat.f[:,5])  # plot f versus iteration, see file header
        show()

    Details
    =======
    After loading data, the logger has the attributes `xmean`, `xrecent`, `std`, `f`, and `D`,
    corresponding to xmean, xrecentbest, stddev, fit, and axlen filename trails.

    :See: `disp()`, `plot()`

    """
    default_prefix = 'outcmaes'
    names = ('axlen','fit','stddev','xmean') # ,'xrecentbest')
    key_names_with_annotation = ('std', 'xmean')

    def __init__(self, name_prefix=default_prefix, modulo=1, append=False):
        """initialize logging of data from a `CMAEvolutionStrategy` instance,
        default modulo expands to 1 == log with each call

        """
        # super(CMAData, self).__init__({'iter':[], 'stds':[], 'D':[], 'sig':[], 'fit':[], 'xm':[]})
        # class properties:
        self.counter = 0  # number of calls of add
        self.best_fitness = np.inf
        self.modulo = modulo  # allows calling with None
        self.append = append
        self.name_prefix = name_prefix if name_prefix else CMADataLogger.default_prefix
        if type(self.name_prefix) == CMAEvolutionStrategy:
            self.name_prefix = self.name_prefix.opts.eval('verb_filenameprefix')
        self.registered = False

    def register(self, es, append=None, modulo=None):
        """register a `CMAEvolutionStrategy` instance for logging,
        ``append=True`` appends to previous data logged under the same name,
        by default previous data are overwritten.

        """
        self.es = es
        if append is not None:
            self.append = append
        if modulo is not None:
            self.modulo = modulo
        if not self.append and self.modulo != 0:
            self.initialize()  # write file headers
        self.registered = True
        return self

    def initialize(self, modulo=None):
        """reset logger, overwrite original files, `modulo`: log only every modulo call"""
        if modulo is not None:
            self.modulo = modulo
        try:
            es = self.es  # must have been registered
        except AttributeError:
            pass  # TODO: revise usage of es... that this can pass
            raise _Error('call register() before initialize()')

        # write headers for output
        fn = self.name_prefix + 'fit.dat'
        if 11 < 3:
            strseedtime = 'seed=%d, %s' % (es.opts['seed'], time.asctime())
        else:
            strseedtime = 'seed=unkown, %s' % (time.asctime())

        try:
            with open(fn, 'w') as f:
                f.write('% # columns="iteration, evaluation, sigma, axis ratio, ' +
                        'bestever, best, median, worst objective function value, ' +
                        'further objective values of best", ' +
                        strseedtime +
                        # strftime("%Y/%m/%d %H:%M:%S", localtime()) + # just asctime() would do
                        '\n')
        except (IOError, OSError):
            print('could not open file ' + fn)

        fn = self.name_prefix + 'axlen.dat'
        try:
            f = open(fn, 'w')
            f.write('%  columns="iteration, evaluation, sigma, max axis length, ' +
                    ' min axis length, all principle axes lengths ' +
                    ' (sorted square roots of eigenvalues of C)", ' +
                    strseedtime +
                    '\n')
            f.close()
        except (IOError, OSError):
            print('could not open file ' + fn)
        finally:
            f.close()
        fn = self.name_prefix + 'stddev.dat'
        try:
            f = open(fn, 'w')
            f.write('% # columns=["iteration, evaluation, sigma, void, void, ' +
                    ' stds==sigma*sqrt(diag(C))", ' +
                    strseedtime +
                    '\n')
            f.close()
        except (IOError, OSError):
            print('could not open file ' + fn)
        finally:
            f.close()

        fn = self.name_prefix + 'xmean.dat'
        try:
            with open(fn, 'w') as f:
                f.write('% # columns="iteration, evaluation, void, void, void, xmean", ' +
                        strseedtime)
                if 11 < 3:
                    f.write(' # scaling_of_variables: ')
                    if np.size(es.gp.scales) > 1:
                        f.write(' '.join(map(str, es.gp.scales)))
                    else:
                        f.write(str(es.gp.scales))
                    f.write(', typical_x: ')
                    if np.size(es.gp.typical_x) > 1:
                        f.write(' '.join(map(str, es.gp.typical_x)))
                    else:
                        f.write(str(es.gp.typical_x))
                f.write('\n')
                f.close()
        except (IOError, OSError):
            print('could not open/write file ' + fn)

        if 11 < 3:
            fn = self.name_prefix + 'xrecentbest.dat'
            try:
                with open(fn, 'w') as f:
                    f.write('% # iter+eval+sigma+0+fitness+xbest, ' +
                            strseedtime +
                            '\n')
            except (IOError, OSError):
                print('could not open/write file ' + fn)

        return self
    # end def __init__

    def load(self, filenameprefix=None):
        """loads data from files written and return a data dictionary, *not*
        a prerequisite for using `plot()` or `disp()`.

        Argument `filenameprefix` is the filename prefix of data to be loaded (five files),
        by default ``'outcmaes'``.

        Return data dictionary with keys `xrecent`, `xmean`, `f`, `D`, `std`

        """
        if not filenameprefix:
            filenameprefix = self.name_prefix
        dat = self  # historical
        # dat.xrecent = _fileToMatrix(filenameprefix + 'xrecentbest.dat')
        dat.xmean = _fileToMatrix(filenameprefix + 'xmean.dat')
        dat.std = _fileToMatrix(filenameprefix + 'stddev' + '.dat')
        # a hack to later write something into the last entry
        for key in ['xmean', 'std']:  # 'xrecent',
            dat.__dict__[key].append(dat.__dict__[key][-1])  # copy last row to later fill in annotation position for display
            dat.__dict__[key] = array(dat.__dict__[key], copy=False)
        dat.f = array(_fileToMatrix(filenameprefix + 'fit.dat'))
        dat.D = array(_fileToMatrix(filenameprefix + 'axlen' + '.dat'))
        return dat


    def add(self, fitness_values, es=None, more_data=[], modulo=None): # TODO: find a different way to communicate current x and f
        """append some logging data from `CMAEvolutionStrategy` class instance `es`,
        if ``number_of_times_called % modulo`` equals to zero, never if ``modulo==0``.

        The sequence ``more_data`` must always have the same length.

        """
        self.counter += 1
        fitness_values = np.sort(fitness_values)
        if fitness_values[0] < self.best_fitness:
            self.best_fitness = fitness_values[0]
        mod = modulo if modulo is not None else self.modulo
        if mod == 0 or (self.counter > 3 and self.counter % mod):
            return
        if es is None:
            try:
                es = self.es  # must have been registered
            except AttributeError :
                raise _Error('call register() before add() or add(es)')
        elif not self.registered:
            self.register(es)

        if 11 < 3:
            try: # TODO: find a more decent interface to store and pass recent_x
                xrecent = es.best.last.x
            except:
                if self.counter == 2:  # by now a recent_x should be available
                    print('WARNING: es.out[\'recent_x\'] not found in CMADataLogger.add, count='
                          + str(self.counter))
        try:
            # fit
            if es.update_count > 0:
                # fit = es.fit.fit[0]  # TODO: where do we get the fitness from?
                fn = self.name_prefix + 'fit.dat'
                with open(fn, 'a') as f:
                    f.write(str(es.update_count) + ' '
                            + str(es.update_count * es.lambda_) + ' '
                            + str(es.sigma) + ' '
                            + str(es.diagD[-1]/es.diagD[0]) + ' '
                            + str(self.best_fitness) + ' '
                            + '%.16e' % fitness_values[0] + ' '
                            + str(fitness_values[es.lambda_//2]) + ' '
                            + str(fitness_values[-1]) + ' '
                            # + str(es.sp.popsize) + ' '
                            # + str(10**es.noiseS) + ' '
                            # + str(es.sp.cmean) + ' '
                            # + ' '.join(str(i) for i in es.more_to_write)
                            + ' '.join(str(i) for i in more_data)
                            + '\n')
                    # es.more_to_write = []
            # axlen
            fn = self.name_prefix + 'axlen.dat'
            with open(fn, 'a') as f:  # does not rely on reference counting
                f.write(str(es.update_count) + ' '
                        + str(es.update_count * es.lambda_) + ' '
                        + str(es.sigma) + ' '
                        + str(es.diagD[-1]) + ' '
                        + str(es.diagD[0]) + ' '
                        + ' '.join(map(str, es.diagD))
                        + '\n')
            # stddev
            fn = self.name_prefix + 'stddev.dat'
            with open(fn, 'a') as f:
                f.write(str(es.update_count) + ' '
                        + str(es.update_count * es.lambda_) + ' '
                        + str(es.sigma) + ' '
                        + '0 0 '
                        + ' '.join(map(str, es.sigma*np.sqrt([es.C[i][i] for i in xrange(es.dim)])))
                        + '\n')
            # xmean
            fn = self.name_prefix + 'xmean.dat'
            with open(fn, 'a') as f:
                if es.update_count < 1:
                    f.write('0 0 0 0 0 '
                            + ' '.join(map(str,
                                              # TODO should be optional the phenotyp?
                                              # es.gp.geno(es.x0)
                                              es.mean))
                            + '\n')
                else:
                    f.write(str(es.update_count) + ' '
                            + str(es.update_count * es.lambda_) + ' '
                            # + str(es.sigma) + ' '
                            + '0 0 0 '
                            # + str(es.fmean_noise_free) + ' '
                            # + str(es.fmean) + ' '  # TODO: this does not make sense
                            # TODO should be optional the phenotyp?
                            + ' '.join(map(str, es.centroid))
                            + '\n')
            # xrecent
            if 11 < 3:
                fn = self.name_prefix + 'xrecentbest.dat'
                if es.countiter > 0 and xrecent is not None:
                    with open(fn, 'a') as f:
                        f.write(str(es.countiter) + ' '
                                + str(es.countevals) + ' '
                                + str(es.sigma) + ' '
                                + '0 '
                                + str(es.fit.fit[0]) + ' '
                                + ' '.join(map(str, xrecent))
                                + '\n')

        except (IOError, OSError):
            if es.countiter == 1:
                print('could not open/write file')

    def closefig(self):
        pylab.close(self.fighandle)

    def save(self, nameprefix, switch=False):
        """saves logger data to a different set of files, for
        ``switch=True`` also the loggers name prefix is switched to
        the new value

        """
        if not nameprefix or type(nameprefix) is not str:
            _Error('filename prefix must be a nonempty string')

        if nameprefix == self.default_prefix:
            _Error('cannot save to default name "' + nameprefix + '...", chose another name')

        if nameprefix == self.name_prefix:
            return

        for name in CMADataLogger.names:
            open(nameprefix+name+'.dat', 'w').write(open(self.name_prefix+name+'.dat').read())

        if switch:
            self.name_prefix = nameprefix

    def plot(self, fig=None, iabscissa=1, iteridx=None, plot_mean=True,  # TODO: plot_mean default should be False
             foffset=1e-19, x_opt = None, fontsize=10):
        """
        plot data from a `CMADataLogger` (using the files written by the logger).

        Arguments
        ---------
            `fig`
                figure number, by default 325
            `iabscissa`
                ``0==plot`` versus iteration count,
                ``1==plot`` versus function evaluation number
            `iteridx`
                iteration indices to plot

        Return `CMADataLogger` itself.

        Examples
        --------
        ::

            import cma
            logger = cma.CMADataLogger()  # with default name
            # try to plot the "default logging" data (e.g. from previous fmin calls)
            logger.plot() # to continue you might need to close the pop-up window
                          # once and call plot() again.
                          # This behavior seems to disappear in subsequent
                          # calls of plot(). Also using ipython with -pylab
                          # option might help.
            cma.savefig('fig325.png')  # save current figure
            logger.closefig()

        Dependencies: matlabplotlib/pylab.

        """

        dat = self.load(self.name_prefix)

        try:
            # pylab: prodedural interface for matplotlib
            from  matplotlib.pylab import figure, ioff, ion, subplot, semilogy, hold, plot, grid, \
                 axis, title, text, xlabel, isinteractive, draw, gcf

        except ImportError:
            ImportError('could not find matplotlib.pylab module, function plot() is not available')
            return

        if fontsize and pylab.rcParams['font.size'] != fontsize:
            print('global variable pylab.rcParams[\'font.size\'] set (from ' +
                  str(pylab.rcParams['font.size']) + ') to ' + str(fontsize))
            pylab.rcParams['font.size'] = fontsize  # subtracted in the end, but return can happen inbetween

        if fig:
            figure(fig)
        else:
            figure(325)
            # show()  # should not be necessary
        self.fighandle = gcf()  # fighandle.number

        if iabscissa not in (0,1):
            iabscissa = 1
        interactive_status = isinteractive()
        ioff() # prevents immediate drawing

        if 11 < 3:
            dat.x = dat.xrecent
            if len(dat.x) < 2:
                print('not enough data to plot')
                return {}
        # if plot_mean:
        dat.x = dat.xmean    # this is the genotyp
        if iteridx is not None:
            dat.f = dat.f[np.where([x in iteridx for x in dat.f[:,0]])[0],:]
            dat.D = dat.D[np.where([x in iteridx for x in dat.D[:,0]])[0],:]
            iteridx.append(dat.x[-1,1])  # last entry is artificial
            dat.x = dat.x[np.where([x in iteridx for x in dat.x[:,0]])[0],:]
            dat.std = dat.std[np.where([x in iteridx for x in dat.std[:,0]])[0],:]

        if iabscissa == 0:
            xlab = 'iterations'
        elif iabscissa == 1:
            xlab = 'function evaluations'

        # use fake last entry in x and std for line extension-annotation
        if dat.x.shape[1] < 100:
            minxend = int(1.06*dat.x[-2, iabscissa])
            # write y-values for individual annotation into dat.x
            dat.x[-1, iabscissa] = minxend  # TODO: should be ax[1]
            idx = np.argsort(dat.x[-2,5:])
            idx2 = np.argsort(idx)
            if x_opt is None:
                dat.x[-1,5+idx] = np.linspace(np.min(dat.x[:,5:]),
                            np.max(dat.x[:,5:]), dat.x.shape[1]-5)
            else:
                dat.x[-1,5+idx] = np.logspace(np.log10(np.min(abs(dat.x[:,5:]))),
                            np.log10(np.max(abs(dat.x[:,5:]))), dat.x.shape[1]-5)
        else:
            minxend = 0

        if len(dat.f) == 0:
            print('nothing to plot')
            return

        # not in use anymore, see formatter above
        # xticklocs = np.arange(5) * np.round(minxend/4., -int(np.log10(minxend/4.)))

        # dfit(dfit<1e-98) = NaN;

        ioff() # turns update off

        # TODO: if abscissa==0 plot in chunks, ie loop over subsets where dat.f[:,0]==countiter is monotonous

        subplot(2,2,1)
        self.plotdivers(dat, iabscissa, foffset)

        # TODO: modularize also the remaining subplots
        subplot(2,2,2)
        hold(False)
        if x_opt is not None:  # TODO: differentate neg and pos?
            semilogy(dat.x[:, iabscissa], abs(dat.x[:,5:]) - x_opt, '-')
        else:
            plot(dat.x[:, iabscissa], dat.x[:,5:],'-')
        hold(True)
        grid(True)
        ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        axis(ax)
        ax[1] -= 1e-6
        if dat.x.shape[1] < 100:
            yy = np.linspace(ax[2]+1e-6, ax[3]-1e-6, dat.x.shape[1]-5)
            #yyl = np.sort(dat.x[-1,5:])
            idx = np.argsort(dat.x[-1,5:])
            idx2 = np.argsort(idx)
            if x_opt is not None:
                semilogy([dat.x[-1, iabscissa], ax[1]], [abs(dat.x[-1,5:]), yy[idx2]], 'k-') # line from last data point
                semilogy(np.dot(dat.x[-2, iabscissa],[1,1]), array([ax[2]+1e-6, ax[3]-1e-6]), 'k-')
            else:
                # plot([dat.x[-1, iabscissa], ax[1]], [dat.x[-1,5:], yy[idx2]], 'k-') # line from last data point
                plot(np.dot(dat.x[-2, iabscissa],[1,1]), array([ax[2]+1e-6, ax[3]-1e-6]), 'k-')
            # plot(array([dat.x[-1, iabscissa], ax[1]]),
            #      reshape(array([dat.x[-1,5:], yy[idx2]]).flatten(), (2,4)), '-k')
            for i in range(len(idx)):
                # TODOqqq: annotate phenotypic value!?
                # text(ax[1], yy[i], 'x(' + str(idx[i]) + ')=' + str(dat.x[-2,5+idx[i]]))
                text(dat.x[-1,iabscissa], dat.x[-1,5+i], 'x(' + str(i) + ')=' + str(dat.x[-2,5+i]))

        i = 2  # find smallest i where iteration count differs (in case the same row appears twice)
        while i < len(dat.f) and dat.f[-i][0] == dat.f[-1][0]:
            i += 1
        title('Object Variables (' + ('mean' if plot_mean else 'curr best') +
                ', ' + str(dat.x.shape[1]-5) + '-D, popsize~' +
                (str(int((dat.f[-1][1] - dat.f[-i][1]) / (dat.f[-1][0] - dat.f[-i][0])))
                    if len(dat.f.T[0]) > 1 and dat.f[-1][0] > dat.f[-i][0] else 'NA')
                + ')')
        # pylab.xticks(xticklocs)

        # Scaling
        subplot(2,2,3)
        hold(False)
        semilogy(dat.D[:, iabscissa], dat.D[:,5:], '-b')
        hold(True)
        grid(True)
        ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        axis(ax)
        title('Scaling (All Main Axes)')
        # pylab.xticks(xticklocs)
        xlabel(xlab)

        # standard deviations
        subplot(2,2,4)
        hold(False)
        # remove sigma from stds (graphs become much better readible)
        dat.std[:,5:] = np.transpose(dat.std[:,5:].T / dat.std[:,2].T)
        # ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        # axis(ax)
        if 1 < 2 and dat.std.shape[1] < 100:
            # use fake last entry in x and std for line extension-annotation
            minxend = int(1.06*dat.x[-2, iabscissa])
            dat.std[-1, iabscissa] = minxend  # TODO: should be ax[1]
            idx = np.argsort(dat.std[-2,5:])
            idx2 = np.argsort(idx)
            dat.std[-1,5+idx] = np.logspace(np.log10(np.min(dat.std[:,5:])),
                            np.log10(np.max(dat.std[:,5:])), dat.std.shape[1]-5)

            dat.std[-1, iabscissa] = minxend  # TODO: should be ax[1]
            yy = np.logspace(np.log10(ax[2]), np.log10(ax[3]), dat.std.shape[1]-5)
            #yyl = np.sort(dat.std[-1,5:])
            idx = np.argsort(dat.std[-1,5:])
            idx2 = np.argsort(idx)
            # plot(np.dot(dat.std[-2, iabscissa],[1,1]), array([ax[2]+1e-6, ax[3]-1e-6]), 'k-') # vertical separator
            # vertical separator
            plot(np.dot(dat.std[-2, iabscissa],[1,1]), array([np.min(dat.std[-2,5:]), np.max(dat.std[-2,5:])]), 'k-')
            hold(True)
            # plot([dat.std[-1, iabscissa], ax[1]], [dat.std[-1,5:], yy[idx2]], 'k-') # line from last data point
            for i in xrange(len(idx)):
                # text(ax[1], yy[i], ' '+str(idx[i]))
                text(dat.std[-1, iabscissa], dat.std[-1, 5+i], ' '+str(i))
        semilogy(dat.std[:, iabscissa], dat.std[:,5:], '-')
        grid(True)
        title('Standard Deviations in All Coordinates')
        # pylab.xticks(xticklocs)
        xlabel(xlab)
        draw()  # does not suffice
        if interactive_status:
            ion()  # turns interactive mode on (again)
            draw()
        show()

        return self


    #____________________________________________________________
    #____________________________________________________________
    #
    @staticmethod
    def plotdivers(dat, iabscissa, foffset):
        """helper function for `plot()` that plots all what is
        in the upper left subplot like fitness, sigma, etc.

        Arguments
        ---------
            `iabscissa` in ``(0,1)``
                0==versus fevals, 1==versus iteration
            `foffset`
                offset to fitness for log-plot

         :See: `plot()`

        """
        from  matplotlib.pylab import semilogy, hold, grid, \
                 axis, title, text
        fontsize = pylab.rcParams['font.size']

        hold(False)

        dfit = dat.f[:,5]-min(dat.f[:,5])
        dfit[dfit<1e-98] = np.NaN

        if dat.f.shape[1] > 7:
            # semilogy(dat.f[:, iabscissa], abs(dat.f[:,[6, 7, 10, 12]])+foffset,'-k')
            semilogy(dat.f[:, iabscissa], abs(dat.f[:,[6, 7]])+foffset,'-k')
            hold(True)

        # (larger indices): additional fitness data, for example constraints values
        if dat.f.shape[1] > 8:
            # dd = abs(dat.f[:,7:]) + 10*foffset
            # dd = np.where(dat.f[:,7:]==0, np.NaN, dd) # cannot be
            semilogy(dat.f[:, iabscissa], np.abs(dat.f[:,8:]) + 10*foffset, 'm')
            hold(True)

        idx = np.where(dat.f[:,5]>1e-98)[0]  # positive values
        semilogy(dat.f[idx, iabscissa], dat.f[idx,5]+foffset, '.b')
        hold(True)
        grid(True)

        idx = np.where(dat.f[:,5] < -1e-98)  # negative values
        semilogy(dat.f[idx, iabscissa], abs(dat.f[idx,5])+foffset,'.r')

        semilogy(dat.f[:, iabscissa],abs(dat.f[:,5])+foffset,'-b')
        semilogy(dat.f[:, iabscissa], dfit, '-c')

        if 11 < 3:  # delta-fitness as points
            dfit = dat.f[1:, 5] - dat.f[:-1,5]  # should be negative usually
            semilogy(dat.f[1:,iabscissa],  # abs(fit(g) - fit(g-1))
                np.abs(dfit)+foffset, '.c')
            i = dfit > 0
            # print(np.sum(i) / float(len(dat.f[1:,iabscissa])))
            semilogy(dat.f[1:,iabscissa][i],  # abs(fit(g) - fit(g-1))
                np.abs(dfit[i])+foffset, '.r')

        # overall minimum
        i = np.argmin(dat.f[:,5])
        semilogy(dat.f[i, iabscissa]*np.ones(2), dat.f[i,5]*np.ones(2), 'rd')
        # semilogy(dat.f[-1, iabscissa]*np.ones(2), dat.f[-1,4]*np.ones(2), 'rd')

        # AR and sigma
        semilogy(dat.f[:, iabscissa], dat.f[:,3], '-r') # AR
        semilogy(dat.f[:, iabscissa], dat.f[:,2],'-g') # sigma
        semilogy(dat.std[:-1, iabscissa], np.vstack([list(map(max, dat.std[:-1,5:])), list(map(min, dat.std[:-1,5:]))]).T,
                     '-m', linewidth=2)
        text(dat.std[-2, iabscissa], max(dat.std[-2, 5:]), 'max std', fontsize=fontsize)
        text(dat.std[-2, iabscissa], min(dat.std[-2, 5:]), 'min std', fontsize=fontsize)
        ax = array(axis())
        # ax[1] = max(minxend, ax[1])
        axis(ax)
        text(ax[0]+0.01, ax[2], # 10**(log10(ax[2])+0.05*(log10(ax[3])-log10(ax[2]))),
             '.f_recent=' + repr(dat.f[-1,5]) )

        # title('abs(f) (blue), f-min(f) (cyan), Sigma (green), Axis Ratio (red)')
        title('blue:abs(f), cyan:f-min(f), green:sigma, red:axis ratio', fontsize=fontsize-1)
        # pylab.xticks(xticklocs)


    def downsampling(self, factor=10, first=3, switch=True):
        """
        rude downsampling of a `CMADataLogger` data file by `factor`, keeping
        also the first `first` entries. This function is a stump and subject
        to future changes.

        Arguments
        ---------
           - `factor` -- downsampling factor
           - `first` -- keep first `first` entries
           - `switch` -- switch the new logger name to oldname+'down'

        Details
        -------
        ``self.name_prefix+'down'`` files are written

        Example
        -------
        ::

            import cma
            cma.downsampling()  # takes outcmaes* files
            cma.plot('outcmaesdown')

        """
        newprefix = self.name_prefix + 'down'
        for name in CMADataLogger.names:
            f = open(newprefix+name+'.dat','w')
            iline = 0
            cwritten = 0
            for line in open(self.name_prefix+name+'.dat'):
                if iline < first or iline % factor == 0:
                    f.write(line)
                    cwritten += 1
                iline += 1
            f.close()
            print('%d' % (cwritten) + ' lines written in ' + newprefix+name+'.dat')
        if switch:
            self.name_prefix += 'down'
        return self

    #____________________________________________________________
    #____________________________________________________________
    #
    def disp_header(self):
        heading = 'Iterat Nfevals  function value    axis ratio maxstd   minstd'
        print(heading)

    def disp(self, idx=100):  # r_[0:5,1e2:1e9:1e2,-10:0]):
        """displays selected data from (files written by) the class `CMADataLogger`.

        Arguments
        ---------
           `idx`
               indices corresponding to rows in the data file;
               if idx is a scalar (int), the first two, then every idx-th,
               and the last three rows are displayed. Too large index values are removed.
               If ``len(idx) == 1``, only a single row is displayed, e.g. the last
               entry when ``idx == [-1]``.

        Example
        -------
        >>> import cma, numpy as np
        >>> res = cma.fmin(cma.fcts.elli, 7 * [0.1], 1, verb_disp=1e9)  # generate data
        >>> assert res[1] < 1e-9
        >>> assert res[2] < 4400
        >>> l = cma.CMADataLogger()  # == res[-1], logger with default name, "points to" above data
        >>> l.disp([0,-1])  # first and last
        >>> l.disp(20)  # some first/last and every 20-th line
        >>> l.disp(np.r_[0:999999:100, -1]) # every 100-th and last
        >>> l.disp(np.r_[0, -10:0]) # first and ten last
        >>> cma.disp(l.name_prefix, np.r_[0::100, -10:])  # the same as l.disp(...)

        Details
        -------
        The data line with the best f-value is displayed as last line.

        :See: `disp()`

        """

        filenameprefix=self.name_prefix

        def printdatarow(dat, iteration):
            """print data of iteration i"""
            i = np.where(dat.f[:, 0] == iteration)[0][0]
            j = np.where(dat.std[:, 0] == iteration)[0][0]
            print('%5d' % (int(dat.f[i,0])) + ' %6d' % (int(dat.f[i,1])) + ' %.14e' % (dat.f[i,5]) +
                  ' %5.1e' % (dat.f[i,3]) +
                  ' %6.2e' % (max(dat.std[j,5:])) + ' %6.2e' % min(dat.std[j,5:]))

        dat = CMADataLogger(filenameprefix).load()
        ndata = dat.f.shape[0]

        # map index to iteration number, is difficult if not all iteration numbers exist
        # idx = idx[np.where(map(lambda x: x in dat.f[:,0], idx))[0]] # TODO: takes pretty long
        # otherwise:
        if idx is None:
            idx = 100
        if np.isscalar(idx):
            # idx = np.arange(0, ndata, idx)
            if idx:
                idx = np.r_[0, 1, idx:ndata-3:idx, -3:0]
            else:
                idx = np.r_[0, 1, -3:0]

        idx = array(idx)
        idx = idx[idx<=ndata]  # TODO: shouldn't this be "<"?
        idx = idx[-idx<=ndata]
        iters = dat.f[idx, 0]
        idxbest = np.argmin(dat.f[:,5])
        iterbest = dat.f[idxbest, 0]
        if len(iters) == 1:
            printdatarow(dat, iters[0])
        else:
            self.disp_header()
            for i in iters:
                printdatarow(dat, i)
            self.disp_header()
            printdatarow(dat, iterbest)
        sys.stdout.flush()

def irg(ar):
    return xrange(len(ar))
class AII(object):
    """unstable experimental code, updates ps, sigma, sigmai, pr, r, sigma_r, mean,
    all from self.

    Depends on that the ordering of solutions has not change upon calling update

    should become a OOOptimizer in far future?

    """
    # Try: ps**2 - 1 instead of (ps**2)**0.5 / chi1 - 1: compare learning rate etc
    # and dito for psr

    def __init__(self, x0, sigma0, randn=np.random.randn):
        """TODO: check scaling of r-learing: seems worse than linear: 9e3 25e3 65e3 (10,20,40-D)"""
        self.N = len(x0)
        N = self.N
        # parameters to play with:
        # PROBLEM: smaller eta_r even fails on *axparallel* cigar!! Also dampi needs to be smaller then!
        self.dampi = 4 * N  # two times smaller is
        self.eta_r = 0 / N / 3   # c_r learning rate for direction, cigar: 4/N/3 is optimal in 10-D, 10/N/3 still works (15 in 20-D) but not on the axparallel cigar with recombination
        self.mu = 1
        self.use_abs_sigma = 1    # without it is a problem on 20=D axpar-cigar!!, but why?? Because dampi is just boarderline
        self.use_abs_sigma_r = 1  #

        self.randn = randn
        self.x0 = array(x0, copy=True)
        self.sigma0 = sigma0

        self.cs = 1 / N**0.5  # evolution path for step-size(s)
        self.damps = 1
        self.use_sign = 0
        self.use_scalar_product = 0  # sometimes makes it somewhat worse on Rosenbrock, don't know why
        self.csr = 1 / N**0.5  # cumulation for sigma_r
        self.dampsr = (4 * N)**0.5
        self.chi1 = (2/np.pi)**0.5
        self.chiN = N**0.5*(1-1./(4.*N)+1./(21.*N**2)) # expectation of norm(randn(N,1))
        self.initialize()
    def initialize(self):
        """alias ``reset``, set all state variables to initial values"""
        N = self.N
        self.mean = array(self.x0, copy=True)
        self.sigma = self.sigma0
        self.sigmai = np.ones(N)
        self.ps = np.zeros(N)  # path for individual and globalstep-size(s)
        self.r = np.zeros(N)
        self.pr = 0         # cumulation for zr = N(0,1)
        self.sigma_r = 0
    def ask(self, popsize):
        if popsize == 1:
            raise NotImplementedError()
        self.Z = [self.randn(self.N) for _i in xrange(popsize)]
        self.zr = list(self.randn(popsize))
        pop = [self.mean + self.sigma * (self.sigmai * self.Z[k])
                + self.zr[k] * self.sigma_r * self.r
                for k in xrange(popsize)]
        if not np.isfinite(pop[0][0]):
            raise ValueError()
        return pop
    def tell(self, X, f):
        """update """
        mu = 1 if self.mu else int(len(f) / 4)
        idx = np.argsort(f)[:mu]
        zr = [self.zr[i] for i in idx]
        Z = [self.Z[i] for i in idx]
        X = [X[i] for i in idx]
        xmean = np.mean(X, axis=0)

        self.ps *= 1 - self.cs
        self.ps += (self.cs*(2-self.cs))**0.5 * mu**0.5 * np.mean(Z, axis=0)
        self.sigma *= np.exp((self.cs/self.damps) * (sum(self.ps**2)**0.5 / self.chiN - 1))
        if self.use_abs_sigma:
            self.sigmai *= np.exp((1/self.dampi) * (np.abs(self.ps) / self.chi1 - 1))
        else:
            self.sigmai *= np.exp((1.3/self.dampi/2) * (self.ps**2 - 1))

        self.pr *= 1 - self.csr
        self.pr += (self.csr*(2-self.csr))**0.5 * mu**0.5 * np.mean(zr)
        fac = 1
        if self.use_sign:
            fac = np.sign(self.pr)  # produces readaptations on the cigar
        else:
            self.pr = max([0, self.pr])
        if self.use_scalar_product:
            if np.sign(sum(self.r * (xmean - self.mean))) < 0: # and self.pr > 1:
            # if np.sign(sum(self.r * self.ps)) < 0:
                self.r *= -1
        if self.eta_r:
            self.r *= (1 - self.eta_r) * self.sigma_r
            self.r += fac * self.eta_r * mu**0.5 * (xmean - self.mean)
            self.r /= sum(self.r**2)**0.5
        if self.use_abs_sigma_r:
            self.sigma_r *= np.exp((1/self.dampsr) * ((self.pr**2)**0.5 / self.chi1 - 1))
        else:
            # this is worse on the cigar, where the direction vector(!) behaves strangely
            self.sigma_r *= np.exp((1/self.dampsr) * (self.pr**2 - 1) / 2)
        self.sigma_r = max([self.sigma * sum(self.sigmai**2)**0.5 / 3, self.sigma_r])
        # self.sigma_r = 0
        self.mean = xmean
def fmin(func, x0, sigma0=None, args=()
    # the follow string arguments are evaluated, besides the verb_filenameprefix
    , CMA_active='False  # exponential negative update, conducted after the original update'
    , CMA_activefac='1  # learning rate multiplier for active update'
    , CMA_cmean='1  # learning rate for the mean value'
    , CMA_const_trace='False  # normalize trace, value CMA_const_trace=2 normalizes sum log eigenvalues to zero'
    , CMA_diagonal='0*100*N/sqrt(popsize)  # nb of iterations with diagonal covariance matrix, True for always' # TODO 4/ccov_separable?
    , CMA_eigenmethod='np.linalg.eigh  # 0=numpy-s eigh, -1=pygsl, otherwise cma.Misc.eig (slower)'
    , CMA_elitist='False # elitism likely impairs global search performance'
    , CMA_mirrors='popsize < 6  # values <0.5 are interpreted as fraction, values >1 as numbers (rounded), otherwise about 0.16 is used'
    , CMA_mu='None  # parents selection parameter, default is popsize // 2'
    , CMA_on='True  # False or 0 for no adaptation of the covariance matrix'
    , CMA_rankmu='True  # False or 0 for omitting rank-mu update of covariance matrix'
    , CMA_rankmualpha='0.3  # factor of rank-mu update if mu=1, subject to removal, default might change to 0.0'
    , CMA_dampfac='1  #v positive multiplier for step-size damping, 0.3 is close to optimal on the sphere'
    , CMA_dampsvec_fac='np.Inf  # tentative and subject to changes, 0.5 would be a "default" damping for sigma vector update'
    , CMA_dampsvec_fade='0.1  # tentative fading out parameter for sigma vector update'
    , CMA_teststds='None  # factors for non-isotropic initial distr. mainly for test purpose, see scaling_...'
    , CMA_AII='False  # not yet tested'
    , bounds='[None, None]  # lower (=bounds[0]) and upper domain boundaries, each a scalar or a list/vector'
    , eval_parallel='False  # when True, func might be called with more than one solution as first argument'
    , eval_initial_x='False  # '
    , fixed_variables='None  # dictionary with index-value pairs like {0:1.1, 2:0.1} that are not optimized'
    , ftarget='-inf  #v target function value, minimization'
    , incpopsize='2  # in fmin(): multiplier for increasing popsize before each restart'
    , maxfevals='inf  #v maximum number of function evaluations'
    , maxiter='100 + 50 * (N+3)**2 // popsize**0.5  #v maximum number of iterations'
    , mindx='0  #v minimal std in any direction, cave interference with tol*'
    , minstd='0  #v minimal std in any coordinate direction, cave interference with tol*'
    , noise_handling='False  # maximal number of evaluations for noise treatment, only fmin'
    , noise_reevals=' 1.5 + popsize/20  # number of solution to be reevaluated for noise measurement, only fmin'
    , noise_eps='1e-7  # perturbation factor for noise handling reevaluations, only fmin'
    , noise_change_sigma='True  # exponent to default sigma increment'
    , popsize='4+int(3*log(N))  # population size, AKA lambda, number of new solution per iteration'
    , randn='np.random.standard_normal  #v randn((lam, N)) must return an np.array of shape (lam, N)'
    , restarts='0  # in fmin(): number of restarts'
    , restart_from_best='False'
    , scaling_of_variables='None  # scale for each variable, sigma0 is interpreted w.r.t. this scale, in that effective_sigma0 = sigma0*scaling. Internally the variables are divided by scaling_of_variables and sigma is unchanged, default is ones(N)'
    , seed='None  # random number seed'
    , termination_callback='None  #v a function returning True for termination, called after each iteration step and could be abused for side effects'
    , tolfacupx='1e3  #v termination when step-size increases by tolfacupx (diverges). That is, the initial step-size was chosen far too small and better solutions were found far away from the initial solution x0'
    , tolupsigma='1e20  #v sigma/sigma0 > tolupsigma * max(sqrt(eivenvals(C))) indicates "creeping behavior" with usually minor improvements'
    , tolfun='1e-11  #v termination criterion: tolerance in function value, quite useful'
    , tolfunhist='1e-12  #v termination criterion: tolerance in function value history'
    , tolstagnation='int(100 + 100 * N**1.5 / popsize)  #v termination if no improvement over tolstagnation iterations'
    , tolx='1e-11  #v termination criterion: tolerance in x-changes'
    , transformation='None  # [t0, t1] are two mappings, t0 transforms solutions from CMA-representation to f-representation (tf_pheno), t1 is the (optional) back transformation, see class GenoPheno'
    , typical_x='None  # used with scaling_of_variables'
    , updatecovwait='None  #v number of iterations without distribution update, name is subject to future changes' # TODO: rename: iterwaitupdatedistribution?
    , verb_append='0  # initial evaluation counter, if append, do not overwrite output files'
    , verb_disp='100  #v verbosity: display console output every verb_disp iteration'
    , verb_filenameprefix='outcmaes  # output filenames prefix'
    , verb_log='1  #v verbosity: write data to files every verb_log iteration, writing can be time critical on fast to evaluate functions'
    , verb_plot='0  #v in fmin(): plot() is called every verb_plot iteration'
    , verb_time='True  #v output timings on console'
    , vv='0  #? versatile variable for hacking purposes, value found in self.opts[\'vv\']'
     ):
    """functional interface to the stochastic optimizer CMA-ES
    for non-convex function minimization.

    Calling Sequences
    =================
        ``fmin([],[])``
            returns all optional arguments, that is,
            all keyword arguments to fmin with their default values
            in a dictionary.
        ``fmin(func, x0, sigma0)``
            minimizes `func` starting at `x0` and with standard deviation
            `sigma0` (step-size)
        ``fmin(func, x0, sigma0, ftarget=1e-5)``
            minimizes `func` up to target function value 1e-5
        ``fmin(func, x0, sigma0, args=('f',), **options)``
            minimizes `func` called with an additional argument ``'f'``.
            `options` is a dictionary with additional keyword arguments, e.g.
            delivered by `Options()`.
        ``fmin(func, x0, sigma0, **{'ftarget':1e-5, 'popsize':40})``
            the same as ``fmin(func, x0, sigma0, ftarget=1e-5, popsize=40)``
        ``fmin(func, esobj, **{'maxfevals': 1e5})``
            uses the `CMAEvolutionStrategy` object instance `esobj` to optimize
            `func`, similar to `CMAEvolutionStrategy.optimize()`.

    Arguments
    =========
        `func`
            function to be minimized. Called as
            ``func(x,*args)``. `x` is a one-dimensional `numpy.ndarray`. `func`
            can return `numpy.NaN`,
            which is interpreted as outright rejection of solution `x`
            and invokes an immediate resampling and (re-)evaluation
            of a new solution not counting as function evaluation.
        `x0`
            list or `numpy.ndarray`, initial guess of minimum solution
            or `cma.CMAEvolutionStrategy` object instance. In this case
            `sigma0` can be omitted.
        `sigma0`
            scalar, initial standard deviation in each coordinate.
            `sigma0` should be about 1/4 of the search domain width where the
            optimum is to be expected. The variables in `func` should be
            scaled such that they presumably have similar sensitivity.
            See also option `scaling_of_variables`.

    Keyword Arguments
    =================
    All arguments besides `args` and `verb_filenameprefix` are evaluated
    if they are of type `str`, see class `Options` for details. The following
    list might not be fully up-to-date, use ``cma.Options()`` or
    ``cma.fmin([],[])`` to get the actual list.
    ::

        args=() -- additional arguments for func, not in `cma.Options()`
        CMA_active='False  # exponential negative update, conducted after the original
                update'
        CMA_activefac='1  # learning rate multiplier for active update'
        CMA_cmean='1  # learning rate for the mean value'
        CMA_dampfac='1  #v positive multiplier for step-size damping, 0.3 is close to
                optimal on the sphere'
        CMA_diagonal='0*100*N/sqrt(popsize)  # nb of iterations with diagonal
                covariance matrix, True for always'
        CMA_eigenmethod='np.linalg.eigh  # 0=numpy-s eigh, -1=pygsl, alternative: Misc.eig (slower)'
        CMA_elitist='False # elitism likely impairs global search performance'
        CMA_mirrors='0  # values <0.5 are interpreted as fraction, values >1 as numbers
                (rounded), otherwise about 0.16 is used'
        CMA_mu='None  # parents selection parameter, default is popsize // 2'
        CMA_on='True  # False or 0 for no adaptation of the covariance matrix'
        CMA_rankmu='True  # False or 0 for omitting rank-mu update of covariance
                matrix'
        CMA_rankmualpha='0.3  # factor of rank-mu update if mu=1, subject to removal,
                default might change to 0.0'
        CMA_teststds='None  # factors for non-isotropic initial distr. mainly for test
                purpose, see scaling_...'
        bounds='[None, None]  # lower (=bounds[0]) and upper domain boundaries, each a
                scalar or a list/vector'
        eval_initial_x='False  # '
        fixed_variables='None  # dictionary with index-value pairs like {0:1.1, 2:0.1}
                that are not optimized'
        ftarget='-inf  #v target function value, minimization'
        incpopsize='2  # in fmin(): multiplier for increasing popsize before each
                restart'
        maxfevals='inf  #v maximum number of function evaluations'
        maxiter='long(1e3*N**2/sqrt(popsize))  #v maximum number of iterations'
        mindx='0  #v minimal std in any direction, cave interference with tol*'
        minstd='0  #v minimal std in any coordinate direction, cave interference with
                tol*'
        noise_eps='1e-7  # perturbation factor for noise handling reevaluations, only
                fmin'
        noise_handling='False  # maximal number of evaluations for noise treatment,
                only fmin'
        noise_reevals=' 1.5 + popsize/20  # number of solution to be reevaluated for
                noise measurement, only fmin'
        popsize='4+int(3*log(N))  # population size, AKA lambda, number of new solution
                per iteration'
        randn='np.random.standard_normal  #v randn((lam, N)) must return an np.array of
                shape (lam, N)'
        restarts='0  # in fmin(): number of restarts'
        scaling_of_variables='None  # scale for each variable, sigma0 is interpreted
                w.r.t. this scale, in that effective_sigma0 = sigma0*scaling.
                Internally the variables are divided by scaling_of_variables and sigma
                is unchanged, default is ones(N)'
        seed='None  # random number seed'
        termination_callback='None  #v in fmin(): a function returning True for
                termination, called after each iteration step and could be abused for
                side effects'
        tolfacupx='1e3  #v termination when step-size increases by tolfacupx
                (diverges). That is, the initial step-size was chosen far too small and
                better solutions were found far away from the initial solution x0'
        tolupsigma='1e20  #v sigma/sigma0 > tolupsigma * max(sqrt(eivenvals(C)))
                indicates "creeping behavior" with usually minor improvements'
        tolfun='1e-11  #v termination criterion: tolerance in function value, quite
                useful'
        tolfunhist='1e-12  #v termination criterion: tolerance in function value
                history'
        tolstagnation='int(100 * N**1.5 / popsize)  #v termination if no improvement
                over tolstagnation iterations'
        tolx='1e-11  #v termination criterion: tolerance in x-changes'
        transformation='None  # [t0, t1] are two mappings, t0 transforms solutions from
                CMA-representation to f-representation, t1 is the back transformation,
                see class GenoPheno'
        typical_x='None  # used with scaling_of_variables'
        updatecovwait='None  #v number of iterations without distribution update, name
                is subject to future changes'
        verb_append='0  # initial evaluation counter, if append, do not overwrite
                output files'
        verb_disp='100  #v verbosity: display console output every verb_disp iteration'
        verb_filenameprefix='outcmaes  # output filenames prefix'
        verb_log='1  #v verbosity: write data to files every verb_log iteration,
                writing can be time critical on fast to evaluate functions'
        verb_plot='0  #v in fmin(): plot() is called every verb_plot iteration'
        verb_time='True  #v output timings on console'
        vv='0  #? versatile variable for hacking purposes, value found in
                self.opts['vv']'

    Subsets of options can be displayed, for example like ``cma.Options('tol')``,
    see also class `Options`.

    Return
    ======
    Similar to `OOOptimizer.optimize()` and/or `CMAEvolutionStrategy.optimize()`, return the
    list provided by `CMAEvolutionStrategy.result()` appended with an `OOOptimizer` and an
    `BaseDataLogger`::

        res = optim.result() + (optim.stop(), optim, logger)

    where
        - ``res[0]`` (``xopt``) -- best evaluated solution
        - ``res[1]`` (``fopt``) -- respective function value
        - ``res[2]`` (``evalsopt``) -- respective number of function evaluations
        - ``res[3]`` (``evals``) -- number of overall conducted objective function evaluations
        - ``res[4]`` (``iterations``) -- number of overall conducted iterations
        - ``res[5]`` (``xmean``) -- mean of the final sample distribution
        - ``res[6]`` (``stds``) -- effective stds of the final sample distribution
        - ``res[-3]`` (``stop``) -- termination condition(s) in a dictionary
        - ``res[-2]`` (``cmaes``) -- class `CMAEvolutionStrategy` instance
        - ``res[-1]`` (``logger``) -- class `CMADataLogger` instance

    Details
    =======
    This function is an interface to the class `CMAEvolutionStrategy`. The
    class can be used when full control over the iteration loop of the
    optimizer is desired.

    The noise handling follows closely [Hansen et al 2009, A Method for Handling
    Uncertainty in Evolutionary Optimization...] in the measurement part, but the
    implemented treatment is slightly different: for ``noiseS > 0``, ``evaluations``
    (time) and sigma are increased by ``alpha``. For ``noiseS < 0``, ``evaluations``
    (time) is decreased by ``alpha**(1/4)``. The option ``noise_handling`` switches
    the uncertainty handling on/off, the given value defines the maximal number
    of evaluations for a single fitness computation. If ``noise_handling`` is a list,
    the smallest element defines the minimal number and if the list has three elements,
    the median value is the start value for ``evaluations``. See also class
    `NoiseHandler`.

    Examples
    ========
    The following example calls `fmin` optimizing the Rosenbrock function
    in 10-D with initial solution 0.1 and initial step-size 0.5. The
    options are specified for the usage with the `doctest` module.

    >>> import cma
    >>> # cma.Options()  # returns all possible options
    >>> options = {'CMA_diagonal':10, 'seed':1234, 'verb_time':0}
    >>>
    >>> res = cma.fmin(cma.fcts.rosen, [0.1] * 10, 0.5, **options)
    (5_w,10)-CMA-ES (mu_w=3.2,w_1=45%) in dimension 10 (seed=1234)
       Covariance matrix is diagonal for 10 iterations (1/ccov=29.0)
    Iterat #Fevals   function value     axis ratio  sigma   minstd maxstd min:sec
        1      10 1.264232686260072e+02 1.1e+00 4.40e-01  4e-01  4e-01
        2      20 1.023929748193649e+02 1.1e+00 4.00e-01  4e-01  4e-01
        3      30 1.214724267489674e+02 1.2e+00 3.70e-01  3e-01  4e-01
      100    1000 6.366683525319511e+00 6.2e+00 2.49e-02  9e-03  3e-02
      200    2000 3.347312410388666e+00 1.2e+01 4.52e-02  8e-03  4e-02
      300    3000 1.027509686232270e+00 1.3e+01 2.85e-02  5e-03  2e-02
      400    4000 1.279649321170636e-01 2.3e+01 3.53e-02  3e-03  3e-02
      500    5000 4.302636076186532e-04 4.6e+01 4.78e-03  3e-04  5e-03
      600    6000 6.943669235595049e-11 5.1e+01 5.41e-06  1e-07  4e-06
      650    6500 5.557961334063003e-14 5.4e+01 1.88e-07  4e-09  1e-07
    termination on tolfun : 1e-11
    final/bestever f-value = 5.55796133406e-14 2.62435631419e-14
    mean solution:  [ 1.          1.00000001  1.          1.
        1.          1.00000001  1.00000002  1.00000003 ...]
    std deviation: [ 3.9193387e-09  3.7792732e-09  4.0062285e-09  4.6605925e-09
        5.4966188e-09   7.4377745e-09   1.3797207e-08   2.6020765e-08 ...]
    >>>
    >>> print('best solutions fitness = %f' % (res[1]))
    best solutions fitness = 2.62435631419e-14
    >>> assert res[1] < 1e-12

    The method ::

        cma.plot();

    (based on `matplotlib.pylab`) produces a plot of the run and, if necessary::

        cma.show()

    shows the plot in a window. To continue you might need to
    close the pop-up window. This behavior seems to disappear in
    subsequent calls of `cma.plot()` and is avoided by using
    `ipython` with `-pylab` option. Finally ::

        cma.savefig('myfirstrun')  # savefig from matplotlib.pylab

    will save the figure in a png.

    :See: `CMAEvolutionStrategy`, `OOOptimizer.optimize(), `plot()`, `Options`, `scipy.optimize.fmin()`

    """ # style guides say there should be the above empty line
    try: # pass on KeyboardInterrupt
        opts = locals()  # collect all local variables (i.e. arguments) in a dictionary
        del opts['func'] # remove those without a default value
        del opts['args']
        del opts['x0']      # is not optional, no default available
        del opts['sigma0']  # is not optional for the constructor CMAEvolutionStrategy
        if not func:  # return available options in a dictionary
            return Options(opts, True)  # these opts are by definition valid

        # TODO: this is very ugly:
        incpopsize = Options({'incpopsize':incpopsize}).eval('incpopsize')
        restarts = Options({'restarts':restarts}).eval('restarts')
        del opts['restarts']
        noise_handling = Options({'noise_handling': noise_handling}).eval('noise_handling')
        del opts['noise_handling']# otherwise CMA throws an error

        irun = 0
        best = BestSolution()
        while 1:
            # recover from a CMA object
            if irun == 0 and isinstance(x0, CMAEvolutionStrategy):
                es = x0
                x0 = es.inputargs['x0']  # for the next restarts
                if sigma0 is None or not np.isscalar(array(sigma0)):
                    sigma0 = es.inputargs['sigma0']  # for the next restarts
                # ignore further input args and keep original options
            else:  # default case
                if irun and opts['restart_from_best']:
                    print('CAVE: restart_from_best is typically not useful')
                    es = CMAEvolutionStrategy(best.x, sigma0, opts)
                else:
                    es = CMAEvolutionStrategy(x0, sigma0, opts)
                if opts['eval_initial_x']:
                    x = es.gp.pheno(es.mean, bounds=es.gp.bounds)
                    es.best.update([x], None, [func(x, *args)], 1)
                    es.countevals += 1

            opts = es.opts  # processed options, unambiguous

            append = opts['verb_append'] or es.countiter > 0 or irun > 0
            logger = CMADataLogger(opts['verb_filenameprefix'], opts['verb_log'])
            logger.register(es, append).add()  # initial values, not fitness values

            # if es.countiter == 0 and es.opts['verb_log'] > 0 and not es.opts['verb_append']:
            #    logger = CMADataLogger(es.opts['verb_filenameprefix']).register(es)
            #    logger.add()
            # es.writeOutput()  # initial values for sigma etc

            noisehandler = NoiseHandler(es.N, noise_handling, np.median, opts['noise_reevals'], opts['noise_eps'], opts['eval_parallel'])
            while not es.stop():
                X, fit = es.ask_and_eval(func, args, evaluations=noisehandler.evaluations,
                                         aggregation=np.median) # treats NaN with resampling
                # TODO: check args and in case use args=(noisehandler.evaluations, )

                if 11 < 3 and opts['vv']:  # inject a solution
                    # use option check_point = [0]
                    if 0 * np.random.randn() >= 0:
                        X[0] = 0 + opts['vv'] * es.sigma**0 * np.random.randn(es.N)
                        fit[0] = func(X[0], *args)
                        # print fit[0]
                es.tell(X, fit)  # prepare for next iteration
                if noise_handling:
                    es.sigma *= noisehandler(X, fit, func, es.ask, args)**opts['noise_change_sigma']
                    es.countevals += noisehandler.evaluations_just_done  # TODO: this is a hack, not important though

                es.disp()
                logger.add(more_data=[noisehandler.evaluations, 10**noisehandler.noiseS] if noise_handling else [],
                           modulo=1 if es.stop() and logger.modulo else None)
                if opts['verb_log'] and opts['verb_plot'] and \
                    (es.countiter % max(opts['verb_plot'], opts['verb_log']) == 0 or es.stop()):
                    logger.plot(324, fontsize=10)

            # end while not es.stop
            mean_pheno = es.gp.pheno(es.mean, bounds=es.gp.bounds)
            fmean = func(mean_pheno, *args)
            es.countevals += 1

            es.best.update([mean_pheno], None, [fmean], es.countevals)
            best.update(es.best)  # in restarted case

            # final message
            if opts['verb_disp']:
                srestarts = (' after %i restart' + ('s' if irun > 1 else '')) % irun if irun else ''
                for k, v in list(es.stop().items()):
                    print('termination on %s=%s%s (%s)' % (k, str(v), srestarts, time.asctime()))

                print('final/bestever f-value = %e %e' % (es.best.last.f, best.f))
                if es.N < 9:
                    print('mean solution: ' + str(es.gp.pheno(es.mean)))
                    print('std deviation: ' + str(es.sigma * sqrt(es.dC) * es.gp.scales))
                else:
                    print('mean solution: %s ...]' % (str(es.gp.pheno(es.mean)[:8])[:-1]))
                    print('std deviations: %s ...]' % (str((es.sigma * sqrt(es.dC) * es.gp.scales)[:8])[:-1]))

            irun += 1
            if irun > restarts or 'ftarget' in es.stopdict or 'maxfunevals' in es.stopdict:
                break
            opts['verb_append'] = es.countevals
            opts['popsize'] = incpopsize * es.sp.popsize # TODO: use rather options?
            opts['seed'] += 1

        # while irun

        es.out['best'] = best  # TODO: this is a rather suboptimal type for inspection in the shell
        if 1 < 3:
            return es.result() + (es.stop(), es, logger)

        else: # previously: to be removed
            return (best.x.copy(), best.f, es.countevals,
                    dict((('stopdict', CMAStopDict(es.stopdict))
                          ,('mean', es.gp.pheno(es.mean))
                          ,('std', es.sigma * sqrt(es.dC) * es.gp.scales)
                          ,('out', es.out)
                          ,('opts', es.opts)  # last state of options
                          ,('cma', es)
                          ,('inputargs', es.inputargs)
                          ))
                   )
        # TODO refine output, can #args be flexible?
        # is this well usable as it is now?
    except KeyboardInterrupt:  # Exception, e:
        if opts['verb_disp'] > 0:
            print(' in/outcomment ``raise`` in last line of cma.fmin to prevent/restore KeyboardInterrupt exception')
        raise  # cave: swallowing this exception can silently mess up experiments, if ctrl-C is hit
def plot(name=None, fig=None, abscissa=1, iteridx=None, plot_mean=True,  # TODO: plot_mean default should be False
    foffset=1e-19, x_opt=None, fontsize=10):
    """
    plot data from files written by a `CMADataLogger`,
    the call ``cma.plot(name, **argsdict)`` is a shortcut for
    ``cma.CMADataLogger(name).plot(**argsdict)``

    Arguments
    ---------
        `name`
            name of the logger, filename prefix, None evaluates to
            the default 'outcmaes'
        `fig`
            filename or figure number, or both as a tuple (any order)
        `abscissa`
            0==plot versus iteration count,
            1==plot versus function evaluation number
        `iteridx`
            iteration indices to plot

    Return `None`

    Examples
    --------
    ::

       cma.plot();  # the optimization might be still
                    # running in a different shell
       cma.show()  # to continue you might need to close the pop-up window
                   # once and call cma.plot() again.
                   # This behavior seems to disappear in subsequent
                   # calls of cma.plot(). Also using ipython with -pylab
                   # option might help.
       cma.savefig('fig325.png')
       cma.close()

       cdl = cma.CMADataLogger().downsampling().plot()

    Details
    -------
    Data from codes in other languages (C, Java, Matlab, Scilab) have the same
    format and can be plotted just the same.

    :See: `CMADataLogger`, `CMADataLogger.plot()`

    """
    CMADataLogger(name).plot(fig, abscissa, iteridx, plot_mean, foffset, x_opt, fontsize)
def disp(name=None, idx=None):
    """displays selected data from (files written by) the class `CMADataLogger`.

    The call ``cma.disp(name, idx)`` is a shortcut for ``cma.CMADataLogger(name).disp(idx)``.

    Arguments
    ---------
        `name`
            name of the logger, filename prefix, `None` evaluates to
            the default ``'outcmaes'``
        `idx`
            indices corresponding to rows in the data file; by
            default the first five, then every 100-th, and the last
            10 rows. Too large index values are removed.

    Examples
    --------
    ::

       import cma, numpy
       # assume some data are available from previous runs
       cma.disp(None,numpy.r_[0,-1])  # first and last
       cma.disp(None,numpy.r_[0:1e9:100,-1]) # every 100-th and last
       cma.disp(idx=numpy.r_[0,-10:0]) # first and ten last
       cma.disp(idx=numpy.r_[0:1e9:1e3,-10:0])

    :See: `CMADataLogger.disp()`

    """
    return CMADataLogger(name if name else 'outcmaes'
                         ).disp(idx)

#____________________________________________________________
def _fileToMatrix(file_name):
    """rudimentary method to read in data from a file"""
    # TODO: np.loadtxt() might be an alternative
    #     try:
    if 1 < 3:
        lres = []
        for line in open(file_name, 'r').readlines():
            if len(line) > 0 and line[0] not in ('%', '#'):
                lres.append(list(map(float, line.split())))
        res = lres
    else:
        fil = open(file_name, 'r')
        fil.readline() # rudimentary, assume one comment line
        lineToRow = lambda line: list(map(float, line.split()))
        res = list(map(lineToRow, fil.readlines()))
        fil.close()  # close file could be omitted, reference counting should do during garbage collection, but...

    while res != [] and res[0] == []:  # remove further leading empty lines
        del res[0]
    return res
    #     except:
    print('could not read file ' + file_name)

#____________________________________________________________
#____________________________________________________________
class NoiseHandler(object):
    """Noise handling according to [Hansen et al 2009, A Method for Handling
    Uncertainty in Evolutionary Optimization...]

    The interface of this class is yet versatile and subject to changes.

    The attribute ``evaluations`` serves to control the noise via number of
    evaluations, for example with `ask_and_eval()`, see also parameter
    ``maxevals`` and compare the example.

    Example
    -------
    >>> import cma, numpy as np
    >>> func = cma.Fcts.noisysphere
    >>> es = cma.CMAEvolutionStrategy(np.ones(10), 1)
    >>> logger = cma.CMADataLogger().register(es)
    >>> nh = cma.NoiseHandler(es.N, maxevals=[1, 30])
    >>> while not es.stop():
    ...     X, fit = es.ask_and_eval(func, evaluations=nh.evaluations)
    ...     es.tell(X, fit)  # prepare for next iteration
    ...     es.sigma *= nh(X, fit, func, es.ask)  # see method __call__
    ...     es.countevals += nh.evaluations_just_done  # this is a hack, not important though
    ...     logger.add(more_data = [nh.evaluations, nh.noiseS])  # add a data point
    ...     es.disp()
    ...     # nh.maxevals = ...  it might be useful to start with smaller values and then increase
    >>> print(es.stop())
    >>> print(es.result()[-2])  # take mean value, the best solution is totally off
    >>> assert sum(es.result()[-2]**2) < 1e-9
    >>> print(X[np.argmin(fit)])  # not bad, but probably worse than the mean
    >>> logger.plot()

    The noise options of `fmin()` control a `NoiseHandler` instance similar to this
    example. The command ``cma.Options('noise')`` lists in effect the parameters of
    `__init__` apart from ``aggregate``.

    Details
    -------
    The parameters reevals, theta, c_s, and alpha_t are set differently
    than in the original publication, see method `__init__()`. For a
    very small population size, say popsize <= 5, the measurement
    technique based on rank changes is likely to fail.

    Missing Features
    ----------------
    In case no noise is found, ``self.lam_reeval`` should be adaptive
    and get at least as low as 1 (however the possible savings from this
    are rather limited). Another option might be to decide during the
    first call by a quantitative analysis of fitness values whether
    ``lam_reeval`` is set to zero. More generally, an automatic noise
    mode detection might also set the covariance matrix learning rates
    to smaller values.

    :See: `fmin()`, `ask_and_eval()`

    """
    def __init__(self, N, maxevals=10, aggregate=np.median, reevals=None, epsilon=1e-7, parallel=False):
        """parameters are
            `N`
                dimension
            `maxevals`
                maximal value for ``self.evaluations``, where
                ``self.evaluations`` function calls are aggregated for
                noise treatment. With ``maxevals == 0`` the noise
                handler is (temporarily) "switched off". If `maxevals`
                is a list, min value and (for >2 elements) median are
                used to define minimal and initial value of
                ``self.evaluations``. Choosing ``maxevals > 1`` is only
                reasonable, if also the original ``fit`` values (that
                are passed to `__call__`) are computed by aggregation of
                ``self.evaluations`` values (otherwise the values are
                not comparable), as it is done within `fmin()`.
            `aggregate`
                function to aggregate single f-values to a 'fitness', e.g.
                ``np.median``.
            `reevals`
                number of solutions to be reevaluated for noise measurement,
                can be a float, by default set to ``1.5 + popsize/20``,
                zero switches noise handling off.
            `epsilon`
                multiplier for perturbation of the reevaluated solutions
            `parallel`
                a single f-call with all resampled solutions

            :See: `fmin()`, `Options`, `CMAEvolutionStrategy.ask_and_eval()`

        """
        self.lam_reeval = reevals  # 2 + popsize/20, see method indices(), originally 2 + popsize/10
        self.epsilon = epsilon
        self.parallel = parallel
        self.theta = 0.5  # originally 0.2
        self.cum = 0.3  # originally 1, 0.3 allows one disagreement of current point with resulting noiseS
        self.alphasigma = 1 + 2 / (N+10)
        self.alphaevals = 1 + 2 / (N+10)  # originally 1.5
        self.alphaevalsdown = self.alphaevals**-0.25  # originally 1/1.5
        self.evaluations = 1  # to aggregate for a single f-evaluation
        self.minevals = 1
        self.maxevals = int(np.max(maxevals))
        if hasattr(maxevals, '__contains__'):  # i.e. can deal with ``in``
            if len(maxevals) > 1:
                self.minevals = min(maxevals)
                self.evaluations = self.minevals
            if len(maxevals) > 2:
                self.evaluations = np.median(maxevals)
        self.f_aggregate = aggregate
        self.evaluations_just_done = 0  # actually conducted evals, only for documentation
        self.noiseS = 0

    def __call__(self, X, fit, func, ask=None, args=()):
        """proceed with noise measurement, set anew attributes ``evaluations``
        (proposed number of evaluations to "treat" noise) and ``evaluations_just_done``
        and return a factor for increasing sigma.

        Parameters
        ----------
            `X`
                a list/sequence/vector of solutions
            `fit`
                the respective list of function values
            `func`
                the objective function, ``fit[i]`` corresponds to ``func(X[i], *args)``
            `ask`
                a method to generate a new, slightly disturbed solution. The argument
                is mandatory if ``epsilon`` is not zero, see `__init__()`.
            `args`
                optional additional arguments to `func`

        Details
        -------
        Calls the methods ``reeval()``, ``update_measure()`` and ``treat()`` in this order.
        ``self.evaluations`` is adapted within the method `treat()`.

        """
        self.evaluations_just_done = 0
        if not self.maxevals or self.lam_reeval == 0:
            return 1.0
        res = self.reeval(X, fit, func, ask, args)
        if not len(res):
            return 1.0
        self.update_measure()
        return self.treat()

    def get_evaluations(self):
        """return ``self.evaluations``, the number of evalutions to get a single fitness measurement"""
        return self.evaluations

    def treat(self):
        """adapt self.evaluations depending on the current measurement value
        and return ``sigma_fac in (1.0, self.alphasigma)``

        """
        if self.noiseS > 0:
            self.evaluations = min((self.evaluations * self.alphaevals, self.maxevals))
            return self.alphasigma
        else:
            self.evaluations = max((self.evaluations * self.alphaevalsdown, self.minevals))
            return 1.0

    def reeval(self, X, fit, func, ask, args=()):
        """store two fitness lists, `fit` and ``fitre`` reevaluating some
        solutions in `X`.
        ``self.evaluations`` evaluations are done for each reevaluated
        fitness value.
        See `__call__()`, where `reeval()` is called.

        """
        self.fit = list(fit)
        self.fitre = list(fit)
        self.idx = self.indices(fit)
        if not len(self.idx):
            return self.idx
        evals = int(self.evaluations) if self.f_aggregate else 1
        fagg = np.median if self.f_aggregate is None else self.f_aggregate
        for i in self.idx:
            if self.epsilon:
                if self.parallel:
                    self.fitre[i] = fagg(func(ask(evals, X[i], self.epsilon), *args))
                else:
                    self.fitre[i] = fagg([func(ask(1, X[i], self.epsilon)[0], *args)
                                            for _k in xrange(evals)])
            else:
                self.fitre[i] = fagg([func(X[i], *args) for _k in xrange(evals)])
        self.evaluations_just_done = evals * len(self.idx)
        return self.fit, self.fitre, self.idx

    def update_measure(self):
        """updated noise level measure using two fitness lists ``self.fit`` and
        ``self.fitre``, return ``self.noiseS, all_individual_measures``.

        Assumes that `self.idx` contains the indices where the fitness
        lists differ

        """
        lam = len(self.fit)
        idx = np.argsort(self.fit + self.fitre)
        ranks = np.argsort(idx).reshape((2, lam))
        rankDelta = ranks[0] - ranks[1] - np.sign(ranks[0] - ranks[1])

        # compute rank change limits using both ranks[0] and ranks[1]
        r = np.arange(1, 2 * lam)  # 2 * lam - 2 elements
        limits = [0.5 * (Mh.prctile(np.abs(r - (ranks[0,i] + 1 - (ranks[0,i] > ranks[1,i]))),
                                      self.theta*50) +
                         Mh.prctile(np.abs(r - (ranks[1,i] + 1 - (ranks[1,i] > ranks[0,i]))),
                                      self.theta*50))
                    for i in self.idx]
        # compute measurement
        #                               max: 1 rankchange in 2*lambda is always fine
        s = np.abs(rankDelta[self.idx]) - Mh.amax(limits, 1)  # lives roughly in 0..2*lambda
        self.noiseS += self.cum * (np.mean(s) - self.noiseS)
        return self.noiseS, s

    def indices(self, fit):
        """return the set of indices to be reevaluted for noise measurement,
        taking the ``lam_reeval`` best from the first ``2 * lam_reeval + 2``
        values.

        Given the first values are the earliest, this is a useful policy also
        with a time changing objective.

        """
        lam = self.lam_reeval if self.lam_reeval else 2 + len(fit) / 20
        reev = int(lam) + ((lam % 1) > np.random.rand())
        return np.argsort(array(fit, copy=False)[:2 * (reev + 1)])[:reev]

#____________________________________________________________
#____________________________________________________________
class Sections(object):
    """plot sections through an objective function. A first
    rational thing to do, when facing an (expensive) application.
    By default 6 points in each coordinate are evaluated.
    This class is still experimental.

    Examples
    --------

    >>> import cma, numpy as np
    >>> s = cma.Sections(cma.Fcts.rosen, np.zeros(3)).do(plot=False)
    >>> s.do(plot=False)  # evaluate the same points again, i.e. check for noise
    >>> try:
    ...     s.plot()
    ... except:
    ...     print('plotting failed: pylab package is missing?')

    Details
    -------
    Data are saved after each function call during `do()`. The filename is attribute
    ``name`` and by default ``str(func)``, see `__init__()`.

    A random (orthogonal) basis can be generated with ``cma.Rotation()(np.eye(3))``.

    The default name is unique in the function name, but it should be unique in all
    parameters of `__init__()` but `plot_cmd` and `load`.

    ``self.res`` is a dictionary with an entry for each "coordinate" ``i`` and with an
    entry ``'x'``, the middle point. Each entry ``i`` is again a dictionary with keys
    being different dx values and the value being a sequence of f-values.
    For example ``self.res[2][0.1] == [0.01, 0.01]``, which is generated using the
    difference vector ``self.basis[2]`` like
    ``self.res[2][dx] += func(self.res['x'] + dx * self.basis[2])``.

    :See: `__init__()`

    """
    def __init__(self, func, x, args=(), basis=None, name=None,
                 plot_cmd=pylab.plot if pylab else None, load=True):
        """
        Parameters
        ----------
            `func`
                objective function
            `x`
                point in search space, middle point of the sections
            `args`
                arguments passed to `func`
            `basis`
                evaluated points are ``func(x + locations[j] * basis[i]) for i in len(basis) for j in len(locations)``,
                see `do()`
            `name`
                filename where to save the result
            `plot_cmd`
                command used to plot the data, typically matplotlib pylabs `plot` or `semilogy`
            `load`
                load previous data from file ``str(func) + '.pkl'``

        """
        self.func = func
        self.args = args
        self.x = x
        self.name = name if name else str(func).replace(' ', '_').replace('>', '').replace('<', '')
        self.plot_cmd = plot_cmd  # or semilogy
        self.basis = np.eye(len(x)) if basis is None else basis

        try:
            self.load()
            if any(self.res['x'] != x):
                self.res = {}
                self.res['x'] = x  # TODO: res['x'] does not look perfect
            else:
                print(self.name + ' loaded')
        except:
            self.res = {}
            self.res['x'] = x

    def do(self, repetitions=1, locations=np.arange(-0.5, 0.6, 0.2), plot=True):
        """generates, plots and saves function values ``func(y)``,
        where ``y`` is 'close' to `x` (see `__init__()`). The data are stored in
        the ``res`` attribute and the class instance is saved in a file
        with (the weired) name ``str(func)``.

        Parameters
        ----------
            `repetitions`
                for each point, only for noisy functions is >1 useful. For
                ``repetitions==0`` only already generated data are plotted.
            `locations`
                coordinated wise deviations from the middle point given in `__init__`

        """
        if not repetitions:
            self.plot()
            return

        res = self.res
        for i in range(len(self.basis)): # i-th coordinate
            if i not in res:
                res[i] = {}
            # xx = np.array(self.x)
            # TODO: store res[i]['dx'] = self.basis[i] here?
            for dx in locations:
                xx = self.x + dx * self.basis[i]
                xkey = dx  # xx[i] if (self.basis == np.eye(len(self.basis))).all() else dx
                if xkey not in res[i]:
                    res[i][xkey] = []
                n = repetitions
                while n > 0:
                    n -= 1
                    res[i][xkey].append(self.func(xx, *self.args))
                    if plot:
                        self.plot()
                    self.save()
        return self

    def plot(self, plot_cmd=None, tf=lambda y: y):
        """plot the data we have, return ``self``"""
        if not plot_cmd:
            plot_cmd = self.plot_cmd
        colors = 'bgrcmyk'
        pylab.hold(False)
        res = self.res

        flatx, flatf = self.flattened()
        minf = np.inf
        for i in flatf:
            minf = min((minf, min(flatf[i])))
        addf = 1e-9 - minf  if minf <= 0 else 0
        for i in sorted(res.keys()):  # we plot not all values here
            if type(i) is int:
                color = colors[i % len(colors)]
                arx = sorted(res[i].keys())
                plot_cmd(arx, [tf(np.median(res[i][x]) + addf) for x in arx], color + '-')
                pylab.text(arx[-1], tf(np.median(res[i][arx[-1]])), i)
                pylab.hold(True)
                plot_cmd(flatx[i], tf(np.array(flatf[i]) + addf), color + 'o')
        pylab.ylabel('f + ' + str(addf))
        pylab.draw()
        show()
        # raw_input('press return')
        return self

    def flattened(self):
        """return flattened data ``(x, f)`` such that for the sweep through
        coordinate ``i`` we have for data point ``j`` that ``f[i][j] == func(x[i][j])``

        """
        flatx = {}
        flatf = {}
        for i in self.res:
            if type(i) is int:
                flatx[i] = []
                flatf[i] = []
                for x in sorted(self.res[i]):
                    for d in sorted(self.res[i][x]):
                        flatx[i].append(x)
                        flatf[i].append(d)
        return flatx, flatf

    def save(self, name=None):
        """save to file"""
        import pickle
        name = name if name else self.name
        fun = self.func
        del self.func  # instance method produces error
        pickle.dump(self, open(name + '.pkl', "wb" ))
        self.func = fun
        return self

    def load(self, name=None):
        """load from file"""
        import pickle
        name = name if name else self.name
        s = pickle.load(open(name + '.pkl', 'rb'))
        self.res = s.res  # disregard the class
        return self
#____________________________________________________________
#____________________________________________________________
class _Error(Exception):
    """generic exception of cma module"""
    pass

#____________________________________________________________
#____________________________________________________________
#
class ElapsedTime(object):
    """32-bit C overflows after int(2**32/1e6) == 4294s about 72 min"""
    def __init__(self):
        self.tic0 = time.clock()
        self.tic = self.tic0
        self.lasttoc = time.clock()
        self.lastdiff = time.clock() - self.lasttoc
        self.time_to_add = 0
        self.messages = 0

    def __call__(self):
        toc = time.clock()
        if toc - self.tic >= self.lasttoc - self.tic:
            self.lastdiff = toc - self.lasttoc
            self.lasttoc = toc
        else:  # overflow, reset self.tic
            if self.messages < 3:
                self.messages += 1
                print('  in cma.ElapsedTime: time measure overflow, last difference estimated from',
                        self.tic0, self.tic, self.lasttoc, toc, toc - self.lasttoc, self.lastdiff)

            self.time_to_add += self.lastdiff + self.lasttoc - self.tic
            self.tic = toc  # reset
            self.lasttoc = toc
        self.elapsedtime = toc - self.tic + self.time_to_add
        return self.elapsedtime

#____________________________________________________________
#____________________________________________________________
#
class TimeIt(object):
    def __init__(self, fct, args=(), seconds=1):
        pass

class Misc(object):
    #____________________________________________________________
    #____________________________________________________________
    #
    class MathHelperFunctions(object):
        """static convenience math helper functions, if the function name
        is preceded with an "a", a numpy array is returned

        """
        @staticmethod
        def aclamp(x, upper):
            return -Misc.MathHelperFunctions.apos(-x, -upper)
        @staticmethod
        def expms(A, eig=np.linalg.eigh):
            """matrix exponential for a symmetric matrix"""
            # TODO: check that this works reliably for low rank matrices
            # first: symmetrize A
            D, B = eig(A)
            return np.dot(B, (np.exp(D) * B).T)
        @staticmethod
        def amax(vec, vec_or_scalar):
            return array(Misc.MathHelperFunctions.max(vec, vec_or_scalar))
        @staticmethod
        def max(vec, vec_or_scalar):
            b = vec_or_scalar
            if np.isscalar(b):
                m = [max(x, b) for x in vec]
            else:
                m = [max(vec[i], b[i]) for i in xrange(len(vec))]
            return m
        @staticmethod
        def amin(vec_or_scalar, vec_or_scalar2):
            return array(Misc.MathHelperFunctions.min(vec_or_scalar, vec_or_scalar2))
        @staticmethod
        def min(a, b):
            iss = np.isscalar
            if iss(a) and iss(b):
                return min(a, b)
            if iss(a):
                a, b = b, a
            # now only b can be still a scalar
            if iss(b):
                return [min(x, b) for x in a]
            else:  # two non-scalars must have the same length
                return [min(a[i], b[i]) for i in xrange(len(a))]
        @staticmethod
        def norm(vec, expo=2):
            return sum(vec**expo)**(1/expo)
        @staticmethod
        def apos(x, lower=0):
            """clips argument (scalar or array) from below at lower"""
            if lower == 0:
                return (x > 0) * x
            else:
                return lower + (x > lower) * (x - lower)
        @staticmethod
        def prctile(data, p_vals=[0, 25, 50, 75, 100], sorted_=False):
            """``prctile(data, 50)`` returns the median, but p_vals can
            also be a sequence.

            Provides for small samples better values than matplotlib.mlab.prctile,
            however also slower.

            """
            ps = [p_vals] if np.isscalar(p_vals) else p_vals

            if not sorted_:
                data = sorted(data)
            n = len(data)
            d = []
            for p in ps:
                fi = p * n / 100 - 0.5
                if fi <= 0:  # maybe extrapolate?
                    d.append(data[0])
                elif fi >= n - 1:
                    d.append(data[-1])
                else:
                    i = int(fi)
                    d.append((i+1 - fi) * data[i] + (fi - i) * data[i+1])
            return d[0] if np.isscalar(p_vals) else d
        @staticmethod
        def sround(nb):  # TODO: to be vectorized
            """return stochastic round: floor(nb) + (rand()<remainder(nb))"""
            return nb // 1 + (np.random.rand(1)[0] < (nb % 1))

        @staticmethod
        def cauchy_with_variance_one():
            n = np.random.randn() / np.random.randn()
            while abs(n) > 1000:
                n = np.random.randn() / np.random.randn()
            return n / 25
        @staticmethod
        def standard_finite_cauchy(size=1):
            try:
                l = len(size)
            except TypeError:
                l = 0

            if l == 0:
                return array([Mh.cauchy_with_variance_one() for _i in xrange(size)])
            elif l == 1:
                return array([Mh.cauchy_with_variance_one() for _i in xrange(size[0])])
            elif l == 2:
                return array([[Mh.cauchy_with_variance_one() for _i in xrange(size[1])]
                             for _j in xrange(size[0])])
            else:
                raise _Error('len(size) cannot be large than two')


    @staticmethod
    def likelihood(x, m=None, Cinv=None, sigma=1, detC=None):
        """return likelihood of x for the normal density N(m, sigma**2 * Cinv**-1)"""
        # testing: MC integrate must be one: mean(p(x_i)) * volume(where x_i are uniformely sampled)
        # for i in range(3): print mean([cma.likelihood(20*r-10, dim * [0], None, 3) for r in rand(10000,dim)]) * 20**dim
        if m is None:
            dx = x
        else:
            dx = x - m  # array(x) - array(m)
        n = len(x)
        s2pi = (2*np.pi)**(n/2.)
        if Cinv is None:
            return exp(-sum(dx**2) / sigma**2 / 2) / s2pi / sigma**n
        if detC is None:
            detC = 1. / np.linalg.linalg.det(Cinv)
        return  exp(-np.dot(dx, np.dot(Cinv, dx)) / sigma**2 / 2) / s2pi / abs(detC)**0.5 / sigma**n

    @staticmethod
    def loglikelihood(self, x, previous=False):
        """return log-likelihood of `x` regarding the current sample distribution"""
        # testing of original fct: MC integrate must be one: mean(p(x_i)) * volume(where x_i are uniformely sampled)
        # for i in range(3): print mean([cma.likelihood(20*r-10, dim * [0], None, 3) for r in rand(10000,dim)]) * 20**dim
        # TODO: test this!!
        # c=cma.fmin...
        # c[3]['cma'].loglikelihood(...)

        if previous and hasattr(self, 'lastiter'):
            sigma = self.lastiter.sigma
            Crootinv = self.lastiter._Crootinv
            xmean = self.lastiter.mean
            D = self.lastiter.D
        elif previous and self.countiter > 1:
            raise _Error('no previous distribution parameters stored, check options importance_mixing')
        else:
            sigma = self.sigma
            Crootinv = self._Crootinv
            xmean = self.mean
            D = self.D

        dx = array(x) - xmean  # array(x) - array(m)
        n = self.N
        logs2pi = n * log(2*np.pi) / 2.
        logdetC = 2 * sum(log(D))
        dx = np.dot(Crootinv, dx)
        res = -sum(dx**2) / sigma**2 / 2 - logs2pi - logdetC/2 - n*log(sigma)
        if 1 < 3: # testing
            s2pi = (2*np.pi)**(n/2.)
            detC = np.prod(D)**2
            res2 = -sum(dx**2) / sigma**2 / 2 - log(s2pi * abs(detC)**0.5 * sigma**n)
            assert res2 < res + 1e-8 or res2 > res - 1e-8
        return res

    #____________________________________________________________
    #____________________________________________________________
    #
    # C and B are arrays rather than matrices, because they are
    # addressed via B[i][j], matrices can only be addressed via B[i,j]

    # tred2(N, B, diagD, offdiag);
    # tql2(N, diagD, offdiag, B);


    # Symmetric Householder reduction to tridiagonal form, translated from JAMA package.
    @staticmethod
    def eig(C):
        """eigendecomposition of a symmetric matrix, much slower than
        `numpy.linalg.eigh`, return ``(EVals, Basis)``, the eigenvalues
        and an orthonormal basis of the corresponding eigenvectors, where

            ``Basis[i]``
                the i-th row of ``Basis``
            columns of ``Basis``, ``[Basis[j][i] for j in range(len(Basis))]``
                the i-th eigenvector with eigenvalue ``EVals[i]``

        """

    # class eig(object):
    #     def __call__(self, C):

    # Householder transformation of a symmetric matrix V into tridiagonal form.
        # -> n             : dimension
        # -> V             : symmetric nxn-matrix
        # <- V             : orthogonal transformation matrix:
        #                    tridiag matrix == V * V_in * V^t
        # <- d             : diagonal
        # <- e[0..n-1]     : off diagonal (elements 1..n-1)

        # Symmetric tridiagonal QL algorithm, iterative
        # Computes the eigensystem from a tridiagonal matrix in roughtly 3N^3 operations
        # -> n     : Dimension.
        # -> d     : Diagonale of tridiagonal matrix.
        # -> e[1..n-1] : off-diagonal, output from Householder
        # -> V     : matrix output von Householder
        # <- d     : eigenvalues
        # <- e     : garbage?
        # <- V     : basis of eigenvectors, according to d


        #  tred2(N, B, diagD, offdiag); B=C on input
        #  tql2(N, diagD, offdiag, B);

        #  private void tred2 (int n, double V[][], double d[], double e[]) {
        def tred2 (n, V, d, e):
            #  This is derived from the Algol procedures tred2 by
            #  Bowdler, Martin, Reinsch, and Wilkinson, Handbook for
            #  Auto. Comp., Vol.ii-Linear Algebra, and the corresponding
            #  Fortran subroutine in EISPACK.

            num_opt = False  # factor 1.5 in 30-D

            for j in range(n):
                d[j] = V[n-1][j] # d is output argument

            # Householder reduction to tridiagonal form.

            for i in range(n-1,0,-1):
                # Scale to avoid under/overflow.
                h = 0.0
                if not num_opt:
                    scale = 0.0
                    for k in range(i):
                        scale = scale + abs(d[k])
                else:
                    scale = sum(abs(d[0:i]))

                if scale == 0.0:
                    e[i] = d[i-1]
                    for j in range(i):
                        d[j] = V[i-1][j]
                        V[i][j] = 0.0
                        V[j][i] = 0.0
                else:

                    # Generate Householder vector.
                    if not num_opt:
                        for k in range(i):
                            d[k] /= scale
                            h += d[k] * d[k]
                    else:
                        d[:i] /= scale
                        h = np.dot(d[:i],d[:i])

                    f = d[i-1]
                    g = h**0.5

                    if f > 0:
                        g = -g

                    e[i] = scale * g
                    h = h - f * g
                    d[i-1] = f - g
                    if not num_opt:
                        for j in range(i):
                            e[j] = 0.0
                    else:
                        e[:i] = 0.0

                    # Apply similarity transformation to remaining columns.

                    for j in range(i):
                        f = d[j]
                        V[j][i] = f
                        g = e[j] + V[j][j] * f
                        if not num_opt:
                            for k in range(j+1, i):
                                g += V[k][j] * d[k]
                                e[k] += V[k][j] * f
                            e[j] = g
                        else:
                            e[j+1:i] += V.T[j][j+1:i] * f
                            e[j] = g + np.dot(V.T[j][j+1:i],d[j+1:i])

                    f = 0.0
                    if not num_opt:
                        for j in range(i):
                            e[j] /= h
                            f += e[j] * d[j]
                    else:
                        e[:i] /= h
                        f += np.dot(e[:i],d[:i])

                    hh = f / (h + h)
                    if not num_opt:
                        for j in range(i):
                            e[j] -= hh * d[j]
                    else:
                        e[:i] -= hh * d[:i]

                    for j in range(i):
                        f = d[j]
                        g = e[j]
                        if not num_opt:
                            for k in range(j, i):
                                V[k][j] -= (f * e[k] + g * d[k])
                        else:
                            V.T[j][j:i] -= (f * e[j:i] + g * d[j:i])

                        d[j] = V[i-1][j]
                        V[i][j] = 0.0

                d[i] = h
            # end for i--

            # Accumulate transformations.

            for i in range(n-1):
                V[n-1][i] = V[i][i]
                V[i][i] = 1.0
                h = d[i+1]
                if h != 0.0:
                    if not num_opt:
                        for k in range(i+1):
                            d[k] = V[k][i+1] / h
                    else:
                        d[:i+1] = V.T[i+1][:i+1] / h

                    for j in range(i+1):
                        if not num_opt:
                            g = 0.0
                            for k in range(i+1):
                                g += V[k][i+1] * V[k][j]
                            for k in range(i+1):
                                V[k][j] -= g * d[k]
                        else:
                            g = np.dot(V.T[i+1][0:i+1], V.T[j][0:i+1])
                            V.T[j][:i+1] -= g * d[:i+1]

                if not num_opt:
                    for k in range(i+1):
                        V[k][i+1] = 0.0
                else:
                    V.T[i+1][:i+1] = 0.0


            if not num_opt:
                for j in range(n):
                    d[j] = V[n-1][j]
                    V[n-1][j] = 0.0
            else:
                d[:n] = V[n-1][:n]
                V[n-1][:n] = 0.0

            V[n-1][n-1] = 1.0
            e[0] = 0.0


        # Symmetric tridiagonal QL algorithm, taken from JAMA package.
        # private void tql2 (int n, double d[], double e[], double V[][]) {
        # needs roughly 3N^3 operations
        def tql2 (n, d, e, V):

            #  This is derived from the Algol procedures tql2, by
            #  Bowdler, Martin, Reinsch, and Wilkinson, Handbook for
            #  Auto. Comp., Vol.ii-Linear Algebra, and the corresponding
            #  Fortran subroutine in EISPACK.

            num_opt = False  # using vectors from numpy makes it faster

            if not num_opt:
                for i in range(1,n): # (int i = 1; i < n; i++):
                    e[i-1] = e[i]
            else:
                e[0:n-1] = e[1:n]
            e[n-1] = 0.0

            f = 0.0
            tst1 = 0.0
            eps = 2.0**-52.0
            for l in range(n): # (int l = 0; l < n; l++) {

                # Find small subdiagonal element

                tst1 = max(tst1, abs(d[l]) + abs(e[l]))
                m = l
                while m < n:
                    if abs(e[m]) <= eps*tst1:
                        break
                    m += 1

                # If m == l, d[l] is an eigenvalue,
                # otherwise, iterate.

                if m > l:
                    iiter = 0
                    while 1: # do {
                        iiter += 1  # (Could check iteration count here.)

                        # Compute implicit shift

                        g = d[l]
                        p = (d[l+1] - g) / (2.0 * e[l])
                        r = (p**2 + 1)**0.5  # hypot(p,1.0)
                        if p < 0:
                            r = -r

                        d[l] = e[l] / (p + r)
                        d[l+1] = e[l] * (p + r)
                        dl1 = d[l+1]
                        h = g - d[l]
                        if not num_opt:
                            for i in range(l+2, n):
                                d[i] -= h
                        else:
                            d[l+2:n] -= h

                        f = f + h

                        # Implicit QL transformation.

                        p = d[m]
                        c = 1.0
                        c2 = c
                        c3 = c
                        el1 = e[l+1]
                        s = 0.0
                        s2 = 0.0

                        # hh = V.T[0].copy()  # only with num_opt
                        for i in range(m-1, l-1, -1): # (int i = m-1; i >= l; i--) {
                            c3 = c2
                            c2 = c
                            s2 = s
                            g = c * e[i]
                            h = c * p
                            r = (p**2 + e[i]**2)**0.5  # hypot(p,e[i])
                            e[i+1] = s * r
                            s = e[i] / r
                            c = p / r
                            p = c * d[i] - s * g
                            d[i+1] = h + s * (c * g + s * d[i])

                            # Accumulate transformation.

                            if not num_opt: # overall factor 3 in 30-D
                                for k in range(n): # (int k = 0; k < n; k++) {
                                    h = V[k][i+1]
                                    V[k][i+1] = s * V[k][i] + c * h
                                    V[k][i] = c * V[k][i] - s * h
                            else: # about 20% faster in 10-D
                                hh = V.T[i+1].copy()
                                # hh[:] = V.T[i+1][:]
                                V.T[i+1] = s * V.T[i] + c * hh
                                V.T[i] = c * V.T[i] - s * hh
                                # V.T[i] *= c
                                # V.T[i] -= s * hh

                        p = -s * s2 * c3 * el1 * e[l] / dl1
                        e[l] = s * p
                        d[l] = c * p

                        # Check for convergence.
                        if abs(e[l]) <= eps*tst1:
                            break
                    # } while (Math.abs(e[l]) > eps*tst1);

                d[l] = d[l] + f
                e[l] = 0.0


            # Sort eigenvalues and corresponding vectors.
            if 11 < 3:
                for i in range(n-1): # (int i = 0; i < n-1; i++) {
                    k = i
                    p = d[i]
                    for j in range(i+1, n): # (int j = i+1; j < n; j++) {
                        if d[j] < p: # NH find smallest k>i
                            k = j
                            p = d[j]

                    if k != i:
                        d[k] = d[i] # swap k and i
                        d[i] = p
                        for j in range(n): # (int j = 0; j < n; j++) {
                            p = V[j][i]
                            V[j][i] = V[j][k]
                            V[j][k] = p
        # tql2

        N = len(C[0])
        if 11 < 3:
            V = np.array([x[:] for x in C])  # copy each "row"
            N = V[0].size
            d = np.zeros(N)
            e = np.zeros(N)
        else:
            V = [[x[i] for i in xrange(N)] for x in C]  # copy each "row"
            d = N * [0.]
            e = N * [0.]

        tred2(N, V, d, e)
        tql2(N, d, e, V)
        return (array(d), array(V))
Mh = Misc.MathHelperFunctions
def pprint(to_be_printed):
    """nicely formated print"""
    try:
        import pprint as pp
        # generate an instance PrettyPrinter
        # pp.PrettyPrinter().pprint(to_be_printed)
        pp.pprint(to_be_printed)
    except ImportError:
        print('could not use pprint module, will apply regular print')
        print(to_be_printed)
class Rotation(object):
    """Rotation class that implements an orthogonal linear transformation,
    one for each dimension. Used to implement non-separable test functions.

    Example:

    >>> import cma, numpy as np
    >>> R = cma.Rotation()
    >>> R2 = cma.Rotation() # another rotation
    >>> x = np.array((1,2,3))
    >>> print(R(R(x), inverse=1))
    [ 1.  2.  3.]

    """
    dicMatrices = {}  # store matrix if necessary, for each dimension
    def __init__(self):
        self.dicMatrices = {} # otherwise there might be shared bases which is probably not what we want
    def __call__(self, x, inverse=False): # function when calling an object
        """Rotates the input array `x` with a fixed rotation matrix
           (``self.dicMatrices['str(len(x))']``)
        """
        N = x.shape[0]  # can be an array or matrix, TODO: accept also a list of arrays?
        if str(N) not in self.dicMatrices: # create new N-basis for once and all
            B = np.random.randn(N, N)
            for i in xrange(N):
                for j in xrange(0, i):
                    B[i] -= np.dot(B[i], B[j]) * B[j]
                B[i] /= sum(B[i]**2)**0.5
            self.dicMatrices[str(N)] = B
        if inverse:
            return np.dot(self.dicMatrices[str(N)].T, x)  # compute rotation
        else:
            return np.dot(self.dicMatrices[str(N)], x)  # compute rotation
# Use rotate(x) to rotate x
rotate = Rotation()

#____________________________________________________________
#____________________________________________________________
#
class FitnessFunctions(object):
    """ versatile container for test objective functions """

    def __init__(self):
        self.counter = 0  # number of calls or any other practical use
    def rot(self, x, fun, rot=1, args=()):
        """returns ``fun(rotation(x), *args)``, ie. `fun` applied to a rotated argument"""
        if len(np.shape(array(x))) > 1:  # parallelized
            res = []
            for x in x:
                res.append(self.rot(x, fun, rot, args))
            return res

        if rot:
            return fun(rotate(x, *args))
        else:
            return fun(x)
    def somenan(self, x, fun, p=0.1):
        """returns sometimes np.NaN, otherwise fun(x)"""
        if np.random.rand(1) < p:
            return np.NaN
        else:
            return fun(x)
    def rand(self, x):
        """Random test objective function"""
        return np.random.random(1)[0]
    def linear(self, x):
        return -x[0]
    def lineard(self, x):
        if 1 < 3 and any(array(x) < 0):
            return np.nan
        if 1 < 3 and sum([ (10 + i) * x[i] for i in xrange(len(x))]) > 50e3:
            return np.nan
        return -sum(x)
    def sphere(self, x):
        """Sphere (squared norm) test objective function"""
        # return np.random.rand(1)[0]**0 * sum(x**2) + 1 * np.random.rand(1)[0]
        return sum((x+0)**2)
    def spherewithoneconstraint(self, x):
        return sum((x+0)**2) if x[0] > 1 else np.nan
    def elliwithoneconstraint(self, x, idx=[-1]):
        return self.ellirot(x) if all(array(x)[idx] > 1) else np.nan

    def spherewithnconstraints(self, x):
        return sum((x+0)**2) if all(array(x) > 1) else np.nan

    def noisysphere(self, x, noise=4.0, cond=1.0):
        """noise=10 does not work with default popsize, noise handling does not help """
        return self.elli(x, cond=cond) * (1 + noise * np.random.randn() / len(x))
    def spherew(self, x):
        """Sphere (squared norm) with sum x_i = 1 test objective function"""
        # return np.random.rand(1)[0]**0 * sum(x**2) + 1 * np.random.rand(1)[0]
        # s = sum(abs(x))
        # return sum((x/s+0)**2) - 1/len(x)
        # return sum((x/s)**2) - 1/len(x)
        return -0.01*x[0] + abs(x[0])**-2 * sum(x[1:]**2)
    def partsphere(self, x):
        """Sphere (squared norm) test objective function"""
        self.counter += 1
        # return np.random.rand(1)[0]**0 * sum(x**2) + 1 * np.random.rand(1)[0]
        dim = len(x)
        x = array([x[i % dim] for i in range(2*dim)])
        N = 8
        i = self.counter % dim
        #f = sum(x[i:i + N]**2)
        f = sum(x[np.random.randint(dim, size=N)]**2)
        return f
    def sectorsphere(self, x):
        """asymmetric Sphere (squared norm) test objective function"""
        return sum(x**2) + (1e6-1) * sum(x[x<0]**2)
    def cornersphere(self, x):
        """Sphere (squared norm) test objective function constraint to the corner"""
        nconstr = len(x) - 0
        if any(x[:nconstr] < 1):
            return np.NaN
        return sum(x**2) - nconstr
    def cornerelli(self, x):
        """ """
        if any(x < 1):
            return np.NaN
        return self.elli(x) - self.elli(np.ones(len(x)))
    def cornerellirot(self, x):
        """ """
        if any(x < 1):
            return np.NaN
        return self.ellirot(x)
    def normalSkew(self, f):
        N = np.random.randn(1)[0]**2
        if N < 1:
            N = f * N  # diminish blow up lower part
        return N
    def noiseC(self, x, func=sphere, fac=10, expon=0.8):
        f = func(self, x)
        N = np.random.randn(1)[0]/np.random.randn(1)[0]
        return max(1e-19, f + (float(fac)/len(x)) * f**expon * N)
    def noise(self, x, func=sphere, fac=10, expon=1):
        f = func(self, x)
        #R = np.random.randn(1)[0]
        R = np.log10(f) + expon * abs(10-np.log10(f)) * np.random.rand(1)[0]
        # sig = float(fac)/float(len(x))
        # R = log(f) + 0.5*log(f) * random.randn(1)[0]
        # return max(1e-19, f + sig * (f**np.log10(f)) * np.exp(R))
        # return max(1e-19, f * np.exp(sig * N / f**expon))
        # return max(1e-19, f * normalSkew(f**expon)**sig)
        return f + 10**R  # == f + f**(1+0.5*RN)
    def cigar(self, x, rot=0, cond=1e6):
        """Cigar test objective function"""
        if rot:
            x = rotate(x)
        x = [x] if np.isscalar(x[0]) else x  # scalar into list
        f = [x[0]**2 + cond * sum(x[1:]**2) for x in x]
        return f if len(f) > 1 else f[0]  # 1-element-list into scalar
    def tablet(self, x, rot=0):
        """Tablet test objective function"""
        if rot:
            x = rotate(x)
        x = [x] if np.isscalar(x[0]) else x  # scalar into list
        f = [1e6*x[0]**2 + sum(x[1:]**2) for x in x]
        return f if len(f) > 1 else f[0]  # 1-element-list into scalar
    def cigtab(self, y):
        """Cigtab test objective function"""
        X = [y] if np.isscalar(y[0]) else y
        f = [1e-4 * x[0]**2 + 1e4 * x[1]**2 + sum(x[2:]**2) for x in X]
        return f if len(f) > 1 else f[0]
    def twoaxes(self, y):
        """Cigtab test objective function"""
        X = [y] if np.isscalar(y[0]) else y
        N2 = len(X[0]) // 2
        f = [1e6 * sum(x[0:N2]**2) + sum(x[N2:]**2) for x in X]
        return f if len(f) > 1 else f[0]
    def ellirot(self, x):
        return fcts.elli(array(x), 1)
    def hyperelli(self, x):
        N = len(x)
        return sum((np.arange(1, N+1) * x)**2)
    def elli(self, x, rot=0, xoffset=0, cond=1e6, actuator_noise=0.0, both=False):
        """Ellipsoid test objective function"""
        if not np.isscalar(x[0]):  # parallel evaluation
            return [self.elli(xi, rot) for xi in x]  # could save 20% overall
        if rot:
            x = rotate(x)
        N = len(x)
        if actuator_noise:
            x = x + actuator_noise * np.random.randn(N)

        ftrue = sum(cond**(np.arange(N)/(N-1.))*(x+xoffset)**2)

        alpha = 0.49 + 1./N
        beta = 1
        felli = np.random.rand(1)[0]**beta * ftrue * \
                max(1, (10.**9 / (ftrue+1e-99))**(alpha*np.random.rand(1)[0]))
        # felli = ftrue + 1*np.random.randn(1)[0] / (1e-30 +
        #                                           np.abs(np.random.randn(1)[0]))**0
        if both:
            return (felli, ftrue)
        else:
            # return felli  # possibly noisy value
            return ftrue # + np.random.randn()
    def elliconstraint(self, x, cfac = 1e8, tough=True, cond=1e6):
        """ellipsoid test objective function with "constraints" """
        N = len(x)
        f = sum(cond**(np.arange(N)[-1::-1]/(N-1)) * x**2)
        cvals = (x[0] + 1,
                 x[0] + 1 + 100*x[1],
                 x[0] + 1 - 100*x[1])
        if tough:
            f += cfac * sum(max(0,c) for c in cvals)
        else:
            f += cfac * sum(max(0,c+1e-3)**2 for c in cvals)
        return f
    def rosen(self, x, alpha=1e2):
        """Rosenbrock test objective function"""
        x = [x] if np.isscalar(x[0]) else x  # scalar into list
        f = [sum(alpha*(x[:-1]**2-x[1:])**2 + (1.-x[:-1])**2) for x in x]
        return f if len(f) > 1 else f[0]  # 1-element-list into scalar
    def diffpow(self, x, rot=0):
        """Diffpow test objective function"""
        N = len(x)
        if rot:
            x = rotate(x)
        return sum(np.abs(x)**(2.+4.*np.arange(N)/(N-1.)))**0.5
    def rosenelli(self, x):
        N = len(x)
        return self.rosen(x[:N/2]) + self.elli(x[N/2:], cond=1)
    def ridge(self, x, expo=2):
        x = [x] if np.isscalar(x[0]) else x  # scalar into list
        f = [x[0] + 100*np.sum(x[1:]**2)**(expo/2.) for x in x]
        return f if len(f) > 1 else f[0]  # 1-element-list into scalar
    def ridgecircle(self, x, expo=0.5):
        """happy cat by HG Beyer"""
        a = len(x)
        s = sum(x**2)
        return ((s - a)**2)**(expo/2) + s/a + sum(x)/a
    def happycat(self, x, alpha=1./8):
        s = sum(x**2)
        return ((s - len(x))**2)**alpha + (s/2 + sum(x)) / len(x) + 0.5
    def flat(self,x):
        return 1
        return 1 if np.random.rand(1) < 0.9 else 1.1
        return np.random.randint(1,30)
    def branin(self, x):
        # in [0,15]**2
        y = x[1]
        x = x[0] + 5
        return (y - 5.1*x**2 / 4 / np.pi**2 + 5 * x / np.pi - 6)**2 + 10 * (1 - 1/8/np.pi) * np.cos(x) + 10 - 0.397887357729738160000
    def goldsteinprice(self, x):
        x1 = x[0]
        x2 = x[1]
        return (1 + (x1 +x2 + 1)**2 * (19 - 14 * x1 + 3 * x1**2 - 14 * x2 + 6 * x1 * x2 + 3 * x2**2)) * (
                30 + (2 * x1 - 3 * x2)**2 * (18 - 32 * x1 + 12 * x1**2 + 48 * x2 - 36 * x1 * x2 + 27 * x2**2)) - 3
    def griewank(self, x):
        # was in [-600 600]
        x = (600./5) * x
        return 1 - np.prod(np.cos(x/sqrt(1.+np.arange(len(x))))) + sum(x**2)/4e3
    def rastrigin(self, x):
        """Rastrigin test objective function"""
        if not np.isscalar(x[0]):
            N = len(x[0])
            return [10*N + sum(xi**2 - 10*np.cos(2*np.pi*xi)) for xi in x]
            # return 10*N + sum(x**2 - 10*np.cos(2*np.pi*x), axis=1)
        N = len(x)
        return 10*N + sum(x**2 - 10*np.cos(2*np.pi*x))
    def schaffer(self, x):
        """ Schaffer function x0 in [-100..100]"""
        N = len(x);
        s = x[0:N-1]**2 + x[1:N]**2;
        return sum(s**0.25 * (np.sin(50*s**0.1)**2 + 1))

    def schwefelelli(self, x):
        s = 0
        f = 0
        for i in xrange(len(x)):
            s += x[i]
            f += s**2
        return f
    def schwefelmult(self, x, pen_fac = 1e4):
        """multimodal Schwefel function with domain -500..500"""
        y = [x] if np.isscalar(x[0]) else x
        N = len(y[0])
        f = array([418.9829*N - 1.27275661e-5*N - sum(x * np.sin(np.abs(x)**0.5))
                + pen_fac * sum((abs(x) > 500) * (abs(x) - 500)**2) for x in y])
        return f if len(f) > 1 else f[0]
    def optprob(self, x):
        n = np.arange(len(x)) + 1
        f = n * x * (1-x)**(n-1)
        return sum(1-f)
    def lincon(self, x, theta=0.01):
        """ridge like linear function with one linear constraint"""
        if x[0] < 0:
            return np.NaN
        return theta * x[1] + x[0]
    def rosen_nesterov(self, x, rho=100):
        """needs exponential number of steps in a non-increasing f-sequence.

        x_0 = (-1,1,...,1)
        See Jarre (2011) "On Nesterov's Smooth Chebyshev-Rosenbrock Function"

        """
        f = 0.25 * (x[0] - 1)**2
        f += rho * sum((x[1:] - 2 * x[:-1]**2 + 1)**2)
        return f

fcts = FitnessFunctions()
Fcts = fcts  # for cross compatibility, as if the functions were static members of class Fcts
def felli(x): # unbound function, needed to test multiprocessor
    return sum(1e6**(np.arange(len(x))/(len(x)-1))*(x)**2)


#____________________________________________
#____________________________________________________________
def _test(module=None):  # None is fine when called from inside the module
    import doctest
    print(doctest.testmod(module))  # this is pretty coool!
def process_test(stream=None):
    """ """
    import fileinput
    s1 = ""
    s2 = ""
    s3 = ""
    state = 0
    for line in fileinput.input(stream):  # takes argv as file or stdin
        if 1 < 3:
            s3 += line
            if state < -1 and line.startswith('***'):
                print(s3)
            if line.startswith('***'):
                s3 = ""

        if state == -1:  # found a failed example line
            s1 += '\n\n*** Failed Example:' + line
            s2 += '\n\n\n'   # line
            # state = 0  # wait for 'Expected:' line

        if line.startswith('Expected:'):
            state = 1
            continue
        elif line.startswith('Got:'):
            state = 2
            continue
        elif line.startswith('***'):  # marks end of failed example
            state = 0
        elif line.startswith('Failed example:'):
            state = -1
        elif line.startswith('Exception raised'):
            state = -2

        # in effect more else:
        if state == 1:
            s1 += line + ''
        if state == 2:
            s2 += line + ''

#____________________________________________________________
#____________________________________________________________
#
def main(argv=None):
    """to install and/or test from the command line use::

        python cma.py [options | func dim sig0 [optkey optval][optkey optval]...]

    --test (or -t) to run the doctest, ``--test -v`` to get (much) verbosity
    and ``--test -q`` to run it quietly with output only in case of errors.

    install to install cma.py (uses setup from distutils.core).

    --fcts and --doc for more infos or start ipython --pylab.

    Examples
    --------
    First, testing with the local python distribution::

        python cma.py --test

    If succeeded install (uses setup from distutils.core)::

        python cma.py install

    A single run on the ellipsoid function::

        python cma.py elli 10 1

    """
    if argv is None:
        argv = sys.argv  # should have better been sys.argv[1:]

    # uncomment for unit test
    # _test()
    # handle input arguments, getopt might be helpful ;-)
    if len(argv) >= 1:  # function and help
        if len(argv) == 1 or argv[1].startswith('-h') or argv[1].startswith('--help'):
            print(main.__doc__)
            fun = None
        elif argv[1].startswith('-t') or argv[1].startswith('--test'):
            import doctest
            if len(argv) > 2 and (argv[2].startswith('--v') or argv[2].startswith('-v')):  # verbose
                print('doctest for cma.py: due to different platforms and python versions')
                print('and in some cases due to a missing unique random seed')
                print('many examples will "fail". This is OK, if they give a similar')
                print('to the expected result and if no exception occurs. ')
                # if argv[1][2] == 'v':
                doctest.testmod(report=True)  # this is quite cool!
            else:  # was: if len(argv) > 2 and (argv[2].startswith('--qu') or argv[2].startswith('-q')):
                print('doctest for cma.py: launching (it might be necessary to close a few pop up windows to finish)')
                fn = '__cma_doctest__.txt'
                stdout = sys.stdout
                try:
                    with open(fn, 'w') as f:
                        sys.stdout = f
                        doctest.testmod(report=True)  # this is quite cool!
                finally:
                    sys.stdout = stdout
                process_test(fn)
                print('doctest for cma.py: finished (no other output should be seen after launching)')
            return
        elif argv[1] == '--doc':
            print(__doc__)
            print(CMAEvolutionStrategy.__doc__)
            print(fmin.__doc__)
            fun = None
        elif argv[1] == '--fcts':
            print('List of valid function names:')
            print([d for d in dir(fcts) if not d.startswith('_')])
            fun = None
        elif argv[1] in ('install', '--install'):
            from distutils.core import setup
            setup(name = "cma",
                  version = __version__,
                  author = "Nikolaus Hansen",
                  #    packages = ["cma"],
                  py_modules = ["cma"],
                  )
            fun = None
        elif argv[1] in ('plot',):
            plot()
            raw_input('press return')
            fun = None
        elif len(argv) > 3:
            fun = eval('fcts.' + argv[1])
        else:
            print('try -h option')
            fun = None

    if fun is not None:

        if len(argv) > 2:  # dimension
            x0 = np.ones(eval(argv[2]))
        if len(argv) > 3:  # sigma
            sig0 = eval(argv[3])

        opts = {}
        for i in xrange(5, len(argv), 2):
            opts[argv[i-1]] = eval(argv[i])

        # run fmin
        if fun is not None:
            tic = time.time()
            fmin(fun, x0, sig0, **opts)  # ftarget=1e-9, tolfacupx=1e9, verb_log=10)
            # plot()
            # print ' best function value ', res[2]['es'].best[1]
            print('elapsed time [s]: + %.2f', round(time.time() - tic, 2))

    elif not len(argv):
        fmin(fcts.elli, np.ones(6)*0.1, 0.1, ftarget=1e-9)


#____________________________________________________________
#____________________________________________________________
#
# mainly for testing purpose
# executed when called from an OS shell
if __name__ == "__main__":
    # for i in range(1000):  # how to find the memory leak
    #     main(["cma.py", "rastrigin", "10", "5", "popsize", "200", "maxfevals", "24999", "verb_log", "0"])
    main()


########NEW FILE########
__FILENAME__ = CMAChooser
from cma import CMAEvolutionStrategy
from spearmint import util
import Locker

def init(expt_dir, arg_string):
    args = util.unpack_args(arg_string)
    return CMAChooser(expt_dir, **args)

"""
Chooser module for the CMA-ES evolutionary optimizer.
"""
class CMAChooser:

    def __init__(self, expt_dir):

        raise NotImplementedError('The CMA chooser is not yet implemented!')
        
        self.state_pkl = os.path.join(expt_dir, self.__module__ + ".pkl")

        #TODO: params needs to be an array of starting values
        # - need to figure out how to map Spearmint params into
        # all floats usable by the evolution strategy.
        self.optimizer = CMAEvolutionStrategy(params)

    def _real_init(self, dims, values):

        raise NotImplementedError('The CMA chooser is not yet implemented!')
        self.locker.lock_wait(self.state_pkl)

        if os.path.exists(self.state_pkl):
            fh    = open(self.state_pkl, 'r')
            state = cPickle.load(fh)
            fh.close()

            #TODO: setup config and state values from state, or setup fresh
            #defaults

    def __del__(self):

        raise NotImplementedError('The CMA chooser is not yet implemented!')
        self.locker.lock_wait(self.state_pkl)

        # Write the hyperparameters out to a Pickle.
        fh = tempfile.NamedTemporaryFile(mode='w', delete=False)

        # do this to save the optimizer state
#    >>> pickle.dump(es, open('saved-cma-object.pkl', 'wb'))

        # and this to load it back...
#    >>> es = pickle.load(open('saved-cma-object.pkl', 'rb'))

        cPickle.dump({ 'dims'   : self.D,
                       'ls'     : self.ls,
                       'amp2'   : self.amp2,
                       'noise'  : self.noise,
                       'mean'   : self.mean },
                     fh)
        fh.close()

        # Use an atomic move for better NFS happiness.
        cmd = 'mv "%s" "%s"' % (fh.name, self.state_pkl)
        os.system(cmd) # TODO: Should check system-dependent return status.

        self.locker.unlock(self.state_pkl)

    def next(self, grid, values, durations, candidates, pending, complete):

        raise NotImplementedError('The CMA chooser is not yet implemented!')

        # Perform the real initialization.
        if self.D == -1:
            self._real_init(grid.shape[1], values[complete])

        # Grab out the relevant sets.
        comp = grid[complete,:]
        cand = grid[candidates,:]
        pend = grid[pending,:]
        vals = values[complete]

        # TODO: tell the optimizer about any new f-values, get the next proposed
        # sample, or maybe generate a population of samples and iterate through
        # them?

#    ...         X = es.ask()    # get list of new solutions
#    ...         fit = [cma.fcts.rastrigin(x) for x in X]  # evaluate each solution
#    ...         es.tell(X, fit) # besides for termination only the ranking in fit is used

########NEW FILE########
__FILENAME__ = GPConstrainedEIChooser
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
from spearmint import gp
import sys
from spearmint import util
import tempfile
import numpy          as np
import math
import numpy.random   as npr
import scipy.linalg   as spla
import scipy.stats    as sps
import scipy.optimize as spo
import cPickle
import matplotlib.pyplot as plt
import multiprocessing
import copy

from helpers import *
from Locker  import *

# Wrapper function to pass to parallel ei optimization calls
def optimize_pt(c, b, comp, pend, vals, labels, model):
    ret = spo.fmin_l_bfgs_b(model.grad_optimize_ei_over_hypers,
                            c.flatten(), args=(comp, pend, vals, labels),
                            bounds=b, disp=0)
    return ret[0]

def init(expt_dir, arg_string):
    args = util.unpack_args(arg_string)
    return GPConstrainedEIChooser(expt_dir, **args)

"""
Chooser module for Constrained Gaussian process expected improvement.
Candidates are sampled densely in the unit hypercube and then a subset
of the most promising points are optimized to maximize constrained EI
over hyperparameter samples.  Slice sampling is used to sample
Gaussian process hyperparameters for two GPs, one over the objective
function and the other a probit likelihood classification GP that estimates the
probability that a point is outside of the constraint space.
"""
class GPConstrainedEIChooser:

    def __init__(self, expt_dir, covar="Matern52", mcmc_iters=20,
                 pending_samples=100, noiseless=False, burnin=100,
                 grid_subset=20, constraint_violating_value=np.inf,
                 verbosity=0, visualize2D=False):
        self.cov_func        = getattr(gp, covar)
        self.locker          = Locker()
        self.state_pkl       = os.path.join(expt_dir, self.__module__ + ".pkl")

        self.stats_file      = os.path.join(expt_dir,
                                   self.__module__ + "_hyperparameters.txt")
        self.mcmc_iters      = int(mcmc_iters)
        self.burnin          = int(burnin)
        self.needs_burnin    = True
        self.pending_samples = pending_samples
        self.D               = -1
        self.hyper_iters     = 1
        # Number of points to optimize EI over
        self.grid_subset     = int(grid_subset)
        self.noiseless       = bool(int(noiseless))
        self.hyper_samples   = []
        self.constraint_hyper_samples = []
        self.ff              = None
        self.ff_samples      = []
        self.verbosity       = int(verbosity)

        self.noise_scale = 0.1  # horseshoe prior
        self.amp2_scale  = 1    # zero-mean log normal prior
        self.max_ls      = 2    # top-hat prior on length scales

        self.constraint_noise_scale = 0.1  # horseshoe prior
        self.constraint_amp2_scale  = 1    # zero-mean log normal prio
        self.constraint_gain        = 1   # top-hat prior on length scales
        self.constraint_max_ls      = 2   # top-hat prior on length scales
        self.bad_value = float(constraint_violating_value)
        self.visualize2D            = visualize2D

    # A simple function to dump out hyperparameters to allow for a hot start
    # if the optimization is restarted.
    def dump_hypers(self):
        self.locker.lock_wait(self.state_pkl)

        # Write the hyperparameters out to a Pickle.
        fh = tempfile.NamedTemporaryFile(mode='w', delete=False)
        cPickle.dump({ 'dims'        : self.D,
                       'ls'          : self.ls,
                       'amp2'        : self.amp2,
                       'noise'       : self.noise,
                       'mean'        : self.mean,
                       'constraint_ls'     : self.constraint_ls,
                       'constraint_amp2'   : self.constraint_amp2,
                       'constraint_noise'  : self.constraint_noise,
                       'constraint_mean'   : self.constraint_mean },
                     fh)
        fh.close()

        # Use an atomic move for better NFS happiness.
        cmd = 'mv "%s" "%s"' % (fh.name, self.state_pkl)
        os.system(cmd) # TODO: Should check system-dependent return status.

        self.locker.unlock(self.state_pkl)

        # Write the hyperparameters out to a human readable file as well
        fh    = open(self.stats_file, 'w')
        fh.write('Mean Noise Amplitude <length scales>\n')
        fh.write('-----------ALL SAMPLES-------------\n')
        meanhyps = 0*np.hstack(self.hyper_samples[0])
        for i in self.hyper_samples:
            hyps = np.hstack(i)
            meanhyps += (1/float(len(self.hyper_samples)))*hyps
            for j in hyps:
                fh.write(str(j) + ' ')
            fh.write('\n')

        fh.write('-----------MEAN OF SAMPLES-------------\n')
        for j in meanhyps:
            fh.write(str(j) + ' ')
        fh.write('\n')
        fh.close()

    def _real_init(self, dims, values, durations):

        self.locker.lock_wait(self.state_pkl)

        self.randomstate = npr.get_state()
        if os.path.exists(self.state_pkl):
            fh    = open(self.state_pkl, 'r')
            state = cPickle.load(fh)
            fh.close()

            self.D                = state['dims']
            self.ls               = state['ls']
            self.amp2             = state['amp2']
            self.noise            = state['noise']
            self.mean             = state['mean']
            self.constraint_ls    = state['constraint_ls']
            self.constraint_amp2  = state['constraint_amp2']
            self.constraint_noise = state['constraint_noise']
            self.constraint_mean  = state['constraint_mean']
            self.constraint_gain  = state['constraint_gain']
            self.needs_burnin     = False
        else:

            # Identify constraint violations
            # Note that we'll treat NaNs and Infs as these values as well
            # as an optional user defined value
            goodvals = np.nonzero(np.logical_and(values != self.bad_value,
                                                 np.isfinite(values)))[0]

            # Input dimensionality.
            self.D = dims

            # Initial length scales.
            self.ls = np.ones(self.D)
            self.constraint_ls = np.ones(self.D)

            # Initial amplitude.
            self.amp2 = np.std(values[goodvals])+1e-4
            self.constraint_amp2 = 1.0

            # Initial observation noise.
            self.noise = 1e-3
            self.constraint_noise = 1e-3
            self.constraint_gain = 1

            # Initial mean.
            self.mean = np.mean(values[goodvals])
            self.constraint_mean = 0.5

        self.locker.unlock(self.state_pkl)

    def cov(self, amp2, ls, x1, x2=None):
        if x2 is None:
            return amp2 * (self.cov_func(ls, x1, None)
                           + 1e-6*np.eye(x1.shape[0]))
        else:
            return amp2 * self.cov_func(ls, x1, x2)

    # Given a set of completed 'experiments' in the unit hypercube with
    # corresponding objective 'values', pick from the next experiment to
    # run according to the acquisition function.
    def next(self, grid, values, durations,
             candidates, pending, complete):

        # Don't bother using fancy GP stuff at first.
        if complete.shape[0] < 2:
            return int(candidates[0])

        # Grab out the relevant sets.
        comp = grid[complete,:]
        cand = grid[candidates,:]
        pend = grid[pending,:]
        vals = values[complete]

        # Identify constraint violations
        # Note that we'll treat NaNs and Infs as these values as well
        # as an optional user defined value
        idx = np.logical_and(vals != self.bad_value,
                             np.isfinite(vals))
        goodvals = np.nonzero(idx)[0]
        badvals = np.nonzero(np.logical_not(idx))[0]

        print 'Found %d constraint violating jobs' % (badvals.shape[0])

        # There's no point regressing on one observation
        print 'Received %d valid results' % (goodvals.shape[0])
        if goodvals.shape[0] < 2:
            return int(candidates[0])

        labels = np.zeros(vals.shape[0])
        labels[goodvals] = 1

        if np.sum(labels) < 2:
            return int(candidates[0])

        # Perform the real initialization.
        if self.D == -1:
            self._real_init(grid.shape[1], values[complete],
                            durations[complete])

        # Spray a set of candidates around the min so far
        numcand = cand.shape[0]
        best_comp = np.argmin(vals)
        cand2 = np.vstack((np.random.randn(10,comp.shape[1])*0.001 +
                           comp[best_comp,:], cand))

        if self.mcmc_iters > 0:

            # Possibly burn in.
            if self.needs_burnin:
                for mcmc_iter in xrange(self.burnin):
                    self.sample_constraint_hypers(comp, labels)
                    self.sample_hypers(comp[goodvals,:], vals[goodvals])
                    log("BURN %d/%d] mean: %.2f  amp: %.2f "
                                     "noise: %.4f  min_ls: %.4f  max_ls: %.4f"
                                     % (mcmc_iter+1, self.burnin, self.mean,
                                        np.sqrt(self.amp2), self.noise,
                                        np.min(self.ls), np.max(self.ls)))
                self.needs_burnin = False

            # Sample from hyperparameters.
            # Adjust the candidates to hit ei/sec peaks
            self.hyper_samples = []
            for mcmc_iter in xrange(self.mcmc_iters):
                self.sample_constraint_hypers(comp, labels)
                self.sample_hypers(comp[goodvals,:], vals[goodvals])
                if self.verbosity > 0:
                    log("%d/%d] mean: %.2f  amp: %.2f noise: %.4f "
                                     "min_ls: %.4f  max_ls: %.4f"
                                     % (mcmc_iter+1, self.mcmc_iters, self.mean,
                                        np.sqrt(self.amp2), self.noise,
                                        np.min(self.ls), np.max(self.ls)))

                    log("%d/%d] constraint_mean: %.2f "
                                     "constraint_amp: %.2f "
                                     "constraint_gain: %.4f "
                                     "constraint_min_ls: %.4f "
                                     "constraint_max_ls: "
                                     "%.4f"
                                     % (mcmc_iter+1, self.mcmc_iters,
                                        self.constraint_mean,
                                        np.sqrt(self.constraint_amp2),
                                        self.constraint_gain,
                                        np.min(self.constraint_ls),
                                        np.max(self.constraint_ls)))
            self.dump_hypers()
            comp_preds = np.zeros(labels.shape[0]).flatten()

            preds = self.pred_constraint_voilation(cand, comp, labels).flatten()
            for ii in xrange(self.mcmc_iters):
                constraint_hyper = self.constraint_hyper_samples[ii]
                self.ff = self.ff_samples[ii]
                self.constraint_mean = constraint_hyper[0]
                self.constraint_gain = constraint_hyper[1]
                self.constraint_amp2 = constraint_hyper[2]
                self.constraint_ls = constraint_hyper[3]
                comp_preds += self.pred_constraint_voilation(comp, comp,
                                                             labels).flatten()
            comp_preds = comp_preds / float(self.mcmc_iters)
            print 'Predicting %.2f%% constraint violations (%d/%d): ' % (
            np.mean(preds < 0.5)*100, np.sum(preds < 0.5), preds.shape[0])
            if self.verbosity > 0:
                print 'Prediction` %f%% train accuracy (%d/%d): ' % (
                    np.mean((comp_preds > 0.5) == labels),
                    np.sum((comp_preds > 0.5) == labels), comp_preds.shape[0])

            if self.visualize2D:
                delta = 0.025
                x = np.arange(0, 1.0, delta)
                y = np.arange(0, 1.0, delta)
                X, Y = np.meshgrid(x, y)

                cpreds = np.zeros((X.shape[0], X.shape[1]))
                predei = np.zeros((X.shape[0], X.shape[1]))
                predei2 = np.zeros((X.shape[0], X.shape[1]))
                for ii in xrange(self.mcmc_iters):
                    constraint_hyper = self.constraint_hyper_samples[ii]
                    self.ff = self.ff_samples[ii]
                    self.constraint_mean = constraint_hyper[0]
                    self.constraint_gain = constraint_hyper[1]
                    self.constraint_amp2 = constraint_hyper[2]
                    self.constraint_ls = constraint_hyper[3]

                    cpred = self.pred_constraint_voilation(
                        np.hstack((X.flatten()[:,np.newaxis],
                                   Y.flatten()[:,np.newaxis])), comp, labels)
                    pei = self.compute_constrained_ei(
                        comp, pend, np.hstack(
                            (X.flatten()[:,np.newaxis],
                             Y.flatten()[:,np.newaxis])), vals, labels)
                    pei2 = self.compute_ei(
                        comp, pend, np.hstack(
                            (X.flatten()[:,np.newaxis],
                             Y.flatten()[:,np.newaxis])), vals, labels)

                    cpreds += np.reshape(cpred, (X.shape[0], X.shape[1]))
                    predei += np.reshape(pei, (X.shape[0], X.shape[1]))
                    predei2 += np.reshape(pei2, (X.shape[0], X.shape[1]))

                plt.figure(1)
                plt.clf()
                cpreds = cpreds/float(self.mcmc_iters)
                CS = plt.contour(X,Y,cpreds)
                plt.clabel(CS, inline=1, fontsize=10)
                plt.plot(comp[labels == 0,0], comp[labels == 0,1], 'rx')
                plt.plot(comp[labels == 1,0], comp[labels == 1,1], 'bx')
                plt.title(
                    'Contours of Classification GP (Prob of not being a '
                    'constraint violation)')
                plt.legend(('Constraint Violations', 'Good points'),
                           'lower left')
                plt.savefig('constrained_ei_chooser_class_contour.pdf')

                plt.figure(2)
                plt.clf()
                predei = predei/float(self.mcmc_iters)
                CS = plt.contour(X,Y,predei)
                plt.clabel(CS, inline=1, fontsize=10)
                plt.plot(comp[labels == 0,0], comp[labels == 0,1], 'rx')
                plt.plot(comp[labels == 1,0], comp[labels == 1,1], 'bx')
                plt.title('Contours of EI*P(not violating constraint)')
                plt.legend(('Constraint Violations', 'Good points'),
                           'lower left')
                plt.savefig('constrained_ei_chooser_eitimesprob_contour.pdf')

                plt.figure(3)
                plt.clf()
                predei2 = predei2/float(self.mcmc_iters)
                CS = plt.contour(X,Y,predei2)
                plt.clabel(CS, inline=1, fontsize=10)
                plt.plot(comp[labels == 0,0], comp[labels == 0,1], 'rx')
                plt.plot(comp[labels == 1,0], comp[labels == 1,1], 'bx')
                plt.title('Contours of EI')
                plt.legend(('Constraint Violations', 'Good points'),
                           'lower left')
                plt.savefig('constrained_ei_chooser_ei_contour.pdf')
                #plt.show()

            # Pick the top candidates to optimize over
            overall_ei = self.ei_over_hypers(comp,pend,cand2,vals,labels)
            inds = np.argsort(np.mean(overall_ei, axis=1))[-self.grid_subset:]
            cand2 = cand2[inds,:]

            # Adjust the candidates to hit ei peaks
            b = []# optimization bounds
            for i in xrange(0, cand.shape[1]):
                b.append((0, 1))

            # Optimize each point in parallel
            pool = multiprocessing.Pool(self.grid_subset)
            results = [pool.apply_async(optimize_pt,args=(
                        c,b,comp,pend,vals,labels, copy.copy(self))) for c in cand2]
            for res in results:
                cand = np.vstack((cand, res.get(1024)))
            pool.close()

            #for i in xrange(0, cand2.shape[0]):
            #    log("Optimizing candidate %d/%d\n" %
            #                     (i+1, cand2.shape[0]))
            #    self.check_grad_ei(cand2[i,:], comp, pend, vals, labels)
            #    ret = spo.fmin_l_bfgs_b(self.grad_optimize_ei_over_hypers,
            #                            cand2[i,:].flatten(),
            #                            args=(comp,pend,vals,labels,True),
            #                            bounds=b, disp=0)
            #    cand2[i,:] = ret[0]

            cand = np.vstack((cand, cand2))

            overall_ei = self.ei_over_hypers(comp,pend,cand,vals,labels)
            best_cand = np.argmax(np.mean(overall_ei, axis=1))

            self.dump_hypers()
            if (best_cand >= numcand):
                return (int(numcand), cand[best_cand,:])

            return int(candidates[best_cand])

        else:
            print ('This Chooser module permits only slice sampling with > 0 '
                   'samples.')
            raise Exception('mcmc_iters <= 0')

    # Predict constraint voilating points
    def pred_constraint_voilation(self, cand, comp, vals):
        # The primary covariances for prediction.
        comp_cov   = self.cov(self.constraint_amp2, self.constraint_ls, comp)
        cand_cross = self.cov(self.constraint_amp2, self.constraint_ls, comp,
                              cand)

        # Compute the required Cholesky.
        obsv_cov  = comp_cov + self.constraint_noise*np.eye(comp.shape[0])
        obsv_chol = spla.cholesky(obsv_cov, lower=True)

        cov_grad_func = getattr(gp, 'grad_' + self.cov_func.__name__)
        cand_cross_grad = cov_grad_func(self.constraint_ls, comp, cand)

        # Predictive things.
        # Solve the linear systems.
        alpha  = spla.cho_solve((obsv_chol, True), self.ff)
        beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)

        # Predict the marginal means and variances at candidates.
        func_m = np.dot(cand_cross.T, alpha)# + self.constraint_mean
        func_m = sps.norm.cdf(func_m*self.constraint_gain)

        return func_m

    # Compute EI over hyperparameter samples
    def ei_over_hypers(self,comp,pend,cand,vals,labels):
        overall_ei = np.zeros((cand.shape[0], self.mcmc_iters))
        for mcmc_iter in xrange(self.mcmc_iters):
            hyper = self.hyper_samples[mcmc_iter]
            constraint_hyper = self.constraint_hyper_samples[mcmc_iter]
            self.mean = hyper[0]
            self.noise = hyper[1]
            self.amp2 = hyper[2]
            self.ls = hyper[3]

            self.constraint_mean = constraint_hyper[0]
            self.constraint_gain = constraint_hyper[1]
            self.constraint_amp2 = constraint_hyper[2]
            self.constraint_ls = constraint_hyper[3]
            overall_ei[:,mcmc_iter] = self.compute_constrained_ei(comp, pend,
                                                                  cand, vals,
                                                                  labels)

        return overall_ei

    # Adjust points by optimizing EI over a set of hyperparameter samples
    def grad_optimize_ei_over_hypers(self, cand, comp, pend, vals, labels,
                                     compute_grad=True):
        summed_ei = 0
        summed_grad_ei = np.zeros(cand.shape).flatten()

        for mcmc_iter in xrange(self.mcmc_iters):
            hyper = self.hyper_samples[mcmc_iter]
            constraint_hyper = self.constraint_hyper_samples[mcmc_iter]
            self.mean = hyper[0]
            self.noise = hyper[1]
            self.amp2 = hyper[2]
            self.ls = hyper[3]

            self.constraint_mean = constraint_hyper[0]
            self.constraint_gain = constraint_hyper[1]
            self.constraint_amp2 = constraint_hyper[2]
            self.constraint_ls = constraint_hyper[3]
            if compute_grad:
                (ei,g_ei) = self.grad_optimize_ei(cand, comp, pend, vals, labels,
                                                  compute_grad)
                summed_grad_ei = summed_grad_ei + g_ei
            else:
                ei = self.grad_optimize_ei(cand, comp, pend, vals,
                                           labels, compute_grad)

            summed_ei += ei

        if compute_grad:
            return (summed_ei, summed_grad_ei)
        else:
            return summed_ei

    def check_grad_ei(self, cand, comp, pend, vals, labels):
        (ei,dx1) = self.grad_optimize_ei_over_hypers(cand, comp, pend, vals, labels)
        dx2 = dx1*0
        idx = np.zeros(cand.shape[0])
        for i in xrange(0, cand.shape[0]):
            idx[i] = 1e-6
            (ei1,tmp) = self.grad_optimize_ei_over_hypers(
                cand + idx, comp, pend, vals, labels)
            (ei2,tmp) = self.grad_optimize_ei_over_hypers(
                cand - idx, comp, pend, vals, labels)
            dx2[i] = (ei - ei2)/(2*1e-6)
            idx[i] = 0
        print 'computed grads', dx1
        print 'finite diffs', dx2
        print (dx1/dx2)
        print np.sum((dx1 - dx2)**2)
        time.sleep(2)

    def grad_optimize_ei(self, cand, comp, pend, vals, labels, compute_grad=True):
        if pend.shape[0] == 0:
            return self.grad_optimize_ei_nopend(cand, comp, vals, labels,
                                                compute_grad=True)
        else:
            return self.grad_optimize_ei_pend(cand, comp, pend, vals, labels,
                                              compute_grad=True)

    def grad_optimize_ei_pend(self, cand, comp, pend, vals, labels, compute_grad=True):
        # Here we have to compute the gradients for constrained ei
        # This means deriving through the two kernels, the one for predicting
        # constraint violations and the one predicting ei

        # First pull out violating points
        compfull = comp.copy()
        comp = comp[labels > 0, :]
        vals = vals[labels > 0]

        # Use standard EI if there aren't enough observations of either
        # positive or negative constraint violations
        use_vanilla_ei = (np.all(labels > 0) or np.all(labels <= 0))

        best = np.min(vals)
        cand = np.reshape(cand, (-1, comp.shape[1]))
        func_constraint_m = 1

        if (not use_vanilla_ei):

            # First we make predictions for the durations
            # Compute covariances
            comp_constraint_cov   = self.cov(self.constraint_amp2,
                                             self.constraint_ls,
                                             compfull)
            cand_constraint_cross = self.cov(self.constraint_amp2,
                                             self.constraint_ls,
                                             compfull,cand)

            # Cholesky decompositions
            obsv_constraint_cov  = (comp_constraint_cov +
                 self.constraint_noise*np.eye(compfull.shape[0]))
            obsv_constraint_chol = spla.cholesky(obsv_constraint_cov,lower=True)

            # Linear systems
            t_alpha  = spla.cho_solve((obsv_constraint_chol, True), self.ff)

            # Predict marginal mean times and (possibly) variances
            ff = np.dot(cand_constraint_cross.T, t_alpha)

            # Squash through Gaussian cdf
            func_constraint_m = sps.norm.cdf(self.constraint_gain*ff)

            # Apply covariance function
            cov_grad_func = getattr(gp, 'grad_' + self.cov_func.__name__)
            cand_cross_grad = cov_grad_func(self.constraint_ls, compfull, cand)
            grad_cross_t = np.squeeze(cand_cross_grad)

        # Now compute the gradients w.r.t. ei
        # The primary covariances for prediction.
        comp_cov   = self.cov(self.amp2, self.ls, comp)
        cand_cross = self.cov(self.amp2, self.ls, comp, cand)
        comp_cov_full   = self.cov(self.amp2, self.ls, compfull)
        cand_cross_full = self.cov(self.amp2, self.ls, compfull, cand)

        # Create a composite vector of complete and pending.
        comp_pend = np.concatenate((comp, pend))

        # Compute the covariance and Cholesky decomposition.
        comp_pend_cov  = (self.cov(self.amp2, self.ls, comp_pend) +
                          self.noise*np.eye(comp_pend.shape[0]))
        comp_pend_chol = spla.cholesky(comp_pend_cov, lower=True)

        # Compute submatrices.
        pend_cross = self.cov(self.amp2, self.ls, comp, pend)
        pend_kappa = self.cov(self.amp2,self.ls, pend)

        # Use the sub-Cholesky.
        obsv_chol = comp_pend_chol[:comp.shape[0],:comp.shape[0]]

        # Compute the required Cholesky.
        #obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
        #obsv_chol = spla.cholesky(obsv_cov, lower=True)
        obsv_cov_full  = comp_cov_full + self.noise*np.eye(compfull.shape[0])
        obsv_chol_full = spla.cholesky( obsv_cov_full, lower=True)

        # Predictive things.
        # Solve the linear systems.
        alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
        beta   = spla.cho_solve((obsv_chol, True), pend_cross)

        # Finding predictive means and variances.
        pend_m = np.dot(pend_cross.T, alpha) + self.mean
        pend_K = pend_kappa - np.dot(pend_cross.T, beta)

        # Take the Cholesky of the predictive covariance.
        pend_chol = spla.cholesky(pend_K, lower=True)

        # Make predictions.
        npr.set_state(self.randomstate)
        pend_fant = np.dot(pend_chol, npr.randn(pend.shape[0],self.pending_samples)) + pend_m[:,None]

        # Include the fantasies.
        fant_vals = np.concatenate(
            (np.tile(vals[:,np.newaxis],
                     (1,self.pending_samples)), pend_fant))

        # Compute bests over the fantasies.
        bests = np.min(fant_vals, axis=0)

        # Now generalize from these fantasies.
        cand_cross = self.cov(self.amp2, self.ls, comp_pend, cand)
        cov_grad_func = getattr(gp, 'grad_' + self.cov_func.__name__)
        cand_cross_grad = cov_grad_func(self.ls, comp_pend, cand)

        # Solve the linear systems.
        alpha  = spla.cho_solve((comp_pend_chol, True),
                                fant_vals - self.mean)
        beta   = spla.solve_triangular(comp_pend_chol, cand_cross,
                                       lower=True)

        # Predict the marginal means and variances at candidates.
        func_m = np.dot(cand_cross.T, alpha) + self.mean
        func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

        #beta  = spla.solve_triangular(obsv_chol_full, cand_cross_full,
        #                               lower=True)
        #beta   = spla.solve_triangular(obsv_chol, cand_cross,
        #                               lower=True)

        # Predict the marginal means and variances at candidates.
        func_m = np.dot(cand_cross.T, alpha) + self.mean
        func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

        # Expected improvement
        func_s = np.sqrt(func_v)
        u      = (best - func_m) / func_s
        ncdf   = sps.norm.cdf(u)
        npdf   = sps.norm.pdf(u)
        ei     = func_s*(u*ncdf + npdf)

        constrained_ei = -np.sum(ei*func_constraint_m)
        if not compute_grad:
            return constrained_ei

        # Gradients of ei w.r.t. mean and variance
        g_ei_m = -ncdf
        g_ei_s2 = 0.5*npdf / func_s

        # Apply covariance function
        grad_cross = np.squeeze(cand_cross_grad)

        grad_xp_m = np.dot(alpha.transpose(),grad_cross)
        grad_xp_v = np.dot(-2*spla.cho_solve(
                (comp_pend_chol, True),cand_cross).transpose(), grad_cross)

        grad_xp = 0.5*self.amp2*(grad_xp_m*np.tile(g_ei_m,(comp.shape[1],1)).T + (grad_xp_v.T*g_ei_s2).T)

        grad_xp = np.sum(grad_xp,axis=0)

        if use_vanilla_ei:
            return -np.sum(ei), grad_xp.flatten()

        grad_constraint_xp_m = np.dot(t_alpha.transpose(),grad_cross_t)
        grad_constraint_xp_m = (0.5*self.constraint_amp2*
                                self.constraint_gain*
                                grad_constraint_xp_m*
                                sps.norm.pdf(self.constraint_gain*ff))

        grad_xp = (func_constraint_m*grad_xp + np.sum(ei)*grad_constraint_xp_m)

        return constrained_ei, grad_xp.flatten()

    def grad_optimize_ei_nopend(self, cand, comp, vals, labels, compute_grad=True):
        # Here we have to compute the gradients for constrained ei
        # This means deriving through the two kernels, the one for predicting
        # constraint violations and the one predicting ei

        # First pull out violating points
        compfull = comp.copy()
        comp = comp[labels > 0, :]
        vals = vals[labels > 0]

        # Use standard EI if there aren't enough observations of either
        # positive or negative constraint violations
        use_vanilla_ei = (np.all(labels > 0) or np.all(labels <= 0))

        best = np.min(vals)
        cand = np.reshape(cand, (-1, comp.shape[1]))
        func_constraint_m = 1

        if (not use_vanilla_ei):

            # First we make predictions for the durations
            # Compute covariances
            comp_constraint_cov   = self.cov(self.constraint_amp2,
                                             self.constraint_ls,
                                             compfull)
            cand_constraint_cross = self.cov(self.constraint_amp2,
                                             self.constraint_ls,
                                             compfull,cand)

            # Cholesky decompositions
            obsv_constraint_cov  = (comp_constraint_cov +
                 self.constraint_noise*np.eye(compfull.shape[0]))
            obsv_constraint_chol = spla.cholesky(obsv_constraint_cov,lower=True)

            # Linear systems
            t_alpha  = spla.cho_solve((obsv_constraint_chol, True), self.ff)

            # Predict marginal mean times and (possibly) variances
            ff = np.dot(cand_constraint_cross.T, t_alpha)

            # Squash through Gaussian cdf
            func_constraint_m = sps.norm.cdf(self.constraint_gain*ff)

        # Now compute the gradients w.r.t. ei
        # The primary covariances for prediction.
        comp_cov   = self.cov(self.amp2, self.ls, comp)
        cand_cross = self.cov(self.amp2, self.ls, comp, cand)
        comp_cov_full   = self.cov(self.amp2, self.ls, compfull)
        cand_cross_full = self.cov(self.amp2, self.ls, compfull, cand)

        # Compute the required Cholesky.
        obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
        obsv_chol = spla.cholesky(obsv_cov, lower=True)
        obsv_cov_full  = comp_cov_full + self.noise*np.eye(compfull.shape[0])
        obsv_chol_full = spla.cholesky( obsv_cov_full, lower=True)

        # Predictive things.
        # Solve the linear systems.
        alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
        beta   = spla.solve_triangular(obsv_chol_full, cand_cross_full,
                                       lower=True)

        # Predict the marginal means and variances at candidates.
        func_m = np.dot(cand_cross.T, alpha) + self.mean
        func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

        # Expected improvement
        func_s = np.sqrt(func_v)
        u      = (best - func_m) / func_s
        ncdf   = sps.norm.cdf(u)
        npdf   = sps.norm.pdf(u)
        ei     = func_s*(u*ncdf + npdf)

        constrained_ei = -np.sum(ei*func_constraint_m)
        if not compute_grad:
            return constrained_ei

        # Gradients of ei w.r.t. mean and variance
        g_ei_m = -ncdf
        g_ei_s2 = 0.5*npdf / func_s

        # Apply covariance function
        cov_grad_func = getattr(gp, 'grad_' + self.cov_func.__name__)
        cand_cross_grad = cov_grad_func(self.ls, comp, cand)
        grad_cross = np.squeeze(cand_cross_grad)

        cand_cross_grad_full = cov_grad_func(self.ls, compfull, cand)
        grad_cross_full = np.squeeze(cand_cross_grad_full)

        grad_xp_m = np.dot(alpha.transpose(),grad_cross)
        grad_xp_v = np.dot(-2*spla.cho_solve((obsv_chol_full, True),
                                             cand_cross_full).transpose(),
                            grad_cross_full)

        grad_xp = 0.5*self.amp2*(grad_xp_m*g_ei_m + grad_xp_v*g_ei_s2)

        if use_vanilla_ei:
            return -np.sum(ei), grad_xp.flatten()

        # Apply constraint classifier
        cand_cross_grad = cov_grad_func(self.constraint_ls, compfull, cand)
        grad_cross_t = np.squeeze(cand_cross_grad)

        grad_constraint_xp_m = np.dot(t_alpha.transpose(),grad_cross_t)
        grad_constraint_xp_m = (0.5*self.constraint_amp2*
                                self.constraint_gain*
                                grad_constraint_xp_m*
                                sps.norm.pdf(self.constraint_gain*ff))

        grad_xp = (func_constraint_m*grad_xp + ei*grad_constraint_xp_m)

        return constrained_ei, grad_xp.flatten()


    def compute_constrained_ei(self, comp, pend, cand, vals, labels):
        # First we make predictions for the durations as that
        # doesn't depend on pending experiments
        # First pull out violating points
        compfull = comp.copy()
        comp = comp[labels > 0, :]
        vals = vals[labels > 0]

        # Use standard EI if there aren't enough observations of either
        # positive or negative constraint violations
        if (np.all(labels > 0) or np.all(labels <= 0)):
            func_constraint_m = 1
        else:
            # Compute covariances
            comp_constraint_cov   = self.cov(self.constraint_amp2,
                                             self.constraint_ls,
                                             compfull)
            cand_constraint_cross = self.cov(self.constraint_amp2,
                                             self.constraint_ls,
                                             compfull,cand)

            # Cholesky decompositions
            obsv_constraint_cov  = (comp_constraint_cov +
                self.constraint_noise*np.eye(compfull.shape[0]))
            obsv_constraint_chol = spla.cholesky(
                obsv_constraint_cov, lower=True)

            # Linear systems
            t_alpha  = spla.cho_solve((obsv_constraint_chol, True), self.ff)
            t_beta   = spla.solve_triangular(obsv_constraint_chol,
                                             cand_constraint_cross, lower=True)

            # Predict marginal mean times and (possibly) variances
            func_constraint_m = (np.dot(cand_constraint_cross.T, t_alpha))

        # Squash through a probit
        func_constraint_m = sps.norm.cdf(self.constraint_gain*func_constraint_m)
        if pend.shape[0] == 0:
            # If there are no pending, don't do anything fancy.
            # Current best.
            best = np.min(vals)

            # The primary covariances for prediction.
            comp_cov   = self.cov(self.amp2, self.ls, comp)
            comp_cov_full = self.cov(self.amp2, self.ls, compfull)
            cand_cross = self.cov(self.amp2, self.ls, comp, cand)
            cand_cross_full = self.cov(self.amp2, self.ls, compfull, cand)

            # Compute the required Cholesky.
            obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
            obsv_cov_full  = (comp_cov_full +
                              self.noise*np.eye(compfull.shape[0]))
            obsv_chol = spla.cholesky( obsv_cov, lower=True)
            obsv_chol_full = spla.cholesky( obsv_cov_full, lower=True)

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)
            #beta   = spla.solve_triangular(obsv_chol_full, cand_cross_full,
            #                               lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v)
            u      = (best - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            constrained_ei = ei*func_constraint_m
            return constrained_ei
        else:
            # If there are pending experiments, fantasize their outcomes.

            # Create a composite vector of complete and pending.
            comp_pend = np.concatenate((comp, pend))

            # Compute the covariance and Cholesky decomposition.
            comp_pend_cov  = (self.cov(self.amp2, self.ls, comp_pend) +
                              self.noise*np.eye(comp_pend.shape[0]))
            comp_pend_chol = spla.cholesky(comp_pend_cov, lower=True)

            # Compute submatrices.
            pend_cross = self.cov(self.amp2, self.ls, comp, pend)
            pend_kappa = self.cov(self.amp2, self.ls, pend)

            # Use the sub-Cholesky.
            obsv_chol = comp_pend_chol[:comp.shape[0],:comp.shape[0]]

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.cho_solve((obsv_chol, True), pend_cross)

            # Finding predictive means and variances.
            pend_m = np.dot(pend_cross.T, alpha) + self.mean
            pend_K = pend_kappa - np.dot(pend_cross.T, beta)

            # Take the Cholesky of the predictive covariance.
            pend_chol = spla.cholesky(pend_K, lower=True)

            # Make predictions.
            pend_fant = np.dot(pend_chol, npr.randn(pend.shape[0],
                               self.pending_samples)) + pend_m[:,None]

            # Include the fantasies.
            fant_vals = np.concatenate((np.tile(vals[:,np.newaxis],
                                       (1,self.pending_samples)), pend_fant))

            # Compute bests over the fantasies.
            bests = np.min(fant_vals, axis=0)

            # Now generalize from these fantasies.
            cand_cross = self.cov(self.amp2, self.ls, comp_pend, cand)

            # Solve the linear systems.
            alpha  = spla.cho_solve((comp_pend_chol, True),
                                    fant_vals - self.mean)
            beta   = spla.solve_triangular(comp_pend_chol, cand_cross,
                                           lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v[:,np.newaxis])
            u      = (bests[np.newaxis,:] - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            return np.mean(ei, axis=1)*func_constraint_m

    def compute_ei(self, comp, pend, cand, vals, labels):
        # First we make predictions for the durations as that
        # doesn't depend on pending experiments
        # First pull out violating points
        compfull = comp.copy()
        comp = comp[labels > 0, :]
        vals = vals[labels > 0]

        # Compute covariances
        comp_constraint_cov   = self.cov(self.constraint_amp2,
                                         self.constraint_ls,
                                         compfull)
        cand_constraint_cross = self.cov(self.constraint_amp2,
                                         self.constraint_ls,
                                         compfull,cand)

        # Cholesky decompositions
        obsv_constraint_cov  = (comp_constraint_cov +
                                self.constraint_noise*np.eye(
            compfull.shape[0]))
        obsv_constraint_chol = spla.cholesky( obsv_constraint_cov, lower=True )

        # Linear systems
        t_alpha  = spla.cho_solve((obsv_constraint_chol, True), self.ff)

        # Predict marginal mean times and (possibly) variances
        func_constraint_m = (np.dot(cand_constraint_cross.T, t_alpha))

        # Squash through a probit to get prob of not violating a constraint
        func_constraint_m = 1./(1+np.exp(-self.constraint_gain*
                                          func_constraint_m))

        if pend.shape[0] == 0:
            # If there are no pending, don't do anything fancy.

            # Current best.
            best = np.min(vals)

            # The primary covariances for prediction.
            comp_cov   = self.cov(self.amp2, self.ls, comp)
            comp_cov_full = self.cov(self.amp2, self.ls, compfull)
            cand_cross = self.cov(self.amp2, self.ls, comp, cand)
            cand_cross_full = self.cov(self.amp2, self.ls, compfull, cand)

            # Compute the required Cholesky.
            obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
            obsv_cov_full  = (comp_cov_full +
                              self.noise*np.eye(compfull.shape[0]))
            obsv_chol = spla.cholesky( obsv_cov, lower=True )
            obsv_chol_full = spla.cholesky( obsv_cov_full, lower=True )

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)
            #beta   = spla.solve_triangular(obsv_chol_full, cand_cross_full,
                                #lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v)
            u      = (best - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            return ei
        else:
            return 0

    def sample_constraint_hypers(self, comp, labels):
        # The latent GP projection
        # The latent GP projection
        if (self.ff is None or self.ff.shape[0] < comp.shape[0]):
            self.ff_samples = []
            comp_cov  = self.cov(self.constraint_amp2, self.constraint_ls, comp)
            obsv_cov  = comp_cov + 1e-6*np.eye(comp.shape[0])
            obsv_chol = spla.cholesky(obsv_cov, lower=True)
            self.ff = np.dot(obsv_chol,npr.randn(obsv_chol.shape[0]))

        self._sample_constraint_noisy(comp, labels)
        self._sample_constraint_ls(comp, labels)
        self.constraint_hyper_samples.append((self.constraint_mean,
                                              self.constraint_gain,
                                              self.constraint_amp2,
                                              self.constraint_ls))
        self.ff_samples.append(self.ff)

    def sample_hypers(self, comp, vals):
        if self.noiseless:
            self.noise = 1e-3
            self._sample_noiseless(comp, vals)
        else:
            self._sample_noisy(comp, vals)
        self._sample_ls(comp, vals)

        self.hyper_samples.append((self.mean, self.noise, self.amp2, self.ls))

    def _sample_ls(self, comp, vals):
        def logprob(ls):
            if np.any(ls < 0) or np.any(ls > self.max_ls):
                return -np.inf

            cov   = (self.amp2 * (self.cov_func(ls, comp, None) +
                                  1e-6*np.eye(comp.shape[0])) +
                     self.noise*np.eye(comp.shape[0]))
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - self.mean)
            lp    = (-np.sum(np.log(np.diag(chol))) -
                      0.5*np.dot(vals-self.mean, solve))
            return lp

        self.ls = util.slice_sample(self.ls, logprob, compwise=True)

    def _sample_constraint_ls(self, comp, vals):
        def lpProbit(ff, gain=self.constraint_gain):
            probs = sps.norm.cdf(ff*gain)
            probs[probs <= 0] = 1e-12
            probs[probs >= 1] = 1-1e-12
            llh = np.sum(vals*np.log(probs) +
                         (1-vals)*np.log(1-probs))

            return llh

        def lpSigmoid(ff, gain=self.constraint_gain):
            probs = 1./(1. + np.exp(-gain*ff));
            probs[probs <= 0] = 1e-12
            probs[probs >= 1] = 1-1e-12
            llh   = np.sum(vals*np.log(probs) + (1-vals)*np.log(1-probs));
            return llh

        def updateGain(gain):
            if gain < 0.01 or gain > 10:
                return -np.inf

            cov   = (self.constraint_amp2 * (self.cov_func(
                        self.constraint_ls, comp, None) +
                                             1e-6*np.eye(comp.shape[0])) +
                     self.constraint_noise*np.eye(comp.shape[0]))
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals)
            lp   = lpProbit(self.ff, gain)

            return lp

        def logprob(ls):
            if np.any(ls < 0) or np.any(ls > self.constraint_max_ls):
                return -np.inf

            cov   = self.constraint_amp2 * (self.cov_func(ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + self.constraint_noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), self.ff)
            lp   = lpProbit(self.ff)

            return lp

        hypers = util.slice_sample(self.constraint_ls, logprob, compwise=True)
        self.constraint_ls = hypers

        cov   = self.constraint_amp2 * (self.cov_func(self.constraint_ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + self.constraint_noise*np.eye(comp.shape[0])
        chol  = spla.cholesky(cov, lower=False)
        ff = self.ff
        for jj in xrange(20):
            (ff, lpell) = self.elliptical_slice(ff, chol, lpProbit)

        self.ff = ff

        # Update gain
        hypers = util.slice_sample(np.array([self.constraint_gain]),
                                   updateGain, compwise=True)
        self.constraint_gain = hypers[0]

    def _sample_noisy(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = hypers[2]

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0 or noise < 0:
                return -np.inf

            cov   = amp2 * ((self.cov_func(self.ls, comp, None) +
                            1e-6*np.eye(comp.shape[0])) +
                            noise*np.eye(comp.shape[0]))
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in noise horseshoe prior.
            lp += np.log(np.log(1 + (self.noise_scale/noise)**2))

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(amp2)/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array(
                    [self.mean, self.amp2, self.noise]),
                                   logprob, compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = hypers[2]

    def _sample_constraint_noisy(self, comp, vals):
        def lpProbit(ff, gain=self.constraint_gain):
            probs = sps.norm.cdf(ff*gain)
            probs[probs <= 0] = 1e-12
            probs[probs >= 1] = 1-1e-12
            llh = np.sum(vals*np.log(probs) +
                         (1-vals)*np.log(1-probs))
            if np.any(np.isnan(probs)):
                print probs
            return llh

        def lpSigmoid(ff,gain=self.constraint_gain):
            probs = 1./(1. + np.exp(-gain*ff));
            probs[probs <= 0] = 1e-12
            probs[probs >= 1] = 1-1e-12
            llh   = np.sum(vals*np.log(probs) + (1-vals)*np.log(1-probs));
            return llh

        def logprob(hypers):
            amp2  = hypers[0]
            ff = hypers[1:]

            if amp2 < 0:
                return -np.inf

            noise = self.constraint_noise
            cov   = amp2 * (self.cov_func(self.constraint_ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), ff)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(ff, solve)

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(amp2)/self.constraint_amp2_scale)**2

            lp   += lpProbit(ff,self.constraint_gain)

            return lp

        hypers = util.slice_sample(np.hstack((np.array([self.constraint_amp2]),
                                            self.ff)), logprob, compwise=False)
        self.constraint_amp2  = hypers[0]
        self.ff = hypers[1:]
        cov   = self.constraint_amp2 * ((
                    self.cov_func(self.constraint_ls, comp, None) +
                    1e-6*np.eye(comp.shape[0])) +
                                self.constraint_noise*np.eye(comp.shape[0]))
        chol  = spla.cholesky(cov, lower=False)
        ff = self.ff
        for jj in xrange(50):
            (ff, lpell) = self.elliptical_slice(ff, chol, lpProbit)
        self.ff = ff

    def _sample_noiseless(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = 1e-3

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0:
                return -np.inf

            cov   = amp2 * ((self.cov_func(self.ls, comp, None) +
                             1e-6*np.eye(comp.shape[0])) +
                            noise*np.eye(comp.shape[0]))
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(amp2)/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array(
                 [self.mean, self.amp2, self.noise]), logprob, compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = 1e-3

    def elliptical_slice(self, xx, chol_Sigma, log_like_fn, cur_log_like=None,
                         angle_range=0):
        D = xx.shape[0]

        if cur_log_like is None:
            cur_log_like = log_like_fn(xx)

        nu = np.dot(chol_Sigma.T,np.random.randn(D, 1)).flatten()
        hh = np.log(np.random.rand()) + cur_log_like

        # Set up a bracket of angles and pick a first proposal.
        # "phi = (theta'-theta)" is a change in angle.
        if angle_range <= 0:
            # Bracket whole ellipse with both edges at first proposed point
            phi = np.random.rand()*2*math.pi;
            phi_min = phi - 2*math.pi;
            phi_max = phi;
        else:
            # Randomly center bracket on current point
            phi_min = -angle_range*np.random.rand();
            phi_max = phi_min + angle_range;
            phi = np.random.rand()*(phi_max - phi_min) + phi_min;

        # Slice sampling loop
        while True:
            # Compute xx for proposed angle difference
            # and check if it's on the slice
            xx_prop = xx*np.cos(phi) + nu*np.sin(phi);

            cur_log_like = log_like_fn(xx_prop);
            if cur_log_like > hh:
                # New point is on slice, ** EXIT LOOP **
                break;

            # Shrink slice to rejected point
            if phi > 0:
                phi_max = phi;
            elif phi < 0:
                phi_min = phi;
            else:
                raise Exception('BUG DETECTED: Shrunk to current position '
                                'and still not acceptable.');

            # Propose new angle difference
            phi = np.random.rand()*(phi_max - phi_min) + phi_min;

        xx = xx_prop;
        return (xx, cur_log_like)

########NEW FILE########
__FILENAME__ = GPEIChooser
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
from spearmint import gp
import sys
from spearmint import util
import tempfile
import numpy          as np
import numpy.random   as npr
import scipy.linalg   as spla
import scipy.stats    as sps
import scipy.optimize as spo
import cPickle

from Locker  import *
from helpers import *


def init(expt_dir, arg_string):
    args = util.unpack_args(arg_string)
    return GPEIChooser(expt_dir, **args)

"""
Chooser module for the Gaussian process expected improvement
acquisition function.  Candidates are sampled densely in the unit
hypercube and then the highest EI point is selected.  Slice sampling
is used to sample Gaussian process hyperparameters for the GP.
"""
class GPEIChooser:

    def __init__(self, expt_dir, covar="Matern52", mcmc_iters=10,
                 pending_samples=100, noiseless=False):
        self.cov_func        = getattr(gp, covar)
        self.locker          = Locker()
        self.state_pkl       = os.path.join(expt_dir, self.__module__ + ".pkl")

        self.mcmc_iters      = int(mcmc_iters)
        self.pending_samples = pending_samples
        self.D               = -1
        self.hyper_iters     = 1
        self.noiseless       = bool(int(noiseless))

        self.noise_scale = 0.1  # horseshoe prior
        self.amp2_scale  = 1    # zero-mean log normal prior
        self.max_ls      = 2    # top-hat prior on length scales

    def __del__(self):
        self.locker.lock_wait(self.state_pkl)

        # Write the hyperparameters out to a Pickle.
        fh = tempfile.NamedTemporaryFile(mode='w', delete=False)
        cPickle.dump({ 'dims'   : self.D,
                       'ls'     : self.ls,
                       'amp2'   : self.amp2,
                       'noise'  : self.noise,
                       'mean'   : self.mean },
                     fh)
        fh.close()

        # Use an atomic move for better NFS happiness.
        cmd = 'mv "%s" "%s"' % (fh.name, self.state_pkl)
        os.system(cmd) # TODO: Should check system-dependent return status.

        self.locker.unlock(self.state_pkl)

    def _real_init(self, dims, values):
        self.locker.lock_wait(self.state_pkl)

        if os.path.exists(self.state_pkl):
            fh    = open(self.state_pkl, 'r')
            state = cPickle.load(fh)
            fh.close()

            self.D     = state['dims']
            self.ls    = state['ls']
            self.amp2  = state['amp2']
            self.noise = state['noise']
            self.mean  = state['mean']
        else:

            # Input dimensionality.
            self.D = dims

            # Initial length scales.
            self.ls = np.ones(self.D)

            # Initial amplitude.
            self.amp2 = np.std(values)+1e-4

            # Initial observation noise.
            self.noise = 1e-3

            # Initial mean.
            self.mean = np.mean(values)

        self.locker.unlock(self.state_pkl)

    def cov(self, x1, x2=None):
        if x2 is None:
            return self.amp2 * (self.cov_func(self.ls, x1, None)
                               + 1e-6*np.eye(x1.shape[0]))
        else:
            return self.amp2 * self.cov_func(self.ls, x1, x2)

    def next(self, grid, values, durations, candidates, pending, complete):

        # Don't bother using fancy GP stuff at first.
        if complete.shape[0] < 2:
            return int(candidates[0])

        # Perform the real initialization.
        if self.D == -1:
            self._real_init(grid.shape[1], values[complete])

        # Grab out the relevant sets.
        comp = grid[complete,:]
        cand = grid[candidates,:]
        pend = grid[pending,:]
        vals = values[complete]

        if self.mcmc_iters > 0:
            # Sample from hyperparameters.

            overall_ei = np.zeros((cand.shape[0], self.mcmc_iters))

            for mcmc_iter in xrange(self.mcmc_iters):

                self.sample_hypers(comp, vals)
                log("mean: %f  amp: %f  noise: %f  min_ls: %f  max_ls: %f"
                                 % (self.mean, np.sqrt(self.amp2), self.noise, np.min(self.ls), np.max(self.ls)))

                overall_ei[:,mcmc_iter] = self.compute_ei(comp, pend, cand, vals)

            best_cand = np.argmax(np.mean(overall_ei, axis=1))

            return int(candidates[best_cand])

        else:
            # Optimize hyperparameters
            try:
                self.optimize_hypers(comp, vals)
            except:
                # Initial length scales.
                self.ls = np.ones(self.D)
                # Initial amplitude.
                self.amp2 = np.std(vals)
                # Initial observation noise.
                self.noise = 1e-3
            log("mean: %f  amp: %f  noise: %f  min_ls: %f  max_ls: %f"
                             % (self.mean, np.sqrt(self.amp2), self.noise, np.min(self.ls),
                                np.max(self.ls)))

            ei = self.compute_ei(comp, pend, cand, vals)

            best_cand = np.argmax(ei)

            return int(candidates[best_cand])

    def compute_ei(self, comp, pend, cand, vals):
        if pend.shape[0] == 0:
            # If there are no pending, don't do anything fancy.

            # Current best.
            best = np.min(vals)

            # The primary covariances for prediction.
            comp_cov   = self.cov(comp)
            cand_cross = self.cov(comp, cand)

            # Compute the required Cholesky.
            obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
            obsv_chol = spla.cholesky( obsv_cov, lower=True )

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v)
            u      = (best - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            return ei
        else:
            # If there are pending experiments, fantasize their outcomes.

            # Create a composite vector of complete and pending.
            comp_pend = np.concatenate((comp, pend))

            # Compute the covariance and Cholesky decomposition.
            comp_pend_cov  = self.cov(comp_pend) + self.noise*np.eye(comp_pend.shape[0])
            comp_pend_chol = spla.cholesky(comp_pend_cov, lower=True)

            # Compute submatrices.
            pend_cross = self.cov(comp, pend)
            pend_kappa = self.cov(pend)

            # Use the sub-Cholesky.
            obsv_chol = comp_pend_chol[:comp.shape[0],:comp.shape[0]]

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.cho_solve((obsv_chol, True), pend_cross)

            # Finding predictive means and variances.
            pend_m = np.dot(pend_cross.T, alpha) + self.mean
            pend_K = pend_kappa - np.dot(pend_cross.T, beta)

            # Take the Cholesky of the predictive covariance.
            pend_chol = spla.cholesky(pend_K, lower=True)

            # Make predictions.
            pend_fant = (np.dot(pend_chol, npr.randn(pend.shape[0],self.pending_samples))
                         + pend_m[:,None])

            # Include the fantasies.
            fant_vals = np.concatenate((np.tile(vals[:,np.newaxis],
                                                (1,self.pending_samples)), pend_fant))

            # Compute bests over the fantasies.
            bests = np.min(fant_vals, axis=0)

            # Now generalize from these fantasies.
            cand_cross = self.cov(comp_pend, cand)

            # Solve the linear systems.
            alpha  = spla.cho_solve((comp_pend_chol, True), fant_vals - self.mean)
            beta   = spla.solve_triangular(comp_pend_chol, cand_cross, lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v[:,np.newaxis])
            u      = (bests[np.newaxis,:] - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            return np.mean(ei, axis=1)

    def sample_hypers(self, comp, vals):
        if self.noiseless:
            self.noise = 1e-3
            self._sample_noiseless(comp, vals)
        else:
            self._sample_noisy(comp, vals)
        self._sample_ls(comp, vals)

    def _sample_ls(self, comp, vals):
        def logprob(ls):
            if np.any(ls < 0) or np.any(ls > self.max_ls):
                return -np.inf

            cov   = self.amp2 * (self.cov_func(ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + self.noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - self.mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-self.mean, solve)
            return lp

        self.ls = util.slice_sample(self.ls, logprob, compwise=True)

    def _sample_noisy(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = hypers[2]

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0 or noise < 0:
                return -np.inf

            cov   = amp2 * (self.cov_func(self.ls, comp, None) +
                            1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in noise horseshoe prior.
            lp += np.log(np.log(1 + (self.noise_scale/noise)**2))

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(amp2)/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array([self.mean, self.amp2, self.noise]),
                                   logprob, compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = hypers[2]

    def _sample_noiseless(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = 1e-3

            if amp2 < 0:
                return -np.inf

            cov   = amp2 * (self.cov_func(self.ls, comp, None) +
                            1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(amp2)/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array([self.mean, self.amp2, self.noise]), logprob,
                                   compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = 1e-3

    def optimize_hypers(self, comp, vals):
        mygp = gp.GP(self.cov_func.__name__)
        mygp.real_init(comp.shape[1], vals)
        mygp.optimize_hypers(comp,vals)
        self.mean = mygp.mean
        self.ls = mygp.ls
        self.amp2 = mygp.amp2
        self.noise = mygp.noise

        # Save hyperparameter samples
        #self.hyper_samples.append((self.mean, self.noise, self.amp2, self.ls))
        #self.dump_hypers()

        return


########NEW FILE########
__FILENAME__ = GPEIOptChooser
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
from spearmint import gp
import sys
from spearmint import util
import tempfile
import copy
import numpy          as np
import numpy.random   as npr
import scipy.linalg   as spla
import scipy.stats    as sps
import scipy.optimize as spo
import cPickle
import multiprocessing

from helpers import *
from Locker  import *

def optimize_pt(c, b, comp, pend, vals, model):
    ret = spo.fmin_l_bfgs_b(model.grad_optimize_ei_over_hypers,
                            c.flatten(), args=(comp, pend, vals),
                            bounds=b, disp=0)
    return ret[0]

def init(expt_dir, arg_string):
    args = util.unpack_args(arg_string)
    return GPEIOptChooser(expt_dir, **args)
"""
Chooser module for the Gaussian process expected improvement (EI)
acquisition function where points are sampled densely in the unit
hypercube and then a subset of the points are optimized to maximize EI
over hyperparameter samples.  Slice sampling is used to sample
Gaussian process hyperparameters.
"""
class GPEIOptChooser:

    def __init__(self, expt_dir, covar="Matern52", mcmc_iters=10,
                 pending_samples=100, noiseless=False, burnin=100,
                 grid_subset=20, use_multiprocessing=True):
        self.cov_func        = getattr(gp, covar)
        self.locker          = Locker()
        self.state_pkl       = os.path.join(expt_dir, self.__module__ + ".pkl")
        self.stats_file      = os.path.join(expt_dir,
                                   self.__module__ + "_hyperparameters.txt")
        self.mcmc_iters      = int(mcmc_iters)
        self.burnin          = int(burnin)
        self.needs_burnin    = True
        self.pending_samples = int(pending_samples)
        self.D               = -1
        self.hyper_iters     = 1        
        # Number of points to optimize EI over
        self.grid_subset     = int(grid_subset)
        self.noiseless       = bool(int(noiseless))
        self.hyper_samples = []

        self.noise_scale = 0.1  # horseshoe prior
        self.amp2_scale  = 1    # zero-mean log normal prior
        self.max_ls      = 2    # top-hat prior on length scales

        # If multiprocessing fails or deadlocks, set this to False
        self.use_multiprocessing = bool(int(use_multiprocessing))


    def dump_hypers(self):
        self.locker.lock_wait(self.state_pkl)

        # Write the hyperparameters out to a Pickle.
        fh = tempfile.NamedTemporaryFile(mode='w', delete=False)
        cPickle.dump({ 'dims'          : self.D,
                       'ls'            : self.ls,
                       'amp2'          : self.amp2,
                       'noise'         : self.noise,
                       'hyper_samples' : self.hyper_samples,
                       'mean'          : self.mean },
                     fh)
        fh.close()

        # Use an atomic move for better NFS happiness.
        cmd = 'mv "%s" "%s"' % (fh.name, self.state_pkl)
        os.system(cmd) # TODO: Should check system-dependent return status.

        self.locker.unlock(self.state_pkl)

        # Write the hyperparameters out to a human readable file as well
        fh    = open(self.stats_file, 'w')
        fh.write('Mean Noise Amplitude <length scales>\n')
        fh.write('-----------ALL SAMPLES-------------\n')
        meanhyps = 0*np.hstack(self.hyper_samples[0])
        for i in self.hyper_samples:
            hyps = np.hstack(i)
            meanhyps += (1/float(len(self.hyper_samples)))*hyps
            for j in hyps:
                fh.write(str(j) + ' ')
            fh.write('\n')

        fh.write('-----------MEAN OF SAMPLES-------------\n')
        for j in meanhyps:
            fh.write(str(j) + ' ')
        fh.write('\n')
        fh.close()

    # This passes out html or javascript to display interesting
    # stats - such as the length scales (sensitivity to various
    # dimensions).
    def generate_stats_html(self):
        # Need this because the model may not necessarily be
        # initialized when this code is called.
        if not self._read_only():
            return 'Chooser not yet ready to display output'

        mean_mean  = np.mean(np.vstack([h[0] for h in self.hyper_samples]))
        mean_noise = np.mean(np.vstack([h[1] for h in self.hyper_samples]))
        mean_ls    = np.mean(np.vstack([h[3][np.newaxis,:] for h in self.hyper_samples]),0)

        try:
            output = (
                '<br /><span class=\"label label-info\">Estimated mean:</span> ' + str(mean_mean) + 
                '<br /><span class=\"label label-info\">Estimated noise:</span> ' + str(mean_noise) + 
                '<br /><br /><span class=\"label label-info\">Inverse parameter sensitivity' +
                ' - Gaussian Process length scales</span><br /><br />' +
                '<div id=\"lschart\"></div><script type=\"text/javascript\">' +
                'var lsdata = [' + ','.join(['%.2f' % i for i in mean_ls]) + '];')
        except:
            return 'Chooser not yet ready to display output.'

        output += ('bar_chart("#lschart", lsdata, ' + str(self.max_ls) + ');' +
                   '</script>')
        return output

    # Read in the chooser from file. Returns True only on success
    def _read_only(self):
        if os.path.exists(self.state_pkl):
            fh    = open(self.state_pkl, 'r')
            state = cPickle.load(fh)
            fh.close()

            self.D             = state['dims']
            self.ls            = state['ls']
            self.amp2          = state['amp2']
            self.noise         = state['noise']
            self.mean          = state['mean']
            self.hyper_samples = state['hyper_samples']
            self.needs_burnin  = False
            return True

        return False

    def _real_init(self, dims, values):
        self.locker.lock_wait(self.state_pkl)

        self.randomstate = npr.get_state()
        if os.path.exists(self.state_pkl):
            fh    = open(self.state_pkl, 'r')
            state = cPickle.load(fh)
            fh.close()

            self.D             = state['dims']
            self.ls            = state['ls']
            self.amp2          = state['amp2']
            self.noise         = state['noise']
            self.mean          = state['mean']
            self.hyper_samples = state['hyper_samples']
            self.needs_burnin  = False
        else:

            # Input dimensionality.
            self.D = dims

            # Initial length scales.
            self.ls = np.ones(self.D)

            # Initial amplitude.
            self.amp2 = np.std(values)+1e-4

            # Initial observation noise.
            self.noise = 1e-3

            # Initial mean.
            self.mean = np.mean(values)

            # Save hyperparameter samples
            self.hyper_samples.append((self.mean, self.noise, self.amp2,
                                       self.ls))

        self.locker.unlock(self.state_pkl)

    def cov(self, x1, x2=None):
        if x2 is None:
            return self.amp2 * (self.cov_func(self.ls, x1, None)
                               + 1e-6*np.eye(x1.shape[0]))
        else:
            return self.amp2 * self.cov_func(self.ls, x1, x2)

    # Given a set of completed 'experiments' in the unit hypercube with
    # corresponding objective 'values', pick from the next experiment to
    # run according to the acquisition function.
    def next(self, grid, values, durations,
             candidates, pending, complete):

        # Don't bother using fancy GP stuff at first.
        if complete.shape[0] < 2:
            return int(candidates[0])

        # Perform the real initialization.
        if self.D == -1:
            self._real_init(grid.shape[1], values[complete])

        # Grab out the relevant sets.
        comp = grid[complete,:]
        cand = grid[candidates,:]
        pend = grid[pending,:]
        vals = values[complete]
        numcand = cand.shape[0]

        # Spray a set of candidates around the min so far
        best_comp = np.argmin(vals)
        cand2 = np.vstack((np.random.randn(10,comp.shape[1])*0.001 +
                           comp[best_comp,:], cand))

        if self.mcmc_iters > 0:

            # Possibly burn in.
            if self.needs_burnin:
                for mcmc_iter in xrange(self.burnin):
                    self.sample_hypers(comp, vals)
                    log("BURN %d/%d] mean: %.2f  amp: %.2f "
                                     "noise: %.4f  min_ls: %.4f  max_ls: %.4f"
                                     % (mcmc_iter+1, self.burnin, self.mean,
                                        np.sqrt(self.amp2), self.noise,
                                        np.min(self.ls), np.max(self.ls)))
                self.needs_burnin = False

            # Sample from hyperparameters.
            # Adjust the candidates to hit ei peaks
            self.hyper_samples = []
            for mcmc_iter in xrange(self.mcmc_iters):
                self.sample_hypers(comp, vals)
                log("%d/%d] mean: %.2f  amp: %.2f  noise: %.4f "
                                 "min_ls: %.4f  max_ls: %.4f"
                                 % (mcmc_iter+1, self.mcmc_iters, self.mean,
                                    np.sqrt(self.amp2), self.noise,
                                    np.min(self.ls), np.max(self.ls)))
            self.dump_hypers()

            b = []# optimization bounds
            for i in xrange(0, cand.shape[1]):
                b.append((0, 1))

            overall_ei = self.ei_over_hypers(comp,pend,cand2,vals)
            inds = np.argsort(np.mean(overall_ei,axis=1))[-self.grid_subset:]
            cand2 = cand2[inds,:]

            # Optimize each point in parallel
            if self.use_multiprocessing:
                pool = multiprocessing.Pool(self.grid_subset)
                results = [pool.apply_async(optimize_pt,args=(
                            c,b,comp,pend,vals,copy.copy(self))) for c in cand2]
                for res in results:
                    cand = np.vstack((cand, res.get(1e8)))
                pool.close()
            else:
                # This is old code to optimize each point in parallel.
                for i in xrange(0, cand2.shape[0]):
                    log("Optimizing candidate %d/%d" %
                        (i+1, cand2.shape[0]))
                    #self.check_grad_ei(cand2[i,:].flatten(), comp, pend, vals)
                    ret = spo.fmin_l_bfgs_b(self.grad_optimize_ei_over_hypers,
                                            cand2[i,:].flatten(), args=(comp,pend,vals),
                                            bounds=b, disp=0)
                    cand2[i,:] = ret[0]
                cand = np.vstack((cand, cand2))

            overall_ei = self.ei_over_hypers(comp,pend,cand,vals)
            best_cand = np.argmax(np.mean(overall_ei, axis=1))

            if (best_cand >= numcand):
                return (int(numcand), cand[best_cand,:])

            return int(candidates[best_cand])

        else:
            # Optimize hyperparameters
            self.optimize_hypers(comp, vals)

            log("mean: %.2f  amp: %.2f  noise: %.4f  "
                             "min_ls: %.4f  max_ls: %.4f"
                             % (self.mean, np.sqrt(self.amp2), self.noise,
                                np.min(self.ls), np.max(self.ls)))

            # Optimize over EI
            b = []# optimization bounds
            for i in xrange(0, cand.shape[1]):
                b.append((0, 1))

            for i in xrange(0, cand2.shape[0]):
                ret = spo.fmin_l_bfgs_b(self.grad_optimize_ei,
                                        cand2[i,:].flatten(), args=(comp,vals,True),
                                        bounds=b, disp=0)
                cand2[i,:] = ret[0]
            cand = np.vstack((cand, cand2))

            ei = self.compute_ei(comp, pend, cand, vals)
            best_cand = np.argmax(ei)

            if (best_cand >= numcand):
                return (int(numcand), cand[best_cand,:])

            return int(candidates[best_cand])

    # Compute EI over hyperparameter samples
    def ei_over_hypers(self,comp,pend,cand,vals):
        overall_ei = np.zeros((cand.shape[0], self.mcmc_iters))
        for mcmc_iter in xrange(self.mcmc_iters):
            hyper = self.hyper_samples[mcmc_iter]
            self.mean = hyper[0]
            self.noise = hyper[1]
            self.amp2 = hyper[2]
            self.ls = hyper[3]
            overall_ei[:,mcmc_iter] = self.compute_ei(comp, pend, cand,
                                                      vals)
        return overall_ei

    def check_grad_ei(self, cand, comp, pend, vals):
        (ei,dx1) = self.grad_optimize_ei_over_hypers(cand, comp, pend, vals)
        dx2 = dx1*0
        idx = np.zeros(cand.shape[0])
        for i in xrange(0, cand.shape[0]):
            idx[i] = 1e-6
            (ei1,tmp) = self.grad_optimize_ei_over_hypers(cand + idx, comp, pend, vals)
            (ei2,tmp) = self.grad_optimize_ei_over_hypers(cand - idx, comp, pend, vals)
            dx2[i] = (ei - ei2)/(2*1e-6)
            idx[i] = 0
        print 'computed grads', dx1
        print 'finite diffs', dx2
        print (dx1/dx2)
        print np.sum((dx1 - dx2)**2)
        time.sleep(2)

    # Adjust points by optimizing EI over a set of hyperparameter samples
    def grad_optimize_ei_over_hypers(self, cand, comp, pend, vals, compute_grad=True):
        summed_ei = 0
        summed_grad_ei = np.zeros(cand.shape).flatten()
        ls = self.ls.copy()
        amp2 = self.amp2
        mean = self.mean
        noise = self.noise

        for hyper in self.hyper_samples:
            self.mean = hyper[0]
            self.noise = hyper[1]
            self.amp2 = hyper[2]
            self.ls = hyper[3]
            if compute_grad:
                (ei,g_ei) = self.grad_optimize_ei(cand,comp,pend,vals,compute_grad)
                summed_grad_ei = summed_grad_ei + g_ei
            else:
                ei = self.grad_optimize_ei(cand,comp,pend,vals,compute_grad)
            summed_ei += ei

        self.mean = mean
        self.amp2 = amp2
        self.noise = noise
        self.ls = ls.copy()

        if compute_grad:
            return (summed_ei, summed_grad_ei)
        else:
            return summed_ei

    # Adjust points based on optimizing their ei
    def grad_optimize_ei(self, cand, comp, pend, vals, compute_grad=True):
        if pend.shape[0] == 0:
            best = np.min(vals)
            cand = np.reshape(cand, (-1, comp.shape[1]))

            # The primary covariances for prediction.
            comp_cov   = self.cov(comp)
            cand_cross = self.cov(comp, cand)

            # Compute the required Cholesky.
            obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
            obsv_chol = spla.cholesky(obsv_cov, lower=True)

            cov_grad_func = getattr(gp, 'grad_' + self.cov_func.__name__)
            cand_cross_grad = cov_grad_func(self.ls, comp, cand)

            # Predictive things.
            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v)
            u      = (best - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            if not compute_grad:
                return ei

            # Gradients of ei w.r.t. mean and variance
            g_ei_m = -ncdf
            g_ei_s2 = 0.5*npdf / func_s

            # Apply covariance function
            grad_cross = np.squeeze(cand_cross_grad)

            grad_xp_m = np.dot(alpha.transpose(),grad_cross)
            grad_xp_v = np.dot(-2*spla.cho_solve(
                    (obsv_chol, True),cand_cross).transpose(), grad_cross)

            grad_xp = 0.5*self.amp2*(grad_xp_m*g_ei_m + grad_xp_v*g_ei_s2)
            ei = -np.sum(ei)

            return ei, grad_xp.flatten()

        else:
            # If there are pending experiments, fantasize their outcomes.
            cand = np.reshape(cand, (-1, comp.shape[1]))

            # Create a composite vector of complete and pending.
            comp_pend = np.concatenate((comp, pend))

            # Compute the covariance and Cholesky decomposition.
            comp_pend_cov  = (self.cov(comp_pend) +
                              self.noise*np.eye(comp_pend.shape[0]))
            comp_pend_chol = spla.cholesky(comp_pend_cov, lower=True)

            # Compute submatrices.
            pend_cross = self.cov(comp, pend)
            pend_kappa = self.cov(pend)

            # Use the sub-Cholesky.
            obsv_chol = comp_pend_chol[:comp.shape[0],:comp.shape[0]]

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.cho_solve((obsv_chol, True), pend_cross)

            # Finding predictive means and variances.
            pend_m = np.dot(pend_cross.T, alpha) + self.mean
            pend_K = pend_kappa - np.dot(pend_cross.T, beta)

            # Take the Cholesky of the predictive covariance.
            pend_chol = spla.cholesky(pend_K, lower=True)

            # Make predictions.
            npr.set_state(self.randomstate)
            pend_fant = np.dot(pend_chol, npr.randn(pend.shape[0],self.pending_samples)) + pend_m[:,None]

            # Include the fantasies.
            fant_vals = np.concatenate(
                (np.tile(vals[:,np.newaxis],
                         (1,self.pending_samples)), pend_fant))

            # Compute bests over the fantasies.
            bests = np.min(fant_vals, axis=0)

            # Now generalize from these fantasies.
            cand_cross = self.cov(comp_pend, cand)
            cov_grad_func = getattr(gp, 'grad_' + self.cov_func.__name__)
            cand_cross_grad = cov_grad_func(self.ls, comp_pend, cand)

            # Solve the linear systems.
            alpha  = spla.cho_solve((comp_pend_chol, True),
                                    fant_vals - self.mean)
            beta   = spla.solve_triangular(comp_pend_chol, cand_cross,
                                           lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v[:,np.newaxis])
            u      = (bests[np.newaxis,:] - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            # Gradients of ei w.r.t. mean and variance
            g_ei_m = -ncdf
            g_ei_s2 = 0.5*npdf / func_s

            # Apply covariance function
            grad_cross = np.squeeze(cand_cross_grad)

            grad_xp_m = np.dot(alpha.transpose(),grad_cross)
            grad_xp_v = np.dot(-2*spla.cho_solve(
                    (comp_pend_chol, True),cand_cross).transpose(), grad_cross)

            grad_xp = 0.5*self.amp2*(grad_xp_m*np.tile(g_ei_m,(comp.shape[1],1)).T + (grad_xp_v.T*g_ei_s2).T)
            ei = -np.mean(ei, axis=1)
            grad_xp = np.mean(grad_xp,axis=0)

            return ei, grad_xp.flatten()

    def compute_ei(self, comp, pend, cand, vals):
        if pend.shape[0] == 0:
            # If there are no pending, don't do anything fancy.

            # Current best.
            best = np.min(vals)

            # The primary covariances for prediction.
            comp_cov   = self.cov(comp)
            cand_cross = self.cov(comp, cand)

            # Compute the required Cholesky.
            obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
            obsv_chol = spla.cholesky( obsv_cov, lower=True )

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v)
            u      = (best - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            return ei
        else:
            # If there are pending experiments, fantasize their outcomes.

            # Create a composite vector of complete and pending.
            comp_pend = np.concatenate((comp, pend))

            # Compute the covariance and Cholesky decomposition.
            comp_pend_cov  = (self.cov(comp_pend) +
                              self.noise*np.eye(comp_pend.shape[0]))
            comp_pend_chol = spla.cholesky(comp_pend_cov, lower=True)

            # Compute submatrices.
            pend_cross = self.cov(comp, pend)
            pend_kappa = self.cov(pend)

            # Use the sub-Cholesky.
            obsv_chol = comp_pend_chol[:comp.shape[0],:comp.shape[0]]

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.cho_solve((obsv_chol, True), pend_cross)

            # Finding predictive means and variances.
            pend_m = np.dot(pend_cross.T, alpha) + self.mean
            pend_K = pend_kappa - np.dot(pend_cross.T, beta)

            # Take the Cholesky of the predictive covariance.
            pend_chol = spla.cholesky(pend_K, lower=True)

            # Make predictions.
            npr.set_state(self.randomstate)
            pend_fant = np.dot(pend_chol, npr.randn(pend.shape[0],self.pending_samples)) + pend_m[:,None]

            # Include the fantasies.
            fant_vals = np.concatenate(
                (np.tile(vals[:,np.newaxis],
                         (1,self.pending_samples)), pend_fant))

            # Compute bests over the fantasies.
            bests = np.min(fant_vals, axis=0)

            # Now generalize from these fantasies.
            cand_cross = self.cov(comp_pend, cand)

            # Solve the linear systems.
            alpha  = spla.cho_solve((comp_pend_chol, True),
                                    fant_vals - self.mean)
            beta   = spla.solve_triangular(comp_pend_chol, cand_cross,
                                           lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v[:,np.newaxis])
            u      = (bests[np.newaxis,:] - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            return np.mean(ei, axis=1)

    def sample_hypers(self, comp, vals):
        if self.noiseless:
            self.noise = 1e-3
            self._sample_noiseless(comp, vals)
        else:
            self._sample_noisy(comp, vals)
        self._sample_ls(comp, vals)
        self.hyper_samples.append((self.mean, self.noise, self.amp2, self.ls))

    def _sample_ls(self, comp, vals):
        def logprob(ls):
            if np.any(ls < 0) or np.any(ls > self.max_ls):
                return -np.inf

            cov   = (self.amp2 * (self.cov_func(ls, comp, None) +
                1e-6*np.eye(comp.shape[0])) + self.noise*np.eye(comp.shape[0]))
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - self.mean)
            lp    = (-np.sum(np.log(np.diag(chol))) -
                      0.5*np.dot(vals-self.mean, solve))
            return lp

        self.ls = util.slice_sample(self.ls, logprob, compwise=True)

    def _sample_noisy(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = hypers[2]

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0 or noise < 0:
                return -np.inf

            cov   = (amp2 * (self.cov_func(self.ls, comp, None) +
                1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0]))
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in noise horseshoe prior.
            lp += np.log(np.log(1 + (self.noise_scale/noise)**2))

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(np.sqrt(amp2))/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array(
                [self.mean, self.amp2, self.noise]), logprob, compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = hypers[2]

    def _sample_noiseless(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = 1e-3

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0:
                return -np.inf

            cov   = (amp2 * (self.cov_func(self.ls, comp, None) +
                1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0]))
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(np.sqrt(amp2))/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array(
                [self.mean, self.amp2, self.noise]), logprob, compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = 1e-3

    def optimize_hypers(self, comp, vals):
        mygp = gp.GP(self.cov_func.__name__)
        mygp.real_init(comp.shape[1], vals)
        mygp.optimize_hypers(comp,vals)
        self.mean = mygp.mean
        self.ls = mygp.ls
        self.amp2 = mygp.amp2
        self.noise = mygp.noise

        # Save hyperparameter samples
        self.hyper_samples.append((self.mean, self.noise, self.amp2, self.ls))
        self.dump_hypers()

        return

########NEW FILE########
__FILENAME__ = GPEIperSecChooser
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
from spearmint import gp
import sys
from spearmint import util
import tempfile
import numpy          as np
import numpy.random   as npr
import scipy.linalg   as spla
import scipy.stats    as sps
import scipy.optimize as spo
import cPickle

from helpers import *
from Locker  import *

def init(expt_dir, arg_string):
    args = util.unpack_args(arg_string)
    return GPEIperSecChooser(expt_dir, **args)

"""
Chooser module for the Gaussian process expected improvement per
second (EI) acquisition function.  Candidates are sampled densely in the unit
hypercube and then a subset of the most promising points are optimized to maximize
EI per second over hyperparameter samples.  Slice sampling is used to sample
Gaussian process hyperparameters for two GPs, one over the objective function and
the other over the running time of the algorithm.
"""
class GPEIperSecChooser:

    def __init__(self, expt_dir, covar="Matern52", mcmc_iters=10,
                 pending_samples=100, noiseless=False, burnin=100,
                 grid_subset=20):
        self.cov_func        = getattr(gp, covar)
        self.locker          = Locker()
        self.state_pkl       = os.path.join(expt_dir, self.__module__ + ".pkl")

        self.stats_file      = os.path.join(expt_dir,
                                   self.__module__ + "_hyperparameters.txt")
        self.mcmc_iters      = int(mcmc_iters)
        self.burnin          = int(burnin)
        self.needs_burnin    = True
        self.pending_samples = pending_samples
        self.D               = -1
        self.hyper_iters     = 1
        # Number of points to optimize EI over
        self.grid_subset     = int(grid_subset)
        self.noiseless       = bool(int(noiseless))
        self.hyper_samples = []
        self.time_hyper_samples = []

        self.noise_scale = 0.1  # horseshoe prior
        self.amp2_scale  = 1    # zero-mean log normal prior
        self.max_ls      = 10    # top-hat prior on length scales

        self.time_noise_scale = 0.1  # horseshoe prior
        self.time_amp2_scale  = 1    # zero-mean log normal prior
        self.time_max_ls      = 10   # top-hat prior on length scales

    # A simple function to dump out hyperparameters to allow for a hot start
    # if the optimization is restarted.
    def dump_hypers(self):
        self.locker.lock_wait(self.state_pkl)

        # Write the hyperparameters out to a Pickle.
        fh = tempfile.NamedTemporaryFile(mode='w', delete=False)
        cPickle.dump({ 'dims'        : self.D,
                       'ls'          : self.ls,
                       'amp2'        : self.amp2,
                       'noise'       : self.noise,
                       'mean'        : self.mean,
                       'time_ls'     : self.time_ls,
                       'time_amp2'   : self.time_amp2,
                       'time_noise'  : self.time_noise,
                       'time_mean'   : self.time_mean },
                     fh)
        fh.close()

        # Use an atomic move for better NFS happiness.
        cmd = 'mv "%s" "%s"' % (fh.name, self.state_pkl)
        os.system(cmd) # TODO: Should check system-dependent return status.

        self.locker.unlock(self.state_pkl)

    def _real_init(self, dims, values, durations):
        self.locker.lock_wait(self.state_pkl)

        if os.path.exists(self.state_pkl):
            fh    = open(self.state_pkl, 'r')
            state = cPickle.load(fh)
            fh.close()

            self.D          = state['dims']
            self.ls         = state['ls']
            self.amp2       = state['amp2']
            self.noise      = state['noise']
            self.mean       = state['mean']
            self.time_ls    = state['time_ls']
            self.time_amp2  = state['time_amp2']
            self.time_noise = state['time_noise']
            self.time_mean  = state['time_mean']
        else:

            # Input dimensionality.
            self.D = dims

            # Initial length scales.
            self.ls = np.ones(self.D)
            self.time_ls = np.ones(self.D)

            # Initial amplitude.
            self.amp2 = np.std(values)+1e-4
            self.time_amp2 = np.std(durations)+1e-4

            # Initial observation noise.
            self.noise = 1e-3
            self.time_noise = 1e-3

            # Initial mean.
            self.mean = np.mean(values)
            self.time_mean = np.mean(np.log(durations))

        self.locker.unlock(self.state_pkl)

    def cov(self, amp2, ls, x1, x2=None):
        if x2 is None:
            return amp2 * (self.cov_func(ls, x1, None)
                           + 1e-6*np.eye(x1.shape[0]))
        else:
            return amp2 * self.cov_func(ls, x1, x2)

    # Given a set of completed 'experiments' in the unit hypercube with
    # corresponding objective 'values', pick from the next experiment to
    # run according to the acquisition function.
    def next(self, grid, values, durations,
             candidates, pending, complete):

        # Don't bother using fancy GP stuff at first.
        if complete.shape[0] < 2:
            return int(candidates[0])

        # Perform the real initialization.
        if self.D == -1:
            self._real_init(grid.shape[1], values[complete],
                            durations[complete])

        # Grab out the relevant sets.
        comp = grid[complete,:]
        cand = grid[candidates,:]
        pend = grid[pending,:]
        vals = values[complete]
        durs = durations[complete]

        # Bring time into the log domain before we do anything
        # to maintain strict positivity
        durs = np.log(durs)

        # Spray a set of candidates around the min so far
        numcand = cand.shape[0]
        best_comp = np.argmin(vals)
        cand2 = np.vstack((np.random.randn(10,comp.shape[1])*0.001 +
                           comp[best_comp,:], cand))

        if self.mcmc_iters > 0:

            # Possibly burn in.
            if self.needs_burnin:
                for mcmc_iter in xrange(self.burnin):
                    self.sample_hypers(comp, vals, durs)
                    log("BURN %d/%d] mean: %.2f  amp: %.2f "
                                     "noise: %.4f  min_ls: %.4f  max_ls: %.4f"
                                     % (mcmc_iter+1, self.burnin, self.mean,
                                        np.sqrt(self.amp2), self.noise,
                                        np.min(self.ls), np.max(self.ls)))
                self.needs_burnin = False

            # Sample from hyperparameters.
            # Adjust the candidates to hit ei/sec peaks
            self.hyper_samples = []
            for mcmc_iter in xrange(self.mcmc_iters):
                self.sample_hypers(comp, vals, durs)
                log("%d/%d] mean: %.2f  amp: %.2f  noise: %.4f "
                                 "min_ls: %.4f  max_ls: %.4f"
                                 % (mcmc_iter+1, self.mcmc_iters, self.mean,
                                    np.sqrt(self.amp2), self.noise,
                                    np.min(self.ls), np.max(self.ls)))

                log("%d/%d] time_mean: %.2fs time_amp: %.2f  time_noise: %.4f "
                                 "time_min_ls: %.4f  time_max_ls: %.4f"
                                 % (mcmc_iter+1, self.mcmc_iters, np.exp(self.time_mean),
                                    np.sqrt(self.time_amp2), np.exp(self.time_noise),
                                    np.min(self.time_ls), np.max(self.time_ls)))
            self.dump_hypers()

            # Pick the top candidates to optimize over
            overall_ei = self.ei_over_hypers(comp,pend,cand2,vals,durs)
            inds = np.argsort(np.mean(overall_ei, axis=1))[-self.grid_subset:]
            cand2 = cand2[inds,:]

            # Adjust the candidates to hit ei peaks
            b = []# optimization bounds
            for i in xrange(0, cand.shape[1]):
                b.append((0, 1))

            for i in xrange(0, cand2.shape[0]):
                log("Optimizing candidate %d/%d" %
                                 (i+1, cand2.shape[0]))
                ret = spo.fmin_l_bfgs_b(self.grad_optimize_ei_over_hypers,
                                        cand2[i,:].flatten(),
                                        args=(comp,vals,durs,True),
                                        bounds=b, disp=0)
                cand2[i,:] = ret[0]

            cand = np.vstack((cand, cand2))

            overall_ei = self.ei_over_hypers(comp,pend,cand,vals,durs)
            best_cand = np.argmax(np.mean(overall_ei, axis=1))
            self.dump_hypers()
            if (best_cand >= numcand):
                return (int(numcand), cand[best_cand,:])

            return int(candidates[best_cand])

        else:
            # Optimize hyperparameters
            self.optimize_hypers(comp, vals, durs)

            log("mean: %f  amp: %f  noise: %f "
                             "min_ls: %f  max_ls: %f"
                             % (self.mean, np.sqrt(self.amp2),
                                self.noise, np.min(self.ls), np.max(self.ls)))

            # Pick the top candidates to optimize over
            ei = self.compute_ei_per_s(comp, pend, cand2, vals, durs)
            inds = np.argsort(np.mean(overall_ei, axis=1))[-self.grid_subset:]
            cand2 = cand2[inds,:]

            # Adjust the candidates to hit ei peaks
            b = []# optimization bounds
            for i in xrange(0, cand.shape[1]):
                b.append((0, 1))

            for i in xrange(0, cand2.shape[0]):
                log("Optimizing candidate %d/%d" %
                                 (i+1, cand2.shape[0]))
                ret = spo.fmin_l_bfgs_b(self.grad_optimize_ei,
                                        cand2[i,:].flatten(),
                                        args=(comp,vals,durs,True),
                                        bounds=b, disp=0)
                cand2[i,:] = ret[0]

            cand = np.vstack((cand, cand2))
            ei = self.compute_ei_per_s(comp, pend, cand, vals, durs)

            best_cand = np.argmax(ei)
            self.dump_hypers()

            if (best_cand >= numcand):
                return (int(numcand), cand[best_cand,:])

            return int(candidates[best_cand])

    # Compute EI over hyperparameter samples
    def ei_over_hypers(self,comp,pend,cand,vals,durs):
        overall_ei = np.zeros((cand.shape[0], self.mcmc_iters))
        for mcmc_iter in xrange(self.mcmc_iters):
            hyper = self.hyper_samples[mcmc_iter]
            time_hyper = self.time_hyper_samples[mcmc_iter]
            self.mean = hyper[0]
            self.noise = hyper[1]
            self.amp2 = hyper[2]
            self.ls = hyper[3]

            self.time_mean = time_hyper[0]
            self.time_noise = time_hyper[1]
            self.time_amp2 = time_hyper[2]
            self.time_ls = time_hyper[3]

            overall_ei[:,mcmc_iter] = self.compute_ei_per_s(comp, pend, cand,
                                                            vals, durs.squeeze())

            return overall_ei

    def check_grad_ei_per(self, cand, comp, vals, durs):
        (ei,dx1) = self.grad_optimize_ei_over_hypers(cand, comp, vals, durs)
        dx2 = dx1*0
        idx = np.zeros(cand.shape[0])
        for i in xrange(0, cand.shape[0]):
            idx[i] = 1e-6
            (ei1,tmp) = self.grad_optimize_ei_over_hypers(cand + idx, comp, vals, durs)
            (ei2,tmp) = self.grad_optimize_ei_over_hypers(cand - idx, comp, vals, durs)
            dx2[i] = (ei - ei2)/(2*1e-6)
            idx[i] = 0
        print 'computed grads', dx1
        print 'finite diffs', dx2
        print (dx1/dx2)
        print np.sum((dx1 - dx2)**2)
        time.sleep(2)

    # Adjust points by optimizing EI over a set of hyperparameter samples
    def grad_optimize_ei_over_hypers(self, cand, comp, vals, durs, compute_grad=True):
        summed_ei = 0
        summed_grad_ei = np.zeros(cand.shape).flatten()

        for mcmc_iter in xrange(self.mcmc_iters):
            hyper = self.hyper_samples[mcmc_iter]
            time_hyper = self.time_hyper_samples[mcmc_iter]
            self.mean = hyper[0]
            self.noise = hyper[1]
            self.amp2 = hyper[2]
            self.ls = hyper[3]

            self.time_mean = time_hyper[0]
            self.time_noise = time_hyper[1]
            self.time_amp2 = time_hyper[2]
            self.time_ls = time_hyper[3]

            if compute_grad:
                (ei,g_ei) = self.grad_optimize_ei(cand,comp,vals,durs,compute_grad)
                summed_grad_ei = summed_grad_ei + g_ei
            else:
                ei = self.grad_optimize_ei(cand,comp,vals,durs,compute_grad)

            summed_ei += ei

        if compute_grad:
            return (summed_ei, summed_grad_ei)
        else:
            return summed_ei

    def grad_optimize_ei(self, cand, comp, vals, durs, compute_grad=True):
        # Here we have to compute the gradients for ei per second
        # This means deriving through the two kernels, the one for predicting
        # time and the one predicting ei
        best = np.min(vals)
        cand = np.reshape(cand, (-1, comp.shape[1]))

        # First we make predictions for the durations
        # Compute covariances
        comp_time_cov   = self.cov(self.time_amp2, self.time_ls, comp)
        cand_time_cross = self.cov(self.time_amp2, self.time_ls,comp,cand)

        # Cholesky decompositions
        obsv_time_cov  = comp_time_cov + self.time_noise*np.eye(comp.shape[0])
        obsv_time_chol = spla.cholesky( obsv_time_cov, lower=True )

        # Linear systems
        t_alpha  = spla.cho_solve((obsv_time_chol, True), durs - self.time_mean)

        # Predict marginal mean times and (possibly) variances
        func_time_m = np.dot(cand_time_cross.T, t_alpha) + self.time_mean

        # We don't really need the time variances now
        #func_time_v = self.time_amp2*(1+1e-6) - np.sum(t_beta**2, axis=0)

        # Bring time out of the log domain
        func_time_m = np.exp(func_time_m)

        # Compute derivative of cross-distances.
        grad_cross_r = gp.grad_dist2(self.time_ls, comp, cand)

        # Apply covariance function
        cov_grad_func = getattr(gp, 'grad_' + self.cov_func.__name__)
        cand_cross_grad = cov_grad_func(self.time_ls, comp, cand)
        grad_cross_t = np.squeeze(cand_cross_grad)

        # Now compute the gradients w.r.t. ei
        # The primary covariances for prediction.
        comp_cov   = self.cov(self.amp2, self.ls, comp)
        cand_cross = self.cov(self.amp2, self.ls, comp, cand)

        # Compute the required Cholesky.
        obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
        obsv_chol = spla.cholesky( obsv_cov, lower=True )

        cand_cross_grad = cov_grad_func(self.ls, comp, cand)

        # Predictive things.
        # Solve the linear systems.
        alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
        beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)

        # Predict the marginal means and variances at candidates.
        func_m = np.dot(cand_cross.T, alpha) + self.mean
        func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

        # Expected improvement
        func_s = np.sqrt(func_v)
        u      = (best - func_m) / func_s
        ncdf   = sps.norm.cdf(u)
        npdf   = sps.norm.pdf(u)
        ei     = func_s*(u*ncdf + npdf)

        ei_per_s = -np.sum(ei/func_time_m)
        if not compute_grad:
            return ei

        grad_time_xp_m = np.dot(t_alpha.transpose(),grad_cross_t)

        # Gradients of ei w.r.t. mean and variance
        g_ei_m = -ncdf
        g_ei_s2 = 0.5*npdf / func_s

        # Apply covariance function
        grad_cross = np.squeeze(cand_cross_grad)

        grad_xp_m = np.dot(alpha.transpose(),grad_cross)
        grad_xp_v = np.dot(-2*spla.cho_solve((obsv_chol, True),
                                             cand_cross).transpose(),grad_cross)

        grad_xp = 0.5*self.amp2*(grad_xp_m*g_ei_m + grad_xp_v*g_ei_s2)
        grad_time_xp_m = 0.5*self.time_amp2*grad_time_xp_m*func_time_m
        grad_xp = (func_time_m*grad_xp - ei*grad_time_xp_m)/(func_time_m**2)

        return ei_per_s, grad_xp.flatten()

    def compute_ei_per_s(self, comp, pend, cand, vals, durs):
        # First we make predictions for the durations as that
        # doesn't depend on pending experiments

        # Compute covariances
        comp_time_cov   = self.cov(self.time_amp2, self.time_ls, comp)
        cand_time_cross = self.cov(self.time_amp2, self.time_ls,comp,cand)

        # Cholesky decompositions
        obsv_time_cov  = comp_time_cov + self.time_noise*np.eye(comp.shape[0])
        obsv_time_chol = spla.cholesky( obsv_time_cov, lower=True )

        # Linear systems
        t_alpha  = spla.cho_solve((obsv_time_chol, True), durs - self.time_mean)
        #t_beta   = spla.solve_triangular(obsv_time_chol, cand_time_cross, lower=True)

        # Predict marginal mean times and (possibly) variances
        func_time_m = np.dot(cand_time_cross.T, t_alpha) + self.time_mean
        # We don't really need the time variances now
        #func_time_v = self.time_amp2*(1+1e-6) - np.sum(t_beta**2, axis=0)

        # Bring time out of the log domain
        func_time_m = np.exp(func_time_m)

        if pend.shape[0] == 0:
            # If there are no pending, don't do anything fancy.

            # Current best.
            best = np.min(vals)

            # The primary covariances for prediction.
            comp_cov   = self.cov(self.amp2, self.ls, comp)
            cand_cross = self.cov(self.amp2, self.ls, comp, cand)

            # Compute the required Cholesky.
            obsv_cov  = comp_cov + self.noise*np.eye(comp.shape[0])
            obsv_chol = spla.cholesky( obsv_cov, lower=True )

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.solve_triangular(obsv_chol, cand_cross, lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v)
            u      = (best - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            ei_per_s = ei/func_time_m
            return ei_per_s
        else:
            # If there are pending experiments, fantasize their outcomes.

            # Create a composite vector of complete and pending.
            comp_pend = np.concatenate((comp, pend))

            # Compute the covariance and Cholesky decomposition.
            comp_pend_cov  = self.cov(self.amp2, self.ls, comp_pend) + self.noise*np.eye(comp_pend.shape[0])
            comp_pend_chol = spla.cholesky(comp_pend_cov, lower=True)

            # Compute submatrices.
            pend_cross = self.cov(self.amp2, self.ls, comp, pend)
            pend_kappa = self.cov(self.amp2, self.ls, pend)

            # Use the sub-Cholesky.
            obsv_chol = comp_pend_chol[:comp.shape[0],:comp.shape[0]]

            # Solve the linear systems.
            alpha  = spla.cho_solve((obsv_chol, True), vals - self.mean)
            beta   = spla.cho_solve((obsv_chol, True), pend_cross)

            # Finding predictive means and variances.
            pend_m = np.dot(pend_cross.T, alpha) + self.mean
            pend_K = pend_kappa - np.dot(pend_cross.T, beta)

            # Take the Cholesky of the predictive covariance.
            pend_chol = spla.cholesky(pend_K, lower=True)

            # Make predictions.
            pend_fant = np.dot(pend_chol, npr.randn(pend.shape[0],self.pending_samples)) + pend_m[:,None]

            # Include the fantasies.
            fant_vals = np.concatenate((np.tile(vals[:,np.newaxis],
                                                (1,self.pending_samples)), pend_fant))

            # Compute bests over the fantasies.
            bests = np.min(fant_vals, axis=0)

            # Now generalize from these fantasies.
            cand_cross = self.cov(self.amp2, self.ls, comp_pend, cand)

            # Solve the linear systems.
            alpha  = spla.cho_solve((comp_pend_chol, True), fant_vals - self.mean)
            beta   = spla.solve_triangular(comp_pend_chol, cand_cross, lower=True)

            # Predict the marginal means and variances at candidates.
            func_m = np.dot(cand_cross.T, alpha) + self.mean
            func_v = self.amp2*(1+1e-6) - np.sum(beta**2, axis=0)

            # Expected improvement
            func_s = np.sqrt(func_v[:,np.newaxis])
            u      = (bests[np.newaxis,:] - func_m) / func_s
            ncdf   = sps.norm.cdf(u)
            npdf   = sps.norm.pdf(u)
            ei     = func_s*( u*ncdf + npdf)

            return np.divide(np.mean(ei, axis=1), func_time_m)

    def sample_hypers(self, comp, vals, durs):
        if self.noiseless:
            self.noise = 1e-3
            self._sample_noiseless(comp, vals)
        else:
            self._sample_noisy(comp, vals)
        self._sample_ls(comp, vals)

        self._sample_time_noisy(comp, durs.squeeze())
        self._sample_time_ls(comp, durs.squeeze())

        self.hyper_samples.append((self.mean, self.noise, self.amp2, self.ls))
        self.time_hyper_samples.append((self.time_mean, self.time_noise, self.time_amp2,
                                        self.time_ls))

    def _sample_ls(self, comp, vals):
        def logprob(ls):
            if np.any(ls < 0) or np.any(ls > self.max_ls):
                return -np.inf

            cov   = self.amp2 * (self.cov_func(ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + self.noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - self.mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-self.mean, solve)
            return lp

        self.ls = util.slice_sample(self.ls, logprob, compwise=True)

    def _sample_time_ls(self, comp, vals):
        def logprob(ls):
            if np.any(ls < 0) or np.any(ls > self.time_max_ls):
                return -np.inf

            cov   = self.time_amp2 * (self.cov_func(ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + self.time_noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - self.time_mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-self.time_mean, solve)
            return lp

        self.time_ls = util.slice_sample(self.time_ls, logprob, compwise=True)

    def _sample_noisy(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = hypers[2]

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0 or noise < 0:
                return -np.inf

            cov   = amp2 * (self.cov_func(self.ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in noise horseshoe prior.
            lp += np.log(np.log(1 + (self.noise_scale/noise)**2))
            #lp -= 0.5*(np.log(noise)/self.noise_scale)**2

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(amp2)/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array([self.mean, self.amp2, self.noise]), logprob, compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = hypers[2]

    def _sample_time_noisy(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = hypers[2]

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0 or noise < 0:
                return -np.inf

            cov   = amp2 * (self.cov_func(self.time_ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in noise horseshoe prior.
            lp += np.log(np.log(1 + (self.time_noise_scale/noise)**2))
            #lp -= 0.5*(np.log(noise)/self.time_noise_scale)**2

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(np.sqrt(amp2))/self.time_amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array([self.time_mean, self.time_amp2, self.time_noise]), logprob, compwise=False)
        self.time_mean  = hypers[0]
        self.time_amp2  = hypers[1]
        self.time_noise = hypers[2]

    def _sample_noiseless(self, comp, vals):
        def logprob(hypers):
            mean  = hypers[0]
            amp2  = hypers[1]
            noise = 1e-3

            # This is pretty hacky, but keeps things sane.
            if mean > np.max(vals) or mean < np.min(vals):
                return -np.inf

            if amp2 < 0:
                return -np.inf

            cov   = amp2 * (self.cov_func(self.ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)

            # Roll in amplitude lognormal prior
            lp -= 0.5*(np.log(amp2)/self.amp2_scale)**2

            return lp

        hypers = util.slice_sample(np.array([self.mean, self.amp2, self.noise]), logprob, compwise=False)
        self.mean  = hypers[0]
        self.amp2  = hypers[1]
        self.noise = 1e-3

    def optimize_hypers(self, comp, vals, durs):
        # First the GP to observations
        mygp = gp.GP(self.cov_func.__name__)
        mygp.real_init(comp.shape[1], vals)
        mygp.optimize_hypers(comp,vals)
        self.mean = mygp.mean
        self.ls = mygp.ls
        self.amp2 = mygp.amp2
        self.noise = mygp.noise

        # Now the GP to times
        timegp = gp.GP(self.cov_func.__name__)
        timegp.real_init(comp.shape[1], durs)
        timegp.optimize_hypers(comp, durs)
        self.time_mean  = timegp.mean
        self.time_amp2  = timegp.amp2
        self.time_noise = timegp.noise
        self.time_ls    = timegp.ls

        # Save hyperparameter samples
        self.hyper_samples.append((self.mean, self.noise, self.amp2, self.ls))
        self.time_hyper_samples.append((self.time_mean, self.time_noise, self.time_amp2,
                                        self.time_ls))
        self.dump_hypers()

########NEW FILE########
__FILENAME__ = RandomChooser
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import numpy        as np
import numpy.random as npr

def init(expt_dir, arg_string):
    return RandomChooser()

class RandomChooser:

    def __init__(self):
        pass

    def next(self, grid, values, durations,
             candidates, pending, complete):
        return int(candidates[int(np.floor(candidates.shape[0]*npr.rand()))])


########NEW FILE########
__FILENAME__ = RandomForestEIChooser
import numpy        as np
import numpy.random as npr
import scipy.stats  as sps
import sklearn.ensemble
import sklearn.ensemble.forest
from spearmint import util

from sklearn.externals.joblib import Parallel, delayed

def init(expt_dir, arg_string):
    args = util.unpack_args(arg_string)
    return RandomForestEIChooser(**args)

class RandomForestRegressorWithVariance(sklearn.ensemble.RandomForestRegressor):

    def predict(self,X):
        # Check data
        X = np.atleast_2d(X)

        all_y_hat = [ tree.predict(X) for tree in self.estimators_ ]

        # Reduce
        y_hat = sum(all_y_hat) / self.n_estimators
        y_var = np.var(all_y_hat,axis=0,ddof=1)

        return y_hat, y_var

class RandomForestEIChooser:

    def __init__(self,n_trees=50,
                 max_depth=None,
                 min_samples_split=1,
                 max_monkeys=7,
                 max_features="auto",
                 n_jobs=1,
                 random_state=None):
        self.n_trees = float(n_trees)
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.n_jobs = float(n_jobs)
        self.random_state = random_state
        self.rf = RandomForestRegressorWithVariance(n_estimators=n_trees,
                                                    max_depth=max_depth,
                                                    min_samples_split=min_samples_split,
                                                    max_features=max_features,
                                                    n_jobs=n_jobs,
                                                    random_state=random_state)

    def next(self, grid, values, durations,
             candidates, pending, complete):
        # Grab out the relevant sets.

        # Don't bother using fancy RF stuff at first.
        if complete.shape[0] < 2:
            return int(candidates[0])

        # Grab out the relevant sets.
        comp = grid[complete,:]
        cand = grid[candidates,:]
        pend = grid[pending,:]
        vals = values[complete]

        self.rf.fit(comp,vals)

        if pend.shape[0] != 0:
            # Generate fantasies for pending
            func_m, func_v = self.rf.predict(pend)
            vals_pend = func_m + np.sqrt(func_v) + npr.randn(func_m.shape[0])

            # Re-fit using fantasies
            self.rf.fit(np.vstack[comp,pend],np.hstack[vals,vals_pend])

            # Predict the marginal means and variances at candidates.
        func_m, func_v = self.rf.predict(cand)

        # Current best.
        best = np.min(vals)

        # Expected improvement
        func_s = np.sqrt(func_v) + 0.0001
        u      = (best - func_m) / func_s
        ncdf   = sps.norm.cdf(u)
        npdf   = sps.norm.pdf(u)
        ei     = func_s*( u*ncdf + npdf)

        best_cand = np.argmax(ei)
        ei.sort()

        return int(candidates[best_cand])

########NEW FILE########
__FILENAME__ = SequentialChooser
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
# 
# This code is written for research and educational purposes only to 
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np

def init(expt_dir, arg_string):
    return SequentialChooser()

class SequentialChooser:

    def __init__(self):
        pass

    def next(self, grid, values, durations,
             candidates, pending, complete):
        return int(candidates[0])


########NEW FILE########
__FILENAME__ = dispatch


class DispatchDriver(object):
    def submit_job(job):
        '''Schedule a job for execution.'''
        pass


    def is_proc_alive(job_ids):
        '''Check on the status of executing jobs.'''
        pass

########NEW FILE########
__FILENAME__ = local
import os
import multiprocessing

from dispatch import DispatchDriver
from helpers  import *
from runner   import job_runner
from Locker   import Locker

class LocalDriver(DispatchDriver):
    def submit_job(self, job):
       '''Submit a job for local execution.'''

       name = "%s-%08d" % (job.name, job.id)

       # TODO: figure out if this is necessary....
       locker = Locker()
       locker.unlock(grid_for(job))

       proc = multiprocessing.Process(target=job_runner, args=[job])
       proc.start()

       if proc.is_alive():
           log("Submitted job as process: %d" % proc.pid)
           return proc.pid
       else:
           log("Failed to submit job or job crashed "
               "with return code %d !" % proc.exitcode)
           log("Deleting job file.")
           os.unlink(job_file_for(job))
           return None


    def is_proc_alive(self, job_id, proc_id):
        try:
            # Send an alive signal to proc (note this could kill it in windows)
            os.kill(proc_id, 0)
        except OSError:
            return False

        return True


def init():
    return LocalDriver()

########NEW FILE########
__FILENAME__ = sge
import os
import sys
import re
import subprocess
import drmaa

from dispatch import DispatchDriver
from helpers  import *


# TODO: figure out if these modules are necessary, or if they can be handled in
# the matlab runner or a user script...

# System dependent modules
# Note these are specific to the Harvard configuration
DEFAULT_MODULES = [ 'packages/epd/7.1-2',
                    'packages/matlab/r2011b',
                    'mpi/openmpi/1.2.8/intel',
                    'libraries/mkl/10.0',
                    'packages/cuda/4.0',
                    ]

# Removed from SGE script...
# Load matlab modules
#module load %s

class SGEDriver(DispatchDriver):

    def submit_job(self, job):
        output_file = job_output_file(job)
        job_file    = job_file_for(job)
        modules     = " ".join(DEFAULT_MODULES)
        mint_path   = sys.argv[0]
        sge_script  = 'python %s --run-job "%s" .' % (mint_path, job_file)

        qsub_cmd    = ['qsub', '-S', '/bin/bash',
                       '-N', "%s-%d" % (job.name, job.id),
                       '-e', output_file,
                       '-o', output_file,
                       '-j', 'y',
                      ]

        process = subprocess.Popen(" ".join(qsub_cmd),
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   shell=True)
        output = process.communicate(input=sge_script)[0]
        process.stdin.close()

        # Parse out the job id.
        match = re.search(r'Your job (\d+)', output)

        if match:
            return int(match.group(1))
        else:
            return None, output


    def is_proc_alive(self, job_id, sgeid):
        try:
            s = drmaa.Session()
            s.initialize()

            reset_job = False

            try:
                status = s.jobStatus(str(sgeid))
            except:
                log("EXC: %s\n" % (str(sys.exc_info()[0])))
                log("Could not find SGE id for job %d (%d)\n" % (job_id, sgeid))
                status = -1
                reset_job = True

            if status == drmaa.JobState.UNDETERMINED:
                log("Job %d (%d) in undetermined state.\n" % (job_id, sgeid))
                reset_job = True

            elif status == drmaa.JobState.QUEUED_ACTIVE:
                log("Job %d (%d) waiting in queue.\n" % (job_id, sgeid))

            elif status == drmaa.JobState.RUNNING:
                log("Job %d (%d) is running.\n" % (job_id, sgeid))

            elif status in [drmaa.JobState.SYSTEM_ON_HOLD,
                            drmaa.JobState.USER_ON_HOLD,
                            drmaa.JobState.USER_SYSTEM_ON_HOLD,
                            drmaa.JobState.SYSTEM_SUSPENDED,
                            drmaa.JobState.USER_SUSPENDED]:
                log("Job %d (%d) is held or suspended.\n" % (job_id, sgeid))
                reset_job = True

            elif status == drmaa.JobState.DONE:
                log("Job %d (%d) is finished.\n" % (job_id, sgeid))

            elif status == drmaa.JobState.FAILED:
                log("Job %d (%d) failed.\n" % (job_id, sgeid))
                reset_job = True

            if reset_job:

                try:
                    # Kill the job.
                    s.control(str(sgeid), drmaa.JobControlAction.TERMINATE)
                    log("Killed SGE job %d.\n" % (sgeid))
                except:
                    log("Failed to kill SGE job %d.\n" % (sgeid))

                return False
            else:
                return True

        finally:
            s.exit()


def init():
    return SGEDriver()


########NEW FILE########
__FILENAME__ = ExperimentGrid
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import sys
import tempfile
import cPickle

import numpy        as np
import numpy.random as npr

from spearmint_pb2 import *
from Locker        import *
from sobol_lib     import *
from helpers       import *

CANDIDATE_STATE = 0
SUBMITTED_STATE = 1
RUNNING_STATE   = 2
COMPLETE_STATE  = 3
BROKEN_STATE    = -1

EXPERIMENT_GRID_FILE = 'expt-grid.pkl'

class ExperimentGrid:

    @staticmethod
    def job_running(expt_dir, id):
        expt_grid = ExperimentGrid(expt_dir)
        expt_grid.set_running(id)

    @staticmethod
    def job_complete(expt_dir, id, value, duration):
        log("setting job %d complete" % id)
        expt_grid = ExperimentGrid(expt_dir)
        expt_grid.set_complete(id, value, duration)
        log("set...")

    @staticmethod
    def job_broken(expt_dir, id):
        expt_grid = ExperimentGrid(expt_dir)
        expt_grid.set_broken(id)

    def __init__(self, expt_dir, variables=None, grid_size=None, grid_seed=1):
        self.expt_dir = expt_dir
        self.jobs_pkl = os.path.join(expt_dir, EXPERIMENT_GRID_FILE)
        self.locker   = Locker()

        # Only one process at a time is allowed to have access to the grid.
        self.locker.lock_wait(self.jobs_pkl)

        # Set up the grid for the first time if it doesn't exist.
        if variables is not None and not os.path.exists(self.jobs_pkl):
            self.seed     = grid_seed
            self.vmap     = GridMap(variables, grid_size)
            self.grid     = self._hypercube_grid(self.vmap.card(), grid_size)
            self.status   = np.zeros(grid_size, dtype=int) + CANDIDATE_STATE
            self.values   = np.zeros(grid_size) + np.nan
            self.durs     = np.zeros(grid_size) + np.nan
            self.proc_ids = np.zeros(grid_size, dtype=int)
            self._save_jobs()

        # Or load in the grid from the pickled file.
        else:
            self._load_jobs()


    def __del__(self):
        self._save_jobs()
        if self.locker.unlock(self.jobs_pkl):
            pass
        else:
            raise Exception("Could not release lock on job grid.\n")

    def get_grid(self):
        return self.grid, self.values, self.durs

    def get_candidates(self):
        return np.nonzero(self.status == CANDIDATE_STATE)[0]

    def get_pending(self):
        return np.nonzero((self.status == SUBMITTED_STATE) | (self.status == RUNNING_STATE))[0]

    def get_complete(self):
        return np.nonzero(self.status == COMPLETE_STATE)[0]

    def get_broken(self):
        return np.nonzero(self.status == BROKEN_STATE)[0]

    def get_params(self, index):
        return self.vmap.get_params(self.grid[index,:])

    def get_best(self):
        finite = self.values[np.isfinite(self.values)]
        if len(finite) > 0:
            cur_min = np.min(finite)
            index   = np.nonzero(self.values==cur_min)[0][0]
            return cur_min, index
        else:
            return np.nan, -1

    def get_proc_id(self, id):
        return self.proc_ids[id]

    def add_to_grid(self, candidate):
        # Checks to prevent numerical over/underflow from corrupting the grid
        candidate[candidate > 1.0] = 1.0
        candidate[candidate < 0.0] = 0.0

        # Set up the grid
        self.grid   = np.vstack((self.grid, candidate))
        self.status = np.append(self.status, np.zeros(1, dtype=int) +
                                int(CANDIDATE_STATE))

        self.values = np.append(self.values, np.zeros(1)+np.nan)
        self.durs   = np.append(self.durs, np.zeros(1)+np.nan)
        self.proc_ids = np.append(self.proc_ids, np.zeros(1,dtype=int))

        # Save this out.
        self._save_jobs()
        return self.grid.shape[0]-1

    def set_candidate(self, id):
        self.status[id] = CANDIDATE_STATE
        self._save_jobs()

    def set_submitted(self, id, proc_id):
        self.status[id] = SUBMITTED_STATE
        self.proc_ids[id] = proc_id
        self._save_jobs()

    def set_running(self, id):
        self.status[id] = RUNNING_STATE
        self._save_jobs()

    def set_complete(self, id, value, duration):
        self.status[id] = COMPLETE_STATE
        self.values[id] = value
        self.durs[id]   = duration
        self._save_jobs()

    def set_broken(self, id):
        self.status[id] = BROKEN_STATE
        self._save_jobs()

    def _load_jobs(self):
        fh   = open(self.jobs_pkl, 'r')
        jobs = cPickle.load(fh)
        fh.close()

        self.vmap   = jobs['vmap']
        self.grid   = jobs['grid']
        self.status = jobs['status']
        self.values = jobs['values']
        self.durs   = jobs['durs']
        self.proc_ids = jobs['proc_ids']

    def _save_jobs(self):

        # Write everything to a temporary file first.
        fh = tempfile.NamedTemporaryFile(mode='w', delete=False)
        cPickle.dump({ 'vmap'   : self.vmap,
                       'grid'   : self.grid,
                       'status' : self.status,
                       'values' : self.values,
                       'durs'   : self.durs,
                       'proc_ids' : self.proc_ids }, fh, protocol=-1)
        fh.close()

        # Use an atomic move for better NFS happiness.
        cmd = 'mv "%s" "%s"' % (fh.name, self.jobs_pkl)
        os.system(cmd) # TODO: Should check system-dependent return status.

    def _hypercube_grid(self, dims, size):
        # Generate from a sobol sequence
        sobol_grid = np.transpose(i4_sobol_generate(dims,size,self.seed))

        return sobol_grid

class GridMap:

    def __init__(self, variables, grid_size):
        self.variables   = []
        self.cardinality = 0

        # Count the total number of dimensions and roll into new format.
        for variable in variables:
            self.cardinality += variable.size

            if variable.type == Experiment.ParameterSpec.INT:
                self.variables.append({ 'name' : variable.name,
                                        'size' : variable.size,
                                        'type' : 'int',
                                        'min'  : int(variable.min),
                                        'max'  : int(variable.max)})

            elif variable.type == Experiment.ParameterSpec.FLOAT:
                self.variables.append({ 'name' : variable.name,
                                        'size' : variable.size,
                                        'type' : 'float',
                                        'min'  : float(variable.min),
                                        'max'  : float(variable.max)})

            elif variable.type == Experiment.ParameterSpec.ENUM:
                self.variables.append({ 'name'    : variable.name,
                                        'size'    : variable.size,
                                        'type'    : 'enum',
                                        'options' : list(variable.options)})
            else:
                raise Exception("Unknown parameter type.")
        log("Optimizing over %d dimensions\n" % (self.cardinality))

    def get_params(self, u):
        if u.shape[0] != self.cardinality:
            raise Exception("Hypercube dimensionality is incorrect.")

        params = []
        index  = 0
        for variable in self.variables:
            param = Parameter()

            param.name = variable['name']

            if variable['type'] == 'int':
                for dd in xrange(variable['size']):
                    param.int_val.append(variable['min'] + self._index_map(u[index], variable['max']-variable['min']+1))
                    index += 1

            elif variable['type'] == 'float':
                for dd in xrange(variable['size']):
                    param.dbl_val.append(variable['min'] + u[index]*(variable['max']-variable['min']))
                    index += 1

            elif variable['type'] == 'enum':
                for dd in xrange(variable['size']):
                    ii = self._index_map(u[index], len(variable['options']))
                    index += 1
                    param.str_val.append(variable['options'][ii])

            else:
                raise Exception("Unknown parameter type.")

            params.append(param)

        return params

    def card(self):
        return self.cardinality

    def _index_map(self, u, items):
        u = np.max((u, 0.0))
        u = np.min((u, 1.0))
        return int(np.floor((1-np.finfo(float).eps) * u * float(items)))

########NEW FILE########
__FILENAME__ = gp
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
# 
# This code is written for research and educational purposes only to 
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
gp.py contains utility functions related to computation in Gaussian processes.
"""
import numpy as np
import scipy.linalg as spla
import scipy.optimize as spo
import scipy.io as sio
import scipy.weave
    
SQRT_3 = np.sqrt(3.0)
SQRT_5 = np.sqrt(5.0)

def dist2(ls, x1, x2=None):
    # Assumes NxD and MxD matrices.
    # Compute the squared distance matrix, given length scales.
    
    if x2 is None:
        # Find distance with self for x1.

        # Rescale.
        xx1 = x1 / ls        
        xx2 = xx1

    else:
        # Rescale.
        xx1 = x1 / ls
        xx2 = x2 / ls
    
    r2 = np.maximum(-(np.dot(xx1, 2*xx2.T) 
                       - np.sum(xx1*xx1, axis=1)[:,np.newaxis]
                       - np.sum(xx2*xx2, axis=1)[:,np.newaxis].T), 0.0)

    return r2

def grad_dist2(ls, x1, x2=None):
    if x2 is None:
        x2 = x1
        
    # Rescale.
    x1 = x1 / ls
    x2 = x2 / ls
    
    N = x1.shape[0]
    M = x2.shape[0]
    D = x1.shape[1]
    gX = np.zeros((x1.shape[0],x2.shape[0],x1.shape[1]))

    code = \
    """
    for (int i=0; i<N; i++)
      for (int j=0; j<M; j++)
        for (int d=0; d<D; d++)
          gX(i,j,d) = (2/ls(d))*(x1(i,d) - x2(j,d));
    """
    try:
        scipy.weave.inline(code, ['x1','x2','gX','ls','M','N','D'], \
                       type_converters=scipy.weave.converters.blitz, \
                       compiler='gcc')
    except:
        # The C code weave above is 10x faster than this:
        for i in xrange(0,x1.shape[0]):
            gX[i,:,:] = 2*(x1[i,:] - x2[:,:])*(1/ls)

    return gX

def SE(ls, x1, x2=None, grad=False):
    ls = np.ones(ls.shape)
    cov = np.exp(-0.5 * dist2(ls, x1, x2))
    if grad:
        return (cov, grad_ARDSE(ls, x1, x2))
    else:
        return cov

def ARDSE(ls, x1, x2=None, grad=False):
    cov = np.exp(-0.5 * dist2(ls, x1, x2))
    if grad:
        return (cov, grad_ARDSE(ls, x1, x2))
    else:
        return cov

def grad_ARDSE(ls, x1, x2=None):
    r2 = dist2(ls, x1, x2)
    r  = np.sqrt(r2)
    return -0.5*np.exp(-0.5*r2)[:,:,np.newaxis] * grad_dist2(ls, x1, x2)

def Matern32(ls, x1, x2=None, grad=False):
    r   = np.sqrt(dist2(ls, x1, x2))
    cov = (1 + SQRT_3*r) * np.exp(-SQRT_3*r)
    if grad:
        return (cov, grad_Matern32(ls, x1, x2))
    else:
        return cov

def grad_Matern32(ls, x1, x2=None):
    r       = np.sqrt(dist2(ls, x1, x2))
    grad_r2 = -1.5*np.exp(-SQRT_3*r)
    return grad_r2[:,:,np.newaxis] * grad_dist2(ls, x1, x2)

def Matern52(ls, x1, x2=None, grad=False):
    r2  = np.abs(dist2(ls, x1, x2))
    r   = np.sqrt(r2)
    cov = (1.0 + SQRT_5*r + (5.0/3.0)*r2) * np.exp(-SQRT_5*r)
    if grad:
        return (cov, grad_Matern52(ls, x1, x2))
    else:
        return cov

def grad_Matern52(ls, x1, x2=None):
    r       = np.sqrt(dist2(ls, x1, x2))
    grad_r2 = -(5.0/6.0)*np.exp(-SQRT_5*r)*(1 + SQRT_5*r)
    return grad_r2[:,:,np.newaxis] * grad_dist2(ls, x1, x2)

class GP:
    def __init__(self, covar="Matern52", mcmc_iters=10, noiseless=False):
        self.cov_func        = globals()[covar]
        self.mcmc_iters      = int(mcmc_iters)
        self.D               = -1
        self.hyper_iters     = 1
        self.noiseless       = bool(int(noiseless))
        self.hyper_samples = []
        
        self.noise_scale = 0.1  # horseshoe prior 
        self.amp2_scale  = 1    # zero-mean log normal prior
        self.max_ls      = 2    # top-hat prior on length scales 

    def real_init(self, dims, values):
        # Input dimensionality. 
        self.D = dims

        # Initial length scales.               
        self.ls = np.ones(self.D)

        # Initial amplitude.        
        self.amp2 = np.std(values)

        # Initial observation noise.                                          
        self.noise = 1e-3

        # Initial mean.
        self.mean = np.mean(values)

    def cov(self, x1, x2=None):
        if x2 is None:
            return self.amp2 * (self.cov_func(self.ls, x1, None)
                                + 1e-6*np.eye(x1.shape[0]))
        else:
            return self.amp2 * self.cov_func(self.ls, x1, x2)

    def logprob(self, comp, vals):
            mean  = self.mean
            amp2  = self.amp2
            noise = self.noise
            
            cov   = amp2 * (self.cov_func(self.ls, comp, None) + 1e-6*np.eye(comp.shape[0])) + noise*np.eye(comp.shape[0])
            chol  = spla.cholesky(cov, lower=True)
            solve = spla.cho_solve((chol, True), vals - mean)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(vals-mean, solve)
            return lp

    def optimize_hypers(self, comp, vals):
        self.mean = np.mean(vals)
        diffs     = vals - self.mean

        state = { }

        def jitter_chol(covmat):
            passed = False
            jitter = 1e-8
            val = 0
            while not passed:
                if (jitter > 100000):
                    val = spla.cholesky(np.eye(covmat.shape[0]))
                    break
                try:
                    val = spla.cholesky(covmat +
                        jitter*np.eye(covmat.shape[0]), lower=True)
                    passed = True
                except ValueError:
                    jitter = jitter*1.1
                    print "Covariance matrix not PSD, adding jitter:", jitter
                    passed = False
            return val
        
        def memoize(amp2, noise, ls):
            if ( 'corr' not in state
                 or state['amp2'] != amp2
                 or state['noise'] != noise
                 or np.any(state['ls'] != ls)):

                # Get the correlation matrix
                (corr, grad_corr) = self.cov_func(ls, comp, None, grad=True)
        
                # Scale and add noise & jitter.
                covmat = (amp2 * (corr + 1e-6*np.eye(comp.shape[0])) 
                          + noise * np.eye(comp.shape[0]))

                # Memoize
                state['corr']      = corr
                state['grad_corr'] = grad_corr
                state['chol']      = jitter_chol(covmat)
                state['amp2']      = amp2
                state['noise']     = noise
                state['ls']        = ls
                
            return (state['chol'], state['corr'], state['grad_corr'])

        def nlogprob(hypers):
            amp2  = np.exp(hypers[0])
            noise = np.exp(hypers[1])
            ls    = np.exp(hypers[2:])

            chol  = memoize(amp2, noise, ls)[0]
            solve = spla.cho_solve((chol, True), diffs)
            lp    = -np.sum(np.log(np.diag(chol)))-0.5*np.dot(diffs, solve)
            return -lp

        def grad_nlogprob(hypers):
            amp2  = np.exp(hypers[0])
            noise = np.exp(hypers[1])
            ls    = np.exp(hypers[2:])

            chol, corr, grad_corr = memoize(amp2, noise, ls)
            solve   = spla.cho_solve((chol, True), diffs)
            inv_cov = spla.cho_solve((chol, True), np.eye(chol.shape[0]))

            jacobian = np.outer(solve, solve) - inv_cov

            grad = np.zeros(self.D + 2)

            # Log amplitude gradient.
            grad[0] = 0.5 * np.trace(np.dot( jacobian, corr + 1e-6*np.eye(chol.shape[0]))) * amp2

            # Log noise gradient.
            grad[1] = 0.5 * np.trace(np.dot( jacobian, np.eye(chol.shape[0]))) * noise

            # Log length scale gradients.
            for dd in xrange(self.D):
                grad[dd+2] = 1 * np.trace(np.dot( jacobian, -amp2*grad_corr[:,:,dd]*comp[:,dd][:,np.newaxis]/(np.exp(ls[dd]))))*np.exp(ls[dd])

            # Roll in the prior variance.
            #grad -= 2*hypers/self.hyper_prior

            return -grad
        
        # Initial length scales.
        self.ls = np.ones(self.D)
        # Initial amplitude.
        self.amp2 = np.std(vals)
        # Initial observation noise.
        self.noise = 1e-3
        
        hypers     = np.zeros(self.ls.shape[0]+2)
        hypers[0]  = np.log(self.amp2)
        hypers[1]  = np.log(self.noise)
        hypers[2:] = np.log(self.ls)
        
        # Use a bounded bfgs just to prevent the length-scales and noise from 
        # getting into regions that are numerically unstable
        b = [(-10,10),(-10,10)]
        for i in xrange(comp.shape[1]):
            b.append((-10,5))
  
        hypers = spo.fmin_l_bfgs_b(nlogprob, hypers, grad_nlogprob, args=(), bounds=b, disp=0)
                
        #hypers = spo.fmin_bfgs(nlogprob, hypers, grad_nlogprob, maxiter=100)
        hypers = hypers[0]
        #hypers = spo.fmin_bfgs(nlogprob, hypers, grad_nlogprob, maxiter=100)

        self.amp2  = np.exp(hypers[0])
        self.noise = np.exp(hypers[1])
        self.ls    = np.exp(hypers[2:])

def main():
    try:
        import matplotlib.pyplot as plt
    except:
        pass

    # Let's start with some random values
    x = np.linspace(0,1,10)[:,np.newaxis]*10#np.random.rand(100)[:,np.newaxis]
    y = np.random.randn(10)
    mygp = GP(covar='ARDSE')
    mygp.real_init(x.shape[1], y)

    # Sample some functions given these hyperparameters and plot them
    for i in xrange(0,5):
        x = np.linspace(0,1,100)[:,np.newaxis]*10
        K = mygp.cov(x)
        y = np.random.randn(100)
    
        fsamp = mygp.mean + np.dot(spla.cholesky(K).transpose(), y)
        try:
            plt.plot(x, fsamp)
        except:
            pass

    print 'Loglikelihood before optimizing: ', mygp.logprob(x,y)
    mygp.optimize_hypers(x,y)
    print 'Loglikelihood after optimizing: ', mygp.logprob(x,y)
        
    try:
        plt.show()
    except:
        print 'Install matplotlib to get figures'        

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = helpers
import os
import sys
import subprocess
import tempfile

from google.protobuf import text_format
from spearmint_pb2   import *


def log(*args):
    '''Write a msg to stderr.'''
    for v in args:
        sys.stderr.write(str(v))
    sys.stderr.write("\n")


def sh(cmd):
    '''Run a shell command (blocking until completion).'''
    subprocess.check_call(cmd, shell=True)


def redirect_output(path):
    '''Redirect stdout and stderr to a file.'''
    outfile    = open(path, 'a')
    sys.stdout = outfile
    sys.stderr = outfile


def check_dir(path):
    '''Create a directory if it doesn't exist.'''
    if not os.path.exists(path):
        os.mkdir(path)


def grid_for(job):
    return os.path.join(job.expt_dir, 'expt-grid.pkl')



def file_write_safe(path, data):
    '''Write data to a temporary file, then move to the destination path.'''
    fh = tempfile.NamedTemporaryFile(mode='w', delete=False)
    fh.write(data)
    fh.close()
    cmd = 'mv "%s" "%s"' % (fh.name, path)
    sh(cmd)


def save_experiment(filename, expt):
    file_write_safe(filename, text_format.MessageToString(expt))


def load_experiment(filename):
    fh = open(filename, 'rb')
    expt = Experiment()
    text_format.Merge(fh.read(), expt)
    fh.close()
    return expt


def job_output_file(job):
    return os.path.join(job.expt_dir, 'output', '%08d.out' % (job.id))


def job_file_for(job):
    '''Get the path to the job file corresponding to a job object.'''
    return os.path.join(job.expt_dir, 'jobs', '%08d.pb' % (job.id))


def save_job(job):
    filename = job_file_for(job)
    file_write_safe(filename, job.SerializeToString())


def load_job(filename):
    fh = open(filename, 'rb')
    job = Job()
    job.ParseFromString(fh.read())
    fh.close()
    return job


########NEW FILE########
__FILENAME__ = Locker
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import sys
import time

def safe_delete(filename):
    cmd  = 'mv "%s" "%s.delete" && rm "%s.delete"' % (filename, filename,
                                                      filename)
    fail = os.system(cmd)
    return not fail

class Locker:

    def __init__(self):
        self.locks = {}

    def __del__(self):
        for filename in self.locks.keys():
            self.locks[filename] = 1
            self.unlock(filename)

    def lock(self, filename):
        if self.locks.has_key(filename):
            self.locks[filename] += 1
            return True
        else:
            cmd = 'ln -s /dev/null "%s.lock" 2> /dev/null' % (filename)
            fail = os.system(cmd)
            if not fail:
                self.locks[filename] = 1
            return not fail

    def unlock(self, filename):
        if not self.locks.has_key(filename):
            #sys.stderr.write("Trying to unlock not-locked file %s.\n" % (filename))
            return True
        if self.locks[filename] == 1:
            success = safe_delete('%s.lock' % (filename))
            if not success:
                sys.stderr.write("Could not unlock file: %s.\n" % (filename))
            del self.locks[filename]
            return success
        else:
            self.locks[filename] -= 1
            return True

    def lock_wait(self, filename):
        while not self.lock(filename):
          time.sleep(0.01)


########NEW FILE########
__FILENAME__ = main
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import optparse
import tempfile
import datetime
import multiprocessing
import importlib
import time
import imp
import os
import sys
import re
import signal
import socket

try: import simplejson as json
except ImportError: import json


# TODO: this shouldn't be necessary when the project is installed like a normal
# python lib.  For now though, this lets you symlink to supermint from your path and run it
# from anywhere.
sys.path.append(os.path.realpath(__file__))

from ExperimentGrid  import *
from helpers         import *
from runner          import job_runner

# Use a global for the web process so we can kill it cleanly on exit
web_proc = None

# There are two things going on here.  There are "experiments", which are
# large-scale things that live in a directory and in this case correspond
# to the task of minimizing a complicated function.  These experiments
# contain "jobs" which are individual function evaluations.  The set of
# all possible jobs, regardless of whether they have been run or not, is
# the "grid".  This grid is managed by an instance of the class
# ExperimentGrid.
#
# The spearmint.py script can run in two modes, which reflect experiments
# vs jobs.  When run with the --run-job argument, it will try to run a
# single job.  This is not meant to be run by hand, but is intended to be
# run by a job queueing system.  Without this argument, it runs in its main
# controller mode, which determines the jobs that should be executed and
# submits them to the queueing system.


def parse_args():
    parser = optparse.OptionParser(usage="\n\tspearmint [options] <experiment/config.pb>")

    parser.add_option("--max-concurrent", dest="max_concurrent",
                      help="Maximum number of concurrent jobs.",
                      type="int", default=1)
    parser.add_option("--max-finished-jobs", dest="max_finished_jobs",
                      type="int", default=10000)
    parser.add_option("--method", dest="chooser_module",
                      help="Method for choosing experiments [SequentialChooser, RandomChooser, GPEIOptChooser, GPEIOptChooser, GPEIperSecChooser, GPEIChooser]",
                      type="string", default="GPEIOptChooser")
    parser.add_option("--driver", dest="driver",
                      help="Runtime driver for jobs (local, or sge)",
                      type="string", default="local")
    parser.add_option("--method-args", dest="chooser_args",
                      help="Arguments to pass to chooser module.",
                      type="string", default="")
    parser.add_option("--grid-size", dest="grid_size",
                      help="Number of experiments in initial grid.",
                      type="int", default=20000)
    parser.add_option("--grid-seed", dest="grid_seed",
                      help="The seed used to initialize initial grid.",
                      type="int", default=1)
    parser.add_option("--run-job", dest="job",
                      help="Run a job in wrapper mode.",
                      type="string", default="")
    parser.add_option("--polling-time", dest="polling_time",
                      help="The time in-between successive polls for results.",
                      type="float", default=3.0)
    parser.add_option("-w", "--web-status", action="store_true",
                      help="Serve an experiment status web page.",
                      dest="web_status")
    parser.add_option("--port",
                      help="Specify a port to use for the status web interface.",
                      dest="web_status_port", type="int", default=0)
    parser.add_option("-v", "--verbose", action="store_true",
                      help="Print verbose debug output.")

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_help()
        sys.exit(0)

    return options, args


def get_available_port(portnum):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', portnum))
    port = sock.getsockname()[1]
    sock.close()
    return port


def start_web_view(options, experiment_config, chooser):
    '''Start the web view in a separate process.'''

    from spearmint.web.app import app    
    port = get_available_port(options.web_status_port)
    print "Using port: " + str(port)
    app.set_experiment_config(experiment_config)
    app.set_chooser(options.chooser_module,chooser)
    debug = (options.verbose == True)
    start_web_app = lambda: app.run(debug=debug, port=port)
    proc = multiprocessing.Process(target=start_web_app)
    proc.start()

    return proc


def main():
    (options, args) = parse_args()

    if options.job:
        job_runner(load_job(options.job))
        exit(0)

    experiment_config = args[0]
    expt_dir  = os.path.dirname(os.path.realpath(experiment_config))
    log("Using experiment configuration: " + experiment_config)
    log("experiment dir: " + expt_dir)

    if not os.path.exists(expt_dir):
        log("Cannot find experiment directory '%s'. "
            "Aborting." % (expt_dir))
        sys.exit(-1)

    check_experiment_dirs(expt_dir)

    # Load up the chooser module.
    module  = importlib.import_module('chooser.' + options.chooser_module)
    chooser = module.init(expt_dir, options.chooser_args)

    if options.web_status:
        web_proc = start_web_view(options, experiment_config, chooser)

    # Load up the job execution driver.
    module = importlib.import_module('driver.' + options.driver)
    driver = module.init()

    # Loop until we run out of jobs.
    while attempt_dispatch(experiment_config, expt_dir, chooser, driver, options):
        # This is polling frequency. A higher frequency means that the algorithm
        # picks up results more quickly after they finish, but also significantly
        # increases overhead.
        time.sleep(options.polling_time)


# TODO:
#  * move check_pending_jobs out of ExperimentGrid, and implement two simple
#  driver classes to handle local execution and SGE execution.
#  * take cmdline engine arg into account, and submit job accordingly

def attempt_dispatch(expt_config, expt_dir, chooser, driver, options):
    log("\n" + "-" * 40)
    expt = load_experiment(expt_config)

    # Build the experiment grid.
    expt_grid = ExperimentGrid(expt_dir,
                               expt.variable,
                               options.grid_size,
                               options.grid_seed)

    # Print out the current best function value.
    best_val, best_job = expt_grid.get_best()
    if best_job >= 0:
        log("Current best: %f (job %d)" % (best_val, best_job))
    else:
        log("Current best: No results returned yet.")

    # Gets you everything - NaN for unknown values & durations.
    grid, values, durations = expt_grid.get_grid()

    # Returns lists of indices.
    candidates = expt_grid.get_candidates()
    pending    = expt_grid.get_pending()
    complete   = expt_grid.get_complete()

    n_candidates = candidates.shape[0]
    n_pending    = pending.shape[0]
    n_complete   = complete.shape[0]
    log("%d candidates   %d pending   %d complete" %
        (n_candidates, n_pending, n_complete))

    # Verify that pending jobs are actually running, and add them back to the
    # candidate set if they have crashed or gotten lost.
    for job_id in pending:
        proc_id = expt_grid.get_proc_id(job_id)
        if not driver.is_proc_alive(job_id, proc_id):
            log("Set job %d back to pending status." % (job_id))
            expt_grid.set_candidate(job_id)

    # Track the time series of optimization.
    write_trace(expt_dir, best_val, best_job, n_candidates, n_pending, n_complete)

    # Print out the best job results
    write_best_job(expt_dir, best_val, best_job, expt_grid)

    if n_complete >= options.max_finished_jobs:
        log("Maximum number of finished jobs (%d) reached."
                         "Exiting" % options.max_finished_jobs)
        return False

    if n_candidates == 0:
        log("There are no candidates left.  Exiting.")
        return False

    if n_pending >= options.max_concurrent:
        log("Maximum number of jobs (%d) pending." % (options.max_concurrent))
        return True

    else:

        # start a bunch of candidate jobs if possible
        #to_start = min(options.max_concurrent - n_pending, n_candidates)
        #log("Trying to start %d jobs" % (to_start))
        #for i in xrange(to_start):

        # Ask the chooser to pick the next candidate
        log("Choosing next candidate... ")
        job_id = chooser.next(grid, values, durations, candidates, pending, complete)

        # If the job_id is a tuple, then the chooser picked a new job.
        # We have to add this to our grid
        if isinstance(job_id, tuple):
            (job_id, candidate) = job_id
            job_id = expt_grid.add_to_grid(candidate)

        log("selected job %d from the grid." % (job_id))

        # Convert this back into an interpretable job and add metadata.
        job = Job()
        job.id        = job_id
        job.expt_dir  = expt_dir
        job.name      = expt.name
        job.language  = expt.language
        job.status    = 'submitted'
        job.submit_t  = int(time.time())
        job.param.extend(expt_grid.get_params(job_id))

        save_job(job)
        pid = driver.submit_job(job)
        if pid != None:
            log("submitted - pid = %d" % (pid))
            expt_grid.set_submitted(job_id, pid)
        else:
            log("Failed to submit job!")
            log("Deleting job file.")
            os.unlink(job_file_for(job))

    return True


def write_trace(expt_dir, best_val, best_job,
                n_candidates, n_pending, n_complete):
    '''Append current experiment state to trace file.'''
    trace_fh = open(os.path.join(expt_dir, 'trace.csv'), 'a')
    trace_fh.write("%d,%f,%d,%d,%d,%d\n"
                   % (time.time(), best_val, best_job,
                      n_candidates, n_pending, n_complete))
    trace_fh.close()


def write_best_job(expt_dir, best_val, best_job, expt_grid):
    '''Write out the best_job_and_result.txt file containing the top results.'''

    best_job_fh = open(os.path.join(expt_dir, 'best_job_and_result.txt'), 'w')
    best_job_fh.write("Best result: %f\nJob-id: %d\nParameters: \n" %
                      (best_val, best_job))
    for best_params in expt_grid.get_params(best_job):
        best_job_fh.write(str(best_params))
    best_job_fh.close()


def check_experiment_dirs(expt_dir):
    '''Make output and jobs sub directories.'''

    output_subdir = os.path.join(expt_dir, 'output')
    check_dir(output_subdir)

    job_subdir = os.path.join(expt_dir, 'jobs')
    check_dir(job_subdir)

# Cleanup locks and processes on ctl-c
def sigint_handler(signal, frame):
    if web_proc:
        print "closing web server...",
        web_proc.terminate()
        print "done"
    sys.exit(0)


if __name__=='__main__':
    print "setting up signal handler..."
    signal.signal(signal.SIGINT, sigint_handler)
    main()


########NEW FILE########
__FILENAME__ = runner
import sys
import os
import traceback

from spearmint_pb2   import *
from ExperimentGrid  import *
from helpers         import *


# System dependent modules
DEFAULT_MODULES = [ 'packages/epd/7.1-2',
                    'packages/matlab/r2011b',
                    'mpi/openmpi/1.2.8/intel',
                    'libraries/mkl/10.0',
                    'packages/cuda/4.0',
                    ]

MCR_LOCATION = "/home/matlab/v715" # hack


def job_runner(job):
    '''This fn runs in a new process.  Now we are going to do a little
    bookkeeping and then spin off the actual job that does whatever it is we're
    trying to achieve.'''

    redirect_output(job_output_file(job))
    log("Running in wrapper mode for '%s'\n" % (job.id))

    ExperimentGrid.job_running(job.expt_dir, job.id)

    # Update metadata and save the job file, which will be read by the job wrappers.
    job.start_t = int(time.time())
    job.status  = 'running'
    save_job(job)

    success    = False
    start_time = time.time()

    try:
        if job.language == MATLAB:   run_matlab_job(job)
        elif job.language == PYTHON: run_python_job(job)
        elif job.language == SHELL:  run_torch_job(job)
        elif job.language == MCR:    run_mcr_job(job)
        else:
            raise Exception("That function type has not been implemented.")

        success = True
    except:
        log("-" * 40)
        log("Problem running the job:")
        log(sys.exc_info())
        log(traceback.print_exc(limit=1000))
        log("-" * 40)

    end_time = time.time()
    duration = end_time - start_time

    # The job output is written back to the job file, so we read it back in to
    # get the results.
    job_file = job_file_for(job)
    job      = load_job(job_file)

    log("Job file reloaded.")

    if not job.HasField("value"):
        log("Could not find value in output file.")
        success = False

    if success:
        log("Completed successfully in %0.2f seconds. [%f]"
                         % (duration, job.value))

        # Update the status for this job.
        ExperimentGrid.job_complete(job.expt_dir, job.id,
                                    job.value, duration)
        job.status = 'complete'
    else:
        log("Job failed in %0.2f seconds." % (duration))

        # Update the experiment status for this job.
        ExperimentGrid.job_broken(job.expt_dir, job.id)
        job.status = 'broken'

    job.end_t    = int(time.time())
    job.duration = duration

    save_job(job)


def run_matlab_job(job):
    '''Run it as a Matlab function.'''

    log("Running matlab job.")

    job_file      = job_file_for(job)
    function_call = "matlab_wrapper('%s'),quit;" % (job_file)
    matlab_cmd    = ('matlab -nosplash -nodesktop -r "%s"' %
                     (function_call))
    log(matlab_cmd)
    sh(matlab_cmd)


# TODO: change this function to be more flexible when running python jobs
# regarding the python path, experiment directory, etc...
def run_python_job(job):
    '''Run a Python function.'''

    log("Running python job.\n")

    # Add experiment directory to the system path.
    sys.path.append(os.path.realpath(job.expt_dir))

    # Convert the PB object into useful parameters.
    params = {}
    for param in job.param:
        dbl_vals = param.dbl_val._values
        int_vals = param.int_val._values
        str_vals = param.str_val._values

        if len(dbl_vals) > 0:
            params[param.name] = np.array(dbl_vals)
        elif len(int_vals) > 0:
            params[param.name] = np.array(int_vals, dtype=int)
        elif len(str_vals) > 0:
            params[param.name] = str_vals
        else:
            raise Exception("Unknown parameter type.")

    # Load up this module and run
    module  = __import__(job.name)
    result = module.main(job.id, params)

    log("Got result %f\n" % (result))

    # Store the result.
    job.value = result
    save_job(job)


def run_torch_job(job):
    '''Run a torch based job.'''

    params = {}
    for param in job.param:
        dbl_vals = param.dbl_val._values
        int_vals = param.int_val._values
        str_vals = param.str_val._values

        if len(dbl_vals) > 0:
            params[param.name] = dbl_vals
        elif len(int_vals) > 0:
            params[param.name] = int_vals
        elif len(str_vals) > 0:
            params[param.name] = str_vals
        else:
            raise Exception("Unknown parameter type.")

    #TODO: this passes args correctly for experiment utils, but we need to
    # figure out how to get the result back out when the experiment completes.

    param_str = ""
    for pname, pval in params.iteritems():
        if len(pval) == 1:
            pval = str(pval[0])
        else:
            pval = ','.join([str(v) for v in pval])

        param_str += "-" + pname + " " + pval + " "

    cmd = "./%s %s" % (job.name, param_str)
    log("Executing command: %s\n" % (cmd))
    sh(cmd)


def run_shell_job(job):
    '''Run a shell based job.'''

    log("Running shell job.\n")

    # Change into the directory.
    os.chdir(job.expt_dir)

    cmd      = './%s %s' % (job.name, job_file_for(job))
    log("Executing command '%s'\n" % (cmd))

    sh(cmd)


def run_mcr_job(job):
    '''Run a compiled Matlab job.'''

    log("Running a compiled Matlab job.\n")

    # Change into the directory.
    os.chdir(job.expt_dir)

    if os.environ.has_key('MATLAB'):
        mcr_loc = os.environ['MATLAB']
    else:
        mcr_loc = MCR_LOCATION

    cmd = './run_%s.sh %s %s' % (job.name, mcr_loc, job_file_for(job))
    log("Executing command '%s'\n" % (cmd))
    sh(cmd)



########NEW FILE########
__FILENAME__ = sobol_lib
import math
from numpy import *
def i4_bit_hi1 ( n ):
#*****************************************************************************80
#
## I4_BIT_HI1 returns the position of the high 1 bit base 2 in an integer.
#
#  Example:
#
#       N    Binary     BIT
#    ----    --------  ----
#       0           0     0
#       1           1     1
#       2          10     2
#       3          11     2 
#       4         100     3
#       5         101     3
#       6         110     3
#       7         111     3
#       8        1000     4
#       9        1001     4
#      10        1010     4
#      11        1011     4
#      12        1100     4
#      13        1101     4
#      14        1110     4
#      15        1111     4
#      16       10000     5
#      17       10001     5
#    1023  1111111111    10
#    1024 10000000000    11
#    1025 10000000001    11
#
#  	Licensing:
#
#    		This code is distributed under the GNU LGPL license.
#
#  	Modified:
#
#    		26 Nov 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#               Modified by Jasper Snoek to scale to 1111 dimensions
#
#  	Parameters:
#
#    		Input, integer N, the integer to be measured.
#    		N should be nonnegative.  If N is nonpositive, the value will always be 0.
#
#    		Output, integer BIT, the number of bits base 2.
#
	i = math.floor ( n )
	bit = 0
	while ( 1 ):
		if ( i <= 0 ):
			break
		bit += 1
		i = math.floor ( i / 2. )
	return bit
def i4_bit_lo0 ( n ):
#*****************************************************************************80
#
## I4_BIT_LO0 returns the position of the low 0 bit base 2 in an integer.
#
#  Example:
#
#       N    Binary     BIT
#    ----    --------  ----
#       0           0     1
#       1           1     2
#       2          10     1
#       3          11     3 
#       4         100     1
#       5         101     2
#       6         110     1
#       7         111     4
#       8        1000     1
#       9        1001     2
#      10        1010     1
#      11        1011     3
#      12        1100     1
#      13        1101     2
#      14        1110     1
#      15        1111     5
#      16       10000     1
#      17       10001     2
#    1023  1111111111     1
#    1024 10000000000     1
#    1025 10000000001     1
#
#  	Licensing:
#
#    This code is distributed under the GNU LGPL license.
#
#  	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#  Parameters:
#
#    		Input, integer N, the integer to be measured.
#    		N should be nonnegative.
#
#    		Output, integer BIT, the position of the low 1 bit.
#
	bit = 0
	i = math.floor ( n )
	while ( 1 ):
		bit = bit + 1
		i2 = math.floor ( i / 2. )
		if ( i == 2 * i2 ):
			break

		i = i2
	return bit
	
def i4_sobol_generate ( m, n, skip ):
#*****************************************************************************80
#
## I4_SOBOL_GENERATE generates a Sobol dataset.
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#  	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#	Parameters:
#
#		Input, integer M, the spatial dimension.
#
#		Input, integer N, the number of points to generate.
#
#		Input, integer SKIP, the number of initial points to skip.
#
#		Output, real R(M,N), the points.
#
	r=zeros((m,n))
	for j in xrange (1, n+1):
		seed = skip + j - 2
		[ r[0:m,j-1], seed ] = i4_sobol ( m, seed )
	return r
def i4_sobol ( dim_num, seed ):
#*****************************************************************************80
#
## I4_SOBOL generates a new quasirandom Sobol vector with each call.
#
#	Discussion:
#
#		The routine adapts the ideas of Antonov and Saleev.
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		26 February 2013
#
#	Author:
#
#		Original FORTRAN77 version by Bennett Fox.
#		MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#               PYTHON version modified by Jasper Snoek to scale (Joe & Kuo)
#
#	Reference:
#
#		Antonov, Saleev,
#		USSR Computational Mathematics and Mathematical Physics,
#		Volume 19, 1980, pages 252 - 256.
#
#		Paul Bratley, Bennett Fox,
#		Algorithm 659:
#		Implementing Sobol's Quasirandom Sequence Generator,
#		ACM Transactions on Mathematical Software,
#		Volume 14, Number 1, pages 88-100, 1988.
#
#		Bennett Fox,
#		Algorithm 647:
#		Implementation and Relative Efficiency of Quasirandom 
#		Sequence Generators,
#		ACM Transactions on Mathematical Software,
#		Volume 12, Number 4, pages 362-376, 1986.
#
#		Ilya Sobol,
#		USSR Computational Mathematics and Mathematical Physics,
#		Volume 16, pages 236-242, 1977.
#
#		Ilya Sobol, Levitan, 
#		The Production of Points Uniformly Distributed in a Multidimensional 
#		Cube (in Russian),
#		Preprint IPM Akad. Nauk SSSR, 
#		Number 40, Moscow 1976.
#
#               Stephen Joe, Frances Kuo,
#               Remark on Algorithm 659: Implementing Sobol's Quasirandom Sequence Generator,
#               ACM Transactions on Mathematical Software,
#               Volume 29, Number 1, March 2003, pages 49-57.
#
#	Parameters:
#
#		Input, integer DIM_NUM, the number of spatial dimensions.
#		DIM_NUM must satisfy 1 <= DIM_NUM <= 1111.
#
#		Input/output, integer SEED, the "seed" for the sequence.
#		This is essentially the index in the sequence of the quasirandom
#		value to be generated.	On output, SEED has been set to the
#		appropriate next value, usually simply SEED+1.
#		If SEED is less than 0 on input, it is treated as though it were 0.
#		An input value of 0 requests the first (0-th) element of the sequence.
#
#		Output, real QUASI(DIM_NUM), the next quasirandom vector.
#
	global atmost
	global dim_max
	global dim_num_save
	global initialized
	global lastq
	global log_max
	global maxcol
	global poly
	global recipd
	global seed_save
	global v

	if ( not 'initialized' in globals().keys() ):
		initialized = 0
		dim_num_save = -1

	if ( not initialized or dim_num != dim_num_save ):
		initialized = 1
		dim_max = 1111
		dim_num_save = -1
		log_max = 30
		seed_save = -1
#
#	Initialize (part of) V.
#
		v = zeros((dim_max,log_max))
		v[0,0] = 1
		v[1,0] = 1
		v[2,0] = 1
		v[3,0] = 1
		v[4,0] = 1
		v[5,0] = 1
		v[6,0] = 1
		v[7,0] = 1
		v[8,0] = 1
		v[9,0] = 1
		v[10,0] = 1
		v[11,0] = 1
		v[12,0] = 1
		v[13,0] = 1
		v[14,0] = 1
		v[15,0] = 1
		v[16,0] = 1
		v[17,0] = 1
		v[18,0] = 1
		v[19,0] = 1
		v[20,0] = 1
		v[21,0] = 1
		v[22,0] = 1
		v[23,0] = 1
		v[24,0] = 1
		v[25,0] = 1
		v[26,0] = 1
		v[27,0] = 1
		v[28,0] = 1
		v[29,0] = 1
		v[30,0] = 1
		v[31,0] = 1
		v[32,0] = 1
		v[33,0] = 1
		v[34,0] = 1
		v[35,0] = 1
		v[36,0] = 1
		v[37,0] = 1
		v[38,0] = 1
		v[39,0] = 1
		v[40,0] = 1
		v[41,0] = 1
		v[42,0] = 1
		v[43,0] = 1
		v[44,0] = 1
		v[45,0] = 1
		v[46,0] = 1
		v[47,0] = 1
		v[48,0] = 1
		v[49,0] = 1
		v[50,0] = 1
		v[51,0] = 1
		v[52,0] = 1
		v[53,0] = 1
		v[54,0] = 1
		v[55,0] = 1
		v[56,0] = 1
		v[57,0] = 1
		v[58,0] = 1
		v[59,0] = 1
		v[60,0] = 1
		v[61,0] = 1
		v[62,0] = 1
		v[63,0] = 1
		v[64,0] = 1
		v[65,0] = 1
		v[66,0] = 1
		v[67,0] = 1
		v[68,0] = 1
		v[69,0] = 1
		v[70,0] = 1
		v[71,0] = 1
		v[72,0] = 1
		v[73,0] = 1
		v[74,0] = 1
		v[75,0] = 1
		v[76,0] = 1
		v[77,0] = 1
		v[78,0] = 1
		v[79,0] = 1
		v[80,0] = 1
		v[81,0] = 1
		v[82,0] = 1
		v[83,0] = 1
		v[84,0] = 1
		v[85,0] = 1
		v[86,0] = 1
		v[87,0] = 1
		v[88,0] = 1
		v[89,0] = 1
		v[90,0] = 1
		v[91,0] = 1
		v[92,0] = 1
		v[93,0] = 1
		v[94,0] = 1
		v[95,0] = 1
		v[96,0] = 1
		v[97,0] = 1
		v[98,0] = 1
		v[99,0] = 1
		v[100,0] = 1
		v[101,0] = 1
		v[102,0] = 1
		v[103,0] = 1
		v[104,0] = 1
		v[105,0] = 1
		v[106,0] = 1
		v[107,0] = 1
		v[108,0] = 1
		v[109,0] = 1
		v[110,0] = 1
		v[111,0] = 1
		v[112,0] = 1
		v[113,0] = 1
		v[114,0] = 1
		v[115,0] = 1
		v[116,0] = 1
		v[117,0] = 1
		v[118,0] = 1
		v[119,0] = 1
		v[120,0] = 1
		v[121,0] = 1
		v[122,0] = 1
		v[123,0] = 1
		v[124,0] = 1
		v[125,0] = 1
		v[126,0] = 1
		v[127,0] = 1
		v[128,0] = 1
		v[129,0] = 1
		v[130,0] = 1
		v[131,0] = 1
		v[132,0] = 1
		v[133,0] = 1
		v[134,0] = 1
		v[135,0] = 1
		v[136,0] = 1
		v[137,0] = 1
		v[138,0] = 1
		v[139,0] = 1
		v[140,0] = 1
		v[141,0] = 1
		v[142,0] = 1
		v[143,0] = 1
		v[144,0] = 1
		v[145,0] = 1
		v[146,0] = 1
		v[147,0] = 1
		v[148,0] = 1
		v[149,0] = 1
		v[150,0] = 1
		v[151,0] = 1
		v[152,0] = 1
		v[153,0] = 1
		v[154,0] = 1
		v[155,0] = 1
		v[156,0] = 1
		v[157,0] = 1
		v[158,0] = 1
		v[159,0] = 1
		v[160,0] = 1
		v[161,0] = 1
		v[162,0] = 1
		v[163,0] = 1
		v[164,0] = 1
		v[165,0] = 1
		v[166,0] = 1
		v[167,0] = 1
		v[168,0] = 1
		v[169,0] = 1
		v[170,0] = 1
		v[171,0] = 1
		v[172,0] = 1
		v[173,0] = 1
		v[174,0] = 1
		v[175,0] = 1
		v[176,0] = 1
		v[177,0] = 1
		v[178,0] = 1
		v[179,0] = 1
		v[180,0] = 1
		v[181,0] = 1
		v[182,0] = 1
		v[183,0] = 1
		v[184,0] = 1
		v[185,0] = 1
		v[186,0] = 1
		v[187,0] = 1
		v[188,0] = 1
		v[189,0] = 1
		v[190,0] = 1
		v[191,0] = 1
		v[192,0] = 1
		v[193,0] = 1
		v[194,0] = 1
		v[195,0] = 1
		v[196,0] = 1
		v[197,0] = 1
		v[198,0] = 1
		v[199,0] = 1
		v[200,0] = 1
		v[201,0] = 1
		v[202,0] = 1
		v[203,0] = 1
		v[204,0] = 1
		v[205,0] = 1
		v[206,0] = 1
		v[207,0] = 1
		v[208,0] = 1
		v[209,0] = 1
		v[210,0] = 1
		v[211,0] = 1
		v[212,0] = 1
		v[213,0] = 1
		v[214,0] = 1
		v[215,0] = 1
		v[216,0] = 1
		v[217,0] = 1
		v[218,0] = 1
		v[219,0] = 1
		v[220,0] = 1
		v[221,0] = 1
		v[222,0] = 1
		v[223,0] = 1
		v[224,0] = 1
		v[225,0] = 1
		v[226,0] = 1
		v[227,0] = 1
		v[228,0] = 1
		v[229,0] = 1
		v[230,0] = 1
		v[231,0] = 1
		v[232,0] = 1
		v[233,0] = 1
		v[234,0] = 1
		v[235,0] = 1
		v[236,0] = 1
		v[237,0] = 1
		v[238,0] = 1
		v[239,0] = 1
		v[240,0] = 1
		v[241,0] = 1
		v[242,0] = 1
		v[243,0] = 1
		v[244,0] = 1
		v[245,0] = 1
		v[246,0] = 1
		v[247,0] = 1
		v[248,0] = 1
		v[249,0] = 1
		v[250,0] = 1
		v[251,0] = 1
		v[252,0] = 1
		v[253,0] = 1
		v[254,0] = 1
		v[255,0] = 1
		v[256,0] = 1
		v[257,0] = 1
		v[258,0] = 1
		v[259,0] = 1
		v[260,0] = 1
		v[261,0] = 1
		v[262,0] = 1
		v[263,0] = 1
		v[264,0] = 1
		v[265,0] = 1
		v[266,0] = 1
		v[267,0] = 1
		v[268,0] = 1
		v[269,0] = 1
		v[270,0] = 1
		v[271,0] = 1
		v[272,0] = 1
		v[273,0] = 1
		v[274,0] = 1
		v[275,0] = 1
		v[276,0] = 1
		v[277,0] = 1
		v[278,0] = 1
		v[279,0] = 1
		v[280,0] = 1
		v[281,0] = 1
		v[282,0] = 1
		v[283,0] = 1
		v[284,0] = 1
		v[285,0] = 1
		v[286,0] = 1
		v[287,0] = 1
		v[288,0] = 1
		v[289,0] = 1
		v[290,0] = 1
		v[291,0] = 1
		v[292,0] = 1
		v[293,0] = 1
		v[294,0] = 1
		v[295,0] = 1
		v[296,0] = 1
		v[297,0] = 1
		v[298,0] = 1
		v[299,0] = 1
		v[300,0] = 1
		v[301,0] = 1
		v[302,0] = 1
		v[303,0] = 1
		v[304,0] = 1
		v[305,0] = 1
		v[306,0] = 1
		v[307,0] = 1
		v[308,0] = 1
		v[309,0] = 1
		v[310,0] = 1
		v[311,0] = 1
		v[312,0] = 1
		v[313,0] = 1
		v[314,0] = 1
		v[315,0] = 1
		v[316,0] = 1
		v[317,0] = 1
		v[318,0] = 1
		v[319,0] = 1
		v[320,0] = 1
		v[321,0] = 1
		v[322,0] = 1
		v[323,0] = 1
		v[324,0] = 1
		v[325,0] = 1
		v[326,0] = 1
		v[327,0] = 1
		v[328,0] = 1
		v[329,0] = 1
		v[330,0] = 1
		v[331,0] = 1
		v[332,0] = 1
		v[333,0] = 1
		v[334,0] = 1
		v[335,0] = 1
		v[336,0] = 1
		v[337,0] = 1
		v[338,0] = 1
		v[339,0] = 1
		v[340,0] = 1
		v[341,0] = 1
		v[342,0] = 1
		v[343,0] = 1
		v[344,0] = 1
		v[345,0] = 1
		v[346,0] = 1
		v[347,0] = 1
		v[348,0] = 1
		v[349,0] = 1
		v[350,0] = 1
		v[351,0] = 1
		v[352,0] = 1
		v[353,0] = 1
		v[354,0] = 1
		v[355,0] = 1
		v[356,0] = 1
		v[357,0] = 1
		v[358,0] = 1
		v[359,0] = 1
		v[360,0] = 1
		v[361,0] = 1
		v[362,0] = 1
		v[363,0] = 1
		v[364,0] = 1
		v[365,0] = 1
		v[366,0] = 1
		v[367,0] = 1
		v[368,0] = 1
		v[369,0] = 1
		v[370,0] = 1
		v[371,0] = 1
		v[372,0] = 1
		v[373,0] = 1
		v[374,0] = 1
		v[375,0] = 1
		v[376,0] = 1
		v[377,0] = 1
		v[378,0] = 1
		v[379,0] = 1
		v[380,0] = 1
		v[381,0] = 1
		v[382,0] = 1
		v[383,0] = 1
		v[384,0] = 1
		v[385,0] = 1
		v[386,0] = 1
		v[387,0] = 1
		v[388,0] = 1
		v[389,0] = 1
		v[390,0] = 1
		v[391,0] = 1
		v[392,0] = 1
		v[393,0] = 1
		v[394,0] = 1
		v[395,0] = 1
		v[396,0] = 1
		v[397,0] = 1
		v[398,0] = 1
		v[399,0] = 1
		v[400,0] = 1
		v[401,0] = 1
		v[402,0] = 1
		v[403,0] = 1
		v[404,0] = 1
		v[405,0] = 1
		v[406,0] = 1
		v[407,0] = 1
		v[408,0] = 1
		v[409,0] = 1
		v[410,0] = 1
		v[411,0] = 1
		v[412,0] = 1
		v[413,0] = 1
		v[414,0] = 1
		v[415,0] = 1
		v[416,0] = 1
		v[417,0] = 1
		v[418,0] = 1
		v[419,0] = 1
		v[420,0] = 1
		v[421,0] = 1
		v[422,0] = 1
		v[423,0] = 1
		v[424,0] = 1
		v[425,0] = 1
		v[426,0] = 1
		v[427,0] = 1
		v[428,0] = 1
		v[429,0] = 1
		v[430,0] = 1
		v[431,0] = 1
		v[432,0] = 1
		v[433,0] = 1
		v[434,0] = 1
		v[435,0] = 1
		v[436,0] = 1
		v[437,0] = 1
		v[438,0] = 1
		v[439,0] = 1
		v[440,0] = 1
		v[441,0] = 1
		v[442,0] = 1
		v[443,0] = 1
		v[444,0] = 1
		v[445,0] = 1
		v[446,0] = 1
		v[447,0] = 1
		v[448,0] = 1
		v[449,0] = 1
		v[450,0] = 1
		v[451,0] = 1
		v[452,0] = 1
		v[453,0] = 1
		v[454,0] = 1
		v[455,0] = 1
		v[456,0] = 1
		v[457,0] = 1
		v[458,0] = 1
		v[459,0] = 1
		v[460,0] = 1
		v[461,0] = 1
		v[462,0] = 1
		v[463,0] = 1
		v[464,0] = 1
		v[465,0] = 1
		v[466,0] = 1
		v[467,0] = 1
		v[468,0] = 1
		v[469,0] = 1
		v[470,0] = 1
		v[471,0] = 1
		v[472,0] = 1
		v[473,0] = 1
		v[474,0] = 1
		v[475,0] = 1
		v[476,0] = 1
		v[477,0] = 1
		v[478,0] = 1
		v[479,0] = 1
		v[480,0] = 1
		v[481,0] = 1
		v[482,0] = 1
		v[483,0] = 1
		v[484,0] = 1
		v[485,0] = 1
		v[486,0] = 1
		v[487,0] = 1
		v[488,0] = 1
		v[489,0] = 1
		v[490,0] = 1
		v[491,0] = 1
		v[492,0] = 1
		v[493,0] = 1
		v[494,0] = 1
		v[495,0] = 1
		v[496,0] = 1
		v[497,0] = 1
		v[498,0] = 1
		v[499,0] = 1
		v[500,0] = 1
		v[501,0] = 1
		v[502,0] = 1
		v[503,0] = 1
		v[504,0] = 1
		v[505,0] = 1
		v[506,0] = 1
		v[507,0] = 1
		v[508,0] = 1
		v[509,0] = 1
		v[510,0] = 1
		v[511,0] = 1
		v[512,0] = 1
		v[513,0] = 1
		v[514,0] = 1
		v[515,0] = 1
		v[516,0] = 1
		v[517,0] = 1
		v[518,0] = 1
		v[519,0] = 1
		v[520,0] = 1
		v[521,0] = 1
		v[522,0] = 1
		v[523,0] = 1
		v[524,0] = 1
		v[525,0] = 1
		v[526,0] = 1
		v[527,0] = 1
		v[528,0] = 1
		v[529,0] = 1
		v[530,0] = 1
		v[531,0] = 1
		v[532,0] = 1
		v[533,0] = 1
		v[534,0] = 1
		v[535,0] = 1
		v[536,0] = 1
		v[537,0] = 1
		v[538,0] = 1
		v[539,0] = 1
		v[540,0] = 1
		v[541,0] = 1
		v[542,0] = 1
		v[543,0] = 1
		v[544,0] = 1
		v[545,0] = 1
		v[546,0] = 1
		v[547,0] = 1
		v[548,0] = 1
		v[549,0] = 1
		v[550,0] = 1
		v[551,0] = 1
		v[552,0] = 1
		v[553,0] = 1
		v[554,0] = 1
		v[555,0] = 1
		v[556,0] = 1
		v[557,0] = 1
		v[558,0] = 1
		v[559,0] = 1
		v[560,0] = 1
		v[561,0] = 1
		v[562,0] = 1
		v[563,0] = 1
		v[564,0] = 1
		v[565,0] = 1
		v[566,0] = 1
		v[567,0] = 1
		v[568,0] = 1
		v[569,0] = 1
		v[570,0] = 1
		v[571,0] = 1
		v[572,0] = 1
		v[573,0] = 1
		v[574,0] = 1
		v[575,0] = 1
		v[576,0] = 1
		v[577,0] = 1
		v[578,0] = 1
		v[579,0] = 1
		v[580,0] = 1
		v[581,0] = 1
		v[582,0] = 1
		v[583,0] = 1
		v[584,0] = 1
		v[585,0] = 1
		v[586,0] = 1
		v[587,0] = 1
		v[588,0] = 1
		v[589,0] = 1
		v[590,0] = 1
		v[591,0] = 1
		v[592,0] = 1
		v[593,0] = 1
		v[594,0] = 1
		v[595,0] = 1
		v[596,0] = 1
		v[597,0] = 1
		v[598,0] = 1
		v[599,0] = 1
		v[600,0] = 1
		v[601,0] = 1
		v[602,0] = 1
		v[603,0] = 1
		v[604,0] = 1
		v[605,0] = 1
		v[606,0] = 1
		v[607,0] = 1
		v[608,0] = 1
		v[609,0] = 1
		v[610,0] = 1
		v[611,0] = 1
		v[612,0] = 1
		v[613,0] = 1
		v[614,0] = 1
		v[615,0] = 1
		v[616,0] = 1
		v[617,0] = 1
		v[618,0] = 1
		v[619,0] = 1
		v[620,0] = 1
		v[621,0] = 1
		v[622,0] = 1
		v[623,0] = 1
		v[624,0] = 1
		v[625,0] = 1
		v[626,0] = 1
		v[627,0] = 1
		v[628,0] = 1
		v[629,0] = 1
		v[630,0] = 1
		v[631,0] = 1
		v[632,0] = 1
		v[633,0] = 1
		v[634,0] = 1
		v[635,0] = 1
		v[636,0] = 1
		v[637,0] = 1
		v[638,0] = 1
		v[639,0] = 1
		v[640,0] = 1
		v[641,0] = 1
		v[642,0] = 1
		v[643,0] = 1
		v[644,0] = 1
		v[645,0] = 1
		v[646,0] = 1
		v[647,0] = 1
		v[648,0] = 1
		v[649,0] = 1
		v[650,0] = 1
		v[651,0] = 1
		v[652,0] = 1
		v[653,0] = 1
		v[654,0] = 1
		v[655,0] = 1
		v[656,0] = 1
		v[657,0] = 1
		v[658,0] = 1
		v[659,0] = 1
		v[660,0] = 1
		v[661,0] = 1
		v[662,0] = 1
		v[663,0] = 1
		v[664,0] = 1
		v[665,0] = 1
		v[666,0] = 1
		v[667,0] = 1
		v[668,0] = 1
		v[669,0] = 1
		v[670,0] = 1
		v[671,0] = 1
		v[672,0] = 1
		v[673,0] = 1
		v[674,0] = 1
		v[675,0] = 1
		v[676,0] = 1
		v[677,0] = 1
		v[678,0] = 1
		v[679,0] = 1
		v[680,0] = 1
		v[681,0] = 1
		v[682,0] = 1
		v[683,0] = 1
		v[684,0] = 1
		v[685,0] = 1
		v[686,0] = 1
		v[687,0] = 1
		v[688,0] = 1
		v[689,0] = 1
		v[690,0] = 1
		v[691,0] = 1
		v[692,0] = 1
		v[693,0] = 1
		v[694,0] = 1
		v[695,0] = 1
		v[696,0] = 1
		v[697,0] = 1
		v[698,0] = 1
		v[699,0] = 1
		v[700,0] = 1
		v[701,0] = 1
		v[702,0] = 1
		v[703,0] = 1
		v[704,0] = 1
		v[705,0] = 1
		v[706,0] = 1
		v[707,0] = 1
		v[708,0] = 1
		v[709,0] = 1
		v[710,0] = 1
		v[711,0] = 1
		v[712,0] = 1
		v[713,0] = 1
		v[714,0] = 1
		v[715,0] = 1
		v[716,0] = 1
		v[717,0] = 1
		v[718,0] = 1
		v[719,0] = 1
		v[720,0] = 1
		v[721,0] = 1
		v[722,0] = 1
		v[723,0] = 1
		v[724,0] = 1
		v[725,0] = 1
		v[726,0] = 1
		v[727,0] = 1
		v[728,0] = 1
		v[729,0] = 1
		v[730,0] = 1
		v[731,0] = 1
		v[732,0] = 1
		v[733,0] = 1
		v[734,0] = 1
		v[735,0] = 1
		v[736,0] = 1
		v[737,0] = 1
		v[738,0] = 1
		v[739,0] = 1
		v[740,0] = 1
		v[741,0] = 1
		v[742,0] = 1
		v[743,0] = 1
		v[744,0] = 1
		v[745,0] = 1
		v[746,0] = 1
		v[747,0] = 1
		v[748,0] = 1
		v[749,0] = 1
		v[750,0] = 1
		v[751,0] = 1
		v[752,0] = 1
		v[753,0] = 1
		v[754,0] = 1
		v[755,0] = 1
		v[756,0] = 1
		v[757,0] = 1
		v[758,0] = 1
		v[759,0] = 1
		v[760,0] = 1
		v[761,0] = 1
		v[762,0] = 1
		v[763,0] = 1
		v[764,0] = 1
		v[765,0] = 1
		v[766,0] = 1
		v[767,0] = 1
		v[768,0] = 1
		v[769,0] = 1
		v[770,0] = 1
		v[771,0] = 1
		v[772,0] = 1
		v[773,0] = 1
		v[774,0] = 1
		v[775,0] = 1
		v[776,0] = 1
		v[777,0] = 1
		v[778,0] = 1
		v[779,0] = 1
		v[780,0] = 1
		v[781,0] = 1
		v[782,0] = 1
		v[783,0] = 1
		v[784,0] = 1
		v[785,0] = 1
		v[786,0] = 1
		v[787,0] = 1
		v[788,0] = 1
		v[789,0] = 1
		v[790,0] = 1
		v[791,0] = 1
		v[792,0] = 1
		v[793,0] = 1
		v[794,0] = 1
		v[795,0] = 1
		v[796,0] = 1
		v[797,0] = 1
		v[798,0] = 1
		v[799,0] = 1
		v[800,0] = 1
		v[801,0] = 1
		v[802,0] = 1
		v[803,0] = 1
		v[804,0] = 1
		v[805,0] = 1
		v[806,0] = 1
		v[807,0] = 1
		v[808,0] = 1
		v[809,0] = 1
		v[810,0] = 1
		v[811,0] = 1
		v[812,0] = 1
		v[813,0] = 1
		v[814,0] = 1
		v[815,0] = 1
		v[816,0] = 1
		v[817,0] = 1
		v[818,0] = 1
		v[819,0] = 1
		v[820,0] = 1
		v[821,0] = 1
		v[822,0] = 1
		v[823,0] = 1
		v[824,0] = 1
		v[825,0] = 1
		v[826,0] = 1
		v[827,0] = 1
		v[828,0] = 1
		v[829,0] = 1
		v[830,0] = 1
		v[831,0] = 1
		v[832,0] = 1
		v[833,0] = 1
		v[834,0] = 1
		v[835,0] = 1
		v[836,0] = 1
		v[837,0] = 1
		v[838,0] = 1
		v[839,0] = 1
		v[840,0] = 1
		v[841,0] = 1
		v[842,0] = 1
		v[843,0] = 1
		v[844,0] = 1
		v[845,0] = 1
		v[846,0] = 1
		v[847,0] = 1
		v[848,0] = 1
		v[849,0] = 1
		v[850,0] = 1
		v[851,0] = 1
		v[852,0] = 1
		v[853,0] = 1
		v[854,0] = 1
		v[855,0] = 1
		v[856,0] = 1
		v[857,0] = 1
		v[858,0] = 1
		v[859,0] = 1
		v[860,0] = 1
		v[861,0] = 1
		v[862,0] = 1
		v[863,0] = 1
		v[864,0] = 1
		v[865,0] = 1
		v[866,0] = 1
		v[867,0] = 1
		v[868,0] = 1
		v[869,0] = 1
		v[870,0] = 1
		v[871,0] = 1
		v[872,0] = 1
		v[873,0] = 1
		v[874,0] = 1
		v[875,0] = 1
		v[876,0] = 1
		v[877,0] = 1
		v[878,0] = 1
		v[879,0] = 1
		v[880,0] = 1
		v[881,0] = 1
		v[882,0] = 1
		v[883,0] = 1
		v[884,0] = 1
		v[885,0] = 1
		v[886,0] = 1
		v[887,0] = 1
		v[888,0] = 1
		v[889,0] = 1
		v[890,0] = 1
		v[891,0] = 1
		v[892,0] = 1
		v[893,0] = 1
		v[894,0] = 1
		v[895,0] = 1
		v[896,0] = 1
		v[897,0] = 1
		v[898,0] = 1
		v[899,0] = 1
		v[900,0] = 1
		v[901,0] = 1
		v[902,0] = 1
		v[903,0] = 1
		v[904,0] = 1
		v[905,0] = 1
		v[906,0] = 1
		v[907,0] = 1
		v[908,0] = 1
		v[909,0] = 1
		v[910,0] = 1
		v[911,0] = 1
		v[912,0] = 1
		v[913,0] = 1
		v[914,0] = 1
		v[915,0] = 1
		v[916,0] = 1
		v[917,0] = 1
		v[918,0] = 1
		v[919,0] = 1
		v[920,0] = 1
		v[921,0] = 1
		v[922,0] = 1
		v[923,0] = 1
		v[924,0] = 1
		v[925,0] = 1
		v[926,0] = 1
		v[927,0] = 1
		v[928,0] = 1
		v[929,0] = 1
		v[930,0] = 1
		v[931,0] = 1
		v[932,0] = 1
		v[933,0] = 1
		v[934,0] = 1
		v[935,0] = 1
		v[936,0] = 1
		v[937,0] = 1
		v[938,0] = 1
		v[939,0] = 1
		v[940,0] = 1
		v[941,0] = 1
		v[942,0] = 1
		v[943,0] = 1
		v[944,0] = 1
		v[945,0] = 1
		v[946,0] = 1
		v[947,0] = 1
		v[948,0] = 1
		v[949,0] = 1
		v[950,0] = 1
		v[951,0] = 1
		v[952,0] = 1
		v[953,0] = 1
		v[954,0] = 1
		v[955,0] = 1
		v[956,0] = 1
		v[957,0] = 1
		v[958,0] = 1
		v[959,0] = 1
		v[960,0] = 1
		v[961,0] = 1
		v[962,0] = 1
		v[963,0] = 1
		v[964,0] = 1
		v[965,0] = 1
		v[966,0] = 1
		v[967,0] = 1
		v[968,0] = 1
		v[969,0] = 1
		v[970,0] = 1
		v[971,0] = 1
		v[972,0] = 1
		v[973,0] = 1
		v[974,0] = 1
		v[975,0] = 1
		v[976,0] = 1
		v[977,0] = 1
		v[978,0] = 1
		v[979,0] = 1
		v[980,0] = 1
		v[981,0] = 1
		v[982,0] = 1
		v[983,0] = 1
		v[984,0] = 1
		v[985,0] = 1
		v[986,0] = 1
		v[987,0] = 1
		v[988,0] = 1
		v[989,0] = 1
		v[990,0] = 1
		v[991,0] = 1
		v[992,0] = 1
		v[993,0] = 1
		v[994,0] = 1
		v[995,0] = 1
		v[996,0] = 1
		v[997,0] = 1
		v[998,0] = 1
		v[999,0] = 1
		v[1000,0] = 1
		v[1001,0] = 1
		v[1002,0] = 1
		v[1003,0] = 1
		v[1004,0] = 1
		v[1005,0] = 1
		v[1006,0] = 1
		v[1007,0] = 1
		v[1008,0] = 1
		v[1009,0] = 1
		v[1010,0] = 1
		v[1011,0] = 1
		v[1012,0] = 1
		v[1013,0] = 1
		v[1014,0] = 1
		v[1015,0] = 1
		v[1016,0] = 1
		v[1017,0] = 1
		v[1018,0] = 1
		v[1019,0] = 1
		v[1020,0] = 1
		v[1021,0] = 1
		v[1022,0] = 1
		v[1023,0] = 1
		v[1024,0] = 1
		v[1025,0] = 1
		v[1026,0] = 1
		v[1027,0] = 1
		v[1028,0] = 1
		v[1029,0] = 1
		v[1030,0] = 1
		v[1031,0] = 1
		v[1032,0] = 1
		v[1033,0] = 1
		v[1034,0] = 1
		v[1035,0] = 1
		v[1036,0] = 1
		v[1037,0] = 1
		v[1038,0] = 1
		v[1039,0] = 1
		v[1040,0] = 1
		v[1041,0] = 1
		v[1042,0] = 1
		v[1043,0] = 1
		v[1044,0] = 1
		v[1045,0] = 1
		v[1046,0] = 1
		v[1047,0] = 1
		v[1048,0] = 1
		v[1049,0] = 1
		v[1050,0] = 1
		v[1051,0] = 1
		v[1052,0] = 1
		v[1053,0] = 1
		v[1054,0] = 1
		v[1055,0] = 1
		v[1056,0] = 1
		v[1057,0] = 1
		v[1058,0] = 1
		v[1059,0] = 1
		v[1060,0] = 1
		v[1061,0] = 1
		v[1062,0] = 1
		v[1063,0] = 1
		v[1064,0] = 1
		v[1065,0] = 1
		v[1066,0] = 1
		v[1067,0] = 1
		v[1068,0] = 1
		v[1069,0] = 1
		v[1070,0] = 1
		v[1071,0] = 1
		v[1072,0] = 1
		v[1073,0] = 1
		v[1074,0] = 1
		v[1075,0] = 1
		v[1076,0] = 1
		v[1077,0] = 1
		v[1078,0] = 1
		v[1079,0] = 1
		v[1080,0] = 1
		v[1081,0] = 1
		v[1082,0] = 1
		v[1083,0] = 1
		v[1084,0] = 1
		v[1085,0] = 1
		v[1086,0] = 1
		v[1087,0] = 1
		v[1088,0] = 1
		v[1089,0] = 1
		v[1090,0] = 1
		v[1091,0] = 1
		v[1092,0] = 1
		v[1093,0] = 1
		v[1094,0] = 1
		v[1095,0] = 1
		v[1096,0] = 1
		v[1097,0] = 1
		v[1098,0] = 1
		v[1099,0] = 1
		v[1100,0] = 1
		v[1101,0] = 1
		v[1102,0] = 1
		v[1103,0] = 1
		v[1104,0] = 1
		v[1105,0] = 1
		v[1106,0] = 1
		v[1107,0] = 1
		v[1108,0] = 1
		v[1109,0] = 1
		v[1110,0] = 1

		v[2,1] = 1
		v[3,1] = 3
		v[4,1] = 1
		v[5,1] = 3
		v[6,1] = 1
		v[7,1] = 3
		v[8,1] = 3
		v[9,1] = 1
		v[10,1] = 3
		v[11,1] = 1
		v[12,1] = 3
		v[13,1] = 1
		v[14,1] = 3
		v[15,1] = 1
		v[16,1] = 1
		v[17,1] = 3
		v[18,1] = 1
		v[19,1] = 3
		v[20,1] = 1
		v[21,1] = 3
		v[22,1] = 1
		v[23,1] = 3
		v[24,1] = 3
		v[25,1] = 1
		v[26,1] = 1
		v[27,1] = 1
		v[28,1] = 3
		v[29,1] = 1
		v[30,1] = 3
		v[31,1] = 1
		v[32,1] = 3
		v[33,1] = 3
		v[34,1] = 1
		v[35,1] = 3
		v[36,1] = 1
		v[37,1] = 1
		v[38,1] = 1
		v[39,1] = 3
		v[40,1] = 1
		v[41,1] = 3
		v[42,1] = 1
		v[43,1] = 1
		v[44,1] = 1
		v[45,1] = 3
		v[46,1] = 3
		v[47,1] = 1
		v[48,1] = 3
		v[49,1] = 3
		v[50,1] = 1
		v[51,1] = 1
		v[52,1] = 3
		v[53,1] = 3
		v[54,1] = 1
		v[55,1] = 3
		v[56,1] = 3
		v[57,1] = 3
		v[58,1] = 1
		v[59,1] = 3
		v[60,1] = 1
		v[61,1] = 3
		v[62,1] = 1
		v[63,1] = 1
		v[64,1] = 3
		v[65,1] = 3
		v[66,1] = 1
		v[67,1] = 1
		v[68,1] = 1
		v[69,1] = 1
		v[70,1] = 3
		v[71,1] = 1
		v[72,1] = 1
		v[73,1] = 3
		v[74,1] = 1
		v[75,1] = 1
		v[76,1] = 1
		v[77,1] = 3
		v[78,1] = 3
		v[79,1] = 1
		v[80,1] = 3
		v[81,1] = 3
		v[82,1] = 1
		v[83,1] = 3
		v[84,1] = 3
		v[85,1] = 3
		v[86,1] = 1
		v[87,1] = 3
		v[88,1] = 3
		v[89,1] = 3
		v[90,1] = 1
		v[91,1] = 3
		v[92,1] = 3
		v[93,1] = 1
		v[94,1] = 3
		v[95,1] = 3
		v[96,1] = 3
		v[97,1] = 1
		v[98,1] = 3
		v[99,1] = 1
		v[100,1] = 3
		v[101,1] = 1
		v[102,1] = 1
		v[103,1] = 3
		v[104,1] = 3
		v[105,1] = 1
		v[106,1] = 3
		v[107,1] = 3
		v[108,1] = 1
		v[109,1] = 1
		v[110,1] = 1
		v[111,1] = 3
		v[112,1] = 3
		v[113,1] = 1
		v[114,1] = 3
		v[115,1] = 3
		v[116,1] = 1
		v[117,1] = 3
		v[118,1] = 1
		v[119,1] = 1
		v[120,1] = 3
		v[121,1] = 3
		v[122,1] = 3
		v[123,1] = 1
		v[124,1] = 1
		v[125,1] = 1
		v[126,1] = 3
		v[127,1] = 1
		v[128,1] = 1
		v[129,1] = 3
		v[130,1] = 1
		v[131,1] = 1
		v[132,1] = 3
		v[133,1] = 3
		v[134,1] = 1
		v[135,1] = 3
		v[136,1] = 1
		v[137,1] = 3
		v[138,1] = 3
		v[139,1] = 3
		v[140,1] = 3
		v[141,1] = 1
		v[142,1] = 1
		v[143,1] = 1
		v[144,1] = 3
		v[145,1] = 3
		v[146,1] = 1
		v[147,1] = 1
		v[148,1] = 3
		v[149,1] = 1
		v[150,1] = 1
		v[151,1] = 1
		v[152,1] = 1
		v[153,1] = 1
		v[154,1] = 1
		v[155,1] = 3
		v[156,1] = 1
		v[157,1] = 3
		v[158,1] = 1
		v[159,1] = 1
		v[160,1] = 1
		v[161,1] = 3
		v[162,1] = 1
		v[163,1] = 3
		v[164,1] = 1
		v[165,1] = 3
		v[166,1] = 3
		v[167,1] = 3
		v[168,1] = 1
		v[169,1] = 1
		v[170,1] = 3
		v[171,1] = 3
		v[172,1] = 1
		v[173,1] = 3
		v[174,1] = 1
		v[175,1] = 3
		v[176,1] = 1
		v[177,1] = 1
		v[178,1] = 3
		v[179,1] = 1
		v[180,1] = 3
		v[181,1] = 1
		v[182,1] = 3
		v[183,1] = 1
		v[184,1] = 3
		v[185,1] = 1
		v[186,1] = 1
		v[187,1] = 1
		v[188,1] = 3
		v[189,1] = 3
		v[190,1] = 1
		v[191,1] = 3
		v[192,1] = 3
		v[193,1] = 1
		v[194,1] = 3
		v[195,1] = 1
		v[196,1] = 1
		v[197,1] = 1
		v[198,1] = 3
		v[199,1] = 1
		v[200,1] = 3
		v[201,1] = 1
		v[202,1] = 1
		v[203,1] = 3
		v[204,1] = 1
		v[205,1] = 1
		v[206,1] = 3
		v[207,1] = 3
		v[208,1] = 1
		v[209,1] = 1
		v[210,1] = 3
		v[211,1] = 3
		v[212,1] = 3
		v[213,1] = 1
		v[214,1] = 3
		v[215,1] = 3
		v[216,1] = 3
		v[217,1] = 1
		v[218,1] = 3
		v[219,1] = 1
		v[220,1] = 3
		v[221,1] = 1
		v[222,1] = 1
		v[223,1] = 1
		v[224,1] = 3
		v[225,1] = 1
		v[226,1] = 1
		v[227,1] = 1
		v[228,1] = 3
		v[229,1] = 1
		v[230,1] = 1
		v[231,1] = 1
		v[232,1] = 1
		v[233,1] = 1
		v[234,1] = 3
		v[235,1] = 3
		v[236,1] = 3
		v[237,1] = 1
		v[238,1] = 1
		v[239,1] = 1
		v[240,1] = 1
		v[241,1] = 3
		v[242,1] = 3
		v[243,1] = 3
		v[244,1] = 1
		v[245,1] = 3
		v[246,1] = 3
		v[247,1] = 1
		v[248,1] = 1
		v[249,1] = 1
		v[250,1] = 1
		v[251,1] = 3
		v[252,1] = 1
		v[253,1] = 1
		v[254,1] = 3
		v[255,1] = 1
		v[256,1] = 3
		v[257,1] = 3
		v[258,1] = 1
		v[259,1] = 1
		v[260,1] = 3
		v[261,1] = 3
		v[262,1] = 1
		v[263,1] = 1
		v[264,1] = 1
		v[265,1] = 1
		v[266,1] = 3
		v[267,1] = 1
		v[268,1] = 3
		v[269,1] = 3
		v[270,1] = 1
		v[271,1] = 3
		v[272,1] = 3
		v[273,1] = 1
		v[274,1] = 1
		v[275,1] = 1
		v[276,1] = 3
		v[277,1] = 3
		v[278,1] = 3
		v[279,1] = 1
		v[280,1] = 3
		v[281,1] = 3
		v[282,1] = 1
		v[283,1] = 3
		v[284,1] = 3
		v[285,1] = 1
		v[286,1] = 3
		v[287,1] = 1
		v[288,1] = 3
		v[289,1] = 3
		v[290,1] = 3
		v[291,1] = 1
		v[292,1] = 3
		v[293,1] = 1
		v[294,1] = 1
		v[295,1] = 3
		v[296,1] = 1
		v[297,1] = 3
		v[298,1] = 1
		v[299,1] = 1
		v[300,1] = 1
		v[301,1] = 3
		v[302,1] = 3
		v[303,1] = 3
		v[304,1] = 1
		v[305,1] = 1
		v[306,1] = 3
		v[307,1] = 1
		v[308,1] = 3
		v[309,1] = 1
		v[310,1] = 1
		v[311,1] = 1
		v[312,1] = 1
		v[313,1] = 1
		v[314,1] = 1
		v[315,1] = 3
		v[316,1] = 1
		v[317,1] = 1
		v[318,1] = 3
		v[319,1] = 1
		v[320,1] = 3
		v[321,1] = 3
		v[322,1] = 1
		v[323,1] = 1
		v[324,1] = 1
		v[325,1] = 1
		v[326,1] = 3
		v[327,1] = 1
		v[328,1] = 3
		v[329,1] = 1
		v[330,1] = 3
		v[331,1] = 1
		v[332,1] = 1
		v[333,1] = 1
		v[334,1] = 1
		v[335,1] = 3
		v[336,1] = 3
		v[337,1] = 1
		v[338,1] = 1
		v[339,1] = 1
		v[340,1] = 1
		v[341,1] = 1
		v[342,1] = 3
		v[343,1] = 3
		v[344,1] = 3
		v[345,1] = 1
		v[346,1] = 1
		v[347,1] = 3
		v[348,1] = 3
		v[349,1] = 3
		v[350,1] = 3
		v[351,1] = 3
		v[352,1] = 1
		v[353,1] = 3
		v[354,1] = 3
		v[355,1] = 1
		v[356,1] = 3
		v[357,1] = 3
		v[358,1] = 3
		v[359,1] = 3
		v[360,1] = 1
		v[361,1] = 1
		v[362,1] = 1
		v[363,1] = 1
		v[364,1] = 1
		v[365,1] = 1
		v[366,1] = 3
		v[367,1] = 1
		v[368,1] = 1
		v[369,1] = 3
		v[370,1] = 1
		v[371,1] = 1
		v[372,1] = 1
		v[373,1] = 3
		v[374,1] = 1
		v[375,1] = 1
		v[376,1] = 1
		v[377,1] = 3
		v[378,1] = 3
		v[379,1] = 3
		v[380,1] = 1
		v[381,1] = 3
		v[382,1] = 1
		v[383,1] = 1
		v[384,1] = 3
		v[385,1] = 3
		v[386,1] = 3
		v[387,1] = 1
		v[388,1] = 3
		v[389,1] = 3
		v[390,1] = 1
		v[391,1] = 3
		v[392,1] = 1
		v[393,1] = 3
		v[394,1] = 3
		v[395,1] = 1
		v[396,1] = 3
		v[397,1] = 3
		v[398,1] = 3
		v[399,1] = 1
		v[400,1] = 1
		v[401,1] = 3
		v[402,1] = 3
		v[403,1] = 1
		v[404,1] = 3
		v[405,1] = 1
		v[406,1] = 3
		v[407,1] = 1
		v[408,1] = 1
		v[409,1] = 1
		v[410,1] = 3
		v[411,1] = 3
		v[412,1] = 3
		v[413,1] = 3
		v[414,1] = 1
		v[415,1] = 3
		v[416,1] = 1
		v[417,1] = 1
		v[418,1] = 3
		v[419,1] = 1
		v[420,1] = 3
		v[421,1] = 1
		v[422,1] = 1
		v[423,1] = 1
		v[424,1] = 3
		v[425,1] = 1
		v[426,1] = 3
		v[427,1] = 1
		v[428,1] = 3
		v[429,1] = 1
		v[430,1] = 3
		v[431,1] = 3
		v[432,1] = 3
		v[433,1] = 3
		v[434,1] = 3
		v[435,1] = 3
		v[436,1] = 3
		v[437,1] = 3
		v[438,1] = 1
		v[439,1] = 3
		v[440,1] = 3
		v[441,1] = 3
		v[442,1] = 3
		v[443,1] = 3
		v[444,1] = 1
		v[445,1] = 3
		v[446,1] = 1
		v[447,1] = 3
		v[448,1] = 3
		v[449,1] = 3
		v[450,1] = 1
		v[451,1] = 3
		v[452,1] = 1
		v[453,1] = 3
		v[454,1] = 1
		v[455,1] = 3
		v[456,1] = 3
		v[457,1] = 1
		v[458,1] = 3
		v[459,1] = 3
		v[460,1] = 3
		v[461,1] = 3
		v[462,1] = 3
		v[463,1] = 3
		v[464,1] = 3
		v[465,1] = 3
		v[466,1] = 3
		v[467,1] = 1
		v[468,1] = 1
		v[469,1] = 1
		v[470,1] = 1
		v[471,1] = 1
		v[472,1] = 1
		v[473,1] = 3
		v[474,1] = 3
		v[475,1] = 1
		v[476,1] = 1
		v[477,1] = 3
		v[478,1] = 3
		v[479,1] = 1
		v[480,1] = 1
		v[481,1] = 1
		v[482,1] = 3
		v[483,1] = 3
		v[484,1] = 1
		v[485,1] = 1
		v[486,1] = 3
		v[487,1] = 3
		v[488,1] = 3
		v[489,1] = 3
		v[490,1] = 1
		v[491,1] = 1
		v[492,1] = 3
		v[493,1] = 1
		v[494,1] = 3
		v[495,1] = 3
		v[496,1] = 1
		v[497,1] = 3
		v[498,1] = 3
		v[499,1] = 1
		v[500,1] = 1
		v[501,1] = 1
		v[502,1] = 3
		v[503,1] = 3
		v[504,1] = 3
		v[505,1] = 1
		v[506,1] = 1
		v[507,1] = 3
		v[508,1] = 3
		v[509,1] = 3
		v[510,1] = 3
		v[511,1] = 3
		v[512,1] = 1
		v[513,1] = 1
		v[514,1] = 1
		v[515,1] = 3
		v[516,1] = 1
		v[517,1] = 3
		v[518,1] = 3
		v[519,1] = 1
		v[520,1] = 3
		v[521,1] = 3
		v[522,1] = 3
		v[523,1] = 3
		v[524,1] = 1
		v[525,1] = 1
		v[526,1] = 3
		v[527,1] = 1
		v[528,1] = 1
		v[529,1] = 3
		v[530,1] = 1
		v[531,1] = 3
		v[532,1] = 1
		v[533,1] = 3
		v[534,1] = 1
		v[535,1] = 3
		v[536,1] = 3
		v[537,1] = 1
		v[538,1] = 1
		v[539,1] = 3
		v[540,1] = 3
		v[541,1] = 1
		v[542,1] = 3
		v[543,1] = 3
		v[544,1] = 1
		v[545,1] = 3
		v[546,1] = 3
		v[547,1] = 1
		v[548,1] = 1
		v[549,1] = 3
		v[550,1] = 1
		v[551,1] = 3
		v[552,1] = 3
		v[553,1] = 1
		v[554,1] = 1
		v[555,1] = 3
		v[556,1] = 1
		v[557,1] = 3
		v[558,1] = 1
		v[559,1] = 3
		v[560,1] = 1
		v[561,1] = 1
		v[562,1] = 3
		v[563,1] = 3
		v[564,1] = 1
		v[565,1] = 1
		v[566,1] = 1
		v[567,1] = 3
		v[568,1] = 3
		v[569,1] = 1
		v[570,1] = 3
		v[571,1] = 1
		v[572,1] = 1
		v[573,1] = 3
		v[574,1] = 3
		v[575,1] = 1
		v[576,1] = 1
		v[577,1] = 3
		v[578,1] = 1
		v[579,1] = 3
		v[580,1] = 1
		v[581,1] = 1
		v[582,1] = 1
		v[583,1] = 1
		v[584,1] = 1
		v[585,1] = 3
		v[586,1] = 1
		v[587,1] = 1
		v[588,1] = 1
		v[589,1] = 1
		v[590,1] = 3
		v[591,1] = 1
		v[592,1] = 3
		v[593,1] = 1
		v[594,1] = 1
		v[595,1] = 3
		v[596,1] = 3
		v[597,1] = 1
		v[598,1] = 1
		v[599,1] = 3
		v[600,1] = 1
		v[601,1] = 3
		v[602,1] = 1
		v[603,1] = 3
		v[604,1] = 3
		v[605,1] = 3
		v[606,1] = 1
		v[607,1] = 3
		v[608,1] = 3
		v[609,1] = 3
		v[610,1] = 1
		v[611,1] = 1
		v[612,1] = 3
		v[613,1] = 3
		v[614,1] = 3
		v[615,1] = 1
		v[616,1] = 1
		v[617,1] = 1
		v[618,1] = 1
		v[619,1] = 3
		v[620,1] = 1
		v[621,1] = 3
		v[622,1] = 1
		v[623,1] = 3
		v[624,1] = 1
		v[625,1] = 1
		v[626,1] = 3
		v[627,1] = 3
		v[628,1] = 1
		v[629,1] = 1
		v[630,1] = 1
		v[631,1] = 3
		v[632,1] = 3
		v[633,1] = 1
		v[634,1] = 3
		v[635,1] = 1
		v[636,1] = 3
		v[637,1] = 1
		v[638,1] = 1
		v[639,1] = 1
		v[640,1] = 1
		v[641,1] = 1
		v[642,1] = 1
		v[643,1] = 3
		v[644,1] = 1
		v[645,1] = 3
		v[646,1] = 3
		v[647,1] = 1
		v[648,1] = 3
		v[649,1] = 3
		v[650,1] = 3
		v[651,1] = 1
		v[652,1] = 3
		v[653,1] = 1
		v[654,1] = 1
		v[655,1] = 3
		v[656,1] = 3
		v[657,1] = 1
		v[658,1] = 1
		v[659,1] = 3
		v[660,1] = 3
		v[661,1] = 1
		v[662,1] = 1
		v[663,1] = 1
		v[664,1] = 3
		v[665,1] = 1
		v[666,1] = 3
		v[667,1] = 3
		v[668,1] = 1
		v[669,1] = 1
		v[670,1] = 3
		v[671,1] = 1
		v[672,1] = 1
		v[673,1] = 3
		v[674,1] = 1
		v[675,1] = 3
		v[676,1] = 1
		v[677,1] = 1
		v[678,1] = 1
		v[679,1] = 3
		v[680,1] = 3
		v[681,1] = 3
		v[682,1] = 3
		v[683,1] = 1
		v[684,1] = 1
		v[685,1] = 3
		v[686,1] = 3
		v[687,1] = 1
		v[688,1] = 1
		v[689,1] = 1
		v[690,1] = 1
		v[691,1] = 3
		v[692,1] = 1
		v[693,1] = 1
		v[694,1] = 3
		v[695,1] = 3
		v[696,1] = 3
		v[697,1] = 1
		v[698,1] = 1
		v[699,1] = 3
		v[700,1] = 3
		v[701,1] = 1
		v[702,1] = 3
		v[703,1] = 3
		v[704,1] = 1
		v[705,1] = 1
		v[706,1] = 3
		v[707,1] = 3
		v[708,1] = 3
		v[709,1] = 3
		v[710,1] = 3
		v[711,1] = 3
		v[712,1] = 3
		v[713,1] = 1
		v[714,1] = 3
		v[715,1] = 3
		v[716,1] = 1
		v[717,1] = 3
		v[718,1] = 1
		v[719,1] = 3
		v[720,1] = 1
		v[721,1] = 1
		v[722,1] = 3
		v[723,1] = 3
		v[724,1] = 1
		v[725,1] = 1
		v[726,1] = 1
		v[727,1] = 3
		v[728,1] = 1
		v[729,1] = 3
		v[730,1] = 3
		v[731,1] = 1
		v[732,1] = 3
		v[733,1] = 3
		v[734,1] = 1
		v[735,1] = 3
		v[736,1] = 1
		v[737,1] = 1
		v[738,1] = 3
		v[739,1] = 3
		v[740,1] = 3
		v[741,1] = 1
		v[742,1] = 1
		v[743,1] = 1
		v[744,1] = 3
		v[745,1] = 1
		v[746,1] = 1
		v[747,1] = 1
		v[748,1] = 3
		v[749,1] = 3
		v[750,1] = 3
		v[751,1] = 1
		v[752,1] = 3
		v[753,1] = 3
		v[754,1] = 1
		v[755,1] = 3
		v[756,1] = 1
		v[757,1] = 1
		v[758,1] = 3
		v[759,1] = 3
		v[760,1] = 3
		v[761,1] = 1
		v[762,1] = 3
		v[763,1] = 3
		v[764,1] = 1
		v[765,1] = 1
		v[766,1] = 1
		v[767,1] = 3
		v[768,1] = 1
		v[769,1] = 3
		v[770,1] = 3
		v[771,1] = 3
		v[772,1] = 3
		v[773,1] = 3
		v[774,1] = 3
		v[775,1] = 3
		v[776,1] = 3
		v[777,1] = 1
		v[778,1] = 3
		v[779,1] = 3
		v[780,1] = 1
		v[781,1] = 3
		v[782,1] = 1
		v[783,1] = 1
		v[784,1] = 3
		v[785,1] = 3
		v[786,1] = 3
		v[787,1] = 1
		v[788,1] = 3
		v[789,1] = 3
		v[790,1] = 3
		v[791,1] = 3
		v[792,1] = 3
		v[793,1] = 1
		v[794,1] = 3
		v[795,1] = 3
		v[796,1] = 3
		v[797,1] = 1
		v[798,1] = 1
		v[799,1] = 1
		v[800,1] = 3
		v[801,1] = 3
		v[802,1] = 1
		v[803,1] = 3
		v[804,1] = 3
		v[805,1] = 1
		v[806,1] = 3
		v[807,1] = 1
		v[808,1] = 3
		v[809,1] = 1
		v[810,1] = 3
		v[811,1] = 1
		v[812,1] = 3
		v[813,1] = 3
		v[814,1] = 3
		v[815,1] = 3
		v[816,1] = 3
		v[817,1] = 3
		v[818,1] = 1
		v[819,1] = 1
		v[820,1] = 3
		v[821,1] = 1
		v[822,1] = 3
		v[823,1] = 1
		v[824,1] = 1
		v[825,1] = 1
		v[826,1] = 1
		v[827,1] = 1
		v[828,1] = 3
		v[829,1] = 1
		v[830,1] = 1
		v[831,1] = 1
		v[832,1] = 3
		v[833,1] = 1
		v[834,1] = 3
		v[835,1] = 1
		v[836,1] = 1
		v[837,1] = 3
		v[838,1] = 3
		v[839,1] = 3
		v[840,1] = 1
		v[841,1] = 3
		v[842,1] = 1
		v[843,1] = 3
		v[844,1] = 1
		v[845,1] = 1
		v[846,1] = 3
		v[847,1] = 1
		v[848,1] = 3
		v[849,1] = 3
		v[850,1] = 1
		v[851,1] = 3
		v[852,1] = 1
		v[853,1] = 3
		v[854,1] = 3
		v[855,1] = 1
		v[856,1] = 3
		v[857,1] = 3
		v[858,1] = 1
		v[859,1] = 3
		v[860,1] = 3
		v[861,1] = 3
		v[862,1] = 3
		v[863,1] = 3
		v[864,1] = 3
		v[865,1] = 1
		v[866,1] = 3
		v[867,1] = 1
		v[868,1] = 1
		v[869,1] = 3
		v[870,1] = 3
		v[871,1] = 3
		v[872,1] = 1
		v[873,1] = 1
		v[874,1] = 3
		v[875,1] = 3
		v[876,1] = 3
		v[877,1] = 3
		v[878,1] = 3
		v[879,1] = 3
		v[880,1] = 3
		v[881,1] = 1
		v[882,1] = 3
		v[883,1] = 3
		v[884,1] = 3
		v[885,1] = 3
		v[886,1] = 1
		v[887,1] = 3
		v[888,1] = 1
		v[889,1] = 3
		v[890,1] = 3
		v[891,1] = 3
		v[892,1] = 1
		v[893,1] = 3
		v[894,1] = 1
		v[895,1] = 3
		v[896,1] = 1
		v[897,1] = 1
		v[898,1] = 1
		v[899,1] = 3
		v[900,1] = 3
		v[901,1] = 1
		v[902,1] = 3
		v[903,1] = 1
		v[904,1] = 1
		v[905,1] = 3
		v[906,1] = 3
		v[907,1] = 1
		v[908,1] = 3
		v[909,1] = 1
		v[910,1] = 1
		v[911,1] = 1
		v[912,1] = 1
		v[913,1] = 3
		v[914,1] = 1
		v[915,1] = 3
		v[916,1] = 1
		v[917,1] = 1
		v[918,1] = 3
		v[919,1] = 1
		v[920,1] = 3
		v[921,1] = 1
		v[922,1] = 3
		v[923,1] = 3
		v[924,1] = 3
		v[925,1] = 3
		v[926,1] = 3
		v[927,1] = 3
		v[928,1] = 1
		v[929,1] = 3
		v[930,1] = 3
		v[931,1] = 3
		v[932,1] = 3
		v[933,1] = 1
		v[934,1] = 3
		v[935,1] = 3
		v[936,1] = 1
		v[937,1] = 3
		v[938,1] = 3
		v[939,1] = 3
		v[940,1] = 3
		v[941,1] = 3
		v[942,1] = 1
		v[943,1] = 1
		v[944,1] = 1
		v[945,1] = 1
		v[946,1] = 3
		v[947,1] = 3
		v[948,1] = 3
		v[949,1] = 1
		v[950,1] = 3
		v[951,1] = 3
		v[952,1] = 1
		v[953,1] = 1
		v[954,1] = 3
		v[955,1] = 3
		v[956,1] = 1
		v[957,1] = 1
		v[958,1] = 3
		v[959,1] = 3
		v[960,1] = 1
		v[961,1] = 3
		v[962,1] = 1
		v[963,1] = 1
		v[964,1] = 3
		v[965,1] = 1
		v[966,1] = 3
		v[967,1] = 3
		v[968,1] = 3
		v[969,1] = 3
		v[970,1] = 3
		v[971,1] = 1
		v[972,1] = 3
		v[973,1] = 1
		v[974,1] = 1
		v[975,1] = 3
		v[976,1] = 3
		v[977,1] = 3
		v[978,1] = 3
		v[979,1] = 1
		v[980,1] = 3
		v[981,1] = 1
		v[982,1] = 1
		v[983,1] = 3
		v[984,1] = 3
		v[985,1] = 3
		v[986,1] = 3
		v[987,1] = 3
		v[988,1] = 3
		v[989,1] = 1
		v[990,1] = 1
		v[991,1] = 3
		v[992,1] = 1
		v[993,1] = 3
		v[994,1] = 1
		v[995,1] = 1
		v[996,1] = 3
		v[997,1] = 1
		v[998,1] = 1
		v[999,1] = 1
		v[1000,1] = 1
		v[1001,1] = 3
		v[1002,1] = 3
		v[1003,1] = 1
		v[1004,1] = 1
		v[1005,1] = 3
		v[1006,1] = 1
		v[1007,1] = 1
		v[1008,1] = 1
		v[1009,1] = 3
		v[1010,1] = 1
		v[1011,1] = 3
		v[1012,1] = 1
		v[1013,1] = 1
		v[1014,1] = 3
		v[1015,1] = 3
		v[1016,1] = 1
		v[1017,1] = 3
		v[1018,1] = 1
		v[1019,1] = 1
		v[1020,1] = 3
		v[1021,1] = 3
		v[1022,1] = 3
		v[1023,1] = 3
		v[1024,1] = 3
		v[1025,1] = 1
		v[1026,1] = 3
		v[1027,1] = 1
		v[1028,1] = 1
		v[1029,1] = 1
		v[1030,1] = 3
		v[1031,1] = 1
		v[1032,1] = 1
		v[1033,1] = 1
		v[1034,1] = 3
		v[1035,1] = 1
		v[1036,1] = 1
		v[1037,1] = 3
		v[1038,1] = 1
		v[1039,1] = 3
		v[1040,1] = 3
		v[1041,1] = 3
		v[1042,1] = 3
		v[1043,1] = 3
		v[1044,1] = 1
		v[1045,1] = 1
		v[1046,1] = 1
		v[1047,1] = 3
		v[1048,1] = 3
		v[1049,1] = 3
		v[1050,1] = 3
		v[1051,1] = 1
		v[1052,1] = 3
		v[1053,1] = 3
		v[1054,1] = 3
		v[1055,1] = 3
		v[1056,1] = 1
		v[1057,1] = 1
		v[1058,1] = 3
		v[1059,1] = 3
		v[1060,1] = 3
		v[1061,1] = 1
		v[1062,1] = 3
		v[1063,1] = 1
		v[1064,1] = 1
		v[1065,1] = 3
		v[1066,1] = 3
		v[1067,1] = 1
		v[1068,1] = 3
		v[1069,1] = 3
		v[1070,1] = 1
		v[1071,1] = 1
		v[1072,1] = 1
		v[1073,1] = 1
		v[1074,1] = 1
		v[1075,1] = 3
		v[1076,1] = 1
		v[1077,1] = 1
		v[1078,1] = 3
		v[1079,1] = 3
		v[1080,1] = 1
		v[1081,1] = 1
		v[1082,1] = 1
		v[1083,1] = 3
		v[1084,1] = 1
		v[1085,1] = 1
		v[1086,1] = 3
		v[1087,1] = 3
		v[1088,1] = 1
		v[1089,1] = 3
		v[1090,1] = 3
		v[1091,1] = 3
		v[1092,1] = 3
		v[1093,1] = 3
		v[1094,1] = 3
		v[1095,1] = 3
		v[1096,1] = 3
		v[1097,1] = 1
		v[1098,1] = 1
		v[1099,1] = 3
		v[1100,1] = 3
		v[1101,1] = 1
		v[1102,1] = 1
		v[1103,1] = 3
		v[1104,1] = 1
		v[1105,1] = 3
		v[1106,1] = 3
		v[1107,1] = 3
		v[1108,1] = 3
		v[1109,1] = 3
		v[1110,1] = 1

		v[3,2] = 7
		v[4,2] = 5
		v[5,2] = 1
		v[6,2] = 3
		v[7,2] = 3
		v[8,2] = 7
		v[9,2] = 5
		v[10,2] = 5
		v[11,2] = 7
		v[12,2] = 7
		v[13,2] = 1
		v[14,2] = 3
		v[15,2] = 3
		v[16,2] = 7
		v[17,2] = 5
		v[18,2] = 1
		v[19,2] = 1
		v[20,2] = 5
		v[21,2] = 3
		v[22,2] = 7
		v[23,2] = 1
		v[24,2] = 7
		v[25,2] = 5
		v[26,2] = 1
		v[27,2] = 3
		v[28,2] = 7
		v[29,2] = 7
		v[30,2] = 1
		v[31,2] = 1
		v[32,2] = 1
		v[33,2] = 5
		v[34,2] = 7
		v[35,2] = 7
		v[36,2] = 5
		v[37,2] = 1
		v[38,2] = 3
		v[39,2] = 3
		v[40,2] = 7
		v[41,2] = 5
		v[42,2] = 5
		v[43,2] = 5
		v[44,2] = 3
		v[45,2] = 3
		v[46,2] = 3
		v[47,2] = 1
		v[48,2] = 1
		v[49,2] = 5
		v[50,2] = 1
		v[51,2] = 1
		v[52,2] = 5
		v[53,2] = 3
		v[54,2] = 3
		v[55,2] = 3
		v[56,2] = 3
		v[57,2] = 1
		v[58,2] = 3
		v[59,2] = 7
		v[60,2] = 5
		v[61,2] = 7
		v[62,2] = 3
		v[63,2] = 7
		v[64,2] = 1
		v[65,2] = 3
		v[66,2] = 3
		v[67,2] = 5
		v[68,2] = 1
		v[69,2] = 3
		v[70,2] = 5
		v[71,2] = 5
		v[72,2] = 7
		v[73,2] = 7
		v[74,2] = 7
		v[75,2] = 1
		v[76,2] = 1
		v[77,2] = 3
		v[78,2] = 3
		v[79,2] = 1
		v[80,2] = 1
		v[81,2] = 5
		v[82,2] = 1
		v[83,2] = 5
		v[84,2] = 7
		v[85,2] = 5
		v[86,2] = 1
		v[87,2] = 7
		v[88,2] = 5
		v[89,2] = 3
		v[90,2] = 3
		v[91,2] = 1
		v[92,2] = 5
		v[93,2] = 7
		v[94,2] = 1
		v[95,2] = 7
		v[96,2] = 5
		v[97,2] = 1
		v[98,2] = 7
		v[99,2] = 3
		v[100,2] = 1
		v[101,2] = 7
		v[102,2] = 1
		v[103,2] = 7
		v[104,2] = 3
		v[105,2] = 3
		v[106,2] = 5
		v[107,2] = 7
		v[108,2] = 3
		v[109,2] = 3
		v[110,2] = 5
		v[111,2] = 1
		v[112,2] = 3
		v[113,2] = 3
		v[114,2] = 1
		v[115,2] = 3
		v[116,2] = 5
		v[117,2] = 1
		v[118,2] = 3
		v[119,2] = 3
		v[120,2] = 3
		v[121,2] = 7
		v[122,2] = 1
		v[123,2] = 1
		v[124,2] = 7
		v[125,2] = 3
		v[126,2] = 1
		v[127,2] = 3
		v[128,2] = 7
		v[129,2] = 5
		v[130,2] = 5
		v[131,2] = 7
		v[132,2] = 5
		v[133,2] = 5
		v[134,2] = 3
		v[135,2] = 1
		v[136,2] = 3
		v[137,2] = 3
		v[138,2] = 3
		v[139,2] = 1
		v[140,2] = 3
		v[141,2] = 3
		v[142,2] = 7
		v[143,2] = 3
		v[144,2] = 3
		v[145,2] = 1
		v[146,2] = 7
		v[147,2] = 5
		v[148,2] = 1
		v[149,2] = 7
		v[150,2] = 7
		v[151,2] = 5
		v[152,2] = 7
		v[153,2] = 5
		v[154,2] = 1
		v[155,2] = 3
		v[156,2] = 1
		v[157,2] = 7
		v[158,2] = 3
		v[159,2] = 7
		v[160,2] = 3
		v[161,2] = 5
		v[162,2] = 7
		v[163,2] = 3
		v[164,2] = 1
		v[165,2] = 3
		v[166,2] = 3
		v[167,2] = 3
		v[168,2] = 1
		v[169,2] = 5
		v[170,2] = 7
		v[171,2] = 3
		v[172,2] = 3
		v[173,2] = 7
		v[174,2] = 7
		v[175,2] = 7
		v[176,2] = 5
		v[177,2] = 3
		v[178,2] = 1
		v[179,2] = 7
		v[180,2] = 1
		v[181,2] = 3
		v[182,2] = 7
		v[183,2] = 5
		v[184,2] = 3
		v[185,2] = 3
		v[186,2] = 3
		v[187,2] = 7
		v[188,2] = 1
		v[189,2] = 1
		v[190,2] = 3
		v[191,2] = 1
		v[192,2] = 5
		v[193,2] = 7
		v[194,2] = 1
		v[195,2] = 3
		v[196,2] = 5
		v[197,2] = 3
		v[198,2] = 5
		v[199,2] = 3
		v[200,2] = 3
		v[201,2] = 7
		v[202,2] = 5
		v[203,2] = 5
		v[204,2] = 3
		v[205,2] = 3
		v[206,2] = 1
		v[207,2] = 3
		v[208,2] = 7
		v[209,2] = 7
		v[210,2] = 7
		v[211,2] = 1
		v[212,2] = 5
		v[213,2] = 7
		v[214,2] = 1
		v[215,2] = 3
		v[216,2] = 1
		v[217,2] = 1
		v[218,2] = 7
		v[219,2] = 1
		v[220,2] = 3
		v[221,2] = 1
		v[222,2] = 7
		v[223,2] = 1
		v[224,2] = 5
		v[225,2] = 3
		v[226,2] = 5
		v[227,2] = 3
		v[228,2] = 1
		v[229,2] = 1
		v[230,2] = 5
		v[231,2] = 5
		v[232,2] = 3
		v[233,2] = 3
		v[234,2] = 5
		v[235,2] = 7
		v[236,2] = 1
		v[237,2] = 5
		v[238,2] = 3
		v[239,2] = 7
		v[240,2] = 7
		v[241,2] = 3
		v[242,2] = 5
		v[243,2] = 3
		v[244,2] = 3
		v[245,2] = 1
		v[246,2] = 7
		v[247,2] = 3
		v[248,2] = 1
		v[249,2] = 3
		v[250,2] = 5
		v[251,2] = 7
		v[252,2] = 1
		v[253,2] = 3
		v[254,2] = 7
		v[255,2] = 1
		v[256,2] = 5
		v[257,2] = 1
		v[258,2] = 3
		v[259,2] = 1
		v[260,2] = 5
		v[261,2] = 3
		v[262,2] = 1
		v[263,2] = 7
		v[264,2] = 1
		v[265,2] = 5
		v[266,2] = 5
		v[267,2] = 5
		v[268,2] = 3
		v[269,2] = 7
		v[270,2] = 1
		v[271,2] = 1
		v[272,2] = 7
		v[273,2] = 3
		v[274,2] = 1
		v[275,2] = 1
		v[276,2] = 7
		v[277,2] = 5
		v[278,2] = 7
		v[279,2] = 5
		v[280,2] = 7
		v[281,2] = 7
		v[282,2] = 3
		v[283,2] = 7
		v[284,2] = 1
		v[285,2] = 3
		v[286,2] = 7
		v[287,2] = 7
		v[288,2] = 3
		v[289,2] = 5
		v[290,2] = 1
		v[291,2] = 1
		v[292,2] = 7
		v[293,2] = 1
		v[294,2] = 5
		v[295,2] = 5
		v[296,2] = 5
		v[297,2] = 1
		v[298,2] = 5
		v[299,2] = 1
		v[300,2] = 7
		v[301,2] = 5
		v[302,2] = 5
		v[303,2] = 7
		v[304,2] = 1
		v[305,2] = 1
		v[306,2] = 7
		v[307,2] = 1
		v[308,2] = 7
		v[309,2] = 7
		v[310,2] = 1
		v[311,2] = 1
		v[312,2] = 3
		v[313,2] = 3
		v[314,2] = 3
		v[315,2] = 7
		v[316,2] = 7
		v[317,2] = 5
		v[318,2] = 3
		v[319,2] = 7
		v[320,2] = 3
		v[321,2] = 1
		v[322,2] = 3
		v[323,2] = 7
		v[324,2] = 5
		v[325,2] = 3
		v[326,2] = 3
		v[327,2] = 5
		v[328,2] = 7
		v[329,2] = 1
		v[330,2] = 1
		v[331,2] = 5
		v[332,2] = 5
		v[333,2] = 7
		v[334,2] = 7
		v[335,2] = 1
		v[336,2] = 1
		v[337,2] = 1
		v[338,2] = 1
		v[339,2] = 5
		v[340,2] = 5
		v[341,2] = 5
		v[342,2] = 7
		v[343,2] = 5
		v[344,2] = 7
		v[345,2] = 1
		v[346,2] = 1
		v[347,2] = 3
		v[348,2] = 5
		v[349,2] = 1
		v[350,2] = 3
		v[351,2] = 3
		v[352,2] = 7
		v[353,2] = 3
		v[354,2] = 7
		v[355,2] = 5
		v[356,2] = 3
		v[357,2] = 5
		v[358,2] = 3
		v[359,2] = 1
		v[360,2] = 7
		v[361,2] = 1
		v[362,2] = 7
		v[363,2] = 7
		v[364,2] = 1
		v[365,2] = 1
		v[366,2] = 7
		v[367,2] = 7
		v[368,2] = 7
		v[369,2] = 5
		v[370,2] = 5
		v[371,2] = 1
		v[372,2] = 1
		v[373,2] = 7
		v[374,2] = 5
		v[375,2] = 5
		v[376,2] = 7
		v[377,2] = 5
		v[378,2] = 1
		v[379,2] = 1
		v[380,2] = 5
		v[381,2] = 5
		v[382,2] = 5
		v[383,2] = 5
		v[384,2] = 5
		v[385,2] = 5
		v[386,2] = 1
		v[387,2] = 3
		v[388,2] = 1
		v[389,2] = 5
		v[390,2] = 7
		v[391,2] = 3
		v[392,2] = 3
		v[393,2] = 5
		v[394,2] = 7
		v[395,2] = 3
		v[396,2] = 7
		v[397,2] = 1
		v[398,2] = 7
		v[399,2] = 7
		v[400,2] = 1
		v[401,2] = 3
		v[402,2] = 5
		v[403,2] = 1
		v[404,2] = 5
		v[405,2] = 5
		v[406,2] = 3
		v[407,2] = 7
		v[408,2] = 3
		v[409,2] = 7
		v[410,2] = 7
		v[411,2] = 5
		v[412,2] = 7
		v[413,2] = 5
		v[414,2] = 7
		v[415,2] = 1
		v[416,2] = 1
		v[417,2] = 5
		v[418,2] = 3
		v[419,2] = 5
		v[420,2] = 1
		v[421,2] = 5
		v[422,2] = 3
		v[423,2] = 7
		v[424,2] = 1
		v[425,2] = 5
		v[426,2] = 7
		v[427,2] = 7
		v[428,2] = 3
		v[429,2] = 5
		v[430,2] = 1
		v[431,2] = 3
		v[432,2] = 5
		v[433,2] = 1
		v[434,2] = 5
		v[435,2] = 3
		v[436,2] = 3
		v[437,2] = 3
		v[438,2] = 7
		v[439,2] = 3
		v[440,2] = 5
		v[441,2] = 1
		v[442,2] = 3
		v[443,2] = 7
		v[444,2] = 7
		v[445,2] = 3
		v[446,2] = 7
		v[447,2] = 5
		v[448,2] = 3
		v[449,2] = 3
		v[450,2] = 1
		v[451,2] = 7
		v[452,2] = 5
		v[453,2] = 1
		v[454,2] = 1
		v[455,2] = 3
		v[456,2] = 7
		v[457,2] = 1
		v[458,2] = 7
		v[459,2] = 1
		v[460,2] = 7
		v[461,2] = 3
		v[462,2] = 7
		v[463,2] = 3
		v[464,2] = 5
		v[465,2] = 7
		v[466,2] = 3
		v[467,2] = 5
		v[468,2] = 3
		v[469,2] = 1
		v[470,2] = 1
		v[471,2] = 1
		v[472,2] = 5
		v[473,2] = 7
		v[474,2] = 7
		v[475,2] = 3
		v[476,2] = 3
		v[477,2] = 1
		v[478,2] = 1
		v[479,2] = 1
		v[480,2] = 5
		v[481,2] = 5
		v[482,2] = 7
		v[483,2] = 3
		v[484,2] = 1
		v[485,2] = 1
		v[486,2] = 3
		v[487,2] = 3
		v[488,2] = 7
		v[489,2] = 3
		v[490,2] = 3
		v[491,2] = 5
		v[492,2] = 1
		v[493,2] = 3
		v[494,2] = 7
		v[495,2] = 3
		v[496,2] = 3
		v[497,2] = 7
		v[498,2] = 3
		v[499,2] = 5
		v[500,2] = 7
		v[501,2] = 5
		v[502,2] = 7
		v[503,2] = 7
		v[504,2] = 3
		v[505,2] = 3
		v[506,2] = 5
		v[507,2] = 1
		v[508,2] = 3
		v[509,2] = 5
		v[510,2] = 3
		v[511,2] = 1
		v[512,2] = 3
		v[513,2] = 5
		v[514,2] = 1
		v[515,2] = 1
		v[516,2] = 3
		v[517,2] = 7
		v[518,2] = 7
		v[519,2] = 1
		v[520,2] = 5
		v[521,2] = 1
		v[522,2] = 3
		v[523,2] = 7
		v[524,2] = 3
		v[525,2] = 7
		v[526,2] = 3
		v[527,2] = 5
		v[528,2] = 1
		v[529,2] = 7
		v[530,2] = 1
		v[531,2] = 1
		v[532,2] = 3
		v[533,2] = 5
		v[534,2] = 3
		v[535,2] = 7
		v[536,2] = 1
		v[537,2] = 5
		v[538,2] = 5
		v[539,2] = 1
		v[540,2] = 1
		v[541,2] = 3
		v[542,2] = 1
		v[543,2] = 3
		v[544,2] = 3
		v[545,2] = 7
		v[546,2] = 1
		v[547,2] = 7
		v[548,2] = 3
		v[549,2] = 1
		v[550,2] = 7
		v[551,2] = 3
		v[552,2] = 1
		v[553,2] = 7
		v[554,2] = 3
		v[555,2] = 5
		v[556,2] = 3
		v[557,2] = 5
		v[558,2] = 7
		v[559,2] = 3
		v[560,2] = 3
		v[561,2] = 3
		v[562,2] = 5
		v[563,2] = 1
		v[564,2] = 7
		v[565,2] = 7
		v[566,2] = 1
		v[567,2] = 3
		v[568,2] = 1
		v[569,2] = 3
		v[570,2] = 7
		v[571,2] = 7
		v[572,2] = 1
		v[573,2] = 3
		v[574,2] = 7
		v[575,2] = 3
		v[576,2] = 1
		v[577,2] = 5
		v[578,2] = 3
		v[579,2] = 1
		v[580,2] = 1
		v[581,2] = 1
		v[582,2] = 5
		v[583,2] = 3
		v[584,2] = 3
		v[585,2] = 7
		v[586,2] = 1
		v[587,2] = 5
		v[588,2] = 3
		v[589,2] = 5
		v[590,2] = 1
		v[591,2] = 3
		v[592,2] = 1
		v[593,2] = 3
		v[594,2] = 1
		v[595,2] = 5
		v[596,2] = 7
		v[597,2] = 7
		v[598,2] = 1
		v[599,2] = 1
		v[600,2] = 5
		v[601,2] = 3
		v[602,2] = 1
		v[603,2] = 5
		v[604,2] = 1
		v[605,2] = 1
		v[606,2] = 7
		v[607,2] = 7
		v[608,2] = 3
		v[609,2] = 5
		v[610,2] = 5
		v[611,2] = 1
		v[612,2] = 7
		v[613,2] = 1
		v[614,2] = 5
		v[615,2] = 1
		v[616,2] = 1
		v[617,2] = 3
		v[618,2] = 1
		v[619,2] = 5
		v[620,2] = 7
		v[621,2] = 5
		v[622,2] = 7
		v[623,2] = 7
		v[624,2] = 1
		v[625,2] = 5
		v[626,2] = 1
		v[627,2] = 1
		v[628,2] = 3
		v[629,2] = 5
		v[630,2] = 1
		v[631,2] = 5
		v[632,2] = 5
		v[633,2] = 3
		v[634,2] = 1
		v[635,2] = 3
		v[636,2] = 1
		v[637,2] = 5
		v[638,2] = 5
		v[639,2] = 3
		v[640,2] = 3
		v[641,2] = 3
		v[642,2] = 3
		v[643,2] = 1
		v[644,2] = 1
		v[645,2] = 3
		v[646,2] = 1
		v[647,2] = 3
		v[648,2] = 5
		v[649,2] = 5
		v[650,2] = 7
		v[651,2] = 5
		v[652,2] = 5
		v[653,2] = 7
		v[654,2] = 5
		v[655,2] = 7
		v[656,2] = 1
		v[657,2] = 3
		v[658,2] = 7
		v[659,2] = 7
		v[660,2] = 3
		v[661,2] = 5
		v[662,2] = 5
		v[663,2] = 7
		v[664,2] = 5
		v[665,2] = 5
		v[666,2] = 3
		v[667,2] = 3
		v[668,2] = 3
		v[669,2] = 1
		v[670,2] = 7
		v[671,2] = 1
		v[672,2] = 5
		v[673,2] = 5
		v[674,2] = 5
		v[675,2] = 3
		v[676,2] = 3
		v[677,2] = 5
		v[678,2] = 1
		v[679,2] = 3
		v[680,2] = 1
		v[681,2] = 3
		v[682,2] = 3
		v[683,2] = 3
		v[684,2] = 7
		v[685,2] = 1
		v[686,2] = 7
		v[687,2] = 7
		v[688,2] = 3
		v[689,2] = 7
		v[690,2] = 1
		v[691,2] = 1
		v[692,2] = 5
		v[693,2] = 7
		v[694,2] = 1
		v[695,2] = 7
		v[696,2] = 1
		v[697,2] = 7
		v[698,2] = 7
		v[699,2] = 1
		v[700,2] = 3
		v[701,2] = 7
		v[702,2] = 5
		v[703,2] = 1
		v[704,2] = 3
		v[705,2] = 5
		v[706,2] = 5
		v[707,2] = 5
		v[708,2] = 1
		v[709,2] = 1
		v[710,2] = 7
		v[711,2] = 1
		v[712,2] = 7
		v[713,2] = 1
		v[714,2] = 7
		v[715,2] = 7
		v[716,2] = 3
		v[717,2] = 1
		v[718,2] = 1
		v[719,2] = 5
		v[720,2] = 1
		v[721,2] = 5
		v[722,2] = 1
		v[723,2] = 5
		v[724,2] = 3
		v[725,2] = 5
		v[726,2] = 5
		v[727,2] = 5
		v[728,2] = 5
		v[729,2] = 5
		v[730,2] = 3
		v[731,2] = 3
		v[732,2] = 7
		v[733,2] = 3
		v[734,2] = 3
		v[735,2] = 5
		v[736,2] = 5
		v[737,2] = 3
		v[738,2] = 7
		v[739,2] = 1
		v[740,2] = 5
		v[741,2] = 7
		v[742,2] = 5
		v[743,2] = 1
		v[744,2] = 5
		v[745,2] = 5
		v[746,2] = 3
		v[747,2] = 5
		v[748,2] = 5
		v[749,2] = 7
		v[750,2] = 5
		v[751,2] = 3
		v[752,2] = 5
		v[753,2] = 5
		v[754,2] = 5
		v[755,2] = 1
		v[756,2] = 5
		v[757,2] = 5
		v[758,2] = 5
		v[759,2] = 5
		v[760,2] = 1
		v[761,2] = 3
		v[762,2] = 5
		v[763,2] = 3
		v[764,2] = 1
		v[765,2] = 7
		v[766,2] = 5
		v[767,2] = 5
		v[768,2] = 7
		v[769,2] = 1
		v[770,2] = 5
		v[771,2] = 3
		v[772,2] = 3
		v[773,2] = 1
		v[774,2] = 5
		v[775,2] = 3
		v[776,2] = 7
		v[777,2] = 1
		v[778,2] = 7
		v[779,2] = 5
		v[780,2] = 1
		v[781,2] = 1
		v[782,2] = 3
		v[783,2] = 1
		v[784,2] = 1
		v[785,2] = 7
		v[786,2] = 1
		v[787,2] = 5
		v[788,2] = 5
		v[789,2] = 3
		v[790,2] = 7
		v[791,2] = 3
		v[792,2] = 7
		v[793,2] = 5
		v[794,2] = 3
		v[795,2] = 1
		v[796,2] = 1
		v[797,2] = 3
		v[798,2] = 1
		v[799,2] = 3
		v[800,2] = 5
		v[801,2] = 5
		v[802,2] = 7
		v[803,2] = 5
		v[804,2] = 3
		v[805,2] = 7
		v[806,2] = 7
		v[807,2] = 7
		v[808,2] = 3
		v[809,2] = 7
		v[810,2] = 3
		v[811,2] = 7
		v[812,2] = 1
		v[813,2] = 3
		v[814,2] = 1
		v[815,2] = 7
		v[816,2] = 7
		v[817,2] = 1
		v[818,2] = 7
		v[819,2] = 3
		v[820,2] = 7
		v[821,2] = 3
		v[822,2] = 7
		v[823,2] = 3
		v[824,2] = 7
		v[825,2] = 3
		v[826,2] = 5
		v[827,2] = 1
		v[828,2] = 1
		v[829,2] = 7
		v[830,2] = 3
		v[831,2] = 1
		v[832,2] = 5
		v[833,2] = 5
		v[834,2] = 7
		v[835,2] = 1
		v[836,2] = 5
		v[837,2] = 5
		v[838,2] = 5
		v[839,2] = 7
		v[840,2] = 1
		v[841,2] = 5
		v[842,2] = 5
		v[843,2] = 1
		v[844,2] = 5
		v[845,2] = 5
		v[846,2] = 3
		v[847,2] = 1
		v[848,2] = 3
		v[849,2] = 1
		v[850,2] = 7
		v[851,2] = 3
		v[852,2] = 1
		v[853,2] = 3
		v[854,2] = 5
		v[855,2] = 7
		v[856,2] = 7
		v[857,2] = 7
		v[858,2] = 1
		v[859,2] = 1
		v[860,2] = 7
		v[861,2] = 3
		v[862,2] = 1
		v[863,2] = 5
		v[864,2] = 5
		v[865,2] = 5
		v[866,2] = 1
		v[867,2] = 1
		v[868,2] = 1
		v[869,2] = 1
		v[870,2] = 1
		v[871,2] = 5
		v[872,2] = 3
		v[873,2] = 5
		v[874,2] = 1
		v[875,2] = 3
		v[876,2] = 5
		v[877,2] = 3
		v[878,2] = 1
		v[879,2] = 1
		v[880,2] = 1
		v[881,2] = 1
		v[882,2] = 3
		v[883,2] = 7
		v[884,2] = 3
		v[885,2] = 7
		v[886,2] = 5
		v[887,2] = 7
		v[888,2] = 1
		v[889,2] = 5
		v[890,2] = 5
		v[891,2] = 7
		v[892,2] = 5
		v[893,2] = 3
		v[894,2] = 3
		v[895,2] = 7
		v[896,2] = 5
		v[897,2] = 3
		v[898,2] = 1
		v[899,2] = 1
		v[900,2] = 3
		v[901,2] = 1
		v[902,2] = 3
		v[903,2] = 1
		v[904,2] = 1
		v[905,2] = 3
		v[906,2] = 7
		v[907,2] = 1
		v[908,2] = 7
		v[909,2] = 1
		v[910,2] = 1
		v[911,2] = 5
		v[912,2] = 1
		v[913,2] = 7
		v[914,2] = 5
		v[915,2] = 3
		v[916,2] = 7
		v[917,2] = 3
		v[918,2] = 5
		v[919,2] = 3
		v[920,2] = 1
		v[921,2] = 1
		v[922,2] = 5
		v[923,2] = 5
		v[924,2] = 1
		v[925,2] = 7
		v[926,2] = 7
		v[927,2] = 3
		v[928,2] = 7
		v[929,2] = 3
		v[930,2] = 7
		v[931,2] = 1
		v[932,2] = 5
		v[933,2] = 1
		v[934,2] = 5
		v[935,2] = 3
		v[936,2] = 7
		v[937,2] = 3
		v[938,2] = 5
		v[939,2] = 7
		v[940,2] = 7
		v[941,2] = 7
		v[942,2] = 3
		v[943,2] = 3
		v[944,2] = 1
		v[945,2] = 1
		v[946,2] = 5
		v[947,2] = 5
		v[948,2] = 3
		v[949,2] = 7
		v[950,2] = 1
		v[951,2] = 1
		v[952,2] = 1
		v[953,2] = 3
		v[954,2] = 5
		v[955,2] = 3
		v[956,2] = 1
		v[957,2] = 1
		v[958,2] = 3
		v[959,2] = 3
		v[960,2] = 7
		v[961,2] = 5
		v[962,2] = 1
		v[963,2] = 1
		v[964,2] = 3
		v[965,2] = 7
		v[966,2] = 1
		v[967,2] = 5
		v[968,2] = 7
		v[969,2] = 3
		v[970,2] = 7
		v[971,2] = 5
		v[972,2] = 5
		v[973,2] = 7
		v[974,2] = 3
		v[975,2] = 5
		v[976,2] = 3
		v[977,2] = 1
		v[978,2] = 5
		v[979,2] = 3
		v[980,2] = 1
		v[981,2] = 1
		v[982,2] = 7
		v[983,2] = 5
		v[984,2] = 1
		v[985,2] = 7
		v[986,2] = 3
		v[987,2] = 7
		v[988,2] = 5
		v[989,2] = 1
		v[990,2] = 7
		v[991,2] = 1
		v[992,2] = 7
		v[993,2] = 7
		v[994,2] = 1
		v[995,2] = 1
		v[996,2] = 7
		v[997,2] = 1
		v[998,2] = 5
		v[999,2] = 5
		v[1000,2] = 1
		v[1001,2] = 1
		v[1002,2] = 7
		v[1003,2] = 5
		v[1004,2] = 7
		v[1005,2] = 1
		v[1006,2] = 5
		v[1007,2] = 3
		v[1008,2] = 5
		v[1009,2] = 3
		v[1010,2] = 3
		v[1011,2] = 7
		v[1012,2] = 1
		v[1013,2] = 5
		v[1014,2] = 1
		v[1015,2] = 1
		v[1016,2] = 5
		v[1017,2] = 5
		v[1018,2] = 3
		v[1019,2] = 3
		v[1020,2] = 7
		v[1021,2] = 5
		v[1022,2] = 5
		v[1023,2] = 1
		v[1024,2] = 1
		v[1025,2] = 1
		v[1026,2] = 3
		v[1027,2] = 1
		v[1028,2] = 5
		v[1029,2] = 7
		v[1030,2] = 7
		v[1031,2] = 1
		v[1032,2] = 7
		v[1033,2] = 5
		v[1034,2] = 7
		v[1035,2] = 3
		v[1036,2] = 7
		v[1037,2] = 3
		v[1038,2] = 1
		v[1039,2] = 3
		v[1040,2] = 7
		v[1041,2] = 3
		v[1042,2] = 1
		v[1043,2] = 5
		v[1044,2] = 5
		v[1045,2] = 3
		v[1046,2] = 5
		v[1047,2] = 1
		v[1048,2] = 3
		v[1049,2] = 5
		v[1050,2] = 5
		v[1051,2] = 5
		v[1052,2] = 1
		v[1053,2] = 1
		v[1054,2] = 7
		v[1055,2] = 7
		v[1056,2] = 1
		v[1057,2] = 5
		v[1058,2] = 5
		v[1059,2] = 1
		v[1060,2] = 3
		v[1061,2] = 5
		v[1062,2] = 1
		v[1063,2] = 5
		v[1064,2] = 3
		v[1065,2] = 5
		v[1066,2] = 3
		v[1067,2] = 3
		v[1068,2] = 7
		v[1069,2] = 5
		v[1070,2] = 7
		v[1071,2] = 3
		v[1072,2] = 7
		v[1073,2] = 3
		v[1074,2] = 1
		v[1075,2] = 3
		v[1076,2] = 7
		v[1077,2] = 7
		v[1078,2] = 3
		v[1079,2] = 3
		v[1080,2] = 1
		v[1081,2] = 1
		v[1082,2] = 3
		v[1083,2] = 3
		v[1084,2] = 3
		v[1085,2] = 3
		v[1086,2] = 3
		v[1087,2] = 5
		v[1088,2] = 5
		v[1089,2] = 3
		v[1090,2] = 3
		v[1091,2] = 3
		v[1092,2] = 1
		v[1093,2] = 3
		v[1094,2] = 5
		v[1095,2] = 7
		v[1096,2] = 7
		v[1097,2] = 1
		v[1098,2] = 5
		v[1099,2] = 7
		v[1100,2] = 3
		v[1101,2] = 7
		v[1102,2] = 1
		v[1103,2] = 1
		v[1104,2] = 3
		v[1105,2] = 5
		v[1106,2] = 7
		v[1107,2] = 5
		v[1108,2] = 3
		v[1109,2] = 3
		v[1110,2] = 3

		v[5,3] = 1
		v[6,3] = 7
		v[7,3] = 9
		v[8,3] = 13
		v[9,3] = 11
		v[10,3] = 1
		v[11,3] = 3
		v[12,3] = 7
		v[13,3] = 9
		v[14,3] = 5
		v[15,3] = 13
		v[16,3] = 13
		v[17,3] = 11
		v[18,3] = 3
		v[19,3] = 15
		v[20,3] = 5
		v[21,3] = 3
		v[22,3] = 15
		v[23,3] = 7
		v[24,3] = 9
		v[25,3] = 13
		v[26,3] = 9
		v[27,3] = 1
		v[28,3] = 11
		v[29,3] = 7
		v[30,3] = 5
		v[31,3] = 15
		v[32,3] = 1
		v[33,3] = 15
		v[34,3] = 11
		v[35,3] = 5
		v[36,3] = 11
		v[37,3] = 1
		v[38,3] = 7
		v[39,3] = 9
		v[40,3] = 7
		v[41,3] = 7
		v[42,3] = 1
		v[43,3] = 15
		v[44,3] = 15
		v[45,3] = 15
		v[46,3] = 13
		v[47,3] = 3
		v[48,3] = 3
		v[49,3] = 15
		v[50,3] = 5
		v[51,3] = 9
		v[52,3] = 7
		v[53,3] = 13
		v[54,3] = 3
		v[55,3] = 7
		v[56,3] = 5
		v[57,3] = 11
		v[58,3] = 9
		v[59,3] = 1
		v[60,3] = 9
		v[61,3] = 1
		v[62,3] = 5
		v[63,3] = 7
		v[64,3] = 13
		v[65,3] = 9
		v[66,3] = 9
		v[67,3] = 1
		v[68,3] = 7
		v[69,3] = 3
		v[70,3] = 5
		v[71,3] = 1
		v[72,3] = 11
		v[73,3] = 11
		v[74,3] = 13
		v[75,3] = 7
		v[76,3] = 7
		v[77,3] = 9
		v[78,3] = 9
		v[79,3] = 1
		v[80,3] = 1
		v[81,3] = 3
		v[82,3] = 9
		v[83,3] = 15
		v[84,3] = 1
		v[85,3] = 5
		v[86,3] = 13
		v[87,3] = 1
		v[88,3] = 9
		v[89,3] = 9
		v[90,3] = 9
		v[91,3] = 9
		v[92,3] = 9
		v[93,3] = 13
		v[94,3] = 11
		v[95,3] = 3
		v[96,3] = 5
		v[97,3] = 11
		v[98,3] = 11
		v[99,3] = 13
		v[100,3] = 5
		v[101,3] = 3
		v[102,3] = 15
		v[103,3] = 1
		v[104,3] = 11
		v[105,3] = 11
		v[106,3] = 7
		v[107,3] = 13
		v[108,3] = 15
		v[109,3] = 11
		v[110,3] = 13
		v[111,3] = 9
		v[112,3] = 11
		v[113,3] = 15
		v[114,3] = 15
		v[115,3] = 13
		v[116,3] = 3
		v[117,3] = 15
		v[118,3] = 7
		v[119,3] = 9
		v[120,3] = 11
		v[121,3] = 13
		v[122,3] = 11
		v[123,3] = 9
		v[124,3] = 9
		v[125,3] = 5
		v[126,3] = 13
		v[127,3] = 9
		v[128,3] = 1
		v[129,3] = 13
		v[130,3] = 7
		v[131,3] = 7
		v[132,3] = 7
		v[133,3] = 7
		v[134,3] = 7
		v[135,3] = 5
		v[136,3] = 9
		v[137,3] = 7
		v[138,3] = 13
		v[139,3] = 11
		v[140,3] = 9
		v[141,3] = 11
		v[142,3] = 15
		v[143,3] = 3
		v[144,3] = 13
		v[145,3] = 11
		v[146,3] = 1
		v[147,3] = 11
		v[148,3] = 3
		v[149,3] = 3
		v[150,3] = 9
		v[151,3] = 11
		v[152,3] = 1
		v[153,3] = 7
		v[154,3] = 1
		v[155,3] = 15
		v[156,3] = 15
		v[157,3] = 3
		v[158,3] = 1
		v[159,3] = 9
		v[160,3] = 1
		v[161,3] = 7
		v[162,3] = 13
		v[163,3] = 11
		v[164,3] = 3
		v[165,3] = 13
		v[166,3] = 11
		v[167,3] = 7
		v[168,3] = 3
		v[169,3] = 3
		v[170,3] = 5
		v[171,3] = 13
		v[172,3] = 11
		v[173,3] = 5
		v[174,3] = 11
		v[175,3] = 1
		v[176,3] = 3
		v[177,3] = 9
		v[178,3] = 7
		v[179,3] = 15
		v[180,3] = 7
		v[181,3] = 5
		v[182,3] = 13
		v[183,3] = 7
		v[184,3] = 9
		v[185,3] = 13
		v[186,3] = 15
		v[187,3] = 13
		v[188,3] = 9
		v[189,3] = 7
		v[190,3] = 15
		v[191,3] = 7
		v[192,3] = 9
		v[193,3] = 5
		v[194,3] = 11
		v[195,3] = 11
		v[196,3] = 13
		v[197,3] = 13
		v[198,3] = 9
		v[199,3] = 3
		v[200,3] = 5
		v[201,3] = 13
		v[202,3] = 9
		v[203,3] = 11
		v[204,3] = 15
		v[205,3] = 11
		v[206,3] = 7
		v[207,3] = 1
		v[208,3] = 7
		v[209,3] = 13
		v[210,3] = 3
		v[211,3] = 13
		v[212,3] = 3
		v[213,3] = 13
		v[214,3] = 9
		v[215,3] = 15
		v[216,3] = 7
		v[217,3] = 13
		v[218,3] = 13
		v[219,3] = 3
		v[220,3] = 13
		v[221,3] = 15
		v[222,3] = 15
		v[223,3] = 11
		v[224,3] = 9
		v[225,3] = 13
		v[226,3] = 9
		v[227,3] = 15
		v[228,3] = 1
		v[229,3] = 1
		v[230,3] = 15
		v[231,3] = 11
		v[232,3] = 11
		v[233,3] = 7
		v[234,3] = 1
		v[235,3] = 11
		v[236,3] = 13
		v[237,3] = 9
		v[238,3] = 13
		v[239,3] = 3
		v[240,3] = 5
		v[241,3] = 11
		v[242,3] = 13
		v[243,3] = 9
		v[244,3] = 9
		v[245,3] = 13
		v[246,3] = 1
		v[247,3] = 11
		v[248,3] = 15
		v[249,3] = 13
		v[250,3] = 3
		v[251,3] = 13
		v[252,3] = 7
		v[253,3] = 15
		v[254,3] = 1
		v[255,3] = 15
		v[256,3] = 3
		v[257,3] = 3
		v[258,3] = 11
		v[259,3] = 7
		v[260,3] = 13
		v[261,3] = 7
		v[262,3] = 7
		v[263,3] = 9
		v[264,3] = 7
		v[265,3] = 5
		v[266,3] = 15
		v[267,3] = 9
		v[268,3] = 5
		v[269,3] = 5
		v[270,3] = 7
		v[271,3] = 15
		v[272,3] = 13
		v[273,3] = 15
		v[274,3] = 5
		v[275,3] = 15
		v[276,3] = 5
		v[277,3] = 3
		v[278,3] = 1
		v[279,3] = 11
		v[280,3] = 7
		v[281,3] = 1
		v[282,3] = 5
		v[283,3] = 7
		v[284,3] = 9
		v[285,3] = 3
		v[286,3] = 11
		v[287,3] = 1
		v[288,3] = 15
		v[289,3] = 1
		v[290,3] = 3
		v[291,3] = 15
		v[292,3] = 11
		v[293,3] = 13
		v[294,3] = 5
		v[295,3] = 13
		v[296,3] = 1
		v[297,3] = 7
		v[298,3] = 1
		v[299,3] = 15
		v[300,3] = 7
		v[301,3] = 5
		v[302,3] = 1
		v[303,3] = 1
		v[304,3] = 15
		v[305,3] = 13
		v[306,3] = 11
		v[307,3] = 11
		v[308,3] = 13
		v[309,3] = 5
		v[310,3] = 11
		v[311,3] = 7
		v[312,3] = 9
		v[313,3] = 7
		v[314,3] = 1
		v[315,3] = 5
		v[316,3] = 3
		v[317,3] = 9
		v[318,3] = 5
		v[319,3] = 5
		v[320,3] = 11
		v[321,3] = 5
		v[322,3] = 1
		v[323,3] = 7
		v[324,3] = 1
		v[325,3] = 11
		v[326,3] = 7
		v[327,3] = 9
		v[328,3] = 13
		v[329,3] = 15
		v[330,3] = 13
		v[331,3] = 3
		v[332,3] = 1
		v[333,3] = 11
		v[334,3] = 13
		v[335,3] = 15
		v[336,3] = 1
		v[337,3] = 1
		v[338,3] = 11
		v[339,3] = 9
		v[340,3] = 13
		v[341,3] = 3
		v[342,3] = 13
		v[343,3] = 11
		v[344,3] = 15
		v[345,3] = 13
		v[346,3] = 9
		v[347,3] = 9
		v[348,3] = 9
		v[349,3] = 5
		v[350,3] = 5
		v[351,3] = 5
		v[352,3] = 5
		v[353,3] = 1
		v[354,3] = 15
		v[355,3] = 5
		v[356,3] = 9
		v[357,3] = 11
		v[358,3] = 7
		v[359,3] = 15
		v[360,3] = 5
		v[361,3] = 3
		v[362,3] = 13
		v[363,3] = 5
		v[364,3] = 3
		v[365,3] = 11
		v[366,3] = 5
		v[367,3] = 1
		v[368,3] = 11
		v[369,3] = 13
		v[370,3] = 9
		v[371,3] = 11
		v[372,3] = 3
		v[373,3] = 7
		v[374,3] = 13
		v[375,3] = 15
		v[376,3] = 1
		v[377,3] = 7
		v[378,3] = 11
		v[379,3] = 1
		v[380,3] = 13
		v[381,3] = 1
		v[382,3] = 15
		v[383,3] = 1
		v[384,3] = 9
		v[385,3] = 7
		v[386,3] = 3
		v[387,3] = 9
		v[388,3] = 11
		v[389,3] = 1
		v[390,3] = 9
		v[391,3] = 13
		v[392,3] = 13
		v[393,3] = 3
		v[394,3] = 11
		v[395,3] = 7
		v[396,3] = 9
		v[397,3] = 1
		v[398,3] = 7
		v[399,3] = 15
		v[400,3] = 9
		v[401,3] = 1
		v[402,3] = 5
		v[403,3] = 13
		v[404,3] = 5
		v[405,3] = 11
		v[406,3] = 3
		v[407,3] = 9
		v[408,3] = 15
		v[409,3] = 11
		v[410,3] = 13
		v[411,3] = 5
		v[412,3] = 1
		v[413,3] = 7
		v[414,3] = 7
		v[415,3] = 5
		v[416,3] = 13
		v[417,3] = 7
		v[418,3] = 7
		v[419,3] = 9
		v[420,3] = 5
		v[421,3] = 11
		v[422,3] = 11
		v[423,3] = 1
		v[424,3] = 1
		v[425,3] = 15
		v[426,3] = 3
		v[427,3] = 13
		v[428,3] = 9
		v[429,3] = 13
		v[430,3] = 9
		v[431,3] = 9
		v[432,3] = 11
		v[433,3] = 5
		v[434,3] = 5
		v[435,3] = 13
		v[436,3] = 15
		v[437,3] = 3
		v[438,3] = 9
		v[439,3] = 15
		v[440,3] = 3
		v[441,3] = 11
		v[442,3] = 11
		v[443,3] = 15
		v[444,3] = 15
		v[445,3] = 3
		v[446,3] = 11
		v[447,3] = 15
		v[448,3] = 15
		v[449,3] = 3
		v[450,3] = 1
		v[451,3] = 3
		v[452,3] = 1
		v[453,3] = 3
		v[454,3] = 3
		v[455,3] = 1
		v[456,3] = 3
		v[457,3] = 13
		v[458,3] = 1
		v[459,3] = 11
		v[460,3] = 5
		v[461,3] = 15
		v[462,3] = 7
		v[463,3] = 15
		v[464,3] = 9
		v[465,3] = 1
		v[466,3] = 7
		v[467,3] = 1
		v[468,3] = 9
		v[469,3] = 11
		v[470,3] = 15
		v[471,3] = 1
		v[472,3] = 13
		v[473,3] = 9
		v[474,3] = 13
		v[475,3] = 11
		v[476,3] = 7
		v[477,3] = 3
		v[478,3] = 7
		v[479,3] = 3
		v[480,3] = 13
		v[481,3] = 7
		v[482,3] = 9
		v[483,3] = 7
		v[484,3] = 7
		v[485,3] = 3
		v[486,3] = 3
		v[487,3] = 9
		v[488,3] = 9
		v[489,3] = 7
		v[490,3] = 5
		v[491,3] = 11
		v[492,3] = 13
		v[493,3] = 13
		v[494,3] = 7
		v[495,3] = 7
		v[496,3] = 15
		v[497,3] = 9
		v[498,3] = 5
		v[499,3] = 5
		v[500,3] = 3
		v[501,3] = 3
		v[502,3] = 13
		v[503,3] = 3
		v[504,3] = 9
		v[505,3] = 3
		v[506,3] = 1
		v[507,3] = 11
		v[508,3] = 1
		v[509,3] = 3
		v[510,3] = 11
		v[511,3] = 15
		v[512,3] = 11
		v[513,3] = 11
		v[514,3] = 11
		v[515,3] = 9
		v[516,3] = 13
		v[517,3] = 7
		v[518,3] = 9
		v[519,3] = 15
		v[520,3] = 9
		v[521,3] = 11
		v[522,3] = 1
		v[523,3] = 3
		v[524,3] = 3
		v[525,3] = 9
		v[526,3] = 7
		v[527,3] = 15
		v[528,3] = 13
		v[529,3] = 13
		v[530,3] = 7
		v[531,3] = 15
		v[532,3] = 9
		v[533,3] = 13
		v[534,3] = 9
		v[535,3] = 15
		v[536,3] = 13
		v[537,3] = 15
		v[538,3] = 9
		v[539,3] = 13
		v[540,3] = 1
		v[541,3] = 11
		v[542,3] = 7
		v[543,3] = 11
		v[544,3] = 3
		v[545,3] = 13
		v[546,3] = 5
		v[547,3] = 1
		v[548,3] = 7
		v[549,3] = 15
		v[550,3] = 3
		v[551,3] = 13
		v[552,3] = 7
		v[553,3] = 13
		v[554,3] = 13
		v[555,3] = 11
		v[556,3] = 3
		v[557,3] = 5
		v[558,3] = 3
		v[559,3] = 13
		v[560,3] = 11
		v[561,3] = 9
		v[562,3] = 9
		v[563,3] = 3
		v[564,3] = 11
		v[565,3] = 11
		v[566,3] = 7
		v[567,3] = 9
		v[568,3] = 13
		v[569,3] = 11
		v[570,3] = 7
		v[571,3] = 15
		v[572,3] = 13
		v[573,3] = 7
		v[574,3] = 5
		v[575,3] = 3
		v[576,3] = 1
		v[577,3] = 5
		v[578,3] = 15
		v[579,3] = 15
		v[580,3] = 3
		v[581,3] = 11
		v[582,3] = 1
		v[583,3] = 7
		v[584,3] = 3
		v[585,3] = 15
		v[586,3] = 11
		v[587,3] = 5
		v[588,3] = 5
		v[589,3] = 3
		v[590,3] = 5
		v[591,3] = 5
		v[592,3] = 1
		v[593,3] = 15
		v[594,3] = 5
		v[595,3] = 1
		v[596,3] = 5
		v[597,3] = 3
		v[598,3] = 7
		v[599,3] = 5
		v[600,3] = 11
		v[601,3] = 3
		v[602,3] = 13
		v[603,3] = 9
		v[604,3] = 13
		v[605,3] = 15
		v[606,3] = 5
		v[607,3] = 3
		v[608,3] = 5
		v[609,3] = 9
		v[610,3] = 5
		v[611,3] = 3
		v[612,3] = 11
		v[613,3] = 1
		v[614,3] = 13
		v[615,3] = 9
		v[616,3] = 15
		v[617,3] = 3
		v[618,3] = 5
		v[619,3] = 11
		v[620,3] = 9
		v[621,3] = 1
		v[622,3] = 3
		v[623,3] = 15
		v[624,3] = 9
		v[625,3] = 9
		v[626,3] = 9
		v[627,3] = 11
		v[628,3] = 7
		v[629,3] = 5
		v[630,3] = 13
		v[631,3] = 1
		v[632,3] = 15
		v[633,3] = 3
		v[634,3] = 13
		v[635,3] = 9
		v[636,3] = 13
		v[637,3] = 5
		v[638,3] = 1
		v[639,3] = 5
		v[640,3] = 1
		v[641,3] = 13
		v[642,3] = 13
		v[643,3] = 7
		v[644,3] = 7
		v[645,3] = 1
		v[646,3] = 9
		v[647,3] = 5
		v[648,3] = 11
		v[649,3] = 9
		v[650,3] = 11
		v[651,3] = 13
		v[652,3] = 3
		v[653,3] = 15
		v[654,3] = 15
		v[655,3] = 13
		v[656,3] = 15
		v[657,3] = 7
		v[658,3] = 5
		v[659,3] = 7
		v[660,3] = 9
		v[661,3] = 7
		v[662,3] = 9
		v[663,3] = 9
		v[664,3] = 9
		v[665,3] = 11
		v[666,3] = 9
		v[667,3] = 3
		v[668,3] = 11
		v[669,3] = 15
		v[670,3] = 13
		v[671,3] = 13
		v[672,3] = 5
		v[673,3] = 9
		v[674,3] = 15
		v[675,3] = 1
		v[676,3] = 1
		v[677,3] = 9
		v[678,3] = 5
		v[679,3] = 13
		v[680,3] = 3
		v[681,3] = 13
		v[682,3] = 15
		v[683,3] = 3
		v[684,3] = 1
		v[685,3] = 3
		v[686,3] = 11
		v[687,3] = 13
		v[688,3] = 1
		v[689,3] = 15
		v[690,3] = 9
		v[691,3] = 9
		v[692,3] = 3
		v[693,3] = 1
		v[694,3] = 9
		v[695,3] = 1
		v[696,3] = 9
		v[697,3] = 1
		v[698,3] = 13
		v[699,3] = 11
		v[700,3] = 15
		v[701,3] = 7
		v[702,3] = 11
		v[703,3] = 15
		v[704,3] = 13
		v[705,3] = 15
		v[706,3] = 1
		v[707,3] = 9
		v[708,3] = 9
		v[709,3] = 7
		v[710,3] = 3
		v[711,3] = 5
		v[712,3] = 11
		v[713,3] = 7
		v[714,3] = 3
		v[715,3] = 9
		v[716,3] = 5
		v[717,3] = 15
		v[718,3] = 7
		v[719,3] = 5
		v[720,3] = 3
		v[721,3] = 13
		v[722,3] = 7
		v[723,3] = 1
		v[724,3] = 1
		v[725,3] = 9
		v[726,3] = 15
		v[727,3] = 15
		v[728,3] = 15
		v[729,3] = 11
		v[730,3] = 3
		v[731,3] = 5
		v[732,3] = 15
		v[733,3] = 13
		v[734,3] = 7
		v[735,3] = 15
		v[736,3] = 15
		v[737,3] = 11
		v[738,3] = 11
		v[739,3] = 9
		v[740,3] = 5
		v[741,3] = 15
		v[742,3] = 9
		v[743,3] = 7
		v[744,3] = 3
		v[745,3] = 13
		v[746,3] = 1
		v[747,3] = 1
		v[748,3] = 5
		v[749,3] = 1
		v[750,3] = 3
		v[751,3] = 1
		v[752,3] = 7
		v[753,3] = 1
		v[754,3] = 1
		v[755,3] = 5
		v[756,3] = 1
		v[757,3] = 11
		v[758,3] = 11
		v[759,3] = 9
		v[760,3] = 9
		v[761,3] = 5
		v[762,3] = 13
		v[763,3] = 7
		v[764,3] = 7
		v[765,3] = 7
		v[766,3] = 1
		v[767,3] = 1
		v[768,3] = 9
		v[769,3] = 9
		v[770,3] = 11
		v[771,3] = 11
		v[772,3] = 15
		v[773,3] = 7
		v[774,3] = 5
		v[775,3] = 5
		v[776,3] = 3
		v[777,3] = 11
		v[778,3] = 1
		v[779,3] = 3
		v[780,3] = 7
		v[781,3] = 13
		v[782,3] = 7
		v[783,3] = 7
		v[784,3] = 7
		v[785,3] = 3
		v[786,3] = 15
		v[787,3] = 15
		v[788,3] = 11
		v[789,3] = 9
		v[790,3] = 3
		v[791,3] = 9
		v[792,3] = 3
		v[793,3] = 15
		v[794,3] = 13
		v[795,3] = 5
		v[796,3] = 3
		v[797,3] = 3
		v[798,3] = 3
		v[799,3] = 5
		v[800,3] = 9
		v[801,3] = 15
		v[802,3] = 9
		v[803,3] = 9
		v[804,3] = 1
		v[805,3] = 5
		v[806,3] = 9
		v[807,3] = 9
		v[808,3] = 15
		v[809,3] = 5
		v[810,3] = 15
		v[811,3] = 7
		v[812,3] = 9
		v[813,3] = 1
		v[814,3] = 9
		v[815,3] = 9
		v[816,3] = 5
		v[817,3] = 11
		v[818,3] = 5
		v[819,3] = 15
		v[820,3] = 15
		v[821,3] = 11
		v[822,3] = 7
		v[823,3] = 7
		v[824,3] = 7
		v[825,3] = 1
		v[826,3] = 1
		v[827,3] = 11
		v[828,3] = 11
		v[829,3] = 13
		v[830,3] = 15
		v[831,3] = 3
		v[832,3] = 13
		v[833,3] = 5
		v[834,3] = 1
		v[835,3] = 7
		v[836,3] = 1
		v[837,3] = 11
		v[838,3] = 3
		v[839,3] = 13
		v[840,3] = 15
		v[841,3] = 3
		v[842,3] = 5
		v[843,3] = 3
		v[844,3] = 5
		v[845,3] = 7
		v[846,3] = 3
		v[847,3] = 9
		v[848,3] = 9
		v[849,3] = 5
		v[850,3] = 1
		v[851,3] = 7
		v[852,3] = 11
		v[853,3] = 9
		v[854,3] = 3
		v[855,3] = 5
		v[856,3] = 11
		v[857,3] = 13
		v[858,3] = 13
		v[859,3] = 13
		v[860,3] = 9
		v[861,3] = 15
		v[862,3] = 5
		v[863,3] = 7
		v[864,3] = 1
		v[865,3] = 15
		v[866,3] = 11
		v[867,3] = 9
		v[868,3] = 15
		v[869,3] = 15
		v[870,3] = 13
		v[871,3] = 13
		v[872,3] = 13
		v[873,3] = 1
		v[874,3] = 11
		v[875,3] = 9
		v[876,3] = 15
		v[877,3] = 9
		v[878,3] = 5
		v[879,3] = 15
		v[880,3] = 5
		v[881,3] = 7
		v[882,3] = 3
		v[883,3] = 11
		v[884,3] = 3
		v[885,3] = 15
		v[886,3] = 7
		v[887,3] = 13
		v[888,3] = 11
		v[889,3] = 7
		v[890,3] = 3
		v[891,3] = 7
		v[892,3] = 13
		v[893,3] = 5
		v[894,3] = 13
		v[895,3] = 15
		v[896,3] = 5
		v[897,3] = 13
		v[898,3] = 9
		v[899,3] = 1
		v[900,3] = 15
		v[901,3] = 11
		v[902,3] = 5
		v[903,3] = 5
		v[904,3] = 1
		v[905,3] = 11
		v[906,3] = 3
		v[907,3] = 3
		v[908,3] = 7
		v[909,3] = 1
		v[910,3] = 9
		v[911,3] = 7
		v[912,3] = 15
		v[913,3] = 9
		v[914,3] = 9
		v[915,3] = 3
		v[916,3] = 11
		v[917,3] = 15
		v[918,3] = 7
		v[919,3] = 1
		v[920,3] = 3
		v[921,3] = 1
		v[922,3] = 1
		v[923,3] = 1
		v[924,3] = 9
		v[925,3] = 1
		v[926,3] = 5
		v[927,3] = 15
		v[928,3] = 15
		v[929,3] = 7
		v[930,3] = 5
		v[931,3] = 5
		v[932,3] = 7
		v[933,3] = 9
		v[934,3] = 7
		v[935,3] = 15
		v[936,3] = 13
		v[937,3] = 13
		v[938,3] = 11
		v[939,3] = 1
		v[940,3] = 9
		v[941,3] = 11
		v[942,3] = 1
		v[943,3] = 13
		v[944,3] = 1
		v[945,3] = 7
		v[946,3] = 15
		v[947,3] = 15
		v[948,3] = 5
		v[949,3] = 5
		v[950,3] = 1
		v[951,3] = 11
		v[952,3] = 3
		v[953,3] = 9
		v[954,3] = 11
		v[955,3] = 9
		v[956,3] = 9
		v[957,3] = 9
		v[958,3] = 1
		v[959,3] = 9
		v[960,3] = 3
		v[961,3] = 5
		v[962,3] = 15
		v[963,3] = 1
		v[964,3] = 1
		v[965,3] = 9
		v[966,3] = 7
		v[967,3] = 3
		v[968,3] = 3
		v[969,3] = 1
		v[970,3] = 9
		v[971,3] = 9
		v[972,3] = 11
		v[973,3] = 9
		v[974,3] = 9
		v[975,3] = 13
		v[976,3] = 13
		v[977,3] = 3
		v[978,3] = 13
		v[979,3] = 11
		v[980,3] = 13
		v[981,3] = 5
		v[982,3] = 1
		v[983,3] = 5
		v[984,3] = 5
		v[985,3] = 9
		v[986,3] = 9
		v[987,3] = 3
		v[988,3] = 13
		v[989,3] = 13
		v[990,3] = 9
		v[991,3] = 15
		v[992,3] = 9
		v[993,3] = 11
		v[994,3] = 7
		v[995,3] = 11
		v[996,3] = 9
		v[997,3] = 13
		v[998,3] = 9
		v[999,3] = 1
		v[1000,3] = 15
		v[1001,3] = 9
		v[1002,3] = 7
		v[1003,3] = 7
		v[1004,3] = 1
		v[1005,3] = 7
		v[1006,3] = 9
		v[1007,3] = 9
		v[1008,3] = 15
		v[1009,3] = 1
		v[1010,3] = 11
		v[1011,3] = 1
		v[1012,3] = 13
		v[1013,3] = 13
		v[1014,3] = 15
		v[1015,3] = 9
		v[1016,3] = 13
		v[1017,3] = 7
		v[1018,3] = 15
		v[1019,3] = 3
		v[1020,3] = 9
		v[1021,3] = 3
		v[1022,3] = 1
		v[1023,3] = 13
		v[1024,3] = 7
		v[1025,3] = 5
		v[1026,3] = 9
		v[1027,3] = 3
		v[1028,3] = 1
		v[1029,3] = 7
		v[1030,3] = 1
		v[1031,3] = 1
		v[1032,3] = 13
		v[1033,3] = 3
		v[1034,3] = 3
		v[1035,3] = 11
		v[1036,3] = 1
		v[1037,3] = 7
		v[1038,3] = 13
		v[1039,3] = 15
		v[1040,3] = 15
		v[1041,3] = 5
		v[1042,3] = 7
		v[1043,3] = 13
		v[1044,3] = 13
		v[1045,3] = 15
		v[1046,3] = 11
		v[1047,3] = 13
		v[1048,3] = 1
		v[1049,3] = 13
		v[1050,3] = 13
		v[1051,3] = 3
		v[1052,3] = 9
		v[1053,3] = 15
		v[1054,3] = 15
		v[1055,3] = 11
		v[1056,3] = 15
		v[1057,3] = 9
		v[1058,3] = 15
		v[1059,3] = 1
		v[1060,3] = 13
		v[1061,3] = 15
		v[1062,3] = 1
		v[1063,3] = 1
		v[1064,3] = 5
		v[1065,3] = 11
		v[1066,3] = 5
		v[1067,3] = 1
		v[1068,3] = 11
		v[1069,3] = 11
		v[1070,3] = 5
		v[1071,3] = 3
		v[1072,3] = 9
		v[1073,3] = 1
		v[1074,3] = 3
		v[1075,3] = 5
		v[1076,3] = 13
		v[1077,3] = 9
		v[1078,3] = 7
		v[1079,3] = 7
		v[1080,3] = 1
		v[1081,3] = 9
		v[1082,3] = 9
		v[1083,3] = 15
		v[1084,3] = 7
		v[1085,3] = 5
		v[1086,3] = 5
		v[1087,3] = 15
		v[1088,3] = 13
		v[1089,3] = 9
		v[1090,3] = 7
		v[1091,3] = 13
		v[1092,3] = 3
		v[1093,3] = 13
		v[1094,3] = 11
		v[1095,3] = 13
		v[1096,3] = 7
		v[1097,3] = 9
		v[1098,3] = 13
		v[1099,3] = 13
		v[1100,3] = 13
		v[1101,3] = 15
		v[1102,3] = 9
		v[1103,3] = 5
		v[1104,3] = 5
		v[1105,3] = 3
		v[1106,3] = 3
		v[1107,3] = 3
		v[1108,3] = 1
		v[1109,3] = 3
		v[1110,3] = 15

		v[7,4] = 9
		v[8,4] = 3
		v[9,4] = 27
		v[10,4] = 15
		v[11,4] = 29
		v[12,4] = 21
		v[13,4] = 23
		v[14,4] = 19
		v[15,4] = 11
		v[16,4] = 25
		v[17,4] = 7
		v[18,4] = 13
		v[19,4] = 17
		v[20,4] = 1
		v[21,4] = 25
		v[22,4] = 29
		v[23,4] = 3
		v[24,4] = 31
		v[25,4] = 11
		v[26,4] = 5
		v[27,4] = 23
		v[28,4] = 27
		v[29,4] = 19
		v[30,4] = 21
		v[31,4] = 5
		v[32,4] = 1
		v[33,4] = 17
		v[34,4] = 13
		v[35,4] = 7
		v[36,4] = 15
		v[37,4] = 9
		v[38,4] = 31
		v[39,4] = 25
		v[40,4] = 3
		v[41,4] = 5
		v[42,4] = 23
		v[43,4] = 7
		v[44,4] = 3
		v[45,4] = 17
		v[46,4] = 23
		v[47,4] = 3
		v[48,4] = 3
		v[49,4] = 21
		v[50,4] = 25
		v[51,4] = 25
		v[52,4] = 23
		v[53,4] = 11
		v[54,4] = 19
		v[55,4] = 3
		v[56,4] = 11
		v[57,4] = 31
		v[58,4] = 7
		v[59,4] = 9
		v[60,4] = 5
		v[61,4] = 17
		v[62,4] = 23
		v[63,4] = 17
		v[64,4] = 17
		v[65,4] = 25
		v[66,4] = 13
		v[67,4] = 11
		v[68,4] = 31
		v[69,4] = 27
		v[70,4] = 19
		v[71,4] = 17
		v[72,4] = 23
		v[73,4] = 7
		v[74,4] = 5
		v[75,4] = 11
		v[76,4] = 19
		v[77,4] = 19
		v[78,4] = 7
		v[79,4] = 13
		v[80,4] = 21
		v[81,4] = 21
		v[82,4] = 7
		v[83,4] = 9
		v[84,4] = 11
		v[85,4] = 1
		v[86,4] = 5
		v[87,4] = 21
		v[88,4] = 11
		v[89,4] = 13
		v[90,4] = 25
		v[91,4] = 9
		v[92,4] = 7
		v[93,4] = 7
		v[94,4] = 27
		v[95,4] = 15
		v[96,4] = 25
		v[97,4] = 15
		v[98,4] = 21
		v[99,4] = 17
		v[100,4] = 19
		v[101,4] = 19
		v[102,4] = 21
		v[103,4] = 5
		v[104,4] = 11
		v[105,4] = 3
		v[106,4] = 5
		v[107,4] = 29
		v[108,4] = 31
		v[109,4] = 29
		v[110,4] = 5
		v[111,4] = 5
		v[112,4] = 1
		v[113,4] = 31
		v[114,4] = 27
		v[115,4] = 11
		v[116,4] = 13
		v[117,4] = 1
		v[118,4] = 3
		v[119,4] = 7
		v[120,4] = 11
		v[121,4] = 7
		v[122,4] = 3
		v[123,4] = 23
		v[124,4] = 13
		v[125,4] = 31
		v[126,4] = 17
		v[127,4] = 1
		v[128,4] = 27
		v[129,4] = 11
		v[130,4] = 25
		v[131,4] = 1
		v[132,4] = 23
		v[133,4] = 29
		v[134,4] = 17
		v[135,4] = 25
		v[136,4] = 7
		v[137,4] = 25
		v[138,4] = 27
		v[139,4] = 17
		v[140,4] = 13
		v[141,4] = 17
		v[142,4] = 23
		v[143,4] = 5
		v[144,4] = 17
		v[145,4] = 5
		v[146,4] = 13
		v[147,4] = 11
		v[148,4] = 21
		v[149,4] = 5
		v[150,4] = 11
		v[151,4] = 5
		v[152,4] = 9
		v[153,4] = 31
		v[154,4] = 19
		v[155,4] = 17
		v[156,4] = 9
		v[157,4] = 9
		v[158,4] = 27
		v[159,4] = 21
		v[160,4] = 15
		v[161,4] = 15
		v[162,4] = 1
		v[163,4] = 1
		v[164,4] = 29
		v[165,4] = 5
		v[166,4] = 31
		v[167,4] = 11
		v[168,4] = 17
		v[169,4] = 23
		v[170,4] = 19
		v[171,4] = 21
		v[172,4] = 25
		v[173,4] = 15
		v[174,4] = 11
		v[175,4] = 5
		v[176,4] = 5
		v[177,4] = 1
		v[178,4] = 19
		v[179,4] = 19
		v[180,4] = 19
		v[181,4] = 7
		v[182,4] = 13
		v[183,4] = 21
		v[184,4] = 17
		v[185,4] = 17
		v[186,4] = 25
		v[187,4] = 23
		v[188,4] = 19
		v[189,4] = 23
		v[190,4] = 15
		v[191,4] = 13
		v[192,4] = 5
		v[193,4] = 19
		v[194,4] = 25
		v[195,4] = 9
		v[196,4] = 7
		v[197,4] = 3
		v[198,4] = 21
		v[199,4] = 17
		v[200,4] = 25
		v[201,4] = 1
		v[202,4] = 27
		v[203,4] = 25
		v[204,4] = 27
		v[205,4] = 25
		v[206,4] = 9
		v[207,4] = 13
		v[208,4] = 3
		v[209,4] = 17
		v[210,4] = 25
		v[211,4] = 23
		v[212,4] = 9
		v[213,4] = 25
		v[214,4] = 9
		v[215,4] = 13
		v[216,4] = 17
		v[217,4] = 17
		v[218,4] = 3
		v[219,4] = 15
		v[220,4] = 7
		v[221,4] = 7
		v[222,4] = 29
		v[223,4] = 3
		v[224,4] = 19
		v[225,4] = 29
		v[226,4] = 29
		v[227,4] = 19
		v[228,4] = 29
		v[229,4] = 13
		v[230,4] = 15
		v[231,4] = 25
		v[232,4] = 27
		v[233,4] = 1
		v[234,4] = 3
		v[235,4] = 9
		v[236,4] = 9
		v[237,4] = 13
		v[238,4] = 31
		v[239,4] = 29
		v[240,4] = 31
		v[241,4] = 5
		v[242,4] = 15
		v[243,4] = 29
		v[244,4] = 1
		v[245,4] = 19
		v[246,4] = 5
		v[247,4] = 9
		v[248,4] = 19
		v[249,4] = 5
		v[250,4] = 15
		v[251,4] = 3
		v[252,4] = 5
		v[253,4] = 7
		v[254,4] = 15
		v[255,4] = 17
		v[256,4] = 17
		v[257,4] = 23
		v[258,4] = 11
		v[259,4] = 9
		v[260,4] = 23
		v[261,4] = 19
		v[262,4] = 3
		v[263,4] = 17
		v[264,4] = 1
		v[265,4] = 27
		v[266,4] = 9
		v[267,4] = 9
		v[268,4] = 17
		v[269,4] = 13
		v[270,4] = 25
		v[271,4] = 29
		v[272,4] = 23
		v[273,4] = 29
		v[274,4] = 11
		v[275,4] = 31
		v[276,4] = 25
		v[277,4] = 21
		v[278,4] = 29
		v[279,4] = 19
		v[280,4] = 27
		v[281,4] = 31
		v[282,4] = 3
		v[283,4] = 5
		v[284,4] = 3
		v[285,4] = 3
		v[286,4] = 13
		v[287,4] = 21
		v[288,4] = 9
		v[289,4] = 29
		v[290,4] = 3
		v[291,4] = 17
		v[292,4] = 11
		v[293,4] = 11
		v[294,4] = 9
		v[295,4] = 21
		v[296,4] = 19
		v[297,4] = 7
		v[298,4] = 17
		v[299,4] = 31
		v[300,4] = 25
		v[301,4] = 1
		v[302,4] = 27
		v[303,4] = 5
		v[304,4] = 15
		v[305,4] = 27
		v[306,4] = 29
		v[307,4] = 29
		v[308,4] = 29
		v[309,4] = 25
		v[310,4] = 27
		v[311,4] = 25
		v[312,4] = 3
		v[313,4] = 21
		v[314,4] = 17
		v[315,4] = 25
		v[316,4] = 13
		v[317,4] = 15
		v[318,4] = 17
		v[319,4] = 13
		v[320,4] = 23
		v[321,4] = 9
		v[322,4] = 3
		v[323,4] = 11
		v[324,4] = 7
		v[325,4] = 9
		v[326,4] = 9
		v[327,4] = 7
		v[328,4] = 17
		v[329,4] = 7
		v[330,4] = 1
		v[331,4] = 27
		v[332,4] = 1
		v[333,4] = 9
		v[334,4] = 5
		v[335,4] = 31
		v[336,4] = 21
		v[337,4] = 25
		v[338,4] = 25
		v[339,4] = 21
		v[340,4] = 11
		v[341,4] = 1
		v[342,4] = 23
		v[343,4] = 19
		v[344,4] = 27
		v[345,4] = 15
		v[346,4] = 3
		v[347,4] = 5
		v[348,4] = 23
		v[349,4] = 9
		v[350,4] = 25
		v[351,4] = 7
		v[352,4] = 29
		v[353,4] = 11
		v[354,4] = 9
		v[355,4] = 13
		v[356,4] = 5
		v[357,4] = 11
		v[358,4] = 1
		v[359,4] = 3
		v[360,4] = 31
		v[361,4] = 27
		v[362,4] = 3
		v[363,4] = 17
		v[364,4] = 27
		v[365,4] = 11
		v[366,4] = 13
		v[367,4] = 15
		v[368,4] = 29
		v[369,4] = 15
		v[370,4] = 1
		v[371,4] = 15
		v[372,4] = 23
		v[373,4] = 25
		v[374,4] = 13
		v[375,4] = 21
		v[376,4] = 15
		v[377,4] = 3
		v[378,4] = 29
		v[379,4] = 29
		v[380,4] = 5
		v[381,4] = 25
		v[382,4] = 17
		v[383,4] = 11
		v[384,4] = 7
		v[385,4] = 15
		v[386,4] = 5
		v[387,4] = 21
		v[388,4] = 7
		v[389,4] = 31
		v[390,4] = 13
		v[391,4] = 11
		v[392,4] = 23
		v[393,4] = 5
		v[394,4] = 7
		v[395,4] = 23
		v[396,4] = 27
		v[397,4] = 21
		v[398,4] = 29
		v[399,4] = 15
		v[400,4] = 7
		v[401,4] = 27
		v[402,4] = 27
		v[403,4] = 19
		v[404,4] = 7
		v[405,4] = 15
		v[406,4] = 27
		v[407,4] = 27
		v[408,4] = 19
		v[409,4] = 19
		v[410,4] = 9
		v[411,4] = 15
		v[412,4] = 1
		v[413,4] = 3
		v[414,4] = 29
		v[415,4] = 29
		v[416,4] = 5
		v[417,4] = 27
		v[418,4] = 31
		v[419,4] = 9
		v[420,4] = 1
		v[421,4] = 7
		v[422,4] = 3
		v[423,4] = 19
		v[424,4] = 19
		v[425,4] = 29
		v[426,4] = 9
		v[427,4] = 3
		v[428,4] = 21
		v[429,4] = 31
		v[430,4] = 29
		v[431,4] = 25
		v[432,4] = 1
		v[433,4] = 3
		v[434,4] = 9
		v[435,4] = 27
		v[436,4] = 5
		v[437,4] = 27
		v[438,4] = 25
		v[439,4] = 21
		v[440,4] = 11
		v[441,4] = 29
		v[442,4] = 31
		v[443,4] = 27
		v[444,4] = 21
		v[445,4] = 29
		v[446,4] = 17
		v[447,4] = 9
		v[448,4] = 17
		v[449,4] = 13
		v[450,4] = 11
		v[451,4] = 25
		v[452,4] = 15
		v[453,4] = 21
		v[454,4] = 11
		v[455,4] = 19
		v[456,4] = 31
		v[457,4] = 3
		v[458,4] = 19
		v[459,4] = 5
		v[460,4] = 3
		v[461,4] = 3
		v[462,4] = 9
		v[463,4] = 13
		v[464,4] = 13
		v[465,4] = 3
		v[466,4] = 29
		v[467,4] = 7
		v[468,4] = 5
		v[469,4] = 9
		v[470,4] = 23
		v[471,4] = 13
		v[472,4] = 21
		v[473,4] = 23
		v[474,4] = 21
		v[475,4] = 31
		v[476,4] = 11
		v[477,4] = 7
		v[478,4] = 7
		v[479,4] = 3
		v[480,4] = 23
		v[481,4] = 1
		v[482,4] = 23
		v[483,4] = 5
		v[484,4] = 9
		v[485,4] = 17
		v[486,4] = 21
		v[487,4] = 1
		v[488,4] = 17
		v[489,4] = 29
		v[490,4] = 7
		v[491,4] = 5
		v[492,4] = 17
		v[493,4] = 13
		v[494,4] = 25
		v[495,4] = 17
		v[496,4] = 9
		v[497,4] = 19
		v[498,4] = 9
		v[499,4] = 5
		v[500,4] = 7
		v[501,4] = 21
		v[502,4] = 19
		v[503,4] = 13
		v[504,4] = 9
		v[505,4] = 7
		v[506,4] = 3
		v[507,4] = 9
		v[508,4] = 3
		v[509,4] = 15
		v[510,4] = 31
		v[511,4] = 29
		v[512,4] = 29
		v[513,4] = 25
		v[514,4] = 13
		v[515,4] = 9
		v[516,4] = 21
		v[517,4] = 9
		v[518,4] = 31
		v[519,4] = 7
		v[520,4] = 15
		v[521,4] = 5
		v[522,4] = 31
		v[523,4] = 7
		v[524,4] = 15
		v[525,4] = 27
		v[526,4] = 25
		v[527,4] = 19
		v[528,4] = 9
		v[529,4] = 9
		v[530,4] = 25
		v[531,4] = 25
		v[532,4] = 23
		v[533,4] = 1
		v[534,4] = 9
		v[535,4] = 7
		v[536,4] = 11
		v[537,4] = 15
		v[538,4] = 19
		v[539,4] = 15
		v[540,4] = 27
		v[541,4] = 17
		v[542,4] = 11
		v[543,4] = 11
		v[544,4] = 31
		v[545,4] = 13
		v[546,4] = 25
		v[547,4] = 25
		v[548,4] = 9
		v[549,4] = 7
		v[550,4] = 13
		v[551,4] = 29
		v[552,4] = 19
		v[553,4] = 5
		v[554,4] = 19
		v[555,4] = 31
		v[556,4] = 25
		v[557,4] = 13
		v[558,4] = 25
		v[559,4] = 15
		v[560,4] = 5
		v[561,4] = 9
		v[562,4] = 29
		v[563,4] = 31
		v[564,4] = 9
		v[565,4] = 29
		v[566,4] = 27
		v[567,4] = 25
		v[568,4] = 27
		v[569,4] = 11
		v[570,4] = 17
		v[571,4] = 5
		v[572,4] = 17
		v[573,4] = 3
		v[574,4] = 23
		v[575,4] = 15
		v[576,4] = 9
		v[577,4] = 9
		v[578,4] = 17
		v[579,4] = 17
		v[580,4] = 31
		v[581,4] = 11
		v[582,4] = 19
		v[583,4] = 25
		v[584,4] = 13
		v[585,4] = 23
		v[586,4] = 15
		v[587,4] = 25
		v[588,4] = 21
		v[589,4] = 31
		v[590,4] = 19
		v[591,4] = 3
		v[592,4] = 11
		v[593,4] = 25
		v[594,4] = 7
		v[595,4] = 15
		v[596,4] = 19
		v[597,4] = 7
		v[598,4] = 5
		v[599,4] = 3
		v[600,4] = 13
		v[601,4] = 13
		v[602,4] = 1
		v[603,4] = 23
		v[604,4] = 5
		v[605,4] = 25
		v[606,4] = 11
		v[607,4] = 25
		v[608,4] = 15
		v[609,4] = 13
		v[610,4] = 21
		v[611,4] = 11
		v[612,4] = 23
		v[613,4] = 29
		v[614,4] = 5
		v[615,4] = 17
		v[616,4] = 27
		v[617,4] = 9
		v[618,4] = 19
		v[619,4] = 15
		v[620,4] = 5
		v[621,4] = 29
		v[622,4] = 23
		v[623,4] = 19
		v[624,4] = 1
		v[625,4] = 27
		v[626,4] = 3
		v[627,4] = 23
		v[628,4] = 21
		v[629,4] = 19
		v[630,4] = 27
		v[631,4] = 11
		v[632,4] = 17
		v[633,4] = 13
		v[634,4] = 27
		v[635,4] = 11
		v[636,4] = 31
		v[637,4] = 23
		v[638,4] = 5
		v[639,4] = 9
		v[640,4] = 21
		v[641,4] = 31
		v[642,4] = 29
		v[643,4] = 11
		v[644,4] = 21
		v[645,4] = 17
		v[646,4] = 15
		v[647,4] = 7
		v[648,4] = 15
		v[649,4] = 7
		v[650,4] = 9
		v[651,4] = 21
		v[652,4] = 27
		v[653,4] = 25
		v[654,4] = 29
		v[655,4] = 11
		v[656,4] = 3
		v[657,4] = 21
		v[658,4] = 13
		v[659,4] = 23
		v[660,4] = 19
		v[661,4] = 27
		v[662,4] = 17
		v[663,4] = 29
		v[664,4] = 25
		v[665,4] = 17
		v[666,4] = 9
		v[667,4] = 1
		v[668,4] = 19
		v[669,4] = 23
		v[670,4] = 5
		v[671,4] = 23
		v[672,4] = 1
		v[673,4] = 17
		v[674,4] = 17
		v[675,4] = 13
		v[676,4] = 27
		v[677,4] = 23
		v[678,4] = 7
		v[679,4] = 7
		v[680,4] = 11
		v[681,4] = 13
		v[682,4] = 17
		v[683,4] = 13
		v[684,4] = 11
		v[685,4] = 21
		v[686,4] = 13
		v[687,4] = 23
		v[688,4] = 1
		v[689,4] = 27
		v[690,4] = 13
		v[691,4] = 9
		v[692,4] = 7
		v[693,4] = 1
		v[694,4] = 27
		v[695,4] = 29
		v[696,4] = 5
		v[697,4] = 13
		v[698,4] = 25
		v[699,4] = 21
		v[700,4] = 3
		v[701,4] = 31
		v[702,4] = 15
		v[703,4] = 13
		v[704,4] = 3
		v[705,4] = 19
		v[706,4] = 13
		v[707,4] = 1
		v[708,4] = 27
		v[709,4] = 15
		v[710,4] = 17
		v[711,4] = 1
		v[712,4] = 3
		v[713,4] = 13
		v[714,4] = 13
		v[715,4] = 13
		v[716,4] = 31
		v[717,4] = 29
		v[718,4] = 27
		v[719,4] = 7
		v[720,4] = 7
		v[721,4] = 21
		v[722,4] = 29
		v[723,4] = 15
		v[724,4] = 17
		v[725,4] = 17
		v[726,4] = 21
		v[727,4] = 19
		v[728,4] = 17
		v[729,4] = 3
		v[730,4] = 15
		v[731,4] = 5
		v[732,4] = 27
		v[733,4] = 27
		v[734,4] = 3
		v[735,4] = 31
		v[736,4] = 31
		v[737,4] = 7
		v[738,4] = 21
		v[739,4] = 3
		v[740,4] = 13
		v[741,4] = 11
		v[742,4] = 17
		v[743,4] = 27
		v[744,4] = 25
		v[745,4] = 1
		v[746,4] = 9
		v[747,4] = 7
		v[748,4] = 29
		v[749,4] = 27
		v[750,4] = 21
		v[751,4] = 23
		v[752,4] = 13
		v[753,4] = 25
		v[754,4] = 29
		v[755,4] = 15
		v[756,4] = 17
		v[757,4] = 29
		v[758,4] = 9
		v[759,4] = 15
		v[760,4] = 3
		v[761,4] = 21
		v[762,4] = 15
		v[763,4] = 17
		v[764,4] = 17
		v[765,4] = 31
		v[766,4] = 9
		v[767,4] = 9
		v[768,4] = 23
		v[769,4] = 19
		v[770,4] = 25
		v[771,4] = 3
		v[772,4] = 1
		v[773,4] = 11
		v[774,4] = 27
		v[775,4] = 29
		v[776,4] = 1
		v[777,4] = 31
		v[778,4] = 29
		v[779,4] = 25
		v[780,4] = 29
		v[781,4] = 1
		v[782,4] = 23
		v[783,4] = 29
		v[784,4] = 25
		v[785,4] = 13
		v[786,4] = 3
		v[787,4] = 31
		v[788,4] = 25
		v[789,4] = 5
		v[790,4] = 5
		v[791,4] = 11
		v[792,4] = 3
		v[793,4] = 21
		v[794,4] = 9
		v[795,4] = 23
		v[796,4] = 7
		v[797,4] = 11
		v[798,4] = 23
		v[799,4] = 11
		v[800,4] = 1
		v[801,4] = 1
		v[802,4] = 3
		v[803,4] = 23
		v[804,4] = 25
		v[805,4] = 23
		v[806,4] = 1
		v[807,4] = 23
		v[808,4] = 3
		v[809,4] = 27
		v[810,4] = 9
		v[811,4] = 27
		v[812,4] = 3
		v[813,4] = 23
		v[814,4] = 25
		v[815,4] = 19
		v[816,4] = 29
		v[817,4] = 29
		v[818,4] = 13
		v[819,4] = 27
		v[820,4] = 5
		v[821,4] = 9
		v[822,4] = 29
		v[823,4] = 29
		v[824,4] = 13
		v[825,4] = 17
		v[826,4] = 3
		v[827,4] = 23
		v[828,4] = 19
		v[829,4] = 7
		v[830,4] = 13
		v[831,4] = 3
		v[832,4] = 19
		v[833,4] = 23
		v[834,4] = 5
		v[835,4] = 29
		v[836,4] = 29
		v[837,4] = 13
		v[838,4] = 13
		v[839,4] = 5
		v[840,4] = 19
		v[841,4] = 5
		v[842,4] = 17
		v[843,4] = 9
		v[844,4] = 11
		v[845,4] = 11
		v[846,4] = 29
		v[847,4] = 27
		v[848,4] = 23
		v[849,4] = 19
		v[850,4] = 17
		v[851,4] = 25
		v[852,4] = 13
		v[853,4] = 1
		v[854,4] = 13
		v[855,4] = 3
		v[856,4] = 11
		v[857,4] = 1
		v[858,4] = 17
		v[859,4] = 29
		v[860,4] = 1
		v[861,4] = 13
		v[862,4] = 17
		v[863,4] = 9
		v[864,4] = 17
		v[865,4] = 21
		v[866,4] = 1
		v[867,4] = 11
		v[868,4] = 1
		v[869,4] = 1
		v[870,4] = 25
		v[871,4] = 5
		v[872,4] = 7
		v[873,4] = 29
		v[874,4] = 29
		v[875,4] = 19
		v[876,4] = 19
		v[877,4] = 1
		v[878,4] = 29
		v[879,4] = 13
		v[880,4] = 3
		v[881,4] = 1
		v[882,4] = 31
		v[883,4] = 15
		v[884,4] = 13
		v[885,4] = 3
		v[886,4] = 1
		v[887,4] = 11
		v[888,4] = 19
		v[889,4] = 5
		v[890,4] = 29
		v[891,4] = 13
		v[892,4] = 29
		v[893,4] = 23
		v[894,4] = 3
		v[895,4] = 1
		v[896,4] = 31
		v[897,4] = 13
		v[898,4] = 19
		v[899,4] = 17
		v[900,4] = 5
		v[901,4] = 5
		v[902,4] = 1
		v[903,4] = 29
		v[904,4] = 23
		v[905,4] = 3
		v[906,4] = 19
		v[907,4] = 25
		v[908,4] = 19
		v[909,4] = 27
		v[910,4] = 9
		v[911,4] = 27
		v[912,4] = 13
		v[913,4] = 15
		v[914,4] = 29
		v[915,4] = 23
		v[916,4] = 13
		v[917,4] = 25
		v[918,4] = 25
		v[919,4] = 17
		v[920,4] = 19
		v[921,4] = 17
		v[922,4] = 15
		v[923,4] = 27
		v[924,4] = 3
		v[925,4] = 25
		v[926,4] = 17
		v[927,4] = 27
		v[928,4] = 3
		v[929,4] = 27
		v[930,4] = 31
		v[931,4] = 23
		v[932,4] = 13
		v[933,4] = 31
		v[934,4] = 11
		v[935,4] = 15
		v[936,4] = 7
		v[937,4] = 21
		v[938,4] = 19
		v[939,4] = 27
		v[940,4] = 19
		v[941,4] = 21
		v[942,4] = 29
		v[943,4] = 7
		v[944,4] = 31
		v[945,4] = 13
		v[946,4] = 9
		v[947,4] = 9
		v[948,4] = 7
		v[949,4] = 21
		v[950,4] = 13
		v[951,4] = 11
		v[952,4] = 9
		v[953,4] = 11
		v[954,4] = 29
		v[955,4] = 19
		v[956,4] = 11
		v[957,4] = 19
		v[958,4] = 21
		v[959,4] = 5
		v[960,4] = 29
		v[961,4] = 13
		v[962,4] = 7
		v[963,4] = 19
		v[964,4] = 19
		v[965,4] = 27
		v[966,4] = 23
		v[967,4] = 31
		v[968,4] = 1
		v[969,4] = 27
		v[970,4] = 21
		v[971,4] = 7
		v[972,4] = 3
		v[973,4] = 7
		v[974,4] = 11
		v[975,4] = 23
		v[976,4] = 13
		v[977,4] = 29
		v[978,4] = 11
		v[979,4] = 31
		v[980,4] = 19
		v[981,4] = 1
		v[982,4] = 5
		v[983,4] = 5
		v[984,4] = 11
		v[985,4] = 5
		v[986,4] = 3
		v[987,4] = 27
		v[988,4] = 5
		v[989,4] = 7
		v[990,4] = 11
		v[991,4] = 31
		v[992,4] = 1
		v[993,4] = 27
		v[994,4] = 31
		v[995,4] = 31
		v[996,4] = 23
		v[997,4] = 5
		v[998,4] = 21
		v[999,4] = 27
		v[1000,4] = 9
		v[1001,4] = 25
		v[1002,4] = 3
		v[1003,4] = 15
		v[1004,4] = 19
		v[1005,4] = 1
		v[1006,4] = 19
		v[1007,4] = 9
		v[1008,4] = 5
		v[1009,4] = 25
		v[1010,4] = 21
		v[1011,4] = 15
		v[1012,4] = 25
		v[1013,4] = 29
		v[1014,4] = 15
		v[1015,4] = 21
		v[1016,4] = 11
		v[1017,4] = 19
		v[1018,4] = 15
		v[1019,4] = 3
		v[1020,4] = 7
		v[1021,4] = 13
		v[1022,4] = 11
		v[1023,4] = 25
		v[1024,4] = 17
		v[1025,4] = 1
		v[1026,4] = 5
		v[1027,4] = 31
		v[1028,4] = 13
		v[1029,4] = 29
		v[1030,4] = 23
		v[1031,4] = 9
		v[1032,4] = 5
		v[1033,4] = 29
		v[1034,4] = 7
		v[1035,4] = 17
		v[1036,4] = 27
		v[1037,4] = 7
		v[1038,4] = 17
		v[1039,4] = 31
		v[1040,4] = 9
		v[1041,4] = 31
		v[1042,4] = 9
		v[1043,4] = 9
		v[1044,4] = 7
		v[1045,4] = 21
		v[1046,4] = 3
		v[1047,4] = 3
		v[1048,4] = 3
		v[1049,4] = 9
		v[1050,4] = 11
		v[1051,4] = 21
		v[1052,4] = 11
		v[1053,4] = 31
		v[1054,4] = 9
		v[1055,4] = 25
		v[1056,4] = 5
		v[1057,4] = 1
		v[1058,4] = 31
		v[1059,4] = 13
		v[1060,4] = 29
		v[1061,4] = 9
		v[1062,4] = 29
		v[1063,4] = 1
		v[1064,4] = 11
		v[1065,4] = 19
		v[1066,4] = 7
		v[1067,4] = 27
		v[1068,4] = 13
		v[1069,4] = 31
		v[1070,4] = 7
		v[1071,4] = 31
		v[1072,4] = 7
		v[1073,4] = 25
		v[1074,4] = 23
		v[1075,4] = 21
		v[1076,4] = 29
		v[1077,4] = 11
		v[1078,4] = 11
		v[1079,4] = 13
		v[1080,4] = 11
		v[1081,4] = 27
		v[1082,4] = 1
		v[1083,4] = 23
		v[1084,4] = 31
		v[1085,4] = 21
		v[1086,4] = 23
		v[1087,4] = 21
		v[1088,4] = 19
		v[1089,4] = 31
		v[1090,4] = 5
		v[1091,4] = 31
		v[1092,4] = 25
		v[1093,4] = 25
		v[1094,4] = 19
		v[1095,4] = 17
		v[1096,4] = 11
		v[1097,4] = 25
		v[1098,4] = 7
		v[1099,4] = 13
		v[1100,4] = 1
		v[1101,4] = 29
		v[1102,4] = 17
		v[1103,4] = 23
		v[1104,4] = 15
		v[1105,4] = 7
		v[1106,4] = 29
		v[1107,4] = 17
		v[1108,4] = 13
		v[1109,4] = 3
		v[1110,4] = 17

		v[13,5] = 37
		v[14,5] = 33
		v[15,5] = 7
		v[16,5] = 5
		v[17,5] = 11
		v[18,5] = 39
		v[19,5] = 63
		v[20,5] = 59
		v[21,5] = 17
		v[22,5] = 15
		v[23,5] = 23
		v[24,5] = 29
		v[25,5] = 3
		v[26,5] = 21
		v[27,5] = 13
		v[28,5] = 31
		v[29,5] = 25
		v[30,5] = 9
		v[31,5] = 49
		v[32,5] = 33
		v[33,5] = 19
		v[34,5] = 29
		v[35,5] = 11
		v[36,5] = 19
		v[37,5] = 27
		v[38,5] = 15
		v[39,5] = 25
		v[40,5] = 63
		v[41,5] = 55
		v[42,5] = 17
		v[43,5] = 63
		v[44,5] = 49
		v[45,5] = 19
		v[46,5] = 41
		v[47,5] = 59
		v[48,5] = 3
		v[49,5] = 57
		v[50,5] = 33
		v[51,5] = 49
		v[52,5] = 53
		v[53,5] = 57
		v[54,5] = 57
		v[55,5] = 39
		v[56,5] = 21
		v[57,5] = 7
		v[58,5] = 53
		v[59,5] = 9
		v[60,5] = 55
		v[61,5] = 15
		v[62,5] = 59
		v[63,5] = 19
		v[64,5] = 49
		v[65,5] = 31
		v[66,5] = 3
		v[67,5] = 39
		v[68,5] = 5
		v[69,5] = 5
		v[70,5] = 41
		v[71,5] = 9
		v[72,5] = 19
		v[73,5] = 9
		v[74,5] = 57
		v[75,5] = 25
		v[76,5] = 1
		v[77,5] = 15
		v[78,5] = 51
		v[79,5] = 11
		v[80,5] = 19
		v[81,5] = 61
		v[82,5] = 53
		v[83,5] = 29
		v[84,5] = 19
		v[85,5] = 11
		v[86,5] = 9
		v[87,5] = 21
		v[88,5] = 19
		v[89,5] = 43
		v[90,5] = 13
		v[91,5] = 13
		v[92,5] = 41
		v[93,5] = 25
		v[94,5] = 31
		v[95,5] = 9
		v[96,5] = 11
		v[97,5] = 19
		v[98,5] = 5
		v[99,5] = 53
		v[100,5] = 37
		v[101,5] = 7
		v[102,5] = 51
		v[103,5] = 45
		v[104,5] = 7
		v[105,5] = 7
		v[106,5] = 61
		v[107,5] = 23
		v[108,5] = 45
		v[109,5] = 7
		v[110,5] = 59
		v[111,5] = 41
		v[112,5] = 1
		v[113,5] = 29
		v[114,5] = 61
		v[115,5] = 37
		v[116,5] = 27
		v[117,5] = 47
		v[118,5] = 15
		v[119,5] = 31
		v[120,5] = 35
		v[121,5] = 31
		v[122,5] = 17
		v[123,5] = 51
		v[124,5] = 13
		v[125,5] = 25
		v[126,5] = 45
		v[127,5] = 5
		v[128,5] = 5
		v[129,5] = 33
		v[130,5] = 39
		v[131,5] = 5
		v[132,5] = 47
		v[133,5] = 29
		v[134,5] = 35
		v[135,5] = 47
		v[136,5] = 63
		v[137,5] = 45
		v[138,5] = 37
		v[139,5] = 47
		v[140,5] = 59
		v[141,5] = 21
		v[142,5] = 59
		v[143,5] = 33
		v[144,5] = 51
		v[145,5] = 9
		v[146,5] = 27
		v[147,5] = 13
		v[148,5] = 25
		v[149,5] = 43
		v[150,5] = 3
		v[151,5] = 17
		v[152,5] = 21
		v[153,5] = 59
		v[154,5] = 61
		v[155,5] = 27
		v[156,5] = 47
		v[157,5] = 57
		v[158,5] = 11
		v[159,5] = 17
		v[160,5] = 39
		v[161,5] = 1
		v[162,5] = 63
		v[163,5] = 21
		v[164,5] = 59
		v[165,5] = 17
		v[166,5] = 13
		v[167,5] = 31
		v[168,5] = 3
		v[169,5] = 31
		v[170,5] = 7
		v[171,5] = 9
		v[172,5] = 27
		v[173,5] = 37
		v[174,5] = 23
		v[175,5] = 31
		v[176,5] = 9
		v[177,5] = 45
		v[178,5] = 43
		v[179,5] = 31
		v[180,5] = 63
		v[181,5] = 21
		v[182,5] = 39
		v[183,5] = 51
		v[184,5] = 27
		v[185,5] = 7
		v[186,5] = 53
		v[187,5] = 11
		v[188,5] = 1
		v[189,5] = 59
		v[190,5] = 39
		v[191,5] = 23
		v[192,5] = 49
		v[193,5] = 23
		v[194,5] = 7
		v[195,5] = 55
		v[196,5] = 59
		v[197,5] = 3
		v[198,5] = 19
		v[199,5] = 35
		v[200,5] = 13
		v[201,5] = 9
		v[202,5] = 13
		v[203,5] = 15
		v[204,5] = 23
		v[205,5] = 9
		v[206,5] = 7
		v[207,5] = 43
		v[208,5] = 55
		v[209,5] = 3
		v[210,5] = 19
		v[211,5] = 9
		v[212,5] = 27
		v[213,5] = 33
		v[214,5] = 27
		v[215,5] = 49
		v[216,5] = 23
		v[217,5] = 47
		v[218,5] = 19
		v[219,5] = 7
		v[220,5] = 11
		v[221,5] = 55
		v[222,5] = 27
		v[223,5] = 35
		v[224,5] = 5
		v[225,5] = 5
		v[226,5] = 55
		v[227,5] = 35
		v[228,5] = 37
		v[229,5] = 9
		v[230,5] = 33
		v[231,5] = 29
		v[232,5] = 47
		v[233,5] = 25
		v[234,5] = 11
		v[235,5] = 47
		v[236,5] = 53
		v[237,5] = 61
		v[238,5] = 59
		v[239,5] = 3
		v[240,5] = 53
		v[241,5] = 47
		v[242,5] = 5
		v[243,5] = 19
		v[244,5] = 59
		v[245,5] = 5
		v[246,5] = 47
		v[247,5] = 23
		v[248,5] = 45
		v[249,5] = 53
		v[250,5] = 3
		v[251,5] = 49
		v[252,5] = 61
		v[253,5] = 47
		v[254,5] = 39
		v[255,5] = 29
		v[256,5] = 17
		v[257,5] = 57
		v[258,5] = 5
		v[259,5] = 17
		v[260,5] = 31
		v[261,5] = 23
		v[262,5] = 41
		v[263,5] = 39
		v[264,5] = 5
		v[265,5] = 27
		v[266,5] = 7
		v[267,5] = 29
		v[268,5] = 29
		v[269,5] = 33
		v[270,5] = 31
		v[271,5] = 41
		v[272,5] = 31
		v[273,5] = 29
		v[274,5] = 17
		v[275,5] = 29
		v[276,5] = 29
		v[277,5] = 9
		v[278,5] = 9
		v[279,5] = 31
		v[280,5] = 27
		v[281,5] = 53
		v[282,5] = 35
		v[283,5] = 5
		v[284,5] = 61
		v[285,5] = 1
		v[286,5] = 49
		v[287,5] = 13
		v[288,5] = 57
		v[289,5] = 29
		v[290,5] = 5
		v[291,5] = 21
		v[292,5] = 43
		v[293,5] = 25
		v[294,5] = 57
		v[295,5] = 49
		v[296,5] = 37
		v[297,5] = 27
		v[298,5] = 11
		v[299,5] = 61
		v[300,5] = 37
		v[301,5] = 49
		v[302,5] = 5
		v[303,5] = 63
		v[304,5] = 63
		v[305,5] = 3
		v[306,5] = 45
		v[307,5] = 37
		v[308,5] = 63
		v[309,5] = 21
		v[310,5] = 21
		v[311,5] = 19
		v[312,5] = 27
		v[313,5] = 59
		v[314,5] = 21
		v[315,5] = 45
		v[316,5] = 23
		v[317,5] = 13
		v[318,5] = 15
		v[319,5] = 3
		v[320,5] = 43
		v[321,5] = 63
		v[322,5] = 39
		v[323,5] = 19
		v[324,5] = 63
		v[325,5] = 31
		v[326,5] = 41
		v[327,5] = 41
		v[328,5] = 15
		v[329,5] = 43
		v[330,5] = 63
		v[331,5] = 53
		v[332,5] = 1
		v[333,5] = 63
		v[334,5] = 31
		v[335,5] = 7
		v[336,5] = 17
		v[337,5] = 11
		v[338,5] = 61
		v[339,5] = 31
		v[340,5] = 51
		v[341,5] = 37
		v[342,5] = 29
		v[343,5] = 59
		v[344,5] = 25
		v[345,5] = 63
		v[346,5] = 59
		v[347,5] = 47
		v[348,5] = 15
		v[349,5] = 27
		v[350,5] = 19
		v[351,5] = 29
		v[352,5] = 45
		v[353,5] = 35
		v[354,5] = 55
		v[355,5] = 39
		v[356,5] = 19
		v[357,5] = 43
		v[358,5] = 21
		v[359,5] = 19
		v[360,5] = 13
		v[361,5] = 17
		v[362,5] = 51
		v[363,5] = 37
		v[364,5] = 5
		v[365,5] = 33
		v[366,5] = 35
		v[367,5] = 49
		v[368,5] = 25
		v[369,5] = 45
		v[370,5] = 1
		v[371,5] = 63
		v[372,5] = 47
		v[373,5] = 9
		v[374,5] = 63
		v[375,5] = 15
		v[376,5] = 25
		v[377,5] = 25
		v[378,5] = 15
		v[379,5] = 41
		v[380,5] = 13
		v[381,5] = 3
		v[382,5] = 19
		v[383,5] = 51
		v[384,5] = 49
		v[385,5] = 37
		v[386,5] = 25
		v[387,5] = 49
		v[388,5] = 13
		v[389,5] = 53
		v[390,5] = 47
		v[391,5] = 23
		v[392,5] = 35
		v[393,5] = 29
		v[394,5] = 33
		v[395,5] = 21
		v[396,5] = 35
		v[397,5] = 23
		v[398,5] = 3
		v[399,5] = 43
		v[400,5] = 31
		v[401,5] = 63
		v[402,5] = 9
		v[403,5] = 1
		v[404,5] = 61
		v[405,5] = 43
		v[406,5] = 3
		v[407,5] = 11
		v[408,5] = 55
		v[409,5] = 11
		v[410,5] = 35
		v[411,5] = 1
		v[412,5] = 63
		v[413,5] = 35
		v[414,5] = 49
		v[415,5] = 19
		v[416,5] = 45
		v[417,5] = 9
		v[418,5] = 57
		v[419,5] = 51
		v[420,5] = 1
		v[421,5] = 47
		v[422,5] = 41
		v[423,5] = 9
		v[424,5] = 11
		v[425,5] = 37
		v[426,5] = 19
		v[427,5] = 55
		v[428,5] = 23
		v[429,5] = 55
		v[430,5] = 55
		v[431,5] = 13
		v[432,5] = 7
		v[433,5] = 47
		v[434,5] = 37
		v[435,5] = 11
		v[436,5] = 43
		v[437,5] = 17
		v[438,5] = 3
		v[439,5] = 25
		v[440,5] = 19
		v[441,5] = 55
		v[442,5] = 59
		v[443,5] = 37
		v[444,5] = 33
		v[445,5] = 43
		v[446,5] = 1
		v[447,5] = 5
		v[448,5] = 21
		v[449,5] = 5
		v[450,5] = 63
		v[451,5] = 49
		v[452,5] = 61
		v[453,5] = 21
		v[454,5] = 51
		v[455,5] = 15
		v[456,5] = 19
		v[457,5] = 43
		v[458,5] = 47
		v[459,5] = 17
		v[460,5] = 9
		v[461,5] = 53
		v[462,5] = 45
		v[463,5] = 11
		v[464,5] = 51
		v[465,5] = 25
		v[466,5] = 11
		v[467,5] = 25
		v[468,5] = 47
		v[469,5] = 47
		v[470,5] = 1
		v[471,5] = 43
		v[472,5] = 29
		v[473,5] = 17
		v[474,5] = 31
		v[475,5] = 15
		v[476,5] = 59
		v[477,5] = 27
		v[478,5] = 63
		v[479,5] = 11
		v[480,5] = 41
		v[481,5] = 51
		v[482,5] = 29
		v[483,5] = 7
		v[484,5] = 27
		v[485,5] = 63
		v[486,5] = 31
		v[487,5] = 43
		v[488,5] = 3
		v[489,5] = 29
		v[490,5] = 39
		v[491,5] = 3
		v[492,5] = 59
		v[493,5] = 59
		v[494,5] = 1
		v[495,5] = 53
		v[496,5] = 63
		v[497,5] = 23
		v[498,5] = 63
		v[499,5] = 47
		v[500,5] = 51
		v[501,5] = 23
		v[502,5] = 61
		v[503,5] = 39
		v[504,5] = 47
		v[505,5] = 21
		v[506,5] = 39
		v[507,5] = 15
		v[508,5] = 3
		v[509,5] = 9
		v[510,5] = 57
		v[511,5] = 61
		v[512,5] = 39
		v[513,5] = 37
		v[514,5] = 21
		v[515,5] = 51
		v[516,5] = 1
		v[517,5] = 23
		v[518,5] = 43
		v[519,5] = 27
		v[520,5] = 25
		v[521,5] = 11
		v[522,5] = 13
		v[523,5] = 21
		v[524,5] = 43
		v[525,5] = 7
		v[526,5] = 11
		v[527,5] = 33
		v[528,5] = 55
		v[529,5] = 1
		v[530,5] = 37
		v[531,5] = 35
		v[532,5] = 27
		v[533,5] = 61
		v[534,5] = 39
		v[535,5] = 5
		v[536,5] = 19
		v[537,5] = 61
		v[538,5] = 61
		v[539,5] = 57
		v[540,5] = 59
		v[541,5] = 21
		v[542,5] = 59
		v[543,5] = 61
		v[544,5] = 57
		v[545,5] = 25
		v[546,5] = 55
		v[547,5] = 27
		v[548,5] = 31
		v[549,5] = 41
		v[550,5] = 33
		v[551,5] = 63
		v[552,5] = 19
		v[553,5] = 57
		v[554,5] = 35
		v[555,5] = 13
		v[556,5] = 63
		v[557,5] = 35
		v[558,5] = 17
		v[559,5] = 11
		v[560,5] = 11
		v[561,5] = 49
		v[562,5] = 41
		v[563,5] = 55
		v[564,5] = 5
		v[565,5] = 45
		v[566,5] = 17
		v[567,5] = 35
		v[568,5] = 5
		v[569,5] = 31
		v[570,5] = 31
		v[571,5] = 37
		v[572,5] = 17
		v[573,5] = 45
		v[574,5] = 51
		v[575,5] = 1
		v[576,5] = 39
		v[577,5] = 49
		v[578,5] = 55
		v[579,5] = 19
		v[580,5] = 41
		v[581,5] = 13
		v[582,5] = 5
		v[583,5] = 51
		v[584,5] = 5
		v[585,5] = 49
		v[586,5] = 1
		v[587,5] = 21
		v[588,5] = 13
		v[589,5] = 17
		v[590,5] = 59
		v[591,5] = 51
		v[592,5] = 11
		v[593,5] = 3
		v[594,5] = 61
		v[595,5] = 1
		v[596,5] = 33
		v[597,5] = 37
		v[598,5] = 33
		v[599,5] = 61
		v[600,5] = 25
		v[601,5] = 27
		v[602,5] = 59
		v[603,5] = 7
		v[604,5] = 49
		v[605,5] = 13
		v[606,5] = 63
		v[607,5] = 3
		v[608,5] = 33
		v[609,5] = 3
		v[610,5] = 15
		v[611,5] = 9
		v[612,5] = 13
		v[613,5] = 35
		v[614,5] = 39
		v[615,5] = 11
		v[616,5] = 59
		v[617,5] = 59
		v[618,5] = 1
		v[619,5] = 57
		v[620,5] = 11
		v[621,5] = 5
		v[622,5] = 57
		v[623,5] = 13
		v[624,5] = 31
		v[625,5] = 13
		v[626,5] = 11
		v[627,5] = 55
		v[628,5] = 45
		v[629,5] = 9
		v[630,5] = 55
		v[631,5] = 55
		v[632,5] = 19
		v[633,5] = 25
		v[634,5] = 41
		v[635,5] = 23
		v[636,5] = 45
		v[637,5] = 29
		v[638,5] = 63
		v[639,5] = 59
		v[640,5] = 27
		v[641,5] = 39
		v[642,5] = 21
		v[643,5] = 37
		v[644,5] = 7
		v[645,5] = 61
		v[646,5] = 49
		v[647,5] = 35
		v[648,5] = 39
		v[649,5] = 9
		v[650,5] = 29
		v[651,5] = 7
		v[652,5] = 25
		v[653,5] = 23
		v[654,5] = 57
		v[655,5] = 5
		v[656,5] = 19
		v[657,5] = 15
		v[658,5] = 33
		v[659,5] = 49
		v[660,5] = 37
		v[661,5] = 25
		v[662,5] = 17
		v[663,5] = 45
		v[664,5] = 29
		v[665,5] = 15
		v[666,5] = 25
		v[667,5] = 3
		v[668,5] = 3
		v[669,5] = 49
		v[670,5] = 11
		v[671,5] = 39
		v[672,5] = 15
		v[673,5] = 19
		v[674,5] = 57
		v[675,5] = 39
		v[676,5] = 15
		v[677,5] = 11
		v[678,5] = 3
		v[679,5] = 57
		v[680,5] = 31
		v[681,5] = 55
		v[682,5] = 61
		v[683,5] = 19
		v[684,5] = 5
		v[685,5] = 41
		v[686,5] = 35
		v[687,5] = 59
		v[688,5] = 61
		v[689,5] = 39
		v[690,5] = 41
		v[691,5] = 53
		v[692,5] = 53
		v[693,5] = 63
		v[694,5] = 31
		v[695,5] = 9
		v[696,5] = 59
		v[697,5] = 13
		v[698,5] = 35
		v[699,5] = 55
		v[700,5] = 41
		v[701,5] = 49
		v[702,5] = 5
		v[703,5] = 41
		v[704,5] = 25
		v[705,5] = 27
		v[706,5] = 43
		v[707,5] = 5
		v[708,5] = 5
		v[709,5] = 43
		v[710,5] = 5
		v[711,5] = 5
		v[712,5] = 17
		v[713,5] = 5
		v[714,5] = 15
		v[715,5] = 27
		v[716,5] = 29
		v[717,5] = 17
		v[718,5] = 9
		v[719,5] = 3
		v[720,5] = 55
		v[721,5] = 31
		v[722,5] = 1
		v[723,5] = 45
		v[724,5] = 45
		v[725,5] = 13
		v[726,5] = 57
		v[727,5] = 17
		v[728,5] = 3
		v[729,5] = 61
		v[730,5] = 15
		v[731,5] = 49
		v[732,5] = 15
		v[733,5] = 47
		v[734,5] = 9
		v[735,5] = 37
		v[736,5] = 45
		v[737,5] = 9
		v[738,5] = 51
		v[739,5] = 61
		v[740,5] = 21
		v[741,5] = 33
		v[742,5] = 11
		v[743,5] = 21
		v[744,5] = 63
		v[745,5] = 63
		v[746,5] = 47
		v[747,5] = 57
		v[748,5] = 61
		v[749,5] = 49
		v[750,5] = 9
		v[751,5] = 59
		v[752,5] = 19
		v[753,5] = 29
		v[754,5] = 21
		v[755,5] = 23
		v[756,5] = 55
		v[757,5] = 23
		v[758,5] = 43
		v[759,5] = 41
		v[760,5] = 57
		v[761,5] = 9
		v[762,5] = 39
		v[763,5] = 27
		v[764,5] = 41
		v[765,5] = 35
		v[766,5] = 61
		v[767,5] = 29
		v[768,5] = 57
		v[769,5] = 63
		v[770,5] = 21
		v[771,5] = 31
		v[772,5] = 59
		v[773,5] = 35
		v[774,5] = 49
		v[775,5] = 3
		v[776,5] = 49
		v[777,5] = 47
		v[778,5] = 49
		v[779,5] = 33
		v[780,5] = 21
		v[781,5] = 19
		v[782,5] = 21
		v[783,5] = 35
		v[784,5] = 11
		v[785,5] = 17
		v[786,5] = 37
		v[787,5] = 23
		v[788,5] = 59
		v[789,5] = 13
		v[790,5] = 37
		v[791,5] = 35
		v[792,5] = 55
		v[793,5] = 57
		v[794,5] = 1
		v[795,5] = 29
		v[796,5] = 45
		v[797,5] = 11
		v[798,5] = 1
		v[799,5] = 15
		v[800,5] = 9
		v[801,5] = 33
		v[802,5] = 19
		v[803,5] = 53
		v[804,5] = 43
		v[805,5] = 39
		v[806,5] = 23
		v[807,5] = 7
		v[808,5] = 13
		v[809,5] = 13
		v[810,5] = 1
		v[811,5] = 19
		v[812,5] = 41
		v[813,5] = 55
		v[814,5] = 1
		v[815,5] = 13
		v[816,5] = 15
		v[817,5] = 59
		v[818,5] = 55
		v[819,5] = 15
		v[820,5] = 3
		v[821,5] = 57
		v[822,5] = 37
		v[823,5] = 31
		v[824,5] = 17
		v[825,5] = 1
		v[826,5] = 3
		v[827,5] = 21
		v[828,5] = 29
		v[829,5] = 25
		v[830,5] = 55
		v[831,5] = 9
		v[832,5] = 37
		v[833,5] = 33
		v[834,5] = 53
		v[835,5] = 41
		v[836,5] = 51
		v[837,5] = 19
		v[838,5] = 57
		v[839,5] = 13
		v[840,5] = 63
		v[841,5] = 43
		v[842,5] = 19
		v[843,5] = 7
		v[844,5] = 13
		v[845,5] = 37
		v[846,5] = 33
		v[847,5] = 19
		v[848,5] = 15
		v[849,5] = 63
		v[850,5] = 51
		v[851,5] = 11
		v[852,5] = 49
		v[853,5] = 23
		v[854,5] = 57
		v[855,5] = 47
		v[856,5] = 51
		v[857,5] = 15
		v[858,5] = 53
		v[859,5] = 41
		v[860,5] = 1
		v[861,5] = 15
		v[862,5] = 37
		v[863,5] = 61
		v[864,5] = 11
		v[865,5] = 35
		v[866,5] = 29
		v[867,5] = 33
		v[868,5] = 23
		v[869,5] = 55
		v[870,5] = 11
		v[871,5] = 59
		v[872,5] = 19
		v[873,5] = 61
		v[874,5] = 61
		v[875,5] = 45
		v[876,5] = 13
		v[877,5] = 49
		v[878,5] = 13
		v[879,5] = 63
		v[880,5] = 5
		v[881,5] = 61
		v[882,5] = 5
		v[883,5] = 31
		v[884,5] = 17
		v[885,5] = 61
		v[886,5] = 63
		v[887,5] = 13
		v[888,5] = 27
		v[889,5] = 57
		v[890,5] = 1
		v[891,5] = 21
		v[892,5] = 5
		v[893,5] = 11
		v[894,5] = 39
		v[895,5] = 57
		v[896,5] = 51
		v[897,5] = 53
		v[898,5] = 39
		v[899,5] = 25
		v[900,5] = 41
		v[901,5] = 39
		v[902,5] = 37
		v[903,5] = 23
		v[904,5] = 31
		v[905,5] = 25
		v[906,5] = 33
		v[907,5] = 17
		v[908,5] = 57
		v[909,5] = 29
		v[910,5] = 27
		v[911,5] = 23
		v[912,5] = 47
		v[913,5] = 41
		v[914,5] = 29
		v[915,5] = 19
		v[916,5] = 47
		v[917,5] = 41
		v[918,5] = 25
		v[919,5] = 5
		v[920,5] = 51
		v[921,5] = 43
		v[922,5] = 39
		v[923,5] = 29
		v[924,5] = 7
		v[925,5] = 31
		v[926,5] = 45
		v[927,5] = 51
		v[928,5] = 49
		v[929,5] = 55
		v[930,5] = 17
		v[931,5] = 43
		v[932,5] = 49
		v[933,5] = 45
		v[934,5] = 9
		v[935,5] = 29
		v[936,5] = 3
		v[937,5] = 5
		v[938,5] = 47
		v[939,5] = 9
		v[940,5] = 15
		v[941,5] = 19
		v[942,5] = 51
		v[943,5] = 45
		v[944,5] = 57
		v[945,5] = 63
		v[946,5] = 9
		v[947,5] = 21
		v[948,5] = 59
		v[949,5] = 3
		v[950,5] = 9
		v[951,5] = 13
		v[952,5] = 45
		v[953,5] = 23
		v[954,5] = 15
		v[955,5] = 31
		v[956,5] = 21
		v[957,5] = 15
		v[958,5] = 51
		v[959,5] = 35
		v[960,5] = 9
		v[961,5] = 11
		v[962,5] = 61
		v[963,5] = 23
		v[964,5] = 53
		v[965,5] = 29
		v[966,5] = 51
		v[967,5] = 45
		v[968,5] = 31
		v[969,5] = 29
		v[970,5] = 5
		v[971,5] = 35
		v[972,5] = 29
		v[973,5] = 53
		v[974,5] = 35
		v[975,5] = 17
		v[976,5] = 59
		v[977,5] = 55
		v[978,5] = 27
		v[979,5] = 51
		v[980,5] = 59
		v[981,5] = 27
		v[982,5] = 47
		v[983,5] = 15
		v[984,5] = 29
		v[985,5] = 37
		v[986,5] = 7
		v[987,5] = 49
		v[988,5] = 55
		v[989,5] = 5
		v[990,5] = 19
		v[991,5] = 45
		v[992,5] = 29
		v[993,5] = 19
		v[994,5] = 57
		v[995,5] = 33
		v[996,5] = 53
		v[997,5] = 45
		v[998,5] = 21
		v[999,5] = 9
		v[1000,5] = 3
		v[1001,5] = 35
		v[1002,5] = 29
		v[1003,5] = 43
		v[1004,5] = 31
		v[1005,5] = 39
		v[1006,5] = 3
		v[1007,5] = 45
		v[1008,5] = 1
		v[1009,5] = 41
		v[1010,5] = 29
		v[1011,5] = 5
		v[1012,5] = 59
		v[1013,5] = 41
		v[1014,5] = 33
		v[1015,5] = 35
		v[1016,5] = 27
		v[1017,5] = 19
		v[1018,5] = 13
		v[1019,5] = 25
		v[1020,5] = 27
		v[1021,5] = 43
		v[1022,5] = 33
		v[1023,5] = 35
		v[1024,5] = 17
		v[1025,5] = 17
		v[1026,5] = 23
		v[1027,5] = 7
		v[1028,5] = 35
		v[1029,5] = 15
		v[1030,5] = 61
		v[1031,5] = 61
		v[1032,5] = 53
		v[1033,5] = 5
		v[1034,5] = 15
		v[1035,5] = 23
		v[1036,5] = 11
		v[1037,5] = 13
		v[1038,5] = 43
		v[1039,5] = 55
		v[1040,5] = 47
		v[1041,5] = 25
		v[1042,5] = 43
		v[1043,5] = 15
		v[1044,5] = 57
		v[1045,5] = 45
		v[1046,5] = 1
		v[1047,5] = 49
		v[1048,5] = 63
		v[1049,5] = 57
		v[1050,5] = 15
		v[1051,5] = 31
		v[1052,5] = 31
		v[1053,5] = 7
		v[1054,5] = 53
		v[1055,5] = 27
		v[1056,5] = 15
		v[1057,5] = 47
		v[1058,5] = 23
		v[1059,5] = 7
		v[1060,5] = 29
		v[1061,5] = 53
		v[1062,5] = 47
		v[1063,5] = 9
		v[1064,5] = 53
		v[1065,5] = 3
		v[1066,5] = 25
		v[1067,5] = 55
		v[1068,5] = 45
		v[1069,5] = 63
		v[1070,5] = 21
		v[1071,5] = 17
		v[1072,5] = 23
		v[1073,5] = 31
		v[1074,5] = 27
		v[1075,5] = 27
		v[1076,5] = 43
		v[1077,5] = 63
		v[1078,5] = 55
		v[1079,5] = 63
		v[1080,5] = 45
		v[1081,5] = 51
		v[1082,5] = 15
		v[1083,5] = 27
		v[1084,5] = 5
		v[1085,5] = 37
		v[1086,5] = 43
		v[1087,5] = 11
		v[1088,5] = 27
		v[1089,5] = 5
		v[1090,5] = 27
		v[1091,5] = 59
		v[1092,5] = 21
		v[1093,5] = 7
		v[1094,5] = 39
		v[1095,5] = 27
		v[1096,5] = 63
		v[1097,5] = 35
		v[1098,5] = 47
		v[1099,5] = 55
		v[1100,5] = 17
		v[1101,5] = 17
		v[1102,5] = 17
		v[1103,5] = 3
		v[1104,5] = 19
		v[1105,5] = 21
		v[1106,5] = 13
		v[1107,5] = 49
		v[1108,5] = 61
		v[1109,5] = 39
		v[1110,5] = 15

		v[19,6] = 13
		v[20,6] = 33
		v[21,6] = 115
		v[22,6] = 41
		v[23,6] = 79
		v[24,6] = 17
		v[25,6] = 29
		v[26,6] = 119
		v[27,6] = 75
		v[28,6] = 73
		v[29,6] = 105
		v[30,6] = 7
		v[31,6] = 59
		v[32,6] = 65
		v[33,6] = 21
		v[34,6] = 3
		v[35,6] = 113
		v[36,6] = 61
		v[37,6] = 89
		v[38,6] = 45
		v[39,6] = 107
		v[40,6] = 21
		v[41,6] = 71
		v[42,6] = 79
		v[43,6] = 19
		v[44,6] = 71
		v[45,6] = 61
		v[46,6] = 41
		v[47,6] = 57
		v[48,6] = 121
		v[49,6] = 87
		v[50,6] = 119
		v[51,6] = 55
		v[52,6] = 85
		v[53,6] = 121
		v[54,6] = 119
		v[55,6] = 11
		v[56,6] = 23
		v[57,6] = 61
		v[58,6] = 11
		v[59,6] = 35
		v[60,6] = 33
		v[61,6] = 43
		v[62,6] = 107
		v[63,6] = 113
		v[64,6] = 101
		v[65,6] = 29
		v[66,6] = 87
		v[67,6] = 119
		v[68,6] = 97
		v[69,6] = 29
		v[70,6] = 17
		v[71,6] = 89
		v[72,6] = 5
		v[73,6] = 127
		v[74,6] = 89
		v[75,6] = 119
		v[76,6] = 117
		v[77,6] = 103
		v[78,6] = 105
		v[79,6] = 41
		v[80,6] = 83
		v[81,6] = 25
		v[82,6] = 41
		v[83,6] = 55
		v[84,6] = 69
		v[85,6] = 117
		v[86,6] = 49
		v[87,6] = 127
		v[88,6] = 29
		v[89,6] = 1
		v[90,6] = 99
		v[91,6] = 53
		v[92,6] = 83
		v[93,6] = 15
		v[94,6] = 31
		v[95,6] = 73
		v[96,6] = 115
		v[97,6] = 35
		v[98,6] = 21
		v[99,6] = 89
		v[100,6] = 5
		v[101,6] = 1
		v[102,6] = 91
		v[103,6] = 53
		v[104,6] = 35
		v[105,6] = 95
		v[106,6] = 83
		v[107,6] = 19
		v[108,6] = 85
		v[109,6] = 55
		v[110,6] = 51
		v[111,6] = 101
		v[112,6] = 33
		v[113,6] = 41
		v[114,6] = 55
		v[115,6] = 45
		v[116,6] = 95
		v[117,6] = 61
		v[118,6] = 27
		v[119,6] = 37
		v[120,6] = 89
		v[121,6] = 75
		v[122,6] = 57
		v[123,6] = 61
		v[124,6] = 15
		v[125,6] = 117
		v[126,6] = 15
		v[127,6] = 21
		v[128,6] = 27
		v[129,6] = 25
		v[130,6] = 27
		v[131,6] = 123
		v[132,6] = 39
		v[133,6] = 109
		v[134,6] = 93
		v[135,6] = 51
		v[136,6] = 21
		v[137,6] = 91
		v[138,6] = 109
		v[139,6] = 107
		v[140,6] = 45
		v[141,6] = 15
		v[142,6] = 93
		v[143,6] = 127
		v[144,6] = 3
		v[145,6] = 53
		v[146,6] = 81
		v[147,6] = 79
		v[148,6] = 107
		v[149,6] = 79
		v[150,6] = 87
		v[151,6] = 35
		v[152,6] = 109
		v[153,6] = 73
		v[154,6] = 35
		v[155,6] = 83
		v[156,6] = 107
		v[157,6] = 1
		v[158,6] = 51
		v[159,6] = 7
		v[160,6] = 59
		v[161,6] = 33
		v[162,6] = 115
		v[163,6] = 43
		v[164,6] = 111
		v[165,6] = 45
		v[166,6] = 121
		v[167,6] = 105
		v[168,6] = 125
		v[169,6] = 87
		v[170,6] = 101
		v[171,6] = 41
		v[172,6] = 95
		v[173,6] = 75
		v[174,6] = 1
		v[175,6] = 57
		v[176,6] = 117
		v[177,6] = 21
		v[178,6] = 27
		v[179,6] = 67
		v[180,6] = 29
		v[181,6] = 53
		v[182,6] = 117
		v[183,6] = 63
		v[184,6] = 1
		v[185,6] = 77
		v[186,6] = 89
		v[187,6] = 115
		v[188,6] = 49
		v[189,6] = 127
		v[190,6] = 15
		v[191,6] = 79
		v[192,6] = 81
		v[193,6] = 29
		v[194,6] = 65
		v[195,6] = 103
		v[196,6] = 33
		v[197,6] = 73
		v[198,6] = 79
		v[199,6] = 29
		v[200,6] = 21
		v[201,6] = 113
		v[202,6] = 31
		v[203,6] = 33
		v[204,6] = 107
		v[205,6] = 95
		v[206,6] = 111
		v[207,6] = 59
		v[208,6] = 99
		v[209,6] = 117
		v[210,6] = 63
		v[211,6] = 63
		v[212,6] = 99
		v[213,6] = 39
		v[214,6] = 9
		v[215,6] = 35
		v[216,6] = 63
		v[217,6] = 125
		v[218,6] = 99
		v[219,6] = 45
		v[220,6] = 93
		v[221,6] = 33
		v[222,6] = 93
		v[223,6] = 9
		v[224,6] = 105
		v[225,6] = 75
		v[226,6] = 51
		v[227,6] = 115
		v[228,6] = 11
		v[229,6] = 37
		v[230,6] = 17
		v[231,6] = 41
		v[232,6] = 21
		v[233,6] = 43
		v[234,6] = 73
		v[235,6] = 19
		v[236,6] = 93
		v[237,6] = 7
		v[238,6] = 95
		v[239,6] = 81
		v[240,6] = 93
		v[241,6] = 79
		v[242,6] = 81
		v[243,6] = 55
		v[244,6] = 9
		v[245,6] = 51
		v[246,6] = 63
		v[247,6] = 45
		v[248,6] = 89
		v[249,6] = 73
		v[250,6] = 19
		v[251,6] = 115
		v[252,6] = 39
		v[253,6] = 47
		v[254,6] = 81
		v[255,6] = 39
		v[256,6] = 5
		v[257,6] = 5
		v[258,6] = 45
		v[259,6] = 53
		v[260,6] = 65
		v[261,6] = 49
		v[262,6] = 17
		v[263,6] = 105
		v[264,6] = 13
		v[265,6] = 107
		v[266,6] = 5
		v[267,6] = 5
		v[268,6] = 19
		v[269,6] = 73
		v[270,6] = 59
		v[271,6] = 43
		v[272,6] = 83
		v[273,6] = 97
		v[274,6] = 115
		v[275,6] = 27
		v[276,6] = 1
		v[277,6] = 69
		v[278,6] = 103
		v[279,6] = 3
		v[280,6] = 99
		v[281,6] = 103
		v[282,6] = 63
		v[283,6] = 67
		v[284,6] = 25
		v[285,6] = 121
		v[286,6] = 97
		v[287,6] = 77
		v[288,6] = 13
		v[289,6] = 83
		v[290,6] = 103
		v[291,6] = 41
		v[292,6] = 11
		v[293,6] = 27
		v[294,6] = 81
		v[295,6] = 37
		v[296,6] = 33
		v[297,6] = 125
		v[298,6] = 71
		v[299,6] = 41
		v[300,6] = 41
		v[301,6] = 59
		v[302,6] = 41
		v[303,6] = 87
		v[304,6] = 123
		v[305,6] = 43
		v[306,6] = 101
		v[307,6] = 63
		v[308,6] = 45
		v[309,6] = 39
		v[310,6] = 21
		v[311,6] = 97
		v[312,6] = 15
		v[313,6] = 97
		v[314,6] = 111
		v[315,6] = 21
		v[316,6] = 49
		v[317,6] = 13
		v[318,6] = 17
		v[319,6] = 79
		v[320,6] = 91
		v[321,6] = 65
		v[322,6] = 105
		v[323,6] = 75
		v[324,6] = 1
		v[325,6] = 45
		v[326,6] = 67
		v[327,6] = 83
		v[328,6] = 107
		v[329,6] = 125
		v[330,6] = 87
		v[331,6] = 15
		v[332,6] = 81
		v[333,6] = 95
		v[334,6] = 105
		v[335,6] = 65
		v[336,6] = 45
		v[337,6] = 59
		v[338,6] = 103
		v[339,6] = 23
		v[340,6] = 103
		v[341,6] = 99
		v[342,6] = 67
		v[343,6] = 99
		v[344,6] = 47
		v[345,6] = 117
		v[346,6] = 71
		v[347,6] = 89
		v[348,6] = 35
		v[349,6] = 53
		v[350,6] = 73
		v[351,6] = 9
		v[352,6] = 115
		v[353,6] = 49
		v[354,6] = 37
		v[355,6] = 1
		v[356,6] = 35
		v[357,6] = 9
		v[358,6] = 45
		v[359,6] = 81
		v[360,6] = 19
		v[361,6] = 127
		v[362,6] = 17
		v[363,6] = 17
		v[364,6] = 105
		v[365,6] = 89
		v[366,6] = 49
		v[367,6] = 101
		v[368,6] = 7
		v[369,6] = 37
		v[370,6] = 33
		v[371,6] = 11
		v[372,6] = 95
		v[373,6] = 95
		v[374,6] = 17
		v[375,6] = 111
		v[376,6] = 105
		v[377,6] = 41
		v[378,6] = 115
		v[379,6] = 5
		v[380,6] = 69
		v[381,6] = 101
		v[382,6] = 27
		v[383,6] = 27
		v[384,6] = 101
		v[385,6] = 103
		v[386,6] = 53
		v[387,6] = 9
		v[388,6] = 21
		v[389,6] = 43
		v[390,6] = 79
		v[391,6] = 91
		v[392,6] = 65
		v[393,6] = 117
		v[394,6] = 87
		v[395,6] = 125
		v[396,6] = 55
		v[397,6] = 45
		v[398,6] = 63
		v[399,6] = 85
		v[400,6] = 83
		v[401,6] = 97
		v[402,6] = 45
		v[403,6] = 83
		v[404,6] = 87
		v[405,6] = 113
		v[406,6] = 93
		v[407,6] = 95
		v[408,6] = 5
		v[409,6] = 17
		v[410,6] = 77
		v[411,6] = 77
		v[412,6] = 127
		v[413,6] = 123
		v[414,6] = 45
		v[415,6] = 81
		v[416,6] = 85
		v[417,6] = 121
		v[418,6] = 119
		v[419,6] = 27
		v[420,6] = 85
		v[421,6] = 41
		v[422,6] = 49
		v[423,6] = 15
		v[424,6] = 107
		v[425,6] = 21
		v[426,6] = 51
		v[427,6] = 119
		v[428,6] = 11
		v[429,6] = 87
		v[430,6] = 101
		v[431,6] = 115
		v[432,6] = 63
		v[433,6] = 63
		v[434,6] = 37
		v[435,6] = 121
		v[436,6] = 109
		v[437,6] = 7
		v[438,6] = 43
		v[439,6] = 69
		v[440,6] = 19
		v[441,6] = 77
		v[442,6] = 49
		v[443,6] = 71
		v[444,6] = 59
		v[445,6] = 35
		v[446,6] = 7
		v[447,6] = 13
		v[448,6] = 55
		v[449,6] = 101
		v[450,6] = 127
		v[451,6] = 103
		v[452,6] = 85
		v[453,6] = 109
		v[454,6] = 29
		v[455,6] = 61
		v[456,6] = 67
		v[457,6] = 21
		v[458,6] = 111
		v[459,6] = 67
		v[460,6] = 23
		v[461,6] = 57
		v[462,6] = 75
		v[463,6] = 71
		v[464,6] = 101
		v[465,6] = 123
		v[466,6] = 41
		v[467,6] = 107
		v[468,6] = 101
		v[469,6] = 107
		v[470,6] = 125
		v[471,6] = 27
		v[472,6] = 47
		v[473,6] = 119
		v[474,6] = 41
		v[475,6] = 19
		v[476,6] = 127
		v[477,6] = 33
		v[478,6] = 31
		v[479,6] = 109
		v[480,6] = 7
		v[481,6] = 91
		v[482,6] = 91
		v[483,6] = 39
		v[484,6] = 125
		v[485,6] = 105
		v[486,6] = 47
		v[487,6] = 125
		v[488,6] = 123
		v[489,6] = 91
		v[490,6] = 9
		v[491,6] = 103
		v[492,6] = 45
		v[493,6] = 23
		v[494,6] = 117
		v[495,6] = 9
		v[496,6] = 125
		v[497,6] = 73
		v[498,6] = 11
		v[499,6] = 37
		v[500,6] = 61
		v[501,6] = 79
		v[502,6] = 21
		v[503,6] = 5
		v[504,6] = 47
		v[505,6] = 117
		v[506,6] = 67
		v[507,6] = 53
		v[508,6] = 85
		v[509,6] = 33
		v[510,6] = 81
		v[511,6] = 121
		v[512,6] = 47
		v[513,6] = 61
		v[514,6] = 51
		v[515,6] = 127
		v[516,6] = 29
		v[517,6] = 65
		v[518,6] = 45
		v[519,6] = 41
		v[520,6] = 95
		v[521,6] = 57
		v[522,6] = 73
		v[523,6] = 33
		v[524,6] = 117
		v[525,6] = 61
		v[526,6] = 111
		v[527,6] = 59
		v[528,6] = 123
		v[529,6] = 65
		v[530,6] = 47
		v[531,6] = 105
		v[532,6] = 23
		v[533,6] = 29
		v[534,6] = 107
		v[535,6] = 37
		v[536,6] = 81
		v[537,6] = 67
		v[538,6] = 29
		v[539,6] = 115
		v[540,6] = 119
		v[541,6] = 75
		v[542,6] = 73
		v[543,6] = 99
		v[544,6] = 103
		v[545,6] = 7
		v[546,6] = 57
		v[547,6] = 45
		v[548,6] = 61
		v[549,6] = 95
		v[550,6] = 49
		v[551,6] = 101
		v[552,6] = 101
		v[553,6] = 35
		v[554,6] = 47
		v[555,6] = 119
		v[556,6] = 39
		v[557,6] = 67
		v[558,6] = 31
		v[559,6] = 103
		v[560,6] = 7
		v[561,6] = 61
		v[562,6] = 127
		v[563,6] = 87
		v[564,6] = 3
		v[565,6] = 35
		v[566,6] = 29
		v[567,6] = 73
		v[568,6] = 95
		v[569,6] = 103
		v[570,6] = 71
		v[571,6] = 75
		v[572,6] = 51
		v[573,6] = 87
		v[574,6] = 57
		v[575,6] = 97
		v[576,6] = 11
		v[577,6] = 105
		v[578,6] = 87
		v[579,6] = 41
		v[580,6] = 73
		v[581,6] = 109
		v[582,6] = 69
		v[583,6] = 35
		v[584,6] = 121
		v[585,6] = 39
		v[586,6] = 111
		v[587,6] = 1
		v[588,6] = 77
		v[589,6] = 39
		v[590,6] = 47
		v[591,6] = 53
		v[592,6] = 91
		v[593,6] = 3
		v[594,6] = 17
		v[595,6] = 51
		v[596,6] = 83
		v[597,6] = 39
		v[598,6] = 125
		v[599,6] = 85
		v[600,6] = 111
		v[601,6] = 21
		v[602,6] = 69
		v[603,6] = 85
		v[604,6] = 29
		v[605,6] = 55
		v[606,6] = 11
		v[607,6] = 117
		v[608,6] = 1
		v[609,6] = 47
		v[610,6] = 17
		v[611,6] = 65
		v[612,6] = 63
		v[613,6] = 47
		v[614,6] = 117
		v[615,6] = 17
		v[616,6] = 115
		v[617,6] = 51
		v[618,6] = 25
		v[619,6] = 33
		v[620,6] = 123
		v[621,6] = 123
		v[622,6] = 83
		v[623,6] = 51
		v[624,6] = 113
		v[625,6] = 95
		v[626,6] = 121
		v[627,6] = 51
		v[628,6] = 91
		v[629,6] = 109
		v[630,6] = 43
		v[631,6] = 55
		v[632,6] = 35
		v[633,6] = 55
		v[634,6] = 87
		v[635,6] = 33
		v[636,6] = 37
		v[637,6] = 5
		v[638,6] = 3
		v[639,6] = 45
		v[640,6] = 21
		v[641,6] = 105
		v[642,6] = 127
		v[643,6] = 35
		v[644,6] = 17
		v[645,6] = 35
		v[646,6] = 37
		v[647,6] = 97
		v[648,6] = 97
		v[649,6] = 21
		v[650,6] = 77
		v[651,6] = 123
		v[652,6] = 17
		v[653,6] = 89
		v[654,6] = 53
		v[655,6] = 105
		v[656,6] = 75
		v[657,6] = 25
		v[658,6] = 125
		v[659,6] = 13
		v[660,6] = 47
		v[661,6] = 21
		v[662,6] = 125
		v[663,6] = 23
		v[664,6] = 55
		v[665,6] = 63
		v[666,6] = 61
		v[667,6] = 5
		v[668,6] = 17
		v[669,6] = 93
		v[670,6] = 57
		v[671,6] = 121
		v[672,6] = 69
		v[673,6] = 73
		v[674,6] = 93
		v[675,6] = 121
		v[676,6] = 105
		v[677,6] = 75
		v[678,6] = 91
		v[679,6] = 67
		v[680,6] = 95
		v[681,6] = 75
		v[682,6] = 9
		v[683,6] = 69
		v[684,6] = 97
		v[685,6] = 99
		v[686,6] = 93
		v[687,6] = 11
		v[688,6] = 53
		v[689,6] = 19
		v[690,6] = 73
		v[691,6] = 5
		v[692,6] = 33
		v[693,6] = 79
		v[694,6] = 107
		v[695,6] = 65
		v[696,6] = 69
		v[697,6] = 79
		v[698,6] = 125
		v[699,6] = 25
		v[700,6] = 93
		v[701,6] = 55
		v[702,6] = 61
		v[703,6] = 17
		v[704,6] = 117
		v[705,6] = 69
		v[706,6] = 97
		v[707,6] = 87
		v[708,6] = 111
		v[709,6] = 37
		v[710,6] = 93
		v[711,6] = 59
		v[712,6] = 79
		v[713,6] = 95
		v[714,6] = 53
		v[715,6] = 115
		v[716,6] = 53
		v[717,6] = 85
		v[718,6] = 85
		v[719,6] = 65
		v[720,6] = 59
		v[721,6] = 23
		v[722,6] = 75
		v[723,6] = 21
		v[724,6] = 67
		v[725,6] = 27
		v[726,6] = 99
		v[727,6] = 79
		v[728,6] = 27
		v[729,6] = 3
		v[730,6] = 95
		v[731,6] = 27
		v[732,6] = 69
		v[733,6] = 19
		v[734,6] = 75
		v[735,6] = 47
		v[736,6] = 59
		v[737,6] = 41
		v[738,6] = 85
		v[739,6] = 77
		v[740,6] = 99
		v[741,6] = 55
		v[742,6] = 49
		v[743,6] = 93
		v[744,6] = 93
		v[745,6] = 119
		v[746,6] = 51
		v[747,6] = 125
		v[748,6] = 63
		v[749,6] = 13
		v[750,6] = 15
		v[751,6] = 45
		v[752,6] = 61
		v[753,6] = 19
		v[754,6] = 105
		v[755,6] = 115
		v[756,6] = 17
		v[757,6] = 83
		v[758,6] = 7
		v[759,6] = 7
		v[760,6] = 11
		v[761,6] = 61
		v[762,6] = 37
		v[763,6] = 63
		v[764,6] = 89
		v[765,6] = 95
		v[766,6] = 119
		v[767,6] = 113
		v[768,6] = 67
		v[769,6] = 123
		v[770,6] = 91
		v[771,6] = 33
		v[772,6] = 37
		v[773,6] = 99
		v[774,6] = 43
		v[775,6] = 11
		v[776,6] = 33
		v[777,6] = 65
		v[778,6] = 81
		v[779,6] = 79
		v[780,6] = 81
		v[781,6] = 107
		v[782,6] = 63
		v[783,6] = 63
		v[784,6] = 55
		v[785,6] = 89
		v[786,6] = 91
		v[787,6] = 25
		v[788,6] = 93
		v[789,6] = 101
		v[790,6] = 27
		v[791,6] = 55
		v[792,6] = 75
		v[793,6] = 121
		v[794,6] = 79
		v[795,6] = 43
		v[796,6] = 125
		v[797,6] = 73
		v[798,6] = 27
		v[799,6] = 109
		v[800,6] = 35
		v[801,6] = 21
		v[802,6] = 71
		v[803,6] = 113
		v[804,6] = 89
		v[805,6] = 59
		v[806,6] = 95
		v[807,6] = 41
		v[808,6] = 45
		v[809,6] = 113
		v[810,6] = 119
		v[811,6] = 113
		v[812,6] = 39
		v[813,6] = 59
		v[814,6] = 73
		v[815,6] = 15
		v[816,6] = 13
		v[817,6] = 59
		v[818,6] = 67
		v[819,6] = 121
		v[820,6] = 27
		v[821,6] = 7
		v[822,6] = 105
		v[823,6] = 15
		v[824,6] = 59
		v[825,6] = 59
		v[826,6] = 35
		v[827,6] = 91
		v[828,6] = 89
		v[829,6] = 23
		v[830,6] = 125
		v[831,6] = 97
		v[832,6] = 53
		v[833,6] = 41
		v[834,6] = 91
		v[835,6] = 111
		v[836,6] = 29
		v[837,6] = 31
		v[838,6] = 3
		v[839,6] = 103
		v[840,6] = 61
		v[841,6] = 71
		v[842,6] = 35
		v[843,6] = 7
		v[844,6] = 119
		v[845,6] = 29
		v[846,6] = 45
		v[847,6] = 49
		v[848,6] = 111
		v[849,6] = 41
		v[850,6] = 109
		v[851,6] = 59
		v[852,6] = 125
		v[853,6] = 13
		v[854,6] = 27
		v[855,6] = 19
		v[856,6] = 79
		v[857,6] = 9
		v[858,6] = 75
		v[859,6] = 83
		v[860,6] = 81
		v[861,6] = 33
		v[862,6] = 91
		v[863,6] = 109
		v[864,6] = 33
		v[865,6] = 29
		v[866,6] = 107
		v[867,6] = 111
		v[868,6] = 101
		v[869,6] = 107
		v[870,6] = 109
		v[871,6] = 65
		v[872,6] = 59
		v[873,6] = 43
		v[874,6] = 37
		v[875,6] = 1
		v[876,6] = 9
		v[877,6] = 15
		v[878,6] = 109
		v[879,6] = 37
		v[880,6] = 111
		v[881,6] = 113
		v[882,6] = 119
		v[883,6] = 79
		v[884,6] = 73
		v[885,6] = 65
		v[886,6] = 71
		v[887,6] = 93
		v[888,6] = 17
		v[889,6] = 101
		v[890,6] = 87
		v[891,6] = 97
		v[892,6] = 43
		v[893,6] = 23
		v[894,6] = 75
		v[895,6] = 109
		v[896,6] = 41
		v[897,6] = 49
		v[898,6] = 53
		v[899,6] = 31
		v[900,6] = 97
		v[901,6] = 105
		v[902,6] = 109
		v[903,6] = 119
		v[904,6] = 51
		v[905,6] = 9
		v[906,6] = 53
		v[907,6] = 113
		v[908,6] = 97
		v[909,6] = 73
		v[910,6] = 89
		v[911,6] = 79
		v[912,6] = 49
		v[913,6] = 61
		v[914,6] = 105
		v[915,6] = 13
		v[916,6] = 99
		v[917,6] = 53
		v[918,6] = 71
		v[919,6] = 7
		v[920,6] = 87
		v[921,6] = 21
		v[922,6] = 101
		v[923,6] = 5
		v[924,6] = 71
		v[925,6] = 31
		v[926,6] = 123
		v[927,6] = 121
		v[928,6] = 121
		v[929,6] = 73
		v[930,6] = 79
		v[931,6] = 115
		v[932,6] = 13
		v[933,6] = 39
		v[934,6] = 101
		v[935,6] = 19
		v[936,6] = 37
		v[937,6] = 51
		v[938,6] = 83
		v[939,6] = 97
		v[940,6] = 55
		v[941,6] = 81
		v[942,6] = 91
		v[943,6] = 127
		v[944,6] = 105
		v[945,6] = 89
		v[946,6] = 63
		v[947,6] = 47
		v[948,6] = 49
		v[949,6] = 75
		v[950,6] = 37
		v[951,6] = 77
		v[952,6] = 15
		v[953,6] = 49
		v[954,6] = 107
		v[955,6] = 23
		v[956,6] = 23
		v[957,6] = 35
		v[958,6] = 19
		v[959,6] = 69
		v[960,6] = 17
		v[961,6] = 59
		v[962,6] = 63
		v[963,6] = 73
		v[964,6] = 29
		v[965,6] = 125
		v[966,6] = 61
		v[967,6] = 65
		v[968,6] = 95
		v[969,6] = 101
		v[970,6] = 81
		v[971,6] = 57
		v[972,6] = 69
		v[973,6] = 83
		v[974,6] = 37
		v[975,6] = 11
		v[976,6] = 37
		v[977,6] = 95
		v[978,6] = 1
		v[979,6] = 73
		v[980,6] = 27
		v[981,6] = 29
		v[982,6] = 57
		v[983,6] = 7
		v[984,6] = 65
		v[985,6] = 83
		v[986,6] = 99
		v[987,6] = 69
		v[988,6] = 19
		v[989,6] = 103
		v[990,6] = 43
		v[991,6] = 95
		v[992,6] = 25
		v[993,6] = 19
		v[994,6] = 103
		v[995,6] = 41
		v[996,6] = 125
		v[997,6] = 97
		v[998,6] = 71
		v[999,6] = 105
		v[1000,6] = 83
		v[1001,6] = 83
		v[1002,6] = 61
		v[1003,6] = 39
		v[1004,6] = 9
		v[1005,6] = 45
		v[1006,6] = 117
		v[1007,6] = 63
		v[1008,6] = 31
		v[1009,6] = 5
		v[1010,6] = 117
		v[1011,6] = 67
		v[1012,6] = 125
		v[1013,6] = 41
		v[1014,6] = 117
		v[1015,6] = 43
		v[1016,6] = 77
		v[1017,6] = 97
		v[1018,6] = 15
		v[1019,6] = 29
		v[1020,6] = 5
		v[1021,6] = 59
		v[1022,6] = 25
		v[1023,6] = 63
		v[1024,6] = 87
		v[1025,6] = 39
		v[1026,6] = 39
		v[1027,6] = 77
		v[1028,6] = 85
		v[1029,6] = 37
		v[1030,6] = 81
		v[1031,6] = 73
		v[1032,6] = 89
		v[1033,6] = 29
		v[1034,6] = 125
		v[1035,6] = 109
		v[1036,6] = 21
		v[1037,6] = 23
		v[1038,6] = 119
		v[1039,6] = 105
		v[1040,6] = 43
		v[1041,6] = 93
		v[1042,6] = 97
		v[1043,6] = 15
		v[1044,6] = 125
		v[1045,6] = 29
		v[1046,6] = 51
		v[1047,6] = 69
		v[1048,6] = 37
		v[1049,6] = 45
		v[1050,6] = 31
		v[1051,6] = 75
		v[1052,6] = 109
		v[1053,6] = 119
		v[1054,6] = 53
		v[1055,6] = 5
		v[1056,6] = 101
		v[1057,6] = 125
		v[1058,6] = 121
		v[1059,6] = 35
		v[1060,6] = 29
		v[1061,6] = 7
		v[1062,6] = 63
		v[1063,6] = 17
		v[1064,6] = 63
		v[1065,6] = 13
		v[1066,6] = 69
		v[1067,6] = 15
		v[1068,6] = 105
		v[1069,6] = 51
		v[1070,6] = 127
		v[1071,6] = 105
		v[1072,6] = 9
		v[1073,6] = 57
		v[1074,6] = 95
		v[1075,6] = 59
		v[1076,6] = 109
		v[1077,6] = 35
		v[1078,6] = 49
		v[1079,6] = 23
		v[1080,6] = 33
		v[1081,6] = 107
		v[1082,6] = 55
		v[1083,6] = 33
		v[1084,6] = 57
		v[1085,6] = 79
		v[1086,6] = 73
		v[1087,6] = 69
		v[1088,6] = 59
		v[1089,6] = 107
		v[1090,6] = 55
		v[1091,6] = 11
		v[1092,6] = 63
		v[1093,6] = 95
		v[1094,6] = 103
		v[1095,6] = 23
		v[1096,6] = 125
		v[1097,6] = 91
		v[1098,6] = 31
		v[1099,6] = 91
		v[1100,6] = 51
		v[1101,6] = 65
		v[1102,6] = 61
		v[1103,6] = 75
		v[1104,6] = 69
		v[1105,6] = 107
		v[1106,6] = 65
		v[1107,6] = 101
		v[1108,6] = 59
		v[1109,6] = 35
		v[1110,6] = 15

		v[37,7] = 7
		v[38,7] = 23
		v[39,7] = 39
		v[40,7] = 217
		v[41,7] = 141
		v[42,7] = 27
		v[43,7] = 53
		v[44,7] = 181
		v[45,7] = 169
		v[46,7] = 35
		v[47,7] = 15
		v[48,7] = 207
		v[49,7] = 45
		v[50,7] = 247
		v[51,7] = 185
		v[52,7] = 117
		v[53,7] = 41
		v[54,7] = 81
		v[55,7] = 223
		v[56,7] = 151
		v[57,7] = 81
		v[58,7] = 189
		v[59,7] = 61
		v[60,7] = 95
		v[61,7] = 185
		v[62,7] = 23
		v[63,7] = 73
		v[64,7] = 113
		v[65,7] = 239
		v[66,7] = 85
		v[67,7] = 9
		v[68,7] = 201
		v[69,7] = 83
		v[70,7] = 53
		v[71,7] = 183
		v[72,7] = 203
		v[73,7] = 91
		v[74,7] = 149
		v[75,7] = 101
		v[76,7] = 13
		v[77,7] = 111
		v[78,7] = 239
		v[79,7] = 3
		v[80,7] = 205
		v[81,7] = 253
		v[82,7] = 247
		v[83,7] = 121
		v[84,7] = 189
		v[85,7] = 169
		v[86,7] = 179
		v[87,7] = 197
		v[88,7] = 175
		v[89,7] = 217
		v[90,7] = 249
		v[91,7] = 195
		v[92,7] = 95
		v[93,7] = 63
		v[94,7] = 19
		v[95,7] = 7
		v[96,7] = 5
		v[97,7] = 75
		v[98,7] = 217
		v[99,7] = 245
		v[100,7] = 111
		v[101,7] = 189
		v[102,7] = 165
		v[103,7] = 169
		v[104,7] = 141
		v[105,7] = 221
		v[106,7] = 249
		v[107,7] = 159
		v[108,7] = 253
		v[109,7] = 207
		v[110,7] = 249
		v[111,7] = 219
		v[112,7] = 23
		v[113,7] = 49
		v[114,7] = 127
		v[115,7] = 237
		v[116,7] = 5
		v[117,7] = 25
		v[118,7] = 177
		v[119,7] = 37
		v[120,7] = 103
		v[121,7] = 65
		v[122,7] = 167
		v[123,7] = 81
		v[124,7] = 87
		v[125,7] = 119
		v[126,7] = 45
		v[127,7] = 79
		v[128,7] = 143
		v[129,7] = 57
		v[130,7] = 79
		v[131,7] = 187
		v[132,7] = 143
		v[133,7] = 183
		v[134,7] = 75
		v[135,7] = 97
		v[136,7] = 211
		v[137,7] = 149
		v[138,7] = 175
		v[139,7] = 37
		v[140,7] = 135
		v[141,7] = 189
		v[142,7] = 225
		v[143,7] = 241
		v[144,7] = 63
		v[145,7] = 33
		v[146,7] = 43
		v[147,7] = 13
		v[148,7] = 73
		v[149,7] = 213
		v[150,7] = 57
		v[151,7] = 239
		v[152,7] = 183
		v[153,7] = 117
		v[154,7] = 21
		v[155,7] = 29
		v[156,7] = 115
		v[157,7] = 43
		v[158,7] = 205
		v[159,7] = 223
		v[160,7] = 15
		v[161,7] = 3
		v[162,7] = 159
		v[163,7] = 51
		v[164,7] = 101
		v[165,7] = 127
		v[166,7] = 99
		v[167,7] = 239
		v[168,7] = 171
		v[169,7] = 113
		v[170,7] = 171
		v[171,7] = 119
		v[172,7] = 189
		v[173,7] = 245
		v[174,7] = 201
		v[175,7] = 27
		v[176,7] = 185
		v[177,7] = 229
		v[178,7] = 105
		v[179,7] = 153
		v[180,7] = 189
		v[181,7] = 33
		v[182,7] = 35
		v[183,7] = 137
		v[184,7] = 77
		v[185,7] = 97
		v[186,7] = 17
		v[187,7] = 181
		v[188,7] = 55
		v[189,7] = 197
		v[190,7] = 201
		v[191,7] = 155
		v[192,7] = 37
		v[193,7] = 197
		v[194,7] = 137
		v[195,7] = 223
		v[196,7] = 25
		v[197,7] = 179
		v[198,7] = 91
		v[199,7] = 23
		v[200,7] = 235
		v[201,7] = 53
		v[202,7] = 253
		v[203,7] = 49
		v[204,7] = 181
		v[205,7] = 249
		v[206,7] = 53
		v[207,7] = 173
		v[208,7] = 97
		v[209,7] = 247
		v[210,7] = 67
		v[211,7] = 115
		v[212,7] = 103
		v[213,7] = 159
		v[214,7] = 239
		v[215,7] = 69
		v[216,7] = 173
		v[217,7] = 217
		v[218,7] = 95
		v[219,7] = 221
		v[220,7] = 247
		v[221,7] = 97
		v[222,7] = 91
		v[223,7] = 123
		v[224,7] = 223
		v[225,7] = 213
		v[226,7] = 129
		v[227,7] = 181
		v[228,7] = 87
		v[229,7] = 239
		v[230,7] = 85
		v[231,7] = 89
		v[232,7] = 249
		v[233,7] = 141
		v[234,7] = 39
		v[235,7] = 57
		v[236,7] = 249
		v[237,7] = 71
		v[238,7] = 101
		v[239,7] = 159
		v[240,7] = 33
		v[241,7] = 137
		v[242,7] = 189
		v[243,7] = 71
		v[244,7] = 253
		v[245,7] = 205
		v[246,7] = 171
		v[247,7] = 13
		v[248,7] = 249
		v[249,7] = 109
		v[250,7] = 131
		v[251,7] = 199
		v[252,7] = 189
		v[253,7] = 179
		v[254,7] = 31
		v[255,7] = 99
		v[256,7] = 113
		v[257,7] = 41
		v[258,7] = 173
		v[259,7] = 23
		v[260,7] = 189
		v[261,7] = 197
		v[262,7] = 3
		v[263,7] = 135
		v[264,7] = 9
		v[265,7] = 95
		v[266,7] = 195
		v[267,7] = 27
		v[268,7] = 183
		v[269,7] = 1
		v[270,7] = 123
		v[271,7] = 73
		v[272,7] = 53
		v[273,7] = 99
		v[274,7] = 197
		v[275,7] = 59
		v[276,7] = 27
		v[277,7] = 101
		v[278,7] = 55
		v[279,7] = 193
		v[280,7] = 31
		v[281,7] = 61
		v[282,7] = 119
		v[283,7] = 11
		v[284,7] = 7
		v[285,7] = 255
		v[286,7] = 233
		v[287,7] = 53
		v[288,7] = 157
		v[289,7] = 193
		v[290,7] = 97
		v[291,7] = 83
		v[292,7] = 65
		v[293,7] = 81
		v[294,7] = 239
		v[295,7] = 167
		v[296,7] = 69
		v[297,7] = 71
		v[298,7] = 109
		v[299,7] = 97
		v[300,7] = 137
		v[301,7] = 71
		v[302,7] = 193
		v[303,7] = 189
		v[304,7] = 115
		v[305,7] = 79
		v[306,7] = 205
		v[307,7] = 37
		v[308,7] = 227
		v[309,7] = 53
		v[310,7] = 33
		v[311,7] = 91
		v[312,7] = 229
		v[313,7] = 245
		v[314,7] = 105
		v[315,7] = 77
		v[316,7] = 229
		v[317,7] = 161
		v[318,7] = 103
		v[319,7] = 93
		v[320,7] = 13
		v[321,7] = 161
		v[322,7] = 229
		v[323,7] = 223
		v[324,7] = 69
		v[325,7] = 15
		v[326,7] = 25
		v[327,7] = 23
		v[328,7] = 233
		v[329,7] = 93
		v[330,7] = 25
		v[331,7] = 217
		v[332,7] = 247
		v[333,7] = 61
		v[334,7] = 75
		v[335,7] = 27
		v[336,7] = 9
		v[337,7] = 223
		v[338,7] = 213
		v[339,7] = 55
		v[340,7] = 197
		v[341,7] = 145
		v[342,7] = 89
		v[343,7] = 199
		v[344,7] = 41
		v[345,7] = 201
		v[346,7] = 5
		v[347,7] = 149
		v[348,7] = 35
		v[349,7] = 119
		v[350,7] = 183
		v[351,7] = 53
		v[352,7] = 11
		v[353,7] = 13
		v[354,7] = 3
		v[355,7] = 179
		v[356,7] = 229
		v[357,7] = 43
		v[358,7] = 55
		v[359,7] = 187
		v[360,7] = 233
		v[361,7] = 47
		v[362,7] = 133
		v[363,7] = 91
		v[364,7] = 47
		v[365,7] = 71
		v[366,7] = 93
		v[367,7] = 105
		v[368,7] = 145
		v[369,7] = 45
		v[370,7] = 255
		v[371,7] = 221
		v[372,7] = 115
		v[373,7] = 175
		v[374,7] = 19
		v[375,7] = 129
		v[376,7] = 5
		v[377,7] = 209
		v[378,7] = 197
		v[379,7] = 57
		v[380,7] = 177
		v[381,7] = 115
		v[382,7] = 187
		v[383,7] = 119
		v[384,7] = 77
		v[385,7] = 211
		v[386,7] = 111
		v[387,7] = 33
		v[388,7] = 113
		v[389,7] = 23
		v[390,7] = 87
		v[391,7] = 137
		v[392,7] = 41
		v[393,7] = 7
		v[394,7] = 83
		v[395,7] = 43
		v[396,7] = 121
		v[397,7] = 145
		v[398,7] = 5
		v[399,7] = 219
		v[400,7] = 27
		v[401,7] = 11
		v[402,7] = 111
		v[403,7] = 207
		v[404,7] = 55
		v[405,7] = 97
		v[406,7] = 63
		v[407,7] = 229
		v[408,7] = 53
		v[409,7] = 33
		v[410,7] = 149
		v[411,7] = 23
		v[412,7] = 187
		v[413,7] = 153
		v[414,7] = 91
		v[415,7] = 193
		v[416,7] = 183
		v[417,7] = 59
		v[418,7] = 211
		v[419,7] = 93
		v[420,7] = 139
		v[421,7] = 59
		v[422,7] = 179
		v[423,7] = 163
		v[424,7] = 209
		v[425,7] = 77
		v[426,7] = 39
		v[427,7] = 111
		v[428,7] = 79
		v[429,7] = 229
		v[430,7] = 85
		v[431,7] = 237
		v[432,7] = 199
		v[433,7] = 137
		v[434,7] = 147
		v[435,7] = 25
		v[436,7] = 73
		v[437,7] = 121
		v[438,7] = 129
		v[439,7] = 83
		v[440,7] = 87
		v[441,7] = 93
		v[442,7] = 205
		v[443,7] = 167
		v[444,7] = 53
		v[445,7] = 107
		v[446,7] = 229
		v[447,7] = 213
		v[448,7] = 95
		v[449,7] = 219
		v[450,7] = 109
		v[451,7] = 175
		v[452,7] = 13
		v[453,7] = 209
		v[454,7] = 97
		v[455,7] = 61
		v[456,7] = 147
		v[457,7] = 19
		v[458,7] = 13
		v[459,7] = 123
		v[460,7] = 73
		v[461,7] = 35
		v[462,7] = 141
		v[463,7] = 81
		v[464,7] = 19
		v[465,7] = 171
		v[466,7] = 255
		v[467,7] = 111
		v[468,7] = 107
		v[469,7] = 233
		v[470,7] = 113
		v[471,7] = 133
		v[472,7] = 89
		v[473,7] = 9
		v[474,7] = 231
		v[475,7] = 95
		v[476,7] = 69
		v[477,7] = 33
		v[478,7] = 1
		v[479,7] = 253
		v[480,7] = 219
		v[481,7] = 253
		v[482,7] = 247
		v[483,7] = 129
		v[484,7] = 11
		v[485,7] = 251
		v[486,7] = 221
		v[487,7] = 153
		v[488,7] = 35
		v[489,7] = 103
		v[490,7] = 239
		v[491,7] = 7
		v[492,7] = 27
		v[493,7] = 235
		v[494,7] = 181
		v[495,7] = 5
		v[496,7] = 207
		v[497,7] = 53
		v[498,7] = 149
		v[499,7] = 155
		v[500,7] = 225
		v[501,7] = 165
		v[502,7] = 137
		v[503,7] = 155
		v[504,7] = 201
		v[505,7] = 97
		v[506,7] = 245
		v[507,7] = 203
		v[508,7] = 47
		v[509,7] = 39
		v[510,7] = 35
		v[511,7] = 105
		v[512,7] = 239
		v[513,7] = 49
		v[514,7] = 15
		v[515,7] = 253
		v[516,7] = 7
		v[517,7] = 237
		v[518,7] = 213
		v[519,7] = 55
		v[520,7] = 87
		v[521,7] = 199
		v[522,7] = 27
		v[523,7] = 175
		v[524,7] = 49
		v[525,7] = 41
		v[526,7] = 229
		v[527,7] = 85
		v[528,7] = 3
		v[529,7] = 149
		v[530,7] = 179
		v[531,7] = 129
		v[532,7] = 185
		v[533,7] = 249
		v[534,7] = 197
		v[535,7] = 15
		v[536,7] = 97
		v[537,7] = 197
		v[538,7] = 139
		v[539,7] = 203
		v[540,7] = 63
		v[541,7] = 33
		v[542,7] = 251
		v[543,7] = 217
		v[544,7] = 199
		v[545,7] = 199
		v[546,7] = 99
		v[547,7] = 249
		v[548,7] = 33
		v[549,7] = 229
		v[550,7] = 177
		v[551,7] = 13
		v[552,7] = 209
		v[553,7] = 147
		v[554,7] = 97
		v[555,7] = 31
		v[556,7] = 125
		v[557,7] = 177
		v[558,7] = 137
		v[559,7] = 187
		v[560,7] = 11
		v[561,7] = 91
		v[562,7] = 223
		v[563,7] = 29
		v[564,7] = 169
		v[565,7] = 231
		v[566,7] = 59
		v[567,7] = 31
		v[568,7] = 163
		v[569,7] = 41
		v[570,7] = 57
		v[571,7] = 87
		v[572,7] = 247
		v[573,7] = 25
		v[574,7] = 127
		v[575,7] = 101
		v[576,7] = 207
		v[577,7] = 187
		v[578,7] = 73
		v[579,7] = 61
		v[580,7] = 105
		v[581,7] = 27
		v[582,7] = 91
		v[583,7] = 171
		v[584,7] = 243
		v[585,7] = 33
		v[586,7] = 3
		v[587,7] = 1
		v[588,7] = 21
		v[589,7] = 229
		v[590,7] = 93
		v[591,7] = 71
		v[592,7] = 61
		v[593,7] = 37
		v[594,7] = 183
		v[595,7] = 65
		v[596,7] = 211
		v[597,7] = 53
		v[598,7] = 11
		v[599,7] = 151
		v[600,7] = 165
		v[601,7] = 47
		v[602,7] = 5
		v[603,7] = 129
		v[604,7] = 79
		v[605,7] = 101
		v[606,7] = 147
		v[607,7] = 169
		v[608,7] = 181
		v[609,7] = 19
		v[610,7] = 95
		v[611,7] = 77
		v[612,7] = 139
		v[613,7] = 197
		v[614,7] = 219
		v[615,7] = 97
		v[616,7] = 239
		v[617,7] = 183
		v[618,7] = 143
		v[619,7] = 9
		v[620,7] = 13
		v[621,7] = 209
		v[622,7] = 23
		v[623,7] = 215
		v[624,7] = 53
		v[625,7] = 137
		v[626,7] = 203
		v[627,7] = 19
		v[628,7] = 151
		v[629,7] = 171
		v[630,7] = 133
		v[631,7] = 219
		v[632,7] = 231
		v[633,7] = 3
		v[634,7] = 15
		v[635,7] = 253
		v[636,7] = 225
		v[637,7] = 33
		v[638,7] = 111
		v[639,7] = 183
		v[640,7] = 213
		v[641,7] = 169
		v[642,7] = 119
		v[643,7] = 111
		v[644,7] = 15
		v[645,7] = 201
		v[646,7] = 123
		v[647,7] = 121
		v[648,7] = 225
		v[649,7] = 113
		v[650,7] = 113
		v[651,7] = 225
		v[652,7] = 161
		v[653,7] = 165
		v[654,7] = 1
		v[655,7] = 139
		v[656,7] = 55
		v[657,7] = 3
		v[658,7] = 93
		v[659,7] = 217
		v[660,7] = 193
		v[661,7] = 97
		v[662,7] = 29
		v[663,7] = 69
		v[664,7] = 231
		v[665,7] = 161
		v[666,7] = 93
		v[667,7] = 69
		v[668,7] = 143
		v[669,7] = 137
		v[670,7] = 9
		v[671,7] = 87
		v[672,7] = 183
		v[673,7] = 113
		v[674,7] = 183
		v[675,7] = 73
		v[676,7] = 215
		v[677,7] = 137
		v[678,7] = 89
		v[679,7] = 251
		v[680,7] = 163
		v[681,7] = 41
		v[682,7] = 227
		v[683,7] = 145
		v[684,7] = 57
		v[685,7] = 81
		v[686,7] = 57
		v[687,7] = 11
		v[688,7] = 135
		v[689,7] = 145
		v[690,7] = 161
		v[691,7] = 175
		v[692,7] = 159
		v[693,7] = 25
		v[694,7] = 55
		v[695,7] = 167
		v[696,7] = 157
		v[697,7] = 211
		v[698,7] = 97
		v[699,7] = 247
		v[700,7] = 249
		v[701,7] = 23
		v[702,7] = 129
		v[703,7] = 159
		v[704,7] = 71
		v[705,7] = 197
		v[706,7] = 127
		v[707,7] = 141
		v[708,7] = 219
		v[709,7] = 5
		v[710,7] = 233
		v[711,7] = 131
		v[712,7] = 217
		v[713,7] = 101
		v[714,7] = 131
		v[715,7] = 33
		v[716,7] = 157
		v[717,7] = 173
		v[718,7] = 69
		v[719,7] = 207
		v[720,7] = 239
		v[721,7] = 81
		v[722,7] = 205
		v[723,7] = 11
		v[724,7] = 41
		v[725,7] = 169
		v[726,7] = 65
		v[727,7] = 193
		v[728,7] = 77
		v[729,7] = 201
		v[730,7] = 173
		v[731,7] = 1
		v[732,7] = 221
		v[733,7] = 157
		v[734,7] = 1
		v[735,7] = 15
		v[736,7] = 113
		v[737,7] = 147
		v[738,7] = 137
		v[739,7] = 205
		v[740,7] = 225
		v[741,7] = 73
		v[742,7] = 45
		v[743,7] = 49
		v[744,7] = 149
		v[745,7] = 113
		v[746,7] = 253
		v[747,7] = 99
		v[748,7] = 17
		v[749,7] = 119
		v[750,7] = 105
		v[751,7] = 117
		v[752,7] = 129
		v[753,7] = 243
		v[754,7] = 75
		v[755,7] = 203
		v[756,7] = 53
		v[757,7] = 29
		v[758,7] = 247
		v[759,7] = 35
		v[760,7] = 247
		v[761,7] = 171
		v[762,7] = 31
		v[763,7] = 199
		v[764,7] = 213
		v[765,7] = 29
		v[766,7] = 251
		v[767,7] = 7
		v[768,7] = 251
		v[769,7] = 187
		v[770,7] = 91
		v[771,7] = 11
		v[772,7] = 149
		v[773,7] = 13
		v[774,7] = 205
		v[775,7] = 37
		v[776,7] = 249
		v[777,7] = 137
		v[778,7] = 139
		v[779,7] = 9
		v[780,7] = 7
		v[781,7] = 113
		v[782,7] = 183
		v[783,7] = 205
		v[784,7] = 187
		v[785,7] = 39
		v[786,7] = 3
		v[787,7] = 79
		v[788,7] = 155
		v[789,7] = 227
		v[790,7] = 89
		v[791,7] = 185
		v[792,7] = 51
		v[793,7] = 127
		v[794,7] = 63
		v[795,7] = 83
		v[796,7] = 41
		v[797,7] = 133
		v[798,7] = 183
		v[799,7] = 181
		v[800,7] = 127
		v[801,7] = 19
		v[802,7] = 255
		v[803,7] = 219
		v[804,7] = 59
		v[805,7] = 251
		v[806,7] = 3
		v[807,7] = 187
		v[808,7] = 57
		v[809,7] = 217
		v[810,7] = 115
		v[811,7] = 217
		v[812,7] = 229
		v[813,7] = 181
		v[814,7] = 185
		v[815,7] = 149
		v[816,7] = 83
		v[817,7] = 115
		v[818,7] = 11
		v[819,7] = 123
		v[820,7] = 19
		v[821,7] = 109
		v[822,7] = 165
		v[823,7] = 103
		v[824,7] = 123
		v[825,7] = 219
		v[826,7] = 129
		v[827,7] = 155
		v[828,7] = 207
		v[829,7] = 177
		v[830,7] = 9
		v[831,7] = 49
		v[832,7] = 181
		v[833,7] = 231
		v[834,7] = 33
		v[835,7] = 233
		v[836,7] = 67
		v[837,7] = 155
		v[838,7] = 41
		v[839,7] = 9
		v[840,7] = 95
		v[841,7] = 123
		v[842,7] = 65
		v[843,7] = 117
		v[844,7] = 249
		v[845,7] = 85
		v[846,7] = 169
		v[847,7] = 129
		v[848,7] = 241
		v[849,7] = 173
		v[850,7] = 251
		v[851,7] = 225
		v[852,7] = 147
		v[853,7] = 165
		v[854,7] = 69
		v[855,7] = 81
		v[856,7] = 239
		v[857,7] = 95
		v[858,7] = 23
		v[859,7] = 83
		v[860,7] = 227
		v[861,7] = 249
		v[862,7] = 143
		v[863,7] = 171
		v[864,7] = 193
		v[865,7] = 9
		v[866,7] = 21
		v[867,7] = 57
		v[868,7] = 73
		v[869,7] = 97
		v[870,7] = 57
		v[871,7] = 29
		v[872,7] = 239
		v[873,7] = 151
		v[874,7] = 159
		v[875,7] = 191
		v[876,7] = 47
		v[877,7] = 51
		v[878,7] = 1
		v[879,7] = 223
		v[880,7] = 251
		v[881,7] = 251
		v[882,7] = 151
		v[883,7] = 41
		v[884,7] = 119
		v[885,7] = 127
		v[886,7] = 131
		v[887,7] = 33
		v[888,7] = 209
		v[889,7] = 123
		v[890,7] = 53
		v[891,7] = 241
		v[892,7] = 25
		v[893,7] = 31
		v[894,7] = 183
		v[895,7] = 107
		v[896,7] = 25
		v[897,7] = 115
		v[898,7] = 39
		v[899,7] = 11
		v[900,7] = 213
		v[901,7] = 239
		v[902,7] = 219
		v[903,7] = 109
		v[904,7] = 185
		v[905,7] = 35
		v[906,7] = 133
		v[907,7] = 123
		v[908,7] = 185
		v[909,7] = 27
		v[910,7] = 55
		v[911,7] = 245
		v[912,7] = 61
		v[913,7] = 75
		v[914,7] = 205
		v[915,7] = 213
		v[916,7] = 169
		v[917,7] = 163
		v[918,7] = 63
		v[919,7] = 55
		v[920,7] = 49
		v[921,7] = 83
		v[922,7] = 195
		v[923,7] = 51
		v[924,7] = 31
		v[925,7] = 41
		v[926,7] = 15
		v[927,7] = 203
		v[928,7] = 41
		v[929,7] = 63
		v[930,7] = 127
		v[931,7] = 161
		v[932,7] = 5
		v[933,7] = 143
		v[934,7] = 7
		v[935,7] = 199
		v[936,7] = 251
		v[937,7] = 95
		v[938,7] = 75
		v[939,7] = 101
		v[940,7] = 15
		v[941,7] = 43
		v[942,7] = 237
		v[943,7] = 197
		v[944,7] = 117
		v[945,7] = 167
		v[946,7] = 155
		v[947,7] = 21
		v[948,7] = 83
		v[949,7] = 205
		v[950,7] = 255
		v[951,7] = 49
		v[952,7] = 101
		v[953,7] = 213
		v[954,7] = 237
		v[955,7] = 135
		v[956,7] = 135
		v[957,7] = 21
		v[958,7] = 73
		v[959,7] = 93
		v[960,7] = 115
		v[961,7] = 7
		v[962,7] = 85
		v[963,7] = 223
		v[964,7] = 237
		v[965,7] = 79
		v[966,7] = 89
		v[967,7] = 5
		v[968,7] = 57
		v[969,7] = 239
		v[970,7] = 67
		v[971,7] = 65
		v[972,7] = 201
		v[973,7] = 155
		v[974,7] = 71
		v[975,7] = 85
		v[976,7] = 195
		v[977,7] = 89
		v[978,7] = 181
		v[979,7] = 119
		v[980,7] = 135
		v[981,7] = 147
		v[982,7] = 237
		v[983,7] = 173
		v[984,7] = 41
		v[985,7] = 155
		v[986,7] = 67
		v[987,7] = 113
		v[988,7] = 111
		v[989,7] = 21
		v[990,7] = 183
		v[991,7] = 23
		v[992,7] = 103
		v[993,7] = 207
		v[994,7] = 253
		v[995,7] = 69
		v[996,7] = 219
		v[997,7] = 205
		v[998,7] = 195
		v[999,7] = 43
		v[1000,7] = 197
		v[1001,7] = 229
		v[1002,7] = 139
		v[1003,7] = 177
		v[1004,7] = 129
		v[1005,7] = 69
		v[1006,7] = 97
		v[1007,7] = 201
		v[1008,7] = 163
		v[1009,7] = 189
		v[1010,7] = 11
		v[1011,7] = 99
		v[1012,7] = 91
		v[1013,7] = 253
		v[1014,7] = 239
		v[1015,7] = 91
		v[1016,7] = 145
		v[1017,7] = 19
		v[1018,7] = 179
		v[1019,7] = 231
		v[1020,7] = 121
		v[1021,7] = 7
		v[1022,7] = 225
		v[1023,7] = 237
		v[1024,7] = 125
		v[1025,7] = 191
		v[1026,7] = 119
		v[1027,7] = 59
		v[1028,7] = 175
		v[1029,7] = 237
		v[1030,7] = 131
		v[1031,7] = 79
		v[1032,7] = 43
		v[1033,7] = 45
		v[1034,7] = 205
		v[1035,7] = 199
		v[1036,7] = 251
		v[1037,7] = 153
		v[1038,7] = 207
		v[1039,7] = 37
		v[1040,7] = 179
		v[1041,7] = 113
		v[1042,7] = 255
		v[1043,7] = 107
		v[1044,7] = 217
		v[1045,7] = 61
		v[1046,7] = 7
		v[1047,7] = 181
		v[1048,7] = 247
		v[1049,7] = 31
		v[1050,7] = 13
		v[1051,7] = 113
		v[1052,7] = 145
		v[1053,7] = 107
		v[1054,7] = 233
		v[1055,7] = 233
		v[1056,7] = 43
		v[1057,7] = 79
		v[1058,7] = 23
		v[1059,7] = 169
		v[1060,7] = 137
		v[1061,7] = 129
		v[1062,7] = 183
		v[1063,7] = 53
		v[1064,7] = 91
		v[1065,7] = 55
		v[1066,7] = 103
		v[1067,7] = 223
		v[1068,7] = 87
		v[1069,7] = 177
		v[1070,7] = 157
		v[1071,7] = 79
		v[1072,7] = 213
		v[1073,7] = 139
		v[1074,7] = 183
		v[1075,7] = 231
		v[1076,7] = 205
		v[1077,7] = 143
		v[1078,7] = 129
		v[1079,7] = 243
		v[1080,7] = 205
		v[1081,7] = 93
		v[1082,7] = 59
		v[1083,7] = 15
		v[1084,7] = 89
		v[1085,7] = 9
		v[1086,7] = 11
		v[1087,7] = 47
		v[1088,7] = 133
		v[1089,7] = 227
		v[1090,7] = 75
		v[1091,7] = 9
		v[1092,7] = 91
		v[1093,7] = 19
		v[1094,7] = 171
		v[1095,7] = 163
		v[1096,7] = 79
		v[1097,7] = 7
		v[1098,7] = 103
		v[1099,7] = 5
		v[1100,7] = 119
		v[1101,7] = 155
		v[1102,7] = 75
		v[1103,7] = 11
		v[1104,7] = 71
		v[1105,7] = 95
		v[1106,7] = 17
		v[1107,7] = 13
		v[1108,7] = 243
		v[1109,7] = 207
		v[1110,7] = 187

		v[53,8] = 235
		v[54,8] = 307
		v[55,8] = 495
		v[56,8] = 417
		v[57,8] = 57
		v[58,8] = 151
		v[59,8] = 19
		v[60,8] = 119
		v[61,8] = 375
		v[62,8] = 451
		v[63,8] = 55
		v[64,8] = 449
		v[65,8] = 501
		v[66,8] = 53
		v[67,8] = 185
		v[68,8] = 317
		v[69,8] = 17
		v[70,8] = 21
		v[71,8] = 487
		v[72,8] = 13
		v[73,8] = 347
		v[74,8] = 393
		v[75,8] = 15
		v[76,8] = 391
		v[77,8] = 307
		v[78,8] = 189
		v[79,8] = 381
		v[80,8] = 71
		v[81,8] = 163
		v[82,8] = 99
		v[83,8] = 467
		v[84,8] = 167
		v[85,8] = 433
		v[86,8] = 337
		v[87,8] = 257
		v[88,8] = 179
		v[89,8] = 47
		v[90,8] = 385
		v[91,8] = 23
		v[92,8] = 117
		v[93,8] = 369
		v[94,8] = 425
		v[95,8] = 207
		v[96,8] = 433
		v[97,8] = 301
		v[98,8] = 147
		v[99,8] = 333
		v[100,8] = 85
		v[101,8] = 221
		v[102,8] = 423
		v[103,8] = 49
		v[104,8] = 3
		v[105,8] = 43
		v[106,8] = 229
		v[107,8] = 227
		v[108,8] = 201
		v[109,8] = 383
		v[110,8] = 281
		v[111,8] = 229
		v[112,8] = 207
		v[113,8] = 21
		v[114,8] = 343
		v[115,8] = 251
		v[116,8] = 397
		v[117,8] = 173
		v[118,8] = 507
		v[119,8] = 421
		v[120,8] = 443
		v[121,8] = 399
		v[122,8] = 53
		v[123,8] = 345
		v[124,8] = 77
		v[125,8] = 385
		v[126,8] = 317
		v[127,8] = 155
		v[128,8] = 187
		v[129,8] = 269
		v[130,8] = 501
		v[131,8] = 19
		v[132,8] = 169
		v[133,8] = 235
		v[134,8] = 415
		v[135,8] = 61
		v[136,8] = 247
		v[137,8] = 183
		v[138,8] = 5
		v[139,8] = 257
		v[140,8] = 401
		v[141,8] = 451
		v[142,8] = 95
		v[143,8] = 455
		v[144,8] = 49
		v[145,8] = 489
		v[146,8] = 75
		v[147,8] = 459
		v[148,8] = 377
		v[149,8] = 87
		v[150,8] = 463
		v[151,8] = 155
		v[152,8] = 233
		v[153,8] = 115
		v[154,8] = 429
		v[155,8] = 211
		v[156,8] = 419
		v[157,8] = 143
		v[158,8] = 487
		v[159,8] = 195
		v[160,8] = 209
		v[161,8] = 461
		v[162,8] = 193
		v[163,8] = 157
		v[164,8] = 193
		v[165,8] = 363
		v[166,8] = 181
		v[167,8] = 271
		v[168,8] = 445
		v[169,8] = 381
		v[170,8] = 231
		v[171,8] = 135
		v[172,8] = 327
		v[173,8] = 403
		v[174,8] = 171
		v[175,8] = 197
		v[176,8] = 181
		v[177,8] = 343
		v[178,8] = 113
		v[179,8] = 313
		v[180,8] = 393
		v[181,8] = 311
		v[182,8] = 415
		v[183,8] = 267
		v[184,8] = 247
		v[185,8] = 425
		v[186,8] = 233
		v[187,8] = 289
		v[188,8] = 55
		v[189,8] = 39
		v[190,8] = 247
		v[191,8] = 327
		v[192,8] = 141
		v[193,8] = 5
		v[194,8] = 189
		v[195,8] = 183
		v[196,8] = 27
		v[197,8] = 337
		v[198,8] = 341
		v[199,8] = 327
		v[200,8] = 87
		v[201,8] = 429
		v[202,8] = 357
		v[203,8] = 265
		v[204,8] = 251
		v[205,8] = 437
		v[206,8] = 201
		v[207,8] = 29
		v[208,8] = 339
		v[209,8] = 257
		v[210,8] = 377
		v[211,8] = 17
		v[212,8] = 53
		v[213,8] = 327
		v[214,8] = 47
		v[215,8] = 375
		v[216,8] = 393
		v[217,8] = 369
		v[218,8] = 403
		v[219,8] = 125
		v[220,8] = 429
		v[221,8] = 257
		v[222,8] = 157
		v[223,8] = 217
		v[224,8] = 85
		v[225,8] = 267
		v[226,8] = 117
		v[227,8] = 337
		v[228,8] = 447
		v[229,8] = 219
		v[230,8] = 501
		v[231,8] = 41
		v[232,8] = 41
		v[233,8] = 193
		v[234,8] = 509
		v[235,8] = 131
		v[236,8] = 207
		v[237,8] = 505
		v[238,8] = 421
		v[239,8] = 149
		v[240,8] = 111
		v[241,8] = 177
		v[242,8] = 167
		v[243,8] = 223
		v[244,8] = 291
		v[245,8] = 91
		v[246,8] = 29
		v[247,8] = 305
		v[248,8] = 151
		v[249,8] = 177
		v[250,8] = 337
		v[251,8] = 183
		v[252,8] = 361
		v[253,8] = 435
		v[254,8] = 307
		v[255,8] = 507
		v[256,8] = 77
		v[257,8] = 181
		v[258,8] = 507
		v[259,8] = 315
		v[260,8] = 145
		v[261,8] = 423
		v[262,8] = 71
		v[263,8] = 103
		v[264,8] = 493
		v[265,8] = 271
		v[266,8] = 469
		v[267,8] = 339
		v[268,8] = 237
		v[269,8] = 437
		v[270,8] = 483
		v[271,8] = 31
		v[272,8] = 219
		v[273,8] = 61
		v[274,8] = 131
		v[275,8] = 391
		v[276,8] = 233
		v[277,8] = 219
		v[278,8] = 69
		v[279,8] = 57
		v[280,8] = 459
		v[281,8] = 225
		v[282,8] = 421
		v[283,8] = 7
		v[284,8] = 461
		v[285,8] = 111
		v[286,8] = 451
		v[287,8] = 277
		v[288,8] = 185
		v[289,8] = 193
		v[290,8] = 125
		v[291,8] = 251
		v[292,8] = 199
		v[293,8] = 73
		v[294,8] = 71
		v[295,8] = 7
		v[296,8] = 409
		v[297,8] = 417
		v[298,8] = 149
		v[299,8] = 193
		v[300,8] = 53
		v[301,8] = 437
		v[302,8] = 29
		v[303,8] = 467
		v[304,8] = 229
		v[305,8] = 31
		v[306,8] = 35
		v[307,8] = 75
		v[308,8] = 105
		v[309,8] = 503
		v[310,8] = 75
		v[311,8] = 317
		v[312,8] = 401
		v[313,8] = 367
		v[314,8] = 131
		v[315,8] = 365
		v[316,8] = 441
		v[317,8] = 433
		v[318,8] = 93
		v[319,8] = 377
		v[320,8] = 405
		v[321,8] = 465
		v[322,8] = 259
		v[323,8] = 283
		v[324,8] = 443
		v[325,8] = 143
		v[326,8] = 445
		v[327,8] = 3
		v[328,8] = 461
		v[329,8] = 329
		v[330,8] = 309
		v[331,8] = 77
		v[332,8] = 323
		v[333,8] = 155
		v[334,8] = 347
		v[335,8] = 45
		v[336,8] = 381
		v[337,8] = 315
		v[338,8] = 463
		v[339,8] = 207
		v[340,8] = 321
		v[341,8] = 157
		v[342,8] = 109
		v[343,8] = 479
		v[344,8] = 313
		v[345,8] = 345
		v[346,8] = 167
		v[347,8] = 439
		v[348,8] = 307
		v[349,8] = 235
		v[350,8] = 473
		v[351,8] = 79
		v[352,8] = 101
		v[353,8] = 245
		v[354,8] = 19
		v[355,8] = 381
		v[356,8] = 251
		v[357,8] = 35
		v[358,8] = 25
		v[359,8] = 107
		v[360,8] = 187
		v[361,8] = 115
		v[362,8] = 113
		v[363,8] = 321
		v[364,8] = 115
		v[365,8] = 445
		v[366,8] = 61
		v[367,8] = 77
		v[368,8] = 293
		v[369,8] = 405
		v[370,8] = 13
		v[371,8] = 53
		v[372,8] = 17
		v[373,8] = 171
		v[374,8] = 299
		v[375,8] = 41
		v[376,8] = 79
		v[377,8] = 3
		v[378,8] = 485
		v[379,8] = 331
		v[380,8] = 13
		v[381,8] = 257
		v[382,8] = 59
		v[383,8] = 201
		v[384,8] = 497
		v[385,8] = 81
		v[386,8] = 451
		v[387,8] = 199
		v[388,8] = 171
		v[389,8] = 81
		v[390,8] = 253
		v[391,8] = 365
		v[392,8] = 75
		v[393,8] = 451
		v[394,8] = 149
		v[395,8] = 483
		v[396,8] = 81
		v[397,8] = 453
		v[398,8] = 469
		v[399,8] = 485
		v[400,8] = 305
		v[401,8] = 163
		v[402,8] = 401
		v[403,8] = 15
		v[404,8] = 91
		v[405,8] = 3
		v[406,8] = 129
		v[407,8] = 35
		v[408,8] = 239
		v[409,8] = 355
		v[410,8] = 211
		v[411,8] = 387
		v[412,8] = 101
		v[413,8] = 299
		v[414,8] = 67
		v[415,8] = 375
		v[416,8] = 405
		v[417,8] = 357
		v[418,8] = 267
		v[419,8] = 363
		v[420,8] = 79
		v[421,8] = 83
		v[422,8] = 437
		v[423,8] = 457
		v[424,8] = 39
		v[425,8] = 97
		v[426,8] = 473
		v[427,8] = 289
		v[428,8] = 179
		v[429,8] = 57
		v[430,8] = 23
		v[431,8] = 49
		v[432,8] = 79
		v[433,8] = 71
		v[434,8] = 341
		v[435,8] = 287
		v[436,8] = 95
		v[437,8] = 229
		v[438,8] = 271
		v[439,8] = 475
		v[440,8] = 49
		v[441,8] = 241
		v[442,8] = 261
		v[443,8] = 495
		v[444,8] = 353
		v[445,8] = 381
		v[446,8] = 13
		v[447,8] = 291
		v[448,8] = 37
		v[449,8] = 251
		v[450,8] = 105
		v[451,8] = 399
		v[452,8] = 81
		v[453,8] = 89
		v[454,8] = 265
		v[455,8] = 507
		v[456,8] = 205
		v[457,8] = 145
		v[458,8] = 331
		v[459,8] = 129
		v[460,8] = 119
		v[461,8] = 503
		v[462,8] = 249
		v[463,8] = 1
		v[464,8] = 289
		v[465,8] = 463
		v[466,8] = 163
		v[467,8] = 443
		v[468,8] = 63
		v[469,8] = 123
		v[470,8] = 361
		v[471,8] = 261
		v[472,8] = 49
		v[473,8] = 429
		v[474,8] = 137
		v[475,8] = 355
		v[476,8] = 175
		v[477,8] = 507
		v[478,8] = 59
		v[479,8] = 277
		v[480,8] = 391
		v[481,8] = 25
		v[482,8] = 185
		v[483,8] = 381
		v[484,8] = 197
		v[485,8] = 39
		v[486,8] = 5
		v[487,8] = 429
		v[488,8] = 119
		v[489,8] = 247
		v[490,8] = 177
		v[491,8] = 329
		v[492,8] = 465
		v[493,8] = 421
		v[494,8] = 271
		v[495,8] = 467
		v[496,8] = 151
		v[497,8] = 45
		v[498,8] = 429
		v[499,8] = 137
		v[500,8] = 471
		v[501,8] = 11
		v[502,8] = 17
		v[503,8] = 409
		v[504,8] = 347
		v[505,8] = 199
		v[506,8] = 463
		v[507,8] = 177
		v[508,8] = 11
		v[509,8] = 51
		v[510,8] = 361
		v[511,8] = 95
		v[512,8] = 497
		v[513,8] = 163
		v[514,8] = 351
		v[515,8] = 127
		v[516,8] = 395
		v[517,8] = 511
		v[518,8] = 327
		v[519,8] = 353
		v[520,8] = 49
		v[521,8] = 105
		v[522,8] = 151
		v[523,8] = 321
		v[524,8] = 331
		v[525,8] = 329
		v[526,8] = 509
		v[527,8] = 107
		v[528,8] = 109
		v[529,8] = 303
		v[530,8] = 467
		v[531,8] = 287
		v[532,8] = 161
		v[533,8] = 45
		v[534,8] = 385
		v[535,8] = 289
		v[536,8] = 363
		v[537,8] = 331
		v[538,8] = 265
		v[539,8] = 407
		v[540,8] = 37
		v[541,8] = 433
		v[542,8] = 315
		v[543,8] = 343
		v[544,8] = 63
		v[545,8] = 51
		v[546,8] = 185
		v[547,8] = 71
		v[548,8] = 27
		v[549,8] = 267
		v[550,8] = 503
		v[551,8] = 239
		v[552,8] = 293
		v[553,8] = 245
		v[554,8] = 281
		v[555,8] = 297
		v[556,8] = 75
		v[557,8] = 461
		v[558,8] = 371
		v[559,8] = 129
		v[560,8] = 189
		v[561,8] = 189
		v[562,8] = 339
		v[563,8] = 287
		v[564,8] = 111
		v[565,8] = 111
		v[566,8] = 379
		v[567,8] = 93
		v[568,8] = 27
		v[569,8] = 185
		v[570,8] = 347
		v[571,8] = 337
		v[572,8] = 247
		v[573,8] = 507
		v[574,8] = 161
		v[575,8] = 231
		v[576,8] = 43
		v[577,8] = 499
		v[578,8] = 73
		v[579,8] = 327
		v[580,8] = 263
		v[581,8] = 331
		v[582,8] = 249
		v[583,8] = 493
		v[584,8] = 37
		v[585,8] = 25
		v[586,8] = 115
		v[587,8] = 3
		v[588,8] = 167
		v[589,8] = 197
		v[590,8] = 127
		v[591,8] = 357
		v[592,8] = 497
		v[593,8] = 103
		v[594,8] = 125
		v[595,8] = 191
		v[596,8] = 165
		v[597,8] = 55
		v[598,8] = 101
		v[599,8] = 95
		v[600,8] = 79
		v[601,8] = 351
		v[602,8] = 341
		v[603,8] = 43
		v[604,8] = 125
		v[605,8] = 135
		v[606,8] = 173
		v[607,8] = 289
		v[608,8] = 373
		v[609,8] = 133
		v[610,8] = 421
		v[611,8] = 241
		v[612,8] = 281
		v[613,8] = 213
		v[614,8] = 177
		v[615,8] = 363
		v[616,8] = 151
		v[617,8] = 227
		v[618,8] = 145
		v[619,8] = 363
		v[620,8] = 239
		v[621,8] = 431
		v[622,8] = 81
		v[623,8] = 397
		v[624,8] = 241
		v[625,8] = 67
		v[626,8] = 291
		v[627,8] = 255
		v[628,8] = 405
		v[629,8] = 421
		v[630,8] = 399
		v[631,8] = 75
		v[632,8] = 399
		v[633,8] = 105
		v[634,8] = 329
		v[635,8] = 41
		v[636,8] = 425
		v[637,8] = 7
		v[638,8] = 283
		v[639,8] = 375
		v[640,8] = 475
		v[641,8] = 427
		v[642,8] = 277
		v[643,8] = 209
		v[644,8] = 411
		v[645,8] = 3
		v[646,8] = 137
		v[647,8] = 195
		v[648,8] = 289
		v[649,8] = 509
		v[650,8] = 121
		v[651,8] = 55
		v[652,8] = 147
		v[653,8] = 275
		v[654,8] = 251
		v[655,8] = 19
		v[656,8] = 129
		v[657,8] = 285
		v[658,8] = 415
		v[659,8] = 487
		v[660,8] = 491
		v[661,8] = 193
		v[662,8] = 219
		v[663,8] = 403
		v[664,8] = 23
		v[665,8] = 97
		v[666,8] = 65
		v[667,8] = 285
		v[668,8] = 75
		v[669,8] = 21
		v[670,8] = 373
		v[671,8] = 261
		v[672,8] = 339
		v[673,8] = 239
		v[674,8] = 495
		v[675,8] = 415
		v[676,8] = 333
		v[677,8] = 107
		v[678,8] = 435
		v[679,8] = 297
		v[680,8] = 213
		v[681,8] = 149
		v[682,8] = 463
		v[683,8] = 199
		v[684,8] = 323
		v[685,8] = 45
		v[686,8] = 19
		v[687,8] = 301
		v[688,8] = 121
		v[689,8] = 499
		v[690,8] = 187
		v[691,8] = 229
		v[692,8] = 63
		v[693,8] = 425
		v[694,8] = 99
		v[695,8] = 281
		v[696,8] = 35
		v[697,8] = 125
		v[698,8] = 349
		v[699,8] = 87
		v[700,8] = 101
		v[701,8] = 59
		v[702,8] = 195
		v[703,8] = 511
		v[704,8] = 355
		v[705,8] = 73
		v[706,8] = 263
		v[707,8] = 243
		v[708,8] = 101
		v[709,8] = 165
		v[710,8] = 141
		v[711,8] = 11
		v[712,8] = 389
		v[713,8] = 219
		v[714,8] = 187
		v[715,8] = 449
		v[716,8] = 447
		v[717,8] = 393
		v[718,8] = 477
		v[719,8] = 305
		v[720,8] = 221
		v[721,8] = 51
		v[722,8] = 355
		v[723,8] = 209
		v[724,8] = 499
		v[725,8] = 479
		v[726,8] = 265
		v[727,8] = 377
		v[728,8] = 145
		v[729,8] = 411
		v[730,8] = 173
		v[731,8] = 11
		v[732,8] = 433
		v[733,8] = 483
		v[734,8] = 135
		v[735,8] = 385
		v[736,8] = 341
		v[737,8] = 89
		v[738,8] = 209
		v[739,8] = 391
		v[740,8] = 33
		v[741,8] = 395
		v[742,8] = 319
		v[743,8] = 451
		v[744,8] = 119
		v[745,8] = 341
		v[746,8] = 227
		v[747,8] = 375
		v[748,8] = 61
		v[749,8] = 331
		v[750,8] = 493
		v[751,8] = 411
		v[752,8] = 293
		v[753,8] = 47
		v[754,8] = 203
		v[755,8] = 375
		v[756,8] = 167
		v[757,8] = 395
		v[758,8] = 155
		v[759,8] = 5
		v[760,8] = 237
		v[761,8] = 361
		v[762,8] = 489
		v[763,8] = 127
		v[764,8] = 21
		v[765,8] = 345
		v[766,8] = 101
		v[767,8] = 371
		v[768,8] = 233
		v[769,8] = 431
		v[770,8] = 109
		v[771,8] = 119
		v[772,8] = 277
		v[773,8] = 125
		v[774,8] = 263
		v[775,8] = 73
		v[776,8] = 135
		v[777,8] = 123
		v[778,8] = 83
		v[779,8] = 123
		v[780,8] = 405
		v[781,8] = 69
		v[782,8] = 75
		v[783,8] = 287
		v[784,8] = 401
		v[785,8] = 23
		v[786,8] = 283
		v[787,8] = 393
		v[788,8] = 41
		v[789,8] = 379
		v[790,8] = 431
		v[791,8] = 11
		v[792,8] = 475
		v[793,8] = 505
		v[794,8] = 19
		v[795,8] = 365
		v[796,8] = 265
		v[797,8] = 271
		v[798,8] = 499
		v[799,8] = 489
		v[800,8] = 443
		v[801,8] = 165
		v[802,8] = 91
		v[803,8] = 83
		v[804,8] = 291
		v[805,8] = 319
		v[806,8] = 199
		v[807,8] = 107
		v[808,8] = 245
		v[809,8] = 389
		v[810,8] = 143
		v[811,8] = 137
		v[812,8] = 89
		v[813,8] = 125
		v[814,8] = 281
		v[815,8] = 381
		v[816,8] = 215
		v[817,8] = 131
		v[818,8] = 299
		v[819,8] = 249
		v[820,8] = 375
		v[821,8] = 455
		v[822,8] = 43
		v[823,8] = 73
		v[824,8] = 281
		v[825,8] = 217
		v[826,8] = 297
		v[827,8] = 229
		v[828,8] = 431
		v[829,8] = 357
		v[830,8] = 81
		v[831,8] = 357
		v[832,8] = 171
		v[833,8] = 451
		v[834,8] = 481
		v[835,8] = 13
		v[836,8] = 387
		v[837,8] = 491
		v[838,8] = 489
		v[839,8] = 439
		v[840,8] = 385
		v[841,8] = 487
		v[842,8] = 177
		v[843,8] = 393
		v[844,8] = 33
		v[845,8] = 71
		v[846,8] = 375
		v[847,8] = 443
		v[848,8] = 129
		v[849,8] = 407
		v[850,8] = 395
		v[851,8] = 127
		v[852,8] = 65
		v[853,8] = 333
		v[854,8] = 309
		v[855,8] = 119
		v[856,8] = 197
		v[857,8] = 435
		v[858,8] = 497
		v[859,8] = 373
		v[860,8] = 71
		v[861,8] = 379
		v[862,8] = 509
		v[863,8] = 387
		v[864,8] = 159
		v[865,8] = 265
		v[866,8] = 477
		v[867,8] = 463
		v[868,8] = 449
		v[869,8] = 47
		v[870,8] = 353
		v[871,8] = 249
		v[872,8] = 335
		v[873,8] = 505
		v[874,8] = 89
		v[875,8] = 141
		v[876,8] = 55
		v[877,8] = 235
		v[878,8] = 187
		v[879,8] = 87
		v[880,8] = 363
		v[881,8] = 93
		v[882,8] = 363
		v[883,8] = 101
		v[884,8] = 67
		v[885,8] = 215
		v[886,8] = 321
		v[887,8] = 331
		v[888,8] = 305
		v[889,8] = 261
		v[890,8] = 411
		v[891,8] = 491
		v[892,8] = 479
		v[893,8] = 65
		v[894,8] = 307
		v[895,8] = 469
		v[896,8] = 415
		v[897,8] = 131
		v[898,8] = 315
		v[899,8] = 487
		v[900,8] = 83
		v[901,8] = 455
		v[902,8] = 19
		v[903,8] = 113
		v[904,8] = 163
		v[905,8] = 503
		v[906,8] = 99
		v[907,8] = 499
		v[908,8] = 251
		v[909,8] = 239
		v[910,8] = 81
		v[911,8] = 167
		v[912,8] = 391
		v[913,8] = 255
		v[914,8] = 317
		v[915,8] = 363
		v[916,8] = 359
		v[917,8] = 395
		v[918,8] = 419
		v[919,8] = 307
		v[920,8] = 251
		v[921,8] = 267
		v[922,8] = 171
		v[923,8] = 461
		v[924,8] = 183
		v[925,8] = 465
		v[926,8] = 165
		v[927,8] = 163
		v[928,8] = 293
		v[929,8] = 477
		v[930,8] = 223
		v[931,8] = 403
		v[932,8] = 389
		v[933,8] = 97
		v[934,8] = 335
		v[935,8] = 357
		v[936,8] = 297
		v[937,8] = 19
		v[938,8] = 469
		v[939,8] = 501
		v[940,8] = 249
		v[941,8] = 85
		v[942,8] = 213
		v[943,8] = 311
		v[944,8] = 265
		v[945,8] = 379
		v[946,8] = 297
		v[947,8] = 283
		v[948,8] = 393
		v[949,8] = 449
		v[950,8] = 463
		v[951,8] = 289
		v[952,8] = 159
		v[953,8] = 289
		v[954,8] = 499
		v[955,8] = 407
		v[956,8] = 129
		v[957,8] = 137
		v[958,8] = 221
		v[959,8] = 43
		v[960,8] = 89
		v[961,8] = 403
		v[962,8] = 271
		v[963,8] = 75
		v[964,8] = 83
		v[965,8] = 445
		v[966,8] = 453
		v[967,8] = 389
		v[968,8] = 149
		v[969,8] = 143
		v[970,8] = 423
		v[971,8] = 499
		v[972,8] = 317
		v[973,8] = 445
		v[974,8] = 157
		v[975,8] = 137
		v[976,8] = 453
		v[977,8] = 163
		v[978,8] = 87
		v[979,8] = 23
		v[980,8] = 391
		v[981,8] = 119
		v[982,8] = 427
		v[983,8] = 323
		v[984,8] = 173
		v[985,8] = 89
		v[986,8] = 259
		v[987,8] = 377
		v[988,8] = 511
		v[989,8] = 249
		v[990,8] = 31
		v[991,8] = 363
		v[992,8] = 229
		v[993,8] = 353
		v[994,8] = 329
		v[995,8] = 493
		v[996,8] = 427
		v[997,8] = 57
		v[998,8] = 205
		v[999,8] = 389
		v[1000,8] = 91
		v[1001,8] = 83
		v[1002,8] = 13
		v[1003,8] = 219
		v[1004,8] = 439
		v[1005,8] = 45
		v[1006,8] = 35
		v[1007,8] = 371
		v[1008,8] = 441
		v[1009,8] = 17
		v[1010,8] = 267
		v[1011,8] = 501
		v[1012,8] = 53
		v[1013,8] = 25
		v[1014,8] = 333
		v[1015,8] = 17
		v[1016,8] = 201
		v[1017,8] = 475
		v[1018,8] = 257
		v[1019,8] = 417
		v[1020,8] = 345
		v[1021,8] = 381
		v[1022,8] = 377
		v[1023,8] = 55
		v[1024,8] = 403
		v[1025,8] = 77
		v[1026,8] = 389
		v[1027,8] = 347
		v[1028,8] = 363
		v[1029,8] = 211
		v[1030,8] = 413
		v[1031,8] = 419
		v[1032,8] = 5
		v[1033,8] = 167
		v[1034,8] = 219
		v[1035,8] = 201
		v[1036,8] = 285
		v[1037,8] = 425
		v[1038,8] = 11
		v[1039,8] = 77
		v[1040,8] = 269
		v[1041,8] = 489
		v[1042,8] = 281
		v[1043,8] = 403
		v[1044,8] = 79
		v[1045,8] = 425
		v[1046,8] = 125
		v[1047,8] = 81
		v[1048,8] = 331
		v[1049,8] = 437
		v[1050,8] = 271
		v[1051,8] = 397
		v[1052,8] = 299
		v[1053,8] = 475
		v[1054,8] = 271
		v[1055,8] = 249
		v[1056,8] = 413
		v[1057,8] = 233
		v[1058,8] = 261
		v[1059,8] = 495
		v[1060,8] = 171
		v[1061,8] = 69
		v[1062,8] = 27
		v[1063,8] = 409
		v[1064,8] = 21
		v[1065,8] = 421
		v[1066,8] = 367
		v[1067,8] = 81
		v[1068,8] = 483
		v[1069,8] = 255
		v[1070,8] = 15
		v[1071,8] = 219
		v[1072,8] = 365
		v[1073,8] = 497
		v[1074,8] = 181
		v[1075,8] = 75
		v[1076,8] = 431
		v[1077,8] = 99
		v[1078,8] = 325
		v[1079,8] = 407
		v[1080,8] = 229
		v[1081,8] = 281
		v[1082,8] = 63
		v[1083,8] = 83
		v[1084,8] = 493
		v[1085,8] = 5
		v[1086,8] = 113
		v[1087,8] = 15
		v[1088,8] = 271
		v[1089,8] = 37
		v[1090,8] = 87
		v[1091,8] = 451
		v[1092,8] = 299
		v[1093,8] = 83
		v[1094,8] = 451
		v[1095,8] = 311
		v[1096,8] = 441
		v[1097,8] = 47
		v[1098,8] = 455
		v[1099,8] = 47
		v[1100,8] = 253
		v[1101,8] = 13
		v[1102,8] = 109
		v[1103,8] = 369
		v[1104,8] = 347
		v[1105,8] = 11
		v[1106,8] = 409
		v[1107,8] = 275
		v[1108,8] = 63
		v[1109,8] = 441
		v[1110,8] = 15

		v[101,9] = 519
		v[102,9] = 307
		v[103,9] = 931
		v[104,9] = 1023
		v[105,9] = 517
		v[106,9] = 771
		v[107,9] = 151
		v[108,9] = 1023
		v[109,9] = 539
		v[110,9] = 725
		v[111,9] = 45
		v[112,9] = 927
		v[113,9] = 707
		v[114,9] = 29
		v[115,9] = 125
		v[116,9] = 371
		v[117,9] = 275
		v[118,9] = 279
		v[119,9] = 817
		v[120,9] = 389
		v[121,9] = 453
		v[122,9] = 989
		v[123,9] = 1015
		v[124,9] = 29
		v[125,9] = 169
		v[126,9] = 743
		v[127,9] = 99
		v[128,9] = 923
		v[129,9] = 981
		v[130,9] = 181
		v[131,9] = 693
		v[132,9] = 309
		v[133,9] = 227
		v[134,9] = 111
		v[135,9] = 219
		v[136,9] = 897
		v[137,9] = 377
		v[138,9] = 425
		v[139,9] = 609
		v[140,9] = 227
		v[141,9] = 19
		v[142,9] = 221
		v[143,9] = 143
		v[144,9] = 581
		v[145,9] = 147
		v[146,9] = 919
		v[147,9] = 127
		v[148,9] = 725
		v[149,9] = 793
		v[150,9] = 289
		v[151,9] = 411
		v[152,9] = 835
		v[153,9] = 921
		v[154,9] = 957
		v[155,9] = 443
		v[156,9] = 349
		v[157,9] = 813
		v[158,9] = 5
		v[159,9] = 105
		v[160,9] = 457
		v[161,9] = 393
		v[162,9] = 539
		v[163,9] = 101
		v[164,9] = 197
		v[165,9] = 697
		v[166,9] = 27
		v[167,9] = 343
		v[168,9] = 515
		v[169,9] = 69
		v[170,9] = 485
		v[171,9] = 383
		v[172,9] = 855
		v[173,9] = 693
		v[174,9] = 133
		v[175,9] = 87
		v[176,9] = 743
		v[177,9] = 747
		v[178,9] = 475
		v[179,9] = 87
		v[180,9] = 469
		v[181,9] = 763
		v[182,9] = 721
		v[183,9] = 345
		v[184,9] = 479
		v[185,9] = 965
		v[186,9] = 527
		v[187,9] = 121
		v[188,9] = 271
		v[189,9] = 353
		v[190,9] = 467
		v[191,9] = 177
		v[192,9] = 245
		v[193,9] = 627
		v[194,9] = 113
		v[195,9] = 357
		v[196,9] = 7
		v[197,9] = 691
		v[198,9] = 725
		v[199,9] = 355
		v[200,9] = 889
		v[201,9] = 635
		v[202,9] = 737
		v[203,9] = 429
		v[204,9] = 545
		v[205,9] = 925
		v[206,9] = 357
		v[207,9] = 873
		v[208,9] = 187
		v[209,9] = 351
		v[210,9] = 677
		v[211,9] = 999
		v[212,9] = 921
		v[213,9] = 477
		v[214,9] = 233
		v[215,9] = 765
		v[216,9] = 495
		v[217,9] = 81
		v[218,9] = 953
		v[219,9] = 479
		v[220,9] = 89
		v[221,9] = 173
		v[222,9] = 473
		v[223,9] = 131
		v[224,9] = 961
		v[225,9] = 411
		v[226,9] = 291
		v[227,9] = 967
		v[228,9] = 65
		v[229,9] = 511
		v[230,9] = 13
		v[231,9] = 805
		v[232,9] = 945
		v[233,9] = 369
		v[234,9] = 827
		v[235,9] = 295
		v[236,9] = 163
		v[237,9] = 835
		v[238,9] = 259
		v[239,9] = 207
		v[240,9] = 331
		v[241,9] = 29
		v[242,9] = 315
		v[243,9] = 999
		v[244,9] = 133
		v[245,9] = 967
		v[246,9] = 41
		v[247,9] = 117
		v[248,9] = 677
		v[249,9] = 471
		v[250,9] = 717
		v[251,9] = 881
		v[252,9] = 755
		v[253,9] = 351
		v[254,9] = 723
		v[255,9] = 259
		v[256,9] = 879
		v[257,9] = 455
		v[258,9] = 721
		v[259,9] = 289
		v[260,9] = 149
		v[261,9] = 199
		v[262,9] = 805
		v[263,9] = 987
		v[264,9] = 851
		v[265,9] = 423
		v[266,9] = 597
		v[267,9] = 129
		v[268,9] = 11
		v[269,9] = 733
		v[270,9] = 549
		v[271,9] = 153
		v[272,9] = 285
		v[273,9] = 451
		v[274,9] = 559
		v[275,9] = 377
		v[276,9] = 109
		v[277,9] = 357
		v[278,9] = 143
		v[279,9] = 693
		v[280,9] = 615
		v[281,9] = 677
		v[282,9] = 701
		v[283,9] = 475
		v[284,9] = 767
		v[285,9] = 85
		v[286,9] = 229
		v[287,9] = 509
		v[288,9] = 547
		v[289,9] = 151
		v[290,9] = 389
		v[291,9] = 711
		v[292,9] = 785
		v[293,9] = 657
		v[294,9] = 319
		v[295,9] = 509
		v[296,9] = 99
		v[297,9] = 1007
		v[298,9] = 775
		v[299,9] = 359
		v[300,9] = 697
		v[301,9] = 677
		v[302,9] = 85
		v[303,9] = 497
		v[304,9] = 105
		v[305,9] = 615
		v[306,9] = 891
		v[307,9] = 71
		v[308,9] = 449
		v[309,9] = 835
		v[310,9] = 609
		v[311,9] = 377
		v[312,9] = 693
		v[313,9] = 665
		v[314,9] = 627
		v[315,9] = 215
		v[316,9] = 911
		v[317,9] = 503
		v[318,9] = 729
		v[319,9] = 131
		v[320,9] = 19
		v[321,9] = 895
		v[322,9] = 199
		v[323,9] = 161
		v[324,9] = 239
		v[325,9] = 633
		v[326,9] = 1013
		v[327,9] = 537
		v[328,9] = 255
		v[329,9] = 23
		v[330,9] = 149
		v[331,9] = 679
		v[332,9] = 1021
		v[333,9] = 595
		v[334,9] = 199
		v[335,9] = 557
		v[336,9] = 659
		v[337,9] = 251
		v[338,9] = 829
		v[339,9] = 727
		v[340,9] = 439
		v[341,9] = 495
		v[342,9] = 647
		v[343,9] = 223
		v[344,9] = 949
		v[345,9] = 625
		v[346,9] = 87
		v[347,9] = 481
		v[348,9] = 85
		v[349,9] = 799
		v[350,9] = 917
		v[351,9] = 769
		v[352,9] = 949
		v[353,9] = 739
		v[354,9] = 115
		v[355,9] = 499
		v[356,9] = 945
		v[357,9] = 547
		v[358,9] = 225
		v[359,9] = 1015
		v[360,9] = 469
		v[361,9] = 737
		v[362,9] = 495
		v[363,9] = 353
		v[364,9] = 103
		v[365,9] = 17
		v[366,9] = 665
		v[367,9] = 639
		v[368,9] = 525
		v[369,9] = 75
		v[370,9] = 447
		v[371,9] = 185
		v[372,9] = 43
		v[373,9] = 729
		v[374,9] = 577
		v[375,9] = 863
		v[376,9] = 735
		v[377,9] = 317
		v[378,9] = 99
		v[379,9] = 17
		v[380,9] = 477
		v[381,9] = 893
		v[382,9] = 537
		v[383,9] = 519
		v[384,9] = 1017
		v[385,9] = 375
		v[386,9] = 297
		v[387,9] = 325
		v[388,9] = 999
		v[389,9] = 353
		v[390,9] = 343
		v[391,9] = 729
		v[392,9] = 135
		v[393,9] = 489
		v[394,9] = 859
		v[395,9] = 267
		v[396,9] = 141
		v[397,9] = 831
		v[398,9] = 141
		v[399,9] = 893
		v[400,9] = 249
		v[401,9] = 807
		v[402,9] = 53
		v[403,9] = 613
		v[404,9] = 131
		v[405,9] = 547
		v[406,9] = 977
		v[407,9] = 131
		v[408,9] = 999
		v[409,9] = 175
		v[410,9] = 31
		v[411,9] = 341
		v[412,9] = 739
		v[413,9] = 467
		v[414,9] = 675
		v[415,9] = 241
		v[416,9] = 645
		v[417,9] = 247
		v[418,9] = 391
		v[419,9] = 583
		v[420,9] = 183
		v[421,9] = 973
		v[422,9] = 433
		v[423,9] = 367
		v[424,9] = 131
		v[425,9] = 467
		v[426,9] = 571
		v[427,9] = 309
		v[428,9] = 385
		v[429,9] = 977
		v[430,9] = 111
		v[431,9] = 917
		v[432,9] = 935
		v[433,9] = 473
		v[434,9] = 345
		v[435,9] = 411
		v[436,9] = 313
		v[437,9] = 97
		v[438,9] = 149
		v[439,9] = 959
		v[440,9] = 841
		v[441,9] = 839
		v[442,9] = 669
		v[443,9] = 431
		v[444,9] = 51
		v[445,9] = 41
		v[446,9] = 301
		v[447,9] = 247
		v[448,9] = 1015
		v[449,9] = 377
		v[450,9] = 329
		v[451,9] = 945
		v[452,9] = 269
		v[453,9] = 67
		v[454,9] = 979
		v[455,9] = 581
		v[456,9] = 643
		v[457,9] = 823
		v[458,9] = 557
		v[459,9] = 91
		v[460,9] = 405
		v[461,9] = 117
		v[462,9] = 801
		v[463,9] = 509
		v[464,9] = 347
		v[465,9] = 893
		v[466,9] = 303
		v[467,9] = 227
		v[468,9] = 783
		v[469,9] = 555
		v[470,9] = 867
		v[471,9] = 99
		v[472,9] = 703
		v[473,9] = 111
		v[474,9] = 797
		v[475,9] = 873
		v[476,9] = 541
		v[477,9] = 919
		v[478,9] = 513
		v[479,9] = 343
		v[480,9] = 319
		v[481,9] = 517
		v[482,9] = 135
		v[483,9] = 871
		v[484,9] = 917
		v[485,9] = 285
		v[486,9] = 663
		v[487,9] = 301
		v[488,9] = 15
		v[489,9] = 763
		v[490,9] = 89
		v[491,9] = 323
		v[492,9] = 757
		v[493,9] = 317
		v[494,9] = 807
		v[495,9] = 309
		v[496,9] = 1013
		v[497,9] = 345
		v[498,9] = 499
		v[499,9] = 279
		v[500,9] = 711
		v[501,9] = 915
		v[502,9] = 411
		v[503,9] = 281
		v[504,9] = 193
		v[505,9] = 739
		v[506,9] = 365
		v[507,9] = 315
		v[508,9] = 375
		v[509,9] = 809
		v[510,9] = 469
		v[511,9] = 487
		v[512,9] = 621
		v[513,9] = 857
		v[514,9] = 975
		v[515,9] = 537
		v[516,9] = 939
		v[517,9] = 585
		v[518,9] = 129
		v[519,9] = 625
		v[520,9] = 447
		v[521,9] = 129
		v[522,9] = 1017
		v[523,9] = 133
		v[524,9] = 83
		v[525,9] = 3
		v[526,9] = 415
		v[527,9] = 661
		v[528,9] = 53
		v[529,9] = 115
		v[530,9] = 903
		v[531,9] = 49
		v[532,9] = 79
		v[533,9] = 55
		v[534,9] = 385
		v[535,9] = 261
		v[536,9] = 345
		v[537,9] = 297
		v[538,9] = 199
		v[539,9] = 385
		v[540,9] = 617
		v[541,9] = 25
		v[542,9] = 515
		v[543,9] = 275
		v[544,9] = 849
		v[545,9] = 401
		v[546,9] = 471
		v[547,9] = 377
		v[548,9] = 661
		v[549,9] = 535
		v[550,9] = 505
		v[551,9] = 939
		v[552,9] = 465
		v[553,9] = 225
		v[554,9] = 929
		v[555,9] = 219
		v[556,9] = 955
		v[557,9] = 659
		v[558,9] = 441
		v[559,9] = 117
		v[560,9] = 527
		v[561,9] = 427
		v[562,9] = 515
		v[563,9] = 287
		v[564,9] = 191
		v[565,9] = 33
		v[566,9] = 389
		v[567,9] = 197
		v[568,9] = 825
		v[569,9] = 63
		v[570,9] = 417
		v[571,9] = 949
		v[572,9] = 35
		v[573,9] = 571
		v[574,9] = 9
		v[575,9] = 131
		v[576,9] = 609
		v[577,9] = 439
		v[578,9] = 95
		v[579,9] = 19
		v[580,9] = 569
		v[581,9] = 893
		v[582,9] = 451
		v[583,9] = 397
		v[584,9] = 971
		v[585,9] = 801
		v[586,9] = 125
		v[587,9] = 471
		v[588,9] = 187
		v[589,9] = 257
		v[590,9] = 67
		v[591,9] = 949
		v[592,9] = 621
		v[593,9] = 453
		v[594,9] = 411
		v[595,9] = 621
		v[596,9] = 955
		v[597,9] = 309
		v[598,9] = 783
		v[599,9] = 893
		v[600,9] = 597
		v[601,9] = 377
		v[602,9] = 753
		v[603,9] = 145
		v[604,9] = 637
		v[605,9] = 941
		v[606,9] = 593
		v[607,9] = 317
		v[608,9] = 555
		v[609,9] = 375
		v[610,9] = 575
		v[611,9] = 175
		v[612,9] = 403
		v[613,9] = 571
		v[614,9] = 555
		v[615,9] = 109
		v[616,9] = 377
		v[617,9] = 931
		v[618,9] = 499
		v[619,9] = 649
		v[620,9] = 653
		v[621,9] = 329
		v[622,9] = 279
		v[623,9] = 271
		v[624,9] = 647
		v[625,9] = 721
		v[626,9] = 665
		v[627,9] = 429
		v[628,9] = 957
		v[629,9] = 803
		v[630,9] = 767
		v[631,9] = 425
		v[632,9] = 477
		v[633,9] = 995
		v[634,9] = 105
		v[635,9] = 495
		v[636,9] = 575
		v[637,9] = 687
		v[638,9] = 385
		v[639,9] = 227
		v[640,9] = 923
		v[641,9] = 563
		v[642,9] = 723
		v[643,9] = 481
		v[644,9] = 717
		v[645,9] = 111
		v[646,9] = 633
		v[647,9] = 113
		v[648,9] = 369
		v[649,9] = 955
		v[650,9] = 253
		v[651,9] = 321
		v[652,9] = 409
		v[653,9] = 909
		v[654,9] = 367
		v[655,9] = 33
		v[656,9] = 967
		v[657,9] = 453
		v[658,9] = 863
		v[659,9] = 449
		v[660,9] = 539
		v[661,9] = 781
		v[662,9] = 911
		v[663,9] = 113
		v[664,9] = 7
		v[665,9] = 219
		v[666,9] = 725
		v[667,9] = 1015
		v[668,9] = 971
		v[669,9] = 1021
		v[670,9] = 525
		v[671,9] = 785
		v[672,9] = 873
		v[673,9] = 191
		v[674,9] = 893
		v[675,9] = 297
		v[676,9] = 507
		v[677,9] = 215
		v[678,9] = 21
		v[679,9] = 153
		v[680,9] = 645
		v[681,9] = 913
		v[682,9] = 755
		v[683,9] = 371
		v[684,9] = 881
		v[685,9] = 113
		v[686,9] = 903
		v[687,9] = 225
		v[688,9] = 49
		v[689,9] = 587
		v[690,9] = 201
		v[691,9] = 927
		v[692,9] = 429
		v[693,9] = 599
		v[694,9] = 513
		v[695,9] = 97
		v[696,9] = 319
		v[697,9] = 331
		v[698,9] = 833
		v[699,9] = 325
		v[700,9] = 887
		v[701,9] = 139
		v[702,9] = 927
		v[703,9] = 399
		v[704,9] = 163
		v[705,9] = 307
		v[706,9] = 803
		v[707,9] = 169
		v[708,9] = 1019
		v[709,9] = 869
		v[710,9] = 537
		v[711,9] = 907
		v[712,9] = 479
		v[713,9] = 335
		v[714,9] = 697
		v[715,9] = 479
		v[716,9] = 353
		v[717,9] = 769
		v[718,9] = 787
		v[719,9] = 1023
		v[720,9] = 855
		v[721,9] = 493
		v[722,9] = 883
		v[723,9] = 521
		v[724,9] = 735
		v[725,9] = 297
		v[726,9] = 1011
		v[727,9] = 991
		v[728,9] = 879
		v[729,9] = 855
		v[730,9] = 591
		v[731,9] = 415
		v[732,9] = 917
		v[733,9] = 375
		v[734,9] = 453
		v[735,9] = 553
		v[736,9] = 189
		v[737,9] = 841
		v[738,9] = 339
		v[739,9] = 211
		v[740,9] = 601
		v[741,9] = 57
		v[742,9] = 765
		v[743,9] = 745
		v[744,9] = 621
		v[745,9] = 209
		v[746,9] = 875
		v[747,9] = 639
		v[748,9] = 7
		v[749,9] = 595
		v[750,9] = 971
		v[751,9] = 263
		v[752,9] = 1009
		v[753,9] = 201
		v[754,9] = 23
		v[755,9] = 77
		v[756,9] = 621
		v[757,9] = 33
		v[758,9] = 535
		v[759,9] = 963
		v[760,9] = 661
		v[761,9] = 523
		v[762,9] = 263
		v[763,9] = 917
		v[764,9] = 103
		v[765,9] = 623
		v[766,9] = 231
		v[767,9] = 47
		v[768,9] = 301
		v[769,9] = 549
		v[770,9] = 337
		v[771,9] = 675
		v[772,9] = 189
		v[773,9] = 357
		v[774,9] = 1005
		v[775,9] = 789
		v[776,9] = 189
		v[777,9] = 319
		v[778,9] = 721
		v[779,9] = 1005
		v[780,9] = 525
		v[781,9] = 675
		v[782,9] = 539
		v[783,9] = 191
		v[784,9] = 813
		v[785,9] = 917
		v[786,9] = 51
		v[787,9] = 167
		v[788,9] = 415
		v[789,9] = 579
		v[790,9] = 755
		v[791,9] = 605
		v[792,9] = 721
		v[793,9] = 837
		v[794,9] = 529
		v[795,9] = 31
		v[796,9] = 327
		v[797,9] = 799
		v[798,9] = 961
		v[799,9] = 279
		v[800,9] = 409
		v[801,9] = 847
		v[802,9] = 649
		v[803,9] = 241
		v[804,9] = 285
		v[805,9] = 545
		v[806,9] = 407
		v[807,9] = 161
		v[808,9] = 591
		v[809,9] = 73
		v[810,9] = 313
		v[811,9] = 811
		v[812,9] = 17
		v[813,9] = 663
		v[814,9] = 269
		v[815,9] = 261
		v[816,9] = 37
		v[817,9] = 783
		v[818,9] = 127
		v[819,9] = 917
		v[820,9] = 231
		v[821,9] = 577
		v[822,9] = 975
		v[823,9] = 793
		v[824,9] = 921
		v[825,9] = 343
		v[826,9] = 751
		v[827,9] = 139
		v[828,9] = 221
		v[829,9] = 79
		v[830,9] = 817
		v[831,9] = 393
		v[832,9] = 545
		v[833,9] = 11
		v[834,9] = 781
		v[835,9] = 71
		v[836,9] = 1
		v[837,9] = 699
		v[838,9] = 767
		v[839,9] = 917
		v[840,9] = 9
		v[841,9] = 107
		v[842,9] = 341
		v[843,9] = 587
		v[844,9] = 903
		v[845,9] = 965
		v[846,9] = 599
		v[847,9] = 507
		v[848,9] = 843
		v[849,9] = 739
		v[850,9] = 579
		v[851,9] = 397
		v[852,9] = 397
		v[853,9] = 325
		v[854,9] = 775
		v[855,9] = 565
		v[856,9] = 925
		v[857,9] = 75
		v[858,9] = 55
		v[859,9] = 979
		v[860,9] = 931
		v[861,9] = 93
		v[862,9] = 957
		v[863,9] = 857
		v[864,9] = 753
		v[865,9] = 965
		v[866,9] = 795
		v[867,9] = 67
		v[868,9] = 5
		v[869,9] = 87
		v[870,9] = 909
		v[871,9] = 97
		v[872,9] = 995
		v[873,9] = 271
		v[874,9] = 875
		v[875,9] = 671
		v[876,9] = 613
		v[877,9] = 33
		v[878,9] = 351
		v[879,9] = 69
		v[880,9] = 811
		v[881,9] = 669
		v[882,9] = 729
		v[883,9] = 401
		v[884,9] = 647
		v[885,9] = 241
		v[886,9] = 435
		v[887,9] = 447
		v[888,9] = 721
		v[889,9] = 271
		v[890,9] = 745
		v[891,9] = 53
		v[892,9] = 775
		v[893,9] = 99
		v[894,9] = 343
		v[895,9] = 451
		v[896,9] = 427
		v[897,9] = 593
		v[898,9] = 339
		v[899,9] = 845
		v[900,9] = 243
		v[901,9] = 345
		v[902,9] = 17
		v[903,9] = 573
		v[904,9] = 421
		v[905,9] = 517
		v[906,9] = 971
		v[907,9] = 499
		v[908,9] = 435
		v[909,9] = 769
		v[910,9] = 75
		v[911,9] = 203
		v[912,9] = 793
		v[913,9] = 985
		v[914,9] = 343
		v[915,9] = 955
		v[916,9] = 735
		v[917,9] = 523
		v[918,9] = 659
		v[919,9] = 703
		v[920,9] = 303
		v[921,9] = 421
		v[922,9] = 951
		v[923,9] = 405
		v[924,9] = 631
		v[925,9] = 825
		v[926,9] = 735
		v[927,9] = 433
		v[928,9] = 841
		v[929,9] = 485
		v[930,9] = 49
		v[931,9] = 749
		v[932,9] = 107
		v[933,9] = 669
		v[934,9] = 211
		v[935,9] = 497
		v[936,9] = 143
		v[937,9] = 99
		v[938,9] = 57
		v[939,9] = 277
		v[940,9] = 969
		v[941,9] = 107
		v[942,9] = 397
		v[943,9] = 563
		v[944,9] = 551
		v[945,9] = 447
		v[946,9] = 381
		v[947,9] = 187
		v[948,9] = 57
		v[949,9] = 405
		v[950,9] = 731
		v[951,9] = 769
		v[952,9] = 923
		v[953,9] = 955
		v[954,9] = 915
		v[955,9] = 737
		v[956,9] = 595
		v[957,9] = 341
		v[958,9] = 253
		v[959,9] = 823
		v[960,9] = 197
		v[961,9] = 321
		v[962,9] = 315
		v[963,9] = 181
		v[964,9] = 885
		v[965,9] = 497
		v[966,9] = 159
		v[967,9] = 571
		v[968,9] = 981
		v[969,9] = 899
		v[970,9] = 785
		v[971,9] = 947
		v[972,9] = 217
		v[973,9] = 217
		v[974,9] = 135
		v[975,9] = 753
		v[976,9] = 623
		v[977,9] = 565
		v[978,9] = 717
		v[979,9] = 903
		v[980,9] = 581
		v[981,9] = 955
		v[982,9] = 621
		v[983,9] = 361
		v[984,9] = 869
		v[985,9] = 87
		v[986,9] = 943
		v[987,9] = 907
		v[988,9] = 853
		v[989,9] = 353
		v[990,9] = 335
		v[991,9] = 197
		v[992,9] = 771
		v[993,9] = 433
		v[994,9] = 743
		v[995,9] = 195
		v[996,9] = 91
		v[997,9] = 1023
		v[998,9] = 63
		v[999,9] = 301
		v[1000,9] = 647
		v[1001,9] = 205
		v[1002,9] = 485
		v[1003,9] = 927
		v[1004,9] = 1003
		v[1005,9] = 987
		v[1006,9] = 359
		v[1007,9] = 577
		v[1008,9] = 147
		v[1009,9] = 141
		v[1010,9] = 1017
		v[1011,9] = 701
		v[1012,9] = 273
		v[1013,9] = 89
		v[1014,9] = 589
		v[1015,9] = 487
		v[1016,9] = 859
		v[1017,9] = 343
		v[1018,9] = 91
		v[1019,9] = 847
		v[1020,9] = 341
		v[1021,9] = 173
		v[1022,9] = 287
		v[1023,9] = 1003
		v[1024,9] = 289
		v[1025,9] = 639
		v[1026,9] = 983
		v[1027,9] = 685
		v[1028,9] = 697
		v[1029,9] = 35
		v[1030,9] = 701
		v[1031,9] = 645
		v[1032,9] = 911
		v[1033,9] = 501
		v[1034,9] = 705
		v[1035,9] = 873
		v[1036,9] = 763
		v[1037,9] = 745
		v[1038,9] = 657
		v[1039,9] = 559
		v[1040,9] = 699
		v[1041,9] = 315
		v[1042,9] = 347
		v[1043,9] = 429
		v[1044,9] = 197
		v[1045,9] = 165
		v[1046,9] = 955
		v[1047,9] = 859
		v[1048,9] = 167
		v[1049,9] = 303
		v[1050,9] = 833
		v[1051,9] = 531
		v[1052,9] = 473
		v[1053,9] = 635
		v[1054,9] = 641
		v[1055,9] = 195
		v[1056,9] = 589
		v[1057,9] = 821
		v[1058,9] = 205
		v[1059,9] = 3
		v[1060,9] = 635
		v[1061,9] = 371
		v[1062,9] = 891
		v[1063,9] = 249
		v[1064,9] = 123
		v[1065,9] = 77
		v[1066,9] = 623
		v[1067,9] = 993
		v[1068,9] = 401
		v[1069,9] = 525
		v[1070,9] = 427
		v[1071,9] = 71
		v[1072,9] = 655
		v[1073,9] = 951
		v[1074,9] = 357
		v[1075,9] = 851
		v[1076,9] = 899
		v[1077,9] = 535
		v[1078,9] = 493
		v[1079,9] = 323
		v[1080,9] = 1003
		v[1081,9] = 343
		v[1082,9] = 515
		v[1083,9] = 859
		v[1084,9] = 1017
		v[1085,9] = 5
		v[1086,9] = 423
		v[1087,9] = 315
		v[1088,9] = 1011
		v[1089,9] = 703
		v[1090,9] = 41
		v[1091,9] = 777
		v[1092,9] = 163
		v[1093,9] = 95
		v[1094,9] = 831
		v[1095,9] = 79
		v[1096,9] = 975
		v[1097,9] = 235
		v[1098,9] = 633
		v[1099,9] = 723
		v[1100,9] = 297
		v[1101,9] = 589
		v[1102,9] = 317
		v[1103,9] = 679
		v[1104,9] = 981
		v[1105,9] = 195
		v[1106,9] = 399
		v[1107,9] = 1003
		v[1108,9] = 121
		v[1109,9] = 501
		v[1110,9] = 155

		v[161,10] = 7
		v[162,10] = 2011
		v[163,10] = 1001
		v[164,10] = 49
		v[165,10] = 825
		v[166,10] = 415
		v[167,10] = 1441
		v[168,10] = 383
		v[169,10] = 1581
		v[170,10] = 623
		v[171,10] = 1621
		v[172,10] = 1319
		v[173,10] = 1387
		v[174,10] = 619
		v[175,10] = 839
		v[176,10] = 217
		v[177,10] = 75
		v[178,10] = 1955
		v[179,10] = 505
		v[180,10] = 281
		v[181,10] = 1629
		v[182,10] = 1379
		v[183,10] = 53
		v[184,10] = 1111
		v[185,10] = 1399
		v[186,10] = 301
		v[187,10] = 209
		v[188,10] = 49
		v[189,10] = 155
		v[190,10] = 1647
		v[191,10] = 631
		v[192,10] = 129
		v[193,10] = 1569
		v[194,10] = 335
		v[195,10] = 67
		v[196,10] = 1955
		v[197,10] = 1611
		v[198,10] = 2021
		v[199,10] = 1305
		v[200,10] = 121
		v[201,10] = 37
		v[202,10] = 877
		v[203,10] = 835
		v[204,10] = 1457
		v[205,10] = 669
		v[206,10] = 1405
		v[207,10] = 935
		v[208,10] = 1735
		v[209,10] = 665
		v[210,10] = 551
		v[211,10] = 789
		v[212,10] = 1543
		v[213,10] = 1267
		v[214,10] = 1027
		v[215,10] = 1
		v[216,10] = 1911
		v[217,10] = 163
		v[218,10] = 1929
		v[219,10] = 67
		v[220,10] = 1975
		v[221,10] = 1681
		v[222,10] = 1413
		v[223,10] = 191
		v[224,10] = 1711
		v[225,10] = 1307
		v[226,10] = 401
		v[227,10] = 725
		v[228,10] = 1229
		v[229,10] = 1403
		v[230,10] = 1609
		v[231,10] = 2035
		v[232,10] = 917
		v[233,10] = 921
		v[234,10] = 1789
		v[235,10] = 41
		v[236,10] = 2003
		v[237,10] = 187
		v[238,10] = 67
		v[239,10] = 1635
		v[240,10] = 717
		v[241,10] = 1449
		v[242,10] = 277
		v[243,10] = 1903
		v[244,10] = 1179
		v[245,10] = 363
		v[246,10] = 1211
		v[247,10] = 1231
		v[248,10] = 647
		v[249,10] = 1261
		v[250,10] = 1029
		v[251,10] = 1485
		v[252,10] = 1309
		v[253,10] = 1149
		v[254,10] = 317
		v[255,10] = 1335
		v[256,10] = 171
		v[257,10] = 243
		v[258,10] = 271
		v[259,10] = 1055
		v[260,10] = 1601
		v[261,10] = 1129
		v[262,10] = 1653
		v[263,10] = 205
		v[264,10] = 1463
		v[265,10] = 1681
		v[266,10] = 1621
		v[267,10] = 197
		v[268,10] = 951
		v[269,10] = 573
		v[270,10] = 1697
		v[271,10] = 1265
		v[272,10] = 1321
		v[273,10] = 1805
		v[274,10] = 1235
		v[275,10] = 1853
		v[276,10] = 1307
		v[277,10] = 945
		v[278,10] = 1197
		v[279,10] = 1411
		v[280,10] = 833
		v[281,10] = 273
		v[282,10] = 1517
		v[283,10] = 1747
		v[284,10] = 1095
		v[285,10] = 1345
		v[286,10] = 869
		v[287,10] = 57
		v[288,10] = 1383
		v[289,10] = 221
		v[290,10] = 1713
		v[291,10] = 335
		v[292,10] = 1751
		v[293,10] = 1141
		v[294,10] = 839
		v[295,10] = 523
		v[296,10] = 1861
		v[297,10] = 1105
		v[298,10] = 389
		v[299,10] = 1177
		v[300,10] = 1877
		v[301,10] = 805
		v[302,10] = 93
		v[303,10] = 1591
		v[304,10] = 423
		v[305,10] = 1835
		v[306,10] = 99
		v[307,10] = 1781
		v[308,10] = 1515
		v[309,10] = 1909
		v[310,10] = 1011
		v[311,10] = 303
		v[312,10] = 385
		v[313,10] = 1635
		v[314,10] = 357
		v[315,10] = 973
		v[316,10] = 1781
		v[317,10] = 1707
		v[318,10] = 1363
		v[319,10] = 1053
		v[320,10] = 649
		v[321,10] = 1469
		v[322,10] = 623
		v[323,10] = 1429
		v[324,10] = 1241
		v[325,10] = 1151
		v[326,10] = 1055
		v[327,10] = 503
		v[328,10] = 921
		v[329,10] = 3
		v[330,10] = 349
		v[331,10] = 1149
		v[332,10] = 293
		v[333,10] = 45
		v[334,10] = 303
		v[335,10] = 877
		v[336,10] = 1565
		v[337,10] = 1583
		v[338,10] = 1001
		v[339,10] = 663
		v[340,10] = 1535
		v[341,10] = 395
		v[342,10] = 1141
		v[343,10] = 1481
		v[344,10] = 1797
		v[345,10] = 643
		v[346,10] = 1507
		v[347,10] = 465
		v[348,10] = 2027
		v[349,10] = 1695
		v[350,10] = 367
		v[351,10] = 937
		v[352,10] = 719
		v[353,10] = 545
		v[354,10] = 1991
		v[355,10] = 83
		v[356,10] = 819
		v[357,10] = 239
		v[358,10] = 1791
		v[359,10] = 1461
		v[360,10] = 1647
		v[361,10] = 1501
		v[362,10] = 1161
		v[363,10] = 1629
		v[364,10] = 139
		v[365,10] = 1595
		v[366,10] = 1921
		v[367,10] = 1267
		v[368,10] = 1415
		v[369,10] = 509
		v[370,10] = 347
		v[371,10] = 777
		v[372,10] = 1083
		v[373,10] = 363
		v[374,10] = 269
		v[375,10] = 1015
		v[376,10] = 1809
		v[377,10] = 1105
		v[378,10] = 1429
		v[379,10] = 1471
		v[380,10] = 2019
		v[381,10] = 381
		v[382,10] = 2025
		v[383,10] = 1223
		v[384,10] = 827
		v[385,10] = 1733
		v[386,10] = 887
		v[387,10] = 1321
		v[388,10] = 803
		v[389,10] = 1951
		v[390,10] = 1297
		v[391,10] = 1995
		v[392,10] = 833
		v[393,10] = 1107
		v[394,10] = 1135
		v[395,10] = 1181
		v[396,10] = 1251
		v[397,10] = 983
		v[398,10] = 1389
		v[399,10] = 1565
		v[400,10] = 273
		v[401,10] = 137
		v[402,10] = 71
		v[403,10] = 735
		v[404,10] = 1005
		v[405,10] = 933
		v[406,10] = 67
		v[407,10] = 1471
		v[408,10] = 551
		v[409,10] = 457
		v[410,10] = 1667
		v[411,10] = 1729
		v[412,10] = 919
		v[413,10] = 285
		v[414,10] = 1629
		v[415,10] = 1815
		v[416,10] = 653
		v[417,10] = 1919
		v[418,10] = 1039
		v[419,10] = 531
		v[420,10] = 393
		v[421,10] = 1411
		v[422,10] = 359
		v[423,10] = 221
		v[424,10] = 699
		v[425,10] = 1485
		v[426,10] = 471
		v[427,10] = 1357
		v[428,10] = 1715
		v[429,10] = 595
		v[430,10] = 1677
		v[431,10] = 153
		v[432,10] = 1903
		v[433,10] = 1281
		v[434,10] = 215
		v[435,10] = 781
		v[436,10] = 543
		v[437,10] = 293
		v[438,10] = 1807
		v[439,10] = 965
		v[440,10] = 1695
		v[441,10] = 443
		v[442,10] = 1985
		v[443,10] = 321
		v[444,10] = 879
		v[445,10] = 1227
		v[446,10] = 1915
		v[447,10] = 839
		v[448,10] = 1945
		v[449,10] = 1993
		v[450,10] = 1165
		v[451,10] = 51
		v[452,10] = 557
		v[453,10] = 723
		v[454,10] = 1491
		v[455,10] = 817
		v[456,10] = 1237
		v[457,10] = 947
		v[458,10] = 1215
		v[459,10] = 1911
		v[460,10] = 1225
		v[461,10] = 1965
		v[462,10] = 1889
		v[463,10] = 1503
		v[464,10] = 1177
		v[465,10] = 73
		v[466,10] = 1767
		v[467,10] = 303
		v[468,10] = 177
		v[469,10] = 1897
		v[470,10] = 1401
		v[471,10] = 321
		v[472,10] = 921
		v[473,10] = 217
		v[474,10] = 1779
		v[475,10] = 327
		v[476,10] = 1889
		v[477,10] = 333
		v[478,10] = 615
		v[479,10] = 1665
		v[480,10] = 1825
		v[481,10] = 1639
		v[482,10] = 237
		v[483,10] = 1205
		v[484,10] = 361
		v[485,10] = 129
		v[486,10] = 1655
		v[487,10] = 983
		v[488,10] = 1089
		v[489,10] = 1171
		v[490,10] = 401
		v[491,10] = 677
		v[492,10] = 643
		v[493,10] = 749
		v[494,10] = 303
		v[495,10] = 1407
		v[496,10] = 1873
		v[497,10] = 1579
		v[498,10] = 1491
		v[499,10] = 1393
		v[500,10] = 1247
		v[501,10] = 789
		v[502,10] = 763
		v[503,10] = 49
		v[504,10] = 5
		v[505,10] = 1607
		v[506,10] = 1891
		v[507,10] = 735
		v[508,10] = 1557
		v[509,10] = 1909
		v[510,10] = 1765
		v[511,10] = 1777
		v[512,10] = 1127
		v[513,10] = 813
		v[514,10] = 695
		v[515,10] = 97
		v[516,10] = 731
		v[517,10] = 1503
		v[518,10] = 1751
		v[519,10] = 333
		v[520,10] = 769
		v[521,10] = 865
		v[522,10] = 693
		v[523,10] = 377
		v[524,10] = 1919
		v[525,10] = 957
		v[526,10] = 1359
		v[527,10] = 1627
		v[528,10] = 1039
		v[529,10] = 1783
		v[530,10] = 1065
		v[531,10] = 1665
		v[532,10] = 1917
		v[533,10] = 1947
		v[534,10] = 991
		v[535,10] = 1997
		v[536,10] = 841
		v[537,10] = 459
		v[538,10] = 221
		v[539,10] = 327
		v[540,10] = 1595
		v[541,10] = 1881
		v[542,10] = 1269
		v[543,10] = 1007
		v[544,10] = 129
		v[545,10] = 1413
		v[546,10] = 475
		v[547,10] = 1105
		v[548,10] = 791
		v[549,10] = 1983
		v[550,10] = 1359
		v[551,10] = 503
		v[552,10] = 691
		v[553,10] = 659
		v[554,10] = 691
		v[555,10] = 343
		v[556,10] = 1375
		v[557,10] = 1919
		v[558,10] = 263
		v[559,10] = 1373
		v[560,10] = 603
		v[561,10] = 1383
		v[562,10] = 297
		v[563,10] = 781
		v[564,10] = 145
		v[565,10] = 285
		v[566,10] = 767
		v[567,10] = 1739
		v[568,10] = 1715
		v[569,10] = 715
		v[570,10] = 317
		v[571,10] = 1333
		v[572,10] = 85
		v[573,10] = 831
		v[574,10] = 1615
		v[575,10] = 81
		v[576,10] = 1667
		v[577,10] = 1467
		v[578,10] = 1457
		v[579,10] = 1453
		v[580,10] = 1825
		v[581,10] = 109
		v[582,10] = 387
		v[583,10] = 1207
		v[584,10] = 2039
		v[585,10] = 213
		v[586,10] = 1351
		v[587,10] = 1329
		v[588,10] = 1173
		v[589,10] = 57
		v[590,10] = 1769
		v[591,10] = 951
		v[592,10] = 183
		v[593,10] = 23
		v[594,10] = 451
		v[595,10] = 1155
		v[596,10] = 1551
		v[597,10] = 2037
		v[598,10] = 811
		v[599,10] = 635
		v[600,10] = 1671
		v[601,10] = 1451
		v[602,10] = 863
		v[603,10] = 1499
		v[604,10] = 1673
		v[605,10] = 363
		v[606,10] = 1029
		v[607,10] = 1077
		v[608,10] = 1525
		v[609,10] = 277
		v[610,10] = 1023
		v[611,10] = 655
		v[612,10] = 665
		v[613,10] = 1869
		v[614,10] = 1255
		v[615,10] = 965
		v[616,10] = 277
		v[617,10] = 1601
		v[618,10] = 329
		v[619,10] = 1603
		v[620,10] = 1901
		v[621,10] = 395
		v[622,10] = 65
		v[623,10] = 1307
		v[624,10] = 2029
		v[625,10] = 21
		v[626,10] = 1321
		v[627,10] = 543
		v[628,10] = 1569
		v[629,10] = 1185
		v[630,10] = 1905
		v[631,10] = 1701
		v[632,10] = 413
		v[633,10] = 2041
		v[634,10] = 1697
		v[635,10] = 725
		v[636,10] = 1417
		v[637,10] = 1847
		v[638,10] = 411
		v[639,10] = 211
		v[640,10] = 915
		v[641,10] = 1891
		v[642,10] = 17
		v[643,10] = 1877
		v[644,10] = 1699
		v[645,10] = 687
		v[646,10] = 1089
		v[647,10] = 1973
		v[648,10] = 1809
		v[649,10] = 851
		v[650,10] = 1495
		v[651,10] = 1257
		v[652,10] = 63
		v[653,10] = 1323
		v[654,10] = 1307
		v[655,10] = 609
		v[656,10] = 881
		v[657,10] = 1543
		v[658,10] = 177
		v[659,10] = 617
		v[660,10] = 1505
		v[661,10] = 1747
		v[662,10] = 1537
		v[663,10] = 925
		v[664,10] = 183
		v[665,10] = 77
		v[666,10] = 1723
		v[667,10] = 1877
		v[668,10] = 1703
		v[669,10] = 397
		v[670,10] = 459
		v[671,10] = 521
		v[672,10] = 257
		v[673,10] = 1177
		v[674,10] = 389
		v[675,10] = 1947
		v[676,10] = 1553
		v[677,10] = 1583
		v[678,10] = 1831
		v[679,10] = 261
		v[680,10] = 485
		v[681,10] = 289
		v[682,10] = 1281
		v[683,10] = 1543
		v[684,10] = 1591
		v[685,10] = 1123
		v[686,10] = 573
		v[687,10] = 821
		v[688,10] = 1065
		v[689,10] = 1933
		v[690,10] = 1373
		v[691,10] = 2005
		v[692,10] = 905
		v[693,10] = 207
		v[694,10] = 173
		v[695,10] = 1573
		v[696,10] = 1597
		v[697,10] = 573
		v[698,10] = 1883
		v[699,10] = 1795
		v[700,10] = 1499
		v[701,10] = 1743
		v[702,10] = 553
		v[703,10] = 335
		v[704,10] = 333
		v[705,10] = 1645
		v[706,10] = 791
		v[707,10] = 871
		v[708,10] = 1157
		v[709,10] = 969
		v[710,10] = 557
		v[711,10] = 141
		v[712,10] = 223
		v[713,10] = 1129
		v[714,10] = 1685
		v[715,10] = 423
		v[716,10] = 1069
		v[717,10] = 391
		v[718,10] = 99
		v[719,10] = 95
		v[720,10] = 1847
		v[721,10] = 531
		v[722,10] = 1859
		v[723,10] = 1833
		v[724,10] = 1833
		v[725,10] = 341
		v[726,10] = 237
		v[727,10] = 1997
		v[728,10] = 1799
		v[729,10] = 409
		v[730,10] = 431
		v[731,10] = 1917
		v[732,10] = 363
		v[733,10] = 335
		v[734,10] = 1039
		v[735,10] = 1085
		v[736,10] = 1657
		v[737,10] = 1975
		v[738,10] = 1527
		v[739,10] = 1111
		v[740,10] = 659
		v[741,10] = 389
		v[742,10] = 899
		v[743,10] = 595
		v[744,10] = 1439
		v[745,10] = 1861
		v[746,10] = 1979
		v[747,10] = 1569
		v[748,10] = 1087
		v[749,10] = 1009
		v[750,10] = 165
		v[751,10] = 1895
		v[752,10] = 1481
		v[753,10] = 1583
		v[754,10] = 29
		v[755,10] = 1193
		v[756,10] = 1673
		v[757,10] = 1075
		v[758,10] = 301
		v[759,10] = 1081
		v[760,10] = 1377
		v[761,10] = 1747
		v[762,10] = 1497
		v[763,10] = 1103
		v[764,10] = 1789
		v[765,10] = 887
		v[766,10] = 739
		v[767,10] = 1577
		v[768,10] = 313
		v[769,10] = 1367
		v[770,10] = 1299
		v[771,10] = 1801
		v[772,10] = 1131
		v[773,10] = 1837
		v[774,10] = 73
		v[775,10] = 1865
		v[776,10] = 1065
		v[777,10] = 843
		v[778,10] = 635
		v[779,10] = 55
		v[780,10] = 1655
		v[781,10] = 913
		v[782,10] = 1037
		v[783,10] = 223
		v[784,10] = 1871
		v[785,10] = 1161
		v[786,10] = 461
		v[787,10] = 479
		v[788,10] = 511
		v[789,10] = 1721
		v[790,10] = 1107
		v[791,10] = 389
		v[792,10] = 151
		v[793,10] = 35
		v[794,10] = 375
		v[795,10] = 1099
		v[796,10] = 937
		v[797,10] = 1185
		v[798,10] = 1701
		v[799,10] = 769
		v[800,10] = 639
		v[801,10] = 1633
		v[802,10] = 1609
		v[803,10] = 379
		v[804,10] = 1613
		v[805,10] = 2031
		v[806,10] = 685
		v[807,10] = 289
		v[808,10] = 975
		v[809,10] = 671
		v[810,10] = 1599
		v[811,10] = 1447
		v[812,10] = 871
		v[813,10] = 647
		v[814,10] = 99
		v[815,10] = 139
		v[816,10] = 1427
		v[817,10] = 959
		v[818,10] = 89
		v[819,10] = 117
		v[820,10] = 841
		v[821,10] = 891
		v[822,10] = 1959
		v[823,10] = 223
		v[824,10] = 1697
		v[825,10] = 1145
		v[826,10] = 499
		v[827,10] = 1435
		v[828,10] = 1809
		v[829,10] = 1413
		v[830,10] = 1445
		v[831,10] = 1675
		v[832,10] = 171
		v[833,10] = 1073
		v[834,10] = 1349
		v[835,10] = 1545
		v[836,10] = 2039
		v[837,10] = 1027
		v[838,10] = 1563
		v[839,10] = 859
		v[840,10] = 215
		v[841,10] = 1673
		v[842,10] = 1919
		v[843,10] = 1633
		v[844,10] = 779
		v[845,10] = 411
		v[846,10] = 1845
		v[847,10] = 1477
		v[848,10] = 1489
		v[849,10] = 447
		v[850,10] = 1545
		v[851,10] = 351
		v[852,10] = 1989
		v[853,10] = 495
		v[854,10] = 183
		v[855,10] = 1639
		v[856,10] = 1385
		v[857,10] = 1805
		v[858,10] = 1097
		v[859,10] = 1249
		v[860,10] = 1431
		v[861,10] = 1571
		v[862,10] = 591
		v[863,10] = 697
		v[864,10] = 1509
		v[865,10] = 709
		v[866,10] = 31
		v[867,10] = 1563
		v[868,10] = 165
		v[869,10] = 513
		v[870,10] = 1425
		v[871,10] = 1299
		v[872,10] = 1081
		v[873,10] = 145
		v[874,10] = 1841
		v[875,10] = 1211
		v[876,10] = 941
		v[877,10] = 609
		v[878,10] = 845
		v[879,10] = 1169
		v[880,10] = 1865
		v[881,10] = 1593
		v[882,10] = 347
		v[883,10] = 293
		v[884,10] = 1277
		v[885,10] = 157
		v[886,10] = 211
		v[887,10] = 93
		v[888,10] = 1679
		v[889,10] = 1799
		v[890,10] = 527
		v[891,10] = 41
		v[892,10] = 473
		v[893,10] = 563
		v[894,10] = 187
		v[895,10] = 1525
		v[896,10] = 575
		v[897,10] = 1579
		v[898,10] = 857
		v[899,10] = 703
		v[900,10] = 1211
		v[901,10] = 647
		v[902,10] = 709
		v[903,10] = 981
		v[904,10] = 285
		v[905,10] = 697
		v[906,10] = 163
		v[907,10] = 981
		v[908,10] = 153
		v[909,10] = 1515
		v[910,10] = 47
		v[911,10] = 1553
		v[912,10] = 599
		v[913,10] = 225
		v[914,10] = 1147
		v[915,10] = 381
		v[916,10] = 135
		v[917,10] = 821
		v[918,10] = 1965
		v[919,10] = 609
		v[920,10] = 1033
		v[921,10] = 983
		v[922,10] = 503
		v[923,10] = 1117
		v[924,10] = 327
		v[925,10] = 453
		v[926,10] = 2005
		v[927,10] = 1257
		v[928,10] = 343
		v[929,10] = 1649
		v[930,10] = 1199
		v[931,10] = 599
		v[932,10] = 1877
		v[933,10] = 569
		v[934,10] = 695
		v[935,10] = 1587
		v[936,10] = 1475
		v[937,10] = 187
		v[938,10] = 973
		v[939,10] = 233
		v[940,10] = 511
		v[941,10] = 51
		v[942,10] = 1083
		v[943,10] = 665
		v[944,10] = 1321
		v[945,10] = 531
		v[946,10] = 1875
		v[947,10] = 1939
		v[948,10] = 859
		v[949,10] = 1507
		v[950,10] = 1979
		v[951,10] = 1203
		v[952,10] = 1965
		v[953,10] = 737
		v[954,10] = 921
		v[955,10] = 1565
		v[956,10] = 1943
		v[957,10] = 819
		v[958,10] = 223
		v[959,10] = 365
		v[960,10] = 167
		v[961,10] = 1705
		v[962,10] = 413
		v[963,10] = 1577
		v[964,10] = 745
		v[965,10] = 1573
		v[966,10] = 655
		v[967,10] = 1633
		v[968,10] = 1003
		v[969,10] = 91
		v[970,10] = 1123
		v[971,10] = 477
		v[972,10] = 1741
		v[973,10] = 1663
		v[974,10] = 35
		v[975,10] = 715
		v[976,10] = 37
		v[977,10] = 1513
		v[978,10] = 815
		v[979,10] = 941
		v[980,10] = 1379
		v[981,10] = 263
		v[982,10] = 1831
		v[983,10] = 1735
		v[984,10] = 1111
		v[985,10] = 1449
		v[986,10] = 353
		v[987,10] = 1941
		v[988,10] = 1655
		v[989,10] = 1349
		v[990,10] = 877
		v[991,10] = 285
		v[992,10] = 1723
		v[993,10] = 125
		v[994,10] = 1753
		v[995,10] = 985
		v[996,10] = 723
		v[997,10] = 175
		v[998,10] = 439
		v[999,10] = 791
		v[1000,10] = 1051
		v[1001,10] = 1261
		v[1002,10] = 717
		v[1003,10] = 1555
		v[1004,10] = 1757
		v[1005,10] = 1777
		v[1006,10] = 577
		v[1007,10] = 1583
		v[1008,10] = 1957
		v[1009,10] = 873
		v[1010,10] = 331
		v[1011,10] = 1163
		v[1012,10] = 313
		v[1013,10] = 1
		v[1014,10] = 1963
		v[1015,10] = 963
		v[1016,10] = 1905
		v[1017,10] = 821
		v[1018,10] = 1677
		v[1019,10] = 185
		v[1020,10] = 709
		v[1021,10] = 545
		v[1022,10] = 1723
		v[1023,10] = 215
		v[1024,10] = 1885
		v[1025,10] = 1249
		v[1026,10] = 583
		v[1027,10] = 1803
		v[1028,10] = 839
		v[1029,10] = 885
		v[1030,10] = 485
		v[1031,10] = 413
		v[1032,10] = 1767
		v[1033,10] = 425
		v[1034,10] = 129
		v[1035,10] = 1035
		v[1036,10] = 329
		v[1037,10] = 1263
		v[1038,10] = 1881
		v[1039,10] = 1779
		v[1040,10] = 1565
		v[1041,10] = 359
		v[1042,10] = 367
		v[1043,10] = 453
		v[1044,10] = 707
		v[1045,10] = 1419
		v[1046,10] = 831
		v[1047,10] = 1889
		v[1048,10] = 887
		v[1049,10] = 1871
		v[1050,10] = 1869
		v[1051,10] = 747
		v[1052,10] = 223
		v[1053,10] = 1547
		v[1054,10] = 1799
		v[1055,10] = 433
		v[1056,10] = 1441
		v[1057,10] = 553
		v[1058,10] = 2021
		v[1059,10] = 1303
		v[1060,10] = 1505
		v[1061,10] = 1735
		v[1062,10] = 1619
		v[1063,10] = 1065
		v[1064,10] = 1161
		v[1065,10] = 2047
		v[1066,10] = 347
		v[1067,10] = 867
		v[1068,10] = 881
		v[1069,10] = 1447
		v[1070,10] = 329
		v[1071,10] = 781
		v[1072,10] = 1065
		v[1073,10] = 219
		v[1074,10] = 589
		v[1075,10] = 645
		v[1076,10] = 1257
		v[1077,10] = 1833
		v[1078,10] = 749
		v[1079,10] = 1841
		v[1080,10] = 1733
		v[1081,10] = 1179
		v[1082,10] = 1191
		v[1083,10] = 1025
		v[1084,10] = 1639
		v[1085,10] = 1955
		v[1086,10] = 1423
		v[1087,10] = 1685
		v[1088,10] = 1711
		v[1089,10] = 493
		v[1090,10] = 549
		v[1091,10] = 783
		v[1092,10] = 1653
		v[1093,10] = 397
		v[1094,10] = 895
		v[1095,10] = 233
		v[1096,10] = 759
		v[1097,10] = 1505
		v[1098,10] = 677
		v[1099,10] = 1449
		v[1100,10] = 1573
		v[1101,10] = 1297
		v[1102,10] = 1821
		v[1103,10] = 1691
		v[1104,10] = 791
		v[1105,10] = 289
		v[1106,10] = 1187
		v[1107,10] = 867
		v[1108,10] = 1535
		v[1109,10] = 575
		v[1110,10] = 183

		v[337,11] = 3915
		v[338,11] = 97
		v[339,11] = 3047
		v[340,11] = 937
		v[341,11] = 2897
		v[342,11] = 953
		v[343,11] = 127
		v[344,11] = 1201
		v[345,11] = 3819
		v[346,11] = 193
		v[347,11] = 2053
		v[348,11] = 3061
		v[349,11] = 3759
		v[350,11] = 1553
		v[351,11] = 2007
		v[352,11] = 2493
		v[353,11] = 603
		v[354,11] = 3343
		v[355,11] = 3751
		v[356,11] = 1059
		v[357,11] = 783
		v[358,11] = 1789
		v[359,11] = 1589
		v[360,11] = 283
		v[361,11] = 1093
		v[362,11] = 3919
		v[363,11] = 2747
		v[364,11] = 277
		v[365,11] = 2605
		v[366,11] = 2169
		v[367,11] = 2905
		v[368,11] = 721
		v[369,11] = 4069
		v[370,11] = 233
		v[371,11] = 261
		v[372,11] = 1137
		v[373,11] = 3993
		v[374,11] = 3619
		v[375,11] = 2881
		v[376,11] = 1275
		v[377,11] = 3865
		v[378,11] = 1299
		v[379,11] = 3757
		v[380,11] = 1193
		v[381,11] = 733
		v[382,11] = 993
		v[383,11] = 1153
		v[384,11] = 2945
		v[385,11] = 3163
		v[386,11] = 3179
		v[387,11] = 437
		v[388,11] = 271
		v[389,11] = 3493
		v[390,11] = 3971
		v[391,11] = 1005
		v[392,11] = 2615
		v[393,11] = 2253
		v[394,11] = 1131
		v[395,11] = 585
		v[396,11] = 2775
		v[397,11] = 2171
		v[398,11] = 2383
		v[399,11] = 2937
		v[400,11] = 2447
		v[401,11] = 1745
		v[402,11] = 663
		v[403,11] = 1515
		v[404,11] = 3767
		v[405,11] = 2709
		v[406,11] = 1767
		v[407,11] = 3185
		v[408,11] = 3017
		v[409,11] = 2815
		v[410,11] = 1829
		v[411,11] = 87
		v[412,11] = 3341
		v[413,11] = 793
		v[414,11] = 2627
		v[415,11] = 2169
		v[416,11] = 1875
		v[417,11] = 3745
		v[418,11] = 367
		v[419,11] = 3783
		v[420,11] = 783
		v[421,11] = 827
		v[422,11] = 3253
		v[423,11] = 2639
		v[424,11] = 2955
		v[425,11] = 3539
		v[426,11] = 1579
		v[427,11] = 2109
		v[428,11] = 379
		v[429,11] = 2939
		v[430,11] = 3019
		v[431,11] = 1999
		v[432,11] = 2253
		v[433,11] = 2911
		v[434,11] = 3733
		v[435,11] = 481
		v[436,11] = 1767
		v[437,11] = 1055
		v[438,11] = 4019
		v[439,11] = 4085
		v[440,11] = 105
		v[441,11] = 1829
		v[442,11] = 2097
		v[443,11] = 2379
		v[444,11] = 1567
		v[445,11] = 2713
		v[446,11] = 737
		v[447,11] = 3423
		v[448,11] = 3941
		v[449,11] = 2659
		v[450,11] = 3961
		v[451,11] = 1755
		v[452,11] = 3613
		v[453,11] = 1937
		v[454,11] = 1559
		v[455,11] = 2287
		v[456,11] = 2743
		v[457,11] = 67
		v[458,11] = 2859
		v[459,11] = 325
		v[460,11] = 2601
		v[461,11] = 1149
		v[462,11] = 3259
		v[463,11] = 2403
		v[464,11] = 3947
		v[465,11] = 2011
		v[466,11] = 175
		v[467,11] = 3389
		v[468,11] = 3915
		v[469,11] = 1315
		v[470,11] = 2447
		v[471,11] = 141
		v[472,11] = 359
		v[473,11] = 3609
		v[474,11] = 3933
		v[475,11] = 729
		v[476,11] = 2051
		v[477,11] = 1755
		v[478,11] = 2149
		v[479,11] = 2107
		v[480,11] = 1741
		v[481,11] = 1051
		v[482,11] = 3681
		v[483,11] = 471
		v[484,11] = 1055
		v[485,11] = 845
		v[486,11] = 257
		v[487,11] = 1559
		v[488,11] = 1061
		v[489,11] = 2803
		v[490,11] = 2219
		v[491,11] = 1315
		v[492,11] = 1369
		v[493,11] = 3211
		v[494,11] = 4027
		v[495,11] = 105
		v[496,11] = 11
		v[497,11] = 1077
		v[498,11] = 2857
		v[499,11] = 337
		v[500,11] = 3553
		v[501,11] = 3503
		v[502,11] = 3917
		v[503,11] = 2665
		v[504,11] = 3823
		v[505,11] = 3403
		v[506,11] = 3711
		v[507,11] = 2085
		v[508,11] = 1103
		v[509,11] = 1641
		v[510,11] = 701
		v[511,11] = 4095
		v[512,11] = 2883
		v[513,11] = 1435
		v[514,11] = 653
		v[515,11] = 2363
		v[516,11] = 1597
		v[517,11] = 767
		v[518,11] = 869
		v[519,11] = 1825
		v[520,11] = 1117
		v[521,11] = 1297
		v[522,11] = 501
		v[523,11] = 505
		v[524,11] = 149
		v[525,11] = 873
		v[526,11] = 2673
		v[527,11] = 551
		v[528,11] = 1499
		v[529,11] = 2793
		v[530,11] = 3277
		v[531,11] = 2143
		v[532,11] = 3663
		v[533,11] = 533
		v[534,11] = 3991
		v[535,11] = 575
		v[536,11] = 1877
		v[537,11] = 1009
		v[538,11] = 3929
		v[539,11] = 473
		v[540,11] = 3009
		v[541,11] = 2595
		v[542,11] = 3249
		v[543,11] = 675
		v[544,11] = 3593
		v[545,11] = 2453
		v[546,11] = 1567
		v[547,11] = 973
		v[548,11] = 595
		v[549,11] = 1335
		v[550,11] = 1715
		v[551,11] = 589
		v[552,11] = 85
		v[553,11] = 2265
		v[554,11] = 3069
		v[555,11] = 461
		v[556,11] = 1659
		v[557,11] = 2627
		v[558,11] = 1307
		v[559,11] = 1731
		v[560,11] = 1501
		v[561,11] = 1699
		v[562,11] = 3545
		v[563,11] = 3803
		v[564,11] = 2157
		v[565,11] = 453
		v[566,11] = 2813
		v[567,11] = 2047
		v[568,11] = 2999
		v[569,11] = 3841
		v[570,11] = 2361
		v[571,11] = 1079
		v[572,11] = 573
		v[573,11] = 69
		v[574,11] = 1363
		v[575,11] = 1597
		v[576,11] = 3427
		v[577,11] = 2899
		v[578,11] = 2771
		v[579,11] = 1327
		v[580,11] = 1117
		v[581,11] = 1523
		v[582,11] = 3521
		v[583,11] = 2393
		v[584,11] = 2537
		v[585,11] = 1979
		v[586,11] = 3179
		v[587,11] = 683
		v[588,11] = 2453
		v[589,11] = 453
		v[590,11] = 1227
		v[591,11] = 779
		v[592,11] = 671
		v[593,11] = 3483
		v[594,11] = 2135
		v[595,11] = 3139
		v[596,11] = 3381
		v[597,11] = 3945
		v[598,11] = 57
		v[599,11] = 1541
		v[600,11] = 3405
		v[601,11] = 3381
		v[602,11] = 2371
		v[603,11] = 2879
		v[604,11] = 1985
		v[605,11] = 987
		v[606,11] = 3017
		v[607,11] = 3031
		v[608,11] = 3839
		v[609,11] = 1401
		v[610,11] = 3749
		v[611,11] = 2977
		v[612,11] = 681
		v[613,11] = 1175
		v[614,11] = 1519
		v[615,11] = 3355
		v[616,11] = 907
		v[617,11] = 117
		v[618,11] = 771
		v[619,11] = 3741
		v[620,11] = 3337
		v[621,11] = 1743
		v[622,11] = 1227
		v[623,11] = 3335
		v[624,11] = 2755
		v[625,11] = 1909
		v[626,11] = 3603
		v[627,11] = 2397
		v[628,11] = 653
		v[629,11] = 87
		v[630,11] = 2025
		v[631,11] = 2617
		v[632,11] = 3257
		v[633,11] = 287
		v[634,11] = 3051
		v[635,11] = 3809
		v[636,11] = 897
		v[637,11] = 2215
		v[638,11] = 63
		v[639,11] = 2043
		v[640,11] = 1757
		v[641,11] = 3671
		v[642,11] = 297
		v[643,11] = 3131
		v[644,11] = 1305
		v[645,11] = 293
		v[646,11] = 3865
		v[647,11] = 3173
		v[648,11] = 3397
		v[649,11] = 2269
		v[650,11] = 3673
		v[651,11] = 717
		v[652,11] = 3041
		v[653,11] = 3341
		v[654,11] = 3595
		v[655,11] = 3819
		v[656,11] = 2871
		v[657,11] = 3973
		v[658,11] = 1129
		v[659,11] = 513
		v[660,11] = 871
		v[661,11] = 1485
		v[662,11] = 3977
		v[663,11] = 2473
		v[664,11] = 1171
		v[665,11] = 1143
		v[666,11] = 3063
		v[667,11] = 3547
		v[668,11] = 2183
		v[669,11] = 3993
		v[670,11] = 133
		v[671,11] = 2529
		v[672,11] = 2699
		v[673,11] = 233
		v[674,11] = 2355
		v[675,11] = 231
		v[676,11] = 3241
		v[677,11] = 611
		v[678,11] = 1309
		v[679,11] = 3829
		v[680,11] = 1839
		v[681,11] = 1495
		v[682,11] = 301
		v[683,11] = 1169
		v[684,11] = 1613
		v[685,11] = 2673
		v[686,11] = 243
		v[687,11] = 3601
		v[688,11] = 3669
		v[689,11] = 2813
		v[690,11] = 2671
		v[691,11] = 2679
		v[692,11] = 3463
		v[693,11] = 2477
		v[694,11] = 1795
		v[695,11] = 617
		v[696,11] = 2317
		v[697,11] = 1855
		v[698,11] = 1057
		v[699,11] = 1703
		v[700,11] = 1761
		v[701,11] = 2515
		v[702,11] = 801
		v[703,11] = 1205
		v[704,11] = 1311
		v[705,11] = 473
		v[706,11] = 3963
		v[707,11] = 697
		v[708,11] = 1221
		v[709,11] = 251
		v[710,11] = 381
		v[711,11] = 3887
		v[712,11] = 1761
		v[713,11] = 3093
		v[714,11] = 3721
		v[715,11] = 2079
		v[716,11] = 4085
		v[717,11] = 379
		v[718,11] = 3601
		v[719,11] = 3845
		v[720,11] = 433
		v[721,11] = 1781
		v[722,11] = 29
		v[723,11] = 1897
		v[724,11] = 1599
		v[725,11] = 2163
		v[726,11] = 75
		v[727,11] = 3475
		v[728,11] = 3957
		v[729,11] = 1641
		v[730,11] = 3911
		v[731,11] = 2959
		v[732,11] = 2833
		v[733,11] = 1279
		v[734,11] = 1099
		v[735,11] = 403
		v[736,11] = 799
		v[737,11] = 2183
		v[738,11] = 2699
		v[739,11] = 1711
		v[740,11] = 2037
		v[741,11] = 727
		v[742,11] = 289
		v[743,11] = 1785
		v[744,11] = 1575
		v[745,11] = 3633
		v[746,11] = 2367
		v[747,11] = 1261
		v[748,11] = 3953
		v[749,11] = 1735
		v[750,11] = 171
		v[751,11] = 1959
		v[752,11] = 2867
		v[753,11] = 859
		v[754,11] = 2951
		v[755,11] = 3211
		v[756,11] = 15
		v[757,11] = 1279
		v[758,11] = 1323
		v[759,11] = 599
		v[760,11] = 1651
		v[761,11] = 3951
		v[762,11] = 1011
		v[763,11] = 315
		v[764,11] = 3513
		v[765,11] = 3351
		v[766,11] = 1725
		v[767,11] = 3793
		v[768,11] = 2399
		v[769,11] = 287
		v[770,11] = 4017
		v[771,11] = 3571
		v[772,11] = 1007
		v[773,11] = 541
		v[774,11] = 3115
		v[775,11] = 429
		v[776,11] = 1585
		v[777,11] = 1285
		v[778,11] = 755
		v[779,11] = 1211
		v[780,11] = 3047
		v[781,11] = 915
		v[782,11] = 3611
		v[783,11] = 2697
		v[784,11] = 2129
		v[785,11] = 3669
		v[786,11] = 81
		v[787,11] = 3939
		v[788,11] = 2437
		v[789,11] = 915
		v[790,11] = 779
		v[791,11] = 3567
		v[792,11] = 3701
		v[793,11] = 2479
		v[794,11] = 3807
		v[795,11] = 1893
		v[796,11] = 3927
		v[797,11] = 2619
		v[798,11] = 2543
		v[799,11] = 3633
		v[800,11] = 2007
		v[801,11] = 3857
		v[802,11] = 3837
		v[803,11] = 487
		v[804,11] = 1769
		v[805,11] = 3759
		v[806,11] = 3105
		v[807,11] = 2727
		v[808,11] = 3155
		v[809,11] = 2479
		v[810,11] = 1341
		v[811,11] = 1657
		v[812,11] = 2767
		v[813,11] = 2541
		v[814,11] = 577
		v[815,11] = 2105
		v[816,11] = 799
		v[817,11] = 17
		v[818,11] = 2871
		v[819,11] = 3637
		v[820,11] = 953
		v[821,11] = 65
		v[822,11] = 69
		v[823,11] = 2897
		v[824,11] = 3841
		v[825,11] = 3559
		v[826,11] = 4067
		v[827,11] = 2335
		v[828,11] = 3409
		v[829,11] = 1087
		v[830,11] = 425
		v[831,11] = 2813
		v[832,11] = 1705
		v[833,11] = 1701
		v[834,11] = 1237
		v[835,11] = 821
		v[836,11] = 1375
		v[837,11] = 3673
		v[838,11] = 2693
		v[839,11] = 3925
		v[840,11] = 1541
		v[841,11] = 1871
		v[842,11] = 2285
		v[843,11] = 847
		v[844,11] = 4035
		v[845,11] = 1101
		v[846,11] = 2029
		v[847,11] = 855
		v[848,11] = 2733
		v[849,11] = 2503
		v[850,11] = 121
		v[851,11] = 2855
		v[852,11] = 1069
		v[853,11] = 3463
		v[854,11] = 3505
		v[855,11] = 1539
		v[856,11] = 607
		v[857,11] = 1349
		v[858,11] = 575
		v[859,11] = 2301
		v[860,11] = 2321
		v[861,11] = 1101
		v[862,11] = 333
		v[863,11] = 291
		v[864,11] = 2171
		v[865,11] = 4085
		v[866,11] = 2173
		v[867,11] = 2541
		v[868,11] = 1195
		v[869,11] = 925
		v[870,11] = 4039
		v[871,11] = 1379
		v[872,11] = 699
		v[873,11] = 1979
		v[874,11] = 275
		v[875,11] = 953
		v[876,11] = 1755
		v[877,11] = 1643
		v[878,11] = 325
		v[879,11] = 101
		v[880,11] = 2263
		v[881,11] = 3329
		v[882,11] = 3673
		v[883,11] = 3413
		v[884,11] = 1977
		v[885,11] = 2727
		v[886,11] = 2313
		v[887,11] = 1419
		v[888,11] = 887
		v[889,11] = 609
		v[890,11] = 2475
		v[891,11] = 591
		v[892,11] = 2613
		v[893,11] = 2081
		v[894,11] = 3805
		v[895,11] = 3435
		v[896,11] = 2409
		v[897,11] = 111
		v[898,11] = 3557
		v[899,11] = 3607
		v[900,11] = 903
		v[901,11] = 231
		v[902,11] = 3059
		v[903,11] = 473
		v[904,11] = 2959
		v[905,11] = 2925
		v[906,11] = 3861
		v[907,11] = 2043
		v[908,11] = 3887
		v[909,11] = 351
		v[910,11] = 2865
		v[911,11] = 369
		v[912,11] = 1377
		v[913,11] = 2639
		v[914,11] = 1261
		v[915,11] = 3625
		v[916,11] = 3279
		v[917,11] = 2201
		v[918,11] = 2949
		v[919,11] = 3049
		v[920,11] = 449
		v[921,11] = 1297
		v[922,11] = 897
		v[923,11] = 1891
		v[924,11] = 411
		v[925,11] = 2773
		v[926,11] = 749
		v[927,11] = 2753
		v[928,11] = 1825
		v[929,11] = 853
		v[930,11] = 2775
		v[931,11] = 3547
		v[932,11] = 3923
		v[933,11] = 3923
		v[934,11] = 987
		v[935,11] = 3723
		v[936,11] = 2189
		v[937,11] = 3877
		v[938,11] = 3577
		v[939,11] = 297
		v[940,11] = 2763
		v[941,11] = 1845
		v[942,11] = 3083
		v[943,11] = 2951
		v[944,11] = 483
		v[945,11] = 2169
		v[946,11] = 3985
		v[947,11] = 245
		v[948,11] = 3655
		v[949,11] = 3441
		v[950,11] = 1023
		v[951,11] = 235
		v[952,11] = 835
		v[953,11] = 3693
		v[954,11] = 3585
		v[955,11] = 327
		v[956,11] = 1003
		v[957,11] = 543
		v[958,11] = 3059
		v[959,11] = 2637
		v[960,11] = 2923
		v[961,11] = 87
		v[962,11] = 3617
		v[963,11] = 1031
		v[964,11] = 1043
		v[965,11] = 903
		v[966,11] = 2913
		v[967,11] = 2177
		v[968,11] = 2641
		v[969,11] = 3279
		v[970,11] = 389
		v[971,11] = 2009
		v[972,11] = 525
		v[973,11] = 4085
		v[974,11] = 3299
		v[975,11] = 987
		v[976,11] = 2409
		v[977,11] = 813
		v[978,11] = 2683
		v[979,11] = 373
		v[980,11] = 2695
		v[981,11] = 3775
		v[982,11] = 2375
		v[983,11] = 1119
		v[984,11] = 2791
		v[985,11] = 223
		v[986,11] = 325
		v[987,11] = 587
		v[988,11] = 1379
		v[989,11] = 2877
		v[990,11] = 2867
		v[991,11] = 3793
		v[992,11] = 655
		v[993,11] = 831
		v[994,11] = 3425
		v[995,11] = 1663
		v[996,11] = 1681
		v[997,11] = 2657
		v[998,11] = 1865
		v[999,11] = 3943
		v[1000,11] = 2977
		v[1001,11] = 1979
		v[1002,11] = 2271
		v[1003,11] = 3247
		v[1004,11] = 1267
		v[1005,11] = 1747
		v[1006,11] = 811
		v[1007,11] = 159
		v[1008,11] = 429
		v[1009,11] = 2001
		v[1010,11] = 1195
		v[1011,11] = 3065
		v[1012,11] = 553
		v[1013,11] = 1499
		v[1014,11] = 3529
		v[1015,11] = 1081
		v[1016,11] = 2877
		v[1017,11] = 3077
		v[1018,11] = 845
		v[1019,11] = 1793
		v[1020,11] = 2409
		v[1021,11] = 3995
		v[1022,11] = 2559
		v[1023,11] = 4081
		v[1024,11] = 1195
		v[1025,11] = 2955
		v[1026,11] = 1117
		v[1027,11] = 1409
		v[1028,11] = 785
		v[1029,11] = 287
		v[1030,11] = 1521
		v[1031,11] = 1607
		v[1032,11] = 85
		v[1033,11] = 3055
		v[1034,11] = 3123
		v[1035,11] = 2533
		v[1036,11] = 2329
		v[1037,11] = 3477
		v[1038,11] = 799
		v[1039,11] = 3683
		v[1040,11] = 3715
		v[1041,11] = 337
		v[1042,11] = 3139
		v[1043,11] = 3311
		v[1044,11] = 431
		v[1045,11] = 3511
		v[1046,11] = 2299
		v[1047,11] = 365
		v[1048,11] = 2941
		v[1049,11] = 3067
		v[1050,11] = 1331
		v[1051,11] = 1081
		v[1052,11] = 1097
		v[1053,11] = 2853
		v[1054,11] = 2299
		v[1055,11] = 495
		v[1056,11] = 1745
		v[1057,11] = 749
		v[1058,11] = 3819
		v[1059,11] = 619
		v[1060,11] = 1059
		v[1061,11] = 3559
		v[1062,11] = 183
		v[1063,11] = 3743
		v[1064,11] = 723
		v[1065,11] = 949
		v[1066,11] = 3501
		v[1067,11] = 733
		v[1068,11] = 2599
		v[1069,11] = 3983
		v[1070,11] = 3961
		v[1071,11] = 911
		v[1072,11] = 1899
		v[1073,11] = 985
		v[1074,11] = 2493
		v[1075,11] = 1795
		v[1076,11] = 653
		v[1077,11] = 157
		v[1078,11] = 433
		v[1079,11] = 2361
		v[1080,11] = 3093
		v[1081,11] = 3119
		v[1082,11] = 3679
		v[1083,11] = 2367
		v[1084,11] = 1701
		v[1085,11] = 1445
		v[1086,11] = 1321
		v[1087,11] = 2397
		v[1088,11] = 1241
		v[1089,11] = 3305
		v[1090,11] = 3985
		v[1091,11] = 2349
		v[1092,11] = 4067
		v[1093,11] = 3805
		v[1094,11] = 3073
		v[1095,11] = 2837
		v[1096,11] = 1567
		v[1097,11] = 3783
		v[1098,11] = 451
		v[1099,11] = 2441
		v[1100,11] = 1181
		v[1101,11] = 487
		v[1102,11] = 543
		v[1103,11] = 1201
		v[1104,11] = 3735
		v[1105,11] = 2517
		v[1106,11] = 733
		v[1107,11] = 1535
		v[1108,11] = 2175
		v[1109,11] = 3613
		v[1110,11] = 3019

		v[481,12] = 2319
		v[482,12] = 653
		v[483,12] = 1379
		v[484,12] = 1675
		v[485,12] = 1951
		v[486,12] = 7075
		v[487,12] = 2087
		v[488,12] = 7147
		v[489,12] = 1427
		v[490,12] = 893
		v[491,12] = 171
		v[492,12] = 2019
		v[493,12] = 7235
		v[494,12] = 5697
		v[495,12] = 3615
		v[496,12] = 1961
		v[497,12] = 7517
		v[498,12] = 6849
		v[499,12] = 2893
		v[500,12] = 1883
		v[501,12] = 2863
		v[502,12] = 2173
		v[503,12] = 4543
		v[504,12] = 73
		v[505,12] = 381
		v[506,12] = 3893
		v[507,12] = 6045
		v[508,12] = 1643
		v[509,12] = 7669
		v[510,12] = 1027
		v[511,12] = 1549
		v[512,12] = 3983
		v[513,12] = 1985
		v[514,12] = 6589
		v[515,12] = 7497
		v[516,12] = 2745
		v[517,12] = 2375
		v[518,12] = 7047
		v[519,12] = 1117
		v[520,12] = 1171
		v[521,12] = 1975
		v[522,12] = 5199
		v[523,12] = 3915
		v[524,12] = 3695
		v[525,12] = 8113
		v[526,12] = 4303
		v[527,12] = 3773
		v[528,12] = 7705
		v[529,12] = 6855
		v[530,12] = 1675
		v[531,12] = 2245
		v[532,12] = 2817
		v[533,12] = 1719
		v[534,12] = 569
		v[535,12] = 1021
		v[536,12] = 2077
		v[537,12] = 5945
		v[538,12] = 1833
		v[539,12] = 2631
		v[540,12] = 4851
		v[541,12] = 6371
		v[542,12] = 833
		v[543,12] = 7987
		v[544,12] = 331
		v[545,12] = 1899
		v[546,12] = 8093
		v[547,12] = 6719
		v[548,12] = 6903
		v[549,12] = 5903
		v[550,12] = 5657
		v[551,12] = 5007
		v[552,12] = 2689
		v[553,12] = 6637
		v[554,12] = 2675
		v[555,12] = 1645
		v[556,12] = 1819
		v[557,12] = 689
		v[558,12] = 6709
		v[559,12] = 7717
		v[560,12] = 6295
		v[561,12] = 7013
		v[562,12] = 7695
		v[563,12] = 3705
		v[564,12] = 7069
		v[565,12] = 2621
		v[566,12] = 3631
		v[567,12] = 6571
		v[568,12] = 6259
		v[569,12] = 7261
		v[570,12] = 3397
		v[571,12] = 7645
		v[572,12] = 1115
		v[573,12] = 4753
		v[574,12] = 2047
		v[575,12] = 7579
		v[576,12] = 2271
		v[577,12] = 5403
		v[578,12] = 4911
		v[579,12] = 7629
		v[580,12] = 4225
		v[581,12] = 1209
		v[582,12] = 6955
		v[583,12] = 6951
		v[584,12] = 1829
		v[585,12] = 5579
		v[586,12] = 5231
		v[587,12] = 1783
		v[588,12] = 4285
		v[589,12] = 7425
		v[590,12] = 599
		v[591,12] = 5785
		v[592,12] = 3275
		v[593,12] = 5643
		v[594,12] = 2263
		v[595,12] = 657
		v[596,12] = 6769
		v[597,12] = 6261
		v[598,12] = 1251
		v[599,12] = 3249
		v[600,12] = 4447
		v[601,12] = 4111
		v[602,12] = 3991
		v[603,12] = 1215
		v[604,12] = 131
		v[605,12] = 4397
		v[606,12] = 3487
		v[607,12] = 7585
		v[608,12] = 5565
		v[609,12] = 7199
		v[610,12] = 3573
		v[611,12] = 7105
		v[612,12] = 7409
		v[613,12] = 1671
		v[614,12] = 949
		v[615,12] = 3889
		v[616,12] = 5971
		v[617,12] = 3333
		v[618,12] = 225
		v[619,12] = 3647
		v[620,12] = 5403
		v[621,12] = 3409
		v[622,12] = 7459
		v[623,12] = 6879
		v[624,12] = 5789
		v[625,12] = 6567
		v[626,12] = 5581
		v[627,12] = 4919
		v[628,12] = 1927
		v[629,12] = 4407
		v[630,12] = 8085
		v[631,12] = 4691
		v[632,12] = 611
		v[633,12] = 3005
		v[634,12] = 591
		v[635,12] = 753
		v[636,12] = 589
		v[637,12] = 171
		v[638,12] = 5729
		v[639,12] = 5891
		v[640,12] = 1033
		v[641,12] = 3049
		v[642,12] = 6567
		v[643,12] = 5257
		v[644,12] = 8003
		v[645,12] = 1757
		v[646,12] = 4489
		v[647,12] = 4923
		v[648,12] = 6379
		v[649,12] = 5171
		v[650,12] = 1757
		v[651,12] = 689
		v[652,12] = 3081
		v[653,12] = 1389
		v[654,12] = 4113
		v[655,12] = 455
		v[656,12] = 2761
		v[657,12] = 847
		v[658,12] = 7575
		v[659,12] = 5829
		v[660,12] = 633
		v[661,12] = 6629
		v[662,12] = 1103
		v[663,12] = 7635
		v[664,12] = 803
		v[665,12] = 6175
		v[666,12] = 6587
		v[667,12] = 2711
		v[668,12] = 3879
		v[669,12] = 67
		v[670,12] = 1179
		v[671,12] = 4761
		v[672,12] = 7281
		v[673,12] = 1557
		v[674,12] = 3379
		v[675,12] = 2459
		v[676,12] = 4273
		v[677,12] = 4127
		v[678,12] = 7147
		v[679,12] = 35
		v[680,12] = 3549
		v[681,12] = 395
		v[682,12] = 3735
		v[683,12] = 5787
		v[684,12] = 4179
		v[685,12] = 5889
		v[686,12] = 5057
		v[687,12] = 7473
		v[688,12] = 4713
		v[689,12] = 2133
		v[690,12] = 2897
		v[691,12] = 1841
		v[692,12] = 2125
		v[693,12] = 1029
		v[694,12] = 1695
		v[695,12] = 6523
		v[696,12] = 1143
		v[697,12] = 5105
		v[698,12] = 7133
		v[699,12] = 3351
		v[700,12] = 2775
		v[701,12] = 3971
		v[702,12] = 4503
		v[703,12] = 7589
		v[704,12] = 5155
		v[705,12] = 4305
		v[706,12] = 1641
		v[707,12] = 4717
		v[708,12] = 2427
		v[709,12] = 5617
		v[710,12] = 1267
		v[711,12] = 399
		v[712,12] = 5831
		v[713,12] = 4305
		v[714,12] = 4241
		v[715,12] = 3395
		v[716,12] = 3045
		v[717,12] = 4899
		v[718,12] = 1713
		v[719,12] = 171
		v[720,12] = 411
		v[721,12] = 7099
		v[722,12] = 5473
		v[723,12] = 5209
		v[724,12] = 1195
		v[725,12] = 1077
		v[726,12] = 1309
		v[727,12] = 2953
		v[728,12] = 7343
		v[729,12] = 4887
		v[730,12] = 3229
		v[731,12] = 6759
		v[732,12] = 6721
		v[733,12] = 6775
		v[734,12] = 675
		v[735,12] = 4039
		v[736,12] = 2493
		v[737,12] = 7511
		v[738,12] = 3269
		v[739,12] = 4199
		v[740,12] = 6625
		v[741,12] = 7943
		v[742,12] = 2013
		v[743,12] = 4145
		v[744,12] = 667
		v[745,12] = 513
		v[746,12] = 2303
		v[747,12] = 4591
		v[748,12] = 7941
		v[749,12] = 2741
		v[750,12] = 987
		v[751,12] = 8061
		v[752,12] = 3161
		v[753,12] = 5951
		v[754,12] = 1431
		v[755,12] = 831
		v[756,12] = 5559
		v[757,12] = 7405
		v[758,12] = 1357
		v[759,12] = 4319
		v[760,12] = 4235
		v[761,12] = 5421
		v[762,12] = 2559
		v[763,12] = 4415
		v[764,12] = 2439
		v[765,12] = 823
		v[766,12] = 1725
		v[767,12] = 6219
		v[768,12] = 4903
		v[769,12] = 6699
		v[770,12] = 5451
		v[771,12] = 349
		v[772,12] = 7703
		v[773,12] = 2927
		v[774,12] = 7809
		v[775,12] = 6179
		v[776,12] = 1417
		v[777,12] = 5987
		v[778,12] = 3017
		v[779,12] = 4983
		v[780,12] = 3479
		v[781,12] = 4525
		v[782,12] = 4643
		v[783,12] = 4911
		v[784,12] = 227
		v[785,12] = 5475
		v[786,12] = 2287
		v[787,12] = 5581
		v[788,12] = 6817
		v[789,12] = 1937
		v[790,12] = 1421
		v[791,12] = 4415
		v[792,12] = 7977
		v[793,12] = 1789
		v[794,12] = 3907
		v[795,12] = 6815
		v[796,12] = 6789
		v[797,12] = 6003
		v[798,12] = 5609
		v[799,12] = 4507
		v[800,12] = 337
		v[801,12] = 7427
		v[802,12] = 7943
		v[803,12] = 3075
		v[804,12] = 6427
		v[805,12] = 1019
		v[806,12] = 7121
		v[807,12] = 4763
		v[808,12] = 81
		v[809,12] = 3587
		v[810,12] = 2929
		v[811,12] = 1795
		v[812,12] = 8067
		v[813,12] = 2415
		v[814,12] = 1265
		v[815,12] = 4025
		v[816,12] = 5599
		v[817,12] = 4771
		v[818,12] = 3025
		v[819,12] = 2313
		v[820,12] = 6129
		v[821,12] = 7611
		v[822,12] = 6881
		v[823,12] = 5253
		v[824,12] = 4413
		v[825,12] = 7869
		v[826,12] = 105
		v[827,12] = 3173
		v[828,12] = 1629
		v[829,12] = 2537
		v[830,12] = 1023
		v[831,12] = 4409
		v[832,12] = 7209
		v[833,12] = 4413
		v[834,12] = 7107
		v[835,12] = 7469
		v[836,12] = 33
		v[837,12] = 1955
		v[838,12] = 2881
		v[839,12] = 5167
		v[840,12] = 6451
		v[841,12] = 4211
		v[842,12] = 179
		v[843,12] = 5573
		v[844,12] = 7879
		v[845,12] = 3387
		v[846,12] = 7759
		v[847,12] = 5455
		v[848,12] = 7157
		v[849,12] = 1891
		v[850,12] = 5683
		v[851,12] = 5689
		v[852,12] = 6535
		v[853,12] = 3109
		v[854,12] = 6555
		v[855,12] = 6873
		v[856,12] = 1249
		v[857,12] = 4251
		v[858,12] = 6437
		v[859,12] = 49
		v[860,12] = 2745
		v[861,12] = 1201
		v[862,12] = 7327
		v[863,12] = 4179
		v[864,12] = 6783
		v[865,12] = 623
		v[866,12] = 2779
		v[867,12] = 5963
		v[868,12] = 2585
		v[869,12] = 6927
		v[870,12] = 5333
		v[871,12] = 4033
		v[872,12] = 285
		v[873,12] = 7467
		v[874,12] = 4443
		v[875,12] = 4917
		v[876,12] = 3
		v[877,12] = 4319
		v[878,12] = 5517
		v[879,12] = 3449
		v[880,12] = 813
		v[881,12] = 5499
		v[882,12] = 2515
		v[883,12] = 5771
		v[884,12] = 3357
		v[885,12] = 2073
		v[886,12] = 4395
		v[887,12] = 4925
		v[888,12] = 2643
		v[889,12] = 7215
		v[890,12] = 5817
		v[891,12] = 1199
		v[892,12] = 1597
		v[893,12] = 1619
		v[894,12] = 7535
		v[895,12] = 4833
		v[896,12] = 609
		v[897,12] = 4797
		v[898,12] = 8171
		v[899,12] = 6847
		v[900,12] = 793
		v[901,12] = 6757
		v[902,12] = 8165
		v[903,12] = 3371
		v[904,12] = 2431
		v[905,12] = 5235
		v[906,12] = 4739
		v[907,12] = 7703
		v[908,12] = 7223
		v[909,12] = 6525
		v[910,12] = 5891
		v[911,12] = 5605
		v[912,12] = 4433
		v[913,12] = 3533
		v[914,12] = 5267
		v[915,12] = 5125
		v[916,12] = 5037
		v[917,12] = 225
		v[918,12] = 6717
		v[919,12] = 1121
		v[920,12] = 5741
		v[921,12] = 2013
		v[922,12] = 4327
		v[923,12] = 4839
		v[924,12] = 569
		v[925,12] = 5227
		v[926,12] = 7677
		v[927,12] = 4315
		v[928,12] = 2391
		v[929,12] = 5551
		v[930,12] = 859
		v[931,12] = 3627
		v[932,12] = 6377
		v[933,12] = 3903
		v[934,12] = 4311
		v[935,12] = 6527
		v[936,12] = 7573
		v[937,12] = 4905
		v[938,12] = 7731
		v[939,12] = 1909
		v[940,12] = 1555
		v[941,12] = 3279
		v[942,12] = 1949
		v[943,12] = 1887
		v[944,12] = 6675
		v[945,12] = 5509
		v[946,12] = 2033
		v[947,12] = 5473
		v[948,12] = 3539
		v[949,12] = 5033
		v[950,12] = 5935
		v[951,12] = 6095
		v[952,12] = 4761
		v[953,12] = 1771
		v[954,12] = 1271
		v[955,12] = 1717
		v[956,12] = 4415
		v[957,12] = 5083
		v[958,12] = 6277
		v[959,12] = 3147
		v[960,12] = 7695
		v[961,12] = 2461
		v[962,12] = 4783
		v[963,12] = 4539
		v[964,12] = 5833
		v[965,12] = 5583
		v[966,12] = 651
		v[967,12] = 1419
		v[968,12] = 2605
		v[969,12] = 5511
		v[970,12] = 3913
		v[971,12] = 5795
		v[972,12] = 2333
		v[973,12] = 2329
		v[974,12] = 4431
		v[975,12] = 3725
		v[976,12] = 6069
		v[977,12] = 2699
		v[978,12] = 7055
		v[979,12] = 6879
		v[980,12] = 1017
		v[981,12] = 3121
		v[982,12] = 2547
		v[983,12] = 4603
		v[984,12] = 2385
		v[985,12] = 6915
		v[986,12] = 6103
		v[987,12] = 5669
		v[988,12] = 7833
		v[989,12] = 2001
		v[990,12] = 4287
		v[991,12] = 6619
		v[992,12] = 955
		v[993,12] = 2761
		v[994,12] = 5711
		v[995,12] = 6291
		v[996,12] = 3415
		v[997,12] = 3909
		v[998,12] = 2841
		v[999,12] = 5627
		v[1000,12] = 4939
		v[1001,12] = 7671
		v[1002,12] = 6059
		v[1003,12] = 6275
		v[1004,12] = 6517
		v[1005,12] = 1931
		v[1006,12] = 4583
		v[1007,12] = 7301
		v[1008,12] = 1267
		v[1009,12] = 7509
		v[1010,12] = 1435
		v[1011,12] = 2169
		v[1012,12] = 6939
		v[1013,12] = 3515
		v[1014,12] = 2985
		v[1015,12] = 2787
		v[1016,12] = 2123
		v[1017,12] = 1969
		v[1018,12] = 3307
		v[1019,12] = 353
		v[1020,12] = 4359
		v[1021,12] = 7059
		v[1022,12] = 5273
		v[1023,12] = 5873
		v[1024,12] = 6657
		v[1025,12] = 6765
		v[1026,12] = 6229
		v[1027,12] = 3179
		v[1028,12] = 1583
		v[1029,12] = 6237
		v[1030,12] = 2155
		v[1031,12] = 371
		v[1032,12] = 273
		v[1033,12] = 7491
		v[1034,12] = 3309
		v[1035,12] = 6805
		v[1036,12] = 3015
		v[1037,12] = 6831
		v[1038,12] = 7819
		v[1039,12] = 713
		v[1040,12] = 4747
		v[1041,12] = 3935
		v[1042,12] = 4109
		v[1043,12] = 1311
		v[1044,12] = 709
		v[1045,12] = 3089
		v[1046,12] = 7059
		v[1047,12] = 4247
		v[1048,12] = 2989
		v[1049,12] = 1509
		v[1050,12] = 4919
		v[1051,12] = 1841
		v[1052,12] = 3045
		v[1053,12] = 3821
		v[1054,12] = 6929
		v[1055,12] = 4655
		v[1056,12] = 1333
		v[1057,12] = 6429
		v[1058,12] = 6649
		v[1059,12] = 2131
		v[1060,12] = 5265
		v[1061,12] = 1051
		v[1062,12] = 261
		v[1063,12] = 8057
		v[1064,12] = 3379
		v[1065,12] = 2179
		v[1066,12] = 1993
		v[1067,12] = 5655
		v[1068,12] = 3063
		v[1069,12] = 6381
		v[1070,12] = 3587
		v[1071,12] = 7417
		v[1072,12] = 1579
		v[1073,12] = 1541
		v[1074,12] = 2107
		v[1075,12] = 5085
		v[1076,12] = 2873
		v[1077,12] = 6141
		v[1078,12] = 955
		v[1079,12] = 3537
		v[1080,12] = 2157
		v[1081,12] = 841
		v[1082,12] = 1999
		v[1083,12] = 1465
		v[1084,12] = 5171
		v[1085,12] = 5651
		v[1086,12] = 1535
		v[1087,12] = 7235
		v[1088,12] = 4349
		v[1089,12] = 1263
		v[1090,12] = 1453
		v[1091,12] = 1005
		v[1092,12] = 6893
		v[1093,12] = 2919
		v[1094,12] = 1947
		v[1095,12] = 1635
		v[1096,12] = 3963
		v[1097,12] = 397
		v[1098,12] = 969
		v[1099,12] = 4569
		v[1100,12] = 655
		v[1101,12] = 6737
		v[1102,12] = 2995
		v[1103,12] = 7235
		v[1104,12] = 7713
		v[1105,12] = 973
		v[1106,12] = 4821
		v[1107,12] = 2377
		v[1108,12] = 1673
		v[1109,12] = 1
		v[1110,12] = 6541

# 		v[0:40,0] = transpose([ \
# 			1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
# 			1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
# 			1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
# 			1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ])

# 		v[2:40,1] = transpose([ \
# 			1, 3, 1, 3, 1, 3, 3, 1, \
# 			3, 1, 3, 1, 3, 1, 1, 3, 1, 3, \
# 			1, 3, 1, 3, 3, 1, 3, 1, 3, 1, \
# 			3, 1, 1, 3, 1, 3, 1, 3, 1, 3 ])

# 		v[3:40,2] = transpose([ \
# 			7, 5, 1, 3, 3, 7, 5, \
# 			5, 7, 7, 1, 3, 3, 7, 5, 1, 1, \
# 			5, 3, 3, 1, 7, 5, 1, 3, 3, 7, \
# 			5, 1, 1, 5, 7, 7, 5, 1, 3, 3 ])

# 		v[5:40,3] = transpose([ \
# 			1, 7, 9,13,11, \
# 			1, 3, 7, 9, 5,13,13,11, 3,15, \
# 			5, 3,15, 7, 9,13, 9, 1,11, 7, \
# 			5,15, 1,15,11, 5, 3, 1, 7, 9 ])
	
# 		v[7:40,4] = transpose([ \
# 			9, 3,27, \
# 			15,29,21,23,19,11,25, 7,13,17, \
# 			1,25,29, 3,31,11, 5,23,27,19, \
# 			21, 5, 1,17,13, 7,15, 9,31, 9 ])

# 		v[13:40,5] = transpose([ \
# 							37,33, 7, 5,11,39,63, \
# 		 27,17,15,23,29, 3,21,13,31,25, \
# 			9,49,33,19,29,11,19,27,15,25 ])

# 		v[19:40,6] = transpose([ \
# 			13, \
# 			33,115, 41, 79, 17, 29,119, 75, 73,105, \
# 			7, 59, 65, 21,	3,113, 61, 89, 45,107 ])

# 		v[37:40,7] = transpose([ \
# 			7, 23, 39 ])
#
#	Set POLY.
#
		poly= [ \
			1,	 3,	 7,	11,	13,	19,	25,	37,	59,	47, \
			61,	55,	41,	67,	97,	91, 109, 103, 115, 131, \
			193, 137, 145, 143, 241, 157, 185, 167, 229, 171, \
			213, 191, 253, 203, 211, 239, 247, 285, 369, 299 ]

		poly = [\
			1,    3,    7,   11,   13,   19,   25,   37,   59,   47,
			61,   55,   41,   67,   97,   91,  109,  103,  115,  131,
			193,  137,  145,  143,  241,  157,  185,  167,  229,  171,
			213,  191,  253,  203,  211,  239,  247,  285,  369,  299,
			301,  333,  351,  355,  357,  361,  391,  397,  425,  451,
			463,  487,  501,  529,  539,  545,  557,  563,  601,  607,
			617,  623,  631,  637,  647,  661,  675,  677,  687,  695, 
			701,  719,  721,  731,  757,  761,  787,  789,  799,  803,
			817,  827,  847,  859,  865,  875,  877,  883,  895,  901,
			911,  949,  953,  967,  971,  973,  981,  985,  995, 1001,
			1019, 1033, 1051, 1063, 1069, 1125, 1135, 1153, 1163, 1221,
			1239, 1255, 1267, 1279, 1293, 1305, 1315, 1329, 1341, 1347,
			1367, 1387, 1413, 1423, 1431, 1441, 1479, 1509, 1527, 1531,
			1555, 1557, 1573, 1591, 1603, 1615, 1627, 1657, 1663, 1673, 
			1717, 1729, 1747, 1759, 1789, 1815, 1821, 1825, 1849, 1863,
			1869, 1877, 1881, 1891, 1917, 1933, 1939, 1969, 2011, 2035,
			2041, 2053, 2071, 2091, 2093, 2119, 2147, 2149, 2161, 2171,
			2189, 2197, 2207, 2217, 2225, 2255, 2257, 2273, 2279, 2283,
			2293, 2317, 2323, 2341, 2345, 2363, 2365, 2373, 2377, 2385,
			2395, 2419, 2421, 2431, 2435, 2447, 2475, 2477, 2489, 2503, 
			2521, 2533, 2551, 2561, 2567, 2579, 2581, 2601, 2633, 2657,
			2669, 2681, 2687, 2693, 2705, 2717, 2727, 2731, 2739, 2741,
			2773, 2783, 2793, 2799, 2801, 2811, 2819, 2825, 2833, 2867,
			2879, 2881, 2891, 2905, 2911, 2917, 2927, 2941, 2951, 2955,
			2963, 2965, 2991, 2999, 3005, 3017, 3035, 3037, 3047, 3053,
			3083, 3085, 3097, 3103, 3159, 3169, 3179, 3187, 3205, 3209,
			3223, 3227, 3229, 3251, 3263, 3271, 3277, 3283, 3285, 3299,
			3305, 3319, 3331, 3343, 3357, 3367, 3373, 3393, 3399, 3413,
			3417, 3427, 3439, 3441, 3475, 3487, 3497, 3515, 3517, 3529,
			3543, 3547, 3553, 3559, 3573, 3589, 3613, 3617, 3623, 3627,
			3635, 3641, 3655, 3659, 3669, 3679, 3697, 3707, 3709, 3713,
			3731, 3743, 3747, 3771, 3791, 3805, 3827, 3833, 3851, 3865,
			3889, 3895, 3933, 3947, 3949, 3957, 3971, 3985, 3991, 3995,
			4007, 4013, 4021, 4045, 4051, 4069, 4073, 4179, 4201, 4219,
			4221, 4249, 4305, 4331, 4359, 4383, 4387, 4411, 4431, 4439,
			4449, 4459, 4485, 4531, 4569, 4575, 4621, 4663, 4669, 4711,
			4723, 4735, 4793, 4801, 4811, 4879, 4893, 4897, 4921, 4927,
			4941, 4977, 5017, 5027, 5033, 5127, 5169, 5175, 5199, 5213,
			5223, 5237, 5287, 5293, 5331, 5391, 5405, 5453, 5523, 5573,
			5591, 5597, 5611, 5641, 5703, 5717, 5721, 5797, 5821, 5909,
			5913, 5955, 5957, 6005, 6025, 6061, 6067, 6079, 6081, 6231,
			6237, 6289, 6295, 6329, 6383, 6427, 6453, 6465, 6501, 6523,
			6539, 6577, 6589, 6601, 6607, 6631, 6683, 6699, 6707, 6761,
			6795, 6865, 6881, 6901, 6923, 6931, 6943, 6999, 7057, 7079,
			7103, 7105, 7123, 7173, 7185, 7191, 7207, 7245, 7303, 7327, 
			7333, 7355, 7365, 7369, 7375, 7411, 7431, 7459, 7491, 7505, 
			7515, 7541, 7557, 7561, 7701, 7705, 7727, 7749, 7761, 7783,
			7795, 7823, 7907, 7953, 7963, 7975, 8049, 8089, 8123, 8125,
			8137, 8219, 8231, 8245, 8275, 8293, 8303, 8331, 8333, 8351,
			8357, 8367, 8379, 8381, 8387, 8393, 8417, 8435, 8461, 8469,
			8489, 8495, 8507, 8515, 8551, 8555, 8569, 8585, 8599, 8605,
			8639, 8641, 8647, 8653, 8671, 8675, 8689, 8699, 8729, 8741,
			8759, 8765, 8771, 8795, 8797, 8825, 8831, 8841, 8855, 8859,
			8883, 8895, 8909, 8943, 8951, 8955, 8965, 8999, 9003, 9031,
			9045, 9049, 9071, 9073, 9085, 9095, 9101, 9109, 9123, 9129,
			9137, 9143, 9147, 9185, 9197, 9209, 9227, 9235, 9247, 9253,
			9257, 9277, 9297, 9303, 9313, 9325, 9343, 9347, 9371, 9373,
			9397, 9407, 9409, 9415, 9419, 9443, 9481, 9495, 9501, 9505,
			9517, 9529, 9555, 9557, 9571, 9585, 9591, 9607, 9611, 9621,
			9625, 9631, 9647, 9661, 9669, 9679, 9687, 9707, 9731, 9733,
			9745, 9773, 9791, 9803, 9811, 9817, 9833, 9847, 9851, 9863,
			9875, 9881, 9905, 9911, 9917, 9923, 9963, 9973,10003,10025,
			10043,10063,10071,10077,10091,10099,10105,10115,10129,10145,
			10169,10183,10187,10207,10223,10225,10247,10265,10271,10275,
			10289,10299,10301,10309,10343,10357,10373,10411,10413,10431,
			10445,10453,10463,10467,10473,10491,10505,10511,10513,10523,
			10539,10549,10559,10561,10571,10581,10615,10621,10625,10643,
			10655,10671,10679,10685,10691,10711,10739,10741,10755,10767,
			10781,10785,10803,10805,10829,10857,10863,10865,10875,10877,
			10917,10921,10929,10949,10967,10971,10987,10995,11009,11029,
			11043,11045,11055,11063,11075,11081,11117,11135,11141,11159,
			11163,11181,11187,11225,11237,11261,11279,11297,11307,11309,
			11327,11329,11341,11377,11403,11405,11413,11427,11439,11453,
			11461,11473,11479,11489,11495,11499,11533,11545,11561,11567,
			11575,11579,11589,11611,11623,11637,11657,11663,11687,11691,
			11701,11747,11761,11773,11783,11795,11797,11817,11849,11855,
			11867,11869,11873,11883,11919,11921,11927,11933,11947,11955,
			11961,11999,12027,12029,12037,12041,12049,12055,12095,12097,
			12107,12109,12121,12127,12133,12137,12181,12197,12207,12209,
			12239,12253,12263,12269,12277,12287,12295,12309,12313,12335,
			12361,12367,12391,12409,12415,12433,12449,12469,12479,12481,
			12499,12505,12517,12527,12549,12559,12597,12615,12621,12639,
			12643,12657,12667,12707,12713,12727,12741,12745,12763,12769,
			12779,12781,12787,12799,12809,12815,12829,12839,12857,12875,
			12883,12889,12901,12929,12947,12953,12959,12969,12983,12987,
			12995,13015,13019,13031,13063,13077,13103,13137,13149,13173,
			13207,13211,13227,13241,13249,13255,13269,13283,13285,13303,
			13307,13321,13339,13351,13377,13389,13407,13417,13431,13435,
			13447,13459,13465,13477,13501,13513,13531,13543,13561,13581,
			13599,13605,13617,13623,13637,13647,13661,13677,13683,13695,
			13725,13729,13753,13773,13781,13785,13795,13801,13807,13825,
			13835,13855,13861,13871,13883,13897,13905,13915,13939,13941,
			13969,13979,13981,13997,14027,14035,14037,14051,14063,14085,
			14095,14107,14113,14125,14137,14145,14151,14163,14193,14199,
			14219,14229,14233,14243,14277,14287,14289,14295,14301,14305,
			14323,14339,14341,14359,14365,14375,14387,14411,14425,14441,
			14449,14499,14513,14523,14537,14543,14561,14579,14585,14593,
			14599,14603,14611,14641,14671,14695,14701,14723,14725,14743,
			14753,14759,14765,14795,14797,14803,14831,14839,14845,14855,
			14889,14895,14909,14929,14941,14945,14951,14963,14965,14985,
			15033,15039,15053,15059,15061,15071,15077,15081,15099,15121,
			15147,15149,15157,15167,15187,15193,15203,15205,15215,15217,
			15223,15243,15257,15269,15273,15287,15291,15313,15335,15347,
			15359,15373,15379,15381,15391,15395,15397,15419,15439,15453,
			15469,15491,15503,15517,15527,15531,15545,15559,15593,15611,
			15613,15619,15639,15643,15649,15661,15667,15669,15681,15693,
			15717,15721,15741,15745,15765,15793,15799,15811,15825,15835,
			15847,15851,15865,15877,15881,15887,15899,15915,15935,15937,
			15955,15973,15977,16011,16035,16061,16069,16087,16093,16097,
			16121,16141,16153,16159,16165,16183,16189,16195,16197,16201,
			16209,16215,16225,16259,16265,16273,16299,16309,16355,16375,
			16381]
		atmost = 2**log_max - 1
#
#	Find the number of bits in ATMOST.
#
		maxcol = i4_bit_hi1 ( atmost )
#
#	Initialize row 1 of V.
#
		v[0,0:maxcol] = 1

#
#	Things to do only if the dimension changed.
#
	if ( dim_num != dim_num_save ):
#
#	Check parameters.
#
		if ( dim_num < 1 or dim_max < dim_num ):
			print 'I4_SOBOL - Fatal error!' 
			print '	The spatial dimension DIM_NUM should satisfy:' 
			print '		1 <= DIM_NUM <= %d'%dim_max
			print '	But this input value is DIM_NUM = %d'%dim_num
			return

		dim_num_save = dim_num
#
#	Initialize the remaining rows of V.
#
		for i in xrange(2 , dim_num+1):
#
#	The bits of the integer POLY(I) gives the form of polynomial I.
#
#	Find the degree of polynomial I from binary encoding.
#
			j = poly[i-1]
			m = 0
			while ( 1 ):
				j = math.floor ( j / 2. )
				if ( j <= 0 ):
					break
				m = m + 1
#
#	Expand this bit pattern to separate components of the logical array INCLUD.
#
			j = poly[i-1]
			includ=zeros(m)
			for k in xrange(m, 0, -1):
				j2 = math.floor ( j / 2. )
				includ[k-1] =  (j != 2 * j2 )
				j = j2
#
#	Calculate the remaining elements of row I as explained
#	in Bratley and Fox, section 2.
#
			for j in xrange( m+1, maxcol+1 ):
				newv = v[i-1,j-m-1]
				l = 1
				for k in xrange(1, m+1):
					l = 2 * l
					if ( includ[k-1] ):
						newv = bitwise_xor ( int(newv), int(l * v[i-1,j-k-1]) )
				v[i-1,j-1] = newv
#
#	Multiply columns of V by appropriate power of 2.
#
		l = 1
		for j in xrange( maxcol-1, 0, -1):
			l = 2 * l
			v[0:dim_num,j-1] = v[0:dim_num,j-1] * l
#
#	RECIPD is 1/(common denominator of the elements in V).
#
		recipd = 1.0 / ( 2 * l )
		lastq=zeros(dim_num)

	seed = int(math.floor ( seed ))

	if ( seed < 0 ):
		seed = 0

	if ( seed == 0 ):
		l = 1
		lastq=zeros(dim_num)

	elif ( seed == seed_save + 1 ):
#
#	Find the position of the right-hand zero in SEED.
#
		l = i4_bit_lo0 ( seed )

	elif ( seed <= seed_save ):

		seed_save = 0
		l = 1
		lastq=zeros(dim_num)

		for seed_temp in xrange( int(seed_save), int(seed)):
			l = i4_bit_lo0 ( seed_temp )
			for i in xrange(1 , dim_num+1):
				lastq[i-1] = bitwise_xor ( int(lastq[i-1]), int(v[i-1,l-1]) )

		l = i4_bit_lo0 ( seed )

	elif ( seed_save + 1 < seed ):

		for seed_temp in xrange( int(seed_save + 1), int(seed) ):
			l = i4_bit_lo0 ( seed_temp )
			for i in xrange(1, dim_num+1):
				lastq[i-1] = bitwise_xor ( int(lastq[i-1]), int(v[i-1,l-1]) )

		l = i4_bit_lo0 ( seed )
#
#	Check that the user is not calling too many times!
#
	if ( maxcol < l ):
		print 'I4_SOBOL - Fatal error!'
		print '	Too many calls!'
		print '	MAXCOL = %d\n'%maxcol
		print '	L =			%d\n'%l
		return
#
#	Calculate the new components of QUASI.
#
	quasi=zeros(dim_num)
	for i in xrange( 1, dim_num+1):
		quasi[i-1] = lastq[i-1] * recipd
		lastq[i-1] = bitwise_xor ( int(lastq[i-1]), int(v[i-1,l-1]) )

	seed_save = seed
	seed = seed + 1

	return [ quasi, seed ]
def i4_uniform ( a, b, seed ):
#*****************************************************************************80
#
## I4_UNIFORM returns a scaled pseudorandom I4.
#
#	Discussion:
#
#		The pseudorandom number will be scaled to be uniformly distributed
#		between A and B.
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#	Reference:
#
#		Paul Bratley, Bennett Fox, Linus Schrage,
#		A Guide to Simulation,
#		Springer Verlag, pages 201-202, 1983.
#
#		Pierre L'Ecuyer,
#		Random Number Generation,
#		in Handbook of Simulation,
#		edited by Jerry Banks,
#		Wiley Interscience, page 95, 1998.
#
#		Bennett Fox,
#		Algorithm 647:
#		Implementation and Relative Efficiency of Quasirandom
#		Sequence Generators,
#		ACM Transactions on Mathematical Software,
#		Volume 12, Number 4, pages 362-376, 1986.
#
#		Peter Lewis, Allen Goodman, James Miller
#		A Pseudo-Random Number Generator for the System/360,
#		IBM Systems Journal,
#		Volume 8, pages 136-143, 1969.
#
#	Parameters:
#
#		Input, integer A, B, the minimum and maximum acceptable values.
#
#		Input, integer SEED, a seed for the random number generator.
#
#		Output, integer C, the randomly chosen integer.
#
#		Output, integer SEED, the updated seed.
#
	if ( seed == 0 ):
		print 'I4_UNIFORM - Fatal error!' 
		print '	Input SEED = 0!'

	seed = math.floor ( seed )
	a = round ( a )
	b = round ( b )

	seed = mod ( seed, 2147483647 )

	if ( seed < 0 ) :
		seed = seed + 2147483647

	k = math.floor ( seed / 127773 )

	seed = 16807 * ( seed - k * 127773 ) - k * 2836

	if ( seed < 0 ):
		seed = seed + 2147483647

	r = seed * 4.656612875E-10
#
#	Scale R to lie between A-0.5 and B+0.5.
#
	r = ( 1.0 - r ) * ( min ( a, b ) - 0.5 ) + r * ( max ( a, b ) + 0.5 )
#
#	Use rounding to convert R to an integer between A and B.
#
	value = round ( r )

	value = max ( value, min ( a, b ) )
	value = min ( value, max ( a, b ) )

	c = value

	return [ int(c), int(seed) ]
def prime_ge ( n ):
#*****************************************************************************80
#
## PRIME_GE returns the smallest prime greater than or equal to N.
#
#
#	Example:
#
#		N		 PRIME_GE
#
#		-10		2
#			1		2
#			2		2
#			3		3
#			4		5
#			5		5
#			6		7
#			7		7
#			8	 11
#			9	 11
#		 10	 11
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#	Parameters:
#
#		Input, integer N, the number to be bounded.
#
#		Output, integer P, the smallest prime number that is greater
#		than or equal to N.	
#
	p = max ( math.ceil ( n ), 2 )
	while ( not isprime ( p ) ):
		p = p + 1

	return p

def isprime(n):
	#*****************************************************************************80
#
## IS_PRIME returns True if N is a prime number, False otherwise
#
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Corrado Chisari
#
#	Parameters:
#
#		Input, integer N, the number to be checked.
#
#		Output, boolean value, True or False
#
	if n!=int(n) or n<1:
		return False
	p=2
	while p<n:
		if n%p==0:
			return False
		p+=1
	return True
	

########NEW FILE########
__FILENAME__ = spearmint_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: spearmint.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)




DESCRIPTOR = _descriptor.FileDescriptor(
  name='spearmint.proto',
  package='',
  serialized_pb='\n\x0fspearmint.proto\"\xcc\x01\n\x03Job\x12\n\n\x02id\x18\x01 \x02(\x04\x12\x10\n\x08\x65xpt_dir\x18\x02 \x02(\t\x12\x0c\n\x04name\x18\x03 \x02(\t\x12\x1b\n\x08language\x18\x04 \x02(\x0e\x32\t.Language\x12\x0e\n\x06status\x18\x05 \x01(\t\x12\x19\n\x05param\x18\x06 \x03(\x0b\x32\n.Parameter\x12\x10\n\x08submit_t\x18\x07 \x01(\x04\x12\x0f\n\x07start_t\x18\x08 \x01(\x04\x12\r\n\x05\x65nd_t\x18\t \x01(\x04\x12\r\n\x05value\x18\n \x01(\x01\x12\x10\n\x08\x64uration\x18\x0b \x01(\x01\"L\n\tParameter\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0f\n\x07int_val\x18\x02 \x03(\x03\x12\x0f\n\x07str_val\x18\x03 \x03(\t\x12\x0f\n\x07\x64\x62l_val\x18\x04 \x03(\x01\"\x91\x02\n\nExperiment\x12\x1b\n\x08language\x18\x01 \x02(\x0e\x32\t.Language\x12\x0c\n\x04name\x18\x02 \x02(\t\x12+\n\x08variable\x18\x03 \x03(\x0b\x32\x19.Experiment.ParameterSpec\x1a\xaa\x01\n\rParameterSpec\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0c\n\x04size\x18\x02 \x02(\r\x12,\n\x04type\x18\x03 \x02(\x0e\x32\x1e.Experiment.ParameterSpec.Type\x12\x0f\n\x07options\x18\x04 \x03(\t\x12\x0b\n\x03min\x18\x05 \x01(\x01\x12\x0b\n\x03max\x18\x06 \x01(\x01\"$\n\x04Type\x12\x07\n\x03INT\x10\x01\x12\t\n\x05\x46LOAT\x10\x02\x12\x08\n\x04\x45NUM\x10\x03*A\n\x08Language\x12\n\n\x06MATLAB\x10\x01\x12\n\n\x06PYTHON\x10\x02\x12\t\n\x05SHELL\x10\x03\x12\x07\n\x03MCR\x10\x04\x12\t\n\x05TORCH\x10\x05')

_LANGUAGE = _descriptor.EnumDescriptor(
  name='Language',
  full_name='Language',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='MATLAB', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='PYTHON', index=1, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SHELL', index=2, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MCR', index=3, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TORCH', index=4, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=580,
  serialized_end=645,
)

Language = enum_type_wrapper.EnumTypeWrapper(_LANGUAGE)
MATLAB = 1
PYTHON = 2
SHELL = 3
MCR = 4
TORCH = 5


_EXPERIMENT_PARAMETERSPEC_TYPE = _descriptor.EnumDescriptor(
  name='Type',
  full_name='Experiment.ParameterSpec.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='INT', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FLOAT', index=1, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ENUM', index=2, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=542,
  serialized_end=578,
)


_JOB = _descriptor.Descriptor(
  name='Job',
  full_name='Job',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='Job.id', index=0,
      number=1, type=4, cpp_type=4, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='expt_dir', full_name='Job.expt_dir', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='Job.name', index=2,
      number=3, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='language', full_name='Job.language', index=3,
      number=4, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='status', full_name='Job.status', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='param', full_name='Job.param', index=5,
      number=6, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='submit_t', full_name='Job.submit_t', index=6,
      number=7, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='start_t', full_name='Job.start_t', index=7,
      number=8, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='end_t', full_name='Job.end_t', index=8,
      number=9, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='Job.value', index=9,
      number=10, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='Job.duration', index=10,
      number=11, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=20,
  serialized_end=224,
)


_PARAMETER = _descriptor.Descriptor(
  name='Parameter',
  full_name='Parameter',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='Parameter.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='int_val', full_name='Parameter.int_val', index=1,
      number=2, type=3, cpp_type=2, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='str_val', full_name='Parameter.str_val', index=2,
      number=3, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='dbl_val', full_name='Parameter.dbl_val', index=3,
      number=4, type=1, cpp_type=5, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=226,
  serialized_end=302,
)


_EXPERIMENT_PARAMETERSPEC = _descriptor.Descriptor(
  name='ParameterSpec',
  full_name='Experiment.ParameterSpec',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='Experiment.ParameterSpec.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='size', full_name='Experiment.ParameterSpec.size', index=1,
      number=2, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='type', full_name='Experiment.ParameterSpec.type', index=2,
      number=3, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='options', full_name='Experiment.ParameterSpec.options', index=3,
      number=4, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='min', full_name='Experiment.ParameterSpec.min', index=4,
      number=5, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='max', full_name='Experiment.ParameterSpec.max', index=5,
      number=6, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _EXPERIMENT_PARAMETERSPEC_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=408,
  serialized_end=578,
)

_EXPERIMENT = _descriptor.Descriptor(
  name='Experiment',
  full_name='Experiment',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='language', full_name='Experiment.language', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='Experiment.name', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='variable', full_name='Experiment.variable', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_EXPERIMENT_PARAMETERSPEC, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=305,
  serialized_end=578,
)

_JOB.fields_by_name['language'].enum_type = _LANGUAGE
_JOB.fields_by_name['param'].message_type = _PARAMETER
_EXPERIMENT_PARAMETERSPEC.fields_by_name['type'].enum_type = _EXPERIMENT_PARAMETERSPEC_TYPE
_EXPERIMENT_PARAMETERSPEC.containing_type = _EXPERIMENT;
_EXPERIMENT_PARAMETERSPEC_TYPE.containing_type = _EXPERIMENT_PARAMETERSPEC;
_EXPERIMENT.fields_by_name['language'].enum_type = _LANGUAGE
_EXPERIMENT.fields_by_name['variable'].message_type = _EXPERIMENT_PARAMETERSPEC
DESCRIPTOR.message_types_by_name['Job'] = _JOB
DESCRIPTOR.message_types_by_name['Parameter'] = _PARAMETER
DESCRIPTOR.message_types_by_name['Experiment'] = _EXPERIMENT

class Job(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _JOB

  # @@protoc_insertion_point(class_scope:Job)

class Parameter(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PARAMETER

  # @@protoc_insertion_point(class_scope:Parameter)

class Experiment(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class ParameterSpec(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _EXPERIMENT_PARAMETERSPEC

    # @@protoc_insertion_point(class_scope:Experiment.ParameterSpec)
  DESCRIPTOR = _EXPERIMENT

  # @@protoc_insertion_point(class_scope:Experiment)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = util
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
# 
# This code is written for research and educational purposes only to 
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re
import numpy        as np
import numpy.random as npr

def unpack_args(str):
    if len(str) > 1:
        eq_re = re.compile("\s*=\s*")
        return dict(map(lambda x: eq_re.split(x),
                        re.compile("\s*,\s*").split(str)))
    else:
        return {}

def slice_sample(init_x, logprob, sigma=1.0, step_out=True, max_steps_out=1000, 
                 compwise=False, verbose=False):
    def direction_slice(direction, init_x):
        def dir_logprob(z):
            return logprob(direction*z + init_x)
    
        upper = sigma*npr.rand()
        lower = upper - sigma
        llh_s = np.log(npr.rand()) + dir_logprob(0.0)
    
        l_steps_out = 0
        u_steps_out = 0
        if step_out:
            while dir_logprob(lower) > llh_s and l_steps_out < max_steps_out:
                l_steps_out += 1
                lower       -= sigma
            while dir_logprob(upper) > llh_s and u_steps_out < max_steps_out:
                u_steps_out += 1
                upper       += sigma
            
        steps_in = 0
        while True:
            steps_in += 1
            new_z     = (upper - lower)*npr.rand() + lower
            new_llh   = dir_logprob(new_z)
            if np.isnan(new_llh):
                print new_z, direction*new_z + init_x, new_llh, llh_s, init_x, logprob(init_x)
                raise Exception("Slice sampler got a NaN")
            if new_llh > llh_s:
                break
            elif new_z < 0:
                lower = new_z
            elif new_z > 0:
                upper = new_z
            else:
                raise Exception("Slice sampler shrank to zero!")

        if verbose:
            print "Steps Out:", l_steps_out, u_steps_out, " Steps In:", steps_in

        return new_z*direction + init_x
    
    if not init_x.shape:
        init_x = np.array([init_x])

    dims = init_x.shape[0]
    if compwise:
        ordering = range(dims)
        npr.shuffle(ordering)
        cur_x = init_x.copy()
        for d in ordering:
            direction    = np.zeros((dims))
            direction[d] = 1.0
            cur_x = direction_slice(direction, cur_x)
        return cur_x
            
    else:
        direction = npr.randn(dims)
        direction = direction / np.sqrt(np.sum(direction**2))
        return direction_slice(direction, init_x)

########NEW FILE########
__FILENAME__ = app
import os
import sys
import json
import numpy as np
import importlib
from flask import Flask, render_template, redirect, url_for, Markup

from spearmint.ExperimentGrid import ExperimentGrid
from spearmint.helpers import load_experiment
from spearmint.spearmint_pb2 import _LANGUAGE, _EXPERIMENT_PARAMETERSPEC_TYPE

class SpearmintWebApp(Flask):
    def set_experiment_config(self, expt_config):
        self.experiment_config = expt_config
        self.experiment_dir = os.path.dirname(os.path.realpath(expt_config))

    def set_chooser(self, chooser_module, chooser):
        module  = importlib.import_module('chooser.' + chooser_module)
        self.chooser = chooser

    def experiment_grid(self):
        return ExperimentGrid(self.experiment_dir)

    def experiment(self):
        return load_experiment(self.experiment_config)

    def experiment_results(self, grid):
        completed             = grid.get_complete()
        grid_data, vals, durs = grid.get_grid()
        worst_to_best         = sorted(completed, key=lambda i: vals[i], reverse=True)
        return worst_to_best, [vals[i] for i in worst_to_best]


app = SpearmintWebApp(__name__)

# Web App Routes

@app.route("/status")
def status():
    grid = None
    try:
        grid = app.experiment_grid()
        job_ids, scores = app.experiment_results(grid)
        (best_val, best_job) = grid.get_best()
        best_params = list()
        for p in grid.get_params(best_job):
            best_params.append('<br />' + p.name + ':')
            if p.int_val:
                best_params[-1] += np.array_str(np.array(p.int_val))
            if p.dbl_val:
                best_params[-1] += np.array_str(np.array(p.dbl_val))
            if p.str_val:
                best_params[-1] += np.array_str(np.array(p.str_val))
        dims = len(best_params)
        best_params = Markup(','.join(best_params).encode('ascii'))

        # Pump out all experiments (parameter sets) run so far
        all_params = list()
        for job,score in zip(job_ids, scores):
            all_params.append('<tr><td>' + str(job) + '</td>' +
                              '<td>' + str(score) + '</td><td>')
            sub_params = list()
            for p in grid.get_params(job):
                sub_params.append(p.name + ':')
                if p.int_val:
                    sub_params[-1] += np.array_str(np.array(p.int_val))
                if p.dbl_val:
                    sub_params[-1] += np.array_str(np.array(p.dbl_val))
                if p.str_val:
                    sub_params[-1] += np.array_str(np.array(p.str_val))
            all_params.append(',<br />'.join(sub_params).encode('ascii') +
                              '</td></tr>')
        all_params = Markup(' '.join(all_params))

        # If the chooser has a function generate_stats_html, then this
        # will be fed into the web display (as raw html).  This is handy
        # for visualizing things pertaining to the actual underlying statistic
        # model - e.g. for sensitivity analysis.
        try:
            chooseroutput = Markup(app.chooser.generate_stats_html())
        except:
            chooseroutput = ''
        stats  = {
            'candidates'    : grid.get_candidates().size,
            'pending'       : grid.get_pending().size,
            'completed'     : grid.get_complete().size,
            'broken'        : grid.get_broken().size,
            'scores'        : json.dumps(scores),
            'best'          : best_val,
            'bestparams'    : best_params,
            'chooseroutput' : chooseroutput,
            'allresults'    : all_params,
        }
        return render_template('status.html', stats=stats)
    finally:
        # Make sure we unlock the grid so as not to hold up the experiment
        if grid:
            del grid

@app.route("/")
def home():
    exp = app.experiment()
    params = []
    for p in exp.variable:
        param = {
            'name': p.name,
            'min': p.min,
            'max': p.max,
            'type': _EXPERIMENT_PARAMETERSPEC_TYPE.values_by_number[p.type].name,
            'size': p.size
            }
        params.append(param)

    ex = {
        'name': exp.name,
        'language': _LANGUAGE.values_by_number[exp.language].name,
        'params': params,
        }
    return render_template('home.html', experiment=ex)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "No experiment configuration file passed as argument to web app!"
        print "Usage:\n\tpython spearmint/web/app.py path/to/config.pb\n"
        sys.exit(0)

    app.set_experiment_config(sys.argv[1])
    app.run(debug=True)


########NEW FILE########
__FILENAME__ = branin
import numpy as np
import sys
import math
import time

def branin(x):
  x[0] = x[0]*15
  x[1] = (x[1]*15)-5

  y = np.square(x[1] - (5.1/(4*np.square(math.pi)))*np.square(x[0]) + (5/math.pi)*x[0] - 6) + 10*(1-(1./(8*math.pi)))*np.cos(x[0]) + 10;

  result = y;
  #time.sleep(5)

  return result

# Write a function like this called 'main'
def main(job_id, params):
  return branin(params['X'])

########NEW FILE########
__FILENAME__ = braninrunner
import branin
"""
Jasper Snoek
This is a simple script to help demonstrate the functionality of
spearmint-lite.  It will read in results.dat and fill in 'pending'
experiments.
"""
if __name__ == '__main__':
    resfile = open('results.dat','r')
    newlines = []
    for line in resfile.readlines():
        values = line.split()
        if len(values) < 3:
            continue
        val = values.pop(0)
        dur = values.pop(0)
        X = [float(values[0]), float(values[1])]
        print X
        if (val == 'P'):
            val = branin.branin(X)
            newlines.append(str(val) + " 0 " 
                            + str(float(values[0])) + " " 
                            + str(float(values[1])) + "\n")
        else:
            newlines.append(line)

    resfile.close()
    outfile = open('results.dat','w')
    for line in newlines:
        outfile.write(line)

########NEW FILE########
__FILENAME__ = ExperimentGrid
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#                                                                                                                                                                                  
# This code is written for research and educational purposes only to
# supplement the paper entitled "Practical Bayesian Optimization of
# Machine Learning Algorithms" by Snoek, Larochelle and Adams Advances
# in Neural Information Processing Systems, 2012
#                                                                                                                                                                               
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#                                                                                                                                                                             
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#                                                                                                                                                                        
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
import os
import sys
import tempfile
import cPickle

import numpy        as np
import numpy.random as npr

from Locker        import *
from sobol_lib     import *

CANDIDATE_STATE = 0
SUBMITTED_STATE = 1
RUNNING_STATE   = 2
COMPLETE_STATE  = 3
BROKEN_STATE    = -1

class ExperimentGrid:

    @staticmethod
    def job_running(expt_dir, id):
        expt_grid = ExperimentGrid(expt_dir)
        expt_grid.set_running(id)

    @staticmethod
    def job_complete(expt_dir, id, value, duration):
        expt_grid = ExperimentGrid(expt_dir)
        expt_grid.set_complete(id, value, duration)

    @staticmethod
    def job_broken(expt_dir, id):
        expt_grid = ExperimentGrid(expt_dir)
        expt_grid.set_broken(id)

    def __init__(self, expt_dir, variables=None, grid_size=None, grid_seed=1):
        self.expt_dir = expt_dir
        self.jobs_pkl = os.path.join(expt_dir, 'expt-grid.pkl')
        self.locker   = Locker()

        # Only one process at a time is allowed to have access to this.
        sys.stderr.write("Waiting to lock grid...")
        self.locker.lock_wait(self.jobs_pkl)
        sys.stderr.write("...acquired\n")

        # Does this exist already?
        if variables is not None and not os.path.exists(self.jobs_pkl):

            # Set up the grid for the first time.
            self.seed = grid_seed
            self.vmap   = GridMap(variables, grid_size)
            self.grid   = self.hypercube_grid(self.vmap.card(), grid_size)
            self.status = np.zeros(grid_size, dtype=int) + CANDIDATE_STATE
            self.values = np.zeros(grid_size) + np.nan
            self.durs   = np.zeros(grid_size) + np.nan
            self.sgeids = np.zeros(grid_size, dtype=int)

            # Save this out.
            self._save_jobs()
        else:

            # Load in from the pickle.
            self._load_jobs()

    def __del__(self):
        self._save_jobs()
        if self.locker.unlock(self.jobs_pkl):
            sys.stderr.write("Released lock on job grid.\n")
        else:
            raise Exception("Could not release lock on job grid.\n")

    def get_grid(self):
        return self.grid, self.values, self.durs

    def get_candidates(self):
        return np.nonzero(self.status == CANDIDATE_STATE)[0]

    def get_pending(self):
        return np.nonzero((self.status == SUBMITTED_STATE) | (self.status == RUNNING_STATE))[0]

    def get_complete(self):
        return np.nonzero(self.status == COMPLETE_STATE)[0]

    def get_broken(self):
        return np.nonzero(self.status == BROKEN_STATE)[0]

    def get_params(self, index):
        return self.vmap.get_params(self.grid[index,:])

    def get_best(self):
        finite = self.values[np.isfinite(self.values)]
        if len(finite) > 0:
            cur_min = np.min(finite)
            index   = np.nonzero(self.values==cur_min)[0][0]
            return cur_min, index
        else:
            return np.nan, -1

    def get_sgeid(self, id):
        return self.sgeids[id]

    def add_to_grid(self, candidate):
        # Set up the grid
        self.grid   = np.vstack((self.grid, candidate))
        self.status = np.append(self.status, np.zeros(1, dtype=int) + 
                                int(CANDIDATE_STATE))
        
        self.values = np.append(self.values, np.zeros(1)+np.nan)
        self.durs   = np.append(self.durs, np.zeros(1)+np.nan)
        self.sgeids = np.append(self.sgeids, np.zeros(1,dtype=int))

        # Save this out.
        self._save_jobs()
        return self.grid.shape[0]-1

    def set_candidate(self, id):
        self.status[id] = CANDIDATE_STATE
        self._save_jobs()

    def set_submitted(self, id, sgeid):
        self.status[id] = SUBMITTED_STATE
        self.sgeids[id] = sgeid
        self._save_jobs()

    def set_running(self, id):
        self.status[id] = RUNNING_STATE
        self._save_jobs()

    def set_complete(self, id, value, duration):
        self.status[id] = COMPLETE_STATE
        self.values[id] = value
        self.durs[id]   = duration
        self._save_jobs()

    def set_broken(self, id):
        self.status[id] = BROKEN_STATE
        self._save_jobs()

    def _load_jobs(self):
        fh   = open(self.jobs_pkl, 'r')
        jobs = cPickle.load(fh)
        fh.close()

        self.vmap   = jobs['vmap']
        self.grid   = jobs['grid']
        self.status = jobs['status']
        self.values = jobs['values']
        self.durs   = jobs['durs']
        self.sgeids = jobs['sgeids']

    def _save_jobs(self):

        # Write everything to a temporary file first.
        fh = tempfile.NamedTemporaryFile(mode='w', delete=False)
        cPickle.dump({ 'vmap'   : self.vmap,
                       'grid'   : self.grid,
                       'status' : self.status,
                       'values' : self.values,
                       'durs'   : self.durs,
                       'sgeids' : self.sgeids }, fh)
        fh.close()

        # Use an atomic move for better NFS happiness.
        cmd = 'mv "%s" "%s"' % (fh.name, self.jobs_pkl)
        os.system(cmd) # TODO: Should check system-dependent return status.
    
    def _hypercube_grid(self, dims, size):
        # Generate from a sobol sequence
        sobol_grid = np.transpose(i4_sobol_generate(dims,size,self.seed))
                
        return sobol_grid

class Parameter:
    def __init__(self):
        self.type = []
        self.name = []
        self.type = []
        self.min = []
        self.max = []
        self.options = []
        self.int_val = []
        self.dbl_val = []
        self.str_val = []

class GridMap:
    
    def __init__(self, variables, grid_size):
        self.variables   = []
        self.cardinality = 0

        # Count the total number of dimensions and roll into new format.
        for variable in variables:
            self.cardinality += variable['size']

            if variable['type'] == 'int':
                self.variables.append({ 'name' : variable['name'],
                                        'size' : variable['size'],
                                        'type' : 'int',
                                        'min'  : int(variable['min']),
                                        'max'  : int(variable['max'])})

            elif variable['type'] == 'float':
                self.variables.append({ 'name' : variable['name'],
                                        'size' : variable['size'],
                                        'type' : 'float',
                                        'min'  : float(variable['min']),
                                        'max'  : float(variable['max'])})

            elif variable['type'] == 'enum':
                self.variables.append({ 'name'    : variable['name'],
                                        'size'    : variable['size'],
                                        'type'    : 'enum',
                                        'options' : list(variable['options'])})
            else:
                raise Exception("Unknown parameter type.")
        sys.stderr.write("Optimizing over %d dimensions\n" % (self.cardinality))

    # Get a list of candidate experiments generated from a sobol sequence
    def hypercube_grid(self, size, seed):
        # Generate from a sobol sequence
        sobol_grid = np.transpose(i4_sobol_generate(self.cardinality,size,seed))
                
        return sobol_grid

    # Convert a variable to the unit hypercube
    # Takes a single variable encoded as a list, assuming the ordering is 
    # the same as specified in the configuration file
    def to_unit(self, v):
        unit = np.zeros(self.cardinality)
        index  = 0

        for variable in self.variables:
            #param.name = variable['name']
            if variable['type'] == 'int':
                for dd in xrange(variable['size']):
                    unit[index] = self._index_unmap(float(v.pop(0)) - variable['min'], (variable['max']-variable['min'])+1)
                    index += 1

            elif variable['type'] == 'float':
                for dd in xrange(variable['size']):
                    unit[index] = (float(v.pop(0)) - variable['min'])/(variable['max']-variable['min'])
                    index += 1

            elif variable['type'] == 'enum':
                for dd in xrange(variable['size']):
                    unit[index] = variable['options'].index(v.pop(0))
                    index += 1

            else:
                raise Exception("Unknown parameter type.")
            
        if (len(v) > 0):
            raise Exception("Too many variables passed to parser")
        return unit

    def unit_to_list(self, u):
        params = self.get_params(u)
        paramlist = []
        for p in params:
            if p.type == 'int':
                for v in p.int_val:
                    paramlist.append(v)
            if p.type == 'float':
                for v in p.dbl_val:
                    paramlist.append(v)
            if p.type == 'enum':
                for v in p.str_val:
                    paramlist.append(v)
        return paramlist
        
    def get_params(self, u):
        if u.shape[0] != self.cardinality:
            raise Exception("Hypercube dimensionality is incorrect.")

        params = []
        index  = 0
        for variable in self.variables:
            param = Parameter()
            
            param.name = variable['name']
            if variable['type'] == 'int':
                param.type = 'int'
                for dd in xrange(variable['size']):
                    param.int_val.append(variable['min'] + self._index_map(u[index], variable['max']-variable['min']+1))
                    index += 1

            elif variable['type'] == 'float':
                param.type = 'float'
                for dd in xrange(variable['size']):
                    val = variable['min'] + u[index]*(variable['max']-variable['min'])
                    val = variable['min'] if val < variable['min'] else val
                    val = variable['max'] if val > variable['max'] else val
                    param.dbl_val.append(val)
                    index += 1

            elif variable['type'] == 'enum':
                param.type = 'enum'
                for dd in xrange(variable['size']):
                    ii = self._index_map(u[index], len(variable['options']))
                    index += 1
                    param.str_val.append(variable['options'][ii])

            else:
                raise Exception("Unknown parameter type.")
            
            params.append(param)

        return params
            
    def card(self):
        return self.cardinality

    def _index_map(self, u, items):
        return int(np.floor((1-np.finfo(float).eps) * u * float(items)))

    def _index_unmap(self, u, items):
        return float(float(u) / float(items))

########NEW FILE########
__FILENAME__ = Locker
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
# 
# This code is written for research and educational purposes only to 
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import sys
import time

def safe_delete(filename):
    cmd  = 'mv "%s" "%s.delete" && rm "%s.delete"' % (filename, filename, 
                                                      filename)
    fail = os.system(cmd)
    return not fail

class Locker:

    def __init__(self):
        self.locks = {}

    def __del__(self):
        for filename in self.locks.keys():
            self.locks[filename] = 1
            self.unlock(filename)

    def lock(self, filename):
        if self.locks.has_key(filename):
            self.locks[filename] += 1
            return True
        else:
            cmd = 'ln -s /dev/null "%s.lock" 2> /dev/null' % (filename)
            fail = os.system(cmd)
            if not fail:
                self.locks[filename] = 1
            return not fail

    def unlock(self, filename):
        if not self.locks.has_key(filename):
            sys.stderr.write("Trying to unlock not-locked file %s.\n" % 
                             (filename))
            return True
        if self.locks[filename] == 1:
            success = safe_delete('%s.lock' % (filename))
            if not success:
                sys.stderr.write("Could not unlock file: %s.\n" % (filename))
            del self.locks[filename]
            return success
        else:
            self.locks[filename] -= 1
            return True
            
    def lock_wait(self, filename):
        while not self.lock(filename):
          time.sleep(0.01)

########NEW FILE########
__FILENAME__ = sobol_lib
import math
from numpy import *
def i4_bit_hi1 ( n ):
#*****************************************************************************80
#
## I4_BIT_HI1 returns the position of the high 1 bit base 2 in an integer.
#
#  Example:
#
#       N    Binary     BIT
#    ----    --------  ----
#       0           0     0
#       1           1     1
#       2          10     2
#       3          11     2 
#       4         100     3
#       5         101     3
#       6         110     3
#       7         111     3
#       8        1000     4
#       9        1001     4
#      10        1010     4
#      11        1011     4
#      12        1100     4
#      13        1101     4
#      14        1110     4
#      15        1111     4
#      16       10000     5
#      17       10001     5
#    1023  1111111111    10
#    1024 10000000000    11
#    1025 10000000001    11
#
#  	Licensing:
#
#    		This code is distributed under the GNU LGPL license.
#
#  	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#  	Parameters:
#
#    		Input, integer N, the integer to be measured.
#    		N should be nonnegative.  If N is nonpositive, the value will always be 0.
#
#    		Output, integer BIT, the number of bits base 2.
#
	i = math.floor ( n )
	bit = 0
	while ( 1 ):
		if ( i <= 0 ):
			break
		bit += 1
		i = math.floor ( i / 2. )
	return bit
def i4_bit_lo0 ( n ):
#*****************************************************************************80
#
## I4_BIT_LO0 returns the position of the low 0 bit base 2 in an integer.
#
#  Example:
#
#       N    Binary     BIT
#    ----    --------  ----
#       0           0     1
#       1           1     2
#       2          10     1
#       3          11     3 
#       4         100     1
#       5         101     2
#       6         110     1
#       7         111     4
#       8        1000     1
#       9        1001     2
#      10        1010     1
#      11        1011     3
#      12        1100     1
#      13        1101     2
#      14        1110     1
#      15        1111     5
#      16       10000     1
#      17       10001     2
#    1023  1111111111     1
#    1024 10000000000     1
#    1025 10000000001     1
#
#  	Licensing:
#
#    This code is distributed under the GNU LGPL license.
#
#  	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#  Parameters:
#
#    		Input, integer N, the integer to be measured.
#    		N should be nonnegative.
#
#    		Output, integer BIT, the position of the low 1 bit.
#
	bit = 0
	i = math.floor ( n )
	while ( 1 ):
		bit = bit + 1
		i2 = math.floor ( i / 2. )
		if ( i == 2 * i2 ):
			break

		i = i2
	return bit
	
def i4_sobol_generate ( m, n, skip ):
#*****************************************************************************80
#
## I4_SOBOL_GENERATE generates a Sobol dataset.
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#  	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#	Parameters:
#
#		Input, integer M, the spatial dimension.
#
#		Input, integer N, the number of points to generate.
#
#		Input, integer SKIP, the number of initial points to skip.
#
#		Output, real R(M,N), the points.
#
	r=zeros((m,n))
	for j in xrange (1, n+1):
		seed = skip + j - 2
		[ r[0:m,j-1], seed ] = i4_sobol ( m, seed )
	return r
def i4_sobol ( dim_num, seed ):
#*****************************************************************************80
#
## I4_SOBOL generates a new quasirandom Sobol vector with each call.
#
#	Discussion:
#
#		The routine adapts the ideas of Antonov and Saleev.
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original FORTRAN77 version by Bennett Fox.
#		MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#	Reference:
#
#		Antonov, Saleev,
#		USSR Computational Mathematics and Mathematical Physics,
#		Volume 19, 1980, pages 252 - 256.
#
#		Paul Bratley, Bennett Fox,
#		Algorithm 659:
#		Implementing Sobol's Quasirandom Sequence Generator,
#		ACM Transactions on Mathematical Software,
#		Volume 14, Number 1, pages 88-100, 1988.
#
#		Bennett Fox,
#		Algorithm 647:
#		Implementation and Relative Efficiency of Quasirandom 
#		Sequence Generators,
#		ACM Transactions on Mathematical Software,
#		Volume 12, Number 4, pages 362-376, 1986.
#
#		Ilya Sobol,
#		USSR Computational Mathematics and Mathematical Physics,
#		Volume 16, pages 236-242, 1977.
#
#		Ilya Sobol, Levitan, 
#		The Production of Points Uniformly Distributed in a Multidimensional 
#		Cube (in Russian),
#		Preprint IPM Akad. Nauk SSSR, 
#		Number 40, Moscow 1976.
#
#	Parameters:
#
#		Input, integer DIM_NUM, the number of spatial dimensions.
#		DIM_NUM must satisfy 1 <= DIM_NUM <= 40.
#
#		Input/output, integer SEED, the "seed" for the sequence.
#		This is essentially the index in the sequence of the quasirandom
#		value to be generated.	On output, SEED has been set to the
#		appropriate next value, usually simply SEED+1.
#		If SEED is less than 0 on input, it is treated as though it were 0.
#		An input value of 0 requests the first (0-th) element of the sequence.
#
#		Output, real QUASI(DIM_NUM), the next quasirandom vector.
#
	global atmost
	global dim_max
	global dim_num_save
	global initialized
	global lastq
	global log_max
	global maxcol
	global poly
	global recipd
	global seed_save
	global v

	if ( not 'initialized' in globals().keys() ):
		initialized = 0
		dim_num_save = -1

	if ( not initialized or dim_num != dim_num_save ):
		initialized = 1
		dim_max = 40
		dim_num_save = -1
		log_max = 30
		seed_save = -1
#
#	Initialize (part of) V.
#
		v = zeros((dim_max,log_max))
		v[0:40,0] = transpose([ \
			1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
			1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
			1, 1, 1, 1, 1, 1, 1, 1, 1, 1, \
			1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ])

		v[2:40,1] = transpose([ \
			1, 3, 1, 3, 1, 3, 3, 1, \
			3, 1, 3, 1, 3, 1, 1, 3, 1, 3, \
			1, 3, 1, 3, 3, 1, 3, 1, 3, 1, \
			3, 1, 1, 3, 1, 3, 1, 3, 1, 3 ])

		v[3:40,2] = transpose([ \
			7, 5, 1, 3, 3, 7, 5, \
			5, 7, 7, 1, 3, 3, 7, 5, 1, 1, \
			5, 3, 3, 1, 7, 5, 1, 3, 3, 7, \
			5, 1, 1, 5, 7, 7, 5, 1, 3, 3 ])

		v[5:40,3] = transpose([ \
			1, 7, 9,13,11, \
			1, 3, 7, 9, 5,13,13,11, 3,15, \
			5, 3,15, 7, 9,13, 9, 1,11, 7, \
			5,15, 1,15,11, 5, 3, 1, 7, 9 ])
	
		v[7:40,4] = transpose([ \
			9, 3,27, \
			15,29,21,23,19,11,25, 7,13,17, \
			1,25,29, 3,31,11, 5,23,27,19, \
			21, 5, 1,17,13, 7,15, 9,31, 9 ])

		v[13:40,5] = transpose([ \
							37,33, 7, 5,11,39,63, \
		 27,17,15,23,29, 3,21,13,31,25, \
			9,49,33,19,29,11,19,27,15,25 ])

		v[19:40,6] = transpose([ \
			13, \
			33,115, 41, 79, 17, 29,119, 75, 73,105, \
			7, 59, 65, 21,	3,113, 61, 89, 45,107 ])

		v[37:40,7] = transpose([ \
			7, 23, 39 ])
#
#	Set POLY.
#
		poly= [ \
			1,	 3,	 7,	11,	13,	19,	25,	37,	59,	47, \
			61,	55,	41,	67,	97,	91, 109, 103, 115, 131, \
			193, 137, 145, 143, 241, 157, 185, 167, 229, 171, \
			213, 191, 253, 203, 211, 239, 247, 285, 369, 299 ]

		atmost = 2**log_max - 1
#
#	Find the number of bits in ATMOST.
#
		maxcol = i4_bit_hi1 ( atmost )
#
#	Initialize row 1 of V.
#
		v[0,0:maxcol] = 1

#
#	Things to do only if the dimension changed.
#
	if ( dim_num != dim_num_save ):
#
#	Check parameters.
#
		if ( dim_num < 1 or dim_max < dim_num ):
			print 'I4_SOBOL - Fatal error!' 
			print '	The spatial dimension DIM_NUM should satisfy:' 
			print '		1 <= DIM_NUM <= %d'%dim_max
			print '	But this input value is DIM_NUM = %d'%dim_num
			return

		dim_num_save = dim_num
#
#	Initialize the remaining rows of V.
#
		for i in xrange(2 , dim_num+1):
#
#	The bits of the integer POLY(I) gives the form of polynomial I.
#
#	Find the degree of polynomial I from binary encoding.
#
			j = poly[i-1]
			m = 0
			while ( 1 ):
				j = math.floor ( j / 2. )
				if ( j <= 0 ):
					break
				m = m + 1
#
#	Expand this bit pattern to separate components of the logical array INCLUD.
#
			j = poly[i-1]
			includ=zeros(m)
			for k in xrange(m, 0, -1):
				j2 = math.floor ( j / 2. )
				includ[k-1] =  (j != 2 * j2 )
				j = j2
#
#	Calculate the remaining elements of row I as explained
#	in Bratley and Fox, section 2.
#
			for j in xrange( m+1, maxcol+1 ):
				newv = v[i-1,j-m-1]
				l = 1
				for k in xrange(1, m+1):
					l = 2 * l
					if ( includ[k-1] ):
						newv = bitwise_xor ( int(newv), int(l * v[i-1,j-k-1]) )
				v[i-1,j-1] = newv
#
#	Multiply columns of V by appropriate power of 2.
#
		l = 1
		for j in xrange( maxcol-1, 0, -1):
			l = 2 * l
			v[0:dim_num,j-1] = v[0:dim_num,j-1] * l
#
#	RECIPD is 1/(common denominator of the elements in V).
#
		recipd = 1.0 / ( 2 * l )
		lastq=zeros(dim_num)

	seed = int(math.floor ( seed ))

	if ( seed < 0 ):
		seed = 0

	if ( seed == 0 ):
		l = 1
		lastq=zeros(dim_num)

	elif ( seed == seed_save + 1 ):
#
#	Find the position of the right-hand zero in SEED.
#
		l = i4_bit_lo0 ( seed )

	elif ( seed <= seed_save ):

		seed_save = 0
		l = 1
		lastq=zeros(dim_num)

		for seed_temp in xrange( int(seed_save), int(seed)):
			l = i4_bit_lo0 ( seed_temp )
			for i in xrange(1 , dim_num+1):
				lastq[i-1] = bitwise_xor ( int(lastq[i-1]), int(v[i-1,l-1]) )

		l = i4_bit_lo0 ( seed )

	elif ( seed_save + 1 < seed ):

		for seed_temp in xrange( int(seed_save + 1), int(seed) ):
			l = i4_bit_lo0 ( seed_temp )
			for i in xrange(1, dim_num+1):
				lastq[i-1] = bitwise_xor ( int(lastq[i-1]), int(v[i-1,l-1]) )

		l = i4_bit_lo0 ( seed )
#
#	Check that the user is not calling too many times!
#
	if ( maxcol < l ):
		print 'I4_SOBOL - Fatal error!'
		print '	Too many calls!'
		print '	MAXCOL = %d\n'%maxcol
		print '	L =			%d\n'%l
		return
#
#	Calculate the new components of QUASI.
#
	quasi=zeros(dim_num)
	for i in xrange( 1, dim_num+1):
		quasi[i-1] = lastq[i-1] * recipd
		lastq[i-1] = bitwise_xor ( int(lastq[i-1]), int(v[i-1,l-1]) )

	seed_save = seed
	seed = seed + 1

	return [ quasi, seed ]
def i4_uniform ( a, b, seed ):
#*****************************************************************************80
#
## I4_UNIFORM returns a scaled pseudorandom I4.
#
#	Discussion:
#
#		The pseudorandom number will be scaled to be uniformly distributed
#		between A and B.
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#	Reference:
#
#		Paul Bratley, Bennett Fox, Linus Schrage,
#		A Guide to Simulation,
#		Springer Verlag, pages 201-202, 1983.
#
#		Pierre L'Ecuyer,
#		Random Number Generation,
#		in Handbook of Simulation,
#		edited by Jerry Banks,
#		Wiley Interscience, page 95, 1998.
#
#		Bennett Fox,
#		Algorithm 647:
#		Implementation and Relative Efficiency of Quasirandom
#		Sequence Generators,
#		ACM Transactions on Mathematical Software,
#		Volume 12, Number 4, pages 362-376, 1986.
#
#		Peter Lewis, Allen Goodman, James Miller
#		A Pseudo-Random Number Generator for the System/360,
#		IBM Systems Journal,
#		Volume 8, pages 136-143, 1969.
#
#	Parameters:
#
#		Input, integer A, B, the minimum and maximum acceptable values.
#
#		Input, integer SEED, a seed for the random number generator.
#
#		Output, integer C, the randomly chosen integer.
#
#		Output, integer SEED, the updated seed.
#
	if ( seed == 0 ):
		print 'I4_UNIFORM - Fatal error!' 
		print '	Input SEED = 0!'

	seed = math.floor ( seed )
	a = round ( a )
	b = round ( b )

	seed = mod ( seed, 2147483647 )

	if ( seed < 0 ) :
		seed = seed + 2147483647

	k = math.floor ( seed / 127773 )

	seed = 16807 * ( seed - k * 127773 ) - k * 2836

	if ( seed < 0 ):
		seed = seed + 2147483647

	r = seed * 4.656612875E-10
#
#	Scale R to lie between A-0.5 and B+0.5.
#
	r = ( 1.0 - r ) * ( min ( a, b ) - 0.5 ) + r * ( max ( a, b ) + 0.5 )
#
#	Use rounding to convert R to an integer between A and B.
#
	value = round ( r )

	value = max ( value, min ( a, b ) )
	value = min ( value, max ( a, b ) )

	c = value

	return [ int(c), int(seed) ]
def prime_ge ( n ):
#*****************************************************************************80
#
## PRIME_GE returns the smallest prime greater than or equal to N.
#
#
#	Example:
#
#		N		 PRIME_GE
#
#		-10		2
#			1		2
#			2		2
#			3		3
#			4		5
#			5		5
#			6		7
#			7		7
#			8	 11
#			9	 11
#		 10	 11
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Original MATLAB version by John Burkardt.
#		PYTHON version by Corrado Chisari
#
#	Parameters:
#
#		Input, integer N, the number to be bounded.
#
#		Output, integer P, the smallest prime number that is greater
#		than or equal to N.	
#
	p = max ( math.ceil ( n ), 2 )
	while ( not isprime ( p ) ):
		p = p + 1

	return p

def isprime(n):
	#*****************************************************************************80
#
## IS_PRIME returns True if N is a prime number, False otherwise
#
#
#	Licensing:
#
#		This code is distributed under the GNU LGPL license.
#
#	Modified:
#
#    		22 February 2011
#
#	Author:
#
#		Corrado Chisari
#
#	Parameters:
#
#		Input, integer N, the number to be checked.
#
#		Output, boolean value, True or False
#
	if n!=int(n) or n<1:
		return False
	p=2
	while p<n:
		if n%p==0:
			return False
		p+=1
	return True
	
########NEW FILE########
__FILENAME__ = spearmint-lite
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
#
# This code is written for research and educational purposes only to
# supplement the paper entitled "Practical Bayesian Optimization of
# Machine Learning Algorithms" by Snoek, Larochelle and Adams Advances
# in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
import optparse
import tempfile
import datetime
import subprocess
import time
import imp
import os
import re
import collections
import importlib

from ExperimentGrid  import *
try: import simplejson as json
except ImportError: import json

#
# There are two things going on here.  There are "experiments", which are
# large-scale things that live in a directory and in this case correspond
# to the task of minimizing a complicated function.  These experiments
# contain "jobs" which are individual function evaluations.  The set of
# all possible jobs, regardless of whether they have been run or not, is
# the "grid".  This grid is managed by an instance of the class
# ExperimentGrid.
#
# The spearmint.py script can run in two modes, which reflect experiments
# vs jobs.  When run with the --wrapper argument, it will try to run a
# single job.  This is not meant to be run by hand, but is intended to be
# run by a job queueing system.  Without this argument, it runs in its main
# controller mode, which determines the jobs that should be executed and
# submits them to the queueing system.
#

def main():
    parser = optparse.OptionParser(usage="usage: %prog [options] directory")

    parser.add_option("--n", dest="num_jobs",
                      help="Number of concurrent jobs to create.",
                      type="int", default=1)
    parser.add_option("--max-finished-jobs", dest="max_finished_jobs",
                      type="int", default=1000)
    parser.add_option("--method", dest="chooser_module",
                      help="Method for choosing experiments.",
                      type="string", default="GPEIOptChooser")
    parser.add_option("--method-args", dest="chooser_args",
                      help="Arguments to pass to chooser module.",
                      type="string", default="")
    parser.add_option("--grid-size", dest="grid_size",
                      help="Number of experiments in initial grid.",
                      type="int", default=1000)
    parser.add_option("--grid-seed", dest="grid_seed",
                      help="The seed used to initialize initial grid.",
                      type="int", default=1)
    parser.add_option("--config", dest="config_file",
                      help="Configuration file name.",
                      type="string", default="config.json")
    parser.add_option("--results", dest="results_file",
                      help="Results file name.",
                      type="string", default="results.dat")

    (options, args) = parser.parse_args()

    # Otherwise run in controller mode.
    main_controller(options, args)

##############################################################################
##############################################################################
def main_controller(options, args):

    expt_dir  = os.path.realpath(args[0])
    work_dir  = os.path.realpath('.')
    expt_name = os.path.basename(expt_dir)

    if not os.path.exists(expt_dir):
        sys.stderr.write("Cannot find experiment directory '%s'.  Aborting.\n" % (expt_dir))
        sys.exit(-1)

    # Load up the chooser module.
    module  = importlib.import_module('chooser.' + options.chooser_module, package='spearmint')
    chooser = module.init(expt_dir, options.chooser_args)

    # Create the experimental grid
    expt_file = os.path.join(expt_dir, options.config_file)
    variables = json.load(open(expt_file), object_pairs_hook=collections.OrderedDict)

    #@gdahl - added the following three lines and commented out the line above
    vkeys = [k for k in variables]
    #vkeys.sort()
    gmap = GridMap([variables[k] for k in vkeys], options.grid_size)

    # Read in parameters and values observed so far
    for i in xrange(0,options.num_jobs):

        res_file = os.path.join(expt_dir, options.results_file)
        if not os.path.exists(res_file):
            thefile = open(res_file, 'w')
            thefile.write("")
            thefile.close()

        values = np.array([])
        complete = np.array([])
        pending = np.array([])
        durations = np.array([])
        index = 0

        infile = open(res_file, 'r')
        for line in infile.readlines():
            # Each line in this file represents an experiment
            # It is whitespace separated and of the form either
            # <Value> <time taken> <space separated list of parameters>
            # incating a completed experiment or
            # P P <space separated list of parameters>
            # indicating a pending experiment
            expt = line.split()
            if (len(expt) < 3):
                continue

            val = expt.pop(0)
            dur = expt.pop(0)
            variables = gmap.to_unit(expt)
            if val == 'P':
                if pending.shape[0] > 0:
                    pending = np.vstack((pending, variables))
                else:
                    pending = np.matrix(variables)
            else:
                if complete.shape[0] > 0:
                    values = np.vstack((values, float(val)))
                    complete = np.vstack((complete, variables))
                    durations = np.vstack((durations, float(dur)))
                else:
                    values = float(val)
                    complete = np.matrix(variables)
                    durations = float(dur)

        infile.close()
        # Some stats
        sys.stderr.write("#Complete: %d #Pending: %d\n" %
                         (complete.shape[0], pending.shape[0]))

        # Let's print out the best value so far
        if type(values) is not float and len(values) > 0:
            best_val = np.min(values)
            best_job = np.argmin(values)
            sys.stderr.write("Current best: %f (job %d)\n" % (best_val, best_job))

        # Now lets get the next job to run
        # First throw out a set of candidates on the unit hypercube
        # Increment by the number of observed so we don't take the
        # same values twice
        off = pending.shape[0] + complete.shape[0]
        candidates = gmap.hypercube_grid(options.grid_size,
                                         options.grid_seed+off)

        # Ask the chooser to actually pick one.
        # First mash the data into a format that matches that of the other
        # spearmint drivers to pass to the chooser modules.
        grid = candidates
        if (complete.shape[0] > 0):
            grid = np.vstack((complete, candidates))
        if (pending.shape[0] > 0):
            grid = np.vstack((grid, pending))
        grid = np.asarray(grid)
        grid_idx = np.hstack((np.zeros(complete.shape[0]),
                              np.ones(candidates.shape[0]),
                              1.+np.ones(pending.shape[0])))
        job_id = chooser.next(grid, np.squeeze(values), durations,
                              np.nonzero(grid_idx == 1)[0],
                              np.nonzero(grid_idx == 2)[0],
                              np.nonzero(grid_idx == 0)[0])

        # If the job_id is a tuple, then the chooser picked a new job not from
        # the candidate list
        if isinstance(job_id, tuple):
            (job_id, candidate) = job_id
        else:
            candidate = grid[job_id,:]

        sys.stderr.write("Selected job %d from the grid.\n" % (job_id))
        if pending.shape[0] > 0:
            pending = np.vstack((pending, candidate))
        else:
            pending = np.matrix(candidate)

        params = gmap.unit_to_list(candidate)

        # Now lets write this candidate to the file as pending
        output = ""
        for p in params:
            output = output + str(p) + " "

        output = "P P " + output + "\n"
        outfile = open(res_file,"a")
        outfile.write(output)
        outfile.close()

# And that's it
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = util
##
# Copyright (C) 2012 Jasper Snoek, Hugo Larochelle and Ryan P. Adams
# 
# This code is written for research and educational purposes only to 
# supplement the paper entitled
# "Practical Bayesian Optimization of Machine Learning Algorithms"
# by Snoek, Larochelle and Adams
# Advances in Neural Information Processing Systems, 2012
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re
import numpy        as np
import numpy.random as npr

def unpack_args(str):
    if len(str) > 1:
        eq_re = re.compile("\s*=\s*")
        return dict(map(lambda x: eq_re.split(x),
                        re.compile("\s*,\s*").split(str)))
    else:
        return {}

def slice_sample(init_x, logprob, sigma=1.0, step_out=True, max_steps_out=1000, 
                 compwise=False, verbose=False):
    def direction_slice(direction, init_x):
        def dir_logprob(z):
            return logprob(direction*z + init_x)
    
        upper = sigma*npr.rand()
        lower = upper - sigma
        llh_s = np.log(npr.rand()) + dir_logprob(0.0)
    
        l_steps_out = 0
        u_steps_out = 0
        if step_out:
            while dir_logprob(lower) > llh_s and l_steps_out < max_steps_out:
                l_steps_out += 1
                lower       -= sigma
            while dir_logprob(upper) > llh_s and u_steps_out < max_steps_out:
                u_steps_out += 1
                upper       += sigma
            
        steps_in = 0
        while True:
            steps_in += 1
            new_z     = (upper - lower)*npr.rand() + lower
            new_llh   = dir_logprob(new_z)
            if np.isnan(new_llh):
                print new_z, direction*new_z + init_x, new_llh, llh_s, init_x, logprob(init_x)
                raise Exception("Slice sampler got a NaN")
            if new_llh > llh_s:
                break
            elif new_z < 0:
                lower = new_z
            elif new_z > 0:
                upper = new_z
            else:
                raise Exception("Slice sampler shrank to zero!")

        if verbose:
            print "Steps Out:", l_steps_out, u_steps_out, " Steps In:", steps_in

        return new_z*direction + init_x
    
    if not init_x.shape:
        init_x = np.array([init_x])

    dims = init_x.shape[0]
    if compwise:
        ordering = range(dims)
        npr.shuffle(ordering)
        cur_x = init_x.copy()
        for d in ordering:
            direction    = np.zeros((dims))
            direction[d] = 1.0
            cur_x = direction_slice(direction, cur_x)
        return cur_x
            
    else:
        direction = npr.randn(dims)
        direction = direction / np.sqrt(np.sum(direction**2))
        return direction_slice(direction, init_x)

########NEW FILE########
