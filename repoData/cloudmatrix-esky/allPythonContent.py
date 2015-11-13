__FILENAME__ = f_bbfreeze
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.bdist_esky.f_bbfreeze:  bdist_esky support for bbfreeze

"""


import os
import sys
import imp
import time
import zipfile
import tempfile
import marshal
import struct
import shutil
import inspect
import zipfile

if sys.platform == "win32":
    from esky import winres


import bbfreeze

import esky
from esky.util import is_core_dependency


def freeze(dist):
    """Freeze the given distribution data using bbfreeze."""
    includes = dist.includes
    excludes = dist.excludes
    options = dist.freezer_options
    #  Merge in any encludes/excludes given in freezer_options
    for inc in options.pop("includes",()):
        includes.append(inc)
    for exc in options.pop("excludes",()):
        excludes.append(exc)
    if "pypy" not in includes and "pypy" not in excludes:
        excludes.append("pypy")
    #  Freeze up the given scripts
    f = bbfreeze.Freezer(dist.freeze_dir,includes=includes,excludes=excludes)
    for (nm,val) in options.iteritems():
        setattr(f,nm,val)
    f.addModule("esky")
    tdir = tempfile.mkdtemp()
    try:
        for exe in dist.get_executables():
            f.addScript(exe.script,gui_only=exe.gui_only)
        if "include_py" not in options:
            f.include_py = False
        if "linkmethod" not in options:
            #  Since we're going to zip it up, the benefits of hard-
            #  or sym-linking the loader exe will mostly be lost.
            f.linkmethod = "loader"
        f()
    finally:
        shutil.rmtree(tdir)
    #  Copy data files into the freeze dir
    for (src,dst) in dist.get_data_files():
        dst = os.path.join(dist.freeze_dir,dst)
        dstdir = os.path.dirname(dst)
        if not os.path.isdir(dstdir):
            dist.mkpath(dstdir)
        dist.copy_file(src,dst)
    #  Copy package data into the library.zip
    lib = zipfile.ZipFile(os.path.join(dist.freeze_dir,"library.zip"),"a")
    for (src,arcnm) in dist.get_package_data():
        lib.write(src,arcnm)
    lib.close()
    #  Create the bootstrap code, using custom code if specified.
    #  For win32 we include a special chainloader that can suck the selected
    #  version into the running process rather than spawn a new proc.
    code_source = ["__name__ = '__main__'"]
    esky_name = dist.distribution.get_name()
    code_source.append("__esky_name__ = %r" % (esky_name,))
    code_source.append(inspect.getsource(esky.bootstrap))
    if dist.compile_bootstrap_exes:
        if sys.platform == "win32":
            #  The pypy-compiled bootstrap exe will try to load a python env
            #  into its own process and run this "take2" code to bootstrap.
            take2_code = code_source[1:]
            take2_code.append(_CUSTOM_WIN32_CHAINLOADER)
            take2_code.append(dist.get_bootstrap_code())
            take2_code = compile("\n".join(take2_code),"<string>","exec")
            take2_code = marshal.dumps(take2_code)
            clscript = "import marshal; "
            clscript += "exec marshal.loads(%r); " % (take2_code,)
            clscript = clscript.replace("%","%%")
            clscript += "chainload(\"%s\")"
            #  Here's the actual source for the compiled bootstrap exe.
            from esky.bdist_esky import pypy_libpython
            code_source.append(inspect.getsource(pypy_libpython))
            code_source.append("_PYPY_CHAINLOADER_SCRIPT = %r" % (clscript,))
            code_source.append(_CUSTOM_PYPY_CHAINLOADER)
        code_source.append(dist.get_bootstrap_code())
        code_source = "\n".join(code_source)
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            bsexe = dist.compile_to_bootstrap_exe(exe,code_source)
            if sys.platform == "win32":
                fexe = os.path.join(dist.freeze_dir,exe.name)
                winres.copy_safe_resources(fexe,bsexe)
        #  We may also need the bundled MSVCRT libs
        if sys.platform == "win32":
            for nm in os.listdir(dist.freeze_dir):
                if is_core_dependency(nm) and nm.startswith("Microsoft"):
                    dist.copy_to_bootstrap_env(nm)
    else:
        if sys.platform == "win32":
            code_source.append(_CUSTOM_WIN32_CHAINLOADER)
        code_source.append(dist.get_bootstrap_code())
        code_source.append("bootstrap()")
        code_source = "\n".join(code_source)
        #  For non-compiled bootstrap exe, store the bootstrapping code
        #  into the library.zip as __main__.
        maincode = imp.get_magic() + struct.pack("<i",0)
        maincode += marshal.dumps(compile(code_source,"__main__.py","exec"))
        #  Create code for a fake esky.bootstrap module
        eskycode = imp.get_magic() + struct.pack("<i",0)
        eskycode += marshal.dumps(compile("","esky/__init__.py","exec"))
        eskybscode = imp.get_magic() + struct.pack("<i",0)
        eskybscode += marshal.dumps(compile("","esky/bootstrap.py","exec"))
        #  Store bootstrap code as __main__ in the bootstrap library.zip.
        #  The frozen library.zip might have the loader prepended to it, but
        #  that gets overwritten here.
        bslib_path = dist.copy_to_bootstrap_env("library.zip")
        bslib = zipfile.PyZipFile(bslib_path,"w",zipfile.ZIP_STORED)
        cdate = (2000,1,1,0,0,0)
        bslib.writestr(zipfile.ZipInfo("__main__.pyc",cdate),maincode)
        bslib.writestr(zipfile.ZipInfo("esky/__init__.pyc",cdate),eskycode)
        bslib.writestr(zipfile.ZipInfo("esky/bootstrap.pyc",cdate),eskybscode)
        bslib.close()
        #  Copy any core dependencies
        if "fcntl" not in sys.builtin_module_names:
            for nm in os.listdir(dist.freeze_dir):
                if nm.startswith("fcntl"):
                    dist.copy_to_bootstrap_env(nm)
        for nm in os.listdir(dist.freeze_dir):
            if is_core_dependency(nm):
                dist.copy_to_bootstrap_env(nm)
        #  Copy the bbfreeze interpreter if necessary
        if f.include_py:
            if sys.platform == "win32":
                dist.copy_to_bootstrap_env("py.exe")
            else:
                dist.copy_to_bootstrap_env("py")
        #  Copy the loader program for each script.
        #  We explicitly strip the loader binaries, in case they were made
        #  by linking to the library.zip.
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            exepath = dist.copy_to_bootstrap_env(exe.name)
            f.stripBinary(exepath)


#  On Windows, execv is flaky and expensive.  If the chainloader is the same
#  python version as the target exe, we can munge sys.path to bootstrap it
#  into the existing process.
_CUSTOM_WIN32_CHAINLOADER = """
_orig_chainload = _chainload
def _chainload(target_dir):
  mydir = dirname(sys.executable)
  pydll = "python%s%s.dll" % sys.version_info[:2]
  if not exists(pathjoin(target_dir,pydll)):
      _orig_chainload(target_dir)
  else:
      sys.bootstrap_executable = sys.executable
      sys.executable = pathjoin(target_dir,basename(sys.executable))
      verify(sys.executable)
      sys.prefix = sys.prefix.replace(mydir,target_dir)
      sys.argv[0] = sys.executable
      for i in xrange(len(sys.path)):
          sys.path[i] = sys.path[i].replace(mydir,target_dir)
      #  If we're in the bootstrap dir, try to chdir into the version dir.
      #  This is sometimes necessary for loading of DLLs by relative path.
      curdir = getcwd()
      if curdir == mydir:
          nt.chdir(target_dir)
      try:
          verify(sys.path[0])
          import zipimport
          importer = zipimport.zipimporter(sys.path[0])
          code = importer.get_code("__main__")
      except ImportError:
          _orig_chainload(target_dir)
      else:
          sys.modules.pop("esky",None)
          sys.modules.pop("esky.bootstrap",None)
          try:
              exec code in {"__name__":"__main__"}
          except zipimport.ZipImportError, e:
              #  If it can't find the __main__{sys.executable} script,
              #  the user might be running from a backup exe file.
              #  Fall back to original chainloader to attempt workaround.
              if e.message.startswith("can't find module '__main__"):
                  _orig_chainload(target_dir)
              raise
          sys.exit(0)
"""

#  On Windows, execv is flaky and expensive.  Since the pypy-compiled bootstrap
#  exe doesn't have a python runtime, it needs to chainload the one from the
#  target version dir before trying to bootstrap in-process.
_CUSTOM_PYPY_CHAINLOADER = """

_orig_chainload = _chainload
def _chainload(target_dir):
  mydir = dirname(sys.executable)
  pydll = pathjoin(target_dir,"python%s%s.dll" % sys.version_info[:2])
  if not exists(pydll):
      _orig_chainload(target_dir)
  else:
      py = libpython(pydll)


      py.Set_NoSiteFlag(1)
      py.Set_FrozenFlag(1)
      py.Set_IgnoreEnvironmentFlag(1)

      py.SetPythonHome("")
      py.Initialize()
      # TODO: can't get this through pypy's type annotator.
      # going to fudge it in python instead :-)
      #py.Sys_SetArgv(list(sys.argv))
      syspath = dirname(py.GetProgramFullPath());
      syspath = syspath + "\\library.zip;" + syspath
      py.Sys_SetPath(syspath);
      #  Escape any double-quotes in sys.argv, so we can easily
      #  include it in a python-level string.
      new_argvs = []
      for arg in sys.argv:
          new_argvs.append('"' + arg.replace('"','\\"') + '"')
      new_argv = "[" + ",".join(new_argvs) + "]"
      py.Run_SimpleString("import sys; sys.argv = %s" % (new_argv,))
      py.Run_SimpleString("import sys; sys.frozen = 'bbfreeze'" % (new_argv,))
      globals = py.Dict_New()
      py.Dict_SetItemString(globals,"__builtins__",py.Eval_GetBuiltins())
      esc_target_dir_chars = []
      for c in target_dir:
          if c == "\\\\":
              esc_target_dir_chars.append("\\\\")
          esc_target_dir_chars.append(c)
      esc_target_dir = "".join(esc_target_dir_chars)
      script = _PYPY_CHAINLOADER_SCRIPT % (esc_target_dir,)
      py.Run_String(script,py.file_input,globals)
      py.Finalize()
      sys.exit(0)

"""

########NEW FILE########
__FILENAME__ = f_cxfreeze
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.bdist_esky.f_cxfreeze:  bdist_esky support for cx_Freeze

"""


import os
import sys
import imp
import time
import zipfile
import marshal
import struct
import shutil
import inspect
import zipfile
import distutils

if sys.platform == "win32":
    from esky import winres


import cx_Freeze
import cx_Freeze.hooks
INITNAME = "cx_Freeze__init__"

import esky
from esky.util import is_core_dependency


def freeze(dist):
    """Freeze the given distribution data using cx_Freeze."""
    includes = dist.includes
    excludes = dist.excludes
    options = dist.freezer_options
    #  Merge in any encludes/excludes given in freezer_options
    for inc in options.pop("includes",()):
        includes.append(inc)
    for exc in options.pop("excludes",()):
        excludes.append(exc)
    if "esky" not in includes and "esky" not in excludes:
        includes.append("esky")
    if "pypy" not in includes and "pypy" not in excludes:
        excludes.append("pypy")
    #  cx_Freeze doesn't seem to respect __path__ properly; hack it so
    #  that the required distutils modules are always found correctly.
    def load_distutils(finder,module):
        module.path = distutils.__path__ + module.path
        finder.IncludeModule("distutils.dist")
    cx_Freeze.hooks.load_distutils = load_distutils
    #  Build kwds arguments out of the given freezer opts.
    kwds = {}
    for (nm,val) in options.iteritems():
        kwds[_normalise_opt_name(nm)] = val
    kwds["includes"] = includes
    kwds["excludes"] = excludes
    kwds["targetDir"] = dist.freeze_dir
    #  Build an Executable object for each script.
    #  To include the esky startup code, we write each to a tempdir.
    executables = []
    for exe in dist.get_executables():
        base = None
        if exe.gui_only and sys.platform == "win32":
            base = "Win32GUI"
        executables.append(cx_Freeze.Executable(exe.script,base=base,targetName=exe.name,icon=exe.icon,**exe._kwds))
    #  Freeze up the executables
    f = cx_Freeze.Freezer(executables,**kwds)
    f.Freeze()
    #  Copy data files into the freeze dir
    for (src,dst) in dist.get_data_files():
        dst = os.path.join(dist.freeze_dir,dst)
        dstdir = os.path.dirname(dst)
        if not os.path.isdir(dstdir):
            dist.mkpath(dstdir)
        dist.copy_file(src,dst)
    #  Copy package data into the library.zip
    #  For now, this only works if there's a shared "library.zip" file.
    if f.createLibraryZip:
        lib = zipfile.ZipFile(os.path.join(dist.freeze_dir,"library.zip"),"a")
        for (src,arcnm) in dist.get_package_data():
            lib.write(src,arcnm)
        lib.close()
    else:
        for (src,arcnm) in dist.get_package_data():
            err = "use of package_data currently requires createLibraryZip=True"
            raise RuntimeError(err)
    #  Create the bootstrap code, using custom code if specified.
    code_source = ["__name__ = '__main__'"]
    esky_name = dist.distribution.get_name()
    code_source.append("__esky_name__ = %r" % (esky_name,))
    code_source.append(inspect.getsource(esky.bootstrap))
    if dist.compile_bootstrap_exes:
        if sys.platform == "win32":
            #  Unfortunately this doesn't work, because the cxfreeze exe
            #  contains frozen modules that are inaccessible to a bootstrapped
            #  interpreter.  Disabled until I figure out a workaround. :-(
            pass
            #  The pypy-compiled bootstrap exe will try to load a python env
            #  into its own process and run this "take2" code to bootstrap.
            #take2_code = code_source[1:]
            #take2_code.append(_CUSTOM_WIN32_CHAINLOADER)
            #take2_code.append(dist.get_bootstrap_code())
            #take2_code = compile("\n".join(take2_code),"<string>","exec")
            #take2_code = marshal.dumps(take2_code)
            #clscript = "import marshal; "
            #clscript += "exec marshal.loads(%r); " % (take2_code,)
            #clscript = clscript.replace("%","%%")
            #clscript += "chainload(\"%s\")"
            #  Here's the actual source for the compiled bootstrap exe.
            #from esky.bdist_esky import pypy_libpython
            #code_source.append(inspect.getsource(pypy_libpython))
            #code_source.append("_PYPY_CHAINLOADER_SCRIPT = %r" % (clscript,))
            #code_source.append(_CUSTOM_PYPY_CHAINLOADER)
        code_source.append(dist.get_bootstrap_code())
        code_source = "\n".join(code_source)
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            bsexe = dist.compile_to_bootstrap_exe(exe,code_source)
            if sys.platform == "win32":
                fexe = os.path.join(dist.freeze_dir,exe.name)
                winres.copy_safe_resources(fexe,bsexe)
    else:
        if sys.platform == "win32":
            code_source.append(_CUSTOM_WIN32_CHAINLOADER)
        code_source.append(dist.get_bootstrap_code())
        code_source.append("bootstrap()")
        code_source = "\n".join(code_source)
        
        #  Since Python 3.3 the .pyc file format contains the source size.
        #  It's not used for anything at all except to check if the file is up to date.
        #  We can set this value to zero to make Esky also work for Python 3.3
        if sys.version_info[:2] < (3, 3):
            maincode = imp.get_magic() + struct.pack("<i",0)
            eskycode = imp.get_magic() + struct.pack("<i",0)
            eskybscode = imp.get_magic() + struct.pack("<i",0)
        else:
            maincode = imp.get_magic() + struct.pack("<ii",0,0)
            eskycode = imp.get_magic() + struct.pack("<ii",0,0)
            eskybscode = eskycode = imp.get_magic() + struct.pack("<ii",0,0)
        
        maincode += marshal.dumps(compile(code_source,INITNAME+".py","exec"))    
        eskycode += marshal.dumps(compile("","esky/__init__.py","exec"))
        eskybscode += marshal.dumps(compile("","esky/bootstrap.py","exec"))
        
        #  Copy any core dependencies
        if "fcntl" not in sys.builtin_module_names:
            for nm in os.listdir(dist.freeze_dir):
                if nm.startswith("fcntl"):
                    dist.copy_to_bootstrap_env(nm)
        for nm in os.listdir(dist.freeze_dir):
            if is_core_dependency(nm):
                dist.copy_to_bootstrap_env(nm)
                
        #  Copy the loader program for each script into the bootstrap env, and
        #  append the bootstrapping code to it as a zipfile.
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            
            exepath = dist.copy_to_bootstrap_env(exe.name)
            if not dist.detached_bootstrap_library:
                #append library to the bootstrap exe.
                exepath = dist.copy_to_bootstrap_env(exe.name)
                bslib = zipfile.PyZipFile(exepath,"a",zipfile.ZIP_STORED)
            else:
                #Create a separate library.zip for the bootstrap exe.
                bslib_path = dist.copy_to_bootstrap_env("library.zip")
                bslib = zipfile.PyZipFile(bslib_path,"w",zipfile.ZIP_STORED)
            cdate = (2000,1,1,0,0,0)
            bslib.writestr(zipfile.ZipInfo(INITNAME+".pyc",cdate),maincode)
            bslib.writestr(zipfile.ZipInfo("esky/__init__.pyc",cdate),eskycode)
            bslib.writestr(zipfile.ZipInfo("esky/bootstrap.pyc",cdate),eskybscode)
            bslib.close()


def _normalise_opt_name(nm):
    """Normalise option names for cx_Freeze.

    This allows people to specify options named like "opt-name" and have
    them converted to the "optName" format used internally by cx_Freeze.
    """
    bits = nm.split("-")
    for i in xrange(1,len(bits)):
        if bits[i]:
            bits[i] = bits[i][0].upper() + bits[i][1:]
    return "".join(bits)


#  On Windows, execv is flaky and expensive.  If the chainloader is the same
#  python version as the target exe, we can munge sys.path to bootstrap it
#  into the existing process.
if sys.version_info[0] < 3:
    EXEC_STATEMENT = "exec code in globals()"
else:
    EXEC_STATEMENT = "exec(code,globals())"

_CUSTOM_WIN32_CHAINLOADER = """

_orig_chainload = _chainload
def _chainload(target_dir):
  mydir = dirname(sys.executable)
  pydll = "python%%s%%s.dll" %% sys.version_info[:2]
  if not exists(pathjoin(target_dir,pydll)):
      _orig_chainload(target_dir)
  else:
      sys.bootstrap_executable = sys.executable
      sys.executable = pathjoin(target_dir,basename(sys.executable))
      verify(sys.executable)
      sys.prefix = sys.prefix.replace(mydir,target_dir)
      sys.argv[0] = sys.executable
      for i in range(len(sys.path)):
          sys.path[i] = sys.path[i].replace(mydir,target_dir)
      #  If we're in the bootstrap dir, try to chdir into the version dir.
      #  This is sometimes necessary for loading of DLLs by relative path.
      curdir = getcwd()
      if curdir == mydir:
          nt.chdir(target_dir)
      import zipimport
      for init_path in sys.path:
          verify(init_path)
          try:
              importer = zipimport.zipimporter(init_path)
              code = importer.get_code("%s")
          except ImportError:
              pass
          else:
              sys.modules.pop("esky",None)
              sys.modules.pop("esky.bootstrap",None)
              #  Adjust various cxfreeze global vars
              global DIR_NAME, FILE_NAME, EXCLUSIVE_ZIP_FILE_NAME
              global SHARED_ZIP_FILE_NAME, INITSCRIPT_ZIP_FILE_NAME
              # TODO: are these derivations correct?
              FILE_NAME = sys.executable
              DIR_NAME = dirname(sys.executable)
              if FILE_NAME.endswith(".exe"):
                  EXCLUSIVE_ZIP_FILE_NAME = pathjoin(DIR_NAME,basename(FILE_NAME)[:-4]+".zip")
              else:
                  EXCLUSIVE_ZIP_FILE_NAME = pathjoin(DIR_NAME,basename(FILE_NAME)+".zip")
              SHARED_ZIP_FILE_NAME = pathjoin(DIR_NAME,"library.zip")
              INITSCRIPT_ZIP_FILE_NAME = init_path
              try:
                  %s
              except zipimport.ZipImportError:
                  e = sys.exc_info()[1]
                  #  If it can't find the __main__{sys.executable} script,
                  #  the user might be running from a backup exe file.
                  #  Fall back to original chainloader to attempt workaround.
                  if e.message.endswith("__main__'"):
                      _orig_chainload(target_dir)
                  raise
              sys.exit(0)
      else:
          _orig_chainload(target_dir)
""" % (INITNAME,EXEC_STATEMENT)


#  On Windows, execv is flaky and expensive.  Since the pypy-compiled bootstrap
#  exe doesn't have a python runtime, it needs to chainload the one from the
#  target version dir before trying to bootstrap in-process.
_CUSTOM_PYPY_CHAINLOADER = """

_orig_chainload = _chainload
def _chainload(target_dir):
  mydir = dirname(sys.executable)
  pydll = "python%s%s.dll" % sys.version_info[:2]
  if not exists(pathjoin(target_dir,pydll)):
      _orig_chainload(target_dir)
  else:
      py = libpython(pydll)

      #Py_NoSiteFlag = 1;
      #Py_FrozenFlag = 1;
      #Py_IgnoreEnvironmentFlag = 1;

      py.SetPythonHome("")
      py.Initialize()
      # TODO: can't get this through pypy's type annotator.
      # going to fudge it in python instead :-)
      #py.Sys_SetArgv(list(sys.argv))
      syspath = py.GetProgramFullPath() + ";"
      sysfilenm = basename(py.GetProgramFullPath())
      i = 0
      while i < len(sysfilenm) and sysfilenm[i:] != ".exe":
          i += 1
      sysfilenm = sysfilenm[:i]
      sysdir = dirname(py.GetProgramFullPath())
      syspath += sysdir + "\\%s.zip;" % (sysfilenm,)
      syspath += sysdir + "\\library.zip;"
      syspath += sysdir
      py.Sys_SetPath(syspath);
      #  Escape any double-quotes in sys.argv, so we can easily
      #  include it in a python-level string.
      new_argvs = []
      for arg in sys.argv:
          new_argvs.append('"' + arg.replace('"','\\"') + '"')
      new_argv = "[" + ",".join(new_argvs) + "]"
      py.Run_SimpleString("import sys; sys.argv = %s" % (new_argv,))
      py.Run_SimpleString("import sys; sys.frozen = 'cxfreeze'" % (new_argv,))
      globals = py.Dict_New()
      py.Dict_SetItemString(globals,"__builtins__",py.Eval_GetBuiltins())
      esc_target_dir_chars = []
      for c in target_dir:
          if c == "\\\\":
              esc_target_dir_chars.append("\\\\")
          esc_target_dir_chars.append(c)
      esc_target_dir = "".join(esc_target_dir_chars)
      script = _PYPY_CHAINLOADER_SCRIPT % (esc_target_dir,)
      py.Run_String(script,py.file_input,globals)
      py.Finalize()
      sys.exit(0)

"""



########NEW FILE########
__FILENAME__ = f_py2app
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.bdist_esky.f_py2app:  bdist_esky support for py2app

"""

from __future__ import with_statement


import os
import sys
import imp
import time
import errno
import zipfile
import shutil
import tempfile
import inspect
import struct
import marshal
from StringIO import StringIO


from py2app.build_app import py2app, get_zipfile, Target

import esky
from esky.util import is_core_dependency, create_zipfile


def freeze(dist):
    """Freeze the given distribution data using py2app."""
    includes = dist.includes
    excludes = dist.excludes
    options = dist.freezer_options
    #  Merge in any includes/excludes given in freezer_options
    includes.append("esky")
    for inc in options.pop("includes",()):
        includes.append(inc)
    for exc in options.pop("excludes",()):
        excludes.append(exc)
    if "pypy" not in includes and "pypy" not in excludes:
        excludes.append("pypy")
    options["includes"] = includes
    options["excludes"] = excludes
    # The control info (name, icon, etc) for the app will be taken from
    # the first script in the list.  Subsequent scripts will be passed
    # as the extra_scripts argument.
    exes = list(dist.get_executables())
    if not exes:
        raise RuntimeError("no scripts specified")
    cmd = _make_py2app_cmd(dist.freeze_dir,dist.distribution,options,exes)
    cmd.run()
    #  Remove any .pyc files with a corresponding .py file.
    #  This helps avoid timestamp changes that might interfere with
    #  the generation of useful patches between versions.
    appnm = dist.distribution.get_name()+".app"
    app_dir = os.path.join(dist.freeze_dir,appnm)
    resdir = os.path.join(app_dir,"Contents/Resources")
    for (dirnm,_,filenms) in os.walk(resdir):
        for nm in filenms:
            if nm.endswith(".pyc"):
                pyfile = os.path.join(dirnm,nm[:-1])
                if os.path.exists(pyfile):
                    os.unlink(pyfile+"c")
            if nm.endswith(".pyo"):
                pyfile = os.path.join(dirnm,nm[:-1])
                if os.path.exists(pyfile):
                    os.unlink(pyfile+"o")
    #  Copy data files into the freeze dir
    for (src,dst) in dist.get_data_files():
        dst = os.path.join(app_dir,"Contents","Resources",dst)
        dstdir = os.path.dirname(dst)
        if not os.path.isdir(dstdir):
            dist.mkpath(dstdir)
        dist.copy_file(src,dst)
    #  Copy package data into site-packages.zip
    zfpath = os.path.join(cmd.lib_dir,get_zipfile(dist.distribution))
    lib = zipfile.ZipFile(zfpath,"a")
    for (src,arcnm) in dist.get_package_data():
        lib.write(src,arcnm)
    lib.close()
    #  Create the bootstraping code, using custom code if specified.
    esky_name = dist.distribution.get_name()
    code_source = ["__esky_name__ = %r" % (esky_name,)]
    code_source.append(inspect.getsource(esky.bootstrap))
    if not dist.compile_bootstrap_exes:
        code_source.append(_FAKE_ESKY_BOOTSTRAP_MODULE)
        code_source.append(_EXTRA_BOOTSTRAP_CODE)
    code_source.append(dist.get_bootstrap_code())
    code_source.append("if not __rpython__:")
    code_source.append("    bootstrap()")
    code_source = "\n".join(code_source)
    def copy_to_bootstrap_env(src,dst=None):
        if dst is None:
            dst = src
        src = os.path.join(appnm,src)
        dist.copy_to_bootstrap_env(src,dst)
    if dist.compile_bootstrap_exes:
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            relpath = os.path.join("Contents","MacOS",exe.name)
            dist.compile_to_bootstrap_exe(exe,code_source,relpath)
    else:
        #  Copy the core dependencies into the bootstrap env.
        pydir = "python%d.%d" % sys.version_info[:2]
        for nm in ("Python.framework","lib"+pydir+".dylib",):
            try:
                copy_to_bootstrap_env("Contents/Frameworks/" + nm)
            except Exception, e:
                #  Distutils does its own crazy exception-raising which I
                #  have no interest in examining right now.  Eventually this
                #  guard will be more conservative.
                pass
        copy_to_bootstrap_env("Contents/Resources/include")
        copy_to_bootstrap_env("Contents/Resources/lib/"+pydir+"/config")
        if "fcntl" not in sys.builtin_module_names:
            dynload = "Contents/Resources/lib/"+pydir+"/lib-dynload"
            for nm in os.listdir(os.path.join(app_dir,dynload)):
                if nm.startswith("fcntl"):
                    copy_to_bootstrap_env(os.path.join(dynload,nm))
        copy_to_bootstrap_env("Contents/Resources/__error__.sh")
        # Copy site.py/site.pyc into the boostrap env, then zero them out.
        bsdir = dist.bootstrap_dir
        if os.path.exists(os.path.join(app_dir, "Contents/Resources/site.py")):
            copy_to_bootstrap_env("Contents/Resources/site.py")
            with open(bsdir + "/Contents/Resources/site.py", "wt") as f:
                pass
        if os.path.exists(os.path.join(app_dir, "Contents/Resources/site.pyc")):
            copy_to_bootstrap_env("Contents/Resources/site.pyc")
            with open(bsdir + "/Contents/Resources/site.pyc", "wb") as f:
                f.write(imp.get_magic() + struct.pack("<i", 0))
                f.write(marshal.dumps(compile("", "site.py", "exec")))
        if os.path.exists(os.path.join(app_dir, "Contents/Resources/site.pyo")):
            copy_to_bootstrap_env("Contents/Resources/site.pyo")
            with open(bsdir + "/Contents/Resources/site.pyo", "wb") as f:
                f.write(imp.get_magic() + struct.pack("<i", 0))
        #  Copy the bootstrapping code into the __boot__.py file.
        copy_to_bootstrap_env("Contents/Resources/__boot__.py")
        with open(bsdir+"/Contents/Resources/__boot__.py","wt") as f:
            f.write(code_source)
        #  Copy the loader program for each script into the bootstrap env.
        copy_to_bootstrap_env("Contents/MacOS/python")
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            exepath = copy_to_bootstrap_env("Contents/MacOS/"+exe.name)
    #  Copy non-python resources (e.g. icons etc) into the bootstrap dir
    copy_to_bootstrap_env("Contents/Info.plist")
    # Include Icon
    if exe.icon is not None:
        copy_to_bootstrap_env("Contents/Resources/"+exe.icon)
    copy_to_bootstrap_env("Contents/PkgInfo")
    with open(os.path.join(app_dir,"Contents","Info.plist"),"rt") as f:
        infotxt = f.read()
    for nm in os.listdir(os.path.join(app_dir,"Contents","Resources")):
        if "<string>%s</string>" % (nm,) in infotxt:
            copy_to_bootstrap_env("Contents/Resources/"+nm)



def zipit(dist,bsdir,zfname):
    """Create the final zipfile of the esky.

    We customize this process for py2app, so that the zipfile contains a
    toplevel "<appname>.app" directory.  This allows users to just extract
    the zipfile and have a proper application all set up and working.
    """
    def get_arcname(fpath):
        return os.path.join(dist.distribution.get_name()+".app",fpath)
    return create_zipfile(bsdir,zfname,get_arcname,compress=True)


def _make_py2app_cmd(dist_dir,distribution,options,exes):
    exe = exes[0]
    extra_exes = exes[1:]
    cmd = py2app(distribution)
    for (nm,val) in options.iteritems():
        setattr(cmd,nm,val)
    cmd.dist_dir = dist_dir
    cmd.app = [Target(script=exe.script,dest_base=exe.name)]
    cmd.extra_scripts = [e.script for e in extra_exes]
    cmd.finalize_options()
    cmd.plist["CFBundleExecutable"] = exe.name
    old_run = cmd.run
    def new_run():
        #  py2app munges the environment in ways that break things.
        old_deployment_target = os.environ.get("MACOSX_DEPLOYMENT_TARGET",None)
        old_run()
        if old_deployment_target is None:
            os.environ.pop("MACOSX_DEPLOYMENT_TARGET",None)
        else:
            os.environ["MACOSX_DEPLOYMENT_TARGET"] = old_deployment_target
        #  We need to script file to have the same name as the exe, which
        #  it won't if they have changed it explicitly.
        resdir = os.path.join(dist_dir,distribution.get_name()+".app","Contents/Resources")
        scriptf = os.path.join(resdir,exe.name+".py")
        if not os.path.exists(scriptf):
           old_scriptf = os.path.basename(exe.script)
           old_scriptf = os.path.join(resdir,old_scriptf)
           shutil.move(old_scriptf,scriptf)
    cmd.run = new_run
    return cmd


#  Code to fake out any bootstrappers that try to import from esky.
_FAKE_ESKY_BOOTSTRAP_MODULE = """
class __fake:
  __all__ = ()
sys.modules["esky"] = __fake()
sys.modules["esky.bootstrap"] = __fake()
"""

#  py2app goes out of its way to set sys.executable to a normal python
#  interpreter, which will break the standard bootstrapping code.
#  Get the original value back.
_EXTRA_BOOTSTRAP_CODE = """
from posix import environ
sys.executable = environ["EXECUTABLEPATH"]
sys.argv[0] = environ["ARGVZERO"]
"""

########NEW FILE########
__FILENAME__ = f_py2exe
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.bdist_esky.f_py2exe:  bdist_esky support for py2exe

"""

from __future__ import with_statement


import os
import sys
import imp
import time
import zipfile
import marshal
import struct
import shutil
import inspect
import zipfile
import ctypes


from py2exe.build_exe import py2exe

import esky
from esky.util import is_core_dependency, ESKY_CONTROL_DIR
from esky import winres

try:
    import py2exe.mf as modulefinder
except ImportError:
    modulefinder = None

#  Hack to make win32com work seamlessly with py2exe
if modulefinder is not None:
  try:
    import win32com
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    for extra in ["win32com.shell"]: #,"win32com.mapi"
        __import__(extra)
        m = sys.modules[extra]
        for p in m.__path__[1:]:
           modulefinder.AddPackagePath(extra, p)
  except ImportError:
     pass


