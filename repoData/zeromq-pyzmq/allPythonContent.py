__FILENAME__ = bundle
"""utilities for fetching build dependencies."""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#
#  This bundling code is largely adapted from pyzmq-static's get.sh by
#  Brandon Craig-Rhodes, which is itself BSD licensed.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import os
import shutil
import stat
import sys
import tarfile
from glob import glob
from subprocess import Popen, PIPE

try:
    # py2
    from urllib2 import urlopen
except ImportError:
    # py3
    from urllib.request import urlopen

from .msg import fatal, debug, info, warn

pjoin = os.path.join

#-----------------------------------------------------------------------------
# Constants
#-----------------------------------------------------------------------------

bundled_version = (4,0,4)
libzmq = "zeromq-%i.%i.%i.tar.gz" % (bundled_version)
libzmq_url = "http://download.zeromq.org/" + libzmq

libsodium_version = (0,4,5)
libsodium = "libsodium-%i.%i.%i.tar.gz" % (libsodium_version)
libsodium_url = "https://github.com/jedisct1/libsodium/releases/download/%i.%i.%i/" % libsodium_version + libsodium

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)

#-----------------------------------------------------------------------------
# Utilities
#-----------------------------------------------------------------------------


def untgz(archive):
    return archive.replace('.tar.gz', '')

def localpath(*args):
    """construct an absolute path from a list relative to the root pyzmq directory"""
    plist = [ROOT] + list(args)
    return os.path.abspath(pjoin(*plist))

def fetch_archive(savedir, url, fname, force=False):
    """download an archive to a specific location"""
    dest = pjoin(savedir, fname)
    if os.path.exists(dest) and not force:
        info("already have %s" % fname)
        return dest
    info("fetching %s into %s" % (url, savedir))
    if not os.path.exists(savedir):
        os.makedirs(savedir)
    req = urlopen(url)
    with open(dest, 'wb') as f:
        f.write(req.read())
    return dest

#-----------------------------------------------------------------------------
# libsodium
#-----------------------------------------------------------------------------

def fetch_libsodium(savedir):
    """download and extract libsodium"""
    dest = pjoin(savedir, 'libsodium')
    if os.path.exists(dest):
        info("already have %s" % dest)
        return
    fname = fetch_archive(savedir, libsodium_url, libsodium)
    tf = tarfile.open(fname)
    with_version = pjoin(savedir, tf.firstmember.path)
    tf.extractall(savedir)
    tf.close()
    # remove version suffix:
    shutil.move(with_version, dest)

def stage_libsodium_headers(libsodium_root):
    """stage configure headers for libsodium"""
    src_dir = pjoin(HERE, 'include_sodium')
    dest_dir = pjoin(libsodium_root, 'src', 'libsodium', 'include', 'sodium')
    for src in glob(pjoin(src_dir, '*.h')):
        base = os.path.basename(src)
        dest = pjoin(dest_dir, base)
        if os.path.exists(dest):
            info("already have %s" % base)
            continue
        info("staging %s to %s" % (src, dest))
        shutil.copy(src, dest)

#-----------------------------------------------------------------------------
# libzmq
#-----------------------------------------------------------------------------

def fetch_libzmq(savedir):
    """download and extract libzmq"""
    dest = pjoin(savedir, 'zeromq')
    if os.path.exists(dest):
        info("already have %s" % dest)
        return
    fname = fetch_archive(savedir, libzmq_url, libzmq)
    tf = tarfile.open(fname)
    with_version = pjoin(savedir, tf.firstmember.path)
    tf.extractall(savedir)
    tf.close()
    # remove version suffix:
    shutil.move(with_version, dest)

def stage_platform_hpp(zmqroot):
    """stage platform.hpp into libzmq sources
    
    Tries ./configure first (except on Windows),
    then falls back on included platform.hpp previously generated.
    """
    
    platform_hpp = pjoin(zmqroot, 'src', 'platform.hpp')
    if os.path.exists(platform_hpp):
        info("already have platform.hpp")
        return
    if os.name == 'nt':
        # stage msvc platform header
        platform_dir = pjoin(zmqroot, 'builds', 'msvc')
    else:
        info("attempting ./configure to generate platform.hpp")
        
        p = Popen('./configure', cwd=zmqroot, shell=True,
            stdout=PIPE, stderr=PIPE,
        )
        o,e = p.communicate()
        if p.returncode:
            warn("failed to configure libzmq:\n%s" % e)
            if sys.platform == 'darwin':
                platform_dir = pjoin(HERE, 'include_darwin')
            elif sys.platform.startswith('freebsd'):
                platform_dir = pjoin(HERE, 'include_freebsd')
            elif sys.platform.startswith('linux-armv'):
                platform_dir = pjoin(HERE, 'include_linux-armv')
            else:
                platform_dir = pjoin(HERE, 'include_linux')
        else:
            return
    
    info("staging platform.hpp from: %s" % platform_dir)
    shutil.copy(pjoin(platform_dir, 'platform.hpp'), platform_hpp)


def copy_and_patch_libzmq(ZMQ, libzmq):
    """copy libzmq into source dir, and patch it if necessary.
    
    This command is necessary prior to running a bdist on Linux or OS X.
    """
    if sys.platform.startswith('win'):
        return
    # copy libzmq into zmq for bdist
    local = localpath('zmq',libzmq)
    if not ZMQ and not os.path.exists(local):
        fatal("Please specify zmq prefix via `setup.py configure --zmq=/path/to/zmq` "
        "or copy libzmq into zmq/ manually prior to running bdist.")
    try:
        # resolve real file through symlinks
        lib = os.path.realpath(pjoin(ZMQ, 'lib', libzmq))
        print ("copying %s -> %s"%(lib, local))
        shutil.copy(lib, local)
    except Exception:
        if not os.path.exists(local):
            fatal("Could not copy libzmq into zmq/, which is necessary for bdist. "
            "Please specify zmq prefix via `setup.py configure --zmq=/path/to/zmq` "
            "or copy libzmq into zmq/ manually.")
    
    if sys.platform == 'darwin':
        # chmod u+w on the lib,
        # which can be user-read-only for some reason
        mode = os.stat(local).st_mode
        os.chmod(local, mode | stat.S_IWUSR)
        # patch install_name on darwin, instead of using rpath
        cmd = ['install_name_tool', '-id', '@loader_path/../%s'%libzmq, local]
        try:
            p = Popen(cmd, stdout=PIPE,stderr=PIPE)
        except OSError:
            fatal("install_name_tool not found, cannot patch libzmq for bundling.")
        out,err = p.communicate()
        if p.returncode:
            fatal("Could not patch bundled libzmq install_name: %s"%err, p.returncode)
        

########NEW FILE########
__FILENAME__ = config
"""Config functions"""
#-----------------------------------------------------------------------------
#  Copyright (C) 2011 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq, copied and adapted from h5py.
#  h5py source used under the New BSD license
#
#  h5py: <http://code.google.com/p/h5py/>
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import sys
import os
import json

try:
    from configparser import ConfigParser
except:
    from ConfigParser import ConfigParser

pjoin = os.path.join
from .msg import debug, fatal, warn

#-----------------------------------------------------------------------------
# Utility functions (adapted from h5py: http://h5py.googlecode.com)
#-----------------------------------------------------------------------------


def load_config(name, base='conf'):
    """Load config dict from JSON"""
    fname = pjoin(base, name + '.json')
    if not os.path.exists(fname):
        return {}
    try:
        with open(fname) as f:
            cfg = json.load(f)
    except Exception as e:
        warn("Couldn't load %s: %s" % (fname, e))
        cfg = {}
    return cfg


def save_config(name, data, base='conf'):
    """Save config dict to JSON"""
    if not os.path.exists(base):
        os.mkdir(base)
    fname = pjoin(base, name+'.json')
    with open(fname, 'w') as f:
        json.dump(data, f, indent=2)


def v_str(v_tuple):
    """turn (2,0,1) into '2.0.1'."""
    return ".".join(str(x) for x in v_tuple)

def get_eargs():
    """ Look for options in environment vars """

    settings = {}

    zmq = os.environ.get("ZMQ_PREFIX", None)
    if zmq is not None:
        debug("Found environ var ZMQ_PREFIX=%s" % zmq)
        settings['zmq_prefix'] = zmq

    return settings

def cfg2dict(cfg):
    """turn a ConfigParser into a nested dict
    
    because ConfigParser objects are dumb.
    """
    d = {}
    for section in cfg.sections():
        d[section] = dict(cfg.items(section))
    return d

def get_cfg_args():
    """ Look for options in setup.cfg """

    if not os.path.exists('setup.cfg'):
        return {}
    cfg = ConfigParser()
    cfg.read('setup.cfg')
    cfg = cfg2dict(cfg)

    g = cfg.setdefault('global', {})
    # boolean keys:
    for key in ['libzmq_extension',
                'bundle_libzmq_dylib',
                'no_libzmq_extension',
                'have_sys_un_h',
                'skip_check_zmq',
                ]:
        if key in g:
            g[key] = eval(g[key])

    # globals go to top level
    cfg.update(cfg.pop('global'))
    return cfg

def config_from_prefix(prefix):
    """Get config from zmq prefix"""
    settings = {}
    if prefix.lower() in ('default', 'auto', ''):
        settings['zmq_prefix'] = ''
        settings['libzmq_extension'] = False
        settings['no_libzmq_extension'] = False
    elif prefix.lower() in ('bundled', 'extension'):
        settings['zmq_prefix'] = ''
        settings['libzmq_extension'] = True
        settings['no_libzmq_extension'] = False
    else:
        settings['zmq_prefix'] = prefix
        settings['libzmq_extension'] = False
        settings['no_libzmq_extension'] = True
    return settings

def merge(into, d):
    """merge two containers
    
    into is updated, d has priority
    """
    if isinstance(into, dict):
        for key in d.keys():
            if key not in into:
                into[key] = d[key]
            else:
                into[key] = merge(into[key], d[key])
        return into
    elif isinstance(into, list):
        return into + d
    else:
        return d

def discover_settings(conf_base=None):
    """ Discover custom settings for ZMQ path"""
    settings = {
        'zmq_prefix': '',
        'libzmq_extension': False,
        'no_libzmq_extension': False,
        'skip_check_zmq': False,
        'build_ext': {},
        'bdist_egg': {},
    }
    if sys.platform.startswith('win'):
        settings['have_sys_un_h'] = False
    
    if conf_base:
        # lowest priority
        merge(settings, load_config('config', conf_base))
    merge(settings, get_cfg_args())
    merge(settings, get_eargs())
    
    return settings

########NEW FILE########
__FILENAME__ = constants
"""
script for generating files that involve repetitive updates for zmq constants.

Run this after updating utils/constant_names

Currently generates the following files from templates:

- constant_enums.pxi
- constants.pxi
- zmq_constants.h

"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian E. Granger & Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
import sys

from . import info
pjoin = os.path.join

root = os.path.abspath(pjoin(os.path.dirname(__file__), os.path.pardir))

sys.path.insert(0, pjoin(root, 'zmq', 'utils'))
from constant_names import all_names, no_prefix

ifndef_t = """#ifndef {0}
    #define {0} (-1)
#endif
"""

def cython_enums():
    """generate `enum: ZMQ_CONST` block for constant_enums.pxi"""
    lines = []
    for name in all_names:
        if no_prefix(name):
            lines.append('enum: ZMQ_{0} "{0}"'.format(name))
        else:
            lines.append('enum: ZMQ_{0}'.format(name))
            
    return dict(ZMQ_ENUMS='\n    '.join(lines))

def ifndefs():
    """generate `#ifndef ZMQ_CONST` block for zmq_constants.h"""
    lines = []
    for name in all_names:
        if not no_prefix(name):
            name = 'ZMQ_%s' % name
        lines.append(ifndef_t.format(name))
    return dict(ZMQ_IFNDEFS='\n'.join(lines))

def constants_pyx():
    """generate CONST = ZMQ_CONST and __all__ for constants.pxi"""
    all_lines = []
    assign_lines = []
    for name in all_names:
        if name == "NULL":
            # avoid conflict with NULL in Cython
            assign_lines.append("globals()['NULL'] = ZMQ_NULL")
        else:
            assign_lines.append('{0} = ZMQ_{0}'.format(name))
        all_lines.append('  "{0}",'.format(name))
    return dict(ASSIGNMENTS='\n'.join(assign_lines), ALL='\n'.join(all_lines))

def generate_file(fname, ns_func, dest_dir="."):
    """generate a constants file from its template"""
    with open(pjoin(root, 'buildutils', 'templates', '%s' % fname), 'r') as f:
        tpl = f.read()
    out = tpl.format(**ns_func())
    dest = pjoin(dest_dir, fname)
    info("generating %s from template" % dest)
    with open(dest, 'w') as f:
        f.write(out)

def render_constants():
    """render generated constant files from templates"""
    generate_file("constant_enums.pxi", cython_enums, pjoin(root, 'zmq', 'backend', 'cython'))
    generate_file("constants.pxi", constants_pyx, pjoin(root, 'zmq', 'backend', 'cython'))
    generate_file("zmq_constants.h", ifndefs, pjoin(root, 'zmq', 'utils'))

if __name__ == '__main__':
    render_constants()

########NEW FILE########
__FILENAME__ = detect
"""Detect zmq version"""
#-----------------------------------------------------------------------------
#  Copyright (C) 2011 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq, copied and adapted from h5py.
#  h5py source used under the New BSD license
#
#  h5py: <http://code.google.com/p/h5py/>
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import shutil
import sys
import os
import logging
import platform
from distutils import ccompiler
from distutils.sysconfig import customize_compiler
from subprocess import Popen, PIPE

from .misc import customize_mingw

pjoin = os.path.join

#-----------------------------------------------------------------------------
# Utility functions (adapted from h5py: http://h5py.googlecode.com)
#-----------------------------------------------------------------------------

def test_compilation(cfile, compiler=None, **compiler_attrs):
    """Test simple compilation with given settings"""
    if compiler is None or isinstance(compiler, str):
        cc = ccompiler.new_compiler(compiler=compiler)
        customize_compiler(cc)
        if cc.compiler_type == 'mingw32':
            customize_mingw(cc)
    else:
        cc = compiler
    
    for name, val in compiler_attrs.items():
        setattr(cc, name, val)
    
    efile, ext = os.path.splitext(cfile)

    cpreargs = lpreargs = None
    if sys.platform == 'darwin':
        # use appropriate arch for compiler
        if platform.architecture()[0]=='32bit':
            if platform.processor() == 'powerpc':
                cpu = 'ppc'
            else:
                cpu = 'i386'
            cpreargs = ['-arch', cpu]
            lpreargs = ['-arch', cpu, '-undefined', 'dynamic_lookup']
        else:
            # allow for missing UB arch, since it will still work:
            lpreargs = ['-undefined', 'dynamic_lookup']
    if sys.platform == 'sunos5':
        if platform.architecture()[0]=='32bit':
            lpreargs = ['-m32']
        else: 
            lpreargs = ['-m64']
    extra = compiler_attrs.get('extra_compile_args', None)

    objs = cc.compile([cfile],extra_preargs=cpreargs, extra_postargs=extra)
    cc.link_executable(objs, efile, extra_preargs=lpreargs)
    return efile

def compile_and_run(basedir, src, compiler=None, **compiler_attrs):
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    cfile = pjoin(basedir, os.path.basename(src))
    shutil.copy(src, cfile)
    try:
        efile = test_compilation(cfile, compiler=compiler, **compiler_attrs)
        result = Popen(efile, stdout=PIPE, stderr=PIPE)
        so, se = result.communicate()
        # for py3k:
        so = so.decode()
        se = se.decode()
    finally:
        shutil.rmtree(basedir)
    
    return result.returncode, so, se
    
    
def detect_zmq(basedir, compiler=None, **compiler_attrs):
    """Compile, link & execute a test program, in empty directory `basedir`.
    
    The C compiler will be updated with any keywords given via setattr.
    
    Parameters
    ----------
    
    basedir : path
        The location where the test program will be compiled and run
    compiler : str
        The distutils compiler key (e.g. 'unix', 'msvc', or 'mingw32')
    **compiler_attrs : dict
        Any extra compiler attributes, which will be set via ``setattr(cc)``.
    
    Returns
    -------
    
    A dict of properties for zmq compilation, with the following two keys:
    
    vers : tuple
        The ZMQ version as a tuple of ints, e.g. (2,2,0)
    settings : dict
        The compiler options used to compile the test function, e.g. `include_dirs`,
        `library_dirs`, `libs`, etc.
    """
    
    cfile = pjoin(basedir, 'vers.c')
    shutil.copy(pjoin(os.path.dirname(__file__), 'vers.c'), cfile)
    
    # check if we need to link against Realtime Extensions library
    if sys.platform.startswith('linux'):
        cc = ccompiler.new_compiler(compiler=compiler)
        cc.output_dir = basedir
        if not cc.has_function('timer_create'):
            compiler_attrs['libraries'].append('rt')
            
    efile = test_compilation(cfile, compiler=compiler, **compiler_attrs)
    
    result = Popen(efile, stdout=PIPE, stderr=PIPE)
    so, se = result.communicate()
    # for py3k:
    so = so.decode()
    se = se.decode()
    if result.returncode:
        msg = "Error running version detection script:\n%s\n%s" % (so,se)
        logging.error(msg)
        raise IOError(msg)

    handlers = {'vers':  lambda val: tuple(int(v) for v in val.split('.'))}

    props = {}
    for line in (x for x in so.split('\n') if x):
        key, val = line.split(':')
        props[key] = handlers[key](val)

    return props


########NEW FILE########
__FILENAME__ = misc
"""misc build utility functions"""
#-----------------------------------------------------------------------------
#  Copyright (C) 2012 Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

def customize_mingw(cc):
    # strip -mno-cygwin from mingw32 (Python Issue #12641)
    for cmd in [cc.compiler, cc.compiler_cxx, cc.compiler_so, cc.linker_exe, cc.linker_so]:
        if '-mno-cygwin' in cmd:
            cmd.remove('-mno-cygwin')
    
    # remove problematic msvcr90
    if 'msvcr90' in cc.dll_libraries:
        cc.dll_libraries.remove('msvcr90')

__all__ = ['customize_mingw']

########NEW FILE########
__FILENAME__ = msg
"""logging"""
#-----------------------------------------------------------------------------
#  Copyright (C) 2011 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq, copied and adapted from h5py.
#  h5py source used under the New BSD license
#
#  h5py: <http://code.google.com/p/h5py/>
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from __future__ import division

import sys
import logging

#-----------------------------------------------------------------------------
# Logging (adapted from h5py: http://h5py.googlecode.com)
#-----------------------------------------------------------------------------


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stderr))

def debug(msg):
    logger.debug(msg)

def info(msg):
    logger.info(msg)

def fatal(msg, code=1):
    logger.error("Fatal: " + msg)
    exit(code)

def warn(msg):
    logger.error("Warning: " + msg)

def line(c='*', width=48):
    print(c * (width // len(c)))


########NEW FILE########
__FILENAME__ = autogen_api
#!/usr/bin/env python
"""Script to auto-generate our API docs.
"""
# stdlib imports
import os
import sys

# local imports
sys.path.append(os.path.abspath('sphinxext'))
# import sphinx_cython
from apigen import ApiDocWriter

#*****************************************************************************
if __name__ == '__main__':
    pjoin = os.path.join
    package = 'zmq'
    outdir = pjoin('source','api','generated')
    docwriter = ApiDocWriter(package,rst_extension='.rst')
    # You have to escape the . here because . is a special char for regexps.
    # You must do make clean if you change this!
    docwriter.package_skip_patterns += [
        r'\.tests$',
        r'\.backend$',
        r'\.auth$',
        r'\.eventloop\.minitornado$',
        r'\.green\.eventloop$',
        r'\.sugar$',
        r'\.devices$',
    ]

    docwriter.module_skip_patterns += [
        r'\.eventloop\.stack_context$',
        r'\.error$',
        r'\.green\..+$',
        r'\.utils\.initthreads$',
        r'\.utils\.constant_names$',
        r'\.utils\.garbage$',
        r'\.utils\.rebuffer$',
        r'\.utils\.strtypes$',
        ]
    
    # Now, generate the outputs
    docwriter.write_api_docs(outdir)
    docwriter.write_index(outdir, 'gen',
                          relative_to = pjoin('source','api')
                          )
    
    print('%d files written' % len(docwriter.written_modules))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyZMQ documentation build configuration file, created by
# sphinx-quickstart on Sat Feb 20 23:31:19 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import string

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0,os.path.abspath('../sphinxext'))

# patch autodoc to work with Cython Sources
import sphinx_cython

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
              'sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.intersphinx',
              'ipython_console_highlighting',
              'numpydoc',
              ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'PyZMQ'
copyright = u"""2013, Brian E. Granger & Min Ragan-Kelley.  
ØMQ logo © iMatix Corportation, used under the Creative Commons Attribution-Share Alike 3.0 License.  
Python logo ™ of the Python Software Foundation, used by Min RK with permission from the Foundation"""

intersphinx_mapping = {'python': ('http://docs.python.org/', None)}
# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

import zmq

# The short X.Y version.
version = zmq.__version__.split('-')[0]
# The full version, including alpha/beta/rc tags.
release = zmq.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = 'zeromq.ico'

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyZMQdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'PyZMQ.tex', u'PyZMQ Documentation',
   u'Brian E. Granger \\and Min Ragan-Kelley', 'manual'),
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

########NEW FILE########
__FILENAME__ = apigen
"""Attempt to generate templates for module reference with Sphinx

XXX - we exclude extension modules

To include extension modules, first identify them as valid in the
``_uri2path`` method, then handle them in the ``_parse_module`` script.

We get functions and classes by parsing the text of .py files.
Alternatively we could import the modules for discovery, and we'd have
to do that for extension modules.  This would involve changing the
``_parse_module`` method to work via import and introspection, and
might involve changing ``discover_modules`` (which determines which
files are modules, and therefore which module URIs will be passed to
``_parse_module``).

NOTE: this is a modified version of a script originally shipped with the
PyMVPA project, which we've adapted for NIPY use.  PyMVPA is an MIT-licensed
project."""

# Stdlib imports
import os
import re

# Functions and classes
class ApiDocWriter(object):
    ''' Class for automatic detection and parsing of API docs
    to Sphinx-parsable reST format'''

    # only separating first two levels
    rst_section_levels = ['*', '=', '-', '~', '^']

    def __init__(self,
                 package_name,
                 rst_extension='.rst',
                 package_skip_patterns=None,
                 module_skip_patterns=None,
                 ):
        ''' Initialize package for parsing

        Parameters
        ----------
        package_name : string
            Name of the top-level package.  *package_name* must be the
            name of an importable package
        rst_extension : string, optional
            Extension for reST files, default '.rst'
        package_skip_patterns : None or sequence of {strings, regexps}
            Sequence of strings giving URIs of packages to be excluded
            Operates on the package path, starting at (including) the
            first dot in the package path, after *package_name* - so,
            if *package_name* is ``sphinx``, then ``sphinx.util`` will
            result in ``.util`` being passed for earching by these
            regexps.  If is None, gives default. Default is:
            ['\.tests$']
        module_skip_patterns : None or sequence
            Sequence of strings giving URIs of modules to be excluded
            Operates on the module name including preceding URI path,
            back to the first dot after *package_name*.  For example
            ``sphinx.util.console`` results in the string to search of
            ``.util.console``
            If is None, gives default. Default is:
            ['\.setup$', '\._']
        '''
        if package_skip_patterns is None:
            package_skip_patterns = ['\\.tests$']
        if module_skip_patterns is None:
            module_skip_patterns = ['\\.setup$', '\\._']
        self.package_name = package_name
        self.rst_extension = rst_extension
        self.package_skip_patterns = package_skip_patterns
        self.module_skip_patterns = module_skip_patterns

    def get_package_name(self):
        return self._package_name

    def set_package_name(self, package_name):
        ''' Set package_name

        >>> docwriter = ApiDocWriter('sphinx')
        >>> import sphinx
        >>> docwriter.root_path == sphinx.__path__[0]
        True
        >>> docwriter.package_name = 'docutils'
        >>> import docutils
        >>> docwriter.root_path == docutils.__path__[0]
        True
        '''
        # It's also possible to imagine caching the module parsing here
        self._package_name = package_name
        self.root_module = __import__(package_name)
        self.root_path = self.root_module.__path__[0]
        self.written_modules = None

    package_name = property(get_package_name, set_package_name, None,
                            'get/set package_name')

    def _get_object_name(self, line):
        ''' Get second token in line
        >>> docwriter = ApiDocWriter('sphinx')
        >>> docwriter._get_object_name("  def func():  ")
        'func'
        >>> docwriter._get_object_name("  class Klass(object):  ")
        'Klass'
        >>> docwriter._get_object_name("  class Klass:  ")
        'Klass'
        '''
        if line.startswith('cdef'):
            line = line.split(None,1)[1]
        name = line.split()[1].split('(')[0].strip()
        # in case we have classes which are not derived from object
        # ie. old style classes
        return name.rstrip(':')

    def _uri2path(self, uri):
        ''' Convert uri to absolute filepath

        Parameters
        ----------
        uri : string
            URI of python module to return path for

        Returns
        -------
        path : None or string
            Returns None if there is no valid path for this URI
            Otherwise returns absolute file system path for URI

        Examples
        --------
        >>> docwriter = ApiDocWriter('sphinx')
        >>> import sphinx
        >>> modpath = sphinx.__path__[0]
        >>> res = docwriter._uri2path('sphinx.builder')
        >>> res == os.path.join(modpath, 'builder.py')
        True
        >>> res = docwriter._uri2path('sphinx')
        >>> res == os.path.join(modpath, '__init__.py')
        True
        >>> docwriter._uri2path('sphinx.does_not_exist')

        '''
        if uri == self.package_name:
            return os.path.join(self.root_path, '__init__.py')
        path = uri.replace('.', os.path.sep)
        path = path.replace(self.package_name + os.path.sep, '')
        path = os.path.join(self.root_path, path)
        # XXX maybe check for extensions as well?
        if os.path.exists(path + '.py'): # file
            path += '.py'
        elif os.path.exists(path + '.pyx'): # file
            path += '.pyx'
        elif os.path.exists(os.path.join(path, '__init__.py')):
            path = os.path.join(path, '__init__.py')
        else:
            return None
        return path

    def _path2uri(self, dirpath):
        ''' Convert directory path to uri '''
        relpath = dirpath.replace(self.root_path, self.package_name)
        if relpath.startswith(os.path.sep):
            relpath = relpath[1:]
        return relpath.replace(os.path.sep, '.')

    def _parse_module(self, uri):
        ''' Parse module defined in *uri* '''
        filename = self._uri2path(uri)
        if filename is None:
            # nothing that we could handle here.
            return ([],[])
        f = open(filename, 'rt')
        functions, classes = self._parse_lines(f)
        f.close()
        return functions, classes
    
    def _parse_lines(self, linesource):
        ''' Parse lines of text for functions and classes '''
        functions = []
        classes = []
        for line in linesource:
            if line.startswith('def ') and line.count('('):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    functions.append(name)
            elif line.startswith('class '):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    classes.append(name)
            elif line.startswith('cpdef ') and line.count('('):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    functions.append(name)
            elif line.startswith('cdef class '):
                # exclude private stuff
                name = self._get_object_name(line)
                if not name.startswith('_'):
                    classes.append(name)
            else:
                pass
        functions.sort()
        classes.sort()
        return functions, classes

    def generate_api_doc(self, uri):
        '''Make autodoc documentation template string for a module

        Parameters
        ----------
        uri : string
            python location of module - e.g 'sphinx.builder'

        Returns
        -------
        S : string
            Contents of API doc
        '''
        # get the names of all classes and functions
        functions, classes = self._parse_module(uri)
        if not len(functions) and not len(classes):
            print 'WARNING: Empty -',uri  # dbg
            return ''

        # Make a shorter version of the uri that omits the package name for
        # titles 
        uri_short = re.sub(r'^%s\.' % self.package_name,'',uri)
        
        ad = '.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n'

        chap_title = uri_short
        ad += (chap_title+'\n'+ self.rst_section_levels[1] * len(chap_title)
               + '\n\n')

        # Set the chapter title to read 'module' for all modules except for the
        # main packages
        if '.' in uri:
            title = 'Module: :mod:`' + uri_short + '`'
        else:
            title = ':mod:`' + uri_short + '`'
        ad += title + '\n' + self.rst_section_levels[2] * len(title)

        # if len(classes):
        #     ad += '\nInheritance diagram for ``%s``:\n\n' % uri
        #     ad += '.. inheritance-diagram:: %s \n' % uri
        #     ad += '   :parts: 3\n'

        ad += '\n.. automodule:: ' + uri + '\n'
        ad += '\n.. currentmodule:: ' + uri + '\n'
        multi_class = len(classes) > 1
        multi_fx = len(functions) > 1
        if multi_class:
            ad += '\n' + 'Classes' + '\n' + \
                  self.rst_section_levels[2] * 7 + '\n'
        elif len(classes) and multi_fx:
            ad += '\n' + 'Class' + '\n' + \
                  self.rst_section_levels[2] * 5 + '\n'
        for c in classes:
            ad += '\n:class:`' + c + '`\n' \
                  + self.rst_section_levels[multi_class + 2 ] * \
                  (len(c)+9) + '\n\n'
            ad += '\n.. autoclass:: ' + c + '\n'
            # must NOT exclude from index to keep cross-refs working
            ad += '  :members:\n' \
                  '  :undoc-members:\n' \
                  '  :inherited-members:\n' \
                  '\n' 
                  # skip class.__init__()
                  # '  .. automethod:: __init__\n'
        if multi_fx:
            ad += '\n' + 'Functions' + '\n' + \
                  self.rst_section_levels[2] * 9 + '\n\n'
        elif len(functions) and multi_class:
            ad += '\n' + 'Function' + '\n' + \
                  self.rst_section_levels[2] * 8 + '\n\n'
        for f in functions:
            # must NOT exclude from index to keep cross-refs working
            ad += '\n.. autofunction:: ' + uri + '.' + f + '\n\n'
        return ad

    def _survives_exclude(self, matchstr, match_type):
        ''' Returns True if *matchstr* does not match patterns

        ``self.package_name`` removed from front of string if present

        Examples
        --------
        >>> dw = ApiDocWriter('sphinx')
        >>> dw._survives_exclude('sphinx.okpkg', 'package')
        True
        >>> dw.package_skip_patterns.append('^\\.badpkg$')
        >>> dw._survives_exclude('sphinx.badpkg', 'package')
        False
        >>> dw._survives_exclude('sphinx.badpkg', 'module')
        True
        >>> dw._survives_exclude('sphinx.badmod', 'module')
        True
        >>> dw.module_skip_patterns.append('^\\.badmod$')
        >>> dw._survives_exclude('sphinx.badmod', 'module')
        False
        '''
        if match_type == 'module':
            patterns = self.module_skip_patterns
        elif match_type == 'package':
            patterns = self.package_skip_patterns
        else:
            raise ValueError('Cannot interpret match type "%s"' 
                             % match_type)
        # Match to URI without package name
        L = len(self.package_name)
        if matchstr[:L] == self.package_name:
            matchstr = matchstr[L:]
        for pat in patterns:
            try:
                pat.search
            except AttributeError:
                pat = re.compile(pat)
            if pat.search(matchstr):
                return False
        return True

    def discover_modules(self):
        ''' Return module sequence discovered from ``self.package_name`` 


        Parameters
        ----------
        None

        Returns
        -------
        mods : sequence
            Sequence of module names within ``self.package_name``

        Examples
        --------
        >>> dw = ApiDocWriter('sphinx')
        >>> mods = dw.discover_modules()
        >>> 'sphinx.util' in mods
        True
        >>> dw.package_skip_patterns.append('\.util$')
        >>> 'sphinx.util' in dw.discover_modules()
        False
        >>> 
        '''
        modules = [self.package_name]
        # raw directory parsing
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Check directory names for packages
            root_uri = self._path2uri(os.path.join(self.root_path,
                                                   dirpath))
            for dirname in dirnames[:]: # copy list - we modify inplace
                package_uri = '.'.join((root_uri, dirname))
                if (self._uri2path(package_uri) and
                    self._survives_exclude(package_uri, 'package')):
                    modules.append(package_uri)
                else:
                    dirnames.remove(dirname)
            # Check filenames for modules
            for filename in filenames:
                module_name = filename[:-3]
                module_uri = '.'.join((root_uri, module_name))
                if (self._uri2path(module_uri) and
                    self._survives_exclude(module_uri, 'module')):
                    modules.append(module_uri)
        return sorted(modules)
    
    def write_modules_api(self, modules,outdir):
        # write the list
        written_modules = []
        for m in modules:
            api_str = self.generate_api_doc(m)
            if not api_str:
                continue
            # write out to file
            outfile = os.path.join(outdir,
                                   m + self.rst_extension)
            fileobj = open(outfile, 'wt')
            fileobj.write(api_str)
            fileobj.close()
            written_modules.append(m)
        self.written_modules = written_modules

    def write_api_docs(self, outdir):
        """Generate API reST files.

        Parameters
        ----------
        outdir : string
            Directory name in which to store files
            We create automatic filenames for each module
            
        Returns
        -------
        None

        Notes
        -----
        Sets self.written_modules to list of written modules
        """
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        # compose list of modules
        modules = self.discover_modules()
        self.write_modules_api(modules,outdir)
        
    def write_index(self, outdir, froot='gen', relative_to=None):
        """Make a reST API index file from written files

        Parameters
        ----------
        path : string
            Filename to write index to
        outdir : string
            Directory to which to write generated index file
        froot : string, optional
            root (filename without extension) of filename to write to
            Defaults to 'gen'.  We add ``self.rst_extension``.
        relative_to : string
            path to which written filenames are relative.  This
            component of the written file path will be removed from
            outdir, in the generated index.  Default is None, meaning,
            leave path as it is.
        """
        if self.written_modules is None:
            raise ValueError('No modules written')
        # Get full filename path
        path = os.path.join(outdir, froot+self.rst_extension)
        # Path written into index is relative to rootpath
        if relative_to is not None:
            relpath = outdir.replace(relative_to + os.path.sep, '')
        else:
            relpath = outdir
        idx = open(path,'wt')
        w = idx.write
        w('.. AUTO-GENERATED FILE -- DO NOT EDIT!\n\n')
        w('.. toctree::\n\n')
        for f in self.written_modules:
            w('   %s\n' % os.path.join(relpath,f))
        idx.close()

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
4
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
    def __init__(self,docstring):
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
            if section in ('Parameters', 'Attributes', 'Methods',
                           'Returns', 'Raises', 'Warns'):
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
        for param_list in ('Parameters','Returns','Raises'):
            out += self._str_param_list(param_list)
        out += self._str_section('Warnings')
        out += self._str_see_also(func_role)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
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
    def __init__(self, func, role='func', doc=None):
        self._f = func
        self._role = role # e.g. "func" or "meth"
        if doc is None:
            doc = inspect.getdoc(func) or ''
        try:
            NumpyDocString.__init__(self, doc)
        except ValueError, e:
            print '*'*78
            print "ERROR: '%s' while parsing `%s`" % (e, self._f)
            print '*'*78
            #print "Docstring follows:"
            #print doclines
            #print '='*78

        if not self['Signature']:
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
    def __init__(self,cls,modulename='',func_doc=FunctionDoc,doc=None):
        if not inspect.isclass(cls):
            raise ValueError("Initialise using a class. Got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename
        self._name = cls.__name__
        self._func_doc = func_doc

        if doc is None:
            doc = pydoc.getdoc(cls)

        NumpyDocString.__init__(self, doc)

    @property
    def methods(self):
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and callable(func)]

    def __str__(self):
        out = ''
        out += super(ClassDoc, self).__str__()
        out += "\n\n"

        #for m in self.methods:
        #    print "Parsing `%s`" % m
        #    out += str(self._func_doc(getattr(self._cls,m), 'meth')) + '\n\n'
        #    out += '.. index::\n   single: %s; %s\n\n' % (self._name, m)

        return out



########NEW FILE########
__FILENAME__ = docscrape_sphinx
import re, inspect, textwrap, pydoc
from docscrape import NumpyDocString, FunctionDoc, ClassDoc

class SphinxDocString(NumpyDocString):
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
        return out

    def __str__(self, indent=0, func_role="obj"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Attributes', 'Methods',
                           'Returns','Raises'):
            out += self._str_param_list(param_list)
        out += self._str_warnings()
        out += self._str_see_also(func_role)
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_section('Examples')
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class SphinxFunctionDoc(SphinxDocString, FunctionDoc):
    pass

class SphinxClassDoc(SphinxDocString, ClassDoc):
    pass

def get_doc_object(obj, what=None, doc=None):
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
        return SphinxClassDoc(obj, '', func_doc=SphinxFunctionDoc, doc=doc)
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, '', doc=doc)
    else:
        if doc is None:
            doc = pydoc.getdoc(obj)
        return SphinxDocString(doc)


########NEW FILE########
__FILENAME__ = inheritance_diagram
"""
Defines a docutils directive for inserting inheritance diagrams.

Provide the directive with one or more classes or modules (separated
by whitespace).  For modules, all of the classes in that module will
be used.

Example::

   Given the following classes:

   class A: pass
   class B(A): pass
   class C(A): pass
   class D(B, C): pass
   class E(B): pass

   .. inheritance-diagram: D E

   Produces a graph like the following:

               A
              / \
             B   C
            / \ /
           E   D

The graph is inserted as a PNG+image map into HTML and a PDF in
LaTeX.
"""

import inspect
import os
import re
import subprocess
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from docutils.nodes import Body, Element
from docutils.parsers.rst import directives
from sphinx.roles import xfileref_role

def my_import(name):
    """Module importer - taken from the python documentation.

    This function allows importing names with dots in them."""
    
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

class DotException(Exception):
    pass

class InheritanceGraph(object):
    """
    Given a list of classes, determines the set of classes that
    they inherit from all the way to the root "object", and then
    is able to generate a graphviz dot graph from them.
    """
    def __init__(self, class_names, show_builtins=False):
        """
        *class_names* is a list of child classes to show bases from.

        If *show_builtins* is True, then Python builtins will be shown
        in the graph.
        """
        self.class_names = class_names
        self.classes = self._import_classes(class_names)
        self.all_classes = self._all_classes(self.classes)
        if len(self.all_classes) == 0:
            raise ValueError("No classes found for inheritance diagram")
        self.show_builtins = show_builtins

    py_sig_re = re.compile(r'''^([\w.]*\.)?    # class names
                           (\w+)  \s* $        # optionally arguments
                           ''', re.VERBOSE)

    def _import_class_or_module(self, name):
        """
        Import a class using its fully-qualified *name*.
        """
        try:
            path, base = self.py_sig_re.match(name).groups()
        except:
            raise ValueError(
                "Invalid class or module '%s' specified for inheritance diagram" % name)
        fullname = (path or '') + base
        path = (path and path.rstrip('.'))
        if not path:
            path = base
        try:
            module = __import__(path, None, None, [])
            # We must do an import of the fully qualified name.  Otherwise if a
            # subpackage 'a.b' is requested where 'import a' does NOT provide
            # 'a.b' automatically, then 'a.b' will not be found below.  This
            # second call will force the equivalent of 'import a.b' to happen
            # after the top-level import above.
            my_import(fullname)
            
        except ImportError:
            raise ValueError(
                "Could not import class or module '%s' specified for inheritance diagram" % name)

        try:
            todoc = module
            for comp in fullname.split('.')[1:]:
                todoc = getattr(todoc, comp)
        except AttributeError:
            raise ValueError(
                "Could not find class or module '%s' specified for inheritance diagram" % name)

        # If a class, just return it
        if inspect.isclass(todoc):
            return [todoc]
        elif inspect.ismodule(todoc):
            classes = []
            for cls in todoc.__dict__.values():
                if inspect.isclass(cls) and cls.__module__ == todoc.__name__:
                    classes.append(cls)
            return classes
        raise ValueError(
            "'%s' does not resolve to a class or module" % name)

    def _import_classes(self, class_names):
        """
        Import a list of classes.
        """
        classes = []
        for name in class_names:
            classes.extend(self._import_class_or_module(name))
        return classes

    def _all_classes(self, classes):
        """
        Return a list of all classes that are ancestors of *classes*.
        """
        all_classes = {}

        def recurse(cls):
            all_classes[cls] = None
            for c in cls.__bases__:
                if c not in all_classes:
                    recurse(c)

        for cls in classes:
            recurse(cls)

        return all_classes.keys()

    def class_name(self, cls, parts=0):
        """
        Given a class object, return a fully-qualified name.  This
        works for things I've tested in matplotlib so far, but may not
        be completely general.
        """
        module = cls.__module__
        if module == '__builtin__':
            fullname = cls.__name__
        else:
            fullname = "%s.%s" % (module, cls.__name__)
        if parts == 0:
            return fullname
        name_parts = fullname.split('.')
        return '.'.join(name_parts[-parts:])

    def get_all_class_names(self):
        """
        Get all of the class names involved in the graph.
        """
        return [self.class_name(x) for x in self.all_classes]

    # These are the default options for graphviz
    default_graph_options = {
        "rankdir": "LR",
        "size": '"8.0, 12.0"'
        }
    default_node_options = {
        "shape": "box",
        "fontsize": 10,
        "height": 0.25,
        "fontname": "Vera Sans, DejaVu Sans, Liberation Sans, Arial, Helvetica, sans",
        "style": '"setlinewidth(0.5)"'
        }
    default_edge_options = {
        "arrowsize": 0.5,
        "style": '"setlinewidth(0.5)"'
        }

    def _format_node_options(self, options):
        return ','.join(["%s=%s" % x for x in options.items()])
    def _format_graph_options(self, options):
        return ''.join(["%s=%s;\n" % x for x in options.items()])

    def generate_dot(self, fd, name, parts=0, urls={},
                     graph_options={}, node_options={},
                     edge_options={}):
        """
        Generate a graphviz dot graph from the classes that
        were passed in to __init__.

        *fd* is a Python file-like object to write to.

        *name* is the name of the graph

        *urls* is a dictionary mapping class names to http urls

        *graph_options*, *node_options*, *edge_options* are
        dictionaries containing key/value pairs to pass on as graphviz
        properties.
        """
        g_options = self.default_graph_options.copy()
        g_options.update(graph_options)
        n_options = self.default_node_options.copy()
        n_options.update(node_options)
        e_options = self.default_edge_options.copy()
        e_options.update(edge_options)

        fd.write('digraph %s {\n' % name)
        fd.write(self._format_graph_options(g_options))

        for cls in self.all_classes:
            if not self.show_builtins and cls in __builtins__.values():
                continue

            name = self.class_name(cls, parts)

            # Write the node
            this_node_options = n_options.copy()
            url = urls.get(self.class_name(cls))
            if url is not None:
                this_node_options['URL'] = '"%s"' % url
            fd.write('  "%s" [%s];\n' %
                     (name, self._format_node_options(this_node_options)))

            # Write the edges
            for base in cls.__bases__:
                if not self.show_builtins and base in __builtins__.values():
                    continue

                base_name = self.class_name(base, parts)
                fd.write('  "%s" -> "%s" [%s];\n' %
                         (base_name, name,
                          self._format_node_options(e_options)))
        fd.write('}\n')

    def run_dot(self, args, name, parts=0, urls={},
                graph_options={}, node_options={}, edge_options={}):
        """
        Run graphviz 'dot' over this graph, returning whatever 'dot'
        writes to stdout.

        *args* will be passed along as commandline arguments.

        *name* is the name of the graph

        *urls* is a dictionary mapping class names to http urls

        Raises DotException for any of the many os and
        installation-related errors that may occur.
        """
        try:
            dot = subprocess.Popen(['dot'] + list(args),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   close_fds=True)
        except OSError:
            raise DotException("Could not execute 'dot'.  Are you sure you have 'graphviz' installed?")
        except ValueError:
            raise DotException("'dot' called with invalid arguments")
        except:
            raise DotException("Unexpected error calling 'dot'")

        self.generate_dot(dot.stdin, name, parts, urls, graph_options,
                          node_options, edge_options)
        dot.stdin.close()
        result = dot.stdout.read()
        returncode = dot.wait()
        if returncode != 0:
            raise DotException("'dot' returned the errorcode %d" % returncode)
        return result

class inheritance_diagram(Body, Element):
    """
    A docutils node to use as a placeholder for the inheritance
    diagram.
    """
    pass

def inheritance_diagram_directive(name, arguments, options, content, lineno,
                                  content_offset, block_text, state,
                                  state_machine):
    """
    Run when the inheritance_diagram directive is first encountered.
    """
    node = inheritance_diagram()

    class_names = arguments

    # Create a graph starting with the list of classes
    graph = InheritanceGraph(class_names)

    # Create xref nodes for each target of the graph's image map and
    # add them to the doc tree so that Sphinx can resolve the
    # references to real URLs later.  These nodes will eventually be
    # removed from the doctree after we're done with them.
    for name in graph.get_all_class_names():
        refnodes, x = xfileref_role(
            'class', ':class:`%s`' % name, name, 0, state)
        node.extend(refnodes)
    # Store the graph object so we can use it to generate the
    # dot file later
    node['graph'] = graph
    # Store the original content for use as a hash
    node['parts'] = options.get('parts', 0)
    node['content'] = " ".join(class_names)
    return [node]

def get_graph_hash(node):
    return md5(node['content'] + str(node['parts'])).hexdigest()[-10:]

def html_output_graph(self, node):
    """
    Output the graph for HTML.  This will insert a PNG with clickable
    image map.
    """
    graph = node['graph']
    parts = node['parts']

    graph_hash = get_graph_hash(node)
    name = "inheritance%s" % graph_hash
    path = '_images'
    dest_path = os.path.join(setup.app.builder.outdir, path)
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    png_path = os.path.join(dest_path, name + ".png")
    path = setup.app.builder.imgpath

    # Create a mapping from fully-qualified class names to URLs.
    urls = {}
    for child in node:
        if child.get('refuri') is not None:
            urls[child['reftitle']] = child.get('refuri')
        elif child.get('refid') is not None:
            urls[child['reftitle']] = '#' + child.get('refid')

    # These arguments to dot will save a PNG file to disk and write
    # an HTML image map to stdout.
    image_map = graph.run_dot(['-Tpng', '-o%s' % png_path, '-Tcmapx'],
                              name, parts, urls)
    return ('<img src="%s/%s.png" usemap="#%s" class="inheritance"/>%s' %
            (path, name, name, image_map))

def latex_output_graph(self, node):
    """
    Output the graph for LaTeX.  This will insert a PDF.
    """
    graph = node['graph']
    parts = node['parts']

    graph_hash = get_graph_hash(node)
    name = "inheritance%s" % graph_hash
    dest_path = os.path.abspath(os.path.join(setup.app.builder.outdir, '_images'))
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    pdf_path = os.path.abspath(os.path.join(dest_path, name + ".pdf"))

    graph.run_dot(['-Tpdf', '-o%s' % pdf_path],
                  name, parts, graph_options={'size': '"6.0,6.0"'})
    return '\n\\includegraphics{%s}\n\n' % pdf_path

def visit_inheritance_diagram(inner_func):
    """
    This is just a wrapper around html/latex_output_graph to make it
    easier to handle errors and insert warnings.
    """
    def visitor(self, node):
        try:
            content = inner_func(self, node)
        except DotException, e:
            # Insert the exception as a warning in the document
            warning = self.document.reporter.warning(str(e), line=node.line)
            warning.parent = node
            node.children = [warning]
        else:
            source = self.document.attributes['source']
            self.body.append(content)
            node.children = []
    return visitor

def do_nothing(self, node):
    pass

def setup(app):
    setup.app = app
    setup.confdir = app.confdir

    app.add_node(
        inheritance_diagram,
        latex=(visit_inheritance_diagram(latex_output_graph), do_nothing),
        html=(visit_inheritance_diagram(html_output_graph), do_nothing))
    app.add_directive(
        'inheritance-diagram', inheritance_diagram_directive,
        False, (1, 100, 0), parts = directives.nonnegative_int)

########NEW FILE########
__FILENAME__ = ipython_console_highlighting
"""reST directive for syntax-highlighting ipython interactive sessions.

XXX - See what improvements can be made based on the new (as of Sept 2009)
'pycon' lexer for the python console.  At the very least it will give better
highlighted tracebacks.
"""

#-----------------------------------------------------------------------------
# Needed modules

# Standard library
import re

# Third party
from pygments.lexer import Lexer, do_insertions
from pygments.lexers.agile import (PythonConsoleLexer, PythonLexer, 
                                   PythonTracebackLexer)
from pygments.token import Comment, Generic

from sphinx import highlighting

#-----------------------------------------------------------------------------
# Global constants
line_re = re.compile('.*?\n')

#-----------------------------------------------------------------------------
# Code begins - classes and functions

class IPythonConsoleLexer(Lexer):
    """
    For IPython console output or doctests, such as:

    .. sourcecode:: ipython

      In [1]: a = 'foo'

      In [2]: a
      Out[2]: 'foo'

      In [3]: print a
      foo

      In [4]: 1 / 0

    Notes:

      - Tracebacks are not currently supported.

      - It assumes the default IPython prompts, not customized ones.
    """
    
    name = 'IPython console session'
    aliases = ['ipython']
    mimetypes = ['text/x-ipython-console']
    input_prompt = re.compile("(In \[[0-9]+\]: )|(   \.\.\.+:)")
    output_prompt = re.compile("(Out\[[0-9]+\]: )|(   \.\.\.+:)")
    continue_prompt = re.compile("   \.\.\.+:")
    tb_start = re.compile("\-+")

    def get_tokens_unprocessed(self, text):
        pylexer = PythonLexer(**self.options)
        tblexer = PythonTracebackLexer(**self.options)

        curcode = ''
        insertions = []
        for match in line_re.finditer(text):
            line = match.group()
            input_prompt = self.input_prompt.match(line)
            continue_prompt = self.continue_prompt.match(line.rstrip())
            output_prompt = self.output_prompt.match(line)
            if line.startswith("#"):
                insertions.append((len(curcode),
                                   [(0, Comment, line)]))
            elif input_prompt is not None:
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, input_prompt.group())]))
                curcode += line[input_prompt.end():]
            elif continue_prompt is not None:
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, continue_prompt.group())]))
                curcode += line[continue_prompt.end():]
            elif output_prompt is not None:
                # Use the 'error' token for output.  We should probably make
                # our own token, but error is typicaly in a bright color like
                # red, so it works fine for our output prompts.
                insertions.append((len(curcode),
                                   [(0, Generic.Error, output_prompt.group())]))
                curcode += line[output_prompt.end():]
            else:
                if curcode:
                    for item in do_insertions(insertions,
                                              pylexer.get_tokens_unprocessed(curcode)):
                        yield item
                        curcode = ''
                        insertions = []
                yield match.start(), Generic.Output, line
        if curcode:
            for item in do_insertions(insertions,
                                      pylexer.get_tokens_unprocessed(curcode)):
                yield item


def setup(app):
    """Setup as a sphinx extension."""

    # This is only a lexer, so adding it below to pygments appears sufficient.
    # But if somebody knows that the right API usage should be to do that via
    # sphinx, by all means fix it here.  At least having this setup.py
    # suppresses the sphinx warning we'd get without it.
    pass

#-----------------------------------------------------------------------------
# Register the extension as a valid pygments lexer
highlighting.lexers['ipython'] = IPythonConsoleLexer()

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

.. [1] http://projects.scipy.org/scipy/numpy/wiki/CodingStyleGuidelines#docstring-standard

"""

import os, re, pydoc
from docscrape_sphinx import get_doc_object, SphinxDocString
import inspect

def mangle_docstrings(app, what, name, obj, options, lines,
                      reference_offset=[0]):
    if what == 'module':
        # Strip top title
        title_re = re.compile(r'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                              re.I|re.S)
        lines[:] = title_re.sub('', "\n".join(lines)).split("\n")
    else:
        doc = get_doc_object(obj, what, "\n".join(lines))
        lines[:] = unicode(doc).split("\n")

    if app.config.numpydoc_edit_link and hasattr(obj, '__name__') and \
           obj.__name__:
        if hasattr(obj, '__module__'):
            v = dict(full_name="%s.%s" % (obj.__module__, obj.__name__))
        else:
            v = dict(full_name=obj.__name__)
        lines += ['', '.. htmlonly::', '']
        lines += ['    %s' % x for x in
                  (app.config.numpydoc_edit_link % v).split("\n")]

    # replace reference numbers so that there are no duplicates
    references = []
    for l in lines:
        l = l.strip()
        if l.startswith('.. ['):
            try:
                references.append(int(l[len('.. ['):l.index(']')]))
            except ValueError:
                print "WARNING: invalid reference in %s docstring" % name

    # Start renaming from the biggest number, otherwise we may
    # overwrite references.
    references.sort()
    if references:
        for i, line in enumerate(lines):
            for r in references:
                new_r = reference_offset[0] + r
                lines[i] = lines[i].replace('[%d]_' % r,
                                            '[%d]_' % new_r)
                lines[i] = lines[i].replace('.. [%d]' % r,
                                            '.. [%d]' % new_r)

    reference_offset[0] += len(references)

def mangle_signature(app, what, name, obj, options, sig, retann):
    # Do not try to inspect classes that don't define `__init__`
    if (inspect.isclass(obj) and
        'initializes x; see ' in pydoc.getdoc(obj.__init__)):
        return '', ''

    if not (callable(obj) or hasattr(obj, '__argspec_is_invalid_')): return
    if not hasattr(obj, '__doc__'): return

    doc = SphinxDocString(pydoc.getdoc(obj))
    if doc['Signature']:
        sig = re.sub("^[^(]*", "", doc['Signature'])
        return sig, ''

def initialize(app):
    try:
        app.connect('autodoc-process-signature', mangle_signature)
    except:
        monkeypatch_sphinx_ext_autodoc()

def setup(app, get_doc_object_=get_doc_object):
    global get_doc_object
    get_doc_object = get_doc_object_
    
    app.connect('autodoc-process-docstring', mangle_docstrings)
    app.connect('builder-inited', initialize)
    app.add_config_value('numpydoc_edit_link', None, True)

#------------------------------------------------------------------------------
# Monkeypatch sphinx.ext.autodoc to accept argspecless autodocs (Sphinx < 0.5)
#------------------------------------------------------------------------------

def monkeypatch_sphinx_ext_autodoc():
    global _original_format_signature
    import sphinx.ext.autodoc

    if sphinx.ext.autodoc.format_signature is our_format_signature:
        return

    print "[numpydoc] Monkeypatching sphinx.ext.autodoc ..."
    _original_format_signature = sphinx.ext.autodoc.format_signature
    sphinx.ext.autodoc.format_signature = our_format_signature

def our_format_signature(what, obj):
    r = mangle_signature(None, what, None, obj, None, None, None)
    if r is not None:
        return r[0]
    else:
        return _original_format_signature(what, obj)

########NEW FILE########
__FILENAME__ = sphinx_cython
'''

sphinx_cython.py

This module monkeypatches sphinx autodoc to support Cython generated
function signatures in the first line of the docstring of functions
implemented as C extensions. 

Copyright (C) Nikolaus Rath <Nikolaus@rath.org>

This file is part of LLFUSE (http://python-llfuse.googlecode.com).
LLFUSE can be distributed under the terms of the GNU LGPL.

It has been slightly modified by MinRK.
'''

import sphinx.ext.autodoc as SphinxAutodoc
from sphinx.util.docstrings import prepare_docstring
import inspect
import re
from sphinx.util import force_decode

TYPE_RE = re.compile(r'(?:int|char)(?:\s+\*?\s*|\s*\*?\s+)([a-zA-Z_].*)')

ClassDocumenter  = SphinxAutodoc.ClassDocumenter
MethodDocumenter = SphinxAutodoc.MethodDocumenter
FunctionDocumenter = SphinxAutodoc.FunctionDocumenter

class MyDocumenter(SphinxAutodoc.Documenter):
    '''
    Overwrites `get_doc()` to remove function and
    method signatures and `format_args` to parse and give
    precedence to function signatures in the first line
    of the docstring. 
    ''' 

    def get_doc(self, encoding=None):
        docstr = self.get_attr(self.object, '__doc__', None)
        if docstr:
            docstr = force_decode(docstr, encoding)
        
        myname = self.fullname[len(self.modname)+1:]
        if myname.endswith('()'):
            myname = myname[:-2]
        
        if (docstr
            and (myname + '(') in docstr
            and '\n' in docstr
            and docstr[docstr.index('\n')-1] == ')'):
            docstr = docstr[docstr.index('\n')+1:]
                    
        if docstr:
            # make sure we have Unicode docstrings, then sanitize and split
            # into lines
            return [prepare_docstring(force_decode(docstr, encoding))]
        return []
        
        
    def format_args(self):
        myname = self.fullname[len(self.modname)+1:]
        if myname.endswith('()'):
            myname = myname[:-2]
        # Try to parse docstring
        docstr = self.get_attr(self.object, '__doc__', None)
        if docstr:
            docstr = force_decode(docstr, 'utf-8')
        if (docstr 
            and (myname + '(') in docstr
            and '\n' in docstr
            and docstr[docstr.index('\n')-1] == ')'):
            args = docstr[len(myname)+1:docstr.index('\n')-1]
            
            # Get rid of Cython style types declarations
            argl = []
            for arg in [ x.strip() for x in args.split(',') ]:
                if (arg in ('cls', 'self') 
                    and isinstance(self, SphinxAutodoc.MethodDocumenter)):
                    continue 
                hit = TYPE_RE.match(arg)
                if hit:
                    argl.append(hit.group(1))
                else:
                    argl.append(arg)
            args = '(%s)' % ', '.join(argl)
        else:
            # super seems to get this wrong:
            for cls in (MethodDocumenter,
                        FunctionDocumenter,
                        ClassDocumenter):
                if isinstance(self, cls):
                    return cls.format_args(self)
            # return super(self.__class__, self).format_args()  

        # escape backslashes for reST
        args = args.replace('\\', '\\\\')
        return args


class MyFunctionDocumenter(MyDocumenter, SphinxAutodoc.FunctionDocumenter):
    pass
        
class MyMethodDocumenter(MyDocumenter, SphinxAutodoc.MethodDocumenter):    
    pass

class MyClassDocumenter(MyDocumenter, SphinxAutodoc.ClassDocumenter):    
    def format_signature(self):
        return self.format_args() or "()"

SphinxAutodoc.ClassDocumenter = MyClassDocumenter 
SphinxAutodoc.MethodDocumenter = MyMethodDocumenter 
SphinxAutodoc.FunctionDocumenter = MyFunctionDocumenter

# don't use AttributeDocumenter on 'method_descriptor' members:
AD = SphinxAutodoc.AttributeDocumenter
AD.method_types = tuple(list(AD.method_types) + [type(str.count)])

########NEW FILE########
__FILENAME__ = benchmark
from timeit import default_timer as timer

def benchmark(f, size, reps):
    msg = size*'0'
    t1 = timer()
    for i in range(reps):
        msg2 = f(msg)
        assert msg == msg2
    t2 = timer()
    diff = (t2-t1)
    latency = diff/reps
    return latency*1000000

kB = [1000*2**n for n in range(10)]
MB = [1000000*2**n for n in range(8)]
sizes = [1] + kB + MB

def benchmark_set(f, sizes, reps):
    latencies = []
    for size, rep in zip(sizes, reps):
        print "Running benchmark with %r reps of %r bytes" % (rep, size)
        lat = benchmark(f, size, rep)
        latencies.append(lat)
    return sizes, latencies


########NEW FILE########
__FILENAME__ = jsonrpc_client
from timeit import default_timer as timer
from jsonrpclib import Server

client = Server('http://localhost:10000')

########NEW FILE########
__FILENAME__ = jsonrpc_server
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

def echo(x):
    return x

server = SimpleJSONRPCServer(('localhost',10000))
server.register_function(echo)
server.serve_forever()
########NEW FILE########
__FILENAME__ = plot_latency
"""Plot latency data from messaging benchmarks.

To generate the data for each library, I started the server and then did
the following for each client::

    from xmlrpc_client import client
    for i in range(9):
        s = '0'*10**i
        print s
        %timeit client.echo(s)
"""

from matplotlib.pylab import *

rawdata = """# Data in milliseconds
Bytes	JSONRPC	PYRO	XMLRPC	pyzmq_copy	pyzmq_nocopy
1	2.15	0.186	2.07	0.111	0.136
10	2.49	0.187	1.87	0.115	0.137
100	2.5	0.189	1.9	0.126	0.138
1000	2.54	0.196	1.91	0.129	0.141
10000	2.91	0.271	2.77	0.204	0.197
100000	6.65	1.44	9.17	0.961	0.546
1000000	50.2	15.8	81.5	8.39	2.25
10000000	491	159	816	91.7	25.2
100000000	5010	1560	8300	893	248

"""
with open('latency.csv','w') as f:
    f.writelines(rawdata)

data = csv2rec('latency.csv',delimiter='\t')

loglog(data.bytes, data.xmlrpc*1000, label='XMLRPC')
loglog(data.bytes, data.jsonrpc*1000, label='JSONRPC')
loglog(data.bytes, data.pyro*1000, label='Pyro')
loglog(data.bytes, data.pyzmq_nocopy*1000, label='PyZMQ')
loglog(data.bytes, len(data.bytes)*[60], label='Ping')
legend(loc=2)
title('Latency')
xlabel('Number of bytes')
ylabel('Round trip latency ($\mu s$)')
grid(True)
show()
savefig('latency.png')

clf()

semilogx(data.bytes, 1000/data.xmlrpc, label='XMLRPC')
semilogx(data.bytes, 1000/data.jsonrpc, label='JSONRPC')
semilogx(data.bytes, 1000/data.pyro, label='Pyro')
semilogx(data.bytes, 1000/data.pyzmq_nocopy, label='PyZMQ')
legend(loc=1)
xlabel('Number of bytes')
ylabel('Message/s')
title('Message Throughput')
grid(True)
show()
savefig('msgs_sec.png')

clf()

loglog(data.bytes, 1000/data.xmlrpc, label='XMLRPC')
loglog(data.bytes, 1000/data.jsonrpc, label='JSONRPC')
loglog(data.bytes, 1000/data.pyro, label='Pyro')
loglog(data.bytes, 1000/data.pyzmq_nocopy, label='PyZMQ')
legend(loc=3)
xlabel('Number of bytes')
ylabel('Message/s')
title('Message Throughput')
grid(True)
show()
savefig('msgs_sec_log.png')

clf()

semilogx(data.bytes, data.pyro/data.pyzmq_nocopy, label="No-copy")
semilogx(data.bytes, data.pyro/data.pyzmq_copy, label="Copy")
xlabel('Number of bytes')
ylabel('Ratio throughputs')
title('PyZMQ Throughput/Pyro Throughput')
grid(True)
legend(loc=2)
show()
savefig('msgs_sec_ratio.png')

########NEW FILE########
__FILENAME__ = pyro_client
import Pyro.core

client = Pyro.core.getProxyForURI("PYROLOC://localhost:7766/echo")
########NEW FILE########
__FILENAME__ = pyro_server
import Pyro.core

class Echo(Pyro.core.ObjBase):
        def __init__(self):
                Pyro.core.ObjBase.__init__(self)
        def echo(self, x):
                return x

Pyro.core.initServer()
daemon=Pyro.core.Daemon()
uri=daemon.connect(Echo(),"echo")

daemon.requestLoop()
    
########NEW FILE########
__FILENAME__ = pyzmq_client
import zmq

c = zmq.Context()
s = c.socket(zmq.REQ)
s.connect('tcp://127.0.0.1:10001')

def echo(msg):
    s.send(msg, copy=False)
    msg2 = s.recv(copy=False)
    return msg2

class Client(object):
    pass

client = Client()
client.echo = echo

########NEW FILE########
__FILENAME__ = pyzmq_server
import zmq

c = zmq.Context()
s = c.socket(zmq.REP)
s.bind('tcp://127.0.0.1:10001')

while True:
    msg = s.recv(copy=False)
    s.send(msg)


########NEW FILE########
__FILENAME__ = xmlrpc_client
from timeit import default_timer as timer
from xmlrpclib import ServerProxy

client = ServerProxy('http://localhost:10002')

    
########NEW FILE########
__FILENAME__ = xmlrpc_server
from SimpleXMLRPCServer import SimpleXMLRPCServer

def echo(x):
    return x

server = SimpleXMLRPCServer(('localhost',10002))
server.register_function(echo)
server.serve_forever()
########NEW FILE########
__FILENAME__ = display
"""The display part of a simply two process chat app."""

#
#    Copyright (c) 2010 Andrew Gwozdziewycz
#
#    This file is part of pyzmq.
#
#    pyzmq is free software; you can redistribute it and/or modify it under
#    the terms of the Lesser GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    pyzmq is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    Lesser GNU General Public License for more details.
#
#    You should have received a copy of the Lesser GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import zmq

def main(addrs):
    
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, "")
    for addr in addrs:
        print "Connecting to: ", addr
        socket.connect(addr)

    while True:
        msg = socket.recv_pyobj()
        print "%s: %s" % (msg[1], msg[0])

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print "usage: display.py <address> [,<address>...]"
        raise SystemExit
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = prompt
"""The prompt part of a simply two process chat app."""

#
#    Copyright (c) 2010 Andrew Gwozdziewycz
#
#    This file is part of pyzmq.
#
#    pyzmq is free software; you can redistribute it and/or modify it under
#    the terms of the Lesser GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    pyzmq is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    Lesser GNU General Public License for more details.
#
#    You should have received a copy of the Lesser GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import zmq

def main(addr, who):

    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUB)
    socket.bind(addr)

    while True:
        msg = raw_input("%s> " % who)
        socket.send_pyobj((msg, who))


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print "usage: prompt.py <address> <username>"
        raise SystemExit
    main(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = client
"""A client for the device based server."""

#
#    Copyright (c) 2010 Brian E. Granger and Eugene Chernyshov
#
#    This file is part of pyzmq.
#
#    pyzmq is free software; you can redistribute it and/or modify it under
#    the terms of the Lesser GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    pyzmq is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    Lesser GNU General Public License for more details.
#
#    You should have received a copy of the Lesser GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import zmq
import os
from time import time

print 'Client', os.getpid()

context = zmq.Context(1)

socket = context.socket(zmq.REQ)
socket.connect('tcp://127.0.0.1:5555')

while True:
    data = zmq.Message(str(os.getpid()))
    start = time()
    socket.send(data)
    data = socket.recv()
    print time()-start, data


########NEW FILE########
__FILENAME__ = server
"""A device based server."""

#
#    Copyright (c) 2010 Brian E. Granger and Eugene Chernyshov
#
#    This file is part of pyzmq.
#
#    pyzmq is free software; you can redistribute it and/or modify it under
#    the terms of the Lesser GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    pyzmq is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    Lesser GNU General Public License for more details.
#
#    You should have received a copy of the Lesser GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import zmq
import os
import threading
import time

print 'Server', os.getpid()

def routine(context):
    socket = context.socket(zmq.REP)

    socket.connect("inproc://workers")

    while True:
        message = socket.recv()
        time.sleep(1)
        socket.send(message)

context = zmq.Context(1)

workers = context.socket(zmq.DEALER)
workers.bind("inproc://workers");

clients = context.socket(zmq.DEALER)
clients.bind('tcp://127.0.0.1:5555')

for i in range(10):
    thread = threading.Thread(target=routine, args=(context, ))
    thread.start()

zmq.device(zmq.QUEUE, clients, workers)

print "Finished"

########NEW FILE########
__FILENAME__ = asyncweb
"""Async web request example with tornado.

Requests to localhost:8888 will be relayed via 0MQ to a slow responder,
who will take 1-5 seconds to respond.  The tornado app will remain responsive
duriung this time, and when the worker replies, the web request will finish.

A '.' is printed every 100ms to demonstrate that the zmq request is not blocking
the event loop.
"""


import sys
import random
import threading
import time

import zmq
from zmq.eventloop import ioloop, zmqstream

"""
ioloop.install() must be called prior to instantiating *any* tornado objects,
and ideally before importing anything from tornado, just to be safe.

install() sets the singleton instance of tornado.ioloop.IOLoop with zmq's
IOLoop. If this is not done properly, multiple IOLoop instances may be
created, which will have the effect of some subset of handlers never being
called, because only one loop will be running.
"""

ioloop.install()

import tornado
from tornado import web


def slow_responder():
    """thread for slowly responding to replies."""
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.REP)
    socket.linger = 0
    socket.bind('tcp://127.0.0.1:5555')
    i=0
    while True:
        msg = socket.recv()
        print "\nworker received %r\n" % msg
        time.sleep(random.randint(1,5))
        socket.send(msg + " to you too, #%i" % i)
        i+=1

def dot():
    """callback for showing that IOLoop is still responsive while we wait"""
    sys.stdout.write('.')
    sys.stdout.flush()

def printer(msg):
    print (msg)

class TestHandler(web.RequestHandler):
    
    @web.asynchronous
    def get(self):
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.connect('tcp://127.0.0.1:5555')
        # send request to worker
        s.send('hello')
        loop = ioloop.IOLoop.instance()
        self.stream = zmqstream.ZMQStream(s)
        self.stream.on_recv(self.handle_reply)
    
    def handle_reply(self, msg):
        # finish web request with worker's reply
        reply = msg[0]
        print "\nfinishing with %r\n" % reply,
        self.stream.close()
        self.write(reply)
        self.finish()

def main():
    worker = threading.Thread(target=slow_responder)
    worker.daemon=True
    worker.start()
    
    application = web.Application([(r"/", TestHandler)])
    beat = ioloop.PeriodicCallback(dot, 100)
    beat.start()
    application.listen(8888)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print ' Interrupted'
    
    
if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = echo
#!/usr/bin/env python
"""A trivial ZMQ echo server using the eventloop.

Authors
-------
* MinRK
"""

import zmq
from zmq.eventloop import ioloop

loop = ioloop.IOLoop.instance()

ctx = zmq.Context()
s = ctx.socket(zmq.REP)
s.bind('tcp://127.0.0.1:5555')

def rep_handler(sock, events):
    # We don't know how many recv's we can do?
    msg = sock.recv()
    # No guarantee that we can do the send. We need a way of putting the
    # send in the event loop.
    sock.send(msg)

loop.add_handler(s, rep_handler, zmq.POLLIN)

loop.start()
########NEW FILE########
__FILENAME__ = echostream
#!/usr/bin/env python
"""Adapted echo.py to put the send in the event loop using a ZMQStream.

Authors
-------
* MinRK
"""

import zmq
from zmq.eventloop import ioloop, zmqstream
loop = ioloop.IOLoop.instance()

ctx = zmq.Context()
s = ctx.socket(zmq.REP)
s.bind('tcp://127.0.0.1:5555')
stream = zmqstream.ZMQStream(s, loop)

def echo(msg):
    print " ".join(msg)
    stream.send_multipart(msg)

stream.on_recv(echo)

loop.start()
########NEW FILE########
__FILENAME__ = web
import zmq
from zmq.eventloop import ioloop, zmqstream

"""
ioloop.install() must be called prior to instantiating *any* tornado objects,
and ideally before importing anything from tornado, just to be safe.

install() sets the singleton instance of tornado.ioloop.IOLoop with zmq's
IOLoop. If this is not done properly, multiple IOLoop instances may be
created, which will have the effect of some subset of handlers never being
called, because only one loop will be running.
"""

ioloop.install()

import tornado
import tornado.web


"""
this application can be used with echostream.py, start echostream.py,
start web.py, then every time you hit http://localhost:8888/,
echostream.py will print out 'hello'
"""

def printer(msg):
    print (msg)

ctx = zmq.Context()
s = ctx.socket(zmq.REQ)
s.connect('tcp://127.0.0.1:5555')
stream = zmqstream.ZMQStream(s)
stream.on_recv(printer)

class TestHandler(tornado.web.RequestHandler):
    def get(self):
        print ("sending hello")
        stream.send("hello")
        self.write("hello")
application = tornado.web.Application([(r"/", TestHandler)])

if __name__ == "__main__":
    application.listen(8888)
    ioloop.IOLoop.instance().start()




########NEW FILE########
__FILENAME__ = poll
import gevent
from zmq import green as zmq

# Connect to both receiving sockets and send 10 messages
def sender():

    sender = context.socket(zmq.PUSH)
    sender.connect('inproc://polltest1')
    sender.connect('inproc://polltest2')

    for i in xrange(10):
        sender.send('test %d' % i)
        gevent.sleep(1)


# create zmq context, and bind to pull sockets
context = zmq.Context()
receiver1 = context.socket(zmq.PULL)
receiver1.bind('inproc://polltest1')
receiver2 = context.socket(zmq.PULL)
receiver2.bind('inproc://polltest2')

gevent.spawn(sender)

# Create poller and register both reciever sockets
poller = zmq.Poller()
poller.register(receiver1, zmq.POLLIN)
poller.register(receiver2, zmq.POLLIN)

# Read 10 messages from both reciever sockets
msgcnt = 0
while msgcnt < 10:
    socks = dict(poller.poll())
    if receiver1 in socks and socks[receiver1] == zmq.POLLIN:
        print "Message from receiver1: %s" % receiver1.recv()
        msgcnt += 1

    if receiver2 in socks and socks[receiver2] == zmq.POLLIN:
        print "Message from receiver2: %s" % receiver2.recv()
        msgcnt += 1

print "%d messages received" % msgcnt

########NEW FILE########
__FILENAME__ = reqrep
"""
Complex example which is a combination of the rr* examples from the zguide.
"""
from gevent import spawn
import zmq.green as zmq

# server
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://localhost:5560")

def serve(socket):
    while True:
        message = socket.recv()
        print "Received request: ", message
        socket.send("World")
server = spawn(serve, socket)


# client
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5559")

#  Do 10 requests, waiting each time for a response
def client():
    for request in range(1,10):
        socket.send("Hello")
        message = socket.recv()
        print "Received reply ", request, "[", message, "]"


# broker
frontend = context.socket(zmq.ROUTER)
backend  = context.socket(zmq.DEALER);
frontend.bind("tcp://*:5559")
backend.bind("tcp://*:5560")

def proxy(socket_from, socket_to):
    while True:
        m = socket_from.recv_multipart()
        socket_to.send_multipart(m)

a = spawn(proxy, frontend, backend)
b = spawn(proxy, backend, frontend)

spawn(client).join()

########NEW FILE########
__FILENAME__ = simple
from gevent import spawn, spawn_later
import zmq.green as zmq

# server
print zmq.Context
ctx = zmq.Context()
sock = ctx.socket(zmq.PUSH)
sock.bind('ipc:///tmp/zmqtest')

spawn(sock.send_pyobj, ('this', 'is', 'a', 'python', 'tuple'))
spawn_later(1, sock.send_pyobj, {'hi': 1234})
spawn_later(2, sock.send_pyobj, ({'this': ['is a more complicated object', ':)']}, 42, 42, 42))
spawn_later(3, sock.send_pyobj, 'foobar')
spawn_later(4, sock.send_pyobj, 'quit')


# client
ctx = zmq.Context() # create a new context to kick the wheels
sock = ctx.socket(zmq.PULL)
sock.connect('ipc:///tmp/zmqtest')

def get_objs(sock):
    while True:
        o = sock.recv_pyobj()
        print 'received python object:', o
        if o == 'quit':
            print 'exiting.'
            break

def print_every(s, t=None):
    print s
    if t:
        spawn_later(t, print_every, s, t)

print_every('printing every half second', 0.5)
spawn(get_objs, sock).join()


########NEW FILE########
__FILENAME__ = heart
#!/usr/bin/env python
"""This launches an echoing rep socket device,
and runs a blocking numpy action. The rep socket should
remain responsive to pings during this time. Use heartbeater.py to
ping this heart, and see the responsiveness.

Authors
-------
* MinRK
"""

import time
import numpy
import zmq
from zmq import devices

ctx = zmq.Context()

dev = devices.ThreadDevice(zmq.FORWARDER, zmq.SUB, zmq.DEALER)
dev.setsockopt_in(zmq.SUBSCRIBE, "")
dev.connect_in('tcp://127.0.0.1:5555')
dev.connect_out('tcp://127.0.0.1:5556')
dev.start()

#wait for connections
time.sleep(1)

A = numpy.random.random((2**11,2**11))
print "starting blocking loop"
while True:
    tic = time.time()
    numpy.dot(A,A.transpose())
    print "blocked for %.3f s"%(time.time()-tic)


########NEW FILE########
__FILENAME__ = heartbeater
#!/usr/bin/env python
"""

For use with heart.py

A basic heartbeater using PUB and ROUTER sockets. pings are sent out on the PUB, and hearts
are tracked based on their DEALER identities.

You can start many hearts with heart.py, and the heartbeater will monitor all of them, and notice when they stop responding.

Authors
-------
* MinRK
"""

import time
import zmq
from zmq.eventloop import ioloop, zmqstream


class HeartBeater(object):
    """A basic HeartBeater class
    pingstream: a PUB stream
    pongstream: an ROUTER stream"""
    
    def __init__(self, loop, pingstream, pongstream, period=1000):
        self.loop = loop
        self.period = period
        
        self.pingstream = pingstream
        self.pongstream = pongstream
        self.pongstream.on_recv(self.handle_pong)
        
        self.hearts = set()
        self.responses = set()
        self.lifetime = 0
        self.tic = time.time()
        
        self.caller = ioloop.PeriodicCallback(self.beat, period, self.loop)
        self.caller.start()
    
    def beat(self):
        toc = time.time()
        self.lifetime += toc-self.tic
        self.tic = toc
        print self.lifetime
        # self.message = str(self.lifetime)
        goodhearts = self.hearts.intersection(self.responses)
        heartfailures = self.hearts.difference(goodhearts)
        newhearts = self.responses.difference(goodhearts)
        # print newhearts, goodhearts, heartfailures
        map(self.handle_new_heart, newhearts)
        map(self.handle_heart_failure, heartfailures)
        self.responses = set()
        print "%i beating hearts: %s"%(len(self.hearts),self.hearts)
        self.pingstream.send(str(self.lifetime))
    
    def handle_new_heart(self, heart):
        print "yay, got new heart %s!"%heart
        self.hearts.add(heart)
    
    def handle_heart_failure(self, heart):
        print "Heart %s failed :("%heart
        self.hearts.remove(heart)
        
    
    def handle_pong(self, msg):
        "if heart is beating"
        if msg[1] == str(self.lifetime):
            self.responses.add(msg[0])
        else:
            print "got bad heartbeat (possibly old?): %s"%msg[1]
        
# sub.setsockopt(zmq.SUBSCRIBE)


if __name__ == '__main__':
    loop = ioloop.IOLoop()
    context = zmq.Context()
    pub = context.socket(zmq.PUB)
    pub.bind('tcp://127.0.0.1:5555')
    router = context.socket(zmq.ROUTER)
    router.bind('tcp://127.0.0.1:5556')
    
    outstream = zmqstream.ZMQStream(pub, loop)
    instream = zmqstream.ZMQStream(router, loop)
    
    hb = HeartBeater(loop, outstream, instream)
    
    loop.start()

########NEW FILE########
__FILENAME__ = ping
#!/usr/bin/env python
"""For use with pong.py

This script simply pings a process started by pong.py or tspong.py, to 
demonstrate that zmq remains responsive while Python blocks.

Authors
-------
* MinRK
"""

import time
import numpy
import zmq

ctx = zmq.Context()

req = ctx.socket(zmq.REQ)
req.connect('tcp://127.0.0.1:10111')

#wait for connects
time.sleep(1)
n=0
while True:
    time.sleep(numpy.random.random())
    for i in range(4):
        n+=1
        msg = 'ping %i'%n
        tic = time.time()
        req.send(msg)
        resp = req.recv()
        print "%s: %.2f ms" % (msg, 1000*(time.time()-tic))
        assert msg == resp


########NEW FILE########
__FILENAME__ = pong
#!/usr/bin/env python
"""This launches an echoing rep socket device using 
zmq.devices.ThreadDevice, and runs a blocking numpy action. 
The rep socket should remain responsive to pings during this time.

Use ping.py to see how responsive it is.

Authors
-------
* MinRK
"""

import time
import numpy
import zmq
from zmq import devices

ctx = zmq.Context()

dev = devices.ThreadDevice(zmq.FORWARDER, zmq.REP, -1)
dev.bind_in('tcp://127.0.0.1:10111')
dev.setsockopt_in(zmq.IDENTITY, "whoda")
dev.start()

#wait for connections
time.sleep(1)

A = numpy.random.random((2**11,2**12))
print "starting blocking loop"
while True:
    tic = time.time()
    numpy.dot(A,A.transpose())
    print "blocked for %.3f s"%(time.time()-tic)


########NEW FILE########
__FILENAME__ = zmqlogger
"""
Simple example of using zmq log handlers

This starts a number of subprocesses with PUBHandlers that generate
log messages at a regular interval.  The main process has a SUB socket,
which aggregates and logs all of the messages to the root logger.
"""

import logging
from multiprocessing import Process
import os
import random
import sys
import time

import zmq
from zmq.log.handlers import PUBHandler

LOG_LEVELS = (logging.DEBUG, logging.INFO, logging.WARN, logging.ERROR, logging.CRITICAL)

def sub_logger(port, level=logging.DEBUG):
    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.bind('tcp://127.0.0.1:%i' % port)
    sub.setsockopt(zmq.SUBSCRIBE, "")
    logging.basicConfig(level=level)
    
    while True:
        level, message = sub.recv_multipart()
        if message.endswith('\n'):
            # trim trailing newline, which will get appended again
            message = message[:-1]
        log = getattr(logging, level.lower())
        log(message)

def log_worker(port, interval=1, level=logging.DEBUG):
    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.connect('tcp://127.0.0.1:%i' % port)
    
    logger = logging.getLogger(str(os.getpid()))
    logger.setLevel(level)
    handler = PUBHandler(pub)
    logger.addHandler(handler)
    print "starting logger at %i with level=%s" % (os.getpid(), level)

    while True:
        level = random.choice(LOG_LEVELS)
        logger.log(level, "Hello from %i!" % os.getpid())
        time.sleep(interval)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    else:
        n = 2
    
    port = 5555
    
    # start the log generators
    workers = [ Process(target=log_worker, args=(port,), kwargs=dict(level=random.choice(LOG_LEVELS))) for i in range(n) ]
    [ w.start() for w in workers ]
    
    # start the log watcher
    try:
        sub_logger(port)
    except KeyboardInterrupt:
        pass
    finally:
        [ w.terminate() for w in workers ]

########NEW FILE########
__FILENAME__ = client
#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Justin Riley
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import zmq

class MongoZMQClient(object):
    """
    Client that connects with MongoZMQ server to add/fetch docs 
    """

    def __init__(self, connect_addr='tcp://127.0.0.1:5000'):
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.DEALER)
        self._socket.connect(connect_addr)

    def _send_recv_msg(self, msg):
        self._socket.send_multipart(msg)
        return self._socket.recv_multipart()[0]

    def get_doc(self, keys):
        msg = ['get', json.dumps(keys)]
        json_str = self._send_recv_msg(msg)
        return json.loads(json_str)

    def add_doc(self, doc):
        msg = ['add', json.dumps(doc)]
        return self._send_recv_msg(msg)

def main():
    client = MongoZMQClient()
    for i in range(10):
        doc = {'job': str(i)}
        print "Adding doc", doc
        print client.add_doc(doc)
    for i in range(10):
        query = {'job': str(i)}
        print "Getting doc matching query:", query
        print client.get_doc(query)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = controller
#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Justin Riley
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import sys
import zmq
import pymongo
import pymongo.json_util
import json

class MongoZMQ(object):
    """
    ZMQ server that adds/fetches documents (ie dictionaries) to a MongoDB.

    NOTE: mongod must be started before using this class
    """

    def __init__(self, db_name, table_name, bind_addr="tcp://127.0.0.1:5000"):
        """
        bind_addr: address to bind zmq socket on
        db_name: name of database to write to (created if doesnt exist)
        table_name: name of mongodb 'table' in the db to write to (created if doesnt exist)
        """
        self._bind_addr = bind_addr
        self._db_name = db_name
        self._table_name = table_name
        self._conn = pymongo.Connection()
        self._db = self._conn[self._db_name]
        self._table = self._db[self._table_name]

    def _doc_to_json(self, doc):
        return json.dumps(doc,default=pymongo.json_util.default)

    def add_document(self, doc):
        """
        Inserts a document (dictionary) into mongo database table
        """
        print 'adding docment %s' % (doc)
        try:
            self._table.insert(doc)
        except Exception,e:
            return 'Error: %s' % e

    def get_document_by_keys(self, keys):
        """
        Attempts to return a single document from database table that matches
        each key/value in keys dictionary.
        """
        print 'attempting to retrieve document using keys: %s' % keys
        try:
            return self._table.find_one(keys)
        except Exception,e:
            return 'Error: %s' % e

    def start(self):
        context = zmq.Context()
        socket = context.socket(zmq.ROUTER)
        socket.bind(self._bind_addr)
        while True:
            msg = socket.recv_multipart()
            print "Received msg: ", msg
            if  len(msg) != 3:
                error_msg = 'invalid message received: %s' % msg
                print error_msg
                reply = [msg[0], error_msg]
                socket.send_multipart(reply)
                continue
            id = msg[0]
            operation = msg[1]
            contents = json.loads(msg[2])
            # always send back the id with ROUTER
            reply = [id]
            if operation == 'add':
                self.add_document(contents)
                reply.append("success")
            elif operation == 'get':
                doc = self.get_document_by_keys(contents)
                json_doc = self._doc_to_json(doc)
                reply.append(json_doc)
            else:
                print 'unknown request'
            socket.send_multipart(reply)

def main():
    MongoZMQ('ipcontroller','jobs').start()

if __name__ == "__main__":
   main()

########NEW FILE########
__FILENAME__ = simple_monitor
# -*- coding: utf-8 -*-
"""Simple example demonstrating the use of the socket monitoring feature."""

# This file is part of pyzmq.
#
# Distributed under the terms of the New BSD License. The full
# license is in the file COPYING.BSD, distributed as part of this
# software.
from __future__ import print_function

__author__ = 'Guido Goldstein'

import json
import os
import struct
import sys
import threading
import time

import zmq
from zmq.utils.monitor import recv_monitor_message

line = lambda : print('-' * 40)

def logger(monitor):
    done = False
    while monitor.poll(timeout=5000):
        evt = recv_monitor_message(monitor)
        print(json.dumps(evt, indent=1))
        if evt['event'] == zmq.EVENT_MONITOR_STOPPED:
            break
    print()
    print("Logger done!")
    monitor.close()

print("libzmq-%s" % zmq.zmq_version())
if zmq.zmq_version_info() < (4,0):
    raise RuntimeError("monitoring in libzmq version < 4.0 is not supported")

print("Event names:")
for name in dir(zmq):
    if name.startswith('EVENT_'):
        print("%21s : %4i" % (name, getattr(zmq, name)))


ctx = zmq.Context().instance()
rep = ctx.socket(zmq.REP)
req = ctx.socket(zmq.REQ)

monitor = req.get_monitor_socket()

t = threading.Thread(target=logger, args=(monitor,))
t.start()

line()
print("bind req")
req.bind("tcp://127.0.0.1:6666")
req.bind("tcp://127.0.0.1:6667")
time.sleep(1)

line()
print("connect rep")
rep.connect("tcp://127.0.0.1:6667")
time.sleep(0.2)
rep.connect("tcp://127.0.0.1:6666")
time.sleep(1)

line()
print("disconnect rep")
rep.disconnect("tcp://127.0.0.1:6667")
time.sleep(1)
rep.disconnect("tcp://127.0.0.1:6666")
time.sleep(1)

line()
print("close rep")
rep.close()
time.sleep(1)

line()
print("close req")
req.close()
time.sleep(1)

line()
print("joining")
t.join()

print("END")
ctx.term()

########NEW FILE########
__FILENAME__ = pair
"""A thorough test of polling PAIR sockets."""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import time
import zmq

print "Running polling tests for PAIR sockets..."

addr = 'tcp://127.0.0.1:5555'
ctx = zmq.Context()
s1 = ctx.socket(zmq.PAIR)
s2 = ctx.socket(zmq.PAIR)

s1.bind(addr)
s2.connect(addr)

# Sleep to allow sockets to connect.
time.sleep(1.0)

poller = zmq.Poller()
poller.register(s1, zmq.POLLIN|zmq.POLLOUT)
poller.register(s2, zmq.POLLIN|zmq.POLLOUT)

# Now make sure that both are send ready.
socks = dict(poller.poll())
assert socks[s1] == zmq.POLLOUT
assert socks[s2] == zmq.POLLOUT

# Now do a send on both, wait and test for zmq.POLLOUT|zmq.POLLIN
s1.send('msg1')
s2.send('msg2')
time.sleep(1.0)
socks = dict(poller.poll())
assert socks[s1] == zmq.POLLOUT|zmq.POLLIN
assert socks[s2] == zmq.POLLOUT|zmq.POLLIN

# Make sure that both are in POLLOUT after recv.
s1.recv()
s2.recv()
socks = dict(poller.poll())
assert socks[s1] == zmq.POLLOUT
assert socks[s2] == zmq.POLLOUT

poller.unregister(s1)
poller.unregister(s2)

# Wait for everything to finish.
time.sleep(1.0)

print "Finished."
########NEW FILE########
__FILENAME__ = pubsub
"""A thorough test of polling PUB/SUB sockets."""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import time
import zmq

print "Running polling tets for PUB/SUB sockets..."

addr = 'tcp://127.0.0.1:5555'
ctx = zmq.Context()
s1 = ctx.socket(zmq.PUB)
s2 = ctx.socket(zmq.SUB)
s2.setsockopt(zmq.SUBSCRIBE, '')

s1.bind(addr)
s2.connect(addr)

# Sleep to allow sockets to connect.
time.sleep(1.0)

poller = zmq.Poller()
poller.register(s1, zmq.POLLIN|zmq.POLLOUT)
poller.register(s2, zmq.POLLIN|zmq.POLLOUT)

# Now make sure that both are send ready.
socks = dict(poller.poll())
assert socks[s1] == zmq.POLLOUT
assert not socks.has_key(s2)

# Make sure that s1 stays in POLLOUT after a send.
s1.send('msg1')
socks = dict(poller.poll())
assert socks[s1] == zmq.POLLOUT

# Make sure that s2 is POLLIN after waiting.
time.sleep(0.5)
socks = dict(poller.poll())
assert socks[s2] == zmq.POLLIN

# Make sure that s2 goes into 0 after recv.
s2.recv()
socks = dict(poller.poll())
assert not socks.has_key(s2)

poller.unregister(s1)
poller.unregister(s2)

# Wait for everything to finish.
time.sleep(1.0)

print "Finished."

########NEW FILE########
__FILENAME__ = reqrep
"""A thorough test of polling REQ/REP sockets."""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import time
import zmq

print "Running polling tests for REQ/REP sockets..."

addr = 'tcp://127.0.0.1:5555'
ctx = zmq.Context()
s1 = ctx.socket(zmq.REP)
s2 = ctx.socket(zmq.REQ)

s1.bind(addr)
s2.connect(addr)

# Sleep to allow sockets to connect.
time.sleep(1.0)

poller = zmq.Poller()
poller.register(s1, zmq.POLLIN|zmq.POLLOUT)
poller.register(s2, zmq.POLLIN|zmq.POLLOUT)

# Make sure that s1 is in state 0 and s2 is in POLLOUT
socks = dict(poller.poll())
assert not socks.has_key(s1)
assert socks[s2] == zmq.POLLOUT

# Make sure that s2 goes immediately into state 0 after send.
s2.send('msg1')
socks = dict(poller.poll())
assert not socks.has_key(s2)

# Make sure that s1 goes into POLLIN state after a time.sleep().
time.sleep(0.5)
socks = dict(poller.poll())
assert socks[s1] == zmq.POLLIN

# Make sure that s1 goes into POLLOUT after recv.
s1.recv()
socks = dict(poller.poll())
assert socks[s1] == zmq.POLLOUT

# Make sure s1 goes into state 0 after send.
s1.send('msg2')
socks = dict(poller.poll())
assert not socks.has_key(s1)

# Wait and then see that s2 is in POLLIN.
time.sleep(0.5)
socks = dict(poller.poll())
assert socks[s2] == zmq.POLLIN

# Make sure that s2 is in POLLOUT after recv.
s2.recv()
socks = dict(poller.poll())
assert socks[s2] == zmq.POLLOUT

poller.unregister(s1)
poller.unregister(s2)

# Wait for everything to finish.
time.sleep(1.0)

print "Finished."

########NEW FILE########
__FILENAME__ = publisher
"""A test that publishes NumPy arrays.

Uses REQ/REP (on PUB/SUB socket + 1) to synchronize
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import sys
import time

import zmq
import numpy

def sync(bind_to):
    # use bind socket + 1
    sync_with = ':'.join(bind_to.split(':')[:-1] +
                         [str(int(bind_to.split(':')[-1]) + 1)])
    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REP)
    s.bind(sync_with)
    print "Waiting for subscriber to connect..."
    s.recv()
    print "   Done."
    s.send('GO')

def main():
    if len (sys.argv) != 4:
        print 'usage: publisher <bind-to> <array-size> <array-count>'
        sys.exit (1)

    try:
        bind_to = sys.argv[1]
        array_size = int(sys.argv[2])
        array_count = int (sys.argv[3])
    except (ValueError, OverflowError), e:
        print 'array-size and array-count must be integers'
        sys.exit (1)

    ctx = zmq.Context()
    s = ctx.socket(zmq.PUB)
    s.bind(bind_to)

    sync(bind_to)

    print "Sending arrays..."
    for i in range(array_count):
        a = numpy.random.rand(array_size, array_size)
        s.send_pyobj(a)
    print "   Done."

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = subscriber
"""A test that subscribes to NumPy arrays.

Uses REQ/REP (on PUB/SUB socket + 1) to synchronize
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------


import sys
import time

import zmq
import numpy

def sync(connect_to):
    # use connect socket + 1
    sync_with = ':'.join(connect_to.split(':')[:-1] +
                         [str(int(connect_to.split(':')[-1]) + 1)]
                        )
    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REQ)
    s.connect(sync_with)
    s.send('READY')
    s.recv()

def main():
    if len (sys.argv) != 3:
        print 'usage: subscriber <connect_to> <array-count>'
        sys.exit (1)

    try:
        connect_to = sys.argv[1]
        array_count = int (sys.argv[2])
    except (ValueError, OverflowError), e:
        print 'array-count must be integers'
        sys.exit (1)

    ctx = zmq.Context()
    s = ctx.socket(zmq.SUB)
    s.connect(connect_to)
    s.setsockopt(zmq.SUBSCRIBE,'')

    sync(connect_to)

    start = time.clock()

    print "Receiving arrays..."
    for i in range(array_count):
        a = s.recv_pyobj()
    print "   Done."

    end = time.clock()

    elapsed = (end - start) * 1000000
    if elapsed == 0:
    	elapsed = 1
    throughput = (1000000.0 * float (array_count)) / float (elapsed)
    message_size = a.nbytes
    megabits = float (throughput * message_size * 8) / 1000000

    print "message size: %.0f [B]" % (message_size, )
    print "array count: %.0f" % (array_count, )
    print "mean throughput: %.0f [msg/s]" % (throughput, )
    print "mean throughput: %.3f [Mb/s]" % (megabits, )

    time.sleep(1.0)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = topics_pub
#!/usr/bin/env python
"""Simple example of publish/subscribe illustrating topics.

Publisher and subscriber can be started in any order, though if publisher
starts first, any messages sent before subscriber starts are lost.  More than
one subscriber can listen, and they can listen to  different topics.

Topic filtering is done simply on the start of the string, e.g. listening to
's' will catch 'sports...' and 'stocks'  while listening to 'w' is enough to
catch 'weather'.
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import itertools
import sys
import time

import zmq

def main():
    if len (sys.argv) != 2:
        print 'usage: publisher <bind-to>'
        sys.exit (1)

    bind_to = sys.argv[1]

    all_topics = ['sports.general','sports.football','sports.basketball',
                  'stocks.general','stocks.GOOG','stocks.AAPL',
                  'weather']

    ctx = zmq.Context()
    s = ctx.socket(zmq.PUB)
    s.bind(bind_to)

    print "Starting broadcast on topics:"
    print "   %s" % all_topics
    print "Hit Ctrl-C to stop broadcasting."
    print "Waiting so subscriber sockets can connect..."
    print
    time.sleep(1.0)

    msg_counter = itertools.count()
    try:
        for topic in itertools.cycle(all_topics):
            msg_body = str(msg_counter.next())
            print '   Topic: %s, msg:%s' % (topic, msg_body)
            s.send_multipart([topic, msg_body])
            # short wait so we don't hog the cpu
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    print "Waiting for message queues to flush..."
    time.sleep(0.5)
    print "Done."

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = topics_sub
#!/usr/bin/env python
"""Simple example of publish/subscribe illustrating topics.

Publisher and subscriber can be started in any order, though if publisher
starts first, any messages sent before subscriber starts are lost.  More than
one subscriber can listen, and they can listen to  different topics.

Topic filtering is done simply on the start of the string, e.g. listening to
's' will catch 'sports...' and 'stocks'  while listening to 'w' is enough to
catch 'weather'.
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger, Fernando Perez
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import sys
import time

import zmq
import numpy

def main():
    if len (sys.argv) < 2:
        print 'usage: subscriber <connect_to> [topic topic ...]'
        sys.exit (1)

    connect_to = sys.argv[1]
    topics = sys.argv[2:]

    ctx = zmq.Context()
    s = ctx.socket(zmq.SUB)
    s.connect(connect_to)

    # manage subscriptions
    if not topics:
        print "Receiving messages on ALL topics..."
        s.setsockopt(zmq.SUBSCRIBE,'')
    else:
        print "Receiving messages on topics: %s ..." % topics
        for t in topics:
            s.setsockopt(zmq.SUBSCRIBE,t)
    print
    try:
        while True:
            topic, msg = s.recv_multipart()
            print '   Topic: %s, msg:%s' % (topic, msg)
    except KeyboardInterrupt:
        pass
    print "Done."

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = generate_certificates
#!/usr/bin/env python

"""
Generate client and server CURVE certificate files then move them into the
appropriate store directory, private_keys or public_keys. The certificates
generated by this script are used by the stonehouse and ironhouse examples.

In practice this would be done by hand or some out-of-band process.

Author: Chris Laws
"""

import os
import shutil
import zmq.auth

def generate_certificates(base_dir):
    ''' Generate client and server CURVE certificate files'''
    keys_dir = os.path.join(base_dir, 'certificates')
    public_keys_dir = os.path.join(base_dir, 'public_keys')
    secret_keys_dir = os.path.join(base_dir, 'private_keys')

    # Create directories for certificates, remove old content if necessary
    for d in [keys_dir, public_keys_dir, secret_keys_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.mkdir(d)

    # create new keys in certificates dir
    server_public_file, server_secret_file = zmq.auth.create_certificates(keys_dir, "server")
    client_public_file, client_secret_file = zmq.auth.create_certificates(keys_dir, "client")

    # move public keys to appropriate directory
    for key_file in os.listdir(keys_dir):
        if key_file.endswith(".key"):
            shutil.move(os.path.join(keys_dir, key_file),
                        os.path.join(public_keys_dir, '.'))

    # move secret keys to appropriate directory
    for key_file in os.listdir(keys_dir):
        if key_file.endswith(".key_secret"):
            shutil.move(os.path.join(keys_dir, key_file),
                        os.path.join(secret_keys_dir, '.'))

if __name__ == '__main__':
    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

    generate_certificates(os.path.dirname(__file__))

########NEW FILE########
__FILENAME__ = grasslands
#!/usr/bin/env python

'''
No protection at all.

All connections are accepted, there is no authentication, and no privacy. 

This is how ZeroMQ always worked until we built security into the wire 
protocol in early 2013. Internally, it uses a security mechanism called 
"NULL".

Author: Chris Laws
'''

import zmq


ctx = zmq.Context().instance()

server = ctx.socket(zmq.PUSH)
server.bind('tcp://*:9000')

client = ctx.socket(zmq.PULL)
client.connect('tcp://127.0.0.1:9000')

server.send(b"Hello")
msg = client.recv()
if msg == b"Hello":
    print("Grasslands test OK")

########NEW FILE########
__FILENAME__ = ioloop-ironhouse
#!/usr/bin/env python

'''
Ironhouse extends Stonehouse with client public key authentication.

This is the strongest security model we have today, protecting against every
attack we know about, except end-point attacks (where an attacker plants
spyware on a machine to capture data before it's encrypted, or after it's
decrypted).

This example demonstrates using the IOLoopAuthenticator.

Author: Chris Laws
'''

import logging
import os
import sys

import zmq
import zmq.auth
from zmq.auth.ioloop import IOLoopAuthenticator
from zmq.eventloop import ioloop, zmqstream

def echo(server, msg):
    logging.debug("server recvd %s", msg)
    reply = msg + [b'World']
    logging.debug("server sending %s", reply)
    server.send_multipart(reply)
    
def setup_server(server_secret_file, endpoint='tcp://127.0.0.1:9000'):
    """setup a simple echo server with CURVE auth"""
    server = zmq.Context.instance().socket(zmq.ROUTER)

    server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
    server.curve_secretkey = server_secret
    server.curve_publickey = server_public
    server.curve_server = True  # must come before bind
    server.bind(endpoint)
    
    server_stream = zmqstream.ZMQStream(server)
    # simple echo
    server_stream.on_recv_stream(echo)
    return server_stream

def client_msg_recvd(msg):
    logging.debug("client recvd %s", msg)
    logging.info("Ironhouse test OK")
    # stop the loop when we get the reply
    ioloop.IOLoop.instance().stop()

def setup_client(client_secret_file, server_public_file, endpoint='tcp://127.0.0.1:9000'):
    """setup a simple client with CURVE auth"""
    
    client = zmq.Context.instance().socket(zmq.DEALER)

    # We need two certificates, one for the client and one for
    # the server. The client must know the server's public key
    # to make a CURVE connection.
    client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
    client.curve_secretkey = client_secret
    client.curve_publickey = client_public

    server_public, _ = zmq.auth.load_certificate(server_public_file)
    # The client must know the server's public key to make a CURVE connection.
    client.curve_serverkey = server_public
    client.connect(endpoint)
    
    client_stream = zmqstream.ZMQStream(client)
    client_stream.on_recv(client_msg_recvd)
    return client_stream
    

def run():
    '''Run Ironhouse example'''

    # These direcotries are generated by the generate_certificates script
    base_dir = os.path.dirname(__file__)
    keys_dir = os.path.join(base_dir, 'certificates')
    public_keys_dir = os.path.join(base_dir, 'public_keys')
    secret_keys_dir = os.path.join(base_dir, 'private_keys')

    if not (os.path.exists(keys_dir) and os.path.exists(keys_dir) and os.path.exists(keys_dir)):
        logging.critical("Certificates are missing - run generate_certificates script first")
        sys.exit(1)

    # Start an authenticator for this context.
    auth = IOLoopAuthenticator()
    auth.allow('127.0.0.1')
    # Tell authenticator to use the certificate in a directory
    auth.configure_curve(domain='*', location=public_keys_dir)
    
    server_secret_file = os.path.join(secret_keys_dir, "server.key_secret")
    server = setup_server(server_secret_file)
    server_public_file = os.path.join(public_keys_dir, "server.key")
    client_secret_file = os.path.join(secret_keys_dir, "client.key_secret")
    client = setup_client(client_secret_file, server_public_file)
    client.send(b'Hello')
    
    auth.start()
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

    if '-v' in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    run()

########NEW FILE########
__FILENAME__ = ironhouse
#!/usr/bin/env python

'''
Ironhouse extends Stonehouse with client public key authentication.

This is the strongest security model we have today, protecting against every
attack we know about, except end-point attacks (where an attacker plants
spyware on a machine to capture data before it's encrypted, or after it's
decrypted).

Author: Chris Laws
'''

import logging
import os
import sys

import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator


def run():
    ''' Run Ironhouse example '''

    # These direcotries are generated by the generate_certificates script
    base_dir = os.path.dirname(__file__)
    keys_dir = os.path.join(base_dir, 'certificates')
    public_keys_dir = os.path.join(base_dir, 'public_keys')
    secret_keys_dir = os.path.join(base_dir, 'private_keys')

    if not (os.path.exists(keys_dir) and os.path.exists(keys_dir) and os.path.exists(keys_dir)):
        logging.critical("Certificates are missing - run generate_certificates.py script first")
        sys.exit(1)

    ctx = zmq.Context().instance()

    # Start an authenticator for this context.
    auth = ThreadAuthenticator(ctx)
    auth.start()
    auth.allow('127.0.0.1')
    # Tell authenticator to use the certificate in a directory
    auth.configure_curve(domain='*', location=public_keys_dir)

    server = ctx.socket(zmq.PUSH)

    server_secret_file = os.path.join(secret_keys_dir, "server.key_secret")
    server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
    server.curve_secretkey = server_secret
    server.curve_publickey = server_public
    server.curve_server = True  # must come before bind
    server.bind('tcp://*:9000')

    client = ctx.socket(zmq.PULL)

    # We need two certificates, one for the client and one for
    # the server. The client must know the server's public key
    # to make a CURVE connection.
    client_secret_file = os.path.join(secret_keys_dir, "client.key_secret")
    client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
    client.curve_secretkey = client_secret
    client.curve_publickey = client_public

    server_public_file = os.path.join(public_keys_dir, "server.key")
    server_public, _ = zmq.auth.load_certificate(server_public_file)
    # The client must know the server's public key to make a CURVE connection.
    client.curve_serverkey = server_public
    client.connect('tcp://127.0.0.1:9000')

    server.send(b"Hello")

    if client.poll(1000):
        msg = client.recv()
        if msg == b"Hello":
            logging.info("Ironhouse test OK")
    else:
        logging.error("Ironhouse test FAIL")

    # stop auth thread
    auth.stop()

if __name__ == '__main__':
    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

    if '-v' in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    run()

########NEW FILE########
__FILENAME__ = stonehouse
#!/usr/bin/env python

'''
Stonehouse uses the "CURVE" security mechanism.

This gives us strong encryption on data, and (as far as we know) unbreakable
authentication. Stonehouse is the minimum you would use over public networks,
and assures clients that they are speaking to an authentic server, while
allowing any client to connect.

Author: Chris Laws
'''

import logging
import os
import sys
import time

import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator


def run():
    ''' Run Stonehouse example '''

    # These directories are generated by the generate_certificates script
    base_dir = os.path.dirname(__file__)
    keys_dir = os.path.join(base_dir, 'certificates')
    public_keys_dir = os.path.join(base_dir, 'public_keys')
    secret_keys_dir = os.path.join(base_dir, 'private_keys')

    if not (os.path.exists(keys_dir) and os.path.exists(keys_dir) and os.path.exists(keys_dir)):
        logging.critical("Certificates are missing: run generate_certificates.py script first")
        sys.exit(1)

    ctx = zmq.Context().instance()

    # Start an authenticator for this context.
    auth = ThreadAuthenticator(ctx)
    auth.start()
    auth.allow('127.0.0.1')
    # Tell the authenticator how to handle CURVE requests
    auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)

    server = ctx.socket(zmq.PUSH)
    server_secret_file = os.path.join(secret_keys_dir, "server.key_secret")
    server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
    server.curve_secretkey = server_secret
    server.curve_publickey = server_public
    server.curve_server = True  # must come before bind
    server.bind('tcp://*:9000')

    client = ctx.socket(zmq.PULL)
    # We need two certificates, one for the client and one for
    # the server. The client must know the server's public key
    # to make a CURVE connection.
    client_secret_file = os.path.join(secret_keys_dir, "client.key_secret")
    client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
    client.curve_secretkey = client_secret
    client.curve_publickey = client_public

    # The client must know the server's public key to make a CURVE connection.
    server_public_file = os.path.join(public_keys_dir, "server.key")
    server_public, _ = zmq.auth.load_certificate(server_public_file)
    client.curve_serverkey = server_public

    client.connect('tcp://127.0.0.1:9000')

    server.send(b"Hello")

    if client.poll(1000):
        msg = client.recv()
        if msg == b"Hello":
            logging.info("Stonehouse test OK")
    else:
        logging.error("Stonehouse test FAIL")

    # stop auth thread
    auth.stop()

if __name__ == '__main__':
    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

    if '-v' in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    run()

########NEW FILE########
__FILENAME__ = strawhouse
#!/usr/bin/env python

'''
Allow or deny clients based on IP address.

Strawhouse, which is plain text with filtering on IP addresses. It still
uses the NULL mechanism, but we install an authentication hook that checks
the IP address against a whitelist or blacklist and allows or denies it
accordingly.

Author: Chris Laws
'''

import logging
import sys

import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator


def run():
    '''Run strawhouse client'''

    allow_test_pass = False
    deny_test_pass = False

    ctx = zmq.Context().instance()

    # Start an authenticator for this context.
    auth = ThreadAuthenticator(ctx)
    auth.start()

    # Part 1 - demonstrate allowing clients based on IP address
    auth.allow('127.0.0.1')

    server = ctx.socket(zmq.PUSH)
    server.zap_domain = b'global'  # must come before bind
    server.bind('tcp://*:9000')

    client_allow = ctx.socket(zmq.PULL)
    client_allow.connect('tcp://127.0.0.1:9000')

    server.send(b"Hello")

    msg = client_allow.recv()
    if msg == b"Hello":
        allow_test_pass = True

    client_allow.close()

    # Part 2 - demonstrate denying clients based on IP address
    auth.stop()
    
    auth = ThreadAuthenticator(ctx)
    auth.start()
    
    auth.deny('127.0.0.1')

    client_deny = ctx.socket(zmq.PULL)
    client_deny.connect('tcp://127.0.0.1:9000')
    
    if server.poll(50, zmq.POLLOUT):
        server.send(b"Hello")

        if client_deny.poll(50):
            msg = client_deny.recv()
        else:
            deny_test_pass = True
    else:
        deny_test_pass = True

    client_deny.close()

    auth.stop()  # stop auth thread

    if allow_test_pass and deny_test_pass:
        logging.info("Strawhouse test OK")
    else:
        logging.error("Strawhouse test FAIL")


if __name__ == '__main__':
    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

    if '-v' in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    run()

########NEW FILE########
__FILENAME__ = woodhouse
#!/usr/bin/env python

'''
Woodhouse extends Strawhouse with a name and password check.

This uses the PLAIN mechanism which does plain-text username and password authentication).
It's not really secure, and anyone sniffing the network (trivial with WiFi)
can capture passwords and then login.

Author: Chris Laws
'''

import logging
import sys

import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator

def run():
    '''Run woodhouse example'''

    valid_client_test_pass = False
    invalid_client_test_pass = False

    ctx = zmq.Context().instance()

    # Start an authenticator for this context.
    auth = ThreadAuthenticator(ctx)
    auth.start()
    auth.allow('127.0.0.1')
    # Instruct authenticator to handle PLAIN requests
    auth.configure_plain(domain='*', passwords={'admin': 'secret'})

    server = ctx.socket(zmq.PUSH)
    server.plain_server = True  # must come before bind
    server.bind('tcp://*:9000')

    client = ctx.socket(zmq.PULL)
    client.plain_username = b'admin'
    client.plain_password = b'secret'
    client.connect('tcp://127.0.0.1:9000')

    server.send(b"Hello")

    if client.poll():
        msg = client.recv()
        if msg == b"Hello":
            valid_client_test_pass = True

    client.close()


    # now use invalid credentials - expect no msg received
    client2 = ctx.socket(zmq.PULL)
    client2.plain_username = b'admin'
    client2.plain_password = b'bogus'
    client2.connect('tcp://127.0.0.1:9000')

    server.send(b"World")

    if client2.poll(50):
        msg = client.recv()
        if msg == "World":
            invalid_client_test_pass = False
    else:
        # no message is expected
        invalid_client_test_pass = True

    # stop auth thread
    auth.stop()

    if valid_client_test_pass and invalid_client_test_pass:
        logging.info("Woodhouse test OK")
    else:
        logging.error("Woodhouse test FAIL")


if __name__ == '__main__':
    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

    if '-v' in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    run()

########NEW FILE########
__FILENAME__ = serialsocket
"""A Socket subclass that adds some serialization methods."""

import zlib
import pickle

import numpy

import zmq

class SerializingSocket(zmq.Socket):
    """A class with some extra serialization methods
    
    send_zipped_pickle is just like send_pyobj, but uses
    zlib to compress the stream before sending.
    
    send_array sends numpy arrays with metadata necessary
    for reconstructing the array on the other side (dtype,shape).
    """
    
    def send_zipped_pickle(self, obj, flags=0, protocol=-1):
        """pack and compress an object with pickle and zlib."""
        pobj = pickle.dumps(obj, protocol)
        zobj = zlib.compress(pobj)
        print('zipped pickle is %i bytes' % len(zobj))
        return self.send(zobj, flags=flags)
    
    def recv_zipped_pickle(self, flags=0):
        """reconstruct a Python object sent with zipped_pickle"""
        zobj = self.recv(flags)
        pobj = zlib.decompress(zobj)
        return pickle.loads(pobj)

    def send_array(self, A, flags=0, copy=True, track=False):
        """send a numpy array with metadata"""
        md = dict(
            dtype = str(A.dtype),
            shape = A.shape,
        )
        self.send_json(md, flags|zmq.SNDMORE)
        return self.send(A, flags, copy=copy, track=track)

    def recv_array(self, flags=0, copy=True, track=False):
        """recv a numpy array"""
        md = self.recv_json(flags=flags)
        msg = self.recv(flags=flags, copy=copy, track=track)
        A = numpy.frombuffer(msg, dtype=md['dtype'])
        return A.reshape(md['shape'])

class SerializingContext(zmq.Context):
    _socket_class = SerializingSocket

def main():
    ctx = SerializingContext()
    req = ctx.socket(zmq.REQ)
    rep = ctx.socket(zmq.REP)
    
    rep.bind('inproc://a')
    req.connect('inproc://a')
    A = numpy.ones((1024,1024))
    print ("Array is %i bytes" % (len(A) * 8))
    
    # send/recv with pickle+zip
    req.send_zipped_pickle(A)
    B = rep.recv_zipped_pickle()
    # now try non-copying version
    rep.send_array(A, copy=False)
    C = req.recv_array(copy=False)
    print ("Checking zipped pickle...")
    print ("Okay" if (A==B).all() else "Failed")
    print ("Checking send_array...")
    print ("Okay" if (C==B).all() else "Failed")

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = perf
#!/usr/bin/env python
# coding: utf-8
#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
# 
#
#  Some original test code Copyright (c) 2007-2010 iMatix Corporation,
#  Used under LGPLv3
#-----------------------------------------------------------------------------

import argparse
import time

from multiprocessing import Process

import zmq

def parse_args(argv=None):

    parser = argparse.ArgumentParser(description='Run a zmq performance test')
    parser.add_argument('-p', '--poll', action='store_true',
                       help='use a zmq Poller instead of raw send/recv')
    parser.add_argument('-c', '--copy', action='store_true',
                       help='copy messages instead of using zero-copy')
    parser.add_argument('-s', '--size', type=int, default=10240,
                       help='size (in bytes) of the test message')
    parser.add_argument('-n', '--count', type=int, default=10240,
                       help='number of test messages to send')
    parser.add_argument('--url', dest='url', type=str, default='tcp://127.0.0.1:5555',
                       help='the zmq URL on which to run the test')
    parser.add_argument(dest='test', type=str, default='lat', choices=['lat', 'thr'],
                       help='which test to run')
    return parser.parse_args(argv)

def latency_echo(url, count, poll, copy):
    """echo messages on a REP socket
    
    Should be started before `latency`
    """
    ctx = zmq.Context()
    s = ctx.socket(zmq.REP)

    if poll:
        p = zmq.Poller()
        p.register(s)

    s.bind(url)
    
    block = zmq.NOBLOCK if poll else 0
    
    for i in range(count):
        if poll:
            res = p.poll()
        msg = s.recv(block, copy=copy)

        if poll:
            res = p.poll()
        s.send(msg, block, copy=copy)
    
    msg = s.recv()
    assert msg == b'done'
    
    s.close()
    ctx.term()
    
def latency(url, count, size, poll, copy):
    """Perform a latency test"""
    ctx = zmq.Context()
    s = ctx.socket(zmq.REQ)
    s.setsockopt(zmq.LINGER, -1)
    s.connect(url)
    if poll:
        p = zmq.Poller()
        p.register(s)

    msg = b' ' * size

    watch = zmq.Stopwatch()

    block = zmq.NOBLOCK if poll else 0
    time.sleep(1)
    watch.start()

    for i in range (0, count):
        if poll:
            res = p.poll()
            assert(res[0][1] & zmq.POLLOUT)
        s.send(msg, block, copy=copy)

        if poll:
            res = p.poll()
            assert(res[0][1] & zmq.POLLIN)
        msg = s.recv(block, copy=copy)
        
        assert len(msg) == size

    elapsed = watch.stop()

    s.send(b'done')

    latency = elapsed / (count * 2.)

    print ("message size   : %8i     [B]" % (size, ))
    print ("roundtrip count: %8i     [msgs]" % (count, ))
    print ("mean latency   : %12.3f [µs]" % (latency, ))
    print ("test time      : %12.3f [s]" % (elapsed * 1e-6, ))

def pusher(url, count, size, copy, poll):
    """send a bunch of messages on a PUSH socket"""
    ctx = zmq.Context()
    s = ctx.socket(zmq.PUSH)

    #  Add your socket options here.
    #  For example ZMQ_RATE, ZMQ_RECOVERY_IVL and ZMQ_MCAST_LOOP for PGM.

    if poll:
        p = zmq.Poller()
        p.register(s)

    s.connect(url)
    
    msg = zmq.Message(b' ' * size)
    block = zmq.NOBLOCK if poll else 0
    
    for i in range(count):
        if poll:
            res = p.poll()
            assert(res[0][1] & zmq.POLLOUT)
        s.send(msg, block, copy=copy)

    s.close()
    ctx.term()

def throughput(url, count, size, poll, copy):
    """recv a bunch of messages on a PULL socket
    
    Should be started before `pusher`
    """
    ctx = zmq.Context()
    s = ctx.socket(zmq.PULL)

    #  Add your socket options here.
    #  For example ZMQ_RATE, ZMQ_RECOVERY_IVL and ZMQ_MCAST_LOOP for PGM.

    if poll:
        p = zmq.Poller()
        p.register(s)

    s.bind(url)

    watch = zmq.Stopwatch()
    block = zmq.NOBLOCK if poll else 0
    
    # Wait for the other side to connect.
    msg = s.recv()
    assert len (msg) == size
    
    watch.start()
    for i in range (count-1):
        if poll:
            res = p.poll()
        msg = s.recv(block, copy=copy)
    elapsed = watch.stop()
    if elapsed == 0:
        elapsed = 1
    
    throughput = (1e6 * float(count)) / float(elapsed)
    megabits = float(throughput * size * 8) / 1e6

    print ("message size   : %8i     [B]" % (size, ))
    print ("message count  : %8i     [msgs]" % (count, ))
    print ("mean throughput: %8.0f     [msg/s]" % (throughput, ))
    print ("mean throughput: %12.3f [Mb/s]" % (megabits, ))
    print ("test time      : %12.3f [s]" % (elapsed * 1e-6, ))


def main():
    args = parse_args()
    tic = time.time()
    if args.test == 'lat':
        bg = Process(target=latency_echo, args=(args.url, args.count, args.poll, args.copy))
        bg.start()
        latency(args.url, args.count, args.size, args.poll, args.copy)
    elif args.test == 'thr':
        bg = Process(target=throughput, args=(args.url, args.count, args.size, args.poll, args.copy))
        bg.start()
        pusher(args.url, args.count, args.size, args.poll, args.copy)
    bg.join()
    toc = time.time()
    if (toc - tic) < 3:
        print ("For best results, tests should take at least a few seconds.")

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = base
"""Base implementation of 0MQ authentication."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import logging

import zmq
from zmq.utils import z85
from zmq.utils.strtypes import bytes, unicode, b, u
from zmq.error import _check_version

from .certs import load_certificates


CURVE_ALLOW_ANY = '*'
VERSION = b'1.0'

class Authenticator(object):
    """Implementation of ZAP authentication for zmq connections.

    Note:
    - libzmq provides four levels of security: default NULL (which the Authenticator does
      not see), and authenticated NULL, PLAIN, and CURVE, which the Authenticator can see.
    - until you add policies, all incoming NULL connections are allowed
    (classic ZeroMQ behavior), and all PLAIN and CURVE connections are denied.
    """

    def __init__(self, context=None, encoding='utf-8', log=None):
        _check_version((4,0), "security")
        self.context = context or zmq.Context.instance()
        self.encoding = encoding
        self.allow_any = False
        self.zap_socket = None
        self.whitelist = set()
        self.blacklist = set()
        # passwords is a dict keyed by domain and contains values
        # of dicts with username:password pairs.
        self.passwords = {}
        # certs is dict keyed by domain and contains values
        # of dicts keyed by the public keys from the specified location.
        self.certs = {}
        self.log = log or logging.getLogger('zmq.auth')
    
    def start(self):
        """Create and bind the ZAP socket"""
        self.zap_socket = self.context.socket(zmq.REP)
        self.zap_socket.linger = 1
        self.zap_socket.bind("inproc://zeromq.zap.01")

    def stop(self):
        """Close the ZAP socket"""
        if self.zap_socket:
            self.zap_socket.close()
        self.zap_socket = None

    def allow(self, *addresses):
        """Allow (whitelist) IP address(es).
        
        Connections from addresses not in the whitelist will be rejected.
        
        - For NULL, all clients from this address will be accepted.
        - For PLAIN and CURVE, they will be allowed to continue with authentication.
        
        whitelist is mutually exclusive with blacklist.
        """
        if self.blacklist:
            raise ValueError("Only use a whitelist or a blacklist, not both")
        self.whitelist.update(addresses)

    def deny(self, *addresses):
        """Deny (blacklist) IP address(es).
        
        Addresses not in the blacklist will be allowed to continue with authentication.
        
        Blacklist is mutually exclusive with whitelist.
        """
        if self.whitelist:
            raise ValueError("Only use a whitelist or a blacklist, not both")
        self.blacklist.update(addresses)

    def configure_plain(self, domain='*', passwords=None):
        """Configure PLAIN authentication for a given domain.
        
        PLAIN authentication uses a plain-text password file.
        To cover all domains, use "*".
        You can modify the password file at any time; it is reloaded automatically.
        """
        if passwords:
            self.passwords[domain] = passwords

    def configure_curve(self, domain='*', location=None):
        """Configure CURVE authentication for a given domain.
        
        CURVE authentication uses a directory that holds all public client certificates,
        i.e. their public keys.
        
        To cover all domains, use "*".
        
        You can add and remove certificates in that directory at any time.
        
        To allow all client keys without checking, specify CURVE_ALLOW_ANY for the location.
        """
        # If location is CURVE_ALLOW_ANY then allow all clients. Otherwise
        # treat location as a directory that holds the certificates.
        if location == CURVE_ALLOW_ANY:
            self.allow_any = True
        else:
            self.allow_any = False
            try:
                self.certs[domain] = load_certificates(location)
            except Exception as e:
                self.log.error("Failed to load CURVE certs from %s: %s", location, e)

    def handle_zap_message(self, msg):
        """Perform ZAP authentication"""
        if len(msg) < 6:
            self.log.error("Invalid ZAP message, not enough frames: %r", msg)
            if len(msg) < 2:
                self.log.error("Not enough information to reply")
            else:
                self._send_zap_reply(msg[1], b"400", b"Not enough frames")
            return
        
        version, request_id, domain, address, identity, mechanism = msg[:6]
        credentials = msg[6:]
        
        domain = u(domain, self.encoding, 'replace')
        address = u(address, self.encoding, 'replace')

        if (version != VERSION):
            self.log.error("Invalid ZAP version: %r", msg)
            self._send_zap_reply(request_id, b"400", b"Invalid version")
            return

        self.log.debug("version: %r, request_id: %r, domain: %r,"
                      " address: %r, identity: %r, mechanism: %r",
                      version, request_id, domain,
                      address, identity, mechanism,
        )


        # Is address is explicitly whitelisted or blacklisted?
        allowed = False
        denied = False
        reason = b"NO ACCESS"

        if self.whitelist:
            if address in self.whitelist:
                allowed = True
                self.log.debug("PASSED (whitelist) address=%s", address)
            else:
                denied = True
                reason = b"Address not in whitelist"
                self.log.debug("DENIED (not in whitelist) address=%s", address)

        elif self.blacklist:
            if address in self.blacklist:
                denied = True
                reason = b"Address is blacklisted"
                self.log.debug("DENIED (blacklist) address=%s", address)
            else:
                allowed = True
                self.log.debug("PASSED (not in blacklist) address=%s", address)

        # Perform authentication mechanism-specific checks if necessary
        username = u("user")
        if not denied:

            if mechanism == b'NULL' and not allowed:
                # For NULL, we allow if the address wasn't blacklisted
                self.log.debug("ALLOWED (NULL)")
                allowed = True

            elif mechanism == b'PLAIN':
                # For PLAIN, even a whitelisted address must authenticate
                if len(credentials) != 2:
                    self.log.error("Invalid PLAIN credentials: %r", credentials)
                    self._send_zap_reply(request_id, b"400", b"Invalid credentials")
                    return
                username, password = [ u(c, self.encoding, 'replace') for c in credentials ]
                allowed, reason = self._authenticate_plain(domain, username, password)

            elif mechanism == b'CURVE':
                # For CURVE, even a whitelisted address must authenticate
                if len(credentials) != 1:
                    self.log.error("Invalid CURVE credentials: %r", credentials)
                    self._send_zap_reply(request_id, b"400", b"Invalid credentials")
                    return
                key = credentials[0]
                allowed, reason = self._authenticate_curve(domain, key)

        if allowed:
            self._send_zap_reply(request_id, b"200", b"OK", username)
        else:
            self._send_zap_reply(request_id, b"400", reason)

    def _authenticate_plain(self, domain, username, password):
        """PLAIN ZAP authentication"""
        allowed = False
        reason = b""
        if self.passwords:
            # If no domain is not specified then use the default domain
            if not domain:
                domain = '*'

            if domain in self.passwords:
                if username in self.passwords[domain]:
                    if password == self.passwords[domain][username]:
                        allowed = True
                    else:
                        reason = b"Invalid password"
                else:
                    reason = b"Invalid username"
            else:
                reason = b"Invalid domain"

            if allowed:
                self.log.debug("ALLOWED (PLAIN) domain=%s username=%s password=%s",
                    domain, username, password,
                )
            else:
                self.log.debug("DENIED %s", reason)

        else:
            reason = b"No passwords defined"
            self.log.debug("DENIED (PLAIN) %s", reason)

        return allowed, reason

    def _authenticate_curve(self, domain, client_key):
        """CURVE ZAP authentication"""
        allowed = False
        reason = b""
        if self.allow_any:
            allowed = True
            reason = b"OK"
            self.log.debug("ALLOWED (CURVE allow any client)")
        else:
            # If no explicit domain is specified then use the default domain
            if not domain:
                domain = '*'

            if domain in self.certs:
                # The certs dict stores keys in z85 format, convert binary key to z85 bytes
                z85_client_key = z85.encode(client_key)
                if z85_client_key in self.certs[domain] or self.certs[domain] == b'OK':
                    allowed = True
                    reason = b"OK"
                else:
                    reason = b"Unknown key"

                status = "ALLOWED" if allowed else "DENIED"
                self.log.debug("%s (CURVE) domain=%s client_key=%s",
                    status, domain, z85_client_key,
                )
            else:
                reason = b"Unknown domain"

        return allowed, reason

    def _send_zap_reply(self, request_id, status_code, status_text, user_id='user'):
        """Send a ZAP reply to finish the authentication."""
        user_id = user_id if status_code == b'200' else b''
        if isinstance(user_id, unicode):
            user_id = user_id.encode(self.encoding, 'replace')
        metadata = b''  # not currently used
        self.log.debug("ZAP reply code=%s text=%s", status_code, status_text)
        reply = [VERSION, request_id, status_code, status_text, user_id, metadata]
        self.zap_socket.send_multipart(reply)

__all__ = ['Authenticator', 'CURVE_ALLOW_ANY']

########NEW FILE########
__FILENAME__ = certs
"""0MQ authentication related functions and classes."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------


import datetime
import glob
import io
import os
import zmq
from zmq.utils.strtypes import bytes, unicode, b, u


_cert_secret_banner = u("""#   ****  Generated on {0} by pyzmq  ****
#   ZeroMQ CURVE **Secret** Certificate
#   DO NOT PROVIDE THIS FILE TO OTHER USERS nor change its permissions.

""")

_cert_public_banner = u("""#   ****  Generated on {0} by pyzmq  ****
#   ZeroMQ CURVE Public Certificate
#   Exchange securely, or use a secure mechanism to verify the contents
#   of this file after exchange. Store public certificates in your home
#   directory, in the .curve subdirectory.

""")

def _write_key_file(key_filename, banner, public_key, secret_key=None, metadata=None, encoding='utf-8'):
    """Create a certificate file"""
    if isinstance(public_key, bytes):
        public_key = public_key.decode(encoding)
    if isinstance(secret_key, bytes):
        secret_key = secret_key.decode(encoding)
    with io.open(key_filename, 'w', encoding='utf8') as f:
        f.write(banner.format(datetime.datetime.now()))

        f.write(u('metadata\n'))
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, bytes):
                    v = v.decode(encoding)
                f.write(u("    {0} = {1}\n").format(k, v))

        f.write(u('curve\n'))
        f.write(u("    public-key = \"{0}\"\n").format(public_key))

        if secret_key:
            f.write(u("    secret-key = \"{0}\"\n").format(secret_key))


def create_certificates(key_dir, name, metadata=None):
    """Create zmq certificates.
    
    Returns the file paths to the public and secret certificate files.
    """
    public_key, secret_key = zmq.curve_keypair()
    base_filename = os.path.join(key_dir, name)
    secret_key_file = "{0}.key_secret".format(base_filename)
    public_key_file = "{0}.key".format(base_filename)
    now = datetime.datetime.now()

    _write_key_file(public_key_file,
                    _cert_public_banner.format(now),
                    public_key)

    _write_key_file(secret_key_file,
                    _cert_secret_banner.format(now),
                    public_key,
                    secret_key=secret_key,
                    metadata=metadata)

    return public_key_file, secret_key_file


def load_certificate(filename):
    """Load public and secret key from a zmq certificate.
    
    Returns (public_key, secret_key)
    
    If the certificate file only contains the public key,
    secret_key will be None.
    """
    public_key = None
    secret_key = None
    if not os.path.exists(filename):
        raise IOError("Invalid certificate file: {0}".format(filename))

    with open(filename, 'rb') as f:
        for line in f:
            line = line.strip()
            if line.startswith(b'#'):
                continue
            if line.startswith(b'public-key'):
                public_key = line.split(b"=", 1)[1].strip(b' \t\'"')
            if line.startswith(b'secret-key'):
                secret_key = line.split(b"=", 1)[1].strip(b' \t\'"')
            if public_key and secret_key:
                break
    
    return public_key, secret_key


def load_certificates(directory='.'):
    """Load public keys from all certificates in a directory"""
    certs = {}
    if not os.path.isdir(directory):
        raise IOError("Invalid certificate directory: {0}".format(directory))
    # Follow czmq pattern of public keys stored in *.key files.
    glob_string = os.path.join(directory, "*.key")
    
    cert_files = glob.glob(glob_string)
    for cert_file in cert_files:
        public_key, _ = load_certificate(cert_file)
        if public_key:
            certs[public_key] = 'OK'
    return certs

__all__ = ['create_certificates', 'load_certificate', 'load_certificates']

########NEW FILE########
__FILENAME__ = ioloop
"""ZAP Authenticator integrated with the tornado IOLoop.

.. versionadded:: 14.1
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from zmq.eventloop import ioloop, zmqstream
from .base import Authenticator


class IOLoopAuthenticator(Authenticator):
    """ZAP authentication for use in the tornado IOLoop"""

    def __init__(self, context=None, encoding='utf-8', log=None, io_loop=None):
        super(IOLoopAuthenticator, self).__init__(context)
        self.zap_stream = None
        self.io_loop = io_loop or ioloop.IOLoop.instance()

    def start(self):
        """Start ZAP authentication"""
        super(IOLoopAuthenticator, self).start()
        self.zap_stream = zmqstream.ZMQStream(self.zap_socket, self.io_loop)
        self.zap_stream.on_recv(self.handle_zap_message)

    def stop(self):
        """Stop ZAP authentication"""
        if self.zap_stream:
            self.zap_stream.close()
            self.zap_stream = None
        super(IOLoopAuthenticator, self).stop()

__all__ = ['IOLoopAuthenticator']

########NEW FILE########
__FILENAME__ = thread
"""ZAP Authenticator in a Python Thread.

.. versionadded:: 14.1
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import logging
from threading import Thread

import zmq
from zmq.utils import jsonapi
from zmq.utils.strtypes import bytes, unicode, b, u

from .base import Authenticator

class AuthenticationThread(Thread):
    """A Thread for running a zmq Authenticator
    
    This is run in the background by ThreadedAuthenticator
    """

    def __init__(self, context, endpoint, encoding='utf-8', log=None):
        super(AuthenticationThread, self).__init__()
        self.context = context or zmq.Context.instance()
        self.encoding = encoding
        self.log = log = log or logging.getLogger('zmq.auth')
        self.authenticator = Authenticator(context, encoding=encoding, log=log)

        # create a socket to communicate back to main thread.
        self.pipe = context.socket(zmq.PAIR)
        self.pipe.linger = 1
        self.pipe.connect(endpoint)

    def run(self):
        """ Start the Authentication Agent thread task """
        self.authenticator.start()
        zap = self.authenticator.zap_socket
        poller = zmq.Poller()
        poller.register(self.pipe, zmq.POLLIN)
        poller.register(zap, zmq.POLLIN)
        while True:
            try:
                socks = dict(poller.poll())
            except zmq.ZMQError:
                break  # interrupted

            if self.pipe in socks and socks[self.pipe] == zmq.POLLIN:
                terminate = self._handle_pipe()
                if terminate:
                    break

            if zap in socks and socks[zap] == zmq.POLLIN:
                self._handle_zap()

        self.pipe.close()
        self.authenticator.stop()

    def _handle_zap(self):
        """
        Handle a message from the ZAP socket.
        """
        msg = self.authenticator.zap_socket.recv_multipart()
        if not msg: return
        self.authenticator.handle_zap_message(msg)

    def _handle_pipe(self):
        """
        Handle a message from front-end API.
        """
        terminate = False

        # Get the whole message off the pipe in one go
        msg = self.pipe.recv_multipart()

        if msg is None:
            terminate = True
            return terminate

        command = msg[0]
        self.log.debug("auth received API command %r", command)

        if command == b'ALLOW':
            addresses = [u(m, self.encoding) for m in msg[1:]]
            try:
                self.authenticator.allow(*addresses)
            except Exception as e:
                self.log.exception("Failed to allow %s", addresses)

        elif command == b'DENY':
            addresses = [u(m, self.encoding) for m in msg[1:]]
            try:
                self.authenticator.deny(*addresses)
            except Exception as e:
                self.log.exception("Failed to deny %s", addresses)

        elif command == b'PLAIN':
            domain = u(msg[1], self.encoding)
            json_passwords = msg[2]
            self.authenticator.configure_plain(domain, jsonapi.loads(json_passwords))

        elif command == b'CURVE':
            # For now we don't do anything with domains
            domain = u(msg[1], self.encoding)

            # If location is CURVE_ALLOW_ANY, allow all clients. Otherwise
            # treat location as a directory that holds the certificates.
            location = u(msg[2], self.encoding)
            self.authenticator.configure_curve(domain, location)

        elif command == b'TERMINATE':
            terminate = True

        else:
            self.log.error("Invalid auth command from API: %r", command)

        return terminate

def _inherit_docstrings(cls):
    """inherit docstrings from Authenticator, so we don't duplicate them"""
    for name, method in cls.__dict__.items():
        if name.startswith('_'):
            continue
        upstream_method = getattr(Authenticator, name, None)
        if not method.__doc__:
            method.__doc__ = upstream_method.__doc__
    return cls

@_inherit_docstrings
class ThreadAuthenticator(object):
    """Run ZAP authentication in a background thread"""

    def __init__(self, context=None, encoding='utf-8', log=None):
        self.context = context or zmq.Context.instance()
        self.log = log
        self.encoding = encoding
        self.pipe = None
        self.pipe_endpoint = "inproc://{0}.inproc".format(id(self))
        self.thread = None

    def allow(self, *addresses):
        self.pipe.send_multipart([b'ALLOW'] + [b(a, self.encoding) for a in addresses])

    def deny(self, *addresses):
        self.pipe.send_multipart([b'DENY'] + [b(a, self.encoding) for a in addresses])

    def configure_plain(self, domain='*', passwords=None):
        self.pipe.send_multipart([b'PLAIN', b(domain, self.encoding), jsonapi.dumps(passwords or {})])

    def configure_curve(self, domain='*', location=''):
        domain = b(domain, self.encoding)
        location = b(location, self.encoding)
        self.pipe.send_multipart([b'CURVE', domain, location])

    def start(self):
        """Start the authentication thread"""
        # create a socket to communicate with auth thread.
        self.pipe = self.context.socket(zmq.PAIR)
        self.pipe.linger = 1
        self.pipe.bind(self.pipe_endpoint)
        self.thread = AuthenticationThread(self.context, self.pipe_endpoint, encoding=self.encoding, log=self.log)
        self.thread.start()

    def stop(self):
        """Stop the authentication thread"""
        if self.pipe:
            self.pipe.send(b'TERMINATE')
            if self.is_alive():
                self.thread.join()
            self.thread = None
            self.pipe.close()
            self.pipe = None

    def is_alive(self):
        """Is the ZAP thread currently running?"""
        if self.thread and self.thread.is_alive():
            return True
        return False

    def __del__(self):
        self.stop()

__all__ = ['ThreadAuthenticator']

########NEW FILE########
__FILENAME__ = constants
# coding: utf-8
"""zmq constants"""

from ._cffi import C, c_constant_names
from zmq.utils.constant_names import all_names

g = globals()
for cname in c_constant_names:
    if cname.startswith("ZMQ_"):
        name = cname[4:]
    else:
        name = cname
    g[name] = getattr(C, cname)

__all__ = all_names

########NEW FILE########
__FILENAME__ = context
# coding: utf-8
"""zmq Context class"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import weakref

from ._cffi import C, ffi

from .socket import *
from .constants import *

from zmq.error import ZMQError, _check_rc

class Context(object):
    _zmq_ctx = None
    _iothreads = None
    _closed = None
    _sockets = None
    _shadow = False

    def __init__(self, io_threads=1, shadow=None):
        
        if shadow:
            self._zmq_ctx = ffi.cast("void *", shadow)
            self._shadow = True
        else:
            self._shadow = False
            if not io_threads >= 0:
                raise ZMQError(EINVAL)
        
            self._zmq_ctx = C.zmq_ctx_new()
        if self._zmq_ctx == ffi.NULL:
            raise ZMQError(C.zmq_errno())
        if not shadow:
            C.zmq_ctx_set(self._zmq_ctx, IO_THREADS, io_threads)
        self._closed = False
        self._sockets = set()
    
    @property
    def underlying(self):
        """The address of the underlying libzmq context"""
        return int(ffi.cast('size_t', self._zmq_ctx))
    
    @property
    def closed(self):
        return self._closed

    def _add_socket(self, socket):
        ref = weakref.ref(socket)
        self._sockets.add(ref)
        return ref

    def _rm_socket(self, ref):
        if ref in self._sockets:
            self._sockets.remove(ref)

    def set(self, option, value):
        """set a context option
        
        see zmq_ctx_set
        """
        rc = C.zmq_ctx_set(self._zmq_ctx, option, value)
        _check_rc(rc)

    def get(self, option):
        """get context option
        
        see zmq_ctx_get
        """
        rc = C.zmq_ctx_get(self._zmq_ctx, option)
        _check_rc(rc)
        return rc

    def term(self):
        if self.closed:
            return

        C.zmq_ctx_destroy(self._zmq_ctx)

        self._zmq_ctx = None
        self._closed = True

    def destroy(self, linger=None):
        if self.closed:
            return

        sockets = self._sockets
        self._sockets = set()
        for s in sockets:
            s = s()
            if s and not s.closed:
                if linger:
                    s.setsockopt(LINGER, linger)
                s.close()
        
        self.term()

__all__ = ['Context']

########NEW FILE########
__FILENAME__ = devices
# coding: utf-8
"""zmq device functions"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from ._cffi import C, ffi, zmq_version_info
from .socket import Socket
from zmq.error import ZMQError, _check_rc

def device(device_type, frontend, backend):
    rc = C.zmq_proxy(frontend._zmq_socket, backend._zmq_socket, ffi.NULL)
    _check_rc(rc)

def proxy(frontend, backend, capture=None):
    if isinstance(capture, Socket):
        capture = capture._zmq_socket
    else:
        capture = ffi.NULL

    rc = C.zmq_proxy(frontend._zmq_socket, backend._zmq_socket, capture)
    _check_rc(rc)

__all__ = ['device', 'proxy']

########NEW FILE########
__FILENAME__ = error
"""zmq error functions"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from ._cffi import C, ffi

def strerror(errno):
    return ffi.string(C.zmq_strerror(errno))

zmq_errno = C.zmq_errno

__all__ = ['strerror', 'zmq_errno']

########NEW FILE########
__FILENAME__ = message
"""Dummy Frame object"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from ._cffi import ffi, C

import zmq

try:
    view = memoryview
except NameError:
    view = buffer

_content = lambda x: x.tobytes() if type(x) == memoryview else x

class Frame(object):
    _data = None
    tracker = None
    closed = False
    more = False
    buffer = None


    def __init__(self, data, track=False):
        try:
            view(data)
        except TypeError:
            raise

        self._data = data

        if isinstance(data, unicode):
            raise TypeError("Unicode objects not allowed. Only: str/bytes, " +
                            "buffer interfaces.")

        self.more = False
        self.tracker = None
        self.closed = False
        if track:
            self.tracker = zmq.MessageTracker()

        self.buffer = view(self.bytes)

    @property
    def bytes(self):
        data = _content(self._data)
        return data

    def __len__(self):
        return len(self.bytes)

    def __eq__(self, other):
        return self.bytes == _content(other)

    def __str__(self):
        if str is unicode:
            return self.bytes.decode()
        else:
            return self.bytes

    @property
    def done(self):
        return True

Message = Frame

__all__ = ['Frame', 'Message']

########NEW FILE########
__FILENAME__ = socket
# coding: utf-8
"""zmq Socket class"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import random
import codecs

import errno as errno_mod

from ._cffi import (C, ffi, new_uint64_pointer, new_int64_pointer,
                    new_int_pointer, new_binary_data, value_uint64_pointer,
                    value_int64_pointer, value_int_pointer, value_binary_data,
                    IPC_PATH_MAX_LEN)

from .message import Frame
from .constants import *

import zmq
from zmq.error import ZMQError, _check_rc, _check_version
from zmq.utils.strtypes import unicode


def new_pointer_from_opt(option, length=0):
    from zmq.sugar.constants import int_sockopts,   \
                                    int64_sockopts, \
                                    bytes_sockopts
    if option in int64_sockopts:
        return new_int64_pointer()
    elif option in int_sockopts:
        return new_int_pointer()
    elif option in bytes_sockopts:
        return new_binary_data(length)
    else:
        raise ZMQError(zmq.EINVAL)

def value_from_opt_pointer(option, opt_pointer, length=0):
    from zmq.sugar.constants import int_sockopts,   \
                                    int64_sockopts, \
                                    bytes_sockopts
    if option in int64_sockopts:
        return int(opt_pointer[0])
    elif option in int_sockopts:
        return int(opt_pointer[0])
    elif option in bytes_sockopts:
        return ffi.buffer(opt_pointer, length)[:]
    else:
        raise ZMQError(zmq.EINVAL)

def initialize_opt_pointer(option, value, length=0):
    from zmq.sugar.constants import int_sockopts,   \
                                    int64_sockopts, \
                                    bytes_sockopts
    if option in int64_sockopts:
        return value_int64_pointer(value)
    elif option in int_sockopts:
        return value_int_pointer(value)
    elif option in bytes_sockopts:
        return value_binary_data(value, length)
    else:
        raise ZMQError(zmq.EINVAL)


class Socket(object):
    context = None
    socket_type = None
    _zmq_socket = None
    _closed = None
    _ref = None
    _shadow = False

    def __init__(self, context=None, socket_type=None, shadow=None):
        self.context = context
        if shadow is not None:
            self._zmq_socket = ffi.cast("void *", shadow)
            self._shadow = True
        else:
            self._shadow = False
            self._zmq_socket = C.zmq_socket(context._zmq_ctx, socket_type)
        if self._zmq_socket == ffi.NULL:
            raise ZMQError()
        self._closed = False
        if context:
            self._ref = context._add_socket(self)
    
    @property
    def underlying(self):
        """The address of the underlying libzmq socket"""
        return int(ffi.cast('size_t', self._zmq_socket))
    
    @property
    def closed(self):
        return self._closed

    def close(self, linger=None):
        rc = 0
        if not self._closed and hasattr(self, '_zmq_socket'):
            if self._zmq_socket is not None:
                rc = C.zmq_close(self._zmq_socket)
            self._closed = True
            if self.context:
                self.context._rm_socket(self._ref)
        return rc

    def bind(self, address):
        if isinstance(address, unicode):
            address = address.encode('utf8')
        rc = C.zmq_bind(self._zmq_socket, address)
        if rc < 0:
            if IPC_PATH_MAX_LEN and C.zmq_errno() == errno_mod.ENAMETOOLONG:
                # py3compat: address is bytes, but msg wants str
                if str is unicode:
                    address = address.decode('utf-8', 'replace')
                path = address.split('://', 1)[-1]
                msg = ('ipc path "{0}" is longer than {1} '
                                'characters (sizeof(sockaddr_un.sun_path)).'
                                .format(path, IPC_PATH_MAX_LEN))
                raise ZMQError(C.zmq_errno(), msg=msg)
            else:
                _check_rc(rc)

    def unbind(self, address):
        _check_version((3,2), "unbind")
        if isinstance(address, unicode):
            address = address.encode('utf8')
        rc = C.zmq_unbind(self._zmq_socket, address)
        _check_rc(rc)

    def connect(self, address):
        if isinstance(address, unicode):
            address = address.encode('utf8')
        rc = C.zmq_connect(self._zmq_socket, address)
        _check_rc(rc)

    def disconnect(self, address):
        _check_version((3,2), "disconnect")
        if isinstance(address, unicode):
            address = address.encode('utf8')
        rc = C.zmq_disconnect(self._zmq_socket, address)
        _check_rc(rc)

    def set(self, option, value):
        length = None
        if isinstance(value, unicode):
            raise TypeError("unicode not allowed, use bytes")
        
        if isinstance(value, bytes):
            if option not in zmq.constants.bytes_sockopts:
                raise TypeError("not a bytes sockopt: %s" % option)
            length = len(value)
        
        c_data = initialize_opt_pointer(option, value, length)

        c_value_pointer = c_data[0]
        c_sizet = c_data[1]

        rc = C.zmq_setsockopt(self._zmq_socket,
                               option,
                               ffi.cast('void*', c_value_pointer),
                               c_sizet)
        _check_rc(rc)

    def get(self, option):
        c_data = new_pointer_from_opt(option, length=255)

        c_value_pointer = c_data[0]
        c_sizet_pointer = c_data[1]

        rc = C.zmq_getsockopt(self._zmq_socket,
                               option,
                               c_value_pointer,
                               c_sizet_pointer)
        _check_rc(rc)
        
        sz = c_sizet_pointer[0]
        v = value_from_opt_pointer(option, c_value_pointer, sz)
        if option != zmq.IDENTITY and option in zmq.constants.bytes_sockopts and v.endswith(b'\0'):
            v = v[:-1]
        return v

    def send(self, message, flags=0, copy=False, track=False):
        if isinstance(message, unicode):
            raise TypeError("Message must be in bytes, not an unicode Object")

        if isinstance(message, Frame):
            message = message.bytes

        zmq_msg = ffi.new('zmq_msg_t*')
        c_message = ffi.new('char[]', message)
        rc = C.zmq_msg_init_size(zmq_msg, len(message))
        C.memcpy(C.zmq_msg_data(zmq_msg), c_message, len(message))

        rc = C.zmq_msg_send(zmq_msg, self._zmq_socket, flags)
        C.zmq_msg_close(zmq_msg)
        _check_rc(rc)

        if track:
            return zmq.MessageTracker()

    def recv(self, flags=0, copy=True, track=False):
        zmq_msg = ffi.new('zmq_msg_t*')
        C.zmq_msg_init(zmq_msg)

        rc = C.zmq_msg_recv(zmq_msg, self._zmq_socket, flags)

        if rc < 0:
            C.zmq_msg_close(zmq_msg)
            _check_rc(rc)

        _buffer = ffi.buffer(C.zmq_msg_data(zmq_msg), C.zmq_msg_size(zmq_msg))
        value = _buffer[:]
        C.zmq_msg_close(zmq_msg)

        frame = Frame(value, track=track)
        frame.more = self.getsockopt(RCVMORE)

        if copy:
            return frame.bytes
        else:
            return frame
    
    def monitor(self, addr, events=-1):
        """s.monitor(addr, flags)

        Start publishing socket events on inproc.
        See libzmq docs for zmq_monitor for details.
        
        Note: requires libzmq >= 3.2
        
        Parameters
        ----------
        addr : str
            The inproc url used for monitoring.
        events : int [default: zmq.EVENT_ALL]
            The zmq event bitmask for which events will be sent to the monitor.
        """
        
        _check_version((3,2), "monitor")
        if events < 0:
            events = zmq.EVENT_ALL
        rc = C.zmq_socket_monitor(self._zmq_socket, addr, events)


__all__ = ['Socket', 'IPC_PATH_MAX_LEN']

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
"""miscellaneous zmq_utils wrapping"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from ._cffi import ffi, C

from zmq.error import ZMQError, _check_rc, _check_version

def curve_keypair():
    """generate a Z85 keypair for use with zmq.CURVE security
    
    Requires libzmq (≥ 4.0) to have been linked with libsodium.
    
    Returns
    -------
    (public, secret) : two bytestrings
        The public and private keypair as 40 byte z85-encoded bytestrings.
    """
    _check_version((3,2), "monitor")
    public = ffi.new('char[64]')
    private = ffi.new('char[64]')
    rc = C.zmq_curve_keypair(public, private)
    _check_rc(rc)
    return ffi.buffer(public)[:40], ffi.buffer(private)[:40]


class Stopwatch(object):
    def __init__(self):
        self.watch = ffi.NULL

    def start(self):
        if self.watch == ffi.NULL:
            self.watch = C.zmq_stopwatch_start()
        else:
            raise ZMQError('Stopwatch is already runing.')

    def stop(self):
        if self.watch == ffi.NULL:
            raise ZMQError('Must start the Stopwatch before calling stop.')
        else:
            time = C.zmq_stopwatch_stop(self.watch)
            self.watch = ffi.NULL
            return time

    def sleep(self, seconds):
        C.zmq_sleep(seconds)

__all__ = ['curve_keypair', 'Stopwatch']

########NEW FILE########
__FILENAME__ = _cffi
# coding: utf-8
"""The main CFFI wrapping of libzmq"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import json
import os
from os.path import dirname, join
from cffi import FFI

from zmq.utils.constant_names import all_names, no_prefix


#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

ffi = FFI()

base_zmq_version = (3,2,2)

core_functions = \
'''
void* zmq_socket(void *context, int type);
int zmq_close(void *socket);

int zmq_bind(void *socket, const char *endpoint);
int zmq_connect(void *socket, const char *endpoint);

int zmq_errno(void);
const char * zmq_strerror(int errnum);

void* zmq_stopwatch_start(void);
unsigned long zmq_stopwatch_stop(void *watch);
void zmq_sleep(int seconds_);
int zmq_device(int device, void *frontend, void *backend);
'''

core32_functions = \
'''
int zmq_unbind(void *socket, const char *endpoint);
int zmq_disconnect(void *socket, const char *endpoint);
void* zmq_ctx_new();
int zmq_ctx_destroy(void *context);
int zmq_ctx_get(void *context, int opt);
int zmq_ctx_set(void *context, int opt, int optval);
int zmq_proxy(void *frontend, void *backend, void *capture);
int zmq_socket_monitor(void *socket, const char *addr, int events);
'''

core40_functions = \
'''
int zmq_curve_keypair (char *z85_public_key, char *z85_secret_key);
'''

message32_functions = \
'''
typedef struct { ...; } zmq_msg_t;
typedef ... zmq_free_fn;

int zmq_msg_init(zmq_msg_t *msg);
int zmq_msg_init_size(zmq_msg_t *msg, size_t size);
int zmq_msg_init_data(zmq_msg_t *msg,
                      void *data,
                      size_t size,
                      zmq_free_fn *ffn,
                      void *hint);

size_t zmq_msg_size(zmq_msg_t *msg);
void *zmq_msg_data(zmq_msg_t *msg);
int zmq_msg_close(zmq_msg_t *msg);

int zmq_msg_send(zmq_msg_t *msg, void *socket, int flags);
int zmq_msg_recv(zmq_msg_t *msg, void *socket, int flags);
'''

sockopt_functions = \
'''
int zmq_getsockopt(void *socket,
                   int option_name,
                   void *option_value,
                   size_t *option_len);

int zmq_setsockopt(void *socket,
                   int option_name,
                   const void *option_value,
                   size_t option_len);
'''

polling_functions = \
'''
typedef struct
{
    void *socket;
    int fd;
    short events;
    short revents;
} zmq_pollitem_t;

int zmq_poll(zmq_pollitem_t *items, int nitems, long timeout);
'''

extra_functions = \
'''
void * memcpy(void *restrict s1, const void *restrict s2, size_t n);
int get_ipc_path_max_len(void);
'''

def load_compiler_config():
    import zmq
    zmq_dir = dirname(zmq.__file__)
    zmq_parent = dirname(zmq_dir)
    
    fname = join(zmq_dir, 'utils', 'compiler.json')
    if os.path.exists(fname):
        with open(fname) as f:
            cfg = json.load(f)
    else:
        cfg = {}
    
    cfg.setdefault("include_dirs", [])
    cfg.setdefault("library_dirs", [])
    cfg.setdefault("runtime_library_dirs", [])
    cfg.setdefault("libraries", ["zmq"])
    
    # cast to str, because cffi can't handle unicode paths (?!)
    cfg['libraries'] = [str(lib) for lib in cfg['libraries']]
    for key in ("include_dirs", "library_dirs", "runtime_library_dirs"):
        # interpret paths relative to parent of zmq (like source tree)
        abs_paths = []
        for p in cfg[key]:
            if p.startswith('zmq'):
                p = join(zmq_parent, p)
            abs_paths.append(str(p))
        cfg[key] = abs_paths
    return cfg

cfg = load_compiler_config()

def zmq_version_info():
    ffi_check = FFI()
    ffi_check.cdef('void zmq_version(int *major, int *minor, int *patch);')
    cfg = load_compiler_config()
    C_check_version = ffi_check.verify('#include <zmq.h>',
        libraries=cfg['libraries'],
        include_dirs=cfg['include_dirs'],
        library_dirs=cfg['library_dirs'],
        runtime_library_dirs=cfg['runtime_library_dirs'],
    )
    major = ffi.new('int*')
    minor = ffi.new('int*')
    patch = ffi.new('int*')

    C_check_version.zmq_version(major, minor, patch)

    return (int(major[0]), int(minor[0]), int(patch[0]))

def _make_defines(names):
    _names = []
    for name in names:
        define_line = "#define %s ..." % (name)
        _names.append(define_line)

    return "\n".join(_names)

c_constant_names = []
for name in all_names:
    if no_prefix(name):
        c_constant_names.append(name)
    else:
        c_constant_names.append("ZMQ_" + name)

constants = _make_defines(c_constant_names)

try:
    _version_info = zmq_version_info()
except Exception as e:
    raise ImportError("PyZMQ CFFI backend couldn't find zeromq: %s\n"
    "Please check that you have zeromq headers and libraries." % e)

if _version_info >= (3,2,2):
    functions = '\n'.join([constants,
                         core_functions,
                         core32_functions,
                         core40_functions,
                         message32_functions,
                         sockopt_functions,
                         polling_functions,
                         extra_functions,
    ])
else:
    raise ImportError("PyZMQ CFFI backend requires zeromq >= 3.2.2,"
        " but found %i.%i.%i" % _version_info
    )


ffi.cdef(functions)

C = ffi.verify('''
    #include <stdio.h>
    #include <sys/un.h>
    #include <string.h>
    
    #include <zmq.h>
    #include <zmq_utils.h>
    #include "zmq_compat.h"

int get_ipc_path_max_len(void) {
    struct sockaddr_un *dummy;
    return sizeof(dummy->sun_path) - 1;
}

''',
    libraries=cfg['libraries'],
    include_dirs=cfg['include_dirs'],
    library_dirs=cfg['library_dirs'],
    runtime_library_dirs=cfg['runtime_library_dirs'],
)

nsp = new_sizet_pointer = lambda length: ffi.new('size_t*', length)

new_uint64_pointer = lambda: (ffi.new('uint64_t*'),
                              nsp(ffi.sizeof('uint64_t')))
new_int64_pointer = lambda: (ffi.new('int64_t*'),
                             nsp(ffi.sizeof('int64_t')))
new_int_pointer = lambda: (ffi.new('int*'),
                           nsp(ffi.sizeof('int')))
new_binary_data = lambda length: (ffi.new('char[%d]' % (length)),
                                  nsp(ffi.sizeof('char') * length))

value_uint64_pointer = lambda val : (ffi.new('uint64_t*', val),
                                     ffi.sizeof('uint64_t'))
value_int64_pointer = lambda val: (ffi.new('int64_t*', val),
                                   ffi.sizeof('int64_t'))
value_int_pointer = lambda val: (ffi.new('int*', val),
                                 ffi.sizeof('int'))
value_binary_data = lambda val, length: (ffi.new('char[%d]' % (length + 1), val),
                                         ffi.sizeof('char') * length)

IPC_PATH_MAX_LEN = C.get_ipc_path_max_len()

########NEW FILE########
__FILENAME__ = _poll
# coding: utf-8
"""zmq poll function"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Felipe Cruz
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from ._cffi import C, ffi, zmq_version_info

from .constants import *

from zmq.error import _check_rc


def _make_zmq_pollitem(socket, flags):
    zmq_socket = socket._zmq_socket
    zmq_pollitem = ffi.new('zmq_pollitem_t*')
    zmq_pollitem.socket = zmq_socket
    zmq_pollitem.fd = 0
    zmq_pollitem.events = flags
    zmq_pollitem.revents = 0
    return zmq_pollitem[0]

def _make_zmq_pollitem_fromfd(socket_fd, flags):
    zmq_pollitem = ffi.new('zmq_pollitem_t*')
    zmq_pollitem.socket = ffi.NULL
    zmq_pollitem.fd = socket_fd
    zmq_pollitem.events = flags
    zmq_pollitem.revents = 0
    return zmq_pollitem[0]

def zmq_poll(sockets, timeout):
    cffi_pollitem_list = []
    low_level_to_socket_obj = {}
    for item in sockets:
        if isinstance(item[0], int):
            low_level_to_socket_obj[item[0]] = item
            cffi_pollitem_list.append(_make_zmq_pollitem_fromfd(item[0], item[1]))
        else:
            low_level_to_socket_obj[item[0]._zmq_socket] = item
            cffi_pollitem_list.append(_make_zmq_pollitem(item[0], item[1]))
    items = ffi.new('zmq_pollitem_t[]', cffi_pollitem_list)
    list_length = ffi.cast('int', len(cffi_pollitem_list))
    c_timeout = ffi.cast('long', timeout)
    rc = C.zmq_poll(items, list_length, c_timeout)
    _check_rc(rc)
    result = []
    for index in range(len(items)):
        if not items[index].socket == ffi.NULL:
            if items[index].revents > 0:
                result.append((low_level_to_socket_obj[items[index].socket][0],
                            items[index].revents))
        else:
            result.append((items[index].fd, items[index].revents))
    return result

__all__ = ['zmq_poll']

########NEW FILE########
__FILENAME__ = select
"""Import basic exposure of libzmq C API as a backend"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

public_api = [
    'Context',
    'Socket',
    'Frame',
    'Message',
    'Stopwatch',
    'device',
    'proxy',
    'zmq_poll',
    'strerror',
    'zmq_errno',
    'curve_keypair',
    'constants',
    'zmq_version_info',
    'IPC_PATH_MAX_LEN',
]

def select_backend(name):
    """Select the pyzmq backend"""
    try:
        mod = __import__(name, fromlist=public_api)
    except ImportError:
        raise
    except Exception as e:
        import sys
        from zmq.utils.sixcerpt import reraise
        exc_info = sys.exc_info()
        reraise(ImportError, ImportError("Importing %s failed with %s" % (name, e)), exc_info[2])
    
    ns = {}
    for key in public_api:
        ns[key] = getattr(mod, key)
    return ns

########NEW FILE########
__FILENAME__ = basedevice
"""Classes for running 0MQ Devices in the background.

Authors
-------
* MinRK
* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import time
from threading import Thread
from multiprocessing import Process

from zmq import device, QUEUE, Context, ETERM, ZMQError

#-----------------------------------------------------------------------------
# Classes
#-----------------------------------------------------------------------------

class Device:
    """A 0MQ Device to be run in the background.
    
    You do not pass Socket instances to this, but rather Socket types::

        Device(device_type, in_socket_type, out_socket_type)

    For instance::

        dev = Device(zmq.QUEUE, zmq.DEALER, zmq.ROUTER)

    Similar to zmq.device, but socket types instead of sockets themselves are
    passed, and the sockets are created in the work thread, to avoid issues
    with thread safety. As a result, additional bind_{in|out} and
    connect_{in|out} methods and setsockopt_{in|out} allow users to specify
    connections for the sockets.
    
    Parameters
    ----------
    device_type : int
        The 0MQ Device type
    {in|out}_type : int
        zmq socket types, to be passed later to context.socket(). e.g.
        zmq.PUB, zmq.SUB, zmq.REQ. If out_type is < 0, then in_socket is used
        for both in_socket and out_socket.
        
    Methods
    -------
    bind_{in_out}(iface)
        passthrough for ``{in|out}_socket.bind(iface)``, to be called in the thread
    connect_{in_out}(iface)
        passthrough for ``{in|out}_socket.connect(iface)``, to be called in the
        thread
    setsockopt_{in_out}(opt,value)
        passthrough for ``{in|out}_socket.setsockopt(opt, value)``, to be called in
        the thread
    
    Attributes
    ----------
    daemon : int
        sets whether the thread should be run as a daemon
        Default is true, because if it is false, the thread will not
        exit unless it is killed
    context_factory : callable (class attribute)
        Function for creating the Context. This will be Context.instance
        in ThreadDevices, and Context in ProcessDevices.  The only reason
        it is not instance() in ProcessDevices is that there may be a stale
        Context instance already initialized, and the forked environment
        should *never* try to use it.
    """
    
    context_factory = Context.instance
    """Callable that returns a context. Typically either Context.instance or Context,
    depending on whether the device should share the global instance or not.
    """

    def __init__(self, device_type=QUEUE, in_type=None, out_type=None):
        self.device_type = device_type
        if in_type is None:
            raise TypeError("in_type must be specified")
        if out_type is None:
            raise TypeError("out_type must be specified")
        self.in_type = in_type
        self.out_type = out_type
        self._in_binds = []
        self._in_connects = []
        self._in_sockopts = []
        self._out_binds = []
        self._out_connects = []
        self._out_sockopts = []
        self.daemon = True
        self.done = False
    
    def bind_in(self, addr):
        """Enqueue ZMQ address for binding on in_socket.

        See zmq.Socket.bind for details.
        """
        self._in_binds.append(addr)
    
    def connect_in(self, addr):
        """Enqueue ZMQ address for connecting on in_socket.

        See zmq.Socket.connect for details.
        """
        self._in_connects.append(addr)
    
    def setsockopt_in(self, opt, value):
        """Enqueue setsockopt(opt, value) for in_socket

        See zmq.Socket.setsockopt for details.
        """
        self._in_sockopts.append((opt, value))
    
    def bind_out(self, addr):
        """Enqueue ZMQ address for binding on out_socket.

        See zmq.Socket.bind for details.
        """
        self._out_binds.append(addr)
    
    def connect_out(self, addr):
        """Enqueue ZMQ address for connecting on out_socket.

        See zmq.Socket.connect for details.
        """
        self._out_connects.append(addr)
    
    def setsockopt_out(self, opt, value):
        """Enqueue setsockopt(opt, value) for out_socket

        See zmq.Socket.setsockopt for details.
        """
        self._out_sockopts.append((opt, value))
    
    def _setup_sockets(self):
        ctx = self.context_factory()
        
        self._context = ctx
        
        # create the sockets
        ins = ctx.socket(self.in_type)
        if self.out_type < 0:
            outs = ins
        else:
            outs = ctx.socket(self.out_type)
        
        # set sockopts (must be done first, in case of zmq.IDENTITY)
        for opt,value in self._in_sockopts:
            ins.setsockopt(opt, value)
        for opt,value in self._out_sockopts:
            outs.setsockopt(opt, value)
        
        for iface in self._in_binds:
            ins.bind(iface)
        for iface in self._out_binds:
            outs.bind(iface)
        
        for iface in self._in_connects:
            ins.connect(iface)
        for iface in self._out_connects:
            outs.connect(iface)
        
        return ins,outs
    
    def run_device(self):
        """The runner method.

        Do not call me directly, instead call ``self.start()``, just like a Thread.
        """
        ins,outs = self._setup_sockets()
        device(self.device_type, ins, outs)
    
    def run(self):
        """wrap run_device in try/catch ETERM"""
        try:
            self.run_device()
        except ZMQError as e:
            if e.errno == ETERM:
                # silence TERM errors, because this should be a clean shutdown
                pass
            else:
                raise
        finally:
            self.done = True
    
    def start(self):
        """Start the device. Override me in subclass for other launchers."""
        return self.run()

    def join(self,timeout=None):
        """wait for me to finish, like Thread.join.
        
        Reimplemented appropriately by subclasses."""
        tic = time.time()
        toc = tic
        while not self.done and not (timeout is not None and toc-tic > timeout):
            time.sleep(.001)
            toc = time.time()


class BackgroundDevice(Device):
    """Base class for launching Devices in background processes and threads."""

    launcher=None
    _launch_class=None

    def start(self):
        self.launcher = self._launch_class(target=self.run)
        self.launcher.daemon = self.daemon
        return self.launcher.start()

    def join(self, timeout=None):
        return self.launcher.join(timeout=timeout)


class ThreadDevice(BackgroundDevice):
    """A Device that will be run in a background Thread.

    See Device for details.
    """
    _launch_class=Thread

class ProcessDevice(BackgroundDevice):
    """A Device that will be run in a background Process.

    See Device for details.
    """
    _launch_class=Process
    context_factory = Context
    """Callable that returns a context. Typically either Context.instance or Context,
    depending on whether the device should share the global instance or not.
    """


__all__ = ['Device', 'ThreadDevice', 'ProcessDevice']

########NEW FILE########
__FILENAME__ = monitoredqueue
"""pure Python monitored_queue function

For use when Cython extension is unavailable (PyPy).

Authors
-------
* MinRK
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import zmq

def _relay(ins, outs, sides, prefix, swap_ids):
    msg = ins.recv_multipart()
    if swap_ids:
        msg[:2] = msg[:2][::-1]
    outs.send_multipart(msg)
    sides.send_multipart([prefix] + msg)

def monitored_queue(in_socket, out_socket, mon_socket,
                    in_prefix=b'in', out_prefix=b'out'):
    
    swap_ids = in_socket.type == zmq.ROUTER and out_socket.type == zmq.ROUTER
    
    poller = zmq.Poller()
    poller.register(in_socket, zmq.POLLIN)
    poller.register(out_socket, zmq.POLLIN)
    while True:
        events = dict(poller.poll())
        if in_socket in events:
            _relay(in_socket, out_socket, mon_socket, in_prefix, swap_ids)
        if out_socket in events:
            _relay(out_socket, in_socket, mon_socket, out_prefix, swap_ids)

__all__ = ['monitored_queue']

########NEW FILE########
__FILENAME__ = monitoredqueuedevice
"""MonitoredQueue classes and functions.

Authors
-------
* MinRK
* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from zmq import ZMQError, PUB
from zmq.devices.proxydevice import ProxyBase, Proxy, ThreadProxy, ProcessProxy
from zmq.devices.monitoredqueue import monitored_queue

#-----------------------------------------------------------------------------
# Classes
#-----------------------------------------------------------------------------


class MonitoredQueueBase(ProxyBase):
    """Base class for overriding methods."""
    
    _in_prefix = b''
    _out_prefix = b''
    
    def __init__(self, in_type, out_type, mon_type=PUB, in_prefix=b'in', out_prefix=b'out'):
        
        ProxyBase.__init__(self, in_type=in_type, out_type=out_type, mon_type=mon_type)
        
        self._in_prefix = in_prefix
        self._out_prefix = out_prefix

    def run_device(self):
        ins,outs,mons = self._setup_sockets()
        monitored_queue(ins, outs, mons, self._in_prefix, self._out_prefix)


class MonitoredQueue(MonitoredQueueBase, Proxy):
    """Class for running monitored_queue in the background.

    See zmq.devices.Device for most of the spec. MonitoredQueue differs from Proxy,
    only in that it adds a ``prefix`` to messages sent on the monitor socket,
    with a different prefix for each direction.
    
    MQ also supports ROUTER on both sides, which zmq.proxy does not.

    If a message arrives on `in_sock`, it will be prefixed with `in_prefix` on the monitor socket.
    If it arrives on out_sock, it will be prefixed with `out_prefix`.

    A PUB socket is the most logical choice for the mon_socket, but it is not required.
    """
    pass


class ThreadMonitoredQueue(MonitoredQueueBase, ThreadProxy):
    """Run zmq.monitored_queue in a background thread.
    
    See MonitoredQueue and Proxy for details.
    """
    pass


class ProcessMonitoredQueue(MonitoredQueueBase, ProcessProxy):
    """Run zmq.monitored_queue in a background thread.
    
    See MonitoredQueue and Proxy for details.
    """


__all__ = [
    'MonitoredQueue',
    'ThreadMonitoredQueue',
    'ProcessMonitoredQueue'
]

########NEW FILE########
__FILENAME__ = proxydevice
"""Proxy classes and functions.

Authors
-------
* MinRK
* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import zmq
from zmq.devices.basedevice import Device, ThreadDevice, ProcessDevice

#-----------------------------------------------------------------------------
# Classes
#-----------------------------------------------------------------------------


class ProxyBase(object):
    """Base class for overriding methods."""
    
    def __init__(self, in_type, out_type, mon_type=zmq.PUB):
        
        Device.__init__(self, in_type=in_type, out_type=out_type)
        self.mon_type = mon_type
        self._mon_binds = []
        self._mon_connects = []
        self._mon_sockopts = []

    def bind_mon(self, addr):
        """Enqueue ZMQ address for binding on mon_socket.

        See zmq.Socket.bind for details.
        """
        self._mon_binds.append(addr)

    def connect_mon(self, addr):
        """Enqueue ZMQ address for connecting on mon_socket.

        See zmq.Socket.bind for details.
        """
        self._mon_connects.append(addr)

    def setsockopt_mon(self, opt, value):
        """Enqueue setsockopt(opt, value) for mon_socket

        See zmq.Socket.setsockopt for details.
        """
        self._mon_sockopts.append((opt, value))

    def _setup_sockets(self):
        ins,outs = Device._setup_sockets(self)
        ctx = self._context
        mons = ctx.socket(self.mon_type)
        
        # set sockopts (must be done first, in case of zmq.IDENTITY)
        for opt,value in self._mon_sockopts:
            mons.setsockopt(opt, value)
        
        for iface in self._mon_binds:
            mons.bind(iface)
        
        for iface in self._mon_connects:
            mons.connect(iface)
        
        return ins,outs,mons
    
    def run_device(self):
        ins,outs,mons = self._setup_sockets()
        zmq.proxy(ins, outs, mons)

class Proxy(ProxyBase, Device):
    """Threadsafe Proxy object.

    See zmq.devices.Device for most of the spec. This subclass adds a
    <method>_mon version of each <method>_{in|out} method, for configuring the
    monitor socket.

    A Proxy is a 3-socket ZMQ Device that functions just like a
    QUEUE, except each message is also sent out on the monitor socket.

    A PUB socket is the most logical choice for the mon_socket, but it is not required.
    """
    pass

class ThreadProxy(ProxyBase, ThreadDevice):
    """Proxy in a Thread. See Proxy for more."""
    pass

class ProcessProxy(ProxyBase, ProcessDevice):
    """Proxy in a Process. See Proxy for more."""
    pass


__all__ = [
    'Proxy',
    'ThreadProxy',
    'ProcessProxy',
]

########NEW FILE########
__FILENAME__ = error
"""0MQ Error classes and functions."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------


class ZMQBaseError(Exception):
    """Base exception class for 0MQ errors in Python."""
    pass

class ZMQError(ZMQBaseError):
    """Wrap an errno style error.

    Parameters
    ----------
    errno : int
        The ZMQ errno or None.  If None, then ``zmq_errno()`` is called and
        used.
    msg : string
        Description of the error or None.
    """
    errno = None

    def __init__(self, errno=None, msg=None):
        """Wrap an errno style error.

        Parameters
        ----------
        errno : int
            The ZMQ errno or None.  If None, then ``zmq_errno()`` is called and
            used.
        msg : string
            Description of the error or None.
        """
        from zmq.backend import strerror, zmq_errno
        if errno is None:
            errno = zmq_errno()
        if isinstance(errno, int):
            self.errno = errno
            if msg is None:
                self.strerror = strerror(errno)
            else:
                self.strerror = msg
        else:
            if msg is None:
                self.strerror = str(errno)
            else:
                self.strerror = msg
        # flush signals, because there could be a SIGINT
        # waiting to pounce, resulting in uncaught exceptions.
        # Doing this here means getting SIGINT during a blocking
        # libzmq call will raise a *catchable* KeyboardInterrupt
        # PyErr_CheckSignals()

    def __str__(self):
        return self.strerror
    
    def __repr__(self):
        return "ZMQError('%s')"%self.strerror


class ZMQBindError(ZMQBaseError):
    """An error for ``Socket.bind_to_random_port()``.
    
    See Also
    --------
    .Socket.bind_to_random_port
    """
    pass


class NotDone(ZMQBaseError):
    """Raised when timeout is reached while waiting for 0MQ to finish with a Message
    
    See Also
    --------
    .MessageTracker.wait : object for tracking when ZeroMQ is done
    """
    pass


class ContextTerminated(ZMQError):
    """Wrapper for zmq.ETERM
    
    .. versionadded:: 13.0
    """
    pass


class Again(ZMQError):
    """Wrapper for zmq.EAGAIN
    
    .. versionadded:: 13.0
    """
    pass


def _check_rc(rc, errno=None):
    """internal utility for checking zmq return condition
    
    and raising the appropriate Exception class
    """
    if rc < 0:
        from zmq.backend import zmq_errno
        if errno is None:
            errno = zmq_errno()
        from zmq import EAGAIN, ETERM
        if errno == EAGAIN:
            raise Again(errno)
        elif errno == ETERM:
            raise ContextTerminated(errno)
        else:
            raise ZMQError(errno)

_zmq_version_info = None
_zmq_version = None

class ZMQVersionError(NotImplementedError):
    """Raised when a feature is not provided by the linked version of libzmq.
    
    .. versionadded:: 14.2
    """
    min_version = None
    def __init__(self, min_version, msg='Feature'):
        global _zmq_version
        if _zmq_version is None:
            from zmq import zmq_version
            _zmq_version = zmq_version()
        self.msg = msg
        self.min_version = min_version
        self.version = _zmq_version
    
    def __repr__(self):
        return "ZMQVersionError('%s')" % str(self)
    
    def __str__(self):
        return "%s requires libzmq >= %s, have %s" % (self.msg, self.min_version, self.version)


def _check_version(min_version_info, msg='Feature'):
    """Check for libzmq
    
    raises ZMQVersionError if current zmq version is not at least min_version
    
    min_version_info is a tuple of integers, and will be compared against zmq.zmq_version_info().
    """
    global _zmq_version_info
    if _zmq_version_info is None:
        from zmq import zmq_version_info
        _zmq_version_info = zmq_version_info()
    if _zmq_version_info < min_version_info:
        min_version = '.'.join(str(v) for v in min_version_info)
        raise ZMQVersionError(min_version, msg)


__all__ = [
    'ZMQBaseError',
    'ZMQBindError',
    'ZMQError',
    'NotDone',
    'ContextTerminated',
    'Again',
    'ZMQVersionError',
]

########NEW FILE########
__FILENAME__ = ioloop
# coding: utf-8
"""tornado IOLoop API with zmq compatibility

If you have tornado ≥ 3.0, this is a subclass of tornado's IOLoop,
otherwise we ship a minimal subset of tornado in zmq.eventloop.minitornado.

The minimal shipped version of tornado's IOLoop does not include
support for concurrent futures - this will only be available if you
have tornado ≥ 3.0.

Authors
-------
* MinRK
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from __future__ import absolute_import, division, with_statement

import os
import time
import warnings

from zmq import (
    Poller,
    POLLIN, POLLOUT, POLLERR,
    ZMQError, ETERM,
)

try:
    import tornado
    tornado_version = tornado.version_info
except (ImportError, AttributeError):
    tornado_version = ()

try:
    # tornado ≥ 3
    from tornado.ioloop import PollIOLoop, PeriodicCallback
    from tornado.log import gen_log
except ImportError:
    from .minitornado.ioloop import PollIOLoop, PeriodicCallback
    from .minitornado.log import gen_log


class DelayedCallback(PeriodicCallback):
    """Schedules the given callback to be called once.

    The callback is called once, after callback_time milliseconds.

    `start` must be called after the DelayedCallback is created.
    
    The timeout is calculated from when `start` is called.
    """
    def __init__(self, callback, callback_time, io_loop=None):
        # PeriodicCallback require callback_time to be positive
        warnings.warn("""DelayedCallback is deprecated.
        Use loop.add_timeout instead.""", DeprecationWarning)
        callback_time = max(callback_time, 1e-3)
        super(DelayedCallback, self).__init__(callback, callback_time, io_loop)
    
    def start(self):
        """Starts the timer."""
        self._running = True
        self._firstrun = True
        self._next_timeout = time.time() + self.callback_time / 1000.0
        self.io_loop.add_timeout(self._next_timeout, self._run)
    
    def _run(self):
        if not self._running: return
        self._running = False
        try:
            self.callback()
        except Exception:
            gen_log.error("Error in delayed callback", exc_info=True)


class ZMQPoller(object):
    """A poller that can be used in the tornado IOLoop.
    
    This simply wraps a regular zmq.Poller, scaling the timeout
    by 1000, so that it is in seconds rather than milliseconds.
    """
    
    def __init__(self):
        self._poller = Poller()
    
    @staticmethod
    def _map_events(events):
        """translate IOLoop.READ/WRITE/ERROR event masks into zmq.POLLIN/OUT/ERR"""
        z_events = 0
        if events & IOLoop.READ:
            z_events |= POLLIN
        if events & IOLoop.WRITE:
            z_events |= POLLOUT
        if events & IOLoop.ERROR:
            z_events |= POLLERR
        return z_events
    
    @staticmethod
    def _remap_events(z_events):
        """translate zmq.POLLIN/OUT/ERR event masks into IOLoop.READ/WRITE/ERROR"""
        events = 0
        if z_events & POLLIN:
            events |= IOLoop.READ
        if z_events & POLLOUT:
            events |= IOLoop.WRITE
        if z_events & POLLERR:
            events |= IOLoop.ERROR
        return events
    
    def register(self, fd, events):
        return self._poller.register(fd, self._map_events(events))
    
    def modify(self, fd, events):
        return self._poller.modify(fd, self._map_events(events))
    
    def unregister(self, fd):
        return self._poller.unregister(fd)
    
    def poll(self, timeout):
        """poll in seconds rather than milliseconds.
        
        Event masks will be IOLoop.READ/WRITE/ERROR
        """
        z_events = self._poller.poll(1000*timeout)
        return [ (fd,self._remap_events(evt)) for (fd,evt) in z_events ]
    
    def close(self):
        pass


class ZMQIOLoop(PollIOLoop):
    """ZMQ subclass of tornado's IOLoop"""
    def initialize(self, impl=None, **kwargs):
        impl = ZMQPoller() if impl is None else impl
        super(ZMQIOLoop, self).initialize(impl=impl, **kwargs)
    
    @staticmethod
    def instance():
        """Returns a global `IOLoop` instance.
        
        Most applications have a single, global `IOLoop` running on the
        main thread.  Use this method to get this instance from
        another thread.  To get the current thread's `IOLoop`, use `current()`.
        """
        # install ZMQIOLoop as the active IOLoop implementation
        # when using tornado 3
        if tornado_version >= (3,):
            PollIOLoop.configure(ZMQIOLoop)
        return PollIOLoop.instance()
    
    def start(self):
        try:
            super(ZMQIOLoop, self).start()
        except ZMQError as e:
            if e.errno == ETERM:
                # quietly return on ETERM
                pass
            else:
                raise e


if tornado_version >= (3,0) and tornado_version < (3,1):
    def backport_close(self, all_fds=False):
        """backport IOLoop.close to 3.0 from 3.1 (supports fd.close() method)"""
        from zmq.eventloop.minitornado.ioloop import PollIOLoop as mini_loop
        return mini_loop.close.__get__(self)(all_fds)
    ZMQIOLoop.close = backport_close


# public API name
IOLoop = ZMQIOLoop


def install():
    """set the tornado IOLoop instance with the pyzmq IOLoop.
    
    After calling this function, tornado's IOLoop.instance() and pyzmq's
    IOLoop.instance() will return the same object.
    
    An assertion error will be raised if tornado's IOLoop has been initialized
    prior to calling this function.
    """
    from tornado import ioloop
    # check if tornado's IOLoop is already initialized to something other
    # than the pyzmq IOLoop instance:
    assert (not ioloop.IOLoop.initialized()) or \
        ioloop.IOLoop.instance() is IOLoop.instance(), "tornado IOLoop already initialized"
    
    if tornado_version >= (3,):
        # tornado 3 has an official API for registering new defaults, yay!
        ioloop.IOLoop.configure(ZMQIOLoop)
    else:
        # we have to set the global instance explicitly
        ioloop.IOLoop._instance = IOLoop.instance()


########NEW FILE########
__FILENAME__ = concurrent
"""pyzmq does not ship tornado's futures,
this just raises informative NotImplementedErrors to avoid having to change too much code.
"""

class NotImplementedFuture(object):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("pyzmq does not ship tornado's Futures, "
            "install tornado >= 3.0 for future support."
        )

Future = TracebackFuture = NotImplementedFuture

########NEW FILE########
__FILENAME__ = ioloop
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""An I/O event loop for non-blocking sockets.

Typical applications will use a single `IOLoop` object, in the
`IOLoop.instance` singleton.  The `IOLoop.start` method should usually
be called at the end of the ``main()`` function.  Atypical applications may
use more than one `IOLoop`, such as one `IOLoop` per thread, or per `unittest`
case.

In addition to I/O events, the `IOLoop` can also schedule time-based events.
`IOLoop.add_timeout` is a non-blocking alternative to `time.sleep`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import datetime
import errno
import functools
import heapq
import logging
import numbers
import os
import select
import sys
import threading
import time
import traceback

from .concurrent import Future, TracebackFuture
from .log import app_log, gen_log
from . import stack_context
from .util import Configurable

try:
    import signal
except ImportError:
    signal = None

try:
    import thread  # py2
except ImportError:
    import _thread as thread  # py3

from .platform.auto import set_close_exec, Waker


class TimeoutError(Exception):
    pass


class IOLoop(Configurable):
    """A level-triggered I/O loop.

    We use ``epoll`` (Linux) or ``kqueue`` (BSD and Mac OS X) if they
    are available, or else we fall back on select(). If you are
    implementing a system that needs to handle thousands of
    simultaneous connections, you should use a system that supports
    either ``epoll`` or ``kqueue``.

    Example usage for a simple TCP server::

        import errno
        import functools
        import ioloop
        import socket

        def connection_ready(sock, fd, events):
            while True:
                try:
                    connection, address = sock.accept()
                except socket.error, e:
                    if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                        raise
                    return
                connection.setblocking(0)
                handle_connection(connection, address)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        sock.bind(("", port))
        sock.listen(128)

        io_loop = ioloop.IOLoop.instance()
        callback = functools.partial(connection_ready, sock)
        io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
        io_loop.start()

    """
    # Constants from the epoll module
    _EPOLLIN = 0x001
    _EPOLLPRI = 0x002
    _EPOLLOUT = 0x004
    _EPOLLERR = 0x008
    _EPOLLHUP = 0x010
    _EPOLLRDHUP = 0x2000
    _EPOLLONESHOT = (1 << 30)
    _EPOLLET = (1 << 31)

    # Our events map exactly to the epoll events
    NONE = 0
    READ = _EPOLLIN
    WRITE = _EPOLLOUT
    ERROR = _EPOLLERR | _EPOLLHUP

    # Global lock for creating global IOLoop instance
    _instance_lock = threading.Lock()

    _current = threading.local()

    @staticmethod
    def instance():
        """Returns a global `IOLoop` instance.

        Most applications have a single, global `IOLoop` running on the
        main thread.  Use this method to get this instance from
        another thread.  To get the current thread's `IOLoop`, use `current()`.
        """
        if not hasattr(IOLoop, "_instance"):
            with IOLoop._instance_lock:
                if not hasattr(IOLoop, "_instance"):
                    # New instance after double check
                    IOLoop._instance = IOLoop()
        return IOLoop._instance

    @staticmethod
    def initialized():
        """Returns true if the singleton instance has been created."""
        return hasattr(IOLoop, "_instance")

    def install(self):
        """Installs this `IOLoop` object as the singleton instance.

        This is normally not necessary as `instance()` will create
        an `IOLoop` on demand, but you may want to call `install` to use
        a custom subclass of `IOLoop`.
        """
        assert not IOLoop.initialized()
        IOLoop._instance = self

    @staticmethod
    def current():
        """Returns the current thread's `IOLoop`.

        If an `IOLoop` is currently running or has been marked as current
        by `make_current`, returns that instance.  Otherwise returns
        `IOLoop.instance()`, i.e. the main thread's `IOLoop`.

        A common pattern for classes that depend on ``IOLoops`` is to use
        a default argument to enable programs with multiple ``IOLoops``
        but not require the argument for simpler applications::

            class MyClass(object):
                def __init__(self, io_loop=None):
                    self.io_loop = io_loop or IOLoop.current()

        In general you should use `IOLoop.current` as the default when
        constructing an asynchronous object, and use `IOLoop.instance`
        when you mean to communicate to the main thread from a different
        one.
        """
        current = getattr(IOLoop._current, "instance", None)
        if current is None:
            return IOLoop.instance()
        return current

    def make_current(self):
        """Makes this the `IOLoop` for the current thread.

        An `IOLoop` automatically becomes current for its thread
        when it is started, but it is sometimes useful to call
        `make_current` explictly before starting the `IOLoop`,
        so that code run at startup time can find the right
        instance.
        """
        IOLoop._current.instance = self

    @staticmethod
    def clear_current():
        IOLoop._current.instance = None

    @classmethod
    def configurable_base(cls):
        return IOLoop

    @classmethod
    def configurable_default(cls):
        # this is the only patch to IOLoop:
        from zmq.eventloop.ioloop import ZMQIOLoop
        return ZMQIOLoop
        # the remainder of this method is unused,
        # but left for preservation reasons
        if hasattr(select, "epoll"):
            from tornado.platform.epoll import EPollIOLoop
            return EPollIOLoop
        if hasattr(select, "kqueue"):
            # Python 2.6+ on BSD or Mac
            from tornado.platform.kqueue import KQueueIOLoop
            return KQueueIOLoop
        from tornado.platform.select import SelectIOLoop
        return SelectIOLoop

    def initialize(self):
        pass

    def close(self, all_fds=False):
        """Closes the `IOLoop`, freeing any resources used.

        If ``all_fds`` is true, all file descriptors registered on the
        IOLoop will be closed (not just the ones created by the
        `IOLoop` itself).

        Many applications will only use a single `IOLoop` that runs for the
        entire lifetime of the process.  In that case closing the `IOLoop`
        is not necessary since everything will be cleaned up when the
        process exits.  `IOLoop.close` is provided mainly for scenarios
        such as unit tests, which create and destroy a large number of
        ``IOLoops``.

        An `IOLoop` must be completely stopped before it can be closed.  This
        means that `IOLoop.stop()` must be called *and* `IOLoop.start()` must
        be allowed to return before attempting to call `IOLoop.close()`.
        Therefore the call to `close` will usually appear just after
        the call to `start` rather than near the call to `stop`.

        .. versionchanged:: 3.1
           If the `IOLoop` implementation supports non-integer objects
           for "file descriptors", those objects will have their
           ``close`` method when ``all_fds`` is true.
        """
        raise NotImplementedError()

    def add_handler(self, fd, handler, events):
        """Registers the given handler to receive the given events for fd.

        The ``events`` argument is a bitwise or of the constants
        ``IOLoop.READ``, ``IOLoop.WRITE``, and ``IOLoop.ERROR``.

        When an event occurs, ``handler(fd, events)`` will be run.
        """
        raise NotImplementedError()

    def update_handler(self, fd, events):
        """Changes the events we listen for fd."""
        raise NotImplementedError()

    def remove_handler(self, fd):
        """Stop listening for events on fd."""
        raise NotImplementedError()

    def set_blocking_signal_threshold(self, seconds, action):
        """Sends a signal if the `IOLoop` is blocked for more than
        ``s`` seconds.

        Pass ``seconds=None`` to disable.  Requires Python 2.6 on a unixy
        platform.

        The action parameter is a Python signal handler.  Read the
        documentation for the `signal` module for more information.
        If ``action`` is None, the process will be killed if it is
        blocked for too long.
        """
        raise NotImplementedError()

    def set_blocking_log_threshold(self, seconds):
        """Logs a stack trace if the `IOLoop` is blocked for more than
        ``s`` seconds.

        Equivalent to ``set_blocking_signal_threshold(seconds,
        self.log_stack)``
        """
        self.set_blocking_signal_threshold(seconds, self.log_stack)

    def log_stack(self, signal, frame):
        """Signal handler to log the stack trace of the current thread.

        For use with `set_blocking_signal_threshold`.
        """
        gen_log.warning('IOLoop blocked for %f seconds in\n%s',
                        self._blocking_signal_threshold,
                        ''.join(traceback.format_stack(frame)))

    def start(self):
        """Starts the I/O loop.

        The loop will run until one of the callbacks calls `stop()`, which
        will make the loop stop after the current event iteration completes.
        """
        raise NotImplementedError()

    def stop(self):
        """Stop the I/O loop.

        If the event loop is not currently running, the next call to `start()`
        will return immediately.

        To use asynchronous methods from otherwise-synchronous code (such as
        unit tests), you can start and stop the event loop like this::

          ioloop = IOLoop()
          async_method(ioloop=ioloop, callback=ioloop.stop)
          ioloop.start()

        ``ioloop.start()`` will return after ``async_method`` has run
        its callback, whether that callback was invoked before or
        after ``ioloop.start``.

        Note that even after `stop` has been called, the `IOLoop` is not
        completely stopped until `IOLoop.start` has also returned.
        Some work that was scheduled before the call to `stop` may still
        be run before the `IOLoop` shuts down.
        """
        raise NotImplementedError()

    def run_sync(self, func, timeout=None):
        """Starts the `IOLoop`, runs the given function, and stops the loop.

        If the function returns a `.Future`, the `IOLoop` will run
        until the future is resolved.  If it raises an exception, the
        `IOLoop` will stop and the exception will be re-raised to the
        caller.

        The keyword-only argument ``timeout`` may be used to set
        a maximum duration for the function.  If the timeout expires,
        a `TimeoutError` is raised.

        This method is useful in conjunction with `tornado.gen.coroutine`
        to allow asynchronous calls in a ``main()`` function::

            @gen.coroutine
            def main():
                # do stuff...

            if __name__ == '__main__':
                IOLoop.instance().run_sync(main)
        """
        future_cell = [None]

        def run():
            try:
                result = func()
            except Exception:
                future_cell[0] = TracebackFuture()
                future_cell[0].set_exc_info(sys.exc_info())
            else:
                if isinstance(result, Future):
                    future_cell[0] = result
                else:
                    future_cell[0] = Future()
                    future_cell[0].set_result(result)
            self.add_future(future_cell[0], lambda future: self.stop())
        self.add_callback(run)
        if timeout is not None:
            timeout_handle = self.add_timeout(self.time() + timeout, self.stop)
        self.start()
        if timeout is not None:
            self.remove_timeout(timeout_handle)
        if not future_cell[0].done():
            raise TimeoutError('Operation timed out after %s seconds' % timeout)
        return future_cell[0].result()

    def time(self):
        """Returns the current time according to the `IOLoop`'s clock.

        The return value is a floating-point number relative to an
        unspecified time in the past.

        By default, the `IOLoop`'s time function is `time.time`.  However,
        it may be configured to use e.g. `time.monotonic` instead.
        Calls to `add_timeout` that pass a number instead of a
        `datetime.timedelta` should use this function to compute the
        appropriate time, so they can work no matter what time function
        is chosen.
        """
        return time.time()

    def add_timeout(self, deadline, callback):
        """Runs the ``callback`` at the time ``deadline`` from the I/O loop.

        Returns an opaque handle that may be passed to
        `remove_timeout` to cancel.

        ``deadline`` may be a number denoting a time (on the same
        scale as `IOLoop.time`, normally `time.time`), or a
        `datetime.timedelta` object for a deadline relative to the
        current time.

        Note that it is not safe to call `add_timeout` from other threads.
        Instead, you must use `add_callback` to transfer control to the
        `IOLoop`'s thread, and then call `add_timeout` from there.
        """
        raise NotImplementedError()

    def remove_timeout(self, timeout):
        """Cancels a pending timeout.

        The argument is a handle as returned by `add_timeout`.  It is
        safe to call `remove_timeout` even if the callback has already
        been run.
        """
        raise NotImplementedError()

    def add_callback(self, callback, *args, **kwargs):
        """Calls the given callback on the next I/O loop iteration.

        It is safe to call this method from any thread at any time,
        except from a signal handler.  Note that this is the **only**
        method in `IOLoop` that makes this thread-safety guarantee; all
        other interaction with the `IOLoop` must be done from that
        `IOLoop`'s thread.  `add_callback()` may be used to transfer
        control from other threads to the `IOLoop`'s thread.

        To add a callback from a signal handler, see
        `add_callback_from_signal`.
        """
        raise NotImplementedError()

    def add_callback_from_signal(self, callback, *args, **kwargs):
        """Calls the given callback on the next I/O loop iteration.

        Safe for use from a Python signal handler; should not be used
        otherwise.

        Callbacks added with this method will be run without any
        `.stack_context`, to avoid picking up the context of the function
        that was interrupted by the signal.
        """
        raise NotImplementedError()

    def add_future(self, future, callback):
        """Schedules a callback on the ``IOLoop`` when the given
        `.Future` is finished.

        The callback is invoked with one argument, the
        `.Future`.
        """
        assert isinstance(future, Future)
        callback = stack_context.wrap(callback)
        future.add_done_callback(
            lambda future: self.add_callback(callback, future))

    def _run_callback(self, callback):
        """Runs a callback with error handling.

        For use in subclasses.
        """
        try:
            callback()
        except Exception:
            self.handle_callback_exception(callback)

    def handle_callback_exception(self, callback):
        """This method is called whenever a callback run by the `IOLoop`
        throws an exception.

        By default simply logs the exception as an error.  Subclasses
        may override this method to customize reporting of exceptions.

        The exception itself is not passed explicitly, but is available
        in `sys.exc_info`.
        """
        app_log.error("Exception in callback %r", callback, exc_info=True)


class PollIOLoop(IOLoop):
    """Base class for IOLoops built around a select-like function.

    For concrete implementations, see `tornado.platform.epoll.EPollIOLoop`
    (Linux), `tornado.platform.kqueue.KQueueIOLoop` (BSD and Mac), or
    `tornado.platform.select.SelectIOLoop` (all platforms).
    """
    def initialize(self, impl, time_func=None):
        super(PollIOLoop, self).initialize()
        self._impl = impl
        if hasattr(self._impl, 'fileno'):
            set_close_exec(self._impl.fileno())
        self.time_func = time_func or time.time
        self._handlers = {}
        self._events = {}
        self._callbacks = []
        self._callback_lock = threading.Lock()
        self._timeouts = []
        self._cancellations = 0
        self._running = False
        self._stopped = False
        self._closing = False
        self._thread_ident = None
        self._blocking_signal_threshold = None

        # Create a pipe that we send bogus data to when we want to wake
        # the I/O loop when it is idle
        self._waker = Waker()
        self.add_handler(self._waker.fileno(),
                         lambda fd, events: self._waker.consume(),
                         self.READ)

    def close(self, all_fds=False):
        with self._callback_lock:
            self._closing = True
        self.remove_handler(self._waker.fileno())
        if all_fds:
            for fd in self._handlers.keys():
                try:
                    close_method = getattr(fd, 'close', None)
                    if close_method is not None:
                        close_method()
                    else:
                        os.close(fd)
                except Exception:
                    gen_log.debug("error closing fd %s", fd, exc_info=True)
        self._waker.close()
        self._impl.close()

    def add_handler(self, fd, handler, events):
        self._handlers[fd] = stack_context.wrap(handler)
        self._impl.register(fd, events | self.ERROR)

    def update_handler(self, fd, events):
        self._impl.modify(fd, events | self.ERROR)

    def remove_handler(self, fd):
        self._handlers.pop(fd, None)
        self._events.pop(fd, None)
        try:
            self._impl.unregister(fd)
        except Exception:
            gen_log.debug("Error deleting fd from IOLoop", exc_info=True)

    def set_blocking_signal_threshold(self, seconds, action):
        if not hasattr(signal, "setitimer"):
            gen_log.error("set_blocking_signal_threshold requires a signal module "
                          "with the setitimer method")
            return
        self._blocking_signal_threshold = seconds
        if seconds is not None:
            signal.signal(signal.SIGALRM,
                          action if action is not None else signal.SIG_DFL)

    def start(self):
        if not logging.getLogger().handlers:
            # The IOLoop catches and logs exceptions, so it's
            # important that log output be visible.  However, python's
            # default behavior for non-root loggers (prior to python
            # 3.2) is to print an unhelpful "no handlers could be
            # found" message rather than the actual log entry, so we
            # must explicitly configure logging if we've made it this
            # far without anything.
            logging.basicConfig()
        if self._stopped:
            self._stopped = False
            return
        old_current = getattr(IOLoop._current, "instance", None)
        IOLoop._current.instance = self
        self._thread_ident = thread.get_ident()
        self._running = True

        # signal.set_wakeup_fd closes a race condition in event loops:
        # a signal may arrive at the beginning of select/poll/etc
        # before it goes into its interruptible sleep, so the signal
        # will be consumed without waking the select.  The solution is
        # for the (C, synchronous) signal handler to write to a pipe,
        # which will then be seen by select.
        #
        # In python's signal handling semantics, this only matters on the
        # main thread (fortunately, set_wakeup_fd only works on the main
        # thread and will raise a ValueError otherwise).
        #
        # If someone has already set a wakeup fd, we don't want to
        # disturb it.  This is an issue for twisted, which does its
        # SIGCHILD processing in response to its own wakeup fd being
        # written to.  As long as the wakeup fd is registered on the IOLoop,
        # the loop will still wake up and everything should work.
        old_wakeup_fd = None
        if hasattr(signal, 'set_wakeup_fd') and os.name == 'posix':
            # requires python 2.6+, unix.  set_wakeup_fd exists but crashes
            # the python process on windows.
            try:
                old_wakeup_fd = signal.set_wakeup_fd(self._waker.write_fileno())
                if old_wakeup_fd != -1:
                    # Already set, restore previous value.  This is a little racy,
                    # but there's no clean get_wakeup_fd and in real use the
                    # IOLoop is just started once at the beginning.
                    signal.set_wakeup_fd(old_wakeup_fd)
                    old_wakeup_fd = None
            except ValueError:  # non-main thread
                pass

        while True:
            poll_timeout = 3600.0

            # Prevent IO event starvation by delaying new callbacks
            # to the next iteration of the event loop.
            with self._callback_lock:
                callbacks = self._callbacks
                self._callbacks = []
            for callback in callbacks:
                self._run_callback(callback)

            if self._timeouts:
                now = self.time()
                while self._timeouts:
                    if self._timeouts[0].callback is None:
                        # the timeout was cancelled
                        heapq.heappop(self._timeouts)
                        self._cancellations -= 1
                    elif self._timeouts[0].deadline <= now:
                        timeout = heapq.heappop(self._timeouts)
                        self._run_callback(timeout.callback)
                    else:
                        seconds = self._timeouts[0].deadline - now
                        poll_timeout = min(seconds, poll_timeout)
                        break
                if (self._cancellations > 512
                        and self._cancellations > (len(self._timeouts) >> 1)):
                    # Clean up the timeout queue when it gets large and it's
                    # more than half cancellations.
                    self._cancellations = 0
                    self._timeouts = [x for x in self._timeouts
                                      if x.callback is not None]
                    heapq.heapify(self._timeouts)

            if self._callbacks:
                # If any callbacks or timeouts called add_callback,
                # we don't want to wait in poll() before we run them.
                poll_timeout = 0.0

            if not self._running:
                break

            if self._blocking_signal_threshold is not None:
                # clear alarm so it doesn't fire while poll is waiting for
                # events.
                signal.setitimer(signal.ITIMER_REAL, 0, 0)

            try:
                event_pairs = self._impl.poll(poll_timeout)
            except Exception as e:
                # Depending on python version and IOLoop implementation,
                # different exception types may be thrown and there are
                # two ways EINTR might be signaled:
                # * e.errno == errno.EINTR
                # * e.args is like (errno.EINTR, 'Interrupted system call')
                if (getattr(e, 'errno', None) == errno.EINTR or
                    (isinstance(getattr(e, 'args', None), tuple) and
                     len(e.args) == 2 and e.args[0] == errno.EINTR)):
                    continue
                else:
                    raise

            if self._blocking_signal_threshold is not None:
                signal.setitimer(signal.ITIMER_REAL,
                                 self._blocking_signal_threshold, 0)

            # Pop one fd at a time from the set of pending fds and run
            # its handler. Since that handler may perform actions on
            # other file descriptors, there may be reentrant calls to
            # this IOLoop that update self._events
            self._events.update(event_pairs)
            while self._events:
                fd, events = self._events.popitem()
                try:
                    self._handlers[fd](fd, events)
                except (OSError, IOError) as e:
                    if e.args[0] == errno.EPIPE:
                        # Happens when the client closes the connection
                        pass
                    else:
                        app_log.error("Exception in I/O handler for fd %s",
                                      fd, exc_info=True)
                except Exception:
                    app_log.error("Exception in I/O handler for fd %s",
                                  fd, exc_info=True)
        # reset the stopped flag so another start/stop pair can be issued
        self._stopped = False
        if self._blocking_signal_threshold is not None:
            signal.setitimer(signal.ITIMER_REAL, 0, 0)
        IOLoop._current.instance = old_current
        if old_wakeup_fd is not None:
            signal.set_wakeup_fd(old_wakeup_fd)

    def stop(self):
        self._running = False
        self._stopped = True
        self._waker.wake()

    def time(self):
        return self.time_func()

    def add_timeout(self, deadline, callback):
        timeout = _Timeout(deadline, stack_context.wrap(callback), self)
        heapq.heappush(self._timeouts, timeout)
        return timeout

    def remove_timeout(self, timeout):
        # Removing from a heap is complicated, so just leave the defunct
        # timeout object in the queue (see discussion in
        # http://docs.python.org/library/heapq.html).
        # If this turns out to be a problem, we could add a garbage
        # collection pass whenever there are too many dead timeouts.
        timeout.callback = None
        self._cancellations += 1

    def add_callback(self, callback, *args, **kwargs):
        with self._callback_lock:
            if self._closing:
                raise RuntimeError("IOLoop is closing")
            list_empty = not self._callbacks
            self._callbacks.append(functools.partial(
                stack_context.wrap(callback), *args, **kwargs))
        if list_empty and thread.get_ident() != self._thread_ident:
            # If we're in the IOLoop's thread, we know it's not currently
            # polling.  If we're not, and we added the first callback to an
            # empty list, we may need to wake it up (it may wake up on its
            # own, but an occasional extra wake is harmless).  Waking
            # up a polling IOLoop is relatively expensive, so we try to
            # avoid it when we can.
            self._waker.wake()

    def add_callback_from_signal(self, callback, *args, **kwargs):
        with stack_context.NullContext():
            if thread.get_ident() != self._thread_ident:
                # if the signal is handled on another thread, we can add
                # it normally (modulo the NullContext)
                self.add_callback(callback, *args, **kwargs)
            else:
                # If we're on the IOLoop's thread, we cannot use
                # the regular add_callback because it may deadlock on
                # _callback_lock.  Blindly insert into self._callbacks.
                # This is safe because the GIL makes list.append atomic.
                # One subtlety is that if the signal interrupted the
                # _callback_lock block in IOLoop.start, we may modify
                # either the old or new version of self._callbacks,
                # but either way will work.
                self._callbacks.append(functools.partial(
                    stack_context.wrap(callback), *args, **kwargs))


class _Timeout(object):
    """An IOLoop timeout, a UNIX timestamp and a callback"""

    # Reduce memory overhead when there are lots of pending callbacks
    __slots__ = ['deadline', 'callback']

    def __init__(self, deadline, callback, io_loop):
        if isinstance(deadline, numbers.Real):
            self.deadline = deadline
        elif isinstance(deadline, datetime.timedelta):
            self.deadline = io_loop.time() + _Timeout.timedelta_to_seconds(deadline)
        else:
            raise TypeError("Unsupported deadline %r" % deadline)
        self.callback = callback

    @staticmethod
    def timedelta_to_seconds(td):
        """Equivalent to td.total_seconds() (introduced in python 2.7)."""
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / float(10 ** 6)

    # Comparison methods to sort by deadline, with object id as a tiebreaker
    # to guarantee a consistent ordering.  The heapq module uses __le__
    # in python2.5, and __lt__ in 2.6+ (sort() and most other comparisons
    # use __lt__).
    def __lt__(self, other):
        return ((self.deadline, id(self)) <
                (other.deadline, id(other)))

    def __le__(self, other):
        return ((self.deadline, id(self)) <=
                (other.deadline, id(other)))


class PeriodicCallback(object):
    """Schedules the given callback to be called periodically.

    The callback is called every ``callback_time`` milliseconds.

    `start` must be called after the `PeriodicCallback` is created.
    """
    def __init__(self, callback, callback_time, io_loop=None):
        self.callback = callback
        if callback_time <= 0:
            raise ValueError("Periodic callback must have a positive callback_time")
        self.callback_time = callback_time
        self.io_loop = io_loop or IOLoop.current()
        self._running = False
        self._timeout = None

    def start(self):
        """Starts the timer."""
        self._running = True
        self._next_timeout = self.io_loop.time()
        self._schedule_next()

    def stop(self):
        """Stops the timer."""
        self._running = False
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

    def _run(self):
        if not self._running:
            return
        try:
            self.callback()
        except Exception:
            app_log.error("Error in periodic callback", exc_info=True)
        self._schedule_next()

    def _schedule_next(self):
        if self._running:
            current_time = self.io_loop.time()
            while self._next_timeout <= current_time:
                self._next_timeout += self.callback_time / 1000.0
            self._timeout = self.io_loop.add_timeout(self._next_timeout, self._run)

########NEW FILE########
__FILENAME__ = log
"""minimal subset of tornado.log for zmq.eventloop.minitornado"""

import logging

app_log = logging.getLogger("tornado.application")
gen_log = logging.getLogger("tornado.general")

########NEW FILE########
__FILENAME__ = auto
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Implementation of platform-specific functionality.

For each function or class described in `tornado.platform.interface`,
the appropriate platform-specific implementation exists in this module.
Most code that needs access to this functionality should do e.g.::

    from tornado.platform.auto import set_close_exec
"""

from __future__ import absolute_import, division, print_function, with_statement

import os

if os.name == 'nt':
    from .common import Waker
    from .windows import set_close_exec
else:
    from .posix import set_close_exec, Waker

try:
    # monotime monkey-patches the time module to have a monotonic function
    # in versions of python before 3.3.
    import monotime
except ImportError:
    pass
try:
    from time import monotonic as monotonic_time
except ImportError:
    monotonic_time = None

########NEW FILE########
__FILENAME__ = common
"""Lowest-common-denominator implementations of platform functionality."""
from __future__ import absolute_import, division, print_function, with_statement

import errno
import socket

from . import interface


class Waker(interface.Waker):
    """Create an OS independent asynchronous pipe.

    For use on platforms that don't have os.pipe() (or where pipes cannot
    be passed to select()), but do have sockets.  This includes Windows
    and Jython.
    """
    def __init__(self):
        # Based on Zope async.py: http://svn.zope.org/zc.ngi/trunk/src/zc/ngi/async.py

        self.writer = socket.socket()
        # Disable buffering -- pulling the trigger sends 1 byte,
        # and we want that sent immediately, to wake up ASAP.
        self.writer.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        count = 0
        while 1:
            count += 1
            # Bind to a local port; for efficiency, let the OS pick
            # a free port for us.
            # Unfortunately, stress tests showed that we may not
            # be able to connect to that port ("Address already in
            # use") despite that the OS picked it.  This appears
            # to be a race bug in the Windows socket implementation.
            # So we loop until a connect() succeeds (almost always
            # on the first try).  See the long thread at
            # http://mail.zope.org/pipermail/zope/2005-July/160433.html
            # for hideous details.
            a = socket.socket()
            a.bind(("127.0.0.1", 0))
            a.listen(1)
            connect_address = a.getsockname()  # assigned (host, port) pair
            try:
                self.writer.connect(connect_address)
                break    # success
            except socket.error as detail:
                if (not hasattr(errno, 'WSAEADDRINUSE') or
                        detail[0] != errno.WSAEADDRINUSE):
                    # "Address already in use" is the only error
                    # I've seen on two WinXP Pro SP2 boxes, under
                    # Pythons 2.3.5 and 2.4.1.
                    raise
                # (10048, 'Address already in use')
                # assert count <= 2 # never triggered in Tim's tests
                if count >= 10:  # I've never seen it go above 2
                    a.close()
                    self.writer.close()
                    raise socket.error("Cannot bind trigger!")
                # Close `a` and try again.  Note:  I originally put a short
                # sleep() here, but it didn't appear to help or hurt.
                a.close()

        self.reader, addr = a.accept()
        self.reader.setblocking(0)
        self.writer.setblocking(0)
        a.close()
        self.reader_fd = self.reader.fileno()

    def fileno(self):
        return self.reader.fileno()

    def write_fileno(self):
        return self.writer.fileno()

    def wake(self):
        try:
            self.writer.send(b"x")
        except (IOError, socket.error):
            pass

    def consume(self):
        try:
            while True:
                result = self.reader.recv(1024)
                if not result:
                    break
        except (IOError, socket.error):
            pass

    def close(self):
        self.reader.close()
        self.writer.close()

########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Interfaces for platform-specific functionality.

This module exists primarily for documentation purposes and as base classes
for other tornado.platform modules.  Most code should import the appropriate
implementation from `tornado.platform.auto`.
"""

from __future__ import absolute_import, division, print_function, with_statement


def set_close_exec(fd):
    """Sets the close-on-exec bit (``FD_CLOEXEC``)for a file descriptor."""
    raise NotImplementedError()


class Waker(object):
    """A socket-like object that can wake another thread from ``select()``.

    The `~tornado.ioloop.IOLoop` will add the Waker's `fileno()` to
    its ``select`` (or ``epoll`` or ``kqueue``) calls.  When another
    thread wants to wake up the loop, it calls `wake`.  Once it has woken
    up, it will call `consume` to do any necessary per-wake cleanup.  When
    the ``IOLoop`` is closed, it closes its waker too.
    """
    def fileno(self):
        """Returns the read file descriptor for this waker.

        Must be suitable for use with ``select()`` or equivalent on the
        local platform.
        """
        raise NotImplementedError()

    def write_fileno(self):
        """Returns the write file descriptor for this waker."""
        raise NotImplementedError()

    def wake(self):
        """Triggers activity on the waker's file descriptor."""
        raise NotImplementedError()

    def consume(self):
        """Called after the listen has woken up to do any necessary cleanup."""
        raise NotImplementedError()

    def close(self):
        """Closes the waker's file descriptor(s)."""
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = posix
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Posix implementations of platform-specific functionality."""

from __future__ import absolute_import, division, print_function, with_statement

import fcntl
import os

from . import interface


def set_close_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)


def _set_nonblocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


class Waker(interface.Waker):
    def __init__(self):
        r, w = os.pipe()
        _set_nonblocking(r)
        _set_nonblocking(w)
        set_close_exec(r)
        set_close_exec(w)
        self.reader = os.fdopen(r, "rb", 0)
        self.writer = os.fdopen(w, "wb", 0)

    def fileno(self):
        return self.reader.fileno()

    def write_fileno(self):
        return self.writer.fileno()

    def wake(self):
        try:
            self.writer.write(b"x")
        except IOError:
            pass

    def consume(self):
        try:
            while True:
                result = self.reader.read()
                if not result:
                    break
        except IOError:
            pass

    def close(self):
        self.reader.close()
        self.writer.close()

########NEW FILE########
__FILENAME__ = windows
# NOTE: win32 support is currently experimental, and not recommended
# for production use.


from __future__ import absolute_import, division, print_function, with_statement
import ctypes
import ctypes.wintypes

# See: http://msdn.microsoft.com/en-us/library/ms724935(VS.85).aspx
SetHandleInformation = ctypes.windll.kernel32.SetHandleInformation
SetHandleInformation.argtypes = (ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD)
SetHandleInformation.restype = ctypes.wintypes.BOOL

HANDLE_FLAG_INHERIT = 0x00000001


def set_close_exec(fd):
    success = SetHandleInformation(fd, HANDLE_FLAG_INHERIT, 0)
    if not success:
        raise ctypes.GetLastError()

########NEW FILE########
__FILENAME__ = stack_context
#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""`StackContext` allows applications to maintain threadlocal-like state
that follows execution as it moves to other execution contexts.

The motivating examples are to eliminate the need for explicit
``async_callback`` wrappers (as in `tornado.web.RequestHandler`), and to
allow some additional context to be kept for logging.

This is slightly magic, but it's an extension of the idea that an
exception handler is a kind of stack-local state and when that stack
is suspended and resumed in a new context that state needs to be
preserved.  `StackContext` shifts the burden of restoring that state
from each call site (e.g.  wrapping each `.AsyncHTTPClient` callback
in ``async_callback``) to the mechanisms that transfer control from
one context to another (e.g. `.AsyncHTTPClient` itself, `.IOLoop`,
thread pools, etc).

Example usage::

    @contextlib.contextmanager
    def die_on_error():
        try:
            yield
        except Exception:
            logging.error("exception in asynchronous operation",exc_info=True)
            sys.exit(1)

    with StackContext(die_on_error):
        # Any exception thrown here *or in callback and its desendents*
        # will cause the process to exit instead of spinning endlessly
        # in the ioloop.
        http_client.fetch(url, callback)
    ioloop.start()

Most applications shouln't have to work with `StackContext` directly.
Here are a few rules of thumb for when it's necessary:

* If you're writing an asynchronous library that doesn't rely on a
  stack_context-aware library like `tornado.ioloop` or `tornado.iostream`
  (for example, if you're writing a thread pool), use
  `.stack_context.wrap()` before any asynchronous operations to capture the
  stack context from where the operation was started.

* If you're writing an asynchronous library that has some shared
  resources (such as a connection pool), create those shared resources
  within a ``with stack_context.NullContext():`` block.  This will prevent
  ``StackContexts`` from leaking from one request to another.

* If you want to write something like an exception handler that will
  persist across asynchronous calls, create a new `StackContext` (or
  `ExceptionStackContext`), and make your asynchronous calls in a ``with``
  block that references your `StackContext`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import sys
import threading

from .util import raise_exc_info


class StackContextInconsistentError(Exception):
    pass


class _State(threading.local):
    def __init__(self):
        self.contexts = (tuple(), None)
_state = _State()


class StackContext(object):
    """Establishes the given context as a StackContext that will be transferred.

    Note that the parameter is a callable that returns a context
    manager, not the context itself.  That is, where for a
    non-transferable context manager you would say::

      with my_context():

    StackContext takes the function itself rather than its result::

      with StackContext(my_context):

    The result of ``with StackContext() as cb:`` is a deactivation
    callback.  Run this callback when the StackContext is no longer
    needed to ensure that it is not propagated any further (note that
    deactivating a context does not affect any instances of that
    context that are currently pending).  This is an advanced feature
    and not necessary in most applications.
    """
    def __init__(self, context_factory):
        self.context_factory = context_factory
        self.contexts = []
        self.active = True

    def _deactivate(self):
        self.active = False

    # StackContext protocol
    def enter(self):
        context = self.context_factory()
        self.contexts.append(context)
        context.__enter__()

    def exit(self, type, value, traceback):
        context = self.contexts.pop()
        context.__exit__(type, value, traceback)

    # Note that some of this code is duplicated in ExceptionStackContext
    # below.  ExceptionStackContext is more common and doesn't need
    # the full generality of this class.
    def __enter__(self):
        self.old_contexts = _state.contexts
        self.new_contexts = (self.old_contexts[0] + (self,), self)
        _state.contexts = self.new_contexts

        try:
            self.enter()
        except:
            _state.contexts = self.old_contexts
            raise

        return self._deactivate

    def __exit__(self, type, value, traceback):
        try:
            self.exit(type, value, traceback)
        finally:
            final_contexts = _state.contexts
            _state.contexts = self.old_contexts

            # Generator coroutines and with-statements with non-local
            # effects interact badly.  Check here for signs of
            # the stack getting out of sync.
            # Note that this check comes after restoring _state.context
            # so that if it fails things are left in a (relatively)
            # consistent state.
            if final_contexts is not self.new_contexts:
                raise StackContextInconsistentError(
                    'stack_context inconsistency (may be caused by yield '
                    'within a "with StackContext" block)')

            # Break up a reference to itself to allow for faster GC on CPython.
            self.new_contexts = None


class ExceptionStackContext(object):
    """Specialization of StackContext for exception handling.

    The supplied ``exception_handler`` function will be called in the
    event of an uncaught exception in this context.  The semantics are
    similar to a try/finally clause, and intended use cases are to log
    an error, close a socket, or similar cleanup actions.  The
    ``exc_info`` triple ``(type, value, traceback)`` will be passed to the
    exception_handler function.

    If the exception handler returns true, the exception will be
    consumed and will not be propagated to other exception handlers.
    """
    def __init__(self, exception_handler):
        self.exception_handler = exception_handler
        self.active = True

    def _deactivate(self):
        self.active = False

    def exit(self, type, value, traceback):
        if type is not None:
            return self.exception_handler(type, value, traceback)

    def __enter__(self):
        self.old_contexts = _state.contexts
        self.new_contexts = (self.old_contexts[0], self)
        _state.contexts = self.new_contexts

        return self._deactivate

    def __exit__(self, type, value, traceback):
        try:
            if type is not None:
                return self.exception_handler(type, value, traceback)
        finally:
            final_contexts = _state.contexts
            _state.contexts = self.old_contexts

            if final_contexts is not self.new_contexts:
                raise StackContextInconsistentError(
                    'stack_context inconsistency (may be caused by yield '
                    'within a "with StackContext" block)')

            # Break up a reference to itself to allow for faster GC on CPython.
            self.new_contexts = None


class NullContext(object):
    """Resets the `StackContext`.

    Useful when creating a shared resource on demand (e.g. an
    `.AsyncHTTPClient`) where the stack that caused the creating is
    not relevant to future operations.
    """
    def __enter__(self):
        self.old_contexts = _state.contexts
        _state.contexts = (tuple(), None)

    def __exit__(self, type, value, traceback):
        _state.contexts = self.old_contexts


def _remove_deactivated(contexts):
    """Remove deactivated handlers from the chain"""
    # Clean ctx handlers
    stack_contexts = tuple([h for h in contexts[0] if h.active])

    # Find new head
    head = contexts[1]
    while head is not None and not head.active:
        head = head.old_contexts[1]

    # Process chain
    ctx = head
    while ctx is not None:
        parent = ctx.old_contexts[1]

        while parent is not None:
            if parent.active:
                break
            ctx.old_contexts = parent.old_contexts
            parent = parent.old_contexts[1]

        ctx = parent

    return (stack_contexts, head)


def wrap(fn):
    """Returns a callable object that will restore the current `StackContext`
    when executed.

    Use this whenever saving a callback to be executed later in a
    different execution context (either in a different thread or
    asynchronously in the same thread).
    """
    # Check if function is already wrapped
    if fn is None or hasattr(fn, '_wrapped'):
        return fn

    # Capture current stack head
    # TODO: Any other better way to store contexts and update them in wrapped function?
    cap_contexts = [_state.contexts]

    def wrapped(*args, **kwargs):
        ret = None
        try:
            # Capture old state
            current_state = _state.contexts

            # Remove deactivated items
            cap_contexts[0] = contexts = _remove_deactivated(cap_contexts[0])

            # Force new state
            _state.contexts = contexts

            # Current exception
            exc = (None, None, None)
            top = None

            # Apply stack contexts
            last_ctx = 0
            stack = contexts[0]

            # Apply state
            for n in stack:
                try:
                    n.enter()
                    last_ctx += 1
                except:
                    # Exception happened. Record exception info and store top-most handler
                    exc = sys.exc_info()
                    top = n.old_contexts[1]

            # Execute callback if no exception happened while restoring state
            if top is None:
                try:
                    ret = fn(*args, **kwargs)
                except:
                    exc = sys.exc_info()
                    top = contexts[1]

            # If there was exception, try to handle it by going through the exception chain
            if top is not None:
                exc = _handle_exception(top, exc)
            else:
                # Otherwise take shorter path and run stack contexts in reverse order
                while last_ctx > 0:
                    last_ctx -= 1
                    c = stack[last_ctx]

                    try:
                        c.exit(*exc)
                    except:
                        exc = sys.exc_info()
                        top = c.old_contexts[1]
                        break
                else:
                    top = None

                # If if exception happened while unrolling, take longer exception handler path
                if top is not None:
                    exc = _handle_exception(top, exc)

            # If exception was not handled, raise it
            if exc != (None, None, None):
                raise_exc_info(exc)
        finally:
            _state.contexts = current_state
        return ret

    wrapped._wrapped = True
    return wrapped


def _handle_exception(tail, exc):
    while tail is not None:
        try:
            if tail.exit(*exc):
                exc = (None, None, None)
        except:
            exc = sys.exc_info()

        tail = tail.old_contexts[1]

    return exc


def run_with_stack_context(context, func):
    """Run a coroutine ``func`` in the given `StackContext`.

    It is not safe to have a ``yield`` statement within a ``with StackContext``
    block, so it is difficult to use stack context with `.gen.coroutine`.
    This helper function runs the function in the correct context while
    keeping the ``yield`` and ``with`` statements syntactically separate.

    Example::

        @gen.coroutine
        def incorrect():
            with StackContext(ctx):
                # ERROR: this will raise StackContextInconsistentError
                yield other_coroutine()

        @gen.coroutine
        def correct():
            yield run_with_stack_context(StackContext(ctx), other_coroutine)

    .. versionadded:: 3.1
    """
    with context:
        return func()

########NEW FILE########
__FILENAME__ = util
"""Miscellaneous utility functions and classes.

This module is used internally by Tornado.  It is not necessarily expected
that the functions and classes defined here will be useful to other
applications, but they are documented here in case they are.

The one public-facing part of this module is the `Configurable` class
and its `~Configurable.configure` method, which becomes a part of the
interface of its subclasses, including `.AsyncHTTPClient`, `.IOLoop`,
and `.Resolver`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import sys


def import_object(name):
    """Imports an object by name.

    import_object('x') is equivalent to 'import x'.
    import_object('x.y.z') is equivalent to 'from x.y import z'.

    >>> import tornado.escape
    >>> import_object('tornado.escape') is tornado.escape
    True
    >>> import_object('tornado.escape.utf8') is tornado.escape.utf8
    True
    >>> import_object('tornado') is tornado
    True
    >>> import_object('tornado.missing_module')
    Traceback (most recent call last):
        ...
    ImportError: No module named missing_module
    """
    if name.count('.') == 0:
        return __import__(name, None, None)

    parts = name.split('.')
    obj = __import__('.'.join(parts[:-1]), None, None, [parts[-1]], 0)
    try:
        return getattr(obj, parts[-1])
    except AttributeError:
        raise ImportError("No module named %s" % parts[-1])


# Fake unicode literal support:  Python 3.2 doesn't have the u'' marker for
# literal strings, and alternative solutions like "from __future__ import
# unicode_literals" have other problems (see PEP 414).  u() can be applied
# to ascii strings that include \u escapes (but they must not contain
# literal non-ascii characters).
if type('') is not type(b''):
    def u(s):
        return s
    bytes_type = bytes
    unicode_type = str
    basestring_type = str
else:
    def u(s):
        return s.decode('unicode_escape')
    bytes_type = str
    unicode_type = unicode
    basestring_type = basestring


if sys.version_info > (3,):
    exec("""
def raise_exc_info(exc_info):
    raise exc_info[1].with_traceback(exc_info[2])

def exec_in(code, glob, loc=None):
    if isinstance(code, str):
        code = compile(code, '<string>', 'exec', dont_inherit=True)
    exec(code, glob, loc)
""")
else:
    exec("""
def raise_exc_info(exc_info):
    raise exc_info[0], exc_info[1], exc_info[2]

def exec_in(code, glob, loc=None):
    if isinstance(code, basestring):
        # exec(string) inherits the caller's future imports; compile
        # the string first to prevent that.
        code = compile(code, '<string>', 'exec', dont_inherit=True)
    exec code in glob, loc
""")


class Configurable(object):
    """Base class for configurable interfaces.

    A configurable interface is an (abstract) class whose constructor
    acts as a factory function for one of its implementation subclasses.
    The implementation subclass as well as optional keyword arguments to
    its initializer can be set globally at runtime with `configure`.

    By using the constructor as the factory method, the interface
    looks like a normal class, `isinstance` works as usual, etc.  This
    pattern is most useful when the choice of implementation is likely
    to be a global decision (e.g. when `~select.epoll` is available,
    always use it instead of `~select.select`), or when a
    previously-monolithic class has been split into specialized
    subclasses.

    Configurable subclasses must define the class methods
    `configurable_base` and `configurable_default`, and use the instance
    method `initialize` instead of ``__init__``.
    """
    __impl_class = None
    __impl_kwargs = None

    def __new__(cls, **kwargs):
        base = cls.configurable_base()
        args = {}
        if cls is base:
            impl = cls.configured_class()
            if base.__impl_kwargs:
                args.update(base.__impl_kwargs)
        else:
            impl = cls
        args.update(kwargs)
        instance = super(Configurable, cls).__new__(impl)
        # initialize vs __init__ chosen for compatiblity with AsyncHTTPClient
        # singleton magic.  If we get rid of that we can switch to __init__
        # here too.
        instance.initialize(**args)
        return instance

    @classmethod
    def configurable_base(cls):
        """Returns the base class of a configurable hierarchy.

        This will normally return the class in which it is defined.
        (which is *not* necessarily the same as the cls classmethod parameter).
        """
        raise NotImplementedError()

    @classmethod
    def configurable_default(cls):
        """Returns the implementation class to be used if none is configured."""
        raise NotImplementedError()

    def initialize(self):
        """Initialize a `Configurable` subclass instance.

        Configurable classes should use `initialize` instead of ``__init__``.
        """

    @classmethod
    def configure(cls, impl, **kwargs):
        """Sets the class to use when the base class is instantiated.

        Keyword arguments will be saved and added to the arguments passed
        to the constructor.  This can be used to set global defaults for
        some parameters.
        """
        base = cls.configurable_base()
        if isinstance(impl, (unicode_type, bytes_type)):
            impl = import_object(impl)
        if impl is not None and not issubclass(impl, cls):
            raise ValueError("Invalid subclass of %s" % cls)
        base.__impl_class = impl
        base.__impl_kwargs = kwargs

    @classmethod
    def configured_class(cls):
        """Returns the currently configured class."""
        base = cls.configurable_base()
        if cls.__impl_class is None:
            base.__impl_class = cls.configurable_default()
        return base.__impl_class

    @classmethod
    def _save_configuration(cls):
        base = cls.configurable_base()
        return (base.__impl_class, base.__impl_kwargs)

    @classmethod
    def _restore_configuration(cls, saved):
        base = cls.configurable_base()
        base.__impl_class = saved[0]
        base.__impl_kwargs = saved[1]


########NEW FILE########
__FILENAME__ = zmqstream
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A utility class to send to and recv from a non-blocking socket."""

from __future__ import with_statement

import sys

import zmq
from zmq.utils import jsonapi

try:
    import cPickle as pickle
except ImportError:
    import pickle

from .ioloop import IOLoop

try:
    # gen_log will only import from >= 3.0
    from tornado.log import gen_log
    from tornado import stack_context
except ImportError:
    from .minitornado.log import gen_log
    from .minitornado import stack_context

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

from zmq.utils.strtypes import bytes, unicode, basestring

try:
    callable
except NameError:
    callable = lambda obj: hasattr(obj, '__call__')


class ZMQStream(object):
    """A utility class to register callbacks when a zmq socket sends and receives
    
    For use with zmq.eventloop.ioloop

    There are three main methods
    
    Methods:
    
    * **on_recv(callback, copy=True):**
        register a callback to be run every time the socket has something to receive
    * **on_send(callback):**
        register a callback to be run every time you call send
    * **send(self, msg, flags=0, copy=False, callback=None):**
        perform a send that will trigger the callback
        if callback is passed, on_send is also called.
        
        There are also send_multipart(), send_json(), send_pyobj()
    
    Three other methods for deactivating the callbacks:
    
    * **stop_on_recv():**
        turn off the recv callback
    * **stop_on_send():**
        turn off the send callback
    
    which simply call ``on_<evt>(None)``.
    
    The entire socket interface, excluding direct recv methods, is also
    provided, primarily through direct-linking the methods.
    e.g.
    
    >>> stream.bind is stream.socket.bind
    True
    
    """
    
    socket = None
    io_loop = None
    poller = None
    
    def __init__(self, socket, io_loop=None):
        self.socket = socket
        self.io_loop = io_loop or IOLoop.instance()
        self.poller = zmq.Poller()
        
        self._send_queue = Queue()
        self._recv_callback = None
        self._send_callback = None
        self._close_callback = None
        self._recv_copy = False
        self._flushed = False
        
        self._state = self.io_loop.ERROR
        self._init_io_state()
        
        # shortcircuit some socket methods
        self.bind = self.socket.bind
        self.bind_to_random_port = self.socket.bind_to_random_port
        self.connect = self.socket.connect
        self.setsockopt = self.socket.setsockopt
        self.getsockopt = self.socket.getsockopt
        self.setsockopt_string = self.socket.setsockopt_string
        self.getsockopt_string = self.socket.getsockopt_string
        self.setsockopt_unicode = self.socket.setsockopt_unicode
        self.getsockopt_unicode = self.socket.getsockopt_unicode
    
    
    def stop_on_recv(self):
        """Disable callback and automatic receiving."""
        return self.on_recv(None)
    
    def stop_on_send(self):
        """Disable callback on sending."""
        return self.on_send(None)
    
    def stop_on_err(self):
        """DEPRECATED, does nothing"""
        gen_log.warn("on_err does nothing, and will be removed")
    
    def on_err(self, callback):
        """DEPRECATED, does nothing"""
        gen_log.warn("on_err does nothing, and will be removed")
    
    def on_recv(self, callback, copy=True):
        """Register a callback for when a message is ready to recv.
        
        There can be only one callback registered at a time, so each
        call to `on_recv` replaces previously registered callbacks.
        
        on_recv(None) disables recv event polling.
        
        Use on_recv_stream(callback) instead, to register a callback that will receive
        both this ZMQStream and the message, instead of just the message.
        
        Parameters
        ----------
        
        callback : callable
            callback must take exactly one argument, which will be a
            list, as returned by socket.recv_multipart()
            if callback is None, recv callbacks are disabled.
        copy : bool
            copy is passed directly to recv, so if copy is False,
            callback will receive Message objects. If copy is True,
            then callback will receive bytes/str objects.
        
        Returns : None
        """
        
        self._check_closed()
        assert callback is None or callable(callback)
        self._recv_callback = stack_context.wrap(callback)
        self._recv_copy = copy
        if callback is None:
            self._drop_io_state(self.io_loop.READ)
        else:
            self._add_io_state(self.io_loop.READ)
    
    def on_recv_stream(self, callback, copy=True):
        """Same as on_recv, but callback will get this stream as first argument
        
        callback must take exactly two arguments, as it will be called as::
        
            callback(stream, msg)
        
        Useful when a single callback should be used with multiple streams.
        """
        if callback is None:
            self.stop_on_recv()
        else:
            self.on_recv(lambda msg: callback(self, msg), copy=copy)
    
    def on_send(self, callback):
        """Register a callback to be called on each send
        
        There will be two arguments::
        
            callback(msg, status)
        
        * `msg` will be the list of sendable objects that was just sent
        * `status` will be the return result of socket.send_multipart(msg) -
          MessageTracker or None.
        
        Non-copying sends return a MessageTracker object whose
        `done` attribute will be True when the send is complete.
        This allows users to track when an object is safe to write to
        again.
        
        The second argument will always be None if copy=True
        on the send.
        
        Use on_send_stream(callback) to register a callback that will be passed
        this ZMQStream as the first argument, in addition to the other two.
        
        on_send(None) disables recv event polling.
        
        Parameters
        ----------
        
        callback : callable
            callback must take exactly two arguments, which will be
            the message being sent (always a list),
            and the return result of socket.send_multipart(msg) -
            MessageTracker or None.
            
            if callback is None, send callbacks are disabled.
        """
        
        self._check_closed()
        assert callback is None or callable(callback)
        self._send_callback = stack_context.wrap(callback)
        
    
    def on_send_stream(self, callback):
        """Same as on_send, but callback will get this stream as first argument
        
        Callback will be passed three arguments::
        
            callback(stream, msg, status)
        
        Useful when a single callback should be used with multiple streams.
        """
        if callback is None:
            self.stop_on_send()
        else:
            self.on_send(lambda msg, status: callback(self, msg, status))
        
        
    def send(self, msg, flags=0, copy=True, track=False, callback=None):
        """Send a message, optionally also register a new callback for sends.
        See zmq.socket.send for details.
        """
        return self.send_multipart([msg], flags=flags, copy=copy, track=track, callback=callback)

    def send_multipart(self, msg, flags=0, copy=True, track=False, callback=None):
        """Send a multipart message, optionally also register a new callback for sends.
        See zmq.socket.send_multipart for details.
        """
        kwargs = dict(flags=flags, copy=copy, track=track)
        self._send_queue.put((msg, kwargs))
        callback = callback or self._send_callback
        if callback is not None:
            self.on_send(callback)
        else:
            # noop callback
            self.on_send(lambda *args: None)
        self._add_io_state(self.io_loop.WRITE)
    
    def send_string(self, u, flags=0, encoding='utf-8', callback=None):
        """Send a unicode message with an encoding.
        See zmq.socket.send_unicode for details.
        """
        if not isinstance(u, basestring):
            raise TypeError("unicode/str objects only")
        return self.send(u.encode(encoding), flags=flags, callback=callback)
    
    send_unicode = send_string
    
    def send_json(self, obj, flags=0, callback=None):
        """Send json-serialized version of an object.
        See zmq.socket.send_json for details.
        """
        if jsonapi is None:
            raise ImportError('jsonlib{1,2}, json or simplejson library is required.')
        else:
            msg = jsonapi.dumps(obj)
            return self.send(msg, flags=flags, callback=callback)

    def send_pyobj(self, obj, flags=0, protocol=-1, callback=None):
        """Send a Python object as a message using pickle to serialize.

        See zmq.socket.send_json for details.
        """
        msg = pickle.dumps(obj, protocol)
        return self.send(msg, flags, callback=callback)
    
    def _finish_flush(self):
        """callback for unsetting _flushed flag."""
        self._flushed = False
    
    def flush(self, flag=zmq.POLLIN|zmq.POLLOUT, limit=None):
        """Flush pending messages.

        This method safely handles all pending incoming and/or outgoing messages,
        bypassing the inner loop, passing them to the registered callbacks.

        A limit can be specified, to prevent blocking under high load.

        flush will return the first time ANY of these conditions are met:
            * No more events matching the flag are pending.
            * the total number of events handled reaches the limit.

        Note that if ``flag|POLLIN != 0``, recv events will be flushed even if no callback
        is registered, unlike normal IOLoop operation. This allows flush to be
        used to remove *and ignore* incoming messages.

        Parameters
        ----------
        flag : int, default=POLLIN|POLLOUT
                0MQ poll flags.
                If flag|POLLIN,  recv events will be flushed.
                If flag|POLLOUT, send events will be flushed.
                Both flags can be set at once, which is the default.
        limit : None or int, optional
                The maximum number of messages to send or receive.
                Both send and recv count against this limit.

        Returns
        -------
        int : count of events handled (both send and recv)
        """
        self._check_closed()
        # unset self._flushed, so callbacks will execute, in case flush has
        # already been called this iteration
        already_flushed = self._flushed
        self._flushed = False
        # initialize counters
        count = 0
        def update_flag():
            """Update the poll flag, to prevent registering POLLOUT events
            if we don't have pending sends."""
            return flag & zmq.POLLIN | (self.sending() and flag & zmq.POLLOUT)
        flag = update_flag()
        if not flag:
            # nothing to do
            return 0
        self.poller.register(self.socket, flag)
        events = self.poller.poll(0)
        while events and (not limit or count < limit):
            s,event = events[0]
            if event & zmq.POLLIN: # receiving
                self._handle_recv()
                count += 1
                if self.socket is None:
                    # break if socket was closed during callback
                    break
            if event & zmq.POLLOUT and self.sending():
                self._handle_send()
                count += 1
                if self.socket is None:
                    # break if socket was closed during callback
                    break
            
            flag = update_flag()
            if flag:
                self.poller.register(self.socket, flag)
                events = self.poller.poll(0)
            else:
                events = []
        if count: # only bypass loop if we actually flushed something
            # skip send/recv callbacks this iteration
            self._flushed = True
            # reregister them at the end of the loop
            if not already_flushed: # don't need to do it again
                self.io_loop.add_callback(self._finish_flush)
        elif already_flushed:
            self._flushed = True

        # update ioloop poll state, which may have changed
        self._rebuild_io_state()
        return count
    
    def set_close_callback(self, callback):
        """Call the given callback when the stream is closed."""
        self._close_callback = stack_context.wrap(callback)
    
    def close(self, linger=None):
        """Close this stream."""
        if self.socket is not None:
            self.io_loop.remove_handler(self.socket)
            self.socket.close(linger)
            self.socket = None
            if self._close_callback:
                self._run_callback(self._close_callback)

    def receiving(self):
        """Returns True if we are currently receiving from the stream."""
        return self._recv_callback is not None

    def sending(self):
        """Returns True if we are currently sending to the stream."""
        return not self._send_queue.empty()

    def closed(self):
        return self.socket is None

    def _run_callback(self, callback, *args, **kwargs):
        """Wrap running callbacks in try/except to allow us to
        close our socket."""
        try:
            # Use a NullContext to ensure that all StackContexts are run
            # inside our blanket exception handler rather than outside.
            with stack_context.NullContext():
                callback(*args, **kwargs)
        except:
            gen_log.error("Uncaught exception, closing connection.",
                          exc_info=True)
            # Close the socket on an uncaught exception from a user callback
            # (It would eventually get closed when the socket object is
            # gc'd, but we don't want to rely on gc happening before we
            # run out of file descriptors)
            self.close()
            # Re-raise the exception so that IOLoop.handle_callback_exception
            # can see it and log the error
            raise

    def _handle_events(self, fd, events):
        """This method is the actual handler for IOLoop, that gets called whenever
        an event on my socket is posted. It dispatches to _handle_recv, etc."""
        # print "handling events"
        if not self.socket:
            gen_log.warning("Got events for closed stream %s", fd)
            return
        try:
            # dispatch events:
            if events & IOLoop.ERROR:
                gen_log.error("got POLLERR event on ZMQStream, which doesn't make sense")
                return
            if events & IOLoop.READ:
                self._handle_recv()
                if not self.socket:
                    return
            if events & IOLoop.WRITE:
                self._handle_send()
                if not self.socket:
                    return

            # rebuild the poll state
            self._rebuild_io_state()
        except:
            gen_log.error("Uncaught exception, closing connection.",
                          exc_info=True)
            self.close()
            raise
            
    def _handle_recv(self):
        """Handle a recv event."""
        if self._flushed:
            return
        try:
            msg = self.socket.recv_multipart(zmq.NOBLOCK, copy=self._recv_copy)
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                # state changed since poll event
                pass
            else:
                gen_log.error("RECV Error: %s"%zmq.strerror(e.errno))
        else:
            if self._recv_callback:
                callback = self._recv_callback
                # self._recv_callback = None
                self._run_callback(callback, msg)
                
        # self.update_state()
        

    def _handle_send(self):
        """Handle a send event."""
        if self._flushed:
            return
        if not self.sending():
            gen_log.error("Shouldn't have handled a send event")
            return
        
        msg, kwargs = self._send_queue.get()
        try:
            status = self.socket.send_multipart(msg, **kwargs)
        except zmq.ZMQError as e:
            gen_log.error("SEND Error: %s", e)
            status = e
        if self._send_callback:
            callback = self._send_callback
            self._run_callback(callback, msg, status)
        
        # self.update_state()
    
    def _check_closed(self):
        if not self.socket:
            raise IOError("Stream is closed")
    
    def _rebuild_io_state(self):
        """rebuild io state based on self.sending() and receiving()"""
        if self.socket is None:
            return
        state = self.io_loop.ERROR
        if self.receiving():
            state |= self.io_loop.READ
        if self.sending():
            state |= self.io_loop.WRITE
        if state != self._state:
            self._state = state
            self._update_handler(state)
    
    def _add_io_state(self, state):
        """Add io_state to poller."""
        if not self._state & state:
            self._state = self._state | state
            self._update_handler(self._state)
    
    def _drop_io_state(self, state):
        """Stop poller from watching an io_state."""
        if self._state & state:
            self._state = self._state & (~state)
            self._update_handler(self._state)
    
    def _update_handler(self, state):
        """Update IOLoop handler with state."""
        if self.socket is None:
            return
        self.io_loop.update_handler(self.socket, state)
    
    def _init_io_state(self):
        """initialize the ioloop event handler"""
        with stack_context.NullContext():
            self.io_loop.add_handler(self.socket, self._handle_events, self._state)


########NEW FILE########
__FILENAME__ = core
#-----------------------------------------------------------------------------
#  Copyright (c) 2011-2012 Travis Cline
#
#  This file is part of pyzmq
#  It is adapted from upstream project zeromq_gevent under the New BSD License
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

"""This module wraps the :class:`Socket` and :class:`Context` found in :mod:`pyzmq <zmq>` to be non blocking
"""

from __future__ import print_function

import sys
import time
import warnings

import zmq

from zmq import Context as _original_Context
from zmq import Socket as _original_Socket
from .poll import _Poller

import gevent
from gevent.event import AsyncResult
from gevent.hub import get_hub

if hasattr(zmq, 'RCVTIMEO'):
    TIMEOS = (zmq.RCVTIMEO, zmq.SNDTIMEO)
else:
    TIMEOS = ()

def _stop(evt):
    """simple wrapper for stopping an Event, allowing for method rename in gevent 1.0"""
    try:
        evt.stop()
    except AttributeError as e:
        # gevent<1.0 compat
        evt.cancel()

class _Socket(_original_Socket):
    """Green version of :class:`zmq.Socket`

    The following methods are overridden:

        * send
        * recv

    To ensure that the ``zmq.NOBLOCK`` flag is set and that sending or receiving
    is deferred to the hub if a ``zmq.EAGAIN`` (retry) error is raised.
    
    The `__state_changed` method is triggered when the zmq.FD for the socket is
    marked as readable and triggers the necessary read and write events (which
    are waited for in the recv and send methods).

    Some double underscore prefixes are used to minimize pollution of
    :class:`zmq.Socket`'s namespace.
    """
    __in_send_multipart = False
    __in_recv_multipart = False
    __writable = None
    __readable = None
    _state_event = None
    _gevent_bug_timeout = 11.6 # timeout for not trusting gevent
    _debug_gevent = False # turn on if you think gevent is missing events
    _poller_class = _Poller
    
    def __init__(self, context, socket_type):
        _original_Socket.__init__(self, context, socket_type)
        self.__in_send_multipart = False
        self.__in_recv_multipart = False
        self.__setup_events()
        

    def __del__(self):
        self.close()

    def close(self, linger=None):
        super(_Socket, self).close(linger)
        self.__cleanup_events()

    def __cleanup_events(self):
        # close the _state_event event, keeps the number of active file descriptors down
        if getattr(self, '_state_event', None):
            _stop(self._state_event)
            self._state_event = None
        # if the socket has entered a close state resume any waiting greenlets
        self.__writable.set()
        self.__readable.set()

    def __setup_events(self):
        self.__readable = AsyncResult()
        self.__writable = AsyncResult()
        self.__readable.set()
        self.__writable.set()
        
        try:
            self._state_event = get_hub().loop.io(self.getsockopt(zmq.FD), 1) # read state watcher
            self._state_event.start(self.__state_changed)
        except AttributeError:
            # for gevent<1.0 compatibility
            from gevent.core import read_event
            self._state_event = read_event(self.getsockopt(zmq.FD), self.__state_changed, persist=True)

    def __state_changed(self, event=None, _evtype=None):
        if self.closed:
            self.__cleanup_events()
            return
        try:
            # avoid triggering __state_changed from inside __state_changed
            events = super(_Socket, self).getsockopt(zmq.EVENTS)
        except zmq.ZMQError as exc:
            self.__writable.set_exception(exc)
            self.__readable.set_exception(exc)
        else:
            if events & zmq.POLLOUT:
                self.__writable.set()
            if events & zmq.POLLIN:
                self.__readable.set()

    def _wait_write(self):
        assert self.__writable.ready(), "Only one greenlet can be waiting on this event"
        self.__writable = AsyncResult()
        # timeout is because libzmq cannot be trusted to properly signal a new send event:
        # this is effectively a maximum poll interval of 1s
        tic = time.time()
        dt = self._gevent_bug_timeout
        if dt:
            timeout = gevent.Timeout(seconds=dt)
        else:
            timeout = None
        try:
            if timeout:
                timeout.start()
            self.__writable.get(block=True)
        except gevent.Timeout as t:
            if t is not timeout:
                raise
            toc = time.time()
            # gevent bug: get can raise timeout even on clean return
            # don't display zmq bug warning for gevent bug (this is getting ridiculous)
            if self._debug_gevent and timeout and toc-tic > dt and \
                    self.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
                print("BUG: gevent may have missed a libzmq send event on %i!" % self.FD, file=sys.stderr)
        finally:
            if timeout:
                timeout.cancel()
            self.__writable.set()

    def _wait_read(self):
        assert self.__readable.ready(), "Only one greenlet can be waiting on this event"
        self.__readable = AsyncResult()
        # timeout is because libzmq cannot always be trusted to play nice with libevent.
        # I can only confirm that this actually happens for send, but lets be symmetrical
        # with our dirty hacks.
        # this is effectively a maximum poll interval of 1s
        tic = time.time()
        dt = self._gevent_bug_timeout
        if dt:
            timeout = gevent.Timeout(seconds=dt)
        else:
            timeout = None
        try:
            if timeout:
                timeout.start()
            self.__readable.get(block=True)
        except gevent.Timeout as t:
            if t is not timeout:
                raise
            toc = time.time()
            # gevent bug: get can raise timeout even on clean return
            # don't display zmq bug warning for gevent bug (this is getting ridiculous)
            if self._debug_gevent and timeout and toc-tic > dt and \
                    self.getsockopt(zmq.EVENTS) & zmq.POLLIN:
                print("BUG: gevent may have missed a libzmq recv event on %i!" % self.FD, file=sys.stderr)
        finally:
            if timeout:
                timeout.cancel()
            self.__readable.set()

    def send(self, data, flags=0, copy=True, track=False):
        """send, which will only block current greenlet
        
        state_changed always fires exactly once (success or fail) at the
        end of this method.
        """
        
        # if we're given the NOBLOCK flag act as normal and let the EAGAIN get raised
        if flags & zmq.NOBLOCK:
            try:
                msg = super(_Socket, self).send(data, flags, copy, track)
            finally:
                if not self.__in_send_multipart:
                    self.__state_changed()
            return msg
        # ensure the zmq.NOBLOCK flag is part of flags
        flags |= zmq.NOBLOCK
        while True: # Attempt to complete this operation indefinitely, blocking the current greenlet
            try:
                # attempt the actual call
                msg = super(_Socket, self).send(data, flags, copy, track)
            except zmq.ZMQError as e:
                # if the raised ZMQError is not EAGAIN, reraise
                if e.errno != zmq.EAGAIN:
                    if not self.__in_send_multipart:
                        self.__state_changed()
                    raise
            else:
                if not self.__in_send_multipart:
                    self.__state_changed()
                return msg
            # defer to the event loop until we're notified the socket is writable
            self._wait_write()

    def recv(self, flags=0, copy=True, track=False):
        """recv, which will only block current greenlet
        
        state_changed always fires exactly once (success or fail) at the
        end of this method.
        """
        if flags & zmq.NOBLOCK:
            try:
                msg = super(_Socket, self).recv(flags, copy, track)
            finally:
                if not self.__in_recv_multipart:
                    self.__state_changed()
            return msg
        
        flags |= zmq.NOBLOCK
        while True:
            try:
                msg = super(_Socket, self).recv(flags, copy, track)
            except zmq.ZMQError as e:
                if e.errno != zmq.EAGAIN:
                    if not self.__in_recv_multipart:
                        self.__state_changed()
                    raise
            else:
                if not self.__in_recv_multipart:
                    self.__state_changed()
                return msg
            self._wait_read()
    
    def send_multipart(self, *args, **kwargs):
        """wrap send_multipart to prevent state_changed on each partial send"""
        self.__in_send_multipart = True
        try:
            msg = super(_Socket, self).send_multipart(*args, **kwargs)
        finally:
            self.__in_send_multipart = False
            self.__state_changed()
        return msg
    
    def recv_multipart(self, *args, **kwargs):
        """wrap recv_multipart to prevent state_changed on each partial recv"""
        self.__in_recv_multipart = True
        try:
            msg = super(_Socket, self).recv_multipart(*args, **kwargs)
        finally:
            self.__in_recv_multipart = False
            self.__state_changed()
        return msg
    
    def get(self, opt):
        """trigger state_changed on getsockopt(EVENTS)"""
        if opt in TIMEOS:
            warnings.warn("TIMEO socket options have no effect in zmq.green", UserWarning)
        optval = super(_Socket, self).get(opt)
        if opt == zmq.EVENTS:
            self.__state_changed()
        return optval
    
    def set(self, opt, val):
        """set socket option"""
        if opt in TIMEOS:
            warnings.warn("TIMEO socket options have no effect in zmq.green", UserWarning)
        return super(_Socket, self).set(opt, val)


class _Context(_original_Context):
    """Replacement for :class:`zmq.Context`

    Ensures that the greened Socket above is used in calls to `socket`.
    """
    _socket_class = _Socket

########NEW FILE########
__FILENAME__ = device
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import zmq
from zmq.green import Poller

def device(device_type, isocket, osocket):
    """Start a zeromq device (gevent-compatible).
    
    Unlike the true zmq.device, this does not release the GIL.

    Parameters
    ----------
    device_type : (QUEUE, FORWARDER, STREAMER)
        The type of device to start (ignored).
    isocket : Socket
        The Socket instance for the incoming traffic.
    osocket : Socket
        The Socket instance for the outbound traffic.
    """
    p = Poller()
    if osocket == -1:
        osocket = isocket
    p.register(isocket, zmq.POLLIN)
    p.register(osocket, zmq.POLLIN)
    
    while True:
        events = dict(p.poll())
        if isocket in events:
            osocket.send_multipart(isocket.recv_multipart())
        if osocket in events:
            isocket.send_multipart(osocket.recv_multipart())

########NEW FILE########
__FILENAME__ = ioloop
from zmq.eventloop.ioloop import *
from zmq.green import Poller

RealIOLoop = IOLoop
RealZMQPoller = ZMQPoller

class IOLoop(RealIOLoop):
    
    def initialize(self, impl=None):
        impl = _poll() if impl is None else impl
        super(IOLoop, self).initialize(impl)

    @staticmethod
    def instance():
        """Returns a global `IOLoop` instance.
        
        Most applications have a single, global `IOLoop` running on the
        main thread.  Use this method to get this instance from
        another thread.  To get the current thread's `IOLoop`, use `current()`.
        """
        # install this class as the active IOLoop implementation
        # when using tornado 3
        if tornado_version >= (3,):
            PollIOLoop.configure(IOLoop)
        return PollIOLoop.instance()


class ZMQPoller(RealZMQPoller):
    """gevent-compatible version of ioloop.ZMQPoller"""
    def __init__(self):
        self._poller = Poller()

_poll = ZMQPoller

########NEW FILE########
__FILENAME__ = zmqstream
from zmq.eventloop.zmqstream import *

from zmq.green.eventloop.ioloop import IOLoop

RealZMQStream = ZMQStream

class ZMQStream(RealZMQStream):
    
    def __init__(self, socket, io_loop=None):
        io_loop = io_loop or IOLoop.instance()
        super(ZMQStream, self).__init__(socket, io_loop=io_loop)

########NEW FILE########
__FILENAME__ = poll
import zmq
import gevent
from gevent import select

from zmq import Poller as _original_Poller


class _Poller(_original_Poller):
    """Replacement for :class:`zmq.Poller`

    Ensures that the greened Poller below is used in calls to
    :meth:`zmq.Poller.poll`.
    """
    _gevent_bug_timeout = 1.33 # minimum poll interval, for working around gevent bug

    def _get_descriptors(self):
        """Returns three elements tuple with socket descriptors ready
        for gevent.select.select
        """
        rlist = []
        wlist = []
        xlist = []

        for socket, flags in self.sockets:
            if isinstance(socket, zmq.Socket):
                rlist.append(socket.getsockopt(zmq.FD))
                continue
            elif isinstance(socket, int):
                fd = socket
            elif hasattr(socket, 'fileno'):
                try:
                    fd = int(socket.fileno())
                except:
                    raise ValueError('fileno() must return an valid integer fd')
            else:
                raise TypeError('Socket must be a 0MQ socket, an integer fd '
                                'or have a fileno() method: %r' % socket)

            if flags & zmq.POLLIN:
                rlist.append(fd)
            if flags & zmq.POLLOUT:
                wlist.append(fd)
            if flags & zmq.POLLERR:
                xlist.append(fd)

        return (rlist, wlist, xlist)

    def poll(self, timeout=-1):
        """Overridden method to ensure that the green version of
        Poller is used.

        Behaves the same as :meth:`zmq.core.Poller.poll`
        """

        if timeout is None:
            timeout = -1

        if timeout < 0:
            timeout = -1

        rlist = None
        wlist = None
        xlist = None

        if timeout > 0:
            tout = gevent.Timeout.start_new(timeout/1000.0)

        try:
            # Loop until timeout or events available
            rlist, wlist, xlist = self._get_descriptors()
            while True:
                events = super(_Poller, self).poll(0)
                if events or timeout == 0:
                    return events

                # wait for activity on sockets in a green way
                # set a minimum poll frequency,
                # because gevent < 1.0 cannot be trusted to catch edge-triggered FD events
                _bug_timeout = gevent.Timeout.start_new(self._gevent_bug_timeout)
                try:
                    select.select(rlist, wlist, xlist)
                except gevent.Timeout as t:
                    if t is not _bug_timeout:
                        raise
                finally:
                    _bug_timeout.cancel()

        except gevent.Timeout as t:
            if t is not tout:
                raise
            return []
        finally:
           if timeout > 0:
               tout.cancel()


########NEW FILE########
__FILENAME__ = handlers
"""pyzmq logging handlers.

This mainly defines the PUBHandler object for publishing logging messages over
a zmq.PUB socket.

The PUBHandler can be used with the regular logging module, as in::

    >>> import logging
    >>> handler = PUBHandler('tcp://127.0.0.1:12345')
    >>> handler.root_topic = 'foo'
    >>> logger = logging.getLogger('foobar')
    >>> logger.setLevel(logging.DEBUG)
    >>> logger.addHandler(handler)

After this point, all messages logged by ``logger`` will be published on the
PUB socket.

Code adapted from StarCluster:

    http://github.com/jtriley/StarCluster/blob/master/starcluster/logger.py

Authors
-------
* Min RK
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import logging
from logging import INFO, DEBUG, WARN, ERROR, FATAL

import zmq
from zmq.utils.strtypes import bytes, unicode, cast_bytes

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

TOPIC_DELIM="::" # delimiter for splitting topics on the receiving end.


class PUBHandler(logging.Handler):
    """A basic logging handler that emits log messages through a PUB socket.

    Takes a PUB socket already bound to interfaces or an interface to bind to.

    Example::

        sock = context.socket(zmq.PUB)
        sock.bind('inproc://log')
        handler = PUBHandler(sock)

    Or::

        handler = PUBHandler('inproc://loc')

    These are equivalent.

    Log messages handled by this handler are broadcast with ZMQ topics
    ``this.root_topic`` comes first, followed by the log level
    (DEBUG,INFO,etc.), followed by any additional subtopics specified in the
    message by: log.debug("subtopic.subsub::the real message")
    """
    root_topic=""
    socket = None
    
    formatters = {
        logging.DEBUG: logging.Formatter(
        "%(levelname)s %(filename)s:%(lineno)d - %(message)s\n"),
        logging.INFO: logging.Formatter("%(message)s\n"),
        logging.WARN: logging.Formatter(
        "%(levelname)s %(filename)s:%(lineno)d - %(message)s\n"),
        logging.ERROR: logging.Formatter(
        "%(levelname)s %(filename)s:%(lineno)d - %(message)s - %(exc_info)s\n"),
        logging.CRITICAL: logging.Formatter(
        "%(levelname)s %(filename)s:%(lineno)d - %(message)s\n")}
    
    def __init__(self, interface_or_socket, context=None):
        logging.Handler.__init__(self)
        if isinstance(interface_or_socket, zmq.Socket):
            self.socket = interface_or_socket
            self.ctx = self.socket.context
        else:
            self.ctx = context or zmq.Context()
            self.socket = self.ctx.socket(zmq.PUB)
            self.socket.bind(interface_or_socket)

    def format(self,record):
        """Format a record."""
        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        """Emit a log message on my socket."""
        try:
            topic, record.msg = record.msg.split(TOPIC_DELIM,1)
        except Exception:
            topic = ""
        try:
            bmsg = cast_bytes(self.format(record))
        except Exception:
            self.handleError(record)
            return
        
        topic_list = []

        if self.root_topic:
            topic_list.append(self.root_topic)

        topic_list.append(record.levelname)

        if topic:
            topic_list.append(topic)

        btopic = b'.'.join(cast_bytes(t) for t in topic_list)

        self.socket.send_multipart([btopic, bmsg])


class TopicLogger(logging.Logger):
    """A simple wrapper that takes an additional argument to log methods.

    All the regular methods exist, but instead of one msg argument, two
    arguments: topic, msg are passed.

    That is::

        logger.debug('msg')

    Would become::

        logger.debug('topic.sub', 'msg')
    """
    def log(self, level, topic, msg, *args, **kwargs):
        """Log 'msg % args' with level and topic.

        To pass exception information, use the keyword argument exc_info
        with a True value::

            logger.log(level, "zmq.fun", "We have a %s", 
                    "mysterious problem", exc_info=1)
        """
        logging.Logger.log(self, level, '%s::%s'%(topic,msg), *args, **kwargs)

# Generate the methods of TopicLogger, since they are just adding a
# topic prefix to a message.
for name in "debug warn warning error critical fatal".split():
    meth = getattr(logging.Logger,name)
    setattr(TopicLogger, name, 
            lambda self, level, topic, msg, *args, **kwargs: 
                meth(self, level, topic+TOPIC_DELIM+msg,*args, **kwargs))
    

########NEW FILE########
__FILENAME__ = forward
#
# This file is adapted from a paramiko demo, and thus licensed under LGPL 2.1.
# Original Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
# Edits Copyright (C) 2010 The IPython Team
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distrubuted in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02111-1301  USA.

"""
Sample script showing how to do local port forwarding over paramiko.

This script connects to the requested SSH server and sets up local port
forwarding (the openssh -L option) from a local port through a tunneled
connection to a destination reachable from the SSH server machine.
"""

from __future__ import print_function

import logging
import select
try:  # Python 3
    import socketserver
except ImportError:  # Python 2
    import SocketServer as socketserver

logger = logging.getLogger('ssh')

class ForwardServer (socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
    

class Handler (socketserver.BaseRequestHandler):

    def handle(self):
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip',
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
        except Exception as e:
            logger.debug('Incoming request to %s:%d failed: %s' % (self.chain_host,
                                                              self.chain_port,
                                                              repr(e)))
            return
        if chan is None:
            logger.debug('Incoming request to %s:%d was rejected by the SSH server.' %
                    (self.chain_host, self.chain_port))
            return

        logger.debug('Connected!  Tunnel open %r -> %r -> %r' % (self.request.getpeername(),
                                                            chan.getpeername(), (self.chain_host, self.chain_port)))
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        chan.close()
        self.request.close()
        logger.debug('Tunnel closed ')


def forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object.  (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHander (Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport
    ForwardServer(('127.0.0.1', local_port), SubHander).serve_forever()


__all__ = ['forward_tunnel']

########NEW FILE########
__FILENAME__ = tunnel
"""Basic ssh tunnel utilities, and convenience functions for tunneling
zeromq connections.
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2010-2011  IPython Development Team
#  Copyright (C) 2011- Min Ragan-Kelley
#  This file is part of pyzmq.
#
#  Redistributed from IPython under the terms of the BSD License.
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
from __future__ import print_function

import atexit
import os
import signal
import socket
import sys
import warnings
from getpass import getpass, getuser
from multiprocessing import Process

try:
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        import paramiko
except ImportError:
    paramiko = None
else:
    from .forward import forward_tunnel


try:
    import pexpect
except ImportError:
    pexpect = None

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

_random_ports = set()

def select_random_ports(n):
    """Selects and return n random ports that are available."""
    ports = []
    for i in range(n):
        sock = socket.socket()
        sock.bind(('', 0))
        while sock.getsockname()[1] in _random_ports:
            sock.close()
            sock = socket.socket()
            sock.bind(('', 0))
        ports.append(sock)
    for i, sock in enumerate(ports):
        port = sock.getsockname()[1]
        sock.close()
        ports[i] = port
        _random_ports.add(port)
    return ports


#-----------------------------------------------------------------------------
# Check for passwordless login
#-----------------------------------------------------------------------------

def try_passwordless_ssh(server, keyfile, paramiko=None):
    """Attempt to make an ssh connection without a password.
    This is mainly used for requiring password input only once
    when many tunnels may be connected to the same server.
    
    If paramiko is None, the default for the platform is chosen.
    """
    if paramiko is None:
        paramiko = sys.platform == 'win32'
    if not paramiko:
        f = _try_passwordless_openssh
    else:
        f = _try_passwordless_paramiko
    return f(server, keyfile)

def _try_passwordless_openssh(server, keyfile):
    """Try passwordless login with shell ssh command."""
    if pexpect is None:
        raise ImportError("pexpect unavailable, use paramiko")
    cmd = 'ssh -f '+ server
    if keyfile:
        cmd += ' -i ' + keyfile
    cmd += ' exit'
    p = pexpect.spawn(cmd)
    while True:
        try:
            p.expect('[Pp]assword:', timeout=.1)
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            return True
        else:
            return False

def _try_passwordless_paramiko(server, keyfile):
    """Try passwordless login with paramiko."""
    if paramiko is None:
        msg = "Paramiko unavaliable, "
        if sys.platform == 'win32':
            msg += "Paramiko is required for ssh tunneled connections on Windows."
        else:
            msg += "use OpenSSH."
        raise ImportError(msg)
    username, server, port = _split_server(server)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    try:
        client.connect(server, port, username=username, key_filename=keyfile,
               look_for_keys=True)
    except paramiko.AuthenticationException:
        return False
    else:
        client.close()
        return True


def tunnel_connection(socket, addr, server, keyfile=None, password=None, paramiko=None, timeout=60):
    """Connect a socket to an address via an ssh tunnel.
    
    This is a wrapper for socket.connect(addr), when addr is not accessible
    from the local machine.  It simply creates an ssh tunnel using the remaining args,
    and calls socket.connect('tcp://localhost:lport') where lport is the randomly
    selected local port of the tunnel.
    
    """
    new_url, tunnel = open_tunnel(addr, server, keyfile=keyfile, password=password, paramiko=paramiko, timeout=timeout)
    socket.connect(new_url)
    return tunnel


def open_tunnel(addr, server, keyfile=None, password=None, paramiko=None, timeout=60):
    """Open a tunneled connection from a 0MQ url.
    
    For use inside tunnel_connection.
    
    Returns
    -------
    
    (url, tunnel) : (str, object)
        The 0MQ url that has been forwarded, and the tunnel object
    """
    
    lport = select_random_ports(1)[0]
    transport, addr = addr.split('://')
    ip,rport = addr.split(':')
    rport = int(rport)
    if paramiko is None:
        paramiko = sys.platform == 'win32'
    if paramiko:
        tunnelf = paramiko_tunnel
    else:
        tunnelf = openssh_tunnel
    
    tunnel = tunnelf(lport, rport, server, remoteip=ip, keyfile=keyfile, password=password, timeout=timeout)
    return 'tcp://127.0.0.1:%i'%lport, tunnel

def openssh_tunnel(lport, rport, server, remoteip='127.0.0.1', keyfile=None, password=None, timeout=60):
    """Create an ssh tunnel using command-line ssh that connects port lport
    on this machine to localhost:rport on server.  The tunnel
    will automatically close when not in use, remaining open
    for a minimum of timeout seconds for an initial connection.
    
    This creates a tunnel redirecting `localhost:lport` to `remoteip:rport`,
    as seen from `server`.
    
    keyfile and password may be specified, but ssh config is checked for defaults.
    
    Parameters
    ----------
    
    lport : int
        local port for connecting to the tunnel from this machine.
    rport : int
        port on the remote machine to connect to.
    server : str
        The ssh server to connect to. The full ssh server string will be parsed.
        user@server:port
    remoteip : str [Default: 127.0.0.1]
        The remote ip, specifying the destination of the tunnel.
        Default is localhost, which means that the tunnel would redirect
        localhost:lport on this machine to localhost:rport on the *server*.
        
    keyfile : str; path to public key file
        This specifies a key to be used in ssh login, default None.
        Regular default ssh keys will be used without specifying this argument.
    password : str; 
        Your ssh password to the ssh server. Note that if this is left None,
        you will be prompted for it if passwordless key based login is unavailable.
    timeout : int [default: 60]
        The time (in seconds) after which no activity will result in the tunnel
        closing.  This prevents orphaned tunnels from running forever.
    """
    if pexpect is None:
        raise ImportError("pexpect unavailable, use paramiko_tunnel")
    ssh="ssh "
    if keyfile:
        ssh += "-i " + keyfile
    
    if ':' in server:
        server, port = server.split(':')
        ssh += " -p %s" % port
    
    cmd = "%s -O check %s" % (ssh, server)
    (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
    if not exitstatus:
        pid = int(output[output.find("(pid=")+5:output.find(")")]) 
        cmd = "%s -O forward -L 127.0.0.1:%i:%s:%i %s" % (
            ssh, lport, remoteip, rport, server)
        (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
        if not exitstatus:
            atexit.register(_stop_tunnel, cmd.replace("forward", "cancel", 1))
            return pid
    cmd = "%s -f -S none -L 127.0.0.1:%i:%s:%i %s sleep %i" % (
        ssh, lport, remoteip, rport, server, timeout)
    tunnel = pexpect.spawn(cmd)
    failed = False
    while True:
        try:
            tunnel.expect('[Pp]assword:', timeout=.1)
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            if tunnel.exitstatus:
                print(tunnel.exitstatus)
                print(tunnel.before)
                print(tunnel.after)
                raise RuntimeError("tunnel '%s' failed to start"%(cmd))
            else:
                return tunnel.pid
        else:
            if failed:
                print("Password rejected, try again")
                password=None
            if password is None:
                password = getpass("%s's password: "%(server))
            tunnel.sendline(password)
            failed = True
    
def _stop_tunnel(cmd):
    pexpect.run(cmd)

def _split_server(server):
    if '@' in server:
        username,server = server.split('@', 1)
    else:
        username = getuser()
    if ':' in server:
        server, port = server.split(':')
        port = int(port)
    else:
        port = 22
    return username, server, port

def paramiko_tunnel(lport, rport, server, remoteip='127.0.0.1', keyfile=None, password=None, timeout=60):
    """launch a tunner with paramiko in a subprocess. This should only be used
    when shell ssh is unavailable (e.g. Windows).
    
    This creates a tunnel redirecting `localhost:lport` to `remoteip:rport`,
    as seen from `server`.
    
    If you are familiar with ssh tunnels, this creates the tunnel:
    
    ssh server -L localhost:lport:remoteip:rport
    
    keyfile and password may be specified, but ssh config is checked for defaults.
    
    
    Parameters
    ----------
    
    lport : int
        local port for connecting to the tunnel from this machine.
    rport : int
        port on the remote machine to connect to.
    server : str
        The ssh server to connect to. The full ssh server string will be parsed.
        user@server:port
    remoteip : str [Default: 127.0.0.1]
        The remote ip, specifying the destination of the tunnel.
        Default is localhost, which means that the tunnel would redirect
        localhost:lport on this machine to localhost:rport on the *server*.
        
    keyfile : str; path to public key file
        This specifies a key to be used in ssh login, default None.
        Regular default ssh keys will be used without specifying this argument.
    password : str; 
        Your ssh password to the ssh server. Note that if this is left None,
        you will be prompted for it if passwordless key based login is unavailable.
    timeout : int [default: 60]
        The time (in seconds) after which no activity will result in the tunnel
        closing.  This prevents orphaned tunnels from running forever.
    
    """
    if paramiko is None:
        raise ImportError("Paramiko not available")
    
    if password is None:
        if not _try_passwordless_paramiko(server, keyfile):
            password = getpass("%s's password: "%(server))

    p = Process(target=_paramiko_tunnel, 
            args=(lport, rport, server, remoteip), 
            kwargs=dict(keyfile=keyfile, password=password))
    p.daemon=False
    p.start()
    atexit.register(_shutdown_process, p)
    return p
    
def _shutdown_process(p):
    if p.is_alive():
        p.terminate()

def _paramiko_tunnel(lport, rport, server, remoteip, keyfile=None, password=None):
    """Function for actually starting a paramiko tunnel, to be passed
    to multiprocessing.Process(target=this), and not called directly.
    """
    username, server, port = _split_server(server)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    try:
        client.connect(server, port, username=username, key_filename=keyfile,
                       look_for_keys=True, password=password)
#    except paramiko.AuthenticationException:
#        if password is None:
#            password = getpass("%s@%s's password: "%(username, server))
#            client.connect(server, port, username=username, password=password)
#        else:
#            raise
    except Exception as e:
        print('*** Failed to connect to %s:%d: %r' % (server, port, e))
        sys.exit(1)

    # Don't let SIGINT kill the tunnel subprocess
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        forward_tunnel(lport, remoteip, rport, client.get_transport())
    except KeyboardInterrupt:
        print('SIGINT: Port forwarding stopped cleanly')
        sys.exit(0)
    except Exception as e:
        print("Port forwarding stopped uncleanly: %s"%e)
        sys.exit(255)

if sys.platform == 'win32':
    ssh_tunnel = paramiko_tunnel
else:
    ssh_tunnel = openssh_tunnel

    
__all__ = ['tunnel_connection', 'ssh_tunnel', 'openssh_tunnel', 'paramiko_tunnel', 'try_passwordless_ssh']



########NEW FILE########
__FILENAME__ = attrsettr
# coding: utf-8
"""Mixin for mapping set/getattr to self.set/get"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from . import constants
#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

class AttributeSetter(object):
    
    def __setattr__(self, key, value):
        """set zmq options by attribute"""
        
        # regular setattr only allowed for class-defined attributes
        for obj in [self] + self.__class__.mro():
            if key in obj.__dict__:
                object.__setattr__(self, key, value)
                return
        
        upper_key = key.upper()
        try:
            opt = getattr(constants, upper_key)
        except AttributeError:
            raise AttributeError("%s has no such option: %s" % (
                self.__class__.__name__, upper_key)
            )
        else:
            self._set_attr_opt(upper_key, opt, value)
    
    def _set_attr_opt(self, name, opt, value):
        """override if setattr should do something other than call self.set"""
        self.set(opt, value)
    
    def __getattr__(self, key):
        """get zmq options by attribute"""
        upper_key = key.upper()
        try:
            opt = getattr(constants, upper_key)
        except AttributeError:
            raise AttributeError("%s has no such option: %s" % (
                self.__class__.__name__, upper_key)
            )
        else:
            return self._get_attr_opt(upper_key, opt)

    def _get_attr_opt(self, name, opt):
        """override if getattr should do something other than call self.get"""
        return self.get(opt)
    

__all__ = ['AttributeSetter']

########NEW FILE########
__FILENAME__ = constants
"""0MQ Constants."""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian E. Granger & Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from zmq.backend import constants
from zmq.utils.constant_names import (
    base_names,
    switched_sockopt_names,
    int_sockopt_names,
    int64_sockopt_names,
    bytes_sockopt_names,
    ctx_opt_names,
    msg_opt_names,
)

#-----------------------------------------------------------------------------
# Python module level constants
#-----------------------------------------------------------------------------

__all__ = [
    'int_sockopts',
    'int64_sockopts',
    'bytes_sockopts',
    'ctx_opts',
    'ctx_opt_names',
    ]

int_sockopts    = set()
int64_sockopts  = set()
bytes_sockopts  = set()
ctx_opts        = set()
msg_opts        = set()


if constants.VERSION < 30000:
    int64_sockopt_names.extend(switched_sockopt_names)
else:
    int_sockopt_names.extend(switched_sockopt_names)

def _add_constant(name, container=None):
    """add a constant to be defined
    
    optionally add it to one of the sets for use in get/setopt checkers
    """
    c = getattr(constants, name, -1)
    if c == -1:
        return
    globals()[name] = c
    __all__.append(name)
    if container is not None:
        container.add(c)
    return c
    
for name in base_names:
    _add_constant(name)

for name in int_sockopt_names:
    _add_constant(name, int_sockopts)

for name in int64_sockopt_names:
    _add_constant(name, int64_sockopts)

for name in bytes_sockopt_names:
    _add_constant(name, bytes_sockopts)

for name in ctx_opt_names:
    _add_constant(name, ctx_opts)

for name in msg_opt_names:
    _add_constant(name, msg_opts)

# ensure some aliases are always defined
aliases = [
    ('DONTWAIT', 'NOBLOCK'),
    ('XREQ', 'DEALER'),
    ('XREP', 'ROUTER'),
]
for group in aliases:
    undefined = set()
    found = None
    for name in group:
        value = getattr(constants, name, -1)
        if value != -1:
            found = value
        else:
            undefined.add(name)
    if found is not None:
        for name in undefined:
            globals()[name] = found
            __all__.append(name)

########NEW FILE########
__FILENAME__ = context
# coding: utf-8
"""Python bindings for 0MQ."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import atexit
import weakref

from zmq.backend import Context as ContextBase
from . import constants
from .attrsettr import AttributeSetter
from .constants import ENOTSUP, ctx_opt_names
from .socket import Socket
from zmq.error import ZMQError

from zmq.utils.interop import cast_int_addr


class Context(ContextBase, AttributeSetter):
    """Create a zmq Context
    
    A zmq Context creates sockets via its ``ctx.socket`` method.
    """
    sockopts = None
    _instance = None
    _shadow = False
    _exiting = False
    
    def __init__(self, io_threads=1, **kwargs):
        super(Context, self).__init__(io_threads=io_threads, **kwargs)
        if kwargs.get('shadow', False):
            self._shadow = True
        else:
            self._shadow = False
        self.sockopts = {}
        
        self._exiting = False
        if not self._shadow:
            ctx_ref = weakref.ref(self)
            def _notify_atexit():
                ctx = ctx_ref()
                if ctx is not None:
                    ctx._exiting = True
            atexit.register(_notify_atexit)
    
    def __del__(self):
        """deleting a Context should terminate it, without trying non-threadsafe destroy"""
        if not self._shadow and not self._exiting:
            self.term()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args, **kwargs):
        self.term()
    
    @classmethod
    def shadow(cls, address):
        """Shadow an existing libzmq context
        
        address is the integer address of the libzmq context
        or an FFI pointer to it.
        
        .. versionadded:: 14.1
        """
        address = cast_int_addr(address)
        return cls(shadow=address)
    
    @classmethod
    def shadow_pyczmq(cls, ctx):
        """Shadow an existing pyczmq context
        
        ctx is the FFI `zctx_t *` pointer
        
        .. versionadded:: 14.1
        """
        from pyczmq import zctx
        
        underlying = zctx.underlying(ctx)
        address = cast_int_addr(underlying)
        return cls(shadow=address)

    # static method copied from tornado IOLoop.instance
    @classmethod
    def instance(cls, io_threads=1):
        """Returns a global Context instance.

        Most single-threaded applications have a single, global Context.
        Use this method instead of passing around Context instances
        throughout your code.

        A common pattern for classes that depend on Contexts is to use
        a default argument to enable programs with multiple Contexts
        but not require the argument for simpler applications:

            class MyClass(object):
                def __init__(self, context=None):
                    self.context = context or Context.instance()
        """
        if cls._instance is None or cls._instance.closed:
            cls._instance = cls(io_threads=io_threads)
        return cls._instance
    
    #-------------------------------------------------------------------------
    # Hooks for ctxopt completion
    #-------------------------------------------------------------------------
    
    def __dir__(self):
        keys = dir(self.__class__)

        for collection in (
            ctx_opt_names,
        ):
            keys.extend(collection)
        return keys

    #-------------------------------------------------------------------------
    # Creating Sockets
    #-------------------------------------------------------------------------

    @property
    def _socket_class(self):
        return Socket
    
    def socket(self, socket_type):
        """Create a Socket associated with this Context.

        Parameters
        ----------
        socket_type : int
            The socket type, which can be any of the 0MQ socket types:
            REQ, REP, PUB, SUB, PAIR, DEALER, ROUTER, PULL, PUSH, etc.
        """
        if self.closed:
            raise ZMQError(ENOTSUP)
        s = self._socket_class(self, socket_type)
        for opt, value in self.sockopts.items():
            try:
                s.setsockopt(opt, value)
            except ZMQError:
                # ignore ZMQErrors, which are likely for socket options
                # that do not apply to a particular socket type, e.g.
                # SUBSCRIBE for non-SUB sockets.
                pass
        return s
    
    def setsockopt(self, opt, value):
        """set default socket options for new sockets created by this Context
        
        .. versionadded:: 13.0
        """
        self.sockopts[opt] = value
    
    def getsockopt(self, opt):
        """get default socket options for new sockets created by this Context
        
        .. versionadded:: 13.0
        """
        return self.sockopts[opt]
    
    def _set_attr_opt(self, name, opt, value):
        """set default sockopts as attributes"""
        if name in constants.ctx_opt_names:
            return self.set(opt, value)
        else:
            self.sockopts[opt] = value
    
    def _get_attr_opt(self, name, opt):
        """get default sockopts as attributes"""
        if name in constants.ctx_opt_names:
            return self.get(opt)
        else:
            if opt not in self.sockopts:
                raise AttributeError(name)
            else:
                return self.sockopts[opt]
    
    def __delattr__(self, key):
        """delete default sockopts as attributes"""
        key = key.upper()
        try:
            opt = getattr(constants, key)
        except AttributeError:
            raise AttributeError("no such socket option: %s" % key)
        else:
            if opt not in self.sockopts:
                raise AttributeError(key)
            else:
                del self.sockopts[opt]

__all__ = ['Context']

########NEW FILE########
__FILENAME__ = frame
# coding: utf-8
"""0MQ Frame pure Python methods."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from .attrsettr import AttributeSetter
from zmq.backend import Frame as FrameBase

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

class Frame(FrameBase, AttributeSetter):
    pass

# keep deprecated alias
Message = Frame
__all__ = ['Frame', 'Message']
########NEW FILE########
__FILENAME__ = poll
"""0MQ polling related functions and classes."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import zmq
from zmq.backend import zmq_poll
from .constants import POLLIN, POLLOUT, POLLERR

#-----------------------------------------------------------------------------
# Polling related methods
#-----------------------------------------------------------------------------


class Poller(object):
    """A stateful poll interface that mirrors Python's built-in poll."""
    sockets = None
    _map = {}

    def __init__(self):
        self.sockets = []
        self._map = {}
    
    def __contains__(self, socket):
        return socket in self._map

    def register(self, socket, flags=POLLIN|POLLOUT):
        """p.register(socket, flags=POLLIN|POLLOUT)

        Register a 0MQ socket or native fd for I/O monitoring.
        
        register(s,0) is equivalent to unregister(s).

        Parameters
        ----------
        socket : zmq.Socket or native socket
            A zmq.Socket or any Python object having a ``fileno()`` 
            method that returns a valid file descriptor.
        flags : int
            The events to watch for.  Can be POLLIN, POLLOUT or POLLIN|POLLOUT.
            If `flags=0`, socket will be unregistered.
        """
        if flags:
            if socket in self._map:
                idx = self._map[socket]
                self.sockets[idx] = (socket, flags)
            else:
                idx = len(self.sockets)
                self.sockets.append((socket, flags))
                self._map[socket] = idx
        elif socket in self._map:
            # uregister sockets registered with no events
            self.unregister(socket)
        else:
            # ignore new sockets with no events
            pass

    def modify(self, socket, flags=POLLIN|POLLOUT):
        """Modify the flags for an already registered 0MQ socket or native fd."""
        self.register(socket, flags)

    def unregister(self, socket):
        """Remove a 0MQ socket or native fd for I/O monitoring.

        Parameters
        ----------
        socket : Socket
            The socket instance to stop polling.
        """
        idx = self._map.pop(socket)
        self.sockets.pop(idx)
        # shift indices after deletion
        for socket, flags in self.sockets[idx:]:
            self._map[socket] -= 1

    def poll(self, timeout=None):
        """Poll the registered 0MQ or native fds for I/O.

        Parameters
        ----------
        timeout : float, int
            The timeout in milliseconds. If None, no `timeout` (infinite). This
            is in milliseconds to be compatible with ``select.poll()``. The
            underlying zmq_poll uses microseconds and we convert to that in
            this function.
        
        Returns
        -------
        events : list of tuples
            The list of events that are ready to be processed.
            This is a list of tuples of the form ``(socket, event)``, where the 0MQ Socket
            or integer fd is the first element, and the poll event mask (POLLIN, POLLOUT) is the second.
            It is common to call ``events = dict(poller.poll())``,
            which turns the list of tuples into a mapping of ``socket : event``.
        """
        if timeout is None or timeout < 0:
            timeout = -1
        elif isinstance(timeout, float):
            timeout = int(timeout)
        return zmq_poll(self.sockets, timeout=timeout)


def select(rlist, wlist, xlist, timeout=None):
    """select(rlist, wlist, xlist, timeout=None) -> (rlist, wlist, xlist)

    Return the result of poll as a lists of sockets ready for r/w/exception.

    This has the same interface as Python's built-in ``select.select()`` function.

    Parameters
    ----------
    timeout : float, int, optional
        The timeout in seconds. If None, no timeout (infinite). This is in seconds to be
        compatible with ``select.select()``. The underlying zmq_poll uses microseconds
        and we convert to that in this function.
    rlist : list of sockets/FDs
        sockets/FDs to be polled for read events
    wlist : list of sockets/FDs
        sockets/FDs to be polled for write events
    xlist : list of sockets/FDs
        sockets/FDs to be polled for error events
    
    Returns
    -------
    (rlist, wlist, xlist) : tuple of lists of sockets (length 3)
        Lists correspond to sockets available for read/write/error events respectively.
    """
    if timeout is None:
        timeout = -1
    # Convert from sec -> us for zmq_poll.
    # zmq_poll accepts 3.x style timeout in ms
    timeout = int(timeout*1000.0)
    if timeout < 0:
        timeout = -1
    sockets = []
    for s in set(rlist + wlist + xlist):
        flags = 0
        if s in rlist:
            flags |= POLLIN
        if s in wlist:
            flags |= POLLOUT
        if s in xlist:
            flags |= POLLERR
        sockets.append((s, flags))
    return_sockets = zmq_poll(sockets, timeout)
    rlist, wlist, xlist = [], [], []
    for s, flags in return_sockets:
        if flags & POLLIN:
            rlist.append(s)
        if flags & POLLOUT:
            wlist.append(s)
        if flags & POLLERR:
            xlist.append(s)
    return rlist, wlist, xlist

#-----------------------------------------------------------------------------
# Symbols to export
#-----------------------------------------------------------------------------

__all__ = [ 'Poller', 'select' ]

########NEW FILE########
__FILENAME__ = socket
# coding: utf-8
"""0MQ Socket pure Python methods."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import codecs
import random
import warnings

import zmq
from zmq.backend import Socket as SocketBase
from .poll import Poller
from . import constants
from .attrsettr import AttributeSetter
from zmq.error import ZMQError, ZMQBindError
from zmq.utils import jsonapi
from zmq.utils.strtypes import bytes,unicode,basestring
from zmq.utils.interop import cast_int_addr

from .constants import (
    SNDMORE, ENOTSUP, POLLIN,
    int64_sockopt_names,
    int_sockopt_names,
    bytes_sockopt_names,
)
try:
    import cPickle
    pickle = cPickle
except:
    cPickle = None
    import pickle

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

class Socket(SocketBase, AttributeSetter):
    """The ZMQ socket object
    
    To create a Socket, first create a Context::
    
        ctx = zmq.Context.instance()
    
    then call ``ctx.socket(socket_type)``::
    
        s = ctx.socket(zmq.ROUTER)
    
    """
    _shadow = False
    
    def __del__(self):
        if not self._shadow:
            self.close()

    #-------------------------------------------------------------------------
    # Socket creation
    #-------------------------------------------------------------------------
    
    @classmethod
    def shadow(cls, address):
        """Shadow an existing libzmq socket
        
        address is the integer address of the libzmq socket
        or an FFI pointer to it.
        
        .. versionadded:: 14.1
        """
        address = cast_int_addr(address)
        return cls(shadow=address)
    
    #-------------------------------------------------------------------------
    # Deprecated aliases
    #-------------------------------------------------------------------------
    
    @property
    def socket_type(self):
        warnings.warn("Socket.socket_type is deprecated, use Socket.type",
            DeprecationWarning
        )
        return self.type
    
    #-------------------------------------------------------------------------
    # Hooks for sockopt completion
    #-------------------------------------------------------------------------
    
    def __dir__(self):
        keys = dir(self.__class__)
        for collection in (
            bytes_sockopt_names,
            int_sockopt_names,
            int64_sockopt_names,
        ):
            keys.extend(collection)
        return keys
    
    #-------------------------------------------------------------------------
    # Getting/Setting options
    #-------------------------------------------------------------------------
    setsockopt = SocketBase.set
    getsockopt = SocketBase.get
    
    def set_string(self, option, optval, encoding='utf-8'):
        """set socket options with a unicode object
        
        This is simply a wrapper for setsockopt to protect from encoding ambiguity.

        See the 0MQ documentation for details on specific options.
        
        Parameters
        ----------
        option : int
            The name of the option to set. Can be any of: SUBSCRIBE, 
            UNSUBSCRIBE, IDENTITY
        optval : unicode string (unicode on py2, str on py3)
            The value of the option to set.
        encoding : str
            The encoding to be used, default is utf8
        """
        if not isinstance(optval, unicode):
            raise TypeError("unicode strings only")
        return self.set(option, optval.encode(encoding))
    
    setsockopt_unicode = setsockopt_string = set_string
    
    def get_string(self, option, encoding='utf-8'):
        """get the value of a socket option

        See the 0MQ documentation for details on specific options.

        Parameters
        ----------
        option : int
            The option to retrieve.

        Returns
        -------
        optval : unicode string (unicode on py2, str on py3)
            The value of the option as a unicode string.
        """
    
        if option not in constants.bytes_sockopts:
            raise TypeError("option %i will not return a string to be decoded"%option)
        return self.getsockopt(option).decode(encoding)
    
    getsockopt_unicode = getsockopt_string = get_string
    
    def bind_to_random_port(self, addr, min_port=49152, max_port=65536, max_tries=100):
        """bind this socket to a random port in a range

        Parameters
        ----------
        addr : str
            The address string without the port to pass to ``Socket.bind()``.
        min_port : int, optional
            The minimum port in the range of ports to try (inclusive).
        max_port : int, optional
            The maximum port in the range of ports to try (exclusive).
        max_tries : int, optional
            The maximum number of bind attempts to make.

        Returns
        -------
        port : int
            The port the socket was bound to.
    
        Raises
        ------
        ZMQBindError
            if `max_tries` reached before successful bind
        """
        for i in range(max_tries):
            try:
                port = random.randrange(min_port, max_port)
                self.bind('%s:%s' % (addr, port))
            except ZMQError as exception:
                if not exception.errno == zmq.EADDRINUSE:
                    raise
            else:
                return port
        raise ZMQBindError("Could not bind socket to random port.")
    
    def get_hwm(self):
        """get the High Water Mark
        
        On libzmq ≥ 3, this gets SNDHWM if available, otherwise RCVHWM
        """
        major = zmq.zmq_version_info()[0]
        if major >= 3:
            # return sndhwm, fallback on rcvhwm
            try:
                return self.getsockopt(zmq.SNDHWM)
            except zmq.ZMQError as e:
                pass
            
            return self.getsockopt(zmq.RCVHWM)
        else:
            return self.getsockopt(zmq.HWM)
    
    def set_hwm(self, value):
        """set the High Water Mark
        
        On libzmq ≥ 3, this sets both SNDHWM and RCVHWM
        """
        major = zmq.zmq_version_info()[0]
        if major >= 3:
            raised = None
            try:
                self.sndhwm = value
            except Exception as e:
                raised = e
            try:
                self.rcvhwm = value
            except Exception:
                raised = e
            
            if raised:
                raise raised
        else:
            return self.setsockopt(zmq.HWM, value)
    
    hwm = property(get_hwm, set_hwm,
        """property for High Water Mark
        
        Setting hwm sets both SNDHWM and RCVHWM as appropriate.
        It gets SNDHWM if available, otherwise RCVHWM.
        """
    )
    
    #-------------------------------------------------------------------------
    # Sending and receiving messages
    #-------------------------------------------------------------------------

    def send_multipart(self, msg_parts, flags=0, copy=True, track=False):
        """send a sequence of buffers as a multipart message
        
        The zmq.SNDMORE flag is added to all msg parts before the last.

        Parameters
        ----------
        msg_parts : iterable
            A sequence of objects to send as a multipart message. Each element
            can be any sendable object (Frame, bytes, buffer-providers)
        flags : int, optional
            SNDMORE is handled automatically for frames before the last.
        copy : bool, optional
            Should the frame(s) be sent in a copying or non-copying manner.
        track : bool, optional
            Should the frame(s) be tracked for notification that ZMQ has
            finished with it (ignored if copy=True).
    
        Returns
        -------
        None : if copy or not track
        MessageTracker : if track and not copy
            a MessageTracker object, whose `pending` property will
            be True until the last send is completed.
        """
        for msg in msg_parts[:-1]:
            self.send(msg, SNDMORE|flags, copy=copy, track=track)
        # Send the last part without the extra SNDMORE flag.
        return self.send(msg_parts[-1], flags, copy=copy, track=track)

    def recv_multipart(self, flags=0, copy=True, track=False):
        """receive a multipart message as a list of bytes or Frame objects

        Parameters
        ----------
        flags : int, optional
            Any supported flag: NOBLOCK. If NOBLOCK is set, this method
            will raise a ZMQError with EAGAIN if a message is not ready.
            If NOBLOCK is not set, then this method will block until a
            message arrives.
        copy : bool, optional
            Should the message frame(s) be received in a copying or non-copying manner?
            If False a Frame object is returned for each part, if True a copy of
            the bytes is made for each frame.
        track : bool, optional
            Should the message frame(s) be tracked for notification that ZMQ has
            finished with it? (ignored if copy=True)
        
        Returns
        -------
        msg_parts : list
            A list of frames in the multipart message; either Frames or bytes,
            depending on `copy`.
    
        """
        parts = [self.recv(flags, copy=copy, track=track)]
        # have first part already, only loop while more to receive
        while self.getsockopt(zmq.RCVMORE):
            part = self.recv(flags, copy=copy, track=track)
            parts.append(part)
    
        return parts

    def send_string(self, u, flags=0, copy=True, encoding='utf-8'):
        """send a Python unicode string as a message with an encoding
    
        0MQ communicates with raw bytes, so you must encode/decode
        text (unicode on py2, str on py3) around 0MQ.
        
        Parameters
        ----------
        u : Python unicode string (unicode on py2, str on py3)
            The unicode string to send.
        flags : int, optional
            Any valid send flag.
        encoding : str [default: 'utf-8']
            The encoding to be used
        """
        if not isinstance(u, basestring):
            raise TypeError("unicode/str objects only")
        return self.send(u.encode(encoding), flags=flags, copy=copy)
    
    send_unicode = send_string
    
    def recv_string(self, flags=0, encoding='utf-8'):
        """receive a unicode string, as sent by send_string
    
        Parameters
        ----------
        flags : int
            Any valid recv flag.
        encoding : str [default: 'utf-8']
            The encoding to be used

        Returns
        -------
        s : unicode string (unicode on py2, str on py3)
            The Python unicode string that arrives as encoded bytes.
        """
        b = self.recv(flags=flags)
        return b.decode(encoding)
    
    recv_unicode = recv_string
    
    def send_pyobj(self, obj, flags=0, protocol=-1):
        """send a Python object as a message using pickle to serialize

        Parameters
        ----------
        obj : Python object
            The Python object to send.
        flags : int
            Any valid send flag.
        protocol : int
            The pickle protocol number to use. Default of -1 will select
            the highest supported number. Use 0 for multiple platform
            support.
        """
        msg = pickle.dumps(obj, protocol)
        return self.send(msg, flags)

    def recv_pyobj(self, flags=0):
        """receive a Python object as a message using pickle to serialize

        Parameters
        ----------
        flags : int
            Any valid recv flag.

        Returns
        -------
        obj : Python object
            The Python object that arrives as a message.
        """
        s = self.recv(flags)
        return pickle.loads(s)

    def send_json(self, obj, flags=0, **kwargs):
        """send a Python object as a message using json to serialize
        
        Keyword arguments are passed on to json.dumps
        
        Parameters
        ----------
        obj : Python object
            The Python object to send
        flags : int
            Any valid send flag
        """
        msg = jsonapi.dumps(obj, **kwargs)
        return self.send(msg, flags)

    def recv_json(self, flags=0, **kwargs):
        """receive a Python object as a message using json to serialize

        Keyword arguments are passed on to json.loads
        
        Parameters
        ----------
        flags : int
            Any valid recv flag.

        Returns
        -------
        obj : Python object
            The Python object that arrives as a message.
        """
        msg = self.recv(flags)
        return jsonapi.loads(msg, **kwargs)
    
    _poller_class = Poller

    def poll(self, timeout=None, flags=POLLIN):
        """poll the socket for events
        
        The default is to poll forever for incoming
        events.  Timeout is in milliseconds, if specified.

        Parameters
        ----------
        timeout : int [default: None]
            The timeout (in milliseconds) to wait for an event. If unspecified
            (or specified None), will wait forever for an event.
        flags : bitfield (int) [default: POLLIN]
            The event flags to poll for (any combination of POLLIN|POLLOUT).
            The default is to check for incoming events (POLLIN).

        Returns
        -------
        events : bitfield (int)
            The events that are ready and waiting.  Will be 0 if no events were ready
            by the time timeout was reached.
        """

        if self.closed:
            raise ZMQError(ENOTSUP)

        p = self._poller_class()
        p.register(self, flags)
        evts = dict(p.poll(timeout))
        # return 0 if no events, otherwise return event bitfield
        return evts.get(self, 0)

    def get_monitor_socket(self, events=None, addr=None):
        """Return a connected PAIR socket ready to receive the event notifications.
        
        .. versionadded:: libzmq-4.0
        .. versionadded:: 14.0
        
        Parameters
        ----------
        events : bitfield (int) [default: ZMQ_EVENTS_ALL]
            The bitmask defining which events are wanted.
        addr :  string [default: None]
            The optional endpoint for the monitoring sockets.

        Returns
        -------
        socket :  (PAIR)
            The socket is already connected and ready to receive messages.
        """
        # safe-guard, method only available on libzmq >= 4
        if zmq.zmq_version_info() < (4,):
            raise NotImplementedError("get_monitor_socket requires libzmq >= 4, have %s" % zmq.zmq_version())
        if addr is None:
            # create endpoint name from internal fd
            addr = "inproc://monitor.s-%d" % self.FD
        if events is None:
            # use all events
            events = zmq.EVENT_ALL
        # attach monitoring socket
        self.monitor(addr, events)
        # create new PAIR socket and connect it
        ret = self.context.socket(zmq.PAIR)
        ret.connect(addr)
        return ret


__all__ = ['Socket']

########NEW FILE########
__FILENAME__ = tracker
"""Tracker for zero-copy messages with 0MQ."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import time

try:
    # below 3.3
    from threading import _Event as Event
except (ImportError, AttributeError):
    # python throws ImportError, cython throws AttributeError
    from threading import Event

from zmq.error import NotDone
from zmq.backend import Frame

class MessageTracker(object):
    """MessageTracker(*towatch)

    A class for tracking if 0MQ is done using one or more messages.

    When you send a 0MQ message, it is not sent immediately. The 0MQ IO thread
    sends the message at some later time. Often you want to know when 0MQ has
    actually sent the message though. This is complicated by the fact that
    a single 0MQ message can be sent multiple times using different sockets.
    This class allows you to track all of the 0MQ usages of a message.

    Parameters
    ----------
    *towatch : tuple of Event, MessageTracker, Message instances.
        This list of objects to track. This class can track the low-level
        Events used by the Message class, other MessageTrackers or
        actual Messages.
    """
    events = None
    peers = None

    def __init__(self, *towatch):
        """MessageTracker(*towatch)

        Create a message tracker to track a set of mesages.

        Parameters
        ----------
        *towatch : tuple of Event, MessageTracker, Message instances.
            This list of objects to track. This class can track the low-level
            Events used by the Message class, other MessageTrackers or 
            actual Messages.
        """
        self.events = set()
        self.peers = set()
        for obj in towatch:
            if isinstance(obj, Event):
                self.events.add(obj)
            elif isinstance(obj, MessageTracker):
                self.peers.add(obj)
            elif isinstance(obj, Frame):
                if not obj.tracker:
                    raise ValueError("Not a tracked message")
                self.peers.add(obj.tracker)
            else:
                raise TypeError("Require Events or Message Frames, not %s"%type(obj))
    
    @property
    def done(self):
        """Is 0MQ completely done with the message(s) being tracked?"""
        for evt in self.events:
            if not evt.is_set():
                return False
        for pm in self.peers:
            if not pm.done:
                return False
        return True
    
    def wait(self, timeout=-1):
        """mt.wait(timeout=-1)

        Wait for 0MQ to be done with the message or until `timeout`.

        Parameters
        ----------
        timeout : float [default: -1, wait forever]
            Maximum time in (s) to wait before raising NotDone.

        Returns
        -------
        None
            if done before `timeout`
        
        Raises
        ------
        NotDone
            if `timeout` reached before I am done.
        """
        tic = time.time()
        if timeout is False or timeout < 0:
            remaining = 3600*24*7 # a week
        else:
            remaining = timeout
        done = False
        for evt in self.events:
            if remaining < 0:
                raise NotDone
            evt.wait(timeout=remaining)
            if not evt.is_set():
                raise NotDone
            toc = time.time()
            remaining -= (toc-tic)
            tic = toc
        
        for peer in self.peers:
            if remaining < 0:
                raise NotDone
            peer.wait(timeout=remaining)
            toc = time.time()
            remaining -= (toc-tic)
            tic = toc

__all__ = ['MessageTracker']
########NEW FILE########
__FILENAME__ = version
"""PyZMQ and 0MQ version functions."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from zmq.backend import zmq_version_info

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

VERSION_MAJOR = 14
VERSION_MINOR = 4
VERSION_PATCH = 0
VERSION_EXTRA = 'dev'
__version__ = '%i.%i.%i' % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

if VERSION_EXTRA:
    __version__ = "%s-%s" % (__version__, VERSION_EXTRA)
    version_info = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, float('inf'))
else:
    version_info = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

__revision__ = ''

def pyzmq_version():
    """return the version of pyzmq as a string"""
    if __revision__:
        return '@'.join([__version__,__revision__[:6]])
    else:
        return __version__

def pyzmq_version_info():
    """return the pyzmq version as a tuple of at least three numbers
    
    If pyzmq is a development version, `inf` will be appended after the third integer.
    """
    return version_info


def zmq_version():
    """return the version of libzmq as a string"""
    return "%i.%i.%i" % zmq_version_info()


__all__ = ['zmq_version', 'zmq_version_info',
           'pyzmq_version','pyzmq_version_info',
           '__version__', '__revision__'
]


########NEW FILE########
__FILENAME__ = test_auth
# -*- coding: utf8 -*-
#-----------------------------------------------------------------------------
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import logging
import os
import shutil
import sys
import tempfile

import zmq.auth
from zmq.auth.ioloop import IOLoopAuthenticator
from zmq.auth.thread import ThreadAuthenticator

from zmq.eventloop import ioloop, zmqstream
from zmq.tests import (BaseZMQTestCase, SkipTest)

class BaseAuthTestCase(BaseZMQTestCase):
    def setUp(self):
        if zmq.zmq_version_info() < (4,0):
            raise SkipTest("security is new in libzmq 4.0")
        try:
            zmq.curve_keypair()
        except zmq.ZMQError:
            raise SkipTest("security requires libzmq to be linked against libsodium")
        super(BaseAuthTestCase, self).setUp()
        # enable debug logging while we run tests
        logging.getLogger('zmq.auth').setLevel(logging.DEBUG)
        self.auth = self.make_auth()
        self.auth.start()
        self.base_dir, self.public_keys_dir, self.secret_keys_dir = self.create_certs()
    
    def make_auth(self):
        raise NotImplementedError()
    
    def tearDown(self):
        if self.auth:
            self.auth.stop()
            self.auth = None
        self.remove_certs(self.base_dir)
        super(BaseAuthTestCase, self).tearDown()
    
    def create_certs(self):
        """Create CURVE certificates for a test"""

        # Create temporary CURVE keypairs for this test run. We create all keys in a
        # temp directory and then move them into the appropriate private or public
        # directory.

        base_dir = tempfile.mkdtemp()
        keys_dir = os.path.join(base_dir, 'certificates')
        public_keys_dir = os.path.join(base_dir, 'public_keys')
        secret_keys_dir = os.path.join(base_dir, 'private_keys')

        os.mkdir(keys_dir)
        os.mkdir(public_keys_dir)
        os.mkdir(secret_keys_dir)

        server_public_file, server_secret_file = zmq.auth.create_certificates(keys_dir, "server")
        client_public_file, client_secret_file = zmq.auth.create_certificates(keys_dir, "client")

        for key_file in os.listdir(keys_dir):
            if key_file.endswith(".key"):
                shutil.move(os.path.join(keys_dir, key_file),
                            os.path.join(public_keys_dir, '.'))

        for key_file in os.listdir(keys_dir):
            if key_file.endswith(".key_secret"):
                shutil.move(os.path.join(keys_dir, key_file),
                            os.path.join(secret_keys_dir, '.'))

        return (base_dir, public_keys_dir, secret_keys_dir)

    def remove_certs(self, base_dir):
        """Remove certificates for a test"""
        shutil.rmtree(base_dir)

    def load_certs(self, secret_keys_dir):
        """Return server and client certificate keys"""
        server_secret_file = os.path.join(secret_keys_dir, "server.key_secret")
        client_secret_file = os.path.join(secret_keys_dir, "client.key_secret")

        server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)

        return server_public, server_secret, client_public, client_secret



class TestThreadAuthentication(BaseAuthTestCase):
    """Test authentication running in a thread"""

    def make_auth(self):
        return ThreadAuthenticator(self.context)

    def can_connect(self, server, client):
        """Check if client can connect to server using tcp transport"""
        result = False
        iface = 'tcp://127.0.0.1'
        port = server.bind_to_random_port(iface)
        client.connect("%s:%i" % (iface, port))
        msg = [b"Hello World"]
        server.send_multipart(msg)
        if client.poll(1000):
            rcvd_msg = client.recv_multipart()
            self.assertEqual(rcvd_msg, msg)
            result = True
        return result

    def test_null(self):
        """threaded auth - NULL"""
        # A default NULL connection should always succeed, and not
        # go through our authentication infrastructure at all.
        self.auth.stop()
        self.auth = None
        
        server = self.socket(zmq.PUSH)
        client = self.socket(zmq.PULL)
        self.assertTrue(self.can_connect(server, client))

        # By setting a domain we switch on authentication for NULL sockets,
        # though no policies are configured yet. The client connection
        # should still be allowed.
        server = self.socket(zmq.PUSH)
        server.zap_domain = b'global'
        client = self.socket(zmq.PULL)
        self.assertTrue(self.can_connect(server, client))

    def test_blacklist(self):
        """threaded auth - Blacklist"""
        # Blacklist 127.0.0.1, connection should fail
        self.auth.deny('127.0.0.1')
        server = self.socket(zmq.PUSH)
        # By setting a domain we switch on authentication for NULL sockets,
        # though no policies are configured yet.
        server.zap_domain = b'global'
        client = self.socket(zmq.PULL)
        self.assertFalse(self.can_connect(server, client))

    def test_whitelist(self):
        """threaded auth - Whitelist"""
        # Whitelist 127.0.0.1, connection should pass"
        self.auth.allow('127.0.0.1')
        server = self.socket(zmq.PUSH)
        # By setting a domain we switch on authentication for NULL sockets,
        # though no policies are configured yet.
        server.zap_domain = b'global'
        client = self.socket(zmq.PULL)
        self.assertTrue(self.can_connect(server, client))

    def test_plain(self):
        """threaded auth - PLAIN"""

        # Try PLAIN authentication - without configuring server, connection should fail
        server = self.socket(zmq.PUSH)
        server.plain_server = True
        client = self.socket(zmq.PULL)
        client.plain_username = b'admin'
        client.plain_password = b'Password'
        self.assertFalse(self.can_connect(server, client))

        # Try PLAIN authentication - with server configured, connection should pass
        server = self.socket(zmq.PUSH)
        server.plain_server = True
        client = self.socket(zmq.PULL)
        client.plain_username = b'admin'
        client.plain_password = b'Password'
        self.auth.configure_plain(domain='*', passwords={'admin': 'Password'})
        self.assertTrue(self.can_connect(server, client))

        # Try PLAIN authentication - with bogus credentials, connection should fail
        server = self.socket(zmq.PUSH)
        server.plain_server = True
        client = self.socket(zmq.PULL)
        client.plain_username = b'admin'
        client.plain_password = b'Bogus'
        self.assertFalse(self.can_connect(server, client))

        # Remove authenticator and check that a normal connection works
        self.auth.stop()
        self.auth = None

        server = self.socket(zmq.PUSH)
        client = self.socket(zmq.PULL)
        self.assertTrue(self.can_connect(server, client))
        client.close()
        server.close()

    def test_curve(self):
        """threaded auth - CURVE"""
        self.auth.allow('127.0.0.1')
        certs = self.load_certs(self.secret_keys_dir)
        server_public, server_secret, client_public, client_secret = certs

        #Try CURVE authentication - without configuring server, connection should fail
        server = self.socket(zmq.PUSH)
        server.curve_publickey = server_public
        server.curve_secretkey = server_secret
        server.curve_server = True
        client = self.socket(zmq.PULL)
        client.curve_publickey = client_public
        client.curve_secretkey = client_secret
        client.curve_serverkey = server_public
        self.assertFalse(self.can_connect(server, client))

        #Try CURVE authentication - with server configured to CURVE_ALLOW_ANY, connection should pass
        self.auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)
        server = self.socket(zmq.PUSH)
        server.curve_publickey = server_public
        server.curve_secretkey = server_secret
        server.curve_server = True
        client = self.socket(zmq.PULL)
        client.curve_publickey = client_public
        client.curve_secretkey = client_secret
        client.curve_serverkey = server_public
        self.assertTrue(self.can_connect(server, client))

        # Try CURVE authentication - with server configured, connection should pass
        self.auth.configure_curve(domain='*', location=self.public_keys_dir)
        server = self.socket(zmq.PUSH)
        server.curve_publickey = server_public
        server.curve_secretkey = server_secret
        server.curve_server = True
        client = self.socket(zmq.PULL)
        client.curve_publickey = client_public
        client.curve_secretkey = client_secret
        client.curve_serverkey = server_public
        self.assertTrue(self.can_connect(server, client))

        # Remove authenticator and check that a normal connection works
        self.auth.stop()
        self.auth = None

        # Try connecting using NULL and no authentication enabled, connection should pass
        server = self.socket(zmq.PUSH)
        client = self.socket(zmq.PULL)
        self.assertTrue(self.can_connect(server, client))


def with_ioloop(method, expect_success=True):
    """decorator for running tests with an IOLoop"""
    def test_method(self):
        r = method(self)
        
        loop = self.io_loop
        if expect_success:
            self.pullstream.on_recv(self.on_message_succeed)
        else:
            self.pullstream.on_recv(self.on_message_fail)
        
        t = loop.time()
        loop.add_callback(self.attempt_connection)
        loop.add_callback(self.send_msg)
        if expect_success:
            loop.add_timeout(t + 1, self.on_test_timeout_fail)
        else:
            loop.add_timeout(t + 1, self.on_test_timeout_succeed)
        
        loop.start()
        if self.fail_msg:
            self.fail(self.fail_msg)
        
        return r
    return test_method

def should_auth(method):
    return with_ioloop(method, True)

def should_not_auth(method):
    return with_ioloop(method, False)

class TestIOLoopAuthentication(BaseAuthTestCase):
    """Test authentication running in ioloop"""

    def setUp(self):
        self.fail_msg = None
        self.io_loop = ioloop.IOLoop()
        super(TestIOLoopAuthentication, self).setUp()
        self.server = self.socket(zmq.PUSH)
        self.client = self.socket(zmq.PULL)
        self.pushstream = zmqstream.ZMQStream(self.server, self.io_loop)
        self.pullstream = zmqstream.ZMQStream(self.client, self.io_loop)
    
    def make_auth(self):
        return IOLoopAuthenticator(self.context, io_loop=self.io_loop)

    def tearDown(self):
        if self.auth:
            self.auth.stop()
            self.auth = None
        self.io_loop.close(all_fds=True)
        super(TestIOLoopAuthentication, self).tearDown()

    def attempt_connection(self):
        """Check if client can connect to server using tcp transport"""
        iface = 'tcp://127.0.0.1'
        port = self.server.bind_to_random_port(iface)
        self.client.connect("%s:%i" % (iface, port))

    def send_msg(self):
        """Send a message from server to a client"""
        msg = [b"Hello World"]
        self.pushstream.send_multipart(msg)
    
    def on_message_succeed(self, frames):
        """A message was received, as expected."""
        if frames != [b"Hello World"]:
            self.fail_msg = "Unexpected message received"
        self.io_loop.stop()

    def on_message_fail(self, frames):
        """A message was received, unexpectedly."""
        self.fail_msg = 'Received messaged unexpectedly, security failed'
        self.io_loop.stop()

    def on_test_timeout_succeed(self):
        """Test timer expired, indicates test success"""
        self.io_loop.stop()

    def on_test_timeout_fail(self):
        """Test timer expired, indicates test failure"""
        self.fail_msg = 'Test timed out'
        self.io_loop.stop()

    @should_auth
    def test_none(self):
        """ioloop auth - NONE"""
        # A default NULL connection should always succeed, and not
        # go through our authentication infrastructure at all.
        # no auth should be running
        self.auth.stop()
        self.auth = None

    @should_auth
    def test_null(self):
        """ioloop auth - NULL"""
        # By setting a domain we switch on authentication for NULL sockets,
        # though no policies are configured yet. The client connection
        # should still be allowed.
        self.server.zap_domain = b'global'

    @should_not_auth
    def test_blacklist(self):
        """ioloop auth - Blacklist"""
        # Blacklist 127.0.0.1, connection should fail
        self.auth.deny('127.0.0.1')
        self.server.zap_domain = b'global'

    @should_auth
    def test_whitelist(self):
        """ioloop auth - Whitelist"""
        # Whitelist 127.0.0.1, which overrides the blacklist, connection should pass"
        self.auth.allow('127.0.0.1')

        self.server.setsockopt(zmq.ZAP_DOMAIN, b'global')

    @should_not_auth
    def test_plain_unconfigured_server(self):
        """ioloop auth - PLAIN, unconfigured server"""
        self.client.plain_username = b'admin'
        self.client.plain_password = b'Password'
        # Try PLAIN authentication - without configuring server, connection should fail
        self.server.plain_server = True

    @should_auth
    def test_plain_configured_server(self):
        """ioloop auth - PLAIN, configured server"""
        self.client.plain_username = b'admin'
        self.client.plain_password = b'Password'
        # Try PLAIN authentication - with server configured, connection should pass
        self.server.plain_server = True
        self.auth.configure_plain(domain='*', passwords={'admin': 'Password'})

    @should_not_auth
    def test_plain_bogus_credentials(self):
        """ioloop auth - PLAIN, bogus credentials"""
        self.client.plain_username = b'admin'
        self.client.plain_password = b'Bogus'
        self.server.plain_server = True

        self.auth.configure_plain(domain='*', passwords={'admin': 'Password'})

    @should_not_auth
    def test_curve_unconfigured_server(self):
        """ioloop auth - CURVE, unconfigured server"""
        certs = self.load_certs(self.secret_keys_dir)
        server_public, server_secret, client_public, client_secret = certs

        self.auth.allow('127.0.0.1')

        self.server.curve_publickey = server_public
        self.server.curve_secretkey = server_secret
        self.server.curve_server = True

        self.client.curve_publickey = client_public
        self.client.curve_secretkey = client_secret
        self.client.curve_serverkey = server_public

    @should_auth
    def test_curve_allow_any(self):
        """ioloop auth - CURVE, CURVE_ALLOW_ANY"""
        certs = self.load_certs(self.secret_keys_dir)
        server_public, server_secret, client_public, client_secret = certs

        self.auth.allow('127.0.0.1')
        self.auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)

        self.server.curve_publickey = server_public
        self.server.curve_secretkey = server_secret
        self.server.curve_server = True

        self.client.curve_publickey = client_public
        self.client.curve_secretkey = client_secret
        self.client.curve_serverkey = server_public

    @should_auth
    def test_curve_configured_server(self):
        """ioloop auth - CURVE, configured server"""
        self.auth.allow('127.0.0.1')
        certs = self.load_certs(self.secret_keys_dir)
        server_public, server_secret, client_public, client_secret = certs

        self.auth.configure_curve(domain='*', location=self.public_keys_dir)

        self.server.curve_publickey = server_public
        self.server.curve_secretkey = server_secret
        self.server.curve_server = True

        self.client.curve_publickey = client_public
        self.client.curve_secretkey = client_secret
        self.client.curve_serverkey = server_public

########NEW FILE########
__FILENAME__ = test_cffi_backend
# -*- coding: utf8 -*-

import sys
import time

from unittest import TestCase

from zmq.tests import BaseZMQTestCase, SkipTest

try:
    from zmq.backend.cffi import (
        zmq_version_info,
        PUSH, PULL, IDENTITY,
        REQ, REP, POLLIN, POLLOUT,
    )
    from zmq.backend.cffi._cffi import ffi, C
    have_ffi_backend = True
except ImportError:
    have_ffi_backend = False


class TestCFFIBackend(TestCase):
    
    def setUp(self):
        if not have_ffi_backend or not 'PyPy' in sys.version:
            raise SkipTest('PyPy Tests Only')

    def test_zmq_version_info(self):
        version = zmq_version_info()

        assert version[0] in range(2,11)

    def test_zmq_ctx_new_destroy(self):
        ctx = C.zmq_ctx_new()

        assert ctx != ffi.NULL
        assert 0 == C.zmq_ctx_destroy(ctx)

    def test_zmq_socket_open_close(self):
        ctx = C.zmq_ctx_new()
        socket = C.zmq_socket(ctx, PUSH)

        assert ctx != ffi.NULL
        assert ffi.NULL != socket
        assert 0 == C.zmq_close(socket)
        assert 0 == C.zmq_ctx_destroy(ctx)

    def test_zmq_setsockopt(self):
        ctx = C.zmq_ctx_new()
        socket = C.zmq_socket(ctx, PUSH)

        identity = ffi.new('char[3]', 'zmq')
        ret = C.zmq_setsockopt(socket, IDENTITY, ffi.cast('void*', identity), 3)

        assert ret == 0
        assert ctx != ffi.NULL
        assert ffi.NULL != socket
        assert 0 == C.zmq_close(socket)
        assert 0 == C.zmq_ctx_destroy(ctx)

    def test_zmq_getsockopt(self):
        ctx = C.zmq_ctx_new()
        socket = C.zmq_socket(ctx, PUSH)

        identity = ffi.new('char[]', 'zmq')
        ret = C.zmq_setsockopt(socket, IDENTITY, ffi.cast('void*', identity), 3)
        assert ret == 0

        option_len = ffi.new('size_t*', 3)
        option = ffi.new('char*')
        ret = C.zmq_getsockopt(socket,
                            IDENTITY,
                            ffi.cast('void*', option),
                            option_len)

        assert ret == 0
        assert ffi.string(ffi.cast('char*', option))[0] == "z"
        assert ffi.string(ffi.cast('char*', option))[1] == "m"
        assert ffi.string(ffi.cast('char*', option))[2] == "q"
        assert ctx != ffi.NULL
        assert ffi.NULL != socket
        assert 0 == C.zmq_close(socket)
        assert 0 == C.zmq_ctx_destroy(ctx)

    def test_zmq_bind(self):
        ctx = C.zmq_ctx_new()
        socket = C.zmq_socket(ctx, 8)

        assert 0 == C.zmq_bind(socket, 'tcp://*:4444')
        assert ctx != ffi.NULL
        assert ffi.NULL != socket
        assert 0 == C.zmq_close(socket)
        assert 0 == C.zmq_ctx_destroy(ctx)

    def test_zmq_bind_connect(self):
        ctx = C.zmq_ctx_new()

        socket1 = C.zmq_socket(ctx, PUSH)
        socket2 = C.zmq_socket(ctx, PULL)

        assert 0 == C.zmq_bind(socket1, 'tcp://*:4444')
        assert 0 == C.zmq_connect(socket2, 'tcp://127.0.0.1:4444')
        assert ctx != ffi.NULL
        assert ffi.NULL != socket1
        assert ffi.NULL != socket2
        assert 0 == C.zmq_close(socket1)
        assert 0 == C.zmq_close(socket2)
        assert 0 == C.zmq_ctx_destroy(ctx)

    def test_zmq_msg_init_close(self):
        zmq_msg = ffi.new('zmq_msg_t*')

        assert ffi.NULL != zmq_msg
        assert 0 == C.zmq_msg_init(zmq_msg)
        assert 0 == C.zmq_msg_close(zmq_msg)

    def test_zmq_msg_init_size(self):
        zmq_msg = ffi.new('zmq_msg_t*')

        assert ffi.NULL != zmq_msg
        assert 0 == C.zmq_msg_init_size(zmq_msg, 10)
        assert 0 == C.zmq_msg_close(zmq_msg)

    def test_zmq_msg_init_data(self):
        zmq_msg = ffi.new('zmq_msg_t*')
        message = ffi.new('char[5]', 'Hello')

        assert 0 == C.zmq_msg_init_data(zmq_msg,
                                        ffi.cast('void*', message),
                                        5,
                                        ffi.NULL,
                                        ffi.NULL)

        assert ffi.NULL != zmq_msg
        assert 0 == C.zmq_msg_close(zmq_msg)

    def test_zmq_msg_data(self):
        zmq_msg = ffi.new('zmq_msg_t*')
        message = ffi.new('char[]', 'Hello')
        assert 0 == C.zmq_msg_init_data(zmq_msg,
                                        ffi.cast('void*', message),
                                        5,
                                        ffi.NULL,
                                        ffi.NULL)

        data = C.zmq_msg_data(zmq_msg)

        assert ffi.NULL != zmq_msg
        assert ffi.string(ffi.cast("char*", data)) == 'Hello'
        assert 0 == C.zmq_msg_close(zmq_msg)


    def test_zmq_send(self):
        ctx = C.zmq_ctx_new()

        sender = C.zmq_socket(ctx, REQ)
        receiver = C.zmq_socket(ctx, REP)

        assert 0 == C.zmq_bind(receiver, 'tcp://*:7777')
        assert 0 == C.zmq_connect(sender, 'tcp://127.0.0.1:7777')

        time.sleep(0.1)

        zmq_msg = ffi.new('zmq_msg_t*')
        message = ffi.new('char[5]', 'Hello')

        C.zmq_msg_init_data(zmq_msg,
                            ffi.cast('void*', message),
                            ffi.cast('size_t', 5),
                            ffi.NULL,
                            ffi.NULL)

        assert 5 == C.zmq_msg_send(zmq_msg, sender, 0)
        assert 0 == C.zmq_msg_close(zmq_msg)
        assert C.zmq_close(sender) == 0
        assert C.zmq_close(receiver) == 0
        assert C.zmq_ctx_destroy(ctx) == 0

    def test_zmq_recv(self):
        ctx = C.zmq_ctx_new()

        sender = C.zmq_socket(ctx, REQ)
        receiver = C.zmq_socket(ctx, REP)

        assert 0 == C.zmq_bind(receiver, 'tcp://*:2222')
        assert 0 == C.zmq_connect(sender, 'tcp://127.0.0.1:2222')

        time.sleep(0.1)

        zmq_msg = ffi.new('zmq_msg_t*')
        message = ffi.new('char[5]', 'Hello')

        C.zmq_msg_init_data(zmq_msg,
                            ffi.cast('void*', message),
                            ffi.cast('size_t', 5),
                            ffi.NULL,
                            ffi.NULL)

        zmq_msg2 = ffi.new('zmq_msg_t*')
        C.zmq_msg_init(zmq_msg2)

        assert 5 == C.zmq_msg_send(zmq_msg, sender, 0)
        assert 5 == C.zmq_msg_recv(zmq_msg2, receiver, 0)
        assert 5 == C.zmq_msg_size(zmq_msg2)
        assert b"Hello" == ffi.buffer(C.zmq_msg_data(zmq_msg2),
                                      C.zmq_msg_size(zmq_msg2))[:]
        assert C.zmq_close(sender) == 0
        assert C.zmq_close(receiver) == 0
        assert C.zmq_ctx_destroy(ctx) == 0

    def test_zmq_poll(self):
        ctx = C.zmq_ctx_new()

        sender = C.zmq_socket(ctx, REQ)
        receiver = C.zmq_socket(ctx, REP)

        r1 = C.zmq_bind(receiver, 'tcp://*:3333')
        r2 = C.zmq_connect(sender, 'tcp://127.0.0.1:3333')

        zmq_msg = ffi.new('zmq_msg_t*')
        message = ffi.new('char[5]', 'Hello')

        C.zmq_msg_init_data(zmq_msg,
                            ffi.cast('void*', message),
                            ffi.cast('size_t', 5),
                            ffi.NULL,
                            ffi.NULL)

        receiver_pollitem = ffi.new('zmq_pollitem_t*')
        receiver_pollitem.socket = receiver
        receiver_pollitem.fd = 0
        receiver_pollitem.events = POLLIN | POLLOUT
        receiver_pollitem.revents = 0

        ret = C.zmq_poll(ffi.NULL, 0, 0)
        assert ret == 0

        ret = C.zmq_poll(receiver_pollitem, 1, 0)
        assert ret == 0

        ret = C.zmq_msg_send(zmq_msg, sender, 0)
        print(ffi.string(C.zmq_strerror(C.zmq_errno())))
        assert ret == 5

        time.sleep(0.2)

        ret = C.zmq_poll(receiver_pollitem, 1, 0)
        assert ret == 1

        assert int(receiver_pollitem.revents) & POLLIN
        assert not int(receiver_pollitem.revents) & POLLOUT

        zmq_msg2 = ffi.new('zmq_msg_t*')
        C.zmq_msg_init(zmq_msg2)

        ret_recv = C.zmq_msg_recv(zmq_msg2, receiver, 0)
        assert ret_recv == 5

        assert 5 == C.zmq_msg_size(zmq_msg2)
        assert b"Hello" == ffi.buffer(C.zmq_msg_data(zmq_msg2),
                                    C.zmq_msg_size(zmq_msg2))[:]

        sender_pollitem = ffi.new('zmq_pollitem_t*')
        sender_pollitem.socket = sender
        sender_pollitem.fd = 0
        sender_pollitem.events = POLLIN | POLLOUT
        sender_pollitem.revents = 0

        ret = C.zmq_poll(sender_pollitem, 1, 0)
        assert ret == 0

        zmq_msg_again = ffi.new('zmq_msg_t*')
        message_again = ffi.new('char[11]', 'Hello Again')

        C.zmq_msg_init_data(zmq_msg_again,
                            ffi.cast('void*', message_again),
                            ffi.cast('size_t', 11),
                            ffi.NULL,
                            ffi.NULL)

        assert 11 == C.zmq_msg_send(zmq_msg_again, receiver, 0)

        time.sleep(0.2)

        assert 0 <= C.zmq_poll(sender_pollitem, 1, 0)
        assert int(sender_pollitem.revents) & POLLIN
        assert 11 == C.zmq_msg_recv(zmq_msg2, sender, 0)
        assert 11 == C.zmq_msg_size(zmq_msg2)
        assert b"Hello Again" == ffi.buffer(C.zmq_msg_data(zmq_msg2),
                                            int(C.zmq_msg_size(zmq_msg2)))[:]
        assert 0 == C.zmq_close(sender)
        assert 0 == C.zmq_close(receiver)
        assert 0 == C.zmq_ctx_destroy(ctx)
        assert 0 == C.zmq_msg_close(zmq_msg)
        assert 0 == C.zmq_msg_close(zmq_msg2)
        assert 0 == C.zmq_msg_close(zmq_msg_again)

    def test_zmq_stopwatch_functions(self):
        stopwatch = C.zmq_stopwatch_start()
        ret = C.zmq_stopwatch_stop(stopwatch)

        assert ffi.NULL != stopwatch
        assert 0 < int(ret)

    def test_zmq_sleep(self):
        try:
            C.zmq_sleep(1)
        except Exception as e:
            raise AssertionError("Error executing zmq_sleep(int)")


########NEW FILE########
__FILENAME__ = test_constants
#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import json
from unittest import TestCase

import zmq

from zmq.utils import constant_names
from zmq.sugar import constants as sugar_constants
from zmq.backend import constants as backend_constants

all_set = set(constant_names.all_names)
#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestConstants(TestCase):
    
    def _duplicate_test(self, namelist, listname):
        """test that a given list has no duplicates"""
        dupes = {}
        for name in set(namelist):
            cnt = namelist.count(name)
            if cnt > 1:
                dupes[name] = cnt
        if dupes:
            self.fail("The following names occur more than once in %s: %s" % (listname, json.dumps(dupes, indent=2)))
    
    def test_duplicate_all(self):
        return self._duplicate_test(constant_names.all_names, "all_names")
    
    def _change_key(self, change, version):
        """return changed-in key"""
        return "%s-in %d.%d.%d" % tuple([change] + list(version))

    def test_duplicate_changed(self):
        all_changed = []
        for change in ("new", "removed"):
            d = getattr(constant_names, change + "_in")
            for version, namelist in d.items():
                all_changed.extend(namelist)
                self._duplicate_test(namelist, self._change_key(change, version))
        
        self._duplicate_test(all_changed, "all-changed")
    
    def test_changed_in_all(self):
        missing = {}
        for change in ("new", "removed"):
            d = getattr(constant_names, change + "_in")
            for version, namelist in d.items():
                key = self._change_key(change, version)
                for name in namelist:
                    if name not in all_set:
                        if key not in missing:
                            missing[key] = []
                        missing[key].append(name)
        
        if missing:
            self.fail(
                "The following names are missing in `all_names`: %s" % json.dumps(missing, indent=2)
            )
    
    def test_no_negative_constants(self):
        for name in sugar_constants.__all__:
            self.assertNotEqual(getattr(zmq, name), -1)
    
    def test_undefined_constants(self):
        all_aliases = []
        for alias_group in sugar_constants.aliases:
            all_aliases.extend(alias_group)
        
        for name in all_set.difference(all_aliases):
            raw = getattr(backend_constants, name)
            if raw == -1:
                self.assertRaises(AttributeError, getattr, zmq, name)
            else:
                self.assertEqual(getattr(zmq, name), raw)
    
    def test_new(self):
        zmq_version = zmq.zmq_version_info()
        for version, new_names in constant_names.new_in.items():
            should_have = zmq_version >= version
            for name in new_names:
                try:
                    value = getattr(zmq, name)
                except AttributeError:
                    if should_have:
                        self.fail("AttributeError: zmq.%s" % name)
                else:
                    if not should_have:
                        self.fail("Shouldn't have: zmq.%s=%s" % (name, value))

    def test_removed(self):
        zmq_version = zmq.zmq_version_info()
        for version, new_names in constant_names.removed_in.items():
            should_have = zmq_version < version
            for name in new_names:
                try:
                    value = getattr(zmq, name)
                except AttributeError:
                    if should_have:
                        self.fail("AttributeError: zmq.%s" % name)
                else:
                    if not should_have:
                        self.fail("Shouldn't have: zmq.%s=%s" % (name, value))


########NEW FILE########
__FILENAME__ = test_context
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import gc
import sys
import time
from threading import Thread, Event

import zmq
from zmq.tests import (
    BaseZMQTestCase, have_gevent, GreenTest, skip_green, PYPY, SkipTest,
)


#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------


class TestContext(BaseZMQTestCase):

    def test_init(self):
        c1 = self.Context()
        self.assert_(isinstance(c1, self.Context))
        del c1
        c2 = self.Context()
        self.assert_(isinstance(c2, self.Context))
        del c2
        c3 = self.Context()
        self.assert_(isinstance(c3, self.Context))
        del c3

    def test_dir(self):
        ctx = self.Context()
        self.assertTrue('socket' in dir(ctx))
        if zmq.zmq_version_info() > (3,):
            self.assertTrue('IO_THREADS' in dir(ctx))
        ctx.term()

    def test_term(self):
        c = self.Context()
        c.term()
        self.assert_(c.closed)
    
    def test_context_manager(self):
        with self.Context() as c:
            pass
        self.assert_(c.closed)
    
    def test_fail_init(self):
        self.assertRaisesErrno(zmq.EINVAL, self.Context, -1)
    
    def test_term_hang(self):
        rep,req = self.create_bound_pair(zmq.ROUTER, zmq.DEALER)
        req.setsockopt(zmq.LINGER, 0)
        req.send(b'hello', copy=False)
        req.close()
        rep.close()
        self.context.term()
    
    def test_instance(self):
        ctx = self.Context.instance()
        c2 = self.Context.instance(io_threads=2)
        self.assertTrue(c2 is ctx)
        c2.term()
        c3 = self.Context.instance()
        c4 = self.Context.instance()
        self.assertFalse(c3 is c2)
        self.assertFalse(c3.closed)
        self.assertTrue(c3 is c4)
    
    def test_many_sockets(self):
        """opening and closing many sockets shouldn't cause problems"""
        ctx = self.Context()
        for i in range(16):
            sockets = [ ctx.socket(zmq.REP) for i in range(65) ]
            [ s.close() for s in sockets ]
            # give the reaper a chance
            time.sleep(1e-2)
        ctx.term()
    
    def test_sockopts(self):
        """setting socket options with ctx attributes"""
        ctx = self.Context()
        ctx.linger = 5
        self.assertEqual(ctx.linger, 5)
        s = ctx.socket(zmq.REQ)
        self.assertEqual(s.linger, 5)
        self.assertEqual(s.getsockopt(zmq.LINGER), 5)
        s.close()
        # check that subscribe doesn't get set on sockets that don't subscribe:
        ctx.subscribe = b''
        s = ctx.socket(zmq.REQ)
        s.close()
        
        ctx.term()

    
    def test_destroy(self):
        """Context.destroy should close sockets"""
        ctx = self.Context()
        sockets = [ ctx.socket(zmq.REP) for i in range(65) ]
        
        # close half of the sockets
        [ s.close() for s in sockets[::2] ]
        
        ctx.destroy()
        # reaper is not instantaneous
        time.sleep(1e-2)
        for s in sockets:
            self.assertTrue(s.closed)
        
    def test_destroy_linger(self):
        """Context.destroy should set linger on closing sockets"""
        req,rep = self.create_bound_pair(zmq.REQ, zmq.REP)
        req.send(b'hi')
        time.sleep(1e-2)
        self.context.destroy(linger=0)
        # reaper is not instantaneous
        time.sleep(1e-2)
        for s in (req,rep):
            self.assertTrue(s.closed)
        
    def test_term_noclose(self):
        """Context.term won't close sockets"""
        ctx = self.Context()
        s = ctx.socket(zmq.REQ)
        self.assertFalse(s.closed)
        t = Thread(target=ctx.term)
        t.start()
        t.join(timeout=0.1)
        self.assertTrue(t.is_alive(), "Context should be waiting")
        s.close()
        t.join(timeout=0.1)
        self.assertFalse(t.is_alive(), "Context should have closed")
    
    def test_gc(self):
        """test close&term by garbage collection alone"""
        if PYPY:
            raise SkipTest("GC doesn't work ")
            
        # test credit @dln (GH #137):
        def gcf():
            def inner():
                ctx = self.Context()
                s = ctx.socket(zmq.PUSH)
            inner()
            gc.collect()
        t = Thread(target=gcf)
        t.start()
        t.join(timeout=1)
        self.assertFalse(t.is_alive(), "Garbage collection should have cleaned up context")
    
    def test_cyclic_destroy(self):
        """ctx.destroy should succeed when cyclic ref prevents gc"""
        # test credit @dln (GH #137):
        class CyclicReference(object):
            def __init__(self, parent=None):
                self.parent = parent
            
            def crash(self, sock):
                self.sock = sock
                self.child = CyclicReference(self)
        
        def crash_zmq():
            ctx = self.Context()
            sock = ctx.socket(zmq.PULL)
            c = CyclicReference()
            c.crash(sock)
            ctx.destroy()
        
        crash_zmq()
    
    def test_term_thread(self):
        """ctx.term should not crash active threads (#139)"""
        ctx = self.Context()
        evt = Event()
        evt.clear()

        def block():
            s = ctx.socket(zmq.REP)
            s.bind_to_random_port('tcp://127.0.0.1')
            evt.set()
            try:
                s.recv()
            except zmq.ZMQError as e:
                self.assertEqual(e.errno, zmq.ETERM)
                return
            finally:
                s.close()
            self.fail("recv should have been interrupted with ETERM")
        t = Thread(target=block)
        t.start()
        
        evt.wait(1)
        self.assertTrue(evt.is_set(), "sync event never fired")
        time.sleep(0.01)
        ctx.term()
        t.join(timeout=1)
        self.assertFalse(t.is_alive(), "term should have interrupted s.recv()")
    
    def test_destroy_no_sockets(self):
        ctx = self.Context()
        s = ctx.socket(zmq.PUB)
        s.bind_to_random_port('tcp://127.0.0.1')
        s.close()
        ctx.destroy()
        assert s.closed
        assert ctx.closed
    
    def test_ctx_opts(self):
        if zmq.zmq_version_info() < (3,):
            raise SkipTest("context options require libzmq 3")
        ctx = self.Context()
        ctx.set(zmq.MAX_SOCKETS, 2)
        self.assertEqual(ctx.get(zmq.MAX_SOCKETS), 2)
        ctx.max_sockets = 100
        self.assertEqual(ctx.max_sockets, 100)
        self.assertEqual(ctx.get(zmq.MAX_SOCKETS), 100)
    
    def test_shadow(self):
        ctx = self.Context()
        ctx2 = self.Context.shadow(ctx.underlying)
        self.assertEqual(ctx.underlying, ctx2.underlying)
        s = ctx.socket(zmq.PUB)
        s.close()
        del ctx2
        self.assertFalse(ctx.closed)
        s = ctx.socket(zmq.PUB)
        ctx2 = self.Context.shadow(ctx.underlying)
        s2 = ctx2.socket(zmq.PUB)
        s.close()
        s2.close()
        ctx.term()
        self.assertRaisesErrno(zmq.EFAULT, ctx2.socket, zmq.PUB)
        del ctx2
    
    def test_shadow_pyczmq(self):
        try:
            from pyczmq import zctx, zsocket, zstr
        except Exception:
            raise SkipTest("Requires pyczmq")
        
        ctx = zctx.new()
        a = zsocket.new(ctx, zmq.PUSH)
        zsocket.bind(a, "inproc://a")
        ctx2 = self.Context.shadow_pyczmq(ctx)
        b = ctx2.socket(zmq.PULL)
        b.connect("inproc://a")
        zstr.send(a, b'hi')
        rcvd = self.recv(b)
        self.assertEqual(rcvd, b'hi')
        b.close()


if False: # disable green context tests
    class TestContextGreen(GreenTest, TestContext):
        """gevent subclass of context tests"""
        # skip tests that use real threads:
        test_gc = GreenTest.skip_green
        test_term_thread = GreenTest.skip_green
        test_destroy_linger = GreenTest.skip_green

########NEW FILE########
__FILENAME__ = test_device
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import time

import zmq
from zmq import devices
from zmq.tests import BaseZMQTestCase, SkipTest, have_gevent, GreenTest, PYPY
from zmq.utils.strtypes import (bytes,unicode,basestring)

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------
if PYPY:
    # cleanup of shared Context doesn't work on PyPy
    devices.Device.context_factory = zmq.Context

class TestDevice(BaseZMQTestCase):
    
    def test_device_types(self):
        for devtype in (zmq.STREAMER, zmq.FORWARDER, zmq.QUEUE):
            dev = devices.Device(devtype, zmq.PAIR, zmq.PAIR)
            self.assertEqual(dev.device_type, devtype)
            del dev
    
    def test_device_attributes(self):
        dev = devices.Device(zmq.QUEUE, zmq.SUB, zmq.PUB)
        self.assertEqual(dev.in_type, zmq.SUB)
        self.assertEqual(dev.out_type, zmq.PUB)
        self.assertEqual(dev.device_type, zmq.QUEUE)
        self.assertEqual(dev.daemon, True)
        del dev
    
    def test_tsdevice_attributes(self):
        dev = devices.Device(zmq.QUEUE, zmq.SUB, zmq.PUB)
        self.assertEqual(dev.in_type, zmq.SUB)
        self.assertEqual(dev.out_type, zmq.PUB)
        self.assertEqual(dev.device_type, zmq.QUEUE)
        self.assertEqual(dev.daemon, True)
        del dev
        
    
    def test_single_socket_forwarder_connect(self):
        dev = devices.ThreadDevice(zmq.QUEUE, zmq.REP, -1)
        req = self.context.socket(zmq.REQ)
        port = req.bind_to_random_port('tcp://127.0.0.1')
        dev.connect_in('tcp://127.0.0.1:%i'%port)
        dev.start()
        time.sleep(.25)
        msg = b'hello'
        req.send(msg)
        self.assertEqual(msg, self.recv(req))
        del dev
        req.close()
        dev = devices.ThreadDevice(zmq.QUEUE, zmq.REP, -1)
        req = self.context.socket(zmq.REQ)
        port = req.bind_to_random_port('tcp://127.0.0.1')
        dev.connect_out('tcp://127.0.0.1:%i'%port)
        dev.start()
        time.sleep(.25)
        msg = b'hello again'
        req.send(msg)
        self.assertEqual(msg, self.recv(req))
        del dev
        req.close()
        
    def test_single_socket_forwarder_bind(self):
        dev = devices.ThreadDevice(zmq.QUEUE, zmq.REP, -1)
        # select random port:
        binder = self.context.socket(zmq.REQ)
        port = binder.bind_to_random_port('tcp://127.0.0.1')
        binder.close()
        time.sleep(0.1)
        req = self.context.socket(zmq.REQ)
        req.connect('tcp://127.0.0.1:%i'%port)
        dev.bind_in('tcp://127.0.0.1:%i'%port)
        dev.start()
        time.sleep(.25)
        msg = b'hello'
        req.send(msg)
        self.assertEqual(msg, self.recv(req))
        del dev
        req.close()
        dev = devices.ThreadDevice(zmq.QUEUE, zmq.REP, -1)
        # select random port:
        binder = self.context.socket(zmq.REQ)
        port = binder.bind_to_random_port('tcp://127.0.0.1')
        binder.close()
        time.sleep(0.1)
        req = self.context.socket(zmq.REQ)
        req.connect('tcp://127.0.0.1:%i'%port)
        dev.bind_in('tcp://127.0.0.1:%i'%port)
        dev.start()
        time.sleep(.25)
        msg = b'hello again'
        req.send(msg)
        self.assertEqual(msg, self.recv(req))
        del dev
        req.close()
    
    def test_proxy(self):
        if zmq.zmq_version_info() < (3,2):
            raise SkipTest("Proxies only in libzmq >= 3")
        dev = devices.ThreadProxy(zmq.PULL, zmq.PUSH, zmq.PUSH)
        binder = self.context.socket(zmq.REQ)
        iface = 'tcp://127.0.0.1'
        port = binder.bind_to_random_port(iface)
        port2 = binder.bind_to_random_port(iface)
        port3 = binder.bind_to_random_port(iface)
        binder.close()
        time.sleep(0.1)
        dev.bind_in("%s:%i" % (iface, port))
        dev.bind_out("%s:%i" % (iface, port2))
        dev.bind_mon("%s:%i" % (iface, port3))
        dev.start()
        time.sleep(0.25)
        msg = b'hello'
        push = self.context.socket(zmq.PUSH)
        push.connect("%s:%i" % (iface, port))
        pull = self.context.socket(zmq.PULL)
        pull.connect("%s:%i" % (iface, port2))
        mon = self.context.socket(zmq.PULL)
        mon.connect("%s:%i" % (iface, port3))
        push.send(msg)
        self.sockets.extend([push, pull, mon])
        self.assertEqual(msg, self.recv(pull))
        self.assertEqual(msg, self.recv(mon))

if have_gevent:
    import gevent
    import zmq.green
    
    class TestDeviceGreen(GreenTest, BaseZMQTestCase):
        
        def test_green_device(self):
            rep = self.context.socket(zmq.REP)
            req = self.context.socket(zmq.REQ)
            self.sockets.extend([req, rep])
            port = rep.bind_to_random_port('tcp://127.0.0.1')
            g = gevent.spawn(zmq.green.device, zmq.QUEUE, rep, rep)
            req.connect('tcp://127.0.0.1:%i' % port)
            req.send(b'hi')
            timeout = gevent.Timeout(3)
            timeout.start()
            receiver = gevent.spawn(req.recv)
            self.assertEqual(receiver.get(2), b'hi')
            timeout.cancel()
            g.kill(block=True)
            

########NEW FILE########
__FILENAME__ = test_error
# -*- coding: utf8 -*-
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
import time

import zmq
from zmq import ZMQError, strerror, Again, ContextTerminated
from zmq.tests import BaseZMQTestCase

if sys.version_info[0] >= 3:
    long = int

class TestZMQError(BaseZMQTestCase):
    
    def test_strerror(self):
        """test that strerror gets the right type."""
        for i in range(10):
            e = strerror(i)
            self.assertTrue(isinstance(e, str))
    
    def test_zmqerror(self):
        for errno in range(10):
            e = ZMQError(errno)
            self.assertEqual(e.errno, errno)
            self.assertEqual(str(e), strerror(errno))
    
    def test_again(self):
        s = self.context.socket(zmq.REP)
        self.assertRaises(Again, s.recv, zmq.NOBLOCK)
        self.assertRaisesErrno(zmq.EAGAIN, s.recv, zmq.NOBLOCK)
        s.close()
    
    def atest_ctxterm(self):
        s = self.context.socket(zmq.REP)
        t = Thread(target=self.context.term)
        t.start()
        self.assertRaises(ContextTerminated, s.recv, zmq.NOBLOCK)
        self.assertRaisesErrno(zmq.TERM, s.recv, zmq.NOBLOCK)
        s.close()
        t.join()


########NEW FILE########
__FILENAME__ = test_imports
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
from unittest import TestCase

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestImports(TestCase):
    """Test Imports - the quickest test to ensure that we haven't
    introduced version-incompatible syntax errors."""
    
    def test_toplevel(self):
        """test toplevel import"""
        import zmq
        
    def test_core(self):
        """test core imports"""
        from zmq import Context
        from zmq import Socket
        from zmq import Poller
        from zmq import Frame
        from zmq import constants
        from zmq import device, proxy
        from zmq import Stopwatch
        from zmq import ( 
            zmq_version,
            zmq_version_info,
            pyzmq_version,
            pyzmq_version_info,
        )
    
    def test_devices(self):
        """test device imports"""
        import zmq.devices
        from zmq.devices import basedevice
        from zmq.devices import monitoredqueue
        from zmq.devices import monitoredqueuedevice
    
    def test_log(self):
        """test log imports"""
        import zmq.log
        from zmq.log import handlers
    
    def test_eventloop(self):
        """test eventloop imports"""
        import zmq.eventloop
        from zmq.eventloop import ioloop
        from zmq.eventloop import zmqstream
        from zmq.eventloop.minitornado.platform import auto
        from zmq.eventloop.minitornado import ioloop
    
    def test_utils(self):
        """test util imports"""
        import zmq.utils
        from zmq.utils import strtypes
        from zmq.utils import jsonapi
    




########NEW FILE########
__FILENAME__ = test_ioloop
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import time
import os
import threading

import zmq
from zmq.tests import BaseZMQTestCase
from zmq.eventloop import ioloop
from zmq.eventloop.minitornado.ioloop import _Timeout
try:
    from tornado.ioloop import PollIOLoop, IOLoop as BaseIOLoop
except ImportError:
    from zmq.eventloop.minitornado.ioloop import IOLoop as BaseIOLoop


#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------
def printer():
    os.system("say hello")
    raise Exception
    print (time.time())

class Delay(threading.Thread):
    def __init__(self, f, delay=1):
        self.f=f
        self.delay=delay
        self.aborted=False
        self.cond=threading.Condition()
        super(Delay, self).__init__()
    
    def run(self):
        self.cond.acquire()
        self.cond.wait(self.delay)
        self.cond.release()
        if not self.aborted:
            self.f()
    
    def abort(self):
        self.aborted=True
        self.cond.acquire()
        self.cond.notify()
        self.cond.release()

class TestIOLoop(BaseZMQTestCase):

    def test_simple(self):
        """simple IOLoop creation test"""
        loop = ioloop.IOLoop()
        dc = ioloop.PeriodicCallback(loop.stop, 200, loop)
        pc = ioloop.PeriodicCallback(lambda : None, 10, loop)
        pc.start()
        dc.start()
        t = Delay(loop.stop,1)
        t.start()
        loop.start()
        if t.isAlive():
            t.abort()
        else:
            self.fail("IOLoop failed to exit")
    
    def test_timeout_compare(self):
        """test timeout comparisons"""
        loop = ioloop.IOLoop()
        t = _Timeout(1, 2, loop)
        t2 = _Timeout(1, 3, loop)
        self.assertEqual(t < t2, id(t) < id(t2))
        t2 = _Timeout(2,1, loop)
        self.assertTrue(t < t2)

    def test_poller_events(self):
        """Tornado poller implementation maps events correctly"""
        req,rep = self.create_bound_pair(zmq.REQ, zmq.REP)
        poller = ioloop.ZMQPoller()
        poller.register(req, ioloop.IOLoop.READ)
        poller.register(rep, ioloop.IOLoop.READ)
        events = dict(poller.poll(0))
        self.assertEqual(events.get(rep), None)
        self.assertEqual(events.get(req), None)
        
        poller.register(req, ioloop.IOLoop.WRITE)
        poller.register(rep, ioloop.IOLoop.WRITE)
        events = dict(poller.poll(1))
        self.assertEqual(events.get(req), ioloop.IOLoop.WRITE)
        self.assertEqual(events.get(rep), None)
        
        poller.register(rep, ioloop.IOLoop.READ)
        req.send(b'hi')
        events = dict(poller.poll(1))
        self.assertEqual(events.get(rep), ioloop.IOLoop.READ)
        self.assertEqual(events.get(req), None)
    
    def test_instance(self):
        """Test IOLoop.instance returns the right object"""
        loop = ioloop.IOLoop.instance()
        self.assertEqual(loop.__class__, ioloop.IOLoop)
        loop = BaseIOLoop.instance()
        self.assertEqual(loop.__class__, ioloop.IOLoop)
    
    def test_close_all(self):
        """Test close(all_fds=True)"""
        loop = ioloop.IOLoop.instance()
        req,rep = self.create_bound_pair(zmq.REQ, zmq.REP)
        loop.add_handler(req, lambda msg: msg, ioloop.IOLoop.READ)
        loop.add_handler(rep, lambda msg: msg, ioloop.IOLoop.READ)
        self.assertEqual(req.closed, False)
        self.assertEqual(rep.closed, False)
        loop.close(all_fds=True)
        self.assertEqual(req.closed, True)
        self.assertEqual(rep.closed, True)
        


########NEW FILE########
__FILENAME__ = test_log
# encoding: utf-8
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import logging
import time
from unittest import TestCase

import zmq
from zmq.log import handlers
from zmq.utils.strtypes import b, u
from zmq.tests import BaseZMQTestCase

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestPubLog(BaseZMQTestCase):
    
    iface = 'inproc://zmqlog'
    topic= 'zmq'
    
    @property
    def logger(self):
        # print dir(self)
        logger = logging.getLogger('zmqtest')
        logger.setLevel(logging.DEBUG)
        return logger
    
    def connect_handler(self, topic=None):
        topic = self.topic if topic is None else topic
        logger = self.logger
        pub,sub = self.create_bound_pair(zmq.PUB, zmq.SUB)
        handler = handlers.PUBHandler(pub)
        handler.setLevel(logging.DEBUG)
        handler.root_topic = topic
        logger.addHandler(handler)
        sub.setsockopt(zmq.SUBSCRIBE, b(topic))
        time.sleep(0.1)
        return logger, handler, sub
    
    def test_init_iface(self):
        logger = self.logger
        ctx = self.context
        handler = handlers.PUBHandler(self.iface)
        self.assertFalse(handler.ctx is ctx)
        self.sockets.append(handler.socket)
        # handler.ctx.term()
        handler = handlers.PUBHandler(self.iface, self.context)
        self.sockets.append(handler.socket)
        self.assertTrue(handler.ctx is ctx)
        handler.setLevel(logging.DEBUG)
        handler.root_topic = self.topic
        logger.addHandler(handler)
        sub = ctx.socket(zmq.SUB)
        self.sockets.append(sub)
        sub.setsockopt(zmq.SUBSCRIBE, b(self.topic))
        sub.connect(self.iface)
        import time; time.sleep(0.25)
        msg1 = 'message'
        logger.info(msg1)
        
        (topic, msg2) = sub.recv_multipart()
        self.assertEqual(topic, b'zmq.INFO')
        self.assertEqual(msg2, b(msg1)+b'\n')
        logger.removeHandler(handler)
    
    def test_init_socket(self):
        pub,sub = self.create_bound_pair(zmq.PUB, zmq.SUB)
        logger = self.logger
        handler = handlers.PUBHandler(pub)
        handler.setLevel(logging.DEBUG)
        handler.root_topic = self.topic
        logger.addHandler(handler)
        
        self.assertTrue(handler.socket is pub)
        self.assertTrue(handler.ctx is pub.context)
        self.assertTrue(handler.ctx is self.context)
        sub.setsockopt(zmq.SUBSCRIBE, b(self.topic))
        import time; time.sleep(0.1)
        msg1 = 'message'
        logger.info(msg1)
        
        (topic, msg2) = sub.recv_multipart()
        self.assertEqual(topic, b'zmq.INFO')
        self.assertEqual(msg2, b(msg1)+b'\n')
        logger.removeHandler(handler)
    
    def test_root_topic(self):
        logger, handler, sub = self.connect_handler()
        handler.socket.bind(self.iface)
        sub2 = sub.context.socket(zmq.SUB)
        self.sockets.append(sub2)
        sub2.connect(self.iface)
        sub2.setsockopt(zmq.SUBSCRIBE, b'')
        handler.root_topic = b'twoonly'
        msg1 = 'ignored'
        logger.info(msg1)
        self.assertRaisesErrno(zmq.EAGAIN, sub.recv, zmq.NOBLOCK)
        topic,msg2 = sub2.recv_multipart()
        self.assertEqual(topic, b'twoonly.INFO')
        self.assertEqual(msg2, b(msg1)+b'\n')
        
        logger.removeHandler(handler)
    
    def test_unicode_message(self):
        logger, handler, sub = self.connect_handler()
        base_topic = b(self.topic + '.INFO')
        for msg, expected in [
            (u('hello'), [base_topic, b('hello\n')]),
            (u('héllo'), [base_topic, b('héllo\n')]),
            (u('tøpic::héllo'), [base_topic + b('.tøpic'), b('héllo\n')]),
        ]:
            logger.info(msg)
            received = sub.recv_multipart()
            self.assertEqual(received, expected)


########NEW FILE########
__FILENAME__ = test_message
# -*- coding: utf8 -*-
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import copy
import sys
try:
    from sys import getrefcount as grc
except ImportError:
    grc = None

import time
from pprint import pprint
from unittest import TestCase

import zmq
from zmq.tests import BaseZMQTestCase, SkipTest, skip_pypy, PYPY
from zmq.utils.strtypes import unicode, bytes, b, u

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

# some useful constants:

x = b'x'

try:
    view = memoryview
except NameError:
    view = buffer

if grc:
    rc0 = grc(x)
    v = view(x)
    view_rc = grc(x) - rc0

def await_gc(obj, rc):
    """wait for refcount on an object to drop to an expected value
    
    Necessary because of the zero-copy gc thread,
    which can take some time to receive its DECREF message.
    """
    for i in range(50):
        # rc + 2 because of the refs in this function
        if grc(obj) <= rc + 2:
            return
        time.sleep(0.05)
    
class TestFrame(BaseZMQTestCase):

    @skip_pypy
    def test_above_30(self):
        """Message above 30 bytes are never copied by 0MQ."""
        for i in range(5, 16):  # 32, 64,..., 65536
            s = (2**i)*x
            self.assertEqual(grc(s), 2)
            m = zmq.Frame(s)
            self.assertEqual(grc(s), 4)
            del m
            await_gc(s, 2)
            self.assertEqual(grc(s), 2)
            del s

    def test_str(self):
        """Test the str representations of the Frames."""
        for i in range(16):
            s = (2**i)*x
            m = zmq.Frame(s)
            m_str = str(m)
            m_str_b = b(m_str) # py3compat
            self.assertEqual(s, m_str_b)

    def test_bytes(self):
        """Test the Frame.bytes property."""
        for i in range(1,16):
            s = (2**i)*x
            m = zmq.Frame(s)
            b = m.bytes
            self.assertEqual(s, m.bytes)
            if not PYPY:
                # check that it copies
                self.assert_(b is not s)
            # check that it copies only once
            self.assert_(b is m.bytes)

    def test_unicode(self):
        """Test the unicode representations of the Frames."""
        s = u('asdf')
        self.assertRaises(TypeError, zmq.Frame, s)
        for i in range(16):
            s = (2**i)*u('§')
            m = zmq.Frame(s.encode('utf8'))
            self.assertEqual(s, unicode(m.bytes,'utf8'))

    def test_len(self):
        """Test the len of the Frames."""
        for i in range(16):
            s = (2**i)*x
            m = zmq.Frame(s)
            self.assertEqual(len(s), len(m))

    @skip_pypy
    def test_lifecycle1(self):
        """Run through a ref counting cycle with a copy."""
        for i in range(5, 16):  # 32, 64,..., 65536
            s = (2**i)*x
            rc = 2
            self.assertEqual(grc(s), rc)
            m = zmq.Frame(s)
            rc += 2
            self.assertEqual(grc(s), rc)
            m2 = copy.copy(m)
            rc += 1
            self.assertEqual(grc(s), rc)
            buf = m2.buffer

            rc += view_rc
            self.assertEqual(grc(s), rc)

            self.assertEqual(s, b(str(m)))
            self.assertEqual(s, bytes(m2))
            self.assertEqual(s, m.bytes)
            # self.assert_(s is str(m))
            # self.assert_(s is str(m2))
            del m2
            rc -= 1
            self.assertEqual(grc(s), rc)
            rc -= view_rc
            del buf
            self.assertEqual(grc(s), rc)
            del m
            rc -= 2
            await_gc(s, rc)
            self.assertEqual(grc(s), rc)
            self.assertEqual(rc, 2)
            del s

    @skip_pypy
    def test_lifecycle2(self):
        """Run through a different ref counting cycle with a copy."""
        for i in range(5, 16):  # 32, 64,..., 65536
            s = (2**i)*x
            rc = 2
            self.assertEqual(grc(s), rc)
            m = zmq.Frame(s)
            rc += 2
            self.assertEqual(grc(s), rc)
            m2 = copy.copy(m)
            rc += 1
            self.assertEqual(grc(s), rc)
            buf = m.buffer
            rc += view_rc
            self.assertEqual(grc(s), rc)
            self.assertEqual(s, b(str(m)))
            self.assertEqual(s, bytes(m2))
            self.assertEqual(s, m2.bytes)
            self.assertEqual(s, m.bytes)
            # self.assert_(s is str(m))
            # self.assert_(s is str(m2))
            del buf
            self.assertEqual(grc(s), rc)
            del m
            # m.buffer is kept until m is del'd
            rc -= view_rc
            rc -= 1
            self.assertEqual(grc(s), rc)
            del m2
            rc -= 2
            await_gc(s, rc)
            self.assertEqual(grc(s), rc)
            self.assertEqual(rc, 2)
            del s
    
    @skip_pypy
    def test_tracker(self):
        m = zmq.Frame(b'asdf', track=True)
        self.assertFalse(m.tracker.done)
        pm = zmq.MessageTracker(m)
        self.assertFalse(pm.done)
        del m
        for i in range(10):
            if pm.done:
                break
            time.sleep(0.1)
        self.assertTrue(pm.done)
    
    def test_no_tracker(self):
        m = zmq.Frame(b'asdf', track=False)
        self.assertEqual(m.tracker, None)
        m2 = copy.copy(m)
        self.assertEqual(m2.tracker, None)
        self.assertRaises(ValueError, zmq.MessageTracker, m)
    
    @skip_pypy
    def test_multi_tracker(self):
        m = zmq.Frame(b'asdf', track=True)
        m2 = zmq.Frame(b'whoda', track=True)
        mt = zmq.MessageTracker(m,m2)
        self.assertFalse(m.tracker.done)
        self.assertFalse(mt.done)
        self.assertRaises(zmq.NotDone, mt.wait, 0.1)
        del m
        time.sleep(0.1)
        self.assertRaises(zmq.NotDone, mt.wait, 0.1)
        self.assertFalse(mt.done)
        del m2
        self.assertTrue(mt.wait() is None)
        self.assertTrue(mt.done)
        
    
    def test_buffer_in(self):
        """test using a buffer as input"""
        ins = b("§§¶•ªº˜µ¬˚…∆˙åß∂©œ∑´†≈ç√")
        m = zmq.Frame(view(ins))
    
    def test_bad_buffer_in(self):
        """test using a bad object"""
        self.assertRaises(TypeError, zmq.Frame, 5)
        self.assertRaises(TypeError, zmq.Frame, object())
        
    def test_buffer_out(self):
        """receiving buffered output"""
        ins = b("§§¶•ªº˜µ¬˚…∆˙åß∂©œ∑´†≈ç√")
        m = zmq.Frame(ins)
        outb = m.buffer
        self.assertTrue(isinstance(outb, view))
        self.assert_(outb is m.buffer)
        self.assert_(m.buffer is m.buffer)
    
    def test_multisend(self):
        """ensure that a message remains intact after multiple sends"""
        a,b = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        s = b"message"
        m = zmq.Frame(s)
        self.assertEqual(s, m.bytes)
        
        a.send(m, copy=False)
        time.sleep(0.1)
        self.assertEqual(s, m.bytes)
        a.send(m, copy=False)
        time.sleep(0.1)
        self.assertEqual(s, m.bytes)
        a.send(m, copy=True)
        time.sleep(0.1)
        self.assertEqual(s, m.bytes)
        a.send(m, copy=True)
        time.sleep(0.1)
        self.assertEqual(s, m.bytes)
        for i in range(4):
            r = b.recv()
            self.assertEqual(s,r)
        self.assertEqual(s, m.bytes)
    
    def test_buffer_numpy(self):
        """test non-copying numpy array messages"""
        try:
            import numpy
        except ImportError:
            raise SkipTest("numpy required")
        rand = numpy.random.randint
        shapes = [ rand(2,16) for i in range(5) ]
        for i in range(1,len(shapes)+1):
            shape = shapes[:i]
            A = numpy.random.random(shape)
            m = zmq.Frame(A)
            if view.__name__ == 'buffer':
                self.assertEqual(A.data, m.buffer)
                B = numpy.frombuffer(m.buffer,dtype=A.dtype).reshape(A.shape)
            else:
                self.assertEqual(memoryview(A), m.buffer)
                B = numpy.array(m.buffer,dtype=A.dtype).reshape(A.shape)
            self.assertEqual((A==B).all(), True)
    
    def test_memoryview(self):
        """test messages from memoryview"""
        major,minor = sys.version_info[:2]
        if not (major >= 3 or (major == 2 and minor >= 7)):
            raise SkipTest("memoryviews only in python >= 2.7")

        s = b'carrotjuice'
        v = memoryview(s)
        m = zmq.Frame(s)
        buf = m.buffer
        s2 = buf.tobytes()
        self.assertEqual(s2,s)
        self.assertEqual(m.bytes,s)
    
    def test_noncopying_recv(self):
        """check for clobbering message buffers"""
        null = b'\0'*64
        sa,sb = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        for i in range(32):
            # try a few times
            sb.send(null, copy=False)
            m = sa.recv(copy=False)
            mb = m.bytes
            # buf = view(m)
            buf = m.buffer
            del m
            for i in range(5):
                ff=b'\xff'*(40 + i*10)
                sb.send(ff, copy=False)
                m2 = sa.recv(copy=False)
                if view.__name__ == 'buffer':
                    b = bytes(buf)
                else:
                    b = buf.tobytes()
                self.assertEqual(b, null)
                self.assertEqual(mb, null)
                self.assertEqual(m2.bytes, ff)

    @skip_pypy
    def test_buffer_numpy(self):
        """test non-copying numpy array messages"""
        try:
            import numpy
        except ImportError:
            raise SkipTest("requires numpy")
        if sys.version_info < (2,7):
            raise SkipTest("requires new-style buffer interface (py >= 2.7)")
        rand = numpy.random.randint
        shapes = [ rand(2,5) for i in range(5) ]
        a,b = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        dtypes = [int, float, '>i4', 'B']
        for i in range(1,len(shapes)+1):
            shape = shapes[:i]
            for dt in dtypes:
                A = numpy.empty(shape, dtype=dt)
                while numpy.isnan(A).any():
                    # don't let nan sneak in
                    A = numpy.ndarray(shape, dtype=dt)
                a.send(A, copy=False)
                msg = b.recv(copy=False)
                
                B = numpy.frombuffer(msg, A.dtype).reshape(A.shape)
                self.assertEqual(A.shape, B.shape)
                self.assertTrue((A==B).all())
            A = numpy.empty(shape, dtype=[('a', int), ('b', float), ('c', 'a32')])
            A['a'] = 1024
            A['b'] = 1e9
            A['c'] = 'hello there'
            a.send(A, copy=False)
            msg = b.recv(copy=False)
            
            B = numpy.frombuffer(msg, A.dtype).reshape(A.shape)
            self.assertEqual(A.shape, B.shape)
            self.assertTrue((A==B).all())
    
    def test_frame_more(self):
        """test Frame.more attribute"""
        frame = zmq.Frame(b"hello")
        self.assertFalse(frame.more)
        sa,sb = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        sa.send_multipart([b'hi', b'there'])
        frame = self.recv(sb, copy=False)
        self.assertTrue(frame.more)
        if zmq.zmq_version_info()[0] >= 3 and not PYPY:
            self.assertTrue(frame.get(zmq.MORE))
        frame = self.recv(sb, copy=False)
        self.assertFalse(frame.more)
        if zmq.zmq_version_info()[0] >= 3 and not PYPY:
            self.assertFalse(frame.get(zmq.MORE))


########NEW FILE########
__FILENAME__ = test_monitor
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Guido Goldstein, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
import time
import struct

from unittest import TestCase

import zmq
from zmq.tests import BaseZMQTestCase, skip_if, skip_pypy
from zmq.utils.monitor import recv_monitor_message

skip_lt_4 = skip_if(zmq.zmq_version_info() < (4,), "requires zmq >= 4")

class TestSocketMonitor(BaseZMQTestCase):

    @skip_lt_4
    def test_monitor(self):
        """Test monitoring interface for sockets."""
        s_rep = self.context.socket(zmq.REP)
        s_req = self.context.socket(zmq.REQ)
        self.sockets.extend([s_rep, s_req])
        s_req.bind("tcp://127.0.0.1:6666")
        # try monitoring the REP socket
        
        s_rep.monitor("inproc://monitor.rep", zmq.EVENT_ALL)
        # create listening socket for monitor
        s_event = self.context.socket(zmq.PAIR)
        self.sockets.append(s_event)
        s_event.connect("inproc://monitor.rep")
        s_event.linger = 0
        # test receive event for connect event
        s_rep.connect("tcp://127.0.0.1:6666")
        m = recv_monitor_message(s_event)
        self.assertEqual(m['event'], zmq.EVENT_CONNECT_DELAYED)
        self.assertEqual(m['endpoint'], b"tcp://127.0.0.1:6666")
        # test receive event for connected event
        m = recv_monitor_message(s_event)
        self.assertEqual(m['event'], zmq.EVENT_CONNECTED)

    @skip_lt_4
    def test_monitor_connected(self):
        """Test connected monitoring socket."""
        s_rep = self.context.socket(zmq.REP)
        s_req = self.context.socket(zmq.REQ)
        self.sockets.extend([s_rep, s_req])
        s_req.bind("tcp://127.0.0.1:6667")
        # try monitoring the REP socket
        # create listening socket for monitor
        s_event = s_rep.get_monitor_socket()
        s_event.linger = 0
        self.sockets.append(s_event)
        # test receive event for connect event
        s_rep.connect("tcp://127.0.0.1:6667")
        m = recv_monitor_message(s_event)
        self.assertEqual(m['event'], zmq.EVENT_CONNECT_DELAYED)
        self.assertEqual(m['endpoint'], b"tcp://127.0.0.1:6667")
        # test receive event for connected event
        m = recv_monitor_message(s_event)
        self.assertEqual(m['event'], zmq.EVENT_CONNECTED)

########NEW FILE########
__FILENAME__ = test_monqueue
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import time
from unittest import TestCase

import zmq
from zmq import devices

from zmq.tests import BaseZMQTestCase, SkipTest, PYPY
from zmq.utils.strtypes import unicode


if PYPY or zmq.zmq_version_info() >= (4,1):
    # cleanup of shared Context doesn't work on PyPy
    # there also seems to be a bug in cleanup in libzmq-4.1 (zeromq/libzmq#1052)
    devices.Device.context_factory = zmq.Context


class TestMonitoredQueue(BaseZMQTestCase):
    
    sockets = []
    
    def build_device(self, mon_sub=b"", in_prefix=b'in', out_prefix=b'out'):
        self.device = devices.ThreadMonitoredQueue(zmq.PAIR, zmq.PAIR, zmq.PUB,
                                            in_prefix, out_prefix)
        alice = self.context.socket(zmq.PAIR)
        bob = self.context.socket(zmq.PAIR)
        mon = self.context.socket(zmq.SUB)
        
        aport = alice.bind_to_random_port('tcp://127.0.0.1')
        bport = bob.bind_to_random_port('tcp://127.0.0.1')
        mport = mon.bind_to_random_port('tcp://127.0.0.1')
        mon.setsockopt(zmq.SUBSCRIBE, mon_sub)
        
        self.device.connect_in("tcp://127.0.0.1:%i"%aport)
        self.device.connect_out("tcp://127.0.0.1:%i"%bport)
        self.device.connect_mon("tcp://127.0.0.1:%i"%mport)
        self.device.start()
        time.sleep(.2)
        try:
            # this is currenlty necessary to ensure no dropped monitor messages
            # see LIBZMQ-248 for more info
            mon.recv_multipart(zmq.NOBLOCK)
        except zmq.ZMQError:
            pass
        self.sockets.extend([alice, bob, mon])
        return alice, bob, mon
        
    
    def teardown_device(self):
        for socket in self.sockets:
            socket.close()
            del socket
        del self.device
        
    def test_reply(self):
        alice, bob, mon = self.build_device()
        alices = b"hello bob".split()
        alice.send_multipart(alices)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices, bobs)
        bobs = b"hello alice".split()
        bob.send_multipart(bobs)
        alices = self.recv_multipart(alice)
        self.assertEqual(alices, bobs)
        self.teardown_device()
    
    def test_queue(self):
        alice, bob, mon = self.build_device()
        alices = b"hello bob".split()
        alice.send_multipart(alices)
        alices2 = b"hello again".split()
        alice.send_multipart(alices2)
        alices3 = b"hello again and again".split()
        alice.send_multipart(alices3)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices, bobs)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices2, bobs)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices3, bobs)
        bobs = b"hello alice".split()
        bob.send_multipart(bobs)
        alices = self.recv_multipart(alice)
        self.assertEqual(alices, bobs)
        self.teardown_device()
    
    def test_monitor(self):
        alice, bob, mon = self.build_device()
        alices = b"hello bob".split()
        alice.send_multipart(alices)
        alices2 = b"hello again".split()
        alice.send_multipart(alices2)
        alices3 = b"hello again and again".split()
        alice.send_multipart(alices3)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices, bobs)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'in']+bobs, mons)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices2, bobs)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices3, bobs)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'in']+alices2, mons)
        bobs = b"hello alice".split()
        bob.send_multipart(bobs)
        alices = self.recv_multipart(alice)
        self.assertEqual(alices, bobs)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'in']+alices3, mons)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'out']+bobs, mons)
        self.teardown_device()
    
    def test_prefix(self):
        alice, bob, mon = self.build_device(b"", b'foo', b'bar')
        alices = b"hello bob".split()
        alice.send_multipart(alices)
        alices2 = b"hello again".split()
        alice.send_multipart(alices2)
        alices3 = b"hello again and again".split()
        alice.send_multipart(alices3)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices, bobs)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'foo']+bobs, mons)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices2, bobs)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices3, bobs)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'foo']+alices2, mons)
        bobs = b"hello alice".split()
        bob.send_multipart(bobs)
        alices = self.recv_multipart(alice)
        self.assertEqual(alices, bobs)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'foo']+alices3, mons)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'bar']+bobs, mons)
        self.teardown_device()
    
    def test_monitor_subscribe(self):
        alice, bob, mon = self.build_device(b"out")
        alices = b"hello bob".split()
        alice.send_multipart(alices)
        alices2 = b"hello again".split()
        alice.send_multipart(alices2)
        alices3 = b"hello again and again".split()
        alice.send_multipart(alices3)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices, bobs)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices2, bobs)
        bobs = self.recv_multipart(bob)
        self.assertEqual(alices3, bobs)
        bobs = b"hello alice".split()
        bob.send_multipart(bobs)
        alices = self.recv_multipart(alice)
        self.assertEqual(alices, bobs)
        mons = self.recv_multipart(mon)
        self.assertEqual([b'out']+bobs, mons)
        self.teardown_device()
    
    def test_router_router(self):
        """test router-router MQ devices"""
        dev = devices.ThreadMonitoredQueue(zmq.ROUTER, zmq.ROUTER, zmq.PUB, b'in', b'out')
        self.device = dev
        dev.setsockopt_in(zmq.LINGER, 0)
        dev.setsockopt_out(zmq.LINGER, 0)
        dev.setsockopt_mon(zmq.LINGER, 0)
        
        binder = self.context.socket(zmq.DEALER)
        porta = binder.bind_to_random_port('tcp://127.0.0.1')
        portb = binder.bind_to_random_port('tcp://127.0.0.1')
        binder.close()
        time.sleep(0.1)
        a = self.context.socket(zmq.DEALER)
        a.identity = b'a'
        b = self.context.socket(zmq.DEALER)
        b.identity = b'b'
        self.sockets.extend([a, b])
        
        a.connect('tcp://127.0.0.1:%i'%porta)
        dev.bind_in('tcp://127.0.0.1:%i'%porta)
        b.connect('tcp://127.0.0.1:%i'%portb)
        dev.bind_out('tcp://127.0.0.1:%i'%portb)
        dev.start()
        time.sleep(0.2)
        if zmq.zmq_version_info() >= (3,1,0):
            # flush erroneous poll state, due to LIBZMQ-280
            ping_msg = [ b'ping', b'pong' ]
            for s in (a,b):
                s.send_multipart(ping_msg)
                try:
                    s.recv(zmq.NOBLOCK)
                except zmq.ZMQError:
                    pass
        msg = [ b'hello', b'there' ]
        a.send_multipart([b'b']+msg)
        bmsg = self.recv_multipart(b)
        self.assertEqual(bmsg, [b'a']+msg)
        b.send_multipart(bmsg)
        amsg = self.recv_multipart(a)
        self.assertEqual(amsg, [b'b']+msg)
        self.teardown_device()
    
    def test_default_mq_args(self):
        self.device = dev = devices.ThreadMonitoredQueue(zmq.ROUTER, zmq.DEALER, zmq.PUB)
        dev.setsockopt_in(zmq.LINGER, 0)
        dev.setsockopt_out(zmq.LINGER, 0)
        dev.setsockopt_mon(zmq.LINGER, 0)
        # this will raise if default args are wrong
        dev.start()
        self.teardown_device()
    
    def test_mq_check_prefix(self):
        ins = self.context.socket(zmq.ROUTER)
        outs = self.context.socket(zmq.DEALER)
        mons = self.context.socket(zmq.PUB)
        self.sockets.extend([ins, outs, mons])
        
        ins = unicode('in')
        outs = unicode('out')
        self.assertRaises(TypeError, devices.monitoredqueue, ins, outs, mons)

########NEW FILE########
__FILENAME__ = test_multipart
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import zmq


from zmq.tests import BaseZMQTestCase, SkipTest, have_gevent, GreenTest

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestMultipart(BaseZMQTestCase):

    def test_router_dealer(self):
        router, dealer = self.create_bound_pair(zmq.ROUTER, zmq.DEALER)

        msg1 = b'message1'
        dealer.send(msg1)
        ident = self.recv(router)
        more = router.rcvmore
        self.assertEqual(more, True)
        msg2 = self.recv(router)
        self.assertEqual(msg1, msg2)
        more = router.rcvmore
        self.assertEqual(more, False)
    
    def test_basic_multipart(self):
        a,b = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        msg = [ b'hi', b'there', b'b']
        a.send_multipart(msg)
        recvd = b.recv_multipart()
        self.assertEqual(msg, recvd)

if have_gevent:
    class TestMultipartGreen(GreenTest, TestMultipart):
        pass

########NEW FILE########
__FILENAME__ = test_pair
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import zmq


from zmq.tests import BaseZMQTestCase, have_gevent, GreenTest

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

x = b' '
class TestPair(BaseZMQTestCase):

    def test_basic(self):
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)

        msg1 = b'message1'
        msg2 = self.ping_pong(s1, s2, msg1)
        self.assertEqual(msg1, msg2)

    def test_multiple(self):
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)

        for i in range(10):
            msg = i*x
            s1.send(msg)

        for i in range(10):
            msg = i*x
            s2.send(msg)

        for i in range(10):
            msg = s1.recv()
            self.assertEqual(msg, i*x)

        for i in range(10):
            msg = s2.recv()
            self.assertEqual(msg, i*x)

    def test_json(self):
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        o = dict(a=10,b=list(range(10)))
        o2 = self.ping_pong_json(s1, s2, o)

    def test_pyobj(self):
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        o = dict(a=10,b=range(10))
        o2 = self.ping_pong_pyobj(s1, s2, o)

if have_gevent:
    class TestReqRepGreen(GreenTest, TestPair):
        pass


########NEW FILE########
__FILENAME__ = test_poll
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import time
from unittest import TestCase

import zmq

from zmq.tests import PollZMQTestCase, have_gevent, GreenTest

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------
def wait():
    time.sleep(.25)


class TestPoll(PollZMQTestCase):

    Poller = zmq.Poller

    # This test is failing due to this issue:
    # http://github.com/sustrik/zeromq2/issues#issue/26
    def test_pair(self):
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)

        # Sleep to allow sockets to connect.
        wait()

        poller = self.Poller()
        poller.register(s1, zmq.POLLIN|zmq.POLLOUT)
        poller.register(s2, zmq.POLLIN|zmq.POLLOUT)
        # Poll result should contain both sockets
        socks = dict(poller.poll())
        # Now make sure that both are send ready.
        self.assertEqual(socks[s1], zmq.POLLOUT)
        self.assertEqual(socks[s2], zmq.POLLOUT)
        # Now do a send on both, wait and test for zmq.POLLOUT|zmq.POLLIN
        s1.send(b'msg1')
        s2.send(b'msg2')
        wait()
        socks = dict(poller.poll())
        self.assertEqual(socks[s1], zmq.POLLOUT|zmq.POLLIN)
        self.assertEqual(socks[s2], zmq.POLLOUT|zmq.POLLIN)
        # Make sure that both are in POLLOUT after recv.
        s1.recv()
        s2.recv()
        socks = dict(poller.poll())
        self.assertEqual(socks[s1], zmq.POLLOUT)
        self.assertEqual(socks[s2], zmq.POLLOUT)

        poller.unregister(s1)
        poller.unregister(s2)

        # Wait for everything to finish.
        wait()

    def test_reqrep(self):
        s1, s2 = self.create_bound_pair(zmq.REP, zmq.REQ)

        # Sleep to allow sockets to connect.
        wait()

        poller = self.Poller()
        poller.register(s1, zmq.POLLIN|zmq.POLLOUT)
        poller.register(s2, zmq.POLLIN|zmq.POLLOUT)

        # Make sure that s1 is in state 0 and s2 is in POLLOUT
        socks = dict(poller.poll())
        self.assertEqual(s1 in socks, 0)
        self.assertEqual(socks[s2], zmq.POLLOUT)

        # Make sure that s2 goes immediately into state 0 after send.
        s2.send(b'msg1')
        socks = dict(poller.poll())
        self.assertEqual(s2 in socks, 0)

        # Make sure that s1 goes into POLLIN state after a time.sleep().
        time.sleep(0.5)
        socks = dict(poller.poll())
        self.assertEqual(socks[s1], zmq.POLLIN)

        # Make sure that s1 goes into POLLOUT after recv.
        s1.recv()
        socks = dict(poller.poll())
        self.assertEqual(socks[s1], zmq.POLLOUT)

        # Make sure s1 goes into state 0 after send.
        s1.send(b'msg2')
        socks = dict(poller.poll())
        self.assertEqual(s1 in socks, 0)

        # Wait and then see that s2 is in POLLIN.
        time.sleep(0.5)
        socks = dict(poller.poll())
        self.assertEqual(socks[s2], zmq.POLLIN)

        # Make sure that s2 is in POLLOUT after recv.
        s2.recv()
        socks = dict(poller.poll())
        self.assertEqual(socks[s2], zmq.POLLOUT)

        poller.unregister(s1)
        poller.unregister(s2)

        # Wait for everything to finish.
        wait()
    
    def test_no_events(self):
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        poller = self.Poller()
        poller.register(s1, zmq.POLLIN|zmq.POLLOUT)
        poller.register(s2, 0)
        self.assertTrue(s1 in poller)
        self.assertFalse(s2 in poller)
        poller.register(s1, 0)
        self.assertFalse(s1 in poller)

    def test_pubsub(self):
        s1, s2 = self.create_bound_pair(zmq.PUB, zmq.SUB)
        s2.setsockopt(zmq.SUBSCRIBE, b'')

        # Sleep to allow sockets to connect.
        wait()

        poller = self.Poller()
        poller.register(s1, zmq.POLLIN|zmq.POLLOUT)
        poller.register(s2, zmq.POLLIN)

        # Now make sure that both are send ready.
        socks = dict(poller.poll())
        self.assertEqual(socks[s1], zmq.POLLOUT)
        self.assertEqual(s2 in socks, 0)
        # Make sure that s1 stays in POLLOUT after a send.
        s1.send(b'msg1')
        socks = dict(poller.poll())
        self.assertEqual(socks[s1], zmq.POLLOUT)

        # Make sure that s2 is POLLIN after waiting.
        wait()
        socks = dict(poller.poll())
        self.assertEqual(socks[s2], zmq.POLLIN)

        # Make sure that s2 goes into 0 after recv.
        s2.recv()
        socks = dict(poller.poll())
        self.assertEqual(s2 in socks, 0)

        poller.unregister(s1)
        poller.unregister(s2)

        # Wait for everything to finish.
        wait()
    def test_timeout(self):
        """make sure Poller.poll timeout has the right units (milliseconds)."""
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        poller = self.Poller()
        poller.register(s1, zmq.POLLIN)
        tic = time.time()
        evt = poller.poll(.005)
        toc = time.time()
        self.assertTrue(toc-tic < 0.1)
        tic = time.time()
        evt = poller.poll(5)
        toc = time.time()
        self.assertTrue(toc-tic < 0.1)
        self.assertTrue(toc-tic > .001)
        tic = time.time()
        evt = poller.poll(500)
        toc = time.time()
        self.assertTrue(toc-tic < 1)
        self.assertTrue(toc-tic > 0.1)

class TestSelect(PollZMQTestCase):

    def test_pair(self):
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)

        # Sleep to allow sockets to connect.
        wait()

        rlist, wlist, xlist = zmq.select([s1, s2], [s1, s2], [s1, s2])
        self.assert_(s1 in wlist)
        self.assert_(s2 in wlist)
        self.assert_(s1 not in rlist)
        self.assert_(s2 not in rlist)

    def test_timeout(self):
        """make sure select timeout has the right units (seconds)."""
        s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        tic = time.time()
        r,w,x = zmq.select([s1,s2],[],[],.005)
        toc = time.time()
        self.assertTrue(toc-tic < 1)
        self.assertTrue(toc-tic > 0.001)
        tic = time.time()
        r,w,x = zmq.select([s1,s2],[],[],.25)
        toc = time.time()
        self.assertTrue(toc-tic < 1)
        self.assertTrue(toc-tic > 0.1)


if have_gevent:
    import gevent
    from zmq import green as gzmq

    class TestPollGreen(GreenTest, TestPoll):
        Poller = gzmq.Poller

        def test_wakeup(self):
            s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
            poller = self.Poller()
            poller.register(s2, zmq.POLLIN)

            tic = time.time()
            r = gevent.spawn(lambda: poller.poll(10000))
            s = gevent.spawn(lambda: s1.send(b'msg1'))
            r.join()
            toc = time.time()
            self.assertTrue(toc-tic < 1)
        
        def test_socket_poll(self):
            s1, s2 = self.create_bound_pair(zmq.PAIR, zmq.PAIR)

            tic = time.time()
            r = gevent.spawn(lambda: s2.poll(10000))
            s = gevent.spawn(lambda: s1.send(b'msg1'))
            r.join()
            toc = time.time()
            self.assertTrue(toc-tic < 1)


########NEW FILE########
__FILENAME__ = test_pubsub
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import time
from unittest import TestCase

import zmq

from zmq.tests import BaseZMQTestCase, have_gevent, GreenTest

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestPubSub(BaseZMQTestCase):

    pass

    # We are disabling this test while an issue is being resolved.
    def test_basic(self):
        s1, s2 = self.create_bound_pair(zmq.PUB, zmq.SUB)
        s2.setsockopt(zmq.SUBSCRIBE,b'')
        time.sleep(0.1)
        msg1 = b'message'
        s1.send(msg1)
        msg2 = s2.recv()  # This is blocking!
        self.assertEqual(msg1, msg2)

    def test_topic(self):
        s1, s2 = self.create_bound_pair(zmq.PUB, zmq.SUB)
        s2.setsockopt(zmq.SUBSCRIBE, b'x')
        time.sleep(0.1)
        msg1 = b'message'
        s1.send(msg1)
        self.assertRaisesErrno(zmq.EAGAIN, s2.recv, zmq.NOBLOCK)
        msg1 = b'xmessage'
        s1.send(msg1)
        msg2 = s2.recv()
        self.assertEqual(msg1, msg2)

if have_gevent:
    class TestPubSubGreen(GreenTest, TestPubSub):
        pass

########NEW FILE########
__FILENAME__ = test_reqrep
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from unittest import TestCase

import zmq
from zmq.tests import BaseZMQTestCase, have_gevent, GreenTest

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestReqRep(BaseZMQTestCase):

    def test_basic(self):
        s1, s2 = self.create_bound_pair(zmq.REQ, zmq.REP)

        msg1 = b'message 1'
        msg2 = self.ping_pong(s1, s2, msg1)
        self.assertEqual(msg1, msg2)

    def test_multiple(self):
        s1, s2 = self.create_bound_pair(zmq.REQ, zmq.REP)

        for i in range(10):
            msg1 = i*b' '
            msg2 = self.ping_pong(s1, s2, msg1)
            self.assertEqual(msg1, msg2)

    def test_bad_send_recv(self):
        s1, s2 = self.create_bound_pair(zmq.REQ, zmq.REP)
        
        if zmq.zmq_version() != '2.1.8':
            # this doesn't work on 2.1.8
            for copy in (True,False):
                self.assertRaisesErrno(zmq.EFSM, s1.recv, copy=copy)
                self.assertRaisesErrno(zmq.EFSM, s2.send, b'asdf', copy=copy)

        # I have to have this or we die on an Abort trap.
        msg1 = b'asdf'
        msg2 = self.ping_pong(s1, s2, msg1)
        self.assertEqual(msg1, msg2)

    def test_json(self):
        s1, s2 = self.create_bound_pair(zmq.REQ, zmq.REP)
        o = dict(a=10,b=list(range(10)))
        o2 = self.ping_pong_json(s1, s2, o)

    def test_pyobj(self):
        s1, s2 = self.create_bound_pair(zmq.REQ, zmq.REP)
        o = dict(a=10,b=range(10))
        o2 = self.ping_pong_pyobj(s1, s2, o)

    def test_large_msg(self):
        s1, s2 = self.create_bound_pair(zmq.REQ, zmq.REP)
        msg1 = 10000*b'X'

        for i in range(10):
            msg2 = self.ping_pong(s1, s2, msg1)
            self.assertEqual(msg1, msg2)

if have_gevent:
    class TestReqRepGreen(GreenTest, TestReqRep):
        pass

########NEW FILE########
__FILENAME__ = test_security
"""Test libzmq security (libzmq >= 3.3.0)"""
# -*- coding: utf8 -*-
#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import os
from threading import Thread

import zmq
from zmq.tests import (
    BaseZMQTestCase, SkipTest
)
from zmq.utils import z85


USER = b"admin"
PASS = b"password"

class TestSecurity(BaseZMQTestCase):
    
    def setUp(self):
        if zmq.zmq_version_info() < (4,0):
            raise SkipTest("security is new in libzmq 4.0")
        try:
            zmq.curve_keypair()
        except zmq.ZMQError:
            raise SkipTest("security requires libzmq to be linked against libsodium")
        super(TestSecurity, self).setUp()
    
    
    def zap_handler(self):
        socket = self.context.socket(zmq.REP)
        socket.bind("inproc://zeromq.zap.01")
        try:
            msg = self.recv_multipart(socket)

            version, sequence, domain, address, identity, mechanism = msg[:6]
            if mechanism == b'PLAIN':
                username, password = msg[6:]
            elif mechanism == b'CURVE':
                key = msg[6]

            self.assertEqual(version, b"1.0")
            self.assertEqual(identity, b"IDENT")
            reply = [version, sequence]
            if mechanism == b'CURVE' or \
                (mechanism == b'PLAIN' and username == USER and password == PASS) or \
                (mechanism == b'NULL'):
                reply.extend([
                    b"200",
                    b"OK",
                    b"anonymous",
                    b"",
                ])
            else:
                reply.extend([
                    b"400",
                    b"Invalid username or password",
                    b"",
                    b"",
                ])
            socket.send_multipart(reply)
        finally:
            socket.close()
    
    def start_zap(self):
        self.zap_thread = Thread(target=self.zap_handler)
        self.zap_thread.start()
    
    def stop_zap(self):
        self.zap_thread.join()

    def bounce(self, server, client):
        msg = [os.urandom(64), os.urandom(64)]
        client.send_multipart(msg)
        recvd = self.recv_multipart(server)
        self.assertEqual(recvd, msg)
        server.send_multipart(recvd)
        msg2 = self.recv_multipart(client)
        self.assertEqual(msg2, msg)
    
    def test_null(self):
        """test NULL (default) security"""
        server = self.socket(zmq.DEALER)
        client = self.socket(zmq.DEALER)
        self.assertEqual(client.MECHANISM, zmq.NULL)
        self.assertEqual(server.mechanism, zmq.NULL)
        self.assertEqual(client.plain_server, 0)
        self.assertEqual(server.plain_server, 0)
        iface = 'tcp://127.0.0.1'
        port = server.bind_to_random_port(iface)
        client.connect("%s:%i" % (iface, port))
        self.bounce(server, client)

    def test_plain(self):
        """test PLAIN authentication"""
        server = self.socket(zmq.DEALER)
        server.identity = b'IDENT'
        client = self.socket(zmq.DEALER)
        self.assertEqual(client.plain_username, b'')
        self.assertEqual(client.plain_password, b'')
        client.plain_username = USER
        client.plain_password = PASS
        self.assertEqual(client.getsockopt(zmq.PLAIN_USERNAME), USER)
        self.assertEqual(client.getsockopt(zmq.PLAIN_PASSWORD), PASS)
        self.assertEqual(client.plain_server, 0)
        self.assertEqual(server.plain_server, 0)
        server.plain_server = True
        self.assertEqual(server.mechanism, zmq.PLAIN)
        self.assertEqual(client.mechanism, zmq.PLAIN)
        
        assert not client.plain_server
        assert server.plain_server
        
        self.start_zap()
        
        iface = 'tcp://127.0.0.1'
        port = server.bind_to_random_port(iface)
        client.connect("%s:%i" % (iface, port))
        self.bounce(server, client)
        self.stop_zap()

    def skip_plain_inauth(self):
        """test PLAIN failed authentication"""
        server = self.socket(zmq.DEALER)
        server.identity = b'IDENT'
        client = self.socket(zmq.DEALER)
        self.sockets.extend([server, client])
        client.plain_username = USER
        client.plain_password = b'incorrect'
        server.plain_server = True
        self.assertEqual(server.mechanism, zmq.PLAIN)
        self.assertEqual(client.mechanism, zmq.PLAIN)
        
        self.start_zap()
        
        iface = 'tcp://127.0.0.1'
        port = server.bind_to_random_port(iface)
        client.connect("%s:%i" % (iface, port))
        client.send(b'ping')
        server.rcvtimeo = 250
        self.assertRaisesErrno(zmq.EAGAIN, server.recv)
        self.stop_zap()
    
    def test_keypair(self):
        """test curve_keypair"""
        try:
            public, secret = zmq.curve_keypair()
        except zmq.ZMQError:
            raise SkipTest("CURVE unsupported")
        
        self.assertEqual(type(secret), bytes)
        self.assertEqual(type(public), bytes)
        self.assertEqual(len(secret), 40)
        self.assertEqual(len(public), 40)
        
        # verify that it is indeed Z85
        bsecret, bpublic = [ z85.decode(key) for key in (public, secret) ]
        self.assertEqual(type(bsecret), bytes)
        self.assertEqual(type(bpublic), bytes)
        self.assertEqual(len(bsecret), 32)
        self.assertEqual(len(bpublic), 32)
        
    
    def test_curve(self):
        """test CURVE encryption"""
        server = self.socket(zmq.DEALER)
        server.identity = b'IDENT'
        client = self.socket(zmq.DEALER)
        self.sockets.extend([server, client])
        try:
            server.curve_server = True
        except zmq.ZMQError as e:
            # will raise EINVAL if not linked against libsodium
            if e.errno == zmq.EINVAL:
                raise SkipTest("CURVE unsupported")
        
        server_public, server_secret = zmq.curve_keypair()
        client_public, client_secret = zmq.curve_keypair()
        
        server.curve_secretkey = server_secret
        server.curve_publickey = server_public
        client.curve_serverkey = server_public
        client.curve_publickey = client_public
        client.curve_secretkey = client_secret
        
        self.assertEqual(server.mechanism, zmq.CURVE)
        self.assertEqual(client.mechanism, zmq.CURVE)
        
        self.assertEqual(server.get(zmq.CURVE_SERVER), True)
        self.assertEqual(client.get(zmq.CURVE_SERVER), False)
        
        self.start_zap()
        
        iface = 'tcp://127.0.0.1'
        port = server.bind_to_random_port(iface)
        client.connect("%s:%i" % (iface, port))
        self.bounce(server, client)
        self.stop_zap()
        

########NEW FILE########
__FILENAME__ = test_socket
# -*- coding: utf8 -*-
#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
import time
import errno
import warnings

import zmq
from zmq.tests import (
    BaseZMQTestCase, SkipTest, have_gevent, GreenTest, skip_pypy, skip_if
)
from zmq.utils.strtypes import bytes, unicode

try:
    from queue import Queue
except:
    from Queue import Queue

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestSocket(BaseZMQTestCase):

    def test_create(self):
        ctx = self.Context()
        s = ctx.socket(zmq.PUB)
        # Superluminal protocol not yet implemented
        self.assertRaisesErrno(zmq.EPROTONOSUPPORT, s.bind, 'ftl://a')
        self.assertRaisesErrno(zmq.EPROTONOSUPPORT, s.connect, 'ftl://a')
        self.assertRaisesErrno(zmq.EINVAL, s.bind, 'tcp://')
        s.close()
        del ctx
    
    def test_dir(self):
        ctx = self.Context()
        s = ctx.socket(zmq.PUB)
        self.assertTrue('send' in dir(s))
        self.assertTrue('IDENTITY' in dir(s))
        self.assertTrue('AFFINITY' in dir(s))
        self.assertTrue('FD' in dir(s))
        s.close()
        ctx.term()

    def test_bind_unicode(self):
        s = self.socket(zmq.PUB)
        p = s.bind_to_random_port(unicode("tcp://*"))

    def test_connect_unicode(self):
        s = self.socket(zmq.PUB)
        s.connect(unicode("tcp://127.0.0.1:5555"))

    def test_bind_to_random_port(self):
        # Check that bind_to_random_port do not hide usefull exception
        ctx = self.Context()
        c = ctx.socket(zmq.PUB)
        # Invalid format
        try:
            c.bind_to_random_port('tcp:*')
        except zmq.ZMQError as e:
            self.assertEqual(e.errno, zmq.EINVAL)
        # Invalid protocol
        try:
            c.bind_to_random_port('rand://*')
        except zmq.ZMQError as e:
            self.assertEqual(e.errno, zmq.EPROTONOSUPPORT)

    def test_identity(self):
        s = self.context.socket(zmq.PULL)
        self.sockets.append(s)
        ident = b'identity\0\0'
        s.identity = ident
        self.assertEqual(s.get(zmq.IDENTITY), ident)

    def test_unicode_sockopts(self):
        """test setting/getting sockopts with unicode strings"""
        topic = "tést"
        if str is not unicode:
            topic = topic.decode('utf8')
        p,s = self.create_bound_pair(zmq.PUB, zmq.SUB)
        self.assertEqual(s.send_unicode, s.send_unicode)
        self.assertEqual(p.recv_unicode, p.recv_unicode)
        self.assertRaises(TypeError, s.setsockopt, zmq.SUBSCRIBE, topic)
        self.assertRaises(TypeError, s.setsockopt, zmq.IDENTITY, topic)
        s.setsockopt_unicode(zmq.IDENTITY, topic, 'utf16')
        self.assertRaises(TypeError, s.setsockopt, zmq.AFFINITY, topic)
        s.setsockopt_unicode(zmq.SUBSCRIBE, topic)
        self.assertRaises(TypeError, s.getsockopt_unicode, zmq.AFFINITY)
        self.assertRaisesErrno(zmq.EINVAL, s.getsockopt_unicode, zmq.SUBSCRIBE)
        
        identb = s.getsockopt(zmq.IDENTITY)
        identu = identb.decode('utf16')
        identu2 = s.getsockopt_unicode(zmq.IDENTITY, 'utf16')
        self.assertEqual(identu, identu2)
        time.sleep(0.1) # wait for connection/subscription
        p.send_unicode(topic,zmq.SNDMORE)
        p.send_unicode(topic*2, encoding='latin-1')
        self.assertEqual(topic, s.recv_unicode())
        self.assertEqual(topic*2, s.recv_unicode(encoding='latin-1'))
    
    def test_int_sockopts(self):
        "test integer sockopts"
        v = zmq.zmq_version_info()
        if v < (3,0):
            default_hwm = 0
        else:
            default_hwm = 1000
        p,s = self.create_bound_pair(zmq.PUB, zmq.SUB)
        p.setsockopt(zmq.LINGER, 0)
        self.assertEqual(p.getsockopt(zmq.LINGER), 0)
        p.setsockopt(zmq.LINGER, -1)
        self.assertEqual(p.getsockopt(zmq.LINGER), -1)
        self.assertEqual(p.hwm, default_hwm)
        p.hwm = 11
        self.assertEqual(p.hwm, 11)
        # p.setsockopt(zmq.EVENTS, zmq.POLLIN)
        self.assertEqual(p.getsockopt(zmq.EVENTS), zmq.POLLOUT)
        self.assertRaisesErrno(zmq.EINVAL, p.setsockopt,zmq.EVENTS, 2**7-1)
        self.assertEqual(p.getsockopt(zmq.TYPE), p.socket_type)
        self.assertEqual(p.getsockopt(zmq.TYPE), zmq.PUB)
        self.assertEqual(s.getsockopt(zmq.TYPE), s.socket_type)
        self.assertEqual(s.getsockopt(zmq.TYPE), zmq.SUB)
        
        # check for overflow / wrong type:
        errors = []
        backref = {}
        constants = zmq.constants
        for name in constants.__all__:
            value = getattr(constants, name)
            if isinstance(value, int):
                backref[value] = name
        for opt in zmq.constants.int_sockopts.union(zmq.constants.int64_sockopts):
            sopt = backref[opt]
            if sopt.startswith((
                'ROUTER', 'XPUB', 'TCP', 'FAIL',
                'REQ_', 'CURVE_', 'PROBE_ROUTER',
                'IPC_FILTER',
                )):
                # some sockopts are write-only
                continue
            try:
                n = p.getsockopt(opt)
            except zmq.ZMQError as e:
                errors.append("getsockopt(zmq.%s) raised '%s'."%(sopt, e))
            else:
                if n > 2**31:
                    errors.append("getsockopt(zmq.%s) returned a ridiculous value."
                                    " It is probably the wrong type."%sopt)
        if errors:
            self.fail('\n'.join([''] + errors))
    
    def test_bad_sockopts(self):
        """Test that appropriate errors are raised on bad socket options"""
        s = self.context.socket(zmq.PUB)
        self.sockets.append(s)
        s.setsockopt(zmq.LINGER, 0)
        # unrecognized int sockopts pass through to libzmq, and should raise EINVAL
        self.assertRaisesErrno(zmq.EINVAL, s.setsockopt, 9999, 5)
        self.assertRaisesErrno(zmq.EINVAL, s.getsockopt, 9999)
        # but only int sockopts are allowed through this way, otherwise raise a TypeError
        self.assertRaises(TypeError, s.setsockopt, 9999, b"5")
        # some sockopts are valid in general, but not on every socket:
        self.assertRaisesErrno(zmq.EINVAL, s.setsockopt, zmq.SUBSCRIBE, b'hi')
    
    def test_sockopt_roundtrip(self):
        "test set/getsockopt roundtrip."
        p = self.context.socket(zmq.PUB)
        self.sockets.append(p)
        self.assertEqual(p.getsockopt(zmq.LINGER), -1)
        p.setsockopt(zmq.LINGER, 11)
        self.assertEqual(p.getsockopt(zmq.LINGER), 11)
    
    def test_poll(self):
        """test Socket.poll()"""
        req, rep = self.create_bound_pair(zmq.REQ, zmq.REP)
        # default flag is POLLIN, nobody has anything to recv:
        self.assertEqual(req.poll(0), 0)
        self.assertEqual(rep.poll(0), 0)
        self.assertEqual(req.poll(0, zmq.POLLOUT), zmq.POLLOUT)
        self.assertEqual(rep.poll(0, zmq.POLLOUT), 0)
        self.assertEqual(req.poll(0, zmq.POLLOUT|zmq.POLLIN), zmq.POLLOUT)
        self.assertEqual(rep.poll(0, zmq.POLLOUT), 0)
        req.send('hi')
        self.assertEqual(req.poll(0), 0)
        self.assertEqual(rep.poll(1), zmq.POLLIN)
        self.assertEqual(req.poll(0, zmq.POLLOUT), 0)
        self.assertEqual(rep.poll(0, zmq.POLLOUT), 0)
        self.assertEqual(req.poll(0, zmq.POLLOUT|zmq.POLLIN), 0)
        self.assertEqual(rep.poll(0, zmq.POLLOUT), zmq.POLLIN)
    
    def test_send_unicode(self):
        "test sending unicode objects"
        a,b = self.create_bound_pair(zmq.PAIR, zmq.PAIR)
        self.sockets.extend([a,b])
        u = "çπ§"
        if str is not unicode:
            u = u.decode('utf8')
        self.assertRaises(TypeError, a.send, u,copy=False)
        self.assertRaises(TypeError, a.send, u,copy=True)
        a.send_unicode(u)
        s = b.recv()
        self.assertEqual(s,u.encode('utf8'))
        self.assertEqual(s.decode('utf8'),u)
        a.send_unicode(u,encoding='utf16')
        s = b.recv_unicode(encoding='utf16')
        self.assertEqual(s,u)
    
    @skip_pypy
    def test_tracker(self):
        "test the MessageTracker object for tracking when zmq is done with a buffer"
        addr = 'tcp://127.0.0.1'
        a = self.context.socket(zmq.PUB)
        port = a.bind_to_random_port(addr)
        a.close()
        iface = "%s:%i"%(addr,port)
        a = self.context.socket(zmq.PAIR)
        # a.setsockopt(zmq.IDENTITY, b"a")
        b = self.context.socket(zmq.PAIR)
        self.sockets.extend([a,b])
        a.connect(iface)
        time.sleep(0.1)
        p1 = a.send(b'something', copy=False, track=True)
        self.assertTrue(isinstance(p1, zmq.MessageTracker))
        self.assertFalse(p1.done)
        p2 = a.send_multipart([b'something', b'else'], copy=False, track=True)
        self.assert_(isinstance(p2, zmq.MessageTracker))
        self.assertEqual(p2.done, False)
        self.assertEqual(p1.done, False)

        b.bind(iface)
        msg = b.recv_multipart()
        for i in range(10):
            if p1.done:
                break
            time.sleep(0.1)
        self.assertEqual(p1.done, True)
        self.assertEqual(msg, [b'something'])
        msg = b.recv_multipart()
        for i in range(10):
            if p2.done:
                break
            time.sleep(0.1)
        self.assertEqual(p2.done, True)
        self.assertEqual(msg, [b'something', b'else'])
        m = zmq.Frame(b"again", track=True)
        self.assertEqual(m.tracker.done, False)
        p1 = a.send(m, copy=False)
        p2 = a.send(m, copy=False)
        self.assertEqual(m.tracker.done, False)
        self.assertEqual(p1.done, False)
        self.assertEqual(p2.done, False)
        msg = b.recv_multipart()
        self.assertEqual(m.tracker.done, False)
        self.assertEqual(msg, [b'again'])
        msg = b.recv_multipart()
        self.assertEqual(m.tracker.done, False)
        self.assertEqual(msg, [b'again'])
        self.assertEqual(p1.done, False)
        self.assertEqual(p2.done, False)
        pm = m.tracker
        del m
        for i in range(10):
            if p1.done:
                break
            time.sleep(0.1)
        self.assertEqual(p1.done, True)
        self.assertEqual(p2.done, True)
        m = zmq.Frame(b'something', track=False)
        self.assertRaises(ValueError, a.send, m, copy=False, track=True)
        

    def test_close(self):
        ctx = self.Context()
        s = ctx.socket(zmq.PUB)
        s.close()
        self.assertRaisesErrno(zmq.ENOTSOCK, s.bind, b'')
        self.assertRaisesErrno(zmq.ENOTSOCK, s.connect, b'')
        self.assertRaisesErrno(zmq.ENOTSOCK, s.setsockopt, zmq.SUBSCRIBE, b'')
        self.assertRaisesErrno(zmq.ENOTSOCK, s.send, b'asdf')
        self.assertRaisesErrno(zmq.ENOTSOCK, s.recv)
        del ctx
    
    def test_attr(self):
        """set setting/getting sockopts as attributes"""
        s = self.context.socket(zmq.DEALER)
        self.sockets.append(s)
        linger = 10
        s.linger = linger
        self.assertEqual(linger, s.linger)
        self.assertEqual(linger, s.getsockopt(zmq.LINGER))
        self.assertEqual(s.fd, s.getsockopt(zmq.FD))
    
    def test_bad_attr(self):
        s = self.context.socket(zmq.DEALER)
        self.sockets.append(s)
        try:
            s.apple='foo'
        except AttributeError:
            pass
        else:
            self.fail("bad setattr should have raised AttributeError")
        try:
            s.apple
        except AttributeError:
            pass
        else:
            self.fail("bad getattr should have raised AttributeError")

    def test_subclass(self):
        """subclasses can assign attributes"""
        class S(zmq.Socket):
            a = None
            def __init__(self, *a, **kw):
                self.a=-1
                super(S, self).__init__(*a, **kw)
        
        s = S(self.context, zmq.REP)
        self.sockets.append(s)
        self.assertEqual(s.a, -1)
        s.a=1
        self.assertEqual(s.a, 1)
        a=s.a
        self.assertEqual(a, 1)
    
    def test_recv_multipart(self):
        a,b = self.create_bound_pair()
        msg = b'hi'
        for i in range(3):
            a.send(msg)
        time.sleep(0.1)
        for i in range(3):
            self.assertEqual(b.recv_multipart(), [msg])
    
    def test_close_after_destroy(self):
        """s.close() after ctx.destroy() should be fine"""
        ctx = self.Context()
        s = ctx.socket(zmq.REP)
        ctx.destroy()
        # reaper is not instantaneous
        time.sleep(1e-2)
        s.close()
        self.assertTrue(s.closed)
    
    def test_poll(self):
        a,b = self.create_bound_pair()
        tic = time.time()
        evt = a.poll(50)
        self.assertEqual(evt, 0)
        evt = a.poll(50, zmq.POLLOUT)
        self.assertEqual(evt, zmq.POLLOUT)
        msg = b'hi'
        a.send(msg)
        evt = b.poll(50)
        self.assertEqual(evt, zmq.POLLIN)
        msg2 = self.recv(b)
        evt = b.poll(50)
        self.assertEqual(evt, 0)
        self.assertEqual(msg2, msg)
    
    def test_ipc_path_max_length(self):
        """IPC_PATH_MAX_LEN is a sensible value"""
        if zmq.IPC_PATH_MAX_LEN == 0:
            raise SkipTest("IPC_PATH_MAX_LEN undefined")
        
        msg = "Surprising value for IPC_PATH_MAX_LEN: %s" % zmq.IPC_PATH_MAX_LEN
        self.assertTrue(zmq.IPC_PATH_MAX_LEN > 30, msg)
        self.assertTrue(zmq.IPC_PATH_MAX_LEN < 1025, msg)

    def test_ipc_path_max_length_msg(self):
        if zmq.IPC_PATH_MAX_LEN == 0:
            raise SkipTest("IPC_PATH_MAX_LEN undefined")
        
        s = self.context.socket(zmq.PUB)
        self.sockets.append(s)
        try:
            s.bind('ipc://{0}'.format('a' * (zmq.IPC_PATH_MAX_LEN + 1)))
        except zmq.ZMQError as e:
            self.assertTrue(str(zmq.IPC_PATH_MAX_LEN) in e.strerror)
    
    def test_hwm(self):
        zmq3 = zmq.zmq_version_info()[0] >= 3
        for stype in (zmq.PUB, zmq.ROUTER, zmq.SUB, zmq.REQ, zmq.DEALER):
            s = self.context.socket(stype)
            s.hwm = 100
            self.assertEqual(s.hwm, 100)
            if zmq3:
                try:
                    self.assertEqual(s.sndhwm, 100)
                except AttributeError:
                    pass
                try:
                    self.assertEqual(s.rcvhwm, 100)
                except AttributeError:
                    pass
            s.close()
    
    def test_shadow(self):
        p = self.socket(zmq.PUSH)
        p.bind("tcp://127.0.0.1:5555")
        p2 = zmq.Socket.shadow(p.underlying)
        self.assertEqual(p.underlying, p2.underlying)
        s = self.socket(zmq.PULL)
        s2 = zmq.Socket.shadow(s.underlying)
        self.assertNotEqual(s.underlying, p.underlying)
        self.assertEqual(s.underlying, s2.underlying)
        s2.connect("tcp://127.0.0.1:5555")
        sent = b'hi'
        p2.send(sent)
        rcvd = self.recv(s2)
        self.assertEqual(rcvd, sent)
    
    def test_shadow_pyczmq(self):
        try:
            from pyczmq import zctx, zsocket, zstr
        except Exception:
            raise SkipTest("Requires pyczmq")
        
        ctx = zctx.new()
        ca = zsocket.new(ctx, zmq.PUSH)
        cb = zsocket.new(ctx, zmq.PULL)
        a = zmq.Socket.shadow(ca)
        b = zmq.Socket.shadow(cb)
        a.bind("inproc://a")
        b.connect("inproc://a")
        a.send(b'hi')
        rcvd = self.recv(b)
        self.assertEqual(rcvd, b'hi')


if have_gevent:
    import gevent
    
    class TestSocketGreen(GreenTest, TestSocket):
        test_bad_attr = GreenTest.skip_green
        test_close_after_destroy = GreenTest.skip_green
        
        def test_timeout(self):
            a,b = self.create_bound_pair()
            g = gevent.spawn_later(0.5, lambda: a.send(b'hi'))
            timeout = gevent.Timeout(0.1)
            timeout.start()
            self.assertRaises(gevent.Timeout, b.recv)
            g.kill()
        
        @skip_if(not hasattr(zmq, 'RCVTIMEO'))
        def test_warn_set_timeo(self):
            s = self.context.socket(zmq.REQ)
            with warnings.catch_warnings(record=True) as w:
                s.rcvtimeo = 5
            s.close()
            self.assertEqual(len(w), 1)
            self.assertEqual(w[0].category, UserWarning)
            

        @skip_if(not hasattr(zmq, 'SNDTIMEO'))
        def test_warn_get_timeo(self):
            s = self.context.socket(zmq.REQ)
            with warnings.catch_warnings(record=True) as w:
                s.sndtimeo
            s.close()
            self.assertEqual(len(w), 1)
            self.assertEqual(w[0].category, UserWarning)

########NEW FILE########
__FILENAME__ = test_stopwatch
# -*- coding: utf8 -*-
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
import time

from unittest import TestCase

from zmq import Stopwatch, ZMQError

if sys.version_info[0] >= 3:
    long = int

class TestStopWatch(TestCase):
    
    def test_stop_long(self):
        """Ensure stop returns a long int."""
        watch = Stopwatch()
        watch.start()
        us = watch.stop()
        self.assertTrue(isinstance(us, long))
        
    def test_stop_microseconds(self):
        """Test that stop/sleep have right units."""
        watch = Stopwatch()
        watch.start()
        tic = time.time()
        watch.sleep(1)
        us = watch.stop()
        toc = time.time()
        self.assertAlmostEqual(us/1e6,(toc-tic),places=0)
    
    def test_double_stop(self):
        """Test error raised on multiple calls to stop."""
        watch = Stopwatch()
        watch.start()
        watch.stop()
        self.assertRaises(ZMQError, watch.stop)
        self.assertRaises(ZMQError, watch.stop)
    

########NEW FILE########
__FILENAME__ = test_version
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from unittest import TestCase
import zmq
from zmq.sugar import version


#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestVersion(TestCase):

    def test_pyzmq_version(self):
        vs = zmq.pyzmq_version()
        vs2 = zmq.__version__
        self.assertTrue(isinstance(vs, str))
        if zmq.__revision__:
            self.assertEqual(vs, '@'.join(vs2, zmq.__revision__))
        else:
            self.assertEqual(vs, vs2)
        if version.VERSION_EXTRA:
            self.assertTrue(version.VERSION_EXTRA in vs)
            self.assertTrue(version.VERSION_EXTRA in vs2)

    def test_pyzmq_version_info(self):
        info = zmq.pyzmq_version_info()
        self.assertTrue(isinstance(info, tuple))
        for n in info[:3]:
            self.assertTrue(isinstance(n, int))
        if version.VERSION_EXTRA:
            self.assertEqual(len(info), 4)
            self.assertEqual(info[-1], float('inf'))
        else:
            self.assertEqual(len(info), 3)

    def test_zmq_version_info(self):
        info = zmq.zmq_version_info()
        self.assertTrue(isinstance(info, tuple))
        for n in info[:3]:
            self.assertTrue(isinstance(n, int))

    def test_zmq_version(self):
        v = zmq.zmq_version()
        self.assertTrue(isinstance(v, str))


########NEW FILE########
__FILENAME__ = test_z85
# -*- coding: utf8 -*-
"""Test Z85 encoding

confirm values and roundtrip with test values from the reference implementation.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from unittest import TestCase
from zmq.utils import z85

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

class TestZ85(TestCase):
    
    def test_client_public(self):
        client_public = \
            b"\xBB\x88\x47\x1D\x65\xE2\x65\x9B" \
            b"\x30\xC5\x5A\x53\x21\xCE\xBB\x5A" \
            b"\xAB\x2B\x70\xA3\x98\x64\x5C\x26" \
            b"\xDC\xA2\xB2\xFC\xB4\x3F\xC5\x18"
        encoded = z85.encode(client_public)
        
        self.assertEqual(encoded, b"Yne@$w-vo<fVvi]a<NY6T1ed:M$fCG*[IaLV{hID")
        decoded = z85.decode(encoded)
        self.assertEqual(decoded, client_public)
    
    def test_client_secret(self):
        client_secret = \
            b"\x7B\xB8\x64\xB4\x89\xAF\xA3\x67" \
            b"\x1F\xBE\x69\x10\x1F\x94\xB3\x89" \
            b"\x72\xF2\x48\x16\xDF\xB0\x1B\x51" \
            b"\x65\x6B\x3F\xEC\x8D\xFD\x08\x88"
        encoded = z85.encode(client_secret)
        
        self.assertEqual(encoded, b"D:)Q[IlAW!ahhC2ac:9*A}h:p?([4%wOTJ%JR%cs")
        decoded = z85.decode(encoded)
        self.assertEqual(decoded, client_secret)

    def test_server_public(self):
        server_public = \
            b"\x54\xFC\xBA\x24\xE9\x32\x49\x96" \
            b"\x93\x16\xFB\x61\x7C\x87\x2B\xB0" \
            b"\xC1\xD1\xFF\x14\x80\x04\x27\xC5" \
            b"\x94\xCB\xFA\xCF\x1B\xC2\xD6\x52"
        encoded = z85.encode(server_public)
        
        self.assertEqual(encoded, b"rq:rM>}U?@Lns47E1%kR.o@n%FcmmsL/@{H8]yf7")
        decoded = z85.decode(encoded)
        self.assertEqual(decoded, server_public)
    
    def test_server_secret(self):
        server_secret = \
            b"\x8E\x0B\xDD\x69\x76\x28\xB9\x1D" \
            b"\x8F\x24\x55\x87\xEE\x95\xC5\xB0" \
            b"\x4D\x48\x96\x3F\x79\x25\x98\x77" \
            b"\xB4\x9C\xD9\x06\x3A\xEA\xD3\xB7"
        encoded = z85.encode(server_secret)
        
        self.assertEqual(encoded, b"JTKVSB%%)wK0E.X)V>+}o?pNmC{O&4W4b!Ni{Lh6")
        decoded = z85.decode(encoded)
        self.assertEqual(decoded, server_secret)


########NEW FILE########
__FILENAME__ = test_zmqstream
# -*- coding: utf8 -*-
#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
import time

from unittest import TestCase

import zmq
from zmq.eventloop import ioloop, zmqstream

class TestZMQStream(TestCase):
    
    def setUp(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.loop = ioloop.IOLoop.instance()
        self.stream = zmqstream.ZMQStream(self.socket)
    
    def tearDown(self):
        self.socket.close()
        self.context.term()
    
    def test_callable_check(self):
        """Ensure callable check works (py3k)."""
        
        self.stream.on_send(lambda *args: None)
        self.stream.on_recv(lambda *args: None)
        self.assertRaises(AssertionError, self.stream.on_recv, 1)
        self.assertRaises(AssertionError, self.stream.on_send, 1)
        self.assertRaises(AssertionError, self.stream.on_recv, zmq)
        

########NEW FILE########
__FILENAME__ = constant_names
"""0MQ Constant names"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian E. Granger & Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Python module level constants
#-----------------------------------------------------------------------------

# dictionaries of constants new or removed in particular versions

new_in = {
    (2,2,0) : [
        'RCVTIMEO',
        'SNDTIMEO',
    ],
    (3,2,2) : [
        # errnos
        'EMSGSIZE',
        'EAFNOSUPPORT',
        'ENETUNREACH',
        'ECONNABORTED',
        'ECONNRESET',
        'ENOTCONN',
        'ETIMEDOUT',
        'EHOSTUNREACH',
        'ENETRESET',
        
        'IO_THREADS',
        'MAX_SOCKETS',
        'IO_THREADS_DFLT',
        'MAX_SOCKETS_DFLT',
        
        'ROUTER_BEHAVIOR',
        'ROUTER_MANDATORY',
        'FAIL_UNROUTABLE',
        'TCP_KEEPALIVE',
        'TCP_KEEPALIVE_CNT',
        'TCP_KEEPALIVE_IDLE',
        'TCP_KEEPALIVE_INTVL',
        'DELAY_ATTACH_ON_CONNECT',
        'XPUB_VERBOSE',
        
        'EVENT_CONNECTED',
        'EVENT_CONNECT_DELAYED',
        'EVENT_CONNECT_RETRIED',
        'EVENT_LISTENING',
        'EVENT_BIND_FAILED',
        'EVENT_ACCEPTED',
        'EVENT_ACCEPT_FAILED',
        'EVENT_CLOSED',
        'EVENT_CLOSE_FAILED',
        'EVENT_DISCONNECTED',
        'EVENT_ALL',
    ],
    (4,0,0) : [
        # socket types
        'STREAM',
        
        # socket opts
        'IMMEDIATE',
        'ROUTER_RAW',
        'IPV6',
        'MECHANISM',
        'PLAIN_SERVER',
        'PLAIN_USERNAME',
        'PLAIN_PASSWORD',
        'CURVE_SERVER',
        'CURVE_PUBLICKEY',
        'CURVE_SECRETKEY',
        'CURVE_SERVERKEY',
        'PROBE_ROUTER',
        'REQ_RELAXED',
        'REQ_CORRELATE',
        'CONFLATE',
        'ZAP_DOMAIN',
        
        # security
        'NULL',
        'PLAIN',
        'CURVE',
        
        # events
        'EVENT_MONITOR_STOPPED',
    ],
    (4,1,0) : [
        # socket opts
        'ROUTER_HANDOVER',
        'TOS',
        'IPC_FILTER_PID',
        'IPC_FILTER_UID',
        'IPC_FILTER_GID',
        'CONNECT_RID',
    ],
}


removed_in = {
    (3,2,2) : [
        'UPSTREAM',
        'DOWNSTREAM',
        
        'HWM',
        'SWAP',
        'MCAST_LOOP',
        'RECOVERY_IVL_MSEC',
    ]
}

# collections of zmq constant names based on their role
# base names have no specific use
# opt names are validated in get/set methods of various objects

base_names = [
    # base
    'VERSION',
    'VERSION_MAJOR',
    'VERSION_MINOR',
    'VERSION_PATCH',
    'NOBLOCK',
    'DONTWAIT',

    'POLLIN',
    'POLLOUT',
    'POLLERR',
    
    'SNDMORE',

    'STREAMER',
    'FORWARDER',
    'QUEUE',

    'IO_THREADS_DFLT',
    'MAX_SOCKETS_DFLT',

    # socktypes
    'PAIR',
    'PUB',
    'SUB',
    'REQ',
    'REP',
    'DEALER',
    'ROUTER',
    'PULL',
    'PUSH',
    'XPUB',
    'XSUB',
    'UPSTREAM',
    'DOWNSTREAM',
    'STREAM',

    # events
    'EVENT_CONNECTED',
    'EVENT_CONNECT_DELAYED',
    'EVENT_CONNECT_RETRIED',
    'EVENT_LISTENING',
    'EVENT_BIND_FAILED',
    'EVENT_ACCEPTED',
    'EVENT_ACCEPT_FAILED',
    'EVENT_CLOSED',
    'EVENT_CLOSE_FAILED',
    'EVENT_DISCONNECTED',
    'EVENT_ALL',
    'EVENT_MONITOR_STOPPED',

    # security
    'NULL',
    'PLAIN',
    'CURVE',

    ## ERRNO
    # Often used (these are alse in errno.)
    'EAGAIN',
    'EINVAL',
    'EFAULT',
    'ENOMEM',
    'ENODEV',
    'EMSGSIZE',
    'EAFNOSUPPORT',
    'ENETUNREACH',
    'ECONNABORTED',
    'ECONNRESET',
    'ENOTCONN',
    'ETIMEDOUT',
    'EHOSTUNREACH',
    'ENETRESET',

    # For Windows compatability
    'HAUSNUMERO',
    'ENOTSUP',
    'EPROTONOSUPPORT',
    'ENOBUFS',
    'ENETDOWN',
    'EADDRINUSE',
    'EADDRNOTAVAIL',
    'ECONNREFUSED',
    'EINPROGRESS',
    'ENOTSOCK',

    # 0MQ Native
    'EFSM',
    'ENOCOMPATPROTO',
    'ETERM',
    'EMTHREAD',
]

int64_sockopt_names = [
    'AFFINITY',
    'MAXMSGSIZE',

    # sockopts removed in 3.0.0
    'HWM',
    'SWAP',
    'MCAST_LOOP',
    'RECOVERY_IVL_MSEC',
]

bytes_sockopt_names = [
    'IDENTITY',
    'SUBSCRIBE',
    'UNSUBSCRIBE',
    'LAST_ENDPOINT',
    'TCP_ACCEPT_FILTER',

    'PLAIN_USERNAME',
    'PLAIN_PASSWORD',

    'CURVE_PUBLICKEY',
    'CURVE_SECRETKEY',
    'CURVE_SERVERKEY',
    'ZAP_DOMAIN',
    'CONNECT_RID',
]

int_sockopt_names = [
    # sockopts
    'RECONNECT_IVL_MAX',

    # sockopts new in 2.2.0
    'SNDTIMEO',
    'RCVTIMEO',

    # new in 3.x
    'SNDHWM',
    'RCVHWM',
    'MULTICAST_HOPS',
    'IPV4ONLY',

    'ROUTER_BEHAVIOR',
    'TCP_KEEPALIVE',
    'TCP_KEEPALIVE_CNT',
    'TCP_KEEPALIVE_IDLE',
    'TCP_KEEPALIVE_INTVL',
    'DELAY_ATTACH_ON_CONNECT',
    'XPUB_VERBOSE',

    'FD',
    'EVENTS',
    'TYPE',
    'LINGER',
    'RECONNECT_IVL',
    'BACKLOG',
    
    'ROUTER_MANDATORY',
    'FAIL_UNROUTABLE',

    'ROUTER_RAW',
    'IMMEDIATE',
    'IPV6',
    'MECHANISM',
    'PLAIN_SERVER',
    'CURVE_SERVER',
    'PROBE_ROUTER',
    'REQ_RELAXED',
    'REQ_CORRELATE',
    'CONFLATE',
    'ROUTER_HANDOVER',
    'TOS',
    'IPC_FILTER_PID',
    'IPC_FILTER_UID',
    'IPC_FILTER_GID',
]

switched_sockopt_names = [
    'RATE',
    'RECOVERY_IVL',
    'SNDBUF',
    'RCVBUF',
    'RCVMORE',
]

ctx_opt_names = [
    'IO_THREADS',
    'MAX_SOCKETS',
]

msg_opt_names = [
    'MORE',
]

all_names = (
    base_names + ctx_opt_names + msg_opt_names +
    bytes_sockopt_names + int_sockopt_names + int64_sockopt_names + switched_sockopt_names
)

def no_prefix(name):
    """does the given constant have a ZMQ_ prefix?"""
    return name.startswith('E') and not name.startswith('EVENT')


########NEW FILE########
__FILENAME__ = garbage
"""Garbage collection thread for representing zmq refcount of Python objects
used in zero-copy sends.
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian E. Granger & Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import atexit
import struct

from os import getpid
from collections import namedtuple
from threading import Thread, Event, Lock
import warnings

import zmq

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

gcref = namedtuple('gcref', ['obj', 'event'])

class GarbageCollectorThread(Thread):
    """Thread in which garbage collection actually happens."""
    def __init__(self, gc):
        super(GarbageCollectorThread, self).__init__()
        self.gc = gc
        self.daemon = True
        self.pid = getpid()
        self.ready = Event()
    
    def run(self):
        s = self.gc.context.socket(zmq.PULL)
        s.linger = 0
        s.bind(self.gc.url)
        self.ready.set()
        
        while True:
            # detect fork
            if getpid is None or getpid() != self.pid:
                return
            msg = s.recv()
            if msg == b'DIE':
                break
            fmt = 'L' if len(msg) == 4 else 'Q'
            key = struct.unpack(fmt, msg)[0]
            tup = self.gc.refs.pop(key, None)
            if tup and tup.event:
                tup.event.set()
            del tup
        s.close()


class GarbageCollector(object):
    """PyZMQ Garbage Collector
    
    Used for representing the reference held by libzmq during zero-copy sends.
    This object holds a dictionary, keyed by Python id,
    of the Python objects whose memory are currently in use by zeromq.
    
    When zeromq is done with the memory, it sends a message on an inproc PUSH socket
    containing the packed size_t (32 or 64-bit unsigned int),
    which is the key in the dict.
    When the PULL socket in the gc thread receives that message,
    the reference is popped from the dict,
    and any tracker events that should be signaled fire.
    """
    
    refs = None
    _context = None
    _lock = None
    url = "inproc://pyzmq.gc.01"
    
    def __init__(self, context=None):
        super(GarbageCollector, self).__init__()
        self.refs = {}
        self.pid = None
        self.thread = None
        self._context = context
        self._lock = Lock()
        self._stay_down = False
        atexit.register(self._atexit)
    
    @property
    def context(self):
        if self._context is None:
            self._context = zmq.Context()
        return self._context
    
    @context.setter
    def context(self, ctx):
        if self.is_alive():
            if self.refs:
                warnings.warn("Replacing gc context while gc is running", RuntimeWarning)
            self.stop()
        self._context = ctx
    
    def _atexit(self):
        """atexit callback
        
        sets _stay_down flag so that gc doesn't try to start up again in other atexit handlers
        """
        self._stay_down = True
        self.stop()
    
    def stop(self):
        """stop the garbage-collection thread"""
        if not self.is_alive():
            return
        push = self.context.socket(zmq.PUSH)
        push.connect(self.url)
        push.send(b'DIE')
        push.close()
        self.thread.join()
        self.context.term()
        self.refs.clear()
    
    def start(self):
        """Start a new garbage collection thread.
        
        Creates a new zmq Context used for garbage collection.
        Under most circumstances, this will only be called once per process.
        """
        self.pid = getpid()
        self.refs = {}
        self.thread = GarbageCollectorThread(self)
        self.thread.start()
        self.thread.ready.wait()
    
    def is_alive(self):
        """Is the garbage collection thread currently running?
        
        Includes checks for process shutdown or fork.
        """
        if (getpid is None or
            getpid() != self.pid or
            self.thread is None or
            not self.thread.is_alive()
            ):
            return False
        return True
    
    def store(self, obj, event=None):
        """store an object and (optionally) event for zero-copy"""
        if not self.is_alive():
            if self._stay_down:
                return 0
            # safely start the gc thread
            # use lock and double check,
            # so we don't start multiple threads
            with self._lock:
                if not self.is_alive():
                    self.start()
        tup = gcref(obj, event)
        theid = id(tup)
        self.refs[theid] = tup
        return theid
    
    def __del__(self):
        if not self.is_alive():
            return
        try:
            self.stop()
        except Exception as e:
            raise (e)

gc = GarbageCollector()

########NEW FILE########
__FILENAME__ = interop
"""Utils for interoperability with other libraries.

Just CFFI pointer casting for now.
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2014 Brian E. Granger & Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------


try:
    long
except NameError:
    long = int # Python 3


def cast_int_addr(n):
    """Cast an address to a Python int
    
    This could be a Python integer or a CFFI pointer
    """
    if isinstance(n, (int, long)):
        return n
    try:
        import cffi
    except ImportError:
        pass
    else:
        # from pyzmq, this is an FFI void *
        ffi = cffi.FFI()
        if isinstance(n, ffi.CData):
            return int(ffi.cast("size_t", n))
    
    raise ValueError("Cannot cast %r to int" % n)

########NEW FILE########
__FILENAME__ = jsonapi
"""Priority based json library imports.

Always serializes to bytes instead of unicode for zeromq compatibility
on Python 2 and 3.

Use ``jsonapi.loads()`` and ``jsonapi.dumps()`` for guaranteed symmetry.

Priority: ``simplejson`` > ``jsonlib2`` > stdlib ``json``

``jsonapi.loads/dumps`` provide kwarg-compatibility with stdlib json.

``jsonapi.jsonmod`` will be the module of the actual underlying implementation.

Authors
-------
* MinRK
* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from zmq.utils.strtypes import bytes, unicode

jsonmod = None

priority = ['simplejson', 'jsonlib2', 'json']
for mod in priority:
    try:
        jsonmod = __import__(mod)
    except ImportError:
        pass
    else:
        break

def dumps(o, **kwargs):
    """Serialize object to JSON bytes (utf-8).
    
    See jsonapi.jsonmod.dumps for details on kwargs.
    """
    
    if 'separators' not in kwargs:
        kwargs['separators'] = (',', ':')
    
    s = jsonmod.dumps(o, **kwargs)
    
    if isinstance(s, unicode):
        s = s.encode('utf8')
    
    return s

def loads(s, **kwargs):
    """Load object from JSON bytes (utf-8).
    
    See jsonapi.jsonmod.loads for details on kwargs.
    """
    
    if str is unicode and isinstance(s, bytes):
        s = s.decode('utf8')
    
    return jsonmod.loads(s, **kwargs)

__all__ = ['jsonmod', 'dumps', 'loads']


########NEW FILE########
__FILENAME__ = monitor
# -*- coding: utf-8 -*-
"""Module holding utility and convenience functions for zmq event monitoring."""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Guido Goldstein, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import struct
import zmq
from zmq.error import _check_version

def parse_monitor_message(msg):
    """decode zmq_monitor event messages.
    
    Parameters
    ----------
    msg : list(bytes)
        zmq multipart message that has arrived on a monitor PAIR socket.
        
        First frame is::
        
            16 bit event id
            32 bit event value
            no padding

        Second frame is the endpoint as a bytestring

    Returns
    -------
    event : dict
        event description as dict with the keys `event`, `value`, and `endpoint`.
    """
    
    if len(msg) != 2 or len(msg[0]) != 6:
        raise RuntimeError("Invalid event message format: %s" % msg)
    event = {}
    event['event'], event['value'] = struct.unpack("=hi", msg[0])
    event['endpoint'] = msg[1]
    return event

def recv_monitor_message(socket, flags=0):
    """Receive and decode the given raw message from the monitoring socket and return a dict.

    Requires libzmq ≥ 4.0

    The returned dict will have the following entries:
      event     : int, the event id as described in libzmq.zmq_socket_monitor
      value     : int, the event value associated with the event, see libzmq.zmq_socket_monitor
      endpoint  : string, the affected endpoint
    
    Parameters
    ----------
    socket : zmq PAIR socket
        The PAIR socket (created by other.get_monitor_socket()) on which to recv the message
    flags : bitfield (int)
        standard zmq recv flags

    Returns
    -------
    event : dict
        event description as dict with the keys `event`, `value`, and `endpoint`.
    """
    _check_version((4,0), 'libzmq event API')
    # will always return a list
    msg = socket.recv_multipart(flags)
    # 4.0-style event API
    return parse_monitor_message(msg)

__all__ = ['parse_monitor_message', 'recv_monitor_message']

########NEW FILE########
__FILENAME__ = sixcerpt
"""Excerpts of six.py"""

# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys

# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

########NEW FILE########
__FILENAME__ = strtypes
"""Declare basic string types unambiguously for various Python versions.

Authors
-------
* MinRK
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2010-2012 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import sys

if sys.version_info[0] >= 3:
    bytes = bytes
    unicode = str
    basestring = (bytes, unicode)
else:
    unicode = unicode
    bytes = str
    basestring = basestring

def cast_bytes(s, encoding='utf8', errors='strict'):
    """cast unicode or bytes to bytes"""
    if isinstance(s, bytes):
        return s
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    else:
        raise TypeError("Expected unicode or bytes, got %r" % s)

def cast_unicode(s, encoding='utf8', errors='strict'):
    """cast bytes or unicode to unicode"""
    if isinstance(s, bytes):
        return s.decode(encoding, errors)
    elif isinstance(s, unicode):
        return s
    else:
        raise TypeError("Expected unicode or bytes, got %r" % s)

# give short 'b' alias for cast_bytes, so that we can use fake b('stuff')
# to simulate b'stuff'
b = asbytes = cast_bytes
u = cast_unicode

__all__ = ['asbytes', 'bytes', 'unicode', 'basestring', 'b', 'u', 'cast_bytes', 'cast_unicode']

########NEW FILE########
__FILENAME__ = z85
"""Python implementation of Z85 85-bit encoding

Z85 encoding is a plaintext encoding for a bytestring interpreted as 32bit integers.
Since the chunks are 32bit, a bytestring must be a multiple of 4 bytes.
See ZMQ RFC 32 for details.


"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2013 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

import sys
import struct

PY3 = sys.version_info[0] >= 3
# Z85CHARS is the base 85 symbol table
Z85CHARS = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#"
# Z85MAP maps integers in [0,84] to the appropriate character in Z85CHARS
Z85MAP = dict([(c, idx) for idx, c in enumerate(Z85CHARS)])

_85s = [ 85**i for i in range(5) ][::-1]

def encode(rawbytes):
    """encode raw bytes into Z85"""
    # Accepts only byte arrays bounded to 4 bytes
    if len(rawbytes) % 4:
        raise ValueError("length must be multiple of 4, not %i" % len(rawbytes))
    
    nvalues = len(rawbytes) / 4
    
    values = struct.unpack('>%dI' % nvalues, rawbytes)
    encoded = []
    for v in values:
        for offset in _85s:
            encoded.append(Z85CHARS[(v // offset) % 85])
    
    # In Python 3, encoded is a list of integers (obviously?!)
    if PY3:
        return bytes(encoded)
    else:
        return b''.join(encoded)

def decode(z85bytes):
    """decode Z85 bytes to raw bytes"""
    if len(z85bytes) % 5:
        raise ValueError("Z85 length must be multiple of 5, not %i" % len(z85bytes))
    
    nvalues = len(z85bytes) / 5
    values = []
    for i in range(0, len(z85bytes), 5):
        value = 0
        for j, offset in enumerate(_85s):
            value += Z85MAP[z85bytes[i+j]] * offset
        values.append(value)
    return struct.pack('>%dI' % nvalues, *values)

########NEW FILE########
__FILENAME__ = zmqversion
"""A simply script to scrape zmq.h for the zeromq version.
This is similar to the version.sh script in a zeromq source dir, but
it searches for an installed header, rather than in the current dir.
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2011 Brian Granger, Min Ragan-Kelley
#
#  This file is part of pyzmq
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file COPYING.BSD, distributed as part of this software.
#-----------------------------------------------------------------------------

from __future__ import with_statement

import os
import sys
import re
import traceback

from warnings import warn
try:
    from configparser import ConfigParser
except:
    from ConfigParser import ConfigParser

pjoin = os.path.join

MAJOR_PAT='^#define +ZMQ_VERSION_MAJOR +[0-9]+$'
MINOR_PAT='^#define +ZMQ_VERSION_MINOR +[0-9]+$'
PATCH_PAT='^#define +ZMQ_VERSION_PATCH +[0-9]+$'

def include_dirs_from_path():
    """Check the exec path for include dirs."""
    include_dirs = []
    for p in os.environ['PATH'].split(os.path.pathsep):
        if p.endswith('/'):
            p = p[:-1]
        if p.endswith('bin'):
            include_dirs.append(p[:-3]+'include')
    return include_dirs

def default_include_dirs():
    """Default to just /usr/local/include:/usr/include"""
    return ['/usr/local/include', '/usr/include']

def find_zmq_version():
    """check setup.cfg, then /usr/local/include, then /usr/include for zmq.h.
    Then scrape zmq.h for the version tuple.
    
    Returns
    -------
        ((major,minor,patch), "/path/to/zmq.h")"""
    include_dirs = []

    if os.path.exists('setup.cfg'):
        cfg = ConfigParser()
        cfg.read('setup.cfg')
        if 'build_ext' in cfg.sections():
            items = cfg.items('build_ext')
            for name,val in items:
                if name == 'include_dirs':
                    include_dirs = val.split(os.path.pathsep)

    if not include_dirs:
        include_dirs = default_include_dirs()
    
    for include in include_dirs:
        zmq_h = pjoin(include, 'zmq.h')
        if os.path.isfile(zmq_h):
            with open(zmq_h) as f:
                contents = f.read()
        else:
            continue
    
        line = re.findall(MAJOR_PAT, contents, re.MULTILINE)[0]
        major = int(re.findall('[0-9]+',line)[0])
        line = re.findall(MINOR_PAT, contents, re.MULTILINE)[0]
        minor = int(re.findall('[0-9]+',line)[0])
        line = re.findall(PATCH_PAT, contents, re.MULTILINE)[0]
        patch = int(re.findall('[0-9]+',line)[0])
        return ((major,minor,patch), zmq_h)
    
    raise IOError("Couldn't find zmq.h")

def ver_str(version):
    """version tuple as string"""
    return '.'.join(map(str, version))

def check_zmq_version(min_version):
    """Check that zmq.h has an appropriate version."""
    sv = ver_str(min_version)
    try:
        found, zmq_h = find_zmq_version()
        sf = ver_str(found)
        if found < min_version:
            print ("This pyzmq requires zeromq >= %s"%sv)
            print ("but it appears you are building against %s"%zmq_h)
            print ("which has zeromq %s"%sf)
            sys.exit(1)
    except IOError:
        msg = '\n'.join(["Couldn't find zmq.h to check for version compatibility.",
        "If you see 'undeclared identifier' errors, your ZeroMQ is likely too old.",
        "This pyzmq requires zeromq >= %s"%sv])
        warn(msg)
    except IndexError:
        msg = '\n'.join(["Couldn't find ZMQ_VERSION macros in zmq.h to check for version compatibility.",
        "This probably means that you have ZeroMQ <= 2.0.9",
        "If you see 'undeclared identifier' errors, your ZeroMQ is likely too old.",
        "This pyzmq requires zeromq >= %s"%sv])
        warn(msg)
    except Exception:
        traceback.print_exc()
        msg = '\n'.join(["Unexpected Error checking for zmq version.",
        "If you see 'undeclared identifier' errors, your ZeroMQ is likely too old.",
        "This pyzmq requires zeromq >= %s"%sv])
        warn(msg)

if __name__ == '__main__':
    v,h = find_zmq_version()
    print (h)
    print (ver_str(v))



########NEW FILE########
