__FILENAME__ = pymc_test
# pylint: disable=E1101

import pymc as pm
import pymc.distributions as dist
import numpy as np
from numpy.linalg import inv, cholesky as chol
import numpy.linalg as L
import numpy.random as rand

import matplotlib.pyplot as plt

#-------------------------------------------------------------------------------
# Generate MV normal mixture

gen_mean = {
    0 : [0, 5],
    1 : [-10, 0],
    2 : [-10, 10]
}

gen_sd = {
    0 : [0.5, 0.5],
    1 : [.5, 1],
    2 : [1, .25]
}

gen_corr = {
    0 : 0.5,
    1 : -0.5,
    2 : 0
}

group_weights = [0.6, 0.3, 0.1]

def generate_data(n=1e5, k=2, ncomps=3, seed=1):
    rand.seed(seed)
    data_concat = []
    labels_concat = []

    for j in range(ncomps):
        mean = gen_mean[j]
        sd = gen_sd[j]
        corr = gen_corr[j]

        cov = np.empty((k, k))
        cov.fill(corr)
        cov[np.diag_indices(k)] = 1
        cov *= np.outer(sd, sd)

        num = int(n * group_weights[j])
        rvs = pm.rmv_normal_cov(mean, cov, size=num)

        data_concat.append(rvs)
        labels_concat.append(np.repeat(j, num))

    return (np.concatenate(labels_concat),
            np.concatenate(data_concat, axis=0))

N = int(1e5) # n data points per component
K = 2 # ndim
ncomps = 3 # n mixture components

true_labels, data = generate_data(n=N, k=K, ncomps=ncomps)

def plot_2d_mixture(data, labels):
    plt.figure(figsize=(10, 10))
    colors = 'bgr'
    for j in np.unique(labels):
        x, y = data[labels == j].T
        plt.plot(x, y, '%s.' % colors[j], ms=2)


def plot_thetas(sampler):
    plot_2d_mixture(data, true_labels)

    def plot_theta(i):
        x, y = sampler.trace('theta_%d' % i)[:].T
        plt.plot(x, y, 'k.')

    for i in range(3):
        plot_theta(i)

#-------------------------------------------------------------------------------
# set up PyMC model

# priors, fairly vague
prior_mean = data.mean(0)
sigma0 = np.diag([1., 1.])
prior_cov = np.cov(data.T)

# shared hyperparameter?
# theta_tau = pm.Wishart('theta_tau', n=4, Tau=L.inv(sigma0))

# df = pm.DiscreteUniform('df', 3, 50)

thetas = []
taus = []
for j in range(ncomps):
    # need a hyperparameter for degrees of freedom?
    tau = pm.Wishart('C_%d' % j, n=3, Tau=inv(prior_cov))
    theta = pm.MvNormal('theta_%d' % j, mu=prior_mean, tau=inv(2 * prior_cov))

    thetas.append(theta)
    taus.append(tau)

alpha0 = np.ones(3.) / 3
weights = pm.Dirichlet('weights', theta=alpha0)
# labels = pm.Categorical('labels', p=weights, size=len(data))

from pandas.util.testing import set_trace as st
import pdfs
import util

def mixture_loglike(data, thetas, covs, labels):

    n = len(data)
    likes = pdfs.mvnpdf(data, thetas, covs)
    loglike = likes.ravel('F').take(labels * n + np.arange(n)).sum()

    if np.isnan(loglike):
        return -1e300

    return loglike

    if np.isnan(likes).any():
        loglike = 0.
        for j, (theta, cov) in enumerate(zip(thetas, covs)):
            this_data = data[labels == j]
            ch = chol(cov)
            loglike += pm.mv_normal_chol_like(this_data, theta, ch)

        return loglike

def mixture_loglike2(data, thetas, taus, weights):

    n = len(data)

    covs = [inv(tau) for tau in taus]

    likes = pdfs.mvnpdf(data, thetas, covs)
    loglike = (likes * weights).sum()

    # loglike = likes.ravel('F').take(labels * n + np.arange(n)).sum()

    if np.isnan(loglike):
        st()
        return -1e300

    return loglike

    if np.isnan(likes).any():
        loglike = 0.
        for j, (theta, cov) in enumerate(zip(thetas, covs)):
            this_data = data[labels == j]
            loglike += pm.mv_normal_chol_like(this_data, theta, ch)

        return loglike

@pm.deterministic
def adj_weights(weights=weights):
    return np.sort(np.r_[weights, 1 - weights.sum()])

@pm.stochastic(observed=True)
def mixture(value=data, thetas=thetas, taus=taus, weights=adj_weights):
    return mixture_loglike2(value, thetas, taus, weights)

sampler = pm.MCMC(locals())

sampler.sample(iter=3000, burn=100, tune_interval=100, thin=10)


########NEW FILE########
__FILENAME__ = codegen
import pycuda.driver as drv
import pycuda.tools
#import pycuda.autoinit
drv.init()
if drv.Context.get_current() is None:
    import pycuda.autoinit

import numpy
import numpy.linalg as la
import os
from pycuda.compiler import SourceModule
from gpustats.util import get_cufiles_path

class CUDAModule(object):
    """
    Interfaces with PyCUDA

    Parameters
    ----------
    kernel_dict :
    """
    def __init__(self, kernel_dict):
        self.kernel_dict = kernel_dict
        self.support_code = _get_support_code()

        self.all_code = self._get_full_source()
        try:
            #self.pycuda_module = SourceModule(self.all_code)
            # dictionary mapping contexts to their respective loaded code modules
            self.pycuda_modules = { drv.Context.get_current() : SourceModule(self.all_code) }
        except Exception:
            f = open('foo.cu', 'w')
            print >> f, self.all_code
            f.close()
            raise
        #self.curDevice = drv.Context.get_device()

    def _get_full_source(self):
        formatted_kernels = [kern.get_code()
                             for kern in self.kernel_dict.values()]
        return '\n'.join([self.support_code] + formatted_kernels)

    def get_function(self, name):
        # get the module for this context
        context = drv.Context.get_current()
        try:
            mod = self.pycuda_modules[context]
        except KeyError:
            # if it's a new context, init the module
            self.pycuda_modules[context] = SourceModule(self.all_code)
            mod = self.pycuda_modules[context]
        return mod.get_function('k_%s' % name)
        #curDevice = drv.Context.get_device()
        #if self.curDevice != curDevice:
        #    self.pycuda_module = SourceModule(self.all_code)
        #    self.curDevice = curDevice
        #return self.pycuda_module.get_function('k_%s' % name)

def _get_support_code():
    path = os.path.join(get_cufiles_path(), 'support.cu')
    return open(path).read()

def _get_mvcaller_code():
    # for multivariate pdfs
    path = os.path.join(get_cufiles_path(), 'mvcaller.cu')
    return open(path).read()

def _get_univcaller_code():
    # For univariate pdfs
    path = os.path.join(get_cufiles_path(), 'univcaller.cu')
    return open(path).read()

class Kernel(object):

    def __init__(self, name):
        if name is None:
            raise ValueError('Kernel must have a default name')

        self.name = name

    def get_code(self):
        logic = self.get_logic()
        caller = self.get_caller()
        return '\n'.join((logic, caller))

    def get_logic(self, **kwds):
        raise NotImplementedError

    def get_caller(self, **kwds):
        raise NotImplementedError

    def get_name(self, name=None):
        # can override default name, for transforms. this a hack?
        if name is None:
            name = self.name

        return name

