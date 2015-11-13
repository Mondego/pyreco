__FILENAME__ = configure
#! /usr/bin/env python

from aksetup_helper import configure_frontend
configure_frontend()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyCUDA documentation build configuration file, created by
# sphinx-quickstart on Fri Jun 13 00:51:19 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

#import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'PyCUDA'
copyright = '2008, Andreas Kloeckner'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
ver_dic = {}
execfile("../../pycuda/__init__.py", ver_dic)
version = ".".join(str(x) for x in ver_dic["VERSION"])
# The full version, including alpha/beta/rc tags.
release = ver_dic["VERSION_TEXT"]

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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


# Options for HTML output
# -----------------------

try:
    import sphinx_bootstrap_theme
except:
    from warnings import warn
    warn("I would like to use the sphinx bootstrap theme, but can't find it.\n"
            "'pip install sphinx_bootstrap_theme' to fix.")
else:
    # Activate the theme.
    html_theme = 'bootstrap'
    html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

    # Theme options are theme-specific and customize the look and feel of a theme
    # further.  For a list of options available for each theme, see the
    # documentation.
    html_theme_options = {
            "navbar_fixed_top": "true",
            "navbar_site_name": "Contents",
            'bootstrap_version': '3',
            'source_link_position': 'footer',
            }

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyCudadoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'pycdua.tex', 'PyCUDA Documentation', 'Andreas Kloeckner', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

intersphinx_mapping = {
        'http://docs.python.org/dev': None,
        'http://docs.scipy.org/doc/numpy/': None,
        'http://documen.tician.de/codepy/': None,
        }

########NEW FILE########
__FILENAME__ = demo
# Sample source code from the Tutorial Introduction in the documentation.

import pycuda.driver as cuda
import pycuda.autoinit  # noqa
from pycuda.compiler import SourceModule

import numpy
a = numpy.random.randn(4, 4)

a = a.astype(numpy.float32)

a_gpu = cuda.mem_alloc(a.size * a.dtype.itemsize)

cuda.memcpy_htod(a_gpu, a)

mod = SourceModule("""
    __global__ void doublify(float *a)
    {
      int idx = threadIdx.x + threadIdx.y*4;
      a[idx] *= 2;
    }
    """)

func = mod.get_function("doublify")
func(a_gpu, block=(4, 4, 1), grid=(1, 1), shared=0)

a_doubled = numpy.empty_like(a)
cuda.memcpy_dtoh(a_doubled, a_gpu)
print "original array:"
print a
print "doubled with kernel:"
print a_doubled

# alternate kernel invocation -------------------------------------------------

func(cuda.InOut(a), block=(4, 4, 1))
print "doubled with InOut:"
print a

# part 2 ----------------------------------------------------------------------

import pycuda.gpuarray as gpuarray
a_gpu = gpuarray.to_gpu(numpy.random.randn(4, 4).astype(numpy.float32))
a_doubled = (2*a_gpu).get()

print "original array:"
print a_gpu
print "doubled with gpuarray:"
print a_doubled

########NEW FILE########
__FILENAME__ = demo_elementwise
import pycuda.gpuarray as gpuarray
import pycuda.autoinit
import numpy
from pycuda.curandom import rand as curand

a_gpu = curand((50,))
b_gpu = curand((50,))

from pycuda.elementwise import ElementwiseKernel
lin_comb = ElementwiseKernel(
        "float a, float *x, float b, float *y, float *z",
        "z[i] = my_f(a*x[i], b*y[i])",
        "linear_combination",
        preamble="""
        __device__ float my_f(float x, float y)
        { 
          return sin(x*y);
        }
        """)

c_gpu = gpuarray.empty_like(a_gpu)
lin_comb(5, a_gpu, 6, b_gpu, c_gpu)

#import numpy.linalg as la
#assert la.norm((c_gpu - (5*a_gpu+6*b_gpu)).get()) < 1e-5

########NEW FILE########
__FILENAME__ = demo_meta_codepy
import pycuda.driver as cuda
import pycuda.autoinit
import numpy
import numpy.linalg as la
from pycuda.compiler import SourceModule

thread_strides = 16
block_size = 256
macroblock_count = 33

total_size = thread_strides*block_size*macroblock_count
dtype = numpy.float32

a = numpy.random.randn(total_size).astype(dtype)
b = numpy.random.randn(total_size).astype(dtype)

a_gpu = cuda.to_device(a)
b_gpu = cuda.to_device(b)
c_gpu = cuda.mem_alloc(a.nbytes)

from cgen import FunctionBody, \
        FunctionDeclaration, POD, Value, \
        Pointer, Module, Block, Initializer, Assign
from cgen.cuda import CudaGlobal

mod = Module([
    FunctionBody(
        CudaGlobal(FunctionDeclaration(
            Value("void", "add"),
            arg_decls=[Pointer(POD(dtype, name)) 
                for name in ["tgt", "op1", "op2"]])),
        Block([
            Initializer(
                POD(numpy.int32, "idx"),
                "threadIdx.x + %d*blockIdx.x" 
                % (block_size*thread_strides)),
            ]+[
            Assign(
                "tgt[idx+%d]" % (o*block_size),
                "op1[idx+%d] + op2[idx+%d]" % (
                    o*block_size, 
                    o*block_size))
            for o in range(thread_strides)]))])

mod = SourceModule(mod)

func = mod.get_function("add")
func(c_gpu, a_gpu, b_gpu, 
        block=(block_size,1,1),
        grid=(macroblock_count,1))

c = cuda.from_device_like(c_gpu, a)

assert la.norm(c-(a+b)) == 0


########NEW FILE########
__FILENAME__ = demo_meta_template
import pycuda.driver as cuda
import pycuda.autoinit
import numpy
import numpy.linalg as la
from pycuda.compiler import SourceModule

thread_strides = 16
block_size = 32
macroblock_count = 33

total_size = thread_strides*block_size*macroblock_count
dtype = numpy.float32

a = numpy.random.randn(total_size).astype(dtype)
b = numpy.random.randn(total_size).astype(dtype)

a_gpu = cuda.to_device(a)
b_gpu = cuda.to_device(b)
c_gpu = cuda.mem_alloc(a.nbytes)

from jinja2 import Template

tpl = Template("""
    __global__ void add(
            {{ type_name }} *tgt, 
            {{ type_name }} *op1, 
            {{ type_name }} *op2)
    {
      int idx = threadIdx.x + 
        {{ block_size }} * {{thread_strides}}
        * blockIdx.x;

      {% for i in range(thread_strides) %}
          {% set offset = i*block_size %}
          tgt[idx + {{ offset }}] = 
            op1[idx + {{ offset }}] 
            + op2[idx + {{ offset }}];
      {% endfor %}
    }""")

rendered_tpl = tpl.render(
    type_name="float", thread_strides=thread_strides,
    block_size=block_size)

mod = SourceModule(rendered_tpl)
# end

func = mod.get_function("add")
func(c_gpu, a_gpu, b_gpu, 
        block=(block_size,1,1),
        grid=(macroblock_count,1))

c = cuda.from_device_like(c_gpu, a)

assert la.norm(c-(a+b)) == 0

########NEW FILE########
__FILENAME__ = demo_struct
# prepared invocations and structures -----------------------------------------

import pycuda.driver as cuda
import pycuda.autoinit
import numpy
from pycuda.compiler import SourceModule

class DoubleOpStruct:
    mem_size = 8 + numpy.intp(0).nbytes
    def __init__(self, array, struct_arr_ptr):
        self.data = cuda.to_device(array)
        self.shape, self.dtype = array.shape, array.dtype
        cuda.memcpy_htod(int(struct_arr_ptr), numpy.int32(array.size))
        cuda.memcpy_htod(int(struct_arr_ptr) + 8, numpy.intp(int(self.data)))

    def __str__(self):
        return str(cuda.from_device(self.data, self.shape, self.dtype))

struct_arr = cuda.mem_alloc(2 * DoubleOpStruct.mem_size)
do2_ptr = int(struct_arr) + DoubleOpStruct.mem_size

array1 = DoubleOpStruct(numpy.array([1, 2, 3], dtype=numpy.float32), struct_arr)
array2 = DoubleOpStruct(numpy.array([0, 4], dtype=numpy.float32), do2_ptr)

print "original arrays"
print array1
print array2

mod = SourceModule("""
    struct DoubleOperation {
        int datalen, __padding; // so 64-bit ptrs can be aligned
        float *ptr;
    };


    __global__ void double_array(DoubleOperation *a) 
    {
        a = a + blockIdx.x;
        for (int idx = threadIdx.x; idx < a->datalen; idx += blockDim.x) 
        {
            float *a_ptr = a->ptr;
            a_ptr[idx] *= 2;
        }
    }
    """)
func = mod.get_function("double_array")
func(struct_arr, block = (32, 1, 1), grid=(2, 1))

print "doubled arrays"
print array1
print array2

func(numpy.intp(do2_ptr), block = (32, 1, 1), grid=(1, 1))
print "doubled second only"
print array1
print array2

func.prepare("P", block=(32, 1, 1))
func.prepared_call((2, 1), struct_arr)

print "doubled again"
print array1
print array2

func.prepared_call((1, 1), do2_ptr)

print "doubled second only again"
print array1
print array2

########NEW FILE########
__FILENAME__ = download-examples-from-wiki
#! /usr/bin/env python

import xmlrpclib
destwiki = xmlrpclib.ServerProxy("http://wiki.tiker.net?action=xmlrpc2")

import os
try:
    os.mkdir("wiki-examples")
except OSError:
    pass

print "downloading  wiki examples from http://wiki.tiker.net/PyCuda/Examples to wiki-examples/..."
print "fetching page list..."
all_pages = destwiki.getAllPages()


from os.path import exists

for page in all_pages:
    if not page.startswith("PyCuda/Examples/"):
        continue

    print page
    try:
        content = destwiki.getPage(page)

        import re
        match = re.search(r"\{\{\{\#\!python(.*)\}\}\}", content, re.DOTALL)
        code = match.group(1)

        match = re.search("([^/]+)$", page)
        fname = match.group(1)

        outfname = os.path.join("wiki-examples", fname+".py")
        if exists(outfname):
            print "%s exists, refusing to overwrite." % outfname
        else:
            outf = open(outfname, "w")
            outf.write(code)
            outf.close()

        for att_name in destwiki.listAttachments(page):
            content = destwiki.getAttachment(page, att_name)

            outfname = os.path.join("wiki-examples", att_name)
            if exists(outfname):
                print "%s exists, refusing to overwrite." % outfname
            else:
                outf = open(outfname, "w")
                outf.write(str(content))
                outf.close()

    except Exception, e:
        print "Error when processing %s: %s" % (page, e)
        from traceback import print_exc
        print_exc()

########NEW FILE########
__FILENAME__ = dump_properties
import pycuda.driver as drv



drv.init()
print "%d device(s) found." % drv.Device.count()

for ordinal in range(drv.Device.count()):
    dev = drv.Device(ordinal)
    print "Device #%d: %s" % (ordinal, dev.name())
    print "  Compute Capability: %d.%d" % dev.compute_capability()
    print "  Total Memory: %s KB" % (dev.total_memory()//(1024))
    atts = [(str(att), value) 
            for att, value in dev.get_attributes().iteritems()]
    atts.sort()
    
    for att, value in atts:
        print "  %s: %s" % (att, value)


########NEW FILE########
__FILENAME__ = fill_gpu_with_nans
import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import pycuda.driver as cuda
import numpy

free_bytes, total_bytes = cuda.mem_get_info()
exp = 10
while True:
    fill_floats = free_bytes / 4 - (1<<exp)
    if fill_floats < 0:
        raise RuntimeError("couldn't find allocatable size")
    try:
        print "alloc", fill_floats
        ary = gpuarray.empty((fill_floats,), dtype=numpy.float32)
        break
    except:
        pass

    exp += 1

ary.fill(float("nan"))

print "filled %d out of %d bytes with NaNs" % (fill_floats*4, free_bytes)


########NEW FILE########
__FILENAME__ = hello_gpu
import pycuda.driver as drv
import pycuda.tools
import pycuda.autoinit
import numpy
import numpy.linalg as la
from pycuda.compiler import SourceModule

mod = SourceModule("""
__global__ void multiply_them(float *dest, float *a, float *b)
{
  const int i = threadIdx.x;
  dest[i] = a[i] * b[i];
}
""")

multiply_them = mod.get_function("multiply_them")

a = numpy.random.randn(400).astype(numpy.float32)
b = numpy.random.randn(400).astype(numpy.float32)

dest = numpy.zeros_like(a)
multiply_them(
        drv.Out(dest), drv.In(a), drv.In(b),
        block=(400,1,1))

print dest-a*b

########NEW FILE########
__FILENAME__ = autoinit
import pycuda.driver as cuda

# Initialize CUDA
cuda.init()

from pycuda.tools import make_default_context
global context
context = make_default_context()
device = context.get_device()

def _finish_up():
    global context
    context.pop()
    context = None

    from pycuda.tools import clear_context_caches
    clear_context_caches()

import atexit
atexit.register(_finish_up)

########NEW FILE########
__FILENAME__ = characterize
from __future__ import division

from pycuda.tools import context_dependent_memoize
import numpy as np


def platform_bits():
    return tuple.__itemsize__ * 8


def has_stack():
    from pycuda.driver import Context
    return Context.get_device().compute_capability() >= (2, 0)


def has_double_support():
    from pycuda.driver import Context
    return Context.get_device().compute_capability() >= (1, 3)


@context_dependent_memoize
def sizeof(type_name, preamble=""):
    from pycuda.compiler import SourceModule
    mod = SourceModule("""
    %s
    extern "C"
    __global__ void write_size(size_t *output)
    {
      *output = sizeof(%s);
    }
    """ % (preamble, type_name), no_extern_c=True)

    import pycuda.gpuarray as gpuarray
    output = gpuarray.empty((), dtype=np.uintp)
    mod.get_function("write_size")(output, block=(1, 1, 1), grid=(1, 1))

    return int(output.get())

########NEW FILE########
__FILENAME__ = compiler
from pytools import memoize
# don't import pycuda.driver here--you'll create an import loop
import sys
from tempfile import mkstemp
from os import unlink

from pytools.prefork import call_capture_output


@memoize
def get_nvcc_version(nvcc):
    cmdline = [nvcc, "--version"]
    result, stdout, stderr = call_capture_output(cmdline)

    if result != 0 or not stdout:
        from warnings import warn
        warn("NVCC version could not be determined.")
        stdout = "nvcc unknown version"

    return stdout.decode("utf-8", "replace")


def _new_md5():
    try:
        import hashlib
        return hashlib.md5()
    except ImportError:
        # for Python << 2.5
        import md5
        return md5.new()


def preprocess_source(source, options, nvcc):
    handle, source_path = mkstemp(suffix='.cu')

    outf = open(source_path, 'w')
    outf.write(source)
    outf.close()
    os.close(handle)

    cmdline = [nvcc, '--preprocess'] + options + [source_path]
    if 'win32' in sys.platform:
        cmdline.extend(['--compiler-options', '-EP'])
    else:
        cmdline.extend(['--compiler-options', '-P'])

    result, stdout, stderr = call_capture_output(cmdline, error_on_nonzero=False)

    if result != 0:
        from pycuda.driver import CompileError
        raise CompileError("nvcc preprocessing of %s failed" % source_path,
                           cmdline, stderr=stderr)

    # sanity check
    if len(stdout) < 0.5*len(source):
        from pycuda.driver import CompileError
        raise CompileError("nvcc preprocessing of %s failed with ridiculously "
                "small code output - likely unsupported compiler." % source_path,
                cmdline, stderr=stderr.decode("utf-8", "replace"))

    unlink(source_path)

    return stdout.decode("utf-8", "replace")


def compile_plain(source, options, keep, nvcc, cache_dir):
    from os.path import join

    if cache_dir:
        checksum = _new_md5()

        if '#include' in source:
            checksum.update(preprocess_source(source, options, nvcc).encode("utf-8"))
        else:
            checksum.update(source.encode("utf-8"))

        for option in options:
            checksum.update(option.encode("utf-8"))
        checksum.update(get_nvcc_version(nvcc).encode("utf-8"))
        from pycuda.characterize import platform_bits
        checksum.update(str(platform_bits()).encode("utf-8"))

        cache_file = checksum.hexdigest()
        cache_path = join(cache_dir, cache_file + ".cubin")

        try:
            cache_file = open(cache_path, "rb")
            try:
                return cache_file.read()
            finally:
                cache_file.close()

        except:
            pass

    from tempfile import mkdtemp
    file_dir = mkdtemp()
    file_root = "kernel"

    cu_file_name = file_root + ".cu"
    cu_file_path = join(file_dir, cu_file_name)

    outf = open(cu_file_path, "w")
    outf.write(str(source))
    outf.close()

    if keep:
        options = options[:]
        options.append("--keep")

        print "*** compiler output in %s" % file_dir

    cmdline = [nvcc, "--cubin"] + options + [cu_file_name]
    result, stdout, stderr = call_capture_output(cmdline,
            cwd=file_dir, error_on_nonzero=False)

    try:
        cubin_f = open(join(file_dir, file_root + ".cubin"), "rb")
    except IOError:
        no_output = True
    else:
        no_output = False

    if result != 0 or (no_output and (stdout or stderr)):
        if result == 0:
            from warnings import warn
            warn("PyCUDA: nvcc exited with status 0, but appears to have "
                    "encountered an error")
        from pycuda.driver import CompileError
        raise CompileError("nvcc compilation of %s failed" % cu_file_path,
                cmdline, stdout=stdout.decode("utf-8", "replace"),
                stderr=stderr.decode("utf-8", "replace"))

    if stdout or stderr:
        lcase_err_text = (stdout+stderr).decode("utf-8", "replace").lower()
        from warnings import warn
        if "demoted" in lcase_err_text or "demoting" in lcase_err_text:
            warn("nvcc said it demoted types in source code it "
                "compiled--this is likely not what you want.",
                stacklevel=4)
        warn("The CUDA compiler succeeded, but said the following:\n"
                + (stdout+stderr).decode("utf-8", "replace"), stacklevel=4)

    cubin = cubin_f.read()
    cubin_f.close()

    if cache_dir:
        outf = open(cache_path, "wb")
        outf.write(cubin)
        outf.close()

    if not keep:
        from os import listdir, unlink, rmdir
        for name in listdir(file_dir):
            unlink(join(file_dir, name))
        rmdir(file_dir)

    return cubin


def _get_per_user_string():
    try:
        from os import getuid
    except ImportError:
        checksum = _new_md5()
        from os import environ
        checksum.update(environ["USERNAME"].encode("utf-8"))
        return checksum.hexdigest()
    else:
        return "uid%d" % getuid()


def _find_pycuda_include_path():
    from pkg_resources import Requirement, resource_filename
    return resource_filename(Requirement.parse("pycuda"), "pycuda/cuda")


import os
DEFAULT_NVCC_FLAGS = [
        _flag.strip() for _flag in
        os.environ.get("PYCUDA_DEFAULT_NVCC_FLAGS", "").split()
        if _flag.strip()]


def compile(source, nvcc="nvcc", options=None, keep=False,
        no_extern_c=False, arch=None, code=None, cache_dir=None,
        include_dirs=[]):

    if not no_extern_c:
        source = 'extern "C" {\n%s\n}\n' % source

    if options is None:
        options = DEFAULT_NVCC_FLAGS

    options = options[:]
    if arch is None:
        try:
            from pycuda.driver import Context
            arch = "sm_%d%d" % Context.get_device().compute_capability()
        except RuntimeError:
            pass

    from pycuda.driver import CUDA_DEBUGGING
    if CUDA_DEBUGGING:
        cache_dir = False
        keep = True
        options.extend(["-g", "-G"])

    if cache_dir is None:
        from os.path import join
        from tempfile import gettempdir
        cache_dir = join(gettempdir(),
                "pycuda-compiler-cache-v1-%s" % _get_per_user_string())

        from os import mkdir
        try:
            mkdir(cache_dir)
        except OSError, e:
            from errno import EEXIST
            if e.errno != EEXIST:
                raise

    if arch is not None:
        options.extend(["-arch", arch])

    if code is not None:
        options.extend(["-code", code])

    if 'darwin' in sys.platform and sys.maxint == 9223372036854775807:
        options.append('-m64')
    elif 'win32' in sys.platform and sys.maxsize == 9223372036854775807:
        options.append('-m64')
    elif 'win32' in sys.platform and sys.maxsize == 2147483647:
        options.append('-m32')

    include_dirs = include_dirs + [_find_pycuda_include_path()]

    for i in include_dirs:
        options.append("-I"+i)

    return compile_plain(source, options, keep, nvcc, cache_dir)


class SourceModule(object):
    def __init__(self, source, nvcc="nvcc", options=None, keep=False,
            no_extern_c=False, arch=None, code=None, cache_dir=None,
            include_dirs=[]):
        self._check_arch(arch)

        cubin = compile(source, nvcc, options, keep, no_extern_c,
                arch, code, cache_dir, include_dirs)

        from pycuda.driver import module_from_buffer
        self.module = module_from_buffer(cubin)

        self.get_global = self.module.get_global
        self.get_texref = self.module.get_texref
        if hasattr(self.module, "get_surfref"):
            self.get_surfref = self.module.get_surfref

    def _check_arch(self, arch):
        if arch is None:
            return
        try:
            from pycuda.driver import Context
            capability = Context.get_device().compute_capability()
            if tuple(map(int, tuple(arch.split("_")[1]))) > capability:
                from warnings import warn
                warn("trying to compile for a compute capability "
                        "higher than selected GPU")
        except:
            pass

    def get_function(self, name):
        return self.module.get_function(name)

########NEW FILE########
__FILENAME__ = cumath
import pycuda.gpuarray as gpuarray
import pycuda.elementwise as elementwise
import numpy as np
import warnings
from pycuda.driver import Stream


def _make_unary_array_func(name):
    def f(array, stream_or_out=None, **kwargs):

        if stream_or_out is not None:
            warnings.warn("please use 'out' or 'stream' keyword arguments", DeprecationWarning)
            if isinstance(stream_or_out, Stream):
                stream = stream_or_out
                out = None
            else:
                stream = None
                out = stream_or_out

        out, stream = None, None
        if 'out' in kwargs:
            out = kwargs['out']
        if 'stream' in kwargs:
            stream = kwargs['stream']

        if array.dtype == np.float32:
            func_name = name + "f"
        else:
            func_name = name

        if not array.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        if out is None:
            out = array._new_like_me()
        else:
            assert out.dtype == array.dtype
            assert out.strides == array.strides
            assert out.shape == array.shape

        func = elementwise.get_unary_func_kernel(func_name, array.dtype)
        func.prepared_async_call(array._grid, array._block, stream,
                array.gpudata, out.gpudata, array.mem_size)

        return out
    return f

fabs = _make_unary_array_func("fabs")
ceil = _make_unary_array_func("ceil")
floor = _make_unary_array_func("floor")
exp = _make_unary_array_func("exp")
log = _make_unary_array_func("log")
log10 = _make_unary_array_func("log10")
sqrt = _make_unary_array_func("sqrt")

sin = _make_unary_array_func("sin")
cos = _make_unary_array_func("cos")
tan = _make_unary_array_func("tan")
asin = _make_unary_array_func("asin")
acos = _make_unary_array_func("acos")
atan = _make_unary_array_func("atan")

sinh = _make_unary_array_func("sinh")
cosh = _make_unary_array_func("cosh")
tanh = _make_unary_array_func("tanh")

def fmod(arg, mod, stream=None):
    """Return the floating point remainder of the division `arg/mod`,
    for each element in `arg` and `mod`."""
    result = gpuarray.GPUArray(arg.shape, arg.dtype)

    if not arg.flags.forc or not mod.flags.forc:
        raise RuntimeError("only contiguous arrays may "
                "be used as arguments to this operation")

    func = elementwise.get_fmod_kernel()
    func.prepared_async_call(arg._grid, arg._block, stream,
            arg.gpudata, mod.gpudata, result.gpudata, arg.mem_size)

    return result

def frexp(arg, stream=None):
    """Return a tuple `(significands, exponents)` such that
    `arg == significand * 2**exponent`.
    """
    if not arg.flags.forc:
        raise RuntimeError("only contiguous arrays may "
                "be used as arguments to this operation")

    sig = gpuarray.GPUArray(arg.shape, arg.dtype)
    expt = gpuarray.GPUArray(arg.shape, arg.dtype)

    func = elementwise.get_frexp_kernel()
    func.prepared_async_call(arg._grid, arg._block, stream,
            arg.gpudata, sig.gpudata, expt.gpudata, arg.mem_size)

    return sig, expt

def ldexp(significand, exponent, stream=None):
    """Return a new array of floating point values composed from the
    entries of `significand` and `exponent`, paired together as
    `result = significand * 2**exponent`.
    """
    if not significand.flags.forc or not exponent.flags.forc:
        raise RuntimeError("only contiguous arrays may "
                "be used as arguments to this operation")

    result = gpuarray.GPUArray(significand.shape, significand.dtype)

    func = elementwise.get_ldexp_kernel()
    func.prepared_async_call(significand._grid, significand._block, stream,
            significand.gpudata, exponent.gpudata, result.gpudata,
            significand.mem_size)

    return result

def modf(arg, stream=None):
    """Return a tuple `(fracpart, intpart)` of arrays containing the
    integer and fractional parts of `arg`.
    """
    if not arg.flags.forc:
        raise RuntimeError("only contiguous arrays may "
                "be used as arguments to this operation")

    intpart = gpuarray.GPUArray(arg.shape, arg.dtype)
    fracpart = gpuarray.GPUArray(arg.shape, arg.dtype)

    func = elementwise.get_modf_kernel()
    func.prepared_async_call(arg._grid, arg._block, stream,
            arg.gpudata, intpart.gpudata, fracpart.gpudata,
            arg.mem_size)

    return fracpart, intpart

########NEW FILE########
__FILENAME__ = curandom
from __future__ import division

import numpy as np
import pycuda.compiler
import pycuda.driver as drv
import pycuda.gpuarray as array
from pytools import memoize_method



# {{{ MD5-based random number generation

md5_code = """
/*
 **********************************************************************
 ** Copyright (C) 1990, RSA Data Security, Inc. All rights reserved. **
 **                                                                  **
 ** License to copy and use this software is granted provided that   **
 ** it is identified as the "RSA Data Security, Inc. MD5 Message     **
 ** Digest Algorithm" in all material mentioning or referencing this **
 ** software or this function.                                       **
 **                                                                  **
 ** License is also granted to make and use derivative works         **
 ** provided that such works are identified as "derived from the RSA **
 ** Data Security, Inc. MD5 Message Digest Algorithm" in all         **
 ** material mentioning or referencing the derived work.             **
 **                                                                  **
 ** RSA Data Security, Inc. makes no representations concerning      **
 ** either the merchantability of this software or the suitability   **
 ** of this software for any particular purpose.  It is provided "as **
 ** is" without express or implied warranty of any kind.             **
 **                                                                  **
 ** These notices must be retained in any copies of any part of this **
 ** documentation and/or software.                                   **
 **********************************************************************
 */

/* F, G and H are basic MD5 functions: selection, majority, parity */
#define F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define G(x, y, z) (((x) & (z)) | ((y) & (~z)))
#define H(x, y, z) ((x) ^ (y) ^ (z))
#define I(x, y, z) ((y) ^ ((x) | (~z)))

/* ROTATE_LEFT rotates x left n bits */
#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32-(n))))

/* FF, GG, HH, and II transformations for rounds 1, 2, 3, and 4 */
/* Rotation is separate from addition to prevent recomputation */
#define FF(a, b, c, d, x, s, ac) \
  {(a) += F ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }
#define GG(a, b, c, d, x, s, ac) \
  {(a) += G ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }
#define HH(a, b, c, d, x, s, ac) \
  {(a) += H ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }
#define II(a, b, c, d, x, s, ac) \
  {(a) += I ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }

#define X0 threadIdx.x
#define X1 threadIdx.y
#define X2 threadIdx.z
#define X3 blockIdx.x
#define X4 blockIdx.y
#define X5 blockIdx.z
#define X6 seed
#define X7 i
#define X8 n
#define X9  blockDim.x
#define X10 blockDim.y
#define X11 blockDim.z
#define X12 gridDim.x
#define X13 gridDim.y
#define X14 gridDim.z
#define X15 0

  unsigned int a = 0x67452301;
  unsigned int b = 0xefcdab89;
  unsigned int c = 0x98badcfe;
  unsigned int d = 0x10325476;

  /* Round 1 */
#define S11 7
#define S12 12
#define S13 17
#define S14 22
  FF ( a, b, c, d, X0 , S11, 3614090360); /* 1 */
  FF ( d, a, b, c, X1 , S12, 3905402710); /* 2 */
  FF ( c, d, a, b, X2 , S13,  606105819); /* 3 */
  FF ( b, c, d, a, X3 , S14, 3250441966); /* 4 */
  FF ( a, b, c, d, X4 , S11, 4118548399); /* 5 */
  FF ( d, a, b, c, X5 , S12, 1200080426); /* 6 */
  FF ( c, d, a, b, X6 , S13, 2821735955); /* 7 */
  FF ( b, c, d, a, X7 , S14, 4249261313); /* 8 */
  FF ( a, b, c, d, X8 , S11, 1770035416); /* 9 */
  FF ( d, a, b, c, X9 , S12, 2336552879); /* 10 */
  FF ( c, d, a, b, X10, S13, 4294925233); /* 11 */
  FF ( b, c, d, a, X11, S14, 2304563134); /* 12 */
  FF ( a, b, c, d, X12, S11, 1804603682); /* 13 */
  FF ( d, a, b, c, X13, S12, 4254626195); /* 14 */
  FF ( c, d, a, b, X14, S13, 2792965006); /* 15 */
  FF ( b, c, d, a, X15, S14, 1236535329); /* 16 */

  /* Round 2 */
#define S21 5
#define S22 9
#define S23 14
#define S24 20
  GG ( a, b, c, d, X1 , S21, 4129170786); /* 17 */
  GG ( d, a, b, c, X6 , S22, 3225465664); /* 18 */
  GG ( c, d, a, b, X11, S23,  643717713); /* 19 */
  GG ( b, c, d, a, X0 , S24, 3921069994); /* 20 */
  GG ( a, b, c, d, X5 , S21, 3593408605); /* 21 */
  GG ( d, a, b, c, X10, S22,   38016083); /* 22 */
  GG ( c, d, a, b, X15, S23, 3634488961); /* 23 */
  GG ( b, c, d, a, X4 , S24, 3889429448); /* 24 */
  GG ( a, b, c, d, X9 , S21,  568446438); /* 25 */
  GG ( d, a, b, c, X14, S22, 3275163606); /* 26 */
  GG ( c, d, a, b, X3 , S23, 4107603335); /* 27 */
  GG ( b, c, d, a, X8 , S24, 1163531501); /* 28 */
  GG ( a, b, c, d, X13, S21, 2850285829); /* 29 */
  GG ( d, a, b, c, X2 , S22, 4243563512); /* 30 */
  GG ( c, d, a, b, X7 , S23, 1735328473); /* 31 */
  GG ( b, c, d, a, X12, S24, 2368359562); /* 32 */

  /* Round 3 */
#define S31 4
#define S32 11
#define S33 16
#define S34 23
  HH ( a, b, c, d, X5 , S31, 4294588738); /* 33 */
  HH ( d, a, b, c, X8 , S32, 2272392833); /* 34 */
  HH ( c, d, a, b, X11, S33, 1839030562); /* 35 */
  HH ( b, c, d, a, X14, S34, 4259657740); /* 36 */
  HH ( a, b, c, d, X1 , S31, 2763975236); /* 37 */
  HH ( d, a, b, c, X4 , S32, 1272893353); /* 38 */
  HH ( c, d, a, b, X7 , S33, 4139469664); /* 39 */
  HH ( b, c, d, a, X10, S34, 3200236656); /* 40 */
  HH ( a, b, c, d, X13, S31,  681279174); /* 41 */
  HH ( d, a, b, c, X0 , S32, 3936430074); /* 42 */
  HH ( c, d, a, b, X3 , S33, 3572445317); /* 43 */
  HH ( b, c, d, a, X6 , S34,   76029189); /* 44 */
  HH ( a, b, c, d, X9 , S31, 3654602809); /* 45 */
  HH ( d, a, b, c, X12, S32, 3873151461); /* 46 */
  HH ( c, d, a, b, X15, S33,  530742520); /* 47 */
  HH ( b, c, d, a, X2 , S34, 3299628645); /* 48 */

  /* Round 4 */
#define S41 6
#define S42 10
#define S43 15
#define S44 21
  II ( a, b, c, d, X0 , S41, 4096336452); /* 49 */
  II ( d, a, b, c, X7 , S42, 1126891415); /* 50 */
  II ( c, d, a, b, X14, S43, 2878612391); /* 51 */
  II ( b, c, d, a, X5 , S44, 4237533241); /* 52 */
  II ( a, b, c, d, X12, S41, 1700485571); /* 53 */
  II ( d, a, b, c, X3 , S42, 2399980690); /* 54 */
  II ( c, d, a, b, X10, S43, 4293915773); /* 55 */
  II ( b, c, d, a, X1 , S44, 2240044497); /* 56 */
  II ( a, b, c, d, X8 , S41, 1873313359); /* 57 */
  II ( d, a, b, c, X15, S42, 4264355552); /* 58 */
  II ( c, d, a, b, X6 , S43, 2734768916); /* 59 */
  II ( b, c, d, a, X13, S44, 1309151649); /* 60 */
  II ( a, b, c, d, X4 , S41, 4149444226); /* 61 */
  II ( d, a, b, c, X11, S42, 3174756917); /* 62 */
  II ( c, d, a, b, X2 , S43,  718787259); /* 63 */
  II ( b, c, d, a, X9 , S44, 3951481745); /* 64 */

  a += 0x67452301;
  b += 0xefcdab89;
  c += 0x98badcfe;
  d += 0x10325476;
"""




def rand(shape, dtype=np.float32, stream=None):
    from pycuda.gpuarray import GPUArray
    from pycuda.elementwise import get_elwise_kernel

    result = GPUArray(shape, dtype)

    if dtype == np.float32:
        func = get_elwise_kernel(
            "float *dest, unsigned int seed",
            md5_code + """
            #define POW_2_M32 (1/4294967296.0f)
            dest[i] = a*POW_2_M32;
            if ((i += total_threads) < n)
                dest[i] = b*POW_2_M32;
            if ((i += total_threads) < n)
                dest[i] = c*POW_2_M32;
            if ((i += total_threads) < n)
                dest[i] = d*POW_2_M32;
            """,
            "md5_rng_float")
    elif dtype == np.float64:
        func = get_elwise_kernel(
            "double *dest, unsigned int seed",
            md5_code + """
            #define POW_2_M32 (1/4294967296.0)
            #define POW_2_M64 (1/18446744073709551616.)

            dest[i] = a*POW_2_M32 + b*POW_2_M64;

            if ((i += total_threads) < n)
            {
              dest[i] = c*POW_2_M32 + d*POW_2_M64;
            }
            """,
            "md5_rng_float")
    elif dtype in [np.int32, np.uint32]:
        func = get_elwise_kernel(
            "unsigned int *dest, unsigned int seed",
            md5_code + """
            dest[i] = a;
            if ((i += total_threads) < n)
                dest[i] = b;
            if ((i += total_threads) < n)
                dest[i] = c;
            if ((i += total_threads) < n)
                dest[i] = d;
            """,
            "md5_rng_int")
    else:
        raise NotImplementedError;

    func.prepared_async_call(result._grid, result._block, stream,
            result.gpudata, np.random.randint(2**31-1), result.size)

    return result

# }}}

# {{{ CURAND wrapper

try:
    import pycuda._driver as _curand # used to be separate module
except ImportError:
    def get_curand_version():
        return None
else:
    get_curand_version = _curand.get_curand_version

if get_curand_version() >= (3, 2, 0):
    direction_vector_set = _curand.direction_vector_set
    _get_direction_vectors = _curand._get_direction_vectors

if get_curand_version() >= (4, 0, 0):
    _get_scramble_constants32 = _curand._get_scramble_constants32
    _get_scramble_constants64 = _curand._get_scramble_constants64

# {{{ Base class

gen_template = """
__global__ void %(name)s(%(state_type)s *s, %(out_type)s *d, const int n)
{
  const int tidx = blockIdx.x*blockDim.x+threadIdx.x;
  const int delta = blockDim.x*gridDim.x;
  for (int idx = tidx; idx < n; idx += delta)
    d[idx] = curand%(suffix)s(&s[tidx]);
}
"""

gen_log_template = """
__global__ void %(name)s(%(state_type)s *s, %(out_type)s *d, %(in_type)s mean, %(in_type)s stddev, const int n)
{
  const int tidx = blockIdx.x*blockDim.x+threadIdx.x;
  const int delta = blockDim.x*gridDim.x;
  for (int idx = tidx; idx < n; idx += delta)
    d[idx] = curand_log%(suffix)s(&s[tidx], mean, stddev);
}
"""

gen_poisson_template = """
__global__ void %(name)s(%(state_type)s *s, %(out_type)s *d, double lambda, const int n)
{
  const int tidx = blockIdx.x*blockDim.x+threadIdx.x;
  const int delta = blockDim.x*gridDim.x;
  for (int idx = tidx; idx < n; idx += delta)
    d[idx] = curand_poisson%(suffix)s(&s[tidx], lambda);
}
"""

random_source = """
// Uses C++ features (templates); do not surround with extern C
#include <curand_kernel.h>

extern "C"
{

%(generators)s

}
"""

random_skip_ahead32_source = """
extern "C" {
__global__ void skip_ahead(%(state_type)s *s, const int n, const unsigned int skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead(skip, &s[idx]);
}

__global__ void skip_ahead_array(%(state_type)s *s, const int n, const unsigned int *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead(skip[idx], &s[idx]);
}
}
"""

random_skip_ahead64_source = """
extern "C" {
__global__ void skip_ahead(%(state_type)s *s, const int n, const unsigned long long skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead(skip, &s[idx]);
}

__global__ void skip_ahead_array(%(state_type)s *s, const int n, const unsigned long long *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead(skip[idx], &s[idx]);
}
}
"""

class _RandomNumberGeneratorBase(object):
    """
    Class surrounding CURAND kernels from CUDA 3.2.
    It allows for generating random numbers with uniform
    and normal probability function of various types.
    """

    gen_info = [
        ("uniform_int", "unsigned int", ""),
        ("uniform_long", "unsigned long long", ""),
        ("uniform_float", "float", "_uniform"),
        ("uniform_double", "double", "_uniform_double"),
        ("normal_float", "float", "_normal"),
        ("normal_double", "double", "_normal_double"),
        ("normal_float2", "float2", "_normal2"),
        ("normal_double2", "double2", "_normal2_double"),
        ]

    gen_log_info = [
        ("normal_log_float", "float", "float", "_normal"),
        ("normal_log_double", "double", "double", "_normal_double"),
        ("normal_log_float2", "float", "float2", "_normal2"),
        ("normal_log_double2", "double", "double2", "_normal2_double"),
        ]

    gen_poisson_info = [
        ("poisson_int", "unsigned int", ""),
        ]

    def __init__(self, state_type, vector_type, generator_bits,
        additional_source, scramble_type=None):
        if get_curand_version() < (3, 2, 0):
            raise EnvironmentError("Need at least CUDA 3.2")

        dev = drv.Context.get_device()

        self.block_count = dev.get_attribute(
            pycuda.driver.device_attribute.MULTIPROCESSOR_COUNT)

        from pycuda.characterize import has_double_support

        def do_generate(out_type):
            result = True
            if "double" in out_type:
                result = result and has_double_support()
            if "2" in out_type:
                result = result and self.has_box_muller
            return result

        my_generators = [
                (name, out_type, suffix)
                for name, out_type, suffix in self.gen_info
                if do_generate(out_type)]

        if get_curand_version() >= (4, 0, 0):
            my_log_generators = [
                    (name, in_type, out_type, suffix)
                    for name, in_type, out_type, suffix in self.gen_log_info
                    if do_generate(out_type)]

        if get_curand_version() >= (5, 0, 0):
            my_poisson_generators = [
                    (name, out_type, suffix)
                    for name, out_type, suffix in self.gen_poisson_info
                    if do_generate(out_type)]

        generator_sources = [
                gen_template % {
                    "name": name, "out_type": out_type, "suffix": suffix,
                    "state_type": state_type, }
                for name, out_type, suffix in my_generators]
        
        if get_curand_version() >= (4, 0, 0):
            generator_sources.extend([
                    gen_log_template % {
                        "name": name, "in_type": in_type, "out_type": out_type,
                        "suffix": suffix, "state_type": state_type, }
                    for name, in_type, out_type, suffix in my_log_generators])

        if get_curand_version() >= (5, 0, 0):
            generator_sources.extend([
                    gen_poisson_template % {
                        "name": name, "out_type": out_type, "suffix": suffix,
                        "state_type": state_type, }
                    for name, out_type, suffix in my_poisson_generators])

        source = (random_source + additional_source) % {
            "state_type": state_type,
            "vector_type": vector_type,
            "scramble_type": scramble_type,
            "generators": "\n".join(generator_sources)}

        # store in instance to let subclass constructors get to it.
        self.module = module = pycuda.compiler.SourceModule(source, no_extern_c=True)

        self.generators = {}
        for name, out_type, suffix  in my_generators:
            gen_func = module.get_function(name)
            gen_func.prepare("PPi")
            self.generators[name] = gen_func
        if get_curand_version() >= (4, 0, 0):
            for name, in_type, out_type, suffix  in my_log_generators:
                gen_func = module.get_function(name)
                if in_type == "float":
                    gen_func.prepare("PPffi")
                if in_type == "double":
                    gen_func.prepare("PPddi")
                self.generators[name] = gen_func
        if get_curand_version() >= (5, 0, 0):
            for name, out_type, suffix  in my_poisson_generators:
                gen_func = module.get_function(name)
                gen_func.prepare("PPdi")
                self.generators[name] = gen_func

        self.generator_bits = generator_bits
        self._prepare_skipahead()

        self.state_type = state_type
        self._state = None

    def _prepare_skipahead(self):
        self.skip_ahead = self.module.get_function("skip_ahead")
        if self.generator_bits == 32:
            self.skip_ahead.prepare("PiI")
        if self.generator_bits == 64:
            self.skip_ahead.prepare("PiQ")
        self.skip_ahead_array = self.module.get_function("skip_ahead_array")
        self.skip_ahead_array.prepare("PiP")

    def _kernels(self):
        return (
                list(self.generators.itervalues())
                + [self.skip_ahead, self.skip_ahead_array])

    @property
    @memoize_method
    def generators_per_block(self):
        return min(kernel.max_threads_per_block
                for kernel in self._kernels())

    @property
    def state(self):
        if self._state is None:
            from pycuda.characterize import sizeof
            data_type_size = sizeof(self.state_type, "#include <curand_kernel.h>")

            self._state = drv.mem_alloc(
                self.block_count * self.generators_per_block * data_type_size)

        return self._state

    def fill_uniform(self, data, stream=None):
        if data.dtype == np.float32:
            func = self.generators["uniform_float"]
        elif data.dtype == np.float64:
            func = self.generators["uniform_double"]
        elif data.dtype in [np.int, np.int32, np.uint32]:
            func = self.generators["uniform_int"]
        elif data.dtype in [np.int64, np.uint64] and self.generator_bits >= 64:
            func = self.generators["uniform_long"]
        else:
            raise NotImplementedError

        func.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, data.gpudata, data.size)

    def fill_normal(self, data, stream=None):
        if data.dtype == np.float32:
            func_name = "normal_float"
        elif data.dtype == np.float64:
            func_name = "normal_double"
        else:
            raise NotImplementedError

        data_size = data.size
        if self.has_box_muller and data_size % 2 == 0:
            func_name += "2"
            data_size //= 2

        func = self.generators[func_name]

        func.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, data.gpudata, int(data_size))

    def gen_uniform(self, shape, dtype, stream=None):
        result = array.empty(shape, dtype)
        self.fill_uniform(result, stream)
        return result

    def gen_normal(self, shape, dtype, stream=None):
        result = array.empty(shape, dtype)
        self.fill_normal(result, stream)
        return result

    if get_curand_version() >= (4, 0, 0):
        def fill_log_normal(self, data, mean, stddev, stream=None):
            if data.dtype == np.float32:
                func_name = "normal_log_float"
            elif data.dtype == np.float64:
                func_name = "normal_log_double"
            else:
                raise NotImplementedError

            data_size = data.size
            if self.has_box_muller and data_size % 2 == 0:
                func_name += "2"
                data_size //= 2

            func = self.generators[func_name]

            func.prepared_async_call(
                    (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                    self.state, data.gpudata, mean, stddev, int(data_size))

        def gen_log_normal(self, shape, dtype, mean, stddev, stream=None):
            result = array.empty(shape, dtype)
            self.fill_log_normal(result, mean, stddev, stream)
            return result

    if get_curand_version() >= (5, 0, 0):
        def fill_poisson(self, data, lambda_value, stream=None):
            if data.dtype == np.uint32:
                func_name = "poisson_int"
            else:
                raise NotImplementedError

            func = self.generators[func_name]

            func.prepared_async_call(
                    (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                    self.state, data.gpudata, lambda_value, data.size)

        def gen_poisson(self, shape, dtype, lambda_value, stream=None):
            result = array.empty(shape, dtype)
            self.fill_poisson(result, lambda_value, stream)
            return result

    def call_skip_ahead(self, i, stream=None):
        self.skip_ahead.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, self.generators_per_block, i)

    def call_skip_ahead_array(self, i, stream=None):
        self.skip_ahead_array.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, self.generators_per_block, i.gpudata)

