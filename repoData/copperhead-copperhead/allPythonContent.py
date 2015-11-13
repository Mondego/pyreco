__FILENAME__ = build-env
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
EnsureSConsVersion(1,2)

import os

import inspect
import platform

def get_cuda_paths():
  """Determines CUDA {bin,lib,include} paths
  
  returns (bin_path,lib_path,inc_path)
  """

  # determine defaults
  if os.name == 'nt':
    bin_path = 'C:/CUDA/bin'
    lib_path = 'C:/CUDA/lib'
    inc_path = 'C:/CUDA/include'
  elif os.name == 'posix':
    bin_path = '/usr/local/cuda/bin'
    lib_path = '/usr/local/cuda/lib'
    inc_path = '/usr/local/cuda/include'
  else:
    raise ValueError, 'Error: unknown OS.  Where is nvcc installed?'
  
  if platform.system() != 'Darwin' and platform.machine()[-2:] == '64':
    lib_path += '64'

  # override with environement variables
  if 'CUDA_BIN_PATH' in os.environ:
    bin_path = os.path.abspath(os.environ['CUDA_BIN_PATH'])
  if 'CUDA_LIB_PATH' in os.environ:
    lib_path = os.path.abspath(os.environ['CUDA_LIB_PATH'])
  if 'CUDA_INC_PATH' in os.environ:
    inc_path = os.path.abspath(os.environ['CUDA_INC_PATH'])

  return (bin_path,lib_path,inc_path)


def getTools():
  result = []
  if os.name == 'nt':
    result = ['default', 'msvc']
  elif os.name == 'posix':
    result = ['default', 'gcc']
  else:
    result = ['default']
  return result;


OldEnvironment = Environment;


# this dictionary maps the name of a compiler program to a dictionary mapping the name of
# a compiler switch of interest to the specific switch implementing the feature
gCompilerOptions = {
    'gcc' : {'warn_all' : '-Wall', 'warn_errors' : '-Werror', 'optimization' : '-O2', 'debug' : '-g',  'exception_handling' : '',      'omp' : '-fopenmp'},
    'g++' : {'warn_all' : '-Wall', 'warn_errors' : '-Werror', 'optimization' : '-O2', 'debug' : '-g',  'exception_handling' : '',      'omp' : '-fopenmp'},
    'cl'  : {'warn_all' : '/Wall', 'warn_errors' : '/WX',     'optimization' : '/Ox', 'debug' : ['/Zi', '-D_DEBUG', '/MTd'], 'exception_handling' : '/EHsc', 'omp' : '/openmp'}
  }


# this dictionary maps the name of a linker program to a dictionary mapping the name of
# a linker switch of interest to the specific switch implementing the feature
gLinkerOptions = {
    'gcc' : {'debug' : ''},
    'g++' : {'debug' : ''},
    'link'  : {'debug' : '/debug'}
  }


def getCFLAGS(mode, backend, warn, warnings_as_errors, CC):
  result = []
  if mode == 'release':
    # turn on optimization
    result.append(gCompilerOptions[CC]['optimization'])
  elif mode == 'debug':
    # turn on debug mode
    result.append(gCompilerOptions[CC]['debug'])

  # generate omp code
  if backend == 'omp':
    result.append(gCompilerOptions[CC]['omp'])
  
  if warn:
    # turn on all warnings
    result.append(gCompilerOptions[CC]['warn_all'])

  if warnings_as_errors:
    # treat warnings as errors
    result.append(gCompilerOptions[CC]['warn_errors'])

  return result


def getCXXFLAGS(mode, backend, warn, warnings_as_errors, CXX):
  result = []
  if mode == 'release':
    # turn on optimization
    result.append(gCompilerOptions[CXX]['optimization'])
  elif mode == 'debug':
    # turn on debug mode
    result.append(gCompilerOptions[CXX]['debug'])
    result.append('-DTRACE')

  # enable exception handling
  result.append(gCompilerOptions[CXX]['exception_handling'])
  
  # generate omp code
  if backend == 'omp':
    result.append(gCompilerOptions[CXX]['omp'])

  if warn:
    # turn on all warnings
    result.append(gCompilerOptions[CXX]['warn_all'])

  if warnings_as_errors:
    # treat warnings as errors
    result.append(gCompilerOptions[CXX]['warn_errors'])

  return result


def getNVCCFLAGS(mode, backend, arch):
  result = ['-arch=' + arch]
  if mode == 'debug':
    # turn on debug mode
    # XXX make this work when we've debugged nvcc -G
    #result.append('-G')
    pass
  # force 64b code on darwin
  if platform.platform()[:6] == 'Darwin':
    result.append('-m64')

  return result


def getLINKFLAGS(mode, backend, LINK):
  result = []
  if mode == 'debug':
    # turn on debug mode
    result.append(gLinkerOptions[LINK]['debug'])

  # XXX make this portable
  if backend == 'ocelot':
    result.append(os.popen('OcelotConfig -l').read().split())

  return result


def Environment():
  # allow the user discretion to choose the MSVC version
  vars = Variables()
  if os.name == 'nt':
    vars.Add(EnumVariable('MSVC_VERSION', 'MS Visual C++ version', None, allowed_values=('8.0', '9.0', '10.0')))

  # add a variable to handle the device backend
  backend_variable = EnumVariable('backend', 'The parallel device backend to target', 'cuda',
                                  allowed_values = ('cuda', 'omp', 'ocelot'))
  vars.Add(backend_variable)

  # add a variable to handle RELEASE/DEBUG mode
  vars.Add(EnumVariable('mode', 'Release versus debug mode', 'release',
                        allowed_values = ('release', 'debug')))

  # add a variable to handle compute capability
  vars.Add(EnumVariable('arch', 'Compute capability code generation', 'sm_10',
                        allowed_values = ('sm_10', 'sm_11', 'sm_12', 'sm_13', 'sm_20', 'sm_21')))

  # add a variable to handle warnings
  if os.name == 'posix':
    vars.Add(BoolVariable('Wall', 'Enable all compilation warnings', 1))
  else:
    vars.Add(BoolVariable('Wall', 'Enable all compilation warnings', 0))

  # add a variable to treat warnings as errors
  vars.Add(BoolVariable('Werror', 'Treat warnings as errors', 0))

  # create an Environment, pull in user PATH
  env = OldEnvironment(tools = getTools(), variables = vars,
                       ENV={'PATH' : os.environ['PATH']})

  # get the absolute path to the directory containing
  # this source file
  thisFile = inspect.getabsfile(Environment)
  thisDir = os.path.dirname(thisFile)

  # enable nvcc
  env.Tool('nvcc', toolpath = [os.path.join(thisDir)])

  # get C compiler switches
  env.Append(CFLAGS = getCFLAGS(env['mode'], env['backend'], env['Wall'], env['Werror'], env.subst('$CC')))

  # get CXX compiler switches
  env.Append(CXXFLAGS = getCXXFLAGS(env['mode'], env['backend'], env['Wall'], env['Werror'], env.subst('$CXX')))

  # get NVCC compiler switches
  env.Append(NVCCFLAGS = getNVCCFLAGS(env['mode'], env['backend'], env['arch']))

  env.Append(SHNVCCFLAGS = getNVCCFLAGS(env['mode'], env['backend'], env['arch']))

  # get linker switches
  env.Append(LINKFLAGS = getLINKFLAGS(env['mode'], env['backend'], env.subst('$LINK')))
   
  # get CUDA paths
  (cuda_exe_path,cuda_lib_path,cuda_inc_path) = get_cuda_paths()
  env.Append(LIBPATH = [cuda_lib_path])
  env.Append(CPPPATH = [cuda_inc_path])

  env.Replace(CUDA_PATHS = (cuda_lib_path, cuda_inc_path))

  # link against backend-specific runtimes
  # XXX we shouldn't have to link against cudart unless we're using the
  #     cuda runtime, but cudafe inserts some dependencies when compiling .cu files
  # XXX ideally this gets handled in nvcc.py if possible
  #env.Append(LIBS = 'cudart')

  if env['backend'] == 'ocelot':
    if os.name == 'posix':
      env.Append(LIBPATH = ['/usr/local/lib'])
    else:
      raise ValueError, "Unknown OS.  What is the Ocelot library path?"
  elif env['backend'] == 'omp':
    if os.name == 'posix':
      env.Append(LIBS = ['gomp'])
    elif os.name == 'nt':
      env.Append(LIBS = ['VCOMP'])
    else:
      raise ValueError, "Unknown OS.  What is the name of the OpenMP library?"

  # import the LD_LIBRARY_PATH so we can run commands which depend
  # on shared libraries
  # XXX we should probably just copy the entire environment
  # If LD_LIBRARY_PATH doesn't exist, just don't add it
  try:
    if os.name == 'posix':
      if env['PLATFORM'] == "darwin":
        env['ENV']['DYLD_LIBRARY_PATH'] = os.environ['DYLD_LIBRARY_PATH']
      else:
        env['ENV']['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH']
  except Exception:
    #Environment variable not defined
    pass
  # generate help text
  Help(vars.GenerateHelpText(env))


  # enable Doxygen
  env.Tool('dox', toolpath = [os.path.join(thisDir)])

  
  return env


########NEW FILE########
__FILENAME__ = dox
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

import os
import SCons.Builder

def DoxygenEmitter(source, target, env):
    input_dox_file = str(source[0])
    head, tail = os.path.split(input_dox_file)
    html_dir = env.Dir(os.path.join(head, 'html'))
    env.Precious(html_dir)
    env.Clean(html_dir, html_dir)
    return ([html_dir], source)

def generate(env):
    doxygen_builder = SCons.Builder.Builder(
        action = "cd ${SOURCE.dir} && ${DOXYGEN} ${SOURCE.file}",
        emitter = DoxygenEmitter,
        target_factory = env.fs.Entry,
        single_source = True)
    env.Append(BUILDERS = {'Doxygen' : doxygen_builder})
    env.AppendUnique(DOXYGEN='doxygen')

def exists(env):
    return env.Detect('doxygen')

########NEW FILE########
__FILENAME__ = nvcc
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
"""SCons.Tool.nvcc

Tool-specific initialization for NVIDIA CUDA Compiler.

There normally shouldn't be any need to import this module directly.
It will usually be imported through the generic SCons.Tool.Tool()
selection method.

"""

import SCons.Tool
import SCons.Scanner.C
import SCons.Defaults
import os
import platform


def get_cuda_paths():
  """Determines CUDA {bin,lib,include} paths
  
  returns (bin_path,lib_path,inc_path)
  """

  # determine defaults
  if os.name == 'nt':
    bin_path = 'C:/CUDA/bin'
    lib_path = 'C:/CUDA/lib'
    inc_path = 'C:/CUDA/include'
  elif os.name == 'posix':
    bin_path = '/usr/local/cuda/bin'
    lib_path = '/usr/local/cuda/lib'
    inc_path = '/usr/local/cuda/include'
  else:
    raise ValueError, 'Error: unknown OS.  Where is nvcc installed?'
   
  if platform.machine()[-2:] == '64':
    lib_path += '64'

  # override with environement variables
  if 'CUDA_BIN_PATH' in os.environ:
    bin_path = os.path.abspath(os.environ['CUDA_BIN_PATH'])
  if 'CUDA_LIB_PATH' in os.environ:
    lib_path = os.path.abspath(os.environ['CUDA_LIB_PATH'])
  if 'CUDA_INC_PATH' in os.environ:
    inc_path = os.path.abspath(os.environ['CUDA_INC_PATH'])

  return (bin_path,lib_path,inc_path)



CUDASuffixes = ['.cu']

# make a CUDAScanner for finding #includes
# cuda uses the c preprocessor, so we can use the CScanner
CUDAScanner = SCons.Scanner.C.CScanner()

def add_common_nvcc_variables(env):
  """
  Add underlying common "NVIDIA CUDA compiler" variables that
  are used by multiple builders.
  """

  # "NVCC common command line"
  if not env.has_key('_NVCCCOMCOM'):
    # nvcc needs '-I' prepended before each include path, regardless of platform
    env['_NVCCWRAPCPPPATH'] = '${_concat("-I ", CPPPATH, "", __env__)}'
    # prepend -Xcompiler before each flag
    env['_NVCCWRAPCFLAGS'] =     '${_concat("-Xcompiler ", CFLAGS,     "", __env__)}'
    env['_NVCCWRAPSHCFLAGS'] =   '${_concat("-Xcompiler ", SHCFLAGS,   "", __env__)}'
    env['_NVCCWRAPCCFLAGS'] =   '${_concat("-Xcompiler ", CCFLAGS,   "", __env__)}'
    env['_NVCCWRAPSHCCFLAGS'] = '${_concat("-Xcompiler ", SHCCFLAGS, "", __env__)}'
    # assemble the common command line
    env['_NVCCCOMCOM'] = '${_concat("-Xcompiler ", CPPFLAGS, "", __env__)} $_CPPDEFFLAGS $_NVCCWRAPCPPPATH'

def generate(env):
  """
  Add Builders and construction variables for CUDA compilers to an Environment.
  """

  # create a builder that makes PTX files from .cu files
  ptx_builder = SCons.Builder.Builder(action = '$NVCC -ptx $NVCCFLAGS $_NVCCWRAPCFLAGS $NVCCWRAPCCFLAGS $_NVCCCOMCOM $SOURCES -o $TARGET',
                                      emitter = {},
                                      suffix = '.ptx',
                                      src_suffix = CUDASuffixes)
  env['BUILDERS']['PTXFile'] = ptx_builder

  # create builders that make static & shared objects from .cu files
  static_obj, shared_obj = SCons.Tool.createObjBuilders(env)

  for suffix in CUDASuffixes:
    # Add this suffix to the list of things buildable by Object
    static_obj.add_action('$CUDAFILESUFFIX', '$NVCCCOM')
    shared_obj.add_action('$CUDAFILESUFFIX', '$SHNVCCCOM')
    static_obj.add_emitter(suffix, SCons.Defaults.StaticObjectEmitter)
    shared_obj.add_emitter(suffix, SCons.Defaults.SharedObjectEmitter)

    # Add this suffix to the list of things scannable
    SCons.Tool.SourceFileScanner.add_scanner(suffix, CUDAScanner)

  add_common_nvcc_variables(env)

  # set the "CUDA Compiler Command" environment variable
  # windows is picky about getting the full filename of the executable
  if os.name == 'nt':
    env['NVCC'] = 'nvcc.exe'
    env['SHNVCC'] = 'nvcc.exe'
  else:
    env['NVCC'] = 'nvcc'
    env['SHNVCC'] = 'nvcc'
  
  # set the include path, and pass both c compiler flags and c++ compiler flags
  env['NVCCFLAGS'] = SCons.Util.CLVar('')
  env['SHNVCCFLAGS'] = SCons.Util.CLVar('') + ' -shared'
    
  # 'NVCC Command'
  env['NVCCCOM']   = '$NVCC -o $TARGET -c $NVCCFLAGS $_NVCCWRAPCFLAGS $NVCCWRAPCCFLAGS $_NVCCCOMCOM $SOURCES'
  env['SHNVCCCOM'] = '$SHNVCC -o $TARGET -c $SHNVCCFLAGS $_NVCCWRAPSHCFLAGS $_NVCCWRAPSHCCFLAGS $_NVCCCOMCOM $SOURCES'
  
  # the suffix of CUDA source files is '.cu'
  env['CUDAFILESUFFIX'] = '.cu'

  # XXX add code to generate builders for other miscellaneous
  # CUDA files here, such as .gpu, etc.

  # XXX intelligently detect location of nvcc and cuda libraries here
  (bin_path,lib_path,inc_path) = get_cuda_paths()
    
  env.PrependENVPath('PATH', bin_path)

def exists(env):
  return env.Detect('nvcc')


########NEW FILE########
__FILENAME__ = backend
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
import backendcompiler as BC
import conversions

def execute(ast, M):
    assert(len(M.entry_points) == 1)
    entry_point = M.entry_points[0]
    backend_ast = conversions.front_to_back_node(ast)
    c = BC.Compiler(entry_point, M.tag)
    result = c(backend_ast)
    M.compiler_output = result
    M.wrap_info = (BC.hash(), (BC.wrap_result_type(), BC.wrap_name()),
                   zip(BC.wrap_arg_types(), BC.wrap_arg_names()))
    return []

########NEW FILE########
__FILENAME__ = binarygenerator
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#


from __future__ import division
import coresyntax as S
import coretypes as T
import inspect
import pltools
import copy
import numpy as np
import parsetypes
import pdb
from itertools import ifilter
import codepy.bpl
import codepy.cuda
import codepy.cgen as CG
import pickle
import os

def prepare_compilation(M):
    from ..runtime import cuda_support
    if cuda_support:
        from ..runtime import cuda_tag
        if M.tag == cuda_tag:
            return prepare_cuda_compilation(M)
    return prepare_host_compilation(M)

def prepare_cuda_compilation(M):
    assert(len(M.entry_points) == 1)
    procedure_name = M.entry_points[0]
    hash, (wrap_type, wrap_name), wrap_args = M.wrap_info
    wrap_decl = CG.FunctionDeclaration(CG.Value(wrap_type, wrap_name),
                                       [CG.Value(x, y) for x, y in wrap_args])
    host_module = codepy.bpl.BoostPythonModule(max_arity=max(10,M.arity),
                                               use_private_namespace=False)
    host_module.add_to_preamble([
        CG.Include("prelude/runtime/cunp.hpp"),
        CG.Include("prelude/runtime/cuarray.hpp"),
        CG.Line('using namespace copperhead;')])
    device_module = codepy.cuda.CudaModule(host_module)
    hash_namespace_open = CG.Line('namespace %s {' % hash)
    hash_namespace_close = CG.Line('}')
    using_declaration = CG.Line('using namespace %s;' % hash)
    host_module.add_to_preamble([hash_namespace_open, wrap_decl,
                                 hash_namespace_close, using_declaration])

    host_module.add_to_init([CG.Statement(
                "boost::python::def(\"%s\", &%s)" % (
                    procedure_name, wrap_name))])

    device_module.add_to_preamble(
        [CG.Include("prelude/prelude.h"),
         CG.Include("prelude/runtime/cunp.hpp"),
         CG.Include("prelude/runtime/make_cuarray.hpp"),
         CG.Include("prelude/runtime/make_sequence.hpp"),
         CG.Include("prelude/runtime/tuple_utilities.hpp"),
         CG.Line('using namespace copperhead;')])
    wrapped_cuda_code = [CG.Line(M.compiler_output)]
    device_module.add_to_module(wrapped_cuda_code)
    M.device_module = device_module
    if M.compile:
        M.current_toolchains = (M.toolchains.host_toolchain,
                                M.toolchains.nvcc_toolchain)
    else:
        M.current_toolchains = (M.toolchains.null_host_toolchain,
                                M.toolchains.null_nvcc_toolchain)
    M.codepy_module = device_module
    M.code = (str(host_module.generate()), str(device_module.generate()))
    M.kwargs = dict(host_kwargs=dict(cache_dir=M.code_dir),
                    nvcc_kwargs=dict(cache_dir=M.code_dir),
                    debug=M.verbose)
    return []

def prepare_host_compilation(M):
    assert(len(M.entry_points) == 1)
    procedure_name = M.entry_points[0]
    hash, (wrap_type, wrap_name), wrap_args = M.wrap_info
    host_module = codepy.bpl.BoostPythonModule(max_arity=max(10,M.arity),
                                               use_private_namespace=False)
    host_module.add_to_preamble([CG.Include("prelude/prelude.h"),
                                 CG.Include("prelude/runtime/cunp.hpp"),
                                 CG.Include("prelude/runtime/make_cuarray.hpp"),
                                 CG.Include("prelude/runtime/make_sequence.hpp"),
                                 CG.Include("prelude/runtime/tuple_utilities.hpp"),
                                 CG.Line('using namespace copperhead;')])

    host_module.add_to_init([CG.Statement(
                "boost::python::def(\"%s\", &%s)" % (
                    procedure_name, wrap_name))])
    wrapped_code = [CG.Line(M.compiler_output),
                    CG.Line('using namespace %s;' % hash)]
    host_module.add_to_module(wrapped_code)
    M.codepy_module = host_module
    if M.compile:
        M.current_toolchains = (M.toolchains.host_toolchain,)
    else:
        M.current_toolchains = (M.toolchains.null_host_toolchain,)
    M.code = (str(host_module.generate()),)
    M.kwargs = dict(cache_dir=M.code_dir,
                    debug=M.verbose)
    return []

def make_binary(M):
    assert(len(M.entry_points) == 1)
    procedure_name = M.entry_points[0]

    code = M.code
    codepy_module = M.codepy_module
    toolchains = M.current_toolchains
    kwargs = M.kwargs
    try:
        module = codepy_module.compile(*toolchains, **kwargs)
    except Exception as e:
        if isinstance(e, NotImplementedError):
            raise e
        for m in code:
            print m
        print e
        raise e

    name = M.input_types.keys()[0]
    input_type = M.input_types[name]
    #Unmark name
    input_name = name[1:]
    
    copperhead_info = (input_name, input_type, M.tag)
    module_dir, module_file = os.path.split(module.__file__)
    info_file = open(os.path.join(module_dir, 'cuinfo'), 'w')
    pickle.dump(copperhead_info, info_file)
    info_file.close()
    return code, getattr(module, procedure_name)

########NEW FILE########
__FILENAME__ = conversions
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
import backendtypes as ET
import coretypes as T

import backendsyntax as ES
import coresyntax as S

def back_to_front_type(x):
    concrete = ET.unvariate(x)
    if isinstance(concrete, ET.Sequence):
        sub = back_to_front_type(concrete.sub())
        return T.Seq(sub)
    elif isinstance(concrete, ET.Tuple):
        return T.Tuple(*[back_to_front_type(y) for y in concrete])
    elif isinstance(concrete, ET.Monotype):
        name = str(x)
        if name == 'Int32':
            return T.Int
        elif name == 'Int64':
            return T.Long
        elif name == 'Bool':
            return T.Bool
        elif name == 'Float32':
            return T.Float
        elif name == 'Float64':
            return T.Double
        else:
            raise ValueError("Unknown monotype %s" % name)
    else:
        raise ValueError("Unknown type")


def front_to_back_type(x):
    if isinstance(x, T.Polytype):
        variables = [ET.Monotype(str(y)) for y in x.variables]
        sub = front_to_back_type(x.monotype())
        return ET.Polytype(variables, sub)
    elif isinstance(x, T.Tuple):
        subs = [front_to_back_type(y) for y in x.parameters]
        return ET.Tuple(*subs)
    elif isinstance(x, T.Fn):
        args = front_to_back_type(x.parameters[0])
        result = front_to_back_type(x.parameters[1])
        return ET.Fn(args, result)
    elif isinstance(x, T.Seq):
        sub = front_to_back_type(x.unbox())
        return ET.Sequence(sub)
    elif isinstance(x, T.Monotype):
        if str(x) == str(T.Int):
            return ET.Int32
        elif str(x) == str(T.Long):
            return ET.Int64
        elif str(x) == str(T.Float):
            return ET.Float32
        elif str(x) == str(T.Double):
            return ET.Float64
        elif str(x) == str(T.Bool):
            return ET.Bool
        elif str(x) == str(T.Void):
            return ET.Void
    elif isinstance(x, str):
        return ET.Monotype(str(x))
    raise ValueError("Can't convert %s to backendtypes" % str(x))

def front_to_back_node(x):
    if isinstance(x, list):
        subs = [front_to_back_node(y) for y in x]
        return ES.Suite(subs)
    elif isinstance(x, S.Name):
        name = ES.Name(x.id,
                       front_to_back_type(x.type))
        return name
    elif isinstance(x, S.Number):
        literal = ES.Literal(str(x),
                       front_to_back_type(x.type))
        return literal
    elif isinstance(x, S.Tuple):
        subs = [front_to_back_node(y) for y in x]
        tup = ES.Tuple(subs,
                       front_to_back_type(x.type))
        return tup
    elif isinstance(x, S.Apply):
        fn = front_to_back_node(x.function())
        args = [front_to_back_node(y) for y in x.arguments()]
        arg_types = [front_to_back_type(y.type) for y in x.arguments()]
        appl = ES.Apply(fn, ES.Tuple(args,
                                     ET.Tuple(arg_types)))
        return appl
    elif isinstance(x, S.Bind):
        lhs = front_to_back_node(x.binder())
        rhs = front_to_back_node(x.value())
        return ES.Bind(lhs, rhs)
    elif isinstance(x, S.Return):
        val = front_to_back_node(x.value())
        return ES.Return(val)
    elif isinstance(x, S.Cond):
        test = front_to_back_node(x.test())
        body = front_to_back_node(x.body())
        orelse = front_to_back_node(x.orelse())
        return ES.Cond(test, body, orelse)
    elif isinstance(x, S.Lambda):
        args = [front_to_back_node(y) for y in x.formals()]
        body = front_to_back_node(x.body())
        lamb = ES.Lambda(ES.Tuple(args), body,
                         front_to_back_type(x.type))
        return lamb
    elif isinstance(x, S.Closure):
        closed_over = [front_to_back_node(y) for y in x.closed_over()]
        closed_over_types = [front_to_back_type(y.type) for y in x.closed_over()]
        body = front_to_back_node(x.body())
        closure = ES.Closure(ES.Tuple(closed_over,
                                      ET.Tuple(closed_over_types)),
                             body,
                             front_to_back_type(x.type))
        return closure
    elif isinstance(x, S.Procedure):
        name = front_to_back_node(x.name())
        formals = [front_to_back_node(y) for y in x.formals()]
        formal_types = [front_to_back_type(y.type) for y in x.formals()]
        body = front_to_back_node(x.body())
        proc = ES.Procedure(name, ES.Tuple(formals,
                                           ET.Tuple(formal_types)),
                            body,
                            front_to_back_type(x.name().type))
        return proc
    elif isinstance(x, S.Subscript):
        base = front_to_back_node(x.value())
        sl = front_to_back_node(x.slice())
        return ES.Subscript(base,
                            sl,
                            front_to_back_type(x.type))

########NEW FILE########
__FILENAME__ = coresyntax
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

# The Copperhead AST

from pltools import strlist
import copy
import utility as U

def selectCopy(dest, template, items):
    for item in items:
        if hasattr(template, item):
            setattr(dest, item, copy.copy(getattr(template, item))) 

def _indent(text, spaces=4):
    'Indent every line in the given text by a fixed number of spaces'
    from re import sub
    return sub(r'(?m)^', ' '*spaces, text)

def _bracket(text, bracket):
    'Wrap a string in brackets.'
    return bracket[0]+text+bracket[1]

def _paren(text):
    'Wrap a string in parentheses.'
    return _bracket(text, '()')

class AST(object):
    """
    Base class for objects representing syntax trees.

    This class should not be instanced, only subclassed.  Valid
    subclasses should define:

    - self.parameters: a list of nodes that (may) need to be
                       evaluated in order to evaluate this node.

    - self.variables:  a list of variables bound within this node,
                       e.g., the formal arguments of a lambda expression.

    Optionally, subclasses can define:

    - self.type: Type information about this node

    - self.phase: Phase information about this node
    """

    def children(self):  return getattr(self, 'parameters', [])
    def bindings(self):  return getattr(self, 'variables', [])

    def __repr__(self):
        return self.__class__.__name__ + \
               strlist(self.children(), '()', form=repr)

########################################################################
#
# Expression syntax
#

class Expression(AST):
    pass

# XXX Should phase out slots that alias elements in self.parameters
#     This can lead to confusion when/if we do in-place modifications of
#     expression objects.

# Literal expressions
class Literal(Expression):
    pass

class Number(Literal):
    def __init__(self, val):
        self.val = val
        self.parameters = []

    def __repr__(self): return "Number(%r)" % self.val
    def __str__(self):  return str(self.val)

class Name(Literal):
    def __init__(self, id):
        self.id = id
        self.parameters = []
    def __repr__(self): return "Name(%r)" % self.id
    def __str__(self):  return str(self.id)

# Function definition and application

class Apply(Expression):
    def __init__(self, fn, args):
        self.parameters = [fn] + args

    def __repr__(self):
        fn, args = self.parameters[0], self.parameters[1:]
        return "Apply(%r, %s)" % (fn, strlist(args, '[]', form=repr))

    def __str__(self):
        fn, args = self.parameters[0], self.parameters[1:]
        op = str(fn)
        if not isinstance(fn, (str,Name)): op = _paren(op)
        return op + strlist(args, '()', form=str)

    def function(self): return self.parameters[0]
    def arguments(self): return self.parameters[1:]

class Lambda(Expression):
    def __init__(self, args, body):
        self.variables = args
        self.parameters = [body]

    def __repr__(self):
        v, e = self.variables, self.parameters[0]
        return "Lambda(%s, %r)" % (strlist(v, '[]', form=repr), e)

    def __str__(self):
        v, e = self.variables, self.parameters[0]
        return "lambda " + strlist(v, form=str) + ": " + str(e)

    def formals(self):  return self.variables
    def body(self):     return self.parameters[0]


class Closure(Expression):
    def __init__(self, args, body):
        self.variables = args
        if not isinstance(body, list):
            self.parameters = [body]
        else:
            self.parameters = body

    def __repr__(self):
        v, e = self.variables, self.parameters[0]
        return "Closure(%s, %r)" % (strlist(v,'[]',form=repr), e)

    def __str__(self):
        v, e = self.variables, self.parameters[0]
        return "closure(%s, %s)" % (strlist(v,'[]',form=str), e)

    # XXX somewhat ugly special case for Closure nodes
    def children(self):
        return self.variables + self.parameters

    def closed_over(self):  return self.variables
    def body(self):         return self.parameters[0]

# Compound expressions

class If(Expression):
    def __init__(self, test, body, orelse):
        self.parameters = [test, body, orelse]

    def __str__(self):
        t, b, e = str(self.test()), str(self.body()), str(self.orelse())

        if isinstance(self.body(), Lambda):   b = _paren(b)
        if isinstance(self.orelse(), Lambda): e = _paren(e)

        return "%s if %s else %s" % (b, t, e)

    def test(self):   return self.parameters[0]
    def body(self):   return self.parameters[1]
    def orelse(self): return self.parameters[2]

# Special forms whose semantics differ from usual function call

class Tuple(Expression):
    def __init__(self, *args):
        self.parameters = args

    def __str__(self):
        return strlist(self.parameters, '()', form=str)

    def __iter__(self):
        for i in self.parameters:
            yield i

    def arity(self):
        return len(self.parameters)

class And(Expression):
    def __init__(self, *args):
        self.parameters = args

    def __str__(self):
        return strlist(self.parameters, sep=' and ', form=str)

    def arguments(self):
        return self.parameters

class Or(Expression):
    def __init__(self, *args):
        self.parameters = args

    def __str__(self):
        return strlist(self.parameters, sep=' or ', form=str)

    def arguments(self):
        return self.parameters
    
class Map(Expression):
    def __init__(self, args):
        self.parameters = args

    def __str__(self):
        return 'map' + strlist(self.parameters, '()', form=str)

    def function(self): return self.parameters[0]
    def inputs(self):   return self.parameters[1:]

class Subscript(Expression):
    def __init__(self, value, slice):
        self.parameters = [value, slice]

    def __str__(self):
        return str(self.parameters[0]) + '[' + str(self.parameters[1]) + ']'

    def value(self): return self.parameters[0]
    def slice(self): return self.parameters[1]

class Index(Expression):

    def __init__(self, value):
        self.parameters = [value]

    def __str__(self):
        return strlist(self.parameters, '', sep=', ', form=str)

    def value(self): return self.parameters[0]
    
########################################################################
#
# Statement syntax
#