class CUFile(Kernel):
    """
    Expose kernel contained in .cu file in the cufiles directory to code
    generation framework. Kernel need only have a template to be able to change
    the name of the generated kernel
    """
    def __init__(self, name, filepath):
        self.full_path = os.path.join(get_cufiles_path(),
                                      filepath)

        Kernel.__init__(self, name)

    def get_code(self):
        code = open(self.full_path).read()
        return code % {'name' : self.name}

class SamplerKernel(Kernel):
    """
    Holds info for measure sample kernel.
    """
    def __init__(self, name, logic_code):
        self.logic_code = logic_code
        Kernel.__init__(self, name)

    def get_logic(self, name=None):
        return self.logic_code

    def get_caller(self, name=None):
        return self._caller % {'name' : self.get_name(name)}

class DensityKernel(Kernel):
    """
    Generate kernel for probability density function
    """

    _caller = _get_univcaller_code()
    def __init__(self, name, logic_code):

        self.logic_code = logic_code

        Kernel.__init__(self, name)

    def get_logic(self, name=None):
        return self.logic_code % {'name' : self.get_name(name)}

    def get_caller(self, name=None):
        return self._caller % {'name' : self.get_name(name)}

class MVDensityKernel(DensityKernel):
    """

    """
    _caller = _get_mvcaller_code()

class Transform(Kernel):
    """
    Enable simple transforms of kernels to compute modified kernel code stub
    """
    def __init__(self, name, kernel):
        self.kernel = kernel
        Kernel.__init__(self, name)

    # XXX: HACK, not general for non-density kernels
    def is_multivariate(self):
        return isinstance(self.kernel, MVDensityKernel)

# flop the right name?

class Flop(Transform):
    op = None

    def get_logic(self, name=None):
        name = self.get_name(name)

        actual_name = '%s_stub' % name
        kernel_logic = self.kernel.get_logic(name=actual_name)

        if self.is_multivariate():
            stub_caller = _mv_stub_caller
        else:
            stub_caller = _univ_stub_caller

        transform_logic = stub_caller % {'name' : name,
                                         'actual_kernel' : actual_name,
                                         'op' : self.op}

        return '\n'.join((kernel_logic, transform_logic))

    def get_caller(self):
        return self.kernel.get_caller(self.name)

_univ_stub_caller = """
__device__ float %(name)s(float* x, float* params) {
    return %(op)s(%(actual_kernel)s(x, params));
}
"""

_mv_stub_caller = """
__device__ float %(name)s(float* x, float* params, int dim) {
    return %(op)s(%(actual_kernel)s(x, params, dim));
}
"""

class Exp(Flop):
    op = 'expf'

class Log(Flop):
    op = 'logf'

class Sqrt(Flop):
    op = 'sqrtf'

_cu_module = None

def get_full_cuda_module():
    import gpustats.kernels as kernels
    global _cu_module

    if _cu_module is None:
        objects = kernels.__dict__

        all_kernels = dict((k, v)
                           for k, v in kernels.__dict__.iteritems()
                           if isinstance(v, Kernel))
        _cu_module = CUDAModule(all_kernels)

    return _cu_module

if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = compat
"""
Python versions of functions for testing purposes etc.
"""
import numpy as np

def python_mvnpdf(data, means, covs):
    from pymc import mv_normal_cov_like as pdf_func

    results = []
    for i, datum in enumerate(data):
        for j, cov in enumerate(covs):
            mean = means[j]
            results.append(pdf_func(datum, mean, cov))

    return np.array(results).reshape((len(data), len(covs))).squeeze()

def python_sample_discrete(pmfs, draws=None):
    T, K = pmfs.shape
    output = np.empty(T, dtype=np.int32)
    if draws is None:
        draws = np.random.rand(T)

    # rescale
    pmfs = (pmfs.T / pmfs.sum(1)).T

    for i in xrange(T):
        the_sum = 0
        draw = draws[i]
        for j in xrange(K):
            the_sum += pmfs[i, j]

            if the_sum >= draw:
                output[i] = j
                break

    return output

if __name__ == '__main__':
    pmfs = np.random.randn(20, 5)
    pmfs = (pmfs.T - pmfs.min(1)).T



########NEW FILE########
__FILENAME__ = kernels
from gpustats.codegen import (MVDensityKernel, DensityKernel, Exp,
                              CUFile)
import gpustats.codegen as cg

# TODO: check for name conflicts!

_log_pdf_mvnormal = """
__device__ float %(name)s(float* data, float* params, int dim) {
  unsigned int LOGDET_OFFSET = dim * (dim + 3) / 2;
  float* mean = params;
  float* sigma = params + dim;
  float mult = params[LOGDET_OFFSET];
  float logdet = params[LOGDET_OFFSET + 1];

  float discrim = 0;
  float sum;
  unsigned int i, j;
  for (i = 0; i < dim; ++i)
  {
    sum = 0;
    for(j = 0; j <= i; ++j) {
      sum += *sigma++ * (data[j] - mean[j]);
    }
    discrim += sum * sum;
  }
  return log(mult) - 0.5f * (discrim + logdet + LOG_2_PI * dim);
}
"""
log_pdf_mvnormal = MVDensityKernel('log_pdf_mvnormal', _log_pdf_mvnormal)
pdf_mvnormal = Exp('pdf_mvnormal', log_pdf_mvnormal)


_log_pdf_normal = """
__device__ float %(name)s(float* x, float* params) {
  // mean stored in params[0]
  float std = params[1];

  // standardize
  float xstd = (*x - params[0]) / std;
  return - (xstd * xstd) / 2 - 0.5f * LOG_2_PI - log(std);
}
"""
log_pdf_normal = DensityKernel('log_pdf_normal', _log_pdf_normal)
pdf_normal = Exp('pdf_normal', log_pdf_normal)

sample_discrete_old = CUFile('sample_discrete_old',
                         'sample_discrete.cu')

sample_discrete_logged_old = CUFile('sample_discrete_logged_old',
                                'sample_discrete_logged.cu')

sample_discrete = CUFile('sample_discrete',
                             'sampleFromMeasureMedium.cu')

########NEW FILE########
__FILENAME__ = multigpu
from threading import Thread

import testmod

class GPUCall(Thread):
    """

    """

    def __init__(self, func, device=0):
        self.func = func
        self.device = device

    def acquire_device(self):
        testmod.set_device(self.device)

    def release_device(self):
        pass

    def run(self):
        self.acquire_device()
        self.func()
        self.release_device()

def make_calls(func, data, devices=None, splits=None):
    """

    Parameters
    ----------

    Returns
    -------

    """
    if splits is None:
        pass

def _execute_calls(calls):
    """

    """
    for call in calls:
        call.start()

    for call in calls:
        call.join()





########NEW FILE########
__FILENAME__ = pdfs
from numpy.random import randn
from numpy.linalg import cholesky as chol
import numpy as np
import numpy.linalg as LA

