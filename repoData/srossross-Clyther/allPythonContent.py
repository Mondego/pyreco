__FILENAME__ = array_context
'''
Created on Dec 17, 2011

@author: sean
'''

import opencl as cl
import new

class CLArrayContext(cl.Context):
    '''
    classdocs
    '''
    
    def __init__(self, *args, **kwargs):
        cl.Context.__init__(self, *args, **kwargs)
        
        self._queue = cl.Queue(self)
    
    @property
    def queue(self):
        return self._queue
    

    @classmethod
    def method(cls, name):
        def decoator(func):
            meth = new.instancemethod(func, None, cls)
            setattr(cls, name, meth)
            return func
        return decoator
    
    @classmethod
    def func(cls, func):
        if isinstance(func, str):
            name = func
            def decoator(func):
                setattr(cls, name, func)
                return func
            return decoator
        else:
            setattr(cls, func.func_name, func)
            return func

########NEW FILE########
__FILENAME__ = blitz
'''
Created on Dec 13, 2011

@author: sean
'''
from meta.decompiler import decompile_func
from meta.asttools.visitors import Visitor
import ast
from meta.asttools.visitors.print_visitor import print_ast

import clyther as cly
import clyther.runtime as clrt
import opencl as cl

from clyther.array.utils import broadcast_shapes

n = lambda node: {'lineno':node.lineno, 'col_offset': node.col_offset}

class BlitzVisitor(Visitor):
    
    def __init__(self, filename, func_globals):
        self.filename = filename
        self.func_globals = func_globals
        self.locls = {}
        self.count = 0
        
    
    def new_var(self):
        self.count += 1
        return 'var%03i' % self.count
    
    def visitLambda(self, node):
        body = self.visit(node.body)
        
        args = ast.arguments(args=[], vararg=None, kwarg=None, defaults=[])
        
        for var_id in sorted(self.locls.keys()):
            args.args.append(ast.Name(var_id, ast.Param(), **n(node))) 
        return ast.Lambda(args, body, **n(node))
    
    def visitDefault(self, node):
        codeobj = compile(ast.Expression(node), self.filename, 'eval')
        value = eval(codeobj, self.func_globals)
        
        var_id = self.new_var()
        
        self.locls[var_id] = value
        
        return ast.Name(var_id, ast.Load(), **n(node))
    
    def visitBinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        return ast.BinOp(left, node.op, right, **n(node))

blitzed_kernel_py_source = '''
def blitzed_kernel(function, out, {args}):
    gid = clrt.get_global_id(0)
    
    {arg_index}
    
    out[gid] = function({arg_values})
'''

def create_n_arg_kernel(keys):
    args = ', '.join(key for key in keys) 
    arg_values = ', '.join('%s_i' % key for key in keys) 
    arg_index = '\n    '.join('%s_i = %s[gid]' % (arg, arg) for arg in keys) 
    
    py_source = blitzed_kernel_py_source.format(args=args, arg_index=arg_index, arg_values=arg_values)

    locls = {}
    eval(compile(py_source, '', 'exec'), globals(), locls)
    
    blitzed_kernel = cly.kernel(locls['blitzed_kernel'])
    blitzed_kernel.global_work_size = eval(compile('lambda %s: [%s.size]' % (keys[0], keys[0]), '', 'eval'))

    return blitzed_kernel
     
def blitz(queue, func, out=None):
    '''
    lets get blitzed!
    '''
    func_ast = decompile_func(func)
    
    func_globals = func.func_globals.copy()
    
    if func.func_closure:
        func_globals.update({name:cell.cell_contents for name, cell in zip(func.func_code.co_freevars, func.func_closure)}) 
        
    blitzer = BlitzVisitor(func.func_code.co_filename, func_globals)
    
    blitzed = ast.Expression(blitzer.visit(func_ast))
    
    blitzed_code = compile(blitzed, func.func_code.co_filename, 'eval')
    blitzed_func = eval(blitzed_code)
    
    blitz_kernel = create_n_arg_kernel(sorted(blitzer.locls.keys()))
    
    args = {}
    
    for key, var in blitzer.locls.items():
        if not isinstance(var, cl.DeviceMemoryView):
            var = cl.from_host(queue.context, var)
        args[key] = var
        
    shape = broadcast_shapes([var.shape for var in args.values()])
    
    print "shape", shape
    
    for key, var in args.items():
        args[key] = cl.broadcast(var, shape)
        
    print "out, **args", out, args
    blitz_kernel(queue, blitzed_func, out, **args)
    
#    print blitzed_func()
    
    
    
    
    

########NEW FILE########
__FILENAME__ = clarray
'''
Created on Dec 7, 2011

@author: sean
'''


from contextlib import contextmanager
import numpy as np
import opencl as cl

    
class CLArray(cl.DeviceMemoryView):
    
    def __new__(cls, *args):
        return cl.DeviceMemoryView.__new__(cls, *args)

#    def __init__(self, context):
#        pass
    
    def __array_init__(self, context, queue):
        self.acontext = context
        
        if queue is None:
            queue = context.queue
        
        self.queue = queue
        
    def __repr__(self):
        with self.map() as view:
            array_str = str(view)
            return  '%s(%s, ctype=%s, devices=%r)' % (type(self).__name__, array_str, self.ctype, self.context.devices)

    def __str__(self):
        with self.map() as view:
            return  str(view)
        
    def __add__(self, other):
        view = self.acontext.add(self, other)
        
        return view

    def __radd__(self, other):
        view = self.acontext.add(other, self)
        
        return view
    
    def __mul__(self, other):
        view = self.acontext.multiply(self, other)
        
        return view

    def __rmul__(self, other):
        view = self.acontext.multiply(other, self)
        
        return view

    def __sub__(self, other):
        view = self.acontext.subtract(self, other)
        
        return view
    
    def __rsub__(self, other):
        view = self.acontext.subtract(other, self)
        
        return view
    
    def __pow__(self, other):
        view = self.acontext.power(self, other)
        return view

    def sum(self):
        
        from ufuncs import add
        
        view = add.reduce(self)
        
        return view
    
    @contextmanager
    def map(self, queue=None):
        if queue is None:
            queue = self.queue
        with cl.DeviceMemoryView.map(self, queue) as memview:
            yield  np.asarray(memview)
    
    def copy(self):
        view = cl.DeviceMemoryView.copy(self, self.queue)
        array = self._view_as_this(view)
        array.__array_init__(self.acontext, self.queue)
        return array
    
    def item(self):
        value = cl.DeviceMemoryView.item(self, self.queue)
        self.queue.finish()
        return value
    
    def __getitem__(self, item):
        view = cl.DeviceMemoryView.__getitem__(self, item)
        array = self._view_as_this(view)
        array.__array_init__(self.acontext, self.queue)
        return array
    
    def __setitem__(self, item, value):
        self.acontext.setslice(self[item], value)
    
    def reshape(self, shape):
        
        view = cl.DeviceMemoryView.reshape(self, shape)

        array = self._view_as_this(view)
        array.__array_init__(self.acontext, self.queue)
        return array
        
        

########NEW FILE########
__FILENAME__ = functions
'''
Created on Dec 7, 2011

@author: sean
'''
import math
import clyther as cly
import clyther.runtime as clrt
import opencl as cl
from opencl.type_formats import ctype_from_format
from ctypes import c_int, c_float

from clyther.array.clarray import CLArray
from clyther.array.utils import broadcast_shape
from clyther.array.array_context import CLArrayContext as ArrayContext

@cly.global_work_size(lambda arr, *_: arr.shape)
@cly.kernel
def setslice_kernel(arr, value):
    index = cl.cl_uint4(clrt.get_global_id(0), clrt.get_global_id(1), clrt.get_global_id(2), 0)
    
    
    a_strides = index * arr.strides
    aidx = arr.offset + a_strides.x + a_strides.y + a_strides.z
    
    v_strides = index * value.strides
    vidx = value.offset + v_strides.x + v_strides.y + v_strides.z

    arr[aidx] = value[vidx]


@ArrayContext.method('setslice')
def setslice(context, arr, value):
    
    if not isinstance(value, cl.DeviceMemoryView):
        value = context.asarray(value)
       
    if value.queue != arr.queue:
        arr.queue.enqueue_wait_for_events(value.queue.marker())
         
    value = cl.broadcast(value, arr.shape)
    
    kernel = setslice_kernel.compile(context, arr=cl.global_memory(arr.format, flat=True),
                                     value=cl.global_memory(value.format, flat=True),
                                     cly_meta='setslice')
    
    return kernel(arr.queue, arr, arr.array_info, value, value.array_info)

@ArrayContext.method('asarray')
def asarray(ctx, other, queue=None, copy=True):
    
    if not isinstance(other, cl.DeviceMemoryView):
        other = cl.from_host(ctx, other, copy=copy)
        
    array = CLArray._view_as_this(other)
    array.__array_init__(ctx, queue)
    
    return array

@ArrayContext.method('zeros')
def zeros(context, shape, ctype='f', cls=CLArray, queue=None):
    
    out = context.empty(shape=shape, ctype=ctype, queue=queue)
    
    setslice(context, out, 0)
    
    return out

@ArrayContext.method('empty')
def empty(context, shape, ctype='f', cls=CLArray, queue=None):
    out = cl.empty(context, shape, ctype)
    
    array = cls._view_as_this(out)
    array.__array_init__(context, queue)
    return array

@ArrayContext.method('empty_like')
def empty_like(context, A):
    return context.empty(A.shape, A.format, cls=type(A), queue=A.queue)
    

@cly.global_work_size(lambda a, *_: [a.size])
@cly.kernel
def _arange(a, start, step):
    i = clrt.get_global_id(0)
    a[i] = start + step * i 
 
@ArrayContext.method('arange')
def arange(ctx, *args, **kwargs):
    '''
    
    '''
    start = 0.0
    step = 1.0
    
    if len(args) == 1:
        stop = args[0]  
    elif len(args) == 2:
        start = args[0]
        stop = args[1]
    elif len(args) == 3:
        start = args[0]
        stop = args[1]
        step = args[2]
    else:
        raise Exception("wrong number of arguments expected between 2-4 (got %i)" % (len(args) + 1))
    
    size = int(math.ceil((stop - start) / float(step)))
    
    ctype = kwargs.get('ctype', 'f')
    
    queue = kwargs.get('queue', None)
    if queue is None:
        queue = cl.Queue(ctx) 

    arr = empty(ctx, [size], ctype=ctype, queue=queue)
    
    _arange(queue, arr, start, step)
    
    return arr

@cly.global_work_size(lambda a, *_: [a.size])
@cly.kernel
def _linspace(a, start, stop):
    i = clrt.get_global_id(0)
    gsize = clrt.get_global_size(0)
    a[i] = i * (stop - start) / gsize 
 
@ArrayContext.method('linspace')
def linspace(ctx, start, stop, num=50, ctype='f', queue=None):
    '''
    
    '''
    
    if queue is None:
        queue = cl.Queue(ctx) 

    arr = empty(ctx, [num], ctype=ctype, queue=queue)
    _linspace(queue, arr, float(start), float(stop))
    
    return arr
    
    
    
def main():
    
    import opencl as cl
    ctx = cl.Context(device_type=cl.Device.GPU)
    a = arange(ctx, 10.0)

if __name__ == '__main__':
    main()
        

########NEW FILE########
__FILENAME__ = reduce_array
'''
Created on Dec 15, 2011

@author: sean
'''
import clyther as cly
import clyther.runtime as clrt
import opencl as cl
from ctypes import c_float, c_int, c_uint
import numpy as np
import ctypes
from meta.decompiler import decompile_func
from meta.asttools.visitors.pysourcegen import python_source

@cly.global_work_size(lambda group_size: [group_size])
@cly.local_work_size(lambda group_size: [group_size])
@cly.kernel
def cl_reduce(function, output, input, shared, group_size, initial=0.0):
    
    i = c_uint(0)
    
    lid = clrt.get_local_id(0)

    gid = clrt.get_group_id(0)
    gsize = clrt.get_num_groups(0)

    gs2 = group_size * 2

    stride = gs2 * gsize

    i = gid * gs2 + lid

    shared[lid] = initial

    while i < input.size:
        shared[lid] = function(shared[lid], input[i])
        shared[lid] = function(shared[lid], input[i + group_size])
         
        i += stride
        
        clrt.barrier(clrt.CLK_LOCAL_MEM_FENCE)
        
    #The clyther compiler identifies this loop as a constant a
    # unrolls this loop 
    for cgs in [512 , 256, 128, 64, 32, 16, 8, 4, 2]:
        
        #acts as a preprocessor define #if (group_size >= 512) etc. 
        if group_size >= cgs:
            
            if lid < cgs / 2:
                shared[lid] = function(shared[lid] , shared[lid + cgs / 2])
                 
            clrt.barrier(clrt.CLK_LOCAL_MEM_FENCE)
            
    if lid == 0:
        output[gid] = shared[0]

def reduce(queue, function, input, initial=0.0):
    '''
    reduce(queue, function, sequence[, initial]) -> value
    
    Apply a function of two arguments cumulatively to the items of a sequence,
    from left to right, so as to reduce the sequence to a single value.
    For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5]) calculates
    ((((1+2)+3)+4)+5).  If initial is present, it is placed before the items
    of the sequence in the calculation, and serves as a default when the
    sequence is empty.

    '''

    size = input.size
    shared = cl.local_memory(input.format, [size])
    output = cl.empty(queue.context, [1], input.format)
    
    group_size = size // 2
    
    cl_reduce(queue, function, output, input , shared, group_size, initial)
    
    return output

########NEW FILE########
__FILENAME__ = ufuncs
'''
Created on Dec 7, 2011

@author: sean
'''
from clyther.array.ufunc_framework import binary_ufunc, unary_ufunc
import clyther.runtime as clrt 
from clyther.array.array_context import CLArrayContext

@CLArrayContext.method('add')
@binary_ufunc
def add(a, b):
    return a + b

sum = CLArrayContext.method("sum")(add.reduce)


@CLArrayContext.method('subtract')
@binary_ufunc
def subtract(a, b):
    return a - b


@CLArrayContext.method('power')
@binary_ufunc
def power(a, b):
    return a ** b


@CLArrayContext.method('multiply')
@binary_ufunc
def multiply(a, b):
    return a * b

@CLArrayContext.method('sin')
@unary_ufunc
def cly_sin(x):
    return clrt.sin(x)

sin = cly_sin


########NEW FILE########
__FILENAME__ = ufunc_framework
'''
Created on Dec 7, 2011

@author: sean
'''
import clyther as cly
import clyther.runtime as clrt
import opencl as cl
from ctypes import c_uint

from clyther.array.utils import broadcast_shape
from clyther.array.clarray import CLArray

@cly.global_work_size(lambda group_size: [group_size])
@cly.local_work_size(lambda group_size: [group_size])
@cly.kernel
def reduce_kernel(function, output, array, shared, group_size):
    
    lid = clrt.get_local_id(0)
    gid = clrt.get_group_id(0)

    stride = group_size
    
    i = c_uint(gid * group_size + lid)
    
    igs = i + group_size
    
    tmp = array[i]
    
    if igs < array.size:
        tmp = function(tmp, array[igs])
        
    i += stride*2
        
    while i < array.size:
        tmp = function(tmp, array[i])
        i += stride
        
    shared[lid] = tmp
    clrt.barrier(clrt.CLK_LOCAL_MEM_FENCE)
        
    #The clyther compiler identifies this loop as a constant a
    # unrolls this loop 
    for cgs in [512 , 256, 128, 64, 32, 16, 8, 4, 2]:
        
        #acts as a preprocessor define #if (group_size >= 512) etc. 
        if group_size >= cgs:
            
            if lid < cgs / 2:
                shared[lid] = function(shared[lid] , shared[lid + cgs / 2])
                 
            clrt.barrier(clrt.CLK_LOCAL_MEM_FENCE)
            
    if lid == 0:
        output[gid] = shared[0]
        
@cly.global_work_size(lambda a: a.shape)
@cly.kernel
def ufunc_kernel(function, a, b, out):
    
    index = cl.cl_uint4(clrt.get_global_id(0), clrt.get_global_id(1), clrt.get_global_id(2), 0)
    
    
    a_strides = index * a.strides
    aidx = a.offset + a_strides.x + a_strides.y + a_strides.z
    
    b_strides = index * b.strides
    bidx = b.offset + b_strides.x + b_strides.y + b_strides.z

    out_strides = index * out.strides
    oidx = out.offset + out_strides.x + out_strides.y + out_strides.z
        
    a0 = a[aidx]
    b0 = b[bidx]
    
    out[oidx] = function(a0, b0) 
        


class BinaryUfunc(object):
    def __init__(self, device_func):
        self.device_func = device_func
        
    def __call__(self, context, x, y, out=None, queue=None):
        
        if queue is None:
            if hasattr(x,'queue'):
                queue = x.queue
            elif hasattr(y,'queue'):
                queue = y.queue
            else:
                queue = context.queue
            
            
        if not isinstance(x, cl.DeviceMemoryView):
            x = context.asarray(x)
        if not isinstance(y, cl.DeviceMemoryView):
            y = context.asarray(y)
        
        if y.queue != queue:
            queue.enqueue_wait_for_events(y.queue.marker())
        if x.queue != queue:
            queue.enqueue_wait_for_events(x.queue.marker())
        
        new_shape = broadcast_shape(x.shape, y.shape)
        
        a = cl.broadcast(x, new_shape)
        b = cl.broadcast(y, new_shape)
        
        if out is None:
            out = context.empty(shape=new_shape, ctype=x.format, queue=queue)
        
#        kernel_source = ufunc_kernel._compile(queue.context, function=self.device_func,
#                                      a=cl.global_memory(a.format, flat=True),
#                                      b=cl.global_memory(b.format, flat=True),
#                                      out=cl.global_memory(out.format, flat=True), source_only=True)

        kernel = ufunc_kernel.compile(context, function=self.device_func,
                                      a=cl.global_memory(a.format, flat=True),
                                      b=cl.global_memory(b.format, flat=True),
                                      out=cl.global_memory(out.format, flat=True), 
                                      cly_meta=self.device_func.func_name)
        

        kernel(queue, a, a.array_info, b, b.array_info, out, out.array_info)
        
        array = CLArray._view_as_this(out)
        array.__array_init__(context, queue)
        return array
    
    def reduce(self, context, x, out=None, initial=0.0, queue=None):
        
        if queue is None:
            queue = x.queue
        
        if not isinstance(x, cl.DeviceMemoryView):
            x = cl.from_host(queue.context, x)
            
        #output, input, shared, group_size, initial=0.0
        size = x.size
        shared = cl.local_memory(x.ctype, ndim=1, shape=[size])
        
        group_size = size // 2
        for item in [2, 4, 8, 16, 32, 64, 128, 256, 512]:
            if group_size < item:
                group_size = item // 2
                break
        else:
            group_size = 512
        
        if out is None:
            out = cl.empty(queue.context, [1], x.format)
        
        kernel = reduce_kernel.compile(queue.context,
                                       function=self.device_func,
                                       output=cl.global_memory(out.ctype, flat=True),
                                       array=cl.global_memory(x.ctype, flat=True),
                                       shared=shared,
                                       group_size=cl.cl_uint,
                                       cly_meta=self.device_func.func_name)
        
        max_wgsize = kernel.work_group_size(queue.device)
        
        group_size = min(max_wgsize, group_size)
        
        kernel(queue, out, out.array_info, x, x.array_info, shared, shared.local_info, group_size)
#        reduce_kernel(queue, self.device_func, out, x, shared, group_size)
#        reduce_kernel(queue, self.device_func, out, x, shared, group_size)
        
        array = CLArray._view_as_this(out)
        array.__array_init__(context, queue)
        return array


