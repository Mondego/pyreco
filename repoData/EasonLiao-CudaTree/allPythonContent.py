__FILENAME__ = benchmark_all
#!/usr/bin/python
from cudatree import RandomForestClassifier, load_data, timer
from cudatree import util
from hybridforest import RandomForestClassifier as hybridForest
import numpy as np
import math
#from PyWiseRF import WiseRF

debug = False
verbose = False
bootstrap = False
n_estimators = 100

def benchmark_cuda(dataset, bfs_threshold = None):
  x_train, y_train = load_data(dataset)
  #Just use this forest to compile the code.
  throw_away = RandomForestClassifier(n_estimators = 1, bootstrap = bootstrap, verbose = False, 
        max_features = None, debug = debug)
  throw_away.fit(x_train, y_train, bfs_threshold = bfs_threshold)

  with timer("%s benchmark cuda (bfs_threshold = %s)" % (dataset, bfs_threshold)): 
    forest = RandomForestClassifier(n_estimators = n_estimators, bootstrap = bootstrap, verbose = verbose, 
        max_features = None, debug = debug)
    forest.fit(x_train, y_train, bfs_threshold = bfs_threshold)
  forest = None


def benchmark_hybrid(dataset, bfs_threshold = None):
  x_train, y_train = load_data(dataset)
  
  #Just use this forest to compile the code.
  throw_away = hybridForest(n_estimators = 2, bootstrap = bootstrap,  
        max_features = None)
  throw_away.fit(x_train, y_train, bfs_threshold = bfs_threshold)

  with timer("%s benchmark hybrid (bfs_threshold = %s)" % (dataset, bfs_threshold)): 
    forest = hybridForest(n_estimators = n_estimators, bootstrap = bootstrap, n_jobs = 2,
        max_features = None)
    forest.fit(x_train, y_train, bfs_threshold = bfs_threshold)
  forest = None

benchmark_hybrid("covtype", None)
#benchmark_cuda("pamap", None)
#benchmark_cuda("cf100", 10000)
#benchmark_cuda("inet", 1000)
#benchmark_hybrid("inet", 5000)
benchmark_hybrid("poker")
#benchmark_hybrid("inet")

#benchmark_hybrid("cf100")
benchmark_hybrid("cf100")
#benchmark_hybrid("covtype")
#benchmark_hybrid("poker")
#benchmark_hybrid("inet")

"""
benchmark_hybrid("cf100")
benchmark_hybrid("kdd")
benchmark_hybrid("covtype")
benchmark_hybrid("cf10")
benchmark_cuda("cf100", True)
benchmark_cuda("kdd", True)
benchmark_cuda("covtype", True)
benchmark_cuda("cf10", True)
"""

########NEW FILE########
__FILENAME__ = base_tree
import numpy as np
from util import get_best_dtype
from pycuda import gpuarray
import math
from util import start_timer, end_timer
from pycuda import driver

class BaseTree(object):
  def __init__(self):
    self.root = None
    self.max_depth = None

  def print_tree(self):
    def recursive_print(idx, depth):
      if self.left_children[idx] == 0 and \
          self.right_children[idx] == 0:
        print "[LEAF] Depth: %s, Value: %s" % \
            (depth, self.values_array[idx])
      else:
        print "[NODE] Depth: %s, Feature: %s, Threshold: %f" %\
            (depth, self.feature_idx_array[idx], 
            self.feature_threshold_array[idx])
        recursive_print(self.left_children[idx], depth + 1)
        recursive_print(self.right_children[idx], depth + 1) 
    recursive_print(0, 0)

  def __gpu_predict(self, val):
    idx = 0
    while True:
      threshold = self.threshold_array[idx]
      threshold_idx = self.feature_array[idx]
      left_idx = self.left_child_array[idx]
      right_idx = self.right_child_array[idx]

      if left_idx != 0 and right_idx != 0: 
        #Means it has children
        if val[threshold_idx] < threshold:
          idx = left_idx
        else:
          idx = right_idx
      else:
        return self.value_array[idx]

  def gpu_predict(self, inputs, predict_kernel):
    def get_grid_size(n_samples):
      blocks_need = int(math.ceil(float(n_samples) / 16))
      MAX_GRID = 65535
      gy = 1
      gx = MAX_GRID
      if gx >= blocks_need:
        gx = blocks_need
      else:
        gy = int(math.ceil(float(blocks_need) / gx))
      return (gx, gy)
    
    n_predict = inputs.shape[0]    
    predict_gpu = gpuarray.to_gpu(inputs)
    left_child_gpu = gpuarray.to_gpu(self.left_children)
    right_child_gpu = gpuarray.to_gpu(self.right_children)
    threshold_gpu = gpuarray.to_gpu(self.feature_threshold_array)
    value_gpu = gpuarray.to_gpu(self.values_array)
    feature_gpu = gpuarray.to_gpu(self.feature_idx_array)
    
    predict_res_gpu = gpuarray.zeros(n_predict, \
                                    dtype=self.dtype_labels)
    grid = get_grid_size(n_predict)
    
    predict_kernel.prepared_call(
                  grid,
                  (512, 1, 1),
                  left_child_gpu.ptr,
                  right_child_gpu.ptr,
                  feature_gpu.ptr,
                  threshold_gpu.ptr,
                  value_gpu.ptr,
                  predict_gpu.ptr,
                  predict_res_gpu.ptr,
                  self.n_features,
                  n_predict) 

    return predict_res_gpu.get()

  def _find_most_common_label(self, x):
    return np.argmax(np.bincount(x))

########NEW FILE########
__FILENAME__ = datasource
import cPickle
import numpy as np
from os import path
from sklearn.datasets import load_digits,load_iris,load_diabetes,fetch_covtype 
import sklearn

_img_data = None

def load_data(ds_name):
  data_dir = path.dirname(__file__) + "/../data/"
  global _img_data
  if ds_name == "digits":
    ds = load_digits()
    x_train = ds.data
    y_train = ds.target
  elif ds_name == "iris":
    ds = load_iris()
    x_train = ds.data
    y_train = ds.target
  elif ds_name == "diabetes":
    ds = load_diabetes()
    x_train = ds.data 
    y_train = ds.target > 140 
  elif ds_name == "covtype":
    ds = fetch_covtype(download_if_missing = True)
    x_train = ds.data 
    y_train = ds.target 
  elif ds_name == "cf10":
    with open(data_dir + "data_batch_1", "r") as f:
      ds = cPickle.load(f)
      x_train = ds['data']
      y_train = np.array(ds['labels'])
  elif ds_name == "cf100":
    with open(data_dir + "train", "r") as f:
      ds = cPickle.load(f)
      x_train = ds['data']
      y_train = np.array(ds['fine_labels'])
  elif ds_name == "cd10_test":
    with open(data_dir + "test_batch", "r") as f:
      ds = cPickle.load(f)
      x_train = ds['data']
      y_train = np.array(ds['labels'])
  elif ds_name == "cf100_test":
    with open(data_dir + "test", "r") as f:
      ds = cPickle.load(f)
      x_train = ds['data']
      y_train = np.array(ds['fine_labels'])
  elif ds_name == "inet":
    if _img_data is None:
      with open("/ssd/imagenet-subset.pickle", "r") as f:
        _img_data = cPickle.load(f)
    return _img_data['x'][0:10000],  _img_data['Y'][0:10000] 
  elif ds_name == "inet_test":
    if _img_data is None:
      with open("/ssd/imagenet-subset.pickle", "r") as f:
        _img_data = cPickle.load(f)
    return _img_data['x'][10000:],  _img_data['Y'][10000:] 
  elif ds_name == "kdd":
    data = np.load(data_dir + "data.npy")
    x_train = data[:, :-1]
    y_train = data[:, -1]
  elif ds_name == "poker":
    data = sklearn.datasets.fetch_mldata("poker")
    x_train = data.data
    y_train = data.target
  elif ds_name == "pamap":
    data = np.load(data_dir + "pamap.npz")
    x_train = data['x']
    y_train = data['y']
  else:
    assert False, "Unrecognized data set name %s" % ds_name
  return x_train, y_train




########NEW FILE########
__FILENAME__ = random_forest
import numpy as np
from random_tree import RandomClassifierTree
from util import timer, get_best_dtype, dtype_to_ctype, mk_kernel, mk_tex_kernel, compile_module
from pycuda import gpuarray
from pycuda import driver
from util import start_timer, end_timer, show_timings
from parakeet import jit
import math

import parakeet
#parakeet.config.backend = "c"

@jit
def convert_result(tran_table, res):
    return np.array([tran_table[i] for i in res])

#Restore pickled forest, just pickle the trees, the kernel is NOT pickled
def restore_forest(trees, dtype_labels):
  n_estimators = len(trees)
  f = RandomForestClassifier(n_estimators)
  f._trees = trees
  f.dtype_labels = dtype_labels
  return f