class custom_py2exe(py2exe): 
    """Custom py2exe command subclass.

    This py2exe command subclass incorporates some well-known py2exe "hacks"
    to make common third-party packages work better.
    """

    def create_modulefinder(self):
        mf = py2exe.create_modulefinder(self)
        self.__mf = mf
        return mf

    def build_manifest(self,target,template):
        (mfest,mid) = py2exe.build_manifest(self,target,template)
        #  Hack to get proper UI theme when freezing wxPython
        if mfest is not None:
            if "wx" in self.__mf.modules:
                mfest = mfest.replace("</assembly>","""
                    <dependency>
                      <dependentAssembly>
                        <assemblyIdentity
                         type="win32"
                         name="Microsoft.Windows.Common-Controls"
                         version="6.0.0.0"
                         processorArchitecture="*"
                         publicKeyToken="6595b64144ccf1df"
                         language="*" />
                      </dependentAssembly>
                   </dependency>
                 </assembly>""")
        return (mfest,mid)


def freeze(dist):
    """Freeze the given distribution data using py2exe."""
    includes = dist.includes
    excludes = dist.excludes
    options = dist.freezer_options
    #  Merge in any encludes/excludes given in freezer_options
    includes.append("esky")
    for inc in options.pop("includes",()):
        includes.append(inc)
    for exc in options.pop("excludes",()):
        excludes.append(exc)
    if "pypy" not in includes and "pypy" not in excludes:
        excludes.append("pypy")
    #  py2exe expects some arguments on the main distribution object.
    #  We handle data_files ourselves, so fake it out for py2exe.
    if getattr(dist.distribution,"console",None):
        msg = "don't call setup(console=[...]) with esky;"
        msg += " use setup(scripts=[...]) instead"
        raise RuntimeError(msg)
    if getattr(dist.distribution,"windows",None):
        msg = "don't call setup(windows=[...]) with esky;"
        msg += " use setup(scripts=[...]) instead"
        raise RuntimeError(msg)
    dist.distribution.console = []
    dist.distribution.windows = []
    my_data_files = dist.distribution.data_files
    dist.distribution.data_files = []
    for exe in dist.get_executables():
        #  Pass any executable kwds through to py2exe.
        #  We handle "icon" and "gui_only" ourselves.
        s = exe._kwds.copy()
        s["script"] = exe.script
        s["dest_base"] = exe.name[:-4]
        if exe.icon is not None and "icon_resources" not in s:
            s["icon_resources"] = [(1,exe.icon)]
        if exe.gui_only:
            dist.distribution.windows.append(s)
        else:
            dist.distribution.console.append(s)
    if "zipfile" in options:
        dist.distribution.zipfile = options.pop("zipfile")
    #  Create the py2exe cmd and adjust its options
    cmd = custom_py2exe(dist.distribution)
    cmd.includes = includes
    cmd.excludes = excludes
    if "bundle_files" in options:
        if options["bundle_files"] < 3 and dist.compile_bootstrap_exes:
             err = "can't compile bootstrap exes when bundle_files < 3"
             raise RuntimeError(err)
    for (nm,val) in options.iteritems():
        setattr(cmd,nm,val)
    cmd.dist_dir = dist.freeze_dir
    cmd.finalize_options()
    #  Actually run the freeze process
    cmd.run()
    #  Copy data files into the freeze dir
    dist.distribution.data_files = my_data_files
    for (src,dst) in dist.get_data_files():
        dst = os.path.join(dist.freeze_dir,dst)
        dstdir = os.path.dirname(dst)
        if not os.path.isdir(dstdir):
            dist.mkpath(dstdir)
        dist.copy_file(src,dst)
    #  Place a marker file so we know how it was frozen
    os.mkdir(os.path.join(dist.freeze_dir,ESKY_CONTROL_DIR))
    marker_file = os.path.join(ESKY_CONTROL_DIR,"f-py2exe-%d%d.txt")%sys.version_info[:2]
    open(os.path.join(dist.freeze_dir,marker_file),"w").close()
    #  Copy package data into the library.zip
    #  For now, we don't try to put package data into a bundled zipfile.
    dist_zipfile = dist.distribution.zipfile
    if dist_zipfile is None:
        for (src,arcnm) in dist.get_package_data():
            err = "zipfile=None can't be used with package_data (yet...)"
            raise RuntimeError(err)
    elif not cmd.skip_archive:
        lib = zipfile.ZipFile(os.path.join(dist.freeze_dir,dist_zipfile),"a")
        for (src,arcnm) in dist.get_package_data():
            lib.write(src,arcnm)
        lib.close()
    else:
        for (src,arcnm) in dist.get_package_data():
            lib = os.path.join(dist.freeze_dir,os.path.dirname(dist_zipfile))
            dest = os.path.join(lib, os.path.dirname(src))
            f = os.path.basename(src)
            if not os.path.isdir(dest):
                dist.mkpath(dest)
            dist.copy_file(src,os.path.join(dest, f))
    #  There's no need to copy library.zip into the bootstrap env, as the
    #  chainloader will run before py2exe goes looking for it.
    pass
    #  Create the bootstraping code, using custom code if specified.
    #  It gets stored as a marshalled list of code objects directly in the exe.
    esky_name = dist.distribution.get_name()
    code_source = ["__esky_name__ = %r" % (esky_name,)]
    code_source.append(inspect.getsource(esky.bootstrap))
    if dist.compile_bootstrap_exes:
        from esky.bdist_esky import pypy_libpython
        from esky.bdist_esky import pypy_winres
        code_source.append(inspect.getsource(pypy_libpython))
        code_source.append(inspect.getsource(pypy_winres))
        code_source.append(_CUSTOM_PYPY_CHAINLOADER)
        code_source.append(dist.get_bootstrap_code())
        code_source = "\n".join(code_source)
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            fexe = os.path.join(dist.freeze_dir,exe.name)
            bsexe = dist.compile_to_bootstrap_exe(exe,code_source)
            winres.copy_safe_resources(fexe,bsexe)
        #  We may also need the bundled MSVCRT libs
        for nm in os.listdir(dist.freeze_dir):
            if is_core_dependency(nm) and nm.startswith("Microsoft"):
                dist.copy_to_bootstrap_env(nm)
    else:
        code_source.append(_FAKE_ESKY_BOOTSTRAP_MODULE)
        code_source.append(_CUSTOM_WIN32_CHAINLOADER)
        code_source.append(dist.get_bootstrap_code())
        code_source.append("bootstrap()")
        code_source = "\n".join(code_source)
        code = marshal.dumps([compile(code_source,"__main__.py","exec")])
        #  Copy any core dependencies into the bootstrap env.
        for nm in os.listdir(dist.freeze_dir):
            if is_core_dependency(nm):
                dist.copy_to_bootstrap_env(nm)
        #  Copy the loader program for each script into the bootstrap env.
        for exe in dist.get_executables(normalise=False):
            if not exe.include_in_bootstrap_env:
                continue
            exepath = dist.copy_to_bootstrap_env(exe.name)
            #  Read the py2exe metadata from the frozen exe.  We will
            #  need to duplicate some of these fields when to rewrite it.
            coderes = winres.load_resource(exepath,u"PYTHONSCRIPT",1,0)
            headsz = struct.calcsize("iiii")
            (magic,optmz,unbfrd,codesz) = struct.unpack("iiii",coderes[:headsz])
            assert magic == 0x78563412
            #  Insert the bootstrap code into the exe as a resource.
            #  This appears to have the happy side-effect of stripping any
            #  extra data from the end of the exe, which is exactly what we
            #  want when zipfile=None is specified; otherwise each bootstrap
            #  exe would also contain the whole bundled zipfile.
            coderes = struct.pack("iiii",
                         magic, # magic value used for integrity checking,
                         optmz, # optimization level to enable
                         unbfrd,  # whether to use unbuffered output
                         len(code),
                      ) + "\x00" + code + "\x00\x00"
            winres.add_resource(exepath,coderes,u"PYTHONSCRIPT",1,0)
        #  If the python dll hasn't been copied into the bootstrap env,
        #  make sure it's stored in each bootstrap dll as a resource.
        pydll = u"python%d%d.dll" % sys.version_info[:2]
        if not os.path.exists(os.path.join(dist.bootstrap_dir,pydll)):
            buf = ctypes.create_string_buffer(3000)
            GetModuleFileNameA = ctypes.windll.kernel32.GetModuleFileNameA
            if not GetModuleFileNameA(sys.dllhandle,ctypes.byref(buf),3000):
                raise ctypes.WinError()
            with open(buf.value,"rb") as f:
                pydll_bytes = f.read()
            for exe in dist.get_executables(normalise=False):
                if not exe.include_in_bootstrap_env:
                    continue
                exepath = os.path.join(dist.bootstrap_dir,exe.name)
                try:
                    winres.load_resource(exepath,pydll.upper(),1,0)
                except EnvironmentError:
                    winres.add_resource(exepath,pydll_bytes,pydll.upper(),1,0)

#  Code to fake out any bootstrappers that try to import from esky.
_FAKE_ESKY_BOOTSTRAP_MODULE = """
class __fake:
  __all__ = ()
sys.modules["esky"] = __fake()
sys.modules["esky.bootstrap"] = __fake()
"""


#  On Windows, execv is flaky and expensive.  If the chainloader is the same
#  python version as the target exe, we can munge sys.path to bootstrap it
#  into the existing process.
#
#  We need to read the script to execute as a resource from the exe, so this
#  only works if we can bootstrap a working ctypes module.  We then insert
#  the source code from esky.winres.load_resource directly into this function.
#
_CUSTOM_WIN32_CHAINLOADER = """

_orig_chainload = _chainload

def _chainload(target_dir):
  # Be careful to escape percent-sign, this gets interpolated below
  marker_file = pathjoin(ESKY_CONTROL_DIR,"f-py2exe-%%d%%d.txt")%%sys.version_info[:2]
  pydll = "python%%s%%s.dll" %% sys.version_info[:2]
  mydir = dirname(sys.executable)
  #  Check that the target directory is the same version of python as this
  #  bootstrapping script.  If not, we can't chainload it in-process.
  if not exists(pathjoin(target_dir,marker_file)):
      return _orig_chainload(target_dir)
  #  Check whether the target directory contains unbundled C extensions.
  #  These require a physical python dll on disk next to the running
  #  executable, so we must have such a dll in order to chainload.
  #  bootstrapping script.  If not, we can't chainload it in-process.
  for nm in listdir(target_dir):
      if nm == pydll:
          continue
      if nm.lower().startswith("msvcr"):
          continue
      if nm.lower().endswith(".pyd") or nm.lower().endswith(".dll"):
          #  The freeze dir contains unbundled C extensions.
          if not exists(pathjoin(mydir,pydll)):
              return _orig_chainload(target_dir)
          else:
               break
  # Munge the environment to pretend we're in the target dir.
  # This will let us load modules from inside it.
  # If we fail for whatever reason, we can't chainload in-process.
  try:
      import nt
  except ImportError:
      return _orig_chainload(target_dir)
  sys.bootstrap_executable = sys.executable
  sys.executable = pathjoin(target_dir,basename(sys.executable))
  verify(sys.executable)
  sys.prefix = sys.prefix.replace(mydir,target_dir)
  sys.argv[0] = sys.executable
  for i in xrange(len(sys.path)):
      sys.path[i] = sys.path[i].replace(mydir,target_dir)
  #  If we're in the bootstrap dir, try to chdir into the version dir.
  #  This is sometimes necessary for loading of DLLs by relative path.
  curdir = getcwd()
  if curdir == mydir:
      nt.chdir(target_dir)
  #  Use the library.zip from the version dir.
  #  It should already be in sys.path from the above env mangling,
  #  but you never know...
  libfile = pathjoin(target_dir,"library.zip")
  if libfile not in sys.path:
      if exists(libfile):
          sys.path.append(libfile)
      else:
          sys.path.append(target_dir)
  # Try to import the modules we need for bootstrapping.
  # If we fail for whatever reason, we can't chainload in-process.
  try:
      import zipextimporter; zipextimporter.install()
  except ImportError:
      pass
  try:
      import ctypes
      import struct
      import marshal
      import msvcrt
  except ImportError:
      return _orig_chainload(target_dir)
  # The source for esky.winres.load_resource gets inserted below.
  # This allows us to grab the code out of the frozen version exe.
  from ctypes import c_char, POINTER
  k32 = ctypes.windll.kernel32
  LOAD_LIBRARY_AS_DATAFILE = 0x00000002
  _DEFAULT_RESLANG = 1033
  %s
  # Great, now we magically have the load_resource function :-)
  try:
      data = load_resource(sys.executable,u"PYTHONSCRIPT",1,0)
  except EnvironmentError:
      #  This will trigger if sys.executable doesn't exist.
      #  Falling back to the original chainloader will account for
      #  the unlikely case where sys.executable is a backup file.
      return _orig_chainload(target_dir)
  else:
      sys.modules.pop("esky",None)
      sys.modules.pop("esky.bootstrap",None)
      headsz = struct.calcsize("iiii")
      (magic,optmz,unbfrd,codesz) = struct.unpack("iiii",data[:headsz])
      assert magic == 0x78563412
      # Set up the environment requested by "optimized" flag.
      # Currently "unbuffered" is not supported at run-time since I
      # haven't figured out the necessary incantations.
      try:
          opt_var = ctypes.c_int.in_dll(ctypes.pythonapi,"Py_OptimizeFlag")
          opt_var.value = optmz
      except ValueError:
          pass
      # Skip over the archive name to find start of code
      codestart = headsz
      while data[codestart] != "\\0":
          codestart += 1
      codestart += 1
      codeend = codestart + codesz
      codelist = marshal.loads(data[codestart:codeend])
      # Execute all code in the context of __main__ module.
      d_locals = d_globals = sys.modules["__main__"].__dict__
      d_locals["__name__"] = "__main__"
      for code in codelist:
          exec code in d_globals, d_locals
      raise SystemExit(0)
""" % (inspect.getsource(winres.load_resource).replace("\n","\n"+" "*4),)


#  On Windows, execv is flaky and expensive.  Since the pypy-compiled bootstrap
#  exe doesn't have a python runtime, it needs to chainload the one from the
#  target version dir before trying to bootstrap in-process.
_CUSTOM_PYPY_CHAINLOADER = """

import nt
from pypy.rlib.rstruct.runpack import runpack

import time;

_orig_chainload = _chainload

def _chainload(target_dir):
  mydir = dirname(sys.executable)
  pydll = pathjoin(target_dir,"python%s%s.dll" % sys.version_info[:2])
  if not exists(pydll):
      return _orig_chainload(target_dir)
  else:

      #  Munge the environment for DLL loading purposes
      try:
          environ["PATH"] = environ["PATH"] + ";" + target_dir
      except KeyError:
          environ["PATH"] = target_dir

      #  Get the target python env up and running
      verify(pydll)
      py = libpython(pydll)
      py.Set_NoSiteFlag(1)
      py.Set_FrozenFlag(1)
      py.Set_IgnoreEnvironmentFlag(1)
      py.SetPythonHome("")
      py.Initialize()

      #  Extract the marshalled code data from the target executable,
      #  store it into a python string object.
      target_exe = pathjoin(target_dir,basename(sys.executable))
      verify(target_exe)
      try:
          py_data = load_resource_pystr(py,target_exe,"PYTHONSCRIPT",1,0)
      except EnvironmentError:
          return _orig_chainload(target_dir)
      data = py.String_AsString(py_data)
      headsz = 16  # <-- struct.calcsize("iiii")
      headdata = rffi.charpsize2str(rffi.cast(rffi.CCHARP,data),headsz)
      (magic,optmz,unbfrd,codesz) = runpack("iiii",headdata)
      assert magic == 0x78563412
      # skip over the archive name to find start of code
      codestart = headsz
      while data[codestart] != "\\0":
          codestart += 1
      codestart += 1
      codeend = codestart + codesz
      assert codeend > 0

      #  Tweak the python env according to the py2exe frozen metadata
      py.Set_OptimizeFlag(optmz)
      # TODO: set up buffering
      # If you can decide on buffered/unbuffered before loading up
      # the python runtime, this can be done by just setting the
      # PYTHONUNBUFFERED environment variable.  If not, we have to
      # do it ourselves like this:
      #if unbfrd:
      #     setmode(0,nt.O_BINARY)
      #     setmode(1,nt.O_BINARY)
      #     setvbuf(stdin,NULL,4,512)
      #     setvbuf(stdout,NULL,4,512)
      #     setvbuf(stderr,NULL,4,512)

      #  Preted the python env is running from within the frozen executable
      syspath = "%s;%s\\library.zip;%s" % (target_exe,target_dir,target_dir,)
      py.Sys_SetPath(syspath);
      sysmod = py.Import_ImportModule("sys")
      sysargv = py.List_New(len(sys.argv))
      for i in xrange(len(sys.argv)):
          py.List_SetItem(sysargv,i,py.String_FromString(sys.argv[i]))
      py.Object_SetAttrString(sysmod,"argv",sysargv)
      py.Object_SetAttrString(sysmod,"frozen",py.String_FromString("py2exe"))
      py.Object_SetAttrString(sysmod,"executable",py.String_FromString(target_exe))
      py.Object_SetAttrString(sysmod,"bootstrap_executable",py.String_FromString(sys.executable))
      py.Object_SetAttrString(sysmod,"prefix",py.String_FromString(dirname(target_exe)))

      curdir = getcwd()
      if curdir == mydir:
          nt.chdir(target_dir)

      #  Execute the marshalled list of code objects
      globals = py.Dict_New()
      py.Dict_SetItemString(globals,"__builtins__",py.Eval_GetBuiltins())
      py.Dict_SetItemString(globals,"FROZEN_DATA",py_data)
      runcode =  "FROZEN_DATA = FROZEN_DATA[%d:%d]\\n" % (codestart,codeend,)
      runcode +=  "import sys\\n"
      runcode +=  "import marshal\\n"
      runcode += "d_locals = d_globals = sys.modules['__main__'].__dict__\\n"
      runcode += "d_locals['__name__'] = '__main__'\\n"
      runcode += "for code in marshal.loads(FROZEN_DATA):\\n"
      runcode += "  exec code in d_globals, d_locals\\n"
      py.Run_String(runcode,py.file_input,globals)

      #  Clean up after execution.
      py.Finalize()
      sys.exit(0)

"""



########NEW FILE########
__FILENAME__ = pypyc
"""

  esky.bdist_esky.pypyc:  support for compiling bootstrap exes with PyPy


This module provides the supporting code to compile bootstrapping exes with
PyPy.  In theory, this should provide for faster startup and less resource
usage than building the bootstrap exes out of the frozen application stubs.

"""

from __future__ import with_statement

import os
import sys

import pypy.translator.goal.translate

try:
    import pypy.rlib.clibffi
except (ImportError,AttributeError,), e:
    msg = "Compiling bootstrap exes requires PyPy v1.5 or later"
    msg += " [error: %s]" % (e,)
    raise ImportError(msg)


def compile_rpython(infile,outfile,gui_only=False,static_msvcrt=False):
    """Compile the given RPython input file to executable output file."""
    orig_argv = sys.argv[:]
    try:
        if sys.platform == "win32":
            pypy.translator.platform.host.gui_only = gui_only
        sys.argv[0] = sys.executable
        sys.argv[1:] = ["--output",outfile,"--batch","--gc=ref",]
        sys.argv.append(infile)
        pypy.translator.goal.translate.main()
    finally:
        sys.argv = orig_argv



#  For win32, we need some fancy features not provided by the normal
#  PyPy compiler.  Fortunately we can hack them in.
#
if sys.platform == "win32":
  import pypy.translator.platform.windows
  class CustomWin32Platform(pypy.translator.platform.windows.MsvcPlatform):
      """Custom PyPy platform object with fancy windows features.

      This platform knows how to do two things that native PyPy cannot -
      build a gui-only executable, and statically link the C runtime.
      Unfortunately there's a fair amount of monkey-patchery involved.
      """

      gui_only = False
      static_msvcrt = False

      def _is_main_srcfile(self,filename):
          if "platcheck" in filename:
              return True
          if "implement_1" in filename:
              return True
          return False

      def _compile_c_file(self,cc,cfile,compile_args):
          if self.gui_only:
              #  Add stub code for WinMain to gui-only compiles.
              if self._is_main_srcfile(str(cfile)):
                  with open(str(cfile),"r+b") as f:
                      data = f.read()
                      f.seek(0)
                      f.write(WINMAIN_STUB)
                      f.write(data)
          return super(CustomWin32Platform,self)._compile_c_file(cc,cfile,compile_args)

      def _link(self,cc,ofiles,link_args,standalone,exe_name):
          #  Link against windows subsystem if gui-only is specified.
          if self.gui_only:
              link_args.append("/subsystem:windows")
          #  Choose whether to link crt statically or dynamically.
          if not self.static_msvcrt:
              if "/MT" in self.cflags:
                  self.cflags.remove("/MT")
              if "/MD" not in self.cflags:
                  self.cflags.append("/MD")
          else:
              if "/MD" in self.cflags:
                  self.cflags.remove("/MD")
              if "/MT" not in self.cflags:
                  self.cflags.append("/MT")
              #  Static linking means no manifest is generated.
              #  Create a fake one so PyPy doesn't get confused.
              if self.version >= 80:
                  ofile = ofiles[-1]
                  manifest = str(ofile.dirpath().join(ofile.purebasename))
                  manifest += '.manifest'
                  with open(manifest,"w") as mf:
                      mf.write(DUMMY_MANIFEST)
          return super(CustomWin32Platform,self)._link(cc,ofiles,link_args,standalone,exe_name)

      def _finish_linking(self,ofiles,*args,**kwds):
          return super(CustomWin32Platform,self)._finish_linking(ofiles,*args,**kwds)

      #  Ugh.
      #  Trick pypy into letting us mix this with other platform objects.
      #  I should probably check that it's an MsvcPlatform...
      def __eq__(self, other):
          return True


  pypy.translator.platform.platform = CustomWin32Platform()
  pypy.translator.platform.host = pypy.translator.platform.platform
  pypy.translator.platform.host_factory = lambda *a: pypy.translator.platform.platform




WINMAIN_STUB = """
#ifndef PYPY_NOT_MAIN_FILE
#ifndef WIN32_LEAN_AND_MEAN

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdlib.h>

int WINAPI WinMain(HINSTANCE hInstance,HINSTANCE hPrevInstance,
                   LPWSTR lpCmdLine,int nCmdShow) {
    return main(__argc, __argv);
}

#endif
#endif
"""

DUMMY_MANIFEST =  """
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
</assembly>
"""

if __name__ == "__main__":
    import optparse 
    parser = optparse.OptionParser()
    parser.add_option("-g","--gui-only",action="store_true")
    parser.add_option("","--static-msvcrt",action="store_true")
    (opts,args) = parser.parse_args()
    if len(args) == 0:
        raise RuntimeError("no input file specified")
    if len(args) == 1:
        outfile = os.path.basename(args[0]).rsplit(".",1)[0] + "-c"
        if sys.platform == "win32":
            outfile += ".exe"
        outfile = os.path.join(os.path.dirname(args[0]),outfile)
        args.append(outfile)
    compile_rpython(args[0],args[1],opts.gui_only,opts.static_msvcrt)




########NEW FILE########
__FILENAME__ = pypy_libpython
"""

  esky.bdist_esky.pypy_libpython:  load python DLL into pypy bootstrap exe


This module provides the class "libpython", an RPython-compatible class for
loading and exposing a python environment using clibffi.  It's used by the
pypy-compiled bootstrap exes to bootstrap a version dir in-process.

"""


from pypy.rlib import clibffi
from pypy.rpython.lltypesystem import rffi, lltype


class libpython(object):

    file_input = 257


    def __init__(self,library_path):
        self.lib = clibffi.CDLL(library_path)
        self._libc = clibffi.CDLL(clibffi.get_libc_name())


    def Set_NoSiteFlag(self,value):
        addr = self.lib.getaddressindll("Py_NoSiteFlag")
        memset = self._libc.getpointer("memset",[clibffi.ffi_type_pointer,clibffi.ffi_type_uint,clibffi.ffi_type_uint],clibffi.ffi_type_void)
        memset.push_arg(addr)
        memset.push_arg(value)
        memset.push_arg(1)
        memset.call(lltype.Void)


    def Set_FrozenFlag(self,value):
        addr = self.lib.getaddressindll("Py_FrozenFlag")
        memset = self._libc.getpointer("memset",[clibffi.ffi_type_pointer,clibffi.ffi_type_uint,clibffi.ffi_type_uint],clibffi.ffi_type_void)
        memset.push_arg(addr)
        memset.push_arg(value)
        memset.push_arg(1)
        memset.call(lltype.Void)


    def Set_IgnoreEnvironmentFlag(self,value):
        addr = self.lib.getaddressindll("Py_IgnoreEnvironmentFlag")
        memset = self._libc.getpointer("memset",[clibffi.ffi_type_pointer,clibffi.ffi_type_uint,clibffi.ffi_type_uint],clibffi.ffi_type_void)
        memset.push_arg(addr)
        memset.push_arg(value)
        memset.push_arg(1)
        memset.call(lltype.Void)


    def Set_OptimizeFlag(self,value):
        addr = self.lib.getaddressindll("Py_OptimizeFlag")
        memset = self._libc.getpointer("memset",[clibffi.ffi_type_pointer,clibffi.ffi_type_uint,clibffi.ffi_type_uint],clibffi.ffi_type_void)
        memset.push_arg(addr)
        memset.push_arg(value)
        memset.push_arg(1)
        memset.call(lltype.Void)


    def Initialize(self):
        impl = self.lib.getpointer("Py_Initialize",[],clibffi.ffi_type_void)
        impl.call(lltype.Void)


    def Finalize(self):
        impl = self.lib.getpointer("Py_Finalize",[],clibffi.ffi_type_void)
        impl.call(lltype.Void)


    def Err_Occurred(self):
        impl = self.lib.getpointer("PyErr_Occurred",[],clibffi.ffi_type_pointer)
        return impl.call(rffi.VOIDP)


    def Err_Print(self):
        impl = self.lib.getpointer("PyErr_Print",[],clibffi.ffi_type_void)
        impl.call(lltype.Void)


    def _error(self):
        err = self.Err_Occurred()
        if err:
            self.Err_Print()
            raise RuntimeError("an error occurred")


    def Run_SimpleString(self,string):
        impl = self.lib.getpointer("PyRun_SimpleString",[clibffi.ffi_type_pointer],clibffi.ffi_type_sint)
        buf = rffi.str2charp(string)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        res = impl.call(rffi.INT)
        rffi.free_charp(buf)
        if res < 0:
            self._error()


    def Run_String(self,string,start,globals=None,locals=None):
        if globals is None:
            globals = 0
        if locals is None:
            locals = 0
        impl = self.lib.getpointer("PyRun_String",[clibffi.ffi_type_pointer,clibffi.ffi_type_sint,clibffi.ffi_type_pointer,clibffi.ffi_type_pointer],clibffi.ffi_type_pointer)
        buf = rffi.str2charp(string)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        impl.push_arg(start)
        impl.push_arg(globals)
        impl.push_arg(locals)
        res = impl.call(rffi.VOIDP)
        rffi.free_charp(buf)
        if not res:
            self._error()
        return res


    def GetProgramFullPath(self):
        impl = self.lib.getpointer("Py_GetProgramFullPath",[],clibffi.ffi_type_pointer)
        return rffi.charp2str(impl.call(rffi.CCHARP))


    def SetPythonHome(self,path):
        return
        impl = self.lib.getpointer("Py_SetPythonHome",[clibffi.ffi_type_pointer],clibffi.ffi_type_void)
        buf = rffi.str2charp(path)
        impl.push_arg(buf)
        impl.call(lltype.Void)
        rffi.free_charp(buf)


    # TODO: this seems to cause type errors during building
    def Sys_SetArgv(self,argv):
        impl = self.lib.getpointer("PySys_SetArgv",[clibffi.ffi_type_sint,clibffi.ffi_type_pointer],clibffi.ffi_type_void)
        impl.push_arg(len(argv))
        buf = rffi.liststr2charpp(argv)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        impl.call(lltype.Void)
        rffi.free_charpp(buf)


    def Sys_SetPath(self,path):
        impl = self.lib.getpointer("PySys_SetPath",[clibffi.ffi_type_pointer],clibffi.ffi_type_void)
        buf = rffi.str2charp(path)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        impl.call(lltype.Void)
        rffi.free_charp(buf)


    def Eval_GetBuiltins(self):
        impl = self.lib.getpointer("PyEval_GetBuiltins",[],clibffi.ffi_type_pointer)
        d = impl.call(rffi.VOIDP)
        if not d:
            self._error()
        return d


    def Import_ImportModule(self,name):
        impl = self.lib.getpointer("PyImport_ImportModule",[clibffi.ffi_type_pointer],clibffi.ffi_type_pointer)
        buf = rffi.str2charp(name)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        mod = impl.call(rffi.VOIDP)
        rffi.free_charp(buf)
        if not mod:
            self._error()
        return mod


    def Object_GetAttr(self,obj,attr):
        impl = self.lib.getpointer("PyObject_GetAttr",[clibffi.ffi_type_pointer,clibffi.ffi_type_pointer],clibffi.ffi_type_pointer)
        impl.push_arg(obj)
        impl.push_arg(attr)
        a = impl.call(rffi.VOIDP)
        if not a:
            self._error()
        return a


    def Object_GetAttrString(self,obj,attr):
        impl = self.lib.getpointer("PyObject_GetAttrString",[clibffi.ffi_type_pointer,clibffi.ffi_type_pointer],clibffi.ffi_type_pointer)
        impl.push_arg(obj)
        buf = rffi.str2charp(attr)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        a = impl.call(rffi.VOIDP)
        rffi.free_charp(buf)
        if not a:
            self._error()
        return a


    def Object_SetAttr(self,obj,attr,val):
        impl = self.lib.getpointer("PyObject_SetAttr",[clibffi.ffi_type_pointer,clibffi.ffi_type_pointer,clibffi.ffi_type_pointer],clibffi.ffi_type_sint)
        impl.push_arg(obj)
        impl.push_arg(attr)
        impl.push_arg(val)
        res = impl.call(rffi.INT)
        if res < 0:
            self._error()
        return None


    def Object_SetAttrString(self,obj,attr,val):
        impl = self.lib.getpointer("PyObject_SetAttrString",[clibffi.ffi_type_pointer,clibffi.ffi_type_pointer,clibffi.ffi_type_pointer],clibffi.ffi_type_sint)
        impl.push_arg(obj)
        buf = rffi.str2charp(attr)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        impl.push_arg(val)
        res = impl.call(rffi.INT)
        rffi.free_charp(buf)
        if res < 0:
            self._error()
        return None


    def Dict_New(self):
        impl = self.lib.getpointer("PyDict_New",[],clibffi.ffi_type_pointer)
        d = impl.call(rffi.VOIDP)
        if not d:
            self._error()
        return d


    def Dict_SetItemString(self,d,key,value):
        impl = self.lib.getpointer("PyDict_SetItemString",[clibffi.ffi_type_pointer,clibffi.ffi_type_pointer,clibffi.ffi_type_pointer],clibffi.ffi_type_sint)
        impl.push_arg(d)
        buf = rffi.str2charp(key)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        impl.push_arg(value)
        d = impl.call(rffi.INT)
        rffi.free_charp(buf)
        if d < 0:
            self._error()


    def List_New(self,size=0):
        impl = self.lib.getpointer("PyList_New",[clibffi.ffi_type_uint],clibffi.ffi_type_pointer)
        impl.push_arg(size)
        l = impl.call(rffi.VOIDP)
        if not l:
            self._error()
        return l


    def List_Size(self,l):
        impl = self.lib.getpointer("PyList_Size",[clibffi.ffi_type_pointer],clibffi.ffi_type_uint)
        impl.push_arg(l)
        s = impl.call(rffi.INT)
        if s < 0:
            self._error()
        return s


    def List_SetItem(self,l,i,v):
        impl = self.lib.getpointer("PyList_SetItem",[clibffi.ffi_type_pointer,clibffi.ffi_type_uint,clibffi.ffi_type_pointer],clibffi.ffi_type_sint)
        impl.push_arg(l)
        impl.push_arg(i)
        impl.push_arg(v)
        res = impl.call(rffi.INT)
        if res < 0:
            self._error()


    def List_Append(self,l,v):
        impl = self.lib.getpointer("PyList_Append",[clibffi.ffi_type_pointer,clibffi.ffi_type_pointer],clibffi.ffi_type_sint)
        impl.push_arg(l)
        impl.push_arg(v)
        res = impl.call(rffi.INT)
        if res < 0:
            self._error()


    def String_FromString(self,s):
        impl = self.lib.getpointer("PyString_FromString",[clibffi.ffi_type_pointer],clibffi.ffi_type_pointer)
        buf = rffi.str2charp(s)
        impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        ps = impl.call(rffi.VOIDP)
        rffi.free_charp(buf)
        if not ps:
            self._error()
        return ps


    def String_FromStringAndSize(self,s,size):
        impl = self.lib.getpointer("PyString_FromStringAndSize",[clibffi.ffi_type_pointer,clibffi.ffi_type_uint],clibffi.ffi_type_pointer)
        if not s:
            buf = None
            impl.push_arg(None)
        else:
            buf = rffi.str2charp(s)
            impl.push_arg(rffi.cast(rffi.VOIDP,buf))
        impl.push_arg(size)
        ps = impl.call(rffi.VOIDP)
        if s:
            rffi.free_charp(buf)
        if not ps:
            self._error()
        return ps


    def String_AsString(self,s):
        impl = self.lib.getpointer("PyString_AsString",[clibffi.ffi_type_pointer],clibffi.ffi_type_pointer)
        impl.push_arg(s)
        buf = impl.call(rffi.VOIDP)
        if not buf:
            self._error()
        return buf