from pycuda.gpuarray import GPUArray, to_gpu
from pycuda.gpuarray import empty as gpu_empty
import gpustats.kernels as kernels
import gpustats.codegen as codegen
from gpustats.util import transpose as gpu_transpose
reload(codegen)
reload(kernels)
import gpustats.util as util
import pycuda.driver as drv

__all__ = ['mvnpdf', 'mvnpdf_multi', 'normpdf', 'normpdf_multi']

cu_module = codegen.get_full_cuda_module()

#-------------------------------------------------------------------------------
# Invokers for univariate and multivariate density functions conforming to the
# standard API

def _multivariate_pdf_call(cu_func, data, packed_params, get, order,
                           datadim=None):
    packed_params = util.prep_ndarray(packed_params)
    func_regs = cu_func.num_regs

    # Prep the data. Skip if gpudata ...
    if isinstance(data, GPUArray):
        padded_data = data
        if datadim==None:
            ndata, dim = data.shape
        else:
            ndata, dim = data.shape[0], datadim

    else:

        ndata, dim = data.shape
        padded_data = util.pad_data(data)

    nparams = len(packed_params)
    data_per, params_per = util.tune_blocksize(padded_data,
                                               packed_params,
                                               func_regs)

    blocksize = data_per * params_per
    #print 'the blocksize is ' + str(blocksize)
    #print 'data_per ' + str(data_per) + '. params_per ' + str(params_per)
    shared_mem = util.compute_shmem(padded_data, packed_params,
                                    data_per, params_per)
    block_design = (data_per * params_per, 1, 1)
    grid_design = (util.get_boxes(ndata, data_per),
                   util.get_boxes(nparams, params_per))

    # see cufiles/mvcaller.cu
    design = np.array(((data_per, params_per) + # block design
                       padded_data.shape + # data spec
                       (dim,) + # non-padded number of data columns
                       packed_params.shape), # params spec
                      dtype=np.int32)

    if nparams == 1:
        gpu_dest = gpu_empty(ndata, dtype=np.float32)
        #gpu_dest = to_gpu(np.zeros(ndata, dtype=np.float32))
    else:
        gpu_dest = gpu_empty((ndata, nparams), dtype=np.float32, order='F')
        #gpu_dest = to_gpu(np.zeros((ndata, nparams), dtype=np.float32, order='F'))

    # Upload data if not already uploaded
    if not isinstance(padded_data, GPUArray):
        gpu_padded_data = to_gpu(padded_data)
    else:
        gpu_padded_data = padded_data

    gpu_packed_params = to_gpu(packed_params)

    params = (gpu_dest, gpu_padded_data, gpu_packed_params) + tuple(design)
    kwds = dict(block=block_design, grid=grid_design, shared=shared_mem)
    cu_func(*params, **kwds)

    gpu_packed_params.gpudata.free()
    if get:
        if order=='F':
            return gpu_dest.get()
        else:
            return np.asarray(gpu_dest.get(), dtype=np.float32, order='C')
        #output = gpu_dest.get()
        #if nparams > 1:
        #    output = output.reshape((nparams, ndata), order='C').T
        #return output
    else:
        if order=='F' or nparams==1:
            return gpu_dest
        else:
            res = gpu_transpose(util.GPUarray_reshape(gpu_dest, (nparams, ndata), "C"))
            gpu_dest.gpudata.free()
            return res
            #return gpu_transpose(gpu_dest.reshape(nparams, ndata, 'C'))

def _univariate_pdf_call(cu_func, data, packed_params, get):
    ndata = len(data)
    nparams = len(packed_params)

    func_regs = cu_func.num_regs

    packed_params = util.prep_ndarray(packed_params)

    data_per, params_per = util.tune_blocksize(data,
                                               packed_params,
                                               func_regs)

    shared_mem = util.compute_shmem(data, packed_params,
                                    data_per, params_per)

    block_design = (data_per * params_per, 1, 1)
    grid_design = (util.get_boxes(ndata, data_per),
                   util.get_boxes(nparams, params_per))

    # see cufiles/univcaller.cu

    #gpu_dest = to_gpu(np.zeros((ndata, nparams), dtype=np.float32))
    gpu_dest = gpu_empty((ndata, nparams), dtype=np.float32)
    gpu_data = data if isinstance(data, GPUArray) else to_gpu(data)
    gpu_packed_params = to_gpu(packed_params)

    design = np.array(((data_per, params_per) + # block design
                       (len(data),) +
                       packed_params.shape), # params spec
                      dtype=np.int32)

    cu_func(gpu_dest,
            gpu_data, gpu_packed_params, design[0],
            design[1], design[2], design[3], design[4],
            block=block_design, grid=grid_design, shared=shared_mem)

    if get:
        output = gpu_dest.get()
        if nparams > 1:
            output = output.reshape((nparams, ndata), order='C').T
        return output
    else:
        return gpu_dest

#-------------------------------------------------------------------------------
# Multivariate normal

def mvnpdf(data, mean, cov, weight=None, logged=True, get=True, order="F",
           datadim=None):
    """
    Multivariate normal density

    Parameters
    ----------

    Returns
    -------
    """
    return mvnpdf_multi(data, [mean], [cov],
                        logged=logged, get=get, order=order,
                        datadim=datadim).squeeze()

def mvnpdf_multi(data, means, covs, weights=None, logged=True,
                 get=True, order="F", datadim=None):
    """
    Multivariate normal density with multiple sets of parameters

    Parameters
    ----------
    data : ndarray (n x k)
    covs : sequence of 2d k x k matrices (length j)
    weights : ndarray (length j)
        Multiplier for component j, usually will sum to 1

    get = False leaves the result on the GPU
    without copying back.

    If data has already been padded, the orginal dimension
    must be passed in datadim

    It data is of GPUarray type, the data is assumed to be
    padded, and datadim will need to be passed if padding
    was needed.

    Returns
    -------
    densities : n x j
    """
    if logged:
        cu_func = cu_module.get_function('log_pdf_mvnormal')
    else:
        cu_func = cu_module.get_function('pdf_mvnormal')

    assert(len(covs) == len(means))

    ichol_sigmas = [LA.inv(chol(c)) for c in covs]
    logdets = [-2.0*np.log(c.diagonal()).sum() for c in ichol_sigmas]

    if weights is None:
        weights = np.ones(len(means))

    packed_params = _pack_mvnpdf_params(means, ichol_sigmas, logdets, weights)

    return _multivariate_pdf_call(cu_func, data, packed_params,
                                  get, order,datadim)

def _pack_mvnpdf_params(means, ichol_sigmas, logdets, weights):
    to_pack = []
    for m, ch, ld, w in zip(means, ichol_sigmas, logdets, weights):
        to_pack.append(_pack_mvnpdf_params_single(m, ch, ld, w))

    return np.vstack(to_pack)

def _pack_mvnpdf_params_single(mean, ichol_sigma, logdet, weight=1):
    PAD_MULTIPLE = 16
    k = len(mean)
    mean_len = k
    ichol_len = k * (k + 1) / 2
    mch_len = mean_len + ichol_len

    packed_dim = util.next_multiple(mch_len + 2, PAD_MULTIPLE)

    packed_params = np.empty(packed_dim, dtype=np.float32)
    packed_params[:mean_len] = mean

    packed_params[mean_len:mch_len] = ichol_sigma[np.tril_indices(k)]
    packed_params[mch_len:mch_len + 2] = weight, logdet

    return packed_params