class RandomForestClassifier(object):
  """A random forest classifier.

    A random forest is a meta estimator that fits a number of classifical
    decision trees on various sub-samples of the dataset and use averaging
    to improve the predictive accuracy and control over-fitting.
    
    Usage:
    See RandomForestClassifier.fit
  """ 
  COMPUTE_THREADS_PER_BLOCK = 128
  RESHUFFLE_THREADS_PER_BLOCK = 256
  BFS_THREADS = 64
  MAX_BLOCK_PER_FEATURE = 50
  MAX_BLOCK_BFS = 10000
  
  def __reduce__(self):
    return restore_forest, (self._trees, self.dtype_labels)

  def __init__(self, 
              n_estimators = 10, 
              max_features = None, 
              min_samples_split = 1, 
              bootstrap = True, 
              verbose = False, 
              debug = False):
    """Construce multiple trees in the forest.

    Parameters
    ----------
    n_estimator : integer, optional (default=10)
        The number of trees in the forest.

    max_features : int or None, optional (default="sqrt(n_features)")
        The number of features to consider when looking for the best split:
          - If None, then `max_features=sqrt(n_features)`.

    min_samples_split : integer, optional (default=1)
        The minimum number of samples required to split an internal node.
        Note: this parameter is tree-specific.
    
    bootstrap : boolean, optional (default=True)
        Whether use bootstrap samples
    
    verbose : boolean, optional (default=False) 
        Display the time of each tree construction takes if verbose = True.
    
    Returns
    -------
    None
    """    
    self.max_features = max_features
    self.min_samples_split = min_samples_split
    self.bootstrap = bootstrap
    self.verbose = verbose
    self.n_estimators = n_estimators
    self.debug = debug
    self._trees = list()

  def __compact_labels(self, target):
    def check_is_compacted(x):
      return x.size == int(np.max(x)) + 1 and int(np.min(x)) == 0
    def convert_to_dict(x):
      d = {}
      for i, val in enumerate(x):
        d[val] = i
      return d

    self.compt_table = np.unique(target)
    self.compt_table.sort()        
    if not check_is_compacted(self.compt_table):
      trans_table = convert_to_dict(self.compt_table)
      for i, val in enumerate(target):
        target[i] = trans_table[val]

  def __init_bootstrap_kernel(self):
    """ Compile the kernels and GPUArrays needed to generate the bootstrap samples"""
    ctype_indices = dtype_to_ctype(self.dtype_indices)
    self.bootstrap_fill= mk_kernel((ctype_indices,), "bootstrap_fill",
        "bootstrap_fill.cu")
    self.bootstrap_reshuffle, tex_ref = mk_tex_kernel((ctype_indices, 128), "bootstrap_reshuffle",
        "tex_mark", "bootstrap_reshuffle.cu")
    
    self.bootstrap_fill.prepare("PPii")
    self.bootstrap_reshuffle.prepare("PPPi")
    self.mark_table.bind_to_texref_ext(tex_ref)

  def _get_sorted_indices(self, sorted_indices):
    """ Generate sorted indices, if bootstrap == False, 
    then the sorted indices is as same as original sorted indices """
    
    sorted_indices_gpu_original = self.sorted_indices_gpu.copy()

    if not self.bootstrap:
      return sorted_indices_gpu_original, sorted_indices.shape[1]
    else:
      sorted_indices_gpu = gpuarray.empty((self.n_features, self.stride), dtype = self.dtype_indices)
      random_sample_idx = np.unique(np.random.randint(
        0, self.stride, size = self.stride)).astype(self.dtype_indices)
      random_sample_idx_gpu = gpuarray.to_gpu(random_sample_idx)
      n_samples = random_sample_idx.size
      
      self.bootstrap_fill.prepared_call(
                (1, 1),
                (512, 1, 1),
                random_sample_idx_gpu.ptr,
                self.mark_table.ptr,
                n_samples,
                self.stride)

      self.bootstrap_reshuffle.prepared_call(
                (self.n_features, 1),
                (128, 1, 1),
                self.mark_table.ptr,
                sorted_indices_gpu_original.ptr,
                sorted_indices_gpu.ptr,
                self.stride)
      
      return sorted_indices_gpu, n_samples 
  
  def _allocate_arrays(self):
    #allocate gpu arrays and numpy arrays.
    if self.max_features < 4:
      imp_size = 4
    else:
      imp_size = self.max_features
    
    #allocate gpu arrays
    self.impurity_left = gpuarray.empty(imp_size, dtype = np.float32)
    self.impurity_right = gpuarray.empty(self.max_features, dtype = np.float32)
    self.min_split = gpuarray.empty(self.max_features, dtype = self.dtype_counts)
    self.label_total = gpuarray.empty(self.n_labels, self.dtype_indices)  
    self.label_total_2d = gpuarray.zeros(self.max_features * (self.MAX_BLOCK_PER_FEATURE + 1) * self.n_labels, 
        self.dtype_indices)
    self.impurity_2d = gpuarray.empty(self.max_features * self.MAX_BLOCK_PER_FEATURE * 2, np.float32)
    self.min_split_2d = gpuarray.empty(self.max_features * self.MAX_BLOCK_PER_FEATURE, self.dtype_counts)
    self.features_array_gpu = gpuarray.empty(self.n_features, np.uint16)
    self.mark_table = gpuarray.empty(self.stride, np.uint8) 

    #allocate numpy arrays
    self.idx_array = np.zeros(2 * self.n_samples, dtype = np.uint32)
    self.si_idx_array = np.zeros(self.n_samples, dtype = np.uint8)
    self.nid_array = np.zeros(self.n_samples, dtype = np.uint32)
    self.values_idx_array = np.zeros(2 * self.n_samples, dtype = self.dtype_indices)
    self.values_si_idx_array = np.zeros(2 * self.n_samples, dtype = np.uint8)
    self.threshold_value_idx = np.zeros(2, self.dtype_indices)
    self.min_imp_info = driver.pagelocked_zeros(4, dtype = np.float32)  
    self.features_array = driver.pagelocked_zeros(self.n_features, dtype = np.uint16)
    self.features_array[:] = np.arange(self.n_features, dtype = np.uint16)


  def _release_arrays(self):
    self.impurity_left = None
    self.impurity_right = None
    self.min_split = None
    self.label_total = None
    self.label_total_2d = None
    self.min_split_2d = None
    self.impurity_2d = None
    self.feature_mask = None
    self.features_array_gpu = None
    
    #Release kernels
    self.fill_kernel = None
    self.scan_reshuffle_tex = None 
    self.scan_total_kernel = None
    self.comput_label_loop_rand_kernel = None
    self.find_min_kernel = None
    self.scan_total_bfs = None
    self.comput_bfs = None
    self.fill_bfs = None
    self.reshuffle_bfs = None
    self.reduce_bfs_2d = None
    self.comput_bfs_2d = None
    self.get_thresholds = None
    self.scan_reduce = None
    self.mark_table = None
    
    #Release numpy arrays
    self.idx_array = None
    self.si_idx_array = None
    self.nid_array = None
    self.values_idx_array = None
    self.values_si_idx_array = None
    self.threshold_value_idx = None
    self.min_imp_info = None
    self.features_array = None


  def fit_init(self, samples, target):
    assert isinstance(samples, np.ndarray)
    assert isinstance(target, np.ndarray)
    assert samples.size / samples[0].size == target.size
    target = target.copy()
    self.__compact_labels(target)
    
    self.n_samples = len(target)
    self.n_labels = self.compt_table.size 
    self.dtype_indices = get_best_dtype(target.size)

    if self.dtype_indices == np.dtype(np.uint8):
      self.dtype_indices = np.dtype(np.uint16)

    self.dtype_counts = self.dtype_indices
    self.dtype_labels = get_best_dtype(self.n_labels)
    self.dtype_samples = samples.dtype
    
    samples = np.require(np.transpose(samples), requirements = 'C')
    target = np.require(np.transpose(target), dtype = self.dtype_labels, requirements = 'C') 
    
    self.n_features = samples.shape[0]
    self.stride = target.size
    
    if self.COMPUTE_THREADS_PER_BLOCK > self.stride:
      self.COMPUTE_THREADS_PER_BLOCK = 32
    if self.RESHUFFLE_THREADS_PER_BLOCK > self.stride:
      self.RESHUFFLE_THREADS_PER_BLOCK = 32
    
    samples_gpu = gpuarray.to_gpu(samples)
    labels_gpu = gpuarray.to_gpu(target) 
    
    sorted_indices = np.argsort(samples).astype(self.dtype_indices)
    self.sorted_indices_gpu = gpuarray.to_gpu(sorted_indices)
      
    if self.max_features is None:
      self.max_features = int(math.ceil(np.sqrt(self.n_features)))
    
    self._allocate_arrays()
    self.__compile_kernels()
       
    if self.bootstrap:
      self.__init_bootstrap_kernel()
    
    #get default best bfs threshold
    self.bfs_threshold = self._get_best_bfs_threshold(self.n_labels, self.n_samples, self.max_features)
    self.sorted_indices = sorted_indices
    self.target = target
    self.samples = samples
    self.samples_gpu = samples_gpu
    self.labels_gpu = labels_gpu
    assert self.max_features > 0 and self.max_features <= self.n_features
    

  def fit_release(self):
    self.target = None
    self.samples = None
    self.samples_gpu = None
    self.labels_gpu = None
    self.sorted_indices_gpu = None
    self.sorted_indices = None
    self._release_arrays()
     
  def _get_best_bfs_threshold(self, n_labels, n_samples, max_features):
    # coefficients estimated by regression over best thresholds for randomly generated data sets 
    # estimate from GTX 580:
    bfs_threshold = int(3702 + 1.58 * n_labels + 0.05766 * n_samples + 21.84 * self.max_features)
    # estimate from Titan: 
    bfs_threshold = int(4746 + 4 * n_labels + 0.0651 * n_samples - 75 * max_features)
    # don't let it grow too big
    bfs_threshold = min(bfs_threshold, 50000)
    # ...or too small
    bfs_threshold = max(bfs_threshold, 2000)
    #bfs_threshold = max(bfs_threshold, 2000)
    return bfs_threshold 


  def fit(self, samples, target, bfs_threshold = None):
    """Construce multiple trees in the forest.

    Parameters
    ----------
    samples:numpy.array of shape = [n_samples, n_features]
            The training input samples.

    target: numpy.array of shape = [n_samples]
            The training input labels.
    
    bfs_threshold: integer, optional (default= n_samples / 40)
            The n_samples threshold of changing to bfs
    
    Returns
    -------
    self : object
      Returns self
    """
    self.fit_init(samples, target)
    
    if bfs_threshold is not None: 
      self.bfs_threshold = bfs_threshold
    
    if self.verbose: 
      print "bsf_threadshold : %d; bootstrap : %r; min_samples_split : %d" % (self.bfs_threshold, 
          self.bootstrap,  self.min_samples_split)
      print "n_samples : %d; n_features : %d; n_labels : %d; max_features : %d" % (self.stride, 
          self.n_features, self.n_labels, self.max_features)

  
    self._trees = [RandomClassifierTree(self) for i in xrange(self.n_estimators)] 

    for i, tree in enumerate(self._trees):
      si, n_samples = self._get_sorted_indices(self.sorted_indices)

      if self.verbose: 
        with timer("Tree %s" % (i,)):
          tree.fit(self.samples, self.target, si, n_samples)   
        print ""
      else:
        tree.fit(self.samples, self.target, si, n_samples)   
    
    self.fit_release()
    return self


  def predict(self, x):
    """Predict labels for giving samples.

    Parameters
    ----------
    x:numpy.array of shape = [n_samples, n_features]
            The predicting input samples.
    
    Returns
    -------
    y: Array of shape [n_samples].
        The predicted labels.
    """
    x = np.require(x.copy(), requirements = "C")
    res = np.ndarray((len(self._trees), x.shape[0]), dtype = self.dtype_labels)

    for i, tree in enumerate(self._trees):
      res[i] =  tree.gpu_predict(x, self.predict_kernel)

    res =  np.array([np.argmax(np.bincount(res[:,i])) for i in xrange(res.shape[1])]) 
    if hasattr(self, "compt_table"):
      res = convert_result(self.compt_table, res) 

    return res

  def predict_proba(self, x):
    x = np.require(x.copy(), requirements = "C")
    res = np.ndarray((len(self._trees), x.shape[0]), dtype = self.dtype_labels)
    res_proba = np.ndarray((x.shape[0], self.n_labels), np.float64)
    
    for i, tree in enumerate(self._trees):
      res[i] =  tree.gpu_predict(x, self.predict_kernel)
    
    for i in xrange(x.shape[0]):
      tmp_res = np.bincount(res[:, i])
      tmp_res.resize(self.n_labels)
      res_proba[i] = tmp_res.astype(np.float64) / len(self._trees)

    return res_proba

  def score(self, X, Y):
    return np.mean(self.predict(X) == Y) 

  def __compile_kernels(self):
    ctype_indices = dtype_to_ctype(self.dtype_indices)
    ctype_labels = dtype_to_ctype(self.dtype_labels)
    ctype_counts = dtype_to_ctype(self.dtype_counts)
    ctype_samples = dtype_to_ctype(self.dtype_samples)
    n_labels = self.n_labels
    n_threads = self.COMPUTE_THREADS_PER_BLOCK
    n_shf_threads = self.RESHUFFLE_THREADS_PER_BLOCK
    
    """ DFS module """
    dfs_module = compile_module("dfs_module.cu", (n_threads, n_shf_threads, n_labels, 
      ctype_samples, ctype_labels, ctype_counts, ctype_indices, self.MAX_BLOCK_PER_FEATURE, 
      self.debug))
    
    const_stride = dfs_module.get_global("stride")[0]
    driver.memcpy_htod(const_stride, np.uint32(self.stride))

    self.find_min_kernel = dfs_module.get_function("find_min_imp")
    self.find_min_kernel.prepare("PPPi")
  
    self.fill_kernel = dfs_module.get_function("fill_table")
    self.fill_kernel.prepare("PiiP")
    
    self.scan_reshuffle_tex = dfs_module.get_function("scan_reshuffle")
    self.scan_reshuffle_tex.prepare("PPii")
    tex_ref = dfs_module.get_texref("tex_mark")
    self.mark_table.bind_to_texref_ext(tex_ref) 
      
    self.comput_total_2d = dfs_module.get_function("compute_2d")
    self.comput_total_2d.prepare("PPPPPPPii")

    self.reduce_2d = dfs_module.get_function("reduce_2d")
    self.reduce_2d.prepare("PPPPPi")
    
    self.scan_total_2d = dfs_module.get_function("scan_gini_large")
    self.scan_total_2d.prepare("PPPPii")
    
    self.scan_reduce = dfs_module.get_function("scan_reduce")
    self.scan_reduce.prepare("Pi")

    """ BFS module """
    bfs_module = compile_module("bfs_module.cu", (self.BFS_THREADS, n_labels, ctype_samples,
      ctype_labels, ctype_counts, ctype_indices,  self.debug))

    const_stride = bfs_module.get_global("stride")[0]
    const_n_features = bfs_module.get_global("n_features")[0]
    const_max_features = bfs_module.get_global("max_features")[0]
    driver.memcpy_htod(const_stride, np.uint32(self.stride))
    driver.memcpy_htod(const_n_features, np.uint16(self.n_features))
    driver.memcpy_htod(const_max_features, np.uint16(self.max_features))

    self.scan_total_bfs = bfs_module.get_function("scan_bfs")
    self.scan_total_bfs.prepare("PPPP")

    self.comput_bfs_2d = bfs_module.get_function("compute_2d")
    self.comput_bfs_2d.prepare("PPPPPPPPP")

    self.fill_bfs = bfs_module.get_function("fill_table")
    self.fill_bfs.prepare("PPPPP")

    self.reshuffle_bfs = bfs_module.get_function("scan_reshuffle")
    tex_ref = bfs_module.get_texref("tex_mark")
    self.mark_table.bind_to_texref_ext(tex_ref) 
    self.reshuffle_bfs.prepare("PPP") 

    self.reduce_bfs_2d = bfs_module.get_function("reduce")
    self.reduce_bfs_2d.prepare("PPPPPPi")
    
    self.get_thresholds = bfs_module.get_function("get_thresholds")
    self.get_thresholds.prepare("PPPPP")
   
    self.predict_kernel = mk_kernel(
        params = (ctype_indices, ctype_samples, ctype_labels), 
        func_name = "predict", 
        kernel_file = "predict.cu", 
        prepare_args = "PPPPPPPii")
  
    self.bfs_module = bfs_module
    self.dfs_module = dfs_module