# }}}

# {{{ XORWOW RNG

class _PseudoRandomNumberGeneratorBase(_RandomNumberGeneratorBase):
    def __init__(self, seed_getter, offset, state_type, vector_type,
        generator_bits, additional_source, scramble_type=None):

        super(_PseudoRandomNumberGeneratorBase, self).__init__(
            state_type, vector_type, generator_bits, additional_source)

        generator_count = self.generators_per_block * self.block_count
        if seed_getter is None:
            seed = array.to_gpu(
                    np.asarray(
                        np.random.random_integers(
                            0, (1 << 31) - 2, generator_count),
                        dtype=np.int32))
        else:
            seed = seed_getter(generator_count)

        if not (isinstance(seed, pycuda.gpuarray.GPUArray)
                and seed.dtype == np.int32
                and seed.size == generator_count):
            raise TypeError("seed must be GPUArray of integers of right length")

        p = self.module.get_function("prepare")
        p.prepare("PiPi")

        from pycuda.characterize import has_stack
        has_stack = has_stack()

        if has_stack:
            prev_stack_size = drv.Context.get_limit(drv.limit.STACK_SIZE)

        try:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, 1<<14) # 16k
            try:
                p.prepared_call(
                        (self.block_count, 1), (self.generators_per_block, 1, 1), self.state,
                        generator_count, seed.gpudata, offset)
            except drv.LaunchError:
                raise ValueError("Initialisation failed. Decrease number of threads.")

        finally:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, prev_stack_size)

    def _prepare_skipahead(self):
        self.skip_ahead = self.module.get_function("skip_ahead")
        self.skip_ahead.prepare("PiQ")
        self.skip_ahead_array = self.module.get_function("skip_ahead_array")
        self.skip_ahead_array.prepare("PiP")
        self.skip_ahead_sequence = self.module.get_function("skip_ahead_sequence")
        self.skip_ahead_sequence.prepare("PiQ")
        self.skip_ahead_sequence_array = self.module.get_function("skip_ahead_sequence_array")
        self.skip_ahead_sequence_array.prepare("PiP")

    def call_skip_ahead_sequence(self, i, stream=None):
        self.skip_ahead_sequence.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, self.generators_per_block * self.block_count, i)

    def call_skip_ahead_sequence_array(self, i, stream=None):
        self.skip_ahead_sequence_array.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, self.generators_per_block * self.block_count, i.gpudata)

    def _kernels(self):
        return (_RandomNumberGeneratorBase._kernels(self)
                + [self.module.get_function("prepare")]
                + [self.module.get_function("skip_ahead_sequence"),
                   self.module.get_function("skip_ahead_sequence_array")])


def seed_getter_uniform(N):
    result = pycuda.gpuarray.empty([N], np.int32)
    import random
    value = random.randint(0, 2**31-1)
    return result.fill(value)

def seed_getter_unique(N):
    result = np.random.randint(0, 2**31-1, N).astype(np.int32)
    return pycuda.gpuarray.to_gpu(result)

xorwow_random_source = """
extern "C" {
__global__ void prepare(%(state_type)s *s, const int n,
    %(vector_type)s *v, const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], id, o, &s[id]);
}
}
"""

xorwow_skip_ahead_sequence_source = """
extern "C" {
__global__ void skip_ahead_sequence(%(state_type)s *s, const int n, const unsigned long long skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead_sequence(skip, &s[idx]);
}

__global__ void skip_ahead_sequence_array(%(state_type)s *s, const int n, const unsigned long long *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead_sequence(skip[idx], &s[idx]);
}
}
"""

if get_curand_version() >= (3, 2, 0):
    class XORWOWRandomNumberGenerator(_PseudoRandomNumberGeneratorBase):
        has_box_muller = True

        def __init__(self, seed_getter=None, offset=0):
            """
            :arg seed_getter: a function that, given an integer count, will yield an `int32`
              :class:`GPUArray` of seeds.
            """

            super(XORWOWRandomNumberGenerator, self).__init__(
                seed_getter, offset,
                'curandStateXORWOW', 'unsigned int', 32, xorwow_random_source+
                xorwow_skip_ahead_sequence_source+random_skip_ahead64_source)

# }}}

# {{{ MRG32k3a RNG

mrg32k3a_random_source = """
extern "C" {
__global__ void prepare(%(state_type)s *s, const int n,
    %(vector_type)s *v, const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], id, o, &s[id]);
}
}
"""

mrg32k3a_skip_ahead_sequence_source = """
extern "C" {
__global__ void skip_ahead_sequence(%(state_type)s *s, const int n, const unsigned long long skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead_sequence(skip, &s[idx]);
}

__global__ void skip_ahead_sequence_array(%(state_type)s *s, const int n, const unsigned long long *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead_sequence(skip[idx], &s[idx]);
}

__global__ void skip_ahead_subsequence(%(state_type)s *s, const int n, const unsigned long long skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead_subsequence(skip, &s[idx]);
}

__global__ void skip_ahead_subsequence_array(%(state_type)s *s, const int n, const unsigned long long *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead_subsequence(skip[idx], &s[idx]);
}
}
"""

if get_curand_version() >= (4, 1, 0):
    class MRG32k3aRandomNumberGenerator(_PseudoRandomNumberGeneratorBase):
        has_box_muller = True

        def __init__(self, seed_getter=None, offset=0):
            """
            :arg seed_getter: a function that, given an integer count, will yield an `int32`
              :class:`GPUArray` of seeds.
            """

            super(MRG32k3aRandomNumberGenerator, self).__init__(
                seed_getter, offset,
                'curandStateMRG32k3a', 'unsigned int', 32, mrg32k3a_random_source+
                mrg32k3a_skip_ahead_sequence_source+random_skip_ahead64_source)

        def _prepare_skipahead(self):
            super(MRG32k3aRandomNumberGenerator, self)._prepare_skipahead()
            self.skip_ahead_subsequence = self.module.get_function("skip_ahead_subsequence")
            self.skip_ahead_subsequence.prepare("PiQ")
            self.skip_ahead_subsequence_array = self.module.get_function("skip_ahead_subsequence_array")
            self.skip_ahead_subsequence_array.prepare("PiP")

        def call_skip_ahead_subsequence(self, i, stream=None):
            self.skip_ahead_subsequence.prepared_async_call(
                    (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                    self.state, self.generators_per_block * self.block_count, i)

        def call_skip_ahead_subsequence_array(self, i, stream=None):
            self.skip_ahead_subsequence_array.prepared_async_call(
                    (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                    self.state, self.generators_per_block * self.block_count, i.gpudata)

        def _kernels(self):
            return (_PseudoRandomNumberGeneratorBase._kernels(self)
                    + [self.module.get_function("skip_ahead_subsequence"),
                       self.module.get_function("skip_ahead_subsequence_array")])

# }}}

# {{{ Sobol RNG

def generate_direction_vectors(count, direction=None):
    if get_curand_version() >= (4, 0, 0):
        if direction == direction_vector_set.VECTOR_64 or \
            direction == direction_vector_set.SCRAMBLED_VECTOR_64:
            result = np.empty((count, 64), dtype=np.uint64)
        else:
            result = np.empty((count, 32), dtype=np.uint32)
    else:
        result = np.empty((count, 32), dtype=np.uint32)
    _get_direction_vectors(direction, result, count)
    return pycuda.gpuarray.to_gpu(result)

if get_curand_version() >= (4, 0, 0):
    def generate_scramble_constants32(count):
        result = np.empty((count, ), dtype=np.uint32)
        _get_scramble_constants32(result, count)
        return pycuda.gpuarray.to_gpu(result)

    def generate_scramble_constants64(count):
        result = np.empty((count, ), dtype=np.uint64)
        _get_scramble_constants64(result, count)
        return pycuda.gpuarray.to_gpu(result)

sobol_random_source = """
extern "C" {
__global__ void prepare(%(state_type)s *s, const int n,
    %(vector_type)s *v, const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], o, &s[id]);
}
}
"""

class _SobolRandomNumberGeneratorBase(_RandomNumberGeneratorBase):
    """
    Class surrounding CURAND kernels from CUDA 3.2.
    It allows for generating quasi-random numbers with uniform
    and normal probability function of type int, float, and double.
    """

    has_box_muller = False

    def __init__(self, dir_vector, dir_vector_dtype, dir_vector_size,
        dir_vector_set, offset, state_type, vector_type, generator_bits,
        sobol_random_source):
        super(_SobolRandomNumberGeneratorBase, self).__init__(state_type,
            vector_type, generator_bits, sobol_random_source)

        if dir_vector is None:
            dir_vector = generate_direction_vectors(
                self.block_count * self.generators_per_block, dir_vector_set)

        if not (isinstance(dir_vector, pycuda.gpuarray.GPUArray)
                and dir_vector.dtype == dir_vector_dtype
                and dir_vector.shape == (self.block_count * self.generators_per_block, dir_vector_size)):
            raise TypeError("seed must be GPUArray of integers of right length")

        p = self.module.get_function("prepare")
        p.prepare("PiPi")

        from pycuda.characterize import has_stack
        has_stack = has_stack()

        if has_stack:
            prev_stack_size = drv.Context.get_limit(drv.limit.STACK_SIZE)

        try:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, 1<<14) # 16k
            try:
                p.prepared_call((self.block_count, 1), (self.generators_per_block, 1, 1),
                    self.state, self.block_count * self.generators_per_block,
                    dir_vector.gpudata, offset)
            except drv.LaunchError:
                raise ValueError("Initialisation failed. Decrease number of threads.")

        finally:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, prev_stack_size)

    def _kernels(self):
        return (_RandomNumberGeneratorBase._kernels(self)
                + [self.module.get_function("prepare")])

scrambledsobol_random_source = """
extern "C" {
__global__ void prepare( %(state_type)s *s, const int n,
    %(vector_type)s *v, %(scramble_type)s *scramble, const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], scramble[id], o, &s[id]);
}
}
"""

class _ScrambledSobolRandomNumberGeneratorBase(_RandomNumberGeneratorBase):
    """
    Class surrounding CURAND kernels from CUDA 4.0.
    It allows for generating quasi-random numbers with uniform
    and normal probability function of type int, float, and double.
    """

    has_box_muller = False

    def __init__(self, dir_vector, dir_vector_dtype, dir_vector_size,
        dir_vector_set, scramble_vector, scramble_vector_function,
        offset, state_type, vector_type, generator_bits, scramble_type,
	sobol_random_source):
        super(_ScrambledSobolRandomNumberGeneratorBase, self).__init__(state_type,
            vector_type, generator_bits, sobol_random_source, scramble_type)

        if dir_vector is None:
            dir_vector = generate_direction_vectors(
                self.block_count * self.generators_per_block,
                dir_vector_set)

        if scramble_vector is None:
            scramble_vector = scramble_vector_function(
                self.block_count * self.generators_per_block)

        if not (isinstance(dir_vector, pycuda.gpuarray.GPUArray)
                and dir_vector.dtype == dir_vector_dtype
                and dir_vector.shape == (self.block_count * self.generators_per_block, dir_vector_size)):
            raise TypeError("seed must be GPUArray of integers of right length")

        if not (isinstance(scramble_vector, pycuda.gpuarray.GPUArray)
                and scramble_vector.dtype == dir_vector_dtype
                and scramble_vector.shape == (self.block_count * self.generators_per_block, )):
            raise TypeError("scramble must be GPUArray of integers of right length")

        p = self.module.get_function("prepare")
        p.prepare("PiPPi")

        from pycuda.characterize import has_stack
        has_stack = has_stack()

        if has_stack:
            prev_stack_size = drv.Context.get_limit(drv.limit.STACK_SIZE)

        try:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, 1<<14) # 16k
            try:
                p.prepared_call((self.block_count, 1), (self.generators_per_block, 1, 1),
                    self.state, self.block_count * self.generators_per_block,
                    dir_vector.gpudata, scramble_vector.gpudata, offset)
            except drv.LaunchError:
                raise ValueError("Initialisation failed. Decrease number of threads.")

        finally:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, prev_stack_size)

    def _kernels(self):
        return (_RandomNumberGeneratorBase._kernels(self)
                + [self.module.get_function("prepare")])

if get_curand_version() >= (3, 2, 0):
    class Sobol32RandomNumberGenerator(_SobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 3.2.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, offset=0):
            super(Sobol32RandomNumberGenerator, self).__init__(dir_vector,
                np.uint32, 32, direction_vector_set.VECTOR_32, offset,
                'curandStateSobol32', 'curandDirectionVectors32_t', 32,
                sobol_random_source+random_skip_ahead32_source)


if get_curand_version() >= (4, 0, 0):
    class ScrambledSobol32RandomNumberGenerator(_ScrambledSobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 4.0.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, scramble_vector=None, offset=0):
            super(ScrambledSobol32RandomNumberGenerator, self).__init__(dir_vector,
                np.uint32, 32, direction_vector_set.SCRAMBLED_VECTOR_32,
                scramble_vector, generate_scramble_constants32, offset,
                'curandStateScrambledSobol32', 'curandDirectionVectors32_t',
                32, 'unsigned int',
                scrambledsobol_random_source+random_skip_ahead32_source)

if get_curand_version() >= (4, 0, 0):
    class Sobol64RandomNumberGenerator(_SobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 4.0.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, offset=0):
            super(Sobol64RandomNumberGenerator, self).__init__(dir_vector,
                np.uint64, 64, direction_vector_set.VECTOR_64, offset,
                'curandStateSobol64', 'curandDirectionVectors64_t', 64,
                 sobol_random_source+random_skip_ahead64_source)

if get_curand_version() >= (4, 0, 0):
    class ScrambledSobol64RandomNumberGenerator(_ScrambledSobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 4.0.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, scramble_vector=None, offset=0):
            super(ScrambledSobol64RandomNumberGenerator, self).__init__(dir_vector,
                np.uint64, 64, direction_vector_set.SCRAMBLED_VECTOR_64,
                scramble_vector, generate_scramble_constants64, offset,
                'curandStateScrambledSobol64', 'curandDirectionVectors64_t',
                64, 'unsigned long long',
                scrambledsobol_random_source+random_skip_ahead64_source)

# }}}

# }}}





# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = debug
import pycuda.driver
pycuda.driver.set_debugging()

import sys

from optparse import OptionParser
parser = OptionParser(
        usage="usage: %prog [options] SCRIPT-TO-RUN [SCRIPT-ARGUMENTS]")

parser.disable_interspersed_args()
options, args = parser.parse_args()

if len(args) < 1:
    parser.print_help()
    sys.exit(2)

mainpyfile =  args[0]
from os.path import exists
if not exists(mainpyfile):
    print 'Error:', mainpyfile, 'does not exist'
    sys.exit(1)

sys.argv = args

execfile(mainpyfile)

########NEW FILE########
__FILENAME__ = driver
try:
    from pycuda._driver import *  # noqa
except ImportError, e:
    if "_v2" in str(e):
        from warnings import warn
        warn("Failed to import the CUDA driver interface, with an error "
                "message indicating that the version of your CUDA header "
                "does not match the version of your CUDA driver.")
    raise

import numpy as np
import sys


if sys.version_info >= (3,):
    _memoryview = memoryview
    _my_bytes = bytes
else:
    _memoryview = buffer
    _my_bytes = str


try:
    ManagedAllocationOrStub = ManagedAllocation
except NameError:
    # Provide ManagedAllocationOrStub if not on CUDA 6.
    # This avoids having to do a version check in a high-traffic code path below.

    class ManagedAllocationOrStub(object):
        pass


CUDA_DEBUGGING = False


def set_debugging(flag=True):
    global CUDA_DEBUGGING
    CUDA_DEBUGGING = flag


class CompileError(Error):
    def __init__(self, msg, command_line, stdout=None, stderr=None):
        self.msg = msg
        self.command_line = command_line
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        result = self.msg
        if self.command_line:
            try:
                result += "\n[command: %s]" % (" ".join(self.command_line))
            except Exception, e:
                print e
        if self.stdout:
            result += "\n[stdout:\n%s]" % self.stdout
        if self.stderr:
            result += "\n[stderr:\n%s]" % self.stderr

        return result


class ArgumentHandler(object):
    def __init__(self, ary):
        self.array = ary
        self.dev_alloc = None

    def get_device_alloc(self):
        if self.dev_alloc is None:
            self.dev_alloc = mem_alloc_like(self.array)
        return self.dev_alloc

    def pre_call(self, stream):
        pass


class In(ArgumentHandler):
    def pre_call(self, stream):
        if stream is not None:
            memcpy_htod(self.get_device_alloc(), self.array)
        else:
            memcpy_htod(self.get_device_alloc(), self.array)


class Out(ArgumentHandler):
    def post_call(self, stream):
        if stream is not None:
            memcpy_dtoh(self.array, self.get_device_alloc())
        else:
            memcpy_dtoh(self.array, self.get_device_alloc())


class InOut(In, Out):
    pass