#-------------------------------------------------------------------------------
# Univariate normal

def normpdf(x, mean, std, logged=True, get=True):
    """
    Normal (Gaussian) density

    Parameters
    ----------

    Returns
    -------
    """
    return normpdf_multi(x, [mean], [std], logged=logged, get=get).squeeze()

def normpdf_multi(x, means, std, logged=True, get=True):
    if logged:
        cu_func = cu_module.get_function('log_pdf_normal')
    else:
        cu_func = cu_module.get_function('pdf_normal')

    packed_params = np.c_[means, std]

    if not isinstance(x, GPUArray):
        x = util.prep_ndarray(x)

    return _univariate_pdf_call(cu_func, x, packed_params, get)

if __name__ == '__main__':
    import gpustats.compat as compat

    n = 1e5
    k = 8

    np.random.seed(1)
    data = randn(n, k).astype(np.float32)
    mean = randn(k).astype(np.float32)
    cov = util.random_cov(k).astype(np.float32)

    result = mvnpdf_multi(data, [mean, mean], [cov, cov])
    # pyresult = compat.python_mvnpdf(data, [mean], [cov]).squeeze()
    # print result - pyresult

########NEW FILE########
__FILENAME__ = sampler
import numpy as np

import gpustats.kernels as kernels
import gpustats.codegen as codegen
import gpustats.util as util
import pycuda.driver as drv
from pycuda.gpuarray import GPUArray, to_gpu
from pycuda.gpuarray import empty as gpu_empty
from pycuda.curandom import rand as curand

# reload(kernels)
# reload(codegen)

cu_module = codegen.get_full_cuda_module()

def sample_discrete(densities, logged=False,
                        return_gpuarray=False):

    """
    Takes a categorical sample from the unnormalized univariate
    densities defined in the rows of 'densities'

    Parameters
    ---------
    densities : ndarray or gpuarray (n, k)
    logged: boolean indicating whether densities is on the
    log scale ...

    Returns
    -------
    indices : ndarray or gpuarray (if return_gpuarray=True)
    of length n and dtype = int32
    """

    from gpustats.util import info

    n, k = densities.shape
    # prep data
    if isinstance(densities, GPUArray):
        if densities.flags.f_contiguous:
            gpu_densities = util.transpose(densities)
        else:
            gpu_densities = densities
    else:
        densities = util.prep_ndarray(densities)
        gpu_densities = to_gpu(densities)

    # get gpu function
    cu_func = cu_module.get_function('sample_discrete')

    # setup GPU data
    gpu_random = to_gpu(np.asarray(np.random.rand(n), dtype=np.float32))
    gpu_dest = gpu_empty(n, dtype=np.int32)
    dims = np.array([n,k,logged],dtype=np.int32)

    if info.max_block_threads<1024:
        x_block_dim = 16
    else:
        x_block_dim = 32

    y_block_dim = 16
    # setup GPU call
    block_design = (x_block_dim, y_block_dim, 1)
    grid_design = (int(n/y_block_dim) + 1, 1)

    shared_mem = 4 * ( (x_block_dim+1)*y_block_dim +  
                     2 * y_block_dim )  

    cu_func(gpu_densities, gpu_random, gpu_dest, 
            dims[0], dims[1], dims[2], 
            block=block_design, grid=grid_design, shared=shared_mem)

    gpu_random.gpudata.free()
    if return_gpuarray:
        return gpu_dest
    else:
        res = gpu_dest.get()
        gpu_dest.gpudata.free()
        return res


## depreciated 
def sample_discrete_old(in_densities, logged=False, pad=False,
                    return_gpuarray=False):
    """
    Takes a categorical sample from the unnormalized univariate
    densities defined in the rows of 'densities'

    Parameters
    ---------
    densities : ndarray or gpuarray (n, k)
    logged: boolean indicating whether densities is on the
    log scale ...

    Returns
    -------
    indices : ndarray or gpuarray (if return_gpuarray=True)
    of length n and dtype = int32
    """

    if pad:
        if logged:
            densities = util.pad_data_mult16(in_densities, fill=1)
        else:
            densities = util.pad_data_mult16(in_densities, fill=0)

    else:
        densities = in_densities

    n, k = densities.shape

    if logged:
        cu_func = cu_module.get_function('sample_discrete_logged_old')
    else:
        cu_func = cu_module.get_function('sample_discrete_old')

    if isinstance(densities, GPUArray):
        if densities.flags.f_contiguous:
            gpu_densities = util.transpose(densities)
        else:
            gpu_densities = densities
    else:
        densities = util.prep_ndarray(densities)
        gpu_densities = to_gpu(densities)

    # setup GPU data
    #gpu_random = curand(n)
    gpu_random = to_gpu(np.asarray(np.random.rand(n), dtype=np.float32))
    #gpu_dest = to_gpu(np.zeros(n, dtype=np.float32))
    gpu_dest = gpu_empty(n, dtype=np.float32)
    stride = gpu_densities.shape[1]
    if stride % 2 == 0:
        stride += 1
    dims = np.array([n,k, gpu_densities.shape[1], stride],dtype=np.int32)


    # optimize design ...
    grid_design, block_design = _tune_sfm(n, stride, cu_func.num_regs)

    shared_mem = 4 * (block_design[0] * stride + 
                     1 * block_design[0])

    cu_func(gpu_densities, gpu_random, gpu_dest, 
            dims[0], dims[1], dims[2], dims[3],
            block=block_design, grid=grid_design, shared=shared_mem)

    gpu_random.gpudata.free()
    if return_gpuarray:
        return gpu_dest
    else:
        res = gpu_dest.get()
        gpu_dest.gpudata.free()
        return res

def _tune_sfm(n, stride, func_regs):
    """
    Outputs the 'opimal' block and grid configuration
    for the sample discrete kernel.
    """
    from gpustats.util import info

    #info = DeviceInfo()
    comp_cap = info.compute_cap
    max_smem = info.shared_mem * 0.8
    max_threads = int(info.max_block_threads * 0.5)
    max_regs = 0.9 * info.max_registers

    # We want smallest dim possible in x dimsension while
    # still reading mem correctly

    if comp_cap[0] == 1:
        xdim = 16
    else:
        xdim = 32


    def sfm_config_ok(xdim, ydim, stride, func_regs, max_regs, max_smem, max_threads):
        ok = 4*(xdim*stride + 1*xdim) < max_smem and func_regs*ydim*xdim < max_regs
        return ok and xdim*ydim <= max_threads

    ydim = 2
    while sfm_config_ok(xdim, ydim, stride, func_regs, max_regs, max_smem, max_threads):
        ydim += 1

    ydim -= 1

    nblocks = int(n/xdim) + 1

    return (nblocks,1), (xdim,ydim,1)

if __name__ == '__main__':

    n = 100
    k = 5
    dens = np.log(np.abs(np.random.randn(k))) - 200
    densities = [dens.copy() for _ in range(n)]
    dens = np.exp(dens + 200)
    densities = np.asarray(densities)

    labels = sample_discrete(densities, logged=True)
    mu = np.dot(dens / dens.sum(), np.arange(k))
    print mu, labels.mean()