########NEW FILE########
__FILENAME__ = random_tree
import pycuda.autoinit
import pycuda.driver as cuda
from pycuda import gpuarray
import numpy as np
import math
from util import total_times, compile_module, mk_kernel, mk_tex_kernel, timer
from util import  dtype_to_ctype, get_best_dtype, start_timer, end_timer
from base_tree import BaseTree
from pycuda import driver
import random
from parakeet import jit
from util import start_timer, end_timer, show_timings
import sys
import util

def sync():
  if False:
    driver.Context.synchronize()

#Restore the pickled tree
def restore_tree(left_children,
                  right_children,
                  feature_threshold_array,
                  values_array,
                  feature_idx_array,
                  dtype_labels,
                  n_features):
  tree = RandomClassifierTree()
  tree.left_children = left_children
  tree.right_children = right_children
  tree.feature_threshold_array = feature_threshold_array
  tree.dtype_labels = dtype_labels
  tree.values_array = values_array
  tree.feature_idx_array = feature_idx_array
  tree.n_features = n_features
  return tree

@jit
def  _shuffle(x, r):
  for i in xrange(1, len(x)):
    j = np.fmod(r[i], i)
    old_xj = x[j]
    x[j] = x[i]
    x[i] = old_xj

def shuffle(x):
    r = np.random.randint(0, len(x), len(x))
    _shuffle(x, r)

@jit
def decorate(target, 
              si_0, 
              si_1, 
              values_idx_array, 
              values_si_idx_array, 
              values_array, 
              n_nodes):
  
  for i in range(n_nodes):
    if values_si_idx_array[i] == 0:
      values_array[i] = target[si_0[values_idx_array[i]]] 
    else:
      values_array[i] = target[si_1[values_idx_array[i]]] 

@jit
def turn_to_leaf(nid, start_idx, idx, values_idx_array, values_si_idx_array):
  values_idx_array[nid] = start_idx
  values_si_idx_array[nid] = idx

