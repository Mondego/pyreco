__FILENAME__ = diag_demo
#!/usr/bin/env python

"""
Demonstrate diagonal matrix creation on the GPU.
"""

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import pycuda.driver as drv
import numpy as np

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc
culinalg.init()

# Double precision is only supported by devices with compute
# capability >= 1.3:
import string
demo_types = [np.float32, np.complex64]
if cumisc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
    demo_types.extend([np.float64, np.complex128])

for t in demo_types:
    print 'Testing real diagonal matrix creation for type ' + str(np.dtype(t))
    v = np.array([1, 2, 3, 4, 5, 6], t)
    v_gpu = gpuarray.to_gpu(v)
    d_gpu = culinalg.diag(v_gpu);
    print 'Success status: ', np.all(d_gpu.get() == np.diag(v))


########NEW FILE########
__FILENAME__ = dot_demo
#!/usr/bin/env python

"""
Demonstrates multiplication of two matrices on the GPU.
"""

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import pycuda.driver as drv
import numpy as np

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc
culinalg.init()

# Double precision is only supported by devices with compute
# capability >= 1.3:
import string
demo_types = [np.float32, np.complex64]
if cumisc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
    demo_types.extend([np.float64, np.complex128])

for t in demo_types:
    print 'Testing matrix multiplication for type ' + str(np.dtype(t))
    if np.iscomplexobj(t()):
        a = np.asarray(np.random.rand(10, 5)+1j*np.random.rand(10, 5), t)
        b = np.asarray(np.random.rand(5, 5)+1j*np.random.rand(5, 5), t)
        c = np.asarray(np.random.rand(5, 5)+1j*np.random.rand(5, 5), t)
    else:
        a = np.asarray(np.random.rand(10, 5), t)
        b = np.asarray(np.random.rand(5, 5), t)
        c = np.asarray(np.random.rand(5, 5), t)

    a_gpu = gpuarray.to_gpu(a)
    b_gpu = gpuarray.to_gpu(b)
    c_gpu = gpuarray.to_gpu(c)

    temp_gpu = culinalg.dot(a_gpu, b_gpu)
    d_gpu = culinalg.dot(temp_gpu, c_gpu)
    temp_gpu.gpudata.free()
    del(temp_gpu)
    print 'Success status: ', np.allclose(np.dot(np.dot(a, b), c) , d_gpu.get())

    print 'Testing vector multiplication for type '  + str(np.dtype(t))
    if np.iscomplexobj(t()):
        d = np.asarray(np.random.rand(5)+1j*np.random.rand(5), t)
        e = np.asarray(np.random.rand(5)+1j*np.random.rand(5), t)
    else:
        d = np.asarray(np.random.rand(5), t)
        e = np.asarray(np.random.rand(5), t)

    d_gpu = gpuarray.to_gpu(d)
    e_gpu = gpuarray.to_gpu(e)

    temp = culinalg.dot(d_gpu, e_gpu)
    print 'Success status: ', np.allclose(np.dot(d, e), temp)

########NEW FILE########
__FILENAME__ = fft2d_batch_demo
#!/usr/bin/env python

"""
Demonstrates how to use the PyCUDA interface to CUFFT to compute a
batch of 2D FFTs.
"""

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.fft as cu_fft

print 'Testing fft/ifft..'
N = 256
batch_size = 16

x = np.empty((batch_size, N, N), np.float32)
xf = np.empty((batch_size, N, N), np.complex64)
y = np.empty((batch_size, N, N), np.float32)
for i in xrange(batch_size):
    x[i, :, :] = np.asarray(np.random.rand(N, N), np.float32)
    xf[i, :, :] = np.fft.fft2(x[i, :, :])
    y[i, :, :] = np.real(np.fft.ifft2(xf[i, :, :]))

x_gpu = gpuarray.to_gpu(x)
xf_gpu = gpuarray.empty((batch_size, N, N/2+1), np.complex64)
plan_forward = cu_fft.Plan((N, N), np.float32, np.complex64, batch_size)
cu_fft.fft(x_gpu, xf_gpu, plan_forward)

y_gpu = gpuarray.empty_like(x_gpu)
plan_inverse = cu_fft.Plan((N, N), np.complex64, np.float32, batch_size)
cu_fft.ifft(xf_gpu, y_gpu, plan_inverse, True)

print 'Success status: ', np.allclose(y, y_gpu.get(), atol=1e-6)

print 'Testing in-place fft..'
x = np.empty((batch_size, N, N), np.complex64)
x_gpu = gpuarray.to_gpu(x)

plan = cu_fft.Plan((N, N), np.complex64, np.complex64, batch_size)
cu_fft.fft(x_gpu, x_gpu, plan)

cu_fft.ifft(x_gpu, x_gpu, plan, True)

print 'Success status: ', np.allclose(x, x_gpu.get(), atol=1e-6)

########NEW FILE########
__FILENAME__ = fft2d_demo
#!/usr/bin/env python

"""
Demonstrates how to use the PyCUDA interface to CUFFT to compute 2D FFTs.
"""

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.fft as cu_fft

print 'Testing fft/ifft..'
N = 1024
M = N/2

x = np.asarray(np.random.rand(N, M), np.float32)
xf = np.fft.fft2(x)
y = np.real(np.fft.ifft2(xf))

x_gpu = gpuarray.to_gpu(x)
xf_gpu = gpuarray.empty((x.shape[0], x.shape[1]/2+1), np.complex64)
plan_forward = cu_fft.Plan(x_gpu.shape, np.float32, np.complex64)
cu_fft.fft(x_gpu, xf_gpu, plan_forward)

y_gpu = gpuarray.empty_like(x_gpu)
plan_inverse = cu_fft.Plan(x_gpu.shape, np.complex64, np.float32)
cu_fft.ifft(xf_gpu, y_gpu, plan_inverse, True)

print 'Success status: ', np.allclose(y, y_gpu.get(), atol=1e-6)

print 'Testing in-place fft..'
x = np.asarray(np.random.rand(N, M)+1j*np.random.rand(N, M), np.complex64)
x_gpu = gpuarray.to_gpu(x)

plan = cu_fft.Plan(x_gpu.shape, np.complex64, np.complex64)
cu_fft.fft(x_gpu, x_gpu, plan)

cu_fft.ifft(x_gpu, x_gpu, plan, True)

print 'Success status: ', np.allclose(x, x_gpu.get(), atol=1e-6)

########NEW FILE########
__FILENAME__ = fft_batch_demo
#!/usr/bin/env python

"""
Demonstrates how to use the PyCUDA interface to CUFFT to compute a
batch of 1D FFTs.
"""

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.fft as cu_fft

print 'Testing fft/ifft..'
N = 4096*16
batch_size = 16

x = np.asarray(np.random.rand(batch_size, N), np.float32)
xf = np.fft.fft(x)
y = np.real(np.fft.ifft(xf))

x_gpu = gpuarray.to_gpu(x)
xf_gpu = gpuarray.empty((batch_size, N/2+1), np.complex64)
plan_forward = cu_fft.Plan(N, np.float32, np.complex64, batch_size)
cu_fft.fft(x_gpu, xf_gpu, plan_forward)

y_gpu = gpuarray.empty_like(x_gpu)
plan_inverse = cu_fft.Plan(N, np.complex64, np.float32, batch_size)
cu_fft.ifft(xf_gpu, y_gpu, plan_inverse, True)

print 'Success status: ', np.allclose(y, y_gpu.get(), atol=1e-6)

print 'Testing in-place fft..'
x = np.asarray(np.random.rand(batch_size, N)+\
               1j*np.random.rand(batch_size, N), np.complex64)
x_gpu = gpuarray.to_gpu(x)

plan = cu_fft.Plan(N, np.complex64, np.complex64, batch_size)
cu_fft.fft(x_gpu, x_gpu, plan)

cu_fft.ifft(x_gpu, x_gpu, plan, True)

print 'Success status: ', np.allclose(x, x_gpu.get(), atol=1e-6)

########NEW FILE########
__FILENAME__ = fft_demo
#!/usr/bin/env python

"""
Demonstrates how to use the PyCUDA interface to CUFFT to compute 1D FFTs.
"""

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.fft as cu_fft

print 'Testing fft/ifft..'
N = 4096*16

x = np.asarray(np.random.rand(N), np.float32)
xf = np.fft.fft(x)
y = np.real(np.fft.ifft(xf))

x_gpu = gpuarray.to_gpu(x)
xf_gpu = gpuarray.empty(N/2+1, np.complex64)
plan_forward = cu_fft.Plan(x_gpu.shape, np.float32, np.complex64)
cu_fft.fft(x_gpu, xf_gpu, plan_forward)

y_gpu = gpuarray.empty_like(x_gpu)
plan_inverse = cu_fft.Plan(x_gpu.shape, np.complex64, np.float32)
cu_fft.ifft(xf_gpu, y_gpu, plan_inverse, True)

print 'Success status: ', np.allclose(y, y_gpu.get(), atol=1e-6)

print 'Testing in-place fft..'
x = np.asarray(np.random.rand(N)+1j*np.random.rand(N), np.complex64)
x_gpu = gpuarray.to_gpu(x)

plan = cu_fft.Plan(x_gpu.shape, np.complex64, np.complex64)
cu_fft.fft(x_gpu, x_gpu, plan)

cu_fft.ifft(x_gpu, x_gpu, plan, True)

print 'Success status: ', np.allclose(x, x_gpu.get(), atol=1e-6)

########NEW FILE########
__FILENAME__ = indexing_2d_demo
#!/usr/bin/env python

"""
Demonstrates how to access 2D arrays within a PyCUDA kernel in a
numpy-consistent manner.
"""

from string import Template
import pycuda.autoinit
import pycuda.gpuarray as gpuarray
from pycuda.compiler import SourceModule
import numpy as np

import scikits.cuda.misc as misc

A = 3
B = 4
N = A*B

# Define a 2D array:
# x_orig = np.arange(0, N, 1, np.float64)
x_orig = np.asarray(np.random.rand(N), np.float64)
x = x_orig.reshape((A, B))

# These functions demonstrate how to convert a linear index into subscripts:
a = lambda i: i/B
b = lambda i: np.mod(i, B)

# Check that x[subscript(i)] is equivalent to x.flat[i]:
subscript = lambda i: (a(i), b(i))
for i in xrange(x.size):
    assert x.flat[i] == x[subscript(i)]

# Check that x[i, j] is equivalent to x.flat[index(i, j)]:
index = lambda i, j: i*B+j
for i in xrange(A):
    for j in xrange(B):
        assert x[i, j] == x.flat[index(i, j)]
        
func_mod_template = Template("""
// Macro for converting subscripts to linear index:
#define INDEX(a, b) a*${B}+b

__global__ void func(double *x, unsigned int N) {
    // Obtain the linear index corresponding to the current thread:
    unsigned int idx = blockIdx.y*${max_threads_per_block}*${max_blocks_per_grid}+
                       blockIdx.x*${max_threads_per_block}+threadIdx.x;

    // Convert the linear index to subscripts:
    unsigned int a = idx/${B};
    unsigned int b = idx%${B};

    // Use the subscripts to access the array:
    if (idx < N) {
        if (b == 0)
           x[INDEX(a,b)] = 100;
    }
}
""")

max_threads_per_block, max_block_dim, max_grid_dim = misc.get_dev_attrs(pycuda.autoinit.device)
block_dim, grid_dim = misc.select_block_grid_sizes(pycuda.autoinit.device, x.shape)
max_blocks_per_grid = max(max_grid_dim)

func_mod = \
         SourceModule(func_mod_template.substitute(max_threads_per_block=max_threads_per_block,
                                                   max_blocks_per_grid=max_blocks_per_grid,
                                                   A=A, B=B))
func = func_mod.get_function('func')
x_gpu = gpuarray.to_gpu(x)
func(x_gpu.gpudata, np.uint32(x_gpu.size),
     block=block_dim,
     grid=grid_dim)
x_np = x.copy()
x_np[:, 0] = 100

print 'Success status: ', np.allclose(x_np, x_gpu.get())

########NEW FILE########
__FILENAME__ = indexing_3d_demo
#!/usr/bin/env python

"""
Demonstrates how to access 3D arrays within a PyCUDA kernel in a
numpy-consistent manner.
"""

from string import Template
import pycuda.autoinit
import pycuda.gpuarray as gpuarray
from pycuda.compiler import SourceModule
import numpy as np

import scikits.cuda.misc as misc

A = 3
B = 4
C = 5
N = A*B*C

# Define a 3D array:
# x_orig = np.arange(0, N, 1, np.float64)
x_orig = np.asarray(np.random.rand(N), np.float64)
x = x_orig.reshape((A, B, C))

# These functions demonstrate how to convert a linear index into subscripts:
a = lambda i: i/(B*C)
b = lambda i: np.mod(i, B*C)/C
c = lambda i: np.mod(np.mod(i, B*C), C)

# Check that x[ind(i)] is equivalent to x.flat[i]:
subscript = lambda i: (a(i), b(i), c(i))
for i in xrange(x.size):
    assert x.flat[i] == x[subscript(i)]

# Check that x[i,j,k] is equivalent to x.flat[index(i,j,k)]:
index = lambda i,j,k: i*B*C+j*C+k
for i in xrange(A):
    for j in xrange(B):
        for k in xrange(C):
            assert x[i, j, k] == x.flat[index(i, j, k)]

func_mod_template = Template("""
// Macro for converting subscripts to linear index:
#define INDEX(a, b, c) a*${B}*${C}+b*${C}+c

__global__ void func(double *x, unsigned int N) {
    // Obtain the linear index corresponding to the current thread:
    unsigned int idx = blockIdx.y*${max_threads_per_block}*${max_blocks_per_grid}+
                       blockIdx.x*${max_threads_per_block}+threadIdx.x;

    // Convert the linear index to subscripts:
    unsigned int a = idx/(${B}*${C});
    unsigned int b = (idx%(${B}*${C}))/${C};
    unsigned int c = (idx%(${B}*${C}))%${C};

    // Use the subscripts to access the array:
    if (idx < N) {
        if (b == 0)
           x[INDEX(a,b,c)] = 100;
    }
}
""")

max_threads_per_block, max_block_dim, max_grid_dim = misc.get_dev_attrs(pycuda.autoinit.device)
block_dim, grid_dim = misc.select_block_grid_sizes(pycuda.autoinit.device, x.shape)
max_blocks_per_grid = max(max_grid_dim)

func_mod = \
         SourceModule(func_mod_template.substitute(max_threads_per_block=max_threads_per_block,
                                                   max_blocks_per_grid=max_blocks_per_grid,
                                                   A=A, B=B, C=C))
func = func_mod.get_function('func')
x_gpu = gpuarray.to_gpu(x)
func(x_gpu.gpudata, np.uint32(x_gpu.size),
     block=block_dim,
     grid=grid_dim)
x_np = x.copy()
x_np[:, 0, :] = 100

print 'Success status: ', np.allclose(x_np, x_gpu.get())

########NEW FILE########
__FILENAME__ = indexing_4d_demo
#!/usr/bin/env python

"""
Demonstrates how to access 4D arrays within a PyCUDA kernel in a
numpy-consistent manner.
"""

from string import Template
import pycuda.autoinit
import pycuda.gpuarray as gpuarray
from pycuda.compiler import SourceModule
import numpy as np

import scikits.cuda.misc as misc

A = 3
B = 4
C = 5
D = 6
N = A*B*C*D

# Define a 3D array:
# x_orig = np.arange(0, N, 1, np.float64)
x_orig = np.asarray(np.random.rand(N), np.float64)
x = x_orig.reshape((A, B, C, D))

# These functions demonstrate how to convert a linear index into subscripts:
a = lambda i: i/(B*C*D)
b = lambda i: np.mod(i, B*C*D)/(C*D)
c = lambda i: np.mod(np.mod(i, B*C*D), C*D)/D
d = lambda i: np.mod(np.mod(np.mod(i, B*C*D), C*D), D)

# Check that x[subscript(i)] is equivalent to x.flat[i]:
subscript = lambda i: (a(i), b(i), c(i), d(i))
for i in xrange(x.size):
    assert x.flat[i] == x[subscript(i)]

# Check that x[i,j,k,l] is equivalent to x.flat[index(i,j,k,l)]:
index = lambda i,j,k,l: i*B*C*D+j*C*D+k*D+l
for i in xrange(A):
    for j in xrange(B):
        for k in xrange(C):
            for l in xrange(D):
                assert x[i, j, k, l] == x.flat[index(i, j, k, l)]
                
func_mod_template = Template("""
// Macro for converting subscripts to linear index:
#define INDEX(a, b, c, d) a*${B}*${C}*${D}+b*${C}*${D}+c*${D}+d

__global__ void func(double *x, unsigned int N) {
    // Obtain the linear index corresponding to the current thread:
    unsigned int idx = blockIdx.y*${max_threads_per_block}*${max_blocks_per_grid}+
                       blockIdx.x*${max_threads_per_block}+threadIdx.x;

    // Convert the linear index to subscripts:
    unsigned int a = idx/(${B}*${C}*${D});
    unsigned int b = (idx%(${B}*${C}*${D}))/(${C}*${D});
    unsigned int c = ((idx%(${B}*${C}*${D}))%(${C}*${D}))/${D};
    unsigned int d = ((idx%(${B}*${C}*${D}))%(${C}*${D}))%${D};

    // Use the subscripts to access the array:
    if (idx < N) {
        if (c == 0)
           x[INDEX(a,b,c,d)] = 100;
    }
}
""")

max_threads_per_block, max_block_dim, max_grid_dim = misc.get_dev_attrs(pycuda.autoinit.device)
block_dim, grid_dim = misc.select_block_grid_sizes(pycuda.autoinit.device, x.shape)
max_blocks_per_grid = max(max_grid_dim)

func_mod = \
         SourceModule(func_mod_template.substitute(max_threads_per_block=max_threads_per_block,
                                                   max_blocks_per_grid=max_blocks_per_grid,
                                                   A=A, B=B, C=C, D=D))
func = func_mod.get_function('func')
x_gpu = gpuarray.to_gpu(x)
func(x_gpu.gpudata, np.uint32(x_gpu.size),
     block=block_dim,
     grid=grid_dim)
x_np = x.copy()
x_np[:, :, 0, :] = 100

print 'Success status: ', np.allclose(x_np, x_gpu.get())

########NEW FILE########
__FILENAME__ = mdot_demo
#!/usr/bin/env python

"""
Demonstrates multiplication of several matrices on the GPU.
"""

import pycuda.gpuarray as gpuarray
import pycuda.driver as drv
import pycuda.autoinit
import numpy as np

import scikits.cuda.linalg as linalg
import scikits.cuda.misc as cumisc
linalg.init()

# Double precision is only supported by devices with compute
# capability >= 1.3:
import string
demo_types = [np.float32, np.complex64]
if cumisc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
    demo_types.extend([np.float64, np.complex128])

for t in demo_types:
    print 'Testing multiple matrix multiplication for type ' + str(np.dtype(t))
    if np.iscomplexobj(t()):
        a = np.asarray(np.random.rand(8, 4)+1j*np.random.rand(8, 4), t)
        b = np.asarray(np.random.rand(4, 4)+1j*np.random.rand(4, 4), t)
        c = np.asarray(np.random.rand(4, 4)+1j*np.random.rand(4, 4), t)
    else:
        a = np.asarray(np.random.rand(8, 4), t)
        b = np.asarray(np.random.rand(4, 4), t)
        c = np.asarray(np.random.rand(4, 4), t)

    a_gpu = gpuarray.to_gpu(a)
    b_gpu = gpuarray.to_gpu(b)
    c_gpu = gpuarray.to_gpu(c)
    d_gpu = linalg.mdot(a_gpu, b_gpu, c_gpu)
    print 'Success status: ', np.allclose(np.dot(a, np.dot(b, c)), d_gpu.get())

########NEW FILE########
__FILENAME__ = pinv_demo
#!/usr/bin/env python

"""
Demonstrates computation of the pseudoinverse on the GPU.
"""

import pycuda.autoinit
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc
culinalg.init()

# Double precision is only supported by devices with compute
# capability >= 1.3:
import string
import scikits.cuda.cula as cula
demo_types = [np.float32, np.complex64]
if cula._libcula_toolkit == 'premium' and \
       cumisc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
    demo_types.extend([np.float64, np.complex128])

for t in demo_types:
    print 'Testing pinv for type ' + str(np.dtype(t))
    a = np.asarray((np.random.rand(50, 50)-0.5)/10, t)
    a_gpu = gpuarray.to_gpu(a)
    a_inv_gpu = culinalg.pinv(a_gpu)

    print 'Success status: ', np.allclose(np.linalg.pinv(a), a_inv_gpu.get(), 
		                      atol=1e-2)
    print 'Maximum error: ', np.max(np.abs(np.linalg.pinv(a)-a_inv_gpu.get()))
    print ''

########NEW FILE########
__FILENAME__ = svd_demo
#!/usr/bin/env python

"""
Demonstrates computation of the singular value decomposition on the GPU.
"""

import pycuda.autoinit
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc
culinalg.init()

# Double precision is only supported by devices with compute
# capability >= 1.3:
import string
import scikits.cuda.cula as cula
demo_types = [np.float32, np.complex64]
if cula._libcula_toolkit == 'premium' and \
       cumisc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
    demo_types.extend([np.float64, np.complex128])

for t in demo_types:
    print 'Testing svd for type ' + str(np.dtype(t))
    a = np.asarray((np.random.rand(50, 50)-0.5)/10, t)
    a_gpu = gpuarray.to_gpu(a)
    u_gpu, s_gpu, vh_gpu = culinalg.svd(a_gpu)
    a_rec = np.dot(u_gpu.get(), np.dot(np.diag(s_gpu.get()), vh_gpu.get()))
                                                           
    print 'Success status: ', np.allclose(a, a_rec, atol=1e-3)
    print 'Maximum error: ', np.max(np.abs(a-a_rec))
    print ''

########NEW FILE########
__FILENAME__ = transpose_demo
#!/usr/bin/env python

"""
Demonstrates how to transpose matrices on the GPU.
"""

import pycuda.autoinit
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc
culinalg.init()

# Double precision is only supported by devices with compute
# capability >= 1.3:
import string
demo_types = [np.float32, np.complex64]
if cumisc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
    demo_types.extend([np.float64, np.complex128])

for t in demo_types:
    print 'Testing transpose for type ' + str(np.dtype(t))
    if np.iscomplexobj(t()):
        b = np.array([[1j, 2j, 3j, 4j, 5j, 6j],
                      [7j, 8j, 9j, 10j, 11j, 12j]], t)
    else:
        a = np.array([[1, 2, 3, 4, 5, 6],
                      [7, 8, 9, 10, 11, 12]], t)
    a_gpu = gpuarray.to_gpu(a)
    at_gpu = culinalg.transpose(a_gpu)
    if np.iscomplexobj(t()):
        print 'Success status: ', np.all(np.conj(a.T) == at_gpu.get())
    else:
        print 'Success status: ', np.all(a.T == at_gpu.get())




########NEW FILE########
__FILENAME__ = tril_demo
#!/usr/bin/env python

"""
Demonstrates how to extract the lower triangle of a matrix.
"""

import pycuda.autoinit
import pycuda.driver as drv
import numpy as np
import pycuda.gpuarray as gpuarray

import scikits.cuda.linalg as culinalg
import scikits.cuda.misc as cumisc
culinalg.init()

# Double precision is only supported by devices with compute
# capability >= 1.3:
import string
demo_types = [np.float32, np.complex64]
if cumisc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
    demo_types.extend([np.float64, np.complex128])

for t in demo_types:
    print 'Testing lower triangle extraction for type ' + str(np.dtype(t))
    N = 10
    if np.iscomplexobj(t()):
        a = np.asarray(np.random.rand(N, N), t)
    else:
        a = np.asarray(np.random.rand(N, N)+1j*np.random.rand(N, N), t)
    a_gpu = gpuarray.to_gpu(a)
    b_gpu = culinalg.tril(a_gpu, False)
    print 'Success status: ', np.allclose(b_gpu.get(), np.tril(a))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# scikits.cuda documentation build configuration file, created by
# sphinx-quickstart on Fri Jul 19 10:11:54 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import re, sys, os
import sphinx_bootstrap_theme

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('../sphinxext'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              'sphinx.ext.intersphinx',
              'sphinx.ext.pngmath',
              'sphinx.ext.viewcode',
              'numpydoc']
try:
    import matplotlib.sphinxext.plot_directive
except ImportError:
    extensions.append('plot_directive')
else:
    extensions.append('matplotlib.sphinxext.plot_directive')

# Generate autosummary stubs:
autosummary_generate = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'scikits.cuda'
copyright = u'2009-2014, Lev Givon'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

import scikits.cuda
# The short X.Y version.
version = re.sub(r'(\d+\.\d+)\.\d+(.*)', r'\1\2', scikits.cuda.__version__)

# The full version, including alpha/beta/rc tags.
release = scikits.cuda.__version__
print 'scikits.cuda version: ', version, release

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'en'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'bootstrap'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    # Navigation bar title. (Default: ``project`` value)
    'navbar_title': "scikits.cuda",

    # Tab name for entire site. (Default: "Site")
    'navbar_site_name': "Contents",

    # Global TOC depth for "site" navbar tab. (Default: 1)
    # Switching to -1 shows all levels.
    'globaltoc_depth': 2,

    # Include hidden TOCs in Site navbar?
    #
    # Note: If this is "false", you cannot have mixed ``:hidden:`` and
    # non-hidden ``toctree`` directives in the same page, or else the build
    # will break.
    #
    # Values: "true" (default) or "false"
    'globaltoc_includehidden': "true",

    # HTML navbar class (Default: "navbar") to attach to <div> element.
    # For black navbar, do "navbar navbar-inverse"
    #'navbar_class': "navbar navbar-inverse",

    # Fix navigation bar to top of page?
    # Values: "true" (default) or "false"
    'navbar_fixed_top': "true",

    # Location of link to source.
    # Options are "nav" (default), "footer" or anything else to exclude.
    'source_link_position': None,

    # Bootswatch (http://bootswatch.com/) theme.
    #
    # Options are nothing with "" (default) or the name of a valid theme
    # such as "amelia" or "cosmo".
    #
    # Note that this is served off CDN, so won't be available offline.
    'bootswatch_theme': "united",
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

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
#html_static_path = ['_static']

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
html_use_index = True

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

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'scikits-cuda-doc'

# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
'preamble': """
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{ucs}
\\renewcommand{\\familydefault}{\\sfdefault}
"""
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'scikits.cuda-doc.tex', u'scikits.cuda Documentation',
   u'Lev Givon', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
latex_use_parts = True

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True



# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'scikits.cuda', u'CUDA Scikit Documentation',
     [u'Lev Givon'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'scikits.cuda', u'CUDA Scikit Documentation',
   u'Lev Givon', 'scikits.cuda', 'CUDA Scikit.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

# Generate links to other projects' online references:
intersphinx_mapping = {
    'http://docs.python.org/2/': None,
    'http://docs.scipy.org/doc/numpy/': None,
    'http://documen.tician.de/pycuda/': None,
}

########NEW FILE########
__FILENAME__ = comment_eater
from cStringIO import StringIO
import compiler
import inspect
import textwrap
import tokenize

from compiler_unparse import unparse


class Comment(object):
    """ A comment block.
    """
    is_comment = True
    def __init__(self, start_lineno, end_lineno, text):
        # int : The first line number in the block. 1-indexed.
        self.start_lineno = start_lineno
        # int : The last line number. Inclusive!
        self.end_lineno = end_lineno
        # str : The text block including '#' character but not any leading spaces.
        self.text = text

    def add(self, string, start, end, line):
        """ Add a new comment line.
        """
        self.start_lineno = min(self.start_lineno, start[0])
        self.end_lineno = max(self.end_lineno, end[0])
        self.text += string

    def __repr__(self):
        return '%s(%r, %r, %r)' % (self.__class__.__name__, self.start_lineno,
            self.end_lineno, self.text)


class NonComment(object):
    """ A non-comment block of code.
    """
    is_comment = False
    def __init__(self, start_lineno, end_lineno):
        self.start_lineno = start_lineno
        self.end_lineno = end_lineno

    def add(self, string, start, end, line):
        """ Add lines to the block.
        """
        if string.strip():
            # Only add if not entirely whitespace.
            self.start_lineno = min(self.start_lineno, start[0])
            self.end_lineno = max(self.end_lineno, end[0])

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.start_lineno,
            self.end_lineno)


class CommentBlocker(object):
    """ Pull out contiguous comment blocks.
    """
    def __init__(self):
        # Start with a dummy.
        self.current_block = NonComment(0, 0)

        # All of the blocks seen so far.
        self.blocks = []

        # The index mapping lines of code to their associated comment blocks.
        self.index = {}

    def process_file(self, file):
        """ Process a file object.
        """
        for token in tokenize.generate_tokens(file.next):
            self.process_token(*token)
        self.make_index()

    def process_token(self, kind, string, start, end, line):
        """ Process a single token.
        """
        if self.current_block.is_comment:
            if kind == tokenize.COMMENT:
                self.current_block.add(string, start, end, line)
            else:
                self.new_noncomment(start[0], end[0])
        else:
            if kind == tokenize.COMMENT:
                self.new_comment(string, start, end, line)
            else:
                self.current_block.add(string, start, end, line)

    def new_noncomment(self, start_lineno, end_lineno):
        """ We are transitioning from a noncomment to a comment.
        """
        block = NonComment(start_lineno, end_lineno)
        self.blocks.append(block)
        self.current_block = block

    def new_comment(self, string, start, end, line):
        """ Possibly add a new comment.
        
        Only adds a new comment if this comment is the only thing on the line.
        Otherwise, it extends the noncomment block.
        """
        prefix = line[:start[1]]
        if prefix.strip():
            # Oops! Trailing comment, not a comment block.
            self.current_block.add(string, start, end, line)
        else:
            # A comment block.
            block = Comment(start[0], end[0], string)
            self.blocks.append(block)
            self.current_block = block

    def make_index(self):
        """ Make the index mapping lines of actual code to their associated
        prefix comments.
        """
        for prev, block in zip(self.blocks[:-1], self.blocks[1:]):
            if not block.is_comment:
                self.index[block.start_lineno] = prev

    def search_for_comment(self, lineno, default=None):
        """ Find the comment block just before the given line number.

        Returns None (or the specified default) if there is no such block.
        """
        if not self.index:
            self.make_index()
        block = self.index.get(lineno, None)
        text = getattr(block, 'text', default)
        return text


def strip_comment_marker(text):
    """ Strip # markers at the front of a block of comment text.
    """
    lines = []
    for line in text.splitlines():
        lines.append(line.lstrip('#'))
    text = textwrap.dedent('\n'.join(lines))
    return text


def get_class_traits(klass):
    """ Yield all of the documentation for trait definitions on a class object.
    """
    # FIXME: gracefully handle errors here or in the caller?
    source = inspect.getsource(klass)
    cb = CommentBlocker()
    cb.process_file(StringIO(source))
    mod_ast = compiler.parse(source)
    class_ast = mod_ast.node.nodes[0]
    for node in class_ast.code.nodes:
        # FIXME: handle other kinds of assignments?
        if isinstance(node, compiler.ast.Assign):
            name = node.nodes[0].name
            rhs = unparse(node.expr).strip()
            doc = strip_comment_marker(cb.search_for_comment(node.lineno, default=''))
            yield name, rhs, doc


########NEW FILE########
__FILENAME__ = compiler_unparse
""" Turn compiler.ast structures back into executable python code.

    The unparse method takes a compiler.ast tree and transforms it back into
    valid python code.  It is incomplete and currently only works for
    import statements, function calls, function definitions, assignments, and
    basic expressions.

    Inspired by python-2.5-svn/Demo/parser/unparse.py

    fixme: We may want to move to using _ast trees because the compiler for
           them is about 6 times faster than compiler.compile.
"""

import sys
import cStringIO
from compiler.ast import Const, Name, Tuple, Div, Mul, Sub, Add

def unparse(ast, single_line_functions=False):
    s = cStringIO.StringIO()
    UnparseCompilerAst(ast, s, single_line_functions)
    return s.getvalue().lstrip()

op_precedence = { 'compiler.ast.Power':3, 'compiler.ast.Mul':2, 'compiler.ast.Div':2,
                  'compiler.ast.Add':1, 'compiler.ast.Sub':1 }

class UnparseCompilerAst:
    """ Methods in this class recursively traverse an AST and
        output source code for the abstract syntax; original formatting
        is disregarged.
    """

    #########################################################################
    # object interface.
    #########################################################################

    def __init__(self, tree, file = sys.stdout, single_line_functions=False):
        """ Unparser(tree, file=sys.stdout) -> None.

            Print the source for tree to file.
        """
        self.f = file
        self._single_func = single_line_functions
        self._do_indent = True
        self._indent = 0
        self._dispatch(tree)
        self._write("\n")
        self.f.flush()

    #########################################################################
    # Unparser private interface.
    #########################################################################

    ### format, output, and dispatch methods ################################

    def _fill(self, text = ""):
        "Indent a piece of text, according to the current indentation level"
        if self._do_indent:
            self._write("\n"+"    "*self._indent + text)
        else:
            self._write(text)

    def _write(self, text):
        "Append a piece of text to the current line."
        self.f.write(text)

    def _enter(self):
        "Print ':', and increase the indentation."
        self._write(": ")
        self._indent += 1

    def _leave(self):
        "Decrease the indentation level."
        self._indent -= 1

    def _dispatch(self, tree):
        "_dispatcher function, _dispatching tree type T to method _T."
        if isinstance(tree, list):
            for t in tree:
                self._dispatch(t)
            return
        meth = getattr(self, "_"+tree.__class__.__name__)
        if tree.__class__.__name__ == 'NoneType' and not self._do_indent:
            return
        meth(tree)


    #########################################################################
    # compiler.ast unparsing methods.
    #
    # There should be one method per concrete grammar type. They are
    # organized in alphabetical order.
    #########################################################################

    def _Add(self, t):
        self.__binary_op(t, '+')

    def _And(self, t):
        self._write(" (")
        for i, node in enumerate(t.nodes):
            self._dispatch(node)
            if i != len(t.nodes)-1:
                self._write(") and (")
        self._write(")")
               
    def _AssAttr(self, t):
        """ Handle assigning an attribute of an object
        """
        self._dispatch(t.expr)
        self._write('.'+t.attrname)
 
    def _Assign(self, t):
        """ Expression Assignment such as "a = 1".

            This only handles assignment in expressions.  Keyword assignment
            is handled separately.
        """
        self._fill()
        for target in t.nodes:
            self._dispatch(target)
            self._write(" = ")
        self._dispatch(t.expr)
        if not self._do_indent:
            self._write('; ')

    def _AssName(self, t):
        """ Name on left hand side of expression.

            Treat just like a name on the right side of an expression.
        """
        self._Name(t)

    def _AssTuple(self, t):
        """ Tuple on left hand side of an expression.
        """

        # _write each elements, separated by a comma.
        for element in t.nodes[:-1]:
            self._dispatch(element)
            self._write(", ")

        # Handle the last one without writing comma
        last_element = t.nodes[-1]
        self._dispatch(last_element)

    def _AugAssign(self, t):
        """ +=,-=,*=,/=,**=, etc. operations
        """
        
        self._fill()
        self._dispatch(t.node)
        self._write(' '+t.op+' ')
        self._dispatch(t.expr)
        if not self._do_indent:
            self._write(';')
            
    def _Bitand(self, t):
        """ Bit and operation.
        """
        
        for i, node in enumerate(t.nodes):
            self._write("(")
            self._dispatch(node)
            self._write(")")
            if i != len(t.nodes)-1:
                self._write(" & ")
                
    def _Bitor(self, t):
        """ Bit or operation
        """
        
        for i, node in enumerate(t.nodes):
            self._write("(")
            self._dispatch(node)
            self._write(")")
            if i != len(t.nodes)-1:
                self._write(" | ")
                
    def _CallFunc(self, t):
        """ Function call.
        """
        self._dispatch(t.node)
        self._write("(")
        comma = False
        for e in t.args:
            if comma: self._write(", ")
            else: comma = True
            self._dispatch(e)
        if t.star_args:
            if comma: self._write(", ")
            else: comma = True
            self._write("*")
            self._dispatch(t.star_args)
        if t.dstar_args:
            if comma: self._write(", ")
            else: comma = True
            self._write("**")
            self._dispatch(t.dstar_args)
        self._write(")")

    def _Compare(self, t):
        self._dispatch(t.expr)
        for op, expr in t.ops:
            self._write(" " + op + " ")
            self._dispatch(expr)

    def _Const(self, t):
        """ A constant value such as an integer value, 3, or a string, "hello".
        """
        self._dispatch(t.value)

    def _Decorators(self, t):
        """ Handle function decorators (eg. @has_units)
        """
        for node in t.nodes:
            self._dispatch(node)

    def _Dict(self, t):
        self._write("{")
        for  i, (k, v) in enumerate(t.items):
            self._dispatch(k)
            self._write(": ")
            self._dispatch(v)
            if i < len(t.items)-1:
                self._write(", ")
        self._write("}")

    def _Discard(self, t):
        """ Node for when return value is ignored such as in "foo(a)".
        """
        self._fill()
        self._dispatch(t.expr)

    def _Div(self, t):
        self.__binary_op(t, '/')

    def _Ellipsis(self, t):
        self._write("...")

    def _From(self, t):
        """ Handle "from xyz import foo, bar as baz".
        """
        # fixme: Are From and ImportFrom handled differently?
        self._fill("from ")
        self._write(t.modname)
        self._write(" import ")
        for i, (name,asname) in enumerate(t.names):
            if i != 0:
                self._write(", ")
            self._write(name)
            if asname is not None:
                self._write(" as "+asname)
                
    def _Function(self, t):
        """ Handle function definitions
        """
        if t.decorators is not None:
            self._fill("@")
            self._dispatch(t.decorators)
        self._fill("def "+t.name + "(")
        defaults = [None] * (len(t.argnames) - len(t.defaults)) + list(t.defaults)
        for i, arg in enumerate(zip(t.argnames, defaults)):
            self._write(arg[0])
            if arg[1] is not None:
                self._write('=')
                self._dispatch(arg[1])
            if i < len(t.argnames)-1:
                self._write(', ')
        self._write(")")
        if self._single_func:
            self._do_indent = False
        self._enter()
        self._dispatch(t.code)
        self._leave()
        self._do_indent = True

    def _Getattr(self, t):
        """ Handle getting an attribute of an object
        """
        if isinstance(t.expr, (Div, Mul, Sub, Add)):
            self._write('(')
            self._dispatch(t.expr)
            self._write(')')
        else:
            self._dispatch(t.expr)
            
        self._write('.'+t.attrname)
        
    def _If(self, t):
        self._fill()
        
        for i, (compare,code) in enumerate(t.tests):
            if i == 0:
                self._write("if ")
            else:
                self._write("elif ")
            self._dispatch(compare)
            self._enter()
            self._fill()
            self._dispatch(code)
            self._leave()
            self._write("\n")

        if t.else_ is not None:
            self._write("else")
            self._enter()
            self._fill()
            self._dispatch(t.else_)
            self._leave()
            self._write("\n")
            
    def _IfExp(self, t):
        self._dispatch(t.then)
        self._write(" if ")
        self._dispatch(t.test)

        if t.else_ is not None:
            self._write(" else (")
            self._dispatch(t.else_)
            self._write(")")

    def _Import(self, t):
        """ Handle "import xyz.foo".
        """
        self._fill("import ")
        
        for i, (name,asname) in enumerate(t.names):
            if i != 0:
                self._write(", ")
            self._write(name)
            if asname is not None:
                self._write(" as "+asname)

    def _Keyword(self, t):
        """ Keyword value assignment within function calls and definitions.
        """
        self._write(t.name)
        self._write("=")
        self._dispatch(t.expr)
        
    def _List(self, t):
        self._write("[")
        for  i,node in enumerate(t.nodes):
            self._dispatch(node)
            if i < len(t.nodes)-1:
                self._write(", ")
        self._write("]")

    def _Module(self, t):
        if t.doc is not None:
            self._dispatch(t.doc)
        self._dispatch(t.node)

    def _Mul(self, t):
        self.__binary_op(t, '*')

    def _Name(self, t):
        self._write(t.name)

    def _NoneType(self, t):
        self._write("None")
        
    def _Not(self, t):
        self._write('not (')
        self._dispatch(t.expr)
        self._write(')')
        
    def _Or(self, t):
        self._write(" (")
        for i, node in enumerate(t.nodes):
            self._dispatch(node)
            if i != len(t.nodes)-1:
                self._write(") or (")
        self._write(")")
                
    def _Pass(self, t):
        self._write("pass\n")

    def _Printnl(self, t):
        self._fill("print ")
        if t.dest:
            self._write(">> ")
            self._dispatch(t.dest)
            self._write(", ")
        comma = False
        for node in t.nodes:
            if comma: self._write(', ')
            else: comma = True
            self._dispatch(node)

    def _Power(self, t):
        self.__binary_op(t, '**')

    def _Return(self, t):
        self._fill("return ")
        if t.value:
            if isinstance(t.value, Tuple):
                text = ', '.join([ name.name for name in t.value.asList() ])
                self._write(text)
            else:
                self._dispatch(t.value)
            if not self._do_indent:
                self._write('; ')

    def _Slice(self, t):
        self._dispatch(t.expr)
        self._write("[")
        if t.lower:
            self._dispatch(t.lower)
        self._write(":")
        if t.upper:
            self._dispatch(t.upper)
        #if t.step:
        #    self._write(":")
        #    self._dispatch(t.step)
        self._write("]")

    def _Sliceobj(self, t):
        for i, node in enumerate(t.nodes):
            if i != 0:
                self._write(":")
            if not (isinstance(node, Const) and node.value is None):
                self._dispatch(node)

    def _Stmt(self, tree):
        for node in tree.nodes:
            self._dispatch(node)

    def _Sub(self, t):
        self.__binary_op(t, '-')

    def _Subscript(self, t):
        self._dispatch(t.expr)
        self._write("[")
        for i, value in enumerate(t.subs):
            if i != 0:
                self._write(",")
            self._dispatch(value)
        self._write("]")

    def _TryExcept(self, t):
        self._fill("try")
        self._enter()
        self._dispatch(t.body)
        self._leave()

        for handler in t.handlers:
            self._fill('except ')
            self._dispatch(handler[0])
            if handler[1] is not None:
                self._write(', ')
                self._dispatch(handler[1])
            self._enter()
            self._dispatch(handler[2])
            self._leave()
            
        if t.else_:
            self._fill("else")
            self._enter()
            self._dispatch(t.else_)
            self._leave()

    def _Tuple(self, t):

        if not t.nodes:
            # Empty tuple.
            self._write("()")
        else:
            self._write("(")

            # _write each elements, separated by a comma.
            for element in t.nodes[:-1]:
                self._dispatch(element)
                self._write(", ")

            # Handle the last one without writing comma
            last_element = t.nodes[-1]
            self._dispatch(last_element)

            self._write(")")
            
    def _UnaryAdd(self, t):
        self._write("+")
        self._dispatch(t.expr)
        
    def _UnarySub(self, t):
        self._write("-")
        self._dispatch(t.expr)        

    def _With(self, t):
        self._fill('with ')
        self._dispatch(t.expr)
        if t.vars:
            self._write(' as ')
            self._dispatch(t.vars.name)
        self._enter()
        self._dispatch(t.body)
        self._leave()
        self._write('\n')
        
    def _int(self, t):
        self._write(repr(t))

    def __binary_op(self, t, symbol):
        # Check if parenthesis are needed on left side and then dispatch
        has_paren = False
        left_class = str(t.left.__class__)
        if (left_class in op_precedence.keys() and
            op_precedence[left_class] < op_precedence[str(t.__class__)]):
            has_paren = True
        if has_paren:
            self._write('(')
        self._dispatch(t.left)
        if has_paren:
            self._write(')')
        # Write the appropriate symbol for operator
        self._write(symbol)
        # Check if parenthesis are needed on the right side and then dispatch
        has_paren = False
        right_class = str(t.right.__class__)
        if (right_class in op_precedence.keys() and
            op_precedence[right_class] < op_precedence[str(t.__class__)]):
            has_paren = True
        if has_paren:
            self._write('(')
        self._dispatch(t.right)
        if has_paren:
            self._write(')')

    def _float(self, t):
        # if t is 0.1, str(t)->'0.1' while repr(t)->'0.1000000000001'
        # We prefer str here.
        self._write(str(t))

    def _str(self, t):
        self._write(repr(t))
        
    def _tuple(self, t):
        self._write(str(t))

    #########################################################################
    # These are the methods from the _ast modules unparse.
    #
    # As our needs to handle more advanced code increase, we may want to
    # modify some of the methods below so that they work for compiler.ast.
    #########################################################################

#    # stmt
#    def _Expr(self, tree):
#        self._fill()
#        self._dispatch(tree.value)
#
#    def _Import(self, t):
#        self._fill("import ")
#        first = True
#        for a in t.names:
#            if first:
#                first = False
#            else:
#                self._write(", ")
#            self._write(a.name)
#            if a.asname:
#                self._write(" as "+a.asname)
#
##    def _ImportFrom(self, t):
##        self._fill("from ")
##        self._write(t.module)
##        self._write(" import ")
##        for i, a in enumerate(t.names):
##            if i == 0:
##                self._write(", ")
##            self._write(a.name)
##            if a.asname:
##                self._write(" as "+a.asname)
##        # XXX(jpe) what is level for?
##
#
#    def _Break(self, t):
#        self._fill("break")
#
#    def _Continue(self, t):
#        self._fill("continue")
#
#    def _Delete(self, t):
#        self._fill("del ")
#        self._dispatch(t.targets)
#
#    def _Assert(self, t):
#        self._fill("assert ")
#        self._dispatch(t.test)
#        if t.msg:
#            self._write(", ")
#            self._dispatch(t.msg)
#
#    def _Exec(self, t):
#        self._fill("exec ")
#        self._dispatch(t.body)
#        if t.globals:
#            self._write(" in ")
#            self._dispatch(t.globals)
#        if t.locals:
#            self._write(", ")
#            self._dispatch(t.locals)
#
#    def _Print(self, t):
#        self._fill("print ")
#        do_comma = False
#        if t.dest:
#            self._write(">>")
#            self._dispatch(t.dest)
#            do_comma = True
#        for e in t.values:
#            if do_comma:self._write(", ")
#            else:do_comma=True
#            self._dispatch(e)
#        if not t.nl:
#            self._write(",")
#
#    def _Global(self, t):
#        self._fill("global")
#        for i, n in enumerate(t.names):
#            if i != 0:
#                self._write(",")
#            self._write(" " + n)
#
#    def _Yield(self, t):
#        self._fill("yield")
#        if t.value:
#            self._write(" (")
#            self._dispatch(t.value)
#            self._write(")")
#
#    def _Raise(self, t):
#        self._fill('raise ')
#        if t.type:
#            self._dispatch(t.type)
#        if t.inst:
#            self._write(", ")
#            self._dispatch(t.inst)
#        if t.tback:
#            self._write(", ")
#            self._dispatch(t.tback)
#
#
#    def _TryFinally(self, t):
#        self._fill("try")
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#        self._fill("finally")
#        self._enter()
#        self._dispatch(t.finalbody)
#        self._leave()
#
#    def _excepthandler(self, t):
#        self._fill("except ")
#        if t.type:
#            self._dispatch(t.type)
#        if t.name:
#            self._write(", ")
#            self._dispatch(t.name)
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#    def _ClassDef(self, t):
#        self._write("\n")
#        self._fill("class "+t.name)
#        if t.bases:
#            self._write("(")
#            for a in t.bases:
#                self._dispatch(a)
#                self._write(", ")
#            self._write(")")
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#    def _FunctionDef(self, t):
#        self._write("\n")
#        for deco in t.decorators:
#            self._fill("@")
#            self._dispatch(deco)
#        self._fill("def "+t.name + "(")
#        self._dispatch(t.args)
#        self._write(")")
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#
#    def _For(self, t):
#        self._fill("for ")
#        self._dispatch(t.target)
#        self._write(" in ")
#        self._dispatch(t.iter)
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#        if t.orelse:
#            self._fill("else")
#            self._enter()
#            self._dispatch(t.orelse)
#            self._leave
#
#    def _While(self, t):
#        self._fill("while ")
#        self._dispatch(t.test)
#        self._enter()
#        self._dispatch(t.body)
#        self._leave()
#        if t.orelse:
#            self._fill("else")
#            self._enter()
#            self._dispatch(t.orelse)
#            self._leave
#
#    # expr
#    def _Str(self, tree):
#        self._write(repr(tree.s))
##
#    def _Repr(self, t):
#        self._write("`")
#        self._dispatch(t.value)
#        self._write("`")
#
#    def _Num(self, t):
#        self._write(repr(t.n))
#
#    def _ListComp(self, t):
#        self._write("[")
#        self._dispatch(t.elt)
#        for gen in t.generators:
#            self._dispatch(gen)
#        self._write("]")
#
#    def _GeneratorExp(self, t):
#        self._write("(")
#        self._dispatch(t.elt)
#        for gen in t.generators:
#            self._dispatch(gen)
#        self._write(")")
#
#    def _comprehension(self, t):
#        self._write(" for ")
#        self._dispatch(t.target)
#        self._write(" in ")
#        self._dispatch(t.iter)
#        for if_clause in t.ifs:
#            self._write(" if ")
#            self._dispatch(if_clause)
#
#    def _IfExp(self, t):
#        self._dispatch(t.body)
#        self._write(" if ")
#        self._dispatch(t.test)
#        if t.orelse:
#            self._write(" else ")
#            self._dispatch(t.orelse)
#
#    unop = {"Invert":"~", "Not": "not", "UAdd":"+", "USub":"-"}
#    def _UnaryOp(self, t):
#        self._write(self.unop[t.op.__class__.__name__])
#        self._write("(")
#        self._dispatch(t.operand)
#        self._write(")")
#
#    binop = { "Add":"+", "Sub":"-", "Mult":"*", "Div":"/", "Mod":"%",
#                    "LShift":">>", "RShift":"<<", "BitOr":"|", "BitXor":"^", "BitAnd":"&",
#                    "FloorDiv":"//", "Pow": "**"}
#    def _BinOp(self, t):
#        self._write("(")
#        self._dispatch(t.left)
#        self._write(")" + self.binop[t.op.__class__.__name__] + "(")
#        self._dispatch(t.right)
#        self._write(")")
#
#    boolops = {_ast.And: 'and', _ast.Or: 'or'}
#    def _BoolOp(self, t):
#        self._write("(")
#        self._dispatch(t.values[0])
#        for v in t.values[1:]:
#            self._write(" %s " % self.boolops[t.op.__class__])
#            self._dispatch(v)
#        self._write(")")
#
#    def _Attribute(self,t):
#        self._dispatch(t.value)
#        self._write(".")
#        self._write(t.attr)
#
##    def _Call(self, t):
##        self._dispatch(t.func)
##        self._write("(")
##        comma = False
##        for e in t.args:
##            if comma: self._write(", ")
##            else: comma = True
##            self._dispatch(e)
##        for e in t.keywords:
##            if comma: self._write(", ")
##            else: comma = True
##            self._dispatch(e)
##        if t.starargs:
##            if comma: self._write(", ")
##            else: comma = True
##            self._write("*")
##            self._dispatch(t.starargs)
##        if t.kwargs:
##            if comma: self._write(", ")
##            else: comma = True
##            self._write("**")
##            self._dispatch(t.kwargs)
##        self._write(")")
#
#    # slice
#    def _Index(self, t):
#        self._dispatch(t.value)
#
#    def _ExtSlice(self, t):
#        for i, d in enumerate(t.dims):
#            if i != 0:
#                self._write(': ')
#            self._dispatch(d)
#
#    # others
#    def _arguments(self, t):
#        first = True
#        nonDef = len(t.args)-len(t.defaults)
#        for a in t.args[0:nonDef]:
#            if first:first = False
#            else: self._write(", ")
#            self._dispatch(a)
#        for a,d in zip(t.args[nonDef:], t.defaults):
#            if first:first = False
#            else: self._write(", ")
#            self._dispatch(a),
#            self._write("=")
#            self._dispatch(d)
#        if t.vararg:
#            if first:first = False
#            else: self._write(", ")
#            self._write("*"+t.vararg)
#        if t.kwarg:
#            if first:first = False
#            else: self._write(", ")
#            self._write("**"+t.kwarg)
#
##    def _keyword(self, t):
##        self._write(t.arg)
##        self._write("=")
##        self._dispatch(t.value)
#
#    def _Lambda(self, t):
#        self._write("lambda ")
#        self._dispatch(t.args)
#        self._write(": ")
#        self._dispatch(t.body)




########NEW FILE########
__FILENAME__ = docscrape
"""Extract reference documentation from the NumPy source tree.

"""

import inspect
import textwrap
import re
import pydoc
from StringIO import StringIO
from warnings import warn

class Reader(object):
    """A line-based string reader.

    """
    def __init__(self, data):
        """
        Parameters
        ----------
        data : str
           String with lines separated by '\n'.

        """
        if isinstance(data,list):
            self._str = data
        else:
            self._str = data.split('\n') # store string as list of lines

        self.reset()

    def __getitem__(self, n):
        return self._str[n]

    def reset(self):
        self._l = 0 # current line nr

    def read(self):
        if not self.eof():
            out = self[self._l]
            self._l += 1
            return out
        else:
            return ''

    def seek_next_non_empty_line(self):
        for l in self[self._l:]:
            if l.strip():
                break
            else:
                self._l += 1

    def eof(self):
        return self._l >= len(self._str)

    def read_to_condition(self, condition_func):
        start = self._l
        for line in self[start:]:
            if condition_func(line):
                return self[start:self._l]
            self._l += 1
            if self.eof():
                return self[start:self._l+1]
        return []

    def read_to_next_empty_line(self):
        self.seek_next_non_empty_line()
        def is_empty(line):
            return not line.strip()
        return self.read_to_condition(is_empty)

    def read_to_next_unindented_line(self):
        def is_unindented(line):
            return (line.strip() and (len(line.lstrip()) == len(line)))
        return self.read_to_condition(is_unindented)

    def peek(self,n=0):
        if self._l + n < len(self._str):
            return self[self._l + n]
        else:
            return ''

    def is_empty(self):
        return not ''.join(self._str).strip()


class NumpyDocString(object):
    def __init__(self, docstring, config={}):
        docstring = textwrap.dedent(docstring).split('\n')

        self._doc = Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': [''],
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'Other Parameters': [],
            'Attributes': [],
            'Methods': [],
            'See Also': [],
            'Notes': [],
            'Warnings': [],
            'References': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def __getitem__(self,key):
        return self._parsed_data[key]

    def __setitem__(self,key,val):
        if not self._parsed_data.has_key(key):
            warn("Unknown section %s" % key)
        else:
            self._parsed_data[key] = val

    def _is_at_section(self):
        self._doc.seek_next_non_empty_line()

        if self._doc.eof():
            return False

        l1 = self._doc.peek().strip()  # e.g. Parameters

        if l1.startswith('.. index::'):
            return True

        l2 = self._doc.peek(1).strip() #    ---------- or ==========
        return l2.startswith('-'*len(l1)) or l2.startswith('='*len(l1))

    def _strip(self,doc):
        i = 0
        j = 0
        for i,line in enumerate(doc):
            if line.strip(): break

        for j,line in enumerate(doc[::-1]):
            if line.strip(): break

        return doc[i:len(doc)-j]

    def _read_to_next_section(self):
        section = self._doc.read_to_next_empty_line()

        while not self._is_at_section() and not self._doc.eof():
            if not self._doc.peek(-1).strip(): # previous line was empty
                section += ['']

            section += self._doc.read_to_next_empty_line()

        return section

    def _read_sections(self):
        while not self._doc.eof():
            data = self._read_to_next_section()
            name = data[0].strip()

            if name.startswith('..'): # index section
                yield name, data[1:]
            elif len(data) < 2:
                yield StopIteration
            else:
                yield name, self._strip(data[2:])

    def _parse_param_list(self,content):
        r = Reader(content)
        params = []
        while not r.eof():
            header = r.read().strip()
            if ' : ' in header:
                arg_name, arg_type = header.split(' : ')[:2]
            else:
                arg_name, arg_type = header, ''

            desc = r.read_to_next_unindented_line()
            desc = dedent_lines(desc)

            params.append((arg_name,arg_type,desc))

        return params


    _name_rgx = re.compile(r"^\s*(:(?P<role>\w+):`(?P<name>[a-zA-Z0-9_.-]+)`|"
                           r" (?P<name2>[a-zA-Z0-9_.-]+))\s*", re.X)
    def _parse_see_also(self, content):
        """
        func_name : Descriptive text
            continued text
        another_func_name : Descriptive text
        func_name1, func_name2, :meth:`func_name`, func_name3

        """
        items = []

        def parse_item_name(text):
            """Match ':role:`name`' or 'name'"""
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None
                else:
                    return g[2], g[1]
            raise ValueError("%s is not a item name" % text)

        def push_item(name, rest):
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        current_func = None
        rest = []

        for line in content:
            if not line.strip(): continue

            m = self._name_rgx.match(line)
            if m and line[m.end():].strip().startswith(':'):
                push_item(current_func, rest)
                current_func, line = line[:m.end()], line[m.end():]
                rest = [line.split(':', 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(' '):
                push_item(current_func, rest)
                current_func = None
                if ',' in line:
                    for func in line.split(','):
                        if func.strip():
                            push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)
        return items

    def _parse_index(self, section, content):
        """
        .. index: default
           :refguide: something, else, and more

        """
        def strip_each_in(lst):
            return [s.strip() for s in lst]

        out = {}
        section = section.split('::')
        if len(section) > 1:
            out['default'] = strip_each_in(section[1].split(','))[0]
        for line in content:
            line = line.split(':')
            if len(line) > 2:
                out[line[1]] = strip_each_in(line[2].split(','))
        return out

    def _parse_summary(self):
        """Grab signature (if given) and summary"""
        if self._is_at_section():
            return

        summary = self._doc.read_to_next_empty_line()
        summary_str = " ".join([s.strip() for s in summary]).strip()
        if re.compile('^([\w., ]+=)?\s*[\w\.]+\(.*\)$').match(summary_str):
            self['Signature'] = summary_str
            if not self._is_at_section():
                self['Summary'] = self._doc.read_to_next_empty_line()
        else:
            self['Summary'] = summary

        if not self._is_at_section():
            self['Extended Summary'] = self._read_to_next_section()

    def _parse(self):
        self._doc.reset()
        self._parse_summary()

        for (section,content) in self._read_sections():
            if not section.startswith('..'):
                section = ' '.join([s.capitalize() for s in section.split(' ')])
            if section in ('Parameters', 'Returns', 'Raises', 'Warns',
                           'Other Parameters', 'Attributes', 'Methods'):
                self[section] = self._parse_param_list(content)
            elif section.startswith('.. index::'):
                self['index'] = self._parse_index(section, content)
            elif section == 'See Also':
                self['See Also'] = self._parse_see_also(content)
            else:
                self[section] = content

    # string conversion routines

    def _str_header(self, name, symbol='-'):
        return [name, len(name)*symbol]

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        if self['Signature']:
            return [self['Signature'].replace('*','\*')] + ['']
        else:
            return ['']

    def _str_summary(self):
        if self['Summary']:
            return self['Summary'] + ['']
        else:
            return []

    def _str_extended_summary(self):
        if self['Extended Summary']:
            return self['Extended Summary'] + ['']
        else:
            return []

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            for param,param_type,desc in self[name]:
                out += ['%s : %s' % (param, param_type)]
                out += self._str_indent(desc)
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += self[name]
            out += ['']
        return out

    def _str_see_also(self, func_role):
        if not self['See Also']: return []
        out = []
        out += self._str_header("See Also")
        last_had_desc = True
        for func, desc, role in self['See Also']:
            if role:
                link = ':%s:`%s`' % (role, func)
            elif func_role:
                link = ':%s:`%s`' % (func_role, func)
            else:
                link = "`%s`_" % func
            if desc or last_had_desc:
                out += ['']
                out += [link]
            else:
                out[-1] += ", %s" % link
            if desc:
                out += self._str_indent([' '.join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        out += ['']
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            out += ['   :%s: %s' % (section, ', '.join(references))]
        return out

    def __str__(self, func_role=''):
        out = []
        out += self._str_signature()
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Other Parameters',
                           'Raises', 'Warns'):
            out += self._str_param_list(param_list)
        out += self._str_section('Warnings')
        out += self._str_see_also(func_role)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
        for param_list in ('Attributes', 'Methods'):
            out += self._str_param_list(param_list)
        out += self._str_index()
        return '\n'.join(out)


def indent(str,indent=4):
    indent_str = ' '*indent
    if str is None:
        return indent_str
    lines = str.split('\n')
    return '\n'.join(indent_str + l for l in lines)

def dedent_lines(lines):
    """Deindent a list of lines maximally"""
    return textwrap.dedent("\n".join(lines)).split("\n")

def header(text, style='-'):
    return text + '\n' + style*len(text) + '\n'


class FunctionDoc(NumpyDocString):
    def __init__(self, func, role='func', doc=None, config={}):
        self._f = func
        self._role = role # e.g. "func" or "meth"

        if doc is None:
            if func is None:
                raise ValueError("No function or docstring given")
            doc = inspect.getdoc(func) or ''
        NumpyDocString.__init__(self, doc)

        if not self['Signature'] and func is not None:
            func, func_name = self.get_func()
            try:
                # try to read signature
                argspec = inspect.getargspec(func)
                argspec = inspect.formatargspec(*argspec)
                argspec = argspec.replace('*','\*')
                signature = '%s%s' % (func_name, argspec)
            except TypeError, e:
                signature = '%s()' % func_name
            self['Signature'] = signature

    def get_func(self):
        func_name = getattr(self._f, '__name__', self.__class__.__name__)
        if inspect.isclass(self._f):
            func = getattr(self._f, '__call__', self._f.__init__)
        else:
            func = self._f
        return func, func_name

    def __str__(self):
        out = ''

        func, func_name = self.get_func()
        signature = self['Signature'].replace('*', '\*')

        roles = {'func': 'function',
                 'meth': 'method'}

        if self._role:
            if not roles.has_key(self._role):
                print "Warning: invalid role %s" % self._role
            out += '.. %s:: %s\n    \n\n' % (roles.get(self._role,''),
                                             func_name)

        out += super(FunctionDoc, self).__str__(func_role=self._role)
        return out


class ClassDoc(NumpyDocString):

    extra_public_methods = ['__call__']

    def __init__(self, cls, doc=None, modulename='', func_doc=FunctionDoc,
                 config={}):
        if not inspect.isclass(cls) and cls is not None:
            raise ValueError("Expected a class or None, but got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename

        if doc is None:
            if cls is None:
                raise ValueError("No class or documentation string given")
            doc = pydoc.getdoc(cls)

        NumpyDocString.__init__(self, doc)

        if config.get('show_class_members', True):
            if not self['Methods']:
                self['Methods'] = [(name, '', '')
                                   for name in sorted(self.methods)]
            if not self['Attributes']:
                self['Attributes'] = [(name, '', '')
                                      for name in sorted(self.properties)]

    @property
    def methods(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if ((not name.startswith('_')
                     or name in self.extra_public_methods)
                    and callable(func))]

    @property
    def properties(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and func is None]

########NEW FILE########
__FILENAME__ = docscrape_sphinx
import re, inspect, textwrap, pydoc
import sphinx
from docscrape import NumpyDocString, FunctionDoc, ClassDoc

class SphinxDocString(NumpyDocString):
    def __init__(self, docstring, config={}):
        self.use_plots = config.get('use_plots', False)
        NumpyDocString.__init__(self, docstring, config=config)

    # string conversion routines
    def _str_header(self, name, symbol='`'):
        return ['.. rubric:: ' + name, '']

    def _str_field_list(self, name):
        return [':' + name + ':']

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        return ['']
        if self['Signature']:
            return ['``%s``' % self['Signature']] + ['']
        else:
            return ['']

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Extended Summary'] + ['']

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_field_list(name)
            out += ['']
            for param,param_type,desc in self[name]:
                out += self._str_indent(['**%s** : %s' % (param.strip(),
                                                          param_type)])
                out += ['']
                out += self._str_indent(desc,8)
                out += ['']
        return out

    @property
    def _obj(self):
        if hasattr(self, '_cls'):
            return self._cls
        elif hasattr(self, '_f'):
            return self._f
        return None

    def _str_member_list(self, name):
        """
        Generate a member listing, autosummary:: table where possible,
        and a table where not.

        """
        out = []
        if self[name]:
            out += ['.. rubric:: %s' % name, '']
            prefix = getattr(self, '_name', '')

            if prefix:
                prefix = '~%s.' % prefix

            autosum = []
            others = []
            for param, param_type, desc in self[name]:
                param = param.strip()
                if not self._obj or hasattr(self._obj, param):
                    autosum += ["   %s%s" % (prefix, param)]
                else:
                    others.append((param, param_type, desc))

            if autosum:
                out += ['.. autosummary::', '   :toctree:', '']
                out += autosum

            if others:
                maxlen_0 = max([len(x[0]) for x in others])
                maxlen_1 = max([len(x[1]) for x in others])
                hdr = "="*maxlen_0 + "  " + "="*maxlen_1 + "  " + "="*10
                fmt = '%%%ds  %%%ds  ' % (maxlen_0, maxlen_1)
                n_indent = maxlen_0 + maxlen_1 + 4
                out += [hdr]
                for param, param_type, desc in others:
                    out += [fmt % (param.strip(), param_type)]
                    out += self._str_indent(desc, n_indent)
                out += [hdr]
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += ['']
            content = textwrap.dedent("\n".join(self[name])).split("\n")
            out += content
            out += ['']
        return out

    def _str_see_also(self, func_role):
        out = []
        if self['See Also']:
            see_also = super(SphinxDocString, self)._str_see_also(func_role)
            out = ['.. seealso::', '']
            out += self._str_indent(see_also[2:])
        return out

    def _str_warnings(self):
        out = []
        if self['Warnings']:
            out = ['.. warning::', '']
            out += self._str_indent(self['Warnings'])
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        if len(idx) == 0:
            return out

        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            elif section == 'refguide':
                out += ['   single: %s' % (', '.join(references))]
            else:
                out += ['   %s: %s' % (section, ','.join(references))]
        return out

    def _str_references(self):
        out = []
        if self['References']:
            out += self._str_header('References')
            if isinstance(self['References'], str):
                self['References'] = [self['References']]
            out.extend(self['References'])
            out += ['']
            # Latex collects all references to a separate bibliography,
            # so we need to insert links to it
            if sphinx.__version__ >= "0.6":
                out += ['.. only:: latex','']
            else:
                out += ['.. latexonly::','']
            items = []
            for line in self['References']:
                m = re.match(r'.. \[([a-z0-9._-]+)\]', line, re.I)
                if m:
                    items.append(m.group(1))
            out += ['   ' + ", ".join(["[%s]_" % item for item in items]), '']
        return out

    def _str_examples(self):
        examples_str = "\n".join(self['Examples'])

        if (self.use_plots and 'import matplotlib' in examples_str
                and 'plot::' not in examples_str):
            out = []
            out += self._str_header('Examples')
            out += ['.. plot::', '']
            out += self._str_indent(self['Examples'])
            out += ['']
            return out
        else:
            return self._str_section('Examples')

    def __str__(self, indent=0, func_role="obj"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Other Parameters',
                           'Raises', 'Warns'):
            out += self._str_param_list(param_list)
        out += self._str_warnings()
        out += self._str_see_also(func_role)
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_examples()
        for param_list in ('Attributes', 'Methods'):
            out += self._str_member_list(param_list)
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class SphinxFunctionDoc(SphinxDocString, FunctionDoc):
    def __init__(self, obj, doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        FunctionDoc.__init__(self, obj, doc=doc, config=config)

class SphinxClassDoc(SphinxDocString, ClassDoc):
    def __init__(self, obj, doc=None, func_doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        ClassDoc.__init__(self, obj, doc=doc, func_doc=None, config=config)

class SphinxObjDoc(SphinxDocString):
    def __init__(self, obj, doc=None, config={}):
        self._f = obj
        SphinxDocString.__init__(self, doc, config=config)

def get_doc_object(obj, what=None, doc=None, config={}):
    if what is None:
        if inspect.isclass(obj):
            what = 'class'
        elif inspect.ismodule(obj):
            what = 'module'
        elif callable(obj):
            what = 'function'
        else:
            what = 'object'
    if what == 'class':
        return SphinxClassDoc(obj, func_doc=SphinxFunctionDoc, doc=doc,
                              config=config)
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, doc=doc, config=config)
    else:
        if doc is None:
            doc = pydoc.getdoc(obj)
        return SphinxObjDoc(obj, doc, config=config)

########NEW FILE########
__FILENAME__ = linkcode
# -*- coding: utf-8 -*-
"""
    linkcode
    ~~~~~~~~

    Add external links to module code in Python object descriptions.

    :copyright: Copyright 2007-2011 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import warnings
warnings.warn("This extension has been submitted to Sphinx upstream. "
              "Use the version from there if it is accepted "
              "https://bitbucket.org/birkenfeld/sphinx/pull-request/47/sphinxextlinkcode",
              FutureWarning, stacklevel=1)


from docutils import nodes

from sphinx import addnodes
from sphinx.locale import _
from sphinx.errors import SphinxError

class LinkcodeError(SphinxError):
    category = "linkcode error"

def doctree_read(app, doctree):
    env = app.builder.env

    resolve_target = getattr(env.config, 'linkcode_resolve', None)
    if not callable(env.config.linkcode_resolve):
        raise LinkcodeError(
            "Function `linkcode_resolve` is not given in conf.py")

    domain_keys = dict(
        py=['module', 'fullname'],
        c=['names'],
        cpp=['names'],
        js=['object', 'fullname'],
    )

    for objnode in doctree.traverse(addnodes.desc):
        domain = objnode.get('domain')
        uris = set()
        for signode in objnode:
            if not isinstance(signode, addnodes.desc_signature):
                continue

            # Convert signode to a specified format
            info = {}
            for key in domain_keys.get(domain, []):
                value = signode.get(key)
                if not value:
                    value = ''
                info[key] = value
            if not info:
                continue

            # Call user code to resolve the link
            uri = resolve_target(domain, info)
            if not uri:
                # no source
                continue

            if uri in uris or not uri:
                # only one link per name, please
                continue
            uris.add(uri)

            onlynode = addnodes.only(expr='html')
            onlynode += nodes.reference('', '', internal=False, refuri=uri)
            onlynode[0] += nodes.inline('', _('[source]'),
                                        classes=['viewcode-link'])
            signode += onlynode

def setup(app):
    app.connect('doctree-read', doctree_read)
    app.add_config_value('linkcode_resolve', None, 'env')

########NEW FILE########
__FILENAME__ = numpydoc
"""
========
numpydoc
========

Sphinx extension that handles docstrings in the Numpy standard format. [1]

It will:

- Convert Parameters etc. sections to field lists.
- Convert See Also section to a See also entry.
- Renumber references.
- Extract the signature from the docstring, if it can't be determined otherwise.

.. [1] https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt

"""

import sphinx

if sphinx.__version__ < '1.0.1':
    raise RuntimeError("Sphinx 1.0.1 or newer is required")

import os, re, pydoc
from docscrape_sphinx import get_doc_object, SphinxDocString
from sphinx.util.compat import Directive
import inspect

def mangle_docstrings(app, what, name, obj, options, lines,
                      reference_offset=[0]):

    cfg = dict(use_plots=app.config.numpydoc_use_plots,
               show_class_members=app.config.numpydoc_show_class_members)

    if what == 'module':
        # Strip top title
        title_re = re.compile(ur'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                              re.I|re.S)
        lines[:] = title_re.sub(u'', u"\n".join(lines)).split(u"\n")
    else:
        doc = get_doc_object(obj, what, u"\n".join(lines), config=cfg)
        lines[:] = unicode(doc).split(u"\n")

    if app.config.numpydoc_edit_link and hasattr(obj, '__name__') and \
           obj.__name__:
        if hasattr(obj, '__module__'):
            v = dict(full_name=u"%s.%s" % (obj.__module__, obj.__name__))
        else:
            v = dict(full_name=obj.__name__)
        lines += [u'', u'.. htmlonly::', '']
        lines += [u'    %s' % x for x in
                  (app.config.numpydoc_edit_link % v).split("\n")]

    # replace reference numbers so that there are no duplicates
    references = []
    for line in lines:
        line = line.strip()
        m = re.match(ur'^.. \[([a-z0-9_.-])\]', line, re.I)
        if m:
            references.append(m.group(1))

    # start renaming from the longest string, to avoid overwriting parts
    references.sort(key=lambda x: -len(x))
    if references:
        for i, line in enumerate(lines):
            for r in references:
                if re.match(ur'^\d+$', r):
                    new_r = u"R%d" % (reference_offset[0] + int(r))
                else:
                    new_r = u"%s%d" % (r, reference_offset[0])
                lines[i] = lines[i].replace(u'[%s]_' % r,
                                            u'[%s]_' % new_r)
                lines[i] = lines[i].replace(u'.. [%s]' % r,
                                            u'.. [%s]' % new_r)

    reference_offset[0] += len(references)

def mangle_signature(app, what, name, obj, options, sig, retann):
    # Do not try to inspect classes that don't define `__init__`
    if (inspect.isclass(obj) and
        (not hasattr(obj, '__init__') or
        'initializes x; see ' in pydoc.getdoc(obj.__init__))):
        return '', ''

    if not (callable(obj) or hasattr(obj, '__argspec_is_invalid_')): return
    if not hasattr(obj, '__doc__'): return

    doc = SphinxDocString(pydoc.getdoc(obj))
    if doc['Signature']:
        sig = re.sub(u"^[^(]*", u"", doc['Signature'])
        return sig, u''

def setup(app, get_doc_object_=get_doc_object):
    global get_doc_object
    get_doc_object = get_doc_object_

    app.connect('autodoc-process-docstring', mangle_docstrings)
    app.connect('autodoc-process-signature', mangle_signature)
    app.add_config_value('numpydoc_edit_link', None, False)
    app.add_config_value('numpydoc_use_plots', None, False)
    app.add_config_value('numpydoc_show_class_members', True, True)

    # Extra mangling domains
    app.add_domain(NumpyPythonDomain)
    app.add_domain(NumpyCDomain)

#------------------------------------------------------------------------------
# Docstring-mangling domains
#------------------------------------------------------------------------------

from docutils.statemachine import ViewList
from sphinx.domains.c import CDomain
from sphinx.domains.python import PythonDomain

class ManglingDomainBase(object):
    directive_mangling_map = {}

    def __init__(self, *a, **kw):
        super(ManglingDomainBase, self).__init__(*a, **kw)
        self.wrap_mangling_directives()

    def wrap_mangling_directives(self):
        for name, objtype in self.directive_mangling_map.items():
            self.directives[name] = wrap_mangling_directive(
                self.directives[name], objtype)

class NumpyPythonDomain(ManglingDomainBase, PythonDomain):
    name = 'np'
    directive_mangling_map = {
        'function': 'function',
        'class': 'class',
        'exception': 'class',
        'method': 'function',
        'classmethod': 'function',
        'staticmethod': 'function',
        'attribute': 'attribute',
    }

class NumpyCDomain(ManglingDomainBase, CDomain):
    name = 'np-c'
    directive_mangling_map = {
        'function': 'function',
        'member': 'attribute',
        'macro': 'function',
        'type': 'class',
        'var': 'object',
    }

def wrap_mangling_directive(base_directive, objtype):
    class directive(base_directive):
        def run(self):
            env = self.state.document.settings.env

            name = None
            if self.arguments:
                m = re.match(r'^(.*\s+)?(.*?)(\(.*)?', self.arguments[0])
                name = m.group(2).strip()

            if not name:
                name = self.arguments[0]

            lines = list(self.content)
            mangle_docstrings(env.app, objtype, name, None, None, lines)
            self.content = ViewList(lines, self.content.parent)

            return base_directive.run(self)

    return directive


########NEW FILE########
__FILENAME__ = phantom_import
"""
==============
phantom_import
==============

Sphinx extension to make directives from ``sphinx.ext.autodoc`` and similar
extensions to use docstrings loaded from an XML file.

This extension loads an XML file in the Pydocweb format [1] and
creates a dummy module that contains the specified docstrings. This
can be used to get the current docstrings from a Pydocweb instance
without needing to rebuild the documented module.

.. [1] http://code.google.com/p/pydocweb

"""
import imp, sys, compiler, types, os, inspect, re

def setup(app):
    app.connect('builder-inited', initialize)
    app.add_config_value('phantom_import_file', None, True)

def initialize(app):
    fn = app.config.phantom_import_file
    if (fn and os.path.isfile(fn)):
        print "[numpydoc] Phantom importing modules from", fn, "..."
        import_phantom_module(fn)

#------------------------------------------------------------------------------
# Creating 'phantom' modules from an XML description
#------------------------------------------------------------------------------
def import_phantom_module(xml_file):
    """
    Insert a fake Python module to sys.modules, based on a XML file.

    The XML file is expected to conform to Pydocweb DTD. The fake
    module will contain dummy objects, which guarantee the following:

    - Docstrings are correct.
    - Class inheritance relationships are correct (if present in XML).
    - Function argspec is *NOT* correct (even if present in XML).
      Instead, the function signature is prepended to the function docstring.
    - Class attributes are *NOT* correct; instead, they are dummy objects.

    Parameters
    ----------
    xml_file : str
        Name of an XML file to read
    
    """
    import lxml.etree as etree

    object_cache = {}

    tree = etree.parse(xml_file)
    root = tree.getroot()

    # Sort items so that
    # - Base classes come before classes inherited from them
    # - Modules come before their contents
    all_nodes = dict([(n.attrib['id'], n) for n in root])
    
    def _get_bases(node, recurse=False):
        bases = [x.attrib['ref'] for x in node.findall('base')]
        if recurse:
            j = 0
            while True:
                try:
                    b = bases[j]
                except IndexError: break
                if b in all_nodes:
                    bases.extend(_get_bases(all_nodes[b]))
                j += 1
        return bases

    type_index = ['module', 'class', 'callable', 'object']
    
    def base_cmp(a, b):
        x = cmp(type_index.index(a.tag), type_index.index(b.tag))
        if x != 0: return x

        if a.tag == 'class' and b.tag == 'class':
            a_bases = _get_bases(a, recurse=True)
            b_bases = _get_bases(b, recurse=True)
            x = cmp(len(a_bases), len(b_bases))
            if x != 0: return x
            if a.attrib['id'] in b_bases: return -1
            if b.attrib['id'] in a_bases: return 1
        
        return cmp(a.attrib['id'].count('.'), b.attrib['id'].count('.'))

    nodes = root.getchildren()
    nodes.sort(base_cmp)

    # Create phantom items
    for node in nodes:
        name = node.attrib['id']
        doc = (node.text or '').decode('string-escape') + "\n"
        if doc == "\n": doc = ""

        # create parent, if missing
        parent = name
        while True:
            parent = '.'.join(parent.split('.')[:-1])
            if not parent: break
            if parent in object_cache: break
            obj = imp.new_module(parent)
            object_cache[parent] = obj
            sys.modules[parent] = obj

        # create object
        if node.tag == 'module':
            obj = imp.new_module(name)
            obj.__doc__ = doc
            sys.modules[name] = obj
        elif node.tag == 'class':
            bases = [object_cache[b] for b in _get_bases(node)
                     if b in object_cache]
            bases.append(object)
            init = lambda self: None
            init.__doc__ = doc
            obj = type(name, tuple(bases), {'__doc__': doc, '__init__': init})
            obj.__name__ = name.split('.')[-1]
        elif node.tag == 'callable':
            funcname = node.attrib['id'].split('.')[-1]
            argspec = node.attrib.get('argspec')
            if argspec:
                argspec = re.sub('^[^(]*', '', argspec)
                doc = "%s%s\n\n%s" % (funcname, argspec, doc)
            obj = lambda: 0
            obj.__argspec_is_invalid_ = True
            obj.func_name = funcname
            obj.__name__ = name
            obj.__doc__ = doc
            if inspect.isclass(object_cache[parent]):
                obj.__objclass__ = object_cache[parent]
        else:
            class Dummy(object): pass
            obj = Dummy()
            obj.__name__ = name
            obj.__doc__ = doc
            if inspect.isclass(object_cache[parent]):
                obj.__get__ = lambda: None
        object_cache[name] = obj

        if parent:
            if inspect.ismodule(object_cache[parent]):
                obj.__module__ = parent
                setattr(object_cache[parent], name.split('.')[-1], obj)

    # Populate items
    for node in root:
        obj = object_cache.get(node.attrib['id'])
        if obj is None: continue
        for ref in node.findall('ref'):
            if node.tag == 'class':
                if ref.attrib['ref'].startswith(node.attrib['id'] + '.'):
                    setattr(obj, ref.attrib['name'],
                            object_cache.get(ref.attrib['ref']))
            else:
                setattr(obj, ref.attrib['name'],
                        object_cache.get(ref.attrib['ref']))

########NEW FILE########
__FILENAME__ = plot_directive
"""
A special directive for generating a matplotlib plot.

.. warning::

   This is a hacked version of plot_directive.py from Matplotlib.
   It's very much subject to change!


Usage
-----

Can be used like this::

    .. plot:: examples/example.py

    .. plot::

       import matplotlib.pyplot as plt
       plt.plot([1,2,3], [4,5,6])

    .. plot::

       A plotting example:

       >>> import matplotlib.pyplot as plt
       >>> plt.plot([1,2,3], [4,5,6])

The content is interpreted as doctest formatted if it has a line starting
with ``>>>``.

The ``plot`` directive supports the options

    format : {'python', 'doctest'}
        Specify the format of the input

    include-source : bool
        Whether to display the source code. Default can be changed in conf.py
    
and the ``image`` directive options ``alt``, ``height``, ``width``,
``scale``, ``align``, ``class``.

Configuration options
---------------------

The plot directive has the following configuration options:

    plot_include_source
        Default value for the include-source option

    plot_pre_code
        Code that should be executed before each plot.

    plot_basedir
        Base directory, to which plot:: file names are relative to.
        (If None or empty, file names are relative to the directoly where
        the file containing the directive is.)

    plot_formats
        File formats to generate. List of tuples or strings::

            [(suffix, dpi), suffix, ...]

        that determine the file format and the DPI. For entries whose
        DPI was omitted, sensible defaults are chosen.

    plot_html_show_formats
        Whether to show links to the files in HTML.

TODO
----

* Refactor Latex output; now it's plain images, but it would be nice
  to make them appear side-by-side, or in floats.

"""

import sys, os, glob, shutil, imp, warnings, cStringIO, re, textwrap, traceback
import sphinx

import warnings
warnings.warn("A plot_directive module is also available under "
              "matplotlib.sphinxext; expect this numpydoc.plot_directive "
              "module to be deprecated after relevant features have been "
              "integrated there.",
              FutureWarning, stacklevel=2)


#------------------------------------------------------------------------------
# Registration hook
#------------------------------------------------------------------------------

def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir
    
    app.add_config_value('plot_pre_code', '', True)
    app.add_config_value('plot_include_source', False, True)
    app.add_config_value('plot_formats', ['png', 'hires.png', 'pdf'], True)
    app.add_config_value('plot_basedir', None, True)
    app.add_config_value('plot_html_show_formats', True, True)

    app.add_directive('plot', plot_directive, True, (0, 1, False),
                      **plot_directive_options)

#------------------------------------------------------------------------------
# plot:: directive
#------------------------------------------------------------------------------
from docutils.parsers.rst import directives
from docutils import nodes

def plot_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    return run(arguments, content, options, state_machine, state, lineno)
plot_directive.__doc__ = __doc__

def _option_boolean(arg):
    if not arg or not arg.strip():
        # no argument given, assume used as a flag
        return True
    elif arg.strip().lower() in ('no', '0', 'false'):
        return False
    elif arg.strip().lower() in ('yes', '1', 'true'):
        return True
    else:
        raise ValueError('"%s" unknown boolean' % arg)

def _option_format(arg):
    return directives.choice(arg, ('python', 'lisp'))

def _option_align(arg):
    return directives.choice(arg, ("top", "middle", "bottom", "left", "center",
                                   "right"))

plot_directive_options = {'alt': directives.unchanged,
                          'height': directives.length_or_unitless,
                          'width': directives.length_or_percentage_or_unitless,
                          'scale': directives.nonnegative_int,
                          'align': _option_align,
                          'class': directives.class_option,
                          'include-source': _option_boolean,
                          'format': _option_format,
                          }

#------------------------------------------------------------------------------
# Generating output
#------------------------------------------------------------------------------

from docutils import nodes, utils

try:
    # Sphinx depends on either Jinja or Jinja2
    import jinja2
    def format_template(template, **kw):
        return jinja2.Template(template).render(**kw)
except ImportError:
    import jinja
    def format_template(template, **kw):
        return jinja.from_string(template, **kw)

TEMPLATE = """
{{ source_code }}

{{ only_html }}

   {% if source_link or (html_show_formats and not multi_image) %}
   (
   {%- if source_link -%}
   `Source code <{{ source_link }}>`__
   {%- endif -%}
   {%- if html_show_formats and not multi_image -%}
     {%- for img in images -%}
       {%- for fmt in img.formats -%}
         {%- if source_link or not loop.first -%}, {% endif -%}
         `{{ fmt }} <{{ dest_dir }}/{{ img.basename }}.{{ fmt }}>`__
       {%- endfor -%}
     {%- endfor -%}
   {%- endif -%}
   )
   {% endif %}

   {% for img in images %}
   .. figure:: {{ build_dir }}/{{ img.basename }}.png
      {%- for option in options %}
      {{ option }}
      {% endfor %}

      {% if html_show_formats and multi_image -%}
        (
        {%- for fmt in img.formats -%}
        {%- if not loop.first -%}, {% endif -%}
        `{{ fmt }} <{{ dest_dir }}/{{ img.basename }}.{{ fmt }}>`__
        {%- endfor -%}
        )
      {%- endif -%}
   {% endfor %}

{{ only_latex }}

   {% for img in images %}
   .. image:: {{ build_dir }}/{{ img.basename }}.pdf
   {% endfor %}

"""

class ImageFile(object):
    def __init__(self, basename, dirname):
        self.basename = basename
        self.dirname = dirname
        self.formats = []

    def filename(self, format):
        return os.path.join(self.dirname, "%s.%s" % (self.basename, format))

    def filenames(self):
        return [self.filename(fmt) for fmt in self.formats]

def run(arguments, content, options, state_machine, state, lineno):
    if arguments and content:
        raise RuntimeError("plot:: directive can't have both args and content")

    document = state_machine.document
    config = document.settings.env.config

    options.setdefault('include-source', config.plot_include_source)

    # determine input
    rst_file = document.attributes['source']
    rst_dir = os.path.dirname(rst_file)

    if arguments:
        if not config.plot_basedir:
            source_file_name = os.path.join(rst_dir,
                                            directives.uri(arguments[0]))
        else:
            source_file_name = os.path.join(setup.confdir, config.plot_basedir,
                                            directives.uri(arguments[0]))
        code = open(source_file_name, 'r').read()
        output_base = os.path.basename(source_file_name)
    else:
        source_file_name = rst_file
        code = textwrap.dedent("\n".join(map(str, content)))
        counter = document.attributes.get('_plot_counter', 0) + 1
        document.attributes['_plot_counter'] = counter
        base, ext = os.path.splitext(os.path.basename(source_file_name))
        output_base = '%s-%d.py' % (base, counter)

    base, source_ext = os.path.splitext(output_base)
    if source_ext in ('.py', '.rst', '.txt'):
        output_base = base
    else:
        source_ext = ''

    # ensure that LaTeX includegraphics doesn't choke in foo.bar.pdf filenames
    output_base = output_base.replace('.', '-')

    # is it in doctest format?
    is_doctest = contains_doctest(code)
    if options.has_key('format'):
        if options['format'] == 'python':
            is_doctest = False
        else:
            is_doctest = True

    # determine output directory name fragment
    source_rel_name = relpath(source_file_name, setup.confdir)
    source_rel_dir = os.path.dirname(source_rel_name)
    while source_rel_dir.startswith(os.path.sep):
        source_rel_dir = source_rel_dir[1:]

    # build_dir: where to place output files (temporarily)
    build_dir = os.path.join(os.path.dirname(setup.app.doctreedir),
                             'plot_directive',
                             source_rel_dir)
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    # output_dir: final location in the builder's directory
    dest_dir = os.path.abspath(os.path.join(setup.app.builder.outdir,
                                            source_rel_dir))

    # how to link to files from the RST file
    dest_dir_link = os.path.join(relpath(setup.confdir, rst_dir),
                                 source_rel_dir).replace(os.path.sep, '/')
    build_dir_link = relpath(build_dir, rst_dir).replace(os.path.sep, '/')
    source_link = dest_dir_link + '/' + output_base + source_ext

    # make figures
    try:
        results = makefig(code, source_file_name, build_dir, output_base,
                          config)
        errors = []
    except PlotError, err:
        reporter = state.memo.reporter
        sm = reporter.system_message(
            2, "Exception occurred in plotting %s: %s" % (output_base, err),
            line=lineno)
        results = [(code, [])]
        errors = [sm]

    # generate output restructuredtext
    total_lines = []
    for j, (code_piece, images) in enumerate(results):
        if options['include-source']:
            if is_doctest:
                lines = ['']
                lines += [row.rstrip() for row in code_piece.split('\n')]
            else:
                lines = ['.. code-block:: python', '']
                lines += ['    %s' % row.rstrip()
                          for row in code_piece.split('\n')]
            source_code = "\n".join(lines)
        else:
            source_code = ""

        opts = [':%s: %s' % (key, val) for key, val in options.items()
                if key in ('alt', 'height', 'width', 'scale', 'align', 'class')]

        only_html = ".. only:: html"
        only_latex = ".. only:: latex"

        if j == 0:
            src_link = source_link
        else:
            src_link = None

        result = format_template(
            TEMPLATE,
            dest_dir=dest_dir_link,
            build_dir=build_dir_link,
            source_link=src_link,
            multi_image=len(images) > 1,
            only_html=only_html,
            only_latex=only_latex,
            options=opts,
            images=images,
            source_code=source_code,
            html_show_formats=config.plot_html_show_formats)

        total_lines.extend(result.split("\n"))
        total_lines.extend("\n")

    if total_lines:
        state_machine.insert_input(total_lines, source=source_file_name)

    # copy image files to builder's output directory
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for code_piece, images in results:
        for img in images:
            for fn in img.filenames():
                shutil.copyfile(fn, os.path.join(dest_dir,
                                                 os.path.basename(fn)))

    # copy script (if necessary)
    if source_file_name == rst_file:
        target_name = os.path.join(dest_dir, output_base + source_ext)
        f = open(target_name, 'w')
        f.write(unescape_doctest(code))
        f.close()

    return errors


#------------------------------------------------------------------------------
# Run code and capture figures
#------------------------------------------------------------------------------

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as image
from matplotlib import _pylab_helpers

import exceptions

def contains_doctest(text):
    try:
        # check if it's valid Python as-is
        compile(text, '<string>', 'exec')
        return False
    except SyntaxError:
        pass
    r = re.compile(r'^\s*>>>', re.M)
    m = r.search(text)
    return bool(m)

def unescape_doctest(text):
    """
    Extract code from a piece of text, which contains either Python code
    or doctests.

    """
    if not contains_doctest(text):
        return text

    code = ""
    for line in text.split("\n"):
        m = re.match(r'^\s*(>>>|\.\.\.) (.*)$', line)
        if m:
            code += m.group(2) + "\n"
        elif line.strip():
            code += "# " + line.strip() + "\n"
        else:
            code += "\n"
    return code

def split_code_at_show(text):
    """
    Split code at plt.show()

    """

    parts = []
    is_doctest = contains_doctest(text)

    part = []
    for line in text.split("\n"):
        if (not is_doctest and line.strip() == 'plt.show()') or \
               (is_doctest and line.strip() == '>>> plt.show()'):
            part.append(line)
            parts.append("\n".join(part))
            part = []
        else:
            part.append(line)
    if "\n".join(part).strip():
        parts.append("\n".join(part))
    return parts

class PlotError(RuntimeError):
    pass

def run_code(code, code_path, ns=None):
    # Change the working directory to the directory of the example, so
    # it can get at its data files, if any.
    pwd = os.getcwd()
    old_sys_path = list(sys.path)
    if code_path is not None:
        dirname = os.path.abspath(os.path.dirname(code_path))
        os.chdir(dirname)
        sys.path.insert(0, dirname)

    # Redirect stdout
    stdout = sys.stdout
    sys.stdout = cStringIO.StringIO()

    # Reset sys.argv
    old_sys_argv = sys.argv
    sys.argv = [code_path]
    
    try:
        try:
            code = unescape_doctest(code)
            if ns is None:
                ns = {}
            if not ns:
                exec setup.config.plot_pre_code in ns
            exec code in ns
        except (Exception, SystemExit), err:
            raise PlotError(traceback.format_exc())
    finally:
        os.chdir(pwd)
        sys.argv = old_sys_argv
        sys.path[:] = old_sys_path
        sys.stdout = stdout
    return ns


#------------------------------------------------------------------------------
# Generating figures
#------------------------------------------------------------------------------

def out_of_date(original, derived):
    """
    Returns True if derivative is out-of-date wrt original,
    both of which are full file paths.
    """
    return (not os.path.exists(derived)
            or os.stat(derived).st_mtime < os.stat(original).st_mtime)


def makefig(code, code_path, output_dir, output_base, config):
    """
    Run a pyplot script *code* and save the images under *output_dir*
    with file names derived from *output_base*

    """

    # -- Parse format list
    default_dpi = {'png': 80, 'hires.png': 200, 'pdf': 50}
    formats = []
    for fmt in config.plot_formats:
        if isinstance(fmt, str):
            formats.append((fmt, default_dpi.get(fmt, 80)))
        elif type(fmt) in (tuple, list) and len(fmt)==2:
            formats.append((str(fmt[0]), int(fmt[1])))
        else:
            raise PlotError('invalid image format "%r" in plot_formats' % fmt)

    # -- Try to determine if all images already exist

    code_pieces = split_code_at_show(code)

    # Look for single-figure output files first
    all_exists = True
    img = ImageFile(output_base, output_dir)
    for format, dpi in formats:
        if out_of_date(code_path, img.filename(format)):
            all_exists = False
            break
        img.formats.append(format)

    if all_exists:
        return [(code, [img])]

    # Then look for multi-figure output files
    results = []
    all_exists = True
    for i, code_piece in enumerate(code_pieces):
        images = []
        for j in xrange(1000):
            img = ImageFile('%s_%02d_%02d' % (output_base, i, j), output_dir)
            for format, dpi in formats:
                if out_of_date(code_path, img.filename(format)):
                    all_exists = False
                    break
                img.formats.append(format)

            # assume that if we have one, we have them all
            if not all_exists:
                all_exists = (j > 0)
                break
            images.append(img)
        if not all_exists:
            break
        results.append((code_piece, images))

    if all_exists:
        return results

    # -- We didn't find the files, so build them

    results = []
    ns = {}

    for i, code_piece in enumerate(code_pieces):
        # Clear between runs
        plt.close('all')

        # Run code
        run_code(code_piece, code_path, ns)

        # Collect images
        images = []
        fig_managers = _pylab_helpers.Gcf.get_all_fig_managers()
        for j, figman in enumerate(fig_managers):
            if len(fig_managers) == 1 and len(code_pieces) == 1:
                img = ImageFile(output_base, output_dir)
            else:
                img = ImageFile("%s_%02d_%02d" % (output_base, i, j),
                                output_dir)
            images.append(img)
            for format, dpi in formats:
                try:
                    figman.canvas.figure.savefig(img.filename(format), dpi=dpi)
                except exceptions.BaseException, err:
                    raise PlotError(traceback.format_exc())
                img.formats.append(format)

        # Results
        results.append((code_piece, images))

    return results


#------------------------------------------------------------------------------
# Relative pathnames
#------------------------------------------------------------------------------

try:
    from os.path import relpath
except ImportError:
    # Copied from Python 2.7
    if 'posix' in sys.builtin_module_names:
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""
            from os.path import sep, curdir, join, abspath, commonprefix, \
                 pardir

            if not path:
                raise ValueError("no path specified")

            start_list = abspath(start).split(sep)
            path_list = abspath(path).split(sep)

            # Work out how much of the filepath is shared by start and path.
            i = len(commonprefix([start_list, path_list]))

            rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return curdir
            return join(*rel_list)
    elif 'nt' in sys.builtin_module_names:
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""
            from os.path import sep, curdir, join, abspath, commonprefix, \
                 pardir, splitunc

            if not path:
                raise ValueError("no path specified")
            start_list = abspath(start).split(sep)
            path_list = abspath(path).split(sep)
            if start_list[0].lower() != path_list[0].lower():
                unc_path, rest = splitunc(path)
                unc_start, rest = splitunc(start)
                if bool(unc_path) ^ bool(unc_start):
                    raise ValueError("Cannot mix UNC and non-UNC paths (%s and %s)"
                                                                        % (path, start))
                else:
                    raise ValueError("path is on drive %s, start on drive %s"
                                                        % (path_list[0], start_list[0]))
            # Work out how much of the filepath is shared by start and path.
            for i in range(min(len(start_list), len(path_list))):
                if start_list[i].lower() != path_list[i].lower():
                    break
            else:
                i += 1

            rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return curdir
            return join(*rel_list)
    else:
        raise RuntimeError("Unsupported platform (no relpath available!)")

########NEW FILE########
__FILENAME__ = traitsdoc
"""
=========
traitsdoc
=========

Sphinx extension that handles docstrings in the Numpy standard format, [1]
and support Traits [2].

This extension can be used as a replacement for ``numpydoc`` when support
for Traits is required.

.. [1] http://projects.scipy.org/numpy/wiki/CodingStyleGuidelines#docstring-standard
.. [2] http://code.enthought.com/projects/traits/

"""

import inspect
import os
import pydoc

import docscrape
import docscrape_sphinx
from docscrape_sphinx import SphinxClassDoc, SphinxFunctionDoc, SphinxDocString

import numpydoc

import comment_eater

class SphinxTraitsDoc(SphinxClassDoc):
    def __init__(self, cls, modulename='', func_doc=SphinxFunctionDoc):
        if not inspect.isclass(cls):
            raise ValueError("Initialise using a class. Got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename
        self._name = cls.__name__
        self._func_doc = func_doc

        docstring = pydoc.getdoc(cls)
        docstring = docstring.split('\n')

        # De-indent paragraph
        try:
            indent = min(len(s) - len(s.lstrip()) for s in docstring
                         if s.strip())
        except ValueError:
            indent = 0

        for n,line in enumerate(docstring):
            docstring[n] = docstring[n][indent:]

        self._doc = docscrape.Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': '',
            'Description': [],
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'Other Parameters': [],
            'Traits': [],
            'Methods': [],
            'See Also': [],
            'Notes': [],
            'References': '',
            'Example': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Description'] + self['Extended Summary'] + ['']

    def __str__(self, indent=0, func_role="func"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Traits', 'Methods',
                           'Returns','Raises'):
            out += self._str_param_list(param_list)
        out += self._str_see_also("obj")
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_section('Example')
        out += self._str_section('Examples')
        out = self._str_indent(out,indent)
        return '\n'.join(out)

def looks_like_issubclass(obj, classname):
    """ Return True if the object has a class or superclass with the given class
    name.

    Ignores old-style classes.
    """
    t = obj
    if t.__name__ == classname:
        return True
    for klass in t.__mro__:
        if klass.__name__ == classname:
            return True
    return False

def get_doc_object(obj, what=None, config=None):
    if what is None:
        if inspect.isclass(obj):
            what = 'class'
        elif inspect.ismodule(obj):
            what = 'module'
        elif callable(obj):
            what = 'function'
        else:
            what = 'object'
    if what == 'class':
        doc = SphinxTraitsDoc(obj, '', func_doc=SphinxFunctionDoc, config=config)
        if looks_like_issubclass(obj, 'HasTraits'):
            for name, trait, comment in comment_eater.get_class_traits(obj):
                # Exclude private traits.
                if not name.startswith('_'):
                    doc['Traits'].append((name, trait, comment.splitlines()))
        return doc
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, '', config=config)
    else:
        return SphinxDocString(pydoc.getdoc(obj), config=config)

def setup(app):
    # init numpydoc
    numpydoc.setup(app, get_doc_object)


########NEW FILE########
__FILENAME__ = autoinit
#!/usr/bin/env python

"""
Autoinitialize CUDA tools.
"""

import atexit
import misc

try:
    import cula
    _has_cula = True
except (ImportError, OSError):
    _has_cula = False

misc.init()
if _has_cula:
    cula.culaInitialize()
atexit.register(misc.shutdown)

########NEW FILE########
__FILENAME__ = cublas
#!/usr/bin/env python

"""
Python interface to CUBLAS functions.

Note: this module does not explicitly depend on PyCUDA.
"""

import re
import os
import sys
import warnings
import ctypes
import ctypes.util
import atexit
import numpy as np

from string import Template

import cuda
import utils

if sys.platform == 'linux2':
    _libcublas_libname_list = ['libcublas.so', 'libcublas.so.4.0',
                               'libcublas.so.5.0', 'libcublas.so.6.0']
elif sys.platform == 'darwin':
    _libcublas_libname_list = ['libcublas.dylib']
elif sys.platform == 'Windows':
    _libcublas_libname_list = ['cublas.lib']
else:
    raise RuntimeError('unsupported platform')

# Print understandable error message when library cannot be found:
_libcublas = None
for _libcublas_libname in _libcublas_libname_list:
    try:
        _libcublas = ctypes.cdll.LoadLibrary(_libcublas_libname)
    except OSError:
        pass
    else:
        break
if _libcublas == None:
    raise OSError('cublas library not found')

# Generic CUBLAS error:
class cublasError(Exception):
    """CUBLAS error"""
    pass

# Exceptions corresponding to different CUBLAS errors:
class cublasNotInitialized(cublasError):
    """CUBLAS library not initialized."""
    pass

class cublasAllocFailed(cublasError):
    """Resource allocation failed."""
    pass

class cublasInvalidValue(cublasError):
    """Unsupported numerical value was passed to function."""
    pass

class cublasArchMismatch(cublasError):
    """Function requires an architectural feature absent from the device."""
    pass

class cublasMappingError(cublasError):
    """Access to GPU memory space failed."""
    pass

class cublasExecutionFailed(cublasError):
    """GPU program failed to execute."""
    pass

class cublasInternalError(cublasError):
    """An internal CUBLAS operation failed."""
    pass

cublasExceptions = {
    0x1: cublasNotInitialized,
    0x3: cublasAllocFailed,
    0x7: cublasInvalidValue,
    0x8: cublasArchMismatch,
    0xb: cublasMappingError,
    0xd: cublasExecutionFailed,
    0xe: cublasInternalError,
    }

_CUBLAS_OP = {
    0: 0,   # CUBLAS_OP_N
    'n': 0, 
    'N': 0,
    1: 1,   # CUBLAS_OP_T
    't': 1, 
    'T': 1,
    2: 2,   # CUBLAS_OP_C
    'c': 2, 
    'C': 2,
    }

_CUBLAS_FILL_MODE = {
    0: 0,   # CUBLAS_FILL_MODE_LOWER
    'l': 0, 
    'L': 0,
    1: 1,   # CUBLAS_FILL_MODE_UPPER
    'u': 1, 
    'U': 1,
    }

_CUBLAS_DIAG = {
    0: 0,   # CUBLAS_DIAG_NON_UNIT,
    'n': 0, 
    'N': 0,
    1: 1,   # CUBLAS_DIAG_UNIT
    'u': 1, 
    'U': 1,
    }

_CUBLAS_SIDE_MODE = {
    0: 0,   # CUBLAS_SIDE_LEFT
    'l': 0,
    'L': 0, 
    1: 1,   # CUBLAS_SIDE_RIGHT
    'r': 1,
    'r': 1  
    }

class _types:
    """Some alias types."""
    handle = ctypes.c_void_p
    stream = ctypes.c_void_p

def cublasCheckStatus(status):
    """
    Raise CUBLAS exception
    
    Raise an exception corresponding to the specified CUBLAS error
    code.
    
    Parameters
    ----------
    status : int
        CUBLAS error code.

    See Also
    --------
    cublasExceptions

    """
    
    if status != 0:
        try:
            raise cublasExceptions[status]
        except KeyError:
            raise cublasError
        
# Helper functions:
_libcublas.cublasCreate_v2.restype = int
_libcublas.cublasCreate_v2.argtypes = [_types.handle]
def cublasCreate():
    """
    Initialize CUBLAS.

    Initializes CUBLAS and creates a handle to a structure holding
    the CUBLAS library context.

    Returns
    -------
    handle : int
        CUBLAS context.
            
    """

    handle = _types.handle()
    status = _libcublas.cublasCreate_v2(ctypes.byref(handle))
    cublasCheckStatus(status)
    return handle.value    

_libcublas.cublasDestroy_v2.restype = int
_libcublas.cublasDestroy_v2.argtypes = [_types.handle]
def cublasDestroy(handle):
    """
    Release CUBLAS resources.

    Releases hardware resources used by CUBLAS.

    Parameters
    ----------
    handle : int
        CUBLAS context.
        
    """

    status = _libcublas.cublasDestroy_v2(handle)
    cublasCheckStatus(status)

_libcublas.cublasGetVersion_v2.restype = int
_libcublas.cublasGetVersion_v2.argtypes = [_types.handle,
                                           ctypes.c_void_p]
def cublasGetVersion(handle):
    """
    Get CUBLAS version.

    Returns version number of installed CUBLAS libraries.

    Parameters
    ----------
    handle : int
        CUBLAS context.

    Returns
    -------
    version : int
        CUBLAS version.

    """
    
    version = ctypes.c_int()
    status = _libcublas.cublasGetVersion_v2(handle, ctypes.byref(version))
    cublasCheckStatus(status)
    return version.value


# Get and save CUBLAS major version using the CUBLAS library's SONAME;
# this is done because creating a CUBLAS context can subtly affect the
# performance of subsequent CUDA operations in certain circumstances.
# We append zeros to match format of version returned by cublasGetVersion():
# XXX This approach to obtaining the CUBLAS version number
# may break Windows/MacOSX compatibility XXX
_cublas_path = utils.find_lib_path('cublas')
_cublas_version = int(re.search('[\D\.]\.+(\d)',
                                utils.get_soname(_cublas_path)).group(1) + '000')

class _cublas_version_req(object):
    """
    Decorator to replace function with a placeholder that raises an exception
    if the installed CUBLAS version is not greater than `v`.
    """

    def __init__(self, v):
        self.vs = str( v)
        self.vi = int(v*1000)

    def __call__(self,f):
        def f_new(*args,**kwargs):
            raise NotImplementedError('CUBLAS '+self.vs+' required')
        f_new.__doc__ = f.__doc__

        if _cublas_version >= self.vi:
            return f
        else:
            return f_new

_libcublas.cublasSetStream_v2.restype = int
_libcublas.cublasSetStream_v2.argtypes = [_types.handle,
                                          _types.stream]
def cublasSetStream(handle, id):
    """
    Set current CUBLAS library stream.
    
    Parameters
    ----------
    handle : id
        CUBLAS context.
    id : int
        Stream ID.

    """

    status = _libcublas.cublasSetStream_v2(handle, id)
    cublasCheckStatus(status)

_libcublas.cublasGetStream_v2.restype = int
_libcublas.cublasGetStream_v2.argtypes = [_types.handle,
                                          ctypes.c_void_p]
def cublasGetStream(handle):
    """
    Set current CUBLAS library stream.

    Parameters
    ----------
    handle : int
        CUBLAS context.
  
    Returns
    -------
    id : int
        Stream ID.
  
    """
    
    id = _types.stream()
    status = _libcublas.cublasGetStream_v2(handle, ctypes.byref(id))
    cublasCheckStatus(status)
    return id.value

try:
    _libcublas.cublasGetCurrentCtx.restype = int
except AttributeError:
    def cublasGetCurrentCtx():
        raise NotImplementedError(
            'cublasGetCurrentCtx() not found; CULA CUBLAS library probably\n'
            'precedes NVIDIA CUBLAS library in library search path')
else:
    def cublasGetCurrentCtx():
        return _libcublas.cublasGetCurrentCtx()
cublasGetCurrentCtx.__doc__ = """
    Get current CUBLAS context.

    Returns the current context used by CUBLAS.

    Returns
    -------
    handle : int
        CUBLAS context.

"""

### BLAS Level 1 Functions ###

# ISAMAX, IDAMAX, ICAMAX, IZAMAX
I_AMAX_doc = Template(
"""
    Index of maximum magnitude element.

    Finds the smallest index of the maximum magnitude element of a
    ${precision} ${real} vector.

    Note: for complex arguments x, the "magnitude" is defined as 
    `abs(x.real) + abs(x.imag)`, *not* as `abs(x)`.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vector.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input vector.
    incx : int
        Storage spacing between elements of `x`.

    Returns
    -------
    idx : int
        Index of maximum magnitude element.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data} 
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> h = cublasCreate()
    >>> m = ${func}(h, x_gpu.size, x_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(m, np.argmax(abs(x.real) + abs(x.imag)))
    True
    
    Notes
    -----
    This function returns a 0-based index.
    
""")

_libcublas.cublasIsamax_v2.restype = int
_libcublas.cublasIsamax_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIsamax(handle, n, x, incx):
    result = ctypes.c_int()    
    status = \
           _libcublas.cublasIsamax_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1

cublasIsamax.__doc__ = \
                     I_AMAX_doc.substitute(precision='single-precision',
                                           real='real',
                                           data='np.random.rand(5).astype(np.float32)',
                                           func='cublasIsamax')

_libcublas.cublasIdamax_v2.restype = int
_libcublas.cublasIdamax_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIdamax(handle, n, x, incx):
    result = ctypes.c_int()
    status = \
           _libcublas.cublasIdamax_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1

cublasIdamax.__doc__ = \
                     I_AMAX_doc.substitute(precision='double-precision',
                                           real='real',
                                           data='np.random.rand(5).astype(np.float64)',
                                           func='cublasIdamax')

_libcublas.cublasIcamax_v2.restype = int
_libcublas.cublasIcamax_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIcamax(handle, n, x, incx):
    result = ctypes.c_int()
    status = \
           _libcublas.cublasIcamax_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1

cublasIcamax.__doc__ = \
                     I_AMAX_doc.substitute(precision='single precision',
                                           real='complex',
                                           data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                           func='cublasIcamax')

_libcublas.cublasIzamax_v2.restype = int
_libcublas.cublasIzamax_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIzamax(handle, n, x, incx):
    result = ctypes.c_int()
    status = \
           _libcublas.cublasIzamax_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1
    
cublasIzamax.__doc__ = \
                     I_AMAX_doc.substitute(precision='double precision',
                                           real='complex',
                                           data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                           func='cublasIzamax')

# ISAMIN, IDAMIN, ICAMIN, IZAMIN
I_AMIN_doc = Template(
"""
    Index of minimum magnitude element (${precision} ${real}).

    Finds the smallest index of the minimum magnitude element of a
    ${precision} ${real} vector.

    Note: for complex arguments x, the "magnitude" is defined as 
    `abs(x.real) + abs(x.imag)`, *not* as `abs(x)`.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vector.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input vector.
    incx : int
        Storage spacing between elements of `x`.

    Returns
    -------
    idx : int
        Index of minimum magnitude element.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> h = cublasCreate()
    >>> m = ${func}(h, x_gpu.size, x_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(m, np.argmin(abs(x.real) + abs(x.imag)))
    True

    Notes
    -----
    This function returns a 0-based index.

    """
)

_libcublas.cublasIsamin_v2.restype = int
_libcublas.cublasIsamin_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIsamin(handle, n, x, incx):
    result = ctypes.c_int()
    status = \
           _libcublas.cublasIsamin_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1

cublasIsamin.__doc__ = \
                     I_AMIN_doc.substitute(precision='single-precision',
                                           real='real',
                                           data='np.random.rand(5).astype(np.float32)',
                                           func='cublasIsamin')

_libcublas.cublasIdamin_v2.restype = int
_libcublas.cublasIdamin_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIdamin(handle, n, x, incx):
    result = ctypes.c_int()
    status = \
           _libcublas.cublasIdamin_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1

cublasIdamin.__doc__ = \
                     I_AMIN_doc.substitute(precision='double-precision',
                                           real='real',
                                           data='np.random.rand(5).astype(np.float64)',
                                           func='cublasIdamin')

_libcublas.cublasIcamin_v2.restype = int
_libcublas.cublasIcamin_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIcamin(handle, n, x, incx):
    result = ctypes.c_int()
    status = \
           _libcublas.cublasIcamin_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1

cublasIcamin.__doc__ = \
                     I_AMIN_doc.substitute(precision='single-precision',
                                           real='complex',
                                           data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                           func='cublasIcamin')

_libcublas.cublasIzamin_v2.restype = int
_libcublas.cublasIzamin_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasIzamin(handle, n, x, incx):
    result = ctypes.c_int()
    status = \
           _libcublas.cublasIzamin_v2(handle,
                                      n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return result.value-1

cublasIzamin.__doc__ = \
                     I_AMIN_doc.substitute(precision='double-precision',
                                           real='complex',
                                           data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                           func='cublasIzamin')

# SASUM, DASUM, SCASUM, DZASUM
_ASUM_doc = Template(                    
"""
    Sum of absolute values of ${precision} ${real} vector.

    Computes the sum of the absolute values of the elements of a
    ${precision} ${real} vector.

    Note: if the vector is complex, then this computes the sum 
    `sum(abs(x.real)) + sum(abs(x.imag))`

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vector.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input vector.
    incx : int
        Storage spacing between elements of `x`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> h = cublasCreate()
    >>> s = ${func}(h, x_gpu.size, x_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(s, abs(x.real).sum() + abs(x.imag).sum())
    True

    Returns
    -------
    s : ${ret_type}
        Sum of absolute values.
        
    """
)

_libcublas.cublasSasum_v2.restype = int
_libcublas.cublasSasum_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasSasum(handle, n, x, incx):
    result = ctypes.c_float()
    status = _libcublas.cublasSasum_v2(handle,
                                       n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float32(result.value)

cublasSasum.__doc__ = \
                    _ASUM_doc.substitute(precision='single-precision',
                                         real='real',
                                         data='np.random.rand(5).astype(np.float32)',
                                         func='cublasSasum',
                                         ret_type='numpy.float32')

_libcublas.cublasDasum_v2.restype = int
_libcublas.cublasDasum_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasDasum(handle, n, x, incx):
    result = ctypes.c_double()
    status = _libcublas.cublasDasum_v2(handle,
                                       n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float64(result.value)

cublasDasum.__doc__ = \
                    _ASUM_doc.substitute(precision='double-precision',
                                         real='real',
                                         data='np.random.rand(5).astype(np.float64)',
                                         func='cublasDasum',
                                         ret_type='numpy.float64')

_libcublas.cublasScasum_v2.restype = int
_libcublas.cublasScasum_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasScasum(handle, n, x, incx):
    result = ctypes.c_float()
    status = _libcublas.cublasScasum_v2(handle,
                                        n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float32(result.value)
    
cublasScasum.__doc__ = \
                     _ASUM_doc.substitute(precision='single-precision',
                                          real='complex',
                                          data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                          func='cublasScasum',
                                          ret_type='numpy.float32')

_libcublas.cublasDzasum_v2.restype = int
_libcublas.cublasDzasum_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasDzasum(handle, n, x, incx):
    result = ctypes.c_double()
    status = _libcublas.cublasDzasum_v2(handle,
                                        n, int(x), incx, ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float64(result.value)

cublasDzasum.__doc__ = \
                     _ASUM_doc.substitute(precision='double-precision',
                                          real='complex',
                                          data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                          func='cublasDzasum',
                                          ret_type='numpy.float64')

# SAXPY, DAXPY, CAXPY, ZAXPY
_AXPY_doc = Template(
"""
    Vector addition (${precision} ${real}).

    Computes the sum of a ${precision} ${real} vector scaled by a
    ${precision} ${real} scalar and another ${precision} ${real} vector.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    alpha : ${type}
        Scalar.
    x : ctypes.c_void_p
        Pointer to single-precision input vector.
    incx : int
        Storage spacing between elements of `x`.
    y : ctypes.c_void_p
        Pointer to single-precision input/output vector.
    incy : int
        Storage spacing between elements of `y`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> alpha = ${alpha} 
    >>> x = ${data}
    >>> y = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = gpuarray.to_gpu(y)
    >>> h = cublasCreate()
    >>> ${func}(h, x_gpu.size, alpha, x_gpu.gpudata, 1, y_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(y_gpu.get(), alpha*x+y)
    True

    Notes
    -----
    Both `x` and `y` must contain `n` elements.
    
    """
)

_libcublas.cublasSaxpy_v2.restype = int
_libcublas.cublasSaxpy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSaxpy(handle, n, alpha, x, incx, y, incy):
    status = _libcublas.cublasSaxpy_v2(handle,
                                       n, ctypes.byref(ctypes.c_float(alpha)),
                                       int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasSaxpy.__doc__ = \
                    _AXPY_doc.substitute(precision='single-precision',
                                         real='real',
                                         type='numpy.float32',
                                         alpha='np.float32(np.random.rand())',
                                         data='np.random.rand(5).astype(np.float32)',
                                         func='cublasSaxpy')

_libcublas.cublasDaxpy_v2.restype = int
_libcublas.cublasDaxpy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDaxpy(handle, n, alpha, x, incx, y, incy):
    status = _libcublas.cublasDaxpy_v2(handle,
                                       n, ctypes.byref(ctypes.c_double(alpha)),
                                       int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasDaxpy.__doc__ = \
                    _AXPY_doc.substitute(precision='double-precision',
                                         real='real',
                                         type='numpy.float64',
                                         alpha='np.float64(np.random.rand())',
                                         data='np.random.rand(5).astype(np.float64)',
                                         func='cublasDaxpy')

_libcublas.cublasCaxpy_v2.restype = int
_libcublas.cublasCaxpy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCaxpy(handle, n, alpha, x, incx, y, incy):
    status = _libcublas.cublasCaxpy_v2(handle, n,
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real, alpha.imag)),
                                       int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasCaxpy.__doc__ = \
                    _AXPY_doc.substitute(precision='single-precision',
                                         real='complex',
                                         type='numpy.complex64',
                                         alpha='np.complex64(np.random.rand()+1j*np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',             
                                         func='cublasCaxpy')

_libcublas.cublasZaxpy_v2.restype = int
_libcublas.cublasZaxpy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZaxpy(handle, n, alpha, x, incx, y, incy):
    status = _libcublas.cublasZaxpy_v2(handle, n,
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real, alpha.imag)),
                                       int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasZaxpy.__doc__ = \
                    _AXPY_doc.substitute(precision='double-precision',
                                         real='complex',
                                         type='numpy.complex128',
                                         alpha='np.complex128(np.random.rand()+1j*np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',             
                                         func='cublasZaxpy')

# SCOPY, DCOPY, CCOPY, ZCOPY
_COPY_doc = Template(
"""
    Vector copy (${precision} ${real})

    Copies a ${precision} ${real} vector to another ${precision} ${real}
    vector.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input vector.
    incx : int
        Storage spacing between elements of `x`.
    y : ctypes.c_void_p
        Pointer to ${precision} ${real} output vector.
    incy : int
        Storage spacing between elements of `y`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = gpuarray.zeros_like(x_gpu)
    >>> h = cublasCreate()
    >>> ${func}(h, x_gpu.size, x_gpu.gpudata, 1, y_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(y_gpu.get(), x_gpu.get())
    True
    
    Notes
    -----
    Both `x` and `y` must contain `n` elements.

""")

_libcublas.cublasScopy_v2.restype = int
_libcublas.cublasScopy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasScopy(handle, n, x, incx, y, incy):
    status = _libcublas.cublasScopy_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)
                
cublasScopy.__doc__ = \
                    _COPY_doc.substitute(precision='single-precision',
                                         real='real',
                                         data='np.random.rand(5).astype(np.float32)',
                                         func='cublasScopy')

_libcublas.cublasDcopy_v2.restype = int
_libcublas.cublasDcopy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDcopy(handle, n, x, incx, y, incy):
    status = _libcublas.cublasDcopy_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)
                
cublasDcopy.__doc__ = \
                    _COPY_doc.substitute(precision='double-precision',
                                         real='real',
                                         data='np.random.rand(5).astype(np.float64)',
                                         func='cublasDcopy')

_libcublas.cublasCcopy_v2.restype = int
_libcublas.cublasCcopy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCcopy(handle, n, x, incx, y, incy):
    status = _libcublas.cublasCcopy_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)
                
cublasCcopy.__doc__ = \
                    _COPY_doc.substitute(precision='single-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+np.random.rand(5)).astype(np.complex64)',
                                         func='cublasCcopy')

_libcublas.cublasZcopy_v2.restype = int
_libcublas.cublasZcopy_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZcopy(handle, n, x, incx, y, incy):
    status = _libcublas.cublasZcopy_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)
                
cublasZcopy.__doc__ = \
                    _COPY_doc.substitute(precision='double-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+np.random.rand(5)).astype(np.complex128)',
                                         func='cublasZcopy')

# SDOT, DDOT, CDOTU, CDOTC, ZDOTU, ZDOTC
_DOT_doc = Template(
"""
    Vector dot product (${precision} ${real})

    Computes the dot product of two ${precision} ${real} vectors.
    cublasCdotc and cublasZdotc use the conjugate of the first vector
    when computing the dot product.
    
    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input vector.
    incx : int
        Storage spacing between elements of `x`.
    y : ctypes.c_void_p
        Pointer to ${precision} ${real} input/output vector.
    incy : int
        Storage spacing between elements of `y`.

    Returns
    -------
    d : ${ret_type}
        Dot product of `x` and `y`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data}
    >>> y = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = gpuarray.to_gpu(y)
    >>> h = cublasCreate()
    >>> d = ${func}(h, x_gpu.size, x_gpu.gpudata, 1, y_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> ${check} 
    True

    Notes
    -----
    Both `x` and `y` must contain `n` elements.
    
""")

_libcublas.cublasSdot_v2.restype = int
_libcublas.cublasSdot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p]
def cublasSdot(handle, n, x, incx, y, incy):
    result = ctypes.c_float()
    status = _libcublas.cublasSdot_v2(handle, n,
                                      int(x), incx, int(y), incy,
                                      ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float32(result.value)

cublasSdot.__doc__ = _DOT_doc.substitute(precision='single-precision',
                                         real='real',
                                         data='np.float32(np.random.rand(5))',
                                         ret_type='np.float32',
                                         func='cublasSdot',
                                         check='np.allclose(d, np.dot(x, y))')

_libcublas.cublasDdot_v2.restype = int
_libcublas.cublasDdot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p]
def cublasDdot(handle, n, x, incx, y, incy):
    result = ctypes.c_double()
    status = _libcublas.cublasDdot_v2(handle, n,
                                      int(x), incx, int(y), incy,
                                      ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float64(result.value)

cublasDdot.__doc__ = _DOT_doc.substitute(precision='double-precision',
                                         real='real',
                                         data='np.float64(np.random.rand(5))',
                                         ret_type='np.float64',
                                         func='cublasDdot',
                                         check='np.allclose(d, np.dot(x, y))')

_libcublas.cublasCdotu_v2.restype = int
_libcublas.cublasCdotu_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasCdotu(handle, n, x, incx, y, incy):
    result = cuda.cuFloatComplex()
    status = _libcublas.cublasCdotu_v2(handle, n,
                                       int(x), incx, int(y), incy,
                                       ctypes.byref(result))
    cublasCheckStatus(status)
    return np.complex64(result.value)

cublasCdotu.__doc__ = _DOT_doc.substitute(precision='single-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                         ret_type='np.complex64',
                                         func='cublasCdotu',
                                         check='np.allclose(d, np.dot(x, y))')

_libcublas.cublasCdotc_v2.restype = int
_libcublas.cublasCdotc_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasCdotc(handle, n, x, incx, y, incy):
    result = cuda.cuFloatComplex()
    status = _libcublas.cublasCdotc_v2(handle, n,
                                       int(x), incx, int(y), incy,
                                       ctypes.byref(result))
    cublasCheckStatus(status)
    return np.complex64(result.value)

cublasCdotc.__doc__ = _DOT_doc.substitute(precision='single-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                         ret_type='np.complex64',
                                         func='cublasCdotc',
                                         check='np.allclose(d, np.dot(np.conj(x), y))')

_libcublas.cublasZdotu_v2.restype = int
_libcublas.cublasZdotu_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasZdotu(handle, n, x, incx, y, incy):
    result = cuda.cuDoubleComplex()
    status = _libcublas.cublasZdotu_v2(handle, n,
                                       int(x), incx, int(y), incy,
                                       ctypes.byref(result))
    cublasCheckStatus(status)
    return np.complex128(result.value)

cublasZdotu.__doc__ = _DOT_doc.substitute(precision='double-precision',
                                          real='complex',
                                          data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                          ret_type='np.complex128',
                                          func='cublasZdotu',
                                          check='np.allclose(d, np.dot(x, y))')

_libcublas.cublasZdotc_v2.restype = int
_libcublas.cublasZdotc_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasZdotc(handle, n, x, incx, y, incy):
    result = cuda.cuDoubleComplex()
    status = _libcublas.cublasZdotc_v2(handle, n,
                                       int(x), incx, int(y), incy,
                                       ctypes.byref(result))
    cublasCheckStatus(status)
    return np.complex128(result.value)

cublasZdotc.__doc__ = _DOT_doc.substitute(precision='double-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                         ret_type='np.complex128',
                                         func='cublasZdotc',
                                         check='np.allclose(d, np.dot(np.conj(x), y))')

# SNRM2, DNRM2, SCNRM2, DZNRM2
_NRM2_doc = Template(
"""
    Euclidean norm (2-norm) of real vector.

    Computes the Euclidean norm of a ${precision} ${real} vector.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input vector.
    incx : int
        Storage spacing between elements of `x`.

    Returns
    -------
    nrm : ${ret_type}
        Euclidean norm of `x`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> h = cublasCreate()
    >>> nrm = ${func}(h, x.size, x_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(nrm, np.linalg.norm(x))
    True
    
""")

_libcublas.cublasSnrm2_v2.restype = int
_libcublas.cublasSnrm2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasSnrm2(handle, n, x, incx):
    result = ctypes.c_float()
    status = _libcublas.cublasSnrm2_v2(handle,
                                       n, int(x), incx,
                                       ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float32(result.value)
    
cublasSnrm2.__doc__ = \
                    _NRM2_doc.substitute(precision='single-precision',
                                         real='real',
                                         data='np.float32(np.random.rand(5))',
                                         ret_type = 'numpy.float32',
                                         func='cublasSnrm2')

_libcublas.cublasDnrm2_v2.restype = int
_libcublas.cublasDnrm2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasDnrm2(handle, n, x, incx):
    result = ctypes.c_double()
    status = _libcublas.cublasDnrm2_v2(handle,
                                       n, int(x), incx,
                                       ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float64(result.value)
    
cublasDnrm2.__doc__ = \
                    _NRM2_doc.substitute(precision='double-precision',
                                         real='real',
                                         data='np.float64(np.random.rand(5))',
                                         ret_type = 'numpy.float64',
                                         func='cublasDnrm2')

_libcublas.cublasScnrm2_v2.restype = int
_libcublas.cublasScnrm2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasScnrm2(handle, n, x, incx):
    result = ctypes.c_float()
    status = _libcublas.cublasScnrm2_v2(handle,
                                        n, int(x), incx,
                                        ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float32(result.value)
    
cublasScnrm2.__doc__ = \
                    _NRM2_doc.substitute(precision='single-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                         ret_type = 'numpy.complex64',
                                         func='cublasScnrm2')

_libcublas.cublasDznrm2_v2.restype = int
_libcublas.cublasDznrm2_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def cublasDznrm2(handle, n, x, incx):
    result = ctypes.c_double()
    status = _libcublas.cublasDznrm2_v2(handle,
                                        n, int(x), incx,
                                        ctypes.byref(result))
    cublasCheckStatus(status)
    return np.float64(result.value)
    
cublasDznrm2.__doc__ = \
                    _NRM2_doc.substitute(precision='double-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                         ret_type = 'numpy.complex128',
                                         func='cublasDznrm2')


# SROT, DROT, CROT, CSROT, ZROT, ZDROT
_ROT_doc = Template(
"""
    Apply a ${real} rotation to ${real} vectors (${precision})

    Multiplies the ${precision} matrix `[[c, s], [-s.conj(), c]]`
    with the 2 x `n` ${precision} matrix `[[x.T], [y.T]]`.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input/output vector.
    incx : int
        Storage spacing between elements of `x`.
    y : ctypes.c_void_p
        Pointer to ${precision} ${real} input/output vector.
    incy : int
        Storage spacing between elements of `y`.
    c : ${c_type}
        Element of rotation matrix.
    s : ${s_type}
        Element of rotation matrix.

    Notes
    -----
    Both `x` and `y` must contain `n` elements.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> s = ${s_val}; c = ${c_val};
    >>> x = ${data}
    >>> y = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = gpuarray.to_gpu(y)
    >>> h = cublasCreate()
    >>> ${func}(h, x.size, x_gpu.gpudata, 1, y_gpu.gpudata, 1, c, s)
    >>> cublasDestroy(h)
    >>> np.allclose(x_gpu.get(), c*x+s*y)
    True
    >>> np.allclose(y_gpu.get(), -s.conj()*x+c*y)
    True
    
""")

_libcublas.cublasSrot_v2.restype = int
_libcublas.cublasSrot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p]
def cublasSrot(handle, n, x, incx, y, incy, c, s):
    status = _libcublas.cublasSrot_v2(handle,
                                      n, int(x), incx,
                                      int(y), incy,
                                      ctypes.byref(ctypes.c_float(c)),
                                      ctypes.byref(ctypes.c_float(s)))

    cublasCheckStatus(status)
        
cublasSrot.__doc__ = _ROT_doc.substitute(precision='single-precision',
                                         real='real',
                                         c_type='numpy.float32',
                                         s_type='numpy.float32',
                                         c_val='np.float32(np.random.rand())',
                                         s_val='np.float32(np.random.rand())',
                                         data='np.random.rand(5).astype(np.float32)',
                                         func='cublasSrot')

_libcublas.cublasDrot_v2.restype = int
_libcublas.cublasDrot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p]
def cublasDrot(handle, n, x, incx, y, incy, c, s):
    status = _libcublas.cublasDrot_v2(handle,
                                      n, int(x),
                                      incx, int(y), incy,
                                      ctypes.byref(ctypes.c_double(c)),
                                      ctypes.byref(ctypes.c_double(s)))
    cublasCheckStatus(status)
        
cublasDrot.__doc__ = _ROT_doc.substitute(precision='double-precision',
                                         real='real',
                                         c_type='numpy.float64',
                                         s_type='numpy.float64',
                                         c_val='np.float64(np.random.rand())',
                                         s_val='np.float64(np.random.rand())',
                                         data='np.random.rand(5).astype(np.float64)',
                                         func='cublasDrot')

_libcublas.cublasCrot_v2.restype = int
_libcublas.cublasCrot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p]
def cublasCrot(handle, n, x, incx, y, incy, c, s):
    status = _libcublas.cublasCrot_v2(handle,
                                      n, int(x),
                                      incx, int(y), incy,
                                      ctypes.byref(ctypes.c_float(c)),
                                      ctypes.byref(cuda.cuFloatComplex(s.real,
                                                                       s.imag)))
    cublasCheckStatus(status)
        
cublasCrot.__doc__ = _ROT_doc.substitute(precision='single-precision',
                                         real='complex',
                                         c_type='numpy.float32',
                                         s_type='numpy.complex64',
                                         c_val='np.float32(np.random.rand())',
                                         s_val='np.complex64(np.random.rand()+1j*np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                         func='cublasCrot')

_libcublas.cublasCsrot_v2.restype = int
_libcublas.cublasCsrot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p]
def cublasCsrot(handle, n, x, incx, y, incy, c, s):
    status = _libcublas.cublasCsrot_v2(handle,
                                       n, int(x),
                                       incx, int(y), incy,
                                       ctypes.byref(ctypes.c_float(c)), 
                                       ctypes.byref(ctypes.c_float(s)))
    cublasCheckStatus(status)
        
cublasCsrot.__doc__ = _ROT_doc.substitute(precision='single-precision',
                                          real='complex',
                                          c_type='numpy.float32',
                                          s_type='numpy.float32',
                                          c_val='np.float32(np.random.rand())',
                                          s_val='np.float32(np.random.rand())',
                                          data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                          func='cublasCsrot')

_libcublas.cublasZrot_v2.restype = int
_libcublas.cublasZrot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p]
def cublasZrot(handle, n, x, incx, y, incy, c, s):
    status = _libcublas.cublasZrot_v2(handle,
                                      n, int(x),
                                      incx, int(y), incy,
                                      ctypes.byref(ctypes.c_double(c)),
                                      ctypes.byref(cuda.cuDoubleComplex(s.real,
                                                                        s.imag)))
    cublasCheckStatus(status)
        
cublasZrot.__doc__ = _ROT_doc.substitute(precision='double-precision',
                                         real='complex',
                                         c_type='numpy.float64',
                                         s_type='numpy.complex128',
                                         c_val='np.float64(np.random.rand())',
                                         s_val='np.complex128(np.random.rand()+1j*np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                         func='cublasZrot')

_libcublas.cublasZdrot_v2.restype = int
_libcublas.cublasZdrot_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p]
def cublasZdrot(handle, n, x, incx, y, incy, c, s):
    status = _libcublas.cublasZdrot_v2(handle,
                                       n, int(x),
                                       incx, int(y), incy,
                                       ctypes.byref(ctypes.c_double(c)),
                                       ctypes.byref(ctypes.c_double(s)))
    cublasCheckStatus(status)
        
cublasZdrot.__doc__ = _ROT_doc.substitute(precision='double-precision',
                                          real='complex',
                                          c_type='numpy.float64',
                                          s_type='numpy.float64',
                                          c_val='np.float64(np.random.rand())',
                                          s_val='np.float64(np.random.rand())',
                                          data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                          func='cublasZdrot')


# SROTG, DROTG, CROTG, ZROTG
_ROTG_doc = Template(
"""
    Construct a ${precision} ${real} Givens rotation matrix.

    Constructs the ${precision} ${real} Givens rotation matrix
    `G = [[c, s], [-s.conj(), c]]` such that
    `dot(G, [[a], [b]] == [[r], [0]]`, where
    `c**2+s**2 == 1` and `r == a**2+b**2` for real numbers and
    `c**2+(conj(s)*s) == 1` and `r ==
    (a/abs(a))*sqrt(abs(a)**2+abs(b)**2)` for `a != 0` and `r == b`
    for `a == 0`.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    a, b : ${type}
        Entries of vector whose second entry should be zeroed
        out by the rotation.

    Returns
    -------
    r : ${type}
        Defined above.
    c : ${c_type}
        Cosine component of rotation matrix.
    s : ${s_type}
        Sine component of rotation matrix.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> a = ${a_val}
    >>> b = ${b_val}
    >>> h = cublasCreate()
    >>> r, c, s = ${func}(h, a, b)
    >>> cublasDestroy(h)
    >>> np.allclose(np.dot(np.array([[c, s], [-np.conj(s), c]]), np.array([[a], [b]])), np.array([[r], [0.0]]), atol=1e-6)
    True

""")

_libcublas.cublasSrotg_v2.restype = int
_libcublas.cublasSrotg_v2.argtypes = [_types.handle,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p]
def cublasSrotg(handle, a, b):
    _a = ctypes.c_float(a)
    _b = ctypes.c_float(b)
    _c = ctypes.c_float()
    _s = ctypes.c_float()
    status = _libcublas.cublasSrotg_v2(handle,
                                       ctypes.byref(_a), ctypes.byref(_b),
                                       ctypes.byref(_c), ctypes.byref(_s))
    cublasCheckStatus(status)
    return np.float32(_a.value), np.float32(_c.value), np.float32(_s.value)
                                  
cublasSrotg.__doc__ = \
                    _ROTG_doc.substitute(precision='single-precision',
                                         real='real',
                                         type='numpy.float32',
                                         c_type='numpy.float32',
                                         s_type='numpy.float32',
                                         a_val='np.float32(np.random.rand())',
                                         b_val='np.float32(np.random.rand())',
                                         func='cublasSrotg')

_libcublas.cublasDrotg_v2.restype = int
_libcublas.cublasDrotg_v2.argtypes = [_types.handle,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p]
def cublasDrotg(handle, a, b):
    _a = ctypes.c_double(a)
    _b = ctypes.c_double(b)
    _c = ctypes.c_double()
    _s = ctypes.c_double()
    status = _libcublas.cublasDrotg_v2(handle,
                                       ctypes.byref(_a), ctypes.byref(_b),
                                       ctypes.byref(_c), ctypes.byref(_s))
    cublasCheckStatus(status)
    return np.float64(_a.value), np.float64(_c.value), np.float64(_s.value)
                                  
cublasDrotg.__doc__ = \
                    _ROTG_doc.substitute(precision='double-precision',
                                         real='real',
                                         type='numpy.float64',
                                         c_type='numpy.float64',
                                         s_type='numpy.float64',
                                         a_val='np.float64(np.random.rand())',
                                         b_val='np.float64(np.random.rand())',
                                         func='cublasDrotg')

_libcublas.cublasCrotg_v2.restype = int
_libcublas.cublasCrotg_v2.argtypes = [_types.handle,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p]
def cublasCrotg(handle, a, b):
    _a = cuda.cuFloatComplex(a.real, a.imag)
    _b = cuda.cuFloatComplex(b.real, b.imag)
    _c = ctypes.c_float()
    _s = cuda.cuFloatComplex()
    status = _libcublas.cublasCrotg_v2(handle,
                                       ctypes.byref(_a), ctypes.byref(_b),
                                       ctypes.byref(_c), ctypes.byref(_s))
    cublasCheckStatus(status)
    return np.complex64(_a.value), np.float32(_c.value), np.complex64(_s.value)
                                  
cublasCrotg.__doc__ = \
                    _ROTG_doc.substitute(precision='single-precision',
                                         real='complex',
                                         type='numpy.complex64',
                                         c_type='numpy.float32',
                                         s_type='numpy.complex64',
                                         a_val='np.complex64(np.random.rand()+1j*np.random.rand())',
                                         b_val='np.complex64(np.random.rand()+1j*np.random.rand())',
                                         func='cublasCrotg')

_libcublas.cublasZrotg_v2.restype = int
_libcublas.cublasZrotg_v2.argtypes = [_types.handle,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p]
def cublasZrotg(handle, a, b):
    _a = cuda.cuDoubleComplex(a.real, a.imag)
    _b = cuda.cuDoubleComplex(b.real, b.imag)
    _c = ctypes.c_double()
    _s = cuda.cuDoubleComplex()
    status = _libcublas.cublasZrotg_v2(handle,
                                       ctypes.byref(_a), ctypes.byref(_b),
                                       ctypes.byref(_c), ctypes.byref(_s))
    cublasCheckStatus(status)
    return np.complex128(_a.value), np.float64(_c.value), np.complex128(_s.value)
                                  
cublasZrotg.__doc__ = \
                    _ROTG_doc.substitute(precision='double-precision',
                                         real='complex',
                                         type='numpy.complex128',
                                         c_type='numpy.float64',
                                         s_type='numpy.complex128',
                                         a_val='np.complex128(np.random.rand()+1j*np.random.rand())',
                                         b_val='np.complex128(np.random.rand()+1j*np.random.rand())',
                                         func='cublasZrotg')

# SROTM, DROTM (need to add example)
_ROTM_doc = Template(        
"""
    Apply a ${precision} real modified Givens rotation.

    Applies the ${precision} real modified Givens rotation matrix `h`
    to the 2 x `n` matrix `[[x.T], [y.T]]`.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    x : ctypes.c_void_p
        Pointer to ${precision} real input/output vector.
    incx : int
        Storage spacing between elements of `x`.
    y : ctypes.c_void_p
        Pointer to ${precision} real input/output vector.
    incy : int
        Storage spacing between elements of `y`.
    sparam : numpy.ndarray
        sparam[0] contains the `flag` described below;
        sparam[1:5] contains the values `[h00, h10, h01, h11]`
        that determine the rotation matrix `h`.

    Notes
    -----
    The rotation matrix may assume the following values:

    for `flag` == -1.0, `h` == `[[h00, h01], [h10, h11]]`
    for `flag` == 0.0,  `h` == `[[1.0, h01], [h10, 1.0]]`
    for `flag` == 1.0,  `h` == `[[h00, 1.0], [-1.0, h11]]`
    for `flag` == -2.0, `h` == `[[1.0, 0.0], [0.0, 1.0]]`

    Both `x` and `y` must contain `n` elements.
    
""")

_libcublas.cublasSrotm_v2.restype = int
_libcublas.cublasSrotm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasSrotm(handle, n, x, incx, y, incy, sparam):
    status = _libcublas.cublasSrotm_v2(handle,
                                       n, int(x), incx, int(y),
                                       incy, int(sparam.ctypes.data))
    cublasCheckStatus(status)

cublasSrotm.__doc__ = \
                    _ROTM_doc.substitute(precision='single-precision')

_libcublas.cublasDrotm_v2.restype = int
_libcublas.cublasDrotm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasDrotm(handle, n, x, incx, y, incy, sparam):
    status = _libcublas.cublasDrotm_v2(handle,
                                       n, int(x), incx, int(y),
                                       incy, int(sparam.ctypes.data))
    cublasCheckStatus(status)

cublasDrotm.__doc__ = \
                    _ROTM_doc.substitute(precision='double-precision')
                                        
# SROTMG, DROTMG (need to add example)
_ROTMG_doc = Template( 
"""
    Construct a ${precision} real modified Givens rotation matrix.

    Constructs the ${precision} real modified Givens rotation matrix
    `h = [[h11, h12], [h21, h22]]` that zeros out the second entry of
    the vector `[[sqrt(d1)*x1], [sqrt(d2)*x2]]`.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    d1 : ${type}
        ${precision} real value.
    d2 : ${type}
        ${precision} real value.
    x1 : ${type}
        ${precision} real value.
    x2 : ${type}
        ${precision} real value.

    Returns
    -------
    sparam : numpy.ndarray
        sparam[0] contains the `flag` described below;
        sparam[1:5] contains the values `[h00, h10, h01, h11]`
        that determine the rotation matrix `h`.
        
    Notes
    -----
    The rotation matrix may assume the following values:

    for `flag` == -1.0, `h` == `[[h00, h01], [h10, h11]]`
    for `flag` == 0.0,  `h` == `[[1.0, h01], [h10, 1.0]]`
    for `flag` == 1.0,  `h` == `[[h00, 1.0], [-1.0, h11]]`
    for `flag` == -2.0, `h` == `[[1.0, 0.0], [0.0, 1.0]]`

""")

_libcublas.cublasSrotmg_v2.restype = int
_libcublas.cublasSrotmg_v2.argtypes = [_types.handle,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p]
def cublasSrotmg(handle, d1, d2, x1, y1):
    _d1 = ctypes.c_float(d1)
    _d2 = ctypes.c_float(d2)
    _x1 = ctypes.c_float(x1)
    _y1 = ctypes.c_float(y1)
    sparam = np.empty(5, np.float32)

    status = _libcublas.cublasSrotmg_v2(handle,
                                        ctypes.byref(_d1), ctypes.byref(_d2),
                                        ctypes.byref(_x1), ctypes.byref(_y1),
                                        int(sparam.ctypes.data))
    cublasCheckStatus(status)        
    return sparam

cublasSrotmg.__doc__ = \
                     _ROTMG_doc.substitute(precision='single-precision',
                                           type='numpy.float32')

_libcublas.cublasDrotmg_v2.restype = int
_libcublas.cublasDrotmg_v2.argtypes = [_types.handle,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p]
def cublasDrotmg(handle, d1, d2, x1, y1):
    _d1 = ctypes.c_double(d1)
    _d2 = ctypes.c_double(d2)
    _x1 = ctypes.c_double(x1)
    _y1 = ctypes.c_double(y1)
    sparam = np.empty(5, np.float64)

    status = _libcublas.cublasDrotmg_v2(handle,
                                        ctypes.byref(_d1), ctypes.byref(_d2),
                                        ctypes.byref(_x1), ctypes.byref(_y1),
                                        int(sparam.ctypes.data))
    cublasCheckStatus(status)        
    return sparam

cublasDrotmg.__doc__ = \
                     _ROTMG_doc.substitute(precision='double-precision',
                                           type='numpy.float64')

# SSCAL, DSCAL, CSCAL, CSCAL, CSSCAL, ZSCAL, ZDSCAL
_SCAL_doc = Template(
"""
    Scale a ${precision} ${real} vector by a ${precision} ${a_real} scalar.

    Replaces a ${precision} ${real} vector `x` with
    `alpha * x`.
    
    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    alpha : ${a_type}
        Scalar multiplier.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input/output vector.
    incx : int
        Storage spacing between elements of `x`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> alpha = ${alpha}
    >>> h = cublasCreate()
    >>> ${func}(h, x.size, alpha, x_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(x_gpu.get(), alpha*x)
    True    
""")

_libcublas.cublasSscal_v2.restype = int
_libcublas.cublasSscal_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSscal(handle, n, alpha, x, incx):
    status = _libcublas.cublasSscal_v2(handle, n,
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(x), incx)
    cublasCheckStatus(status)
        
cublasSscal.__doc__ = \
                    _SCAL_doc.substitute(precision='single-precision',
                                         real='real',
                                         a_real='real',
                                         a_type='numpy.float32',
                                         alpha='np.float32(np.random.rand())',
                                         data='np.random.rand(5).astype(np.float32)',
                                         func='cublasSscal')

_libcublas.cublasDscal_v2.restype = int
_libcublas.cublasDscal_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDscal(handle, n, alpha, x, incx):
    status = _libcublas.cublasDscal_v2(handle, n,
                                       ctypes.byref(ctypes.c_double(alpha)),
                                       int(x), incx)
    cublasCheckStatus(status)
        
cublasDscal.__doc__ = \
                    _SCAL_doc.substitute(precision='double-precision',
                                         real='real',
                                         a_real='real',
                                         a_type='numpy.float64',
                                         alpha='np.float64(np.random.rand())',
                                         data='np.random.rand(5).astype(np.float64)',
                                         func='cublasDscal')

_libcublas.cublasCscal_v2.restype = int
_libcublas.cublasCscal_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCscal(handle, n, alpha, x, incx):
    status = _libcublas.cublasCscal_v2(handle, n,
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)),
                                       int(x), incx)
    cublasCheckStatus(status)
        
cublasCscal.__doc__ = \
                    _SCAL_doc.substitute(precision='single-precision',
                                         real='complex',
                                         a_real='complex',
                                         a_type='numpy.complex64',
                                         alpha='np.complex64(np.random.rand()+1j*np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                         func='cublasCscal')

_libcublas.cublasCsscal_v2.restype = int
_libcublas.cublasCsscal_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCsscal(handle, n, alpha, x, incx):
    status = _libcublas.cublasCsscal_v2(handle, n,
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(x), incx)
    cublasCheckStatus(status)
        
cublasCsscal.__doc__ = \
                    _SCAL_doc.substitute(precision='single-precision',
                                         real='complex',
                                         a_real='real',
                                         a_type='numpy.float32',
                                         alpha='np.float32(np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                         func='cublasCsscal')

_libcublas.cublasZscal_v2.restype = int
_libcublas.cublasZscal_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZscal(handle, n, alpha, x, incx):
    status = _libcublas.cublasZscal_v2(handle, n,
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)),
                                       int(x), incx)
    cublasCheckStatus(status)
        
cublasZscal.__doc__ = \
                    _SCAL_doc.substitute(precision='double-precision',
                                         real='complex',
                                         a_real='complex',
                                         a_type='numpy.complex128',
                                         alpha='np.complex128(np.random.rand()+1j*np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                         func='cublasZscal')

_libcublas.cublasZdscal_v2.restype = int
_libcublas.cublasZdscal_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZdscal(handle, n, alpha, x, incx):
    status = _libcublas.cublasZdscal_v2(handle, n,
                                       ctypes.byref(ctypes.c_double(alpha)),
                                       int(x), incx)
    cublasCheckStatus(status)
        
cublasZdscal.__doc__ = \
                    _SCAL_doc.substitute(precision='double-precision',
                                         real='complex',
                                         a_real='real',
                                         a_type='numpy.float64',
                                         alpha='np.float64(np.random.rand())',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                         func='cublasZdscal')

# SSWAP, DSWAP, CSWAP, ZSWAP
_SWAP_doc = Template(
"""
    Swap ${precision} ${real} vectors.

    Swaps the contents of one ${precision} ${real} vector with those
    of another ${precision} ${real} vector.

    Parameters
    ----------
    handle : int
        CUBLAS context.
    n : int
        Number of elements in input vectors.
    x : ctypes.c_void_p
        Pointer to ${precision} ${real} input/output vector.
    incx : int
        Storage spacing between elements of `x`.
    y : ctypes.c_void_p
        Pointer to ${precision} ${real} input/output vector.
    incy : int
        Storage spacing between elements of `y`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> x = ${data}
    >>> y = ${data}
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = gpuarray.to_gpu(y)
    >>> h = cublasCreate() 
    >>> ${func}(h, x.size, x_gpu.gpudata, 1, y_gpu.gpudata, 1)
    >>> cublasDestroy(h)
    >>> np.allclose(x_gpu.get(), y)
    True
    >>> np.allclose(y_gpu.get(), x)
    True

    Notes
    -----
    Both `x` and `y` must contain `n` elements.

""")

_libcublas.cublasSswap_v2.restype = int
_libcublas.cublasSswap_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSswap(handle, n, x, incx, y, incy):
    status = _libcublas.cublasSswap_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasSswap.__doc__ = \
                    _SWAP_doc.substitute(precision='single-precision',
                                         real='real',
                                         data='np.random.rand(5).astype(np.float32)',
                                         func='cublasSswap')

_libcublas.cublasDswap_v2.restype = int
_libcublas.cublasDswap_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]    
def cublasDswap(handle, n, x, incx, y, incy):
    status = _libcublas.cublasDswap_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasDswap.__doc__ = \
                    _SWAP_doc.substitute(precision='double-precision',
                                         real='real',
                                         data='np.random.rand(5).astype(np.float64)',
                                         func='cublasDswap')

_libcublas.cublasCswap_v2.restype = int
_libcublas.cublasCswap_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCswap(handle, n, x, incx, y, incy):
    status = _libcublas.cublasCswap_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasCswap.__doc__ = \
                    _SWAP_doc.substitute(precision='single-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)',
                                         func='cublasCswap')

_libcublas.cublasZswap_v2.restype = int
_libcublas.cublasZswap_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZswap(handle, n, x, incx, y, incy):
    status = _libcublas.cublasZswap_v2(handle,
                                       n, int(x), incx, int(y), incy)
    cublasCheckStatus(status)

cublasZswap.__doc__ = \
                    _SWAP_doc.substitute(precision='double-precision',
                                         real='complex',
                                         data='(np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)',
                                         func='cublasZswap')

### BLAS Level 2 Functions ###

# SGBMV, DGVMV, CGBMV, ZGBMV 
_libcublas.cublasSgbmv_v2.restype = int
_libcublas.cublasSgbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_char,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSgbmv(handle, trans, m, n, kl, ku, alpha, A, lda,
                x, incx, beta, y, incy):
    """
    Matrix-vector product for real general banded matrix.

    """

    status = _libcublas.cublasSgbmv_v2(handle,
                                       trans, m, n, kl, ku,
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda,
                                       int(x), incx,
                                       ctypes.byref(ctypes.c_float(beta)),
                                       int(y), incy)
    cublasCheckStatus(status)

_libcublas.cublasDgbmv_v2.restype = int
_libcublas.cublasDgbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_char,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDgbmv(handle, trans, m, n, kl, ku, alpha, A, lda, 
                x, incx, beta, y, incy):
    """
    Matrix-vector product for real general banded matrix.

    """

    status = _libcublas.cublasDgbmv_v2(handle,
                                       trans, m, n, kl, ku,
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(ctypes.c_float(beta)),
                                       int(y), incy)
    cublasCheckStatus(status)

_libcublas.cublasCgbmv_v2.restype = int
_libcublas.cublasCgbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_char,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCgbmv(handle, trans, m, n, kl, ku, alpha, A, lda,
                x, incx, beta, y, incy):
    """
    Matrix-vector product for complex general banded matrix.

    """

    status = _libcublas.cublasCgbmv_v2(handle,
                                       trans, m, n, kl, ku,
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

_libcublas.cublasZgbmv_v2.restype = int
_libcublas.cublasZgbmv_v2.argtypes = [ctypes.c_char,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZgbmv(handle, trans, m, n, kl, ku, alpha, A, lda, 
                x, incx, beta, y, incy):
    """
    Matrix-vector product for complex general banded matrix.

    """

    status = _libcublas.cublasZgbmv_v2(handle,
                                       trans, m, n, kl, ku,
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                         beta.imag)),
                              int(y), incy)
    cublasCheckStatus(status)
    
# SGEMV, DGEMV, CGEMV, ZGEMV # XXX need to adjust
# _GEMV_doc = Template( 
# """
#     Matrix-vector product for ${precision} ${real} general matrix.

#     Computes the product `alpha*op(A)*x+beta*y`, where `op(A)` == `A`
#     or `op(A)` == `A.T`, and stores it in `y`.

#     Parameters
#     ----------
#     trans : char
#         If `upper(trans)` in `['T', 'C']`, assume that `A` is
#         transposed.
#     m : int
#         Number of rows in `A`.
#     n : int
#         Number of columns in `A`.
#     alpha : ${a_type}
#         `A` is multiplied by this quantity. 
#     A : ctypes.c_void_p
#         Pointer to ${precision} matrix. The matrix has
#         shape `(lda, n)` if `upper(trans)` == 'N', `(lda, m)`
#         otherwise.
#     lda : int
#         Leading dimension of `A`.
#     X : ctypes.c_void_p
#         Pointer to ${precision} array of length at least
#         `(1+(n-1)*abs(incx))` if `upper(trans) == 'N',
#         `(1+(m+1)*abs(incx))` otherwise.
#     incx : int
#         Spacing between elements of `x`. Must be nonzero.
#     beta : ${a_type}
#         `y` is multiplied by this quantity. If zero, `y` is ignored.
#     y : ctypes.c_void_p
#         Pointer to ${precision} array of length at least
#         `(1+(m+1)*abs(incy))` if `upper(trans)` == `N`,
#         `(1+(n+1)*abs(incy))` otherwise.
#     incy : int
#         Spacing between elements of `y`. Must be nonzero.

#     Examples
#     --------
#     >>> import pycuda.autoinit
#     >>> import pycuda.gpuarray as gpuarray
#     >>> import numpy as np
#     >>> a = np.random.rand(2, 3).astype(np.float32)
#     >>> x = np.random.rand(3, 1).astype(np.float32)
#     >>> a_gpu = gpuarray.to_gpu(a.T.copy())
#     >>> x_gpu = gpuarray.to_gpu(x)
#     >>> y_gpu = gpuarray.empty((2, 1), np.float32)
#     >>> alpha = np.float32(1.0)
#     >>> beta = np.float32(0)
#     >>> h = cublasCreate()
#     >>> ${func}(h, 'n', 2, 3, alpha, a_gpu.gpudata, 2, x_gpu.gpudata, 1, beta, y_gpu.gpudata, 1)
#     >>> cublasDestroy(h)
#     >>> np.allclose(y_gpu.get(), np.dot(a, x))
#     True

# """
    
_libcublas.cublasSgemv_v2.restype = int
_libcublas.cublasSgemv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSgemv(handle, trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real general matrix.

    """

    status = _libcublas.cublasSgemv_v2(handle,
                                       _CUBLAS_OP[trans], m, n,
                                       ctypes.byref(ctypes.c_float(alpha)), int(A), lda,
                                       int(x), incx,
                                       ctypes.byref(ctypes.c_float(beta)), int(y), incy) 
    cublasCheckStatus(status)
        
_libcublas.cublasDgemv_v2.restype = int
_libcublas.cublasDgemv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDgemv(handle, trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real general matrix.

    """

    status = _libcublas.cublasDgemv_v2(handle,
                                       _CUBLAS_OP[trans], m, n,
                                       ctypes.byref(ctypes.c_double(alpha)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(ctypes.c_double(beta)),
                                       int(y), incy)
    cublasCheckStatus(status)
    
_libcublas.cublasCgemv_v2.restype = int
_libcublas.cublasCgemv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCgemv(handle, trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for complex general matrix.

    """

    status = _libcublas.cublasCgemv_v2(handle,
                                       _CUBLAS_OP[trans], m, n,
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)
    
_libcublas.cublasZgemv_v2.restype = int
_libcublas.cublasZgemv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,        
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZgemv(handle, trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for complex general matrix.

    """

    status = _libcublas.cublasZgemv_v2(handle,
                                       _CUBLAS_OP[trans], m, n,
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                         beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

# SGER, DGER, CGERU, CGERC, ZGERU, ZGERC
_libcublas.cublasSger_v2.restype = int
_libcublas.cublasSger_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def cublasSger(handle, m, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-1 operation on real general matrix.

    """
    
    status = _libcublas.cublasSger_v2(handle,
                                      m, n,
                                      ctypes.byref(ctypes.c_float(alpha)),
                                      int(x), incx,
                                      int(y), incy, int(A), lda)
    cublasCheckStatus(status)

_libcublas.cublasDger_v2.restype = int
_libcublas.cublasDger_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def cublasDger(handle, m, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-1 operation on real general matrix.

    """
    
    status = _libcublas.cublasDger_v2(handle,
                                      m, n,
                                      ctypes.byref(ctypes.c_double(alpha)),
                                      int(x), incx,
                                      int(y), incy, int(A), lda)
    cublasCheckStatus(status)
    
_libcublas.cublasCgerc_v2.restype = int
_libcublas.cublasCgerc_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCgerc(handle, m, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-1 operation on complex general matrix.

    """

    status = _libcublas.cublasCgerc_v2(handle,
                                       m, n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                            alpha.imag)),
                                       int(x), incx, int(y), incy, int(A), lda)
    cublasCheckStatus(status)
    
_libcublas.cublasCgeru_v2.restype = int
_libcublas.cublasCgeru_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCgeru(handle, m, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-1 operation on complex general matrix.

    """

    status = _libcublas.cublasCgeru_v2(handle,
                                       m, n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                              alpha.imag)),
                                       int(x), incx, int(y), incy, int(A), lda)
    cublasCheckStatus(status)
    
_libcublas.cublasZgerc_v2.restype = int
_libcublas.cublasZgerc_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZgerc(handle, m, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-1 operation on complex general matrix.

    """

    status = _libcublas.cublasZgerc_v2(handle,
                                       m, n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                               alpha.imag)),
                                       int(x), incx, int(y), incy, int(A), lda)
    cublasCheckStatus(status)

_libcublas.cublasZgeru_v2.restype = int
_libcublas.cublasZgeru_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZgeru(handle, m, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-1 operation on complex general matrix.

    """

    status = _libcublas.cublasZgeru_v2(handle,
                                       m, n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                               alpha.imag)),
                                       int(x), incx, int(y), incy, int(A), lda)
    cublasCheckStatus(status)

# SSBMV, DSBMV 
_libcublas.cublasSsbmv_v2.restype = int
_libcublas.cublasSsbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]

def cublasSsbmv(handle, uplo, n, k, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real symmetric-banded matrix.

    """

    status = _libcublas.cublasSsbmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], n, k,
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(ctypes.c_float(beta)),
                                       int(y), incy)
    cublasCheckStatus(status)
        
_libcublas.cublasDsbmv_v2.restype = int
_libcublas.cublasDsbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDsbmv(handle, uplo, n, k, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real symmetric-banded matrix.

    """

    status = _libcublas.cublasDsbmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], n, k,
                                       ctypes.byref(ctypes.c_double(alpha)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(ctypes.c_double(beta)),
                                       int(y), incy)
    cublasCheckStatus(status)
        
# SSPMV, DSPMV
_libcublas.cublasSspmv_v2.restype = int
_libcublas.cublasSspmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSspmv(handle, uplo, n, alpha, AP, x, incx, beta, y, incy):
    """
    Matrix-vector product for real symmetric-packed matrix.

    """

    status = _libcublas.cublasSspmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n,
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       ctypes.byref(ctypes.c_float(AP)),
                                       int(x),
                                       incx,
                                       ctypes.byref(ctypes.c_float(beta)),
                                       int(y),
                                       incy)
    cublasCheckStatus(status)
        
_libcublas.cublasDspmv_v2.restype = int
_libcublas.cublasDspmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDspmv(handle, uplo, n, alpha, AP, x, incx, beta, y, incy):
    """
    Matrix-vector product for real symmetric-packed matrix.

    """

    status = _libcublas.cublasDspmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n,
                                       ctypes.byref(ctypes.c_double(alpha)),
                                       ctypes.byref(ctypes.c_double(AP)),
                                       int(x),
                                       incx,
                                       ctypes.byref(ctypes.c_double(beta)),
                                       int(y),
                                       incy)
    cublasCheckStatus(status)

# SSPR, DSPR
_libcublas.cublasSspr_v2.restype = int
_libcublas.cublasSspr_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p]
def cublasSspr(handle, uplo, n, alpha, x, incx, AP):
    """
    Rank-1 operation on real symmetric-packed matrix.

    """
    
    status = _libcublas.cublasSspr_v2(handle, 
                                      _CUBLAS_FILL_MODE[uplo], n,                                       
                                      ctypes.byref(ctypes.c_float(alpha)), 
                                      int(x), incx, int(AP))                                      
    cublasCheckStatus(status)


_libcublas.cublasDspr_v2.restype = int
_libcublas.cublasDspr_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p]
def cublasDspr(handle, uplo, n, alpha, x, incx, AP):
    """
    Rank-1 operation on real symmetric-packed matrix.

    """

    status = _libcublas.cublasDspr_v2(handle, 
                                      _CUBLAS_FILL_MODE[uplo], n,                                       
                                      ctypes.byref(ctypes.c_double(alpha)), 
                                      int(x), incx, int(AP))                                           
    cublasCheckStatus(status)

# SSPR2, DSPR2
_libcublas.cublasSspr2_v2.restype = int
_libcublas.cublasSspr2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasSspr2(handle, uplo, n, alpha, x, incx, y, incy, AP):
    """
    Rank-2 operation on real symmetric-packed matrix.

    """

    status = _libcublas.cublasSspr2_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(x), incx, int(y), incy, int(AP))    
                                                                              
    cublasCheckStatus(status)

_libcublas.cublasDspr2_v2.restype = int
_libcublas.cublasDspr2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasDspr2(handle, uplo, n, alpha, x, incx, y, incy, AP):
    """
    Rank-2 operation on real symmetric-packed matrix.

    """

    status = _libcublas.cublasDspr2_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(ctypes.c_double(alpha)), 
                                       int(x), incx, int(y), incy, int(AP))
    cublasCheckStatus(status)

# SSYMV, DSYMV, CSYMV, ZSYMV
_libcublas.cublasSsymv_v2.restype = int
_libcublas.cublasSsymv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSsymv(handle, uplo, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real symmetric matrix.
    
    """
    
    status = _libcublas.cublasSsymv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(ctypes.c_float(beta)), 
                                       int(y), incy)
    cublasCheckStatus(status)

_libcublas.cublasDsymv_v2.restype = int
_libcublas.cublasDsymv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDsymv(handle, uplo, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real symmetric matrix.
    
    """

    status = _libcublas.cublasDsymv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(ctypes.c_double(alpha)), 
                                       int(A), lda, int(x), incx, 
                                       ctypes.byref(ctypes.c_double(beta)), 
                                       int(y), incy)
    cublasCheckStatus(status)

if _cublas_version >= 5000:
    _libcublas.cublasCsymv_v2.restype = int
    _libcublas.cublasCsymv_v2.argtypes = [_types.handle,
                                          ctypes.c_int,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_int]
    
@_cublas_version_req(5.0)    
def cublasCsymv(handle, uplo, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for complex symmetric matrix.

    """

    status = _libcublas.cublasCsymv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                       alpha.imag)), 
                                       int(A), lda, int(x), incx, 
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)), 
                                       int(y), incy)
    cublasCheckStatus(status)

if _cublas_version >= 5000:    
    _libcublas.cublasZsymv_v2.restype = int
    _libcublas.cublasZsymv_v2.argtypes = [_types.handle,
                                          ctypes.c_int,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_int]

@_cublas_version_req(5.0)
def cublasZsymv(handle, uplo, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for complex symmetric matrix.

    """

    status = _libcublas.cublasZsymv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)), 
                                       int(A), lda, int(x), incx, 
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                         beta.imag)), 
                                       int(y), incy)
    cublasCheckStatus(status)
    
# SSYR, DSYR, CSYR, ZSYR
_libcublas.cublasSsyr_v2.restype = int
_libcublas.cublasSsyr_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def cublasSsyr(handle, uplo, n, alpha, x, incx, A, lda): 
    """
    Rank-1 operation on real symmetric matrix.

    """
   
    status = _libcublas.cublasSsyr_v2(handle,
                                      _CUBLAS_FILL_MODE[uplo], n, 
                                      ctypes.byref(ctypes.c_float(alpha)),
                                      int(x), incx, int(A), lda)
    cublasCheckStatus(status)

_libcublas.cublasDsyr_v2.restype = int
_libcublas.cublasDsyr_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def cublasDsyr(handle, uplo, n, alpha, x, incx, A, lda):
    """
    Rank-1 operation on real symmetric matrix.

    """

    status = _libcublas.cublasDsyr_v2(handle,
                                      _CUBLAS_FILL_MODE[uplo], n, 
                                      ctypes.byref(ctypes.c_double(alpha)), 
                                      int(x), incx, int(A), lda)
    cublasCheckStatus(status)

if _cublas_version >= 5000:
    _libcublas.cublasCsyr_v2.restype = int
    _libcublas.cublasCsyr_v2.argtypes = [_types.handle,
                                         ctypes.c_int,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_void_p,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_int]

@_cublas_version_req(5.0)                                         
def cublasCsyr(handle, uplo, n, alpha, x, incx, A, lda):
    """
    Rank-1 operation on complex symmetric matrix.

    """

    status = _libcublas.cublasCsyr_v2(handle,
                                      _CUBLAS_FILL_MODE[uplo], n, 
                                      ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                       alpha.imag)),
                                      int(x), incx, int(A), lda)
    cublasCheckStatus(status)

if _cublas_version >= 5000:
    _libcublas.cublasZsyr_v2.restype = int
    _libcublas.cublasZsyr_v2.argtypes = [_types.handle,
                                         ctypes.c_int,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_void_p,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_int]

@_cublas_version_req(5.0)                                         
def cublasZsyr(handle, uplo, n, alpha, x, incx, A, lda):
    """
    Rank-1 operation on complex symmetric matrix.

    """

    status = _libcublas.cublasZsyr_v2(handle,
                                      _CUBLAS_FILL_MODE[uplo], n, 
                                      ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                        alpha.imag)),
                                      int(x), incx, int(A), lda)
    cublasCheckStatus(status)
    
# SSYR2, DSYR2, CSYR2, ZSYR2
_libcublas.cublasSsyr2_v2.restype = int
_libcublas.cublasSsyr2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSsyr2(handle, uplo, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-2 operation on real symmetric matrix.

    """

    status = _libcublas.cublasSsyr2_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(x), incx, int(y), incy,
                                       int(A), lda)
    cublasCheckStatus(status)

_libcublas.cublasDsyr2_v2.restype = int
_libcublas.cublasDsyr2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,                                   
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDsyr2(handle, uplo, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-2 operation on real symmetric matrix.

    """

    status = _libcublas.cublasDsyr2_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(ctypes.c_double(alpha)), 
                                       int(x), incx, int(y), incy, 
                                       int(A), lda)                                       
    cublasCheckStatus(status)

if _cublas_version >= 5000:
    _libcublas.cublasCsyr2_v2.restype = int
    _libcublas.cublasCsyr2_v2.argtypes = [_types.handle,
                                          ctypes.c_int,
                                          ctypes.c_int,                                   
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int]

@_cublas_version_req(5.0)                                          
def cublasCsyr2(handle, uplo, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-2 operation on complex symmetric matrix.

    """

    status = _libcublas.cublasCsyr2_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)), 
                                       int(x), incx, int(y), incy, 
                                       int(A), lda)                                       
    cublasCheckStatus(status)

if _cublas_version >= 5000:    
    _libcublas.cublasZsyr2_v2.restype = int
    _libcublas.cublasZsyr2_v2.argtypes = [_types.handle,
                                          ctypes.c_int,
                                          ctypes.c_int,                                   
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int]

@_cublas_version_req(5.0)                                          
def cublasZsyr2(handle, uplo, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-2 operation on complex symmetric matrix.

    """

    status = _libcublas.cublasZsyr2_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], n, 
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)), 
                                       int(x), incx, int(y), incy, 
                                       int(A), lda)                                       
    cublasCheckStatus(status)
    
# STBMV, DTBMV, CTBMV, ZTBMV
_libcublas.cublasStbmv_v2.restype = int
_libcublas.cublasStbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasStbmv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Matrix-vector product for real triangular-banded matrix.

    """
    
    status = _libcublas.cublasStbmv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasDtbmv_v2.restype = int
_libcublas.cublasDtbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtbmv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Matrix-vector product for real triangular-banded matrix.

    """

    status = _libcublas.cublasDtbmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)                                       
    cublasCheckStatus(status)

_libcublas.cublasCtbmv_v2.restype = int
_libcublas.cublasCtbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtbmv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Matrix-vector product for complex triangular-banded matrix.

    """
    
    status = _libcublas.cublasCtbmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)                           
    cublasCheckStatus(status)

_libcublas.cublasZtbmv_v2.restype = int
_libcublas.cublasZtbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtbmv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Matrix-vector product for complex triangular-banded matrix.

    """
    
    status = _libcublas.cublasZtbmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

# STBSV, DTBSV, CTBSV, ZTBSV
_libcublas.cublasStbsv_v2.restype = int
_libcublas.cublasStbsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasStbsv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Solve real triangular-banded system with one right-hand side.

    """
    
    status = _libcublas.cublasStbsv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)                                       
    cublasCheckStatus(status)

_libcublas.cublasDtbsv_v2.restype = int
_libcublas.cublasDtbsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtbsv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Solve real triangular-banded system with one right-hand side.

    """

    status = _libcublas.cublasDtbsv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)                           
    cublasCheckStatus(status)

_libcublas.cublasCtbsv_v2.restype = int
_libcublas.cublasCtbsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtbsv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Solve complex triangular-banded system with one right-hand side.

    """
    
    status = _libcublas.cublasCtbsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)                                       
    cublasCheckStatus(status)

_libcublas.cublasZtbsv_v2.restype = int
_libcublas.cublasZtbsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtbsv(handle, uplo, trans, diag, n, k, A, lda, x, incx):
    """
    Solve complex triangular-banded system with one right-hand side.

    """
    
    status = _libcublas.cublasZtbsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, k, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

# STPMV, DTPMV, CTPMV, ZTPMV
_libcublas.cublasStpmv_v2.restype = int
_libcublas.cublasStpmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasStpmv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Matrix-vector product for real triangular-packed matrix.

    """
    
    status = _libcublas.cublasStpmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasCtpmv_v2.restype = int
_libcublas.cublasCtpmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtpmv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Matrix-vector product for complex triangular-packed matrix.

    """
    
    status = _libcublas.cublasCtpmv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasDtpmv_v2.restype = int
_libcublas.cublasDtpmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtpmv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Matrix-vector product for real triangular-packed matrix.

    """

    status = _libcublas.cublasDtpmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasZtpmv_v2.restype = int
_libcublas.cublasZtpmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtpmv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Matrix-vector product for complex triangular-packed matrix.

    """
    
    status = _libcublas.cublasZtpmv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)

# STPSV, DTPSV, CTPSV, ZTPSV
_libcublas.cublasStpsv_v2.restype = int
_libcublas.cublasStpsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasStpsv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Solve real triangular-packed system with one right-hand side.

    """
    
    status = _libcublas.cublasStpsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)


_libcublas.cublasDtpsv_v2.restype = int
_libcublas.cublasDtpsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtpsv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Solve real triangular-packed system with one right-hand side.

    """

    status = _libcublas.cublasDtpsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasCtpsv_v2.restype = int
_libcublas.cublasCtpsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtpsv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Solve complex triangular-packed system with one right-hand side.
    
    """
    
    status = _libcublas.cublasCtpsv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasZtpsv_v2.restype = int
_libcublas.cublasZtpsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtpsv(handle, uplo, trans, diag, n, AP, x, incx):
    """
    Solve complex triangular-packed system with one right-hand size.

    """
    
    status = _libcublas.cublasZtpsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(AP), int(x), incx)
    cublasCheckStatus(status)

# STRMV, DTRMV, CTRMV, ZTRMV
_libcublas.cublasStrmv_v2.restype = int
_libcublas.cublasStrmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasStrmv(handle, uplo, trans, diag, n, A, lda, x, inx):
    """
    Matrix-vector product for real triangular matrix.

    """
    
    status = _libcublas.cublasStrmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), inx)                                       
    cublasCheckStatus(status)

_libcublas.cublasCtrmv_v2.restype = int
_libcublas.cublasCtrmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtrmv(handle, uplo, trans, diag, n, A, lda, x, incx):
    """
    Matrix-vector product for complex triangular matrix.

    """
    
    status = _libcublas.cublasCtrmv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasDtrmv_v2.restype = int
_libcublas.cublasDtrmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtrmv(handle, uplo, trans, diag, n, A, lda, x, inx):
    """
    Matrix-vector product for real triangular matrix.

    """

    status = _libcublas.cublasDtrmv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), inx)
    cublasCheckStatus(status)

_libcublas.cublasZtrmv_v2.restype = int
_libcublas.cublasZtrmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtrmv(handle, uplo, trans, diag, n, A, lda, x, incx):
    """
    Matrix-vector product for complex triangular matrix.

    """
    
    status = _libcublas.cublasZtrmv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

# STRSV, DTRSV, CTRSV, ZTRSV
_libcublas.cublasStrsv_v2.restype = int
_libcublas.cublasStrsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasStrsv(handle, uplo, trans, diag, n, A, lda, x, incx):
    """
    Solve real triangular system with one right-hand side.

    """
    
    status = _libcublas.cublasStrsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), incx)                                       
    cublasCheckStatus(status)

_libcublas.cublasDtrsv_v2.restype = int
_libcublas.cublasDtrsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtrsv(handle, uplo, trans, diag, n, A, lda, x, incx):
    """
    Solve real triangular system with one right-hand side.

    """

    status = _libcublas.cublasDtrsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasCtrsv_v2.restype = int
_libcublas.cublasCtrsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtrsv(handle, uplo, trans, diag, n, A, lda, x, incx):
    """
    Solve complex triangular system with one right-hand side.

    """
    
    status = _libcublas.cublasCtrsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

_libcublas.cublasZtrsv_v2.restype = int
_libcublas.cublasZtrsv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtrsv(handle, uplo, trans, diag, n, A, lda, x, incx):
    """
    Solve complex triangular system with one right-hand side.

    """
    
    status = _libcublas.cublasZtrsv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       n, int(A), lda, int(x), incx)
    cublasCheckStatus(status)

# CHEMV, ZHEMV
_libcublas.cublasChemv_v2.restype = int
_libcublas.cublasChemv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasChemv(handle, uplo, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix vector product for Hermitian matrix.
    
    """
    
    status = _libcublas.cublasChemv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                           alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

_libcublas.cublasZhemv_v2.restype = int
_libcublas.cublasZhemv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,                                       
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZhemv(handle, uplo, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for Hermitian matrix.

    """
    
    status = _libcublas.cublasZhemv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                            alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real, 
                                                                         beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

# CHBMV, ZHBMV
_libcublas.cublasChbmv_v2.restype = int
_libcublas.cublasChbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasChbmv(handle, uplo, n, k, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for Hermitian-banded matrix.

    """
    
    status = _libcublas.cublasChbmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, k,
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

_libcublas.cublasZhbmv_v2.restype = int
_libcublas.cublasZhbmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZhbmv(handle, uplo, n, k, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for Hermitian banded matrix.

    """
    
    status = _libcublas.cublasZhbmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, k,
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)),
                                       int(A), lda, int(x), incx,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real, 
                                                                         beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

# CHPMV, ZHPMV
_libcublas.cublasChpmv_v2.restype = int
_libcublas.cublasChpmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasChpmv(handle, uplo, n, alpha, AP, x, incx, beta, y, incy):
    """
    Matrix-vector product for Hermitian-packed matrix.

    """
    
    status = _libcublas.cublasChpmv_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                           alpha.imag)),
                                       int(AP), int(x), incx,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

_libcublas.cublasZhpmv_v2.restype = int
_libcublas.cublasZhpmv_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZhpmv(handle, uplo, n, alpha, AP, x, incx, beta, y, incy):
    """
    Matrix-vector product for Hermitian-packed matrix.

    """
    
    status = _libcublas.cublasZhpmv_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                            alpha.imag)),
                                       int(AP), int(x), incx,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real, 
                                                                         beta.imag)),
                                       int(y), incy)
    cublasCheckStatus(status)

# CHER, ZHER
_libcublas.cublasCher_v2.restype = int
_libcublas.cublasCher_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def cublasCher(handle, uplo, n, alpha, x, incx, A, lda):
    """
    Rank-1 operation on Hermitian matrix.

    """

    status = _libcublas.cublasCher_v2(handle, 
                                      _CUBLAS_FILL_MODE[uplo], 
                                      n, alpha, int(x), incx, int(A), lda)
    cublasCheckStatus(status)

_libcublas.cublasZher_v2.restype = int
_libcublas.cublasZher_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,                                     
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def cublasZher(handle, uplo, n, alpha, x, incx, A, lda):
    """
    Rank-1 operation on Hermitian matrix.

    """
    
    status = _libcublas.cublasZher_v2(handle, 
                                      _CUBLAS_FILL_MODE[uplo], 
                                      n, alpha, int(x), incx, int(A), lda)
    cublasCheckStatus(status)


# CHER2, ZHER2
_libcublas.cublasCher2_v2.restype = int
_libcublas.cublasCher2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCher2(handle, uplo, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-2 operation on Hermitian matrix.


    """
    
    status = _libcublas.cublasCher2_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                           alpha.imag)),
                                       int(x), incx, int(y), incy, int(A), lda)                           
    cublasCheckStatus(status)

_libcublas.cublasZher2_v2.restype = int
_libcublas.cublasZher2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZher2(handle, uplo, n, alpha, x, incx, y, incy, A, lda):
    """
    Rank-2 operation on Hermitian matrix.

    """
    
    status = _libcublas.cublasZher2_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                            alpha.imag)),
                                       int(x), incx, int(y), incy, int(A), lda)
    cublasCheckStatus(status)

# CHPR, ZHPR
_libcublas.cublasChpr_v2.restype = int
_libcublas.cublasChpr_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,                                     
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p]
def cublasChpr(handle, uplo, n, alpha, x, incx, AP):
    """
    Rank-1 operation on Hermitian-packed matrix.
    
    """
    
    status = _libcublas.cublasChpr_v2(handle, 
                                      _CUBLAS_FILL_MODE[uplo], 
                                      n, ctypes.byref(ctypes.c_float(alpha)),
                                      int(x), incx, int(AP))
    cublasCheckStatus(status)

_libcublas.cublasZhpr_v2.restype = int
_libcublas.cublasZhpr_v2.argtypes = [_types.handle,
                                     ctypes.c_int,
                                     ctypes.c_int,                                     
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p]
def cublasZhpr(handle, uplo, n, alpha, x, incx, AP):
    """
    Rank-1 operation on Hermitian-packed matrix.

    """
    
    status = _libcublas.cublasZhpr_v2(handle,
                                      _CUBLAS_FILL_MODE[uplo], 
                                      n, ctypes.byref(ctypes.c_double(alpha)),
                                      int(x), incx, int(AP))
    cublasCheckStatus(status)

# CHPR2, ZHPR2
_libcublas.cublasChpr2.restype = int
_libcublas.cublasChpr2.argtypes = [_types.handle,
                                   ctypes.c_int,
                                   ctypes.c_int,                                   
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p]
def cublasChpr2(handle, uplo, n, alpha, x, inx, y, incy, AP):
    """
    Rank-2 operation on Hermitian-packed matrix.

    """

    status = _libcublas.cublasChpr2_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo],
                                       n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                           alpha.imag)),
                                       int(x), incx, int(y), incy, int(AP))
    cublasCheckStatus(status)

_libcublas.cublasZhpr2_v2.restype = int
_libcublas.cublasZhpr2_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def cublasZhpr2(handle, uplo, n, alpha, x, inx, y, incy, AP):
    """
    Rank-2 operation on Hermitian-packed matrix.

    """
    
    status = _libcublas.cublasZhpr2_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,  
                                                                            alpha.imag)),
                                       int(x), incx, int(y), incy, int(AP))
    cublasCheckStatus(status)

# SGEMM, CGEMM, DGEMM, ZGEMM
_libcublas.cublasSgemm_v2.restype = int
_libcublas.cublasSgemm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSgemm(handle, transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for real general matrix.

    """

    status = _libcublas.cublasSgemm_v2(handle,
                                       _CUBLAS_OP[transa],
                                       _CUBLAS_OP[transb], m, n, k, 
                                       ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, int(B), ldb,
                                       ctypes.byref(ctypes.c_float(beta)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasCgemm_v2.restype = int
_libcublas.cublasCgemm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCgemm(handle, transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for complex general matrix.

    """

    status = _libcublas.cublasCgemm_v2(handle,
                                       _CUBLAS_OP[transa],
                                       _CUBLAS_OP[transb], m, n, k, 
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)),
                                       int(A), lda, int(B), ldb,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasDgemm_v2.restype = int
_libcublas.cublasDgemm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDgemm(handle, transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for real general matrix.

    """

    status = _libcublas.cublasDgemm_v2(handle,
                                       _CUBLAS_OP[transa],
                                       _CUBLAS_OP[transb], m, n, k, 
                                       ctypes.byref(ctypes.c_double(alpha)),
                                       int(A), lda, int(B), ldb,
                                       ctypes.byref(ctypes.c_double(beta)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasZgemm_v2.restype = int
_libcublas.cublasZgemm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZgemm(handle, transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for complex general matrix.

    """

    status = _libcublas.cublasZgemm_v2(handle,
                                       _CUBLAS_OP[transa],
                                       _CUBLAS_OP[transb], m, n, k, 
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)),
                                       int(A), lda, int(B), ldb,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                         beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)
    
# SSYMM, DSYMM, CSYMM, ZSYMM
_libcublas.cublasSsymm_v2.restype = int
_libcublas.cublasSsymm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSsymm(handle, side, uplo, m, n, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for symmetric matrix.

    """
    
    status = _libcublas.cublasSsymm_v2(handle,
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       m, n, ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, int(B), ldb, 
                                       ctypes.byref(ctypes.c_float(beta)), 
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasDsymm_v2.restype = int
_libcublas.cublasDsymm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]

def cublasDsymm(handle, side, uplo, m, n, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for real symmetric matrix.

    """
    
    status = _libcublas.cublasDsymm_v2(handle,
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo],
                                       m, n, ctypes.byref(ctypes.c_double(alpha)),
                                       int(A), lda, int(B), ldb, 
                                       ctypes.byref(ctypes.c_double(beta)), 
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasCsymm_v2.restype = int
_libcublas.cublasCsymm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCsymm(handle, side, uplo, m, n, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for complex symmetric matrix.

    """
    
    status = _libcublas.cublasCsymm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       m, n, ctypes.byref(cuda.cuFloatComplex(alpha.real,                   
                                                                              alpha.imag)),
                                       int(A), lda, int(B), ldb,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real, 
                                                                        beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasZsymm_v2.restype = int
_libcublas.cublasZsymm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZsymm(handle, side, uplo, m, n, alpha, A, lda, B, ldb, beta, C, ldc):                
    """
    Matrix-matrix product for complex symmetric matrix.

    """
    
    status = _libcublas.cublasZsymm_v2(handle,
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], m, n,
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)),
                                       int(A), lda, int(B), ldb,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                         beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

# SSYRK, DSYRK, CSYRK, ZSYRK
_libcublas.cublasSsyrk_v2.restype = int
_libcublas.cublasSsyrk_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasSsyrk(handle, uplo, trans, n, k, alpha, A, lda, beta, C, ldc):
    """
    Rank-k operation on real symmetric matrix.

    """
    
    status = _libcublas.cublasSsyrk_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       n, k, ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, 
                                       ctypes.byref(ctypes.c_float(beta)), 
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasDsyrk_v2.restype = int
_libcublas.cublasDsyrk_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDsyrk(handle, uplo, trans, n, k, alpha, A, lda, beta, C, ldc):
    """
    Rank-k operation on real symmetric matrix.

    """
    
    status = _libcublas.cublasDsyrk_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       n, k, ctypes.byref(cuda.cuFloatComplex(alpha.real,     
                                                                              alpha.imag)),
                                       int(A), lda, 
                                       ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasCsyrk_v2.restype = int
_libcublas.cublasCsyrk_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCsyrk(handle, uplo, trans, n, k, alpha, A, lda, beta, C, ldc):
    """
    Rank-k operation on complex symmetric matrix.

    """
    
    status = _libcublas.cublasCsyrk_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       n, k, ctypes.byref(cuda.cuFloatComplex(alpha.real,       
                                                                              alpha.imag)),
                                       int(A), lda,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real, 
                                                                        beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasZsyrk_v2.restype = int
_libcublas.cublasZsyrk_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZsyrk(handle, uplo, trans, n, k, alpha, A, lda, beta, C, ldc):
    """
    Rank-k operation on complex symmetric matrix.

    """
    
    status = _libcublas.cublasZsyrk_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       n, k, ctypes.byref(cuda.cuDoubleComplex(alpha.real,    
                                                                               alpha.imag)),
                                       int(A), lda,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                         beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

# SSYR2K, DSYR2K, CSYR2K, ZSYR2K
_libcublas.cublasSsyr2k_v2.restype = int
_libcublas.cublasSsyr2k_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                       
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
def cublasSsyr2k(handle, uplo, trans, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Rank-2k operation on real symmetric matrix.

    """
    
    status = _libcublas.cublasSsyr2k_v2(handle,
                                        _CUBLAS_FILL_MODE[uplo], 
                                        _CUBLAS_OP[trans], 
                                        n, k, ctypes.byref(ctypes.c_float(alpha)),
                                        int(A), lda, int(B), ldb, 
                                        ctypes.byref(ctypes.c_float(beta)), 
                                        int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasDsyr2k_v2.restype = int
_libcublas.cublasDsyr2k_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                       
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
def cublasDsyr2k(handle, uplo, trans, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Rank-2k operation on real symmetric matrix.

    """

    status = _libcublas.cublasDsyr2k_v2(handle, 
                                        _CUBLAS_FILL_MODE[uplo], 
                                        _CUBLAS_OP[trans], 
                                        n, k, ctypes.byref(ctypes.c_double(alpha)),
                                        int(A), lda, int(B), ldb, 
                                        ctypes.byref(ctypes.c_double(beta)), 
                                        int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasCsyr2k_v2.restype = int
_libcublas.cublasCsyr2k_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                       
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
def cublasCsyr2k(handle, uplo, trans, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Rank-2k operation on complex symmetric matrix.

    """

    status = _libcublas.cublasCsyr2k_v2(handle,
                                        _CUBLAS_FILL_MODE[uplo], 
                                        _CUBLAS_OP[trans], 
                                        n, k, ctypes.byref(cuda.cuFloatComplex(alpha.real,                
                                                                               alpha.imag)),
                                        int(A), lda, int(B), ldb,
                                        ctypes.byref(cuda.cuFloatComplex(beta.real, 
                                                                         beta.imag)),
                                        int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasZsyr2k_v2.restype = int
_libcublas.cublasZsyr2k_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                       
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
def cublasZsyr2k(handle, uplo, trans, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Rank-2k operation on complex symmetric matrix.
    
    """
    
    status = _libcublas.cublasZsyr2k_v2(handle,
                                        _CUBLAS_FILL_MODE[uplo], 
                                        _CUBLAS_OP[trans], 
                                        n, k, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                                alpha.imag)),
                                        int(A), lda, int(B), ldb,
                                        ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                          beta.imag)),
                                        int(C), ldc)
    cublasCheckStatus(status)

# STRMM, DTRMM, CTRMM, ZTRMM
_libcublas.cublasStrmm_v2.restype = int
_libcublas.cublasStrmm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,                                      
                                      ctypes.c_int]
def cublasStrmm(handle, side, uplo, trans, diag, m, n, alpha, A, lda, B, ldb, C, ldc):
    """
    Matrix-matrix product for real triangular matrix.

    """
    
    status = _libcublas.cublasStrmm_v2(handle,
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, int(B), ldb, int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasDtrmm_v2.restype = int
_libcublas.cublasDtrmm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                       
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtrmm(handle, side, uplo, trans, diag, m, n, alpha, A, lda, B, ldb, C, ldc):                
    """
    Matrix-matrix product for real triangular matrix.

    """
    
    status = _libcublas.cublasDtrmm_v2(handle,
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(ctypes.c_double(alpha)),
                                       int(A), lda, int(B), ldb, int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasCtrmm_v2.restype = int
_libcublas.cublasCtrmm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                       
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtrmm(handle, side, uplo, trans, diag, m, n, alpha, A, lda, B, ldb, C, ldc):    
    """
    Matrix-matrix product for complex triangular matrix.

    """
    
    status = _libcublas.cublasCtrmm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                              alpha.imag)),
                                       int(A), lda, int(B), ldb)
    cublasCheckStatus(status)

_libcublas.cublasZtrmm_v2.restype = int
_libcublas.cublasZtrmm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtrmm(handle, side, uplo, trans, diag, m, n, alpha, A, lda, B, ldb, C, ldc):
    """
    Matrix-matrix product for complex triangular matrix.

    """
    
    status = _libcublas.cublasZtrmm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,     
                                                                               alpha.imag)),
                                       int(A), lda, int(B), ldb, int(C), ldc)
    cublasCheckStatus(status)

# STRSM, DTRSM, CTRSM, ZTRSM
_libcublas.cublasStrsm_v2.restype = int
_libcublas.cublasStrsm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasStrsm(handle, side, uplo, trans, diag, m, n, alpha, A, lda, B, ldb):
    """
    Solve a real triangular system with multiple right-hand sides.

    """
    
    status = _libcublas.cublasStrsm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, int(B), ldb)
    cublasCheckStatus(status)

_libcublas.cublasDtrsm_v2.restype = int
_libcublas.cublasDtrsm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasDtrsm(handle, side, uplo, trans, diag, m, n, alpha, A, lda, B, ldb):
    """
    Solve a real triangular system with multiple right-hand sides.

    """
    
    status = _libcublas.cublasDtrsm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(ctypes.c_double(alpha)),
                                       int(A), lda, int(B), ldb)
    cublasCheckStatus(status)

_libcublas.cublasCtrsm_v2.restype = int
_libcublas.cublasCtrsm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCtrsm(handle, side, uplo, trans, diag, m, n, alpha, A, lda, B, ldb):
    """
    Solve a complex triangular system with multiple right-hand sides.

    """
    
    status = _libcublas.cublasCtrsm_v2(handle,
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                              alpha.imag)),
                                       int(A), lda, int(B), ldb)
    cublasCheckStatus(status)

_libcublas.cublasZtrsm_v2.restype = int
_libcublas.cublasZtrsm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZtrsm(handle, side, uplo, transa, diag, m, n, alpha, A, lda, B, ldb):
    """
    Solve complex triangular system with multiple right-hand sides.

    """
    
    status = _libcublas.cublasZtrsm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       _CUBLAS_DIAG[diag], 
                                       m, n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,                    
                                                                               alpha.imag)),
                                       int(A), lda, int(B), ldb)
    cublasCheckStatus(status)

# CHEMM, ZHEMM
_libcublas.cublasChemm_v2.restype = int
_libcublas.cublasChemm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasChemm(handle, side, uplo, m, n, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for complex Hermitian matrix.

    """
    
    status = _libcublas.cublasChemm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], m, n,
                                       ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)),
                                       int(A), lda, int(B), ldb,
                                       ctypes.byref(cuda.cuFloatComplex(beta.real, 
                                                                        beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasZhemm_v2.restype = int
_libcublas.cublasZhemm_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZhemm(handle, side, uplo, m, n, alpha, A, lda, B, ldb, beta, C, ldc):                
    """
    Matrix-matrix product for Hermitian matrix.

    """
    
    status = _libcublas.cublasZhemm_v2(handle, 
                                       _CUBLAS_SIDE_MODE[side], 
                                       _CUBLAS_FILL_MODE[uplo], m, n,                                       
                                       ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                         alpha.imag)),
                                                                         int(A), lda, int(B), ldb,
                                       ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                         beta.imag)),
                                       int(C), ldc)
    cublasCheckStatus(status)

# CHERK, ZHERK
_libcublas.cublasCherk_v2.restype = int
_libcublas.cublasCherk_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasCherk(handle, uplo, trans, n, k, alpha, A, lda, beta, C, ldc):
    """
    Rank-k operation on Hermitian matrix.

    """
    
    status = _libcublas.cublasCherk_v2(handle, 
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans], 
                                       n, k, ctypes.byref(ctypes.c_float(alpha)),
                                       int(A), lda, 
                                       ctypes.byref(ctypes.c_float(beta)),
                                       int(C), ldc)
    cublasCheckStatus(status)

_libcublas.cublasZherk_v2.restype = int
_libcublas.cublasZherk_v2.argtypes = [_types.handle,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,                                      
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def cublasZherk(handle, uplo, trans, n, k, alpha, A, lda, beta, C, ldc):
    """
    Rank-k operation on Hermitian matrix.

    """
    
    status = _libcublas.cublasZherk_v2(handle,
                                       _CUBLAS_FILL_MODE[uplo], 
                                       _CUBLAS_OP[trans],
                                       n, k, ctypes.byref(ctypes.c_double(alpha)),
                                       int(A), lda, 
                                       ctypes.byref(ctypes.c_double(beta)),
                                       int(C), ldc)
    cublasCheckStatus(status)

# CHER2K, ZHER2K
_libcublas.cublasCher2k_v2.restype = int
_libcublas.cublasCher2k_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_float,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
def cublasCher2k(handle, uplo, trans, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Rank-2k operation on Hermitian matrix.

    """
    
    status = _libcublas.cublasCher2k_v2(handle, 
                                        _CUBLAS_FILL_MODE[uplo], 
                                        _CUBLAS_OP[trans], 
                                        n, k, ctypes.byref(cuda.cuFloatComplex(alpha.real,                 
                                                                               alpha.imag)),
                                        int(A), lda, int(B), ldb, 
                                        ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                         beta.imag)),
                                        int(C), ldc)
    cublasCheckStatus(status)
        
_libcublas.cublasZher2k_v2.restype = int
_libcublas.cublasZher2k_v2.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                       
                                       ctypes.c_void_p,                                       
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
def cublasZher2k(handle, uplo, trans, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Rank-2k operation on Hermitian matrix.

    """

    status = _libcublas.cublasZher2k_v2(handle,
                                        _CUBLAS_FILL_MODE[uplo], 
                                        _CUBLAS_OP[trans], 
                                        n, k, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                                alpha.imag)),
                                        int(A), lda, int(B), ldb,
                                        ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                          beta.imag)), 
                                        int(C), ldc)
    cublasCheckStatus(status)

### BLAS-like extension routines ###

# SGEAM, DGEAM, CGEAM, ZGEAM
_GEAM_doc = Template(
"""
    Matrix-matrix addition/transposition (${precision} ${real}).

    Computes the sum of two ${precision} ${real} scaled and possibly (conjugate)
    transposed matrices.

    Parameters
    ----------
    handle : int
        CUBLAS context
    transa, transb : char        
        't' if they are transposed, 'c' if they are conjugate transposed,
        'n' if otherwise.
    m : int
        Number of rows in `A` and `C`.
    n : int
        Number of columns in `B` and `C`.
    alpha : ${num_type}
        Constant by which to scale `A`.
    A : ctypes.c_void_p
        Pointer to first matrix operand (`A`).
    lda : int
        Leading dimension of `A`.
    beta : ${num_type}
        Constant by which to scale `B`.
    B : ctypes.c_void_p
        Pointer to second matrix operand (`B`).
    ldb : int
        Leading dimension of `A`.
    C : ctypes.c_void_p
        Pointer to result matrix (`C`).
    ldc : int
        Leading dimension of `C`.
    
    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> alpha = ${alpha_data}
    >>> beta = ${beta_data}
    >>> a = ${a_data_1} 
    >>> b = ${b_data_1}
    >>> c = ${c_data_1}
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> b_gpu = gpuarray.to_gpu(b)
    >>> c_gpu = gpuarray.empty(c.shape, c.dtype)
    >>> h = cublasCreate()
    >>> ${func}(h, 'n', 'n', c.shape[0], c.shape[1], alpha, a_gpu.gpudata, a.shape[0], beta, b_gpu.gpudata, b.shape[0], c_gpu.gpudata, c.shape[0])    
    >>> np.allclose(c_gpu.get(), c)
    True
    >>> a = ${a_data_2}
    >>> b = ${b_data_2}
    >>> c = ${c_data_2}
    >>> a_gpu = gpuarray.to_gpu(a.T.copy())
    >>> b_gpu = gpuarray.to_gpu(b.T.copy())
    >>> c_gpu = gpuarray.empty(c.T.shape, c.dtype)
    >>> transa = 'c' if np.iscomplexobj(a) else 't'
    >>> ${func}(h, transa, 'n', c.shape[0], c.shape[1], alpha, a_gpu.gpudata, a.shape[0], beta, b_gpu.gpudata, b.shape[0], c_gpu.gpudata, c.shape[0])    
    >>> np.allclose(c_gpu.get().T, c)
    True
    >>> cublasDestroy(h)
""")

if _cublas_version >= 5000:
    _libcublas.cublasSgeam.restype = int
    _libcublas.cublasSgeam.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                   
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5.0)                                   
def cublasSgeam(handle, transa, transb,
                m, n, alpha, A, lda, beta, B, ldb, C, ldc):    
    status = _libcublas.cublasSgeam(handle,
                                    _CUBLAS_OP[transa],
                                    _CUBLAS_OP[transb],
                                    m, n, ctypes.byref(ctypes.c_float(alpha)),
                                    int(A), lda, 
                                    ctypes.byref(ctypes.c_float(beta)),
                                    int(B), ldb,
                                    int(C), ldc)
    cublasCheckStatus(status)
cublasSgeam.__doc__ = _GEAM_doc.substitute(precision='single-precision',
                                           real='real',
                                           num_type='numpy.float32',
                                           alpha_data='np.float32(np.random.rand())',
                                           beta_data='np.float32(np.random.rand())',
                                           a_data_1='np.random.rand(2, 3).astype(np.float32)',
                                           b_data_1='np.random.rand(2, 3).astype(np.float32)',
                                           a_data_2='np.random.rand(2, 3).astype(np.float32)',
                                           b_data_2='np.random.rand(3, 2).astype(np.float32)',
                                           c_data_1='alpha*a+beta*b',
                                           c_data_2='alpha*a.T+beta*b',
                                           func='cublasSgeam')
                                           
if _cublas_version >= 5000:                                    
    _libcublas.cublasDgeam.restype = int
    _libcublas.cublasDgeam.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                   
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5.0)                                   
def cublasDgeam(handle, transa, transb,
                m, n, alpha, A, lda, beta, B, ldb, C, ldc):
    status = _libcublas.cublasDgeam(handle,
                                    _CUBLAS_OP[transa],
                                    _CUBLAS_OP[transb],
                                    m, n, ctypes.byref(ctypes.c_double(alpha)),
                                    int(A), lda,                                    
                                    ctypes.byref(ctypes.c_double(beta)),
                                    int(B), ldb,
                                    int(C), ldc)
    cublasCheckStatus(status)
cublasDgeam.__doc__ = _GEAM_doc.substitute(precision='double-precision',
                                           real='real',
                                           num_type='numpy.float64',
                                           alpha_data='np.float64(np.random.rand())',
                                           beta_data='np.float64(np.random.rand())',
                                           a_data_1='np.random.rand(2, 3).astype(np.float64)',
                                           b_data_1='np.random.rand(2, 3).astype(np.float64)',
                                           a_data_2='np.random.rand(2, 3).astype(np.float64)',
                                           b_data_2='np.random.rand(3, 2).astype(np.float64)',
                                           c_data_1='alpha*a+beta*b',
                                           c_data_2='alpha*a.T+beta*b',
                                           func='cublasDgeam')
    
if _cublas_version >= 5000:                                    
    _libcublas.cublasCgeam.restype = int
    _libcublas.cublasCgeam.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                   
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5.0)                                   
def cublasCgeam(handle, transa, transb,
                m, n, alpha, A, lda, beta, B, ldb, C, ldc):
    status = _libcublas.cublasCgeam(handle,
                                    _CUBLAS_OP[transa],
                                    _CUBLAS_OP[transb],
                                    m, n, 
                                    ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                     alpha.imag)),
                                    int(A), lda,
                                    ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                     beta.imag)),
                                    int(B), ldb,
                                    int(C), ldc)
    cublasCheckStatus(status)
cublasCgeam.__doc__ = _GEAM_doc.substitute(precision='single-precision',
                                           real='complex',
                                           num_type='numpy.complex64',
                                           alpha_data='np.complex64(np.random.rand()+1j*np.random.rand())',
                                           beta_data='np.complex64(np.random.rand()+1j*np.random.rand())',
                                           a_data_1='(np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex64)',
                                           a_data_2='(np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex64)',
                                           b_data_1='(np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex64)',
                                           b_data_2='(np.random.rand(3, 2)+1j*np.random.rand(3, 2)).astype(np.complex64)',
                                           c_data_1='alpha*a+beta*b',
                                           c_data_2='alpha*np.conj(a).T+beta*b',
                                           func='cublasCgeam')
    
if _cublas_version >= 5000:                                    
    _libcublas.cublasZgeam.restype = int
    _libcublas.cublasZgeam.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,                                   
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5.0)                                   
def cublasZgeam(handle, transa, transb,
                m, n, alpha, A, lda, beta, B, ldb, C, ldc):
    status = _libcublas.cublasZgeam(handle,
                                    _CUBLAS_OP[transa],
                                    _CUBLAS_OP[transb],
                                    m, n, 
                                    ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                      alpha.imag)),
                                    int(A), lda,                                    
                                    ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                      beta.imag)),
                                    int(B), ldb,
                                    int(C), ldc)
    cublasCheckStatus(status)
cublasZgeam.__doc__ = _GEAM_doc.substitute(precision='double-precision',
                                           real='complex',
                                           num_type='numpy.complex128',
                                           alpha_data='np.complex128(np.random.rand()+1j*np.random.rand())',
                                           beta_data='np.complex128(np.random.rand()+1j*np.random.rand())',
                                           a_data_1='(np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex128)',
                                           a_data_2='(np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex128)',
                                           b_data_1='(np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex128)',
                                           b_data_2='(np.random.rand(3, 2)+1j*np.random.rand(3, 2)).astype(np.complex128)',
                                           c_data_1='alpha*a+beta*b',
                                           c_data_2='alpha*np.conj(a).T+beta*b',
                                           func='cublasZgeam')
    
# SDGMM, DDGMM, CDGMM, ZDGMM
if _cublas_version >= 5000:
    _libcublas.cublasSdgmm.restype = int
    _libcublas.cublasSdgmm.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5.0)
def cublasSdgmm(handle, mode, m, n, A, lda, x, incx, C, ldc):
    """
    Matrix-diagonal matrix product for real general matrix.
    
    """

    status = _libcublas.cublasSdgmm(handle,
                                    _CUBLAS_SIDE_MODE[mode],
                                    m, n, 
                                    int(A), lda, 
                                    int(x), incx,
                                    int(C), ldc)
    cublasCheckStatus(status)

if _cublas_version >= 5000:    
    _libcublas.cublasDdgmm.restype = int
    _libcublas.cublasDdgmm.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5)
def cublasDdgmm(handle, mode, m, n, A, lda, x, incx, C, ldc):
    """
    Matrix-diagonal matrix product for real general matrix.
    
    """

    status = _libcublas.cublasDdgmm(handle,
                                    _CUBLAS_SIDE_MODE[mode],
                                    m, n, 
                                    int(A), lda, 
                                    int(x), incx,
                                    int(C), ldc)
    cublasCheckStatus(status)
    
if _cublas_version >= 5000:
    _libcublas.cublasCdgmm.restype = int
    _libcublas.cublasCdgmm.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5)
def cublasCdgmm(mode, m, n, A, lda, x, incx, C, ldc):
    """
    Matrix-diagonal matrix product for complex general matrix.
    
    """

    status = _libcublas.cublasCdgmm(handle,
                                    _CUBLAS_SIDE_MODE[mode],
                                    m, n, 
                                    int(A), lda, 
                                    int(x), incx,
                                    int(C), ldc)
    cublasCheckStatus(status)

if _cublas_version >= 5000:    
    _libcublas.cublasZdgmm.restype = int
    _libcublas.cublasZdgmm.argtypes = [_types.handle,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int]
@_cublas_version_req(5)
def cublasZdgmm(mode, m, n, A, lda, x, incx, C, ldc):
    """
    Matrix-diagonal matrix product for complex general matrix.
    
    """

    status = _libcublas.cublasZdgmm(handle,
                                    _CUBLAS_SIDE_MODE[mode],
                                    m, n, 
                                    int(A), lda, 
                                    int(x), incx,
                                    int(C), ldc)
    cublasCheckStatus(status)        
    
### Batched routines ###

# SgemmBatched, DgemmBatched
if _cublas_version >= 5000:
    _libcublas.cublasSgemmBatched.restype = int
    _libcublas.cublasSgemmBatched.argtypes = [_types.handle,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_int]
@_cublas_version_req(5.0)
def cublasSgemmBatched(handle, transa, transb, m, n, k, 
                       alpha, A, lda, B, ldb, beta, C, ldc, batchCount):
    """
    Matrix-matrix product for arrays of real general matrices.

    """

    status = _libcublas.cublasSgemmBatched(handle,
                                           _CUBLAS_OP[transa],
                                           _CUBLAS_OP[transb], m, n, k, 
                                           ctypes.byref(ctypes.c_float(alpha)),
                                           int(A), lda, int(B), ldb,
                                           ctypes.byref(ctypes.c_float(beta)),
                                           int(C), ldc, batchCount)
    cublasCheckStatus(status)

if _cublas_version >= 5000:    
    _libcublas.cublasDgemmBatched.restype = int
    _libcublas.cublasDgemmBatched.argtypes = [_types.handle,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_int]
@_cublas_version_req(5.0)
def cublasDgemmBatched(handle, transa, transb, m, n, k, 
                       alpha, A, lda, B, ldb, beta, C, ldc, batchCount):
    """
    Matrix-matrix product for arrays of real general matrices.

    """

    status = _libcublas.cublasDgemmBatched(handle,
                                           _CUBLAS_OP[transa],
                                           _CUBLAS_OP[transb], m, n, k, 
                                           ctypes.byref(ctypes.c_double(alpha)),
                                           int(A), lda, int(B), ldb,
                                           ctypes.byref(ctypes.c_double(beta)),
                                           int(C), ldc, batchCount)
    cublasCheckStatus(status)

# CgemmBatched, ZgemmBatched

if _cublas_version >= 5000:
    _libcublas.cublasCgemmBatched.restype = int
    _libcublas.cublasCgemmBatched.argtypes = [_types.handle,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_int]
@_cublas_version_req(5.0)
def cublasCgemmBatched(handle, transa, transb, m, n, k, 
                       alpha, A, lda, B, ldb, beta, C, ldc, batchCount):
    """
    Matrix-matrix product for arrays of complex general matrices.

    """

    status = _libcublas.cublasCgemmBatched(handle,
                                           _CUBLAS_OP[transa],
                                           _CUBLAS_OP[transb], m, n, k, 
                                           ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                                        alpha.imag)),
                                           int(A), lda, int(B), ldb,
                                           ctypes.byref(cuda.cuFloatComplex(beta.real,
                                                                        beta.imag)),
                                           int(C), ldc, batchCount)

if _cublas_version >= 5000:
    _libcublas.cublasZgemmBatched.restype = int
    _libcublas.cublasZgemmBatched.argtypes = [_types.handle,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_int]
@_cublas_version_req(5.0)
def cublasZgemmBatched(handle, transa, transb, m, n, k, 
                       alpha, A, lda, B, ldb, beta, C, ldc, batchCount):
    """
    Matrix-matrix product for arrays of complex general matrices.

    """

    status = _libcublas.cublasZgemmBatched(handle,
                                           _CUBLAS_OP[transa],
                                           _CUBLAS_OP[transb], m, n, k, 
                                           ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                                        alpha.imag)),
                                           int(A), lda, int(B), ldb,
                                           ctypes.byref(cuda.cuDoubleComplex(beta.real,
                                                                        beta.imag)),
                                           int(C), ldc, batchCount)
    
# StrsmBatched, DtrsmBatched
if _cublas_version >= 5000:
    _libcublas.cublasStrsmBatched.restype = int
    _libcublas.cublasStrsmBatched.argtypes = [_types.handle,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_int]
@_cublas_version_req(5.0)
def cublasStrsmBatched(handle, side, uplo, trans, diag, m, n, alpha, 
                       A, lda, B, ldb, batchCount):
    """
    This function solves an array of triangular linear systems with multiple right-hand-sides.

    """

    status = _libcublas.cublasStrsmBatched(handle,
                                           _CUBLAS_SIDE_MODE[side],
                                           _CUBLAS_FILL_MODE[uplo],
                                           _CUBLAS_OP[trans],
                                           _CUBLAS_DIAG[diag],
                                           m, n, 
                                           ctypes.byref(ctypes.c_float(alpha)),
                                           int(A), lda, int(B), ldb,
                                           batchCount)
    cublasCheckStatus(status)

if _cublas_version >= 5000:    
    _libcublas.cublasDtrsmBatched.restype = int
    _libcublas.cublasDtrsmBatched.argtypes = [_types.handle,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_void_p,
                                              ctypes.c_int,
                                              ctypes.c_int]
@_cublas_version_req(5.0)
def cublasDtrsmBatched(handle, side, uplo, trans, diag, m, n, alpha, 
                       A, lda, B, ldb, batchCount):
    """
    This function solves an array of triangular linear systems with multiple right-hand-sides.

    """

    status = _libcublas.cublasDtrsmBatched(handle,
                                           _CUBLAS_SIDE_MODE[side],
                                           _CUBLAS_FILL_MODE[uplo],
                                           _CUBLAS_OP[trans],
                                           _CUBLAS_DIAG[diag],
                                           m, n, 
                                           ctypes.byref(ctypes.c_double(alpha)),
                                           int(A), lda, int(B), ldb,
                                           batchCount)
    cublasCheckStatus(status)
    

# SgetrfBatched, DgetrfBatched
if _cublas_version >= 5000:
    _libcublas.cublasSgetrfBatched.restype = int
    _libcublas.cublasSgetrfBatched.argtypes = [_types.handle,
                                               ctypes.c_int,
                                               ctypes.c_void_p,
                                               ctypes.c_int,
                                               ctypes.c_void_p,
                                               ctypes.c_void_p,
                                               ctypes.c_int]
@_cublas_version_req(5.0)
def cublasSgetrfBatched(handle, n, A, lda, P, info, batchSize):
    """
    This function performs the LU factorization of an array of n x n matrices.
    """

    status = _libcublas.cublasSgetrfBatched(handle, n,
                                            int(A), lda, int(P), 
                                            int(info), batchSize)                                       
    cublasCheckStatus(status)

if _cublas_version >= 5000:    
    _libcublas.cublasDgetrfBatched.restype = int
    _libcublas.cublasDgetrfBatched.argtypes = [_types.handle,
                                               ctypes.c_int,
                                               ctypes.c_void_p,
                                               ctypes.c_int,
                                               ctypes.c_void_p,
                                               ctypes.c_void_p,
                                               ctypes.c_int]
@_cublas_version_req(5.0)
def cublasDgetrfBatched(handle, n, A, lda, P, info, batchSize):
    """
    This function performs the LU factorization of an array of n x n matrices.
    """

    status = _libcublas.cublasDgetrfBatched(handle, n,
                                            int(A), lda, int(P), 
                                            int(info), batchSize)                                       
    cublasCheckStatus(status)
     
if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = cuda
#!/usr/bin/env python

"""
Python interface to CUDA functions.
"""

from cudart import *
from cudadrv import *


########NEW FILE########
__FILENAME__ = cudadrv
#!/usr/bin/env python

"""
Python interface to CUDA driver functions.
"""

import sys, ctypes

# Load CUDA driver library:
if sys.platform == 'linux2':
    _libcuda_libname_list = ['libcuda.so', 'libcuda.so.3', 'libcuda.so.4']
elif sys.platform == 'darwin':
    _libcuda_libname_list = ['libcuda.dylib']
elif sys.platform == 'Windows':
    _libcuda_libname_list = ['cuda.lib']
else:
    raise RuntimeError('unsupported platform')

# Print understandable error message when library cannot be found:
_libcuda = None
for _libcuda_libname in _libcuda_libname_list:
    try:
        _libcuda = ctypes.cdll.LoadLibrary(_libcuda_libname)
    except OSError:
        pass
    else:
        break
if _libcuda == None:
    raise OSError('CUDA driver library not found')


# Exceptions corresponding to various CUDA driver errors:

class CUDA_ERROR(Exception):
    """CUDA error."""
    pass

class CUDA_ERROR_INVALID_VALUE(CUDA_ERROR):
    pass

class CUDA_ERROR_OUT_OF_MEMORY(CUDA_ERROR):
    pass

class CUDA_ERROR_NOT_INITIALIZED(CUDA_ERROR):
    pass

class CUDA_ERROR_DEINITIALIZED(CUDA_ERROR):
    pass

class CUDA_ERROR_PROFILER_DISABLED(CUDA_ERROR):
    pass

class CUDA_ERROR_PROFILER_NOT_INITIALIZED(CUDA_ERROR):
    pass

class CUDA_ERROR_PROFILER_ALREADY_STARTED(CUDA_ERROR):
    pass

class CUDA_ERROR_PROFILER_ALREADY_STOPPED(CUDA_ERROR):
    pass

class CUDA_ERROR_NO_DEVICE(CUDA_ERROR):
    pass

class CUDA_ERROR_INVALID_DEVICE(CUDA_ERROR):
    pass

class CUDA_ERROR_INVALID_IMAGE(CUDA_ERROR):
    pass

class CUDA_ERROR_INVALID_CONTEXT(CUDA_ERROR):
    pass

class CUDA_ERROR_CONTEXT_ALREADY_CURRENT(CUDA_ERROR):
    pass

class CUDA_ERROR_MAP_FAILED(CUDA_ERROR):
    pass

class CUDA_ERROR_UNMAP_FAILED(CUDA_ERROR):
    pass

class CUDA_ERROR_ARRAY_IS_MAPPED(CUDA_ERROR):
    pass

class CUDA_ERROR_ALREADY_MAPPED(CUDA_ERROR):
    pass

class CUDA_ERROR_NO_BINARY_FOR_GPU(CUDA_ERROR):
    pass

class CUDA_ERROR_ALREADY_ACQUIRED(CUDA_ERROR):
    pass

class CUDA_ERROR_NOT_MAPPED(CUDA_ERROR):
    pass

class CUDA_ERROR_NOT_MAPPED_AS_ARRAY(CUDA_ERROR):
    pass

class CUDA_ERROR_NOT_MAPPED_AS_POINTER(CUDA_ERROR):
    pass

class CUDA_ERROR_ECC_UNCORRECTABLE(CUDA_ERROR):
    pass

class CUDA_ERROR_UNSUPPORTED_LIMIT(CUDA_ERROR):
    pass

class CUDA_ERROR_CONTEXT_ALREADY_IN_USE(CUDA_ERROR):
    pass

class CUDA_ERROR_INVALID_SOURCE(CUDA_ERROR):
    pass

class CUDA_ERROR_FILE_NOT_FOUND(CUDA_ERROR):
    pass

class CUDA_ERROR_SHARED_OBJECT_SYMBOL_NOT_FOUND(CUDA_ERROR):
    pass

class CUDA_ERROR_SHARED_OBJECT_INIT_FAILED(CUDA_ERROR):
    pass

class CUDA_ERROR_OPERATING_SYSTEM(CUDA_ERROR):
    pass

class CUDA_ERROR_INVALID_HANDLE(CUDA_ERROR):
    pass

class CUDA_ERROR_NOT_FOUND(CUDA_ERROR):
    pass

class CUDA_ERROR_NOT_READY(CUDA_ERROR):
    pass


CUDA_EXCEPTIONS = {
    1: CUDA_ERROR_INVALID_VALUE,
    2: CUDA_ERROR_OUT_OF_MEMORY,
    3: CUDA_ERROR_NOT_INITIALIZED,
    4: CUDA_ERROR_DEINITIALIZED,
    5: CUDA_ERROR_PROFILER_DISABLED,
    6: CUDA_ERROR_PROFILER_NOT_INITIALIZED,
    7: CUDA_ERROR_PROFILER_ALREADY_STARTED,
    8: CUDA_ERROR_PROFILER_ALREADY_STOPPED,
    100: CUDA_ERROR_NO_DEVICE,
    101: CUDA_ERROR_INVALID_DEVICE,
    200: CUDA_ERROR_INVALID_IMAGE,
    201: CUDA_ERROR_INVALID_CONTEXT,
    202: CUDA_ERROR_CONTEXT_ALREADY_CURRENT,
    205: CUDA_ERROR_MAP_FAILED,
    206: CUDA_ERROR_UNMAP_FAILED,
    207: CUDA_ERROR_ARRAY_IS_MAPPED,
    208: CUDA_ERROR_ALREADY_MAPPED,
    209: CUDA_ERROR_NO_BINARY_FOR_GPU,
    210: CUDA_ERROR_ALREADY_ACQUIRED,
    211: CUDA_ERROR_NOT_MAPPED,
    212: CUDA_ERROR_NOT_MAPPED_AS_ARRAY,
    213: CUDA_ERROR_NOT_MAPPED_AS_POINTER,
    214: CUDA_ERROR_ECC_UNCORRECTABLE,
    215: CUDA_ERROR_UNSUPPORTED_LIMIT,
    216: CUDA_ERROR_CONTEXT_ALREADY_IN_USE,
    300: CUDA_ERROR_INVALID_SOURCE,
    301: CUDA_ERROR_FILE_NOT_FOUND,
    302: CUDA_ERROR_SHARED_OBJECT_SYMBOL_NOT_FOUND,
    303: CUDA_ERROR_SHARED_OBJECT_INIT_FAILED,
    304: CUDA_ERROR_OPERATING_SYSTEM,
    400: CUDA_ERROR_INVALID_HANDLE,
    500: CUDA_ERROR_NOT_FOUND,
    600: CUDA_ERROR_NOT_READY,
    }

def cuCheckStatus(status):
    """
    Raise CUDA exception.

    Raise an exception corresponding to the specified CUDA driver
    error code.

    Parameters
    ----------
    status : int
        CUDA driver error code.

    See Also
    --------
    CUDA_EXCEPTIONS

    """

    if status != 0:
        try:
            raise CUDA_EXCEPTIONS[status]
        except KeyError:
            raise CUDA_ERROR

        
CU_POINTER_ATTRIBUTE_CONTEXT = 1
CU_POINTER_ATTRIBUTE_MEMORY_TYPE = 2 
CU_POINTER_ATTRIBUTE_DEVICE_POINTER = 3
CU_POINTER_ATTRIBUTE_HOST_POINTER = 4

_libcuda.cuPointerGetAttribute.restype = int
_libcuda.cuPointerGetAttribute.argtypes = [ctypes.c_void_p,
                                           ctypes.c_int,
                                           ctypes.c_uint]
def cuPointerGetAttribute(attribute, ptr):
    data = ctypes.c_void_p()
    status = _libcuda.cuPointerGetAttribute(data, attribute, ptr)
    cuCheckStatus(status)
    return data

########NEW FILE########
__FILENAME__ = cudart
#!/usr/bin/env python

"""
Python interface to CUDA runtime functions.
"""

import atexit, ctypes, sys, warnings
import numpy as np

# Load CUDA runtime library:
if sys.platform == 'linux2':
    _libcudart_libname_list = ['libcudart.so', 'libcudart.so.3', 'libcudart.so.4']
elif sys.platform == 'darwin':
    _libcudart_libname_list = ['libcudart.dylib']
elif sys.platform == 'win32':
    _libcudart_libname_list = ['cudart.lib']
else:
    raise RuntimeError('unsupported platform')

# Print understandable error message when library cannot be found:
_libcudart = None
for _libcudart_libname in _libcudart_libname_list:
    try:
        _libcudart = ctypes.cdll.LoadLibrary(_libcudart_libname)
    except OSError:
        pass
    else:
        break
if _libcudart == None:
    raise OSError('CUDA runtime library not found')

# Code adapted from PARRET:
def POINTER(obj):
    """
    Create ctypes pointer to object.

    Notes
    -----
    This function converts None to a real NULL pointer because of bug
    in how ctypes handles None on 64-bit platforms.

    """

    p = ctypes.POINTER(obj)
    if not isinstance(p.from_param, classmethod):
        def from_param(cls, x):
            if x is None:
                return cls()
            else:
                return x
        p.from_param = classmethod(from_param)

    return p

# Classes corresponding to CUDA vector structures:
class float2(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_float),
        ('y', ctypes.c_float)
        ]

class cuFloatComplex(float2):
    @property
    def value(self):
        return complex(self.x, self.y)

class double2(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_double),
        ('y', ctypes.c_double)
        ]

class cuDoubleComplex(double2):
    @property
    def value(self):
        return complex(self.x, self.y)

def gpuarray_ptr(g):
    """
    Return ctypes pointer to data in GPUAarray object.

    """

    addr = int(g.gpudata)
    if g.dtype == np.int8:
        return ctypes.cast(addr, POINTER(ctypes.c_byte))
    if g.dtype == np.uint8:
        return ctypes.cast(addr, POINTER(ctypes.c_ubyte))
    if g.dtype == np.int16:
        return ctypes.cast(addr, POINTER(ctypes.c_short))
    if g.dtype == np.uint16:
        return ctypes.cast(addr, POINTER(ctypes.c_ushort))
    if g.dtype == np.int32:
        return ctypes.cast(addr, POINTER(ctypes.c_int))
    if g.dtype == np.uint32:
        return ctypes.cast(addr, POINTER(ctypes.c_uint))
    if g.dtype == np.int64:
        return ctypes.cast(addr, POINTER(ctypes.c_long))
    if g.dtype == np.uint64:
        return ctypes.cast(addr, POINTER(ctypes.c_ulong))
    if g.dtype == np.float32:
        return ctypes.cast(addr, POINTER(ctypes.c_float))
    elif g.dtype == np.float64:
        return ctypes.cast(addr, POINTER(ctypes.c_double))
    elif g.dtype == np.complex64:
        return ctypes.cast(addr, POINTER(cuFloatComplex))
    elif g.dtype == np.complex128:
        return ctypes.cast(addr, POINTER(cuDoubleComplex))
    else:
        raise ValueError('unrecognized type')

_libcudart.cudaGetErrorString.restype = ctypes.c_char_p
_libcudart.cudaGetErrorString.argtypes = [ctypes.c_int]
def cudaGetErrorString(e):
    """
    Retrieve CUDA error string.

    Return the string associated with the specified CUDA error status
    code.

    Parameters
    ----------
    e : int
        Error number.

    Returns
    -------
    s : str
        Error string.

    """

    return _libcudart.cudaGetErrorString(e)

# Generic CUDA error:
class cudaError(Exception):
    """CUDA error."""
    pass

# Exceptions corresponding to various CUDA runtime errors:
class cudaErrorMissingConfiguration(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(1)
    pass

class cudaErrorMemoryAllocation(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(2)
    pass

class cudaErrorInitializationError(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(3)
    pass

class cudaErrorLaunchFailure(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(4)
    pass

class cudaErrorPriorLaunchFailure(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(5)
    pass

class cudaErrorLaunchTimeout(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(6)
    pass

class cudaErrorLaunchOutOfResources(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(7)
    pass

class cudaErrorInvalidDeviceFunction(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(8)
    pass

class cudaErrorInvalidConfiguration(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(9)
    pass

class cudaErrorInvalidDevice(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(10)
    pass

class cudaErrorInvalidValue(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(11)
    pass

class cudaErrorInvalidPitchValue(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(12)
    pass

class cudaErrorInvalidSymbol(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(13)
    pass

class cudaErrorMapBufferObjectFailed(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(14)
    pass

class cudaErrorUnmapBufferObjectFailed(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(15)
    pass

class cudaErrorInvalidHostPointer(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(16)
    pass

class cudaErrorInvalidDevicePointer(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(17)
    pass

class cudaErrorInvalidTexture(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(18)
    pass

class cudaErrorInvalidTextureBinding(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(19)
    pass

class cudaErrorInvalidChannelDescriptor(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(20)
    pass

class cudaErrorInvalidMemcpyDirection(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(21)
    pass

class cudaErrorTextureFetchFailed(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(23)
    pass

class cudaErrorTextureNotBound(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(24)
    pass

class cudaErrorSynchronizationError(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(25)
    pass

class cudaErrorInvalidFilterSetting(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(26)
    pass

class cudaErrorInvalidNormSetting(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(27)
    pass

class cudaErrorMixedDeviceExecution(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(28)
    pass

class cudaErrorCudartUnloading(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(29)
    pass

class cudaErrorUnknown(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(30)
    pass

class cudaErrorNotYetImplemented(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(31)
    pass

class cudaErrorMemoryValueTooLarge(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(32)
    pass

class cudaErrorInvalidResourceHandle(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(33)
    pass

class cudaErrorNotReady(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(34)
    pass

class cudaErrorInsufficientDriver(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(35)
    pass

class cudaErrorSetOnActiveProcess(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(36)
    pass

class cudaErrorInvalidSurface(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(37)
    pass

class cudaErrorNoDevice(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(38)
    pass

class cudaErrorECCUncorrectable(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(39)
    pass

class cudaErrorSharedObjectSymbolNotFound(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(40)
    pass

class cudaErrorSharedObjectInitFailed(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(41)
    pass

class cudaErrorUnsupportedLimit(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(42)
    pass

class cudaErrorDuplicateVariableName(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(43)
    pass

class cudaErrorDuplicateTextureName(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(44)
    pass

class cudaErrorDuplicateSurfaceName(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(45)
    pass

class cudaErrorDevicesUnavailable(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(46)
    pass

class cudaErrorInvalidKernelImage(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(47)
    pass

class cudaErrorNoKernelImageForDevice(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(48)
    pass

class cudaErrorIncompatibleDriverContext(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(49)
    pass

class cudaErrorPeerAccessAlreadyEnabled(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(50)
    pass

class cudaErrorPeerAccessNotEnabled(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(51)
    pass

class cudaErrorDeviceAlreadyInUse(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(54)
    pass

class cudaErrorProfilerDisabled(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(55)
    pass

class cudaErrorProfilerNotInitialized(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(56)
    pass

class cudaErrorProfilerAlreadyStarted(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(57)
    pass

class cudaErrorProfilerAlreadyStopped(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(58)
    pass

class cudaErrorStartupFailure(cudaError):
    __doc__ = _libcudart.cudaGetErrorString(127)
    pass

cudaExceptions = {
    1: cudaErrorMissingConfiguration,
    2: cudaErrorMemoryAllocation,
    3: cudaErrorInitializationError,
    4: cudaErrorLaunchFailure,
    5: cudaErrorPriorLaunchFailure,
    6: cudaErrorLaunchTimeout,
    7: cudaErrorLaunchOutOfResources,
    8: cudaErrorInvalidDeviceFunction,
    9: cudaErrorInvalidConfiguration,
    10: cudaErrorInvalidDevice,
    11: cudaErrorInvalidValue,
    12: cudaErrorInvalidPitchValue,
    13: cudaErrorInvalidSymbol,
    14: cudaErrorMapBufferObjectFailed,
    15: cudaErrorUnmapBufferObjectFailed,
    16: cudaErrorInvalidHostPointer,
    17: cudaErrorInvalidDevicePointer,
    18: cudaErrorInvalidTexture,
    19: cudaErrorInvalidTextureBinding,
    20: cudaErrorInvalidChannelDescriptor,
    21: cudaErrorInvalidMemcpyDirection,
    22: cudaError,
    23: cudaErrorTextureFetchFailed,
    24: cudaErrorTextureNotBound,
    25: cudaErrorSynchronizationError,
    26: cudaErrorInvalidFilterSetting,
    27: cudaErrorInvalidNormSetting,
    28: cudaErrorMixedDeviceExecution,
    29: cudaErrorCudartUnloading,
    30: cudaErrorUnknown,
    31: cudaErrorNotYetImplemented,
    32: cudaErrorMemoryValueTooLarge,
    33: cudaErrorInvalidResourceHandle,
    34: cudaErrorNotReady,
    35: cudaErrorInsufficientDriver,
    36: cudaErrorSetOnActiveProcess,
    37: cudaErrorInvalidSurface,
    38: cudaErrorNoDevice,
    39: cudaErrorECCUncorrectable,
    40: cudaErrorSharedObjectSymbolNotFound,
    41: cudaErrorSharedObjectInitFailed,
    42: cudaErrorUnsupportedLimit,
    43: cudaErrorDuplicateVariableName,
    44: cudaErrorDuplicateTextureName,
    45: cudaErrorDuplicateSurfaceName,
    46: cudaErrorDevicesUnavailable,
    47: cudaErrorInvalidKernelImage,
    48: cudaErrorNoKernelImageForDevice,
    49: cudaErrorIncompatibleDriverContext,
    50: cudaErrorPeerAccessAlreadyEnabled,
    51: cudaErrorPeerAccessNotEnabled,
    52: cudaError,
    53: cudaError,
    54: cudaErrorDeviceAlreadyInUse,
    55: cudaErrorProfilerDisabled,
    56: cudaErrorProfilerNotInitialized,
    57: cudaErrorProfilerAlreadyStarted,
    58: cudaErrorProfilerAlreadyStopped,
    127: cudaErrorStartupFailure
    }

def cudaCheckStatus(status):
    """
    Raise CUDA exception.

    Raise an exception corresponding to the specified CUDA runtime error
    code.

    Parameters
    ----------
    status : int
        CUDA runtime error code.

    See Also
    --------
    cudaExceptions

    """

    if status != 0:
        try:
            raise cudaExceptions[status]
        except KeyError:
            raise cudaError

# Memory allocation functions (adapted from pystream):
_libcudart.cudaMalloc.restype = int
_libcudart.cudaMalloc.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                  ctypes.c_size_t]
def cudaMalloc(count, ctype=None):
    """
    Allocate device memory.

    Allocate memory on the device associated with the current active
    context.

    Parameters
    ----------
    count : int
        Number of bytes of memory to allocate
    ctype : _ctypes.SimpleType, optional
        ctypes type to cast returned pointer.

    Returns
    -------
    ptr : ctypes pointer
        Pointer to allocated device memory.

    """

    ptr = ctypes.c_void_p()
    status = _libcudart.cudaMalloc(ctypes.byref(ptr), count)
    cudaCheckStatus(status)
    if ctype != None:
        ptr = ctypes.cast(ptr, ctypes.POINTER(ctype))
    return ptr

_libcudart.cudaFree.restype = int
_libcudart.cudaFree.argtypes = [ctypes.c_void_p]
def cudaFree(ptr):
    """
    Free device memory.

    Free allocated memory on the device associated with the current active
    context.

    Parameters
    ----------
    ptr : ctypes pointer
        Pointer to allocated device memory.

    """

    status = _libcudart.cudaFree(ptr)
    cudaCheckStatus(status)

_libcudart.cudaMallocPitch.restype = int
_libcudart.cudaMallocPitch.argtypes = [ctypes.POINTER(ctypes.c_void_p),
                                       ctypes.POINTER(ctypes.c_size_t),
                                       ctypes.c_size_t, ctypes.c_size_t]
def cudaMallocPitch(pitch, rows, cols, elesize):
    """
    Allocate pitched device memory.

    Allocate pitched memory on the device associated with the current active
    context.

    Parameters
    ----------
    pitch : int
        Pitch for allocation.
    rows : int
        Requested pitched allocation height.
    cols : int
        Requested pitched allocation width.
    elesize : int
        Size of memory element.

    Returns
    -------
    ptr : ctypes pointer
        Pointer to allocated device memory.

    """

    ptr = ctypes.c_void_p()
    status = _libcudart.cudaMallocPitch(ctypes.byref(ptr),
                                        ctypes.c_size_t(pitch), cols*elesize,
                                        rows)
    cudaCheckStatus(status)
    return ptr, pitch

# Memory copy modes:
cudaMemcpyHostToHost = 0
cudaMemcpyHostToDevice = 1
cudaMemcpyDeviceToHost = 2
cudaMemcpyDeviceToDevice = 3
cudaMemcpyDefault = 4

_libcudart.cudaMemcpy.restype = int
_libcudart.cudaMemcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.c_int]
def cudaMemcpy_htod(dst, src, count):
    """
    Copy memory from host to device.

    Copy data from host memory to device memory.

    Parameters
    ----------
    dst : ctypes pointer
        Device memory pointer.
    src : ctypes pointer
        Host memory pointer.
    count : int
        Number of bytes to copy.

    """

    status = _libcudart.cudaMemcpy(dst, src,
                                   ctypes.c_size_t(count),
                                   cudaMemcpyHostToDevice)
    cudaCheckStatus(status)

def cudaMemcpy_dtoh(dst, src, count):
    """
    Copy memory from device to host.

    Copy data from device memory to host memory.

    Parameters
    ----------
    dst : ctypes pointer
        Host memory pointer.
    src : ctypes pointer
        Device memory pointer.
    count : int
        Number of bytes to copy.

    """

    status = _libcudart.cudaMemcpy(dst, src,
                                   ctypes.c_size_t(count),
                                   cudaMemcpyDeviceToHost)
    cudaCheckStatus(status)

_libcudart.cudaMemGetInfo.restype = int
_libcudart.cudaMemGetInfo.argtypes = [ctypes.c_void_p,
                                      ctypes.c_void_p]
def cudaMemGetInfo():
    """
    Return the amount of free and total device memory.

    Returns
    -------
    free : long
        Free memory in bytes.
    total : long
        Total memory in bytes.

    """

    free = ctypes.c_size_t()
    total = ctypes.c_size_t()
    status = _libcudart.cudaMemGetInfo(ctypes.byref(free),
                                       ctypes.byref(total))
    cudaCheckStatus(status)
    return free.value, total.value

_libcudart.cudaSetDevice.restype = int
_libcudart.cudaSetDevice.argtypes = [ctypes.c_int]
def cudaSetDevice(dev):
    """
    Set current CUDA device.

    Select a device to use for subsequent CUDA operations.

    Parameters
    ----------
    dev : int
        Device number.

    """

    status = _libcudart.cudaSetDevice(dev)
    cudaCheckStatus(status)

_libcudart.cudaGetDevice.restype = int
_libcudart.cudaGetDevice.argtypes = [ctypes.POINTER(ctypes.c_int)]
def cudaGetDevice():
    """
    Get current CUDA device.

    Return the identifying number of the device currently used to
    process CUDA operations.

    Returns
    -------
    dev : int
        Device number.

    """

    dev = ctypes.c_int()
    status = _libcudart.cudaGetDevice(ctypes.byref(dev))
    cudaCheckStatus(status)
    return dev.value

_libcudart.cudaDriverGetVersion.restype = int
_libcudart.cudaDriverGetVersion.argtypes = [ctypes.POINTER(ctypes.c_int)]
def cudaDriverGetVersion():
    """
    Get installed CUDA driver version.

    Return the version of the installed CUDA driver as an integer. If
    no driver is detected, 0 is returned.

    Returns
    -------
    version : int
        Driver version.

    """

    version = ctypes.c_int()
    status = _libcudart.cudaDriverGetVersion(ctypes.byref(version))
    cudaCheckStatus(status)
    return version.value

# Memory types:
cudaMemoryTypeHost = 1
cudaMemoryTypeDevice = 2

class cudaPointerAttributes(ctypes.Structure):
    _fields_ = [
        ('memoryType', ctypes.c_int),
        ('device', ctypes.c_int),
        ('devicePointer', ctypes.c_void_p),
        ('hostPointer', ctypes.c_void_p)
        ]

_libcudart.cudaPointerGetAttributes.restype = int
_libcudart.cudaPointerGetAttributes.argtypes = [ctypes.c_void_p,
                                                ctypes.c_void_p]
def cudaPointerGetAttributes(ptr):
    """
    Get memory pointer attributes.

    Returns attributes of the specified pointer.

    Parameters
    ----------
    ptr : ctypes pointer
        Memory pointer to examine.

    Returns
    -------
    memory_type : int
        Memory type; 1 indicates host memory, 2 indicates device
        memory.
    device : int
        Number of device associated with pointer.

    Notes
    -----
    This function only works with CUDA 4.0 and later.

    """

    attributes = cudaPointerAttributes()
    status = \
        _libcudart.cudaPointerGetAttributes(ctypes.byref(attributes), ptr)
    cudaCheckStatus(status)
    return attributes.memoryType, attributes.device


########NEW FILE########
__FILENAME__ = cufft
#!/usr/bin/env python

"""
Python interface to CUFFT functions.

Note: this module does not explicitly depend on PyCUDA.
"""

import ctypes, sys

if sys.platform == 'linux2':
    _libcufft_libname_list = ['libcufft.so', 'libcufft.so.3', 'libcufft.so.4']
elif sys.platform == 'darwin':
    _libcufft_libname_list = ['libcufft.dylib']
elif sys.platform == 'Windows':
    _libcufft_libname_list = ['cufft.lib']
else:
    raise RuntimeError('unsupported platform')

# Print understandable error message when library cannot be found:
_libcufft = None
for _libcufft_libname in _libcufft_libname_list:
    try:
        _libcufft = ctypes.cdll.LoadLibrary(_libcufft_libname)
    except OSError:
        pass
    else:
        break
if _libcufft == None:
    raise OSError('cufft library not found')

# General CUFFT error:
class cufftError(Exception):
    """CUFFT error"""
    pass

# Exceptions corresponding to different CUFFT errors:
class cufftInvalidPlan(cufftError):
    """CUFFT was passed an invalid plan handle."""
    pass

class cufftAllocFailed(cufftError):
    """CUFFT failed to allocate GPU memory."""
    pass

class cufftInvalidType(cufftError):
    """The user requested an unsupported type."""
    pass

class cufftInvalidValue(cufftError):
    """The user specified a bad memory pointer."""
    pass

class cufftInternalError(cufftError):
    """Internal driver error."""
    pass

class cufftExecFailed(cufftError):
    """CUFFT failed to execute an FFT on the GPU."""
    pass

class cufftSetupFailed(cufftError):
    """The CUFFT library failed to initialize."""
    pass

class cufftInvalidSize(cufftError):
    """The user specified an unsupported FFT size."""
    pass

class cufftUnalignedData(cufftError):
    """Input or output does not satisfy texture alignment requirements."""
    pass

cufftExceptions = {
    0x1: cufftInvalidPlan,
    0x2: cufftAllocFailed,
    0x3: cufftInvalidType,
    0x4: cufftInvalidValue,
    0x5: cufftInternalError,
    0x6: cufftExecFailed,
    0x7: cufftSetupFailed,
    0x8: cufftInvalidSize,
    0x9: cufftUnalignedData
    }


class _types:
    """Some alias types."""
    plan = ctypes.c_int
    stream = ctypes.c_void_p

def cufftCheckStatus(status):
    """Raise an exception if the specified CUBLAS status is an error."""

    if status != 0:
        try:
            raise cufftExceptions[status]
        except KeyError:
            raise cufftError


# Data transformation types:
CUFFT_R2C = 0x2a
CUFFT_C2R = 0x2c
CUFFT_C2C = 0x29
CUFFT_D2Z = 0x6a
CUFFT_Z2D = 0x6c
CUFFT_Z2Z = 0x69

# Transformation directions:
CUFFT_FORWARD = -1
CUFFT_INVERSE = 1

# FFTW compatibility modes:
CUFFT_COMPATIBILITY_NATIVE = 0x00
CUFFT_COMPATIBILITY_FFTW_PADDING = 0x01
CUFFT_COMPATIBILITY_FFTW_ASYMMETRIC = 0x02
CUFFT_COMPATIBILITY_FFTW_ALL = 0x03

# FFT functions implemented by CUFFT:
_libcufft.cufftPlan1d.restype = int
_libcufft.cufftPlan1d.argtypes = [ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_int]
def cufftPlan1d(nx, fft_type, batch):
    """Create 1D FFT plan configuration."""

    plan = _types.plan()
    status = _libcufft.cufftPlan1d(ctypes.byref(plan), nx, fft_type, batch)
    cufftCheckStatus(status)
    return plan

_libcufft.cufftPlan2d.restype = int
_libcufft.cufftPlan2d.argtypes = [ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_int]
def cufftPlan2d(nx, ny, fft_type):
    """Create 2D FFT plan configuration."""

    plan = _types.plan()
    status = _libcufft.cufftPlan2d(ctypes.byref(plan), nx, ny,
                                   fft_type)
    cufftCheckStatus(status)
    return plan

_libcufft.cufftPlan3d.restype = int
_libcufft.cufftPlan3d.argtypes = [ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_int]
def cufftPlan3d(nx, ny, nz, fft_type):
    """Create 3D FFT plan configuration."""

    plan = _types.plan()
    status = _libcufft.cufftPlan3d(ctypes.byref(plan), nx, ny, nz,
                                   fft_type)
    cufftCheckStatus(status)
    return plan

_libcufft.cufftPlanMany.restype = int
_libcufft.cufftPlanMany.argtypes = [ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_int]                                    
def cufftPlanMany(rank, n, 
                  inembed, istride, idist, 
                  onembed, ostride, odist, fft_type, batch):
    """Create batched FFT plan configuration."""

    plan = _types.plan()
    status = _libcufft.cufftPlanMany(ctypes.byref(plan), rank, n,
                                     inembed, istride, idist, 
                                     onembed, ostride, odist, 
                                     fft_type, batch)
    cufftCheckStatus(status)
    return plan

_libcufft.cufftDestroy.restype = int
_libcufft.cufftDestroy.argtypes = [_types.plan]
def cufftDestroy(plan):
    """Destroy FFT plan."""
    
    status = _libcufft.cufftDestroy(plan)
    cufftCheckStatus(status)

_libcufft.cufftSetCompatibilityMode.restype = int
_libcufft.cufftSetCompatibilityMode.argtypes = [_types.plan,
                                                ctypes.c_int]
def cufftSetCompatibilityMode(plan, mode):
    """Set FFTW compatibility mode."""

    status = _libcufft.cufftSetCompatibilityMode(plan, mode)
    cufftCheckStatus(status)

_libcufft.cufftExecC2C.restype = int
_libcufft.cufftExecC2C.argtypes = [_types.plan,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def cufftExecC2C(plan, idata, odata, direction):
    """Execute single precision complex-to-complex transform plan as
    specified by `direction`."""
    
    status = _libcufft.cufftExecC2C(plan, idata, odata,
                                    direction)
    cufftCheckStatus(status)

_libcufft.cufftExecR2C.restype = int
_libcufft.cufftExecR2C.argtypes = [_types.plan,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p]
def cufftExecR2C(plan, idata, odata):
    """Execute single precision real-to-complex forward transform plan."""
    
    status = _libcufft.cufftExecR2C(plan, idata, odata)
    cufftCheckStatus(status)

_libcufft.cufftExecC2R.restype = int
_libcufft.cufftExecC2R.argtypes = [_types.plan,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p]
def cufftExecC2R(plan, idata, odata):
    """Execute single precision complex-to-real reverse transform plan."""
    
    status = _libcufft.cufftExecC2R(plan, idata, odata)
    cufftCheckStatus(status)

_libcufft.cufftExecZ2Z.restype = int
_libcufft.cufftExecZ2Z.argtypes = [_types.plan,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def cufftExecZ2Z(plan, idata, odata, direction):
    """Execute double precision complex-to-complex transform plan as
    specified by `direction`."""
    
    status = _libcufft.cufftExecZ2Z(plan, idata, odata,
                                    direction)
    cufftCheckStatus(status)

_libcufft.cufftExecD2Z.restype = int
_libcufft.cufftExecD2Z.argtypes = [_types.plan,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p]
def cufftExecD2Z(plan, idata, odata):
    """Execute double precision real-to-complex forward transform plan."""
    
    status = _libcufft.cufftExecD2Z(plan, idata, odata)
    cufftCheckStatus(status)

_libcufft.cufftExecZ2D.restype = int
_libcufft.cufftExecZ2D.argtypes = [_types.plan,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p]
def cufftExecZ2D(plan, idata, odata):
    """Execute double precision complex-to-real transform plan."""
    
    status = _libcufft.cufftExecZ2D(plan, idata, odata)
    cufftCheckStatus(status)

_libcufft.cufftSetStream.restype = int
_libcufft.cufftSetStream.argtypes = [_types.plan,
                                     _types.stream]
def cufftSetStream(plan, stream):
    """Associate a CUDA stream with a CUFFT plan."""
    
    status = _libcufft.cufftSetStream(plan, stream)
    cufftCheckStatus(status)

########NEW FILE########
__FILENAME__ = cula
#!/usr/bin/env python

"""
Python interface to CULA toolkit.
"""

import sys
import ctypes
import atexit
import numpy as np

import cuda

# Load CULA library:
if sys.platform == 'linux2':
    _libcula_libname_list = ['libcula_lapack.so', 'libcula_lapack_basic.so', 'libcula.so']
elif sys.platform == 'darwin':
    _libcula_libname_list = ['libcula_lapack.so', 'libcula.dylib']
else:
    raise RuntimeError('unsupported platform')

_load_err = ''
for _lib in  _libcula_libname_list:
    try:
        _libcula = ctypes.cdll.LoadLibrary(_lib)
    except OSError:
        _load_err += ('' if _load_err == '' else ', ') + _lib
    else:
        _load_err = ''
        break
if _load_err:
    raise OSError('%s not found' % _load_err)

# Check whether the free or standard version of the toolkit is
# installed by trying to access a function that is only available in
# the latter:
try:
    _libcula.culaDeviceMalloc
except AttributeError:
    _libcula_toolkit = 'free'
else:
    _libcula_toolkit = 'standard'

# Function for retrieving string associated with specific CULA error
# code:
_libcula.culaGetStatusString.restype = ctypes.c_char_p
_libcula.culaGetStatusString.argtypes = [ctypes.c_int]
def culaGetStatusString(e):
    """
    Get string associated with the specified CULA status code.

    Parameters
    ----------
    e : int
        Status code.

    Returns
    -------
    s : str
        Status string.

    """

    return _libcula.culaGetStatusString(e)

# Generic CULA error:
class culaError(Exception):
    """CULA error."""
    pass

# Exceptions corresponding to various CULA errors:
class culaNotFound(culaError):
    """CULA shared library not found"""
    pass

class culaStandardNotFound(culaError):
    """Standard CULA Dense toolkit unavailable"""
    pass

class culaNotInitialized(culaError):
    try:
        __doc__ = culaGetStatusString(1)
    except:
        pass
    pass

class culaNoHardware(culaError):
    try:
        __doc__ = culaGetStatusString(2)
    except:
        pass
    pass

class culaInsufficientRuntime(culaError):
    try:
        __doc__ = culaGetStatusString(3)
    except:
        pass
    pass

class culaInsufficientComputeCapability(culaError):
    try:
        __doc__ = culaGetStatusString(4)
    except:
        pass
    pass

class culaInsufficientMemory(culaError):
    try:
        __doc__ = culaGetStatusString(5)
    except:
        pass
    pass

class culaFeatureNotImplemented(culaError):
    try:
        __doc__ = culaGetStatusString(6)
    except:
        pass
    pass

class culaArgumentError(culaError):
    try:
        __doc__ = culaGetStatusString(7)
    except:
        pass
    pass

class culaDataError(culaError):
    try:
        __doc__ = culaGetStatusString(8)
    except:
        pass
    pass

class culaBlasError(culaError):
    try:
        __doc__ = culaGetStatusString(9)
    except:
        pass
    pass

class culaRuntimeError(culaError):
    try:
        __doc__ = culaGetStatusString(10)
    except:
        pass
    pass

class culaBadStorageFormat(culaError):
    try:
        __doc__ = culaGetStatusString(11)
    except:
        pass
    pass

class culaInvalidReferenceHandle(culaError):
    try:
        __doc__ = culaGetStatusString(12)
    except:
        pass
    pass

class culaUnspecifiedError(culaError):
    try:
        __doc__ = culaGetStatusString(13)
    except:
        pass
    pass

culaExceptions = {
    -1: culaNotFound,
    1: culaNotInitialized,
    2: culaNoHardware,
    3: culaInsufficientRuntime,
    4: culaInsufficientComputeCapability,
    5: culaInsufficientMemory,
    6: culaFeatureNotImplemented,
    7: culaArgumentError,
    8: culaDataError,
    9: culaBlasError,
    10: culaRuntimeError,
    11: culaBadStorageFormat,
    12: culaInvalidReferenceHandle,
    13: culaUnspecifiedError,
    }

# CULA functions:
_libcula.culaGetErrorInfo.restype = int
def culaGetErrorInfo():
    """
    Returns extended information code for the last CULA error.

    Returns
    -------
    err : int
        Extended information code.
        
    """

    return _libcula.culaGetErrorInfo()

_libcula.culaGetErrorInfoString.restype = int
_libcula.culaGetErrorInfoString.argtypes = [ctypes.c_int,
                                            ctypes.c_void_p,
                                            ctypes.c_void_p,
                                            ctypes.c_int]
def culaGetErrorInfoString(e, i, bufsize=100):
    """
    Returns a readable CULA error string.

    Returns a readable error string corresponding to a given CULA
    error code and extended error information code.

    Parameters
    ----------
    e : int
        CULA error code.
    i : int
        Extended information code.
    bufsize : int
        Length of string to return.

    Returns
    -------
    s : str
        Error string.
        
    """

    buf = ctypes.create_string_buffer(bufsize)
    status = _libcula.culaGetErrorInfoString(e, i, buf, bufsize)
    culaCheckStatus(status)
    return buf.value
    
def culaGetLastStatus():
    """
    Returns the last status code returned from a CULA function.

    Returns
    -------
    s : int
        Status code.
        
    """
    
    return _libcula.culaGetLastStatus()

def culaCheckStatus(status):
    """
    Raise an exception corresponding to the specified CULA status
    code.

    Parameters
    ----------
    status : int
        CULA status code.
        
    """
    
    if status != 0:
        error = culaGetErrorInfo()
        try:
            raise culaExceptions[status](error)
        except KeyError:
            raise culaError(error)

_libcula.culaSelectDevice.restype = int
_libcula.culaSelectDevice.argtypes = [ctypes.c_int]
def culaSelectDevice(dev):
    """
    Selects a device with which CULA will operate.

    Parameters
    ----------
    dev : int
        GPU device number.
        
    Notes
    -----
    Must be called before `culaInitialize`.
    
    """

    status = _libcula.culaSelectDevice(dev)
    culaCheckStatus(status)

_libcula.culaGetExecutingDevice.restype = int
_libcula.culaGetExecutingDevice.argtypes = [ctypes.c_void_p]
def culaGetExecutingDevice():
    """
    Reports the id of the GPU device used by CULA.

    Returns
    -------
    dev : int
       Device id.

    """

    dev = ctypes.c_int()
    status = _libcula.culaGetExecutingDevice(ctypes.byref(dev))
    culaCheckStatus(status)
    return dev.value

def culaFreeBuffers():
    """
    Releases any memory buffers stored internally by CULA.

    """

    _libcula.culaFreeBuffers()

_libcula.culaGetVersion.restype = int    
def culaGetVersion():
    """
    Report the version number of CULA.

    """

    return _libcula.culaGetVersion()

_libcula.culaGetCudaMinimumVersion.restype = int
def culaGetCudaMinimumVersion():
    """
    Report the minimum version of CUDA required by CULA.

    """

    return _libcula.culaGetCudaMinimumVersion()

_libcula.culaGetCudaRuntimeVersion.restype = int
def culaGetCudaRuntimeVersion():
    """
    Report the version of the CUDA runtime linked to by the CULA library.

    """

    return _libcula.culaGetCudaRuntimeVersion()

_libcula.culaGetCudaDriverVersion.restype = int
def culaGetCudaDriverVersion():
    """
    Report the version of the CUDA driver installed on the system.

    """

    return _libcula.culaGetCudaDriverVersion()

_libcula.culaGetCublasMinimumVersion.restype = int
def culaGetCublasMinimumVersion():
    """
    Report the version of CUBLAS required by CULA.

    """

    return _libcula.culaGetCublasMinimumVersion()

_libcula.culaGetCublasRuntimeVersion.restype = int
def culaGetCublasRuntimeVersion():
    """
    Report the version of CUBLAS linked to by CULA.

    """

    return _libcula.culaGetCublasRuntimeVersion()

_libcula.culaGetDeviceCount.restype = int
def culaGetDeviceCount():
    """
    Report the number of available GPU devices.

    """
    return _libcula.culaGetDeviceCount()

_libcula.culaInitialize.restype = int
def culaInitialize():
    """
    Initialize CULA.

    Notes
    -----
    Must be called before using any other CULA functions.

    """
    
    status = _libcula.culaInitialize()
    culaCheckStatus(status)

_libcula.culaShutdown.restype = int    
def culaShutdown():
    """
    Shuts down CULA.
    """
    
    status = _libcula.culaShutdown()
    culaCheckStatus(status)

# Shut down CULA upon exit:
atexit.register(_libcula.culaShutdown)

# LAPACK functions available in CULA Dense Free:

# SGESV, CGESV
_libcula.culaDeviceSgesv.restype = \
_libcula.culaDeviceCgesv.restype = int
_libcula.culaDeviceSgesv.argtypes = \
_libcula.culaDeviceCgesv.argtypes = [ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def culaDeviceSgesv(n, nrhs, a, lda, ipiv, b, ldb):
    """
    Solve linear system with LU factorization.

    """

    status = _libcula.culaDeviceSgesv(n, nrhs, int(a), lda, int(ipiv),
                                      int(b), ldb)
    culaCheckStatus(status)

def culaDeviceCgesv(n, nrhs, a, lda, ipiv, b, ldb):
    """
    Solve linear system with LU factorization.

    """

    status = _libcula.culaDeviceCgesv(n, nrhs, int(a), lda, int(ipiv),
                                      int(b), ldb)
    culaCheckStatus(status)

# SGETRF, CGETRF    
_libcula.culaDeviceSgetrf.restype = \
_libcula.culaDeviceCgetrf.restype = int
_libcula.culaDeviceSgetrf.argtypes = \
_libcula.culaDeviceCgetrf.argtypes = [ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def culaDeviceSgetrf(m, n, a, lda, ipiv):
    """
    LU factorization.

    """
    
    status = _libcula.culaDeviceSgetrf(m, n, int(a), lda, int(ipiv))
    culaCheckStatus(status)

def culaDeviceCgetrf(m, n, a, lda, ipiv):
    """
    LU factorization.

    """
    
    status = _libcula.culaDeviceCgetrf(m, n, int(a), lda, int(ipiv))
    culaCheckStatus(status)

# SGEQRF, CGEQRF    
_libcula.culaDeviceSgeqrf.restype = \
_libcula.culaDeviceCgeqrf.restype = int
_libcula.culaDeviceSgeqrf.argtypes = \
_libcula.culaDeviceCgeqrf.argtypes = [ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p]
def culaDeviceSgeqrf(m, n, a, lda, tau):
    """
    QR factorization.

    """
    
    status = _libcula.culaDeviceSgeqrf(m, n, int(a), lda, int(tau))
    culaCheckStatus(status)

def culaDeviceCgeqrf(m, n, a, lda, tau):
    """
    QR factorization.

    """
    
    status = _libcula.culaDeviceCgeqrf(m, n, int(a), lda, int(tau))
    culaCheckStatus(status)

# SGELS, CGELS    
_libcula.culaDeviceSgels.restype = \
_libcula.culaDeviceCgels.restype = int
_libcula.culaDeviceSgels.argtypes = \
_libcula.culaDeviceCgels.argtypes = [ctypes.c_char,                           
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_void_p,                              
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int]
def culaDeviceSgels(trans, m, n, nrhs, a, lda, b, ldb):
    """
    Solve linear system with QR or LQ factorization.

    """
    
    status = _libcula.culaDeviceSgels(trans, m, n, nrhs, int(a),
                                      lda, int(b), ldb)
    culaCheckStatus(status)

def culaDeviceCgels(trans, m, n, nrhs, a, lda, b, ldb):
    """
    Solve linear system with QR or LQ factorization.

    """

    status = _libcula.culaDeviceCgels(trans, m, n, nrhs, int(a),
                                      lda, int(b), ldb)
    culaCheckStatus(status)

# SGGLSE, CGGLSE    
_libcula.culaDeviceSgglse.restype = \
_libcula.culaDeviceCgglse.restype = int
_libcula.culaDeviceSgglse.argtypes = \
_libcula.culaDeviceCgglse.argtypes = [ctypes.c_int,                             
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p]
def culaDeviceSgglse(m, n, p, a, lda, b, ldb, c, d, x):
    """
    Solve linear equality-constrained least squares problem.

    """
    
    status = _libcula.culaDeviceSgglse(m, n, p, int(a), lda, int(b),
                                       ldb, int(c), int(d), int(x))
    culaCheckStatus(status)

def culaDeviceCgglse(m, n, p, a, lda, b, ldb, c, d, x):
    """
    Solve linear equality-constrained least squares problem.

    """

    status = _libcula.culaDeviceCgglse(m, n, p, int(a), lda, int(b),
                                       ldb, int(c), int(d), int(x))
    culaCheckStatus(status)

# SGESVD, CGESVD    
_libcula.culaDeviceSgesvd.restype = \
_libcula.culaDeviceCgesvd.restype = int
_libcula.culaDeviceSgesvd.argtypes = \
_libcula.culaDeviceCgesvd.argtypes = [ctypes.c_char,
                                      ctypes.c_char,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_int]
def culaDeviceSgesvd(jobu, jobvt, m, n, a, lda, s, u, ldu, vt, ldvt):
    """
    SVD decomposition.

    """
    
    status = _libcula.culaDeviceSgesvd(jobu, jobvt, m, n, int(a), lda,
                                       int(s), int(u), ldu, int(vt),
                                       ldvt)
    culaCheckStatus(status)

def culaDeviceCgesvd(jobu, jobvt, m, n, a, lda, s, u, ldu, vt, ldvt):
    """
    SVD decomposition.

    """

    status = _libcula.culaDeviceCgesvd(jobu, jobvt, m, n, int(a), lda,
                                       int(s), int(u), ldu, int(vt),
                                       ldvt)
    culaCheckStatus(status)

# LAPACK functions available in CULA Dense:

# DGESV, ZGESV
try:
    _libcula.culaDeviceDgesv.restype = \
    _libcula.culaDeviceZgesv.restype = int
    _libcula.culaDeviceDgesv.argtypes = \
    _libcula.culaDeviceZgesv.argtypes = [ctypes.c_int,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_void_p,
                                         ctypes.c_int]
except AttributeError:
    def culaDeviceDgesv(n, nrhs, a, lda, ipiv, b, ldb):
        """
        Solve linear system with LU factorization.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgesv(n, nrhs, a, lda, ipiv, b, ldb):
        """
        Solve linear system with LU factorization.

        """

        raise NotImplementedError('CULA Dense required')
else:
    def culaDeviceDgesv(n, nrhs, a, lda, ipiv, b, ldb):
        """
        Solve linear system with LU factorization.

        """

        status = _libcula.culaDeviceDgesv(n, nrhs, int(a), lda, int(ipiv),
                                          int(b), ldb)
        culaCheckStatus(status)

    def culaDeviceZgesv(n, nrhs, a, lda, ipiv, b, ldb):
        """
        Solve linear system with LU factorization.

        """

        status = _libcula.culaDeviceZgesv(n, nrhs, int(a), lda, int(ipiv),
                                          int(b), ldb)
        culaCheckStatus(status)

# DGETRF, ZGETRF        
try:
    _libcula.culaDeviceDgetrf.restype = \
    _libcula.culaDeviceZgetrf.restype = int
    _libcula.culaDeviceDgetrf.argtypes = \
    _libcula.culaDeviceZgetrf.argtypes = [ctypes.c_int,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p]
except AttributeError:
    def culaDeviceDgetrf(m, n, a, lda, ipiv):
        """
        LU factorization.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgetrf(m, n, a, lda, ipiv):
        """
        LU factorization.

        """
        
        raise NotImplementedError('CULA Dense required')    
else:
    def culaDeviceDgetrf(m, n, a, lda, ipiv):
        """
        LU factorization.

        """

        status = _libcula.culaDeviceDgetrf(m, n, int(a), lda, int(ipiv))
        culaCheckStatus(status)

    def culaDeviceZgetrf(m, n, a, lda, ipiv):
        """
        LU factorization.

        """

        status = _libcula.culaDeviceZgetrf(m, n, int(a), lda, int(ipiv))
        culaCheckStatus(status)

# DGEQRF, ZGEQRF        
try:
    _libcula.culaDeviceDgeqrf.restype = \
    _libcula.culaDeviceZgeqrf.restype = int
    _libcula.culaDeviceDgeqrf.argtypes = \
    _libcula.culaDeviceZgeqrf.argtypes = [ctypes.c_int,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p]
except AttributeError:
    def culaDeviceDgeqrf(m, n, a, lda, tau):
        """
        QR factorization.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgeqrf(m, n, a, lda, tau):
        """
        QR factorization.

        """
        raise NotImplementedError('CULA Dense required')    
else:
    def culaDeviceDgeqrf(m, n, a, lda, tau):
        """
        QR factorization.

        """

        status = _libcula.culaDeviceDgeqrf(m, n, int(a), lda, int(tau))
        culaCheckStatus(status)

    def culaDeviceZgeqrf(m, n, a, lda, tau):
        """
        QR factorization.

        """

        status = _libcula.culaDeviceZgeqrf(m, n, int(a), lda, int(tau))
        culaCheckStatus(status)

# DGELS, ZGELS        
try:
    _libcula.culaDeviceDgels.restype = \
    _libcula.culaDeviceZgels.restype = int
    _libcula.culaDeviceDgels.argtypes = \
    _libcula.culaDeviceZgels.argtypes = [ctypes.c_char,                           
                                         ctypes.c_int,
                                         ctypes.c_int,
                                         ctypes.c_int,
                                         ctypes.c_void_p,                              
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_int]
except AttributeError:
    def culaDeviceDgels(trans, m, n, nrhs, a, lda, b, ldb):
        """
        Solve linear system with QR or LQ factorization.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgels(trans, m, n, nrhs, a, lda, b, ldb):
        """
        Solve linear system with QR or LQ factorization.

        """
        raise NotImplementedError('CULA Dense required')
else:  
    def culaDeviceDgels(trans, m, n, nrhs, a, lda, b, ldb):
        """
        Solve linear system with QR or LQ factorization.

        """

        status = _libcula.culaDeviceDgels(trans, m, n, nrhs, int(a),
                                          lda, int(b), ldb)
        culaCheckStatus(status)

    def culaDeviceZgels(trans, m, n, nrhs, a, lda, b, ldb):
        """
        Solve linear system with QR or LQ factorization.

        """

        status = _libcula.culaDeviceZgels(trans, m, n, nrhs, int(a),
                                          lda, int(b), ldb)
        culaCheckStatus(status)

# DGGLSE, ZGGLSE        
try:
    _libcula.culaDeviceDgglse.restype = \
    _libcula.culaDeviceZgglse.restype = int
    _libcula.culaDeviceDgglse.argtypes = \
    _libcula.culaDeviceZgglse.argtypes = [ctypes.c_int,                             
                                          ctypes.c_int,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_void_p]
except AttributeError:
    def culaDeviceDgglse(m, n, p, a, lda, b, ldb, c, d, x):
        """
        Solve linear equality-constrained least squares problem.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgglse(m, n, p, a, lda, b, ldb, c, d, x):
        """
        Solve linear equality-constrained least squares problem.

        """
        
        raise NotImplementedError('CULA Dense required')    
else:
    def culaDeviceDgglse(m, n, p, a, lda, b, ldb, c, d, x):
        """
        Solve linear equality-constrained least squares problem.

        """

        status = _libcula.culaDeviceDgglse(m, n, p, int(a), lda, int(b),
                                           ldb, int(c), int(d), int(x))
        culaCheckStatus(status)

    def culaDeviceZgglse(m, n, p, a, lda, b, ldb, c, d, x):
        """
        Solve linear equality-constrained least squares problem.

        """

        status = _libcula.culaDeviceZgglse(m, n, p, int(a), lda, int(b),
                                           ldb, int(c), int(d), int(x))
        culaCheckStatus(status)

# DGESVD, ZGESVD        
try:
    _libcula.culaDeviceDgesvd.restype = \
    _libcula.culaDeviceZgesvd.restype = int
    _libcula.culaDeviceDgesvd.argtypes = \
    _libcula.culaDeviceZgesvd.argtypes = [ctypes.c_char,
                                          ctypes.c_char,
                                          ctypes.c_int,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int]
except AttributeError:
    def culaDeviceDgesvd(jobu, jobvt, m, n, a, lda, s, u, ldu, vt, ldvt):
        """
        SVD decomposition.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgesvd(jobu, jobvt, m, n, a, lda, s, u, ldu, vt, ldvt):
        """
        SVD decomposition.

        """

        raise NotImplementedError('CULA Dense required')
else:
    def culaDeviceDgesvd(jobu, jobvt, m, n, a, lda, s, u, ldu, vt, ldvt):
        """
        SVD decomposition.

        """

        status = _libcula.culaDeviceDgesvd(jobu, jobvt, m, n, int(a), lda,
                                           int(s), int(u), ldu, int(vt),
                                           ldvt)
        culaCheckStatus(status)

    def culaDeviceZgesvd(jobu, jobvt, m, n, a, lda, s, u, ldu, vt, ldvt):
        """
        SVD decomposition.

        """

        status = _libcula.culaDeviceZgesvd(jobu, jobvt, m, n, int(a), lda,
                                           int(s), int(u), ldu, int(vt),
                                           ldvt)
        culaCheckStatus(status)

# SPOSV, CPOSV, DPOSV, ZPOSV        
try:
    _libcula.culaDeviceSposv.restype = \
    _libcula.culaDeviceCposv.restype = \
    _libcula.culaDeviceDposv.restype = \
    _libcula.culaDeviceZposv.restype = int
    _libcula.culaDeviceSposv.argtypes = \
    _libcula.culaDeviceCposv.argtypes = \
    _libcula.culaDeviceDposv.argtypes = \
    _libcula.culaDeviceZposv.argtypes = [ctypes.c_char,
                                         ctypes.c_int,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_int]
except AttributeError:
    def culaDeviceSposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceCposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceDposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceDposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """

        raise NotImplementedError('CULA Dense required')
else:
    def culaDeviceSposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """

        status = _libcula.culaDeviceSposv(upio, n, nrhs, int(a), lda, int(b),
                                          ldb)
        culaCheckStatus(status)

    def culaDeviceCposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """

        status = _libcula.culaDeviceCposv(upio, n, nrhs, int(a), lda, int(b),
                                          ldb)
        culaCheckStatus(status)

    def culaDeviceDposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """

        status = _libcula.culaDeviceDposv(upio, n, nrhs, int(a), lda, int(b),
                                          ldb)
        culaCheckStatus(status)

    def culaDeviceZposv(upio, n, nrhs, a, lda, b, ldb):
        """
        Solve positive definite linear system with Cholesky factorization.

        """

        status = _libcula.culaDeviceZposv(upio, n, nrhs, int(a), lda, int(b),
                                          ldb)
        culaCheckStatus(status)

# SPOTRF, CPOTRF, DPOTRF, ZPOTRF        
try:
    _libcula.culaDeviceSpotrf.restype = \
    _libcula.culaDeviceCpotrf.restype = \
    _libcula.culaDeviceDpotrf.restype = \
    _libcula.culaDeviceZpotrf.restype = int
    _libcula.culaDeviceSpotrf.argtypes = \
    _libcula.culaDeviceCpotrf.argtypes = \
    _libcula.culaDeviceDpotrf.argtypes = \
    _libcula.culaDeviceZpotrf.argtypes = [ctypes.c_char,
                                          ctypes.c_int,
                                          ctypes.c_void_p,
                                          ctypes.c_int]
except AttributeError:
    def culaDeviceSpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceCpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceDpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceZpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """
        
        raise NotImplementedError('CULA Dense required')    
else:            
    def culaDeviceSpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """

        status = _libcula.culaDeviceSpotrf(uplo, n, int(a), lda)
        culaCheckStatus(status)

    def culaDeviceCpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """

        status = _libcula.culaDeviceCpotrf(uplo, n, int(a), lda)
        culaCheckStatus(status)

    def culaDeviceDpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """

        status = _libcula.culaDeviceDpotrf(uplo, n, int(a), lda)
        culaCheckStatus(status)

    def culaDeviceZpotrf(uplo, n, a, lda):
        """
        Cholesky factorization.

        """

        status = _libcula.culaDeviceZpotrf(uplo, n, int(a), lda)
        culaCheckStatus(status)

# SSYEV, DSYEV, CHEEV, ZHEEV        
try:
    _libcula.culaDeviceSsyev.restype = \
    _libcula.culaDeviceDsyev.restype = \
    _libcula.culaDeviceCheev.restype = \
    _libcula.culaDeviceZheev.restype = int
    _libcula.culaDeviceSsyev.argtypes = \
    _libcula.culaDeviceDsyev.argtypes = \
    _libcula.culaDeviceCheev.argtypes = \
    _libcula.culaDeviceZheev.argtypes = [ctypes.c_char,
                                         ctypes.c_char,
                                         ctypes.c_int,
                                         ctypes.c_void_p,
                                         ctypes.c_int,
                                         ctypes.c_void_p]
except AttributeError:
    def culaDeviceSsyev(jobz, uplo, n, a, lda, w):
        """
        Symmetric eigenvalue decomposition.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceDsyev(jobz, uplo, n, a, lda, w):
        """
        Symmetric eigenvalue decomposition.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceCheev(jobz, uplo, n, a, lda, w):
        """
        Hermitian eigenvalue decomposition.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceZheev(jobz, uplo, n, a, lda, w):
        """
        Hermitian eigenvalue decomposition.

        """
        
        raise NotImplementedError('CULA Dense required')    
else:
    
    def culaDeviceSsyev(jobz, uplo, n, a, lda, w):
        """
        Symmetric eigenvalue decomposition.

        """

        status = _libcula.culaDeviceSsyev(jobz, uplo, n, int(a), lda, int(w))
        culaCheckStatus(status)

    def culaDeviceDsyev(jobz, uplo, n, a, lda, w):
        """
        Symmetric eigenvalue decomposition.

        """

        status = _libcula.culaDeviceDsyev(jobz, uplo, n, int(a), lda, int(w))
        culaCheckStatus(status)

    def culaDeviceCheev(jobz, uplo, n, a, lda, w):
        """
        Hermitian eigenvalue decomposition.

        """

        status = _libcula.culaDeviceCheev(jobz, uplo, n, int(a), lda, int(w))
        culaCheckStatus(status)

    def culaDeviceZheev(jobz, uplo, n, a, lda, w):
        """
        Hermitian eigenvalue decomposition.

        """

        status = _libcula.culaDeviceZheev(jobz, uplo, n, int(a), lda, int(w))
        culaCheckStatus(status)

# BLAS routines provided by CULA:

# SGEMM, DGEMM, CGEMM, ZGEMM
_libcula.culaDeviceSgemm.restype = \
_libcula.culaDeviceDgemm.restype = \
_libcula.culaDeviceCgemm.restype = \
_libcula.culaDeviceZgemm.restype = int

_libcula.culaDeviceSgemm.argtypes = [ctypes.c_char,
                                     ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_float,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_float,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

_libcula.culaDeviceDgemm.argtypes = [ctypes.c_char,
                                     ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_double,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_double,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

_libcula.culaDeviceCgemm.argtypes = [ctypes.c_char,
                                     ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     cuda.cuFloatComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     cuda.cuFloatComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

_libcula.culaDeviceZgemm.argtypes = [ctypes.c_char,
                                     ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     cuda.cuDoubleComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     cuda.cuDoubleComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

def culaDeviceSgemm(transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for general matrix.

    """
    
    status = _libcula.culaDeviceSgemm(transa, transb, m, n, k, alpha,
                           int(A), lda, int(B), ldb, beta, int(C), ldc)
    culaCheckStatus(status)

def culaDeviceDgemm(transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for general matrix.

    """
    
    status = _libcula.culaDeviceDgemm(transa, transb, m, n, k, alpha,
                           int(A), lda, int(B), ldb, beta, int(C), ldc)
    culaCheckStatus(status)

def culaDeviceCgemm(transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for complex general matrix.

    """
    
    status = _libcula.culaDeviceCgemm(transa, transb, m, n, k,
                                      cuda.cuFloatComplex(alpha.real,
                                                        alpha.imag),
                                      int(A), lda, int(B), ldb,
                                      cuda.cuFloatComplex(beta.real,
                                                        beta.imag),
                                      int(C), ldc)
    culaCheckStatus(status)

def culaDeviceZgemm(transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc):
    """
    Matrix-matrix product for complex general matrix.

    """
    
    status = _libcula.culaDeviceZgemm(transa, transb, m, n, k,
                                      cuda.cuDoubleComplex(alpha.real,
                                                        alpha.imag),
                                      int(A), lda, int(B), ldb,
                                      cuda.cuDoubleComplex(beta.real,
                                                        beta.imag),
                                      int(C), ldc)
    culaCheckStatus(status)

# SGEMV, DGEMV, CGEMV, ZGEMV
_libcula.culaDeviceSgemv.restype = \
_libcula.culaDeviceDgemv.restype = \
_libcula.culaDeviceCgemv.restype = \
_libcula.culaDeviceZgemv.restype = int

_libcula.culaDeviceSgemv.argtypes = [ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_float,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_float,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

_libcula.culaDeviceDgemv.argtypes = [ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_double,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_double,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

_libcula.culaDeviceCgemv.argtypes = [ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     cuda.cuFloatComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     cuda.cuFloatComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

_libcula.culaDeviceZgemv.argtypes = [ctypes.c_char,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     cuda.cuDoubleComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     ctypes.c_void_p,
                                     ctypes.c_int,
                                     cuda.cuDoubleComplex,
                                     ctypes.c_void_p,
                                     ctypes.c_int]

def culaDeviceSgemv(trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real general matrix.

    """
    
    status = _libcula.culaDeviceSgemv(trans, m, n, alpha, int(A), lda,
                           int(x), incx, beta, int(y), incy)
    culaCheckStatus(status)

def culaDeviceDgemv(trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for real general matrix.

    """
    
    status = _libcula.culaDeviceDgemv(trans, m, n, alpha, int(A), lda,
                           int(x), incx, beta, int(y), incy)
    culaCheckStatus(status)
    

def culaDeviceCgemv(trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for complex general matrix.

    """
    
    status = _libcula.culaDeviceCgemv(trans, m, n,
                           cuda.cuFloatComplex(alpha.real,
                                               alpha.imag),
                           int(A), lda, int(x), incx,
                           cuda.cuFloatComplex(beta.real,
                                               beta.imag),
                           int(y), incy)
    culaCheckStatus(status)

def culaDeviceZgemv(trans, m, n, alpha, A, lda, x, incx, beta, y, incy):
    """
    Matrix-vector product for complex general matrix.

    """
    
    status = _libcula.culaDeviceZgemv(trans, m, n,
                           cuda.cuDoubleComplex(alpha.real,
                                               alpha.imag),
                           int(A), lda, int(x), incx,
                           cuda.cuDoubleComplex(beta.real,
                                               beta.imag),
                           int(y), incy)
    culaCheckStatus(status)
    
# Auxiliary routines:
    
try:
    _libcula.culaDeviceSgeTranspose.restype = \
    _libcula.culaDeviceDgeTranspose.restype = \
    _libcula.culaDeviceCgeTranspose.restype = \
    _libcula.culaDeviceZgeTranspose.restype = int
    _libcula.culaDeviceSgeTranspose.argtypes = \
    _libcula.culaDeviceDgeTranspose.argtypes = \
    _libcula.culaDeviceCgeTranspose.argtypes = \
    _libcula.culaDeviceZgeTranspose.argtypes = [ctypes.c_int,
                                                ctypes.c_int,
                                                ctypes.c_void_p,
                                                ctypes.c_int,
                                                ctypes.c_void_p,
                                                ctypes.c_int]
except AttributeError:
    def culaDeviceSgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of real general matrix.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceDgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of real general matrix.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceCgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of complex general matrix.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of complex general matrix.

        """

        raise NotImplementedError('CULA Dense required')
else:
    def culaDeviceSgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of real general matrix.

        """
        
        status = _libcula.culaDeviceSgeTranspose(m, n, int(A), lda, int(B), ldb)
        culaCheckStatus(status)

    def culaDeviceDgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of real general matrix.

        """
        
        status = _libcula.culaDeviceDgeTranspose(m, n, int(A), lda, int(B), ldb)
        culaCheckStatus(status)

    def culaDeviceCgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of complex general matrix.

        """
        
        status = _libcula.culaDeviceCgeTranspose(m, n, int(A), lda, int(B), ldb)
        culaCheckStatus(status)

    def culaDeviceZgeTranspose(m, n, A, lda, B, ldb):
        """
        Transpose of complex general matrix.

        """
        
        status = _libcula.culaDeviceZgeTranspose(m, n, int(A), lda, int(B), ldb)
        culaCheckStatus(status)
    
    
try:
    _libcula.culaDeviceSgeTransposeInplace.restype = \
    _libcula.culaDeviceDgeTransposeInplace.restype = \
    _libcula.culaDeviceCgeTransposeInplace.restype = \
    _libcula.culaDeviceZgeTransposeInplace.restype = int
    _libcula.culaDeviceSgeTransposeInplace.argtypes = \
    _libcula.culaDeviceDgeTransposeInplace.argtypes = \
    _libcula.culaDeviceCgeTransposeInplace.argtypes = \
    _libcula.culaDeviceZgeTransposeInplace.argtypes = [ctypes.c_int,
                                                    ctypes.c_void_p,
                                                    ctypes.c_int]
except AttributeError:
    def culaDeviceSgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of real square matrix.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceDgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of real square matrix.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceCgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of complex square matrix.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of complex square matrix.

        """

        raise NotImplementedError('CULA Dense required')
else:
    def culaDeviceSgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of real square matrix.

        """
        
        status = _libcula.culaDeviceSgeTransposeInplace(n, int(A), lda)
        culaCheckStatus(status)

    def culaDeviceDgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of real square matrix.

        """
        
        status = _libcula.culaDeviceDgeTransposeInplace(n, int(A), lda)
        culaCheckStatus(status)

    def culaDeviceCgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of complex square matrix.

        """
        
        status = _libcula.culaDeviceCgeTransposeInplace(n, int(A), lda)
        culaCheckStatus(status)

    def culaDeviceZgeTransposeInplace(n, A, lda):
        """
        Inplace transpose of complex square matrix.

        """
        
        status = _libcula.culaDeviceZgeTransposeInplace(n, int(A), lda)
        culaCheckStatus(status)

try:

    _libcula.culaDeviceCgeTransposeConjugate.restype = \
    _libcula.culaDeviceZgeTransposeConjugate.restype = int
    _libcula.culaDeviceCgeTransposeConjugate.argtypes = \
    _libcula.culaDeviceZgeTransposeConjugate.argtypes = [ctypes.c_int,
                                                        ctypes.c_int,
                                                        ctypes.c_void_p,
                                                        ctypes.c_int,
                                                        ctypes.c_void_p,
                                                        ctypes.c_int]
except AttributeError:
    def culaDeviceCgeTransposeConjugate(m, n, A, lda, B, ldb):
        """
        Conjugate transpose of complex general matrix.

        """
        
        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgeTransposeConjugate(m, n, A, lda, B, ldb):
        """
        Conjugate transpose of complex general matrix.

        """
        raise NotImplementedError('CULA Dense required')    
else:
    def culaDeviceCgeTransposeConjugate(m, n, A, lda, B, ldb):
        """
        Conjugate transpose of complex general matrix.

        """
        
        status = _libcula.culaDeviceCgeTransposeConjugate(m, n, int(A), lda, int(B), ldb)
        culaCheckStatus(status)

    def culaDeviceZgeTransposeConjugate(m, n, A, lda, B, ldb):
        """
        Conjugate transpose of complex general matrix.

        """
        
        status = _libcula.culaDeviceZgeTransposeConjugate(m, n, int(A), lda, int(B), ldb)
        culaCheckStatus(status)

try:
    _libcula.culaDeviceCgeTransposeConjugateInplace.restype = \
    _libcula.culaDeviceZgeTransposeConjugateInplace.restype = int
    _libcula.culaDeviceCgeTransposeConjugateInplace.argtypes = \
    _libcula.culaDeviceZgeTransposeConjugateInplace.argtypes = [ctypes.c_int,
                                                                ctypes.c_void_p,
                                                                ctypes.c_int]
except AttributeError:
    def culaDeviceCgeTransposeConjugateInplace(n, A, lda):
        """
        Inplace conjugate transpose of complex square matrix.

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgeTransposeConjugateInplace(n, A, lda):
        """
        Inplace conjugate transpose of complex square matrix.

        """
        
        raise NotImplementedError('CULA Dense required')    
else:
    def culaDeviceCgeTransposeConjugateInplace(n, A, lda):
        """
        Inplace conjugate transpose of complex square matrix.

        """
        
        status = _libcula.culaDeviceCgeTransposeConjugateInplace(n, int(A), lda)
        culaCheckStatus(status)

    def culaDeviceZgeTransposeConjugateInplace(n, A, lda):
        """
        Inplace conjugate transpose of complex square matrix.

        """
        
        status = _libcula.culaDeviceZgeTransposeConjugateInplace(n, int(A), lda)
        culaCheckStatus(status)

try:
    _libcula.culaDeviceCgeConjugate.restype = \
    _libcula.culaDeviceZgeConjugate.restype = int
    _libcula.culaDeviceCgeConjugate.argtypes = \
    _libcula.culaDeviceZgeConjugate.argtypes = [ctypes.c_int,
                                                ctypes.c_int,
                                                ctypes.c_void_p,
                                                ctypes.c_int]
except AttributeError:
    def culaDeviceCgeConjugate(m, n, A, lda):
        """
        Conjugate of complex general matrix.

        """
    
        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgeConjugate(m, n, A, lda):
        """
        Conjugate of complex general matrix.

        """

        raise NotImplementedError('CULA Dense required')
else:
    def culaDeviceCgeConjugate(m, n, A, lda):
        """
        Conjugate of complex general matrix.

        """
        
        status = _libcula.culaDeviceCgeConjugate(m, n, int(A), lda)
        culaCheckStatus(status)

    def culaDeviceZgeConjugate(m, n, A, lda):
        """
        Conjugate of complex general matrix.

        """
        
        status = _libcula.culaDeviceZgeConjugate(m, n, int(A), lda)
        culaCheckStatus(status)

try:
    _libcula.culaDeviceCtrConjugate.restype = \
    _libcula.culaDeviceZtrConjugate.restype = int
    _libcula.culaDeviceCtrConjugate.argtypes = \
    _libcula.culaDeviceZtrConjugate.argtypes = [ctypes.c_char,
                                                ctypes.c_char,
                                                ctypes.c_int,
                                                ctypes.c_int,
                                                ctypes.c_void_p,
                                                ctypes.c_int]
except AttributeError:
    def culaDeviceCtrConjugate(uplo, diag, m, n, A, lda):
        """
        Conjugate of complex upper or lower triangle matrix.

        """
    
        raise NotImplementedError('CULA Dense required')

    def culaDeviceZtrConjugate(uplo, diag, m, n, A, lda):
        """
        Conjugate of complex upper or lower triangle matrix.

        """
        
        raise NotImplementedError('CULA Dense required')    
else:
    def culaDeviceCtrConjugate(uplo, diag, m, n, A, lda):
        """
        Conjugate of complex upper or lower triangle matrix.

        """
        
        status = _libcula.culaDeviceCtrConjugate(uplo, diag, m, n, int(A), lda)
        culaCheckStatus(status)

    def culaDeviceZtrConjugate(uplo, diag, m, n, A, lda):
        """
        Conjugate of complex upper or lower triangle matrix.

        """
        
        status = _libcula.culaDeviceZtrConjugate(uplo, diag, m, n, int(A), lda)
        culaCheckStatus(status)

try:
    _libcula.culaDeviceSgeNancheck.restype = \
    _libcula.culaDeviceDgeNancheck.restype = \
    _libcula.culaDeviceCgeNancheck.restype = \
    _libcula.culaDeviceZgeNancheck.restype = int
    _libcula.culaDeviceSgeNancheck.argtypes = \
    _libcula.culaDeviceDgeNancheck.argtypes = \
    _libcula.culaDeviceCgeNancheck.argtypes = \
    _libcula.culaDeviceZgeNancheck.argtypes = [ctypes.c_int,
                                                ctypes.c_int,
                                                ctypes.c_void_p,
                                                ctypes.c_int]
except AttributeError:
    def culaDeviceSgeNancheck(m, n, A, lda):
        """
        Check a real general matrix for invalid entries

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceDgeNancheck(m, n, A, lda):
        """
        Check a real general matrix for invalid entries

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceCgeNancheck(m, n, A, lda):
        """
        Check a complex general matrix for invalid entries

        """

        raise NotImplementedError('CULA Dense required')

    def culaDeviceZgeNancheck(m, n, A, lda):
        """
        Check a complex general matrix for invalid entries

        """

        raise NotImplementedError('CULA Dense required')        
else:
    def culaDeviceSgeNancheck(m, n, A, lda):
        """
        Check a real general matrix for invalid entries

        """
        
        status = _libcula.culaDeviceSgeNancheck(m, n, int(A), lda)
        try:
            culaCheckStatus(status)
        except culaDataError:
            return True
        return False

    def culaDeviceDgeNancheck(m, n, A, lda):
        """
        Check a real general matrix for invalid entries

        """
        
        status = _libcula.culaDeviceDgeNancheck(m, n, int(A), lda)
        try:
            culaCheckStatus(status)
        except culaDataError:
            return True
        return False

    def culaDeviceCgeNancheck(m, n, A, lda):
        """
        Check a complex general matrix for invalid entries

        """
        
        status = _libcula.culaDeviceCgeNancheck(m, n, int(A), lda)
        try:
            culaCheckStatus(status)
        except culaDataError:
            return True
        return False

    def culaDeviceZgeNancheck(m, n, A, lda):
        """
        Check a complex general matrix for invalid entries

        """
        
        status = _libcula.culaDeviceZgeNancheck(m, n, int(A), lda)
        try:
            culaCheckStatus(status)
        except culaDataError:
            return True
        return False

        
if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = cusparse
#!/usr/bin/env python

"""
Python interface to CUSPARSE functions.

Note: this module does not explicitly depend on PyCUDA.
"""

import sys
import warnings
import ctypes
import ctypes.util
import atexit
import numpy as np

from string import Template

import cuda

if sys.platform == 'linux2':
    _libcusparse_libname_list = ['libcusparse.so', 'libcusparse.so.3',
                                 'libcusparse.so.4', 'libcusparse.so.5']
elif sys.platform == 'darwin':
    _libcusparse_libname_list = ['libcusparse.dylib']
elif sys.platform == 'Windows':
    _libcusparse_libname_list = ['cusparse.lib']
else:
    raise RuntimeError('unsupported platform')

# Print understandable error message when library cannot be found:
_libcusparse = None
for _libcusparse_libname in _libcusparse_libname_list:
    try:
        _libcusparse = ctypes.cdll.LoadLibrary(_libcusparse_libname)
    except OSError:
        pass
    else:
        break
if _libcusparse == None:
    OSError('CUDA sparse library not found')

class cusparseError(Exception):
    """CUSPARSE error"""
    pass

class cusparseStatusNotInitialized(cusparseError):
    """CUSPARSE library not initialized"""
    pass

class cusparseStatusAllocFailed(cusparseError):
    """CUSPARSE resource allocation failed"""
    pass

class cusparseStatusInvalidValue(cusparseError):
    """Unsupported value passed to the function"""
    pass

class cusparseStatusArchMismatch(cusparseError):
    """Function requires a feature absent from the device architecture"""
    pass

class cusparseStatusMappingError(cusparseError):
    """An access to GPU memory space failed"""
    pass

class cusparseStatusExecutionFailed(cusparseError):
    """GPU program failed to execute"""
    pass

class cusparseStatusInternalError(cusparseError):
    """An internal CUSPARSE operation failed"""
    pass

class cusparseStatusMatrixTypeNotSupported(cusparseError):
    """The matrix type is not supported by this function"""
    pass

cusparseExceptions = {
    1: cusparseStatusNotInitialized,
    2: cusparseStatusAllocFailed,
    3: cusparseStatusInvalidValue,
    4: cusparseStatusArchMismatch,
    5: cusparseStatusMappingError,
    6: cusparseStatusExecutionFailed,
    7: cusparseStatusInternalError,
    8: cusparseStatusMatrixTypeNotSupported,
    }

# Matrix types:
CUSPARSE_MATRIX_TYPE_GENERAL = 0
CUSPARSE_MATRIX_TYPE_SYMMETRIC = 1
CUSPARSE_MATRIX_TYPE_HERMITIAN = 2
CUSPARSE_MATRIX_TYPE_TRIANGULAR = 3

CUSPARSE_FILL_MODE_LOWER = 0
CUSPARSE_FILL_MODE_UPPER = 1

# Whether or not a matrix' diagonal entries are unity:
CUSPARSE_DIAG_TYPE_NON_UNIT = 0
CUSPARSE_DIAG_TYPE_UNIT = 1

# Matrix index bases:
CUSPARSE_INDEX_BASE_ZERO = 0
CUSPARSE_INDEX_BASE_ONE = 1

# Operation types:
CUSPARSE_OPERATION_NON_TRANSPOSE = 0
CUSPARSE_OPERATION_TRANSPOSE = 1
CUSPARSE_OPERATION_CONJUGATE_TRANSPOSE = 2

# Whether or not to parse elements of a dense matrix row or column-wise.
CUSPARSE_DIRECTION_ROW = 0
CUSPARSE_DIRECTION_COLUMN = 1

# Helper functions:
class cusparseMatDescr(ctypes.Structure):
    _fields_ = [
        ('MatrixType', ctypes.c_int),
        ('FillMode', ctypes.c_int),
        ('DiagType', ctypes.c_int),
        ('IndexBase', ctypes.c_int)
        ]

def cusparseCheckStatus(status):
    """
    Raise CUSPARSE exception

    Raise an exception corresponding to the specified CUSPARSE error
    code.

    Parameters
    ----------
    status : int
        CUSPARSE error code.

    See Also
    --------
    cusparseExceptions

    """

    if status != 0:
        try:
            raise cusparseExceptions[status]
        except KeyError:
            raise cusparseError

_libcusparse.cusparseCreate.restype = int
_libcusparse.cusparseCreate.argtypes = [ctypes.c_void_p]
def cusparseCreate():
    """
    Initialize CUSPARSE.

    Initializes CUSPARSE and creates a handle to a structure holding
    the CUSPARSE library context.

    Returns
    -------
    handle : int
        CUSPARSE library context.

    """

    handle = ctypes.c_int()
    status = _libcusparse.cusparseCreate(ctypes.byref(handle))
    cusparseCheckStatus(status)
    return handle.value

_libcusparse.cusparseDestroy.restype = int
_libcusparse.cusparseDestroy.argtypes = [ctypes.c_int]
def cusparseDestroy(handle):
    """
    Release CUSPARSE resources.

    Releases hardware resources used by CUSPARSE

    Parameters
    ----------
    handle : int
        CUSPARSE library context.

    """

    status = _libcusparse.cusparseDestroy(handle)
    cusparseCheckStatus(status)

_libcusparse.cusparseGetVersion.restype = int
_libcusparse.cusparseGetVersion.argtypes = [ctypes.c_int,
                                            ctypes.c_void_p]
def cusparseGetVersion(handle):
    """
    Return CUSPARSE library version.

    Returns the version number of the CUSPARSE library.

    Parameters
    ----------
    handle : int
        CUSPARSE library context.

    Returns
    -------
    version : int
        CUSPARSE library version number.

    """

    version = ctypes.c_int()
    status = _libcusparse.cusparseGetVersion(handle,
                                             ctypes.byref(version))
    cusparseCheckStatus(status)
    return version.value

_libcusparse.cusparseSetStream.restype = int
_libcusparse.cusparseSetStream.argtypes = [ctypes.c_int,
                                                 ctypes.c_int]
def cusparseSetStream(handle, id):
    """
    Sets the CUSPARSE stream in which kernels will run.

    Parameters
    ----------
    handle : int
        CUSPARSE library context.
    id : int
        Stream ID.

    """

    status = _libcusparse.cusparseSetStream(handle, id)
    cusparseCheckStatus(status)

_libcusparse.cusparseCreateMatDescr.restype = int
_libcusparse.cusparseCreateMatDescr.argtypes = [cusparseMatDescr]
def cusparseCreateMatDescr():
    """
    Initialize a sparse matrix descriptor.

    Initializes the `MatrixType` and `IndexBase` fields of the matrix
    descriptor to the default values `CUSPARSE_MATRIX_TYPE_GENERAL`
    and `CUSPARSE_INDEX_BASE_ZERO`.

    Returns
    -------
    desc : cusparseMatDescr
        Matrix descriptor.

    """

    desc = cusparseMatrixDesc()
    status = _libcusparse.cusparseCreateMatDescr(ctypes.byref(desc))
    cusparseCheckStatus(status)
    return desc

_libcusparse.cusparseDestroyMatDescr.restype = int
_libcusparse.cusparseDestroyMatDescr.argtypes = [ctypes.c_int]
def cusparseDestroyMatDescr(desc):
    """
    Releases the memory allocated for the matrix descriptor.

    Parameters
    ----------
    desc : cusparseMatDescr
        Matrix descriptor.

    """

    status = _libcusparse.cusparseDestroyMatDescr(desc)
    cusparseCheckStatus(status)

_libcusparse.cusparseSetMatType.restype = int
_libcusparse.cusparseSetMatType.argtypes = [cusparseMatDescr,
                                            ctypes.c_int]
def cusparseSetMatType(desc, type):
    """
    Sets the matrix type of the specified matrix.

    Parameters
    ----------
    desc : cusparseMatDescr
        Matrix descriptor.
    type : int
        Matrix type.

    """

    status = _libcusparse.cusparseSetMatType(desc, type)
    cusparseCheckStatus(status)

_libcusparse.cusparseGetMatType.restype = int
_libcusparse.cusparseGetMatType.argtypes = [cusparseMatDescr]                                 
def cusparseGetMatType(desc):
    """
    Gets the matrix type of the specified matrix.

    Parameters
    ----------
    desc : cusparseMatDescr
        Matrix descriptor.

    Returns
    -------
    type : int
        Matrix type.

    """

    return _libcusparse.cusparseGetMatType(desc)

# Format conversion functions:
_libcusparse.cusparseSnnz.restype = int
_libcusparse.cusparseSnnz.argtypes = [ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      ctypes.c_int,
                                      cusparseMatDescr,
                                      ctypes.c_void_p,
                                      ctypes.c_int,
                                      ctypes.c_void_p,
                                      ctypes.c_void_p]
def cusparseSnnz(handle, dirA, m, n, descrA, A, lda, 
                 nnzPerRowColumn, nnzTotalDevHostPtr):
    """
    Compute number of non-zero elements per row, column, or dense matrix.

    Parameters
    ----------
    handle : int
        CUSPARSE library context.
    dirA : int
        Data direction of elements.
    m : int
        Rows in A.
    n : int
        Columns in A.
    descrA : cusparseMatDescr
        Matrix descriptor.
    A : pycuda.gpuarray.GPUArray
        Dense matrix of dimensions (lda, n).
    lda : int
        Leading dimension of A.
    
    Returns
    -------
    nnzPerRowColumn : pycuda.gpuarray.GPUArray
        Array of length m or n containing the number of 
        non-zero elements per row or column, respectively.
    nnzTotalDevHostPtr : pycuda.gpuarray.GPUArray
        Total number of non-zero elements in device or host memory.

    """

    # Unfinished:
    nnzPerRowColumn = gpuarray.empty()
    nnzTotalDevHostPtr = gpuarray.empty()

    status = _libcusparse.cusparseSnnz(handle, dirA, m, n, 
                                       descrA, int(A), lda,
                                       int(nnzPerRowColumn), int(nnzTotalDevHostPtr))
    cusparseCheckStatus(status)
    return nnzPerVector, nnzHost

_libcusparse.cusparseSdense2csr.restype = int
_libcusparse.cusparseSdense2csr.argtypes = [ctypes.c_int,
                                            ctypes.c_int,
                                            ctypes.c_int,
                                            cusparseMatDescr,
                                            ctypes.c_void_p,
                                            ctypes.c_int,
                                            ctypes.c_void_p,
                                            ctypes.c_void_p,
                                            ctypes.c_void_p,
                                            ctypes.c_void_p]
def cusparseSdense2csr(handle, m, n, descrA, A, lda, 
                       nnzPerRow, csrValA, csrRowPtrA, csrColIndA):
    # Unfinished
    pass

########NEW FILE########
__FILENAME__ = fft
#!/usr/bin/env python

"""
PyCUDA-based FFT functions.
"""

import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
import pycuda.elementwise as el
import pycuda.tools as tools
import numpy as np

import cufft
from cufft import CUFFT_COMPATIBILITY_NATIVE, \
     CUFFT_COMPATIBILITY_FFTW_PADDING, \
     CUFFT_COMPATIBILITY_FFTW_ASYMMETRIC, \
     CUFFT_COMPATIBILITY_FFTW_ALL

import misc

class Plan:
    """
    CUFFT plan class.

    This class represents an FFT plan for CUFFT.

    Parameters
    ----------
    shape : tuple of ints
        Transform shape. May contain more than 3 elements.
    in_dtype : { numpy.float32, numpy.float64, numpy.complex64, numpy.complex128 }
        Type of input data.
    out_dtype : { numpy.float32, numpy.float64, numpy.complex64, numpy.complex128 }
        Type of output data.
    batch : int
        Number of FFTs to configure in parallel (default is 1).
    stream : pycuda.driver.Stream
        Stream with which to associate the plan. If no stream is specified,
        the default stream is used.
    mode : int
        FFTW compatibility mode.

    """

    def __init__(self, shape, in_dtype, out_dtype, batch=1, stream=None,
                 mode=0x01):

        if np.isscalar(shape):
            self.shape = (shape, )
        else:
            self.shape = shape

        self.in_dtype = in_dtype
        self.out_dtype = out_dtype

        if batch <= 0:
            raise ValueError('batch size must be greater than 0')
        self.batch = batch

        # Determine type of transformation:
        if in_dtype == np.float32 and out_dtype == np.complex64:
            self.fft_type = cufft.CUFFT_R2C
            self.fft_func = cufft.cufftExecR2C
        elif in_dtype == np.complex64 and out_dtype == np.float32:
            self.fft_type = cufft.CUFFT_C2R
            self.fft_func = cufft.cufftExecC2R
        elif in_dtype == np.complex64 and out_dtype == np.complex64:
            self.fft_type = cufft.CUFFT_C2C
            self.fft_func = cufft.cufftExecC2C
        elif in_dtype == np.float64 and out_dtype == np.complex128:
            self.fft_type = cufft.CUFFT_D2Z
            self.fft_func = cufft.cufftExecD2Z
        elif in_dtype == np.complex128 and out_dtype == np.float64:
            self.fft_type = cufft.CUFFT_Z2D
            self.fft_func = cufft.cufftExecZ2D
        elif in_dtype == np.complex128 and out_dtype == np.complex128:
            self.fft_type = cufft.CUFFT_Z2Z
            self.fft_func = cufft.cufftExecZ2Z
        else:
            raise ValueError('unsupported input/output type combination')

        # Check for double precision support:
        capability = misc.get_compute_capability(misc.get_current_device())
        if capability < 1.3 and \
           (misc.isdoubletype(in_dtype) or misc.isdoubletype(out_dtype)):
            raise RuntimeError('double precision requires compute capability '
                               '>= 1.3 (you have %g)' % capability)

        # Set up plan:
        if len(self.shape) > 0:
            n = np.asarray(self.shape, np.int32)
            self.handle = cufft.cufftPlanMany(len(self.shape), n.ctypes.data,
                                              None, 1, 0, None, 1, 0,
                                              self.fft_type, self.batch)
        else:
            raise ValueError('invalid transform size')

        # Set FFTW compatibility mode:
        cufft.cufftSetCompatibilityMode(self.handle, mode)

        # Associate stream with plan:
        if stream != None:
            cufft.cufftSetStream(self.handle, stream.handle)

    def __del__(self):

        # Don't complain if handle destruction fails because the plan
        # may have already been cleaned up:
        try:
            cufft.cufftDestroy(self.handle)
        except:
            pass

def _scale_inplace(a, x_gpu):
    """
    Scale an array by a specified value in-place.
    """

    # Cache the kernel to avoid invoking the compiler if the
    # specified scale factor and array type have already been encountered:
    try:
        func = _scale_inplace.cache[(a, x_gpu.dtype)]
    except KeyError:
        ctype = tools.dtype_to_ctype(x_gpu.dtype)
        func = el.ElementwiseKernel(
            "{ctype} a, {ctype} *x".format(ctype=ctype),
            "x[i] /= a")
        _scale_inplace.cache[(a, x_gpu.dtype)] = func
    func(x_gpu.dtype.type(a), x_gpu)
_scale_inplace.cache = {}

def _fft(x_gpu, y_gpu, plan, direction, scale=None):
    """
    Fast Fourier Transform.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.
    y_gpu : pycuda.gpuarray.GPUArray
        Output array.
    plan : Plan
        FFT plan.
    direction : { cufft.CUFFT_FORWARD, cufft.CUFFT_INVERSE }
        Transform direction. Only affects in-place transforms.

    Optional Parameters
    -------------------
    scale : int or float
        Scale the values in the output array by dividing them by this value.

    Notes
    -----
    This function should not be called directly.

    """

    if (x_gpu.gpudata == y_gpu.gpudata) and \
           plan.fft_type not in [cufft.CUFFT_C2C, cufft.CUFFT_Z2Z]:
        raise ValueError('can only compute in-place transform of complex data')

    if direction == cufft.CUFFT_FORWARD and \
           plan.in_dtype in np.sctypes['complex'] and \
           plan.out_dtype in np.sctypes['float']:
        raise ValueError('cannot compute forward complex -> real transform')

    if direction == cufft.CUFFT_INVERSE and \
           plan.in_dtype in np.sctypes['float'] and \
           plan.out_dtype in np.sctypes['complex']:
        raise ValueError('cannot compute inverse real -> complex transform')

    if plan.fft_type in [cufft.CUFFT_C2C, cufft.CUFFT_Z2Z]:
        plan.fft_func(plan.handle, int(x_gpu.gpudata), int(y_gpu.gpudata),
                      direction)
    else:
        plan.fft_func(plan.handle, int(x_gpu.gpudata),
                      int(y_gpu.gpudata))

    # Scale the result by dividing it by the number of elements:
    if scale != None:
        _scale_inplace(scale, y_gpu)

def fft(x_gpu, y_gpu, plan, scale=False):
    """
    Fast Fourier Transform.

    Compute the FFT of some data in device memory using the
    specified plan.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.
    y_gpu : pycuda.gpuarray.GPUArray
        FFT of input array.
    plan : Plan
        FFT plan.
    scale : bool, optional
        If True, scale the computed FFT by the number of elements in
        the input array.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> N = 128
    >>> x = np.asarray(np.random.rand(N), np.float32)
    >>> xf = np.fft.fft(x)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> xf_gpu = gpuarray.empty(N/2+1, np.complex64)
    >>> plan = Plan(x.shape, np.float32, np.complex64)
    >>> fft(x_gpu, xf_gpu, plan)
    >>> np.allclose(xf[0:N/2+1], xf_gpu.get(), atol=1e-6)
    True

    Returns
    -------
    y_gpu : pycuda.gpuarray.GPUArray
        Computed FFT.

    Notes
    -----
    For real to complex transformations, this function computes
    N/2+1 non-redundant coefficients of a length-N input signal.

    """

    if scale == True:
        return _fft(x_gpu, y_gpu, plan, cufft.CUFFT_FORWARD, x_gpu.size/plan.batch)
    else:
        return _fft(x_gpu, y_gpu, plan, cufft.CUFFT_FORWARD)

def ifft(x_gpu, y_gpu, plan, scale=False):
    """
    Inverse Fast Fourier Transform.

    Compute the inverse FFT of some data in device memory using the
    specified plan.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.
    y_gpu : pycuda.gpuarray.GPUArray
        Inverse FFT of input array.
    plan : Plan
        FFT plan.
    scale : bool, optional
        If True, scale the computed inverse FFT by the number of
        elements in the output array.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> N = 128
    >>> x = np.asarray(np.random.rand(N), np.float32)
    >>> xf = np.asarray(np.fft.fft(x), np.complex64)
    >>> xf_gpu = gpuarray.to_gpu(xf[0:N/2+1])
    >>> x_gpu = gpuarray.empty(N, np.float32)
    >>> plan = Plan(N, np.complex64, np.float32)
    >>> ifft(xf_gpu, x_gpu, plan, True)
    >>> np.allclose(x, x_gpu.get(), atol=1e-6)
    True

    Notes
    -----
    For complex to real transformations, this function assumes the
    input contains N/2+1 non-redundant FFT coefficents of a signal of
    length N.

    """

    if scale == True:
        return _fft(x_gpu, y_gpu, plan, cufft.CUFFT_INVERSE, y_gpu.size/plan.batch)
    else:
        return _fft(x_gpu, y_gpu, plan, cufft.CUFFT_INVERSE)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = info
#!/usr/bin/env python

"""
scikits.cuda
============

This SciKit (toolkit for SciPy [1]_) provides Python interfaces to a
subset of the functions in the CUDA, CUDART, CUBLAS, and CUFFT
libraries distributed as part of NVIDIA's CUDA Programming Toolkit
[2]_, as well as interfaces to select functions in the free-of-charge
CULA Toolkit [3]_. In contrast to most existing Python wrappers for
these libraries (many of which only provide a low-level interface to
the actual library functions), this package uses PyCUDA [4]_ to
provide high-level functions comparable to those in the NumPy package
[5]_.


High-level modules
------------------

- autoinit       Import this module to automatically initialize CUBLAS and CULA.
- fft            Fast Fourier Transform functions.
- integrate      Numerical integration functions.
- linalg         Linear algebra functions.
- misc           Miscellaneous support functions.
- special        Special math functions.

Low-level modules
-----------------

- cublas         Wrappers for functions in the CUBLAS library.
- cufft          Wrappers for functions in the CUFFT library.
- cuda           Wrappers for functions in the CUDA/CUDART libraries.
- cula           Wrappers for functions in the CULA library.
- pcula          Wrappers for functions in the multi-GPU CULA library.

.. [1] http://www.scipy.org/
.. [2] http://www.nvidia.com/cuda
.. [3] http://www.culatools.com/
.. [4] http://mathema.tician.de/software/pycuda/
.. [5] http://numpy.scipy.org/
.. [6] http://bionet.ee.columbia.edu/
.. [7] http://www.mathcs.emory.edu/~yfan/PARRET

"""

########NEW FILE########
__FILENAME__ = integrate
#!/usr/bin/env python

"""
PyCUDA-based integration functions.
"""

from string import Template
from pycuda.compiler import SourceModule
import pycuda.gpuarray as gpuarray
import numpy as np

import ctypes
import cublas
import misc

from misc import init

gen_trapz_mult_template = Template("""
#include <pycuda-complex.hpp>

#if ${use_double}
#if ${use_complex}
#define TYPE pycuda::complex<double>
#else
#define TYPE double
#endif
#else
#if ${use_complex}
#define TYPE pycuda::complex<float>
#else
#define TYPE float
#endif
#endif

__global__ void gen_trapz_mult(TYPE *mult, unsigned int N) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;

    if (idx < N) {
        if ((idx == 0) || (idx == N-1)) {                      
            mult[idx] = TYPE(0.5);
        } else {
            mult[idx] = TYPE(1.0);
        }
    }
}
""")

def gen_trapz_mult(N, mult_type):
    """
    Generate multiplication array for 1D trapezoidal integration.

    Generates an array whose dot product with some array of equal
    length is equivalent to the definite integral of the latter
    computed using trapezoidal integration.

    Parameters
    ----------
    N : int
        Length of array.
    mult_type : float type
        Floating point type to use when generating the array.

    Returns
    -------
    result : pycuda.gpuarray.GPUArray
        Generated array.

    """
    
    if mult_type not in [np.float32, np.float64, np.complex64,
                         np.complex128]:
        raise ValueError('unrecognized type')
    
    use_double = int(mult_type in [np.float64, np.complex128])
    use_complex = int(mult_type in [np.complex64, np.complex128])

    # Allocate output matrix:
    mult_gpu = gpuarray.empty(N, mult_type)

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, N)

    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    gen_trapz_mult_mod = \
                       SourceModule(gen_trapz_mult_template.substitute(use_double=use_double,
                                                                       use_complex=use_complex),
                                    cache_dir=cache_dir)

    gen_trapz_mult = gen_trapz_mult_mod.get_function("gen_trapz_mult")    
    gen_trapz_mult(mult_gpu, np.uint32(N),
                   block=block_dim,
                   grid=grid_dim)
    
    return mult_gpu

def trapz(x_gpu, dx=1.0, handle=None):
    """
    1D trapezoidal integration.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array to integrate.
    dx : scalar
        Spacing.
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.misc._global_cublas_handle` is used.

    Returns
    -------
    result : float
        Definite integral as approximated by the trapezoidal rule.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray
    >>> import numpy as np
    >>> import integrate
    >>> integrate.init()
    >>> x = np.asarray(np.random.rand(10), np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> z = integrate.trapz(x_gpu)
    >>> np.allclose(np.trapz(x), z)
    True
    
    """

    if handle is None:
        handle = misc._global_cublas_handle
        
    if len(x_gpu.shape) > 1:
        raise ValueError('input array must be 1D')
    if np.iscomplex(dx):
        raise ValueError('dx must be real')

    float_type = x_gpu.dtype.type
    if float_type == np.complex64:
        cublas_func = cublas.cublasCdotu        
    elif float_type == np.float32:
        cublas_func = cublas.cublasSdot
    elif float_type == np.complex128:
        cublas_func = cublas.cublasZdotu
    elif float_type == np.float64:
        cublas_func = cublas.cublasDdot
    else:
        raise ValueError('unsupported input type')

    trapz_mult_gpu = gen_trapz_mult(x_gpu.size, float_type)
    result = cublas_func(handle, x_gpu.size, x_gpu.gpudata, 1,
                         trapz_mult_gpu.gpudata, 1)

    return float_type(dx)*result

gen_trapz2d_mult_template = Template("""
#include <pycuda-complex.hpp>

#if ${use_double}
#if ${use_complex}
#define TYPE pycuda::complex<double>
#else
#define TYPE double
#endif
#else
#if ${use_complex}
#define TYPE pycuda::complex<float>
#else
#define TYPE float
#endif
#endif

// Ny: number of rows
// Nx: number of columns
__global__ void gen_trapz2d_mult(TYPE *mult,
                                 unsigned int Ny, unsigned int Nx) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;

    if (idx < Nx*Ny) {
        if (idx == 0 || idx == Nx-1 || idx == Nx*(Ny-1) || idx == Nx*Ny-1)
            mult[idx] = TYPE(0.25);
        else if ((idx > 0 && idx < Nx-1) || (idx % Nx == 0) ||
                (((idx + 1) % Nx) == 0) || (idx > Nx*(Ny-1) && idx < Nx*Ny-1))
            mult[idx] = TYPE(0.5);
        else 
            mult[idx] = TYPE(1.0);
    }
}
""")

def gen_trapz2d_mult(mat_shape, mult_type):
    """
    Generate multiplication matrix for 2D trapezoidal integration.

    Generates a matrix whose dot product with some other matrix of
    equal length (when flattened) is equivalent to the definite double
    integral of the latter computed using trapezoidal integration.

    Parameters
    ----------
    mat_shape : tuple
        Shape of matrix.
    mult_type : float type
        Floating point type to use when generating the array.

    Returns
    -------
    result : pycuda.gpuarray.GPUArray
        Generated matrix.

    """

    if mult_type not in [np.float32, np.float64, np.complex64,
                         np.complex128]:
        raise ValueError('unrecognized type')
    
    use_double = int(mult_type in [np.float64, np.complex128])
    use_complex = int(mult_type in [np.complex64, np.complex128])

    # Allocate output matrix:
    Ny, Nx = mat_shape
    mult_gpu = gpuarray.empty(mat_shape, mult_type)

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, mat_shape)
    
    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    gen_trapz2d_mult_mod = \
                         SourceModule(gen_trapz2d_mult_template.substitute(use_double=use_double,
                                                                           use_complex=use_complex),
                                      cache_dir=cache_dir)

    gen_trapz2d_mult = gen_trapz2d_mult_mod.get_function("gen_trapz2d_mult")    
    gen_trapz2d_mult(mult_gpu, np.uint32(Ny), np.uint32(Nx),
                     block=block_dim,
                     grid=grid_dim)
    
    return mult_gpu

def trapz2d(x_gpu, dx=1.0, dy=1.0, handle=None):
    """
    2D trapezoidal integration.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input matrix to integrate.
    dx : float
        X-axis spacing.
    dy : float
        Y-axis spacing
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.misc._global_cublas_handle` is used.
        
    Returns
    -------
    result : float
        Definite double integral as approximated by the trapezoidal rule.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray
    >>> import numpy as np
    >>> import integrate
    >>> integrate.init()
    >>> x = np.asarray(np.random.rand(10, 10), np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> z = integrate.trapz2d(x_gpu)
    >>> np.allclose(np.trapz(np.trapz(x)), z)
    True

    """

    if handle is None:
        handle = misc._global_cublas_handle
        
    if len(x_gpu.shape) != 2:
        raise ValueError('input array must be 2D')
    if np.iscomplex(dx) or np.iscomplex(dy):
        raise ValueError('dx and dy must be real')

    float_type = x_gpu.dtype.type
    if float_type == np.complex64:
        cublas_func = cublas.cublasCdotu        
    elif float_type == np.float32:
        cublas_func = cublas.cublasSdot
    elif float_type == np.complex128:
        cublas_func = cublas.cublasZdotu
    elif float_type == np.float64:
        cublas_func = cublas.cublasDdot
    else:
        raise ValueError('unsupported input type')
                                            
    trapz_mult_gpu = gen_trapz2d_mult(x_gpu.shape, float_type)
    result = cublas_func(handle, x_gpu.size, x_gpu.gpudata, 1,
                         trapz_mult_gpu.gpudata, 1)

    return float_type(dx)*float_type(dy)*result

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = linalg
#!/usr/bin/env python

"""
PyCUDA-based linear algebra functions.
"""

from pprint import pprint
from string import Template, lower, upper
from pycuda.compiler import SourceModule
import pycuda.gpuarray as gpuarray
import pycuda.driver as drv
import pycuda.elementwise as el
import pycuda.tools as tools
import numpy as np

import cuda
import cublas
import misc

try:
    import cula
    _has_cula = True
except (ImportError, OSError):
    _has_cula = False

from misc import init

# Get installation location of C headers:
from . import install_headers

def svd(a_gpu, jobu='A', jobvt='A'):
    """
    Singular Value Decomposition.

    Factors the matrix `a` into two unitary matrices, `u` and `vh`,
    and a 1-dimensional array of real, non-negative singular values,
    `s`, such that `a == dot(u.T, dot(diag(s), vh.T))`.

    Parameters
    ----------
    a : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, n)` to decompose.
    jobu : {'A', 'S', 'O', 'N'}
        If 'A', return the full `u` matrix with shape `(m, m)`.
        If 'S', return the `u` matrix with shape `(m, k)`.
        If 'O', return the `u` matrix with shape `(m, k) without
        allocating a new matrix.
        If 'N', don't return `u`.
    jobvt : {'A', 'S', 'O', 'N'}
        If 'A', return the full `vh` matrix with shape `(n, n)`.
        If 'S', return the `vh` matrix with shape `(k, n)`.
        If 'O', return the `vh` matrix with shape `(k, n) without
        allocating a new matrix.
        If 'N', don't return `vh`.

    Returns
    -------
    u : pycuda.gpuarray.GPUArray
        Unitary matrix of shape `(m, m)` or `(m, k)` depending on
        value of `jobu`.
    s : pycuda.gpuarray.GPUArray
        Array containing the singular values, sorted such that `s[i] >= s[i+1]`.
        `s` is of length `min(m, n)`.
    vh : pycuda.gpuarray.GPUArray
        Unitary matrix of shape `(n, n)` or `(k, n)`, depending
        on `jobvt`.

    Notes
    -----
    Double precision is only supported if the standard version of the
    CULA Dense toolkit is installed.

    This function destroys the contents of the input matrix regardless
    of the values of `jobu` and `jobvt`.

    Only one of `jobu` or `jobvt` may be set to `O`, and then only for
    a square matrix.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> a = np.random.randn(9, 6) + 1j*np.random.randn(9, 6)
    >>> a = np.asarray(a, np.complex64)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 'S', 'S')
    >>> np.allclose(a, np.dot(u_gpu.get(), np.dot(np.diag(s_gpu.get()), vh_gpu.get())), 1e-4)
    True

    """

    if not _has_cula:
        raise NotImplementError('CULA not installed')

    # The free version of CULA only supports single precision floating
    # point numbers:
    data_type = a_gpu.dtype.type
    real_type = np.float32
    if data_type == np.complex64:
        cula_func = cula._libcula.culaDeviceCgesvd
    elif data_type == np.float32:
        cula_func = cula._libcula.culaDeviceSgesvd
    else:
        if cula._libcula_toolkit == 'standard':
            if data_type == np.complex128:
                cula_func = cula._libcula.culaDeviceZgesvd
            elif data_type == np.float64:
                cula_func = cula._libcula.culaDeviceDgesvd
            else:
                raise ValueError('unsupported type')
            real_type = np.float64
        else:
            raise ValueError('double precision not supported')

    # Since CUDA assumes that arrays are stored in column-major
    # format, the input matrix is assumed to be transposed:
    n, m = a_gpu.shape
    square = (n == m)

    # Since the input matrix is transposed, jobu and jobvt must also
    # be switched because the computed matrices will be returned in
    # reversed order:
    jobvt, jobu = jobu, jobvt

    # Set the leading dimension of the input matrix:
    lda = max(1, m)

    # Allocate the array of singular values:
    s_gpu = gpuarray.empty(min(m, n), real_type)

    # Set the leading dimension and allocate u:
    jobu = upper(jobu)
    jobvt = upper(jobvt)
    ldu = m
    if jobu == 'A':
        u_gpu = gpuarray.empty((ldu, m), data_type)
    elif jobu == 'S':
        u_gpu = gpuarray.empty((min(m, n), ldu), data_type)
    elif jobu == 'O':
        if not square:
            raise ValueError('in-place computation of singular vectors '+
                             'of non-square matrix not allowed')
        ldu = 1
        u_gpu = a_gpu
    else:
        ldu = 1
        u_gpu = gpuarray.empty((), data_type)

    # Set the leading dimension and allocate vh:
    if jobvt == 'A':
        ldvt = n
        vh_gpu = gpuarray.empty((n, n), data_type)
    elif jobvt == 'S':
        ldvt = min(m, n)
        vh_gpu = gpuarray.empty((n, ldvt), data_type)
    elif jobvt == 'O':
        if jobu == 'O':
            raise ValueError('jobu and jobvt cannot both be O')
        if not square:
            raise ValueError('in-place computation of singular vectors '+
                             'of non-square matrix not allowed')
        ldvt = 1
        vh_gpu = a_gpu
    else:
        ldvt = 1
        vh_gpu = gpuarray.empty((), data_type)

    # Compute SVD and check error status:

    status = cula_func(jobu, jobvt, m, n, int(a_gpu.gpudata),
                       lda, int(s_gpu.gpudata), int(u_gpu.gpudata),
                       ldu, int(vh_gpu.gpudata), ldvt)

    cula.culaCheckStatus(status)

    # Free internal CULA memory:
    cula.culaFreeBuffers()

    # Since the input is assumed to be transposed, it is necessary to
    # return the computed matrices in reverse order:
    if jobu in ['A', 'S', 'O'] and jobvt in ['A', 'S', 'O']:
        return vh_gpu, s_gpu, u_gpu
    elif jobu == 'N' and jobvt != 'N':
        return vh_gpu, s_gpu
    elif jobu != 'N' and jobvt == 'N':
        return s_gpu, u_gpu
    else:
        return s_gpu


def cho_factor(a_gpu, uplo='L'):
    """
    Cholesky factorisation

    Performs an in-place cholesky factorisation on the matrix `a`
    such that `a = x*x.T` or `x.T*x`, if the lower='L' or upper='U'
    triangle of `a` is used, respectively.

    Parameters
    ----------
    a : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, m)` to decompose.
    uplo: use the upper='U' or lower='L' (default) triangle of 'a'

    Returns
    -------
    a: pycuda.gpuarray.GPUArray
        Cholesky factorised matrix

    Notes
    -----
    Double precision is only supported if the standard version of the
    CULA Dense toolkit is installed.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import scipy.linalg
    >>> import linalg
    >>> linalg.init()
    >>> a = np.array([[3.0,0.0],[0.0,7.0]])
    >>> a = np.asarray(a, np.float64)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> cho_factor(a_gpu)
    >>> np.allclose(a_gpu.get(), scipy.linalg.cho_factor(a)[0])
    True

    """

    if not _has_cula:
        raise NotImplementError('CULA not installed')

    data_type = a_gpu.dtype.type
    real_type = np.float32
    if cula._libcula_toolkit == 'standard':
        if data_type == np.complex64:
            cula_func = cula._libcula.culaDeviceCpotrf
        elif data_type == np.float32:
            cula_func = cula._libcula.culaDeviceSpotrf
        if data_type == np.complex128:
            cula_func = cula._libcula.culaDeviceZpotrf
        elif data_type == np.float64:
            cula_func = cula._libcula.culaDeviceDpotrf
        else:
            raise ValueError('unsupported type')
        real_type = np.float64
    else:
        raise ValueError('Cholesky factorisation not included in CULA Dense Free version')

    # Since CUDA assumes that arrays are stored in column-major
    # format, the input matrix is assumed to be transposed:
    n, m = a_gpu.shape
    square = (n == m)

    if (n!=m):
        raise ValueError('Matrix must be symmetric positive-definite')

    # Set the leading dimension of the input matrix:
    lda = max(1, m)

    status = cula_func(uplo, n, int(a_gpu.gpudata), lda)

    cula.culaCheckStatus(status)

    # Free internal CULA memory:
    cula.culaFreeBuffers()

    # In-place operation. No return matrix. Result is stored in the input matrix.


def cho_solve(a_gpu, b_gpu, uplo='L'):
    """
    Cholesky solver

    Solve a system of equations via cholesky factorization,
    i.e. `a*x = b`.
    Overwrites `b` to give `inv(a)*b`, and overwrites the chosen triangle
    of `a` with factorized triangle

    Parameters
    ----------
    a : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, m)` to decompose.
    b : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, 1)` to decompose.
    uplo: chr
        use the upper='U' or lower='L' (default) triangle of `a`.

    Returns
    -------
    a: pycuda.gpuarray.GPUArray
        Cholesky factorised matrix

    Notes
    -----
    Double precision is only supported if the standard version of the
    CULA Dense toolkit is installed.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import scipy.linalg
    >>> import linalg
    >>> linalg.init()
    >>> a = np.array([[3.0,0.0],[0.0,7.0]])
    >>> a = np.asarray(a, np.float64)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> b = np.array([11.,19.])
    >>> b = np.asarray(b, np.float64)
    >>> b_gpu  = gpuarray.to_gpu(b)
    >>> cho_solve(a_gpu,b_gpu)
    >>> np.allclose(b_gpu.get(), scipy.linalg.cho_solve(scipy.linalg.cho_factor(a), b))
    True

    """

    if not _has_cula:
        raise NotImplementError('CULA not installed')

    data_type = a_gpu.dtype.type
    real_type = np.float32
    if cula._libcula_toolkit == 'standard':
        if data_type == np.complex64:
            cula_func = cula._libcula.culaDeviceCposv
        elif data_type == np.float32:
            cula_func = cula._libcula.culaDeviceSposv
        if data_type == np.complex128:
            cula_func = cula._libcula.culaDeviceZposv
        elif data_type == np.float64:
            cula_func = cula._libcula.culaDeviceDposv
        else:
            raise ValueError('unsupported type')
        real_type = np.float64
    else:
        raise ValueError('Cholesky factorisation not included in CULA Dense Free version')

    # Since CUDA assumes that arrays are stored in column-major
    # format, the input matrix is assumed to be transposed:
    na, ma = a_gpu.shape
    square = (na == ma)
    
    if (na!=ma):
        raise ValueError('Matrix must be symmetric positive-definite')

    # Set the leading dimension of the input matrix:
    lda = max(1, ma)
    ldb = lda

    # Assuming we are only solving for a vector. Hence, nrhs = 1
    status = cula_func(uplo, na, 1, int(a_gpu.gpudata), lda, 
                       int(b_gpu.gpudata), ldb)

    cula.culaCheckStatus(status)

    # Free internal CULA memory:
    cula.culaFreeBuffers()

    # In-place operation. No return matrix. Result is stored in the input matrix
    # and in the input vector.


def dot(x_gpu, y_gpu, transa='N', transb='N', handle=None):
    """
    Dot product of two arrays.

    For 1D arrays, this function computes the inner product. For 2D
    arrays of shapes `(m, k)` and `(k, n)`, it computes the matrix
    product; the result has shape `(m, n)`.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.
    y_gpu : pycuda.gpuarray.GPUArray
        Input array.
    transa : char
        If 'T', compute the product of the transpose of `x_gpu`.
        If 'C', compute the product of the Hermitian of `x_gpu`.
    transb : char
        If 'T', compute the product of the transpose of `y_gpu`.
        If 'C', compute the product of the Hermitian of `y_gpu`.
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.cuda.misc._global_cublas_handle` is used.

    Returns
    -------
    c_gpu : pycuda.gpuarray.GPUArray, float{32,64}, or complex{64,128}
        Inner product of `x_gpu` and `y_gpu`. When the inputs are 1D
        arrays, the result will be returned as a scalar.

    Notes
    -----
    The input matrices must all contain elements of the same data type.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> import misc
    >>> linalg.init()
    >>> a = np.asarray(np.random.rand(4, 2), np.float32)
    >>> b = np.asarray(np.random.rand(2, 2), np.float32)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> b_gpu = gpuarray.to_gpu(b)
    >>> c_gpu = linalg.dot(a_gpu, b_gpu)
    >>> np.allclose(np.dot(a, b), c_gpu.get())
    True
    >>> d = np.asarray(np.random.rand(5), np.float32)
    >>> e = np.asarray(np.random.rand(5), np.float32)
    >>> d_gpu = gpuarray.to_gpu(d)
    >>> e_gpu = gpuarray.to_gpu(e)
    >>> f = linalg.dot(d_gpu, e_gpu)
    >>> np.allclose(np.dot(d, e), f)
    True

    """

    if handle is None:
        handle = misc._global_cublas_handle

    if len(x_gpu.shape) == 1 and len(y_gpu.shape) == 1:

        if x_gpu.size != y_gpu.size:
            raise ValueError('arrays must be of same length')

        # Compute inner product for 1D arrays:
        if (x_gpu.dtype == np.complex64 and y_gpu.dtype == np.complex64):
            cublas_func = cublas.cublasCdotu
        elif (x_gpu.dtype == np.float32 and y_gpu.dtype == np.float32):
            cublas_func = cublas.cublasSdot
        elif (x_gpu.dtype == np.complex128 and y_gpu.dtype == np.complex128):
            cublas_func = cublas.cublasZdotu
        elif (x_gpu.dtype == np.float64 and y_gpu.dtype == np.float64):
            cublas_func = cublas.cublasDdot
        else:
            raise ValueError('unsupported combination of input types')

        return cublas_func(handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
    else:

        # Get the shapes of the arguments (accounting for the
        # possibility that one of them may only have one dimension):
        x_shape = x_gpu.shape
        y_shape = y_gpu.shape
        if len(x_shape) == 1:
            x_shape = (1, x_shape[0])
        if len(y_shape) == 1:
            y_shape = (1, y_shape[0])

        # Perform matrix multiplication for 2D arrays:
        if (x_gpu.dtype == np.complex64 and y_gpu.dtype == np.complex64):
            cublas_func = cublas.cublasCgemm
            alpha = np.complex64(1.0)
            beta = np.complex64(0.0)
        elif (x_gpu.dtype == np.float32 and y_gpu.dtype == np.float32):
            cublas_func = cublas.cublasSgemm
            alpha = np.float32(1.0)
            beta = np.float32(0.0)
        elif (x_gpu.dtype == np.complex128 and y_gpu.dtype == np.complex128):
            cublas_func = cublas.cublasZgemm
            alpha = np.complex128(1.0)
            beta = np.complex128(0.0)
        elif (x_gpu.dtype == np.float64 and y_gpu.dtype == np.float64):
            cublas_func = cublas.cublasDgemm
            alpha = np.float64(1.0)
            beta = np.float64(0.0)
        else:
            raise ValueError('unsupported combination of input types')

        transa = lower(transa)
        transb = lower(transb)

        if transb in ['t', 'c']:
            m, k = y_shape
        elif transb in ['n']:
            k, m = y_shape
        else:
            raise ValueError('invalid value for transb')

        if transa in ['t', 'c']:
            l, n = x_shape
        elif transa in ['n']:
            n, l = x_shape
        else:
            raise ValueError('invalid value for transa')

        if l != k:
            raise ValueError('objects are not aligned')

        if transb == 'n':
            lda = max(1, m)
        else:
            lda = max(1, k)

        if transa == 'n':
            ldb = max(1, k)
        else:
            ldb = max(1, n)

        ldc = max(1, m)

        # Note that the desired shape of the output matrix is the transpose
        # of what CUBLAS assumes:
        c_gpu = gpuarray.empty((n, ldc), x_gpu.dtype)
        cublas_func(handle, transb, transa, m, n, k, alpha, y_gpu.gpudata,
                    lda, x_gpu.gpudata, ldb, beta, c_gpu.gpudata, ldc)

        return c_gpu

def mdot(*args, **kwargs):
    """
    Product of several matrices.

    Computes the matrix product of several arrays of shapes.

    Parameters
    ----------
    a_gpu, b_gpu, ... : pycuda.gpuarray.GPUArray
        Arrays to multiply.
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.cuda.misc._global_cublas_handle` is used.

    Returns
    -------
    c_gpu : pycuda.gpuarray.GPUArray
        Matrix product of `a_gpu`, `b_gpu`, etc.

    Notes
    -----
    The input matrices must all contain elements of the same data type.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> a = np.asarray(np.random.rand(4, 2), np.float32)
    >>> b = np.asarray(np.random.rand(2, 2), np.float32)
    >>> c = np.asarray(np.random.rand(2, 2), np.float32)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> b_gpu = gpuarray.to_gpu(b)
    >>> c_gpu = gpuarray.to_gpu(c)
    >>> d_gpu = linalg.mdot(a_gpu, b_gpu, c_gpu)
    >>> np.allclose(np.dot(a, np.dot(b, c)), d_gpu.get())
    True

    """

    if kwargs.has_key('handle') and kwargs['handle'] is not None:
        handle = kwargs['handle']
    else:
        handle = misc._global_cublas_handle
        
    # Free the temporary matrix allocated when computing the dot
    # product:
    out_gpu = args[0]
    for next_gpu in args[1:]:
        temp_gpu = dot(out_gpu, next_gpu, handle=handle)
        out_gpu.gpudata.free()
        del(out_gpu)
        out_gpu = temp_gpu
        del(temp_gpu)
    return out_gpu

def dot_diag(d_gpu, a_gpu, trans='N', overwrite=True, handle=None):
    """
    Dot product of diagonal and non-diagonal arrays.

    Computes the matrix product of a diagonal array represented as a
    vector and a non-diagonal array.

    Parameters
    ----------
    d_gpu : pycuda.gpuarray.GPUArray
        Array of length `N` corresponding to the diagonal of the
        multiplier.
    a_gpu : pycuda.gpuarray.GPUArray
        Multiplicand array with shape `(N, M)`.
    trans : char
        If 'T', compute the product of the transpose of `a_gpu`.
    overwrite : bool
        If true (default), save the result in `a_gpu`.
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.cuda.misc._global_cublas_handle` is used.

    Returns
    -------
    r_gpu : pycuda.gpuarray.GPUArray
        The computed matrix product.

    Notes
    -----
    `d_gpu` and `a_gpu` must have the same precision data
    type. `d_gpu` may be real and `a_gpu` may be complex, but not
    vice-versa.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> d = np.random.rand(4)
    >>> a = np.random.rand(4, 4)
    >>> d_gpu = gpuarray.to_gpu(d)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> r_gpu = linalg.dot_diag(d_gpu, a_gpu)
    >>> np.allclose(np.dot(np.diag(d), a), r_gpu.get())
    True

    """

    if handle is None:
        handle = misc._global_cublas_handle

    if len(d_gpu.shape) != 1:
        raise ValueError('d_gpu must be a vector')
    if len(a_gpu.shape) != 2:
        raise ValueError('a_gpu must be a matrix')

    if lower(trans) == 'n':
        rows, cols = a_gpu.shape
    else:
        cols, rows = a_gpu.shape
    N = d_gpu.size
    if N != rows:
        raise ValueError('incompatible dimensions')

    float_type = a_gpu.dtype.type
    if float_type == np.float32:
        if d_gpu.dtype != np.float32:
            raise ValueError('precision of argument types must be the same')
        scal_func = cublas.cublasSscal
        copy_func = cublas.cublasScopy
    elif float_type == np.float64:
        if d_gpu.dtype != np.float64:
            raise ValueError('precision of argument types must be the same')
        scal_func = cublas.cublasDscal
        copy_func = cublas.cublasDcopy
    elif float_type == np.complex64:
        if d_gpu.dtype == np.complex64:
            scal_func = cublas.cublasCscal
        elif d_gpu.dtype == np.float32:
            scal_func = cublas.cublasCsscal
        else:
            raise ValueError('precision of argument types must be the same')
        copy_func = cublas.cublasCcopy
    elif float_type == np.complex128:
        if d_gpu.dtype == np.complex128:
            scal_func = cublas.cublasZscal
        elif d_gpu.dtype == np.float64:
            scal_func = cublas.cublasZdscal
        else:
            raise ValueError('precision of argument types must be the same')
        copy_func = cublas.cublasZcopy
    else:
        raise ValueError('unrecognized type')

    d = d_gpu.get()
    if overwrite:
        r_gpu = a_gpu
    else:
        r_gpu = gpuarray.empty_like(a_gpu)
        copy_func(handle, a_gpu.size, int(a_gpu.gpudata), 1,
                  int(r_gpu.gpudata), 1)

    if lower(trans) == 'n':
        incx = 1
        bytes_step = cols*float_type().itemsize
    else:
        incx = rows
        bytes_step = float_type().itemsize

    for i in xrange(N):
        scal_func(handle, cols, d[i], int(r_gpu.gpudata)+i*bytes_step, incx)
    return r_gpu

transpose_template = Template("""
#include <pycuda-complex.hpp>

#if ${use_double}
#if ${use_complex}
#define FLOAT pycuda::complex<double>
#define CONJ(x) conj(x)
#else
#define FLOAT double
#define CONJ(x) (x)
#endif
#else
#if ${use_complex}
#define FLOAT pycuda::complex<float>
#define CONJ(x) conj(x)
#else
#define FLOAT float
#define CONJ(x) (x)
#endif
#endif

__global__ void transpose(FLOAT *odata, FLOAT *idata, unsigned int N)
{
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;
    unsigned int ix = idx/${cols};
    unsigned int iy = idx%${cols};

    if (idx < N)
        if (${hermitian})
            odata[iy*${rows}+ix] = CONJ(idata[ix*${cols}+iy]);
        else
            odata[iy*${rows}+ix] = idata[ix*${cols}+iy];
}
""")

def transpose(a_gpu):
    """
    Matrix transpose.

    Transpose a matrix in device memory and return an object
    representing the transposed matrix.

    Parameters
    ----------
    a_gpu : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, n)`.

    Returns
    -------
    at_gpu : pycuda.gpuarray.GPUArray
        Transposed matrix of shape `(n, m)`.

    Notes
    -----
    The current implementation of the transpose operation is relatively inefficient.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> a = np.array([[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]], np.float32)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> at_gpu = linalg.transpose(a_gpu)
    >>> np.all(a.T == at_gpu.get())
    True
    >>> b = np.array([[1j, 2j, 3j, 4j, 5j, 6j], [7j, 8j, 9j, 10j, 11j, 12j]], np.complex64)
    >>> b_gpu = gpuarray.to_gpu(b)
    >>> bt_gpu = linalg.transpose(b_gpu)
    >>> np.all(b.T == bt_gpu.get())
    True

    """

    if a_gpu.dtype not in [np.float32, np.float64, np.complex64,
                           np.complex128]:
        raise ValueError('unrecognized type')

    use_double = int(a_gpu.dtype in [np.float64, np.complex128])
    use_complex = int(a_gpu.dtype in [np.complex64, np.complex128])

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, a_gpu.shape)

    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    transpose_mod = \
                  SourceModule(transpose_template.substitute(use_double=use_double,
                                                             use_complex=use_complex,
                                                             hermitian=0,
                               cols=a_gpu.shape[1],
                               rows=a_gpu.shape[0]),
                               cache_dir=cache_dir)

    transpose = transpose_mod.get_function("transpose")
    at_gpu = gpuarray.empty(a_gpu.shape[::-1], a_gpu.dtype)
    transpose(at_gpu, a_gpu, np.uint32(a_gpu.size),
              block=block_dim,
              grid=grid_dim)

    return at_gpu

def hermitian(a_gpu):
    """
    Hermitian (conjugate) matrix transpose.

    Conjugate transpose a matrix in device memory and return an object
    representing the transposed matrix.

    Parameters
    ----------
    a_gpu : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, n)`.

    Returns
    -------
    at_gpu : pycuda.gpuarray.GPUArray
        Transposed matrix of shape `(n, m)`.

    Notes
    -----
    The current implementation of the transpose operation is relatively inefficient.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> a = np.array([[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]], np.float32)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> at_gpu = linalg.hermitian(a_gpu)
    >>> np.all(a.T == at_gpu.get())
    True
    >>> b = np.array([[1j, 2j, 3j, 4j, 5j, 6j], [7j, 8j, 9j, 10j, 11j, 12j]], np.complex64)
    >>> b_gpu = gpuarray.to_gpu(b)
    >>> bt_gpu = linalg.hermitian(b_gpu)
    >>> np.all(np.conj(b.T) == bt_gpu.get())
    True

    """

    if a_gpu.dtype not in [np.float32, np.float64, np.complex64,
                           np.complex128]:
        raise ValueError('unrecognized type')

    use_double = int(a_gpu.dtype in [np.float64, np.complex128])
    use_complex = int(a_gpu.dtype in [np.complex64, np.complex128])

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, a_gpu.shape)

    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    transpose_mod = \
                  SourceModule(transpose_template.substitute(use_double=use_double,
                                                             use_complex=use_complex,
                                                             hermitian=1,
                               cols=a_gpu.shape[1],
                               rows=a_gpu.shape[0]),
                               cache_dir=cache_dir)

    transpose = transpose_mod.get_function("transpose")
    at_gpu = gpuarray.empty(a_gpu.shape[::-1], a_gpu.dtype)
    transpose(at_gpu, a_gpu, np.uint32(a_gpu.size),
              block=block_dim,
              grid=grid_dim)

    return at_gpu

def conj(x_gpu, overwrite=True):
    """
    Complex conjugate.

    Compute the complex conjugate of the array in device memory.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array of shape `(m, n)`.
    overwrite : bool
        If true (default), save the result in the specified array.
        If false, return the result in a newly allocated array.

    Returns
    -------
    xc_gpu : pycuda.gpuarray.GPUArray
        Conjugate of the input array. If `overwrite` is true, the
        returned matrix is the same as the input array.

    Examples
    --------
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> x = np.array([[1+1j, 2-2j, 3+3j, 4-4j], [5+5j, 6-6j, 7+7j, 8-8j]], np.complex64)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = linalg.conj(x_gpu)
    >>> np.all(x == np.conj(y_gpu.get()))
    True

    """

    # Don't attempt to process non-complex matrix types:
    if x_gpu.dtype in [np.float32, np.float64]:
        return x_gpu
    
    try:
        func = conj.cache[x_gpu.dtype]
    except KeyError:
        ctype = tools.dtype_to_ctype(x_gpu.dtype)
        func = el.ElementwiseKernel(
                "{ctype} *x, {ctype} *y".format(ctype=ctype),
                "y[i] = conj(x[i])")
        conj.cache[x_gpu.dtype] = func
    if overwrite:
        func(x_gpu, x_gpu)
        return x_gpu
    else:
        y_gpu = gpuarray.empty_like(x_gpu)
        func(x_gpu, y_gpu)
        return y_gpu
conj.cache = {}

diag_template = Template("""
#include <pycuda-complex.hpp>

#if ${use_double}
#if ${use_complex}
#define FLOAT pycuda::complex<double>
#else
#define FLOAT double
#endif
#else
#if ${use_complex}
#define FLOAT pycuda::complex<float>
#else
#define FLOAT float
#endif
#endif

// Assumes that d already contains zeros in all positions.
// N must contain the number of elements in v.
__global__ void diag(FLOAT *v, FLOAT *d, int N) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;
    if (idx < N)
        d[idx*(N+1)] = v[idx];
}

""")

def diag(v_gpu):
    """
    Construct a diagonal matrix if input array is one-dimensional,
    or extracts diagonal entries of a two-dimensional array.

    --- If input-array is one-dimensional: 
    Constructs a matrix in device memory whose diagonal elements
    correspond to the elements in the specified array; all
    non-diagonal elements are set to 0.
    
    --- If input-array is two-dimensional: 
    Constructs an array in device memory whose elements
    correspond to the elements along the main-diagonal of the specified 
    array.

    Parameters
    ----------
    v_obj : pycuda.gpuarray.GPUArray
            Input array of shape `(n,m)`.

    Returns
    -------
    d_gpu : pycuda.gpuarray.GPUArray
            ---If v_obj has shape `(n,1)`, output is 
               diagonal matrix of dimensions `[n, n]`.
            ---If v_obj has shape `(n,m)`, output is 
               array of length `min(n,m)`.

    Examples
    --------
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> v = np.array([1, 2, 3, 4, 5, 6], np.float32)
    >>> v_gpu = gpuarray.to_gpu(v)
    >>> d_gpu = linalg.diag(v_gpu)
    >>> np.all(d_gpu.get() == np.diag(v))
    True
    >>> v = np.array([1j, 2j, 3j, 4j, 5j, 6j], np.complex64)
    >>> v_gpu = gpuarray.to_gpu(v)
    >>> d_gpu = linalg.diag(v_gpu)
    >>> np.all(d_gpu.get() == np.diag(v))
    True
    >>> v = np.array([[1., 2., 3.],[4., 5., 6.]], np.float64)
    >>> v_gpu = gpuarray.to_gpu(v)
    >>> d_gpu = linalg.diag(v_gpu)
    >>> d_gpu
    array([ 1.,  5.])

    """

    if v_gpu.dtype not in [np.float32, np.float64, np.complex64,
                           np.complex128]:
        raise ValueError('unrecognized type')

    if (len(v_gpu.shape) > 1) and (len(v_gpu.shape) < 3):
        # Since CUDA assumes that arrays are stored in column-major
        # format, the input matrix is assumed to be transposed:
        n, m = v_gpu.shape
        square = (n == m)

        # Allocate the output array
        d_gpu = gpuarray.empty(min(m, n), v_gpu.dtype.type)

        diag_kernel = el.ElementwiseKernel("double *x, double *y, int z", "y[i] = x[(z+1)*i]", "diakernel")
        diag_kernel(v_gpu,d_gpu,max(m,n))

        return d_gpu
    elif len(v_gpu.shape) >= 3:
        raise ValueError('input array cannot have greater than 2-dimensions')

    use_double = int(v_gpu.dtype in [np.float64, np.complex128])
    use_complex = int(v_gpu.dtype in [np.complex64, np.complex128])

    # Initialize output matrix:
    d_gpu = misc.zeros((v_gpu.size, v_gpu.size), v_gpu.dtype)

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, d_gpu.shape)

    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    diag_mod = \
             SourceModule(diag_template.substitute(use_double=use_double,
                                                   use_complex=use_complex),
                          cache_dir=cache_dir)

    diag = diag_mod.get_function("diag")
    diag(v_gpu, d_gpu, np.uint32(v_gpu.size),
         block=block_dim,
         grid=grid_dim)

    return d_gpu

eye_template = Template("""
#include <pycuda-complex.hpp>

#if ${use_double}
#if ${use_complex}
#define FLOAT pycuda::complex<double>
#else
#define FLOAT double
#endif
#else
#if ${use_complex}
#define FLOAT pycuda::complex<float>
#else
#define FLOAT float
#endif
#endif

// Assumes that d already contains zeros in all positions.
// N must contain the number of rows or columns in the matrix.
__global__ void eye(FLOAT *d, int N) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;
    if (idx < N)
        d[idx*(N+1)] = FLOAT(1.0);
}

""")

def eye(N, dtype=np.float32):
    """
    Construct a 2D matrix with ones on the diagonal and zeros elsewhere.

    Constructs a matrix in device memory whose diagonal elements
    are set to 1 and non-diagonal elements are set to 0.

    Parameters
    ----------
    N : int
        Number of rows or columns in the output matrix.
    dtype : type
        Matrix data type.

    Returns
    -------
    e_gpu : pycuda.gpuarray.GPUArray
        Diagonal matrix of dimensions `[N, N]` with diagonal values
        set to 1.

    Examples
    --------
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> N = 5
    >>> e_gpu = linalg.eye(N)
    >>> np.all(e_gpu.get() == np.eye(N))
    True
    >>> e_gpu = linalg.eye(N, np.complex64)
    >>> np.all(e_gpu.get() == np.eye(N, dtype=np.complex64))
    True

    """

    if dtype not in [np.float32, np.float64, np.complex64,
                     np.complex128]:
        raise ValueError('unrecognized type')
    if N <= 0:
        raise ValueError('N must be greater than 0')

    use_double = int(dtype in [np.float64, np.complex128])
    use_complex = int(dtype in [np.complex64, np.complex128])

    # Initialize output matrix:
    e_gpu = misc.zeros((N, N), dtype)

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, e_gpu.shape)

    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    eye_mod = \
             SourceModule(eye_template.substitute(use_double=use_double,
                                                   use_complex=use_complex),
                          cache_dir=cache_dir)

    eye = eye_mod.get_function("eye")
    eye(e_gpu, np.uint32(N),
        block=block_dim,
        grid=grid_dim)

    return e_gpu

cutoff_invert_s_template = Template("""
#if ${use_double}
#define FLOAT double
#else
#define FLOAT float
#endif

// N must equal the length of s:
__global__ void cutoff_invert_s(FLOAT *s, FLOAT *cutoff, unsigned int N) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;

    if (idx < N)
        if (s[idx] > cutoff[0])
            s[idx] = 1/s[idx];
        else
            s[idx] = 0.0;
}
""")

def pinv(a_gpu, rcond=1e-15):
    """
    Moore-Penrose pseudoinverse.

    Compute the Moore-Penrose pseudoinverse of the specified matrix.

    Parameters
    ----------
    a_gpu : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, n)`.
    rcond : float
        Singular values smaller than `rcond`*max(singular_values)`
        are set to zero.

    Returns
    -------
    a_inv_gpu : pycuda.gpuarray.GPUArray
        Pseudoinverse of input matrix.

    Notes
    -----
    Double precision is only supported if the standard version of the
    CULA Dense toolkit is installed.

    This function destroys the contents of the input matrix.

    If the input matrix is square, the pseudoinverse uses less memory.

    Examples
    --------
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> a = np.asarray(np.random.rand(8, 4), np.float32)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> a_inv_gpu = linalg.pinv(a_gpu)
    >>> np.allclose(np.linalg.pinv(a), a_inv_gpu.get(), 1e-4)
    True
    >>> b = np.asarray(np.random.rand(8, 4)+1j*np.random.rand(8, 4), np.complex64)
    >>> b_gpu = gpuarray.to_gpu(b)
    >>> b_inv_gpu = linalg.pinv(b_gpu)
    >>> np.allclose(np.linalg.pinv(b), b_inv_gpu.get(), 1e-4)
    True

    """

    if not _has_cula:
        raise NotImplementedError('CULA not installed')

    # Perform in-place SVD if the matrix is square to save memory:
    if a_gpu.shape[0] == a_gpu.shape[1]:
        u_gpu, s_gpu, vh_gpu = svd(a_gpu, 's', 'o')
    else:
        u_gpu, s_gpu, vh_gpu = svd(a_gpu, 's', 's')

    # Get block/grid sizes; the number of threads per block is limited
    # to 512 because the cutoff_invert_s kernel defined above uses too
    # many registers to be invoked in 1024 threads per block (i.e., on
    # GPUs with compute capability >= 2.x):
    dev = misc.get_current_device()
    max_threads_per_block = 512
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, s_gpu.shape, max_threads_per_block)

    # Suppress very small singular values:
    use_double = 1 if s_gpu.dtype == np.float64 else 0
    cutoff_invert_s_mod = \
        SourceModule(cutoff_invert_s_template.substitute(use_double=use_double))
    cutoff_invert_s = \
                    cutoff_invert_s_mod.get_function('cutoff_invert_s')
    cutoff_gpu = gpuarray.max(s_gpu)*rcond
    cutoff_invert_s(s_gpu, cutoff_gpu,
                    np.uint32(s_gpu.size),
                    block=block_dim, grid=grid_dim)

    # Compute the pseudoinverse without allocating a new diagonal matrix:
    return dot(vh_gpu, dot_diag(s_gpu, u_gpu, 't'), 'c', 'c')

tril_template = Template("""
#include <pycuda-complex.hpp>

#if ${use_double}
#if ${use_complex}
#define FLOAT pycuda::complex<double>
#else
#define FLOAT double
#endif
#else
#if ${use_complex}
#define FLOAT pycuda::complex<float>
#else
#define FLOAT float
#endif
#endif

__global__ void tril(FLOAT *a, unsigned int N) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;
    unsigned int ix = idx/${cols};
    unsigned int iy = idx%${cols};

    if (idx < N) {
        if (ix < iy)
            a[idx] = 0.0;
    }
}
""")

def tril(a_gpu, overwrite=True, handle=None):
    """
    Lower triangle of a matrix.

    Return the lower triangle of a square matrix.

    Parameters
    ----------
    a_gpu : pycuda.gpuarray.GPUArray
        Input matrix of shape `(m, m)`
    overwrite : boolean
        If true (default), zero out the upper triangle of the matrix.
        If false, return the result in a newly allocated matrix.
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.cuda.misc._global_cublas_handle` is used.

    Returns
    -------
    l_gpu : pycuda.gpuarray
        The lower triangle of the original matrix.

    Examples
    --------
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> a = np.asarray(np.random.rand(4, 4), np.float32)
    >>> a_gpu = gpuarray.to_gpu(a)
    >>> l_gpu = linalg.tril(a_gpu, False)
    >>> np.allclose(np.tril(a), l_gpu.get())
    True

    """

    if handle is None:
        handle = misc._global_cublas_handle
        
    if len(a_gpu.shape) != 2 or a_gpu.shape[0] != a_gpu.shape[1]:
        raise ValueError('matrix must be square')

    if a_gpu.dtype == np.float32:
        swap_func = cublas.cublasSswap
        copy_func = cublas.cublasScopy
        use_double = 0
        use_complex = 0
    elif a_gpu.dtype == np.float64:
        swap_func = cublas.cublasDswap
        copy_func = cublas.cublasDcopy
        use_double = 1
        use_complex = 0
    elif a_gpu.dtype == np.complex64:
        swap_func = cublas.cublasCswap
        copy_func = cublas.cublasCcopy
        use_double = 0
        use_complex = 1
    elif a_gpu.dtype == np.complex128:
        swap_func = cublas.cublasZswap
        copy_func = cublas.cublasZcopy
        use_double = 1
        use_complex = 1
    else:
        raise ValueError('unrecognized type')

    N = a_gpu.shape[0]

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, a_gpu.shape)

    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    tril_mod = \
             SourceModule(tril_template.substitute(use_double=use_double,
                                                   use_complex=use_complex,
                                                   cols=N),
                          cache_dir=cache_dir)
    tril = tril_mod.get_function("tril")

    if not overwrite:
        a_orig_gpu = gpuarray.empty(a_gpu.shape, a_gpu.dtype)
        copy_func(handle, a_gpu.size, int(a_gpu.gpudata), 1, int(a_orig_gpu.gpudata), 1)

    tril(a_gpu, np.uint32(a_gpu.size),
         block=block_dim,
         grid=grid_dim)

    if overwrite:
        return a_gpu
    else:

        # Restore original contents of a_gpu:
        swap_func(handle, a_gpu.size, int(a_gpu.gpudata), 1, int(a_orig_gpu.gpudata), 1)
        return a_orig_gpu

multiply_template = Template("""
#include <pycuda-complex.hpp>

#if ${use_double}
#if ${use_complex}
#define FLOAT pycuda::complex<double>
#else
#define FLOAT double
#endif
#else
#if ${use_complex}
#define FLOAT pycuda::complex<float>
#else
#define FLOAT float
#endif
#endif

// Stores result in y
__global__ void multiply_inplace(FLOAT *x, FLOAT *y,
                                 unsigned int N) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;
    if (idx < N) {
        y[idx] *= x[idx];
    }
}

// Stores result in z
__global__ void multiply(FLOAT *x, FLOAT *y, FLOAT *z,
                         unsigned int N) {
    unsigned int idx = blockIdx.y*blockDim.x*gridDim.x+
                       blockIdx.x*blockDim.x+threadIdx.x;
    if (idx < N) {
        z[idx] = x[idx]*y[idx];
    }
}
""")

def multiply(x_gpu, y_gpu, overwrite=True):
    """
    Multiply arguments element-wise.

    Parameters
    ----------
    x_gpu, y_gpu : pycuda.gpuarray.GPUArray
        Input arrays to be multiplied.
    dev : pycuda.driver.Device
        Device object to be used.
    overwrite : bool
        If true (default), return the result in `y_gpu`.
        is false, return the result in a newly allocated array.

    Returns
    -------
    z_gpu : pycuda.gpuarray.GPUArray
        The element-wise product of the input arrays.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> x = np.asarray(np.random.rand(4, 4), np.float32)
    >>> y = np.asarray(np.random.rand(4, 4), np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = gpuarray.to_gpu(y)
    >>> z_gpu = linalg.multiply(x_gpu, y_gpu)
    >>> np.allclose(x*y, z_gpu.get())
    True

    """

    if x_gpu.shape != y_gpu.shape:
        raise ValueError('input arrays must have the same shape')

    if x_gpu.dtype not in [np.float32, np.float64, np.complex64,
                           np.complex128]:
        raise ValueError('unrecognized type')

    use_double = int(x_gpu.dtype in [np.float64, np.complex128])
    use_complex = int(x_gpu.dtype in [np.complex64, np.complex128])

    # Get block/grid sizes:
    dev = misc.get_current_device()
    block_dim, grid_dim = misc.select_block_grid_sizes(dev, x_gpu.shape)

    # Set this to False when debugging to make sure the compiled kernel is
    # not cached:
    cache_dir=None
    multiply_mod = \
             SourceModule(multiply_template.substitute(use_double=use_double,
                                                       use_complex=use_complex),
                          cache_dir=cache_dir)
    if overwrite:
        multiply = multiply_mod.get_function("multiply_inplace")
        multiply(x_gpu, y_gpu, np.uint32(x_gpu.size),
                 block=block_dim,
                 grid=grid_dim)
        return y_gpu
    else:
        multiply = multiply_mod.get_function("multiply")
        z_gpu = gpuarray.empty(x_gpu.shape, x_gpu.dtype)
        multiply(x_gpu, y_gpu, z_gpu, np.uint32(x_gpu.size),
                 block=block_dim,
                 grid=grid_dim)
        return z_gpu

def norm(x_gpu, handle=None):
    """
    Euclidean norm (2-norm) of real vector.

    Computes the Euclidean norm of an array.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.misc._global_cublas_handle` is used.

    Returns
    -------
    nrm : real
        Euclidean norm of `x`.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> x = np.asarray(np.random.rand(4, 4), np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> nrm = linalg.norm(x_gpu)
    >>> np.allclose(nrm, np.linalg.norm(x))
    True
    >>> x_gpu = gpuarray.to_gpu(np.array([3+4j, 12-84j]))
    >>> linalg.norm(x_gpu)
    85.0

    """
    
    if handle is None:
        handle = misc._global_cublas_handle

    if len(x_gpu.shape) != 1:
        x_gpu = x_gpu.ravel()

    # Compute inner product for 1D arrays:
    if (x_gpu.dtype == np.complex64):
        cublas_func = cublas.cublasScnrm2
    elif (x_gpu.dtype == np.float32):
        cublas_func = cublas.cublasSnrm2
    elif (x_gpu.dtype == np.complex128):
        cublas_func = cublas.cublasDznrm2
    elif (x_gpu.dtype == np.float64):
        cublas_func = cublas.cublasDnrm2
    else:
        raise ValueError('unsupported input type')

    return cublas_func(handle, x_gpu.size, x_gpu.gpudata, 1) 

def scale(alpha, x_gpu, alpha_real=False, handle=None):
    """
    Scale a vector by a factor alpha.

    Parameters
    ----------
    alpha : scalar
        Scale parameter
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.
    alpha_real : bool
        If `True` and `x_gpu` is complex, then one of the specialized versions 
        `cublasCsscal` or `cublasZdscal` is used which might improve
        performance for large arrays.  (By default, `alpha` is coerced to
        the corresponding complex type.) 
    handle : int
        CUBLAS context. If no context is specified, the default handle from
        `scikits.misc._global_cublas_handle` is used.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import numpy as np
    >>> import linalg
    >>> linalg.init()
    >>> x = np.asarray(np.random.rand(4, 4), np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> alpha = 2.4
    >>> linalg.scale(alpha, x_gpu)
    >>> np.allclose(x_gpu.get(), alpha*x)
    True
    """
    
    if handle is None:
        handle = misc._global_cublas_handle

    if len(x_gpu.shape) != 1:
        x_gpu = x_gpu.ravel()

    cublas_func = {
        np.float32: cublas.cublasSscal,
        np.float64: cublas.cublasDscal,
        np.complex64: cublas.cublasCsscal if alpha_real else 
                      cublas.cublasCscal, 
        np.complex128: cublas.cublasZdscal if alpha_real else 
                       cublas.cublasZscal 
    }.get(x_gpu.dtype.type, None)

    if cublas_func:
        return cublas_func(handle, x_gpu.size, alpha, x_gpu.gpudata, 1) 
    else:
        raise ValueError('unsupported input type')


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = magma
#!/usr/bin/env python

"""
Python interface to MAGMA toolkit.
"""

import sys
import ctypes
import atexit
import numpy as np

import cuda

# Load MAGMA library:
if sys.platform == 'linux2':
    _libmagma_libname_list = ['libmagma.so']
elif sys.platform == 'darwin':
    _libmagma_libname_list = ['magma.so', 'libmagma.dylib']
else:
    raise RuntimeError('unsupported platform')

_load_err = ''
for _lib in  _libmagma_libname_list:
    try:
        _libmagma = ctypes.cdll.LoadLibrary(_lib)
    except OSError:
        _load_err += ('' if _load_err == '' else ', ') + _lib
    else:
        _load_err = ''
        break
if _load_err:
    raise OSError('%s not found' % _load_err)

# Exceptions corresponding to various MAGMA errors:
_libmagma.magma_strerror.restype = ctypes.c_char_p
_libmagma.magma_strerror.argtypes = [ctypes.c_int]
def magma_strerror(error):
    """
    Return string corresponding to specified MAGMA error code.
    """
    
    return _libmagma.magma_strerror(error)

class magmaError(Exception):
    try:
        __doc__ = magma_strerror(-100)
    except:
        pass
    pass

class magmaNotInitialized(magmaError):
    try:
        __doc__ = magma_strerror(-101)
    except:
        pass
    pass

class magmaReinitialized(magmaError):
    try:
        __doc__ = magma_strerror(-102)
    except:
        pass
    pass

class magmaNotSupported(magmaError):
    try:
        __doc__ = magma_strerror(-103)
    except:
        pass
    pass

class magmaIllegalValue(magmaError):
    try:
        __doc__ = magma_strerror(-104)
    except:
        pass
    pass

class magmaIllegalValue(magmaError):
    try:
        __doc__ = magma_strerror(-104)
    except:
        pass
    pass

class magmaNotFound(magmaError):
    try:
        __doc__ = magma_strerror(-105)
    except:
        pass
    pass

class magmaAllocation(magmaError):
    try:
        __doc__ = magma_strerror(-106)
    except:
        pass
    pass

class magmaInternalLimit(magmaError):
    try:
        __doc__ = magma_strerror(-107)
    except:
        pass
    pass

class magmaUnallocated(magmaError):
    try:
        __doc__ = magma_strerror(-108)
    except:
        pass
    pass

class magmaFilesystem(magmaError):
    try:
        __doc__ = magma_strerror(-109)
    except:
        pass
    pass

class magmaUnexpected(magmaError):
    try:
        __doc__ = magma_strerror(-110)
    except:
        pass
    pass
 
class magmaSequenceFlushed(magmaError):
    try:
        __doc__ = magma_strerror(-111)
    except:
        pass
    pass

class magmaHostAlloc(magmaError):
    try:
        __doc__ = magma_strerror(-112)
    except:
        pass
    pass
  
class magmaDeviceAlloc(magmaError):
    try:
        __doc__ = magma_strerror(-113)
    except:
        pass
    pass

class magmaCUDAStream(magmaError):
    try:
        __doc__ = magma_strerror(-114)
    except:
        pass
    pass

class magmaInvalidPtr(magmaError):
    try:
        __doc__ = magma_strerror(-115)
    except:
        pass
    pass

class magmaUnknown(magmaError):
    try:
        __doc__ = magma_strerror(-116)
    except:
        pass
    pass

magmaExceptions = {
    -100: magmaError,
     -101: magmaNotInitialized,
     -102: magmaReinitialized,
     -103: magmaNotSupported,
     -104: magmaIllegalValue,
     -105: magmaNotFound,
     -106: magmaAllocation,
     -107: magmaInternalLimit,
     -108: magmaUnallocated,
     -109: magmaFilesystem,
     -110: magmaUnexpected,
     -111: magmaSequenceFlushed,
     -112: magmaHostAlloc,
     -113: magmaDeviceAlloc,
     -114: magmaCUDAStream,
     -115: magmaInvalidPtr,
     -116: magmaUnknown
     }

def magmaCheckStatus(status):
    """
    Raise an exception corresponding to the specified MAGMA status code.
    """

    if status != 0:
        try:
            raise magmaExceptions[status]
        except KeyError:
            raise magmaError

# Utility functions:

_libmagma.magma_init.restype = int
def magma_init():
    """
    Initialize MAGMA.
    """

    status = _libmagma.magma_init()
    magmaCheckStatus(status)

_libmagma.magma_finalize.restype = int
def magma_finalize():
    """
    Finalize MAGMA.
    """

    status = _libmagma.magma_finalize()
    magmaCheckStatus(status)

_libmagma.magma_getdevice_arch.restype = int
def magma_getdevice_arch():
    """
    Get device architecture.
    """

    return _libmagma.magma_getdevice_arch()

_libmagma.magma_getdevice.argtypes = [ctypes.c_void_p]
def magma_getdevice():
    """
    Get current device used by MAGMA.
    """

    dev = ctypes.c_int()
    _libmagma.magma_getdevice(ctypes.byref(dev))
    return dev.value

_libmagma.magma_setdevice.argtypes = [ctypes.c_int]
def magma_setdevice(dev):
    """
    Get current device used by MAGMA.
    """

    _libmagma.magma_setdevice(dev)

def magma_device_sync():
    """
    Synchronize device used by MAGMA.
    """

    _libmagma.magma_device_sync()

# BLAS routines

# ISAMAX, IDAMAX, ICAMAX, IZAMAX
_libmagma.magma_isamax.restype = int
_libmagma.magma_isamax.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_isamax(n, dx, incx):
    """
    Index of maximum magnitude element.
    """

    return _libmagma.magma_isamax(n, int(dx), incx)

_libmagma.magma_idamax.restype = int
_libmagma.magma_idamax.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_idamax(n, dx, incx):
    """
    Index of maximum magnitude element.
    """

    return _libmagma.magma_idamax(n, int(dx), incx)

_libmagma.magma_icamax.restype = int
_libmagma.magma_icamax.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_icamax(n, dx, incx):
    """
    Index of maximum magnitude element.
    """

    return _libmagma.magma_icamax(n, int(dx), incx)

_libmagma.magma_izamax.restype = int
_libmagma.magma_izamax.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_izamax(n, dx, incx):
    """
    Index of maximum magnitude element.
    """

    return _libmagma.magma_izamax(n, int(dx), incx)

# ISAMIN, IDAMIN, ICAMIN, IZAMIN
_libmagma.magma_isamin.restype = int
_libmagma.magma_isamin.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_isamin(n, dx, incx):
    """
    Index of minimum magnitude element.
    """

    return _libmagma.magma_isamin(n, int(dx), incx)

_libmagma.magma_idamin.restype = int
_libmagma.magma_idamin.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_idamin(n, dx, incx):
    """
    Index of minimum magnitude element.
    """

    return _libmagma.magma_idamin(n, int(dx), incx)

_libmagma.magma_icamin.restype = int
_libmagma.magma_icamin.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_icamin(n, dx, incx):
    """
    Index of minimum magnitude element.
    """

    return _libmagma.magma_icamin(n, int(dx), incx)

_libmagma.magma_izamin.restype = int
_libmagma.magma_izamin.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_izamin(n, dx, incx):
    """
    Index of minimum magnitude element.
    """

    return _libmagma.magma_izamin(n, int(dx), incx)

# SASUM, DASUM, SCASUM, DZASUM
_libmagma.magma_sasum.restype = int
_libmagma.magma_sasum.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_sasum(n, dx, incx):
    """
    Sum of absolute values of vector.
    """

    return _libmagma.magma_sasum(n, int(dx), incx)

_libmagma.magma_dasum.restype = int
_libmagma.magma_dasum.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_dasum(n, dx, incx):
    """
    Sum of absolute values of vector.
    """

    return _libmagma.magma_dasum(n, int(dx), incx)

_libmagma.magma_scasum.restype = int
_libmagma.magma_scasum.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_scasum(n, dx, incx):
    """
    Sum of absolute values of vector.
    """

    return _libmagma.magma_scasum(n, int(dx), incx)

_libmagma.magma_dzasum.restype = int
_libmagma.magma_dzasum.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_dzasum(n, dx, incx):
    """
    Sum of absolute values of vector.
    """

    return _libmagma.magma_dzasum(n, int(dx), incx)

# SAXPY, DAXPY, CAXPY, ZAXPY
_libmagma.magma_saxpy.restype = int
_libmagma.magma_saxpy.argtypes = [ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_saxpy(n, alpha, dx, incx, dy, incy):
    """
    Vector addition.
    """

    _libmagma.magma_saxpy(n, alpha, int(dx), incx, int(dy), incy)

_libmagma.magma_daxpy.restype = int
_libmagma.magma_daxpy.argtypes = [ctypes.c_int,
                                  ctypes.c_double,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_daxpy(n, alpha, dx, incx, dy, incy):
    """
    Vector addition.
    """

    _libmagma.magma_daxpy(n, alpha, int(dx), incx, int(dy), incy)

_libmagma.magma_caxpy.restype = int
_libmagma.magma_caxpy.argtypes = [ctypes.c_int,
                                  cuda.cuFloatComplex,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_caxpy(n, alpha, dx, incx, dy, incy):
    """
    Vector addition.
    """

    _libmagma.magma_caxpy(n, ctypes.byref(cuda.cuFloatComplex(alpha.real,
                                                              alpha.imag)), 
                          int(dx), incx, int(dy), incy)

_libmagma.magma_zaxpy.restype = int
_libmagma.magma_zaxpy.argtypes = [ctypes.c_int,
                                  cuda.cuDoubleComplex,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_zaxpy(n, alpha, dx, incx, dy, incy):
    """
    Vector addition.
    """

    _libmagma.magma_zaxpy(n, ctypes.byref(cuda.cuDoubleComplex(alpha.real,
                                                               alpha.imag)), 
                          int(dx), incx, int(dy), incy)

# SCOPY, DCOPY, CCOPY, ZCOPY
_libmagma.magma_scopy.restype = int
_libmagma.magma_scopy.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_scopy(n, dx, incx, dy, incy):
    """
    Vector copy.
    """

    _libmagma.magma_scopy(n, int(dx), incx, int(dy), incy)

_libmagma.magma_dcopy.restype = int
_libmagma.magma_dcopy.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_dcopy(n, dx, incx, dy, incy):
    """
    Vector copy.
    """

    _libmagma.magma_dcopy(n, int(dx), incx, int(dy), incy)

_libmagma.magma_ccopy.restype = int
_libmagma.magma_ccopy.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_ccopy(n, dx, incx, dy, incy):
    """
    Vector copy.
    """

    _libmagma.magma_ccopy(n, int(dx), incx, int(dy), incy)

_libmagma.magma_zcopy.restype = int
_libmagma.magma_zcopy.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_zcopy(n, dx, incx, dy, incy):
    """
    Vector copy.
    """

    _libmagma.magma_zcopy(n, int(dx), incx, int(dy), incy)

# SDOT, DDOT, CDOTU, CDOTC, ZDOTU, ZDOTC
_libmagma.magma_sdot.restype = ctypes.c_float
_libmagma.magma_sdot.argtypes = [ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def magma_sdot(n, dx, incx, dy, incy):
    """
    Vector dot product.
    """

    return _libmagma.magma_sdot(n, int(dx), incx, int(dy), incy)

_libmagma.magma_ddot.restype = ctypes.c_double
_libmagma.magma_ddot.argtypes = [ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def magma_ddot(n, dx, incx, dy, incy):
    """
    Vector dot product.
    """

    return _libmagma.magma_ddot(n, int(dx), incx, int(dy), incy)

_libmagma.magma_cdotc.restype = cuda.cuFloatComplex
_libmagma.magma_cdotc.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_cdotc(n, dx, incx, dy, incy):
    """
    Vector dot product.
    """

    return _libmagma.magma_cdotc(n, int(dx), incx, int(dy), incy)

_libmagma.magma_cdotu.restype = cuda.cuFloatComplex
_libmagma.magma_cdotu.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_cdotu(n, dx, incx, dy, incy):
    """
    Vector dot product.
    """

    return _libmagma.magma_cdotu(n, int(dx), incx, int(dy), incy)

_libmagma.magma_zdotc.restype = cuda.cuDoubleComplex
_libmagma.magma_zdotc.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_zdotc(n, dx, incx, dy, incy):
    """
    Vector dot product.
    """

    return _libmagma.magma_zdotc(n, int(dx), incx, int(dy), incy)

_libmagma.magma_zdotu.restype = cuda.cuDoubleComplex
_libmagma.magma_zdotu.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_zdotu(n, dx, incx, dy, incy):
    """
    Vector dot product.
    """

    return _libmagma.magma_zdotu(n, int(dx), incx, int(dy), incy)

# SNRM2, DNRM2, SCNRM2, DZNRM2
_libmagma.magma_snrm2.restype = ctypes.c_float
_libmagma.magma_snrm2.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_snrm2(n, dx, incx):
    """
    Euclidean norm (2-norm) of vector.
    """

    return _libmagma.magma_snrm2(n, int(dx), incx)

_libmagma.magma_dnrm2.restype = ctypes.c_double
_libmagma.magma_dnrm2.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_dnrm2(n, dx, incx):
    """
    Euclidean norm (2-norm) of vector.
    """

    return _libmagma.magma_dnrm2(n, int(dx), incx)

_libmagma.magma_scnrm2.restype = ctypes.c_float
_libmagma.magma_scnrm2.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_scnrm2(n, dx, incx):
    """
    Euclidean norm (2-norm) of vector.
    """

    return _libmagma.magma_scnrm2(n, int(dx), incx)

_libmagma.magma_dznrm2.restype = ctypes.c_double
_libmagma.magma_dznrm2.argtypes = [ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_dznrm2(n, dx, incx):
    """
    Euclidean norm (2-norm) of vector.
    """

    return _libmagma.magma_dznrm2(n, int(dx), incx)

# SROT, DROT, CROT, CSROT, ZROT, ZDROT
_libmagma.magma_srot.argtypes = [ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_float,
                                 ctypes.c_float]
def magma_srot(n, dx, incx, dy, incy, dc, ds):
    """
    Apply a rotation to vectors.
    """

    _libmagma.magma_srot(n, int(dx), incx, int(dy), incy, dc, ds)

# SROTM, DROTM
_libmagma.magma_srotm.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p]
def magma_srotm(n, dx, incx, dy, incy, param):
    """
    Apply a real modified Givens rotation.
    """

    _libmagma.magma_srotm(n, int(dx), incx, int(dy), incy, param)

# SROTMG, DROTMG
_libmagma.magma_srotmg.argtypes = [ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p]
def magma_srotmg(d1, d2, x1, y1, param):
    """
    Construct a real modified Givens rotation matrix.
    """

    _libmagma.magma_srotmg(int(d1), int(d2), int(x1), int(y1), param)

# SSCAL, DSCAL, CSCAL, CSCAL, CSSCAL, ZSCAL, ZDSCAL
_libmagma.magma_sscal.argtypes = [ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_sscal(n, alpha, dx, incx):
    """
    Scale a vector by a scalar.
    """

    _libmagma.magma_sscal(n, alpha, int(dx), incx)

# SSWAP, DSWAP, CSWAP, ZSWAP
_libmagma.magma_sswap.argtypes = [ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_sswap(n, dA, ldda, dB, lddb):
    """
    Swap vectors.
    """

    _libmagma.magma_sswap(n, int(dA), ldda, int(dB), lddb)

# SGEMV, DGEMV, CGEMV, ZGEMV
_libmagma.magma_sgemv.argtypes = [ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_sgemv(trans, m, n, alpha, dA, ldda, dx, incx, beta,
                dy, incy):
    """
    Matrix-vector product for general matrix.
    """

    _libmagma.magma_sgemv(trans, m, n, alpha, int(dA), ldda, dx, incx,
                          beta, int(dy), incy)

# SGER, DGER, CGERU, CGERC, ZGERU, ZGERC
_libmagma.magma_sger.argtypes = [ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_float,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def magma_sger(m, n, alpha, dx, incx, dy, incy, dA, ldda):
    """
    Rank-1 operation on real general matrix.
    """

    _libmagma.magma_sger(m, n, alpha, int(dx), incx, int(dy), incy,
                         int(dA), ldda)

# SSYMV, DSYMV, CSYMV, ZSYMV
_libmagma.magma_ssymv.argtypes = [ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_ssymv(uplo, n, alpha, dA, ldda, dx, incx, beta, dy, incy):
    _libmagma.magma_ssymv(uplo, n, alpha, int(dA), ldda, int(dx), incx, beta,
                          int(dy), incy)

# SSYR, DSYR, CSYR, ZSYR
_libmagma.magma_ssyr.argtypes = [ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_float,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def magma_ssyr(uplo, n, alpha, dx, incx, dA, ldda):
    _libmagma.magma_ssyr(uplo, n, alpha, int(dx), incx, int(dA), ldda)

# SSYR2, DSYR2, CSYR2, ZSYR2
_libmagma.magma_ssyr2.argtypes = [ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_float,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def magma_ssyr2(uplo, n, alpha, dx, incx, dy, incy, dA, ldda):
    _libmagma.magma_ssyr2(uplo, n, alpha, int(dx), incx, 
                          int(dy), incy, int(dA), ldda)

# STRMV, DTRMV, CTRMV, ZTRMV
_libmagma.magma_strmv.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_strmv(uplo, trans, diag, n,
                dA, ldda, dx, incx):
    _libmagma.magma_strmv(uplo, trans, diag, n,
                          int(dA), ldda, int(dx), incx)                          

# STRSV, DTRSV, CTRSV, ZTRSV
_libmagma.magma_strsv.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_strsv(uplo, trans, diag, n,
                dA, ldda, dx, incx):
    _libmagma.magma_strsv(uplo, trans, diag, n,
                          int(dA), ldda, int(dx), incx)                          

# SGEMM, DGEMM, CGEMM, ZGEMM
_libmagma.magma_sgemm.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_sgemm(transA, transB, m, n, k, alpha, dA, ldda, dB, lddb, beta,
                dC, lddc):
    _libmagma.magma_sgemm(transA, transB, m, n, k, alpha, 
                          int(dA), ldda, int(dB), lddb,
                          beta, int(dC), lddc)

# SSYMM, DSYMM, CSYMM, ZSYMM
_libmagma.magma_ssymm.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_ssymm(side, uplo, m, n, alpha, dA, ldda, dB, lddb, beta,
                dC, lddc):
    _libmagma.magma_ssymm(side, uplo, m, n, alpha, 
                          int(dA), ldda, int(dB), lddb,
                          beta, int(dC), lddc)

# SSYRK, DSYRK, CSYRK, ZSYRK
_libmagma.magma_ssyrk.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_ssyrk(uplo, trans, n, k, alpha, dA, ldda, beta,
                dC, lddc):
    _libmagma.magma_ssyrk(uplo, trans, n, k, alpha, 
                          int(dA), ldda, beta, int(dC), lddc)

# SSYR2K, DSYR2K, CSYR2K, ZSYR2K
_libmagma.magma_ssyr2k.argtypes = [ctypes.c_char,
                                   ctypes.c_char,
                                   ctypes.c_int,
                                   ctypes.c_int,
                                   ctypes.c_float,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_float,
                                   ctypes.c_void_p,
                                   ctypes.c_int]
def magma_ssyr2k(uplo, trans, n, k, alpha, dA, ldda, 
                 dB, lddb, beta, dC, lddc):                
    _libmagma.magma_ssyr2k(uplo, trans, n, k, alpha, 
                           int(dA), ldda, int(dB), lddb, 
                           beta, int(dC), lddc)

# STRMM, DTRMM, CTRMM, ZTRMM
_libmagma.magma_strmm.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_strmm(side, uplo, trans, diag, m, n, alpha, dA, ldda, 
                dB, lddb):                
    _libmagma.magma_strmm(uplo, trans, diag, m, n, alpha, 
                          int(dA), ldda, int(dB), lddb)

# STRSM, DTRSM, CTRSM, ZTRSM
_libmagma.magma_strsm.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_float,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def magma_strsm(side, uplo, trans, diag, m, n, alpha, dA, ldda, 
                dB, lddb):                
    _libmagma.magma_strsm(uplo, trans, diag, m, n, alpha, 
                          int(dA), ldda, int(dB), lddb)


# Auxiliary routines:
_libmagma.magma_get_spotrf_nb.restype = int
_libmagma.magma_get_spotrf_nb.argtypes = [ctypes.c_int]
def magma_get_spotrf_nb(m):
    return _libmagma.magma_get_spotrf_nb(m)

_libmagma.magma_get_sgetrf_nb.restype = int
_libmagma.magma_get_sgetrf_nb.argtypes = [ctypes.c_int]
def magma_get_sgetrf_nb(m):
    return _libmagma.magma_get_sgetrf_nb(m)

_libmagma.magma_get_sgetri_nb.restype = int
_libmagma.magma_get_sgetri_nb.argtypes = [ctypes.c_int]
def magma_get_sgetri_nb(m):
    return _libmagma.magma_get_sgetri_nb(m)

_libmagma.magma_get_sgeqp3_nb.restype = int
_libmagma.magma_get_sgeqp3_nb.argtypes = [ctypes.c_int]
def magma_get_sgeqp3_nb(m):
    return _libmagma.magma_get_sgeqp3_nb(m)

_libmagma.magma_get_sgeqrf_nb.restype = int
_libmagma.magma_get_sgeqrf_nb.argtypes = [ctypes.c_int]
def magma_get_sgeqrf_nb(m):
    return _libmagma.magma_get_sgeqrf_nb(m)

_libmagma.magma_get_sgeqlf_nb.restype = int
_libmagma.magma_get_sgeqlf_nb.argtypes = [ctypes.c_int]
def magma_get_sgeqlf_nb(m):
    return _libmagma.magma_get_sgeqlf_nb(m)

_libmagma.magma_get_sgehrd_nb.restype = int
_libmagma.magma_get_sgehrd_nb.argtypes = [ctypes.c_int]
def magma_get_sgehrd_nb(m):
    return _libmagma.magma_get_sgehrd_nb(m)

_libmagma.magma_get_ssytrd_nb.restype = int
_libmagma.magma_get_ssytrd_nb.argtypes = [ctypes.c_int]
def magma_get_ssytrd_nb(m):
    return _libmagma.magma_get_ssytrd_nb(m)

_libmagma.magma_get_sgelqf_nb.restype = int
_libmagma.magma_get_sgelqf_nb.argtypes = [ctypes.c_int]
def magma_get_sgelqf_nb(m):
    return _libmagma.magma_get_sgelqf_nb(m)

_libmagma.magma_get_sgebrd_nb.restype = int
_libmagma.magma_get_sgebrd_nb.argtypes = [ctypes.c_int]
def magma_get_sgebrd_nb(m):
    return _libmagma.magma_get_sgebrd_nb(m)

_libmagma.magma_get_ssygst_nb.restype = int
_libmagma.magma_get_ssygst_nb.argtypes = [ctypes.c_int]
def magma_get_ssygst_nb(m):
    return _libmagma.magma_get_ssgyst_nb(m)

_libmagma.magma_get_sgesvd_nb.restype = int
_libmagma.magma_get_sgesvd_nb.argtypes = [ctypes.c_int]
def magma_get_sgesvd_nb(m):
    return _libmagma.magma_get_sgesvd_nb(m)

_libmagma.magma_get_ssygst_nb_m.restype = int
_libmagma.magma_get_ssygst_nb_m.argtypes = [ctypes.c_int]
def magma_get_ssygst_nb_m(m):
    return _libmagma.magma_get_ssgyst_nb_m(m)

_libmagma.magma_get_sbulge_nb.restype = int
_libmagma.magma_get_sbulge_nb.argtypes = [ctypes.c_int]
def magma_get_sbulge_nb(m):
    return _libmagma.magma_get_sbulge_nb(m)

_libmagma.magma_get_sbulge_nb_mgpu.restype = int
_libmagma.magma_get_sbulge_nb_mgpu.argtypes = [ctypes.c_int]
def magma_get_sbulge_nb_mgpu(m):
    return _libmagma.magma_get_sbulge_nb_mgpu(m)

# LAPACK routines

# SGEBRD, DGEBRD, CGEBRD, ZGEBRD
_libmagma.magma_sgebrd.restype = int
_libmagma.magma_sgebrd.argtypes = [ctypes.c_int,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p]
def magma_sgebrd(m, n, A, lda, d, e, tauq, taup, work, lwork, info):
    """
    Reduce matrix to bidiagonal form.
    """

    status = _libmagma.magma_sgebrd.argtypes(m, n, int(A), lda,
                                             int(d), int(e),
                                             int(tauq), int(taup),
                                             int(work), int(lwork),
                                             int(info))
    magmaCheckStatus(status)

# SGEHRD2, DGEHRD2, CGEHRD2, ZGEHRD2
_libmagma.magma_sgehrd2.restype = int
_libmagma.magma_sgehrd2.argtypes = [ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p]
def magma_sgehrd2(n, ilo, ihi, A, lda, tau,
                  work, lwork, info):
    """
    Reduce matrix to upper Hessenberg form.
    """
    
    status = _libmagma.magma_sgehrd2(n, ilo, ihi, int(A), lda,
                                     int(tau), int(work), 
                                     lwork, int(info))
    magmaCheckStatus(status)

# SGEHRD, DGEHRD, CGEHRD, ZGEHRD
_libmagma.magma_sgehrd.restype = int
_libmagma.magma_sgehrd.argtypes = [ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p]
def magma_sgehrd(n, ilo, ihi, A, lda, tau,
                 work, lwork, dT, info):
    """
    Reduce matrix to upper Hessenberg form (fast algorithm).
    """
    
    status = _libmagma.magma_sgehrd(n, ilo, ihi, int(A), lda,
                                    int(tau), int(work), 
                                    lwork, int(dT), int(info))
    magmaCheckStatus(status)

# SGELQF, DGELQF, CGELQF, ZGELQF
_libmagma.magma_sgelqf.restype = int
_libmagma.magma_sgelqf.argtypes = [ctypes.c_int,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p]
def magma_sgelqf(m, n, A, lda, tau, work, lwork, info):
                 
    """
    LQ factorization.
    """
    
    status = _libmagma.magma_sgelqf(m, n, int(A), lda,
                                    int(tau), int(work), 
                                    lwork, int(info))
    magmaCheckStatus(status)

# SGEQRF, DGEQRF, CGEQRF, ZGEQRF
_libmagma.magma_sgeqrf.restype = int
_libmagma.magma_sgeqrf.argtypes = [ctypes.c_int,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p]
def magma_sgeqrf(m, n, A, lda, tau, work, lwork, info):
                 
    """
    QR factorization.
    """
    
    status = _libmagma.magma_sgeqrf(m, n, int(A), lda,
                                    int(tau), int(work), 
                                    lwork, int(info))
    magmaCheckStatus(status)

# SGEQRF4, DGEQRF4, CGEQRF4, ZGEQRF4
_libmagma.magma_sgeqrf4.restype = int
_libmagma.magma_sgeqrf4.argtypes = [ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p]
def magma_sgeqrf4(num_gpus, m, n, a, lda, tau, work, lwork, info):
                 
    """

    """
    
    status = _libmagma.magma_sgeqrf4(num_gpus, m, n, int(a), lda,
                                    int(tau), int(work), 
                                    lwork, int(info))
    magmaCheckStatus(status)

# SGEQRF, DGEQRF, CGEQRF, ZGEQRF (ooc)
_libmagma.magma_sgeqrf_ooc.restype = int
_libmagma.magma_sgeqrf_ooc.argtypes = [ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p,
                                       ctypes.c_void_p,
                                       ctypes.c_int,
                                       ctypes.c_void_p]
def magma_sgeqrf_ooc(m, n, A, lda, tau, work, lwork, info):
                 
    """
    QR factorization (ooc).
    """
    
    status = _libmagma.magma_sgeqrf_ooc(m, n, int(A), lda,
                                        int(tau), int(work), 
                                        lwork, int(info))
    magmaCheckStatus(status)

# SGESV, DGESV, CGESV, ZGESV
_libmagma.magma_sgesv.restype = int
_libmagma.magma_sgesv.argtypes = [ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p]
def magma_sgesv(n, nhrs, A, lda, ipiv, B, ldb, info):
                 
    """
    Solve system of linear equations.
    """
    
    status = _libmagma.magma_sgesv(n, nhrs, int(A), lda,
                                   int(ipiv), int(B), 
                                   ldb, int(info))
    magmaCheckStatus(status)

# SGETRF, DGETRF, CGETRF, ZGETRF
_libmagma.magma_sgetrf.restype = int
_libmagma.magma_sgetrf.argtypes = [ctypes.c_int,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p]
def magma_sgetrf(m, n, A, lda, ipiv, info):
                 
    """
    LU factorization.
    """
    
    status = _libmagma.magma_sgetrf(m, n, int(A), lda,
                                    int(ipiv), int(info))   
    magmaCheckStatus(status)

# SGETRF2, DGETRF2, CGETRF2, ZGETRF2
_libmagma.magma_sgetrf2.restype = int
_libmagma.magma_sgetrf2.argtypes = [ctypes.c_int,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_int,
                                    ctypes.c_void_p,
                                    ctypes.c_void_p]
def magma_sgetrf2(m, n, A, lda, ipiv, info):
                 
    """
    LU factorization (multi-GPU).
    """
    
    status = _libmagma.magma_sgetrf2(m, n, int(A), lda,
                                    int(ipiv), int(info))
    magmaCheckStatus(status)

# SGEEV, DGEEV, CGEEV, ZGEEV
_libmagma.magma_sgeev.restype = int
_libmagma.magma_sgeev.argtypes = [ctypes.c_char,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p]
def magma_sgeev(jobvl, jobvr, n, a, lda,
                w, vl, ldvl, vr, ldvr, work, lwork, rwork, info):
                 
    """
    Compute eigenvalues and eigenvectors.
    """

    status = _libmagma.magma_sgeev(jobvl, jobvr, n, int(a), lda,
                                   int(w), int(vl), ldvl, int(vr), ldvr, 
                                   int(work), lwork, int(rwork), int(info))
    magmaCheckStatus(status)

# SGESVD, DGESVD, CGESVD, ZGESVD
_libmagma.magma_sgesvd.restype = int
_libmagma.magma_sgesvd.argtypes = [ctypes.c_char,
                                   ctypes.c_char,
                                   ctypes.c_int,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_int,
                                   ctypes.c_void_p,
                                   ctypes.c_void_p]
def magma_sgesvd(jobu, jobvt, m, n, a, lda, s, u, ldu, vt, ldvt, work, lwork,
                 rwork, info):
    """
    SVD decomposition.
    """

    status = _libmagma.magma_sgesvd(jobu, jobvt, m, n, 
                                    int(a), lda, int(s), int(u), ldu,
                                    int(vt), ldvt, int(work), lwork, 
                                    int(rwork), int(info))
    magmaCheckStatus(status)

########NEW FILE########
__FILENAME__ = misc
#!/usr/bin/env python

"""
Miscellaneous PyCUDA functions.
"""

import string
from string import Template
import atexit

import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
import pycuda.elementwise as elementwise
import pycuda.reduction as reduction
import pycuda.scan as scan
import pycuda.tools as tools
from pycuda.compiler import SourceModule
from pytools import memoize
import numpy as np

import cuda
import cublas

try:
    import cula
    _has_cula = True
except (ImportError, OSError):
    _has_cula = False

isdoubletype = lambda x : True if x == np.float64 or \
               x == np.complex128 else False
isdoubletype.__doc__ = """
Check whether a type has double precision.

Parameters
----------
t : numpy float type
    Type to test.

Returns
-------
result : bool
    Result.

"""

iscomplextype = lambda x : True if x == np.complex64 or \
                x == np.complex128 else False
iscomplextype.__doc__ = """
Check whether a type is complex.

Parameters
----------
t : numpy float type
    Type to test.

Returns
-------
result : bool
    Result.

"""

def init_device(n=0):
    """
    Initialize a GPU device.

    Initialize a specified GPU device rather than the default device
    found by `pycuda.autoinit`.

    Parameters
    ----------
    n : int
        Device number.

    Returns
    -------
    dev : pycuda.driver.Device
        Initialized device.

    """

    drv.init()
    dev = drv.Device(n)
    return dev

def init_context(dev):
    """
    Create a context that will be cleaned up properly.

    Create a context on the specified device and register its pop()
    method with atexit.

    Parameters
    ----------
    dev : pycuda.driver.Device
        GPU device.

    Returns
    -------
    ctx : pycuda.driver.Context
        Created context.

    """

    ctx = dev.make_context()
    atexit.register(ctx.pop)
    return ctx

def done_context(ctx):
    """
    Detach from a context cleanly.

    Detach from a context and remove its pop() from atexit.

    Parameters
    ----------
    ctx : pycuda.driver.Context
        Context from which to detach.

    """

    for i in xrange(len(atexit._exithandlers)):
        if atexit._exithandlers[i][0] == ctx.pop:
            del atexit._exithandlers[i]
            break
    ctx.detach()

global _global_cublas_handle
_global_cublas_handle = None
def init():
    """
    Initialize libraries used by scikits.cuda.

    Initialize the CUBLAS and CULA libraries used by high-level functions
    provided by scikits.cuda.
    
    Notes
    -----
    This function does not initialize PyCUDA; it uses whatever device
    and context were initialized in the current host thread.

    """

    # CUBLAS uses whatever device is being used by the host thread:
    global _global_cublas_handle
    if not _global_cublas_handle:
        _global_cublas_handle = cublas.cublasCreate()

    # culaSelectDevice() need not (and, in fact, cannot) be called
    # here because the host thread has already been bound to a GPU
    # device:
    if _has_cula:
        cula.culaInitialize()

def shutdown():
    """
    Shutdown libraries used by scikits.cuda.

    Shutdown the CUBLAS and CULA libraries used by high-level functions provided
    by scikits.cuda.

    Notes
    -----
    This function does not shutdown PyCUDA.

    """

    global _global_cublas_handle
    if _global_cublas_handle:
        cublas.cublasDestroy(_global_cublas_handle)
        _global_cublas_handle = None

    if _has_cula:
        cula.culaShutdown()    
    
def get_compute_capability(dev):
    """
    Get the compute capability of the specified device.

    Retrieve the compute capability of the specified CUDA device and
    return it as a floating point value.

    Parameters
    ----------
    d : pycuda.driver.Device
        Device object to examine.

    Returns
    -------
    c : float
        Compute capability.

    """

    return np.float(string.join([str(i) for i in
                                 dev.compute_capability()], '.'))

def get_current_device():
    """
    Get the device in use by the current context.

    Returns
    -------
    d : pycuda.driver.Device
        Device in use by current context.

    """

    return drv.Device(cuda.cudaGetDevice())

@memoize
def get_dev_attrs(dev):
    """
    Get select CUDA device attributes.

    Retrieve select attributes of the specified CUDA device that
    relate to maximum thread block and grid sizes.

    Parameters
    ----------
    d : pycuda.driver.Device
        Device object to examine.

    Returns
    -------
    attrs : list
        List containing [MAX_THREADS_PER_BLOCK,
        (MAX_BLOCK_DIM_X, MAX_BLOCK_DIM_Y, MAX_BLOCK_DIM_Z),
        (MAX_GRID_DIM_X, MAX_GRID_DIM_Y)]

    """

    attrs = dev.get_attributes()
    return [attrs[drv.device_attribute.MAX_THREADS_PER_BLOCK],
            (attrs[drv.device_attribute.MAX_BLOCK_DIM_X],
             attrs[drv.device_attribute.MAX_BLOCK_DIM_Y],
             attrs[drv.device_attribute.MAX_BLOCK_DIM_Z]),
            (attrs[drv.device_attribute.MAX_GRID_DIM_X],
            attrs[drv.device_attribute.MAX_GRID_DIM_Y])]

@memoize
def select_block_grid_sizes(dev, data_shape, threads_per_block=None):
    """
    Determine CUDA block and grid dimensions given device constraints.

    Determine the CUDA block and grid dimensions allowed by a GPU
    device that are sufficient for processing every element of an
    array in a separate thread.

    Parameters
    ----------
    d : pycuda.driver.Device
        Device object to be used.
    data_shape : tuple
        Shape of input data array. Must be of length 2.
    threads_per_block : int, optional
        Number of threads to execute in each block. If this is None,
        the maximum number of threads per block allowed by device `d`
        is used.

    Returns
    -------
    block_dim : tuple
        X, Y, and Z dimensions of minimal required thread block.
    grid_dim : tuple
        X and Y dimensions of minimal required block grid.

    Notes
    -----
    Using the scheme in this function, all of the threads in the grid can be enumerated
    as `i = blockIdx.y*max_threads_per_block*max_blocks_per_grid+
    blockIdx.x*max_threads_per_block+threadIdx.x`.

    For 2D shapes, the subscripts of the element `data[a, b]` where `data.shape == (A, B)`
    can be computed as
    `a = i/B`
    `b = mod(i,B)`.

    For 3D shapes, the subscripts of the element `data[a, b, c]` where
    `data.shape == (A, B, C)` can be computed as
    `a = i/(B*C)`
    `b = mod(i, B*C)/C`
    `c = mod(mod(i, B*C), C)`.

    For 4D shapes, the subscripts of the element `data[a, b, c, d]`
    where `data.shape == (A, B, C, D)` can be computed as
    `a = i/(B*C*D)`
    `b = mod(i, B*C*D)/(C*D)`
    `c = mod(mod(i, B*C*D)%(C*D))/D`
    `d = mod(mod(mod(i, B*C*D)%(C*D)), D)`

    It is advisable that the number of threads per block be a multiple
    of the warp size to fully utilize a device's computing resources.

    """

    # Sanity checks:
    if np.isscalar(data_shape):
        data_shape = (data_shape,)

    # Number of elements to process; we need to cast the result of
    # np.prod to a Python int to prevent PyCUDA's kernel execution
    # framework from getting confused when
    N = int(np.prod(data_shape))

    # Get device constraints:
    max_threads_per_block, max_block_dim, max_grid_dim = get_dev_attrs(dev)

    if threads_per_block != None:
        max_threads_per_block = threads_per_block

    # Assume that the maximum number of threads per block is no larger
    # than the maximum X and Y dimension of a thread block:
    assert max_threads_per_block <= max_block_dim[0]
    assert max_threads_per_block <= max_block_dim[1]

    # Actual number of thread blocks needed:
    blocks_needed = N/max_threads_per_block+1
    
    # Assume that the maximum X dimension of a grid
    # is always at least as large as the maximum Y dimension:
    assert max_grid_dim[0] >= max_grid_dim[1]

    if blocks_needed < max_block_dim[0]:
        grid_x = blocks_needed
        grid_y = 1
    elif blocks_needed < max_grid_dim[0]*max_grid_dim[1]:
        grid_x = max_grid_dim[0]
        grid_y = blocks_needed/max_grid_dim[0]+1
    else:
        raise ValueError('array size too large')

    return (max_threads_per_block, 1, 1), (grid_x, grid_y)

def zeros(shape, dtype, allocator=drv.mem_alloc):
    """
    Return an array of the given shape and dtype filled with zeros.

    Parameters
    ----------
    shape : tuple
        Array shape.
    dtype : data-type
        Data type for the array.
    allocator : callable
        Returns an object that represents the memory allocated for
        the requested array.

    Returns
    -------
    out : pycuda.gpuarray.GPUArray
        Array of zeros with the given shape and dtype.

    Notes
    -----
    This function exists to work around the following numpy bug that
    prevents pycuda.gpuarray.zeros() from working properly with
    complex types in pycuda 2011.1.2:
    http://projects.scipy.org/numpy/ticket/1898

    """

    out = gpuarray.GPUArray(shape, dtype, allocator)
    out.fill(0)
    return out

def zeros_like(a):
    """
    Return an array of zeros with the same shape and type as a given
    array.

    Parameters
    ----------
    a : array_like
        The shape and data type of `a` determine the corresponding
        attributes of the returned array.

    Returns
    -------
    out : pycuda.gpuarray.GPUArray
        Array of zeros with the shape and dtype of `a`.

    """

    out = gpuarray.GPUArray(a.shape, a.dtype, drv.mem_alloc)
    out.fill(0)
    return out

def ones(shape, dtype, allocator=drv.mem_alloc):
    """
    Return an array of the given shape and dtype filled with ones.

    Parameters
    ----------
    shape : tuple
        Array shape.
    dtype : data-type
        Data type for the array.
    allocator : callable
        Returns an object that represents the memory allocated for
        the requested array.

    Returns
    -------
    out : pycuda.gpuarray.GPUArray
        Array of ones with the given shape and dtype.

    """

    out = gpuarray.GPUArray(shape, dtype, allocator)
    out.fill(1)
    return out

def ones_like(other):
    """
    Return an array of ones with the same shape and type as a given array.

    Parameters
    ----------
    other : pycuda.gpuarray.GPUArray
        Array whose shape and dtype are to be used to allocate a new array.

    Returns
    -------
    out : pycuda.gpuarray.GPUArray
        Array of ones with the shape and dtype of `other`.

    """

    out = gpuarray.GPUArray(other.shape, other.dtype,
                            other.allocator)
    out.fill(1)
    return out

def inf(shape, dtype, allocator=drv.mem_alloc):
    """
    Return an array of the given shape and dtype filled with infs.

    Parameters
    ----------
    shape : tuple
        Array shape.
    dtype : data-type
        Data type for the array.
    allocator : callable
        Returns an object that represents the memory allocated for
        the requested array.

    Returns
    -------
    out : pycuda.gpuarray.GPUArray
        Array of infs with the given shape and dtype.

    """

    out = gpuarray.GPUArray(shape, dtype, allocator)
    out.fill(np.inf)
    return out

def maxabs(x_gpu):
    """
    Get maximum absolute value.

    Find maximum absolute value in the specified array.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.

    Returns
    -------
    m_gpu : pycuda.gpuarray.GPUArray
        Array containing maximum absolute value in `x_gpu`.        

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import misc
    >>> x_gpu = gpuarray.to_gpu(np.array([-1, 2, -3], np.float32))
    >>> m_gpu = misc.maxabs(x_gpu)
    >>> np.allclose(m_gpu.get(), 3.0)
    True

    """

    try:
        func = maxabs.cache[x_gpu.dtype]
    except KeyError:
        ctype = tools.dtype_to_ctype(x_gpu.dtype)
        use_double = int(x_gpu.dtype in [np.float64, np.complex128])        
        ret_type = np.float64 if use_double else np.float32
        func = reduction.ReductionKernel(ret_type, neutral="0",
                                           reduce_expr="max(a,b)", 
                                           map_expr="abs(x[i])",
                                           arguments="{ctype} *x".format(ctype=ctype))
        maxabs.cache[x_gpu.dtype] = func
    return func(x_gpu)
maxabs.cache = {}

def cumsum(x_gpu):
    """
    Cumulative sum.

    Return the cumulative sum of the elements in the specified array.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input array.

    Returns
    -------
    c_gpu : pycuda.gpuarray.GPUArray
        Output array containing cumulative sum of `x_gpu`.

    Notes
    -----
    Higher dimensional arrays are implicitly flattened row-wise by this function.

    Examples
    --------
    >>> import pycuda.autoinit
    >>> import pycuda.gpuarray as gpuarray
    >>> import misc
    >>> x_gpu = gpuarray.to_gpu(np.random.rand(5).astype(np.float32))
    >>> c_gpu = misc.cumsum(x_gpu)
    >>> np.allclose(c_gpu.get(), np.cumsum(x_gpu.get()))
    True

    """

    try:
        func = cumsum.cache[x_gpu.dtype]
    except KeyError:
        func = scan.InclusiveScanKernel(x_gpu.dtype, 'a+b',
                                        preamble='#include <pycuda-complex.hpp>')
        cumsum.cache[x_gpu.dtype] = func
    return func(x_gpu)
cumsum.cache = {}

def diff(x_gpu):
    """
    Calculate the discrete difference.

    Calculates the first order difference between the successive
    entries of a vector.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        Input vector.

    Returns
    -------
    y_gpu : pycuda.gpuarray.GPUArray
        Discrete difference.

    Examples
    --------
    >>> import pycuda.driver as drv
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import misc
    >>> x = np.asarray(np.random.rand(5), np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> y_gpu = misc.diff(x_gpu)
    >>> np.allclose(np.diff(x), y_gpu.get())
    True

    """

    y_gpu = gpuarray.empty(len(x_gpu)-1, x_gpu.dtype)
    try:
        func = diff.cache[x_gpu.dtype]
    except KeyError:
        ctype = tools.dtype_to_ctype(x_gpu.dtype)
        func = elementwise.ElementwiseKernel("{ctype} *a, {ctype} *b".format(ctype=ctype),
                                             "b[i] = a[i+1]-a[i]")
        diff.cache[x_gpu.dtype] = func
    func(x_gpu, y_gpu)
    return y_gpu
diff.cache = {}
        
# List of available numerical types provided by numpy:
num_types = [np.typeDict[t] for t in \
             np.typecodes['AllInteger']+np.typecodes['AllFloat']]

# Numbers of bytes occupied by each numerical type:
num_nbytes = dict((np.dtype(t),t(1).nbytes) for t in num_types)

def set_realloc(x_gpu, data):
    """
    Transfer data into a GPUArray instance.

    Copies the contents of a numpy array into a GPUArray instance. If
    the array has a different type or dimensions than the instance,
    the GPU memory used by the instance is reallocated and the
    instance updated appropriately.

    Parameters
    ----------
    x_gpu : pycuda.gpuarray.GPUArray
        GPUArray instance to modify.
    data : numpy.ndarray
        Array of data to transfer to the GPU.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import misc
    >>> x = np.asarray(np.random.rand(5), np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> x = np.asarray(np.random.rand(10, 1), np.float64)
    >>> set_realloc(x_gpu, x)
    >>> np.allclose(x, x_gpu.get())
    True

    """

    # Only reallocate if absolutely necessary:
    if x_gpu.shape != data.shape or x_gpu.size != data.size or \
        x_gpu.strides != data.strides or x_gpu.dtype != data.dtype:

        # Free old memory:
        x_gpu.gpudata.free()

        # Allocate new memory:
        nbytes = num_nbytes[data.dtype]
        x_gpu.gpudata = drv.mem_alloc(nbytes*data.size)

        # Set array attributes:
        x_gpu.shape = data.shape
        x_gpu.size = data.size
        x_gpu.strides = data.strides
        x_gpu.dtype = data.dtype

    # Update the GPU memory:
    x_gpu.set(data)
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = pcula
#!/usr/bin/env/python

"""
Python interface to multi-GPU CULA toolkit functions.
"""

import ctypes
import sys

import cuda
from cula import culaCheckStatus

if sys.platform == 'linux2':
    _libpcula_libname_list = ['libcula_scalapack.so']
elif sys.platform == 'darwin':
    _libpcula_libname_list = ['libcula_scalapack.dylib']
else:
    raise RuntimeError('unsupported platform')

_load_err = ''
for _lib in  _libpcula_libname_list:
    try:
        _libpcula = ctypes.cdll.LoadLibrary(_lib)
    except OSError:
        _load_err += ('' if _load_err == '' else ', ') + _lib
    else:
        _load_err = ''
        break
if _load_err:
    raise OSError('%s not found' % _load_err)

class pculaConfig(ctypes.Structure):
    _fields_ = [
        ('ncuda', ctypes.c_int),
        ('cudaDeviceList', ctypes.c_void_p),
        ('maxCudaMemoryUsage', ctypes.c_void_p),
        ('preserveTuningResult', ctypes.c_int),
        ('dotFileName', ctypes.c_char_p),
        ('timelineFileName', ctypes.c_char_p)]

_libpcula.pculaConfigInit.restype = int
_libpcula.pculaConfigInit.argtypes = [ctypes.c_void_p]
def pculaConfigInit(config):
    """
    Initialize pCULA configuration structure to sensible defaults.
    """

    status = _libpcula.pculaConfigInit(ctypes.byref(config))
    culaCheckStatus(status)

# SGEMM, DGEMM, CGEMM, ZGEMM
_libpcula.pculaSgemm.restype = int
_libpcula.pculaSgemm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_float,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_float,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaSgemm(config, transa, transb, m, n, k, alpha, A, lda, B, ldb,
               beta, C, ldc):
    """
    Matrix-matrix product for general matrix.

    """

    status = _libpcula.pculaSgemm(ctypes.byref(config), transa, transb, m, n, k, alpha, 
                                  int(A), lda, int(B), ldb, beta, int(C), ldc)
    culaCheckStatus(status)

_libpcula.pculaDgemm.restype = int
_libpcula.pculaDgemm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_double,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_double,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaDgemm(config, transa, transb, m, n, k, alpha, A, lda, B, ldb,
               beta, C, ldc):
    """
    Matrix-matrix product for general matrix.

    """

    status = _libpcula.pculaDgemm(ctypes.byref(config), transa, transb, m, n, k, alpha, 
                                  int(A), lda, int(B), ldb, beta, int(C), ldc)
    culaCheckStatus(status)

_libpcula.pculaCgemm.restype = int
_libpcula.pculaCgemm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 cuda.cuFloatComplex,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 cuda.cuFloatComplex,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaCgemm(config, transa, transb, m, n, k, alpha, A, lda, B, ldb,
               beta, C, ldc):
    """
    Matrix-matrix product for general matrix.

    """

    status = _libpcula.pculaCgemm(ctypes.byref(config), transa, transb, m, n, k, alpha, 
                                  int(A), lda, int(B), ldb, beta, int(C), ldc)
    culaCheckStatus(status)

_libpcula.pculaZgemm.restype = int
_libpcula.pculaZgemm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 cuda.cuDoubleComplex,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 cuda.cuDoubleComplex,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaZgemm(config, transa, transb, m, n, k, alpha, A, lda, B, ldb,
               beta, C, ldc):
    """
    Matrix-matrix product for general matrix.

    """

    status = _libpcula.pculaZgemm(ctypes.byref(config), transa, transb, m, n, k, alpha, 
                                  int(A), lda, int(B), ldb, beta, int(C), ldc)
    culaCheckStatus(status)

# STRSM, DTRSM, CTRSM, ZTRSM
_libpcula.pculaStrsm.restype = int
_libpcula.pculaStrsm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_float,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaStrsm(config, side, uplo, transa, diag, m, n, alpha, a, lda, b, ldb):
    """
    Triangular system solve.

    """

    status = _libpcula.pculaStrsm(ctypes.byref(config), side, uplo, transa,
                                  diag, m, n, alpha, int(a), lda, int(b), ldb)                                  
    culaCheckStatus(status)

_libpcula.pculaDtrsm.restype = int
_libpcula.pculaDtrsm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_double,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaDtrsm(config, side, uplo, transa, diag, m, n, alpha, a, lda, b, ldb):
    """
    Triangular system solve.

    """

    status = _libpcula.pculaDtrsm(ctypes.byref(config), side, uplo, transa,
                                  diag, m, n, alpha, int(a), lda, int(b), ldb)                                  
    culaCheckStatus(status)

_libpcula.pculaCtrsm.restype = int
_libpcula.pculaCtrsm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 cuda.cuFloatComplex,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaCtrsm(config, side, uplo, transa, diag, m, n, alpha, a, lda, b, ldb):
    """
    Triangular system solve.

    """

    status = _libpcula.pculaCtrsm(ctypes.byref(config), side, uplo, transa,
                                  diag, m, n, alpha, int(a), lda, int(b), ldb)                                  
    culaCheckStatus(status)

_libpcula.pculaZtrsm.restype = int
_libpcula.pculaZtrsm.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 cuda.cuDoubleComplex,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaZtrsm(config, side, uplo, transa, diag, m, n, alpha, a, lda, b, ldb):
    """
    Triangular system solve.

    """

    status = _libpcula.pculaZtrsm(ctypes.byref(config), side, uplo, transa,
                                  diag, m, n, alpha, int(a), lda, int(b), ldb)                                  
    culaCheckStatus(status)

# SGESV, DGESV, CGESV, ZGESV
_libpcula.pculaSgesv.restype = int
_libpcula.pculaSgesv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaSgesv(config, n, nrhs, a, lda, ipiv, b, ldb):
    """
    General system solve using LU decomposition.

    """

    status = _libpcula.pculaSgesv(ctypes.byref(config), n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaDgesv.restype = int
_libpcula.pculaDgesv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaDgesv(config, n, nrhs, a, lda, ipiv, b, ldb):
    """
    General system solve using LU decomposition.

    """

    status = _libpcula.pculaDgesv(ctypes.byref(config), n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaCgesv.restype = int
_libpcula.pculaCgesv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaCgesv(config, n, nrhs, a, lda, ipiv, b, ldb):
    """
    General system solve using LU decomposition.

    """

    status = _libpcula.pculaCgesv(ctypes.byref(config), n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaZgesv.restype = int
_libpcula.pculaZgesv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaZgesv(config, n, nrhs, a, lda, ipiv, b, ldb):
    """
    General system solve using LU decomposition.

    """

    status = _libpcula.pculaZgesv(ctypes.byref(config), n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

# SGETRF, DGETRF, CGETRF, ZGETRF
_libpcula.pculaSgetrf.restype = int
_libpcula.pculaSgetrf.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p]
def pculaSgetrf(config, m, n, a, lda, ipiv):
    """
    LU decomposition.

    """

    status = _libpcula.pculaSgetrf(ctypes.byref(config), m, n, int(a), lda,
                                  int(ipiv))
    culaCheckStatus(status)

_libpcula.pculaDgetrf.restype = int
_libpcula.pculaDgetrf.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p]
def pculaDgetrf(config, m, n, a, lda, ipiv):
    """
    LU decomposition.

    """

    status = _libpcula.pculaDgetrf(ctypes.byref(config), m, n, int(a), lda,
                                  int(ipiv))
    culaCheckStatus(status)

_libpcula.pculaCgetrf.restype = int
_libpcula.pculaCgetrf.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p]
def pculaCgetrf(config, m, n, a, lda, ipiv):
    """
    LU decomposition.

    """

    status = _libpcula.pculaCgetrf(ctypes.byref(config), m, n, int(a), lda,
                                  int(ipiv))
    culaCheckStatus(status)

_libpcula.pculaZgetrf.restype = int
_libpcula.pculaZgetrf.argtypes = [ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p]
def pculaZgetrf(config, m, n, a, lda, ipiv):
    """
    LU decomposition.

    """

    status = _libpcula.pculaZgetrf(ctypes.byref(config), m, n, int(a), lda,
                                  int(ipiv))
    culaCheckStatus(status)

# SGETRS, DGETRS, CGETRS, ZGETRS
_libpcula.pculaSgetrs.restype = int
_libpcula.pculaSgetrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaSgetrs(config, trans, n, nrhs, a, lda, ipiv, b, ldb):
    """
    LU solve.

    """

    status = _libpcula.pculaSgetrs(ctypes.byref(config), trans, n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaDgetrs.restype = int
_libpcula.pculaDgetrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaDgetrs(config, trans, n, nrhs, a, lda, ipiv, b, ldb):
    """
    LU solve.

    """

    status = _libpcula.pculaDgetrs(ctypes.byref(config), trans, n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaCgetrs.restype = int
_libpcula.pculaCgetrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaCgetrs(config, trans, n, nrhs, a, lda, ipiv, b, ldb):
    """
    LU solve.

    """

    status = _libpcula.pculaCgetrs(ctypes.byref(config), trans, n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaZgetrs.restype = int
_libpcula.pculaZgetrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaZgetrs(config, trans, n, nrhs, a, lda, ipiv, b, ldb):
    """
    LU solve.

    """

    status = _libpcula.pculaZgetrs(ctypes.byref(config), trans, n, nrhs, int(a), lda,
                                  int(ipiv), int(b), ldb)
    culaCheckStatus(status)

# SPOSV, DPOSV, CPOSV, ZPOSV
_libpcula.pculaSposv.restype = int
_libpcula.pculaSposv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaSposv(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    QR factorization.

    """

    status = _libpcula.pculaSposv(ctypes.byref(config), uplo, n, nrhs, int(a), lda,
                                   int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaDposv.restype = int
_libpcula.pculaDposv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaDposv(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    QR factorization.

    """

    status = _libpcula.pculaDposv(ctypes.byref(config), uplo, n, nrhs, int(a), lda,
                                   int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaCposv.restype = int
_libpcula.pculaCposv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaCposv(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    QR factorization.

    """

    status = _libpcula.pculaCposv(ctypes.byref(config), uplo, n, nrhs, int(a), lda,
                                   int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaZposv.restype = int
_libpcula.pculaZposv.argtypes = [ctypes.c_void_p,
                                 ctypes.c_char,
                                 ctypes.c_int,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int,
                                 ctypes.c_void_p,
                                 ctypes.c_int]
def pculaZposv(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    QR factorization.

    """

    status = _libpcula.pculaZposv(ctypes.byref(config), uplo, n, nrhs, int(a), lda,
                                   int(b), ldb)
    culaCheckStatus(status)

# SPOTRF, DPOTRF, CPOTRF, ZPOTRF
_libpcula.pculaSpotrf.restype = int
_libpcula.pculaSpotrf.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaSpotrf(config, uplo, n, a, lda):
    """
    Cholesky decomposition.

    """

    status = _libpcula.pculaSpotrf(ctypes.byref(config), uplo, n, int(a), lda)
    culaCheckStatus(status)

_libpcula.pculaDpotrf.restype = int
_libpcula.pculaDpotrf.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaDpotrf(config, uplo, n, a, lda):
    """
    Cholesky decomposition.

    """

    status = _libpcula.pculaDpotrf(ctypes.byref(config), uplo, n, int(a), lda)
    culaCheckStatus(status)

_libpcula.pculaCpotrf.restype = int
_libpcula.pculaCpotrf.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaCpotrf(config, uplo, n, a, lda):
    """
    Cholesky decomposition.

    """

    status = _libpcula.pculaCpotrf(ctypes.byref(config), uplo, n, int(a), lda)
    culaCheckStatus(status)

_libpcula.pculaZpotrf.restype = int
_libpcula.pculaZpotrf.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaZpotrf(config, uplo, n, a, lda):
    """
    Cholesky decomposition.

    """

    status = _libpcula.pculaZpotrf(ctypes.byref(config), uplo, n, int(a), lda)
    culaCheckStatus(status)

# SPOTRS, DPOTRS, CPOTRS, ZPOTRS
_libpcula.pculaSpotrs.restype = int
_libpcula.pculaSpotrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaSpotrs(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    Cholesky solve.

    """

    status = _libpcula.pculaSpotrs(ctypes.byref(config), uplo, n, nrhs, int(a),
                                   lda, int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaDpotrs.restype = int
_libpcula.pculaDpotrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaDpotrs(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    Cholesky solve.

    """

    status = _libpcula.pculaDpotrs(ctypes.byref(config), uplo, n, nrhs, int(a),
                                   lda, int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaCpotrs.restype = int
_libpcula.pculaCpotrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaCpotrs(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    Cholesky solve.

    """

    status = _libpcula.pculaCpotrs(ctypes.byref(config), uplo, n, nrhs, int(a),
                                   lda, int(b), ldb)
    culaCheckStatus(status)

_libpcula.pculaZpotrs.restype = int
_libpcula.pculaZpotrs.argtypes = [ctypes.c_void_p,
                                  ctypes.c_char,
                                  ctypes.c_int,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int,
                                  ctypes.c_void_p,
                                  ctypes.c_int]
def pculaZpotrs(config, uplo, n, nrhs, a, lda, b, ldb):
    """
    Cholesky solve.

    """

    status = _libpcula.pculaZpotrs(ctypes.byref(config), uplo, n, nrhs, int(a),
                                   lda, int(b), ldb)
    culaCheckStatus(status)

########NEW FILE########
__FILENAME__ = special
#!/usr/bin/env python

"""
PyCUDA-based special functions.
"""

import os
import pycuda.gpuarray as gpuarray
import pycuda.elementwise as elementwise
import numpy as np

import misc

from misc import init

# Get installation location of C headers:
from . import install_headers

def sici(x_gpu):
    """
    Sine/Cosine integral.

    Computes the sine and cosine integral of every element in the
    input matrix.

    Parameters
    ----------
    x_gpu : GPUArray
        Input matrix of shape `(m, n)`.
        
    Returns
    -------
    (si_gpu, ci_gpu) : tuple of GPUArrays
        Tuple of GPUarrays containing the sine integrals and cosine
        integrals of the entries of `x_gpu`.
        
    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import scipy.special
    >>> import special
    >>> x = np.array([[1, 2], [3, 4]], np.float32)
    >>> x_gpu = gpuarray.to_gpu(x)
    >>> (si_gpu, ci_gpu) = sici(x_gpu)
    >>> (si, ci) = scipy.special.sici(x)
    >>> np.allclose(si, si_gpu.get())
    True
    >>> np.allclose(ci, ci_gpu.get())
    True
    """

    if x_gpu.dtype == np.float32:
        args = 'float *x, float *si, float *ci'
        op = 'sicif(x[i], &si[i], &ci[i])'
    elif x_gpu.dtype == np.float64:
        args = 'double *x, double *si, double *ci'
        op = 'sici(x[i], &si[i], &ci[i])'
    else:
        raise ValueError('unsupported type')
    
    try:
        func = sici.cache[x_gpu.dtype]
    except KeyError:
        func = elementwise.ElementwiseKernel(args, op,
                                 options=["-I", install_headers],
                                 preamble='#include "cuSpecialFuncs.h"')
        sici.cache[x_gpu.dtype] = func

    si_gpu = gpuarray.empty_like(x_gpu)
    ci_gpu = gpuarray.empty_like(x_gpu)
    func(x_gpu, si_gpu, ci_gpu)
        
    return (si_gpu, ci_gpu)
sici.cache = {}

def exp1(z_gpu):
    """
    Exponential integral with `n = 1` of complex arguments.

    Parameters
    ----------
    z_gpu : GPUArray
        Input matrix of shape `(m, n)`.
        
    Returns
    -------
    e_gpu : GPUArray
        GPUarrays containing the exponential integrals of
        the entries of `z_gpu`.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import scipy.special
    >>> import special
    >>> z = np.asarray(np.random.rand(4, 4)+1j*np.random.rand(4, 4), np.complex64)
    >>> z_gpu = gpuarray.to_gpu(z)
    >>> e_gpu = exp1(z_gpu)
    >>> e_sp = scipy.special.exp1(z)
    >>> np.allclose(e_sp, e_gpu.get())
    True
    """

    if z_gpu.dtype == np.complex64:
        args = 'pycuda::complex<float> *z, pycuda::complex<float> *e' 
    elif z_gpu.dtype == np.complex128:
        args = 'pycuda::complex<double> *z, pycuda::complex<double> *e' 
    else:
        raise ValueError('unsupported type')
    op = 'e[i] = exp1(z[i])'
    
    try:
        func = exp1.cache[z_gpu.dtype]
    except KeyError:
        func = elementwise.ElementwiseKernel(args, op,
                                 options=["-I", install_headers],
                                 preamble='#include "cuSpecialFuncs.h"')
        exp1.cache[z_gpu.dtype] = func

    e_gpu = gpuarray.empty_like(z_gpu)
    func(z_gpu, e_gpu)

    return e_gpu
exp1.cache = {}

def expi(z_gpu):
    """
    Exponential integral of complex arguments.

    Parameters
    ----------
    z_gpu : GPUArray
        Input matrix of shape `(m, n)`.
        
    Returns
    -------
    e_gpu : GPUArray
        GPUarrays containing the exponential integrals of
        the entries of `z_gpu`.

    Examples
    --------
    >>> import pycuda.gpuarray as gpuarray
    >>> import pycuda.autoinit
    >>> import numpy as np
    >>> import scipy.special
    >>> import special
    >>> z = np.asarray(np.random.rand(4, 4)+1j*np.random.rand(4, 4), np.complex64)
    >>> z_gpu = gpuarray.to_gpu(z)
    >>> e_gpu = expi(z_gpu)
    >>> e_sp = scipy.special.expi(z)
    >>> np.allclose(e_sp, e_gpu.get())
    True
    """

    if z_gpu.dtype == np.complex64:
        args = 'pycuda::complex<float> *z, pycuda::complex<float> *e' 
    elif z_gpu.dtype == np.complex128:
        args = 'pycuda::complex<double> *z, pycuda::complex<double> *e' 
    else:
        raise ValueError('unsupported type')
    op = 'e[i] = expi(z[i])'
   
    try:
        func = expi.cache[z_gpu.dtype]
    except KeyError:
        func = elementwise.ElementwiseKernel(args, op,
                                 options=["-I", install_headers],
                                 preamble='#include "cuSpecialFuncs.h"')
        expi.cache[z_gpu.dtype] = func

    e_gpu = gpuarray.empty_like(z_gpu)
    func(z_gpu, e_gpu)

    return e_gpu
expi.cache = {}
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

"""
Utility functions.
"""

import sys
import ctypes
import os
import re
import subprocess
import struct

try:
    import elftools
except ImportError:
    import re

    
    def get_soname(filename):
        """
        Retrieve SONAME of shared library.

        Parameters
        ----------
        filename : str
            Full path to shared library.

        Returns
        -------
        soname : str
            SONAME of shared library.

        Notes
        -----
        This function uses the `objdump` system command on linux and
        'otool' on Mac OS X (darwin).
        
        """
        if sys.platform == 'darwin':
            cmds = ['otool', '-L', filename]
        else:
            # Fallback to linux... what about windows?
            cmds = ['objdump', '-p', filename]

        try:
            p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
            out = p.communicate()[0]
        except:
            raise RuntimeError('error executing {0}'.format(cmds))

        if sys.platform == 'darwin':
            result = re.search('^\s@rpath/(lib.+.dylib)', out, re.MULTILINE)
        else:
            result = re.search('^\s+SONAME\s+(.+)$',out,re.MULTILINE)
        
        if result:
            return result.group(1)
        else:
            # No SONAME found:
            raise RuntimeError('no library name found for {0}'.format(
                (filename,)))

else:
    import ctypes
    import elftools.elf.elffile as elffile
    import elftools.construct.macros as macros
    import elftools.elf.structs as structs

    def get_soname(filename):
        """
        Retrieve SONAME of shared library.

        Parameters
        ----------
        filename : str
            Full path to shared library.

        Returns
        -------
        soname : str
            SONAME of shared library.

        Notes
        -----
        This function uses the pyelftools [ELF] package.

        References
        ----------
        .. [ELF] http://pypi.python.org/pypi/pyelftools
        
        """

        stream = open(filename, 'rb')
        f = elffile.ELFFile(stream)
        dynamic = f.get_section_by_name('.dynamic')
        dynstr = f.get_section_by_name('.dynstr')

        # Handle libraries built for different machine architectures:         
        if f.header['e_machine'] == 'EM_X86_64':
            st = structs.Struct('Elf64_Dyn',
                                macros.ULInt64('d_tag'),
                                macros.ULInt64('d_val'))
        elif f.header['e_machine'] == 'EM_386':
            st = structs.Struct('Elf32_Dyn',
                                macros.ULInt32('d_tag'),
                                macros.ULInt32('d_val'))
        else:
            raise RuntimeError('unsupported machine architecture')

        entsize = dynamic['sh_entsize']
        for k in xrange(dynamic['sh_size']/entsize):
            result = st.parse(dynamic.data()[k*entsize:(k+1)*entsize])

            # The following value for the SONAME tag is specified in elf.h:  
            if result.d_tag == 14:
                return dynstr.get_string(result.d_val)

        # No SONAME found:
        return ''

def find_lib_path(name):
    """
    Find full path of a shared library.

    Searches for the full path of a shared library in the directories
    listed in LD_LIBRARY_PATH (if any) and in the ld.so cache.

    Parameter
    ---------
    name : str
        Link name of library, e.g., cublas for libcublas.so.*.

    Returns
    -------
    path : str
        Full path to library.

    Notes
    -----
    Code adapted from ctypes.util module. Doesn't check whether the 
    architectures of libraries found in LD_LIBRARY_PATH directories conform
    to that of the machine.
    """

    # First, check the directories in LD_LIBRARY_PATH:
    expr = r'\s+(lib%s\.[^\s]+)\s+\-\>' % re.escape(name)
    for dir_path in os.environ['LD_LIBRARY_PATH'].split(':'):
        f = os.popen('/sbin/ldconfig -Nnv %s 2>/dev/null' % dir_path)
        try:
            data = f.read()
        finally:
            f.close()
        res = re.search(expr, data)
        if res:
            return os.path.join(dir_path, res.group(1))

    # Next, check the ld.so cache:
    uname = os.uname()[4]
    if uname.startswith("arm"):
        uname = "arm"
    if struct.calcsize('l') == 4:
        machine = uname + '-32'
    else:
        machine = uname + '-64'
    mach_map = {
        'x86_64-64': 'libc6,x86-64',
        'ppc64-64': 'libc6,64bit',
        'sparc64-64': 'libc6,64bit',
        's390x-64': 'libc6,64bit',
        'ia64-64': 'libc6,IA-64',
        'arm-32': 'libc6(,hard-float)?',
        }
    abi_type = mach_map.get(machine, 'libc6')
    expr = r'\s+lib%s\.[^\s]+\s+\(%s.*\=\>\s(.+)' % (re.escape(name), abi_type)
    f = os.popen('/sbin/ldconfig -p 2>/dev/null')
    try:
        data = f.read()
    finally:
        f.close()
    res = re.search(expr, data)
    if not res:
        return None
    return res.group(1)

########NEW FILE########
__FILENAME__ = version
import pkg_resources
__version__ = pkg_resources.require('scikits.cuda')[0].version 

########NEW FILE########
__FILENAME__ = test_cublas
#!/usr/bin/env python

"""
Unit tests for scikits.cuda.cublas
"""



from unittest import main, makeSuite, TestCase, TestSuite

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

_SEPS = np.finfo(np.float32).eps
_DEPS = np.finfo(np.float64).eps

import scikits.cuda.cublas as cublas
import scikits.cuda.misc as misc
    
def bptrs(a):
    """
    Pointer array when input represents a batch of matrices.
    """
    
    return gpuarray.arange(a.ptr,a.ptr+a.shape[0]*a.strides[0],a.strides[0],
                dtype=cublas.ctypes.c_void_p)

class test_cublas(TestCase):
    def setUp(self):
        np.random.seed(23)    # For reproducible tests.
        self.cublas_handle = cublas.cublasCreate()

    def tearDown(self):
        cublas.cublasDestroy(self.cublas_handle)
        
    # ISAMAX, IDAMAX, ICAMAX, IZAMAX
    def test_cublasIsamax(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIsamax(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmax(x))

    def test_cublasIdamax(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIdamax(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmax(x))

    def test_cublasIcamax(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIcamax(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmax(np.abs(x.real) + np.abs(x.imag)))

    def test_cublasIzamax(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIzamax(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmax(np.abs(x.real) + np.abs(x.imag)))

    # ISAMIN, IDAMIN, ICAMIN, IZAMIN
    def test_cublasIsamin(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIsamin(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmin(x))

    def test_cublasIdamin(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIdamin(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmin(x))

    def test_cublasIcamin(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIcamin(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmin(np.abs(x.real) + np.abs(x.imag)))

    def test_cublasIzamin(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasIzamin(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.argmin(np.abs(x.real) + np.abs(x.imag)))

    # SASUM, DASUM, SCASUM, DZASUM
    def test_cublasSasum(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasSasum(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.sum(np.abs(x)))

    def test_cublasDasum(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasDasum(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.sum(np.abs(x)))

    def test_cublasScasum(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasScasum(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.sum(np.abs(x.real)+np.abs(x.imag)))

    def test_cublasDzasum(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasDzasum(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.sum(np.abs(x.real)+np.abs(x.imag)))

    # SAXPY, DAXPY, CAXPY, ZAXPY
    def test_cublasSaxpy(self):
        alpha = np.float32(np.random.rand())
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        y = np.random.rand(5).astype(np.float32)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasSaxpy(self.cublas_handle, x_gpu.size, alpha, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), alpha*x+y)

    def test_cublasDaxpy(self):
        alpha = np.float64(np.random.rand())
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        y = np.random.rand(5).astype(np.float64)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasDaxpy(self.cublas_handle, x_gpu.size, alpha, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), alpha*x+y)

    def test_cublasCaxpy(self):
        alpha = np.complex64(np.random.rand()+1j*np.random.rand())
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasCaxpy(self.cublas_handle, x_gpu.size, alpha, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), alpha*x+y)

    def test_cublasZaxpy(self):
        alpha = np.complex128(np.random.rand()+1j*np.random.rand())
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasZaxpy(self.cublas_handle, x_gpu.size, alpha, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), alpha*x+y)

    # SCOPY, DCOPY, CCOPY, ZCOPY
    def test_cublasScopy(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.zeros_like(x_gpu)
        cublas.cublasScopy(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), x_gpu.get())

    def test_cublasDcopy(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.zeros_like(x_gpu)
        cublas.cublasDcopy(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), x_gpu.get())

    def test_cublasCcopy(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = misc.zeros_like(x_gpu)
        cublas.cublasCcopy(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), x_gpu.get())

    def test_cublasZcopy(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = misc.zeros_like(x_gpu)
        cublas.cublasZcopy(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), x_gpu.get())

    # SDOT, DDOT, CDOTU, CDOTC, ZDOTU, ZDOTC
    def test_cublasSdot(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        y = np.random.rand(5).astype(np.float32)
        y_gpu = gpuarray.to_gpu(y)
        result = cublas.cublasSdot(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                                   y_gpu.gpudata, 1)
        assert np.allclose(result, np.dot(x, y))

    def test_cublasDdot(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        y = np.random.rand(5).astype(np.float64)
        y_gpu = gpuarray.to_gpu(y)
        result = cublas.cublasDdot(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                                   y_gpu.gpudata, 1)
        assert np.allclose(result, np.dot(x, y))

    def test_cublasCdotu(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        y_gpu = gpuarray.to_gpu(y)
        result = cublas.cublasCdotu(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                                    y_gpu.gpudata, 1)
        assert np.allclose(result, np.dot(x, y))

    def test_cublasCdotc(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        y_gpu = gpuarray.to_gpu(y)
        result = cublas.cublasCdotc(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                                    y_gpu.gpudata, 1)
        assert np.allclose(result, np.dot(np.conj(x), y))

    def test_cublasZdotu(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        y_gpu = gpuarray.to_gpu(y)
        result = cublas.cublasZdotu(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                                    y_gpu.gpudata, 1)
        assert np.allclose(result, np.dot(x, y))

    def test_cublasZdotc(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        y_gpu = gpuarray.to_gpu(y)
        result = cublas.cublasZdotc(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                                    y_gpu.gpudata, 1)
        assert np.allclose(result, np.dot(np.conj(x), y))

    # SNRM2, DNRM2, SCNRM2, DZNRM2
    def test_cublasSrnm2(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasSnrm2(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.linalg.norm(x))

    def test_cublasDrnm2(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasDnrm2(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.linalg.norm(x))

    def test_cublasScrnm2(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasScnrm2(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.linalg.norm(x))

    def test_cublasDzrnm2(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        result = cublas.cublasDznrm2(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1)
        assert np.allclose(result, np.linalg.norm(x))

    # SSCAL, DSCAL, CSCAL, CSSCAL, ZSCAL, ZDSCAL
    def test_cublasSscal(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        alpha = np.float32(np.random.rand())
        cublas.cublasSscal(self.cublas_handle, x_gpu.size, alpha,
                           x_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), alpha*x)
        
    def test_cublasCscal(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        alpha = np.complex64(np.random.rand()+1j*np.random.rand())
        cublas.cublasCscal(self.cublas_handle, x_gpu.size, alpha,
                           x_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), alpha*x)

    def test_cublasCsscal(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        alpha = np.float32(np.random.rand())
        cublas.cublasCscal(self.cublas_handle, x_gpu.size, alpha,
                           x_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), alpha*x)

    def test_cublasDscal(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        alpha = np.float64(np.random.rand())
        cublas.cublasDscal(self.cublas_handle, x_gpu.size, alpha,
                           x_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), alpha*x)

    def test_cublasZscal(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        alpha = np.complex128(np.random.rand()+1j*np.random.rand())
        cublas.cublasZscal(self.cublas_handle, x_gpu.size, alpha,
                           x_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), alpha*x)

    def test_cublasZdscal(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        alpha = np.float64(np.random.rand())
        cublas.cublasZdscal(self.cublas_handle, x_gpu.size, alpha,
                           x_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), alpha*x)

    # SROT, DROT, CROT, CSROT, ZROT, ZDROT
    def test_cublasSrot(self):
        x = np.array([1, 2, 3]).astype(np.float32)
        y = np.array([4, 5, 6]).astype(np.float32)
        s = 2.0
        c = 3.0
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.to_gpu(x)
        cublas.cublasSrot(self.cublas_handle, x_gpu.size, 
                          x_gpu.gpudata, 1, 
                          y_gpu.gpudata, 1,
                          c, s)
        assert np.allclose(x_gpu.get(), [5, 10, 15])
        assert np.allclose(y_gpu.get(), [1, 2, 3])
        
    # SSWAP, DSWAP, CSWAP, ZSWAP
    def test_cublasSswap(self):
        x = np.random.rand(5).astype(np.float32)
        x_gpu = gpuarray.to_gpu(x)
        y = np.random.rand(5).astype(np.float32)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasSswap(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), y)

    def test_cublasDswap(self):
        x = np.random.rand(5).astype(np.float64)
        x_gpu = gpuarray.to_gpu(x)
        y = np.random.rand(5).astype(np.float64)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasDswap(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), y)

    def test_cublasCswap(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex64)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasCswap(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), y)

    def test_cublasZswap(self):
        x = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        y = (np.random.rand(5)+1j*np.random.rand(5)).astype(np.complex128)
        y_gpu = gpuarray.to_gpu(y)
        cublas.cublasZswap(self.cublas_handle, x_gpu.size, x_gpu.gpudata, 1,
                           y_gpu.gpudata, 1)
        assert np.allclose(x_gpu.get(), y)

    # SGEMV, DGEMV, CGEMV, ZGEMV
    def test_cublasSgemv(self):
        a = np.random.rand(2, 3).astype(np.float32)
        x = np.random.rand(3, 1).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a.T.copy())
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.empty((2, 1), np.float32)
        alpha = np.float32(1.0)
        beta = np.float32(0.0)
        cublas.cublasSgemv(self.cublas_handle, 'n', 2, 3, alpha, 
                           a_gpu.gpudata, 2, x_gpu.gpudata,
                           1, beta, y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), np.dot(a, x))

    def test_cublasDgemv(self):
        a = np.random.rand(2, 3).astype(np.float64)
        x = np.random.rand(3, 1).astype(np.float64)
        a_gpu = gpuarray.to_gpu(a.T.copy())
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.empty((2, 1), np.float64)
        alpha = np.float64(1.0)
        beta = np.float64(0.0)
        cublas.cublasDgemv(self.cublas_handle, 'n', 2, 3, alpha, 
                           a_gpu.gpudata, 2, x_gpu.gpudata,
                           1, beta, y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), np.dot(a, x))

    def test_cublasCgemv(self):
        a = (np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex64)
        x = (np.random.rand(3, 1)+1j*np.random.rand(3, 1)).astype(np.complex64)
        a_gpu = gpuarray.to_gpu(a.T.copy())
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.empty((2, 1), np.complex64)
        alpha = np.complex64(1.0)
        beta = np.complex64(0.0)
        cublas.cublasCgemv(self.cublas_handle, 'n', 2, 3, alpha, 
                           a_gpu.gpudata, 2, x_gpu.gpudata,
                           1, beta, y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), np.dot(a, x))

    def test_cublasZgemv(self):
        a = (np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex128)
        x = (np.random.rand(3, 1)+1j*np.random.rand(3, 1)).astype(np.complex128)
        a_gpu = gpuarray.to_gpu(a.T.copy())
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.empty((2, 1), np.complex128)
        alpha = np.complex128(1.0)
        beta = np.complex128(0.0)
        cublas.cublasZgemv(self.cublas_handle, 'n', 2, 3, alpha, 
                           a_gpu.gpudata, 2, x_gpu.gpudata,
                           1, beta, y_gpu.gpudata, 1)
        assert np.allclose(y_gpu.get(), np.dot(a, x))

    # SGEAM, CGEAM, DGEAM, ZDGEAM
    def test_cublasSgeam(self):
        a = np.random.rand(2, 3).astype(np.float32)
        b = np.random.rand(2, 3).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a.copy())
        b_gpu = gpuarray.to_gpu(b.copy())
        c_gpu = gpuarray.zeros_like(a_gpu)
        alpha = np.float32(np.random.rand())
        beta = np.float32(np.random.rand())
        cublas.cublasSgeam(self.cublas_handle, 'n', 'n', 2, 3,
                           alpha, a_gpu.gpudata, 2,
                           beta, b_gpu.gpudata, 2,
                           c_gpu.gpudata, 2)
        assert np.allclose(c_gpu.get(), alpha*a+beta*b)

    def test_cublasCgeam(self):
        a = (np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex64)
        b = (np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex64)
        a_gpu = gpuarray.to_gpu(a.copy())
        b_gpu = gpuarray.to_gpu(b.copy())
        c_gpu = gpuarray.zeros_like(a_gpu)
        alpha = np.complex64(np.random.rand()+1j*np.random.rand())
        beta = np.complex64(np.random.rand()+1j*np.random.rand())
        cublas.cublasCgeam(self.cublas_handle, 'n', 'n', 2, 3,
                           alpha, a_gpu.gpudata, 2,
                           beta, b_gpu.gpudata, 2,
                           c_gpu.gpudata, 2)
        assert np.allclose(c_gpu.get(), alpha*a+beta*b)

    def test_cublasDgeam(self):
        a = np.random.rand(2, 3).astype(np.float64)
        b = np.random.rand(2, 3).astype(np.float64)
        a_gpu = gpuarray.to_gpu(a.copy())
        b_gpu = gpuarray.to_gpu(b.copy())
        c_gpu = gpuarray.zeros_like(a_gpu)
        alpha = np.float64(np.random.rand())
        beta = np.float64(np.random.rand())
        cublas.cublasDgeam(self.cublas_handle, 'n', 'n', 2, 3,
                           alpha, a_gpu.gpudata, 2,
                           beta, b_gpu.gpudata, 2,
                           c_gpu.gpudata, 2)
        assert np.allclose(c_gpu.get(), alpha*a+beta*b)

    def test_cublasZgeam(self):
        a = (np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex128)
        b = (np.random.rand(2, 3)+1j*np.random.rand(2, 3)).astype(np.complex128)
        a_gpu = gpuarray.to_gpu(a.copy())
        b_gpu = gpuarray.to_gpu(b.copy())
        c_gpu = gpuarray.zeros_like(a_gpu)
        alpha = np.complex128(np.random.rand()+1j*np.random.rand())
        beta = np.complex128(np.random.rand()+1j*np.random.rand())
        cublas.cublasZgeam(self.cublas_handle, 'n', 'n', 2, 3,
                           alpha, a_gpu.gpudata, 2,
                           beta, b_gpu.gpudata, 2,
                           c_gpu.gpudata, 2)
        assert np.allclose(c_gpu.get(), alpha*a+beta*b)
        
    # SgemmBatched, DgemmBatched
    def test_cublasSgemmBatched(self):        
        l, m, k, n = 11, 7, 5, 3
        A = np.random.rand(l, m, k).astype(np.float32)
        B = np.random.rand(l, k, n).astype(np.float32)
        
        C_res = np.einsum('nij,njk->nik', A, B)
        
        a_gpu = gpuarray.to_gpu(A)
        b_gpu = gpuarray.to_gpu(B)
        c_gpu = gpuarray.empty((l, m, n), np.float32)
        
        alpha = np.float32(1.0)
        beta = np.float32(0.0)

        a_arr = bptrs(a_gpu)
        b_arr = bptrs(b_gpu)
        c_arr = bptrs(c_gpu)

        cublas.cublasSgemmBatched(self.cublas_handle, 'n','n', 
                                  n, m, k, alpha, 
                                  b_arr.gpudata, n, 
                                  a_arr.gpudata, k, 
                                  beta, c_arr.gpudata, n, l)

        assert np.allclose(C_res, c_gpu.get())

    def test_cublasDgemmBatched(self):        
        l, m, k, n = 11, 7, 5, 3
        A = np.random.rand(l, m, k).astype(np.float64)
        B = np.random.rand(l, k, n).astype(np.float64)
        
        C_res = np.einsum('nij,njk->nik',A,B)
        
        a_gpu = gpuarray.to_gpu(A)
        b_gpu = gpuarray.to_gpu(B)
        c_gpu = gpuarray.empty((l, m, n), np.float64)
        
        alpha = np.float64(1.0)
        beta = np.float64(0.0)

        a_arr = bptrs(a_gpu)
        b_arr = bptrs(b_gpu)
        c_arr = bptrs(c_gpu)

        cublas.cublasDgemmBatched(self.cublas_handle, 'n','n', 
                                  n, m, k, alpha, 
                                  b_arr.gpudata, n, 
                                  a_arr.gpudata, k, 
                                  beta, c_arr.gpudata, n, l)

        assert np.allclose(C_res, c_gpu.get())

    # StrsmBatched, DtrsmBatched
    def test_cublasStrsmBatched(self):        
        l, m, n = 11, 7, 5
        A = np.random.rand(l, m, m).astype(np.float32)
        B = np.random.rand(l, m, n).astype(np.float32)

        A = np.array(map(np.triu, A))
        X = np.array([np.linalg.solve(a, b) for a, b in zip(A, B)])
       
        alpha = np.float32(1.0)

        a_gpu = gpuarray.to_gpu(A)
        b_gpu = gpuarray.to_gpu(B)
        
        a_arr = bptrs(a_gpu)
        b_arr = bptrs(b_gpu)

        cublas.cublasStrsmBatched(self.cublas_handle, 'r', 'l', 'n', 'n',
                                  n, m, alpha, 
                                  a_arr.gpudata, m, 
                                  b_arr.gpudata, n, l)
                                  
        assert np.allclose(X, b_gpu.get(), 5)

    def test_cublasDtrsmBatched(self):        
        l, m, n = 11, 7, 5
        A = np.random.rand(l, m, m).astype(np.float64)
        B = np.random.rand(l, m, n).astype(np.float64)

        A = np.array(map(np.triu, A))
        X = np.array([np.linalg.solve(a, b) for a, b in zip(A, B)])
       
        alpha = np.float64(1.0)

        a_gpu = gpuarray.to_gpu(A)
        b_gpu = gpuarray.to_gpu(B)
        
        a_arr = bptrs(a_gpu)
        b_arr = bptrs(b_gpu)

        cublas.cublasDtrsmBatched(self.cublas_handle, 'r', 'l', 'n', 'n',
                                  n, m, alpha, 
                                  a_arr.gpudata, m, 
                                  b_arr.gpudata, n, l)
                                  
        assert np.allclose(X, b_gpu.get(), 5)

    # SgetrfBatched, DgetrfBatched
    def test_cublasSgetrfBatched(self):
        from scipy.linalg import lu_factor
        l, m = 11, 7
        A = np.random.rand(l, m, m).astype(np.float32)
        A = np.array([np.matrix(a)*np.matrix(a).T for a in A])
        
        a_gpu = gpuarray.to_gpu(A)
        a_arr = bptrs(a_gpu)
        p_gpu = gpuarray.empty((l, m), np.int32)
        i_gpu = gpuarray.zeros(1, np.int32)
        X = np.array([ lu_factor(a)[0] for a in A])

        cublas.cublasSgetrfBatched(self.cublas_handle, 
                                   m, a_arr.gpudata, m,
                                   p_gpu.gpudata, i_gpu.gpudata, l)
        
        X_ = np.array([a.T for a in a_gpu.get()])

        assert np.allclose(X, X_, atol=10*_SEPS)

    def test_cublasDgetrfBatched(self):
        from scipy.linalg import lu_factor
        l, m = 11, 7
        A = np.random.rand(l, m, m).astype(np.float64)
        A = np.array([np.matrix(a)*np.matrix(a).T for a in A])
        
        a_gpu = gpuarray.to_gpu(A)
        a_arr = bptrs(a_gpu)
        p_gpu = gpuarray.empty((l, m), np.int32)
        i_gpu = gpuarray.zeros(1, np.int32)
        X = np.array([ lu_factor(a)[0] for a in A])

        cublas.cublasDgetrfBatched(self.cublas_handle, 
                                   m, a_arr.gpudata, m,
                                   p_gpu.gpudata, i_gpu.gpudata, l)
        
        X_ = np.array([a.T for a in a_gpu.get()])

        assert np.allclose(X,X_)
        

def suite():
    s = TestSuite()
    s.addTest(test_cublas('test_cublasIsamax'))
    s.addTest(test_cublas('test_cublasIcamax'))
    s.addTest(test_cublas('test_cublasIsamin'))
    s.addTest(test_cublas('test_cublasIcamin'))
    s.addTest(test_cublas('test_cublasSasum'))
    s.addTest(test_cublas('test_cublasScasum'))
    s.addTest(test_cublas('test_cublasSaxpy'))
    s.addTest(test_cublas('test_cublasCaxpy'))
    s.addTest(test_cublas('test_cublasScopy'))
    s.addTest(test_cublas('test_cublasCcopy'))    
    s.addTest(test_cublas('test_cublasSdot'))
    s.addTest(test_cublas('test_cublasCdotu'))
    s.addTest(test_cublas('test_cublasCdotc'))
    s.addTest(test_cublas('test_cublasSrnm2'))
    s.addTest(test_cublas('test_cublasScrnm2'))
    s.addTest(test_cublas('test_cublasSscal'))
    s.addTest(test_cublas('test_cublasCscal'))
    s.addTest(test_cublas('test_cublasSrot'))
    s.addTest(test_cublas('test_cublasSswap'))
    s.addTest(test_cublas('test_cublasCswap'))
    s.addTest(test_cublas('test_cublasSgemv'))
    s.addTest(test_cublas('test_cublasCgemv'))
    s.addTest(test_cublas('test_cublasSgeam'))
    s.addTest(test_cublas('test_cublasCgeam'))
    s.addTest(test_cublas('test_cublasSgemmBatched'))
    s.addTest(test_cublas('test_cublasStrsmBatched'))
    s.addTest(test_cublas('test_cublasSgetrfBatched'))
    if misc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
        s.addTest(test_cublas('test_cublasIdamax'))
        s.addTest(test_cublas('test_cublasIzamax'))
        s.addTest(test_cublas('test_cublasIdamin'))
        s.addTest(test_cublas('test_cublasIzamin'))
        s.addTest(test_cublas('test_cublasDasum'))
        s.addTest(test_cublas('test_cublasDzasum'))
        s.addTest(test_cublas('test_cublasDaxpy'))
        s.addTest(test_cublas('test_cublasZaxpy'))
        s.addTest(test_cublas('test_cublasDcopy'))
        s.addTest(test_cublas('test_cublasZcopy'))
        s.addTest(test_cublas('test_cublasDdot'))
        s.addTest(test_cublas('test_cublasZdotu'))
        s.addTest(test_cublas('test_cublasZdotc'))
        s.addTest(test_cublas('test_cublasDrnm2'))
        s.addTest(test_cublas('test_cublasDzrnm2'))
        s.addTest(test_cublas('test_cublasDscal'))
        s.addTest(test_cublas('test_cublasZscal'))
        s.addTest(test_cublas('test_cublasZdscal'))
        s.addTest(test_cublas('test_cublasDswap'))
        s.addTest(test_cublas('test_cublasZswap'))
        s.addTest(test_cublas('test_cublasDgemv'))
        s.addTest(test_cublas('test_cublasZgemv'))
        s.addTest(test_cublas('test_cublasDgeam'))
        s.addTest(test_cublas('test_cublasZgeam'))        
        s.addTest(test_cublas('test_cublasDgemmBatched'))
        s.addTest(test_cublas('test_cublasDtrsmBatched'))
        s.addTest(test_cublas('test_cublasDgetrfBatched'))        
    return s

if __name__ == '__main__':
    main(defaultTest = 'suite')

########NEW FILE########
__FILENAME__ = test_fft
#!/usr/bin/env python

"""
Unit tests for scikits.cuda.fft
"""


from unittest import main, makeSuite, TestCase, TestSuite

import pycuda.autoinit
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.fft as fft
import scikits.cuda.misc as misc

atol_float32 = 1e-6
atol_float64 = 1e-8

class test_fft(TestCase):
    def setUp(self):
        self.N = 8
        self.M = 4
        self.B = 3

    def test_fft_float32_to_complex64_1d(self):
        x = np.asarray(np.random.rand(self.N), np.float32)
        xf = np.fft.rfftn(x)
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty(self.N/2+1, np.complex64)
        plan = fft.Plan(x.shape, np.float32, np.complex64)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float32)

    def test_fft_float32_to_complex64_2d(self):
        x = np.asarray(np.random.rand(self.N, self.M), np.float32)
        xf = np.fft.rfftn(x)
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty((self.N, self.M/2+1), np.complex64)
        plan = fft.Plan(x.shape, np.float32, np.complex64)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float32)

    def test_batch_fft_float32_to_complex64_1d(self):
        x = np.asarray(np.random.rand(self.B, self.N), np.float32)
        xf = np.fft.rfft(x, axis=1)
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty((self.B, self.N/2+1), np.complex64)
        plan = fft.Plan(x.shape[1], np.float32, np.complex64, batch=self.B)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float32)

    def test_batch_fft_float32_to_complex64_2d(self):
        x = np.asarray(np.random.rand(self.B, self.N, self.M), np.float32)
        xf = np.fft.rfftn(x, axes=(1,2))
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty((self.B, self.N, self.M/2+1), np.complex64)
        plan = fft.Plan([self.N, self.M], np.float32, np.complex64, batch=self.B)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float32)
        
    def test_fft_float64_to_complex128_1d(self):
        x = np.asarray(np.random.rand(self.N), np.float64)
        xf = np.fft.rfftn(x)
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty(self.N/2+1, np.complex128)
        plan = fft.Plan(x.shape, np.float64, np.complex128)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float64)

    def test_fft_float64_to_complex128_2d(self):
        x = np.asarray(np.random.rand(self.N, self.M), np.float64)
        xf = np.fft.rfftn(x)
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty((self.N, self.M/2+1), np.complex128)
        plan = fft.Plan(x.shape, np.float64, np.complex128)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float64)

    def test_batch_fft_float64_to_complex128_1d(self):
        x = np.asarray(np.random.rand(self.B, self.N), np.float64)
        xf = np.fft.rfft(x, axis=1)
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty((self.B, self.N/2+1), np.complex128)
        plan = fft.Plan(x.shape[1], np.float64, np.complex128, batch=self.B)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float64)

    def test_batch_fft_float64_to_complex128_2d(self):
        x = np.asarray(np.random.rand(self.B, self.N, self.M), np.float64)
        xf = np.fft.rfftn(x, axes=(1,2))
        x_gpu = gpuarray.to_gpu(x)
        xf_gpu = gpuarray.empty((self.B, self.N, self.M/2+1), np.complex128)
        plan = fft.Plan([self.N, self.M], np.float64, np.complex128, batch=self.B)
        fft.fft(x_gpu, xf_gpu, plan)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float64)
        
    def test_ifft_complex64_to_float32_1d(self):
        x = np.asarray(np.random.rand(self.N), np.float32)
        xf = np.asarray(np.fft.rfftn(x), np.complex64)
        xf_gpu = gpuarray.to_gpu(xf)
        x_gpu = gpuarray.empty(self.N, np.float32)
        plan = fft.Plan(x.shape, np.complex64, np.float32)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float32)

    def test_ifft_complex64_to_float32_2d(self):

        # Note that since rfftn returns a Fortran-ordered array, it
        # needs to be reformatted as a C-ordered array before being
        # passed to gpuarray.to_gpu:
        x = np.asarray(np.random.rand(self.N, self.M), np.float32)
        xf = np.asarray(np.fft.rfftn(x), np.complex64)
        xf_gpu = gpuarray.to_gpu(np.ascontiguousarray(xf))
        x_gpu = gpuarray.empty((self.N, self.M), np.float32)
        plan = fft.Plan(x.shape, np.complex64, np.float32)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float32)

    def test_batch_ifft_complex64_to_float32_1d(self):

        # Note that since rfftn returns a Fortran-ordered array, it
        # needs to be reformatted as a C-ordered array before being
        # passed to gpuarray.to_gpu:
        x = np.asarray(np.random.rand(self.B, self.N), np.float32)
        xf = np.asarray(np.fft.rfft(x, axis=1), np.complex64)
        xf_gpu = gpuarray.to_gpu(np.ascontiguousarray(xf))
        x_gpu = gpuarray.empty((self.B, self.N), np.float32)
        plan = fft.Plan(x.shape[1], np.complex64, np.float32, batch=self.B)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float32)

    def test_batch_ifft_complex64_to_float32_2d(self):

        # Note that since rfftn returns a Fortran-ordered array, it
        # needs to be reformatted as a C-ordered array before being
        # passed to gpuarray.to_gpu:
        x = np.asarray(np.random.rand(self.B, self.N, self.M), np.float32)
        xf = np.asarray(np.fft.rfftn(x, axes=(1,2)), np.complex64)
        xf_gpu = gpuarray.to_gpu(np.ascontiguousarray(xf))
        x_gpu = gpuarray.empty((self.B, self.N, self.M), np.float32)
        plan = fft.Plan([self.N, self.M], np.complex64, np.float32, batch=self.B)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float32)

    def test_ifft_complex128_to_float64_1d(self):
        x = np.asarray(np.random.rand(self.N), np.float64)
        xf = np.asarray(np.fft.rfftn(x), np.complex128)
        xf_gpu = gpuarray.to_gpu(xf)
        x_gpu = gpuarray.empty(self.N, np.float64)
        plan = fft.Plan(x.shape, np.complex128, np.float64)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float64)

    def test_ifft_complex128_to_float64_2d(self):

        # Note that since rfftn returns a Fortran-ordered array, it
        # needs to be reformatted as a C-ordered array before being
        # passed to gpuarray.to_gpu:
        x = np.asarray(np.random.rand(self.N, self.M), np.float64)
        xf = np.asarray(np.fft.rfftn(x), np.complex128)
        xf_gpu = gpuarray.to_gpu(np.ascontiguousarray(xf))
        x_gpu = gpuarray.empty((self.N, self.M), np.float64)
        plan = fft.Plan(x.shape, np.complex128, np.float64)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float64)

    def test_batch_ifft_complex128_to_float64_1d(self):

        # Note that since rfftn returns a Fortran-ordered array, it
        # needs to be reformatted as a C-ordered array before being
        # passed to gpuarray.to_gpu:
        x = np.asarray(np.random.rand(self.B, self.N), np.float64)
        xf = np.asarray(np.fft.rfft(x, axis=1), np.complex128)
        xf_gpu = gpuarray.to_gpu(np.ascontiguousarray(xf))
        x_gpu = gpuarray.empty((self.B, self.N), np.float64)
        plan = fft.Plan(x.shape[1], np.complex128, np.float64, batch=self.B)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float64)

    def test_batch_ifft_complex128_to_float64_2d(self):

        # Note that since rfftn returns a Fortran-ordered array, it
        # needs to be reformatted as a C-ordered array before being
        # passed to gpuarray.to_gpu:
        x = np.asarray(np.random.rand(self.B, self.N, self.M), np.float64)
        xf = np.asarray(np.fft.rfftn(x, axes=(1,2)), np.complex128)
        xf_gpu = gpuarray.to_gpu(np.ascontiguousarray(xf))
        x_gpu = gpuarray.empty((self.B, self.N, self.M), np.float64)
        plan = fft.Plan([self.N, self.M], np.complex128, np.float64, batch=self.B)
        fft.ifft(xf_gpu, x_gpu, plan, True)
        assert np.allclose(x, x_gpu.get(), atol=atol_float64)
        
    def test_multiple_streams(self):
        x = np.asarray(np.random.rand(self.N), np.float32)
        xf = np.fft.rfftn(x)
        y = np.asarray(np.random.rand(self.N), np.float32)
        yf = np.fft.rfftn(y)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.to_gpu(y)
        xf_gpu = gpuarray.empty(self.N/2+1, np.complex64)
        yf_gpu = gpuarray.empty(self.N/2+1, np.complex64)
        stream0 = drv.Stream()
        stream1 = drv.Stream()
        plan1 = fft.Plan(x.shape, np.float32, np.complex64, stream=stream0)
        plan2 = fft.Plan(y.shape, np.float32, np.complex64, stream=stream1)
        fft.fft(x_gpu, xf_gpu, plan1)
        fft.fft(y_gpu, yf_gpu, plan2)
        assert np.allclose(xf, xf_gpu.get(), atol=atol_float32)
        assert np.allclose(yf, yf_gpu.get(), atol=atol_float32)

def suite():
    s = TestSuite()
    s.addTest(test_fft('test_fft_float32_to_complex64_1d'))
    s.addTest(test_fft('test_fft_float32_to_complex64_2d')) 
    s.addTest(test_fft('test_batch_fft_float32_to_complex64_1d'))
    s.addTest(test_fft('test_batch_fft_float32_to_complex64_2d'))
    s.addTest(test_fft('test_ifft_complex64_to_float32_1d'))
    s.addTest(test_fft('test_ifft_complex64_to_float32_2d'))
    s.addTest(test_fft('test_batch_ifft_complex64_to_float32_1d'))
    s.addTest(test_fft('test_batch_ifft_complex64_to_float32_2d'))
    s.addTest(test_fft('test_multiple_streams'))
    if misc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
        s.addTest(test_fft('test_fft_float64_to_complex128_1d'))
        s.addTest(test_fft('test_fft_float64_to_complex128_2d'))
        s.addTest(test_fft('test_batch_fft_float64_to_complex128_1d'))
        s.addTest(test_fft('test_batch_fft_float64_to_complex128_2d'))
        s.addTest(test_fft('test_ifft_complex128_to_float64_1d'))
        s.addTest(test_fft('test_ifft_complex128_to_float64_2d'))
        s.addTest(test_fft('test_batch_ifft_complex128_to_float64_1d'))
        s.addTest(test_fft('test_batch_ifft_complex128_to_float64_2d'))
    return s

if __name__ == '__main__':
    main(defaultTest = 'suite')

########NEW FILE########
__FILENAME__ = test_integrate
"""
Unit tests for scikits.cuda.integrate
"""

from unittest import main, TestCase, TestSuite

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.misc as misc
import scikits.cuda.integrate as integrate

class test_integrate(TestCase):
    def setUp(self):
        integrate.init()

    def test_trapz_float32(self):
        x = np.asarray(np.random.rand(10), np.float32)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz(x_gpu)                                  
        assert np.allclose(np.trapz(x), z)

    def test_trapz_float64(self):
        x = np.asarray(np.random.rand(10), np.float64)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz(x_gpu)                                  
        assert np.allclose(np.trapz(x), z)

    def test_trapz_complex64(self):
        x = np.asarray(np.random.rand(10)+1j*np.random.rand(10), np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz(x_gpu)                                  
        assert np.allclose(np.trapz(x), z)

    def test_trapz_complex128(self):
        x = np.asarray(np.random.rand(10)+1j*np.random.rand(10), np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz(x_gpu)                                  
        assert np.allclose(np.trapz(x), z)

    def test_trapz2d_float32(self):
        x = np.asarray(np.random.rand(5, 5), np.float32)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz2d(x_gpu)                                  
        assert np.allclose(np.trapz(np.trapz(x)), z)

    def test_trapz2d_float64(self):
        x = np.asarray(np.random.rand(5, 5), np.float64)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz2d(x_gpu)
        assert np.allclose(np.trapz(np.trapz(x)), z)

    def test_trapz2d_complex64(self):
        x = np.asarray(np.random.rand(5, 5)+1j*np.random.rand(5, 5), np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz2d(x_gpu)
        assert np.allclose(np.trapz(np.trapz(x)), z)

    def test_trapz2d_complex128(self):
        x = np.asarray(np.random.rand(5, 5)+1j*np.random.rand(5, 5), np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        z = integrate.trapz2d(x_gpu)
        assert np.allclose(np.trapz(np.trapz(x)), z)

def suite():
    s = TestSuite()
    s.addTest(test_integrate('test_trapz_float32'))
    s.addTest(test_integrate('test_trapz_complex64'))
    s.addTest(test_integrate('test_trapz2d_float32'))
    s.addTest(test_integrate('test_trapz2d_complex64'))
    if misc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
        s.addTest(test_integrate('test_trapz_float64'))
        s.addTest(test_integrate('test_trapz_complex128'))
        s.addTest(test_integrate('test_trapz2d_float64'))
        s.addTest(test_integrate('test_trapz2d_complex128'))
    return s

if __name__ == '__main__':
    main(defaultTest = 'suite')

########NEW FILE########
__FILENAME__ = test_linalg
#!/usr/bin/env python

"""
Unit tests for scikits.cuda.linalg
"""

from unittest import main, makeSuite, TestCase, TestSuite

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.linalg as linalg
import scikits.cuda.misc as misc

atol_float32 = 1e-6
atol_float64 = 1e-8

class test_linalg(TestCase):
    def setUp(self):
        linalg.init()

    def test_svd_ss_float32(self):
        a = np.asarray(np.random.randn(9, 6), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 's')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float32)  

    def test_svd_ss_float64(self):
        a = np.asarray(np.random.randn(9, 6), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 's')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float64)  

    def test_svd_ss_complex64(self):
        a = np.asarray(np.random.randn(9, 6) + 1j*np.random.randn(9, 6), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 's')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float32)  

    def test_svd_ss_complex128(self):
        a = np.asarray(np.random.randn(9, 6) + 1j*np.random.randn(9, 6), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 's')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float64)  

    def test_svd_so_float32(self):
        a = np.asarray(np.random.randn(6, 6), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 'o')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float32)  

    def test_svd_so_float64(self):
        a = np.asarray(np.random.randn(6, 6), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 'o')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float64)  

    def test_svd_so_complex64(self):
        a = np.asarray(np.random.randn(6, 6) + 1j*np.random.randn(6, 6), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 'o')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float32)  

    def test_svd_so_complex128(self):
        a = np.asarray(np.random.randn(6, 6) + 1j*np.random.randn(6, 6), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        u_gpu, s_gpu, vh_gpu = linalg.svd(a_gpu, 's', 'o')
        assert np.allclose(a, np.dot(u_gpu.get(),
                                     np.dot(np.diag(s_gpu.get()),
                                            vh_gpu.get())),
                           atol=atol_float64)  

    def test_dot_matrix_float32(self):
        a = np.asarray(np.random.rand(4, 2), np.float32)
        b = np.asarray(np.random.rand(2, 2), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c_gpu.get())

    def test_dot_matrix_float64(self):
        a = np.asarray(np.random.rand(4, 2), np.float64)
        b = np.asarray(np.random.rand(2, 2), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c_gpu.get())

    def test_dot_matrix_complex64(self):
        a = np.asarray(np.random.rand(4, 2), np.complex64)
        b = np.asarray(np.random.rand(2, 2), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c_gpu.get())

    def test_dot_matrix_complex128(self):
        a = np.asarray(np.random.rand(4, 2), np.complex128)
        b = np.asarray(np.random.rand(2, 2), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c_gpu.get())

    def test_dot_matrix_t_float32(self):
        a = np.asarray(np.random.rand(2, 4), np.float32)
        b = np.asarray(np.random.rand(2, 2), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu, 't')
        assert np.allclose(np.dot(a.T, b), c_gpu.get())

    def test_dot_matrix_t_float64(self):
        a = np.asarray(np.random.rand(2, 4), np.float64)
        b = np.asarray(np.random.rand(2, 2), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu, 't')
        assert np.allclose(np.dot(a.T, b), c_gpu.get())

    def test_dot_matrix_t_complex64(self):
        a = np.asarray(np.random.rand(2, 4), np.complex64)
        b = np.asarray(np.random.rand(2, 2), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu, 't')
        assert np.allclose(np.dot(a.T, b), c_gpu.get())

    def test_dot_matrix_t_complex128(self):
        a = np.asarray(np.random.rand(2, 4), np.complex128)
        b = np.asarray(np.random.rand(2, 2), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu, 't')
        assert np.allclose(np.dot(a.T, b), c_gpu.get())

    def test_dot_matrix_h_complex64(self):
        a = np.asarray(np.random.rand(2, 4)+1j*np.random.rand(2, 4), np.complex64)
        b = np.asarray(np.random.rand(2, 2)+1j*np.random.rand(2, 2), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu, 'c')
        assert np.allclose(np.dot(a.conj().T, b), c_gpu.get())

    def test_dot_matrix_h_complex128(self):
        a = np.asarray(np.random.rand(2, 4)+1j*np.random.rand(2, 4), np.complex128)
        b = np.asarray(np.random.rand(2, 2)+1j*np.random.rand(2, 2), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = linalg.dot(a_gpu, b_gpu, 'c')
        assert np.allclose(np.dot(a.conj().T, b), c_gpu.get())

    def test_dot_vector_float32(self):
        a = np.asarray(np.random.rand(5), np.float32)
        b = np.asarray(np.random.rand(5), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c)

    def test_dot_vector_float64(self):
        a = np.asarray(np.random.rand(5), np.float64)
        b = np.asarray(np.random.rand(5), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c)

    def test_dot_vector_complex64(self):
        a = np.asarray(np.random.rand(5), np.complex64)
        b = np.asarray(np.random.rand(5), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c)

    def test_dot_vector_complex128(self):
        a = np.asarray(np.random.rand(5), np.complex128)
        b = np.asarray(np.random.rand(5), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c = linalg.dot(a_gpu, b_gpu)
        assert np.allclose(np.dot(a, b), c)

    def test_mdot_matrix_float32(self):
        a = np.asarray(np.random.rand(4, 2), np.float32)
        b = np.asarray(np.random.rand(2, 2), np.float32)
        c = np.asarray(np.random.rand(2, 2), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = gpuarray.to_gpu(c)
        d_gpu = linalg.mdot(a_gpu, b_gpu, c_gpu)
        assert np.allclose(np.dot(a, np.dot(b, c)), d_gpu.get())

    def test_mdot_matrix_float64(self):
        a = np.asarray(np.random.rand(4, 2), np.float64)
        b = np.asarray(np.random.rand(2, 2), np.float64)
        c = np.asarray(np.random.rand(2, 2), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = gpuarray.to_gpu(c)
        d_gpu = linalg.mdot(a_gpu, b_gpu, c_gpu)
        assert np.allclose(np.dot(a, np.dot(b, c)), d_gpu.get())

    def test_mdot_matrix_complex64(self):
        a = np.asarray(np.random.rand(4, 2), np.complex64)
        b = np.asarray(np.random.rand(2, 2), np.complex64)
        c = np.asarray(np.random.rand(2, 2), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = gpuarray.to_gpu(c)
        d_gpu = linalg.mdot(a_gpu, b_gpu, c_gpu)
        assert np.allclose(np.dot(a, np.dot(b, c)), d_gpu.get())

    def test_mdot_matrix_complex128(self):
        a = np.asarray(np.random.rand(4, 2), np.complex128)
        b = np.asarray(np.random.rand(2, 2), np.complex128)
        c = np.asarray(np.random.rand(2, 2), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)
        c_gpu = gpuarray.to_gpu(c)
        d_gpu = linalg.mdot(a_gpu, b_gpu, c_gpu)
        assert np.allclose(np.dot(a, np.dot(b, c)), d_gpu.get())
 
    def test_dot_diag_float32(self):
        d = np.asarray(np.random.rand(5), np.float32)
        a = np.asarray(np.random.rand(5, 3), np.float32)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu)
        assert np.allclose(np.dot(np.diag(d), a), r_gpu.get())

    def test_dot_diag_float64(self):
        d = np.asarray(np.random.rand(5), np.float64)
        a = np.asarray(np.random.rand(5, 3), np.float64)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu)
        assert np.allclose(np.dot(np.diag(d), a), r_gpu.get())

    def test_dot_diag_complex64(self):
        d = np.asarray(np.random.rand(5), np.float32)
        a = np.asarray(np.random.rand(5, 3)+1j*np.random.rand(5, 3), np.complex64)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu)
        assert np.allclose(np.dot(np.diag(d), a), r_gpu.get())

    def test_dot_diag_complex128(self):
        d = np.asarray(np.random.rand(5), np.float64)
        a = np.asarray(np.random.rand(5, 3)+1j*np.random.rand(5, 3), np.complex128)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu)
        assert np.allclose(np.dot(np.diag(d), a), r_gpu.get())

    def test_dot_diag_t_float32(self):
        d = np.asarray(np.random.rand(5), np.float32)
        a = np.asarray(np.random.rand(3, 5), np.float32)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu, 't')
        assert np.allclose(np.dot(np.diag(d), a.T).T, r_gpu.get())

    def test_dot_diag_t_float64(self):
        d = np.asarray(np.random.rand(5), np.float64)
        a = np.asarray(np.random.rand(3, 5), np.float64)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu, 't')
        assert np.allclose(np.dot(np.diag(d), a.T).T, r_gpu.get())

    def test_dot_diag_t_complex64(self):
        d = np.asarray(np.random.rand(5), np.float32)
        a = np.asarray(np.random.rand(3, 5)+1j*np.random.rand(3, 5), np.complex64)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu, 't')
        assert np.allclose(np.dot(np.diag(d), a.T).T, r_gpu.get())

    def test_dot_diag_t_complex128(self):
        d = np.asarray(np.random.rand(5), np.float64)
        a = np.asarray(np.random.rand(3, 5)+1j*np.random.rand(3, 5), np.complex128)
        d_gpu = gpuarray.to_gpu(d)
        a_gpu = gpuarray.to_gpu(a)
        r_gpu = linalg.dot_diag(d_gpu, a_gpu, 't')
        assert np.allclose(np.dot(np.diag(d), a.T).T, r_gpu.get())
                          
    def test_transpose_float32(self):
        a = np.array([[1, 2, 3, 4, 5, 6],
                      [7, 8, 9, 10, 11, 12]],
                     np.float32)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.transpose(a_gpu)
        assert np.all(a.T == at_gpu.get())

    def test_transpose_float64(self):
        a = np.array([[1, 2, 3, 4, 5, 6],
                      [7, 8, 9, 10, 11, 12]],
                     np.float64)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.transpose(a_gpu)
        assert np.all(a.T == at_gpu.get())

    def test_transpose_complex64(self):
        a = np.array([[1j, 2j, 3j, 4j, 5j, 6j],
                      [7j, 8j, 9j, 10j, 11j, 12j]],
                     np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.transpose(a_gpu)
        assert np.all(a.T == at_gpu.get())

    def test_transpose_complex128(self):
        a = np.array([[1j, 2j, 3j, 4j, 5j, 6j],
                      [7j, 8j, 9j, 10j, 11j, 12j]],
                     np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.transpose(a_gpu)
        assert np.all(a.T == at_gpu.get())

    def test_hermitian_float32(self):
        a = np.array([[1, 2, 3, 4, 5, 6],
                      [7, 8, 9, 10, 11, 12]],
                     np.float32)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.hermitian(a_gpu)
        assert np.all(a.T == at_gpu.get())

    def test_hermitian_complex64(self):
        a = np.array([[1j, 2j, 3j, 4j, 5j, 6j],
                      [7j, 8j, 9j, 10j, 11j, 12j]],
                     np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.hermitian(a_gpu)
        assert np.all(np.conj(a.T) == at_gpu.get())

    def test_hermitian_float64(self):
        a = np.array([[1, 2, 3, 4, 5, 6],
                      [7, 8, 9, 10, 11, 12]],
                     np.float64)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.hermitian(a_gpu)
        assert np.all(a.T == at_gpu.get())

    def test_hermitian_complex128(self):
        a = np.array([[1j, 2j, 3j, 4j, 5j, 6j],
                      [7j, 8j, 9j, 10j, 11j, 12j]],
                     np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        at_gpu = linalg.hermitian(a_gpu)
        assert np.all(np.conj(a.T) == at_gpu.get())

    def test_conj_complex64(self):
        a = np.array([[1+1j, 2-2j, 3+3j, 4-4j],
                      [5+5j, 6-6j, 7+7j, 8-8j]], np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        linalg.conj(a_gpu)
        assert np.all(np.conj(a) == a_gpu.get())

    def test_conj_complex128(self):
        a = np.array([[1+1j, 2-2j, 3+3j, 4-4j],
                      [5+5j, 6-6j, 7+7j, 8-8j]], np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        linalg.conj(a_gpu)
        assert np.all(np.conj(a) == a_gpu.get())

    def test_diag_float32(self):
        v = np.array([1, 2, 3, 4, 5, 6], np.float32)
        v_gpu = gpuarray.to_gpu(v)
        d_gpu = linalg.diag(v_gpu)
        assert np.all(np.diag(v) == d_gpu.get())

    def test_diag_float64(self):
        v = np.array([1, 2, 3, 4, 5, 6], np.float64)
        v_gpu = gpuarray.to_gpu(v)
        d_gpu = linalg.diag(v_gpu)
        assert np.all(np.diag(v) == d_gpu.get())

    def test_diag_complex64(self):
        v = np.array([1j, 2j, 3j, 4j, 5j, 6j], np.complex64)
        v_gpu = gpuarray.to_gpu(v)
        d_gpu = linalg.diag(v_gpu)
        assert np.all(np.diag(v) == d_gpu.get())

    def test_diag_complex128(self):
        v = np.array([1j, 2j, 3j, 4j, 5j, 6j], np.complex128)
        v_gpu = gpuarray.to_gpu(v)
        d_gpu = linalg.diag(v_gpu)
        assert np.all(np.diag(v) == d_gpu.get())

    def test_eye_float32(self):
        N = 10
        e_gpu = linalg.eye(N, dtype=np.float32)
        assert np.all(np.eye(N, dtype=np.float32) == e_gpu.get())

    def test_eye_float64(self):
        N = 10
        e_gpu = linalg.eye(N, dtype=np.float64)
        assert np.all(np.eye(N, dtype=np.float64) == e_gpu.get())

    def test_eye_complex64(self):
        N = 10
        e_gpu = linalg.eye(N, dtype=np.complex64)
        assert np.all(np.eye(N, dtype=np.complex64) == e_gpu.get())

    def test_eye_complex128(self):
        N = 10
        e_gpu = linalg.eye(N, dtype=np.complex128)
        assert np.all(np.eye(N, dtype=np.complex128) == e_gpu.get())

    def test_pinv_float32(self):
        a = np.asarray(np.random.rand(8, 4), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        a_inv_gpu = linalg.pinv(a_gpu)
        assert np.allclose(np.linalg.pinv(a), a_inv_gpu.get(),
                           atol=atol_float32)   

    def test_pinv_float64(self):
        a = np.asarray(np.random.rand(8, 4), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        a_inv_gpu = linalg.pinv(a_gpu)
        assert np.allclose(np.linalg.pinv(a), a_inv_gpu.get(),
                           atol=atol_float64)   

    def test_pinv_complex64(self):
        a = np.asarray(np.random.rand(8, 4) + \
                       1j*np.random.rand(8, 4), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        a_inv_gpu = linalg.pinv(a_gpu)
        assert np.allclose(np.linalg.pinv(a), a_inv_gpu.get(),
                           atol=atol_float32)   

    def test_pinv_complex128(self):
        a = np.asarray(np.random.rand(8, 4) + \
                       1j*np.random.rand(8, 4), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        a_inv_gpu = linalg.pinv(a_gpu)
        assert np.allclose(np.linalg.pinv(a), a_inv_gpu.get(),
                           atol=atol_float64)   

    def test_tril_float32(self):
        a = np.asarray(np.random.rand(4, 4), np.float32)
        a_gpu = gpuarray.to_gpu(a)
        l_gpu = linalg.tril(a_gpu)
        assert np.allclose(np.tril(a), l_gpu.get())   

    def test_tril_float64(self):
        a = np.asarray(np.random.rand(4, 4), np.float64)
        a_gpu = gpuarray.to_gpu(a)
        l_gpu = linalg.tril(a_gpu)
        assert np.allclose(np.tril(a), l_gpu.get())   

    def test_tril_complex64(self):
        a = np.asarray(np.random.rand(4, 4), np.complex64)
        a_gpu = gpuarray.to_gpu(a)
        l_gpu = linalg.tril(a_gpu)
        assert np.allclose(np.tril(a), l_gpu.get())   

    def test_tril_complex128(self):
        a = np.asarray(np.random.rand(4, 4), np.complex128)
        a_gpu = gpuarray.to_gpu(a)
        l_gpu = linalg.tril(a_gpu)
        assert np.allclose(np.tril(a), l_gpu.get())   

    def test_multiply_float32(self):
        x = np.asarray(np.random.rand(4, 4), np.float32)
        y = np.asarray(np.random.rand(4, 4), np.float32)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.to_gpu(y)
        z_gpu = linalg.multiply(x_gpu, y_gpu)
        assert np.allclose(x*y, z_gpu.get())   

    def test_multiply_float64(self):
        x = np.asarray(np.random.rand(4, 4), np.float64)
        y = np.asarray(np.random.rand(4, 4), np.float64)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.to_gpu(y)
        z_gpu = linalg.multiply(x_gpu, y_gpu)
        assert np.allclose(x*y, z_gpu.get())   

    def test_multiply_complex64(self):
        x = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex64)
        y = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.to_gpu(y)
        z_gpu = linalg.multiply(x_gpu, y_gpu)
        assert np.allclose(x*y, z_gpu.get())   

    def test_multiply_complex128(self):
        x = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex128)
        y = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = gpuarray.to_gpu(y)
        z_gpu = linalg.multiply(x_gpu, y_gpu)
        assert np.allclose(x*y, z_gpu.get())   


def suite():
    s = TestSuite()
    s.addTest(test_linalg('test_svd_ss_float32'))
    s.addTest(test_linalg('test_svd_ss_complex64'))
    s.addTest(test_linalg('test_svd_so_float32'))
    s.addTest(test_linalg('test_svd_so_complex64'))
    s.addTest(test_linalg('test_dot_matrix_float32'))
    s.addTest(test_linalg('test_dot_matrix_complex64'))
    s.addTest(test_linalg('test_dot_matrix_t_float32'))
    s.addTest(test_linalg('test_dot_matrix_t_complex64'))
    s.addTest(test_linalg('test_dot_matrix_h_complex64'))
    s.addTest(test_linalg('test_dot_vector_float32'))
    s.addTest(test_linalg('test_dot_vector_complex64'))
    s.addTest(test_linalg('test_mdot_matrix_float32'))
    s.addTest(test_linalg('test_mdot_matrix_complex64'))
    s.addTest(test_linalg('test_dot_diag_float32'))
    s.addTest(test_linalg('test_dot_diag_complex64'))
    s.addTest(test_linalg('test_dot_diag_t_float32'))
    s.addTest(test_linalg('test_dot_diag_t_complex64'))
    s.addTest(test_linalg('test_transpose_float32'))
    s.addTest(test_linalg('test_transpose_complex64'))
    s.addTest(test_linalg('test_hermitian_float32'))
    s.addTest(test_linalg('test_hermitian_complex64'))
    s.addTest(test_linalg('test_conj_complex64'))
    s.addTest(test_linalg('test_diag_float32'))
    s.addTest(test_linalg('test_diag_complex64'))
    s.addTest(test_linalg('test_eye_float32'))
    s.addTest(test_linalg('test_eye_complex64'))
    s.addTest(test_linalg('test_pinv_float32'))
    s.addTest(test_linalg('test_pinv_complex64'))
    s.addTest(test_linalg('test_tril_float32'))
    s.addTest(test_linalg('test_tril_complex64'))
    s.addTest(test_linalg('test_multiply_float32'))
    s.addTest(test_linalg('test_multiply_complex64'))
    if misc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
        s.addTest(test_linalg('test_svd_ss_float64'))
        s.addTest(test_linalg('test_svd_ss_complex128'))
        s.addTest(test_linalg('test_svd_so_float64'))
        s.addTest(test_linalg('test_svd_so_complex128'))
        s.addTest(test_linalg('test_dot_matrix_float64'))
        s.addTest(test_linalg('test_dot_matrix_complex128'))
        s.addTest(test_linalg('test_dot_matrix_t_float64'))
        s.addTest(test_linalg('test_dot_matrix_t_complex128'))
        s.addTest(test_linalg('test_dot_matrix_h_complex128'))
        s.addTest(test_linalg('test_dot_vector_float64'))
        s.addTest(test_linalg('test_dot_vector_complex128'))
        s.addTest(test_linalg('test_mdot_matrix_float64'))
        s.addTest(test_linalg('test_mdot_matrix_complex128'))
        s.addTest(test_linalg('test_dot_diag_float64'))
        s.addTest(test_linalg('test_dot_diag_complex128'))
        s.addTest(test_linalg('test_dot_diag_t_float64'))
        s.addTest(test_linalg('test_dot_diag_t_complex128'))
        s.addTest(test_linalg('test_transpose_float64'))
        s.addTest(test_linalg('test_transpose_complex128'))
        s.addTest(test_linalg('test_hermitian_float64'))
        s.addTest(test_linalg('test_hermitian_complex64'))
        s.addTest(test_linalg('test_conj_complex128'))
        s.addTest(test_linalg('test_diag_float64'))
        s.addTest(test_linalg('test_diag_complex128'))
        s.addTest(test_linalg('test_eye_float64'))
        s.addTest(test_linalg('test_eye_complex128'))
        s.addTest(test_linalg('test_pinv_float64'))
        s.addTest(test_linalg('test_pinv_complex128'))        
        s.addTest(test_linalg('test_tril_float64'))
        s.addTest(test_linalg('test_tril_complex128'))
        s.addTest(test_linalg('test_multiply_float64'))
        s.addTest(test_linalg('test_multiply_complex128'))
    return s

if __name__ == '__main__':
    main(defaultTest = 'suite')

########NEW FILE########
__FILENAME__ = test_misc
#!/usr/bin/env python

"""
Unit tests for scikits.cuda.misc
"""

from unittest import main, TestCase, TestSuite

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np

import scikits.cuda.misc as misc

class test_misc(TestCase):        
    def test_maxabs_float32(self):
        x = np.array([-1, 2, -3], np.float32)
        x_gpu = gpuarray.to_gpu(x)
        m_gpu = misc.maxabs(x_gpu)
        assert np.allclose(m_gpu.get(), np.max(np.abs(x)))

    def test_maxabs_float64(self):
        x = np.array([-1, 2, -3], np.float64)
        x_gpu = gpuarray.to_gpu(x)
        m_gpu = misc.maxabs(x_gpu)
        assert np.allclose(m_gpu.get(), np.max(np.abs(x)))

    def test_maxabs_complex64(self):
        x = np.array([-1j, 2, -3j], np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        m_gpu = misc.maxabs(x_gpu)
        assert np.allclose(m_gpu.get(), np.max(np.abs(x)))

    def test_maxabs_complex128(self):
        x = np.array([-1j, 2, -3j], np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        m_gpu = misc.maxabs(x_gpu)
        assert np.allclose(m_gpu.get(), np.max(np.abs(x)))

    def test_cumsum_float32(self):
        x = np.array([1, 4, 3, 2, 8], np.float32)
        x_gpu = gpuarray.to_gpu(x)
        c_gpu = misc.cumsum(x_gpu)
        assert np.allclose(c_gpu.get(), np.cumsum(x))

    def test_cumsum_float64(self):
        x = np.array([1, 4, 3, 2, 8], np.float64)
        x_gpu = gpuarray.to_gpu(x)
        c_gpu = misc.cumsum(x_gpu)
        assert np.allclose(c_gpu.get(), np.cumsum(x))

    def test_cumsum_complex64(self):
        x = np.array([1, 4j, 3, 2j, 8], np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        c_gpu = misc.cumsum(x_gpu)
        assert np.allclose(c_gpu.get(), np.cumsum(x))

    def test_cumsum_complex128(self):
        x = np.array([1, 4j, 3, 2j, 8], np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        c_gpu = misc.cumsum(x_gpu)
        assert np.allclose(c_gpu.get(), np.cumsum(x))

    def test_diff_float32(self):
        x = np.array([1.3, 2.7, 4.9, 5.1], np.float32)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = misc.diff(x_gpu)
        assert np.allclose(y_gpu.get(), np.diff(x))

    def test_diff_float64(self):
        x = np.array([1.3, 2.7, 4.9, 5.1], np.float64)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = misc.diff(x_gpu)
        assert np.allclose(y_gpu.get(), np.diff(x))

    def test_diff_complex64(self):
        x = np.array([1.3+2.0j, 2.7-3.9j, 4.9+1.0j, 5.1-9.0j], np.complex64)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = misc.diff(x_gpu)
        assert np.allclose(y_gpu.get(), np.diff(x))

    def test_diff_complex128(self):
        x = np.array([1.3+2.0j, 2.7-3.9j, 4.9+1.0j, 5.1-9.0j], np.complex128)
        x_gpu = gpuarray.to_gpu(x)
        y_gpu = misc.diff(x_gpu)
        assert np.allclose(y_gpu.get(), np.diff(x))

def suite():
    s = TestSuite()
    s.addTest(test_misc('test_maxabs_float32'))
    s.addTest(test_misc('test_maxabs_complex64'))
    s.addTest(test_misc('test_cumsum_float32'))
    s.addTest(test_misc('test_cumsum_complex64'))
    s.addTest(test_misc('test_diff_float32'))
    s.addTest(test_misc('test_diff_complex64'))
    if misc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
        s.addTest(test_misc('test_maxabs_float64'))
        s.addTest(test_misc('test_maxabs_complex128'))
        s.addTest(test_misc('test_cumsum_float64'))
        s.addTest(test_misc('test_cumsum_complex128'))
        s.addTest(test_misc('test_diff_float64'))
        s.addTest(test_misc('test_diff_complex128'))
    return s

if __name__ == '__main__':
    main(defaultTest = 'suite')

########NEW FILE########
__FILENAME__ = test_special
#!/usr/bin/env python

"""
Unit tests for scikits.cuda.linalg
"""


from unittest import main, makeSuite, TestCase, TestSuite

import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import numpy as np
import scipy as sp
import scipy.special

import scikits.cuda.linalg as linalg
import scikits.cuda.misc as misc
import scikits.cuda.special as special

class test_special(TestCase):
    def setUp(self):
        linalg.init()
        
    def test_sici_float32(self):
        x = np.array([[1, 2], [3, 4]], np.float32)
        x_gpu = gpuarray.to_gpu(x)
        (si_gpu, ci_gpu) = special.sici(x_gpu)
        (si, ci) = scipy.special.sici(x)
        assert np.allclose(si, si_gpu.get())
        assert np.allclose(ci, ci_gpu.get())

    def test_sici_float64(self):
        x = np.array([[1, 2], [3, 4]], np.float64)
        x_gpu = gpuarray.to_gpu(x)
        (si_gpu, ci_gpu) = special.sici(x_gpu)
        (si, ci) = scipy.special.sici(x)
        assert np.allclose(si, si_gpu.get())
        assert np.allclose(ci, ci_gpu.get())

    def test_exp1_complex64(self):
        z = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex64)
        z_gpu = gpuarray.to_gpu(z)
        e_gpu = special.exp1(z_gpu)
        assert np.allclose(sp.special.exp1(z), e_gpu.get())   

    def test_exp1_complex128(self):
        z = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex128)
        z_gpu = gpuarray.to_gpu(z)
        e_gpu = special.exp1(z_gpu)
        assert np.allclose(sp.special.exp1(z), e_gpu.get())   

    def test_expi_complex64(self):
        z = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex64)
        z_gpu = gpuarray.to_gpu(z)
        e_gpu = special.expi(z_gpu)
        assert np.allclose(sp.special.expi(z), e_gpu.get())   

    def test_expi_complex128(self):
        z = np.asarray(np.random.rand(4, 4) + 1j*np.random.rand(4, 4), np.complex128)
        z_gpu = gpuarray.to_gpu(z)
        e_gpu = special.expi(z_gpu)
        assert np.allclose(sp.special.expi(z), e_gpu.get())   

def suite():
    s = TestSuite()
    s.addTest(test_special('test_sici_float32'))
    s.addTest(test_special('test_exp1_complex64'))
    s.addTest(test_special('test_expi_complex64'))
    if misc.get_compute_capability(pycuda.autoinit.device) >= 1.3:
        s.addTest(test_special('test_sici_float64'))
        s.addTest(test_special('test_exp1_complex128'))
        s.addTest(test_special('test_expi_complex128'))
    return s

if __name__ == '__main__':
    main(defaultTest = 'suite')

########NEW FILE########