def _add_functionality():

    def device_get_attributes(dev):
        result = {}

        for att_name in dir(device_attribute):
            if not att_name[0].isupper():
                continue

            att_id = getattr(device_attribute, att_name)

            try:
                att_value = dev.get_attribute(att_id)
            except LogicError, e:
                from warnings import warn
                warn("CUDA driver raised '%s' when querying '%s' on '%s'"
                        % (e, att_name, dev))
            else:
                result[att_id] = att_value

        return result

    def device___getattr__(dev, name):
        return dev.get_attribute(getattr(device_attribute, name.upper()))

    def _build_arg_buf(args):
        handlers = []

        arg_data = []
        format = ""
        for i, arg in enumerate(args):
            if isinstance(arg, np.number):
                arg_data.append(arg)
                format += arg.dtype.char
            elif isinstance(arg, (DeviceAllocation, PooledDeviceAllocation)):
                arg_data.append(int(arg))
                format += "P"
            elif isinstance(arg, ArgumentHandler):
                handlers.append(arg)
                arg_data.append(int(arg.get_device_alloc()))
                format += "P"
            elif isinstance(arg, np.ndarray):
                if isinstance(arg.base, ManagedAllocationOrStub):
                    arg_data.append(int(arg.base))
                    format += "P"
                else:
                    arg_data.append(arg)
                    format += "%ds" % arg.nbytes
            elif isinstance(arg, np.void):
                arg_data.append(_my_bytes(_memoryview(arg)))
                format += "%ds" % arg.itemsize
            else:
                try:
                    gpudata = np.intp(arg.gpudata)
                except AttributeError:
                    raise TypeError("invalid type on parameter #%d (0-based)" % i)
                else:
                    # for gpuarrays
                    arg_data.append(int(gpudata))
                    format += "P"

        from pycuda._pvt_struct import pack
        return handlers, pack(format, *arg_data)

    # {{{ pre-CUDA 4 call interface (stateful)

    def function_param_set_pre_v4(func, *args):
        handlers = []

        handlers, buf = _build_arg_buf(args)

        func._param_setv(0, buf)
        func._param_set_size(len(buf))

        return handlers

    def function_call_pre_v4(func, *args, **kwargs):
        grid = kwargs.pop("grid", (1, 1))
        stream = kwargs.pop("stream", None)
        block = kwargs.pop("block", None)
        shared = kwargs.pop("shared", None)
        texrefs = kwargs.pop("texrefs", [])
        time_kernel = kwargs.pop("time_kernel", False)

        if kwargs:
            raise ValueError(
                    "extra keyword arguments: %s"
                    % (",".join(kwargs.iterkeys())))

        if block is None:
            raise ValueError("must specify block size")

        func._set_block_shape(*block)
        handlers = func._param_set(*args)
        if shared is not None:
            func._set_shared_size(shared)

        for handler in handlers:
            handler.pre_call(stream)

        for texref in texrefs:
            func.param_set_texref(texref)

        post_handlers = [handler
                for handler in handlers
                if hasattr(handler, "post_call")]

        if stream is None:
            if time_kernel:
                Context.synchronize()

                from time import time
                start_time = time()
            func._launch_grid(*grid)
            if post_handlers or time_kernel:
                Context.synchronize()

                if time_kernel:
                    run_time = time()-start_time

                for handler in post_handlers:
                    handler.post_call(stream)

                if time_kernel:
                    return run_time
        else:
            assert not time_kernel, \
                    "Can't time the kernel on an asynchronous invocation"
            func._launch_grid_async(grid[0], grid[1], stream)

            if post_handlers:
                for handler in post_handlers:
                    handler.post_call(stream)

    def function_prepare_pre_v4(func, arg_types, block=None,
            shared=None, texrefs=[]):
        from warnings import warn
        if block is not None:
            warn("setting the block size in Function.prepare is deprecated",
                    DeprecationWarning, stacklevel=2)
            func._set_block_shape(*block)

        if shared is not None:
            warn("setting the shared memory size in Function.prepare is deprecated",
                    DeprecationWarning, stacklevel=2)
            func._set_shared_size(shared)

        func.texrefs = texrefs

        func.arg_format = ""

        for i, arg_type in enumerate(arg_types):
            if (isinstance(arg_type, type)
                    and np is not None and np.number in arg_type.__mro__):
                func.arg_format += np.dtype(arg_type).char
            elif isinstance(arg_type, str):
                func.arg_format += arg_type
            else:
                func.arg_format += np.dtype(np.intp).char

        from pycuda._pvt_struct import calcsize
        func._param_set_size(calcsize(func.arg_format))

        return func

    def function_prepared_call_pre_v4(func, grid, block, *args, **kwargs):
        if isinstance(block, tuple):
            func._set_block_shape(*block)
        else:
            from warnings import warn
            warn("Not passing the block size to prepared_call is deprecated as of "
                    "version 2011.1.", DeprecationWarning, stacklevel=2)
            args = (block,) + args

        shared_size = kwargs.pop("shared_size", None)
        if shared_size is not None:
            func._set_shared_size(shared_size)

        if kwargs:
            raise TypeError("unknown keyword arguments: "
                    + ", ".join(kwargs.iterkeys()))

        from pycuda._pvt_struct import pack
        func._param_setv(0, pack(func.arg_format, *args))

        for texref in func.texrefs:
            func.param_set_texref(texref)

        func._launch_grid(*grid)

    def function_prepared_timed_call_pre_v4(func, grid, block, *args, **kwargs):
        if isinstance(block, tuple):
            func._set_block_shape(*block)
        else:
            from warnings import warn
            warn("Not passing the block size to prepared_timed_call is "
                    "deprecated as of version 2011.1.",
                    DeprecationWarning, stacklevel=2)
            args = (block,) + args

        shared_size = kwargs.pop("shared_size", None)
        if shared_size is not None:
            func._set_shared_size(shared_size)

        if kwargs:
            raise TypeError("unknown keyword arguments: "
                    + ", ".join(kwargs.iterkeys()))

        from pycuda._pvt_struct import pack
        func._param_setv(0, pack(func.arg_format, *args))

        for texref in func.texrefs:
            func.param_set_texref(texref)

        start = Event()
        end = Event()

        start.record()
        func._launch_grid(*grid)
        end.record()

        def get_call_time():
            end.synchronize()
            return end.time_since(start)*1e-3

        return get_call_time

    def function_prepared_async_call_pre_v4(func, grid, block, stream,
            *args, **kwargs):
        if isinstance(block, tuple):
            func._set_block_shape(*block)
        else:
            from warnings import warn
            warn("Not passing the block size to prepared_async_call is "
                    "deprecated as of version 2011.1.",
                    DeprecationWarning, stacklevel=2)
            args = (stream,) + args
            stream = block

        shared_size = kwargs.pop("shared_size", None)
        if shared_size is not None:
            func._set_shared_size(shared_size)

        if kwargs:
            raise TypeError("unknown keyword arguments: "
                    + ", ".join(kwargs.iterkeys()))

        from pycuda._pvt_struct import pack
        func._param_setv(0, pack(func.arg_format, *args))

        for texref in func.texrefs:
            func.param_set_texref(texref)

        if stream is None:
            func._launch_grid(*grid)
        else:
            grid_x, grid_y = grid
            func._launch_grid_async(grid_x, grid_y, stream)

    # }}}

    # {{{ CUDA 4+ call interface (stateless)

    def function_call(func, *args, **kwargs):
        grid = kwargs.pop("grid", (1, 1))
        stream = kwargs.pop("stream", None)
        block = kwargs.pop("block", None)
        shared = kwargs.pop("shared", 0)
        texrefs = kwargs.pop("texrefs", [])
        time_kernel = kwargs.pop("time_kernel", False)

        if kwargs:
            raise ValueError(
                    "extra keyword arguments: %s"
                    % (",".join(kwargs.iterkeys())))

        if block is None:
            raise ValueError("must specify block size")

        func._set_block_shape(*block)
        handlers, arg_buf = _build_arg_buf(args)

        for handler in handlers:
            handler.pre_call(stream)

        for texref in texrefs:
            func.param_set_texref(texref)

        post_handlers = [handler
                for handler in handlers
                if hasattr(handler, "post_call")]

        if stream is None:
            if time_kernel:
                Context.synchronize()

                from time import time
                start_time = time()

            func._launch_kernel(grid, block, arg_buf, shared, None)

            if post_handlers or time_kernel:
                Context.synchronize()

                if time_kernel:
                    run_time = time()-start_time

                for handler in post_handlers:
                    handler.post_call(stream)

                if time_kernel:
                    return run_time
        else:
            assert not time_kernel, \
                    "Can't time the kernel on an asynchronous invocation"
            func._launch_kernel(grid, block, arg_buf, shared, stream)

            if post_handlers:
                for handler in post_handlers:
                    handler.post_call(stream)

    def function_prepare(func, arg_types, texrefs=[]):
        func.texrefs = texrefs

        func.arg_format = ""

        for i, arg_type in enumerate(arg_types):
            if (isinstance(arg_type, type)
                    and np.number in arg_type.__mro__):
                func.arg_format += np.dtype(arg_type).char
            elif isinstance(arg_type, np.dtype):
                if arg_type.char == "V":
                    func.arg_format += "%ds" % arg_type.itemsize
                else:
                    func.arg_format += arg_type.char
            elif isinstance(arg_type, str):
                func.arg_format += arg_type
            else:
                func.arg_format += np.dtype(np.intp).char

        return func

    def function_prepared_call(func, grid, block, *args, **kwargs):
        if isinstance(block, tuple):
            func._set_block_shape(*block)
        else:
            from warnings import warn
            warn("Not passing the block size to prepared_call is deprecated as of "
                    "version 2011.1.", DeprecationWarning, stacklevel=2)
            args = (block,) + args

        shared_size = kwargs.pop("shared_size", 0)

        if kwargs:
            raise TypeError("unknown keyword arguments: "
                    + ", ".join(kwargs.iterkeys()))

        from pycuda._pvt_struct import pack
        arg_buf = pack(func.arg_format, *args)

        for texref in func.texrefs:
            func.param_set_texref(texref)

        func._launch_kernel(grid, block, arg_buf, shared_size, None)

    def function_prepared_timed_call(func, grid, block, *args, **kwargs):
        shared_size = kwargs.pop("shared_size", 0)
        if kwargs:
            raise TypeError("unknown keyword arguments: "
                    + ", ".join(kwargs.iterkeys()))

        from pycuda._pvt_struct import pack
        arg_buf = pack(func.arg_format, *args)

        for texref in func.texrefs:
            func.param_set_texref(texref)

        start = Event()
        end = Event()

        start.record()
        func._launch_kernel(grid, block, arg_buf, shared_size, None)
        end.record()

        def get_call_time():
            end.synchronize()
            return end.time_since(start)*1e-3

        return get_call_time

    def function_prepared_async_call(func, grid, block, stream, *args, **kwargs):
        if isinstance(block, tuple):
            func._set_block_shape(*block)
        else:
            from warnings import warn
            warn("Not passing the block size to prepared_async_call is "
                    "deprecated as of version 2011.1.",
                    DeprecationWarning, stacklevel=2)
            args = (stream,) + args
            stream = block

        shared_size = kwargs.pop("shared_size", 0)

        if kwargs:
            raise TypeError("unknown keyword arguments: "
                    + ", ".join(kwargs.iterkeys()))

        from pycuda._pvt_struct import pack
        arg_buf = pack(func.arg_format, *args)

        for texref in func.texrefs:
            func.param_set_texref(texref)

        func._launch_kernel(grid, block, arg_buf, shared_size, stream)

    # }}}

    def function___getattr__(self, name):
        if get_version() >= (2, 2):
            return self.get_attribute(getattr(function_attribute, name.upper()))
        else:
            if name == "num_regs":
                return self._hacky_registers
            elif name == "shared_size_bytes":
                return self._hacky_smem
            elif name == "local_size_bytes":
                return self._hacky_lmem
            else:
                raise AttributeError("no attribute '%s' in Function" % name)

    def mark_func_method_deprecated(func):
        def new_func(*args, **kwargs):
            from warnings import warn
            warn("'%s' has been deprecated in version 2011.1. Please use "
                    "the stateless launch interface instead." % func.__name__[1:],
                    DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        try:
            from functools import update_wrapper
        except ImportError:
            pass
        else:
            try:
                update_wrapper(new_func, func)
            except:
                # User won't see true signature. Oh well.
                pass

        return new_func

    Device.get_attributes = device_get_attributes
    Device.__getattr__ = device___getattr__

    if get_version() >= (4,):
        Function.__call__ = function_call
        Function.prepare = function_prepare
        Function.prepared_call = function_prepared_call
        Function.prepared_timed_call = function_prepared_timed_call
        Function.prepared_async_call = function_prepared_async_call
    else:
        Function._param_set = function_param_set_pre_v4
        Function.__call__ = function_call_pre_v4
        Function.prepare = function_prepare_pre_v4
        Function.prepared_call = function_prepared_call_pre_v4
        Function.prepared_timed_call = function_prepared_timed_call_pre_v4
        Function.prepared_async_call = function_prepared_async_call_pre_v4

        for meth_name in ["set_block_shape", "set_shared_size",
                "param_set_size", "param_set", "param_seti", "param_setf",
                "param_setv",
                "launch", "launch_grid", "launch_grid_async"]:
            setattr(Function, meth_name, mark_func_method_deprecated(
                    getattr(Function, "_"+meth_name)))

    Function.__getattr__ = function___getattr__


_add_functionality()


# {{{ pagelocked numpy arrays

def pagelocked_zeros(shape, dtype, order="C", mem_flags=0):
    result = pagelocked_empty(shape, dtype, order, mem_flags)
    result.fill(0)
    return result


def pagelocked_empty_like(array, mem_flags=0):
    if array.flags.c_contiguous:
        order = "C"
    elif array.flags.f_contiguous:
        order = "F"
    else:
        raise ValueError("could not detect array order")

    return pagelocked_empty(array.shape, array.dtype, order, mem_flags)


def pagelocked_zeros_like(array, mem_flags=0):
    result = pagelocked_empty_like(array, mem_flags)
    result.fill(0)
    return result

# }}}


# {{{ aligned numpy arrays

def aligned_zeros(shape, dtype, order="C", alignment=4096):
    result = aligned_empty(shape, dtype, order, alignment)
    result.fill(0)
    return result


def aligned_empty_like(array, alignment=4096):
    if array.flags.c_contiguous:
        order = "C"
    elif array.flags.f_contiguous:
        order = "F"
    else:
        raise ValueError("could not detect array order")

    return aligned_empty(array.shape, array.dtype, order, alignment)


def aligned_zeros_like(array, alignment=4096):
    result = aligned_empty_like(array, alignment)
    result.fill(0)
    return result

# }}}


# {{{ managed numpy arrays (CUDA Unified Memory)

def managed_zeros(shape, dtype, order="C", mem_flags=0):
    result = managed_empty(shape, dtype, order, mem_flags)
    result.fill(0)
    return result


def managed_empty_like(array, mem_flags=0):
    if array.flags.c_contiguous:
        order = "C"
    elif array.flags.f_contiguous:
        order = "F"
    else:
        raise ValueError("could not detect array order")

    return managed_empty(array.shape, array.dtype, order, mem_flags)


def managed_zeros_like(array, mem_flags=0):
    result = pagelocked_empty_like(array, mem_flags)
    result.fill(0)
    return result

# }}}


def mem_alloc_like(ary):
    return mem_alloc(ary.nbytes)


# {{{ array handling

def dtype_to_array_format(dtype):
    if dtype == np.uint8:
        return array_format.UNSIGNED_INT8
    elif dtype == np.uint16:
        return array_format.UNSIGNED_INT16
    elif dtype == np.uint32:
        return array_format.UNSIGNED_INT32
    elif dtype == np.int8:
        return array_format.SIGNED_INT8
    elif dtype == np.int16:
        return array_format.SIGNED_INT16
    elif dtype == np.int32:
        return array_format.SIGNED_INT32
    elif dtype == np.float32:
        return array_format.FLOAT
    else:
        raise TypeError(
                "cannot convert dtype '%s' to array format"
                % dtype)


def matrix_to_array(matrix, order, allow_double_hack=False):
    if order.upper() == "C":
        h, w = matrix.shape
        stride = 0
    elif order.upper() == "F":
        w, h = matrix.shape
        stride = -1
    else:
        raise LogicError("order must be either F or C")

    matrix = np.asarray(matrix, order=order)
    descr = ArrayDescriptor()

    descr.width = w
    descr.height = h

    if matrix.dtype == np.float64 and allow_double_hack:
        descr.format = array_format.SIGNED_INT32
        descr.num_channels = 2
    else:
        descr.format = dtype_to_array_format(matrix.dtype)
        descr.num_channels = 1

    ary = Array(descr)

    copy = Memcpy2D()
    copy.set_src_host(matrix)
    copy.set_dst_array(ary)
    copy.width_in_bytes = copy.src_pitch = copy.dst_pitch = \
            matrix.strides[stride]
    copy.height = h
    copy(aligned=True)

    return ary


def make_multichannel_2d_array(ndarray, order):
    """Channel count has to be the first dimension of the C{ndarray}."""

    descr = ArrayDescriptor()

    if order.upper() == "C":
        h, w, num_channels = ndarray.shape
        stride = 0
    elif order.upper() == "F":
        num_channels, w, h = ndarray.shape
        stride = 2
    else:
        raise LogicError("order must be either F or C")

    descr.width = w
    descr.height = h
    descr.format = dtype_to_array_format(ndarray.dtype)
    descr.num_channels = num_channels

    ary = Array(descr)

    copy = Memcpy2D()
    copy.set_src_host(ndarray)
    copy.set_dst_array(ary)
    copy.width_in_bytes = copy.src_pitch = copy.dst_pitch = \
            ndarray.strides[stride]
    copy.height = h
    copy(aligned=True)

    return ary


def bind_array_to_texref(ary, texref):
    texref.set_array(ary)
    texref.set_address_mode(0, address_mode.CLAMP)
    texref.set_address_mode(1, address_mode.CLAMP)
    texref.set_filter_mode(filter_mode.POINT)

# }}}


def matrix_to_texref(matrix, texref, order):
    bind_array_to_texref(matrix_to_array(matrix, order), texref)


# {{{ device copies

def to_device(bf_obj):
    import sys
    if sys.version_info >= (2, 7):
        bf = memoryview(bf_obj).tobytes()
    else:
        bf = buffer(bf_obj)
    result = mem_alloc(len(bf))
    memcpy_htod(result, bf)
    return result


def from_device(devptr, shape, dtype, order="C"):
    result = np.empty(shape, dtype, order)
    memcpy_dtoh(result, devptr)
    return result


def from_device_like(devptr, other_ary):
    result = np.empty_like(other_ary)
    memcpy_dtoh(result, devptr)
    return result

# }}}

# vim: fdm=marker

########NEW FILE########
__FILENAME__ = elementwise
"""Elementwise functionality."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""


from pycuda.tools import context_dependent_memoize
import numpy as np
from pycuda.tools import dtype_to_ctype, VectorArg, ScalarArg
from pytools import memoize_method


def get_elwise_module(arguments, operation,
        name="kernel", keep=False, options=None,
        preamble="", loop_prep="", after_loop=""):
    from pycuda.compiler import SourceModule
    return SourceModule("""
        #include <pycuda-complex.hpp>

        %(preamble)s

        __global__ void %(name)s(%(arguments)s)
        {

          unsigned tid = threadIdx.x;
          unsigned total_threads = gridDim.x*blockDim.x;
          unsigned cta_start = blockDim.x*blockIdx.x;
          unsigned i;

          %(loop_prep)s;

          for (i = cta_start + tid; i < n; i += total_threads)
          {
            %(operation)s;
          }

          %(after_loop)s;
        }
        """ % {
            "arguments": ", ".join(arg.declarator() for arg in arguments),
            "operation": operation,
            "name": name,
            "preamble": preamble,
            "loop_prep": loop_prep,
            "after_loop": after_loop,
            },
        options=options, keep=keep)


def get_elwise_range_module(arguments, operation,
        name="kernel", keep=False, options=None,
        preamble="", loop_prep="", after_loop=""):
    from pycuda.compiler import SourceModule
    return SourceModule("""
        #include <pycuda-complex.hpp>

        %(preamble)s

        __global__ void %(name)s(%(arguments)s)
        {
          unsigned tid = threadIdx.x;
          unsigned total_threads = gridDim.x*blockDim.x;
          unsigned cta_start = blockDim.x*blockIdx.x;
          long i;

          %(loop_prep)s;

          if (step < 0)
          {
            for (i = start + (cta_start + tid)*step;
              i > stop; i += total_threads*step)
            {
              %(operation)s;
            }
          }
          else
          {
            for (i = start + (cta_start + tid)*step;
              i < stop; i += total_threads*step)
            {
              %(operation)s;
            }
          }

          %(after_loop)s;
        }
        """ % {
            "arguments": ", ".join(arg.declarator() for arg in arguments),
            "operation": operation,
            "name": name,
            "preamble": preamble,
            "loop_prep": loop_prep,
            "after_loop": after_loop,
            },
        options=options, keep=keep)


def get_elwise_kernel_and_types(arguments, operation,
        name="kernel", keep=False, options=None, use_range=False, **kwargs):
    if isinstance(arguments, str):
        from pycuda.tools import parse_c_arg
        arguments = [parse_c_arg(arg) for arg in arguments.split(",")]

    if use_range:
        arguments.extend([
            ScalarArg(np.intp, "start"),
            ScalarArg(np.intp, "stop"),
            ScalarArg(np.intp, "step"),
            ])
    else:
        arguments.append(ScalarArg(np.uintp, "n"))

    if use_range:
        module_builder = get_elwise_range_module
    else:
        module_builder = get_elwise_module

    mod = module_builder(arguments, operation, name,
            keep, options, **kwargs)

    func = mod.get_function(name)
    func.prepare("".join(arg.struct_char for arg in arguments))

    return func, arguments


def get_elwise_kernel(arguments, operation,
        name="kernel", keep=False, options=None, **kwargs):
    """Return a L{pycuda.driver.Function} that performs the same scalar operation
    on one or several vectors.
    """
    func, arguments = get_elwise_kernel_and_types(
            arguments, operation, name, keep, options, **kwargs)

    return func


class ElementwiseKernel:
    def __init__(self, arguments, operation,
            name="kernel", keep=False, options=None, **kwargs):

        self.gen_kwargs = kwargs.copy()
        self.gen_kwargs.update(dict(keep=keep, options=options, name=name,
            operation=operation, arguments=arguments))

    @memoize_method
    def generate_stride_kernel_and_types(self, use_range):
        knl, arguments = get_elwise_kernel_and_types(use_range=use_range,
                **self.gen_kwargs)

        assert [i for i, arg in enumerate(arguments)
                if isinstance(arg, VectorArg)], \
                "ElementwiseKernel can only be used with functions that " \
                "have at least one vector argument"

        return knl, arguments

    def __call__(self, *args, **kwargs):
        vectors = []

        range_ = kwargs.pop("range", None)
        slice_ = kwargs.pop("slice", None)
        stream = kwargs.pop("stream", None)

        if kwargs:
            raise TypeError("invalid keyword arguments specified: "
                    + ", ".join(kwargs.iterkeys()))

        invocation_args = []
        func, arguments = self.generate_stride_kernel_and_types(
                range_ is not None or slice_ is not None)

        for arg, arg_descr in zip(args, arguments):
            if isinstance(arg_descr, VectorArg):
                if not arg.flags.forc:
                    raise RuntimeError("elementwise kernel cannot "
                            "deal with non-contiguous arrays")

                vectors.append(arg)
                invocation_args.append(arg.gpudata)
            else:
                invocation_args.append(arg)

        repr_vec = vectors[0]

        if slice_ is not None:
            if range_ is not None:
                raise TypeError("may not specify both range and slice "
                        "keyword arguments")

            range_ = slice(*slice_.indices(repr_vec.size))

        if range_ is not None:
            invocation_args.append(range_.start)
            invocation_args.append(range_.stop)
            if range_.step is None:
                invocation_args.append(1)
            else:
                invocation_args.append(range_.step)

            from pycuda.gpuarray import splay
            grid, block = splay(abs(range_.stop - range_.start)//range_.step)
        else:
            block = repr_vec._block
            grid = repr_vec._grid
            invocation_args.append(repr_vec.mem_size)

        func.prepared_async_call(grid, block, stream, *invocation_args)


@context_dependent_memoize
def get_take_kernel(dtype, idx_dtype, vec_count=1):
    ctx = {
            "idx_tp": dtype_to_ctype(idx_dtype),
            "tp": dtype_to_ctype(dtype),
            "tex_tp": dtype_to_ctype(dtype, with_fp_tex_hack=True),
            }

    args = [VectorArg(idx_dtype, "idx")] + [
            VectorArg(dtype, "dest"+str(i))for i in range(vec_count)] + [
                ScalarArg(np.intp, "n")
            ]
    preamble = "#include <pycuda-helpers.hpp>\n\n" + "\n".join(
        "texture <%s, 1, cudaReadModeElementType> tex_src%d;" % (ctx["tex_tp"], i)
        for i in range(vec_count))
    body = (
            ("%(idx_tp)s src_idx = idx[i];\n" % ctx)
            + "\n".join(
                "dest%d[i] = fp_tex1Dfetch(tex_src%d, src_idx);" % (i, i)
                for i in range(vec_count)))

    mod = get_elwise_module(args, body, "take", preamble=preamble)
    func = mod.get_function("take")
    tex_src = [mod.get_texref("tex_src%d" % i) for i in range(vec_count)]
    func.prepare("P"+(vec_count*"P")+np.dtype(np.uintp).char, texrefs=tex_src)
    return func, tex_src


@context_dependent_memoize
def get_take_put_kernel(dtype, idx_dtype, with_offsets, vec_count=1):
    ctx = {
            "idx_tp": dtype_to_ctype(idx_dtype),
            "tp": dtype_to_ctype(dtype),
            "tex_tp": dtype_to_ctype(dtype, with_fp_tex_hack=True),
            }

    args = [
                VectorArg(idx_dtype, "gmem_dest_idx"),
                VectorArg(idx_dtype, "gmem_src_idx"),
            ] + [
                VectorArg(dtype, "dest%d" % i)
                    for i in range(vec_count)
            ] + [
                ScalarArg(idx_dtype, "offset%d" % i)
                    for i in range(vec_count) if with_offsets
            ] + [ScalarArg(np.intp, "n")]

    preamble = "#include <pycuda-helpers.hpp>\n\n" + "\n".join(
        "texture <%s, 1, cudaReadModeElementType> tex_src%d;" % (ctx["tex_tp"], i)
        for i in range(vec_count))

    if with_offsets:
        def get_copy_insn(i):
            return ("dest%d[dest_idx] = "
                    "fp_tex1Dfetch(tex_src%d, src_idx+offset%d);"
                    % (i, i, i))
    else:
        def get_copy_insn(i):
            return ("dest%d[dest_idx] = "
                    "fp_tex1Dfetch(tex_src%d, src_idx);" % (i, i))

    body = (("%(idx_tp)s src_idx = gmem_src_idx[i];\n"
                "%(idx_tp)s dest_idx = gmem_dest_idx[i];\n" % ctx)
            + "\n".join(get_copy_insn(i) for i in range(vec_count)))

    mod = get_elwise_module(args, body, "take_put", preamble=preamble)
    func = mod.get_function("take_put")
    tex_src = [mod.get_texref("tex_src%d" % i) for i in range(vec_count)]

    func.prepare(
            "PP"+(vec_count*"P")
            + (bool(with_offsets)*vec_count*idx_dtype.char)
            + np.dtype(np.uintp).char,
            texrefs=tex_src)
    return func, tex_src


@context_dependent_memoize
def get_put_kernel(dtype, idx_dtype, vec_count=1):
    ctx = {
            "idx_tp": dtype_to_ctype(idx_dtype),
            "tp": dtype_to_ctype(dtype),
            }

    args = [
            VectorArg(idx_dtype, "gmem_dest_idx"),
            ] + [
                VectorArg(dtype, "dest%d" % i)
                    for i in range(vec_count)
            ] + [
                VectorArg(dtype, "src%d" % i)
                    for i in range(vec_count)
            ] + [ScalarArg(np.intp, "n")]

    body = (
            "%(idx_tp)s dest_idx = gmem_dest_idx[i];\n" % ctx
            + "\n".join("dest%d[dest_idx] = src%d[i];" % (i, i)
                for i in range(vec_count)))

    func = get_elwise_module(args, body, "put").get_function("put")
    func.prepare("P"+(2*vec_count*"P")+np.dtype(np.uintp).char)
    return func


@context_dependent_memoize
def get_copy_kernel(dtype_dest, dtype_src):
    return get_elwise_kernel(
            "%(tp_dest)s *dest, %(tp_src)s *src" % {
                "tp_dest": dtype_to_ctype(dtype_dest),
                "tp_src": dtype_to_ctype(dtype_src),
                },
            "dest[i] = src[i]",
            "copy")


@context_dependent_memoize
def get_linear_combination_kernel(summand_descriptors,
        dtype_z):
    from pycuda.tools import dtype_to_ctype
    from pycuda.elementwise import \
            VectorArg, ScalarArg, get_elwise_module

    args = []
    preamble = ["#include <pycuda-helpers.hpp>\n\n"]
    loop_prep = []
    summands = []
    tex_names = []

    for i, (is_gpu_scalar, scalar_dtype, vector_dtype) in \
            enumerate(summand_descriptors):
        if is_gpu_scalar:
            preamble.append(
                    "texture <%s, 1, cudaReadModeElementType> tex_a%d;"
                    % (dtype_to_ctype(scalar_dtype, with_fp_tex_hack=True), i))
            args.append(VectorArg(vector_dtype, "x%d" % i))
            tex_names.append("tex_a%d" % i)
            loop_prep.append(
                    "%s a%d = fp_tex1Dfetch(tex_a%d, 0)"
                    % (dtype_to_ctype(scalar_dtype), i, i))
        else:
            args.append(ScalarArg(scalar_dtype, "a%d" % i))
            args.append(VectorArg(vector_dtype, "x%d" % i))

        summands.append("a%d*x%d[i]" % (i, i))

    args.append(VectorArg(dtype_z, "z"))
    args.append(ScalarArg(np.uintp, "n"))

    mod = get_elwise_module(args,
            "z[i] = " + " + ".join(summands),
            "linear_combination",
            preamble="\n".join(preamble),
            loop_prep=";\n".join(loop_prep))

    func = mod.get_function("linear_combination")
    tex_src = [mod.get_texref(tn) for tn in tex_names]
    func.prepare("".join(arg.struct_char for arg in args),
            texrefs=tex_src)

    return func, tex_src


@context_dependent_memoize
def get_axpbyz_kernel(dtype_x, dtype_y, dtype_z):
    return get_elwise_kernel(
            "%(tp_x)s a, %(tp_x)s *x, %(tp_y)s b, %(tp_y)s *y, %(tp_z)s *z" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = a*x[i] + b*y[i]",
            "axpbyz")


@context_dependent_memoize
def get_axpbz_kernel(dtype_x, dtype_z):
    return get_elwise_kernel(
            "%(tp_z)s a, %(tp_x)s *x,%(tp_z)s b, %(tp_z)s *z" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_z": dtype_to_ctype(dtype_z)
                },
            "z[i] = a * x[i] + b",
            "axpb")


@context_dependent_memoize
def get_binary_op_kernel(dtype_x, dtype_y, dtype_z, operator):
    return get_elwise_kernel(
            "%(tp_x)s *x, %(tp_y)s *y, %(tp_z)s *z" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = x[i] %s y[i]" % operator,
            "multiply")


@context_dependent_memoize
def get_rdivide_elwise_kernel(dtype_x, dtype_z):
    return get_elwise_kernel(
            "%(tp_x)s *x, %(tp_z)s y, %(tp_z)s *z" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = y / x[i]",
            "divide_r")


@context_dependent_memoize
def get_binary_func_kernel(func, dtype_x, dtype_y, dtype_z):
    return get_elwise_kernel(
            "%(tp_x)s *x, %(tp_y)s *y, %(tp_z)s *z" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s(x[i], y[i])" % func,
            func+"_kernel")


def get_binary_minmax_kernel(func, dtype_x, dtype_y, dtype_z):
    if not np.float64 in [dtype_x, dtype_y]:
        func = func + "f"

    from pytools import any
    if any(dt.kind == "f" for dt in [dtype_x, dtype_y, dtype_z]):
        func = "f"+func

    return get_binary_func_kernel(func, dtype_x, dtype_y, dtype_z)


@context_dependent_memoize
def get_fill_kernel(dtype):
    return get_elwise_kernel(
            "%(tp)s a, %(tp)s *z" % {
                "tp": dtype_to_ctype(dtype),
                },
            "z[i] = a",
            "fill")


@context_dependent_memoize
def get_reverse_kernel(dtype):
    return get_elwise_kernel(
            "%(tp)s *y, %(tp)s *z" % {
                "tp": dtype_to_ctype(dtype),
                },
            "z[i] = y[n-1-i]",
            "reverse")


@context_dependent_memoize
def get_real_kernel(dtype, real_dtype):
    return get_elwise_kernel(
            "%(tp)s *y, %(real_tp)s *z" % {
                "tp": dtype_to_ctype(dtype),
                "real_tp": dtype_to_ctype(real_dtype),
                },
            "z[i] = real(y[i])",
            "real")


@context_dependent_memoize
def get_imag_kernel(dtype, real_dtype):
    return get_elwise_kernel(
            "%(tp)s *y, %(real_tp)s *z" % {
                "tp": dtype_to_ctype(dtype),
                "real_tp": dtype_to_ctype(real_dtype),
                },
            "z[i] = imag(y[i])",
            "imag")


@context_dependent_memoize
def get_conj_kernel(dtype):
    return get_elwise_kernel(
            "%(tp)s *y, %(tp)s *z" % {
                "tp": dtype_to_ctype(dtype),
                },
            "z[i] = pycuda::conj(y[i])",
            "conj")


@context_dependent_memoize
def get_arange_kernel(dtype):
    return get_elwise_kernel(
            "%(tp)s *z, %(tp)s start, %(tp)s step" % {
                "tp": dtype_to_ctype(dtype),
                },
            "z[i] = start + i*step",
            "arange")


@context_dependent_memoize
def get_pow_kernel(dtype):
    if dtype == np.float32:
        func = "powf"
    else:
        func = "pow"

    return get_elwise_kernel(
            "%(tp)s value, %(tp)s *y, %(tp)s *z" % {
                "tp": dtype_to_ctype(dtype),
                },
            "z[i] = %s(y[i], value)" % func,
            "pow_method")


@context_dependent_memoize
def get_pow_array_kernel(dtype_x, dtype_y, dtype_z):
    if np.float64 in [dtype_x, dtype_y]:
        func = "pow"
    else:
        func = "powf"

    return get_elwise_kernel(
            "%(tp_x)s *x, %(tp_y)s *y, %(tp_z)s *z" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_z": dtype_to_ctype(dtype_z),
                },
            "z[i] = %s(x[i], y[i])" % func,
            "pow_method")


@context_dependent_memoize
def get_fmod_kernel():
    return get_elwise_kernel(
            "float *arg, float *mod, float *z",
            "z[i] = fmod(arg[i], mod[i])",
            "fmod_kernel")


@context_dependent_memoize
def get_modf_kernel():
    return get_elwise_kernel(
            "float *x, float *intpart ,float *fracpart",
            "fracpart[i] = modf(x[i], &intpart[i])",
            "modf_kernel")


@context_dependent_memoize
def get_frexp_kernel():
    return get_elwise_kernel(
            "float *x, float *significand, float *exponent",
            """
                int expt = 0;
                significand[i] = frexp(x[i], &expt);
                exponent[i] = expt;
            """,
            "frexp_kernel")


@context_dependent_memoize
def get_ldexp_kernel():
    return get_elwise_kernel(
            "float *sig, float *expt, float *z",
            "z[i] = ldexp(sig[i], int(expt[i]))",
            "ldexp_kernel")


@context_dependent_memoize
def get_unary_func_kernel(func_name, in_dtype, out_dtype=None):
    if out_dtype is None:
        out_dtype = in_dtype

    return get_elwise_kernel(
            "%(tp_in)s *y, %(tp_out)s *z" % {
                "tp_in": dtype_to_ctype(in_dtype),
                "tp_out": dtype_to_ctype(out_dtype),
                },
            "z[i] = %s(y[i])" % func_name,
            "%s_kernel" % func_name)


@context_dependent_memoize
def get_if_positive_kernel(crit_dtype, dtype):
    return get_elwise_kernel([
            VectorArg(crit_dtype, "crit"),
            VectorArg(dtype, "then_"),
            VectorArg(dtype, "else_"),
            VectorArg(dtype, "result"),
            ],
            "result[i] = crit[i] > 0 ? then_[i] : else_[i]",
            "if_positive")


@context_dependent_memoize
def get_scalar_op_kernel(dtype_x, dtype_y, operator):
    return get_elwise_kernel(
            "%(tp_x)s *x, %(tp_a)s a, %(tp_y)s *y" % {
                "tp_x": dtype_to_ctype(dtype_x),
                "tp_y": dtype_to_ctype(dtype_y),
                "tp_a": dtype_to_ctype(dtype_x),
                },
            "y[i] = x[i] %s a" % operator,
            "scalarop_kernel")

########NEW FILE########
__FILENAME__ = autoinit
import pycuda.driver as cuda
import pycuda.gl as cudagl

cuda.init()
assert cuda.Device.count() >= 1

from pycuda.tools import make_default_context
context = make_default_context(lambda dev: cudagl.make_context(dev))
device = context.get_device()

import atexit
atexit.register(context.pop)

########NEW FILE########
__FILENAME__ = gpuarray
from __future__ import division
import numpy as np
import pycuda.elementwise as elementwise
from pytools import memoize, memoize_method
import pycuda.driver as drv
from pycuda.compyte.array import (
        as_strided as _as_strided,
        f_contiguous_strides as _f_contiguous_strides,
        c_contiguous_strides as _c_contiguous_strides,
        ArrayFlags as _ArrayFlags,
        get_common_dtype as _get_common_dtype_base)
from pycuda.characterize import has_double_support


def _get_common_dtype(obj1, obj2):
    return _get_common_dtype_base(obj1, obj2, has_double_support())


# {{{ vector types

class vec:
    pass


def _create_vector_types():
    from pycuda.characterize import platform_bits
    if platform_bits() == 32:
        long_dtype = np.int32
        ulong_dtype = np.uint32
    else:
        long_dtype = np.int64
        ulong_dtype = np.uint64

    field_names = ["x", "y", "z", "w"]

    from pycuda.tools import get_or_register_dtype

    for base_name, base_type, counts in [
            ('char', np.int8, [1, 2, 3, 4]),
            ('uchar', np.uint8, [1, 2, 3, 4]),
            ('short', np.int16, [1, 2, 3, 4]),
            ('ushort', np.uint16, [1, 2, 3, 4]),
            ('int', np.int32, [1, 2, 3, 4]),
            ('uint', np.uint32, [1, 2, 3, 4]),
            ('long', long_dtype, [1, 2, 3, 4]),
            ('ulong', ulong_dtype, [1, 2, 3, 4]),
            ('longlong', np.int64, [1, 2]),
            ('ulonglong', np.uint64, [1, 2]),
            ('float', np.float32, [1, 2, 3, 4]),
            ('double', np.float64, [1, 2]),
            ]:
        for count in counts:
            name = "%s%d" % (base_name, count)
            dtype = np.dtype([
                (field_names[i], base_type)
                for i in range(count)])

            get_or_register_dtype(name, dtype)

            setattr(vec, name, dtype)

            my_field_names = ",".join(field_names[:count])
            setattr(vec, "make_"+name,
                    staticmethod(eval(
                        "lambda %s: array((%s), dtype=my_dtype)"
                        % (my_field_names, my_field_names),
                        dict(array=np.array, my_dtype=dtype))))

_create_vector_types()

# }}}


# {{{ helper functionality

@memoize
def _splay_backend(n, dev):
    # heavily modified from cublas
    from pycuda.tools import DeviceData
    devdata = DeviceData(dev)

    min_threads = devdata.warp_size
    max_threads = 128
    max_blocks = 4 * devdata.thread_blocks_per_mp \
            * dev.get_attribute(drv.device_attribute.MULTIPROCESSOR_COUNT)

    if n < min_threads:
        block_count = 1
        threads_per_block = min_threads
    elif n < (max_blocks * min_threads):
        block_count = (n + min_threads - 1) // min_threads
        threads_per_block = min_threads
    elif n < (max_blocks * max_threads):
        block_count = max_blocks
        grp = (n + min_threads - 1) // min_threads
        threads_per_block = ((grp + max_blocks - 1) // max_blocks) * min_threads
    else:
        block_count = max_blocks
        threads_per_block = max_threads

    #print "n:%d bc:%d tpb:%d" % (n, block_count, threads_per_block)
    return (block_count, 1), (threads_per_block, 1, 1)


def splay(n, dev=None):
    if dev is None:
        dev = drv.Context.get_device()
    return _splay_backend(n, dev)

# }}}


# {{{ main GPUArray class

def _make_binary_op(operator):
    def func(self, other):
        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        if isinstance(other, GPUArray):
            assert self.shape == other.shape

            if not other.flags.forc:
                raise RuntimeError("only contiguous arrays may "
                        "be used as arguments to this operation")

            result = self._new_like_me()
            func = elementwise.get_binary_op_kernel(
                    self.dtype, other.dtype, result.dtype,
                    operator)
            func.prepared_async_call(self._grid, self._block, None,
                    self.gpudata, other.gpudata, result.gpudata,
                    self.mem_size)

            return result
        else:  # scalar operator
            result = self._new_like_me()
            func = elementwise.get_scalar_op_kernel(
                    self.dtype, result.dtype, operator)
            func.prepared_async_call(self._grid, self._block, None,
                    self.gpudata, other, result.gpudata,
                    self.mem_size)
            return result

    return func


class GPUArray(object):
    """A GPUArray is used to do array-based calculation on the GPU.

    This is mostly supposed to be a numpy-workalike. Operators
    work on an element-by-element basis, just like numpy.ndarray.
    """

    __array_priority__ = 100

    def __init__(self, shape, dtype, allocator=drv.mem_alloc,
            base=None, gpudata=None, strides=None, order="C"):
        dtype = np.dtype(dtype)

        try:
            s = 1
            for dim in shape:
                s *= dim
        except TypeError:
            assert isinstance(shape, (int, long, np.integer))
            s = shape
            shape = (shape,)

        if isinstance(s, np.integer):
            # bombs if s is a Python integer
            s = np.asscalar(s)

        if strides is None:
            if order == "F":
                strides = _f_contiguous_strides(
                        dtype.itemsize, shape)
            elif order == "C":
                strides = _c_contiguous_strides(
                        dtype.itemsize, shape)
            else:
                raise ValueError("invalid order: %s" % order)
        else:
            # FIXME: We should possibly perform some plausibility
            # checking on 'strides' here.

            strides = tuple(strides)

        self.shape = shape
        self.dtype = dtype
        self.strides = strides
        self.mem_size = self.size = s
        self.nbytes = self.dtype.itemsize * self.size

        self.allocator = allocator
        if gpudata is None:
            if self.size:
                self.gpudata = self.allocator(self.size * self.dtype.itemsize)
            else:
                self.gpudata = None

            assert base is None
        else:
            self.gpudata = gpudata

        self.base = base

        self._grid, self._block = splay(self.mem_size)

    @property
    @memoize_method
    def flags(self):
        return _ArrayFlags(self)

    def set(self, ary):
        assert ary.size == self.size
        assert ary.dtype == self.dtype
        if ary.strides != self.strides:
            from warnings import warn
            warn("Setting array from one with different strides/storage order. "
                    "This will cease to work in 2013.x.",
                    stacklevel=2)

        assert self.flags.forc

        if self.size:
            drv.memcpy_htod(self.gpudata, ary)

    def set_async(self, ary, stream=None):
        assert ary.size == self.size
        assert ary.dtype == self.dtype
        if ary.strides != self.strides:
            from warnings import warn
            warn("Setting array from one with different strides/storage order. "
                    "This will cease to work in 2013.x.",
                    stacklevel=2)

        assert self.flags.forc

        if not ary.flags.forc:
            raise RuntimeError("cannot asynchronously set from "
                    "non-contiguous array")

        if self.size:
            drv.memcpy_htod_async(self.gpudata, ary, stream)

    def get(self, ary=None, pagelocked=False):
        if ary is None:
            if pagelocked:
                ary = drv.pagelocked_empty(self.shape, self.dtype)
            else:
                ary = np.empty(self.shape, self.dtype)

            ary = _as_strided(ary, strides=self.strides)
        else:
            assert ary.size == self.size
            assert ary.dtype == self.dtype
            assert ary.flags.forc

        assert self.flags.forc, "Array in get() must be contiguous"

        if self.size:
            drv.memcpy_dtoh(ary, self.gpudata)
        return ary

    def get_async(self, stream=None, ary=None):
        if ary is None:
            ary = drv.pagelocked_empty(self.shape, self.dtype)

            ary = _as_strided(ary, strides=self.strides)
        else:
            assert ary.size == self.size
            assert ary.dtype == self.dtype
            assert ary.flags.forc

        assert self.flags.forc, "Array in get() must be contiguous"

        if self.size:
            drv.memcpy_dtoh_async(ary, self.gpudata, stream)
        return ary

    def copy(self):
        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may copied.")

        new = GPUArray(self.shape, self.dtype)
        drv.memcpy_dtod(new.gpudata, self.gpudata, self.nbytes)
        return new

    def __str__(self):
        return str(self.get())

    def __repr__(self):
        return repr(self.get())

    def __hash__(self):
        raise TypeError("GPUArrays are not hashable.")

    @property
    def ptr(self):
        return self.gpudata.__int__()

    # kernel invocation wrappers ----------------------------------------------
    def _axpbyz(self, selffac, other, otherfac, out, add_timer=None, stream=None):
        """Compute ``out = selffac * self + otherfac*other``,
        where `other` is a vector.."""
        assert self.shape == other.shape
        if not self.flags.forc or not other.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        func = elementwise.get_axpbyz_kernel(self.dtype, other.dtype, out.dtype)

        if add_timer is not None:
            add_timer(3*self.size, func.prepared_timed_call(self._grid,
                selffac, self.gpudata, otherfac, other.gpudata,
                out.gpudata, self.mem_size))
        else:
            func.prepared_async_call(self._grid, self._block, stream,
                    selffac, self.gpudata, otherfac, other.gpudata,
                    out.gpudata, self.mem_size)

        return out

    def _axpbz(self, selffac, other, out, stream=None):
        """Compute ``out = selffac * self + other``, where `other` is a scalar."""

        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        func = elementwise.get_axpbz_kernel(self.dtype, out.dtype)
        func.prepared_async_call(self._grid, self._block, stream,
                selffac, self.gpudata,
                other, out.gpudata, self.mem_size)

        return out

    def _elwise_multiply(self, other, out, stream=None):
        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        func = elementwise.get_binary_op_kernel(self.dtype, other.dtype,
                out.dtype, "*")
        func.prepared_async_call(self._grid, self._block, stream,
                self.gpudata, other.gpudata,
                out.gpudata, self.mem_size)

        return out

    def _rdiv_scalar(self, other, out, stream=None):
        """Divides an array by a scalar::

           y = n / self
        """

        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        func = elementwise.get_rdivide_elwise_kernel(self.dtype, out.dtype)
        func.prepared_async_call(self._grid, self._block, stream,
                self.gpudata, other,
                out.gpudata, self.mem_size)

        return out

    def _div(self, other, out, stream=None):
        """Divides an array by another array."""

        if not self.flags.forc or not other.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        assert self.shape == other.shape

        func = elementwise.get_binary_op_kernel(self.dtype, other.dtype,
                out.dtype, "/")
        func.prepared_async_call(self._grid, self._block, stream,
                self.gpudata, other.gpudata,
                out.gpudata, self.mem_size)

        return out

    def _new_like_me(self, dtype=None):
        strides = None
        if dtype is None:
            dtype = self.dtype
        else:
            if dtype == self.dtype:
                strides = self.strides

        return self.__class__(self.shape, dtype,
                allocator=self.allocator, strides=strides)

    # operators ---------------------------------------------------------------
    def mul_add(self, selffac, other, otherfac, add_timer=None, stream=None):
        """Return `selffac * self + otherfac*other`.
        """
        result = self._new_like_me(_get_common_dtype(self, other))
        return self._axpbyz(selffac, other, otherfac, result, add_timer)

    def __add__(self, other):
        """Add an array with an array or an array with a scalar."""

        if isinstance(other, GPUArray):
            # add another vector
            result = self._new_like_me(_get_common_dtype(self, other))
            return self._axpbyz(1, other, 1, result)
        else:
            # add a scalar
            if other == 0:
                return self.copy()
            else:
                result = self._new_like_me(_get_common_dtype(self, other))
                return self._axpbz(1, other, result)

    __radd__ = __add__

    def __sub__(self, other):
        """Substract an array from an array or a scalar from an array."""

        if isinstance(other, GPUArray):
            result = self._new_like_me(_get_common_dtype(self, other))
            return self._axpbyz(1, other, -1, result)
        else:
            if other == 0:
                return self.copy()
            else:
                # create a new array for the result
                result = self._new_like_me(_get_common_dtype(self, other))
                return self._axpbz(1, -other, result)

    def __rsub__(self, other):
        """Substracts an array by a scalar or an array::

           x = n - self
        """
        # other must be a scalar
        result = self._new_like_me(_get_common_dtype(self, other))
        return self._axpbz(-1, other, result)

    def __iadd__(self, other):
        if isinstance(other, GPUArray):
            return self._axpbyz(1, other, 1, self)
        else:
            return self._axpbz(1, other, self)

    def __isub__(self, other):
        if isinstance(other, GPUArray):
            return self._axpbyz(1, other, -1, self)
        else:
            return self._axpbz(1, -other, self)

    def __neg__(self):
        result = self._new_like_me()
        return self._axpbz(-1, 0, result)

    def __mul__(self, other):
        if isinstance(other, GPUArray):
            result = self._new_like_me(_get_common_dtype(self, other))
            return self._elwise_multiply(other, result)
        else:
            result = self._new_like_me(_get_common_dtype(self, other))
            return self._axpbz(other, 0, result)

    def __rmul__(self, scalar):
        result = self._new_like_me(_get_common_dtype(self, scalar))
        return self._axpbz(scalar, 0, result)

    def __imul__(self, other):
        if isinstance(other, GPUArray):
            return self._elwise_multiply(other, self)
        else:
            return self._axpbz(other, 0, self)

    def __div__(self, other):
        """Divides an array by an array or a scalar::

           x = self / n
        """
        if isinstance(other, GPUArray):
            result = self._new_like_me(_get_common_dtype(self, other))
            return self._div(other, result)
        else:
            if other == 1:
                return self.copy()
            else:
                # create a new array for the result
                result = self._new_like_me(_get_common_dtype(self, other))
                return self._axpbz(1/other, 0, result)

    __truediv__ = __div__

    def __rdiv__(self, other):
        """Divides an array by a scalar or an array::

           x = n / self
        """
        # create a new array for the result
        result = self._new_like_me(_get_common_dtype(self, other))
        return self._rdiv_scalar(other, result)

    __rtruediv__ = __rdiv__

    def __idiv__(self, other):
        """Divides an array by an array or a scalar::

           x /= n
        """
        if isinstance(other, GPUArray):
            return self._div(other, self)
        else:
            if other == 1:
                return self
            else:
                return self._axpbz(1/other, 0, self)

    __itruediv__ = __idiv__

    def fill(self, value, stream=None):
        """fills the array with the specified value"""
        func = elementwise.get_fill_kernel(self.dtype)
        func.prepared_async_call(self._grid, self._block, stream,
                value, self.gpudata, self.mem_size)

        return self

    def bind_to_texref(self, texref, allow_offset=False):
        return texref.set_address(self.gpudata, self.nbytes,
                allow_offset=allow_offset) / self.dtype.itemsize

    def bind_to_texref_ext(self, texref, channels=1, allow_double_hack=False,
            allow_complex_hack=False, allow_offset=False):
        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        if self.dtype == np.float64 and allow_double_hack:
            if channels != 1:
                raise ValueError(
                        "'fake' double precision textures can "
                        "only have one channel")

            channels = 2
            fmt = drv.array_format.SIGNED_INT32
            read_as_int = True
        elif self.dtype == np.complex64 and allow_complex_hack:
            if channels != 1:
                raise ValueError(
                        "'fake' complex64 textures can "
                        "only have one channel")

            channels = 2
            fmt = drv.array_format.UNSIGNED_INT32
            read_as_int = True
        elif self.dtype == np.complex128 and allow_complex_hack:
            if channels != 1:
                raise ValueError(
                        "'fake' complex128 textures can "
                        "only have one channel")

            channels = 4
            fmt = drv.array_format.SIGNED_INT32
            read_as_int = True
        else:
            fmt = drv.dtype_to_array_format(self.dtype)
            read_as_int = np.integer in self.dtype.type.__mro__

        offset = texref.set_address(self.gpudata, self.nbytes,
                allow_offset=allow_offset)
        texref.set_format(fmt, channels)

        if read_as_int:
            texref.set_flags(texref.get_flags() | drv.TRSF_READ_AS_INTEGER)

        return offset/self.dtype.itemsize

    def __len__(self):
        """Return the size of the leading dimension of self."""
        if len(self.shape):
            return self.shape[0]
        else:
            return TypeError("scalar has no len()")

    def __abs__(self):
        """Return a `GPUArray` of the absolute values of the elements
        of `self`.
        """

        result = self._new_like_me()

        if self.dtype == np.float32:
            fname = "fabsf"
        elif self.dtype == np.float64:
            fname = "fabs"
        else:
            fname = "abs"

        if issubclass(self.dtype.type, np.complexfloating):
            from pytools import match_precision
            out_dtype = match_precision(np.dtype(np.float64), self.dtype)
            result = self._new_like_me(out_dtype)
        else:
            out_dtype = self.dtype

        func = elementwise.get_unary_func_kernel(fname, self.dtype,
                out_dtype=out_dtype)

        func.prepared_async_call(self._grid, self._block, None,
                self.gpudata, result.gpudata, self.mem_size)

        return result

    def __pow__(self, other):
        """pow function::

           example:
                   array = pow(array)
                   array = pow(array,4)
                   array = pow(array,array)

        """

        if isinstance(other, GPUArray):
            if not self.flags.forc or not other.flags.forc:
                raise RuntimeError("only contiguous arrays may "
                        "be used as arguments to this operation")

            assert self.shape == other.shape

            result = self._new_like_me(_get_common_dtype(self, other))

            func = elementwise.get_pow_array_kernel(
                    self.dtype, other.dtype, result.dtype)

            func.prepared_async_call(self._grid, self._block, None,
                    self.gpudata, other.gpudata, result.gpudata,
                    self.mem_size)

            return result
        else:
            if not self.flags.forc:
                raise RuntimeError("only contiguous arrays may "
                        "be used as arguments to this operation")

            result = self._new_like_me()
            func = elementwise.get_pow_kernel(self.dtype)
            func.prepared_async_call(self._grid, self._block, None,
                    other, self.gpudata, result.gpudata,
                    self.mem_size)

            return result

    def reverse(self, stream=None):
        """Return this array in reversed order. The array is treated
        as one-dimensional.
        """

        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        result = self._new_like_me()

        func = elementwise.get_reverse_kernel(self.dtype)
        func.prepared_async_call(self._grid, self._block, stream,
                self.gpudata, result.gpudata,
                self.mem_size)

        return result

    def astype(self, dtype, stream=None):
        if not self.flags.forc:
            raise RuntimeError("only contiguous arrays may "
                    "be used as arguments to this operation")

        if dtype == self.dtype:
            return self.copy()

        result = self._new_like_me(dtype=dtype)

        func = elementwise.get_copy_kernel(dtype, self.dtype)
        func.prepared_async_call(self._grid, self._block, stream,
                result.gpudata, self.gpudata,
                self.mem_size)

        return result

    def reshape(self, *shape):
        # TODO: add more error-checking, perhaps
        if isinstance(shape[0], tuple) or isinstance(shape[0], list):
            shape = tuple(shape[0])

        if shape == self.shape:
            return self

        size = reduce(lambda x, y: x * y, shape, 1)
        if size != self.size:
            raise ValueError("total size of new array must be unchanged")

        return GPUArray(
                shape=shape,
                dtype=self.dtype,
                allocator=self.allocator,
                base=self,
                gpudata=int(self.gpudata))

    def ravel(self):
        return self.reshape(self.size)

    def view(self, dtype=None):
        if dtype is None:
            dtype = self.dtype

        old_itemsize = self.dtype.itemsize
        itemsize = np.dtype(dtype).itemsize

        from pytools import argmin2
        min_stride_axis = argmin2(
                (axis, abs(stride))
                for axis, stride in enumerate(self.strides))

        if self.shape[min_stride_axis] * old_itemsize % itemsize != 0:
            raise ValueError("new type not compatible with array")

        new_shape = (
                self.shape[:min_stride_axis]
                + (self.shape[min_stride_axis] * old_itemsize // itemsize,)
                + self.shape[min_stride_axis+1:])
        new_strides = (
                self.strides[:min_stride_axis]
                + (self.strides[min_stride_axis] * itemsize // old_itemsize,)
                + self.strides[min_stride_axis+1:])

        return GPUArray(
                shape=new_shape,
                dtype=dtype,
                allocator=self.allocator,
                strides=new_strides,
                base=self,
                gpudata=int(self.gpudata))

    # {{{ slicing

    def __getitem__(self, index):
        """
        .. versionadded:: 2013.1
        """
        if not isinstance(index, tuple):
            index = (index,)

        new_shape = []
        new_offset = 0
        new_strides = []

        seen_ellipsis = False

        index_axis = 0
        array_axis = 0
        while index_axis < len(index):
            index_entry = index[index_axis]

            if array_axis > len(self.shape):
                raise IndexError("too many axes in index")

            if isinstance(index_entry, slice):
                start, stop, idx_stride = index_entry.indices(
                        self.shape[array_axis])

                array_stride = self.strides[array_axis]

                new_shape.append((stop-start)//idx_stride)
                new_strides.append(idx_stride*array_stride)
                new_offset += array_stride*start

                index_axis += 1
                array_axis += 1

            elif isinstance(index_entry, (int, np.integer)):
                array_shape = self.shape[array_axis]
                if index_entry < 0:
                    index_entry += array_shape

                if not (0 <= index_entry < array_shape):
                    raise IndexError(
                            "subindex in axis %d out of range" % index_axis)

                new_offset += self.strides[array_axis]*index_entry

                index_axis += 1
                array_axis += 1

            elif index_entry is Ellipsis:
                index_axis += 1

                remaining_index_count = len(index) - index_axis
                new_array_axis = len(self.shape) - remaining_index_count
                if new_array_axis < array_axis:
                    raise IndexError("invalid use of ellipsis in index")
                while array_axis < new_array_axis:
                    new_shape.append(self.shape[array_axis])
                    new_strides.append(self.strides[array_axis])
                    array_axis += 1

                if seen_ellipsis:
                    raise IndexError(
                            "more than one ellipsis not allowed in index")
                seen_ellipsis = True

            else:
                raise IndexError("invalid subindex in axis %d" % index_axis)

        while array_axis < len(self.shape):
            new_shape.append(self.shape[array_axis])
            new_strides.append(self.strides[array_axis])

            array_axis += 1

        return GPUArray(
                shape=tuple(new_shape),
                dtype=self.dtype,
                allocator=self.allocator,
                base=self,
                gpudata=int(self.gpudata)+new_offset,
                strides=tuple(new_strides))

    # }}}

    # {{{ complex-valued business

    @property
    def real(self):
        dtype = self.dtype
        if issubclass(dtype.type, np.complexfloating):
            from pytools import match_precision
            real_dtype = match_precision(np.dtype(np.float64), dtype)

            result = self._new_like_me(dtype=real_dtype)

            func = elementwise.get_real_kernel(dtype, real_dtype)
            func.prepared_async_call(self._grid, self._block, None,
                    self.gpudata, result.gpudata,
                    self.mem_size)

            return result
        else:
            return self

    @property
    def imag(self):
        dtype = self.dtype
        if issubclass(self.dtype.type, np.complexfloating):
            if not self.flags.forc:
                raise RuntimeError("only contiguous arrays may "
                        "be used as arguments to this operation")

            from pytools import match_precision
            real_dtype = match_precision(np.dtype(np.float64), dtype)

            result = self._new_like_me(dtype=real_dtype)

            func = elementwise.get_imag_kernel(dtype, real_dtype)
            func.prepared_async_call(self._grid, self._block, None,
                    self.gpudata, result.gpudata,
                    self.mem_size)

            return result
        else:
            return zeros_like(self)

    def conj(self):
        dtype = self.dtype
        if issubclass(self.dtype.type, np.complexfloating):
            if not self.flags.forc:
                raise RuntimeError("only contiguous arrays may "
                        "be used as arguments to this operation")

            result = self._new_like_me()

            func = elementwise.get_conj_kernel(dtype)
            func.prepared_async_call(self._grid, self._block, None,
                    self.gpudata, result.gpudata,
                    self.mem_size)

            return result
        else:
            return self

    # }}}

    # {{{ rich comparisons

    __eq__ = _make_binary_op("==")
    __ne__ = _make_binary_op("!=")
    __le__ = _make_binary_op("<=")
    __ge__ = _make_binary_op(">=")
    __lt__ = _make_binary_op("<")
    __gt__ = _make_binary_op(">")

    # }}}

# }}}


# {{{ creation helpers

def to_gpu(ary, allocator=drv.mem_alloc):
    """converts a numpy array to a GPUArray"""
    result = GPUArray(ary.shape, ary.dtype, allocator, strides=ary.strides)
    result.set(ary)
    return result


def to_gpu_async(ary, allocator=drv.mem_alloc, stream=None):
    """converts a numpy array to a GPUArray"""
    result = GPUArray(ary.shape, ary.dtype, allocator, strides=ary.strides)
    result.set_async(ary, stream)
    return result


empty = GPUArray


def zeros(shape, dtype, allocator=drv.mem_alloc, order="C"):
    """Returns an array of the given shape and dtype filled with 0's."""

    result = GPUArray(shape, dtype, allocator, order=order)
    zero = np.zeros((), dtype)
    result.fill(zero)
    return result


def empty_like(other_ary):
    result = GPUArray(
            other_ary.shape, other_ary.dtype, other_ary.allocator)
    return result


def zeros_like(other_ary):
    result = GPUArray(
            other_ary.shape, other_ary.dtype, other_ary.allocator)
    zero = np.zeros((), result.dtype)
    result.fill(zero)
    return result


def arange(*args, **kwargs):
    """Create an array filled with numbers spaced `step` apart,
    starting from `start` and ending at `stop`.

    For floating point arguments, the length of the result is
    `ceil((stop - start)/step)`.  This rule may result in the last
    element of the result being greater than stop.
    """

    # argument processing -----------------------------------------------------

    # Yuck. Thanks, numpy developers. ;)
    from pytools import Record

    class Info(Record):
        pass

    explicit_dtype = False

    inf = Info()
    inf.start = None
    inf.stop = None
    inf.step = None
    inf.dtype = None

    if isinstance(args[-1], np.dtype):
        inf.dtype = args[-1]
        args = args[:-1]
        explicit_dtype = True

    argc = len(args)
    if argc == 0:
        raise ValueError("stop argument required")
    elif argc == 1:
        inf.stop = args[0]
    elif argc == 2:
        inf.start = args[0]
        inf.stop = args[1]
    elif argc == 3:
        inf.start = args[0]
        inf.stop = args[1]
        inf.step = args[2]
    else:
        raise ValueError("too many arguments")

    admissible_names = ["start", "stop", "step", "dtype"]
    for k, v in kwargs.iteritems():
        if k in admissible_names:
            if getattr(inf, k) is None:
                setattr(inf, k, v)
                if k == "dtype":
                    explicit_dtype = True
            else:
                raise ValueError("may not specify '%s' by position and keyword" % k)
        else:
            raise ValueError("unexpected keyword argument '%s'" % k)

    if inf.start is None:
        inf.start = 0
    if inf.step is None:
        inf.step = 1
    if inf.dtype is None:
        inf.dtype = np.array([inf.start, inf.stop, inf.step]).dtype

    # actual functionality ----------------------------------------------------
    dtype = np.dtype(inf.dtype)
    start = dtype.type(inf.start)
    step = dtype.type(inf.step)
    stop = dtype.type(inf.stop)

    if not explicit_dtype and dtype != np.float32:
        from warnings import warn
        warn("behavior change: arange guessed dtype other than float32. "
                "suggest specifying explicit dtype.")

    from math import ceil
    size = int(ceil((stop-start)/step))

    result = GPUArray((size,), dtype)

    func = elementwise.get_arange_kernel(dtype)
    func.prepared_async_call(result._grid, result._block, kwargs.get("stream"),
            result.gpudata, start, step, size)

    return result

# }}}

# {{{ pickle support

import copy_reg
copy_reg.pickle(GPUArray,
                lambda data: (to_gpu, (data.get(),)),
                to_gpu)

# }}}


# {{{ take/put

def take(a, indices, out=None, stream=None):
    if out is None:
        out = GPUArray(indices.shape, a.dtype, a.allocator)

    assert len(indices.shape) == 1

    func, tex_src = elementwise.get_take_kernel(a.dtype, indices.dtype)
    a.bind_to_texref_ext(tex_src[0], allow_double_hack=True, allow_complex_hack=True)

    func.prepared_async_call(out._grid, out._block, stream,
            indices.gpudata, out.gpudata, indices.size)

    return out


def multi_take(arrays, indices, out=None, stream=None):
    if not len(arrays):
        return []

    assert len(indices.shape) == 1

    from pytools import single_valued
    a_dtype = single_valued(a.dtype for a in arrays)
    a_allocator = arrays[0].dtype

    vec_count = len(arrays)

    if out is None:
        out = [GPUArray(indices.shape, a_dtype, a_allocator)
                for i in range(vec_count)]
    else:
        if len(out) != len(arrays):
            raise ValueError("out and arrays must have the same length")

    chunk_size = _builtin_min(vec_count, 20)

    def make_func_for_chunk_size(chunk_size):
        return elementwise.get_take_kernel(a_dtype, indices.dtype,
                vec_count=chunk_size)

    func, tex_src = make_func_for_chunk_size(chunk_size)

    for start_i in range(0, len(arrays), chunk_size):
        chunk_slice = slice(start_i, start_i+chunk_size)

        if start_i + chunk_size > vec_count:
            func, tex_src = make_func_for_chunk_size(vec_count-start_i)

        for i, a in enumerate(arrays[chunk_slice]):
            a.bind_to_texref_ext(tex_src[i], allow_double_hack=True)

        func.prepared_async_call(indices._grid, indices._block, stream,
                indices.gpudata,
                *([o.gpudata for o in out[chunk_slice]]
                    + [indices.size]))

    return out


def multi_take_put(arrays, dest_indices, src_indices, dest_shape=None,
        out=None, stream=None, src_offsets=None):
    if not len(arrays):
        return []

    from pytools import single_valued
    a_dtype = single_valued(a.dtype for a in arrays)
    a_allocator = arrays[0].allocator

    vec_count = len(arrays)

    if out is None:
        out = [GPUArray(dest_shape, a_dtype, a_allocator)
                for i in range(vec_count)]
    else:
        if a_dtype != single_valued(o.dtype for o in out):
            raise TypeError("arrays and out must have the same dtype")
        if len(out) != vec_count:
            raise ValueError("out and arrays must have the same length")

    if src_indices.dtype != dest_indices.dtype:
        raise TypeError("src_indices and dest_indices must have the same dtype")

    if len(src_indices.shape) != 1:
        raise ValueError("src_indices must be 1D")

    if src_indices.shape != dest_indices.shape:
        raise ValueError("src_indices and dest_indices must have the same shape")

    if src_offsets is None:
        src_offsets_list = []
        max_chunk_size = 20
    else:
        src_offsets_list = src_offsets
        if len(src_offsets) != vec_count:
            raise ValueError("src_indices and src_offsets must have the same length")
        max_chunk_size = 10

    chunk_size = _builtin_min(vec_count, max_chunk_size)

    def make_func_for_chunk_size(chunk_size):
        return elementwise.get_take_put_kernel(
                a_dtype, src_indices.dtype,
                with_offsets=src_offsets is not None,
                vec_count=chunk_size)

    func, tex_src = make_func_for_chunk_size(chunk_size)

    for start_i in range(0, len(arrays), chunk_size):
        chunk_slice = slice(start_i, start_i+chunk_size)

        if start_i + chunk_size > vec_count:
            func, tex_src = make_func_for_chunk_size(vec_count-start_i)

        for src_tr, a in zip(tex_src, arrays[chunk_slice]):
            a.bind_to_texref_ext(src_tr, allow_double_hack=True)

        func.prepared_async_call(src_indices._grid,  src_indices._block, stream,
                dest_indices.gpudata, src_indices.gpudata,
                *([o.gpudata for o in out[chunk_slice]]
                    + src_offsets_list[chunk_slice]
                    + [src_indices.size]))

    return out


def multi_put(arrays, dest_indices, dest_shape=None, out=None, stream=None):
    if not len(arrays):
        return []

    from pytools import single_valued
    a_dtype = single_valued(a.dtype for a in arrays)
    a_allocator = arrays[0].allocator

    vec_count = len(arrays)

    if out is None:
        out = [GPUArray(dest_shape, a_dtype, a_allocator)
                for i in range(vec_count)]
    else:
        if a_dtype != single_valued(o.dtype for o in out):
            raise TypeError("arrays and out must have the same dtype")
        if len(out) != vec_count:
            raise ValueError("out and arrays must have the same length")

    if len(dest_indices.shape) != 1:
        raise ValueError("src_indices must be 1D")

    chunk_size = _builtin_min(vec_count, 10)

    def make_func_for_chunk_size(chunk_size):
        return elementwise.get_put_kernel(
                a_dtype, dest_indices.dtype, vec_count=chunk_size)

    func = make_func_for_chunk_size(chunk_size)

    for start_i in range(0, len(arrays), chunk_size):
        chunk_slice = slice(start_i, start_i+chunk_size)

        if start_i + chunk_size > vec_count:
            func = make_func_for_chunk_size(vec_count-start_i)

        func.prepared_async_call(dest_indices._grid, dest_indices._block, stream,
                dest_indices.gpudata,
                *([o.gpudata for o in out[chunk_slice]]
                    + [i.gpudata for i in arrays[chunk_slice]]
                    + [dest_indices.size]))

    return out

# }}}


# {{{ conditionals

def if_positive(criterion, then_, else_, out=None, stream=None):
    if not (criterion.shape == then_.shape == else_.shape):
        raise ValueError("shapes do not match")

    if not (then_.dtype == else_.dtype):
        raise ValueError("dtypes do not match")

    func = elementwise.get_if_positive_kernel(
            criterion.dtype, then_.dtype)

    if out is None:
        out = empty_like(then_)

    func.prepared_async_call(criterion._grid, criterion._block, stream,
            criterion.gpudata, then_.gpudata, else_.gpudata, out.gpudata,
            criterion.size)

    return out


def _make_binary_minmax_func(which):
    def f(a, b, out=None, stream=None):
        if out is None:
            out = empty_like(a)

        func = elementwise.get_binary_minmax_kernel(which,
                a.dtype, b.dtype, out.dtype)

        func.prepared_async_call(a._grid, a._block, stream,
                a.gpudata, b.gpudata, out.gpudata, a.size)

        return out
    return f


minimum = _make_binary_minmax_func("min")
maximum = _make_binary_minmax_func("max")

# }}}


# {{{ reductions

def sum(a, dtype=None, stream=None):
    from pycuda.reduction import get_sum_kernel
    krnl = get_sum_kernel(dtype, a.dtype)
    return krnl(a, stream=stream)


def subset_sum(subset, a, dtype=None, stream=None):
    from pycuda.reduction import get_subset_sum_kernel
    krnl = get_subset_sum_kernel(dtype, subset.dtype, a.dtype)
    return krnl(subset, a, stream=stream)


def dot(a, b, dtype=None, stream=None):
    from pycuda.reduction import get_dot_kernel
    if dtype is None:
        dtype = _get_common_dtype(a, b)
    krnl = get_dot_kernel(dtype, a.dtype, b.dtype)
    return krnl(a, b, stream=stream)


def subset_dot(subset, a, b, dtype=None, stream=None):
    from pycuda.reduction import get_subset_dot_kernel
    krnl = get_subset_dot_kernel(dtype, subset.dtype, a.dtype, b.dtype)
    return krnl(subset, a, b, stream=stream)


def _make_minmax_kernel(what):
    def f(a, stream=None):
        from pycuda.reduction import get_minmax_kernel
        krnl = get_minmax_kernel(what, a.dtype)
        return krnl(a,  stream=stream)

    return f

_builtin_min = min
_builtin_max = max
min = _make_minmax_kernel("min")
max = _make_minmax_kernel("max")


def _make_subset_minmax_kernel(what):
    def f(subset, a, stream=None):
        from pycuda.reduction import get_subset_minmax_kernel
        krnl = get_subset_minmax_kernel(what, a.dtype, subset.dtype)
        return krnl(subset, a,  stream=stream)

    return f

subset_min = _make_subset_minmax_kernel("min")
subset_max = _make_subset_minmax_kernel("max")

# }}}

# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = reduction
"""Computation of reductions on vectors."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

Based on code/ideas by Mark Harris <mharris@nvidia.com>.

Original License:

Copyright 1993-2007 NVIDIA Corporation.  All rights reserved.

NOTICE TO USER:

This source code is subject to NVIDIA ownership rights under U.S. and
international Copyright laws.

NVIDIA MAKES NO REPRESENTATION ABOUT THE SUITABILITY OF THIS SOURCE
CODE FOR ANY PURPOSE.  IT IS PROVIDED "AS IS" WITHOUT EXPRESS OR
IMPLIED WARRANTY OF ANY KIND.  NVIDIA DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOURCE CODE, INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY, NONINFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
IN NO EVENT SHALL NVIDIA BE LIABLE FOR ANY SPECIAL, INDIRECT, INCIDENTAL,
OR CONSEQUENTIAL DAMAGES, OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE
OR PERFORMANCE OF THIS SOURCE CODE.

U.S. Government End Users.  This source code is a "commercial item" as
that term is defined at 48 C.F.R. 2.101 (OCT 1995), consisting  of
"commercial computer software" and "commercial computer software
documentation" as such terms are used in 48 C.F.R. 12.212 (SEPT 1995)
and is provided to the U.S. Government only as a commercial end item.
Consistent with 48 C.F.R.12.212 and 48 C.F.R. 227.7202-1 through
227.7202-4 (JUNE 1995), all U.S. Government End Users acquire the
source code with only those rights set forth herein.
"""




from pycuda.tools import context_dependent_memoize
from pycuda.tools import dtype_to_ctype
import numpy as np




def get_reduction_module(out_type, block_size,
        neutral, reduce_expr, map_expr, arguments,
        name="reduce_kernel", keep=False, options=None, preamble=""):

    from pycuda.compiler import SourceModule
    src = """
        #include <pycuda-complex.hpp>

        #define BLOCK_SIZE %(block_size)d
        #define READ_AND_MAP(i) (%(map_expr)s)
        #define REDUCE(a, b) (%(reduce_expr)s)

        %(preamble)s

        typedef %(out_type)s out_type;

        extern "C"
        __global__
        void %(name)s(out_type *out, %(arguments)s,
          unsigned int seq_count, unsigned int n)
        {
          // Needs to be variable-size to prevent the braindead CUDA compiler from
          // running constructors on this array. Grrrr.
          extern __shared__ out_type sdata[];

          unsigned int tid = threadIdx.x;

          unsigned int i = blockIdx.x*BLOCK_SIZE*seq_count + tid;

          out_type acc = %(neutral)s;
          for (unsigned s = 0; s < seq_count; ++s)
          {
            if (i >= n)
              break;
            acc = REDUCE(acc, READ_AND_MAP(i));

            i += BLOCK_SIZE;
          }

          sdata[tid] = acc;

          __syncthreads();

          #if (BLOCK_SIZE >= 512)
            if (tid < 256) { sdata[tid] = REDUCE(sdata[tid], sdata[tid + 256]); }
            __syncthreads();
          #endif

          #if (BLOCK_SIZE >= 256)
            if (tid < 128) { sdata[tid] = REDUCE(sdata[tid], sdata[tid + 128]); }
            __syncthreads();
          #endif

          #if (BLOCK_SIZE >= 128)
            if (tid < 64) { sdata[tid] = REDUCE(sdata[tid], sdata[tid + 64]); }
            __syncthreads();
          #endif

          if (tid < 32)
          {
            // 'volatile' required according to Fermi compatibility guide 1.2.2
            volatile out_type *smem = sdata;
            if (BLOCK_SIZE >= 64) smem[tid] = REDUCE(smem[tid], smem[tid + 32]);
            if (BLOCK_SIZE >= 32) smem[tid] = REDUCE(smem[tid], smem[tid + 16]);
            if (BLOCK_SIZE >= 16) smem[tid] = REDUCE(smem[tid], smem[tid + 8]);
            if (BLOCK_SIZE >= 8)  smem[tid] = REDUCE(smem[tid], smem[tid + 4]);
            if (BLOCK_SIZE >= 4)  smem[tid] = REDUCE(smem[tid], smem[tid + 2]);
            if (BLOCK_SIZE >= 2)  smem[tid] = REDUCE(smem[tid], smem[tid + 1]);
          }

          if (tid == 0) out[blockIdx.x] = sdata[0];
        }
        """ % {
            "out_type": out_type,
            "arguments": arguments,
            "block_size": block_size,
            "neutral": neutral,
            "reduce_expr": reduce_expr,
            "map_expr": map_expr,
            "name": name,
            "preamble": preamble
            }
    return SourceModule(src, options=options, keep=keep, no_extern_c=True)




def get_reduction_kernel_and_types(stage, out_type, block_size,
        neutral, reduce_expr, map_expr=None, arguments=None,
        name="reduce_kernel", keep=False, options=None, preamble=""):

    if stage == 1:
        if map_expr is None:
            map_expr = "in[i]"

    elif stage == 2:
        if map_expr is None:
            map_expr = "pycuda_reduction_inp[i]"

        in_arg = "const %s *pycuda_reduction_inp" % out_type
        if arguments:
            arguments = in_arg + ", " + arguments
        else:
            arguments = in_arg

    else:
        assert False

    mod = get_reduction_module(out_type, block_size,
            neutral, reduce_expr, map_expr, arguments,
            name, keep, options, preamble)

    from pycuda.tools import get_arg_type
    func = mod.get_function(name)
    arg_types = [get_arg_type(arg) for arg in arguments.split(",")]
    func.prepare("P%sII" % "".join(arg_types))

    return func, arg_types




class ReductionKernel:
    def __init__(self, dtype_out,
            neutral, reduce_expr, map_expr=None, arguments=None,
            name="reduce_kernel", keep=False, options=None, preamble=""):

        self.dtype_out = np.dtype(dtype_out)

        self.block_size = 512

        s1_func, self.stage1_arg_types = get_reduction_kernel_and_types(
                1, dtype_to_ctype(dtype_out), self.block_size,
                neutral, reduce_expr, map_expr,
                arguments, name=name+"_stage1", keep=keep, options=options,
                preamble=preamble)
        self.stage1_func = s1_func.prepared_async_call

        # stage 2 has only one input and no map expression
        s2_func, self.stage2_arg_types = get_reduction_kernel_and_types(
                2, dtype_to_ctype(dtype_out), self.block_size,
                neutral, reduce_expr, arguments=arguments,
                name=name+"_stage2", keep=keep, options=options,
                preamble=preamble)
        self.stage2_func = s2_func.prepared_async_call

        assert [i for i, arg_tp in enumerate(self.stage1_arg_types) if arg_tp == "P"], \
                "ReductionKernel can only be used with functions that have at least one " \
                "vector argument"

    def __call__(self, *args, **kwargs):
        MAX_BLOCK_COUNT = 1024
        SMALL_SEQ_COUNT = 4

        s1_func = self.stage1_func
        s2_func = self.stage2_func

        kernel_wrapper = kwargs.get("kernel_wrapper")
        if kernel_wrapper is not None:
            s1_func = kernel_wrapper(s1_func)
            s2_func = kernel_wrapper(s2_func)

        stream = kwargs.get("stream")

        from gpuarray import empty

        f = s1_func
        arg_types = self.stage1_arg_types

        stage1_args = args

        while True:
            invocation_args = []
            vectors = []

            for arg, arg_tp in zip(args, arg_types):
                if arg_tp == "P":
                    if not arg.flags.forc:
                        raise RuntimeError("ReductionKernel cannot "
                                "deal with non-contiguous arrays")

                    vectors.append(arg)
                    invocation_args.append(arg.gpudata)
                else:
                    invocation_args.append(arg)

            repr_vec = vectors[0]
            sz = repr_vec.size

            if sz <= self.block_size*SMALL_SEQ_COUNT*MAX_BLOCK_COUNT:
                total_block_size = SMALL_SEQ_COUNT*self.block_size
                block_count = (sz + total_block_size - 1) // total_block_size
                seq_count = SMALL_SEQ_COUNT
            else:
                block_count = MAX_BLOCK_COUNT
                macroblock_size = block_count*self.block_size
                seq_count = (sz + macroblock_size - 1) // macroblock_size

            if block_count == 1:
                result = empty((), self.dtype_out, repr_vec.allocator)
            else:
                result = empty((block_count,), self.dtype_out, repr_vec.allocator)

            kwargs = dict(shared_size=self.block_size*self.dtype_out.itemsize)

            #print block_count, seq_count, self.block_size, sz
            f((block_count, 1), (self.block_size, 1, 1), stream,
                    *([result.gpudata]+invocation_args+[seq_count, sz]),
                    **kwargs)

            if block_count == 1:
                return result
            else:
                f = s2_func
                arg_types = self.stage2_arg_types
                args = (result,) + stage1_args




@context_dependent_memoize
def get_sum_kernel(dtype_out, dtype_in):
    if dtype_out is None:
        dtype_out = dtype_in

    return ReductionKernel(dtype_out, "0", "a+b",
            arguments="const %(tp)s *in" % {"tp": dtype_to_ctype(dtype_in)})




@context_dependent_memoize
def get_subset_sum_kernel(dtype_out, dtype_subset, dtype_in):
    if dtype_out is None:
        dtype_out = dtype_in

    return ReductionKernel(dtype_out, "0", "a+b",
            map_expr="in[lookup_tbl[i]]",
            arguments="const %(tp_lut)s *lookup_tbl, const %(tp)s *in"
            % {
                "tp": dtype_to_ctype(dtype_in),
                "tp_lut": dtype_to_ctype(dtype_subset),
                })




@context_dependent_memoize
def get_dot_kernel(dtype_out, dtype_a, dtype_b):
    return ReductionKernel(dtype_out, neutral="0",
            reduce_expr="a+b", map_expr="a[i]*b[i]",
            arguments="const %(tp_a)s *a, const %(tp_b)s *b" % {
                "tp_a": dtype_to_ctype(dtype_a),
                "tp_b": dtype_to_ctype(dtype_b),
                }, keep=True)




@context_dependent_memoize
def get_subset_dot_kernel(dtype_out, dtype_subset, dtype_a=None, dtype_b=None):
    if dtype_out is None:
        dtype_out = dtype_a

    if dtype_b is None:
        if dtype_a is None:
            dtype_b = dtype_out
        else:
            dtype_b = dtype_a

    if dtype_a is None:
        dtype_a = dtype_out

    # important: lookup_tbl must be first--it controls the length
    return ReductionKernel(dtype_out, neutral="0",
            reduce_expr="a+b", map_expr="a[lookup_tbl[i]]*b[lookup_tbl[i]]",
            arguments="const %(tp_lut)s *lookup_tbl, "
            "const %(tp_a)s *a, const %(tp_b)s *b" % {
            "tp_a": dtype_to_ctype(dtype_a),
            "tp_b": dtype_to_ctype(dtype_b),
            "tp_lut": dtype_to_ctype(dtype_subset),
            })




def get_minmax_neutral(what, dtype):
    dtype = np.dtype(dtype)
    if issubclass(dtype.type, np.inexact):
        if what == "min":
            return "MY_INFINITY"
        elif what == "max":
            return "-MY_INFINITY"
        else:
            raise ValueError("what is not min or max.")
    else:
        if what == "min":
            return str(np.iinfo(dtype).max)
        elif what == "max":
            return str(np.iinfo(dtype).min)
        else:
            raise ValueError("what is not min or max.")




@context_dependent_memoize
def get_minmax_kernel(what, dtype):
    if dtype == np.float64:
        reduce_expr = "f%s(a,b)" % what
    elif dtype == np.float32:
        reduce_expr = "f%sf(a,b)" % what
    elif dtype.kind in "iu":
        reduce_expr = "%s(a,b)" % what
    else:
        raise TypeError("unsupported dtype specified")

    return ReductionKernel(dtype,
            neutral=get_minmax_neutral(what, dtype),
            reduce_expr="%(reduce_expr)s" % {"reduce_expr": reduce_expr},
            arguments="const %(tp)s *in" % {
                "tp": dtype_to_ctype(dtype),
                }, preamble="#define MY_INFINITY (1./0)")




@context_dependent_memoize
def get_subset_minmax_kernel(what, dtype, dtype_subset):
    if dtype == np.float64:
        reduce_expr = "f%s(a,b)" % what
    elif dtype == np.float32:
        reduce_expr = "f%sf(a,b)" % what
    elif dtype.kind in "iu":
        reduce_expr = "%s(a,b)" % what
    else:
        raise TypeError("unsupported dtype specified")

    return ReductionKernel(dtype,
            neutral=get_minmax_neutral(what, dtype),
            reduce_expr="%(reduce_expr)s" % {"reduce_expr": reduce_expr},
            map_expr="in[lookup_tbl[i]]",
            arguments="const %(tp_lut)s *lookup_tbl, "
            "const %(tp)s *in"  % {
            "tp": dtype_to_ctype(dtype),
            "tp_lut": dtype_to_ctype(dtype_subset),
            }, preamble="#define MY_INFINITY (1./0)")

########NEW FILE########
__FILENAME__ = scan
"""Scan primitive."""

from __future__ import division

__copyright__ = """
Copyright 2011 Andreas Kloeckner
Copyright 2008-2011 NVIDIA Corporation
"""



__license__ = """
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Derived from thrust/detail/backend/cuda/detail/fast_scan.inl
within the Thrust project, https://code.google.com/p/thrust/

Direct browse link:
https://code.google.com/p/thrust/source/browse/thrust/detail/backend/cuda/detail/fast_scan.inl
"""




import numpy as np

import pycuda.driver as driver
import pycuda.gpuarray as gpuarray
from pycuda.compiler import SourceModule
from pycuda.tools import dtype_to_ctype
import pycuda._mymako as mako
from pycuda._cluda import CLUDA_PREAMBLE




SHARED_PREAMBLE = CLUDA_PREAMBLE + """
#define WG_SIZE ${wg_size}
#define SCAN_EXPR(a, b) ${scan_expr}

${preamble}

typedef ${scan_type} scan_type;
"""




SCAN_INTERVALS_SOURCE = mako.template.Template(SHARED_PREAMBLE + """//CL//
#define K ${wg_seq_batches}

<%def name="make_group_scan(name, with_bounds_check)">
    WITHIN_KERNEL
    void ${name}(LOCAL_MEM_ARG scan_type *array
    % if with_bounds_check:
      , const unsigned n
    % endif
    )
    {
        scan_type val = array[LID_0];

        <% offset = 1 %>

        % while offset <= wg_size:
            if (LID_0 >= ${offset}
            % if with_bounds_check:
              && LID_0 < n
            % endif
            )
            {
                scan_type tmp = array[LID_0 - ${offset}];
                val = SCAN_EXPR(tmp, val);
            }

            local_barrier();
            array[LID_0] = val;
            local_barrier();

            <% offset *= 2 %>
        % endwhile
    }
</%def>

${make_group_scan("scan_group", False)}
${make_group_scan("scan_group_n", True)}

KERNEL
REQD_WG_SIZE(WG_SIZE, 1, 1)
void ${name_prefix}_scan_intervals(
    GLOBAL_MEM scan_type *input,
    const unsigned int N,
    const unsigned int interval_size,
    GLOBAL_MEM scan_type *output,
    GLOBAL_MEM scan_type *group_results)
{
    // padded in WG_SIZE to avoid bank conflicts
    // index K in first dimension used for carry storage
    LOCAL_MEM scan_type ldata[K + 1][WG_SIZE + 1];

    const unsigned int interval_begin = interval_size * GID_0;
    const unsigned int interval_end   = min(interval_begin + interval_size, N);

    const unsigned int unit_size  = K * WG_SIZE;

    unsigned int unit_base = interval_begin;

    %for is_tail in [False, True]:

        %if not is_tail:
            for(; unit_base + unit_size <= interval_end; unit_base += unit_size)
        %else:
            if (unit_base < interval_end)
        %endif

        {
            // Algorithm: Each work group is responsible for one contiguous
            // 'interval', of which there are just enough to fill all compute
            // units.  Intervals are split into 'units'. A unit is what gets
            // worked on in parallel by one work group.

            // Each unit has two axes--the local-id axis and the k axis.
            //
            // * * * * * * * * * * ----> lid
            // * * * * * * * * * *
            // * * * * * * * * * *
            // * * * * * * * * * *
            // * * * * * * * * * *
            // |
            // v k

            // This is a three-phase algorithm, in which first each interval
            // does its local scan, then a scan across intervals exchanges data
            // globally, and the final update adds the exchanged sums to each
            // interval.

            // Exclusive scan is realized by performing a right-shift inside
            // the final update.

            // read a unit's worth of data from global

            for(unsigned int k = 0; k < K; k++)
            {
                const unsigned int offset = k*WG_SIZE + LID_0;

                %if is_tail:
                if (unit_base + offset < interval_end)
                %endif
                {
                    ldata[offset % K][offset / K] = input[unit_base + offset];
                }
            }

            // carry in from previous unit, if applicable.
            if (LID_0 == 0 && unit_base != interval_begin)
                ldata[0][0] = SCAN_EXPR(ldata[K][WG_SIZE - 1], ldata[0][0]);

            local_barrier();

            // scan along k (sequentially in each work item)
            scan_type sum = ldata[0][LID_0];

            %if is_tail:
                const unsigned int offset_end = interval_end - unit_base;
            %endif

            for(unsigned int k = 1; k < K; k++)
            {
                %if is_tail:
                if (K * LID_0 + k < offset_end)
                %endif
                {
                    scan_type tmp = ldata[k][LID_0];
                    sum = SCAN_EXPR(sum, tmp);
                    ldata[k][LID_0] = sum;
                }
            }

            // store carry in out-of-bounds (padding) array entry in the K direction
            ldata[K][LID_0] = sum;
            local_barrier();

            // tree-based parallel scan along local id
            %if not is_tail:
                scan_group(&ldata[K][0]);
            %else:
                scan_group_n(&ldata[K][0], offset_end / K);
            %endif

            // update local values
            if (LID_0 > 0)
            {
                sum = ldata[K][LID_0 - 1];

                for(unsigned int k = 0; k < K; k++)
                {
                    %if is_tail:
                    if (K * LID_0 + k < offset_end)
                    %endif
                    {
                        scan_type tmp = ldata[k][LID_0];
                        ldata[k][LID_0] = SCAN_EXPR(sum, tmp);
                    }
                }
            }

            local_barrier();

            // write data
            for(unsigned int k = 0; k < K; k++)
            {
                const unsigned int offset = k*WG_SIZE + LID_0;

                %if is_tail:
                if (unit_base + offset < interval_end)
                %endif
                {
                    output[unit_base + offset] = ldata[offset % K][offset / K];
                }
            }

            local_barrier();
        }

    % endfor

    // write interval sum
    if (LID_0 == 0)
    {
        group_results[GID_0] = output[interval_end - 1];
    }
}
""")




INCLUSIVE_UPDATE_SOURCE = mako.template.Template(SHARED_PREAMBLE + """//CL//
KERNEL
REQD_WG_SIZE(WG_SIZE, 1, 1)
void ${name_prefix}_final_update(
    GLOBAL_MEM scan_type *output,
    const unsigned int N,
    const unsigned int interval_size,
    GLOBAL_MEM scan_type *group_results)
{
    const unsigned int interval_begin = interval_size * GID_0;
    const unsigned int interval_end   = min(interval_begin + interval_size, N);

    if (GID_0 == 0)
        return;

    // value to add to this segment
    scan_type prev_group_sum = group_results[GID_0 - 1];

    // advance result pointer
    output += interval_begin + LID_0;

    for(unsigned int unit_base = interval_begin;
        unit_base < interval_end;
        unit_base += WG_SIZE, output += WG_SIZE)
    {
        const unsigned int i = unit_base + LID_0;

        if(i < interval_end)
        {
            *output = SCAN_EXPR(prev_group_sum, *output);
        }
    }
}
""")




EXCLUSIVE_UPDATE_SOURCE = mako.template.Template(SHARED_PREAMBLE + """//CL//
KERNEL
REQD_WG_SIZE(WG_SIZE, 1, 1)
void ${name_prefix}_final_update(
    GLOBAL_MEM scan_type *output,
    const unsigned int N,
    const unsigned int interval_size,
    GLOBAL_MEM scan_type *group_results)
{
    LOCAL_MEM scan_type ldata[WG_SIZE];

    const unsigned int interval_begin = interval_size * GID_0;
    const unsigned int interval_end   = min(interval_begin + interval_size, N);

    // value to add to this segment
    scan_type carry = ${neutral};
    if(GID_0 != 0)
    {
        scan_type tmp = group_results[GID_0 - 1];
        carry = SCAN_EXPR(carry, tmp);
    }

    scan_type val = carry;

    // advance result pointer
    output += interval_begin + LID_0;

    for (unsigned int unit_base = interval_begin;
        unit_base < interval_end;
        unit_base += WG_SIZE, output += WG_SIZE)
    {
        const unsigned int i = unit_base + LID_0;

        if(i < interval_end)
        {
            scan_type tmp = *output;
            ldata[LID_0] = SCAN_EXPR(carry, tmp);
        }

        local_barrier();

        if (LID_0 != 0)
            val = ldata[LID_0 - 1];
        /*
        else (see above)
            val = carry OR last tail;
        */

        if (i < interval_end)
            *output = val;

        if(LID_0 == 0)
            val = ldata[WG_SIZE - 1];

        local_barrier();
    }
}
""")




class _ScanKernelBase(object):
    def __init__(self, dtype,
            scan_expr, neutral=None,
            name_prefix="scan", options=[], preamble="", devices=None):

        if isinstance(self, ExclusiveScanKernel) and neutral is None:
            raise ValueError("neutral element is required for exclusive scan")

        dtype = self.dtype = np.dtype(dtype)
        self.neutral = neutral

        # Thrust says these are good for GT200
        self.scan_wg_size = 128
        self.update_wg_size = 256
        self.scan_wg_seq_batches = 6

        kw_values = dict(
            preamble=preamble,
            name_prefix=name_prefix,
            scan_type=dtype_to_ctype(dtype),
            scan_expr=scan_expr,
            neutral=neutral)

        scan_intervals_src = str(SCAN_INTERVALS_SOURCE.render(
            wg_size=self.scan_wg_size,
            wg_seq_batches=self.scan_wg_seq_batches,
            **kw_values))
        scan_intervals_prg = SourceModule(
                scan_intervals_src, options=options, no_extern_c=True)
        self.scan_intervals_knl = scan_intervals_prg.get_function(
                name_prefix+"_scan_intervals")
        self.scan_intervals_knl.prepare("PIIPP")

        final_update_src = str(self.final_update_tp.render(
            wg_size=self.update_wg_size,
            **kw_values))

        final_update_prg = SourceModule(
                final_update_src, options=options, no_extern_c=True)
        self.final_update_knl = final_update_prg.get_function(
                name_prefix+"_final_update")
        self.final_update_knl.prepare("PIIP")

    def __call__(self, input_ary, output_ary=None, allocator=None,
            stream=None):
        allocator = allocator or input_ary.allocator

        if output_ary is None:
            output_ary = input_ary

        if isinstance(output_ary, (str, unicode)) and output_ary == "new":
            output_ary = gpuarray.empty_like(input_ary, allocator=allocator)

        if input_ary.shape != output_ary.shape:
            raise ValueError("input and output must have the same shape")

        if not input_ary.flags.forc:
            raise RuntimeError("ScanKernel cannot "
                    "deal with non-contiguous arrays")

        n, = input_ary.shape

        if not n:
            return output_ary

        unit_size  = self.scan_wg_size * self.scan_wg_seq_batches
        dev = driver.Context.get_device()
        max_groups = 3*dev.get_attribute(
                driver.device_attribute.MULTIPROCESSOR_COUNT)

        from pytools import uniform_interval_splitting
        interval_size, num_groups = uniform_interval_splitting(
                n, unit_size, max_groups);

        block_results = allocator(self.dtype.itemsize*num_groups)
        dummy_results = allocator(self.dtype.itemsize)

        # first level scan of interval (one interval per block)
        self.scan_intervals_knl.prepared_async_call(
                (num_groups, 1), (self.scan_wg_size, 1, 1), stream,
                input_ary.gpudata,
                n, interval_size,
                output_ary.gpudata,
                block_results)

        # second level inclusive scan of per-block results
        self.scan_intervals_knl.prepared_async_call(
                (1,1), (self.scan_wg_size, 1, 1), stream,
                block_results,
                num_groups, interval_size,
                block_results,
                dummy_results)

        # update intervals with result of second level scan
        self.final_update_knl.prepared_async_call(
                (num_groups, 1,), (self.update_wg_size, 1, 1), stream,
                output_ary.gpudata,
                n, interval_size,
                block_results)

        return output_ary




class InclusiveScanKernel(_ScanKernelBase):
    final_update_tp = INCLUSIVE_UPDATE_SOURCE

class ExclusiveScanKernel(_ScanKernelBase):
    final_update_tp = EXCLUSIVE_UPDATE_SOURCE

########NEW FILE########
__FILENAME__ = cg
from __future__ import division
from pycuda.sparse.inner import AsyncInnerProduct
from pytools import memoize_method
import pycuda.gpuarray as gpuarray

import numpy as np




class ConvergenceError(RuntimeError):
    pass



class CGStateContainer:
    def __init__(self, operator, precon=None, pagelocked_allocator=None):
        if precon is None:
            from pycuda.sparse.operator import IdentityOperator
            precon = IdentityOperator(operator.dtype, operator.shape[0])

        self.operator = operator
        self.precon = precon

        self.pagelocked_allocator = pagelocked_allocator

    @memoize_method
    def make_lc2_kernel(self, dtype, a_is_gpu, b_is_gpu):
        from pycuda.elementwise import get_linear_combination_kernel
        return get_linear_combination_kernel((
                (a_is_gpu, dtype, dtype),
                (b_is_gpu, dtype, dtype)
                ), dtype)

    def lc2(self, a, x, b, y, out=None):
        if out is None:
            out = gpuarray.empty(x.shape, dtype=x.dtype,
                    allocator=x.allocator)

        assert x.dtype == y.dtype == out.dtype
        a_is_gpu = isinstance(a, gpuarray.GPUArray)
        b_is_gpu = isinstance(b, gpuarray.GPUArray)
        assert x.shape == y.shape == out.shape

        kernel, texrefs = self.make_lc2_kernel(
                x.dtype, a_is_gpu, b_is_gpu)

        texrefs = texrefs[:]

        args = []

        if a_is_gpu:
            assert a.dtype == x.dtype
            assert a.shape == ()
            a.bind_to_texref_ext(texrefs.pop(0), allow_double_hack=True)
        else:
            args.append(a)
        args.append(x.gpudata)

        if b_is_gpu:
            assert b.dtype == y.dtype
            assert b.shape == ()
            b.bind_to_texref_ext(texrefs.pop(0), allow_double_hack=True)
        else:
            args.append(b)
        args.append(y.gpudata)
        args.append(out.gpudata)
        args.append(x.mem_size)

        kernel.prepared_call(x._grid, x._block, *args)

        return out

    @memoize_method
    def guarded_div_kernel(self, dtype_x, dtype_y, dtype_z):
        from pycuda.elementwise import get_elwise_kernel
        from pycuda.tools import dtype_to_ctype
        return get_elwise_kernel(
                "%(tp_x)s *x, %(tp_y)s *y, %(tp_z)s *z" % {
                    "tp_x": dtype_to_ctype(dtype_x),
                    "tp_y": dtype_to_ctype(dtype_y),
                    "tp_z": dtype_to_ctype(dtype_z),
                    },
                "z[i] = y[i] == 0 ? 0 : (x[i] / y[i])",
                "divide")

    def guarded_div(self, a, b):
        from pycuda.gpuarray import _get_common_dtype
        result = a._new_like_me(_get_common_dtype(a, b))

        assert a.shape == b.shape

        func = self.guarded_div_kernel(a.dtype, b.dtype, result.dtype)
        func.prepared_async_call(a._grid, a._block, None,
                a.gpudata, b.gpudata,
                result.gpudata, a.mem_size)

        return result

    def reset(self, rhs, x=None):
        self.rhs = rhs

        if x is None:
            x = np.zeros((self.operator.shape[0],))
        self.x = x

        self.residual = rhs - self.operator(x)

        self.d = self.precon(self.residual)

        # grows at the end
        delta = AsyncInnerProduct(self.residual, self.d,
                self.pagelocked_allocator)
        self.real_delta_queue = [delta]
        self.delta = delta.gpu_result

    def one_iteration(self, compute_real_residual=False):
        # typed up from J.R. Shewchuk,
        # An Introduction to the Conjugate Gradient Method
        # Without the Agonizing Pain, Edition 1 1/4 [8/1994]
        # Appendix B3

        q = self.operator(self.d)
        myip = gpuarray.dot(self.d, q)
        alpha = self.guarded_div(self.delta, myip)

        self.lc2(1, self.x, alpha, self.d, out=self.x)

        if compute_real_residual:
            self.residual = self.lc2(
                    1, self.rhs, -1, self.operator(self.x))
        else:
            self.lc2(1, self.residual, -alpha, q, out=self.residual)

        s = self.precon(self.residual)
        delta_old = self.delta
        delta = AsyncInnerProduct(self.residual, s,
                self.pagelocked_allocator)
        self.delta = delta.gpu_result
        beta = self.guarded_div(self.delta, delta_old)

        self.lc2(1, s, beta, self.d, out=self.d)

        if compute_real_residual:
            self.real_delta_queue.append(delta)

    def run(self, max_iterations=None, tol=1e-7, debug_callback=None):
        check_interval = 20

        if max_iterations is None:
            max_iterations = max(
                    3*check_interval+1, 10 * self.operator.shape[0])
        real_resid_interval = min(self.operator.shape[0], 50)

        iterations = 0
        delta_0 = None
        while iterations < max_iterations:
            compute_real_residual = \
                    iterations % real_resid_interval == 0

            self.one_iteration(
                    compute_real_residual=compute_real_residual)

            if debug_callback is not None:
                if compute_real_residual:
                    what = "it+residual"
                else:
                    what = "it"

                debug_callback(what, iterations, self.x,
                        self.residual, self.d, self.delta)

            # do often enough to allow AsyncInnerProduct
            # to progress through (polled) event chain
            rdq = self.real_delta_queue
            if iterations % check_interval == 0:
                if delta_0 is None:
                    delta_0 = rdq[0].get_host_result()
                    if delta_0 is not None:
                        rdq.pop(0)

                if delta_0 is not None:
                    i = 0
                    while i < len(rdq):
                        delta = rdq[i].get_host_result()
                        if delta is not None:
                            if abs(delta) < tol*tol * abs(delta_0):
                                if debug_callback is not None:
                                    debug_callback("end", iterations,
                                            self.x, self.residual,
                                            self.d, self.delta)
                                return self.x
                            rdq.pop(i)
                        else:
                            i += 1

            iterations += 1

        raise ConvergenceError("cg failed to converge")




def solve_pkt_with_cg(pkt_spmv, b, precon=None, x=None, tol=1e-7, max_iterations=None,
        debug=False, pagelocked_allocator=None):
    if x is None:
        x = gpuarray.zeros(pkt_spmv.shape[0], dtype=pkt_spmv.dtype,
                allocator=b.allocator)
    else:
        x = pkt_spmv.permute(x)

    if pagelocked_allocator is None:
        pagelocked_allocator = drv.pagelocked_empty

    cg = CGStateContainer(pkt_spmv, precon,
            pagelocked_allocator=pagelocked_allocator)

    cg.reset(pkt_spmv.permute(b), x)

    it_count = [0]
    res_count = [0]
    def debug_callback(what, it_number, x, resid, d, delta):
        if what == "it":
            it_count[0] += 1
        elif what == "it+residual":
            res_count[0] += 1
            it_count[0] += 1

    result = cg.run(max_iterations, tol,
            debug_callback=debug_callback)

    return pkt_spmv.unpermute(result), it_count[0], res_count[0]





########NEW FILE########
__FILENAME__ = coordinate
from __future__ import division
from pytools import memoize_method
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
from pycuda.compiler import SourceModule
import numpy as np




COO_FLAT_KERNEL_TEMPLATE = """
#include <pycuda-helpers.hpp>

#define BLOCK_SIZE %(block_size)d
#define WARP_SIZE %(warp_size)d

typedef %(value_type)s value_type;
typedef %(index_type)s index_type;

texture<%(tex_value_type)s, 1, cudaReadModeElementType> tex_x;

static __inline__ __device__ float atomicAdd(float *addr, float val)
{
    float old=*addr, assumed;

    do {
        assumed = old;
        old = int_as_float( atomicCAS((int*)addr,
                                        float_as_int(assumed),
                                        float_as_int(val+assumed)));
    } while( assumed!=old );

    return old;
}

#ifndef CUDA_NO_SM_13_DOUBLE_INTRINSICS
static __attribute__ ((unused)) __inline__ __device__ double atomicAdd(double *addr, double val)
{
    double old=*addr, assumed;

    do {
        assumed = old;
        old = __longlong_as_double( atomicCAS((unsigned long long int*)addr,
                                        __double_as_longlong(assumed),
                                        __double_as_longlong(val+assumed)));
    } while( assumed!=old );

    return old;
}
#endif

__global__ void
spmv_coo_flat_kernel(const index_type num_nonzeros,
                     const index_type interval_size,
                     const index_type *I,
                     const index_type *J,
                     const value_type *V,
                           value_type *y)
{
  __shared__ index_type idx[BLOCK_SIZE];
  __shared__ value_type val[BLOCK_SIZE];
  __shared__ index_type carry_idx[BLOCK_SIZE / 32];
  __shared__ value_type carry_val[BLOCK_SIZE / 32];

  const index_type thread_id   = BLOCK_SIZE * blockIdx.x + threadIdx.x;     // global thread index
  const index_type thread_lane = threadIdx.x & (WARP_SIZE-1);               // thread index within the warp
  const index_type warp_id     = thread_id   / WARP_SIZE;                   // global warp index
  const index_type warp_lane   = threadIdx.x / WARP_SIZE;                   // warp index within the CTA

  const index_type begin = warp_id * interval_size + thread_lane;           // thread's offset into I,J,V
  const index_type end   = min(begin + interval_size, num_nonzeros);        // end of thread's work

  if(begin >= end) return;                                                 // warp has no work to do

  const index_type first_idx = I[warp_id * interval_size];                  // first row of this warp's interval

  if (thread_lane == 0)
  {
    carry_idx[warp_lane] = first_idx;
    carry_val[warp_lane] = 0;
  }

  for(index_type n = begin; n < end; n += WARP_SIZE)
  {
    idx[threadIdx.x] = I[n];                                             // row index
    val[threadIdx.x] = V[n] * fp_tex1Dfetch(tex_x, J[n]);                // val = A[row,col] * x[col]

    if (thread_lane == 0){
      if(idx[threadIdx.x] == carry_idx[warp_lane])
          val[threadIdx.x] += carry_val[warp_lane];                    // row continues into this warp's span
      else if(carry_idx[warp_lane] != first_idx)
          y[carry_idx[warp_lane]] += carry_val[warp_lane];             // row terminated, does not span boundary
      else
          atomicAdd(y + carry_idx[warp_lane], carry_val[warp_lane]);   // row terminated, but spans iter-warp boundary
    }

    // segmented reduction in shared memory
    if( thread_lane >=  1 && idx[threadIdx.x] == idx[threadIdx.x - 1] ) { val[threadIdx.x] += val[threadIdx.x -  1]; }
    if( thread_lane >=  2 && idx[threadIdx.x] == idx[threadIdx.x - 2] ) { val[threadIdx.x] += val[threadIdx.x -  2]; }
    if( thread_lane >=  4 && idx[threadIdx.x] == idx[threadIdx.x - 4] ) { val[threadIdx.x] += val[threadIdx.x -  4]; }
    if( thread_lane >=  8 && idx[threadIdx.x] == idx[threadIdx.x - 8] ) { val[threadIdx.x] += val[threadIdx.x -  8]; }
    if( thread_lane >= 16 && idx[threadIdx.x] == idx[threadIdx.x -16] ) { val[threadIdx.x] += val[threadIdx.x - 16]; }

    if( thread_lane == 31 ) {
      carry_idx[warp_lane] = idx[threadIdx.x];                         // last thread in warp saves its results
      carry_val[warp_lane] = val[threadIdx.x];
    }
    else if ( idx[threadIdx.x] != idx[threadIdx.x+1] ) {                 // row terminates here
      if(idx[threadIdx.x] != first_idx)
          y[idx[threadIdx.x]] += val[threadIdx.x];                     // row terminated, does not span inter-warp boundary
      else
          atomicAdd(y + idx[threadIdx.x], val[threadIdx.x]);           // row terminated, but spans iter-warp boundary
    }
  }

  // final carry
  if(thread_lane == 31){
    atomicAdd(y + carry_idx[warp_lane], carry_val[warp_lane]);
  }
}
"""



COO_SERIAL_KERNEL_TEMPLATE = """
typedef %(value_type)s value_type;
typedef %(index_type)s index_type;

__global__ void
spmv_coo_serial_kernel(const index_type num_nonzeros,
                       const index_type *I,
                       const index_type *J,
                       const value_type *V,
                       const value_type *x,
                             value_type *y)
{
  for (index_type n = 0; n < num_nonzeros; n++)
    y[I[n]] += V[n] * x[J[n]];
}
"""




class CoordinateSpMV:
    def __init__(self, mat, dtype):
        self.dtype = np.dtype(dtype)
        self.index_dtype = np.dtype(np.int32)
        self.shape = mat.shape

        self.block_size = 128

        from scipy.sparse import coo_matrix
        coo_mat = coo_matrix(mat, dtype=self.dtype)

        self.row_gpu = gpuarray.to_gpu(coo_mat.row.astype(self.index_dtype))
        self.col_gpu = gpuarray.to_gpu(coo_mat.col.astype(self.index_dtype))
        self.data_gpu = gpuarray.to_gpu(coo_mat.data)
        self.nnz = coo_mat.nnz

        from pycuda.tools import DeviceData
        dev = drv.Context.get_device()
        devdata = DeviceData()
        max_threads = (devdata.warps_per_mp*devdata.warp_size*
                dev.multiprocessor_count)
        max_blocks = 4*max_threads // self.block_size
        warps_per_block = self.block_size // dev.warp_size

        if self.nnz:
            def divide_into(x, y):
                return (x+y-1)//y

            num_units  = self.nnz // dev.warp_size
            num_warps  = min(num_units, warps_per_block * max_blocks)
            self.num_blocks = divide_into(num_warps, warps_per_block)
            num_iters  = divide_into(num_units, num_warps)

            self.interval_size = dev.warp_size * num_iters
            self.tail = num_units * dev.warp_size


    @memoize_method
    def get_flat_kernel(self):
        from pycuda.tools import dtype_to_ctype

        mod = SourceModule(
                COO_FLAT_KERNEL_TEMPLATE % {
                    "value_type": dtype_to_ctype(self.dtype),
                    "tex_value_type": dtype_to_ctype(
                        self.dtype, with_fp_tex_hack=True),
                    "index_type": dtype_to_ctype(self.index_dtype),
                    "block_size": self.block_size,
                    "warp_size": drv.Context.get_device().warp_size,
                    })
        func = mod.get_function("spmv_coo_flat_kernel")
        x_texref = mod.get_texref("tex_x")
        func.prepare(self.index_dtype.char*2 + "PPPP",
            (self.block_size, 1, 1), texrefs=[x_texref])
        return func, x_texref

    @memoize_method
    def get_serial_kernel(self):
        from pycuda.tools import dtype_to_ctype

        mod = SourceModule(
                COO_SERIAL_KERNEL_TEMPLATE % {
                    "value_type": dtype_to_ctype(self.dtype),
                    "index_type": dtype_to_ctype(self.index_dtype),
                    })
        func = mod.get_function("spmv_coo_serial_kernel")
        func.prepare(self.index_dtype.char + "PPPPP", (1, 1, 1))
        return func

    def __call__(self, x, y=None):
        if y is None:
            y = gpuarray.zeros(self.shape[0], dtype=self.dtype,
                    allocator=x.allocator)

        if self.nnz == 0:
            return y

        flat_func, x_texref = self.get_flat_kernel()
        x.bind_to_texref_ext(x_texref, allow_double_hack=True)
        flat_func.prepared_call((self.num_blocks, 1),
                self.tail, self.interval_size,
                self.row_gpu.gpudata,
                self.col_gpu.gpudata,
                self.data_gpu.gpudata,
                y.gpudata)

        self.get_serial_kernel().prepared_call(
                (1, 1),
                self.nnz - self.tail,
                self.row_gpu[self.tail:].gpudata,
                self.col_gpu[self.tail:].gpudata,
                self.data_gpu[self.tail:].gpudata,
                x.gpudata, y.gpudata)

        return y

########NEW FILE########
__FILENAME__ = inner
from __future__ import division
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray




STREAM_POOL = []




def get_stream():
    if STREAM_POOL:
        return STREAM_POOL.pop()
    else:
        return drv.Stream()





class AsyncInnerProduct:
    def __init__(self, a, b, pagelocked_allocator):
        self.gpu_result = gpuarray.dot(a, b)
        self.gpu_finished_evt = drv.Event()
        self.gpu_finished_evt.record()
        self.gpu_finished = False

        self.pagelocked_allocator = pagelocked_allocator

    def get_host_result(self):
        if not self.gpu_finished:
            if self.gpu_finished_evt.query():
                self.gpu_finished = True
                self.copy_stream = get_stream()
                self.host_dest = self.pagelocked_allocator(
                        self.gpu_result.shape, self.gpu_result.dtype,
                        self.copy_stream)
                drv.memcpy_dtoh_async(self.host_dest,
                        self.gpu_result.gpudata,
                        self.copy_stream)
                self.copy_finished_evt = drv.Event()
                self.copy_finished_evt.record()
        else:
            if self.copy_finished_evt.query():
                STREAM_POOL.append(self.copy_stream)
                return self.host_dest




def _at_exit():
    STREAM_POOL[:] = []

import atexit
atexit.register(_at_exit)


########NEW FILE########
__FILENAME__ = operator
class OperatorBase(object):
    @property
    def dtype(self):
        raise NotImplementedError

    @property
    def shape(self):
        raise NotImplementedError

    def __neg__(self):
        return NegOperator(self)




class IdentityOperator(OperatorBase):
    def __init__(self, dtype, n):
        self.my_dtype = dtype
        self.n = n

    @property
    def dtype(self):
        return self.my_dtype

    @property
    def shape(self):
        return self.n, self.n

    def __call__(self, operand):
        return operand




class DiagonalPreconditioner(OperatorBase):
    def __init__(self, diagonal):
        self.diagonal = diagonal

    @property
    def dtype(self):
        return self.diagonal.dtype

    @property
    def shape(self):
        n = self.diagonal.shape[0]
        return n, n

    def __call__(self, operand):
        return self.diagonal*operand





########NEW FILE########
__FILENAME__ = packeted
from __future__ import division
from pytools import memoize_method
import pycuda.driver as drv
import pycuda.gpuarray as gpuarray
from pycuda.compiler import SourceModule
import numpy as np




PKT_KERNEL_TEMPLATE = """
typedef %(index_type)s index_type;
typedef %(value_type)s value_type;
typedef %(packed_index_type)s packed_index_type;

#define ROWS_PER_PACKET %(rows_per_packet)d
#define THREADS_PER_PACKET %(threads_per_packet)d

template <typename IndexType, typename ValueType>
__device__ void memcpy_device(
  ValueType *dest, const ValueType *src,
  const IndexType num_values)
{
  for(unsigned int i = threadIdx.x; i < num_values; i += blockDim.x)
  {
    dest[i] = src[i];
  }
}

#define pkt_unpack_row_index(packed_index) ( packed_index >> 16  )
#define pkt_unpack_col_index(packed_index) (packed_index & 0xFFFF)

extern "C" {
__global__ void
spmv_pkt_kernel(const index_type *row_ptr,
                const index_type *pos_start,
                const index_type *pos_end,
                const packed_index_type *index_array,
                const value_type *data_array,
                const value_type *x,
                      value_type *y)
{
  __shared__ value_type s_x[ROWS_PER_PACKET]; // input x-values
  __shared__ value_type s_y[ROWS_PER_PACKET]; // output y-values

  const index_type thread_id =
    __umul24(THREADS_PER_PACKET, blockIdx.x) + threadIdx.x;

  // base index of the submatrix corresponding to this packet
  const index_type packet_base_row = row_ptr[blockIdx.x];
  const index_type packet_num_rows = row_ptr[blockIdx.x+1] - packet_base_row;

  // copy local x and y values from global memory into shared memory
  memcpy_device(s_x, x + packet_base_row, packet_num_rows);
  memcpy_device(s_y, y + packet_base_row, packet_num_rows);

  __syncthreads();

  // process packet

  const index_type packet_start = pos_start[thread_id];
  const index_type packet_end = pos_end[thread_id];

  for(index_type pos = packet_start; pos != packet_end; pos += THREADS_PER_PACKET)
  {
    // row and column indices are stored in the same 32-bit word

    const index_type packed_index = index_array[pos];

    const index_type row = pkt_unpack_row_index(packed_index);
    const index_type col = pkt_unpack_col_index(packed_index);
    const value_type val = data_array[pos];

    s_y[row] += val * s_x[col];
  }

  __syncthreads();

  // copy y-values from shared memory to global array

  memcpy_device(y + packet_base_row, s_y, packet_num_rows);
}
}
"""




class PacketedSpMV:
    def __init__(self, mat, is_symmetric, dtype):
        from pycuda.tools import DeviceData
        devdata = DeviceData()

        # all row indices in the data structure generation code are
        # "unpermuted" unless otherwise specified
        self.dtype = np.dtype(dtype)
        self.index_dtype = np.int32
        self.packed_index_dtype = np.uint32
        self.threads_per_packet = devdata.max_threads

        h, w = self.shape = mat.shape
        if h != w:
            raise ValueError("only square matrices are supported")

        self.rows_per_packet = (devdata.shared_memory - 100) \
                // (2*self.dtype.itemsize)

        self.block_count = \
                (h + self.rows_per_packet - 1) // self.rows_per_packet

        # get metis partition -------------------------------------------------
        from scipy.sparse import csr_matrix
        csr_mat = csr_matrix(mat, dtype=self.dtype)

        from pymetis import part_graph
        if not is_symmetric:
            # make sure adjacency graph is undirected
            adj_mat = csr_mat + csr_mat.T
        else:
            adj_mat = csr_mat

        while True:
            cut_count, dof_to_packet_nr = part_graph(int(self.block_count),
                    xadj=adj_mat.indptr, adjncy=adj_mat.indices)

            # build packet_nr_to_dofs
            packet_nr_to_dofs = {}
            for i, packet_nr in enumerate(dof_to_packet_nr):
                try:
                    dof_packet = packet_nr_to_dofs[packet_nr]
                except KeyError:
                    packet_nr_to_dofs[packet_nr] = dof_packet = []

                dof_packet.append(i)

            packet_nr_to_dofs = [packet_nr_to_dofs.get(i)
                    for i in range(len(packet_nr_to_dofs))]

            too_big = False
            for packet_dofs in packet_nr_to_dofs:
                if len(packet_dofs) >= self.rows_per_packet:
                    too_big = True
                    break

            if too_big:
                old_block_count = self.block_count
                self.block_count = int(2+1.05*self.block_count)
                print ("Metis produced a big block at block count "
                        "%d--retrying with %d"
                        % (old_block_count, self.block_count))
                continue

            break

        assert len(packet_nr_to_dofs) == self.block_count

        # permutations, base rows ---------------------------------------------
        new2old_fetch_indices, \
                old2new_fetch_indices, \
                packet_base_rows = self.find_simple_index_stuff(
                        packet_nr_to_dofs)

        # find local row cost and remaining_coo -------------------------------
        local_row_costs, remaining_coo = \
                self.find_local_row_costs_and_remaining_coo(
                        csr_mat, dof_to_packet_nr, old2new_fetch_indices)
        local_nnz = np.sum(local_row_costs)

        assert remaining_coo.nnz == csr_mat.nnz - local_nnz

        # find thread assignment for each block -------------------------------
        thread_count = len(packet_nr_to_dofs)*self.threads_per_packet
        thread_assignments, thread_costs = self.find_thread_assignment(
                packet_nr_to_dofs, local_row_costs, thread_count)

        max_thread_costs = np.max(thread_costs)

        # build data structure ------------------------------------------------
        from pkt_build import build_pkt_data_structure
        build_pkt_data_structure(self, packet_nr_to_dofs, max_thread_costs,
            old2new_fetch_indices, csr_mat, thread_count, thread_assignments,
            local_row_costs)

        self.packet_base_rows = gpuarray.to_gpu(packet_base_rows)
        self.new2old_fetch_indices = gpuarray.to_gpu(
                new2old_fetch_indices)
        self.old2new_fetch_indices = gpuarray.to_gpu(
                old2new_fetch_indices)

        from coordinate import CoordinateSpMV
        self.remaining_coo_gpu = CoordinateSpMV(
                remaining_coo, dtype)

    def find_simple_index_stuff(self, packet_nr_to_dofs):
        new2old_fetch_indices = np.zeros(
                self.shape[0], dtype=self.index_dtype)
        old2new_fetch_indices = np.zeros(
                self.shape[0], dtype=self.index_dtype)

        packet_base_rows = np.zeros(
                self.block_count+1,
                dtype=self.index_dtype)

        row_start = 0
        for packet_nr, packet in enumerate(packet_nr_to_dofs):
            packet_base_rows[packet_nr] = row_start
            row_end = row_start + len(packet)

            pkt_indices = np.array(packet, dtype=self.index_dtype)
            new2old_fetch_indices[row_start:row_end] = \
                    pkt_indices
            old2new_fetch_indices[pkt_indices] = \
                    np.arange(row_start, row_end, dtype=self.index_dtype)

            row_start += len(packet)

        packet_base_rows[self.block_count] = row_start

        return (new2old_fetch_indices, old2new_fetch_indices,
                packet_base_rows)

    def find_local_row_costs_and_remaining_coo(self, csr_mat, dof_to_packet_nr,
            old2new_fetch_indices):
        h, w = self.shape
        local_row_costs = [0]*h
        rem_coo_values = []
        rem_coo_i = []
        rem_coo_j = []

        iptr = csr_mat.indptr
        indices = csr_mat.indices
        data = csr_mat.data

        for i in xrange(h):
            for idx in xrange(iptr[i], iptr[i+1]):
                j = indices[idx]

                if dof_to_packet_nr[i] == dof_to_packet_nr[j]:
                    local_row_costs[i] += 1
                else:
                    rem_coo_values.append(data[idx])
                    rem_coo_i.append(old2new_fetch_indices[i])
                    rem_coo_j.append(old2new_fetch_indices[j])

        from scipy.sparse import coo_matrix
        remaining_coo = coo_matrix(
                (rem_coo_values, (rem_coo_i, rem_coo_j)), self.shape,
                dtype=self.dtype)

        return local_row_costs, remaining_coo

    def find_thread_assignment(self, packet_nr_to_dofs, local_row_cost,
            thread_count):
        thread_assignments = [[] for i in range(thread_count)]
        thread_costs = np.zeros(thread_count)

        for packet_nr, packet_dofs in enumerate(packet_nr_to_dofs):
            row_costs_and_numbers = sorted(
                    [(local_row_cost[i], i) for i in packet_dofs],
                    reverse=True)

            base_thread_nr = packet_nr*self.threads_per_packet
            thread_offset = 0

            # zigzag assignment
            step = 1
            for row_cost, row_number in row_costs_and_numbers:
                ti = base_thread_nr+thread_offset
                thread_assignments[ti].append(row_number)
                thread_costs[ti] += row_cost

                if thread_offset + step >= self.threads_per_packet:
                    step = -1
                elif thread_offset + step < 0:
                    step = 1
                else:
                    thread_offset += step

        return thread_assignments, thread_costs

    def build_gpu_data_structure(self, packet_nr_to_dofs, max_thread_costs,
            old2new_fetch_indices, csr_mat, thread_count, thread_assignments,
            local_row_costs):
        # these arrays will likely be too long, but that's ok

        from pkt_build import build_pkt_structure
        build_pkt_structure(self, packet_nr_to_dofs, thread_assignments,
                thread_starts, thread_ends, index_array, data_array)



        # copy data to the gpu ------------------------------------------------

    # execution ---------------------------------------------------------------
    @memoize_method
    def get_kernel(self):
        from pycuda.tools import dtype_to_ctype

        mod = SourceModule(
                PKT_KERNEL_TEMPLATE % {
                    "value_type": dtype_to_ctype(self.dtype),
                    "index_type": dtype_to_ctype(self.index_dtype),
                    "packed_index_type": dtype_to_ctype(self.packed_index_dtype),
                    "threads_per_packet": self.threads_per_packet,
                    "rows_per_packet": self.rows_per_packet,
                    }, no_extern_c=True)
        func = mod.get_function("spmv_pkt_kernel")
        func.prepare("PPPPPPP")
        return func

    def permute(self, x):
        return gpuarray.take(x, self.new2old_fetch_indices)

    def unpermute(self, x):
        return gpuarray.take(x, self.old2new_fetch_indices)

    def __call__(self, x, y=None):
        if y is None:
            y = gpuarray.zeros(self.shape[0], dtype=self.dtype,
                    allocator=x.allocator)

        self.get_kernel().prepared_call(
                (self.block_count, 1),
                (self.threads_per_packet, 1, 1),
                self.packet_base_rows.gpudata,
                self.thread_starts.gpudata,
                self.thread_ends.gpudata,
                self.index_array.gpudata,
                self.data_array.gpudata,
                x.gpudata,
                y.gpudata)

        self.remaining_coo_gpu(x, y)

        return y


########NEW FILE########
__FILENAME__ = pkt_build
import numpy as np
import pycuda.gpuarray as gpuarray




def build_pkt_data_structure(spmv, packet_nr_to_dofs, max_thread_costs,
        old2new_fetch_indices, csr_mat, thread_count, thread_assignments,
        local_row_costs):
    packet_start = 0
    base_dof_nr = 0

    index_array = np.zeros(
            max_thread_costs*thread_count, dtype=spmv.packed_index_dtype)
    data_array = np.zeros(
            max_thread_costs*thread_count, dtype=spmv.dtype)
    thread_starts = np.zeros(
            thread_count, dtype=spmv.index_dtype)
    thread_ends = np.zeros(
            thread_count, dtype=spmv.index_dtype)

    for packet_nr, packet_dofs in enumerate(packet_nr_to_dofs):
        base_thread_nr = packet_nr*spmv.threads_per_packet
        max_packet_items = 0

        for thread_offset in range(spmv.threads_per_packet):
            thread_write_idx = packet_start+thread_offset
            thread_start = packet_start+thread_offset
            thread_starts[base_thread_nr+thread_offset] = thread_write_idx

            for row_nr in thread_assignments[base_thread_nr+thread_offset]:
                perm_row_nr = old2new_fetch_indices[row_nr]
                rel_row_nr = perm_row_nr - base_dof_nr
                assert 0 <= rel_row_nr < len(packet_dofs)

                row_entries = 0

                for idx in range(csr_mat.indptr[row_nr], csr_mat.indptr[row_nr+1]):
                    col_nr = csr_mat.indices[idx]

                    perm_col_nr = old2new_fetch_indices[col_nr]
                    rel_col_nr = perm_col_nr - base_dof_nr

                    if 0 <= rel_col_nr < len(packet_dofs):
                        index_array[thread_write_idx] = (rel_row_nr << 16) + rel_col_nr
                        data_array[thread_write_idx] = csr_mat.data[idx]
                        thread_write_idx += spmv.threads_per_packet
                        row_entries += 1

                assert row_entries == local_row_costs[row_nr]

            thread_ends[base_thread_nr+thread_offset] = thread_write_idx

            thread_items = (thread_write_idx - thread_start)//spmv.threads_per_packet
            max_packet_items = max(
                    max_packet_items, thread_items)

        base_dof_nr += len(packet_dofs)
        packet_start += max_packet_items*spmv.threads_per_packet

    spmv.thread_starts = gpuarray.to_gpu(thread_starts)
    spmv.thread_ends = gpuarray.to_gpu(thread_ends)
    spmv.index_array = gpuarray.to_gpu(index_array)
    spmv.data_array = gpuarray.to_gpu(data_array)




try:
    import pyximport
except ImportError:
    pass
else:
    pyximport.install()
    from pycuda.sparse.pkt_build_cython import build_pkt_data_structure

########NEW FILE########
__FILENAME__ = tools
"""Miscallenous helper functionality."""

from __future__ import division

__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import pycuda.driver as cuda
from decorator import decorator
import pycuda._driver as _drv
import numpy as np




bitlog2 = _drv.bitlog2
DeviceMemoryPool = _drv.DeviceMemoryPool
PageLockedMemoryPool = _drv.PageLockedMemoryPool

from pycuda.compyte.dtypes import (
        register_dtype, get_or_register_dtype, _fill_dtype_registry,
        dtype_to_ctype as base_dtype_to_ctype)

_fill_dtype_registry(respect_windows=True)
get_or_register_dtype("pycuda::complex<float>", np.complex64)
get_or_register_dtype("pycuda::complex<double>", np.complex128)




# {{{ debug memory pool

class DebugMemoryPool(DeviceMemoryPool):
    def __init__(self, interactive=True, logfile=None):
        DeviceMemoryPool.__init__(self)
        self.last_free, _ = cuda.mem_get_info()
        self.interactive = interactive

        if logfile is None:
            import sys
            logfile = sys.stdout

        self.logfile = logfile

        from weakref import WeakKeyDictionary
        self.blocks = WeakKeyDictionary()

        if interactive:
            from pytools.diskdict import DiskDict
            self.stacktrace_mnemonics = DiskDict("pycuda-stacktrace-mnemonics")

    def allocate(self, size):
        from traceback import extract_stack
        stack = tuple(frm[2] for frm in extract_stack())
        description = self.describe(stack, size)

        histogram = {}
        for bsize, descr in self.blocks.itervalues():
            histogram[bsize, descr] = histogram.get((bsize, descr), 0) + 1

        from pytools import common_prefix
        cpfx = common_prefix(descr for bsize, descr in histogram)

        print >> self.logfile, \
                "\n  Allocation of size %d occurring " \
                "(mem: last_free:%d, free: %d, total:%d) (pool: held:%d, active:%d):" \
                "\n      at: %s" % (
                (size, self.last_free)
                + cuda.mem_get_info()
                + (self.held_blocks, self.active_blocks,
                    description))

        hist_items = sorted(list(histogram.iteritems()))
        for (bsize, descr), count in hist_items:
            print >> self.logfile, \
                    "  %s (%d bytes): %dx" % (descr[len(cpfx):], bsize, count)

        if self.interactive:
            raw_input("  [Enter]")

        result = DeviceMemoryPool.allocate(self, size)
        self.blocks[result] = size, description
        self.last_free, _ = cuda.mem_get_info()
        return result

    def describe(self, stack, size):
        if not self.interactive:
            return "|".join(stack)
        else:
            try:
                return self.stacktrace_mnemonics[stack, size]
            except KeyError:
                print size, stack
                while True:
                    mnemonic = raw_input("Enter mnemonic or [Enter] for more info:")
                    if mnemonic == '':
                        from traceback import print_stack
                        print_stack()
                    else:
                        break
                self.stacktrace_mnemonics[stack, size] = mnemonic
                return mnemonic

# }}}

# {{{ default device/context

def get_default_device(default=0):
    from warnings import warn
    warn("get_default_device() is deprecated; "
            "use make_default_context() instead", DeprecationWarning)

    from pycuda.driver import Device
    import os
    dev = os.environ.get("CUDA_DEVICE")

    if dev is None:
        try:
            dev = (open(os.path.join(os.path.expanduser("~"), ".cuda_device"))
                    .read().strip())
        except:
            pass

    if dev is None:
        dev = default

    try:
        dev = int(dev)
    except TypeError:
        raise TypeError("CUDA device number (CUDA_DEVICE or ~/.cuda-device) must be an integer")

    return Device(dev)




def make_default_context(ctx_maker=None):
    if ctx_maker is None:
        def ctx_maker(dev):
            return dev.make_context()

    ndevices = cuda.Device.count()
    if ndevices == 0:
        raise RuntimeError("No CUDA enabled device found. "
                "Please check your installation.")

    # Is CUDA_DEVICE set?
    import os
    devn = os.environ.get("CUDA_DEVICE")

    # Is $HOME/.cuda_device set ?
    if devn is None:
        try:
            homedir = os.environ.get("HOME")
            assert homedir is not None
            devn = (open(os.path.join(homedir, ".cuda_device"))
                    .read().strip())
        except:
            pass

    # If either CUDA_DEVICE or $HOME/.cuda_device is set, try to use it
    if devn is not None:
        try:
            devn = int(devn)
        except TypeError:
            raise TypeError("CUDA device number (CUDA_DEVICE or ~/.cuda_device)"
                    " must be an integer")

        dev = cuda.Device(devn)
        return ctx_maker(dev)

    # Otherwise, try to use any available device
    else:
        for devn in xrange(ndevices):
            dev = cuda.Device(devn)
            try:
                return ctx_maker(dev)
            except cuda.Error:
                pass

        raise RuntimeError("make_default_context() wasn't able to create a context "
                "on any of the %d detected devices" % ndevices)

# }}}

# {{{ rounding helpers

def _exact_div(dividend, divisor):
    quot, rem = divmod(dividend, divisor)
    assert rem == 0
    return quot

def _int_ceiling(value, multiple_of=1):
    """Round C{value} up to be a C{multiple_of} something."""
    # Mimicks the Excel "floor" function (for code stolen from occupancy calculator)

    from math import ceil
    return int(ceil(value/multiple_of))*multiple_of

def _int_floor(value, multiple_of=1):
    """Round C{value} down to be a C{multiple_of} something."""
    # Mimicks the Excel "floor" function (for code stolen from occupancy calculator)

    from math import floor
    return int(floor(value/multiple_of))*multiple_of

# }}}

# {{{ device data

class DeviceData:
    def __init__(self, dev=None):
        import pycuda.driver as drv

        if dev is None:
            dev = cuda.Context.get_device()

        self.max_threads = dev.get_attribute(drv.device_attribute.MAX_THREADS_PER_BLOCK)
        self.warp_size = dev.get_attribute(drv.device_attribute.WARP_SIZE)

        if dev.compute_capability() >= (2,0):
            self.warps_per_mp = 48
        elif dev.compute_capability() >= (1,2):
            self.warps_per_mp = 32
        else:
            self.warps_per_mp = 24

        self.thread_blocks_per_mp = 8
        self.registers = dev.get_attribute(drv.device_attribute.MAX_REGISTERS_PER_BLOCK)
        self.shared_memory = dev.get_attribute(drv.device_attribute.MAX_SHARED_MEMORY_PER_BLOCK)

        if dev.compute_capability() >= (2,0):
            self.smem_alloc_granularity = 128
            self.smem_granularity = 32
        else:
            self.smem_alloc_granularity = 512
            self.smem_granularity = 16

        if dev.compute_capability() >= (2,0):
            self.register_allocation_unit = "warp"
        else:
            self.register_allocation_unit = "block"

    def align(self, bytes, word_size=4):
        return _int_ceiling(bytes, self.align_bytes(word_size))

    def align_dtype(self, elements, dtype_size):
        return _int_ceiling(elements,
                self.align_words(dtype_size))

    def align_words(self, word_size):
        return _exact_div(self.align_bytes(word_size), word_size)

    def align_bytes(self, word_size=4):
        if word_size == 4:
            return 64
        elif word_size == 8:
            return 128
        elif word_size == 16:
            return 128
        else:
            raise ValueError, "no alignment possible for fetches of size %d" % word_size

    def coalesce(self, thread_count):
        return _int_ceiling(thread_count, 16)

    @staticmethod
    def make_valid_tex_channel_count(size):
        valid_sizes = [1,2,4]
        for vs in valid_sizes:
            if size <= vs:
                return vs

        raise ValueError, "could not enlarge argument to valid channel count"

# }}}

# {{{ occupancy

class OccupancyRecord:
    def __init__(self, devdata, threads, shared_mem=0, registers=0):
        if threads > devdata.max_threads:
            raise ValueError("too many threads")

        # copied literally from occupancy calculator
        alloc_warps = _int_ceiling(threads/devdata.warp_size)
        alloc_smem = _int_ceiling(shared_mem, devdata.smem_alloc_granularity)
        if devdata.register_allocation_unit == "warp":
            alloc_regs = alloc_warps*32*registers
        elif devdata.register_allocation_unit == "block":
            alloc_regs = _int_ceiling(alloc_warps*2, 4)*16*registers
        else:
            raise ValueError("Improper register allocation unit:"+devdata.register_allocation_unit)

        if alloc_regs > devdata.registers:
            raise ValueError("too many registers")

        if alloc_smem > devdata.shared_memory:
            raise ValueError("too much smem")

        self.tb_per_mp_limits = [(devdata.thread_blocks_per_mp, "device"),
                (_int_floor(devdata.warps_per_mp/alloc_warps), "warps")
                ]
        if registers > 0:
            self.tb_per_mp_limits.append((_int_floor(devdata.registers/alloc_regs), "regs"))
        if shared_mem > 0:
            self.tb_per_mp_limits.append((_int_floor(devdata.shared_memory/alloc_smem), "smem"))

        self.tb_per_mp, self.limited_by = min(self.tb_per_mp_limits)

        self.warps_per_mp = self.tb_per_mp * alloc_warps
        self.occupancy = self.warps_per_mp / devdata.warps_per_mp

# }}}

# {{{ C types <-> dtypes

class Argument:
    def __init__(self, dtype, name):
        self.dtype = np.dtype(dtype)
        self.name = name

    def __repr__(self):
        return "%s(%r, %s)" % (
                self.__class__.__name__,
                self.name,
                self.dtype)


def dtype_to_ctype(dtype, with_fp_tex_hack=False):
    if dtype is None:
        raise ValueError("dtype may not be None")

    dtype = np.dtype(dtype)
    if with_fp_tex_hack:
        if dtype == np.float32:
            return "fp_tex_float"
        elif dtype == np.float64:
            return "fp_tex_double"
        elif dtype == np.complex64:
            return "fp_tex_cfloat"
        elif dtype == np.complex128:
            return "fp_tex_cdouble"

    return base_dtype_to_ctype(dtype)


class VectorArg(Argument):
    def declarator(self):
        return "%s *%s" % (dtype_to_ctype(self.dtype), self.name)

    struct_char = "P"

class ScalarArg(Argument):
    def declarator(self):
        return "%s %s" % (dtype_to_ctype(self.dtype), self.name)

    @property
    def struct_char(self):
        result = self.dtype.char
        if result == "V":
            result = "%ds" % self.dtype.itemsize

        return result




def parse_c_arg(c_arg):
    from pycuda.compyte.dtypes import parse_c_arg_backend
    return parse_c_arg_backend(c_arg, ScalarArg, VectorArg)

def get_arg_type(c_arg):
    return parse_c_arg(c_arg).struct_char

# }}}

# {{{ context-dep memoization

context_dependent_memoized_functions = []




@decorator
def context_dependent_memoize(func, *args):
    try:
        ctx_dict = func._pycuda_ctx_dep_memoize_dic
    except AttributeError:
        # FIXME: This may keep contexts alive longer than desired.
        # But I guess since the memory in them is freed, who cares.
        ctx_dict = func._pycuda_ctx_dep_memoize_dic = {}

    cur_ctx = cuda.Context.get_current()

    try:
        return ctx_dict[cur_ctx][args]
    except KeyError:
        context_dependent_memoized_functions.append(func)
        arg_dict = ctx_dict.setdefault(cur_ctx, {})
        result = func(*args)
        arg_dict[args] = result
        return result



def clear_context_caches():
    for func in context_dependent_memoized_functions:
        try:
            ctx_dict = func._pycuda_ctx_dep_memoize_dic
        except AttributeError:
            pass
        else:
            ctx_dict.clear()

# }}}

# {{{ py.test interaction

def mark_cuda_test(inner_f):
    def f(*args, **kwargs):
        import pycuda.driver
        # appears to be idempotent, i.e. no harm in calling it more than once
        pycuda.driver.init()

        ctx = make_default_context()
        try:
            assert isinstance(ctx.get_device().name(), str)
            assert isinstance(ctx.get_device().compute_capability(), tuple)
            assert isinstance(ctx.get_device().get_attributes(), dict)
            inner_f(*args, **kwargs)
        finally:
            ctx.pop()

            from pycuda.tools import clear_context_caches
            clear_context_caches()

            from gc import collect
            collect()

    try:
        from py.test import mark as mark_test
    except ImportError:
        return f

    return mark_test.cuda(f)

# }}}



# vim: foldmethod=marker

########NEW FILE########
__FILENAME__ = _cluda
CLUDA_PREAMBLE = """
#define local_barrier() __syncthreads();

#define WITHIN_KERNEL __device__
#define KERNEL extern "C" __global__
#define GLOBAL_MEM /* empty */
#define LOCAL_MEM __shared__
#define LOCAL_MEM_ARG /* empty */
#define REQD_WG_SIZE(X,Y,Z) __launch_bounds__(X*Y*Z, 1)

#define LID_0 threadIdx.x
#define LID_1 threadIdx.y
#define LID_2 threadIdx.z

#define GID_0 blockIdx.x
#define GID_1 blockIdx.y
#define GID_2 blockIdx.z

#define LDIM_0 blockDim.x
#define LDIM_1 blockDim.y
#define LDIM_2 blockDim.z

#define GDIM_0 gridDim.x
#define GDIM_1 gridDim.y
#define GDIM_2 gridDim.z
"""





########NEW FILE########
__FILENAME__ = _mymako
try:
    import mako.template
except ImportError:
    raise ImportError(
            "Some of PyCUDA's facilities require the Mako templating engine.\n"
            "You or a piece of software you have used has tried to call such a\n"
            "part of PyCUDA, but there was a problem importing Mako.\n\n"
            "You may install mako now by typing one of:\n"
            "- easy_install Mako\n"
            "- pip install Mako\n"
            "- aptitude install python-mako\n"
            "\nor whatever else is appropriate for your system.")

from mako import *

########NEW FILE########
__FILENAME__ = test_cumath
from __future__ import division
import math
import numpy as np
from pycuda.tools import mark_cuda_test


def have_pycuda():
    try:
        import pycuda  # noqa
        return True
    except:
        return False


if have_pycuda():
    import pycuda.gpuarray as gpuarray
    import pycuda.driver as drv  # noqa
    import pycuda.cumath as cumath


sizes = [10, 128, 1024, 1 << 10, 1 << 13]
dtypes = [np.float32, np.float64]
complex_dtypes = [np.complex64, np.complex128]


numpy_func_names = {
        "asin": "arcsin",
        "acos": "arccos",
        "atan": "arctan",
        }


def make_unary_function_test(name, a=0, b=1, threshold=0, complex=False):
    def test():
        gpu_func = getattr(cumath, name)
        cpu_func = getattr(np, numpy_func_names.get(name, name))
        if complex:
            _dtypes = complex_dtypes
        else:
            _dtypes = dtypes

        for s in sizes:
            for dtype in _dtypes:
                np.random.seed(1)
                A = (np.random.random(s)*(b-a) + a).astype(dtype)
                if complex:
                    A += (np.random.random(s)*(b-a) + a)*1j

                args = gpuarray.to_gpu(A)
                gpu_results = gpu_func(args).get()
                cpu_results = cpu_func(A)

                max_err = np.max(np.abs(cpu_results - gpu_results))
                assert (max_err <= threshold).all(), \
                        (max_err, name, dtype)

                gpu_results2 = gpuarray.empty_like(args)
                gr2 = gpu_func(args, out=gpu_results2)
                assert gpu_results2 is gr2
                gr2 = gr2.get()
                max_err = np.max(np.abs(cpu_results - gr2))
                assert (max_err <= threshold).all(), \
                        (max_err, name, dtype)

    return mark_cuda_test(test)


if have_pycuda():
    test_ceil = make_unary_function_test("ceil", -10, 10)
    test_floor = make_unary_function_test("ceil", -10, 10)
    test_fabs = make_unary_function_test("fabs", -10, 10)
    test_exp = make_unary_function_test("exp", -3, 3, 1e-5)
    test_exp_c = make_unary_function_test("exp", -3, 3, 1e-5, complex=True)
    test_log = make_unary_function_test("log", 1e-5, 1, 5e-7)
    test_log10 = make_unary_function_test("log10", 1e-5, 1, 3e-7)
    test_sqrt = make_unary_function_test("sqrt", 1e-5, 1, 2e-7)

    test_sin = make_unary_function_test("sin", -10, 10, 1e-7)
    test_sin_c = make_unary_function_test("sin", -3, 3, 2e-6, complex=True)
    test_cos = make_unary_function_test("cos", -10, 10, 1e-7)
    test_cos_c = make_unary_function_test("cos", -3, 3, 2e-6, complex=True)
    test_asin = make_unary_function_test("asin", -0.9, 0.9, 5e-7)
    #test_sin_c = make_unary_function_test("sin", -0.9, 0.9, 2e-6, complex=True)
    test_acos = make_unary_function_test("acos", -0.9, 0.9, 5e-7)
    #test_acos_c = make_unary_function_test("acos", -0.9, 0.9, 2e-6, complex=True)
    test_tan = make_unary_function_test("tan",
            -math.pi/2 + 0.1, math.pi/2 - 0.1, 1e-5)
    test_tan_c = make_unary_function_test("tan",
            -math.pi/2 + 0.1, math.pi/2 - 0.1, 3e-5, complex=True)
    test_atan = make_unary_function_test("atan", -10, 10, 2e-7)

    test_sinh = make_unary_function_test("sinh", -3, 3, 2e-6)
    test_sinh_c = make_unary_function_test("sinh", -3, 3, 2e-6, complex=True)
    test_cosh = make_unary_function_test("cosh", -3, 3, 2e-6)
    test_cosh_c = make_unary_function_test("cosh", -3, 3, 2e-6, complex=True)
    test_tanh = make_unary_function_test("tanh", -3, 3, 2e-6)
    test_tanh_c = make_unary_function_test("tanh",
            -math.pi/2 + 0.1, math.pi/2 - 0.1, 3e-5, complex=True)


class TestMath:
    disabled = not have_pycuda()

    @mark_cuda_test
    def test_fmod(self):
        """tests if the fmod function works"""
        for s in sizes:
            a = gpuarray.arange(s, dtype=np.float32)/10
            a2 = gpuarray.arange(s, dtype=np.float32)/45.2 + 0.1
            b = cumath.fmod(a, a2)

            a = a.get()
            a2 = a2.get()
            b = b.get()

            for i in range(s):
                assert math.fmod(a[i], a2[i]) == b[i]

    @mark_cuda_test
    def test_ldexp(self):
        """tests if the ldexp function works"""
        for s in sizes:
            a = gpuarray.arange(s, dtype=np.float32)
            a2 = gpuarray.arange(s, dtype=np.float32)*1e-3
            b = cumath.ldexp(a, a2)

            a = a.get()
            a2 = a2.get()
            b = b.get()

            for i in range(s):
                assert math.ldexp(a[i], int(a2[i])) == b[i]

    @mark_cuda_test
    def test_modf(self):
        """tests if the modf function works"""
        for s in sizes:
            a = gpuarray.arange(s, dtype=np.float32)/10
            fracpart, intpart = cumath.modf(a)

            a = a.get()
            intpart = intpart.get()
            fracpart = fracpart.get()

            for i in range(s):
                fracpart_true, intpart_true = math.modf(a[i])

                assert intpart_true == intpart[i]
                assert abs(fracpart_true - fracpart[i]) < 1e-4

    @mark_cuda_test
    def test_frexp(self):
        """tests if the frexp function works"""
        for s in sizes:
            a = gpuarray.arange(s, dtype=np.float32)/10
            significands, exponents = cumath.frexp(a)

            a = a.get()
            significands = significands.get()
            exponents = exponents.get()

            for i in range(s):
                sig_true, ex_true = math.frexp(a[i])

                assert sig_true == significands[i]
                assert ex_true == exponents[i]

    @mark_cuda_test
    def test_unary_func_kwargs(self):
        """tests if the kwargs to the unary functions work"""
        from pycuda.driver import Stream

        name, a, b, threshold = ("exp", -3, 3, 1e-5)
        gpu_func = getattr(cumath, name)
        cpu_func = getattr(np, numpy_func_names.get(name, name))
        for s in sizes:
            for dtype in dtypes:
                np.random.seed(1)
                A = (np.random.random(s)*(b-a) + a).astype(dtype)
                if complex:
                    A += (np.random.random(s)*(b-a) + a)*1j

                np.random.seed(1)
                A = (np.random.random(s)*(b-a) + a).astype(dtype)
                args = gpuarray.to_gpu(A)

                # 'out' kw
                gpu_results = gpuarray.empty_like(args)
                gpu_results = gpu_func(args, out=gpu_results).get()
                cpu_results = cpu_func(A)
                max_err = np.max(np.abs(cpu_results - gpu_results))
                assert (max_err <= threshold).all(), (max_err, name, dtype)

                # 'out' position
                gpu_results = gpuarray.empty_like(args)
                gpu_results = gpu_func(args, gpu_results).get()
                cpu_results = cpu_func(A)
                max_err = np.max(np.abs(cpu_results - gpu_results))
                assert (max_err <= threshold).all(), (max_err, name, dtype)

                # 'stream' kw
                mystream = Stream()
                np.random.seed(1)
                A = (np.random.random(s)*(b-a) + a).astype(dtype)
                args = gpuarray.to_gpu(A)
                gpu_results = gpuarray.empty_like(args)
                gpu_results = gpu_func(args, stream=mystream).get()
                cpu_results = cpu_func(A)
                max_err = np.max(np.abs(cpu_results - gpu_results))
                assert (max_err <= threshold).all(), (max_err, name, dtype)

                # 'stream' position
                mystream = Stream()
                np.random.seed(1)
                A = (np.random.random(s)*(b-a) + a).astype(dtype)
                args = gpuarray.to_gpu(A)
                gpu_results = gpuarray.empty_like(args)
                gpu_results = gpu_func(args, mystream).get()
                cpu_results = cpu_func(A)
                max_err = np.max(np.abs(cpu_results - gpu_results))
                assert (max_err <= threshold).all(), (max_err, name, dtype)

                # 'out' and 'stream' kw
                mystream = Stream()
                np.random.seed(1)
                A = (np.random.random(s)*(b-a) + a).astype(dtype)
                args = gpuarray.to_gpu(A)
                gpu_results = gpuarray.empty_like(args)
                gpu_results = gpu_func(args, stream=mystream, out=gpu_results).get()
                cpu_results = cpu_func(A)
                max_err = np.max(np.abs(cpu_results - gpu_results))
                assert (max_err <= threshold).all(), (max_err, name, dtype)


if __name__ == "__main__":
    # make sure that import failures get reported, instead of skipping the tests.
    import pycuda.autoinit  # noqa

    import sys
    if len(sys.argv) > 1:
        exec (sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])