#bfs loop called in bfs construction.
@jit
def bfs_loop(queue_size, 
            n_nodes, 
            max_features, 
            new_idx_array, 
            idx_array, 
            new_si_idx_array, 
            new_nid_array, 
            left_children, 
            right_children, 
            feature_idx_array, 
            feature_threshold_array, 
            nid_array, 
            imp_min, 
            min_split, 
            feature_idx, 
            si_idx_array, 
            threshold, 
            min_samples_split,
            values_idx_array, 
            values_si_idx_array):
  
  new_queue_size = 0
  for i in range(queue_size):
    if si_idx_array[i] == 1:
      si_idx = 0
      si_idx_ = 1
    else:
      si_idx = 1
      si_idx_ = 0
    
    nid = nid_array[i]
    row = feature_idx[i]
    col = min_split[i]     
    left_imp = imp_min[2 * i]
    right_imp = imp_min[2 * i + 1]

    start_idx = idx_array[2 * i]
    stop_idx = idx_array[2 * i + 1] 
    feature_idx_array[nid] = row
    feature_threshold_array[nid] = threshold[i] 
  
    if left_imp + right_imp == 4.0:
      turn_to_leaf(nid, start_idx, si_idx_, values_idx_array, values_si_idx_array)
    else:
      left_nid = n_nodes
      n_nodes += 1
      right_nid = n_nodes
      n_nodes += 1
      right_children[nid] = right_nid
      left_children[nid] = left_nid

      if left_imp != 0.0:
        n_samples_left = col + 1 - start_idx 
        if n_samples_left < min_samples_split:
          turn_to_leaf(left_nid, 
                        start_idx, 
                        si_idx, 
                        values_idx_array, 
                        values_si_idx_array)
        else:
          new_idx_array[2 * new_queue_size] = start_idx
          new_idx_array[2 * new_queue_size + 1] = col + 1
          new_si_idx_array[new_queue_size] = si_idx
          new_nid_array[new_queue_size] = left_nid
          new_queue_size += 1
      else:
        turn_to_leaf(left_nid, 
                      start_idx, 
                      si_idx, 
                      values_idx_array, 
                      values_si_idx_array)

      if right_imp != 0.0:
        n_samples_right = stop_idx - col - 1
        if n_samples_right < min_samples_split:
          turn_to_leaf(right_nid, 
                        col + 1, 
                        si_idx, 
                        values_idx_array, 
                        values_si_idx_array)
        else:
          new_idx_array[2 * new_queue_size] = col + 1
          new_idx_array[2 * new_queue_size + 1] = stop_idx
          new_si_idx_array[new_queue_size] = si_idx
          new_nid_array[new_queue_size] = right_nid
          new_queue_size += 1
      else:
        turn_to_leaf(right_nid, 
                      col + 1, 
                      si_idx, 
                      values_idx_array, 
                      values_si_idx_array)   
  
  return n_nodes, new_queue_size, new_idx_array, new_si_idx_array, new_nid_array