########NEW FILE########
__FILENAME__ = pypy_winres
"""

  esky.bdist_esky.pypy_winres:  access win32 exe resources in rpython


This module provides some functions for accessing win32 exe resources from
rpython code.  It's a trimmed-down version of the esky.winres module with
just enough functionality to get the py2exe compiled bootstrapper working.

"""

from pypy.rlib import clibffi
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import rwin32


LOAD_LIBRARY_AS_DATAFILE = 0x00000002


k32_LoadLibraryExA = rwin32.winexternal("LoadLibraryExA",[rffi.CCHARP,rwin32.HANDLE,rwin32.DWORD],rwin32.HANDLE)
k32_FindResourceExA = rwin32.winexternal("FindResourceExA",[rwin32.HANDLE,rffi.CCHARP,rwin32.DWORD,rwin32.DWORD],rwin32.HANDLE)
k32_SizeofResource = rwin32.winexternal("SizeofResource",[rwin32.HANDLE,rwin32.HANDLE],rwin32.DWORD)
k32_LoadResource = rwin32.winexternal("LoadResource",[rwin32.HANDLE,rwin32.HANDLE],rwin32.HANDLE)
k32_LockResource = rwin32.winexternal("LockResource",[rwin32.HANDLE],rffi.CCHARP)
k32_FreeLibrary = rwin32.winexternal("FreeLibrary",[rwin32.HANDLE],rwin32.BOOL)


def load_resource(filename,resname,resid,reslang):
    """Load the named resource from the given file.

    The filename and resource name must be ascii strings, and the resid and
    reslang must be integers.
    """
    l_handle = k32_LoadLibraryExA(filename,rffi.cast(rwin32.HANDLE,0),LOAD_LIBRARY_AS_DATAFILE)
    if not l_handle:
        raise WindowsError(rwin32.GetLastError(),"LoadLibraryExW failed")
    try:
        r_handle = k32_FindResourceExA(l_handle,resname,resid,reslang)
        if not r_handle:
            raise WindowsError(rwin32.GetLastError(),"FindResourceExA failed")
        r_size = k32_SizeofResource(l_handle,r_handle)
        if not r_size:
            raise WindowsError(rwin32.GetLastError(),"SizeofResource failed")
        r_info = k32_LoadResource(l_handle,r_handle)
        if not r_info:
            raise WindowsError(rwin32.GetLastError(),"LoadResource failed")
        r_ptr = k32_LockResource(r_info)
        if not r_ptr:
            raise WindowsError(rwin32.GetLastError(),"LockResource failed")
        return rffi.charpsize2str(r_ptr,r_size)
    finally:
        if not k32_FreeLibrary(l_handle):
            raise WindowsError(rwin32.GetLastError(),"FreeLibrary failed")


def load_resource_pystr(py,filename,resname,resid,reslang):
    """Load the named resource from the given file as a python-level string

    The filename and resource name must be ascii strings, and the resid and
    reslang must be integers.

    This uses the given python dll object to load the data directly into 
    a python string, saving a lot of copying and carrying on.
    """
    l_handle = k32_LoadLibraryExA(filename,rffi.cast(rwin32.HANDLE,0),LOAD_LIBRARY_AS_DATAFILE)
    if not l_handle:
        raise WindowsError(rwin32.GetLastError(),"LoadLibraryExW failed")
    try:
        r_handle = k32_FindResourceExA(l_handle,resname,resid,reslang)
        if not r_handle:
            raise WindowsError(rwin32.GetLastError(),"FindResourceExA failed")
        r_size = k32_SizeofResource(l_handle,r_handle)
        if not r_size:
            raise WindowsError(rwin32.GetLastError(),"SizeofResource failed")
        r_info = k32_LoadResource(l_handle,r_handle)
        if not r_info:
            raise WindowsError(rwin32.GetLastError(),"LoadResource failed")
        r_ptr = k32_LockResource(r_info)
        if not r_ptr:
            raise WindowsError(rwin32.GetLastError(),"LockResource failed")
        s = py.String_FromStringAndSize(None,r_size)
        buf = py.String_AsString(s)
        memcpy(buf,rffi.cast(rffi.VOIDP,r_ptr),r_size)
        return s
    finally:
        if not k32_FreeLibrary(l_handle):
            raise WindowsError(rwin32.GetLastError(),"FreeLibrary failed")


def memcpy(target,source,n):
    impl = clibffi.CDLL(clibffi.get_libc_name()).getpointer("memcpy",[clibffi.ffi_type_pointer,clibffi.ffi_type_pointer,clibffi.ffi_type_uint],clibffi.ffi_type_void)
    impl.push_arg(target)
    impl.push_arg(source)
    impl.push_arg(n)
    impl.call(lltype.Void)
   


########NEW FILE########
__FILENAME__ = bootstrap
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.bootstrap:  minimal bootstrapping code for esky

This module provides the minimal code necessary to bootstrap a frozen
application packaged using esky.  It checks the base runtime directory to
find the most appropriate version of the app and then execvs to the frozen
executable.

This module must use no modules other than builtins, since the stdlib is
not available in the bootstrapping environment.  It must also be capable
of bootstrapping into apps made with older versions of esky, since a partial
update could result in the boostrapper from a new version being forced
to load an old version.

If you want to compile your bootstrapping exes into standalone executables,
this module must also be written in the "RPython" dialect used by the PyPy
translation toolchain.

The code from this module is always executed in the bootstrapping environment
before any custom bootstrapping code.  It provides the following functions for
use during the bootstrap process:

  Chainloading:         execv, chainload
  Filesystem:           listdir, exists, basename, dirname, pathjoin
  Version handling:     split_app_version, join_app_version, parse_version,
                        get_all_versions, get_best_version, is_version_dir,
                        is_installed_version_dir, is_uninstalled_version_dir,
                        lock_version_dir, unlock_version_dir


"""


import sys
import errno

try:
    ESKY_CONTROL_DIR
except NameError:
    ESKY_CONTROL_DIR = "esky-files"

try:
    ESKY_APPDATA_DIR
except NameError:
    ESKY_APPDATA_DIR = "appdata"

try:
    __esky_name__
except NameError:
    __esky_name__ = ""

try:
    __rpython__
except NameError:
    __rpython__ = False

#  RPython doesn't handle SystemExit automatically, so we put the exit code
#  in this global var and catch SystemExit ourselves at the outmost scope.
_exit_code = [0]

#  The os module is not builtin, so we grab what we can from the
#  platform-specific modules and fudge the rest.
if "posix" in sys.builtin_module_names:
    import fcntl
    from posix import listdir, stat, unlink, rename, execv, getcwd, environ
    from posix import open as os_open
    from posix import read as os_read
    from posix import close as os_close
    SEP = "/"
    def isabs(path):
        return (path.startswith(SEP))
    def abspath(path):
        path = pathjoin(getcwd(),path)
        components_in = path.split(SEP)
        components = [components_in[0]]
        for comp in components_in[1:]:
            if not comp or comp == ".":
                pass
            elif comp == "..":
                components.pop()
            else:
                components.append(comp)
        return SEP.join(components)
elif "nt" in sys.builtin_module_names:
    fcntl = None
    import nt
    from nt import listdir, stat, unlink, rename, spawnv
    from nt import getcwd, P_WAIT, environ
    from nt import open as os_open
    from nt import read as os_read
    from nt import close as os_close
    SEP = "\\"
    def isabs(path):
        if path.startswith(SEP):
            return True
        if len(path) >= 2:
            if path[0].isalpha() and path[1] == ":":
                return True
        return False
    def abspath(path):
        path = pathjoin(getcwd(),path)
        components_in = path.split(SEP)
        components = [components_in[0]]
        for comp in components_in[1:]:
            if not comp or comp == ".":
                pass
            elif comp == "..":
                components.pop()
            else:
                components.append(comp)
        if path.startswith(SEP + SEP):
            components.insert(0, "")
        return SEP.join(components)
    #  The standard execv terminates the spawning process, which makes
    #  it impossible to wait for it.  This alternative is waitable, and
    #  uses the esky.slaveproc machinery to avoid leaving zombie children.
    def execv(filename,args):
        #  Create an O_TEMPORARY file and pass its name to the slave process.
        #  When this master process dies, the file will be deleted and the
        #  slave process will know to terminate.
        try:
            tdir = environ["TEMP"]
        except:
            tdir = None
        if tdir:
            try:
                nt.mkdir(pathjoin(tdir,"esky-slave-procs"),0600)
            except EnvironmentError:
                pass
            if exists(pathjoin(tdir,"esky-slave-procs")):
                flags = nt.O_CREAT|nt.O_EXCL|nt.O_TEMPORARY|nt.O_NOINHERIT
                for i in xrange(10):
                    tfilenm = "slave-%d.%d.txt" % (nt.getpid(),i,)
                    tfilenm = pathjoin(tdir,"esky-slave-procs",tfilenm)
                    try:
                        os_open(tfilenm,flags,0600)
                        args.insert(1,tfilenm)
                        args.insert(1,"--esky-slave-proc")
                        break
                    except EnvironmentError:
                        pass
        # Ensure all arguments are quoted (to allow spaces in paths)
        for i, arg in enumerate(args):
            if arg[0] != "\"" and args[-1] != "\"":
                args[i] = "\"{}\"".format(arg)
        res = spawnv(P_WAIT,filename, args)
        _exit_code[0] = res
        raise SystemExit(res)
    #  A fake fcntl module which is false, but can fake out RPython
    class fcntl:
        LOCK_SH = 0
        def flock(self,fd,mode):
            pass
        def __nonzero__(self):
            return False
    fcntl = fcntl()
else:
    raise RuntimeError("unsupported platform: " + sys.platform)


if __rpython__:
    # RPython provides ll hooks for the actual os.environ object, not the
    # one we pulled out of "nt" or "posix".
    from os import environ

    # RPython doesn't have access to the "sys" module, so we fake it out.
    # The entry_point function will set these value appropriately.
    _sys = sys
    class sys:
        platform = _sys.platform
        executable = _sys.executable
        argv = _sys.argv
        version_info = _sys.version_info
        modules = {}
        builtin_module_names = _sys.builtin_module_names
        def exit(self,code):
            _exit_code[0] = code
            raise SystemExit(code)
        def exc_info(self):
            return None,None,None
    sys = sys()
    sys.modules["sys"] = sys

    #  RPython doesn't provide the sorted() builtin, and actually makes sorting
    #  quite complicated in general.  I can't convince the type annotator to be
    #  happy about using their "listsort" module, so I'm doing my own using a
    #  simple insertion sort.  We're only sorting short lists and they always
    #  contain (list(str),str), so this should do for now.
    def _list_gt(l1,l2):
        i = 0
        while i < len(l1) and i < len(l2):
            if l1[i] > l2[i]:
               return True
            if l1[i] < l2[i]:
               return False
            i += 1
        if len(l1) > len(l2):
            return True
        return False
    def sorted(lst,reverse=False):
        slst = []
        if reverse:
            for item in lst:
                for j in xrange(len(slst)):
                    if not _list_gt(slst[j][0],item[0]):
                        slst.insert(j,item)
                        break 
                else:
                    slst.append(item)
        else:
            for item in lst:
                for j in xrange(len(slst)):
                    if _list_gt(slst[j][0],item[0]):
                        slst.insert(j,item)
                        break 
                else:
                    slst.append(item)
        return slst
    # RPython doesn't provide the "zfill" or "isalnum" methods on strings.
    def zfill(str,n):
        while len(str) < n:
            str = "0" + str
        return str
    def isalnum(str):
        for c in str:
            if not c.isalnum():
                return False
        return True
    # RPython doesn't provide the "fcntl" module.  Fake it.
    # TODO: implement it using externals
    if fcntl:
        class fcntl:
            LOCK_SH = fcntl.LOCK_SH
            def flock(self,fd,mode):
                pass
        fcntl = fcntl()
else:
    #  We need to use a compatability wrapper for some string methods missing
    #  in RPython, since we can't just add them as methods on the str type.
    def zfill(str,n):
        return str.zfill(n)
    def isalnum(str):
        return str.isalnum()


def pathjoin(*args):
    """Local re-implementation of os.path.join."""
    path = args[0]
    for arg in list(args[1:]):
        if isabs(arg):
            path = arg
        else:
            while path.endswith(SEP):
                path = path[:-1]
            path = path + SEP + arg
    return path

def basename(p):
    """Local re-implementation of os.path.basename."""
    return p.split(SEP)[-1]

def dirname(p):
    """Local re-implementation of os.path.dirname."""
    return SEP.join(p.split(SEP)[:-1])

def exists(path):
    """Local re-implementation of os.path.exists."""
    try:
        stat(path)
    except EnvironmentError, e:
        # TODO: how to get the errno under RPython?
        if not __rpython__:
            if e.errno not in (errno.ENOENT,errno.ENOTDIR,errno.ESRCH,):
                raise
        return False
    else:
        return True

def appdir_from_executable(exepath):
    """Find the top-level application directory, given sys.executable.

    Ordinarily this would simply be the directory containing the executable,
    but when running via a bundle on OSX the executable will be located at
    <appdir>/Contents/MacOS/<exe>.
    """
    appdir = dirname(exepath)
    if sys.platform == "darwin" and basename(appdir) == "MacOS":
        # Looks like we might be in an app bundle.
        appdir = dirname(appdir)
        if basename(appdir) == "Contents":
            # Yep, definitely in a bundle
            appdir = dirname(appdir)
        else:
            # Nope, some other crazy scheme
            appdir = dirname(exepath)
    return appdir


def bootstrap():
    """Bootstrap an esky frozen app into the newest available version.

    This function searches the application directory to find the highest-
    numbered version of the application that is fully installed, then
    chainloads that version of the application.
    """
    sys.executable = abspath(sys.executable)
    appdir = appdir_from_executable(sys.executable)
    vsdir = pathjoin(appdir,ESKY_APPDATA_DIR)
    # TODO: remove compatability hook for ESKY_APPDATA_DIR="".
    best_version = None
    try:
        if __esky_name__:
            best_version = get_best_version(vsdir,appname=__esky_name__)
        if best_version is None:
            best_version = get_best_version(vsdir)
        if best_version is None:
            if exists(vsdir):
                raise RuntimeError("no usable frozen versions were found")
            else:
                raise EnvironmentError
    except EnvironmentError:
        if exists(vsdir):
            raise
        vsdir = appdir
        if __esky_name__:
            best_version = get_best_version(vsdir,appname=__esky_name__)
        if best_version is None:
            best_version = get_best_version(vsdir)
        if best_version is None:
            raise RuntimeError("no usable frozen versions were found")
    return chainload(pathjoin(vsdir,best_version))


def chainload(target_dir):
    """Load and execute the selected version of an application.

    This function replaces the currently-running executable with the equivalent
    executable from the given target directory.

    On platforms that support it, this also locks the target directory so that
    it will not be removed by any simultaneously-running instances of the
    application.
    """
    try:
        lock_version_dir(target_dir)
    except EnvironmentError:
        #  If the bootstrap file is missing, the version is being uninstalled.
        #  Our only option is to re-execute ourself and find the new version.
        if exists(dirname(target_dir)):
            bsfile = pathjoin(target_dir,ESKY_CONTROL_DIR)
            bsfile = pathjoin(bsfile,"bootstrap-manifest.txt")
            if not exists(bsfile):
                execv(sys.executable,list(sys.argv))
                return
        raise
    else:
        #  If all goes well, we can actually launch the target version.
        _chainload(target_dir)


def get_exe_locations(target_dir):
    """Generate possible locations from which to chainload in the target dir."""
    # TODO: let this be a generator when not compiling with PyPy, so we can
    # avoid a few stat() calls in the common case.
    locs = []
    appdir = appdir_from_executable(sys.executable)
    #  If we're in an appdir, first try to launch from within "<appname>.app"
    #  directory.  We must also try the default scheme for backwards compat.
    if sys.platform == "darwin":
        if basename(dirname(sys.executable)) == "MacOS":
            if __esky_name__:
                locs.append(pathjoin(target_dir,
                                     __esky_name__+".app",
                                     sys.executable[len(appdir)+1:]))
            else:
                for nm in listdir(target_dir):
                    if nm.endswith(".app"):
                        locs.append(pathjoin(target_dir,
                                             nm,
                                             sys.executable[len(appdir)+1:]))
    #  This is the default scheme: the same path as the exe in the appdir.
    locs.append(target_dir + sys.executable[len(appdir):])
    #  If sys.executable was a backup file, try using original filename.
    orig_exe = get_original_filename(sys.executable)
    if orig_exe is not None:
        locs.append(target_dir + orig_exe[len(appdir):])
    return locs


def verify(target_file):
    """Verify the integrity of the given target file.

    By default this is a no-op; override it to provide e.g. signature checks.
    """
    pass


def _chainload(target_dir):
    """Default implementation of the chainload() function.

    Specific freezer modules may provide a more efficient, reliable or
    otherwise better version of this function.
    """
    exc_type,exc_value,traceback = None,None,None
    for target_exe in get_exe_locations(target_dir):
        verify(target_exe)
        try:
            execv(target_exe,[target_exe] + sys.argv[1:])
            return
        except EnvironmentError, exc_value:
            #  Careful, RPython lacks a usable exc_info() function.
            exc_type,_,traceback = sys.exc_info()
            if not __rpython__:
                if exc_value.errno != errno.ENOENT:
                    raise
            else:
                if exists(target_exe):
                    raise
    else:
        if exc_value is not None:
            if exc_type is not None:
                raise exc_type,exc_value,traceback
            else:
                raise exc_value
        raise RuntimeError("couldn't chainload any executables")


def get_best_version(appdir,include_partial_installs=False,appname=None):
    """Get the best usable version directory from inside the given appdir.

    In the common case there is only a single version directory, but failed
    or partial updates can result in several being present.  This function
    finds the highest-numbered version that is completely installed.
    """
    #  Find all potential version directories, sorted by version number.
    candidates = []
    for nm in listdir(appdir):
        (appnm,ver,platform) = split_app_version(nm)
        #  If its name didn't parse properly, don't bother looking inside.
        if ver and platform:
            #  If we're given a specific name, it must have that name
            if appname is not None and appnm != appname:
                continue
            #  We have to pay another stat() call to check if it's active.
            if is_version_dir(pathjoin(appdir,nm)):
                ver = parse_version(ver)
                candidates.append((ver,nm))
    candidates = [c[1] for c in sorted(candidates,reverse=True)]
    #  In the (hopefully) common case of no failed updates, we don't need
    #  to poke around in the filesystem so we just return asap.
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if include_partial_installs:
        return candidates[0]
    #  If there are several candidate versions, we need to find the best
    #  one that is completely installed.
    while candidates:
        nm = candidates.pop(0)
        if is_installed_version_dir(pathjoin(appdir,nm)):
            return nm
    return None


def get_all_versions(appdir,include_partial_installs=False):
    """Get a list of all usable version directories inside the given appdir.

    The list will be in order from most-recent to least-recent.  The head
    of the list will be the same directory as returned by get_best_version.
    """
    #  Find all potential version directories, sorted by version number.
    candidates = []
    for nm in listdir(appdir):
        (_,ver,platform) = split_app_version(nm)
        if ver and platform:
            if is_version_dir(pathjoin(appdir,nm)):
                ver = parse_version(ver)
                candidates.append((ver,nm))
    candidates = [c[1] for c in sorted(candidates,reverse=True)]
    #  Filter out any that are not completely installed.
    if not include_partial_installs:
        i = 0
        while i < len(candidates):
            if not is_installed_version_dir(pathjoin(appdir,candidates[i])):
                del candidates[i]
            else:
                i += 1
    return candidates


def is_version_dir(vdir):
    """Check whether the given directory contains an esky app version.

    Currently it only need contain the "esky-files/bootstrap-mainfest.txt" file.
    """
    if exists(pathjoin(vdir,ESKY_CONTROL_DIR,"bootstrap-manifest.txt")):
        return True
    return False


def is_installed_version_dir(vdir):
    """Check whether the given version directory is fully installed.

    Currently, a completed installation is indicated by the lack of an
    "esky-files/bootstrap" directory.
    """
    if not exists(pathjoin(vdir,ESKY_CONTROL_DIR,"bootstrap")):
        return True
    return False


def is_uninstalled_version_dir(vdir):
    """Check whether the given version directory is partially uninstalled.

    A partially-uninstalled version dir has had the "bootstrap-manifest.txt"
    renamed to "bootstrap-manifest-old.txt".
    """
    if exists(pathjoin(vdir,ESKY_CONTROL_DIR,"bootstrap-manifest-old.txt")):
        return True
    return False
    


def split_app_version(s):
    """Split an app version string to name, version and platform components.

    For example, app-name-0.1.2.win32 => ("app-name","0.1.2","win32")
    """
    bits = s.split("-")
    idx = 1
    while idx < len(bits):
        if bits[idx]:
            if not bits[idx][0].isalpha() or not isalnum(bits[idx]):
                break
        idx += 1
    appname = "-".join(bits[:idx])
    bits = "-".join(bits[idx:]).split(".")
    version = ".".join(bits[:-1])
    platform = bits[-1]
    return (appname,version,platform)


def join_app_version(appname,version,platform):
    """Join an app name, version and platform into a version directory name.

    For example, ("app-name","0.1.2","win32") => appname-0.1.2.win32
    """
    return "%s-%s.%s" % (appname,version,platform,)
    

def parse_version(s):
    """Parse a version string into a chronologically-sortable key

    This function returns a sequence of strings that compares with the results
    for other versions in a chronologically sensible way.  You'd use it to
    compare two version strings like so:

        if parse_version("1.9.2") > parse_version("1.10.0"):
            raise RuntimeError("what rubbish, that's an older version!")

    This is essentially the parse_version() function from pkg_resources,
    but re-implemented to avoid using modules that may not be available
    during bootstrapping.
    """
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith('*'):
            if part<'*final':   # remove '-' before a prerelease tag
                while parts and parts[-1]=='*final-': parts.pop()
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1]=='00000000':
                parts.pop()
        parts.append(part)
    return parts


_replace_p = {'pre':'c', 'preview':'c','-':'final-','rc':'c','dev':'@'}.get
def _parse_version_parts(s):
    parts = []
    for part in _split_version_components(s):
        part = _replace_p(part,part)
        if not part or part=='.':
            continue
        if part[:1] in '0123456789':
            parts.append(zfill(part,8))    # pad for numeric comparison
        else:
            parts.append('*'+part)
    parts.append('*final')  # ensure that alpha/beta/candidate are before final
    return parts


def _split_version_components(s):
    """Split version string into individual tokens.

    pkg_resources does this using a regexp: (\d+ | [a-z]+ | \.| -)
    Unfortunately the 're' module isn't in the bootstrap, so we have to do
    an equivalent parse by hand.  Forunately, that's pretty easy.
    """
    comps = []
    start = 0
    while start < len(s):
        end = start+1
        if s[start].isdigit():
            while end < len(s) and s[end].isdigit():
                end += 1
        elif s[start].isalpha():
            while end < len(s) and s[end].isalpha():
                end += 1
        elif s[start] in (".","-"):
            pass
        else:
            while end < len(s) and not (s[end].isdigit() or s[end].isalpha() or s[end] in (".","-")):
                end += 1
        comps.append(s[start:end])
        start = end
    return comps


def get_original_filename(backname):
    """Given a backup filename, get the original name to which it refers.

    This is only really possible if the original file actually exists and
    is not guaranteed to be correct in all cases; but unless you do something
    silly it should work out OK.

    If no matching original file is found, None is returned.
    """
    filtered = ".".join([n for n in backname.split(".") if n != "old"])
    for nm in listdir(dirname(backname)):
        if nm == backname:
            continue
        if filtered == ".".join([n for n in nm.split(".") if n != "old"]):
            return pathjoin(dirname(backname),nm)
    return None


_locked_version_dirs = {}

def lock_version_dir(vdir):
    """Lock the given version dir so it cannot be uninstalled."""
    if sys.platform == "win32":
        #  On win32, we just hold bootstrap file open for reading.
        #  This will prevent it from being renamed during uninstall.
        lockfile = pathjoin(vdir,ESKY_CONTROL_DIR,"bootstrap-manifest.txt")
        _locked_version_dirs.setdefault(vdir,[]).append(os_open(lockfile,0,0))
    else:
        #  On posix platforms we take a shared flock on esky-files/lockfile.txt.
        #  While fcntl.fcntl locks are apparently the new hotness, they have
        #  unfortunate semantics that we don't want for this application:
        #      * not inherited across fork()
        #      * released when closing *any* fd associated with that file
        #  fcntl.flock doesn't have these problems, but may fail on NFS.
        #  To complicate matters, python sometimes emulates flock with fcntl!
        #  We therefore use a separate lock file to avoid unpleasantness.
        lockfile = pathjoin(vdir,ESKY_CONTROL_DIR,"lockfile.txt")
        f = os_open(lockfile,0,0)
        _locked_version_dirs.setdefault(vdir,[]).append(f)
        fcntl.flock(f,fcntl.LOCK_SH)

def unlock_version_dir(vdir):
    """Unlock the given version dir, allowing it to be uninstalled."""
    os_close(_locked_version_dirs[vdir].pop())

if __rpython__:
    def main():
        bootstrap()
    def target(driver,args):
        """Target function for compiling a standalone bootstraper with PyPy."""
        def entry_point(argv):
             exit_code = 0
             #  TODO: resolve symlinks etc
             sys.executable = abspath(pathjoin(getcwd(),argv[0]))
             sys.argv = argv
             try:
                 main()
             except SystemExit, e:
                 exit_code = _exit_code[0]
             return exit_code
        return entry_point, None


########NEW FILE########
__FILENAME__ = errors
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.errors:  error classes for esky

These definitions live in a separate sub-module to avoid circular imports,
but you should access them directly from the main 'esky' namespace.

"""

class Error(Exception):
    """Base error class for esky."""
    pass

class EskyBrokenError(Error):
    """Error thrown when accessing a broken esky directory."""
    pass

class EskyLockedError(Error):
    """Error thrown when trying to lock an esky that's already locked."""
    pass

class VersionLockedError(Error):
    """Error thrown when trying to remove a locked version."""
    pass

class EskyVersionError(Error):
    """Error thrown when an invalid version is requested."""
    pass

class NoVersionFinderError(Error):
    """Error thrown when trying to find updates without a VersionFinder."""
    pass



########NEW FILE########
__FILENAME__ = finder
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.finder:  VersionFinder implementations for esky

This module provides the default VersionFinder implementations for esky. The
abstract base class "VersionFinder" defines the expected interface, while 
"DefaultVersionFinder" provides a simple default implementation that hits a
specified URL to look for new versions.