@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def unary_ufunc_kernel(function, a, out):
    gid = clrt.get_global_id(0)
    
    a0 = a[gid]
    out[gid] = function(a0)
    
class UnaryUfunc(object):
    def __init__(self, device_func):
        self.device_func = device_func
        
    def __call__(self, x, out=None, queue=None):
        
        if queue is None:
            queue = x.queue

        if not isinstance(x, cl.DeviceMemoryView):
            x = cl.from_host(queue.context, x)
        
        if out is None:
            out = cl.empty(queue.context, x.shape, x.format)
        
        unary_ufunc_kernel(queue, self.device_func, x, out)
        
        array = CLArray._view_as_this(out)
        array.__array_init__(queue)
        return array
    
def binary_ufunc(device_func):
    return BinaryUfunc(device_func)

def unary_ufunc(device_func):
    return UnaryUfunc(device_func)


########NEW FILE########
__FILENAME__ = utils
'''
Created on Dec 13, 2011

@author: sean
'''

    
def broadcast_shapes(shapes):
    return reduce(broadcast_shape, shapes)
    
def broadcast_shape(shape1, shape2):
    max_shape = max(shape1, shape2, key=lambda item: (len(item), item))
    min_shape = min(shape1, shape2, key=lambda item: (len(item), item))
    
    ndim = len(max_shape)
    noff = len(max_shape) - len(min_shape)
    
    new_shape = list(max_shape)
    for i in range(noff, ndim):
        if (new_shape[i] == 1) ^ (min_shape[i - noff] == 1):
            new_shape[i] = max(new_shape[i], min_shape[i - noff])
        elif new_shape[i] == min_shape[i - noff]:
            continue
        elif (new_shape[i] != 1) and (min_shape[i - noff] != 1):
            raise ValueError("shape mismatch: objects cannot be broadcast to a single shape")
        
    return tuple(new_shape)

########NEW FILE########
__FILENAME__ = caching
import _ctypes
from inspect import isfunction, isclass
import pickle
import opencl as cl

class KernelCache(object):
    '''
    Basic Cache object.
    '''
    def generate_key(self, kwarg_types):
        '''
        create a hashable key from argument type dict.
        '''
        arlist = []
        for key, value in sorted(kwarg_types.viewitems(), key=lambda item:item[0]):
            CData = _ctypes._SimpleCData.mro()[1]
            if isfunction(value):
                value = (value.func_name, hash(value.func_code.co_code))
            elif isclass(value) and issubclass(value, CData):
                value = hash(pickle.dumps(value))
            else:
                value = hash(value)
                
            arlist.append((key, value))
        
        return hash(tuple(arlist))

    def __contains__(self, item):
        #ctx, func, cache_key = item
        raise NotImplementedError("This is an abstract class")
    
    def get(self, ctx, func, cache_key):
        raise NotImplementedError("This is an abstract class")
    
    def set(self, ctx, func, cache_key,
                  args, defaults, kernel_name, cly_meta, source,
                  binaries):
        raise NotImplementedError("This is an abstract class")

class NoFileCache(KernelCache):
    '''
    This is the default. It never caches a kernel's binary to disk. 
    '''
    
    def __contains__(self, item):
        #ctx, func, cache_key = item
        return False
    
    def get(self, ctx, func, cache_key):
        raise NotImplementedError("This object does not support caching use 'HDFCache' to cache to disk")
    
    def set(self, ctx, func, cache_key,
                  args, defaults, kernel_name, cly_meta, source,
                  binaries):
        pass
    

class HDFCache(NoFileCache):
    '''
    Cache a clyher.kernel to disk. 
    '''
    
    def __init__(self, kernel):
        # file://ff.h5.cly:/function_name/<hash of code obj>/<hash of arguments>/<device binary>
        try:
            import h5py
        except ImportError:
            raise NotImplementedError("import h5py failed. can not use HDFCache object")
        
        self.hf = h5py.File(kernel.db_filename)
    
    
    def __contains__(self, item):
        ctx, func, cache_key = item

        
        kgroup = self.hf.require_group(func.func_name)
        cgroup = kgroup.require_group(hex(hash(func.func_code)))
        tgroup = cgroup.require_group(hex(hash(cache_key)))
        
        have_compiled_version = all([device.name in tgroup.keys() for device in ctx.devices])
        
        return have_compiled_version

    
    def get(self, ctx, func, cache_key):
        
        kgroup = self.hf.require_group(func.func_name)
        cgroup = kgroup.require_group(hex(hash(func.func_code)))
        tgroup = cgroup.require_group(hex(hash(cache_key)))

#        source = cgroup.attrs['source']
        args = pickle.loads(tgroup.attrs['args'])
        defaults = pickle.loads(tgroup.attrs['defaults'])
        kernel_name = tgroup.attrs['kernel_name']

        binaries = {}
        for device in ctx.devices:
            binaries[device] = tgroup[device.name].value
            
        program = cl.Program(ctx, binaries=binaries)
        program.build()
        
        program, kernel_name, args, defaults
    
    def set(self, ctx, func, cache_key,
                  args, defaults, kernel_name, cly_meta, source,
                  binaries):
        
        kgroup = self.hf.require_group(func.func_name)
        cgroup = kgroup.require_group(hex(hash(func.func_code)))
        tgroup = cgroup.require_group(hex(hash(cache_key)))

        tgroup.attrs['args'] = pickle.dumps(args)
        tgroup.attrs['defaults'] = pickle.dumps(defaults)
        tgroup.attrs['kernel_name'] = kernel_name
        tgroup.attrs['meta'] = str(cly_meta)
        cgroup.attrs['source'] = source
        
        for device, binary in binaries.items():
            if device.name not in tgroup.keys():
                tgroup.create_dataset(device.name, data=binary)



########NEW FILE########
__FILENAME__ = cast
'''
Created on Nov 29, 2011

@author: sean
'''
import ast

class CError(Exception):
    def __init__(self, node, exc, msg):
        self.exc = exc
        self.node = node
        self.msg = msg
        Exception.__init__(self,  node, exc, msg)
    
class CTypeCast(ast.expr):
    _fields = 'value', 'ctype'
    
class CVectorTypeCast(ast.expr):
    _fields = 'values', 'ctype'
    
class Comment(ast.AST):
    _fields = 's',
    
class CGroup(ast.AST):
    _fields = 'body',
    
class CTypeName(ast.AST):
    _fields = 'typename',

class CVarDec(ast.AST):
    _fields = 'id', 'ctype',
    
class CNum(ast.Num):
    _fields = 'n', 'ctype'
    
class CStr(ast.Str):
    _fields = 's', 'ctype'
    
class CCall(ast.Call):
    _fields = 'func', 'args', 'keywords', 'ctype'
    
class CReturn(ast.AST):
    _fields = 'value', 'ctype'
    
class CFunctionForwardDec(ast.AST):
    _fields = 'name', 'args', 'return_type'
    
class CFunctionDef(ast.AST):
    _fields = 'name', 'args', 'body', 'decorator_list', 'return_type'
        
class CName(ast.Name):
    _fields = 'id', 'ctx', 'ctype'

class CBinOp(ast.AST):
    _fields = 'left', 'op', 'right', 'ctype'

class CUnaryOp(ast.AST):
    _fields = 'op', 'operand', 'ctype'

class ckeyword(ast.AST):
    _fields = 'arg', 'value', 'ctype'
    
class clkernel(ast.AST):
    _fields = ()

class CSubscript(ast.Subscript):
    _fields = 'value', 'slice', 'ctx', 'ctype'
    
class CAttribute(ast.Attribute):
    _fields = 'value', 'attr', 'ctx', 'ctype'
    
class CPointerAttribute(ast.Attribute):
    _fields = 'value', 'attr', 'ctx', 'ctype'

class CIfExp(ast.IfExp):
    _fields = 'test', 'body', 'orelse', 'ctype'
    
class CCompare(ast.Compare):
    _fields = 'left', 'ops', 'comparators', 'ctype'

class CFor(ast.AST):
    _fields = 'init', 'condition', 'increment', 'body', 'orelse'

class CStruct(ast.AST):
    _fields = "id", 'declaration_list'
    
class CAssignExpr(ast.expr):
    _fields = 'targets', 'value', 'ctype'
    
class CAugAssignExpr(ast.expr):
    _fields = 'target', 'op', 'value', 'ctype'

class CList(ast.List):
    _fields = 'elts', 'ctx', 'ctype'


class CBoolOp(ast.BoolOp):
    _fields = 'op', 'values', 'ctype'

#===============================================================================
# 
#===============================================================================
class FuncPlaceHolder(object):
    def __init__(self, name, key, node):
        self.name = name
        self.key = key
        self.node = node
        
    def __repr__(self):
        return 'placeholder(%r)' % (self.name)

def n(node):
    return {'lineno':node.lineno, 'col_offset':node.col_offset}


def build_forward_dec(func_def):
    return CFunctionForwardDec(func_def.name, func_def.args, func_def.return_type)



    




########NEW FILE########
__FILENAME__ = for_loops
'''
Created on Dec 7, 2011

@author: sean
'''
from meta.asttools.visitors import Mutator
from meta.asttools.visitors.print_visitor import print_ast
from clyther.clast import cast
from clyther.pybuiltins import cl_range
import ctypes
import ast
from clyther.rttt import cList
from meta.asttools.visitors.copy_tree import copy_node

class ReplaceCNameMutator(Mutator):
    def __init__(self, nameid, with_node):
        self.nameid = nameid
        self.with_node = with_node
        
    def mutateCName(self, node):
        if node.id == self.nameid:
            return copy_node(self.with_node)
    
def replace_cname(nodes, nameid, with_node):
    
    if not isinstance(nodes, (list, tuple)):
        nodes = (nodes,)
        
    for node in nodes:
        ReplaceCNameMutator(nameid, with_node).mutate(node)
    
class UnrollLoopMutator(Mutator):
    def mutateFor(self, node):
        if not isinstance(node.iter.ctype, cList):
            return
            
        body_items = [cast.Comment("UnrollLoopMutator")]
        for i, item in enumerate(node.iter.elts):
            body_items.append(cast.Comment("UnrollLoopMutator loop: %i" % i))
            body = [copy_node(stmnt) for stmnt in node.body] 
            replace_cname(body, node.target.id, item)
            body_items.extend(body)
        
        body_items.append(cast.Comment("UnrollLoopMutator End"))
        return cast.CGroup(body_items)

class ForLoopMutator(Mutator):
    def mutateFor(self, node):
        
        if not isinstance(node.iter.ctype, cl_range):
            orelse = None
            body = []
            for stmnt in node.body:
                new_stmnt = self.mutate(stmnt)
                if new_stmnt is not None:
                    stmnt = new_stmnt
                body.append(stmnt)
                
            if len(node.iter.args) == 1:
                start = cast.CNum(0, ctypes.c_long)
                stop = node.iter.args[0]
                step = cast.CNum(1, ctypes.c_long)
            elif len(node.iter.args) == 2:
                start = node.iter.args[0]
                stop = node.iter.args[1]
                step = cast.CNum(1, ctypes.c_long)
            elif len(node.iter.args) == 3:
                start = node.iter.args[0]
                stop = node.iter.args[1]
                step = node.iter.args[2]
            else:
                raise TypeError("range wrong number of arguments")
            
            init = cast.CAssignExpr(targets=[node.target], value=start, ctype=ctypes.c_long)
            condition = cast.CCompare(left=node.target, ops=[ast.Lt()], comparators=[stop], ctype=ctypes.c_ubyte)
            increment = cast.CAugAssignExpr(target=node.target, op=ast.Add(), value=step, ctype=ctypes.c_long)
        else:
            raise NotImplementedError("can not iterate over %r object" % (node.iter.ctype))
        
        return cast.CFor(init, condition, increment, body, orelse)



def format_for_loops(mod_ast):
    UnrollLoopMutator().mutate(mod_ast)
    ForLoopMutator().mutate(mod_ast)
    return 

########NEW FILE########
__FILENAME__ = keywords
'''
Created on Dec 2, 2011

@author: sean
'''
from meta.asttools.visitors import Visitor, visit_children
from clyther.clast import cast

class KeywordMover(Visitor):
    visitDefault = visit_children
    
    def visitCCall(self, node):
        
        if isinstance(node.func, cast.CName):
            return
        
        arg_names = [arg.id for arg in node.func.node.args.args]
        num_args = len(node.args)
        num_additional_required = len(arg_names) - num_args
        node.args.extend([None] * num_additional_required)
        
        if num_additional_required != len(node.keywords):
            raise TypeError()
        
        while node.keywords:
            keyword = node.keywords.pop()
            
            if keyword.arg not in arg_names:
                raise TypeError()
             
            i = arg_names.index(keyword.arg)
            
            if i < num_args:
                raise TypeError()
            
            node.args[i] = keyword.value
        
def move_keywords_to_args(node):
    mover = KeywordMover()
    mover.visit(node)

########NEW FILE########
__FILENAME__ = placeholder_replace
'''
Created on Dec 2, 2011

@author: sean
'''
from clyther.clast.cast import FuncPlaceHolder
from meta.asttools.visitors import visit_children, Visitor
import ast
from clyther.clast import cast

class PlaceholderGetter(Visitor):
    visitDefault = visit_children
    
    def __init__(self):
        self.forward_decs = set()
        
    def visitCFunctionForwardDec(self, node):
        self.forward_decs.add(node)
        self.visitDefault(node)

    def visitCFunctionDef(self, node):
        self.forward_decs.add(node)
        self.visitDefault(node)

class PlaceholderReplacer(Visitor):
    visitDefault = visit_children
        
    def visitCFunctionForwardDec(self, node):
        if isinstance(node.name, FuncPlaceHolder):
            if node.name.name == '<lambda>':
                name = 'lambda_id%i' % id(node.name)
            else:
                name = node.name.name

            node.name = name
            
        self.visitDefault(node)

    def visitCFunctionDef(self, node):
        if isinstance(node.name, FuncPlaceHolder):
            if node.name.name == '<lambda>':
                name = 'lambda_id%i' % id(node.name)
            else:
                name = node.name.name

            node.name = name
            
        self.visitDefault(node)
            
    def visitCCall(self, node):
        if isinstance(node.func, FuncPlaceHolder):
            
            if node.func.name == '<lambda>':
                name = 'lambda_id%i' % id(node.func)
            else:
                name = node.func.name
                
            node.func = cast.CName(name, ast.Load(), node.func.key[0])
 
 
def resolve_functions(mod):
    getter = PlaceholderGetter()
    getter.visit(mod)
    
    placeholders = {decl.name for decl in getter.forward_decs if isinstance(decl.name, FuncPlaceHolder)}
    abs_defines = {decl.name for decl in getter.forward_decs if not isinstance(decl.name, FuncPlaceHolder)}
    
    for placeholder in placeholders:
        base_name = placeholder.name
        name = placeholder.name
        i = 0
        while name in abs_defines:
            i += 1
            name = '%s_%03i' % (base_name, i) 
             
        abs_defines.add(name)
    
    replacer = PlaceholderReplacer()
    replacer.visit(mod)
    


########NEW FILE########
__FILENAME__ = printf
'''
Created on Dec 9, 2011

@author: sean
'''
from meta.asttools.visitors import Mutator
from clyther.clast import cast
import ast
from opencl.type_formats import type_format

STR_FORMAT_MAP = {
                  'l': '%i',
                  'L': '%lu',
                  'f': '%f',
                  }
class PrintFMutator(Mutator):
    def mutatePrint(self, node):
        
        str_formats = []
        for val in node.values:
            if val.ctype == str:
                str_formats.append('%s')
            else:
                cfmt = type_format(val.ctype)
                fmt = STR_FORMAT_MAP[cfmt]
                str_formats.append(fmt)
        if node.nl: 
            str_formats.append('\\n')
            
        cstr = cast.CStr(" ".join(str_formats), str)
        
        arg = cast.CTypeCast(cstr, 'const char*')
        vlaue = cast.CCall(cast.CName('printf', ast.Load(), None), [arg] + node.values, [], None)
        
        return ast.Expr(vlaue)
    

def make_printf(mod_ast):
    
    printf = PrintFMutator()
    printf.mutate(mod_ast)

########NEW FILE########
__FILENAME__ = replace_constants
'''
Created on Dec 23, 2011

@author: sean
'''
import ast
import opencl as cl
from inspect import isclass
import _ctypes
from clyther.clast import cast
from clyther.rttt import typeof

def is_constant(ctype):
    if not isclass(ctype) and not isinstance(ctype, cl.contextual_memory):
        return True
    else:
        return False
    
def isnumber(data):
    return isinstance(data, (_ctypes._SimpleCData, int, float)) 


class ConstantTransformer(ast.NodeTransformer):
    
    def generic_visit(self, node):
        if isinstance(node, ast.expr):
            if is_constant(node.ctype):
                if isnumber(node.ctype):
                    return cast.CNum(node.ctype, typeof(None, node.ctype))
            
        return ast.NodeTransformer.generic_visit(self, node)

def replace_constants(node):
    return ConstantTransformer().visit(node)


########NEW FILE########
__FILENAME__ = rm_const_params
'''
Created on Dec 2, 2011

@author: sean
'''
from meta.asttools.visitors import Visitor, visit_children
from inspect import isroutine

def not_const(arg):
    if isroutine(arg.ctype):
        return False
    return True


class RemoveConstParams(Visitor):
    visitDefault = visit_children
    
    def visitCFunctionDef(self, node):
        
        args = node.args.args
        
        args = [arg for arg in args if not_const(arg)]
        node.args.args = args

def remove_const_params(node):
    remover = RemoveConstParams()
    remover.visit(node)

########NEW FILE########
__FILENAME__ = type_cast
'''
Created on Dec 2, 2011

@author: sean
'''
from meta.asttools.visitors import Mutator
from inspect import isroutine
from clyther.clast import cast
from clyther.clast.visitors.typify import RuntimeFunction
import _ctypes


class TypeCaster(Mutator):
    
    def mutateCCall(self, node):
        
        new_node = self.mutateDefault(node)
        if new_node:
            node = new_node
        
        if hasattr(node.func, 'ctype') \
            and not isroutine(node.func.ctype) \
            and not isinstance(node.func.ctype, RuntimeFunction):
            
            if len(node.args) == 0:
                arg = cast.CNum(0, node.func.ctype)
            elif len(node.args) == 1:
                arg = self.mutate(node.args[0])
                arg = node.args[0] if arg is None else arg
            elif issubclass(node.ctype, _ctypes.Array):
                return cast.CVectorTypeCast(node.args, node.ctype)
            else:
                raise TypeError()
            return cast.CTypeCast(arg, node.func.ctype)
        
        return new_node
            
def call_type2type_cast(node):
    caster = TypeCaster()
    caster.mutate(node)


########NEW FILE########
__FILENAME__ = unpacker
'''
Created on Dec 7, 2011

@author: sean
'''
from meta.asttools.visitors import Visitor, visit_children, Mutator
from meta.asttools.visitors.print_visitor import print_ast

from opencl import contextual_memory, global_memory, mem_layout
from clyther.clast import cast
import ast
import ctypes
from clyther.clast.visitors.typify import derefrence
import opencl as cl

class Unpacker(Mutator):
    visitDefault = visit_children
    
    def visitCCall(self, node):
        i = 0
        while i < len(node.args):
            arg = node.args[i]
            if isinstance(arg.ctype, contextual_memory):
                new_id = 'cly_%s_info' % arg.id
                
                if (i + 1) < len(node.args) and isinstance(node.args[i + 1], cast.CName) and node.args[i + 1].id == new_id:
                    i += 1
                    continue
                
                if arg.ctype.ndim > 0 or arg.ctype.flat:
                    new_arg = cast.CName(new_id, ast.Load(), arg.ctype.array_info)
                    node.args.insert(i + 1, new_arg)
                    i += 1
            i += 1
            
        self.visitDefault(node)

    def visitarguments(self, node):