class Statement(AST):
   pass

class Return(Statement):
    'Return a value from the enclosing procedure definition'
    def __init__(self, value):
        self.parameters = [value]

    def value(self): return self.parameters[0]

    def __str__(self):  return 'return %s' % self.value()

class Bind(Statement):
    'Bind a value to an identifier in the current scope'
    def __init__(self, id, value):
        self.id = id
        self.parameters = [value]

    def binder(self): return self.id
    def value(self): return self.parameters[0]

    def __repr__(self):
        return 'Bind(%r, %r)' % (self.binder(), self.value())

    def __str__(self):
        return '%s = %s' % (self.binder(), self.value())

    
class Cond(Statement):
    'Conditional statement'
    def __init__(self, test, body, orelse):
        self.parameters = [test, body, orelse]

    def __str__(self):
        test   = str(self.test())
        body   = _indent(strlist(self.body(),   sep='\n', form=str))
        orelse = _indent(strlist(self.orelse(), sep='\n', form=str))
                            
        return 'if %s:\n%s\nelse:\n%s' % (test, body, orelse)

    def test(self):   return self.parameters[0]
    def body(self):   return self.parameters[1]
    def orelse(self): return self.parameters[2]

class Procedure(Statement):
    'Define a new procedure'
    def __init__(self, id, args, body, template=None):
        self.variables = [id] + args
        self.parameters = body
        if template:
            selectCopy(self, template, ['entry_point', 'master', 'type', 'phase', 'context', 'typings', 'phases'])

    def __repr__(self):
        id, args = self.variables[0], self.variables[1:]
        body = self.parameters
        return 'Procedure(%r, %r, %r)' % (id, args, body)

    def __str__(self):
        id = self.variables[0]
        args = strlist(self.variables[1:], '()', form=str)
        body   = _indent(strlist(self.parameters, sep='\n', form=str))
        return 'def %s%s:\n%s' % (id, args, body)

    def name(self):    return self.variables[0]
    def formals(self): return self.variables[1:]
    def body(self):    return self.parameters

class Null(Statement):
    def __init__(self):
        pass
    def __repr__(self):
        return 'Null()'
    def __str__(self):
        return ''


########################################################################
#
# Standard tools for processing syntax trees
#

def walk(*roots):
    from collections import deque

    pending = deque(roots)
    while pending:
        next = pending.popleft()
        pending.extend(next.children())
        yield next


class SyntaxVisitor(object):

    def visit_children(self, x):  return self.visit(x.children())

    def visit(self, x):
        from itertools import chain
        if isinstance(x, (list, tuple)):
            return [self.visit(y) for y in x]
        else:
            name = "_"+x.__class__.__name__
            fn = getattr(self, name, self._default)
            return fn(x)

    def _default(self, x):
        if not hasattr(x, 'children'):
            raise ValueError, "can't visit node: %r" % x
        else:
            return self.visit_children(x)

class SyntaxFlattener(object):

    def visit_children(self, x):  return self.visit(x.children())

    def visit(self, x):
        from itertools import chain
        if isinstance(x, (list, tuple)):
            # NOTE: the 'or []' is not necessary in Python 2.6, but is
            #       needed in Python 2.5.
            return chain(*[self.visit(y) or [] for y in x])
        else:
            name = "_"+x.__class__.__name__
            fn = getattr(self, name, self._default)
            return fn(x)

    def _default(self, x):
        if not hasattr(x, 'children'):
            raise ValueError, "can't visit node: %r" % x
        else:
            return self.visit_children(x)


class SyntaxRewrite(object):

    def rewrite_children(self, x):
        x.parameters = self.rewrite(x.parameters)

        # XXX ugly special case for Closure nodes!
        if isinstance(x, Closure):
            x.variables = self.rewrite(x.variables)

        return x
        
    def rewrite(self, x):
        if isinstance(x, (list, tuple)):
            return  [self.rewrite(y) for y in x]
        else:
            name = "_"+x.__class__.__name__
            fn = getattr(self, name, self._default)
            x_copy = copy.copy(x)
            rewritten = fn(x_copy)
            return rewritten

    def _default(self, x):
        if not hasattr(x, 'parameters'):
            raise ValueError, "can't rewrite node: %r" % x
        else:
            return self.rewrite_children(x)


class FreeVariables(SyntaxFlattener):

    def __init__(self, env):
        self.env = env
      
    def _Name(self, x):
        if x.id not in self.env:
            yield x.id
            
    def _Bind(self, x):
        names = U.flatten(x.binder())
        result = list(self.visit(x.value()))
        for name in names:
            self.env[name.id] = name.id
        return result
    
    def filter_bindings(self, x):
        from itertools import ifilter
        bound = [v.id if hasattr(v, 'id') else v for v in x.variables]
        return ifilter(lambda id: id not in bound, self.visit_children(x))

    def _Lambda(self, x):     return self.filter_bindings(x)
    def _Procedure(self, x):
        self.env.begin_scope()
        result = list(self.filter_bindings(x))
        self.env.end_scope()
        return result


class VariableSubstitute(SyntaxRewrite):

    def __init__(self, subst):  self.subst = subst

    def _Name(self, x):
        if x.id in self.subst:
            return copy.copy(self.subst[x.id])
        return x

    def _Lambda(self, x):
        self.subst.begin_scope()
        for v in x.variables:
            # Prevent variables bound by Lambda from being substituted
            self.subst[v.id] = v

        self.rewrite_children(x)
        self.subst.end_scope()
        return x

    def _Procedure(self, x): return self._Lambda(x)

    def _Bind(self, bind):
        newId = self.rewrite(bind.id)
        self.rewrite_children(bind)
        return Bind(newId, bind.parameters[0])


def print_source(ast, step=4, indentation=0, prefix=''):
    lead = prefix + ' '*indentation

    if isinstance(ast, Procedure):
        name = ast.variables[0]
        args = strlist(ast.variables[1:], '()', form=str)
        body = ast.parameters
        print "%sdef %s%s:" % (lead, name, args)
        print_source(body, step, indentation+step, prefix)
    elif isinstance(ast, list):
        for s in ast:
            print_source(s, step, indentation, prefix)
    else:
        print "%s%s" % (lead, ast)

def free_variables(e, env={}):
    'Generates all freely occurring identifiers in E not bound in ENV.'
    from pltools import Environment
    return FreeVariables(Environment(env)).visit(e)

def toplevel_procedures(ast):
    'Generate names of all top-level procedures in the given code block.'
    from itertools import ifilter
    if isinstance(ast, list):
        for p in ifilter(lambda x: isinstance(x,Procedure), ast):
            yield p.name().id
    elif isinstance(ast, Procedure):
        yield ast.name().id

def substituted_expression(e, env):
    """
    Return an expression with all freely occurring identifiers in E
    replaced by their corresponding value in ENV.
    """
    from pltools import Environment
    subst = Environment(env)
    rewriter = VariableSubstitute(subst)
    return rewriter.rewrite(e)

def mark_user(name):
    if isinstance(name, Tuple):
        return Tuple(*map(mark_user, name))
    else:
        return Name('_' + name.id)
    

########NEW FILE########
__FILENAME__ = coretypes
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""Type system for Copperhead.

This module defines the core type system intended for use in Copperhead
and related projects.  It is designed to be suitable for type inference
using the Hindley-Milner algorithm.

The type system is described by the following grammar:

    Type = Monotype | Polytype | Typevar

    Monotype = Con(Type1, ..., TypeN)  for all type constructors <Con>
    Polytype = [a1, ..., an] Type      for all type variables <ai>
    Typevar  = name                    for all strings <name>
"""

from pltools import strlist, name_supply

class Type:
    pass

        
class Monotype(Type):
    def __init__(self, name, *parameters):
        self.name = name
        self.parameters = parameters

    def __repr__(self):
        if not self.parameters:
            return self.name
        else:
            args = strlist(self.parameters, bracket='()', form=repr)
            return "%s%s" % (self.name, args)

    def __str__(self):
        if not self.parameters:
            return self.name
        else:
            args = strlist(self.parameters, bracket='()', form=str)
            return "%s%s" % (self.name, args)

    def __eq__(self, other):
        if not isinstance(other, Monotype):
            return False
        if self.name != other.name:
            return False
        if self.parameters != other.parameters:
            return False
        return True
    def __ne__(self, other):
        return not self.__eq__(other)
    def __hash__(self):
        return id(self)
    
class Polytype(Type):
    def __init__(self, variables, monotype):
        self.variables = variables
        self.parameters = (monotype,)

    def __repr__(self):
        return "Polytype(%r, %r)" % (self.variables, self.monotype())

    def __str__(self):
        vars = strlist(self.variables, form=str)
        return "ForAll %s: %s" % (vars, self.monotype())

    def monotype(self): return self.parameters[0]

    def __eq__(self, other):
        if not isinstance(other, Polytype):
            return False
        if self.variables != other.variables:
            return False
        return self.parameters == other.parameters
    def __ne__(self, other):
        return not self.__eq__(other)
    def __hash__(self):
        return id(self)
  
Int    = Monotype("Int")
Long   = Monotype("Long")
Float  = Monotype("Float")
Double = Monotype("Double")
Number = Monotype("Number")
Bool   = Monotype("Bool")
Void   = Monotype("Void")

class Fn(Monotype):
    def __init__(self, args, result):
        if not args:
            args = Void
        elif isinstance(args, list) or isinstance(args, tuple):
            args = Tuple(*args)
        elif not isinstance(args, Tuple):
            args = Tuple(args)

        Monotype.__init__(self, "Fn", args, result)

    def __str__(self):
        arg_type, result_type = self.parameters
        return str(arg_type) + " -> " + str(result_type)

    def input_types(self):
        arg = self.parameters[0]
        if isinstance(arg, Tuple):
            return arg.parameters
        else:
            return []

    def result_type(self):
        return self.parameters[1]
    
class Seq(Monotype):
    def __init__(self, eltype):  Monotype.__init__(self, "Seq", eltype)
    def __str__(self):  return "[" + str(self.parameters[0]) + "]"
    def unbox(self): return self.parameters[0]

class Tuple(Monotype):
    def __init__(self, *types):  Monotype.__init__(self, "Tuple", *types)
    def __str__(self):
        if len(self.parameters) > 1:
            return strlist(self.parameters, "()", form=str)
        else:
            if not(self.parameters):
                return '()'
            else:
                return str(self.parameters[0])

    def __iter__(self):
        return iter(self.parameters)
class Array(Monotype):
    def __init__(self, idxtype, eltype):
        Monotype.__init__(self, "Array", idxtype, eltype)


class Typevar(Type, str): pass

from itertools import ifilter, chain
import copy

def quantifiers(t):
    'Produce list of immediately bound quantifiers in given type.'
    return t.variables if isinstance(t, Polytype) else []


def names_in_type(t):
    'Yields the sequence of names occurring in the given type t'
    if isinstance(t, Typevar) or isinstance(t, str):
        yield t
    else:
        for n in chain(*[names_in_type(s) for s in t.parameters]):
            yield n

def free_in_type(t):
    'Yields the sequence of names occurring free in the given type t'
    if isinstance(t, Typevar) or isinstance(t, str):
        yield t
    else:
        bound = quantifiers(t)
        for n in chain(*[free_in_type(s) for s in t.parameters]):
            if n not in bound:
                yield n

def substituted_type(t, subst):
    """
    Return copy of T with all variables mapped to their values in SUBST,
    if any.  All names in SUBST must be unbound in T.
    """
    if isinstance(t, Typevar) or isinstance(t, str):
        return subst[t] if t in subst else t
    else:
        if isinstance(t, Polytype):
            for v in t.variables:
                assert v not in subst
        u = copy.copy(t)
        u.parameters = [substituted_type(p, subst) for p in t.parameters]
        return u

def occurs(id, t):
    'Returns true if the given identifier occurs as a name in type t'
    return id in names_in_type(t)

def quantify_type(t, bound=None, quantified=None):
    """
    If t is a type containing free type variables not occuring in bound,
    then this function will return a Polytype quantified over those
    variables.  Otherwise, it returns t itself.

    If an optional quantified dictionary is provided, that dictionary
    will be used to map free variables to quantifiers.  Any free
    variables not found in that dictionary will be mapped to fresh
    quantifiers, and the dictionary will be augmented with these new
    mappings.
    """

    if bound is None:
        free = list(free_in_type(t))
    else:
        free = list(ifilter(lambda t: t not in bound, free_in_type(t)))

    if not free:
        return t
    else:
        supply = name_supply()
        if quantified is None: quantified = dict()

        for v in free:
            if v not in quantified:
                quantified[v] = supply.next()

        quantifiers = sorted([quantified[v] for v in set(free)])
        return Polytype(quantifiers, substituted_type(t, quantified))

########NEW FILE########
__FILENAME__ = parsetypes
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
"""
Parsing Copperhead types from strings.
"""

import coretypes as T
import pyast
import re

class _TypeConversion(pyast._astVisitor):
    "Convert Pythonified type expressions into internal form"

    def _Expression(self, tree): return self.visit(tree.body)

    def _Name(self, tree):
        id = tree.id

        if (id in T.__dict__) and isinstance(T.__dict__[id], T.Monotype):
            return T.__dict__[id]
        else:
            return tree.id

    def _BinOp(self, tree):
        if type(tree.op) != pyast.ast.RShift:
            raise SyntaxError, "illegal type operator (%s)" % tree.op
        L = self.visit(tree.left)
        R = self.visit(tree.right)
        return T.Fn(L, R)

    def _Lambda(self, tree):
        args = self.visit(tree.args.args)
        body = self.visit(tree.body)
        print "BODY=", repr(body)
        return T.Polytype(args, body)

    def _Call(self, tree):
        conx = self.visit(tree.func)
        args = self.visit(tree.args)

        if (id in T.__dict__) and isinstance(T.__dict__[id], T.Monotype):
            return T.__dict__[id](*args)
        else:
            return T.Monotype(conx, *args)

    def _Tuple(self, tree):  return T.Tuple(*self.visit(tree.elts))
    def _List(self, tree):  return T.Seq(*self.visit(tree.elts))

def _pythonify_type(text):
    """
    Convert valid Copperhead type expression to valid Python expression.

    The Copperhead type language is very nearly syntactically valid
    Python.  To make parsing types relatively painless, we shamelessly
    convert type expressions into similar Python expressions, which we
    then feed into the Python parser.  Producing a syntactically valid
    Python expression involves the following conversions:

        - substitute 'lambda' for 'ForAll'
        - substitute '>>' for the '->' function operator
    """

    text = re.sub(r'ForAll(?=\s)', 'lambda', text)
    text = re.sub(r'->', '>>', text)

    return text.strip()

_convert_type = _TypeConversion()

def type_from_text(text):
    past = pyast.ast.parse(_pythonify_type(text), "<type string>", mode='eval')
    return T.quantify_type(_convert_type(past))



if __name__ == "__main__":

    def trial(text):
        t = type_from_text(text)
        print
        print text, "==", str(t)
        print "        ", repr(t)

    trial("ForAll a, b : a -> b")
    trial("Int -> Bool")
    trial("Point(Float, Float)")
    trial("(Int, Bool, Float)")
    trial("[(Int,Bool) -> Float]")

########NEW FILE########
__FILENAME__ = passes
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Top-level coordination of compiler passes.

The Copperhead compiler is organized as a collection of passes.  This
module handles the coordination of passes necessary to compile a
Copperhead source program, and also provides the facilities to define
custom compilation pipelines.

A compiler pass is any callable object that accepts two parameters:

    - a Copperhead AST

    - a Compilation object

and returns an AST suitable for passing to subsequent passes.
Compilation objects encapsulate all persistent state that needs to be
passed between passes.
"""

import __builtin__

from pltools import strlist, Environment

import typeinference

import rewrites as Front
import conversions
import binarygenerator as Binary
import coresyntax as S
import backend as Back

def ast_to_string(ast):
    return strlist(ast, sep='\n', form=str)

class Compilation(object):
    """
    Compilation objects hold persistent state accumulated in the compiler.
    """

    def __init__(self,
                 source=str(),
                 globals=dict(),
                 input_types=dict(),
                 silence=False
                 ):
        

        self.input_types = input_types
        self.entry_points = self.input_types.keys()
        self.source_text = source
        self.globals = globals
        self.type_context = typeinference.TypingContext(globals=globals)
        self.silence = silence
        
class Pipeline(object):

    def __init__(self, name, passes):
        self.name = name
        self.__name__ = name
        self.passes = passes

        self.capture = None

    def emit(self, name, ast, M):
        if self.capture:
            self.capture.send( (name, ast, M) )

    def __call__(self, ast, M):
        self.emit('BEGIN '+self.__name__, ast, M)

        for P in self.passes:
            try:
                ast = P(ast, M)
            except Exception as e:
                if isinstance(e, NotImplementedError):
                    raise e
                if not M.silence:
                    print
                    print "ERROR during compilation in", P.__name__
                    print S._indent(ast_to_string(ast))
                raise

            self.emit(P.__name__, ast, M)

        self.emit('END '+self.__name__, ast, M)
        return ast

def parse(source, mode='exec', **opts):
    'Convert string containing Copperhead code to an AST'
    from pyast import expression_from_text, statement_from_text
    if mode is 'exec':
        return statement_from_text(source)
    elif mode is 'eval':
        return expression_from_text(source)
    else:
        raise ValueError, "illegal parsing mode (%s)" % mode



def xform(fn):
    'Decorator indicating a procedure which is a compiler pass.'
    return fn

########################################################################
#
# FRONT-END PASSES
#

@xform
def gather_source(ast, M):
    'Gather source code for this function'
    return Front.gather_source(ast, M)

@xform
def mark_identifiers(ast, M):
    'Mark all user-provided identifiers'
    return Front.mark_identifiers(ast, M)

@xform
def lower_variadics(ast, M):
    'Convert variadic function calls into a lowered form'
    return Front.lower_variadics(ast)

@xform
def cast_literals(ast, M):
    'Insert typecasts for literals'
    return Front.cast_literals(ast, M)

@xform
def single_assignment_conversion(ast, M):
    'Perform single assignment conversion'
    return Front.single_assignment_conversion(ast, M=M)

@xform
def closure_conversion(ast, M):
    'Perform closure conversion'
    env = Environment(M.globals, __builtin__.__dict__)
    return Front.closure_conversion(ast, env)

@xform
def syntax_check(ast, M):
    'Ensure syntactic rules of language have been kept'
    #Ensure all functions and tuples have bounded arity
    Front.arity_check(ast)
    #Ensure all functions and conditionals end in return statements
    Front.return_check(ast)
    #Ensure builtins are not overridden
    Front.builtin_check(ast)
    return ast

@xform
def return_check(ast, M):
    'Ensure all functions and conditionals end in return statements'
    Front.return_check(ast)
    return ast

@xform
def return_check(ast, M):
    'Ensure all functions and conditionals end in return statements'
    Front.return_check(ast)
    return ast

@xform
def lambda_lift(ast, M):
    'Promote lambda functions to real procedures'
    return Front.lambda_lift(ast)

@xform
def procedure_flatten(ast, M):
    'Turn nested procedures into sets of procedures'
    return Front.procedure_flatten(ast)

@xform
def expression_flatten(ast, M):
    'Make every statement an atomic expression (no nested expressions)'
    return Front.expression_flatten(ast, M)

@xform
def protect_conditionals(ast, M):
    'Wrap branches of conditional expressions with lambdas'
    return Front.ConditionalProtector().rewrite(ast)

@xform
def name_tuples(ast, M):
    'Make sure tuple arguments to functions have proper names'
    return Front.name_tuples(ast)

@xform
def unrebind(ast, M):
    'Eliminate extraneous rebindings'
    return Front.unrebind(ast)

@xform
def inline(ast, M):
    return Front.procedure_prune(Front.inline(ast, M), M.entry_points)

@xform
def type_assignment(ast, M):
    typeinference.infer(ast, context=M.type_context, input_types=M.input_types)
    return ast



@xform
def backend_compile(ast, M):
    return Back.execute(ast, M)

@xform
def prepare_compilation(ast, M):
    return Binary.prepare_compilation(M)

@xform
def make_binary(ast, M):
    return Binary.make_binary(M)
    



frontend = Pipeline('frontend', [gather_source,
                                 mark_identifiers,
                                 closure_conversion,
                                 single_assignment_conversion,
                                 protect_conditionals,  # XXX temporary fix
                                 lambda_lift,
                                 procedure_flatten,
                                 expression_flatten,
                                 syntax_check,
                                 inline,
                                 cast_literals,
                                 name_tuples,
                                 unrebind,
                                 lower_variadics,
                                 type_assignment
                                 ])

backend = Pipeline('backend', [backend_compile])

binarize = Pipeline('binarize', [prepare_compilation,
                                 make_binary])

to_binary = Pipeline('to_binary', [frontend,
                                   backend,
                                   binarize])

def run_compilation(target, suite, M):
    """
    Internal compilation interface.

    This will run the target compilation pipeline over the given suite
    of declarations with metadata state M.
    """
    return target(suite, M)


def compile(source,
            input_types={},
            tag=None,
            globals=None,
            target=to_binary, toolchains=(), **opts):

    M = Compilation(source=source,
                    globals=globals,
                    input_types=input_types)
    if isinstance(source, str):
        source = parse(source, mode='exec')
    M.arity = len(source[0].formals())
    M.time = opts.pop('time', False)
    M.tag = tag
    M.verbose = opts.pop('verbose', False)
    M.code_dir = opts['code_dir']
    M.toolchains = toolchains
    M.compile = opts.pop('compile', True)
    M.silence = not M.compile
    return run_compilation(target, source, M)



########NEW FILE########
__FILENAME__ = pltools
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

# Tools for programming language implementation

import string, itertools

def strlist(items, bracket=None, sep=', ', form=repr):
    'Convert a list to strings and join with optional separator and brackets'
    body = sep.join(map(form, items))
    if bracket:
        open,close = bracket
        return open+body+close
    else:
        return body


class Environment:
    "Associative map with chained maps for fallback"

    def __init__(self, *chained):
        self.maps = [dict()] + list(chained)

    def lookup(self, key):
        for M in self.maps:
            if key in M: return M[key]

        raise KeyError, "no value defined for %s" % key

    def has_key(self, key):
        for M in self.maps:
            if key in M: return True
        return False

    def __len__(self):  return sum([M.__len__() for M in self.maps])

    def __getitem__(self, key):  return self.lookup(key)
    def __setitem__(self, key, value):  self.maps[0][key] = value
    def __contains__(self, key): return self.has_key(key)

    def __iter__(self):
        return itertools.chain(*[M.__iter__() for M in self.maps])
    def __repr__(self):
        return 'Environment(' + repr(self.maps) + ')'

    def iterkeys(self):
        return self.__iter__()

    def begin_scope(self):  self.maps = [dict()] + self.maps
    def end_scope(self):  self.maps.pop(0)
    def update(self, E, **F): self.maps[0].update(E, **F)

def resolve(name, env):
    """
    Resolve the value assigned to NAME by ENV, possibly via chained bindings
    """
    t = name
    while t in env:
        t = env[t]
    return t

def resolution_map(names, env):
    """
    Return a dictionary that maps each NAME to its resolution in ENV.
    """
    return dict(zip(names, [resolve(n, env) for n in names]))

def name_supply(stems=string.ascii_lowercase, drop_zero=True):
    """
    Produce an infinite stream of unique names from stems.
    Defaults to a, b, ..., z, a1, ..., z1, a2, ..., z2, ...
    """
    k = 0
    while 1:
        for a in stems:
            yield a+str(k) if (k or not drop_zero) else a
        k = k+1

def name_list(length, **kwargs):
    """
    Produce a list of unique names of the given length.
    """
    return list(itertools.islice(name_supply(**kwargs), length))

########NEW FILE########
__FILENAME__ = pyast
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

# Converting Python's native AST to internal Copperhead form


# There are several internal Python AST representations.  This is the
# most recent and the simplest.  It is only supported in Python 2.5 and
# later.

try:
    # Try the Python 2.6 interface
    import ast
except ImportError:
    # Fall back on the Python 2.5 interface, faking the 2.6 interface
    # where possible
    import _ast as ast
    ast.parse = lambda expr, filename='<unknown>', mode='exec': \
                    compile(expr, filename, mode, ast.PyCF_ONLY_AST)


from visitor import Visitor
from coresyntax import *


# Map from Python operator AST classes to function names
op_table = {
        # Binary operators
        ast.Add : 'op_add',
        ast.Sub : 'op_sub',
        ast.Mult : 'op_mul',
        ast.Div  : 'op_div',
        ast.Mod  : 'op_mod',
        ast.Pow  : 'op_pow',
        ast.LShift : 'op_lshift',
        ast.RShift : 'op_rshift',
        ast.BitOr  : 'op_or',
        ast.BitXor : 'op_xor',
        ast.BitAnd : 'op_and',

        # Boolean operators
        ast.Eq    : 'cmp_eq',
        ast.NotEq : 'cmp_ne',
        ast.Lt    : 'cmp_lt',
        ast.LtE   : 'cmp_le',
        ast.Gt    : 'cmp_gt',
        ast.GtE   : 'cmp_ge',

        # Unary operators
        ast.Invert : 'op_invert',
        ast.Not    : 'op_not',
        ast.UAdd   : 'op_pos',
        ast.USub   : 'op_neg',
}




class _astVisitor(Visitor):
    def __init__(self):  super(_astVisitor,self).__init__()

    def name_list(self, names):  return [name.id for name in names]

    def extract_arguments(self, args):  return self.name_list(args.args)

class Printer(_astVisitor):

    def __init__(self):
        super(Printer,self).__init__()

    def _Module(self, tree):
        print "BEGIN module"
        self.visit(tree.body)

    def _FunctionDef(self, tree):
        argnames = self.extract_arguments(tree.args)
        print "def %s(%s):" % (tree.name, argnames)
        self.visit(tree.body)

    def _Name(self, tree):
        print tree.id

    def _Call(self, tree):
        name = tree.func
        args = tree.args
        print "%s(%s)" % (name.id, self.visit(args))

    def _Lambda(self, tree):
        argnames = self.extract_arguments(tree.args)
        print "lambda %s: ", argnames
        self.visit(tree.body)
        
    def _Return(self, tree):
        print "return "
        if tree.value:
            self.visit(tree.value)

class ExprConversion(_astVisitor):
    "Convert Python's ast expression trees to Copperhead's AST"

    def __init__(self):  super(ExprConversion,self).__init__()

    def _Expression(self, tree): return self.visit(tree.body)

    def _Num(self, tree):  return Number(tree.n)
    def _Name(self, tree): return Name(tree.id)

    def _BoolOp(self, tree):
        op = type(tree.op)
        # XXX Issue #3: Short-circuiting operators
        
        # Correct code
        # if op==ast.And:
        #     return And(*self.visit(tree.values))
        # elif op==ast.Or:
        #     return Or(*self.visit(tree.values))
        # else:
        #     self.unknown_node(tree)
        if op==ast.And:
            fn = Name('op_band')
        elif op==ast.Or:
            fn = Name('op_bor')
        else:
            self.unknown_node(tree)
        children = self.visit(tree.values)
        def nest_ops(e, r):
            if len(r) == 0:
                return e
            new_e = Apply(fn, [r.pop(), e])
            return nest_ops(new_e, r)
        nested_ops = nest_ops(Apply(fn, [children.pop(-2), children.pop()]),
                              children)
        return nested_ops

    def _BinOp(self, tree):
        L = self.visit(tree.left)
        R = self.visit(tree.right)
        op = Name(op_table[type(tree.op)])
        return Apply(op, [L, R])

    def _UnaryOp(self, tree):
        L = self.visit(tree.operand)
        op = Name(op_table[type(tree.op)])
        return Apply(op, [L])

    def _Compare(self, tree):
        if tree.ops[1:]:
            raise SyntaxError, "can't accept multiple comparisons"
        else:
            L = self.visit(tree.left)
            R = self.visit(tree.comparators[0])
            op = Name(op_table[type(tree.ops[0])])
            return Apply(op, [L, R])

    def _Call(self, tree):
        fn = self.visit(tree.func)
        args = self.visit(tree.args)
        if type(fn)==Name and fn.id=='map':
            return Map(args)
        else:
            return Apply(fn, args)

    def _Lambda(self, tree):
        args = self.visit(tree.args.args)
        body = self.visit(tree.body)
        return Lambda(args, body)

    def _IfExp(self, tree):
        test = self.visit(tree.test)
        body = self.visit(tree.body)
        alt  = self.visit(tree.orelse)
        return If(test, body, alt)

    def _Tuple(self, tree):
        return Tuple(*self.visit(tree.elts))

    def _Subscript(self, tree):
        value = self.visit(tree.value)
        slice = self.visit(tree.slice)
        return Subscript(value, slice)

    def _Index(self, tree):
        #Instead of previous:
        #return Index(self.visit(tree.value))
        
        #We map Index types to Number or Name types here
        return self.visit(tree.value)
    def _Slice(self, tree):
        raise SyntaxError, "array slicing is not yet supported"

    def _ListComp(self, tree):
        E      = self.visit(tree.elt)
        target = tree.generators[0].target
        iter   = tree.generators[0].iter
        ifs    = tree.generators[0].ifs

        if len(tree.generators) > 1:
            raise SyntaxError, \
                  "can't have multiple generators in comprehensions"
        if len(ifs)>0:
            raise SyntaxError, \
                    "predicated comprehensions are not supported"

        target = self.visit(target)
        iter = self.visit(iter)

        if isinstance(target, Name):
            return Map([Lambda([target], E), iter])
        elif isinstance(target, Tuple):
            def is_zip(t):
                return isinstance(t, Apply) and t.function().id == "zip"

            if not is_zip(iter):
                raise SyntaxError, \
                        "multivariable comprehensions work only with zip()"

            return Map([Lambda(list(target.parameters), E)] + list(iter.arguments()))

        else:
            raise SyntaxError, \
                    "unsupported list comprehension form"



convert_expression = ExprConversion()

def expression_from_text(text, source="<string>"):
    past = ast.parse(text, source, mode='eval')
    return convert_expression(past)



class StmtConversion(_astVisitor):
    "Convert Python's _ast statement trees to Copperhead's AST"

    def __init__(self):  super(StmtConversion,self).__init__()

    def _Module(self, tree):  return self.visit(tree.body)

    def _Return(self, tree):
        return Return(convert_expression(tree.value))

    def _Assign(self, tree):
        if len(tree.targets)>1:
            raise SyntaxError, 'multiple assignments not supported'

        id = convert_expression(tree.targets[0])
        value = convert_expression(tree.value)
        return Bind(id, value)

    def _FunctionDef(self, tree):
        id = tree.name
        args = convert_expression(tree.args.args)

        if tree.args.vararg:
            raise SyntaxError, 'varargs not allowed in function definitions'
        if tree.args.kwarg:
            raise SyntaxError, 'kwargs not allowed in function definitions'
        if tree.args.defaults:
            raise SyntaxError, 'argument defaults not allowed in function definitions'

        #Remove Docstring before converting to Copperhead
        if tree.body[0].__class__.__name__ == 'Expr':
            if tree.body[0].value.__class__.__name__ == 'Str':
                body = tree.body[1:]
            else:
                body = tree.body
        else:
            body = tree.body
            
        body = self.visit(body)

        return Procedure(Name(id), args, body)

    def _If(self, tree):
        test   = convert_expression(tree.test)
        body   = self.visit(tree.body)
        orelse = self.visit(tree.orelse)
        #Python will check to make sure the test and body are not empty
        #But Python allows empty else branches. Copperhead does not.
        if not orelse:
            raise SyntaxError, 'if statements must include an else branch'
        return Cond(test, body, orelse)