########NEW FILE########
__FILENAME__ = test_driver
from __future__ import division
import numpy as np
import numpy.linalg as la
from pycuda.tools import mark_cuda_test




def have_pycuda():
    try:
        import pycuda
        return True
    except:
        return False


if have_pycuda():
    import pycuda.gpuarray as gpuarray
    import pycuda.driver as drv
    from pycuda.compiler import SourceModule




class TestDriver:
    disabled = not have_pycuda()

    @mark_cuda_test
    def test_memory(self):
        z = np.random.randn(400).astype(np.float32)
        new_z = drv.from_device_like(drv.to_device(z), z)
        assert la.norm(new_z-z) == 0

    @mark_cuda_test
    def test_simple_kernel(self):
        mod = SourceModule("""
        __global__ void multiply_them(float *dest, float *a, float *b)
        {
          const int i = threadIdx.x;
          dest[i] = a[i] * b[i];
        }
        """)

        multiply_them = mod.get_function("multiply_them")

        a = np.random.randn(400).astype(np.float32)
        b = np.random.randn(400).astype(np.float32)

        dest = np.zeros_like(a)
        multiply_them(
                drv.Out(dest), drv.In(a), drv.In(b),
                block=(400,1,1))
        assert la.norm(dest-a*b) == 0

    @mark_cuda_test
    def test_simple_kernel_2(self):
        mod = SourceModule("""
        __global__ void multiply_them(float *dest, float *a, float *b)
        {
          const int i = threadIdx.x;
          dest[i] = a[i] * b[i];
        }
        """)

        multiply_them = mod.get_function("multiply_them")

        a = np.random.randn(400).astype(np.float32)
        b = np.random.randn(400).astype(np.float32)
        a_gpu = drv.to_device(a)
        b_gpu = drv.to_device(b)

        dest = np.zeros_like(a)
        multiply_them(
                drv.Out(dest), a_gpu, b_gpu,
                block=(400,1,1))
        assert la.norm(dest-a*b) == 0

        drv.Context.synchronize()
        # now try with offsets
        dest = np.zeros_like(a)
        multiply_them(
                drv.Out(dest), np.intp(a_gpu)+a.itemsize, b_gpu,
                block=(399,1,1))

        assert la.norm((dest[:-1]-a[1:]*b[:-1])) == 0

    @mark_cuda_test
    def test_vector_types(self):
        mod = SourceModule("""
        __global__ void set_them(float3 *dest, float3 x)
        {
          const int i = threadIdx.x;
          dest[i] = x;
        }
        """)

        set_them = mod.get_function("set_them")
        a = gpuarray.vec.make_float3(1, 2, 3)
        dest = np.empty((400), gpuarray.vec.float3)

        set_them(drv.Out(dest), a, block=(400,1,1))
        assert (dest == a).all()

    from py.test import mark as mark_test

    @mark_cuda_test
    def test_streamed_kernel(self):
        # this differs from the "simple_kernel" case in that *all* computation
        # and data copying is asynchronous. Observe how this necessitates the
        # use of page-locked memory.

        mod = SourceModule("""
        __global__ void multiply_them(float *dest, float *a, float *b)
        {
          const int i = threadIdx.x*blockDim.y + threadIdx.y;
          dest[i] = a[i] * b[i];
        }
        """)

        multiply_them = mod.get_function("multiply_them")

        shape = (32,8)
        a = drv.pagelocked_zeros(shape, dtype=np.float32)
        b = drv.pagelocked_zeros(shape, dtype=np.float32)
        a[:] = np.random.randn(*shape)
        b[:] = np.random.randn(*shape)

        a_gpu = drv.mem_alloc(a.nbytes)
        b_gpu = drv.mem_alloc(b.nbytes)

        strm = drv.Stream()
        drv.memcpy_htod_async(a_gpu, a, strm)
        drv.memcpy_htod_async(b_gpu, b, strm)
        strm.synchronize()

        dest = drv.pagelocked_empty_like(a)
        multiply_them(
                drv.Out(dest), a_gpu, b_gpu,
                block=shape+(1,), stream=strm)
        strm.synchronize()

        drv.memcpy_dtoh_async(a, a_gpu, strm)
        drv.memcpy_dtoh_async(b, b_gpu, strm)
        strm.synchronize()

        assert la.norm(dest-a*b) == 0

    @mark_cuda_test
    def test_gpuarray(self):
        a = np.arange(200000, dtype=np.float32)
        b = a + 17
        import pycuda.gpuarray as gpuarray
        a_g = gpuarray.to_gpu(a)
        b_g = gpuarray.to_gpu(b)
        diff = (a_g-3*b_g+(-a_g)).get() - (a-3*b+(-a))
        assert la.norm(diff) == 0

        diff = ((a_g*b_g).get()-a*b)
        assert la.norm(diff) == 0

    @mark_cuda_test
    def donottest_cublas_mixing():
        test_streamed_kernel()

        import pycuda.blas as blas

        shape = (10,)
        a = blas.ones(shape, dtype=np.float32)
        b = 33*blas.ones(shape, dtype=np.float32)
        assert ((-a+b).from_gpu() == 32).all()

        test_streamed_kernel()

    @mark_cuda_test
    def test_2d_texture(self):
        mod = SourceModule("""
        texture<float, 2, cudaReadModeElementType> mtx_tex;

        __global__ void copy_texture(float *dest)
        {
          int row = threadIdx.x;
          int col = threadIdx.y;
          int w = blockDim.y;
          dest[row*w+col] = tex2D(mtx_tex, row, col);
        }
        """)

        copy_texture = mod.get_function("copy_texture")
        mtx_tex = mod.get_texref("mtx_tex")

        shape = (3,4)
        a = np.random.randn(*shape).astype(np.float32)
        drv.matrix_to_texref(a, mtx_tex, order="F")

        dest = np.zeros(shape, dtype=np.float32)
        copy_texture(drv.Out(dest),
                block=shape+(1,),
                texrefs=[mtx_tex]
                )
        assert la.norm(dest-a) == 0

    @mark_cuda_test
    def test_multiple_2d_textures(self):
        mod = SourceModule("""
        texture<float, 2, cudaReadModeElementType> mtx_tex;
        texture<float, 2, cudaReadModeElementType> mtx2_tex;

        __global__ void copy_texture(float *dest)
        {
          int row = threadIdx.x;
          int col = threadIdx.y;
          int w = blockDim.y;
          dest[row*w+col] =
              tex2D(mtx_tex, row, col)
              +
              tex2D(mtx2_tex, row, col);
        }
        """)

        copy_texture = mod.get_function("copy_texture")
        mtx_tex = mod.get_texref("mtx_tex")
        mtx2_tex = mod.get_texref("mtx2_tex")

        shape = (3,4)
        a = np.random.randn(*shape).astype(np.float32)
        b = np.random.randn(*shape).astype(np.float32)
        drv.matrix_to_texref(a, mtx_tex, order="F")
        drv.matrix_to_texref(b, mtx2_tex, order="F")

        dest = np.zeros(shape, dtype=np.float32)
        copy_texture(drv.Out(dest),
                block=shape+(1,),
                texrefs=[mtx_tex, mtx2_tex]
                )
        assert la.norm(dest-a-b) < 1e-6

    @mark_cuda_test
    def test_multichannel_2d_texture(self):
        mod = SourceModule("""
        #define CHANNELS 4
        texture<float4, 2, cudaReadModeElementType> mtx_tex;

        __global__ void copy_texture(float *dest)
        {
          int row = threadIdx.x;
          int col = threadIdx.y;
          int w = blockDim.y;
          float4 texval = tex2D(mtx_tex, row, col);
          dest[(row*w+col)*CHANNELS + 0] = texval.x;
          dest[(row*w+col)*CHANNELS + 1] = texval.y;
          dest[(row*w+col)*CHANNELS + 2] = texval.z;
          dest[(row*w+col)*CHANNELS + 3] = texval.w;
        }
        """)

        copy_texture = mod.get_function("copy_texture")
        mtx_tex = mod.get_texref("mtx_tex")

        shape = (5,6)
        channels = 4
        a = np.asarray(
                np.random.randn(*((channels,)+shape)),
                dtype=np.float32, order="F")
        drv.bind_array_to_texref(
            drv.make_multichannel_2d_array(a, order="F"), mtx_tex)

        dest = np.zeros(shape+(channels,), dtype=np.float32)
        copy_texture(drv.Out(dest),
                block=shape+(1,),
                texrefs=[mtx_tex]
                )
        reshaped_a = a.transpose(1,2,0)
        #print reshaped_a
        #print dest
        assert la.norm(dest-reshaped_a) == 0

    @mark_cuda_test
    def test_multichannel_linear_texture(self):
        mod = SourceModule("""
        #define CHANNELS 4
        texture<float4, 1, cudaReadModeElementType> mtx_tex;

        __global__ void copy_texture(float *dest)
        {
          int i = threadIdx.x+blockDim.x*threadIdx.y;
          float4 texval = tex1Dfetch(mtx_tex, i);
          dest[i*CHANNELS + 0] = texval.x;
          dest[i*CHANNELS + 1] = texval.y;
          dest[i*CHANNELS + 2] = texval.z;
          dest[i*CHANNELS + 3] = texval.w;
        }
        """)

        copy_texture = mod.get_function("copy_texture")
        mtx_tex = mod.get_texref("mtx_tex")

        shape = (16, 16)
        channels = 4
        a = np.random.randn(*(shape+(channels,))).astype(np.float32)
        a_gpu = drv.to_device(a)
        mtx_tex.set_address(a_gpu, a.nbytes)
        mtx_tex.set_format(drv.array_format.FLOAT, 4)

        dest = np.zeros(shape+(channels,), dtype=np.float32)
        copy_texture(drv.Out(dest),
                block=shape+(1,),
                texrefs=[mtx_tex]
                )
        #print a
        #print dest
        assert la.norm(dest-a) == 0

    @mark_cuda_test
    def test_large_smem(self):
        n = 4000
        mod = SourceModule("""
        #include <stdio.h>

        __global__ void kernel(int *d_data)
        {
        __shared__ int sdata[%d];
        sdata[threadIdx.x] = threadIdx.x;
        d_data[threadIdx.x] = sdata[threadIdx.x];
        }
        """ % n)

        kernel = mod.get_function("kernel")

        import pycuda.gpuarray as gpuarray
        arg = gpuarray.zeros((n,), dtype=np.float32)

        kernel(arg, block=(1,1,1,), )

    @mark_cuda_test
    def test_bitlog(self):
        from pycuda.tools import bitlog2
        assert bitlog2(17) == 4
        assert bitlog2(0xaffe) == 15
        assert bitlog2(0x3affe) == 17
        assert bitlog2(0xcc3affe) == 27

    @mark_cuda_test
    def test_mempool_2(self):
        from pycuda.tools import DeviceMemoryPool as DMP
        from random import randrange

        for i in range(2000):
            s = randrange(1<<31) >> randrange(32)
            bin_nr = DMP.bin_number(s)
            asize = DMP.alloc_size(bin_nr)

            assert asize >= s, s
            assert DMP.bin_number(asize) == bin_nr, s
            assert asize < asize*(1+1/8)

    @mark_cuda_test
    def test_mempool(self):
        from pycuda.tools import bitlog2
        from pycuda.tools import DeviceMemoryPool

        pool = DeviceMemoryPool()
        maxlen = 10
        queue = []
        free, total = drv.mem_get_info()

        e0 = bitlog2(free)

        for e in range(e0-6, e0-4):
            for i in range(100):
                queue.append(pool.allocate(1<<e))
                if len(queue) > 10:
                    queue.pop(0)
        del queue
        pool.stop_holding()

    @mark_cuda_test
    def test_multi_context(self):
        if drv.get_version() < (2,0,0):
            return
        if drv.get_version() >= (2,2,0):
            if drv.Context.get_device().compute_mode == drv.compute_mode.EXCLUSIVE:
                return

        mem_a = drv.mem_alloc(50)
        ctx2 = drv.Context.get_device().make_context()
        mem_b = drv.mem_alloc(60)

        del mem_a
        del mem_b
        ctx2.detach()

    @mark_cuda_test
    def test_3d_texture(self):
        # adapted from code by Nicolas Pinto
        w = 2
        h = 4
        d = 8
        shape = (w, h, d)

        a = np.asarray(
                np.random.randn(*shape),
                dtype=np.float32, order="F")

        descr = drv.ArrayDescriptor3D()
        descr.width = w
        descr.height = h
        descr.depth = d
        descr.format = drv.dtype_to_array_format(a.dtype)
        descr.num_channels = 1
        descr.flags = 0

        ary = drv.Array(descr)

        copy = drv.Memcpy3D()
        copy.set_src_host(a)
        copy.set_dst_array(ary)
        copy.width_in_bytes = copy.src_pitch = a.strides[1]
        copy.src_height = copy.height = h
        copy.depth = d

        copy()

        mod = SourceModule("""
        texture<float, 3, cudaReadModeElementType> mtx_tex;

        __global__ void copy_texture(float *dest)
        {
          int x = threadIdx.x;
          int y = threadIdx.y;
          int z = threadIdx.z;
          int dx = blockDim.x;
          int dy = blockDim.y;
          int i = (z*dy + y)*dx + x;
          dest[i] = tex3D(mtx_tex, x, y, z);
          //dest[i] = x;
        }
        """)

        copy_texture = mod.get_function("copy_texture")
        mtx_tex = mod.get_texref("mtx_tex")

        mtx_tex.set_array(ary)

        dest = np.zeros(shape, dtype=np.float32, order="F")
        copy_texture(drv.Out(dest), block=shape, texrefs=[mtx_tex])
        assert la.norm(dest-a) == 0

    @mark_cuda_test
    def test_prepared_invocation(self):
        a = np.random.randn(4,4).astype(np.float32)
        a_gpu = drv.mem_alloc(a.size * a.dtype.itemsize)

        drv.memcpy_htod(a_gpu, a)

        mod = SourceModule("""
            __global__ void doublify(float *a)
            {
              int idx = threadIdx.x + threadIdx.y*blockDim.x;
              a[idx] *= 2;
            }
            """)

        func = mod.get_function("doublify")
        func.prepare("P")
        func.prepared_call((1, 1), (4,4,1), a_gpu, shared_size=20)
        a_doubled = np.empty_like(a)
        drv.memcpy_dtoh(a_doubled, a_gpu)
        print (a)
        print (a_doubled)
        assert la.norm(a_doubled-2*a) == 0

        # now with offsets
        func.prepare("P")
        a_quadrupled = np.empty_like(a)
        func.prepared_call((1, 1), (15,1,1), int(a_gpu)+a.dtype.itemsize)
        drv.memcpy_dtoh(a_quadrupled, a_gpu)
        assert la.norm(a_quadrupled[1:]-4*a[1:]) == 0

    @mark_cuda_test
    def test_prepared_with_vector(self):
        cuda_source = r'''
        __global__ void cuda_function(float3 input)
        {
        float3 result = make_float3(input.x, input.y, input.z);
        }
        '''

        mod = SourceModule(cuda_source, cache_dir=False, keep=False)

        kernel = mod.get_function("cuda_function")
        arg_types = [gpuarray.vec.float3]

        kernel.prepare(arg_types)
        kernel.prepared_call((1, 1, 1), (1, 1, 1),
                gpuarray.vec.make_float3(0.0, 1.0, 2.0))

    @mark_cuda_test
    def test_fp_textures(self):
        if drv.Context.get_device().compute_capability() < (1, 3):
            return

        for tp in [np.float32, np.float64]:
            from pycuda.tools import dtype_to_ctype

            tp_cstr = dtype_to_ctype(tp)
            mod = SourceModule("""
            #include <pycuda-helpers.hpp>

            texture<fp_tex_%(tp)s, 1, cudaReadModeElementType> my_tex;

            __global__ void copy_texture(%(tp)s *dest)
            {
              int i = threadIdx.x;
              dest[i] = fp_tex1Dfetch(my_tex, i);
            }
            """ % {"tp": tp_cstr})

            copy_texture = mod.get_function("copy_texture")
            my_tex = mod.get_texref("my_tex")

            import pycuda.gpuarray as gpuarray

            shape = (384,)
            a = np.random.randn(*shape).astype(tp)
            a_gpu = gpuarray.to_gpu(a)
            a_gpu.bind_to_texref_ext(my_tex, allow_double_hack=True)

            dest = np.zeros(shape, dtype=tp)
            copy_texture(drv.Out(dest),
                    block=shape+(1,1,),
                    texrefs=[my_tex])

            assert la.norm(dest-a) == 0

    @mark_cuda_test
    def test_constant_memory(self):
        # contributed by Andrew Wagner

        module = SourceModule("""
        __constant__ float const_array[32];

        __global__ void copy_constant_into_global(float* global_result_array)
        {
            global_result_array[threadIdx.x] = const_array[threadIdx.x];
        }
        """)

        copy_constant_into_global = module.get_function("copy_constant_into_global")
        const_array, _ = module.get_global('const_array')

        host_array = np.random.randint(0,255,(32,)).astype(np.float32)

        global_result_array = drv.mem_alloc_like(host_array)
        drv.memcpy_htod(const_array, host_array)

        copy_constant_into_global(
                global_result_array,  
                grid=(1, 1), block=(32, 1, 1))

        host_result_array = np.zeros_like(host_array)
        drv.memcpy_dtoh(host_result_array, global_result_array)

        assert (host_result_array == host_array).all

    @mark_cuda_test
    def test_register_host_memory(self):
        if drv.get_version() < (4,):
            from py.test import skip
            skip("register_host_memory only exists on CUDA 4.0 and later")

        import sys
        if sys.platform == "darwin":
            from py.test import skip
            skip("register_host_memory is not supported on OS X")

        a = drv.aligned_empty((2**20,), np.float64, alignment=4096)
        drv.register_host_memory(a)