#        for i in range(len(node.args)):
        i = 0
        while i < len(node.args):
            arg = node.args[i]
            if isinstance(arg.ctype, contextual_memory):
                new_id = 'cly_%s_info' % arg.id
                
                if (i + 1) < len(node.args) and node.args[i + 1].id == new_id:
                    i += 1
                    continue  
                if arg.ctype.ndim > 0 or arg.ctype.flat:
                    new_arg = cast.CName(new_id, ast.Param(), arg.ctype.array_info)
                    node.args.insert(i + 1, new_arg)
                    i += 1
            i += 1
            
    def visitCSubscript(self, node):
        if isinstance(node.value.ctype, contextual_memory):
            if isinstance(node.slice, ast.Index):
                if not node.value.ctype.flat:
                    node.slice = self._mutate_index(node.value.id, node.value.ctype, node.slice)
            else:
                raise cast.CError(node, NotImplementedError, "I will get to slicing later")
            
        self.visitDefault(node)

    
    def _mutate_index_dim(self, gid, ctype, node, axis=0):
        info = cast.CName('cly_%s_info' % gid, ast.Load(), ctype.array_info)
        right = cast.CAttribute(info, 's%s' % hex(axis + 4)[2:], ast.Load(), derefrence(ctype.array_info))
        index = cast.CBinOp(node, ast.Mult(), right, node.ctype) #FIXME: cast type
        return index
    
    def _mutate_index(self, gid, ctype, node):
        
        info = cast.CName('cly_%s_info' % gid, ast.Load(), ctype.array_info)
        left = cast.CAttribute(info, 's7', ast.Load(), derefrence(ctype.array_info))
        
        if isinstance(node.value, cast.CList):
            if len(node.value.elts) > ctype.ndim:
                raise cast.CError(node, IndexError, "invalid index. Array is an %i dimentional array (got %i indices)" % (ctype.ndim, len(node.value.elts)))
            elif len(node.value.elts) < ctype.ndim:
                raise cast.CError(node, NotImplementedError, "Slicing not supported yet. Array is an %i dimentional array (got %i indices)" % (ctype.ndim, len(node.value.elts)))
                
            for axis, elt in enumerate(node.value.elts):
                index = self._mutate_index_dim(gid, ctype, elt, axis)
                left = cast.CBinOp(left, ast.Add(), index, node.value.ctype) #FIXME: cast type
        else:
            if ctype.ndim not in [1, None]:
                if ctype.ndim is None:
                    raise cast.CError(node, NotImplementedError, "Can not slice a flat array") 
                raise cast.CError(node, NotImplementedError, "Slicing not supported yet. Array is an %i dimentional array (got 1 index)" % (ctype.ndim,))
            
            index = self._mutate_index_dim(gid, ctype, node.value, 0)
            left = cast.CBinOp(left, ast.Add(), index, node.value.ctype) #FIXME: cast type
        
        return left
    
    def mutateCAttribute(self, node):
        if isinstance(node.value.ctype, contextual_memory):
            if node.attr == 'size':
                array_name = node.value.id
                node.value.id = 'cly_%s_info' % array_name
                node.value.ctype = node.value.ctype.array_info
                ctx = ast.Load()
                ctype = ctypes.c_ulong
#                slc = ast.Index(value=cast.CNum(3, ctypes.c_int))
#                return cast.CSubscript(node.value, slc, ctx, ctype)
                return cast.CAttribute(node.value,'s3', ctx, ctype)

            if node.attr == 'offset':
                array_name = node.value.id
                node.value.id = 'cly_%s_info' % array_name
                node.value.ctype = node.value.ctype.array_info
                ctx = ast.Load()
                ctype = ctypes.c_ulong
#                slc = ast.Index(value=cast.CNum(7, ctypes.c_int))
                return cast.CAttribute(node.value,'s7', ctx, ctype)
#                return cast.CSubscript(node.value, slc, ctx, ctype)
            
            elif node.attr == 'strides':
                array_name = node.value.id
                node.value.id = 'cly_%s_info' % array_name
                node.value.ctype = node.value.ctype.array_info
                
                ctx = ast.Load()
                ctype = cl.cl_uint4
                return cast.CAttribute(node.value, 's4567', ctx, ctype)
            
            elif node.attr == 'shape':
                array_name = node.value.id
                node.value.id = 'cly_%s_info' % array_name
                node.value.ctype = node.value.ctype.array_info
                ctx = ast.Load()
                ctype = cl.cl_uint4
                return cast.CAttribute(node.value, 's0123', ctx, ctype)
            else:
                raise AttributeError(node.attr)
                
        

def unpack_mem_args(mod_ast, argtypes):
    
#    declaration_list = cast.CVarDec('shape', ulong4), cast.CVarDec('strides', ulong4),
#    struct_def = cast.CStruct("cly_array_info", declaration_list, ctype=mem_layout)
#    mod_ast.body.insert(0, struct_def)
    mod_ast.defined_types = {}
    
    Unpacker().visit(mod_ast)
    Unpacker().mutate(mod_ast)
    
    

########NEW FILE########
__FILENAME__ = openCL_sourcegen
'''
Created on Dec 1, 2011

@author: sean
'''
from __future__ import print_function

from meta.asttools.visitors import Visitor
import sys
from StringIO import StringIO
from string import Formatter
import ast
from meta.asttools.visitors.print_visitor import print_ast
from clyther.clast import cast

class ASTFormatter(Formatter):

    def format_field(self, value, format_spec):
        if format_spec == 'node':
            gen = GenOpenCLExpr()
            gen.visit(value)
            return gen.dumps()
        elif value == '':
            return value
        else:
            return super(ASTFormatter, self).format_field(value, format_spec)

    def get_value(self, key, args, kwargs):
        if key == '':
            return args[0]
        elif key in kwargs:
            return kwargs[key]
        elif isinstance(key, int):
            return args[key]

        key = int(key)
        return args[key]

        raise Exception

class NoIndent(object):
    def __init__(self, gen):
        self.gen = gen

    def __enter__(self):
        self.level = self.gen.level
        self.gen.level = 0

    def __exit__(self, *args):
        self.gen.level = self.level

class Indenter(object):
    def __init__(self, gen):
        self.gen = gen

    def __enter__(self):
        self.gen.print('\n', level=0)
        self.gen.level += 1

    def __exit__(self, *args):
        self.gen.level -= 1
        
class Bracer(object):
    def __init__(self, gen):
        self.gen = gen

    def __enter__(self):
        self.gen.print('{{\n', level=0)
        self.gen.level += 1

    def __exit__(self, *args):
        self.gen.print('\n')
        self.gen.level -= 1
        self.gen.print('}}\n')

def simple_string(value):
    def visitNode(self, node):
        self.print(value, **node.__dict__)
    return visitNode

class GenOpenCLExpr(Visitor):
    
    def __init__(self):
        self.out = StringIO()
        self.formatter = ASTFormatter()
        self.indent = '    '
        self.level = 0


    @property
    def brace(self):
        return Bracer(self)
    @property
    def indenter(self):
        return Indenter(self)

    @property
    def no_indent(self):
        return NoIndent(self)

    def dump(self, file=sys.stdout):
        self.out.seek(0)
        print(self.out.read(), file=file)

    def dumps(self):
        self.out.seek(0)
        value = self.out.read()
        return value

    def print(self, line, *args, **kwargs):
        line = self.formatter.format(line, *args, **kwargs)

        level = kwargs.get('level')
        prx = self.indent * (level if level else self.level)
        print(prx, line, sep='', end='', file=self.out)

    def visitCTypeName(self, node):
        with self.no_indent:
            self.print(node.typename)
            
    def visitarguments(self, node):
        with self.no_indent:
            i = 0
            for arg in node.args:
                if i:
                    self.print(', ')
                self.print('{0:node}', arg)
                i += 1
            
    def visitCName(self, node):
        with self.no_indent:
            if isinstance(node.ctx, ast.Param):
                self.print('{0:node} {1:s}', node.ctype, node.id)
            elif isinstance(node.ctx, ast.Load):
                self.print('{0:s}', node.id)
            elif isinstance(node.ctx, ast.Store):
                self.print('{0:s}', node.id)
            else:
                raise Exception()
             
    def visitCUnaryOp(self, node):
        self.print('({op:node}{operand:node})', op=node.op, operand=node.operand)
    def visitCBinOp(self, node):
        
        if isinstance(node.op, ast.Pow):
            self.print('pow({left:node}, {right:node})', left=node.left, op=node.op, right=node.right)
        else:
            self.print('({left:node} {op:node} {right:node})', left=node.left, op=node.op, right=node.right)
    
    visitMult = simple_string('*')
    visitAdd = simple_string('+')
    visitUAdd = simple_string('+')
    visitSub = simple_string('-')
    visitUSub = simple_string('-')
    visitDiv = simple_string('/')
    visitMod = simple_string('%')
    
    visitNot = simple_string('!')

    visitBitOr = simple_string('|')
    visitBitAnd = simple_string('&')
    visitBitXor = simple_string('^')
    
    visitLShift = simple_string('<<')
    visitRShift = simple_string('>>')
    
    def visitCStr(self, node):
        with self.no_indent:
            self.print('"{!s}"', node.s)
            
    def visitCNum(self, node):
        with self.no_indent:
            self.print('{!r}', node.n)
            
    def visitCCall(self, node):

        self.print('{func:node}(' , func=node.func)
        i = 0

        print_comma = lambda i: self.print(", ") if i > 0 else None
        with self.no_indent:

            for arg in node.args:
                print_comma(i)
                self.print('{:node}', arg)
                i += 1
            self.print(')')
    
    def visitCTypeCast(self, node):
        with self.no_indent:
            self.print('(({0:node}) ({1:node}))', node.ctype, node.value)
            
    def visitCVectorTypeCast(self, node):
        with self.no_indent:
            self.print('(({0:node}) (', node.ctype)
            
            
            self.print('({0:node})', node.values[0])
            
            for value in node.values[1:]:
                self.print(', ({0:node})', value)
                
            self.print('))', node.ctype)
#            self.print('(({0:node}) ({1:node}))', node.ctype)
    
    def visitclkernel(self, node):
        with self.no_indent:
            self.print('__kernel')
            
    def visitIndex(self, node):
        with self.no_indent:
            self.print('{0:node}', node.value)
            
    def visitCSubscript(self, node):
        with self.no_indent:
            self.print('{0:node}[{1:node}]', node.value, node.slice)
            
    def visitCAttribute(self, node):
        with self.no_indent:
            self.print('{0:node}.{1}', node.value, node.attr)

    def visitCPointerAttribute(self, node):
        with self.no_indent:
            self.print('{0:node}->{1}', node.value, node.attr)
        
    def visitCIfExp(self, node):
        with self.no_indent:
            self.print('{0:node} ? {1:node} : {2:node}', node.test, node.body, node.orelse)
    
    def visitCCompare(self, node):
        with self.no_indent:
            self.print('({0:node}', node.left)
            
            for op, right in zip(node.ops, node.comparators):
                self.print(' {0:node} {1:node}', op, right)
                
            self.print(')')
            
    visitLt = simple_string('<')
    visitGt = simple_string('>')
    visitGtE = simple_string('>=')
    visitLtE = simple_string('<=')
    visitEq = simple_string('==')
    visitNotEq = simple_string('!=')
    
    
    def visitCAssignExpr(self, node):
        with self.no_indent:
            targets = list(node.targets)
            self.print('{0:node} = ', targets.pop()) 
            
            for target in targets:
                self.print('{0:node} = ', target)
                
            self.print('{0:node}', node.value)
        
    def visitCAugAssignExpr(self, node):
        # 'target', 'op', 'value'
        with self.no_indent:
            self.print('{0:node} {1:node}= {2:node}', node.target, node.op, node.value)

    def visitExec(self, node):
        self.print('// Begin Exec Statement\n')
        self.print('{0!s}\n', node.body.s)
        self.print('// End exec Statement\n')
            
    def visitCBoolOp(self, node):
        with self.no_indent:
            self.print('(')
            self.print('{0:node}', node.values[0])
            for value in node.values[1:]:
                self.print(' {0:node} {1:node}', node.op, value)
            self.print(')')
            
    visitAnd = simple_string('&&')
    visitOr = simple_string('||')
            
        
class GenOpenCLSource(GenOpenCLExpr):

    def print_lines(self, lines,):
        prx = self.indent * self.level
        for line in lines:
            print(prx, line, sep='', file=self.out)
    
    def visitModule(self, node):
        self.print('// This file is automatically generated please do not edit\n\n')
        for stmnt in node.body:
            self.visit(stmnt)
            
    def visitCFunctionForwardDec(self, node):
        self.print('{0:node} {1:s}({2:node});', node.return_type, node.name, node.args)
        self.print('\n\n')
    
    def visitCFunctionDef(self, node):
        for decorator in node.decorator_list:
            self.print('{0:node}\n', decorator)
             
        self.print('{0:node} {1:s}({2:node})', node.return_type, node.name, node.args)
        with self.brace:
            for stmnt in node.body:
                self.visit(stmnt)
        self.print('\n\n')
        
    def visitReturn(self, node):
        if node.value is None:
            self.print('return;\n')
        else:
            self.print('return {0:node};\n', node.value)
        
    def visitAssign(self, node):
        targets = list(node.targets)
        self.print('{0:node} = ', targets.pop()) 
        
        with self.no_indent:
            for target in targets:
                self.print('{0:node} = ', target)
                
            self.print('{0:node};\n', node.value)
            
    def visitCVarDec(self, node):
        
        self.print('{0:node} {1};\n', node.ctype, node.id) 
        
    def visitCStruct(self, node):
        
        self.print("typedef struct {{")
        with self.indenter:
            for dec in node.declaration_list:
                self.visit(dec)
        self.print("}} {0};\n\n", node.id)
        
    def visitAugAssign(self, node):
        # 'target', 'op', 'value'
        self.print('{0:node} {1:node}= {2:node};\n', node.target, node.op, node.value)
        
    def visitCFor(self, node):
        #'init', 'condition', 'increment', 'body', 'orelse'
        self.print('for ({0:node}; {1:node}; {2:node})', node.init, node.condition, node.increment)
        
        with self.brace:
            for statement in node.body:
                self.visit(statement)
                
    def visitExpr(self, node):
        self.print('{0:node};\n', node.value)
        
    def visitIf(self, node):
        
        self.print('if ({0:node}) {{\n', node.test)
        with self.indenter:
            for statement in node.body:
                self.visit(statement)
        
        self.print('}}')
        
        if not node.orelse:
            self.print('\n')
            
        for orelse in node.orelse:
            self.print(' else ')
            if isinstance(orelse, ast.If):
                self.visit(orelse)
            else:
                self.print('{{')
                with self.indenter:
                    self.visit(orelse)
                self.print('}}\n')

    def visitWhile(self, node):
        
        self.print('while ({0:node}) {{\n', node.test)
        with self.indenter:
            for statement in node.body:
                self.visit(statement)
        
        self.print('}}\n')
        
    def visitComment(self, node):
        
        commentstr = node.s
        if '\n' in commentstr:
            assert False
        else:
            self.print('// {0!s}\n', commentstr)
            
    def visitCGroup(self, node):
        for statement in node.body:
            self.visit(statement)
            
    def visitBreak(self, node):
        self.print('break;\n')

    def visitContinue(self, node):
        self.print('continue;\n')
            
    
def opencl_source(node):
    source_gen = GenOpenCLSource()
    source_gen.visit(node)
    return source_gen.dumps()

########NEW FILE########
__FILENAME__ = returns
'''
Created on Dec 2, 2011

@author: sean
'''
from meta.asttools.visitors import Visitor, visit_children


class Returns(Visitor):
    def __init__(self):
        self.return_types = []
        self.return_nodes = []
        
    visitDefault = visit_children
    
    def visitReturn(self, node):
        self.return_nodes.append(node)
        self.return_types.append(node.value.ctype)

def returns(body):
    r = Returns()
    list(r.visit_list(body))
    return r.return_types

def return_nodes(body):
    r = Returns()
    list(r.visit_list(body))
    return r.return_nodes

########NEW FILE########
__FILENAME__ = typify
'''
clyther.clast.visitors.typify
-----------------------------------

Generate a typed ast from a python ast.

This is the first step in the Python -> OpenCL pipeline.
'''

from clyther.clast import cast
from clyther.clast.cast import build_forward_dec, FuncPlaceHolder, n
from clyther.clast.visitors.returns import returns
from clyther.pybuiltins import builtin_map
from clyther.rttt import greatest_common_type, RuntimeFunction, cList, \
    is_vetor_type, derefrence
from ctypes import c_ubyte
from inspect import isroutine, isclass, ismodule, isfunction, ismethod
from meta.asttools.visitors import Visitor
from meta.asttools.visitors.print_visitor import print_ast
from meta.decompiler import decompile_func
import __builtin__ as builtins
import _ctypes
import ast
import ctypes
import re
import opencl as cl

class CException(Exception): pass
class CTypeError(TypeError): pass

CData = _ctypes._SimpleCData.mro()[1]

def is_type(func_call):
    if isinstance(func_call, cl.contextual_memory):
        return True
    elif isclass(func_call) and issubclass(func_call, CData):
        return True
    else:
        return False

var_builtins = set(vars(builtins).values())

class CLAttributeError(AttributeError):
    pass

def dict2hashable(dct):
    return tuple(sorted(dct.items(), key=lambda item:item[0]))

def is_slice(slice):
    if isinstance(slice, ast.Index):
        return False
    else:
        raise NotImplementedError(slice)


def get_struct_attr(ctype, attr):
    fields = dict(ctype._fields_)
    if attr in fields:
        return fields[attr]
    elif hasattr(ctype, attr):
        return getattr(ctype, attr)
    else:
        raise CLAttributeError("type %r has no attribute %s" % (ctype, attr))

def getattrtype(ctype, attr):
    '''
    Get the ctype of an attribute on a ctype 
    '''
    if isclass(ctype) and issubclass(ctype, _ctypes.Structure):
        return get_struct_attr(ctype, attr)
        
    elif ismodule(ctype):
        return getattr(ctype, attr)
    elif isinstance(ctype, cl.contextual_memory):
        if ctype.ndim == 0:
            return getattrtype(ctype.ctype, attr)
        else:
            return getattr(ctype, attr)
    elif is_vetor_type(ctype):
        return derefrence(ctype)
#        raise NotImplementedError("is_vetor_type", ctype, attr, derefrence(ctype))
    elif hasattr(ctype, attr):
        return getattr(ctype, attr)
    else:
        raise CLAttributeError("type %r has no attribute %r" % (ctype, attr))
    