convert_statement = StmtConversion()

def statement_from_text(text, source="<string>"):
    past = ast.parse(text, source, mode='exec')
    return convert_statement(past)


########NEW FILE########
__FILENAME__ = rewrites
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""Basic syntactic rewrites for Copperhead compiler.

This module implements the rewrite passes used by the Copperhead
compiler to transform the input program into a more easily analyzed
form.  The routines in this module assume that the syntax trees they are
given are well-formed, but they do not generally make any assumptions
about type soundness.

The rewrites provided by this module are fairly standard and operate on
the source program without consideration for any parallelism.

Supported rewrites include:

    o Closure conversion

    o Lambda lifting

    o Single assignment conversion
"""

import coresyntax as S
import pltools
from utility import flatten
import copy
import coretypes as T
import itertools
import inspect

class SourceGatherer(S.SyntaxRewrite):
    def __init__(self, globals):
        self.globals = globals
        import copperhead.prelude_impl as PI
        self.prelude_impl = set(dir(PI))
        self.PI = PI
        self.env = pltools.Environment()
        self.clean = []
    def gather(self, suite):
        self.sources = []
        self.gathered = set()
        for stmt in suite:
            self.clean.append(self.rewrite(stmt))
        while self.sources:
            stmt = self.sources.pop(0)
            self.clean.insert(0, self.rewrite(stmt))
        return list(flatten(self.clean))
    def _Procedure(self, proc):
        proc_id = proc.name().id
        self.env[proc_id] = proc_id
        self.env.begin_scope()
        for param in flatten(proc.formals()):
            id = param.id
            self.env[id] = id
        self.rewrite_children(proc)
        self.env.end_scope()
        return proc
    def _Bind(self, bind):
        destination = bind.binder()
        if isinstance(destination, S.Tuple):
            for dest in flatten(destination):
                self.env[dest.id] = dest.id
        else:
            id = destination.id
            self.env[id] = id
        self.rewrite_children(bind)
        return bind
    def _Name(self, name):
        if not name.id in self.env:
            if name.id in self.globals:
                fn = self.globals[name.id]
                #Is this a prelude function implemented in Copperhead?
                if (fn.__name__ in self.prelude_impl):
                    #If it's a function or a builtin, override
                    #If it's not either, then the user has redefined
                    # a prelude function and we'll respect their wishes
                    if inspect.isbuiltin(fn) or \
                            inspect.isfunction(fn):
                        fn = getattr(self.PI, fn.__name__)
                if hasattr(fn, 'syntax_tree') and \
                    fn.__name__ not in self.gathered:
                    self.sources.append(fn.syntax_tree)
                    self.gathered.add(fn.__name__)
        return name

def gather_source(stmt, M):
    gatherer = SourceGatherer(M.globals)
    gathered = gatherer.gather(stmt)
    return gathered

class IdentifierMarker(S.SyntaxRewrite):
    def __init__(self, globals):
        self.globals = globals
        self.locals = pltools.Environment()
        import copperhead.prelude_impl as PI
        self.prelude_impl = set(dir(PI))
        self.PI = PI
        self.bools = ["True", "False"]
    def _Name(self, name):
        if name.id in self.bools:
            return name
        if name.id in self.globals and name.id not in self.locals:
            if hasattr(self.globals[name.id], 'syntax_tree') \
                    or name.id in self.prelude_impl:
                #A user wrote this identifier or it's a non-primitive
                #part of the prelude - mark it
                return S.mark_user(name)
            else:
                return name
        else:
            return S.mark_user(name)
    def _Procedure(self, proc):
        self.locals.begin_scope()
        for x in proc.formals():
            #Tuples may be arguments to procedures
            #Mark all ids found in each formal argument
            for y in flatten(x):
                self.locals[y.id] = True
        self.rewrite_children(proc)
        self.locals.end_scope()
        proc.variables = map(S.mark_user, proc.variables)
        return proc
    def _Lambda(self, lamb):
        return self._Procedure(lamb)
    def _Bind(self, bind):
        self.rewrite_children(bind)
        bind.id = self.rewrite(bind.id)
        return bind
   
def mark_identifiers(stmt, M):
    marker = IdentifierMarker(M.globals)
    marked = marker.rewrite(stmt)
    #Rather than make core syntax deal sordidly with strings
    #Wrap them up here.
    def mark_user(x):
        return S.mark_user(S.Name(x)).id
    M.entry_points = map(mark_user, M.entry_points)
    for x in M.input_types.keys():
        M.input_types[mark_user(x)] = M.input_types[x]
        del M.input_types[x]
    return marked


class VariadicLowerer(S.SyntaxRewrite):
    def __init__(self):
        self.applies = set(['zip'])
        # XXX Do this for unzip as well
        self.binders = set(['unzip'])
        self.arity = -1
    def _Bind(self, bind):
        if isinstance(bind.binder(), S.Tuple):
            self.arity = bind.binder().arity()
        self.rewrite_children(bind)
        return bind
    def _Map(self, ast):
        args = ast.parameters
        arity = len(args) - 1
        assert(arity > 0)
        return S.Apply(S.Name('map' + str(arity)),
                       args)
    def _Apply(self, ast):
        fn_id = ast.function().id
        arity = -1
        if fn_id in self.applies:
            args = ast.arguments()
            arity = len(args)
        elif fn_id in self.binders:
            arity = self.arity
            assert(arity > 0)
            
        if arity > 0:
            return S.Apply(S.Name(fn_id + str(arity)), ast.arguments())
        else:
            return ast
                        

def lower_variadics(stmt):
    rewriter = VariadicLowerer()
    lowered = rewriter.rewrite(stmt)
    return lowered

class SingleAssignmentRewrite(S.SyntaxRewrite):
    def __init__(self, env, exceptions, state):
        self.env = pltools.Environment(env)
        self.exceptions = exceptions
        if state:
            self.serial = state
        else:
            self.serial = itertools.count(1)

    def _Return(self, stmt):
        result = S.Return(S.substituted_expression(stmt.value(), self.env))
        return result
    def _Cond(self, cond):
        condition = S.substituted_expression(cond.parameters[0], self.env)
        self.env.begin_scope()
        body = self.rewrite(cond.body())
        self.env.end_scope()
        self.env.begin_scope()
        orelse = self.rewrite(cond.orelse())
        self.env.end_scope()
        return S.Cond(condition, body, orelse)
    def _Bind(self, stmt):
        var = stmt.binder()
        varNames = [x.id for x in flatten(var)]
        operation = S.substituted_expression(stmt.value(), self.env)
        for name in varNames:
            if name not in self.exceptions:
                rename = '%s_%s' % (name, self.serial.next())
            else:
                rename = name
           
            self.env[name] = S.Name(rename)
        result = S.Bind(S.substituted_expression(var, self.env), operation)
        return result

    def _Procedure(self, stmt):
        self.env.begin_scope()
        for var in flatten(stmt.variables):
            self.env[var.id] = var

        result = self.rewrite_children(stmt)
        self.env.end_scope()

        return result


def single_assignment_conversion(stmt, env={}, exceptions=set(), M=None):
    'Rename locally declared variables so that each is bound exactly once'
    state = None
    if M:
        state = getattr(M, 'single_conv_state', None)
    rewrite = SingleAssignmentRewrite(env, exceptions, state)
    rewritten = rewrite.rewrite(stmt)
    if M:
        M.single_conv_state = rewrite.serial
    return rewritten

class LambdaLifter(S.SyntaxRewrite):
    """
    Convert every expression of the form:
    
        lambda x1,...,xn: E 

    into a reference to a proceduce __lambdaN and add

        def __lambdaN(x1,...,xn): return E

    to the procedure list.

    This rewriter assumes that closure conversion has already been
    performed.  In other words, there are no freely occurring
    local variables in the body of the lambda expression.
    """

    def __init__(self):
        # Collect lifted Lambdas as Procedures 
        self.proclist = []
        self.names = pltools.name_supply(stems=['_lambda'], drop_zero=False)

    def _Lambda(self, e):
        fn = S.Name(self.names.next())

        self.rewrite_children(e)
        body = S.Return(e.parameters[0])
        self.proclist.append(S.Procedure(fn, e.variables, [body]))

        return fn

    def _Procedure(self, ast):
        # We explicitly interleave lifted lambda procedures with the
        # statements from which they come.  This guarantees correct
        # ordering of existing nested procedures with new
        # lambda-generated procedures.
        body = []
        for stmt in ast.parameters:
            stmt = self.rewrite(stmt)
            body = body + self.proclist + [stmt]
            self.proclist = []
        ast.parameters = body
        return ast

def lambda_lift(e):
    lift = LambdaLifter()
    eL = lift.rewrite(e)
    return lift.proclist + eL



class ProcedureFlattener(S.SyntaxRewrite):
    """
    Flatten the list of defined procedures so that no definition is
    nested within another procedure.  This should only be applied after
    closure conversion and lambda lifting are complete.
    """

    def __init__(self):
        self.toplevel = list()

    def _Procedure(self, e):
        self.rewrite_children(e)
        e.parameters = filter(lambda x: x is not None, e.parameters)
        self.toplevel.append(e)
        return None

    # XXX If things other than procedures become allowed as top-level
    #     forms, make sure that they are handled here.

def procedure_flatten(e):
    flattener = ProcedureFlattener()
    eF = flattener.rewrite(e)
    return flattener.toplevel

class _ClosureRecursion(S.SyntaxRewrite):
    # XXX Most of the code in this rewriter simply serves to track
    #     variables defined in the current scope.  That should be
    #     abstracted into a more generic base class that could be used
    #     elsewhere.
    def __init__(self, env):
        self.env = env

    def locally_bound(self, B):
        for v in flatten(B):
            self.env[v.id] = v.id

    def _Bind(self, ast):
        self.rewrite_children(ast)
        binders = [v for v in S.walk(ast.binder()) if isinstance(v, S.Name)]
        self.locally_bound(binders)
        return ast

    def _Lambda(self, ast):
        self.env.begin_scope()
        self.locally_bound(ast.formals())
        self.rewrite_children(ast)
        self.env.end_scope()
        return ast

    def _Procedure(self, ast):
        self.env.begin_scope()
        self.locally_bound(ast.variables)
        self.rewrite_children(ast)
        self.env.end_scope()
        return ast

    def _Apply(self, ast):
        #This catches the case where a procedure that is being
        #converted to a closure is recursive. In this case,
        #we don't make a new closure, we simply call the one
        #we've already got
        if not isinstance(ast.function(), S.Name):
            import pdb
            pdb.set_trace()
        proc_name = ast.function().id
        if proc_name in self.env and isinstance(self.env[proc_name], list):
            return S.Apply(ast.function(),
                           ast.arguments() + self.env[proc_name])
        return self.rewrite_children(ast)
    
    # XXX This rewrite rule -- coupled with the rule for _Procedure in
    #     _ClosureConverter -- is an ugly hack for rewriting calls to
    #     procedures.  We should find a more elegant solution!
    def _Name(self, ast):
        x = getattr(self.env, ast.id, None)
        if ast.id in self.env and isinstance(self.env[ast.id], S.Closure):
            return S.Closure(self.env[ast.id].variables, ast)
        else:
            return ast


class _ClosureConverter(_ClosureRecursion):

    def __init__(self, globals=None):
        self.globals = globals or dict()
        self.env = pltools.Environment()
        # self.proc_name = []
        
    def _Lambda(self, e):
        
        _ClosureRecursion._Lambda(self, e)
        
        formals = [v.id for v in flatten(e.formals())]
        # Take the free variable list, stick it in a set to make sure we don't
        # duplicate a variable, and then put it back in a list to make sure
        # it's got a defined ordering, which sets don't have
        free = list(set([v for v in S.free_variables(e.body(), formals)
                        if v in self.env]))

        if free:
            bound = [S.Name("_K%d" % i) for i in range(len(free))]
            body = S.substituted_expression(e.body(), dict(zip(free, bound)))

            e.parameters = [body]
            e.variables = e.variables + bound

            return S.Closure([S.Name(x) for x in free], e)
        else:
            return e

    def _Procedure(self, ast):
        binders = [v.id for v in flatten(ast.variables)] # NOTE: this includes name

        _ClosureRecursion._Procedure(self, ast)

        # Take the free variable list, stick it in a set to make sure we don't
        # duplicate a variable, and then put it back in a list to make sure
        # it's got a defined ordering, which sets don't have
        free = list(set([v for v in S.free_variables(ast.body(), binders)
                        if v in self.env]))

        if free:
            bound = [S.Name("_K%d" % i) for i in range(len(free))]
            ast.variables = ast.variables + bound
            ast.parameters = S.substituted_expression(ast.parameters,
                                                      dict(zip(free, bound)))

            # Transform recursive calls of this procedure within its own body.
            recursive = _ClosureRecursion(self.env)
            self.env[ast.name().id] = bound
            ast.parameters = recursive.rewrite(ast.parameters)

            # Register rewrite for calls to this procedure in later
            # parts of the defining scope
            self.env[ast.name().id] = S.Closure([S.Name(x) for x in free],
                                                ast.name())
        # else:
#             self.locally_bound([ast.name()])

        return ast

def closure_conversion(ast, globals=None):
    """
    Detect and explicitly tag all variables in the given syntax tree
    which are lexically closed over by lambdas or nested procedure
    definitions.

    A variable occurring within a lambda/procedure is considered to form
    a closure if:

        - it is not bound as a formal parameter of the lambda/procedure

        - it is bound in the containing scope of the lambda/procedure

    Such variables are lifted into arguments to explicit "closure"
    forms, and are passed as explicit arguments to the nested
    lambda/procedure.

        e.g., lambda x: lambda y: x =>
              lambda x: closure([x], lambda y, _K0: _K0)

    Global variables (if any) defined in the globals parameter are never
    closed over, since they are  globally visible.

    The copperhead.interlude module provide a native Python
    implementation of the Copperhead closure() expression.
    """
    converter = _ClosureConverter(globals=globals)
    converted = converter.rewrite(ast)
    
    return converted


class ExpressionFlattener(S.SyntaxRewrite):
    def __init__(self):
        self.stmts = [list()]
        self.names = pltools.name_supply(stems=['e'], drop_zero=False)


    def top(self): return self.stmts[-1]
    def emit(self, ast): self.top().append(ast)
    def push(self):  self.stmts.append(list())
    def pop(self):
        x = self.top()
        self.stmts.pop()
        return x

    def _Lambda(self, ast):
        raise ValueError, "lambda's cannot be flattened (%s)" % e

    def _Name(self, ast): return ast
    def _Number(self, ast): return ast
    def _Closure(self, ast): return ast

    def _Expression(self, e):
        subexpressions = e.parameters
        e.parameters = []
        for sub in subexpressions:
            sub = self.rewrite(sub)
            # XXX It doesn't seem right to include Closure on this list
            #     of "atomic" values.  But phase_assignment breaks if I
            #     don't do this.
            if not isinstance(sub, (S.Name, S.Literal, S.Closure)):
                tn = S.Name(self.names.next())
                self.emit(S.Bind(tn, sub))
            else:
                tn = sub
            e.parameters.append(tn)
        return e

    def _Bind(self, stmt):
        e = self.rewrite(stmt.value())
        stmt.parameters = [e]
        self.emit(stmt)
        return stmt

    def _Return(self, stmt):
        e = self.rewrite(stmt.value())
        if isinstance(e, S.Name):
            stmt.parameters = [e]
            self.emit(stmt)
            return
        # If we're returning a tuple, we always copy the value into a return
        # variable.  We may undo this later on, for entry-point procedures.
        ret = S.Name("result")
        self.emit(S.Bind(ret, e))
        stmt.parameters = [ret]
        self.emit(stmt)

    def _Cond(self, stmt):
        test = self.rewrite(stmt.test())

        self.push()
        self.rewrite(stmt.body())
        body = self.pop()

        self.push()
        self.rewrite(stmt.orelse())
        orelse = self.pop()

        stmt.parameters = [test, body, orelse]
        self.emit(stmt)

    def _Procedure(self, stmt):
        self.push()
        self.formals = set((x.id for x in flatten(stmt.formals())))
        self.rewrite_children(stmt)
        self.formals = None
        body = self.pop()
        stmt.parameters = body
        self.emit(stmt)

    def _default(self, ast):
        if isinstance(ast, S.Expression):
            return self._Expression(ast)
        else:
            raise ValueError, "can't flatten syntax (%s)" % ast

def expression_flatten(s, M):
    #Expression flattening may be called multiple times
    #Keep around the flattener name supply
    flattener = ExpressionFlattener()

    if hasattr(M, 'flattener_names'):
        flattener.names = M.flattener_names
    else:
        flattener = ExpressionFlattener()
        M.flattener_names = flattener.names
    flattener.rewrite(s)
    return flattener.top()

class LiteralCaster(S.SyntaxRewrite):
    def __init__(self, globals):
        self.globals = globals
    def _Procedure(self, proc):
        self.literal_names = set()
        self.rewrite_children(proc)
        return proc
    def _Bind(self, bind):
        if isinstance(bind.value(), S.Number):
            self.literal_names.add(bind.binder().id)
        self.rewrite_children(bind)
        return bind
    def _Apply(self, appl):
        #Rewrite children
        self.rewrite_children(appl)
        #Insert typecasts for arguments
        #First, retrieve type of function, if we can't find it, pass
        #If function is a closure, pass
        fn = appl.function()
        if isinstance(fn, S.Closure):
            return appl
        fn_obj = self.globals.get(fn.id, None)
        if not fn_obj:
            return appl
        #If the function doesn't have a recorded Copperhead type, pass
        if not hasattr(fn_obj, 'cu_type'):
            return appl
        fn_type = fn_obj.cu_type
        if isinstance(fn_type, T.Polytype):
            fn_input_types = fn_type.monotype().input_types()
        else:
            fn_input_types = fn_type.input_types()
        def build_cast(cast_name, args):
            "Helper function to build cast expressions"
            return S.Apply(S.Name(cast_name),
                           args)
        def insert_cast(arg_type, arg):
            "Returns either the argument or a casted argument"
            if hasattr(arg, 'literal_expr'):
                if arg_type is T.Int:
                    return build_cast("int32", [arg])
                elif arg_type is T.Long:
                    return build_cast("int64", [arg])
                elif arg_type is T.Float:
                    return build_cast("float32", [arg])
                elif arg_type is T.Double:
                    return build_cast("float64", [arg])
                elif isinstance(arg_type, str):
                    #We have a polymorphic function
                    #We must insert a polymorphic cast
                    #This means we search through the inputs
                    #To find an input with a related type
                    for in_type, in_arg in \
                        zip(fn_input_types, appl.arguments()):
                        if not hasattr(in_arg, 'literal_expr'):
                            if in_type == arg_type:
                                return build_cast("cast_to", [arg, in_arg])
                            elif isinstance(in_type, T.Seq) and \
                                in_type.unbox() == arg_type:
                                return build_cast("cast_to_el", [arg, in_arg])
            #No cast was found, just return the argument
            return arg
        casted_arguments = map(insert_cast, fn_input_types, appl.arguments())
        appl.parameters[1:] = casted_arguments
        #Record if this expression is a literal expression
        if all(map(lambda x: hasattr(x, 'literal_expr'), appl.arguments())):
            appl.literal_expr = True
        return appl
    def _Number(self, ast):
        ast.literal_expr = True
        return ast
    def _Name(self, ast):
        if ast.id in self.literal_names:
            ast.literal_expr = True
        return ast
    
def cast_literals(s, M):
    caster = LiteralCaster(M.globals)
    casted = caster.rewrite(s)
    #Inserting casts may nest expressions
    return expression_flatten(casted, M)

class TupleNamer(S.SyntaxRewrite):
    def _Procedure(self, proc):
        names = pltools.name_supply(stems=['tuple'], drop_zero=False)
        disassembly = []
        def make_name(arg):
            if not isinstance(arg, S.Tuple):
                return arg
            else:
                made_name = S.Name(names.next())
                assembled = S.Bind(S.Tuple(*[make_name(x) for x in arg]),
                                   made_name)
                disassembly.insert(0, assembled)
                return made_name
        new_variables = map(make_name, proc.formals())
        return S.Procedure(proc.name(), new_variables, disassembly + proc.parameters)

def name_tuples(s):
    namer = TupleNamer()
    named = namer.rewrite(s)
    return named
    
class ReturnFinder(S.SyntaxVisitor):
    def __init__(self):
        #XXX HACK. Need to perform conditional statement->expression flattening
        #In order to inline properly. This dodges the issue.
        self.in_conditional = False
        self.return_in_conditional = False
    def _Cond(self, cond):
        self.in_conditional = True
        self.visit_children(cond)
        self.in_conditional = False
    def _Return(self, node):
        if self.in_conditional:
            self.return_in_conditional = True
            return
        self.return_value = node.value()
                                       
class FunctionInliner(S.SyntaxRewrite):
    def __init__(self, M):
        self.activeBinding = None
        self.statements = []
        self.procedures = {}
        self.M = M
    def _Bind(self, binding):
        self.activeBinding = binding.binder()
        self.rewrite_children(binding)
        self.activeBinding = None
        statements = self.statements
        self.statements = []
        if statements == []:
            return binding
        return statements
    def _Apply(self, appl):
        fn = appl.function()
        if isinstance(fn, S.Closure):
            fn_name = fn.body().id
        else:
            fn_name = fn.id
        if fn_name in self.procedures:
            instantiatedFunction = self.procedures[fn_name]
            functionArguments = instantiatedFunction.variables[1:]
            instantiatedArguments = appl.parameters[1:]
            if isinstance(fn, S.Closure):
                instantiatedArguments.extend(fn.variables)
            env = pltools.Environment()
            for (internal, external) in zip(functionArguments, instantiatedArguments):
                env[internal.id] = external
            return_finder = ReturnFinder()
            return_finder.visit(instantiatedFunction)
            #XXX HACK. Need to do conditional statement->expression conversion
            # In order to make inlining possible
            if return_finder.return_in_conditional:
                return appl
            env[return_finder.return_value.id] = self.activeBinding
            statements = filter(lambda x: not isinstance(x, S.Return),
                                instantiatedFunction.body())
            statements = [S.substituted_expression(x, env) for x in \
                              statements]
            singleAssignmentInstantiation = single_assignment_conversion(statements, exceptions=set((x.id for x in flatten(self.activeBinding))), M=self.M)
            self.statements = singleAssignmentInstantiation
            return None
        return appl
    def _Cond(self, cond):
        body = list(flatten(self.rewrite(cond.body())))
        orelse = list(flatten(self.rewrite(cond.orelse())))
        return S.Cond(cond.test(), body, orelse)
    
    def _Procedure(self, proc):
        self.rewrite_children(proc)
        proc.parameters = list(flatten(proc.parameters))
        
        procedureName = proc.variables[0].id
        self.procedures[procedureName] = proc
        return proc

class LiteralOpener(S.SyntaxRewrite):
    """
    It is possible that inlining has produced closures over literals.
    These closures can be pruned down by propagating literal values,
    and in some cases the closures can be eliminated completely.

    This pass performs this transformation to ensure that we never
    close over literals.  Removing this pass will cause assertion
    failures in the backend, which assumes closures are performed
    only over names."""
    def __init__(self):
        self.procedures = {}
        self.name_supply = pltools.name_supply(stems=['_'], drop_zero=False)
    def _Procedure(self, proc):
        self.propagated = []
        self.rewrite_children(proc)
        self.procedures[proc.name().id] = proc
        if self.propagated:
            return self.propagated + [proc]
        else:
            return proc
    def _Closure(self, c):
        closed_over_literal = any(map(lambda x: not isinstance(x, S.Name),
                                      c.closed_over()))
        if not closed_over_literal:
            return c
        #Find procedure being closed over
        proc_name = c.body().id
        proc = self.procedures[proc_name]
        proc_args = proc.formals()
        closed_args = c.closed_over()
        #Construct new set of arguments, with literals closed over removed
        replaced_args = proc_args[:-len(closed_args)]
        replaced_closed_over = []
        #Also record what replacements to make
        replacement = {}
        for orig_arg, closed_arg in zip(proc_args[-len(closed_args):],
                                        closed_args):
            if isinstance(closed_arg, S.Name):
                replaced_args.append(orig_arg)
                replaced_closed_over.append(closed_arg)
            else:
                replacement[orig_arg.id] = closed_arg
        #If we are only closing over literals, we will return a name
        #rather than a reduced closure. Check.
        fully_opened = len(replacement) == len(closed_args)
        replaced_stmts = [
            S.substituted_expression(si, replacement) \
                for si in proc.body()]
        replaced_name = S.Name(proc_name + self.name_supply.next())
        self.propagated.append(
            S.Procedure(
                replaced_name,
                replaced_args,
                replaced_stmts))
        if fully_opened:
            return replaced_name
        else:
            return S.Closure(replaced_closed_over,
                             replaced_name)

def procedure_prune(ast, entries):
    needed = set(entries)

    # First, figure out which procedures we actually need by determining
    # the free variables in each of the entry points
    for p in ast:
        needed.update(S.free_variables(p.body()))

    # Now, only keep top-level procedures that have been referenced
    return [p for p in ast if p.name().id in needed]

        
def inline(s, M):
    inliner = FunctionInliner(M)
    inlined = list(flatten(inliner.rewrite(s)))
    literal_opener = LiteralOpener()
    opened = list(flatten(literal_opener.rewrite(inlined)))
    return opened

class Unrebinder(S.SyntaxRewrite):
    """Rebindings like
    y = x
    or
    y0, y1 = x0, x1
    Can be eliminated completely.
    This is important for the backend, as phase inference and
    containerization assume that there is a unique identifier
    for every use of a variable.
    It's also inefficient to rebind things unnecessarily.
    This pass removes extraneous rebindings.
    """
    def __init__(self):
        self.env = pltools.Environment()

    def recursive_record(self, lhs, rhs):
        if isinstance(lhs, S.Name) and isinstance(rhs, S.Name):
            #Simple rebind
            self.env[lhs.id] = rhs.id
            return True
        elif isinstance(lhs, S.Tuple) and isinstance(rhs, S.Tuple):
            #Compound rebind:
            #Do not mark as extraneous unless all components are
            recorded = True
            for x, y in zip(lhs, rhs):
                recorded = self.recursive_record(x, y) and recorded
            return recorded
        else:
            return False
                
    def _Bind(self, b):
        self.rewrite_children(b)
        lhs = b.binder()
        rhs = b.value()

        extraneous = self.recursive_record(lhs, rhs)
        if extraneous:
            return None
        else:
            return b

    def _Name(self, n):
        if n.id in self.env:
            n.id = self.env[n.id]
        return n
        
    def rewrite_suite(self, suite):
        rewritten = map(self.rewrite, suite)
        return filter(lambda xi: xi is not None, rewritten)
            
    def _Procedure(self, p):
        stmts = self.rewrite_suite(p.body())
        p.parameters = stmts
        return p

    def _Cond(self, cond):
        body = self.rewrite_suite(cond.body())
        orelse = self.rewrite_suite(cond.orelse())
        return S.Cond(cond.test(), body, orelse)

def unrebind(ast):
    rewritten = Unrebinder().rewrite(ast)
    return rewritten
    
class ConditionalProtector(S.SyntaxRewrite):
    """
    Convert every expression of the form:

        E1 if P else E2

    into the equivalent form:

        ((lambda: E1) if P else (lambda: E2))()

    The purpose of this rewriter is to protect the branches of the
    conditional during later phases of the compiler.  It guarantees that
    exactly one of E1/E2 will ever be evaluated.
    """

    def __init__(self):
        pass


    def _If(self, e):
        self.rewrite_children(e)

        test   = e.test()
        body   = S.Lambda([], e.body())
        orelse = S.Lambda([], e.orelse())

        e.parameters = [test, body, orelse]

        return S.Apply(e, [])

class ArityChecker(S.SyntaxVisitor):
    def _Tuple(self, tup):
        self.visit_children(tup)
        if tup.arity() > 10:
            raise SyntaxError, 'Tuples cannot have more than 10 elements'
    def _Procedure(self, proc):
        self.visit_children(proc)
        if len(proc.formals()) > 10:
            raise SyntaxError, 'Procedures cannot have more than 10 arguments'
        
    
def arity_check(ast):
    ArityChecker().visit(ast)
    
class ReturnChecker(S.SyntaxVisitor):
    def suite_must_return(self, suite, error):
        if not isinstance(suite[-1], S.Return):
            raise SyntaxError, error
    def _Cond(self, cond):
        cond_error = 'Both branches of a conditional must end in a return'
        def check_cond_suite(suite):
            if isinstance(suite[0], S.Cond):
                self.visit_children(suite[0])
                if len(suite) != 1:
                    raise SyntaxError, cond_error
            else:
                self.suite_must_return(suite, cond_error)
        check_cond_suite(cond.body())
        check_cond_suite(cond.orelse())
    def _Procedure(self, proc):
        proc_error = 'A procedure must end in a return'
        last = proc.body()[-1]
        if isinstance(last, S.Cond):
            self.visit_children(proc)
        else:
            self.suite_must_return(proc.body(), proc_error)

def return_check(ast):
    ReturnChecker().visit(ast)

class BuiltinChecker(S.SyntaxVisitor):
    def __init__(self):
        import copperhead.prelude as P
        self.builtins = set(
            filter(lambda n: n[0] != '_', dir(P)))
    def _Procedure(self, proc):
        name = proc.name().id
        if name in self.builtins:
            raise SyntaxError, '%s is a builtin to Copperhead and cannot be redefined' % name

def builtin_check(ast):
    BuiltinChecker().visit(ast)

########NEW FILE########
__FILENAME__ = typeinference
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Second-generation type inference module

This module implements a new approach to type inference.  It separates
the inference process into separate (I) constraint generation and (II)
constraint solution phases.
"""

from itertools import ifilter, chain, islice
import coresyntax as AST
import coretypes as T
from pltools import Environment, resolve, name_supply, resolution_map
from utility import flatten

class InferenceError(TypeError):
    "An error occuring during type inference"
    def __init__(self, msg): TypeError.__init__(self, msg)