"""

from __future__ import with_statement

import os
import re
import stat
import urllib
import urllib2
import zipfile
import shutil
import tempfile
import errno
from urlparse import urlparse, urljoin

from esky.bootstrap import parse_version, join_app_version
from esky.errors import *
from esky.util import deep_extract_zipfile, copy_ownership_info, \
                      ESKY_CONTROL_DIR, ESKY_APPDATA_DIR, \
                      really_rmtree, really_rename
from esky.patch import apply_patch, PatchError


class VersionFinder(object):
    """Base VersionFinder class.

    This class defines the interface expected of a VersionFinder object.
    The important methods expected from any VersionFinder are:

        find_versions:  get a list of all available versions for a given esky

        fetch_version:  make the specified version available locally
                        (e.g. download it from the internet)

        fetch_version_iter:  like fetch_version but yielding progress updates
                             during its execution

        has_version:  check that the specified version is available locally

        cleanup:  perform maintenance/cleanup tasks in the workdir
                  (e.g. removing old or broken downloads)

        needs_cleanup:  check whether maintenance/cleanup tasks are required

    """

    def __init__(self):
        pass

    def needs_cleanup(self,app):
        """Check whether the cleanup() method has any work to do."""
        return False

    def cleanup(self,app):
        """Perform maintenance tasks in the working directory."""
        pass

    def find_versions(self,app):
        """Find available versions of the app, returned as a list."""
        raise NotImplementedError

    def fetch_version(self,app,version,callback=None):
        """Fetch a specific version of the app into a local directory.

        If specified, `callback` must be a callable object taking a dict as
        its only argument.  It will be called periodically with status info
        about the progress of the download.
        """
        for status in self.fetch_version_iter(app,version):
            if callback is not None:
                callback(status)
        return self.has_version(app,version)

    def fetch_version_iter(self,app,version):
        """Fetch a specific version of the app, using iterator control flow.

        This is just like the fetch_version() method, but it returns an
        iterator which you must step through in order to process the download
        The items yielded by the iterator are the same as those that would
        be received by the callback function in fetch_version().
        """
        raise NotImplementedError

    def has_version(self,app,version):
        """Check whether a specific version of the app is available locally.

        Returns either False, or the path to the unpacked version directory.
        """
        raise NotImplementedError



class DefaultVersionFinder(VersionFinder):
    """VersionFinder implementing simple default download scheme.

    DefaultVersionFinder expects to be given a download url, which it will
    hit looking for new versions packaged as zipfiles.  These are simply
    downloaded and extracted on request.

    Zipfiles suitable for use with this class can be produced using the
    "bdist_esky" distutils command.  It also supports simple differential
    updates as produced by the "bdist_esky_patch" command.
    """

    def __init__(self,download_url):
        self.download_url = download_url
        super(DefaultVersionFinder,self).__init__()
        self.version_graph = VersionGraph()

    def _workdir(self,app,nm,create=True):
        """Get full path of named working directory, inside the given app."""
        updir = app._get_update_dir()
        workdir = os.path.join(updir,nm)
        if create:
            for target in (updir,workdir):
                try:
                    os.mkdir(target)
                except OSError, e:
                    if e.errno not in (errno.EEXIST,183):
                        raise
                else:
                    copy_ownership_info(app.appdir,target)
        return workdir

    def needs_cleanup(self,app):
        """Check whether the cleanup() method has any work to do."""
        dldir = self._workdir(app,"downloads",create=False)
        if os.path.isdir(dldir):
            for nm in os.listdir(dldir):
                return True
        updir = self._workdir(app,"unpack",create=False)
        if os.path.isdir(updir):
            for nm in os.listdir(updir):
                return True
        rddir = self._workdir(app,"ready",create=False)
        if os.path.isdir(rddir):
            for nm in os.listdir(rddir):
                return True
        return False

    def cleanup(self,app):
        # TODO: hang onto the latest downloaded version
        dldir = self._workdir(app,"downloads")
        for nm in os.listdir(dldir):
            os.unlink(os.path.join(dldir,nm))
        updir = self._workdir(app,"unpack")
        for nm in os.listdir(updir):
            really_rmtree(os.path.join(updir,nm))
        rddir = self._workdir(app,"ready")
        for nm in os.listdir(rddir):
            really_rmtree(os.path.join(rddir,nm))

    def open_url(self,url):
        f = urllib2.urlopen(url, timeout=30)
        try:
            size = f.headers.get("content-length",None)
            if size is not None:
                size = int(size)
        except ValueError:
            pass
        else:
            f.size = size
        return f

    def find_versions(self,app):
        version_re = "[a-zA-Z0-9\\.-_]+"
        appname_re = "(?P<version>%s)" % (version_re,)
        name_re = "(%s|%s)" % (app.name, urllib.quote(app.name))
        appname_re = join_app_version(name_re,appname_re,app.platform)
        filename_re = "%s\\.(zip|exe|from-(?P<from_version>%s)\\.patch)"
        filename_re = filename_re % (appname_re,version_re,)
        link_re = "href=['\"](?P<href>([^'\"]*/)?%s)['\"]" % (filename_re,)
        # Read the URL.  If this followed any redirects, update the
        # recorded URL to match the final endpoint.
        df = self.open_url(self.download_url)
        try:
            if df.url != self.download_url:
                self.download_url = df.url
        except AttributeError:
            pass
        # TODO: would be nice not to have to guess encoding here.
        try:
            downloads = df.read().decode("utf-8")
        finally:
            df.close()
        for match in re.finditer(link_re,downloads,re.I):
            version = match.group("version")
            href = match.group("href")
            from_version = match.group("from_version")
            # TODO: try to assign costs based on file size.
            if from_version is None:
                cost = 40
            else:
                cost = 1
            self.version_graph.add_link(from_version or "",version,href,cost)
        return self.version_graph.get_versions(app.version)

    def fetch_version_iter(self,app,version):
        #  There's always the possibility that a file fails to download or 
        #  that a patch fails to apply.  _fetch_file_iter and _prepare_version
        #  will remove such files from the version graph; we loop until we find
        #  a patch path that works, or we run out of options.
        name = self._ready_name(app,version)
        while not os.path.exists(name):
            try:
                path = self.version_graph.get_best_path(app.version,version)
            except KeyError:
                raise EskyVersionError(version)
            if path is None:
                raise EskyVersionError(version)
            local_path = []
            try:
                for url in path:
                    for status in self._fetch_file_iter(app,url):
                        if status["status"] == "ready":
                            local_path.append((status["path"],url))
                        else:
                            yield status
                self._prepare_version(app,version,local_path)
            except (PatchError,EskyVersionError,EnvironmentError), e:
                yield {"status":"retrying","size":None,"exception":e}
        yield {"status":"ready","path":name}

    def _fetch_file_iter(self,app,url):
        nm = os.path.basename(urlparse(url).path)
        outfilenm = os.path.join(self._workdir(app,"downloads"),nm)
        if not os.path.exists(outfilenm):
            try:
                infile = self.open_url(urljoin(self.download_url,url))
                outfile_size = 0
                # The to determine size of download, so that we can
                # detect corrupted or truncated downloads.
                try:
                    infile_size = infile.size
                except AttributeError:
                    try:
                        fh = infile.fileno()
                    except AttributeError:
                        infile_size = None
                    else:
                        infile_size = os.fstat(fh).st_size
                # Read it into a temporary file, then rename into place.
                try:
                    partfilenm = outfilenm + ".part"
                    partfile = open(partfilenm,"wb")
                    try:
                        data = infile.read(1024*64)
                        while data:
                            yield {"status": "downloading",
                                   "size": infile_size,
                                   "received": partfile.tell(),
                            }
                            partfile.write(data)
                            outfile_size += len(data)
                            data = infile.read(1024*64)
                        if infile_size is not None:
                            if outfile_size != infile_size:
                                err = "corrupted download: %s" % (url,)
                                raise IOError(err)
                    except Exception:
                        partfile.close()
                        os.unlink(partfilenm)
                        raise
                    else:
                        partfile.close()
                        really_rename(partfilenm,outfilenm)
                finally:
                    infile.close()
            except Exception:
                # Something went wrong.  To avoid infinite looping, we
                # must remove that file from the link graph.
                self.version_graph.remove_all_links(url)
                raise
        yield {"status":"ready","path":outfilenm}

    def _prepare_version(self,app,version,path):
        """Prepare the requested version from downloaded data.

        This method is responsible for unzipping downloaded versions, applying
        patches and so-forth, and making the result available as a local
        directory ready for renaming into the appdir.
        """
        uppath = tempfile.mkdtemp(dir=self._workdir(app,"unpack"))
        try:
            if not path:
                #  There's nothing to prepare, just copy the current version.
                self._copy_best_version(app,uppath)
            else:
                if path[0][0].endswith(".patch"):
                    #  We're direcly applying a series of patches.
                    #  Copy the current version across and go from there.
                    try:
                        self._copy_best_version(app,uppath)
                    except EnvironmentError, e:
                        self.version_graph.remove_all_links(path[0][1])
                        err = "couldn't copy current version: %s" % (e,)
                        raise PatchError(err)
                    patches = path
                else:
                    #  We're starting from a zipfile.  Extract the first dir
                    #  containing more than a single item and go from there.
                    try:
                        deep_extract_zipfile(path[0][0],uppath)
                    except (zipfile.BadZipfile,zipfile.LargeZipFile):
                        self.version_graph.remove_all_links(path[0][1])
                        try:
                            os.unlink(path[0][0])
                        except EnvironmentError:
                            pass
                        raise
                    patches = path[1:]
                # TODO: remove compatability hooks for ESKY_APPDATA_DIR="".
                # If a patch fails to apply because we've put an appdata dir
                # where it doesn't expect one, try again with old layout. 
                for _ in xrange(2):
                    #  Apply any patches in turn.
                    for (patchfile,patchurl) in patches:
                        try:
                            try:
                                with open(patchfile,"rb") as f:
                                    apply_patch(uppath,f)
                            except EnvironmentError, e:
                                if e.errno not in (errno.ENOENT,):
                                    raise
                                if not path[0][0].endswith(".patch"):
                                    raise
                                really_rmtree(uppath)
                                os.mkdir(uppath)
                                self._copy_best_version(app,uppath,False)
                                break
                        except (PatchError,EnvironmentError):
                            self.version_graph.remove_all_links(patchurl)
                            try:
                                os.unlink(patchfile)
                            except EnvironmentError:
                                pass
                            raise
                    else:
                        break
            # Find the actual version dir that we're unpacking.
            # TODO: remove compatability hooks for ESKY_APPDATA_DIR=""
            vdir = join_app_version(app.name,version,app.platform)
            vdirpath = os.path.join(uppath,ESKY_APPDATA_DIR,vdir)
            if not os.path.isdir(vdirpath):
                vdirpath = os.path.join(uppath,vdir)
                if not os.path.isdir(vdirpath):
                    self.version_graph.remove_all_links(path[0][1])
                    err = version + ": version directory does not exist"
                    raise EskyVersionError(err)
            # Move anything that's not the version dir into "bootstrap" dir.
            ctrlpath = os.path.join(vdirpath,ESKY_CONTROL_DIR)
            bspath = os.path.join(ctrlpath,"bootstrap")
            if not os.path.isdir(bspath):
                os.makedirs(bspath)
            for nm in os.listdir(uppath):
                if nm != vdir and nm != ESKY_APPDATA_DIR:
                    really_rename(os.path.join(uppath,nm),
                                  os.path.join(bspath,nm))
            # Check that it has an esky-files/bootstrap-manifest.txt file
            bsfile = os.path.join(ctrlpath,"bootstrap-manifest.txt")
            if not os.path.exists(bsfile):
                self.version_graph.remove_all_links(path[0][1])
                err = version + ": version has no bootstrap-manifest.txt"
                raise EskyVersionError(err)
            # Make it available for upgrading, replacing anything
            # that we previously had available.
            rdpath = self._ready_name(app,version)
            tmpnm = None
            try:
                if os.path.exists(rdpath):
                    tmpnm = rdpath + ".old"
                    while os.path.exists(tmpnm):
                        tmpnm = tmpnm + ".old"
                    really_rename(rdpath,tmpnm)
                really_rename(vdirpath,rdpath)
            finally:
                if tmpnm is not None:
                    really_rmtree(tmpnm)
            #  Clean up any downloaded files now that we've used them.
            for (filenm,_) in path:
                os.unlink(filenm)
        finally:
            really_rmtree(uppath)

    def _copy_best_version(self,app,uppath,force_appdata_dir=True):
        """Copy the best version directory from the given app.

        This copies the best version directory from the given app into the
        unpacking path.  It's useful for applying patches against an existing
        version.
        """
        best_vdir = join_app_version(app.name,app.version,app.platform)
        #  TODO: remove compatability hooks for ESKY_APPDATA_DIR="".
        source = os.path.join(app.appdir,ESKY_APPDATA_DIR,best_vdir)
        if not os.path.exists(source):
            source = os.path.join(app.appdir,best_vdir)
        if not force_appdata_dir:
            dest = uppath
        else:
            dest = os.path.join(uppath,ESKY_APPDATA_DIR)
        try:
            os.mkdir(dest)
        except OSError, e:
            if e.errno not in (errno.EEXIST,183):
                raise
        shutil.copytree(source,os.path.join(dest,best_vdir))
        mfstnm = os.path.join(source,ESKY_CONTROL_DIR,"bootstrap-manifest.txt")
        with open(mfstnm,"r") as manifest:
            for nm in manifest:
                nm = nm.strip()
                bspath = os.path.join(app.appdir,nm)
                dstpath = os.path.join(uppath,nm)
                if os.path.isdir(bspath):
                    shutil.copytree(bspath,dstpath)
                else:
                    if not os.path.isdir(os.path.dirname(dstpath)):
                        os.makedirs(os.path.dirname(dstpath))
                    shutil.copy2(bspath,dstpath)

    def has_version(self,app,version):
        path = self._ready_name(app,version)
        if os.path.exists(path):
            return path
        return False

    def _ready_name(self,app,version):
        version = join_app_version(app.name,version,app.platform)
        return os.path.join(self._workdir(app,"ready"),version)


class LocalVersionFinder(DefaultVersionFinder):
    """VersionFinder that looks only in a local directory.

    This VersionFinder subclass looks for updates in a specific local
    directory.  It's probably only useful for testing purposes.
    """

    def find_versions(self,app):
        version_re = "[a-zA-Z0-9\\.\\-_]+"
        appname_re = "(?P<version>%s)" % (version_re,)
        appname_re = join_app_version(app.name,appname_re,app.platform)
        filename_re = "%s\\.(zip|exe|from-(?P<from_version>%s)\\.patch)"
        filename_re = filename_re % (appname_re,version_re,)
        for nm in os.listdir(self.download_url):
            match = re.match(filename_re,nm)
            if match:
                version = match.group("version")
                from_version = match.group("from_version")
                if from_version is None:
                    cost = 40
                else:
                    cost = 1
                self.version_graph.add_link(from_version or "",version,nm,cost)
        return self.version_graph.get_versions(app.version)

    def open_url(self,url):
        return open(os.path.join(self.download_url,url),"rb")


class VersionGraph(object):
    """Class for managing links between different versions.

    This class implements a simple graph-based approach to planning upgrades
    between versions.  It allows you to specify "links" from one version to
    another, each with an associated cost.  You can then do a graph traversal
    to find the lowest-cose route between two versions.

    There is always a special source node with value "", which it is possible
    to reach at zero cost from any other version.  Use this to represent a full
    download, which can reach a specific version from any other version.
    """

    def __init__(self):
        self._links = {"":{}}

    def add_link(self,source,target,via,cost):
        """Add a link from source to target."""
        if source not in self._links:
            self._links[source] = {}
        if target not in self._links:
            self._links[target] = {}
        from_source = self._links[source]
        to_target = from_source.setdefault(target,{})
        if via in to_target:
            to_target[via] = min(to_target[via],cost)
        else:
            to_target[via] = cost

    def remove_all_links(self,via):
        for source in self._links:
            for target in self._links[source]:
                self._links[source][target].pop(via,None)

    def get_versions(self,source):
        """List all versions reachable from the given source version."""
        # TODO: be more efficient here
        best_paths = self.get_best_paths(source)
        return [k for (k,v) in best_paths.iteritems() if k and v]

    def get_best_path(self,source,target):
        """Get the best path from source to target.

        This method returns a list of "via" links representing the lowest-cost
        path from source to target.
        """
        return self.get_best_paths(source)[target]

    def get_best_paths(self,source):
        """Get the best path from source to every other version.

        This returns a dictionary mapping versions to lists of "via" links.
        Each entry gives the lowest-cost path from the given source version
        to that version.
        """
        remaining = set(v for v in self._links)
        best_costs = dict((v,_inf) for v in remaining)
        best_paths = dict((v,None) for v in remaining)
        best_costs[source] = 0
        best_paths[source] = []
        best_costs[""] = 0
        best_paths[""] = []
        while remaining:
            (cost,best) = sorted((best_costs[v],v) for v in remaining)[0]
            if cost is _inf:
                break
            remaining.remove(best)
            for v in self._links[best]:
                (v_cost,v_link) = self._get_best_link(best,v)
                if cost + v_cost < best_costs[v]:
                    best_costs[v] = cost + v_cost
                    best_paths[v] = best_paths[best] + [v_link]
        return best_paths
                
    def _get_best_link(self,source,target):
        if source not in self._links:
            return (_inf,"")
        if target not in self._links[source]:
            return (_inf,"")
        vias = self._links[source][target]
        if not vias:
            return (_inf,"")
        vias = sorted((cost,via) for (via,cost) in vias.iteritems())
        return vias[0]


class _Inf(object):
    """Object that is greater than everything."""
    def __lt__(self,other):
        return False
    def __le__(self,other):
        return False
    def __gt__(self,other):
        return True
    def __ge__(self,other):
        return True
    def __eq__(self,other):
        return other is self
    def __ne__(self,other):
        return other is not self
    def __cmp___(self,other):
        return 1
    def __add__(self,other):
        return self
    def __radd__(self,other):
        return self
    def __iadd__(self,other):
        return self
    def __sub__(self,other):
        return self
    def __rsub__(self,other):
        return self
    def __isub__(self,other):
        return self
_inf = _Inf()



########NEW FILE########
__FILENAME__ = fallback
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.fstransact.fallback: fallback implementation for FSTransaction

"""

import os
import sys
import shutil

from esky.util import get_backup_filename, files_differ, really_rename


class FSTransaction(object):
    """Utility class for transactionally operating on the filesystem.

    This particular implementation is the fallback for systems that don't
    support transactional filesystem operations.
    """

    def __init__(self,root=None):
        if root is None:
            self.root = None
        else:
            self.root = os.path.normpath(os.path.abspath(root))
            if self.root.endswith(os.sep):
                self.root = self.root[:-1]
        self.pending = []

    def _check_path(self,path):
        if self.root is not None:
            path = os.path.normpath(os.path.join(self.root,path))
            if len(self.root) == 2 and sys.platform == "win32":
                prefix = self.root
            else:
                prefix = self.root + os.sep
            if not path.startswith(prefix):
                err = "path is outside transaction root: %s" % (path,)
                raise ValueError(err)
        return path

    def move(self,source,target):
        source = self._check_path(source)
        target = self._check_path(target)
        if os.path.isdir(source):
            if os.path.isdir(target):
                s_names = os.listdir(source)
                for nm in s_names:
                    self.move(os.path.join(source,nm),
                              os.path.join(target,nm))
                for nm in os.listdir(target):
                    if nm not in s_names:
                        self.remove(os.path.join(target,nm))
                self.remove(source)
            else:
                self.pending.append(("_move",source,target))
        else:
            if os.path.isdir(target) or files_differ(source,target):
                self.pending.append(("_move",source,target))
            else:
                self.pending.append(("_remove",source))

    def _move(self,source,target):
        if sys.platform == "win32" and os.path.exists(target):
            #  os.rename won't overwite an existing file on win32.
            #  We also want to use this on files that are potentially open.
            #  Renaming the target out of the way is the best we can do :-(
            target_old = target + ".old"
            while os.path.exists(target_old):
                target_old = target_old + ".old"
            really_rename(target,target_old)
            try:
                really_rename(source,target)
            except:
                really_rename(target_old,target)
                raise
            else:
                try:
                    self._remove(target_old)
                except EnvironmentError:
                    pass
        else:
            target_old = None
            if os.path.isdir(target) and os.path.isfile(source):
                target_old = target + ".old"
                while os.path.exists(target_old):
                    target_old = target_old + ".old"
                really_rename(target,target_old)
            elif os.path.isfile(target) and os.path.isdir(source):
                target_old = target + ".old"
                while os.path.exists(target_old):
                    target_old = target_old + ".old"
                really_rename(target,target_old)
            self._create_parents(target)
            really_rename(source,target)
            if target_old is not None:
                self._remove(target_old)

    def _create_parents(self,target):
        parents = [target]
        while not os.path.exists(os.path.dirname(parents[-1])):
            parents.append(os.path.dirname(parents[-1]))
        for parent in reversed(parents[1:]):
            os.mkdir(parent)

    def copy(self,source,target):
        source = self._check_path(source)
        target = self._check_path(target)
        if os.path.isdir(source):
            if os.path.isdir(target):
                s_names = os.listdir(source)
                for nm in s_names:
                    self.copy(os.path.join(source,nm),
                              os.path.join(target,nm))
                for nm in os.listdir(target):
                    if nm not in s_names:
                        self.remove(os.path.join(target,nm))
            else:
                self.pending.append(("_copy",source,target))
        else:
            if os.path.isdir(target) or files_differ(source,target):
                self.pending.append(("_copy",source,target))

    def _copy(self,source,target):
        is_win32 = (sys.platform == "win32")
        if is_win32 and os.path.exists(target) and target != source:
            target_old = get_backup_filename(target)
            really_rename(target,target_old)
            try:
                self._do_copy(source,target)
            except:
                really_rename(target_old,target)
                raise
            else:
                try:
                    os.unlink(target_old)
                except EnvironmentError:
                    pass
        else:
            target_old = None
            if os.path.isdir(target) and os.path.isfile(source):
                target_old = get_backup_filename(target)
                really_rename(target,target_old)
            elif os.path.isfile(target) and os.path.isdir(source):
                target_old = get_backup_filename(target)
                really_rename(target,target_old)
            self._do_copy(source,target)
            if target_old is not None:
                self._remove(target_old)

    def _do_copy(self,source,target):
        self._create_parents(target)
        if os.path.isfile(source):
            shutil.copy2(source,target)
        else:
            shutil.copytree(source,target)

    def remove(self,target):
        target = self._check_path(target)
        self.pending.append(("_remove",target))

    def _remove(self,target):
        if os.path.isfile(target):
            os.unlink(target)
        elif os.path.isdir(target):
            for nm in os.listdir(target):
                self._remove(os.path.join(target,nm))
            os.rmdir(target)

    def commit(self):
        for op in self.pending:
            getattr(self,op[0])(*op[1:])

    def abort(self):
        del self.pending[:]



########NEW FILE########
__FILENAME__ = win32txf
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.fstransact.win32fxt:  win32 transactional filesystem operations

"""


import os
import sys
import errno
import shutil

from esky.util import get_backup_filename, files_differ

if sys.platform != "win32":
    raise ImportError("win32fxt only available on win32 platform")

def check_call(func):
    def wrapper(*args,**kwds):
        res = func(*args,**kwds)
        if not res or res == 0xFFFFFFFF or res == -1:
            raise ctypes.WinError()
        return res
    return wrapper


try:
    import ctypes
    ktmw32 = ctypes.windll.ktmw32
    CreateTransaction = check_call(ktmw32.CreateTransaction)
    CommitTransaction = check_call(ktmw32.CommitTransaction)
    RollbackTransaction = check_call(ktmw32.RollbackTransaction)
    kernel32 = ctypes.windll.kernel32
    MoveFileTransacted = check_call(kernel32.MoveFileTransactedW)
    CopyFileTransacted = check_call(kernel32.CopyFileTransactedW)
    DeleteFileTransacted = check_call(kernel32.DeleteFileTransactedW)
    RemoveDirectoryTransacted = check_call(kernel32.RemoveDirectoryTransactedW)
    CreateDirectoryTransacted = check_call(kernel32.CreateDirectoryTransactedW)
except (WindowsError,AttributeError):
    raise ImportError("win32 TxF is not available")


ERROR_TRANSACTIONAL_OPEN_NOT_ALLOWED = 6832


def unicode_path(path):
    if sys.version_info[0] < 3:
        if not isinstance(path, unicode):
            path = path.decode(sys.getfilesystemencoding())
    return path


class FSTransaction(object):
    """Utility class for transactionally operating on the filesystem.

    This particular implementation uses the transaction services provided
    by Windows Vista and later (from ktmw32.dll).
    """

    def __init__(self,root=None):
        if root is None:
            self.root = None
        else:
            root = unicode_path(root)
            self.root = os.path.normpath(os.path.abspath(root))
            if self.root.endswith(os.sep):
                self.root = self.root[:-1]
        self.trnid = CreateTransaction(None,0,0,0,0,None,"")
        self._check_root()

    def _check_root(self):
        if self.root is not None:
            #  Verify that files under the given root can actually be
            #  operated on transactionally.  We do this by trying to move
            #  the root directory to itself.  This should always fail, but
            #  will fail with a transaction error if they're not supported.
            try:
                self._move(self.root,self.root)
            except WindowsError, e:
                if e.winerror == ERROR_TRANSACTIONAL_OPEN_NOT_ALLOWED:
                    raise
            finally:
                self.abort()
            self.trnid = CreateTransaction(None,0,0,0,0,None,"")
        
    def _check_path(self,path):
        if self.root is not None:
            path = os.path.normpath(os.path.join(self.root,path))
            if len(self.root) == 2:
                prefix = self.root
            else:
                prefix = self.root + os.sep
            if not path.startswith(prefix):
                err = "path is outside transaction root: %s" % (path,)
                raise ValueError(err)
        return path

    def move(self,source,target):
        source = self._check_path(source)
        target = self._check_path(target)
        if os.path.isdir(source):
            if os.path.isdir(target):
                s_names = os.listdir(source)
                for nm in s_names:
                    self.move(os.path.join(source,nm),
                              os.path.join(target,nm))
                for nm in os.listdir(target):
                    if nm not in s_names:
                        self._remove(os.path.join(target,nm))
                self._remove(source)
            else:
                self._move(source,target)
        else:
            if os.path.isdir(target) or files_differ(source,target):
                self._move(source,target)
            else:
                self._remove(source)

    def _move(self,source,target):
        source = unicode_path(source)
        target = unicode_path(target)
        if os.path.exists(target) and target != source:
            target_old = get_backup_filename(target)
            MoveFileTransacted(target,target_old,None,None,1,self.trnid)
            MoveFileTransacted(source,target,None,None,1,self.trnid)
            try:
                self._remove(target_old)
            except EnvironmentError:
                pass
        else:
            self._create_parents(target)
            MoveFileTransacted(source,target,None,None,1,self.trnid)

    def _create_parents(self,target):
        parents = [target]
        while not os.path.exists(os.path.dirname(parents[-1])):
            parents.append(os.path.dirname(parents[-1]))
            if not parents[-1]:
                parents = parents[:-1]
                break
        for parent in reversed(parents[1:]):
            try:
                CreateDirectoryTransacted(None,parent,0,self.trnid)
            except WindowsError, e:
                if e.winerror != 183:
                    raise

    def copy(self,source,target):
        source = self._check_path(source)
        target = self._check_path(target)
        if os.path.isdir(source):
            if os.path.isdir(target):
                s_names = os.listdir(source)
                for nm in s_names:
                    self.copy(os.path.join(source,nm),
                              os.path.join(target,nm))
                for nm in os.listdir(target):
                    if nm not in s_names:
                        self._remove(os.path.join(target,nm))
            else:
                self._copy(source,target)
        else:
            if os.path.isdir(target) or files_differ(source,target):
                self._copy(source,target)

    def _copy(self,source,target):
        source = unicode_path(source)
        target = unicode_path(target)
        if os.path.exists(target) and target != source:
            target_old = get_backup_filename(target)
            MoveFileTransacted(target,target_old,None,None,1,self.trnid)
            self._do_copy(source,target)
            try:
                self._remove(target_old)
            except EnvironmentError:
                pass
        else:
            target_old = None
            if os.path.isdir(target) and target != source:
                target_old = get_backup_filename(target)
                MoveFileTransacted(target,target_old,None,None,1,self.trnid)
            self._do_copy(source,target)
            if target_old is not None:
                self._remove(target_old)

    def _do_copy(self,source,target):
        self._create_parents(target)
        if os.path.isdir(source):
            CreateDirectoryTransacted(None,target,0,self.trnid)
            for nm in os.listdir(source):
                self._do_copy(os.path.join(source,nm),
                              os.path.join(target,nm))
        else:
            CopyFileTransacted(source,target,None,None,None,0,self.trnid)

    def remove(self,target):
        target = self._check_path(target)
        self._remove(target)

    def _remove(self,target):
        target = unicode_path(target)
        if os.path.isdir(target):
            for nm in os.listdir(target):
                self.remove(os.path.join(target,nm))
            try:
                RemoveDirectoryTransacted(target,self.trnid)
            except EnvironmentError, e:
                if e.errno != errno.ENOENT:
                    raise
        else:
            try:
                DeleteFileTransacted(target,self.trnid)
            except EnvironmentError, e:
                if e.errno != errno.ENOENT:
                    raise

    def commit(self):
        CommitTransaction(self.trnid)

    def abort(self):
        RollbackTransaction(self.trnid)



########NEW FILE########
__FILENAME__ = patch
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.patch:  directory diffing and patching support for esky.

This module forms the basis of esky's differential update support.  It defines
a compact protocol to encode the differences between two directories, and
functions to calculate and apply patches based on this protocol.  It exposes
the following functions:

  write_patch(srcpath,tgtpath,stream):

      calculate the differences between directories (or files) "srcpath"
      and "tgtpath", and write a patch to transform the format into the
      latter to the file-like object "stream".

  apply_patch(tgtpath,stream):

      read a patch from the file-like object "stream" and apply it to the
      directory (or file) at "tgtpath".  For directories, the patch is
      applied *in-situ*.  If you want to guard against patches that fail to
      apply, patch a copy then copy it back over the original.


This module can also be executed as a script (e.g. "python -m esky.patch ...")
to calculate or apply patches from the command-line:

  python -m esky.patch diff <source> <target> <patch>

      generate a patch to transform <source> into <target>, and write it into
      file <patch> (or stdout if not specified).

  python -m esky.patch patch <source> <patch>

      transform <source> by applying the patches in the file <patch> (or
      stdin if not specified.  The modifications are made in-place.

To patch or diff zipfiles as though they were a directory, pass the "-z" or
"--zipped" option on the command-line, e.g:

  python -m esky.patch --zipped diff <source>.zip <target>.zip <patch>

To "deep unzip" the zipfiles so that any leading directories are ignored, use
the "-Z" or "--deep-zipped" option instead:

  python -m esky.patch -Z diff <source>.zip <target>.zip <patch>

This can be useful for generating differential esky updates by hand, when you
already have the corresponding zip files.

"""

from __future__ import with_statement
try:
    bytes = bytes
except NameError:
    bytes = str


import os
import sys
import bz2
import time
import shutil
import hashlib
import optparse
import zipfile
import tempfile
if sys.version_info[0] < 3:
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
       from StringIO import StringIO as BytesIO
else:
    from io import BytesIO


#  Try to get code for working with bsdiff4-format patches.
#
#  We have three options:
#     * use the cleaned-up bsdiff4 module by Ilan Schnell.
#     * use the original cx-bsdiff module by Anthony Tuininga.
#     * use a pure-python patch-only version.
#
#  We define each one if we can, so it's available for testing purposes.
#  We then set the main "bsdiff4" name equal to the best option.
#
#  TODO: move this into a support module, it clutters up reading
#        of the code in this file
#

try:
    import bsdiff4 as bsdiff4_native
except ImportError:
    bsdiff4_native = None


try:
    import bsdiff as _cx_bsdiff
except ImportError:
    bsdiff4_cx = None
else:
    #  This wrapper code basically takes care of the bsdiff patch format,
    #  translating to/from the raw control information for the algorithm.
    class bsdiff4_cx(object):
        @staticmethod
        def diff(source,target):
            (tcontrol,bdiff,bextra) = _cx_bsdiff.Diff(source,target)
            #  Write control tuples as series of offts
            bcontrol = BytesIO()
            for c in tcontrol:
                for x in c:
                    bcontrol.write(_encode_offt(x))
            del tcontrol
            bcontrol = bcontrol.getvalue()
            #  Compress each block
            bcontrol = bz2.compress(bcontrol)
            bdiff = bz2.compress(bdiff)
            bextra = bz2.compress(bextra)
            #  Final structure is:
            #  (header)(len bcontrol)(len bdiff)(len target)(bcontrol)\
            #  (bdiff)(bextra)
            return "".join((
                "BSDIFF40",
                _encode_offt(len(bcontrol)),
                _encode_offt(len(bdiff)),
                _encode_offt(len(target)),
                bcontrol,
                bdiff,
                bextra,
            ))
        @staticmethod
        def patch(source,patch):
            #  Read the length headers
            l_bcontrol = _decode_offt(patch[8:16])
            l_bdiff = _decode_offt(patch[16:24])
            l_target = _decode_offt(patch[24:32])
            #  Read the three data blocks
            e_bcontrol = 32 + l_bcontrol
            e_bdiff = e_bcontrol + l_bdiff
            bcontrol = bz2.decompress(patch[32:e_bcontrol])
            bdiff = bz2.decompress(patch[e_bcontrol:e_bdiff])
            bextra = bz2.decompress(patch[e_bdiff:])
            #  Decode the control tuples 
            tcontrol = []
            for i in xrange(0,len(bcontrol),24):
                tcontrol.append((
                    _decode_offt(bcontrol[i:i+8]),
                    _decode_offt(bcontrol[i+8:i+16]),
                    _decode_offt(bcontrol[i+16:i+24]),
                ))
            #  Actually do the patching.
            return _cx_bsdiff.Patch(source,l_target,tcontrol,bdiff,bextra)


class bsdiff4_py(object):
    """Pure-python version of bsdiff4 module that can only patch, not diff.

    By providing a pure-python fallback, we don't force frozen apps to 
    bundle the bsdiff module in order to make use of patches.  Besides,
    the patch-applying algorithm is very simple.
    """
    #  Expose a diff method if we have one from another module, to
    #  make it easier to test this class.
    if bsdiff4_native is not None:
        @staticmethod
        def diff(source,target):
            return bsdiff4_native.diff(source,target)
    elif bsdiff4_cx is not None:
        @staticmethod
        def diff(source,target):
            return bsdiff4_cx.diff(source,target)
    else:
        diff = None
    @staticmethod
    def patch(source,patch):
        #  Read the length headers
        l_bcontrol = _decode_offt(patch[8:16])
        l_bdiff = _decode_offt(patch[16:24])
        l_target = _decode_offt(patch[24:32])
        #  Read the three data blocks
        e_bcontrol = 32 + l_bcontrol
        e_bdiff = e_bcontrol + l_bdiff
        bcontrol = bz2.decompress(patch[32:e_bcontrol])
        bdiff = bz2.decompress(patch[e_bcontrol:e_bdiff])
        bextra = bz2.decompress(patch[e_bdiff:])
        #  Decode the control tuples 
        tcontrol = []
        for i in xrange(0,len(bcontrol),24):
            tcontrol.append((
                _decode_offt(bcontrol[i:i+8]),
                _decode_offt(bcontrol[i+8:i+16]),
                _decode_offt(bcontrol[i+16:i+24]),
            ))
        #  Actually do the patching.
        #  This is the bdiff4 patch algorithm in slow, pure python.
        source = BytesIO(source)
        result = BytesIO()
        bdiff = BytesIO(bdiff)
        bextra = BytesIO(bextra)
        for (x,y,z) in tcontrol:
            diff_data = bdiff.read(x)
            orig_data = source.read(x)
            if sys.version_info[0] < 3:
                for i in xrange(len(diff_data)):
                    result.write(chr((ord(diff_data[i])+ord(orig_data[i]))%256))
            else:
                for i in xrange(len(diff_data)):
                    result.write(bytes([(diff_data[i]+orig_data[i])%256]))
            result.write(bextra.read(y))
            source.seek(z,os.SEEK_CUR)
        return result.getvalue()


if bsdiff4_native is not None:
    bsdiff4 = bsdiff4_native
elif bsdiff4_cx is not None:
    bsdiff4 = bsdiff4_cx
else:
    bsdiff4 = bsdiff4_py


#  Default size of blocks to use when diffing a file.  4M seems reasonable.
#  Setting this higher generates smaller patches at the cost of higher
#  memory use (and bsdiff is a memory hog at the best of times...)
DIFF_WINDOW_SIZE = 1024 * 1024 * 4

#  Highest patch version that can be processed by this module.
HIGHEST_VERSION = 1

#  Header bytes included in the patch file
PATCH_HEADER = "ESKYPTCH".encode("ascii")


from esky.errors import Error
from esky.util import extract_zipfile, create_zipfile, deep_extract_zipfile,\
                      zipfile_common_prefix_dir, really_rmtree, really_rename

__all__ = ["PatchError","DiffError","main","write_patch","apply_patch",
           "Differ","Patcher"]



class PatchError(Error):
    """Error raised when a patch fails to apply."""
    pass

class DiffError(Error):
    """Error raised when a diff can't be generated."""
    pass


#  Commands used in the directory patching protocol.  Each of these is
#  encoded as a vint in the patch stream; unless we get really out of
#  control and have more than 127 commands, this means one byte per command.
#
#  It's very important that you don't reorder these commands.  Their order
#  in this list determines what byte each command is assigned, so doing
#  anything but adding to the end will break all existing patches!
#
_COMMANDS = [
 "END",           # END():               stop processing current context
 "SET_PATH",      # SET_PATH(path):      set current target path 
 "JOIN_PATH",     # JOIN_PATH(path):     join path to the current target
 "POP_PATH",      # POP_PATH(h):         pop one level off current target
 "POP_JOIN_PATH", # POP_JOIN_PATH(path): pop the current path, then join
 "VERIFY_MD5",    # VERIFY_MD5(dgst):    check md5 digest of current target
 "REMOVE",        # REMOVE():            remove the current target
 "MAKEDIR",       # MAKEDIR():           make directory at current target
 "COPY_FROM",     # COPY_FROM(path):     copy item at path to current target
 "MOVE_FROM",     # MOVE_FROM(path):     move item at path to current target
 "PF_COPY",       # PF_COPY(n):          patch file; copy n bytes from input
 "PF_SKIP",       # PF_SKIP(n):          patch file; skip n bytes from input
 "PF_INS_RAW",    # PF_INS_RAW(bytes):   patch file; insert raw bytes 
 "PF_INS_BZ2",    # PF_INS_BZ2(bytes):   patch file; insert unbzip'd bytes
 "PF_BSDIFF4",    # PF_BSDIFF4(n,p):     patch file; bsdiff4 from n input bytes
 "PF_REC_ZIP",    # PF_REC_ZIP(m,cs):    patch file; recurse into zipfile
 "CHMOD",         # CHMOD(mode):         set mode of current target
]

# Make commands available as global variables
for i,cmd in enumerate(_COMMANDS):
    globals()[cmd] = i