def test_import_pyopencl_before_pycuda():
    try:
        import pyopencl
    except ImportError:
        return
    import pycuda.driver


if __name__ == "__main__":
    # make sure that import failures get reported, instead of skipping the tests.
    import pycuda.autoinit

    import sys
    if len(sys.argv) > 1:
        exec (sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])

########NEW FILE########
__FILENAME__ = test_gpuarray
#! /usr/bin/env python
import numpy as np
import numpy.linalg as la
import sys
from pycuda.tools import mark_cuda_test
from pycuda.characterize import has_double_support


def have_pycuda():
    try:
        import pycuda  # noqa
        return True
    except:
        return False

if have_pycuda():
    import pycuda.gpuarray as gpuarray
    import pycuda.driver as drv
    from pycuda.compiler import SourceModule


class TestGPUArray:
    disabled = not have_pycuda()

    @mark_cuda_test
    def test_pow_array(self):
        a = np.array([1, 2, 3, 4, 5]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)

        result = pow(a_gpu, a_gpu).get()
        assert (np.abs(a**a - result) < 1e-3).all()

        result = (a_gpu**a_gpu).get()
        assert (np.abs(pow(a, a) - result) < 1e-3).all()

    @mark_cuda_test
    def test_pow_number(self):
        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)

        result = pow(a_gpu, 2).get()
        assert (np.abs(a**2 - result) < 1e-3).all()

    @mark_cuda_test
    def test_numpy_integer_shape(self):
        gpuarray.empty(np.int32(17), np.float32)
        gpuarray.empty((np.int32(17), np.int32(17)), np.float32)

    @mark_cuda_test
    def test_abs(self):
        a = -gpuarray.arange(111, dtype=np.float32)
        res = a.get()

        for i in range(111):
            assert res[i] <= 0

        a = abs(a)

        res = a.get()

        for i in range(111):
            assert abs(res[i]) >= 0
            assert res[i] == i

    @mark_cuda_test
    def test_len(self):
        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_cpu = gpuarray.to_gpu(a)
        assert len(a_cpu) == 10

    @mark_cuda_test
    def test_multiply(self):
        """Test the muliplication of an array with a scalar. """

        for sz in [10, 50000]:
            for dtype, scalars in [
                    (np.float32, [2]),
                    (np.complex64, [2, 2j])
                    ]:
                for scalar in scalars:
                    a = np.arange(sz).astype(dtype)
                    a_gpu = gpuarray.to_gpu(a)
                    a_doubled = (scalar * a_gpu).get()

                    assert (a * scalar == a_doubled).all()

    @mark_cuda_test
    def test_rmul_yields_right_type(self):
        a = np.array([1, 2, 3, 4, 5]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)

        two_a = 2*a_gpu
        assert isinstance(two_a, gpuarray.GPUArray)

        two_a = np.float32(2)*a_gpu
        assert isinstance(two_a, gpuarray.GPUArray)

    @mark_cuda_test
    def test_multiply_array(self):
        """Test the multiplication of two arrays."""

        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)

        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(a)

        a_squared = (b_gpu*a_gpu).get()

        assert (a*a == a_squared).all()

    @mark_cuda_test
    def test_addition_array(self):
        """Test the addition of two arrays."""

        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        a_added = (a_gpu+a_gpu).get()

        assert (a+a == a_added).all()

    @mark_cuda_test
    def test_iaddition_array(self):
        """Test the inplace addition of two arrays."""

        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        a_gpu += a_gpu
        a_added = a_gpu.get()

        assert (a+a == a_added).all()

    @mark_cuda_test
    def test_addition_scalar(self):
        """Test the addition of an array and a scalar."""

        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        a_added = (7+a_gpu).get()

        assert (7+a == a_added).all()

    @mark_cuda_test
    def test_iaddition_scalar(self):
        """Test the inplace addition of an array and a scalar."""

        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        a_gpu += 7
        a_added = a_gpu.get()

        assert (7+a == a_added).all()

    @mark_cuda_test
    def test_substract_array(self):
        """Test the substraction of two arrays."""
        #test data
        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        b = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100]).astype(np.float32)

        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)

        result = (a_gpu-b_gpu).get()
        assert (a-b == result).all()

        result = (b_gpu-a_gpu).get()
        assert (b-a == result).all()

    @mark_cuda_test
    def test_substract_scalar(self):
        """Test the substraction of an array and a scalar."""

        #test data
        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)

        #convert a to a gpu object
        a_gpu = gpuarray.to_gpu(a)

        result = (a_gpu-7).get()
        assert (a-7 == result).all()

        result = (7-a_gpu).get()
        assert (7-a == result).all()

    @mark_cuda_test
    def test_divide_scalar(self):
        """Test the division of an array and a scalar."""

        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)

        result = (a_gpu/2).get()
        assert (a/2 == result).all()

        result = (2/a_gpu).get()
        assert (2/a == result).all()

    @mark_cuda_test
    def test_divide_array(self):
        """Test the division of an array and a scalar. """

        #test data
        a = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100]).astype(np.float32)
        b = np.array([10, 10, 10, 10, 10, 10, 10, 10, 10, 10]).astype(np.float32)

        a_gpu = gpuarray.to_gpu(a)
        b_gpu = gpuarray.to_gpu(b)

        a_divide = (a_gpu/b_gpu).get()
        assert (np.abs(a/b - a_divide) < 1e-3).all()

        a_divide = (b_gpu/a_gpu).get()
        assert (np.abs(b/a - a_divide) < 1e-3).all()

    @mark_cuda_test
    def test_random(self):
        from pycuda.curandom import rand as curand

        if has_double_support():
            dtypes = [np.float32, np.float64]
        else:
            dtypes = [np.float32]

        for dtype in dtypes:
            a = curand((10, 100), dtype=dtype).get()

            assert (0 <= a).all()
            assert (a < 1).all()

    @mark_cuda_test
    def test_curand_wrappers(self):
        from pycuda.curandom import get_curand_version
        if get_curand_version() is None:
            from pytest import skip
            skip("curand not installed")

        generator_types = []
        if get_curand_version() >= (3, 2, 0):
            from pycuda.curandom import (
                    XORWOWRandomNumberGenerator,
                    Sobol32RandomNumberGenerator)
            generator_types.extend([
                    XORWOWRandomNumberGenerator,
                    Sobol32RandomNumberGenerator])
        if get_curand_version() >= (4, 0, 0):
            from pycuda.curandom import (
                    ScrambledSobol32RandomNumberGenerator,
                    Sobol64RandomNumberGenerator,
                    ScrambledSobol64RandomNumberGenerator)
            generator_types.extend([
                    ScrambledSobol32RandomNumberGenerator,
                    Sobol64RandomNumberGenerator,
                    ScrambledSobol64RandomNumberGenerator])
        if get_curand_version() >= (4, 1, 0):
            from pycuda.curandom import MRG32k3aRandomNumberGenerator
            generator_types.extend([MRG32k3aRandomNumberGenerator])

        if has_double_support():
            dtypes = [np.float32, np.float64]
        else:
            dtypes = [np.float32]

        for gen_type in generator_types:
            gen = gen_type()

            for dtype in dtypes:
                gen.gen_normal(10000, dtype)
                # test non-Box-Muller version, if available
                gen.gen_normal(10001, dtype)

                if get_curand_version() >= (4, 0, 0):
                    gen.gen_log_normal(10000, dtype, 10.0, 3.0)
                    # test non-Box-Muller version, if available
                    gen.gen_log_normal(10001, dtype, 10.0, 3.0)

                x = gen.gen_uniform(10000, dtype)
                x_host = x.get()
                assert (-1 <= x_host).all()
                assert (x_host <= 1).all()

            gen.gen_uniform(10000, np.uint32)
            if get_curand_version() >= (5, 0, 0):
                gen.gen_poisson(10000, np.uint32, 13.0)

    @mark_cuda_test
    def test_array_gt(self):
        """Test whether array contents are > the other array's
        contents"""

        a = np.array([5, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b = np.array([2, 10]).astype(np.float32)
        b_gpu = gpuarray.to_gpu(b)
        result = (a_gpu > b_gpu).get()
        assert result[0]
        assert not result[1]

    @mark_cuda_test
    def test_array_lt(self):
        """Test whether array contents are < the other array's
        contents"""

        a = np.array([5, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b = np.array([2, 10]).astype(np.float32)
        b_gpu = gpuarray.to_gpu(b)
        result = (b_gpu < a_gpu).get()
        assert result[0]
        assert not result[1]

    @mark_cuda_test
    def test_array_le(self):
        """Test whether array contents are <= the other array's
        contents"""

        a = np.array([5, 10, 1]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b = np.array([2, 10, 2]).astype(np.float32)
        b_gpu = gpuarray.to_gpu(b)
        result = (b_gpu <= a_gpu).get()
        assert result[0]
        assert result[1]
        assert not result[2]

    @mark_cuda_test
    def test_array_ge(self):
        """Test whether array contents are >= the other array's
        contents"""

        a = np.array([5, 10, 1]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b = np.array([2, 10, 2]).astype(np.float32)
        b_gpu = gpuarray.to_gpu(b)
        result = (a_gpu >= b_gpu).get()
        assert result[0]
        assert result[1]
        assert not result[2]

    @mark_cuda_test
    def test_array_eq(self):
        """Test whether array contents are == the other array's
        contents"""

        a = np.array([5, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b = np.array([2, 10]).astype(np.float32)
        b_gpu = gpuarray.to_gpu(b)
        result = (a_gpu == b_gpu).get()
        assert not result[0]
        assert result[1]

    @mark_cuda_test
    def test_array_ne(self):
        """Test whether array contents are != the other array's
        contents"""

        a = np.array([5, 10]).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)
        b = np.array([2, 10]).astype(np.float32)
        b_gpu = gpuarray.to_gpu(b)
        result = (a_gpu != b_gpu).get()
        assert result[0]
        assert not result[1]

    @mark_cuda_test
    def test_nan_arithmetic(self):
        def make_nan_contaminated_vector(size):
            shape = (size,)
            a = np.random.randn(*shape).astype(np.float32)
            #for i in range(0, shape[0], 3):
                #a[i] = float('nan')
            from random import randrange
            for i in range(size//10):
                a[randrange(0, size)] = float('nan')
            return a

        size = 1 << 20

        a = make_nan_contaminated_vector(size)
        a_gpu = gpuarray.to_gpu(a)
        b = make_nan_contaminated_vector(size)
        b_gpu = gpuarray.to_gpu(b)

        ab = a*b
        ab_gpu = (a_gpu*b_gpu).get()

        assert (np.isnan(ab) == np.isnan(ab_gpu)).all()

    @mark_cuda_test
    def test_elwise_kernel(self):
        from pycuda.curandom import rand as curand

        a_gpu = curand((50,))
        b_gpu = curand((50,))

        from pycuda.elementwise import ElementwiseKernel
        lin_comb = ElementwiseKernel(
                "float a, float *x, float b, float *y, float *z",
                "z[i] = a*x[i] + b*y[i]",
                "linear_combination")

        c_gpu = gpuarray.empty_like(a_gpu)
        lin_comb(5, a_gpu, 6, b_gpu, c_gpu)

        assert la.norm((c_gpu - (5*a_gpu+6*b_gpu)).get()) < 1e-5

    @mark_cuda_test
    def test_ranged_elwise_kernel(self):
        from pycuda.elementwise import ElementwiseKernel
        set_to_seven = ElementwiseKernel(
                "float *z",
                "z[i] = 7",
                "set_to_seven")

        for i, slc in enumerate([
                slice(5, 20000),
                slice(5, 20000, 17),
                slice(3000, 5, -1),
                slice(1000, -1),
                ]):

            a_gpu = gpuarray.zeros((50000,), dtype=np.float32)
            a_cpu = np.zeros(a_gpu.shape, a_gpu.dtype)

            a_cpu[slc] = 7
            set_to_seven(a_gpu, slice=slc)
            drv.Context.synchronize()

            assert la.norm(a_cpu - a_gpu.get()) == 0, i

    @mark_cuda_test
    def test_take(self):
        idx = gpuarray.arange(0, 10000, 2, dtype=np.uint32)
        for dtype in [np.float32, np.complex64]:
            a = gpuarray.arange(0, 600000, dtype=np.uint32).astype(dtype)
            a_host = a.get()
            result = gpuarray.take(a, idx)

            assert (a_host[idx.get()] == result.get()).all()

    @mark_cuda_test
    def test_arange(self):
        a = gpuarray.arange(12, dtype=np.float32)
        assert (np.arange(12, dtype=np.float32) == a.get()).all()

    @mark_cuda_test
    def test_reverse(self):
        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).astype(np.float32)
        a_cpu = gpuarray.to_gpu(a)

        a_cpu = a_cpu.reverse()

        b = a_cpu.get()

        for i in range(0, 10):
            assert a[len(a)-1-i] == b[i]

    @mark_cuda_test
    def test_sum(self):
        from pycuda.curandom import rand as curand
        a_gpu = curand((200000,))
        a = a_gpu.get()

        sum_a = np.sum(a)

        sum_a_gpu = gpuarray.sum(a_gpu).get()

        assert abs(sum_a_gpu-sum_a)/abs(sum_a) < 1e-4

    @mark_cuda_test
    def test_minmax(self):
        from pycuda.curandom import rand as curand

        if has_double_support():
            dtypes = [np.float64, np.float32, np.int32]
        else:
            dtypes = [np.float32, np.int32]

        for what in ["min", "max"]:
            for dtype in dtypes:
                a_gpu = curand((200000,), dtype)
                a = a_gpu.get()

                op_a = getattr(np, what)(a)
                op_a_gpu = getattr(gpuarray, what)(a_gpu).get()

                assert op_a_gpu == op_a, (op_a_gpu, op_a, dtype, what)

    @mark_cuda_test
    def test_subset_minmax(self):
        from pycuda.curandom import rand as curand

        l_a = 200000
        gran = 5
        l_m = l_a - l_a // gran + 1

        if has_double_support():
            dtypes = [np.float64, np.float32, np.int32]
        else:
            dtypes = [np.float32, np.int32]

        for dtype in dtypes:
            a_gpu = curand((l_a,), dtype)
            a = a_gpu.get()

            meaningful_indices_gpu = gpuarray.zeros(l_m, dtype=np.int32)
            meaningful_indices = meaningful_indices_gpu.get()
            j = 0
            for i in range(len(meaningful_indices)):
                meaningful_indices[i] = j
                j = j + 1
                if j % gran == 0:
                    j = j + 1

            meaningful_indices_gpu = gpuarray.to_gpu(meaningful_indices)
            b = a[meaningful_indices]

            min_a = np.min(b)
            min_a_gpu = gpuarray.subset_min(meaningful_indices_gpu, a_gpu).get()

            assert min_a_gpu == min_a

    @mark_cuda_test
    def test_dot(self):
        from pycuda.curandom import rand as curand
        for l in [2, 3, 4, 5, 6, 7, 31, 32, 33, 127, 128, 129,
                255, 256, 257, 16384 - 993,
                20000]:
            a_gpu = curand((l,))
            a = a_gpu.get()
            b_gpu = curand((l,))
            b = b_gpu.get()

            dot_ab = np.dot(a, b)

            dot_ab_gpu = gpuarray.dot(a_gpu, b_gpu).get()

            assert abs(dot_ab_gpu-dot_ab)/abs(dot_ab) < 1e-4

    @mark_cuda_test
    def test_slice(self):
        from pycuda.curandom import rand as curand

        l = 20000
        a_gpu = curand((l,))
        a = a_gpu.get()

        from random import randrange
        for i in range(200):
            start = randrange(l)
            end = randrange(start, l)

            a_gpu_slice = a_gpu[start:end]
            a_slice = a[start:end]

            assert la.norm(a_gpu_slice.get()-a_slice) == 0

    @mark_cuda_test
    def test_2d_slice_c(self):
        from pycuda.curandom import rand as curand

        n = 1000
        m = 300
        a_gpu = curand((n, m))
        a = a_gpu.get()

        from random import randrange
        for i in range(200):
            start = randrange(n)
            end = randrange(start, n)

            a_gpu_slice = a_gpu[start:end]
            a_slice = a[start:end]

            assert la.norm(a_gpu_slice.get()-a_slice) == 0

    @mark_cuda_test
    def test_2d_slice_f(self):
        from pycuda.curandom import rand as curand
        import pycuda.gpuarray as gpuarray

        n = 1000
        m = 300
        a_gpu = curand((n, m))
        a_gpu_f = gpuarray.GPUArray((m, n), np.float32,
                                    gpudata=a_gpu.gpudata,
                                    order="F")
        a = a_gpu_f.get()

        from random import randrange
        for i in range(200):
            start = randrange(n)
            end = randrange(start, n)

            a_gpu_slice = a_gpu_f[:, start:end]
            a_slice = a[:, start:end]

            assert la.norm(a_gpu_slice.get()-a_slice) == 0

    @mark_cuda_test
    def test_if_positive(self):
        from pycuda.curandom import rand as curand

        l = 20
        a_gpu = curand((l,))
        b_gpu = curand((l,))
        a = a_gpu.get()
        b = b_gpu.get()

        import pycuda.gpuarray as gpuarray

        max_a_b_gpu = gpuarray.maximum(a_gpu, b_gpu)
        min_a_b_gpu = gpuarray.minimum(a_gpu, b_gpu)

        print (max_a_b_gpu)
        print (np.maximum(a, b))

        assert la.norm(max_a_b_gpu.get() - np.maximum(a, b)) == 0
        assert la.norm(min_a_b_gpu.get() - np.minimum(a, b)) == 0

    @mark_cuda_test
    def test_take_put(self):
        for n in [5, 17, 333]:
            one_field_size = 8
            buf_gpu = gpuarray.zeros(n*one_field_size, dtype=np.float32)
            dest_indices = gpuarray.to_gpu(np.array(
                [0,  1,  2,  3, 32, 33, 34, 35], dtype=np.uint32))
            read_map = gpuarray.to_gpu(
                    np.array([7, 6, 5, 4, 3, 2, 1, 0], dtype=np.uint32))

            gpuarray.multi_take_put(
                    arrays=[buf_gpu for i in range(n)],
                    dest_indices=dest_indices,
                    src_indices=read_map,
                    src_offsets=[i*one_field_size for i in range(n)],
                    dest_shape=(96,))

            drv.Context.synchronize()

    @mark_cuda_test
    def test_astype(self):
        from pycuda.curandom import rand as curand

        if not has_double_support():
            return

        a_gpu = curand((2000,), dtype=np.float32)

        a = a_gpu.get().astype(np.float64)
        a2 = a_gpu.astype(np.float64).get()

        assert a2.dtype == np.float64
        assert la.norm(a - a2) == 0, (a, a2)

        a_gpu = curand((2000,), dtype=np.float64)

        a = a_gpu.get().astype(np.float32)
        a2 = a_gpu.astype(np.float32).get()

        assert a2.dtype == np.float32
        assert la.norm(a - a2)/la.norm(a) < 1e-7

    @mark_cuda_test
    def test_complex_bits(self):
        from pycuda.curandom import rand as curand

        if has_double_support():
            dtypes = [np.complex64, np.complex128]
        else:
            dtypes = [np.complex64]

        n = 20
        for tp in dtypes:
            dtype = np.dtype(tp)
            from pytools import match_precision
            real_dtype = match_precision(np.dtype(np.float64), dtype)

            z = (curand((n,), real_dtype).astype(dtype)
                    + 1j*curand((n,), real_dtype).astype(dtype))

            assert la.norm(z.get().real - z.real.get()) == 0
            assert la.norm(z.get().imag - z.imag.get()) == 0
            assert la.norm(z.get().conj() - z.conj().get()) == 0

    @mark_cuda_test
    def test_pass_slice_to_kernel(self):
        mod = SourceModule("""
        __global__ void twice(float *a)
        {
          const int i = threadIdx.x + blockIdx.x * blockDim.x;
          a[i] *= 2;
        }
        """)

        multiply_them = mod.get_function("twice")

        a = np.ones(256**2, np.float32)
        a_gpu = gpuarray.to_gpu(a)

        multiply_them(a_gpu[256:-256], block=(256, 1, 1), grid=(254, 1))

        a = a_gpu.get()
        assert (a[255:257] == np.array([1, 2], np.float32)).all()
        assert (a[255*256-1:255*256+1] == np.array([2, 1], np.float32)).all()

    @mark_cuda_test
    def test_scan(self):
        from pycuda.scan import ExclusiveScanKernel, InclusiveScanKernel
        for cls in [ExclusiveScanKernel, InclusiveScanKernel]:
            scan_kern = cls(np.int32, "a+b", "0")

            for n in [
                    10, 2**10-5, 2**10,
                    2**20-2**18,
                    2**20-2**18+5,
                    2**10+5,
                    2**20+5,
                    2**20, 2**24
                    ]:
                host_data = np.random.randint(0, 10, n).astype(np.int32)
                gpu_data = gpuarray.to_gpu(host_data)

                scan_kern(gpu_data)

                desired_result = np.cumsum(host_data, axis=0)
                if cls is ExclusiveScanKernel:
                    desired_result -= host_data

                assert (gpu_data.get() == desired_result).all()

    @mark_cuda_test
    def test_stride_preservation(self):
        A = np.random.rand(3, 3)
        AT = A.T
        print (AT.flags.f_contiguous, AT.flags.c_contiguous)
        AT_GPU = gpuarray.to_gpu(AT)
        print (AT_GPU.flags.f_contiguous, AT_GPU.flags.c_contiguous)
        assert np.allclose(AT_GPU.get(), AT)

    @mark_cuda_test
    def test_vector_fill(self):
        a_gpu = gpuarray.GPUArray(100, dtype=gpuarray.vec.float3)
        a_gpu.fill(gpuarray.vec.make_float3(0.0, 0.0, 0.0))
        a = a_gpu.get()
        assert a.dtype is gpuarray.vec.float3

    @mark_cuda_test
    def test_create_complex_zeros(self):
        gpuarray.zeros(3, np.complex64)

    @mark_cuda_test
    def test_reshape(self):
        a = np.arange(128).reshape(8, 16).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)

        # different ways to specify the shape
        a_gpu.reshape(4, 32)
        a_gpu.reshape((4, 32))
        a_gpu.reshape([4, 32])

    @mark_cuda_test
    def test_view(self):
        a = np.arange(128).reshape(8, 16).astype(np.float32)
        a_gpu = gpuarray.to_gpu(a)

        # same dtype
        view = a_gpu.view()
        assert view.shape == a_gpu.shape and view.dtype == a_gpu.dtype

        # larger dtype
        view = a_gpu.view(np.complex64)
        assert view.shape == (8, 8) and view.dtype == np.complex64

        # smaller dtype
        view = a_gpu.view(np.int16)
        assert view.shape == (8, 32) and view.dtype == np.int16

    @mark_cuda_test
    def test_struct_reduce(self):
        preamble = """
        struct minmax_collector
        {
            float cur_min;
            float cur_max;

            __device__
            minmax_collector()
            { }

            __device__
            minmax_collector(float cmin, float cmax)
            : cur_min(cmin), cur_max(cmax)
            { }

            __device__ minmax_collector(minmax_collector const &src)
            : cur_min(src.cur_min), cur_max(src.cur_max)
            { }

            __device__ minmax_collector(minmax_collector const volatile &src)
            : cur_min(src.cur_min), cur_max(src.cur_max)
            { }

            __device__ minmax_collector volatile &operator=(
                minmax_collector const &src) volatile
            {
                cur_min = src.cur_min;
                cur_max = src.cur_max;
                return *this;
            }
        };

        __device__
        minmax_collector agg_mmc(minmax_collector a, minmax_collector b)
        {
            return minmax_collector(
                fminf(a.cur_min, b.cur_min),
                fmaxf(a.cur_max, b.cur_max));
        }
        """
        mmc_dtype = np.dtype([("cur_min", np.float32), ("cur_max", np.float32)])

        from pycuda.curandom import rand as curand
        a_gpu = curand((20000,), dtype=np.float32)
        a = a_gpu.get()

        from pycuda.tools import register_dtype
        register_dtype(mmc_dtype, "minmax_collector")

        from pycuda.reduction import ReductionKernel
        red = ReductionKernel(mmc_dtype,
                neutral="minmax_collector(10000, -10000)",
                # FIXME: needs infinity literal in real use, ok here
                reduce_expr="agg_mmc(a, b)", map_expr="minmax_collector(x[i], x[i])",
                arguments="float *x", preamble=preamble)

        minmax = red(a_gpu).get()
        #print minmax["cur_min"], minmax["cur_max"]
        #print np.min(a), np.max(a)

        assert minmax["cur_min"] == np.min(a)
        assert minmax["cur_max"] == np.max(a)

    @mark_cuda_test
    def test_view_and_strides(self):
        from pycuda.curandom import rand as curand

        X = curand((5, 10), dtype=np.float32)
        Y = X[:3, :5]
        y = Y.view()

        assert y.shape == Y.shape
        assert y.strides == Y.strides

        import pytest
        with pytest.raises(AssertionError):
            assert (y.get() == X.get()[:3, :5]).all()

    @mark_cuda_test
    def test_scalar_comparisons(self):
        a = np.array([1.0, 0.25, 0.1, -0.1, 0.0])
        a_gpu = gpuarray.to_gpu(a)
        
        x_gpu = a_gpu > 0.25
        x = (a > 0.25).astype(a.dtype)
        assert (x == x_gpu.get()).all()

        x_gpu = a_gpu <= 0.25
        x = (a <= 0.25).astype(a.dtype)
        assert (x == x_gpu.get()).all()

        x_gpu = a_gpu == 0.25
        x = (a == 0.25).astype(a.dtype)
        assert (x == x_gpu.get()).all()

        x_gpu = a_gpu == 1  # using an integer scalar
        x = (a == 1).astype(a.dtype)
        assert (x == x_gpu.get()).all()

        


if __name__ == "__main__":
    # make sure that import failures get reported, instead of skipping the tests.
    import pycuda.autoinit  # noqa

    if len(sys.argv) > 1:
        exec (sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])

########NEW FILE########
__FILENAME__ = elwise-perf
#! /usr/bin/env python
import pycuda.driver as drv
import pycuda.autoinit
import numpy
import numpy.linalg as la




def main():
    from pytools import Table
    tbl = Table()
    tbl.add_row(("size [MiB]", "time [s]", "mem.bw [GB/s]"))

    import pycuda.gpuarray as gpuarray

    # they're floats, i.e. 4 bytes each
    for power in range(10, 28):
        size = 1<<power
        print size

        a = gpuarray.empty((size,), dtype=numpy.float32)
        b = gpuarray.empty_like(a)
        a.fill(1)
        b.fill(2)

        if power > 20:
            count = 10
        else:
            count = 100

        elapsed = [0]

        def add_timer(_, time):
            elapsed[0] += time()

        for i in range(count):
            a.mul_add(1, b, 2, add_timer)

        bytes = a.nbytes*count*3
        bytes = a.nbytes*count*3

        tbl.add_row((a.nbytes/(1<<20), elapsed[0]/count, bytes/elapsed[0]/1e9))

    print tbl
        




if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = measure_gpuarray_speed
#! /usr/bin/env python
import pycuda.driver as drv
import pycuda.autoinit
import numpy
import numpy.linalg as la




def main():
    import pycuda.gpuarray as gpuarray

    sizes = []
    times_gpu = []
    flops_gpu = []
    flops_cpu = []
    times_cpu = []

    from pycuda.tools import bitlog2
    max_power = bitlog2(drv.mem_get_info()[0]) - 2
    # they're floats, i.e. 4 bytes each
    for power in range(10, max_power):
        size = 1<<power
        print size
        sizes.append(size)
        a = gpuarray.zeros((size,), dtype=numpy.float32)
        b = gpuarray.zeros((size,), dtype=numpy.float32)
        b.fill(1)

        if power > 20:
            count = 100
        else:
            count = 1000

        # gpu -----------------------------------------------------------------
        start = drv.Event()
        end = drv.Event()
        start.record()

        for i in range(count):
            a+b

        end.record()
        end.synchronize()

        secs = start.time_till(end)*1e-3

        times_gpu.append(secs/count)
        flops_gpu.append(size)
        del a
        del b

        # cpu -----------------------------------------------------------------
        a_cpu = numpy.random.randn(size).astype(numpy.float32)
        b_cpu = numpy.random.randn(size).astype(numpy.float32)

        #start timer
        from time import time
        start = time()
        for i in range(count):
            a_cpu + b_cpu
        secs = time() - start

        times_cpu.append(secs/count)
        flops_cpu.append(size)


    # calculate pseudo flops
    flops_gpu = [f/t for f, t in zip(flops_gpu,times_gpu)]
    flops_cpu = [f/t for f, t in zip(flops_cpu,times_cpu)]

    from pytools import Table
    tbl = Table()
    tbl.add_row(("Size", "Time GPU", "Size/Time GPU",
        "Time CPU","Size/Time CPU","GPU vs CPU speedup"))
    for s, t, f, t_cpu, f_cpu in zip(sizes, times_gpu, flops_gpu, times_cpu, flops_cpu):
        tbl.add_row((s, t, f, t_cpu, f_cpu, f/f_cpu))
    print tbl





if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = reduction-perf
from __future__ import division
import pycuda.autoinit
import pycuda.gpuarray as gpuarray
import pycuda.driver as cuda
import numpy



def main():
    from pytools import Table
    tbl = Table()
    tbl.add_row(("type", "size [MiB]", "time [ms]", "mem.bw [GB/s]"))

    from random import shuffle
    for dtype_out in [numpy.float32, numpy.float64]:
        for ex in range(15,27):
            sz = 1 << ex
            print sz

            from pycuda.curandom import rand as curand
            a_gpu = curand((sz,))
            b_gpu = curand((sz,))
            assert sz == a_gpu.shape[0]
            assert len(a_gpu.shape) == 1

            from pycuda.reduction import get_sum_kernel, get_dot_kernel
            krnl = get_dot_kernel(dtype_out, a_gpu.dtype)

            elapsed = [0]

            def wrap_with_timer(f):
                def result(*args, **kwargs):
                    start = cuda.Event()
                    stop = cuda.Event()
                    start.record()
                    f(*args, **kwargs)
                    stop.record()
                    stop.synchronize()
                    elapsed[0] += stop.time_since(start)

                return result

            # warm-up
            for i in range(3):
                krnl(a_gpu, b_gpu)

            cnt = 10

            for i in range(cnt):
                krnl(a_gpu, b_gpu,
                #krnl(a_gpu, 
                        kernel_wrapper=wrap_with_timer)

            bytes = a_gpu.nbytes*2*cnt
            secs = elapsed[0]*1e-3

            tbl.add_row((str(dtype_out), a_gpu.nbytes/(1<<20), elapsed[0]/cnt, bytes/secs/1e9))

    print tbl

if __name__ == "__main__":
    main()

########NEW FILE########