class TypingContext:
    """
    Encapsulate information passed around during type inference.
    Binding everything up in a structure like this makes it possible to
    add optional annotations without rewriting the parameter lists of
    all procedures involved in inference.
    """

    def __init__(self,
                 globals=None,
                 tvsupply=None):

        # Record the global Python namespace (if any) in which code is
        # defined.  This maps identifiers to values; by convention
        # Copperhead objects have a 'cu_type' slot that we will
        # use for typing information.
        #
        # This dictionary should never be modified.
        self.globals = globals or dict()

        # Supply of unique type variable names: #tv0, #tv1, #tv2, ...
        # They're known to be unique because they are illegal identifiers.
        self._tvsupply = tvsupply or name_supply(['#tv'], drop_zero=False)

        # The typings environment maps local identifiers to their
        # corresponding types.
        self.typings = Environment()

        # Type variables associated with formal parameters, both in
        # lambdas and procedures, are required to be monomorphic.  This
        # set records all introduced type variables that are known to be
        # monomorphic.  Since we make all internal variables unique, we
        # only need a single set for this, rather than a hierarchical
        # environment structure as with self.typings.
        self.monomorphs = set()

        # During inference, we accumulate a set of freely occurring
        # identifiers.  This set contains AST nodes, rather than names.
        # Thus, multiple occurrences of a given name (e.g., 'x') may be
        # found in this set if they occurred at separate source
        # locations.  For example, the expression 'x+x' will introduce
        # two free occurrences, not one.
        self.free_occurrences = set()

        # The inference system builds up a set of assumptions about the
        # types of identifiers occurring outside the current compilation
        # unit and which have no known 'cu_type' attribute.
        # This table provides a mapping from type variables created for
        # free occurrences to the AST node at which they occur.
        self.assumptions = dict()


    ######################################################################
    #
    # The following methods provide convenient ways of working with the
    # state encapsulated in the TypingContext
    #

    def fresh_typevar(self):
        return T.Typevar(self._tvsupply.next())

    def fresh_typevars(self, n):
        return [T.Typevar(n) for n in islice(self._tvsupply, n)]

    def fresh_typelist(self, keys, varmap=None):
        tvs = [self.fresh_typevar() for k in keys]
        if varmap:
            for k, v in zip(keys, tvs):
                varmap[k] = v
        return tvs

    def begin_scope(self):
        self.typings.begin_scope()
       
    def end_scope(self):
        self.typings.end_scope()

    def assuming(self, t, ast):
        assert t not in self.assumptions.keys()
        self.assumptions[t] = ast
        self.free_occurrences.add(ast)
        # XXX because monomorphs is scoped within functions, we treat
        # assumptions specially when generalizing bindings rather than
        # accumulating them here
        #self.monomorphs.add(t)

    ######################################################################
    #
    # Following are the methods required by the unification interface.
    #
       
    def instantiate(tcon, t):
        'Instantiate Polytypes as Monotypes with fresh type variables'
        if isinstance(t, T.Polytype):
            vars = tcon.fresh_typelist(t.variables)
            return T.substituted_type(t.monotype(),
                                      dict(zip(t.variables, vars)))
        else:
            return t

    def resolve_variable(tcon, t):
        'Resolve current mapping (if any) of typevars'
        if isinstance(t, T.Typevar): return resolve(t, tcon.typings)
        else: return t
        
    def occurs_check(tcon, t1, t2):
        if T.occurs(t1, t2):
            raise InferenceError, "%s occurs in %s" % (t1,t2)

    def is_variable(tcon, t):  return isinstance(t, T.Typevar)

    def error(tcon, msg):  raise InferenceError, msg


def resolve_type(t, S):
    """
    Return a new type where all type variables occurring free in t
    are replaced with their values under the substitution S.  If t has
    no free variables, it is returned unchanged.
    """
    
    free = list(T.free_in_type(t))
    if not free:  return t

    R = resolution_map(free, S)
    for v in free:
        if R[v] != v:
            R[v] = resolve_type(R[v], S)

    return T.substituted_type(t, R)

class TypeLabeling(AST.SyntaxVisitor):
    """
    Perform a traversal of an AST, labeling each with a new type variable.
    """

    def __init__(self, context):
        self.context = context
        self.verbose = False

    def _Lambda(self, node):
        if self.verbose:  print "Labeling: ", node
        self.visit(node.formals())
        self._default(node)

    def _Procedure(self, node):
        if self.verbose:  print "Labeling procedure:", node.name()
        self.visit(node.name())
        self.visit(node.formals())
        self.visit(node.body())

    def _Bind(self, node):
        if self.verbose:  print "Labeling:", node
        self.visit(node.binder())
        self.visit(node.value())


    def _default(self, node):
        t = self.context.fresh_typevar()
        t.source = node
        node.type = t
        if self.verbose:
            print "...", t, ":>", node
        self.visit_children(node)

class TypeResolution(AST.SyntaxVisitor):
    """
    Traverse the AST and resolve the types bound to the type variables
    associated with every node.
    """

    def __init__(self, solution, quantified):
        self.solution = solution
        self.quantified = quantified

    def _Lambda(self, node):
        self._default(node)
        self.visit(node.formals())

    def _Procedure(self, node):
        self.visit(node.body())
        self.visit(node.name())
        self.visit(node.formals())

    def _Bind(self, node):
        self.visit(node.value())
        self.visit(node.binder())

    def _default(self, node):
        if getattr(node, 'type', None):
            node.type = resolve_type(node.type, self.solution)
            #
            # XXX all quantification should normally have happened
            # already by this point (i.e., in the solver) solver by this
            # point
            #node.type = T.quantify_type(node.type, self.solution, self.quantified)
        self.visit_children(node)

class Constraint(object): pass

class Equality(Constraint):

    def __init__(self, lhs, rhs, source=None):
        self.parameters = (lhs, rhs)
        self.source = source

    def __str__(self):
        lhs, rhs = self.parameters
        return str(lhs)+" == "+str(rhs)

class Generalizing(Constraint):

    def __init__(self, t1, t2, monomorphs, source=None):
        self.parameters = (t1, t2, monomorphs)
        self.source = source

    def __str__(self):
        return "Generalizing(%s, %s, %s)" % self.parameters

class ClosedOver(Constraint):

    def __init__(self, t, closed, body, source=None):
        self.parameters = (t, closed, body)
        self.source = source

    def __str__(self):
        return "ClosedOver(%s, %s, %s)" % self.parameters



class ConstraintGenerator(AST.SyntaxFlattener):

    def __init__(self, context=None):

        self.context = context or TypingContext()

    def _Number(self, ast):
        if isinstance(ast.val, int):
            yield Equality(ast.type, T.Long, ast)
        elif isinstance(ast.val, float):
            yield Equality(ast.type, T.Double, ast)
        
    def _Name(self, ast):
        if ast.id is 'True' or ast.id is 'False':
            yield Equality(ast.type, T.Bool, ast)
        elif ast.id is 'None':
            yield Equality(ast.type, T.Void, ast)

        elif ast.id in self.context.typings:
            yield Equality(ast.type,
                       self.context.instantiate(self.context.typings[ast.id]),
                       ast)

        elif ast.id in self.context.globals:
            obj = self.context.globals[ast.id]
            t = getattr(obj, 'cu_type', None)

            if isinstance(t, T.Type):
                yield Equality(ast.type, self.context.instantiate(t), ast)
            else:
                # This name has no known type at present.  Therefore, we
                # treat it as freely occurring (as below).
                self.context.assuming(ast.type, ast)

        else:
            # This was a freely occurring variable reference
            self.context.assuming(ast.type, ast)

    def _Tuple(self, ast):
        for c in self.visit_children(ast): yield c
        yield Equality(ast.type,
                       T.Tuple(*[x.type for x in ast.children()]),
                       ast)

    def _Index(self, ast):
        for c in self.visit_children(ast): yield c
        yield Equality(ast.type, ast.value().type, ast)

    def _Subscript(self, ast):
        for c in self.visit_children(ast): yield c
        yield Equality(ast.slice().type, T.Long, ast)
        yield Equality(T.Seq(ast.type), ast.value().type, ast)


    def _If(self, ast):
        for c in self.visit_children(ast): yield c

        tb, t1, t2 = ast.test().type, ast.body().type, ast.orelse().type
        yield Equality(tb, T.Bool, ast)
        yield Equality(t1, t2, ast)
        yield Equality(ast.type, t1, ast)

    def _And(self, ast):
        for x in ast.children():
            for c in self.visit(x): yield c
            yield Equality(x.type, T.Bool, ast)

        yield Equality(ast.type, T.Bool, ast)

    def _Or(self, ast): return self._And(ast)

    def _Apply(self, ast):
        for c in self.visit_children(ast): yield c
        fntype = ast.function().type
        argtypes = [x.type for x in ast.arguments()]

        yield Equality(fntype,
                       T.Fn(argtypes, ast.type),
                       ast)

    def _Map(self, ast):
        for c in self.visit_children(ast): yield c

        fn, args = ast.parameters[0], ast.parameters[1:]
        argtypes = [x.type for x in args]

        # Type variables that name the element types for each of the
        # argument sequences
        items = self.context.fresh_typelist(args)

        for itemtype, seqtype in zip(items, argtypes):
            itemtype.source = None
            yield Equality(seqtype, T.Seq(itemtype), ast)

        restype = self.context.fresh_typevar()
        restype.source = None

        yield Equality(fn.type, T.Fn(items, restype), ast)
        yield Equality(ast.type, T.Seq(restype), ast)

    def _Lambda(self, ast):
        restype = ast.parameters[0].type
        argnames = [arg.id   for arg in ast.variables]
        argtypes = [arg.type for arg in ast.variables]

        con = self.context
        con.begin_scope()
        con.typings.update(dict(zip(argnames, argtypes)))
        con.monomorphs.update(argtypes)

        for c in self.visit_children(ast): yield c

        self.context.end_scope()

        yield Equality(ast.type, T.Fn(argtypes, restype), ast)

    def _Closure(self, ast):
        for c in self.visit_children(ast): yield c

        yield ClosedOver(ast.type, ast.closed_over(), ast.body().type, ast)

    # ... statements ...

    def _Return(self, ast):
        for c in self.visit_children(ast): yield c
        yield Equality(ast.type, ast.value().type, ast)

    def _Bind(self, ast):
        # Constraints produced by the RHS
        for c in self.visit_children(ast): yield c

        # Make binders in the LHS visible in the typing environment
        bindings = [(node.id, node.type) for node in AST.walk(ast.binder())
                                         if isinstance(node, AST.Name)]

        self.context.typings.update(dict(bindings))

        # Generate destructuring constraints (if any) in the LHS
        for c in self.visit(ast.binder()): yield c

        # XXX We only allow polymorphic bindings when the LHS is a
        #     single identifier.  Generalizing this would be nice but is
        #     fraught with peril if the RHS is not required to have a
        #     syntactically equivalent structure to the LHS.
        if isinstance(ast.binder(), AST.Name):
            M = self.context.monomorphs
            yield Generalizing(ast.binder().type, ast.value().type, M, ast)
        else:
            yield Equality(ast.binder().type, ast.value().type, ast)



    def visit_block(self, ast, restype, block):
        for stmt in block:
            # Generate constraints from each statement in turn
            for c in self.visit(stmt): yield c

            # Any statement claiming to have a return type must return
            # the same type as all the others
            t_i = getattr(stmt, 'type', None)
            if t_i:
                yield Equality(restype, t_i, ast)

    def _Cond(self, ast):
        for c in self.visit(ast.test()): yield c
        yield Equality(ast.test().type, T.Bool, ast)

        for c in self.visit_block(ast, ast.type, ast.body()): yield c
        for c in self.visit_block(ast, ast.type, ast.orelse()): yield c

    def _Procedure(self, ast):
        con = self.context

        # Create a new type variable for the return type of the procedure
        restype = con.fresh_typevar()
        restype.source = None

        # Get the names and type variables for the formal parameters
        argnames = [arg.id   for arg in flatten(ast.formals())]
        argtypes = [arg.type for arg in flatten(ast.formals())]

        
        
        # Make the definition of this function visible within its body
        # to allow for recursive calls
        con.typings[ast.name().id] = ast.name().type

        con.begin_scope()

        # Make the formals visible
        con.typings.update(dict(zip(argnames, argtypes)))
        prior_monomorphs = con.monomorphs
        con.monomorphs = prior_monomorphs | set(argtypes)

        argtypeit = iter(argtypes)
        
        # Construct the formals types
        def make_type(formal):
            if hasattr(formal, '__iter__'):
                return T.Tuple(*[make_type(x) for x in iter(formal)])
            else:
                return argtypeit.next()

        formals_types = make_type(ast.formals())

        # XXX This makes the restriction that recursive invocations of F
        # in the body of F must have the same type signature.  Probably
        # not strictly necessary, but allowing the more general case
        # might prove problematic, especially in tail recursive cases.
        # For now, we will forbid this.
        con.monomorphs.add(ast.name().type)

        # Produce all constraints for arguments
        # Tuple arguments, for example, will produce constraints
        for a in ast.formals():
            for c in self.visit(a): yield c
        
        # Produce all the constraints for the body
        for c in self.visit_block(ast, restype, ast.body()): yield c

        con.monomorphs = prior_monomorphs

        M = set(self.context.monomorphs)
        yield Generalizing(ast.name().type,
                           T.Fn(formals_types, restype),
                           M,
                           ast)

        con.end_scope()


    # XXX Should probably segregate this elsewhere, since while blocks are
    #     only allowed internally
    def _While(self, ast):
        for c in self.visit(ast.test()): yield c
        yield Equality(ast.test().type, T.Bool, ast)

        for c in self.visit_block(ast, ast.type, ast.body()): yield c

class ConstrainInputTypes(AST.SyntaxFlattener):
    def __init__(self, input_types):
        self.input_types = input_types
        if input_types:
            self.entry_points = set(input_types.keys())
        else:
            self.entry_points = set()
    def _Procedure(self, ast):
        ident = ast.name().id
        if ident in self.entry_points:
            for formal, entry_type in zip(ast.formals(), self.input_types[ident]):
                yield Equality(formal.type, entry_type, formal)
    


class Solver1(object):

    def __init__(self, constraints, context):
        self.constraints = constraints
        self.context     = context

        # The solution that we're building is a substitution mapping
        # type variables into types.  Any type variable not contained in
        # the solution is assumed to map to itself
        self.solution = dict()

        # Keep track of type variables we generalize into quantifiers
        self.quantified = dict()

        # A single pass through the input constraints may produce a
        # solution, but some constraints may remain.  Here we collect
        # the remaining constraints for later solution.
        from collections import deque
        self.pending = deque()

        self.verbose = False

    def unify_variable(self, tvar, t):
        assert isinstance(tvar, T.Typevar)
        assert isinstance(t, T.Type)

        t = resolve_type(t, self.solution)
        self.context.occurs_check(tvar, t)

        #if len(list(T.free_in_type(t))) > 0:
        if False:
            self.pending.append(Equality(tvar, t, tvar.source))
        else:
            self.solution[tvar] = t


    def unify_monotypes(self, t1, t2):
        "Unify the given types, which must be either Monotypes or Variables"

        assert isinstance(t1, (T.Monotype, T.Typevar)) 
        assert isinstance(t2, (T.Monotype, T.Typevar)) 

        con = self.context

        # Resolve w.r.t. the current solution before proceeding
        t1 = resolve(t1, self.solution)
        t2 = resolve(t2, self.solution)
        if self.verbose: print "\tunifying", t1, "and", t2

        if t1==t2:                  pass
        elif con.is_variable(t1):   self.unify_variable(t1, t2)
        elif con.is_variable(t2):   self.unify_variable(t2, t1)

        else:
            t1 = self.context.instantiate(t1)
            t2 = self.context.instantiate(t2)
            if t1.name != t2.name or len(t1.parameters) != len(t2.parameters):
                con.error('type mismatch %s and %s' % (t1,t2))
           
            for (u,v) in zip(t1.parameters, t2.parameters):
                self.unify_monotypes(u, v)

    def generalize_binding(self, t1, t2, M):
        assert isinstance(t1, T.Typevar)
        assert isinstance(t2, (T.Typevar, T.Monotype))

        # Generalization occurs for identifiers introduced in
        # declaration statements.  This may, for instance, occur as the
        # result of a declaration:
        #     x = E
        # or a procedure definition
        #     def f(...): S
        #
        # The type variable t1 associated with the binder (e.g., 'x') is
        # allowed to become a Polytype.  We generate this polytype by
        # quantifying over the free variables of t2 that do not occur in
        # M.

        # NOTE: In general, we must be careful about when we can solve
        # Generalizing constraints.  In the current solver, where
        # constraints are generated in post-order, they can be solved
        # immediately.  In other orderings, they may need to be deferred
        # if they contain "active" type variables.

        r1 = resolve(t1, self.solution)
        r2 = resolve_type(t2, self.solution)

        if self.verbose:
            print "\tt1 =", t1
            print "\tt2 =", t2
            print "\tresolve(t1) =", r1
            print "\tresolve(t2) =", r2

        if r1 != t1 and isinstance(r2, T.Monotype):
            self.unify_monotypes(r1, r2)
            r2 = resolve_type(t2, self.solution)

        # The set of type variables associated with assumptions should
        # also be treated as monomorphs.  While we may have made
        # assumptions about a polymorphic function, we will have
        # generated a fresh type variable for each occurrence.  These
        # type variables are thus properly monomorphic.
        #
        R = set()
        for x in chain(M, self.context.assumptions.keys()):
            R |= set(T.names_in_type(resolve_type(x, self.solution)))

        if self.verbose:
            print "\tR =", R

        assert self.context.is_variable(t1)
        self.solution[t1] = T.quantify_type(r2, R, self.quantified)
        if self.verbose:
            print "\t--> Quantifying", t2, "to", self.solution[t1]


    def closing_over(self, t, closed, body):
        # NOTE: Like the Generalizing constraint, we're implicitly
        #       assuming that due to constraint ordering the body
        #       referenced here has already been solved.

        fntype = self.context.instantiate(resolve_type(body, self.solution))
        if not isinstance(fntype, T.Fn):
            raise InferenceError, "closure must be over functional types"

        # Get the list of argument types from the Fn type
        innertypes = fntype.input_types()

        # Partition the inner argument types into the outer types
        # exported to the world and those corresponding to the closed
        # arguments
        outertypes, closedtypes = innertypes[:-len(closed)], \
                                  innertypes[-len(closed):]

        for v, t2 in zip(closed, closedtypes):
            if self.verbose:
                print "\tt1 =", v.type
                print "\tt2 =", t2
            t1 = resolve(v.type, self.solution)
            t1 = self.context.instantiate(t1)
            if self.verbose:
                print "\tresolve(t1) =", t1
                print "\tresolve(t2) =", resolve_type(t2, self.solution)
            self.unify_monotypes(t1, t2)

        self.unify_monotypes(t, T.Fn(outertypes, fntype.result_type()))

    def compact_solution(self):
        for v, t in self.solution.items():
            self.solution[v] = resolve_type(t, self.solution)

        # note: could delete any self-mappings for additional cleansing

    def solve1(self, c):
        if self.verbose: print ".. solving", c, "\tfrom", c.source

        if isinstance(c, Equality):
            lhs, rhs = c.parameters
            self.unify_monotypes(lhs, rhs)

        elif isinstance(c, Generalizing):
            t1, t2, monomorphs = c.parameters
            self.generalize_binding(t1, t2, monomorphs)

        elif isinstance(c, ClosedOver):
            t, closed, body = c.parameters
            self.closing_over(t, closed, body)

        else:
            self.context.error("encountered unknown constraint type") 

    def solve(self):
        # (1) Process the initial constraint system
        for c in self.constraints:
            self.solve1(c)

        # (2) Process all remaining constraints
        while self.pending:
            self.solve1(self.pending.popleft())

        # (3) Clean-up the solution
        self.solution.update(self.quantified)
        self.compact_solution()

        if self.verbose:
            print
            print
            print "The solution is:"
            for v, t in self.solution.items():
                print "  %s == %s \t\t {%s}" % (v, t, getattr(v,'source',''))

def infer(P, verbose=False, globals=None, context=None, input_types=None):
    'Run type inference on the given AST.  Returns the inferred type.'
    tcon = context or TypingContext(globals=globals)
    # Label every AST node with a temporary type variable
    L = TypeLabeling(tcon)
    L.verbose = verbose
    L.visit(P)

    # Generate constraints from AST
    # And chain them to constraints from input_types
    C = chain(ConstrainInputTypes(input_types).visit(P),
              ConstraintGenerator(tcon).visit(P))


    S = Solver1(C,tcon)
    S.verbose = verbose

    S.solve()

    if verbose:
        print "\nThe free occurrence set is:"
        print "    ", tcon.free_occurrences
        print "\nThe assumption set is:"
        print "    ", tcon.assumptions

    if len(tcon.free_occurrences) > 0:
        undef = set([x.id for x in tcon.free_occurrences])
        raise InferenceError, 'undefined variables: %s' % list(undef)

    if len(tcon.assumptions) > 0:
        assumed = set(assumptions.values())
        raise InferenceError, 'unexplored assumptions: %s' % list(assumed)

    # Resolve the AST type slots to their solved types
    TypeResolution(S.solution, S.quantified).visit(P)

    # Resolve any outstanding variables in the typing context
    # XXX it's inefficient to go through the whole typings
    # environment when we could just record which ones were
    # introduced by the program P
    for id in tcon.typings:
        t = tcon.typings[id]
        if t in S.solution:
            tcon.typings[id] = resolve_type(t, S.solution)

    if isinstance(P, list):
        result = getattr(P[-1], 'type', T.Void)
    else:
        result = getattr(P, 'type', T.Void)
        
    # We quantify here to normalize the result of this procedure.
    # For instance, running the solver on a polymorphic expression like
    # "op_plus" will instantiate the polytype for op_plus with fresh
    # type variables.  While what we want internally, this is not what
    # external clients expect.
    return T.quantify_type(result)

########NEW FILE########
__FILENAME__ = unifier
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Procedures for unification of syntactic forms.
"""

def unify(t1, t2, tcon):
    # (1) Instantiate with fresh variables where appropriate
    t1 = tcon.instantiate(t1)
    t2 = tcon.instantiate(t2)

    # (2) If t1/t2 are variables, resolve their values in current environment
    t1 = tcon.resolve_variable(t1)
    t2 = tcon.resolve_variable(t2)

    # (3a) For variables, update the environment
    if tcon.is_variable(t1):
        # Do nothing if t1 and t2 are identical typevars
        if t1!=t2:
            tcon.occurs_check(t1, t2)
            tcon.typings[t1] = t2
    elif tcon.is_variable(t2):
        tcon.occurs_check(t2, t1)
        tcon.typings[t2] = t1

    # (3b) For other forms, check that constructors are compatible and
    #      then recursively unify parameters
    else:
        if t1.name != t2.name or len(t1.parameters) != len(t2.parameters):
            tcon.error('type mismatch %s and %s' % (t1,t2))
       
        for (u,v) in zip(t1.parameters, t2.parameters):
            unify(u, v, tcon)

########NEW FILE########
__FILENAME__ = utility
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

def flatten(x):
    if hasattr(x, '__iter__'):
        for xi in x:
            if hasattr(xi, '__iter__'):
                for i in flatten(iter(xi)):
                    yield i
            else:
                yield xi
    else:
        yield x

def interleave(*args):
    iterators = [iter(x) for x in args]
    while iterators:
        for it in iterators:
            try:
                yield it.next()
            except:
                iterators.remove(it)

import copy

class ExtendingList(list):
    def __init__(self, default=0):
        list.__init__(self)
        self.default=default
        
    def enlarge(self, length):
        if len(self) < length:
            extension = length - len(self)
            super(ExtendingList, self).extend([copy.copy(self.default) \
                                               for x in range(extension)])
    def __getitem__(self, index):
        self.enlarge(index + 1)
        return super(ExtendingList, self).__getitem__(index)
    def __setitem__(self, index, value):
        self.enlarge(index + 1)
        return super(ExtendingList, self).__setitem__(index, value)

########NEW FILE########
__FILENAME__ = visitor
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#


class Visitor(object):

    def __init__(self):
        super(Visitor,self).__init__()
        self.fallback = self.unknown_node

    def visit(self, tree):
        if isinstance(tree, list):
            return [self.visit(i) for i in tree]
        elif isinstance(tree, tuple): 
            return [self.visit(i) for i in list(tree)]
        else:
            name = "_"+tree.__class__.__name__
            if hasattr(self, name):
                fn = getattr(self, name)
                return fn(tree)
            else:
                return self.fallback(tree)

    def __call__(self, tree): return self.visit(tree)

    def unknown_node(self, tree):
        raise ValueError, "visiting unknown node: %s " % tree

########NEW FILE########
__FILENAME__ = decorators
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Decorators for Copperhead procedure declarations
"""

def cu(fn):
    """
    Decorator for declaring that a procedure is visible in Copperhead.

    For example:
        @cu
        def plus1(x):
            return [xi + 1 for xi in x]
    """
    from runtime import CuFunction

    # Wrap Python procedure in CuFunction object that will intercept
    # calls (e.g., for JIT compilation).
    cufn = CuFunction(fn)

    return cufn

def cutype(type):
    """
    Decorator for declaring the type of a Copperhead procedure.

    For example:
        @cutype("[Int] -> Int")
        @cu
        def plus1(x):
            return [xi + 1 for xi in x]
    """
    from compiler.parsetypes import T, type_from_text

    if isinstance(type, str):
        type = type_from_text(type)
    elif not isinstance(type, T.Type):
        raise TypeError, \
                "type (%s) must be string or Copperhead Type object" % type

    def setter(fn):
        # Don't use CuFunction methods here, as we may be decorating a
        # raw Python procedure object.
        fn.cu_type = type
        return fn

    return setter

def cushape(shape):
    """
    Decorator for declaring the shape of a Copperhead procedure.

    This decorator expects a python function which, given input shapes,
    will compute a tuple: (output_shapes, output_constraints).
    
    For example:
        @cushape(lambda *x:  (Unit, []))
        @cushape(lambda a,b: (a, [sq(a,b)])

    This is largely meant for internal use.  User programs should
    generally never have declared shapes.

    """


    if not callable(shape):
        raise TypeError("%s is not a legal procedure shape" % shape)


    def setter(fn):
        fn.cu_shape = shape
        return fn
    return setter


def cuphase(*args):
    """
    Decorator for declaring the phase completion of a Copperhead procedure.

    This decorator expects a tuple consisting of input completion requirements
    and output completion declaration, which it then fashions into a phase
    procedure.
    
    For example:
        @cuphase((P.local, P.total), P.local)

    This is largely meant for internal use.  User programs should
    generally never have declared phases.

    """
    import compiler.phasetypes as P
    cu_phase = P.cuphase(*args)
    def setter(fn):
        fn.cu_phase = cu_phase
        return fn
    return setter

def cubox(*args):
    """
    Decorator for black box Copperhead procedures.

    This decorator accepts parameters: each parameter is a file to be included
    in compilation when this black box is compiled.

    For example:
        @cubox('wrappers/reduce.h')
    """
    from runtime import CuBox
    def setter(fn):
        return CuBox(fn, *args) 
    return setter

########NEW FILE########
__FILENAME__ = interlude
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Copperhead Interlude

The Copperhead compiler transforms input programs through a number of
discrete phases before generating C code in the back-end.  These
intermediate forms of the program are all valid Python programs,
although they may or may not be valid Copperhead programs.  The
Copperhead Interlude provides implementations of various special
constructions used by the compiler.
"""

class mutable:
    """
    The Copperhead mid-end uses mutable blocks to explicitly declare
    what identifiers may be rebound (e.g., in loop bodies).  This
    context manager object makes such constructions syntactically valid.

    In native Python, a mutable block essentially does nothing, since
    all Python identifiers may be re-assigned.

        >>> x = 1
        >>> with mutable(x):
        ...    x = x + 1
        >>> print x
        2

    The only real effect in Python is simply that the variables named as
    arguments to mutable must already be defined.

    The typical use of mutable blocks within the Copperhead compiler is
    in conjunction with variables being modified in loop bodies.

        count = 0
        i = 0
        with mutable(i, count):
            while i<len(A):
                if A[i]:
                    count = count + 1
                i = i + 1
    """

    def __init__(self, *vars): pass
    def __enter__(self): pass
    def __exit__(self, *args): pass

class closure:
    """
    The Copperhead compiler transforms procedures and lambdas that close
    over external values into explicit closure objects.
    
    
    Consider a procedure like the following example:

        >>> def original_scale(a, X):
        ...    def mul(x):
        ...        return a*x
        ...    return map(mul, X)
        >>> original_scale(2, [1, 2, 3, 4])
        [2, 4, 6, 8]

    The inner procedure mul() closes over the value of a in the body of
    scale.  The Copperhead compiler will transform this procedure into
    one where the closed values are explicitly captured with a closure()
    object and explicitly passed as arguments to mul().

        >>> def transformed_scale(a, X):
        ...    def mul(x, _K0):
        ...        return _K0*x
        ...    return map(closure([a], mul), X)
        >>> transformed_scale(2, [1, 2, 3, 4])
        [2, 4, 6, 8]
    """

    def __init__(self, K, fn):
        self.K = K
        self.fn = fn

    def __call__(self, *args):
        args = list(args) + list(self.K)
        return self.fn(*args)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = prelude
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Copperhead Prelude

This module provides native Python implementations for the set of
standard functions provided to all Copperhead programs.  When running on
a parallel device, operations like gather() or reduce() may have special
meaning.  They may, for instance, require the synchronization of various
parallel tasks.  Therefore, they are implemented in Copperhead via
architecture-specific primitive routines.  The Python implementations
here guarantee that Copperhead programs using these functions will run
correctly in the host Python interpreter as well.

Some of the functions listed here are Python built-ins, such as reduce()
and zip().  Unlike in Python, these functions are treated by Copperhead
as parallel primitives.  They are declared here so that they are visible
as Copperhead primitives.  Some, like zip(), may also have a restricted
interface in comparison to their Python counterpart.  The built-ins any,
all, sum, min, & max are treated as special cases of reduce.

Finally, the Python built-in map() is treated as a special syntactic
form by Copperhead.
"""
from __future__ import division
import __builtin__

from decorators import cutype
import copperhead.runtime.places as PL

import math
import numpy as np

# Unlike @functools.wraps, our @_wraps decorator only sets the docstring
# Thus reduce.__module__ will become 'copperhead.prelude' rather than
# '__builtin__'.  This makes it possible for the application to
# determine which reduce it's calling, in case it cares
def _wraps(wrapped):
    from functools import wraps
    return wraps(wrapped, assigned=['__doc__'])

########################################################################
#
# Python built-ins
#
# Reflect built-in Python functions that have special meaning to
# Copperhead.  These wrapper functions allow us to (a) annotate them
# with type attributes and (b) restrict arguments if necessary.
#

@_wraps(__builtin__.map)
def map(f, *sequences):
    """
    Applies the function f elementwise across a number of sequences.
    The function f should have arity equal to the number of arguments.
    Each sequence must have the same length.
    """
    return __builtin__.map(f, *sequences)

@cutype("( (a,a)->a, [a], a ) -> a")
@_wraps(__builtin__.reduce)
def reduce(fn, x, init):
    """
    Repeatedly applies the given binary function to the elements of the
    sequence.  Using the infix notation <fn>, reduction computes the
    value: init <fn> x[0] <fn> ... <fn> x[len(x)-1].
    
    The given function is required to be both associative and
    commutative.

        >>> reduce(op_add, [1, 2, 3, 4, 5], 0)
        15

        >>> reduce(op_add, [1, 2, 3, 4, 5], 10)
        25

        >>> reduce(op_add, [], 10)
        10

    Unlike the Python built-in reduce, the Copperhead reduce function
    makes the initial value mandatory.
    """
    return __builtin__.reduce(fn, x, init)

@cutype("[Bool] -> Bool")
@_wraps(__builtin__.any)
def any(sequence):
    """
    Returns True if any element of sequence is True.  It is equivalent
    to calling reduce(op_or, sequence, False).

        >>> any([True, False, False])
        True

        >>> any([])
        False
    """
    return __builtin__.any(sequence)

@cutype("[Bool] -> Bool")
@_wraps(__builtin__.any)
def all(sequence):
    """
    Returns True if all elements of sequence are True.  It is equivalent
    to calling reduce(op_and, sequence, True).

        >>> all([True, False, False])
        False

        >>> all([])
        True
    """
    return __builtin__.all(sequence)

@cutype("[a] -> a")
@_wraps(__builtin__.sum)
def sum(sequence):
    """
    This is equivalent to calling reduce(op_add, sequence, 0).

        >>> sum([1, 2, 3, 4, 5])
        15

        >>> sum([])
        0
    """
    return __builtin__.sum(sequence)

@cutype("[a] -> a")
@_wraps(__builtin__.min)
def min(sequence):
    """
    Returns the minimum value in sequence, which must be non-empty.

        >>> min([3, 1, 4, 1, 5, 9])
        1

        >>> min([])
        Traceback (most recent call last):
          ...
        ValueError: min() arg is an empty sequence
    """
    return __builtin__.min(sequence)