########NEW FILE########
__FILENAME__ = test_pdfs
import nose
import sys
import unittest

from numpy.random import randn
from numpy.linalg import inv, cholesky as chol
from numpy.testing import assert_almost_equal, assert_equal
import numpy as np

import scipy.stats as sp_stats

import gpustats as gps
import gpustats.compat as compat
import gpustats.util as util

DECIMAL_6 = 6
DECIMAL_5 = 5
DECIMAL_4 = 4
DECIMAL_3 = 3
DECIMAL_2 = 2

np.set_printoptions(suppress=True)

def _make_test_case(n=1000, k=4, p=1):
    data = randn(n, k)
    covs = [util.random_cov(k) for _ in range(p)]
    means = [randn(k) for _ in range(p)]
    return data, means, covs

# debugging...

def _compare_multi(n, k, p):
    data, means, covs = _make_test_case(n, k, p)

    # cpu in PyMC
    pyresult = compat.python_mvnpdf(data, means, covs)

    # gpu
    result = gps.mvnpdf_multi(data, means, covs)

    return result, pyresult

def _compare_single(n, k):
    data, means, covs = _make_test_case(n, k, 1)

    mean = means[0]
    cov = covs[0]

    # cpu in PyMC
    pyresult = compat.python_mvnpdf(data, [mean], [cov]).squeeze()
    # gpu

    result = gps.mvnpdf(data, mean, cov)
    return result, pyresult

class TestMVN(unittest.TestCase):
    # ndata, dim, ncomponents
    test_cases = [(1000, 4, 1),
                  (1000, 4, 16),
                  (1000, 4, 32),
                  (1000, 4, 64),
                  (1000, 7, 64),
                  (1000, 8, 64),
                  (1000, 14, 32),
                  (1000, 16, 128),
                  (250, 25, 32),
                  (10, 15, 2),
                  (500000, 5, 12)]

    def _check_multi(self, n, k, p):
        a, b = _compare_multi(n, k, p)
        assert_almost_equal(a, b, DECIMAL_2)

    def _check_single(self, n, k):
        a, b = _compare_single(n, k)
        assert_almost_equal(a, b, DECIMAL_2)

    def test_multi(self):
        for n, k, p in self.test_cases:
            self._check_multi(n, k, p)

    def test_single(self):
        for n, k, p in self.test_cases:
            self._check_single(n, k)

class TestUnivariate(unittest.TestCase):
    def test_normal(self):
        test_cases = [
            (100, 0, 1),
            (100, .5, 2.5),
            (10, 5, 3),
            (2000, 1, 4)
        ]
        for n, mean, std in test_cases:
            data = randn(n)
            pyresult = sp_stats.norm.pdf(data, loc=mean, scale=std)

            result = gps.normpdf(data, mean, std, logged=True)
            assert_almost_equal(result, np.log(pyresult), DECIMAL_5)

    def test_normal_multi(self):
        means = np.random.randn(5)
        scales = np.ones(5)

        data = np.random.randn(10)
        result = gps.normpdf_multi(data, means, scales, logged=True)

        pyresult = np.empty_like(result)
        for i, (m, sc) in enumerate(zip(means, scales)):
            pyresult[:, i] = sp_stats.norm.pdf(data, loc=m, scale=sc)
        assert_almost_equal(result, np.log(pyresult), DECIMAL_5)

if __name__ == '__main__':
    # nose.runmodule(argv=['', '--pdb', '-v', '--pdb-failure'])
    _compare_multi(500000, 4, 128)
    pass

########NEW FILE########
__FILENAME__ = test_samplers
import nose
import sys
import unittest

from numpy.random import rand
from numpy.linalg import inv, cholesky as chol
from numpy.testing import assert_almost_equal, assert_equal
import numpy as np

import scipy.stats as sp_stats

import gpustats as gps
import gpustats.sampler as gpusamp
import gpustats.compat as compat
import gpustats.util as util

DECIMAL_6 = 6
DECIMAL_5 = 5
DECIMAL_4 = 4
DECIMAL_3 = 3
DECIMAL_2 = 2
DECIMAL_1 = 1

np.set_printoptions(suppress=True)

def _make_test_densities(n=10000, k=4):
    dens = rand(k)
    densities = [dens.copy() for _ in range(n)]
    return np.asarray(densities)
    #return (densities.T - densities.sum(1)).T

def _compare_discrete(n, k):
    densities = _make_test_densities(n, k)
    dens = densities[0,:].copy() / densities[0,:].sum()
    expected_mu = np.dot(np.arange(k), dens)

    labels = gpusamp.sample_discrete(densities, logged=False)
    est_mu = labels.mean()
    return est_mu, expected_mu

def _compare_logged(n, k):
    densities = np.log(_make_test_densities(n, k))
    dens = np.exp((densities[0,:] - densities[0,:].max()))
    dens = dens / dens.sum()
    expected_mu = np.dot(np.arange(k), dens)

    labels = gpusamp.sample_discrete(densities, logged=True)
    est_mu = labels.mean()
    return est_mu, expected_mu


class TestDiscreteSampler(unittest.TestCase):
    test_cases = [(100000, 4),
                  (100000, 9),
                  (100000, 16),
                  (100000, 20),
                  (1000000, 35)]

    def _check_discrete(self, n, k):
        a, b = _compare_discrete(n, k)
        assert_almost_equal(a, b, DECIMAL_1)

    def _check_logged(self, n, k):
        a, b = _compare_logged(n, k)
        assert_almost_equal(a, b, DECIMAL_1)

    def test_discrete(self):
        for n, k in self.test_cases:
            self._check_discrete(n, k)

    def test_logged(self):
        for n, k in self.test_cases:
            self._check_logged(n, k)


if __name__ == '__main__':
    print 'starting sampler'
    a, b = _compare_logged(1000000, 35)
    print a
    print b

    
    

########NEW FILE########
__FILENAME__ = util
import numpy as np
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
import pycuda
import scipy.linalg as LA
drv.init()
if drv.Context.get_current() is None:
    import pycuda.autoinit
from pycuda.compiler import SourceModule

def threadSafeInit(device = 0):
    """
    If gpustats (or any other pycuda work) is used inside a 
    multiprocessing.Process, this function must be used inside the
    thread to clean up invalid contexts and create a new one on the 
    given device. Assumes one GPU per thread.
    """

    import atexit
    drv.init() # just in case

    ## clean up all contexts. most will be invalid from
    ## multiprocessing fork
    import os; import sys
    clean = False
    while not clean:
        _old_ctx = drv.Context.get_current()
        if _old_ctx is None:
            clean = True
        else:
            ## detach: will give warnings to stderr if invalid
            _old_cerr = os.dup(sys.stderr.fileno())
            _nl = os.open(os.devnull, os.O_RDWR)
            os.dup2(_nl, sys.stderr.fileno())
            _old_ctx.detach() 
            sys.stderr = os.fdopen(_old_cerr, "wb")
            os.close(_nl)
    from pycuda.tools import clear_context_caches
    clear_context_caches()
        
    ## init a new device
    dev = drv.Device(device)
    ctx = dev.make_context()

    ## pycuda.autoinit exitfunc is bad now .. delete it
    exit_funcs = atexit._exithandlers
    for fn in exit_funcs:
        if hasattr(fn[0], 'func_name'):
            if fn[0].func_name == '_finish_up':
                exit_funcs.remove(fn)
            if fn[0].func_name == 'clean_all_contexts': # avoid duplicates
                exit_funcs.remove(fn)

    ## make sure we clean again on exit
    atexit.register(clean_all_contexts)