class RandomClassifierTree(BaseTree): 
  def __init__(self, 
              forest = None):
    if forest == None:
      return

    self.n_labels = forest.n_labels
    self.stride = forest.stride
    self.dtype_labels = forest.dtype_labels
    self.dtype_samples = forest.dtype_samples
    self.dtype_indices = forest.dtype_indices
    self.dtype_counts = forest.dtype_counts
    self.n_features = forest.n_features
    self.COMPUTE_THREADS_PER_BLOCK = forest.COMPUTE_THREADS_PER_BLOCK
    self.RESHUFFLE_THREADS_PER_BLOCK = forest.RESHUFFLE_THREADS_PER_BLOCK
    self.samples_gpu = forest.samples_gpu
    self.labels_gpu = forest.labels_gpu
    self.compt_table = forest.compt_table
    self.max_features = forest.max_features
    self.min_samples_split =  forest.min_samples_split
    self.bfs_threshold = forest.bfs_threshold
    self.forest = forest
    self.BFS_THREADS = self.forest.BFS_THREADS
    self.MAX_BLOCK_PER_FEATURE = self.forest.MAX_BLOCK_PER_FEATURE
    self.MAX_BLOCK_BFS = self.forest.MAX_BLOCK_BFS
    if forest.debug == False:
      self.debug = 0
    else:
      self.debug = 1
     
  def __shuffle_feature_indices(self):
    if self.debug == 0:
      shuffle(self.features_array)
  

  def __reduce__(self):
    assert self.left_children is not None
    assert self.right_children is not None
    assert self.feature_threshold_array is not None
    assert self.values_array is not None
    assert self.feature_idx_array is not None
    assert self.dtype_labels is not None
    return restore_tree, (self.left_children,
                            self.right_children,
                            self.feature_threshold_array,
                            self.values_array,
                            self.feature_idx_array,
                            self.dtype_labels,
                            self.n_features) 

  def __compile_kernels(self):
    """ DFS module """
    f = self.forest
    self.find_min_kernel = f.find_min_kernel  
    self.fill_kernel = f.fill_kernel 
    self.scan_reshuffle_tex = f.scan_reshuffle_tex 
    self.comput_total_2d = f.comput_total_2d 
    self.reduce_2d = f.reduce_2d
    self.scan_total_2d = f.scan_total_2d 
    self.scan_reduce = f.scan_reduce 
    
    """ BFS module """
    self.scan_total_bfs = f.scan_total_bfs
    self.comput_bfs_2d = f.comput_bfs_2d
    self.fill_bfs = f.fill_bfs 
    self.reshuffle_bfs = f.reshuffle_bfs 
    self.reduce_bfs_2d = f.reduce_bfs_2d 
    self.get_thresholds = f.get_thresholds 

    """ Other """
    self.mark_table = f.mark_table
    const_sorted_indices = f.bfs_module.get_global("sorted_indices_1")[0]
    const_sorted_indices_ = f.bfs_module.get_global("sorted_indices_2")[0]
    cuda.memcpy_htod(const_sorted_indices, np.uint64(self.sorted_indices_gpu.ptr)) 
    cuda.memcpy_htod(const_sorted_indices_, np.uint64(self.sorted_indices_gpu_.ptr)) 

  def __allocate_gpuarrays(self):
    f = self.forest
    self.impurity_left = f.impurity_left 
    self.impurity_right = f.impurity_right 
    self.min_split = f.min_split 
    self.label_total = f.label_total  
    self.label_total_2d = f.label_total_2d
    self.impurity_2d = f.impurity_2d 
    self.min_split_2d = f.min_split_2d 
    self.features_array_gpu = f.features_array_gpu 

  def __release_gpuarrays(self):
    self.impurity_left = None
    self.impurity_right = None
    self.min_split = None
    self.label_total = None
    self.sorted_indices_gpu = None
    self.sorted_indices_gpu_ = None
    self.label_total_2d = None
    self.min_split_2d = None
    self.impurity_2d = None
    self.feature_mask = None
    self.features_array_gpu = None
    
    #Release kernels
    self.fill_kernel = None
    self.scan_reshuffle_tex = None 
    self.scan_total_kernel = None
    self.comput_label_loop_rand_kernel = None
    self.find_min_kernel = None
    self.scan_total_bfs = None
    self.comput_bfs = None
    self.fill_bfs = None
    self.reshuffle_bfs = None
    self.reduce_bfs_2d = None
    self.comput_bfs_2d = None
    self.get_thresholds = None
    self.scan_reduce = None
    self.mark_table = None

  def __allocate_numpyarrays(self):
    f = self.forest
    self.left_children = np.zeros(self.n_samples * 2, dtype = np.uint32)
    self.right_children = np.zeros(self.n_samples * 2, dtype = np.uint32) 
    self.feature_idx_array = np.zeros(2 * self.n_samples, dtype = np.uint16)
    self.feature_threshold_array = np.zeros(2 * self.n_samples, dtype = np.float32)
    self.idx_array = f.idx_array 
    self.si_idx_array = f.si_idx_array 
    self.nid_array = f.nid_array 
    self.values_idx_array = f.values_idx_array 
    self.values_si_idx_array = f.values_si_idx_array 
    self.threshold_value_idx = f.threshold_value_idx 
    self.min_imp_info = f.min_imp_info  
    self.features_array = f.features_array  

  def __release_numpyarrays(self):
    self.features_array = None
    self.nid_array = None
    self.idx_array = None
    self.si_idx_array = None
    self.threshold_value_idx = None
    self.min_imp_info = None
    self.samples = None
    self.target = None

  def __bfs_construct(self):
    while self.queue_size > 0:
      self.__bfs()
  
  def __bfs(self):
    block_per_split = int(math.ceil(float(self.MAX_BLOCK_BFS) / self.queue_size))
    
    if block_per_split > self.max_features:
      n_blocks = self.max_features
    else:
      n_blocks = block_per_split

    idx_array_gpu = gpuarray.to_gpu(
                    self.idx_array[0 : self.queue_size * 2])
    
    si_idx_array_gpu = gpuarray.to_gpu(
                    self.si_idx_array[0 : self.queue_size])
    
    self.label_total = gpuarray.empty(self.queue_size * self.n_labels, 
                                      dtype = self.dtype_counts)  
    
    threshold_value = gpuarray.empty(self.queue_size, dtype = np.float32)
    
    impurity_gpu = gpuarray.empty(self.queue_size * 2, dtype = np.float32)
    self.min_split = gpuarray.empty(self.queue_size, dtype = self.dtype_indices) 
    min_feature_idx_gpu = gpuarray.empty(self.queue_size, dtype = np.uint16)
    
    impurity_gpu_2d = gpuarray.empty(self.queue_size * 2 * n_blocks, 
                                      dtype = np.float32)
    
    min_split_2d = gpuarray.empty(self.queue_size * n_blocks, 
                                      dtype = self.dtype_indices) 

    min_feature_idx_gpu_2d = gpuarray.empty(self.queue_size * n_blocks, 
                                      dtype = np.uint16)
    
    cuda.memcpy_htod(self.features_array_gpu.ptr, self.features_array) 
    
      
    self.scan_total_bfs.prepared_call(
            (self.queue_size, 1),
            (self.BFS_THREADS, 1, 1),
            self.labels_gpu.ptr,
            self.label_total.ptr,
            si_idx_array_gpu.ptr,
            idx_array_gpu.ptr)
    

    self.comput_bfs_2d.prepared_call(
          (self.queue_size, n_blocks),
          (self.BFS_THREADS, 1, 1),
          self.samples_gpu.ptr,
          self.labels_gpu.ptr,
          idx_array_gpu.ptr,
          si_idx_array_gpu.ptr,
          self.label_total.ptr,
          self.features_array_gpu.ptr,
          impurity_gpu_2d.ptr,
          min_split_2d.ptr,
          min_feature_idx_gpu_2d.ptr)
    
    self.reduce_bfs_2d.prepared_call(
          (self.queue_size, 1),
          (1, 1, 1),
          impurity_gpu_2d.ptr,
          min_split_2d.ptr,
          min_feature_idx_gpu_2d.ptr,
          impurity_gpu.ptr,
          self.min_split.ptr,
          min_feature_idx_gpu.ptr,
          n_blocks)

    self.fill_bfs.prepared_call(
          (self.queue_size, 1),
          (self.BFS_THREADS, 1, 1),
          si_idx_array_gpu.ptr,
          min_feature_idx_gpu.ptr,
          idx_array_gpu.ptr,
          self.min_split.ptr,
          self.mark_table.ptr)


    if block_per_split > self.n_features:
      n_blocks = self.n_features
    else:
      n_blocks = block_per_split
      
    self.reshuffle_bfs.prepared_call(
          (self.queue_size, n_blocks),
          (self.BFS_THREADS, 1, 1),
          si_idx_array_gpu.ptr,
          idx_array_gpu.ptr,
          self.min_split.ptr)
    
    self.__shuffle_feature_indices()
    
    self.get_thresholds.prepared_call(
          (self.queue_size, 1),
          (1, 1, 1),
          si_idx_array_gpu.ptr,
          self.samples_gpu.ptr,
          threshold_value.ptr,
          min_feature_idx_gpu.ptr,
          self.min_split.ptr) 
    
    new_idx_array = np.empty(self.queue_size * 2 * 2, dtype = np.uint32)
    idx_array = self.idx_array
    new_si_idx_array = np.empty(self.queue_size * 2, dtype = np.uint8)
    new_nid_array = np.empty(self.queue_size * 2, dtype = np.uint32)
    left_children = self.left_children
    right_children = self.right_children
    feature_idx_array = self.feature_idx_array
    feature_threshold_array = self.feature_threshold_array
    nid_array = self.nid_array
    
    imp_min = np.empty(self.queue_size * 2, np.float32)
    min_split = np.empty(self.queue_size, self.dtype_indices)
    feature_idx = np.empty(self.queue_size, np.uint16)
    threshold = np.empty(self.queue_size, np.float32) 
    cuda.memcpy_dtoh(imp_min, impurity_gpu.ptr)
    cuda.memcpy_dtoh(min_split, self.min_split.ptr)
    cuda.memcpy_dtoh(feature_idx, min_feature_idx_gpu.ptr)
    cuda.memcpy_dtoh(threshold, threshold_value.ptr) 
    
    si_idx_array = self.si_idx_array 

    self.n_nodes, self.queue_size, self.idx_array, self.si_idx_array, self.nid_array =\
        bfs_loop(self.queue_size, 
                  self.n_nodes, 
                  self.max_features, 
                  new_idx_array, 
                  idx_array, 
                  new_si_idx_array, 
                  new_nid_array, 
                  left_children, 
                  right_children, 
                  feature_idx_array, 
                  feature_threshold_array, 
                  nid_array, 
                  imp_min, 
                  min_split, 
                  feature_idx, 
                  si_idx_array, 
                  threshold, 
                  self.min_samples_split, 
                  self.values_idx_array, 
                  self.values_si_idx_array)

    self.n_nodes = int(self.n_nodes)
    self.queue_size = int(self.queue_size)
 

  def fit(self, samples, target, sorted_indices, n_samples): 
    self.samples_itemsize = self.dtype_samples.itemsize
    self.labels_itemsize = self.dtype_labels.itemsize
    
    self.__allocate_gpuarrays()
    self.sorted_indices_gpu = sorted_indices 
    self.sorted_indices_gpu_ = self.sorted_indices_gpu.copy()
    self.__compile_kernels() 
    self.n_samples = n_samples    

    self.sorted_indices_gpu.idx = 0
    self.sorted_indices_gpu_.idx = 1

    self.samples = samples
    self.target = target
    self.queue_size = 0

    self.__allocate_numpyarrays()
    self.n_nodes = 0 
    
    self.__shuffle_feature_indices()
    self.__dfs_construct(1, 
                        1.0, 
                        0, 
                        self.n_samples, self.sorted_indices_gpu, 
                        self.sorted_indices_gpu_)  
    
    self.__bfs_construct() 
    self.__gpu_decorate_nodes(samples, target)
    self.__release_gpuarrays() 
    self.__release_numpyarrays()

  def __gpu_decorate_nodes(self, samples, labels):
    si_0 = driver.pagelocked_empty(self.n_samples, dtype = self.dtype_indices)
    si_1 = driver.pagelocked_empty(self.n_samples, dtype = self.dtype_indices)
    self.values_array = np.empty(self.n_nodes, dtype = self.dtype_labels)
    cuda.memcpy_dtoh(si_0, self.sorted_indices_gpu.ptr)
    cuda.memcpy_dtoh(si_1, self.sorted_indices_gpu_.ptr)
    
    decorate(self.target, 
              si_0, 
              si_1, 
              self.values_idx_array, 
              self.values_si_idx_array, 
              self.values_array, 
              self.n_nodes)

    self.values_idx_array = None
    self.values_si_idx_array = None
    self.left_children.resize(self.n_nodes, refcheck = False)
    self.right_children.resize(self.n_nodes, refcheck = False) 
    self.feature_threshold_array.resize(self.n_nodes, refcheck = False) 
    self.feature_idx_array.resize(self.n_nodes, refcheck = False)

  def __get_block_size(self, n_samples):
    n_block = int(math.ceil(float(n_samples) / 2000))
    if n_block > self.MAX_BLOCK_PER_FEATURE:
      n_block = self.MAX_BLOCK_PER_FEATURE
    return n_block, int(math.ceil(float(n_samples) / n_block))

  def __gini(self, n_samples, indices_offset, si_gpu_in):
    n_block, n_range = self.__get_block_size(n_samples)
    
    self.scan_total_2d.prepared_call(
          (self.max_features, n_block),
          (self.COMPUTE_THREADS_PER_BLOCK, 1, 1),
          si_gpu_in.ptr + indices_offset,
          self.labels_gpu.ptr,
          self.label_total_2d.ptr,
          self.features_array_gpu.ptr,
          n_range,
          n_samples)

    self.scan_reduce.prepared_call(
          (self.max_features, 1),
          (32, 1, 1),
          self.label_total_2d.ptr,
          n_block)  
    
    self.comput_total_2d.prepared_call(
         (self.max_features, n_block),
         (self.COMPUTE_THREADS_PER_BLOCK, 1, 1),
         si_gpu_in.ptr + indices_offset,
         self.samples_gpu.ptr,
         self.labels_gpu.ptr,
         self.impurity_2d.ptr,
         self.label_total_2d.ptr,
         self.min_split_2d.ptr,
         self.features_array_gpu.ptr,
         n_range,
         n_samples)

    self.reduce_2d.prepared_call(
         (self.max_features, 1),
         (32, 1, 1),
         self.impurity_2d.ptr,
         self.impurity_left.ptr,
         self.impurity_right.ptr,
         self.min_split_2d.ptr,
         self.min_split.ptr,
         n_block)    
    
    self.find_min_kernel.prepared_call(
                (1, 1),
                (32, 1, 1),
                self.impurity_left.ptr,
                self.impurity_right.ptr,
                self.min_split.ptr,
                self.max_features)
    
    
    cuda.memcpy_dtoh(self.min_imp_info, self.impurity_left.ptr)
    min_right = self.min_imp_info[1] 
    min_left = self.min_imp_info[0] 
    col = int(self.min_imp_info[2]) 
    row = int(self.min_imp_info[3])
    row = self.features_array[row]  
    return min_left, min_right, row, col

  def  __dfs_construct(self, 
                        depth, 
                        error_rate, 
                        start_idx, 
                        stop_idx, 
                        si_gpu_in, 
                        si_gpu_out):
    def check_terminate():
      if error_rate == 0.0:
        return True
      else:
        return False     

    n_samples = stop_idx - start_idx 
    indices_offset =  start_idx * self.dtype_indices.itemsize    
    nid = self.n_nodes
    self.n_nodes += 1

    if check_terminate():
      turn_to_leaf(nid, 
                    start_idx, 
                    si_gpu_in.idx, 
                    self.values_idx_array, 
                    self.values_si_idx_array
                    )
      return
    
    if n_samples < self.min_samples_split:
      turn_to_leaf(nid, 
                    start_idx, 
                    si_gpu_in.idx, 
                    self.values_idx_array, 
                    self.values_si_idx_array
                    )
      return
    
    if n_samples <= self.bfs_threshold:
      self.idx_array[self.queue_size * 2] = start_idx
      self.idx_array[self.queue_size * 2 + 1] = stop_idx
      self.si_idx_array[self.queue_size] = si_gpu_in.idx
      self.nid_array[self.queue_size] = nid
      self.queue_size += 1
      return
    
    cuda.memcpy_htod(self.features_array_gpu.ptr, self.features_array)
    min_left, min_right, row, col = self.__gini(n_samples, 
                                                indices_offset, 
                                                si_gpu_in) 
    if min_left + min_right == 4:
      turn_to_leaf(nid, 
                  start_idx, 
                  si_gpu_in.idx, 
                  self.values_idx_array, 
                  self.values_si_idx_array) 
      return
    
    cuda.memcpy_dtoh(self.threshold_value_idx, 
                    si_gpu_in.ptr + int(indices_offset) + \
                    int(row * self.stride + col) * \
                    int(self.dtype_indices.itemsize)) 

    self.feature_idx_array[nid] = row
    self.feature_threshold_array[nid] = (float(self.samples[row, \
        self.threshold_value_idx[0]]) + self.samples[row, \
        self.threshold_value_idx[1]]) / 2
    

    self.fill_kernel.prepared_call(
                      (1, 1),
                      (512, 1, 1),
                      si_gpu_in.ptr + row * self.stride * \
                          self.dtype_indices.itemsize + \
                          indices_offset, 
                      n_samples, 
                      col, 
                      self.mark_table.ptr) 


    block = (self.RESHUFFLE_THREADS_PER_BLOCK, 1, 1)
    
    self.scan_reshuffle_tex.prepared_call(
                      (self.n_features, 1),
                      block,
                      si_gpu_in.ptr + indices_offset,
                      si_gpu_out.ptr + indices_offset,
                      n_samples,
                      col)

    self.__shuffle_feature_indices() 

    self.left_children[nid] = self.n_nodes
    self.__dfs_construct(depth + 1, min_left, 
        start_idx, start_idx + col + 1, si_gpu_out, si_gpu_in)
    
    self.right_children[nid] = self.n_nodes
    self.__dfs_construct(depth + 1, min_right, 
        start_idx + col + 1, stop_idx, si_gpu_out, si_gpu_in)