@cutype("[a] -> a")
@_wraps(__builtin__.max)
def max(sequence):
    """
    Returns the maximum value in sequence, which must be non-empty.

        >>> max([3, 1, 4, 1, 5, 9])
        9

        >>> max([])
        Traceback (most recent call last):
          ...
        ValueError: max() arg is an empty sequence
    """
    return __builtin__.max(sequence)

@cutype("[a] -> (Long, a)")
def argmax(seq):
    """
    Returns the index of the maximum value of the sequence, and the
    maximum value.

    >>> argmax([3, 1, 4, 1, 5, 9])
    (5, 9)
    """
    return seq

@cutype("[a] -> Long")
@_wraps(__builtin__.len)
def len(sequence):  return __builtin__.len(sequence)

@cutype("Long -> [Long]")
@_wraps(__builtin__.range)
def range(n):
    """
    Returns the sequence of integers from 0 to n-1.

        >>> range(5)
        [0, 1, 2, 3, 4]

        >>> range(0)
        []
    """
    return __builtin__.range(n)

@_wraps(__builtin__.zip)
def zip(*args):
    """
    Combines corresponding tuples of elements from several sequences into a
    sequence of pairs.

        >>> zip([1, 2, 3], [4, 5, 6])
        [(1, 4), (2, 5), (3, 6)]

    Zipping empty sequences will produce the empty sequence.

        >>> zip([], [])
        []

    The given sequences must be of the same length.

        >>> zip([1, 2], [3])
        Traceback (most recent call last):
          ...
        AssertionError
    """
    return __builtin__.zip(*args)

@cutype("(a->Bool, [a]) -> [a]")
@_wraps(__builtin__.filter)
def filter(function, sequence):
    """
    Return a sequence containing those items of sequence for which
    function(item) is True.  The order of items in sequence is
    preserved.

        >>> filter(lambda x: x<3, [3, 1, 5, 0, 2, 4])
        [1, 0, 2]
    """
    return __builtin__.filter(function, sequence)

@cutype("([a]) -> [(Int, a)]")
@_wraps(__builtin__.enumerate)
def enumerate(x):
    """
    Return a sequence containing (index, value) pairs, with values
    from the input sequence.

    """
    return list(__builtin__.enumerate(x))

############## Copperhead primitives not in Python builtins

@cutype("([a], [b]) -> [a]")
def gather(x, indices):
    """
    Return the sequence [x[i] for i in indices].

    >>> gather([8, 16, 32, 64, 128], [3, 0, 2])
    [64, 8, 32]

    >>> gather([8, 16, 32, 64, 128], [])
    []
    """
    return [x[i] for i in indices]


@cutype("([a], [b], [a]) -> [a]")
def scatter(src, indices, dst):
    """
    Create a copy of dst and update it by scattering each src[i] to
    location indices[i] of the copy.  Returns the final result.

        >>> scatter([11, 12], [3, 1], [1, 2, 3, 4])
        [1, 12, 3, 11]

    It is valid to pass empty src & indices lists to scatter, whose
    result will then be an unaltered copy of dst.

    If any indices are duplicated, one of the corresponding values
    from src will be chosen arbitrarily and placed in the result.  

        >>> scatter([], [], [1, 2, 3, 4])
        [1, 2, 3, 4]
    """
    assert len(src)==len(indices)

    result = list(dst)
    for i in xrange(len(src)):
        result[indices[i]] = src[i]
    return result

@cutype("([a], [b]) -> [a]")
def permute(x, indices):
    """
    Permute the sequence x by sending each value to the index specified
    in the corresponding array.

        >>> permute([1, 2, 3, 4], [3, 0, 1, 2])
        [2, 3, 4, 1]

    Permute requires that the lengths of its arguments match.  It will
    raise an AssertionError if they do not.

        >>> permute([1, 2, 3, 4], [3, 0, 1])
        Traceback (most recent call last):
          ...
        AssertionError

    If any indices are duplicated, one of the corresponding values
    from x will be chosen arbitrarily and placed in the result.
    """
    assert len(x)==len(indices)
    return scatter(x, indices, x)

@cutype("([a], [(b,a)]) -> [a]")
def update(dst, updates):
    """
    Compute an updated version of dst where each (i, x) pair in updates
    is used to replace the value of dst[i] with x.

        >>> update([True, False, True, False], [(1, True), (0, False)])
        [False, True, True, False]

    If the updates list is empty, dst is returned unmodified.

        >>> update(range(4), [])
        [0, 1, 2, 3]
    """
    indices, src = unzip(updates) if updates else ([],[])
    return scatter(src, indices, dst)

@cutype("((a,a)->a, [a]) -> [a]")
def scan(f, A):
    """
    Return the inclusive prefix scan of f over A.
    
    >>> scan(lambda x,y: x+y, [1,1,1,1,1])
    [1, 2, 3, 4, 5]

    >>> scan(lambda x,y: x, [4, 3, 1, 2, 0])
    [4, 4, 4, 4, 4]

    >>> scan(lambda x,y: x+y, [])
    []
    """
    B = list(A)

    for i in xrange(1, len(B)):
        B[i] = f(B[i-1], B[i])

    return B

@cutype("((a,a)->a, [a]) -> [a]")
def rscan(f, A):
    """
    Reverse (i.e., right-to-left) scan of f over A.

    >>> rscan(lambda x,y: x+y, [1,1,1,1,1])
    [5, 4, 3, 2, 1]

    >>> rscan(lambda x,y: x, [3, 1, 4, 1, 5])
    [5, 5, 5, 5, 5]

    >>> rscan(lambda x,y: x+y, [])
    []
    """
    return list(reversed(scan(f, reversed(A))))

@cutype("((a,a)->a, a, [a]) -> [a]")
def exclusive_scan(f, prefix, A):
    """
    Exclusive prefix scan of f over A.

    >>> exclusive_scan(lambda x,y: x+y, 0, [1, 1, 1, 1, 1])
    [0, 1, 2, 3, 4]
    """
    return scan(f, [prefix] + A[:-1])

@cutype("((a,a)->a, a, [a]) -> [a]")
def exclusive_rscan(f, suffix, A):
    """
    Reverse exclusive prefix scan of f over A.

    >>> exclusive_rscan(lambda x,y: x+y, 0, [1, 1, 1, 1, 1])
    [4, 3, 2, 1, 0]
    """
    return rscan(f, A[1:]+[suffix])



@cutype("[a] -> [Long]")
def indices(A):
    """
    Return a sequence containing all the indices for elements in A.

    >>> indices([6, 3, 2, 9, 10])
    [0, 1, 2, 3, 4]
    """
    return range(len(A))

@cutype("(a, b) -> [a]")
def replicate(x, n):
    """
    Return a sequence containing n copies of x.

        >>> replicate(True, 3)
        [True, True, True]

    If n=0, this will return the empty list.

        >>> replicate(101, 0)
        []
    """
    return [x]*n

@cutype("(Long, Long) -> [Long]")
def bounded_range(a, b):
    """
    Return a sequence from [a, b).
    This exists because we currently do not support function overloads,
    and we use the Python range in its simplest form:
    range(b) outputs bounded_range(0, b). 

        >>> bounded_range(1, 10)
        [1, 2, 3, 4, 5, 6, 7, 8, 9]

    If a==b, this will return the empty list.

        >>> bounded_range(1, 1)
        []
    """

    return range(a, b)

def unzip(seq):
    """
    Inverse of zip.  Converts a list of tuples into a tuple of lists.

    >>> unzip([(1,2), (3,4), (5,6)])
    ([1, 3, 5], [2, 4, 6])
    """
    return tuple(map(list, __builtin__.zip(*seq)))

@cutype("([a], b, a) -> [a]")
def shift(src, offset, default):
    """
    Returns a sequence which is a shifted version of src.
    It is shifted by offset elements, and default will be
    shifted in to fill the empty spaces.
    """
    u, v = split_at(src, offset)
    if offset < 0:
        return join([replicate(default, -offset), u])
    else:
        return join([v, replicate(default, offset)])

@cutype("([a], b) -> [a]")
def rotate(src, offset):
    """
    Returns a sequence which is a rotated version of src.
    It is rotated by offset elements.
    """
    u, v = split_at(src, offset)
    return join([v, u])
    

@cutype("((a, a)->Bool, [a]) -> [a]")
def sort(fn, x):
    """
    Returns a sequence containing the sorted values of `x`, sorted by
    `fn`, which must be a strict weak ordering like cmp_lt.
    """
    def my_cmp(xi, xj):
        if fn(xi, xj):
            return -1
        else:
            return 0
    return sorted(x, cmp=my_cmp)


########################################################################
#
# Math functions
#

@cutype("a -> a")
@_wraps(np.sqrt)
def sqrt(x):
    return np.sqrt(x)

@cutype("a -> a")
@_wraps(np.abs)
def abs(x):
    return np.abs(x)

@cutype("a -> a")
@_wraps(np.exp)
def exp(x):
    return np.exp(x)

@cutype("a -> a")
@_wraps(np.log)
def log(x):
    return np.log(x)
    
########################################################################
#
# Operators
#
# Reflect various unary/binary function names that are equivalent to
# infix operators like + and ==.
#

import operator as _op

@cutype("(a,a) -> a")
@_wraps(_op.add)
def op_add(x,y): return _op.add(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.sub)
def op_sub(x,y): return _op.sub(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.mul)
def op_mul(x,y): return _op.mul(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.div)
def op_div(x,y): return _op.div(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.mod)
def op_mod(x,y): return _op.mod(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.pow)
def op_pow(x,y): return _op.pow(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.lshift)
def op_lshift(x,y): return _op.lshift(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.rshift)
def op_rshift(x,y): return _op.rshift(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.or_)
def op_or(x,y): return _op.or_(x,y)

#XXX Issue 3. Should be removed
@cutype("(Bool,Bool) -> Bool")
def op_bor(x,y): return True if (x or y) else False

@cutype("(a,a) -> a")
@_wraps(_op.xor)
def op_xor(x,y): return _op.xor(x,y)

@cutype("(a,a) -> a")
@_wraps(_op.and_)
def op_and(x,y): return _op.and_(x,y)

#XXX Issue 3. Should be removed
@cutype("(Bool,Bool) -> Bool")
def op_band(x,y): return True if (x and y) else False

@cutype("a -> a")
@_wraps(_op.invert)
def op_invert(x): return _op.invert(x)

@cutype("a -> a")
@_wraps(_op.pos)
def op_pos(x): return _op.pos(x)

@cutype("a -> a")
@_wraps(_op.neg)
def op_neg(x): return _op.neg(x)

@cutype("Bool -> Bool")
@_wraps(_op.not_)
def op_not(x): return _op.not_(x)

@cutype("(a, a) -> Bool")
@_wraps(_op.eq)
def cmp_eq(x,y): return _op.eq(x,y)

@cutype("(a, a) -> Bool")
@_wraps(_op.ne)
def cmp_ne(x,y): return _op.ne(x,y)

@cutype("(a, a) -> Bool")
@_wraps(_op.lt)
def cmp_lt(x,y): return _op.lt(x,y)

@cutype("(a, a) -> Bool")
@_wraps(_op.le)
def cmp_le(x,y): return _op.le(x,y)

@cutype("(a, a) -> Bool")
@_wraps(_op.gt)
def cmp_gt(x,y): return _op.gt(x,y)

@cutype("(a, a) -> Bool")
@_wraps(_op.ge)
def cmp_ge(x,y): return _op.ge(x,y)

########################################################################
#
# Type casting functions
#

# Monomorphic casts
@cutype("a -> Int")
def int32(x):
    """Returns a 32-bit representation of the input.
    Only defined for basic scalar types."""
    return np.int32(x)

@cutype("a -> Long")
def int64(x):    
    """Returns a 64-bit representation of the input.
    Only defined for basic scalar types."""
    return np.int64(x)

@cutype("a -> Float")
def float32(x):
    """Returns a 32-bit floating point representation of the input.
    Only defined for basic scalar types."""
    return np.float32(x)

@cutype("a -> Double")
def float64(x):
    """Returns a 64-bit floating point representation of the input.
    Only defined for basic scalar types."""
    return np.float64(x)

# Polymorphic casts
@cutype("(a, b) -> b")
def cast_to(x, y):
    """Returns a representation of `x` in the same type as `y`.
    Only defined for basic scalar types."""
    return x

@cutype("(a, [b]) -> b")
def cast_to_el(x, y):
    """Returns a representation of `x` in the same type as
    an element of `y`. Only defined for `x` which is a basic scalar type,
    and `y` which is a sequence of basic scalar types."""
    return x


########################################################################
#
# Scalar functions
#

@cutype("a -> a")
def max_bound(x):
    """
    Returns maximum bound value for data of the same type as x.
    This is useful, for example, to make identities for comparisons.
    @param x Any scalar type. Value will be ignored.
    """
    if isinstance(x, np.float32) or isinstance(x, np.float64) or \
            isinstance(x, float):
        return np.finfo(x).max
    else:
        return np.iinfo(x).max

@cutype("a -> a")
def min_bound(x):
    """
    Returns minimum bound value for data of the same type as x.
    This is useful, for example, to make identities for comparisons.
    @param x Any scalar type. Value will be ignored.
    """
    if isinstance(x, np.float32) or isinstance(x, np.float64) or \
            isinstance(x, float):
        return np.finfo(x).min
    else:
        return np.iinfo(x).min

@cutype("[a] -> a")
def max_bound_el(x):
    """
    Returns maximum bound value for data of the same type as x.
    This is useful, for example, to make identities for comparisons.
    @param x Any scalar type. Value will be ignored.
    """
    y = x[0]
    if isinstance(y, np.float32) or isinstance(y, np.float64) or \
            isinstance(y, float):
        return np.finfo(y).max
    else:
        return np.iinfo(y).max

@cutype("[a] -> a")
def min_bound_el(x):
    """
    Returns minimum bound value for data of the same type as x.
    This is useful, for example, to make identities for comparisons.
    @param x Any scalar type. Value will be ignored.
    """
    y = x[0]
    if isinstance(x, np.float32) or isinstance(x, np.float64) or \
            isinstance(x, float):
        return np.finfo(x).min
    else:
        return np.iinfo(x).min




###########################################################################
# UNIMPLEMENTED FUNCTIONS
# These may be implemented in the future, but are not currently functional
###########################################################################

# @cutype("(a->k, [a]) -> [(k, [a])]")
# def collect(key_function, A):
#     """
#     Using the given function to assign keys to all elements of A, return
#     a list of (key, [values]) pairs such that all elements with
#     equivalent keys are gathered together in the same list.

#         >>> collect(lambda x:x, [1, 1, 2, 3, 1, 3, 2, 1])
#         [(1, [1, 1, 1, 1]), (2, [2, 2]), (3, [3, 3])]

#     The returned pairs will be ordered by increasing key values.  The
#     individual values will occur in the order in which they occur in the
#     original sequence.

#         >>> collect(lambda x: x<0, [1, -1, 4, 3, -5])
#         [(False, [1, 4, 3]), (True, [-1, -5])]
#     """
#     from itertools import groupby
#     B = list()

#     for key,values in groupby(sorted(A, key=key_function), key_function):
#         B.append((key,list(values)))

#     return B

# @cutype("((a,a)->a, [a], [b], [a]) -> [a]")
# def scatter_reduce(fn, src, indices, dst):
#     """
#     Alternate version of scatter that combines -- rather than replaces
#     -- values in dst with values from src.  The binary function fn is
#     used to combine values, and is required to be both associative and
#     commutative.
    
#     If multiple values in src are sent to the same location in dst,
#     those values will be combined together as in reduce.  The order in
#     which values are combined is undefined.

#         >>> scatter_reduce(op_add, [1,1,1], [1,2,3], [0,0,0,0,0])
#         [0, 1, 1, 1, 0]

#         >>> scatter_reduce(op_add, [1,1,1], [3,3,3], [0,0,0,0,0])
#         [0, 0, 0, 3, 0]
#     """
#     assert len(src)==len(indices)

#     result = list(dst)
#     for i in xrange(len(src)):
#         j = indices[i]
#         result[j] = fn(result[j], src[i])
#     return result

# @cutype("([a], [b], [a]) -> [a]")
# def scatter_sum(src, indices, dst):
#     """
#     Specialization of scatter_reduce for addition (cf. reduce and sum).
#     """
#     return scatter_reduce(op_add, src, indices, dst)

# @cutype("([a], [b], [a]) -> [a]")
# def scatter_min(src, indices, dst):
#     """
#     Specialization of scatter_reduce with the min operator (cf. reduce and min).
#     """
#     return scatter_reduce(op_min, src, indices, dst)

# @cutype("([a], [b], [a]) -> [a]")
# def scatter_max(src, indices, dst):
#     """
#     Specialization of scatter_reduce with the max operator (cf. reduce and max).
#     """
#     return scatter_reduce(op_max, src, indices, dst)

# @cutype("([Bool], [b], [Bool]) -> [Bool]")
# def scatter_any(src, indices, dst):
#     """
#     Specialization of scatter_reduce for logical or (cf. reduce and any).
#     """
#     return scatter_reduce(op_or, src, indices, dst)

# @cutype("([Bool], [b], [Bool]) -> [Bool]")
# def scatter_all(src, indices, dst):
#     """
#     Specialization of scatter_reduce for logical and (cf. reduce and all).
#     """
#     return scatter_reduce(op_and, src, indices, dst)

# @cutype("[[a]] -> [a]")
# def join(lists):
#     """
#     Return a list which is the concatenation of all elements of input list.

#     >>> join([[1,2], [3,4,5], [6,7]])
#     [1, 2, 3, 4, 5, 6, 7]
#     """
#     from operator import concat
#     return __builtin__.reduce(concat, lists)


# @cutype("[a] -> [a]")
# @_wraps(__builtin__.reversed)
# def reversed(sequence):
#     """
#     Return a sequence containing the elements of the input in reverse
#     order.

#         >>> reversed([3, 0, 1, 2])
#         [2, 1, 0, 3]
#     """
#     return list(__builtin__.reversed(sequence))

# @cutype("([a], Int) -> [[a]]")
# def split(A, tilesize):
#     """
#     Split the sequence A into a sequence of sub-sequences.  Every
#     sub-sequence will contain tilesize elements, except for the last
#     sub-sequence which may contain fewer.

#         >>> split(range(8), 3)
#         [[0, 1, 2], [3, 4, 5], [6, 7]]

#         >>> split([1,2,3,4], 1)
#         [[1], [2], [3], [4]]

#     If the tilesize is larger than the size of A, only one sub-sequence
#     will be returned.

#         >>> split([1,2], 3)
#         [[1, 2]]
#     """
#     tile = A[:tilesize]
#     if len(A) > tilesize:
#         return [tile] + split(A[tilesize:], tilesize)
#     else:
#         return [tile]

# @cutype("([a], Int) -> [[a]]")
# def splitr(A, tilesize):
#     """
#     Split the sequence A into a sequence of sub-sequences.  Every
#     sub-sequence will contain tilesize elements, except for the first
#     sub-sequence which may contain fewer.

#         >>> splitr(range(8), 3)
#         [[0, 1], [2, 3, 4], [5, 6, 7]]

#         >>> splitr([1,2,3,4], 1)
#         [[1], [2], [3], [4]]

#     If the tilesize is larger than the size of A, only one sub-sequence
#     will be returned.

#         >>> splitr([1,2], 3)
#         [[1, 2]]
#     """
#     tile = A[-tilesize:]
#     if len(A) > tilesize:
#         return splitr(A[:-tilesize], tilesize) + [tile]
#     else:
#         return [tile]

# @cutype("([a], Int) -> ([a], [a])")
# def split_at(A, k):
#     """
#     Return pair of sequences containing the k elements and the rest
#     of A, respectively.

#         >>> split_at([0,1,2,3,4,5,6,7], 3)
#         ([0, 1, 2], [3, 4, 5, 6, 7])

#     It is acceptable to specify values of k=0 or k=len(A).  In both
#     cases, one of the returned sequences will be empty.

#         >>> split_at(range(3), 0)
#         ([], [0, 1, 2])

#         >>> split_at(range(3), 3)
#         ([0, 1, 2], [])
#     """
#     return A[:k], A[k:]

# @cutype("([a], Int) -> [[a]]")
# def split_cyclic(A, k):
#     """
#     Splits the sequence A into k subsequences.  Elements of A are
#     distributed into subsequences in cyclic round-robin fashion.  Every
#     subsequence will contain ceil(A/k) elements, except for the last
#     which may contain fewer.

#         >>> split_cyclic(range(10), 3)
#         [[0, 3, 6, 9], [1, 4, 7], [2, 5, 8]]

#     If there are fewer than k elements in A, the last n-k subsequences
#     will be empty.

#         >>> split_cyclic([1, 2], 4)
#         [[1], [2], [], []]
#     """
#     return [A[i::k] for i in range(k)]

# @cutype("[[a]] -> [a]")
# def interleave(A):
#     """
#     The inverse of split_cyclic, this takes a collection of
#     subsequences and interleaves them to form a single sequence.

#         >>> interleave([[0, 3, 6, 9], [1, 4, 7], [2, 5, 8]])
#         [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

#         >>> interleave([[1], [2], [], []])
#         [1, 2]

#     The input sequence may contain only empty sequences, but may not
#     itself be empty.

#         >>> interleave([[],[]])
#         []

#         >>> interleave([])
#         Traceback (most recent call last):
#           ...
#         AssertionError
#     """
#     assert len(A)>0
#     return [x for items in map(None, *A) for x in items if x is not None]

# @cutype("[a] -> [a]")
# def odds(A):
#     """
#     Return list of all elements of A at odd-numbered indices.

#         >>> odds([1, 2, 3, 4, 5])
#         [2, 4]

#         >>> odds([1])
#         []
#     """
#     return A[1::2]

# @cutype("[a] -> [a]")
# def evens(A):
#     """
#     Return list of all elements of A at even-numbered indices.

#         >>> evens([1, 2, 3, 4, 5])
#         [1, 3, 5]

#         >>> evens([1])
#         [1]
#     """
#     return A[0::2]

# @cutype("([a], [a]) -> [a]")
# def interleave2(A, B):
#     """
#     Interleave the given lists element-wise, starting with A.

#         >>> interleave2([1,2,3], [4])
#         [1, 4, 2, 3]
#     """
#     return [x for items in map(None, A, B) for x in items if x is not None]

# @cutype("([a], Int) -> [a]")
# def take(a,i):
#     'Return sequence containing first i elements of a'
#     return a[:i]

# @cutype("([a], Int) -> [a]")
# def drop(a,i):
#     'Return sequence containing all but the first i elements of a'
#     return a[i:]

# @cutype("[a] -> a")
# def first(A):
#     'Return the first element of the sequence A.  Equivalent to A[0].'
#     return A[0]

# @cutype("[a] -> a")
# def second(A):
#     'Return the second element of A.  Equivalent to A[1].'
#     return A[1]

# @cutype("[a] -> a")
# def last(A):
#     'Return the last element of A.  Equivalent to A[-1].'
#     return A[-1]

# @cutype("[Bool] -> Int")
# def count(preds):
#     'Count the number of True values in preds'

#     # Python treats True like 1, but Copperhead does not
#     return sum(preds)

# @cutype("[(Bool, a)] -> [a]")
# def pack(A):
#     """
#     Given a sequence of (flag,value) pairs, pack will produce a sequence
#     containing only those values whose flag was True.  The relative
#     order of values in the input is preserved in the output.

#         >>> pack(zip([False, True, True, False], range(4)))
#         [1, 2]
#     """
#     def _gen(A):
#         for flag, value in A:
#             if flag:
#                 yield value

#     return list(_gen(A))

## @cond INTERNAL
# Implementations of variadic map, zip and unzip
# Necessary for type inference.

@cutype("((a0)->b, [a0])->[b]")
def map1(f, a0):
    return map(f, a0)

@cutype("((a0,a1)->b, [a0], [a1])->[b]")
def map2(f, a0, a1):
    return map(f, a0, a1)

@cutype("((a0,a1,a2)->b, [a0], [a1], [a2])->[b]")
def map3(f, a0, a1, a2):
    return map(f, a0, a1, a2)

@cutype("((a0,a1,a2,a3)->b, [a0], [a1], [a2], [a3])->[b]")
def map4(f, a0, a1, a2, a3):
    return map(f, a0, a1, a2, a3)

@cutype("((a0,a1,a2,a3,a4)->b, [a0], [a1], [a2], [a3], [a4])->[b]")
def map5(f, a0, a1, a2, a3, a4):
    return map(f, a0, a1, a2, a3, a4)

@cutype("((a0,a1,a2,a3,a4,a5)->b, [a0], [a1], [a2], [a3], [a4], [a5])->[b]")
def map6(f, a0, a1, a2, a3, a4, a5):
    return map(f, a0, a1, a2, a3, a4, a5)

@cutype("((a0,a1,a2,a3,a4,a5,a6)->b, [a0], [a1], [a2], [a3], [a4], [a5], [a6])->[b]")
def map7(f, a0, a1, a2, a3, a4, a5, a6):
    return map(f, a0, a1, a2, a3, a4, a5, a6)

@cutype("((a0,a1,a2,a3,a4,a5,a6,a7)->b, [a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7])->[b]")
def map8(f, a0, a1, a2, a3, a4, a5, a6, a7):
    return map(f, a0, a1, a2, a3, a4, a5, a6, a7)

@cutype("((a0,a1,a2,a3,a4,a5,a6,a7,a8)->b, [a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7], [a8])->[b]")
def map9(f, a0, a1, a2, a3, a4, a5, a6, a7, a8):
    return map(f, a0, a1, a2, a3, a4, a5, a6, a7, a8)

@cutype("((a0,a1,a2,a3,a4,a5,a6,a7,a8,a9)->b, [a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7], [a8], [a9])->[b]")
def map10(f, a0, a1, a2, a3, a4, a5, a6, a7, a8, a9):
    return map(f, a0, a1, a2, a3, a4, a5, a6, a7, a8, a9)

@cutype("([a0])->[(a0)]")
def zip1(a0):
    return zip(a0)

@cutype("([a0], [a1])->[(a0, a1)]")
def zip2(a0, a1):
    return zip(a0, a1)

@cutype("([a0], [a1], [a2])->[(a0, a1, a2)]")
def zip3(a0, a1, a2):
    return zip(a0, a1, a2)

@cutype("([a0], [a1], [a2], [a3])->[(a0, a1, a2, a3)]")
def zip4(a0, a1, a2, a3):
    return zip(a0, a1, a2, a3)

@cutype("([a0], [a1], [a2], [a3], [a4])->[(a0, a1, a2, a3, a4)]")
def zip5(a0, a1, a2, a3, a4):
    return zip(a0, a1, a2, a3, a4)

@cutype("([a0], [a1], [a2], [a3], [a4], [a5])->[(a0, a1, a2, a3, a4, a5)]")
def zip6(a0, a1, a2, a3, a4, a5):
    return zip(a0, a1, a2, a3, a4, a5)

@cutype("([a0], [a1], [a2], [a3], [a4], [a5], [a6])->[(a0, a1, a2, a3, a4, a5, a6)]")
def zip7(a0, a1, a2, a3, a4, a5, a6):
    return zip(a0, a1, a2, a3, a4, a5, a6)

@cutype("([a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7])->[(a0, a1, a2, a3, a4, a5, a6, a7)]")
def zip8(a0, a1, a2, a3, a4, a5, a6, a7):
    return zip(a0, a1, a2, a3, a4, a5, a6, a7)

@cutype("([a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7], [a8])->[(a0, a1, a2, a3, a4, a5, a6, a7, a8)]")
def zip9(a0, a1, a2, a3, a4, a5, a6, a7, a8):
    return zip(a0, a1, a2, a3, a4, a5, a6, a7, a8)

@cutype("([a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7], [a8], [a9])->[(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9)]")
def zip10(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9):
    return zip(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9)

@cutype("([(a0)])->([a0])")
def unzip1(a0):
    return unzip(a0)

@cutype("([(a0, a1)])->([a0], [a1])")
def unzip2(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2)])->([a0], [a1], [a2])")
def unzip3(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2, a3)])->([a0], [a1], [a2], [a3])")
def unzip4(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2, a3, a4)])->([a0], [a1], [a2], [a3], [a4])")
def unzip5(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2, a3, a4, a5)])->([a0], [a1], [a2], [a3], [a4], [a5])")
def unzip6(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2, a3, a4, a5, a6)])->([a0], [a1], [a2], [a3], [a4], [a5], [a6])")
def unzip7(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2, a3, a4, a5, a6, a7)])->([a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7])")
def unzip8(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2, a3, a4, a5, a6, a7, a8)])->([a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7], [a8])")
def unzip9(a0):
    return unzip(a0)

@cutype("([(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9)])->([a0], [a1], [a2], [a3], [a4], [a5], [a6], [a7], [a8], [a9])")
def unzip10(a0):
    return unzip(a0)

## @endcond

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = prelude_impl
#
#   Copyright 2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Copperhead Prelude

This module provides Copperhead implementations for non-primitive prelude
functions.
These implementations are not provided in the prelude proper, because doing so
would preclude the use of Python builtins for certain functions, like range,
which are built in to Python, but are implemented as Copperhead functions.