def clean_all_contexts():

    ctx = True
    while ctx is not None:
        ctx = drv.Context.get_current()
        if ctx is not None:
            ctx.detach()

    from pycuda.tools import clear_context_caches
    clear_context_caches()
    

def GPUarray_reshape(garray, shape=None, order="C"):
    if shape is None:
        shape = garray.shape
    return gpuarray.GPUArray(
        shape=shape,
        dtype=garray.dtype,
        allocator=garray.allocator,
        base=garray,
        gpudata=int(garray.gpudata),
        order=order)

def GPUarray_order(garray, order="F"):
    """
    will set the order of garray in place
    """
    if order=="F":
        if garray.flags.f_contiguous:
            exit
        else:
            garray.strides = gpuarray._f_contiguous_strides(
                garray.dtype.itemsize, garray.shape)
            garray.flags.f_contiguous = True
            garray.flags.c_contiguous = False
    elif order=="C":
        if garray.flags.c_contiguous:
            exit
        else:
            garray.strides = gpuarray._c_contiguous_strides(
                garray.dtype.itemsize, garray.shape)
            garray.flags.c_contiguous = True
            garray.flags.f_contiguous = False
            


_dev_attr = drv.device_attribute
## TO DO: should be different for each device .. assumes they are the same
class DeviceInfo(object):

    def __init__(self):
        #self._dev = pycuda.autoinit.device
        #self._dev = drv.Device(dev)
        self._dev = drv.Context.get_device()
        self._attr = self._dev.get_attributes()

        self.max_block_threads = self._attr[_dev_attr.MAX_THREADS_PER_BLOCK]
        self.shared_mem = self._attr[_dev_attr.MAX_SHARED_MEMORY_PER_BLOCK]
        self.warp_size = self._attr[_dev_attr.WARP_SIZE]
        self.max_registers = self._attr[_dev_attr.MAX_REGISTERS_PER_BLOCK]
        self.compute_cap = self._dev.compute_capability()
        self.max_grid_dim = (self._attr[_dev_attr.MAX_GRID_DIM_X],
                             self._attr[_dev_attr.MAX_GRID_DIM_Y])

info = DeviceInfo()

HALF_WARP = 16

def random_cov(dim):
    from pymc.distributions import rwishart
    return LA.inv(rwishart(dim, np.eye(dim)))

def unvech(v):
    # quadratic formula, correct fp error
    rows = .5 * (-1 + np.sqrt(1 + 8 * len(v)))
    rows = int(np.round(rows))

    result = np.zeros((rows, rows))
    result[np.triu_indices(rows)] = v
    result = result + result.T

    # divide diagonal elements by 2
    result[np.diag_indices(rows)] /= 2

    return result

def pad_data_mult16(data, fill=0):
    """
    Pad data to be a multiple of 16 for discrete sampler.
    """

    if type(data) == gpuarray:
        data = data.get()

    n, k = data.shape

    km = int(k/16) + 1

    newk = km*16
    if newk != k:
        padded_data = np.zeros((n, newk), dtype=np.float32)
        if fill!=0:
            padded_data = padded_data + fill

        padded_data[:,:k] = data

        return padded_data
    else:
        return prep_ndarray(data)

def pad_data(data):
    """
    Pad data to avoid bank conflicts on the GPU-- dimension should not be a
    multiple of the half-warp size (16)
    """
    if type(data) == gpuarray:
        data = data.get()

    n, k = data.shape

    if not k % HALF_WARP:
        pad_dim = k + 1
    else:
        pad_dim = k

    if k != pad_dim:
        padded_data = np.empty((n, pad_dim), dtype=np.float32)
        padded_data[:, :k] = data

        return padded_data
    else:
        return prep_ndarray(data)

def prep_ndarray(arr):
    # is float32 and contiguous?
    if not arr.dtype == np.float32 or not arr.flags.contiguous:
        arr = np.array(arr, dtype=np.float32, order='C')

    return arr




def tune_blocksize(data, params, func_regs):
    """
    For multivariate distributions-- what's the optimal block size given the
    gpu?

    Parameters
    ----------
    data : ndarray
    params : ndarray

    Returns
    -------
    (data_per, params_per) : (int, int)
    """
    #info = DeviceInfo()

    max_smem = info.shared_mem * 0.9
    max_threads = int(info.max_block_threads * 0.5)
    max_regs = info.max_registers
    max_grid = int(info.max_grid_dim[0])

    params_per = 64#max_threads
    if (len(params) < params_per):
        params_per = _next_pow2(len(params), info.max_block_threads)

    min_data_per = data.shape[0] / max_grid;
    data_per0 = _next_pow2( max( max_threads / params_per, min_data_per ), 512);
    data_per = data_per0

    def _can_fit(data_per, params_per):
        ok = compute_shmem(data, params, data_per, params_per) <= max_smem
        ok = ok and data_per*params_per <= max_threads
        return ok and func_regs*data_per*params_per <= max_regs

    while True:
        while not _can_fit(data_per, params_per):
            if data_per <= min_data_per:
                break

            if params_per > 1:
                # reduce number of parameters first
                params_per /= 2
            else:
                # can't go any further, have to do less data
                data_per /= 2

        if data_per <= min_data_per:
            # we failed somehow. start over
            data_per = 2 * data_per0
            params_per /= 2
            continue
        else:
            break

    while _can_fit(2 * data_per, params_per):
        #if 2 * data_per * params_per < max_threads:
            data_per *= 2
        #else:
            # hit block size limit
        #    break

    #import pdb; pdb.set_trace()
    return data_per, params_per

def get_boxes(n, box_size):
    # how many boxes of size box_size are needed to hold n things
    return int((n + box_size - 1) / box_size)

def compute_shmem(data, params, data_per, params_per):
    result_space = data_per * params_per

    data_dim = 1 if len(data.shape) == 1 else data.shape[1]
    params_dim = len(params) if len(params.shape) == 1 else params.shape[1]

    param_space = params_dim * params_per
    data_space = data_dim * data_per
    return 4 * (result_space + param_space + data_space)

def _next_pow2(k, pow2):
    while k <= pow2 / 2:
        pow2 /= 2
    return pow2

def next_multiple(k, mult):
    if k % mult:
        return k + (mult - k % mult)
    else:
        return k

def get_cufiles_path():
    import os.path as pth
    basepath = pth.abspath(pth.split(__file__)[0])
    return pth.join(basepath, 'cufiles')


from pycuda.tools import context_dependent_memoize