def apply_patch(target,stream,**kwds):
    """Apply patch commands from the given stream to the given target.

    'target' must be the path of a file or directory, and 'stream' an object
    supporting the read() method.  Patch protocol commands will be read from
    the stream and applied in sequence to the target.
    """
    Patcher(target,stream,**kwds).patch()


def write_patch(source,target,stream,**kwds):
    """Generate patch commands to transform source into target.

    'source' and 'target' must be paths to a file or directory, and 'stream'
    an object supporting the write() method.  Patch protocol commands to
    transform 'source' into 'target' will be generated and written sequentially
    to the stream.
    """
    Differ(stream,**kwds).diff(source,target)


def _read_vint(stream):
    """Read a vint-encoded integer from the given stream."""
    b = stream.read(1)
    if not b:
        raise EOFError
    b = ord(b)
    if b < 128:
        return b
    x = e = 0
    while b >= 128:
        x += (b - 128) << e
        e += 7
        b = stream.read(1)
        if not b:
            raise EOFError
        b = ord(b)
    x += (b << e)
    return x

if sys.version_info[0] > 2:
    def _write_vint(stream,x):
        """Write a vint-encoded integer to the given stream."""
        while x >= 128:
            b = x & 127
            stream.write(bytes([b | 128]))
            x = x >> 7
        stream.write(bytes([x]))
else:
    def _write_vint(stream,x):
        """Write a vint-encoded integer to the given stream."""
        while x >= 128:
            b = x & 127
            stream.write(chr(b | 128))
            x = x >> 7
        stream.write(chr(x))


def _read_zipfile_metadata(stream):
    """Read zipfile metadata from the given stream.

    The result is a zipfile.ZipFile object where all members are zero length.
    """
    return zipfile.ZipFile(stream,"r")


def _write_zipfile_metadata(stream,zfin):
    """Write zipfile metadata to the given stream.

    For simplicity, the metadata is represented as a zipfile with the same
    members as the given zipfile, but where they all have zero length.
    """
    zfout = zipfile.ZipFile(stream,"w")
    try:
        for zinfo in zfin.infolist():
            zfout.writestr(zinfo,"")
    finally:
        zfout.close()


def paths_differ(path1,path2):
    """Check whether two paths differ."""
    if os.path.isdir(path1):
        if not os.path.isdir(path2):
            return True
        for nm in os.listdir(path1):
            if paths_differ(os.path.join(path1,nm),os.path.join(path2,nm)):
                return True
        for nm in os.listdir(path2):
            if not os.path.exists(os.path.join(path1,nm)):
                return True
    elif os.path.isfile(path1):
        if not os.path.isfile(path2):
            return True
        if os.stat(path1).st_size != os.stat(path2).st_size:
            return True
        with open(path1,"rb") as f1:
            with open(path2,"rb") as f2:
                data1 = f1.read(1024*16)
                data2 = f2.read(1024*16)
                while data1:
                    if data1 != data2:
                        return True
                    data1 = f1.read(1024*16)
                    data2 = f2.read(1024*16)
                if data1 != data2:
                    return True
    elif os.path.exists(path2):
        return True
    return False

    

def calculate_digest(target,hash=hashlib.md5):
    """Calculate the digest of the given path.

    If the target is a file, its digest is calculated as normal.  If it is
    a directory, it is calculated from the names and digests of its contents.
    """
    d = hash()
    if os.path.isdir(target):
        for nm in sorted(os.listdir(target)):
            d.update(nm.encode("utf8"))
            d.update(calculate_digest(os.path.join(target,nm)))
    else:
        with open(target,"rb") as f:
            data = f.read(1024*16)
            while data:
                d.update(data)
                data = f.read(1024*16)
    return d.digest()


class Patcher(object):
    """Class interpreting our patch protocol.

    Instances of this class can be used to apply a sequence of patch commands
    to a target file or directory.  You can think of it as a little automaton
    that edits a directory in-situ.
    """

    def __init__(self,target,commands,dry_run=False):
        target = os.path.abspath(target)
        self.target = target
        self.new_target = None
        self.commands = commands
        self.root_dir = self.target
        self.infile = None
        self.outfile = None
        self.dry_run = dry_run
        self._workdir = tempfile.mkdtemp()
        self._context_stack = []

    def __del__(self):
        if self.infile:
            self.infile.close()
        if self.outfile:
            self.outfile.close()
        if self._workdir and shutil:
            really_rmtree(self._workdir)

    def _read(self,size):
        """Read the given number of bytes from the command stream."""
        return self.commands.read(size)

    def _read_int(self):
        """Read an integer from the command stream."""
        i = _read_vint(self.commands)
        if self.dry_run:
            print "  ", i
        return i

    def _read_command(self):
        """Read the next command to be processed."""
        cmd = _read_vint(self.commands)
        if self.dry_run:
            print _COMMANDS[cmd]
        return cmd

    def _read_bytes(self):
        """Read a bytestring from the command stream."""
        l = _read_vint(self.commands)
        bytes = self.commands.read(l)
        if len(bytes) != l:
            raise PatchError("corrupted bytestring")
        if self.dry_run:
            print "   [%s bytes]" % (len(bytes),)
        return bytes

    def _read_path(self):
        """Read a unicode path from the given stream."""
        l = _read_vint(self.commands)
        bytes = self.commands.read(l)
        if len(bytes) != l:
            raise PatchError("corrupted path")
        path = bytes.decode("utf-8")
        if self.dry_run:
            print "  ", path
        return path

    def _check_begin_patch(self):
        """Begin patching the current file, if not already.

        This method is called by all file-patching commands; if there is
        no file open for patching then the current target is opened.
        """
        if not self.outfile and not self.dry_run:
            if os.path.exists(self.target) and not os.path.isfile(self.target):
                really_rmtree(self.target)
            self.new_target = self.target + ".new"
            while os.path.exists(self.new_target):
                self.new_target += ".new"
            if os.path.exists(self.target):
                self.infile = open(self.target,"rb")
            else:
                self.infile = BytesIO("".encode("ascii"))
            self.outfile = open(self.new_target,"wb")
            if os.path.isfile(self.target):
                mod = os.stat(self.target).st_mode
                os.chmod(self.new_target,mod)

    def _check_end_patch(self):
        """Finish patching the current file, if there is one.

        This method is called by all non-file-patching commands; if there is
        a file open for patching then it is closed and committed.
        """
        if self.outfile and not self.dry_run:
            self.infile.close()
            self.infile = None
            self.outfile.close()
            self.outfile = None
            if os.path.exists(self.target):
                os.unlink(self.target)
                if sys.platform == "win32":
                    time.sleep(0.01)
            really_rename(self.new_target,self.target)
            self.new_target = None

    def _check_path(self,path=None):
        """Check that we're not traversing outside the root."""
        if path is None:
            path = self.target
        if path != self.root_dir:
            if not path.startswith(self.root_dir + os.sep):
                raise PatchError("traversed outside root_dir")

    def _blank_state(self):
        """Save current state, then blank it out.

        The previous state is returned.
        """
        state = self._save_state()
        self.infile = None
        self.outfile = None
        self.new_target = None
        return state
        
    def _save_state(self):
        """Return the current state, for later restoration."""
        return (self.target,self.root_dir,self.infile,self.outfile,self.new_target)

    def _restore_state(self,state):
        """Restore the object to a previously-saved state."""
        (self.target,self.root_dir,self.infile,self.outfile,self.new_target) = state

    def patch(self):
        """Interpret and apply patch commands to the target.

        This is a simple command loop that dispatches to the _do_<CMD>
        methods defined below.  It keeps processing until one of them
        raises EOFError.
        """
        header = self._read(len(PATCH_HEADER))
        if header != PATCH_HEADER:
            raise PatchError("not an esky patch file [%s]" % (header,))
        version = self._read_int()
        if version > HIGHEST_VERSION:
            raise PatchError("esky patch version %d not supported"%(version,))
        try:
            while True:
                cmd = self._read_command()
                getattr(self,"_do_" + _COMMANDS[cmd])()
        except EOFError:
            self._check_end_patch()
        finally:
            if self.infile:
                self.infile.close()
                self.infile = None
            if self.outfile:
                self.outfile.close()
                self.outfile = None

    def _do_END(self):
        """Execute the END command.

        If there are entries on the context stack, this pops and executes
        the topmost entry.  Otherwise, it exits the main command loop.
        """
        self._check_end_patch()
        if self._context_stack:
            self._context_stack.pop()()
        else:
            raise EOFError

    def _do_SET_PATH(self):
        """Execute the SET_PATH command.

        This reads a path from the command stream, and sets the current
        target path to that path.
        """
        self._check_end_patch()
        path = self._read_path()
        if path:
            self.target = os.path.join(self.root_dir,path)
        else:
            self.target = self.root_dir
        self._check_path()

    def _do_JOIN_PATH(self):
        """Execute the JOIN_PATH command.

        This reads a path from the command stream, and joins it to the
        current target path.
        """
        self._check_end_patch()
        path = self._read_path()
        self.target = os.path.join(self.target,path)
        self._check_path()

    def _do_POP_PATH(self):
        """Execute the POP_PATH command.

        This pops one name component from the current target path.  It
        is an error to attempt to pop past the root directory.
        """
        self._check_end_patch()
        while self.target.endswith(os.sep):
            self.target = self.target[:-1]
        self.target = os.path.dirname(self.target)
        self._check_path()

    def _do_POP_JOIN_PATH(self):
        """Execute the POP_JOIN_PATH command.

        This pops one name component from the current target path, then
        joins the path read from the command stream.
        """
        self._do_POP_PATH()
        self._do_JOIN_PATH()

    def _do_VERIFY_MD5(self):
        """Execute the VERIFY_MD5 command.

        This reads 16 bytes from the command stream, and compares them to
        the calculated digest for the current target path.  If they differ,
        a PatchError is raised.
        """
        self._check_end_patch()
        digest = self._read(16)
        assert len(digest) == 16
        if not self.dry_run:
            if digest != calculate_digest(self.target,hashlib.md5):
                raise PatchError("incorrect MD5 digest for %s" % (self.target,))

    def _do_MAKEDIR(self):
        """Execute the MAKEDIR command.

        This makes a directory at the current target path.  It automatically
        removes any existing entry at that path, as well as creating any
        intermediate directories.
        """
        self._check_end_patch()
        if not self.dry_run:
            if os.path.isdir(self.target):
                really_rmtree(self.target)
            elif os.path.exists(self.target):
                os.unlink(self.target)
            os.makedirs(self.target)

    def _do_REMOVE(self):
        """Execute the REMOVE command.

        This forcibly removes the file or directory at the current target path.
        """
        self._check_end_patch()
        if not self.dry_run:
            if os.path.isdir(self.target):
                really_rmtree(self.target)
            elif os.path.exists(self.target):
                os.unlink(self.target)

    def _do_COPY_FROM(self):
        """Execute the COPY_FROM command.

        This reads a path from the command stream, and copies whatever is
        at that path to the current target path.  The source path is
        interpreted relative to the directory containing the current path;
        this caters for the common case of copying a file within the same
        directory.
        """
        self._check_end_patch()
        source_path = os.path.join(os.path.dirname(self.target),self._read_path())
        self._check_path(source_path)
        if not self.dry_run:
            if os.path.exists(self.target):
                if os.path.isdir(self.target):
                    really_rmtree(self.target)
                else:
                    os.unlink(self.target)
            if os.path.isfile(source_path):
                shutil.copy2(source_path,self.target)
            else:
                shutil.copytree(source_path,self.target)

    def _do_MOVE_FROM(self):
        """Execute the MOVE_FROM command.

        This reads a path from the command stream, and moves whatever is
        at that path to the current target path.  The source path is
        interpreted relative to the directory containing the current path;
        this caters for the common case of moving a file within the same
        directory.
        """
        self._check_end_patch()
        source_path = os.path.join(os.path.dirname(self.target),self._read_path())
        self._check_path(source_path)
        if not self.dry_run:
            if os.path.exists(self.target):
                if os.path.isdir(self.target):
                    really_rmtree(self.target)
                else:
                    os.unlink(self.target)
                if sys.platform == "win32":
                    time.sleep(0.01)
            really_rename(source_path,self.target)

    def _do_PF_COPY(self):
        """Execute the PF_COPY command.

        This generates new data for the file currently being patched.  It
        reads an integer from the command stream, then copies that many bytes
        directory from the source file into the target file.
        """
        self._check_begin_patch()
        n = self._read_int()
        if not self.dry_run:
            self.outfile.write(self.infile.read(n))

    def _do_PF_SKIP(self):
        """Execute the PF_SKIP command.

        This reads an integer from the command stream, then moves the source
        file pointer by that amount without changing the target file.
        """
        self._check_begin_patch()
        n = self._read_int()
        if not self.dry_run:
            self.infile.read(n)

    def _do_PF_INS_RAW(self):
        """Execute the PF_INS_RAW command.

        This generates new data for the file currently being patched.  It
        reads a bytestring from the command stream and writes it directly
        into the target file.
        """
        self._check_begin_patch()
        data = self._read_bytes()
        if not self.dry_run:
            self.outfile.write(data)

    def _do_PF_INS_BZ2(self):
        """Execute the PF_INS_BZ2 command.

        This generates new data for the file currently being patched.  It
        reads a bytestring from the command stream, decompresses it using
        bz2 and and write the result into the target file.
        """
        self._check_begin_patch()
        data = bz2.decompress(self._read_bytes())
        if not self.dry_run:
            self.outfile.write(data)

    def _do_PF_BSDIFF4(self):
        """Execute the PF_BSDIFF4 command.

        This reads an integer N and a BSDIFF4-format patch bytestring from
        the command stream.  It then reads N bytes from the source file,
        applies the patch to these bytes, and writes the result into the
        target file.
        """
        self._check_begin_patch()
        n = self._read_int()
        # Restore the standard bsdiff header bytes
        patch = "BSDIFF40".encode("ascii") + self._read_bytes()
        if not self.dry_run:
            source = self.infile.read(n)
            if len(source) != n:
                raise PatchError("insufficient source data in %s" % (self.target,))
            self.outfile.write(bsdiff4.patch(source,patch))

    def _do_PF_REC_ZIP(self):
        """Execute the PF_REC_ZIP command.

        This patches the current target by treating it as a zipfile and
        recursing into it.  It extracts the source file to a temp directory,
        then reads commands and applies them to that directory.

        This command expects two END-terminated blocks of sub-commands.  The
        first block patches the zipfile metadata, and the second patches the
        actual contents of the zipfile.
        """
        self._check_begin_patch()
        if not self.dry_run:
            workdir = os.path.join(self._workdir,str(len(self._context_stack)))
            os.mkdir(workdir)
            t_temp = os.path.join(workdir,"contents")
            m_temp = os.path.join(workdir,"meta")
            z_temp = os.path.join(workdir,"result.zip")
        cur_state = self._blank_state()
        zfmeta = [None]  # stupid lack of mutable closure variables...
        #  First we process a set of commands to generate the zipfile metadata.
        def end_metadata():
            if not self.dry_run:
                zfmeta[0] = _read_zipfile_metadata(m_temp)
                self.target = t_temp
        #  Then we process a set of commands to patch the actual contents.
        def end_contents():
            self._restore_state(cur_state)
            if not self.dry_run:
                create_zipfile(t_temp,z_temp,members=zfmeta[0].infolist())
                with open(z_temp,"rb") as f:
                    data = f.read(1024*16)
                    while data:
                        self.outfile.write(data)
                        data = f.read(1024*16)
                zfmeta[0].close()
                really_rmtree(workdir)
        self._context_stack.append(end_contents)
        self._context_stack.append(end_metadata)
        if not self.dry_run:
            #  Begin by writing the current zipfile metadata to a temp file.
            #  This will be patched, then end_metadata() will be called.
            with open(m_temp,"wb") as f:
                zf = zipfile.ZipFile(self.target)
                try:
                    _write_zipfile_metadata(f,zf)
                finally:
                    zf.close()
            extract_zipfile(self.target,t_temp)
            self.root_dir = workdir
            self.target = m_temp

    def _do_CHMOD(self):
        """Execute the CHMOD command.

        This reads an integer from the command stream, and sets the mode
        of the current target to that integer.
        """
        self._check_end_patch()
        mod = self._read_int()
        if not self.dry_run:
            os.chmod(self.target,mod)


class Differ(object):
    """Class generating our patch protocol.

    Instances of this class can be used to generate a sequence of patch
    commands to transform one file/directory into another.
    """

    def __init__(self,outfile,diff_window_size=None):
        if not diff_window_size:
            diff_window_size = DIFF_WINDOW_SIZE
        self.diff_window_size = diff_window_size
        self.outfile = outfile
        self._pending_pop_path = 0

    def _write(self,data):
        self.outfile.write(data)

    def _write_int(self,i):
        _write_vint(self.outfile,i)

    def _write_command(self,cmd):
        """Write the given command to the stream.

        This does some simple optimisations to collapse sequences of commands
        into a single command - current only around path manipulation.
        """
        # Gather up POP_PATH instructions, we may be able to eliminate them.
        if cmd == POP_PATH:
            self._pending_pop_path += 1
        # If POP_PATH is followed by something else, try to eliminate.
        elif self._pending_pop_path:
            # POP_PATH,JOIN_PATH => POP_JOIN_PATH
            if cmd == JOIN_PATH:
                for _ in xrange(self._pending_pop_path - 1):
                    _write_vint(self.outfile,POP_PATH)
                _write_vint(self.outfile,POP_JOIN_PATH)
            # POP_PATH,SET_PATH => SET_PATH
            elif cmd == SET_PATH:
                _write_vint(self.outfile,SET_PATH)
            # Otherwise, write out all the POP_PATH instructions.
            else:
                for _ in xrange(self._pending_pop_path):
                    _write_vint(self.outfile,POP_PATH)
                _write_vint(self.outfile,cmd)
            self._pending_pop_path = 0
        else:
            _write_vint(self.outfile,cmd)

    def _write_bytes(self,bytes):
        _write_vint(self.outfile,len(bytes))
        self._write(bytes)

    def _write_path(self,path):
        self._write_bytes(path.encode("utf8"))

    def diff(self,source,target):
        """Generate patch commands to transform source into target.

        'source' and 'target' must be paths to a file or directory.  Patch
        protocol commands to transform 'source' into 'target' will be generated
        and written sequentially to the output file.
        """
        source = os.path.abspath(source)
        target = os.path.abspath(target)
        self._write(PATCH_HEADER)
        self._write_int(HIGHEST_VERSION)
        self._diff(source,target)
        self._write_command(SET_PATH)
        self._write_bytes("".encode("ascii"))
        self._write_command(VERIFY_MD5)
        self._write(calculate_digest(target,hashlib.md5))

    def _diff(self,source,target):
        """Recursively generate patch commands to transform source into target.

        This is the workhorse for the diff() method - it recursively
        generates the patch commands for a given (source,target) pair.  The
        main diff() method adds some header and footer commands.
        """
        if os.path.isdir(target):
            self._diff_dir(source,target)
        elif os.path.isfile(target):
            self._diff_file(source,target)
        else:
            #  We can't deal with any other objects for the moment.
            #  Could eventually add support for e.g. symlinks.
            raise DiffError("unknown filesystem object: " + target)

    def _diff_dir(self,source,target):
        """Generate patch commands for when the target is a directory."""
        #  If it's not already a directoy, make it one.
        if not os.path.isdir(source):
            self._write_command(MAKEDIR)
        #  For each new item try to find a sibling to copy/move from.
        #  This might generate a few spurious COPY_FROM and REMOVE commands,
        #  but in return we get a better chance of diffing against something.
        nm_sibnm_map = {}
        sibnm_nm_map = {}
        for nm in os.listdir(target):
            s_nm = os.path.join(source,nm)
            if not os.path.exists(s_nm):
                sibnm = self._find_similar_sibling(source,target,nm)
                if sibnm is not None:
                    nm_sibnm_map[nm] = sibnm
                    try:
                        sibnm_nm_map[sibnm].append(nm)
                    except KeyError:
                        sibnm_nm_map[sibnm] = [nm]
        #  Now generate COPY or MOVE commands for all those new items.
        #  Doing them all in a batch means we gracefully cope with
        #  several tagrgets coming from the same source.
        for nm, sibnm in nm_sibnm_map.iteritems():
            s_nm = os.path.join(source,sibnm)
            self._write_command(JOIN_PATH)
            self._write_path(nm)
            if os.path.exists(os.path.join(target,sibnm)):
                self._write_command(COPY_FROM)
            elif len(sibnm_nm_map[sibnm]) > 1:
                self._write_command(COPY_FROM)
            else:
                self._write_command(MOVE_FROM)
            self._write_path(sibnm)
            sibnm_nm_map[sibnm].remove(nm)
            self._write_command(POP_PATH)
        # Every target item now has a source. Diff against it.
        for nm in os.listdir(target):
            try:
                s_nm = os.path.join(source,nm_sibnm_map[nm])
            except KeyError:
                s_nm = os.path.join(source,nm)
            t_nm = os.path.join(target,nm)
            #  Recursively diff against the selected source.
            if paths_differ(s_nm,t_nm):
                self._write_command(JOIN_PATH)
                self._write_path(nm)
                self._diff(s_nm,t_nm)
                self._write_command(POP_PATH)
            #  Clean up .pyc files, as they can be generated automatically
            #  and cause digest verification to fail.
            if nm.endswith(".py"):
                if not os.path.exists(t_nm+"c"):
                    self._write_command(JOIN_PATH)
                    self._write_path(nm+"c")
                    self._write_command(REMOVE)
                    self._write_command(POP_PATH)
                if not os.path.exists(t_nm+"o"):
                    self._write_command(JOIN_PATH)
                    self._write_path(nm+"o")
                    self._write_command(REMOVE)
                    self._write_command(POP_PATH)
        #  Remove anything that's no longer in the target dir
        if os.path.isdir(source):
            for nm in os.listdir(source):
                if not os.path.exists(os.path.join(target,nm)):
                    if nm not in sibnm_nm_map:
                        self._write_command(JOIN_PATH)
                        self._write_path(nm)
                        self._write_command(REMOVE)
                        self._write_command(POP_PATH)
        #  Adjust mode if necessary
        t_mod = os.stat(target).st_mode
        if os.path.isdir(source):
            s_mod = os.stat(source).st_mode
            if s_mod != t_mod:
                self._write_command(CHMOD)
                self._write_int(t_mod)
        else:
            self._write_command(CHMOD)
            self._write_int(t_mod)

    def _diff_file(self,source,target):
        """Generate patch commands for when the target is a file."""
        if paths_differ(source,target):
            if not os.path.isfile(source):
                self._diff_binary_file(source,target)
            elif target.endswith(".zip") and source.endswith(".zip"):
                self._diff_dotzip_file(source,target)
            else:
                self._diff_binary_file(source,target)
        #  Adjust mode if necessary
        t_mod = os.stat(target).st_mode
        if os.path.isfile(source):
            s_mod = os.stat(source).st_mode
            if s_mod != t_mod:
                self._write_command(CHMOD)
                self._write_int(t_mod)
        else:
            self._write_command(CHMOD)
            self._write_int(t_mod)

    def _open_and_check_zipfile(self,path):
        """Open the given path as a zipfile, and check its suitability.

        Returns either the ZipFile object, or None if we can't diff it
        as a zipfile.
        """
        try:
            zf = zipfile.ZipFile(path,"r")
        except (zipfile.BadZipfile,zipfile.LargeZipFile):
            return None
        else:
            # Diffing empty zipfiles is kinda pointless
            if not zf.filelist:
                zf.close()
                return None
            # Can't currently handle zipfiles with comments
            if zf.comment:
                zf.close()
                return None
            # Can't currently handle zipfiles with prepended data
            if zf.filelist[0].header_offset != 0:
                zf.close()
                return None
            # Hooray! Looks like something we can use.
            return zf
      
    def _diff_dotzip_file(self,source,target):
        s_zf = self._open_and_check_zipfile(source)
        if s_zf is None:
            self._diff_binary_file(source,target)
        else:
            t_zf = self._open_and_check_zipfile(target)
            if t_zf is None:
                s_zf.close()
                self._diff_binary_file(source,target)
            else:
                try:
                    self._write_command(PF_REC_ZIP)
                    with _tempdir() as workdir:
                        #  Write commands to transform source metadata file
                        #  into target metadata file.
                        s_meta = os.path.join(workdir,"s_meta")
                        with open(s_meta,"wb") as f:
                            _write_zipfile_metadata(f,s_zf)
                        t_meta = os.path.join(workdir,"t_meta")
                        with open(t_meta,"wb") as f:
                            _write_zipfile_metadata(f,t_zf)
                        self._diff_binary_file(s_meta,t_meta)
                        self._write_command(END)
                        #  Write commands to transform source contents
                        #  directory into target contents directory.
                        s_workdir = os.path.join(workdir,"source")
                        t_workdir = os.path.join(workdir,"target")
                        extract_zipfile(source,s_workdir)
                        extract_zipfile(target,t_workdir)
                        self._diff(s_workdir,t_workdir)
                        self._write_command(END)
                finally:
                    t_zf.close() 
                    s_zf.close() 


    def _diff_binary_file(self,source,target):
        """Diff a generic binary file.

        This is the per-file diffing method used when we don't know enough
        about the file to do anything fancier.  It's basically a windowed
        bsdiff.
        """
        spos = 0
        with open(target,"rb") as tfile:
            if os.path.isfile(source):
                sfile = open(source,"rb")
            else:
                sfile = None
            try:
                #  Process the file in diff_window_size blocks.  This
                #  will produce slightly bigger patches but we avoid
                #  running out of memory for large files.
                tdata = tfile.read(self.diff_window_size)
                if not tdata:
                    #  The file is empty, do a raw insert of zero bytes.
                    self._write_command(PF_INS_RAW)
                    self._write_bytes("".encode("ascii"))
                else:
                    while tdata:
                        sdata = b""
                        if sfile is not None:
                            sdata = sfile.read(self.diff_window_size)
                        #  Look for a shared prefix.
                        i = 0; maxi = min(len(tdata),len(sdata))
                        while i < maxi and tdata[i] == sdata[i]:
                            i += 1
                        #  Copy it in directly, unless it's tiny.
                        if i > 8:
                            skipbytes = sfile.tell() - len(sdata) - spos
                            if skipbytes > 0:
                                self._write_command(PF_SKIP)
                                self._write_int(skipbytes)
                                spos += skipbytes
                            self._write_command(PF_COPY)
                            self._write_int(i)
                            tdata = tdata[i:]; sdata = sdata[i:]
                            spos += i
                        #  Write the rest of the block as a diff
                        if tdata:
                            spos += self._write_file_patch(sdata,tdata)
                        tdata = tfile.read(self.diff_window_size)
            finally:
                if sfile is not None:
                    sfile.close()

    def _find_similar_sibling(self,source,target,nm):
        """Find a sibling of an entry against which we can calculate a diff.

        Given two directories 'source' and 'target' and an entry from the target
        directory 'nm', this function finds an entry from the source directory
        that we can diff against to produce 'nm'.

        The idea here is to detect files or directories that have been moved,
        and avoid generating huge patches by diffing against the original.
        We use some pretty simple heuristics but it can make a big difference.
        """
        t_nm = os.path.join(target,nm)
        if os.path.isfile(t_nm):
             # For files, I haven't decided on a good heuristic yet...
            return None
        elif os.path.isdir(t_nm):
            #  For directories, decide similarity based on the number of
            #  entry names they have in common.  This is very simple but should
            #  work well for the use cases we're facing in esky.
            if not os.path.isdir(source):
                return None
            t_names = set(os.listdir(t_nm))
            best = (2,None)
            for sibnm in os.listdir(source):
                if not os.path.isdir(os.path.join(source,sibnm)):
                    continue
                if os.path.exists(os.path.join(target,sibnm)):
                    continue
                sib_names = set(os.listdir(os.path.join(source,sibnm)))
                cur = (len(sib_names & t_names),sibnm)
                if cur > best:
                    best = cur
            return best[1]
        else:
            return None

    def _write_file_patch(self,sdata,tdata):
        """Write a series of PF_* commands to generate tdata from sdata.

        This function tries the various PF_* commands to find the one which can
        generate tdata from sdata with the smallest command size.  Usually that
        will be BSDIFF4, but you never know :-)
        """
        options = []
        #  We could just include the raw data
        options.append((0,PF_INS_RAW,tdata))
        #  We could bzip2 the raw data
        options.append((0,PF_INS_BZ2,bz2.compress(tdata)))
        #  We could bsdiff4 the data, if we have an appropriate module
        if bsdiff4.diff is not None:
            patch_data = bsdiff4.diff(sdata,tdata)
            # remove the 8 header bytes, we know it's BSDIFF4 format
            options.append((len(sdata),PF_BSDIFF4,len(sdata),patch_data[8:]))
        #  Find the option with the smallest data and use that.
        options = [(len(cmd[-1]),cmd) for cmd in options]
        options.sort()
        best_option = options[0][1]
        self._write_command(best_option[1])
        for arg in best_option[2:]:
            if isinstance(arg,(str,unicode,bytes)):
                self._write_bytes(arg)
            else:
                self._write_int(arg)
        return best_option[0]


class _tempdir(object):
    def __init__(self):
        self.path = tempfile.mkdtemp()
    def __enter__(self):
        return self.path
    def __exit__(self,*args):
        really_rmtree(self.path)





def _decode_offt(bytes):
    """Decode an off_t value from a string.

    This decodes a signed integer into 8 bytes.  I'd prefer some sort of
    signed vint representation, but this is the format used by bsdiff4.
    """
    if sys.version_info[0] < 3:
        bytes = map(ord,bytes)
    x = bytes[7] & 0x7F
    for b in xrange(6,-1,-1):
        x = x * 256 + bytes[b]
    if bytes[7] & 0x80:
        x = -x
    return x

def _encode_offt(x):
    """Encode an off_t value as a string.

    This encodes a signed integer into 8 bytes.  I'd prefer some sort of
    signed vint representation, but this is the format used by bsdiff4.
    """
    if x < 0:
        x = -x
        sign = 0x80
    else:
        sign = 0
    bs = [0]*8
    bs[0] = x % 256
    for b in xrange(7):
        x = (x - bs[b]) / 256
        bs[b+1] = x % 256
    bs[7] |= sign
    if sys.version_info[0] < 3:
        return "".join(map(chr,bs))
    else:
        return bytes(bs)



def main(args):
    """Command-line diffing and patching for esky."""
    parser = optparse.OptionParser()
    parser.add_option("-z","--zipped",action="store_true",dest="zipped",
                      help="work with zipped source/target dirs")
    parser.add_option("-Z","--deep-zipped",action="store_true",
                      dest="deep_zipped",
                      help="work with deep zipped source/target dirs")
    parser.add_option("","--diff-window",dest="diff_window",metavar="N",
                      help="set the window size for diffing files")
    parser.add_option("","--dry-run",dest="dry_run",action="store_true",
                      help="print commands instead of executing them")
    (opts,args) = parser.parse_args(args)
    if opts.deep_zipped:
        opts.zipped = True
    if opts.zipped:
        workdir = tempfile.mkdtemp()
    if opts.diff_window:
        scale = 1
        if opts.diff_window[-1].lower() == "k":
            scale = 1024
            opts.diff_window = opts.diff_window[:-1]
        elif opts.diff_window[-1].lower() == "m":
            scale = 1024 * 1024
            opts.diff_window = opts.diff_window[:-1]
        elif opts.diff_window[-1].lower() == "g":
            scale = 1024 * 1024 * 1024
            opts.diff_window = opts.diff_window[:-1]
        opts.diff_window = int(float(opts.diff_window)*scale)
    stream = None
    try:
        cmd = args[0]
        if cmd == "diff":
            #  Generate a diff between two files/directories.
            #  If --zipped is specified, the source and/or target is unzipped
            #  to a temporary directory before processing.
            source = args[1]
            target = args[2]
            if len(args) > 3:
                stream = open(args[3],"wb")
            else:
                stream = sys.stdout
            if opts.zipped:
                if os.path.isfile(source):
                    source_zip = source
                    source = os.path.join(workdir,"source")
                    if opts.deep_zipped:
                        deep_extract_zipfile(source_zip,source)
                    else:
                        extract_zipfile(source_zip,source)
                if os.path.isfile(target):
                    target_zip = target
                    target = os.path.join(workdir,"target")
                    if opts.deep_zipped:
                        deep_extract_zipfile(target_zip,target)
                    else:
                        extract_zipfile(target_zip,target)
            write_patch(source,target,stream,diff_window_size=opts.diff_window)
        elif cmd == "patch":
            #  Patch a file or directory.
            #  If --zipped is specified, the target is unzipped to a temporary
            #  directory before processing, then overwritten with a zipfile
            #  containing the new directory contents.
            target = args[1]
            if len(args) > 2:
                stream = open(args[2],"rb")
            else:
                stream = sys.stdin
            target_zip = None
            if opts.zipped:
                if os.path.isfile(target):
                    target_zip = target
                    target = os.path.join(workdir,"target")
                    if opts.deep_zipped:
                        deep_extract_zipfile(target_zip,target)
                    else:
                        extract_zipfile(target_zip,target)
            apply_patch(target,stream,dry_run=opts.dry_run)
            if opts.zipped and target_zip is not None:
                target_dir = os.path.dirname(target_zip)
                (fd,target_temp) = tempfile.mkstemp(dir=target_dir)
                os.close(fd)
                if opts.deep_zipped:
                    prefix = zipfile_common_prefix_dir(target_zip)
                    def name_filter(nm):
                        return prefix + nm
                    create_zipfile(target,target_temp,name_filter)
                else:
                    create_zipfile(target,target_temp)
                if sys.platform == "win32":
                    os.unlink(target_zip)
                    time.sleep(0.01)
                really_rename(target_temp,target_zip)
        else:
            raise ValueError("invalid command: " + cmd)
    finally:
        if stream is not None:
            if stream not in (sys.stdin,sys.stdout,):
                stream.close()
        if opts.zipped:
            really_rmtree(workdir)
 