class Typify(Visitor):
    '''
    Makes a copy of an ast
    '''
    def __init__(self, name, argtypes, globls):
        self.globls = globls
        self.argtypes = argtypes
        self.locls = argtypes.copy()
        self.func_name = name
        self.function_calls = {}
    
    def visit(self, node, *args, **kwargs):
        new_node = Visitor.visit(self, node, *args, **kwargs)
        if isinstance(new_node, ast.AST):
            if not hasattr(new_node, 'lineno'): 
                new_node.lineno = node.lineno
            if not hasattr(new_node, 'col_offset'): 
                new_node.col_offset = getattr(node, 'col_offset', 0)
                
        return new_node
    
    def visitDefault(self, node):
        raise cast.CError(node, NotImplementedError, 'python ast node %r is not yet supported by clyther' % type(node).__name__)
    
    def make_cfunction(self, node):
        
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            raise CException()

        func_ast = self.visit(node)
        
        local_names = set(self.locls.keys()) - set(self.argtypes.keys())
        for local_name in local_names:
            func_ast.body.insert(0, cast.CVarDec(local_name, self.locls[local_name]))
            
        return func_ast
        
    def make_module(self, func_ast):
        mod = ast.Module([])
        
        forward = []
        body = []
        
        for func_dict in self.function_calls.values():
            for fast in func_dict.values():
                forward.append(build_forward_dec(fast))
                body.append(fast)
                
        forward.append(build_forward_dec(func_ast))
        body.append(func_ast)
        
        mod.body.extend(forward)
        mod.body.extend(body)
        
        return mod 
    
    def visitLambda(self, node):
        args = self.visit(node.args)
        body = self.visit(node.body)
        
        return_type = body.ctype
        
        new_body = [ast.Return(body)]
        return cast.CFunctionDef('lambda', args, new_body, [], return_type)
    
    def visitFunctionDef(self, node):
        #'name', 'args', 'body', 'decorator_list'
        
        args = self.visit(node.args)
        body = list(self.visit_list(node.body))
        
        return_types = returns(body)
        if len(return_types) == 0:
            return_type = None
        else:
            return_type = greatest_common_type(return_types)
        
        return cast.CFunctionDef(node.name, args, body, [], return_type)
    
    def visitarguments(self, node):
        #'args', 'vararg', 'kwarg', 'defaults'
        
        if node.kwarg or node.vararg:
            raise cast.CError(node, NotImplementedError, 'star args or kwargs')
        
        args = list(self.visit_list(node.args))
        defaults = list(self.visit_list(node.defaults))
        
        return ast.arguments(args, None, None, defaults)
    
    def visitReturn(self, node):
        value = self.visit(node.value)
        return ast.Return(value, lineno=node.lineno, col_offset=node.col_offset)
    
    def scope(self, key):
        if key in self.locls:
            return self.locls[key]
        elif key in self.globls:
            return self.globls[key]
        elif key in dir(builtins):
            return getattr(builtins, key)
        else:
            raise NameError("name %r is not defined" % (key,)) 
        
    def visitName(self, node, ctype=None):
        if isinstance(node.ctx, ast.Param):
            if node.id not in self.argtypes:
                raise CTypeError(node.id, 'function %s() requires argument %r' % (self.func_name, node.id))
            ctype = self.argtypes[node.id]
            return cast.CName(node.id, ast.Param(), ctype, **n(node))
        elif isinstance(node.ctx, ast.Load):
            try:
                ctype = self.scope(node.id)
            except NameError as err:
                raise cast.CError(node, NameError, err.args[0])
                
            return cast.CName(node.id, ast.Load(), ctype, **n(node))
        
        elif isinstance(node.ctx, ast.Store):
            assert type is not None
            
            if node.id in self.locls:
                ectype = self.locls[node.id]
                try:
                    greatest_common_type(ctype, ectype)
                except: # Raise a custom exception if the types are not compatible
                    raise
                ctype = ectype
                
            self.locls[node.id] = ctype
            
            return cast.CName(node.id, ast.Store(), ctype, **n(node))
        else:
            assert False
    
    def visitBinOp(self, node):
        left = self.visit(node.left)
        op = node.op
        right = self.visit(node.right)
        ctype = greatest_common_type(left.ctype, right.ctype)
        return cast.CBinOp(left, op, right, ctype)
    
    def visitkeyword(self, node):
        value = self.visit(node.value) 
        return cast.ckeyword(node.arg, value, value.ctype)
    
    def visitNum(self, node):
        type_map = {int:ctypes.c_int, float:ctypes.c_double}
        num_type = type(node.n)
#        ctype = rttt.const_type(type_map[num_type])
        return cast.CNum(node.n, type_map[num_type], **n(node))
    
    def call_python_function(self, node, func, args, keywords):

        func_ast = decompile_func(func)
        
        argtypes = {}
        for keyword in keywords:
            argtypes[keyword.arg] = keyword.ctype

        for param, arg  in zip(func_ast.args.args, args):
            argtypes[param.id] = arg.ctype
            
        
        func_dict = self.function_calls.setdefault(func, {})
        hsh = dict2hashable(argtypes)
        
        if hsh not in func_dict:
            try:
                typed_ast = Typify(func.func_name, argtypes, func.func_globals).make_cfunction(func_ast)
            except CTypeError as err:
                argid = err.args[0]
                ids = [arg.id for arg in func_ast.args.args]
                if argid in ids:
                    pos = ids.index(argid)
                else:
                    pos = '?'
                    
                raise cast.CError(node, TypeError, err.args[1] + ' at position %s' % (pos))
                
            key = (func, hsh)
            plchldr = FuncPlaceHolder(func.func_name, key, typed_ast)
            typed_ast.name = plchldr 
            func_dict[hsh] = typed_ast
        else:
            typed_ast = func_dict[hsh]
            plchldr = typed_ast.name
    
        return cast.CCall(plchldr, args, keywords, typed_ast.return_type) 
    
    def visitCall(self, node):
        #('func', 'args', 'keywords', 'starargs', 'kwargs')
        if node.starargs or node.kwargs:
            raise cast.CError(node, NotImplementedError, '* and ** args ar not supported yet')
        
        expr = ast.Expression(node.func, lineno=node.func.lineno, col_offset=node.func.col_offset)
        code = compile(expr, '<nofile>', 'eval')
        try:
            func = eval(code, self.globls, self.locls)
        except AttributeError as err:
            raise cast.CError(node, AttributeError, err.args[0])   
        
        args = list(self.visit_list(node.args))
        keywords = list(self.visit_list(node.keywords))
        if func in builtin_map:
            cl_func = builtin_map[func]
            if isinstance(cl_func, RuntimeFunction):
                argtypes = [arg.ctype for arg in args]
                try:
                    return_type = cl_func.return_type(argtypes)
                except TypeError as exc:
                    raise cast.CError(node, type(exc), exc.args[0])
                
                func_name = cast.CName(cl_func.name, ast.Load(), cl_func)
                return cast.CCall(func_name, args, keywords, return_type)
            else:
                func = self.visit(node.func)
                return cast.CCall(func, args, keywords, cl_func)
        
        
        elif isfunction(func):
            return self.call_python_function(node, func, args, keywords)
        elif ismethod(func):
            value = self.visit(node.func.value)
            return self.call_python_function(node, func.im_func, [value] + args, keywords)
        else:
            func_name = self.visit(node.func)
            
            if isinstance(func_name.ctype, RuntimeFunction):
                rt = func_name.ctype
                argtypes = [arg.ctype for arg in args]
                try:
                    func = rt.return_type(argtypes)
                except TypeError as exc:
                    raise cast.CError(node, type(exc), exc.args[0])
                func_name = cast.CName(rt.name, ast.Load(), rt)
            elif is_type(func):
                # possibly a type cast
                pass
            else:
                msg = ('This function is not one that CLyther understands. '
                       'A function may be a) A native python function. '
                       'A python built-in function registered with clyther.pybuiltins '
                       'or a ctype (got %r)' % (func))
                raise cast.CError(node, TypeError, msg)
                
            return cast.CCall(func_name, args, keywords, func) 
            
        
    
    def visitAssign(self, node):
        value = self.visit(node.value)
        
        tragets = list(self.visit_list(node.targets, value.ctype))

        assign = ast.Assign(tragets, value)
        
        return assign
    
    def visitIndex(self, node):
        value = self.visit(node.value)
        index = ast.Index(value)
        
        return index
        
    def visitSubscript(self, node, ctype=None):
        
        value = self.visit(node.value)
        slice = self.visit(node.slice)
        
        if is_slice(slice):
            ctype = value.ctype
        else:
            ctype = derefrence(value.ctype)
        ctx = node.ctx
        subscr = cast.CSubscript(value, slice, ctx, ctype)
        
        return subscr
    
    def visitIfExp(self, node, ctype=None):
        test = self.visit(node.test)
        body = self.visit(node.body)
        orelse = self.visit(node.orelse)
        
        ctype = greatest_common_type(body.ctype, orelse.ctype)
        
        return cast.CIfExp(test, body, orelse, ctype)
        
    def visitAttribute(self, node, ctype=None):
        
        value = self.visit(node.value)
        
        try:
            attr_type = getattrtype(value.ctype, node.attr)
        except CLAttributeError as err:
            raise cast.CError(node, CLAttributeError, err.args[0])
        
        if isinstance(node.ctx, ast.Store):
            pass
        
        if isinstance(value.ctype, cl.contextual_memory) and value.ctype.ndim == 0:
            attr = cast.CPointerAttribute(value, node.attr, node.ctx, attr_type)
        else:
            attr = cast.CAttribute(value, node.attr, node.ctx, attr_type)
        
        return attr
    
    def visitCompare(self, node):
        # ('left', 'ops', 'comparators')
        left = self.visit(node.left)
        comparators = list(self.visit_list(node.comparators))
        
        return cast.CCompare(left, list(node.ops), comparators, ctypes.c_ubyte)
    
    def visitAugAssign(self, node):
        # 'target', 'op', 'value' 
        value = self.visit(node.value)
        target = self.visit(node.target, value.ctype)
        
        return ast.AugAssign(target, node.op, value)
        
    def visitFor(self, node):
        # 'target', 'iter', 'body', 'orelse'
        
        if node.orelse:
            raise NotImplementedError("todo: for - else")
        
        iter = self.visit(node.iter)
        target = self.visit(node.target, iter.ctype.iter_type)
        
        body = list(self.visit_list(node.body))
        
        return ast.For(target, iter, body, None)
    
    def visitPrint(self, node):
        #('dest', 'values', 'nl')
        
        if node.dest is not None:
            raise cast.CError(node, NotImplementedError, ("print '>>' operator is not allowed in openCL"))
        
        values = list(self.visit_list(node.values))
        
        return ast.Print(None, values, node.nl)
        
    def visitExec(self, node):
        # ('body', 'globals', 'locals')
        if node.globals is not None:
            raise cast.CError(node, NotImplementedError, ("exec globals is not allowed in openCL"))
        if node.locals is not None:
            raise cast.CError(node, NotImplementedError, "exec locals is not allowed in openCL")
        
        body = self.visit(node.body)
        
        return ast.Exec(body, None, None)
    
    def visitStr(self, node):
        return cast.CStr(node.s, str)
    
    def visitIf(self, node):
        #('test', 'body', 'orelse')
        test = self.visit(node.test)
        body = list(self.visit_list(node.body))
        orelse = list(self.visit_list(node.orelse))
        return ast.If(test, body, orelse)
    
    def visitWhile(self, node):
        #('test', 'body', 'orelse')
        if node.orelse:
            raise cast.CError(node, NotImplementedError, "while ... else is not yet allowed in openCL")
        
        test = self.visit(node.test)
        body = list(self.visit_list(node.body))
        
        return ast.While(test, body, None)
        
    def visitExpr(self, node):
        value = self.visit(node.value)
        return ast.Expr(value) 
    
    def visitList(self, node):
        elts = list(self.visit_list(node.elts))
        
        ltypes = [elt.ctype for elt in elts]
        ctype = greatest_common_type(ltypes)
        return cast.CList(elts, node.ctx, cList(ctype))
    
    def visitBoolOp(self, node):
        #('op', 'values')
        print node.op, node.values
        
        values = list(self.visit_list(node.values))
        
        return cast.CBoolOp(node.op, values, c_ubyte) 
     
    def visitTuple(self, node):
        
        elts = list(self.visit_list(node.elts))
        
        ltypes = [elt.ctype for elt in elts]
        ctype = greatest_common_type(ltypes)
        return cast.CList(elts, node.ctx, cList(ctype))
        
    def visitBreak(self, node):
        return ast.copy_location(ast.Break(), node)
    
    def visitContinue(self, node):
        return ast.copy_location(ast.Continue(), node)
    
    def visitUnaryOp(self, node):
        #('op', 'operand')
        operand = self.visit(node.operand)
        new_node = cast.CUnaryOp(node.op, operand, operand.ctype)
        return ast.copy_location(new_node, node)
            
def typify_function(name, argtypes, globls, node):
    typify = Typify(name, argtypes, globls)
    func_ast = typify.make_cfunction(node)
    return typify.make_module(func_ast)

########NEW FILE########
__FILENAME__ = cly_kernel
'''
Created on Dec 4, 2011

@author: sean
'''

from clyther.clast import cast
from clyther.pipeline import create_kernel_source
from clyther.queue_record import EventRecord
from clyther.rttt import typeof
from inspect import isfunction
from tempfile import mktemp
import ast
import opencl as cl
from clyther.caching import NoFileCache

class ClytherKernel(object):
    pass

class CLComileError(Exception):
    def __init__(self, lines, prog):
        Exception.__init__(self, lines)
        self.prog = prog
        

def is_const(obj):
    if isfunction(obj):
        return True
    else:
        return False
    
def developer(func):
    '''
    Kernel decorator to enable developer tracebacks.
    '''
    func._development_mode = True
    func._no_cache = True

    return func

class kernel(object):
    '''
    Create an OpenCL kernel from a Python function.
    
    This class can be used as a decorator::
    
        @kernel
        def foo(a):
            ...
    '''
    
    def __init__(self, func):
        self.func = func
        self.__doc__ = self.func.__doc__ 
        self.global_work_size = None
        self.local_work_size = None
        self.global_work_offset = None
        self._cache = {}
        
        self._development_mode = False
        self._no_cache = False
        self._file_cacher = NoFileCache()
        self._use_cache_file = False
    

    def clear_cache(self):
        '''
        Clear the binary cache in memory.
        '''
        self._cache.clear()
        
    def run_kernel(self, cl_kernel, queue, kernel_args, kwargs):
        '''
        Run a kernel this method is subclassable for the task class.
        '''
        event = cl_kernel(queue, global_work_size=kwargs.get('global_work_size'),
                                 global_work_offset=kwargs.get('global_work_offset'),
                                 local_work_size=kwargs.get('local_work_size'),
                                 **kernel_args)
        
        return event
    
    
    def _unpack(self, argnames, arglist, kwarg_types):
        '''
        Unpack memobject structure into two arguments. 
        '''
        kernel_args = {}
        for name, arg  in zip(argnames, arglist):
            
            if is_const(arg):
                continue
            
            arg_type = kwarg_types[name]
            if isinstance(arg_type, cl.contextual_memory):
                if kwarg_types[name].ndim != 0:
                    kernel_args['cly_%s_info' % name] = arg_type._get_array_info(arg)
            kernel_args[name] = arg
        return kernel_args

    def __call__(self, queue_or_context, *args, **kwargs):
        '''
        Call this kernel as a function.
        
        :param queue_or_context: a queue or context. if this is a context a queue is created and finish is called before return.
        
        :return: an OpenCL event.
        '''
        if isinstance(queue_or_context, cl.Context):
            queue = cl.Queue(queue_or_context)
        else:
            queue = queue_or_context
             
        argnames = self.func.func_code.co_varnames[:self.func.func_code.co_argcount]
        defaults = self.func.func_defaults
        
        kwargs_ = kwargs.copy()
        kwargs_.pop('global_work_size', None)
        kwargs_.pop('global_work_offset', None)
        kwargs_.pop('local_work_size', None)
        
        arglist = cl.kernel.parse_args(self.func.__name__, args, kwargs_, argnames, defaults)
        
        kwarg_types = {argnames[i]:typeof(queue.context, arglist[i]) for i in range(len(argnames))}
        
        cl_kernel = self.compile(queue.context, **kwarg_types)
        
        kernel_args = self._unpack(argnames, arglist, kwarg_types)
            
        event = self.run_kernel(cl_kernel, queue, kernel_args, kwargs)
        
        #FIXME: I don't like that this breaks encapsulation
        if isinstance(event, EventRecord):
            event.set_kernel_args(kernel_args)
            
        if isinstance(queue_or_context, cl.Context):
            queue.finish()
        
        return event
    
    def compile(self, ctx, source_only=False, cly_meta=None, **kwargs):
        '''
        Compile a kernel or lookup in cache.
        
        :param ctx: openCL context
        :param cly_meta: meta-information for inspecting the cache. (does nothing)
        :param kwargs: All other keyword arguments are used for type information.
        
        :return: An OpenCL kernel 
        '''
        cache = self._cache.setdefault(ctx, {})
        
        cache_key = tuple(sorted(kwargs.viewitems(), key=lambda item:item[0]))
        
        #Check for in memory cache
        if cache_key not in cache or self._no_cache:
            cl_kernel = self.compile_or_cly(ctx, source_only=source_only, cly_meta=cly_meta, **kwargs)
            
            cache[cache_key] = cl_kernel

        return cache[cache_key] 
    
    def source(self, ctx, *args, **kwargs):
        '''
        Get the source that would be compiled for specific argument types.
        
        .. note:: 
            
            This is meant to have a similar signature to the function call.
            i.e::
                 
                 print func.source(queue.context, arg1, arg2) 
                 func(queue, arg1, arg2)
        
        '''
        
        argnames = self.func.func_code.co_varnames[:self.func.func_code.co_argcount]
        defaults = self.func.func_defaults
        
        arglist = cl.kernel.parse_args(self.func.__name__, args, kwargs, argnames, defaults)
        
        kwarg_types = {argnames[i]:typeof(ctx, arglist[i]) for i in range(len(argnames))}
        
        return self.compile_or_cly(ctx, source_only=True, **kwarg_types)

    
    @property
    def db_filename(self):
        '''
        get the filename that the binaries can be cached to
        '''
        from os.path import splitext
        base = splitext(self.func.func_code.co_filename)[0]
        return base + '.h5.cly'
     
    def compile_or_cly(self, ctx, source_only=False, cly_meta=None, **kwargs):
        '''
        internal
        '''
        cache_key = self._file_cacher.generate_key(kwargs)

        if (ctx, self.func, cache_key) in self._file_cacher:
            program, kernel_name, args, defaults = self._file_cacher.get(ctx, self.func, cache_key)
        else:
            args, defaults, kernel_name, source = self.translate(ctx, **kwargs)
            
            program = self._compile(ctx, args, defaults, kernel_name, source)
            
            self._file_cacher.set(ctx, self.func, cache_key,
                                  args, defaults, kernel_name, cly_meta, source,
                                  program.binaries)

            
        cl_kernel = program.kernel(kernel_name)
        
        cl_kernel.global_work_size = self.global_work_size
        cl_kernel.local_work_size = self.local_work_size
        cl_kernel.global_work_offset = self.global_work_offset
        cl_kernel.argtypes = [arg[1] for arg in args]
        cl_kernel.argnames = [arg[0] for arg in args]
        cl_kernel.__defaults__ = defaults
        
        return cl_kernel
    
    def translate(self, ctx, **kwargs):
        '''
        Translate this func into a tuple of (args, defaults, kernel_name, source)  
        '''
        try:
            args, defaults, source, kernel_name = create_kernel_source(self.func, kwargs)
        except cast.CError as error:
            if self._development_mode: raise
            
            redirect = ast.parse('raise error.exc(error.msg)')
            redirect.body[0].lineno = error.node.lineno
            filename = self.func.func_code.co_filename
            redirect_error_to_function = compile(redirect, filename, 'exec')
            eval(redirect_error_to_function) #use the @cly.developer function decorator to turn this off and see stack trace ...
            
        return args, defaults, kernel_name, source
        
    
    def _compile(self, ctx, args, defaults, kernel_name, source):
        '''
        Compile a kernel without cache lookup. 
        '''
        tmpfile = mktemp('.cl', 'clyther_')
        program = cl.Program(ctx, ('#line 1 "%s"\n' % (tmpfile)) + source)
        
        try:
            program.build()
        except cl.OpenCLException:
            log_lines = []
            for device, log in program.logs.items():
                log_lines.append(repr(device))
                log_lines.append(log)
            
            with open(tmpfile, 'w') as fp:
                fp.write(source)
                
            raise CLComileError('\n'.join(log_lines), program)
        
        for device, log in program.logs.items():
            if log: print log
            
        return program