@context_dependent_memoize
def _get_transpose_kernel():

    #info = DeviceInfo()
    if info.max_block_threads >= 1024:
        t_block_size = 32
    else:
        t_block_size = 16

    import os.path as pth
    mod = SourceModule( 
        open(pth.join(get_cufiles_path(), "transpose.cu")).read() % { "block_size" : t_block_size })

    func = mod.get_function("transpose")
    func.prepare("PPii") #, block=(t_block_size, t_block_size, 1))
    return t_block_size, func
    

    #from pytools import Record
    #class TransposeKernelInfo(Record): pass
    #return TransposeKernelInfo(func=func, 
    #                           block_size=t_block_size,
    #                           granularity=t_block_size)
    

def _transpose(tgt, src):
    block_size, func = _get_transpose_kernel()
    

    h, w = src.shape
    assert tgt.shape == (w, h)
    #assert w % block_size == 0
    #assert h % block_size == 0
    
    gw = int(np.ceil(float(w) / block_size))
    gh = int(np.ceil(float(h) / block_size))
    gz = int(1)

    ### 3D grids are needed for larger data ... should be comming soon ...
    #while gw > info.max_grid_dim[0]:
    #    gz += 1
    #    gw = int(np.ceil(float(w) / (gz * block_size) ))

    func.prepared_call(
        (gw, gh),
        (block_size, block_size, 1),
        tgt.gpudata, src.gpudata, w, h)


def transpose(src):
    h, w = src.shape

    result = gpuarray.empty((w, h), dtype=src.dtype)
    _transpose(result, src)
    del src
    return result

########NEW FILE########
__FILENAME__ = build_cython
#/usr/bin/env python

from distutils.extension import Extension
from numpy.distutils.core import setup
from Cython.Distutils import build_ext
import numpy

def get_cuda_include():
    return '/usr/local/cuda/include'

pyx_ext = Extension('testmod', ['cytest.pyx'],
                    include_dirs=[numpy.get_include(),
                                  get_cuda_include()],
                    library_dirs=['.'],
                    libraries=['gpustats'])

setup(name='testmod', description='',
      ext_modules=[pyx_ext],
      cmdclass = {
          'build_ext' : build_ext
      })

########NEW FILE########
__FILENAME__ = pdfs
from numpy.linalg import inv, cholesky as chol
import numpy as np

import testmod
import util

def mvnpdf(data, means, covs):
    '''
    Compute multivariate normal log pdf

    Parameters
    ----------

    Returns
    -------

    '''
    logdets = [np.log(np.linalg.det(c)) for c in covs]
    ichol_sigmas = [inv(chol(c)) for c in covs]

    packed_params = util.pack_params(means, ichol_sigmas, logdets)
    packed_data = util.pad_data(data)
    return testmod.mvn_call(packed_data, packed_params,
                            data.shape[1])

########NEW FILE########
__FILENAME__ = scratch
from numpy.random import randn
from numpy.linalg import cholesky as chol
import numpy as np
import numpy.linalg as L
import scipy.special as sp
import pymc.flib as flib
import time
import testmod
import util
import pdb

def gen_testdata(n=100, k=4):
    # use static data to compare to R
    data = randn(n, k)
    mean = randn(k)

    np.savetxt('test_data', data)
    np.savetxt('test_mean', mean)

def load_testdata():
    data = np.loadtxt('test_data')
    mean = np.loadtxt('test_mean')
    cov = np.cov(data.T)


    return data, mean, cov

def bench(cpu_func, gpu_func, gruns=50):
    """

    """

    _s = time.clock()
    for i in xrange(gruns):
        gpu_func()

    gpu_speed = (time.clock() - _s) / gruns

    _s = time.clock()
    cpu_func()
    cpu_speed = (time.clock() - _s)
    print 'CPU speed: %.3f' % (cpu_speed * 1000)
    print 'GPU speed: %.3f' % (gpu_speed * 1000)
    print cpu_speed / gpu_speed

if __name__ == '__main__':
    testmod.set_device(0)

    n = 1e3
    k = 16

    data = randn(n, k).astype(np.float32)
    mean = randn(k)
    cov = np.array(util.random_cov(k), dtype=np.float32)

    j = 32

    padded_data = util.pad_data(data)

    chol_sigma = chol(cov)
    ichol_sigma = L.inv(chol_sigma)
    logdet = np.log(np.linalg.det(cov))

    means = (mean,) * j
    covs = (ichol_sigma,) * j
    logdets = (logdet,) * j

    packed_params = util.pack_params(means, covs, logdets)

    cpu_func = lambda: testmod.cpu_mvnpdf(padded_data, packed_params, k).squeeze()
    gpu_func = lambda: testmod._mvnpdf(padded_data, packed_params, k).squeeze()

    print cpu_func()
    print gpu_func()

    # bench(cpu_func, gpu_func, gruns=50)

########NEW FILE########
__FILENAME__ = util
import numpy as np
import pymc.distributions as pymc_dist

PAD_MULTIPLE = 16
HALF_WARP = 16

def random_cov(dim):
    return pymc_dist.rinverse_wishart(dim, np.eye(dim))

def unvech(v):
    # quadratic formula, correct fp error
    rows = .5 * (-1 + np.sqrt(1 + 8 * len(v)))
    rows = int(np.round(rows))

    result = np.zeros((rows, rows))
    result[np.triu_indices(rows)] = v
    result = result + result.T

    # divide diagonal elements by 2
    result[np.diag_indices(rows)] /= 2

    return result

def next_multiple(k, p):
    if k % p:
        return k + (p - k % p)

    return k

def pad_data(data):
    """
    Pad data to avoid bank conflicts on the GPU-- dimension should not be a
    multiple of the half-warp size (16)
    """
    n, k = data.shape

    if not k % HALF_WARP:
        pad_dim = k + 1
    else:
        pad_dim = k

    if k != pad_dim:
        padded_data = np.empty((n, pad_dim), dtype=np.float32)
        padded_data[:, :k] = data

        return padded_data
    else:
        return prep_ndarray(data)

def prep_ndarray(arr):
    # is float32 and contiguous?
    if not arr.dtype == np.float32 or not arr.flags.contiguous:
        arr = np.array(arr, dtype=np.float32)

    return arr

def pack_params(means, chol_sigmas, logdets):
    to_pack = []
    for m, ch, ld in zip(means, chol_sigmas, logdets):
        to_pack.append(pack_pdf_params(m, ch, ld))

    return np.vstack(to_pack)

def pack_pdf_params(mean, chol_sigma, logdet):
    '''


    '''
    k = len(mean)
    mean_len = k
    chol_len = k * (k + 1) / 2
    mch_len = mean_len + chol_len

    packed_dim = next_multiple(mch_len + 2, PAD_MULTIPLE)

    packed_params = np.empty(packed_dim, dtype=np.float32)
    packed_params[:mean_len] = mean

    packed_params[mean_len:mch_len] = chol_sigma[np.tril_indices(k)]
    packed_params[mch_len:mch_len + 2] = 1, logdet

    return packed_params

########NEW FILE########
__FILENAME__ = bench
from pandas import *

import numpy as np

from pycuda.gpuarray import to_gpu
import gpustats
import gpustats.util as util
from scipy.stats import norm
import timeit

data = np.random.randn(1000000)
mean = 20
std = 5

univ_setup = """
import numpy as np
from pycuda.gpuarray import to_gpu
k = 8
means = np.random.randn(k)
stds = np.abs(np.random.randn(k))

mean = 20
std = 5
import gpustats
from scipy.stats import norm
cpu_data = np.random.randn(%d)
gpu_data = cpu_data
"""