########NEW FILE########
__FILENAME__ = util
import time
import numpy as np
from pycuda.compiler import SourceModule
from os import path
import operator
import os
import logging

logging.basicConfig(level=logging.DEBUG)

log_debug = logging.debug
log_info = logging.info
log_warn = logging.warn
log_error = logging.error
log_fatal = logging.fatal


_kernel_cache = {}
_module_cache = {}

kernels_dir = path.dirname(os.path.realpath(__file__)) +\
                "/cuda_kernels/"

def compile_module(module_file, params):
  module_file = kernels_dir + module_file
  key = (module_file, params)
  if key in _module_cache:
    return _module_cache[key]
  
  with open(module_file) as code_file:
    start_timer("compile module")
    code = code_file.read()
    src = code % params
    mod = SourceModule(src, include_dirs = [kernels_dir])
    _module_cache[key] = mod
    end_timer("compile module")
    return mod


def get_best_dtype(max_value):
  """ Find the best dtype to minimize the memory usage"""
  if max_value <= np.iinfo(np.uint8).max:
    return np.dtype(np.uint8)
  if max_value <= np.iinfo(np.uint16).max:
    return np.dtype(np.uint16)
  if max_value <= np.iinfo(np.uint32).max:
    return np.dtype(np.uint32)
  else:
    return np.dtype(np.uint64)

class timer(object):
  def __init__(self, name):
    self.name = name

  def __enter__(self, *args):
    print "Running %s" % self.name 
    self.start_t = time.time()

  def __exit__(self, *args):
    print "Time for %s: %s" % (self.name, time.time() - self.start_t)

def dtype_to_ctype(dtype):
  if dtype.kind == 'f':
    if dtype == 'float32':
      return 'float'
    else:
      assert dtype == 'float64', "Unsupported dtype %s" % dtype
      return 'double'
  assert dtype.kind in ('u', 'i')
  return "%s_t" % dtype 

def mk_kernel(params, func_name, kernel_file, prepare_args = None):
  kernel_file = kernels_dir + kernel_file
  key = (params, kernel_file, prepare_args)
  if key in _kernel_cache:
    return _kernel_cache[key]
  
  with open(kernel_file) as code_file:
    code = code_file.read()
    src = code % params
    mod = SourceModule(src, include_dirs = [kernels_dir])
    fn = mod.get_function(func_name)
    if prepare_args is not None: fn.prepare(prepare_args)
    _kernel_cache[key] = fn
    return fn

def mk_tex_kernel(params, 
                  func_name, 
                  tex_name, 
                  kernel_file, 
                  prepare_args = None):
  kernel_file = kernels_dir + kernel_file
  key = (params, kernel_file, prepare_args)
  if key in _kernel_cache:
    return _kernel_cache[key]

  with open(kernel_file) as code_file:
    code = code_file.read()
    src = code % params
    mod = SourceModule(src, include_dirs = [kernels_dir])
    fn = mod.get_function(func_name)
    tex = mod.get_texref(tex_name)
    if prepare_args is not None: fn.prepare(prepare_args)
    _kernel_cache[key] = (fn, tex)
    return fn, tex

def test_diff(x, y):
  """ Test how many elements betweenn array 
  x and y are different. """
  assert isinstance(x, np.ndarray)
  assert isinstance(y, np.ndarray)
  assert x.size == y.size
  diff = x - y
  return (np.count_nonzero(diff), x.size)


start_times = {}
total_times = {}

def start_timer(name):
  start_times[name] = time.time()
  
def end_timer(name):
  total = total_times.get(name, 0)
  total += time.time() - start_times[name]
  total_times[name] = total

def show_timings(limit = 100):
  tables = sorted(total_times.iteritems(), 
                  key = operator.itemgetter(1), 
                  reverse = True) 
  idx = 0
  print "---------Timings---------"
  for key, value in tables:
    print key.ljust(15), ":", value
    idx += 1
    if idx == limit:
      break

  print "-------------------------"

########NEW FILE########
__FILENAME__ = estimate_threshold
import numpy as np
import cudatree
import time 


inputs = []
best_threshold_prcts = []
best_threshold_values = []

all_classes = [2, 10, 20, 40, 80, 160]
all_examples = [10**4, 2*10**4, 4*10**4, 8*10**4, 12* 10**4, 16*10**4, 20 * 10**4, 32 * 10**4, 64 * 10**4]
all_features = [10, 50, 100, 200, 400, 600, 800] 
thresholds = [2000, 3000, 4000, 5000, 
              10000, 15000, 20000, 30000, 40000, 50000, 60000, 70000]


# np.exp(np.linspace(np.log(1000), np.log(50000), num = 15)).astype('int')
total_iters = len(all_classes) * len(all_examples) * len(all_features) * len(thresholds)

i = 1 
# thresholds =  [0.001, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, .1, .2]

# use just one set of random forests, since we seem to be leaking memory
rfs = {}
for f in all_features:
  max_features = max_features = int(np.sqrt(f))
  rfs[f] = cudatree.RandomForestClassifier(n_estimators = 3, bootstrap = False, max_features = max_features)

for n_classes in reversed(all_classes):
  print "n_classes", n_classes
  for n_examples in reversed(all_examples):
    print "n_examples", n_examples
    y = np.random.randint(low = 0, high = n_classes, size = n_examples)
    for n_features in reversed(all_features):
      print "n_features", n_features
      max_features = int(np.sqrt(n_features))
      print "sqrt(n_features) =", max_features 
      if n_features * n_examples > 10**7:
        print "Skipping due excessive n_features * n_examples..."
	i += len(thresholds)
        continue
      if n_examples * n_classes > 10 ** 7:
        print "Skipping due to excessive n_examples * n_classes"
	i += len(thresholds)
        continue
	 
      x = np.random.randn(n_examples, n_features)
      rf = rfs[n_features]
      # warm up
      rf.fit(x[:100],y[:100])
      best_time = np.inf
      best_threshold = None
      best_threshold_prct = None 
      print "(n_classes = %d, n_examples = %d, max_features = %d)" % (n_classes, n_examples, max_features)
      tested_thresholds = []
      times = []
      for bfs_threshold in thresholds:
        bfs_threshold_prct = float(bfs_threshold) / n_examples
        print "  -- (%d / %d) threshold %d (%0.2f%%)" % (i, total_iters,  bfs_threshold, bfs_threshold_prct * 100)
        i += 1 
        if bfs_threshold > n_examples:
          print "Skipping threshold > n_examples" 
	  continue 
        if bfs_threshold / float(n_examples) < 0.001:
	  print "SKipping, BFS threshold too small relative to n_examples"
        
       
        start_t = time.time()
        rf.fit(x, y, bfs_threshold)
        t = time.time() - start_t
        tested_thresholds.append(bfs_threshold)
        times.append(t)
        print "  ---> total time", t 
        if t < best_time:
          best_time = t
          best_threshold = bfs_threshold
          best_theshold_prct = bfs_threshold_prct
      print "thresholds", tested_thresholds
      print "times", times 
      inputs.append([1.0, n_classes, n_examples, max_features])
      best_threshold_values.append(best_threshold)
      best_threshold_prcts.append(best_threshold_prct)