The compiler brings these in during the compilation process, otherwise
they will not override the Python builtins.
"""

from decorators import cu

@cu
def range(n):
    return indices(replicate(0, n))

@cu
def gather(x, i):
    def el(ii):
        return x[ii]
    return map(el, i)

@cu
def update(dst, updates):
    indices, src = unzip(updates)
    return scatter(src, indices, dst)

@cu
def any(preds):
    return reduce(op_or, preds, False)

@cu
def all(preds):
    return reduce(op_and, preds, True)

@cu
def sum(x):
    return reduce(op_add, x, cast_to_el(0, x))

@cu
def min(x):
    def min_el(a, b):
        if a < b:
            return a
        else:
            return b
    return reduce(min_el, x, x[0])

@cu
def max(x):
    def max_el(a, b):
        if a > b:
            return a
        else:
            return b
    return reduce(max_el, x, x[0])

@cu
def shift(x, a, d):
    def shift_el(i):
        i = i + a
        if i < 0 or i >= len(x):
            return d
        else:
            return x[i]
    return map(shift_el, indices(x))

@cu
def rotate(x, a):
    def torus_index(i, a, b):
        return (i + a) % b
        
    def rotate_el(i):
        return x[torus_index(i, a, len(x))]

    return map(rotate_el, indices(x))

@cu
def bounded_range(a, b):
    length = b - a
    return [xi + a for xi in range(length)]

@cu
def enumerate(x):
    return zip(range(len(x)), x)

########NEW FILE########
__FILENAME__ = cufunction
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

from __future__ import with_statement     # make with visible in Python 2.5
from __future__ import absolute_import

import inspect
import tempfile
import os.path
from .. import compiler
from . import places
import fnmatch
import os
import pickle

class CuFunction:

    def __init__(self, fn):
        self.fn = fn
        self.__doc__ = fn.__doc__
        self.__name__ = fn.__name__

        # Copy attributes that may have been set by Copperhead decorators.
        self.cu_type  = getattr(fn, 'cu_type', None)
        self.cu_shape = getattr(fn, 'cu_shape', None)
        self.cu_phase = getattr(fn, 'cu_phase', None)

        # Type inference is deferred until the first __call__
        # invocation.  This avoids the need for procedures to be defined
        # textually before they are called.
        self.inferred_type = None

        # Parse and cache the Copperhead AST for this function
        stmts = compiler.pyast.statement_from_text(self.get_source())
        self.syntax_tree = stmts
        # Establish code directory
        self.code_dir = self.get_code_dir()
        self.cache = self.get_cache()
        self.code = {}
        
    def __call__(self, *args, **kwargs):
        P = kwargs.pop('target_place', places.default_place)
        return P.execute(self, args, kwargs)

    def get_source(self):
        """
        Return a string containing the source code for the wrapped function.

        NOTE: This will only work if the function was defined in a file.
        We have no access to the source of functions defined at the
        interpreter prompt.
        """
        return inspect.getsource(self.fn)

    def get_globals(self):
        """
        Return the global namespace in which the function was defined.
        """
        return self.fn.func_globals

    def get_ast(self):
        """
        Return the cached Copperhead AST.
        """
        return self.syntax_tree

    def python_function(self):
        """
        Return the underlying Python function object for this procedure.
        """
        return self.fn

    def infer_type(self):
        """
        Every Copperhead function must have a valid static type.  This
        method infers the most general type for the wrapped function.
        It will raise an exception if the function is not well-typed.
        """
        typer = compiler.typeinference.TypingContext(globals=self.get_globals())

        compiler.typeinference.infer(self.syntax_tree, context=typer)
        self.inferred_type = self.syntax_tree[0].name().type

        # XXX TODO: Should unify inferred_type with cu_type, if any
        if not self.cu_type:
            self.cu_type = self.inferred_type

        return self.inferred_type

    def get_code(self):
        return self.code

    def get_code_dir(self):
        #Rationale for the default code directory location:
        # PEP 3147
        # http://www.python.org/dev/peps/pep-3147/
        #
        # Which standardizes the __pycache__ directory as a place to put
        # compilation artifacts for python programs
        source_dir, source_file = os.path.split(inspect.getsourcefile(self.fn))
        candidate = os.path.join(source_dir, '__pycache__', source_file, self.__name__)
        
        if os.path.exists(candidate):
            return candidate
        try:
            os.makedirs(candidate)
            return candidate
        except OSError:
            #Fallback!
            #Can't create a directory where the source file lives
            #(Maybe the source file is in a system directory)
            #Let's put it in a tempdir which we know will be writable
            candidate = os.path.join(tempfile.gettempdir(),
                                     'copperhead-cache-uid%s' % os.getuid(),
                                     source_file, self.__name__)
            if os.path.exists(candidate):
                return candidate
            #No check here to ensure this succeeds - fatal error if it fails
            os.makedirs(candidate)    
            return candidate

    def get_cache(self):
        #XXX Can't we get rid of this circular dependency?
        from . import toolchains
        cache = {}
        cuinfos = []
        for r, d, f in os.walk(self.code_dir):
            for filename in fnmatch.filter(f, 'cuinfo'):
                cuinfos.append(os.path.join(r, filename))
            
        for cuinfo in cuinfos:
            cuinfo_file = open(cuinfo, 'r')
            input_name, input_type, tag = pickle.load(cuinfo_file)
            cuinfo_file.close()

            if input_name == self.__name__:
                try:
                    input_types = {}
                    input_types[input_name] = input_type
                    
                    code, compiled_fn = \
                        compiler.passes.compile(self.get_ast(),
                                                globals = self.get_globals(),
                                                input_types=input_types,
                                                tag=tag,
                                                code_dir=self.code_dir,
                                                toolchains=toolchains,
                                                compile=False)
                    signature = ','.join([str(tag)]+[str(x) for x in input_type])
                    cache[signature] = compiled_fn

                except:
                    # We don't process exceptions at this point
                    pass
            
        return cache

########NEW FILE########
__FILENAME__ = driver
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
import numpy as np
from copperhead.compiler import passes, conversions, coretypes

import places
import tags

from . import cuda_support, omp_support, tbb_support

class Sequential(places.Place):
    def __str__(self):
        return "Sequential"
    def __repr__(self):
        return str(self)
    def tag(self):
        return tags.cpp
    def execute(self, cufn, args, kwargs):
        return execute(self.tag(), cufn, *args, **kwargs)

if cuda_support:
    class Cuda(places.Place):
        def __str__(self):
            return "Cuda"
        def __repr__(self):
            return str(self)
        def tag(self):
            return tags.cuda

    class DefaultCuda(Cuda):
        def execute(self, cufn, args, kwargs):
            return execute(self.tag(), cufn, *args, **kwargs)
if omp_support:
    class OpenMP(places.Place):
        def __str__(self):
            return "OpenMP"
        def __repr__(self):
            return str(self)
        def tag(self):
            return tags.omp
        def execute(self, cufn, args, kwargs):
            return execute(self.tag(), cufn, *args, **kwargs)

if tbb_support:
    class TBB(places.Place):
        def __str__(self):
            return "TBB"
        def __repr__(self):
            return str(self)
        def tag(self):
            return tags.tbb
        def execute(self, cufn, args, kwargs):
            return execute(self.tag(), cufn, *args, **kwargs)
    
def induct(x):
    from . import cudata
    """Compute Copperhead type of an input, also convert data structure"""
    if isinstance(x, cudata.cuarray):
        return (conversions.back_to_front_type(x.type), x)
    if isinstance(x, np.ndarray):
        induced = cudata.cuarray(x)
        return (conversions.back_to_front_type(induced.type), induced)
    if isinstance(x, np.float32):
        return (coretypes.Float, x)
    if isinstance(x, np.float64):
        return (coretypes.Double, x)
    if isinstance(x, np.int32):
        return (coretypes.Int, x)
    if isinstance(x, np.int64):
        return (coretypes.Long, x)
    if isinstance(x, np.bool):
        return (coretypes.Bool, x)
    if isinstance(x, list):
        induced = cudata.cuarray(np.array(x))
        return (conversions.back_to_front_type(induced.type), induced)
    if isinstance(x, float):
        #Treat Python floats as double precision
        return (coretypes.Double, np.float64(x))
    if isinstance(x, int):
        #Treat Python ints as 64-bit ints (following numpy)
        return (coretypes.Long, np.int64(x))
    if isinstance(x, bool):
        return (coretypes.Bool, np.bool(x))
    if isinstance(x, tuple):
        sub_types, sub_elements = zip(*(induct(y) for y in x))
        return (coretypes.Tuple(*sub_types), tuple(sub_elements))
    #Can't digest this input
    raise ValueError("This input is not convertible to a Copperhead data structure: %r" % x)
    
def execute(tag, cufn, *v, **k):
    """Call Copperhead function. Invokes compilation if necessary"""

    if len(v) == 0:
        #Functions which take no arguments
        cu_types, cu_inputs = ((),())
    else:
        cu_types, cu_inputs = zip(*map(induct, v))
    #Derive unique hash for function based on inputs and target place
    signature = ','.join([str(tag)]+[str(x) for x in cu_types])
    #Have we executed this function before, in which case it is loaded in cache?
    if signature in cufn.cache:
        return cufn.cache[signature](*cu_inputs)

    #XXX can't we get rid of this circular dependency?
    from . import toolchains
    #Compile function
    ast = cufn.get_ast()
    name = ast[0].name().id
    code, compiled_fn = \
                 passes.compile(ast,
                                globals=cufn.get_globals(),
                                input_types={name : cu_types},
                                tag=tag,
                                code_dir=cufn.code_dir,
                                toolchains=toolchains,
                                **k)
    #Store the binary and the compilation result
    cufn.cache[signature] = compiled_fn
    #Call the function
    return compiled_fn(*cu_inputs)

########NEW FILE########
__FILENAME__ = intermediate
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Support execution of intermediate forms generated in the compiler.
"""

from __future__ import absolute_import

import sys

from . import places
from ..compiler import passes, coretypes as T
from .. import prelude, interlude


def _typeof(x):
    """
    Compute the appropriate Copperhead type for a given Python object.
    This is a quick little procedure to suit the needs of these
    intermediate execution places.  It should really be replaced by
    suitable functionality elsewhere in the compiler/runtime.
    """
    if isinstance(x, int):
        return T.Int
    elif isinstance(x, float):
        return T.Float
    elif isinstance(x, tuple):
        return T.Tuple( *[_typeof(y) for y in x] )
    elif isinstance(x, list):
        return T.Seq(_typeof(x[0]))
    else:
        return ValueError, "%s has no Copperhead type" % x

class Intermediate(places.PythonInterpreter):
    """
    Intermediate places compile code through a portion of the Copperhead
    compilation pipeline and then execute the results in the native
    Python interpreter.
    """

    def __init__(self, target):
        self.compilation_target = target

    def execute(self, cufn, args, kwargs):

        name = cufn.__name__
        text = passes.compile(cufn.get_source(),
                              globals=cufn.get_globals(),
                              target=self.compilation_target,
                              inputTypes={name : map(_typeof, args)})

        bindings = dict(cufn.get_globals())
        bindings.update(interlude.__dict__)

        try:
            exec text in bindings

            fn2 = bindings[name]
            bindings['__entry__'] = lambda: fn2(*args)
            result = eval('__entry__()',  bindings)
        except:
            print
            print "ERROR IN INTERMEDIATE CODE:", sys.exc_value
            print text
            print
            raise

        return result

places.frontend = Intermediate(passes.frontend)

import pdb
def print_and_pause(name, ast, M):
    print
    print "after", name, ":"
    if isinstance(ast, list):
        code = passes.ast_to_string(ast)
        print passes.S._indent(code)
    else:
        print str(ast)
    pdb.set_trace()

def print_repr(name, ast, M):
    print "after", name, ":"
    print repr(ast)

class tracing(object):
    """
    Tracing objects are context managers for Python 'with' statements.
    They are a debugging tool that allows top-level code to capture a
    program in various stages of the compiler pipeline.  The default
    action taken is to simply print the source code.

    This facility is only meant for use by those familiar with the
    compiler internals.  It is unlikely to ever be useful for others.

    For example, to print the result of every Copperhead function at the
    end of the front-end compiler, simply do this:

        with tracing(parts=[passes.frontend], including=['END frontend']):
            # invoked Copperhead functions here
    """

    def __init__(self, action=None,
                       parts=[passes.frontend],
                       including=None,
                       excluding=[]):

        self.action = action
        self.parts = parts
        self.including = including
        self.excluding = excluding

        self._saved = []

    def send(self, data):
        name, ast, M = data
        if (name not in self.excluding) and \
                (not self.including or name in self.including):

            if self.action is None:
                print
                print "after", name, ":"

                code = passes.ast_to_string(ast)
                print passes.S._indent(code)
            else:
                self.action(name, ast, M)

    def __enter__(self):
        self._saved = [part.capture for part in self.parts]
        for part in self.parts:
            part.capture = self

    def __exit__(self, *args):
        for part, old in zip(self.parts, self._saved):
            part.capture = old

########NEW FILE########
__FILENAME__ = np_interop
import numpy as np
import copperhead.compiler.backendtypes as ET
import copperhead.compiler.coretypes as T
from copperhead.compiler.conversions import back_to_front_type


def to_numpy(ary):
    front_type = back_to_front_type(ary.type)
    if not isinstance(front_type, T.Seq):
        raise ValueError("Not convertible to numpy")
    sub = front_type.unbox()
    if str(sub) == str(T.Int):
        return np.fromiter(ary, dtype=np.int32, count=-1)
    elif str(sub) == str(T.Long):
        return np.fromiter(ary, dtype=np.int64, count=-1)
    elif str(sub) == str(T.Float):
        return np.fromiter(ary, dtype=np.float32, count=-1)
    elif str(sub) == str(T.Double):
        return np.fromiter(ary, dtype=np.float64, count=-1)
    elif str(sub) == str(T.Bool):
        return np.fromiter(ary, dtype=np.bool, count=-1)
    else:
        raise ValueError("Not convertible to numpy")
    

########NEW FILE########
__FILENAME__ = null_toolchain
import copy

class SelectiveUnimplementer(object):
    def __init__(self, base, deletions):
        self._base = base
        self._deletions = deletions
    def unimplemented(self, *args, **kwargs):
        raise NotImplementedError
    def __getattr__(self, name):
        if name not in self._deletions:
            return getattr(self._base, name)
        else:
            return self.unimplemented
    def copy(self):
        return SelectiveUnimplementer(
            copy.deepcopy(self._base), self._deletions)
        
def make_null_toolchain(toolchain):
    """Creates a codepy toolchain which behaves identically to a given
    toolchain, but cannot actually compile code.  This allows us to
    check whether a binary has already been compiled, without paying
    the cost of compiling one if it has not been compiled."""
    
    return SelectiveUnimplementer(toolchain,
                                  set(["build_extension",
                                       "build_object",
                                       "link_extension"]))

########NEW FILE########
__FILENAME__ = places
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

import numpy as np

class Place(object):

    def __init__(self):
        self._previous = None

    def __enter__(self):
        global default_place
        self._previous = default_place
        default_place = self

    def __exit__(self, *args):
        global default_place
        if self._previous:
            default_place = self._previous
            self._previous = None


class PythonInterpreter(Place):

    def __init__(self): pass

    def new_copy(self, x):
        assert isinstance(x, np.ndarray)
        return np.array(x)

    def execute(self, cufn, args, kwargs):
        fn = cufn.python_function()
        return fn(*args, **kwargs)

here = PythonInterpreter()

default_place = here

########NEW FILE########
__FILENAME__ = utility
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
import cufunction


import pdb
import sys, os, os.path, shutil

def print_code(code, dest_path, name, ext):
    o_file = open(os.path.join(dest_path, name + ext), 'w')
    print >>o_file, code
    o_file.close()

def mkdir(dirname):
    exists = os.access(dirname, os.F_OK)
    if not exists:
        os.mkdir(dirname)

def save_code(objects, source_file=None):
    if source_file:
        dirname, ext = os.path.splitext(source_file)
        mkdir(dirname)
        shutil.copy(source_file, dirname)
    else:
        dirname = '.'
    for name, v in objects.items():
        if isinstance(v, cufunction.CuFunction):
            code = v.get_code()
            #There may be many variants, let's just grab the first
            implementations = code.values()
            if len(implementations) > 0:
                selected_impl = implementations[0]
                extensions = ('.py', '.cpp', '.cu')
                #make target directory
                dest_path = os.path.join(dirname, name)
                mkdir(dest_path)
                map(lambda x, y: print_code(x, dest_path, name, y),
                    selected_impl,
                    extensions)
            
         

########NEW FILE########
__FILENAME__ = axpy
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

from copperhead import *
import numpy as np

@cu
def nrm2(x, y):
    def diff_sq(xi, yi):
        diff = xi - yi
        return diff * diff
    return sqrt(sum(map(diff_sq, x, y)))

@cu
def axpy(a, x, y):
    def triad(xi, yi):
        return a * xi + yi
    return map(triad, x, y)


def test_saxpy(length):
    x = np.arange(0, length, dtype=np.float32)
    y = np.arange(1, length + 1, dtype=np.float32)
    a = np.float32(0.5)
    with places.gpu0:
        print("Compiling and Running on GPU")
        z = axpy(a, x, y)

    #Run on Python interpreter
    with places.here:
        print("Running in Python interpreter")
        zPython = axpy(a, x, y)
        
    print("Calculating difference")
    with places.gpu0:
        error = nrm2(z, zPython)
    
    return (x, y, z, zPython, error)

if __name__ == '__main__':
    length = 1000000

    (x, y, z, zPython, error) = test_saxpy(length)

    print('Error: %s' % str(error))
   

   

########NEW FILE########
__FILENAME__ = benchmark
from copperhead import *
import numpy as np
import timeit

@cu
def ident(x):
    def ident_e(xi):
        return xi
    return map(ident_e, x)

iters = 1000
s = 10000000
t = np.float32
a = np.ndarray(shape=(s,), dtype=t)
b = cuarray(a)
p = runtime.places.gpu0

#Optional: Send data to execution place
b = force(b, p)


def test_ident():
    for x in xrange(iters):
        r = ident(b)
    # Materialize result
    # If you don't do this, you won't time the actual execution
    # But rather the asynchronous function calls
    force(r, p)

 
with p:
    time = timeit.timeit('test_ident()', setup='from __main__ import test_ident', number=1)

bandwidth = (2.0 * 4.0 * s * float(iters))/time/1.0e9
print('Sustained bandwidth: %s GB/s' % bandwidth)

########NEW FILE########
__FILENAME__ = black_scholes
from copperhead import *
import numpy as np

@cu
def cnd(d):
    A1 = 0.31938153
    A2 = -0.356563782
    A3 = 1.781477937
    A4 = -1.821255978
    A5 = 1.330274429
    RSQRT2PI = 0.39894228040143267793994605993438

    K = 1.0 / (1.0 + 0.2316419 * abs(d))

    cnd = RSQRT2PI * exp(- 0.5 * d * d) * \
        (K * (A1 + K * (A2 + K * (A3 + K * (A4 + K * A5)))))

    if d > 0:
        return 1.0 - cnd
    else:
        return cnd


@cu
def black_scholes(S, X, T, R, V):
    def black_scholes_el(si, xi, ti):
        sqrt_ti = sqrt(ti)
        d1 = (log(si/xi) + (R + .5 * V * V) * ti) / (V * sqrt_ti)
        d2 = d1 - V * sqrt_ti
        cnd_d1 = cnd(d1)
        cnd_d2 = cnd(d2)
        exp_Rti = exp(-R * ti)
        call_result = si * cnd_d1 - xi * exp_Rti * cnd_d2;
        put_result = xi * exp_Rti * (1.0 - cnd_d2) - si * (1.0 - cnd_d1)
        return call_result, put_result
    return map(black_scholes_el, S, X, T)

def rand_floats(n, min, max):
    diff = np.float32(max) - np.float32(min)
    rands = np.array(np.random.random(n), dtype=np.float32)
    rands = rands * diff
    rands = rands + np.float32(min)
    return cuarray(rands)


n = 100


S = rand_floats(n, 5, 30)
X = rand_floats(n, 1, 100)
T = rand_floats(n, .25, 10)
R = np.float32(.02)
V = np.float32(.3)

r = black_scholes(S, X, T, R, V)


########NEW FILE########
__FILENAME__ = extrema
from copperhead import *
import numpy as np

@cu
def extrema_op(a, b):
    a_min_idx, a_min_val, a_max_idx, a_max_val = a
    b_min_idx, b_min_val, b_max_idx, b_max_val = b
    if a_min_val < b_min_val:
        if a_max_val > b_max_val:
            return a
        else:
            return a_min_idx, a_min_val, b_max_idx, b_max_val
    else:
        if a_max_val > b_max_val:
            return b_min_idx, b_min_val, a_max_idx, a_max_val
        else:
            return b

@cu
def extrema_id(x):
    return -1, max_bound(x), 1, min_bound(x)

@cu
def extrema(x, x_id):
    return reduce(extrema_op, zip(indices(x), x, indices(x), x), x_id)

n = 1e7
a = np.array(np.random.ranf(n), dtype=np.float32)
b = cuarray(a)

b_id = extrema_id(np.float32(0))
x = extrema(b, b_id)
print(x)

########NEW FILE########
__FILENAME__ = fibonacci
#
#   Copyright 2008-2009 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 

"""
Computing Fibonacci numbers with scan.

The Fibonacci numbers F_i obey the recurrence equation

    [ F_n+1 ]  =  [1  1] [ F_n   ]
    [ F_n   ]     [1  0] [ F_n-1 ]

or equivalently

    [ F_n+1 ]  =  [1  1]^n [ F_1 ]
    [ F_n   ]     [1  0]   [ F_0 ]

This implies that we can compute the Fibonacci sequence using parallel
prefix (a.k.a. scan) operations.  We need only initialize a sequence
of 2x2 matrices to A = replicate([[1 1] [1 0]], n) and then compute
scan(*,A) where '*' is the usual matrix multiplication operator.
"""

from copperhead import *

@cu
def vdot2(x, y):
    'Compute dot product of two 2-vectors.'
    x0, x1 = x
    y0, y1 = y
    return x0*y0 + x1*y1

@cu
def rows(A):
    'Return the 2 rows of the symmetric matrix A.'
    a0, a1, a2 = A
    return ((a0,a1), (a1,a2))

#@cutype("((a,a,a),) -> a")
@cu
def offdiag(A):
    'Return the off-diagonal element of the symmetric matrix A.'
    a0, a1, a2 = A
    return a1

#@cutype("( (a,a,a), (a,a,a) ) -> (a,a,a)")
@cu
def mul2x2(A, B):
    'Multiply two symmetric 2x2 matrices A and B represented as 3-tuples.'

    # rows of A
    a0, a1 = rows(A)

    # columns of B (which are its rows due to symmetry)
    b_0, b_1 = rows(B)

    return (vdot2(a0, b_0),
            vdot2(a0, b_1),
            vdot2(a1, b_1))

@cu
def fib(n):
    'Return a sequence containing the first n Fibonacci numbers.'

    # A is the symmetric matrix [[1 1], [1 0]] stored in a compressed
    # 3-tuple form.
    A = (1, 1, 0)

    # Calculate Fibonacci numbers by scan over the sequence [A]*n.
    F = scan(mul2x2, replicate(A, n))
    return map(offdiag, F)

print fib(92)

########NEW FILE########
__FILENAME__ = laplace
from copperhead import *
from numpy import zeros

@cu
def initialize(N):
    nx, ny = N
    def el(i):
        y = i / nx
        if y==0:
            return 1.0
        else:
            return 0.0
    return map(el, range(nx * ny))

@cu
def solve(u, N, D2, it):
    nx, ny = N
    dx2, dy2 = D2
    
    def el(i):
        x = i % nx
        y = i / nx
        if x == 0 or x == nx-1 or y == 0 or y == ny-1:
            return u[i]
        else:
            return ((u[i-1]+u[i+1])*dy2 + \
                        (u[i-nx]+u[i+nx])*dx2)/(2*(dx2+dy2))
        
            
    if it > 0:
        u = map(el, indices(u))
        return solve(u, N, D2, it-1)
    else:
        return u
    
dx = 0.1
dy = 0.1
dx2 = dx*dx
dy2 = dy*dy
N = (100,100)
D2 = (dx2, dy2)

p = runtime.places.default_place

with p:
    u = initialize(N)
    print("starting timer")
    import time
    start = time.time()
    #Solve
    u = solve(u, N, D2, 8000)
    #Force result to be finalized at execution place
    #Otherwise, timing loop may not account for all computation
    u = force(u, p)
    end = time.time()
    print("Computation time: %s seconds" %(end - start))

result = np.reshape(to_numpy(u), N)

try:
    import matplotlib.pyplot as plt
    plt.imshow(result)
    plt.show()
except:
    pass

########NEW FILE########
__FILENAME__ = mandelbrot
from copperhead import *

@cu
def z_square(z):
    real, imag = z
    return real * real - imag * imag, 2 * real * imag

@cu
def z_magnitude(z):
    real, imag = z
    return sqrt(real * real + imag * imag)

@cu
def z_add((z0r, z0i), (z1r, z1i)):
    return z0r + z1r, z0i + z1i

@cu
def mandelbrot_iteration(z0, z, i, m, t):
    z = z_add(z_square(z), z0)
    escaped = z_magnitude(z) > m
    converged = i > t
    done = escaped or converged
    if not done:
        return mandelbrot_iteration(z0, z, i+1, m, t)
    else:
        return i


@cu
def mandelbrot(lb, scale, (x, y), m, t):

    def mandelbrot_el(zi):
        return mandelbrot_iteration(zi, zi, 0, m, t)

    def index(i):
        scale_x, scale_y = scale
        lb_x, lb_y = lb
        return float32(i % x) * scale_x + lb_x, float32(i / x) * scale_y + lb_y

    
    two_d_points = map(index, range(x*y))

    return map(mandelbrot_el, two_d_points)
    


lb = (np.float32(-2.5), np.float32(-2.0))
ub = (np.float32(1.5), np.float32(2.0))
x, y = 1000, 1000

scale = ((ub[0]-lb[0])/np.float32(x), (ub[0]-lb[0])/np.float32(y))

max_iterations = 100
diverge_threshold = np.float32(4.0)

print("Calculating...")
result = mandelbrot(lb, scale, (x,y), diverge_threshold, max_iterations)
print("Plotting...")

import matplotlib.pyplot as plt
im_result = to_numpy(result).reshape([x, y])
plt.imshow(im_result)
plt.show()

########NEW FILE########
__FILENAME__ = of_cg
#
#  Copyright 2008-2010 NVIDIA Corporation
#  Copyright 2009-2010 University of California
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from copperhead import *

import numpy as np
import matplotlib as mat
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import plac
import urllib

@cu
def axpy(a, x, y):
    return [a * xi + yi for xi, yi in zip(x, y)]

@cu
def dot(x, y):
    return sum(map(op_mul, x, y))

@cu
def vadd(x, y):
    return map(op_add, x, y)

@cu
def vmul(x, y):
    return map(op_mul, x, y)

@cu
def vsub(x, y):
    return map(op_sub, x, y)


@cu
def of_spmv((du, dv), width, (m1, m2, m3, m4, m5, m6, m7)):
    e = vadd(vmul(m1, du), vmul(m2, dv))
    f = vadd(vmul(m2, du), vmul(m3, dv))
    e = vadd(e, vmul(m4, shift(du, -width, float32(0.0))))
    f = vadd(f, vmul(m4, shift(dv, -width, float32(0.0))))
    e = vadd(e, vmul(m5, shift(du, -1, float32(0.0))))
    f = vadd(f, vmul(m5, shift(dv, -1, float32(0.0))))
    e = vadd(e, vmul(m6, shift(du, 1, float32(0.0))))
    f = vadd(f, vmul(m6, shift(dv, 1, float32(0.0))))
    e = vadd(e, vmul(m7, shift(du, width, float32(0.0))))
    f = vadd(f, vmul(m7, shift(dv, width, float32(0.0))))
    return (e, f)

@cu
def zeros(x):
    return [float32(0.0) for xi in x]

eps = 1e-6

@cu
def init_cg(V, D, width, A):
    u, v = of_spmv(V, width, A)
    du, dv = D
    ur = vsub(du, u)
    vr = vsub(dv, v)
    return ur, vr

@cu
def precondition(u, v, (p1, p2, p3)):
    e = vadd(vmul(p1, u), vmul(p2, v))
    f = vadd(vmul(p2, u), vmul(p3, v))
    return e, f

@cu
def pre_cg_iteration(width, V, R, D, Z, A, P):
    ux, vx = V
    ur, vr = R
    uz, vz = Z
    ud, vd = D
    uAdi, vAdi = of_spmv(D, width, A)
    urnorm = dot(ur, uz)
    vrnorm = dot(vr, vz)
    rnorm = urnorm + vrnorm
    udtAdi = dot(ud, uAdi)
    vdtAdi = dot(vd, vAdi)
    dtAdi = udtAdi + vdtAdi
    alpha = rnorm / dtAdi
    ux = axpy(alpha, ud, ux)
    vx = axpy(alpha, vd, vx)
    urp1 = axpy(-alpha, uAdi, ur)
    vrp1 = axpy(-alpha, vAdi, vr)
    uzp1, vzp1 = precondition(urp1, vrp1, P)
    urp1norm = dot(urp1, uzp1)
    vrp1norm = dot(vrp1, vzp1)
    beta = (urp1norm + vrp1norm)/rnorm
    udp1 = axpy(beta, uzp1, urp1)
    vdp1 = axpy(beta, vzp1, vrp1)
    return (ux, vx), (urp1, vrp1), (udp1, vdp1), (uzp1, vzp1), rnorm



@cu
def form_preconditioner(m1, m2, m3):
    def indet(a, b, c):
        return 1.0/(a * c - b * b)
    indets = map(indet, m1, m2, m3)
    
    p1 = map(op_mul, indets, m3)
    p2 = map(lambda a, b: -a * b, indets, m2)
    p3 = map(op_mul, indets, m1)
    return p1, p2, p3


@cu
def pre_cg_solver(it, width, V, R, D, Z, A, P):
    if (it > 0):
        V, R, D, Z, rnorm = \
            pre_cg_iteration(width, V, R, D, Z, A, P)
        return pre_cg_solver(it-1, width, V, R, D, Z, A, P)
    else:
        return V

def cg(it, A, width, V, D):
    print("Solving...")
    m1, m2, m3, m4, m5, m6, m7 = A
    P = form_preconditioner(m1, m2, m3)
    R = init_cg(V, D, width, A)
    ur, vr = R
    Z = precondition(ur, vr, P)

    D = R

    return pre_cg_solver(it, width, V, R, D, Z, A, P)
    

def initialize_data(file_name):
    print("Reading data from file")
    if not file_name:
        file_name, headers = urllib.urlretrieve('http://copperhead.github.com/data/Urban331.npz')
    npz = np.load(file_name)
    width = npz['width'].item()
    height = npz['height'].item()
    npixels = width * height
    m1 = cuarray(npz['m1'])
    m2 = cuarray(npz['m2'])
    m3 = cuarray(npz['m3'])
    m4 = cuarray(npz['m4'])
    m5 = cuarray(npz['m5'])
    m6 = cuarray(npz['m6'])
    m7 = cuarray(npz['m7'])
    A = (m1, m2, m3, m4, m5, m6, m7)

    du = cuarray(npz['du'])
    dv = cuarray(npz['dv'])

    D = (du, dv)

    
    ux = cuarray(np.zeros(npixels, dtype=np.float32))
    vx = cuarray(np.zeros(npixels, dtype=np.float32))

    V = (ux, vx)
    
    img = npz['img']
    
    return(A, V, D, width, height, img)

def plot_data(image, width, height, V):
    plt.subplot(121)
    plt.imshow(image[10:110, 10:110])
    plt.subplot(122)

    ux, vx = V
    
    u = to_numpy(ux)
    v = to_numpy(vx)
    u = np.reshape(u, [height,width])
    v = np.reshape(v, [height,width])
    x, y = np.meshgrid(np.arange(0, 100), np.arange(99, -1, -1))

    plt.quiver(x, y, u[10:110,10:110], v[10:110, 10:110], angles='xy')
    plt.show()

@plac.annotations(data_file="""Filename of Numpy data file for this problem.
If none is found, a default dataset will be loaded from
http://copperhead.github.com/data/Urban331.npz""")
def main(data_file=None):
    """Performs a Preconditioned Conjugate Gradient solver for a particular
    problem found in Variational Optical Flow methods for video analysis."""
    A, V, D, width, height, image = initialize_data(data_file)
    
    VX = cg(100, A, width, V, D)

    plot_data(image, width, height, VX)



if __name__ == '__main__':
    plac.call(main)


########NEW FILE########
__FILENAME__ = p14
from copperhead import *


@cu
def enumerate(x):
    return zip(indices(x), x)

@cu
def argmax(x):
    def argmax_el((ia, xa), (ib, xb)):
        if xa > xb:
            return ia, xa
        else:
            return ib, xb
    return reduce(argmax_el, enumerate(x), (-1, min_bound_el(x)))

@cu
def choose(x):
    if x % 2 == 0:
        return x / 2
    else:
        return 3 * x + 1


@cu
def evaluate(x, i):
    if x == 1:
        return i
    else:
        return evaluate(choose(x), i + 1)

@cu
def start(x):
    return evaluate(x, 1)

@cu
def p14(n):
    lengths = map(start, bounded_range(1, n))
    index, value = argmax(lengths)
    return index+1, value


print p14(1000000, verbose=True)

########NEW FILE########
__FILENAME__ = radix_sort
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

from copperhead import *
import numpy as np
import plac