univ_setup_gpuarray = univ_setup + """
gpu_data = to_gpu(cpu_data)
"""

multivar_setup = """
# from __main__ import data, mean, std
import gpustats
import gpustats.util as util
import numpy as np
import testmod
from pycuda.gpuarray import to_gpu
import testmod
from numpy.linalg import cholesky as chol
import numpy.linalg as L


def next_multiple(k, p):
    if k.__mod__(p):
        return k + (p - k.__mod__(p))

    return k

PAD_MULTIPLE = 16
HALF_WARP = 16


def pad_data(data):
    n, k = data.shape

    if not k.__mod__(HALF_WARP):
        pad_dim = k + 1
    else:
        pad_dim = k

    if k != pad_dim:
        padded_data = np.empty((n, pad_dim), dtype=np.float32)
        padded_data[:, :k] = data

        return padded_data
    else:
        return prep_ndarray(data)

def prep_ndarray(arr):
    # is float32 and contiguous?
    if not arr.dtype == np.float32 or not arr.flags.contiguous:
        arr = np.array(arr, dtype=np.float32)

    return arr

def pack_params(means, chol_sigmas, logdets):
    to_pack = []
    for m, ch, ld in zip(means, chol_sigmas, logdets):
        to_pack.append(pack_pdf_params(m, ch, ld))

    return np.vstack(to_pack)

def pack_pdf_params(mean, chol_sigma, logdet):
    k = len(mean)
    mean_len = k
    chol_len = k * (k + 1) / 2
    mch_len = mean_len + chol_len

    packed_dim = next_multiple(mch_len + 2, PAD_MULTIPLE)

    packed_params = np.empty(packed_dim, dtype=np.float32)
    packed_params[:mean_len] = mean

    packed_params[mean_len:mch_len] = chol_sigma[np.tril_indices(k)]
    packed_params[mch_len:mch_len + 2] = 1, logdet

    return packed_params

k = %d

dim = 15
means = np.random.randn(k, dim)
covs = [util.random_cov(dim) for _ in xrange(k)]

cpu_data = np.random.randn(%d, dim)
gpu_data = cpu_data
"""

multivar_setup_gpuarray = multivar_setup + """
gpu_data = to_gpu(cpu_data)
"""

LOG_2_PI = np.log(2 * np.pi)

# def mvnpdf(data, mean, cov):
#     ichol_sigma = np.asarray(np.linalg.inv(np.linalg.cholesky(cov)))
#     # ichol_sigma = np.tril(ichol_sigma)
#     logdet = np.log(np.linalg.det(cov))
#     return [_mvnpdf(x, mean, ichol_sigma, logdet)
#             for x in data]

# def _mvnpdf(x, mean, ichol_sigma, logdet):
#     demeaned = x - mean
#     discrim = ((ichol_sigma * demeaned) ** 2).sum()
#     # discrim = np.dot(demeaned, np.dot(ichol_sigma, demeaned))
#     return - 0.5 * (discrim + logdet + LOG_2_PI * dim)

def get_timeit(stmt, setup, iter=10):
    return timeit.Timer(stmt, setup).timeit(number=iter) / iter

def compare_timings_single(n, setup=univ_setup):
    gpu = "gpustats.normpdf(gpu_data, mean, std, logged=False)"
    cpu = "norm.pdf(cpu_data, loc=mean, scale=std)"
    setup = setup % n
    return {'GPU' : get_timeit(gpu, setup, iter=1000),
            'CPU' : get_timeit(cpu, setup)}

def compare_timings_multi(n, setup=univ_setup):
    gpu = "gpustats.normpdf_multi(gpu_data, means, stds, logged=False)"
    cpu = """
for m, s in zip(means, stds):
    norm.pdf(cpu_data, loc=m, scale=s)
"""
    setup = setup % n
    return {'GPU' : get_timeit(gpu, setup, iter=100),
            'CPU' : get_timeit(cpu, setup)}


def mvcompare_timings(n, k=1, setup=multivar_setup):
    gpu = "gpustats.mvnpdf_multi(gpu_data, means, covs, logged=False)"
    cpu = """
ichol_sigmas = [L.inv(chol(sig)) for sig in covs]
logdets = [np.log(np.linalg.det(sig)) for sig in covs]
params = pack_params(means, covs, logdets)
testmod.cpu_mvnpdf(cpu_data, params, dim)
    """
    setup = setup % (k, n)
    return {'GPU' : get_timeit(gpu, setup, iter=100),
            'CPU' : get_timeit(cpu, setup)}

def get_timing_results(timing_f):
    lengths = [100, 1000, 10000, 100000, 1000000]

    result = {}
    for n in lengths:
        print n
        result[n] = timing_f(n)
    result = DataFrame(result).T
    result['Speedup'] = result['CPU'] / result['GPU']
    return result

# mvsingle = get_timing_results(mvcompare_timings)
# comp_gpu = lambda n: mvcompare_timings(n, setup=multivar_setup_gpuarray)
# mvsingle_gpu = get_timing_results(comp_gpu)
# multi_comp = lambda n: mvcompare_timings(n, k=16)
# mvmulti = get_timing_results(multi_comp)
# multi_comp_gpu = lambda n: mvcompare_timings(n, k=16,
#                                        setup=multivar_setup_gpuarray)
# mvmulti_gpu = get_timing_results(multi_comp_gpu)

single = get_timing_results(compare_timings_single)
comp_gpu = lambda n: compare_timings_single(n, setup=univ_setup_gpuarray)
single_gpu = get_timing_results(comp_gpu)
multi = get_timing_results(compare_timings_multi)
comp_gpu = lambda n: compare_timings_multi(n, setup=univ_setup_gpuarray)
multi_gpu = get_timing_results(comp_gpu)

data = DataFrame({
    'Single' : single['Speedup'],
    'Single (GPUArray)' : single_gpu['Speedup'],
    'Multi' : multi['Speedup'],
    'Multi (GPUArray)' : multi_gpu['Speedup'],
})


mvdata = DataFrame({
    'Single' : mvsingle['Speedup'],
    'Single (GPUArray)' : mvsingle_gpu['Speedup'],
    'Multi' : mvmulti['Speedup'],
    'Multi (GPUArray)' : mvmulti_gpu['Speedup'],
})

if __name__ == '__main__':
    import gpustats
    import numpy as np
    from scipy.stats import norm
    import testmod
    from numpy.linalg import cholesky as chol
    import numpy.linalg as L

    # dim = 15
    # k = 8
    # means = np.random.randn(k, dim)
    # covs = [np.asarray(util.random_cov(dim)) for _ in xrange(k)]

    # cpu_data = np.random.randn(100000, dim)
    # gpu_data = to_gpu(cpu_data)

    # ichol_sigmas = [L.inv(chol(sig)) for sig in covs]
    # logdets = [np.log(np.linalg.det(sig)) for sig in covs]
    # packed_params = pack_params(means, covs, logdets)

    # pdfs = gpustats.mvnpdf(cpu_data, means[0], covs[0])
    # pdfs = testmod.cpu_mvnpdf(cpu_data, packed_params, 15)


########NEW FILE########
