__FILENAME__ = abstractions
from __future__ import division
import abc
import numpy as np
from matplotlib import pyplot as plt

from pybasicbayes.abstractions import *
from ..util.stats import flattendata, sample_discrete_from_log, combinedata
from ..util.general import rcumsum

class DurationDistribution(Distribution):
    __metaclass__ = abc.ABCMeta

    # in addition to the methods required by Distribution, we also require a
    # log_sf implementation

    @abc.abstractmethod
    def log_sf(self,x):
        '''
        log survival function, defined by log_sf(x) = log(P[X \gt x]) =
        log(1-cdf(x)) where cdf(x) = P[X \leq x]
        '''
        pass

    def log_pmf(self,x):
        return self.log_likelihood(x)

    def expected_log_pmf(self,x):
        return self.expected_log_likelihood(x)

    # default implementations below

    def pmf(self,x):
        return np.exp(self.log_pmf(x))

    def rvs_given_greater_than(self,x):
        tail = self.log_sf(x)
        if np.isinf(tail):
            return x+1
        trunc = 500
        while self.log_sf(x+trunc) - tail > -20:
            trunc = int(1.1*trunc)
        logprobs = self.log_pmf(np.arange(x+1,x+trunc+1)) - tail
        return sample_discrete_from_log(logprobs)+x+1

    def expected_log_sf(self,x):
        x = np.atleast_1d(x).astype('int32')
        assert x.ndim == 1
        inf = max(2*x.max(),2*1000) # approximately infinity, we hope
        return rcumsum(self.expected_log_pmf(np.arange(1,inf)),strict=True)[x]

    def resample_with_truncations(self,data=[],truncated_data=[]):
        '''
        truncated_data is full of observations that were truncated, so this
        method samples them out to be at least that large
        '''
        if not isinstance(truncated_data,list):
            filled_in = np.asarray([self.rvs_given_greater_than(x-1) for x in truncated_data])
        else:
            filled_in = np.asarray([self.rvs_given_greater_than(x-1)
                for xx in truncated_data for x in xx])
        self.resample(data=combinedata((data,filled_in)))

    @property
    def mean(self):
        trunc = 500
        while self.log_sf(trunc) > -20:
            trunc *= 1.5
        return np.arange(1,trunc+1).dot(self.pmf(np.arange(1,trunc+1)))

    def plot(self,data=None,color='b',**kwargs):
        data = flattendata(data) if data is not None else None

        try:
            tmax = np.where(np.exp(self.log_sf(np.arange(1,1000))) < 1e-3)[0][0]
        except IndexError:
            tmax = 2*self.rvs(1000).mean()
        tmax = max(tmax,data.max()) if data is not None else tmax

        t = np.arange(1,tmax+1)
        plt.plot(t,self.pmf(t),color=color)

        if data is not None:
            if len(data) > 1:
                plt.hist(data,bins=t-0.5,color=color,normed=len(set(data)) > 1)
            else:
                plt.hist(data,bins=t-0.5,color=color)


########NEW FILE########
__FILENAME__ = distributions
from __future__ import division
import numpy as np
import scipy.stats as stats
import scipy.special as special

from pybasicbayes.distributions import *
from pybasicbayes.models import MixtureDistribution
from abstractions import DurationDistribution

##############################################
#  Mixins for making duratino distributions  #
##############################################

class _StartAtOneMixin(object):
    def log_likelihood(self,x,*args,**kwargs):
        return super(_StartAtOneMixin,self).log_likelihood(x-1,*args,**kwargs)

    def log_sf(self,x,*args,**kwargs):
        return super(_StartAtOneMixin,self).log_sf(x-1,*args,**kwargs)

    def expected_log_likelihood(self,x,*args,**kwargs):
        return super(_StartAtOneMixin,self).expected_log_likelihood(x-1,*args,**kwargs)

    def rvs(self,size=None):
        return super(_StartAtOneMixin,self).rvs(size)+1

    def rvs_given_greater_than(self,x):
        return super(_StartAtOneMixin,self).rvs_given_greater_than(x)+1

    def resample(self,data=[],*args,**kwargs):
        if isinstance(data,np.ndarray):
            return super(_StartAtOneMixin,self).resample(data-1,*args,**kwargs)
        else:
            return super(_StartAtOneMixin,self).resample([d-1 for d in data],*args,**kwargs)

    def max_likelihood(self,data,weights=None,*args,**kwargs):
        if isinstance(data,np.ndarray):
            return super(_StartAtOneMixin,self).max_likelihood(
                    data-1,weights=weights,*args,**kwargs)
        else:
            return super(_StartAtOneMixin,self).max_likelihood(
                    [d-1 for d in data],weights=weights,*args,**kwargs)

    def meanfieldupdate(self,data,weights,*args,**kwargs):
        if isinstance(data,np.ndarray):
            return super(_StartAtOneMixin,self).meanfieldupdate(
                    data-1,weights=weights,*args,**kwargs)
        else:
            return super(_StartAtOneMixin,self).meanfieldupdate(
                    [d-1 for d in data],weights=weights,*args,**kwargs)

    def meanfield_sgdstep(self,data,weights,minibatchfrac,stepsize):
        if isinstance(data,np.ndarray):
            return super(_StartAtOneMixin,self).meanfield_sgdstep(
                    data-1,weights=weights,
                    minibatchfrac=minibatchfrac,stepsize=stepsize)
        else:
            return super(_StartAtOneMixin,self).meanfield_sgdstep(
                    [d-1 for d in data],weights=weights,
                    minibatchfrac=minibatchfrac,stepsize=stepsize)

##########################
#  Distribution classes  #
##########################

class GeometricDuration(
        Geometric,
        DurationDistribution):
    pass

class PoissonDuration(
        _StartAtOneMixin,
        Poisson,
        DurationDistribution):
    pass

class NegativeBinomialDuration(
        _StartAtOneMixin,
        NegativeBinomial,
        DurationDistribution):
    pass

class NegativeBinomialFixedRDuration(
        _StartAtOneMixin,
        NegativeBinomialFixedR,
        DurationDistribution):
    pass

class NegativeBinomialIntegerRDuration(
        _StartAtOneMixin,
        NegativeBinomialIntegerR,
        DurationDistribution):
    pass

class NegativeBinomialIntegerR2Duration(
        _StartAtOneMixin,
        NegativeBinomialIntegerR2,
        DurationDistribution):
    pass

class NegativeBinomialFixedRVariantDuration(
        NegativeBinomialFixedRVariant,
        DurationDistribution):
    pass

class NegativeBinomialIntegerRVariantDuration(
        NegativeBinomialIntegerRVariant,
        DurationDistribution):
    pass

#################
#  Model stuff  #
#################

# this is extending the MixtureDistribution from basic/pybasicbayes/models.py
# and then clobbering the name
class MixtureDistribution(MixtureDistribution, DurationDistribution):
    # TODO test this
    def log_sf(self,x):
        x = np.asarray(x,dtype=np.float64)
        K = len(self.components)
        vals = np.empty((x.shape[0],K))
        for idx, c in enumerate(self.components):
            vals[:,idx] = c.log_sf(x)
        vals += self.weights.log_likelihood(np.arange(K))
        return np.logaddexp.reduce(vals,axis=1)

##########
#  Meta  #
##########

# this class is for delaying instances of duration distributions
class Delay(DurationDistribution):
    def __init__(self,dur_distn,delay):
        self.dur_distn = dur_distn
        self.delay = delay

    def log_sf(self,x):
        return self.dur_distn.log_sf(x-self.delay)

    def log_likelihood(self,x):
        return self.dur_distn.log_likelihood(x-self.delay)

    def rvs(self,size=None):
        return self.dur_distn.rvs(size) + self.delay

    def resample(self,data=[],*args,**kwargs):
        if isinstance(data,np.ndarray):
            return self.dur_distn.resample(data-self.delay,*args,**kwargs)
        else:
            return self.dur_distn.resample([d-self.delay for d in data],*args,**kwargs)

    def max_likelihood(self,*args,**kwargs):
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = models
from pybasicbayes.models import *

########NEW FILE########
__FILENAME__ = printers
# -*- coding: utf-8 -*-
# This file is part of Eigen, a lightweight C++ template library
# for linear algebra.
#
# Copyright (C) 2009 Benjamin Schindler <bschindler@inf.ethz.ch>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Pretty printers for Eigen::Matrix
# This is still pretty basic as the python extension to gdb is still pretty basic. 
# It cannot handle complex eigen types and it doesn't support any of the other eigen types
# Such as quaternion or some other type. 
# This code supports fixed size as well as dynamic size matrices

# To use it:
#
# * Create a directory and put the file as well as an empty __init__.py in 
#   that directory.
# * Create a ~/.gdbinit file, that contains the following:
#      python
#      import sys
#      sys.path.insert(0, '/path/to/eigen/printer/directory')
#      from printers import register_eigen_printers
#      register_eigen_printers (None)
#      end

import gdb
import re
import itertools


class EigenMatrixPrinter:
	"Print Eigen Matrix or Array of some kind"

	def __init__(self, variety, val):
		"Extract all the necessary information"
		
		# Save the variety (presumably "Matrix" or "Array") for later usage
		self.variety = variety
		
		# The gdb extension does not support value template arguments - need to extract them by hand
		type = val.type
		if type.code == gdb.TYPE_CODE_REF:
			type = type.target()
		self.type = type.unqualified().strip_typedefs()
		tag = self.type.tag
		regex = re.compile('\<.*\>')
		m = regex.findall(tag)[0][1:-1]
		template_params = m.split(',')
		template_params = map(lambda x:x.replace(" ", ""), template_params)
		
		if template_params[1] == '-0x00000000000000001' or template_params[1] == '-0x000000001' or template_params[1] == '-1':
			self.rows = val['m_storage']['m_rows']
		else:
			self.rows = int(template_params[1])
		
		if template_params[2] == '-0x00000000000000001' or template_params[2] == '-0x000000001' or template_params[2] == '-1':
			self.cols = val['m_storage']['m_cols']
		else:
			self.cols = int(template_params[2])
		
		self.options = 0 # default value
		if len(template_params) > 3:
			self.options = template_params[3];
		
		self.rowMajor = (int(self.options) & 0x1)
		
		self.innerType = self.type.template_argument(0)
		
		self.val = val
		
		# Fixed size matrices have a struct as their storage, so we need to walk through this
		self.data = self.val['m_storage']['m_data']
		if self.data.type.code == gdb.TYPE_CODE_STRUCT:
			self.data = self.data['array']
			self.data = self.data.cast(self.innerType.pointer())
			
	class _iterator:
		def __init__ (self, rows, cols, dataPtr, rowMajor):
			self.rows = rows
			self.cols = cols
			self.dataPtr = dataPtr
			self.currentRow = 0
			self.currentCol = 0
			self.rowMajor = rowMajor
			
		def __iter__ (self):
			return self
			
		def next(self):
			
			row = self.currentRow
			col = self.currentCol
			if self.rowMajor == 0:
				if self.currentCol >= self.cols:
					raise StopIteration
					
				self.currentRow = self.currentRow + 1
				if self.currentRow >= self.rows:
					self.currentRow = 0
					self.currentCol = self.currentCol + 1
			else:
				if self.currentRow >= self.rows:
					raise StopIteration
					
				self.currentCol = self.currentCol + 1
				if self.currentCol >= self.cols:
					self.currentCol = 0
					self.currentRow = self.currentRow + 1
				
			
			item = self.dataPtr.dereference()
			self.dataPtr = self.dataPtr + 1
			if (self.cols == 1): #if it's a column vector
				return ('[%d]' % (row,), item)
			elif (self.rows == 1): #if it's a row vector
				return ('[%d]' % (col,), item)
			return ('[%d,%d]' % (row, col), item)
			
	def children(self):
		
		return self._iterator(self.rows, self.cols, self.data, self.rowMajor)
		
	def to_string(self):
		return "Eigen::%s<%s,%d,%d,%s> (data ptr: %s)" % (self.variety, self.innerType, self.rows, self.cols, "RowMajor" if self.rowMajor else  "ColMajor", self.data)

class EigenQuaternionPrinter:
	"Print an Eigen Quaternion"
	
	def __init__(self, val):
		"Extract all the necessary information"
		# The gdb extension does not support value template arguments - need to extract them by hand
		type = val.type
		if type.code == gdb.TYPE_CODE_REF:
			type = type.target()
		self.type = type.unqualified().strip_typedefs()
		self.innerType = self.type.template_argument(0)
		self.val = val
		
		# Quaternions have a struct as their storage, so we need to walk through this
		self.data = self.val['m_coeffs']['m_storage']['m_data']['array']
		self.data = self.data.cast(self.innerType.pointer())
			
	class _iterator:
		def __init__ (self, dataPtr):
			self.dataPtr = dataPtr
			self.currentElement = 0
			self.elementNames = ['x', 'y', 'z', 'w']
			
		def __iter__ (self):
			return self
			
		def next(self):
			element = self.currentElement
			
			if self.currentElement >= 4: #there are 4 elements in a quanternion
				raise StopIteration
			
			self.currentElement = self.currentElement + 1
			
			item = self.dataPtr.dereference()
			self.dataPtr = self.dataPtr + 1
			return ('[%s]' % (self.elementNames[element],), item)
			
	def children(self):
		
		return self._iterator(self.data)
	
	def to_string(self):
		return "Eigen::Quaternion<%s> (data ptr: %s)" % (self.innerType, self.data)

def build_eigen_dictionary ():
	pretty_printers_dict[re.compile('^Eigen::Quaternion<.*>$')] = lambda val: EigenQuaternionPrinter(val)
	pretty_printers_dict[re.compile('^Eigen::Matrix<.*>$')] = lambda val: EigenMatrixPrinter("Matrix", val)
	pretty_printers_dict[re.compile('^Eigen::Array<.*>$')]  = lambda val: EigenMatrixPrinter("Array",  val)

def register_eigen_printers(obj):
	"Register eigen pretty-printers with objfile Obj"

	if obj == None:
		obj = gdb
	obj.pretty_printers.append(lookup_function)

def lookup_function(val):
	"Look-up and return a pretty-printer that can print va."
	
	type = val.type
	
	if type.code == gdb.TYPE_CODE_REF:
		type = type.target()
	
	type = type.unqualified().strip_typedefs()
	
	typename = type.tag
	if typename == None:
		return None
	
	for function in pretty_printers_dict:
		if function.search(typename):
			return pretty_printers_dict[function](val)
	
	return None

pretty_printers_dict = {}

build_eigen_dictionary ()

########NEW FILE########
__FILENAME__ = relicense
# This file is part of Eigen, a lightweight C++ template library
# for linear algebra.
#
# Copyright (C) 2012 Keir Mierle <mierle@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla
# Public License v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: mierle@gmail.com (Keir Mierle)
#
# Make the long-awaited conversion to MPL.

lgpl3_header = '''
// Eigen is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation; either
// version 3 of the License, or (at your option) any later version.
//
// Alternatively, you can redistribute it and/or
// modify it under the terms of the GNU General Public License as
// published by the Free Software Foundation; either version 2 of
// the License, or (at your option) any later version.
//
// Eigen is distributed in the hope that it will be useful, but WITHOUT ANY
// WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
// FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License or the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License and a copy of the GNU General Public License along with
// Eigen. If not, see <http://www.gnu.org/licenses/>.
'''