if __name__ == "__main__":
    main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = slaveproc
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.slaveproc:  utilities for running a slave process.

A "slave process" is one that automatically dies when its master process dies.
To implement this, the slave process spins up a background thread that watches
the parent and calls os._exit(1) if it dies.

On unix, the master process takes an exclusive flock on a temporary file, which
will disappear when the master dies.  The slave process can do a blocking 
acquire on this lock to wait for the master to die.

On windows, the master process creates a file with O_TEMPORARY, which will
disappear when the master dies.  The slave process can use ReadDirectoryChanges
to watch for the disappearance of this file.

"""

from __future__ import absolute_import

import sys

from esky.util import lazy_import


@lazy_import
def os():
    import os
    return os

@lazy_import
def tempfile():
    import tempfile
    return tempfile

@lazy_import
def threading():
    try:
        import threading
    except ImportError:
        threading = None
    return threading

@lazy_import
def ctypes():
    import ctypes
    import ctypes.wintypes
    return ctypes


def monitor_master_process(fpath):
    """Watch the given path to detect the master process dying.

    If the master process dies, the current process is terminated.
    """
    if not threading:
        return None
    def monitor():
        if wait_for_master(fpath):
            os._exit(1)
    t = threading.Thread(target=monitor)
    t.daemon = True
    t.start()
    return t


def get_slave_process_args():
    """Get the arguments that should be passed to a new slave process."""


def run_startup_hooks():
    if len(sys.argv) > 1 and sys.argv[1] == "--esky-slave-proc":
        del sys.argv[1]
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            del sys.argv[1]
        else:
            arg = None
        monitor_master_process(arg)


if sys.platform == "win32":

    #  On win32, the master process creates a tempfile that will be deleted
    #  when it exits.  Use ReadDirectoryChanges to block on this event.

    def wait_for_master(fpath):
        """Wait for the master process to die."""
        try:
            RDCW = ctypes.windll.kernel32.ReadDirectoryChangesW
        except AttributeError:
            return False

        INVALID_HANDLE_VALUE = 0xFFFFFFFF
        FILE_NOTIFY_CHANGE_FILE_NAME = 0x01

        FILE_LIST_DIRECTORY = 0x01
        FILE_SHARE_READ = 0x01
        FILE_SHARE_WRITE = 0x02
        OPEN_EXISTING = 3
        FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

        try:
            ctypes.wintypes.LPVOID
        except AttributeError:
            ctypes.wintypes.LPVOID = ctypes.c_void_p

        def _errcheck_bool(value,func,args):
            if not value:
                 raise ctypes.WinError()
            return args

        def _errcheck_handle(value,func,args):
            if not value:
                raise ctypes.WinError()
            if value == INVALID_HANDLE_VALUE:
                raise ctypes.WinError()
            return args

        RDCW.errcheck = _errcheck_bool
        RDCW.restype = ctypes.wintypes.BOOL
        RDCW.argtypes = (
            ctypes.wintypes.HANDLE, # hDirectory
            ctypes.wintypes.LPVOID, # lpBuffer
            ctypes.wintypes.DWORD, # nBufferLength
            ctypes.wintypes.BOOL, # bWatchSubtree
            ctypes.wintypes.DWORD, # dwNotifyFilter
            ctypes.POINTER(ctypes.wintypes.DWORD), # lpBytesReturned
            ctypes.wintypes.LPVOID, # lpOverlapped
            ctypes.wintypes.LPVOID  # lpCompletionRoutine
        )

        CreateFileW = ctypes.windll.kernel32.CreateFileW
        CreateFileW.errcheck = _errcheck_handle
        CreateFileW.restype = ctypes.wintypes.HANDLE
        CreateFileW.argtypes = (
            ctypes.wintypes.LPCWSTR, # lpFileName
            ctypes.wintypes.DWORD, # dwDesiredAccess
            ctypes.wintypes.DWORD, # dwShareMode
            ctypes.wintypes.LPVOID, # lpSecurityAttributes
            ctypes.wintypes.DWORD, # dwCreationDisposition
            ctypes.wintypes.DWORD, # dwFlagsAndAttributes
            ctypes.wintypes.HANDLE # hTemplateFile
        )

        CloseHandle = ctypes.windll.kernel32.CloseHandle
        CloseHandle.restype = ctypes.wintypes.BOOL
        CloseHandle.argtypes = (
            ctypes.wintypes.HANDLE, # hObject
        )

        result = ctypes.create_string_buffer(1024)
        nbytes = ctypes.c_ulong()
        handle = CreateFileW(os.path.join(os.path.dirname(fpath),u""),
                             FILE_LIST_DIRECTORY,
                             FILE_SHARE_READ | FILE_SHARE_WRITE,
                             None,
                             OPEN_EXISTING,
                             FILE_FLAG_BACKUP_SEMANTICS,
                             0
                 )

        #  Since this loop may still be running at interpreter close, we
        #  take local references to our imported functions to avoid
        #  garbage-collection-related errors at shutdown.
        byref = ctypes.byref
        pathexists = os.path.exists

        try:
            while pathexists(fpath):
                RDCW(handle,byref(result),len(result),
                     True,FILE_NOTIFY_CHANGE_FILE_NAME,
                     byref(nbytes),None,None)
        finally:
            CloseHandle(handle)
        return True

    def get_slave_process_args():
        """Get the arguments that should be passed to a new slave process."""
        try:
            flags = os.O_CREAT|os.O_EXCL|os.O_TEMPORARY|os.O_NOINHERIT
            tfile = tempfile.mktemp()
            fd = os.open(tfile,flags)
        except EnvironmentError:
            return []
        else:
            return ["--esky-slave-proc",tfile]
             

else:

    #  On unix, the master process takes an exclusive flock on the given file.
    #  We try to take one as well, which will block until the master dies.

    import fcntl

    def wait_for_master(fpath):
        """Wait for the master process to die."""
        try:
            fd = os.open(fpath,os.O_RDWR)
            fcntl.flock(fd,fcntl.LOCK_EX)
            return True
        except EnvironmentError:
            return False

    def get_slave_process_args():
        """Get the arguments that should be passed to a new slave process."""
        try:
            (fd,tfile) = tempfile.mkstemp()
            fcntl.flock(fd,fcntl.LOCK_EX)
        except EnvironmentError:
            return []
        else:
            return ["--esky-slave-proc",tfile]



########NEW FILE########
__FILENAME__ = sudo_base
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.sudo.sudo_base:  base functionality for esky sudo helpers

"""

import os
import sys
import errno
import base64
import struct
import signal
import subprocess
import tempfile
import hmac
from functools import wraps

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import threading
except ImportError:
    threading = None


def b64pickle(obj):
    """Serialize object to a base64-string."""
    return base64.b64encode(pickle.dumps(obj, -1)).decode("ascii")


def b64unpickle(data):
    """Deserialize object from a base64-string."""
    if sys.version_info[0] > 2:
        data = data.encode("ascii")
    return pickle.loads(base64.b64decode(data))


def has_root():
    """Check whether the user currently has root access."""
    return False


def can_get_root():
    """Check whether the user may be able to get root access.

    This is currently always True on unix-like platforms, since we have no
    way of peering inside the sudoers file.
    """
    return True


class SecureStringPipe(object):
    """Two-way pipe for securely communicating strings with a sudo subprocess.

    This is the control pipe used for passing command data from the non-sudo
    master process to the sudo slave process.  Use read() to read the next
    string, write() to write the next string.

    As a security measure, all strings are "signed" using a rolling hmac based
    off a shared security token.  A bad signature results in the pipe being
    immediately closed and a RuntimeError being generated.
    """

    def __init__(self,token=None):
        if token is None:
            token = os.urandom(16)
        self.token = token
        self.connected = False

    def __del__(self):
        self.close()

    def connect(self):
        raise NotImplementedError

    def _read(self,size):
        raise NotImplementedError

    def _write(self,data):
        raise NotImplementedError

    def _open(self):
        raise NotImplementedError

    def _recover(self):
        pass

    def check_connection(self):
        if not self.connected:
            self._read_hmac = hmac.new(self.token)
            self._write_hmac = hmac.new(self.token)
            #timed_out = []
            #t = None
            #if threading is not None:
            #    def rescueme():
            #        timed_out.append(True)
            #        self._recover()
            #    t = threading.Timer(30,rescueme)
            #    t.start()
            self._open()
            #if timed_out:
            #    raise IOError(errno.ETIMEDOUT,"timed out during sudo")
            #elif t is not None:
            #    t.cancel()
            self.connected = True

    def close(self):
        self.connected = False

    def read(self):
        """Read the next string from the pipe.

        The expected data format is:  4-byte size, data, signature
        """
        self.check_connection()
        sz = self._read(4)
        if len(sz) < 4:
            raise EOFError
        sz = struct.unpack("I",sz)[0]
        data = self._read(sz)
        if len(data) < sz:
            raise EOFError
        sig = self._read(self._read_hmac.digest_size)
        self._read_hmac.update(data)
        if sig != self._read_hmac.digest():
            self.close()
            raise RuntimeError("mismatched hmac; terminating")
        return data

    def write(self,data):
        """Write the given string to the pipe.

        The expected data format is:  4-byte size, data, signature
        """
        self.check_connection()
        self._write(struct.pack("I",len(data)))
        self._write(data)
        self._write_hmac.update(data)
        self._write(self._write_hmac.digest())


def spawn_sudo(proxy):
    """Spawn the sudo slave process, returning proc and a pipe to message it."""
    raise NotImplementedError


def run_startup_hooks():
    raise NotImplementedError



########NEW FILE########
__FILENAME__ = sudo_osx
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.sudo.sudo_osx:  OSX platform-specific functionality for esky.sudo


This implementation of esky.sudo uses the native OSX Authorization framework
to spawn a helper with root privileges.

"""

import sys
if sys.platform != "darwin":
    raise ImportError("only usable on OSX")

import os
import errno
import struct
import signal
import subprocess
from base64 import b64encode, b64decode
from functools import wraps

from esky.sudo import sudo_base as base
import esky.slaveproc

pickle = base.pickle
HIGHEST_PROTOCOL = pickle.HIGHEST_PROTOCOL

import ctypes
import ctypes.util
from ctypes import byref

libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
sec = ctypes.cdll.LoadLibrary(ctypes.util.find_library("Security"))
try:
    sec.AuthorizationCreate
except AttributeError:
    raise ImportError("Security library not usable")

kAuthorizationFlagDefaults = 0
kAuthorizationFlagInteractionAllowed = (1 << 0)
kAuthorizationFlagExtendRights = (1 << 1)
kAuthorizationFlagPartialRights = (1 << 2)
kAuthorizationFlagDestroyRights = (1 << 3)
kAuthorizationFlagPreAuthorize = (1 << 4)
kAuthorizationFlagNoData = (1 << 20)

class AuthorizationRight(ctypes.Structure):
    _fields_ = [("name",ctypes.c_char_p),
                ("valueLength",ctypes.c_uint32),
                ("value",ctypes.c_void_p),
                ("flags",ctypes.c_uint32),
               ]

class AuthorizationRights(ctypes.Structure):
    _fields_ = [("count",ctypes.c_uint32),
                ("items",AuthorizationRight * 1)
               ]


def has_root():
    """Check whether the use current has root access."""
    return (os.geteuid() == 0)


def can_get_root():
    """Check whether the usee may be able to get root access.

    This is currently always True on unix-like platforms, since we have no
    way of peering inside the sudoers file.
    """
    return True


class FakePopen(subprocess.Popen):
    """Popen-esque class that's guaranteed killable, even on python2.5."""
    def __init__(self,pid):
        super(FakePopen,self).__init__(None)
        self.pid = pid
    def terminate(self):
        import signal
        os.kill(self.pid,signal.SIGTERM)
    def _execute_child(self,*args,**kwds):
        pass


class SecureStringPipe(base.SecureStringPipe):
    """A two-way pipe for securely communicating with a sudo subprocess.

    On OSX this is implemented by a FILE* object on the master end, and by
    stdin/stdout on the slave end.  Which is convenient, because that's just
    the thing that AuthorizationExecuteWithPrivileges gives us...
    """

    def __init__(self,token=None):
        super(SecureStringPipe,self).__init__(token)
        self.fp = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def connect(self):
        return SecureStringPipe(self.token)

    def _read(self,size):
        if self.fp is None:
            return os.read(0,size)
        else:
            buf = ctypes.create_string_buffer(size+2)
            read = libc.fread(byref(buf),1,size,self.fp)
            return buf.raw[:read]

    def _write(self,data):
        if self.fp is None:
            os.write(1,data)
        else:
            libc.fwrite(data,1,len(data),self.fp)

    def _open(self):
        pass

    def _recover(self):
        pass

    def close(self):
        if self.fp is not None:
            libc.fclose(self.fp)
            self.fp = None
        super(SecureStringPipe,self).close()


def spawn_sudo(proxy):
    """Spawn the sudo slave process, returning proc and a pipe to message it."""

    pipe = SecureStringPipe()
    c_pipe = pipe.connect()

    if not getattr(sys,"frozen",False):
        exe = [sys.executable,"-c","import esky; esky.run_startup_hooks()"]
    elif os.path.basename(sys.executable).lower() in ("python","pythonw"):
        exe = [sys.executable,"-c","import esky; esky.run_startup_hooks()"]
    else:
        if not esky._startup_hooks_were_run:
            raise OSError(None,"unable to sudo: startup hooks not run")
        exe = [sys.executable]
    args = ["--esky-spawn-sudo"]
    args.append(base.b64pickle(proxy))
    args.append(base.b64pickle(c_pipe))

    # Make it a slave process so it dies if we die
    exe = exe + esky.slaveproc.get_slave_process_args() + args

    auth = ctypes.c_void_p()

    right = AuthorizationRight()
    right.name = "py.esky.sudo." + proxy.name
    right.valueLength = 0
    right.value = None
    right.flags = 0

    rights = AuthorizationRights()
    rights.count = 1
    rights.items[0] = right

    r_auth = byref(auth)
    err = sec.AuthorizationCreate(None,None,kAuthorizationFlagDefaults,r_auth)
    if err:
        raise OSError(errno.EACCES,"could not sudo: %d" % (err,))

    try:

        kAuthFlags = kAuthorizationFlagDefaults \
                     | kAuthorizationFlagPreAuthorize \
                     | kAuthorizationFlagInteractionAllowed \
                     | kAuthorizationFlagExtendRights
        
        err = sec.AuthorizationCopyRights(auth,None,None,kAuthFlags,None)
        if err:
            raise OSError(errno.EACCES,"could not sudo: %d" % (err,))

        args = (ctypes.c_char_p * len(exe))()
        for i,arg in enumerate(exe[1:]):
            args[i] = arg
        args[len(exe)-1] = None
        io = ctypes.c_void_p()
        err = sec.AuthorizationExecuteWithPrivileges(auth,exe[0],0,args,byref(io))
        if err:
            raise OSError(errno.EACCES,"could not sudo: %d" %(err,))
        
        buf = ctypes.create_string_buffer(8)
        read = libc.fread(byref(buf),1,4,io)
        if read != 4:
            libc.fclose(io)
            raise OSError(errno.EACCES,"could not sudo: child failed")
        pid = struct.unpack("I",buf.raw[:4])[0]
        pipe.fp = io
        return (FakePopen(pid),pipe)
    finally:
        sec.AuthorizationFree(auth,kAuthorizationFlagDestroyRights)


def run_startup_hooks():
    if len(sys.argv) > 1 and sys.argv[1] == "--esky-spawn-sudo":
        if sys.version_info[0] > 2:
            proxy = b64unpickle(sys.argv[2])
            pipe = b64unpickle(sys.argv[3])
        else:
            proxy = pickle.loads(b64decode(sys.argv[2]))
            pipe = pickle.loads(b64decode(sys.argv[3]))
        os.write(1,struct.pack("I",os.getpid()))
        proxy.run(pipe)
        sys.exit(0)


########NEW FILE########
__FILENAME__ = sudo_unix
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.sudo.sudo_unix:  unix platform-specific functionality for esky.sudo

"""

import os
import sys
import errno
import struct
import signal
import subprocess
import tempfile
from functools import wraps

from esky.sudo import sudo_base as base
import esky.slaveproc


def has_root():
    """Check whether the use current has root access."""
    return (os.geteuid() == 0)


def can_get_root():
    """Check whether the usee may be able to get root access.

    This is currently always True on unix-like platforms, since we have no
    sensible way of peering inside the sudoers file.
    """
    return True


class KillablePopen(subprocess.Popen):
    """Popen that's guaranteed killable, even on python2.5."""
    if not hasattr(subprocess.Popen,"terminate"):
        def terminate(self):
            import signal
            os.kill(self.pid,signal.SIGTERM)


class SecureStringPipe(base.SecureStringPipe):
    """A two-way pipe for securely communicating with a sudo subprocess.

    On unix this is implemented as a pair of fifos.  It would be more secure
    to use anonymous pipes, but they're not reliably inherited through sudo
    wrappers such as gksudo.

    Unfortunately this leaves the pipes wide open to hijacking by other
    processes running as the same user.  Security depends on secrecy of the
    message-hashing token, which we pass to the slave in its env vars.
    """

    def __init__(self,token=None,data=None):
        super(SecureStringPipe,self).__init__(token)
        self.rfd = None
        self.wfd = None
        if data is None:
            self.tdir = tempfile.mkdtemp()
            self.rnm = os.path.join(self.tdir,"master")
            self.wnm = os.path.join(self.tdir,"slave")
            os.mkfifo(self.rnm,0600)
            os.mkfifo(self.wnm,0600)
        else:
            self.tdir,self.rnm,self.wnm = data

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def connect(self):
        return SecureStringPipe(self.token,(self.tdir,self.wnm,self.rnm))

    def _read(self,size):
        return os.read(self.rfd,size)

    def _write(self,data):
        return os.write(self.wfd,data)

    def _open(self):
        if self.rnm.endswith("master"):
            self.rfd = os.open(self.rnm,os.O_RDONLY)
            self.wfd = os.open(self.wnm,os.O_WRONLY)
        else:
            self.wfd = os.open(self.wnm,os.O_WRONLY)
            self.rfd = os.open(self.rnm,os.O_RDONLY)
        os.unlink(self.wnm)

    def _recover(self):
        try:
            os.close(os.open(self.rnm,os.O_WRONLY))
        except EnvironmentError:
            pass
        try:
            os.close(os.open(self.wnm,os.O_RDONLY))
        except EnvironmentError:
            pass

    def close(self):
        if self.rfd is not None:
            os.close(self.rfd)
            os.close(self.wfd)
            self.rfd = None
            self.wfd = None
            if os.path.isfile(self.wnm):
                os.unlink(self.wnm)
            try:
                if not os.listdir(self.tdir):
                    os.rmdir(self.tdir)
            except EnvironmentError, e:
                if e.errno != errno.ENOENT:
                    raise
        super(SecureStringPipe,self).close()


def find_exe(name,*args):
    path = os.environ.get("PATH","/bin:/usr/bin").split(":")
    if getattr(sys,"frozen",False):
        path.append(os.path.dirname(sys.executable))
    for dir in path:
        exe = os.path.join(dir,name)
        if os.path.exists(exe):
            return [exe] + list(args)
    return None


def spawn_sudo(proxy):
    """Spawn the sudo slave process, returning proc and a pipe to message it."""
    rnul = open(os.devnull,"r")
    wnul = open(os.devnull,"w")
    pipe = SecureStringPipe()
    c_pipe = pipe.connect()
    if not getattr(sys,"frozen",False):
        exe = [sys.executable,"-c","import esky; esky.run_startup_hooks()"]
    elif os.path.basename(sys.executable).lower() in ("python","pythonw"):
        exe = [sys.executable,"-c","import esky; esky.run_startup_hooks()"]
    else:
        if not esky._startup_hooks_were_run:
            raise OSError(None,"unable to sudo: startup hooks not run")
        exe = [sys.executable]
    args = ["--esky-spawn-sudo"]
    args.append(base.b64pickle(proxy))
    # Look for a variety of sudo-like programs
    sudo = None
    display_name = "%s update" % (proxy.name,)
    if "DISPLAY" in os.environ:
        sudo = find_exe("gksudo","-k","-D",display_name,"--")
        if sudo is None:
            sudo = find_exe("kdesudo")
        if sudo is None:
            sudo = find_exe("cocoasudo","--prompt='%s'" % (display_name,))
    if sudo is None:
        sudo = find_exe("sudo")
    if sudo is None:
        sudo = []
    # Make it a slave process so it dies if we die
    exe = sudo + exe + esky.slaveproc.get_slave_process_args() + args
    # Pass the pipe in environment vars, they seem to be harder to snoop.
    env = os.environ.copy()
    env["ESKY_SUDO_PIPE"] = base.b64pickle(c_pipe)
    # Spawn the subprocess
    kwds = dict(stdin=rnul,stdout=wnul,stderr=wnul,close_fds=True,env=env)
    proc = KillablePopen(exe,**kwds)
    return (proc,pipe)


def run_startup_hooks():
    if len(sys.argv) > 1 and sys.argv[1] == "--esky-spawn-sudo":
        proxy = base.b64unpickle(sys.argv[2])
        pipe = base.b64unpickle(os.environ["ESKY_SUDO_PIPE"])
        proxy.run(pipe)
        sys.exit(0)


########NEW FILE########
__FILENAME__ = sudo_win32
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.sudo.sudo_win32:  win32 platform-specific functionality for esky.sudo


This module implements the esky.sudo interface using ctypes bindings to the
native win32 API.  In particular, it uses the "runas" verb technique to
launch a process with administrative rights on Windows Vista and above.

"""

import os
import sys
import struct
import uuid
import ctypes
import ctypes.wintypes
import subprocess

from esky.sudo import sudo_base as base
import esky.slaveproc


byref = ctypes.byref
sizeof = ctypes.sizeof
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
advapi32 = ctypes.windll.advapi32

GENERIC_READ = -0x80000000
GENERIC_WRITE = 0x40000000
GENERIC_RDWR = GENERIC_READ | GENERIC_WRITE
OPEN_EXISTING = 3
TOKEN_QUERY = 8
SECURITY_MAX_SID_SIZE = 68
SECURITY_SQOS_PRESENT = 1048576
SECURITY_IDENTIFICATION = 65536
WinBuiltinAdministratorsSid = 26
ERROR_NO_SUCH_LOGON_SESSION = 1312
ERROR_PRIVILEGE_NOT_HELD = 1314
TokenLinkedToken = 19
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_NOASYNC  = 0x00000100


def _errcheck_bool(value,func,args):
    if not value:
        raise ctypes.WinError()
    return args

class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = (
      ("cbSize",ctypes.wintypes.DWORD),
      ("fMask",ctypes.c_ulong),
      ("hwnd",ctypes.wintypes.HANDLE),
      ("lpVerb",ctypes.c_char_p),
      ("lpFile",ctypes.c_char_p),
      ("lpParameters",ctypes.c_char_p),
      ("lpDirectory",ctypes.c_char_p),
      ("nShow",ctypes.c_int),
      ("hInstApp",ctypes.wintypes.HINSTANCE),
      ("lpIDList",ctypes.c_void_p),
      ("lpClass",ctypes.c_char_p),
      ("hKeyClass",ctypes.wintypes.HKEY),
      ("dwHotKey",ctypes.wintypes.DWORD),
      ("hIconOrMonitor",ctypes.wintypes.HANDLE),
      ("hProcess",ctypes.wintypes.HANDLE),
    )


try:
    ShellExecuteEx = shell32.ShellExecuteEx
except AttributeError:
    ShellExecuteEx = None
else:
    ShellExecuteEx.restype = ctypes.wintypes.BOOL
    ShellExecuteEx.errcheck = _errcheck_bool
    ShellExecuteEx.argtypes = (
        ctypes.POINTER(SHELLEXECUTEINFO),
    )

try:
    OpenProcessToken = advapi32.OpenProcessToken
except AttributeError:
    pass
else:
    OpenProcessToken.restype = ctypes.wintypes.BOOL
    OpenProcessToken.errcheck = _errcheck_bool
    OpenProcessToken.argtypes = (
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(ctypes.wintypes.HANDLE)
    )

try:
    CreateWellKnownSid = advapi32.CreateWellKnownSid
except AttributeError:
    pass
else:
    CreateWellKnownSid.restype = ctypes.wintypes.BOOL
    CreateWellKnownSid.errcheck = _errcheck_bool
    CreateWellKnownSid.argtypes = (
        ctypes.wintypes.DWORD,
        ctypes.POINTER(ctypes.wintypes.DWORD),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.wintypes.DWORD)
    )

try:
    CheckTokenMembership = advapi32.CheckTokenMembership
except AttributeError:
    pass
else:
    CheckTokenMembership.restype = ctypes.wintypes.BOOL
    CheckTokenMembership.errcheck = _errcheck_bool
    CheckTokenMembership.argtypes = (
        ctypes.wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.wintypes.BOOL)
    )

try:
    GetTokenInformation = advapi32.GetTokenInformation
except AttributeError:
    pass
else:
    GetTokenInformation.restype = ctypes.wintypes.BOOL
    GetTokenInformation.errcheck = _errcheck_bool
    GetTokenInformation.argtypes = (
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(ctypes.wintypes.DWORD)
    )



def has_root():
    """Check whether the user currently has root access."""
    return bool(shell32.IsUserAnAdmin())


def can_get_root():
    """Check whether the user may be able to get root access."""
    #  On XP or lower this is equivalent to has_root()
    if sys.getwindowsversion()[0] < 6:
        return bool(shell32.IsUserAnAdmin())
    #  On Vista or higher, there's the whole UAC token-splitting thing.
    #  Many thanks for Junfeng Zhang for the workflow:
    #      http://blogs.msdn.com/junfeng/archive/2007/01/26/how-to-tell-if-the-current-user-is-in-administrators-group-programmatically.aspx
    proc = kernel32.GetCurrentProcess()
    #  Get the token for the current process.
    try:
        token = ctypes.wintypes.HANDLE()
        OpenProcessToken(proc,TOKEN_QUERY,byref(token))
        try:
            #  Get the administrators SID.
            sid = ctypes.create_string_buffer(SECURITY_MAX_SID_SIZE)
            sz = ctypes.wintypes.DWORD(SECURITY_MAX_SID_SIZE)
            target_sid = WinBuiltinAdministratorsSid
            CreateWellKnownSid(target_sid,None,byref(sid),byref(sz))
            #  Check whether the token has that SID directly.
            has_admin = ctypes.wintypes.BOOL()
            CheckTokenMembership(None,byref(sid),byref(has_admin))
            if has_admin.value:
                return True
            #  Get the linked token.  Failure may mean no linked token.
            lToken = ctypes.wintypes.HANDLE()
            try:
                cls = TokenLinkedToken
                GetTokenInformation(token,cls,byref(lToken),sizeof(lToken),byref(sz))
            except WindowsError, e:
                if e.winerror == ERROR_NO_SUCH_LOGON_SESSION:
                    return False
                elif e.winerror == ERROR_PRIVILEGE_NOT_HELD:
                    return False
                else:
                    raise
            #  Check if the linked token has the admin SID
            try:
                CheckTokenMembership(lToken,byref(sid),byref(has_admin))
                return bool(has_admin.value)
            finally:
                kernel32.CloseHandle(lToken)
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(proc)



class KillablePopen(subprocess.Popen):
    """Popen that's guaranteed killable, even on python2.5."""
    if not hasattr(subprocess.Popen,"terminate"):
        def terminate(self):
            kernel32.TerminateProcess(self._handle,-1)


class FakePopen(KillablePopen):
    """Popen-alike based on a raw process handle."""
    def __init__(self,handle):
        super(FakePopen,self).__init__(None)
        self._handle = handle
    def terminate(self):
        kernel32.TerminateProcess(self._handle,-1)
    def _execute_child(self,*args,**kwds):
        pass
    

class SecureStringPipe(base.SecureStringPipe):
    """Two-way pipe for securely communicating strings with a sudo subprocess.

    This is the control pipe used for passing command data from the non-sudo
    master process to the sudo slave process.  Use read() to read the next
    string, write() to write the next string.

    On win32, this is implemented using CreateNamedPipe in the non-sudo
    master process, and connecting to the pipe from the sudo slave process.

    Security considerations to prevent hijacking of the pipe:

        * it has a strongly random name, so there can be no race condition
          before the pipe is created.
        * it has nMaxInstances set to 1 so another process cannot spoof the
          pipe while we are still alive.
        * the slave connects with pipe client impersonation disabled.

    A possible attack vector would be to wait until we spawn the slave process,
    capture the name of the pipe, then kill us and re-create the pipe to become
    the new master process.  Not sure what can be done about this, but at the
    very worst this will allow the attacker to call into the esky API with
    root privs; it *shouldn't* be sufficient to crack root on the machine...
    """

    def __init__(self,token=None,pipename=None):
        super(SecureStringPipe,self).__init__(token)
        if pipename is None:
            self.pipename = r"\\.\pipe\esky-" + uuid.uuid4().hex
            self.pipe = kernel32.CreateNamedPipeA(
                          self.pipename,0x03,0x00,1,8192,8192,0,None
                        )
        else:
            self.pipename = pipename
            self.pipe = None

    def connect(self):
        return SecureStringPipe(self.token,self.pipename)

    def _read(self,size):
        data = ctypes.create_string_buffer(size)
        szread = ctypes.c_int()
        kernel32.ReadFile(self.pipe,data,size,byref(szread),None)
        return data.raw[:szread.value]

    def _write(self,data):
        szwritten = ctypes.c_int()
        kernel32.WriteFile(self.pipe,data,len(data),byref(szwritten),None)

    def close(self):
        if self.pipe is not None:
            kernel32.CloseHandle(self.pipe)
            self.pipe = None
        super(SecureStringPipe,self).close()

    def _open(self):
        if self.pipe is None:
            self.pipe = kernel32.CreateFileA(
                self.pipename,GENERIC_RDWR,0,None,OPEN_EXISTING,
                SECURITY_SQOS_PRESENT|SECURITY_IDENTIFICATION,None
            )
        else:
            kernel32.ConnectNamedPipe(self.pipe,None)

    def _recover(self):
        kernel32.CreateFileA(
            self.pipename,GENERIC_RDWR,0,None,OPEN_EXISTING,
            SECURITY_SQOS_PRESENT|SECURITY_IDENTIFICATION,None
        )


def spawn_sudo(proxy):
    """Spawn the sudo slave process, returning proc and a pipe to message it.

    This function spawns the proxy app with administrator privileges, using
    ShellExecuteEx and the undocumented-but-widely-recommended "runas" verb.
    """
    pipe = SecureStringPipe()
    c_pipe = pipe.connect()
    if getattr(sys,"frozen",False):
        if not esky._startup_hooks_were_run:
            raise OSError(None,"unable to sudo: startup hooks not run")
        exe = [sys.executable]
    else:
        exe = [sys.executable,"-c","import esky; esky.run_startup_hooks()"]
    args = ["--esky-spawn-sudo"]
    args.append(base.b64pickle(proxy))
    args.append(base.b64pickle(c_pipe))
    # Make it a slave process so it dies if we die
    exe = exe + esky.slaveproc.get_slave_process_args() + args
    if sys.getwindowsversion()[0] < 6:
        kwds = {}
        if sys.hexversion >= 0x02060000:
            kwds["close_fds"] = True
        proc = KillablePopen(exe,**kwds)
    else:
        execinfo = SHELLEXECUTEINFO()
        execinfo.cbSize = sizeof(execinfo)
        execinfo.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
        execinfo.hwnd = None
        execinfo.lpVerb = "runas"
        execinfo.lpFile = exe[0]
        execinfo.lpParameters = " ".join(exe[1:])
        execinfo.lpDirectory = None
        execinfo.nShow = 0
        ShellExecuteEx(byref(execinfo))
        proc = FakePopen(execinfo.hProcess)
    return (proc,pipe)


def run_startup_hooks():
    if len(sys.argv) > 1 and sys.argv[1] == "--esky-spawn-sudo":
        proxy = base.b64unpickle(sys.argv[2])
        pipe = base.b64unpickle(sys.argv[3])
        proxy.run(pipe)
        sys.exit(0)

########NEW FILE########
__FILENAME__ = script1

#  Entry point for testing an esky install.

import os
import sys
import time
import errno


import esky
import esky.tests
import esky.util

ESKY_CONTROL_DIR = esky.util.ESKY_CONTROL_DIR
ESKY_APPDATA_DIR = esky.util.ESKY_APPDATA_DIR

#  Test that the frozen app is actually working
import eskytester
eskytester.yes_i_am_working()
eskytester.yes_my_deps_are_working()
eskytester.yes_my_data_is_installed()