class task(kernel):
    '''
    Create an OpenCL kernel from a Python function.
    
    Calling this object will enqueue a task.
    
    This class can be used as a decorator::
    
        @task
        def foo(a):
            ...
    '''

    def emulate(self, ctx, *args, **kwargs):
        '''
        Run this function in emulation mode.
        '''
        return self.func(*args, **kwargs)
    
    def run_kernel(self, cl_kernel, queue, kernel_args, kwargs):
        '''
        Run the kernel as a single thread task.
        '''
        #have to keep args around OpenCL refrence count is not incremented until enqueue_task is called
        args = cl_kernel.set_args(**kernel_args)
        event = queue.enqueue_task(cl_kernel)
        
#        event = cl_kernel(queue, global_work_size=kwargs.get('global_work_size'),
#                                 global_work_offset=kwargs.get('global_work_offset'),
#                                 local_work_size=kwargs.get('local_work_size'),
#                                 **kernel_args)
        
        return event
    
def global_work_size(arg):
    '''
    Bind the global work size of an nd range kernel to a arguments.
    
    :param arg: can be either a list of integers or a function with the same signature as the python
        kernel.
    '''
    def decorator(func):
        func.global_work_size = arg
        return func
    return decorator

def local_work_size(arg):
    '''
    Bind the local work size of an nd range kernel to a arguments.
    
    :param arg: can be either a list of integers or a function with the same signature as the python
        kernel.
    '''
    def decorator(func):
        func.local_work_size = arg
        return func
    return decorator

def global_work_offset(arg):
    '''
    Bind the local work size of an nd range kernel to a arguments.
    
    :param arg: can be either a list of integers or a function with the same signature as the python
        kernel.
    '''
    def decorator(func):
        func.global_work_offset = arg
        return func
    return decorator

def cache(chache_obj):
    '''
    Set the caching type for a kernel binaries to file. (default is :class:`clyther.caching.NoFileCache`)
    Use cache as a decorator::
        
        @cache(HDFCache)
        @cly.kernel
        def foo(...):
            ...
    
    
    :param chache_obj: Cache object 
    
    
    '''
    def decorator(func):
        func._file_cacher = chache_obj
        return func
    return decorator

########NEW FILE########
__FILENAME__ = my_sphinx
'''
Created on Dec 24, 2011

@author: sean
'''

from sphinx.ext.autodoc import ModuleLevelDocumenter 
import inspect

class RuntimeFunctionDocumenter(ModuleLevelDocumenter):
    """
    Specialized Documenter subclass for functions.
    """
    objtype = 'clrt'
    directivetype = 'function'
    member_order = 30

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        import clyther.rttt
        return isinstance(member, clyther.rttt.RuntimeFunction)

    def format_args(self):
        argtypes = self.object.argtypes
        
        args = '(' + ', '.join([str(arg.__name__) for arg in argtypes]) + ')'
        return args
    
    def document_members(self, all_members=False):
        pass



def setup(app):
    app.add_autodocumenter(RuntimeFunctionDocumenter)

########NEW FILE########
__FILENAME__ = pipeline
'''
clyther.pipeline
----------------------


'''

from clyther.clast import cast
from clyther.clast.mutators.for_loops import format_for_loops
from clyther.clast.mutators.keywords import move_keywords_to_args
from clyther.clast.mutators.placeholder_replace import resolve_functions
from clyther.clast.mutators.printf import make_printf
from clyther.clast.mutators.rm_const_params import remove_const_params
from clyther.clast.mutators.type_cast import call_type2type_cast
from clyther.clast.mutators.unpacker import unpack_mem_args
from clyther.clast.openCL_sourcegen import opencl_source
from clyther.clast.visitors.returns import return_nodes
from clyther.clast.visitors.typify import Typify
from clyther.rttt import replace_types
from meta.decompiler import decompile_func
from clyther.clast.mutators.replace_constants import replace_constants




def make_kernel(cfunc_def):
    returns = return_nodes(cfunc_def.body)
    for return_node in returns:
        return_node.value = None
    
    cfunc_def.decorator_list.insert(0, cast.clkernel())
    cfunc_def.return_type = None
    
    
def typify_function(name, argtypes, globls, node):
    typify = Typify(name, argtypes, globls)
    func_ast = typify.make_cfunction(node)
    make_kernel(func_ast)
    return typify.make_module(func_ast), func_ast


def create_kernel_source(function, argtypes):
    '''
    Create OpenCL source code from a Python function.
    
    :param function: A pure python function
    :param argtypes: A dict of name:type for the compiler to use in optimizing the function.
    
    Steps:
        
        * Decompile to AST.:
            Get AST from python bytecode
        * Typify AST: 
            This transforms the AST in to a partially typed OpenCL AST.
            It will recursively dive into pure Python functions and add thoes to the OpenCL module.
            Function names will be replace with placeholders for the namespace conflict resolution stage.
        * Replace Constants:
            Replace Python constants with values. e.g. `math.e` -> `2.7182`
        * Unpack memobjects:
            To support multi-dimensional indexing and non contiguous memory arrays. 
            CLyther adds a uint8 to the function signature to store this information.
        * Replace calls of types to type casts e.g. int(i) -> ((int)(i))
        * Format for loops:
            only `range` or a explicit Python list is currently supported as the iterator in a for loop.
        * Remove arguments to functions that are constant. e.g. python functions. 
        * Move keyword arguments in function calls to positional arguments.
        * Resolve function place-holders
        * Make printf statements from print
        * Replace Types:
            Replace python ctype objects with OpenCL type names.
            This will also define structs in the module if required. 
        * Generate Source
    '''
    
    func_ast = decompile_func(function)
    
    globls = function.func_globals
    
    mod_ast, func_ast = typify_function(function.func_name, argtypes, globls, func_ast)
    
    mod_ast = replace_constants(mod_ast)
    
    unpack_mem_args(mod_ast, argtypes)
    # convert type calls to casts 
    # eg int(i) -> ((int) (i))
    call_type2type_cast(mod_ast)
    
    format_for_loops(mod_ast)
    
    # Remove arguments to functions that are constant
    # eg. functions modules. etc
    remove_const_params(mod_ast)
    
    #C/opencl do not accept keword arguments. 
    #This moves them to positional arguments 
    move_keywords_to_args(mod_ast)
    
    #typify created function placeholders. resolve them here 
    resolve_functions(mod_ast)
    
    make_printf(mod_ast)
    
    defaults = function.func_defaults
    
    args = [(arg.id, arg.ctype) for arg in func_ast.args.args]
    
    #replace python type objects with strings 
    replace_types(mod_ast)
    
#    mod_ast.body.insert(0, ast.Exec(cast.CStr('#pragma OPENCL EXTENSION cl_amd_printf : enable', str), None, None))
    
    #generate source
    return args, defaults, opencl_source(mod_ast), func_ast.name
    

########NEW FILE########
__FILENAME__ = pybuiltins
'''
Created on Jul 27, 2011

@author: sean

Used to convert python builtins 
'''
import ctypes
import _ast

builtin_map = {}

class bl_builtin(object): pass

class cl_range(bl_builtin):
    iter_type = ctypes.c_long

builtin_map[range] = cl_range


########NEW FILE########
__FILENAME__ = queue_record
'''
Created on Dec 8, 2011

@author: sean
'''
import opencl as cl
from uuid import uuid1
from collections import OrderedDict

class EventRecord(object):
    def __init__(self, uuid, operation, *args, **kwargs):
        self._uuid = uuid
        self._valid = False
        self._operation = operation
        self.args = args
        self.kwargs = kwargs
        self.kenel_args = None
        
    @property
    def uuid(self):
        return self._uuid
    
    def set_event(self, event):
        self._event = event
        self.validate()
    
    def invalidate(self):
        self._valid = False
        
    def validate(self):
        self._valid = True

    def valid(self):
        return self._valid
    
    def set_kernel_args(self, kernel, *args, **kwargs):
        self.kenel_args = kernel, args, kwargs
        
    def enqueue(self, queue):
        if self.kenel_args:
            kernel, args, kwargs = self.kenel_args
            kernel.set_args(*args, **kwargs)
            
        event = self._operation(queue, *self.args, **self.kwargs)
        self.set_event(event)
        
    
class QueueRecord(object):
    def __init__(self, context, queue=None):
        self._context = context
        self.events = []
        
        if queue is None:
            queue = cl.Queue(context)
            
        self.queue = queue
        
    @property
    def context(self):
        return self._context
    
    def set_kernel_args(self, queue, cl_kernel, kernel_args):
        cl_kernel.set_args(**kernel_args)
    
    def enqueue_set_kernel_args(self, cl_kernel, kernel_args):
        
        uuid = uuid1()
        args = cl_kernel, kernel_args.copy()
        self.operations[uuid] = self.set_kernel_args, args
        
        self.events[uuid] = EventRecord(uuid,)
        return self.events[uuid]
    
    def enqueue_nd_range_kernel(self, kernel, work_dim, global_work_size, global_work_offset=None, local_work_size=None, wait_on=()):
        
        uuid = uuid1()
        args = kernel, work_dim, global_work_size, global_work_offset, local_work_size, wait_on
        self.operations[uuid] = cl.Queue.enqueue_nd_range_kernel, args
        
        self.events[uuid] = EventRecord(uuid, cl.Queue.enqueue_nd_range_kernel,
                                        kernel, work_dim, global_work_size, global_work_offset,
                                        local_work_size, wait_on)
        return self.events[uuid]
        
    def enqueue(self, queue=None):
        
        if queue is None:
            queue = self.queue

        for revent in self.events:
            if not revent.valid():
                revent.enqueue(queue)
                





########NEW FILE########
__FILENAME__ = rttt
'''
clyther.rttt
--------------------

Run Time Type Tree (rttt)

'''

from clast import cast
from clyther.pybuiltins import builtin_map
from inspect import isroutine, isclass, isfunction
from meta.asttools.visitors import visit_children, Mutator
from meta.asttools.visitors.print_visitor import print_ast
from opencl import contextual_memory
from opencl.type_formats import type_format, cdefn
import _ctypes
import abc
import ast
import ctypes
import opencl as cl
import re

class cltype(object):
    __metaclass__ = abc.ABCMeta
    pass

cltype.register(contextual_memory)

class cList(cltype):
    def __init__(self, ctype):
        self.iter_type = ctype
        

class RuntimeConstant(object):
    '''
    define a constant value that is defined in the OpenCL runtime.
    
    :param name: the name of the constant in OpenCL.
    :param rtt: the ctype of the constant.
    
    '''
    def __init__(self, name, rtt):
        self.name = name
        self.rtt = rtt
    
    def ctype_string(self):
        return self.name
    
class RuntimeType(cltype):
    
    def __init__(self, name):
        self.name = name
    
            
    def __call__(self, name):
        return RuntimeConstant(name, self)
        
    def ctype_string(self):
        return self.name
    
class gentype(object):
    '''
    a generic numeric type in OpenCL
    '''
    def __init__(self, *types):
        self.types = types
        
class ugentype(object):
    '''
    an unsigned generic numeric type in OpenCL
    '''
    def __init__(self, *types):
        self.types = types
        
class sgentype(object):
    '''
    a signed generic numeric type in OpenCL
    '''
    def __init__(self, *types):
        self.types = types
        
class RuntimeFunction(cltype):
    '''
    A function that is defined in the openCL runtime.
    
    :param name: the name of the function as per the oencl specification.
    :param return_type: Either a ctype or a function that returns a ctype
    :param argtypes: Either a ctype or a function that returns a ctype
    
    Keyword only parameters:
        :param doc: Either a ctype or a function that returns a ctype
        :param builtin: a python builtin function that is equivalent to this function
        :param emulate: A function that emulates the behavior of this function in python. 
            This argument is not required if `builtin` is given. 
    
    If `return_type` is a function it must have the same signature as the runtime function.
     
    '''
    
    def __init__(self, name, return_type, *argtypes, **kwargs):
        self.name = name
        self._return_type = return_type
        self.argtypes = argtypes
        self.kwargs = kwargs
        self.__doc__ = kwargs.get('doc', None)
        self.builtin = kwargs.get('builtin', None)
        self.emulate = kwargs.get('emulate', None)
        
        if self.builtin is not None:
            builtin_map[self.builtin] = self
        
    def return_type(self, argtypes):
        if isfunction(self._return_type):
            return self._return_type(*argtypes)
        else:
            if len(argtypes) != len(self.argtypes):
                raise TypeError('openCL builtin function %r expected %i argument(s) (got %i)' % (self.name, len(self.argtypes), len(argtypes)))
            
            return self._return_type
            
    def ctype_string(self):
        return None
    
    def __call__(self, *args):
        if self.builtin is not None:
            return self.builtin(*args)
        elif self.emulate is not None:
            return self.builtin(*args)
        else: 
            raise NotImplementedError("python can not emulate this function yet.")
         

int_ctypes = {ctypes.c_int, ctypes.c_int32, ctypes.c_int8, ctypes.c_int16, ctypes.c_int64, ctypes.c_long , ctypes.c_longlong,
              ctypes.c_size_t, ctypes.c_ssize_t,
              ctypes.c_ubyte, ctypes.c_uint16, ctypes.c_uint64, ctypes.c_ulong, ctypes.c_ushort,
              ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_ulonglong,
              int}

unsigned_ctypes = {ctypes.c_ubyte, ctypes.c_uint16, ctypes.c_uint64, ctypes.c_ulong, ctypes.c_ushort,
                   ctypes.c_size_t, ctypes.c_ssize_t,
                   ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint8, ctypes.c_ulonglong}

float_types = {ctypes.c_float, ctypes.c_double, ctypes.c_longdouble, float}

type_groups = {'unsigned': unsigned_ctypes, 'int':int_ctypes, 'float':float_types}
type_group_weight = ['unsigned', 'int', 'float']

def groupof(ctype):
    for gname, group in type_groups.items():
        if ctype in group:
            return gname
        
    return None

def same_group(left, right):
    return groupof(left) == groupof(right)

def greatest_common_type(*args):
    if len(args) == 1:
        args = args[0]
        
    if len(args) == 1:
        return args[0]
    else:
        return reduce(_greatest_common_type, args)
  
vector_len = re.compile('^\((\d)\)([f|i|I|d|l|L])$')

def is_vetor_type(ctype):
    return vector_len.match(type_format(ctype)) is not None

def derefrence(ctype):
    
    if isinstance(ctype, cltype):
        return ctype.derefrence()
    elif is_vetor_type(ctype):
        return ctype._type_
    elif isclass(ctype) and issubclass(ctype, _ctypes._Pointer):
        return ctype._type_
    else:
        raise NotImplementedError(slice)

def typeof(ctx, obj):
    if isinstance(obj, cl.MemoryObject):
        return cl.global_memory(obj.ctype, ndim=len(obj.shape), shape=obj.shape, context=ctx)
    elif isinstance(obj, cl.local_memory):
        return obj
    elif isfunction(obj):
        return obj
    
    elif isinstance(obj, int):
        return ctypes.c_int
    elif isinstance(obj, float):
        return ctypes.c_float
    elif isinstance(obj, ctypes.Structure):
        return cl.constant_memory(type(obj), 0, (), context=ctx)
#        raise NotImplementedError("ctypes.Structure as parameter")
    else:
        try:
            view = memoryview(obj)
            return cl.global_memory(view.format, ndim=len(view.shape), shape=view.shape, context=ctx)
        except TypeError:
            pass
        
        return type(obj)


def _greatest_common_type(left, right):
    if not isclass(left):
        left = type(left)
    if not isclass(right):
        right = type(right)
        
    if left == int:
        left = ctypes.c_int32
    elif left == float:
        left = ctypes.c_float
    if right == int:
        right = ctypes.c_int32
    elif right == float:
        right = ctypes.c_float
    
    if left == right:
        return left
    
    if issubclass(left, _ctypes.Array):
        if not isinstance(right, _ctypes.Array):
            return left
        else:
            raise TypeError("type conversion for vector logic is not implemented yet")
    elif issubclass(right, _ctypes.Array):
        if not isinstance(left, _ctypes.Array):
            return right
        else:
            raise TypeError("type conversion for vector logic is not implemented yet")
        
    
    elif same_group(left, right):
        return max(left, right, key=lambda ctype:ctypes.sizeof(ctype))
    else:
        size = max(ctypes.sizeof(left), ctypes.sizeof(right))
        group = max(groupof(left), groupof(right), key=lambda group:type_group_weight.index(group))
        
        test = lambda ctype: issubclass(ctype, _ctypes._SimpleCData) and ctypes.sizeof(ctype) >= size 
        ctype = min([ctype for ctype in type_groups[group] if test(ctype)], key=lambda ctype:ctypes.sizeof(ctype))

        return ctype


class rtt(object):
    def __repr__(self):
        return '%s()' % self.__class__.__name__

class const_type(rtt):
    def __init__(self, ctype):
        self._ctype = ctype
    
    def resolve(self, locls, globls):
        return self._ctype

class type_tree(rtt):
    def __init__(self, ctype_list):
        self._ctype_list = ctype_list

class parameter_type(rtt):
    def __init__(self, param_id):
        self.param_id = param_id
        
class return_type(rtt):
    pass

class local_type(rtt):
    def __init__(self, param_id):
        self.param_id = param_id
    
    def resolve(self, locls, globls):
        return eval(self.param_id, locls, globls)


from opencl import cl_types
type_map = {
    cl_types.cl_char : 'char',
    cl_types.cl_char16 : 'char16',
    cl_types.cl_char2 : 'char2',
    cl_types.cl_char4 : 'char4',
    cl_types.cl_char8 : 'char8',
    cl_types.cl_double : 'double',
    cl_types.cl_double16 : 'double16',
    cl_types.cl_double2 : 'double2',
    cl_types.cl_double4 : 'double4',
    cl_types.cl_double8 : 'double8',
    cl_types.cl_float : 'float',
    cl_types.cl_float16 : 'float16',
    cl_types.cl_float2 : 'float2',
    cl_types.cl_float4 : 'float4',
    cl_types.cl_float8 : 'float8',
    cl_types.cl_half : 'half',
    cl_types.cl_int : 'int',
    cl_types.cl_int16 : 'int16',
    cl_types.cl_int2 : 'int2',
    cl_types.cl_int4 : 'int4',
    cl_types.cl_int8 : 'int8',
    cl_types.cl_long : 'long',
    cl_types.cl_long16 : 'long16',
    cl_types.cl_long2 : 'long2',
    cl_types.cl_long4 : 'long4',
    cl_types.cl_long8 : 'long8',
    cl_types.cl_short : 'short',
    cl_types.cl_short16 : 'short16',
    cl_types.cl_short2 : 'short2',
    cl_types.cl_short4 : 'short4',
    cl_types.cl_short8 : 'short8',
    cl_types.cl_uchar : 'uchar',
    cl_types.cl_uchar16 : 'uchar16',
    cl_types.cl_uchar2 : 'uchar2',
    cl_types.cl_uchar4 : 'uchar4',
    cl_types.cl_uchar8 : 'uchar8',
    cl_types.cl_uint : 'uint',
    cl_types.cl_uint16 : 'uint16',
    cl_types.cl_uint2 : 'uint2',
    cl_types.cl_uint4 : 'uint4',
    cl_types.cl_uint8 : 'uint8',
    cl_types.cl_ulong : 'ulong',
    cl_types.cl_ulong16 : 'ulong16',
    cl_types.cl_ulong2 : 'ulong2',
    cl_types.cl_ulong4 : 'ulong4',
    cl_types.cl_ulong8 : 'ulong8',
    cl_types.cl_ushort : 'ushort',
    cl_types.cl_ushort16 : 'ushort16',
    cl_types.cl_ushort2 : 'ushort2',
    cl_types.cl_ushort4 : 'ushort4',
    cl_types.cl_ushort8 : 'ushort8',

    }