mpl2_header = """
// This Source Code Form is subject to the terms of the Mozilla
// Public License v. 2.0. If a copy of the MPL was not distributed
// with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import os
import sys

exclusions = set(['relicense.py'])

def update(text):
  if text.find(lgpl3_header) == -1:
    return text, False
  return text.replace(lgpl3_header, mpl2_header), True

rootdir = sys.argv[1]
for root, sub_folders, files in os.walk(rootdir):
    for basename in files:
        if basename in exclusions:
          print 'SKIPPED', filename
          continue
        filename = os.path.join(root, basename)
        fo = file(filename)
        text = fo.read()
        fo.close()

        text, updated = update(text)
        if updated:
          fo = file(filename, "w")
          fo.write(text)
          fo.close()
          print 'UPDATED', filename
        else:
          print '       ', filename

########NEW FILE########
__FILENAME__ = concentration-resampling
from __future__ import division
import numpy as np
np.seterr(divide='ignore') # these warnings are usually harmless for this code
from matplotlib import pyplot as plt
import os
import scipy.stats as stats

import pyhsmm
from pyhsmm.util.text import progprint_xrange

###############
#  load data  #
###############

T = 1000
data = np.loadtxt(os.path.join(os.path.dirname(__file__),'example-data.txt'))[:T]

#########################
#  posterior inference  #
#########################

Nmax = 20
obs_dim = data.shape[1]
obs_hypparams = {'mu_0':np.zeros(obs_dim),
                'sigma_0':np.eye(obs_dim),
                'kappa_0':0.25,
                'nu_0':obs_dim+2}
dur_hypparams = {'alpha_0':2*30,
                 'beta_0':2}

obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in range(Nmax)]
dur_distns = [pyhsmm.distributions.PoissonDuration(**dur_hypparams) for state in range(Nmax)]

posteriormodel = pyhsmm.models.WeakLimitHDPHSMM(
        # NOTE: instead of passing in alpha_0 and gamma_0, we pass in parameters
        # for priors over those concentration parameters
        alpha_a_0=1.,alpha_b_0=1./4,
        gamma_a_0=1.,gamma_b_0=1./4,
        init_state_concentration=6.,
        obs_distns=obs_distns,
        dur_distns=dur_distns)
posteriormodel.add_data(data,trunc=70)

for idx in progprint_xrange(100):
    posteriormodel.resample_model()

plt.figure()
posteriormodel.plot()
plt.gcf().suptitle('Sampled after 100 iterations')

plt.figure()
t = np.linspace(0.01,30,1000)
plt.plot(t,stats.gamma.pdf(t,1.,scale=4.)) # NOTE: numpy/scipy scale is inverted compared to my scale
plt.title('Prior on concentration parameters')

plt.show()

########NEW FILE########
__FILENAME__ = hmm-EM
from __future__ import division
import numpy as np
np.seterr(divide='ignore') # these warnings are usually harmless for this code
from matplotlib import pyplot as plt
import matplotlib
import os
matplotlib.rcParams['font.size'] = 8

import pyhsmm
from pyhsmm.util.text import progprint_xrange

save_images = False

#### load data

data = np.loadtxt(os.path.join(os.path.dirname(__file__),'example-data.txt'))

#### EM

N = 4
obs_dim = data.shape[1]
obs_hypparams = {'mu_0':np.zeros(obs_dim),
                'sigma_0':np.eye(obs_dim),
                'kappa_0':0.25,
                'nu_0':obs_dim+2}

obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in xrange(N)]

# Build the HMM model that will represent the fitmodel
fitmodel = pyhsmm.models.HMM(
        alpha=50.,init_state_concentration=50., # these are only used for initialization
        obs_distns=obs_distns)
fitmodel.add_data(data)

print 'Gibbs sampling for initialization'

for idx in progprint_xrange(25):
    fitmodel.resample_model()

plt.figure()
fitmodel.plot()
plt.gcf().suptitle('Gibbs-sampled initialization')

print 'EM'

likes = fitmodel.EM_fit()

plt.figure()
fitmodel.plot()
plt.gcf().suptitle('EM fit')

plt.figure()
plt.plot(likes)
plt.gcf().suptitle('log likelihoods during EM')

plt.show()


########NEW FILE########
__FILENAME__ = hmm
from __future__ import division
import numpy as np
np.seterr(divide='ignore') # these warnings are usually harmless for this code
from matplotlib import pyplot as plt
import matplotlib
import os
matplotlib.rcParams['font.size'] = 8

import pyhsmm
from pyhsmm.util.text import progprint_xrange

print \
'''
This demo shows how HDP-HMMs can fail when the underlying data has state
persistence without some kind of temporal regularization (in the form of a
sticky bias or duration modeling): without setting the number of states to be
the correct number a priori, lots of extra states can be intsantiated.

BUT the effect is much more relevant on real data (when the data doesn't exactly
fit the model). Maybe this demo should use multinomial emissions...
'''

###############
#  load data  #
###############

data = np.loadtxt(os.path.join(os.path.dirname(__file__),'example-data.txt'))

#########################
#  posterior inference  #
#########################

# Set the weak limit truncation level
Nmax = 25

# and some hyperparameters
obs_dim = data.shape[1]
obs_hypparams = {'mu_0':np.zeros(obs_dim),
                'sigma_0':np.eye(obs_dim),
                'kappa_0':0.25,
                'nu_0':obs_dim+2}

### HDP-HMM without the sticky bias

obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in xrange(Nmax)]
posteriormodel = pyhsmm.models.WeakLimitHDPHMM(alpha=6.,gamma=6.,init_state_concentration=1.,
                                   obs_distns=obs_distns)
posteriormodel.add_data(data)

for idx in progprint_xrange(100):
    posteriormodel.resample_model()

plt.figure()
posteriormodel.plot()
plt.gcf().suptitle('HDP-HMM sampled model after 100 iterations')

### Sticky-HDP-HMM

obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in xrange(Nmax)]
posteriormodel = pyhsmm.models.WeakLimitStickyHDPHMM(
        kappa=50.,alpha=6.,gamma=6.,init_state_concentration=1.,
        obs_distns=obs_distns)
posteriormodel.add_data(data)

for idx in progprint_xrange(100):
    posteriormodel.resample_model()

plt.figure()
posteriormodel.plot()
plt.gcf().suptitle('Sticky HDP-HMM sampled model after 100 iterations')

plt.show()


########NEW FILE########
__FILENAME__ = hsmm-geo
from __future__ import division
import numpy as np
np.seterr(divide='ignore') # these warnings are usually harmless for this code
from matplotlib import pyplot as plt
import copy, os

import pyhsmm
from pyhsmm.util.text import progprint_xrange

###################
#  generate data  #
###################

T = 1000
obs_dim = 2
N = 4

obs_hypparams = {'mu_0':np.zeros(obs_dim),
                'sigma_0':np.eye(obs_dim),
                'kappa_0':0.25,
                'nu_0':obs_dim+2}
dur_hypparams = {'alpha_0':10*1,
                 'beta_0':10*100}

true_obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams)
        for state in range(N)]
true_dur_distns = [pyhsmm.distributions.GeometricDuration(**dur_hypparams)
        for state in range(N)]

truemodel = pyhsmm.models.WeakLimitGeoHDPHSMM(
        alpha=6.,gamma=6.,
        init_state_concentration=6.,
        obs_distns=true_obs_distns,
        dur_distns=true_dur_distns)

data, labels = truemodel.generate(T)

plt.figure()
truemodel.plot()

#########################
#  posterior inference  #
#########################

Nmax = 25

obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in range(Nmax)]
dur_distns = [pyhsmm.distributions.GeometricDuration(**dur_hypparams) for state in range(Nmax)]

posteriormodel = pyhsmm.models.WeakLimitGeoHDPHSMM(
        alpha=6.,gamma=6.,
        init_state_concentration=6.,
        obs_distns=obs_distns,
        dur_distns=dur_distns)
posteriormodel.add_data(data)

for idx in progprint_xrange(50):
    posteriormodel.resample_model()

plt.figure()
posteriormodel.plot()

plt.show()

########NEW FILE########
__FILENAME__ = hsmm-possiblechangepoints
from __future__ import division
import numpy as np
np.seterr(divide='ignore')
from matplotlib import pyplot as plt

import pyhsmm
from pyhsmm.util.text import progprint_xrange

#####################
#  data generation  #
#####################

N = 4
T = 1000
obs_dim = 2

obs_hypparams = {'mu_0':np.zeros(obs_dim),
                'sigma_0':np.eye(obs_dim),
                'kappa_0':0.3,
                'nu_0':obs_dim+5}

dur_hypparams = {'alpha_0':2*30,
                 'beta_0':2}

true_obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in range(N)]
true_dur_distns = [pyhsmm.distributions.PoissonDuration(**dur_hypparams) for state in range(N)]

truemodel = pyhsmm.models.HSMM(alpha=6.,init_state_concentration=6.,
                               obs_distns=true_obs_distns,
                               dur_distns=true_dur_distns)

data, labels = truemodel.generate(T)

plt.figure()
truemodel.plot()
plt.gcf().suptitle('True HSMM')


# !!! get the changepoints !!!
# NOTE: usually these would be estimated by some external process; here I'm
# totally cheating and just getting them from the truth
temp = np.concatenate(((0,),truemodel.states_list[0].durations.cumsum()))
changepoints = zip(temp[:-1],temp[1:])
changepoints[-1] = (changepoints[-1][0],T) # because last duration might be censored
print 'segments:'
print changepoints

#########################
#  posterior inference  #
#########################

Nmax = 25

obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in xrange(Nmax)]
dur_distns = [pyhsmm.distributions.PoissonDuration(**dur_hypparams) for state in xrange(Nmax)]

posteriormodel = pyhsmm.models.HSMMPossibleChangepoints(alpha=6.,init_state_concentration=6.,
        obs_distns=obs_distns,dur_distns=dur_distns)
posteriormodel.add_data(data,changepoints,trunc=70)

for idx in progprint_xrange(100):
    posteriormodel.resample_model()

plt.figure()
posteriormodel.plot()
plt.gcf().suptitle('HDP-HSMM sampled after 100 iterations')

plt.show()

########NEW FILE########
__FILENAME__ = hsmm
from __future__ import division
import numpy as np
np.seterr(divide='ignore') # these warnings are usually harmless for this code
from matplotlib import pyplot as plt
import copy, os

import pyhsmm
from pyhsmm.util.text import progprint_xrange

SAVE_FIGURES = False

print \
'''
This demo shows the HDP-HSMM in action. Its iterations are slower than those for
the (Sticky-)HDP-HMM, but explicit duration modeling can be a big advantage for
conditioning the prior or for discovering structure in data.
'''

###############
#  load data  #
###############

T = 1000
data = np.loadtxt(os.path.join(os.path.dirname(__file__),'example-data.txt'))[:T]

#########################
#  posterior inference  #
#########################

# Set the weak limit truncation level
Nmax = 25

# and some hyperparameters
obs_dim = data.shape[1]
obs_hypparams = {'mu_0':np.zeros(obs_dim),
                'sigma_0':np.eye(obs_dim),
                'kappa_0':0.25,
                'nu_0':obs_dim+2}
dur_hypparams = {'alpha_0':2*30,
                 'beta_0':2}

obs_distns = [pyhsmm.distributions.Gaussian(**obs_hypparams) for state in range(Nmax)]
dur_distns = [pyhsmm.distributions.PoissonDuration(**dur_hypparams) for state in range(Nmax)]

posteriormodel = pyhsmm.models.WeakLimitHDPHSMM(
        alpha=6.,gamma=6., # these can matter; see concentration-resampling.py
        init_state_concentration=6., # pretty inconsequential
        obs_distns=obs_distns,
        dur_distns=dur_distns)
posteriormodel.add_data(data,trunc=60) # duration truncation speeds things up when it's possible

models = []
for idx in progprint_xrange(150):
    posteriormodel.resample_model()
    if (idx+1) % 10 == 0:
        models.append(copy.deepcopy(posteriormodel))

fig = plt.figure()
for idx, model in enumerate(models):
    plt.clf()
    model.plot()
    plt.gcf().suptitle('HDP-HSMM sampled after %d iterations' % (10*(idx+1)))
    if SAVE_FIGURES:
        plt.savefig('iter_%.3d.png' % (10*(idx+1)))

plt.show()

########NEW FILE########
__FILENAME__ = meanfield
from __future__ import division
import numpy as np
from matplotlib import pyplot as plt

from pyhsmm import models, distributions

np.seterr(invalid='raise')
obs_hypparams = dict(mu_0=np.zeros(2),sigma_0=np.eye(2),kappa_0=0.05,nu_0=5)

### generate data

num_modes = 3

true_obs_distns = [distributions.Gaussian(**obs_hypparams) for i in range(num_modes)]
data = np.concatenate([true_obs_distns[i % num_modes].rvs(25) for i in range(25)])

## inference!

hmm = models.HMM(
        obs_distns=[distributions.Gaussian(**obs_hypparams) for i in range(num_modes*3)],
        alpha=3.,init_state_concentration=1.)
hmm.add_data(data)
hmm.meanfield_coordinate_descent_step()
scores = [hmm.meanfield_coordinate_descent_step() for i in range(50)]
scores = np.array(scores)

plt.figure()
hmm.plot()

plt.figure()
plt.plot(scores)

def normalize(A):
    return A / A.sum(1)[:,None]
plt.matshow(normalize(hmm.trans_distn.exp_expected_log_trans_matrix))

plt.show()

########NEW FILE########
__FILENAME__ = svi
from __future__ import division
import numpy as np
from numpy import newaxis as na
from matplotlib import pyplot as plt
from os.path import join, dirname, isfile

from pyhsmm import models, distributions
from pyhsmm.util.general import sgd_onepass, hold_out, get_file
from pyhsmm.util.text import progprint_xrange, progprint

np.random.seed(0)
datapath = str(join(dirname(__file__),'svi_data.gz'))

### load data

if not isfile(datapath):
    print 'download svi_data.gz data and put it in examples/'
    print 'https://github.com/mattjj/example_data'
    import sys; sys.exit(1)

print 'loading data...'
alldata = np.loadtxt(datapath)
allseqs = np.array_split(alldata,250)
datas, heldout = hold_out(allseqs,0.05)
training_size = sum(data.shape[0] for data in datas)
print '...done!'

print '%d total frames' % sum(data.shape[0] for data in alldata)
print 'split into %d training and %d test sequences' % (len(datas),len(heldout))

### inference!

Nmax = 20
obs_hypparams = dict(mu_0=np.zeros(2),sigma_0=np.eye(2),kappa_0=0.2,nu_0=5)

hmm = models.HMM(
        obs_distns=[distributions.Gaussian(**obs_hypparams) for i in range(Nmax)],
        alpha=10.,init_state_concentration=1.)

scores = []
sgdseq = sgd_onepass(tau=0,kappa=0.7,datalist=datas)
for t, (data, rho_t) in progprint(enumerate(sgdseq)):
    hmm.meanfield_sgdstep(data, data.shape[0] / training_size, rho_t)

    if t % 10 == 0:
        scores.append(hmm.log_likelihood(heldout))

plt.figure()
plt.plot(scores)

plt.show()


########NEW FILE########
__FILENAME__ = hmm_states
from __future__ import division
import numpy as np
from numpy import newaxis as na
from numpy.random import random
import abc, copy, warnings

from ..util.stats import sample_discrete, sample_discrete_from_log, sample_markov
from ..util.general import rle, top_eigenvector, rcumsum, cumsum
from ..util.profiling import line_profiled
PROFILING = False

class _StatesBase(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self,model,T=None,data=None,stateseq=None,
            initialize_from_prior=True,**kwargs):
        self.model = model

        self.T = T if T is not None else data.shape[0]
        self.data = data

        self.clear_caches()

        if stateseq is not None:
            self.stateseq = np.array(stateseq,dtype=np.int32)
        else:
            if data is not None and not initialize_from_prior:
                self.resample(**kwargs)
            else:
                self.generate_states()

    def copy_sample(self,newmodel):
        new = copy.copy(self)
        new.clear_caches() # saves space, though may recompute later for likelihoods
        new.model = newmodel
        new.stateseq = self.stateseq.copy()
        return new

    ### model properties

    @property
    def obs_distns(self):
        return self.model.obs_distns

    @property
    def trans_matrix(self):
        return self.model.trans_distn.trans_matrix

    @property
    def pi_0(self):
        return self.model.init_state_distn.pi_0

    @property
    def num_states(self):
        return self.model.num_states

    ### generation

    def generate(self):
        self.generate_states()
        return self.generate_obs()

    @abc.abstractmethod
    def generate_states(self):
        pass

    def generate_obs(self):
        counts = np.bincount(self.stateseq,minlength=self.num_states)
        obs = [iter(o.rvs(count)) for o, count in zip(self.obs_distns,counts)]
        self.data = np.vstack([obs[state].next() for state in self.stateseq])
        return self.data

    ### messages and likelihoods

    # some cached things depends on model parameters, so caches should be
    # cleared when the model changes (e.g. when parameters are updated)

    def clear_caches(self):
        self._aBl = self._mf_aBl = None
        self._normalizer = None

    @property
    def aBl(self):
        if self._aBl is None:
            data = self.data
            aBl = self._aBl = np.empty((data.shape[0],self.num_states))
            for idx, obs_distn in enumerate(self.obs_distns):
                aBl[:,idx] = np.nan_to_num(obs_distn.log_likelihood(data))
        return self._aBl

    @abc.abstractmethod
    def log_likelihood(self):
        pass


class HMMStatesPython(_StatesBase):
    ### generation

    def generate_states(self):
        T = self.T
        nextstate_distn = self.pi_0
        A = self.trans_matrix

        stateseq = np.zeros(T,dtype=np.int32)
        for idx in xrange(T):
            stateseq[idx] = sample_discrete(nextstate_distn)
            nextstate_distn = A[stateseq[idx]]

        self.stateseq = stateseq
        return stateseq

    ### message passing

    def log_likelihood(self):
        if self._normalizer is None:
            self.messages_forwards_normalized() # NOTE: sets self._normalizer
        return self._normalizer

    def _messages_log(self,trans_matrix,init_state_distn,log_likelihoods):
        alphal = self._messages_forwards_log(trans_matrix,init_state_distn,log_likelihoods)
        betal = self._messages_backwards_log(trans_matrix,log_likelihoods)
        return alphal, betal

    def messages_log(self):
        return self._messages_log(self.trans_matrix,self.pi_0,self.aBl)

    @staticmethod
    def _messages_backwards_log(trans_matrix,log_likelihoods):
        errs = np.seterr(over='ignore')
        Al = np.log(trans_matrix)
        aBl = log_likelihoods

        betal = np.zeros_like(aBl)

        for t in xrange(betal.shape[0]-2,-1,-1):
            np.logaddexp.reduce(Al + betal[t+1] + aBl[t+1],axis=1,out=betal[t])

        np.seterr(**errs)
        return betal

    def messages_backwards_log(self):
        betal = self._messages_backwards_log(self.trans_matrix,self.aBl)
        assert not np.isnan(betal).any()
        self._normalizer = np.logaddexp.reduce(np.log(self.pi_0) + betal[0] + self.aBl[0])
        return betal

    @staticmethod
    def _messages_forwards_log(trans_matrix,init_state_distn,log_likelihoods):
        errs = np.seterr(over='ignore')
        Al = np.log(trans_matrix)
        aBl = log_likelihoods

        alphal = np.zeros_like(aBl)

        alphal[0] = np.log(init_state_distn) + aBl[0]
        for t in xrange(alphal.shape[0]-1):
            alphal[t+1] = np.logaddexp.reduce(alphal[t] + Al.T,axis=1) + aBl[t+1]

        np.seterr(**errs)
        return alphal

    def messages_forwards_log(self):
        alphal = self._messages_forwards_log(self.trans_matrix,self.pi_0,self.aBl)
        assert not np.any(np.isnan(alphal))
        self._normalizer = np.logaddexp.reduce(alphal[-1])
        return alphal

    @staticmethod
    def _messages_backwards_normalized(trans_matrix,init_state_distn,log_likelihoods):
        aBl = log_likelihoods
        A = trans_matrix
        T = aBl.shape[0]

        betan = np.empty_like(aBl)
        logtot = 0.

        betan[-1] = 1.
        for t in xrange(T-2,-1,-1):
            cmax = aBl[t+1].max()
            betan[t] = A.dot(betan[t+1] * np.exp(aBl[t+1] - cmax))
            norm = betan[t].sum()
            logtot += cmax + np.log(norm)
            betan[t] /= norm

        cmax = aBl[0].max()
        logtot += cmax + np.log((np.exp(aBl[0] - cmax) * init_state_distn * betan[0]).sum())

        return betan, logtot

    def messages_backwards_normalized(self):
        betan, self._normalizer = \
                self._messages_backwards_normalized(self.trans_matrix,self.pi_0,self.aBl)
        return betan

    @staticmethod
    def _messages_forwards_normalized(trans_matrix,init_state_distn,log_likelihoods):
        aBl = log_likelihoods
        A = trans_matrix
        T = aBl.shape[0]

        alphan = np.empty_like(aBl)
        logtot = 0.

        in_potential = init_state_distn
        for t in xrange(T):
            cmax = aBl[t].max()
            alphan[t] = in_potential * np.exp(aBl[t] - cmax)
            norm = alphan[t].sum()
            if norm != 0:
                alphan[t] /= norm
                logtot += np.log(norm) + cmax
            else:
                alphan[t:] = 0.
                return alphan, np.log(0.)
            in_potential = alphan[t].dot(A)

        return alphan, logtot

    def messages_forwards_normalized(self):
        alphan, self._normalizer = \
                self._messages_forwards_normalized(self.trans_matrix,self.pi_0,self.aBl)
        return alphan

    ### Gibbs sampling

    def resample_log(self,temp=None):
        self.temp = temp
        betal = self.messages_backwards_log()
        self.sample_forwards_log(betal)

    def resample_normalized(self,temp=None):
        self.temp = temp
        alphan = self.messages_forwards_normalized()
        self.sample_backwards_normalized(alphan)

    def resample(self,temp=None):
        return self.resample_normalized(temp=temp)

    @staticmethod
    def _sample_forwards_log(betal,trans_matrix,init_state_distn,log_likelihoods):
        A = trans_matrix
        aBl = log_likelihoods
        T = aBl.shape[0]

        stateseq = np.empty(T,dtype=np.int32)

        nextstate_unsmoothed = init_state_distn
        for idx in xrange(T):
            logdomain = betal[idx] + aBl[idx]
            logdomain[nextstate_unsmoothed == 0] = -np.inf
            if np.any(np.isfinite(logdomain)):
                stateseq[idx] = sample_discrete(nextstate_unsmoothed * np.exp(logdomain - np.amax(logdomain)))
            else:
                stateseq[idx] = sample_discrete(nextstate_unsmoothed)
            nextstate_unsmoothed = A[stateseq[idx]]

        return stateseq

    def sample_forwards_log(self,betal):
        self.stateseq = self._sample_forwards_log(betal,self.trans_matrix,self.pi_0,self.aBl)

    @staticmethod
    def _sample_forwards_normalized(betan,trans_matrix,init_state_distn,log_likelihoods):
        A = trans_matrix
        aBl = log_likelihoods
        T = aBl.shape[0]

        stateseq = np.empty(T,dtype=np.int32)

        nextstate_unsmoothed = init_state_distn
        for idx in xrange(T):
            logdomain = aBl[idx]
            logdomain[nextstate_unsmoothed == 0] = -np.inf
            stateseq[idx] = sample_discrete(nextstate_unsmoothed * betan * np.exp(logdomain - np.amax(logdomain)))
            nextstate_unsmoothed = A[stateseq[idx]]

        return stateseq

    def sample_forwards_normalized(self,betan):
        self.stateseq = self._sample_forwards_normalized(
                betan,self.trans_matrix,self.pi_0,self.aBl)

    @staticmethod
    def _sample_backwards_normalized(alphan,trans_matrix_transpose):
        AT = trans_matrix_transpose
        T = alphan.shape[0]

        stateseq = np.empty(T,dtype=np.int32)

        next_potential = np.ones(AT.shape[0])
        for t in xrange(T-1,-1,-1):
            stateseq[t] = sample_discrete(next_potential * alphan[t])
            next_potential = AT[stateseq[t]]

        return stateseq

    def sample_backwards_normalized(self,alphan):
        self.stateseq = self._sample_backwards_normalized(alphan,self.trans_matrix.T.copy())

    ### Mean Field

    @property
    def mf_aBl(self):
        if self._mf_aBl is None:
            self._mf_aBl = aBl = np.empty((self.data.shape[0],self.num_states))
            for idx, o in enumerate(self.obs_distns):
                aBl[:,idx] = o.expected_log_likelihood(self.data)
            np.maximum(self._mf_aBl,-100000,out=self._mf_aBl)
        return self._mf_aBl

    @property
    def mf_trans_matrix(self):
        return np.maximum(self.model.trans_distn.exp_expected_log_trans_matrix,1e-3)

    @property
    def mf_pi_0(self):
        return self.model.init_state_distn.exp_expected_log_init_state_distn

    @property
    def all_expected_stats(self):
        return self.expected_states, self.expected_transcounts, self._normalizer

    @all_expected_stats.setter
    def all_expected_stats(self,vals):
        self.expected_states, self.expected_transcounts, self._normalizer = vals

    def meanfieldupdate(self):
        self.clear_caches()
        self.all_expected_stats = self._expected_statistics(
                self.mf_trans_matrix,self.mf_pi_0,self.mf_aBl)
        self.stateseq = self.expected_states.argmax(1) # for plotting

    def get_vlb(self):
        if self._normalizer is None:
            self.meanfieldupdate() # NOTE: sets self._normalizer
        return self._normalizer

    def _expected_statistics(self,trans_potential,init_potential,likelihood_log_potential):
        alphal = self._messages_forwards_log(trans_potential,init_potential,
                likelihood_log_potential)
        betal = self._messages_backwards_log(trans_potential,likelihood_log_potential)
        expected_states, expected_transcounts, normalizer = \
                self._expected_statistics_from_messages(trans_potential,likelihood_log_potential,alphal,betal)
        assert not np.isinf(expected_states).any()
        return expected_states, expected_transcounts, normalizer

    @staticmethod
    def _expected_statistics_from_messages(trans_potential,likelihood_log_potential,alphal,betal):
        expected_states = alphal + betal
        expected_states -= expected_states.max(1)[:,na]
        np.exp(expected_states,out=expected_states)
        expected_states /= expected_states.sum(1)[:,na]

        Al = np.log(trans_potential)
        log_joints = alphal[:-1,:,na] + (betal[1:,na,:] + likelihood_log_potential[1:,na,:]) + Al[na,...]
        log_joints -= log_joints.max((1,2))[:,na,na]
        joints = np.exp(log_joints)
        joints /= joints.sum((1,2))[:,na,na] # NOTE: renormalizing each isnt really necessary
        expected_transcounts = joints.sum(0)

        normalizer = np.logaddexp.reduce(alphal[0] + betal[0])

        return expected_states, expected_transcounts, normalizer

    ### EM

    def E_step(self):
        self.clear_caches()
        self.expected_states, self.expected_transcounts, self._normalizer \
                = self._expected_statistics(self.trans_matrix,self.pi_0,self.aBl)
        self.stateseq = self.expected_states.argmax(1) # for plotting

    ### Viterbi

    def Viterbi(self):
        scores, args = self.maxsum_messages_backwards()
        self.maximize_forwards(scores,args)

    def maxsum_messages_backwards(self):
        return self._maxsum_messages_backwards(self.trans_matrix,self.aBl)

    def maximize_forwards(self,scores,args):
        self.stateseq = self._maximize_forwards(scores,args,self.pi_0,self.aBl)


    def mf_Viterbi(self):
        scores, args = self.mf_maxsum_messages_backwards()
        self.mf_maximize_forwards(scores,args)

    def mf_maxsum_messages_backwards(self):
        return self._maxsum_messages_backwards(self.mf_trans_matrix,self.mf_aBl)

    def mf_maximize_forwards(self,scores,args):
        self.stateseq = self._maximize_forwards(scores,args,self.mf_pi_0,self.mf_aBl)


    @staticmethod
    def _maxsum_messages_backwards(trans_matrix, log_likelihoods):
        errs = np.seterr(divide='ignore')
        Al = np.log(trans_matrix)
        np.seterr(**errs)
        aBl = log_likelihoods

        scores = np.zeros_like(aBl)
        args = np.zeros(aBl.shape,dtype=np.int32)

        for t in xrange(scores.shape[0]-2,-1,-1):
            vals = Al + scores[t+1] + aBl[t+1]
            vals.argmax(axis=1,out=args[t+1])
            vals.max(axis=1,out=scores[t])

        return scores, args

    @staticmethod
    def _maximize_forwards(scores,args,init_state_distn,log_likelihoods):
        aBl = log_likelihoods
        T = aBl.shape[0]

        stateseq = np.empty(T,dtype=np.int32)

        stateseq[0] = (scores[0] + np.log(init_state_distn) + aBl[0]).argmax()
        for idx in xrange(1,T):
            stateseq[idx] = args[idx,stateseq[idx-1]]

        return stateseq

    ### plotting

    def plot(self,colors_dict=None,vertical_extent=(0,1),**kwargs):
        from matplotlib import pyplot as plt
        states,durations = rle(self.stateseq)
        X,Y = np.meshgrid(np.hstack((0,durations.cumsum())),vertical_extent)

        if colors_dict is not None:
            C = np.array([[colors_dict[state] for state in states]])
        else:
            C = states[na,:]

        plt.pcolor(X,Y,C,vmin=0,vmax=1,**kwargs)
        plt.ylim(vertical_extent)
        plt.xlim((0,durations.sum()))
        plt.yticks([])

class HMMStatesEigen(HMMStatesPython):
    def generate_states(self):
        self.stateseq = sample_markov(
                T=self.T,
                trans_matrix=self.trans_matrix,
                init_state_distn=self.pi_0)

    ### common messages (Gibbs, EM, likelihood calculation)

    @staticmethod
    def _messages_backwards_log(trans_matrix,log_likelihoods):
        from hmm_messages_interface import messages_backwards_log
        return messages_backwards_log(
                trans_matrix,log_likelihoods,
                np.empty_like(log_likelihoods))

    @staticmethod
    def _messages_forwards_log(trans_matrix,init_state_distn,log_likelihoods):
        from hmm_messages_interface import messages_forwards_log
        return messages_forwards_log(trans_matrix,log_likelihoods,
                init_state_distn,np.empty_like(log_likelihoods))

    @staticmethod
    def _messages_forwards_normalized(trans_matrix,init_state_distn,log_likelihoods):
        from hmm_messages_interface import messages_forwards_normalized
        return messages_forwards_normalized(trans_matrix,log_likelihoods,
                init_state_distn,np.empty_like(log_likelihoods))

    # next three methods are just for convenient testing

    def messages_backwards_log_python(self):
        return super(HMMStatesEigen,self)._messages_backwards_log(
                self.trans_matrix,self.aBl)

    def messages_forwards_log_python(self):
        return super(HMMStatesEigen,self)._messages_forwards_log(
                self.trans_matrix,self.pi_0,self.aBl)

    def messages_forwards_normalized_python(self):
        return super(HMMStatesEigen,self)._messages_forwards_normalized(
                self.trans_matrix,self.pi_0,self.aBl)

    ### sampling

    @staticmethod
    def _sample_forwards_log(betal,trans_matrix,init_state_distn,log_likelihoods):
        from hmm_messages_interface import sample_forwards_log
        return sample_forwards_log(trans_matrix,log_likelihoods,
                init_state_distn,betal,np.empty(log_likelihoods.shape[0],dtype='int32'))

    @staticmethod
    def _sample_backwards_normalized(alphan,trans_matrix_transpose):
        from hmm_messages_interface import sample_backwards_normalized
        return sample_backwards_normalized(trans_matrix_transpose,alphan,
                np.empty(alphan.shape[0],dtype='int32'))

    @staticmethod
    def _resample_multiple(states_list):
        from hmm_messages_interface import resample_normalized_multiple
        if len(states_list) > 0:
            loglikes = resample_normalized_multiple(
                    states_list[0].trans_matrix,states_list[0].pi_0,
                    [s.aBl for s in states_list],[s.stateseq for s in states_list])
            for s, loglike in zip(states_list,loglikes):
                s._normalizer = loglike

    ### EM

    @staticmethod
    def _expected_statistics_from_messages(
            trans_potential,likelihood_log_potential,alphal,betal,
            expected_states=None,expected_transcounts=None):
        from hmm_messages_interface import expected_statistics_log
        expected_states = np.zeros_like(alphal) \
                if expected_states is None else expected_states
        expected_transcounts = np.zeros_like(trans_potential) \
                if expected_transcounts is None else expected_transcounts
        return expected_statistics_log(
                np.log(trans_potential),likelihood_log_potential,alphal,betal,
                expected_states,expected_transcounts)

    ### Vitberbi

    def Viterbi(self):
        from hmm_messages_interface import viterbi
        self.stateseq = viterbi(self.trans_matrix,self.aBl,self.pi_0,
                np.empty(self.aBl.shape[0],dtype='int32'))


########NEW FILE########
__FILENAME__ = hsmm_inb_states
from __future__ import division
import numpy as np
from numpy import newaxis as na
from numpy.random import random
import abc, copy, warnings
import scipy.stats as stats
import scipy.special as special

np.seterr(invalid='raise')

from ..util.stats import sample_discrete, sample_discrete_from_log, sample_markov
from ..util.general import rle, top_eigenvector, cumsum
from ..util.profiling import line_profiled
PROFILING = False

from hmm_states import HMMStatesPython, HMMStatesEigen
from hsmm_states import HSMMStatesPython, HSMMStatesEigen


class _HSMMStatesIntegerNegativeBinomialBase(HSMMStatesEigen, HMMStatesEigen):
    __metaclass__ = abc.ABCMeta

    @property
    def rs(self):
        return np.array([d.r for d in self.dur_distns])

    @property
    def ps(self):
        return np.array([d.p for d in self.dur_distns])

    ### HMM embedding parameters

    @abc.abstractproperty
    def hmm_fwd_trans_matrix(self):
        pass

    @abc.abstractproperty
    def hmm_bwd_trans_matrix(self):
        pass

    @property
    def hmm_aBl(self):
        if self._hmm_aBl is None:
            self._hmm_aBl = self.aBl.repeat(self.rs,axis=1)
        return self._hmm_aBl

    @property
    def hmm_pi_0(self):
        rs = self.rs
        starts = np.concatenate(((0,),rs.cumsum()[:-1]))
        pi_0 = np.zeros(rs.sum())
        pi_0[starts] = self.pi_0
        return pi_0

    @property
    def hmm_fwd_pi_0(self):
        if not self.left_censoring:
            return self.hmm_pi_0
        else:
            return top_eigenvector(self.hmm_fwd_trans_matrix)

    @property
    def hmm_bwd_pi_0(self):
        if not self.left_censoring:
            return self.hmm_pi_0
        else:
            return top_eigenvector(self.hmm_bwd_trans_matrix)

    def clear_caches(self):
        super(_HSMMStatesIntegerNegativeBinomialBase,self).clear_caches()
        self._hmm_aBl = None


    def hmm_messages_backwards(self):
        betal = HMMStatesEigen._messages_backwards_log(
                self.hmm_bwd_trans_matrix,
                self.hmm_aBl)
        self._normalizer = np.logaddexp.reduce(
                np.log(self.hmm_bwd_pi_0) + betal[0] + self.hmm_aBl[0])
        return betal

    def hmm_messages_forwards(self):
        alphal = HMMStatesEigen._messages_forwards_log(
                self.hmm_fwd_trans_matrix,
                self.hmm_fwd_pi_0,
                self.hmm_aBl)
        self._normalier = np.logaddexp.reduce(alphal[-1])
        return alphal


    def _map_states(self):
        themap = np.arange(self.num_states).repeat(self.rs)
        self.stateseq = themap[self.stateseq]

    def generate_states(self):
        self.stateseq = sample_markov(
                T=self.T,
                trans_matrix=self.hmm_bwd_trans_matrix,
                init_state_distn=self.hmm_bwd_pi_0)
        self._map_states()

    def Viterbi_hmm(self):
        scores, args = HMMStatesEigen._maxsum_messages_backwards(
                self.hmm_bwd_trans_matrix,self.hmm_aBl)
        self.stateseq = HMMStatesEigen._maximize_forwards(scores,args)
        self._map_states()

    def resample_hmm(self):
        betal = HMMStatesEigen._messages_backwards_log(
                self.hmm_bwd_trans_matrix,self.hmm_aBl)
        self.stateseq = HMMStatesEigen._sample_forwards_log(
                betal,self.hmm_bwd_trans_matrix,self.hmm_bwd_pi_0,self.hmm_aBl)
        self._map_states()

    def resample_hsmm(self):
        betal, betastarl = HSMMStatesEigen.messages_backwards(self)
        HMMStatesEigen.sample_forwards(betal,betastarl)

    ### TODO TEMP

    def resample(self):
        self.resample_hmm()


class HSMMStatesIntegerNegativeBinomial(_HSMMStatesIntegerNegativeBinomialBase):
    @property
    def hmm_bwd_trans_matrix(self):
        rs, ps = self.rs, self.ps
        starts, ends = cumsum(rs,strict=True), cumsum(rs,strict=False)
        trans_matrix = np.zeros((ends[-1],ends[-1]))

        enters = self.bwd_enter_rows
        for (i,j), Aij in np.ndenumerate(self.trans_matrix):
            block = trans_matrix[starts[i]:ends[i],starts[j]:ends[j]]
            block[-1,:] = Aij * (1-ps[i]) * enters[j]
            if i == j:
                block[...] += np.diag(np.repeat(ps[i],rs[i])) \
                        + np.diag(np.repeat(1-ps[i],rs[i]-1),k=1)

        assert np.allclose(trans_matrix.sum(1),1)
        return trans_matrix

    @property
    def bwd_enter_rows(self):
        return [stats.binom.pmf(np.arange(r)[::-1],r-1,p) for r,p in zip(self.rs,self.ps)]

    @property
    def hmm_fwd_trans_matrix(self):
        rs, ps = self.rs, self.ps
        starts, ends = cumsum(rs,strict=True), cumsum(rs,strict=False)
        trans_matrix = np.zeros((ends[-1],ends[-1]))

        exits = self.fwd_exit_cols
        for (i,j), Aij in np.ndenumerate(self.trans_matrix):
            block = trans_matrix[starts[i]:ends[i],starts[j]:ends[j]]
            block[:,0] = Aij * exits[i] * (1-ps[i])
            if i == j:
                block[...] += \
                        np.diag(np.repeat(ps[i],rs[i])) \
                        + np.diag(np.repeat(1-ps[i],rs[i]-1) * (1-exits[i][:-1]),k=1)

        assert np.allclose(trans_matrix.sum(1),1)
        assert (0 <= trans_matrix).all() and (trans_matrix <= 1.).all()
        return trans_matrix

    @property
    def fwd_exit_cols(self):
        return [(1-p)**(np.arange(r)[::-1]) for r,p in zip(self.rs,self.ps)]

    def messages_backwards2(self):
        # this method is just for numerical testing
        # returns HSMM messages using HMM embedding. the way of the future!
        Al = np.log(self.trans_matrix)
        T, num_states = self.T, self.num_states

        betal = np.zeros((T,num_states))
        betastarl = np.zeros((T,num_states))

        starts = cumsum(self.rs,strict=True)
        ends = cumsum(self.rs,strict=False)
        foo = np.zeros((num_states,ends[-1]))
        for idx, row in enumerate(self.bwd_enter_rows):
            foo[idx,starts[idx]:ends[idx]] = row
        bar = np.zeros_like(self.hmm_bwd_trans_matrix)
        for start, end in zip(starts,ends):
            bar[start:end,start:end] = self.hmm_bwd_trans_matrix[start:end,start:end]

        pmess = np.zeros(ends[-1])

        # betal[-1] is 0
        for t in xrange(T-1,-1,-1):
            pmess += self.hmm_aBl[t]
            betastarl[t] = np.logaddexp.reduce(np.log(foo) + pmess, axis=1)
            betal[t-1] = np.logaddexp.reduce(Al + betastarl[t], axis=1)

            pmess = np.logaddexp.reduce(np.log(bar) + pmess, axis=1)
            pmess[ends-1] = np.logaddexp(pmess[ends-1],betal[t-1] + np.log(1-self.ps))
        betal[-1] = 0.

        return betal, betastarl

    ### NEW

    def meanfieldupdate(self):
        return self.meanfieldupdate_sampling()
        # return self.meanfieldupdate_Estep()

    def meanfieldupdate_sampling(self):
        from ..util.general import count_transitions
        num_r_samples = self.model.mf_num_samples \
                if hasattr(self.model,'mf_num_samples') else 10

        self.expected_states = np.zeros((self.T,self.num_states))
        self.expected_transcounts = np.zeros((self.num_states,self.num_states))
        self.expected_durations = np.zeros((self.num_states,self.T))

        eye = np.eye(self.num_states)/num_r_samples
        for i in xrange(num_r_samples):
            self.model._resample_from_mf()
            self.clear_caches()

            self.resample()

            self.expected_states += eye[self.stateseq]
            self.expected_transcounts += \
                count_transitions(self.stateseq_norep,minlength=self.num_states)\
                /num_r_samples
            for state in xrange(self.num_states):
                self.expected_durations[state] += \
                    np.bincount(
                            self.durations_censored[self.stateseq_norep == state],
                            minlength=self.T)[:self.T].astype(np.double)/num_r_samples

    def meanfieldupdate_Estep(self):
        # TODO bug in here? it's not as good as sampling
        num_r_samples = self.model.mf_num_samples \
                if hasattr(self.model,'mf_num_samples') else 10
        num_stateseq_samples_per_r = self.model.mf_num_stateseq_samples_per_r \
                if hasattr(self.model,'mf_num_stateseq_samples_per_r') else 1

        self.expected_states = np.zeros((self.T,self.num_states))
        self.expected_transcounts = np.zeros((self.num_states,self.num_states))
        self.expected_durations = np.zeros((self.num_states,self.T))

        mf_aBl = self.mf_aBl

        for i in xrange(num_r_samples):
            for d in self.dur_distns:
                d._resample_r_from_mf()
            self.clear_caches()

            trans = self.mf_bwd_trans_matrix # TODO check this
            init = self.hmm_mf_bwd_pi_0
            aBl = mf_aBl.repeat(self.rs,axis=1)

            hmm_alphal, hmm_betal = HMMStatesEigen._messages_log(self,trans,init,aBl)

            # collect stateseq and transitions statistics from messages
            hmm_expected_states, hmm_expected_transcounts, normalizer = \
                    HMMStatesPython._expected_statistics_from_messages(
                            trans,aBl,hmm_alphal,hmm_betal)
            expected_states, expected_transcounts, _ \
                    = self._hmm_stats_to_hsmm_stats(
                            hmm_expected_states, hmm_expected_transcounts, normalizer)

            self.expected_states += expected_states / num_r_samples
            self.expected_transcounts += expected_transcounts / num_r_samples

            # collect duration statistics by sampling from messages
            for j in xrange(num_stateseq_samples_per_r):
                self._resample_from_mf(trans,init,aBl,hmm_alphal,hmm_betal)
                for state in xrange(self.num_states):
                    self.expected_durations[state] += \
                        np.bincount(
                                self.durations_censored[self.stateseq_norep == state],
                                minlength=self.T)[:self.T].astype(np.double) \
                            /(num_r_samples*num_stateseq_samples_per_r)

    def _hmm_stats_to_hsmm_stats(self,hmm_expected_states,hmm_expected_transcounts,normalizer):
        rs = self.rs
        starts = np.concatenate(((0,),np.cumsum(rs[:-1])))
        dotter = np.zeros((rs.sum(),len(rs)))
        for idx, (start, length) in enumerate(zip(starts,rs)):
            dotter[start:start+length,idx] = 1.

        expected_states = hmm_expected_states.dot(dotter)
        expected_transcounts = dotter.T.dot(hmm_expected_transcounts).dot(dotter)
        expected_transcounts.flat[::expected_transcounts.shape[0]+1] = 0

        return expected_states, expected_transcounts, normalizer

    def _resample_from_mf(self,trans,init,aBl,hmm_alphal,hmm_betal):
        self.stateseq = HMMStatesEigen._sample_forwards_log(
                hmm_betal,trans,init,aBl)
        self._map_states()

    @property
    def hmm_mf_bwd_pi_0(self):
        rs = self.rs
        starts = np.concatenate(((0,),rs.cumsum()[:-1]))
        mf_pi_0 = np.zeros(rs.sum())
        mf_pi_0[starts] = self.mf_pi_0
        return mf_pi_0

    @property
    def mf_bwd_trans_matrix(self):
        # TODO i guess check each part of this...
        rs = self.rs
        starts, ends = cumsum(rs,strict=True), cumsum(rs,strict=False)
        trans_matrix = np.zeros((ends[-1],ends[-1]))

        Elnps, Eln1mps = zip(*[d._fixedr_distns[d.ridx]._mf_expected_statistics() for d in self.dur_distns])
        Eps, E1mps = np.exp(Elnps), np.exp(Eln1mps) # NOTE: technically exp(E[ln(p)]) etc

        enters = self.mf_bwd_enter_rows(rs,Eps,E1mps)
        for (i,j), Aij in np.ndenumerate(self.mf_trans_matrix):
            block = trans_matrix[starts[i]:ends[i],starts[j]:ends[j]]
            block[-1,:] = Aij * eE1mps[i] * enters[j]
            if i == j:
                block[...] += np.diag(np.repeat(eEps[i],rs[i])) \
                        + np.diag(np.repeat(eE1mps[i],rs[i]-1),k=1)

        assert np.all(trans_matrix >= 0)
        return trans_matrix

    def mf_bwd_enter_rows(self,rs,Elnps,Eln1mps):
        return [self._mf_binom(np.arange(r)[::-1],r-1,Ep,E1mp)
            for r,Ep,E1mp in zip(rs,Eps,E1mps)]

    @staticmethod
    def _mf_binom(k,n,p1,p2):
        return np.exp(special.gammaln(n+1) - special.gammaln(k+1) - special.gammaln(n-k+1) \
                + k*p1 + (n-k)*p2)


class HSMMStatesIntegerNegativeBinomialVariant(_HSMMStatesIntegerNegativeBinomialBase):
    @property
    def hmm_bwd_trans_matrix(self):
        rs, ps = self.rs, self.ps
        starts, ends = cumsum(rs,strict=True), cumsum(rs,strict=False)
        trans_matrix = np.zeros((rs.sum(),rs.sum()))

        for (i,j), Aij in np.ndenumerate(self.trans_matrix):
            block = trans_matrix[starts[i]:ends[i],starts[j]:ends[j]]
            block[-1,0] = Aij * (1-ps[i])
            if i == j:
                block[...] += np.diag(np.repeat(ps[i],rs[i])) \
                        + np.diag(np.repeat(1-ps[i],rs[i]-1),k=1)

        assert np.allclose(trans_matrix.sum(1),1)
        return trans_matrix

    @property
    def hmm_fwd_trans_matrix(self):
        return self.hmm_bwd_trans_matrix

    # TODO faster HSMM message computation exploiting the HMM embeddings


########NEW FILE########
__FILENAME__ = hsmm_states
from __future__ import division
import numpy as np
from numpy import newaxis as na
from numpy.random import random
from matplotlib import pyplot as plt
import abc, copy, warnings

from ..util.stats import sample_discrete, sample_discrete_from_log, sample_markov
from ..util.general import rle, top_eigenvector, rcumsum, cumsum
from ..util.profiling import line_profiled

PROFILING = False

from hmm_states import _StatesBase, HMMStatesPython, HMMStatesEigen

class HSMMStatesPython(_StatesBase):
    def __init__(self,model,right_censoring=True,left_censoring=False,trunc=None,
            stateseq=None,**kwargs):
        self.right_censoring = right_censoring
        self.left_censoring = left_censoring
        self.trunc = trunc

        super(HSMMStatesPython,self).__init__(model,stateseq=stateseq,**kwargs)

    ### properties for the outside world

    @property
    def stateseq(self):
        return self._stateseq

    @stateseq.setter
    def stateseq(self,stateseq):
        self._stateseq = stateseq
        self._stateseq_norep = None
        self._durations_censored = None

    @property
    def stateseq_norep(self):
        if self._stateseq_norep is None:
            self._stateseq_norep, self._durations_censored = rle(self.stateseq)
        return self._stateseq_norep

    @property
    def durations_censored(self):
        if self._durations_censored is None:
            self._stateseq_norep, self._durations_censored = rle(self.stateseq)
        return self._durations_censored

    @property
    def durations(self):
        durs = self.durations_censored.copy()
        if self.left_censoring:
            durs[0] = self.dur_distns[self.stateseq_norep[0]].rvs_given_greater_than(durs[0]-1)
        if self.right_censoring:
            durs[-1] = self.dur_distns[self.stateseq_norep[-1]].rvs_given_greater_than(durs[-1]-1)
        return durs

    @property
    def untrunc_slice(self):
        return slice(1 if self.left_censoring else 0, -1 if self.right_censoring else None)

    @property
    def trunc_slice(self):
        if self.left_censoring and self.right_censoring:
            return [0,-1] if len(self.stateseq_norep) > 1 else [0]
        elif self.left_censoring:
            return [0]
        elif self.right_censoring:
            return [1] if len(self.stateseq_norep) > 1 else [0]
        else:
            return []

    ### model parameter properties

    @property
    def pi_0(self):
        if not self.left_censoring:
            return self.model.init_state_distn.pi_0
        else:
            return self.model.left_censoring_init_state_distn.pi_0

    @property
    def dur_distns(self):
        return self.model.dur_distns

    @property
    def log_trans_matrix(self):
        if self._log_trans_matrix is None:
            self._log_trans_matrix = np.log(self.trans_matrix)
        return self._log_trans_matrix


    @property
    def mf_pi_0(self):
        return self.model.init_state_distn.exp_expected_log_init_state_distn

    @property
    def mf_log_trans_matrix(self):
        if self._mf_log_trans_matrix is None:
            self._mf_log_trans_matrix = np.log(self.mf_trans_matrix)
        return self._mf_log_trans_matrix

    @property
    def mf_trans_matrix(self):
        return np.maximum(self.model.trans_distn.exp_expected_log_trans_matrix,1e-3)

    ### generation

    # TODO rewrite this thing
    def generate_states(self):
        if self.left_censoring:
            raise NotImplementedError
        idx = 0
        nextstate_distr = self.pi_0
        A = self.trans_matrix

        stateseq = np.empty(self.T,dtype=np.int32)
        # durations = []

        while idx < self.T:
            # sample a state
            state = sample_discrete(nextstate_distr)
            # sample a duration for that state
            duration = self.dur_distns[state].rvs()
            # save everything
            # durations.append(duration)
            stateseq[idx:idx+duration] = state # this can run off the end, that's okay
            # set up next state distribution
            nextstate_distr = A[state,]
            # update index
            idx += duration

        self.stateseq = stateseq

    ### caching

    def clear_caches(self):
        self._aBl = self._mf_aBl = None
        self._aDl = self._mf_aDl = None
        self._aDsl = self._mf_aDsl = None
        self._log_trans_matrix = self._mf_log_trans_matrix = None
        self._normalizer = None
        super(HSMMStatesPython,self).clear_caches()

    ### array properties for homog model

    @property
    def aBl(self):
        if self._aBl is None:
            data = self.data
            aBl = self._aBl = np.empty((data.shape[0],self.num_states))
            for idx, obs_distn in enumerate(self.obs_distns):
                aBl[:,idx] = np.nan_to_num(obs_distn.log_likelihood(data))
        return self._aBl

    @property
    def aDl(self):
        if self._aDl is None:
            aDl = np.empty((self.T,self.num_states))
            possible_durations = np.arange(1,self.T + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDl[:,idx] = dur_distn.log_pmf(possible_durations)
            self._aDl = aDl
        return self._aDl

    @property
    def aDsl(self):
        if self._aDsl is None:
            aDsl = np.empty((self.T,self.num_states))
            possible_durations = np.arange(1,self.T + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDsl[:,idx] = dur_distn.log_sf(possible_durations)
            self._aDsl = aDsl
        return self._aDsl

    @property
    def mf_aBl(self):
        if self._mf_aBl is None:
            self._mf_aBl = aBl = np.empty((self.data.shape[0],self.num_states))
            for idx, o in enumerate(self.obs_distns):
                aBl[:,idx] = o.expected_log_likelihood(self.data)
        return self._mf_aBl

    @property
    def mf_aDl(self):
        if self._mf_aDl is None:
            self._mf_aDl = aDl = np.empty((self.T,self.num_states))
            possible_durations = np.arange(1,self.T + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDl[:,idx] = dur_distn.expected_log_pmf(possible_durations)
        return self._mf_aDl

    @property
    def mf_aDsl(self):
        if self._mf_aDsl is None:
            self._mf_aDsl = aDsl = np.empty((self.T,self.num_states))
            possible_durations = np.arange(1,self.T + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDsl[:,idx] = dur_distn.expected_log_sf(possible_durations)
        return self._mf_aDsl

    # @property
    # def betal(self):
    #     if self._betal is None:
    #         self._betal = np.empty((self.Tblock,self.num_states))
    #     return self._betal

    # @property
    # def betastarl(self):
    #     if self._betastarl is None:
    #         self._betastarl = np.empty((self.Tblock,self.num_states))
    #     return self._betastarl

    # @property
    # def alphal(self):
    #     if self._alphal is None:
    #         self._alphal = np.empty((self.Tblock,self.num_states))
    #     return self._alphal

    # @property
    # def alphastarl(self):
    #     if self._alphastarl is None:
    #         self._alphastarl = np.empty((self.Tblock,self.num_states))
    #     return self._alphastarl

    ### NEW message passing, with external pure functions

    def messages_forwards(self):
        alphal, alphastarl, _ = hsmm_messages_forwards_log(
                self.trans_potentials,
                np.log(self.pi_0),
                self.reverse_cumulative_obs_potentials,
                self.reverse_dur_potentials,
                self.reverse_dur_survival_potentials,
                np.empty((self.T,self.num_states)),np.empty((self.T,self.num_states)))
        return alphal, alphastarl

    def messages_backwards(self):
        betal, betastarl, loglike = hsmm_messages_backwards_log(
                self.trans_potentials,
                np.log(self.pi_0),
                self.cumulative_obs_potentials,
                self.dur_potentials,
                self.dur_survival_potentials,
                np.empty((self.T,self.num_states)),np.empty((self.T,self.num_states)))
        self._normalizer = loglike
        return betal, betastarl



    def log_likelihood(self):
        if self._normalizer is None:
            self.messages_backwards() # NOTE: sets self._normalizer
        return self._normalizer

    def get_vlb(self):
        if self._normalizer is None:
            self.meanfieldupdate() # a bit excessive...
        return self._normalizer

    # forwards messages potentials

    def trans_potentials(self,t):
        return self.log_trans_matrix

    def cumulative_obs_potentials(self,t):
        stop = None if self.trunc is None else min(self.T,t+self.trunc)
        return np.cumsum(self.aBl[t:stop],axis=0)

    def dur_potentials(self,t):
        stop = self.T-t if self.trunc is None else min(self.T-t,self.trunc)
        return self.aDl[:stop]

    def dur_survival_potentials(self,t):
        return self.aDsl[self.T-t -1] if (self.trunc is None or self.T-t > self.trunc) \
                else -np.inf

    # backwards messages potentials

    def reverse_cumulative_obs_potentials(self,t):
        start = 0 if self.trunc is None else max(0,t-self.trunc+1)
        return rcumsum(self.aBl[start:t+1])

    def reverse_dur_potentials(self,t):
        stop = t+1 if self.trunc is None else min(t+1,self.trunc)
        return self.aDl[:stop][::-1]

    def reverse_dur_survival_potentials(self,t):
        # NOTE: untested, unused without left-censoring
        return self.aDsl[t] if (self.trunc is None or t+1 < self.trunc) \
                else -np.inf

    # mean field messages potentials

    def mf_trans_potentials(self,t):
        return self.mf_log_trans_matrix

    def mf_cumulative_obs_potentials(self,t):
        stop = None if self.trunc is None else min(self.T,t+self.trunc)
        return np.cumsum(self.mf_aBl[t:stop],axis=0)

    def mf_reverse_cumulative_obs_potentials(self,t):
        start = 0 if self.trunc is None else max(0,t-self.trunc+1)
        return rcumsum(self.mf_aBl[start:t+1])

    def mf_dur_potentials(self,t):
        stop = self.T-t if self.trunc is None else min(self.T-t,self.trunc)
        return self.mf_aDl[:stop]

    def mf_reverse_dur_potentials(self,t):
        stop = t+1 if self.trunc is None else min(t+1,self.trunc)
        return self.mf_aDl[:stop][::-1]

    def mf_dur_survival_potentials(self,t):
        return self.mf_aDsl[self.T-t -1] if (self.trunc is None or self.T-t > self.trunc) \
                else -np.inf

    def mf_reverse_dur_survival_potentials(self,t):
        # NOTE: untested, unused without left-censoring
        return self.mf_aDsl[t] if (self.trunc is None or t+1 < self.trunc) \
                else -np.inf

    ### Gibbs sampling

    def resample(self):
        betal, betastarl = self.messages_backwards()
        self.sample_forwards(betal,betastarl)

    def copy_sample(self,newmodel):
        new = super(HSMMStatesPython,self).copy_sample(newmodel)
        return new

    def sample_forwards(self,betal,betastarl):
        self.stateseq, _ = hsmm_sample_forwards_log(
                self.trans_potentials,
                np.log(self.pi_0),
                self.cumulative_obs_potentials,
                self.dur_potentials,
                self.dur_survival_potentials,
                betal, betastarl)
        return self.stateseq

    ### Viterbi

    def Viterbi(self):
        self.stateseq = hsmm_maximizing_assignment(
            self.num_states, self.T,
            self.trans_potentials, np.log(self.pi_0),
            self.cumulative_obs_potentials,
            self.reverse_cumulative_obs_potentials,
            self.dur_potentials, self.dur_survival_potentials)

    def mf_Viterbi(self):
        self.stateseq = hsmm_maximizing_assignment(
            self.num_states, self.T,
            self.mf_trans_potentials, np.log(self.mf_pi_0),
            self.mf_cumulative_obs_potentials,
            self.mf_reverse_cumulative_obs_potentials,
            self.mf_dur_potentials, self.mf_dur_survival_potentials)

    ### EM

    # these two methods just call _expected_statistics with the right stuff

    def E_step(self):
        self.clear_caches()
        self.all_expected_stats = self._expected_statistics(
                self.trans_potentials, np.log(self.pi_0),
                self.cumulative_obs_potentials, self.reverse_cumulative_obs_potentials,
                self.dur_potentials, self.reverse_dur_potentials,
                self.dur_survival_potentials, self.reverse_dur_survival_potentials)
        self.stateseq = self.expected_states.argmax(1) # for plotting

    def meanfieldupdate(self):
        self.clear_caches()
        self.all_expected_stats = self._expected_statistics(
                self.mf_trans_potentials, np.log(self.mf_pi_0),
                self.mf_cumulative_obs_potentials, self.mf_reverse_cumulative_obs_potentials,
                self.mf_dur_potentials, self.mf_reverse_dur_potentials,
                self.mf_dur_survival_potentials, self.mf_reverse_dur_survival_potentials)
        self.stateseq = self.expected_states.argmax(1) # for plotting

    @property
    def all_expected_stats(self):
        return self.expected_states, self.expected_transcounts, \
                self.expected_durations, self._normalizer

    @all_expected_stats.setter
    def all_expected_stats(self,vals):
        self.expected_states, self.expected_transcounts, \
                self.expected_durations, self._normalizer = vals

    # here's the real work

    @line_profiled
    def _expected_statistics(self,
            trans_potentials, initial_state_potential,
            cumulative_obs_potentials, reverse_cumulative_obs_potentials,
            dur_potentials, reverse_dur_potentials,
            dur_survival_potentials, reverse_dur_survival_potentials):

        alphal, alphastarl, _ = hsmm_messages_forwards_log(
                trans_potentials,
                initial_state_potential,
                reverse_cumulative_obs_potentials,
                reverse_dur_potentials,
                reverse_dur_survival_potentials,
                np.empty((self.T,self.num_states)),np.empty((self.T,self.num_states)))

        betal, betastarl, normalizer = hsmm_messages_backwards_log(
                trans_potentials,
                initial_state_potential,
                cumulative_obs_potentials,
                dur_potentials,
                dur_survival_potentials,
                np.empty((self.T,self.num_states)),np.empty((self.T,self.num_states)))

        expected_states = self._expected_states(
                alphal, betal, alphastarl, betastarl, normalizer)

        expected_transitions = self._expected_transitions(
                alphal, betastarl, trans_potentials, normalizer) # TODO assumes homog trans

        expected_durations = self._expected_durations(
                dur_potentials,cumulative_obs_potentials,
                alphastarl, betal, normalizer)

        return expected_states, expected_transitions, expected_durations, normalizer

    def _expected_states(self,alphal,betal,alphastarl,betastarl,normalizer):
        gammal = alphal + betal
        gammastarl = alphastarl + betastarl
        gamma = np.exp(gammal - normalizer)
        gammastar = np.exp(gammastarl - normalizer)

        assert gamma.min() > 0.-1e-3 and gamma.max() < 1.+1e-3
        assert gammastar.min() > 0.-1e-3 and gammastar.max() < 1.+1e-3

        expected_states = \
            (gammastar - np.vstack((np.zeros(gamma.shape[1]),gamma[:-1]))).cumsum(0)

        assert not np.isnan(expected_states).any()
        assert expected_states.min() > 0.-1e-3 and expected_states.max() < 1 + 1e-3
        assert np.allclose(expected_states.sum(1),1.,atol=1e-2)

        expected_states = np.maximum(0.,expected_states)
        expected_states /= expected_states.sum(1)[:,na]

        # TODO break this out into a function
        self._changepoint_probs = gammastar.sum(1)

        return expected_states

    def _expected_transitions(self,alphal,betastarl,trans_potentials,normalizer):
        # TODO assumes homog trans; otherwise, need a loop
        Al = trans_potentials(0)
        transl = alphal[:-1,:,na] + betastarl[1:,na,:] + Al[na,...]
        transl -= normalizer
        expected_transcounts = np.exp(transl).sum(0)
        return expected_transcounts

    def _expected_durations(self,
            dur_potentials,cumulative_obs_potentials,
            alphastarl,betal,normalizer):
        if self.trunc is not None:
            raise NotImplementedError, "_expected_durations can't handle trunc"
        T = self.T
        logpmfs = -np.inf*np.ones_like(alphastarl)
        errs = np.seterr(invalid='ignore')
        for t in xrange(T):
            np.logaddexp(dur_potentials(t) + alphastarl[t] + betal[t:] +
                    cumulative_obs_potentials(t) - normalizer,
                    logpmfs[:T-t], out=logpmfs[:T-t])
        np.seterr(**errs)
        expected_durations = np.exp(logpmfs.T)

        return expected_durations


    ### plotting

    def plot(self,colors_dict=None,**kwargs):
        # TODO almost identical to HMM.plot, but with reference to
        # stateseq_norep
        from matplotlib import pyplot as plt
        X,Y = np.meshgrid(np.hstack((0,self.durations_censored.cumsum())),(0,1))

        if colors_dict is not None:
            C = np.array([[colors_dict[state] for state in self.stateseq_norep]])
        else:
            C = self.stateseq_norep[na,:]

        plt.pcolor(X,Y,C,vmin=0,vmax=1,**kwargs)
        plt.ylim((0,1))
        plt.xlim((0,self.T))
        plt.yticks([])
        plt.title('State Sequence')


# TODO call this 'time homog'
class HSMMStatesEigen(HSMMStatesPython):
    # NOTE: the methods in this class only work with iid emissions (i.e. without
    # overriding methods like cumulative_likelihood_block)

    def messages_backwards(self):
        # NOTE: np.maximum calls are because the C++ code doesn't do
        # np.logaddexp(-inf,-inf) = -inf, it likes nans instead
        from hsmm_messages_interface import messages_backwards_log
        betal, betastarl = messages_backwards_log(
                np.maximum(self.trans_matrix,1e-50),self.aBl,np.maximum(self.aDl,-1000000),
                self.aDsl,np.empty_like(self.aBl),np.empty_like(self.aBl),
                self.right_censoring,self.trunc if self.trunc is not None else self.T)
        assert not np.isnan(betal).any()
        assert not np.isnan(betastarl).any()

        if not self.left_censoring:
            self._normalizer = np.logaddexp.reduce(np.log(self.pi_0) + betastarl[0])
        else:
            raise NotImplementedError

        return betal, betastarl

    def messages_backwards_python(self):
        return super(HSMMStatesEigen,self).messages_backwards()

    def sample_forwards(self,betal,betastarl):
        from hsmm_messages_interface import sample_forwards_log
        if self.left_censoring:
            raise NotImplementedError
        caBl = np.vstack((np.zeros(betal.shape[1]),np.cumsum(self.aBl[:-1],axis=0)))
        self.stateseq = sample_forwards_log(
                self.trans_matrix,caBl,self.aDl,self.pi_0,betal,betastarl,
                np.empty(betal.shape[0],dtype='int32'))
        assert not (0 == self.stateseq).all()

    def sample_forwards_python(self,betal,betastarl):
        return super(HSMMStatesEigen,self).sample_forwards(betal,betastarl)

    @staticmethod
    def _resample_multiple(states_list):
        from hsmm_messages_interface import resample_log_multiple
        if len(states_list) > 0:
            Ts = [s.T for s in states_list]
            longest = np.argmax(Ts)
            stateseqs = [np.empty(T,dtype=np.int32) for T in Ts]
            loglikes = resample_log_multiple(
                    states_list[0].trans_matrix,
                    states_list[0].pi_0,
                    states_list[longest].aDl,
                    states_list[longest].aDsl,
                    [s.aBl for s in states_list],
                    np.array([s.right_censoring for s in states_list],dtype=np.int32),
                    np.array([s.trunc for s in states_list],dtype=np.int32),
                    stateseqs,
                    )
            for s, loglike, stateseq in zip(states_list,loglikes,stateseqs):
                s._normalizer = loglike
                s.stateseq = stateseq


class GeoHSMMStates(HSMMStatesPython):
    def resample(self):
        alphan, self._normalizer = HMMStatesEigen._messages_forwards_normalized(
                self.hmm_trans_matrix,
                self.pi_0,
                self.aBl)
        self.stateseq = HMMStatesEigen._sample_backwards_normalized(
                alphan,
                self.hmm_trans_matrix.T.copy())

    @property
    def hmm_trans_matrix(self):
        A = self.trans_matrix.copy()
        ps = np.array([d.p for d in self.dur_distns])

        A *= ps[:,na]
        A.flat[::A.shape[0]+1] = 1-ps
        assert np.allclose(1.,A.sum(1))

        return A


class HSMMStatesPossibleChangepoints(HSMMStatesPython):
    def __init__(self,model,data,changepoints,**kwargs):
        self.changepoints = changepoints
        self.segmentstarts = np.array([start for start,stop in changepoints],dtype=np.int32)
        self.segmentlens = np.array([stop-start for start,stop in changepoints],dtype=np.int32)

        assert all(l > 0 for l in self.segmentlens)
        assert sum(self.segmentlens) == data.shape[0]
        assert self.changepoints[0][0] == 0 and self.changepoints[-1][-1] == data.shape[0]

        super(HSMMStatesPossibleChangepoints,self).__init__(
                model,T=len(changepoints),data=data,**kwargs)

    def clear_caches(self):
        self._aBBl = self._mf_aBBl = None
        super(HSMMStatesPossibleChangepoints,self).clear_caches()

    ### properties for the outside world

    @property
    def stateseq(self):
        return self.blockstateseq.repeat(self.segmentlens)

    @stateseq.setter
    def stateseq(self,stateseq):
        self._stateseq_norep = None
        self._durations_censored = None

        assert len(stateseq) == self.Tblock or len(stateseq) == self.Tfull
        if len(stateseq) == self.Tblock:
            self.blockstateseq = stateseq
        else:
            self.blockstateseq = stateseq[self.segmentstarts]

    # @property
    # def stateseq_norep(self):
    #     if self._stateseq_norep is None:
    #         self._stateseq_norep, self._repeats_censored = rle(self.stateseq)
    #     self._durations_censored = self._repeats_censored.repeat(self.segmentlens)
    #     return self._stateseq_norep

    # @property
    # def durations_censored(self):
    #     if self._durations_censored is None:
    #         self._stateseq_norep, self._repeats_censored = rle(self.stateseq)
    #     self._durations_censored = self._repeats_censored.repeat(self.segmentlens)
    #     return self._durations_censored

    ### model parameter properties

    @property
    def Tblock(self):
        return len(self.changepoints)

    @property
    def Tfull(self):
        return self.data.shape[0]

    @property
    def aBBl(self):
        if self._aBBl is None:
            aBl = self.aBl
            aBBl = self._aBBl = np.empty((self.Tblock,self.num_states))
            for idx, (start,stop) in enumerate(self.changepoints):
                aBBl[idx] = aBl[start:stop].sum(0)
        return self._aBBl

    @property
    def mf_aBBl(self):
        if self._mf_aBBl is None:
            aBl = self.mf_aBl
            aBBl = self._mf_aBBl = np.empty((self.Tblock,self.num_states))
            for idx, (start,stop) in enumerate(self.changepoints):
                aBBl[idx] = aBl[start:stop].sum(0)
        return self._mf_aBBl

    # TODO reduce repetition with parent in next 4 props

    @property
    def aDl(self):
        # just like parent aDl, except we use Tfull
        if self._aDl is None:
            aDl = np.empty((self.Tfull,self.num_states))
            possible_durations = np.arange(1,self.Tfull + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDl[:,idx] = dur_distn.log_pmf(possible_durations)
            self._aDl = aDl
        return self._aDl

    @property
    def aDsl(self):
        # just like parent aDl, except we use Tfull
        if self._aDsl is None:
            aDsl = np.empty((self.Tfull,self.num_states))
            possible_durations = np.arange(1,self.Tfull + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDsl[:,idx] = dur_distn.log_sf(possible_durations)
            self._aDsl = aDsl
        return self._aDsl

    @property
    def mf_aDl(self):
        # just like parent aDl, except we use Tfull
        if self._aDl is None:
            aDl = np.empty((self.Tfull,self.num_states))
            possible_durations = np.arange(1,self.Tfull + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDl[:,idx] = dur_distn.expected_log_pmf(possible_durations)
            self._aDl = aDl
        return self._aDl

    @property
    def mf_aDsl(self):
        # just like parent aDl, except we use Tfull
        if self._aDsl is None:
            aDsl = np.empty((self.Tfull,self.num_states))
            possible_durations = np.arange(1,self.Tfull + 1,dtype=np.float64)
            for idx, dur_distn in enumerate(self.dur_distns):
                aDsl[:,idx] = dur_distn.expected_log_sf(possible_durations)
            self._aDsl = aDsl
        return self._aDsl

    # @property
    # def betal(self):
    #     if self._betal is None:
    #         self._betal = np.empty((self.Tblock,self.num_states))
    #     return self._betal

    # @property
    # def betastarl(self):
    #     if self._betastarl is None:
    #         self._betastarl = np.empty((self.Tblock,self.num_states))
    #     return self._betastarl

    # @property
    # def alphal(self):
    #     if self._alphal is None:
    #         self._alphal = np.empty((self.Tblock,self.num_states))
    #     return self._alphal

    # @property
    # def alphastarl(self):
    #     if self._alphastarl is None:
    #         self._alphastarl = np.empty((self.Tblock,self.num_states))
    #     return self._alphastarl

    ### message passing

    # TODO caching
    # TODO trunc

    # TODO wrap the duration stuff into single functions. reduces passing
    # around, reduces re-computation in this case

    # backwards messages potentials

    def cumulative_obs_potentials(self,tblock):
        return self.aBBl[tblock:].cumsum(0)[:self.trunc]

    def dur_potentials(self,tblock):
        possible_durations = self.segmentlens[tblock:].cumsum()[:self.trunc]
        return self.aDl[possible_durations -1]

    def dur_survival_potentials(self,tblock):
        # return -np.inf # for testing against other implementation
        max_dur = self.segmentlens[tblock:].cumsum()[:self.trunc][-1]
        return self.aDsl[max_dur -1]

    # forwards messages potentials

    def reverse_cumulative_obs_potentials(self,tblock):
        return rcumsum(self.aBBl[:tblock+1])\
                [-self.trunc if self.trunc is not None else None:]

    def reverse_dur_potentials(self,tblock):
        possible_durations = rcumsum(self.segmentlens[:tblock+1])\
                [-self.trunc if self.trunc is not None else None:]
        return self.aDl[possible_durations -1]

    def reverse_dur_survival_potentials(self,tblock):
        # NOTE: untested, unused
        max_dur = rcumsum(self.segmentlens[:tblock+1])\
                [-self.trunc if self.trunc is not None else None:][0]
        return self.aDsl[max_dur -1]

    # mean field messages potentials

    def mf_cumulative_obs_potentials(self,tblock):
        return self.mf_aBBl[tblock:].cumsum(0)[:self.trunc]

    def mf_reverse_cumulative_obs_potentials(self,tblock):
        return rcumsum(self.mf_aBBl[:tblock+1])\
                [-self.trunc if self.trunc is not None else None:]

    def mf_dur_potentials(self,tblock):
        possible_durations = self.segmentlens[tblock:].cumsum()[:self.trunc]
        return self.mf_aDl[possible_durations -1]

    def mf_reverse_dur_potentials(self,tblock):
        possible_durations = rcumsum(self.segmentlens[:tblock+1])\
                [-self.trunc if self.trunc is not None else None:]
        return self.mf_aDl[possible_durations -1]

    def mf_dur_survival_potentials(self,tblock):
        max_dur = self.segmentlens[tblock:].cumsum()[:self.trunc][-1]
        return self.mf_aDsl[max_dur -1]

    def mf_reverse_dur_survival_potentials(self,tblock):
        max_dur = rcumsum(self.segmentlens[:tblock+1])\
                [-self.trunc if self.trunc is not None else None:][0]
        return self.mf_aDsl[max_dur -1]


    ### generation

    def generate_states(self):
        if self.left_censoring:
            raise NotImplementedError
        Tblock = len(self.changepoints)
        blockstateseq = self.blockstateseq = np.zeros(Tblock,dtype=np.int32)

        tblock = 0
        nextstate_distr = self.pi_0
        A = self.trans_matrix

        while tblock < Tblock:
            # sample the state
            state = sample_discrete(nextstate_distr)

            # compute possible duration info (indep. of state)
            possible_durations = self.segmentlens[tblock:].cumsum()

            # compute the pmf over those steps
            durprobs = self.dur_distns[state].pmf(possible_durations)
            # TODO censoring: the last possible duration isn't quite right
            durprobs /= durprobs.sum()

            # sample it
            blockdur = sample_discrete(durprobs) + 1

            # set block sequence
            blockstateseq[tblock:tblock+blockdur] = state

            # set up next iteration
            tblock += blockdur
            nextstate_distr = A[state]

        self._stateseq_norep = None
        self._durations_censored = None

    def generate(self):
        raise NotImplementedError

    def plot(self,*args,**kwargs):
        super(HSMMStatesPossibleChangepoints,self).plot(*args,**kwargs)
        plt.xlim((0,self.Tfull))

    # TODO E step refactor
    # TODO trunc

    def _expected_states(self,*args,**kwargs):
        expected_states = super(HSMMStatesPossibleChangepoints,self)._expected_states(*args,**kwargs)
        return expected_states.repeat(self.segmentlens,axis=0)

    def _expected_durations(self,
            dur_potentials,cumulative_obs_potentials,
            alphastarl,betal,normalizer):
        logpmfs = -np.inf*np.ones((self.Tfull,alphastarl.shape[1]))
        errs = np.seterr(invalid='ignore') # logaddexp(-inf,-inf)
        # TODO censoring not handled correctly here
        for tblock in xrange(self.Tblock):
            possible_durations = self.segmentlens[tblock:].cumsum()[:self.trunc]
            logpmfs[possible_durations -1] = np.logaddexp(
                    dur_potentials(tblock) + alphastarl[tblock]
                    + betal[tblock:tblock+self.trunc if self.trunc is not None else None]
                    + cumulative_obs_potentials(tblock) - normalizer,
                    logpmfs[possible_durations -1])
        np.seterr(**errs)
        return np.exp(logpmfs.T)



# NOTE: this class is purely for testing HSMM messages
class _HSMMStatesEmbedding(HSMMStatesPython,HMMStatesPython):

    @property
    def hmm_aBl(self):
        return np.repeat(self.aBl,self.T,axis=1)

    @property
    def hmm_backwards_pi_0(self):
        if not self.left_censoring:
            aD = np.exp(self.aDl)
            aD[-1] = [np.exp(distn.log_sf(self.T-1)) for distn in self.dur_distns]
            assert np.allclose(aD.sum(0),1.)
            pi_0 = (self.pi_0 *  aD[::-1,:]).T.ravel()
            assert np.isclose(pi_0.sum(),1.)
            return pi_0
        else:
            raise NotImplementedError

    @property
    def hmm_backwards_trans_matrix(self):
        # TODO construct this as a csr
        blockcols = []
        aD = np.exp(self.aDl)
        aDs = np.array([np.exp(distn.log_sf(self.T-1)) for distn in self.dur_distns])
        for j in xrange(self.num_states):
            block = np.zeros((self.T,self.T))
            block[-1,0] = aDs[j]
            block[-1,1:] = aD[self.T-2::-1,j]
            blockcol = np.kron(self.trans_matrix[:,na,j],block)
            blockcol[j*self.T:(j+1)*self.T] = np.eye(self.T,k=1)
            blockcols.append(blockcol)
        return np.hstack(blockcols)

    @property
    def hmm_forwards_pi_0(self):
        if not self.left_censoring:
            out = np.zeros((self.num_states,self.T))
            out[:,0] = self.pi_0
            return out.ravel()
        else:
            raise NotImplementedError

    @property
    def hmm_forwards_trans_matrix(self):
        # TODO construct this as a csc
        blockrows = []
        aD = np.exp(self.aDl)
        aDs = np.hstack([np.exp(distn.log_sf(np.arange(self.T)))[:,na]
            for distn in self.dur_distns])
        for i in xrange(self.num_states):
            block = np.zeros((self.T,self.T))
            block[:,0] = aD[:self.T,i] / aDs[:self.T,i]
            blockrow = np.kron(self.trans_matrix[i],block)
            blockrow[:self.T,i*self.T:(i+1)*self.T] = \
                    np.diag(1-aD[:self.T-1,i]/aDs[:self.T-1,i],k=1)
            blockrow[-1,(i+1)*self.T-1] = 1-aD[self.T-1,i]/aDs[self.T-1,i]
            blockrows.append(blockrow)
        return np.vstack(blockrows)


    def messages_forwards_normalized_hmm(self):
        return HMMStatesPython._messages_forwards_normalized(
                self.hmm_forwards_trans_matrix,self.hmm_forwards_pi_0,self.hmm_aBl)

    def messages_backwards_normalized_hmm(self):
        return HMMStatesPython._messages_backwards_normalized(
                self.hmm_backwards_trans_matrix,self.hmm_backwards_pi_0,self.hmm_aBl)


    def messages_forwards_log_hmm(self):
        return HMMStatesPython._messages_forwards_log(
                self.hmm_forwards_trans_matrix,self.hmm_forwards_pi_0,self.hmm_aBl)

    def log_likelihood_forwards_hmm(self):
        alphal = self.messages_forwards_log_hmm()
        if self.right_censoring:
            return np.logaddexp.reduce(alphal[-1])
        else:
            # TODO should dot against deltas instead of ones
            raise NotImplementedError


    def messages_backwards_log_hmm(self):
        return HMMStatesPython._messages_backwards_log(
            self.hmm_backwards_trans_matrix,self.hmm_aBl)

    def log_likelihood_backwards_hmm(self):
        betal = self.messages_backwards_log_hmm()
        return np.logaddexp.reduce(np.log(self.hmm_backwards_pi_0) + self.hmm_aBl[0] + betal[0])


    def messages_backwards_log(self,*args,**kwargs):
        raise NotImplementedError # NOTE: this hmm method shouldn't be called this way

    def messages_fowrards_log(self,*args,**kwargs):
        raise NotImplementedError # NOTE: this hmm method shouldn't be called this way

    def messages_backwards_normalized(self,*args,**kwargs):
        raise NotImplementedError # NOTE: this hmm method shouldn't be called this way

    def messages_forwards_normalized(self,*args,**kwargs):
        raise NotImplementedError # NOTE: this hmm method shouldn't be called this way


### HSMM messages

def hsmm_messages_backwards_log(
    trans_potentials, initial_state_potential,
    cumulative_obs_potentials, dur_potentials, dur_survival_potentials,
    betal, betastarl,
    left_censoring=False, right_censoring=True):

    T, _ = betal.shape

    betal[-1] = 0.
    for t in xrange(T-1,-1,-1):
        cB = cumulative_obs_potentials(t)
        np.logaddexp.reduce(betal[t:t+cB.shape[0]] + cB + dur_potentials(t),
                axis=0, out=betastarl[t])
        if right_censoring:
            np.logaddexp(betastarl[t], cB[-1] + dur_survival_potentials(t),
                    out=betastarl[t])
        np.logaddexp.reduce(betastarl[t] + trans_potentials(t-1),
                axis=1, out=betal[t-1])
    betal[-1] = 0. # overwritten on last iteration

    if not left_censoring:
        normalizer = np.logaddexp.reduce(initial_state_potential + betastarl[0])
    else:
        raise NotImplementedError

    return betal, betastarl, normalizer

def hsmm_messages_forwards_log(
    trans_potential, initial_state_potential,
    reverse_cumulative_obs_potentials, reverse_dur_potentials, reverse_dur_survival_potentials,
    alphal, alphastarl,
    left_censoring=False, right_censoring=True):

    T, _ = alphal.shape

    alphastarl[0] = initial_state_potential
    for t in xrange(T-1):
        cB = reverse_cumulative_obs_potentials(t)
        np.logaddexp.reduce(alphastarl[t+1-cB.shape[0]:t+1] + cB + reverse_dur_potentials(t),
                axis=0, out=alphal[t])
        if left_censoring:
            raise NotImplementedError
        np.logaddexp.reduce(alphal[t][:,na] + trans_potential(t),
                axis=0, out=alphastarl[t+1])
    t = T-1
    cB = reverse_cumulative_obs_potentials(t)
    np.logaddexp.reduce(alphastarl[t+1-cB.shape[0]:t+1] + cB + reverse_dur_potentials(t),
            axis=0, out=alphal[t])

    if not right_censoring:
        normalizer = np.logaddexp.reduce(alphal[t])
    else:
        normalizer = None # TODO

    return alphal, alphastarl, normalizer


# TODO test with trunc
def hsmm_sample_forwards_log(
    trans_potentials, initial_state_potential,
    cumulative_obs_potentials, dur_potentials, dur_survival_potentails,
    betal, betastarl,
    left_censoring=False, right_censoring=True):

    T, _ = betal.shape
    stateseq = np.empty(T,dtype=np.int)
    durations = []

    t = 0

    if left_censoring:
        raise NotImplementedError
    else:
        nextstate_unsmoothed = initial_state_potential

    while t < T:
        ## sample the state
        nextstate_distn_log = nextstate_unsmoothed + betastarl[t]
        nextstate_distn = np.exp(nextstate_distn_log - np.logaddexp.reduce(nextstate_distn_log))
        assert nextstate_distn.sum() > 0
        state = sample_discrete(nextstate_distn)

        ## sample the duration
        dur_logpmf = dur_potentials(t)[:,state]
        obs = cumulative_obs_potentials(t)[:,state]
        durprob = np.random.random()

        dur = 0 # NOTE: always incremented at least once
        while durprob > 0 and dur < dur_logpmf.shape[0] and t+dur < T:
            p_d = np.exp(dur_logpmf[dur] + obs[dur]
                    + betal[t+dur,state] - betastarl[t,state])

            assert not np.isnan(p_d)
            durprob -= p_d
            dur += 1

        stateseq[t:t+dur] = state
        durations.append(dur)

        t += dur
        nextstate_log_distn = trans_potentials(t)[state]

    return stateseq, durations

def hsmm_maximizing_assignment(
    N, T,
    trans_potentials, initial_state_potential,
    cumulative_obs_potentials, reverse_cumulative_obs_potentials,
    dur_potentials, dur_survival_potentials,
    left_censoring=False, right_censoring=True):

    beta_scores, beta_args = np.empty((T,N)), np.empty((T,N),dtype=np.int)
    betastar_scores, betastar_args = np.empty((T,N)), np.empty((T,N),dtype=np.int)

    beta_scores[-1] = 0.
    for t in xrange(T-1,-1,-1):
        cB = cumulative_obs_potentials(t)

        vals = beta_scores[t:t+cB.shape[0]] + cB + dur_potentials(t)
        if right_censoring:
            vals = np.vstack((vals,cB[-1] + dur_survival_potentials(t)))

        vals.max(axis=0,out=betastar_scores[t])
        vals.argmax(axis=0,out=betastar_args[t])

        vals = betastar_scores[t] + trans_potentials(t-1)

        vals.max(axis=1,out=beta_scores[t-1])
        vals.argmax(axis=1,out=beta_args[t-1])
    beta_scores[-1] = 0.

    stateseq = np.empty(T,dtype=np.int)

    t = 0
    state = (betastar_scores[t] + initial_state_potential).argmax()
    dur = betastar_args[t,state]
    stateseq[t:t+dur] = state
    t += dur
    while t < T:
        state = beta_args[t-1,state]
        dur = betastar_args[t,state] + 1
        stateseq[t:t+dur] = state
        t += dur

    return stateseq


########NEW FILE########
__FILENAME__ = initial_state
from __future__ import division
import numpy as np

from ..util.general import top_eigenvector
from ..basic.abstractions import GibbsSampling, MaxLikelihood
from ..basic.distributions import Categorical

class HMMInitialState(Categorical):
    def __init__(self,model,init_state_concentration=None,pi_0=None):
        self.model = model
        if init_state_concentration is not None or pi_0 is not None:
            self._is_steady_state = False
            super(HMMInitialState,self).__init__(
                    alpha_0=init_state_concentration,K=model.num_states,weights=pi_0)
        else:
            self._is_steady_state = True

    @property
    def pi_0(self):
        if self._is_steady_state:
            return self.steady_state_distribution
        else:
            return self.weights

    @pi_0.setter
    def pi_0(self,pi_0):
        self.weights = pi_0

    @property
    def exp_expected_log_init_state_distn(self):
        return np.exp(self.expected_log_likelihood())

    @property
    def steady_state_distribution(self):
        return top_eigenvector(self.model.trans_distn.trans_matrix)

    def clear_caches(self):
        pass

class StartInZero(GibbsSampling,MaxLikelihood):
    def __init__(self,num_states,**kwargs):
        self.pi_0 = np.zeros(num_states)
        self.pi_0[0] = 1.

    def resample(self,init_states=np.array([])):
        pass

    def rvs(self,size=[]):
        return np.zeros(size)

    def max_likelihood(*args,**kwargs):
        pass

class HSMMInitialState(HMMInitialState):
    @property
    def steady_state_distribution(self):
        if self._steady_state_distribution is None:
            markov_part = super(HSMMSteadyState,self).pi_0
            duration_expectations = np.array([d.mean for d in self.model.dur_distns])
            self._steady_state_distribution = markov_part * duration_expectations
            self._steady_state_distribution /= self._steady_state_distribution.sum()
        return self._steady_state_distribution

    def clear_caches(self):
        self._steady_state_distribution = None


########NEW FILE########
__FILENAME__ = transitions
from __future__ import division
import numpy as np
import scipy.stats as stats
from numpy import newaxis as na
np.seterr(invalid='raise')
import operator
import copy

from scipy.special import digamma, gammaln

from ..basic.abstractions import GibbsSampling
from ..basic.distributions import GammaCompoundDirichlet, Multinomial, \
        MultinomialAndConcentration
from ..util.general import rle, count_transitions, cumsum, rcumsum
from ..util.cstats import sample_crp_tablecounts

# TODO separate out bayesian and nonbayesian versions?

########################
#  HMM / HSMM classes  #
########################

# NOTE: no hierarchical priors here (i.e. no number-of-states inference)

### HMM

class _HMMTransitionsBase(object):
    def __init__(self,num_states=None,alpha=None,alphav=None,trans_matrix=None):
        self.N = num_states

        if trans_matrix is not None:
            self._row_distns = [Multinomial(alpha_0=alpha,K=self.N,alphav_0=alphav,
                weights=row) for row in trans_matrix]
        elif None not in (alpha,self.N) or alphav is not None:
            self._row_distns = [Multinomial(alpha_0=alpha,K=self.N,alphav_0=alphav)
                    for n in xrange(self.N)] # sample from prior

    @property
    def trans_matrix(self):
        return np.array([d.weights for d in self._row_distns])

    @trans_matrix.setter
    def trans_matrix(self,trans_matrix):
        N = self.N = trans_matrix.shape[0]
        self._row_distns = \
                [Multinomial(alpha_0=self.alpha,K=N,alphav_0=self.alphav,weights=row)
                        for row in trans_matrix]

    @property
    def alpha(self):
        return self._row_distns[0].alpha_0

    @alpha.setter
    def alpha(self,val):
        for distn in self._row_distns:
            distn.alpha_0 = val

    @property
    def alphav(self):
        return self._row_distns[0].alphav_0

    @alphav.setter
    def alphav(self,weights):
        for distn in self._row_distns:
            distn.alphav_0 = weights

    def _count_transitions(self,stateseqs):
        if len(stateseqs) == 0 or isinstance(stateseqs,np.ndarray) \
                or isinstance(stateseqs[0],int) or isinstance(stateseqs[0],float):
            return count_transitions(stateseqs,minlength=self.N)
        else:
            return sum(count_transitions(stateseq,minlength=self.N)
                    for stateseq in stateseqs)

    def copy_sample(self):
        new = copy.copy(self)
        new._row_distns = [distn.copy_sample() for distn in self._row_distns]
        return new

class _HMMTransitionsGibbs(_HMMTransitionsBase):
    def resample(self,stateseqs=[],trans_counts=None):
        trans_counts = self._count_transitions(stateseqs) if trans_counts is None \
                else trans_counts
        for distn, counts in zip(self._row_distns,trans_counts):
            distn.resample(counts)
        return self

class _HMMTransitionsMaxLikelihood(_HMMTransitionsBase):
    def max_likelihood(self,stateseqs=None,expected_transcounts=None):
        trans_counts = sum(expected_transcounts) if stateseqs is None \
                else self._count_transitions(stateseqs)
        # NOTE: could just call max_likelihood on each trans row, but this way
        # it handles a few lazy-initialization cases (e.g. if _row_distns aren't
        # initialized)
        errs = np.seterr(invalid='ignore',divide='ignore')
        self.trans_matrix = np.nan_to_num(trans_counts / trans_counts.sum(1)[:,na])
        np.seterr(**errs)
        return self

class _HMMTransitionsMeanField(_HMMTransitionsBase):
    @property
    def exp_expected_log_trans_matrix(self):
        return np.exp(np.array([distn.expected_log_likelihood()
            for distn in self._row_distns]))

    def meanfieldupdate(self,expected_transcounts):
        assert isinstance(expected_transcounts,list) and len(expected_transcounts) > 0
        trans_softcounts = sum(expected_transcounts)
        for distn, counts in zip(self._row_distns,trans_softcounts):
            distn.meanfieldupdate(None,counts)
        return self

    def get_vlb(self):
        return sum(distn.get_vlb() for distn in self._row_distns)

    def _resample_from_mf(self):
        for d in self._row_distns:
            d._resample_from_mf()

class _HMMTransitionsSVI(_HMMTransitionsMeanField):
    def meanfield_sgdstep(self,expected_transcounts,minibatchfrac,stepsize):
        assert isinstance(expected_transcounts,list)
        trans_softcounts = sum(expected_transcounts)
        for distn, counts in zip(self._row_distns,trans_softcounts):
            distn.meanfield_sgdstep(None,counts,minibatchfrac,stepsize)
        return self

class HMMTransitions(
        _HMMTransitionsGibbs,
        _HMMTransitionsSVI,
        _HMMTransitionsMeanField,
        _HMMTransitionsMaxLikelihood):
    pass

class _ConcentrationResamplingMixin(object):
    # NOTE: because all rows share the same concentration parameter, we can't
    # use CategoricalAndConcentration; gotta use GammaCompoundDirichlet directly
    def __init__(self,num_states,alpha_a_0,alpha_b_0,**kwargs):
        self.alpha_obj = GammaCompoundDirichlet(num_states,alpha_a_0,alpha_b_0)
        super(_ConcentrationResamplingMixin,self).__init__(
                num_states=num_states,alpha=self.alpha,**kwargs)

    @property
    def alpha(self):
        return self.alpha_obj.concentration

    @alpha.setter
    def alpha(self,alpha):
        if alpha is not None:
            self.alpha_obj.concentration = alpha # a no-op when called internally
            for d in self._row_distns:
                d.alpha_0 = alpha

    def resample(self,stateseqs=[],trans_counts=None):
        trans_counts = self._count_transitions(stateseqs) if trans_counts is None \
                else trans_counts

        self._resample_alpha(trans_counts)

        return super(_ConcentrationResamplingMixin,self).resample(
                stateseqs=stateseqs,trans_counts=trans_counts)

    def _resample_alpha(self,trans_counts):
        self.alpha_obj.resample(trans_counts)
        self.alpha = self.alpha_obj.concentration

    def meanfieldupdate(self,*args,**kwargs):
        raise NotImplementedError # TODO

class HMMTransitionsConc(_ConcentrationResamplingMixin,_HMMTransitionsGibbs):
    pass

### HSMM

class _HSMMTransitionsBase(_HMMTransitionsBase):
    def _get_trans_matrix(self):
        out = self.full_trans_matrix
        out.flat[::out.shape[0]+1] = 0
        errs = np.seterr(invalid='ignore')
        out /= out.sum(1)[:,na]
        out = np.nan_to_num(out)
        np.seterr(**errs)
        return out

    trans_matrix = property(_get_trans_matrix,_HMMTransitionsBase.trans_matrix.fset)

    @property
    def full_trans_matrix(self):
        return super(_HSMMTransitionsBase,self).trans_matrix

    def _count_transitions(self,stateseqs):
        stateseq_noreps = [rle(stateseq)[0] for stateseq in stateseqs]
        return super(_HSMMTransitionsBase,self)._count_transitions(stateseq_noreps)

class _HSMMTransitionsGibbs(_HSMMTransitionsBase,_HMMTransitionsGibbs):
    # NOTE: in this non-hierarchical case, we wouldn't need the below data
    # augmentation if we were only to update the distribution on off-diagonal
    # components. but it's easier to code if we just keep everything complete
    # dirichlet/multinomial and do the data augmentation here, especially since
    # we'll need it for the hierarchical case anyway.

    def _count_transitions(self,stateseqs):
        trans_counts = super(_HSMMTransitionsGibbs,self)._count_transitions(stateseqs)

        if trans_counts.sum() > 0:
            froms = trans_counts.sum(1)
            self_trans = [np.random.geometric(1-A_ii,size=n).sum() if n > 0 else 0
                    for A_ii, n in zip(self.full_trans_matrix.diagonal(),froms)]
            trans_counts += np.diag(self_trans)

        return trans_counts

class _HSMMTransitionsMaxLikelihood(_HSMMTransitionsBase,_HMMTransitionsMaxLikelihood):
    def max_likelihood(self,stateseqs=None,expected_transcounts=None):
        trans_counts = sum(expected_transcounts) if stateseqs is None \
                else self._count_transitions(stateseqs)
        # NOTE: we could just call max_likelihood on each trans row, but this
        # way it's a bit nicer
        errs = np.seterr(invalid='ignore',divide='ignore')
        self.trans_matrix = np.nan_to_num(trans_counts / trans_counts.sum(1)[:,na])
        np.seterr(**errs)
        assert np.allclose(0,np.diag(self.trans_matrix))
        return self

class _HSMMTransitionsMeanField(_HSMMTransitionsBase,_HMMTransitionsMeanField):
    pass

class _HSMMTransitionsSVI(_HSMMTransitionsMeanField,_HMMTransitionsSVI):
    pass

class HSMMTransitions(_HSMMTransitionsGibbs,
        _HSMMTransitionsMaxLikelihood,
        _HSMMTransitionsSVI,
        _HSMMTransitionsMeanField):
    # NOTE: include MaxLikelihood for convenience, uses
    # _HMMTransitionsBase._count_transitions
    pass

class HSMMTransitionsConc(_ConcentrationResamplingMixin,_HSMMTransitionsGibbs):
    pass

############################
#  Weak-Limit HDP classes  #
############################

### HDP-HMM

class _WeakLimitHDPHMMTransitionsBase(_HMMTransitionsBase):
    def __init__(self,gamma,alpha,num_states=None,beta=None,trans_matrix=None):
        if num_states is None:
            assert beta is not None or trans_matrix is not None
            self.N = len(beta) if beta is not None else trans_matrix.shape[0]
        else:
            self.N = num_states

        self.alpha = alpha
        self.beta_obj = Multinomial(alpha_0=gamma,K=self.N,weights=beta)

        super(_WeakLimitHDPHMMTransitionsBase,self).__init__(
                num_states=self.N,alpha=alpha,
                alphav=alpha*self.beta,trans_matrix=trans_matrix)

    @property
    def beta(self):
        return self.beta_obj.weights

    @beta.setter
    def beta(self,weights):
        self.beta_obj.weights = weights
        self.alphav = self.alpha * self.beta

    @property
    def gamma(self):
        return self.beta_obj.alpha_0

    @gamma.setter
    def gamma(self,val):
        self.beta_obj.alpha_0 = val

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self,val):
        self._alpha = val

    def copy_sample(self):
        new = super(_WeakLimitHDPHMMTransitionsBase,self).copy_sample()
        new.beta_obj = self.beta_obj.copy_sample()
        return new

class _WeakLimitHDPHMMTransitionsGibbs(
        _WeakLimitHDPHMMTransitionsBase,
        _HMMTransitionsGibbs):
    def resample(self,stateseqs=[],trans_counts=None,ms=None):
        trans_counts = self._count_transitions(stateseqs) if trans_counts is None \
                else trans_counts
        ms = self._get_m(trans_counts) if ms is None else ms

        self._resample_beta(ms)

        return super(_WeakLimitHDPHMMTransitionsGibbs,self).resample(
                stateseqs=stateseqs,trans_counts=trans_counts)

    def _resample_beta(self,ms):
        self.beta_obj.resample(ms)
        self.alphav = self.alpha * self.beta

    def _get_m(self,trans_counts):
        if not (0 == trans_counts).all():
            m = sample_crp_tablecounts(self.alpha,trans_counts,self.beta)
        else:
            m = np.zeros_like(trans_counts)
        self.m = m
        return m

class WeakLimitHDPHMMTransitions(_WeakLimitHDPHMMTransitionsGibbs,_HMMTransitionsMaxLikelihood):
    # NOTE: include MaxLikelihood for convenience
    pass


class _WeakLimitHDPHMMTransitionsConcBase(_WeakLimitHDPHMMTransitionsBase):
    def __init__(self,num_states,gamma_a_0,gamma_b_0,alpha_a_0,alpha_b_0,
            beta=None,trans_matrix=None,**kwargs):
        if num_states is None:
            assert beta is not None or trans_matrix is not None
            self.N = len(beta) if beta is not None else trans_matrix.shape[0]
        else:
            self.N = num_states

        self.beta_obj = MultinomialAndConcentration(a_0=gamma_a_0,b_0=gamma_b_0,
                K=self.N,weights=beta)
        self.alpha_obj = GammaCompoundDirichlet(self.N,alpha_a_0,alpha_b_0)

        # NOTE: we don't want to call WeakLimitHDPHMMTransitions.__init__
        # because it sets beta_obj in a different way
        _HMMTransitionsBase.__init__(
                self, num_states=self.N, alphav=self.alpha*self.beta,
                trans_matrix=trans_matrix, **kwargs)

    @property
    def alpha(self):
        return self.alpha_obj.concentration

    @alpha.setter
    def alpha(self,val):
        self.alpha_obj.concentration = val

class _WeakLimitHDPHMMTransitionsConcGibbs(
        _WeakLimitHDPHMMTransitionsConcBase,_WeakLimitHDPHMMTransitionsGibbs):
    def resample(self,stateseqs=[],trans_counts=None,ms=None):
        trans_counts = self._count_transitions(stateseqs) if trans_counts is None \
                else trans_counts
        ms = self._get_m(trans_counts) if ms is None else ms

        self._resample_beta(ms)
        self._resample_alpha(trans_counts)

        return super(_WeakLimitHDPHMMTransitionsConcGibbs,self).resample(
                stateseqs=stateseqs,trans_counts=trans_counts)

    def _resample_beta(self,ms):
        # NOTE: unlike parent, alphav is updated in _resample_alpha
        self.beta_obj.resample(ms)

    def _resample_alpha(self,trans_counts):
        self.alpha_obj.resample(trans_counts,weighted_cols=self.beta)
        self.alphav = self.alpha * self.beta

    def copy_sample(self):
        new = super(_WeakLimitHDPHMMTransitionsConcGibbs,self).copy_sample()
        new.alpha_obj = self.alpha_obj.copy_sample()
        return new

class WeakLimitHDPHMMTransitionsConc(_WeakLimitHDPHMMTransitionsConcGibbs):
    pass

# Sticky HDP-HMM

class _WeakLimitStickyHDPHMMTransitionsBase(_WeakLimitHDPHMMTransitionsBase):
    def __init__(self,kappa,**kwargs):
        self.kappa = kappa
        super(_WeakLimitStickyHDPHMMTransitionsBase,self).__init__(**kwargs)


class _WeakLimitStickyHDPHMMTransitionsGibbs(
        _WeakLimitStickyHDPHMMTransitionsBase,_WeakLimitHDPHMMTransitionsGibbs):
    def _set_alphav(self,weights):
        for distn, delta_ij in zip(self._row_distns,np.eye(self.N)):
            distn.alphav_0 = weights + self.kappa * delta_ij

    alphav = property(_WeakLimitHDPHMMTransitionsGibbs.alphav.fget,_set_alphav)

    def _get_m(self,trans_counts):
        # NOTE: this thins the m's
        ms = super(_WeakLimitStickyHDPHMMTransitionsGibbs,self)._get_m(trans_counts)
        newms = ms.copy()
        if ms.sum() > 0:
            # np.random.binomial fails when n=0, so pull out nonzero indices
            indices = np.nonzero(newms.flat[::ms.shape[0]+1])
            newms.flat[::ms.shape[0]+1][indices] = np.array(np.random.binomial(
                    ms.flat[::ms.shape[0]+1][indices],
                    self.beta[indices]*self.alpha/(self.beta[indices]*self.alpha + self.kappa)),
                    dtype=np.int32)
        return newms

class WeakLimitStickyHDPHMMTransitions(
        _WeakLimitStickyHDPHMMTransitionsGibbs,_HMMTransitionsMaxLikelihood):
    # NOTE: includes MaxLikelihood for convenience
    pass

# DA Truncation

class _DATruncHDPHMMTransitionsBase(_HMMTransitionsBase):
    # NOTE: self.beta stores \beta_{1:K}, so \beta_{\text{rest}} is implicit

    def __init__(self,gamma,alpha,num_states,beta=None,trans_matrix=None):
        self.N = num_states
        self.gamma = gamma
        self._alpha = alpha
        if beta is None:
            beta = np.ones(num_states) / (num_states + 1)
            # beta = self._sample_GEM(gamma,num_states)
        assert not np.isnan(beta).any()

        betafull = np.concatenate(((beta,(1.-beta.sum(),))))

        super(_DATruncHDPHMMTransitionsBase,self).__init__(
                num_states=self.N,alphav=alpha*betafull,trans_matrix=trans_matrix)

        self.beta = beta

    @staticmethod
    def _sample_GEM(gamma,K):
        v = np.random.beta(1.,gamma,size=K)
        return v * np.concatenate(((1.,),np.cumprod(1.-v[:-1])))

    @property
    def beta(self):
        return self._beta

    @beta.setter
    def beta(self,beta):
        self._beta = beta
        self.alphav = self._alpha * np.concatenate((beta,(1.-beta.sum(),)))

    @property
    def exp_expected_log_trans_matrix(self):
        return super(_DATruncHDPHMMTransitionsBase,self).exp_expected_log_trans_matrix[:,:-1].copy()

    @property
    def trans_matrix(self):
        return super(_DATruncHDPHMMTransitionsBase,self).trans_matrix[:,:-1].copy()

class _DATruncHDPHMMTransitionsSVI(_DATruncHDPHMMTransitionsBase,_HMMTransitionsSVI):
    def meanfieldupdate(self,expected_transcounts):
        super(_DATruncHDPHMMTransitionsSVI,self).meanfieldupdate(
                self._pad_zeros(expected_transcounts))

    def meanfield_sgdstep(self,expected_transcounts,minibatchfrac,stepsize):
        # NOTE: since we take a step on q(beta) and on q(pi) at the same time
        # (as usual with SVI), we compute the beta gradient and perform the pi
        # step before applying the beta gradient

        beta_gradient = self._beta_gradient()
        super(_DATruncHDPHMMTransitionsSVI,self).meanfield_sgdstep(
                self._pad_zeros(expected_transcounts),minibatchfrac,stepsize)
        self.beta = self._feasible_step(self.beta,beta_gradient,stepsize)
        assert (self.beta >= 0.).all() and self.beta.sum() < 1
        return self

    def _pad_zeros(self,counts):
        if isinstance(counts,np.ndarray):
            return np.pad(counts,((0,1),(0,1)),mode='constant',constant_values=0)
        return [self._pad_zeros(c) for c in counts]

    @staticmethod
    def _feasible_step(pt,grad,stepsize):
        def newpt(pt,grad,stepsize):
            return pt + stepsize*grad
        def feas(pt):
            return (pt>0.).all() and pt.sum() < 1.
        grad = grad / np.abs(grad).max()
        while True:
            new = newpt(pt,grad,stepsize)
            if feas(new):
                return new
            else:
                grad /= 1.5

    def _beta_gradient(self):
        return self._grad_log_p_beta(self.beta,self.gamma) + \
            sum(self._grad_E_log_p_pi_given_beta(self.beta,self._alpha,
                distn._alpha_mf) for distn in self._row_distns)

    @staticmethod
    def _grad_log_p_beta(beta,alpha):
        # NOTE: switched argument name gamma <-> alpha
        return  -(alpha-1)*rcumsum(1./(1-cumsum(beta))) \
                + 2*rcumsum(1./(1-cumsum(beta,strict=True)),strict=True)

    def _grad_E_log_p_pi_given_beta(self,beta,gamma,alphatildes):
        # NOTE: switched argument name gamma <-> alpha
        retval = gamma*(digamma(alphatildes[:-1]) - digamma(alphatildes[-1])) \
                - gamma * (digamma(gamma*beta) - digamma(gamma))
        return retval

    def get_vlb(self):
        return super(_DATruncHDPHMMTransitionsSVI,self).get_vlb() \
                + self._beta_vlb()

    def _beta_vlb(self):
        return np.log(self.beta).sum() + self.gamma*np.log(1-cumsum(self.beta)).sum() \
               - 3*np.log(1-cumsum(self.beta,strict=True)).sum()

class DATruncHDPHMMTransitions(_DATruncHDPHMMTransitionsSVI):
    pass

### HDP-HSMM

# Weak limit

class WeakLimitHDPHSMMTransitions(
        _HSMMTransitionsGibbs,
        _WeakLimitHDPHMMTransitionsGibbs,
        _HSMMTransitionsMaxLikelihood):
    # NOTE: required data augmentation handled in HSMMTransitions._count_transitions
    # NOTE: include MaxLikelihood for convenience
    pass

class WeakLimitHDPHSMMTransitionsConc(
        _WeakLimitHDPHMMTransitionsConcGibbs,
        _HSMMTransitionsGibbs,
        _HSMMTransitionsMaxLikelihood):
    # NOTE: required data augmentation handled in HSMMTransitions._count_transitions
    pass

# DA Truncation

class _DATruncHDPHSMMTransitionsSVI(_DATruncHDPHMMTransitionsSVI,_HSMMTransitionsSVI):
    # TODO the diagonal terms are still included in the vlb, so it's off by some
    # constant offset

    def _beta_gradient(self):
        return self._grad_log_p_beta(self.beta,self.gamma) + \
            sum(self._zero_ith_component(
                    self._grad_E_log_p_pi_given_beta(self.beta,self._alpha,distn._alpha_mf),i)
                    for i, distn in enumerate(self._row_distns))

    @staticmethod
    def _zero_ith_component(v,i):
        v = v.copy()
        v[i] = 0
        return v

class DATruncHDPHSMMTransitions(_DATruncHDPHSMMTransitionsSVI):
    pass


########NEW FILE########
__FILENAME__ = models
from __future__ import division
import numpy as np
from numpy import newaxis as na
import itertools, collections, operator, random, abc, copy
from matplotlib import pyplot as plt
from matplotlib import cm

from basic.abstractions import Model, ModelGibbsSampling, \
        ModelEM, ModelMAPEM, ModelMeanField, ModelMeanFieldSVI
import basic.distributions
from internals import hmm_states, hsmm_states, hsmm_inb_states, \
        initial_state, transitions
import util.general
from util.profiling import line_profiled

# TODO get rid of logical indexing with a data abstraction

################
#  HMM Mixins  #
################

class _HMMBase(Model):
    _states_class = hmm_states.HMMStatesPython
    _trans_class = transitions.HMMTransitions
    _trans_conc_class = transitions.HMMTransitionsConc
    _init_state_class = initial_state.HMMInitialState

    def __init__(self,
            obs_distns,
            trans_distn=None,
            alpha=None,alpha_a_0=None,alpha_b_0=None,trans_matrix=None,
            init_state_distn=None,init_state_concentration=None,pi_0=None):
        self.obs_distns = obs_distns
        self.states_list = []

        if trans_distn is not None:
            self.trans_distn = trans_distn
        elif not None in (alpha_a_0,alpha_b_0):
            self.trans_distn = self._trans_conc_class(
                    num_states=len(obs_distns),
                    alpha_a_0=alpha_a_0,alpha_b_0=alpha_b_0,
                    trans_matrix=trans_matrix)
        else:
            self.trans_distn = self._trans_class(
                    num_states=len(obs_distns),alpha=alpha,trans_matrix=trans_matrix)

        if init_state_distn is not None:
            self.init_state_distn = init_state_distn
        else:
            self.init_state_distn = self._init_state_class(
                    model=self,
                    init_state_concentration=init_state_concentration,
                    pi_0=pi_0)

        self._clear_caches()

    def add_data(self,data,stateseq=None,**kwargs):
        self.states_list.append(
                self._states_class(
                    model=self,data=data,
                    stateseq=stateseq,**kwargs))

    def generate(self,T,keep=True):
        s = self._states_class(model=self,T=T,initialize_from_prior=True)
        data, stateseq = s.generate_obs(), s.stateseq
        if keep:
            self.states_list.append(s)
        return data, stateseq

    def log_likelihood(self,data=None,**kwargs):
        if data is not None:
            if isinstance(data,np.ndarray):
                self.add_data(data=data,generate=False,**kwargs)
                return self.states_list.pop().log_likelihood()
            else:
                assert isinstance(data,list)
                loglike = 0.
                for d in data:
                    self.add_data(data=d,generate=False,**kwargs)
                    loglike += self.states_list.pop().log_likelihood()
                return loglike
        else:
            return sum(s.log_likelihood() for s in self.states_list)

    @property
    def stateseqs(self):
        return [s.stateseq for s in self.states_list]

    @property
    def num_states(self):
        return len(self.obs_distns)

    @property
    def num_parameters(self):
        return sum(o.num_parameters() for o in self.obs_distns) + self.num_states**2

    ### predicting

    def heldout_viterbi(self,data,**kwargs):
        self.add_data(data=data,stateseq=np.zeros(len(data)),**kwargs)
        s = self.states_list.pop()
        s.Viterbi()
        return s.stateseq

    def heldout_state_marginals(self,data,**kwargs):
        self.add_data(data=data,stateseq=np.zeros(len(data)),**kwargs)
        s = self.states_list.pop()
        log_margs = s.messages_forwards_log() + s.messages_backwards_log()
        log_margs -= s.log_likelihood()
        margs = np.exp(log_margs)
        margs /= margs.sum(1)[:,na]
        return margs

    def _resample_from_mf(self):
        self.trans_distn._resample_from_mf()
        self.init_state_distn._resample_from_mf()
        for o in self.obs_distns:
            o._resample_from_mf()

    ### caching

    def _clear_caches(self):
        for s in self.states_list:
            s.clear_caches()

    def __getstate__(self):
        self._clear_caches()
        return self.__dict__.copy()

    ### plotting

    def _get_used_states(self,states_objs=None):
        if states_objs is None:
            states_objs = self.states_list
        canonical_ids = collections.defaultdict(itertools.count().next)
        for s in states_objs:
            for state in s.stateseq:
                canonical_ids[state]
        return map(operator.itemgetter(0),
                sorted(canonical_ids.items(),key=operator.itemgetter(1)))

    def _get_colors(self,states_objs=None):
        if states_objs is not None:
            states = self._get_used_states(states_objs)
        else:
            states = range(len(self.obs_distns))
        numstates = len(states)
        return dict(zip(states,np.linspace(0,1,numstates,endpoint=True)))

    def plot_observations(self,colors=None,states_objs=None):
        if states_objs is None:
            states_objs = self.states_list

        cmap = cm.get_cmap()

        if len(states_objs) > 0:
            if colors is None:
                colors = self._get_colors(states_objs)
            used_states = self._get_used_states(states_objs)
            for state,o in enumerate(self.obs_distns):
                if state in used_states:
                    o.plot(
                        color=cmap(colors[state]),
                        data=[s.data[s.stateseq == state] if s.data is not None else None
                            for s in states_objs],
                        indices=[np.where(s.stateseq == state)[0] for s in states_objs],
                        label='%d' % state)
        else:
            N = len(self.obs_distns)
            colors = self._get_colors()
            weights = np.repeat(1./N,N).dot(
                    np.linalg.matrix_power(self.trans_distn.trans_matrix,1000))
            for state, o in enumerate(self.obs_distns):
                o.plot(
                        color=cmap(colors[state]),
                        label='%d' % state,
                        alpha=min(1.,weights[state]+0.05))
        plt.title('Observation Distributions')

    def plot(self,color=None,legend=False):
        plt.gcf() #.set_size_inches((10,10))

        if len(self.states_list) > 0:
            colors = self._get_colors()
            num_subfig_cols = len(self.states_list)
            for subfig_idx,s in enumerate(self.states_list):
                plt.subplot(2,num_subfig_cols,1+subfig_idx)
                self.plot_observations(colors=colors,states_objs=[s])

                plt.subplot(2,num_subfig_cols,1+num_subfig_cols+subfig_idx)
                s.plot(colors_dict=colors)

            if legend:
                plt.legend()
        else:
            self.plot_observations()

class _HMMGibbsSampling(_HMMBase,ModelGibbsSampling):
    def resample_model(self):
        self.resample_parameters()
        self.resample_states()

    def resample_parameters(self):
        self.resample_obs_distns()
        self.resample_trans_distn()
        self.resample_init_state_distn()

    def resample_obs_distns(self):
        for state, distn in enumerate(self.obs_distns):
            distn.resample([s.data[s.stateseq == state] for s in self.states_list])
        self._clear_caches()

    def resample_trans_distn(self):
        self.trans_distn.resample([s.stateseq for s in self.states_list])
        self._clear_caches()

    def resample_init_state_distn(self):
        self.init_state_distn.resample([s.stateseq[0] for s in self.states_list])
        self._clear_caches()

    def resample_states(self):
        for s in self.states_list:
            s.resample()

    def copy_sample(self):
        new = copy.copy(self)
        new.obs_distns = [o.copy_sample() for o in self.obs_distns]
        new.trans_distn = self.trans_distn.copy_sample()
        new.init_state_distn = self.init_state_distn.copy_sample()
        new.states_list = [s.copy_sample(new) for s in self.states_list]
        return new

    ### parallel

    def add_data_parallel(self,data,broadcast=False,**kwargs):
        import parallel
        self.add_data(data=data,**kwargs)
        if broadcast:
            parallel.broadcast_data(self._get_parallel_data(data))
        else:
            parallel.add_data(self._get_parallel_data(self.states_list[-1]))

    def resample_model_parallel(self,temp=None):
        self.resample_parameters(temp=temp)
        self.resample_states_parallel(temp=temp)

    def resample_states_parallel(self,temp=None):
        import parallel
        states_to_resample = self.states_list
        self.states_list = [] # removed because we push the global model
        raw = parallel.map_on_each(
                self._state_sampler,
                [self._get_parallel_data(s) for s in states_to_resample],
                kwargss=self._get_parallel_kwargss(states_to_resample),
                engine_globals=dict(global_model=self,temp=temp))
        for s, stateseq in zip(states_to_resample,raw):
            s.stateseq = stateseq
        self.states_list = states_to_resample

    def _get_parallel_data(self,states_obj):
        return states_obj.data

    def _get_parallel_kwargss(self,states_objs):
        # this method is broken out so that it can be overridden
        return None

    @staticmethod
    @util.general.engine_global_namespace # access to engine globals
    def _state_sampler(data,**kwargs):
        # expects globals: global_model, temp
        global_model.add_data(data=data,initialize_from_prior=False,temp=temp,**kwargs)
        return global_model.states_list.pop().stateseq

class _HMMMeanField(_HMMBase,ModelMeanField):
    def meanfield_coordinate_descent_step(self):
        self._meanfield_update_sweep()
        return self._vlb()

    def _meanfield_update_sweep(self):
        for s in self.states_list:
            if not hasattr(s,'expected_states'):
                s.meanfieldupdate()

        self.meanfield_update_parameters()
        self.meanfield_update_states()

    def meanfield_update_parameters(self):
        self.meanfield_update_obs_distns()
        self.meanfield_update_trans_distn()
        self.meanfield_update_init_state_distn()

    def meanfield_update_obs_distns(self):
        for state, o in enumerate(self.obs_distns):
            o.meanfieldupdate([s.data for s in self.states_list],
                    [s.expected_states[:,state] for s in self.states_list])

    def meanfield_update_trans_distn(self):
        self.trans_distn.meanfieldupdate(
                [s.expected_transcounts for s in self.states_list])

    def meanfield_update_init_state_distn(self):
        self.init_state_distn.meanfieldupdate(None,
                [s.expected_states[0] for s in self.states_list])

    def meanfield_update_states(self):
        for s in self.states_list:
            s.meanfieldupdate()

    def _vlb(self):
        vlb = 0.
        vlb += sum(s.get_vlb() for s in self.states_list)
        vlb += self.trans_distn.get_vlb()
        vlb += self.init_state_distn.get_vlb()
        vlb += sum(o.get_vlb() for o in self.obs_distns)
        return vlb

class _HMMSVI(_HMMBase,ModelMeanFieldSVI):
    def meanfield_sgdstep(self,minibatch,minibatchfrac,stepsize,joblib_jobs=0,**kwargs):
        ## compute the local mean field step for the minibatch
        if joblib_jobs == 0:
            mb_states_list = self._get_mb_states_list(minibatch,**kwargs)
            for s in mb_states_list:
                s.meanfieldupdate()
        else:
            from joblib import Parallel, delayed
            from parallel import _get_stats

            from warnings import warn
            warn('this is segfaulting, not sure why') # TODO

            joblib_args = self._get_joblib_args(joblib_jobs,minibatch,**kwargs)
            assert len(joblib_args) == joblib_jobs

            allstats = Parallel(n_jobs=joblib_jobs,backend='multiprocessing')\
                    (delayed(_get_stats)(self,arg) for arg in joblib_args)

            mb_states_list = self._get_mb_states_list(minibatch,**kwargs)
            for s, stats in zip(mb_states_list,[s for grp in allstats for s in grp]):
                s.all_expected_stats = stats

        ## take a global step on the parameters
        self._meanfield_sgdstep_parameters(mb_states_list,minibatchfrac,stepsize)

    def _get_joblib_args(self,joblib_jobs,minibatch):
        minibatch = minibatch if isinstance(minibatch,list) else [minibatch]
        return util.general.list_split(minibatch,joblib_jobs)

    def _get_mb_states_list(self,minibatch,**kwargs):
        minibatch = minibatch if isinstance(minibatch,list) else [minibatch]
        mb_states_list = []
        for mb in minibatch:
            self.add_data(mb,stateseq=np.empty(mb.shape[0]),**kwargs) # dummy to hook stuff up
            mb_states_list.append(self.states_list.pop())
        return mb_states_list

    def _meanfield_sgdstep_parameters(self,mb_states_list,minibatchfrac,stepsize):
        self._meanfield_sgdstep_obs_distns(mb_states_list,minibatchfrac,stepsize)
        self._meanfield_sgdstep_trans_distn(mb_states_list,minibatchfrac,stepsize)
        self._meanfield_sgdstep_init_state_distn(mb_states_list,minibatchfrac,stepsize)

    def _meanfield_sgdstep_obs_distns(self,mb_states_list,minibatchfrac,stepsize):
        for state, o in enumerate(self.obs_distns):
            o.meanfield_sgdstep(
                    [s.data for s in mb_states_list],
                    [s.expected_states[:,state] for s in mb_states_list],
                    minibatchfrac,stepsize)

    def _meanfield_sgdstep_trans_distn(self,mb_states_list,minibatchfrac,stepsize):
        self.trans_distn.meanfield_sgdstep(
                [s.expected_transcounts for s in mb_states_list],
                minibatchfrac,stepsize)

    def _meanfield_sgdstep_init_state_distn(self,mb_states_list,minibatchfrac,stepsize):
        self.init_state_distn.meanfield_sgdstep(
                None,[s.expected_states[0] for s in mb_states_list],
                minibatchfrac,stepsize)

    def heldout_vlb(self,datas):
        assert len(self.states_list) == 0

        if isinstance(datas,list):
            for data in datas:
                self.add_data(data)
        else:
            self.add_data(datas)

        for s in self.states_list:
            s.meanfieldupdate()

        vlb = self._vlb()

        self.states_list = []
        return vlb

class _HMMEM(_HMMBase,ModelEM):
    def EM_step(self):
        assert len(self.states_list) > 0, 'Must have data to run EM'
        self._clear_caches()
        self._E_step()
        self._M_step()

    def _E_step(self):
        for s in self.states_list:
            s.E_step()

    def _M_step(self):
        for state, distn in enumerate(self.obs_distns):
            distn.max_likelihood([s.data for s in self.states_list],
                    [s.expectations[:,state] for s in self.states_list])

        self.init_state_distn.max_likelihood(
                None,weights=[s.expectations[0] for s in self.states_list])

        self.trans_distn.max_likelihood(
                expected_transcounts=[s.expected_transcounts for s in self.states_list])

    def BIC(self,data=None):
        '''
        BIC on the passed data. If passed data is None (default), calculates BIC
        on the model's assigned data
        '''
        # NOTE: in principle this method computes the BIC only after finding the
        # maximum likelihood parameters (or, of course, an EM fixed-point as an
        # approximation!)
        assert data is None and len(self.states_list) > 0, 'Must have data to get BIC'
        if data is None:
            return -2*sum(self.log_likelihood(s.data).sum() for s in self.states_list) + \
                        self.num_parameters() * np.log(
                                sum(s.data.shape[0] for s in self.states_list))
        else:
            return -2*self.log_likelihood(data) + self.num_parameters() * np.log(data.shape[0])

class _HMMViterbiEM(_HMMBase,ModelMAPEM):
    def Viterbi_EM_fit(self, tol=0.1, maxiter=20):
        return self.MAP_EM_fit(tol, maxiter)

    def Viterbi_EM_step(self):
        assert len(self.states_list) > 0, 'Must have data to run Viterbi EM'
        self._clear_caches()

        ## Viterbi step
        for s in self.states_list:
            s.Viterbi()

        ## M step
        for state, distn in enumerate(self.obs_distns):
            distn.max_likelihood([s.data[s.stateseq == state] for s in self.states_list])

        self.init_state_distn.max_likelihood(
                np.array([s.stateseq[0] for s in self.states_list]))

        self.trans_distn.max_likelihood([s.stateseq for s in self.states_list])

    MAP_EM_step = Viterbi_EM_step

class _WeakLimitHDPMixin(object):
    def __init__(self,
            obs_distns,
            trans_distn=None,alpha=None,alpha_a_0=None,alpha_b_0=None,
            gamma=None,gamma_a_0=None,gamma_b_0=None,trans_matrix=None,
            **kwargs):

        if trans_distn is not None:
            trans_distn = trans_distn
        elif not None in (alpha_a_0,alpha_b_0):
            trans_distn = self._trans_conc_class(
                    num_states=len(obs_distns),
                    alpha_a_0=alpha_a_0,alpha_b_0=alpha_b_0,
                    gamma_a_0=gamma_a_0,gamma_b_0=gamma_b_0,
                    trans_matrix=trans_matrix)
        else:
            trans_distn = self._trans_class(
                    num_states=len(obs_distns),alpha=alpha,gamma=gamma,
                    trans_matrix=trans_matrix)

        super(_WeakLimitHDPMixin,self).__init__(
                obs_distns=obs_distns,trans_distn=trans_distn,**kwargs)

################
#  HMM models  #
################

class HMMPython(_HMMGibbsSampling,_HMMSVI,_HMMMeanField,_HMMEM,_HMMViterbiEM):
    pass

class HMM(HMMPython):
    _states_class = hmm_states.HMMStatesEigen

class WeakLimitHDPHMMPython(_WeakLimitHDPMixin,HMMPython):
    # NOTE: shouldn't really inherit EM or ViterbiEM, but it's convenient!
    _trans_class = transitions.WeakLimitHDPHMMTransitions
    _trans_conc_class = transitions.WeakLimitHDPHMMTransitionsConc

class WeakLimitHDPHMM(_WeakLimitHDPMixin,HMM):
    _trans_class = transitions.WeakLimitHDPHMMTransitions
    _trans_conc_class = transitions.WeakLimitHDPHMMTransitionsConc

class DATruncHDPHMM(_WeakLimitHDPMixin,HMMPython):
    # NOTE: weak limit mixin is poorly named; we just want its init method
    _trans_class = transitions.DATruncHDPHMMTransitions
    _trans_conc_class = None

class DATruncHDPHMM(_WeakLimitHDPMixin,HMM):
    _trans_class = transitions.DATruncHDPHMMTransitions
    _trans_conc_class = None

class WeakLimitStickyHDPHMM(WeakLimitHDPHMM):
    # TODO concentration resampling, too!
    def __init__(self,obs_distns,
            kappa=None,alpha=None,gamma=None,trans_matrix=None,**kwargs):
        trans_distn = transitions.WeakLimitStickyHDPHMMTransitions(
                num_states=len(obs_distns),
                kappa=kappa,alpha=alpha,gamma=gamma,trans_matrix=trans_matrix)
        super(WeakLimitStickyHDPHMM,self).__init__(
                obs_distns=obs_distns,trans_distn=trans_distn,**kwargs)

#################
#  HSMM Mixins  #
#################

class _HSMMBase(_HMMBase):
    _states_class = hsmm_states.HSMMStatesPython
    _trans_class = transitions.HSMMTransitions
    _trans_conc_class = transitions.HSMMTransitionsConc
    # _init_steady_state_class = initial_state.HSMMSteadyState # TODO

    def __init__(self,dur_distns,**kwargs):
        self.dur_distns = dur_distns
        super(_HSMMBase,self).__init__(**kwargs)

    def add_data(self,data,stateseq=None,trunc=None,
            right_censoring=True,left_censoring=False,**kwargs):
        self.states_list.append(self._states_class(
            model=self,
            data=np.asarray(data),
            stateseq=stateseq,
            right_censoring=right_censoring,
            left_censoring=left_censoring,
            trunc=trunc,
            **kwargs))

    @property
    def stateseqs_norep(self):
        return [s.stateseq_norep for s in self.states_list]

    @property
    def durations(self):
        return [s.durations for s in self.states_list]

    @property
    def num_parameters(self):
        return sum(o.num_parameters() for o in self.obs_distns) \
                + sum(d.num_parameters() for d in self.dur_distns) \
                + self.num_states**2 - self.num_states

    def plot_durations(self,colors=None,states_objs=None):
        if colors is None:
            colors = self._get_colors()
        if states_objs is None:
            states_objs = self.states_list

        cmap = cm.get_cmap()
        used_states = self._get_used_states(states_objs)
        for state,d in enumerate(self.dur_distns):
            if state in used_states:
                d.plot(color=cmap(colors[state]),
                        data=[s.durations[s.stateseq_norep == state]
                            for s in states_objs])
        plt.title('Durations')

    def plot(self,color=None):
        plt.gcf() #.set_size_inches((10,10))
        colors = self._get_colors()

        num_subfig_cols = len(self.states_list)
        for subfig_idx,s in enumerate(self.states_list):
            plt.subplot(3,num_subfig_cols,1+subfig_idx)
            self.plot_observations(colors=colors,states_objs=[s])

            plt.subplot(3,num_subfig_cols,1+num_subfig_cols+subfig_idx)
            s.plot(colors_dict=colors)

            plt.subplot(3,num_subfig_cols,1+2*num_subfig_cols+subfig_idx)
            self.plot_durations(colors=colors,states_objs=[s])

class _HSMMGibbsSampling(_HSMMBase,_HMMGibbsSampling):
    def resample_parameters(self):
        self.resample_dur_distns()
        super(_HSMMGibbsSampling,self).resample_parameters()

    @line_profiled
    def resample_dur_distns(self):
        for state, distn in enumerate(self.dur_distns):
            distn.resample_with_truncations(
            data=
            [s.durations_censored[s.untrunc_slice][s.stateseq_norep[s.untrunc_slice] == state]
                for s in self.states_list],
            truncated_data=
            [s.durations_censored[s.trunc_slice][s.stateseq_norep[s.trunc_slice] == state]
                for s in self.states_list])
        self._clear_caches()

    def copy_sample(self):
        new = super(_HSMMGibbsSampling,self).copy_sample()
        new.dur_distns = [d.copy_sample() for d in self.dur_distns]
        return new

    ### parallel

    def _get_parallel_kwargss(self,states_objs):
        return [dict(trunc=s.trunc,left_censoring=s.left_censoring,
                    right_censoring=s.right_censoring) for s in states_objs]

class _HSMMEM(_HSMMBase,_HMMEM):
    def _M_step(self):
        super(_HSMMEM,self)._M_step()
        for state, distn in enumerate(self.dur_distns):
            distn.max_likelihood(
                    [np.arange(1,s.expected_durations[state].shape[0]+1)
                        for s in self.states_list],
                    [s.expected_durations[state] for s in self.states_list])

class _HSMMMeanField(_HSMMBase,_HMMMeanField):
    def meanfield_update_parameters(self):
        super(_HSMMMeanField,self).meanfield_update_parameters()
        self.meanfield_update_dur_distns()

    def meanfield_update_dur_distns(self):
        for state, d in enumerate(self.dur_distns):
            d.meanfieldupdate(
                    [np.arange(1,s.expected_durations[state].shape[0]+1)
                        for s in self.states_list],
                    [s.expected_durations[state] for s in self.states_list])

    def _vlb(self):
        vlb = super(_HSMMMeanField,self)._vlb()
        vlb += sum(d.get_vlb() for d in self.dur_distns)
        return vlb

class _HSMMSVI(_HSMMBase,_HMMSVI):
    def _meanfield_sgdstep_parameters(self,mb_states_list,minibatchfrac,stepsize):
        super(_HSMMSVI,self)._meanfield_sgdstep_parameters(mb_states_list,minibatchfrac,stepsize)
        self._meanfield_sgdstep_dur_distns(mb_states_list,minibatchfrac,stepsize)

    def _meanfield_sgdstep_dur_distns(self,mb_states_list,minibatchfrac,stepsize):
        for state, d in enumerate(self.dur_distns):
            d.meanfield_sgdstep(
                    [np.arange(1,s.expected_durations[state].shape[0]+1)
                        for s in mb_states_list],
                    [s.expected_durations[state] for s in mb_states_list],
                    minibatchfrac,stepsize)

class _HSMMINBEMMixin(_HMMEM,ModelEM):
    def EM_step(self):
        super(_HSMMINBEMMixin,self).EM_step()
        for state, distn in enumerate(self.dur_distns):
            distn.max_likelihood(data=None,stats=(
                sum(s.expected_dur_ns[state] for s in self.states_list),
                sum(s.expected_dur_tots[state] for s in self.states_list)))

class _HSMMViterbiEM(_HSMMBase,_HMMViterbiEM):
    def Viterbi_EM_step(self):
        super(_HSMMViterbiEM,self).Viterbi_EM_step()
        for state, distn in enumerate(self.dur_distns):
            distn.max_likelihood(
                    [s.durations[s.stateseq_norep == state] for s in self.states_list])

class _HSMMPossibleChangepointsMixin(object):
    _states_class = hsmm_states.HSMMStatesPossibleChangepoints

    def add_data(self,data,changepoints,**kwargs):
        super(_HSMMPossibleChangepointsMixin,self).add_data(
                data=data,changepoints=changepoints,**kwargs)

    def _get_joblib_args(self,joblib_jobs,minibatch,changepoints):
        if not isinstance(minibatch,(list,tuple)):
            assert isinstance(minibatch,np.ndarray)
            assert isinstance(changepoints,list) and isinstance(changepoints[0],tuple)
            minibatch = [minibatch]
            changepoints = [changepoints]
        else:
            assert  isinstance(changepoints,(list,tuple))  \
                    and isinstance(changepoints[0],(list,tuple)) \
                    and isinstance(changepoints[0][0],tuple)
            assert len(minibatch) == len(changepoints)

        return util.general.list_split(zip(*[minibatch,changepoints]),joblib_jobs)

    def _get_mb_states_list(self,minibatch,changepoints,**kwargs):
        if not isinstance(minibatch,(list,tuple)):
            assert isinstance(minibatch,np.ndarray)
            assert isinstance(changepoints,list) and isinstance(changepoints[0],tuple)
            minibatch = [minibatch]
            changepoints = [changepoints]
        else:
            assert  isinstance(changepoints,(list,tuple))  \
                    and isinstance(changepoints[0],(list,tuple)) \
                    and isinstance(changepoints[0][0],tuple)
            assert len(minibatch) == len(changepoints)

        mb_states_list = []
        for data, changes in zip(minibatch,changepoints):
            self.add_data(data,changepoints=changes,
                    stateseq=np.empty(data.shape[0]),**kwargs)
            mb_states_list.append(self.states_list.pop())
        return mb_states_list

    def log_likelihood(self,data=None,changepoints=None,**kwargs):
        if data is not None:
            assert changepoints is not None
            if isinstance(data,np.ndarray):
                assert isinstance(changepoints,list)
                self.add_data(data=data,changepoints=changepoints,
                        generate=False,**kwargs)
                return self.states_list.pop().log_likelihood()
            else:
                assert isinstance(data,list) and isinstance(changepoints,list) \
                        and len(changepoints) == len(data)
                loglike = 0.
                for d, c in zip(data,changepoints):
                    self.add_data(data=d,changepoints=c,generate=False,**kwargs)
                    loglike += self.states_list.pop().log_likelihood()
                return loglike
        else:
            return sum(s.log_likelihood() for s in self.states_list)

    def _get_parallel_kwargss(self,states_objs):
        # TODO this is wasteful: it should be in _get_parallel_data
        dcts = super(HSMMPossibleChangepoints,self)._get_parallel_kwargss(states_objs)
        for dct, states_obj in zip(dcts,states_objs):
            dct.update(dict(changepoints=states_obj.changepoints))
        return dcts

#################
#  HSMM Models  #
#################

class HSMMPython(_HSMMGibbsSampling,_HSMMSVI,_HSMMMeanField,_HSMMViterbiEM,_HSMMEM):
    _trans_class = transitions.HSMMTransitions
    _trans_conc_class = transitions.HSMMTransitionsConc

class HSMM(HSMMPython):
    _states_class = hsmm_states.HSMMStatesEigen

# class HSMMHMMEmbedding(HSMMPython):
#     _states_class = hsmm_states.HSMMStatesEmbedding

class WeakLimitHDPHSMMPython(_WeakLimitHDPMixin,HSMMPython):
    # NOTE: shouldn't technically inherit EM or ViterbiEM, but it's convenient
    _trans_class = transitions.WeakLimitHDPHSMMTransitions
    _trans_conc_class = transitions.WeakLimitHDPHSMMTransitionsConc

class WeakLimitHDPHSMM(_WeakLimitHDPMixin,HSMM):
    _trans_class = transitions.WeakLimitHDPHSMMTransitions
    _trans_conc_class = transitions.WeakLimitHDPHSMMTransitionsConc

class WeakLimitGeoHDPHSMM(WeakLimitHDPHSMM):
    _states_class = hsmm_states.GeoHSMMStates

class DATruncHDPHSMM(_WeakLimitHDPMixin,HSMM):
    # NOTE: weak limit mixin is poorly named; we just want its init method
    _trans_class = transitions.DATruncHDPHSMMTransitions
    _trans_conc_class = None

class HSMMIntNegBin(_HSMMGibbsSampling,_HSMMMeanField,_HSMMSVI,_HSMMViterbiEM):
    _trans_class = transitions.HSMMTransitions
    _trans_conc_class = transitions.HSMMTransitionsConc
    _states_class = hsmm_inb_states.HSMMStatesIntegerNegativeBinomial

    def _resample_from_mf(self):
        super(HSMMIntNegBin,self)._resample_from_mf()
        for d in self.dur_distns:
            d._resample_from_mf()

    def _vlb(self):
        return 0. # TODO

class WeakLimitHDPHSMMIntNegBin(_WeakLimitHDPMixin,HSMMIntNegBin):
    _trans_class = transitions.WeakLimitHDPHSMMTransitions
    _trans_conc_class = transitions.WeakLimitHDPHSMMTransitionsConc

class HSMMIntNegBinVariant(_HSMMGibbsSampling,_HSMMINBEMMixin,_HSMMViterbiEM):
    _trans_class = transitions.HSMMTransitions
    _trans_conc_class = transitions.HSMMTransitionsConc
    _states_class = hsmm_inb_states.HSMMStatesIntegerNegativeBinomialVariant

class WeakLimitHDPHSMMIntNegBinVariant(_WeakLimitHDPMixin,HSMMIntNegBinVariant):
    _trans_class = transitions.WeakLimitHDPHSMMTransitions
    _trans_conc_class = transitions.WeakLimitHDPHSMMTransitionsConc


class HSMMPossibleChangepointsPython(_HSMMPossibleChangepointsMixin,HSMMPython):
    pass

class HSMMPossibleChangepoints(_HSMMPossibleChangepointsMixin,HSMM):
    pass

class WeakLimitHDPHSMMPossibleChangepointsPython(_HSMMPossibleChangepointsMixin,WeakLimitHDPHSMMPython):
    pass

class WeakLimitHDPHSMMPossibleChangepoints(_HSMMPossibleChangepointsMixin,WeakLimitHDPHSMM):
    pass


########NEW FILE########
__FILENAME__ = parallel
from __future__ import division
import numpy as np
from IPython.parallel import Client
import os
from util.general import engine_global_namespace

from warnings import warn
warn("This code hasn't been tested in a while...") # TODO

# these globals get set, named here for clarity
client = None
dv = None
costs = None
data_residency = None

def reset_engines():
    global costs, data_residency
    dv.push(dict(my_data={}))
    costs = np.zeros(len(dv))
    data_residency = {}

def set_up_engines():
    global client, dv
    try:
        profile = os.environ["PYHSMM_IPYTHON_PARALLEL_PROFILE"]
    except KeyError:
        profile = 'default'
    if client is None:
        client = Client(profile=profile)
        dv = client[:]
        reset_engines()

def set_profile(this_profile):
    global profile, client
    profile = this_profile
    client = None
    os.environ["PYHSMM_IPYTHON_PARALLEL_PROFILE"] = profile

def get_num_engines():
    return len(dv)

def phash(d):
    'hash based on object address in memory, not data values'
    assert isinstance(d,(np.ndarray,tuple))
    if isinstance(d,np.ndarray):
        return d.__hash__()
    else:
        return hash(tuple(map(phash,d)))

def vhash(d):
    'hash based on data values'
    assert isinstance(d,(np.ndarray,tuple))
    if isinstance(d,np.ndarray):
        d.flags.writeable = False
        return hash(d.data)
    else:
        return hash(tuple(map(vhash,d)))

def clear_ipython_caches():
    client.purge_results('all')
    client.results.clear()
    dv.results.clear()

### adding and managing data

# internals

# NOTE: data_id (and everything else that doesn't have to do with preloading) is
# based on phash, which should only be called on the controller

@engine_global_namespace
def update_my_data(data_id,data):
    my_data[data_id] = data

# interface

def has_data(data):
    return phash(data) in data_residency

def add_data(data,costfunc=len):
    global data_residency, costs
    set_up_engines()
    # NOTE: this is basically a one-by-one scatter with an additive parametric
    # cost function treated greedily
    ph = phash(data)
    engine_to_send = np.argmin(costs)
    data_residency[ph] = engine_to_send
    costs[engine_to_send] += costfunc(data)
    return client[client._ids[engine_to_send]].apply_async(update_my_data,ph,data)

def broadcast_data(data,costfunc=len):
    global data_residency, costs
    set_up_engines()
    ph = phash(data)
    # sets data residency so that other functions can be used (one engine,
    # chosen by greedy static balancing, has responsibility)
    # NOTE: not blocking above assumes linear cost function
    engine_to_send = np.argmin(costs)
    data_residency[ph] = engine_to_send
    costs[engine_to_send] += costfunc(data)
    return dv.apply_async(update_my_data,ph,data)


def register_added_data(data):
    raise NotImplementedError # TODO

def register_broadcasted_data(data):
    raise NotImplementedError # TODO


def map_on_each(fn,added_datas,kwargss=None,engine_globals=None):
    global client, dv
    set_up_engines()
    @engine_global_namespace
    def _call(f,data_id,**kwargs):
        return f(my_data[data_id],**kwargs)

    if engine_globals is not None:
        dv.push(engine_globals,block=True)

    if kwargss is None:
        kwargss = [{} for data in added_datas] # no communication overhead

    indata = [(phash(data),data,kwargs) for data,kwargs in zip(added_datas,kwargss)]
    ars = [client[client._ids[data_residency[data_id]]].apply_async(_call,fn,data_id,**kwargs)
                    for data_id, data, kwargs in indata]
    dv.wait(ars)
    results = [ar.get() for ar in ars]

    clear_ipython_caches()

    return results

def map_on_each_broadcasted(fn,broadcasted_datas,kwargss=None,engine_globals=None):
    raise NotImplementedError # TODO lbv version

def call_with_all(fn,broadcasted_datas,kwargss,engine_globals=None):
    global client, dv
    set_up_engines()

    # one call for each element of kwargss
    @engine_global_namespace
    def _call(f,data_ids,kwargs):
        return f([my_data[data_id] for data_id in data_ids],**kwargs)

    if engine_globals is not None:
        dv.push(engine_globals,block=True)

    results = dv.map_sync(
            _call,
            [fn]*len(kwargss),
            [[phash(data) for data in broadcasted_datas]]*len(kwargss),
            kwargss)

    clear_ipython_caches()

    return results


### MISC / TEMP

def _get_stats(model,grp):
    datas, changepointss = zip(*grp)
    mb_states_list = []
    for data, changepoints in zip(datas,changepointss):
        model.add_data(data,changepoints=changepoints,stateseq=np.empty(data.shape[0]))
        mb_states_list.append(model.states_list.pop())

    for s in mb_states_list:
        s.meanfieldupdate()

    return [s.all_expected_stats for s in mb_states_list]


########NEW FILE########
__FILENAME__ = test_hmm
from __future__ import division
import numpy as np
from numpy import newaxis as na
from inspect import getargspec
from functools import wraps
import itertools
from nose.plugins.attrib import attr

from pyhsmm import models as m, distributions as d

##################################
#  likelihoods / messages tests  #
##################################

### util

def likelihood_check(obs_distns,trans_matrix,init_distn,data,target_val):
    for cls in [m.HMMPython, m.HMM]:
        hmm = cls(alpha=6.,init_state_concentration=1, # placeholders
                obs_distns=obs_distns)
        hmm.trans_distn.trans_matrix = trans_matrix
        hmm.init_state_distn.weights = init_distn
        hmm.add_data(data)

        # test default log_likelihood method

        assert np.isclose(target_val, hmm.log_likelihood())

        # manual tests of the several message passing methods

        states = hmm.states_list[-1]

        states.clear_caches()
        states.messages_forwards_normalized()
        assert np.isclose(target_val,states._loglike)

        states.clear_caches()
        states.messages_forwards_log()
        assert np.isinf(target_val) or np.isclose(target_val,states._loglike)

        states.clear_caches()
        states.messages_backwards_log()
        assert np.isinf(target_val) or np.isclose(target_val,states._loglike)

        # test held-out vs in-model

        assert np.isclose(target_val, hmm.log_likelihood(data))

def compute_likelihood_enumeration(obs_distns,trans_matrix,init_distn,data):
    N = len(obs_distns)
    T = len(data)

    Al = np.log(trans_matrix)
    aBl = np.hstack([o.log_likelihood(data)[:,na] for o in obs_distns])

    tot = -np.inf
    for stateseq in itertools.product(range(N),repeat=T):
        loglike = 0.
        loglike += np.log(init_distn[stateseq[0]])
        for a,b in zip(stateseq[:-1],stateseq[1:]):
            loglike += Al[a,b]
        for t,a in enumerate(stateseq):
            loglike += aBl[t,a]
        tot = np.logaddexp(tot,loglike)
    return tot

def random_model(nstates):
    init_distn = np.random.dirichlet(np.ones(nstates))
    trans_matrix = np.vstack([np.random.dirichlet(np.ones(nstates)) for i in range(nstates)])
    return dict(init_distn=init_distn,trans_matrix=trans_matrix)

def runmultiple(n):
    def dec(fn):
        @wraps(fn)
        def wrapper():
            for i in range(n):
                yield fn
        return wrapper
    return dec

### tests

@attr('hmm','likelihood','messages','basic')
def like_hand_test_1():
    likelihood_check(
        obs_distns=[d.Categorical(weights=row) for row in np.eye(2)],
        trans_matrix=np.eye(2),
        init_distn=np.array([1.,0.]),
        data=np.zeros(10,dtype=int),
        target_val=0.)

@attr('hmm','likelihood','messages','basic','robust')
def like_hand_test_2():
    likelihood_check(
        obs_distns=[d.Categorical(weights=row) for row in np.eye(2)],
        trans_matrix=np.eye(2),
        init_distn=np.array([0.,1.]),
        data=np.zeros(10,dtype=int),
        target_val=np.log(0.))

@attr('hmm','likelihood','messages','basic')
def like_hand_test_3():
    likelihood_check(
        obs_distns=[d.Categorical(weights=row) for row in np.eye(2)],
        trans_matrix=np.array([[0.,1.],[1.,0.]]),
        init_distn=np.array([1.,0.]),
        data=np.tile([0,1],5).astype(int),
        target_val=0.)

@attr('hmm','likelihood','messages','basic')
def like_hand_test_4():
    likelihood_check(
        obs_distns=[d.Categorical(weights=row) for row in np.eye(2)],
        trans_matrix=np.array([[0.,1.],[1.,0.]]),
        init_distn=np.array([1.,0.]),
        data=np.tile([0,1],5).astype(int),
        target_val=0.)

@attr('hmm','likelihood','messages','basic')
def like_hand_test_5():
    likelihood_check(
        obs_distns=[d.Categorical(weights=row) for row in np.eye(2)],
        trans_matrix=np.array([[0.9,0.1],[0.2,0.8]]),
        init_distn=np.array([1.,0.]),
        data=np.tile((0,1),5),
        target_val=5*np.log(0.1) + 4*np.log(0.2))

@attr('hmm','slow','likelihood','messages')
@runmultiple(3)
def discrete_exhaustive_test():
    model = random_model(2)
    obs_distns = [d.Categorical(K=3,alpha_0=1.),d.Categorical(K=3,alpha_0=1.)]
    stateseq = np.random.randint(2,size=10)
    data = np.array([obs_distns[a].rvs() for a in stateseq])
    target_val = compute_likelihood_enumeration(obs_distns=obs_distns,data=data,**model)
    likelihood_check(target_val=target_val,data=data,obs_distns=obs_distns,**model)

@attr('hmm','slow','likelihood','messages')
@runmultiple(3)
def gaussian_exhaustive_test():
    model = random_model(3)
    obs_distns = [
            d.Gaussian(mu=np.random.randn(2),sigma=np.eye(2)),
            d.Gaussian(mu=np.random.randn(2),sigma=np.eye(2)),
            d.Gaussian(mu=np.random.randn(2),sigma=np.eye(2))]
    stateseq = np.random.randint(3,size=10)
    data = np.vstack([obs_distns[a].rvs() for a in stateseq])
    target_val = compute_likelihood_enumeration(obs_distns=obs_distns,data=data,**model)
    likelihood_check(target_val=target_val,data=data,obs_distns=obs_distns,**model)


########NEW FILE########
__FILENAME__ = test_intnegbinhsmm
from __future__ import division
import numpy as np

from pyhsmm import models as m, distributions as d

######################
#  likelihood tests  #
######################

def _random_variant_model():
    N = 4
    obs_dim = 2

    obs_hypparams = {'mu_0':np.zeros(obs_dim),
                    'sigma_0':np.eye(obs_dim),
                    'kappa_0':0.05,
                    'nu_0':obs_dim+5}

    obs_distns = [d.Gaussian(**obs_hypparams) for state in range(N)]

    dur_distns = \
            [d.NegativeBinomialIntegerRVariantDuration(
                np.r_[0,0,0,0,0,1.,1.,1.], # discrete distribution uniform over {6,7,8}
                alpha_0=9,beta_0=1, # average geometric success probability 1/(9+1)
                ) for state in range(N)]

    model  = m.HSMMIntNegBinVariant(
            init_state_concentration=10.,alpha=6.,
            obs_distns=obs_distns,
            dur_distns=dur_distns)

    return model


def in_out_comparison_test():
    for i in range(2):
        yield _hmm_in_out_comparison_helper

def _hmm_in_out_comparison_helper():
    model = _random_variant_model()
    data, _ = model.generate(1000)

    like1 = model.log_likelihood()
    model.states_list = []
    like2 = model.log_likelihood(data)
    model.add_data(data)
    like3 = model.log_likelihood()

    assert np.isclose(like1,like2) and np.isclose(like2,like3)


def hmm_message_comparison_test():
    for i in range(2):
        yield _hmm_message_comparison_helper

def _hmm_message_comparison_helper():
    model = _random_variant_model()

    data, _ = model.generate(1000)

    likelihood_hsmmintnegbin_messages = model.log_likelihood(data)

    s = model.states_list[0]
    s.messages_backwards = None
    likelihood_hmm_messages = np.logaddexp.reduce(
            np.log(s.pi_0) + s.messages_backwards_hmm() + s.aBl[0])

    assert np.isclose(likelihood_hmm_messages, likelihood_hsmmintnegbin_messages)


########NEW FILE########
__FILENAME__ = cyutil
import Cython.Build
from Cython.Build.Dependencies import *

# NOTE: mostly a copy of cython's create_extension_list except for the lines
# surrounded by "begin matt added" / "end matt added"
def create_extension_list(patterns, exclude=[], ctx=None, aliases=None, quiet=False, exclude_failures=False):
    if not isinstance(patterns, list):
        patterns = [patterns]
    explicit_modules = set([m.name for m in patterns if isinstance(m, Extension)])
    seen = set()
    deps = create_dependency_tree(ctx, quiet=quiet)
    to_exclude = set()
    if not isinstance(exclude, list):
        exclude = [exclude]
    for pattern in exclude:
        to_exclude.update(extended_iglob(pattern))
    module_list = []
    for pattern in patterns:
        if isinstance(pattern, str):
            filepattern = pattern
            template = None
            name = '*'
            base = None
            exn_type = Extension
        elif isinstance(pattern, Extension):
            filepattern = pattern.sources[0]
            if os.path.splitext(filepattern)[1] not in ('.py', '.pyx'):
                # ignore non-cython modules
                module_list.append(pattern)
                continue
            template = pattern
            name = template.name
            base = DistutilsInfo(exn=template)
            exn_type = template.__class__
        else:
            raise TypeError(pattern)
        for file in extended_iglob(filepattern):
            if file in to_exclude:
                continue
            pkg = deps.package(file)
            if '*' in name:
                # NOTE: begin matt added
                # cython pre-0.20 had a typo here
                try:
                    module_name = deps.fully_qualifeid_name(file)
                except AttributeError:
                    module_name = deps.fully_qualified_name(file)
                # NOTE: end matt added
                if module_name in explicit_modules:
                    continue
            else:
                module_name = name
            if module_name not in seen:
                try:
                    kwds = deps.distutils_info(file, aliases, base).values
                except Exception:
                    if exclude_failures:
                        continue
                    raise
                if base is not None:
                    for key, value in base.values.items():
                        if key not in kwds:
                            kwds[key] = value
                sources = [file]
                if template is not None:
                    sources += template.sources[1:]
                if 'sources' in kwds:
                    # allow users to add .c files etc.
                    for source in kwds['sources']:
                        source = encode_filename_in_py2(source)
                        if source not in sources:
                            sources.append(source)
                    del kwds['sources']
                if 'depends' in kwds:
                    depends = resolve_depends(kwds['depends'], (kwds.get('include_dirs') or []) + [find_root_package_dir(file)])
                    if template is not None:
                        # Always include everything from the template.
                        depends = list(set(template.depends).union(set(depends)))
                    kwds['depends'] = depends
                # NOTE: begin matt added
                if 'name' in kwds:
                    module_name = str(kwds['name'])
                    del kwds['name']
                else:
                    module_name = os.path.splitext(file)[0].replace('/','.')
                # NOTE: end matt added
                module_list.append(exn_type(
                        name=module_name,
                        sources=sources,
                        **kwds))
                m = module_list[-1]
                seen.add(name)
    return module_list

true_cythonize = Cython.Build.cythonize
true_create_extension_list = Cython.Build.Dependencies.create_extension_list

def cythonize(*args,**kwargs):
    Cython.Build.Dependencies.create_extension_list = create_extension_list
    out = true_cythonize(*args,**kwargs)
    Cython.Build.Dependencies.create_extension_list = true_create_extension_list
    return out


########NEW FILE########
__FILENAME__ = general
from __future__ import division
import numpy as np
from numpy.lib.stride_tricks import as_strided as ast
import scipy.linalg
import copy, collections, os, shutil
from contextlib import closing
from urllib2 import urlopen
from itertools import izip, chain, count, ifilter

def solve_psd(A,b,chol=None,overwrite_b=False,overwrite_A=False):
    if A.shape[0] < 5000 and chol is None:
        return np.linalg.solve(A,b)
    else:
        if chol is None:
            chol = np.linalg.cholesky(A)
        return scipy.linalg.solve_triangular(
                chol.T,
                scipy.linalg.solve_triangular(chol,b,lower=True,overwrite_b=overwrite_b),
                lower=False,overwrite_b=True)

def interleave(*iterables):
    return list(chain.from_iterable(zip(*iterables)))

def joindicts(dicts):
    # stuff on right clobbers stuff on left
    return reduce(lambda x,y: dict(x,**y), dicts, {})

def one_vs_all(stuff):
    stuffset = set(stuff)
    for thing in stuff:
        yield thing, stuffset - set([thing])

def rle(stateseq):
    pos, = np.where(np.diff(stateseq) != 0)
    pos = np.concatenate(([0],pos+1,[len(stateseq)]))
    return stateseq[pos[:-1]], np.diff(pos)

def irle(vals,lens):
    out = np.empty(np.sum(lens))
    for v,l,start in zip(vals,lens,np.concatenate(((0,),np.cumsum(lens)[:-1]))):
        out[start:start+l] = v
    return out

def ibincount(counts):
    'returns an array a such that counts = np.bincount(a)'
    return np.repeat(np.arange(counts.shape[0]),counts)

def cumsum(v,strict=False):
    if not strict:
        return np.cumsum(v,axis=0)
    else:
        out = np.zeros_like(v)
        out[1:] = np.cumsum(v[:-1],axis=0)
        return out

def rcumsum(v,strict=False):
    if not strict:
        return np.cumsum(v[::-1],axis=0)[::-1]
    else:
        out = np.zeros_like(v)
        out[:-1] = np.cumsum(v[-1:0:-1],axis=0)[::-1]
        return out

def delta_like(v,i):
    out = np.zeros_like(v)
    out[i] = 1
    return out

def deepcopy(obj):
    return copy.deepcopy(obj)

def nice_indices(arr):
    '''
    takes an array like [1,1,5,5,5,999,1,1]
    and maps to something like [0,0,1,1,1,2,0,0]
    modifies original in place as well as returns a ref
    '''
    # surprisingly, this is slower for very small (and very large) inputs:
    # u,f,i = np.unique(arr,return_index=True,return_inverse=True)
    # arr[:] = np.arange(u.shape[0])[np.argsort(f)][i]
    ids = collections.defaultdict(count().next)
    for idx,x in enumerate(arr):
        arr[idx] = ids[x]
    return arr

def ndargmax(arr):
    return np.unravel_index(np.argmax(np.ravel(arr)),arr.shape)

def match_by_overlap(a,b):
    assert a.ndim == b.ndim == 1 and a.shape[0] == b.shape[0]
    ais, bjs = list(set(a)), list(set(b))
    scores = np.zeros((len(ais),len(bjs)))
    for i,ai in enumerate(ais):
        for j,bj in enumerate(bjs):
            scores[i,j] = np.dot(np.array(a==ai,dtype=np.float),b==bj)

    flip = len(bjs) > len(ais)

    if flip:
        ais, bjs = bjs, ais
        scores = scores.T

    matching = []
    while scores.size > 0:
        i,j = ndargmax(scores)
        matching.append((ais[i],bjs[j]))
        scores = np.delete(np.delete(scores,i,0),j,1)
        ais = np.delete(ais,i)
        bjs = np.delete(bjs,j)

    return matching if not flip else [(x,y) for y,x in matching]

def hamming_error(a,b):
    return (a!=b).sum()

def scoreatpercentile(data,per,axis=0):
    'like the function in scipy.stats but with an axis argument and works on arrays'
    a = np.sort(data,axis=axis)
    idx = per/100. * (data.shape[axis]-1)

    if (idx % 1 == 0):
        return a[[slice(None) if ii != axis else idx for ii in range(a.ndim)]]
    else:
        lowerweight = 1-(idx % 1)
        upperweight = (idx % 1)
        idx = int(np.floor(idx))
        return lowerweight * a[[slice(None) if ii != axis else idx for ii in range(a.ndim)]] \
                + upperweight * a[[slice(None) if ii != axis else idx+1 for ii in range(a.ndim)]]

def stateseq_hamming_error(sampledstates,truestates):
    sampledstates = np.array(sampledstates,ndmin=2).copy()

    errors = np.zeros(sampledstates.shape[0])
    for idx,s in enumerate(sampledstates):
        # match labels by maximum overlap
        matching = match_by_overlap(s,truestates)
        s2 = s.copy()
        for i,j in matching:
            s2[s==i] = j
        errors[idx] = hamming_error(s2,truestates)

    return errors if errors.shape[0] > 1 else errors[0]

def _sieve(stream):
    # just for fun; doesn't work over a few hundred
    val = stream.next()
    yield val
    for x in ifilter(lambda x: x%val != 0, _sieve(stream)):
        yield x

def primes():
    return _sieve(count(2))

def top_eigenvector(A,niter=1000,force_iteration=False):
    '''
    assuming the LEFT invariant subspace of A corresponding to the LEFT
    eigenvalue of largest modulus has geometric multiplicity of 1 (trivial
    Jordan block), returns the vector at the intersection of that eigenspace and
    the simplex

    A should probably be a ROW-stochastic matrix

    probably uses power iteration
    '''
    n = A.shape[0]
    np.seterr(invalid='raise',divide='raise')
    if n <= 25 and not force_iteration:
        x = np.repeat(1./n,n)
        x = np.linalg.matrix_power(A.T,niter).dot(x)
        x /= x.sum()
        return x
    else:
        x1 = np.repeat(1./n,n)
        x2 = x1.copy()
        for itr in xrange(niter):
            np.dot(A.T,x1,out=x2)
            x2 /= x2.sum()
            x1,x2 = x2,x1
            if np.linalg.norm(x1-x2) < 1e-8:
                break
        return x1

def engine_global_namespace(f):
    # see IPython.parallel.util.interactive; it's copied here so as to avoid
    # extra imports/dependences elsewhere, and to provide a slightly clearer
    # name
    f.__module__ = '__main__'
    return f

def block_view(a,block_shape):
    shape = (a.shape[0]/block_shape[0],a.shape[1]/block_shape[1]) + block_shape
    strides = (a.strides[0]*block_shape[0],a.strides[1]*block_shape[1]) + a.strides
    return ast(a,shape=shape,strides=strides)

def count_transitions(stateseq,minlength=None):
    if minlength is None:
        minlength = stateseq.max() + 1
    out = np.zeros((minlength,minlength),dtype=np.int32)
    for a,b in izip(stateseq[:-1],stateseq[1:]):
        out[a,b] += 1
    return out

### SGD

def sgd_steps(tau,kappa):
    assert 0.5 < kappa <= 1 and tau >= 0
    for t in count(1):
        yield (t+tau)**(-kappa)

def hold_out(datalist,frac):
    N = len(datalist)
    perm = np.random.permutation(N)
    split = int(np.ceil(frac * N))
    return [datalist[i] for i in perm[split:]], [datalist[i] for i in perm[:split]]

def sgd_onepass(tau,kappa,datalist,minibatchsize=1):
    N = len(datalist)

    if minibatchsize == 1:
        perm = np.random.permutation(N)
        for idx, rho_t in izip(perm,sgd_steps(tau,kappa)):
            yield datalist[idx], rho_t
    else:
        minibatch_indices = np.array_split(np.random.permutation(N),N/minibatchsize)
        for indices, rho_t in izip(minibatch_indices,sgd_steps(tau,kappa)):
            yield [datalist[idx] for idx in indices], rho_t

def sgd_manypass(tau,kappa,datalist,npasses,minibatchsize=1):
    for itr in xrange(npasses):
        for x in sgd_onepass(tau,kappa,datalist,minibatchsize=minibatchsize):
            yield x

def sgd_sampling(tau,kappa,datalist,minibatchsize=1):
    N = len(datalist)
    if minibatchsize == 1:
        for rho_t in sgd_steps(tau,kappa):
            minibatch_index = np.random.choice(N)
            yield datalist[minibatch_index], rho_t
    else:
        for rho_t in sgd_steps(tau,kappa):
            minibatch_indices = np.random.choice(N,size=minibatchsize,replace=False)
            yield [datalist[idx] for idx in minibatch_indices], rho_t

# TODO should probably eliminate this function
def minibatchsize(lst):
    return float(sum(d.shape[0] for d in lst))

### misc

def random_subset(lst,sz):
    perm = np.random.permutation(len(lst))
    return [lst[perm[idx]] for idx in xrange(sz)]

def get_file(remote_url,local_path):
    if not os.path.isfile(local_path):
        with closing(urlopen(remote_url)) as remotefile:
            with open(local_path,'wb') as localfile:
                shutil.copyfileobj(remotefile,localfile)

def list_split(lst,num):
    assert num > 0
    return [lst[start::num] for start in range(num)]


########NEW FILE########
__FILENAME__ = plot
from __future__ import division
import numpy as np
from matplotlib import pyplot as plt

# TODO move pca to stats

def plot_gaussian_2D(mu, lmbda, color='b', centermarker=True,label='',alpha=1.):
    '''
    Plots mean and cov ellipsoid into current axes. Must be 2D. lmbda is a covariance matrix.
    '''
    assert len(mu) == 2

    t = np.hstack([np.arange(0,2*np.pi,0.01),0])
    circle = np.vstack([np.sin(t),np.cos(t)])
    ellipse = np.dot(np.linalg.cholesky(lmbda),circle)

    if centermarker:
        plt.plot([mu[0]],[mu[1]],marker='D',color=color,markersize=4,alpha=alpha)
    plt.plot(ellipse[0,:] + mu[0], ellipse[1,:] + mu[1],linestyle='-',
            linewidth=2,color=color,label=label,alpha=alpha)


def plot_gaussian_projection(mu, lmbda, vecs, **kwargs):
    '''
    Plots a ndim gaussian projected onto 2D vecs, where vecs is a matrix whose two columns
    are the subset of some orthonomral basis (e.g. from PCA on samples).
    '''
    plot_gaussian_2D(project_data(mu,vecs),project_ellipsoid(lmbda,vecs),**kwargs)


def pca_project_data(data,num_components=2):
    # convenience combination of the next two functions
    return project_data(data,pca(data,num_components=num_components))


def pca(data,num_components=2):
    U,s,Vh = np.linalg.svd(data - np.mean(data,axis=0))
    return Vh.T[:,:num_components]


def project_data(data,vecs):
    return np.dot(data,vecs.T)


def project_ellipsoid(ellipsoid,vecs):
    # vecs is a matrix whose columns are a subset of an orthonormal basis
    # ellipsoid is a pos def matrix
    return np.dot(vecs,np.dot(ellipsoid,vecs.T))


def subplot_gridsize(num):
    return sorted(min([(x,int(np.ceil(num/x))) for x in range(1,int(np.floor(np.sqrt(num)))+1)],key=sum))

########NEW FILE########
__FILENAME__ = profiling
from __future__ import division
import numpy as np
import sys, StringIO, inspect, os, functools, time, collections

### use @timed for really basic timing

_timings = collections.defaultdict(list)

def timed(func):
    @functools.wraps(func)
    def wrapped(*args,**kwargs):
        tic = time.time()
        out = func(*args,**kwargs)
        _timings[func].append(time.time() - tic)
        return out
    return wrapped

def show_timings(stream=None):
    if stream is None:
        stream = sys.stdout
    if len(_timings) > 0:
        results = [(inspect.getsourcefile(f),f.__name__,
            len(vals),np.sum(vals),np.mean(vals),np.std(vals))
            for f, vals in _timings.iteritems()]
        filename_lens = max(len(filename) for filename, _, _, _, _, _ in results)
        name_lens = max(len(name) for _, name, _, _, _, _ in results)

        fmt = '{:>%d} {:>%d} {:>10} {:>10} {:>10} {:>10}' % (filename_lens, name_lens)
        print >>stream, fmt.format('file','name','ncalls','tottime','avg time','std dev')

        fmt = '{:>%d} {:>%d} {:>10} {:>10.3} {:>10.3} {:>10.3}' % (filename_lens, name_lens)
        print >>stream, '\n'.join(fmt.format(*tup) for tup in sorted(results))

### use @line_profiled for a thin wrapper around line_profiler

try:
    import line_profiler
    _prof = line_profiler.LineProfiler()

    def line_profiled(func):
        mod = inspect.getmodule(func)
        if 'PROFILING' in os.environ or (hasattr(mod,'PROFILING') and mod.PROFILING):
            return _prof(func)
        return func

    def show_line_stats(stream=None):
        _prof.print_stats(stream=stream)
except ImportError:
    line_profiled = lambda x: x


########NEW FILE########
__FILENAME__ = stats
from __future__ import division
import numpy as np
from numpy.random import random
na = np.newaxis
import scipy.stats as stats
import scipy.special as special
import scipy.linalg
from numpy.core.umath_tests import inner1d

import general

# TODO write cholesky versions

### data abstraction

def atleast_2d(data):
    # NOTE: can't use np.atleast_2d because if it's 1D we want axis 1 to be the
    # singleton and axis 0 to be the sequence index
    if data.ndim == 1:
        return data.reshape((-1,1))
    return data

def mask_data(data):
    return np.ma.masked_array(np.nan_to_num(data),np.isnan(data),fill_value=0.,hard_mask=True)

def gi(data):
    out = (np.isnan(atleast_2d(data)).sum(1) == 0).ravel()
    return out if len(out) != 0 else None

def getdatasize(data):
    if isinstance(data,np.ma.masked_array):
        return data.shape[0] - data.mask.reshape((data.shape[0],-1))[:,0].sum()
    elif isinstance(data,np.ndarray):
        if len(data) == 0:
            return 0
        return data[gi(data)].shape[0]
    elif isinstance(data,list):
        return sum(getdatasize(d) for d in data)
    else:
        # handle unboxed case for convenience
        assert isinstance(data,int) or isinstance(data,float)
        return 1

def getdatadimension(data):
    if isinstance(data,np.ndarray):
        assert data.ndim > 1
        return data.shape[1]
    elif isinstance(data,list):
        assert len(data) > 0
        return getdatadimension(data[0])
    else:
        # handle unboxed case for convenience
        assert isinstance(data,int) or isinstance(data,float)
        return 1

def combinedata(datas):
    ret = []
    for data in datas:
        if isinstance(data,np.ma.masked_array):
            ret.append(np.ma.compress_rows(data))
        if isinstance(data,np.ndarray):
            ret.append(data)
        elif isinstance(data,list):
            ret.extend(combinedata(data))
        else:
            # handle unboxed case for convenience
            assert isinstance(data,int) or isinstance(data,float)
            ret.append(np.atleast_1d(data))
    return ret

def flattendata(data):
    # data is either an array (possibly a maskedarray) or a list of arrays
    if isinstance(data,np.ndarray):
        return data
    elif isinstance(data,list) or isinstance(data,tuple):
        if any(isinstance(d,np.ma.MaskedArray) for d in data):
            return np.concatenate([np.ma.compress_rows(d) for d in data])
        else:
            return np.concatenate(data)
    else:
        # handle unboxed case for convenience
        assert isinstance(data,int) or isinstance(data,float)
        return np.atleast_1d(data)

### misc

def cov(a):
    # return np.cov(a,rowvar=0,bias=1)
    mu = a.mean(0)
    if isinstance(a,np.ma.MaskedArray):
        return np.ma.dot(a.T,a)/a.count(0)[0] - np.ma.outer(mu,mu)
    else:
        return a.T.dot(a)/a.shape[0] - np.outer(mu,mu)

### Sampling functions

def sample_discrete(distn,size=[],dtype=np.int32):
    'samples from a one-dimensional finite pmf'
    distn = np.atleast_1d(distn)
    assert (distn >=0).all() and distn.ndim == 1
    if (0 == distn).all():
        return np.random.randint(distn.shape[0],size=size)
    cumvals = np.cumsum(distn)
    return np.sum(np.array(random(size))[...,na] * cumvals[-1] > cumvals, axis=-1,dtype=dtype)

def sample_discrete_from_log(p_log,axis=0,dtype=np.int32):
    'samples log probability array along specified axis'
    cumvals = np.exp(p_log - np.expand_dims(p_log.max(axis),axis)).cumsum(axis) # cumlogaddexp
    thesize = np.array(p_log.shape)
    thesize[axis] = 1
    randvals = random(size=thesize) * \
            np.reshape(cumvals[[slice(None) if i is not axis else -1
                for i in range(p_log.ndim)]],thesize)
    return np.sum(randvals > cumvals,axis=axis,dtype=dtype)

def sample_markov(T,trans_matrix,init_state_distn):
    out = np.empty(T,dtype=np.int32)
    out[0] = sample_discrete(init_state_distn)
    for t in range(1,T):
        out[t] = sample_discrete(trans_matrix[out[t-1]])
    return out

def sample_niw(mu,lmbda,kappa,nu):
    '''
    Returns a sample from the normal/inverse-wishart distribution, conjugate
    prior for (simultaneously) unknown mean and unknown covariance in a
    Gaussian likelihood model. Returns covariance.
    '''
    # code is based on Matlab's method
    # reference: p. 87 in Gelman's Bayesian Data Analysis
    assert nu > lmbda.shape[0] and kappa > 0

    # first sample Sigma ~ IW(lmbda,nu)
    lmbda = sample_invwishart(lmbda,nu)
    # then sample mu | Lambda ~ N(mu, Lambda/kappa)
    mu = np.random.multivariate_normal(mu,lmbda / kappa)

    return mu, lmbda

def sample_invwishart(S,nu):
    # TODO make a version that returns the cholesky
    # TODO allow passing in chol/cholinv of matrix parameter lmbda
    # TODO lowmem! memoize! dchud (eigen?)
    n = S.shape[0]
    chol = np.linalg.cholesky(S)

    if (nu <= 81+n) and (nu == np.round(nu)):
        x = np.random.randn(nu,n)
    else:
        x = np.diag(np.sqrt(np.atleast_1d(stats.chi2.rvs(nu-np.arange(n)))))
        x[np.triu_indices_from(x,1)] = np.random.randn(n*(n-1)/2)
    R = np.linalg.qr(x,'r')
    T = scipy.linalg.solve_triangular(R.T,chol.T,lower=True).T
    return np.dot(T,T.T)

def sample_wishart(sigma, nu):
    n = sigma.shape[0]
    chol = np.linalg.cholesky(sigma)

    # use matlab's heuristic for choosing between the two different sampling schemes
    if (nu <= 81+n) and (nu == round(nu)):
        # direct
        X = np.dot(chol,np.random.normal(size=(n,nu)))
    else:
        A = np.diag(np.sqrt(np.random.chisquare(nu - np.arange(n))))
        A[np.tri(n,k=-1,dtype=bool)] = np.random.normal(size=(n*(n-1)/2.))
        X = np.dot(chol,A)

    return np.dot(X,X.T)

def sample_mn(M,U=None,Uinv=None,V=None,Vinv=None):
    assert (U is None) ^ (Uinv is None)
    assert (V is None) ^ (Vinv is None)

    G = np.random.normal(size=M.shape)

    if U is not None:
        G = np.dot(np.linalg.cholesky(U),G)
    else:
        G = np.linalg.solve(np.linalg.cholesky(Uinv).T,G)

    if V is not None:
        G = np.dot(G,np.linalg.cholesky(V).T)
    else:
        G = np.linalg.solve(np.linalg.cholesky(Vinv).T,G.T).T

    return M + G

def sample_mniw(nu,S,M,K=None,Kinv=None):
    assert (K is None) ^ (Kinv is None)
    Sigma = sample_invwishart(S,nu)
    if K is not None:
        return sample_mn(M=M,U=Sigma,V=K), Sigma
    else:
        return sample_mn(M=M,U=Sigma,Vinv=Kinv), Sigma

def sample_pareto(x_m,alpha):
    return x_m + np.random.pareto(alpha)

### Entropy
def invwishart_entropy(sigma,nu,chol=None):
    D = sigma.shape[0]
    chol = np.linalg.cholesky(sigma) if chol is None else chol
    Elogdetlmbda = special.digamma((nu-np.arange(D))/2).sum() + D*np.log(2) - 2*np.log(chol.diagonal()).sum()
    return invwishart_log_partitionfunction(sigma,nu,chol)-(nu-D-1)/2*Elogdetlmbda + nu*D/2

def invwishart_log_partitionfunction(sigma,nu,chol=None):
    D = sigma.shape[0]
    chol = np.linalg.cholesky(sigma) if chol is None else chol
    return -1*(nu*np.log(chol.diagonal()).sum() - (nu*D/2*np.log(2) + D*(D-1)/4*np.log(np.pi) \
            + special.gammaln((nu-np.arange(D))/2).sum()))

### Predictive

def multivariate_t_loglik(y,nu,mu,lmbda):
    # returns the log value
    d = len(mu)
    yc = np.array(y-mu,ndmin=2)
    L = np.linalg.cholesky(lmbda)
    ys = scipy.linalg.solve_triangular(L,yc.T,overwrite_b=True,lower=True)
    return scipy.special.gammaln((nu+d)/2.) - scipy.special.gammaln(nu/2.) \
            - (d/2.)*np.log(nu*np.pi) - np.log(L.diagonal()).sum() \
            - (nu+d)/2.*np.log1p(1./nu*inner1d(ys.T,ys.T))

def beta_predictive(priorcounts,newcounts):
    prior_nsuc, prior_nfail = priorcounts
    nsuc, nfail = newcounts

    numer = scipy.special.gammaln(np.array([nsuc+prior_nsuc,
        nfail+prior_nfail, prior_nsuc+prior_nfail])).sum()
    denom = scipy.special.gammaln(np.array([prior_nsuc, prior_nfail,
        prior_nsuc+prior_nfail+nsuc+nfail])).sum()
    return numer - denom

### Statistical tests

def two_sample_t_statistic(pop1, pop2):
    pop1, pop2 = (flattendata(p) for p in (pop1, pop2))
    t = (pop1.mean(0) - pop2.mean(0)) / np.sqrt(pop1.var(0)/pop1.shape[0] + pop2.var(0)/pop2.shape[0])
    p = 2*stats.t.sf(np.abs(t),np.minimum(pop1.shape[0],pop2.shape[0]))
    return t,p

def f_statistic(pop1, pop2): # TODO test
    pop1, pop2 = (flattendata(p) for p in (pop1, pop2))
    var1, var2 = pop1.var(0), pop2.var(0)
    n1, n2 = np.where(var1 >= var2, pop1.shape[0], pop2.shape[0]), \
             np.where(var1 >= var2, pop2.shape[0], pop1.shape[0])
    var1, var2 = np.maximum(var1,var2), np.minimum(var1,var2)
    f = var1 / var2
    p = stats.f.sf(f,n1,n2)
    return f,p


########NEW FILE########
__FILENAME__ = testing
from __future__ import division
import numpy as np
from numpy import newaxis as na
from matplotlib import pyplot as plt

import stats, general

#########################
#  statistical testing  #
#########################

### graphical

def populations_eq_quantile_plot(pop1, pop2, fig=None, percentilecutoff=5):
    pop1, pop2 = stats.flattendata(pop1), stats.flattendata(pop2)
    assert pop1.ndim == pop2.ndim == 1 or \
            (pop1.ndim == pop2.ndim == 2 and pop1.shape[1] == pop2.shape[1]), \
            'populations must have consistent dimensions'
    D = pop1.shape[1] if pop1.ndim == 2 else 1

    # we want to have the same number of samples
    n1, n2 = pop1.shape[0], pop2.shape[0]
    if n1 != n2:
        # subsample, since interpolation is dangerous
        if n1 < n2:
            pop1, pop2 = pop2, pop1
        np.random.shuffle(pop1)
        pop1 = pop1[:pop2.shape[0]]

    def plot_1d_scaled_quantiles(p1,p2,plot_midline=True):
        # scaled quantiles so that multiple calls line up
        p1.sort(), p2.sort() # NOTE: destructive! but that's cool
        xmin,xmax = general.scoreatpercentile(p1,percentilecutoff), \
                    general.scoreatpercentile(p1,100-percentilecutoff)
        ymin,ymax = general.scoreatpercentile(p2,percentilecutoff), \
                    general.scoreatpercentile(p2,100-percentilecutoff)
        plt.plot((p1-xmin)/(xmax-xmin),(p2-ymin)/(ymax-ymin))

        if plot_midline:
            plt.plot((0,1),(0,1),'k--')
        plt.axis((0,1,0,1))

    if D == 1:
        if fig is None:
            plt.figure()
        plot_1d_scaled_quantiles(pop1,pop2)
    else:
        if fig is None:
            fig = plt.figure()

        if not hasattr(fig,'_quantile_test_projs'):
            firsttime = True
            randprojs = np.random.randn(D,D)
            randprojs /= np.sqrt(np.sum(randprojs**2,axis=1))[:,na]
            projs = np.vstack((np.eye(D),randprojs))
            fig._quantile_test_projs = projs
        else:
            firsttime = False
            projs = fig._quantile_test_projs

        ims1, ims2 = pop1.dot(projs.T), pop2.dot(projs.T)
        for i, (im1, im2) in enumerate(zip(ims1.T,ims2.T)):
            plt.subplot(2,D,i)
            plot_1d_scaled_quantiles(im1,im2,plot_midline=firsttime)

### numerical

# NOTE: a random numerical test should be repeated at the OUTERMOST loop (with
# exception catching) to see if its failures exceed the number expected
# according to the specified pvalue (tests could be repeated via sample
# bootstrapping inside the test, but that doesn't work reliably and random tests
# should have no problem generating new randomness!)

def assert_populations_eq(pop1, pop2):
    assert_populations_eq_moments(pop1,pop2) and \
    assert_populations_eq_komolgorofsmirnov(pop1,pop2)

def assert_populations_eq_moments(pop1, pop2, **kwargs):
    # just first two moments implemented; others are hard to estimate anyway!
    assert_populations_eq_means(pop1,pop2,**kwargs) and \
    assert_populations_eq_variances(pop1,pop2,**kwargs)

def assert_populations_eq_means(pop1, pop2, pval=0.05, msg=None):
    _,p = stats.two_sample_t_statistic(pop1,pop2)
    if np.any(p < pval):
        raise AssertionError(msg or "population means might be different at %0.3f" % pval)

def assert_populations_eq_variances(pop1, pop2, pval=0.05, msg=None):
    _,p = stats.f_statistic(pop1, pop2)
    if np.any(p < pval):
        raise AssertionError(msg or "population variances might be different at %0.3f" % pval)

def assert_populations_eq_komolgorofsmirnov(pop1, pop2, msg=None):
    raise NotImplementedError # TODO


########NEW FILE########
__FILENAME__ = text
import numpy as np
import sys, time

# time.clock() is cpu time of current process
# time.time() is wall time

# to see what this does, try
# for x in progprint_xrange(100):
#     time.sleep(0.01)

# TODO there are probably better progress bar libraries I could use

def progprint_xrange(*args,**kwargs):
    xr = xrange(*args)
    return progprint(xr,total=len(xr),**kwargs)

def progprint(iterator,total=None,perline=25,show_times=True):
    times = []
    idx = 0
    if total is not None:
        numdigits = len('%d' % total)
    for thing in iterator:
        prev_time = time.time()
        yield thing
        times.append(time.time() - prev_time)
        sys.stdout.write('.')
        if (idx+1) % perline == 0:
            if show_times:
                avgtime = np.mean(times)
                if total is not None:
                    sys.stdout.write(('  [ %%%dd/%%%dd, %%7.2fsec avg, %%7.2fsec ETA ]\n' % (numdigits,numdigits)) % (idx+1,total,avgtime,avgtime*(total-(idx+1))))
                else:
                    sys.stdout.write('  [ %d done, %7.2fsec avg ]\n' % (idx+1,avgtime))
            else:
                if total is not None:
                    sys.stdout.write(('  [ %%%dd/%%%dd ]\n' % (numdigits,numdigits) ) % (idx+1,total))
                else:
                    sys.stdout.write('  [ %d ]\n' % (idx+1))
        idx += 1
        sys.stdout.flush()
    print ''
    if show_times:
        print '%7.2fsec avg, %7.2fsec total\n' % (np.mean(times),np.sum(times))

########NEW FILE########