assert sys.frozen
assert __name__ == "__main__"
app = esky.tests.TestableEsky(sys.executable,"http://localhost:8000/dist/")
assert app.name == "eskytester"
assert app.active_version == "0.1"
assert app.version == "0.1"
assert app.find_update() == "0.3"
assert os.path.isfile(eskytester.script_path(app,"script1"))

#  Test that the script is executed with sensible globals etc, so
#  it can create classes and other "complicated" things
class ATestClass(object):
    def __init__(self):
        self.a = "A"
class BTestClass(ATestClass):
    def __init__(self):
        super(BTestClass,self).__init__()
        self.a = "B"
assert BTestClass().a == "B"


#  Spawn another instance that just busy-loops,
#  holding a lock on the current version.
if len(sys.argv) > 1:
    while True:
        time.sleep(0.1)
    sys.exit(0)
else:
    #  This needs to be in a function because of something screwy in the way
    #  py2exe (or our wrapper) execs the script.  It doesn't leave global
    #  variables alive long enough for atexit functions to find them.
    def spawn_busy_loop(app):
        import os
        import atexit
        import signal
        import ctypes
        import subprocess
        import eskytester
        proc = subprocess.Popen([eskytester.script_path(app,"script1"),"busyloop"])
        assert proc.poll() is None
        @atexit.register
        def cleanup():
            assert proc.poll() is None
            if hasattr(proc,"terminate"):
                proc.terminate()
            else:
               if sys.platform == "win32":
                  ctypes.windll.kernel32.TerminateProcess(int(proc._handle),-1)
               else:
                  os.kill(proc.pid,signal.SIGTERM)
            proc.wait()
    spawn_busy_loop(app)

#  Upgrade to the next version (0.2, even though 0.3 is available)
if os.environ.get("ESKY_NEEDSROOT",""):
    already_root = app.has_root()
    app.get_root()
    assert app.has_root()
    app.drop_root()
    assert app.has_root() == already_root
    app.get_root()


app.install_version("0.2")
app.reinitialize()
assert app.name == "eskytester"
assert app.active_version == "0.1"
assert app.version == "0.2"
assert app.find_update() == "0.3"


assert os.path.isfile(eskytester.script_path(app,"script1"))
assert os.path.isfile(eskytester.script_path(app,"script2"))
if ESKY_APPDATA_DIR:
    assert os.path.isfile(os.path.join(os.path.dirname(app._get_versions_dir()),"eskytester-0.1."+esky.util.get_platform(),ESKY_CONTROL_DIR,"bootstrap-manifest.txt"))
else:
    assert os.path.isfile(os.path.join(app._get_versions_dir(),"eskytester-0.1."+esky.util.get_platform(),ESKY_CONTROL_DIR,"bootstrap-manifest.txt"))
assert os.path.isfile(os.path.join(app._get_versions_dir(),"eskytester-0.2."+esky.util.get_platform(),ESKY_CONTROL_DIR,"bootstrap-manifest.txt"))


#  Check that we can't uninstall a version that's in use.
if ESKY_APPDATA_DIR:
    assert esky.util.is_locked_version_dir(os.path.join(os.path.dirname(app._get_versions_dir()),"eskytester-0.1."+esky.util.get_platform()))
else:
    assert esky.util.is_locked_version_dir(os.path.join(app._get_versions_dir(),"eskytester-0.1."+esky.util.get_platform()))
try:
    app.uninstall_version("0.1")
except esky.VersionLockedError:
    pass
else:
    assert False, "in-use version was not locked"

open(os.path.join(app.appdir,"tests-completed"),"w").close()

########NEW FILE########
__FILENAME__ = script2

#  Second entry point for testing an esky install.

from __future__ import with_statement

import os
import sys
import stat
import subprocess
import esky
import esky.util
import esky.tests


ESKY_CONTROL_DIR = esky.util.ESKY_CONTROL_DIR
ESKY_APPDATA_DIR = esky.util.ESKY_APPDATA_DIR
 

platform = esky.util.get_platform()
if platform == "win32":
    import esky.winres
    dotexe = ".exe"
else:
    dotexe = ""

#  Check that the app is still working
import eskytester
eskytester.yes_i_am_working()
eskytester.yes_my_deps_are_working()
eskytester.yes_my_data_is_installed()

#  Sanity check the esky environment
assert sys.frozen
app = esky.tests.TestableEsky(sys.executable,"http://localhost:8000/dist/")
assert app.name == "eskytester"
assert app.active_version == app.version == "0.2"
assert app.find_update() == "0.3"
assert os.path.isfile(eskytester.script_path(app,"script1"))
assert os.path.isfile(eskytester.script_path(app,"script2"))

#  Test that MSVCRT was bundled correctly
if sys.platform == "win32" and sys.hexversion >= 0x02600000:
    versiondir = os.path.dirname(sys.executable)
    for nm in os.listdir(versiondir):
        if nm.startswith("Microsoft.") and nm.endswith(".CRT"):
            msvcrt_dir = os.path.join(versiondir,nm)
            assert os.path.isdir(msvcrt_dir)
            assert len(os.listdir(msvcrt_dir)) >= 2
            break
    else:
        assert False, "MSVCRT not bundled in version dir"
    for nm in os.listdir(app.appdir):
        if nm.startswith("Microsoft.") and nm.endswith(".CRT"):
            msvcrt_dir = os.path.join(app.appdir,nm)
            assert os.path.isdir(msvcrt_dir)
            assert len(os.listdir(msvcrt_dir)) >= 2
            break
    else:
        assert False, "MSVCRT not bundled in app dir"

if ESKY_APPDATA_DIR:
    v1dir = os.path.join(os.path.dirname(app._get_versions_dir()),"eskytester-0.1."+platform)
else:
    v1dir = os.path.join(app._get_versions_dir(),"eskytester-0.1."+platform)
v3dir = os.path.join(app._get_versions_dir(),"eskytester-0.3."+platform)

if len(sys.argv) == 1:
    # This is the first time we've run this script.
    assert os.path.isdir(v1dir)
    assert not os.path.isdir(v3dir)
    if os.environ.get("ESKY_NEEDSROOT",""):
        app.get_root()
    app.cleanup()
    assert not os.path.isdir(v1dir)
    assert not os.path.isdir(v3dir)
    #  Check that the bootstrap env is intact
    with open(os.path.join(app._get_versions_dir(),"eskytester-0.2."+platform,ESKY_CONTROL_DIR,"bootstrap-manifest.txt"),"rt") as mf:
        for nm in mf:
            nm = nm.strip()
            assert os.path.exists(os.path.join(app.appdir,nm))
    script2 = eskytester.script_path(app,"script2")
    #  Simulate a broken upgrade.
    upv3 = app.version_finder.fetch_version(app,"0.3")
    os.rename(upv3,v3dir)
    #  While we're here, check that the bootstrap library hasn't changed
    if os.path.exists(os.path.join(app.appdir,"library.zip")):
        f1 = open(os.path.join(app.appdir,"library.zip"),"rb")
        f2 = open(os.path.join(v3dir,ESKY_CONTROL_DIR,"bootstrap","library.zip"),"rb")
        assert f1.read() == f2.read()
        f1.close()
        f2.close()
    #  Also check one of the bootstrap exes to make sure it has changed safely
    if sys.platform == "win32":
        f1 = open(os.path.join(app.appdir,"script2"+dotexe),"rb")
        f2 = open(os.path.join(v3dir,ESKY_CONTROL_DIR,"bootstrap","script2"+dotexe),"rb")
        if f1.read() != f2.read():
            assert esky.winres.is_safe_to_overwrite(f1.name,f2.name), "bootstrap exe was changed unsafely"
        f1.close()
        f2.close()
    if sys.platform == "darwin":
        os.unlink(os.path.join(v3dir,ESKY_CONTROL_DIR,"bootstrap/Contents/MacOS/script2"))
    elif sys.platform != "win32":
        # win32 won't let us delete it since we loaded it as a library
        # when checking whether it was safe to overwrite.
        os.unlink(os.path.join(v3dir,ESKY_CONTROL_DIR,"bootstrap","script2"+dotexe))
    #  Re-launch the script.
    #  We should still be at version 0.2 after this.
    subprocess.check_call([script2,"rerun"])
else:
    # This is the second time we've run this script.
    #  Recover from the broken upgrade
    assert len(sys.argv) == 2
    assert os.path.isdir(v3dir)
    assert os.path.isfile(eskytester.script_path(app,"script2"))
    app.auto_update()
    assert os.path.isfile(eskytester.script_path(app,"script2"))
    assert not os.path.isfile(eskytester.script_path(app,"script1"))
    assert os.path.isfile(eskytester.script_path(app,"script3"))
    assert os.path.isdir(os.path.join(app._get_versions_dir(),"eskytester-0.2."+platform))
    assert os.path.isdir(os.path.join(app._get_versions_dir(),"eskytester-0.3."+platform))

    open(os.path.join(app.appdir,"tests-completed"),"w").close()



########NEW FILE########
__FILENAME__ = script3

#  Third entry point for testing an esky install.

import os
import sys
import time
import esky
import esky.util
import esky.tests

platform = esky.util.get_platform()

#  Test that the frozen app is actually working
import eskytester
eskytester.yes_i_am_working()
eskytester.yes_my_deps_are_working()
eskytester.yes_my_data_is_installed()

#  Test that we're at the best possible version
assert sys.frozen
app = esky.tests.TestableEsky(sys.executable,"http://localhost:8000/dist/")
assert app.name == "eskytester"
assert app.active_version == app.version == "0.3"
assert app.find_update() is None

if os.environ.get("ESKY_NEEDSROOT",""):
    app.get_root()

try:
    app.cleanup()
except esky.EskyLockedError:
    print "LOCKED, SLEEPING"
    time.sleep(10)
    app.cleanup()
assert os.path.isdir(os.path.join(app._get_versions_dir(),"eskytester-0.3."+platform))
assert not os.path.isfile(eskytester.script_path(app,"script1"))
assert os.path.isfile(eskytester.script_path(app,"script2"))
assert os.path.isfile(eskytester.script_path(app,"script3"))

#  Test that MSVCRT wasn't bundled with this version
if sys.platform == "win32":
    for nm in os.listdir(os.path.dirname(sys.executable)):
        if nm.startswith("Microsoft.") and nm.endswith(".CRT"):
            assert False, "MSVCRT bundled in version dir when it shouldn't be"
    for nm in os.listdir(app.appdir):
        if nm.startswith("Microsoft.") and nm.endswith(".CRT"):
            assert False, "MSVCRT bundled in appdir when it shouldn't be"

#  On windows, test that we were chainloaded without an execv
if sys.platform == "win32":
    if "ESKY_NO_CUSTOM_CHAINLOAD" not in os.environ:
        assert hasattr(sys,"bootstrap_executable"), "didn't chainload in-proc"


open(os.path.join(app.appdir,"tests-completed"),"w").close()

########NEW FILE########
__FILENAME__ = test_esky
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.

from __future__ import with_statement

import sys
import os
import unittest
from os.path import dirname
import subprocess
import shutil
import zipfile
import threading
import tempfile
import urllib2
import hashlib
import tarfile
import time
from contextlib import contextmanager
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

from distutils.core import setup as dist_setup
from distutils import dir_util

import esky
import esky.patch
import esky.sudo
from esky import bdist_esky
from esky.bdist_esky import Executable
from esky.util import extract_zipfile, deep_extract_zipfile, get_platform, \
                      ESKY_CONTROL_DIR, files_differ, ESKY_APPDATA_DIR, \
                      really_rmtree
from esky.fstransact import FSTransaction

try:
    import py2exe
except ImportError:
    py2exe = None
try:
    import py2app
except ImportError:
    py2app = None
try:
    import bbfreeze
except ImportError:
    bbfreeze = None
try:
    import cx_Freeze
except ImportError:
    cx_Freeze = None
try:
    import pypy
except ImportError:
    pypy = None

sys.path.append(os.path.dirname(__file__))


def assert_freezedir_exists(dist):
    assert os.path.exists(dist.freeze_dir)


if not hasattr(HTTPServer,"shutdown"):
    import socket
    def socketserver_shutdown(self):
        try:
            self.socket.close()
        except socket.error:
            pass
    HTTPServer.shutdown = socketserver_shutdown


@contextmanager
def setenv(key,value):
    oldval = os.environ.get(key,None)
    os.environ[key] = value
    yield
    if oldval is not None:
        os.environ[key] = oldval
    else:
        del os.environ[key]


class TestEsky(unittest.TestCase):

  if py2exe is not None:

    def test_esky_py2exe(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe"}})

    def test_esky_py2exe_bundle1(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                            "freezer_options": {
                                              "bundle_files": 1}}})

    def test_esky_py2exe_bundle2(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                            "freezer_options": {
                                              "bundle_files": 2}}})

    def test_esky_py2exe_bundle3(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                            "freezer_options": {
                                              "bundle_files": 3}}})

    def test_esky_py2exe_skiparchive(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                            "freezer_options": {
                                              "skip_archive": True}}})

    def test_esky_py2exe_unbuffered(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                            "freezer_options": {
                                              "unbuffered": True}}})

    def test_esky_py2exe_nocustomchainload(self):
        with setenv("ESKY_NO_CUSTOM_CHAINLOAD","1"):
           bscode = "_chainload = _orig_chainload\nbootstrap()"
           self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                               "bootstrap_code":bscode}})

    if esky.sudo.can_get_root():
        def test_esky_py2exe_needsroot(self):
            with setenv("ESKY_NEEDSROOT","1"):
               self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe"}})

    if pypy is not None:
        def test_esky_py2exe_pypy(self):
            self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                                "compile_bootstrap_exes":1}})
        def test_esky_py2exe_unbuffered_pypy(self):
            self._run_eskytester({"bdist_esky":{"freezer_module":"py2exe",
                                                "compile_bootstrap_exes":1,
                                                "freezer_options": {
                                                  "unbuffered": True}}})


  if py2app is not None:

    def test_esky_py2app(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"py2app"}})

    if esky.sudo.can_get_root():
        def test_esky_py2app_needsroot(self):
            with setenv("ESKY_NEEDSROOT","1"):
                self._run_eskytester({"bdist_esky":{"freezer_module":"py2app"}})

    if pypy is not None:
        def test_esky_py2app_pypy(self):
            self._run_eskytester({"bdist_esky":{"freezer_module":"py2app",
                                                "compile_bootstrap_exes":1}})

  if bbfreeze is not None:

    def test_esky_bbfreeze(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"bbfreeze"}})

    if sys.platform == "win32":
        def test_esky_bbfreeze_nocustomchainload(self):
            with setenv("ESKY_NO_CUSTOM_CHAINLOAD","1"):
               bscode = "_chainload = _orig_chainload\nbootstrap()"
               self._run_eskytester({"bdist_esky":{"freezer_module":"bbfreeze",
                                                   "bootstrap_code":bscode}})
    if esky.sudo.can_get_root():
        def test_esky_bbfreeze_needsroot(self):
            with setenv("ESKY_NEEDSROOT","1"):
                self._run_eskytester({"bdist_esky":{"freezer_module":"bbfreeze"}})

    if pypy is not None:
        def test_esky_bbfreeze_pypy(self):
            self._run_eskytester({"bdist_esky":{"freezer_module":"bbfreeze",
                                                "compile_bootstrap_exes":1}})

  if cx_Freeze is not None:

    def test_esky_cxfreeze(self):
        self._run_eskytester({"bdist_esky":{"freezer_module":"cxfreeze"}})

    if sys.platform == "win32":
        def test_esky_cxfreeze_nocustomchainload(self):
            with setenv("ESKY_NO_CUSTOM_CHAINLOAD","1"):
               bscode = ["_chainload = _orig_chainload",None]
               self._run_eskytester({"bdist_esky":{"freezer_module":"cxfreeze",
                                                   "bootstrap_code":bscode}})

    if esky.sudo.can_get_root():
        def test_esky_cxfreeze_needsroot(self):
            with setenv("ESKY_NEEDSROOT","1"):
                self._run_eskytester({"bdist_esky":{"freezer_module":"cxfreeze"}})

    if pypy is not None:
        def test_esky_cxfreeze_pypy(self):
            with setenv("ESKY_NO_CUSTOM_CHAINLOAD","1"):
              self._run_eskytester({"bdist_esky":{"freezer_module":"cxfreeze",
                                                 "compile_bootstrap_exes":1}})
 

  def _run_eskytester(self,options):
    """Build and run the eskytester app using the given distutils options.

    The "eskytester" application can be found next to this file, and the
    sequence of tests performed range across "script1.py" to "script3.py".
    """
    olddir = os.path.abspath(os.curdir)