def str_type(ctype, defined_types):
    if ctype in defined_types:
        return defined_types[ctype]
    elif ctype in type_map:
        return type_map[ctype]
    elif isroutine(ctype):
        return None
    elif isinstance(ctype, cl.contextual_memory):
        base_str = str_type(ctype.ctype, defined_types)
        return '%s %s*' % (ctype.qualifier, base_str)
    elif isinstance(ctype, cltype):
        return ctype.ctype_string()
    elif isinstance(ctype, str):
        return ctype
    else:
        format = type_format(ctype)
        return cdefn(format)

class TypeReplacer(Mutator):
    '''
    Replace ctype with opencl type string. 
    '''
    def __init__(self, defined_types):
        self.defined_types = defined_types
        self.new_types = {}
        
    def visitCVarDec(self, node):
        if not isinstance(node.ctype, cast.CTypeName):
            node.ctype = cast.CTypeName(str_type(node.ctype, self.defined_types))
        
        self.visitDefault(node)
        
    def visitCFunctionForwardDec(self, node):
        if not isinstance(node.return_type, cast.CTypeName):
            node.return_type = cast.CTypeName(str_type(node.return_type, self.defined_types))
        
        self.visitDefault(node)
            
    def visitCFunctionDef(self, node):
        if not isinstance(node.return_type, cast.CTypeName):
            node.return_type = cast.CTypeName(str_type(node.return_type, self.defined_types))
            
        self.visitDefault(node)
        
    def mutateDefault(self, node):
        if isinstance(node, ast.expr):
            if isinstance(node.ctype, RuntimeConstant):
                return cast.CName(node.ctype.name, ast.Load(), node.ctype.rtt)
        return Mutator.mutateDefault(self, node)
                
    def visitDefault(self, node):
        if isinstance(node, ast.expr):
            if not isinstance(node.ctype, cast.CTypeName):
                
                try:
                    type_repr = str_type(node.ctype, self.defined_types)
                except KeyError:
                    if isinstance(node.ctype, cl.contextual_memory):
                        ctype = node.ctype.ctype
                    else:
                        ctype = node.ctype
                        
                    base_name = 'cly_%s' % (ctype.__name__) 
                    type_repr = base_name
                    i = 0
                    while type_repr in self.defined_types.viewvalues():
                        i += 1
                        type_repr = '%s_%03i' % (base_name, i)
                        
                    self.defined_types[ctype] = type_repr
                    self.new_types[type_repr] = ctype
                    
                    if isinstance(node.ctype, cl.contextual_memory):
                        type_repr = str_type(node.ctype, self.defined_types)
                    
                node.ctype = cast.CTypeName(type_repr)
                
        visit_children(self, node)
        
        
def create_cstruct(struct_id, ctype, defined_types):
    decs = []
    
    for name, field in ctype._fields_:
        typename = cast.CTypeName(str_type(field, defined_types))
        decs.append(cast.CVarDec(name, typename))
    
    return cast.CStruct(struct_id, decs)

def replace_types(node):
    defined_types = {None:'void', str:'char*'}
    if isinstance(node, ast.Module):
        for statement in node.body:
            if isinstance(statement, cast.CStruct):
                defined_types[statement.ctype] = statement.id
    
    type_replacer = TypeReplacer(defined_types)
    
    type_replacer.mutate(node)
    type_replacer.visit(node)
    
    for name, ctype in type_replacer.new_types.items():
        c_struct = create_cstruct(name, ctype, type_replacer.defined_types)
        node.body.insert(0, c_struct)

########NEW FILE########
__FILENAME__ = runtime
'''
clyther.runtime
----------------
'''

__all__ = ['get_global_id', 'get_group_id', 'get_local_id', 'get_num_groups', 'get_global_size']

import opencl as cl
from clyther.rttt import RuntimeFunction, RuntimeType, gentype

# Get the global id
get_global_id = RuntimeFunction('get_global_id', cl.cl_uint, cl.cl_uint, emulate=None, doc='This is the doc for get_global_id')

get_group_id = RuntimeFunction('get_group_id', cl.cl_uint, cl.cl_uint)
get_local_id = RuntimeFunction('get_local_id', cl.cl_uint, cl.cl_uint)
get_num_groups = RuntimeFunction('get_num_groups', cl.cl_uint, cl.cl_uint)
get_global_size = RuntimeFunction('get_global_size', cl.cl_uint, cl.cl_uint,
                                  doc='''Returns the number of global work-items specified for 
                                  dimension identified by dimindx. This value is given by 
                                  the global_work_size argument to
                                  ''')


cl_mem_fence_flags = RuntimeType('cl_mem_fence_flags')

CLK_LOCAL_MEM_FENCE = cl_mem_fence_flags('CLK_LOCAL_MEM_FENCE') 
CLK_GLOBAL_MEM_FENCE = cl_mem_fence_flags('CLK_GLOBAL_MEM_FENCE') 

barrier = RuntimeFunction('barrier', None, cl_mem_fence_flags)

native_sin = RuntimeFunction('native_sin', cl.cl_float, cl.cl_float)

#===============================================================================
# Math builtin functions
#===============================================================================

import math

sin = RuntimeFunction('sin', lambda argtype: argtype, gentype(cl.cl_float), builtin=math.sin)
cos = RuntimeFunction('cos', lambda argtype: argtype, gentype(cl.cl_float), builtin=math.cos)



########NEW FILE########
__FILENAME__ = inspect_cly
'''
Created on Dec 20, 2011

@author: sean
'''
from argparse import ArgumentParser
import h5py
import pickle
from clyther.rttt import str_type
import opencl as cl



def create_parser():
    parser = ArgumentParser(description=__doc__)
    
    parser.add_argument('input')
    parser.add_argument('-f', '--functions', action='store_true')
    parser.add_argument('-s', '--short', action='store_true')
    return parser

def main():
    
    parser = create_parser()
    
    args = parser.parse_args()

    hf = h5py.File(args.input, 'r')
    
    
    for funcname in hf.keys():
        print "Kernel Function: '%s'" % (funcname,)
        
        func = hf[funcname]
        
        groups = {}
        for func_code_group in func.values():
            for arg_group in func_code_group.values():
                
                items = pickle.loads(arg_group.attrs['args'])
                
                if args.short:
                    argstr = ', '.join('%s' % str_type(item[1], {}) for item in items)
                else:
                    argstr = ', '.join('%s %s' % (str_type(item[1], {}), item[0]) for item in items)
                    
                name = arg_group.attrs['kernel_name']
                meta = arg_group.attrs['meta']
                
                if args.short:
                    defn = '%s(%s)' % (name, argstr)
                else:
                    defn = '__kernel void %s(%s);' % (name, argstr)

                groups.setdefault(meta, []).append(defn)
                
        for meta, kernels in groups.items():
            print "   + %s" % (meta,)
            for kernel in kernels:
                print "     - %s" % (kernel,)
                 
              
        
        

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_typify
'''
Created on Dec 22, 2011

@author: sean
'''
import unittest


class Test(unittest.TestCase):


    def test_wth(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_wth']
    unittest.main()
########NEW FILE########
__FILENAME__ = test_array_info
'''
Created on Jan 9, 2012

@author: sean
'''
import clyther as cly
from clyther.array import CLArrayContext
import opencl as cl
import unittest
import math
import os
import numpy as np
import clyther.runtime as clrt


ca = None

def setUpModule():
    global ca
    
    
    DEVICE_TYPE_ATTR = os.environ.get('DEVICE_TYPE', 'DEFAULT')
    DEVICE_TYPE = getattr(cl.Device, DEVICE_TYPE_ATTR)
    
    ca = CLArrayContext(device_type=DEVICE_TYPE)
    
    print ca.devices

class Test(unittest.TestCase):

    def test_simple_func(self):
        
        @cly.global_work_size(lambda a:a.shape)
        @cly.kernel
        def test_kernel(a):
            idx = clrt.get_global_id(0)
            a[idx] = idx 
            
        a = ca.empty([10], ctype='f')
        
        test_kernel(a.queue, a)
        self.assertEqual(a[1].item().value, 1)
        self.assertEqual(a[2].item().value, 2)
        self.assertEqual(a[3].item().value, 3)

        test_kernel(a.queue, a[::2])
        
        self.assertEqual(a[1].item().value, 1)
        self.assertEqual(a[2].item().value, 1)
        self.assertEqual(a[3].item().value, 3)
        self.assertEqual(a[4].item().value, 2)

    def test_2Dsimple_func(self):
        
        @cly.global_work_size(lambda a:a.shape)
        @cly.kernel
        def test_kernel(a):
            idx0 = clrt.get_global_id(0)
            idx1 = clrt.get_global_id(1)
            a[idx0, idx1] = idx0 * 100 + idx1 
            
        a = ca.empty([10, 10], ctype='f')
        
        test_kernel(a.queue, a)
        self.assertEqual(a[1, 1].item().value, 101)
        self.assertEqual(a[2, 2].item().value, 202)
        self.assertEqual(a[3, 2].item().value, 302)

        test_kernel(a.queue, a[::2, ::3])
        
        self.assertEqual(a[1, 1].item().value, 101)
        self.assertEqual(a[2, 3].item().value, 101)
        self.assertEqual(a[2, 2].item().value, 202)
        self.assertEqual(a[3, 2].item().value, 302)
    
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_bcast']
    unittest.main()

########NEW FILE########
__FILENAME__ = test_builtins
'''
Created on Dec 24, 2011

@author: sean
'''
import clyther as cly
from clyther.array import CLArrayContext
import opencl as cl
import unittest
import math
import os
import numpy as np


ca = None

def setUpModule():
    global ca
    
    
    DEVICE_TYPE_ATTR = os.environ.get('DEVICE_TYPE', 'DEFAULT')
    DEVICE_TYPE = getattr(cl.Device, DEVICE_TYPE_ATTR)
    
    ca = CLArrayContext(device_type=DEVICE_TYPE)
    
    print ca.devices

class Test(unittest.TestCase):

    def test_cos(self):
        
        @cly.task
        def do_sin(ret, value):
            ret[0] = math.sin(value)
         
        cy = ca.empty([1], 'f')
        nu = np.empty([1], 'f')
         
        do_sin(cy.queue, cy, math.pi / 2)
        do_sin.emulate(cy.queue, nu, math.pi / 2)
        
        with cy.map() as arr:
            self.assertTrue(np.allclose(arr, nu))

    def test_sin(self):
        
        @cly.task
        def do_sin(ret, value):
            ret[0] = math.sin(value)
         
        cy = ca.empty([1], 'f')
        nu = np.empty([1], 'f')
         
        do_sin(cy.queue, cy, math.pi / 2)
        do_sin.emulate(cy.queue, nu, math.pi / 2)
        
        with cy.map() as arr:
            self.assertTrue(np.allclose(arr, nu))



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_sim']
    unittest.main()

########NEW FILE########
__FILENAME__ = test_simple
'''
Created on Jan 9, 2012

@author: sean
'''
import clyther as cly
from clyther.array import CLArrayContext
import opencl as cl
import unittest
import math
import os
import numpy as np
import clyther.runtime as clrt

ca = None
def setUpModule():
    global ca
    
    
    DEVICE_TYPE_ATTR = os.environ.get('DEVICE_TYPE', 'DEFAULT')
    DEVICE_TYPE = getattr(cl.Device, DEVICE_TYPE_ATTR)
    
    ca = CLArrayContext(device_type=DEVICE_TYPE)
    
    print ca.devices


class TestBinaryOp(unittest.TestCase):

    def run_function(self, func, b, c):
        
        fmt = cl.type_formats.type_format(type(b))
        a = ca.empty([1], ctype=fmt)
        
        @cly.task
        def foo(a, b, c, function):
            a[0] = function(b, c)
            
        foo(ca, a, b, c, func)
        
        
        d = func(b, c)
        
        self.assertAlmostEqual(a[0].item().value, d)
     
    def test_add(self):
        
        self.run_function(lambda a, b: a + b, 1.0, 2.0)
         
    def test_sub(self):
        
        self.run_function(lambda a, b: a - b, 1.0, 2.0) 
        
    def test_mul(self):
        
        self.run_function(lambda a, b: a * b, 1.0, 2.0) 
        
    def test_pow(self):
        
        self.run_function(lambda a, b: a ** b, 2.0, 2.0) 
        
    def test_div(self):
        
        self.run_function(lambda a, b: a / b, 2.0, 5.0) 

class TestCompOp(unittest.TestCase):

    def run_function(self, func, b, c):
        
        a = ca.empty([1], ctype='B')
        
        @cly.task
        def foo(a, b, c, function):
            a[0] = function(b, c)
            
        foo(ca, a, b, c, func)
        
        
        d = func(b, c)
        
        self.assertAlmostEqual(a[0].item().value, d)

    def test_lt(self):
        
        self.run_function(lambda a, b: a < b, 2.0, 5.0) 
        self.run_function(lambda a, b: a < b, 5.0, 2.0) 

    def test_gt(self):

        self.run_function(lambda a, b: a > b, 2.0, 5.0) 
        self.run_function(lambda a, b: a > b, 5.0, 2.0) 

    def test_gtEq(self):

        self.run_function(lambda a, b: a >= b, 2.0, 5.0) 
        self.run_function(lambda a, b: a >= b, 5.0, 2.0) 
        self.run_function(lambda a, b: a >= b, 5.0, 5.0) 
        

    def test_ltEq(self):

        self.run_function(lambda a, b: a <= b, 2.0, 5.0) 
        self.run_function(lambda a, b: a <= b, 5.0, 2.0) 
        self.run_function(lambda a, b: a <= b, 5.0, 5.0) 
        
    def test_eq(self):

        self.run_function(lambda a, b: a == b, 2.0, 5.0) 
        self.run_function(lambda a, b: a == b, 5.0, 5.0) 

    def test_neq(self):

        self.run_function(lambda a, b: a != b, 2.0, 5.0) 
        self.run_function(lambda a, b: a != b, 5.0, 5.0) 
        

class TestStatements(unittest.TestCase):
    pass
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_add']
    unittest.main()


########NEW FILE########
__FILENAME__ = test_ufuncs
'''
Created on Dec 24, 2011

@author: sean
'''
import clyther as cly
from clyther.array import CLArrayContext
import opencl as cl
import unittest
import math
import os
import numpy as np

ca = None

def setUpModule():
    global ca
    
    
    DEVICE_TYPE_ATTR = os.environ.get('DEVICE_TYPE', 'DEFAULT')
    DEVICE_TYPE = getattr(cl.Device, DEVICE_TYPE_ATTR)
    
    ca = CLArrayContext(device_type=DEVICE_TYPE)
    
    print ca.devices

class Test(unittest.TestCase):


    def test_arange(self):
        a = ca.arange(5, ctype='f')
        npa = np.arange(5, dtype='f')
        
        with a.map() as view:
            self.assertTrue(np.allclose(view, npa))
        
    def test_add_scalar(self):
        
        a = ca.arange(5, ctype='f')
        a1 = ca.add(a, 5)

        b = np.arange(5, dtype='f')
        b1 = np.add(b, 5)
        
        self.assertEqual(a1.shape, b1.shape)
        
        with a1.map() as arr:
            self.assertTrue(np.allclose(arr, b1))
            
    def test_add_vector(self):
        
        a = ca.arange(5, ctype='f')
        x = ca.arange(5, ctype='f')
        
        a1 = ca.add(a, x)

        b = np.arange(5, dtype='f')
        y = np.arange(5, dtype='f')
        
        b1 = np.add(b, y)
        
        self.assertEqual(a1.shape, b1.shape)
        
        with a1.map() as arr:
            self.assertTrue(np.allclose(arr, b1))
            
    def test_add_vector_outer(self):
        
        a = ca.arange(5, ctype='f')
        x = ca.arange(5, ctype='f').reshape([5, 1])
        
        a1 = ca.add(a, x)

        b = np.arange(5, dtype='f')
        y = np.arange(5, dtype='f').reshape([5, 1])
        
        b1 = np.add(b, y)
        
        self.assertEqual(a1.shape, b1.shape)
        
        with a1.map() as arr:
            self.assertTrue(np.allclose(arr, b1))
        
    def test_sum(self):
        
        
        a = ca.arange(5, ctype='f')
        a1 = ca.sum(a)

        b = np.arange(5, dtype='f')
        b1 = np.sum(b)
        
        self.assertEqual(a1.size, b1.size)
        
        with a1.map() as arr:
            self.assertTrue(np.allclose(arr, b1))
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_add']
    unittest.main()

########NEW FILE########
__FILENAME__ = version
'''
Created on Jan 9, 2012

@author: sean
'''


__version__ = 'development'

########NEW FILE########
__FILENAME__ = convert_opencl
'''
'''
from cwrap.config import Config, File
from glob import glob
from argparse import ArgumentParser
from os.path import join, exists, abspath
if __name__ == '__main__':
    
    
    
    parser = ArgumentParser(description=__doc__)
    mac_frameworks = ['/System/Library/Frameworks/'] + glob('/Developer/SDKs/MacOSX*.sdk/System/Library/Frameworks')
    parser.add_argument('-F', action='append', dest='framework_paths', default=mac_frameworks)
    parser.add_argument('--framework', action='append', dest='frameworks', default=[])
    
    parser.add_argument('-I', action='append', dest='include_dirs', default=[])
    parser.add_argument('-i', '--header', action='append', dest='headers', default=[])
    parser.add_argument('-o', dest='output_dir', required=True)
     
    args = parser.parse_args()
    
    print args.framework_paths
    print args.frameworks
    
    for framework in args.frameworks:
        for fdir in args.framework_paths:
            path = join(abspath(fdir), framework + '.framework')
            if exists(path):
                args.include_dirs.append(path + '/Versions/Current/Headers/')
                break
        else:
            raise Exception("could not find framework %s" % (framework))
        
    headers = []
    for header in args.headers:
        for include in args.include_dirs:
            path = join(abspath(include), header)
            print "path", path
            if exists(path):
                headers.append(path)
                break
        else:
            raise Exception("could not find header %s" % (header))
            
    
    config = Config('gccxml', save_dir=args.output_dir, files=[File(header) for header in headers])
    config.generate()

########NEW FILE########
__FILENAME__ = demo

import opencl as cl
import clyther as cly
import clyther.array as ca
from ctypes import c_float
import numpy as np
#Always have to create a context.
ctx = cl.Context()

#can 
print ctx.devices

#Create an array
a = ca.arange(ctx, 12)

print a

#map is the same as a memory map
with a.map() as arr:
    print arr

#can clice
b = a[1::2]

with b.map() as arr:
    print arr

#ufuncs
c = a + 1

with c.map() as arr:
    print arr

# Multiply is not defined
try:
    c = a * 2
except TypeError as err:
    print 'Expected:', err
    
    
@ca.binary_ufunc
def multuply(x, y):
    return x * y

c = multuply(a, 2)

with c.map() as arr:
    print arr

#can do sin
d = ca.sin(c)


import clyther.runtime as clrt
#===============================================================================
# Controll the kernel
#===============================================================================


@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def generate_sin(a):
    
    gid = clrt.get_global_id(0)
    n = clrt.get_global_size(0)
    
    r = c_float(gid) / c_float(n)
    
    # sin wave with 16 occilations
    x = r * c_float(16.0 * 3.1415)
    
    # x is a range from -1 to 1
    a[gid].x = r * 2.0 - 1.0
    
    # y is sin wave
    a[gid].y = clrt.native_sin(x)

queue = cl.Queue(ctx)

a = cl.empty(ctx, [200], cly.float2)

event = generate_sin(queue, a)

event.wait()

print a
with a.map(queue) as view:
    print np.asarray(view)

#===============================================================================
# From here I can keep boiling down until I get the the bare openCL C framework 
#===============================================================================

#===============================================================================
# Plotting
#===============================================================================
from maka import roo

ctx = roo.start()
queue = cl.Queue(ctx)

a = cl.gl.empty_gl(ctx, [200], cly.float2)

event = generate_sin(queue, a)
event.wait()

roo.plot(a)

roo.show()

#===============================================================================
# Compile to openCL code 
#===============================================================================

print generate_sin.compile(ctx, a=cl.global_memory('f'), source_only=True) 


########NEW FILE########
__FILENAME__ = demo_1
'''
Created on Dec 15, 2011

@author: sean
'''

import opencl as cl
from clyther.array import CLArrayContext
#Always have to create a context.
ca = CLArrayContext()

#can print the current devices
print ca.devices

#Create an array
a = ca.arange(12)

print a

#map is the same as a memory map
with a.map() as arr:
    print arr

#can clice
b = a[1::2]

with b.map() as arr:
    print arr

#ufuncs
c = a + 1

with c.map() as arr:
    print arr

########NEW FILE########
__FILENAME__ = demo_2
'''
Created on Dec 15, 2011

@author: sean
'''


import opencl as cl
import clyther as cly
import clyther.array as ca
from ctypes import c_float
import numpy as np

#Always have to create a context.
ctx = cl.Context()

#Create an array
a = ca.arange(ctx, 12)

# Multiply is not defined
try:
    c = a * 2
except TypeError as err:
    print 'Expected:', err
    
    
@ca.binary_ufunc
def multuply(x, y):
    return x * y

c = multuply(a, 2)

with c.map() as arr:
    print arr

########NEW FILE########
__FILENAME__ = demo_3
'''
Created on Dec 15, 2011

@author: sean
'''

import opencl as cl
import clyther as cly
from ctypes import c_float
import numpy as np
from math import sin
import clyther.runtime as clrt
#===============================================================================
# Controll the kernel
#===============================================================================

#Always have to create a context.
ctx = cl.Context()

@cly.global_work_size(lambda a: a.shape)
@cly.kernel
def generate_sin(a):
    
    gid = clrt.get_global_id(0)
    n = clrt.get_global_size(0)
    
    r = c_float(gid) / c_float(n)
    
    # sin wave with 8 oscillations
    y = r * c_float(16.0 * 3.1415)
    
    # x is a range from -1 to 1
    a[gid].x = r * 2.0 - 1.0
    
    # y is sin wave
    a[gid].y = sin(y)

queue = cl.Queue(ctx)

a = cl.empty(ctx, [200], cl.cl_float2)
event = generate_sin(queue, a)

event.wait()

print a
with a.map(queue) as view:
    print np.asarray(view)

########NEW FILE########
__FILENAME__ = demo_compile
'''
Created on Dec 15, 2011

@author: sean
'''


import opencl as cl
import clyther as cly

import clyther.runtime as clrt

#Always have to create a context.
ctx = cl.Context()

@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def generate_sin(a):
    
    gid = clrt.get_global_id(0)
    n = clrt.get_global_size(0)
    
    r = cl.cl_float(gid) / cl.cl_float(n)
    
    # sin wave with 8 peaks
    y = r * cl.cl_float(16.0 * 3.1415)
    
    # x is a range from -1 to 1
    a[gid].x = r * 2.0 - 1.0
    
    # y is sin wave
    a[gid].y = clrt.native_sin(y)


#===============================================================================
# Compile to openCL code 
#===============================================================================

print generate_sin.compile(ctx, a=cl.global_memory(cl.cl_float2), source_only=True) 


########NEW FILE########
__FILENAME__ = demo_compile_err
'''
Created on Dec 15, 2011

@author: sean
'''


import opencl as cl
import clyther as cly
import clyther.array as ca
from ctypes import c_float
import numpy as np

import clyther.runtime as clrt

#Always have to create a context.
ctx = cl.Context()

@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def generate_sin(a):
    
    gid = clrt.get_global_id(0)
    n = clrt.get_global_size(0)
    
    r = c_float(gid) / c_float(n)
    
    # sin wave with 8 peaks
    y = r * c_float(16.0 * 3.1415)
    
    # x is a range from -1 to 1
    a[gid].x = r * 2.0 - 1.0
    
    # y is sin wave
    a[gid].y = clrt.native_sin(y)


#===============================================================================
# Compile to openCL code 
#===============================================================================

print generate_sin.compile(ctx, a=cl.global_memory('f'), source_only=True) 


########NEW FILE########
__FILENAME__ = demo_object
'''
Created on Jan 2, 2012

@author: sean
'''
import clyther as cly
import opencl as cl
from ctypes import Structure
from clyther.array import CLArrayContext

class Foo(Structure):
    _fields_ = [('i', cl.cl_float), ('j', cl.cl_float)]

    def bar(self):
        return self.i ** 2 + self.j ** 2
    
@cly.task
def objects(ret, foo):
    ret[0] = foo.bar()

def main():
    ca = CLArrayContext()  
    
    a = ca.empty([1], ctype='f')
    
    foo = Foo(10., 2.)
     
    objects(ca, a, foo)
    
    print "compiled result: ", a.item().value
    print "python result:   ", foo.bar()
    
    


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_reduce
'''
Created on Dec 11, 2011

@author: sean
'''
import clyther as cly
import clyther.array as ca
import clyther.runtime as clrt
import opencl as cl
from ctypes import c_float, c_int, c_uint
import numpy as np
import ctypes
from meta.decompiler import decompile_func
from meta.asttools.visitors.pysourcegen import python_source


def main():
    
    ctx = cl.Context(device_type=cl.Device.GPU)
    queue = cl.Queue(ctx)
    
    host_init = np.arange(8, dtype=c_float) + 1
    device_input = cl.from_host(ctx, host_init)
    
    output = ca.reduce(queue, lambda a, b: a + b, device_input)
    
    print "-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- "
    print "data:", host_init
    print "-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- "
    print "host   sum:", host_init.sum()
    
    with output.map(queue) as view:
        print "device sum:", np.asarray(view).item()

    output = ca.reduce(queue, lambda a, b: a * b, device_input, initial=1.0)
    
    print "host   product:", host_init.prod()
    
    with output.map(queue) as view:
        print "device product:", np.asarray(view).item()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = demo_roo
'''
Created on Dec 15, 2011

@author: sean
'''


import opencl as cl
import clyther as cly
import clyther.array as ca
from ctypes import c_float
import numpy as np

import clyther.runtime as clrt
#===============================================================================
# Controll the kernel
#===============================================================================

#Always have to create a context.
ctx = cl.Context()

@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def generate_sin(a):
    
    gid = clrt.get_global_id(0)
    n = clrt.get_global_size(0)
    
    r = c_float(gid) / c_float(n)
    
    # sin wave with 8 peaks
    y = r * c_float(16.0 * 3.1415)
    
    # x is a range from -1 to 1
    a[gid].x = r * 2.0 - 1.0
    
    # y is sin wave
    a[gid].y = clrt.native_sin(y)

queue = cl.Queue(ctx)

a = cl.empty(ctx, [200], cly.float2)

event = generate_sin(queue, a)

event.wait()

print a
with a.map(queue) as view:
    print np.asarray(view)

#===============================================================================
# Plotting
#===============================================================================
from maka import roo

ctx = roo.start()
queue = cl.Queue(ctx)

a = cl.gl.empty_gl(ctx, [200], cly.float2)

event = generate_sin(queue, a)
event.wait()

roo.plot(a)

roo.show()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Clyther documentation build configuration file, created by
# sphinx-quickstart on Sat Sep 24 21:31:29 2011.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode', 'sphinxtogithub', 'clyther.my_sphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Clyther'
copyright = u'2011, Sean Ross-Ross'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    from os.path import join
    exec open(join('..', 'clyther', 'version.py')).read()
except IOError as err:
    __version__ = '???'

# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__

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
#html_logo = 'logo_small.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = '_static/clyther.ico'

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
htmlhelp_basename = 'Clytherdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Clyther.tex', u'Clyther Documentation',
   u'Sean Ross-Ross', 'manual'),
]

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
    ('index', 'clyther', u'Clyther Documentation',
     [u'Sean Ross-Ross'], 1)
]

