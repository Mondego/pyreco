__FILENAME__ = cudamat
import os, pdb, platform, time, warnings
import ctypes as ct
import numpy as np

MAX_ONES = 1024*256

if platform.system() == 'Windows':
    _cudamat = ct.cdll.LoadLibrary('libcudamat.dll')
else:
    _cudamat = ct.cdll.LoadLibrary('libcudamat.so')

_cudamat.get_last_cuda_error.restype = ct.c_char_p
_cudamat.cublas_init.restype = ct.c_int
_cudamat.cublas_shutdown.restype = ct.c_int
_cudamat.cuda_set_device.restype = ct.c_int
_cudamat.init_random.restype = ct.c_int

_cudamat.init_empty.restype = ct.c_int
_cudamat.reshape.restype = ct.c_int
_cudamat.copy_to_host.restype = ct.c_int
_cudamat.allocate_device_memory = ct.c_int
_cudamat.copy_to_device.restype = ct.c_int
_cudamat.copy_on_device.restype = ct.c_int
_cudamat.free_device_memory.restype = ct.c_int

_cudamat.get_slice.restype = ct.c_int
_cudamat.get_row_slice.restype = ct.c_int
_cudamat.set_row_slice.restype = ct.c_int
_cudamat.copy_transpose.restype = ct.c_int
_cudamat.get_vector_slice.restype = ct.c_int
_cudamat.fill_with_rand.restype = ct.c_int
_cudamat.fill_with_randn.restype = ct.c_int

_cudamat.add_col_vec.restype = ct.c_int
_cudamat.add_col_mult.restype = ct.c_int
_cudamat.add_row_mult.restype = ct.c_int
_cudamat.add_row_vec.restype = ct.c_int
_cudamat.mult_by_col_vec.restype = ct.c_int
_cudamat.mult_by_row_vec.restype = ct.c_int
_cudamat.div_by_col_vec.restype = ct.c_int
_cudamat.div_by_row_vec.restype = ct.c_int

_cudamat.less_than.restype = ct.c_int
_cudamat.less_than_scalar.restype = ct.c_int
_cudamat.greater_than.restype = ct.c_int
_cudamat.greater_than_scalar.restype = ct.c_int
_cudamat.max_by_axis.restype = ct.c_int
_cudamat.argmax_by_axis.restype = ct.c_int
_cudamat.sqsum_by_axis.restype = ct.c_int
_cudamat.normlimit_by_axis.restype = ct.c_int
_cudamat.sign.restype = ct.c_int
_cudamat.apply_sigmoid.restype = ct.c_int
_cudamat.apply_tanh.restype = ct.c_int
_cudamat.apply_abs.restype = ct.c_int
_cudamat.apply_log_1_plus_exp.restype = ct.c_int
_cudamat.apply_log.restype = ct.c_int
_cudamat.apply_floor.restype = ct.c_int
_cudamat.apply_ceil.restype = ct.c_int
_cudamat.apply_exp.restype = ct.c_int
_cudamat.apply_sqrt.restype = ct.c_int
_cudamat.apply_pow.restype = ct.c_int
_cudamat.apply_pow_matrix.restype = ct.c_int
_cudamat.reciprocal.restype = ct.c_int

_cudamat.add_elementwise.restype = ct.c_int
_cudamat.subtract_elementwise.restype = ct.c_int
_cudamat.divide_elementwise.restype = ct.c_int
_cudamat.mult_elementwise.restype = ct.c_int
_cudamat.apply_logistic_deriv.restype = ct.c_int
_cudamat.assign_scalar.restype = ct.c_int
_cudamat.mult_by_scalar.restype = ct.c_int
_cudamat.divide_by_scalar.restype = ct.c_int
_cudamat.add_scalar.restype = ct.c_int

_cudamat.euclid_norm.restype = ct.c_float
_cudamat.selectRows.restype = ct.c_int
_cudamat.setSelectedRows.restype = ct.c_int
_cudamat.vdot.restype = ct.c_float
_cudamat.dot.restype = ct.c_int

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""

    def newFunc(*args, **kwargs):
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

class CUDAMatException(Exception):
    pass

def get_last_cuda_error():
    return str(_cudamat.get_last_cuda_error())

def generate_exception(err_code):
    """
    Return a CUDAMatException object based on the error code err_code.
    """

    if err_code == -1:
        return CUDAMatException("Incompatible matrix dimensions.")
    elif err_code == -2:
        return CUDAMatException("CUBLAS error.")
    elif err_code == -3:
        return CUDAMatException("CUDA error: " + get_last_cuda_error())
    elif err_code == -4:
        return CUDAMatException("Operation not supported on views.")
    elif err_code == -5:
        return CUDAMatException("Operation not supported on transposed matrices.")
    elif err_code == -6:
        return CUDAMatException("")
    elif err_code == -7:
        return CUDAMatException("Incompatible transposedness.")
    elif err_code == -8:
        return CUDAMatException("Matrix is not in device memory.")
    elif err_code == -9:
        return CUDAMatException("Operation not supported.")
        

class cudamat(ct.Structure):
    _fields_ = [('data_host', ct.POINTER(ct.c_float)),
                ('data_device', ct.POINTER(ct.c_float)),
                ('on_device', ct.c_int),
                ('on_host', ct.c_int),
                ('size', ct.c_int * 2),
                ('is_trans', ct.c_int),
                ('owns_data', ct.c_int)]

class rnd_struct(ct.Structure):
    _fields_ = [('dev_rnd_mults', ct.POINTER(ct.c_uint)), 
                ('dev_rnd_words', ct.POINTER(ct.c_longlong))]

class TransposedCUDAMatrix(object):
    def __init__(self, mat):
        self.mat = cudamat()
        ct.memmove(ct.pointer(self.mat), ct.pointer(mat), ct.sizeof(self.mat))
        self.mat.is_trans = 1
        self.p_mat = ct.pointer(self.mat)

class CUDAMatrix(object):
    """
    A CUDAMatrix object represents a matrix of single precision floating point
    numbers on a GPU.
    """

    def overwrite(self, array, copy_to_device=True):
        """Overwrites self with array.
        
        'array' should have a size smaller than that of the array used to
        initialize the CUDAMatrix. The method will not throw an Exception just
        yet if this is not true. It will throw exceptions or behave in strange
        ways later on.
        """
        assert type(array) == np.ndarray, 'array must be a np.ndarray.'
        array = reformat(array)
        self.numpy_array = array
        _cudamat.init_from_array(self.p_mat, array.ctypes.data_as(ct.POINTER(ct.c_float)), ct.c_int(array.shape[0]), ct.c_int(array.shape[1]))
        _cudamat.set_on_device(self.p_mat)
        if copy_to_device:
            err_code = _cudamat.copy_to_device(self.p_mat)
            if err_code:
                raise generate_exception(err_code)


    def __init__(self, array, copy_to_device = True):
        """
        Initializes a new matrix object in one of two ways. If array is a numpy
        ndarray, memory for a matrix with the same dimensions is allocated on
        the GPU. If the copy_to_device flag is set to True, the GPU matrix is
        initialized with the given ndarray. If array is not an ndarray, it must
        be a cudamat structure (typically the user will never use this way of
        calling __init__).
        """

        if type(array) == np.ndarray:
            # Convert array to float32 in FORTRAN order
            array = reformat(array)

            # Initialize as a ndarray-tied matrix.
            self.mat = cudamat()
            self.size = self.mat.size
            self.p_mat = ct.pointer(self.mat)
            self.numpy_array = array

            _cudamat.init_from_array(self.p_mat, array.ctypes.data_as(ct.POINTER(ct.c_float)), ct.c_int(array.shape[0]), ct.c_int(array.shape[1]))
            if copy_to_device:
                err_code = _cudamat.copy_to_device(self.p_mat)
                if err_code:
                    raise generate_exception(err_code)

        else:
            # Initialize based on existing cudamat structure.
            mat = array
            self.mat = mat
            self.p_mat = ct.pointer(self.mat)

        self.T = TransposedCUDAMatrix(self.mat)

        # Keep a reference to free device memory in case of a crash.
        self.__free_device_memory = _cudamat.free_device_memory


    @staticmethod
    def init_random(seed = 0):
        """
        Initialize and seed the random number generator.
        """

        NUM_RND_STREAMS = 96*128
        CUDAMatrix.rndInitialized = 1
        CUDAMatrix.rnd_state = rnd_struct()
        CUDAMatrix.rnd_state_p = ct.pointer(CUDAMatrix.rnd_state)

        cudamat_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'rnd_multipliers_32bit.txt')

        err_code = _cudamat.init_random(CUDAMatrix.rnd_state_p, ct.c_int(seed), cudamat_path)
        if err_code:
            raise generate_exception(err_code)

    @property
    def shape(self):
        return (self.mat.size[0], self.mat.size[1])

    def set_shape(self, shape):
        """
        Sets the shape of the array to the given array.
        Highly unsafe method. Does no checking.
        Do not use this unless you know what you are doing.
        """

        m = ct.c_uint(shape[0])
        n = ct.c_uint(shape[1])

        err_code = _cudamat.set_shape(self.p_mat, m, n)
        if err_code:
            raise generate_exception(err_code)

        return self

    def reshape(self, shape):
        """
        Reshapes self to have the given shape. The number of elements cannot
        change as this only changes how the contents are interpreted.
        """
        m, n = shape
        mlen = self.shape[0] * self.shape[1]
        if m == -1:
          assert n > 0 and mlen % n == 0
          m = mlen / n
        elif n == -1:
          assert m > 0 and mlen % m == 0
          n = mlen / m

        err_code = _cudamat.reshape(self.p_mat, ct.c_uint(m), ct.c_uint(n))
        if err_code:
            raise generate_exception(err_code)

        return self

    def blockify(source, blocksize, target = None):
        if target == None:
            target = source

        err_code = _cudamat.blockify(source.p_mat, target.p_mat, ct.c_uint(blocksize))

        if err_code:
            raise generate_exception(err_code)

        return target

    def generate_translations(source, source_w, target_w, off_x, off_y, target = None):
        num_channels = source.shape[0] / (source_w**2)

        if target == None:
            batch_s = source.shape[1]
            target = empty((target_w**2, batch_s))

        err_code = _cudamat.generate_translations_big_var_off(source.p_mat, target.p_mat, off_x.p_mat, off_y.p_mat, ct.c_uint(source_w), ct.c_uint(target_w), ct.c_uint(num_channels))

        if err_code:
            raise generate_exception(err_code)

        return target

    def asarray(self):
        """
        Copies the matrix to an ndarray on the CPU and returns it.
        """

        self.copy_to_host()

        return self.numpy_array

    def copy_to_device(self):
        """
        Copy the matrix to the GPU.
        """

        err_code = _cudamat.copy_to_device(self.p_mat)
        if err_code:
            raise generate_exception(err_code)

    def copy_to_host(self):
        """
        Copy the matrix to the CPU.
        """

        if not self.mat.on_host:
            # allocate host storage if necessary
            m = self.mat.size[0]
            n = self.mat.size[1]

            self.numpy_array = np.empty((m, n), dtype=np.float32, order = 'F')
            self.mat.data_host = self.numpy_array.ctypes.data_as(ct.POINTER(ct.c_float))

            self.mat.on_host = 1

        err_code = _cudamat.copy_to_host(self.p_mat)
        if err_code:
            raise generate_exception(err_code)

    def assign(self, val):
        """Assign val to self, where val can be a scalar or a CUDAMatrix
        with the same dimensions as self. """

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.copy_on_device(val.p_mat, self.p_mat)
        elif isinstance(val, (int, float)):
            err_code = _cudamat.assign_scalar(self.p_mat, ct.c_float(val))
        else:
            raise ValueError, "Assigned value must be of type CUDAMatrix, int, or float."
            
        if err_code:
            raise generate_exception(err_code)

        return self

    def free_device_memory(self):
        """
        Free memory used up by the matrix on the GPU.
        """

        err_code = _cudamat.free_device_memory(self.p_mat)
        if err_code:
            raise generate_exception(err_code)

    def set_trans(self, is_trans):
        """
        Set the transposedness flag to is_trans.
        """

        _cudamat.set_transpose(self.p_mat, ct.c_int(1 * is_trans))

    def slice(self, first_col, last_col):
        mat = cudamat()

        if self.mat.size[0] == 1 or self.mat.size[1] == 1:
            err_code = _cudamat.get_vector_slice(self.p_mat, ct.pointer(mat), ct.c_int(first_col), ct.c_int(last_col))
        else:
            err_code = _cudamat.get_slice(self.p_mat, ct.pointer(mat), ct.c_int(first_col), ct.c_int(last_col))

        if err_code:
            raise generate_exception(err_code)

        new_mat = CUDAMatrix(mat)

        try:
            new_mat.sliceof = self.sliceof
        except:
            new_mat.sliceof = self

        return new_mat

    def get_col_slice(self, first_col, last_col, target = None):
        col_slice = self.slice(first_col, last_col)

        if target:
            target.assign(col_slice)
            return target
        else:
            return col_slice

    def set_col_slice(self, first_col, last_col, mat):
        self.slice(first_col, last_col).assign(mat)

        return self

    def get_row_slice(self, start, end, target = None):
        """
        Get the rows with indices start through end. If target is not provided
        memory for a new matrix will be allocated.
        """

        width = self.shape[1]

        if not target:
            target = empty((end-start, width))

        err_code = _cudamat.get_row_slice(self.p_mat, target.p_mat, ct.c_int(start), ct.c_int(end))
        if err_code:
            raise generate_exception(err_code)

        return target

    def set_row_slice(self, start, end, mat):
        """
        Assign the contents of mat to the rows with indices start through end.
        """

        err_code = _cudamat.set_row_slice(mat.p_mat, self.p_mat, ct.c_int(start), ct.c_int(end))
        if err_code:
            raise generate_exception(err_code)

        return self

    def transpose(self, target = None):
        """
        Return a transposed copy of the matrix.
        """
        if not target:
            target = empty((self.shape[1], self.shape[0]))

        err_code = _cudamat.copy_transpose(self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target

    def fill_with_rand(self):
        """
        Fill matrix on the GPU with random numbers drawn from the uniform
        distribution over the (0,1) interval.
        """

        err_code = _cudamat.fill_with_rand(CUDAMatrix.rnd_state_p, self.p_mat) 
        if err_code:
            raise generate_exception(err_code)

        return self

    def fill_with_randn(self):
        """
        Fill matrix on the GPU with random numbers drawn from the standard normal
        distribution.
        """

        err_code = _cudamat.fill_with_randn(CUDAMatrix.rnd_state_p, self.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return self

    def dropout(self, dropprob, val=0.0):
        """
        Drop entries in this matrix uniformly randomly with given probability
        and set the dropped out unit to state val.
        """
        err_code = _cudamat.dropout(CUDAMatrix.rnd_state_p, self.p_mat,
                                    ct.c_float(dropprob), ct.c_float(val))
        if err_code:
            raise generate_exception(err_code)

        return self

    def sample_bernoulli(self, target=None):
        """
        Sample a bernoulli distribution. Choose 1 with probability given by entries of self, 0 otherwise.
        """
        if not target:
          target = self
        err_code = _cudamat.sample_bernoulli(CUDAMatrix.rnd_state_p, self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return self

    def sample_bernoulli_tanh(self, target=None):
        """
        Sample a bernoulli distribution. Choose 1 with probability given by entries of (1+self)/2, -1 otherwise.
        """
        if not target:
          target = self
        err_code = _cudamat.sample_bernoulli_tanh(CUDAMatrix.rnd_state_p, self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return self

    def sample_poisson(self, target=None):
        """
        Sample a poisson distribution. Choose 1 with probability given by entries of self.
        Not implemented yet.
        """
        if not target:
          target = self
        err_code = _cudamat.sample_poisson(CUDAMatrix.rnd_state_p, self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return self

    def sample_gaussian(self, mult=1.0, target=None):
        """
        Add zero mean gaussian noise to the matrix. mult is the stddev.
        """
        if not target:
          target = self
        err_code = _cudamat.sample_gaussian(CUDAMatrix.rnd_state_p, self.p_mat, target.p_mat, ct.c_float(mult))
        if err_code:
            raise generate_exception(err_code)

        return self

    def perturb_energy_for_softmax_sampling(self, target=None):
        """
        Add by -log(-log(rand)).
        """
        if not target:
          target = self
        err_code = _cudamat.perturb_energy(CUDAMatrix.rnd_state_p, self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return self

    def perturb_prob_for_softmax_sampling(self, target=None):
        """
        Divide by -log(rand).
        """
        if not target:
          target = self
        err_code = _cudamat.perturb_prob(CUDAMatrix.rnd_state_p, self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return self


    def add_col_vec(self, vec, target = None):
        """
        Add vector vec to every column of the matrix. If a target is provided,
        it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.add_col_vec(self.p_mat, vec.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target
        
    def add_col_mult(self, vec, mult, target = None):
        """
        Add a multiple of vector vec to every column of the matrix. If a target
        is provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.add_col_mult(self.p_mat, vec.p_mat, target.p_mat, ct.c_float(mult))
        if err_code:
            raise generate_exception(err_code)

        return target

    def mult_diagonal(self, val, target = None):
        """
        Mult val to the diagonal of self. If a target
        is provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        assert self.shape[0] == self.shape[1], 'self must be a square matrix'
        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.mult_diagonal(self.p_mat, val.p_mat, target.p_mat)
        elif isinstance(val, (int, float)):
            err_code = _cudamat.mult_diagonal_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."

        if err_code:
            raise generate_exception(err_code)

        return target



    def add_diagonal(self, val, target = None):
        """
        Add val to the diagonal of self. If a target
        is provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        assert self.shape[0] == self.shape[1], 'self must be a square matrix'
        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.add_diagonal(self.p_mat, val.p_mat, target.p_mat)
        elif isinstance(val, (int, float)):
            err_code = _cudamat.add_diagonal_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."

        if err_code:
            raise generate_exception(err_code)

        return target


    def add_row_mult(self, vec, mult, target = None):
        """
        Add a multiple of vector vec to every row of the matrix. If a target
        is provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.add_row_mult(self.p_mat, vec.p_mat, target.p_mat, ct.c_float(mult))
        if err_code:
            raise generate_exception(err_code)

        return target
        
    def add_row_vec(self, vec, target = None):
        """
        Add vector vec to every row of the matrix. If a target is provided,
        it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.add_row_vec(self.p_mat, vec.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target
        
    def mult_by_col(self, vec, target = None):
        """
        Multiply vector vec into every column of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.mult_by_col_vec(self.p_mat, vec.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target
        
    def mult_by_row(self, vec, target = None):
        """
        Multiply vector vec into every row of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.mult_by_row_vec(self.p_mat, vec.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target

    def div_by_col(self, vec, target = None):
        """
        Multiply vector vec into every column of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.div_by_col_vec(self.p_mat, vec.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target
        
    def div_by_row(self, vec, target = None):
        """
        Divide vector vec into every row of the matrix. If a target is
        provided, it is used to store the result instead of self.
        """

        if not target:
            target = self

        err_code = _cudamat.div_by_row_vec(self.p_mat, vec.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target
 
    def sum(self, axis=None, target = None):
        """
        Sum the matrix along the given dimension, where 0 represents the leading
        dimension and 1 represents the non-leading dimension. If None, the sum
        of all elements is returned. If a target is not prvided, a new vector is
        created for storing the result.
        """
        if axis is None:
          return vdot(self, CUDAMatrix.ones.slice(0, self.shape[0]*self.shape[1]))
        else:
          return sum(self, axis, target)

    def add_sums(self, mat, axis, mult = 1.):
        """
        Add a multiple of the sums of the matrix mat along the given dimension
        to self. 
        """

        m = _cudamat.get_leading_dimension(mat.p_mat)
        n = _cudamat.get_nonleading_dimension(mat.p_mat)

        if axis == 0:
            # sum along leading dimension
            left = CUDAMatrix.ones.slice(0, m)
            left.set_trans(True)
            right = mat
 
        elif axis == 1:
            # sum along non-leading dimension
            left = mat
            right = CUDAMatrix.ones.slice(0, n)

        err_code = _cudamat.dot(left.p_mat, right.p_mat, self.p_mat, ct.c_float(1.), ct.c_float(mult))
        if err_code:
            raise generate_exception(err_code)

        return self

    def less_than_eq(self, val, target = None):
        """
        Perform the operation target = 1. * (self < val), where val can be a matrix or a scalar.
        """

        if not target:
            target = self

        if isinstance(val, (int, float)):
            err_code = _cudamat.less_than_eq_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            err_code = _cudamat.less_than_eq(self.p_mat, val.p_mat, target.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target

    def less_than(self, val, target = None):
        """
        Perform the operation target = 1. * (self < val), where val can be a matrix or a scalar.
        """

        if not target:
            target = self

        if isinstance(val, (int, float)):
            err_code = _cudamat.less_than_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            err_code = _cudamat.less_than(self.p_mat, val.p_mat, target.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target

    def greater_than_eq(self, val, target = None):
        """
        Perform the operation target = 1. * (self > val), where val can be a matrix or a scalar.
        """

        if not target:
            target = self

        if isinstance(val, (int, float)):
            err_code = _cudamat.greater_than_eq_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            err_code = _cudamat.greater_than_eq(self.p_mat, val.p_mat, target.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target

    def greater_than(self, val, target = None):
        """
        Perform the operation target = 1. * (self > val), where val can be a matrix or a scalar.
        """

        if not target:
            target = self

        if isinstance(val, (int, float)):
            err_code = _cudamat.greater_than_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            err_code = _cudamat.greater_than(self.p_mat, val.p_mat, target.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target

    def upper_bound(self, val, target = None):
        """
        Perform the operation target = (self > val) ? val:self, where val can be a matrix or a scalar.
        """
        if not target:
            target = self

        if isinstance(val, (int, float)):
            err_code = _cudamat.upper_bound_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            err_code = _cudamat.upper_bound(self.p_mat, val.p_mat, target.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target


    def lower_bound(self, val, target = None):
        """
        Perform the operation target = (self < val) ? val:self, where val can be a matrix or a scalar.
        """
        if not target:
            target = self

        if isinstance(val, (int, float)):
            err_code = _cudamat.lower_bound_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            err_code = _cudamat.lower_bound(self.p_mat, val.p_mat, target.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target

    def cumsum(self, axis, temp=None, target = None):
        """
        Cumulative sum along axis.
        """

        m, n = self.shape
        assert axis == 0, 'axis = 1 not implemented.'
        if not target:
            target = empty((m, n))
        if not temp:
            temp = empty((m, n))
        """ 
        elif axis == 1:
            if not target:
                target = empty((m, 1))
        """ 

        err_code =  _cudamat.cumsum_by_axis(self.p_mat, target.p_mat, temp.p_mat, ct.c_int(axis))
        if err_code:
            raise generate_exception(err_code)

        return target

    def choose_max_and_accumulate(self, acc):
        """
        Find the maximum value along the given dimension, where 0 represents the
        leading dimension and 1 represents the non-leading dimension. If a target
        is not prvided, a new vector is created for storing the result.
        """

        m, n = self.shape

        err_code =  _cudamat.choose_max_and_accumulate(self.p_mat, acc.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return acc


    def choose_max(self, axis, target = None):
        """
        Sets the argmax along axis to 1 and rest to zero.
        """

        m, n = self.shape

        assert axis == 0, 'Axis = 1 not implemented.'
        if not target:
          target = self

        err_code =  _cudamat.choose_max_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
        if err_code:
            raise generate_exception(err_code)

        return target


    def max(self, axis, target = None):
        """
        Find the maximum value along the given dimension, where 0 represents the
        leading dimension and 1 represents the non-leading dimension. If a target
        is not prvided, a new vector is created for storing the result.
        """

        m, n = self.shape

        if axis == 0:
            if not target:
                target = empty((1, n))
 
        elif axis == 1:
            if not target:
                target = empty((m, 1))

        err_code =  _cudamat.max_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
        if err_code:
            raise generate_exception(err_code)

        return target

    def argmax(self, axis, target = None):
        """
        Find the index with the maximum value along the given dimension, where 0 represents the
        leading dimension and 1 represents the non-leading dimension. If a target
        is not prvided, a new vector is created for storing the result.
        """

        m, n = self.shape

        if axis == 0:
            if not target:
                target = empty((1, n))
 
        elif axis == 1:
            if not target:
                target = empty((m, 1))

        err_code =  _cudamat.argmax_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
        if err_code:
            raise generate_exception(err_code)

        return target

    def add_sqsums(self, mat, axis, mult = 1.):
        """
        Add the sum of squares of mat along the given dimension to self. 0 represents the
        leading dimension and 1 represents the non-leading dimension.
        """
        m, n = mat.shape
        if axis == 0:
          assert self.shape == (1, n), 'Self has shape %s but mat has shape %s' % (self.shape, mat.shape)
        elif axis == 1:
          assert self.shape == (m, 1)

        err_code =  _cudamat.sqsum_by_axis(mat.p_mat, self.p_mat,
                                           ct.c_int(axis), ct.c_float(mult),
                                           ct.c_float(1.0))
        if err_code:
            raise generate_exception(err_code)

    def sqsum(self, axis, target = None):
        """
        Find the sum of squares along the given dimension, where 0 represents the
        leading dimension and 1 represents the non-leading dimension. If a target
        is not prvided, a new vector is created for storing the result.
        """

        m, n = self.shape

        if axis == 0:
            if not target:
                target = empty((1, n))
 
        elif axis == 1:
            if not target:
                target = empty((m, 1))

        err_code =  _cudamat.sqsum_by_axis(self.p_mat, target.p_mat, ct.c_int(axis), 1.0, 0.0)
        if err_code:
            raise generate_exception(err_code)

        return target

    def norm_limit(self, norm, axis, target = None):
        """
        Limit the norm along the given dimension to be 'norm', where 0
        represents the leading dimension and 1 represents the non-leading
        dimension. If a target is not provided, self is used as target.
        """
        m, n = self.shape

        if not target:
            target = self
 
        err_code =  _cudamat.normlimit_by_axis(self.p_mat, target.p_mat,
                                               ct.c_int(axis), ct.c_float(norm))
        if err_code:
            raise generate_exception(err_code)

        return target


    def apply_softmax(self, target = None):
        """
        Apply the softmax activation function.
        """
        return softmax(self, target)

    def sign(self, target = None):
        """
        Find the sign of each element of the matrix.
        """

        if not target:
            target = empty((self.mat.size[0], self.mat.size[1]))

        err_code = _cudamat.sign(self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target

    def apply_cos(self, target = None):
        """
        Apply the cos sigmoid to each element of the matrix.
        """

        return cos(self, target)

    def apply_sin(self, target = None):
        """
        Apply the sin sigmoid to each element of the matrix.
        """

        return sin(self, target)

    def apply_sigmoid(self, target = None):
        """
        Apply the logistic sigmoid to each element of the matrix.
        """

        return sigmoid(self, target)

    def reciprocal(self, target = None):
        """
        Find the reciprocal of each element of the matrix.
        """

        if not target:
            target = self

        err_code = _cudamat.reciprocal(self.p_mat, target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target

    def dot(self, mat2, mult=1.0, target = None):
        """
        Multiply the matrix by mat2 from the right and multiply by scalar mult.
        """

        return dot(self, mat2, mult, target)

    def add_dot(self, m1, m2, mult=1.0):
        """
        Add the dot product of m1 and m2 to the matrix.
        """

        err_code = _cudamat.dot(m1.p_mat, m2.p_mat, self.p_mat, ct.c_float(1.), ct.c_float(mult))
        if err_code:
            raise generate_exception(err_code)

        return self

    def subtract_dot(self, m1, m2):
        """
        Subtract the dot product of m1 and m2 from the matrix.
        """

        err_code = _cudamat.dot(m1.p_mat, m2.p_mat, self.p_mat, ct.c_float(1.), ct.c_float(-1.))
        if err_code:
            raise generate_exception(err_code)

        return self

    def add_mult_sign(self, mat2, mult = 1.):
        """
        Add multiple of sign of mat2 to the matrix.
        """

        err_code = _cudamat.add_mult_sign(self.p_mat, mat2.p_mat, ct.c_float(mult))
        if err_code:
            raise generate_exception(err_code)

        return self

    def add_mult(self, mat2, mult = 1.):
        """
        Add multiple of mat2 to the matrix.
        """

        err_code = _cudamat.add_mult(self.p_mat, mat2.p_mat, ct.c_float(mult))
        if err_code:
            raise generate_exception(err_code)

        return self
    
    def subtract_mult(self, mat2, mult = 1.):
        """
        Subtract a multiple of mat2 from the matrix.
        """

        err_code = _cudamat.add_mult(self.p_mat, mat2.p_mat, ct.c_float(-1. * mult))
        if err_code:
            raise generate_exception(err_code)

        return self

    def add(self, val, target = None):
        """Add val to self, where val can be a scalar or a CUDAMatrix with the
        same dimensions as self. """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.add_elementwise(self.p_mat, val.p_mat, target.p_mat)
        elif isinstance(val, (int, float)):
            err_code = _cudamat.add_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."

        if err_code:
            raise generate_exception(err_code)

        return target

    def accumulate_columns(self, indices, target, mult=1.0, avg=False):
        if not target:
            target = self
        if avg:
          avgg = 1
        else:
          avgg = 0
        err_code = _cudamat.accumulate_columns(self.p_mat, indices.p_mat, target.p_mat, ct.c_float(mult), ct.c_int(avgg))
        if err_code:
            raise generate_exception(err_code)
        return target

    def expand(self, expansion_indices, target):

        err_code = _cudamat.expand(self.p_mat, expansion_indices.p_mat, target.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target

    def expand_and_add(self, val, expansion_indices, target = None, mult=1.0):

        if not target:
            target = self

        if isinstance(val, CUDAMatrix) and isinstance(expansion_indices, CUDAMatrix):
            err_code = _cudamat.expand_and_add(self.p_mat, val.p_mat, expansion_indices.p_mat, target.p_mat, ct.c_float(mult))
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."

        if err_code:
            raise generate_exception(err_code)

        return target

    def subtract(self, val, target = None):
        """Subtract val from self, where val can be a scalar or a CUDAMatrix with
        the same dimensions as self. """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.subtract_elementwise(self.p_mat, val.p_mat, target.p_mat)
        elif isinstance(val, (int, float)):
            err_code = _cudamat.add_scalar(self.p_mat, ct.c_float(-1*val), target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."

        if err_code:
            raise generate_exception(err_code)

        return target

    def divide(self, val, target = None):
        """Divide self by val, where val can be a scalar or a CUDAMatrix with the
        same dimensions as self. """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.divide_elementwise(self.p_mat, val.p_mat, target.p_mat)
        elif isinstance(val, (int, float)):
            err_code = _cudamat.divide_by_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."

        if err_code:
            raise generate_exception(err_code)

        return target

    def mult(self, val, target = None):
        """Multiply self by val, where val can be a scalar or a CUDAMatrix with
        the same dimensions as self. """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.mult_elementwise(self.p_mat, val.p_mat, target.p_mat)
        elif isinstance(val, (int, float)):
            err_code = _cudamat.mult_by_scalar(self.p_mat, ct.c_float(val), target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix, int, or float."

        if err_code:
            raise generate_exception(err_code)

        return target

    def apply_cos_deriv(self, val, target = None):
        """
        Apply cos derivative, where val is the activation of cos units.
        """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.apply_cos_deriv(self.p_mat, val.p_mat, target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target


    def apply_sin_deriv(self, val, target = None):
        """
        Apply sin derivative, where val is the activation of sin units.
        """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.apply_sin_deriv(self.p_mat, val.p_mat, target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target

    def get_softmax_correct(self, labels, target):
        """
        target[i] = 1, iff labels[i] is correctly predicted; 0 otherwise.
        """
        assert labels.shape == (1, self.shape[1])
        assert target.shape == labels.shape
        if isinstance(labels, CUDAMatrix):
            err_code = _cudamat.get_softmax_correct(self.p_mat, labels.p_mat, target.p_mat)
        else:
            raise ValueError, "labels must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target

    def get_softmax_cross_entropy(self, labels, target, tiny=1e-10):
        """
        target[i] = -log(self[label[i]] + tiny).
        """
        assert labels.shape == (1, self.shape[1])
        assert target.shape == labels.shape
        if isinstance(labels, CUDAMatrix):
            err_code = _cudamat.get_softmax_cross_entropy(self.p_mat, labels.p_mat, target.p_mat, ct.c_float(tiny))
        else:
            raise ValueError, "labels must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target



    def apply_softmax_grad(self, labels, target = None):
        """
        Apply softmax derivative, where labels are the correct labels.
        """
        if not target:
            target = self

        assert labels.shape == (1, self.shape[1])
        assert target.shape == self.shape
        if isinstance(labels, CUDAMatrix):
            err_code = _cudamat.apply_softmax_grad(self.p_mat, labels.p_mat, target.p_mat)
        else:
            raise ValueError, "labels must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target


    def apply_logistic_deriv(self, val, target = None):
        """
        Apply logistic derivative, where val is the activation of logistic units.
        """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.apply_logistic_deriv(self.p_mat, val.p_mat, target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target

    def apply_tanh_deriv(self, val, target = None):
        """
        Apply tanh derivative, where val is the activation of the units.
        """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.apply_tanh_deriv(self.p_mat, val.p_mat, target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target

    def apply_rectified_linear_deriv(self, val, target = None):
        """
        Apply rectified linear derivative, where val is the activation of the units.
        """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.apply_rectified_linear_deriv(self.p_mat, val.p_mat, target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target

    def apply_rectified_linear_smooth_deriv(self, val, target = None):
        """
        Apply rectified linear smooth derivative, where val is the activation of the units.
        """

        if not target:
            target = self

        if isinstance(val, CUDAMatrix):
            err_code = _cudamat.apply_rectified_linear_smooth_deriv(self.p_mat, val.p_mat, target.p_mat)
        else:
            raise ValueError, "Value must be of type CUDAMatrix."

        if err_code:
            raise generate_exception(err_code)

        return target

    @deprecated
    def assign_scalar(self, alpha):
        """
        Assign scalar alpha to every element of the matrix.
        """

        err_code = _cudamat.assign_scalar(self.p_mat, ct.c_float(alpha))
        if err_code:
            raise generate_exception(err_code)

        return self

    @deprecated
    def mult_by_scalar(self, alpha, target = None):
        """
        Multiply the matrix by a scalar.
        """

        if not target:
            target = self

        err_code = _cudamat.mult_by_scalar(self.p_mat, ct.c_float(alpha), target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target


    @deprecated
    def div_by_scalar(self, alpha, target = None):
        """
        Divide the matrix by a scalar.
        """

        if not target:
            target = self

        err_code = _cudamat.divide_by_scalar(self.p_mat, ct.c_float(alpha), target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target

    @deprecated
    def add_scalar(self, alpha, target = None):
        """
        Increment the matrix by a scalar.
        """

        if not target:
            target = self

        err_code = _cudamat.add_scalar(self.p_mat, ct.c_float(alpha), target.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return target

    def euclid_norm(self):
        err_code = ct.c_int(0)
        res = _cudamat.euclid_norm(self.p_mat, ct.byref(err_code))

        if err_code:
            raise generate_exception(err_code.value)

        return res

    def select_columns(self, indices, target):
        """
        copies some columns of self into target.
        <indices> must be a row vector. Its elements are float32's representing integers, e.g. "34.0" means the integer "34".
        after this call, for all r,c, target[r,c]=self[r,indices[c]].
        This returns target.
        Negative indices are interpreted in the usual Python way: all elements of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
        This does bounds checking, but out of bounds indices do not raise an exception (because the programmer was lazy). Instead, they result in NaN values in <target>.
        """

        err_code = _cudamat.selectRows(self.p_mat, target.p_mat, indices.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target


    def swap_columns(self, indices1, indices2, target):
        """
        swap columns at indices1 of self with columns at indices2 of target.
        <indices1> and <indices2> must be row vectors of equal length. Its elements are float32's representing integers, e.g. "34.0" means the integer "34".
        after this call, for all r,c, target[r,indices2[c]=self[r,indices1[c]].
        self can be same as target, but then the result will be non-deterministic if there is overlap between indices1 and indices2. Can be used for in-place shuffling by making sure indices1 and indices2 do not overlap.
        This returns target.
        Negative indices are interpreted in the usual Python way: all elements of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
        This does bounds checking, but out of bounds indices do not raise an exception (because the programmer was lazy). Instead, they result in NaN values in <target>.
        """
        assert indices1.shape == indices2.shape
        err_code = _cudamat.swapColumns(self.p_mat, target.p_mat, indices1.p_mat, indices2.p_mat)

        if err_code:
            raise generate_exception(err_code)

        return target

    def set_selected_columns(self, indices, source):
        """
        copies all columns of source into some columns of self.
        <indices> must be a row vector. Its elements are float32's representing
        integers, e.g. "34.0" means the integer "34". after this call, for all
        r,c, self[r,indices[c]]=source[r,c]. This returns self.
        Negative indices are interpreted in the usual Python way: all elements
        of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
        This does bounds checking, but out of bounds indices do not raise an
        exception (because the programmer was lazy). Instead, they result in NaN
        values in <self>.
        """

        err_code = _cudamat.setSelectedRows(self.p_mat, source.p_mat, indices.p_mat)
        if err_code:
            raise generate_exception(err_code)

        return self

def empty(shape):
    """
    Creates and returns a new CUDAMatrix with the given shape.
    """

    mat = cudamat()
    err_code = _cudamat.init_empty(ct.pointer(mat), ct.c_int(shape[0]), ct.c_int(shape[1]))

    if err_code:
        raise generate_exception(err_code)

    return CUDAMatrix(mat)

def sum(mat, axis, target = None):
    """
    Sum the matrix along the given dimension, where 0 represents the leading
    dimension and 1 represents the non-leading dimension. If a target is
    not prvided, a new vector is created for storing the result.
    """

    m = _cudamat.get_leading_dimension(mat.p_mat)
    n = _cudamat.get_nonleading_dimension(mat.p_mat)

    if axis == 0:
        # sum along leading dimension
        left = CUDAMatrix.ones.slice(0, m)
        left.set_trans(True)
        right = mat

        if not target:
            target = empty((1, n))
 
    elif axis == 1:
        # sum along non-leading dimension
        left = mat
        right = CUDAMatrix.ones.slice(0, n)

        if not target:
            target = empty((m, 1))

    err_code = _cudamat.dot(left.p_mat, right.p_mat, target.p_mat, ct.c_float(0.), ct.c_float(1.))
    if err_code:
        raise generate_exception(err_code)

    return target

def dot(m1, m2, mult=1.0, target = None):
    """
    Find the dot product between m1 and m2.
    """

    if not target:
        m = _cudamat.get_leading_dimension(m1.p_mat)
        n = _cudamat.get_nonleading_dimension(m2.p_mat)

        target = empty((m, n))

    err_code = _cudamat.dot(m1.p_mat, m2.p_mat, target.p_mat, ct.c_float(0.), ct.c_float(mult))
    if err_code:
        raise generate_exception(err_code)

    return target

def vdot(m1, m2):
    """
    Compute the vector dot product of matrices m1 and m2.
    """

    err_code = ct.c_int(0)
    res = _cudamat.vdot(m1.p_mat, m2.p_mat, ct.byref(err_code))

    if err_code:
        raise generate_exception(err_code.value)

    return res

def softmax(mat, target = None):
    """
    Apply cos to each element of the matrix mat.
    """

    if target:
      err_code = _cudamat.softmax(mat.p_mat, target.p_mat)
    else:
      err_code = _cudamat.softmax_overwrite(mat.p_mat)
      target = mat
    if err_code:
        raise generate_exception(err_code)
    return target

def cos(mat, target = None):
    """
    Apply cos to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_cos(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target



def sin(mat, target = None):
    """
    Apply sin to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_sin(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def sigmoid(mat, target = None):
    """
    Apply the logistic sigmoid to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_sigmoid(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def tanh(mat, target = None):
    """
    Apply the tanh to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_tanh(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def abs(mat, target = None):
    """
    Apply abs to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_abs(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def log_1_plus_exp(mat, target = None, exact=False):
    """
    Apply log(1+exp(x)) to each element of the matrix mat. If exact is True, use
    slow and accurate log and exp.
    """

    if not target:
        target = mat

    if exact:
      err_code = _cudamat.apply_log_1_plus_exp_exact(mat.p_mat, target.p_mat)
    else:
      err_code = _cudamat.apply_log_1_plus_exp(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def log(mat, tiny=0.0, target = None):
    """
    Find the natural logarithm of each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_log(mat.p_mat, target.p_mat, ct.c_float(tiny))
    if err_code:
        raise generate_exception(err_code)

    return target

def exp(mat, target = None):
    """
    Apply the exponential function to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_exp(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def ceil(mat, target = None):
    """
    Apply the ceil function to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_ceil(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def floor(mat, target = None):
    """
    Apply the floor function to each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_floor(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def sqrt(mat, target = None):
    """
    Compute the square root of each element of the matrix mat.
    """

    if not target:
        target = mat

    err_code = _cudamat.apply_sqrt(mat.p_mat, target.p_mat)
    if err_code:
        raise generate_exception(err_code)

    return target

def cross_entropy_bernoulli(mat, p, target = None, tiny=1e-10):
    """
    Compute -mat*log(p) - (1-mat).*log(1-p)
    """

    if not target:
        target = mat

    if isinstance(p, CUDAMatrix):
        err_code = _cudamat.compute_cross_entropy_bernoulli(mat.p_mat, p.p_mat, target.p_mat, ct.c_float(tiny))
    else:
        raise ValueError, "Value must be of type CUDAMatrix."

    if err_code:
        raise generate_exception(err_code)

    return target


def cross_entropy(mat, p, target = None, tiny=1e-10):
    """
    Compute -mat*log(p)
    """

    if not target:
        target = mat

    if isinstance(p, CUDAMatrix):
        err_code = _cudamat.compute_cross_entropy(mat.p_mat, p.p_mat, target.p_mat, ct.c_float(tiny))
    else:
        raise ValueError, "Value must be of type CUDAMatrix."

    if err_code:
        raise generate_exception(err_code)

    return target

def correct_preds(mat, p, target = None, cutoff=0.5):
    """
    Compute mat*(p >= 0.5) + (1-mat).*(p < 0.5)
    """

    if not target:
        target = mat

    if isinstance(p, CUDAMatrix):
        err_code = _cudamat.correct_preds(mat.p_mat, p.p_mat, target.p_mat, ct.c_float(cutoff))
    else:
        raise ValueError, "Value must be of type CUDAMatrix."

    if err_code:
        raise generate_exception(err_code)

    return target

def pow(mat, p, target = None):
    """
    If p is a scalar, compute the 'p'th power of each element of the matrix mat,
    otherwise raise each element of the matrix mat to the power given by the
    corresponding element of the matrix p.
    """

    if not target:
        target = mat

    if isinstance(p, CUDAMatrix):
        err_code = _cudamat.apply_pow_matrix(mat.p_mat, p.p_mat, target.p_mat)
    elif isinstance(p, (int, float)):
        err_code = _cudamat.apply_pow(mat.p_mat, ct.c_float(p), target.p_mat)
    else:
        raise ValueError, "Value must be of type CUDAMatrix, int, or float."

    if err_code:
        raise generate_exception(err_code)

    return target

def cuda_sync_threads():
    _cudamat.cuda_sync_threads()

def reformat(array):
    """
    Returns array as a float32 array in FORTRAN order.
    """

    return np.array(array, dtype=np.float32, order='F')

def cuda_set_device(dev_id):
    """
    Selects the CUDA device with the given ID.
    """

    err_code =  _cudamat.cuda_set_device(ct.c_int(dev_id))
    if err_code:
        raise generate_exception(err_code)

def cublas_init():
    """
    Initialize Cublas.
    """

    _cudamat.cublas_init()
    CUDAMatrix.ones = CUDAMatrix(np.ones((MAX_ONES, 1), dtype=np.float32, order = 'F'))

init = cublas_init

def cublas_shutdown():
    """
    Shut down Cublas.
    """

    CUDAMatrix.ones = 0
    _cudamat.cublas_shutdown()

shutdown = cublas_shutdown

########NEW FILE########
__FILENAME__ = cudamat_conv
import ctypes as ct
import math
import pdb
_ConvNet = ct.cdll.LoadLibrary('libcudamat_conv.so')

def convUp(images, filters, targets, numModulesX, paddingStart, moduleStride, numImgColors, numGroups=1):
  """
  images - (n_images, img_w**2 * n_chans)
  filters - (n_filters, filter_w**2 * n_chans)
  targets - (n_images, n_locs**2 * n_filters)
  numModulesX - Number of filter locations along an axis. = n_locs
  paddingStart - Set to k for a k-pixel border of zeros. Usually set to 0.
  moduleStride - stride to move the filters by. 
  numImgColors - n_chans
  """
  numImages = images.shape[0]
  numFilters = filters.shape[0]

  assert targets.shape == (numImages, numFilters * numModulesX * numModulesX), '%s %d %d-%d-%d' % (targets.shape.__str__(), numImages, numFilters, numModulesX, numModulesX)

  _ConvNet.convUp(images.p_mat, filters.p_mat, targets.p_mat, numModulesX,
                  -paddingStart, moduleStride, numImgColors, numGroups)

def convDown(hidSums, filters, targets, numModulesX, paddingStart, moduleStride, filterSizeX, imSizeX, numImgColors):
  """
  hidSums - (n_images, n_locs**2 * n_filters)
  filters - (n_filters, filter_w**2 * n_chans)
  targets - (n_images, img_w**2 * n_chans)
  """
  numGroups = 1
  numFilters = filters.shape[0]
  numImages = hidSums.shape[0] 
  numModules = numModulesX**2 

  assert paddingStart >= 0
  assert targets.shape == (numImages, numImgColors * imSizeX * imSizeX)

  _ConvNet.convDown(hidSums.p_mat, filters.p_mat, targets.p_mat, imSizeX,
                    -paddingStart, moduleStride, numImgColors, numGroups)


def convOutp(images, hidSums, targets, numModulesX, paddingStart, filterSizeX, moduleStride, numImgColors):
  """
  images - (n_images, img_w**2 * n_chans)
  hidSums - (n_images, n_locs**2 * n_filters)
  targets - (n_filters, filter_w**2 * n_chans)
  """
  numGroups = 1
  partialSum = 0
  numImages = images.shape[0]
  numFilters = hidSums.shape[1] / (numModulesX**2)

  assert targets.shape == (numFilters, numImgColors * filterSizeX * filterSizeX), '%s %d %d-%d-%d' % (targets.shape.__str__(), numFilters, numImgColors, filterSizeX, filterSizeX)
  _ConvNet.convOutp(images.p_mat, hidSums.p_mat, targets.p_mat, numModulesX, filterSizeX, -paddingStart, moduleStride, numImgColors, 1, 0)

def localUp(images, filters, targets, numModulesX, paddingStart, moduleStride, numImgColors, numGroups=1):
  """
  images - (n_images, img_w**2 * n_chans)
  filters - (n_filters, filter_w**2 * n_chans)
  targets - (n_images, n_locs**2 * n_filters)
  numModulesX - Number of filter locations along an axis. = n_locs
  paddingStart - Set to k for a k-pixel border of zeros. Usually set to 0.
  moduleStride - stride to move the filters by. 
  numImgColors - n_chans
  """
  numImages = images.shape[0]
  numFilters = filters.shape[0]

  assert targets.shape == (numImages, numFilters * numModulesX * numModulesX), '%s %d %d-%d-%d' % (targets.shape.__str__(), numImages, numFilters, numModulesX, numModulesX)

  _ConvNet.localUp(images.p_mat, filters.p_mat, targets.p_mat,
           numModulesX, -paddingStart, moduleStride, numImgColors, numGroups)

def localDown(hidSums, filters, targets, numModulesX, paddingStart, moduleStride, filterSizeX, imSizeX, numImgColors):
  """
  hidSums - (n_images, n_locs**2 * n_filters)
  filters - (n_filters, filter_w**2 * n_chans)
  targets - (n_images, img_w**2 * n_chans)
  """
  numGroups = 1
  numFilters = filters.shape[0]
  numImages = hidSums.shape[0] 
  numModules = numModulesX**2 

  assert paddingStart >= 0
  assert targets.shape == (numImages, numImgColors * imSizeX * imSizeX)

  _ConvNet.localDown(hidSums.p_mat, filters.p_mat, targets.p_mat,
            imSizeX, -paddingStart, moduleStride, numImgColors, numGroups)


def localOutp(images, hidSums, targets, numModulesX, paddingStart, filterSizeX, moduleStride, numImgColors):
  """
  images - (n_images, img_w**2 * n_chans)
  hidSums - (n_images, n_locs**2 * n_filters)
  targets - (n_filters, filter_w**2 * n_chans)
  """
  numGroups = 1
  partialSum = 0
  numImages = images.shape[0]
  numFilters = hidSums.shape[1] / (numModulesX**2)

  assert targets.shape == (numFilters, numModulesX**2 * numImgColors * filterSizeX**2), '%s %d %d-%d-%d' % (targets.shape.__str__(), numFilters, numImgColors, filterSizeX, filterSizeX)
  _ConvNet.localOutp(images.p_mat, hidSums.p_mat, targets.p_mat,
            numModulesX, filterSizeX, -paddingStart, moduleStride, numImgColors, numGroups, partialSum)



def MaxPool(images, targets, numChannels, subsX, startX, strideX, outputsX):
  """
  images - (n_images, img_w**2 * n_chans)
  numChannels - number of filter/color channels
  subsX - width of pooling area
  startX - pixel where pooling starts
  strideX - stride
  outputsX - number of pooling sites
  """
  numImages = images.shape[0]

  assert targets.shape == (numImages, numChannels * outputsX * outputsX)
  
  _ConvNet.MaxPool(images.p_mat, targets.p_mat,
           numChannels, subsX, startX, strideX, outputsX)

def ProbMaxPool(images, rnd, targets, numChannels, subsX, startX, strideX, outputsX):
  """
  images - (n_images, img_w**2 * n_chans)
  rnd - (n_images, img_w**2 * n_chans)
  numChannels - number of filter/color channels
  subsX - width of pooling area
  startX - pixel where pooling starts
  strideX - stride
  outputsX - number of pooling sites
  """
  numImages = images.shape[0]

  assert targets.shape == (numImages, numChannels * outputsX * outputsX)
  assert rnd.shape == images.shape

  _ConvNet.ProbMaxPool(images.p_mat, rnd.p_mat, targets.p_mat,
           numChannels, subsX, startX, strideX, outputsX)


def MaxPoolUndo(images, targets, grad, maxes,
        subsX, startX, strideX, outputsX):
  """
  images - (n_images, img_w**2 * n_chans)
  grad - (n_images, outputsX**2 * n_chans) cudamat of deltas/gradients of loss wrt layer outputs.
  maxes - (n_images, outputsX**2 * n_chans) cudamat of layer outputs.
  subsX - width of pooling area
  startX - pixel where pooling starts
  strideX - stride
  outputsX - number of pooling sites
  """
  assert targets.shape == images.shape

  _ConvNet.MaxPoolUndo(images.p_mat, grad.p_mat, maxes.p_mat, targets.p_mat,
             subsX, startX, strideX, outputsX)

def ResponseNorm(images, denoms, targets, numChannels, sizeX, addScale, powScale):
  assert targets.shape == images.shape
  assert targets.shape == denoms.shape
  num_images = images.shape[0]
  numpixels = images.shape[1] / numChannels
  imgsize = int(math.sqrt(numpixels))
  #assert images.shape[1] == numChannels * numpixels
  #assert imgsize * imgsize == numpixels
  #pdb.setrace()
  _ConvNet.ResponseNorm(images.p_mat, denoms.p_mat, targets.p_mat,
             numChannels, sizeX, ct.c_float(addScale),
             ct.c_float(powScale))

def ResponseNormUndo(outGrad, denoms, inGrad, acts, targets, numChannels, sizeX,
           addScale, powScale):
  assert targets.shape == outGrad.shape
  assert targets.shape == denoms.shape
  assert targets.shape == inGrad.shape
  assert targets.shape == acts.shape
  _ConvNet.ResponseNormUndo(outGrad.p_mat, denoms.p_mat, inGrad.p_mat,
               acts.p_mat, targets.p_mat, numChannels, sizeX,
               ct.c_float(addScale), ct.c_float(powScale))

########NEW FILE########
__FILENAME__ = nn_cudamat
# This file shows how to implement a single hidden layer neural network for
# performing binary classification on the GPU using cudamat.

import pdb
import time
import numpy as np
import cudamat as cm
from cudamat import learn as cl
import util

# initialize CUDA
cm.cublas_init()

# load data
util.load('mnist49.dat', globals())

# Put training data onto the GPU.
dat_train = dat_train/255.
dat_train = dat_train - (np.mean(dat_train, 1)+10**-8)[:, np.newaxis]
dev_train = cm.CUDAMatrix(dat_train)
dev_lbl = cm.CUDAMatrix(lbl_train)

# training parameters
epsilon = 0.01
momentum = 0.9

num_epochs = 30
batch_size = 128
num_batches = dat_train.shape[1]/batch_size

# model parameters
dim_in = dat_train.shape[0]
dim_out = 1
num_hid = 1024

# initialize weights
w_w1 = cm.CUDAMatrix(dim_in ** -0.5 * np.random.randn(dim_in, num_hid))
w_b1 = cm.CUDAMatrix(np.zeros((num_hid, 1)))
w_w2 = cm.CUDAMatrix(num_hid ** -0.5 * np.random.randn(num_hid, dim_out))
w_b2 = cm.CUDAMatrix(np.zeros((dim_out, 1)))

# initialize weight update matrices
wu_w1 = cm.CUDAMatrix(np.zeros(w_w1.shape))
wu_b1 = cm.CUDAMatrix(np.zeros(w_b1.shape))
wu_w2 = cm.CUDAMatrix(np.zeros(w_w2.shape))
wu_b2 = cm.CUDAMatrix(np.zeros(w_b2.shape))

# initialize temporary storage
h = cm.empty((num_hid, batch_size))
out = cm.empty((dim_out, batch_size))
delta = cm.empty((num_hid, batch_size))

# Train neural network.
start_time = time.time()
for epoch in range(num_epochs):
    print "Epoch " + str(epoch + 1)
    err = []

    for batch in range(num_batches):
        # get current minibatch
        inp = dev_train.slice(batch*batch_size,(batch + 1)*batch_size)
        target = dev_lbl.slice(batch*batch_size,(batch + 1)*batch_size)

        # apply momentum
        wu_w1.mult(momentum)
        wu_b1.mult(momentum)
        wu_w2.mult(momentum)
        wu_b2.mult(momentum)

        # forward pass
        cm.dot(w_w1.T, inp, target = h)

        h.add_col_vec(w_b1)
        h.apply_sigmoid()

        cm.dot(w_w2.T, h, target = out)

        out.add_col_vec(w_b2)
        out.apply_sigmoid()

        # back prop errors
        out.subtract(target) # compute error

        # gradients for w_w2 and w_b2
        wu_w2.add_dot(h, out.T)
        wu_b2.add_sums(out, axis = 1)

        # compute delta
        cm.dot(w_w2, out, target = delta)

        # delta = delta * h * (1 - h)
        cl.mult_by_sigmoid_deriv(delta, h)

        # gradients for w_w1 and w_b1
        wu_w1.add_dot(inp, delta.T)
        wu_b1.add_sums(delta, axis = 1)

        # update weights
        w_w1.subtract_mult(wu_w1, epsilon/batch_size)
        w_b1.subtract_mult(wu_b1, epsilon/batch_size)
        w_w2.subtract_mult(wu_w2, epsilon/batch_size)
        w_b2.subtract_mult(wu_b2, epsilon/batch_size)

        # calculate error on current minibatch 
        err.append(np.abs(out.asarray())>0.5)

    print "Training misclassification rate: " + str(np.mean(err))
    print "Time: " + str(time.time() - start_time)

# Evaluate neural network on test data.

# Load test data onto the GPU.
dat_test = dat_test/255.
dat_test = dat_test - np.mean(dat_test, 1)[:, np.newaxis]
dev_test = cm.CUDAMatrix(dat_test)
dev_lbl = cm.CUDAMatrix(lbl_test)

# Initalize temporary storage.
h = cm.empty((num_hid, dat_test.shape[1]))
out = cm.empty((dim_out, dat_test.shape[1]))

# forward pass
cm.dot(w_w1.T, dev_test, target = h)

h.add_col_vec(w_b1)
h.apply_sigmoid()

cm.dot(w_w2.T, h, target = out)

out.add_col_vec(w_b2)
out.apply_sigmoid()

# compute error
out.subtract(dev_lbl)

print "Testing misclassification rate: " + str(np.mean(np.abs(out.asarray())>0.5))

cm.cublas_shutdown()

########NEW FILE########
__FILENAME__ = rbm_cudamat
import time
import numpy as np
import cudamat as cm
import util

# initialize CUDA
cm.cublas_init()
cm.CUDAMatrix.init_random(1)

# load data
util.load('mnist.dat', globals())
dev_dat = cm.CUDAMatrix(cm.reformat(dat/255.))

# training parameters
epsilon = 0.1
momentum = 0.9

num_epochs = 3
batch_size = 128
num_batches = dat.shape[1]/batch_size

# model parameters
num_vis = dat.shape[0]
num_hid = 4096

# initialize weights
w_vh = cm.CUDAMatrix(0.1 * np.random.randn(num_vis, num_hid))
w_v = cm.CUDAMatrix(np.zeros((num_vis, 1)))
w_h = cm.CUDAMatrix(-4.*np.ones((num_hid, 1)))

# initialize weight updates
wu_vh = cm.CUDAMatrix(np.zeros((num_vis, num_hid)))
wu_v = cm.CUDAMatrix(np.zeros((num_vis, 1)))
wu_h = cm.CUDAMatrix(np.zeros((num_hid, 1)))

# initialize temporary storage
v = cm.empty((num_vis, batch_size))
h = cm.empty((num_hid, batch_size))
r = cm.empty((num_hid, batch_size))

start_time = time.time()
for epoch in range(num_epochs):
    print "Epoch " + str(epoch + 1)
    err = []

    for batch in range(num_batches):
        # get current minibatch
        v_true = dev_dat.slice(batch*batch_size,(batch + 1)*batch_size)
        v.assign(v_true)

        # apply momentum
        wu_vh.mult(momentum)
        wu_v.mult(momentum)
        wu_h.mult(momentum)

        # positive phase
        cm.dot(w_vh.T, v, target = h)
        h.add_col_vec(w_h)
        h.apply_sigmoid()

        wu_vh.add_dot(v, h.T)
        wu_v.add_sums(v, axis = 1)
        wu_h.add_sums(h, axis = 1)

        # sample hiddens
        r.fill_with_rand()
        r.less_than(h, target = h)

        # negative phase
        cm.dot(w_vh, h, target = v)
        v.add_col_vec(w_v)
        v.apply_sigmoid()

        cm.dot(w_vh.T, v, target = h)
        h.add_col_vec(w_h)
        h.apply_sigmoid()

        wu_vh.subtract_dot(v, h.T)
        wu_v.add_sums(v, axis = 1, mult = -1.)
        wu_h.add_sums(h, axis = 1, mult = -1.)

        # update weights
        w_vh.add_mult(wu_vh, epsilon/batch_size)
        w_v.add_mult(wu_v, epsilon/batch_size)
        w_h.add_mult(wu_h, epsilon/batch_size)

        # calculate reconstruction error
        v.subtract(v_true)
        err.append(v.euclid_norm()**2/(num_vis*batch_size))

    print "Mean squared error: " + str(np.mean(err))
    print "Time: " + str(time.time() - start_time)

w_vh.copy_to_host()
util.save('weights.dat', 'w_vh', {'w_vh': w_vh.numpy_array})

#cm.cublas_shutdown()

########NEW FILE########
__FILENAME__ = rbm_numpy
import time
import numpy as np
import util

# load data
util.load('mnist.dat', globals())
dat = dat/255.

# training parameters
epsilon = 0.01
momentum = 0.9

num_epochs = 10
batch_size = 64
num_batches = dat.shape[1]/batch_size

# model parameters
num_vis = dat.shape[0]
num_hid = 1024

# initialize weights
w_vh = 0.1 * np.random.randn(num_vis, num_hid)
w_v = np.zeros((num_vis, 1))
w_h = np.zeros((num_hid, 1))

# initialize weight updates
wu_vh = np.zeros((num_vis, num_hid))
wu_v = np.zeros((num_vis, 1))
wu_h = np.zeros((num_hid, 1))

start_time = time.time()
for epoch in range(num_epochs):
    print "Epoch " + str(epoch + 1)
    err = []

    for batch in range(num_batches):
        v_true = dat[:, batch*batch_size:(batch + 1)*batch_size]
        v = v_true

        # apply momentum
        wu_vh *= momentum
        wu_v *= momentum
        wu_h *= momentum

        # positive phase
        h = 1. / (1 + np.exp(-(np.dot(w_vh.T, v) + w_h)))

        wu_vh += np.dot(v, h.T)
        wu_v += v.sum(1)[:, np.newaxis]
        wu_h += h.sum(1)[:, np.newaxis]

        # sample hiddens
        h = 1. * (h > np.random.rand(num_hid, batch_size))

        # negative phase
        v = 1. / (1 + np.exp(-(np.dot(w_vh, h) + w_v)))
        h = 1. / (1 + np.exp(-(np.dot(w_vh.T, v) + w_h)))

        wu_vh -= np.dot(v, h.T)
        wu_v -= v.sum(1)[:, np.newaxis]
        wu_h -= h.sum(1)[:, np.newaxis]

        # update weights
        w_vh += epsilon/batch_size * wu_vh
        w_v += epsilon/batch_size * wu_v
        w_h += epsilon/batch_size * wu_h

        err.append(np.mean((v - v_true)**2))

    print "Mean squared error: " + str(np.mean(err))
    print "Time: " + str(time.time() - start_time)

########NEW FILE########
__FILENAME__ = test2
import numpy as np
import cudamat as cm

cm.cublas_init()

# create two random matrices and copy them to the GPU
a = cm.CUDAMatrix(np.random.rand(32, 256))
b = cm.CUDAMatrix(np.random.rand(256, 32))

# perform calculations on the GPU
c = cm.dot(a, b)
d = c.sum(axis = 0)

# copy d back to the host (CPU) and print
print d.asarray()

########NEW FILE########
__FILENAME__ = util
import gzip
import cPickle as pickle

def save(fname, var_list, source_dict):
    var_list = [var.strip() for var in var_list.split() if len(var.strip())>0]
    fo = gzip.GzipFile(fname, 'wb')
    pickle.dump(var_list, fo)
    for var in var_list:
        pickle.dump(source_dict[var], fo, protocol=2)
    fo.close()

def load(fname, target_dict, verbose = True):
    fo = gzip.GzipFile(fname, 'rb')
    var_list = pickle.load(fo)
    if verbose:
        print var_list
    for var in var_list:
        target_dict[var] = pickle.load(fo)
    fo.close()


########NEW FILE########
__FILENAME__ = gpu_lock
#!/usr/bin/python

"""
A simple discretionary locking system for /dev/nvidia devices.

Iain Murray, November 2009, January 2010.
"""

import os
import os.path

_dev_prefix = '/dev/nvidia'

# Get ID's of NVIDIA boards. Should do this through a CUDA call, but this is
# a quick and dirty way that works for now:
def board_ids():
    """Returns integer board ids available on this machine."""
    from glob import glob
    board_devs = glob(_dev_prefix + '[0-9]*')
    return range(len(board_devs))

def _lock_file(id):
    """lock file from integer id"""
    # /tmp is cleared on reboot on many systems, but it doesn't have to be
    if os.path.exists('/dev/shm'):
        # /dev/shm on linux machines is a RAM disk, so is definitely cleared
        return '/dev/shm/gpu_lock_%d' % id
    else:
        return '/tmp/gpu_lock_%d' % id

def owner_of_lock(id):
    """Username that has locked the device id. (Empty string if no lock)."""
    import pwd
    try:
        statinfo = os.lstat(_lock_file(id))
        return pwd.getpwuid(statinfo.st_uid).pw_name
    except:
        return ""

def _obtain_lock(id):
    """Attempts to lock id, returning success as True/False."""
    try:
        # On POSIX systems symlink creation is atomic, so this should be a
        # robust locking operation:
        os.symlink('/dev/null', _lock_file(id))
        return True
    except:
        return False

def _launch_reaper(id, pid):
    """Start a process that will free a lock when process pid terminates"""
    from subprocess import Popen, PIPE
    me = __file__
    if me.endswith('.pyc'):
        me = me[:-1]
    myloc = os.path.dirname(me)
    if not myloc:
        myloc = os.getcwd()
    reaper_cmd = os.path.join(myloc, 'run_on_me_or_pid_quit')
    Popen([reaper_cmd, str(pid), me, '--free', str(id)],
        stdout=open('/dev/null', 'w'))

def obtain_lock_id(pid = None):
    """
    Finds a free id, locks it and returns integer id, or -1 if none free.

    A process is spawned that will free the lock automatically when the
    process pid (by default the current python process) terminates.
    """
    id = -1
    id = obtain_lock_id_to_hog()
    try:
        if id >= 0:
            if pid is None:
                pid = os.getpid()
            _launch_reaper(id, pid)
    except:
        free_lock(id)
        id = -1
    return id

def obtain_lock_id_to_hog():
    """
    Finds a free id, locks it and returns integer id, or -1 if none free.

    * Lock must be freed manually *
    """
    for id in board_ids():
        if _obtain_lock(id):
            return id
    return -1

def free_lock(id):
    """Attempts to free lock id, returning success as True/False."""
    try:
        filename = _lock_file(id)
        # On POSIX systems os.rename is an atomic operation, so this is the safe
        # way to delete a lock:
        os.rename(filename, filename + '.redundant')
        os.remove(filename + '.redundant')
        return True
    except:
        return False


# If run as a program:
if __name__ == "__main__":
    import sys
    me = sys.argv[0]
    # Report
    if '--id' in sys.argv:
        if len(sys.argv) > 2:
            try:
                pid = int(sys.argv[2])
                assert(os.path.exists('/proc/%d' % pid))
            except:
                print 'Usage: %s --id [pid_to_wait_on]' % me
                print 'The optional process id must exist if specified.'
                print 'Otherwise the id of the parent process is used.'
                sys.exit(1)
        else:
            pid = os.getppid()
        print obtain_lock_id(pid)
    elif '--id-to-hog' in sys.argv:
        print obtain_lock_id_to_hog()
    elif '--free' in sys.argv:
        try:
            id = int(sys.argv[2])
        except:
            print 'Usage: %s --free <id>' % me
            sys.exit(1)
        if free_lock(id):
            print "Lock freed"
        else:
            owner = owner_of_lock(id)
            if owner:
                print "Failed to free lock id=%d owned by %s" % (id, owner)
            else:
                print "Failed to free lock, but it wasn't actually set?"
    else:
        print '\n  Usage instructions:\n'
        print '  To obtain and lock an id: %s --id' % me
        print '  The lock is automatically freed when the parent terminates'
        print
        print "  To get an id that won't be freed: %s --id-to-hog" % me
        print "  You *must* manually free these ids: %s --free <id>\n" % me
        print '  More info: http://www.cs.toronto.edu/~murray/code/gpu_monitoring/\n'
        div = '  ' + "-"*60
        print '\n' + div
        print "  NVIDIA board users:"
        print div
        for id in board_ids():
            print "      Board %d: %s" % (id, owner_of_lock(id))
        print div + '\n'

########NEW FILE########
__FILENAME__ = gpu_lock2
#!/usr/bin/python

"""
A simple discretionary locking system for /dev/nvidia devices.

Iain Murray, November 2009, January 2010.

-- Additions -- Charlie Tang, Jan, 2011: 
added display of GPU usages

-- Charlie Tang, July, 2011:
improved statistics displaying
"""

import os
import os.path
from xml.dom import Node
from xml.dom.minidom import parseString
from subprocess import Popen, PIPE, STDOUT

_dev_prefix = '/dev/nvidia'

# Get ID's of NVIDIA boards. Should do this through a CUDA call, but this is
# a quick and dirty way that works for now:
def board_ids():
    """Returns integer board ids available on this machine."""
    #from glob import glob
    #board_devs = glob(_dev_prefix + '[0-9]*')
    #return range(len(board_devs))
    p = Popen(['/u/tang/bin/get_num_gpu_boards'], stdout=PIPE)    
    nBoards = int(p.stdout.read())
    return range(nBoards)

def _lock_file(id):
    """lock file from integer id"""
    # /tmp is cleared on reboot on many systems, but it doesn't have to be
    if os.path.exists('/dev/shm'):
        # /dev/shm on linux machines is a RAM disk, so is definitely cleared
        return '/dev/shm/gpu_lock_%d' % id
    else:
        return '/tmp/gpu_lock_%d' % id

def owner_of_lock(id):
    """Username that has locked the device id. (Empty string if no lock)."""
    import pwd
    try:
        statinfo = os.lstat(_lock_file(id))
        return pwd.getpwuid(statinfo.st_uid).pw_name
    except:
        return ""

def _obtain_lock(id):
    """Attempts to lock id, returning success as True/False."""
    try:
        # On POSIX systems symlink creation is atomic, so this should be a
        # robust locking operation:
        os.symlink('/dev/null', _lock_file(id))
        return True
    except:
        return False

def _launch_reaper(id, pid):
    """Start a process that will free a lock when process pid terminates"""
    from subprocess import Popen, PIPE
    me = __file__
    if me.endswith('.pyc'):
        me = me[:-1]
    myloc = os.path.dirname(me)
    if not myloc:
        myloc = os.getcwd()
    reaper_cmd = os.path.join(myloc, 'run_on_me_or_pid_quit')
    Popen([reaper_cmd, str(pid), me, '--free', str(id)],
        stdout=open('/dev/null', 'w'))

def obtain_lock_id(pid=None):
    """
    Finds a free id, locks it and returns integer id, or -1 if none free.

    A process is spawned that will free the lock automatically when the
    process pid (by default the current python process) terminates.
    """
    id = -1
    id = obtain_lock_id_to_hog()
    try:
        if id >= 0:
            if pid is None:
                pid = os.getpid()
            _launch_reaper(id, pid)
    except:
        free_lock(id)
        id = -1
    return id

def obtain_lock_id_to_hog():
    """
    Finds a free id, locks it and returns integer id, or -1 if none free.

    * Lock must be freed manually *
    """
    for id in board_ids():
        if _obtain_lock(id):
            return id
    return -1

def free_lock(id):
    """Attempts to free lock id, returning success as True/False."""
    try:
        filename = _lock_file(id)
        # On POSIX systems os.rename is an atomic operation, so this is the safe
        # way to delete a lock:
        os.rename(filename, filename + '.redundant')
        os.remove(filename + '.redundant')
        return True
    except:
        return False

def nvidia_gpu_stats():    
    p = Popen(['nvidia-smi', '-x', '-a'], stdout=PIPE)    
    output = p.stdout.read().lstrip()
    try:
        doc = parseString(output)
        gpucounter = 0        
        templist = []
        memlist = []
        uselist = []        
        fanlist = []
        doc2 = doc.getElementsByTagName("nvidia_smi_log")[0]
        gpulist = doc2.getElementsByTagName("gpu")
        for gpu in gpulist:        
            temp = gpu.getElementsByTagName('temperature')[0]            
            temp2 = temp.getElementsByTagName('gpu_temp')[0]
            templist.append(str(temp2.firstChild.toxml()))            
            mem = gpu.getElementsByTagName('memory_usage')[0]               
            memtot = mem.getElementsByTagName('total')[0]
            memused = mem.getElementsByTagName('used')[0]
            memfree = mem.getElementsByTagName('free')[0]            
            memtot_str = str(memtot.firstChild.toxml())
            memused_str = str(memused.firstChild.toxml())
            memfree_str = str(memfree.firstChild.toxml())
            memtot_float = float(memtot_str[:-3])            
            memused_float = float(memused_str[:-3])
            memfree_float = float(memfree_str[:-3])
            memlist.append('%03.f' % memused_float + '+%03.f' % memfree_float + '=%03.f' % memtot_float + 'Mb')
            use = gpu.getElementsByTagName('gpu_util')[0]        
            uselist.append(str(use.firstChild.toxml()))
            fan = gpu.getElementsByTagName('fan_speed')[0]
            fanlist.append(str(fan.firstChild.toxml()))
            gpucounter += 1
                    
        return [uselist, memlist, fanlist, templist]
    except:        
        return [ [-9999] * len(board_ids()) ] *4
       
         
# If run as a program:
if __name__ == "__main__":
    
    div = '  ' + "-" * 90    
    import sys
    me = sys.argv[0]
    # Report
    if '--id' in sys.argv:
        if len(sys.argv) > 2:
            try:
                pid = int(sys.argv[2])
                assert(os.path.exists('/proc/%d' % pid))
            except:
                print 'Usage: %s --id [pid_to_wait_on]' % me
                print 'The optional process id must exist if specified.'
                print 'Otherwise the id of the parent process is used.'
                sys.exit(1)
        else:
            pid = os.getppid()
        print obtain_lock_id(pid)
    elif '--ids' in sys.argv:
        try:
            id = int(sys.argv[2])            
        except:
            print 'Usage: %s --ids [specific gpu id]' % me
            sys.exit(1)       
        if _obtain_lock(id):
            print id
        else:
            print - 1
    elif '--id-to-hog' in sys.argv:
        print obtain_lock_id_to_hog()
    elif '--free' in sys.argv:
        try:
            id = int(sys.argv[2])
        except:
            print 'Usage: %s --free <id>' % me
            sys.exit(1)
        if free_lock(id):
            print "Lock freed"
        else:
            owner = owner_of_lock(id)
            if owner:
                print "Failed to free lock id=%d owned by %s" % (id, owner)        
            else:
                print "Failed to free lock, but it wasn't actually set?"
    elif '--noverbose' in sys.argv:
        stats = nvidia_gpu_stats()        
        print div
        print "%s board users:" % 'abc'
        print div       
        for id in board_ids():         
            print "      Board %d {Use:%s; Mem:%s; Temp:%s}: %s" % (id, stats[0][id], stats[1][id], stats[2][id], owner_of_lock(id))
        print div + '\n'
    else:
        stats = nvidia_gpu_stats()
        print div      
        print '  Usage instructions:\n'        
        print '  To obtain and lock an id: %s --id' % me
        print '  The lock is automatically freed when the parent terminates'
        print
        print "  To get an id that won't be freed: %s --id-to-hog <id>" % me
        print "  To get a specific id: %s --ids <id>" % me        
        print                                                   
        print "  You *must* manually free these ids: %s --free <id>\n" % me
        print '  More info: http://www.cs.toronto.edu/~murray/code/gpu_monitoring/'
        print '  Report any problems to: tang@cs.toronto.edu'    
        print '\n' + div
        print "  NVIDIA board users:"
        print div
        for id in board_ids():         
            print "  Board %d {Use:%s; Mem(used+free=total): %s; Fan:%s; Temp:%s}: %s" % (id, stats[0][id], stats[1][id], stats[2][id], stats[3][id], owner_of_lock(id))
        print div + '\n'



########NEW FILE########
__FILENAME__ = test_cudamat
import pdb
import numpy as np
import nose
import cudamat as cm

def setup():
    cm.cublas_init()

def teardown():
    cm.cublas_shutdown()

def test_reshape():
    m = 256
    n = 1
    cm1 = np.array(np.random.rand(n, m)*10, dtype=np.float32, order='F')
    cm2 = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')

    gm1 = cm.CUDAMatrix(cm1)
    gm2 = cm.CUDAMatrix(cm2)

    gm1.reshape((m, n))
    gm2.assign(gm1)
    gm1.reshape((n, m))

    gm1.copy_to_host()
    gm2.copy_to_host()

    assert np.max(np.abs(gm1.numpy_array - gm2.numpy_array.T)) < 10**-2, "Error in CUDAMatrix.reshape exceeded threshold"

def test_T_field():
    m = 256
    n = 128
    cm1 = np.array(np.random.rand(n, m)*10, dtype=np.float32, order='F')
    cm2 = np.array(np.random.rand(m, 1)*10, dtype=np.float32, order='F')
    gm1 = cm.CUDAMatrix(cm1)
    gm2 = cm.CUDAMatrix(cm2)

    # test dot
    gm = cm.dot(gm2.T, gm1.T)
    c = np.dot(cm2.T, cm1.T)
    gm.copy_to_host()

    assert np.max(np.abs(gm.numpy_array - c)) < 10**-2, "Error in CUDAMatrix.dot with TransposedCUDAMatrix exceeded threshold"

    # test add_dot
    cm3 = np.array(np.random.rand(1, n)*10, dtype=np.float32, order='F')
    gm3 = cm.CUDAMatrix(cm3)
    gm3.add_dot(gm2.T, gm1.T)
    c = cm3 + np.dot(cm2.T, cm1.T)
    gm3.copy_to_host()

    assert np.max(np.abs(gm3.numpy_array - c)) < 10**-2, "Error in CUDAMatrix.add_dot TransposedCUDAMatrix exceeded threshold"

    # test add_sums
    gm2.add_sums(gm1.T, axis = 1)
    c = cm2 + np.atleast_2d(cm1.sum(0)).T
    gm2.copy_to_host()

    assert np.max(np.abs(gm2.numpy_array - c)) < 10**-2, "Error in CUDAMatrix.add_sums TransposedCUDAMatrix exceeded threshold"

def test_assign():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)

    m1.assign(m2)
    m1.copy_to_host()

    assert np.max(np.abs(m1.numpy_array - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.assign exceeded threshold"

def test_assign_scalar():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    m1 = cm.CUDAMatrix(a)

    m1.assign(np.pi)
    m1.copy_to_host()

    assert np.max(np.abs(m1.numpy_array - np.pi)) < 10**-4, "Error in CUDAMatrix.assign_scalar exceeded threshold"

def test_get_row_slice():
    m = 256
    n = 128
    start = 11
    end = 54

    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(end-start, n)*10, dtype=np.float32, order='F')
    
    c = np.array(a[start:end,:], order='F')
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m1.get_row_slice(start, end, target = m2)
    m3 = m1.get_row_slice(start, end)
    m2.copy_to_host()
    m3.copy_to_host()

    #pdb.set_trace()
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.get_row_slice exceeded threshold"
    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.get_row_slice exceeded threshold"

def test_set_row_slice():
    m = 256
    n = 128
    start = 11
    end = 54

    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(end-start, n)*10, dtype=np.float32, order='F')
    
    c = a.copy()
    c[start:end,:] = b
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m1.set_row_slice(start, end, m2)
    m1.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.set_row_slice exceeded threshold"

def test_transpose():
    m = 6
    n = 128

    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(n, m), dtype=np.float32, order='F')
    
    c = a.copy().T
    
    m = cm.CUDAMatrix(a)
    mt1 = cm.CUDAMatrix(b)
    m.transpose(target = mt1)
    mt2 = m.transpose()

    mt1.copy_to_host()
    mt2.copy_to_host()

    assert np.max(np.abs(c - mt1.numpy_array)) < 10**-4, "Error in CUDAMatrix.transpose exceeded threshold"
    assert np.max(np.abs(c - mt2.numpy_array)) < 10**-4, "Error in CUDAMatrix.transpose exceeded threshold"

def test_slice():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    c = np.array(a[:,32:64], order='F')
    
    m1 = cm.CUDAMatrix(a)
    m2 = m1.slice(32, 64)
    m2.copy_to_host()

    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.slice exceeded threshold"


def test_add_col_vec():
    m = 250
    n = 120
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, 1)*10, dtype=np.float32, order='F')
    t = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    c = a + b
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.add_col_vec(m2, target = m3)
    m1.add_col_vec(m2)
    m1.copy_to_host()
    m3.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_col_vec exceeded threshold"
    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_col_vec exceeded threshold"

def test_add_col_mult():
    m = 256
    n = 128
    mult = np.pi
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, 1)*10, dtype=np.float32, order='F')
    t = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    c = a + mult * b
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.add_col_mult(m2, mult, target = m3)
    m1.add_col_mult(m2, mult)
    m1.copy_to_host()
    m3.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_col_mult exceeded threshold"
    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_col_mult exceeded threshold"

def test_add_row_vec():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(1, n)*10, dtype=np.float32, order='F')
    t = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    c = a + b
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.add_row_vec(m2, target = m3)
    m1.add_row_vec(m2)
    m1.copy_to_host()
    m3.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_row_vec exceeded threshold"
    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_row_vec exceeded threshold"

def test_mult_by_col():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, 1)*10, dtype=np.float32, order='F')
    t = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    c = a * b
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.mult_by_col(m2, target = m3)
    m1.mult_by_col(m2)
    m1.copy_to_host()
    m3.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.mult_by_col exceeded threshold"
    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.mult_by_col exceeded threshold"

def test_mult_by_row():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.rand(1, n)*10, dtype=np.float32, order='F')
    t = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    c = a * b
    
    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.mult_by_row(m2, target = m3)
    m1.mult_by_row(m2)
    m1.copy_to_host()
    m3.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.mult_by_row exceeded threshold"
    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.mult_by_row exceeded threshold"

def test_sum():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    t1 = np.array(np.random.rand(1, n)*10, dtype=np.float32, order='F')
    t2 = np.array(np.random.rand(m, 1)*10, dtype=np.float32, order='F')
    
    c1 = np.atleast_2d(a.sum(0))
    c2 = np.atleast_2d(a.sum(1)).T
    
    m = cm.CUDAMatrix(a)
    mt1 = cm.CUDAMatrix(t1)
    mt2 = cm.CUDAMatrix(t2)

    m.sum(axis = 0, target = mt1)
    mt1r = m.sum(axis = 0)

    m.sum(axis = 1, target = mt2)
    mt2r = m.sum(axis = 1)

    mt1.copy_to_host()
    mt1r.copy_to_host()
    mt2.copy_to_host()
    mt2r.copy_to_host()

    assert np.max(np.abs(c1 - mt1.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"
    assert np.max(np.abs(c1 - mt1r.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"
    assert np.max(np.abs(c2 - mt2.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"
    assert np.max(np.abs(c2 - mt2r.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"

def test_sum_trans():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    t1 = np.array(np.random.rand(1, m)*10, dtype=np.float32, order='F')
    t2 = np.array(np.random.rand(n, 1)*10, dtype=np.float32, order='F')
    
    c1 = np.atleast_2d(a.T.sum(0))
    c2 = np.atleast_2d(a.T.sum(1)).T
    
    m = cm.CUDAMatrix(a)
    m.set_trans(True)
    mt1 = cm.CUDAMatrix(t1)
    mt2 = cm.CUDAMatrix(t2)

    m.sum(axis = 0, target = mt1)
    mt1r = m.sum(axis = 0)

    m.sum(axis = 1, target = mt2)
    mt2r = m.sum(axis = 1)

    mt1.copy_to_host()
    mt1r.copy_to_host()
    mt2.copy_to_host()
    mt2r.copy_to_host()

    assert np.max(np.abs(c1 - mt1.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"
    assert np.max(np.abs(c1 - mt1r.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"
    assert np.max(np.abs(c2 - mt2.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"
    assert np.max(np.abs(c2 - mt2r.numpy_array)) < 10**-3, "Error in CUDAMatrix.sum exceeded threshold"

def test_add_sums():
    m = 256
    n = 128

    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    t1 = np.array(np.random.rand(m, 1)*10, dtype=np.float32, order='F')
    t2 = np.array(np.random.rand(1, n)*10, dtype=np.float32, order='F')

    mult = np.pi
    
    c1 = t1 + mult * np.atleast_2d(a.sum(1)).T
    c2 = t2 + np.atleast_2d(a.sum(0))
    
    m = cm.CUDAMatrix(a)
    mt1 = cm.CUDAMatrix(t1)
    mt2 = cm.CUDAMatrix(t2)

    mt1.add_sums(m, axis = 1, mult = np.pi)
    mt2.add_sums(m, axis = 0)

    mt1.copy_to_host()
    mt2.copy_to_host()

    assert np.max(np.abs(c1 - mt1.numpy_array)) < 10**-3, "Error in CUDAMatrix.add_sums exceeded threshold"
    assert np.max(np.abs(c2 - mt2.numpy_array)) < 10**-3, "Error in CUDAMatrix.add_sums exceeded threshold"


def test_less_than():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t1 = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t2 = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    v = 0.1

    r1 = 1 * (a < b)
    r2 = 1 * (a < v)

    da = cm.CUDAMatrix(a)
    db = cm.CUDAMatrix(b)
    dt1 = cm.CUDAMatrix(t1)
    dt2 = cm.CUDAMatrix(t2)

    da.less_than(db, target = dt1)
    da.less_than(v, target = dt2)
    da.less_than(db)

    da.copy_to_host()
    dt1.copy_to_host()
    dt2.copy_to_host()

    assert np.max(np.abs(r1 - da.numpy_array)) < 10**-4, "Error in CUDAMatrix.less_than exceeded threshold"
    assert np.max(np.abs(r1 - dt1.numpy_array)) < 10**-4, "Error in CUDAMatrix.less_than exceeded threshold"
    assert np.max(np.abs(r2 - dt2.numpy_array)) < 10**-4, "Error in CUDAMatrix.less_than exceeded threshold"

def test_greater_than():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t1 = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t2 = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    v = 0.1

    r1 = 1 * (a > b)
    r2 = 1 * (a > v)

    da = cm.CUDAMatrix(a)
    db = cm.CUDAMatrix(b)
    dt1 = cm.CUDAMatrix(t1)
    dt2 = cm.CUDAMatrix(t2)

    da.greater_than(db, target = dt1)
    da.greater_than(v, target = dt2)
    da.greater_than(db)

    da.copy_to_host()
    dt1.copy_to_host()
    dt2.copy_to_host()

    assert np.max(np.abs(r1 - da.numpy_array)) < 10**-4, "Error in CUDAMatrix.greater_than exceeded threshold"
    assert np.max(np.abs(r1 - dt1.numpy_array)) < 10**-4, "Error in CUDAMatrix.greater_than exceeded threshold"
    assert np.max(np.abs(r2 - dt2.numpy_array)) < 10**-4, "Error in CUDAMatrix.greater_than exceeded threshold"

def test_max():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.random.rand(1, n)*10, dtype=np.float32, order='F')
   
    r = np.atleast_2d(a.max(0)) 
    
    da = cm.CUDAMatrix(a)
    dr1 = cm.CUDAMatrix(t)

    da.max(axis = 0, target = dr1)
    dr2 = da.max(axis = 0)

    dr1.copy_to_host()
    dr2.copy_to_host()

    assert np.max(np.abs(r - dr1.numpy_array)) < 10**-4, "Error in CUDAMatrix.max exceeded threshold"
    assert np.max(np.abs(r - dr2.numpy_array)) < 10**-4, "Error in CUDAMatrix.max exceeded threshold"

def test_max2():
    m = 256
    n = 128
    a = np.array(-np.random.rand(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.random.rand(1, n)*10, dtype=np.float32, order='F')
   
    r = np.atleast_2d(a.max(0)) 
    
    da = cm.CUDAMatrix(a)
    dr1 = cm.CUDAMatrix(t)

    da.max(axis = 0, target = dr1)
    dr2 = da.max(axis = 0)

    dr1.copy_to_host()
    dr2.copy_to_host()

    assert np.max(np.abs(r - dr1.numpy_array)) < 10**-4, "Error in CUDAMatrix.max exceeded threshold"
    assert np.max(np.abs(r - dr2.numpy_array)) < 10**-4, "Error in CUDAMatrix.max exceeded threshold"

def test_sign():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    a[0,0] = 0.
    a[0,1] = -0.
    t = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')

    c = np.sign(a)

    m1 = cm.CUDAMatrix(a)
    m3 = cm.CUDAMatrix(t)

    m2 = m1.sign()
    m1.sign(target = m3)

    m2.copy_to_host()
    m3.copy_to_host()

    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.sign exceeded threshold"
    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.sign exceeded threshold"

def test_sigmoid():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')

    c = 1. / (1. + np.exp(-a))

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m1.apply_sigmoid(target = m2)
    m1.apply_sigmoid()

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.apply_sigmoid exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.apply_sigmoid exceeded threshold"

def test_log():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10+0.1, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, n)*10+0.1, dtype=np.float32, order='F')

    c = np.log(a)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    cm.log(m1, target = m2)
    cm.log(m1)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in cudamat.log exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in cudamat.log exceeded threshold"

def test_exp():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n), dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n), dtype=np.float32, order='F')

    c = np.exp(a)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    cm.exp(m1, target = m2)
    cm.exp(m1)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in cudamat.exp exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in cudamat.exp exceeded threshold"

def test_sqrt():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*20, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, n), dtype=np.float32, order='F')

    c = np.sqrt(a)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    cm.sqrt(m1, target = m2)
    cm.sqrt(m1)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in cudamat.sqrt exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in cudamat.sqrt exceeded threshold"

def test_pow():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*20, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, n), dtype=np.float32, order='F')
    p = 2

    c = a**p

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    cm.pow(m1, p, target = m2)
    cm.pow(m1, p)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-3, "Error in cudamat.pow exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-3, "Error in cudamat.pow exceeded threshold"

def test_pow_matrix():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*20, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, n), dtype=np.float32, order='F')
    p = np.array(np.random.randn(m, n), dtype=np.float32, order='F')


    c = a**p

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    mp = cm.CUDAMatrix(p)
    cm.pow(m1, mp, target = m2)
    cm.pow(m1, mp)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-2, "Error in cudamat.pow exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-2, "Error in cudamat.pow exceeded threshold"

def test_reciprocal():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10+10**-3, dtype=np.float32, order='F')
    b = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')

    c = 1. / a

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m1.reciprocal(target = m2)
    m1.reciprocal()

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.reciprocal exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.reciprocal exceeded threshold"

def test_add_mult():
    m = 256
    n = 128
    alpha = np.pi
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')

    c = a + np.pi * b

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m1.add_mult(m2, np.pi)
    m1.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_mult exceeded threshold"

def test_subtract_mult():
    m = 256
    n = 128
    alpha = np.pi
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')

    c = a - np.pi * b

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m1.subtract_mult(m2, np.pi)
    m1.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.subtract_mult exceeded threshold"

def test_add():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(1.+np.random.rand(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.empty((m, n)), dtype=np.float32, order='F')

    c = a + b

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.add(m2, target = m3)
    m1.add(m2)

    m3.copy_to_host()
    m1.copy_to_host()

    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.add exceeded threshold"
    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.add exceeded threshold"

def test_subtract():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(1.+np.random.rand(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.empty((m, n)), dtype=np.float32, order='F')

    c = a - b

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.subtract(m2, target = m3)
    m1.subtract(m2)

    m3.copy_to_host()
    m1.copy_to_host()

    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.subtract exceeded threshold"
    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.subtract exceeded threshold"

def test_divide():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(1.+np.random.rand(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.empty((m, n)), dtype=np.float32, order='F')

    c = a / b

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.divide(m2, target = m3)
    m1.divide(m2)

    m3.copy_to_host()
    m1.copy_to_host()

    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.div exceeded threshold"
    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.div exceeded threshold"

def test_mult():
    m = 256
    n = 128
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.empty((m, n)), dtype=np.float32, order='F')

    c = a * b

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(t)

    m1.mult(m2, target = m3)
    m1.mult(m2)

    m3.copy_to_host()
    m1.copy_to_host()

    assert np.max(np.abs(c - m3.numpy_array)) < 10**-4, "Error in CUDAMatrix.multiply exceeded threshold"
    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.multiply exceeded threshold"

def test_scalar_mult():
    m = 256
    n = 128
    alpha = np.pi
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.empty((m, n)), dtype=np.float32, order='F')

    c = a * alpha

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(t)

    m1.mult(alpha, target = m2)
    m1.mult(alpha)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.mult exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.mult exceeded threshold"

def test_scalar_div():
    m = 256
    n = 128
    alpha = np.pi
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.empty((m, n)), dtype=np.float32, order='F')

    c = a / alpha

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(t)

    m1.divide(alpha, target = m2)
    m1.divide(alpha)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.divide exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.divide exceeded threshold"

def test_add_scalar():
    m = 256
    n = 128
    alpha = np.pi
    a = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')
    t = np.array(np.empty((m, n)), dtype=np.float32, order='F')

    c = a + alpha

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(t)

    m1.add(alpha, target = m2)
    m1.add(alpha)

    m1.copy_to_host()
    m2.copy_to_host()

    assert np.max(np.abs(c - m1.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_scalar exceeded threshold"
    assert np.max(np.abs(c - m2.numpy_array)) < 10**-4, "Error in CUDAMatrix.add_scalar exceeded threshold"

def test_dot():
    m = 128
    k = 256
    n = 64
    a = np.array(np.random.randn(m, k)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(k, n)*10, dtype=np.float32, order='F')

    c = np.dot(a, b)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.dot(m1, m2)
    m3.copy_to_host()

    assert np.max(np.abs(c - m3.numpy_array)) < 10**-2, "Error in CUDAMatrix.dot exceeded threshold"

def test_dot_trans():
    m = 128
    k = 256
    n = 64
    a = np.array(np.random.randn(k, m)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(k, n)*10, dtype=np.float32, order='F')

    c = np.dot(a.T, b)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m1.set_trans(True);
    m3 = cm.dot(m1, m2)
    m3.copy_to_host()

    assert np.max(np.abs(c - m3.numpy_array)) < 10**-2, "Error in CUDAMatrix.dot exceeded threshold"

def test_add_dot():
    m = 128
    k = 256
    n = 64
    a = np.array(np.random.randn(m, k)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(k, n)*10, dtype=np.float32, order='F')
    c = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')

    res = c + np.dot(a, b)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(c)
    m3.add_dot(m1, m2)

    m3.copy_to_host()

    assert np.max(np.abs(res - m3.numpy_array)) < 10**-2, "Error in CUDAMatrix.add_dot exceeded threshold"

def test_vdot():
    m = 64
    n = 64
    a = np.array(np.random.randn(m, n), dtype=np.float32, order='F')
    b = np.array(np.random.randn(m, n), dtype=np.float32, order='F')

    true_res = np.vdot(a, b)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)

    res = cm.vdot(m1, m2)

    assert np.abs(res - true_res) < 10**-2, "Error in CUDAMatrix.vdot exceeded threshold"

def test_subtract_dot():
    m = 128
    k = 256
    n = 64
    a = np.array(np.random.randn(m, k)*10, dtype=np.float32, order='F')
    b = np.array(np.random.randn(k, n)*10, dtype=np.float32, order='F')
    c = np.array(np.random.randn(m, n)*10, dtype=np.float32, order='F')

    res = c - np.dot(a, b)

    m1 = cm.CUDAMatrix(a)
    m2 = cm.CUDAMatrix(b)
    m3 = cm.CUDAMatrix(c)
    m3.subtract_dot(m1, m2)

    m3.copy_to_host()

    assert np.max(np.abs(res - m3.numpy_array)) < 10**-2, "Error in CUDAMatrix.subtract_dot exceeded threshold"

def test_random():
    cm.CUDAMatrix.init_random(1)
    m1 = cm.CUDAMatrix(np.array(np.empty((128,256)), dtype=np.float32, order='F'))
    m2 = cm.CUDAMatrix(np.array(np.empty((128,256)), dtype=np.float32, order='F'))

    m1.fill_with_rand()
    m1.copy_to_host()
    m2.fill_with_randn()
    m2.copy_to_host()

    assert np.abs(np.mean(m1.numpy_array) - 0.5) < 10**-2, "Error in CUDAMatrix.fill_with_rand threshold"
    assert np.abs(np.mean(m2.numpy_array)) < 10**-2, "Error in CUDAMatrix.fill_with_randn threshold"

def test_euclid_norm():
    m = 256
    n = 128
    a = np.array(np.random.rand(m, n)*10, dtype=np.float32, order='F')
    
    m = cm.CUDAMatrix(a)

    n1 = np.sqrt(np.sum(a**2))
    n2 = m.euclid_norm()

    assert np.abs(n1-n2) < 10**-2, "Error in CUDAMatrix.euclid_norm exceeded threshold"

def test_select_columns():
    m = 256
    n = 128
    k = 8

    s = np.array(np.random.randn(m, n), dtype=np.float32, order='F')
    i_l = [0, 1, 2, 3, 5, 10, 12, 20]
    i = np.array(i_l).T[np.newaxis, :]
    t = np.empty((m, k))
    
    s_d = cm.CUDAMatrix(s)
    i_d = cm.CUDAMatrix(i)
    t_d = cm.CUDAMatrix(t)

    s_d.select_columns(i_d, t_d)
    res = s[:,i_l]

    assert np.max(np.abs(res - t_d.asarray())) < 10**-4, "Error in CUDAMatrix.select_columns exceeded threshold"

if __name__ == '__main__':
    nose.run()

########NEW FILE########
__FILENAME__ = ais
"""Computes partition function for RBM-like models using Annealed Importance Sampling."""
import numpy as np
from deepnet import dbm
from deepnet import util
from deepnet import trainer as tr
from choose_matrix_library import *
import sys
import numpy as np
import pdb
import time
import itertools
import matplotlib.pyplot as plt
from deepnet import visualize
import lightspeed

def SampleEnergySoftmax(layer, numsamples, use_lightspeed=False):
  sample = layer.sample
  energy = layer.state
  temp = layer.expanded_batch
  if use_lightspeed:
    layer.ApplyActivation()
    layer.state.sum(axis=0, target=layer.temp)
    layer.state.div_by_row(layer.temp, target=temp)
    probs_cpu = temp.asarray().astype(np.float64)
    samples_cpu = lightspeed.SampleSoftmax(probs_cpu, numsamples)
    sample.overwrite(samples_cpu.astype(np.float32))
  else:
    sample.assign(0)
    for i in range(numsamples):
      energy.perturb_energy_for_softmax_sampling(target=temp)
      temp.choose_max_and_accumulate(sample)

def LogMeanExp(x):
  offset = x.max()
  return offset + np.log(np.exp(x-offset).mean())

def LogSumExp(x):
  offset = x.max()
  return offset + np.log(np.exp(x-offset).sum())

def Display(w, hid_state, input_state, w_var, x_axis):
  w = w.asarray().flatten()
  #plt.figure(1)
  #plt.clf()
  #plt.hist(w, 100)
  #visualize.display_hidden(hid_state.asarray(), 2, 'activations', prob=True)
  #plt.figure(3)
  #plt.clf()
  #plt.imshow(hid_state.asarray().T, cmap=plt.cm.gray, interpolation='nearest')
  #plt.figure(4)
  #plt.clf()
  #plt.imshow(input_state.asarray().T, cmap=plt.cm.gray, interpolation='nearest')
  #, state.shape[0], state.shape[1], state.shape[0], 3, title='Markov chains')
  #plt.tight_layout(pad=0, w_pad=0, h_pad=0)
  plt.figure(5)
  plt.clf()
  plt.suptitle('Variance')
  plt.plot(np.array(x_axis), np.array(w_var))
  plt.draw()

def AISReplicatedSoftmax(model, D, num_chains, display=False):
  schedule = np.concatenate((
    #np.arange(0.0, 1.0, 0.01),
    #np.arange(0.0, 1.0, 0.001),
    np.arange(0.0, 0.7, 0.001),  # 700
    np.arange(0.7, 0.9, 0.0001),  # 2000
    np.arange(0.9, 1.0, 0.00002)  # 5000
    ))
  #schedule = np.array([0.])
  cm.CUDAMatrix.init_random(seed=0)

  assert len(model.layer) == 2, 'Only implemented for RBMs.'
  steps = len(schedule)
  input_layer = model.layer[0]
  hidden_layer = model.layer[1]
  edge = model.edge[0]
  batchsize = num_chains
  w = edge.params['weight']
  a = hidden_layer.params['bias']
  b = input_layer.params['bias']
  numvis, numhid = w.shape
  f = 0.1
  input_layer.AllocateBatchsizeDependentMemory(num_chains)
  hidden_layer.AllocateBatchsizeDependentMemory(num_chains)

  # INITIALIZE TO SAMPLES FROM BASE MODEL.
  input_layer.state.assign(0)
  input_layer.NN.assign(D)
  input_layer.state.add_col_mult(b, f)
  SampleEnergySoftmax(input_layer, D)
  w_ais = cm.CUDAMatrix(np.zeros((1, batchsize)))
  #pdb.set_trace()

  w_variance = []
  x_axis = []
  if display:
    Display(w_ais, hidden_layer.state, input_layer.state, w_variance, x_axis)
    #raw_input('Press Enter.')
  #pdb.set_trace()

  # RUN AIS.
  for i in range(steps-1):
    sys.stdout.write('\r%d' % (i+1))
    sys.stdout.flush()
    cm.dot(w.T, input_layer.sample, target=hidden_layer.state)
    hidden_layer.state.add_col_mult(a, D)

    hidden_layer.state.mult(schedule[i], target=hidden_layer.temp)
    hidden_layer.state.mult(schedule[i+1])
    cm.log_1_plus_exp(hidden_layer.state, target=hidden_layer.deriv)
    cm.log_1_plus_exp(hidden_layer.temp)
    hidden_layer.deriv.subtract(hidden_layer.temp)
    w_ais.add_sums(hidden_layer.deriv, axis=0)
    w_ais.add_dot(b.T, input_layer.sample, mult=(1-f)*(schedule[i+1]-schedule[i]))

    hidden_layer.ApplyActivation()
    hidden_layer.Sample()
    cm.dot(w, hidden_layer.sample, target=input_layer.state)
    input_layer.state.add_col_vec(b)
    input_layer.state.mult(schedule[i+1])
    input_layer.state.add_col_mult(b, f*(1-schedule[i+1]))
    SampleEnergySoftmax(input_layer, D)
    if display and (i % 100 == 0 or i == steps - 2):
      w_variance.append(w_ais.asarray().var())
      x_axis.append(i)
      Display(w_ais, hidden_layer.state, input_layer.sample, w_variance, x_axis)
  sys.stdout.write('\n')
  z = LogMeanExp(w_ais.asarray()) + D * LogSumExp(f * b.asarray()) + numhid * np.log(2)
  return z

def AISBinaryRbm(model, schedule):
  cm.CUDAMatrix.init_random(seed=int(time.time()))
  assert len(model.layer) == 2, 'Only implemented for RBMs.'
  steps = len(schedule)
  input_layer = model.layer[0]
  hidden_layer = model.layer[1]
  edge = model.edge[0]
  batchsize = model.t_op.batchsize
  w = edge.params['weight']
  a = hidden_layer.params['bias']
  b = input_layer.params['bias']
  numvis, numhid = w.shape

  # INITIALIZE TO UNIFORM RANDOM.
  input_layer.state.assign(0)
  input_layer.ApplyActivation()
  input_layer.Sample()
  w_ais = cm.CUDAMatrix(np.zeros((1, batchsize)))
  unitcell = cm.empty((1, 1))
  # RUN AIS.
  for i in range(1, steps):
    cm.dot(w.T, input_layer.sample, target=hidden_layer.state)
    hidden_layer.state.add_col_vec(a)

    hidden_layer.state.mult(schedule[i-1], target=hidden_layer.temp)
    hidden_layer.state.mult(schedule[i])
    cm.log_1_plus_exp(hidden_layer.state, target=hidden_layer.deriv)
    cm.log_1_plus_exp(hidden_layer.temp)
    hidden_layer.deriv.subtract(hidden_layer.temp)
    w_ais.add_sums(hidden_layer.deriv, axis=0)
    w_ais.add_dot(b.T, input_layer.state, mult=schedule[i]-schedule[i-1])

    hidden_layer.ApplyActivation()
    hidden_layer.Sample()
    cm.dot(w, hidden_layer.sample, target=input_layer.state)
    input_layer.state.add_col_vec(b)
    input_layer.state.mult(schedule[i])
    input_layer.ApplyActivation()
    input_layer.Sample()
  z = LogMeanExp(w_ais.asarray()) + numvis * np.log(2) + numhid * np.log(2)
  return z

def GetAll(n):
  x = np.zeros((n, 2**n))
  a = []
  for i in range(n):
    a.append([0, 1])
  for i, r in enumerate(itertools.product(*tuple(a))):
    x[:, i] = np.array(r)
  return x

def ExactZ_binary_binary(model):
  assert len(model.layer) == 2, 'Only implemented for RBMs.'
  steps = len(schedule)
  input_layer = model.layer[0]
  hidden_layer = model.layer[1]
  edge = model.edge[0]
  w = edge.params['weight']
  a = hidden_layer.params['bias']
  b = input_layer.params['bias']
  numvis, numhid = w.shape
  batchsize = 2**numvis
  input_layer.AllocateBatchsizeDependentMemory(batchsize)
  hidden_layer.AllocateBatchsizeDependentMemory(batchsize)
  all_inputs = GetAll(numvis)
  w_ais = cm.CUDAMatrix(np.zeros((1, batchsize)))
  input_layer.sample.overwrite(all_inputs)
  cm.dot(w.T, input_layer.sample, target=hidden_layer.state)
  hidden_layer.state.add_col_vec(a)
  cm.log_1_plus_exp(hidden_layer.state)
  w_ais.add_sums(hidden_layer.state, axis=0)
  w_ais.add_dot(b.T, input_layer.state)
  offset = float(w_ais.asarray().max())
  w_ais.subtract(offset)
  cm.exp(w_ais)
  z = offset + np.log(w_ais.asarray().sum())
  return z

def Usage():
  print '%s <model file> <number of Markov chains to run> [number of words (for Replicated Softmax models)]'

if __name__ == '__main__':
  board = tr.LockGPU()
  model_file = sys.argv[1]
  numchains = int(sys.argv[2])
  if len(sys.argv) > 3:
    D = int(sys.argv[3]) #10 # number of words.
  m = dbm.DBM(model_file)
  m.LoadModelOnGPU(batchsize=numchains)
  plt.ion()
  log_z = AISReplicatedSoftmax(m, D, numchains, display=True)
  print 'Log Z %.5f' % log_z
  #log_z = AIS(m, schedule)
  #print 'Log Z %.5f' % log_z
  #log_z = ExactZ_binary_binary(m)
  #print 'Exact %.5f' % log_z
  tr.FreeGPU(board)
  raw_input('Press Enter.')

########NEW FILE########
__FILENAME__ = choose_matrix_library
import os
use_gpu = os.environ.get('USE_GPU', 'auto')
assert use_gpu in ['auto', 'yes', 'no'], "environment variable USE_GPU, should be one of 'auto', 'yes', 'no'."
if use_gpu == 'auto':
  try:
    import cudamat as cm
    use_gpu = 'yes'
  except:
    print 'Failed to import cudamat. Using eigenmat. No GPU will be used.'
    use_gpu = 'no'
if use_gpu == 'yes':
  import cudamat as cm
  from cudamat import cudamat_conv as cc
  from cudamat import gpu_lock
elif use_gpu == 'no':
  import eigenmat as cm

########NEW FILE########
__FILENAME__ = compute_data_stats
"""Utility for computing data stats."""
# python compute_data_stats.py mnist.pbtxt mnist_stats.npz train_full_data
import sys
from datahandler import *
from google.protobuf import text_format

class DataViewer(object):
  def __init__(self, proto_file):
    assert os.path.exists(proto_file)
    self.data_proto = util.ReadData(proto_file)

  def Load(self, name, batchsize=None, typesize=4):
    data_proto = self.data_proto
    try:
      this_set = next(d for d in data_proto.data if d.name == name)
    except StopIteration as e:
      print 'No data called %s found in proto file.' % name
      raise e

    filenames = sorted(glob.glob(os.path.join(data_proto.prefix,
                                              this_set.file_pattern)))
    numdims = np.prod(np.array(this_set.dimensions))
    numlabels = this_set.num_labels
    key = this_set.key
    self.numdims = numdims * numlabels
    datasetsize = this_set.size
    if batchsize is None:
      batchsize = datasetsize
    self.batchsize = batchsize
    total_disk_space = datasetsize * numdims * typesize
    self.numbatches = datasetsize / batchsize
    max_cpu_capacity = min(total_disk_space, GetBytes(data_proto.main_memory))
    self.num_cpu_batches = max_cpu_capacity / (typesize * numdims * batchsize)
    cpu_capacity = self.num_cpu_batches * batchsize * numdims * typesize

    self.disk = Disk([filenames], [numdims], datasetsize, keys=[key])
    self.cpu_cache = Cache(self.disk, cpu_capacity, [numdims],
                           typesize = typesize, randomize=False)

  def Get(self):
    datachunk = self.cpu_cache.Get(self.batchsize)[0]
    try:
      if 'sparse' in datachunk.__module__:
        datachunk = datachunk.toarray()
    except Exception as e:
      pass
    return datachunk

  def ComputeStats(self):
    numdims = self.numdims
    numbatches = self.numbatches
    means = np.zeros((numbatches, numdims))
    variances = np.zeros((numbatches, numdims))
    for i in range(numbatches):
      sys.stdout.write('\r%d of %d' % ((i + 1), numbatches))
      sys.stdout.flush()
      batch = self.Get()
      means[i] = batch.mean(axis=0)
      variances[i] = batch.var(axis=0)
    sys.stdout.write('\n')
    mean = means.mean(axis=0)
    std = np.sqrt(variances.mean(axis=0) + means.var(axis=0))
    mean_std = std.mean()
    std += (std == 0.0) * mean_std
    return {'mean': mean, 'std': std}

def Usage():
  print 'python %s <data_pbtxt> <output_stats_file> <data_field_whose_stats_need_to_be_computed> ' % sys.argv[0]

if __name__ == '__main__':
  if len(sys.argv) < 4:
    Usage()
    sys.exit()
  data_proto_file = sys.argv[1]
  outputfilename = sys.argv[2]
  data_name = sys.argv[3]
  batchsize = 100
  if len(sys.argv) > 4:
    if sys.argv[4] == 'all':
      batchsize = None
    else:
      batchsize = int(sys.argv[4])
  dv = DataViewer(data_proto_file)
  dv.Load(data_name, batchsize=batchsize)
  stats = dv.ComputeStats()
  np.savez(outputfilename, **stats)

########NEW FILE########
__FILENAME__ = convolutions
"""Convolutional operations."""
from choose_matrix_library import *
import math

def ConvolveUp(inputs, edge, target):
  w = edge.params['weight']
  conv = edge.conv_params
  size = conv.size
  stride = conv.stride
  padding = conv.padding
  num_filters = conv.num_filters
  num_colors = conv.num_colors

  f, numdims = w.shape
  assert f == num_filters, 'f is %d but num_filters is %d' % (f, num_filters)
  if edge.conv:
    assert numdims == size**2 * num_colors

  input_t = edge.input_t
  inputs.transpose(input_t)
  # Convolve Up.
  if conv.max_pool:
    output_t = edge.unpooled_layer
  elif conv.rnorm:
    output_t = edge.unrnormalized_layer
  else:
    output_t = edge.output_t

  numimages, numdims = input_t.shape
  numimages2, numdims2 = output_t.shape
  assert numimages == numimages2, '%d %d.' % (numimages, numimages2)
  assert numdims % num_colors == 0
  x = int(math.sqrt(numdims / num_colors))
  assert x**2 == numdims/num_colors
  n_locs = (x + 2 * padding - size) / stride + 1
  if edge.conv:
    cc.convUp(input_t, w, output_t, n_locs, padding, stride, num_colors)
  else:
    cc.localUp(input_t, w, output_t, n_locs, padding, stride, num_colors)

  # Do maxpooling
  if conv.max_pool:
    input_t = output_t
    if conv.rnorm:
      output_t = edge.unrnormalized_layer
    else:
      output_t = edge.output_t
    n_locs = (n_locs - conv.pool_size) / conv.pool_stride + 1
    if conv.prob:
      rnd = edge.rnd
      rnd.fill_with_rand()
      cm.log(rnd)
      rnd.mult(-1)
      #cm.log(rnd)
      #rnd.mult(-1)
      cc.ProbMaxPool(input_t, rnd, output_t, num_filters, conv.pool_size, 0, conv.pool_stride, n_locs)
    else:
      cc.MaxPool(input_t, output_t, num_filters, conv.pool_size, 0, conv.pool_stride, n_locs)
  if conv.rnorm:
    input_t = output_t
    output_t = edge.output_t
    denoms = edge.denoms
    sizeX = conv.norm_size
    add_scale = conv.add_scale
    pow_scale = conv.pow_scale
    cc.ResponseNorm(input_t, denoms, output_t, num_filters, sizeX, add_scale, pow_scale)
  output_t.transpose(target)

def AccumulateConvDeriv(layer, edge, deriv):
  """Accumulate the derivative w.r.t the outputs of this layer.

  Each layer needs to compute derivatives w.r.t its outputs. These outputs may
  have been connected to lots of other nodes through outgoing edges.
  This method adds up the derivatives contributed by each outgoing edge.
  It gets derivatives w.r.t the inputs at the other end of an outgoing edge.
  Args:
    edge: The edge which is sending the derivative.
    deriv: The derivative w.r.t the inputs at the other end of this edge.
  """

  if layer.dirty:  # If some derivatives have already been received.
    raise Exception('Not implemented.')
  layer.dirty = True
  w = edge.params['weight']
  conv = edge.conv_params
  size = conv.size
  stride = conv.stride
  padding = conv.padding
  num_filters = conv.num_filters
  num_colors = conv.num_colors

  input_t = edge.input_t
  numImages, numdims = input_t.shape

  assert numdims % num_colors == 0
  x = int(math.sqrt(numdims / num_colors))
  assert x**2 == numdims/num_colors

  n_locs = (x + 2 * padding - size) / stride + 1

  # Incoming gradient.
  deriv.transpose(edge.output_t2)
  input_grads = edge.output_t2

  # Output activation (after conv + pool? + norm?)
  output_acts = edge.output_t

  if conv.rnorm:

    # ResponseNormUndo overwrites input_acts, so make a copy.
    input_acts = edge.rnorm_temp1
    input_acts.assign(edge.unrnormalized_layer)

    output_grads = edge.rnorm_temp2
    denoms = edge.denoms

    sizeX = conv.norm_size
    pow_scale = conv.pow_scale
    add_scale = conv.add_scale
    cc.ResponseNormUndo(input_grads, denoms, output_acts, input_acts,
                        output_grads, num_filters, sizeX, add_scale,
                        pow_scale)
    input_grads = output_grads
    output_acts = edge.unrnormalized_layer

  if conv.max_pool:
    input_acts = edge.unpooled_layer
    output_grads = edge.unpooled_layer
    # It's OK to overwrite input_acts because we don't need it later.

    n_pool_locs = (n_locs - conv.pool_size) / conv.pool_stride + 1
    sizeX = conv.pool_size
    strideX = conv.pool_stride
    cc.MaxPoolUndo(output_grads, input_acts, input_grads, output_acts, sizeX,
                   0, strideX, n_pool_locs)
    input_grads = output_grads
    output_acts = input_acts
  if layer.is_input:
    return

  output_grads = edge.input_t2
  if edge.conv:
    cc.convDown(input_grads, w, output_grads, n_locs, padding, stride, size, x, num_colors)
  else:
    cc.localDown(input_grads, w, output_grads, n_locs, padding, stride, size, x, num_colors)
  output_grads.transpose(layer.deriv)

def ConvOuter(edge, grad):
  """Get the gradient for the weights in this edge.
  Args:
    grad: (output) the gradient for the weights in this edge.
  """
  w = edge.params['weight']
  conv = edge.conv_params
  size = conv.size
  stride = conv.stride
  padding = conv.padding
  num_filters = conv.num_filters
  num_colors = conv.num_colors

  f, numdims = w.shape
  assert f == num_filters, 'f is %d but num_filters is %d' % (f, num_filters)
  if edge.conv:
    assert numdims == size**2 * num_colors
  input_t = edge.input_t
  if conv.max_pool:
    output_t = edge.unpooled_layer
  elif conv.rnorm:
    output_t = edge.rnorm_temp2
  else:
    output_t = edge.output_t2
  numdims, numimages = edge.node1.state.shape

  assert numdims % num_colors == 0
  x = int(math.sqrt(numdims / num_colors))

  assert x**2 == numdims/num_colors

  n_locs = (x + 2 * padding - size) / stride + 1

  if edge.conv:
    cc.convOutp(input_t, output_t, grad, n_locs, padding, size, stride, num_colors)
  else:
    cc.localOutp(input_t, output_t, grad, n_locs, padding, size, stride, num_colors)

def AddConvolveUp(inputs, edge, target):
  raise Exception('Not implemented.')


########NEW FILE########
__FILENAME__ = cos_layer
from layer import *

class CosLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(CosLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.COS

  def ApplyActivation(self):
    self.backup_state.assign(self.state)
    cm.cos(self.state)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    self.deriv.apply_cos_deriv(self.backup_state)

  def AllocateBatchsizeDependentMemory(self, batchsize):
    super(CosLayer, self).AllocateBatchsizeDependentMemory(batchsize)
    self.backup_state = cm.CUDAMatrix(np.zeros(self.statesize.shape))

########NEW FILE########
__FILENAME__ = datahandler
from deepnet import util
from deepnet import deepnet_pb2
import cPickle as pickle
from choose_matrix_library import *
import glob
import numpy as np
import os.path
import scipy.sparse as sp
import pdb
import gzip
import random

class Disk(object):
  """A Disk access manager."""
  def __init__(self, filenames, numdim_list, total_size, keys=[], verbose=False,
              **kwargs):
    """Initializes a Disk object.

    Args:
      filenames: List of list of filenames.
      numdim_list: List of integers that represent the dimensionality of the
        data.
      total_size: Number of data points in the dataset (sum over all files).
      verbose: If True, will print out details of what is happening.
    """
    assert len(filenames) == len(numdim_list)
    self.num_data = len(filenames)
    self.numdim_list = numdim_list
    self.filenames = filenames
    self._num_file_list = [len(filename_list) for filename_list in filenames]
    self._maxpos = total_size
    self.verbose = verbose
    self.left_overs = [None]*self.num_data
    self.last_read_chunk = [None]*self.num_data
    self.last_read_file = [-1]*self.num_data
    self.data = [None]*self.num_data
    if keys:
      self.keys = keys
    else:
      self.keys = [None]*self.num_data


  def AddSparseData(self, data, chunk):
    """Appends chunk to data."""
    if data is None:
      return chunk
    else:
      return sp.vstack((data, chunk)).tocsr()

  def Get(self, batchsize):
    """Reads data from disk.
    Args:
      batchsize: Number of data points to read.
    Returns:
      A list of numpy arrays each with batchsize rows. Each element of the list
      is one data modality.
    """
    data_list = []
    for i in range(self.num_data):
      key = self.keys[i]
      numdims = self.numdim_list[i]
      filename_list = self.filenames[i]
      num_files = self._num_file_list[i]
      current_file = (self.last_read_file[i] + 1) % num_files
      sparse = os.path.splitext(filename_list[current_file])[1] == '.npz'

      # Allocate memory for storing data that will come from the disk.
      if sparse:
        # Sparse matrices do not allow slice assignment, so we will stack them
        # as they come.
        data = None
      else:
        if self.data[i] is None:
          self.data[i] = np.zeros((batchsize, numdims), dtype='float32')
        data = self.data[i]
      datasize = 0  # Number of rows of data filled up.

      # First put any left overs from previous disk accesses.
      if self.left_overs[i] is not None:
        left_over_size = self.left_overs[i].shape[0]
        if left_over_size > batchsize:
          if sparse:
            data = self.left_overs[i][:batchsize]
          else:
            data[:batchsize] = self.left_overs[i][:batchsize]
          self.left_overs[i] = self.left_overs[i][batchsize:]
          datasize = batchsize
        else:
          if sparse:
            data = self.left_overs[i]
          else:
            data[:left_over_size] = self.left_overs[i]
          self.left_overs[i] = None
          datasize = left_over_size

      # Read data from disk.
      while(datasize < batchsize):
        if self.last_read_file[i] != current_file:
          this_chunk = self.ReadDiskData(filename_list[current_file], key)
          self.last_read_chunk[i] = this_chunk
          self.last_read_file[i] = current_file
        else:
          this_chunk = self.last_read_chunk[i]
        this_chunk_size = this_chunk.shape[0]

        if datasize + this_chunk_size > batchsize:
          # Put part of this_chunk into the data and remaining in left_overs.
          self.left_overs[i] = this_chunk[batchsize - datasize:]
          if sparse:
            data = self.AddSparseData(data, this_chunk[:batchsize - datasize])
          else:
            data[datasize : batchsize] = this_chunk[:batchsize - datasize]
          datasize = batchsize
        else:
          # Put whole of this_chunk into the data.
          self.left_overs[i] = None
          if sparse:
            data = self.AddSparseData(data, this_chunk)
          else:
            data[datasize : datasize + this_chunk_size] = this_chunk
          datasize += this_chunk_size
        current_file = (current_file + 1) % num_files
      data_list.append(data)
    return data_list

  @staticmethod
  def LoadPickle(inputfile, key=None, verbose=False):
    """Loads a pickle."""
    fo = gzip.GzipFile(inputfile, 'rb')
    spec = pickle.load(fo)
    if key:
      spec = spec[key].T
    fo.close()
    return spec

  @staticmethod
  def LoadSparse(inputfile, verbose=False):
    """Loads a sparse matrix stored as npz file."""
    npzfile = np.load(inputfile)
    mat = sp.csr_matrix((npzfile['data'], npzfile['indices'],
                                  npzfile['indptr']),
                                  shape=tuple(list(npzfile['shape'])))
    if verbose:
      print 'Loaded sparse matrix from %s of shape %s' % (inputfile,
                                                          mat.shape.__str__())
    return mat

  @staticmethod
  def SaveSparse(outputfile, mat, verbose=False):
    if verbose:
      print 'Saving to %s shape %s' % (outputfile, mat.shape.__str__())
    np.savez(outputfile, data=mat.data, indices=mat.indices, indptr=mat.indptr,
             shape=np.array(list(mat.shape)))



  def ReadDiskData(self, filename, key=''):
    """Reads data from filename."""
    if self.verbose:
      print 'Reading from disk %s' % filename
    ext = os.path.splitext(filename)[1]
    if ext == '.npy':
      data = np.load(filename)
    elif ext == '.mat':
      data = scipy.io.loadmat(filename, struct_as_record = True)[key]
    elif ext == '.p':
      data = pickle.load(gzip.GzipFile(filename, 'rb'))
    elif ext == '.txt':
      data = np.loadtext(filename)
    elif ext == '.npz':
      data = Disk.LoadSparse(filename, verbose=self.verbose)
    elif ext == '.spec':
      data = Disk.LoadPickle(filename, key, verbose=self.verbose)
    else:
      raise Exception('Unknown file extension %s' % ext)
    if data.dtype == 'float64':
      data = data.astype('float32')

    # 1-D data as column vector.
    if len(data.shape) == 1 or (len(data.shape)==2 and data.shape[0] == 1):
      data = data.reshape(-1, 1)

    return data


class Cache(object):
  def __init__(self, parent, capacity, numdim_list, typesize=4, randomize=False,
              verbose=False, **kwargs):
    """Initialize a Cache.
    Args:
      parent: object that will provide data to this cache. Must have a Get().
      capacity: Maximum number of bytes that can fit in the cache.
      numdim_list: List of dimensions of the data.
      typesize: size (in bytes) of an atomic data entry.
      randomize: If True, shuffle the vectors after receiving them from the
        parent.
      verbose: If True, print info about what is happening.
    """
    self.parent = parent
    self.num_data = len(numdim_list)
    self.numdims = sum(numdim_list)
    self.numdim_list = numdim_list
    self._maxpos = capacity / (self.numdims * typesize)
    self.verbose = verbose
    self.capacity = self._maxpos * self.numdims * typesize
    self.typesize = typesize
    self._pos = 0
    self.data = []
    self.datasize = 0
    self.randomize = randomize
    if self.verbose:
      print 'Capacity %d bytes for data of size %d X %d rand=%s' % (
        self.capacity, self._maxpos, self.numdims, randomize)

  def LoadData(self):
    """Load data from the parent."""

    # If cache has no data or it holds less data than parent, then it is
    # time to ask for more data.
    if self.data == [] or self._maxpos < self.parent._maxpos:
      self.data = self.parent.Get(self._maxpos)
      self.datasize = self.data[0].shape[0]

    if self.randomize:
      # Shuffle the data. Need to make sure same shuffle is applied to all data
      # pieces in the list.
      rng_state = np.random.get_state()
      for i, d in enumerate(self.data):
        if sp.issparse(d):  # Not easy to do in-place shuffling for sparse data.
          indices = np.arange(d.shape[0])
          np.random.set_state(rng_state)
          np.random.shuffle(indices)
          self.data[i] = d[indices]
        else:
          np.random.set_state(rng_state)
          np.random.shuffle(d)

  def Get(self, batchsize):
    """Get data points from the cache.
    Args:
      batchsize: Number of data points requested. Will return fewer than
        batchsize iff the cache does not have enough data.
    Returns:
      Numpy array slice of shape batchsize X numdims.
    """
    if self._pos == self.datasize:
      self._pos = 0
    if self._pos == 0:
      self.LoadData()
    start = self._pos
    end = self._pos + batchsize
    if end > self.datasize:
      end = self.datasize
    self._pos = end
    batch = [d[start:end] for d in self.data]
    return batch


class GPUCache(Cache):
  """GPU memory manager."""
  def __init__(self, *args, **kwargs):
    super(GPUCache, self).__init__(*args, **kwargs)
    
    self.data = [None] * self.num_data
    self.empty = True
    self.allocated_memory_size = [0] * self.num_data
    
    # Elementary preprocessing can be done on the GPU.
    self.normalize = [False] * self.num_data
    self.means = [None] * self.num_data
    self.stds = [None] * self.num_data

    # Add gaussian noise.
    self.add_noise = kwargs.get('add_noise', [False]*self.num_data)
    sigma = 0.01

    # Add random translations (useful for vision data).
    self.translate = kwargs.get('shift', [False]*self.num_data)
    shift_amt_x = kwargs.get('shift_amt_x', [0])[0]
    shift_amt_y = kwargs.get('shift_amt_y', [0])[0]
    center_only = kwargs.get('center_only', False)
    shift_amt = max(shift_amt_x, shift_amt_y)
    self.sizeX = 32  # Should pass this as arguments!
    self.sizex = 32 - 2 * shift_amt
    self.num_channels = 3
    if center_only:  # True for test data.
      self.translate_range_x = [0]
      self.translate_range_y = [0]
      self.sigma = 0
    else:
      self.translate_range_x = range(-shift_amt_x, shift_amt_x + 1)
      self.translate_range_y = range(-shift_amt_y, shift_amt_y + 1)
      self.sigma = sigma

    self.translated_d = None
    self.offset_x = None
    self.offset_y = None

  def Normalize(self):
    """Normalize the data present in self.data"""
    for i, batch in enumerate(self.data):
      if self.normalize[i]:
        mean = self.means[i]
        std = self.stds[i]
        batch.add_col_mult(mean, mult=-1.0)
        batch.div_by_col(std)

  def LoadData(self):
    """Load data from parent cache."""

    # Ask parent for data.
    data_cpu = self.parent.Get(self._maxpos)
    datasize = data_cpu[0].shape[0]
    assert datasize <= self._maxpos,\
      "GPU cache can only store %d datapoints, but parent gave it %d." % (
        self._maxpos, datasize)

    self.datasize = datasize
    for i, d in enumerate(data_cpu):
      if sp.issparse(d):
        mat = d.toarray().T
      else:
        mat = d.T
      size = mat.shape[0] * mat.shape[1]
      if size > self.allocated_memory_size[i]:
        # If need more space, then allocate new matrix on the GPU.
        self.data[i] = cm.CUDAMatrix(mat)
        self.allocated_memory_size[i] = mat.shape[0] * mat.shape[1]
      else:
        # Overwrite old memory. It is ok if size of mat is less than the total
        # space that has been allocated.
        self.data[i].overwrite(mat)
    self.Normalize()

  def AddNoise(self, batch, i):
    # Add gaussian noise to data at index i in batch.
    batch[i].sample_gaussian(mult=self.sigma)

  def TranslateData(self, batch, i):
    """Applies translations to data at index i in batch."""
    sizeX = self.sizeX
    sizex = self.sizex
    batchsize = batch[i].shape[1]
    shift = (sizeX - sizex)/2
    offset_x = np.array([random.choice(self.translate_range_x) + shift for k in range(batchsize)]).reshape(1, -1)
    offset_y = np.array([random.choice(self.translate_range_y) + shift for k in range(batchsize)]).reshape(1, -1)
    num_channels = self.num_channels

    d = batch[i]

    if self.offset_x is None:
      self.offset_x = cm.CUDAMatrix(offset_x)
    else:
      self.offset_x.overwrite(offset_x)
    if self.offset_y is None:
      self.offset_y = cm.CUDAMatrix(offset_y)
    else:
      self.offset_y.overwrite(offset_y)
    if self.translated_d is None or self.translated_d.shape[1] != batchsize:
      self.translated_d = cm.empty((sizex**2 * num_channels, batchsize))
    d.generate_translations(sizeX, sizex, self.offset_x, self.offset_y, target=self.translated_d)
    batch[i] = self.translated_d

  def ShuffleData(self):
    """In-place shuffle the data in self.data."""
    indices = np.arange(self.datasize)
    np.random.shuffle(indices)
    indices1 = indices[:self.datasize/2]
    indices2 = indices[self.datasize/2:2*(self.datasize/2)]
    indices1_gpu = cm.CUDAMatrix(indices1.reshape(1, -1))
    indices2_gpu = cm.CUDAMatrix(indices2.reshape(1, -1))
    for d in self.data:
      d.swap_columns(indices1_gpu, indices2_gpu, target=d)
    indices1_gpu.free_device_memory()
    indices2_gpu.free_device_memory()

  def SetDataStats(self, i, stats_file):
    """Load stats for normalizing the data."""
    assert os.path.exists(stats_file), 'Stats file %s not found.' % stats_file
    stats = np.load(stats_file)
    self.normalize[i] = True
    self.means[i] = cm.CUDAMatrix(stats['mean'].reshape(-1, 1))
    self.stds[i] = cm.CUDAMatrix(1e-10 + stats['std'].reshape(-1, 1))

  def Get(self, batchsize, get_last_piece=False):
    """Return 'batchsize' data points from the cache.
    
    May return fewer points towards the end of the dataset when there are fewer
    than batchsize left.
    """
    skip = False
    if self._pos == self.datasize:
      self._pos = 0
    if self._pos == 0:
      if self.empty or self._maxpos < self.parent._maxpos:
        self.LoadData()
        self.empty = False
      if self.randomize and self._maxpos == self.parent._maxpos:
        # Shuffle if randomize is True and parent has not already shuffled it.
        self.ShuffleData()
    start = self._pos
    end = self._pos + batchsize
    if end > self.datasize:
      end = self.datasize
      skip = not get_last_piece
    self._pos = end
    if skip:
      return self.Get(batchsize, get_last_piece=get_last_piece)
    else:
      batch = [d.slice(start, end) for d in self.data]
      for i in range(self.num_data):
        if self.add_noise[i]:
          self.AddNoise(batch, i)
        if self.translate[i]:
          self.TranslateData(batch, i)
      return batch

def GetBytes(mem_str):
  """Converts human-readable numbers to bytes.

  E.g., converts '2.1M' to 2.1 * 1024 * 1024 bytes.
  """
  unit = mem_str[-1]
  val = float(mem_str[:-1])
  if unit == 'G':
    val *= 1024*1024*1024
  elif unit == 'M':
    val *= 1024*1024
  elif unit == 'K':
    val *= 1024
  else:
    try:
      val = int(mem_str)
    except Exception:
      print '%s is not a valid way of writing memory size.' % mem_str
  return int(val)

def GetDataHandles(op, names, hyp_list, verbose=False):
  """Returns a list of data handles.

  This method is the top-level routine for creating data handlers. It takes a
  description of which datasets to load and returns data handlers to access
  them.
  Args:
    op: Operation protocol buffer.
    names: list of list of data names. The top level list corresponds to train,
      validation and test sets. The lower-level lists correspond to data
      modalities.
    hyp_list: List of hyperparameters for each modality.
    verbose: If True, will print out details of what is happening.
  Returns:
    A list of DataHandler objects.
  """
  typesize = 4
  data_proto_file = os.path.join(op.data_proto_prefix, op.data_proto)
  dataset_proto = util.ReadData(data_proto_file)
  handlers = []
  if dataset_proto.data_handler == 'deepnet':
    size_list = []
    for name_list in names:
      size = 0
      for name in name_list:
        try:
          data_proto = next(d for d in dataset_proto.data if d.name == name)
        except StopIteration as e:
          print '%s not found in data pbtxt' % name
          raise e
        datasetsize = data_proto.size
        numdims = np.prod(np.array(data_proto.dimensions))
        size += datasetsize * numdims * typesize
      size_list.append(size)
    total_size = sum(size_list)
    proportions = [float(size)/total_size for size in size_list]
    for i, name_list in enumerate(names):
      if name_list == []:
        handlers.append(None)
      else:
        handlers.append(DataHandler(op, name_list, hyp_list, frac=proportions[i]))
  elif dataset_proto.data_handler == 'navdeep':
    import navdeep_datahandler
    for i, name_list in enumerate(names):
      if name_list == []:
        handlers.append(None)
      else:
        handlers.append(navdeep_datahandler.NavdeepDataHandler(
          op, dataset_proto, name_list, hyp_list))

  return handlers

class DataHandler(object):
  """Data handling class."""
  def __init__(self, op, data_name_list, hyperparameter_list, frac=1.0):
    """Initializes a DataHandler.
    Args:
      op: Operation protocol buffer.
      data_name_list: List of data names that should be put together. (Usually
        refers to a list of different modalities, e.g., ['data', 'label'] or
        ['image', 'audio'].)
      hyperparameter_list: List of hyperparameters, one for each modality.
      frac: What fraction of the total memory should this data handler use.
    """
    filenames = []
    numdim_list = []
    datasetsize = None
    left_window = []
    right_window = []
    stats_files = []
    shift = []
    add_noise = []
    shift_amt_x = []
    shift_amt_y = []
    keys = []
    typesize = 4
    if isinstance(op, str):
      op = util.ReadOperation(op)
    self.verbose = op.verbose
    verbose = self.verbose
    data_proto_file = os.path.join(op.data_proto_prefix, op.data_proto)
    dataset_proto = util.ReadData(data_proto_file)
    seq = False
    is_train = False
    for name, hyp in zip(data_name_list, hyperparameter_list):
      data_proto = next(d for d in dataset_proto.data if d.name == name)
      file_pattern = os.path.join(dataset_proto.prefix, data_proto.file_pattern)
      filenames.append(sorted(glob.glob(file_pattern)))
      stats_files.append(os.path.join(dataset_proto.prefix, data_proto.stats_file))
      numdims = np.prod(np.array(data_proto.dimensions))
      if not data_proto.sparse:
        numdims *= data_proto.num_labels
      numdim_list.append(numdims)
      seq = seq or data_proto.seq
      left_window.append(hyp.left_window)
      right_window.append(hyp.right_window)
      add_noise.append(hyp.add_noise)
      shift.append(hyp.shift)
      shift_amt_x.append(hyp.shift_amt_x)
      shift_amt_y.append(hyp.shift_amt_y)
      keys.append(data_proto.key)
      is_train = 'train' in name  # HACK - Fix this!
      if datasetsize is None:
        datasetsize = data_proto.size
      else:
        assert datasetsize == data_proto.size, 'Size of %s is not %d' % (
          name, datasetsize)

    # Add space for padding.
    if seq:
      max_rw = max(right_window)
      max_lw = max(left_window)
      actual_datasetsize = datasetsize
      datasetsize += len(filenames[0]) * (max_rw + max_lw)

    numdims = sum(numdim_list)
    batchsize = op.batchsize
    randomize = op.randomize
    self.get_last_piece = op.get_last_piece
    # Compute size of each cache.
    total_disk_space = datasetsize * numdims * typesize
    max_gpu_capacity = int(frac*GetBytes(dataset_proto.gpu_memory))
    max_cpu_capacity = int(frac*GetBytes(dataset_proto.main_memory))

    # Each capacity should correspond to integral number of batches.
    vectorsize_bytes = typesize * numdims
    batchsize_bytes = vectorsize_bytes * batchsize
    max_gpu_capacity = (max_gpu_capacity / batchsize_bytes) * batchsize_bytes
    #max_cpu_capacity = (max_cpu_capacity / batchsize_bytes) * batchsize_bytes

    # Don't need more than total dataset size.
    gpu_capacity = min(total_disk_space, max_gpu_capacity) 
    cpu_capacity = min(total_disk_space, max_cpu_capacity) 
    num_gpu_batches = gpu_capacity / batchsize_bytes
    num_cpu_batches = cpu_capacity / batchsize_bytes

    gpu_left_overs = gpu_capacity / vectorsize_bytes - num_gpu_batches * batchsize
    cpu_left_overs = cpu_capacity / vectorsize_bytes - num_cpu_batches * batchsize
    
    if self.verbose:
      if seq:
        num_valid_gpu_vectors = (gpu_capacity/vectorsize_bytes) - len(filenames[0])*(max_rw+max_lw)
        print num_valid_gpu_vectors

      else:
        print 'Batches in GPU memory: %d + leftovers %d' % (num_gpu_batches,
                                                            gpu_left_overs)
        print 'Batches in main memory: %d + leftovers %d' % (num_cpu_batches,
                                                             cpu_left_overs)
        print 'Batches in disk: %d + leftovers %d' % ((datasetsize / batchsize),
                                                      datasetsize % batchsize)
    
    if seq:
      import sequence_datahandler as seq_dh
      self.disk = seq_dh.SequenceDisk(
        filenames, numdim_list, datasetsize, keys=keys, left_window=left_window,
        right_window=right_window, verbose=verbose)
      self.cpu_cache = seq_dh.SequenceCache(
        self.disk, cpu_capacity, numdim_list, typesize = typesize,
        randomize=randomize, left_window=left_window,
        right_window=right_window, verbose=verbose)
      self.gpu_cache = seq_dh.SequenceGPUCache(
        self.cpu_cache, gpu_capacity, numdim_list, typesize = typesize,
        randomize=randomize, left_window=left_window,
        right_window=right_window, verbose=verbose, batchsize=batchsize)
    else:
      self.disk = Disk(filenames, numdim_list, datasetsize, keys=keys,
                       verbose=self.verbose)
      self.cpu_cache = Cache(self.disk, cpu_capacity, numdim_list,
                             typesize = typesize, randomize=randomize,
                             verbose=self.verbose)
      self.gpu_cache = GPUCache(self.cpu_cache, gpu_capacity, numdim_list,
                                typesize = typesize, randomize=randomize,
                                verbose=self.verbose, shift=shift, add_noise=add_noise,
                                center_only=not is_train, shift_amt_x=shift_amt_x, shift_amt_y=shift_amt_y)
    for i, stats_file in enumerate(stats_files):
      if hyperparameter_list[i].normalize and hyperparameter_list[i].activation != deepnet_pb2.Hyperparams.REPLICATED_SOFTMAX:
        self.gpu_cache.SetDataStats(i, stats_file)
    self.batchsize = batchsize
    if seq:
      datasetsize = actual_datasetsize
    self.num_batches = datasetsize / batchsize
    if self.get_last_piece and datasetsize % batchsize > 0:
      self.num_batches += 1

  def Get(self):
    """Returns a list of minibatches on the GPU.
    Each element of the list corresponds to one modality.
    """
    batch = self.gpu_cache.Get(self.batchsize, get_last_piece=self.get_last_piece)
    return batch

  def GetCPUBatches(self):
    """Returns batches from main memory."""
    batch = self.cpu_cache.Get(self.batchsize)
    return batch


class DataWriter(object):
  """Class for writing lots of data to disk."""

  def __init__(self, names, output_dir, memory, numdim_list, datasize=None):
    """Initializes a Data Writer.
    Args:
      names: Names used to identify the different data components. Will be used
        as prefixes for the output files.
      output_dir: Directory where the data will be written.
      memory: Size of each output chunk.
      numdim_list: Number of dimensions in each data component.
      datasize: Total number of data vectors that will be written. Having this
        number helps to save memory.
    """
    typesize = 4  # Fixed for now.
    self.typesize = typesize
    self.names = names
    self.output_dir = output_dir
    if not os.path.isdir(output_dir):
      os.makedirs(output_dir)
    self.numdim_list = numdim_list
    self.data_len = len(names)
    assert self.data_len == len(numdim_list)
    numdims = sum(numdim_list)
    total_memory = GetBytes(memory)
    if datasize is not None:
      total_memory_needed = datasize * typesize * numdims
      total_memory = min(total_memory, total_memory_needed)
    self.buffer_index = [0] * self.data_len
    self.dump_count = [0] * self.data_len
    self.data_written = [0] * self.data_len
    self.max_dumps = []
    self.buffers = []
    for numdim in numdim_list:
      memory = (total_memory * numdim) / numdims
      numvecs = memory / (typesize * numdim)
      data = np.zeros((numvecs, numdim), dtype='float32')
      self.buffers.append(data)
      if datasize is not None:
        max_dump = datasize / numvecs
        if datasize % numvecs > 0:
          max_dump += 1
        self.max_dumps.append(max_dump)
      else:
        self.max_dumps.append(1)

  def AddToBuffer(self, i, data):
    """Add data into buffer i."""
    buf = self.buffers[i]
    buf_index = self.buffer_index[i]
    datasize = data.shape[0]
    assert datasize + buf_index <= buf.shape[0], 'Not enough space in buffer.'
    buf[buf_index:buf_index + datasize] = data
    self.buffer_index[i] += datasize

  def FreeSpace(self, i):
    """Return amount of free space left."""
    return self.buffers[i].shape[0] - self.buffer_index[i]

  def HasSpace(self, i, datasize):
    """Return True if buffer i has space to add datasize more vectors."""
    buf = self.buffers[i]
    buf_index = self.buffer_index[i]
    return buf.shape[0] > buf_index + datasize
  
  def IsFull(self, i):
    return not self.HasSpace(i, 0)

  def DumpBuffer(self, i):
    """Write the contents of buffer i to disk."""
    buf_index = self.buffer_index[i]
    if buf_index == 0:
      return
    buf = self.buffers[i]
    output_prefix = os.path.join(self.output_dir, self.names[i])
    output_filename = '%s-%.5d-of-%.5d' % (
      output_prefix, (self.dump_count[i]+1), self.max_dumps[i])
    self.dump_count[i] += 1
    np.save(output_filename, buf[:buf_index])
    self.buffer_index[i] = 0
    self.data_written[i] += buf_index

  def SubmitOne(self, i, d):
    datasize = d.shape[0]
    free_space = self.FreeSpace(i)
    if datasize > free_space:
      self.AddToBuffer(i, d[:free_space])
    else:
      self.AddToBuffer(i, d)
    if self.IsFull(i):
      self.DumpBuffer(i)
    if datasize > free_space:
      self.SubmitOne(i, d[free_space:])

  def Submit(self, data):
    assert len(data) == self.data_len
    for i, d in enumerate(data):
      self.SubmitOne(i, d)

  def Commit(self):
    for i in range(self.data_len):
      self.DumpBuffer(i)
    return self.data_written

########NEW FILE########
__FILENAME__ = dbm
"""Implements a Deep Boltzmann Machine."""
from neuralnet import *

class DBM(NeuralNet):

  def __init__(self, *args, **kwargs):
    super(DBM, self).__init__(*args, **kwargs)
    self.initializer_net = None
    self.cd = self.t_op.optimizer == deepnet_pb2.Operation.CD

  @staticmethod
  def AreInputs(l):
    return reduce(lambda a, x: x.is_input and a, l, True)

  def SetPhase(self, layer, pos=True):
    """Setup required before starting a phase.

    This method makes 'state' and 'sample' point to the right variable depending
    on the phase.
    """
    if pos:
      layer.state = layer.pos_state
      layer.sample = layer.pos_sample
    else:
      layer.state = layer.neg_state
      layer.sample = layer.neg_sample

  def DumpModelState(self, step):
    state_dict = dict([(node.name, node.state.asarray().T) for node in self.node_list])
    filename = '/ais/gobi3/u/nitish/flickr/states/%s_%d' % (self.net.name, step)
    print 'Dumping state at step %d to %s' % (step, filename)
    np.savez(filename, **state_dict)

  def Sort(self):
    """Sort layers into useful orders.

    After this method is done:
    pos_phase_order: Order in which nodes have to be updated in the positive
      phase.
    neg_phase_order: Order in which nodes have to be updated in the negative
      phase.
    node_list: List of all nodes. All input nodes occur before non input ones.
    """
    non_input_nodes = []
    node_list = list(self.input_datalayer)
    for node in self.layer:
      if not node.is_input:
        non_input_nodes.append(node)
    node_list.extend(non_input_nodes)
    if self.net.positive_phase_order:
      self.pos_phase_order = [self.GetLayerByName(x) for x in self.net.positive_phase_order]
      self.pos_phase_order.extend([self.GetLayerByName(x) for x in self.unclamped_layer])
    else:
      self.pos_phase_order = non_input_nodes
    if self.net.negative_phase_order:
      self.neg_phase_order = [self.GetLayerByName(x) for x in self.net.negative_phase_order]
    else:
      self.neg_phase_order = node_list
    return node_list

  def ComputeUnnormalizedLogProb(self):
    pass

  def ComputeUp(self, layer, train=False, compute_input=False, step=0,
                maxsteps=0, use_samples=False, neg_phase=False):
    """
    Computes the state of a layer, given the state of its incoming neighbours.

    Args:
      train: True if this computation is happening during training, False during
        evaluation.
      compute_input: If True, the state of the input layer will be computed.
        Otherwise, it will be loaded as data.
      step: Training step.
      maxsteps: Maximum number of steps that will be taken (Some hyperparameters
        may depend on this.)
      use_samples: Use neighbours' samples to update the layer's state.
  """
    if layer.is_input and not compute_input:
      layer.GetData()
    else:
      for i, edge in enumerate(layer.incoming_edge):
        neighbour = layer.incoming_neighbour[i]
        if use_samples:
          inputs = neighbour.sample
        else:
          inputs = neighbour.state
        if edge.node2 == layer:
          w = edge.params['weight'].T
          factor = edge.proto.up_factor
        else:
          w = edge.params['weight']
          factor = edge.proto.down_factor
        if i == 0:
          cm.dot(w, inputs, target=layer.state)
          if factor != 1:
            layer.state.mult(factor)
        else:
          layer.state.add_dot(w, inputs, mult=factor)
      b = layer.params['bias']
      if layer.replicated_neighbour is None:
        layer.state.add_col_vec(b)
      else:
        layer.state.add_dot(b, layer.replicated_neighbour.NN)
      layer.ApplyActivation()
    if layer.hyperparams.dropout:
      if train and maxsteps - step >= layer.hyperparams.stop_dropout_for_last:
        # Randomly set states to zero.
        if not neg_phase:
          layer.mask.fill_with_rand()
          layer.mask.greater_than(layer.hyperparams.dropout_prob)
        layer.state.mult(layer.mask)
      else:
        # Produce expected output.
        layer.state.mult(1.0 - layer.hyperparams.dropout_prob)


  def PositivePhase(self, train=False, evaluate=False, step=0):
    """Perform the positive phase.

    This method computes the sufficient statistics under the data distribution.
    """

    # Do a forward pass in the initializer net, if set.
    if self.initializer_net:
      self.initializer_net.ForwardPropagate(train=train, step=step)

    # Initialize layers.
    for node in self.node_list:
      if node.is_input:
        # Load data into input nodes.
        self.ComputeUp(node, train=train)
      elif node.is_initialized:
        node.state.assign(node.initialization_source.state)
      else:
        # Initialize other nodes to zero.
        node.ResetState(rand=False)

    # Starting MF.
    for i in range(self.net.hyperparams.mf_steps):
      for node in self.pos_phase_order:
        self.ComputeUp(node, train=train, step=step, maxsteps=self.train_stop_steps)
    # End of MF.

    losses = []
    if train:
      for node in self.layer:
        r = node.CollectSufficientStatistics()
        if r is not None:  # This is true only if sparsity is active.
          perf = deepnet_pb2.Metrics()
          perf.MergeFrom(node.proto.performance_stats)
          perf.count = 1
          perf.sparsity = r
          losses.append(perf)
      for edge in self.edge:
        edge.CollectSufficientStatistics()

    # Evaluation
    # If CD, then this step would be performed by the negative phase anyways,
    # So the loss is measured in the negative phase instead. Return []
    # Otherwise, reconstruct the input given the other layers and report
    # the loss.
    if not self.cd or evaluate:
      for node in self.input_datalayer:
        self.ComputeUp(node, compute_input=True, step=step, maxsteps=self.train_stop_steps)
        losses.append(node.GetLoss())
    return losses

  def InitializeNegPhase(self, to_pos=False):
    """Initialize negative particles.

    Copies the pos state and samples it to initialize the ngative particles.
    """
    for layer in self.layer:
      self.SetPhase(layer, pos=False)
      if to_pos:
        layer.state.assign(layer.pos_state)
      else:
        layer.ResetState(rand=True)
      layer.Sample()
      self.SetPhase(layer, pos=True)

  def NegativePhase(self, step=0, train=True, gibbs_steps=-1):
    """Perform the negative phase.

    This method computes the sufficient statistics under the model distribution.
    Args:
      step: Training step
      train: If true, then this computation is happening during training.
      gibbs_steps: Number of gibbs steps to take. If -1, use default.
    """
    losses = []

    if self.cd:
      for node in self.node_list:
        if not node.is_input:
          node.Sample()
    else:
      for node in self.layer:
        self.SetPhase(node, pos=False)

    if gibbs_steps < 0:
      h = self.net.hyperparams
      start_after = h.start_step_up_cd_after
      if start_after > 0 and start_after < step:
        gibbs_steps = h.gibbs_steps + 1 + (step - start_after) / h.step_up_cd_after
      else:
        gibbs_steps = h.gibbs_steps

    for i in range(gibbs_steps):
      for node in self.neg_phase_order:
        self.ComputeUp(node, train=train, step=step,
                       maxsteps=self.train_stop_steps, use_samples=True,
                       compute_input=True, neg_phase=True)
        if i == 0 and node.is_input and self.cd:
          losses.append(node.GetLoss())
        if node.is_input:
          if node.sample_input and node.hyperparams.sample_input_after <= step:
            node.Sample()
          else:
            # Not sampling inputs usually makes learning faster.
            node.sample.assign(node.state)
        else:
          node.Sample()
    # End of Gibbs Sampling.

    if train:
      for node in self.layer:
        node.CollectSufficientStatistics(neg=True)
        self.UpdateLayerParams(node, step=step)
      for edge in self.edge:
        edge.CollectSufficientStatistics(neg=True)
        self.UpdateEdgeParams(edge, step=step)

    if not self.cd:
      for node in self.layer:
        self.SetPhase(node, pos=True)
    return losses

  def UpdateLayerParams(self, layer, step=0):
    """Update parameters associated with this layer."""
    layer.gradient.add_mult(layer.suff_stats, -1.0 / layer.batchsize)
    if layer.tied_to:
      layer.tied_to.gradient.add(layer.gradient)
      layer.gradient.assign(0)
      layer = layer.tied_to
    layer.num_grads_received += 1
    if layer.num_grads_received == layer.num_shares:
      layer.Update('bias', step, no_reg=True)  # By default, do not regularize bias.

  def UpdateEdgeParams(self, edge, step):
    """ Update the parameters associated with this edge."""
    numcases = edge.node1.batchsize
    edge.gradient.add_mult(edge.suff_stats, -1.0/numcases)
    if edge.tied_to:
      edge.tied_to.gradient.add(edge.gradient)
      edge.gradient.assign(0)
      edge = edge.tied_to
    edge.num_grads_received += 1
    if edge.num_grads_received == edge.num_shares:
      edge.Update('weight', step)

  def GetBatch(self, handler=None):
    super(DBM, self).GetBatch(handler=handler)
    if self.initializer_net:
      self.initializer_net.GetBatch()

  def TrainOneBatch(self, step):
    losses1 = self.PositivePhase(train=True, step=step)
    if step == 0 and self.t_op.optimizer == deepnet_pb2.Operation.PCD:
      self.InitializeNegPhase(to_pos=True)
    losses2 = self.NegativePhase(step, train=True)
    losses1.extend(losses2)
    return losses1
  
  def EvaluateOneBatch(self):
    losses = self.PositivePhase(train=False, evaluate=True)
    return losses

  def SetUpData(self, *args, **kwargs):
    super(DBM, self).SetUpData(*args, **kwargs)

    # Set up data for initializer net.
    if self.initializer_net:
      for node in self.initializer_net.layer:
        try:
          matching_dbm_node = next(l for l in self.layer \
                              if l.name == node.name)
        except StopIteration:
          matching_dbm_node = None
        if matching_dbm_node:
          if node.is_input or node.is_output:
            self.initializer_net.tied_datalayer.append(node)
            node.tied_to = matching_dbm_node
          elif matching_dbm_node.is_initialized:
            matching_dbm_node.initialization_source = node


  def LoadModelOnGPU(self, batchsize=-1):
    super(DBM, self).LoadModelOnGPU(batchsize=batchsize)
    if self.net.initializer_net:
      self.initializer_net = NeuralNet(self.net.initializer_net, self.t_op,
                                     self.e_op)
      self.initializer_net.LoadModelOnGPU(batchsize=batchsize)

  def Reconstruct(self, layername, numbatches, inputlayername=[],
                  validation=True):
    """Reconstruct from the model.
    Args:
      layername: Name of the layer which is to be reconstructed.
      numbatches: Number of batches to reconstruct.
      inputlayername: List of input layers whose states will be returned.
      validation: If True, reconstruct the validation set,
        else reconstruct test set.
    Returns:
      The reconstruction for layer 'layername' and inputs in layers
        'inputlayername'
    """
    step = 0
    self.recon = []
    self.inputs = []
    self.recon_pos = 0
    inputlayer = []
    layer_to_tap = self.GetLayerByName(layername, down=True)
    self.recon = np.zeros((numbatches * self.e_op.batchsize,
                           layer_to_tap.state.shape[0]))
    for i, lname in enumerate(inputlayername):
      l = self.GetLayerByName(lname)
      inputlayer.append(l)
      self.inputs.append(np.zeros((numbatches * self.e_op.batchsize,
                                   l.state.shape[0])))
    if validation:
      datagetter = self.GetValidationBatch
    else:
      datagetter = self.GetTestBatch
    for batch in range(numbatches):
      datagetter()
      self.ReconstructOneBatch(layer_to_tap, inputlayer)
    return self.recon, self.inputs

  def GetAllRepresentations(self, numbatches, validation=True):
    """Get representations at all layers.
    Returns:
      A dictionary with the name of the layer as the key and its state as as the
        value.
    """
    if validation:
      datagetter = self.GetValidationBatch
    else:
      datagetter = self.GetTestBatch
    rep_list = []
    names = []
    for node in self.node_list:
      rep_list.append(np.zeros((numbatches * node.state.shape[1],
                                node.state.shape[0]), dtype='float32'))
      names.append(node.name)
    for batch in range(numbatches):
      datagetter()
      self.PositivePhase(train=False, evaluate=False)
      for i, node in enumerate(self.node_list):
        rep_list[i][batch*node.batchsize:(batch+1)*node.batchsize,:] =\
            node.state.asarray().T
    return dict(zip(names, rep_list))

  def WriteRepresentationToDisk(self, layernames, output_dir, memory='1G',
                                dataset='test', input_recon=False):
    layers = [self.GetLayerByName(lname) for lname in layernames]
    numdim_list = [layer.state.shape[0] for layer in layers]
    if dataset == 'train':
      datagetter = self.GetTrainBatch
      if self.train_data_handler is None:
        return
      numbatches = self.train_data_handler.num_batches
      size = numbatches * self.train_data_handler.batchsize
    elif dataset == 'validation':
      datagetter = self.GetValidationBatch
      if self.validation_data_handler is None:
        return
      numbatches = self.validation_data_handler.num_batches
      size = numbatches * self.validation_data_handler.batchsize
    elif dataset == 'test':
      datagetter = self.GetTestBatch
      if self.test_data_handler is None:
        return
      numbatches = self.test_data_handler.num_batches
      size = numbatches * self.test_data_handler.batchsize
    datawriter = DataWriter(layernames, output_dir, memory, numdim_list, size)

    for batch in range(numbatches):
      datagetter()
      sys.stdout.write('\r%d' % (batch+1))
      sys.stdout.flush()
      self.PositivePhase(train=False, evaluate=input_recon)
      reprs = [l.state.asarray().T for l in layers]
      datawriter.Submit(reprs)
    sys.stdout.write('\n')
    size = datawriter.Commit()
    return size

  def GetRepresentation(self, layername, numbatches, inputlayername=[],
                        validation=True):
    """Get the representation at layer 'layername'."""
    step = 0
    self.rep_pos = 0
    inputlayer = []
    self.inputs = []
    layer_to_tap = self.GetLayerByName(layername)
    self.rep = np.zeros((numbatches * self.e_op.batchsize, layer_to_tap.state.shape[0]))
    for i, lname in enumerate(inputlayername):
      l = self.GetLayerByName(lname)
      inputlayer.append(l)
      self.inputs.append(np.zeros((numbatches * self.e_op.batchsize,
                                   l.state.shape[0])))
    if validation:
      datagetter = self.GetValidationBatch
    else:
      datagetter = self.GetTestBatch
    for batch in range(numbatches):
      datagetter()
      self.GetRepresentationOneBatch(layer_to_tap, inputlayer)
    return self.rep, self.inputs

  def GetLayerByName(self, layername, down=False):
    try:
      l = next(l for l in self.layer if l.name == layername)
    except StopIteration:
      l = None
    return l

  def Inference(self, steps, layernames, unclamped_layers, output_dir, memory='1G', dataset='test', method='gibbs'):
    layers_to_infer = [self.GetLayerByName(l) for l in layernames]
    layers_to_unclamp = [self.GetLayerByName(l) for l in unclamped_layers]

    numdim_list = [layer.state.shape[0] for layer in layers_to_infer]
    for l in layers_to_unclamp:
      l.is_input = False
      self.pos_phase_order.append(l)

    if dataset == 'train':
      datagetter = self.GetTrainBatch
      if self.train_data_handler is None:
        return
      numbatches = self.train_data_handler.num_batches
      size = numbatches * self.train_data_handler.batchsize
    elif dataset == 'validation':
      datagetter = self.GetValidationBatch
      if self.validation_data_handler is None:
        return
      numbatches = self.validation_data_handler.num_batches
      size = numbatches * self.validation_data_handler.batchsize
    elif dataset == 'test':
      datagetter = self.GetTestBatch
      if self.test_data_handler is None:
        return
      numbatches = self.test_data_handler.num_batches
      size = numbatches * self.test_data_handler.batchsize
    dw = DataWriter(layernames, output_dir, memory, numdim_list, size)

    gibbs = method == 'gibbs'
    mf = method == 'mf'

    for batch in range(numbatches):
      sys.stdout.write('\r%d' % (batch+1))
      sys.stdout.flush()
      datagetter()
      for node in self.node_list:
        if node.is_input or node.is_initialized:
          node.GetData()
        else:
          node.ResetState(rand=False)
        if gibbs:
          node.sample.assign(node.state)
      for i in range(steps):
        for node in self.pos_phase_order:
          self.ComputeUp(node, use_samples=gibbs)
          if gibbs:
            node.Sample()
      output = [l.state.asarray().T for l in layers_to_infer]
      dw.Submit(output)
    sys.stdout.write('\n')
    size = dw.Commit()
    return size[0]

  def ReconstructOneBatch(self, layer, inputlayers):
    self.PositivePhase(train=False, evaluate=True)
    self.recon[self.recon_pos:self.recon_pos + self.e_op.batchsize,:] =\
      layer.state.asarray().T
    for i, l in enumerate(inputlayers):
      self.inputs[i][self.recon_pos:self.recon_pos + self.e_op.batchsize,:] =\
        l.data.asarray().T
    self.recon_pos += self.e_op.batchsize

  def GetRepresentationOneBatch(self, layer, inputlayers):
    self.PositivePhase(train=False, evaluate=False)
    if layer.proto.is_input:
      self.rep[self.rep_pos:self.rep_pos + self.e_op.batchsize,:] =\
          layer.data.asarray().T
    else:
      self.rep[self.rep_pos:self.rep_pos + self.e_op.batchsize,:] =\
          layer.state.asarray().T
    for i, l in enumerate(inputlayers):
      self.inputs[i][self.rep_pos:self.rep_pos + self.e_op.batchsize,:] =\
        l.data.asarray().T
    self.rep_pos += self.e_op.batchsize

  def UnclampLayer(self, layername):
    """Unclamps the layer 'layername'.
    
    Most useful when called just after calling the constructor.
    """
    for l in self.net.layer:
      if l.name == layername:
        print 'Unclamping %s' % layername
        l.is_input = False
        self.unclamped_layer.append(l.name)

########NEW FILE########
__FILENAME__ = dbn
"""Implements a Deep Belief Network."""
from dbm import *

class DBN(DBM):

  def __init__(self, net, t_op=None, e_op=None):
    rbm, upward_net, downward_net, junction_layers = DBN.SplitDBN(net)
    self.rbm = DBM(rbm, t_op, e_op)
    self.upward_net = NeuralNet(upward_net, t_op, e_op)
    self.downward_net = NeuralNet(downward_net, t_op, e_op)
    self.junction_layers = junction_layers
    self.net = self.rbm.net
    self.t_op = self.rbm.t_op
    self.e_op = self.rbm.e_op
    self.verbose = self.rbm.verbose
    self.batchsize = self.t_op.batchsize

  def CopyModelToCPU(self):
    self.rbm.CopyModelToCPU()

  def DeepCopy(self):
    return CopyModel(self.rbm.net)

  def Show(self):
    """Visualize the state of the layers and edges in the network."""
    self.rbm.Show()
    self.upward_net.Show()
    self.downward_net.Show()

  def PrintNetwork(self):
    print 'RBM:'
    self.rbm.PrintNetwork()
    print 'Up:'
    self.upward_net.PrintNetwork()
    print 'Down:'
    self.downward_net.PrintNetwork()

  def ExchangeGlobalInfo(self):
    for layer in self.rbm.layer:
      layer.GetGlobalInfo(self)
    for edge in self.rbm.edge:
      edge.GetGlobalInfo(self)

  @staticmethod
  def SplitDBN(net):
    #net = ReadModel(dbn_file)
    rbm = deepnet_pb2.Model()
    rbm.CopyFrom(net)
    rbm.name = '%s_rbm' % net.name
    rbm.model_type = deepnet_pb2.Model.DBM
    
    directed_edges = []
    undirected_edges = []
    layer1 = set()  # Layers that are touched by directed edges.
    layer2 = set()  # Layers that are touched by undirected edges.
    for e in net.edge:
      if e.directed:
        directed_edges.append(e)
        layer1.add(e.node1)
        layer1.add(e.node2)
      else:
        undirected_edges.append(e)
        layer2.add(e.node1)
        layer2.add(e.node2)

    junction_layers = list(layer1.intersection(layer2))
    
    # CONTRUCT RBM.
    del rbm.edge[:]
    for e in undirected_edges:
      rbm.edge.extend([e])

    del rbm.layer[:]
    for node in list(layer2):
      l = next(l for l in net.layer if l.name == node)
      layer = rbm.layer.add()
      layer.CopyFrom(l)
      if node in junction_layers:
        layer.is_input = True
        del layer.param[:]
        for p in l.param:
          if p.name == 'bias':
            continue
          elif p.name == 'bias_generative':
            p_copy = layer.param.add()
            p_copy.CopyFrom(p)
            p_copy.name = 'bias'
          else:
            layer.param.extend([p])

    # CONSTRUCT DOWNNARD NET.
    down_net = deepnet_pb2.Model()
    down_net.CopyFrom(net)
    down_net.name = '%s_downward_net' % net.name
    down_net.model_type = deepnet_pb2.Model.FEED_FORWARD_NET

    del down_net.edge[:]
    for e in directed_edges:
      down_net.edge.extend([e])

    del down_net.layer[:]
    for node in list(layer1):
      l = next(l for l in net.layer if l.name == node)
      layer_down = down_net.layer.add()
      layer_down.CopyFrom(l)
      if l.is_input:
        layer_down.is_input = False
      if node in junction_layers:
        layer_down.is_input = True
      del layer_down.param[:]
      for p in l.param:
        if p.name == 'bias':
          continue
        elif p.name == 'bias_generative':
          p_copy = layer_down.param.add()
          p_copy.CopyFrom(p)
          p_copy.name = 'bias'
        else:
          layer_down.param.extend([p])

    # CONSTRUCT UPWARD NET.
    up_net = deepnet_pb2.Model()
    up_net.CopyFrom(net)
    up_net.name = '%s_upward_net' % net.name
    up_net.model_type = deepnet_pb2.Model.FEED_FORWARD_NET
    del up_net.edge[:]
    for e in directed_edges:
      e_up = DBN.ReverseEdge(e)
      up_net.edge.extend([e_up])
    del up_net.layer[:]
    for node in list(layer1):
      l = next(l for l in net.layer if l.name == node)
      layer_up = up_net.layer.add()
      layer_up.CopyFrom(l)
      del layer_up.param[:]
      for p in l.param:
        if p.name == 'bias_generative':
          continue
        else:
          layer_up.param.extend([p])

    return rbm, up_net, down_net, junction_layers

  @staticmethod
  def ReverseEdge(e):
    rev_e = deepnet_pb2.Edge()
    rev_e.CopyFrom(e)
    rev_e.node1 = e.node2
    rev_e.node2 = e.node1
    rev_e.up_factor = e.down_factor
    rev_e.down_factor = e.up_factor
    for p in rev_e.param:
      if p.name == 'weight':
        if p.initialization == deepnet_pb2.Parameter.PRETRAINED:
          p.transpose_pretrained = not p.transpose_pretrained
        elif p.mat:
          mat = ParameterAsNumpy(p).T
          p.mat = NumpyAsParameter(mat)
          del p.dimensions
          for dim in mat.shape:
            p.dimensions.add(dim)
    return rev_e

  def LoadModelOnGPU(self, *args, **kwargs):
    self.rbm.LoadModelOnGPU(*args, **kwargs)
    self.upward_net.LoadModelOnGPU(*args, **kwargs)
    self.downward_net.LoadModelOnGPU(*args, **kwargs)
    self.TieUpNets()

  def TieUpNets(self):
    # Tie up nets.
    for layer_name in self.junction_layers:
      rbm_layer = next(l for l in self.rbm.layer if l.name == layer_name)
      up_layer = next(l for l in self.upward_net.layer if l.name == layer_name)
      down_layer = next(l for l in self.downward_net.layer if l.name == layer_name)
      rbm_layer.data = up_layer.state
      down_layer.data = rbm_layer.state

  def ResetBatchsize(self, batchsize):
    self.batchsize = batchsize
    self.rbm.ResetBatchsize(batchsize)
    self.upward_net.ResetBatchsize(batchsize)
    self.downward_net.ResetBatchsize(batchsize)
    self.TieUpNets()

  def SetUpData(self, *args, **kwargs):
    self.upward_net.SetUpData(*args, **kwargs)
    self.train_data_handler = self.upward_net.train_data_handler
    self.validation_data_handler = self.upward_net.validation_data_handler
    self.test_data_handler = self.upward_net.test_data_handler

  def GetBatch(self, handler=None):
    if handler:
      data_list = handler.Get()
      if data_list[0].shape[1] != self.batchsize:
        self.ResetBatchsize(data_list[0].shape[1])
      for i, layer in enumerate(self.upward_net.datalayer):
        layer.SetData(data_list[i])
    for layer in self.upward_net.tied_datalayer:
      layer.SetData(layer.tied_to.data)

  def TrainOneBatch(self, step):
    self.upward_net.ForwardPropagate(train=True, step=step)
    return self.rbm.TrainOneBatch(step)
 
  def PositivePhase(self, train=False, evaluate=False, step=0):
    self.upward_net.ForwardPropagate(train=train, step=step)
    return self.rbm.PositivePhase(train=train, evaluate=evaluate, step=step)
    #self.downward_net.ForwardPropagate(train=train, step=step)

  def NegativePhase(self, *args, **kwargs):
    return self.rbm.NegativePhase(*args, **kwargs)

  def Inference(self, steps, layernames, unclamped_layers, output_dir, memory='1G', dataset='test', method='gibbs'):
    layers_to_infer = [self.GetLayerByName(l, down=True) for l in layernames]
    layers_to_unclamp = [self.GetLayerByName(l) for l in unclamped_layers]

    numdim_list = [layer.state.shape[0] for layer in layers_to_infer]
    upward_net_unclamped_inputs = []
    for l in layers_to_unclamp:
      l.is_input = False
      l.is_initialized = True
      if l in self.rbm.layer:
        self.rbm.pos_phase_order.append(l)
      else:
        upward_net_unclamped_inputs.append(l)

    if dataset == 'train':
      datagetter = self.GetTrainBatch
      if self.train_data_handler is None:
        return
      numbatches = self.train_data_handler.num_batches
      size = numbatches * self.train_data_handler.batchsize
    elif dataset == 'validation':
      datagetter = self.GetValidationBatch
      if self.validation_data_handler is None:
        return
      numbatches = self.validation_data_handler.num_batches
      size = numbatches * self.validation_data_handler.batchsize
    elif dataset == 'test':
      datagetter = self.GetTestBatch
      if self.test_data_handler is None:
        return
      numbatches = self.test_data_handler.num_batches
      size = numbatches * self.test_data_handler.batchsize
    dw = DataWriter(layernames, output_dir, memory, numdim_list, size)

    gibbs = method == 'gibbs'
    mf = method == 'mf'

    for batch in range(numbatches):
      sys.stdout.write('\r%d' % (batch+1))
      sys.stdout.flush()
      datagetter()
      for l in upward_net_unclamped_inputs:
        l.data.assign(0)
      self.upward_net.ForwardPropagate()
      for node in self.rbm.node_list:
        if node.is_input or node.is_initialized:
          node.GetData()
          if gibbs:
            node.sample.assign(node.state)
        else:
          node.ResetState(rand=False)
      for i in range(steps):
        for node in self.rbm.pos_phase_order:
          self.ComputeUp(node, use_samples=gibbs)
          if gibbs:
            node.Sample()
      self.downward_net.ForwardPropagate()
      output = [l.state.asarray().T for l in layers_to_infer]
      dw.Submit(output)
    sys.stdout.write('\n')
    size = dw.Commit()
    return size[0]

  def GetLayerByName(self, layername, down=False):
    layer = self.rbm.GetLayerByName(layername)
    if layer is None:
      if down:
        layer = self.downward_net.GetLayerByName(layername)
      else:
        layer = self.upward_net.GetLayerByName(layername)
    return layer

########NEW FILE########
__FILENAME__ = deepnet_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='deepnet.proto',
  package='deepnet',
  serialized_pb='\n\rdeepnet.proto\x12\x07\x64\x65\x65pnet\"\xda\x05\n\x05Layer\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x14\n\x0c\x66ile_pattern\x18\x02 \x01(\t\x12\x12\n\ndimensions\x18\x03 \x02(\x05\x12\x14\n\tnumlabels\x18\x04 \x01(\x05:\x01\x31\x12!\n\x05param\x18\x05 \x03(\x0b\x32\x12.deepnet.Parameter\x12\x17\n\x08is_input\x18\x07 \x01(\x08:\x05\x66\x61lse\x12\x18\n\tis_output\x18\x08 \x01(\x08:\x05\x66\x61lse\x12@\n\rloss_function\x18\t \x01(\x0e\x32\x1b.deepnet.Layer.LossFunction:\x0cSQUARED_LOSS\x12)\n\x0bhyperparams\x18\n \x01(\x0b\x32\x14.deepnet.Hyperparams\x12,\n\ndata_field\x18\x0b \x01(\x0b\x32\x18.deepnet.Layer.DataField\x12+\n\x11performance_stats\x18\x0c \x01(\x0b\x32\x10.deepnet.Metrics\x12\r\n\x05shape\x18\r \x03(\x05\x12\x1d\n\x0eis_initialized\x18\x0e \x01(\x08:\x05\x66\x61lse\x12\x0e\n\x06prefix\x18\x0f \x01(\t\x12\x1c\n\x0ereplicate_bias\x18\x10 \x01(\x08:\x04true\x12\x13\n\x04tied\x18\x11 \x01(\x08:\x05\x66\x61lse\x12\x0f\n\x07tied_to\x18\x12 \x01(\t\x12\x16\n\x0bloss_weight\x18\x13 \x01(\x02:\x01\x31\x1a\x85\x01\n\tDataField\x12\r\n\x05train\x18\x01 \x01(\t\x12\x12\n\nvalidation\x18\x02 \x01(\t\x12\x0c\n\x04test\x18\x03 \x01(\t\x12\r\n\x05model\x18\x04 \x01(\t\x12\x12\n\nlayer_name\x18\x05 \x01(\t\x12\x13\n\x04tied\x18\x06 \x01(\x08:\x05\x66\x61lse\x12\x0f\n\x07tied_to\x18\x07 \x01(\t\"C\n\x0cLossFunction\x12\x10\n\x0cSQUARED_LOSS\x10\x00\x12\x11\n\rCROSS_ENTROPY\x10\x01\x12\x0e\n\nHINGE_LOSS\x10\x02\"\xa4\x07\n\tParameter\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0b\n\x03mat\x18\x02 \x01(\x0c\x12\x12\n\ndimensions\x18\x03 \x03(\x05\x12\x43\n\x0einitialization\x18\x04 \x01(\x0e\x32!.deepnet.Parameter.Initialization:\x08\x43ONSTANT\x12\x14\n\x05sigma\x18\x05 \x01(\x02:\x05\x30.001\x12\x13\n\x08\x63onstant\x18\x06 \x01(\x02:\x01\x30\x12\x13\n\x04\x63onv\x18\x07 \x01(\x08:\x05\x66\x61lse\x12\x33\n\x0b\x63onv_params\x18\x08 \x01(\x0b\x32\x1e.deepnet.Parameter.Convolution\x12\x18\n\x10pretrained_model\x18\t \x03(\t\x12\x1e\n\x16pretrained_model_node1\x18\n \x01(\t\x12\x1e\n\x16pretrained_model_node2\x18\x0b \x01(\t\x12#\n\x14transpose_pretrained\x18\x0c \x01(\x08:\x05\x66\x61lse\x12#\n\x1bpretrained_model_param_name\x18\r \x01(\t\x12\x14\n\x05local\x18\x0e \x01(\x08:\x05\x66\x61lse\x12\x16\n\x0bmult_factor\x18\x0f \x01(\x02:\x01\x31\x1a\xaf\x02\n\x0b\x43onvolution\x12\x0f\n\x04size\x18\x01 \x01(\x05:\x01\x30\x12\x11\n\x06stride\x18\x02 \x01(\x05:\x01\x30\x12\x12\n\x07padding\x18\x03 \x01(\x05:\x01\x30\x12\x16\n\x0bnum_filters\x18\x04 \x01(\x05:\x01\x30\x12\x15\n\nnum_colors\x18\x05 \x01(\x05:\x01\x30\x12\x17\n\x08max_pool\x18\x06 \x01(\x08:\x05\x66\x61lse\x12\x14\n\tpool_size\x18\x07 \x01(\x05:\x01\x30\x12\x16\n\x0bpool_stride\x18\x08 \x01(\x05:\x01\x30\x12\x14\n\x05rnorm\x18\t \x01(\x08:\x05\x66\x61lse\x12\x14\n\tnorm_size\x18\n \x01(\x05:\x01\x30\x12\x17\n\tpow_scale\x18\x0b \x01(\x02:\x04\x30.75\x12\x18\n\tadd_scale\x18\x0c \x01(\x02:\x05\x30.001\x12\x13\n\x04prob\x18\r \x01(\x08:\x05\x66\x61lse\"\xa9\x01\n\x0eInitialization\x12\x12\n\x0e\x44\x45NSE_GAUSSIAN\x10\x00\x12\x13\n\x0fSPARSE_GAUSSIAN\x10\x01\x12\x0c\n\x08\x43ONSTANT\x10\x02\x12\x1e\n\x1a\x44\x45NSE_GAUSSIAN_SQRT_FAN_IN\x10\x03\x12\x0e\n\nPRETRAINED\x10\x04\x12\x11\n\rDENSE_UNIFORM\x10\x05\x12\x1d\n\x19\x44\x45NSE_UNIFORM_SQRT_FAN_IN\x10\x06\"\xd8\x10\n\x0bHyperparams\x12\x1a\n\x0c\x62\x61se_epsilon\x18\x01 \x01(\x02:\x04\x30.01\x12\x37\n\repsilon_decay\x18\x02 \x01(\x0e\x32\x1a.deepnet.Hyperparams.Decay:\x04NONE\x12%\n\x17\x65psilon_decay_half_life\x18\x03 \x01(\x05:\x04\x31\x30\x30\x30\x12\x1b\n\x10initial_momentum\x18\x04 \x01(\x02:\x01\x30\x12\x19\n\x0e\x66inal_momentum\x18\x05 \x01(\x02:\x01\x30\x12!\n\x15momentum_change_steps\x18\x06 \x01(\x05:\x02\x31\x30\x12\x17\n\x08sparsity\x18\x07 \x01(\x08:\x05\x66\x61lse\x12\x1c\n\x0fsparsity_target\x18\x08 \x01(\x02:\x03\x30.1\x12\x1c\n\rsparsity_cost\x18\t \x01(\x02:\x05\x30.001\x12\x1d\n\x10sparsity_damping\x18\n \x01(\x02:\x03\x30.9\x12\x16\n\x07\x64ropout\x18\x0b \x01(\x08:\x05\x66\x61lse\x12\x19\n\x0c\x64ropout_prob\x18\x0c \x01(\x02:\x03\x30.5\x12 \n\x11\x61pply_weight_norm\x18\r \x01(\x08:\x05\x66\x61lse\x12\x17\n\x0bweight_norm\x18\x0e \x01(\x02:\x02\x31\x30\x12\x1d\n\x0e\x61pply_l2_decay\x18\x0f \x01(\x08:\x05\x66\x61lse\x12\x16\n\x08l2_decay\x18\x10 \x01(\x02:\x04\x30.01\x12;\n\nactivation\x18\x11 \x01(\x0e\x32\x1f.deepnet.Hyperparams.Activation:\x06LINEAR\x12\x16\n\x0bleft_window\x18\x12 \x01(\x05:\x01\x30\x12\x17\n\x0cright_window\x18\x13 \x01(\x05:\x01\x30\x12\x13\n\x08mf_steps\x18\x14 \x01(\x05:\x01\x31\x12\x16\n\x0bgibbs_steps\x18\x15 \x01(\x05:\x01\x31\x12\x33\n\x05\x61\x64\x61pt\x18\x18 \x01(\x0e\x32\x1a.deepnet.Hyperparams.Adapt:\x08NO_ADAPT\x12 \n\x15stop_dropout_for_last\x18\x19 \x01(\x05:\x01\x30\x12\x1d\n\x0e\x65nable_display\x18\x1a \x01(\x08:\x05\x66\x61lse\x12\x18\n\tnormalize\x18\x1b \x01(\x08:\x05\x66\x61lse\x12\x17\n\x0cnormalize_to\x18\x1c \x01(\x02:\x01\x31\x12\x1f\n\x14start_learning_after\x18\x1d \x01(\x05:\x01\x30\x12\x1b\n\x10step_up_cd_after\x18\x1e \x01(\x05:\x01\x30\x12\'\n\x1c\x64\x65\x63\x61y_learning_rate_for_last\x18\x1f \x01(\x05:\x01\x30\x12\x1e\n\x0flearn_precision\x18  \x01(\x08:\x05\x66\x61lse\x12\x1c\n\x11precision_epsilon\x18! \x01(\x02:\x01\x30\x12 \n\x15precision_upper_bound\x18\" \x01(\x02:\x01\x31\x12\x1d\n\x0e\x61pply_l1_decay\x18# \x01(\x08:\x05\x66\x61lse\x12\x16\n\x08l1_decay\x18$ \x01(\x02:\x04\x30.01\x12\x1e\n\x13\x61pply_l1decay_after\x18% \x01(\x05:\x01\x30\x12\x18\n\tadd_noise\x18& \x01(\x08:\x05\x66\x61lse\x12\x14\n\x05shift\x18\' \x01(\x08:\x05\x66\x61lse\x12\x16\n\x0bshift_amt_x\x18( \x01(\x05:\x01\x30\x12\x14\n\tblocksize\x18) \x01(\x05:\x01\x31\x12\x16\n\x0bshift_amt_y\x18* \x01(\x05:\x01\x30\x12\x13\n\x08sc_alpha\x18+ \x01(\x02:\x01\x30\x12\x12\n\x07sc_beta\x18, \x01(\x02:\x01\x30\x12\x13\n\x08sc_gamma\x18- \x01(\x02:\x01\x30\x12\x1b\n\x0csample_input\x18. \x01(\x08:\x05\x66\x61lse\x12\x1b\n\x0cmult_dropout\x18/ \x01(\x08:\x05\x66\x61lse\x12\'\n\x18select_model_using_error\x18\x30 \x01(\x08:\x05\x66\x61lse\x12\x1d\n\x12sample_input_after\x18\x31 \x01(\x05:\x01\x30\x12\x19\n\x0e\x61\x64\x64itive_prior\x18\x32 \x01(\x05:\x01\x30\x12\x1f\n\x14multiplicative_prior\x18\x33 \x01(\x05:\x01\x30\x12\x19\n\x0e\x61\x64\x61ptive_prior\x18\x34 \x01(\x05:\x01\x30\x12\x1e\n\x0fnormalize_error\x18\x35 \x01(\x08:\x05\x66\x61lse\x12!\n\x16start_step_up_cd_after\x18\x36 \x01(\x05:\x01\x30\x12%\n\x16select_model_using_acc\x18\x37 \x01(\x08:\x05\x66\x61lse\x12%\n\x16select_model_using_map\x18\x38 \x01(\x08:\x05\x66\x61lse\x12\x1b\n\x0c\x66\x61st_dropout\x18\x39 \x01(\x08:\x05\x66\x61lse\x12\x1c\n\x11\x66\x61st_dropout_cost\x18: \x01(\x02:\x01\x30\x12\x1b\n\x0cshared_prior\x18; \x01(\x08:\x05\x66\x61lse\x12\x19\n\x11shared_prior_file\x18< \x01(\t\x12\x19\n\x11shared_prior_edge\x18= \x01(\t\x12\x1c\n\x11shared_prior_cost\x18> \x01(\x02:\x01\x30\x12 \n\x11soft_shared_prior\x18? \x01(\x08:\x05\x66\x61lse\x12\x17\n\x0flabel_freq_file\x18@ \x01(\t\"1\n\x05\x44\x65\x63\x61y\x12\x08\n\x04NONE\x10\x00\x12\r\n\tINVERSE_T\x10\x01\x12\x0f\n\x0b\x45XPONENTIAL\x10\x02\"\x9a\x01\n\nActivation\x12\n\n\x06LINEAR\x10\x00\x12\x0c\n\x08LOGISTIC\x10\x01\x12\x08\n\x04TANH\x10\x02\x12\x14\n\x10RECTIFIED_LINEAR\x10\x03\x12\x1b\n\x17RECTIFIED_LINEAR_SMOOTH\x10\x04\x12\x0b\n\x07SOFTMAX\x10\x05\x12\x16\n\x12REPLICATED_SOFTMAX\x10\x06\x12\x07\n\x03SIN\x10\x07\x12\x07\n\x03\x43OS\x10\x08\"\"\n\x05\x41\x64\x61pt\x12\x0c\n\x08NO_ADAPT\x10\x00\x12\x0b\n\x07\x41\x44\x41GRAD\x10\x01\"\x9d\x03\n\x04\x45\x64ge\x12\r\n\x05node1\x18\x01 \x02(\t\x12\r\n\x05node2\x18\x02 \x02(\t\x12\x16\n\x08\x64irected\x18\x03 \x01(\x08:\x04true\x12!\n\x05param\x18\x04 \x03(\x0b\x32\x12.deepnet.Parameter\x12)\n\x0bhyperparams\x18\x05 \x01(\x0b\x32\x14.deepnet.Hyperparams\x12 \n\x15receptive_field_width\x18\x06 \x01(\x05:\x01\x31\x12\x17\n\x0c\x64isplay_rows\x18\x07 \x01(\x05:\x01\x31\x12\x17\n\x0c\x64isplay_cols\x18\x08 \x01(\x05:\x01\x31\x12\x14\n\tup_factor\x18\t \x01(\x02:\x01\x31\x12\x16\n\x0b\x64own_factor\x18\n \x01(\x02:\x01\x31\x12\x0e\n\x06prefix\x18\x0b \x01(\t\x12\x13\n\x04tied\x18\x0c \x01(\x08:\x05\x66\x61lse\x12\x15\n\rtied_to_node1\x18\r \x01(\t\x12\x15\n\rtied_to_node2\x18\x0e \x01(\t\x12\x1d\n\x0etied_transpose\x18\x0f \x01(\x08:\x05\x66\x61lse\x12\x1d\n\x0e\x62lock_gradient\x18\x10 \x01(\x08:\x05\x66\x61lse\"\x85\x05\n\x05Model\x12\x0c\n\x04name\x18\x01 \x02(\t\x12,\n\nmodel_type\x18\x02 \x02(\x0e\x32\x18.deepnet.Model.ModelType\x12\x1d\n\x05layer\x18\x03 \x03(\x0b\x32\x0e.deepnet.Layer\x12\x1b\n\x04\x65\x64ge\x18\x04 \x03(\x0b\x32\r.deepnet.Edge\x12)\n\x0bhyperparams\x18\x05 \x01(\x0b\x32\x14.deepnet.Hyperparams\x12%\n\x0btrain_stats\x18\x06 \x03(\x0b\x32\x10.deepnet.Metrics\x12*\n\x10validation_stats\x18\x07 \x03(\x0b\x32\x10.deepnet.Metrics\x12$\n\ntest_stats\x18\x08 \x03(\x0b\x32\x10.deepnet.Metrics\x12\x0f\n\x04seed\x18\t \x01(\x05:\x01\x30\x12\x1c\n\x14positive_phase_order\x18\n \x03(\t\x12\x1c\n\x14negative_phase_order\x18\x0b \x03(\t\x12\x17\n\x0finitializer_net\x18\x0c \x01(\t\x12\x0e\n\x06prefix\x18\r \x01(\t\x12)\n\x0f\x62\x65st_valid_stat\x18\x0e \x01(\x0b\x32\x10.deepnet.Metrics\x12\'\n\rtrain_stat_es\x18\x0f \x01(\x0b\x32\x10.deepnet.Metrics\x12&\n\x0ctest_stat_es\x18\x10 \x01(\x0b\x32\x10.deepnet.Metrics\"n\n\tModelType\x12\x14\n\x10\x46\x45\x45\x44_FORWARD_NET\x10\x00\x12\x11\n\rRECURRENT_NET\x10\x01\x12\x07\n\x03\x44\x42N\x10\x02\x12\x07\n\x03\x44\x42M\x10\x03\x12\x10\n\x0cSPARSE_CODER\x10\x04\x12\x14\n\x10\x46\x41ST_DROPOUT_NET\x10\x05\"\xe4\x04\n\tOperation\x12/\n\toptimizer\x18\x01 \x02(\x0e\x32\x1c.deepnet.Operation.Optimizer\x12\x37\n\rstopcondition\x18\x02 \x02(\x0b\x32 .deepnet.Operation.StopCondition\x12\x14\n\x05train\x18\x03 \x01(\x08:\x05\x66\x61lse\x12\x17\n\x0c\x63urrent_step\x18\x04 \x01(\x05:\x01\x30\x12\x14\n\tbatchsize\x18\x05 \x01(\x05:\x01\x31\x12\x12\n\ndata_proto\x18\x06 \x02(\t\x12\x15\n\neval_after\x18\x07 \x01(\x05:\x01\x31\x12\x1b\n\x10\x63heckpoint_after\x18\x08 \x01(\x05:\x01\x31\x12#\n\x14\x63heckpoint_directory\x18\t \x01(\t:\x05/tmp/\x12\x1d\n\x0fskip_last_piece\x18\n \x01(\x08:\x04true\x12\x18\n\trandomize\x18\x0e \x01(\x08:\x05\x66\x61lse\x12\x15\n\nshow_after\x18\x0f \x01(\x05:\x01\x30\x12\x16\n\x07verbose\x18\x10 \x01(\x08:\x05\x66\x61lse\x12\x1d\n\x0eget_last_piece\x18\x11 \x01(\x08:\x05\x66\x61lse\x12\x19\n\x11\x64\x61ta_proto_prefix\x18\x12 \x01(\t\x12\x19\n\x11\x63heckpoint_prefix\x18\x13 \x01(\t\x1a?\n\rStopCondition\x12\x1c\n\rall_processed\x18\x01 \x01(\x08:\x05\x66\x61lse\x12\x10\n\x05steps\x18\x02 \x01(\x05:\x01\x30\"=\n\tOptimizer\x12\x14\n\x10GRADIENT_DESCENT\x10\x00\x12\t\n\x05LBFGS\x10\x03\x12\x06\n\x02\x43\x44\x10\x04\x12\x07\n\x03PCD\x10\x05\"\xf4\x02\n\x07Metrics\x12\x10\n\x05\x63ount\x18\x01 \x01(\x05:\x01\x30\x12\x15\n\rcorrect_preds\x18\x02 \x01(\x02\x12$\n\x15\x63ompute_correct_preds\x18\x03 \x01(\x08:\x05\x66\x61lse\x12\x15\n\rcross_entropy\x18\x04 \x01(\x02\x12$\n\x15\x63ompute_cross_entropy\x18\x05 \x01(\x08:\x05\x66\x61lse\x12\r\n\x05\x65rror\x18\x06 \x01(\x02\x12\x1c\n\rcompute_error\x18\x07 \x01(\x08:\x05\x66\x61lse\x12\x0b\n\x03MAP\x18\x08 \x01(\x02\x12\x1a\n\x0b\x63ompute_MAP\x18\t \x01(\x08:\x05\x66\x61lse\x12\x0e\n\x06prec50\x18\n \x01(\x02\x12\x1d\n\x0e\x63ompute_prec50\x18\x0b \x01(\x08:\x05\x66\x61lse\x12\x10\n\x08MAP_list\x18\x0c \x03(\x02\x12\x13\n\x0bprec50_list\x18\r \x03(\x02\x12\x10\n\x08sparsity\x18\x0e \x01(\x02\x12\x1f\n\x10\x63ompute_sparsity\x18\x0f \x01(\x08:\x05\x66\x61lse\"\xd0\x02\n\x07\x44\x61taset\x12\x0c\n\x04name\x18\x01 \x02(\t\x12#\n\x04\x64\x61ta\x18\x02 \x03(\x0b\x32\x15.deepnet.Dataset.Data\x12\x16\n\ngpu_memory\x18\x03 \x01(\t:\x02\x32G\x12\x17\n\x0bmain_memory\x18\x04 \x01(\t:\x02\x34G\x12\x1d\n\x0c\x64\x61ta_handler\x18\x05 \x01(\t:\x07\x64\x65\x65pnet\x12\x10\n\x06prefix\x18\x06 \x01(\t:\x00\x1a\xaf\x01\n\x04\x44\x61ta\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x14\n\x0c\x66ile_pattern\x18\x02 \x02(\t\x12\x0c\n\x04size\x18\x03 \x02(\x05\x12\x12\n\ndimensions\x18\x04 \x03(\x05\x12\x15\n\nnum_labels\x18\x05 \x01(\x05:\x01\x31\x12\x0b\n\x03key\x18\x06 \x01(\t\x12\x15\n\x06sparse\x18\x07 \x01(\x08:\x05\x66\x61lse\x12\x12\n\x03seq\x18\x08 \x01(\x08:\x05\x66\x61lse\x12\x12\n\nstats_file\x18\t \x01(\t')



_LAYER_LOSSFUNCTION = descriptor.EnumDescriptor(
  name='LossFunction',
  full_name='deepnet.Layer.LossFunction',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='SQUARED_LOSS', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CROSS_ENTROPY', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='HINGE_LOSS', index=2, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=690,
  serialized_end=757,
)

_PARAMETER_INITIALIZATION = descriptor.EnumDescriptor(
  name='Initialization',
  full_name='deepnet.Parameter.Initialization',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='DENSE_GAUSSIAN', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SPARSE_GAUSSIAN', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CONSTANT', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DENSE_GAUSSIAN_SQRT_FAN_IN', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='PRETRAINED', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DENSE_UNIFORM', index=5, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DENSE_UNIFORM_SQRT_FAN_IN', index=6, number=6,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=1523,
  serialized_end=1692,
)

_HYPERPARAMS_DECAY = descriptor.EnumDescriptor(
  name='Decay',
  full_name='deepnet.Hyperparams.Decay',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='NONE', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='INVERSE_T', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='EXPONENTIAL', index=2, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3589,
  serialized_end=3638,
)

_HYPERPARAMS_ACTIVATION = descriptor.EnumDescriptor(
  name='Activation',
  full_name='deepnet.Hyperparams.Activation',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='LINEAR', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LOGISTIC', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TANH', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='RECTIFIED_LINEAR', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='RECTIFIED_LINEAR_SMOOTH', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SOFTMAX', index=5, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='REPLICATED_SOFTMAX', index=6, number=6,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SIN', index=7, number=7,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='COS', index=8, number=8,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3641,
  serialized_end=3795,
)

_HYPERPARAMS_ADAPT = descriptor.EnumDescriptor(
  name='Adapt',
  full_name='deepnet.Hyperparams.Adapt',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='NO_ADAPT', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ADAGRAD', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3797,
  serialized_end=3831,
)

_MODEL_MODELTYPE = descriptor.EnumDescriptor(
  name='ModelType',
  full_name='deepnet.Model.ModelType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='FEED_FORWARD_NET', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='RECURRENT_NET', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DBN', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DBM', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SPARSE_CODER', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='FAST_DROPOUT_NET', index=5, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=4785,
  serialized_end=4895,
)

_OPERATION_OPTIMIZER = descriptor.EnumDescriptor(
  name='Optimizer',
  full_name='deepnet.Operation.Optimizer',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='GRADIENT_DESCENT', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='LBFGS', index=1, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='CD', index=2, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='PCD', index=3, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=5449,
  serialized_end=5510,
)


_LAYER_DATAFIELD = descriptor.Descriptor(
  name='DataField',
  full_name='deepnet.Layer.DataField',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='train', full_name='deepnet.Layer.DataField.train', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='validation', full_name='deepnet.Layer.DataField.validation', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='test', full_name='deepnet.Layer.DataField.test', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='model', full_name='deepnet.Layer.DataField.model', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='layer_name', full_name='deepnet.Layer.DataField.layer_name', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied', full_name='deepnet.Layer.DataField.tied', index=5,
      number=6, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied_to', full_name='deepnet.Layer.DataField.tied_to', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
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
  serialized_start=555,
  serialized_end=688,
)

_LAYER = descriptor.Descriptor(
  name='Layer',
  full_name='deepnet.Layer',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='deepnet.Layer.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='file_pattern', full_name='deepnet.Layer.file_pattern', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='dimensions', full_name='deepnet.Layer.dimensions', index=2,
      number=3, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='numlabels', full_name='deepnet.Layer.numlabels', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='param', full_name='deepnet.Layer.param', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='is_input', full_name='deepnet.Layer.is_input', index=5,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='is_output', full_name='deepnet.Layer.is_output', index=6,
      number=8, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='loss_function', full_name='deepnet.Layer.loss_function', index=7,
      number=9, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hyperparams', full_name='deepnet.Layer.hyperparams', index=8,
      number=10, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data_field', full_name='deepnet.Layer.data_field', index=9,
      number=11, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='performance_stats', full_name='deepnet.Layer.performance_stats', index=10,
      number=12, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shape', full_name='deepnet.Layer.shape', index=11,
      number=13, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='is_initialized', full_name='deepnet.Layer.is_initialized', index=12,
      number=14, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='prefix', full_name='deepnet.Layer.prefix', index=13,
      number=15, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='replicate_bias', full_name='deepnet.Layer.replicate_bias', index=14,
      number=16, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=True,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied', full_name='deepnet.Layer.tied', index=15,
      number=17, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied_to', full_name='deepnet.Layer.tied_to', index=16,
      number=18, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='loss_weight', full_name='deepnet.Layer.loss_weight', index=17,
      number=19, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_LAYER_DATAFIELD, ],
  enum_types=[
    _LAYER_LOSSFUNCTION,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=27,
  serialized_end=757,
)


_PARAMETER_CONVOLUTION = descriptor.Descriptor(
  name='Convolution',
  full_name='deepnet.Parameter.Convolution',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='size', full_name='deepnet.Parameter.Convolution.size', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='stride', full_name='deepnet.Parameter.Convolution.stride', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='padding', full_name='deepnet.Parameter.Convolution.padding', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='num_filters', full_name='deepnet.Parameter.Convolution.num_filters', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='num_colors', full_name='deepnet.Parameter.Convolution.num_colors', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='max_pool', full_name='deepnet.Parameter.Convolution.max_pool', index=5,
      number=6, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pool_size', full_name='deepnet.Parameter.Convolution.pool_size', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pool_stride', full_name='deepnet.Parameter.Convolution.pool_stride', index=7,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='rnorm', full_name='deepnet.Parameter.Convolution.rnorm', index=8,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='norm_size', full_name='deepnet.Parameter.Convolution.norm_size', index=9,
      number=10, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pow_scale', full_name='deepnet.Parameter.Convolution.pow_scale', index=10,
      number=11, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.75,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='add_scale', full_name='deepnet.Parameter.Convolution.add_scale', index=11,
      number=12, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.001,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='prob', full_name='deepnet.Parameter.Convolution.prob', index=12,
      number=13, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
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
  serialized_start=1217,
  serialized_end=1520,
)

_PARAMETER = descriptor.Descriptor(
  name='Parameter',
  full_name='deepnet.Parameter',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='deepnet.Parameter.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mat', full_name='deepnet.Parameter.mat', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='dimensions', full_name='deepnet.Parameter.dimensions', index=2,
      number=3, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='initialization', full_name='deepnet.Parameter.initialization', index=3,
      number=4, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=2,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sigma', full_name='deepnet.Parameter.sigma', index=4,
      number=5, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.001,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='constant', full_name='deepnet.Parameter.constant', index=5,
      number=6, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='conv', full_name='deepnet.Parameter.conv', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='conv_params', full_name='deepnet.Parameter.conv_params', index=7,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pretrained_model', full_name='deepnet.Parameter.pretrained_model', index=8,
      number=9, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pretrained_model_node1', full_name='deepnet.Parameter.pretrained_model_node1', index=9,
      number=10, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pretrained_model_node2', full_name='deepnet.Parameter.pretrained_model_node2', index=10,
      number=11, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='transpose_pretrained', full_name='deepnet.Parameter.transpose_pretrained', index=11,
      number=12, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pretrained_model_param_name', full_name='deepnet.Parameter.pretrained_model_param_name', index=12,
      number=13, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='local', full_name='deepnet.Parameter.local', index=13,
      number=14, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mult_factor', full_name='deepnet.Parameter.mult_factor', index=14,
      number=15, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_PARAMETER_CONVOLUTION, ],
  enum_types=[
    _PARAMETER_INITIALIZATION,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=760,
  serialized_end=1692,
)


_HYPERPARAMS = descriptor.Descriptor(
  name='Hyperparams',
  full_name='deepnet.Hyperparams',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='base_epsilon', full_name='deepnet.Hyperparams.base_epsilon', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.01,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='epsilon_decay', full_name='deepnet.Hyperparams.epsilon_decay', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='epsilon_decay_half_life', full_name='deepnet.Hyperparams.epsilon_decay_half_life', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1000,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='initial_momentum', full_name='deepnet.Hyperparams.initial_momentum', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='final_momentum', full_name='deepnet.Hyperparams.final_momentum', index=4,
      number=5, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='momentum_change_steps', full_name='deepnet.Hyperparams.momentum_change_steps', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=10,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sparsity', full_name='deepnet.Hyperparams.sparsity', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sparsity_target', full_name='deepnet.Hyperparams.sparsity_target', index=7,
      number=8, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sparsity_cost', full_name='deepnet.Hyperparams.sparsity_cost', index=8,
      number=9, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.001,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sparsity_damping', full_name='deepnet.Hyperparams.sparsity_damping', index=9,
      number=10, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.9,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='dropout', full_name='deepnet.Hyperparams.dropout', index=10,
      number=11, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='dropout_prob', full_name='deepnet.Hyperparams.dropout_prob', index=11,
      number=12, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.5,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='apply_weight_norm', full_name='deepnet.Hyperparams.apply_weight_norm', index=12,
      number=13, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='weight_norm', full_name='deepnet.Hyperparams.weight_norm', index=13,
      number=14, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=10,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='apply_l2_decay', full_name='deepnet.Hyperparams.apply_l2_decay', index=14,
      number=15, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='l2_decay', full_name='deepnet.Hyperparams.l2_decay', index=15,
      number=16, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.01,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='activation', full_name='deepnet.Hyperparams.activation', index=16,
      number=17, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='left_window', full_name='deepnet.Hyperparams.left_window', index=17,
      number=18, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='right_window', full_name='deepnet.Hyperparams.right_window', index=18,
      number=19, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mf_steps', full_name='deepnet.Hyperparams.mf_steps', index=19,
      number=20, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='gibbs_steps', full_name='deepnet.Hyperparams.gibbs_steps', index=20,
      number=21, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='adapt', full_name='deepnet.Hyperparams.adapt', index=21,
      number=24, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='stop_dropout_for_last', full_name='deepnet.Hyperparams.stop_dropout_for_last', index=22,
      number=25, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='enable_display', full_name='deepnet.Hyperparams.enable_display', index=23,
      number=26, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='normalize', full_name='deepnet.Hyperparams.normalize', index=24,
      number=27, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='normalize_to', full_name='deepnet.Hyperparams.normalize_to', index=25,
      number=28, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='start_learning_after', full_name='deepnet.Hyperparams.start_learning_after', index=26,
      number=29, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='step_up_cd_after', full_name='deepnet.Hyperparams.step_up_cd_after', index=27,
      number=30, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='decay_learning_rate_for_last', full_name='deepnet.Hyperparams.decay_learning_rate_for_last', index=28,
      number=31, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='learn_precision', full_name='deepnet.Hyperparams.learn_precision', index=29,
      number=32, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='precision_epsilon', full_name='deepnet.Hyperparams.precision_epsilon', index=30,
      number=33, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='precision_upper_bound', full_name='deepnet.Hyperparams.precision_upper_bound', index=31,
      number=34, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='apply_l1_decay', full_name='deepnet.Hyperparams.apply_l1_decay', index=32,
      number=35, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='l1_decay', full_name='deepnet.Hyperparams.l1_decay', index=33,
      number=36, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.01,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='apply_l1decay_after', full_name='deepnet.Hyperparams.apply_l1decay_after', index=34,
      number=37, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='add_noise', full_name='deepnet.Hyperparams.add_noise', index=35,
      number=38, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shift', full_name='deepnet.Hyperparams.shift', index=36,
      number=39, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shift_amt_x', full_name='deepnet.Hyperparams.shift_amt_x', index=37,
      number=40, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='blocksize', full_name='deepnet.Hyperparams.blocksize', index=38,
      number=41, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shift_amt_y', full_name='deepnet.Hyperparams.shift_amt_y', index=39,
      number=42, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sc_alpha', full_name='deepnet.Hyperparams.sc_alpha', index=40,
      number=43, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sc_beta', full_name='deepnet.Hyperparams.sc_beta', index=41,
      number=44, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sc_gamma', full_name='deepnet.Hyperparams.sc_gamma', index=42,
      number=45, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sample_input', full_name='deepnet.Hyperparams.sample_input', index=43,
      number=46, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mult_dropout', full_name='deepnet.Hyperparams.mult_dropout', index=44,
      number=47, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='select_model_using_error', full_name='deepnet.Hyperparams.select_model_using_error', index=45,
      number=48, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sample_input_after', full_name='deepnet.Hyperparams.sample_input_after', index=46,
      number=49, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='additive_prior', full_name='deepnet.Hyperparams.additive_prior', index=47,
      number=50, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='multiplicative_prior', full_name='deepnet.Hyperparams.multiplicative_prior', index=48,
      number=51, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='adaptive_prior', full_name='deepnet.Hyperparams.adaptive_prior', index=49,
      number=52, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='normalize_error', full_name='deepnet.Hyperparams.normalize_error', index=50,
      number=53, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='start_step_up_cd_after', full_name='deepnet.Hyperparams.start_step_up_cd_after', index=51,
      number=54, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='select_model_using_acc', full_name='deepnet.Hyperparams.select_model_using_acc', index=52,
      number=55, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='select_model_using_map', full_name='deepnet.Hyperparams.select_model_using_map', index=53,
      number=56, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='fast_dropout', full_name='deepnet.Hyperparams.fast_dropout', index=54,
      number=57, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='fast_dropout_cost', full_name='deepnet.Hyperparams.fast_dropout_cost', index=55,
      number=58, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shared_prior', full_name='deepnet.Hyperparams.shared_prior', index=56,
      number=59, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shared_prior_file', full_name='deepnet.Hyperparams.shared_prior_file', index=57,
      number=60, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shared_prior_edge', full_name='deepnet.Hyperparams.shared_prior_edge', index=58,
      number=61, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='shared_prior_cost', full_name='deepnet.Hyperparams.shared_prior_cost', index=59,
      number=62, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='soft_shared_prior', full_name='deepnet.Hyperparams.soft_shared_prior', index=60,
      number=63, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='label_freq_file', full_name='deepnet.Hyperparams.label_freq_file', index=61,
      number=64, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _HYPERPARAMS_DECAY,
    _HYPERPARAMS_ACTIVATION,
    _HYPERPARAMS_ADAPT,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1695,
  serialized_end=3831,
)


_EDGE = descriptor.Descriptor(
  name='Edge',
  full_name='deepnet.Edge',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='node1', full_name='deepnet.Edge.node1', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='node2', full_name='deepnet.Edge.node2', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='directed', full_name='deepnet.Edge.directed', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=True,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='param', full_name='deepnet.Edge.param', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hyperparams', full_name='deepnet.Edge.hyperparams', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='receptive_field_width', full_name='deepnet.Edge.receptive_field_width', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='display_rows', full_name='deepnet.Edge.display_rows', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='display_cols', full_name='deepnet.Edge.display_cols', index=7,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='up_factor', full_name='deepnet.Edge.up_factor', index=8,
      number=9, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='down_factor', full_name='deepnet.Edge.down_factor', index=9,
      number=10, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='prefix', full_name='deepnet.Edge.prefix', index=10,
      number=11, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied', full_name='deepnet.Edge.tied', index=11,
      number=12, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied_to_node1', full_name='deepnet.Edge.tied_to_node1', index=12,
      number=13, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied_to_node2', full_name='deepnet.Edge.tied_to_node2', index=13,
      number=14, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tied_transpose', full_name='deepnet.Edge.tied_transpose', index=14,
      number=15, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='block_gradient', full_name='deepnet.Edge.block_gradient', index=15,
      number=16, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
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
  serialized_start=3834,
  serialized_end=4247,
)


_MODEL = descriptor.Descriptor(
  name='Model',
  full_name='deepnet.Model',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='deepnet.Model.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='model_type', full_name='deepnet.Model.model_type', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='layer', full_name='deepnet.Model.layer', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='edge', full_name='deepnet.Model.edge', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hyperparams', full_name='deepnet.Model.hyperparams', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='train_stats', full_name='deepnet.Model.train_stats', index=5,
      number=6, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='validation_stats', full_name='deepnet.Model.validation_stats', index=6,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='test_stats', full_name='deepnet.Model.test_stats', index=7,
      number=8, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='seed', full_name='deepnet.Model.seed', index=8,
      number=9, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='positive_phase_order', full_name='deepnet.Model.positive_phase_order', index=9,
      number=10, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='negative_phase_order', full_name='deepnet.Model.negative_phase_order', index=10,
      number=11, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='initializer_net', full_name='deepnet.Model.initializer_net', index=11,
      number=12, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='prefix', full_name='deepnet.Model.prefix', index=12,
      number=13, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='best_valid_stat', full_name='deepnet.Model.best_valid_stat', index=13,
      number=14, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='train_stat_es', full_name='deepnet.Model.train_stat_es', index=14,
      number=15, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='test_stat_es', full_name='deepnet.Model.test_stat_es', index=15,
      number=16, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _MODEL_MODELTYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4250,
  serialized_end=4895,
)


_OPERATION_STOPCONDITION = descriptor.Descriptor(
  name='StopCondition',
  full_name='deepnet.Operation.StopCondition',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='all_processed', full_name='deepnet.Operation.StopCondition.all_processed', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='steps', full_name='deepnet.Operation.StopCondition.steps', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
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
  serialized_start=5384,
  serialized_end=5447,
)

_OPERATION = descriptor.Descriptor(
  name='Operation',
  full_name='deepnet.Operation',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='optimizer', full_name='deepnet.Operation.optimizer', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='stopcondition', full_name='deepnet.Operation.stopcondition', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='train', full_name='deepnet.Operation.train', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='current_step', full_name='deepnet.Operation.current_step', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='batchsize', full_name='deepnet.Operation.batchsize', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data_proto', full_name='deepnet.Operation.data_proto', index=5,
      number=6, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='eval_after', full_name='deepnet.Operation.eval_after', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='checkpoint_after', full_name='deepnet.Operation.checkpoint_after', index=7,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='checkpoint_directory', full_name='deepnet.Operation.checkpoint_directory', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("/tmp/", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='skip_last_piece', full_name='deepnet.Operation.skip_last_piece', index=9,
      number=10, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=True,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='randomize', full_name='deepnet.Operation.randomize', index=10,
      number=14, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='show_after', full_name='deepnet.Operation.show_after', index=11,
      number=15, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='verbose', full_name='deepnet.Operation.verbose', index=12,
      number=16, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='get_last_piece', full_name='deepnet.Operation.get_last_piece', index=13,
      number=17, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data_proto_prefix', full_name='deepnet.Operation.data_proto_prefix', index=14,
      number=18, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='checkpoint_prefix', full_name='deepnet.Operation.checkpoint_prefix', index=15,
      number=19, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_OPERATION_STOPCONDITION, ],
  enum_types=[
    _OPERATION_OPTIMIZER,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4898,
  serialized_end=5510,
)


_METRICS = descriptor.Descriptor(
  name='Metrics',
  full_name='deepnet.Metrics',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='count', full_name='deepnet.Metrics.count', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='correct_preds', full_name='deepnet.Metrics.correct_preds', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compute_correct_preds', full_name='deepnet.Metrics.compute_correct_preds', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cross_entropy', full_name='deepnet.Metrics.cross_entropy', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compute_cross_entropy', full_name='deepnet.Metrics.compute_cross_entropy', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='error', full_name='deepnet.Metrics.error', index=5,
      number=6, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compute_error', full_name='deepnet.Metrics.compute_error', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='MAP', full_name='deepnet.Metrics.MAP', index=7,
      number=8, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compute_MAP', full_name='deepnet.Metrics.compute_MAP', index=8,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='prec50', full_name='deepnet.Metrics.prec50', index=9,
      number=10, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compute_prec50', full_name='deepnet.Metrics.compute_prec50', index=10,
      number=11, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='MAP_list', full_name='deepnet.Metrics.MAP_list', index=11,
      number=12, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='prec50_list', full_name='deepnet.Metrics.prec50_list', index=12,
      number=13, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sparsity', full_name='deepnet.Metrics.sparsity', index=13,
      number=14, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='compute_sparsity', full_name='deepnet.Metrics.compute_sparsity', index=14,
      number=15, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
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
  serialized_start=5513,
  serialized_end=5885,
)


_DATASET_DATA = descriptor.Descriptor(
  name='Data',
  full_name='deepnet.Dataset.Data',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='deepnet.Dataset.Data.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='file_pattern', full_name='deepnet.Dataset.Data.file_pattern', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='size', full_name='deepnet.Dataset.Data.size', index=2,
      number=3, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='dimensions', full_name='deepnet.Dataset.Data.dimensions', index=3,
      number=4, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='num_labels', full_name='deepnet.Dataset.Data.num_labels', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='key', full_name='deepnet.Dataset.Data.key', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='sparse', full_name='deepnet.Dataset.Data.sparse', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='seq', full_name='deepnet.Dataset.Data.seq', index=7,
      number=8, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='stats_file', full_name='deepnet.Dataset.Data.stats_file', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
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
  serialized_start=6049,
  serialized_end=6224,
)

_DATASET = descriptor.Descriptor(
  name='Dataset',
  full_name='deepnet.Dataset',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='deepnet.Dataset.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data', full_name='deepnet.Dataset.data', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='gpu_memory', full_name='deepnet.Dataset.gpu_memory', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("2G", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='main_memory', full_name='deepnet.Dataset.main_memory', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("4G", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data_handler', full_name='deepnet.Dataset.data_handler', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("deepnet", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='prefix', full_name='deepnet.Dataset.prefix', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_DATASET_DATA, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5888,
  serialized_end=6224,
)

_LAYER_DATAFIELD.containing_type = _LAYER;
_LAYER.fields_by_name['param'].message_type = _PARAMETER
_LAYER.fields_by_name['loss_function'].enum_type = _LAYER_LOSSFUNCTION
_LAYER.fields_by_name['hyperparams'].message_type = _HYPERPARAMS
_LAYER.fields_by_name['data_field'].message_type = _LAYER_DATAFIELD
_LAYER.fields_by_name['performance_stats'].message_type = _METRICS
_LAYER_LOSSFUNCTION.containing_type = _LAYER;
_PARAMETER_CONVOLUTION.containing_type = _PARAMETER;
_PARAMETER.fields_by_name['initialization'].enum_type = _PARAMETER_INITIALIZATION
_PARAMETER.fields_by_name['conv_params'].message_type = _PARAMETER_CONVOLUTION
_PARAMETER_INITIALIZATION.containing_type = _PARAMETER;
_HYPERPARAMS.fields_by_name['epsilon_decay'].enum_type = _HYPERPARAMS_DECAY
_HYPERPARAMS.fields_by_name['activation'].enum_type = _HYPERPARAMS_ACTIVATION
_HYPERPARAMS.fields_by_name['adapt'].enum_type = _HYPERPARAMS_ADAPT
_HYPERPARAMS_DECAY.containing_type = _HYPERPARAMS;
_HYPERPARAMS_ACTIVATION.containing_type = _HYPERPARAMS;
_HYPERPARAMS_ADAPT.containing_type = _HYPERPARAMS;
_EDGE.fields_by_name['param'].message_type = _PARAMETER
_EDGE.fields_by_name['hyperparams'].message_type = _HYPERPARAMS
_MODEL.fields_by_name['model_type'].enum_type = _MODEL_MODELTYPE
_MODEL.fields_by_name['layer'].message_type = _LAYER
_MODEL.fields_by_name['edge'].message_type = _EDGE
_MODEL.fields_by_name['hyperparams'].message_type = _HYPERPARAMS
_MODEL.fields_by_name['train_stats'].message_type = _METRICS
_MODEL.fields_by_name['validation_stats'].message_type = _METRICS
_MODEL.fields_by_name['test_stats'].message_type = _METRICS
_MODEL.fields_by_name['best_valid_stat'].message_type = _METRICS
_MODEL.fields_by_name['train_stat_es'].message_type = _METRICS
_MODEL.fields_by_name['test_stat_es'].message_type = _METRICS
_MODEL_MODELTYPE.containing_type = _MODEL;
_OPERATION_STOPCONDITION.containing_type = _OPERATION;
_OPERATION.fields_by_name['optimizer'].enum_type = _OPERATION_OPTIMIZER
_OPERATION.fields_by_name['stopcondition'].message_type = _OPERATION_STOPCONDITION
_OPERATION_OPTIMIZER.containing_type = _OPERATION;
_DATASET_DATA.containing_type = _DATASET;
_DATASET.fields_by_name['data'].message_type = _DATASET_DATA
DESCRIPTOR.message_types_by_name['Layer'] = _LAYER
DESCRIPTOR.message_types_by_name['Parameter'] = _PARAMETER
DESCRIPTOR.message_types_by_name['Hyperparams'] = _HYPERPARAMS
DESCRIPTOR.message_types_by_name['Edge'] = _EDGE
DESCRIPTOR.message_types_by_name['Model'] = _MODEL
DESCRIPTOR.message_types_by_name['Operation'] = _OPERATION
DESCRIPTOR.message_types_by_name['Metrics'] = _METRICS
DESCRIPTOR.message_types_by_name['Dataset'] = _DATASET

class Layer(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  
  class DataField(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _LAYER_DATAFIELD
    
    # @@protoc_insertion_point(class_scope:deepnet.Layer.DataField)
  DESCRIPTOR = _LAYER
  
  # @@protoc_insertion_point(class_scope:deepnet.Layer)

class Parameter(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  
  class Convolution(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _PARAMETER_CONVOLUTION
    
    # @@protoc_insertion_point(class_scope:deepnet.Parameter.Convolution)
  DESCRIPTOR = _PARAMETER
  
  # @@protoc_insertion_point(class_scope:deepnet.Parameter)

class Hyperparams(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _HYPERPARAMS
  
  # @@protoc_insertion_point(class_scope:deepnet.Hyperparams)

class Edge(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EDGE
  
  # @@protoc_insertion_point(class_scope:deepnet.Edge)

class Model(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MODEL
  
  # @@protoc_insertion_point(class_scope:deepnet.Model)

class Operation(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  
  class StopCondition(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _OPERATION_STOPCONDITION
    
    # @@protoc_insertion_point(class_scope:deepnet.Operation.StopCondition)
  DESCRIPTOR = _OPERATION
  
  # @@protoc_insertion_point(class_scope:deepnet.Operation)

class Metrics(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _METRICS
  
  # @@protoc_insertion_point(class_scope:deepnet.Metrics)

class Dataset(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  
  class Data(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _DATASET_DATA
    
    # @@protoc_insertion_point(class_scope:deepnet.Dataset.Data)
  DESCRIPTOR = _DATASET
  
  # @@protoc_insertion_point(class_scope:deepnet.Dataset)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = edge
"""Implements an edge connecting two layers of neurons."""
from parameter import *

class Edge(Parameter):
  def __init__(self, proto, node1, node2, t_op=None, tied_to=None):
    super(Edge, self).__init__()
    self.node1 = node1
    self.node2 = node2
    self.tied_to = tied_to
    if proto.tied:
      tied_to.num_shares += 1
      self.transpose = proto.tied_transpose
      proto.CopyFrom(tied_to.proto)
      proto.node1 = node1.name
      proto.node2 = node2.name
      if self.transpose:
        for param in proto.param:
          if param.dimensions:
            dims = list(reversed(param.dimensions))
            del param.dimensions[:]
            param.dimensions.extend(dims)
    self.proto = proto
    self.params = {}
    self.conv = False
    self.local = False
    self.t_op = t_op
    self.name = '%s:%s' % (self.node1.name, self.node2.name)
    self.prefix = proto.prefix
    self.hyperparams = None
    if proto.directed:
      node1.AddOutgoingEdge(self)
      node2.AddIncomingEdge(self)
    else:
      node1.AddOutgoingEdge(self)
      node1.AddIncomingEdge(self)
      node2.AddOutgoingEdge(self)
      node2.AddIncomingEdge(self)

    self.LoadParams(proto, t_op=t_op, tied_to=tied_to)
    self.marker = 0
    self.fig = visualize.GetFigId()
    self.fig_stats = visualize.GetFigId()
    if self.conv or self.local:
      self.conv_filter_fig = visualize.GetFigId()
    self.AllocateMemory()

  def Show(self):
    if not self.hyperparams.enable_display:
      return
    visualize.show_hist(self.params['weight'].asarray(), self.fig)
    """
    if self.node1.is_input:
      if self.conv or self.local:
        visualize.display_convw(self.params['weight'].asarray(),
                                self.proto.receptive_field_width,
                                self.proto.display_rows,
                                self.proto.display_cols, self.conv_filter_fig,
                                title=self.name)
        visualize.display_hidden(self.params['weight'].asarray(),
                                 self.fig,
                                 title=self.name)
      else:
        if len(self.node1.proto.shape) < 3:
          visualize.display_wsorted(self.params['weight'].asarray(),
                                    self.proto.receptive_field_width,
                                    self.proto.display_rows,
                                    self.proto.display_cols, self.fig,
                                    title=self.name)
          visualize.show_stats(self, self.fig_stats, self.name)
        else:
          visualize.display_convw(self.params['weight'].asarray().T,
                                  self.proto.receptive_field_width,
                                  self.proto.display_rows,
                                  self.proto.display_cols, self.fig,
                                  title=self.name)
    """

  def AllocateBatchsizeDependentMemory(self):
    for param in self.proto.param:
      if param.conv or param.local:
        self.AllocateMemoryForConvolutions(param, self.node1, self.node2)
 
  def AllocateMemory(self):
    if 'weight' in self.params:
      edge_shape = self.params['weight'].shape
      self.temp = cm.CUDAMatrix(np.zeros(edge_shape))
      self.gradient = cm.CUDAMatrix(np.zeros(edge_shape))
      self.gradient_history = cm.CUDAMatrix(np.zeros(edge_shape))
      t_op = self.t_op
      if t_op and (t_op.optimizer == deepnet_pb2.Operation.PCD or \
        t_op.optimizer == deepnet_pb2.Operation.CD):
        self.suff_stats = cm.CUDAMatrix(np.zeros(edge_shape))

  def AllocateMemoryForConvolutions(self, param, node1, node2):
    self.conv = param.conv
    self.local = param.local
    if self.conv:
      assert not self.local
    else:
      assert not self.conv
    self.conv_params = param.conv_params
    num_colors = self.conv_params.num_colors
    num_filters = self.conv_params.num_filters
    size = self.conv_params.size
    padding = self.conv_params.padding
    stride = self.conv_params.stride

    numdims, numimages = node1.state.shape
    assert numdims % num_colors == 0
    x = int(np.sqrt(numdims / num_colors))
    assert x**2 == numdims / num_colors
    n_locs = (x + 2 * padding - size) / stride + 1

    input_shape = node1.state.shape[::-1]
    output_shape = node2.state.shape[::-1]

    self.input_t = cm.empty(input_shape)
    self.input_t2 = cm.empty(input_shape)
    self.output_t = cm.empty(output_shape)
    self.output_t2 = cm.empty(output_shape)
    if param.conv_params.max_pool:
      pool_output_size = n_locs**2 * num_filters
      self.unpooled_layer = cm.empty((numimages, pool_output_size))
      pool_size = param.conv_params.pool_size
      pool_stride = param.conv_params.pool_stride
      n_pool_locs = (n_locs - pool_size) / pool_stride + 1
      assert output_shape[1] == n_pool_locs**2 * num_filters, (
        "%s expected %s outputs, got %s" % (
          self.name, n_pool_locs**2 * num_filters, output_shape[1]))
      if param.conv_params.prob:
        self.rnd = cm.empty(self.unpooled_layer.shape)
    else:
      assert output_shape[1] == n_locs**2 * num_filters, (
        "%s expected %s outputs, got %s" % (
          self.name, n_locs**2 * num_filters, output_shape[1]))
    if param.conv_params.rnorm:
      self.unrnormalized_layer = cm.empty(output_shape)
      self.denoms = cm.empty(output_shape)
      self.rnorm_temp1 = cm.empty(output_shape)
      self.rnorm_temp2 = cm.empty(output_shape)

    return n_locs

  def LoadParams(self, proto, **kwargs):
    """Load the parameters for this edge.

    Load the parameters if present in self.proto. Otherwise initialize them
    appropriately.
    """
    node1 = self.node1
    node2 = self.node2
    self.hyperparams = proto.hyperparams
    param_names = [param.name for param in proto.param]
    for param in proto.param:
      if param.conv or param.local:
        n_locs = self.AllocateMemoryForConvolutions(param, node1, node2)
      if not param.dimensions:
        if param.conv:
          cv = param.conv_params
          dims = [cv.num_filters, cv.size**2 * cv.num_colors]
        elif param.local:
          dims = [cv.num_filters, n_locs**2 * cv.size**2 * cv.num_colors]
        else:
          dims = [node1.numlabels * node1.dimensions,
                  node2.numlabels * node2.dimensions]
        param.dimensions.extend(dims)
    super(Edge, self).LoadParams(proto, **kwargs)

  def LoadPretrained(self, param):
    node1_name = param.pretrained_model_node1
    node2_name = param.pretrained_model_node2
    if node1_name == '':
      node1_name = self.proto.node1
    if node2_name == '':
      node2_name = self.proto.node2

    if param.transpose_pretrained:
      temp = node1_name
      node1_name = node2_name
      node2_name = temp
    mat = None
    for pretrained_model in param.pretrained_model:
      model_file = os.path.join(self.prefix, pretrained_model)
      ext = os.path.splitext(pretrained_model)[1]
      if ext == '.npz':
        npzfile = np.load(model_file)
        if param.name == 'bias':
          this_mat = np.nan_to_num(npzfile['mean'] / npzfile['std'])
        elif param.name == 'precision':
          this_mat = np.nan_to_num(1. / npzfile['std'])
      elif ext == '.npy':
        this_mat = np.load(model_file)
      else:
        model = util.ReadModel(model_file)
        try:
          edge = next(e for e in model.edge if e.node1 == node1_name and e.node2 == node2_name)
        except StopIteration as e:
          print 'No edge found between %s and %s in model %s.' % (node1_name, node2_name, model_file)
          raise e
        pretrained_param = next(p for p in edge.param if p.name == param.name)
        assert pretrained_param.mat != '',\
                'Pretrained param %s in edge %s:%s of model %s is empty!!' % (
                  pretrained_param.name, edge.node1, edge.node2, pretrained_model)
        if param.transpose_pretrained:
          assert param.dimensions == pretrained_param.dimensions[::-1],\
              'Param has shape %s but transposed pretrained param has shape %s' % (
                param.dimensions, reversed(pretrained_param.dimensions))
        else:
          assert param.dimensions == pretrained_param.dimensions,\
              'Param has shape %s but pretrained param has shape %s' % (
                param.dimensions, pretrained_param.dimensions)
        this_mat = param.mult_factor * util.ParameterAsNumpy(pretrained_param)
      if param.transpose_pretrained:
        this_mat = this_mat.T
      if mat is None:
        mat = this_mat
      else:
        mat += this_mat
    return mat / len(param.pretrained_model)


  def CollectSufficientStatistics(self, neg=False):
    logging.debug('Collecting suff stats %s', self.name)

    if self.node1.activation == deepnet_pb2.Hyperparams.REPLICATED_SOFTMAX:
      self.node1.state.div_by_row(self.node1.NN)
    if self.node2.activation == deepnet_pb2.Hyperparams.REPLICATED_SOFTMAX:
      self.node2.state.div_by_row(self.node2.NN)
    if not neg:
      h1 = self.node1.hyperparams
      h2 = self.node2.hyperparams
      if h1.sparsity:
        self.node1.state.add_col_mult(self.node1.sparsity_gradient, -1)
      if h2.sparsity:
        self.node2.state.add_col_mult(self.node2.sparsity_gradient, -1)
      cm.dot(self.node1.state, self.node2.state.T, target=self.suff_stats)
      if h1.sparsity:
        self.node1.state.add_col_vec(self.node1.sparsity_gradient)
      if h2.sparsity:
        self.node2.state.add_col_vec(self.node2.sparsity_gradient)
    else:
      self.suff_stats.add_dot(self.node1.state, self.node2.state.T, mult=-1.0)
    if self.node1.activation == deepnet_pb2.Hyperparams.REPLICATED_SOFTMAX:
      self.node1.state.mult_by_row(self.node1.NN)
    if self.node2.activation == deepnet_pb2.Hyperparams.REPLICATED_SOFTMAX:
      self.node2.state.mult_by_row(self.node2.NN)


########NEW FILE########
__FILENAME__ = collect_dbn_reps
"""Collects Multimodal-DBN representations.
This script combines representations created for all inputs, whether missing
text or not in one place to be used for classification/retrieval.
"""
import numpy as np
import sys
import os
from deepnet import deepnet_pb2
from deepnet import util
import glob
from deepnet import datahandler as dh
import pdb
from google.protobuf import text_format

def main():
  model_file = sys.argv[1]
  base_output_dir = sys.argv[2]
  rep_dir = sys.argv[3]
  prefix = sys.argv[4]
  gpu_mem = sys.argv[5]
  main_mem = sys.argv[6]
  model = util.ReadModel(model_file)
  data_pb = deepnet_pb2.Dataset()
  data_pb.name = model.name
  data_pb.gpu_memory = gpu_mem
  data_pb.main_memory = main_mem
  output_dir = os.path.join(base_output_dir, 'validation')
  if not os.path.isdir(output_dir):
    os.makedirs(output_dir)
  output_proto_file = os.path.join(base_output_dir, 'data.pbtxt')

  # IMAGE PATHWAY
  img_input_pbtxt = os.path.join(prefix, 'flickr.pbtxt')
  img_hidden1_pbtxt = os.path.join(rep_dir, 'image_rbm1_LAST', 'data.pbtxt')
  img_hidden2_pbtxt = os.path.join(rep_dir, 'image_rbm2_LAST', 'data.pbtxt')
 
  # TEXT PATHWAY
  text_input_pbtxt = os.path.join(prefix, 'flickr_nnz.pbtxt')
  text_hidden1_pbtxt = os.path.join(rep_dir, 'text_rbm1_LAST', 'data.pbtxt')
  text_hidden2_pbtxt = os.path.join(rep_dir, 'text_rbm2_LAST', 'data.pbtxt')
  text_pbtxt_z = os.path.join(rep_dir, 'generated_text', 'data.pbtxt')
  
  joint_pbtxt = os.path.join(rep_dir, 'joint_rbm_LAST', 'data.pbtxt')

  
  img_input_pb = util.ReadData(img_input_pbtxt)
  data = next(d for d in img_input_pb.data if d.name == 'image_labelled')
  data.file_pattern = os.path.join(img_input_pb.prefix, data.file_pattern)
  data.stats_file = os.path.join(img_input_pb.prefix, data.stats_file)
  data.name = 'image_input'
  data_pb.data.extend([data])

  img_hidden1_pb = util.ReadData(img_hidden1_pbtxt)
  data = next(d for d in img_hidden1_pb.data if d.name == 'image_hidden1_validation')
  data.file_pattern = os.path.join(img_hidden1_pb.prefix, data.file_pattern)
  data.name = 'image_hidden1'
  data_pb.data.extend([data])

  img_hidden2_pb = util.ReadData(img_hidden2_pbtxt)
  data = next(d for d in img_hidden2_pb.data if d.name == 'image_hidden2_validation')
  data.file_pattern = os.path.join(img_hidden2_pb.prefix, data.file_pattern)
  data.name = 'image_hidden2'
  data_pb.data.extend([data])
  
  indices_file = os.path.join(prefix, 'text', 'indices_labelled.npz')
  indices = np.load(indices_file)
  nnz_indices = indices['nnz_indices']
  z_indices = indices['z_indices']

  text_pb_z = util.ReadData(text_pbtxt_z)
  text_input_pb = util.ReadData(text_input_pbtxt)
  data_nnz = next(d for d in text_input_pb.data if d.name == 'text_labelled')
  data_z = next(d for d in text_pb_z.data if d.name == 'text_input_layer_validation')
  output_file = os.path.join(output_dir, 'text_input-00001-of-00001.npy')
  data = Merge(data_nnz, data_z, nnz_indices, z_indices, text_pb_z.prefix, text_input_pb.prefix, 'text_input', output_file)
  data_pb.data.extend([data])

  text_hidden1_pb = util.ReadData(text_hidden1_pbtxt)
  data_nnz = next(d for d in text_hidden1_pb.data if d.name == 'text_hidden1_validation')
  data_z = next(d for d in text_pb_z.data if d.name == 'text_hidden1_validation')
  output_file = os.path.join(output_dir, 'text_hidden1-00001-of-00001.npy')
  data = Merge(data_nnz, data_z, nnz_indices, z_indices, text_pb_z.prefix, text_hidden1_pb.prefix, 'text_hidden1', output_file)
  data_pb.data.extend([data])

  text_hidden2_pb = util.ReadData(text_hidden2_pbtxt)
  data_nnz = next(d for d in text_hidden2_pb.data if d.name == 'text_hidden2_validation')
  data_z = next(d for d in text_pb_z.data if d.name == 'text_hidden2_validation')
  output_file = os.path.join(output_dir, 'text_hidden2-00001-of-00001.npy')
  data = Merge(data_nnz, data_z, nnz_indices, z_indices, text_pb_z.prefix, text_hidden2_pb.prefix, 'text_hidden2', output_file)
  data_pb.data.extend([data])

  joint_pb = util.ReadData(joint_pbtxt)
  data_nnz = next(d for d in joint_pb.data if d.name == 'joint_hidden_validation')
  data_z = next(d for d in text_pb_z.data if d.name == 'joint_hidden_validation')
  output_file = os.path.join(output_dir, 'joint_hidden-00001-of-00001.npy')
  data = Merge(data_nnz, data_z, nnz_indices, z_indices, text_pb_z.prefix, joint_pb.prefix, 'joint_hidden', output_file)
  data_pb.data.extend([data])

  with open(output_proto_file, 'w') as f:
    text_format.PrintMessage(data_pb, f)

def Load(file_pattern):
  data = None
  for f in sorted(glob.glob(file_pattern)):
    ext = os.path.splitext(f)[1]
    if ext == '.npy':
      this_data = np.load(f)
    elif ext == '.npz':
      this_data = dh.Disk.LoadSparse(f).toarray()
    else:
      raise Exception('unknown data format.')
    if data is None:
      data = this_data
    else:
      data = np.concatenate((data, this_data))
  return data

def Merge(data_nnz, data_z, indices_nnz, indices_z, prefix_z, prefix_nnz, name, output_file):
  data_nnz = Load(os.path.join(prefix_nnz, data_nnz.file_pattern))
  data_z = Load(os.path.join(prefix_z, data_z.file_pattern))
  assert data_nnz.shape[1] == data_z.shape[1], 'Dimension mismatch.'
  size = data_nnz.shape[0] + data_z.shape[0]
  numdims = data_nnz.shape[1]
  data = np.zeros((size, numdims), dtype=np.float32)
  data[indices_nnz] = data_nnz
  data[indices_z] = data_z
  np.save(output_file, data)

  data = deepnet_pb2.Dataset.Data()
  data.name = name
  data.size = size
  data.dimensions.extend([numdims])
  data.file_pattern = output_file

  return data

if __name__ == '__main__':
  main()


########NEW FILE########
__FILENAME__ = create_results_table
"""Collects results from multiple runs and puts them into a nice table."""
import sys
import numpy as np
from deepnet import util
import os

def main():
  path = sys.argv[1]
  numsplits = int(sys.argv[2])
  output_file = sys.argv[3]

  layers = ['image_input', 'image_hidden1', 'image_hidden2', 'joint_hidden',
            'text_hidden2', 'text_hidden1', 'text_input']
  maps = {}
  precs = {}
  for i in range(1, numsplits+1):
    for layer in layers:
      mfile = os.path.join(path, 'split_%d' % i, '%s_classifier_BEST' % layer)
      model = util.ReadModel(mfile)
      MAP = model.test_stat_es.MAP
      prec50 = model.test_stat_es.prec50
      if layer not in maps:
        maps[layer] = []
      if layer not in precs:
        precs[layer] = []
      maps[layer].append(MAP)
      precs[layer].append(prec50)

  f = open(output_file, 'w')
  f.write('\\begin{tabular}{|l|c|c|} \\hline \n')
  f.write('Layer & MAP & Prec@50 \\\\ \\hline\n')
  for layer in layers:
    lmap = np.array(maps[layer])
    lprec = np.array(precs[layer])
    f.write('%s & %.3f $\\pm$ %.3f & %.3f $\\pm$ %.3f \\\\ \n' % (layer,
            lmap.mean(), lmap.std(), lprec.mean(), lprec.std()))
  f.write('\\hline\n')
  f.write('\\end{tabular}\n')
  f.close()

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = merge_dataset_pb
from deepnet import util
from deepnet import deepnet_pb2
import sys, os
from google.protobuf import text_format

proto1 = sys.argv[1]
proto2 = sys.argv[2]
output_pbtxt = sys.argv[3]

out_dir = '/'.join(output_pbtxt.split('/')[:-1])
if out_dir and not os.path.isdir(out_dir):
  os.makedirs(out_dir)
dataset1 = util.ReadData(proto1)
name1 = dataset1.name
dataset2 = util.ReadData(proto2)
name2 = dataset2.name

dataset1_prefix = dataset1.prefix
dataset2_prefix = dataset2.prefix
prefix = os.path.commonprefix([dataset1_prefix, dataset2_prefix])

if dataset1_prefix != dataset2_prefix:
  for dataset in [dataset1, dataset2]:
    _prefix = dataset.prefix[len(prefix):]
    for d in dataset.data:
      if d.file_pattern:
        d.file_pattern = os.path.join(_prefix, d.file_pattern)
      if d.stats_file:
        d.file_pattern = os.path.join(_prefix, d.stats_file)

dataset1.MergeFrom(dataset2)
dataset1.name = '%s_%s' % (name1, name2)
dataset1.prefix = prefix

with open(output_pbtxt, 'w') as f:
  text_format.PrintMessage(dataset1, f)

########NEW FILE########
__FILENAME__ = sample_text
"""Samples text conditioned on image."""
from deepnet import inference
from deepnet import trainer as tr
import sys


def SampleText(model_file, op_file, base_output_dir, data_proto, gpu_mem, main_mem):
  datasets = ['validation']
  layernames = ['joint_hidden', 'text_hidden2', 'text_hidden1', 'text_input_layer']
  layernames_to_unclamp = ['text_input_layer', 'text_hidden2']
  method = 'mf'  # 'gibbs'
  steps = 10

  inference.DoInference(model_file, op_file, base_output_dir, layernames,
                        layernames_to_unclamp, memory='1G', method=method,
                        steps=steps, datasets=datasets, gpu_mem=gpu_mem,
                        main_mem=main_mem, data_proto=data_proto)

def main():
  model_file = sys.argv[1]
  op_file = sys.argv[2]
  output_dir = sys.argv[3]
  data_proto = sys.argv[4]
  if len(sys.argv) > 5:
    gpu_mem = sys.argv[5]
  else:
    gpu_mem = '2G'
  if len(sys.argv) > 6:
    main_mem = sys.argv[6]
  else:
    main_mem = '30G'
  board = tr.LockGPU()
  SampleText(model_file, op_file, output_dir, data_proto, gpu_mem, main_mem)
  tr.FreeGPU(board)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = split_reps
import numpy as np
import glob, os, sys
from deepnet import deepnet_pb2
from deepnet import util
from google.protobuf import text_format 

def DumpDataSplit(data, output_dir, name, dataset_pb, stats_file):
  data_pb = dataset_pb.data.add()
  output_file_name = os.path.join(output_dir, name)
  np.save(output_file_name, data)
  data_pb.name = name
  data_pb.file_pattern = '%s.npy' % output_file_name
  data_pb.size = data.shape[0]
  if stats_file:
    data_pb.stats_file = stats_file
  data_pb.dimensions.append(data.shape[1])

def DumpLabelSplit(data, output_dir, name, dataset_pb):
  data_pb = dataset_pb.data.add()
  output_file_name = os.path.join(output_dir, name)
  np.save(output_file_name, data)
  data_pb.name = name
  data_pb.file_pattern = '%s.npy' % output_file_name
  data_pb.size = data.shape[0]
  data_pb.dimensions.append(data.shape[1])

def Load(file_pattern):
  data = None
  for f in sorted(glob.glob(file_pattern)):
    ext = os.path.splitext(f)[1]
    if ext == '.npy':
      this_data = np.load(f)
    elif ext == '.npz':
      this_data = dh.Disk.LoadSparse(f).toarray()
    else:
      raise Exception('unknown data format.')
    if data is None:
      data = this_data
    else:
      data = np.concatenate((data, this_data))
  return data

def MakeDict(data_pbtxt):
  data_pb = util.ReadData(data_pbtxt)
  rep_dict = {}
  stats_files = {}
  for data in data_pb.data:
    rep_dict[data.name] = Load(data.file_pattern)
    stats_files[data.name] = data.stats_file
  return rep_dict, stats_files

def main():
  data_pbtxt = sys.argv[1]
  output_dir = sys.argv[2]
  prefix = sys.argv[3]
  r = int(sys.argv[4])
  gpu_mem = sys.argv[5]
  main_mem = sys.argv[6]
  if not os.path.isdir(output_dir):
    os.makedirs(output_dir)

  rep_dict, stats_files = MakeDict(data_pbtxt)
  reps = rep_dict.keys()

  indices_file = os.path.join(prefix, 'splits', 'train_indices_%d.npy' % r)
  if os.path.exists(indices_file):
    train = np.load(indices_file)
    valid = np.load(os.path.join(prefix, 'splits', 'valid_indices_%d.npy' % r))
    test = np.load(os.path.join(prefix, 'splits', 'test_indices_%d.npy' % r))
  else:
    print 'Creating new split.'
    indices = np.arange(25000)
    np.random.shuffle(indices)
    train = indices[:10000]
    valid = indices[10000:15000]
    test = indices[15000:]
    np.save(os.path.join(prefix, 'splits', 'train_indices_%d.npy' % r), train)
    np.save(os.path.join(prefix, 'splits', 'valid_indices_%d.npy' % r), valid)
    np.save(os.path.join(prefix, 'splits', 'test_indices_%d.npy' % r), test)

    
  print 'Splitting data'
  dataset_pb = deepnet_pb2.Dataset()
  dataset_pb.name = 'flickr_split_%d' % r
  dataset_pb.gpu_memory = gpu_mem
  dataset_pb.main_memory = main_mem
  for rep in reps:
    data = rep_dict[rep]
    stats_file = stats_files[rep]
    DumpDataSplit(data[train], output_dir, 'train_%s' % rep, dataset_pb, stats_file)
    DumpDataSplit(data[valid], output_dir, 'valid_%s' % rep, dataset_pb, stats_file)
    DumpDataSplit(data[test], output_dir, 'test_%s' % rep, dataset_pb, stats_file)

  print 'Splitting labels'
  labels = np.load(os.path.join(prefix, 'labels.npy')).astype('float32')
  DumpLabelSplit(labels[train,], output_dir, 'train_labels', dataset_pb)
  DumpLabelSplit(labels[valid,], output_dir, 'valid_labels', dataset_pb)
  DumpLabelSplit(labels[test,], output_dir, 'test_labels', dataset_pb)

  #d = 'indices'
  #np.save(os.path.join(output_dir, 'train_%s.npy' % d), train)
  #np.save(os.path.join(output_dir, 'valid_%s.npy' % d), valid)
  #np.save(os.path.join(output_dir, 'test_%s.npy' % d), test)

  with open(os.path.join(output_dir, 'data.pbtxt'), 'w') as f:
    text_format.PrintMessage(dataset_pb, f)

  print 'Output written in directory %s' % output_dir

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = extract_dbn_representation
from neuralnet import *
from trainer import *
#from extract_rbm_representation import *
def ExtractRepresentations(model_file, train_op_file, layernames,
                           base_output_dir, memory = '100M'):
  model = util.ReadModel(model_file)
  op = ReadOperation(train_op_file)
  op.randomize = False
  net = CreateDeepnet(model, op, op)
  net.LoadModelOnGPU()
  net.SetUpData()

  data_pb = deepnet_pb2.Dataset()
  data_pb.name = model.name
  data_pb.gpu_memory = '5G'
  data_pb.main_memory =  '30G'
  output_proto_file = os.path.join(base_output_dir, 'data.pbtxt')
  for dataset in ['train', 'validation', 'test']:
    output_dir = os.path.join(base_output_dir, dataset)
    print 'Writing to %s' % output_dir
    size = net.WriteRepresentationToDisk(
      layernames, output_dir, memory=memory, dataset=dataset)
    if size is None:
      continue
    # Write protocol buffer.
    if dataset == 'train':
      tag = 'unlabelled'
    else:
      tag = 'labelled'
    for lname in layernames:
      layer = net.GetLayerByName(lname)
      data = data_pb.data.add()
      data.name = '%s_%s' % (lname, tag)
      data.file_pattern = os.path.join(output_dir, '*-of-*.npy')
      data.size = size
      data.dimensions.append(layer.state.shape[0])
  with open(output_proto_file, 'w') as f:
    text_format.PrintMessage(data_pb, f)

def main():
  LockGPU()
  prefix = '/ais/gobi3/u/nitish/flickr'
  model = util.ReadModel(sys.argv[1])
  train_op_file = sys.argv[2]
  layernames = ['joint_hidden', 'text_hidden2', 'text_hidden1', 'image_hidden2',
                'image_hidden1', 'image_input_layer', 'text_input_layer']
  if len(sys.argv) > 3:
    output_d = sys.argv[3]
  else:
    output_d = 'dbn_reps'
  output_dir = os.path.join(prefix, output_d, '%s_LAST' % model.name)
  #model_file = os.path.join(prefix, 'models', '%s_LAST' % model.name)
  model_file = sys.argv[1]
  ExtractRepresentations(model_file, train_op_file, layernames, output_dir, memory='1G')
  FreeGPU()


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = extract_neural_net_representation
"""Push the data through a network and get representations at each layer."""
from neuralnet import *
from trainer import *
import sys

def ExtractRepresentations(model_file, train_op_file, layernames,
                           base_output_dir, memory = '100M', skip_outputs=True,
                           datasets=['test'], gpu_mem='2G', main_mem='30G'):
  if isinstance(model_file, str):
    model = util.ReadModel(model_file)
  else:
    model = model_file
  if isinstance(train_op_file, str):
    op = ReadOperation(train_op_file)
  else:
    op = train_op_file
  if not os.path.isdir(base_output_dir):
    os.makedirs(base_output_dir)
  op.randomize = False
  op.get_last_piece = True
  net = CreateDeepnet(model, op, op)
  net.LoadModelOnGPU()
  net.SetUpData(skip_outputs=skip_outputs)

  data_pb = deepnet_pb2.Dataset()
  data_pb.name = model.name
  data_pb.gpu_memory = gpu_mem
  data_pb.main_memory =  main_mem
  output_proto_file = os.path.join(base_output_dir, 'data.pbtxt')
  for dataset in datasets:
    output_dir = os.path.join(base_output_dir, dataset)
    if not os.path.isdir(output_dir):
      os.makedirs(output_dir)
    print 'Writing to %s' % output_dir
    size = net.WriteRepresentationToDisk(
      layernames, output_dir, memory=memory, dataset=dataset)
    # Write protocol buffer.
    for i, lname in enumerate(layernames):
      if not size or size[i] == 0:
        continue
      layer = net.GetLayerByName(lname)
      data = data_pb.data.add()
      data.name = '%s_%s' % (lname, dataset)
      data.file_pattern = os.path.join(output_dir, '*-of-*.npy')
      data.size = size[i]
      data.dimensions.append(layer.state.shape[0])
  with open(output_proto_file, 'w') as f:
    text_format.PrintMessage(data_pb, f)

def Usage():
  print 'python %s <model_file> <train_op_file> <output_dir> <layer name1> [layer name2 [..]]' % sys.argv[0]

def main():
  if len(sys.argv) < 5:
    Usage()
    sys.exit(0)
  board = LockGPU()
  model_file = sys.argv[1]
  model = util.ReadModel(model_file)
  train_op_file = sys.argv[2]
  output_dir = sys.argv[3]
  layernames = sys.argv[4:]
  ExtractRepresentations(model_file, train_op_file, layernames, output_dir,
                         #memory='1G', datasets=['train', 'validation', 'test'])
                         memory='1G', datasets=['validation', 'test'])
  FreeGPU(board)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = extract_rbm_representation
from neuralnet import *
from trainer import *

def ExtractRepresentations(model_file, train_op_file, layernames,
                           base_output_dir, memory='10G',
                           datasets=['validation', 'test', 'train'],
                           gpu_mem='2G', main_mem='30G', data_proto=None):
  if isinstance(model_file, str):
    model = util.ReadModel(model_file)
  else:
    model = model_file
  if isinstance(train_op_file, str):
    op = ReadOperation(train_op_file)
  else:
    op = train_op_file
  if data_proto:
    op.data_proto = data_proto
  op.randomize = False
  op.verbose = False
  op.get_last_piece = True
  if not os.path.isdir(base_output_dir):
    os.makedirs(base_output_dir)

  net = CreateDeepnet(model, op, op)
  net.LoadModelOnGPU()
  net.SetUpData()

  data_pb = deepnet_pb2.Dataset()
  data_pb.name = model.name
  data_pb.gpu_memory = gpu_mem
  data_pb.main_memory = main_mem
  data_pb.prefix = base_output_dir
  output_proto_file = os.path.join(base_output_dir, 'data.pbtxt')
  for dataset in datasets:
    output_dir = os.path.join(base_output_dir, dataset)
    if not os.path.isdir(output_dir):
      os.makedirs(output_dir)
    print 'Writing to %s' % output_dir
    size = net.WriteRepresentationToDisk(
      layernames, output_dir, memory=memory, dataset=dataset, input_recon=True)
    # Write protocol buffer.
    tag = dataset
    if size is None:
      continue
    for i, lname in enumerate(layernames):
      layer = net.GetLayerByName(lname)
      data = data_pb.data.add()
      data.size = size[i]
      data.name = '%s_%s' % (lname, tag)
      data.file_pattern = os.path.join(dataset, '%s-*-of-*.npy' % lname)
      data.dimensions.append(layer.state.shape[0])
  with open(output_proto_file, 'w') as f:
    text_format.PrintMessage(data_pb, f)

def main():
  board = LockGPU()
  model_file = sys.argv[1]
  train_op_file = sys.argv[2]
  layernames = sys.argv[3].split()
  output_dir = sys.argv[4]
  datasets = ['validation', 'test', 'train']
  #datasets = ['validation', 'test']
  #datasets = ['test']
  gpu_mem = '2G'
  main_mem = '30G'
  data_proto = None
  if len(sys.argv) > 5:
    gpu_mem = sys.argv[5]
  if len(sys.argv) > 6:
    main_mem = sys.argv[6]
  if len(sys.argv) > 7:
    data_proto = sys.argv[7]

  ExtractRepresentations(model_file, train_op_file, layernames, output_dir,
                         datasets=datasets, gpu_mem=gpu_mem, main_mem=main_mem,
                         data_proto=data_proto)
  FreeGPU(board)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = fastdropoutnet
"""Implements a feed-forward neural net."""
from neuralnet import *
from layer import *

class FastDropoutNet(NeuralNet):

  def __init__(self, *args, **kwargs):
    super(FastDropoutNet, self).__init__(*args, **kwargs)
    self.SetUpLinks()

  def SetUpLinks(self):
    """Modifies self.net to create two parallel nets."""
    net1 = self.net
    net2 = CopyModel(net1)  # creates a copy of the net.
    for layer in net1.layer:
      if layer.hyperparams.fast_dropout:
        layer.is_output = True
      layer.name += '_1'
    for edge in net1.edge:
      edge.node1 += '_1'
      edge.node2 += '_1'
    for layer in net2.layer:
      layer.tied = True
      layer.tied_to = '%s_1' % layer.name
      if layer.hyperparams.fast_dropout:
        layer.is_output = True
      if layer.is_input or layer.is_output:
        layer.data_field.tied = True
        layer.data_field.tied_to = '%s_1' % layer.name
      layer.name += '_2'
    for edge in net2.edge:
      edge.tied = True
      edge.tied_to_node1 = '%s_1' % edge.node1
      edge.tied_to_node2 = '%s_1' % edge.node2
      edge.node1 += '_2'
      edge.node2 += '_2'
    self.net.MergeFrom(net2)

  def LoadModelOnGPU(self, *args, **kwargs):
    super(FastDropoutNet, self).LoadModelOnGPU(*args, **kwargs)
    for layer in self.layer:
      if layer.hyperparams.fast_dropout and layer.proto.tied:
        tied_to = next(l for l in self.layer if l.name == layer.proto.tied_to)
        layer.fast_dropout_partner = tied_to
        tied_to.fast_dropout_partner = layer

  def ComputeUp(self, layer, train=False, step=0, maxsteps=0):
    """
    Computes the state of `layer', given the state of its incoming neighbours.

    Args:
      layer: Layer whose state is to be computed.
      train: True if this computation is happening during training, False during
        evaluation.
      step: Training step.
      maxsteps: Maximum number of steps that will be taken (Needed because some
        hyperparameters may depend on this).
    """
    layer.dirty = False
    perf = None
    if layer.is_input or layer.is_initialized:
      layer.GetData()
    else:
      for i, edge in enumerate(layer.incoming_edge):
        if edge in layer.outgoing_edge:
          continue
        inputs = layer.incoming_neighbour[i].state
        if edge.conv or edge.local:
          if i == 0:
            ConvolveUp(inputs, edge, layer.state)
          else:
            AddConvoleUp(inputs, edge, layer.state)
        else:
          w = edge.params['weight']
          factor = edge.proto.up_factor
          if i == 0:
            cm.dot(w.T, inputs, target=layer.state)
            if factor != 1:
              layer.state.mult(factor)
          else:
            layer.state.add_dot(w.T, inputs, mult=factor)
      b = layer.params['bias']
      if layer.replicated_neighbour is None:
        layer.state.add_col_vec(b)
      else:
        layer.state.add_dot(b, layer.replicated_neighbour.NN)
      layer.ApplyActivation()
      if layer.hyperparams.sparsity:
        layer.state.sum(axis=1, target=layer.dimsize)
        perf = deepnet_pb2.Metrics()
        perf.MergeFrom(layer.proto.performance_stats)
        perf.count = layer.batchsize
        layer.dimsize.sum(axis=0, target=layer.unitcell)
        perf.sparsity = layer.unitcell.euclid_norm() / layer.dimsize.shape[0]
        layer.unitcell.greater_than(0)
        if layer.unitcell.euclid_norm() == 0:
          perf.sparsity *= -1

    if layer.hyperparams.fast_dropout:
      layer.data.assign(layer.state)

    if layer.hyperparams.dropout:
      if train and maxsteps - step >= layer.hyperparams.stop_dropout_for_last:
        # Randomly set states to zero.
        if layer.hyperparams.mult_dropout:
          layer.mask.fill_with_randn()
          layer.mask.add(1)
          layer.state.mult(layer.mask)
        else:
          layer.mask.fill_with_rand()
          layer.mask.greater_than(layer.hyperparams.dropout_prob)
          if layer.hyperparams.blocksize > 1:
            layer.mask.blockify(layer.hyperparams.blocksize)
          layer.state.mult(layer.mask)
      else:
        # Produce expected output.
        if layer.hyperparams.mult_dropout:
          pass
        else:
          layer.state.mult(1.0 - layer.hyperparams.dropout_prob)
    return perf

  def EvaluateOneBatch(self):
    """Evaluate one mini-batch."""
    losses = self.ForwardPropagate()
    losses.extend([node.GetLoss() for node in self.output_datalayer if '_1' in node.name])
    return losses

  def GetFastDropoutGradient(self, layer):
    perf = deepnet_pb2.Metrics()
    perf.MergeFrom(layer.proto.performance_stats)
    perf.count = layer.batchsize
    if layer.loss_function == deepnet_pb2.Layer.SQUARED_LOSS:
      target = layer.statesize
      layer.data.subtract(layer.fast_dropout_partner.data, target=target)
      error = target.euclid_norm()**2
      perf.error = error
      layer.deriv.add_mult(target, alpha=layer.loss_weight)
      layer.ComputeDeriv()
    else:
      raise Exception('Unknown loss function for ReLU units.')
    return perf

  def ComputeDown(self, layer, step):
    """Backpropagate through this layer.
    Args:
      step: The training step. Needed because some hyperparameters depend on
      which training step they are being used in.
    """
    if layer.is_input:  # Nobody to backprop to.
      return
    # At this point layer.deriv contains the derivative with respect to the
    # outputs of this layer. Compute derivative with respect to the inputs.
    h = layer.hyperparams
    loss = None
    if h.fast_dropout:
      if layer.hyperparams.sparsity:
        layer.AddSparsityGradient()
      loss = self.GetFastDropoutGradient(layer)
    else:
      if layer.is_output:
        loss = layer.GetLoss(get_deriv=True)
      else:
        if layer.hyperparams.sparsity:
          layer.AddSparsityGradient()
        layer.ComputeDeriv()
    # Now layer.deriv contains the derivative w.r.t to the inputs.
    # Send it down each incoming edge and update parameters on the edge.
    for edge in layer.incoming_edge:
      if edge.conv or edge.local:
        AccumulateConvDeriv(edge.node1, edge, layer.deriv)
      else:
        self.AccumulateDeriv(edge.node1, edge, layer.deriv)
      self.UpdateEdgeParams(edge, layer.deriv, step)
    # Update the parameters on this layer (i.e., the bias).
    self.UpdateLayerParams(layer, step)
    return loss

  def SetUpData(self, skip_outputs=False, skip_layernames=[]):
    """Setup the data."""
    hyp_list = []
    name_list = [[], [], []]
    for node in self.layer:
      if not (node.is_input or node.is_output):
        continue
      if skip_outputs and node.is_output:
        continue
      if node.name in skip_layernames:
        continue
      data_field = node.proto.data_field
      if node.hyperparams.fast_dropout:
        pass
        #self.fast_dropout_layers.append(node)
      elif data_field.tied:
        self.tied_datalayer.append(node)
        node.tied_to = next(l for l in self.datalayer\
                            if l.name == data_field.tied_to)
      else:
        self.datalayer.append(node)
        hyp_list.append(node.hyperparams)
        if data_field.train:
          name_list[0].append(data_field.train)
        if data_field.validation:
          name_list[1].append(data_field.validation)
        if data_field.test:
          name_list[2].append(data_field.test)
    if self.t_op:
      op = self.t_op
    else:
      op = self.e_op
    handles = GetDataHandles(op, name_list, hyp_list,
                             verbose=self.verbose)
    self.train_data_handler = handles[0]
    self.validation_data_handler = handles[1]
    self.test_data_handler = handles[2]



########NEW FILE########
__FILENAME__ = fast_dropout_layer
from layer import *
from logistic_layer import *
from linear_layer import *
from softmax_layer import *

class FastDropoutLayer(Layer):
  pass
class FastDropoutLogisticLayer(FastDropoutLayer, LogisticLayer):
  pass
class FastDropoutLinearLayer(FastDropoutLayer, LinearLayer):
  pass
class FastDropoutSoftmaxLayer(FastDropoutLayer, LinearLayer):
  pass

########NEW FILE########
__FILENAME__ = inference
"""Do inference in deepnet models."""
from neuralnet import *
from trainer import *

def DoInference(model_file, train_op_file, base_output_dir, layernames,
                layernames_to_unclamp, memory='1G', method='gibbs',
                steps=10, datasets=['validation', 'test'], gpu_mem='2G',
                main_mem='30G', data_proto=None):
  model = util.ReadModel(model_file)
  op = ReadOperation(train_op_file)
  op.randomize = False
  op.get_last_piece = True
  if data_proto:
    op.data_proto = data_proto
  net = CreateDeepnet(model, op, op)
  net.LoadModelOnGPU()
  net.SetUpData(skip_layernames=layernames_to_unclamp)

  data_pb = deepnet_pb2.Dataset()
  data_pb.name = model.name
  data_pb.gpu_memory = gpu_mem
  data_pb.main_memory =  main_mem
  output_proto_file = os.path.join(base_output_dir, 'data.pbtxt')
  for dataset in datasets:
    output_dir = os.path.join(base_output_dir, dataset)
    print 'Writing to %s' % output_dir
    size = net.Inference(steps, layernames, layernames_to_unclamp, output_dir,
                         memory=memory, dataset=dataset, method=method)
    if size is None:
      continue
    # Write protocol buffer.
    for lname in layernames:
      layer = net.GetLayerByName(lname)
      data = data_pb.data.add()
      data.name = '%s_%s' % (lname, dataset)
      data.file_pattern = os.path.join(output_dir, '%s-*-of-*.npy' % lname)
      data.size = size
      data.dimensions.append(layer.state.shape[0])
  with open(output_proto_file, 'w') as f:
    text_format.PrintMessage(data_pb, f)

def main():
  LockGPU()
  prefix = '/ais/gobi3/u/nitish/flickr'
  model = util.ReadModel(sys.argv[1])
  train_op_file = sys.argv[2]
  layernames = ['joint_hidden', 'text_hidden2', 'text_hidden1',
                'text_input_layer']
  layernames_to_unclamp = ['text_input_layer', 'text_hidden2']
  method = 'gibbs'
  steps = 10
  output_d = 'dbn_inference'

  output_dir = os.path.join(prefix, output_d, '%s_LAST' % model.name)
  model_file = sys.argv[1]
  DoInference(model_file, train_op_file, output_dir, layernames,
              layernames_to_unclamp, memory = '1G', method=method,
              steps=steps)
  FreeGPU()


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = layer
"""Implements a layer of neurons."""
from parameter import *
import matplotlib.pyplot as plt
plt.ion()
class Layer(Parameter):

  def __init__(self, proto, t_op=None, tied_to=None):
    super(Layer, self).__init__()
    self.tied_to = tied_to
    if proto.tied:
      tied_to.num_shares += 1
      proto = util.LoadMissing(proto, tied_to.proto)
    self.proto = proto
    self.state = None
    self.params = {}
    self.hyperparams = proto.hyperparams
    self.incoming_edge = []
    self.outgoing_edge = []
    self.outgoing_neighbour = []
    self.incoming_neighbour = []
    self.use_suff_stats = False
    self.fast_dropout_partner = None
    if t_op:
      self.batchsize = t_op.batchsize
      self.use_suff_stats = t_op.optimizer == deepnet_pb2.Operation.PCD \
          or t_op.optimizer == deepnet_pb2.Operation.CD
    else:
      self.batchsize = 0
    self.name = proto.name
    self.dimensions = proto.dimensions
    self.numlabels = proto.numlabels
    self.activation = proto.hyperparams.activation
    self.is_input = proto.is_input
    self.is_output = proto.is_output
    self.loss_function = proto.loss_function
    self.loss_weight = proto.loss_weight
    self.train_data_handler = None
    self.validation_data_handler = None
    self.test_data_handler = None
    self.tied_to = None
    self.data_tied_to = None
    self.data = None
    self.deriv = None
    self.prefix = proto.prefix
    self.marker = 0
    self.fig = visualize.GetFigId()
    self.tiny = 1e-10
    self.replicated_neighbour = None
    self.is_initialized = proto.is_initialized
    self.t_op = t_op
    self.learn_precision = False
    self.sample_input = self.hyperparams.sample_input
    self.LoadParams(proto, t_op=t_op, tied_to=tied_to)
    if self.batchsize > 0:
      self.AllocateMemory(self.batchsize)

  def LoadParams(self, proto, **kwargs):
    assert proto
    for param in proto.param:
      if not param.dimensions:
        param.dimensions.extend([proto.numlabels * proto.dimensions, 1])
      elif len(param.dimensions) == 1:
        param.dimensions.append(1)
    super(Layer, self).LoadParams(proto, **kwargs)

  def LoadPretrained(self, param):
    node_name = param.pretrained_model_node1
    if node_name == '':
      node_name = self.proto.name
    mat = None
    for pretrained_model in param.pretrained_model:
      model_file = os.path.join(self.prefix, pretrained_model)
      ext = os.path.splitext(pretrained_model)[1]
      if ext == '.npz':
        npzfile = np.load(model_file)
        if param.name == 'bias':
          this_mat = np.nan_to_num(npzfile['mean'] / npzfile['std'])
        elif param.name == 'precision':
          this_mat = np.nan_to_num(1. / npzfile['std'])
      elif ext == '.npy':
        this_mat = np.load(model_file)
      else:
        model = util.ReadModel(model_file)
        # Find the relevant node in the model.
        node = next(n for n in model.layer if n.name == node_name)
        # Find the relevant parameter in the node.
        pretrained_param = next(p for p in node.param if p.name == param.name)
        assert pretrained_param.mat != '',\
                'Pretrained param %s in layer %s of model %s is empty!!' % (
                  pretrained_param.name, node.name, pretrained_model)
        this_mat = util.ParameterAsNumpy(pretrained_param)
      if len(this_mat.shape) == 1:
        this_mat = this_mat.reshape(-1, 1)
      if mat is None:
        mat = this_mat
      else:
        mat += this_mat
    return mat / len(param.pretrained_model)

  def SetData(self, data):
    self.data = data

  def AddIncomingEdge(self, edge):
    if edge not in self.incoming_edge:
      self.incoming_edge.append(edge)
      if self == edge.node1:
        neighbour = edge.node2
      else:
        neighbour = edge.node1
      self.incoming_neighbour.append(neighbour)
      if neighbour.proto.replicate_bias and neighbour.activation == deepnet_pb2.Hyperparams.REPLICATED_SOFTMAX:
        self.replicated_neighbour = neighbour

  def AddOutgoingEdge(self, edge):
    if edge not in self.outgoing_edge:
      self.outgoing_edge.append(edge)
      if self == edge.node1:
        self.outgoing_neighbour.append(edge.node2)
      else:
        self.outgoing_neighbour.append(edge.node1)

  def PrintNeighbours(self):
    for n in self.incoming_neighbour:
      print "Incoming edge from %s" % n.name
    for n in self.outgoing_neighbour:
      print "Outgoing edge to %s" % n.name

  def ResetState(self, rand=False):
    if rand:
      self.state.fill_with_randn()
      self.ApplyActivation()
    else:
      self.state.assign(0)

  def GetData(self):
    self.state.assign(self.data)

  def GetSparsityGradient(self):
    h = self.hyperparams
    damping = h.sparsity_damping
    target = h.sparsity_target
    cost = h.sparsity_cost

    # Update \hat{\rho}.
    self.means.mult(damping)
    self.means.add_sums(self.state, axis=1, mult=(1-damping)/self.batchsize)
    
    # Compute gradient.
    self.means.subtract(target, target=self.sparsity_gradient)
    div = self.GetSparsityDivisor()
    self.sparsity_gradient.divide(div)
    self.sparsity_gradient.mult(cost)

    # Return gradient.
    return self.sparsity_gradient

  def AllocateMemory(self, batchsize):
    self.AllocateBatchsizeDependentMemory(batchsize)
    dimensions = self.dimensions
    numlabels = self.numlabels
    numdims = dimensions * numlabels
    self.dimsize = cm.CUDAMatrix(np.zeros((numdims, 1)))
    if self.hyperparams.sparsity:
      tgt = self.hyperparams.sparsity_target
      self.means = cm.CUDAMatrix(tgt + np.zeros((numdims, 1)))
      self.sparsity_gradient = cm.CUDAMatrix(np.zeros((numdims, 1)))
      self.means_temp2 = cm.CUDAMatrix(np.zeros((numdims, 1)))
    self.gradient = cm.CUDAMatrix(np.zeros((numdims, 1)))
    self.gradient_history = cm.CUDAMatrix(np.zeros((numdims, 1)))

  def AllocateBatchsizeDependentMemory(self, batchsize):
    if self.data:
      self.data.free_device_memory()
    if self.deriv:
      self.deriv.free_device_memory()
    self.batchsize = batchsize
    dimensions = self.dimensions
    numlabels = self.numlabels
    numdims = dimensions * numlabels
    self.statesize = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
    self.batchsize_temp = cm.CUDAMatrix(np.zeros((1, batchsize)))
    self.state = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
    self.deriv = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
    if self.t_op:
      if self.t_op.optimizer == deepnet_pb2.Operation.PCD:
        self.pos_state = self.state
        self.pos_sample = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
        self.neg_state = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
        self.neg_sample = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
        self.sample = self.pos_sample
        self.suff_stats = cm.empty((numdims, 1))
      elif self.t_op.optimizer == deepnet_pb2.Operation.CD:
        self.sample = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
        self.suff_stats = cm.empty((numdims, 1))
    else:
        self.state = cm.CUDAMatrix(np.zeros((numdims, batchsize)))
    if self.is_input or self.is_initialized or self.is_output:
      self.data = cm.CUDAMatrix(np.zeros((dimensions, batchsize)))
    if self.hyperparams.dropout:
      self.mask = cm.CUDAMatrix(np.zeros(self.state.shape))

  def CollectSufficientStatistics(self, neg=False):
    """Collect sufficient statistics for this layer."""
    h = self.hyperparams
    if not neg:
      self.state.sum(axis=1, target=self.suff_stats)
      if h.sparsity:
        sparsity_gradient = self.GetSparsityGradient()
        self.suff_stats.add_mult(sparsity_gradient, -self.batchsize)
    else:
      self.suff_stats.add_sums(self.state, axis=1, mult=-1.0)
    if not neg and h.sparsity:
      return self.means.sum()/self.means.shape[0]

  def Show(self, train=False):
    """Displays useful statistics about the model."""
    if not self.proto.hyperparams.enable_display:
      return
    f = 1
    if self.hyperparams.dropout and not train:
      f = 1 / (1 - self.hyperparams.dropout_prob)
    if self.is_input:
      visualize.display_hidden(self.data.asarray(), self.fig, title=self.name)
      #visualize.display_w(self.neg_sample.asarray(), 28, 10, self.state.shape[1]/10, self.fig, title=self.name, vmax=1, vmin=0)
      #visualize.show_hist(self.params['bias'].asarray(), self.fig)
    else:
      visualize.display_hidden(f*self.state.asarray(), self.fig, title=self.name)
      #visualize.show_hist(self.params['bias'].asarray(), self.fig)
      """
      plt.figure(self.fig)
      plt.clf()
      plt.subplot(1, 3, 1)
      plt.title('pos_probabilities')
      plt.imshow(self.pos_state.asarray(), cmap = plt.cm.gray, interpolation = 'nearest', vmax=1, vmin=0)
      plt.subplot(1, 3, 2)
      plt.title('neg_probabilities')
      plt.imshow(self.neg_state.asarray(), cmap = plt.cm.gray, interpolation = 'nearest', vmax=1, vmin=0)
      plt.subplot(1, 3, 3)
      plt.title('neg_samples')
      plt.imshow(self.neg_sample.asarray(), cmap = plt.cm.gray, interpolation = 'nearest', vmax=1, vmin=0)
      plt.suptitle(self.name)
      plt.draw()
      """
      #visualize.display_w(self.neg_sample.asarray(), 1, 1, self.state.shape[1], self.fig, title=self.name)

def display_w(w, s, r, c, fig, vmax=None, vmin=None, dataset='mnist', title='weights'):

  def ComputeDeriv(self):
    pass
  def GetLoss(self, get_deriv=False):
    pass
  def Sample(self):
    pass
  def ApplyActivation(self):
    pass
  def GetSparsityDivisor(self):
    self.means_temp2.assign(1)
    return self.means_temp2

########NEW FILE########
__FILENAME__ = linear_layer
from layer import *

class LinearLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(LinearLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.LINEAR

  def ApplyActivation(self):
    pass

  def Sample(self):
    sample = self.sample
    state = self.state
    #sample.assign(state)
    #state.sample_gaussian(target=sample, mult=0.01)
    if self.learn_precision:
      sample.fill_with_randn()
      sample.div_by_col(self.params['precision'])
      sample.add(state)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    if self.hyperparams.dropout:
      self.deriv.mult(self.mask)

  def GetData(self):
    self.state.assign(self.data)
    if 'precision' in self.params:
      self.state.mult_by_col(self.params['precision'])

  def GetLoss(self, get_deriv=False, **kwargs):
    """Compute loss and also deriv w.r.t to it if asked for.

    Compute the loss function. Targets should be in self.data, predictions
    should be in self.state.
    Args:
      get_deriv: If True, compute the derivative w.r.t the loss function and put
        it in self.deriv.
    """
    perf = deepnet_pb2.Metrics()
    perf.MergeFrom(self.proto.performance_stats)
    perf.count = self.batchsize
    tiny = self.tiny
    if self.loss_function == deepnet_pb2.Layer.SQUARED_LOSS:
      if get_deriv:
        target = self.deriv
      else:
        target = self.statesize
      if 'precision' in self.params:
        self.data.mult_by_col(self.params['precision'], target=target)
        target.subtract(self.state)
      else:
        self.state.subtract(self.data, target=target)
      error = target.euclid_norm()**2
      perf.error = error
      if get_deriv:
        self.ComputeDeriv()
    elif self.loss_function == deepnet_pb2.Layer.HINGE_LOSS:
      pass
    else:
      raise Exception('Unknown loss function for linear units.')
    return perf

  def GetSparsityDivisor(self):
    self.means_temp2.assign(1)


########NEW FILE########
__FILENAME__ = logistic_layer
from layer import *

class LogisticLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(LogisticLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.LOGISTIC

  def ApplyActivation(self):
    cm.sigmoid(self.state)

  def Sample(self):
    self.state.sample_bernoulli(target=self.sample)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    self.deriv.apply_logistic_deriv(self.state)

  def GetLoss(self, get_deriv=False, acc_deriv=False, **kwargs):
    """Compute loss and also deriv w.r.t to it if asked for.

    Compute the loss function. Targets should be in self.data, predictions
    should be in self.state.
    Args:
      get_deriv: If True, compute the derivative w.r.t the loss function and put
        it in self.deriv.
    """
    perf = deepnet_pb2.Metrics()
    perf.MergeFrom(self.proto.performance_stats)
    perf.count = self.batchsize
    tiny = self.tiny
    if self.loss_function == deepnet_pb2.Layer.CROSS_ENTROPY:
      data = self.data
      state = self.state
      temp1 = self.statesize

      cm.cross_entropy_bernoulli(data, state, target=temp1, tiny=self.tiny)
      perf.cross_entropy = temp1.sum()
   
      cm.correct_preds(data, state, target=temp1, cutoff=0.5)
      perf.correct_preds = temp1.sum()

      if get_deriv:
        self.state.subtract(self.data, target=self.deriv)

    elif self.loss_function == deepnet_pb2.Layer.SQUARED_LOSS:
      target = self.statesize
      self.state.subtract(self.data, target=target)
      error = target.euclid_norm()**2
      perf.error = error
      if acc_deriv:
        self.deriv.add_mult(target, alpha=self.loss_weight)
      else:
        self.deriv.assign(target)
      if get_deriv:
        self.ComputeDeriv()
    else:
      raise Exception('Unknown loss function for logistic units.')

    return perf

  def GetSparsityDivisor(self):
    self.means_temp2.assign(1)
    self.means_temp2.subtract(self.means)
    self.means_temp2.mult(self.means)
    return self.means_temp2
  

########NEW FILE########
__FILENAME__ = make_plots
from deepnet import deepnet_pb2
import matplotlib.pyplot as plt
import glob, sys, gzip, numpy as np

def preds(metrics_list):
  y = []
  for metric in metrics_list:
    count = metric.count
    y.append( 100*(1- metric.correct_preds/metric.count))
  return y


def get_plot(v, skip, label):
  y = v[skip:]
  x = np.arange(skip, len(v))
  return plt.plot(x, y, label=label)


if __name__ == '__main__':
  plt.ion()
  proto = sys.argv[1]
  proto = glob.glob(proto + "*")[-1]
  print proto
  skip = 0
  if len(sys.argv) > 2:
    skip = int(sys.argv[2])
  model_pb = deepnet_pb2.Model()
  f = gzip.open(proto, 'rb')
  model_pb.ParseFromString(f.read())
  f.close()
  train = preds(model_pb.train_stats)
  valid = preds(model_pb.validation_stats)
  test = preds(model_pb.test_stats)
  x = np.arange(len(train))
  plt.figure(1)
  p1 = get_plot(train, skip, 'train')
  p2 = get_plot(valid, skip, 'valid')
  p3 = get_plot(test, skip, 'test')
  plt.legend()
  plt.xlabel('Iterations / 2000')
  plt.ylabel('Error %')
  plt.draw()
  raw_input('Press any key')

########NEW FILE########
__FILENAME__ = mc_avg
"""Monte Carlo model averaging for dropout networks."""
from neuralnet import *
from trainer import *
import glob
import sys
import random

def ExtractRepresentations(model_file, train_op_file, layernames,
                           base_output_dir, memory = '100M', k=10):
  LockGPU()
  model = util.ReadModel(model_file)
  op = ReadOperation(train_op_file)
  op.randomize = False
  net = CreateDeepnet(model, op, op)
  net.LoadModelOnGPU()
  net.SetUpData()
  for i in range(k):
    output_dir = os.path.join(base_output_dir, 'sample_%.5d' % i) 
    sys.stdout.write('\r Sample %d' % (i+1))
    sys.stdout.flush()
    net.WriteRepresentationToDisk(layernames, output_dir, memory=memory, drop=True)
  sys.stdout.write('\n')
  FreeGPU()


def GetAverageResult(truth_file, pred_dir, total, k, avg_over=10):
  sample_ids = range(total)
  x = []
  pred_dict = {}
  truth = np.load(truth_file)
  for t in range(avg_over):
    avg_pred = None
    for j in range(k):
      i = random.choice(sample_ids)
      prediction_file = glob.glob(os.path.join(pred_dir, 'sample_%.5d' % i, '*.npy'))[0]
      predictions = pred_dict.get(i, np.load(prediction_file))
      pred_dict[i] = predictions 
      if avg_pred is None:
        avg_pred = predictions
      else:
        avg_pred += predictions
    avg_pred /= k
    pred = avg_pred.argmax(axis=1)
    error = len((pred - truth).nonzero()[0])
    x.append((100. * error) / len(truth))
  x = np.array(x)
  return x.mean(), x.std()

def main():
  model_file = sys.argv[1]
  model = util.ReadModel(model_file)
  train_op_file = sys.argv[2]
  output_dir = sys.argv[3]
  layernames = ['output_layer']
  total = 1000
  k = 200
  avg_over = 100

  true_label_file = '/ais/gobi3/u/nitish/mnist/test_labels.npy'
  plot_data_file = '/ais/gobi3/u/nitish/mnist/results/mc_avg.npy'
  #ExtractRepresentations(model_file, train_op_file, layernames, output_dir, memory='1G', k=total)
  out = np.zeros((k, 3))
  for l in range(1, k+1):
    mean, std = GetAverageResult(true_label_file, output_dir, total, l, avg_over=avg_over)
    print '%d %.4f %.4f' % (l, mean, std)
    out[l-1, 0] = l
    out[l-1, 1] = mean
    out[l-1, 2] = std
  np.save(plot_data_file, out)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = neuralnet
"""Implements a feed-forward neural net."""
import gzip
import logging
import sys
import time
from google.protobuf import text_format

from datahandler import *
from convolutions import *
from edge import *
from layer import *
from util import *
from logistic_layer import *
from tanh_layer import *
from relu_layer import *
from smooth_relu_layer import *
from linear_layer import *
from softmax_layer import *
from replicated_softmax_layer import *
from cos_layer import *
from sin_layer import *
from transfer_edge import *
from soft_transfer_edge import *

class NeuralNet(object):

  def __init__(self, net, t_op=None, e_op=None):
    self.net = None
    if isinstance(net, deepnet_pb2.Model):
      self.net = net
    elif isinstance(net, str) or isinstance(net, unicode):
      self.net = ReadModel(net)
    self.t_op = None
    if isinstance(t_op, deepnet_pb2.Operation):
      self.t_op = t_op
    elif isinstance(t_op, str) or isinstance(net, unicode):
      self.t_op = ReadOperation(t_op)
    self.e_op = None
    if isinstance(e_op, deepnet_pb2.Operation):
      self.e_op = e_op
    elif isinstance(e_op, str) or isinstance(net, unicode):
      self.e_op = ReadOperation(e_op)
    cm.CUDAMatrix.init_random(self.net.seed)
    np.random.seed(self.net.seed)
    self.data = None
    self.layer = []
    self.edge = []
    self.input_datalayer = []
    self.output_datalayer = []
    self.datalayer = []
    self.tied_datalayer = []
    self.unclamped_layer = []
    self.verbose = False
    self.batchsize = 0
    if self.t_op:
      self.verbose = self.t_op.verbose
      self.batchsize = self.t_op.batchsize
    elif self.e_op:
      self.verbose = self.e_op.verbose
      self.batchsize = self.e_op.batchsize
    self.train_stop_steps = sys.maxint

  def PrintNetwork(self):
    for layer in self.layer:
      print layer.name
      layer.PrintNeighbours()

  def DeepCopy(self):
    return CopyModel(self.net)

  def LoadModelOnGPU(self, batchsize=-1):
    """Load the model on the GPU."""
    if batchsize < 0:
      if self.t_op:
        batchsize=self.t_op.batchsize
      else:
        batchsize=self.e_op.batchsize

    for layer in self.net.layer:
      layer.hyperparams.MergeFrom(LoadMissing(layer.hyperparams,
                                              self.net.hyperparams))
      if not layer.prefix:
        layer.prefix = self.net.prefix
      tied_to = None
      if layer.tied:
        tied_to = next(l for l in self.layer if l.name == layer.tied_to)
      self.layer.append(CreateLayer(Layer, layer, self.t_op, tied_to=tied_to))

    for edge in self.net.edge:
      hyp = deepnet_pb2.Hyperparams()
      hyp.CopyFrom(self.net.hyperparams)
      hyp.MergeFrom(edge.hyperparams)
      edge.hyperparams.MergeFrom(hyp)
      try:
        node1 = next(layer for layer in self.layer if layer.name == edge.node1)
      except StopIteration:
        print edge.node1, [l.name for l in self.layer]
      node2 = next(layer for layer in self.layer if layer.name == edge.node2)
      if not edge.prefix:
        edge.prefix = self.net.prefix
      tied_to = None
      if edge.tied:
        tied_to = next(e for e in self.edge if e.node1.name == edge.tied_to_node1 and e.node2.name == edge.tied_to_node2)
      self.edge.append(CreateEdge(Edge, edge, node1, node2, self.t_op, tied_to=tied_to))

    self.input_datalayer = [node for node in self.layer if node.is_input]
    self.output_datalayer = [node for node in self.layer if node.is_output]
    self.node_list = self.Sort()

  def ExchangeGlobalInfo(self):
    for layer in self.layer:
      layer.GetGlobalInfo(self)
    for edge in self.edge:
      edge.GetGlobalInfo(self)

  def Sort(self):
    """Topological sort."""
    node_list = []
    S = [node for node in self.layer if not node.incoming_neighbour]
    while S:
      n = S.pop()
      node_list.append(n)
      for m in n.outgoing_edge:
        if m.marker == 0:
          m.marker = 1
          if reduce(lambda a, edge: a and edge.marker == 1,
                    m.node2.incoming_edge, True):
            S.append(m.node2)
    if reduce(lambda a, edge: a and edge.marker == 1, self.edge, True):
      if self.verbose:
        print 'Fprop Order:'
        for node in node_list:
          print node.name
    else:
      raise Exception('Invalid net for backprop. Cycle exists.')
    return node_list

  def ComputeUp(self, layer, train=False, step=0, maxsteps=0):
    """
    Computes the state of `layer', given the state of its incoming neighbours.

    Args:
      layer: Layer whose state is to be computed.
      train: True if this computation is happening during training, False during
        evaluation.
      step: Training step.
      maxsteps: Maximum number of steps that will be taken (Needed because some
        hyperparameters may depend on this).
    """
    layer.dirty = False
    perf = None
    if layer.is_input or layer.is_initialized:
      layer.GetData()
    else:
      for i, edge in enumerate(layer.incoming_edge):
        if edge in layer.outgoing_edge:
          continue
        inputs = layer.incoming_neighbour[i].state
        if edge.conv or edge.local:
          if i == 0:
            ConvolveUp(inputs, edge, layer.state)
          else:
            AddConvoleUp(inputs, edge, layer.state)
        else:
          w = edge.params['weight']
          factor = edge.proto.up_factor
          if i == 0:
            cm.dot(w.T, inputs, target=layer.state)
            if factor != 1:
              layer.state.mult(factor)
          else:
            layer.state.add_dot(w.T, inputs, mult=factor)
      b = layer.params['bias']
      if layer.replicated_neighbour is None:
        layer.state.add_col_vec(b)
      else:
        layer.state.add_dot(b, layer.replicated_neighbour.NN)
      layer.ApplyActivation()
      if layer.hyperparams.sparsity:
        layer.state.sum(axis=1, target=layer.dimsize)
        perf = deepnet_pb2.Metrics()
        perf.MergeFrom(layer.proto.performance_stats)
        perf.count = layer.batchsize
        perf.sparsity = layer.dimsize.sum() / layer.dimsize.shape[0]

    if layer.hyperparams.dropout:
      if train and maxsteps - step >= layer.hyperparams.stop_dropout_for_last:
        # Randomly set states to zero.
        if layer.hyperparams.mult_dropout:
          layer.mask.fill_with_randn()
          layer.mask.add(1)
          layer.state.mult(layer.mask)
        else:
          layer.mask.fill_with_rand()
          layer.mask.greater_than(layer.hyperparams.dropout_prob)
          if layer.hyperparams.blocksize > 1:
            layer.mask.blockify(layer.hyperparams.blocksize)
          layer.state.mult(layer.mask)
      else:
        # Produce expected output.
        if layer.hyperparams.mult_dropout:
          pass
        else:
          layer.state.mult(1.0 - layer.hyperparams.dropout_prob)
    return perf

  def ComputeDown(self, layer, step):
    """Backpropagate through this layer.
    Args:
      step: The training step. Needed because some hyperparameters depend on
      which training step they are being used in.
    """
    if layer.is_input:  # Nobody to backprop to.
      return
    # At this point layer.deriv contains the derivative with respect to the
    # outputs of this layer. Compute derivative with respect to the inputs.
    if layer.is_output:
      loss = layer.GetLoss(get_deriv=True)
    else:
      loss = None
      if layer.hyperparams.sparsity:
        sparsity_gradient = layer.GetSparsityGradient()
        layer.deriv.add_col_vec(sparsity_gradient)
      layer.ComputeDeriv()
    # Now layer.deriv contains the derivative w.r.t to the inputs.
    # Send it down each incoming edge and update parameters on the edge.
    for edge in layer.incoming_edge:
      if edge.conv or edge.local:
        AccumulateConvDeriv(edge.node1, edge, layer.deriv)
      else:
        self.AccumulateDeriv(edge.node1, edge, layer.deriv)
      self.UpdateEdgeParams(edge, layer.deriv, step)
    # Update the parameters on this layer (i.e., the bias).
    self.UpdateLayerParams(layer, step)
    return loss

  def AccumulateDeriv(self, layer, edge, deriv):
    """Accumulate the derivative w.r.t the outputs of this layer.

    A layer needs to compute derivatives w.r.t its outputs. These outputs may
    have been connected to lots of other nodes through outgoing edges.
    This method adds up the derivatives contributed by each outgoing edge.
    It gets derivatives w.r.t the inputs at the other end of its outgoing edge.
    Args:
      edge: The edge which is sending the derivative.
      deriv: The derivative w.r.t the inputs at the other end of this edge.
    """
    if layer.is_input or edge.proto.block_gradient:
      return
    if layer.dirty:  # If some derivatives have already been received.
      layer.deriv.add_dot(edge.params['weight'], deriv)
    else:  # Receiving derivative for the first time.
      cm.dot(edge.params['weight'], deriv, target=layer.deriv)
      layer.dirty = True

  def UpdateEdgeParams(self, edge, deriv, step):
    """ Update the parameters associated with this edge.

    Update the weights and associated parameters.
    Args:
      deriv: Gradient w.r.t the inputs at the outgoing end.
      step: Training step.
    """
    numcases = edge.node1.batchsize
    if edge.conv or edge.local:
      ConvOuter(edge, edge.temp)
      edge.gradient.add_mult(edge.temp, mult=1.0/numcases)
    else:
      edge.gradient.add_dot(edge.node1.state, deriv.T, mult=1.0/numcases)
    if edge.tied_to:
      edge.tied_to.gradient.add(edge.gradient)
      edge.gradient.assign(0)
      edge = edge.tied_to
    edge.num_grads_received += 1
    if edge.num_grads_received == edge.num_shares:
      edge.Update('weight', step)

  def UpdateLayerParams(self, layer, step):
    """ Update the parameters associated with this layer.
    Update the bias.
    Args:
      step: Training step.
    """
    layer.gradient.add_sums(layer.deriv, axis=1, mult=1.0 / layer.batchsize)
    if layer.tied_to:
      layer.tied_to.gradient.add(layer.gradient)
      layer.gradient.assign(0)
      layer = layer.tied_to
    layer.num_grads_received += 1
    if layer.num_grads_received == layer.num_shares:
      layer.Update('bias', step, no_reg=True)  # By default, do not regularize bias.

  def ForwardPropagate(self, train=False, step=0):
    """Do a forward pass through the network.

    Args:
      train: True if the forward pass is done during training, False during
        evaluation.
      step: Training step.
    """
    losses = []
    for node in self.node_list:
      loss = self.ComputeUp(node, train, step, self.train_stop_steps)
      if loss:
        losses.append(loss)
    return losses

  def BackwardPropagate(self, step):
    """Backprop through the network.

    Args:
      step: Training step.
    """
    losses = []
    for node in reversed(self.node_list):
      loss = self.ComputeDown(node, step)
      if loss:
        losses.append(loss)
    return losses

  def TrainOneBatch(self, step):
    """Train once on one mini-batch.

    Args:
      step: Training step.
    Returns:
      List of losses incurred at each output layer.
    """
    losses1 = self.ForwardPropagate(train=True)
    losses2 = self.BackwardPropagate(step)
    losses1.extend(losses2)
    return losses1

  def EvaluateOneBatch(self):
    """Evaluate one mini-batch."""
    losses = self.ForwardPropagate()
    losses.extend([node.GetLoss() for node in self.output_datalayer])
    return losses

  def Evaluate(self, validation=True, collect_predictions=False):
    """Evaluate the model.
    Args:
      validation: If True, evaluate on the validation set,
        else evaluate on test set.
      collect_predictions: If True, collect the predictions.
    """
    step = 0
    stats = []
    if validation:
      stopcondition = self.ValidationStopCondition
      stop = stopcondition(step)
      if stop or self.validation_data_handler is None:
        return
      datagetter = self.GetValidationBatch
      prefix = 'V'
      stats_list = self.net.validation_stats
      num_batches = self.validation_data_handler.num_batches
    else:
      stopcondition = self.TestStopCondition
      stop = stopcondition(step)
      if stop or self.test_data_handler is None:
        return
      datagetter = self.GetTestBatch
      prefix = 'E'
      stats_list = self.net.test_stats
      num_batches = self.test_data_handler.num_batches
    if collect_predictions:
      output_layer = self.output_datalayer[0]
      collect_pos = 0
      batchsize = output_layer.batchsize
      numdims = output_layer.state.shape[0]
      predictions = np.zeros((batchsize * num_batches, numdims))
      targets = np.zeros(predictions.shape)
    while not stop:
      datagetter()
      losses = self.EvaluateOneBatch()
      if collect_predictions:
        predictions[collect_pos:collect_pos + batchsize] = \
            output_layer.state.asarray().T
        targets[collect_pos:collect_pos + batchsize] = \
            output_layer.data.asarray().T
        collect_pos += batchsize

      if stats:
        for loss, acc in zip(losses, stats):
          Accumulate(acc, loss)
      else:
        stats = losses
      step += 1
      stop = stopcondition(step)
    if collect_predictions and stats:
      predictions = predictions[:collect_pos]
      targets = targets[:collect_pos]
      MAP, prec50, MAP_list, prec50_list = self.ComputeScore(predictions, targets)
      stat = stats[0]
      stat.MAP = MAP
      stat.prec50 = prec50
      for m in MAP_list:
        stat.MAP_list.extend([m])
      for m in prec50_list:
        stat.prec50_list.extend([m])
    for stat in stats:
      sys.stdout.write(GetPerformanceStats(stat, prefix=prefix))
    stats_list.extend(stats)


  def ScoreOneLabel(self, preds, targets):
    """Computes Average precision and precision at 50."""
    targets_sorted = targets[(-preds.T).argsort().flatten(),:]
    cumsum = targets_sorted.cumsum()
    prec = cumsum / np.arange(1.0, 1 + targets.shape[0])
    total_pos = float(sum(targets))
    if total_pos == 0:
      total_pos = 1e-10
    recall = cumsum / total_pos
    ap = np.dot(prec, targets_sorted) / total_pos
    prec50 = prec[50]
    return ap, prec50

  def ComputeScore(self, preds, targets):
    """Computes Average precision and precision at 50."""
    assert preds.shape == targets.shape
    numdims = preds.shape[1]
    ap = 0
    prec = 0
    ap_list = []
    prec_list = []
    for i in range(numdims):
      this_ap, this_prec = self.ScoreOneLabel(preds[:,i], targets[:,i])
      ap_list.append(this_ap)
      prec_list.append(this_prec)
      ap += this_ap
      prec += this_prec
    ap /= numdims
    prec /= numdims
    return ap, prec, ap_list, prec_list

  def WriteRepresentationToDisk(self, layernames, output_dir, memory='1G',
                                dataset='test', drop=False):
    layers = [self.GetLayerByName(lname) for lname in layernames]
    numdim_list = [layer.state.shape[0] for layer in layers]
    if dataset == 'train':
      datagetter = self.GetTrainBatch
      if self.train_data_handler is None:
        return
      numbatches = self.train_data_handler.num_batches
      size = numbatches * self.train_data_handler.batchsize
    elif dataset == 'validation':
      datagetter = self.GetValidationBatch
      if self.validation_data_handler is None:
        return
      numbatches = self.validation_data_handler.num_batches
      size = numbatches * self.validation_data_handler.batchsize
    elif dataset == 'test':
      datagetter = self.GetTestBatch
      if self.test_data_handler is None:
        return
      numbatches = self.test_data_handler.num_batches
      size = numbatches * self.test_data_handler.batchsize
    datawriter = DataWriter(layernames, output_dir, memory, numdim_list, size)

    for batch in range(numbatches):
      datagetter()
      sys.stdout.write('\r%d' % (batch+1))
      sys.stdout.flush()
      self.ForwardPropagate(train=drop)
      reprs = [l.state.asarray().T for l in layers]
      datawriter.Submit(reprs)
    sys.stdout.write('\n')
    return datawriter.Commit()

  def TrainStopCondition(self, step):
    return step >= self.train_stop_steps

  def ValidationStopCondition(self, step):
    return step >= self.validation_stop_steps

  def TestStopCondition(self, step):
    return step >= self.test_stop_steps

  def EvalNow(self, step):
    return step % self.eval_now_steps == 0

  def SaveNow(self, step):
    return step % self.save_now_steps == 0

  def ShowNow(self, step):
    return self.show_now_steps > 0 and step % self.show_now_steps == 0

  def GetLayerByName(self, layername, down=False):
    try:
      l = next(l for l in self.layer if l.name == layername)
    except StopIteration:
      l = None
    return l

  def CopyModelToCPU(self):
    for layer in self.layer:
      layer.SaveParameters()
    for edge in self.edge:
      edge.SaveParameters()

  def ResetBatchsize(self, batchsize):
    self.batchsize = batchsize
    for layer in self.layer:
      layer.AllocateBatchsizeDependentMemory(batchsize)
    for edge in self.edge:
      edge.AllocateBatchsizeDependentMemory()

  def GetBatch(self, handler=None):
    if handler:
      data_list = handler.Get()
      if data_list[0].shape[1] != self.batchsize:
        self.ResetBatchsize(data_list[0].shape[1])
      for i, layer in enumerate(self.datalayer):
        layer.SetData(data_list[i])
    for layer in self.tied_datalayer:
      data = layer.data_tied_to.data
      if data.shape[1] != self.batchsize:
        self.ResetBatchsize(data.shape[1])
      layer.SetData(data)

  def GetTrainBatch(self):
    self.GetBatch(self.train_data_handler)

  def GetValidationBatch(self):
    self.GetBatch(self.validation_data_handler)

  def GetTestBatch(self):
    self.GetBatch(self.test_data_handler)

  def SetUpData(self, skip_outputs=False, skip_layernames=[]):
    """Setup the data."""
    hyp_list = []
    name_list = [[], [], []]
    for node in self.layer:
      if not (node.is_input or node.is_output):
        continue
      if skip_outputs and node.is_output:
        continue
      if node.name in skip_layernames:
        continue
      data_field = node.proto.data_field
      if data_field.tied:
        self.tied_datalayer.append(node)
        node.data_tied_to = next(l for l in self.datalayer\
                                 if l.name == data_field.tied_to)
      else:
        self.datalayer.append(node)
        hyp_list.append(node.hyperparams)
        if data_field.train:
          name_list[0].append(data_field.train)
        if data_field.validation:
          name_list[1].append(data_field.validation)
        if data_field.test:
          name_list[2].append(data_field.test)
    if self.t_op:
      op = self.t_op
    else:
      op = self.e_op
    handles = GetDataHandles(op, name_list, hyp_list,
                             verbose=self.verbose)
    self.train_data_handler = handles[0]
    self.validation_data_handler = handles[1]
    self.test_data_handler = handles[2]

  def SetUpTrainer(self):
    """Load the model, setup the data, set the stopping conditions."""
    self.LoadModelOnGPU()
    if self.verbose:
      self.PrintNetwork()
    self.SetUpData()
    if self.t_op.stopcondition.all_processed:
      num_steps = self.train_data_handler.num_batches
    else:
      num_steps = self.t_op.stopcondition.steps
    self.train_stop_steps = num_steps
    if self.e_op.stopcondition.all_processed and self.validation_data_handler:
      num_steps = self.validation_data_handler.num_batches
    else:
      num_steps = self.e_op.stopcondition.steps
    self.validation_stop_steps = num_steps
    if self.e_op.stopcondition.all_processed and self.test_data_handler:
      num_steps = self.test_data_handler.num_batches
    else:
      num_steps = self.e_op.stopcondition.steps
    self.test_stop_steps = num_steps

    self.eval_now_steps = self.t_op.eval_after
    self.save_now_steps = self.t_op.checkpoint_after
    self.show_now_steps = self.t_op.show_after

    self.ExchangeGlobalInfo()

  def Show(self):
    """Visualize the state of the layers and edges in the network."""
    for layer in self.layer:
      layer.Show()
    for edge in self.edge:
      edge.Show()

  def Train(self):
    """Train the model."""
    assert self.t_op is not None, 't_op is None.'
    assert self.e_op is not None, 'e_op is None.'
    self.SetUpTrainer()
    step = self.t_op.current_step
    stop = self.TrainStopCondition(step)
    stats = []

    collect_predictions = False
    try:
      p = self.output_datalayer[0].proto.performance_stats
      if p.compute_MAP or p.compute_prec50:
        collect_predictions = True
    except Exception as e:
      pass
    select_model_using_error = self.net.hyperparams.select_model_using_error
    select_model_using_acc = self.net.hyperparams.select_model_using_acc
    select_model_using_map = self.net.hyperparams.select_model_using_map
    select_best = select_model_using_error or select_model_using_acc or select_model_using_map
    if select_best:
      best_valid_error = float('Inf')
      test_error = float('Inf')
      best_net = self.DeepCopy()

    dump_best = False
    while not stop:
      sys.stdout.write('\rTrain Step: %d' % step)
      sys.stdout.flush()
      self.GetTrainBatch()
      losses = self.TrainOneBatch(step)
      if stats:
        for acc, loss in zip(stats, losses):
          Accumulate(acc, loss)
      else:
        stats = losses
      step += 1
      if self.ShowNow(step):
        self.Show()
      if self.EvalNow(step):
        # Print out training stats.
        sys.stdout.write('\rStep %d ' % step)
        for stat in stats:
          sys.stdout.write(GetPerformanceStats(stat, prefix='T'))
        self.net.train_stats.extend(stats)
        stats = []
        # Evaluate on validation set.
        self.Evaluate(validation=True, collect_predictions=collect_predictions)
        # Evaluate on test set.
        self.Evaluate(validation=False, collect_predictions=collect_predictions)
        if select_best:
          valid_stat = self.net.validation_stats[-1]
          if len(self.net.test_stats) > 1:
            test_stat = self.net.test_stats[-1]
          else:
            test_stat = valid_stat
          if select_model_using_error:
            valid_error = valid_stat.error / valid_stat.count
            _test_error = test_stat.error / test_stat.count
          elif select_model_using_acc:
            valid_error = 1 - float(valid_stat.correct_preds) / valid_stat.count
            _test_error = 1 - float(test_stat.correct_preds) / test_stat.count
          elif select_model_using_map:
            valid_error = 1 - valid_stat.MAP
            _test_error = 1 - test_stat.MAP
          if valid_error < best_valid_error:
            best_valid_error = valid_error
            test_error = _test_error
            dump_best = True
            self.CopyModelToCPU()
            self.t_op.current_step = step
            self.net.best_valid_stat.CopyFrom(valid_stat)
            self.net.train_stat_es.CopyFrom(self.net.train_stats[-1])
            self.net.test_stat_es.CopyFrom(test_stat)
            best_net = self.DeepCopy()
            best_t_op = CopyOperation(self.t_op)
        #for e in self.edge:
        #  sys.stdout.write(' %s %.3f' % (e.name, e.params['weight'].euclid_norm()))
        sys.stdout.write('\n')
      if self.SaveNow(step):
        self.t_op.current_step = step
        self.CopyModelToCPU()
        util.WriteCheckpointFile(self.net, self.t_op)
        if dump_best:
          dump_best = False
          if select_model_using_error:
            print 'Best valid error : %.4f Test error %.4f' % (best_valid_error, test_error)
          elif select_model_using_acc:
            print 'Best valid acc : %.4f Test acc %.4f' % (1-best_valid_error, 1-test_error)
          elif select_model_using_map:
            print 'Best valid MAP : %.4f Test MAP %.4f' % (1-best_valid_error, 1-test_error)

          util.WriteCheckpointFile(best_net, best_t_op, best=True)

      stop = self.TrainStopCondition(step)

########NEW FILE########
__FILENAME__ = parameter
from choose_matrix_library import *
import deepnet_pb2
import logging
import numpy as np
import os.path
import util
import visualize
import pdb

class Parameter(object):

  def __init__(self):
    self.num_shares = 1
    self.num_grads_received = 0
    self.transpose = False

  def SaveParameters(self):
    for param in self.proto.param:
      param.mat = util.NumpyAsParameter(self.params[param.name].asarray())

  def LoadParams(self, proto, t_op=None, tied_to=None):
    """Load the parameters for this edge.

    Load the parameters if present in self.proto. Otherwise initialize them
    appropriately.
    """
    param_names = [param.name for param in proto.param]
    for param in proto.param:
      assert param.dimensions, 'Empty dimensions'
      if tied_to:
        if self.transpose:
          self.params[param.name] = tied_to.params[param.name].T
        else:
          self.params[param.name] = tied_to.params[param.name]
        mat = self.params[param.name]
      else:
        if param.mat:
          mat = util.ParameterAsNumpy(param)
        else:
          mat = self.InitializeParameter(param)
        self.params[param.name] = cm.CUDAMatrix(mat)

  def InitializeParameter(self, param):
    if param.initialization == deepnet_pb2.Parameter.CONSTANT:
      return np.zeros(tuple(param.dimensions)) + param.constant
    elif param.initialization == deepnet_pb2.Parameter.DENSE_GAUSSIAN:
      return param.sigma * np.random.randn(*tuple(param.dimensions))
    elif param.initialization == deepnet_pb2.Parameter.DENSE_UNIFORM:
      return param.sigma * (2 * np.random.rand(*tuple(param.dimensions)) - 1)
    elif param.initialization == deepnet_pb2.Parameter.DENSE_GAUSSIAN_SQRT_FAN_IN:
      assert len(param.dimensions) > 1
      if param.conv or param.local:
        fan_in = np.prod(param.dimensions[0])
      else:
        fan_in = np.prod(param.dimensions[1])
      stddev = param.sigma / np.sqrt(fan_in)
      return stddev * np.random.randn(*tuple(param.dimensions))
    elif param.initialization == deepnet_pb2.Parameter.DENSE_UNIFORM_SQRT_FAN_IN:
      assert len(param.dimensions) > 1
      if param.conv or param.local:
        fan_in = np.prod(param.dimensions[0])
      else:
        fan_in = np.prod(param.dimensions[1])
      stddev = param.sigma / np.sqrt(fan_in)
      return stddev * (2 * np.random.rand(*tuple(param.dimensions)) - 1)
    elif param.initialization == deepnet_pb2.Parameter.PRETRAINED:
      return self.LoadPretrained(param)
    else:
      raise Exception('Unknown parameter initialization.')

  def LoadPretrained(self, param):
    pass

  def GetGlobalInfo(self, net):
    pass

  def ApplyL2Decay(self, w_delta, w, lambdaa, **kwargs):
    w_delta.add_mult(w, lambdaa)

  def Update(self, param_name, step, no_reg=False):
    h = self.hyperparams
    momentum, epsilon = self.GetMomentumAndEpsilon(step)

    w = self.params[param_name]  # Parameter to be updated.
    w_delta = self.gradient_history  # Previous update.
    gradient = self.gradient  # Current gradient.

    # Compute update.
    if h.adapt == deepnet_pb2.Hyperparams.NONE:
      w_delta.mult(momentum)
      if not no_reg and h.apply_l2_decay:
        self.ApplyL2Decay(w_delta, w, h.l2_decay, step=step, eps=epsilon, mom=momentum)
      if not no_reg and h.apply_l1_decay and step > h.apply_l1decay_after:
        w_delta.add_mult_sign(w, h.l1_decay)
    else:
      raise Exception('Not implemented.')
    w_delta.add_mult(gradient)

    # Apply update.
    w.add_mult(w_delta, -epsilon)
    if not no_reg and h.apply_weight_norm:
      w.norm_limit(h.weight_norm, axis=0)

    # Reset.
    self.num_grads_received = 0
    gradient.assign(0)

  def GetMomentumAndEpsilon(self, step):
    """
    if h.momentum_change_steps > step:
      f = float(step) / h.momentum_change_steps
      momentum = (1.0 - f) * h.initial_momentum + f * h.final_momentum
    else:
      momentum = h.final_momentum
    """
    h = self.hyperparams
    momentum = h.final_momentum - (h.final_momentum - h.initial_momentum)*np.exp(-float(step)/h.momentum_change_steps)
    epsilon = h.base_epsilon
    if h.epsilon_decay == deepnet_pb2.Hyperparams.INVERSE_T:
      epsilon = h.base_epsilon / (1 + float(step) / h.epsilon_decay_half_life)
    elif h.epsilon_decay == deepnet_pb2.Hyperparams.EXPONENTIAL:
      epsilon = h.base_epsilon / np.power(2, float(step) / h.epsilon_decay_half_life)
    if step < h.start_learning_after:
      epsilon = 0.0
    return momentum, epsilon


########NEW FILE########
__FILENAME__ = relu_layer
from layer import *

class ReluLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(ReluLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.RECTIFIED_LINEAR

  def ApplyActivation(self, neg=False):
    if neg:
      state = self.neg_state
    else:
      state = self.state
    state.lower_bound(0)

  def Sample(self, neg=False):
    if neg:
      sample = self.neg_sample
      state = self.neg_state
    else:
      sample = self.sample
      state = self.state
    state.sample_gaussian(target=sample, mult=1.0)
    sample.lower_bound(0)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    self.deriv.apply_rectified_linear_deriv(self.state)

  def GetLoss(self, get_deriv=False, acc_deriv=False, **kwargs):
    """Compute loss and also deriv w.r.t to it if asked for.

    Compute the loss function. Targets should be in self.data, predictions
    should be in self.state.
    Args:
      get_deriv: If True, compute the derivative w.r.t the loss function and put
        it in self.deriv.
    """
    perf = deepnet_pb2.Metrics()
    perf.MergeFrom(self.proto.performance_stats)
    perf.count = self.batchsize
    if self.loss_function == deepnet_pb2.Layer.SQUARED_LOSS:
      target = self.statesize
      self.state.subtract(self.data, target=target)
      error = target.euclid_norm()**2
      perf.error = error
      if acc_deriv:
        self.deriv.add_mult(target, alpha=self.loss_weight)
      else:
        self.deriv.assign(target)
      if get_deriv:
        self.ComputeDeriv()
    else:
      raise Exception('Unknown loss function for ReLU units.')
    return perf


########NEW FILE########
__FILENAME__ = replicated_softmax_layer
from layer import *

class ReplicatedSoftmaxLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(ReplicatedSoftmaxLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == \
        deepnet_pb2.Hyperparams.REPLICATED_SOFTMAX

  def ApplyActivation(self):
    state = self.state
    temp = self.batchsize_temp

    state.max(axis=0, target=temp)
    state.add_row_mult(temp, -1)
    cm.exp(state)
    state.sum(axis=0, target=temp)
    self.NN.divide(temp, target=temp)
    state.mult_by_row(temp)

  def Sample(self):
    sample = self.sample
    state = self.state
    use_lightspeed = False
    if use_lightspeed:  # Do sampling on cpu.
      temp = self.expanded_batch
      state.sum(axis=0, target=self.temp)
      state.div_by_row(self.temp, target=temp)
      probs_cpu = temp.asarray().astype(np.float64)
      numsamples = self.NN.asarray()
      samples_cpu = lightspeed.SampleSoftmax(probs_cpu, numsamples)
      sample.overwrite(samples_cpu.astype(np.float32))
    else:
      if self.proto.hyperparams.adaptive_prior > 0:
        sample.assign(0)
        temp_sample = self.expanded_batch
        numsamples = int(self.proto.hyperparams.adaptive_prior)
        for i in range(numsamples):
          state.perturb_prob_for_softmax_sampling(target=temp_sample)
          temp_sample.choose_max_and_accumulate(sample)
      else:
        NN = self.NN.asarray().reshape(-1)
        numdims, batchsize = self.state.shape
        max_samples = self.big_sample_matrix.shape[1]
        for i in range(batchsize):
          nn = NN[i]
          factor = 1
          if nn > max_samples:
            nn = max_samples
            factor = float(nn) / max_samples
          samples = self.big_sample_matrix.slice(0, nn)
          samples.assign(0)
          samples.add_col_vec(self.state.slice(i, i+1))
          samples.perturb_prob_for_softmax_sampling()
          samples.choose_max(axis=0)
          samples.sum(axis=1, target=sample.slice(i, i+1))
          if factor > 1:
            sample.slice(i, i+1).mult(factor)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    raise Exception('Back prop through replicated softmax not implemented.')

  def AllocateMemory(self, batchsize):
    super(ReplicatedSoftmaxLayer, self).AllocateMemory(batchsize)
    self.expansion_matrix = cm.CUDAMatrix(np.eye(self.numlabels))
    self.big_sample_matrix = cm.empty((self.numlabels * self.dimensions, 1000))

  def AllocateBatchsizeDependentMemory(self, batchsize):
    super(ReplicatedSoftmaxLayer, self).AllocateBatchsizeDependentMemory(batchsize)
    dimensions = self.dimensions
    numlabels = self.numlabels
    self.expanded_batch = cm.CUDAMatrix(np.zeros((numlabels * dimensions, batchsize)))
    self.batchsize_temp = cm.CUDAMatrix(np.zeros((dimensions, batchsize)))
    if self.is_input or self.is_initialized or self.is_output:
      self.data = cm.CUDAMatrix(np.zeros((numlabels * dimensions, batchsize)))
    self.NN = cm.CUDAMatrix(np.ones((1, batchsize)))
    self.counter = cm.empty(self.NN.shape)
    self.count_filter = cm.empty(self.NN.shape)

  def ResetState(self, rand=False):
    if self.hyperparams.normalize:
      self.NN.assign(self.hyperparams.normalize_to)
    else:
      self.NN.assign(1)
    super(ReplicatedSoftmaxLayer, self).ResetState(rand=rand)

  def GetData(self):
    self.state.assign(self.data)
    h = self.hyperparams
    self.state.sum(axis=0, target=self.NN)
    self.NN.add(self.tiny)  # To deal with documents of 0 words.
    if h.multiplicative_prior > 0:
      self.NN.mult(1 + h.multiplicative_prior)
      self.state.mult(1 + h.multiplicative_prior)
    if h.additive_prior > 0:
      self.state.div_by_row(self.NN)
      self.NN.add(h.additive_prior)
      self.state.mult_by_row(self.NN)
    if h.adaptive_prior > 0:
      self.state.div_by_row(self.NN)
      self.state.mult(h.adaptive_prior)
      self.NN.assign(h.adaptive_prior)

  def GetLoss(self, get_deriv=False):
    """Compute loss and also deriv w.r.t to it if asked for.

    Compute the loss function. Targets should be in self.data, predictions
    should be in self.state.
    Args:
      get_deriv: If True, compute the derivative w.r.t the loss function and put
        it in self.deriv.
    """
    perf = deepnet_pb2.Metrics()
    perf.MergeFrom(self.proto.performance_stats)
    perf.count = self.batchsize
    tiny = self.tiny
    temp = self.batchsize_temp
    if self.loss_function == deepnet_pb2.Layer.SQUARED_LOSS:
      if get_deriv:
        target = self.deriv
      else:
        target = self.statesize
      if self.hyperparams.normalize_error:
        self.data.sum(axis=0, target=temp)
        temp.add(self.tiny)
        self.data.div_by_row(temp, target=target)
        self.state.div_by_row(self.NN, target=self.expanded_batch)
        target.subtract(self.expanded_batch)
      else:
        self.data.sum(axis=0, target=temp)
        temp.add(self.tiny)
        self.state.div_by_row(temp, target=target)
        target.subtract(self.data)
      error = target.euclid_norm()**2
      perf.error = error
    else:
      raise Exception('Unknown loss function for Replicated Softmax units.')
    return perf

  def GetSparsityDivisor(self):
    raise Exception('Sparsity not implemented for replicated softmax units.')

  def CollectSufficientStatistics(self, neg=False):
    """Collect sufficient statistics for this layer."""
    h = self.hyperparams
    self.state.div_by_row(self.NN)
    if not neg:
      self.state.sum(axis=1, target=self.suff_stats)
    else:
      self.suff_stats.add_sums(self.state, axis=1, mult=-1.0)
    self.state.mult_by_row(self.NN)

########NEW FILE########
__FILENAME__ = sequence_datahandler
import datahandler as dh
import pdb
import sys

class SequenceDisk(dh.Disk):
  def __init__(self, *args, **kwargs):
    super(SequenceDisk, self).__init__(*args, **kwargs)
    self.disable_chunk_split = True
    self.collect_chunk_boundaries = True
    self.left_window = kwargs.get('left_window', [])
    self.right_window = kwargs.get('right_window', [])

  def LoadSequence(self, inputfile):
    """Loads a squence file stored in a pickle."""

    data_pkl = dh.Disk.LoadPickle(inputfile)
    data_list = []
    for i, key in enumerate(self.keys):
      seq = data_pkl[key].T
      if len(seq.shape) == 1:
        seq = seq.reshape(-1, 1)

      # Add padding.
      lw = self.left_window[i]
      rw = self.right_window[i]
      if lw > 0 or rw > 0:
        padded_length = lw + seq.shape[0] + rw
        numdims = seq.shape[1]
        seq_padded = dh.np.zeros((padded_length, numdims))

        if lw > 0:
          seq_padded[0:lw,:] = dh.np.tile(seq[0], (lw, 1))

        start = lw
        end = seq.shape[0] + lw
        seq_padded[start:end,:] = seq

        if rw > 0:
          seq_padded[end:end+rw,:] = dh.np.tile(seq[-1], (rw, 1))
        data_list.append(seq_padded)
      else:
        data_list.append(seq)

    return data_list

  def Get(self, batchsize):
    """Reads data from disk.
    Args:
      batchsize: Number of data points to read.
    Returns:
      A list of numpy arrays each with batchsize rows. Each element of the list
      is one data modality.
    """
    assert self.num_data <= 2

    i = 0
    numdims = self.numdim_list[i]
    filename_list = self.filenames[i]
    num_files = self._num_file_list[i]
    current_file = (self.last_read_file[i] + 1) % num_files

    data_list = []
    boundaries = []
    datasize = [0]*self.num_data  # Number of rows of data filled up.
    for i in range(self.num_data):
      boundaries.append([])
      data_list.append(dh.np.zeros((batchsize, self.numdim_list[i]), dtype='float32'))

    # Read data from disk.
    while(datasize[0] < batchsize):
      if self.last_read_file[0] != current_file:
        if self.verbose:
          sys.stdout.write('\rLoading %s ...' % filename_list[current_file])
          sys.stdout.flush()
        this_chunk = self.LoadSequence(filename_list[current_file])
        self.last_read_chunk[0] = this_chunk
        self.last_read_file[0] = current_file
      else:
        this_chunk = self.last_read_chunk[0]
      is_full = False
      for i, d in enumerate(this_chunk):
        chunk_size = d.shape[0]
        if chunk_size + datasize[i] > batchsize:
          is_full = True
      if is_full:
        for i in range(len(this_chunk)):
          data_list[i] = data_list[i][:datasize[i]]
        break
      else:
        for i, d in enumerate(this_chunk):
          lw = self.left_window[i]
          rw = self.right_window[i]
          cs = d.shape[0]
          ds = datasize[i]
          data_list[i][ds : ds + cs] = d
          # if lw + rw > 0:
          #   valid_boundaries = range(ds + lw, ds + cs - rw)
          boundaries[i].append(cs)
          datasize[i] += cs
      current_file = (current_file + 1) % num_files
    if self.verbose:
      sys.stdout.write('\n')
    return data_list, boundaries

class SequenceCache(dh.Cache):
  def __init__(self, *args, **kwargs):
    super(SequenceCache, self).__init__(*args, **kwargs)
    self.left_window = kwargs.get('left_window', [])
    self.right_window = kwargs.get('right_window', [])
    self.data_len = len(self.left_window)
    self._pos = [0] * self.data_len
    self._relpos = [0] * self.data_len
    self._utt = [0] * self.data_len
    max_padding = 0
    max_padding_i = 0
    for i in range(self.data_len):
      lw = self.left_window[i]
      rw = self.right_window[i]
      if lw + rw > max_padding:
        max_padding_i = i
        max_padding = lw + rw
    self.max_padding_i = max_padding_i

  def LoadData(self):
    if self.data == [] or self._maxpos < self.parent._maxpos:
      data, boundaries = self.parent.Get(self._maxpos)
      self.data = data
      self.boundaries = boundaries
      self.datasize = self.data[self.max_padding_i].shape[0]

  def Get(self, batchsize, mult_of):
    max_i = self.max_padding_i
    if self._pos[max_i] == self.datasize:
      for i in range(self.data_len):
        self._pos[i] = 0
    if self._pos[max_i] == 0:
      self.LoadData()
    
    max_lw = self.left_window[max_i]
    max_rw = self.right_window[max_i]

    startpos = self._pos[max_i]  # pos from start of in-memory data.
    start_relpos = self._relpos[max_i]  # Relative pos from start of utterance.
    start_utt = self._utt[max_i]  # Current utterance.
    bd = self.boundaries[max_i]

    endpos = min(startpos + batchsize, self.datasize)

    # Find number of valid indices between start_pos and end_pos.
    utt = start_utt
    relpos = start_relpos
    num_valid = 0
    pos = 0
    while pos < endpos - startpos:
      f = bd[utt]
      if pos + f - relpos > endpos - startpos:
        remaining = endpos - startpos - pos
        if relpos + remaining > f - max_rw:
          remaining = f - rw - relpos
        if relpos > max_lw:
          num_valid_in_this_utt = remaining
        else:
          num_valid_in_this_utt = max(0, relpos + remaining - lw)
        num_valid += num_valid_in_this_utt
        pos = endpos - startpos
        relpos += remaining
      else:
        if relpos < max_lw:
          num_valid_in_this_utt = f - max_lw - max_rw
        elif relpos > f - max_rw:
          num_valid_in_this_utt = 0
        else:
          num_valid_in_this_utt = f - relpos - max_rw
        num_valid += num_valid_in_this_utt
        pos += f - relpos
        relpos = 0
        utt += 1
    num_valid = (num_valid / mult_of) * mult_of

    batch = []
    indices = []
    for i in range(self.data_len):
      startpos = self._pos[i]  # pos from start of in-memory data.
      relpos = self._relpos[i]  # Relative pos from start of utterance.
      utt = self._utt[i]  # Current utterance.
      lw = self.left_window[i]
      rw = self.right_window[i]

      this_valid = 0
      pos = 0
      bd = self.boundaries[i]
      this_indices = []
      while(this_valid < num_valid):
        f = bd[utt]
        if relpos < lw:
          num_valid_in_this_utt = f - lw - rw
          start_valid = pos + lw
        elif relpos > f - rw:
          num_valid_in_this_utt = 0
          start_valid = pos
        else:
          num_valid_in_this_utt = f - relpos - rw
          start_valid = pos
        if this_valid + num_valid_in_this_utt > num_valid:
          num_valid_needed = num_valid - this_valid
          this_indices.extend(range(
            start_valid, start_valid + num_valid_needed))
          pos += lw + num_valid_needed + rw
          relpos = lw + num_valid_needed
          break
        else:
          this_valid += num_valid_in_this_utt
          this_indices.extend(range(
            start_valid, start_valid + num_valid_in_this_utt))
          pos += f - relpos
          relpos = 0
          utt += 1
      batch.append(self.data[i][startpos:startpos + pos])
      indices.append(this_indices)
      self._utt[i] = utt
      self._pos[i] += pos 
      self._relpos[i] = relpos
    return batch, indices


class SequenceGPUCache(dh.GPUCache):
  """Manager for a cache that stores sequential data."""

  def __init__(self, *args, **kwargs):
    super(SequenceGPUCache, self).__init__(*args, **kwargs)
    self.left_window = kwargs.get('left_window', [])
    self.right_window = kwargs.get('right_window', [])
    self.batchsize = kwargs.get('batchsize')
    batchsize = self.batchsize
    #self.indices = dh.cm.CUDAMatrix(dh.np.arange(batchsize).reshape(1, -1))
    self.batches = []
    self.templates = []
    self.window_sizes = []
    self.batch_indices = []
    self.data_len = len(self.left_window)
    self.AllocateBatchsizeDepedentMemory(batchsize)

    self.data = []
    self.valid_indices = []
    self.empty = True
    for i in range(self.data_len):
      self.data.append(dh.cm.CUDAMatrix(dh.np.zeros((self.numdim_list[i], self._maxpos))))
      self.valid_indices.append(dh.cm.CUDAMatrix(dh.np.zeros((1, self._maxpos))))

  def AllocateBatchsizeDepedentMemory(self, batchsize):
    self.batches = []
    self.templates = []
    self.window_sizes = []
    self.batch_indices = []
    for i in range(self.data_len):
      l = self.left_window[i]
      r = self.right_window[i]
      window_size = 1 + l + r
      numdims = self.numdim_list[i]
      batch = dh.cm.empty((numdims * window_size, batchsize))
      window = dh.np.arange(-l, r + 1).reshape(-1, 1)
      template = dh.cm.CUDAMatrix(dh.np.tile(window, (1, batchsize)))
      self.batches.append(batch)
      self.templates.append(template)
      self.window_sizes.append(window_size)
      self.batch_indices.append(dh.cm.empty(template.shape))


  def ShuffleData(self):
    indices = dh.np.arange(self.datasize)
    dh.np.random.shuffle(indices)
    indices1 = indices[:self.datasize/2]
    indices2 = indices[self.datasize/2:2*(self.datasize/2)]
    indices1_gpu = dh.cm.CUDAMatrix(indices1.reshape(1, -1))
    indices2_gpu = dh.cm.CUDAMatrix(indices2.reshape(1, -1))
    for d in self.valid_indices:
      d.swap_columns(indices1_gpu, indices2_gpu, target=d)
    indices1_gpu.free_device_memory()
    indices2_gpu.free_device_memory()

  def Get(self, batchsize, get_last_piece=False):
    """Return 'batchsize' data points from the cache."""
    skip = False
    if self._pos == self.datasize:
      self._pos = 0
    if self._pos == 0:
      if self.empty or self._maxpos < self.parent._maxpos:
        if get_last_piece:
          self.LoadData(1)
        else:
          self.LoadData(batchsize)
        self.empty = False
      if self.randomize:
        self.ShuffleData()
    start = self._pos
    end = self._pos + batchsize
    if end > self.datasize:
      end = self.datasize
      skip = not get_last_piece
    self._pos = end
    if skip:
      return self.Get(batchsize, get_last_piece=get_last_piece)
    else:
      for i, d in enumerate(self.data):
        centers = self.valid_indices[i].slice(start, end)
        self.ExtractWindows(d, centers, i)
      return self.batches

  def ExtractWindows(self, d, centers, i):
    """Extracts window around the indices in 'centers' from d."""
    batchsize = centers.shape[1] 
    if batchsize != self.batches[i].shape[1]:
      self.AllocateBatchsizeDepedentMemory(batchsize)
    batch = self.batches[i]
    template = self.templates[i]
    batch_indices = self.batch_indices[i]
    window_size = self.window_sizes[i]
    numdims = self.numdim_list[i]

    batch_indices.reshape((window_size, batchsize))
    template.add_row_vec(centers, target=batch_indices)
    batch_indices.reshape((1, window_size * batchsize))
    batch.reshape((numdims, window_size * batchsize))
    d.select_columns(batch_indices, target=batch)
    batch.reshape((numdims * window_size, batchsize))

  def LoadData(self, batchsize):
    data_cpu, indices_cpu = self.parent.Get(self._maxpos, batchsize)
    datasize = len(indices_cpu[0])
    self.datasize = datasize
    for i, d in enumerate(data_cpu):
      mat = d.T
      self.data[i].overwrite(mat)
      self.valid_indices[i].overwrite(dh.np.array(
        indices_cpu[i]).reshape(1, -1))
    self.Normalize()

  def Normalize(self):
    for i, batch in enumerate(self.data):
      if self.normalize[i]:
        mean = self.means[i]
        std = self.stds[i]
        window_size = self.window_sizes[i]
        batchsize = self.batchsize
        numdims = self.numdim_list[i]
        batch.add_col_mult(mean, mult=-1.0)
        batch.div_by_col(std)

########NEW FILE########
__FILENAME__ = sin_layer
from layer import *

class SinLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(SinLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.SIN

  def ApplyActivation(self):
    self.backup_state.assign(self.state)
    cm.sin(self.state)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    self.deriv.apply_sin_deriv(self.backup_state)

  def AllocateBatchsizeDependentMemory(self, batchsize):
    super(SinLayer, self).AllocateBatchsizeDependentMemory(batchsize)
    self.backup_state = cm.CUDAMatrix(np.zeros(self.statesize.shape))

########NEW FILE########
__FILENAME__ = smooth_relu_layer
from relu_layer import *

class SmoothReluLayer(ReluLayer):
  def __init__(self, *args, **kwargs):
    super(SmoothReluLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.RECTIFIED_LINEAR_SMOOTH

  def ApplyActivation(self):
    if neg:
      state = self.neg_state
    else:
      state = self.state
    cm.log_1_plus_exp(state)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    self.deriv.apply_rectified_linear_smooth_deriv(self.state)

########NEW FILE########
__FILENAME__ = softmax_layer
from layer import *

class SoftmaxLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(SoftmaxLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.SOFTMAX

  def ApplyActivation(self):
    self.state.apply_softmax()

  def Sample(self):
    self.state.perturb_prob_for_softmax_sampling(target=self.sample)
    self.sample.choose_max(axis=0)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    raise Exception('Back prop through softmax not implemented.')

  def AllocateMemory(self, batchsize):
    super(SoftmaxLayer, self).AllocateMemory(batchsize)
    self.expansion_matrix = cm.CUDAMatrix(np.eye(self.numlabels))

  def AllocateBatchsizeDependentMemory(self, batchsize):
    super(SoftmaxLayer, self).AllocateBatchsizeDependentMemory(batchsize)
    dimensions = self.dimensions
    numlabels = self.numlabels
    self.data = cm.CUDAMatrix(np.zeros((dimensions, batchsize)))
    self.deriv = cm.CUDAMatrix(np.zeros((numlabels*dimensions, batchsize)))
    self.batchsize_temp = cm.CUDAMatrix(np.zeros((dimensions, batchsize)))

  def GetData(self):
    self.expansion_matrix.select_columns(self.data, target=self.state)

  def GetLoss(self, get_deriv=False, **kwargs):
    """Compute loss and also deriv w.r.t to it if asked for.

    Compute the loss function. Targets should be in self.data, predictions
    should be in self.state.
    Args:
      get_deriv: If True, compute the derivative w.r.t the loss function and put
        it in self.deriv.
    """
    perf = deepnet_pb2.Metrics()
    perf.MergeFrom(self.proto.performance_stats)
    perf.count = self.batchsize
    tiny = self.tiny
    batchsize = self.batchsize
    dimensions = self.dimensions
    numlabels = self.numlabels
    state = self.state
    data = self.data

    # Reshape to make each softmax be one column.
    state.reshape((numlabels, dimensions * batchsize))
    data.reshape((1, dimensions * batchsize))

    if self.loss_function == deepnet_pb2.Layer.CROSS_ENTROPY:
      temp = self.batchsize_temp
      
      # Compute correct predictions.
      state.get_softmax_correct(data, target=temp)
      perf.correct_preds = temp.sum()

      # Compute cross entropy.
      state.get_softmax_cross_entropy(data, target=temp, tiny=tiny)
      perf.cross_entropy = temp.sum()

      # Compute derivative.
      if get_deriv:
        state.apply_softmax_grad(data, target=self.deriv)

    elif self.loss_function == deepnet_pb2.Layer.SQUARED_LOSS:
      state.apply_softmax_grad(data, target=self.deriv)
      error = self.deriv.euclid_norm()**2
      perf.error = error
    else:
      raise Exception('Unknown loss function for Softmax units.')
    
    # Restore shapes.
    state.reshape((numlabels * dimensions, batchsize))
    data.reshape((dimensions, batchsize))
    
    return perf

  def GetSparsityDivisor(self):
    raise Exception('Sparsity not implemented for softmax units.')


########NEW FILE########
__FILENAME__ = soft_transfer_edge
from edge import *

class SoftTransferEdge(Edge):
  @classmethod
  def IsEdgeType(cls, proto):
    return proto.hyperparams.soft_shared_prior


  def InitializeSoftWeights(self, superclasses):
    numsuperclasses = superclasses.max() + 1
    numclasses = len(superclasses)
    sw = np.zeros((numclasses, numclasses))
    for k in range(numsuperclasses):
      indices = (superclasses == k).nonzero()[0]
      for i in indices:
        sw[i, indices] = 1
        sw[i, i] = 0
    sw /= sw.sum(axis=1) + 1e-10
    return sw

  def LoadParams(self, proto, **kwargs):
    super(SoftTransferEdge, self).LoadParams(proto, **kwargs)
    self.shared_prior_cost = self.hyperparams.shared_prior_cost

    if self.hyperparams.shared_prior_file:
      fname = os.path.join(self.prefix, self.hyperparams.shared_prior_file)
      sc = np.load(fname).reshape(-1)
      sw = self.InitializeSoftWeights(sc)
      if 'soft_weight' in self.params:
        self.params['soft_weight'].overwrite(sw)
      else:
        self.params['soft_weight'] = cm.CUDAMatrix(sw)
    if self.hyperparams.label_freq_file:
      fname = os.path.join(self.prefix, self.hyperparams.label_freq_file)
      label_freq = np.load(fname).reshape(1, -1)
      self.label_freq = cm.CUDAMatrix(label_freq)
    else:
      self.label_freq = None

    w = self.params['weight']
    self.prior_mean = cm.empty(w.shape)
    self.diff = cm.empty(w.shape)

  def AllocateMemory(self):
    super(SoftTransferEdge, self).AllocateMemory()
    self.transform_gradient_history = cm.CUDAMatrix(np.zeros(self.params['soft_weight'].shape))

  def ApplyL2Decay(self, w_delta, w, lambdaa, step=0, eps=0.0, mom=0.0, **kwargs):
    diff = self.diff
    transform = self.params['soft_weight']
    transform_delta = self.transform_gradient_history
    pm = self.prior_mean

    cm.dot(w, transform, target=pm)
    w.subtract(pm, target=diff)
    if self.label_freq is not None:
      diff.div_by_row(self.label_freq)
    w_delta.add_mult(diff, lambdaa)

    transform_delta.mult(mom)
    transform_delta.add_dot(w.T, diff, mult=-lambdaa)  # gradient for the transform.
    transform_delta.add_mult_sign(transform, self.shared_prior_cost) # L1-Decay the transform.
    transform_delta.mult_diagonal(0)  # set diagonal to zero.
    transform.add_mult(transform_delta, -eps)

  def Show(self):
    if not self.hyperparams.enable_display:
      return
    visualize.show(self.params['soft_weight'].asarray(), self.fig, title='Sharing weights')


########NEW FILE########
__FILENAME__ = sparse_coder
from neuralnet import *
from sparse_code_layer import *
import scipy.linalg

class SparseCoder(NeuralNet):
  def SetLayerAndEdgeClass(self):
    self.LayerClass = SparseCodeLayer
    self.EdgeClass = Edge

  def Show(self):
    encoder = self.encoder.params['weight'].asarray()
    decoder = self.decoder.params['weight'].asarray()
    recon = self.input_layer.approximator.asarray()
    recep_field = self.encoder.proto.receptive_field_width
    rows = self.encoder.proto.display_rows
    cols = self.encoder.proto.display_cols
    visualize.display_wsorted(encoder, recep_field, rows, cols, 1, title='encoder')
    visualize.display_wsorted(decoder.T, recep_field, rows, cols, 2, title='decoder')
    visualize.display_w(recon[:, :100], recep_field, 10, 10, 3, title='reconstructions')
    visualize.display_hidden(self.code_layer.state.asarray(), 4, 'code distribution', prob=False)

  def Sort(self):
    assert len(self.layer) == 2
    assert len(self.edge) == 2
    if self.layer[0].is_input:
      self.input_layer = self.layer[0]
      self.code_layer = self.layer[1]
    else:
      self.input_layer = self.layer[1]
      self.code_layer = self.layer[0]
    if self.edge[0].node1 == self.input_layer:
      self.encoder = self.edge[0]
      self.decoder = self.edge[1]
    else:
      self.encoder = self.edge[1]
      self.decoder = self.edge[0]
    return [self.input_layer, self.code_layer]

  def SolveForZ(self):
    """Solve for z in (alpha + beta.wd.wd^T)z = wd . x + alpha z_est - gamma exactly.

    Output goes in z. temp is a matrix to store wd^Twd.
    """
    input_layer = self.input_layer
    code_layer = self.code_layer
    z = code_layer.state
    wd = self.decoder.params['weight']
    hyp = code_layer.hyperparams
    alpha = hyp.sc_alpha
    beta = hyp.sc_beta
    gamma = hyp.sc_gamma
    temp = code_layer.m_by_m
    temp2 = code_layer.deriv
    eye_m_by_m = code_layer.eye_m_by_m

    cm.dot(wd, wd.T, target=temp)
    temp.mult(beta)
    temp.add(alpha)
    z_est.mult(alpha, target=temp2)
    temp2.add_dot(wd, x, mult=beta)
    temp2.subtract(gamma)

    # Copy matrices to cpu.
    A = temp.asarray()
    B = temp2.asarray()

    # Solve AZ = B
    Z = scipy.linalg.solve(A, B, overwrite_a=True, overwrite_b=True)
    
    # Copy result back to gpu.
    z.overwrite(Z)

  def IterateForZ(self, train=False):
    """Solve for z in (alpha + beta.wd.wd^T)z = wd . x + alpha z_est - gamma using gradient descent.

    Output goes in z. temp is a matrix to store wd^Twd.
    """
    input_layer = self.input_layer
    code_layer = self.code_layer
    epsilon = 0.01
    steps = 20
    z = code_layer.state
    wd = self.decoder.params['weight']
    hyp = code_layer.hyperparams
    alpha = hyp.sc_alpha
    beta = hyp.sc_beta
    gamma = hyp.sc_gamma
    temp = code_layer.m_by_m
    temp2 = code_layer.deriv
    temp3 = code_layer.temp3  # This is bad! use better names.
    grad = code_layer.grad
    z_est = code_layer.approximator

    avg_models = hyp.dropout and (not hyp.dropout or not train)

    cm.dot(wd, wd.T, target=temp)
    temp.mult(beta)

    if avg_models:
      temp.mult((1.0 - hyp.dropout_prob)**2)
      temp.mult_diagonal(1. / (1.0 - hyp.dropout_prob))

    temp.add_diagonal(alpha)

    z_est.mult(alpha, target=temp2)

    if avg_models:
      temp2.add_dot(wd, input_layer.state, mult=beta * (1.0 - hyp.dropout_prob))
      #temp2.add_dot(wd, input_layer.state, mult=beta)
    elif hyp.dropout:
      temp2.add_dot(wd, input_layer.state, mult=beta)
      temp2.mult(code_layer.mask)
    else:
      temp2.add_dot(wd, input_layer.state, mult=beta)
    z.assign(z_est)

    #pdb.set_trace()
    for i in range(steps):
      cm.dot(temp, z, target=grad)
      grad.subtract(temp2)
      z.sign(target=temp3)
      grad.add_mult(temp3, alpha=gamma)
      if hyp.dropout and train:
        #code_layer.mask.fill_with_rand()
        #code_layer.mask.greater_than(hyp.dropout_prob)
        grad.mult(code_layer.mask)
      z.add_mult(grad, alpha=-epsilon)
    #pdb.set_trace()


  def ForwardPropagate(self, train=False, method='iter'):
    """Loads input and computes the sparse code for it."""

    input_layer = self.input_layer
    code_layer = self.code_layer

    # Load data into state.
    input_layer.GetData()

    # Run it through the encoder.
    inputs = input_layer.state
    we = self.encoder.params['weight']
    be = code_layer.params['bias']
    scale = code_layer.params['scale']
    hyp = code_layer.hyperparams
    code_approx = code_layer.approximator
    cm.dot(we.T, inputs, target=code_approx)
    code_approx.add_col_vec(be)
    code_layer.ApplyActivation(code_approx)
    code_approx.mult_by_col(scale)
    if hyp.dropout and train:
      code_layer.mask.fill_with_rand()
      code_layer.mask.greater_than(hyp.dropout_prob)
      code_approx.mult(code_layer.mask)

    # Infer z.
    if train:
      if method == 'iter':
        self.IterateForZ(train=train)
      elif method == 'exact':
        self.SolveForZ()
    else:
      if method == 'iter':
        self.IterateForZ(train=train)
      #code_layer.state.assign(code_approx)

  def GetLoss(self, train=False):
    """Computes loss and its derivatives."""

    input_layer = self.input_layer
    code_layer = self.code_layer

    # Decode z.
    hyp = code_layer.hyperparams
    wd = self.decoder.params['weight']
    bd = input_layer.params['bias']
    z = code_layer.state
    input_recon = input_layer.approximator
    cm.dot(wd.T, z, target=input_recon)
    input_recon.add_col_vec(bd)

    # Compute loss function.
    code_approx = code_layer.approximator
    alpha = hyp.sc_alpha
    gamma = hyp.sc_gamma
    beta = hyp.sc_beta
    input_recon.subtract(input_layer.state, target=input_layer.deriv)  # input reconstruction residual.
    code_approx.subtract(z, target=code_layer.deriv)  # code construction residual.
    cm.abs(z, target=code_layer.temp)  # L1 norm of code.
    code_layer.temp.sum(axis=1, target=code_layer.dimsize)
    code_layer.dimsize.sum(axis=0, target=code_layer.unitcell)
    loss1 = 0.5 * beta * input_layer.deriv.euclid_norm()**2
    loss2 = 0.5 * alpha * code_layer.deriv.euclid_norm()**2
    loss3 = gamma * code_layer.unitcell.euclid_norm()
    loss4 = loss1 + loss2 + loss3
    err = []
    for l in [loss1, loss2, loss3, loss4]:
      perf = deepnet_pb2.Metrics()
      perf.MergeFrom(code_layer.proto.performance_stats)
      perf.count = self.batchsize
      perf.error = l
      err.append(perf)
    return err

  def UpdateParameters(self, step):
    """Update the encoder and decoder weigths and biases.
    Args:
      step: Time step of training.
    """
    numcases = self.batchsize
    code_layer = self.code_layer
    input_layer = self.input_layer
    encoder = self.encoder
    decoder = self.decoder
    wd = decoder.params['weight']
    bd = input_layer.params['bias']
    z = code_layer.state
    inputs = input_layer.state
    we = encoder.params['weight']
    be = code_layer.params['bias']
    scale = code_layer.params['scale']
    code_approx = code_layer.approximator
    hyp = code_layer.hyperparams
    alpha = hyp.sc_alpha
    beta = hyp.sc_beta
    gamma = hyp.sc_gamma
    enc_hyp = encoder.hyperparams
    dec_hyp = decoder.hyperparams

    # Derivatives for decoder weights.
    deriv = input_layer.deriv
    momentum, epsilon = decoder.GetMomentumAndEpsilon(step)
    wd_delta = self.decoder.grad_weight
    wd_delta.mult(momentum)
    wd_delta.add_dot(z, deriv.T, beta / numcases)
    if dec_hyp.apply_l2_decay:
      wd_delta.add_mult(wd, alpha=dec_hyp.l2_decay)

    # Derivatives for decoder bias.
    momentum, epsilon = input_layer.GetMomentumAndEpsilon(step)
    bd_delta = input_layer.grad_bias
    bd_delta.mult(momentum)
    bd_delta.add_sums(deriv, axis=1, mult=beta / numcases)

    # Derivatives for scale.
    deriv = code_layer.deriv
    code_approx.div_by_col(scale)
    scale_delta = code_layer.grad_scale
    scale_delta.mult(momentum)
    temp = code_layer.temp3
    code_approx.mult(deriv, target=temp)
    scale_delta.add_sums(temp, axis=1, mult=alpha / numcases)

    # Derivatives for encoder weights.
    code_layer.deriv.mult_by_col(scale)
    code_layer.ComputeDeriv(code_approx)  # backprop through non-linearity.
    deriv = code_layer.deriv
    momentum, epsilon = encoder.GetMomentumAndEpsilon(step)
    we_delta = self.encoder.grad_weight
    we_delta.mult(momentum)
    we_delta.add_dot(inputs, deriv.T, alpha / numcases)
    if enc_hyp.apply_l2_decay:
      we_delta.add_mult(we, alpha=enc_hyp.l2_decay)

    # Derivatives for encoder bias.
    momentum, epsilon = code_layer.GetMomentumAndEpsilon(step)
    be_delta = code_layer.grad_bias
    be_delta.mult(momentum)
    be_delta.add_sums(deriv, axis=1, mult=alpha / numcases)

    # Apply the updates.
    scale.add_mult(scale_delta, -epsilon)
    bd.add_mult(bd_delta, -epsilon)
    wd.add_mult(wd_delta, -epsilon)
    be.add_mult(be_delta, -epsilon)
    we.add_mult(we_delta, -epsilon)

    if dec_hyp.apply_weight_norm:
      wd.norm_limit(dec_hyp.weight_norm, axis=0)
    if enc_hyp.apply_weight_norm:
      we.norm_limit(enc_hyp.weight_norm, axis=0)

  def EvaluateOneBatch(self):
    """Evaluate on one mini-batch.
    Args:
      step: Training step.
    """
    self.ForwardPropagate()
    return self.GetLoss()

  def TrainOneBatch(self, step):
    """Train using one mini-batch.
    Args:
      step: Training step.
    """
    """
    if step > self.code_layer.hyperparams.switch_on_sc_alpha_after:
      self.code_layer.hyperparams.sc_alpha = 1.0
    """
    self.ForwardPropagate(train=True)
    losses = self.GetLoss(train=True)
    self.UpdateParameters(step)
    return losses

########NEW FILE########
__FILENAME__ = sparse_code_layer
from layer import *

class SparseCodeLayer(Layer):

  def AllocateBatchsizeDependentMemory(self, batchsize):
    super(SparseCodeLayer, self).AllocateBatchsizeDependentMemory(batchsize)
    self.approximator = cm.empty(self.state.shape)
    self.temp3 = cm.empty(self.state.shape)
    self.grad = cm.empty(self.state.shape)
    self.grad_scale = cm.CUDAMatrix(np.zeros((self.state.shape[0], 1)))
    self.m_by_m = cm.empty((self.state.shape[0], self.state.shape[0]))

  def ApplyActivation(self, state):
    if self.activation == deepnet_pb2.Hyperparams.LOGISTIC:
      cm.sigmoid(state)
    elif self.activation == deepnet_pb2.Hyperparams.TANH:
      cm.tanh(state)
    elif self.activation == deepnet_pb2.Hyperparams.RECTIFIED_LINEAR:
      state.greater_than(0, target=self.temp)
      state.mult(self.temp)
    elif self.activation == deepnet_pb2.Hyperparams.RECTIFIED_LINEAR_SMOOTH:
      cm.log_1_plus_exp(state)
    elif self.activation == deepnet_pb2.Hyperparams.LINEAR:
      pass

  def ComputeDeriv(self, state):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    if self.activation == deepnet_pb2.Hyperparams.LOGISTIC:
      self.deriv.apply_logistic_deriv(state)
    elif self.activation == deepnet_pb2.Hyperparams.TANH:
      self.deriv.apply_tanh_deriv(state)
      if self.hyperparams.dropout:
        self.deriv.mult(self.mask)
    elif self.activation == deepnet_pb2.Hyperparams.RECTIFIED_LINEAR:
      self.deriv.apply_rectified_linear_deriv(state)
    elif self.activation == deepnet_pb2.Hyperparams.RECTIFIED_LINEAR_SMOOTH:
      self.deriv.apply_rectified_linear_smooth_deriv(state)
    elif self.activation == deepnet_pb2.Hyperparams.LINEAR:
      if self.hyperparams.dropout:
        self.deriv.mult(self.mask)
    elif self.activation == deepnet_pb2.Hyperparams.SOFTMAX:
      raise Exception('Not implemented.')
    else:
      raise Exception('Unknown activation.')




########NEW FILE########
__FILENAME__ = tanh_layer
from layer import *

class TanhLayer(Layer):
  def __init__(self, *args, **kwargs):
    super(TanhLayer, self).__init__(*args, **kwargs)

  @classmethod
  def IsLayerType(cls, proto):
    return proto.hyperparams.activation == deepnet_pb2.Hyperparams.TANH

  def ApplyActivation(self):
    cm.tanh(self.state)

  def Sample(self):
    self.state.sample_bernoulli_tanh(target=self.sample)

  def ComputeDeriv(self):
    """Compute derivative w.r.t input given derivative w.r.t output."""
    self.deriv.apply_tanh_deriv(self.state)
    if self.hyperparams.dropout:
      self.deriv.mult(self.mask)

  def GetLoss(self, get_deriv=False, **kwargs):
    """Computes loss.

    Computes the loss function. Assumes target is in self.data and predictions
    are in self.state.
    Args:
      get_deriv: If True, computes the derivative of the loss function w.r.t the
      inputs to this layer and puts the result in self.deriv.
    """
    perf = deepnet_pb2.Metrics()
    perf.MergeFrom(self.proto.performance_stats)
    perf.count = self.batchsize
    if self.loss_function == deepnet_pb2.Layer.SQUARED_LOSS:
      self.state.subtract(self.data, target=self.deriv)
      error = self.deriv.euclid_norm()**2
      perf.error = error
      if get_deriv:
        self.ComputeDeriv()
    else:
      raise Exception('Unknown loss function for tanh units.')
    return perf

  def GetSparsityDivisor(self):
    self.means_temp2.assign(1)
    self.means_temp2.subtract(self.means, target=self.means_temp)
    self.means_temp2.add(self.means)
    self.means_temp2.mult(self.means_temp)
    return self.means_temp2


########NEW FILE########
__FILENAME__ = trainer
from neuralnet import *
from fastdropoutnet import *
from dbm import *
from dbn import *
from sparse_coder import *
from choose_matrix_library import *
import numpy as np
from time import sleep

def LockGPU(max_retries=10):
  for retry_count in range(max_retries):
    board = gpu_lock.obtain_lock_id()
    if board != -1:
      break
    sleep(1)
  if board == -1:
    print 'No GPU board available.'
    sys.exit(1)
  else:
    cm.cuda_set_device(board)
    cm.cublas_init()
  return board

def FreeGPU(board):
  cm.cublas_shutdown()
  #gpu_lock.free_lock(board)

def LoadExperiment(model_file, train_op_file, eval_op_file):
  model = util.ReadModel(model_file)
  train_op = util.ReadOperation(train_op_file)
  eval_op = util.ReadOperation(eval_op_file)
  return model, train_op, eval_op

def CreateDeepnet(model, train_op, eval_op):
  if model.model_type == deepnet_pb2.Model.FEED_FORWARD_NET:
    return NeuralNet(model, train_op, eval_op)
  elif model.model_type == deepnet_pb2.Model.DBM:
    return DBM(model, train_op, eval_op)
  elif model.model_type == deepnet_pb2.Model.DBN:
    return DBN(model, train_op, eval_op)
  elif model.model_type == deepnet_pb2.Model.SPARSE_CODER:
    return SparseCoder(model, train_op, eval_op)
  elif model.model_type == deepnet_pb2.Model.FAST_DROPOUT_NET:
    return FastDropoutNet(model, train_op, eval_op)
  else:
    raise Exception('Model not implemented.')

def main():
  if use_gpu == 'yes':
    board = LockGPU()
  model, train_op, eval_op = LoadExperiment(sys.argv[1], sys.argv[2],
                                            sys.argv[3])
  model = CreateDeepnet(model, train_op, eval_op)
  model.Train()
  if use_gpu == 'yes':
    FreeGPU(board)
  #raw_input('Press Enter.')

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = transfer_edge
from edge import *

class TransferEdge(Edge):
  @classmethod
  def IsEdgeType(cls, proto):
    return proto.hyperparams.shared_prior

  def LoadParams(self, proto, **kwargs):
    super(TransferEdge, self).LoadParams(proto, **kwargs)
    fname = os.path.join(self.prefix, self.hyperparams.shared_prior_file)
    self.shared_prior_cost = self.hyperparams.shared_prior_cost
    sc = np.load(fname).reshape(1, -1)
    self.superclasses = cm.CUDAMatrix(sc)
    self.diff = cm.empty(self.params['weight'].shape)
    self.expanded_prior_mean = cm.empty(self.params['weight'].shape)
    self.prior_mean = cm.empty((self.diff.shape[0], sc.max() +1)) 

  def GetGlobalInfo(self, net):
    pass
    #edge_name = self.hyperparams.shared_prior_edge
    #prior_edge = next(e for e in net.edge if e.name == edge_name)
    #self.prior_mean = prior_edge.params['weight']

  def ApplyL2Decay(self, w_delta, w, lambdaa, step=0, **kwargs):
    if step % 50 == 0:
      w.accumulate_columns(self.superclasses, self.prior_mean, avg=True)
      self.prior_mean.expand(self.superclasses, target=self.expanded_prior_mean)
    diff = self.diff
    w.subtract(self.expanded_prior_mean, target=diff)
    w_delta.add_mult(diff, lambdaa)
    w_delta.add_mult(self.expanded_prior_mean, self.shared_prior_cost)

"""
class TransferEdge(Edge):
  @classmethod
  def IsEdgeType(cls, proto):
    return proto.hyperparams.shared_prior

  def LoadParams(self, proto, **kwargs):
    super(TransferEdge, self).LoadParams(proto, **kwargs)
    fname = os.path.join(self.prefix, self.hyperparams.shared_prior_file)
    self.superclasses = cm.CUDAMatrix(np.load(fname).reshape(1, -1))
    self.diff = cm.empty(self.params['weight'].shape)

  def GetGlobalInfo(self, net):
    edge_name = self.hyperparams.shared_prior_edge
    prior_edge = next(e for e in net.edge if e.name == edge_name)
    self.prior_mean = prior_edge.params['weight']

  def ApplyL2Decay(self, w_delta, w, lambdaa):
    diff = self.diff
    w.expand_and_add(self.prior_mean, self.superclasses, target=diff, mult=-1.0)
    w_delta.add_mult(diff, lambdaa)
"""

########NEW FILE########
__FILENAME__ = util
"""Utility functions for loading/saving models."""

import cPickle as pickle
import deepnet_pb2
import gzip
import numpy as np
import os.path
import shutil
import time
import pdb
from google.protobuf import text_format

def ParameterAsNumpy(param):
  """Converts a serialized parameter string into a numpy array."""
  return np.fromstring(param.mat, dtype='float32').reshape(
    *tuple(param.dimensions))

def NumpyAsParameter(numpy_array):
  """Converts a numpy array into a serialized parameter string."""
  assert numpy_array.dtype == 'float32', 'Saved arrays should be float32.'
  return numpy_array.tostring()

def WriteCheckpointFile(net, t_op, best=False):
  """Writes out the model to disk."""
  ckpt_dir = os.path.join(t_op.checkpoint_prefix, t_op.checkpoint_directory)
  if not os.path.isdir(ckpt_dir):
    os.makedirs(ckpt_dir)
  if best:
    tag = 'BEST'
    checkpoint_file = '%s_%s' % (net.name, tag)
    checkpoint_file = os.path.join(ckpt_dir, checkpoint_file)
    print 'Writing current best model %s' % checkpoint_file
    f = gzip.open(checkpoint_file, 'wb')
    f.write(net.SerializeToString())
    f.close()
  else:
    tag = 'LAST'
    checkpoint_file = '%s_%s' % (net.name, time.strftime('%s'))
    checkpoint_file = os.path.join(ckpt_dir, checkpoint_file)
    print 'Writing checkpoint %s' % checkpoint_file
    f = gzip.open(checkpoint_file, 'wb')
    f.write(net.SerializeToString())
    f.close()
    checkpoint_file_LAST = '%s_%s' % (net.name, tag)
    checkpoint_file_LAST = os.path.join(ckpt_dir, checkpoint_file_LAST)
    shutil.copyfile(checkpoint_file, checkpoint_file_LAST)

  # Save the t_op.
  checkpoint_file_op = '%s_train_op_%s' % (net.name, tag)
  checkpoint_file = os.path.join(ckpt_dir, checkpoint_file_op)
  f = gzip.open(checkpoint_file, 'wb')
  f.write(t_op.SerializeToString())
  f.close()

def ReadOperation(proto_file):
  protoname, ext = os.path.splitext(proto_file)
  proto = deepnet_pb2.Operation()
  if ext == '.pbtxt':
    proto_pbtxt = open(proto_file, 'r')
    text_format.Merge(proto_pbtxt.read(), proto)
  else:
    f = gzip.open(proto_file, 'rb')
    proto.ParseFromString(f.read())
    f.close()
  return proto

def ReadModel(proto_file):
  protoname, ext = os.path.splitext(proto_file)
  proto = deepnet_pb2.Model()
  if ext == '.pbtxt':
    proto_pbtxt = open(proto_file, 'r')
    text_format.Merge(proto_pbtxt.read(), proto)
  else:
    f = gzip.open(proto_file, 'rb')
    proto.ParseFromString(f.read())
    f.close()
  return proto

def WritePbtxt(output_file, pb):
  with open(output_file, 'w') as f:
    text_format.PrintMessage(pb, f)

def ReadData(proto_file):
  protoname, ext = os.path.splitext(proto_file)
  proto = deepnet_pb2.Dataset()
  if ext == '.pbtxt':
    proto_pbtxt = open(proto_file, 'r')
    text_format.Merge(proto_pbtxt.read(), proto)
  else:
    f = open(proto_file, 'rb')
    proto.ParseFromString(f.read())
    f.close()
  return proto

def CopyData(data):
  copy = deepnet_pb2.Dataset.Data()
  copy.CopyFrom(data)
  return copy

def CopyDataset(data):
  copy = deepnet_pb2.Dataset()
  copy.CopyFrom(data)
  return copy

def CopyOperation(op):
  copy = deepnet_pb2.Operation()
  copy.CopyFrom(op)
  return copy

def CopyModel(model):
  copy = deepnet_pb2.Model()
  copy.CopyFrom(model)
  return copy

def CopyLayer(layer):
  copy = deepnet_pb2.Layer()
  copy.CopyFrom(layer)
  return copy

def GetPerformanceStats(stat, prefix=''):
  s = ''
  if stat.compute_cross_entropy:
    s += ' %s_CE: %.3f' % (prefix, stat.cross_entropy / stat.count)
  if stat.compute_correct_preds:
    s += ' %s_Acc: %.3f (%d/%d)' % (
      prefix, stat.correct_preds/stat.count, stat.correct_preds, stat.count)
  if stat.compute_error:
    s += ' %s_E: %.7f' % (prefix, stat.error / stat.count)
  if stat.compute_MAP and prefix != 'T':
    s += ' %s_MAP: %.3f' % (prefix, stat.MAP)
  if stat.compute_prec50 and prefix != 'T':
    s += ' %s_prec50: %.3f' % (prefix, stat.prec50)
  if stat.compute_sparsity:
    s += ' %s_sp: %.3f' % (prefix, stat.sparsity / stat.count)
  return s

def Accumulate(acc, perf):
 acc.count += perf.count
 acc.cross_entropy += perf.cross_entropy
 acc.error += perf.error
 acc.correct_preds += perf.correct_preds
 acc.sparsity += perf.sparsity

def CreateLayer(layer_class, proto, *args, **kwargs):
  for cls in layer_class.__subclasses__():
    if cls.IsLayerType(proto):
      return cls(proto, *args, **kwargs)
    l = CreateLayer(cls, proto, *args, **kwargs)
    if l is not None:
      return l
  return None

def CreateEdge(edge_class, proto, *args, **kwargs):
  for cls in edge_class.__subclasses__():
    if cls.IsEdgeType(proto):
      return cls(proto, *args, **kwargs)
  return edge_class(proto, *args, **kwargs)


def LoadMissing(p1, p2):
  p = p1.__class__()
  p.CopyFrom(p2)
  p.MergeFrom(p1)
  return p

# For Navdeep's data.
def save(fname, var_list, source_dict):
    var_list = [var.strip() for var in var_list.split() if len(var.strip())>0]
    fo = gzip.GzipFile(fname, 'wb')
    pickle.dump(var_list, fo)
    for var in var_list:
        pickle.dump(source_dict[var], fo, protocol=2)
    fo.close()

def load(fname, target_dict, verbose = False):
    fo = gzip.GzipFile(fname, 'rb')
    var_list = pickle.load(fo)
    if verbose:
        print var_list
    for var in var_list:
        target_dict[var] = pickle.load(fo)
    fo.close()

########NEW FILE########
__FILENAME__ = visualize
import numpy as np
import cPickle as pickle
import matplotlib.pyplot as plt
plt.ion()

fig_id = 0
def GetFigId():
  globals()['fig_id'] += 1
  return globals()['fig_id'] - 1

def show_model_state(model, step):
  for i, node in enumerate(model.node_list):
    dims = int(np.floor(np.sqrt(node.state.shape[0])))
    display_w(node.sample.asarray(), dims, 10, 10, i, title=node.name)


def show(mat, fig=1, title=''):
  plt.figure(fig)
  plt.clf()
  plt.imshow(mat, interpolation='nearest')
  plt.suptitle(title)
  plt.colorbar()
  plt.draw()

def scatter(Y, s=20, c='b', fig=1):
  plt.figure(fig)
  plt.clf()
  plt.scatter(Y[:,0], Y[:,1], s, c)
  plt.draw()

def show_hist(mat, fig):
  plt.figure(fig)
  plt.clf()
  plt.hist(mat.flatten(), 100)
  plt.draw()

def show_stats(edge, fig, title):
  plt.figure(fig)
  plt.clf()
  plt.suptitle(title)
  plt.hist(edge.params['weight'].asarray().flatten(), 100)
  plt.draw()

def display_hidden(state, fig, title, log=False, prob=True):
  plt.figure(fig)
  plt.clf()
  plt.suptitle(title)
  plt.subplot(1, 3, 1)
  plt.hist(state.mean(axis=1), 100)
  if prob:
    plt.xlim([0, 1])
  plt.title('Mean Activation')
  plt.subplot(1, 3, 2)
  plt.hist(state.flatten(), 100, log=log)
  if prob:
    plt.xlim([-0.1, 1.1])
  plt.title('Activation')
  plt.subplot(1, 3, 3)
  plt.imshow(state, cmap = plt.cm.gray, interpolation='nearest', vmax=1, vmin=0)
  plt.title('State')
  plt.draw()

def display_wsorted(w, s, r, c, fig, vmax=None, vmin=None, dataset='mnist',
                    title='weights_sorted'):

  if dataset == 'norb':
    numvis = 4096
  else:
    numvis = w.shape[0]
  numhid = w.shape[1]
  sc = s
  sr = numvis/s
  padding = numhid - r*c
  if isinstance(w, np.ndarray):
    w = w.T[:, :sr*sc]
  else:
    w = w.asarray().T[:, :sr*sc]

  vh = w.reshape(sr*numhid, sc)
  pvh = np.zeros((sr, sc, r, c))
  pvh2 = np.zeros((sr*r, sc*c))
  norm_list = []
  for i in range(r):
    for j in range(c):
      pvh[:,:, i, j] = vh[ (i*c+j)*sr : (i*c+j+1)*sr ,:]
      norm = (pvh[:,:,i,j]**2).sum()
      norm_list.append((norm, i, j))
  norm_list.sort(reverse = True)
  index = 0
  for norm, i, j in norm_list:
    ii = index/c
    jj = index%c
    pvh2[ii*sr:(ii+1)*sr , jj*sc:(jj+1)*sc] = pvh[:,:,i,j]
    index+=1
  plt.figure(fig)
  plt.clf()

  plt.suptitle(title)
  # vmax = 0.5
  # vmin = -0.5
  plt.imshow(pvh2, cmap = plt.cm.gray, interpolation = 'nearest', vmax=vmax, vmin=vmin)
  scale = 1
  xmax = sc*c
  ymax = sr*r
  color = 'k'
  for x in range(0,c):
    plt.axvline(x=x*sc/scale,ymin=0,ymax=ymax/scale, color = color)
  for y in range(0,r):
    plt.axhline(y=y*sr/scale, xmin=0,xmax=xmax/scale, color = color)
  plt.draw()

  return pvh

def display_w(w, s, r, c, fig, vmax=None, vmin=None, dataset='mnist', title='weights'):

  if dataset == 'norb':
    numvis = 4096
  else:
    numvis = w.shape[0]
  numhid = w.shape[1]
  sc = s
  sr = numvis/s
  if isinstance(w, np.ndarray):
    vh = w.T[:,:sr*sc].reshape(sr*numhid, sc)
  else:
    vh = w.asarray().T[:,:sr*sc].reshape(sr*numhid, sc)
  pvh = np.zeros((sr*r, sc*c))
  for i in range(r):
    for j in range(c):
      pvh[i*sr:(i+1)*sr , j*sc:(j+1)*sc] = vh[ (i*c+j)*sr : (i*c+j+1)*sr ,:]
  plt.figure(fig)
  plt.clf()
  plt.title(title)
  plt.imshow(pvh, cmap = plt.cm.gray, interpolation = 'nearest', vmax=vmax, vmin=vmin)
  scale = 1
  xmax = sc*c
  ymax = sr*r
  color = 'k'
  if r > 1:
    for x in range(0,c):
      plt.axvline(x=x*sc/scale, ymin=0,ymax=ymax/scale, color = color)
  if c > 1:
    for y in range(0,r):
      plt.axhline(y=y*sr/scale, xmin=0,xmax=xmax/scale, color = color)
  plt.draw()

  return pvh

def display_convw2(w, s, r, c, fig, title='conv_filters'):
  """w: num_filters X sizeX**2 * num_colors."""
  num_f, num_d = w.shape
  assert s**2 * 3 == num_d
  pvh = np.zeros((s*r, s*c, 3))
  for i in range(r):
    for j in range(c):
      pvh[i*s:(i+1)*s, j*s:(j+1)*s, :] = w[i*c + j, :].reshape(3, s, s).T
  mx = pvh.max()
  mn = pvh.min()
  pvh = 255*(pvh - mn) / (mx-mn)
  pvh = pvh.astype('uint8')
  plt.figure(fig)
  plt.suptitle(title)
  plt.imshow(pvh, interpolation="nearest")
  scale = 1
  xmax = s * c
  ymax = s * r
  color = 'k'
  for x in range(0, c):
    plt.axvline(x=x*s/scale, ymin=0, ymax=ymax/scale, color=color)
  for y in range(0, r):
    plt.axhline(y=y*s/scale, xmin=0, xmax=xmax/scale, color=color)
  plt.draw()
  return pvh

def display_convw(w, s, r, c, fig, vmax=None, vmin=None, dataset='mnist', title='conv_filters'):

  """
  w2 = np.zeros(w.shape)
  d = w.shape[1]/3
  print w.shape
  for i in range(w.shape[0]):
    for j in range(w.shape[1]/3):
      w2[i, j] = w[i, 3*j]
      w2[i, j + d] = w[i, 3*j+1]
      w2[i, j + 2*d] = w[i, 3*j+2]
  w = w2
  """

  numhid = w.shape[0]
  size_x = s
  size_y = s    # For now.
  num_channels = w.shape[1] / (size_x*size_y)
  assert num_channels == 3
  assert w.shape[1] % size_x*size_y == 0
  if isinstance(w, np.ndarray):
    vh = w.reshape(size_x*numhid*num_channels, size_y)
  else:
    vh = w.asarray().reshape(size_x*numhid*num_channels, size_y)
  pvh = np.zeros((size_x*r, size_y*c, num_channels))
  for i in range(r):
    for j in range(c):
      for ch in range(num_channels):
        pvh[i*size_x:(i+1)*size_x, j*size_y:(j+1)*size_y, ch] = \
            vh[(num_channels*(i*c+j)+ch)*size_x:(num_channels*(i*c+j)+ch+1)*size_x,:]

  # pvh /= np.std(pvh)
  plt.figure(fig)
  plt.clf()
  plt.title(title)
  plt.imshow(pvh, vmax=vmax, vmin=vmin)
  scale = 1
  xmax = size_x*c
  ymax = size_y*r
  color = 'k'
  for x in range(0, c):
    plt.axvline(x=x*size_x/scale, ymin=0,ymax=ymax/scale, color = color)
  for y in range(0, r):
    plt.axhline(y=y*size_y/scale, xmin=0,xmax=xmax/scale, color = color)
  plt.draw()

  return pvh

########NEW FILE########
__FILENAME__ = write_model_to_mat
"""Write a model protocol buffer to mat file."""
from deepnet import util
import numpy as np
import sys
import scipy.io

def Convert(model_file, output_file):
  model = util.ReadModel(model_file)
  params = {}
  for l in model.layer:
    for p in l.param:
      params['%s_%s' % (l.name, p.name)] = util.ParameterAsNumpy(p)
  for e in model.edge:
    for p in e.param:
      params['%s_%s_%s' % (e.node1, e.node2, p.name)] = util.ParameterAsNumpy(p)

  scipy.io.savemat(output_file, params, oned_as='column')

if __name__ == '__main__':
  Convert(sys.argv[1], sys.argv[2])


########NEW FILE########
__FILENAME__ = eigenmat
import os, pdb, platform, time, warnings
import ctypes as ct
import numpy as np

if platform.system() == 'Windows':
  _eigenmat = ct.cdll.LoadLibrary('libeigenmat.dll')
elif platform.system() == 'Darwin':
  _eigenmat = ct.cdll.LoadLibrary('libeigenmat.dylib')
else:
  _eigenmat = ct.cdll.LoadLibrary('libeigenmat.so')

_eigenmat.euclid_norm.restype = ct.c_float
_eigenmat.vdot.restype = ct.c_float
_eigenmat.sum_all.restype = ct.c_float

def deprecated(func):
  """This is a decorator which can be used to mark functions
  as deprecated. It will result in a warning being emmitted
  when the function is used."""

  def newFunc(*args, **kwargs):
    warnings.warn("Call to deprecated function %s." % func.__name__,
           category=DeprecationWarning)
    return func(*args, **kwargs)
  newFunc.__name__ = func.__name__
  newFunc.__doc__ = func.__doc__
  newFunc.__dict__.update(func.__dict__)
  return newFunc

class EigenMatException(Exception):
  pass

def get_last_cuda_error():
  return str(_eigenmat.get_last_cuda_error())

def generate_exception(err_code):
  """
  Return a EigenMatException object based on the error code err_code.
  """

  if err_code == -1:
    return EigenMatException("Incompatible matrix dimensions.")
  elif err_code == -2:
    return EigenMatException("CUBLAS error.")
  elif err_code == -3:
    return EigenMatException("CUDA error: " + get_last_cuda_error())
  elif err_code == -4:
    return EigenMatException("Operation not supported on views.")
  elif err_code == -5:
    return EigenMatException("Operation not supported on transposed matrices.")
  elif err_code == -6:
    return EigenMatException("")
  elif err_code == -7:
    return EigenMatException("Incompatible transposedness.")
  elif err_code == -8:
    return EigenMatException("Matrix is not in device memory.")
  elif err_code == -9:
    return EigenMatException("Operation not supported.")
    

class eigenmat(ct.Structure):
  _fields_ = [('data', ct.POINTER(ct.c_float)),
        ('size', ct.c_int * 2),
        ('is_trans', ct.c_int),
        ('owns_data', ct.c_int)]

class rnd_struct(ct.Structure):
  _fields_ = [('seed', ct.c_ulong),
        ('kn', ct.c_int * 128),
        ('fn', ct.c_float * 128),
        ('wn', ct.c_float * 128)]


class TransposedEigenMatrix(object):
  def __init__(self, mat):
    self.mat = eigenmat()
    ct.memmove(ct.pointer(self.mat), ct.pointer(mat), ct.sizeof(self.mat))
    self.mat.is_trans = 1
    self.p_mat = ct.pointer(self.mat)
    self.T = mat

class EigenMatrix(object):
  """
  A EigenMatrix object represents a matrix of single precision floating point
  numbers on a GPU.
  """

  def overwrite(self, array):
    """Overwrites self with array.
    
    'array' should have a size smaller than that of the array used to
    initialize the EigenMatrix. The method will not throw an Exception just
    yet if this is not true. It will throw exceptions or behave in strange
    ways later on.
    """
    assert type(array) == np.ndarray, 'array must be a np.ndarray.'
    array = reformat(array)
    self.numpy_array = array
    _eigenmat.init_from_array(self.p_mat, array.ctypes.data_as(ct.POINTER(ct.c_float)), ct.c_int(array.shape[0]), ct.c_int(array.shape[1]))

  def __init__(self, array, **kwargs):
    """
    Initializes a new matrix object in one of two ways. If array is a numpy
    ndarray, memory for a matrix with the same dimensions is allocated on
    the GPU. If the copy_to_device flag is set to True, the GPU matrix is
    initialized with the given ndarray. If array is not an ndarray, it must
    be a eigenmat structure (typically the user will never use this way of
    calling __init__).
    """

    if type(array) == np.ndarray:
      # Convert array to float32 in FORTRAN order
      array = reformat(array)

      # Initialize as a ndarray-tied matrix.
      self.mat = eigenmat()
      self.size = self.mat.size
      self.p_mat = ct.pointer(self.mat)
      self.numpy_array = array

      _eigenmat.init_from_array(self.p_mat, array.ctypes.data_as(ct.POINTER(ct.c_float)), ct.c_int(array.shape[0]), ct.c_int(array.shape[1]))
    else:
      # Initialize based on existing eigenmat structure.
      self.mat = array
      self.p_mat = ct.pointer(self.mat)
    self.T = TransposedEigenMatrix(self.mat)

  @staticmethod
  def init_random(seed=0):
    """
    Initialize and seed the random number generator.
    """
    assert seed >= 0, "Seed must be a non-negative integer."
    EigenMatrix.rnd_state = rnd_struct()
    EigenMatrix.rnd_state_p = ct.pointer(EigenMatrix.rnd_state)
    _eigenmat.init_random(EigenMatrix.rnd_state_p, ct.c_int(seed+1))
 

  @property
  def shape(self):
    return (self.mat.size[0], self.mat.size[1])

  def set_shape(self, shape):
    """
    Sets the shape of the array to the given array.
    Highly unsafe method. Does no checking.
    Do not use this unless you know what you are doing.
    """

    m = ct.c_uint(shape[0])
    n = ct.c_uint(shape[1])

    err_code = _eigenmat.set_shape(self.p_mat, m, n)
    if err_code:
      raise generate_exception(err_code)

    return self

  def reshape(self, shape):
    """
    Reshapes self to have the given shape. The number of elements cannot
    change as this only changes how the contents are interpreted.
    """

    m = ct.c_uint(shape[0])
    n = ct.c_uint(shape[1])

    err_code = _eigenmat.reshape(self.p_mat, m, n)
    if err_code:
      raise generate_exception(err_code)

    return self

  def blockify(source, blocksize, target=None):
    if target == None:
      target = source

    err_code = _eigenmat.blockify(source.p_mat, target.p_mat, ct.c_uint(blocksize))

    if err_code:
      raise generate_exception(err_code)

    return target

  def generate_translations(source, source_w, target_w, off_x, off_y, target=None):
    num_channels = source.shape[0] / (source_w**2)

    if target == None:
      batch_s = source.shape[1]
      target = empty((target_w**2, batch_s))

    err_code = _eigenmat.generate_translations_big_var_off(source.p_mat, target.p_mat, off_x.p_mat, off_y.p_mat, ct.c_uint(source_w), ct.c_uint(target_w), ct.c_uint(num_channels))

    if err_code:
      raise generate_exception(err_code)

    return target

  def asarray(self):
    """
    Copies the matrix to an ndarray on the CPU and returns it.
    """
    return self.numpy_array

  def copy_to_device(self):
    """
    Copy the matrix to the GPU.
    """
    pass

  def copy_to_host(self):
    """
    Copy the matrix to the CPU.
    """
    pass

  def assign(self, val):
    """Assign val to self, where val can be a scalar or a EigenMatrix
    with the same dimensions as self. """

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.copy_on_device(val.p_mat, self.p_mat)
    elif isinstance(val, (int, float)):
      err_code = _eigenmat.assign_scalar(self.p_mat, ct.c_float(val))
    else:
      raise ValueError, "Assigned value must be of type EigenMatrix, int, or float."
      
    if err_code:
      raise generate_exception(err_code)

    return self

  def free_device_memory(self):
    """
    Free memory used up by the matrix on the GPU.
    """
    pass

  def set_trans(self, is_trans):
    """
    Set the transposedness flag to is_trans.
    """
    _eigenmat.set_transpose(self.p_mat, ct.c_int(1 * is_trans))

  def slice(self, first_col, last_col):
    mat = eigenmat()

    if self.mat.size[0] == 1 or self.mat.size[1] == 1:
      err_code = _eigenmat.get_vector_slice(self.p_mat, ct.pointer(mat), ct.c_int(first_col), ct.c_int(last_col))
    else:
      err_code = _eigenmat.get_slice(self.p_mat, ct.pointer(mat), ct.c_int(first_col), ct.c_int(last_col))

    if err_code:
      raise generate_exception(err_code)

    new_mat = EigenMatrix(mat)

    try:
      new_mat.sliceof = self.sliceof
    except:
      new_mat.sliceof = self

    return new_mat

  def get_col_slice(self, first_col, last_col, target=None):
    col_slice = self.slice(first_col, last_col)

    if target:
      target.assign(col_slice)
      return target
    else:
      return col_slice

  def set_col_slice(self, first_col, last_col, mat):
    self.slice(first_col, last_col).assign(mat)

    return self

  def get_row_slice(self, start, end, target=None):
    """
    Get the rows with indices start through end. If target is not provided
    memory for a new matrix will be allocated.
    """

    width = self.shape[1]

    if not target:
      target = empty((end-start, width))

    err_code = _eigenmat.get_row_slice(self.p_mat, target.p_mat, ct.c_int(start), ct.c_int(end))
    if err_code:
      raise generate_exception(err_code)

    return target

  def set_row_slice(self, start, end, mat):
    """
    Assign the contents of mat to the rows with indices start through end.
    """

    err_code = _eigenmat.set_row_slice(mat.p_mat, self.p_mat, ct.c_int(start), ct.c_int(end))
    if err_code:
      raise generate_exception(err_code)

    return self

  def transpose(self, target=None):
    """
    Return a transposed copy of the matrix.
    """
    if not target:
      target = empty((self.shape[1], self.shape[0]))

    err_code = _eigenmat.copy_transpose(self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target

  def fill_with_rand(self):
    """
    Fill matrix on the GPU with random numbers drawn from the uniform
    distribution over the (0,1) interval.
    """

    err_code = _eigenmat.fill_with_rand(EigenMatrix.rnd_state_p, self.p_mat) 
    if err_code:
      raise generate_exception(err_code)

    return self

  def fill_with_randn(self):
    """
    Fill matrix on the GPU with random numbers drawn from the standard normal
    distribution.
    """

    err_code = _eigenmat.fill_with_randn(EigenMatrix.rnd_state_p, self.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return self

  def dropout(self, dropprob, val=0.0):
    """
    Drop entries in this matrix uniformly randomly with given probability
    and set the dropped out unit to state val.
    """
    err_code = _eigenmat.dropout(EigenMatrix.rnd_state_p, self.p_mat,
                  ct.c_float(dropprob), ct.c_float(val))
    if err_code:
      raise generate_exception(err_code)

    return self

  def sample_bernoulli(self, target=None):
    """
    Sample a bernoulli distribution. Choose 1 with probability given by entries of self, 0 otherwise.
    """
    if not target:
     target = self
    err_code = _eigenmat.sample_bernoulli(EigenMatrix.rnd_state_p, self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return self

  def sample_bernoulli_tanh(self, target=None):
    """
    Sample a bernoulli distribution. Choose 1 with probability given by entries of (1+self)/2, -1 otherwise.
    """
    if not target:
     target = self
    err_code = _eigenmat.sample_bernoulli_tanh(EigenMatrix.rnd_state_p, self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return self

  def sample_poisson(self, target=None):
    """
    Sample a poisson distribution. Choose 1 with probability given by entries of self.
    Not implemented yet.
    """
    if not target:
     target = self
    err_code = _eigenmat.sample_poisson(EigenMatrix.rnd_state_p, self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return self

  def sample_gaussian(self, mult=1.0, target=None):
    """
    Add zero mean gaussian noise to the matrix. mult is the stddev.
    """
    if not target:
     target = self
    err_code = _eigenmat.sample_gaussian(EigenMatrix.rnd_state_p, self.p_mat, target.p_mat, ct.c_float(mult))
    if err_code:
      raise generate_exception(err_code)

    return self

  def perturb_energy_for_softmax_sampling(self, target=None):
    """
    Add by -log(-log(rand)).
    """
    if not target:
     target = self
    err_code = _eigenmat.perturb_energy(EigenMatrix.rnd_state_p, self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return self

  def perturb_prob_for_softmax_sampling(self, target=None):
    """
    Divide by -log(rand).
    """
    if not target:
     target = self
    err_code = _eigenmat.perturb_prob(EigenMatrix.rnd_state_p, self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return self


  def add_col_vec(self, vec, target=None):
    """
    Add vector vec to every column of the matrix. If a target is provided,
    it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.add_col_vec(self.p_mat, vec.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target
    
  def add_col_mult(self, vec, mult, target=None):
    """
    Add a multiple of vector vec to every column of the matrix. If a target
    is provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.add_col_mult(self.p_mat, vec.p_mat, target.p_mat, ct.c_float(mult))
    if err_code:
      raise generate_exception(err_code)

    return target

  def add_mult_sign(self, mat2, mult = 1.):
    """
    Add multiple of sign of mat2 to the matrix.
    """

    err_code = _eigenmat.add_mult_sign(self.p_mat, mat2.p_mat, ct.c_float(mult))
    if err_code:
      raise generate_exception(err_code)

    return self

  def mult_diagonal(self, val, target=None):
    """
    Mult val to the diagonal of self. If a target
    is provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    assert self.shape[0] == self.shape[1], 'self must be a square matrix'
    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.mult_diagonal(self.p_mat, val.p_mat, target.p_mat)
    elif isinstance(val, (int, float)):
      err_code = _eigenmat.mult_diagonal_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix, int, or float."

    if err_code:
      raise generate_exception(err_code)

    return target



  def add_diagonal(self, val, target=None):
    """
    Add val to the diagonal of self. If a target
    is provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    assert self.shape[0] == self.shape[1], 'self must be a square matrix'
    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.add_diagonal(self.p_mat, val.p_mat, target.p_mat)
    elif isinstance(val, (int, float)):
      err_code = _eigenmat.add_diagonal_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix, int, or float."

    if err_code:
      raise generate_exception(err_code)

    return target


  def add_row_mult(self, vec, mult, target=None):
    """
    Add a multiple of vector vec to every row of the matrix. If a target
    is provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.add_row_mult(self.p_mat, vec.p_mat, target.p_mat, ct.c_float(mult))
    if err_code:
      raise generate_exception(err_code)

    return target
    
  def add_row_vec(self, vec, target=None):
    """
    Add vector vec to every row of the matrix. If a target is provided,
    it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.add_row_vec(self.p_mat, vec.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target
    
  def mult_by_col(self, vec, target=None):
    """
    Multiply vector vec into every column of the matrix. If a target is
    provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.mult_by_col_vec(self.p_mat, vec.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target
    
  def mult_by_row(self, vec, target=None):
    """
    Multiply vector vec into every row of the matrix. If a target is
    provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.mult_by_row_vec(self.p_mat, vec.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target

  def div_by_col(self, vec, target=None):
    """
    Multiply vector vec into every column of the matrix. If a target is
    provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.div_by_col_vec(self.p_mat, vec.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target
    
  def div_by_row(self, vec, target=None):
    """
    Divide vector vec into every row of the matrix. If a target is
    provided, it is used to store the result instead of self.
    """

    if not target:
      target = self

    err_code = _eigenmat.div_by_row_vec(self.p_mat, vec.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target
 
  def sum(self, axis=None, target = None):
    """
    Sum the matrix along the given dimension, where 0 represents the leading
    dimension and 1 represents the non-leading dimension. If None, the sum
    of all elements is returned. If a target is not prvided, a new vector is
    created for storing the result.
    """
    if axis is None:
     return _eigenmat.sum_all(self.p_mat)
    else:
     return sum(self, axis, target)


  def add_sums(self, mat, axis, mult = 1.):
    """
    Add a multiple of the sums of the matrix mat along the given dimension
    to self. 
    """

    m = _eigenmat.get_leading_dimension(mat.p_mat)
    n = _eigenmat.get_nonleading_dimension(mat.p_mat)

    err_code = _eigenmat.add_sum_by_axis(mat.p_mat, self.p_mat, ct.c_int(axis), ct.c_float(mult))
    if err_code:
      raise generate_exception(err_code)

    return self

  def less_than(self, val, target=None):
    """
    Perform the operation target = 1. * (self < val), where val can be a matrix or a scalar.
    """

    if not target:
      target = self

    if isinstance(val, (int, float)):
      err_code = _eigenmat.less_than_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      err_code = _eigenmat.less_than(self.p_mat, val.p_mat, target.p_mat)

    if err_code:
      raise generate_exception(err_code)

    return target

  def greater_than(self, val, target=None):
    """
    Perform the operation target = 1. * (self > val), where val can be a matrix or a scalar.
    """

    if not target:
      target = self

    if isinstance(val, (int, float)):
      err_code = _eigenmat.greater_than_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      err_code = _eigenmat.greater_than(self.p_mat, val.p_mat, target.p_mat)

    if err_code:
      raise generate_exception(err_code)

    return target

  def upper_bound(self, val, target=None):
    """
    Perform the operation target = (self > val) ? val:self, where val can be a matrix or a scalar.
    """
    if not target:
      target = self

    if isinstance(val, (int, float)):
      err_code = _eigenmat.upper_bound_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      err_code = _eigenmat.upper_bound(self.p_mat, val.p_mat, target.p_mat)

    if err_code:
      raise generate_exception(err_code)

    return target


  def lower_bound(self, val, target=None):
    """
    Perform the operation target = (self < val) ? val:self, where val can be a matrix or a scalar.
    """
    if not target:
      target = self

    if isinstance(val, (int, float)):
      err_code = _eigenmat.lower_bound_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      err_code = _eigenmat.lower_bound(self.p_mat, val.p_mat, target.p_mat)

    if err_code:
      raise generate_exception(err_code)

    return target

  def cumsum(self, axis, temp=None, target=None):
    """
    Cumulative sum along axis.
    """

    m, n = self.shape
    assert axis == 0, 'axis = 1 not implemented.'
    if not target:
      target = empty((m, n))
    if not temp:
      temp = empty((m, n))
    """ 
    elif axis == 1:
      if not target:
        target = empty((m, 1))
    """ 

    err_code = _eigenmat.cumsum_by_axis(self.p_mat, target.p_mat, temp.p_mat, ct.c_int(axis))
    if err_code:
      raise generate_exception(err_code)

    return target

  def choose_max_and_accumulate(self, acc):
    """
    Find the maximum value along the given dimension, where 0 represents the
    leading dimension and 1 represents the non-leading dimension. If a target
    is not prvided, a new vector is created for storing the result.
    """

    m, n = self.shape

    err_code = _eigenmat.choose_max_and_accumulate(self.p_mat, acc.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return acc


  def choose_max(self, axis, target=None):
    """
    Find the maximum value along the given dimension, where 0 represents the
    leading dimension and 1 represents the non-leading dimension. If a target
    is not prvided, a new vector is created for storing the result.
    """

    m, n = self.shape

    assert axis == 0, 'Axis = 1 not implemented.'
    if not target:
     target = self

    err_code = _eigenmat.choose_max_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
    if err_code:
      raise generate_exception(err_code)

    return target


  def max(self, axis, target=None):
    """
    Find the maximum value along the given dimension, where 0 represents the
    leading dimension and 1 represents the non-leading dimension. If a target
    is not prvided, a new vector is created for storing the result.
    """

    m, n = self.shape

    if axis == 0:
      if not target:
        target = empty((1, n))
 
    elif axis == 1:
      if not target:
        target = empty((m, 1))

    err_code = _eigenmat.max_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
    if err_code:
      raise generate_exception(err_code)

    return target

  def argmax(self, axis, target=None):
    """
    Find the index with the maximum value along the given dimension, where 0 represents the
    leading dimension and 1 represents the non-leading dimension. If a target
    is not prvided, a new vector is created for storing the result.
    """

    m, n = self.shape

    if axis == 0:
      if not target:
        target = empty((1, n))
 
    elif axis == 1:
      if not target:
        target = empty((m, 1))

    err_code = _eigenmat.argmax_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
    if err_code:
      raise generate_exception(err_code)

    return target


  def sqsum(self, axis, target=None):
    """
    Find the sum of squares along the given dimension, where 0 represents the
    leading dimension and 1 represents the non-leading dimension. If a target
    is not prvided, a new vector is created for storing the result.
    """

    m, n = self.shape

    if axis == 0:
      if not target:
        target = empty((1, n))
 
    elif axis == 1:
      if not target:
        target = empty((m, 1))

    err_code = _eigenmat.sqsum_by_axis(self.p_mat, target.p_mat, ct.c_int(axis))
    if err_code:
      raise generate_exception(err_code)

    return target

  def norm_limit(self, norm, axis, target=None):
    """
    Limit the norm along the given dimension to be 'norm', where 0
    represents the leading dimension and 1 represents the non-leading
    dimension. If a target is not provided, self is used as target.
    """
    m, n = self.shape

    if axis == 0:
      if not target:
        target = self
 
    elif axis == 1:
      if not target:
        target = self

    err_code = _eigenmat.normlimit_by_axis(self.p_mat, target.p_mat,
                        ct.c_int(axis), ct.c_float(norm))
    if err_code:
      raise generate_exception(err_code)

    return target

  def sign(self, target=None):
    """
    Find the sign of each element of the matrix.
    """

    if not target:
      target = empty((self.mat.size[0], self.mat.size[1]))

    err_code = _eigenmat.sign(self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target

  def apply_cos(self, target=None):
    """
    Apply the cos sigmoid to each element of the matrix.
    """

    return cos(self, target)

  def apply_sin(self, target=None):
    """
    Apply the sin sigmoid to each element of the matrix.
    """

    return sin(self, target)

  def apply_sigmoid(self, target=None):
    """
    Apply the logistic sigmoid to each element of the matrix.
    """

    return sigmoid(self, target)

  def apply_softmax(self, target=None):
    """
    Apply softmax activation. Each column is taken as one softmax.
    """
    return softmax(self, target)


  def reciprocal(self, target=None):
    """
    Find the reciprocal of each element of the matrix.
    """

    if not target:
      target = self

    err_code = _eigenmat.reciprocal(self.p_mat, target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target

  def dot(self, mat2, mult=1.0, target=None):
    """
    Multiply the matrix by mat2 from the right and multiply by scalar mult.
    """

    return dot(self, mat2, mult, target)

  def add_dot(self, m1, m2, mult=1.0):
    """
    Add the dot product of m1 and m2 to the matrix.
    """

    err_code = _eigenmat.dot(m1.p_mat, m2.p_mat, self.p_mat, ct.c_float(1.), ct.c_float(mult))
    if err_code:
      raise generate_exception(err_code)

    return self

  def subtract_dot(self, m1, m2):
    """
    Subtract the dot product of m1 and m2 from the matrix.
    """

    err_code = _eigenmat.dot(m1.p_mat, m2.p_mat, self.p_mat, ct.c_float(1.), ct.c_float(-1.))
    if err_code:
      raise generate_exception(err_code)

    return self

  def add_mult(self, mat2, alpha = 1.):
    """
    Add multiple of mat2 to the matrix.
    """

    err_code = _eigenmat.add_mult(self.p_mat, mat2.p_mat, ct.c_float(alpha))
    if err_code:
      raise generate_exception(err_code)

    return self
  
  def subtract_mult(self, mat2, alpha = 1.):
    """
    Subtract a multiple of mat2 from the matrix.
    """

    err_code = _eigenmat.add_mult(self.p_mat, mat2.p_mat, ct.c_float(-1. * alpha))
    if err_code:
      raise generate_exception(err_code)

    return self

  def add(self, val, target=None):
    """Add val to self, where val can be a scalar or a EigenMatrix with the
    same dimensions as self. """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.add_elementwise(self.p_mat, val.p_mat, target.p_mat)
    elif isinstance(val, (int, float)):
      err_code = _eigenmat.add_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix, int, or float."

    if err_code:
      raise generate_exception(err_code)

    return target

  def subtract(self, val, target=None):
    """Subtract val from self, where val can be a scalar or a EigenMatrix with
    the same dimensions as self. """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.subtract_elementwise(self.p_mat, val.p_mat, target.p_mat)
    elif isinstance(val, (int, float)):
      err_code = _eigenmat.add_scalar(self.p_mat, ct.c_float(-1*val), target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix, int, or float."

    if err_code:
      raise generate_exception(err_code)

    return target

  def divide(self, val, target=None):
    """Divide self by val, where val can be a scalar or a EigenMatrix with the
    same dimensions as self. """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.divide_elementwise(self.p_mat, val.p_mat, target.p_mat)
    elif isinstance(val, (int, float)):
      err_code = _eigenmat.divide_by_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix, int, or float."

    if err_code:
      raise generate_exception(err_code)

    return target

  def mult(self, val, target=None):
    """Multiply self by val, where val can be a scalar or a EigenMatrix with
    the same dimensions as self. """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.mult_elementwise(self.p_mat, val.p_mat, target.p_mat)
    elif isinstance(val, (int, float)):
      err_code = _eigenmat.mult_by_scalar(self.p_mat, ct.c_float(val), target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix, int, or float."

    if err_code:
      raise generate_exception(err_code)

    return target

  def apply_cos_deriv(self, val, target=None):
    """
    Apply cos derivative, where val is the activation of cos units.
    """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.apply_cos_deriv(self.p_mat, val.p_mat, target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target


  def apply_sin_deriv(self, val, target=None):
    """
    Apply sin derivative, where val is the activation of sin units.
    """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.apply_sin_deriv(self.p_mat, val.p_mat, target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target


  def apply_logistic_deriv(self, val, target=None):
    """
    Apply logistic derivative, where val is the activation of logistic units.
    """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.apply_logistic_deriv(self.p_mat, val.p_mat, target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target

  def apply_tanh_deriv(self, val, target=None):
    """
    Apply tanh derivative, where val is the activation of the units.
    """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.apply_tanh_deriv(self.p_mat, val.p_mat, target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target

  def apply_rectified_linear_deriv(self, val, target=None):
    """
    Apply rectified linear derivative, where val is the activation of the units.
    """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.apply_rectified_linear_deriv(self.p_mat, val.p_mat, target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target

  def apply_rectified_linear_smooth_deriv(self, val, target=None):
    """
    Apply rectified linear smooth derivative, where val is the activation of the units.
    """

    if not target:
      target = self

    if isinstance(val, EigenMatrix):
      err_code = _eigenmat.apply_rectified_linear_smooth_deriv(self.p_mat, val.p_mat, target.p_mat)
    else:
      raise ValueError, "Value must be of type EigenMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target

  @deprecated
  def assign_scalar(self, alpha):
    """
    Assign scalar alpha to every element of the matrix.
    """

    err_code = _eigenmat.assign_scalar(self.p_mat, ct.c_float(alpha))
    if err_code:
      raise generate_exception(err_code)

    return self

  @deprecated
  def mult_by_scalar(self, alpha, target=None):
    """
    Multiply the matrix by a scalar.
    """

    if not target:
      target = self

    err_code = _eigenmat.mult_by_scalar(self.p_mat, ct.c_float(alpha), target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target


  @deprecated
  def div_by_scalar(self, alpha, target=None):
    """
    Divide the matrix by a scalar.
    """

    if not target:
      target = self

    err_code = _eigenmat.divide_by_scalar(self.p_mat, ct.c_float(alpha), target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target

  @deprecated
  def add_scalar(self, alpha, target=None):
    """
    Increment the matrix by a scalar.
    """

    if not target:
      target = self

    err_code = _eigenmat.add_scalar(self.p_mat, ct.c_float(alpha), target.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return target

  def sum_all(self):
    err_code = ct.c_int(0)
    res = _eigenmat.sum_all(self.p_mat)

    if err_code:
      raise generate_exception(err_code.value, ct.byref(err_code))

    return res

  def euclid_norm(self):
    err_code = ct.c_int(0)
    res = _eigenmat.euclid_norm(self.p_mat, ct.byref(err_code))

    if err_code:
      raise generate_exception(err_code.value)

    return res

  def select_columns(self, indices, target):
    """
    copies some columns of self into target.
    <indices> must be a row vector. Its elements are float32's representing integers, e.g. "34.0" means the integer "34".
    after this call, for all r,c, target[r,c]=self[r,indices[c]].
    This returns target.
    Negative indices are interpreted in the usual Python way: all elements of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
    This does bounds checking, but out of bounds indices do not raise an exception (because the programmer was lazy). Instead, they result in NaN values in <target>.
    """

    err_code = _eigenmat.selectRows(self.p_mat, target.p_mat, indices.p_mat)

    if err_code:
      raise generate_exception(err_code)

    return target


  def swap_columns(self, indices1, indices2, target):
    """
    swap columns at indices1 of self with columns at indices2 of target.
    <indices1> and <indices2> must be row vectors of equal length. Its elements are float32's representing integers, e.g. "34.0" means the integer "34".
    after this call, for all r,c, target[r,indices2[c]=self[r,indices1[c]].
    self can be same as target, but then the result will be non-deterministic if there is overlap between indices1 and indices2. Can be used for in-place shuffling by making sure indices1 and indices2 do not overlap.
    This returns target.
    Negative indices are interpreted in the usual Python way: all elements of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
    This does bounds checking, but out of bounds indices do not raise an exception (because the programmer was lazy). Instead, they result in NaN values in <target>.
    """
    assert indices1.shape[0] == 1
    assert indices1.shape == indices2.shape
    err_code = _eigenmat.swapCols(self.p_mat, target.p_mat, indices1.p_mat, indices2.p_mat)

    if err_code:
      raise generate_exception(err_code)

    return target

  def set_selected_columns(self, indices, source):
    """
    copies all columns of source into some columns of self.
    <indices> must be a row vector. Its elements are float32's representing
    integers, e.g. "34.0" means the integer "34". after this call, for all
    r,c, self[r,indices[c]]=source[r,c]. This returns self.
    Negative indices are interpreted in the usual Python way: all elements
    of <indices> had better be in the range [-self.shape[1], self.shape[1]-1].
    This does bounds checking, but out of bounds indices do not raise an
    exception (because the programmer was lazy). Instead, they result in NaN
    values in <self>.
    """

    err_code = _eigenmat.setSelectedRows(self.p_mat, source.p_mat, indices.p_mat)
    if err_code:
      raise generate_exception(err_code)

    return self

  def get_softmax_correct(self, labels, target):
    """
    target[i] = 1, iff labels[i] is correctly predicted; 0 otherwise.
    """
    assert labels.shape == (1, self.shape[1])
    assert target.shape == labels.shape
    if isinstance(labels, EigenMatrix):
      err_code = _eigenmat.get_softmax_correct(self.p_mat, labels.p_mat, target.p_mat)
    else:
      raise ValueError, "labels must be of type CUDAMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target

  def get_softmax_cross_entropy(self, labels, target, tiny=1e-10):
    """
    target[i] = -log(self[label[i]] + tiny).
    """
    assert labels.shape == (1, self.shape[1])
    assert target.shape == labels.shape
    if isinstance(labels, EigenMatrix):
      err_code = _eigenmat.get_softmax_cross_entropy(self.p_mat, labels.p_mat, target.p_mat, ct.c_float(tiny))
    else:
      raise ValueError, "labels must be of type EigenMatrix or CUDAMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target

  def apply_softmax_grad(self, labels, target = None):
    """
    Apply softmax derivative, where labels are the correct labels.
    """
    if not target:
      target = self

    assert labels.shape == (1, self.shape[1])
    assert target.shape == self.shape
    if isinstance(labels, EigenMatrix):
      err_code = _eigenmat.apply_softmax_grad(self.p_mat, labels.p_mat, target.p_mat)
    else:
      raise ValueError, "labels must be of type EigenMatrix or CUDAMatrix."

    if err_code:
      raise generate_exception(err_code)

    return target




CUDAMatrix = EigenMatrix
def empty(shape):
  """
  Creates and returns a new EigenMatrix with the given shape.
  """
  return EigenMatrix(np.zeros(shape))

def sum(mat, axis, target=None):
  """
  Sum the matrix along the given dimension, where 0 represents the leading
  dimension and 1 represents the non-leading dimension. If a target is
  not prvided, a new vector is created for storing the result.
  """

  m = _eigenmat.get_leading_dimension(mat.p_mat)
  n = _eigenmat.get_nonleading_dimension(mat.p_mat)

  if axis == 0:
    # sum along leading dimension
    if not target:
      target = empty((1, n))
 
  elif axis == 1:
    # sum along non-leading dimension
    if not target:
      target = empty((m, 1))

  err_code = _eigenmat.sum_by_axis(mat.p_mat, target.p_mat, ct.c_int(axis))

  if err_code:
    raise generate_exception(err_code)

  return target

def dot(m1, m2, mult=1.0, target=None):
  """
  Find the dot product between m1 and m2.
  """

  if not target:
    m = _eigenmat.get_leading_dimension(m1.p_mat)
    n = _eigenmat.get_nonleading_dimension(m2.p_mat)

    target = empty((m, n))

  err_code = _eigenmat.dot(m1.p_mat, m2.p_mat, target.p_mat, ct.c_float(0.), ct.c_float(mult))
  if err_code:
    raise generate_exception(err_code)

  return target

def vdot(m1, m2):
  """
  Compute the vector dot product of matrices m1 and m2.
  """

  err_code = ct.c_int(0)
  res = _eigenmat.vdot(m1.p_mat, m2.p_mat, ct.byref(err_code))

  if err_code:
    raise generate_exception(err_code.value)

  return res

def cos(mat, target=None):
  """
  Apply cos to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_cos(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target



def sin(mat, target=None):
  """
  Apply sin to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_sin(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def softmax(mat, target = None):
  """
  Apply softmax activation to each column of mat.
  """
  if not target:
    target = mat

  err_code = _eigenmat.apply_softmax(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)
  return target

def sigmoid(mat, target=None):
  """
  Apply the logistic sigmoid to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_sigmoid(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def tanh(mat, target=None):
  """
  Apply the tanh to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_tanh(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def abs(mat, target=None):
  """
  Apply abs to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_abs(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def log_1_plus_exp(mat, target=None, exact=False):
  """
  Apply log(1+exp(x)) to each element of the matrix mat. If exact is True, use
  slow and accurate log and exp.
  """

  if not target:
    target = mat

  if exact:
   err_code = _eigenmat.apply_log_1_plus_exp_exact(mat.p_mat, target.p_mat)
  else:
   err_code = _eigenmat.apply_log_1_plus_exp(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def log(mat, tiny=0.0, target=None):
  """
  Find the natural logarithm of each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_log(mat.p_mat, target.p_mat, ct.c_float(tiny))
  if err_code:
    raise generate_exception(err_code)

  return target

def exp(mat, target=None):
  """
  Apply the exponential function to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_exp(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def ceil(mat, target=None):
  """
  Apply the ceil function to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_ceil(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def floor(mat, target=None):
  """
  Apply the floor function to each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_floor(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def sqrt(mat, target=None):
  """
  Compute the square root of each element of the matrix mat.
  """

  if not target:
    target = mat

  err_code = _eigenmat.apply_sqrt(mat.p_mat, target.p_mat)
  if err_code:
    raise generate_exception(err_code)

  return target

def cross_entropy_bernoulli(mat, p, target=None, tiny=1e-10):
  """
  Compute -mat*log(p) - (1-mat).*log(1-p)
  """

  if not target:
    target = mat

  if isinstance(p, EigenMatrix):
    err_code = _eigenmat.compute_cross_entropy_bernoulli(mat.p_mat, p.p_mat, target.p_mat, ct.c_float(tiny))
  else:
    raise ValueError, "Value must be of type EigenMatrix."

  if err_code:
    raise generate_exception(err_code)

  return target


def cross_entropy(mat, p, target=None, tiny=1e-10):
  """
  Compute -mat*log(p)
  """

  if not target:
    target = mat

  if isinstance(p, EigenMatrix):
    err_code = _eigenmat.compute_cross_entropy(mat.p_mat, p.p_mat, target.p_mat, ct.c_float(tiny))
  else:
    raise ValueError, "Value must be of type EigenMatrix."

  if err_code:
    raise generate_exception(err_code)

  return target

def correct_preds(mat, p, target=None, cutoff=0.5):
  """
  Compute mat*(p >= 0.5) + (1-mat).*(p < 0.5)
  """

  if not target:
    target = mat

  if isinstance(p, EigenMatrix):
    err_code = _eigenmat.correct_preds(mat.p_mat, p.p_mat, target.p_mat, ct.c_float(cutoff))
  else:
    raise ValueError, "Value must be of type EigenMatrix."

  if err_code:
    raise generate_exception(err_code)

  return target

def pow(mat, p, target=None):
  """
  If p is a scalar, compute the 'p'th power of each element of the matrix mat,
  otherwise raise each element of the matrix mat to the power given by the
  corresponding element of the matrix p.
  """

  if not target:
    target = mat

  if isinstance(p, EigenMatrix):
    err_code = _eigenmat.apply_pow_matrix(mat.p_mat, p.p_mat, target.p_mat)
  elif isinstance(p, (int, float)):
    err_code = _eigenmat.apply_pow(mat.p_mat, ct.c_float(p), target.p_mat)
  else:
    raise ValueError, "Value must be of type EigenMatrix, int, or float."

  if err_code:
    raise generate_exception(err_code)

  return target

def cuda_sync_threads():
  pass

def reformat(array):
  """
  Returns array as a float32 array in FORTRAN order.
  """
  return np.array(array, dtype=np.float32, order='F')

def cuda_set_device(dev_id):
  """
  Selects the CUDA device with the given ID.
  """
  pass

def cublas_init():
  """
  Initialize Cublas.
  """
  pass

init = cublas_init

def cublas_shutdown():
  """
  Shut down Cublas.
  """
  pass

shutdown = cublas_shutdown

########NEW FILE########
__FILENAME__ = test
import unittest
import eigenmat as mat
import numpy as np

class TestEigenMat(unittest.TestCase):

  def setUp(self):
    mat.EigenMatrix.init_random(seed=1)

  def test_add(self):
    x = np.random.randn(10, 10)
    y = np.random.randn(10, 10)
    eig_x = mat.EigenMatrix(x)
    eig_y = mat.EigenMatrix(y)
    eig_z = mat.empty(x.shape)

    z = x + y  # Numpy add.
    eig_x.add(eig_y, target=eig_z)  # EigenMat add.
    
    diff = ((eig_z.asarray() - z)**2).sum()
    self.assertAlmostEqual(diff, 0)

  def test_dot(self):
    x = np.random.randn(500, 1000)
    y = np.random.randn(1000, 600)
    eig_x = mat.EigenMatrix(x)
    eig_y = mat.EigenMatrix(y)
    eig_z = mat.empty((x.shape[0], y.shape[1]))

    z = x.dot(y)
    mat.dot(eig_x, eig_y, target=eig_z)

    diff = ((eig_z.asarray() - z)**2).sum()
    self.assertAlmostEqual(diff, 0, places=5)

  def test_dot_transposed(self):
    x = np.random.randn(500, 1000)
    y = np.random.randn(600, 1000)
    eig_x = mat.EigenMatrix(x)
    eig_y = mat.EigenMatrix(y)
    eig_z = mat.empty((x.shape[0], y.shape[0]))

    z = x.dot(y.T)
    mat.dot(eig_x, eig_y.T, target=eig_z)

    diff = ((eig_z.asarray() - z)**2).sum()
    self.assertAlmostEqual(diff, 0, places=5)

  def test_sum_by_axis(self):
    x = 1.1 + np.random.randn(10, 1000)
    y = np.zeros((1, 1000))
    z = np.zeros((10, 1))
    eig_x = mat.EigenMatrix(x)
    eig_y = mat.EigenMatrix(y)
    eig_z = mat.EigenMatrix(z)

    eig_x.sum(axis=0, target=eig_y)
    eig_x.sum(axis=1, target=eig_z)
    diff = ((eig_y.asarray() - x.sum(axis=0).reshape(1, -1))**2).sum()
    self.assertAlmostEqual(diff, 0, places=5)
    diff = ((eig_z.asarray() - x.sum(axis=1).reshape(-1, 1))**2).sum()
    self.assertAlmostEqual(diff, 0, places=5)


  def test_apply_softmax(self):
    x = np.random.randn(100, 10)
    eig_x = mat.EigenMatrix(x)
    eig_y = mat.empty((100, 10))

    eig_x.apply_softmax(target=eig_y)
    
    y = np.exp(x - x.max(axis=0))
    y /= y.sum(axis=0)

    diff = ((eig_y.asarray() - y)**2).sum()
    self.assertAlmostEqual(diff, 0, places=5)

if __name__ == '__main__':
  unittest.main()




########NEW FILE########
__FILENAME__ = visual_test
import matplotlib.pyplot as plt
import numpy as np
plt.ion()
import eigenmat as mat
mat.EigenMatrix.init_random(seed=1)
plt.figure(1)
plt.clf()
x = mat.empty((100, 100))
x.fill_with_randn()
plt.hist(x.asarray().flatten(), 100)

plt.figure(2)
plt.clf()
y = np.random.randn(100, 100)
plt.hist(y.flatten(), 100)

raw_input('Press Enter.')

########NEW FILE########