#    tdir = os.path.join(os.path.dirname(__file__),"DIST")
#    if os.path.exists(tdir):
#        really_rmtree(tdir)
#    os.mkdir(tdir)
    tdir = tempfile.mkdtemp()
    server = None
    script2 = None
    try:
        options.setdefault("build",{})["build_base"] = os.path.join(tdir,"build")
        options.setdefault("bdist",{})["dist_dir"] = os.path.join(tdir,"dist")
        #  Set some callbacks to test that they work correctly
        options.setdefault("bdist_esky",{}).setdefault("pre_freeze_callback","esky.tests.test_esky.assert_freezedir_exists")
        options.setdefault("bdist_esky",{}).setdefault("pre_zip_callback",assert_freezedir_exists)
        platform = get_platform()
        deploydir = "deploy.%s" % (platform,)
        esky_root = dirname(dirname(dirname(__file__)))
        os.chdir(tdir)
        shutil.copytree(os.path.join(esky_root,"esky","tests","eskytester"),"eskytester")
        dir_util._path_created.clear()
        #  Build three increasing versions of the test package.
        #  Version 0.2 will include a bundled MSVCRT on win32.
        #  Version 0.3 will be distributed as a patch.
        metadata = dict(name="eskytester",packages=["eskytester"],author="rfk",
                        description="the esky test package",
                        data_files=[("data",["eskytester/datafile.txt"])],
                        package_data={"eskytester":["pkgdata.txt"]},)
        options2 = options.copy()
        options2["bdist_esky"] = options["bdist_esky"].copy()
        options2["bdist_esky"]["bundle_msvcrt"] = True
        script1 = "eskytester/script1.py"
        script2 = Executable([None,open("eskytester/script2.py")],name="script2")
        script3 = "eskytester/script3.py"
        dist_setup(version="0.1",scripts=[script1],options=options,script_args=["bdist_esky"],**metadata)
        dist_setup(version="0.2",scripts=[script1,script2],options=options2,script_args=["bdist_esky"],**metadata)
        dist_setup(version="0.3",scripts=[script2,script3],options=options,script_args=["bdist_esky_patch"],**metadata)
        os.unlink(os.path.join(tdir,"dist","eskytester-0.3.%s.zip"%(platform,)))
        #  Check that the patches apply cleanly
        uzdir = os.path.join(tdir,"unzip")
        deep_extract_zipfile(os.path.join(tdir,"dist","eskytester-0.1.%s.zip"%(platform,)),uzdir)
        with open(os.path.join(tdir,"dist","eskytester-0.3.%s.from-0.1.patch"%(platform,)),"rb") as f:
            esky.patch.apply_patch(uzdir,f)
        shutil.rmtree(uzdir)
        deep_extract_zipfile(os.path.join(tdir,"dist","eskytester-0.2.%s.zip"%(platform,)),uzdir)
        with open(os.path.join(tdir,"dist","eskytester-0.3.%s.from-0.2.patch"%(platform,)),"rb") as f:
            esky.patch.apply_patch(uzdir,f)
        shutil.rmtree(uzdir)
        #  Serve the updates at http://localhost:8000/dist/
        print "running local update server"
        server = HTTPServer(("localhost",8000),SimpleHTTPRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        #  Set up the deployed esky environment for the initial version
        zfname = os.path.join(tdir,"dist","eskytester-0.1.%s.zip"%(platform,))
        os.mkdir(deploydir)
        extract_zipfile(zfname,deploydir)
        #  Run the scripts in order.
        if options["bdist_esky"]["freezer_module"] == "py2app":
            appdir = os.path.join(deploydir,os.listdir(deploydir)[0])
            cmd1 = os.path.join(appdir,"Contents","MacOS","script1")
            cmd2 = os.path.join(appdir,"Contents","MacOS","script2")
            cmd3 = os.path.join(appdir,"Contents","MacOS","script3")
        else:
            appdir = deploydir
            if sys.platform == "win32":
                cmd1 = os.path.join(deploydir,"script1.exe")
                cmd2 = os.path.join(deploydir,"script2.exe")
                cmd3 = os.path.join(deploydir,"script3.exe")
            else:
                cmd1 = os.path.join(deploydir,"script1")
                cmd2 = os.path.join(deploydir,"script2")
                cmd3 = os.path.join(deploydir,"script3")
        print "spawning eskytester script1", options["bdist_esky"]["freezer_module"]
        os.unlink(os.path.join(tdir,"dist","eskytester-0.1.%s.zip"%(platform,)))
        p = subprocess.Popen(cmd1)
        assert p.wait() == 0
        os.unlink(os.path.join(appdir,"tests-completed"))
        print "spawning eskytester script2"
        os.unlink(os.path.join(tdir,"dist","eskytester-0.2.%s.zip"%(platform,)))
        p = subprocess.Popen(cmd2)
        assert p.wait() == 0
        os.unlink(os.path.join(appdir,"tests-completed"))
        print "spawning eskytester script3"
        p = subprocess.Popen(cmd3)
        assert p.wait() == 0
        os.unlink(os.path.join(appdir,"tests-completed"))
    finally:
        if script2:
            script2.script[1].close()
        os.chdir(olddir)
        if sys.platform == "win32":
           # wait for the cleanup-at-exit pocess to finish
           time.sleep(4)
        really_rmtree(tdir)
        if server:
            server.shutdown()
 
  def test_esky_locking(self):
    """Test that locking an Esky works correctly."""
    platform = get_platform()
    appdir = tempfile.mkdtemp()
    try: 
        vdir = os.path.join(appdir,ESKY_APPDATA_DIR,"testapp-0.1.%s" % (platform,))
        os.makedirs(vdir)
        os.mkdir(os.path.join(vdir,ESKY_CONTROL_DIR))
        open(os.path.join(vdir,ESKY_CONTROL_DIR,"bootstrap-manifest.txt"),"wb").close()
        e1 = esky.Esky(appdir,"http://example.com/downloads/")
        assert e1.name == "testapp"
        assert e1.version == "0.1"
        assert e1.platform == platform
        e2 = esky.Esky(appdir,"http://example.com/downloads/")
        assert e2.name == "testapp"
        assert e2.version == "0.1"
        assert e2.platform == platform
        locked = []; errors = [];
        trigger1 = threading.Event(); trigger2 = threading.Event()
        def runit(e,t1,t2):
            def runme():
                try:
                    e.lock()
                except Exception, err:
                    errors.append(err)
                else:
                    locked.append(e)
                t1.set()
                t2.wait()
            return runme
        t1 = threading.Thread(target=runit(e1,trigger1,trigger2))
        t2 = threading.Thread(target=runit(e2,trigger2,trigger1))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(locked) == 1
        assert (e1 in locked or e2 in locked)
        assert len(errors) == 1
        assert isinstance(errors[0],esky.EskyLockedError)
    finally:
        shutil.rmtree(appdir)

 
  def test_esky_lock_breaking(self):
    """Test that breaking the lock on an Esky works correctly."""
    appdir = tempfile.mkdtemp()
    try: 
        os.makedirs(os.path.join(appdir,ESKY_APPDATA_DIR,"testapp-0.1",ESKY_CONTROL_DIR))
        open(os.path.join(appdir,ESKY_APPDATA_DIR,"testapp-0.1",ESKY_CONTROL_DIR,"bootstrap-manifest.txt"),"wb").close()
        e1 = esky.Esky(appdir,"http://example.com/downloads/")
        e2 = esky.Esky(appdir,"http://example.com/downloads/")
        trigger1 = threading.Event(); trigger2 = threading.Event()
        errors = []
        def run1():
            try:
                e1.lock()
            except Exception, err:
                errors.append(err)
            trigger1.set()
            trigger2.wait()
        def run2():
            trigger1.wait()
            try:
                e2.lock()
            except esky.EskyLockedError:
                pass
            except Exception, err:
                errors.append(err)
            else:
                errors.append("locked when I shouldn't have")
            e2.lock_timeout = 0.1
            time.sleep(0.5)
            try:
                e2.lock()
            except Exception, err:
                errors.append(err)
            trigger2.set()
        t1 = threading.Thread(target=run1)
        t2 = threading.Thread(target=run2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(errors) == 0, str(errors)
    finally:
        shutil.rmtree(appdir)


  def test_README(self):
    """Ensure that the README is in sync with the docstring.

    This test should always pass; if the README is out of sync it just updates
    it with the contents of esky.__doc__.
    """
    dirname = os.path.dirname
    readme = os.path.join(dirname(dirname(dirname(__file__))),"README.rst")
    if not os.path.isfile(readme):
        f = open(readme,"wb")
        f.write(esky.__doc__.encode())
        f.close()
    else:
        f = open(readme,"rb")
        if f.read() != esky.__doc__:
            f.close()
            f = open(readme,"wb")
            f.write(esky.__doc__.encode())
            f.close()


class TestFSTransact(unittest.TestCase):
    """Testcases for FSTransact."""

    def setUp(self):
        self.testdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def path(self,path):
        return os.path.join(self.testdir,path)

    def setContents(self,path,contents=""):
        if not os.path.isdir(os.path.dirname(self.path(path))):
            os.makedirs(os.path.dirname(self.path(path)))
        with open(self.path(path),"wb") as f:
            f.write(contents.encode())

    def assertContents(self,path,contents):
        with open(self.path(path),"rb") as f:
            self.assertEquals(f.read().decode(),contents)

    def test_no_move_outside_root(self):
        self.setContents("file1","hello world")
        trn = FSTransaction(self.testdir)
        trn.move(self.path("file1"),"file2")
        trn.commit()
        self.assertContents("file2","hello world")
        trn = FSTransaction(self.testdir)
        self.assertRaises(ValueError,trn.move,self.path("file2"),"../file1")
        trn.abort()

    def test_move_file(self):
        self.setContents("file1","hello world")
        trn = FSTransaction()
        trn.move(self.path("file1"),self.path("file2"))
        self.assertContents("file1","hello world")
        self.assertFalse(os.path.exists(self.path("file2")))
        trn.commit()
        self.assertContents("file2","hello world")
        self.assertFalse(os.path.exists(self.path("file1")))

    def test_move_file_with_unicode_name(self):
        self.setContents(u"file\N{SNOWMAN}","hello world")
        trn = FSTransaction()
        trn.move(self.path(u"file\N{SNOWMAN}"),self.path("file2"))
        self.assertContents(u"file\N{SNOWMAN}","hello world")
        self.assertFalse(os.path.exists(self.path("file2")))
        trn.commit()
        self.assertContents("file2","hello world")
        self.assertFalse(os.path.exists(self.path(u"file\N{SNOWMAN}")))

    def test_copy_file(self):
        self.setContents("file1","hello world")
        trn = FSTransaction()
        trn.copy(self.path("file1"),self.path("file2"))
        self.assertContents("file1","hello world")
        self.assertFalse(os.path.exists(self.path("file2")))
        trn.commit()
        self.assertContents("file1","hello world")
        self.assertContents("file2","hello world")

    def test_move_dir(self):
        self.setContents("dir1/file1","hello world")
        self.setContents("dir1/file2","how are you?")
        self.setContents("dir1/subdir/file3","fine thanks")
        trn = FSTransaction()
        trn.move(self.path("dir1"),self.path("dir2"))
        self.assertContents("dir1/file1","hello world")
        self.assertFalse(os.path.exists(self.path("dir2")))
        trn.commit()
        self.assertContents("dir2/file1","hello world")
        self.assertContents("dir2/file2","how are you?")
        self.assertContents("dir2/subdir/file3","fine thanks")
        self.assertFalse(os.path.exists(self.path("dir1")))

    def test_copy_dir(self):
        self.setContents("dir1/file1","hello world")
        self.setContents("dir1/file2","how are you?")
        self.setContents("dir1/subdir/file3","fine thanks")
        trn = FSTransaction()
        trn.copy(self.path("dir1"),self.path("dir2"))
        self.assertContents("dir1/file1","hello world")
        self.assertFalse(os.path.exists(self.path("dir2")))
        trn.commit()
        self.assertContents("dir2/file1","hello world")
        self.assertContents("dir2/file2","how are you?")
        self.assertContents("dir2/subdir/file3","fine thanks")
        self.assertContents("dir1/file1","hello world")
        self.assertContents("dir1/file2","how are you?")
        self.assertContents("dir1/subdir/file3","fine thanks")

    def test_remove(self):
        self.setContents("dir1/file1","hello there world")
        trn = FSTransaction()
        trn.remove(self.path("dir1/file1"))
        self.assertTrue(os.path.exists(self.path("dir1/file1")))
        trn.commit()
        self.assertFalse(os.path.exists(self.path("dir1/file1")))
        self.assertTrue(os.path.exists(self.path("dir1")))
        trn = FSTransaction()
        trn.remove(self.path("dir1"))
        trn.commit()
        self.assertFalse(os.path.exists(self.path("dir1")))

    def test_remove_abort(self):
        self.setContents("dir1/file1","hello there world")
        trn = FSTransaction()
        trn.remove(self.path("dir1/file1"))
        self.assertTrue(os.path.exists(self.path("dir1/file1")))
        trn.abort()
        self.assertTrue(os.path.exists(self.path("dir1/file1")))
        trn = FSTransaction()
        trn.remove(self.path("dir1"))
        trn.abort()
        self.assertTrue(os.path.exists(self.path("dir1/file1")))
        trn = FSTransaction()
        trn.remove(self.path("dir1"))
        trn.commit()
        self.assertFalse(os.path.exists(self.path("dir1")))

    def test_move_dir_exists(self):
        self.setContents("dir1/file0","zero zero zero")
        self.setContents("dir1/file1","hello world")
        self.setContents("dir1/file2","how are you?")
        self.setContents("dir1/subdir/file3","fine thanks")
        self.setContents("dir2/file1","different contents")
        self.setContents("dir2/file3","a different file")
        self.setContents("dir1/subdir/file3","fine thanks")
        trn = FSTransaction()
        trn.move(self.path("dir1"),self.path("dir2"))
        self.assertContents("dir1/file1","hello world")
        trn.commit()
        self.assertContents("dir2/file0","zero zero zero")
        self.assertContents("dir2/file1","hello world")
        self.assertContents("dir2/file2","how are you?")
        self.assertFalse(os.path.exists(self.path("dir2/file3")))
        self.assertContents("dir2/subdir/file3","fine thanks")
        self.assertFalse(os.path.exists(self.path("dir1")))

    def test_copy_dir_exists(self):
        self.setContents("dir1/file0","zero zero zero")
        self.setContents("dir1/file1","hello world")
        self.setContents("dir1/file2","how are you?")
        self.setContents("dir1/subdir/file3","fine thanks")
        self.setContents("dir2/file1","different contents")
        self.setContents("dir2/file3","a different file")
        self.setContents("dir1/subdir/file3","fine thanks")
        trn = FSTransaction()
        trn.copy(self.path("dir1"),self.path("dir2"))
        self.assertContents("dir1/file1","hello world")
        trn.commit()
        self.assertContents("dir2/file0","zero zero zero")
        self.assertContents("dir2/file1","hello world")
        self.assertContents("dir2/file2","how are you?")
        self.assertFalse(os.path.exists(self.path("dir2/file3")))
        self.assertContents("dir2/subdir/file3","fine thanks")
        self.assertContents("dir1/file0","zero zero zero")
        self.assertContents("dir1/file1","hello world")
        self.assertContents("dir1/file2","how are you?")
        self.assertContents("dir1/subdir/file3","fine thanks")

    def test_move_dir_over_file(self):
        self.setContents("dir1/file0","zero zero zero")
        self.setContents("dir2","actually a file")
        trn = FSTransaction()
        trn.move(self.path("dir1"),self.path("dir2"))
        self.assertContents("dir1/file0","zero zero zero")
        trn.commit()
        self.assertContents("dir2/file0","zero zero zero")
        self.assertFalse(os.path.exists(self.path("dir1")))

    def test_copy_dir_over_file(self):
        self.setContents("dir1/file0","zero zero zero")
        self.setContents("dir2","actually a file")
        trn = FSTransaction()
        trn.copy(self.path("dir1"),self.path("dir2"))
        self.assertContents("dir1/file0","zero zero zero")
        trn.commit()
        self.assertContents("dir2/file0","zero zero zero")
        self.assertContents("dir1/file0","zero zero zero")

    def test_move_file_over_dir(self):
        self.setContents("file0","zero zero zero")
        self.setContents("dir2/myfile","hahahahaha!")
        trn = FSTransaction()
        trn.move(self.path("file0"),self.path("dir2"))
        self.assertContents("file0","zero zero zero")
        self.assertContents("dir2/myfile","hahahahaha!")
        trn.commit()
        self.assertContents("dir2","zero zero zero")
        self.assertFalse(os.path.exists(self.path("file0")))

    def test_copy_file_over_dir(self):
        self.setContents("file0","zero zero zero")
        self.setContents("dir2/myfile","hahahahaha!")
        trn = FSTransaction()
        trn.copy(self.path("file0"),self.path("dir2"))
        self.assertContents("file0","zero zero zero")
        self.assertContents("dir2/myfile","hahahahaha!")
        trn.commit()
        self.assertContents("dir2","zero zero zero")
        self.assertContents("file0","zero zero zero")


class TestPatch(unittest.TestCase):
    """Testcases for esky.patch."""
 
    _TEST_FILES = (
        ("pyenchant-1.2.0.tar.gz","2fefef0868b110b1da7de89c08344dd2"),
        ("pyenchant-1.5.2.tar.gz","fa1e4f3f3c473edd98c7bb0e46eea352"),
        ("pyenchant-1.6.0.tar.gz","3fd7336989764d8d379a367236518439"),
    )

    _TEST_FILES_URL = "http://pypi.python.org/packages/source/p/pyenchant/"

    def setUp(self):
        self.tests_root = dirname(__file__)
        platform = get_platform()
        self.tfdir = tfdir = os.path.join(self.tests_root,"patch-test-files")
        self.workdir = workdir = os.path.join(self.tests_root,"patch-test-temp."+platform)
        if not os.path.isdir(tfdir):
            os.makedirs(tfdir)
        if not os.path.isdir(workdir):
            os.makedirs(workdir)
        #  Ensure we have the expected test files.
        #  Download from PyPI if necessary.
        for (tfname,hash) in self._TEST_FILES:
            tfpath = os.path.join(tfdir,tfname)
            if not os.path.exists(tfpath):
                data = urllib2.urlopen(self._TEST_FILES_URL+tfname).read()
                assert hashlib.md5(data).hexdigest() == hash
                with open(tfpath,"wb") as f:
                    f.write(data)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_patch_bigfile(self):
        tdir = tempfile.mkdtemp()
        try:
            data = [os.urandom(100)*10 for i in xrange(6)]
            for nm in ("source","target"):
                with open(os.path.join(tdir,nm),"wb") as f:
                    for i in xrange(1000):
                        for chunk in data:
                            f.write(chunk)
                data[2],data[3] = data[3],data[2]
            with open(os.path.join(tdir,"patch"),"wb") as f:
                esky.patch.write_patch(os.path.join(tdir,"source"),os.path.join(tdir,"target"),f)
            dgst1 = esky.patch.calculate_digest(os.path.join(tdir,"target"))
            dgst2 = esky.patch.calculate_digest(os.path.join(tdir,"source"))
            self.assertNotEquals(dgst1,dgst2)
            with open(os.path.join(tdir,"patch"),"rb") as f:
                esky.patch.apply_patch(os.path.join(tdir,"source"),f)
            dgst3 = esky.patch.calculate_digest(os.path.join(tdir,"source"))
            self.assertEquals(dgst1,dgst3)
        finally:
            shutil.rmtree(tdir)

    def test_diffing_back_and_forth(self):
        for (tf1,_) in self._TEST_FILES:
            for (tf2,_) in self._TEST_FILES:
                path1 = self._extract(tf1,"source")
                path2 = self._extract(tf2,"target")
                with open(os.path.join(self.workdir,"patch"),"wb") as f:
                    esky.patch.write_patch(path1,path2,f)
                if tf1 != tf2:
                    self.assertNotEquals(esky.patch.calculate_digest(path1),
                                         esky.patch.calculate_digest(path2))
                with open(os.path.join(self.workdir,"patch"),"rb") as f:
                    esky.patch.apply_patch(path1,f)
                self.assertEquals(esky.patch.calculate_digest(path1),
                                  esky.patch.calculate_digest(path2))

    def test_apply_patch(self):
        path1 = self._extract("pyenchant-1.2.0.tar.gz","source")
        path2 = self._extract("pyenchant-1.6.0.tar.gz","target")
        path1 = os.path.join(path1,"pyenchant-1.2.0")
        path2 = os.path.join(path2,"pyenchant-1.6.0")
        pf = os.path.join(self.tfdir,"v1.2.0_to_v1.6.0.patch")
        if not os.path.exists(pf):
            pf = os.path.join(dirname(esky.__file__),"tests","patch-test-files","v1.2.0_to_v1.6.0.patch")
        with open(pf,"rb") as f:
            esky.patch.apply_patch(path1,f)
        self.assertEquals(esky.patch.calculate_digest(path1),
                         esky.patch.calculate_digest(path2))

    def test_copying_multiple_targets_from_a_single_sibling(self):
        join = os.path.join
        src_dir = src_dir = join(self.workdir, "source")
        tgt_dir = tgt_dir = join(self.workdir, "target")
        for dirnm in src_dir, tgt_dir:
            os.mkdir(dirnm)
        zf = zipfile.ZipFile(join(self.tfdir, "movefrom-source.zip"), "r")
        zf.extractall(src_dir)
        zf = zipfile.ZipFile(join(self.tfdir, "movefrom-target.zip"), "r")
        zf.extractall(tgt_dir)

        # The two directory structures should initially be difference.
        self.assertNotEquals(esky.patch.calculate_digest(src_dir),
                             esky.patch.calculate_digest(tgt_dir))

        # Create patch from source to target.
        patch_fname = join(self.workdir, "patch")
        with open(patch_fname, "wb") as patchfile:
            esky.patch.write_patch(src_dir, tgt_dir, patchfile)

        # Try to apply the patch.
        with open(patch_fname, "rb") as patchfile:
            esky.patch.apply_patch(src_dir, patchfile)

        # Then the two directory structures should be equal.
        self.assertEquals(esky.patch.calculate_digest(src_dir),
                          esky.patch.calculate_digest(tgt_dir))

    def _extract(self,filename,dest):
        dest = os.path.join(self.workdir,dest)
        if os.path.exists(dest):
            really_rmtree(dest)
        f = tarfile.open(os.path.join(self.tfdir,filename),"r:gz")
        try:
            f.extractall(dest)
        finally:
            f.close()
        return dest


class TestPatch_cxbsdiff(TestPatch):
    """Test the patching code with cx-bsdiff rather than bsdiff4."""

    def setUp(self):
        self.__orig_bsdiff4 = esky.patch.bsdiff4
        if esky.patch.bsdiff4_cx is not None:
            esky.patch.bsdiff4 = esky.patch.bsdiff4_cx
        return super(TestPatch_cxbsdiff,self).setUp()

    def tearDown(self):
        esky.patch.bsdiff4 = self.__orig_bsdiff4
        return super(TestPatch_cxbsdiff,self).tearDown()


class TestPatch_pybsdiff(TestPatch):
    """Test the patching code with pure-python bsdiff4."""

    def setUp(self):
        self.__orig_bsdiff4 = esky.patch.bsdiff4
        esky.patch.bsdiff4 = esky.patch.bsdiff4_py
        return super(TestPatch_pybsdiff,self).setUp()

    def tearDown(self):
        esky.patch.bsdiff4 = self.__orig_bsdiff4
        return super(TestPatch_pybsdiff,self).tearDown()
    
        

class TestFilesDiffer(unittest.TestCase):

    def setUp(self):
        self.tdir = tempfile.mkdtemp()

    def _path(self,*names):
        return os.path.join(self.tdir,*names)

    def _differs(self,data1,data2,start=0,stop=None):
        with open(self._path("file1"),"wb") as f:
            f.write(data1.encode("ascii"))
        with open(self._path("file2"),"wb") as f:
            f.write(data2.encode("ascii"))
        return files_differ(self._path("file1"),self._path("file2"),start,stop)

    def test_files_differ(self):
        assert self._differs("one","two")
        assert self._differs("onethreetwo","twothreeone")
        assert self._differs("onethreetwo","twothreeone",3)
        assert not self._differs("onethreetwo","twothreeone",3,-3)
        assert self._differs("onethreetwo","twothreeone",2,-3)
        assert self._differs("onethreetwo","twothreeone",3,-2)

    def tearDown(self):
        shutil.rmtree(self.tdir)


########NEW FILE########
__FILENAME__ = util
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.util:  misc utility functions for esky

"""

from __future__ import with_statement
from __future__ import absolute_import

import sys
import errno

#  Since esky apps are required to call the esky.run_startup_hooks() method on
#  every invocation, we want as little overhead as possible when importing
#  the main module.  We therefore use a simple lazy-loading scheme for many
#  of our imports, built from the functions below.

def lazy_import(func):
    """Decorator for declaring a lazy import.

    This decorator turns a function into an object that will act as a lazy
    importer.  Whenever the object's attributes are accessed, the function
    is called and its return value used in place of the object.  So you
    can declare lazy imports like this:

        @lazy_import
        def socket():
            import socket
            return socket

    The name "socket" will then be bound to a transparent object proxy which
    will import the socket module upon first use.

    The syntax here is slightly more verbose than other lazy import recipes,
    but it's designed not to hide the actual "import" statements from tools
    like py2exe or grep.
    """
    try:
        f = sys._getframe(1)
    except Exception:
        namespace = None
    else:
        namespace = f.f_locals
    return _LazyImport(func.func_name,func,namespace)


class _LazyImport(object):
    """Class representing a lazy import."""

    def __init__(self,name,loader,namespace=None):
        self._esky_lazy_target = _LazyImport
        self._esky_lazy_name = name
        self._esky_lazy_loader = loader
        self._esky_lazy_namespace = namespace

    def _esky_lazy_load(self):
        if self._esky_lazy_target is _LazyImport:
            self._esky_lazy_target = self._esky_lazy_loader()
            ns = self._esky_lazy_namespace
            if ns is not None:
                try:
                    if ns[self._esky_lazy_name] is self:
                        ns[self._esky_lazy_name] = self._esky_lazy_target
                except KeyError:
                    pass

    def __getattribute__(self,attr):
        try:
            return object.__getattribute__(self,attr)
        except AttributeError:
            if self._esky_lazy_target is _LazyImport:
                self._esky_lazy_load()
            return getattr(self._esky_lazy_target,attr)

    def __nonzero__(self):
        if self._esky_lazy_target is _LazyImport:
            self._esky_lazy_load()
        return bool(self._esky_lazy_target)


@lazy_import
def os():
    import os
    return os

@lazy_import
def shutil():
    import shutil
    return shutil

@lazy_import
def time():
    import time
    return time

@lazy_import
def re():
    import re
    return re

@lazy_import
def zipfile():
    import zipfile
    return zipfile

@lazy_import
def itertools():
    import itertools
    return itertools

@lazy_import
def StringIO():
    try:
        import cStringIO as StringIO
    except ImportError:
        import StringIO
    return StringIO

@lazy_import
def distutils():
    import distutils
    import distutils.log   # need to prompt cxfreeze about this dep
    import distutils.util
    return distutils


from esky.bootstrap import appdir_from_executable as _bs_appdir_from_executable
from esky.bootstrap import get_best_version, get_all_versions,\
                           is_version_dir, is_installed_version_dir,\
                           is_uninstalled_version_dir,\
                           split_app_version, join_app_version, parse_version,\
                           get_original_filename, lock_version_dir,\
                           unlock_version_dir, fcntl, ESKY_CONTROL_DIR,\
                           ESKY_APPDATA_DIR


def files_differ(file1,file2,start=0,stop=None):
    """Check whether two files are actually different."""
    try:
        stat1 = os.stat(file1)
        stat2 = os.stat(file2)
    except EnvironmentError:
         return True
    if stop is None and stat1.st_size != stat2.st_size:
        return True
    f1 = open(file1,"rb")
    try:
        f2 = open(file2,"rb")
        if start >= stat1.st_size:
            return False
        elif start < 0:
            start = stat1.st_size + start
        if stop is None or stop > stat1.st_size:
            stop = stat1.st_size
        elif stop < 0:
            stop = stat1.st_size + stop
        if stop <= start:
            return False
        toread = stop - start
        f1.seek(start)
        f2.seek(start)
        try:
            sz = min(1024*256,toread)
            data1 = f1.read(sz)
            data2 = f2.read(sz)
            while sz > 0 and data1 and data2:
                if data1 != data2:
                    return True
                toread -= sz
                sz = min(1024*256,toread)
                data1 = f1.read(sz)
                data2 = f2.read(sz)
            return (data1 != data2)
        finally:
            f2.close()
    finally:
        f1.close()


def pairwise(iterable):
    """Iterator over pairs of elements from the given iterable."""
    a,b = itertools.tee(iterable)
    try:
        b.next()
    except StopIteration:
        pass
    return itertools.izip(a,b)


def common_prefix(iterables):
    """Find the longest common prefix of a series of iterables."""
    iterables = iter(iterables)
    try:
        prefix = iterables.next()
    except StopIteration:
        raise ValueError("at least one iterable is required")
    for item in iterables:
        count = 0
        for (c1,c2) in itertools.izip(prefix,item):
            if c1 != c2:
                break
            count += 1
        prefix = prefix[:count]
    return prefix


def appdir_from_executable(exepath):
    """Find the top-level application directory, given sys.executable."""
    #  The standard layout is <appdir>/ESKY_APPDATA_DIR/<vdir>/<exepath>.
    #  Stripping of <exepath> is done by _bs_appdir_from_executable.
    vdir = _bs_appdir_from_executable(exepath)
    appdir = os.path.dirname(vdir)
    #  On OSX we sometimes need to strip an additional directory since the
    #  app can be contained in an <appname>.app directory.
    if sys.platform == "darwin" and is_version_dir(appdir):
        appdir = os.path.dirname(appdir)
    # TODO: remove compatability hook for ESKY_APPDATA_DIR=""
    if ESKY_APPDATA_DIR and os.path.basename(appdir) == ESKY_APPDATA_DIR:
        appdir = os.path.dirname(appdir)
    return appdir


def appexe_from_executable(exepath):
    """Find the top-level application executable, given sys.executable."""
    appdir = appdir_from_executable(exepath)
    exename = os.path.basename(exepath)
    #  On OSX we might be in a bundle, run from Contents/MacOS/<exename>
    if sys.platform == "darwin":
        osx_dot_app_name = os.path.basename(appdir)
        potential_py2app_bootstrap_exe = None
        if osx_dot_app_name.endswith('.app'):
            potential_py2app_bootstrap_exe = osx_dot_app_name[:-4]
        app_bin_dir = os.path.join(appdir,"Contents","MacOS")
        if os.path.isdir(app_bin_dir):
            if potential_py2app_bootstrap_exe and os.path.exists(
                    os.path.join(app_bin_dir, potential_py2app_bootstrap_exe)):
                return os.path.join(app_bin_dir, potential_py2app_bootstrap_exe)
            return os.path.join(app_bin_dir, exename)
    return os.path.join(appdir,exename)


def extract_zipfile(source,target,name_filter=None):
    """Extract the contents of a zipfile into a target directory.

    The argument 'source' names the zipfile to read, while 'target' names
    the directory into which to extract.  If given, the optional argument
    'name_filter' must be a function mapping names from the zipfile to names
    in the target directory.
    """
    zf = zipfile.ZipFile(source,"r")
    try:
        if hasattr(zf,"open"):
            zf_open = zf.open
        else:
            def zf_open(nm,mode):
                return StringIO.StringIO(zf.read(nm))
        for nm in zf.namelist():
            if nm.endswith("/"):
                continue
            if name_filter:
                outfilenm = name_filter(nm)
                if outfilenm is None:
                    continue
                outfilenm = os.path.join(target,outfilenm)
            else:
                outfilenm = os.path.join(target,nm)
            if not os.path.isdir(os.path.dirname(outfilenm)):
                os.makedirs(os.path.dirname(outfilenm))
            infile = zf_open(nm,"r")
            try:
                outfile = open(outfilenm,"wb")
                try:
                    shutil.copyfileobj(infile,outfile)
                finally:
                    outfile.close()
            finally:
                infile.close()
            mode = zf.getinfo(nm).external_attr >> 16L
            if mode:
                os.chmod(outfilenm,mode)
    finally:
        zf.close()


def zipfile_common_prefix_dir(source):
    """Find the common prefix directory of all files in a zipfile."""
    zf = zipfile.ZipFile(source)
    prefix = common_prefix(zf.namelist())
    if "/" in prefix:
        return prefix.rsplit("/",1)[0] + "/"
    else:
        return ""


def deep_extract_zipfile(source,target,name_filter=None):
    """Extract the deep contents of a zipfile into a target directory.

    This is just like extract_zipfile() except that any common prefix dirs
    are removed.  For example, if everything in the zipfile is under the
    directory "example.app" then that prefix will be removed during unzipping.

    This is useful to allow distribution of "friendly" zipfiles that don't
    overwrite files in the current directory when extracted by hand.
    """
    prefix = zipfile_common_prefix_dir(source)
    if prefix:
        def new_name_filter(nm):
            if not nm.startswith(prefix):
                return None
            if name_filter is not None:
                return name_filter(nm[len(prefix):])
            return nm[len(prefix):]
    else:
         new_name_filter = name_filter
    return extract_zipfile(source,target,new_name_filter)



def create_zipfile(source,target,get_zipinfo=None,members=None,compress=None):
    """Bundle the contents of a given directory into a zipfile.

    The argument 'source' names the directory to read, while 'target' names
    the zipfile to be written.

    If given, the optional argument 'get_zipinfo' must be a function mapping
    filenames to ZipInfo objects.  It may also return None to indicate that
    defaults should be used, or a string to indicate that defaults should be
    used with a new archive name.

    If given, the optional argument 'members' must be an iterable yielding
    names or ZipInfo objects.  Files will be added to the archive in the
    order specified by this function.

    If the optional argument 'compress' is given, it must be a bool indicating
    whether to compress the files by default.  The default is no compression.
    """
    if not compress:
        compress_type = zipfile.ZIP_STORED
    else:
        compress_type = zipfile.ZIP_DEFLATED
    zf = zipfile.ZipFile(target,"w",compression=compress_type)
    if members is None:
        def gen_members():
            for (dirpath,dirnames,filenames) in os.walk(source):
                for fn in filenames:
                    yield os.path.join(dirpath,fn)[len(source)+1:]
        members = gen_members()
    for fpath in members:
        if isinstance(fpath,zipfile.ZipInfo):
            zinfo = fpath
            fpath = os.path.join(source,zinfo.filename)
        else:
            if get_zipinfo:
                zinfo = get_zipinfo(fpath)
            else:
                zinfo = None
            fpath = os.path.join(source,fpath)
        if zinfo is None:
            zf.write(fpath,fpath[len(source)+1:])
        elif isinstance(zinfo,basestring):
            zf.write(fpath,zinfo)
        else:
            with open(fpath,"rb") as f:
                zf.writestr(zinfo,f.read())
    zf.close()


_CACHED_PLATFORM = None
def get_platform():
    """Get the platform identifier for the current platform.

    This is similar to the function distutils.util.get_platform(); it returns
    a string identifying the types of platform on which binaries built on this
    machine can reasonably be expected to run.

    Unlike distutils.util.get_platform(), the value returned by this function
    is guaranteed not to contain any periods. This makes it much easier to
    parse out of filenames.
    """
    global _CACHED_PLATFORM
    if _CACHED_PLATFORM is None:
        _CACHED_PLATFORM = distutils.util.get_platform().replace(".","_")
    return _CACHED_PLATFORM


def is_core_dependency(filenm):
    """Check whether than named file is a core python dependency.

    If it is, then it's required for any frozen program to run (even the
    bootstrapper).  Currently this includes only the python DLL and the
    MSVCRT private assembly.
    """
    if re.match("^(lib)?python\\d[\\d\\.]*\\.[a-z\d\\.]*$",filenm):
        return True
    if filenm.startswith("Microsoft.") and filenm.endswith(".CRT"):
        return True
    if filenm.startswith("Python"):
        return True
    return False


def copy_ownership_info(src,dst,cur="",default=None):
    """Copy file ownership from src onto dst, as much as possible."""
    # TODO: how on win32?
    source = os.path.join(src,cur)
    target = os.path.join(dst,cur)
    if default is None:
        default = os.stat(src)
    if os.path.exists(source):
        info = os.stat(source)
    else:
        info = default
    if sys.platform != "win32":
        os.chown(target,info.st_uid,info.st_gid)
    if os.path.isdir(target):
        for nm in os.listdir(target):
            copy_ownership_info(src,dst,os.path.join(cur,nm),default)



def get_backup_filename(filename):
    """Get the name to which a backup of the given file can be written.

    This will typically the filename with ".old" inserted at an appropriate
    location.  We try to preserve the file extension where possible.
    """
    parent = os.path.dirname(filename)
    parts = os.path.basename(filename).split(".")
    parts.insert(-1,"old")
    backname = os.path.join(parent,".".join(parts))
    while os.path.exists(backname):
        parts.insert(-1,"old")
        backname = os.path.join(parent,".".join(parts))
    return backname


def is_locked_version_dir(vdir):
    """Check whether the given version dir is locked."""
    if sys.platform == "win32":
        lockfile = os.path.join(vdir,ESKY_CONTROL_DIR,"bootstrap-manifest.txt")
        try:
            os.rename(lockfile,lockfile)
        except EnvironmentError:
            return True
        else:
            return False
    else:
        lockfile = os.path.join(vdir,ESKY_CONTROL_DIR,"lockfile.txt")
        f = open(lockfile,"r")
        try:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except EnvironmentError, e:
            if e.errno not in (errno.EACCES,errno.EAGAIN,):
                raise
            return True
        else:
            return False
        finally:
            f.close()


def really_rename(source,target):
    """Like os.rename, but try to work around some win32 wierdness.

    Every so often windows likes to throw a spurious error about not being
    able to rename something; if we sleep for a brief period and try
    again it seems to get over it.
    """
    if sys.platform != "win32":
        os.rename(source,target)
    else:
        for _ in xrange(10):
            try:
                os.rename(source,target)
            except WindowsError, e:
                if e.errno not in (errno.EACCES,):
                    raise
                time.sleep(0.01)
            else:
                break
        else:
            os.rename(source,target)


def really_rmtree(path):
    """Like shutil.rmtree, but try to work around some win32 wierdness.

    Every so often windows likes to throw a spurious error about not being
    able to remove a directory - like claiming it still contains files after
    we just deleted all the files in the directory.  If we sleep for a brief
    period and try again it seems to get over it.
    """
    if sys.platform != "win32":
        shutil.rmtree(path)
    else:
        #  If it's going to error out legitimately, let it do so.
        if not os.path.exists(path):
            shutil.rmtree(path)
        #  This is a little retry loop that catches troublesome errors.
        for _ in xrange(10):
            try:
                shutil.rmtree(path)
            except WindowsError, e:
                if e.errno in (errno.ENOTEMPTY,errno.EACCES,):
                    time.sleep(0.01)
                elif e.errno == errno.ENOENT:
                    if not os.path.exists(path):
                        return
                    time.sleep(0.01)
                else:
                    raise
            else:
                break
        else:
            shutil.rmtree(path)



########NEW FILE########
__FILENAME__ = winres
#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.winres:  utilities for working with windows EXE resources.

This module provides some wrapper functions for accessing resources in win32
PE-format executable files.  It requires ctypes and (obviously) only works
under Windows.

"""

from __future__ import with_statement

import os
import sys
import tempfile
import ctypes
import ctypes.wintypes
from ctypes import windll, c_char, c_void_p, POINTER, byref, sizeof
from ctypes.wintypes import HMODULE, DWORD

if sys.platform != "win32":
    raise ImportError("winres is only avilable on Windows platforms")

from esky.util import pairwise, files_differ


LOAD_LIBRARY_AS_DATAFILE = 0x00000002
RT_ICON = 3
RT_GROUP_ICON = 14
RT_VERSION = 16
RT_MANIFEST = 24


k32 = windll.kernel32

# Ensure that the first parameter is treated as a handle, not an int. They
# are the same size on Win32, and typically small enough values on Win64 that
# they translate okay, but if a handle value is too large there will be a
# overflow exception.  So this will tell ctypes to convert the value correctly.
k32.GetModuleFileNameA.argtypes = [HMODULE, c_void_p, DWORD]

# AFAIK 1033 is some sort of "default" language.
# Is it (LANG_NEUTRAL,SUBLANG_NEUTRAL)?
_DEFAULT_RESLANG = 1033


try:
    EnumProcessModules = k32.EnumProcessModules
except AttributeError:
    EnumProcessModules = windll.psapi.EnumProcessModules

def get_loaded_modules():
    """Iterator over the currently-loaded modules of the current process.

    This is a skinny little wrapper around the EnumProcessModules and 
    GetModuleFileName functions.
    """
    sz = -1
    msz = sizeof(ctypes.wintypes.HMODULE)
    needed = ctypes.c_int(0)
    proc = k32.GetCurrentProcess()
    try:
        while needed.value > sz:
            sz = needed.value + 32
            buf = (ctypes.wintypes.HMODULE * sz)()
            if not EnumProcessModules(proc,byref(buf),sz*msz,byref(needed)):
                raise ctypes.WinError()
        nmbuf = ctypes.create_string_buffer(300)
        i = 0
        while i < needed.value / msz:
            hmod = buf[i]
            i += 1
            if not k32.GetModuleFileNameA(hmod, byref(nmbuf), 300):
                raise ctypes.WinError()
            yield nmbuf.value
    finally:
        k32.CloseHandle(proc)
 


def find_resource(filename_or_handle,res_type,res_id,res_lang=None):
    """Locate a resource inside the given file or module handle.

    This function returns a tuple (start,end) giving the location of the
    specified resource inside the given module.

    Currently this relies on the kernel32.LockResource function returning
    a pointer based at the module handle; ideally we'd do our own parsing.
    """ 
    tdir = None
    free_library = False
    try:
        if res_lang is None:
            res_lang = _DEFAULT_RESLANG
        if isinstance(filename_or_handle,basestring):
            filename = filename_or_handle
            if not isinstance(filename,unicode):
                filename = filename.decode(sys.getfilesystemencoding())
            #  See if we already have that file loaded as a module.
            #  In this case it won't be in memory as one big block and we
            #  can't calculate resource position by pointer arithmetic.
            #  Solution: copy it to a tempfile and load that.
            for nm in get_loaded_modules():
                if os.path.abspath(filename) == nm:
                    ext = filename[filename.rfind("."):]
                    tdir = tempfile.mkdtemp()
                    with open(filename,"rb") as inF:
                        filename = os.path.join(tdir,"tempmodule"+ext)
                        with open(filename,"wb") as outF:
                            outF.write(inF.read())
                    break
            l_handle = k32.LoadLibraryExW(filename,None,LOAD_LIBRARY_AS_DATAFILE)
            if not l_handle:
                raise ctypes.WinError()
            free_library = True
        else:
            l_handle = filename_or_handle
        r_handle = k32.FindResourceExW(l_handle,res_type,res_id,res_lang)
        if not r_handle:
            raise ctypes.WinError()
        r_size = k32.SizeofResource(l_handle,r_handle)
        if not r_size:
            raise ctypes.WinError()
        r_info = k32.LoadResource(l_handle,r_handle)
        if not r_info:
            raise ctypes.WinError()
        r_ptr = k32.LockResource(r_info)
        if not r_ptr:
            raise ctypes.WinError()
        return (r_ptr - l_handle + 1,r_ptr - l_handle + r_size + 1)
    finally:
        if free_library:
            k32.FreeLibrary(l_handle)
        if tdir is not None:
            for nm in os.listdir(tdir):
                os.unlink(os.path.join(tdir,nm))
            os.rmdir(tdir)
    

def load_resource(filename_or_handle,res_type,res_id,res_lang=_DEFAULT_RESLANG):
    """Load a resource from the given filename or module handle.

    The "res_type" and "res_id" arguments identify the particular resource
    to be loaded, along with the "res_lang" argument if given.  The contents
    of the specified resource are returned as a string.
    """
    if isinstance(filename_or_handle,basestring):
        filename = filename_or_handle
        if not isinstance(filename,unicode):
            filename = filename.decode(sys.getfilesystemencoding())
        l_handle = k32.LoadLibraryExW(filename,None,LOAD_LIBRARY_AS_DATAFILE)
        if not l_handle:
            raise ctypes.WinError()
        free_library = True
    else:
        l_handle = filename_or_handle
        free_library = False
    try:
        r_handle = k32.FindResourceExW(l_handle,res_type,res_id,res_lang)
        if not r_handle:
            raise ctypes.WinError()
        r_size = k32.SizeofResource(l_handle,r_handle)
        if not r_size:
            raise ctypes.WinError()
        r_info = k32.LoadResource(l_handle,r_handle)
        if not r_info:
            raise ctypes.WinError()
        r_ptr = k32.LockResource(r_info)
        if not r_ptr:
            raise ctypes.WinError()
        resource = ctypes.cast(r_ptr,POINTER(c_char))[0:r_size]
        return resource
    finally:
        if free_library:
            k32.FreeLibrary(l_handle)


def add_resource(filename,resource,res_type,res_id,res_lang=_DEFAULT_RESLANG):
    """Add a resource to the given filename.

    The "res_type" and "res_id" arguments identify the particular resource
    to be added, along with the "res_lang" argument if given.  The contents
    of the specified resource must be provided as a string.
    """
    if not isinstance(filename,unicode):
        filename = filename.decode(sys.getfilesystemencoding())
    l_handle = k32.BeginUpdateResourceW(filename,0)
    if not l_handle:
        raise ctypes.WinError()
    res_info = (resource,len(resource))
    if not k32.UpdateResourceW(l_handle,res_type,res_id,res_lang,*res_info):
        raise ctypes.WinError()
    if not k32.EndUpdateResourceW(l_handle,0):
        raise ctypes.WinError()
 

def get_app_manifest(filename_or_handle=None):
    """Get the default application manifest for frozen Python apps.

    The manifest is a special XML file that must be embedded in the executable
    in order for it to correctly load SxS assemblies.

    Called without arguments, this function reads the manifest from the
    current python executable.  Pass the filename or handle of a different
    executable if you want a different manifest.
    """
    return load_resource(filename_or_handle,RT_MANIFEST,1)


COMMON_SAFE_RESOURCES = ((RT_VERSION,1,0),(RT_ICON,0,0),(RT_ICON,1,0),
                         (RT_ICON,2,0),(RT_GROUP_ICON,1,0),)
                         

def copy_safe_resources(source,target):
    """Copy "safe" exe resources from one executable to another.

    This is useful if you want to make one executable look the same as another,
    by copying version info, icon resources, etc.
    """
    for (rtype,rid,rlang) in COMMON_SAFE_RESOURCES:
        try:
            res = load_resource(source,rtype,rid,rlang)
        except WindowsError:
            pass
        else:
            add_resource(target,res,rtype,rid,rlang)


def is_safe_to_overwrite(source,target):
    """Check whether it is safe to overwrite target exe with source exe.

    This function checks whether two exe files 'source' and 'target' differ
    only in the contents of certain non-critical resource segments.  If so,
    then overwriting the target file with the contents of the source file
    should be safe even in the face of system crashes or power outages; the
    worst outcome would be a corrupted resource such as an icon.
    """
    if not source.endswith(".exe") or not target.endswith(".exe"):
        return False
    #  Check if they're the same size
    s_sz = os.stat(source).st_size
    t_sz = os.stat(target).st_size
    if s_sz != t_sz:
        return False
    #  Find each safe resource, and confirm that either (1) it's in the same
    #  location in both executables, or (2) it's missing in both executables.
    locs = []
    for (rtype,rid,rlang) in COMMON_SAFE_RESOURCES:
        try:
            s_loc = find_resource(source,rtype,rid,rlang)
        except WindowsError:
            s_loc = None
        try: 
            t_loc = find_resource(target,rtype,rid,rlang)
        except WindowsError:
            t_loc = None
        if s_loc != t_loc:
            return False
        if s_loc is not None:
            locs.append(s_loc)
    #  Confirm that no other portions of the file have changed
    if locs:
        locs.extend(((0,0),(s_sz,s_sz)))
        locs.sort()
        for (_,start),(stop,_) in pairwise(locs):
            if files_differ(source,target,start,stop):
                return False
    #  Looks safe to me!
    return True



########NEW FILE########
__FILENAME__ = example

print "HELLO WORLD"


########NEW FILE########
__FILENAME__ = example


print ("HELLO WORLD")


########NEW FILE########
__FILENAME__ = example

import sys
import esky

if getattr(sys,"frozen",False):
    app = esky.Esky(sys.executable,"https://example-app.com/downloads/")
    try:
        app.auto_update()
    except Exception, e:
        print "ERROR UPDATING APP:", e

print "HELLO AGAIN WORLD"


########NEW FILE########
__FILENAME__ = example

import sys
import esky

if getattr(sys,"frozen",False):
    app = esky.Esky(sys.executable,"https://example-app.com/downloads/")
    try:
        app.auto_update()
    except Exception, e:
        print "ERROR UPDATING APP:", e

print "HELLO AGAIN WORLD"


########NEW FILE########
__FILENAME__ = example
import sys
import os
import esky

if getattr(sys,"frozen",False):
    app = esky.Esky(sys.executable,"https://example-app.com/downloads/")
    print "You are running: %s" % app.active_version
    try:
        if(app.find_update() != None):
            app.auto_update()
            appexe = esky.util.appexe_from_executable(sys.executable)
            os.execv(appexe,[appexe] + sys.argv[1:])
    except Exception, e:
        print "ERROR UPDATING APP:", e
    app.cleanup()

print "HELLO WORLD"


########NEW FILE########