########NEW FILE########
__FILENAME__ = demo_1
'''
Created on Dec 15, 2011

@author: sean
'''

import opencl as cl
from clyther.array import CLArrayContext
#Always have to create a context.
ca = CLArrayContext()

#can print the current devices
print ca.devices

#Create an array
a = ca.arange(12)

print a

#map is the same as a memory map
with a.map() as arr:
    print arr

#can clice
b = a[1::2]

with b.map() as arr:
    print arr

#ufuncs
c = a + 1

with c.map() as arr:
    print arr

########NEW FILE########
__FILENAME__ = example
'''
Created on Jul 25, 2011

@author: sean
'''
from clyther import kernel, get_global_id, PyKernel
import pyopencl as cl
from ccode.buffer import int_p

PyKernel.use_cache = False

def addX(a, x):

    return a + x

def f1(ff, x):
    return ff(1, x)

gid = get_global_id

i = 1

@kernel()
def do_somthing(a, b):

    idx = get_global_id(0)
    b[idx] = a[idx]
    
    for i in range(10):
        exec """
        uchar16 vec;
        vec[0] = 1;
        break;
        """
    return

def main():
    ctx = cl.Context()

    cladd = do_somthing.compile(ctx, int_p, int_p)

    print cladd.src

if __name__ == '__main__':

    main()

    
# gather resources - recurse through functions and assign types
# close consts -
# expand loops 
# expand structs
# expand slices

########NEW FILE########
__FILENAME__ = new_types
'''
Created on Sep 25, 2011

@author: sean
'''


from ctypes import Structure, c_int, c_float
from clyther import kernel
import pyopencl as cl

class M(Structure):
    _fields_ = [('a', c_int),
                ('b', c_float),
                ]
    
    def foo(self):
        return self.a + self.b

def func(a): return a + 1

@kernel()
def kern(m, f2):
    
    c = func(m.a) + f2(m.b)
    

ctx = cl.Context()


built = kern.compile(ctx, m=M, f2=func)

m = M(a=1, b=2)

queue = cl.CommandQueue(ctx)
global_size = (1,)
local_size = (1,)
built(queue, global_size, local_size, m)

########NEW FILE########
__FILENAME__ = core
'''
Created on Dec 22, 2011

@author: sean
'''

class Grid(object):
    
    """A simple grid class that stores the details and solution of the
    computational grid."""
    
    def __init__(self, np, nx=10, ny=10, xmin=0.0, xmax=1.0,
                 ymin=0.0, ymax=1.0):
        self.np = np
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.dx = float(xmax - xmin) / (nx - 1)
        self.dy = float(ymax - ymin) / (ny - 1)
        self.u = np.zeros((nx, ny), 'f')
        # used to compute the change in solution in some of the methods.
        self.old_u = self.u.copy()        

    def setBC(self, l, r, b, t):        
        """Sets the boundary condition given the left, right, bottom
        and top values (or arrays)"""        
        self.u[0, :] = l
        self.u[-1, :] = r
        self.u[:, 0] = b
        self.u[:, -1] = t
        self.old_u = self.u.copy()

    def setBCFunc(self, func):
        """Sets the BC given a function of two variables."""
        xmin, ymin = self.xmin, self.ymin
        xmax, ymax = self.xmax, self.ymax
        x = self.np.arange(xmin, xmax + self.dx * 0.5, self.dx)
        y = self.np.arange(ymin, ymax + self.dy * 0.5, self.dy)
        self.u[0 , :] = func(xmin, y)
        self.u[-1, :] = func(xmax, y)
        self.u[:, 0] = func(x, ymin)
        self.u[:, -1] = func(x, ymax)

    def computeError(self):        
        """Computes absolute error using an L2 norm for the solution.
        This requires that self.u and self.old_u must be appropriately
        setup."""        
        v = (self.u - self.old_u).flat
        return self.np.sqrt(self.np.dot(v, v))

    
class TimeSteper(object):
    @classmethod
    def create_grid(cls, nx=500, ny=500):
        import numpy as np
        g = Grid(np, nx, ny)
        return g

    @classmethod
    def finish(cls, grid):
        pass


timestep_methods = {}
 
get_title = lambda func: func.__doc__.splitlines()[0].strip()

def available(test):
    def decorator(func):
        func.available = bool(test)
        timestep_methods[get_title(func)] = func
        return func
    
    return decorator

########NEW FILE########
__FILENAME__ = laplace
#!/usr/bin/env python

"""
This script compares different ways of implementing an iterative
procedure to solve Laplace's equation.  These provide a general
guideline to using Python for high-performance computing and also
provide a simple means to compare the computational time taken by the
different approaches.  The script compares functions implemented in
pure Python, Numeric, weave.blitz, weave.inline, fortran (via f2py)
and Pyrex.  The function main(), additionally accelerates the pure
Python version using Psyco and provides some numbers on how well that
works.  To compare all the options you need to have Numeric, weave,
f2py, Pyrex and Psyco installed.  If Psyco is not installed the script
will print a warning but will perform all other tests.

The fortran and pyrex modules are compiled using the setup.py script
that is provided with this file.  You can build them like so:

  python setup.py build_ext --inplace


Author: Prabhu Ramachandran <prabhu_r at users dot sf dot net>
License: BSD
Last modified: Sep. 18, 2004
"""

import numpy
from scipy import weave
import sys, time
from argparse import ArgumentParser, FileType

from core import TimeSteper, available, timestep_methods

import opencl_methods

try:
    import flaplace
    import flaplace90_arrays
    import flaplace95_forall
except ImportError:
    flaplace = None
    flaplace90_arrays = None
    flaplace95_forall = None
try:
    import pyx_lap
except ImportError:
    pyx_lap = None

@available(True)
class slow(TimeSteper):
    'slow'
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """pure-python
        Takes a time step using straight forward Python loops.
        """
        g = grid
        nx, ny = g.u.shape        
        dx2, dy2 = g.dx ** 2, g.dy ** 2
        dnr_inv = 0.5 / (dx2 + dy2)
        u = g.u
    
        err = 0.0
        for i in range(1, nx - 1):
            for j in range(1, ny - 1):
                tmp = u[i, j]
                u[i, j] = ((u[i - 1, j] + u[i + 1, j]) * dy2 + 
                          (u[i, j - 1] + u[i, j + 1]) * dx2) * dnr_inv
                diff = u[i, j] - tmp
                err += diff * diff
    
        return numpy.sqrt(err)
        
@available(True)
class numeric(TimeSteper):
    'numpy'
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """
        Takes a time step using a numeric expressions."""
        g = grid
        dx2, dy2 = g.dx ** 2, g.dy ** 2
        dnr_inv = 0.5 / (dx2 + dy2)
        u = g.u
        g.old_u = u.copy()
    
        # The actual iteration
        u[1:-1, 1:-1] = ((u[0:-2, 1:-1] + u[2:, 1:-1]) * dy2 + 
                         (u[1:-1, 0:-2] + u[1:-1, 2:]) * dx2) * dnr_inv
        
        return g.computeError()


@available(True)
class weave_blitz(TimeSteper):
    'weave-blitz'
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """weave-blitz
        Takes a time step using a numeric expression that has been
        blitzed using weave."""        
        g = grid
        dx2, dy2 = g.dx ** 2, g.dy ** 2
        dnr_inv = 0.5 / (dx2 + dy2)
        u = g.u
        g.old_u = u.copy()
    
        # The actual iteration
        expr = "u[1:-1, 1:-1] = ((u[0:-2, 1:-1] + u[2:, 1:-1])*dy2 + "\
               "(u[1:-1,0:-2] + u[1:-1, 2:])*dx2)*dnr_inv"
        weave.blitz(expr, check_size=0)
    
        return g.computeError()
    
@available(True)
class weave_fast_inline(TimeSteper):
    'weave-fast-inline'
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """weave-fast-inline
        Takes a time step using inlined C code -- this version is
        faster, dirtier and manipulates the numeric array in C.  This
        code was contributed by Eric Jones.  """
        g = grid
        nx, ny = g.u.shape
        dx2, dy2 = g.dx ** 2, g.dy ** 2
        dnr_inv = 0.5 / (dx2 + dy2)
        u = g.u
        
        code = """
               #line 151 "laplace.py"
               float tmp, err, diff;
               float *uc, *uu, *ud, *ul, *ur;
               err = 0.0;
               for (int i=1; i<nx-1; ++i) {
                   uc = u+i*ny+1;
                   ur = u+i*ny+2;     ul = u+i*ny;
                   ud = u+(i+1)*ny+1; uu = u+(i-1)*ny+1;
                   for (int j=1; j<ny-1; ++j) {
                       tmp = *uc;
                       *uc = ((*ul + *ur)*dy2 +
                              (*uu + *ud)*dx2)*dnr_inv;
                       diff = *uc - tmp;
                       err += diff*diff;
                       uc++;ur++;ul++;ud++;uu++;
                   }
               }
               return_val = sqrt(err);
               """
        # compiler keyword only needed on windows with MSVC installed
        err = weave.inline(code,
                           ['u', 'dx2', 'dy2', 'dnr_inv', 'nx', 'ny'],
                           compiler='gcc')
        return err
    
@available(flaplace is not None)
class fortran77(TimeSteper):
    'fortran77'
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """fortran77
        Takes a time step using a simple fortran module that
        implements the loop in fortran90 arrays.  Use f2py to compile
        flaplace.f like so: f2py -c flaplace.f -m flaplace.  You need
        the latest f2py version for this to work.  This Fortran
        example was contributed by Pearu Peterson. """
        g = grid
        g.u, err = flaplace.timestep(g.u, g.dx, g.dy)
        return err
    
@available(flaplace90_arrays is not None)
class fortran90(TimeSteper):
    'fortran90'
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """fortran90
        Takes a time step using a simple fortran module that
        implements the loop in fortran90 arrays.  Use
        f2py to compile flaplace_arrays.f90 like so: f2py -c
        flaplace_arrays.f90 -m flaplace90_arrays.  You need
        the latest f2py version for this to work.  This Fortran
        example was contributed by Ramon Crehuet. """
        g = grid
        g.u, err = flaplace90_arrays.timestep(g.u, g.dx, g.dy)
        return err
    
@available(flaplace95_forall is not None)
class fortran95(TimeSteper):
    'fortran95'
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """fortran95
        Takes a time step using a simple fortran module that
        implements the loop in fortran95 forall construct.  Use
        f2py to compile flaplace_forall.f95 like so: f2py -c
        flaplace_forall.f95 -m flaplace95_forall.  You need
        the latest f2py version for this to work.  This Fortran
        example was contributed by Ramon Crehuet. """
        g = grid
        g.u, err = flaplace95_forall.timestep(g.u, g.dx, g.dy)
        return err
    
@available(pyx_lap is not None)
class pyrex(TimeSteper):
    'pyrex'
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """pyrex
        Takes a time step using a function written in Pyrex.  Use
        the given setup.py to build the extension using the command
        python setup.py build_ext --inplace.  You will need Pyrex
        installed to run this."""        
        g = grid
        err = pyx_lap.pyrexTimeStep(g.u, g.dx, g.dy)
        return err
            
def solve(grid, timeStep, n_iter=0, eps=1.0e-16):        
    """Solves the equation given an error precision -- eps.  If
    n_iter=0 the solving is stopped only on the eps condition.  If
    n_iter is finite then solution stops in that many iterations
    or when the error is less than eps whichever is earlier.
    Returns the error if the loop breaks on the n_iter condition
    and returns the iterations if the loop breaks on the error
    condition."""        
    err = timeStep(grid)
    count = 1

    while True:
        if n_iter and count >= n_iter:
            return err
        err = timeStep(grid)
        count = count + 1

    return err