X = np.array(inputs)
print "input shape", X.shape



best_threshold_prcts = np.array(best_threshold_prcts)
best_threshold_values = np.array(best_threshold_values)
Y = best_threshold_values

lstsq_result = np.linalg.lstsq(X, Y)
print "Regression coefficients:", lstsq_result[0]
n = len(best_threshold_values)
print "Regression residual:", lstsq_result[1], "RMSE:", np.sqrt(lstsq_result[1] / n)

import socket 
csv_filename = "threshold_results_" + socket.gethostname()
with open(csv_filename, 'w') as csvfile:
    for i, input_tuple in enumerate(inputs):
      csvfile.write(str(input_tuple[1:]))
      csvfile.write("," + str(best_threshold_values[i]))
      csvfile.write("," + str(best_threshold_prcts[i]))
      csvfile.write("\n")

LogX = X.copy()
LogX[:, 1:] = np.log(X[:, 1:])
LogY = np.log(Y)

log_lstsq_result = np.linalg.lstsq(LogX, LogY)

print "Log regression coefficients:", log_lstsq_result[0]
n = len(best_threshold_values)
print "Log regression residual:", log_lstsq_result[1], "RMSE:", np.sqrt(log_lstsq_result[1] / n)
log_pred = np.dot(LogX, log_lstsq_result[0])
pred = np.exp(log_pred)
residual = np.sum((Y - pred)**2)
print "Actual residual", residual 
print "Actual RMSE:", np.sqrt(residual / n)


"""
import sklearn
import sklearn.linear_model
ridge = sklearn.linear_model.RidgeCV(alphas = [0.01, 0.1, 1, 10, 100], fit_intercept = False)
ridge.fit(X, Y)
print "Ridge regression coef", ridge.coef_
print "Ridge regression alpha", ridge.alpha_

pred = ridge.predict(X)
sse = np.sum( (pred - Y) ** 2)
print "Ridge residual", sse
print "Ridge RMSE", np.sqrt(sse / n)
"""

########NEW FILE########
__FILENAME__ = builder
from sklearn.ensemble import RandomForestClassifier as skRF
from pycuda import driver
import multiprocessing
import numpy as np
from cudatree import RandomForestClassifier as cdRF
from cudatree import RandomClassifierTree, util 

class CPUBuilder(multiprocessing.Process):
  """
  Build some trees on cpu, the cpu classifier should be cpu 
  implementation of random forest classifier.
  """
  def __init__(self,
                cpu_classifier,
                X,
                Y,
                bootstrap,
                max_features,
                n_jobs,
                remain_trees,
                lock):
    multiprocessing.Process.__init__(self)
    self.cpu_classifier = cpu_classifier
    self.X = X
    self.Y = Y
    self.bootstrap = bootstrap
    self.max_features = max_features
    self.n_jobs = n_jobs
    self.remain_trees = remain_trees
    self.lock = lock
    self.result_queue = multiprocessing.Queue()

  def run(self):
    lock = self.lock
    remain_trees = self.remain_trees
    cpu_classifier = self.cpu_classifier
    max_features = self.max_features
    bootstrap = self.bootstrap
    n_jobs = self.n_jobs
    result_queue = self.result_queue
    forests = list()
    X = self.X
    Y = self.Y

    if max_features == None:
      max_features = "auto"
    
    self.Y = self.Y.astype(np.uint16) 
    classifier_name = cpu_classifier.__name__
    n_trees_before = 0

    while True:
      lock.acquire()
      #The trees trained by GPU in last round
      n_trees_by_gpu = n_trees_before - remain_trees.value
      
      #Stop trainning if the remaining tree is smaller than the sum of n_jobs and n_trees trained by gpu 
      if remain_trees.value < n_jobs or (n_trees_before != 0 and remain_trees.value - n_jobs <= n_trees_by_gpu):
        lock.release()
        break
            
      remain_trees.value -= n_jobs
      n_trees_before = remain_trees.value
      lock.release()

      util.log_info("%s got %s jobs.", classifier_name, n_jobs)
      f = cpu_classifier(n_estimators = n_jobs, n_jobs = n_jobs, 
          bootstrap = bootstrap, max_features = max_features)
      f.fit(X, Y)
      forests.append(f)

    result_queue.put(forests)
    util.log_info("CPU DONE")

  def get_result(self):
    return self.result_queue.get()


class GPUBuilder(multiprocessing.Process):
  "Build some trees on gpu" 
  def __init__(self, 
                gpu_id,
                X,
                Y,
                bootstrap,
                max_features,
                bfs_threshold,
                remain_trees,
                lock):
    multiprocessing.Process.__init__(self)
    self.gpu_id = gpu_id
    self.X = X
    self.Y = Y
    self.bootstrap = bootstrap
    self.max_features = max_features
    self.bfs_threshold = bfs_threshold
    self.remain_trees = remain_trees
    self.lock = lock
    self.result_queue = multiprocessing.Queue()

  def run(self):
    reload(util)
    driver.init()
    ctx = driver.Device(self.gpu_id).make_context()

    X = self.X
    Y = self.Y
    bootstrap = self.bootstrap
    max_features = self.max_features
    bfs_threshold = self.bfs_threshold
    remain_trees = self.remain_trees
    lock = self.lock

    trees = list()
    forest = cdRF(n_estimators = 1,
                    bootstrap = bootstrap, 
                    max_features = max_features)
    forest.fit_init(X, Y)
    
    while True:
      lock.acquire()
      if remain_trees.value == 0:
        lock.release()
        break
      
      remain_trees.value -= 1
      lock.release()
      
      util.log_info("CUDA gets 1 job")
      tree = RandomClassifierTree(forest)   
      
      si, n_samples = forest._get_sorted_indices(forest.sorted_indices)
      tree.fit(forest.samples, forest.target, si, n_samples)
      trees.append(tree)

    forest.fit_release()
    self.result_queue.put(trees)

    ctx.detach()
    del ctx
    util.log_info("GPU DONE")

  def get_result(self):
    return self.result_queue.get()

########NEW FILE########
__FILENAME__ = hybridforest
#!/usr/bin/python
from sklearn.ensemble import RandomForestClassifier as skRF
import numpy as np
from cudatree import RandomClassifierTree, convert_result, util
from cudatree import RandomForestClassifier as cdRF, timer
import multiprocessing
from multiprocessing import Value, Lock, cpu_count
import atexit
import pycuda
from builder import CPUBuilder, GPUBuilder

#kill the child process if any
def cleanup(proc):
  if proc.is_alive():
    proc.terminate()