@cu
def radix_sort(A, bits, lsb):
    """
    Sort A using radix sort.
    
    Each element of A is assumed to be an integer.  The key used in
    sorting will be bits [lsb, lsb+bits).  For the general case, use
    bits=32 and lsb=0 to sort on all 32 bits.

    For sequences of length n with b-bit keys, this performs O(b*n) work.
    """

    def delta(flag, ones_before, zeros_after):
        if flag==0:  return -ones_before
        else:        return +zeros_after

    if lsb >= bits:
        return A
    else:
        flags = map(lambda x: int64((x>>lsb)&1), A)
        ones  = scan(op_add, flags)
        zeros = rscan(op_add, [f^1 for f in flags])
    
        offsets = map(delta, flags, ones, zeros)
        
        bit_sorted = permute(A, map(op_add, indices(A), offsets))

        return radix_sort(bit_sorted, bits, lsb+1)

    
def radix_sort8(A):   return radix_sort(A, np.int32(8), np.int32(0))
def radix_sort32(A):  return radix_sort(A, np.int32(32), np.int32(0))

@plac.annotations(n="Length of array to test sort with, defaults to 277")
def main(n=277):
    """Tests Copperhead radix sort in Python interpreter and on GPU."""
    def random_numbers(n, bits=8):
        import random
        return [np.int32(random.getrandbits(bits)) for i in xrange(n)]

    def test_sort(S, n=277, trials=50, bits=8):
        npass, nfail = 0,0
        name = S.__name__

        for i in xrange(trials):
            data_in  = random_numbers(n, bits)
            gold     = sorted(data_in)
            data_out = S(data_in)
            if list(gold) == list(data_out):
                npass = npass+1
            else:
                nfail = nfail+1

            print ("%-20s passed [%2d]\tfailed [%2d]\r" % (name, npass,nfail)),
        print

    print
    
    print "---- Checking Python implementations (n=277) ----"
    with places.here:
        test_sort(radix_sort8,    n=277)
   

    print "---- Checking GPU results (n=277) ----"
    with places.gpu0:
        test_sort(radix_sort8,    n=277)

if __name__ == '__main__':
    plac.call(main)

########NEW FILE########
__FILENAME__ = create_tests
import sys

def create_tests(*parameters):
    def tuplify(x):
        if not isinstance(x, tuple):
            return (x,)
        return x

    def decorator(method, parameters=parameters):
        for parameter in (tuplify(x) for x in parameters):
            
            def method_for_parameter(self, method=method, parameter=parameter):
                method(self, *parameter)
            args_for_parameter = ",".join(repr(v) for v in parameter)
            name_for_parameter = method.__name__ + "(" + args_for_parameter + ")"
            frame = sys._getframe(1)  # pylint: disable-msg=W0212
            frame.f_locals[name_for_parameter] = method_for_parameter
        return None
    return decorator

########NEW FILE########
__FILENAME__ = recursive_equal
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

import collections
import itertools

def recursive_equal(a, b):
    if isinstance(a, collections.Iterable):
        elwise_equal = all(itertools.imap(recursive_equal, a, b))
        length_check = sum(1 for x in a) == sum(1 for x in b)
        return elwise_equal and length_check
    else:
        return a == b

########NEW FILE########
__FILENAME__ = test_all
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

from test_syntax import *
from test_types import *
from test_unify import *
from test_infer import *
from test_indices import *
from test_simple import *
from test_reduce import *
from test_replicate import *
from test_rotate import *
from test_sort import *
from test_shift import *
from test_aos import *
from test_scalar_math import *
from test_gather import *
from test_subscript import *
from test_tuple_data import *
from test_scatter import *
from test_fixed import *
from test_closure import *
from test_tail_recursion import *
from test_zip import *
from test_update import *
from test_scan import *
from test_filter import *

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_aos
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

from copperhead import *
import unittest
from recursive_equal import recursive_equal
import numpy as np

@cu
def demux(x):
    return int32(x), (float32(x)+1.25, float32(x)+2.5)

@cu
def test(x):
    return map(demux, x)

@cu
def mux((x, (y, z))):
    return float32(x) + float32(y) + float32(z)

@cu
def test2(x):
    return map(mux, x)

@cu
def test3(x):
    a = test(x)
    b = test2(a)
    return b

class AoSTest(unittest.TestCase):
    def setUp(self):
        self.three = [1,2,3]
        self.golden_result = [(1, (2.25, 3.5)),
                         (2, (3.25, 4.5)),
                         (3, (4.25, 5.5))]
        self.golden_result_2 = [6.75, 9.75, 12.75]
        
    def testAoS_1(self):
        self.assertTrue(recursive_equal(self.golden_result, test(self.three)))

    def testAoS_2(self):
        #XXX Change once cuarrays can be constructed with tuple elements
        self.assertTrue(recursive_equal(self.golden_result_2,
                                        test2(test(self.three))))
    def testAoS_3(self):
        self.assertTrue(recursive_equal(self.golden_result_2,
                                        test3(self.three)))
        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_closure
from copperhead import *
import unittest

@cu
def closure_test(x):
    x = map(lambda xi: xi * 3, x)
    def stencil(i):
        if i == 0 or i == len(x)-1:
            return x[i]
        else:
            return (x[i-1] + x[i] + x[i+1])/3
    return map(stencil, indices(x))

@cu
def inline_closure_test(x, it):
    def inc():
        return map(lambda xi: xi + 1, x)
    if it > 0:
        incremented = inc()
        return inline_closure_test(incremented, it-1)
    else:
        return x

@cu
def cond_closure_test(a, x, it):
    def inc(xi):
        return a + xi
    if it > 0:
        incremented = map(inc, x)
        return cond_closure_test(a, incremented, it-1)
    else:
        return x

@cu
def nested_closure_test(a, x, it):
    def inc(xi):
        return a + xi
    def work():
        return map(inc, x)
    if it > 0:
        x = work()
        return nested_closure_test(a, x, it-1)
    else:
        return x
    
class ClosureTest(unittest.TestCase):
    def testClosure(self):
        self.assertEqual(list(closure_test(
                np.array([0, .25, .5, .75, 1.0], dtype=np.float32))),
                         [0, 0.75, 1.5, 2.25, 3])
    def testClosureInline(self):
        self.assertEqual(list(inline_closure_test(np.array([1,3,2], dtype=np.int32),
                                                  np.int32(2))),
                         [3,5,4])
    def testClosureCond(self):
        self.assertEqual(list(cond_closure_test(np.int32(2),
                                                np.array([5,5,5], dtype=np.int32),
                                                np.int32(2))),
                         [9,9,9])
    def testClosureNested(self):
        self.assertEqual(list(nested_closure_test(np.int32(2),
                                                  np.array([5,5,5], dtype=np.int32),
                                                  np.int32(2))),
                         [9,9,9])
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cudata
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

import numpy as np
from copperhead import *
import unittest
from recursive_equal import recursive_equal

class CudataTest(unittest.TestCase):
    def testNumpyFlat(self):
        a = np.array([1,2,3,4,5])
        self.assertTrue(recursive_equal(a, cuarray(a)))
    def testPythonFlat(self):
        a = [2.78, 3.14, 1.62]
        self.assertTrue(recursive_equal(a, cuarray(a)))
    def testNumpyNested(self):
        a = [[np.array([1,2]), np.array([3,4,5])],
        [np.array([6,7,8,9]), np.array([10,11,12,13,14]),
         np.array([15,16,17,18,19,20])]]
        self.assertTrue(recursive_equal(a, cuarray(a)))
    def testPythonNested(self):
        a = [[[1,2], [3,4,5]],
        [[6,7,8,9], [10,11,12,13,14],
         [15,16,17,18,19,20]]]
        self.assertTrue(recursive_equal(a, cuarray(a)))
    def deref_type_check(self, np_type):
        a = np.array([1], dtype=np_type)
        b = cuarray(a)
        self.assertTrue(type(a[0]) == type(b[0]))
        self.assertTrue(a[0] == b[0])
    def testInt32(self):
        self.deref_type_check(np.int32)
    def testInt64(self):
        self.deref_type_check(np.int64)
    def testFloat32(self):
        self.deref_type_check(np.float32)
    def testFloat64(self):
        self.deref_type_check(np.float64)
    def testBool(self):
        self.deref_type_check(np.bool)
    def testStr(self):
        a = [[[1,2], [3,4,5]],
        [[6,7,8,9], [10,11,12,13,14],
         [15,16,17,18,19,20]]]
        self.assertEqual(str(a), str(cuarray(a)))
    def testUnequalLength(self):
        a = [1,2,3]
        b = [1,2,3,4]
        self.assertFalse(recursive_equal(a, cuarray(b)))
        self.assertFalse(recursive_equal(b, cuarray(a)))
    def testUnequalContent(self):
        a = [1,2,3]
        b = [3,2,1]
        self.assertFalse(recursive_equal(a, cuarray(b)))
    def testUnequalNested(self):
        a = [[1,2],[3,4,5]]
        b = [[1,2],[3,4,5,6]]
        self.assertFalse(recursive_equal(a, cuarray(b)))
    def testUnequalTriplyNested(self):
        a = [[[1,2], [3,4,5]],
        [[6,7,8,9], [10,11,12,13,14],
        [15,16,17,18,19,20]]]
        b = [[[1,2], [3,4,5]],
        [[6,7,8,9,10], [10,11,12,13,14],
        [15,16,17,18,19,20]]]
        self.assertFalse(recursive_equal(a, cuarray(b)))
    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_filter
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_filter(x):
    return filter(lambda xi: xi > 3, x)

    
class GatherTest(unittest.TestCase):
    def setUp(self):
        self.source = [3, 1, 4, 5, 9, 2, 6, 4]
    def run_test(self, target, fn, *args):
        
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
        
    @create_tests(*runtime.backends)
    def testFilter(self, target):
        self.run_test(target, test_filter, self.source)
        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_fixed
from copperhead import *

import unittest

@cu
def dismantle((x, (y, z))):
    return x

@cu
def tuple_inline_test(x):
    return dismantle((x,(x,x)))

class TupleInlineTest(unittest.TestCase):
    def testTupleInline(self):
        self.assertEqual(tuple_inline_test(2), 2)


@cu
def rebind_test(x):
    y = [xi + 1 for xi in x]
    z = y
    return z

class RebindTest(unittest.TestCase):
    def testRebind(self):
        self.assertEqual(list(rebind_test([0,1,2])),
                         [1,2,3])


@cu
def inline_closure_literal_test(x, y):
    def my_add(a, b):
        return a + b
    def my_closure(a):
        return my_add(a, y)
    return my_closure(x)


        
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_gather
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_gather(x, i):
    return gather(x, i)

@cu
def test_gather_indices_fusion(x, i):
    return gather(x, [ii + 1 for ii in i])

@cu
def test_gather_source_boundary(x, i):
    return gather([xi + 1 for xi in x], i)
    
class GatherTest(unittest.TestCase):
    def setUp(self):
        self.source = [1,2,3,4,5]
        self.idx = [0,1,3]
    def run_test(self, target, fn, *args):
        
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
        
    @create_tests(*runtime.backends)
    def testGather(self, target):
        self.run_test(target, test_gather, self.source, self.idx)

    @create_tests(*runtime.backends)
    def testGatherIndicesFusion(self, target):
        self.run_test(target, test_gather_indices_fusion, self.source, self.idx)

    @create_tests(*runtime.backends)
    def testGatherSourceBoundary(self, target):
        self.run_test(target, test_gather_source_boundary, self.source, self.idx)

        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_indices
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_indices(x):
    return indices(x)

class IndicesTest(unittest.TestCase):
    def setUp(self):
        self.golden = np.array([0,1,2,3,4])
        self.input = np.array([5,4,3,2,1])

    @create_tests(*runtime.backends)
    def testIndices(self, target):
        with target:
            self.assertEqual(list(test_indices(self.input)), list(self.golden))
    
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_infer
#! /usr/bin/env python
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

import unittest

from copperhead import prelude
from copperhead.compiler.pyast import expression_from_text as parseE, \
                                      statement_from_text as parseS

from copperhead.compiler.parsetypes import type_from_text



from copperhead.compiler.typeinference import InferenceError, infer, TypingContext


def thunk(type):
    'Create type-carrying thunk'
    fn = lambda x:x

    if isinstance(type, str):
        type = type_from_text(type)
    elif not isinstance(type, T.Type):
        raise TypeError, \
                "type (%s) must be string or Copperhead Type object" % type

    fn.cu_type = type

    return fn

# Fake globals to be used in place of the Prelude for now
G1 = {
        'op_add'   : thunk('(a,a) -> a'),
        'op_sub'   : thunk('(a,a) -> a'),
        'op_mul'   : thunk('(a,a) -> a'),
        'op_neg'   : thunk('a -> a'),
        #XXX Remove once issue #3 is resolved
        'op_band'  : thunk('(Bool, Bool) -> Bool'),
        'op_bor'   : thunk('(Bool, Bool) -> Bool'),
        #End XXX
        'range'    : thunk('Long -> [Long]'),
        'cmp_lt'   : thunk('(a,a) -> Bool'),
        'cmp_eq'   : thunk('(a,a) -> Bool'),

        'sum'      : thunk('[a] -> a'),
        'any'      : thunk('[Bool] -> Bool'),

        'ZZ'       : thunk('[Long]'),
        'RR'       : thunk('[Double]'),
        'BB'       : thunk('[Bool]'),
     }


class ExpressionTypeTests(unittest.TestCase):

    def setUp(self): pass

    def tearDown(self): pass

    def typing(self, source, t):
        P = parseE(source)
        self.assertEqual(str(infer(P, globals=G1)), t)

    def illegal(self, source):
        P = parseE(source)
        self.assertRaises(InferenceError, lambda:infer(P, globals=G1))

    def testLiterals(self):
        self.typing("5", "Long")
        self.typing("1.33", "Double")
        self.typing("True", "Bool")
        self.typing("False", "Bool")
        self.typing("None", "Void")

    def testBuiltins(self):
        self.typing("op_add", "ForAll a: (a, a) -> a")
        self.typing("range", "Long -> [Long]")
        self.illegal("undefined_variable")
        self.typing("op_add(2,3)", "Long")
        self.typing("range(9)", "[Long]")

    def testTuples(self):
        self.typing("(1, True, 3.0, 4, 5)", "(Long, Bool, Double, Long, Long)")

    def testConditionals(self):
        self.typing("12 if True else 24", "Long")
        self.illegal("12 if -100 else 24")
        self.illegal("12 if False else 24.0")

    def testArithmetic(self):
        self.typing("2 + 3", "Long")
        self.typing("2.0 + 3.0", "Double")
        self.illegal("2 + 3.0")

    def testBoolean(self):
        self.typing("True and False", "Bool")
        self.typing("True or  False", "Bool")
        self.illegal("True or  0")
        self.illegal("1 and False")
        self.illegal("1 and 0")

    def testLambdas(self):
        self.typing("lambda: 1", "Void -> Long")
        self.typing("lambda x: 1", "ForAll a: a -> Long")
        self.typing("lambda x: x", "ForAll a: a -> a")
        self.typing("lambda x: x+1", "Long -> Long")
        self.typing("lambda x,y: x+y", "ForAll a: (a, a) -> a")
        self.typing("lambda x,y: x+y*2.0", "(Double, Double) -> Double")
        self.typing("lambda x: 12 if x else 24", "Bool -> Long")
        self.typing("True and (lambda x:True)(3)", "Bool")

    def testMaps(self):
        self.typing("map(lambda x: x, ZZ)", "[Long]")
        self.typing("map(lambda x: x, range(9))", "[Long]")
        self.typing("map(lambda x: x+1, range(9))", "[Long]")
        self.illegal("map(lambda x: x+2.0, range(9))")
        self.illegal("map(lambda x: x and True, range(9))")
        self.typing("map(lambda x: x<42, range(9))", "[Bool]")

    def testReduction(self):
        self.typing("any(BB)", "Bool")
        self.typing("any(map(lambda x: x<42, ZZ))", "Bool")
        self.typing("sum(ZZ)", "Long")
        self.typing("sum(RR)", "Double")
        self.typing("sum(range(9))", "Long")

    def testIdentity(self):
        self.typing("lambda x: x", "ForAll a: a -> a")
        self.typing("(lambda x: x)(lambda x:x)", "ForAll a: a -> a")
        self.typing("(lambda x: x)(lambda x:x)(7)", "Long")
        self.illegal("lambda x: x(x)")
        self.illegal("(lambda i: i(i))(lambda x:x)")

    def testWrapping(self):
        self.typing("lambda A: map(lambda x:x, A)", "ForAll a: [a] -> [a]")
        self.typing("lambda A: map(lambda x:x+1, A)", "[Long] -> [Long]")
        self.typing("lambda A: any(A)", "[Bool] -> Bool")
        self.typing("lambda A: sum(A)", "ForAll a: [a] -> a")

    def testVecAdd(self):
        self.typing("lambda x,y:  map(lambda a, b: a + b, x, y)",
                    "ForAll a: ([a], [a]) -> [a]")

    def testSaxpy(self):
        self.typing("lambda Z: map(lambda xi, yi: 2*xi + 3*yi, Z, Z)",
                    "[Long] -> [Long]")

        self.typing("lambda a: map(lambda xi, yi: a*xi + yi, ZZ, ZZ)",
                    "Long -> [Long]")

        self.typing("lambda a: map(lambda xi, yi: a*xi + yi, RR, RR)",
                    "Double -> [Double]")

        self.illegal("lambda a: map(lambda xi, yi: a*xi + yi, RR, ZZ)")

        self.typing("lambda a: lambda x,y: map(lambda xi, yi: a*xi + yi, x, y)",
                    "ForAll a: a -> ([a], [a]) -> [a]")

        self.typing("lambda a,x,y: map(lambda xi, yi: a*xi + yi, x, y)",
                    "ForAll a: (a, [a], [a]) -> [a]")

    def testSlicing(self):
        self.typing("ZZ[10]", "Long")
        self.typing("RR[10]", "Double")
        self.typing("lambda i: RR[i]", "Long -> Double")
        self.illegal("ZZ[1.0]")
        self.illegal("ZZ[undef]")


class StatementTypeTests(unittest.TestCase):

    def setUp(self):
        self.tycon = TypingContext(globals=G1)

    def tearDown(self): pass

    def illegal(self, source):
        ast = parseS(source)
        self.assertRaises(InferenceError,
                lambda: infer(ast, globals=G1))

    def typing(self, source, t="Void"):
        ast = parseS(source)
        result = infer(ast, context=self.tycon)
        self.assertEqual(str(result), t)

    def testReturnLiteral(self):
        self.typing("return 1", "Long")
        self.typing("return True", "Bool")
        self.typing("return (1,1)", "(Long, Long)")
        self.typing("return (1.0, False)", "(Double, Bool)")

    def testReturnSimple(self):
        self.typing("return 1+3*4", "Long")
        self.illegal("return x+3")
        self.typing("x = 5", "Void")
        self.typing("x = 4; return 1", "Long")
        self.typing("x = 4; return x", "Long")
        self.typing("x=4; y=3; return x*y", "Long")
        self.typing("x=7; x=False; return x", "Bool")

    def testTupleBinding(self):
        self.typing("p0 = (0.0, 0.0); return p0", "(Double, Double)")
        self.typing("x0, y0 = (5, -5)")
        self.typing("return x0", "Long")
        self.typing("return y0", "Long")
        self.illegal("x0, y0, z0 = (5, -5)")
        self.illegal("x0, y0 = (5, -5, 55)")

    def testSimpleProcedures(self):
        self.typing("def f1(x): return x")
        self.typing("def f2(x): y=3; return x+3")
        self.typing("def f3(x): return f2(x)")
        self.typing("def f4():  return 5")
        self.typing("def f5(x): return lambda y: x+y")

        self.typing("return f1", "ForAll a: a -> a")
        self.typing("return f2", "Long -> Long")
        self.typing("return f3", "Long -> Long")
        self.typing("return f4", "() -> Long")
        self.typing("return f5", "ForAll a: a -> a -> a")

    def testIdentity(self):
        self.typing("def id(x): return x")
        self.typing("return id(True) and id(False)", "Bool")
        self.illegal("return id(True) and id(3)")
        self.typing("return id(True) and 1<id(3)", "Bool")
        self.typing("return id(id)(True) and id(id)(False)", "Bool")
        self.typing("return id(id)(True) and 1<id(id)(3)", "Bool")
        self.typing("g=id(id); return g(True) and g(False)", "Bool")
        self.typing("g=id(id); return g(True) and 1<g(3)", "Bool")
        self.illegal("def f6(f): return f(True) and 1<f(3)")

    def testReduction(self):
        self.typing("return sum(range(9))", "Long")

        self.typing("def red1(A): return sum(A)")
        self.typing("return red1", "ForAll a: [a] -> a")
        self.typing("return red1(range(9))", "Long")

        self.typing("red2 = lambda(A): sum(A)")
        self.typing("return red2", "ForAll a: [a] -> a")

    def testIncr(self):
        self.typing("def incr(a): return a+1")
        self.typing("def add1(x): return map(incr, x)")
        self.typing("return incr", "Long -> Long")
        self.typing("return add1", "[Long] -> [Long]")

    def testSaxpy(self):
        self.typing(saxpy)
        t = "ForAll a: (a, [a], [a]) -> [a]"
        self.typing("return saxpy1", t)
        self.typing("return saxpy2", t)
        self.typing("return saxpy3", t)
        self.typing("return saxpy4", t)

    def testIfThenElse(self):
        self.typing(ifelse1, "Long")
        self.illegal(ifelse2)
        self.typing(conditionals)
        self.typing("return abs", "Long -> Long")

    def testEmbeddedFunctions(self):
        self.typing(idseq)
        self.typing("return idseq0", "ForAll a: [a] -> [a]")
        self.typing("return idseq1", "ForAll a: [a] -> [a]")
        self.typing("return idseq2", "ForAll a: [a] -> [a]")

    def testRecursive(self):
        self.typing(recursive)
        self.typing("return fun1", "ForAll a, b: a -> b")
        self.typing("return fun2", "ForAll a: a -> Long")
        self.typing("return fun3", "Long -> Long")


class ClosureTypeTests(unittest.TestCase):

    def setUp(self):
        self.tycon = TypingContext(globals=G1)

    def tearDown(self): pass

    def illegal(self, source):
        from copperhead.compiler.rewrites import closure_conversion
        ast = parseS(source)
        ast = closure_conversion(ast, G1)
        self.assertRaises(InferenceError,
                lambda: infer(ast, globals=G1))

    def typing(self, source, t="Void"):
        from copperhead.compiler.rewrites import closure_conversion
        ast = parseS(source)
        ast = closure_conversion(ast, G1)
        result = infer(ast, context=self.tycon)
        self.assertEqual(str(result), t)

    def testLambdaClosures(self):
        self.typing("a=1; f=lambda x: x+a; return f(2)", "Long")
        self.illegal("a=1; f=lambda x: x+a; return f(True)")
        self.illegal("a=True; f=lambda x: x+a; return f(2)")

        self.typing("a,b=1,2; f=lambda x: a*x+b; return f(2)", "Long")
        self.illegal("a,b=1,2.0; f=lambda x: a*x+b; return f(2)")

    def testProcedureClosures(self):
        self.typing(saxpy)
        self.typing("return saxpy1", "ForAll a: (a, [a], [a]) -> [a]")
        self.typing("return saxpy2", "ForAll a: (a, [a], [a]) -> [a]")
        self.typing("return saxpy3", "ForAll a: (a, [a], [a]) -> [a]")
        self.typing("return saxpy4", "ForAll a: (a, [a], [a]) -> [a]")

    def testEmbeddedFunctions(self):
        self.typing(idseq)
        self.typing("return idseq0", "ForAll a: [a] -> [a]")
        self.typing("return idseq1", "ForAll a: [a] -> [a]")
        self.typing("return idseq2", "ForAll a: [a] -> [a]")

class FrontendTypeTests(unittest.TestCase):
    def setUp(self):
        self.tycon = TypingContext(globals=G1)

    def tearDown(self): pass

    def typing(self, source, t="Void"):
        from copperhead.compiler import rewrites as Front

        ast = parseS(source)
        ast = Front.closure_conversion(ast, G1)
        ast = Front.single_assignment_conversion(ast)
        ast = Front.lambda_lift(ast)
        result = infer(ast, context=self.tycon)
        self.assertEqual(str(result), t)

    def testSaxpy(self):
        self.typing(saxpy)
        self.typing("return saxpy1", "ForAll a: (a, [a], [a]) -> [a]")
        self.typing("return saxpy2", "ForAll a: (a, [a], [a]) -> [a]")
        self.typing("return saxpy3", "ForAll a: (a, [a], [a]) -> [a]")
        self.typing("return saxpy4", "ForAll a: (a, [a], [a]) -> [a]")



class TypingWithPrelude(unittest.TestCase):

    def setUp(self):
        self.tycon = TypingContext(globals=prelude.__dict__)

    def tearDown(self): pass

    def illegal(self, source):
        ast = parseS(source)
        self.assertRaises(InferenceError,
                lambda: infer(ast, globals=prelude.__dict__))

    def typing(self, source, t="Void"):
        ast = parseS(source)
        result = infer(ast, context=self.tycon)
        self.assertEqual(str(result), t)

    def testSpvv(self):
        self.typing(spvv)
        self.typing("return spvv1", "ForAll a: ([Long], [a], [Long]) -> Long")
        self.typing("return spvv2", "ForAll a, b: ([a], [b], [a]) -> a")

    # def testZipping(self):
    #     self.typing("def zippy1(x,y): return zip(x, y)")
    #     self.typing("def zippy2(x,y): return map(lambda xi,yi: (xi,yi), x, y)")
    #     self.typing("def zippy3(x,y): f=(lambda x,y: (x,y)); return map(f, x, y)")
    #     self.typing("def zippy4(x,y,z): return zip(x, y)")
    #     self.typing("def zippy5(x,y,z): z=x; return zip(x, y)")

    #     self.typing("return zippy1", "ForAll a, b: ([a], [b]) -> [(a, b)]")
    #     self.typing("return zippy2", "ForAll a, b: ([a], [b]) -> [(a, b)]")
    #     self.typing("return zippy3", "ForAll a, b: ([a], [b]) -> [(a, b)]")
    #     self.typing("return zippy4", "ForAll a, b, c: ([a], [b], c) -> [(a, b)]")
    #     self.typing("return zippy5", "ForAll a, b, c: ([a], [b], c) -> [(a, b)]")

    def testDot(self):
        self.typing("def dot1(x,y): return sum(map(lambda a, b: a * b, x, y))")
        self.typing("def dot2(x,y): return reduce(op_add, map(lambda a, b: a * b, x, y), 0)")
        self.typing("def dot3(x,y): y=x; return sum(map(lambda a, b: a * b, x, y))")

        self.typing("return dot1", "ForAll a: ([a], [a]) -> a")
        self.typing("return dot2", "([Long], [Long]) -> Long")
        self.typing("return dot3", "ForAll a, b: ([a], b) -> a")

        self.typing(dots)
        self.typing("return dot4", "ForAll a: ([a], [a]) -> a")
        self.typing("return dot5", "ForAll a: ([a], [a]) -> a")


spvv = """
def spvv1(x, cols, y):
    z = gather(y, cols)
    return reduce(lambda a, b: a + b, map(lambda a, b: a * b, x, z), 0)

def spvv2(x, cols, y):
    z = gather(y, cols)
    return sum(map(op_mul, x, z))
"""


saxpy = """
def saxpy1(a, x ,y):
    return map(lambda xi, yi: a*xi + yi, x, y)

def saxpy2(a, x, y):
    return [a*xi + yi for xi,yi in zip(x,y)]

def saxpy3(a, x, y):
    triad = lambda xi, yi: a*xi + yi
    return map(triad, x, y)

def saxpy4(a, x, y):
    def triad(xi, yi):
        return a * xi + yi
    return map(triad, x, y)
"""

ifelse1 = """
if 1<0: x=1; y=0; return x+y
else:   x=2; y=3; return y-x
"""

ifelse2 = """
if 1<0: x=1; y=0; return x+y
else:   x=2; y=3; return 3.0*y-x
"""

conditionals = """
def abs(x):
    if x==0:  return x
    elif x<0: return -x
    else:     return x
"""

dots = """
def dot4(x, y):
    return sum(map(op_mul, x, y))

def dot5(x, y):
    _e0 = map(op_mul, x, y)
    _returnValue = sum(_e0)
    return _returnValue
"""

idseq = """
def ident(x): return x

def idseq0(A):
    return map(ident, A)

def idseq1(A):
    return map(lambda x: ident(x), A)

def idseq2(A):
    def _ident(x): return x
    return map(lambda x: _ident(x), A)
"""

recursive = """\
def fun1(x):  return fun1(x)

def fun2(x):  return 1 + fun2(x)

def fun3(x):  return 1 + fun3(x-1)
"""

if __name__ == "__main__":
    unittest.main()
    exit()

########NEW FILE########
__FILENAME__ = test_range
from copperhead import *

# @cu
# def test_bounded_range(a, b):
#     return bounded_range(a, b)

# print test_bounded_range(10, 15)


@cu
def test(x):
    y = bounded_range(10, x)
    return [yi + 1 for yi in y]

import copperhead.runtime.intermediate as I
with I.tracing(action=I.print_and_pause):
    print test(15)

# @cu
# def inline_closure_literal_test(x):
#     def scale(b, y):
#         return [yi + b for yi in y]
#     return scale(10, x)

# print inline_closure_literal_test([0, 1])

########NEW FILE########
__FILENAME__ = test_reduce
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_reduce(x, p):
    return reduce(op_add, x, p)

@cu
def test_sum(x):
    return sum(x)

@cu
def test_reduce_as_sum(x):
    return reduce(op_add, x, 0)

@cu
def test_any(x):
    return any(x)

@cu
def test_all(x):
    return all(x)

@cu
def test_min(x):
    return min(x)

@cu
def test_max(x):
    return max(x)

class ReduceTest(unittest.TestCase):
    def setUp(self):
        source = [1,2,3,4,5]
        prefix = 1
        self.golden_s = sum(source)
        self.golden_r = self.golden_s + prefix
        self.int32 = (np.array(source, dtype=np.int32), np.int32(prefix))
        self.negative = [False, False, False, False, False]
        self.positive = [True, True, True, True, True]
        self.indeterminate = [False, True, False, True, False]
        
    def run_test(self, target, f, g, *args):
        with target:
            self.assertEqual(f(*args), g)
            
    @create_tests(*runtime.backends)
    def testReduce(self, target):
        self.run_test(target, test_reduce, self.golden_r, *self.int32)

    @create_tests(*runtime.backends)
    def testSum(self, target):
        self.run_test(target, test_sum, self.golden_s, self.int32[0])

    @create_tests(*runtime.backends)
    def testSumAsReduce(self, target):
        self.run_test(target, test_reduce_as_sum, self.golden_s, self.int32[0])

    @create_tests(*runtime.backends)
    def testAny(self, target):
        self.run_test(target, test_any, False, self.negative)
        self.run_test(target, test_any, True, self.positive)
        self.run_test(target, test_any, True, self.indeterminate)

    @create_tests(*runtime.backends)
    def testAll(self, target):
        self.run_test(target, test_all, False, self.negative)
        self.run_test(target, test_all, True, self.positive)
        self.run_test(target, test_all, False, self.indeterminate)

    @create_tests(*runtime.backends)
    def testMax(self, target):
        self.run_test(target, test_max, 5, self.int32[0])

    @create_tests(*runtime.backends)
    def testMin(self, target):
        self.run_test(target, test_min, 1, self.int32[0])



if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_replicate
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests
from recursive_equal import recursive_equal


@cu
def test_repl(x, n):
    return replicate(x, n)

@cu
def test_internal_tuple_repl(x, n):
    return replicate((x, x), n)

@cu
def test_internal_named_tuple_repl(x, n):
    a = x, x
    return replicate(a, n)