def BC(x, y):    
    """Used to set the boundary condition for the grid of points.
    Change this as you feel fit."""    
    return (x ** 2 - y ** 2)

def create_parser():
    parser = ArgumentParser(description=__doc__)
    
    parser.add_argument('-n', '--size', type=int, default=1000)
    parser.add_argument('-i', '--n_iter', type=int, default=100)
    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('-m', '--method', dest='methods', action='append', default=[])
    parser.add_argument('-e', '--exclude', action='append', default=[])
    parser.add_argument('-a', '--all', action='store_true')
    parser.add_argument('-o', '--output', type=FileType('w'))
    
    return parser

def main():
    
    parser = create_parser()
    
    args = parser.parse_args()
    
    available = {title:func for title, func in timestep_methods.items() if func.available}
    un_available = {title:func for title, func in timestep_methods.items() if not func.available}
    
    if args.list:
        print 
        print "Available Methods:"
        for title, func in available.items():
            print "    +", title
        print 
        print "Unavailable Methods:"
        for title, func in un_available.items():
            print "    +", title
        print 
        return
    
    if args.all:
        methods = set(available.keys())
    else:
        methods = set(args.methods)
        
    methods = sorted(methods - set(args.exclude))
        
    print >> sys.stderr, "args.methods", methods
    print >> args.output, "method, time"
    for method in methods:
        
        if method == 'slow':
            n_iter = 1
            scale = n_iter
        else:
            n_iter = args.n_iter
            scale = 1
             
        print >> sys.stderr, "method", method
        print >> sys.stderr, " + Doing %d iterations on a %dx%d grid" % (n_iter, args.size, args.size)
        
        cls = timestep_methods[method]
        grid = cls.create_grid(args.size, args.size)
        grid.setBCFunc(BC)
        
        try:
            t0 = time.time()
            err = solve(grid, cls.time_step, n_iter, eps=1.0e-16)
            
            print "err: ", err 
            cls.finish(grid)
            seconds0 = time.time() - t0
            if method == 'slow':
                print >> sys.stderr, " + Took", seconds0 * scale, "seconds (estimate)"
                print >> args.output, '%s, %r' % (method, seconds0 * scale)
            else:
                print >> sys.stderr, " + Took", seconds0, "seconds"
                print >> args.output, '%s, %r' % (method, seconds0)
        except Exception as err:
            print "%s: %s" % (type(err), err)
    return
     

if __name__ == "__main__":
    main()
    print "done!"

########NEW FILE########
__FILENAME__ = opencl_methods
'''
Created on Dec 22, 2011

@author: sean
'''

import opencl as cl
from clyther.array import CLArrayContext
import clyther as cly
import clyther.runtime as clrt
from core import Grid, available 
import numpy



class CLTimeSteper(object):
    DEVICE_TYPE = cl.Device.CPU
    @classmethod
    def create_grid(cls, nx=500, ny=500):
        ca = CLArrayContext(device_type=cls.DEVICE_TYPE)
        g = Grid(ca, nx, ny)
        g.queue = cl.Queue(ca)
        return g

    @classmethod
    def finish(cls, grid):
        grid.queue.finish()
        

class openclCheckerTimeStep(CLTimeSteper):
    @classmethod
    def create_grid(cls, nx=500, ny=500):
        ca = CLArrayContext(device_type=cls.DEVICE_TYPE)
        g = Grid(ca, nx, ny)
        
        dx2, dy2 = g.dx ** 2, g.dy ** 2
        dnr_inv = 0.5 / (dx2 + dy2)
          
        #self.ctx = cl.create_some_context()
    
        g.prg = cl.Program(ca, """
        __kernel void lp2dstep( __global float *u, const uint stidx )
        {          
            int i = get_global_id(0) + 1;
            int ny = %d;
        
            for ( int j = 1 + ( ( i + stidx ) %% 2 ); j<( %d-1 ); j+=2 ) {
                u[ny*j + i] = ((u[ny*(j-1) + i] + u[ny*(j+1) + i])*%g +
                                     (u[ny*j + i-1] + u[ny*j + i + 1])*%g)*%g;
            }
        }""" % (ny, ny, dy2, dx2, dnr_inv))
        
                        
        g.prg.build()

        g.lp2dstep = g.prg.lp2dstep
        
        g.lp2dstep.argnames = 'u', 'stidx'
        g.lp2dstep.argtypes = cl.global_memory(ctype='f'), cl.cl_uint
        g.lp2dstep.global_work_size = [nx - 2]
        
        g.queue = cl.Queue(ca)
        
        return g
    
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """
        Takes a time step using a PyOpenCL kernel based on inline C code from:
        http://www.scipy.org/PerformancePython
        The original method has been modified to use a red-black method that is
        more parallelizable.
        """
        nx, ny = grid.u.shape
        
        event = grid.lp2dstep(grid.queue, grid.u, 1)
        grid.queue.enqueue_wait_for_events(event)
        
        event = grid.lp2dstep(grid.queue, grid.u, 2)
        grid.queue.enqueue_wait_for_events(event)
        
@available(True)
class opencl_cpu(openclCheckerTimeStep):
    'opencl-cpu'
    DEVICE_TYPE = cl.Device.CPU



@available(True)
class opencl_gpu(openclCheckerTimeStep):
    'opencl-gpu'
    DEVICE_TYPE = cl.Device.GPU

#===============================================================================
# 
#===============================================================================

@cly.global_work_size(lambda u: [u.shape[0] - 2])
@cly.kernel
def lp2dstep(u, dx2, dy2, dnr_inv, stidx):
    i = clrt.get_global_id(0) + 1
    
    ny = u.shape[1]
    
    for j in range(1 + ((i + stidx) % 2), ny - 1, 2):
        u[j, i] = ((u[j - 1, i] + u[j + 1, i]) * dy2 + 
                   (u[j, i - 1] + u[j, i + 1]) * dx2) * dnr_inv

class clytherCheckerTimeStep(CLTimeSteper):
    @classmethod
    def create_grid(cls, nx=500, ny=500):
        ca = CLArrayContext(device_type=cls.DEVICE_TYPE)
        g = Grid(ca, nx, ny)

        g.queue = cl.Queue(ca)
        
        return g
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """
        Takes a time step using a PyOpenCL kernel based on inline C code from:
        http://www.scipy.org/PerformancePython
        The original method has been modified to use a red-black method that is
        more parallelizable.
        """
        dx2, dy2 = grid.dx ** 2, grid.dy ** 2
        dnr_inv = 0.5 / (dx2 + dy2)
        
        event = lp2dstep(grid.queue, grid.u, dx2, dy2, dnr_inv, 1)
        grid.queue.enqueue_wait_for_events(event)
        
        event = lp2dstep(grid.queue, grid.u, dx2, dy2, dnr_inv, 2)
        grid.queue.enqueue_wait_for_events(event)
        
        

@available(True)
class clyther_checker_cpu(clytherCheckerTimeStep):
    'clyther-checker-cpu'
    DEVICE_TYPE = cl.Device.CPU

@available(True)
class clyther_checker_gpu(clytherCheckerTimeStep):
    'clyther-checker-gpu'
    DEVICE_TYPE = cl.Device.GPU


#===============================================================================
# 
#===============================================================================


@cly.task
def cly_time_step_task(u, dy2, dx2, dnr_inv, error):
    # The actual iteration
    nx = u.shape[0] 
    ny = u.shape[1]
    err = 0.0
    for i in range(1, nx - 1):
        for j in range(1, ny - 1):
            tmp = u[i, j]
            u[i, j] = ((u[i - 1, j] + u[i + 1, j]) * dy2 + 
                      (u[i, j - 1] + u[i, j + 1]) * dx2) * dnr_inv
                      
            diff = u[i, j] - tmp
            err += diff * diff
            
    error[0] = err
    

@available(cly is not None)
class clyther_task(CLTimeSteper):
    'clyther-task'
    
    @classmethod
    def time_step(cls, grid, dt=0.0):
        """clyther-task
        Takes a time step using a numeric expressions."""
        g = grid
        dx2, dy2 = g.dx ** 2, g.dy ** 2
        dnr_inv = 0.5 / (dx2 + dy2)
        u = g.u
        
        error = g.np.empty([1], ctype='f')
            
        cly_time_step_task(u.queue, u, dy2, dx2, dnr_inv, error)
        
        return error.item().value

########NEW FILE########
__FILENAME__ = runtime_doc
'''
Created on Dec 24, 2011

@author: sean
'''

from sphinx.ext.autodoc import ModuleLevelDocumenter 
import inspect

class RuntimeFunctionDocumenter(ModuleLevelDocumenter):
    """
    Specialized Documenter subclass for functions.
    """
    objtype = 'clrt'
    directivetype = 'function'
    member_order = 30

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        import clyther.rttt
        return isinstance(member, clyther.rttt.RuntimeFunction)

    def format_args(self):
        argtypes = self.object.argtypes
        
        args = '(' + ', '.join([str(arg.__name__) for arg in argtypes]) + ')'
        return args
    
    def document_members(self, all_members=False):
        pass



def setup(app):
    app.add_autodocumenter(RuntimeFunctionDocumenter)

########NEW FILE########
__FILENAME__ = conv
'''
Created on Dec 7, 2011

@author: sean
'''

import clyther as cly
import clyther.runtime as clrt
import opencl as cl
from ctypes import c_float, c_int
import numpy as np
import ctypes

@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def setslice(a, value):
    
    i = clrt.get_global_id(0)
    a[i] = value
    
    clrt.barrier(clrt.CLK_GLOBAL_MEM_FENCE)

@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def conv(a, b, ret):
    
    i = clrt.get_global_id(0)
    ret[i] = b.size
    
def main():
    
    ctx = cl.Context(device_type=cl.Device.GPU)

    ret = cl.empty(ctx, [16], 'l')

    queue = cl.Queue(ctx)
        
        
    print setslice.compile(ctx, a=cl.global_memory('l'), value=c_int, source_only=True)
    
#    print setslice(queue, ret[::2], c_int(6))
#    print setslice(queue, ret[1::2], c_int(5))
    
    with ret.map(queue) as foo:
        print np.asarray(foo)


#    kernel = conv._cache.values()[0].values()[0]
    
#    print kernel.program.source
    
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = example1
import clyther as cly

import opencl as cl

import clyther.runtime as clrt

@cly.global_work_size(lambda a: a.shape)
@cly.kernel
def foo(a):
    x = clrt.get_global_id(0)
    y = clrt.get_global_id(1)
   
    a[x, y] = x + y * 100
     
ctx = cl.Context(device_type=cl.Device.CPU)

queue = cl.Queue(ctx)

a = cl.empty(ctx, [4, 4], 'f')

foo(queue, a)

print foo._compile(ctx, a=cl.global_memory('f'), source_only=True)

import numpy as np
with a.map(queue) as view:
    print np.asarray(view)

########NEW FILE########
__FILENAME__ = gl_integration
# IPython log file

import numpy as np
import opencl as cl
from PySide.QtGui import *
from PySide.QtOpenGL import *
from OpenGL import GL

app = QApplication([])
qgl = QGLWidget()
qgl.makeCurrent()

props = cl.ContextProperties()
cl.gl.set_opengl_properties(props)

ctx = cl.Context(device_type=cl.Device.DEFAULT, properties=props)

#print cl.ImageFormat.supported_formats(ctx)
print ctx.devices

view = cl.gl.empty_gl(ctx, [10], ctype='ff')
view2 = cl.empty(ctx, [10], ctype='ff')

view.shape

print view
queue = cl.Queue(ctx)

with cl.gl.acquire(queue, view), view.map(queue) as buffer:
    print np.asarray(buffer)

print
print 'cl.gl.is_gl_object: view2', cl.gl.is_gl_object(view2)
print 'cl.gl.is_gl_object: view ', cl.gl.is_gl_object(view)
print 'cl.gl.get_gl_name', cl.gl.get_gl_name(view)
print


iamge_format = cl.ImageFormat('CL_RGBA', 'CL_UNORM_INT8')

shape = 32, 32, 32

GL_FORMAT = cl.gl.get_gl_image_format(iamge_format)

#print "GL_FORMAT", GL_FORMAT
#print "GL.GL_RGBA", GL.GL_RGBA
#GL.glEnable(GL.GL_TEXTURE_2D)
#texture = GL.glGenTextures(1)
#GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
#GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, 4, shape[0], shape[1], 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
#GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

image = cl.gl.empty_gl_image(ctx, shape, None)

print "image.shape"
print image.shape
print 
print 
with cl.gl.acquire(queue, image), image.map(queue) as buffer:
    array = np.asarray(buffer)
    array[:] = 0

with cl.gl.acquire(queue, image), image.map(queue) as buffer:
    array = np.asarray(buffer)
    print array

print image.image_format
print "done"


########NEW FILE########
__FILENAME__ = gl_interop_demo
'''
Created on Dec 8, 2011

@author: sean
'''

from OpenGL.GL import *
from OpenGL.GLUT import *
import opencl as cl
from ctypes import c_float
from clyther.types import float2
import clyther as cly
import clyther.runtime as clrt
import numpy as np


@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def generate_sin(a):
    gid = clrt.get_global_id(0)
    n = clrt.get_global_size(0)
    r = c_float(gid) / c_float(n)
    
    x = r * c_float(16.0) * c_float(3.1415)
    
    a[gid].x = c_float(r * 2.0) - c_float(1.0)
    a[gid].y = clrt.native_sin(x)

n_vertices = 100
coords_dev = None

def initialize():
    global coords_dev, n_vertices
    
    ctx = cl.gl.context()

    coords_dev = cl.gl.empty_gl(ctx, [n_vertices], ctype=float2)
    
    glClearColor(1, 1, 1, 1)
    glColor(0, 0, 1)
    
    queue = cl.Queue(ctx)
    
    with cl.gl.acquire(queue, coords_dev):
        generate_sin(queue, coords_dev)
        
    glEnableClientState(GL_VERTEX_ARRAY)
    
def display():
    global coords_dev, n_vertices

    glClear(GL_COLOR_BUFFER_BIT)
    
    vbo = cl.gl.get_gl_name(coords_dev)
    
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glVertexPointer(2, GL_FLOAT, 0, None)
    glDrawArrays(GL_LINE_STRIP, 0, n_vertices)
    
    glFlush()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)

if __name__ == '__main__':
    import sys
    glutInit(sys.argv)
    if len(sys.argv) > 1:
        n_vertices = int(sys.argv[1])
    glutInitWindowSize(800, 160)
    glutInitWindowPosition(0, 0)
    glutCreateWindow('OpenCL/OpenGL Interop Tutorial: Sin Generator')
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    initialize()
    glutMainLoop()

########NEW FILE########
__FILENAME__ = print_device_info
'''
Created on Dec 7, 2011

@author: sean
'''
import opencl as cl

DMAP = {cl.Device.CPU:'CPU', cl.Device.GPU:'GPU'}
def main():
    
    for platform in cl.get_platforms():
        print "Platform %r version: %s" % (platform.name, platform.version)
        
        for device in platform.devices():
            print " ++  %s Device %r" % (DMAP[device.type], device.name) 
            
            print "     | global_mem_size", device.global_mem_size / (1024 ** 2), 'Mb'
            print "     | local_mem_size", device.local_mem_size / (1024 ** 1), 'Kb'
            print "     | max_mem_alloc_size", device.max_mem_alloc_size / (1024 ** 2), 'Mb'
            print "     | has_image_support", device.has_image_support
            print "     | has_native_kernel", device.has_native_kernel
            print "     | max_compute_units", device.max_compute_units
            print "     | max_work_item_dimension", device.max_work_item_dimensions
            print "     | max_work_item_sizes", device.max_work_item_sizes
            print "     | max_work_group_size", device.max_work_group_size
            print "     | max_clock_frequency", device.max_clock_frequency, 'MHz'
            print "     | address_bits", device.address_bits, 'bits'
            print "     | max_read_image_args", device.max_read_image_args
            print "     | max_write_image_args", device.max_write_image_args
            print "     | max_image2d_shape", device.max_image2d_shape
            print "     | max_image3d_shape", device.max_image3d_shape
            print "     | max_parameter_size", device.max_parameter_size, 'bytes'
            print "     | max_const_buffer_size", device.max_const_buffer_size, 'bytes'
            print "     | has_local_mem", device.has_local_mem
            print "     | host_unified_memory", device.host_unified_memory
            print "     | available", device.available
            print "     | compiler_available", device.compiler_available
            print "     | driver_version", device.driver_version
            print "     | device_profile", device.profile
            print "     | version", device.version
#            print "     | extensions", device.extensions
            print 




if __name__ == '__main__':
    main()
    

########NEW FILE########
__FILENAME__ = reduce
'''
Created on Dec 11, 2011

@author: sean
'''
#import clyther as cly
#import clyther.runtime as clrt
#import clyther.array as ca
from clyther.array import CLArrayContext
import opencl as cl
import numpy as np

def main():
    
    ca = CLArrayContext(device_type=cl.Device.GPU)
    
    size = 8
    
    device_input = ca.arange(size)
    
    output = ca.add.reduce(device_input)
    
    print output.item()
    with output.map() as view:
        print "device sum", np.asarray(view).item()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sin_wave
'''
Created on Dec 12, 2011

@author: sean
'''
from ctypes import *
import clyther as cly
import opencl as cl
import clyther.runtime as clrt
import numpy as np

@cly.global_work_size(lambda a: [a.size])
@cly.kernel
def generate_sin(a):
    gid = clrt.get_global_id(0)
    n = clrt.get_global_size(0)
    r = c_float(gid) / c_float(n)
    
    x = r * c_float(16.0) * c_float(3.1415)
    
    a[gid].x = c_float(r * 2.0) - c_float(1.0)
    a[gid].y = clrt.native_sin(x)
    
    
def main():
    ctx = cl.Context()
    a = cl.empty(ctx, [256], cly.float2)
    
    queue = cl.Queue(ctx)
    
    generate_sin(queue, a)
    
    with a.map(queue) as view:
        array = np.asarray(view)
        print array
        
if __name__ == '__main__':
    main()


[('x','float'),('y','float')]
########NEW FILE########
__FILENAME__ = ufunc
'''
Created on Dec 12, 2011

@author: sean
'''
import clyther as cly
import  clyther.array as ca 
import opencl as cl
from ctypes import c_float
import numpy as np

@ca.binary_ufunc
def add(a, b): 
    return a + b


def main():
    ctx = cl.Context(device_type=cl.Device.GPU)
    queue = cl.Queue(ctx)
    
    npa = np.arange(1.0 * 12.0, dtype=c_float)
    a = ca.arange(ctx, 12, ctype=c_float)
    
    out = ca.empty_like(a[:])
    output = cl.broadcast(out, a[:].shape)
    
    ca.blitz(queue, lambda: a[:] + a[:] + 1, out=output)
    
    print npa[1:] + npa[:-1]
    
    with out.map() as view:
        print view
    
def main_reduce():
    ctx = cl.Context(device_type=cl.Device.GPU)
    
    sum = add.reduce
    
#    for size in range(250, 258):
    size = 1027
        
    a = ca.arange(ctx, size, ctype=cl.cl_int)
    
    result = sum(a)
    
    with a.map() as view:
        print size, view.sum(), result.item()
    
    
def main_ufunc():
    
    ctx = cl.Context(device_type=cl.Device.GPU)
    
    size = 10
    a = ca.arange(ctx, size, ctype=c_float)
    b = ca.arange(ctx, size, ctype=c_float).reshape([size, 1])

    o1 = add(a, b)
    
    with o1.map() as view:
        print view

    with a.map() as view:
        print np.sum(view)

    result = add.reduce(a)
    
    result.queue.finish()
    
    with a.map() as view:
        print view
        print view.sum()
        
    print result.item()
    
if __name__ == '__main__':
    main_reduce()

########NEW FILE########