class RandomForestClassifier(object):
  """
  This RandomForestClassifier uses both CudaTree and cpu 
  implementation of RandomForestClassifier(default is sklearn) 
  to construct random forest. The reason is that CudaTree only 
  use one CPU core, the main computation is done at GPU side, 
  so in order to get maximum utilization of the system, we can 
  trai one CudaTree random forest with GPU and one core of CPU,
  and simultaneously we construct some trees on other cores by 
  other multicore implementaion of random forest.
  """
  def __init__(self, 
              n_estimators = 10, 
              n_jobs = -1, 
              n_gpus = 1,
              max_features = None, 
              bootstrap = True, 
              cpu_classifier = skRF):
    """Construce random forest on GPU and multicores.

    Parameters
    ----------
    n_estimators : integer, optional (default=10)
        The number of trees in the forest.

    max_features : int or None, optional (default="log2(n_features)")
        The number of features to consider when looking for the best split:
          - If None, then `max_features=log2(n_features)`.
    
    bootstrap : boolean, optional (default=True)
        Whether use bootstrap samples
    
    n_jobs : int (default=-1)
        How many cores to use when construct random forest.
        Please note that we will give n_gpu cores to GPU builder,
        If the remaining number of cores is less than 1, we won't
        train any trees on CPU.
          - If -1, then use number of cores you CPU has.
    
    n_gpus: int (default = 1)
        How many gpu devices to use when construct random forest.
          - If -1, then use number of devices you GPU has.

    cpu_classifier : class(default=sklearn.ensemble.RandomForestClassifier)
        Which random forest classifier class to use when construct trees on CPU.
          The default is sklearn.ensemble.RandomForestClassifier. You can also pass 
          some other classes like WiseRF.

    Returns
    -------
    None
    """ 
    assert hasattr(cpu_classifier, "fit"),\
              "cpu classifier must support fit method."
    assert hasattr(cpu_classifier, "predict_proba"),\
              "cpu classifier must support predict proba method."
    
    self.n_estimators = n_estimators
    self.max_features = max_features
    self.bootstrap = bootstrap
    self._cpu_forests = None
    self._cuda_forest = None
    self._cuda_trees = None
    self._cpu_classifier = cpu_classifier
    self.n_gpus = n_gpus
    
    if n_jobs == -1:
      n_jobs = cpu_count()
    if n_gpus == -1:
      n_gpus = pycuda.autoinit.device.count()
    
    assert n_gpus <= pycuda.autoinit.device.count(),\
      "You can't use more devices than your system has."
    
    self.n_jobs = n_jobs
    self.n_gpus = n_gpus


  def _cuda_fit(self, X, Y, bfs_threshold, remain_trees, lock):
    self._cuda_forest = cdRF(n_estimators = 1,
                            bootstrap = self.bootstrap, 
                            max_features = self.max_features) 
    #allocate resource
    self._cuda_forest.fit_init(X, Y)
    f = self._cuda_forest

    while True:
      lock.acquire()
      if remain_trees.value == 0:
        lock.release()
        break
      
      remain_trees.value -= 1
      lock.release()
      
      tree = RandomClassifierTree(f)   
      
      si, n_samples = f._get_sorted_indices(f.sorted_indices)
      tree.fit(f.samples, f.target, si, n_samples)
      f._trees.append(tree) 
    
    #release the resource
    self._cuda_forest.fit_release()
    #util.log_info("cudatee's job done")


  def fit(self, X, Y, bfs_threshold = None):
    #shared memory value which tells two processes when should stop
    remain_trees = Value("i", self.n_estimators)    
    lock = Lock()
    #how many labels    
    self.n_classes = np.unique(Y).size
    
    n_jobs = self.n_jobs - self.n_gpus
    

    if n_jobs > 0:
      cpu_builder = CPUBuilder(self._cpu_classifier,
                            X,
                            Y,
                            self.bootstrap,
                            self.max_features,
                            n_jobs,
                            remain_trees,
                            lock)
      
      cpu_builder.start()
    
    gpu_builders = [GPUBuilder(i + 1,
                              X,
                              Y,
                              self.bootstrap,
                              self.max_features,
                              bfs_threshold,
                              remain_trees,
                              lock) for i in xrange(self.n_gpus - 1)]
 
    pycuda.autoinit.context.pop()  
    for b in gpu_builders:
      b.start()
    pycuda.autoinit.context.push()
    
    #At same time, we construct cuda radom forest
    self._cuda_fit(X, Y, bfs_threshold, remain_trees, lock)    
    
    if n_jobs > 0:
      #get the cpu forest result
      self._cpu_forests = cpu_builder.get_result()
      cpu_builder.join()
    
    #get the gpu forest result
    for b in gpu_builders:
      self._cuda_forest._trees.extend(b.get_result())
      b.join()
  

  def predict(self, X):
    sk_proba = np.zeros((X.shape[0], self.n_classes), np.float64)

    if self._cpu_forests is not None:
      for f in self._cpu_forests:
        sk_proba += f.predict_proba(X) * len(f.estimators_)
     
    n_sk_trees = self.n_estimators - len(self._cuda_forest._trees)
    n_cd_trees = self.n_estimators - n_sk_trees
    cuda_proba = self._cuda_forest.predict_proba(X) * n_cd_trees
    final_proba = (sk_proba  + cuda_proba ) / self.n_estimators
    res = np.array([np.argmax(final_proba[i]) for i in xrange(final_proba.shape[0])])
    
    if hasattr(self._cuda_forest, "compt_table"):
      res = convert_result(self._cuda_forest.compt_table, res)
    return res


  def score(self, X, Y):
    return np.mean(self.predict(X) == Y)

########NEW FILE########
__FILENAME__ = helpers
from cudatree import RandomForestClassifier
import hybridforest

def compare_accuracy(x,y, n_estimators = 11, bootstrap = True, slop = 0.98, n_repeat = 10):
  n = x.shape[0] / 2 
  xtrain = x[:n]
  ytrain = y[:n]
  xtest = x[n:]
  ytest = y[n:]
  cudarf = RandomForestClassifier(n_estimators = n_estimators, bootstrap = bootstrap)
  import sklearn.ensemble
  skrf = sklearn.ensemble.RandomForestClassifier(n_estimators = n_estimators, bootstrap = bootstrap)
  cuda_score_total = 0 
  sk_score_total = 0
  for i in xrange(n_repeat):
    cudarf.fit(xtrain, ytrain)
    skrf.fit(xtrain, ytrain)
    sk_score = skrf.score(xtest, ytest)
    cuda_score = cudarf.score(xtest, ytest)
    print "Iteration", i 
    print "Sklearn score", sk_score 
    print "CudaTree score", cuda_score 
    sk_score_total += sk_score 
    cuda_score_total += cuda_score 

  assert cuda_score_total >= (sk_score_total * slop), \
    "Getting significantly worse test accuracy than sklearn: %s vs. %s"\
    % (cuda_score_total / n_repeat, sk_score_total / n_repeat)


def compare_hybrid_accuracy(x,y, n_estimators = 20, bootstrap = True, slop = 0.98, n_repeat = 5):
  n = x.shape[0] / 2 
  xtrain = x[:n]
  ytrain = y[:n]
  xtest = x[n:]
  ytest = y[n:]
  hybridrf = hybridforest.RandomForestClassifier(n_estimators = n_estimators, bootstrap = bootstrap)
  import sklearn.ensemble
  skrf = sklearn.ensemble.RandomForestClassifier(n_estimators = n_estimators, bootstrap = bootstrap)
  cuda_score_total = 0 
  sk_score_total = 0
  for i in xrange(n_repeat):
    hybridrf.fit(xtrain, ytrain)
    skrf.fit(xtrain, ytrain)
    sk_score = skrf.score(xtest, ytest)
    cuda_score = hybridrf.score(xtest, ytest)
    print "Iteration", i 
    print "Sklearn score", sk_score 
    print "Hybrid score", cuda_score 
    sk_score_total += sk_score 
    cuda_score_total += cuda_score 

  assert cuda_score_total >= (sk_score_total * slop), \
    "Getting significantly worse test accuracy than sklearn: %s vs. %s"\
    % (cuda_score_total / n_repeat, sk_score_total / n_repeat)


########NEW FILE########
__FILENAME__ = test_covtype
import numpy as np
from cudatree import load_data, RandomForestClassifier, timer
from cudatree import util

x, y = load_data("covtype")
x = x[:10000]
y = y[:10000]

def test_covtype_memorize():
  with timer("Cuda treelearn"):
    forest = RandomForestClassifier(bootstrap = False)
    forest.fit(x, y, bfs_threshold = 500000)
  with timer("Predict"):
    diff, total = util.test_diff(forest.predict(x), y)  
    print "%s(Wrong)/%s(Total). The error rate is %f." % (diff, total, diff/float(total))
  assert diff == 0, "Didn't perfectly memorize, got %d wrong" % diff

from helpers import compare_accuracy, compare_hybrid_accuracy
def test_covtype_accuracy():
  compare_accuracy(x,y)
  compare_hybrid_accuracy(x, y)

if __name__ == "__main__":
  test_covtype_memorize()
  test_covtype_accuracy()
  

########NEW FILE########
__FILENAME__ = test_diabetes_classify
import numpy as np
from cudatree import load_data, RandomForestClassifier, timer
from cudatree import util

x, y = load_data("diabetes")

def test_diabetes_memorize():
  with timer("Cuda treelearn"):
    forest = RandomForestClassifier(bootstrap = False)
    forest.fit(x, y)
  with timer("Predict"):
    diff, total = util.test_diff(forest.predict(x), y)  
    print "%s(Wrong)/%s(Total). The error rate is %f." % (diff, total, diff/float(total))
  assert diff == 0, "Didn't perfectly memorize, got %d wrong" % diff

from helpers import compare_accuracy, compare_hybrid_accuracy
def test_diabetes_accuracy():
  compare_accuracy(x,y)
  compare_hybrid_accuracy(x,y)


if __name__ == "__main__":
  test_diabetes_memorize()
  test_diabetes_accuracy()
  

########NEW FILE########
__FILENAME__ = test_digits
import numpy as np
from cudatree import load_data, RandomForestClassifier, timer
from cudatree import util

x,y = load_data("digits")

n_estimators = 13 
bootstrap = True

def test_digits_memorize():
  with timer("Cuda treelearn"):
    forest = RandomForestClassifier(n_estimators = n_estimators/2, bootstrap = False)
    forest.fit(x, y)
  with timer("Predict"):
    diff, total = util.test_diff(forest.predict(x), y)  
    print "%s (Wrong) / %s (Total). The error rate is %f." % (diff, total, diff/float(total))
  assert diff == 0, "Didn't memorize, got %d wrong" % diff 

from helpers import compare_accuracy 
def test_digits_vs_sklearn():
  compare_accuracy(x,y)

if __name__ == "__main__":
  test_digits_memorize()
  test_digits_vs_sklearn()

########NEW FILE########
__FILENAME__ = test_iris
import numpy as np
from cudatree import load_data, RandomForestClassifier, timer
from cudatree import util

x, y = load_data("iris")

def test_iris_memorize():
  with timer("Cuda treelearn"):
    forest = RandomForestClassifier(bootstrap = False)
    forest.fit(x, y)
  with timer("Predict"):
    diff, total = util.test_diff(forest.predict(x), y)  
    print "%s(Wrong)/%s(Total). The error rate is %f." % (diff, total, diff/float(total))
  assert diff == 0, "Didn't perfectly memorize, got %d wrong" % diff

from helpers import compare_accuracy
def test_iris_accuracy():
  compare_accuracy(x,y)


if __name__ == "__main__":
  test_iris_memorize()
  test_iris_accuracy()
  

########NEW FILE########