class ReplicateTest(unittest.TestCase):
    def setUp(self):
        self.val = 3
        self.size = 5
        self.golden = [self.val] * self.size

    def run_test(self, target, x, n):
        with target:
            self.assertEqual(list(test_repl(x, n)), self.golden)

    @create_tests(*runtime.backends)
    def testRepl(self, target):
        self.run_test(target, np.int32(self.val), self.size)

    def testReplTuple(self):
        self.assertTrue(recursive_equal(test_repl((1,1), 2), [(1,1),(1,1)]))

    def testReplNestedTuple(self):
        a = test_repl(((1,2),3),2)
        self.assertTrue(recursive_equal(
                a,
                [((1,2),3),((1,2),3)]))              
        
    def testReplInternalTuple(self):
        self.assertTrue(recursive_equal(test_internal_tuple_repl(1, 2),
                                        [(1, 1), (1, 1)]))
    def testReplInternalNamedTuple(self):
        self.assertTrue(recursive_equal(test_internal_named_tuple_repl(1, 2),
                                        [(1, 1), (1, 1)]))
        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_rotate
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_rotate(x, amount):
    return rotate(x, amount)

class RotateTest(unittest.TestCase):
    def setUp(self):
        self.source = [1,2,3,4,5]
        

    def run_test(self, target, fn, *args):
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))

    @create_tests(*runtime.backends)
    def testRotateP(self, target):
        self.run_test(target, test_rotate, self.source, 2)

    @create_tests(*runtime.backends)
    def testRotateN(self, target):
        self.run_test(target, test_rotate, self.source, -2)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_scalar
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np

@cu
def scalar_fn(x, y):
    return x + y

a = scalar_fn(np.float32(1.0), np.float32(2.0))
print a

########NEW FILE########
__FILENAME__ = test_scalar_math
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests
from recursive_equal import recursive_equal

@cu
def test_abs(x):
    return abs(x)

@cu
def test_seq_abs(x):
    return map(abs, x)

@cu
def test_exp(x):
    return exp(x)

@cu
def test_seq_exp(x):
    return map(exp, x)

@cu
def test_log(x):
    return log(x)

@cu
def test_seq_log(x):
    return map(log, x)

@cu
def test_sqrt(x):
    return sqrt(x)

@cu
def test_seq_sqrt(x):
    return map(sqrt, x)



class ScalarMathTest(unittest.TestCase):
        
    def run_test(self, target, f, g, *args):
        with target:
            self.assertTrue(recursive_equal(f(*args), g))
            
    @create_tests(*runtime.backends)
    def testAbs(self, target):
        self.run_test(target, test_abs, 1, *(1,))
        self.run_test(target, test_abs, 1, *(-1,))

    @create_tests(*runtime.backends)
    def testAbsSeq(self, target):
        self.run_test(target, test_seq_abs, [1, 1], *([1,-1],))

    @create_tests(*runtime.backends)
    def testExp(self, target):
        b = np.float32(1)
        e_b = np.exp(b)
        self.run_test(target, test_exp, e_b, *(b,))

    @create_tests(*runtime.backends)
    def testExpSeq(self, target):
        a = np.float32(0)
        e_a = np.exp(a)
        b = np.float32(1)
        e_b = np.exp(b)
        self.run_test(target, test_seq_exp, [e_a, e_b], *([a, b],))

    @create_tests(*runtime.backends)
    def testLog(self, target):
        b = np.float32(1)
        e_b = np.log(b)
        self.run_test(target, test_log, e_b, *(b,))

    @create_tests(*runtime.backends)
    def testLogSeq(self, target):
        a = np.float32(1)
        e_a = np.log(a)
        b = np.float32(1)
        e_b = np.log(b)
        self.run_test(target, test_seq_log, [e_a, e_b], *([a, b],))

    @create_tests(*runtime.backends)
    def testSqrt(self, target):
        b = np.float32(2)
        e_b = np.sqrt(b)
        self.run_test(target, test_sqrt, e_b, *(b,))

    @create_tests(*runtime.backends)
    def testSqrtSeq(self, target):
        a = np.float32(1)
        e_a = np.sqrt(a)
        b = np.float32(4)
        e_b = np.sqrt(b)
        self.run_test(target, test_seq_sqrt, [e_a, e_b], *([a, b],))



if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_scan
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def fn(xa, xb):
    return xa + xb + 1

@cu
def test_scan(x):
    return scan(fn, x)

@cu
def test_rscan(x):
    return rscan(fn, x)

@cu
def test_exclusive_scan(x):
    return exclusive_scan(fn, cast_to_el(0, x), x)

@cu
def test_exclusive_rscan(x):
    return exclusive_rscan(fn, cast_to_el(0, x), x)

class ScanTest(unittest.TestCase):
    def setUp(self):
        self.source = [1,2,3,4,5]

    def run_test(self, target, fn, *args):
        
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
        
    @create_tests(*runtime.backends)
    def testScan(self, target):
        self.run_test(target, test_scan, self.source)

    @create_tests(*runtime.backends)
    def testRscan(self, target):
        self.run_test(target, test_rscan, self.source)

    @create_tests(*runtime.backends)
    def testExscan(self, target):
        self.run_test(target, test_exclusive_scan, self.source)

    @create_tests(*runtime.backends)
    def testExrscan(self, target):
        self.run_test(target, test_exclusive_rscan, self.source)
        
        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_scatter
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_permute(x, i):
    return permute(x, i)

class PermuteTest(unittest.TestCase):
    def setUp(self):
        self.source = [1,2,3,4,5]
        self.idx = [2,4,1,0,3]
    def run_test(self, target, fn, *args):
        
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
        
    @create_tests(*runtime.backends)
    def testPermute(self, target):
        self.run_test(target, test_permute, self.source, self.idx)


@cu
def test_scatter(x, i, d):
    return scatter(x, i, d)

class ScatterTest(unittest.TestCase):
    def setUp(self):
        self.source = [1,2]
        self.idx = [2,4]
        self.dest = [1,2,3,4,5]
    def run_test(self, target, fn, *args):
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
        
    @create_tests(*runtime.backends)
    def testPermute(self, target):
        self.run_test(target, test_scatter, self.source, self.idx, self.dest)

        
        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_shift
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_shift(x, amount, boundary):
    return shift(x, amount, boundary)

class ShiftTest(unittest.TestCase):
    def setUp(self):
        self.source = [1,2,3,4,5]

    def run_test(self, target, fn, *args):
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
    @create_tests(*runtime.backends)
    def testShiftP(self, target):
        self.run_test(target, test_shift, self.source, 2, 3)

    @create_tests(*runtime.backends)
    def testShiftN(self, target):
        self.run_test(target, test_shift, self.source, -2, 4)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_simple
#
#   Copyright 2008-2012 NVIDIA Corporation
#  Copyright 2009-2010 University of California
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

from copperhead import *
import numpy as np

import unittest
from create_tests import create_tests

@cu
def saxpy(a, x, y):
    """Add a vector y to a scaled vector a*x"""
    return map(lambda xi, yi: a * xi + yi, x, y)

@cu
def saxpy2(a, x, y):
    return [a*xi+yi for xi,yi in zip(x,y)]

@cu
def saxpy3(a, x, y):
    def triad(xi, yi):
        return a * xi + yi
    return map(triad, x, y)

@cu
def sxpy(x, y):
    def duad(xi, yi):
        return xi + yi
    return map(duad, x, y)

@cu
def incr(x):
    return map(lambda xi: xi + 1, x)

@cu
def as_ones(x):
    return map(lambda xi: 1, x)

@cu
def idm(x):
    return map(lambda b: b, x)

@cu
def idx(x):
    def id(xi):
        return xi
    return map(id, x)

@cu
def incr_list(x):
    return [xi + 1 for xi in x]

class SimpleTests(unittest.TestCase):
    def setUp(self):
        self.hasGPU = hasattr(places, 'gpu0')
        self.ints = np.arange(7, dtype=np.int32)
        self.consts = np.array([1] * 7, dtype = np.int32)
        self.floats = np.array(self.ints, dtype=np.float32)


    def run_test(self, fn, *args):
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args)
        self.assertEqual(list(python_result), list(copperhead_result))


    @create_tests(*runtime.backends)
    def testIncrInts(self, target):
        with target:
            self.run_test(incr, self.ints)
    @create_tests(*runtime.backends)
    def testIncrFloats(self, target):
        with target:
            self.run_test(incr, self.floats)
    @create_tests(*runtime.backends)
    def testIncrListInts(self, target):
        with target:
            self.run_test(incr_list, self.ints)
    @create_tests(*runtime.backends)
    def testIncrListFloats(self, target):
        with target:
            self.run_test(incr_list, self.floats)
    @create_tests(*runtime.backends)
    def testAsonesInts(self, target):
        with target:
            self.run_test(as_ones, self.ints)
    @create_tests(*runtime.backends)
    def testAsonesFloats(self, target):
        with target:
            self.run_test(as_ones, self.floats)
    @create_tests(*runtime.backends)
    def testIdmInts(self, target):
        with target:
            self.run_test(idm, self.ints)
    @create_tests(*runtime.backends)
    def testIdmFloats(self, target):
        with target:
            self.run_test(idm, self.floats)
    @create_tests(*runtime.backends)
    def testSaxpyInts(self, target):
        with target:
            self.run_test(saxpy, np.int32(2), self.ints, self.consts)
    @create_tests(*runtime.backends)
    def testSaxpyFloats(self, target):
        with target:
            self.run_test(saxpy, np.float32(2), self.floats, self.floats)
    @create_tests(*runtime.backends)
    def testSaxpy2Ints(self, target):
        with target:
            self.run_test(saxpy2, np.int32(2), self.ints, self.consts)
    @create_tests(*runtime.backends)
    def testSaxpy2Floats(self, target):
        with target:
            self.run_test(saxpy2, np.float32(2), self.floats, self.floats)
    @create_tests(*runtime.backends)
    def testSaxpy3Ints(self, target):
        with target:
            self.run_test(saxpy3, np.int32(2), self.ints, self.consts)
    @create_tests(*runtime.backends)
    def testSaxpy3Floats(self, target):
        with target:
            self.run_test(saxpy3, np.float32(2), self.floats, self.floats)    
    @create_tests(*runtime.backends)
    def testSxpyInts(self, target):
        with target:
            self.run_test(sxpy, self.ints, self.ints)
    @create_tests(*runtime.backends)
    def testSxpyFloats(self, target):
        with target:
            self.run_test(sxpy, self.ints, self.ints)    

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sort
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
import random
from create_tests import create_tests

@cu
def lt_sort(x):
    return sort(cmp_lt, x)

@cu
def gt_sort(x):
    return sort(cmp_gt, x)

class SortTest(unittest.TestCase):
    def setUp(self):
        self.source = np.array([random.random() for x in range(5)], dtype=np.float32)
        
        
    def run_test(self, target, fn, *args):
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
    
    @create_tests(*runtime.backends)
    def testLtSort(self, target):
        self.run_test(target, lt_sort, self.source)

    @create_tests(*runtime.backends)
    def testGtSort(self, target):
        self.run_test(target, gt_sort, self.source)


if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_subscript
import unittest
from copperhead import *
from recursive_equal import recursive_equal

@cu
def test_sub(a):
    def el(i):
        return a[len(a)-1-i]
    return map(el, indices(a))

@cu
def test_deref(a):
    return a[0]

@cu
def test_deref_zip(a):
    b = zip(a, a)
    return b[1]

class Subscripting(unittest.TestCase):
    def testSub(self):
        source = [1,2,3,4,5]
        result = test_sub(source)
        self.assertTrue(recursive_equal([5,4,3,2,1],result))
    def testDeref(self):
        source = [4,3,2,1]
        result = test_deref(source)
        self.assertTrue(4, result)
    def testDerefZip(self):
        source = [5,6,7]
        result = test_deref_zip(source)
        self.assertEqual((6,6), result)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_syntax
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Test Copperhead abstract syntax tree parsing and manipulation.
"""

import unittest
import __builtin__

from copperhead import prelude
from copperhead.compiler import pltools, pyast, coresyntax as S, rewrites as F, passes as P

def expr(text):  return pyast.expression_from_text(text)
def stmt(text):  return pyast.statement_from_text(text)

class ExprParsingTests(unittest.TestCase):

    def setUp(self): pass
    def tearDown(self): pass

    def testLiterals(self):
        self.assertEqual(str(expr('1')), '1')
        self.assertEqual(str(expr('x')), 'x')

        self.assertEqual(repr(expr('1')), "Number(1)")
        self.assertEqual(repr(expr('x')), "Name('x')")

    def testOperators(self):
        self.assertEqual( str(expr('1+2')), 'op_add(1, 2)' )
        self.assertEqual( str(expr('1>>2')), 'op_rshift(1, 2)' )
        self.assertEqual( str(expr('1<2')), 'cmp_lt(1, 2)' )
        
        self.assertEqual( str(expr('x and y and (32*2)')),
                          #XXX Issue 3: Short circuit operators
                          # When this issue is fixed, replace with:
                          #'x and y and op_mul(32, 2)'
                          'op_band(x, op_band(y, op_mul(32, 2)))' )

    def testMap(self):
        self.assertEqual(str(expr('map(fmad, a, x, y)')), 'map(fmad, a, x, y)')

    def testIf(self):
        self.assertEqual(str(expr('x if True else y')), 'x if True else y')

    def testLambda(self):
        self.assertEqual(str(expr('lambda x: lambda y: x+y')),
                         'lambda x: lambda y: op_add(x, y)')

    def testComprehensions(self):
        self.assertEqual(str(expr('[x+3 for x in range(10)]')),
                'map(lambda x: op_add(x, 3), range(10))')
        self.assertEqual(str(expr('[x+y for x,y in zip(range(10),range(10))]')),
                'map(lambda x, y: op_add(x, y), range(10), range(10))')

    def testSubscripts(self):
        self.assertEqual(str(expr('A[i]')), 'A[i]')
        self.assertEqual(repr(expr('A[10]')),
                         "Subscript(Name('A'), Number(10))")
        self.assertEqual(repr(expr('A[i]')),
                         "Subscript(Name('A'), Name('i'))")

class StmtParsingTests(unittest.TestCase):
    
    def setUp(self): pass
    def tearDown(self): pass

    def match(self, src, ref):
        code = stmt(src)
        text = '\n'.join(map(str, code))
        self.assertEqual(text, ref)

    def testBindings(self):
        self.match('x = 4', 'x = 4')

    def testReturn(self):
        self.match('return x+y', 'return op_add(x, y)')

    def testProcedure(self):
        self.match('def f(a,b): return a * b - 4',
                   'def f(a, b):\n    return op_sub(op_mul(a, b), 4)')

    def testCond(self):
        self.match('if x<1: return x\nelse:  return 1/x',
            'if cmp_lt(x, 1):\n    return x\nelse:\n    return op_div(1, x)')


class FreeVariableTests(unittest.TestCase):
    
    def setUp(self):
        # The proper "global" environment for these tests must include
        # __builtins__ so that things like True are considered defined.
        self.env = pltools.Environment(prelude.__dict__, __builtin__.__dict__)

    def tearDown(self): pass

    def check(self, src, vars):
        f = S.free_variables(src, self.env)
        self.assertEqual(sorted(f), sorted(list(vars)))

    def testLiterals(self):
        self.check(expr('32'), [])
        self.check(expr('True and False'), [])
        self.check(expr('None'), [])
        self.check(expr('True and x'), 'x')

    def testSimple(self):
        self.check(expr('x+y'), 'xy')
        self.check(expr('f(g(x, y))'), 'fgxy')

    def testLambda(self):
        self.check(expr('lambda x: y*x'), 'y')
        self.check(expr('lambda y: lambda x: y*x'), [])

    def testClosure(self):
        # closure are not supported by our front-end parser, so we have
        # to construct the AST manually.
        self.check(S.Closure([S.Name('a'), S.Name('b')],
                             S.Lambda(map(S.Name, ['x','y','z']),
                                      S.And(map(S.Name, ['w', 'x','y','z'])))),
                   'abw')

    def testBindings(self):
        self.check(stmt('x=3+y'), 'y')
        self.check(stmt('x=3; z=x+y'), 'y')
        self.check(stmt('x=3; z=x+y; return z'), 'y')

        # XXX This is currently the correct behavior according to
        #     Copperhead, but represents a semantic deviation from
        #     Python.  See the Copperhead wiki for details.
        self.check(stmt('f = lambda x: (x+y, f)'), 'fy')


class SubstitutionTests(unittest.TestCase):

    def setUp(self): pass
    def tearDown(self): pass

    def check(self, src, subst, ref):
        e = expr(src)
        code = S.substituted_expression(e, subst)
        self.assertEqual(str(code), ref)

    def testExpressions(self):
        self.check('x+y', {'x': 'x_1'}, 'op_add(x_1, y)')

    def testLambda(self):
        self.check('lambda x: y*x', {'x': 'x_1', 'y': 'y_1'},
                   'lambda x: op_mul(y_1, x)')

        self.check('lambda y: lambda x: y*x', {'x': 'x_1', 'y': 'y_1'},
                   'lambda y: lambda x: op_mul(y, x)')

class SyntaxErrorTests(unittest.TestCase):
    def check(self, fn, *args):
        self.assertRaises(SyntaxError, fn, *args)
    def testCond(self):
        self.check(stmt, """
if True:
  return False
""")
    def testArity(self):
        self.check(F.arity_check, stmt("""
a = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)"""))
        self.check(F.arity_check, stmt("""
def foo(a, b, c, d, e, f, g, h, i, j, k):
  return 0
"""))
        self.check(P.run_compilation, P.frontend, stmt("""
def foo(x):
  def sub(a, b, c, d, e, f, g, h, i, j):
    return a + b + c + d + e + f + g + h + i + j + x 
  return sub(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
"""), P.Compilation(silence=True))
    def testReturn(self):
        self.check(F.return_check, stmt("""
def foo(x):
  y = x
"""))
        self.check(F.return_check, stmt("""
def foo(x):
  if True:
    return x
  else:
    y = x
"""))
        self.check(F.return_check, stmt("""
def foo(x):
  if True:
    y = x
  else:
    return x
"""))
        self.check(F.return_check, stmt("""
def foo(x):
  if True:
    y = x
  else:
    y = x
"""))
    def testBuiltin(self):
        self.check(F.builtin_check, stmt("""
def map(x):
  return x
"""))
        self.check(F.builtin_check, stmt("""
def zip(x):
  return x
"""))
        self.check(F.builtin_check, stmt("""
def op_add(x):
  return x
"""))


        #If this raises an exception, the test will fail
        stmt("""
def foo(x):
  return x
""")
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tail_recursion
from copperhead import *
import unittest

# @cu
# def infinite_loop(val):
#     return infinite_loop(val+1)

# @cu
# def nested_non_tail(val, limit_a, limit_b):
#     if (val < limit_a):
#         if (val < limit_b):
#             return nested_non_tail(val+1, limit_a, limit_b)
#         else:
#             return val
#     else:
#         if (val > limit_b):
#             return val
#         else:
#             return nested_non_tail(val+1, limit_a, limit_b)

# @cu
# def non_tail_recursive(val, limit):
#     if (val < limit):
#         return non_tail_recursive(val, limit) + 1
#     else:
#         return val

#These should all fail
#print(nested_non_tail(0, 1, 2))
#print(infinite_loop(0))
#print(non_tail_recursive(0))


@cu 
def thencount(val, limit):
    if (val < limit):
        return thencount(val+1, limit)
    else:
        return val

@cu
def elsecount(val, limit):
    if (val == limit):
        return val
    else:
        return elsecount(val+1, limit)

@cu
def prethencount(val, limit):
    incval = val + 1
    if (val < limit):
        return prethencount(incval, limit)
    else:
        return val

@cu
def preelsecount(val, limit):
    incval = val + 1
    if (val == limit):
        return val
    else:
        return preelsecount(incval, limit)
    
@cu
def vinc(x, val, limit):
    if (val == limit):
        return x
    else:
        return vinc(map(lambda xi: xi+1, x), val+1, limit)

@cu
def previnc(x, val, limit):
    incval = map(lambda xi:xi+1, x)
    if (val == limit-1):
        return incval
    else:
        return previnc(incval, val+1, limit)
    
@cu
def divergent(limit):
    def divergent_sub(val):
        if (val == limit):
            return val
        else:
            return divergent_sub(val+1)
    return map(divergent_sub, range(limit))

class TailRecursionTest(unittest.TestCase):
    def test_thencount(self):
        self.assertEqual(thencount(0, 10), 10)
    def test_elsecountself(self):
        self.assertEqual(elsecount(0, 10), 10)
    def test_prethencount(self):
        self.assertEqual(prethencount(0, 10), 10)
    def test_preelsecount(self):
        self.assertEqual(preelsecount(0, 10), 10)
    def test_vinc(self):
        self.assertEqual(list(vinc([0,0,0], 0, 5)), [5,5,5])
    def test_previnc(self):
        self.assertEqual(list(previnc([0,0,0], 0, 5)), [5,5,5])
    def test_divergent(self):
        self.assertEqual(list(divergent(5)), [5,5,5,5,5])

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_tuple_data
import unittest
from copperhead import *
from recursive_equal import recursive_equal

class TupleData(unittest.TestCase):
    def testTypeTupleScalars(self):
        source = (1, 2.0)
        result_type, result_value = runtime.driver.induct(source)
        self.assertEqual(repr(result_type), "Tuple(Long, Double)")
    def testTypeTupleSequences(self):
        source = ([1, 2], [3.0, 4.0])
        result_type, result_value = runtime.driver.induct(source)
        self.assertEqual(repr(result_type), "Tuple(Seq(Long), Seq(Double))")
    def testTypeNestedTuple(self):
        source = (1, (2, 3.0, (4.0, 5)), 6.0)
        result_type, result_value = runtime.driver.induct(source)
        self.assertEqual(repr(result_type), "Tuple(Long, Tuple(Long, Double, Tuple(Double, Long)), Double)")

@cu
def test_tuple((m, n), b):
    """Test tuple assembly/disassembly.
    Tuples disassembled in arguments!
    Tuples disassembled in statements!
    Tuples assigned to other tuples!
    Tuples assigned to identifiers!
    Tuples returned!"""

    #tuple = tuple bind
    q, r = m, n
    #tuple pack
    s = q, r
    #tuple unpack
    t, u = s
    o, p = b
    #return tuple
    return t + o, u + p

@cu
def test_tuple_return():
    """Test returning a tuple by identifier"""
    a = 1, 2
    return a

@cu
def test_nested_tuple_return():
    return (1, (2, 3))

@cu
def test_tuple_seq(x, y):
    return x, y

@cu
def test_containerize(x):
    def sub(xi):
        return -xi
    y = map(sub, x)
    z = x, y
    return z

@cu
def test_tuple_seq_args(x):
    y, z = x
    return y, z


class TupleExtract(unittest.TestCase):
    def testTuple(self):
        source_a = (1, 2)
        source_b = (5, 6)
        golden = (6, 8)
        self.assertEqual(test_tuple(source_a, source_b), golden)
    def testNestedTupleReturn(self):
        self.assertTrue(
            recursive_equal(test_nested_tuple_return(), (1, (2, 3))))
    def testTupleReturn(self):
        self.assertEqual(test_tuple_return(), (1, 2))
    def testTupleSeqSeq(self):
        self.assertTrue(recursive_equal(test_tuple_seq([1,2], [3,4]), ([1,2],[3,4])))
    def testTupleSeqScalar(self):
        self.assertTrue(recursive_equal(test_tuple_seq([1,2], 3), ([1,2],3)))
    def testTupleSeqTuple(self):
        self.assertTrue(recursive_equal(test_tuple_seq([1,2], (3,4)), ([1,2],(3,4))))
    def testTupleSeqArgs(self):
        self.assertTrue(recursive_equal(test_tuple_seq_args(([1,2],[3,4])),
                                        ([1,2], [3,4])))
    def testContainerize(self):
        self.assertTrue(recursive_equal(test_containerize([1,2]), ([1,2], [-1,-2])))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_types
#! /usr/bin/env python
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

"""
Simple tests of type primitives.

These tests exercise the coretypes module of the Copperhead compiler.
They do not depend on any other module, but simply check that the core
functionality provided by the types module are functioning correctly.
"""

import unittest

from copperhead.compiler.coretypes import *

class CoretypeTests(unittest.TestCase):

    def setUp(self):
        self.types = \
            [
                Typevar('x'),
                Tuple(Int, Typevar('a'), Bool, Typevar('b')),
                Fn((Int, Typevar('a')), Bool),
                Fn((Int, Typevar('a')), Typevar('b')),
                Polytype(['a', 'b'], Fn((Int, Typevar('a')), Typevar('b'))),
                Polytype(['a', 'b'], Fn((Int, 'a'), 'b')),
                Polytype(['a', 'b'], Fn((Typevar('c'), Typevar('a')), Typevar('b'))),
            ]

        self.strings = \
            [
                'x'                 ,
                '(Int, a, Bool, b)' ,
                '(Int, a) -> Bool'  ,
                '(Int, a) -> b'     ,
                'ForAll a, b: (Int, a) -> b',
                'ForAll a, b: (Int, a) -> b',
                'ForAll a, b: (c, a) -> b',
            ]

        self.occurring = \
            [
                ['x'],
                ['a', 'b'],
                ['a'],
                ['a', 'b'],
                ['a', 'b'],
                ['a', 'b'],
                ['a', 'b', 'c'],
            ]

        self.free = \
            [
                ['x'],
                ['a', 'b'],
                ['a'],
                ['a', 'b'],
                [],
                [],
                ['c'],
            ]

    def tearDown(self): pass

    def testTypevarAsString(self):
        self.assertEqual(Typevar('x'), 'x')
        self.assertEqual(Typevar('aLongTypeVariable'), 'aLongTypeVariable')

    def testTypeStrings(self):
        for t, s in zip(self.types, self.strings):
            self.assertEqual(str(t), s)

    def testOccurringVariables(self):
        for t, vars in zip(self.types, self.occurring):
            names = sorted(list(names_in_type(t)))
            self.assertEqual(names, vars)

    def testFreeVariables(self):
        for t, vars in zip(self.types, self.free):
            names = sorted(list(free_in_type(t)))
            self.assertEqual(names, vars)

    def testOccursCheck(self):
        self.assert_(occurs('a', 'a'))
        self.assert_(not occurs('a', Fn((Int,Int), Bool)))
        self.assert_(not occurs('a', Fn(('b','c'), 'a0')))
        self.assert_(occurs('a', Fn(('b',Seq('a')), 'b')))
        self.assert_(occurs('a', Polytype(['b','a'], Seq(Tuple('a', 'b')))))
        self.assert_(not occurs('a', Polytype(['b','a'], Seq(Int))))


    def testSubstitution(self):
        S = lambda t: substituted_type(t, {'x':'y','z':'u','zz':'v'})

        self.assertEqual(S('x'), 'y')
        self.assertEqual(S('y'), 'y')
        self.assertEqual(str(S(Polytype(['a','b'], Tuple('a','b','c',
            'z')))),
            'ForAll a, b: (a, b, c, u)')



if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_unify
#! /usr/bin/env python
#
#   Copyright 2008-2012 NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#

import unittest

from copperhead.compiler.typeinference import *
from copperhead.compiler.unifier import unify

a, b, c, d = [T.Typevar(v) for v in "abcd"]

int2 = T.Tuple(T.Int, T.Int)


class UnificationTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def succeeds(self, s, t):
        tcon = TypingContext()
        unify(s, t, tcon)

    def fails(self, s, t):
        tcon = TypingContext()
        self.assertRaises(InferenceError, lambda: unify(s, t, tcon))

    def testLiterals(self):
        self.succeeds(T.Int, T.Int)
        self.succeeds(T.Float, T.Float)
        self.fails(T.Int, T.Float)

    def testVars(self):
        self.succeeds(a, T.Int)
        self.succeeds(T.Float, T.Typevar('a'))
        self.succeeds(a, a)
        self.succeeds(a, b)

    def testCombining(self):
        self.succeeds(T.Tuple(T.Int, T.Int), T.Tuple(T.Int, T.Int))
        self.succeeds(T.Tuple(T.Int, T.Int), T.Tuple(a, a))
        self.succeeds(T.Tuple(T.Int, T.Int), T.Tuple(a, b))
        self.fails(T.Tuple(T.Int, T.Int), T.Fn(T.Int, T.Int))


    def testFunctions(self):
        self.succeeds(T.Fn(T.Int, T.Int), T.Fn(T.Int, T.Int)) 
        self.succeeds(T.Fn(T.Int, T.Int), T.Fn([T.Int], T.Int)) 
        self.succeeds(T.Fn(T.Int, T.Int), T.Fn(T.Tuple(T.Int), T.Int)) 

        self.succeeds(T.Fn(T.Int, T.Int), T.Fn(a, a)) 
        self.succeeds(T.Fn(T.Int, T.Int), T.Fn(a, b)) 
        self.succeeds(T.Fn(a, T.Int), T.Fn(T.Int, b)) 


    def testPolytypes(self):
        self.succeeds(T.Polytype([a], T.Tuple(a,a)), int2)
        self.succeeds(T.Polytype(['a'], T.Tuple('a','a')), int2)
        self.succeeds(T.Polytype([a], T.Fn((a,a), a)), T.Fn(int2, T.Int))
        self.fails(T.Polytype([a], T.Fn((a,a), a)), T.Fn(int2, int2))
        self.succeeds(T.Polytype([a], T.Fn((a,a), a)), T.Fn(int2, b))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_update
#
#   Copyright 2012      NVIDIA Corporation
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
# 
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# 
#
from copperhead import *
import numpy as np
import unittest
from create_tests import create_tests

@cu
def test_update(dst, updates):
    return update(dst, updates)

@cu
def test_zip(a, b):
    return zip(a, b)
class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.dest = [1,2,3,4,5]
        update_indices = [0,1,3]
        update_data = [11, 12, 14]
        self.updates = test_zip(update_indices, update_data)
        
    def run_test(self, target, fn, *args):
        
        python_result = fn(*args, target_place=places.here)
        copperhead_result = fn(*args, target_place=target)
        self.assertEqual(list(python_result), list(copperhead_result))
        
    @create_tests(*runtime.backends)
    def testUpdate(self, target):
        self.run_test(target, test_update, self.dest, self.updates)

        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_zip
from copperhead import *
import unittest
from recursive_equal import recursive_equal

@cu
def test_zip(x, y):
    return zip(x, y)

@cu
def test_unzip(x):
    y, z = unzip(x)
    return y, z

@cu
def shift_zip(x, y, z, d):
    a = zip(x, y)
    b = shift(a, d, z)
    return b

class ZipTest(unittest.TestCase):
    def setUp(self):
        self.x = [1,2,3,4,5]
        self.y = [3,4,5,6,7]
    def testZip(self):
        self.assertTrue(
            recursive_equal(test_zip(self.x, self.y),
                            [(1,3),(2,4),(3,5),(4,6),(5,7)]))
    def testShiftZip(self):
        self.assertTrue(
            recursive_equal(shift_zip(self.x, self.y, (-1, -2), 1),
                            [(2, 4), (3, 5), (4, 6), (5, 7), (-1, -2)]))
        self.assertTrue(
            recursive_equal(shift_zip(self.x, self.y, (-3, -4), -1),
                            [(-3, -4), (1, 3), (2, 4), (3, 5), (4, 6)]))
    
    def testUnzip(self):
        self.assertTrue(
            recursive_equal(test_unzip(test_zip(self.x, self.y)),
                            ([1,2,3,4,5],[3,4,5,6,7])))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
