__FILENAME__ = blaze
#!/usr/bin/env python

"""
Blaze REPL.
"""

import os
import sys
import code
import atexit
import logging
import readline
import warnings
import functools

# pop directory from sys.path so that we can import blaze instead of
# importing this module again
sys.path.pop(0)

import blaze
from blaze import array, eval
from datashape import (dshape, dshapes, unify_simple as unify,
                       normalize_ellipses as normalize,
                       promote, tmap, coercion_cost, typeof)

logging.getLogger('blaze').setLevel(logging.DEBUG)

banner = """
The Blaze typing interpreter.

    blaze:
        blaze module

    dshape('<type string>'):
        parse a blaze type

    dshapes('<type string1>', ..., '<type string N>')
        parse a series of blaze types in the same context, so they will
        shared type variables of equal name.

    typeof(val)
        Return a blaze DataShape for a python object

    unify(t1, t2):
        unify t1 with t2, and return a result type and a list of additional
        constraints

    promote(t1, t2):
        promote two blaze types to a common type general enough to represent
        values of either type

    normalize_ellipses(ds1, ds2):
        normalize_ellipses takes two datashapes for unification (ellipses, broadcasting)

    coercion_cost(t1, t2):
        Determine a coercion cost for coercing type t1 to type t2

    tmap(f, t):
        map function `f` over type `t` and its sub-terms post-order

    array(obj, dshape=None, storage=None)
        Create a blaze array from the given object and data shape

    eval(arr, storage=None)
        Evaluate a blaze expression
"""

eval = functools.partial(eval, debug=True)

env = {
    'blaze':     blaze,
    'dshape':    dshape,
    'dshapes':   dshapes,
    'typeof':    typeof,
    'unify':     unify,
    'promote':   promote,
    'normalize_ellipses': normalize,
    'coercion_cost': coercion_cost,
    'tmap':      tmap,
    'array':     array,
    'eval':      eval,
}


def init_readline():
    readline.parse_and_bind('tab: menu-complete')
    histfile = os.path.expanduser('~/.blaze_history%s' % sys.version[:3])
    atexit.register(readline.write_history_file, histfile)
    if not os.path.exists(histfile):
        open(histfile, 'w').close()
    readline.read_history_file(histfile)


def main():
    init_readline()
    try:
        import fancycompleter
        print(banner)
        fancycompleter.interact(persist_history=True)
    except ImportError:
        warnings.warn("fancycompleter not installed")
        interp = code.InteractiveConsole(env)
        interp.interact(banner)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = array_provider
from __future__ import absolute_import, division, print_function

import os
from os import path
import glob
import shutil
import tempfile

from dynd import nd, ndt

from .. import array


def load_json_file_array(root, array_name):
    # Load the datashape
    dsfile = root + '.datashape'
    if not path.isfile(dsfile):
        dsfile = path.dirname(root) + '.datashape'
        if not path.isfile(dsfile):
            raise Exception('No datashape file found for array %s'
                            % array_name)
    with open(dsfile) as f:
        dt = ndt.type(f.read())

    # Load the JSON
    # TODO: Add stream support to parse_json for compressed JSON, etc.
    arr = nd.parse_json(dt, nd.memmap(root + '.json'))
    return array(arr)


def load_json_directory_array(root, array_name):
    # Load the datashape
    dsfile = root + '.datashape'
    if not path.isfile(dsfile):
        raise Exception('No datashape file found for array %s' % array_name)
    with open(dsfile) as f:
        dt = ndt.type(f.read())

    # Scan for JSON files, assuming they're just #.json
    # Sort them numerically
    files = sorted([(int(path.splitext(path.basename(x))[0]), x)
                    for x in glob.glob(path.join(root, '*.json'))])
    files = [x[1] for x in files]
    # Make an array with an extra fixed dimension, then
    # read a JSON file into each element of that array
    dt = ndt.make_fixed_dim(len(files), dt)
    arr = nd.empty(dt)
    for i, fname in enumerate(files):
        nd.parse_json(arr[i], nd.memmap(fname))
    arr.flag_as_immutable()
    return array(arr)


def load_json_file_list_array(root, array_name):
    # Load the datashape
    dsfile = root + '.datashape'
    if not path.isfile(dsfile):
        raise Exception('No datashape file found for array %s' % array_name)
    with open(dsfile) as f:
        dt = ndt.type(f.read())

    # Scan for JSON files -- no assumption on file suffix

    #open list of files and load into python list
    files = root + '.files'
    with open(files) as f:
        l_files = [fs.strip() for fs in f]

    # Make an array with an extra fixed dimension, then
    # read a JSON file into each element of that array
    dt = ndt.make_fixed_dim(len(l_files), dt)
    arr = nd.empty(dt)
    for i, fname in enumerate(l_files):
        with open(fname) as f:
            nd.parse_json(arr[i], f.read())
    arr.flag_as_immutable()
    return array(arr)


class json_array_provider:
    def __init__(self, root_dir):
        if not path.isdir(root_dir):
            raise ValueError('%s is not a valid directory' % root_dir)
        self.root_dir = root_dir
        self.array_cache = {}
        self.session_dirs = {}

    def __call__(self, array_name):
        # First check that the .json file at the requested address exists
        root = path.join(self.root_dir, array_name[1:])
        if (not path.isfile(root + '.json') and
                 not path.isfile(root + '.deferred.json') and
                 not path.isfile(root + '.files') and
                 not path.isdir(root)):
            return None

        # If we've already read this array into cache, just return it
        print('Cache has keys %s' % self.array_cache.keys())
        print('Checking cache for %s' % array_name)
        if array_name in self.array_cache:
            print('Returning cached array %s' % array_name)
            return self.array_cache[array_name]

        if path.isfile(root + '.json'):
            print('Loading array %s from file %s'
                  % (array_name, root + '.json'))
            arr = load_json_file_array(root, array_name)
        elif path.isfile(root + '.deferred.json'):
            print('Loading deferred array %s from file %s'
                  % (array_name, root + '.deferred.json'))
            with open(root + '.deferred.json') as f:
                print(f.read())
            raise RuntimeError('TODO: Deferred loading not implemented!')
        elif path.isfile(root + '.files'):
            print('Loading files from file list: %s' % (root + '.files'))
            arr = load_json_file_list_array(root, array_name)
        else:
            print('Loading array %s from directory %s' % (array_name, root))
            arr = load_json_directory_array(root, array_name)

        self.array_cache[array_name] = arr
        return arr

    def create_session_dir(self):
        d = tempfile.mkdtemp(prefix='.session_', dir=self.root_dir)
        session_name = '/' + os.path.basename(d)
        if type(session_name) is unicode:
            session_name = session_name.encode('utf-8')
        self.session_dirs[session_name] = d
        return session_name, d

    def delete_session_dir(self, session_name):
        shutil.rmtree(self.session_dirs[session_name])
        del self.session_dirs[session_name]

    def create_deferred_array_filename(self, session_name,
                                       prefix, cache_array):
        d = tempfile.mkstemp(suffix='.deferred.json', prefix=prefix,
                             dir=self.session_dirs[session_name], text=True)
        array_name = os.path.basename(d[1])
        array_name = session_name + '/' + array_name[:array_name.find('.')]
        if type(array_name) is unicode:
            array_name = array_name.encode('utf-8')

        if cache_array is not None:
            self.array_cache[array_name] = cache_array

        return (os.fdopen(d[0], "w"), array_name, d[1])

########NEW FILE########
__FILENAME__ = blaze_url
from __future__ import absolute_import, division, print_function

__all__ = ['split_array_base', 'add_indexers_to_url', 'slice_as_string',
           'index_tuple_as_string']

from pyparsing import (Word, Regex, Optional, ZeroOrMore,
                       StringStart, StringEnd, alphas, alphanums)
from ..py2help import _strtypes, _inttypes

# Parser to match the Blaze URL syntax
intNumber = Regex(r'[-+]?\b\d+\b')
arrayName = Regex(r'(/(\.session_)?\w*)*[a-zA-Z0-9_]+\b')
bracketsIndexer = (Optional(intNumber) +
                   Optional(':' + Optional(intNumber)) +
                   Optional(':' + Optional(intNumber)))
indexerPattern = (('.' + Word(alphas + '_', alphanums + '_')) ^
                  ('[' + bracketsIndexer +
                   ZeroOrMore(',' + bracketsIndexer) + ']'))
arrayBase = (StringStart() +
             arrayName + ZeroOrMore(indexerPattern) +
             StringEnd())


def split_array_base(array_base):
    pieces = arrayBase.parseString(array_base)
    array_name = pieces[0]
    indexers = []
    i = 1
    while i < len(pieces):
        # Convert [...] into an int, a slice, or a tuple of int/slice
        if pieces[i] == '[':
            i += 1
            ilist = []
            while pieces[i-1] != ']':
                if pieces[i] != ':':
                    first = int(pieces[i])
                    i += 1
                else:
                    first = None
                if pieces[i] in [',', ']']:
                    i += 1
                    ilist.append(first)
                else:
                    i += 1
                    if pieces[i] not in [',', ':', ']']:
                        second = int(pieces[i])
                        i += 1
                    else:
                        second = None
                    if pieces[i] in [',', ']']:
                        i += 1
                        ilist.append(slice(first, second))
                    else:
                        i += 1
                        if pieces[i] not in [',', ']']:
                            third = int(pieces[i])
                            i += 1
                        else:
                            third = 1
                        ilist.append(slice(first, second, third))
                        i += 2
            if len(ilist) == 1:
                indexers.append(ilist[0])
            else:
                indexers.append(tuple(ilist))
        elif pieces[i] == '.':
            i += 1
        else:
            indexers.append(pieces[i])
            i += 1

    return array_name, indexers


def slice_as_interior_string(s):
    if type(s) is int:
        return str(s)
    else:
        result = ''
        if s.start is not None:
            result += str(s.start)
        result += ':'
        if s.stop is not None:
            result += str(s.stop)
        if s.step is not None and s.step != 1:
            result += ':' + str(s.step)
        return result


def slice_as_string(s):
    return '[' + slice_as_interior_string(s) + ']'


def index_tuple_as_string(s):
    result = '[' + slice_as_interior_string(s[0])
    for i in s[1:]:
        result += ',' + slice_as_interior_string(i)
    result += ']'
    return result


def add_indexers_to_url(base_url, indexers):
    for idx in indexers:
        if isinstance(idx, _strtypes):
            base_url += '.' + idx
        elif isinstance(idx, _inttypes):
            base_url += '[' + str(idx) + ']'
        elif isinstance(idx, slice):
            base_url += slice_as_string(idx)
        elif isinstance(idx, tuple):
            base_url += index_tuple_as_string(idx)
        else:
            raise IndexError('Cannot process index object %r' % idx)
    return base_url

########NEW FILE########
__FILENAME__ = catalog_arr
from __future__ import absolute_import, division, print_function

from os import path
import csv

import yaml
from dynd import nd, ndt
import datashape
from datashape.type_equation_solver import matches_datashape_pattern

import blaze
from .. import py2help


def load_blaze_array(conf, dir):
    """Loads a blaze array from the catalog configuration and catalog path"""
    # This is a temporary hack, need to transition to using the
    # deferred data descriptors for various formats.
    fsdir = conf.get_fsdir(dir)
    if not path.isfile(fsdir + '.array'):
        raise RuntimeError('Could not find blaze array description file %r'
                           % (fsdir + '.array'))
    with open(fsdir + '.array') as f:
        arrmeta = yaml.load(f)
    tp = arrmeta['type']
    imp = arrmeta['import']
    ds_str = arrmeta.get('datashape')  # optional. HDF5 does not need that.

    if tp == 'csv':
        with open(fsdir + '.csv', 'r') as f:
            rd = csv.reader(f)
            if imp.get('headers', False):
                # Skip the header line
                next(rd)
            dat = list(rd)
        arr = nd.array(dat, ndt.type(ds_str))[:]
        return blaze.array(arr)
    elif tp == 'json':
        arr = nd.parse_json(ds_str, nd.memmap(fsdir + '.json'))
        return blaze.array(arr)
    elif tp == 'hdf5':
        import tables as tb
        from blaze.datadescriptor import HDF5_DDesc
        fname = fsdir + '.h5'   # XXX .h5 assumed for HDF5
        with tb.open_file(fname, 'r') as f:
            dp = imp.get('datapath')  # specifies a path in HDF5
            try:
                dparr = f.get_node(f.root, dp, 'Leaf')
            except tb.NoSuchNodeError:
                raise RuntimeError(
                    'HDF5 file does not have a dataset in %r' % dp)
            dd = HDF5_DDesc(fname, dp)
        return blaze.array(dd)
    elif tp == 'npy':
        import numpy as np
        use_memmap = imp.get('memmap', False)
        if use_memmap:
            arr = np.load(fsdir + '.npy', 'r')
        else:
            arr = np.load(fsdir + '.npy')
        arr = nd.array(arr)
        arr = blaze.array(arr)
        ds = datashape.dshape(ds_str)
        if not matches_datashape_pattern(arr.dshape, ds):
            raise RuntimeError(('NPY file for blaze catalog path %r ' +
                                'has the wrong datashape (%r instead of ' +
                                '%r)') % (arr.dshape, ds))
        return arr
    elif tp == 'py':
        ds = datashape.dshape(ds_str)
        # The script is run with the following globals,
        # and should put the loaded array in a global
        # called 'result'.
        gbl = {'catconf': conf,  # Catalog configuration object
               'impdata': imp,   # Import data from the .array file
               'catpath': dir,   # Catalog path
               'fspath': fsdir,  # Equivalent filesystem path
               'dshape': ds      # Datashape the result should have
               }
        if py2help.PY2:
            execfile(fsdir + '.py', gbl, gbl)
        else:
            with open(fsdir + '.py') as f:
                code = compile(f.read(), fsdir + '.py', 'exec')
                exec(code, gbl, gbl)
        arr = gbl.get('result', None)
        if arr is None:
            raise RuntimeError(('Script for blaze catalog path %r did not ' +
                                'return anything in "result" variable')
                               % (dir))
        elif not isinstance(arr, blaze.Array):
            raise RuntimeError(('Script for blaze catalog path %r returned ' +
                                'wrong type of object (%r instead of ' +
                                'blaze.Array)') % (type(arr)))
        if not matches_datashape_pattern(arr.dshape, ds):
            raise RuntimeError(('Script for blaze catalog path %r returned ' +
                                'array with wrong datashape (%r instead of ' +
                                '%r)') % (arr.dshape, ds))
        return arr
    else:
        raise ValueError(('Unsupported array type %r from ' +
                          'blaze catalog entry %r')
                         % (tp, dir))

def load_blaze_subcarray(conf, cdir, subcarray):
    import tables as tb
    from blaze.datadescriptor import HDF5_DDesc
    with tb.open_file(cdir.fname, 'r') as f:
        try:
            dparr = f.get_node(f.root, subcarray, 'Leaf')
        except tb.NoSuchNodeError:
            raise RuntimeError(
                'HDF5 file does not have a dataset in %r' % dp)
        dd = HDF5_DDesc(cdir.fname, subcarray)
    return blaze.array(dd)
    

########NEW FILE########
__FILENAME__ = catalog_config
from __future__ import absolute_import, division, print_function

import yaml
import os
from os import path
from .catalog_dir import is_abs_bpath, CatalogCDir


class CatalogConfig(object):
    """This object stores a catalog configuration.
    """
    def __init__(self, catconfigfile):
        try:
            catconfigfile = path.abspath(catconfigfile)
            self.configfile = catconfigfile
            with open(catconfigfile) as f:
                cfg = yaml.load(f)
            if not isinstance(cfg, dict):
                raise RuntimeError(('Blaze catalog config file "%s" is ' +
                                    'not valid') % catconfigfile)
            self.root = cfg.pop('root')
            # Allow ~/...
            self.root = path.expanduser(self.root)
            # For paths that are not absolute, make them relative
            # to the config file, so a catalog + config can
            # be easily relocatable.
            if not path.isabs(self.root):
                self.root = path.join(path.dirname(catconfigfile), self.root)
            self.root = path.abspath(self.root)

            if not path.exists(self.root):
                raise RuntimeError(('Root Blaze catalog dir "%s" ' +
                                    'from config file "%s" does not exist')
                                   % (self.root, catconfigfile))

            if len(cfg) != 0:
                raise KeyError('Extra Blaze catalog config options: %s'
                               % cfg.keys())
        except KeyError as e:
            raise KeyError('Missing Blaze catalog config option: %s' % e)

    def get_fsdir(self, dir):
        """Return the filesystem path of the blaze catalog path"""
        if is_abs_bpath(dir):
            return path.join(self.root, dir[1:])
        else:
            raise ValueError('Expected absolute blaze catalog path: %r' % dir)

    def isarray(self, dir):
        """Check if a blaze catalog path points to an existing array"""
        if is_abs_bpath(dir):
            return path.isfile(path.join(self.root, dir[1:]) + '.array')
        else:
            raise ValueError('Expected absolute blaze catalog path: %r' % dir)

    def isdir(self, dir):
        """Check if a blaze catalog path points to an existing directory"""
        if is_abs_bpath(dir):
            return self._isdir(dir) or self._iscdir(dir)
        else:
            raise ValueError('Expected absolute blaze catalog path: %r' % dir)

    def _isdir(self, dir):
        """Check if a blaze catalog path points to an existing directory"""
        return path.isdir(path.join(self.root, dir[1:]))

    def _iscdir(self, dir):
        """Check if a blaze catalog path points to an existing cdir"""
        return path.isfile(path.join(self.root, dir[1:]) + '.dir')

    def get_subcdir(self, dir):
        """Check if a blaze catalog path points to an existing cdir or subcdir.

           If the path exists in catalog, a tuple to the `cdir` and
           `subcdir` are returned.  If not, a (None, None) is returned
           instead.
        """
        # Build all the possible paths in `dir`
        paths = ['/']
        for p in dir[1:].split('/'):
            paths.append(path.join(paths[-1], p))
        # Check if any of these paths contains a cdir
        for p in paths[1:]:
            dir2 = path.join(self.root, p)
            if self._iscdir(p):
                # Bingo!  Now, let's see if we can find the subcdir there
                if p == dir:
                    # The cdir is the root, return it
                    return (p, '/')
                cdir = CatalogCDir(self, p)
                subcdir = dir[len(p):]
                if subcdir in cdir.ls_abs('Group'):
                    return (p, subcdir)
                else:
                    return (None, None)
        return (None, None)
                    
    def get_subcarray(self, dir):
        """Check if an array path is inside a cdir.

           If the path exists in catalog, a tuple to the `cdir` and
           `subcarray` are returned.  If not, a (None, None) is
           returned instead.
        """
        # Build all the possible paths in `dir`
        paths = ['/']
        for p in dir[1:].split('/'):
            paths.append(path.join(paths[-1], p))
        # Check if any of these paths contains a cdir
        for p in paths[1:]:
            dir2 = path.join(self.root, p)
            if self._iscdir(p):
                # Bingo!  Now, let's see if we can find the subcarray there
                cdir = CatalogCDir(self, p)
                subcarray = dir[len(p):]
                if subcarray in cdir.ls_abs('Leaf'):
                    return (p, subcarray)
                else:
                    return (None, None)
        return (None, None)
                    
    def ls_arrs(self, dir):
        """Return a list of all the arrays in the provided blaze catalog dir"""
        if is_abs_bpath(dir):
            if self._iscdir(dir):
                cdir = CatalogCDir(self, dir)
                return sorted(cdir.ls_arrs())
            (cdir, subcdir) = self.get_subcdir(dir)
            if cdir or subcdir:
                cdir = CatalogCDir(self, cdir, subcdir)
                return sorted(cdir.ls_arrs())
            fsdir = path.join(self.root, dir[1:])
            listing = os.listdir(fsdir)
            res = [path.splitext(x)[0] for x in listing
                    if x.endswith('.array')]
            return sorted(res)
        else:
            raise ValueError('Expected absolute blaze catalog path: %r' % dir)

    def ls_dirs(self, dir):
        """
        Return a list of all the directories in the provided
        blaze catalog dir
        """
        if is_abs_bpath(dir):
            cdirs = []
            # First check if dir is a catalog directory (HDF5) itself
            (cdir, subcdir) = self.get_subcdir(dir)
            if cdir and subcdir:
                cdir = CatalogCDir(self, cdir, subcdir)
                return sorted(cdir.ls_dirs())
            # Now, the regular filesystem directories
            fsdir = path.join(self.root, dir[1:])
            listing = os.listdir(fsdir)
            res = [x for x in listing
                   if path.isdir(path.join(fsdir, x))]
            # Finally, check for .dir files, which act as catalog directories
            res += [x[:-4] for x in listing
                   if self.isdir(path.join(dir, x[:-4]))]
            return sorted(cdirs + res)
        else:
            raise ValueError('Expected absolute blaze catalog path: %r' % dir)

    def ls(self, dir):
        """Return a list of all the arrays and directories in the provided
           blaze catalog dir
           """
        if is_abs_bpath(dir):
            if self._iscdir(dir):
                cdir = CatalogCDir(self, dir)
                return sorted(cdir.ls())
            (cdir, subcdir) = self.get_subcdir(dir)
            if cdir or subcdir:
                cdir = CatalogCDir(self, cdir, subcdir)
                return sorted(cdir.ls())
            fsdir = path.join(self.root, dir[1:])
            listing = os.listdir(fsdir)
            res = [path.splitext(x)[0] for x in listing
                   if x.endswith('.array')]
            res += [x for x in listing
                    if path.isdir(path.join(fsdir, x))]
            return sorted(res)
        else:
            raise ValueError('Expected absolute blaze catalog path: %r' % dir)

    def __repr__(self):
        return ("Blaze Catalog Configuration\n%s\n\nroot: %s"
                % (self.configfile, self.root))


def load_default_config(create_default=False):
    dcf = path.expanduser('~/.blaze/catalog.yaml')
    if not path.exists(dcf):
        if create_default:
            # If requested explicitly, create a default configuration
            if not path.exists(path.dirname(dcf)):
                os.mkdir(path.dirname(dcf))
            with open(dcf, 'w') as f:
                f.write("### Blaze Catalog Configuration File\n")
                f.write("root: Arrays\n")
            arrdir = path.expanduser('~/.blaze/Arrays')
            if not path.exists(arrdir):
                os.mkdir(arrdir)
        else:
            return None
    elif create_default:
        import warnings
        warnings.warn("Default catalog configuration already exists",
                      RuntimeWarning)
    return CatalogConfig(dcf)

########NEW FILE########
__FILENAME__ = catalog_dir
from __future__ import absolute_import, division, print_function

from os import path
import yaml
from .catalog_arr import load_blaze_array


def is_valid_bpath(d):
    """Returns true if it's a valid blaze path"""
    # Disallow backslashes in blaze paths
    if '\\' in d:
        return False
    # There should not be multiple path separators in a row
    if '//' in d:
        return False
    return True


def is_abs_bpath(d):
    """Returns true if it's an absolute blaze path"""
    return is_valid_bpath(d) and d.startswith('/')


def is_rel_bpath(d):
    """Returns true if it's a relative blaze path"""
    return is_valid_bpath(d) and not d.startswith('/')


def _clean_bpath_components(components):
    res = []
    for c in components:
        if c == '.':
            # Remove '.'
            pass
        elif c == '..':
            if all(x == '..' for x in res):
                # Relative path starting with '..'
                res.append('..')
            elif res == ['']:
                # Root of absolute path
                raise ValueError('Cannot use ".." at root of blaze catalog')
            else:
                # Remove the last entry
                res.pop()
        else:
            res.append(c)
    return res


def _split_bpath(d):
    if is_valid_bpath(d):
        if d == '':
            return []
        elif d == '/':
            return ['']
        elif d.endswith('/'):
            d = d[:-1]
        return d.split('/')
    else:
        raise ValueError('Invalid blaze catalog path %r' % d)


def _rejoin_bpath(components):
    if components == ['']:
        return '/'
    else:
        return '/'.join(components)


def clean_bpath(d):
    if is_valid_bpath(d):
        components = _split_bpath(d)
        components = _clean_bpath_components(components)
        return _rejoin_bpath(components)
    else:
        raise ValueError('Invalid blaze catalog path %r' % d)


def join_bpath(d1, d2):
    if is_abs_bpath(d2):
        return clean_bpath(d2)
    elif is_abs_bpath(d1):
        components = _split_bpath(d1) + _split_bpath(d2)
        components = _clean_bpath_components(components)
        return _rejoin_bpath(components)


class CatalogDir(object):
    """This object represents a directory path within the blaze catalog"""
    def __init__(self, conf, dir):
        self.conf = conf
        self.dir = dir
        if not is_abs_bpath(dir):
            raise ValueError('Require an absolute blaze path: %r' % dir)
        self._fsdir = path.join(conf.root, dir[1:])
        if not path.exists(self._fsdir) or not path.isdir(self._fsdir):
            raise RuntimeError('Blaze path not found: %r' % dir)

    def ls_arrs(self):
        """Return a list of all the arrays in this blaze dir"""
        return self.conf.ls_arrs(self.dir)

    def ls_dirs(self):
        """Return a list of all the directories in this blaze dir"""
        return self.conf.ls_dirs(self.dir)

    def ls(self):
        """
        Returns a list of all the arrays and directories in this blaze dir
        """
        return self.conf.ls(self.dir)

    def __getindex__(self, key):
        if isinstance(key, tuple):
            key = '/'.join(key)
        if not is_rel_bpath(key):
            raise ValueError('Require a relative blaze path: %r' % key)
        dir = '/'.join([self.dir, key])
        fsdir = path.join(self._fsdir, dir)
        if path.isdir(fsdir):
            return CatalogDir(self.conf, dir)
        elif path.isfile(fsdir + '.array'):
            return load_blaze_array(self.conf, dir)
        else:
            raise RuntimeError('Blaze path not found: %r' % dir)

    def __repr__(self):
        return ("Blaze Catalog Directory\nconfig: %s\ndir: %s"
                % (self.conf.configfile, self.dir))


class CatalogCDir(CatalogDir):
    """This object represents a directory path within a special catalog"""
    def __init__(self, conf, dir, subdir='/'):
        self.conf = conf
        self.dir = dir
        self.subdir = subdir
        if not is_abs_bpath(dir):
            raise ValueError('Require a path to dir file: %r' % dir)
        self._fsdir = path.join(conf.root, dir[1:])
        if not path.exists(self._fsdir + '.dir'):
            raise RuntimeError('Blaze path not found: %r' % dir)
        self.load_blaze_dir()

    def load_blaze_dir(self):
        fsdir = self.conf.get_fsdir(self.dir)
        with open(fsdir + '.dir') as f:
            dirmeta = yaml.load(f)
        self.ctype = dirmeta['type']
        imp = dirmeta['import']
        self.fname = imp.get('filename')

    def ls_arrs(self):
        """Return a list of all the arrays in this blaze dir"""
        if self.ctype == "hdf5":
            import tables as tb
            with tb.open_file(self.fname, 'r') as f:
                leafs = [l._v_name for l in
                         f.iter_nodes(self.subdir, classname='Leaf')]
            return sorted(leafs)

    def ls_dirs(self):
        """Return a list of all the directories in this blaze dir"""
        if self.ctype == "hdf5":
            import tables as tb
            with tb.open_file(self.fname, 'r') as f:
                groups = [g._v_name for g in 
                          f.iter_nodes(self.subdir, classname='Group')]
            return sorted(groups)

    def ls(self):
        """
        Returns a list of all the arrays and directories in this blaze dir
        """
        if self.ctype == "hdf5":
            import tables as tb
            with tb.open_file(self.fname, 'r') as f:
                nodes = [n._v_name for n in
                         f.iter_nodes(self.subdir)]
            return sorted(nodes)

    def ls_abs(self, cname=''):
        """
        Returns a list of all the directories in this blaze dir
        """
        if self.ctype == "hdf5":
            import tables as tb
            with tb.open_file(self.fname, 'r') as f:
                nodes = [n._v_pathname for n in
                         f.walk_nodes(self.subdir, classname=cname)]
            return sorted(nodes)

    def __getindex__(self, key):
        # XXX Adapt this to HDF5
        if isinstance(key, tuple):
            key = '/'.join(key)
        if not is_rel_bpath(key):
            raise ValueError('Require a relative blaze path: %r' % key)
        dir = '/'.join([self.dir, key])
        fsdir = path.join(self._fsdir, dir)
        if path.isfile(fsdir + '.dir'):
            return CatalogCDir(self.conf, dir)
        elif path.isfile(fsdir + '.array'):
            return load_blaze_array(self.conf, dir)
        else:
            raise RuntimeError('Blaze path not found: %r' % dir)

########NEW FILE########
__FILENAME__ = catalog_harness
"""
Some functions to create/tear down a simple catalog
for tests to use.
"""
from __future__ import absolute_import, division, print_function

import tempfile
import os
import shutil

import numpy as np

from dynd import nd
from blaze.optional_packages import tables_is_here


class CatalogHarness(object):
    def __init__(self):
        self.catdir = tempfile.mkdtemp()
        self.arrdir = os.path.join(self.catdir, 'arrays')
        os.mkdir(self.arrdir)
        self.catfile = os.path.join(self.catdir, 'testcat.yaml')
        with open(self.catfile, 'w') as f:
            f.write('# Temporary catalog for Blaze testing\n')
            f.write('root: ./arrays\n')
        # Create arrays with various formats at the top level
        self.create_csv('csv_arr')
        if tables_is_here:
            self.create_hdf5('hdf5')
        self.create_npy('npy_arr')
        self.create_py('py_arr')
        self.create_json('json_arr')
        # Create an array in a subdirectory
        os.mkdir(os.path.join(self.arrdir, 'subdir'))
        self.create_csv('subdir/csv_arr2')

    def close(self):
        shutil.rmtree(self.catdir)

    def create_csv(self, name):
        with open(os.path.join(self.arrdir, '%s.csv' % name), 'w') as f:
            f.write('Letter, Number\n')
            f.write('alpha, 0\n')
            f.write('beta, 1\n')
            f.write('gamma, 2\n')
            f.write('delta, 3\n')
            f.write('epsilon, 4\n')
        with open(os.path.join(self.arrdir, '%s.array' % name), 'w') as f:
            f.write('type: csv\n')
            f.write('import: {\n')
            f.write('    headers: True\n')
            f.write('}\n')
            f.write('datashape: |\n')
            f.write('    var * {\n')
            f.write('        Letter: string,\n')
            f.write('        Number: int32,\n')
            f.write('    }\n')

    def create_json(self, name):
        a = nd.array([[1, 2, 3], [1, 2]])
        with open(os.path.join(self.arrdir, '%s.json' % name), 'w') as f:
            f.write(nd.as_py(nd.format_json(a)))
        with open(os.path.join(self.arrdir, '%s.array' % name), 'w') as f:
            f.write('type: json\n')
            f.write('import: {}\n')
            f.write('datashape: "var * var * int32"\n')

    def create_hdf5(self, name):
        import tables as tb
        a1 = nd.array([[1, 2, 3], [4, 5, 6]], dtype="int32")
        a2 = nd.array([[1, 2, 3], [3, 2, 1]], dtype="int32")
        a3 = nd.array([[1, 3, 2], [2, 1, 3]], dtype="int32")
        fname = os.path.join(self.arrdir, '%s_arr.h5' % name)
        with tb.open_file(fname, 'w') as f:
            f.create_array(f.root, "a1", nd.as_numpy(a1))
            mg = f.create_group(f.root, "mygroup")
            f.create_array(mg, "a2", nd.as_numpy(a2))
            f.create_array(mg, "a3", nd.as_numpy(a3))
            mg2 = f.create_group(mg, "mygroup2")
        # Create a .array file for locating the dataset inside the file
        with open(os.path.join(self.arrdir, '%s_arr.array' % name), 'w') as f:
            f.write('type: hdf5\n')
            f.write('import: {\n')
            f.write('    datapath: /mygroup/a2\n')
            f.write('    }\n')
        # Create a .dir file for listing datasets inside the file
        with open(os.path.join(self.arrdir, '%s_dir.dir' % name), 'w') as f:
            f.write('type: hdf5\n')
            f.write('import: {\n')
            f.write('    filename: "%s"\n' % fname.replace('\\', '\\\\'))
            f.write('    }\n')

    def create_npy(self, name):
        a = np.empty(20, dtype=[('idx', np.int32), ('val', 'S4')])
        a['idx'] = np.arange(20)
        a['val'] = ['yes', 'no'] * 10
        np.save(os.path.join(self.arrdir, '%s.npy' % name), a)
        with open(os.path.join(self.arrdir, '%s.array' % name), 'w') as f:
            f.write('type: npy\n')
            f.write('import: {}\n')
            f.write('datashape: |\n')
            f.write('    M * {\n')
            f.write('        idx: int32,\n')
            f.write('        val: string,\n')
            f.write('    }\n')

    def create_py(self, name):
        with open(os.path.join(self.arrdir, '%s.py' % name), 'w') as f:
            f.write('import blaze\n')
            f.write('result = blaze.array([1, 2, 3, 4, 5])\n')
        with open(os.path.join(self.arrdir, '%s.array' % name), 'w') as f:
            f.write('type: py\n')
            f.write('import: {}\n')
            f.write('datashape: "5 * int32"\n')

########NEW FILE########
__FILENAME__ = test_catalog
from __future__ import absolute_import, division, print_function

import unittest

import datashape
import blaze
from blaze.optional_packages import tables_is_here
from blaze.catalog.tests.catalog_harness import CatalogHarness
from blaze.py2help import skipIf


class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.cat = CatalogHarness()
        blaze.catalog.load_config(self.cat.catfile)

    def tearDown(self):
        blaze.catalog.load_default()
        self.cat.close()

    def test_dir_traversal(self):
        blaze.catalog.cd('/')
        self.assertEquals(blaze.catalog.cwd(), '/')
        entities = ['csv_arr', 'json_arr', 'npy_arr', 'py_arr', 'subdir']
        if tables_is_here:
            entities.append('hdf5_arr')
        self.assertEquals(blaze.catalog.ls(), sorted(entities))
        arrays = ['csv_arr', 'json_arr', 'npy_arr', 'py_arr']
        if tables_is_here:
            arrays.append('hdf5_arr')
        self.assertEquals(blaze.catalog.ls_arrs(), sorted(arrays))
        self.assertEquals(blaze.catalog.ls_dirs(),
                          ['hdf5_dir', 'subdir'])
        blaze.catalog.cd('subdir')
        self.assertEquals(blaze.catalog.cwd(), '/subdir')
        self.assertEquals(blaze.catalog.ls(),
                          ['csv_arr2'])

    def test_load_csv(self):
        # Confirms that a simple csv file can be loaded
        blaze.catalog.cd('/')
        a = blaze.catalog.get('csv_arr')
        ds = datashape.dshape('5 * {Letter: string, Number: int32}')
        self.assertEqual(a.dshape, ds)
        dat = blaze.datadescriptor.ddesc_as_py(a.ddesc)
        self.assertEqual(dat, [{'Letter': 'alpha', 'Number': 0},
                               {'Letter': 'beta', 'Number': 1},
                               {'Letter': 'gamma', 'Number': 2},
                               {'Letter': 'delta', 'Number': 3},
                               {'Letter': 'epsilon', 'Number': 4}])

    def test_load_json(self):
        # Confirms that a simple json file can be loaded
        blaze.catalog.cd('/')
        a = blaze.catalog.get('json_arr')
        ds = datashape.dshape('2 * var * int32')
        self.assertEqual(a.dshape, ds)
        dat = blaze.datadescriptor.ddesc_as_py(a.ddesc)
        self.assertEqual(dat, [[1, 2, 3], [1, 2]])

    @skipIf(not tables_is_here, 'PyTables is not installed')
    def test_load_hdf5(self):
        # Confirms that a simple hdf5 array in a file can be loaded
        blaze.catalog.cd('/')
        a = blaze.catalog.get('hdf5_arr')
        ds = datashape.dshape('2 * 3 * int32')
        self.assertEqual(a.dshape, ds)
        dat = blaze.datadescriptor.ddesc_as_py(a.ddesc)
        self.assertEqual(dat, [[1, 2, 3], [3, 2, 1]])

    @skipIf(not tables_is_here, 'PyTables is not installed')
    def test_hdf5_dir(self):
        blaze.catalog.cd('/hdf5_dir')
        self.assertEquals(blaze.catalog.cwd(), '/hdf5_dir')
        self.assertEquals(blaze.catalog.ls(), sorted(['a1', 'mygroup']))
        self.assertEquals(blaze.catalog.ls_dirs(), sorted(['mygroup']))
        self.assertEquals(blaze.catalog.ls_arrs(), sorted(['a1']))

    @skipIf(not tables_is_here, 'PyTables is not installed')
    def test_hdf5_subdir(self):
        blaze.catalog.cd('/hdf5_dir/mygroup')
        self.assertEquals(blaze.catalog.cwd(), '/hdf5_dir/mygroup')
        self.assertEquals(blaze.catalog.ls(),
                          sorted(['a2', 'a3', 'mygroup2']))
        self.assertEquals(blaze.catalog.ls_dirs(), sorted(['mygroup2']))
        self.assertEquals(blaze.catalog.ls_arrs(), sorted(['a2', 'a3']))

    @skipIf(not tables_is_here, 'PyTables is not installed')
    def test_hdf5_subdir_get(self):
        blaze.catalog.cd('/hdf5_dir/mygroup')
        a = blaze.catalog.get('a3')
        ds = datashape.dshape('2 * 3 * int32')
        self.assertEqual(a.dshape, ds)
        dat = blaze.datadescriptor.ddesc_as_py(a.ddesc)
        self.assertEqual(dat, [[1, 3, 2], [2, 1, 3]])

    @skipIf(not tables_is_here, 'PyTables is not installed')
    def test_hdf5_subdir_ls(self):
        # Check top level
        blaze.catalog.cd('/')
        lall = blaze.catalog.ls_dirs()
        self.assertEqual(lall, ['hdf5_dir', 'subdir'])
        # Check HDF5 root level
        blaze.catalog.cd('/hdf5_dir')
        larrs = blaze.catalog.ls_arrs()
        self.assertEqual(larrs, ['a1'])
        ldirs = blaze.catalog.ls_dirs()
        self.assertEqual(ldirs, ['mygroup'])
        lall = blaze.catalog.ls()
        self.assertEqual(lall, ['a1', 'mygroup'])
        # Check HDF5 second level
        blaze.catalog.cd('/hdf5_dir/mygroup')
        larrs = blaze.catalog.ls_arrs()
        self.assertEqual(larrs, ['a2', 'a3'])
        ldirs = blaze.catalog.ls_dirs()
        self.assertEqual(ldirs, ['mygroup2'])
        lall = blaze.catalog.ls()
        self.assertEqual(lall, ['a2', 'a3', 'mygroup2'])

    def test_load_npy(self):
        # Confirms that a simple npy file can be loaded
        blaze.catalog.cd('/')
        a = blaze.catalog.get('npy_arr')
        ds = datashape.dshape('20 * {idx: int32, val: string}')
        self.assertEqual(a.dshape, ds)
        dat = blaze.datadescriptor.ddesc_as_py(a.ddesc)
        self.assertEqual([x['idx'] for x in dat],
                         list(range(20)))
        self.assertEqual([x['val'] for x in dat],
                         ['yes', 'no'] * 10)

    def test_load_py(self):
        # Confirms that a simple py file can generate a blaze array
        blaze.catalog.cd('/')
        a = blaze.catalog.get('py_arr')
        ds = datashape.dshape('5 * int32')
        self.assertEqual(a.dshape, ds)
        dat = blaze.datadescriptor.ddesc_as_py(a.ddesc)
        self.assertEqual(dat, [1, 2, 3, 4, 5])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = compatibility

import sys
PY3 = sys.version_info[0] > 2

if PY3:
    from urllib.request import urlopen

else:
    from urllib2 import urlopen

########NEW FILE########
__FILENAME__ = builder
"""Convenience IR builder."""

from __future__ import print_function, division, absolute_import
from contextlib import contextmanager

from . import _generated, error, types
from .ir import Value, Const, Undef, ops, FuncArg
from .utils import findop

#===------------------------------------------------------------------===
# Helpers
#===------------------------------------------------------------------===

def unary(op):
    def unary(self, value0, **kwds):
        type = value0.type
        m = getattr(super(OpBuilder, self), op)
        return m(type, value0, **kwds)
    return unary

def binop(op, type=None):
    def binop(self, value0, value1, **kwds):
        assert value0.type == value1.type, (value0.type, value1.type)
        if type is None:
            ty = value0.type
        else:
            ty = type
        m = getattr(super(OpBuilder, self), op)
        return m(ty, value0, value1, **kwds)
    return binop

#===------------------------------------------------------------------===
# Builder
#===------------------------------------------------------------------===

class OpBuilder(_generated.GeneratedBuilder):
    """
    Build Operations, improving upon the generated methods.
    """

    def alloca(self, type, numItems=None, **kwds):
        assert type is not None
        assert numItems is None or numItems.is_int
        return super(OpBuilder, self).alloca(type, numItems, **kwds)

    def load(self, value0, **kwds):
        # TODO: Write a builder that produces untyped code !
        type = value0.type
        if type.is_opaque:
            base = type
        else:
            assert type.is_pointer, type
            base = type.base
        return super(OpBuilder, self).load(base, value0, **kwds)

    def store(self, val, var, **kwds):
        assert var.type.is_pointer
        assert val.type == var.type.base or var.type.base.is_opaque, (
            str(val.type), str(var.type), val, var)
        return super(OpBuilder, self).store(val, var, **kwds)

    def call(self, type, func, args, **kwds):
        return super(OpBuilder, self).call(type, func, args, **kwds)

    def ptradd(self, ptr, value, **kwds):
        type = ptr.type
        assert type.is_pointer
        return super(OpBuilder, self).ptradd(type, ptr, value, **kwds)

    def ptrload(self, ptr, **kwds):
        assert ptr.type.is_pointer
        return super(OpBuilder, self).ptrload(ptr.type.base, ptr, **kwds)

    def ptrstore(self, value, ptr, **kwds):
        assert ptr.type.is_pointer
        assert ptr.type.base == value.type
        return super(OpBuilder, self).ptrstore(value, ptr, **kwds)

    def ptr_isnull(self, ptr, **kwds):
        assert ptr.type.is_pointer
        return super(OpBuilder, self).ptr_isnull(types.Bool, ptr, **kwds)

    def shufflevector(self, vec1, vec2, mask, **kwds):
        assert vec1.type.is_vector
        if vec2:
            assert vec2.type == vec1.type
        assert mask.type.is_vector
        assert mask.type.base.is_int
        restype = types.Vector(vec1.type.base, mask.type.count)
        return super(OpBuilder, self).shufflevector(restype, vec1, vec2, mask, **kwds)

    # determines the type of an aggregate member
    @staticmethod
    def __indextype(t, idx):
        # must be a list of indexes
        assert isinstance(idx, list)
        assert len(idx) > 0

        # single level vector
        if t.is_vector:
            assert len(idx) == 1
            assert isinstance(idx[0], Const)
            return t.base

        # go through all indices
        for i in range(len(idx)):
            if t.is_array:
                assert isinstance(idx[i], Const) and idx[i].type.is_int
                idx[i] = idx[i].const
                t = t.base
            elif t.is_struct:
                # convert to int index
                if i.type.is_int and isinstance(i, Const):
                    idx[i] = idx[i].const
                elif isinstance(idx[i], str):
                    assert t.is_struct
                    idx[i] = t.names.index(idx[i])
                assert isinstance(i, int), "Invalid index " + idx[i]

                t = t.types[idx[i]]
            else:
                assert False, "Index too deep for type"
        return t

    def set(self, target, value, idx, **kwds):
        # handle single-level indices
        if not isinstance(idx, list):
            idx = [idx]
        t = self.__indextype(target.type, idx)
        assert value.type == t
        return super(OpBuilder, self).set(target.type, target, value, idx, **kwds)

    def get(self, target, idx, **kwds):
        # handle single-level indices
        if not isinstance(idx, list):
            idx = [idx]
        t = self.__indextype(target.type, idx)
        return super(OpBuilder, self).get(t, target, idx, **kwds)

    invert               = unary('invert')
    uadd                 = unary('uadd')
    not_                 = unary('not_')
    usub                 = unary('usub')
    add                  = binop('add')
    rshift               = binop('rshift')
    sub                  = binop('sub')
    lshift               = binop('lshift')
    mul                  = binop('mul')
    div                  = binop('div')
    bitor                = binop('bitor')
    bitxor               = binop('bitxor')
    bitand               = binop('bitand')
    mod                  = binop('mod')
    gt                   = binop('gt'      , type=types.Bool)
    is_                  = binop('is_'     , type=types.Bool)
    ge                   = binop('ge'      , type=types.Bool)
    ne                   = binop('ne'      , type=types.Bool)
    lt                   = binop('lt'      , type=types.Bool)
    le                   = binop('le'      , type=types.Bool)
    eq                   = binop('eq'      , type=types.Bool)


class Builder(OpBuilder):
    """
    I build Operations and emit them into the function.

    Also provides convenience operations, such as loops, guards, etc.
    """

    def __init__(self, func):
        self.func = func
        self.module = func.module
        self._curblock = None
        self._lastop = None

    def emit(self, op):
        """
        Emit an Operation at the current position.
        Sets result register if not set already.
        """
        assert self._curblock, "Builder is not positioned!"

        if op.result is None:
            op.result = self.func.temp()

        if self._lastop == 'head' and self._curblock.ops:
            op.insert_before(self._curblock.ops.head)
        elif self._lastop in ('head', 'tail'):
            self._curblock.append(op)
        else:
            lastop = self._lastop
            if ops.is_leader(lastop.opcode) and not ops.is_leader(op.opcode):
                self.insert_after_last_leader(lastop.block, op)
            else:
                op.insert_after(lastop)

        self._lastop = op

    def insert_after_last_leader(self, block, op):
        for firstop in block.ops:
            if not ops.is_leader(firstop.opcode):
                op.insert_before(firstop)
                return

        block.append(op)

    def _insert_op(self, op):
        if self._curblock:
            self.emit(op)

    # __________________________________________________________________
    # Positioning

    @property
    def basic_block(self):
        return self._curblock

    def position_at_beginning(self, block):
        """Position the builder at the beginning of the given block."""
        self._curblock = block
        self._lastop = 'head'

    def position_at_end(self, block):
        """Position the builder at the end of the given block."""
        self._curblock = block
        self._lastop = block.tail or 'tail'

    def position_before(self, op):
        """Position the builder before the given op."""
        if isinstance(op, FuncArg):
            raise error.PositioningError(
                "Cannot place builder before function argument")
        self._curblock = op.block
        if op == op.block.head:
            self._lastop = 'head'
        else:
            self._lastop = op._prev

    def position_after(self, op):
        """Position the builder after the given op."""
        if isinstance(op, FuncArg):
            self.position_at_beginning(op.parent.startblock)
        else:
            self._curblock = op.block
            self._lastop = op

    @contextmanager
    def _position(self, block, position):
        curblock, lastop = self._curblock, self._lastop
        position(block)
        yield self
        self._curblock, self._lastop = curblock, lastop

    at_front = lambda self, b: self._position(b, self.position_at_beginning)
    at_end   = lambda self, b: self._position(b, self.position_at_end)

    # __________________________________________________________________
    # Convenience

    def gen_call_external(self, fname, args, result=None):
        """Generate call to external function (which must be declared"""
        gv = self.module.get_global(fname)

        assert gv is not None, "Global %s not declared" % fname
        assert gv.type.is_function, gv
        assert gv.type.argtypes == [arg.type for arg in args]

        op = self.call(gv.type.res, [Const(fname), args])
        op.result = result or op.result
        return op

    def _find_handler(self, exc, exc_setup):
        """
        Given an exception and an exception setup clause, generate
        exc_matches() checks
        """
        catch_sites = [findop(block, 'exc_catch') for block in exc_setup.args]
        for exc_catch in catch_sites:
            for exc_type in exc_catch.args:
                with self.if_(self.exc_matches(types.Bool, [exc, exc_type])):
                    self.jump(exc_catch.block)
                    block = self._curblock
                self.position_at_end(block)

    def gen_error_propagation(self, exc=None):
        """
        Propagate an exception. If `exc` is not given it will be loaded
        to match in 'except' clauses.
        """
        assert self._curblock

        block = self._curblock
        exc_setup = findop(block.leaders, 'exc_setup')
        if exc_setup:
            exc = exc or self.load_tl_exc(types.Exception)
            self._find_handler(exc, exc_setup)
        else:
            self.gen_ret_undef()

    def gen_ret_undef(self):
        """Generate a return with undefined value"""
        type = self.func.type.restype
        if type.is_void:
            self.ret(None)
        else:
            self.ret(Undef(type))

    def splitblock(self, name=None, terminate=False, preserve_exc=True):
        """Split the current block, returning (old_block, new_block)"""
        oldblock = self._curblock
        op = self._lastop
        if op == 'head':
            trailing = list(self._curblock.ops)
        elif op != 'tail':
            trailing = list(op.block.ops.iter_from(op))[1:]
        else:
            trailing = []

        return splitblock(oldblock, trailing, name,
                          terminate, preserve_exc)

    def _patch_phis(self, oldblock, newblock):
        """
        Patch phis when a predecessor block changes
        """
        for op in ops:
            for use in self.func.uses[op]:
                if use.opcode == 'phi':
                    # Update predecessor blocks
                    preds, vals = use.args
                    preds = [newblock if pred == oldblock else pred
                                 for pred in preds]
                    use.set_args([preds, vals])

    def if_(self, cond):
        """with b.if_(b.eq(a, b)): ..."""
        old, exit = self.splitblock()
        if_block = self.func.new_block("if_block", after=self._curblock)
        self.cbranch(cond, if_block, exit)
        return self.at_end(if_block)

    def ifelse(self, cond):
        old, exit = self.splitblock()
        if_block = self.func.new_block("if_block", after=self._curblock)
        el_block = self.func.new_block("else_block", after=if_block)
        self.cbranch(cond, if_block, el_block)
        return self.at_end(if_block), self.at_end(el_block), exit

    def gen_loop(self, start=None, stop=None, step=None):
        """
        Generate a loop given start, stop, step and the index variable type.
        The builder's position is set to the end of the body block.

        Returns (condition_block, body_block, exit_block).
        """
        assert isinstance(stop, Value), "Stop should be a Constant or Operation"

        ty = stop.type
        start = start or Const(0, ty)
        step  = step or Const(1, ty)
        assert start.type == ty == step.type

        with self.at_front(self.func.startblock):
            var = self.alloca(types.Pointer(ty))

        prev, exit = self.splitblock('loop.exit')
        cond = self.func.new_block('loop.cond', after=prev)
        body = self.func.new_block('loop.body', after=cond)

        with self.at_end(prev):
            self.store(start, var)
            self.jump(cond)

        # Condition
        with self.at_front(cond):
            index = self.load(var)
            self.store(self.add(index, step), var)
            self.cbranch(self.lt(index, stop), body, exit)

        with self.at_end(body):
            self.jump(cond)

        self.position_at_beginning(body)
        return cond, body, exit

    # --- predecessors --- #

    def replace_predecessor(self, former_pred, new_pred, succ):
        """
        Replace `former_pred` with `new_pred` as a predecessor of block `succ`.
        """
        for op in succ:
            if op.opcode == 'phi':
                blocks, vals = op.args
                d = dict(zip(blocks, blocks))
                d.update({former_pred: new_pred})
                blocks = [d[block] for block in blocks]
                op.set_args([blocks, vals])


def deduce_successors(block):
    """Deduce the successors of a basic block"""
    op = block.terminator
    if op.opcode == 'jump':
        successors = [op.args[0]]
    elif op.opcode == 'cbranch':
        cond, ifbb, elbb = op.args
        successors = [ifbb, elbb]
    else:
        assert op.opcode in (ops.ret, ops.exc_throw)
        successors = []

    return successors


def splitblock(block, trailing, name=None, terminate=False, preserve_exc=True):
    """Split the current block, returning (old_block, new_block)"""

    func = block.parent

    if block.is_terminated():
        successors = deduce_successors(block)
    else:
        successors = []

    # -------------------------------------------------
    # Sanity check

    # Allow splitting only after leaders and before terminator
    # TODO: error check

    # -------------------------------------------------
    # Split

    blockname = name or func.temp('Block')
    newblock = func.new_block(blockname, after=block)

    # -------------------------------------------------
    # Move ops after the split to new block

    for op in trailing:
        op.unlink()
    newblock.extend(trailing)

    if terminate and not block.is_terminated():
        # Terminate
        b = Builder(func)
        b.position_at_end(block)
        b.jump(newblock)

    # Update phis and preserve exception blocks
    patch_phis(block, newblock, successors)
    if preserve_exc:
        preserve_exceptions(block, newblock)

    return block, newblock


def preserve_exceptions(oldblock, newblock):
    """
    Preserve exc_setup instructions for block splits.
    """
    from pykit.ir import Builder

    func = oldblock.parent
    b = Builder(func)
    b.position_at_beginning(newblock)

    for op in oldblock.leaders:
        if op.opcode == 'exc_setup':
            b.exc_setup(op.args[0], **op.metadata)


def patch_phis(oldblock, newblock, successors):
    """
    Patch phis when a predecessor block changes
    """
    for succ in successors:
        for op in succ.leaders:
            if op.opcode == 'phi':
                # Update predecessor blocks
                preds, vals = op.args
                preds = [newblock if pred == oldblock else pred
                             for pred in preds]
                op.set_args([preds, vals])

########NEW FILE########
__FILENAME__ = configuration
from __future__ import print_function, division, absolute_import

class Config(object):

    # Enable debug output
    debug = False

    # Verify result of each pass
    verify = True

    # Verify operations as they are built
    op_verify = True


config = Config()

########NEW FILE########
__FILENAME__ = defs
"""IR definitions."""

from __future__ import print_function, division, absolute_import

import math
import operator

import numpy as np

from . import ops
from .utils import invert, mergedicts

#===------------------------------------------------------------------===
# Python Version Compatibility
#===------------------------------------------------------------------===

def divide(a, b):
    """
    `a / b` with python 2 semantics:

        - floordiv() integer division
        - truediv() float division
    """
    if isinstance(a, (int, long)) and isinstance(b, (int, long)):
        return operator.floordiv(a, b)
    else:
        return operator.truediv(a, b)

def erfc(x):
    # Python 2.6
    # libm = ctypes.util.find_library("m")
    # return libm.erfc(x)

    return math.erfc(x)

#===------------------------------------------------------------------===
# Definitions -> Evaluation function
#===------------------------------------------------------------------===

unary = {
    ops.invert        : operator.inv,
    ops.not_          : operator.not_,
    ops.uadd          : operator.pos,
    ops.usub          : operator.neg,
}

binary = {
    ops.add           : operator.add,
    ops.sub           : operator.sub,
    ops.mul           : operator.mul,
    ops.div           : divide,
    ops.mod           : operator.mod,
    ops.lshift        : operator.lshift,
    ops.rshift        : operator.rshift,
    ops.bitor         : operator.or_,
    ops.bitand        : operator.and_,
    ops.bitxor        : operator.xor,
}

compare = {
    ops.lt            : operator.lt,
    ops.le            : operator.le,
    ops.gt            : operator.gt,
    ops.ge            : operator.ge,
    ops.eq            : operator.eq,
    ops.ne            : operator.ne,
    ops.is_           : operator.is_,
    #ops.contains      : operator.contains,
}

math_funcs = {
    ops.Sin         : np.sin,
    ops.Asin        : np.arcsin,
    ops.Sinh        : np.sinh,
    ops.Asinh       : np.arcsinh,
    ops.Cos         : np.cos,
    ops.Acos        : np.arccos,
    ops.Cosh        : np.cosh,
    ops.Acosh       : np.arccosh,
    ops.Tan         : np.tan,
    ops.Atan        : np.arctan,
    ops.Atan2       : np.arctan2,
    ops.Tanh        : np.tanh,
    ops.Atanh       : np.arctanh,
    ops.Log         : np.log,
    ops.Log2        : np.log2,
    ops.Log10       : np.log10,
    ops.Log1p       : np.log1p,
    ops.Exp         : np.exp,
    ops.Exp2        : np.exp2,
    ops.Expm1       : np.expm1,
    ops.Floor       : np.floor,
    ops.Ceil        : np.ceil,
    ops.Abs         : np.abs,
    ops.Erfc        : erfc,
    ops.Rint        : np.rint,
    ops.Pow         : np.power,
    ops.Round       : np.round,
}

#===------------------------------------------------------------------===
# Definitions
#===------------------------------------------------------------------===

unary_defs = {
    "~": ops.invert,
    "!": ops.not_,
    "+": ops.uadd,
    "-": ops.usub,
}

binary_defs = {
    "+":  ops.add,
    "-":  ops.sub,
    "*":  ops.mul,
    "/":  ops.div,
    "%":  ops.mod,
    "<<": ops.lshift,
    ">>": ops.rshift,
    "|":  ops.bitor,
    "&":  ops.bitand,
    "^":  ops.bitxor,
}

compare_defs = {
    "<":  ops.lt,
    "<=": ops.le,
    ">":  ops.gt,
    ">=": ops.ge,
    "==": ops.eq,
    "!=": ops.ne,
}

unary_opcodes = invert(unary_defs)
binary_opcodes = invert(binary_defs)
compare_opcodes = invert(compare_defs)

opcode2operator = mergedicts(unary, binary, compare)
operator2opcode = mergedicts(invert(unary), invert(binary), invert(compare))
bitwise = set(["<<", ">>", "|", "&", "^", "~"])

########NEW FILE########
__FILENAME__ = entrypoint
"""
Assemble an execution kernel from a given expression graph.
"""

from __future__ import absolute_import, division, print_function

from . import pipeline, environment, passes, execution

def compile(expr, ddesc, debug=False):
    """
    Prepare a Deferred for interpretation
    """
    env = environment.fresh_env(expr, ddesc, debug=debug)
    if debug:
        passes_ = passes.debug_passes
    else:
        passes_ = passes.passes
    return pipeline.run_pipeline(expr, env, passes_)


def run(air_func, env, **kwds):
    """
    Prepare a Deferred for interpretation
    """
    return execution.interpret(air_func, env, **kwds)

########NEW FILE########
__FILENAME__ = environment
"""
AIR compilation environment.
"""

from __future__ import print_function, division, absolute_import

# Any state that should persist between passes end up in the environment, and
# should be documented here

air_env = {
    # blaze expression graph
    #'expr_graph':       None,

    # strategy determined for each Op: { Op : strategy }
    # For instance different sub-expressions may be execution in different
    # environments
    'strategies':       None,

    # Runtime input arguments
    'runtime.args':     None,

    # Set by partitioning pass, indicates for each Op and strategy which
    # overload should be used. { (Op, strategy) : Overload }
    'kernel.overloads': None,

    # storage passed in to blaze.eval(). This is where we store the result
    'storage':          None,
}

def fresh_env(expr, storage, debug=False):
    """
    Allocate a new environment.
    """
    env = dict(air_env)
    env['storage'] = storage
    env['debug'] = debug
    return env

########NEW FILE########
__FILENAME__ = error
class CompileError(Exception):
    """Raised for various sorts of compilation errors"""

class PositioningError(CompileError):
    """Raised when a builder cannot be positioned as requested"""

class IRError(CompileError):
    """Raised when the IR is somehow malformed"""
########NEW FILE########
__FILENAME__ = interp
"""CKernel evaluation of blaze AIR."""

from __future__ import absolute_import, division, print_function

import operator

from dynd import nd, ndt
import blaze
import blz
import datashape

from ..traversal import visit
from ....datadescriptor import DyND_DDesc, BLZ_DDesc


def interpret(func, env, ddesc=None, **kwds):
    args = env['runtime.arglist']

    if ddesc is None:
        # Evaluate once
        values = dict(zip(func.args, args))
        interp = CKernelInterp(values)
        visit(interp, func)
        return interp.result
    else:
        result_ndim = env['result-ndim']

        res_shape, res_dt = datashape.to_numpy(func.type.restype)
        dim_size = operator.index(res_shape[0])
        row_size = ndt.type(str(func.type.restype.subarray(1))).default_data_size
        chunk_size = min(max(1, (1024*1024) // row_size), dim_size)
        # Evaluate by streaming the outermost dimension,
        # and using the BLZ data descriptor's append
        ddesc.blzarr = blz.zeros((0,)+res_shape[1:], res_dt,
                                 rootdir=ddesc.path, mode=ddesc.mode)
        # Loop through all the chunks
        for chunk_start in range(0, dim_size, chunk_size):
            # Tell the interpreter which chunk size to use (last
            # chunk might be smaller)
            chunk_size = min(chunk_size, dim_size - chunk_start)
            # Evaluate the chunk
            args_chunk = [arg[chunk_start:chunk_start+chunk_size]
                            if len(arg.dshape.shape) == result_ndim
                            else arg for arg in args]
            values = dict(zip(func.args, args_chunk))
            interp = CKernelChunkInterp(values, chunk_size, result_ndim)
            visit(interp, func)
            chunk = interp.result.ddesc.dynd_arr()
            ddesc.append(chunk)

        return blaze.Array(ddesc)


class CKernelInterp(object):
    """
    Interpret low-level AIR in the most straightforward way possible.

    Low-level AIR contains the following operations:

        alloc/dealloc
        ckernel

    There is a huge number of things we can still do, like blocking and
    parallelism.

    Blocking
    ========
    This should probably happen through a "blocking-ckernel" wrapper

    Parallelism
    ===========
    Both data-parallelism by executing ckernels over slices, and executing
    disjoint sub-expressions in parallel.
    """

    def __init__(self, values):
        self.values = values # { Op : py_val }

    def op_alloc(self, op):
        dshape = op.type
        ddesc = op.metadata.get('ddesc') # TODO: ddesc!
        self.values[op] = blaze.empty(dshape, ddesc=ddesc)

    def op_dealloc(self, op):
        alloc, = op.args
        del self.values[alloc]

    def op_convert(self, op):
        input = self.values[op.args[0]]
        input = input.ddesc.dynd_arr()
        result = nd.array(input, type=ndt.type(str(op.type)))
        result = blaze.Array(DyND_DDesc(result))
        self.values[op] = result

    def op_pykernel(self, op):
        pykernel, opargs = op.args
        args = [self.values[arg] for arg in opargs]
        result = pykernel(*args)
        self.values[op] = result

    def op_kernel(self, op):
        raise RuntimeError("Shouldn't be seeing a kernel here...", op)

    def op_ckernel(self, op):
        raise RuntimeError("Shouldn't be seeing a ckernel here...", op)

    def op_ret(self, op):
        retvar = op.args[0]
        self.result = self.values[retvar]


class CKernelChunkInterp(CKernelInterp):
    """
    Like CKernelInterp, but for processing one chunk.
    """

    def __init__(self, values, chunk_size, result_ndim):
        self.values = values # { Op : py_val }
        self.chunk_size = chunk_size
        self.result_ndim = result_ndim

    def op_alloc(self, op):
        dshape = op.type
        # Allocate a chunk instead of the whole thing
        if len(dshape.shape) == self.result_ndim:
            chunk = nd.empty(self.chunk_size, str(dshape.subarray(1)))
        else:
            chunk = nd.empty(str(dshape))
        self.values[op] = blaze.array(chunk)

########NEW FILE########
__FILENAME__ = test_jit_interp
from __future__ import absolute_import, division, print_function

import unittest

from datashape import dshape
import blaze
from blaze import array
from blaze.compute.ops.ufuncs import add, multiply

import numpy as np

#------------------------------------------------------------------------
# Utils
#------------------------------------------------------------------------

def make_expr(ds1, ds2):
    a = array(range(10), dshape=ds1)
    b = array(range(10), dshape=ds2)
    expr = add(a, multiply(a, b))
    return expr

#------------------------------------------------------------------------
# Tests
#------------------------------------------------------------------------

class TestExecution(unittest.TestCase):

    def test_exec(self):
        expr = make_expr(dshape('10 * float32'), dshape('10 * float32'))
        result = blaze.eval(expr)
        expected = blaze.array([ 0,  2,  6, 12, 20, 30, 42, 56, 72, 90])
        self.assertEqual(type(result), blaze.Array)
        self.assertTrue(np.all(result == expected))

    def test_exec_promotion(self):
        expr = make_expr(dshape('10 * int32'), dshape('10 * float32'))
        result = blaze.eval(expr)
        expected = blaze.array([ 0,  2,  6, 12, 20, 30, 42, 56, 72, 90],
                               dshape=dshape('10 * float64'))
        self.assertEqual(type(result), blaze.Array)
        self.assertTrue(np.all(result == expected))

    def test_exec_scalar(self):
        a = blaze.array(range(10), dshape=dshape('10 * int32'))
        b = 10
        expr = add(a, multiply(a, b))
        result = blaze.eval(expr)
        np_a = np.arange(10)
        expected = np_a + np_a * b
        self.assertTrue(np.all(result == expected))


if __name__ == '__main__':
    #TestJit('test_jit').debug()
    unittest.main()

########NEW FILE########
__FILENAME__ = allocation
"""
Insert temporary allocations and deallocations into the IR.
"""

from __future__ import absolute_import, division, print_function

from ..ir import Op
from ..builder import Builder
from .. import types


def insert_allocations(func, env):
    b = Builder(func)

    # IR positions and list of ops
    positions = dict((op, idx) for idx, op in enumerate(func.ops))
    oplist = list(func.ops)

    for op in func.ops:
        if op.opcode == 'ckernel':
            ckernel, args = op.args
            alloc   = Op('alloc', op.type, args=[])

            # TODO: Insert alloc in args list of ckernel

            # Replace uses of ckernel with temporary allocation
            op.replace_uses(alloc)
            op.set_args([ckernel, [alloc] + args])

            # Emit allocation before first use
            b.position_before(op)
            b.emit(alloc)

            # Emit deallocation after last use, unless we are returning
            # the result
            idx = max(positions[u] for u in func.uses[alloc])
            last_op = oplist[idx]
            if not last_op.opcode == 'ret':
                b.position_after(last_op)
                dealloc = Op('dealloc', types.Void, [alloc])
                b.emit(dealloc)

    return func, env


run = insert_allocations

########NEW FILE########
__FILENAME__ = ckernel_impls
"""
Convert 'kernel' Op to 'ckernel'.
"""

from __future__ import absolute_import, division, print_function

from ..ir import Op
from ..traversal import transform

def run(func, env):
    strategies = env['strategies']
    transform(CKernelImplementations(strategies), func)


class CKernelImplementations(object):
    """
    For kernels that are implemented via ckernels, this
    grabs the dynd arrfunc and turns it into a ckernel
    op.
    """

    def __init__(self, strategies):
        self.strategies = strategies

    def op_kernel(self, op):
        if self.strategies[op] != 'ckernel':
            return

        # Default overload is CKERNEL, so no need to look it up again
        overload = op.metadata['overload']

        impl = overload.func

        new_op = Op('ckernel', op.type, [impl, op.args[1:]], op.result)
        new_op.add_metadata({'rank': 0,
                             'parallel': True})
        return new_op

########NEW FILE########
__FILENAME__ = ckernel_lift
"""
Lift ckernels to their appropriate rank so they always consume the full array
arguments.
"""

from __future__ import absolute_import, division, print_function

from dynd import nd, ndt, _lowlevel

from ..traversal import visit


class CKernelLifter(object):
    """
    Lift ckernels to their appropriate rank so they always consume the
    full array arguments.

    If the environment defines 'stream-outer' as True, then the
    outermost dimension is skipped, so that the operation can be
    chunked along that dimension.
    """
    def __init__(self, env):
        self.env = env

    def get_arg_type(self, arg):
        dynd_types = self.env['dynd-types']
        if arg in dynd_types:
            return dynd_types[arg]
        else:
            return ndt.type(str(arg.type))

    def op_ckernel(self, op):
        op_ndim = len(op.type.shape)
        result_ndim = self.env.get('result-ndim', 0)
        ckernel, args = op.args
        in_types = [self.get_arg_type(arg) for arg in args[1:]]
        out_type = ndt.type(str(args[0].type))

        if isinstance(ckernel, dict):
            tag = ckernel['tag']
            if tag == 'elwise':
                ck = ckernel['ckernel']
                if op.metadata['rank'] < op_ndim and \
                        self.env.get('stream-outer', False) and result_ndim == op_ndim:
                    # Replace the leading dimension type with 'strided' in each operand
                    # if we're streaming it for processing BLZ
                    # TODO: Add dynd tp.subarray(N) function like datashape has
                    for i, tp in enumerate(in_types):
                        if tp.ndim == result_ndim:
                            in_types[i] = ndt.make_strided_dim(tp.element_type)
                    out_type = ndt.make_strided_dim(out_type.element_type)

                op.args[0] = _lowlevel.lift_arrfunc(ck)
            elif tag == 'reduction':
                ck = ckernel['ckernel']
                assoc = ckernel['assoc']
                comm = ckernel['comm']
                ident = ckernel['ident']
                ident = None if ident is None else nd.asarray(ident)
                axis = ckernel['axis']
                keepdims = ckernel['keepdims']
                op.args[0] = _lowlevel.lift_reduction_arrfunc(
                                ck, in_types[0],
                                axis=axis, keepdims=keepdims,
                                associative=assoc, commutative=comm,
                                reduction_identity=ident)
            elif tag == 'rolling':
                ck = ckernel['ckernel']
                window = ckernel['window']
                minp = ckernel['minp']
                if minp != 0:
                    raise ValueError('rolling window with minp != 0 not supported yet')
                op.args[0] = _lowlevel.make_rolling_arrfunc(ck, window)
            elif tag == 'ckfactory':
                ckfactory = ckernel['ckernel_factory']
                ck = ckfactory(out_type, *in_types)
                op.args[0] = ck
            else:
                raise RuntimeError('unnrecognized ckernel tag %s' % tag)
        else:
            op.args[0] = ckernel


def run(func, env):
    visit(CKernelLifter(env), func)

########NEW FILE########
__FILENAME__ = ckernel_prepare
"""
Lift ckernels to their appropriate rank so they always consume the full array
arguments.
"""

from __future__ import absolute_import, division, print_function
from ....datadescriptor import DyND_DDesc, BLZ_DDesc

from dynd import nd

def prepare_local_execution(func, env):
    """
    Prepare for local execution
    """
    storage = env['storage']

    argdict = env['runtime.args']
    args = [argdict[arg] for arg in func.args]

    # If it's a BLZ output, we want an interpreter that streams
    # the processing through in chunks
    if storage is not None:
        if len(func.type.restype.shape) == 0:
            raise TypeError('Require an array, not a scalar, for outputting to BLZ')

        result_ndim = len(func.type.restype.shape)
        env['stream-outer'] = True
        env['result-ndim'] = result_ndim
    else:
        # Convert any persistent inputs to memory
        # TODO: should stream the computation in this case
        for i, arg in enumerate(args):
            if isinstance(arg.ddesc, BLZ_DDesc):
                args[i] = arg[:]

    # Update environment with dynd type information
    dynd_types = dict((arg, get_dynd_type(array))
                          for arg, array in zip(func.args, args)
                              if isinstance(array.ddesc, DyND_DDesc))
    env['dynd-types'] = dynd_types
    env['runtime.arglist'] = args


def get_dynd_type(array):
    return nd.type_of(array.ddesc.dynd_arr())

########NEW FILE########
__FILENAME__ = ckernel_rewrite
"""
Rewrite ckernels to executable pykernels.
"""

from __future__ import absolute_import, division, print_function

from dynd import nd, ndt

from ..ir import Op


def run(func, env):
    storage = env['storage']

    for op in func.ops:
        if op.opcode == 'ckernel':
            # Build an executable chunked or in-memory pykernel
            if storage is None:
                pykernel = op_ckernel(op)
            else:
                pykernel = op_ckernel_chunked(op)

            newop = Op('pykernel', op.type, [pykernel, op.args[1]],
                       op.result)
            op.replace(newop)


def op_ckernel(op):
    """
    Create a pykernel for a ckernel for uniform interpretation.
    """
    af = op.args[0]

    def pykernel(*args):
        dst = args[0]
        srcs = args[1:]

        dst_descriptor  = dst.ddesc
        src_descriptors = [src.ddesc for src in srcs]

        out = dst_descriptor.dynd_arr()
        inputs = [desc.dynd_arr() for desc in src_descriptors]

        # Execute!
        af.execute(out, *inputs)

    return pykernel


def op_ckernel_chunked(op):
    """
    Create a pykernel for a ckernel for uniform interpretation that handled
    chunked out-of-core execution.
    """
    deferred_ckernel = op.args[0]

    def pykernel(*args):
        dst = args[0]
        srcs = args[1:]

        dst_descriptor  = dst.ddesc
        src_descriptors = [src.ddesc for src in srcs]

        out = dst_descriptor.dynd_arr()
        inputs = [desc.dynd_arr() for desc in src_descriptors]

        # Execute!
        deferred_ckernel.execute(out, *inputs)

    return pykernel

########NEW FILE########
__FILENAME__ = coercions
"""
Some Blaze AIR transformations and simplifications.
"""

from __future__ import absolute_import, division, print_function

from ..ir import Op
from ..builder import Builder

#------------------------------------------------------------------------
# Coercions -> Conversions
#------------------------------------------------------------------------

def explicit_coercions(func, env=None):
    """
    Turn implicit coercions into explicit conversion operations.
    """
    conversions = {}
    b = Builder(func)

    for op in func.ops:
        if op.opcode != 'kernel':
            continue

        overload = op.metadata['overload']
        signature = overload.resolved_sig
        parameters = signature.parameters[:-1]
        assert len(op.args) - 1 == len(parameters)

        # -------------------------------------------------
        # Identify conversion points

        replacements = {} # { arg : replacement_conversion }
        for arg, param_type in zip(op.args[1:], parameters):
            if arg.type != param_type:
                conversion = conversions.get((arg, param_type))
                if not conversion:
                    conversion = Op('convert', param_type, [arg])
                    b.position_after(arg)
                    b.emit(conversion)
                    conversions[arg, param_type] = conversion

                replacements[arg] = conversion

        # -------------------------------------------------

        op.replace_args(replacements)


run = explicit_coercions

########NEW FILE########
__FILENAME__ = partitioning
"""
Plugin annotation and partitioning. This determines according to a set of
rules which plugin to use for which operation.
"""

from __future__ import absolute_import, division, print_function
from collections import defaultdict

import datashape

from ..ir import FuncArg
from ...strategy import CKERNEL
from ....io.sql import SQL, SQL_DDesc


# List of backends to use greedily listed in order of preference

preferences = [
    SQL,  # TODO: Allow easier extension of new backends
]

#------------------------------------------------------------------------
# Strategies
#------------------------------------------------------------------------

# TODO: We may want the first N passes to have access to accurate types
#       (containing concrete shape) and runtime inputs, and then do our
#       instruction selection. After that we can throw this away to perform
#       caching from that point on.
#
#       Alternatively, we can encode everything as metadata early on, but this
#       may not work well for open-ended extension, such as plugins that were
#       not foreseen

def use_sql(op, strategies, env):
    """
    Determine whether `op` needs to be handled by the SQL backend.

    NOTE: This also populates env['sql.conns']. Mutating this way is somewhat
          undesirable, but this is a non-local decision anyway
    """
    conns = env.setdefault('sql.conns', {})

    if isinstance(op, FuncArg):
        # Function argument, this is a valid SQL query if the runtime input
        # described an SQL data source
        runtime_args = env['runtime.args']
        array = runtime_args[op]
        data_desc = array.ddesc
        is_scalar = not data_desc.dshape.shape
        if not isinstance(data_desc, SQL_DDesc) and not is_scalar:
            return False
        if isinstance(data_desc, SQL_DDesc):
            conns[op] = data_desc.conn
        return True
    elif all(strategies[arg] == SQL for arg in op.args[1:]):
        connections = set(conns[arg] for arg in op.args[1:] if arg in conns)
        if len(connections) == 1:
            [conn] = connections
            conns[op] = conn
            return True
        return False
    else:
        return False


determine_plugin = {
    SQL:        use_sql,
}

#------------------------------------------------------------------------
# Annotation
#------------------------------------------------------------------------

def annotate_all_kernels(func, env):
    """
    Annotate all sub-expressions with all kernels that can potentially
    execute the operation.

    Populate environment with 'kernel.overloads':

        { (Op, pluginname) : Overload }
    """
    # { (Op, pluginname) : Overload }
    impls = env['kernel.overloads'] = {}

    # { op: [plugin] }
    unmatched = env['unmached_impls'] = defaultdict(list)

    for op in func.ops:
        if op.opcode == "kernel":
            _find_impls(op, unmatched, impls)


def _find_impls(op, unmatched, impls):
    function = op.metadata['kernel']
    overload = op.metadata['overload']

    found_impl = False
    for pluginname in function.available_plugins:
        py_func, signature = overload_for_plugin(function, overload, pluginname)
        if py_func is not None:
            impls[op, pluginname] = py_func, signature
            found_impl = True
        else:
            unmatched[op].append(pluginname)


def overload_for_plugin(function, overload, pluginname):
    """Find an implementation overload for the given plugin"""
    expected_signature = overload.resolved_sig
    argstype = datashape.coretypes.Tuple(expected_signature.argtypes)

    try:
        overloader, datalist = function.plugins[pluginname]
        idx, match = overloader.resolve_overload(argstype)
    except datashape.OverloadError:
        return None, None

    if match != expected_signature and False:
        ckdispatcher = function.get_dispatcher('ckernel')
        raise TypeError(
            "Signature of implementation (%s) does not align with "
            "signature from blaze function (%s) from argtypes [%s] "
            "for function %s with signature %s" %
                (match, expected_signature,
                 ", ".join(map(str, expected_signature.argtypes)),
                 function, overload.sig))

    return datalist[idx], match

#------------------------------------------------------------------------
# Partitioning
#------------------------------------------------------------------------

def partition(func, env):
    """
    Determine the execution plugin for each operation.
    """
    strategies = env['strategies'] = {}
    impls = env['kernel.overloads']

    for arg in func.args:
        strategies[arg] = determine_preference(arg, env, preferences)

    for op in func.ops:
        if op.opcode == "kernel":
            prefs = [p for p in preferences if (op, p) in impls]
            strategies[op] = determine_preference(op, env, prefs)


def determine_preference(op, env, preferences):
    """Return the first valid plugin according to a list of preferences"""
    strategies = env['strategies']
    for preference in preferences:
        valid_plugin = determine_plugin[preference]
        if valid_plugin(op, strategies, env):
            return preference

    # If no alternative plugin was found, use the default ckernel
    return CKERNEL

#------------------------------------------------------------------------
# Backend boundaries / Fusion boundaries
#------------------------------------------------------------------------

def annotate_roots(func, env):
    """
    Determine 'root' ops, those are ops along fusion boundaries. E.g.
    a unary kernel that can only operate on in-memory data, with an sql
    operand expression:

        kernel(expr{sql}){jit}

    Roots become the place where some backend-specific (e.g. 'jit', or 'sql')
    must return some blaze result to the execution engine, that describes the
    data (e.g. via an out-of-core, remote or local data descriptor).

    NOTE: The number and nature of uses of a root can govern where and if
          to move the data. For instance, if we do two local computations on
          one remote data source, we may want to move it just once first (
          or in chunks)
    """
    strategies = env['strategies']
    roots = env['roots'] = set()

    for op in func.ops:
        if op.opcode == "kernel":
            uses = func.uses[op]
            if len(uses) > 1:
                # Multiple uses, boundary
                roots.add(op)
            elif any(strategies[arg] != strategies[op] for arg in op.args[1:]):
                # Different exeuction strategies, boundary
                roots.add(op)
            elif len(uses) == 1:
                # Result for user, boundary
                [use] = uses
                if use.opcode == 'ret':
                    roots.add(op)

########NEW FILE########
__FILENAME__ = translate
"""
Translate blaze expressoin graphs into blaze AIR.
"""

from __future__ import absolute_import, division, print_function

from .. import types
from ..ir import Function, Op, Const
from ..builder import Builder

#------------------------------------------------------------------------
# AIR construction
#------------------------------------------------------------------------


def run(expr, env):
    graph, expr_ctx = expr
    air_func = from_expr(graph, expr_ctx, env)
    return air_func, env


def from_expr(graph, expr_context, env):
    """
    Map a Blaze expression graph to blaze AIR

    Parameters
    ----------
    graph: blaze.expr.Op
        Expression graph

    expr_context: ExprContext
        Context of the expression

    ctx: ExecutionContext
    """
    inputs = expr_context.params

    # -------------------------------------------------
    # Types

    argtypes = [operand.dshape for operand in inputs]
    signature = types.Function(graph.dshape, argtypes, varargs=False)

    # -------------------------------------------------
    # Setup function

    name = "expr"
    argnames = ["e%d" % i for i in range(len(inputs))]
    f = Function(name, argnames, signature)
    builder = Builder(f)
    builder.position_at_beginning(f.new_block('entry'))

    # -------------------------------------------------
    # Generate function

    valuemap = dict((expr, f.get_arg("e%d" % i))
                      for i, expr in enumerate(inputs))
    _from_expr(graph, f, builder, valuemap)

    retval = valuemap[graph]
    builder.ret(retval)

    # Update environment with runtime arguments
    runtime_args = [expr_context.terms[input] for input in inputs]
    env['runtime.args'] = dict(zip(f.args, runtime_args))

    return f

def _from_expr(expr, f, builder, values):
    if expr.opcode == 'array':
        result = values[expr]
    else:
        # -------------------------------------------------
        # Construct args

        # This is purely for IR readability
        name = expr.metadata['kernel'].fullname
        args = [_from_expr(arg, f, builder, values) for arg in expr.args]
        args = [Const(name)] + args

        # -------------------------------------------------
        # Construct Op

        result = Op("kernel", expr.dshape, args)

        # Copy metadata verbatim
        assert 'kernel' in expr.metadata
        assert 'overload' in expr.metadata
        result.add_metadata(expr.metadata)

        # -------------------------------------------------
        # Emit Op in code stream

        builder.emit(result)

    values[expr] = result
    return result

########NEW FILE########
__FILENAME__ = interp
"""IR interpreter."""

from __future__ import print_function, division, absolute_import

import ctypes

try:
    import exceptions
except ImportError:
    import builtins as exceptions
from itertools import chain
from collections import namedtuple
from functools import partial

from . import defs, ops, tracing, types
from .ir import Function
from .traversal import ArgLoader
from .utils import linearize
#===------------------------------------------------------------------===
# Interpreter
#===------------------------------------------------------------------===

Undef = "Undef"                         # Undefined/uninitialized value
State = namedtuple('State', ['refs'])   # State shared by stack frames

class Reference(object):
    """
    Models a reference to an object
    """

    def __init__(self, obj, refcount, producer):
        self.obj = obj
        self.refcount = refcount
        self.producer = producer

class UncaughtException(Exception):
    """
    Raised by the interpreter when code raises an exception that isn't caught
    """

class Interp(object):
    """
    Interpret the function given as a ir.Function. See the run() function
    below.

        func:           The ir.Function we interpret
        exc_model:      ExceptionModel that knows how to deal with exceptions
        argloader:      InterpArgloader: knows how pykit Values are associated
                        with runtime (stack) values (loads from the store)
        ops:            Flat list of instruction targets (['%0'])
        blockstarts:    Dict mapping block labels to address offsets
        prevblock:      Previously executing basic block
        pc:             Program Counter
        lastpc:         Last value of Program Counter
        exc_handlers:   List of exception target blocks to try
        exception:      Currently raised exception
        refs:           { id(obj) : Reference }
    """

    def __init__(self, func, env, exc_model, argloader, tracer):
        self.func = func
        self.env = env
        self.exc_model = exc_model
        self.argloader = argloader

        self.state = {
            'env':       env,
            'exc_model': exc_model,
            'tracer':    tracer,
        }

        self.ops, self.blockstarts = linearize(func)
        self.lastpc = 0
        self._pc = 0
        self.prevblock = None
        self.exc_handlers = None
        self.exception = None

    # __________________________________________________________________
    # Utils

    def incr_pc(self):
        """Increment program counter"""
        self.pc += 1

    def decr_pc(self):
        """Decrement program counter"""
        self.pc -= 1

    def halt(self):
        """Stop interpreting"""
        self.pc = -1

    @property
    def op(self):
        """Return the current operation"""
        return self.getop(self.pc)

    def getop(self, pc):
        """PC -> Op"""
        return self.ops[pc]

    def setpc(self, newpc):
        self.lastpc = self.pc
        self._pc = newpc

    pc = property(lambda self: self._pc, setpc, doc="Program Counter")

    def blockswitch(self, oldblock, newblock, valuemap):
        self.prevblock = oldblock
        self.exc_handlers = []

        self.execute_phis(newblock, valuemap)

    def execute_phis(self, block, valuemap):
        """
        Execute all phis in parallel, i.e. execute them before updating the
        store.
        """
        new_values = {}
        for op in block.leaders:
            if op.opcode == 'phi':
                new_values[op.result] = self.execute_phi(op)

        valuemap.update(new_values)

    def execute_phi(self, op):
        for i, block in enumerate(op.args[0]):
            if block == self.prevblock:
                values = op.args[1]
                return self.argloader.load_op(values[i])

        raise RuntimeError("Previous block %r not a predecessor of %r!" %
                                    (self.prevblock.name, op.block.name))

    noop = lambda *args: None

    # __________________________________________________________________
    # Core operations

    # unary, binary and compare operations set below

    def convert(self, arg):
        return types.convert(arg, self.op.type)

    # __________________________________________________________________
    # Var

    def alloca(self, numitems=None):
        return { 'value': Undef, 'type': self.op.type }

    def load(self, var):
        #assert var['value'] is not Undef, self.op
        return var['value']

    def store(self, value, var):
        if isinstance(value, dict) and set(value) == set(['type', 'value']):
            value = value['value']
        var['value'] = value

    def phi(self):
        "See execute_phis"
        return self.argloader.load_op(self.op)

    # __________________________________________________________________
    # Functions

    def function(self, funcname):
        return self.func.module.get_function(funcname)

    def call(self, func, args):
        if isinstance(func, Function):
            # We're calling another known pykit function,
            try:
                return run(func, args=args, **self.state)
            except UncaughtException as e:
                # make sure to handle any uncaught exceptions properly
                self.exception, = e.args
                self._propagate_exc()
        else:
            return func(*args)

    def call_math(self, fname, *args):
        return defs.math_funcs[fname](*args)

    # __________________________________________________________________
    # Attributes

    def getfield(self, obj, attr):
        if obj['value'] is Undef:
            return Undef
        return obj['value'][attr] # structs are dicts

    def setfield(self, obj, attr, value):
        if obj['value'] is Undef:
            obj['value'] = {}
        obj['value'][attr] = value

    # __________________________________________________________________

    print = print

    # __________________________________________________________________
    # Pointer

    def ptradd(self, ptr, addend):
        value = ctypes.cast(ptr, ctypes.c_void_p).value
        itemsize = ctypes.sizeof(type(ptr)._type_)
        return ctypes.cast(value + itemsize * addend, type(ptr))

    def ptrload(self, ptr):
        return ptr[0]

    def ptrstore(self, value, ptr):
        ptr[0] = value

    def ptr_isnull(self, ptr):
        return ctypes.cast(ptr, ctypes.c_void_p).value == 0

    def func_from_addr(self, ptr):
        type = self.op.type
        return ctypes.cast(ptr, types.to_ctypes(type))

    # __________________________________________________________________
    # Control flow

    def ret(self, arg):
        self.halt()
        if self.func.type.restype != types.Void:
            return arg

    def cbranch(self, test, true, false):
        if test:
            self.pc = self.blockstarts[true.name]
        else:
            self.pc = self.blockstarts[false.name]

    def jump(self, block):
        self.pc = self.blockstarts[block.name]

    # __________________________________________________________________
    # Exceptions

    def new_exc(self, exc_name, exc_args):
        return self.exc_model.exc_instantiate(exc_name, *exc_args)

    def exc_catch(self, types):
        self.exception = None # We caught it!

    def exc_setup(self, exc_handlers):
        self.exc_handlers = exc_handlers

    def exc_throw(self, exc):
        self.exception = exc
        self._propagate_exc() # Find exception handler

    def _exc_match(self, exc_types):
        """
        See whether the current exception matches any of the exception types
        """
        return any(self.exc_model.exc_match(self.exception, exc_type)
                        for exc_type in exc_types)

    def _propagate_exc(self):
        """Propagate installed exception (`self.exception`)"""
        catch_op = self._find_handler()
        if catch_op:
            # Exception caught! Transfer control to block
            catch_block = catch_op.parent
            self.pc = self.blockstarts[catch_block.name]
        else:
            # No exception handler!
            raise UncaughtException(self.exception)

    def _find_handler(self):
        """Find a handler for an active exception"""
        exc = self.exception

        for block in self.exc_handlers:
            for leader in block.leaders:
                if leader.opcode != ops.exc_catch:
                    continue

                args = [arg.const for arg in leader.args[0]]
                if self._exc_match(args):
                    return leader

    # __________________________________________________________________
    # Generators

    def yieldfrom(self, op):
        pass # TODO:

    def yieldval(self, op):
        pass # TODO:


# Set unary, binary and compare operators
for opname, evaluator in chain(defs.unary.items(), defs.binary.items(),
                               defs.compare.items()):
    setattr(Interp, opname, staticmethod(evaluator))

#===------------------------------------------------------------------===
# Exceptions
#===------------------------------------------------------------------===

class ExceptionModel(object):
    """
    Model that governs the exception hierarchy
    """

    def exc_op_match(self, exc_type, op):
        """
        See whether `exception` matches `exc_type`
        """
        assert exc_type.opcode == 'constant'
        if op.opcode == 'constant':
            return self.exc_match(exc_type.const, op.const)
        raise NotImplementedError("Dynamic exception checks")

    def exc_match(self, exc_type, exception):
        """
        See whether `exception` matches `exc_type`
        """
        return (isinstance(exc_type, exception) or
                issubclass(exception, exc_type))

    def exc_instantiate(self, exc_name, *args):
        """
        Instantiate an exception
        """
        exc_type = getattr(exceptions, exc_name)
        return exc_type(*args)

#===------------------------------------------------------------------===
# Run
#===------------------------------------------------------------------===

class InterpArgLoader(ArgLoader):

    def load_GlobalValue(self, arg):
        assert not arg.external, "Not supported yet"
        return arg.value.const

    def load_Undef(self, arg):
        return Undef

def run(func, env=None, exc_model=None, _state=None, args=(),
        tracer=tracing.DummyTracer()):
    """
    Interpret function. Raises UncaughtException(exc) for uncaught exceptions
    """
    assert len(func.args) == len(args)

    tracer.push(tracing.Call(func, args))

    # -------------------------------------------------
    # Set up interpreter


    valuemap = dict(zip(func.argnames, args)) # { '%0' : pyval }
    argloader = InterpArgLoader(valuemap)
    interp = Interp(func, env, exc_model or ExceptionModel(),
                    argloader, tracer)
    if env:
        handlers = env.get("interp.handlers") or {}
    else:
        handlers = {}

    # -------------------------------------------------
    # Eval loop

    curblock = None
    while True:
        # -------------------------------------------------
        # Block transitioning

        op = interp.op
        if op.block != curblock:
            interp.blockswitch(curblock, op.block, valuemap)
            curblock = op.block

        # -------------------------------------------------
        # Find handler

        if op.opcode in handlers:
            fn = partial(handlers[op.opcode], interp)
        else:
            fn = getattr(interp, op.opcode)

        # -------------------------------------------------
        # Load arguments

        args = argloader.load_args(op)

        # -------------------------------------------------
        # Execute...

        tracer.push(tracing.Op(op, args))

        oldpc = interp.pc
        try:
            result = fn(*args)
        except UncaughtException as e:
            tracer.push(tracing.Exc(e))
            raise
        valuemap[op.result] = result

        tracer.push(tracing.Res(op, args, result))

        # -------------------------------------------------
        # Advance PC

        if oldpc == interp.pc:
            interp.incr_pc()
        elif interp.pc == -1:
            # Returning...
            tracer.push(tracing.Ret(result))
            return result

########NEW FILE########
__FILENAME__ = ir
"""Module defines the IR for AIR with a few utility functions"""

from __future__ import print_function, division, absolute_import
from collections import defaultdict
from itertools import chain

from .linkedlist import LinkedList
from .pattern import match
from .prettyprint import pretty
from .traits import Delegate, traits
from .utils import flatten, listify, make_temper, nestedmap
from . import error, ops, types


class Value(object):
    __str__ = pretty

    __slots__ = ()


class Function(Value):
    """
    Function consisting of basic blocks.

    Attributes
    ----------
    module: Module
         Module owning the function

    name:
        name of the function

    args: [FuncArg]

    argnames:
        argument names ([str])

    blocks:
        List of basic blocks in topological order

    startblock: Block
        The entry basic block

    exitblock: Block
        The last block in the list. This will only be the actual 'exit block'
        if the function is actually populated and has an exit block.

    values:  { op_name: Operation }

    uses: { Operation : [Operation] }
        Operations that refer to this operation in their 'args' list

    temp: function, name -> tempname
        allocate a temporary name
    """

    __slots__ = ('module', 'name', 'type', 'temp', 'blocks', 'blockmap',
                 'argnames', 'argdict', 'uses')

    def __init__(self, name, argnames, type, temper=None):
        self.module = None
        self.name = name
        self.type = type
        self.temp = temper or make_temper()

        self.blocks = LinkedList()
        self.blockmap = dict((block.name, block) for block in self.blocks)
        self.argnames = argnames
        self.argdict = {}

        self.uses = defaultdict(set)

        # reserve names
        for argname in argnames:
            self.temp(argname)

    @property
    def args(self):
        return [self.get_arg(argname) for argname in self.argnames]

    @property
    def startblock(self):
        return self.blocks.head

    @property
    def exitblock(self):
        return self.blocks.tail

    @property
    def ops(self):
        """Get a flat iterable of all Ops in this function"""
        return chain(*self.blocks)

    def new_block(self, label, ops=None, after=None):
        """Create a new block with name `label` and append it"""
        label = self.temp(label)
        return self.add_block(Block(label, self, ops), after)

    def add_arg(self, argname, argtype):
        self.argnames.append(argname)
        argtypes = tuple(self.type.argtypes) + (argtype,)
        self.type = types.Function(self.type.restype, argtypes,
                                   self.type.varargs)
        return self.get_arg(argname)

    def add_block(self, block, after=None):
        """Add a Block at the end, or after `after`"""
        assert block.name not in self.blockmap
        self.temp(block.name)  # Make sure this name is taken

        if block.parent is None:
            block.parent = self
        else:
            assert block.parent is self

        self.blockmap[block.name] = block
        if after is None:
            self.blocks.append(block)
        else:
            idx = self.blocks.index(after)
            self.blocks.insert(idx + 1, block)

        return block

    def get_block(self, label):
        return self.blockmap[label]

    def del_block(self, block):
        self.blocks.remove(block)
        del self.blockmap[block.name]

    def get_arg(self, argname):
        """Get argument as a Value"""
        if argname in self.argdict:
            return self.argdict[argname]

        idx = self.argnames.index(argname)
        type = self.type.argtypes[idx]
        arg = FuncArg(self, argname, type)
        self.argdict[argname] = arg
        return arg

    @property
    def result(self):
        """We are a first-class value..."""
        return self.name

    # ______________________________________________________________________
    # uses

    def add_op(self, op):
        """
        Register a new Op as part of the function.

        Does NOT insert the Op in any basic block
        """
        _add_args(self.uses, op, op.args)

    def reset_uses(self):
        from pykit.analysis import defuse
        self.uses = defuse.defuse(self)

    def delete_all(self, delete):
        """
        Delete all given operands, don't complain about uses from ops are that
        to be deleted. For example:

            %0 = myop(%arg0)
            %1 = add(%0, %arg1)

        delete = [%0, %1]
        """
        for op in delete:
            op.set_args([])
        for op in delete:
            op.delete()

    # ______________________________________________________________________

    def __repr__(self):
        return "Function(%s)" % self.name


@traits
class Block(Value):
    """
    Basic block of Operations.

        name:   Name of block (unique within function)
        parent: Function owning block
    """

    head, tail = Delegate('ops'), Delegate('ops')

    __slots__ = ('name', 'parent', 'ops', '_prev', '_next')

    def __init__(self, name, parent=None, ops=None):
        self.name   = name
        self.parent = parent
        self.ops = LinkedList(ops or [])
        self._prev = None
        self._next = None

    @property
    def opcodes(self):
        """Returns [opcode] for all operations in the block"""
        for op in self.ops:
            yield op.opcode

    @property
    def optypes(self):
        """Returns [type] for all operations in the block"""
        for op in self.ops:
            yield op.type

    def __iter__(self):
        return iter(self.ops)

    def append(self, op):
        """Append op to block"""
        self.ops.append(op)
        op.parent = self
        self.parent.add_op(op)

    def extend(self, ops):
        """Extend block with ops"""
        for op in ops:
            self.append(op)

    @property
    def result(self):
        """We are a first-class value..."""
        return self.name

    @property
    @listify
    def leaders(self):
        """
        Return an iterator of basic block leaders
        """
        for op in self.ops:
            if ops.is_leader(op.opcode):
                yield op
            else:
                break

    @property
    def terminator(self):
        """Block Op in block, which needs to be a terminator"""
        assert self.is_terminated(), self.ops.tail
        return self.ops.tail

    def is_terminated(self):
        """Returns whether the block is terminated"""
        return self.ops.tail and ops.is_terminator(self.ops.tail.opcode)

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return "Block(%s)" % self.name


class Local(Value):
    """
    Local value in a Function. This is either a FuncArg or an Operation.
    Constants do not belong to any function.
    """

    __slots__ = ()

    @property
    def function(self):
        """The Function owning this local value"""
        raise NotImplementedError

    def replace_uses(self, dst):
        """
        Replace all uses of `self` with `dst`. This does not invalidate this
        Operation!
        """
        src = self

        # Replace src with dst in use sites
        for use in set(self.function.uses[src]):
            def replace(op):
                if op == src:
                    return dst
                return op
            newargs = nestedmap(replace, use.args)
            use.set_args(newargs)


class FuncArg(Local):
    """
    Argument to the function. Use Function.get_arg()
    """

    __slots__ = ('parent', 'opcode', 'type', 'result')

    def __init__(self, func, name, type):
        self.parent = func
        self.opcode = 'arg'
        self.type   = type
        self.result = name

    @property
    def function(self):
        return self.parent

    def __repr__(self):
        return "FuncArg(%%%s)" % self.result


class Operation(Local):
    """
    Typed n-ary operation with a result. E.g.

        %0 = add(%a, %b)

    Attributes:
    -----------
    opcode:
        ops.* opcode, e.g. "getindex"

    type: types.Type
        Result type of applying this operation

    args:
        (one level nested) list of argument Values

    operands:
        symbolic operands, e.g. ['%0'] (virtual registers)

    result:
        symbol result, e.g. '%0'

    args:
        Operand values, e.g. [Operation("getindex", ...)
    """

    __slots__ = ("parent", "opcode", "type", "result",
                  "_prev", "_next", "_args", "_metadata")

    def __init__(self, opcode, type, args, result=None, parent=None,
                 metadata=None):
        self.parent    = parent
        self.opcode    = opcode
        self.type      = type
        self._args     = args
        self.result    = result
        self._metadata = None
        self._prev     = None
        self._next     = None
        if metadata:
            self.add_metadata(metadata)

    def get_metadata(self):
        if self._metadata is None:
            self._metadata = {}
        return self._metadata

    def set_metadata(self, metadata):
        self._metadata = metadata

    metadata = property(get_metadata, set_metadata)

    @property
    def uses(self):
        "Enumerate all Operations referring to this value"
        return self.function.uses[self]

    @property
    def args(self):
        """Operands to this Operation (readonly)"""
        return self._args

    # ______________________________________________________________________
    # Placement

    def insert_before(self, op):
        """Insert self before op"""
        assert self.parent is None, op
        self.parent = op.parent
        self.parent.ops.insert_before(self, op)
        self.function.add_op(self)

    def insert_after(self, op):
        """Insert self after op"""
        assert self.parent is None, self
        self.parent = op.parent
        self.parent.ops.insert_after(self, op)
        self.function.add_op(self)

    # ______________________________________________________________________
    # Replace

    def replace_op(self, opcode, args, type=None):
        """Replace this operation's opcode, args and optionally type"""
        # Replace ourselves inplace
        self.opcode = opcode
        self.set_args(args)
        if type is not None:
            self.type = type
        self.metadata = {}

    def replace_args(self, replacements):
        """
        Replace arguments listed in the `replacements` dict. The replacement
        instructions must dominate this instruction.
        """
        if replacements:
            newargs = nestedmap(lambda arg: replacements.get(arg, arg), self.args)
            self.set_args(newargs)

    @match
    def replace(self, op):
        """
        Replace this operation with a new operation, changing this operation.
        """
        assert op.result is not None and op.result == self.result
        self.replace_op(op.opcode, op.args, op.type)
        self.add_metadata(op.metadata)

    @replace.case(op=list)
    def replace_list(self, op):
        """
        Replace this Op with a list of other Ops. If no Op has the same
        result as this Op, the Op is deleted:

            >>> print block
            %0 = ...
            >>> print [op0, op1, op2]
            [%0 = ..., %1 = ..., %2 = ...]
            >>> op0.replace_with([op1, op0, op2])
            >>> print block
            %1 = ...
            %0 = ...
            %2 = ...
            >>> op0.replace_with([op3, op4])
            %1 = ...
            %3 = ...
            %4 = ...
            %2 = ...
        """
        lst = self._set_registers(*op)
        for i, op in enumerate(lst):
            if op.result == self.result:
                break
            op.insert_before(self)
        else:
            self.delete()
            return

        self.replace(op)
        last = op
        for op in lst[i + 1:]:
            op.insert_after(last)
            last = op

    # ______________________________________________________________________

    def set_args(self, args):
        """Set a new argslist"""
        _del_args(self.function.uses, self, self.args)
        _add_args(self.function.uses, self, args)
        self._args = args

    # ______________________________________________________________________

    def delete(self):
        """Delete this operation"""
        if self.uses:
            raise error.IRError(
                "Operation %s is still in use and cannot be deleted" % (self,))

        _del_args(self.function.uses, self, self.args)
        del self.function.uses[self]
        self.unlink()
        self.result = "deleted(%s)" % (self.result,)

    def unlink(self):
        """Unlink from the basic block"""
        self.parent.ops.remove(self)
        self.parent = None

    # ______________________________________________________________________

    def add_metadata(self, metadata):
        if self.metadata is None:
            self.metadata = dict(metadata)
        else:
            self.metadata.update(metadata)

    @property
    def function(self):
        return self.parent.parent

    @property
    def block(self):
        """Containing block"""
        return self.parent

    @property
    def operands(self):
        """
        Operands to this operation, in the form of args with symbols
        and constants.

            >>> print Op("mul", Int32, [op_a, op_b]).operands
            ['a', 'b']
        """
        non_constants = (Block, Operation, FuncArg, GlobalValue)
        result = lambda x: x.result if isinstance(x, non_constants) else x
        return nestedmap(result, self.args)

    @property
    def symbols(self):
        """Set of symbolic register operands"""
        return [x for x in flatten(self.operands)]

    # ______________________________________________________________________

    def _set_registers(self, *ops):
        "Set virtual register names if unset for each Op in ops"
        for op in ops:
            if not op.result:
                op.result = self.function.temp()
        return ops

    # ______________________________________________________________________

    def __repr__(self):
        if self.result:
            return "%%%s" % self.result
        return "? = %s(%s)" % (self.opcode, repr(self.operands))

    def __iter__(self):
        return iter((self.result, self.type, self.opcode, self.args))


class Constant(Value):
    """
    Constant value. A constant value is an int, a float or a struct
    (passes as a Struct).
    """

    __slots__ = ('opcode', 'type', 'args', 'result')

    def __init__(self, pyval, type=None):
        self.opcode = ops.constant
        self.type = type or types.typeof(pyval)
        self.args = [pyval]
        self.result = None

    def replace_op(self, opcode, args, type=None):
        raise RuntimeError("Constants cannot be replaced")

    def replace(self, newop):
        raise RuntimeError("Constants cannot be replaced")

    @property
    def const(self):
        const, = self.args
        return const

    def __hash__(self):
        return hash(self.type) ^ 0xd662a8f

    def __eq__(self, other):
        return (isinstance(other, Constant) and self.type == other.type and
                id(self.const) == id(other.const))

    def __repr__(self):
        return "constant(%s, %s)" % (self.const, self.type)


class Undef(Value):
    """Undefined value"""

    __slots__ = ('type',)

    def __init__(self, type):
        self.type = type


def _add_args(uses, newop, args):
    "Update uses when a new instruction is inserted"

    def add(arg):
        if isinstance(arg, (Op, FuncArg, Block)):
            uses[arg].add(newop)

    nestedmap(add, args)


def _del_args(uses, oldop, args):
    "Delete uses when an instruction is removed"
    seen = set() # Guard against duplicates in 'args'

    def remove(arg):
        if isinstance(arg, (FuncArg, Operation)) and arg not in seen:
            uses[arg].remove(oldop)
            seen.add(arg)

    nestedmap(remove, args)


Op = Operation
Const = Constant

########NEW FILE########
__FILENAME__ = linkedlist
# -*- coding: utf-8 -*-

"""
Doubly-linked list implementation.
"""

from __future__ import print_function, division, absolute_import

class LinkableItem(object):
    """
    Linked list item interface. Items must support the _prev and _next
    attributes initialized to None
    """

    def __init__(self, data=None):
        self.data  = data
        self._prev = None
        self._next = None

    def __eq__(self, other):
        return isinstance(other, LinkableItem) and self.data == other.data

    def __hash__(self):
        return hash(self.data)

    def __repr__(self):
        return "Item(%r)" % (self.data,)


class LinkedList(object):
    """Simple doubly linked list of objects with LinkableItem inferface"""

    def __init__(self, items=()):
        self._head = LinkableItem()
        self._tail = LinkableItem()
        self._head._next = self._tail
        self._tail._prev = self._head
        self.size = 0
        self.extend(items)

    def insert_before(self, a, b):
        """Insert a before b"""
        a._prev = b._prev
        a._next = b
        b._prev = a
        a._prev._next = a
        self.size += 1

    def insert_after(self, a, b):
        """Insert a after b"""
        assert b._next
        a._prev = b
        a._next = b._next
        b._next = a
        a._next._prev = a
        self.size += 1

    def remove(self, item):
        """Remove item from list"""
        item._prev._next = item._next
        item._next._prev = item._prev
        item._prev = None
        item._next = None
        self.size -= 1

    def append(self, item):
        """Append an item at the end"""
        self.insert_after(item, self._tail._prev)

    def extend(self, items):
        """Extend list at the end"""
        for op in items:
            self.append(op)

    @property
    def head(self):
        return self._head._next if self._head._next is not self._tail else None

    @property
    def tail(self):
        return self._tail._prev if self._tail._prev is not self._head else None

    def iter_inplace(self, from_op=None):
        cur = from_op or self._head._next
        end = self._tail
        while cur is not end:
            cur_next = cur._next # 'cur' may be deleted before we advance
            yield cur
            cur = cur._next or cur_next

    def __iter__(self, from_op=None):
        return iter(list(self.iter_inplace(from_op)))

    iter_from = __iter__

    def __len__(self):
        return self.size

    def __reversed__(self):
        return reversed(iter(self))

    def __repr__(self):
        return "LinkedList([%s])" % ", ".join(map(repr, self))
########NEW FILE########
__FILENAME__ = ops
from __future__ import print_function, division, absolute_import
import collections

try:
    intern
except NameError:
    intern = lambda s: s

#===------------------------------------------------------------------===
# Syntax
#===------------------------------------------------------------------===

all_ops = []
op_syntax = {} # Op -> Syntax

List  = collections.namedtuple('List',  []) # syntactic list
Value = collections.namedtuple('Value', []) # single Value
Const = collections.namedtuple('Const', []) # syntactic constant
Any   = collections.namedtuple('Any',   []) # Value | List
Star  = collections.namedtuple('Star',  []) # any following arguments
Obj   = collections.namedtuple('Obj',   []) # any object

fmts = {'l': List, 'v': Value, 'c': Const, 'a': Any, '*': Star, 'o': Obj}

# E.g. op('foo', List, Const, Value, Star) specificies an opcode 'foo' accepting
# as the argument list a list of arguments, a constant, an operation and any
# trailing arguments. E.g. [[], Const(...), Op(...)] would be valid.

def op(name, *args):
    if '/' in name:
        name, fmt = name.split('/')
        args = [fmts[c] for c in fmt]

    name = intern(name)
    all_ops.append(name)
    op_syntax[name] = list(args)
    return name

#===------------------------------------------------------------------===
# Typed IR (initial input)
#===------------------------------------------------------------------===

# IR Constants. Constants start with an uppercase letter

# math
Sin                = 'Sin'
Asin               = 'Asin'
Sinh               = 'Sinh'
Asinh              = 'Asinh'
Cos                = 'Cos'
Acos               = 'Acos'
Cosh               = 'Cosh'
Acosh              = 'Acosh'
Tan                = 'Tan'
Atan               = 'Atan'
Atan2              = 'Atan2'
Tanh               = 'Tanh'
Atanh              = 'Atanh'
Log                = 'Log'
Log2               = 'Log2'
Log10              = 'Log10'
Log1p              = 'Log1p'
Exp                = 'Exp'
Exp2               = 'Exp2'
Expm1              = 'Expm1'
Floor              = 'Floor'
Ceil               = 'Ceil'
Abs                = 'Abs'
Erfc               = 'Erfc'
Rint               = 'Rint'
Pow                = 'Pow'
Round              = 'Round'

# ______________________________________________________________________
# Constants

constant           = op('constant/o')         # object pyval

# ______________________________________________________________________
# Variables

alloca             = op('alloca/o')           # obj numItems [length of allocation implied by return type]
load               = op('load/v')             # alloc var
store              = op('store/vv')           # expr value, alloc var

# ______________________________________________________________________
# Conversion

convert            = op('convert/v')          # expr arg
bitcast            = op('bitcast/v')          # expr value

# ______________________________________________________________________
# Control flow

# Basic block leaders
phi                = op('phi/ll')             # expr *blocks, expr *values
exc_setup          = op('exc_setup/l')        # block *handlers
exc_catch          = op('exc_catch/l')        # expr *types

# Basic block terminators
jump               = op('jump/v')             # block target
cbranch            = op('cbranch/vvv')        # (expr test, block true_target,
                                              #  block false_target)
exc_throw          = op('exc_throw/v')        # expr exc
ret                = op('ret/o')              # expr result

# ______________________________________________________________________
# Functions

call               = op('call/vl')            # expr obj, expr *args
call_math          = op('call_math/ol')       # str name, expr *args

# ______________________________________________________________________
# sizeof

addressof          = op('addressof/v')        # expr obj
sizeof             = op('sizeof/v')           # expr obj

# ______________________________________________________________________
# Pointers

ptradd             = op('ptradd/vv')          # expr pointer, expr value
ptrload            = op('ptrload/v')          # expr pointer
ptrstore           = op('ptrstore/vv')        # expr value, expr pointer
ptrcast            = op('ptrcast/v')          # expr pointer
ptr_isnull         = op('ptr_isnull/v')       # expr pointer

# ______________________________________________________________________
# Unified: Structs/Arrays/Objects/Vectors

get                = op('get/vl')        # (expr value, list index)
set                = op('set/vvl')       # (expr value, expr value, list index)

# ______________________________________________________________________
# Attributes

getfield           = op('getfield/vo')        # (expr value, str attr)
setfield           = op('setfield/vov')       # (expr value, str attr, expr value)

# ______________________________________________________________________
# Fields

extractfield       = op('extractfield/vo')
insertfield        = op('insertfield/vov')

# ______________________________________________________________________
# Vectors

shufflevector      = op('shufflevector/vvv')  # (expr vector0, expr vector1, expr vector2)

# ______________________________________________________________________
# Basic operators

# Binary
add                = op('add/vv')
sub                = op('sub/vv')
mul                = op('mul/vv')
div                = op('div/vv')
mod                = op('mod/vv')
lshift             = op('lshift/vv')
rshift             = op('rshift/vv')
bitand             = op('bitand/vv')
bitor              = op('bitor/vv')
bitxor             = op('bitxor/vv')

# Unary
invert             = op('invert/v')
not_               = op('not_/v')
uadd               = op('uadd/v')
usub               = op('usub/v')

# Compare
eq                 = op('eq/vv')
ne                 = op('ne/vv')
lt                 = op('lt/vv')
le                 = op('le/vv')
gt                 = op('gt/vv')
ge                 = op('ge/vv')
is_                = op('is_/vv')

# ______________________________________________________________________
# Exceptions

check_error        = op('check_error/vv')   # (expr arg, expr badval)
new_exc            = op('new_exc/vv')       # (expr exc, expr? msg)

# ______________________________________________________________________
# Debugging

print              = op('print/v')

# ______________________________________________________________________
# Opcode utils

import fnmatch

void_ops = (print, store, ptrstore, exc_setup, exc_catch, jump, cbranch, exc_throw,
            ret, setfield, check_error)

is_leader     = lambda x: x in (phi, exc_setup, exc_catch)
is_terminator = lambda x: x in (jump, cbranch, exc_throw, ret)
is_void       = lambda x: x in void_ops

def oplist(pattern):
    """Given a pattern, return all matching opcodes, e.g. thread_*"""
    for name, value in globals().iteritems():
        if not name.startswith('__') and fnmatch.fnmatch(name, pattern):
            yield value

########NEW FILE########
__FILENAME__ = passes
"""
Passes that massage expression graphs into execution kernels.
"""

from __future__ import absolute_import, division, print_function

from functools import partial

from .prettyprint import verbose
from .frontend import (translate, partitioning, coercions, ckernel_impls,
                       ckernel_lift, allocation, ckernel_prepare,
                       ckernel_rewrite)
from ...io.sql.air import rewrite_sql

passes = [
    translate,

    partitioning.annotate_all_kernels,
    partitioning.partition,
    partitioning.annotate_roots,

    # erasure, # TODO: erase shape from ops
    # cache, # TODO:
    coercions,
    # TODO: Make the below compile-time passes !
    ckernel_prepare.prepare_local_execution,
    ckernel_impls,
    allocation,
    ckernel_lift,
    ckernel_rewrite,
    rewrite_sql,
]

debug_passes = [partial(verbose, p) for p in passes]

########NEW FILE########
__FILENAME__ = pattern
"""
Taken and slightly adapted from lair/backend/pattern.py
"""

from __future__ import print_function, division, absolute_import

import inspect
from functools import partial
from collections import namedtuple

Case = namedtuple('Case', ['pattern', 'function', 'argspec'])

class match(object):
    '''Dispatch a function by pattern matching.
    Start with the most generic case; Add more specialized cases afterwards.
    Pattern value of type `type` is matched using the builtin `isinstance`.
    Pattern value of type `Matcher` is used directly.
    Pattern value of other types is matched using `==`.
    '''
    def __init__(self, func):
        self._generic = func
        self._cases = []
        self._argspec = inspect.getargspec(func)

        assert not self._argspec.varargs, 'Thou shall not use *args'
        assert not self._argspec.keywords, 'Thou shall not use **kws'

    def case(self, *patargs, **patkws):
        def wrap(fn):
            argspec = inspect.getargspec(fn)
            assert len(argspec.args) == len(self._argspec.args), "mismatch signature"
            for pat, arg in zip(patargs, argspec.args):
                assert arg not in patkws
                patkws[arg] = pat
            case = Case(_prepare_pattern(patkws.items()), fn, argspec)
            self._cases.append(case)
            return self
        return wrap

    def __get__(self, inst, type=None):
        return partial(self, inst)

    def __call__(self, *args, **kwds):
        for case in reversed(self._cases):
            kws = dict(kwds)
            _pack_args(case.argspec, args, kws)
            for k, matcher in case.pattern:
                if not matcher(kws[k]):
                    break
            else:
                return case.function(*args, **kwds)
        else:
            return self._generic(*args, **kwds)


def _pack_args(argspec, args, kws):
    args = list(args)
    for v, k in zip(args, argspec.args):
        if k in kws:
            return NameError(k)
        else:
            kws[k] = v


def _prepare_pattern(pats):
    return tuple((k, _select_matcher(v)) for k, v in pats)


def _select_matcher(v):
    if isinstance(v, Matcher):
        return v
    elif isinstance(v, type):
        return InstanceOf(v)
    else:
        return Equal(v)


class Matcher(object):
    __slots__ = 'arg'
    def __init__(self, arg):
        self.arg = arg


class InstanceOf(Matcher):
    def __call__(self, x):
        return isinstance(x, self.arg)


class Equal(Matcher):
    def __call__(self, x):
        return self.arg == x


class Custom(Matcher):
    def __call__(self, x):
        return self.arg(x)

custom = Custom     # alias

########NEW FILE########
__FILENAME__ = pipeline
"""
Pipeline that determines phase ordering and execution.
"""

from __future__ import absolute_import, division, print_function
import types


def run_pipeline(func, env, passes):
    """
    Run a sequence of transforms (given as functions or modules) on the
    AIR function.
    """
    for transform in passes:
        func, env = apply_transform(transform, func, env)
    return func, env


def apply_transform(transform, func, env):
    if isinstance(transform, types.ModuleType):
        result = transform.run(func, env)
    else:
        result = transform(func, env)

    _check_transform_result(transform, result)
    return result or (func, env)


def _check_transform_result(transform, result):
    if result is not None and not isinstance(result, tuple):
        if isinstance(transform, types.ModuleType):
            transform = transform.run
        transform = transform.__module__ + '.' + transform.__name__
        raise ValueError(
            "Expected (func, env) result in %r, got %s" % (transform, result))

########NEW FILE########
__FILENAME__ = prettyprint
"""
Pretty printing of AIR.
"""

from __future__ import print_function, division, absolute_import

import difflib
import dis
import types

from . import pipeline
from .utils import hashable

prefix = lambda s: '%' + s
indent = lambda s: '\n'.join('    ' + s for s in s.splitlines())
ejoin  = "".join
sjoin  = " ".join
ajoin  = ", ".join
njoin  = "\n".join
parens = lambda s: '(' + s + ')'

compose = lambda f, g: lambda x: f(g(x))



def diff(before, after):
    """Diff two strings"""
    lines = difflib.Differ().compare(before.splitlines(), after.splitlines())
    return "\n".join(lines)


def pretty(value):
    formatter = formatters[type(value).__name__]
    return formatter(value)


def fmod(mod):
    gs, fs = mod.globals.values(), mod.functions.values()
    return njoin([njoin(map(pretty, gs)), "", njoin(map(pretty, fs))])


def ffunc(f):
    restype = ftype(f.type.restype)
    types, names = map(ftype, f.type.argtypes), map(prefix, f.argnames)
    args = ajoin(map(sjoin, zip(types, names)))
    header = sjoin(["function", restype, f.name + parens(args)])
    return njoin([header + " {", njoin(map(fblock, f.blocks)), "}"])


def farg(func_arg):
    return "%" + func_arg.result


def fblock(block):
    body = njoin(map(compose(indent, fop), block))
    return njoin([block.name + ':', body, ''])


def _farg(oparg):
    from . import ir

    if isinstance(oparg, (ir.Function, ir.Block)):
        return prefix(oparg.name)
    elif isinstance(oparg, list):
        return "[%s]" % ", ".join(_farg(arg) for arg in oparg)
    elif isinstance(oparg, ir.Op):
        return prefix(str(oparg.result))
    else:
        return str(oparg)


def fop(op):
    body = "%s(%s)" % (op.opcode, ajoin(map(_farg, op.args)))
    return '%%%-5s = %s -> %s' % (op.result, body, ftype(op.type))


def fconst(c):
    return 'const(%s, %s)' % (c.const, ftype(c.type))


def fglobal(val):
    return "global %{0} = {1}".format(val.name, ftype(val.type))


def fundef(val):
    return '((%s) Undef)' % (val.type,)


def ftype(val, seen=None):
    from pykit import types

    if not isinstance(val, types.Type):
        return str(val)

    if seen is None:
        seen = set()
    if id(val) in seen:
        return '...'

    seen.add(id(val))

    if hashable(val) and val in types.type2name:
        result = types.type2name[val]
    elif val.is_struct:
        args = ", ".join('%s:%s' % (name, ftype(ty, seen))
                         for name, ty in zip(val.names, val.types))
        result = '{ %s }' % args
    elif val.is_pointer:
        result ="%s*" % (ftype(val.base, seen),)
    else:
        result = repr(val)

    seen.remove(id(val))
    return result


def fptr(val):
    return repr(val)


def fstruct(val):
    return repr(val)


formatters = {
    'Module':      fmod,
    'GlobalValue': fglobal,
    'Function':    ffunc,
    'FuncArg':     farg,
    'Block':       fblock,
    'Operation':   fop,
    'Constant':    fconst,
    'Undef':       fundef,
    'Pointer':     fptr,
    'Struct':      fstruct,
}


def debug_print(func, env):
    """
    Returns whether to enable debug printing.
    """
    from . import ir
    return isinstance(func, ir.Function)


def verbose(p, func, env):
    if not debug_print(func, env):
        return pipeline.apply_transform(p, func, env)

    title = "%s [ %s %s(%s) ]" % (_passname(p), func.type.restype,
                                  _funcname(func),
                                  ", ".join(map(str, func.type.argtypes)))

    print(title.center(60).center(90, "-"))

    if isinstance(func, types.FunctionType):
        dis.dis(func)
        func, env = pipeline.apply_transform(p, func, env)
        print()
        print(func)
        return func, env

    before = _formatfunc(func)
    func, env = pipeline.apply_transform(p, func, env)
    after = _formatfunc(func)

    if before != after:
        print(diff(before, after))

    return func, env


def _passname(transform):
    return transform.__name__
    #if isinstance(transform, types.ModuleType):
    #    return transform.__name__
    #else:
    #    return ".".join([transform.__module__, transform.__name__])


def _funcname(func):
    if isinstance(func, types.FunctionType):
        return func.__name__
    else:
        return func.name


def _formatfunc(func):
    if isinstance(func, types.FunctionType):
        dis.dis(func)
        return ""
    else:
        return str(func)

########NEW FILE########
__FILENAME__ = test_ir
from __future__ import absolute_import, division, print_function

import unittest

from datashape import dshape
from blaze.compute.air.tests.utils import make_graph


class TestIR(unittest.TestCase):

    def test_ir(self):
        f, graph = make_graph()

        # Structure
        self.assertEqual(len(f.blocks), 1)
        self.assertTrue(f.startblock.is_terminated())

        # Types
        got      = [op.type for op in f.ops][:-1]
        expected = [dshape("10 * float64"), dshape("10 * complex[float64]")]
        self.assertEqual(got, expected)

        # function 10, complex[float64] expr0(10, int32 %e0, 10, float64 %e1, 10, complex[float64] %e2) {
        # entry:
        #     %0 = (10, float64) kernel(%const(Bytes, blaze.ops.ufuncs.add), %e0, %e1)
        #     %1 = (10, complex[float64]) kernel(%const(Bytes, blaze.ops.ufuncs.mul), %0, %e2)
        #     %2 = (Void) ret(%1)
        #
        # }


if __name__ == '__main__':
    # TestIR('test_ir').debug()
    unittest.main()

########NEW FILE########
__FILENAME__ = test_transforms
from __future__ import absolute_import, division, print_function

import unittest

from datashape import dshape
from blaze.compute.air.frontend import coercions
from blaze.compute.air.tests.utils import make_graph


class TestCoercions(unittest.TestCase):

    def test_coercions(self):
        f, graph = make_graph()
        coercions.run(f)
        ops = [(op.opcode, op.type) for op in f.ops][:-1]
        expected = [('convert', dshape("10 * float64")),
                    ('kernel', dshape("10 * float64")),
                    ('convert', dshape("10 * complex[float64]")),
                    ('kernel', dshape("10 * complex[float64]"))]
        self.assertEqual(ops, expected)

        # function 10, complex[float64] expr0(10, float64 %e0, 10, int32 %e1, 10, complex[float64] %e2) {
        # entry:
        #     %3 = (10, float64) convert(%e1)
        #     %0 = (10, float64) kernel(%const(Bytes, blaze.ops.ufuncs.add), %3, %e0)
        #     %4 = (10, complex[float64]) convert(%0)
        #     %1 = (10, complex[float64]) kernel(%const(Bytes, blaze.ops.ufuncs.mul), %4, %e2)
        #     %2 = (Void) ret(%1)
        #
        # }


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import, division, print_function

from datashape import dshape
import blaze
from blaze.compute.ops.ufuncs import add, multiply
from blaze.compute.air.frontend.translate import from_expr

#------------------------------------------------------------------------
# Utils
#------------------------------------------------------------------------

def make_graph():
    a = blaze.array(range(10), dshape('10 * int32'))
    b = blaze.array(range(10), dshape('10 * float64'))
    c = blaze.array([i+0j for i in range(10)],
                    dshape('10 * complex[float64]'))

    result = multiply(add(a, b), c)
    graph, expr_ctx = result.expr

    f = from_expr(graph, expr_ctx, {})

    return f, graph

########NEW FILE########
__FILENAME__ = tracing
"""Interpreter tracing of air programs."""

from __future__ import print_function, division, absolute_import
from collections import namedtuple

from .ir import Value
from .utils import nestedmap

#===------------------------------------------------------------------===
# Trace Items
#===------------------------------------------------------------------===

Call = namedtuple('Call', ['func', 'args'])
Op   = namedtuple('Op',   ['op', 'args'])
Res  = namedtuple('Res',  ['op', 'args', 'result'])
Ret  = namedtuple('Ret',  ['result'])
Exc  = namedtuple('Exc',  ['exc'])

#===------------------------------------------------------------------===
# Tracer
#===------------------------------------------------------------------===

def reprobj(obj):
    try: return str(obj)
    except Exception: pass

    try: return repr(obj)
    except Exception: pass

    try: return "Unprintable(%s)" % (vars(obj),)
    except Exception: pass

    return "<unprintable object %s>" % (type(obj),)


def _format_arg(arg):
    if isinstance(arg, Value):
        return repr(arg)
    elif isinstance(arg, dict) and sorted(arg) == ['type', 'value']:
        return '{value=%s}' % (arg['value'],)
    return reprobj(arg)

def _format_args(args):
    return ", ".join(map(str, nestedmap(_format_arg, args)))

class Tracer(object):
    """
    Collects and formats an execution trace when interpreting a program.
    """

    def __init__(self, record=False):
        """
        record: whether to record the trace for later inspection
        """
        self.stmts = []
        self.record = record
        self.beginning = True

        self.callstack = [] # stack of function calls
        self.indent = 0     # indentation level

    @property
    def func(self):
        """Currently executing function"""
        return self.callstack[-1]

    def push(self, item):
        """
        Push a trace item, which is a Stmt or a Call, for processing.
        """
        self.format_item(item)
        if self.record:
            self.stmts.append(item)

    def format_item(self, item):
        """
        Display a single trace item.
        """
        if isinstance(item, Call):
            self.call(item.func)
            self.emit("\n")
            self.emit(" --------> %s(%s)" % (item.func.name,
                                             _format_args(item.args)))
        elif isinstance(item, Op):
            opcode = item.op.opcode
            args = "(%s)" % _format_args(item.args)
            self.emit("%-10s: op %%%-5s: %-80s" % (item.op.block.name,
                                                   item.op.result,
                                                   opcode + args), end='')
        elif isinstance(item, Res):
            if item.result is not None:
                self.emit(" -> %s" % (_format_arg(item.result),))
            else:
                self.emit("")
        elif isinstance(item, Ret):
            self.emit(" <---- (%s) ---- %s" % (_format_arg(item.result),
                                               self.callstack[-1].name))
            self.ret()
        elif isinstance(item, Exc):
            self.emit("\n")
            self.emit(" <-------- propagating %s from %s" % (item.exc,
                                                             self.func.name))
            self.ret()

    def emit(self, s, end="\n"):
        if self.beginning:
            parts = self.func.name.split(".")[-2:]
            name = ".".join(parts)
            print("%-20s: " % name, end="")
        self.beginning = (end == "\n")
        print(" " * self.indent + s, end=end)

    def call(self, func):
        self.callstack.append(func)
        self.indent += 4

    def ret(self):
        self.indent -= 4
        self.callstack.pop()

class DummyTracer(Tracer):

    def format_item(self, item):
        pass

#===------------------------------------------------------------------===
# Utils
#===------------------------------------------------------------------===

def format_stream(stream):
    """
    Format a stream of trace items.
    """
    tracer = Tracer()
    for item in stream:
        tracer.push(item)

########NEW FILE########
__FILENAME__ = traits
"""
Minimal traits implementation:

    @traits
    class MyClass(object):

        attr = Instance(SomeClass)
        my_delegation = Delegate('attr')
"""


class TraitBase(object):
    """Base class for traits"""

    def __init__(self, value, doc=None):
        self.value = value
        self.doc = doc

    def set_attr_name(self, name):
        self.attr_name = name


class Delegate(TraitBase):
    """Delegate to some other object."""

    def __init__(self, value, delegate_attr_name=None, doc=None):
        super(Delegate, self).__init__(value, doc=doc)
        self.delegate_attr_name = delegate_attr_name

    def obj(self, instance):
        return getattr(instance, self.value)

    @property
    def attr(self):
        return self.delegate_attr_name or self.attr_name

    def __get__(self, instance, owner):
        return getattr(self.obj(instance), self.attr)

    def __set__(self, instance, value):
        return setattr(self.obj(instance), self.attr, value)

    def __delete__(self, instance):
        delattr(self.obj(instance), self.attr)


def traits(cls):
    "@traits class decorator"
    for name, py_func in vars(cls).items():
        if isinstance(py_func, TraitBase):
            py_func.set_attr_name(name)

    return cls

########NEW FILE########
__FILENAME__ = traversal
"""Visitor and transformer helpers.

    transform(transformer, func):
        transform Ops in func using transformer

    visit(visitor, func):
        visit Ops in func

    vvisit(visitor, func):
        visit Ops in func and track values for each Op, returned
        by each visit method

    Combinator([visitors...]):
        Combine a bunch of visitors into one
"""

from __future__ import print_function, division, absolute_import
import inspect

from .utils import nestedmap
from .error import CompileError


def _missing(visitor, op):
    raise CompileError(
                "Opcode %r not implemented by %s" % (op.opcode, visitor))


def transform(obj, function, handlers=None, errmissing=False):
    """Transform a bunch of operations"""
    obj = combine(obj, handlers)
    for op in function.ops:
        fn = getattr(obj, 'op_' + op.opcode, None)
        if fn is not None:
            result = fn(op)
            if result is not None and result is not op:
                op.replace(result)
        elif errmissing:
            _missing(obj, op)


def visit(obj, function, handlers=None, errmissing=False):
    """Visit a bunch of operations"""
    obj = combine(obj, handlers)
    for op in function.ops:
        fn = getattr(obj, 'op_' + op.opcode, None)
        if fn is not None:
            fn(op)
        elif errmissing:
            _missing(obj, op)


def vvisit(obj, function, argloader=None, valuemap=None, errmissing=True):
    """
    Visit a bunch of operations and track values. Uses ArgLoader to
    resolve Op arguments.
    """
    argloader = argloader or ArgLoader()
    valuemap = argloader.store if valuemap is None else valuemap

    for arg in function.args:
        valuemap[arg.result] = obj.op_arg(arg)

    for block in function.blocks:
        obj.blockswitch(argloader.load_Block(block))
        for op in block.ops:
            fn = getattr(obj, 'op_' + op.opcode, None)
            if fn is not None:
                args = argloader.load_args(op)
                result = fn(op, *args)
                valuemap[op.result] = result
            elif errmissing:
                _missing(obj, op)

    return valuemap


class ArgLoader(object):
    """
    Resolve Operation values and Operation arguments. This keeps a store that
    can be used for translation or interpretation, mapping IR values to
    translation or runtime values (e.g. LLVM or Python values).

        store: { Value : Result }
    """

    def __init__(self, store=None):
        self.store = store if store is not None else {}

    def load_op(self, op):
        from pykit.ir import Value, Op

        if isinstance(op, Value):
            return getattr(self, 'load_' + type(op).__name__)(op)
        else:
            return op

    def load_args(self, op):
        if op.opcode == 'phi':
            # phis have cycles and values cannot be loaded in a single pass
            return ()
        return nestedmap(self.load_op, op.args)

    def load_Block(self, arg):
        return arg

    def load_Constant(self, arg):
        return arg.const

    def load_Pointer(self, arg):
        return arg

    def load_Struct(self, arg):
        return arg

    def load_GlobalValue(self, arg):
        raise NotImplementedError

    def load_Function(self, arg):
        return arg

    def load_Operation(self, arg):
        if arg.result not in self.store:
            raise NameError("%s not in %s" % (arg, self.store))
        return self.store[arg.result]

    load_FuncArg = load_Operation


class Combinator(object):
    """
    Combine several visitors/transformers into one.
    One can also use dicts wrapped in pykit.utils.ValueDict.
    """

    def __init__(self, visitors, prefix='op_', index=None):
        self.visitors = visitors
        self.index = _build_index(visitors, prefix)
        if index:
            assert not set(index) & set(self.index)
            self.index.update(index)

    def __getattr__(self, attr):
        try:
            return self.index[attr]
        except KeyError:
            if len(self.visitors) == 1:
                # no ambiguity
                return getattr(self.visitors[0], attr)
            raise AttributeError(attr)


def _build_index(visitors, prefix):
    """Build a method table of method names starting with `prefix`"""
    index = {}
    for visitor in visitors:
        for attr, method in inspect.getmembers(visitor):
            if attr.startswith(prefix):
                if attr in index:
                    raise ValueError("Handler %s not unique!" % attr)
                index[attr] = method

    return index


def combine(visitor, handlers):
    """Combine a visitor/transformer with a handler dict ({'name': func})"""
    if handlers:
        visitor = Combinator([visitor], index=handlers)
    return visitor

########NEW FILE########
__FILENAME__ = types
"""
AIR types.
"""

from __future__ import print_function, division, absolute_import

from itertools import starmap
from collections import namedtuple
from functools import partial

from .utils import invert, hashable


alltypes = set()


class Type(object):
    """Base of types"""

    def __eq__(self, other):
        incompatible = (type(self) != type(other) and not (self.is_typedef or
                                                           other.is_typedef))
        if not isinstance(other, Type) or incompatible:
            return False

        self_recursive = recursive_terms(self)
        other_recursive = recursive_terms(other)

        if len(self_recursive) != len(other_recursive):
            return False
        elif self_recursive:
            return compare_recursive(self_recursive, other_recursive, {}, self, other)
        else:
            return (super(Type, self).__eq__(other) or
                    (self.is_typedef and self.type == other) or
                    (other.is_typedef and other.type == self))

    def __ne__(self, other):
        return not (self == other)

    def __nonzero__(self):
        return True

    def __hash__(self):
        if self.is_struct:
            return 0 # TODO: better hashing
        obj = tuple(tuple(c) if isinstance(c, list) else c for c in self)
        return hash(obj)


def compare_recursive(rec1, rec2, mapping, t1, t2):
    """Structural comparison of recursive types"""
    cmp = partial(compare_recursive, rec1, rec2, mapping)

    sub1 = subterms(t1)
    sub2 = subterms(t2)

    if id(t1) in rec1:
        if id(t1) in mapping:
            return mapping[id(t1)] == id(t2)

        mapping[id(t1)] = id(t2)

    if bool(sub1) ^ bool(sub2) or type(t1) != type(t2):
        return False
    elif not sub1:
        return t1 == t2 # Unit types
    elif t1.is_struct:
        return (t1.names == t2.names and
                all(starmap(cmp, zip(t1.types, t2.types))))
    elif t1.is_function:
        return (t1.varargs == t2.varargs and
                cmp(t1.restype, t2.restype) and
                all(starmap(cmp, zip(t1.argtypes, t2.argtypes))))
    elif t1.is_vector or t1.is_array:
        return t1.count == t2.count and cmp(t1.base, t2.base)
    elif t1.is_pointer:
        return cmp(t1.base, t2.base)


def subterms(type):
    if type.is_struct:
        return type.types
    elif type.is_pointer or type.is_vector or type.is_array:
        return [type.base]
    elif type.is_function:
        return [type.restype] + list(type.argtypes)
    else:
        return []


def recursive_terms(type, seen=None, recursive=None):
    """Find all recursive terms in a type"""
    if seen is None:
        seen = set()
        recursive = set()

    if id(type) in seen:
        recursive.add(id(type))
        return recursive

    seen.add(id(type))
    for subterm in subterms(type):
        recursive_terms(subterm, seen, recursive)
    seen.remove(id(type))

    return recursive

def typetuple(name, elems):
    def __str__(self):
        from .ir import pretty
        return pretty.ftype(self)

    def __repr__(self):
        return "%s(%s)" % (name, ", ".join(str(getattr(self, attr)) for attr in elems))

    ty = type(name, (Type, namedtuple(name, elems)), {'__str__': __str__,
                                                      '__repr__': __repr__})
    alltypes.add(ty)
    return ty

VoidT      = typetuple('Void',     [])
Boolean    = typetuple('Bool',     [])
Integral   = typetuple('Int',      ['bits', 'unsigned'])
Real       = typetuple('Real',     ['bits'])
Array      = typetuple('Array',    ['base', 'count'])
Vector     = typetuple('Vector',   ['base', 'count'])
Struct     = typetuple('Struct',   ['names', 'types'])
Pointer    = typetuple('Pointer',  ['base'])
Function   = typetuple('Function', ['restype', 'argtypes', 'varargs'])
ExceptionT = typetuple('Exception',[])
BytesT     = typetuple('Bytes',    [])
OpaqueT    = typetuple('Opaque',   []) # Some type we make zero assumptions about

# These are user-defined types
# Complex    = typetuple('Complex',  ['base'])
# ObjectT    = typetuple('Object',   [])

class Typedef(typetuple('Typedef',  ['name', 'type'])):
    def __init__(self, name, ty):
        setattr(self, 'is_' + type(ty).__name__.lower(), True)


for ty in alltypes:
    attr = 'is_' + ty.__name__.lower()
    for ty2 in alltypes:
        setattr(ty2, attr, False)
    setattr(ty, attr, True)

# ______________________________________________________________________
# Types

Void    = VoidT()
Bool    = Boolean()
Int8    = Integral(8,  False)
Int16   = Integral(16, False)
Int32   = Integral(32, False)
Int64   = Integral(64, False)
Int128  = Integral(128, False)
UInt8   = Integral(8,  True)
UInt16  = Integral(16, True)
UInt32  = Integral(32, True)
UInt64  = Integral(64, True)
UInt128 = Integral(128, True)

Vector64x2 = Vector(UInt64, 2)
Vector32x4 = Vector(UInt32, 4)
Vector16x8 = Vector(UInt16, 8)

Float32  = Real(32)
Float64  = Real(64)
# Float128 = Real(128)

# Object    = ObjectT()
Exception = ExceptionT()
Bytes     = BytesT()
Opaque    = OpaqueT()

# Typedefs
Char      = Typedef("Char", Int8)
Short     = Typedef("Short", Int16)
Int       = Typedef("Int", Int32)
Long      = Typedef("Long", Int32)
LongLong  = Typedef("LongLong", Int32)

UChar     = Typedef("UChar", UInt8)
UShort    = Typedef("UShort", UInt16)
UInt      = Typedef("UInt", UInt32)
ULong     = Typedef("ULong", UInt32)
ULongLong = Typedef("ULongLong", UInt32)

# ______________________________________________________________________

signed_set   = frozenset([Int8, Int16, Int32, Int64, Int128])
unsigned_set = frozenset([UInt8, UInt16, UInt32, UInt64, UInt128])
int_set      = signed_set | unsigned_set
float_set    = frozenset([Float32, Float64])
# complex_set  = frozenset([Complex64, Complex128])
bool_set     = frozenset([Bool])
numeric_set  = int_set | float_set # | complex_set
scalar_set   = numeric_set | bool_set

# ______________________________________________________________________
# Internal

VirtualTable  = typetuple('VirtualTable',  ['obj_type'])
VirtualMethod = typetuple('VirtualMethod', ['obj_type'])

# ______________________________________________________________________
# Parsing

def parse_type(s):
    from pykit.parsing import parser
    return parser.build(parser.parse(s, parser.type_parser))

# ______________________________________________________________________
# Typeof

typing_defaults = {
    bool:       Bool,
    int:        Int32,
    float:      Float64,
    # These types are not actually supported
    str:        Bytes,
    bytes:      Bytes,
}

def typeof(value):
    """Python value -> type"""
    return typing_defaults[type(value)]

# ______________________________________________________________________
# Convert

conversion_map = invert(typing_defaults)
conversion_map.update(dict.fromkeys(int_set, int))
conversion_map.update(dict.fromkeys(float_set, float))
# conversion_map.update(dict.fromkeys(complex_set, complex))

def convert(value, dst_type):
    """(python value, type) -> converted python value"""
    if dst_type.is_typedef:
        dst_type = dst_type.type
    converter = conversion_map[dst_type]
    return converter(value)

# ______________________________________________________________________

type2name = dict((v, n) for n, v in globals().items() if hashable(v))
typename = type2name.__getitem__

def resolve_typedef(type):
    while type.is_typedef:
        type = type.type
    return type

########NEW FILE########
__FILENAME__ = utils
from __future__ import print_function, division, absolute_import

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

import string
import functools
import collections
from itertools import chain

map    = lambda *args: list(builtins.map(*args))
invert = lambda d: dict((v, k) for k, v in d.items())

def linearize(func):
    """
    Return a linearized from of the IR and a dict mapping basic blocks to
    offsets.
    """
    result = []
    blockstarts = {} # { block_label : instruction offset }
    for block in func.blocks:
        blockstarts[block.name] = len(result)
        result.extend(iter(block))

    return result, blockstarts

def nestedmap(f, args, type=list):
    """
    Map `f` over `args`, which contains elements or nested lists
    """
    result = []
    for arg in args:
        if isinstance(arg, type):
            result.append(list(map(f, arg)))
        else:
            result.append(f(arg))

    return result

def flatten(args):
    """Flatten nested lists (return as iterator)"""
    for arg in args:
        if isinstance(arg, list):
            for x in arg:
                yield x
        else:
            yield arg

def mutable_flatten(args):
    """Flatten nested lists (return as iterator)"""
    for arg in args:
        if isinstance(arg, list):
            for x in arg:
                yield x
        else:
            yield arg

def mergedicts(*dicts):
    """Merge all dicts into a new dict"""
    return dict(chain(*[d.items() for d in dicts]))

def listify(f):
    """Decorator to turn generator results into lists"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return list(f(*args, **kwargs))
    return wrapper

@listify
def listitems(fields):
    """Turn [1, [2, 3], (4,)] into [[1], [2, 3], [4]]"""
    for x in fields:
        if not isinstance(x, (list, tuple)):
            yield [x]
        else:
            yield list(x)

@listify
def prefix(iterable, prefix):
    """Prefix each item from the iterable with a prefix"""
    for item in iterable:
        yield prefix + item

# ______________________________________________________________________
# Strings

def substitute(s, **substitutions):
    """Use string.Template to substitute placeholders in a string"""
    return string.Template(s).substitute(**substitutions)

# ______________________________________________________________________

def hashable(x):
    try:
        hash(x)
    except TypeError:
        return False
    else:
        return True

# ______________________________________________________________________

class ValueDict(object):
    """
    Use dict values as attributes.
    """

    def __init__(self, d):
        self.__getattr__ = d.__getitem__
        self.__setattr__ = d.__setitem__
        self.__detattr__ = d.__detitem__

# ______________________________________________________________________

def call_once(f):
    """Cache the result of the function, so that it's called only once"""
    result = []
    def wrapper(*args, **kwargs):
        if len(result) == 0:
            ret = f(*args, **kwargs)
            result.append(ret)

        return result[0]
    return wrapper

def cached(limit=1000):
    """Cache the result for the arguments just once"""
    def decorator(f):
        cache = {}
        def wrapper(*args):
            if args not in cache:
                if len(cache) > limit:
                    cache.popitem()
                cache[args] = f(*args)
            return cache[args]
        return wrapper
    return decorator

# ______________________________________________________________________

def make_temper():
    """Return a function that returns temporary names"""
    temps = collections.defaultdict(int)
    seen = set()

    def temper(input=""):
        name, dot, tail = input.rpartition('.')
        if tail.isdigit():
            varname = name
        else:
            varname = input

        count = temps[varname]
        temps[varname] += 1
        if varname and count == 0:
            result = varname
        else:
            result = "%s.%d" % (varname, count)

        assert result not in seen
        seen.add(result)

        return result

    return temper

# ______________________________________________________________________


def _getops(func_or_block_or_list):
    if isinstance(func_or_block_or_list, list):
        return func_or_block_or_list
    return func_or_block_or_list.ops


def findop(container, opcode):
    """Find the first Operation with the given opcode"""
    for op in _getops(container):
        if op.opcode == opcode:
            return op


def findallops(container, opcode):
    """Find all Operations with the given opcode"""
    found = []
    for op in _getops(container):
        if op.opcode == opcode:
            found.append(op)

    return found

########NEW FILE########
__FILENAME__ = verification
"""
Verify the validity of  IR.
"""

from __future__ import print_function, division, absolute_import
import functools

from .types import (Boolean, Integral, Real, Array, Struct, Pointer,
                    Vector, resolve_typedef)
from .ir import Function, Block, Value, Operation, Constant
from .traversal import visit, combine
from . import ops
from .pattern import match
from .utils import findallops

#===------------------------------------------------------------------===
# Utils
#===------------------------------------------------------------------===

class VerifyError(Exception):
    """Raised when we fail to verify IR"""

def unique(items):
    """Assert uniqueness of items"""
    seen = set()
    for item in items:
        if item in seen:
            raise VerifyError("Item not unique", item)
        seen.add(item)

#===------------------------------------------------------------------===
# Entry points
#===------------------------------------------------------------------===

@match
def verify(value, env=None):
    if isinstance(value, Function):
        verify_function(value)
    elif isinstance(value, Block):
        verify_operations(value)
    elif isinstance(value, Operation):
        verify_operation(value)
    else:
        assert isinstance(value, Value)

    return value, env

def op_verifier(func):
    """Verifying decorator for functions return a new (list of) Op"""
    @functools.wraps(func)
    def wrapper(*a, **kw):
        op = func(*a, **kw)
        if not isinstance(op, list):
            op = [op]
        for op in op:
            verify_op_syntax(op)
        return op

    return wrapper

#===------------------------------------------------------------------===
# Internal verification
#===------------------------------------------------------------------===

def verify_module(mod):
    """Verify a pykit module"""
    assert not set.intersection(set(mod.functions), set(mod.globals))
    for function in mod.functions.itervalues():
        verify_function(function)

def verify_function(func):
    try:
        _verify_function(func)
    except Exception as e:
        raise VerifyError("Error verifying function %s: %s" % (func.name, e))

def _verify_function(func):
    """Verify a pykit function"""
    # Verify arguments
    assert len(func.args) == len(func.type.argtypes)

    # Verify return presence and type
    restype = func.type.restype
    if not restype.is_void and not restype.is_opaque:
        rets = findallops(func, 'ret')
        for ret in rets:
            arg, = ret.args
            assert arg.type == restype, (arg.type, restype)

    verify_uniqueness(func)
    verify_block_order(func)
    verify_operations(func)
    verify_uses(func)
    verify_semantics(func)

def verify_uniqueness(func):
    """Verify uniqueness of register names and labels"""
    unique(block.name for block in func.blocks)
    unique(op for block in func.blocks for op in block)
    unique(op.result for block in func.blocks for op in block)

def verify_block_order(func):
    """Verify block order according to dominator tree"""
    from pykit.analysis import cfa

    flow = cfa.cfg(func)
    dominators = cfa.compute_dominators(func, flow)

    visited = set()
    for block in func.blocks:
        visited.add(block.name)
        for dominator in dominators[block.name]:
            if dominator not in visited:
                raise VerifyError("Dominator %s does not precede block %s" % (
                                                        dominator, block.name))

def verify_operations(func_or_block):
    """Verify all operations in the function or block"""
    for op in func_or_block.ops:
        verify_operation(op)

def verify_operation(op):
    """Verify a single Op"""
    assert op.block is not None, op
    assert op.result is not None, op
    verify_op_syntax(op)

def verify_op_syntax(op):
    """
    Verify the syntactic structure of the Op (arity, List/Value/Const, etc)
    """
    if op.opcode not in ops.op_syntax:
        return

    syntax = ops.op_syntax[op.opcode]
    vararg = syntax and syntax[-1] == ops.Star
    args = op.args
    if vararg:
        syntax = syntax[:-1]
        args = args[:len(syntax)]

    assert len(syntax) == len(args), (op, syntax)
    for arg, expected in zip(args, syntax):
        msg = (op, arg)
        if expected == ops.List:
            assert isinstance(arg, list), msg
        elif expected == ops.Const:
            assert isinstance(arg, Constant), msg
        elif expected == ops.Value:
            if op.opcode == "alloca":
                assert arg is None or isinstance(arg, Value), msg
            else:
                assert isinstance(arg, Value), msg
        elif expected == ops.Any:
            assert isinstance(arg, (Value, list)), msg
        elif expected == ops.Obj:
            pass
        else:
            raise ValueError("Invalid meta-syntax?", msg, expected)

def verify_uses(func):
    """Verify the def-use chains"""
    # NOTE: verify should be importable from any pass!
    from pykit.analysis import defuse
    uses = defuse.defuse(func)
    diff = set.difference(set(uses), set(func.uses))
    assert not diff, diff
    # assert uses == func.uses, (uses, func.uses)

# ______________________________________________________________________

class Verifier(object):
    """Semantic verification of all operations"""

def verify_semantics(func, env=None):
    verifier = combine(Verifier(), env and env.get("verify.handlers"))
    visit(verifier, func)

# ______________________________________________________________________

class LowLevelVerifier(object):

    def op_unary(self, op):
        assert type(op.type) in (Integral, Real)

    def op_binary(self, op):
        assert type(op.type) in (Integral, Real)

    def op_compare(self, op):
        assert type(op.type) in (Boolean,)
        left, right = op.args
        assert left.type == right.type
        assert type(left.type) in (Boolean, Integral, Real)

    def op_getfield(self, op):
        struct, attr = op.args
        assert struct.type.is_struct

    def op_setfield(self, op):
        struct, attr, value = op.args
        assert struct.type.is_struct


def verify_lowlevel(func):
    """
    Assert that the function is lowered for code generation.
    """
    for op in func.ops:
        assert type(resolve_typedef(op.type)) in (
            Boolean, Array, Integral, Real, Struct, Pointer, Function, Vector), op

########NEW FILE########
__FILENAME__ = _generate
#! /usr/bin/env python

"""
Generate some internal code.
"""

from __future__ import absolute_import
from collections import defaultdict
from os.path import splitext

from blaze.compute.air import ops, defs

def getorder():
    pos = defaultdict(int) # { 'opname': index }
    fn, ext = splitext(ops.__file__)
    lines = list(open(fn + '.py'))
    for name, op in vars(ops).items():
        if isinstance(op, str) and name not in ('__file__', '__name__',
                                                       'constant'):
            for i, line in enumerate(lines):
                if line.startswith(op):
                    pos[op] = i
                    break

    order = sorted((lineno, op) for op, lineno in pos.items())
    return order

order = getorder()

def gen_builder():
    """Generate code for pykit.ir.builder operations"""
    print("    # Generated by pykit.utils._generate")
    for lineno, op in order:
        if op[0].isupper():
            print("    %-20s = _const(ops.%s)" % (op, op))
        else:
            print("    %-20s = _op(ops.%s)" % (op, op))

def gen_builder_methods():
    """Generate code for blaze.compute.air.builder operations"""
    print("""
    #===------------------------------------------------------------------===
    # Generated by blaze.compute.air._generate
    #===------------------------------------------------------------------===
    """)

    names = {
        ops.List: 'lst',
        ops.Value: 'value',
        ops.Const: 'const',
        ops.Any: 'any',
        ops.Obj: 'obj'
    }

    for lineno, op in order:
        if op[0].isupper():
            print("    %-20s = _const(ops.%s)" % (op, op))
        else:
            counts = defaultdict(int)
            params = []
            args = []
            stmts = []

            if not ops.is_void(op):
                params.append("returnType")

            for s in ops.op_syntax[op]:
                if s == ops.Star:
                    params.append('*args')
                    args.append('list(args)')
                else:
                    param = "%s%d" % (names[s], counts[s])
                    params.append(param)
                    args.append(param)

                    if s == ops.List:
                        ty = "list"
                    elif s == ops.Value:
                        ty = "Value"
                    elif s == ops.Const:
                        ty = "Const"
                    else:
                        continue

                    stmts.append("assert isinstance(%s, %s)" % (param, ty))

                counts[s] += 1

            params = ", ".join(params) + "," if params else ""
            args = ", ".join(args)
            if not ops.is_void(op):
                stmts.append('assert returnType is not None')
            else:
                stmts.append('returnType = types.Void')

            d = {
                'op': op, 'params': params, 'args': args,
                'stmts': '\n        '.join(stmts),
            }

            print("""
    def %(op)s(self, %(params)s **kwds):
        %(stmts)s
        register = kwds.pop('result', None)
        op = Op('%(op)s', returnType, [%(args)s], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op""" % d)

def gen_visitor():
    """Generate code for any visitor"""
    for lineno, op in order:
        if not op[0].isupper():
            print("    def %s(self, op):\n        pass\n" % (op,))

def gen_ops(lst):
    """Generate ops for ops.py"""
    for name in lst:
        print("%-18s = %r" % (name, name))

def gen_ops2():
    for op in defs.unary:
        print("    %-20s = unary(%r)" % (op, op))
    for op in defs.binary:
        print("    %-20s = binop(%r)" % (op, op))
    for op in defs.compare:
        print("    %-20s = binop(%-10s, type=types.Bool)" % (op, repr(op)))



if __name__ == "__main__":
    #gen_ops2()
    gen_builder_methods()


########NEW FILE########
__FILENAME__ = _generated
"""
    Generated builder methods.
"""

from __future__ import print_function, division, absolute_import

from . import types
from .configuration import config
from .ir import Op, Value, Const, ops
from .verification import verify_op_syntax


class GeneratedBuilder(object):
    _const = lambda val: Const(val, types.Opaque)
    _insert_op = lambda self, op: None  # noop

    #===------------------------------------------------------------------===
    # Generated by pykit.utils._generate
    #===------------------------------------------------------------------===
    
    Sin                  = _const(ops.Sin)
    Asin                 = _const(ops.Asin)
    Sinh                 = _const(ops.Sinh)
    Asinh                = _const(ops.Asinh)
    Cos                  = _const(ops.Cos)
    Acos                 = _const(ops.Acos)
    Cosh                 = _const(ops.Cosh)
    Acosh                = _const(ops.Acosh)
    Tan                  = _const(ops.Tan)
    Atan                 = _const(ops.Atan)
    Atan2                = _const(ops.Atan2)
    Tanh                 = _const(ops.Tanh)
    Atanh                = _const(ops.Atanh)
    Log                  = _const(ops.Log)
    Log2                 = _const(ops.Log2)
    Log10                = _const(ops.Log10)
    Log1p                = _const(ops.Log1p)
    Exp                  = _const(ops.Exp)
    Exp2                 = _const(ops.Exp2)
    Expm1                = _const(ops.Expm1)
    Floor                = _const(ops.Floor)
    Ceil                 = _const(ops.Ceil)
    Abs                  = _const(ops.Abs)
    Erfc                 = _const(ops.Erfc)
    Rint                 = _const(ops.Rint)
    Pow                  = _const(ops.Pow)
    Round                = _const(ops.Round)

    def alloca(self, returnType, obj0, **kwds):
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('alloca', returnType, [obj0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def load(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('load', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def store(self, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('store', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def convert(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('convert', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def bitcast(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('bitcast', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def phi(self, returnType, lst0, lst1, **kwds):
        assert isinstance(lst0, list)
        assert isinstance(lst1, list)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('phi', returnType, [lst0, lst1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def exc_setup(self, lst0, **kwds):
        assert isinstance(lst0, list)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('exc_setup', returnType, [lst0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def exc_catch(self, lst0, **kwds):
        assert isinstance(lst0, list)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('exc_catch', returnType, [lst0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def jump(self, value0, **kwds):
        assert isinstance(value0, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('jump', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def cbranch(self, value0, value1, value2, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert isinstance(value2, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('cbranch', returnType, [value0, value1, value2], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def exc_throw(self, value0, **kwds):
        assert isinstance(value0, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('exc_throw', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ret(self, obj0, **kwds):
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('ret', returnType, [obj0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def call(self, returnType, value0, lst0, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(lst0, list)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('call', returnType, [value0, lst0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def call_math(self, returnType, obj0, lst0, **kwds):
        assert isinstance(lst0, list)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('call_math', returnType, [obj0, lst0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def add(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('add', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def addressof(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('addressof', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def sizeof(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('sizeof', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ptradd(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('ptradd', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ptrload(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('ptrload', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ptrstore(self, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('ptrstore', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ptrcast(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('ptrcast', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ptr_isnull(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('ptr_isnull', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ge(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('ge', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def get(self, returnType, value0, lst0, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(lst0, list)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('get', returnType, [value0, lst0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def set(self, returnType, value0, value1, lst0, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert isinstance(lst0, list)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('set', returnType, [value0, value1, lst0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def getfield(self, returnType, value0, obj0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('getfield', returnType, [value0, obj0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def setfield(self, value0, obj0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('setfield', returnType, [value0, obj0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def extractfield(self, returnType, value0, obj0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('extractfield', returnType, [value0, obj0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def insertfield(self, returnType, value0, obj0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('insertfield', returnType, [value0, obj0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def shufflevector(self, returnType, value0, value1, value2, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert isinstance(value2, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('shufflevector', returnType, [value0, value1, value2], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def sub(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('sub', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def mul(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('mul', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def div(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('div', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def mod(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('mod', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def lshift(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('lshift', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def rshift(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('rshift', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def bitand(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('bitand', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def bitor(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('bitor', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def bitxor(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('bitxor', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def invert(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('invert', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def not_(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('not_', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def uadd(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('uadd', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def usub(self, returnType, value0, **kwds):
        assert isinstance(value0, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('usub', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def eq(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('eq', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def ne(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('ne', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def lt(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('lt', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def le(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('le', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def gt(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('gt', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def is_(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('is_', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def check_error(self, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('check_error', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def new_exc(self, returnType, value0, value1, **kwds):
        assert isinstance(value0, Value)
        assert isinstance(value1, Value)
        assert returnType is not None
        register = kwds.pop('result', None)
        op = Op('new_exc', returnType, [value0, value1], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

    def print(self, value0, **kwds):
        assert isinstance(value0, Value)
        returnType = types.Void
        register = kwds.pop('result', None)
        op = Op('print', returnType, [value0], register, metadata=kwds)
        if config.op_verify:
            verify_op_syntax(op)
        self._insert_op(op)
        return op

########NEW FILE########
__FILENAME__ = ckernel
from __future__ import absolute_import, division, print_function

__all__ = ['JITCKernelData', 'wrap_ckernel_func']

import sys
import ctypes
from dynd import _lowlevel

from dynd._lowlevel import (CKernelPrefixStruct, CKernelPrefixStructPtr,
        CKernelPrefixDestructor)

if sys.version_info >= (2, 7):
    c_ssize_t = ctypes.c_ssize_t
else:
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        c_ssize_t = ctypes.c_int32
    else:
        c_ssize_t = ctypes.c_int64

# Get some ctypes function pointers we need
if sys.platform == 'win32':
    _malloc = ctypes.cdll.msvcrt.malloc
    _free = ctypes.cdll.msvcrt.free
else:
    _malloc = ctypes.pythonapi.malloc
    _free = ctypes.pythonapi.free
_malloc.argtypes = (ctypes.c_size_t,)
_malloc.restype = ctypes.c_void_p
_free.argtypes = (ctypes.c_void_p,)
# Convert _free into a CFUNCTYPE so the assignment of it into the struct works
_free_proto = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
_free = _free_proto(ctypes.c_void_p.from_address(ctypes.addressof(_free)).value)

_py_decref = ctypes.pythonapi.Py_DecRef
_py_decref.argtypes = (ctypes.py_object,)
_py_incref = ctypes.pythonapi.Py_IncRef
_py_incref.argtypes = (ctypes.py_object,)

class JITCKernelData(ctypes.Structure):
    _fields_ = [('base', CKernelPrefixStruct),
                ('owner', ctypes.py_object)]

def _jitkerneldata_destructor(jkd_ptr):
    jkd = JITCKernelData.from_address(jkd_ptr)
    # Free the reference to the owner object
    _py_decref(jkd.owner)
    jkd.owner = 0
_jitkerneldata_destructor = CKernelPrefixDestructor(_jitkerneldata_destructor)

def wrap_ckernel_func(out_ckb, ckb_offset, func, owner):
    """
    This function generates a ckernel inside a ckernel_builder
    object from a ctypes function pointer, typically created using a JIT like
    Numba or directly using LLVM. The func must have its
    argtypes set, and its last parameter must be a
    CKernelPrefixStructPtr to be a valid CKernel function.
    The owner should be a pointer to an object which
    keeps the function pointer alive.
    """
    functype = type(func)
    # Validate the arguments
    if not isinstance(func, ctypes._CFuncPtr):
        raise TypeError('Require a ctypes function pointer to wrap')
    if func.argtypes is None:
        raise TypeError('The argtypes of the ctypes function ' +
                        'pointer must be set')
    if func.argtypes[-1] != CKernelPrefixStructPtr:
        raise TypeError('The last argument of the ctypes function ' +
                        'pointer must be CKernelPrefixStructPtr')

    # Allocate the memory for the kernel data
    ksize = ctypes.sizeof(JITCKernelData)
    ckb_end_offset = ckb_offset + ksize
    _lowlevel.ckernel_builder_ensure_capacity_leaf(out_ckb, ckb_end_offset)

    # Populate the kernel data with the function
    jkd = JITCKernelData.from_address(out_ckb.data + ckb_offset)
    # Getting the raw pointer address seems to require these acrobatics
    jkd.base.function = ctypes.c_void_p.from_address(ctypes.addressof(func))
    jkd.base.destructor = _jitkerneldata_destructor
    jkd.owner = ctypes.py_object(owner)
    _py_incref(jkd.owner)

    # Return the offset to the end of the ckernel
    return ckb_end_offset


########NEW FILE########
__FILENAME__ = test_wrapped_ckernel
from __future__ import absolute_import, division, print_function

import unittest
import ctypes
import sys

from blaze.compute import ckernel
from blaze.py2help import skipIf
from dynd import nd, ndt, _lowlevel

# On 64-bit windows python 2.6 appears to have
# ctypes bugs in the C calling convention, so
# disable these tests.
win64_py26 = (sys.platform == 'win32' and
              ctypes.sizeof(ctypes.c_void_p) == 8 and
              sys.version_info[:2] <= (2, 6))

class TestWrappedCKernel(unittest.TestCase):
    @skipIf(win64_py26, 'py26 win64 ctypes is buggy')
    def test_ctypes_callback(self):
        # Create a ckernel directly with ctypes
        def my_kernel_func(dst_ptr, src_ptr, kdp):
            dst = ctypes.c_int32.from_address(dst_ptr)
            src = ctypes.c_double.from_address(src_ptr)
            dst.value = int(src.value * 3.5)
        my_callback = _lowlevel.UnarySingleOperation(my_kernel_func)
        with _lowlevel.ckernel.CKernelBuilder() as ckb:
            # The ctypes callback object is both the function and the owner
            ckernel.wrap_ckernel_func(ckb, 0, my_callback, my_callback)
            # Delete the callback to make sure the ckernel is holding a reference
            del my_callback
            # Make some memory and call the kernel
            src_val = ctypes.c_double(4.0)
            dst_val = ctypes.c_int32(-1)
            ck = ckb.ckernel(_lowlevel.UnarySingleOperation)
            ck(ctypes.addressof(dst_val), ctypes.addressof(src_val))
            self.assertEqual(dst_val.value, 14)

    @skipIf(win64_py26, 'py26 win64 ctypes is buggy')
    def test_ctypes_callback_deferred(self):
        # Create a deferred ckernel via a closure
        def instantiate_ckernel(out_ckb, ckb_offset, dst_tp, dst_arrmeta,
                                   src_tp, src_arrmeta, kernreq, ectx):
            out_ckb = _lowlevel.CKernelBuilder(out_ckb)
            def my_kernel_func_single(dst_ptr, src_ptr, kdp):
                dst = ctypes.c_int32.from_address(dst_ptr)
                src = ctypes.c_double.from_address(src_ptr[0])
                dst.value = int(src.value * 3.5)
            def my_kernel_func_strided(dst_ptr, dst_stride, src_ptr, src_stride, count, kdp):
                src_ptr0 = src_ptr[0]
                src_stride0 = src_stride[0]
                for i in range(count):
                    my_kernel_func_single(dst_ptr, [src_ptr0], kdp)
                    dst_ptr += dst_stride
                    src_ptr0 += src_stride0
            if kernreq == 'single':
                kfunc = _lowlevel.ExprSingleOperation(my_kernel_func_single)
            else:
                kfunc = _lowlevel.ExprStridedOperation(my_kernel_func_strided)
            return ckernel.wrap_ckernel_func(out_ckb, ckb_offset,
                            kfunc, kfunc)
        ckd = _lowlevel.arrfunc_from_instantiate_pyfunc(instantiate_ckernel,
                        "(float64) -> int32")
        # Test calling the ckd
        out = nd.empty(ndt.int32)
        in0 = nd.array(4.0, type=ndt.float64)
        ckd.execute(out, in0)
        self.assertEqual(nd.as_py(out), 14)

        # Also call it lifted
        ckd_lifted = _lowlevel.lift_arrfunc(ckd)
        out = nd.empty('2 * var * int32')
        in0 = nd.array([[1.0, 3.0, 2.5], [1.25, -1.5]], type='2 * var * float64')
        ckd_lifted.execute(out, in0)
        self.assertEqual(nd.as_py(out), [[3, 10, 8], [4, -5]])

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = elwise_eval
from __future__ import absolute_import, division, print_function

"""Implements blaze._elwise_eval function.

This function is meant to do OOC operations following a different
strategy than the canonical Blaze approach, and should be phased out as
soon as the canonical approach can do these sort of things efficiently.
"""

import sys, math
from dynd import nd, ndt
from .. import array, empty
from .eval import eval as blaze_eval, append
import datashape
import re

if sys.version_info >= (3, 0):
    xrange = range
    def dict_viewkeys(d):
        return d.keys()
else:
    def dict_viewkeys(d):
        return d.iterkeys()

min_numexpr_version = '2.2'  # the minimum version of Numexpr needed
numexpr_here = False
try:
    import numexpr
except ImportError:
    pass
else:
    if numexpr.__version__ >= min_numexpr_version:
        numexpr_here = True

if numexpr_here:
    import numexpr
    from numexpr.expressions import functions as numexpr_functions


class Defaults(object):
    """Class to taylor the setters and getters of default values."""

    def __init__(self):
        self.choices = {}

        # Choices setup
        self.choices['vm'] = ("numexpr", "python")

    def check_choices(self, name, value):
        if value not in self.choices[name]:
            raise ValueError(
                "value must be in: %s" % (self.choices[name],))

    #
    # Properties start here...
    #

    @property
    def vm(self):
        return self.__vm

    @vm.setter
    def vm(self, value):
        self.check_choices('vm', value)
        if value == "numexpr" and not numexpr_here:
            raise ValueError(
                   "cannot use `numexpr` virtual machine "
                   "(minimum required version is probably not installed)")
        self.__vm = value


# Default values start here...
defaults = Defaults()
if numexpr_here:
    defaults.vm = "numexpr"
else:
    defaults.vm = "python"
"""
The virtual machine to be used in computations (via `eval`).  It can
be 'numexpr' or 'python'.  Default is 'numexpr', if installed.  If
not, then the default is 'python'.

"""

# Compute the product of a sequence
def prod(seq):
    ret = 1
    for i in seq:
        ret *= int(i)
    return ret

def _elwise_eval(expression, vm=None, user_dict={}, **kwargs):
    """
    eval(expression, vm=None, user_dict=None, **kwargs)

    Evaluate an `expression` and return the result.

    Parameters
    ----------
    expression : string
        A string forming an expression, like '2*a+3*b'. The values for 'a' and
        'b' are variable names to be taken from the calling function's frame.
        These variables may be scalars or Blaze arrays.
    vm : string
        The virtual machine to be used in computations.  It can be 'numexpr'
        or 'python'.  The default is to use 'numexpr' if it is installed.
    user_dict : dict
        An user-provided dictionary where the variables in expression
        can be found by name.
    kwargs : list of parameters or dictionary
        Any parameter supported by the blaze.array constructor.
        Useful for setting properties of the returned array object.

    Returns
    -------
    out : array object
        The outcome of the expression.  You can tailor the
        properties of this array by passing additional arguments
        supported by blaze.array constructor in `kwargs`.

    """

    if vm is None:
        vm = defaults.vm
    else:
        defaults.vm = vm

    # Get variables and column names participating in expression
    depth = kwargs.pop('depth', 2)
    vars = _getvars(expression, user_dict, depth, vm=vm)

    # The next is a hack to try to prevent people of using axis=dim,
    # where dim is > 0.
    if ("axis" in expression and
        re.findall("axis\s*=\s*[1-9]", expression)):
        raise NotImplementedError(
            "reductions in axis different than 0 are not supported yet")

    # Gather info about sizes and lengths
    rowsize, vlen = 0, 1
    for name in dict_viewkeys(vars):
        var = vars[name]
        # Scalars
        if not hasattr(var, "__len__"):
            continue
        if not hasattr(var, "dshape"):
            try:
                var = array(var)
            except:
                raise ValueError(
                    "sequence cannot be converted into a blaze array")
        # From now on, we only have Blaze arrays
        rowsize += var.dshape.measure.itemsize * prod(var.dshape.shape[1:])
        # Check for length
        if vlen > 1 and vlen != len(var):
            raise ValueError("arrays must have the same length")
        vlen = len(var)

    if rowsize == 0 or vlen == 0:
        # All scalars or zero-length objects
        if vm == "python":
            return eval(expression, vars)
        else:
            return numexpr.evaluate(expression, local_dict=vars)

    return _eval_blocks(expression, vars, vlen, rowsize, vm, **kwargs)

def _getvars(expression, user_dict, depth, vm):
    """Get the variables in `expression`.

    `depth` specifies the depth of the frame in order to reach local
    or global variables.
    """

    cexpr = compile(expression, '<string>', 'eval')
    if vm == "python":
        exprvars = [ var for var in cexpr.co_names
                     if var not in ['None', 'False', 'True'] ]
    else:
        # Check that var is not a numexpr function here.  This is useful for
        # detecting unbound variables in expressions.  This is not necessary
        # for the 'python' engine.
        exprvars = [ var for var in cexpr.co_names
                     if var not in ['None', 'False', 'True']
                     and var not in numexpr_functions ]

    # Get the local and global variable mappings of the user frame
    user_locals, user_globals = {}, {}
    user_frame = sys._getframe(depth)
    user_locals = user_frame.f_locals
    user_globals = user_frame.f_globals

    # Look for the required variables
    reqvars = {}
    for var in exprvars:
        # Get the value
        if var in user_dict:
            val = user_dict[var]
        elif var in user_locals:
            val = user_locals[var]
        elif var in user_globals:
            val = user_globals[var]
        else:
            if vm == "numexpr":
                raise NameError("variable name ``%s`` not found" % var)
            val = None
        # Check the value
        if (vm == "numexpr" and
            hasattr(val, 'dshape') and
            val.dshape.measure.name == 'uint64'):
            raise NotImplementedError(
                "variable ``%s`` refers to "
                "a 64-bit unsigned integer object, that is "
                "not yet supported in numexpr expressions; "
                "rather, use the 'python' vm." % var )
        if val is not None:
            reqvars[var] = val
    return reqvars

def _eval_blocks(expression, vars, vlen, rowsize, vm, **kwargs):
    """Perform the evaluation in blocks."""

    # Compute the optimal block size (in elements)
    # The next is based on experiments, but YMMV
    if vm == "numexpr":
        # If numexpr, make sure that operands fit in L3 chache
        bsize = 2**20  # 1 MB is common for L3
    else:
        # If python, make sure that operands fit in L2 chache
        bsize = 2**17  # 256 KB is common for L2
    bsize //= rowsize
    # Evaluation seems more efficient if block size is a power of 2
    bsize = 2 ** (int(math.log(bsize, 2)))
    if vlen < 100*1000:
        bsize //= 8
    elif vlen < 1000*1000:
        bsize //= 4
    elif vlen < 10*1000*1000:
        bsize //= 2
    # Protection against too large rowsizes
    if bsize == 0:
        bsize = 1

    vars_ = {}
    # Convert operands into Blaze arrays and get temporaries for vars
    maxndims = 0
    for name in dict_viewkeys(vars):
        var = vars[name]
        if not hasattr(var, "dshape"):
            # Convert sequences into regular Blaze arrays
            vars[name] = var = array(var)
        if hasattr(var, "__len__"):
            ndims = len(var.dshape.shape)
            if ndims > maxndims:
                maxndims = ndims
            if len(var) > bsize:
                # Variable is too large; get a container for a chunk
                res_shape, res_dtype = datashape.to_numpy(var.dshape)
                res_shape = list(res_shape)
                res_shape[0] = bsize
                dshape = datashape.from_numpy(res_shape, res_dtype)
                vars_[name] = empty(dshape)

    if 'ddesc' in kwargs and kwargs['ddesc'] is not None:
        res_ddesc = True
    else:
        res_ddesc = False

    for i in xrange(0, vlen, bsize):
        # Correction for the block size
        if i+bsize > vlen:
            bsize = vlen - i
        # Get buffers for vars
        for name in dict_viewkeys(vars):
            var = vars[name]
            if hasattr(var, "__len__") and len(var) > bsize:
                vars_[name] = var[i:i+bsize]
            else:
                if hasattr(var, "__getitem__"):
                    vars_[name] = var[:]
                else:
                    vars_[name] = var

        # Perform the evaluation for this block
        # We need array evals
        if vm == "python":
            res_block = eval(expression, vars_)
            dynd_block = blaze_eval(res_block).ddesc.dynd_arr()
        else:
            res_block = numexpr.evaluate(expression, local_dict=vars_)
            # numexpr returns a numpy array, and we need dynd/blaze ones
            dynd_block = nd.array(res_block)
            res_block = array(res_block)

        if i == 0:
            scalar = False
            dim_reduction = False
            # Detection of reduction operations
            if res_block.dshape.shape == ():
                scalar = True
                result = dynd_block
                continue
            elif len(res_block.dshape.shape) < maxndims:
                dim_reduction = True
                result = dynd_block
                continue
            block_shape, block_dtype = datashape.to_numpy(res_block.dshape)
            out_shape = list(block_shape)
            if res_ddesc:
                out_shape[0] = 0
                dshape = datashape.from_numpy(out_shape, block_dtype)
                result = empty(dshape, **kwargs)
                append(result, dynd_block)
            else:
                out_shape[0] = vlen
                dshape = datashape.from_numpy(out_shape, block_dtype)
                result = empty(dshape, **kwargs)
                # The next is a workaround for bug #183
                #result[:bsize] = res_block
                result[:bsize] = dynd_block
        else:
            if scalar:
                result += dynd_block
                result = result.eval()
            elif dim_reduction:
                if len(res_block) < len(result):
                    result[:bsize] += dynd_block
                else:
                    result += dynd_block
                result = result.eval()
            elif res_ddesc:
                append(result, dynd_block)
            else:
                # The next is a workaround for bug #183
                #result[i:i+bsize] = res_block
                result[i:i+bsize] = dynd_block

    # Scalars and dim reductions generate dynd array for workaround
    # different issues in Blaze array operations (see #197)
    if isinstance(result, nd.array):
        if scalar:
            return array(result)
        else:
            # If not an scalar pass the arguments (persistency, etc.)
            return array(result, **kwargs)
    return result

########NEW FILE########
__FILENAME__ = eval
from __future__ import absolute_import, division, print_function

"""Implements the blaze.eval function"""

from .air import compile, run
from .. import array

#------------------------------------------------------------------------
# Eval
#------------------------------------------------------------------------

def eval(arr, ddesc=None, caps={'efficient-write': True},
         out=None, debug=False):
    """Evaluates a deferred blaze kernel tree
    data descriptor into a concrete array.
    If the array is already concrete, merely
    returns it unchanged.

    Parameters
    ----------
    ddesc: DDesc instance, optional
        A data descriptor for storing the result, if evaluating to a BLZ
        output or (in the future) to a distributed array.

    caps: { str : object }
        Capabilities for evaluation and storage
        TODO: elaborate on values

    out: Array
        Output array to store the result in, or None for a new array

    strategy: str
        Evaluation strategy.
        Currently supported: 'py', 'jit'
    """
    if arr.ddesc.capabilities.deferred:
        result = eval_deferred(
            arr, ddesc=ddesc, caps=caps, out=out, debug=debug)
    elif arr.ddesc.capabilities.remote:
        # Retrieve the data to local memory
        # TODO: Caching should play a role here.
        result = array(arr.ddesc.dynd_arr())
    else:
        # TODO: This isn't right if the data descriptor is different, requires
        #       a copy then.
        result = arr

    return result


def eval_deferred(arr, ddesc, caps, out, debug=False):
    expr = arr.ddesc.expr
    graph, ctx = expr

    # collected 'params' from the expression
    args = [ctx.terms[param] for param in ctx.params]

    func, env = compile(expr, ddesc=ddesc)
    result = run(func, env, ddesc=ddesc, caps=caps, out=out, debug=debug)

    return result

#------------------------------------------------------------------------
# Append
#------------------------------------------------------------------------

def append(arr, values):
    """Append a list of values."""
    # XXX If not efficient appends supported, this should raise
    # a `PerformanceWarning`
    if arr.ddesc.capabilities.appendable:
        arr.ddesc.append(values)
    else:
        raise ValueError('Data source cannot be appended to')


########NEW FILE########
__FILENAME__ = expr
"""
Blaze expression graph for deferred evaluation. Each expression node has
an opcode and operands. An operand is a Constant or another expression node.
Each expression node carries a DataShape as type.
"""

from __future__ import absolute_import, division, print_function
from functools import partial


array = 'array'    # array input
kernel = 'kernel'  # kernel application, carrying the blaze kernel as a
                   # first argument (Constant)


class ExprContext(object):
    """
    Context for blaze graph expressions.

    This keeps track of a mapping between graph expression nodes and the
    concrete data inputs (i.e. blaze Arrays).

    Attributes:
    ===========

    terms: { ArrayOp: Array }
        Mapping from ArrayOp nodes to inputs
    """

    def __init__(self, contexts=[]):
        # Coercion constraints between types with free variables
        self.constraints = []
        self.terms = {} # All terms in the graph, { Array : Op }
        self.params = []

        for ctx in contexts:
            self.constraints.extend(ctx.constraints)
            self.terms.update(ctx.terms)
            self.params.extend(ctx.params)

    def add_input(self, term, data):
        if term not in self.terms:
            self.params.append(term)
        self.terms[term] = data


class Op(object):
    """
    Single node in blaze expression graph.

    Attributes
    ----------
    opcode: string
        Kind of the operation, i.e. 'array' or 'kernel'

    uses: [Op]
        Consumers (or parents) of this result. This is useful to keep
        track of, since we always start evaluation from the 'root', and we
        may miss tracking outside uses. However, for correct behaviour, these
        need to be retained
    """

    def __init__(self, opcode, dshape, *args, **metadata):
        self.opcode = opcode
        self.dshape = dshape
        self.uses = []
        self.args = list(args)

        if opcode == 'kernel':
            assert 'kernel' in metadata
            assert 'overload' in metadata
        self.metadata = metadata

        for arg in self.args:
            arg.add_use(self)

    def add_use(self, use):
        self.uses.append(use)

    def __repr__(self):
        opcode = self.opcode
        if opcode == kernel:
            opcode = self.metadata["kernel"]
        metadata = ", ".join(self.metadata)
        return "%s(...){dshape(%s), %s}" % (opcode, self.dshape, metadata)

    def tostring(self):
        subtrees = " -+- ".join(map(str, self.args))
        node = str(self)
        length = max(len(subtrees), len(node))
        return "%s\n%s" % (node.center(len(subtrees) / 2), subtrees.center(length))


ArrayOp = partial(Op, array)

# Kernel application. Associated metadata:
#   kernel: the blaze.function.Kernel that was applied
#   overload: the blaze.overload.Overload that selected for the input args
KernelOp = partial(Op, kernel)

########NEW FILE########
__FILENAME__ = function
"""
The purpose of this module is to create blaze functions. A Blaze Function
carries a polymorphic signature which allows it to verify well-typedness over
the input arguments, and to infer the result of the operation.

Blaze function also create a deferred expression graph when executed over
operands. A blaze function carries default ckernel implementations as well
as plugin implementations.
"""

from __future__ import print_function, division, absolute_import

from collections import namedtuple

# TODO: Remove circular dependency between blaze.objects.Array and blaze.compute
import blaze
import datashape
from datashape import coretypes, dshape

from ..datadescriptor import Deferred_DDesc
from .expr import ArrayOp, ExprContext, KernelOp

Overload = namedtuple('Overload', 'resolved_sig, sig, func')

def construct(bfunc, ctx, overload, args):
    """
    Blaze expression graph construction for deferred evaluation.

    Parameters
    ----------
    bfunc : Blaze Function
        (Overloaded) blaze function representing the operation

    ctx: ExprContext
        Context of the expression

    overload: blaze.overload.Overload
        Instance representing the overloaded function

    args: list
        bfunc parameters
    """
    assert isinstance(bfunc, BlazeFunc), bfunc

    params = [] # [(graph_term, ExprContext)]

    # -------------------------------------------------
    # Build type unification parameters

    for i, arg in enumerate(args):
        if isinstance(arg, blaze.Array) and arg.expr:
            # Compose new expression using previously constructed expression
            term, context = arg.expr
            if not arg.deferred:
                ctx.add_input(term, arg)
        elif isinstance(arg, blaze.Array):
            term = ArrayOp(arg.dshape)
            ctx.add_input(term, arg)
            empty = ExprContext()
            arg.expr = (term, empty)
        else:
            term = ArrayOp(coretypes.typeof(arg))

        ctx.terms[term] = arg
        params.append(term)

    assert isinstance(overload.resolved_sig, coretypes.Function)
    restype = dshape(overload.resolved_sig.restype)

    return KernelOp(restype, *params, kernel=bfunc, overload=overload)


class BlazeFunc(object):
    """
    Blaze function. This is like the numpy ufunc object, in that it
    holds all the overloaded implementations of a function, and provides
    dispatch when called as a function. Objects of this type can be
    created directly, or using one of the decorators like @function .

    Attributes
    ----------
    overloader : datashape.OverloadResolver
        This is the multiple dispatch overload resolver which is used
        to determine the overload upon calling the function.
    ckernels : list of ckernels
        This is the list of ckernels corresponding to the signatures
        in overloader.
    plugins : dict of {pluginname : (overloader, datalist)}
        For each plugin that has registered with this blaze function,
        there is an overloader and corresponding data object describing
        execution using that plugin.
    name : string
        The name of the function (e.g. "sin").
    module : string
        The name of the module the function is in (e.g. "blaze")
    fullname : string
        The fully qualified name of the function (e.g. "blaze.sin").

    """

    def __init__(self, module, name):
        self._module = module
        self._name = name
        # The ckernels list corresponds to the
        # signature indices in the overloader
        self.overloader = datashape.OverloadResolver(self.fullname)
        self.ckernels = []
        # Each plugin has its own overloader and data (a two-tuple)
        self.plugins = {}

    @property
    def name(self):
        """Return the name of the blazefunc."""
        return self._name

    @property
    def module(self):
        return self._module

    @property
    def fullname(self):
        return self._module + '.' + self._name

    @property
    def available_plugins(self):
        return list(self.plugins.keys())

    def add_overload(self, sig, ck):
        """
        Adds a single signature and its ckernel to the overload resolver.
        """
        self.overloader.extend_overloads([sig])
        self.ckernels.append(ck)

    def add_plugin_overload(self, sig, data, pluginname):
        """
        Adds a single signature and corresponding data for a plugin
        implementation of the function.
        """
        # Get the overloader and data list for the plugin
        overloader, datalist = self.plugins.get(pluginname, (None, None))
        if overloader is None:
            overloader = datashape.OverloadResolver(self.fullname)
            datalist = []
            self.plugins[pluginname] = (overloader, datalist)
        # Add the overload
        overloader.extend_overloads([sig])
        datalist.append(data)

    def __call__(self, *args):
        """
        Apply blaze kernel `kernel` to the given arguments.

        Returns: a Deferred node representation the delayed computation
        """
        # Convert the arguments into blaze.Array
        args = [blaze.array(a) for a in args]

        # Merge input contexts
        ctxs = [term.expr[1] for term in args
                if isinstance(term, blaze.Array) and term.expr]
        ctx = ExprContext(ctxs)

        # Find match to overloaded function
        argstype = coretypes.Tuple([a.dshape for a in args])
        idx, match = self.overloader.resolve_overload(argstype)
        overload = Overload(match, self.overloader[idx], self.ckernels[idx])

        # Construct graph
        term = construct(self, ctx, overload, args)
        desc = Deferred_DDesc(term.dshape, (term, ctx))

        return blaze.Array(desc)

    def __str__(self):
        return "BlazeFunc %s" % self.name

    def __repr__(self):
        # TODO proper repr
        return str(self)


def _normalized_sig(sig):
    sig = datashape.dshape(sig)
    if len(sig) == 1:
        sig = sig[0]
    if not isinstance(sig, coretypes.Function):
        raise TypeError(('Only function signatures allowed as' +
                         'overloads, not %s') % sig)
    return sig


def _prepend_to_ds(ds, typevar):
    if isinstance(ds, coretypes.DataShape):
        tlist = ds.parameters
    else:
        tlist = (ds,)
    return coretypes.DataShape(typevar, *tlist)


def _add_elementwise_dims_to_sig(sig, typevarname):
    sig = _normalized_sig(sig)
    # Process the signature to add 'Dims... *' broadcasting
    if datashape.has_ellipsis(sig):
        raise TypeError(('Signature provided to ElementwiseBlazeFunc' +
                         'already includes ellipsis: %s') % sig)
    dims = coretypes.Ellipsis(coretypes.TypeVar(typevarname))
    params = [_prepend_to_ds(param, dims)
              for param in sig.parameters]
    return coretypes.Function(*params)


class ElementwiseBlazeFunc(BlazeFunc):
    """
    This is a kind of BlazeFunc that is always processed element-wise.
    When overloads are added to it, they have 'Dims... *' prepend
    the the datashape of every argument and the return type.
    """
    def add_overload(self, sig, ck):
        # Prepend 'Dims... *' to args and return type
        sig = _add_elementwise_dims_to_sig(sig, 'Dims')
        info = {'tag': 'elwise',
                'ckernel': ck}
        BlazeFunc.add_overload(self, sig, info)

    def add_plugin_overload(self, sig, data, pluginname):
        # Prepend 'Dims... *' to args and return type
        sig = _add_elementwise_dims_to_sig(sig, 'Dims')
        BlazeFunc.add_plugin_overload(self, sig, data, pluginname)


class _ReductionResolver(object):
    """
    This is a helper class which resolves the output dimensions
    of a ReductionBlazeFunc call based on the 'axis=' and 'keepdims='
    arguments.
    """
    def __init__(self, axis, keepdims):
        self.axis = axis
        self.keepdims = keepdims
        self.dimsin = coretypes.Ellipsis(coretypes.TypeVar('DimsIn'))
        self.dimsout = coretypes.Ellipsis(coretypes.TypeVar('DimsOut'))

    def __call__(self, sym, tvdict):
        if sym == self.dimsout:
            dims = tvdict[self.dimsin]
            # Create an array of flags indicating which dims are reduced
            if self.axis is None:
                dimflags = [True] * len(dims)
            else:
                dimflags = [False] * len(dims)
                try:
                    for ax in self.axis:
                        dimflags[ax] = True
                except IndexError:
                    raise IndexError(('axis %s is out of bounds for the' +
                                      'input type') % self.axis)
            # Remove or convert the reduced dims to fixed size-one
            if self.keepdims:
                reddim = coretypes.Fixed(1)
                return [reddim if dimflags[i] else dim
                        for i, dim in enumerate(dims)]
            else:
                return [dim for i, dim in enumerate(dims) if not dimflags[i]]


class ReductionBlazeFunc(BlazeFunc):
    """
    This is a kind of BlazeFunc with a calling convention for
    elementwise reductions which support 'axis=' and 'keepdims='
    keyword arguments.
    """
    def add_overload(self, sig, ck, associative, commutative, identity=None):
        sig = _normalized_sig(sig)
        if datashape.has_ellipsis(sig):
            raise TypeError(('Signature provided to ReductionBlazeFunc' +
                             'already includes ellipsis: %s') % sig)
        if len(sig.argtypes) != 1:
            raise TypeError(('Signature provided to ReductionBlazeFunc' +
                             'must have only one argument: %s') % sig)
        # Prepend 'DimsIn... *' to the args, and 'DimsOut... *' to
        # the return type
        sig = coretypes.Function(_prepend_to_ds(sig.argtypes[0],
                                                coretypes.Ellipsis(coretypes.TypeVar('DimsIn'))),
                                 _prepend_to_ds(sig.restype,
                                                coretypes.Ellipsis(coretypes.TypeVar('DimsOut'))))
        # TODO: This probably should be an object instead of a dict
        info = {'tag': 'reduction',
                'ckernel': ck,
                'assoc': associative,
                'comm': commutative,
                'ident': identity}
        BlazeFunc.add_overload(self, sig, info)

    def add_plugin_overload(self, sig, data, pluginname):
        raise NotImplementedError('TODO: implement add_plugin_overload')

    def __call__(self, *args, **kwargs):
        """
        Apply blaze kernel `kernel` to the given arguments.

        Returns: a Deferred node representation the delayed computation
        """
        # Validate the 'axis=' and 'keepdims=' keyword-only arguments
        axis = kwargs.pop('axis', None)
        if axis is not None and not isinstance(axis, tuple):
            axis = (axis,)
        keepdims = kwargs.pop('keepdims', False)
        if kwargs:
            msg = "%s got an unexpected keyword argument '%s'"
            raise TypeError(msg % (self.fullname, kwargs.keys()[0]))

        # Convert the arguments into blaze.Array
        args = [blaze.array(a) for a in args]

        # Merge input contexts
        ctxs = [term.expr[1] for term in args
                if isinstance(term, blaze.Array) and term.expr]
        ctx = ExprContext(ctxs)

        # Find match to overloaded function
        redresolver = _ReductionResolver(axis, keepdims)
        argstype = coretypes.Tuple([a.dshape for a in args])
        idx, match = self.overloader.resolve_overload(argstype, redresolver)
        info = dict(self.ckernels[idx])
        info['axis'] = axis
        info['keepdims'] = keepdims
        overload = Overload(match, self.overloader[idx], info)

        # Construct graph
        term = construct(self, ctx, overload, args)
        desc = Deferred_DDesc(term.dshape, (term, ctx))

        return blaze.Array(desc)


class RollingWindowBlazeFunc(BlazeFunc):
    """
    This is a kind of BlazeFunc with a calling convention for
    rolling windows which support 'window=' and 'minp='
    keyword arguments.
    """
    def add_overload(self, sig, ck):
        sig = _normalized_sig(sig)
        # TODO: This probably should be an object instead of a dict
        info = {'tag': 'rolling',
                'ckernel': ck}
        BlazeFunc.add_overload(self, sig, info)

    def add_plugin_overload(self, sig, data, pluginname):
        raise NotImplementedError('TODO: implement add_plugin_overload')

    def __call__(self, *args, **kwargs):
        """
        Apply blaze kernel `kernel` to the given arguments.

        Returns: a Deferred node representation the delayed computation
        """
        # Validate the 'window=' and 'minp=' keyword-only arguments
        window = kwargs.pop('window', None)
        if window is None:
            raise TypeError("%s() missing required keyword argument 'window'" % self.name)
        minp = kwargs.pop('minp', 0)
        if kwargs:
            msg = "%s got an unexpected keyword argument '%s'"
            raise TypeError(msg % (self.fullname, kwargs.keys()[0]))

        # Convert the arguments into blaze.Array
        args = [blaze.array(a) for a in args]

        # Merge input contexts
        ctxs = [term.expr[1] for term in args
                if isinstance(term, blaze.Array) and term.expr]
        ctx = ExprContext(ctxs)

        # Find match to overloaded function
        argstype = coretypes.Tuple([a.dshape for a in args])
        idx, match = self.overloader.resolve_overload(argstype)
        info = dict(self.ckernels[idx])
        info['window'] = window
        info['minp'] = minp
        overload = Overload(match, self.overloader[idx], info)

        # Construct graph
        term = construct(self, ctx, overload, args)
        desc = Deferred_DDesc(term.dshape, (term, ctx))

        return blaze.Array(desc)

class CKFBlazeFunc(BlazeFunc):
    """
    This is a kind of BlazeFunc which generates a ckernel
    using a factory function provided with the types.
    """
    def add_overload(self, sig, ckfactory):
        sig = _normalized_sig(sig)
        # TODO: This probably should be an object instead of a dict
        info = {'tag': 'ckfactory',
                'ckernel_factory': ckfactory}
        BlazeFunc.add_overload(self, sig, info)

    def add_plugin_overload(self, sig, data, pluginname):
        raise NotImplementedError('TODO: implement add_plugin_overload')

    def __call__(self, *args):
        """
        Apply blaze kernel `kernel` to the given arguments.

        Returns: a Deferred node representation the delayed computation
        """
        # Convert the arguments into blaze.Array
        args = [blaze.array(a) for a in args]

        # Merge input contexts
        ctxs = [term.expr[1] for term in args
                if isinstance(term, blaze.Array) and term.expr]
        ctx = ExprContext(ctxs)

        # Find match to overloaded function
        argstype = coretypes.Tuple([a.dshape for a in args])
        idx, match = self.overloader.resolve_overload(argstype)
        info = dict(self.ckernels[idx])
        overload = Overload(match, self.overloader[idx], info)

        # Construct graph
        term = construct(self, ctx, overload, args)
        desc = Deferred_DDesc(term.dshape, (term, ctx))

        return blaze.Array(desc)

########NEW FILE########
__FILENAME__ = from_dynd
"""
Helper functions which constructs blaze functions from dynd kernels.
"""

from __future__ import absolute_import, division, print_function

from dynd import nd, _lowlevel
import datashape

from ..function import ElementwiseBlazeFunc


def _make_sig(kern):
    dsret = datashape.dshape(str(nd.as_py(kern.proto).return_type))
    dslist = [datashape.dshape(str(x))
              for x in nd.as_py(kern.proto).param_types]
    return datashape.Function(*(dslist + [dsret]))


def blazefunc_from_dynd_property(tplist, propname, modname, name):
    """Converts a dynd property access into a Blaze ufunc.

    Parameters
    ----------
    tplist : list of dynd types
        A list of the types to use.
    propname : str
        The name of the property to access on the type.
    modname : str
        The module name to report in the ufunc's name
    name : str
        The ufunc's name.
    """
    # Get the list of type signatures
    kernlist = [_lowlevel.make_arrfunc_from_property(tp, propname,
                                                     'expr', 'default')
                for tp in tplist]
    siglist = [_make_sig(kern) for kern in kernlist]
    # Create the empty blaze function to start
    bf = ElementwiseBlazeFunc('blaze', name)
    # TODO: specify elementwise
    #bf.add_metadata({'elementwise': True})
    for (sig, kern) in zip(siglist, kernlist):
        bf.add_overload(sig, kern)
    return bf

########NEW FILE########
__FILENAME__ = from_numpy
"""
A helper function which turns a NumPy ufunc into a Blaze ufunc.
"""

from __future__ import absolute_import, division, print_function

import numpy as np
from dynd import _lowlevel
import datashape
from ..function import ElementwiseBlazeFunc


def _filter_tplist(tplist):
    """Removes duplicates (arising from the long type usually), and
    eliminates the object dtype.
    """
    elim_kinds = ['O', 'M', 'm', 'S', 'U']
    if str(np.longdouble) != str(np.double):
        elim_types = [np.longdouble, np.clongdouble]
    else:
        elim_types = []
    elim_types.append(np.float16)
    seen = set()
    tplistnew = []
    for sig in tplist:
        if sig not in seen and not any(dt.kind in elim_kinds or
                                       dt in elim_types for dt in sig):
            tplistnew.append(sig)
            seen.add(sig)
    return tplistnew


def _make_sig(tplist):
    """Converts a type tuples into datashape function signatures"""
    dslist = [datashape.dshape(str(x)) for x in tplist]
    return datashape.Function(*(dslist[1:] + [dslist[0]]))


def blazefunc_from_numpy_ufunc(uf, modname, name, acquires_gil):
    """Converts a NumPy ufunc into a Blaze ufunc.

    Parameters
    ----------
    uf : NumPy ufunc
        The ufunc to convert.
    modname : str
        The module name to report in the ufunc's name
    name : str
        The ufunc's name.
    acquires_gil : bool
        True if the kernels in the ufunc need the GIL.
        TODO: should support a dict {type -> bool} to allow per-kernel control.
    """
    # Get the list of type signatures
    tplist = _lowlevel.numpy_typetuples_from_ufunc(uf)
    tplist = _filter_tplist(tplist)
    siglist = [_make_sig(tp) for tp in tplist]
    kernlist = [_lowlevel.arrfunc_from_ufunc(uf, tp, acquires_gil)
                for tp in tplist]
    # Create the empty blaze function to start
    bf = ElementwiseBlazeFunc('blaze', name)
    # TODO: specify elementwise
    #bf.add_metadata({'elementwise': True})
    # Add an overload to the function for each signature
    for (tp, sig, kern) in zip(tplist, siglist, kernlist):
        bf.add_overload(sig, kern)
    return bf


########NEW FILE########
__FILENAME__ = reduction
"""
Reduction functions.
"""

from __future__ import absolute_import, division, print_function

from .ufuncs import logical_and, logical_or, abs

#------------------------------------------------------------------------
# Reduce Impl
#------------------------------------------------------------------------

def reduce(kernel, a, axis=None):
    if axis is None:
        axes = range(a.ndim)
    elif isinstance(axis, int):
        axes = (axis,)
    else:
        axes = axis # Tuple

    # TODO: validate axes
    # TODO: insert map for other dimensions
    result = a
    for axis in axes:
        result = reduce_dim(kernel, result)
    return result


# TODO: Deferred
# @kernel('(*, X * Y... * Dtype) -> Y... * Dtype')
def reduce_dim(kernel, a):
    from blaze import eval

    a = eval(a)
    it = iter(a)
    result = next(it)
    for x in it:
        result = kernel(result, x)

    return result

#------------------------------------------------------------------------
# Higher-level reductions
#------------------------------------------------------------------------

def all(a):
    return reduce(logical_and, a)


def any(a):
    return reduce(logical_or, a)


def allclose(a, b, rtol=1e-05, atol=1e-08):
    """
    Returns True if two arrays are element-wise equal within a tolerance.

    The tolerance values are positive, typically very small numbers.  The
    relative difference (`rtol` * abs(`b`)) and the absolute difference
    `atol` are added together to compare against the absolute difference
    between `a` and `b`.

    If either array contains one or more NaNs, False is returned.
    Infs are treated as equal if they are in the same place and of the same
    sign in both arrays.

    Parameters
    ----------
    a, b : array_like
        Input arrays to compare.
    rtol : float
        The relative tolerance parameter (see Notes).
    atol : float
        The absolute tolerance parameter (see Notes).

    Returns
    -------
    allclose : bool
        Returns True if the two arrays are equal within the given
        tolerance; False otherwise.

    See Also
    --------
    all, any, alltrue, sometrue

    Notes
    -----
    If the following equation is element-wise True, then allclose returns
    True.

     absolute(`a` - `b`) <= (`atol` + `rtol` * absolute(`b`))

    The above equation is not symmetric in `a` and `b`, so that
    `allclose(a, b)` might be different from `allclose(b, a)` in
    some rare cases.

    Examples
    --------
    >>> blaze.allclose([1e10,1e-7], [1.00001e10,1e-8])
    False
    >>> blaze.allclose([1e10,1e-8], [1.00001e10,1e-9])
    True
    >>> blaze.allclose([1e10,1e-8], [1.0001e10,1e-9])
    False
    >>> blaze.allclose([1.0, np.nan], [1.0, np.nan])
    False
    """
    return all(abs(a - b) <= atol + rtol * abs(b))

########NEW FILE########
__FILENAME__ = ufuncs
"""
Blaze element-wise ufuncs.
"""

from __future__ import absolute_import, division, print_function

ufuncs_from_numpy = [
            'add', 'subtract', 'multiply', 'divide',
            'logaddexp', 'logaddexp2', 'true_divide',
            'floor_divide', 'negative', 'power',
            'remainder', 'mod', 'fmod',
            'absolute', 'abs', 'rint', 'sign',
            'conj',
            'exp', 'exp2', 'log', 'log2', 'log10', 'expm1', 'log1p',
            'sqrt', 'square', 'reciprocal',
            'sin', 'cos', 'tan', 'arcsin',
            'arccos', 'arctan', 'arctan2',
            'hypot', 'sinh', 'cosh', 'tanh',
            'arcsinh', 'arccosh', 'arctanh',
            'deg2rad', 'rad2deg', 'degrees', 'radians',
            'bitwise_and', 'bitwise_or', 'bitwise_xor', 'bitwise_not',
            'invert', 'left_shift', 'right_shift',
            'greater', 'greater_equal', 'less', 'less_equal',
            'not_equal', 'equal',
            'logical_and', 'logical_or', 'logical_xor', 'logical_not',
            'maximum', 'minimum', 'fmax', 'fmin',
            'isfinite', 'isinf', 'isnan',
            'signbit', 'copysign', 'nextafter', 'ldexp',
            'fmod', 'floor', 'ceil', 'trunc']

ufuncs_from_dynd = ['real', 'imag']

reduction_ufuncs = ['any', 'all', 'sum', 'product', 'min', 'max']

other_ufuncs = ['rolling_mean', 'diff', 'take']

__all__ = ufuncs_from_numpy + ufuncs_from_dynd + reduction_ufuncs + \
          other_ufuncs

import numpy as np
from dynd import ndt, _lowlevel

from .from_numpy import blazefunc_from_numpy_ufunc
from .from_dynd import blazefunc_from_dynd_property
from ..function import ReductionBlazeFunc, RollingWindowBlazeFunc, \
    CKFBlazeFunc, BlazeFunc

#------------------------------------------------------------------------
# UFuncs converted from NumPy
#------------------------------------------------------------------------

for name in ufuncs_from_numpy:
    globals()[name] = blazefunc_from_numpy_ufunc(getattr(np, name),
                                                 'blaze', name, False)

#------------------------------------------------------------------------
# UFuncs from DyND
#------------------------------------------------------------------------

real = blazefunc_from_dynd_property([ndt.complex_float32, ndt.complex_float64],
                                    'real', 'blaze', 'real')
imag = blazefunc_from_dynd_property([ndt.complex_float32, ndt.complex_float64],
                                    'imag', 'blaze', 'imag')

year = blazefunc_from_dynd_property([ndt.date, ndt.datetime],
                                    'year', 'blaze', 'year')
month = blazefunc_from_dynd_property([ndt.date, ndt.datetime],
                                    'month', 'blaze', 'month')
day = blazefunc_from_dynd_property([ndt.date, ndt.datetime],
                                    'day', 'blaze', 'day')
hour = blazefunc_from_dynd_property([ndt.time, ndt.datetime],
                                     'hour', 'blaze', 'hour')
minute = blazefunc_from_dynd_property([ndt.time, ndt.datetime],
                                       'minute', 'blaze', 'minute')
second = blazefunc_from_dynd_property([ndt.time, ndt.datetime],
                                       'second', 'blaze', 'second')
microsecond = blazefunc_from_dynd_property([ndt.time, ndt.datetime],
                                           'microsecond', 'blaze', 'microsecond')
date = blazefunc_from_dynd_property([ndt.datetime],
                                    'date', 'blaze', 'date')
time = blazefunc_from_dynd_property([ndt.datetime],
                                    'time', 'blaze', 'time')

#------------------------------------------------------------------------
# Reduction UFuncs from NumPy
#------------------------------------------------------------------------

bools = np.bool,
ints = np.int8, np.int16, np.int32, np.int64,
floats = np.float32, np.float64
complexes = np.complex64, np.complex128,

reductions = [('any', np.logical_or,   False, bools),
              ('all', np.logical_and,  True, bools),
              ('sum', np.add,          0, ints + floats + complexes),
              ('product', np.multiply, 1, ints + floats + complexes),
              ('min', np.minimum,      None, bools + ints + floats + complexes),
              ('max', np.maximum,      None, bools + ints + floats + complexes)]

for name, np_op, ident, types in reductions:
    x = ReductionBlazeFunc('blaze', name)
    for typ in types:
        x.add_overload('(%s) -> %s' % (typ.__name__, typ.__name__),
                 _lowlevel.arrfunc_from_ufunc(np_op, (typ,) * 3, False),
                 associative=True, commutative=True,
                 identity=ident)
        locals()[name] = x

#------------------------------------------------------------------------
# Other Funcs
#------------------------------------------------------------------------

rolling_mean = RollingWindowBlazeFunc('blaze', 'rolling_mean')
mean1d = _lowlevel.make_builtin_mean1d_arrfunc('float64', 0)
rolling_mean.add_overload('(M * float64) -> M * float64', mean1d)

diff = BlazeFunc('blaze', 'diff')
subtract_doubles_ck = _lowlevel.arrfunc_from_ufunc(np.subtract,
                (np.float64, np.float64, np.float64),
                False)
diff_pair_ck = _lowlevel.lift_reduction_arrfunc(subtract_doubles_ck,
                                         'strided * float64',
                                         axis=0,
                                         commutative=False,
                                         associative=False)
diff_ck = _lowlevel.make_rolling_arrfunc(diff_pair_ck, 2)
diff.add_overload('(M * float64) -> M * float64', diff_ck)

take = BlazeFunc('blaze', 'take')
# Masked take
take.add_overload('(M * T, M * bool) -> var * T',
                  _lowlevel.make_take_arrfunc())
# Indexed take
take.add_overload('(M * T, N * intptr) -> N * T',
                  _lowlevel.make_take_arrfunc())

########NEW FILE########
__FILENAME__ = strategy
"""
Blaze execution strategy.
"""

from __future__ import absolute_import, division, print_function

#------------------------------------------------------------------------
# Strategies
#------------------------------------------------------------------------

CKERNEL = 'ckernel'

########NEW FILE########
__FILENAME__ = test_elwise_eval
from __future__ import absolute_import, division, print_function

import unittest

import numpy as np
from numpy.testing import assert_array_equal, assert_allclose

from dynd import nd, ndt
import blaze

import unittest
import tempfile
import os, os.path
import glob
import blaze


# Useful superclass for disk-based tests
class MayBePersistentTest(unittest.TestCase):
    disk = None

    def setUp(self):
        if self.disk == 'BLZ':
            prefix = 'blaze-' + self.__class__.__name__
            suffix = '.blz'
            path1 = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
            os.rmdir(path1)
            self.ddesc1 = blaze.BLZ_DDesc(path1, mode='w')
            path2 = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
            os.rmdir(path2)
            self.ddesc2 = blaze.BLZ_DDesc(path2, mode='w')
            path3 = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
            os.rmdir(path3)
            self.ddesc3 = blaze.BLZ_DDesc(path3, mode='w')
        elif self.disk == 'HDF5':
            prefix = 'hdf5-' + self.__class__.__name__
            suffix = '.hdf5'
            dpath = "/earray"
            h, path1 = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(h)  # close the non needed file handle
            self.ddesc1 = blaze.HDF5_DDesc(path1, dpath, mode='w')
            h, path2 = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(h)
            self.ddesc2 = blaze.HDF5_DDesc(path2, dpath, mode='w')
            h, path3 = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(h)
            self.ddesc3 = blaze.HDF5_DDesc(path3, dpath, mode='w')
        else:
            self.ddesc1 = None
            self.ddesc2 = None
            self.ddesc3 = None

    def tearDown(self):
        if self.disk:
            self.ddesc1.remove()
            self.ddesc2.remove()
            self.ddesc3.remove()


# Check for arrays that fit in the chunk size
class evalTest(unittest.TestCase):
    vm = "numexpr"  # if numexpr not available, it will fall back to python
    N = 1000

    def test00(self):
        """Testing elwise_eval() with only scalars and constants"""
        a = 3
        cr = blaze._elwise_eval("2 * a", vm=self.vm)
        self.assert_(cr == 6, "eval does not work correctly")

    def test01(self):
        """Testing with only blaze arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c = blaze.array(a)
        d = blaze.array(b)
        cr = blaze._elwise_eval("c * d", vm=self.vm)
        nr = a * b
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test02(self):
        """Testing with only numpy arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        cr = blaze._elwise_eval("a * b", vm=self.vm)
        nr = a * b
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test03(self):
        """Testing with only dynd arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c = nd.array(a)
        d = nd.array(b)
        cr = blaze._elwise_eval("c * d", vm=self.vm)
        nr = a * b
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test04(self):
        """Testing with a mix of blaze, numpy and dynd arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        b = blaze.array(b)
        d = nd.array(a)
        cr = blaze._elwise_eval("a * b + d", vm=self.vm)
        nr = a * b + d
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test05(self):
        """Testing with a mix of scalars and blaze, numpy and dynd arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        b = blaze.array(b)
        d = nd.array(a)
        cr = blaze._elwise_eval("a * b + d + 2", vm=self.vm)
        nr = a * b + d + 2
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test06(self):
        """Testing reductions on blaze arrays"""
        if self.vm == "python":
            # The reductions does not work well using Blaze expressions yet
            return
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        b = blaze.array(b)
        cr = blaze._elwise_eval("sum(b + 2)", vm=self.vm)
        nr = np.sum(b + 2)
        self.assert_(cr == nr, "eval does not work correctly")


# Check for arrays that fit in the chunk size
# Using the Python VM (i.e. Blaze machinery) here
class evalPythonTest(evalTest):
    vm = "python"

# Check for arrays that are larger than a chunk
class evalLargeTest(evalTest):
    N = 10000

# Check for arrays that are larger than a chunk
# Using the Python VM (i.e. Blaze machinery) here
class evalPythonLargeTest(evalTest):
    N = 10000
    vm = "python"


# Check for arrays stored on-disk, but fit in a chunk
# Check for arrays that fit in memory
class storageTest(MayBePersistentTest):
    N = 1000
    vm = "numexpr"
    disk = "BLZ"

    def test00(self):
        """Testing elwise_eval() with only blaze arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = blaze.array(b, ddesc=self.ddesc2)
        cr = blaze._elwise_eval("c * d", vm=self.vm, ddesc=self.ddesc3)
        nr = a * b
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test01(self):
        """Testing elwise_eval() with blaze arrays and constants"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = blaze.array(b, ddesc=self.ddesc2)
        cr = blaze._elwise_eval("c * d + 1", vm=self.vm, ddesc=self.ddesc3)
        nr = a * b + 1
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test03(self):
        """Testing elwise_eval() with blaze and dynd arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = nd.array(b)
        cr = blaze._elwise_eval("c * d + 1", vm=self.vm, ddesc=self.ddesc3)
        nr = a * b + 1
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test04(self):
        """Testing elwise_eval() with blaze, dynd and numpy arrays"""
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = nd.array(b)
        cr = blaze._elwise_eval("a * c + d", vm=self.vm, ddesc=self.ddesc3)
        nr = a * c + d
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test05(self):
        """Testing reductions on blaze arrays"""
        if self.vm == "python":
            # The reductions does not work well using Blaze expressions yet
            return
        a, b = np.arange(self.N), np.arange(1, self.N+1)
        b = blaze.array(b, ddesc=self.ddesc1)
        cr = blaze._elwise_eval("sum(b + 2)", vm=self.vm, ddesc=self.ddesc3)
        nr = np.sum(b + 2)
        self.assert_(cr == nr, "eval does not work correctly")


# Check for arrays stored on-disk, but fit in a chunk
# Using the Python VM (i.e. Blaze machinery) here
class storagePythonTest(storageTest):
    vm = "python"

# Check for arrays stored on-disk, but are larger than a chunk
class storageLargeTest(storageTest):
    N = 10000

# Check for arrays stored on-disk, but are larger than a chunk
# Using the Python VM (i.e. Blaze machinery) here
class storagePythonLargeTest(storageTest):
    N = 10000
    vm = "python"

# Check for arrays stored on-disk, but fit in a chunk
class storageHDF5Test(storageTest):
    disk = "HDF5"

# Check for arrays stored on-disk, but are larger than a chunk
class storageLargeHDF5Test(storageTest):
    N = 10000
    disk = "HDF5"

####################################
# Multidimensional tests start now
####################################

# Check for arrays that fit in a chunk
class evalMDTest(unittest.TestCase):
    N = 10
    M = 100
    vm = "numexpr"

    def test00(self):
        """Testing elwise_eval() with only blaze arrays"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = blaze.array(a)
        d = blaze.array(b)
        cr = blaze._elwise_eval("c * d", vm=self.vm)
        nr = a * b
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test01(self):
        """Testing elwise_eval() with blaze arrays and scalars"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = blaze.array(a)
        d = blaze.array(b)
        cr = blaze._elwise_eval("c * d + 2", vm=self.vm)
        nr = a * b + 2
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test02(self):
        """Testing elwise_eval() with pure dynd arrays and scalars"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = nd.array(a)
        d = nd.array(b)
        cr = blaze._elwise_eval("c * d + 2", vm=self.vm)
        nr = a * b + 2
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test03(self):
        """Testing elwise_eval() with blaze and dynd arrays and scalars"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = blaze.array(a)
        d = nd.array(b)
        cr = blaze._elwise_eval("c * d + 2", vm=self.vm)
        nr = a * b + 2
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test04(self):
        """Testing reductions on blaze arrays"""
        if self.vm == "python":
            # The reductions does not work well using Blaze expressions yet
            return
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        b = blaze.array(b)
        cr = blaze._elwise_eval("sum(b + 2)", vm=self.vm)
        nr = np.sum(b + 2)
        self.assert_(cr == nr, "eval does not work correctly")

    def test05(self):
        """Testing reductions on blaze arrays and axis=0"""
        if self.vm == "python":
            # The reductions does not work well using Blaze expressions yet
            return
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        b = blaze.array(b)
        cr = blaze._elwise_eval("sum(b + 2, axis=0)", vm=self.vm)
        nr = np.sum(b + 2, axis=0)
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test06(self):
        """Testing reductions on blaze arrays and axis=1"""
        if self.vm == "python":
            # The reductions does not work well using Blaze expressions yet
            return
        self.assertRaises(NotImplementedError,
                          blaze._elwise_eval, "sum([[1,2],[3,4]], axis=1)")


# Check for arrays that fit in a chunk
# Using the Python VM (i.e. Blaze machinery) here
class evalPythonMDTest(evalMDTest):
    vm = "python"

# Check for arrays that does not fit in a chunk
class evalLargeMDTest(evalMDTest):
    N = 100
    M = 100

# Check for arrays that does not fit in a chunk, but using python VM
class evalPythonLargeMDTest(evalMDTest):
    N = 100
    M = 100
    vm = "python"

# Check for arrays that fit in a chunk (HDF5)
class evalMDHDF5Test(evalMDTest):
    disk = "HDF5"

# Check for arrays that does not fit in a chunk (HDF5)
class evalLargeMDHDF5Test(evalMDTest):
    N = 100
    M = 100
    disk = "HDF5"


# Check for arrays stored on-disk, but fit in a chunk
# Check for arrays that fit in memory
class storageMDTest(MayBePersistentTest):
    N = 10
    M = 100
    vm = "numexpr"
    disk = "BLZ"

    def test00(self):
        """Testing elwise_eval() with only blaze arrays"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = blaze.array(b, ddesc=self.ddesc2)
        cr = blaze._elwise_eval("c * d", vm=self.vm, ddesc=self.ddesc3)
        nr = a * b
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test01(self):
        """Testing elwise_eval() with blaze arrays and constants"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = blaze.array(b, ddesc=self.ddesc2)
        cr = blaze._elwise_eval("c * d + 1", vm=self.vm, ddesc=self.ddesc3)
        nr = a * b + 1
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test03(self):
        """Testing elwise_eval() with blaze and dynd arrays"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = nd.array(b)
        cr = blaze._elwise_eval("c * d + 1", vm=self.vm, ddesc=self.ddesc3)
        nr = a * b + 1
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test04(self):
        """Testing elwise_eval() with blaze, dynd and numpy arrays"""
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        c = blaze.array(a, ddesc=self.ddesc1)
        d = nd.array(b)
        cr = blaze._elwise_eval("a * c + d", vm=self.vm, ddesc=self.ddesc3)
        nr = a * c + d
        assert_array_equal(cr[:], nr, "eval does not work correctly")

    def test05(self):
        """Testing reductions on blaze arrays"""
        if self.vm == "python":
            # The reductions does not work well using Blaze expressions yet
            return
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        b = blaze.array(b, ddesc=self.ddesc1)
        cr = blaze._elwise_eval("sum(b + 2)", vm=self.vm, ddesc=self.ddesc3)
        nr = np.sum(b + 2)
        self.assert_(cr == nr, "eval does not work correctly")

    def test06(self):
        """Testing reductions on blaze arrays and axis=0"""
        if self.vm == "python":
            # The reductions does not work well using Blaze expressions yet
            return
        a = np.arange(self.N*self.M).reshape(self.N, self.M)
        b = np.arange(1, self.N*self.M+1).reshape(self.N, self.M)
        b = blaze.array(b, ddesc=self.ddesc1)
        cr = blaze._elwise_eval("sum(b, axis=0)",
                                vm=self.vm, ddesc=self.ddesc3)
        nr = np.sum(b, axis=0)
        assert_array_equal(cr, nr, "eval does not work correctly")


# Check for arrays stored on-disk, but fit in a chunk
# Using the Python VM (i.e. Blaze machinery) here
class storagePythonMDTest(storageMDTest):
    vm = "python"

# Check for arrays stored on-disk, but are larger than a chunk
class storageLargeMDTest(storageMDTest):
    N = 500

# Check for arrays stored on-disk, but are larger than a chunk
# Using the Python VM (i.e. Blaze machinery) here
class storagePythonLargeMDTest(storageMDTest):
    N = 500
    vm = "python"

# Check for arrays stored on-disk, but fit in a chunk
class storageMDHDF5Test(storageMDTest):
    disk = "HDF5"

# Check for arrays stored on-disk, but are larger than a chunk
class storageLargeMDHDF5Test(storageMDTest):
    N = 500
    disk = "HDF5"


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_expr
from __future__ import absolute_import, division, print_function

import unittest

from datashape import dshape
from dynd import nd, ndt
from blaze import array
from blaze.compute.ops.ufuncs import add, multiply


class TestGraph(unittest.TestCase):

    def test_graph(self):
        a = array(nd.range(10, dtype=ndt.int32))
        b = array(nd.range(10, dtype=ndt.float32))
        expr = add(a, multiply(a, b))
        graph, ctx = expr.expr
        self.assertEqual(len(ctx.params), 2)
        self.assertFalse(ctx.constraints)
        self.assertEqual(graph.dshape, dshape('10 * float64'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_where
from __future__ import absolute_import, division, print_function

import unittest

import numpy as np

from dynd import nd, ndt
import blaze

import unittest
import tempfile
import os
import glob
import blaze
import blz

from blaze.optional_packages import tables_is_here
if tables_is_here:
    import tables


# Useful superclass for disk-based tests
class createTables(unittest.TestCase):
    disk = None
    open = False

    def setUp(self):
        self.dtype = 'i4,f8'
        self.npt = np.fromiter(((i, i*2.) for i in range(self.N)),
                               dtype=self.dtype, count=self.N)
        if self.disk == 'BLZ':
            prefix = 'blaze-' + self.__class__.__name__
            suffix = '.blz'
            path = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
            os.rmdir(path)
            if self.open:
                table = blz.fromiter(
                    ((i, i*2.) for i in range(self.N)), dtype=self.dtype,
                    count=self.N, rootdir=path)
                self.ddesc = blaze.BLZ_DDesc(table, mode='r')
            else:
                self.ddesc = blaze.BLZ_DDesc(path, mode='w')
                a = blaze.array([(i, i*2.) for i in range(self.N)],
                                'var * {f0: int32, f1: float64}',
                                ddesc=self.ddesc)
        elif self.disk == 'HDF5' and tables_is_here:
            prefix = 'hdf5-' + self.__class__.__name__
            suffix = '.hdf5'
            dpath = "/table"
            h, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(h)  # close the not needed file handle
            if self.open:
                with tables.open_file(path, "w") as h5f:
                    ra = np.fromiter(
                        ((i, i*2.) for i in range(self.N)), dtype=self.dtype,
                        count=self.N)
                    h5f.create_table('/', dpath[1:], ra)
                self.ddesc = blaze.HDF5_DDesc(path, dpath, mode='r')
            else:
                self.ddesc = blaze.HDF5_DDesc(path, dpath, mode='w')
                a = blaze.array([(i, i*2.) for i in range(self.N)],
                                'var * {f0: int32, f1: float64}',
                                ddesc=self.ddesc)
        else:
            table = blz.fromiter(
                ((i, i*2.) for i in range(self.N)), dtype=self.dtype,
                count=self.N)
            self.ddesc = blaze.BLZ_DDesc(table, mode='r')

    def tearDown(self):
        self.ddesc.remove()

# Check for tables in-memory (BLZ)
class whereTest(createTables):
    N = 1000

    def test00(self):
        """Testing the dshape attribute of a streamed array"""
        t = blaze.array(self.ddesc)
        st = t.where("f0 < 10")
        self.assertTrue(isinstance(st, blaze.Array))
        self.assertTrue(isinstance(st.ddesc, blaze.Stream_DDesc))
        self.assertEqual(t.dshape.measure, st.dshape.measure)

    def test01(self):
        """Testing with a filter in only one field"""
        t = blaze.array(self.ddesc)
        st = t.where("f0 < 10")
        cr = list(st)
        # Get a list of dictionaries so as to emulate blaze iter output
        nr = [dict(zip(x.dtype.names, x)) for x in self.npt[
                   self.npt['f0'] < 10]]
        self.assertEqual(cr, nr, "where does not work correctly")

    def test02(self):
        """Testing with two fields"""
        t = blaze.array(self.ddesc)
        st = t.where("(f0 < 10) & (f1 > 4)")
        cr = list(st)
        # Get a list of dictionaries so as to emulate blaze iter output
        nr = [dict(zip(x.dtype.names, x)) for x in self.npt[
                  (self.npt['f0'] < 10) & (self.npt['f1'] > 4)]]
        self.assertEqual(cr, nr, "where does not work correctly")

# Check for tables on-disk (BLZ)
class whereBLZDiskTest(whereTest):
    disk = "BLZ"

# Check for tables on-disk (HDF5)
class whereHDF5DiskTest(whereTest):
    disk = "HDF5"

# Check for tables on-disk, using existing BLZ files
class whereBLZDiskOpenTest(whereTest):
    disk = "BLZ"
    open = True

# Check for tables on-disk, using existng HDF5 files
class whereHDF5DiskOpenTest(whereTest):
    disk = "HDF5"
    open = True



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = core
from __future__ import absolute_import, division, print_function

from itertools import chain
from dynd import nd
import datashape

from .utils import validate, coerce
from ..utils import partition_all

__all__ = ['DataDescriptor']


def isdimension(ds):
    return isinstance(ds, (datashape.Var, datashape.Fixed))


class DataDescriptor(object):
    """
    Standard interface to data storage

    Data descriptors provide read and write access to common data storage
    systems like csv, json, HDF5, and SQL.

    They provide Pythonic iteration over these resources as well as efficient
    chunked access with DyND arrays.

    Data Descriptors implement the following methods:

    __iter__ - iterate over storage, getting results as Python objects
    chunks - iterate over storage, getting results as DyND arrays
    extend - insert new data into storage (if possible.)
             Consumes a sequence of core Python objects
    extend_chunks - insert new data into storage (if possible.)
             Consumes a sequence of DyND arrays
    as_dynd - load entire dataset into memory as a DyND array
    """

    def extend(self, rows):
        """ Extend data with many rows
        """
        if not self.appendable or self.immutable:
            raise TypeError('Data Descriptor not appendable')
        rows = iter(rows)
        row = next(rows)
        if not validate(self.schema, row):
            raise ValueError('Invalid data:\n\t %s \nfor dshape \n\t%s' %
                    (str(row), self.schema))
        self._extend(chain([row], rows))


    def extend_chunks(self, chunks):
        if not self.appendable or self.immutable:
            raise TypeError('Data Descriptor not appendable')
        self._extend_chunks((nd.array(chunk) for chunk in chunks))

    def _extend_chunks(self, chunks):
        self.extend((row for chunk in chunks for row in nd.as_py(chunk)))

    def chunks(self, **kwargs):
        def dshape(chunk):
            return str(len(chunk) * self.dshape.subarray(1))

        chunks = self._chunks(**kwargs)
        return (nd.array(chunk, dtype=dshape(chunk)) for chunk in chunks)

    def _chunks(self, blen=100):
        return partition_all(blen, iter(self))

    def getattr(self, name):
        raise NotImplementedError('this data descriptor does not support attribute access')

    def as_dynd(self):
        return nd.array(self.as_py(), dtype=str(self.dshape))

    def as_py(self):
        if isdimension(self.dshape[0]):
            return list(self)
        else:
            return nd.as_py(self.as_dynd())

    def __array__(self):
        return nd.as_numpy(self.as_dynd())

    def __getitem__(self, key):
        if hasattr(self, '_getitem'):
            return coerce(self.schema, self._getitem(key))
        else:
            return self.as_dynd()[key]

    def __iter__(self):
        try:
            for row in self._iter():
                yield coerce(self.schema, row)
        except NotImplementedError:
            py = nd.as_py(self.as_dynd())
            if isdimension(self.dshape[0]):
                for row in py:
                    yield row
            else:
                yield py

    def _iter(self):
        raise NotImplementedError()

    _dshape = None
    @property
    def dshape(self):
        return datashape.dshape(self._dshape or datashape.Var() * self.schema)

    _schema = None
    @property
    def schema(self):
        if self._schema:
            return datashape.dshape(self._schema)
        if isdimension(self.dshape[0]):
            return self.dshape.subarray(1)
        raise TypeError('Datashape is not indexable to schema\n%s' %
                        self.dshape)

########NEW FILE########
__FILENAME__ = csv
from __future__ import absolute_import, division, print_function

import csv
import itertools as it
import os

import datashape
from dynd import nd

from .core import DataDescriptor
from .utils import coerce_record_to_row
from ..utils import partition_all, nth
from .. import py2help

__all__ = ['CSV']


def has_header(sample):
    """

    >>> s = '''
    ... x,y
    ... 1,1
    ... 2,2'''
    >>> has_header(s)
    True
    """
    sniffer = csv.Sniffer()
    try:
        return sniffer.has_header(sample)
    except:
        return None


def discover_dialect(sample, dialect=None, **kwargs):
    """

    >>> s = '''
    ... 1,1
    ... 2,2'''
    >>> discover_dialect(s) # doctest: +SKIP
    {'escapechar': None,
     'skipinitialspace': False,
     'quoting': 0,
     'delimiter': ',',
     'lineterminator': '\r\n',
     'quotechar': '"',
     'doublequote': False}
    """
    if isinstance(dialect, py2help._strtypes):
        dialect = csv.get_dialect(dialect)

    sniffer = csv.Sniffer()
    if not dialect:
        try:
            dialect = sniffer.sniff(sample)
        except:
            dialect = csv.get_dialect('excel')

    # Convert dialect to dictionary
    dialect = dict((key, getattr(dialect, key))
                   for key in dir(dialect) if not key.startswith('_'))

    # Update dialect with any keyword arguments passed in
    # E.g. allow user to override with delimiter=','
    for k, v in kwargs.items():
        if k in dialect:
            dialect[k] = v

    return dialect


class CSV(DataDescriptor):
    """
    A Blaze data descriptor which exposes a CSV file.

    Parameters
    ----------
    path : string
        A path string for the CSV file.
    schema : string or datashape
        A datashape (or its string representation) of the schema
        in the CSV file.
    dialect : string or csv.Dialect instance
        The dialect as understood by the `csv` module in Python standard
        library.  If not specified, a value is guessed.
    header : boolean
        Whether the CSV file has a header or not.  If not specified a value
        is guessed.
    """
    immutable = False
    deferred = False
    persistent = True
    appendable = True
    remote = False

    def __init__(self, path, mode='r', schema=None, dshape=None,
                 dialect=None, header=None, open=open, **kwargs):
        if 'r' in mode and os.path.isfile(path) is not True:
            raise ValueError('CSV file "%s" does not exist' % path)
        self.path = path
        self.mode = mode
        self.open = open

        if not schema and not dshape:
            # TODO: Infer schema
            raise ValueError('No schema detected')
        if not schema and dshape:
            dshape = datashape.dshape(dshape)
            if isinstance(dshape[0], datashape.Var):
                schema = dshape.subarray(1)

        self._schema = schema

        if os.path.exists(path) and mode != 'w':
            with self.open(path, 'r') as f:
                sample = f.read(1024)
        else:
            sample = ''
        dialect = discover_dialect(sample, dialect, **kwargs)
        assert dialect
        if header is None:
            header = has_header(sample)

        self.header = header
        self.dialect = dialect

    def _getitem(self, key):
        with self.open(self.path, self.mode) as f:
            if self.header:
                next(f)
            if isinstance(key, py2help._inttypes):
                line = nth(key, f)
                result = next(csv.reader([line], **self.dialect))
            elif isinstance(key, slice):
                start, stop, step = key.start, key.stop, key.step
                result = list(csv.reader(it.islice(f, start, stop, step),
                                         **self.dialect))
            else:
                raise IndexError("key '%r' is not valid" % key)
        return result

    def _iter(self):
        with self.open(self.path, 'r') as f:
            if self.header:
                next(f)  # burn header
            for row in csv.reader(f, **self.dialect):
                yield row

    def _extend(self, rows):
        rows = iter(rows)
        with self.open(self.path, self.mode) as f:
            if self.header:
                next(f)
            row = next(rows)
            if isinstance(row, dict):
                schema = datashape.dshape(self.schema)
                row = coerce_record_to_row(schema, row)
                rows = (coerce_record_to_row(schema, row) for row in rows)

            # Write all rows to file
            f.seek(0, os.SEEK_END)  # go to the end of the file
            writer = csv.writer(f, **self.dialect)
            writer.writerow(row)
            writer.writerows(rows)

    def remove(self):
        """Remove the persistent storage."""
        os.unlink(self.path)

########NEW FILE########
__FILENAME__ = dynd
from __future__ import absolute_import, division, print_function

from dynd import nd

from .core import DataDescriptor


class DyND(DataDescriptor):
    deferred = False
    persistent = False
    appendable = False
    remote = False

    def __init__(self, arr):
        self.arr = arr

    @property
    def immutable(self):
        return self.arr.access_flags == 'immutable'

    @property
    def _dshape(self):
        return nd.dshape_of(self.arr)

    def _iter(self):
        return iter(self.arr)

    def _getitem(self, key):
        return self.storage[key]

    def _chunks(self, blen=100):
        for i in range(0, len(self.arr), blen):
            start = i
            stop = min(i + blen, len(self.arr))
            yield self.arr[start:stop]

    def as_dynd(self):
        return self.arr

########NEW FILE########
__FILENAME__ = filesystem
from __future__ import absolute_import, division, print_function

from dynd import nd
from glob import glob
from itertools import chain
from datashape import dshape, Var

from .core import DataDescriptor
from .. import py2help

__all__ = 'Files',

class Files(DataDescriptor):
    immutable = True
    deferred = False
    appendable = False
    remote = False
    persistent = True

    def __init__(self, files, descriptor, subdshape=None, schema=None,
            open=open):
        if isinstance(files, py2help._strtypes):
            files = glob(files)
        self.filenames = files

        self.open = open

        self.descriptor = descriptor
        if schema and not subdshape:
            subdshape = Var() * schema
        self.subdshape = dshape(subdshape)

    @property
    def dshape(self):
        if isinstance(self.subdshape[0], Var):
            return self.subdshape
        else:
            return Var() * self.subdshape

    def _iter(self):
        return chain.from_iterable(self.descriptor(fn,
                                                   dshape=self.subdshape,
                                                   open=self.open)
                                    for fn in self.filenames)

########NEW FILE########
__FILENAME__ = hdf5
from __future__ import absolute_import, division, print_function

import numpy as np
from itertools import chain
import h5py
from dynd import nd
import datashape

from .core import DataDescriptor
from ..utils import partition_all

h5py_attributes = ['chunks', 'compression', 'compression_opts', 'dtype',
                   'fillvalue', 'fletcher32', 'maxshape', 'shape']

__all__ = ['HDF5']

class HDF5(DataDescriptor):
    """
    A Blaze data descriptor which exposes an HDF5 file.

    Parameters
    ----------
    path: string
        Location of hdf5 file on disk
    datapath: string
        Location of array dataset in hdf5
    mode : string
        r, w, rw+
    dshape: string or Datashape
        a datashape describing the data
    schema: string or DataShape
        datashape describing one row of data
    **kwargs:
        Options to send to h5py - see h5py.File.create_dataset for options
    """
    immutable = False
    deferred = False
    persistent = True
    appendable = True
    remote = False

    def __init__(self, path, datapath, mode='r', schema=None, dshape=None, **kwargs):
        self.path = path
        self.datapath = datapath
        self.mode = mode

        if schema and not dshape:
            dshape = 'var * ' + str(schema)

        # TODO: provide sane defaults for kwargs
        # Notably chunks and maxshape
        if dshape:
            dshape = datashape.dshape(dshape)
            shape = dshape.shape
            dtype = datashape.to_numpy_dtype(dshape[-1])
            if shape[0] == datashape.Var():
                kwargs['chunks'] = True
                kwargs['maxshape'] = kwargs.get('maxshape', (None,) + shape[1:])
                shape = (0,) + tuple(map(int, shape[1:]))

        with h5py.File(path, mode) as f:
            dset = f.get(datapath)
            if dset is None:
                if dshape is None:
                    raise ValueError('No dataset or dshape provided')
                else:
                    f.create_dataset(datapath, shape, dtype=dtype, **kwargs)
            else:
                dshape2 = datashape.from_numpy(dset.shape, dset.dtype)
                dshape = dshape2
                # TODO: test provided dshape against given dshape
                # if dshape and dshape != dshape2:
                #     raise ValueError('Inconsistent datashapes.'
                #             '\nGiven: %s\nFound: %s' % (dshape, dshape2))

        attributes = self.attributes()
        if attributes['chunks']:
            # is there a better way to do this?
            words = str(dshape).split(' * ')
            dshape = 'var * ' + ' * '.join(words[1:])
            dshape = datashape.dshape(dshape)

        self._dshape = dshape
        self._schema = schema

    def attributes(self):
        with h5py.File(self.path, 'r') as f:
            arr = f[self.datapath]
            result = dict((attr, getattr(arr, attr))
                            for attr in h5py_attributes)
        return result

    def __getitem__(self, key):
        with h5py.File(self.path, mode='r') as f:
            arr = f[self.datapath]
            result = np.asarray(arr[key])
        return nd.asarray(result, access='readonly')

    def __setitem__(self, key, value):
        with h5py.File(self.path, mode=self.mode) as f:
            arr = f[self.datapath]
            arr[key] = value
        return self

    def _chunks(self, blen=100):
        with h5py.File(self.path, mode='r') as f:
            arr = f[self.datapath]
            for i in range(0, arr.shape[0], blen):
                yield np.array(arr[i:i+blen])

    def as_dynd(self):
        return self[:]

    def _extend_chunks(self, chunks):
        if 'w' not in self.mode and 'a' not in self.mode:
            raise ValueError('Read only')

        with h5py.File(self.path, mode=self.mode) as f:
            dset = f[self.datapath]
            dtype = dset.dtype
            shape = dset.shape
            for chunk in chunks:
                arr = np.array(chunk, dtype=dtype)
                shape = list(dset.shape)
                shape[0] += len(arr)
                dset.resize(shape)
                dset[-len(arr):] = arr

    def _extend(self, seq):
        self.extend_chunks(partition_all(100, seq))

    def _iter(self):
        return chain.from_iterable(self.chunks())

########NEW FILE########
__FILENAME__ = json
from __future__ import absolute_import, division, print_function

import os
import json

from itertools import islice
import datashape
from dynd import nd

from ..utils import partition_all, nth
from .. import py2help
from ..py2help import _inttypes
from .core import DataDescriptor, isdimension
from .utils import coerce


class JSON(DataDescriptor):
    """
    A Blaze data descriptor to expose a JSON file.

    Parameters
    ----------
    path : string
        A path string for the JSON file.
    schema : string or datashape
        A datashape (or its string representation) of the schema
        in the JSON file.
    """
    immutable = True
    deferred = False
    persistent = True
    appendable = False
    remote = False

    def __init__(self, path, mode='r', schema=None, dshape=None, open=open):
        self.path = path
        self.mode = mode
        self.open = open
        if dshape:
            dshape = datashape.dshape(dshape)
        if dshape and not schema and isdimension(dshape[0]):
            schema = dshape.subarray(1)

        if isinstance(schema, py2help._strtypes):
            schema = datashape.dshape(schema)
        if not schema and not dshape:
            # TODO: schema detection from file
            raise ValueError('No schema found')
        # Initially the array is not loaded (is this necessary?)
        self._cache_arr = None

        self._schema = schema
        self._dshape = dshape

    @property
    def _arr_cache(self):
        if self._cache_arr is not None:
            return self._cache_arr
        jsonfile = self.open(self.path)
        # This will read everything in-memory (but a memmap approach
        # is in the works)
        self._cache_arr = nd.parse_json(str(self.dshape), jsonfile.read())
        try:
            jsonfile.close()
        except:
            pass
        return self._cache_arr

    def as_dynd(self):
        return self._arr_cache

    def as_py(self):
        with open(self.path) as f:
            result = json.load(f)
        return result

    def remove(self):
        """Remove the persistent storage."""
        os.unlink(self.path)


class JSON_Streaming(JSON):
    """
    A Blaze data descriptor to expose a Streaming JSON file.

    Parameters
    ----------
    path : string
        A path string for the JSON file.
    schema : string or datashape
        A datashape (or its string representation) of the schema
        in the JSON file.
    """
    immutable = False

    @property
    def _arr_cache(self):
        if self._cache_arr is not None:
            return self._cache_arr
        jsonfile = self.open(self.path)
        # This will read everything in-memory (but a memmap approach
        # is in the works)
        text = '[' + ', '.join(jsonfile) + ']'
        try:
            jsonfile.close()
        except:
            pass
        self._cache_arr = nd.parse_json(str(self.dshape), text)
        return self._cache_arr

    def __getitem__(self, key):
        with self.open(self.path) as f:
            if isinstance(key, _inttypes):
                result = json.loads(nth(key, f))
            elif isinstance(key, slice):
                result = list(map(json.loads,
                                    islice(f, key.start, key.stop, key.step)))
            else:
                raise NotImplementedError('Fancy indexing not supported\n'
                        'Create DyND array and use fancy indexing from there')
        return coerce(self.schema, result)

    def _iter(self):
        with self.open(self.path) as f:
            for line in f:
                yield json.loads(line)

    __iter__ = DataDescriptor.__iter__

    def as_py(self):
        return list(self)

    def _iterchunks(self, blen=100):
        with self.open(self.path) as f:
            for chunk in partition_all(blen, f):
                text = '[' + ',\r\n'.join(chunk) + ']'
                dshape = str(len(chunk)) + ' * ' + self.schema
                yield nd.parse_json(dshape, text)

    @property
    def appendable(self):
        return any(c in self.mode for c in 'wa+')

    def _extend(self, rows):
        if not self.appendable:
            raise IOError("Read only access")
        with self.open(self.path, self.mode) as f:
            f.seek(0, os.SEEK_END)  # go to the end of the file
            for row in rows:
                json.dump(row, f)
                f.write('\n')

    def _chunks(self, blen=100):
        with self.open(self.path) as f:
            for chunk in partition_all(blen, f):
                text = '[' + ',\r\n'.join(chunk) + ']'
                dshape = str(len(chunk) * self.schema)
                yield nd.parse_json(dshape, text)

########NEW FILE########
__FILENAME__ = python
from __future__ import absolute_import, division, print_function

from dynd import nd

from .core import DataDescriptor

class Python(DataDescriptor):
    immutable = False
    deferred = False
    appendable = True
    remote = False
    persistent = False

    def __init__(self, storage=None, schema=None, dshape=None):
        self.storage = storage if storage is not None else []
        self._schema = schema
        self._dshape = dshape

    def _extend(self, seq):
        self.storage.extend(seq)

    def _iter(self):
        return iter(self.storage)

    def _getitem(self, key):
        return self.storage[key]

    def as_py(self):
        return self.storage

########NEW FILE########
__FILENAME__ = sql
from __future__ import absolute_import, division, print_function

from datetime import date, datetime, time
from decimal import Decimal
from dynd import nd
import sqlalchemy as sql
import datashape

from ..utils import partition_all
from ..py2help import basestring
from .core import DataDescriptor
from .utils import coerce_row_to_dict

# http://docs.sqlalchemy.org/en/latest/core/types.html

types = {'int64': sql.types.BigInteger,
         'int32': sql.types.Integer,
         'int': sql.types.Integer,
         'int16': sql.types.SmallInteger,
         'float': sql.types.Float,
         'string': sql.types.String,  # Probably just use only this
#         'date': sql.types.Date,
#         'time': sql.types.Time,
#         'datetime': sql.types.DateTime,
#         bool: sql.types.Boolean,
#         ??: sql.types.LargeBinary,
#         Decimal: sql.types.Numeric,
#         ??: sql.types.PickleType,
#         unicode: sql.types.Unicode,
#         unicode: sql.types.UnicodeText,
#         str: sql.types.Text,  # ??
         }

def dshape_to_alchemy(dshape):
    """

    >>> dshape_to_alchemy('int')
    <class 'sqlalchemy.sql.sqltypes.Integer'>

    >>> dshape_to_alchemy('string')
    <class 'sqlalchemy.sql.sqltypes.String'>

    >>> dshape_to_alchemy('{name: string, amount: int}')
    [Column('name', String(), table=None), Column('amount', Integer(), table=None)]
    """
    dshape = datashape.dshape(dshape)
    if str(dshape) in types:
        return types[str(dshape)]
    try:
        return [sql.Column(name, dshape_to_alchemy(typ))
                for name, typ in dshape.parameters[0].parameters[0]]
    except TypeError:
        raise NotImplementedError("Datashape not supported for SQL Schema")


class SQL(DataDescriptor):
    """
    A Blaze data descriptor to expose a SQL database.

    >>> dd = SQL('sqlite:///:memory:', 'accounts',
    ...          schema='{name: string, amount: int}')

    Insert into database

    >>> dd.extend([('Alice', 100), ('Bob', 200)])

    Select all from table
    >>> list(dd)
    [(u'Alice', 100), (u'Bob', 200)]

    Verify that we're actually touching the database

    >>> with dd.engine.connect() as conn:
    ...     print(list(conn.execute('SELECT * FROM accounts')))
    [(u'Alice', 100), (u'Bob', 200)]


    Parameters
    ----------
    engine : string, A SQLAlchemy engine
        uri of database
        or SQLAlchemy engine
    table : string
        The name of the table
    schema : string, list of Columns
        The datashape/schema of the database
        Possibly a list of SQLAlchemy columns
    """
    immutable = False
    deferred = False
    appendable = True

    @property
    def remote(self):
        return self.engine.dialect.name != 'sqlite'

    @property
    def persistent(self):
        return self.engine.url != 'sqlite:///:memory:'


    def __init__(self, engine, tablename, primary_key='', schema=None):
        if isinstance(engine, basestring):
            engine = sql.create_engine(engine)
        self.engine = engine
        self.tablename = tablename

        if isinstance(schema, (str, datashape.DataShape)):
            columns = dshape_to_alchemy(schema)
            for column in columns:
                if column.name == primary_key:
                    column.primary_key = True

        if schema is None:  # Table must exist
            if not engine.has_table(tablename):
                raise ValueError('Must provide schema. Table %s does not exist'
                                 % tablename)

        self._schema = datashape.dshape(schema)
        metadata = sql.MetaData()

        table = sql.Table(tablename, metadata, *columns)

        self.table = table
        metadata.create_all(engine)

    def __iter__(self):
        with self.engine.connect() as conn:
            result = conn.execute(sql.sql.select([self.table]))
            for item in result:
                yield item

    @property
    def dshape(self):
        return datashape.Var() * self.schema

    def extend(self, rows):
        rows = (coerce_row_to_dict(self.schema, row)
                    if isinstance(row, (tuple, list)) else row
                    for row in rows)
        with self.engine.connect() as conn:
            for chunk in partition_all(1000, rows):  # TODO: 1000 is hardcoded
                conn.execute(self.table.insert(), chunk)

    def chunks(self, blen=1000):
        for chunk in partition_all(blen, iter(self)):
            dshape = str(len(chunk)) + ' * ' + str(self.schema)
            yield nd.array(chunk, dtype=dshape)

########NEW FILE########
__FILENAME__ = test_csv
from __future__ import absolute_import, division, print_function

import unittest
import tempfile
import os
import csv

import datashape

from blaze.data.core import DataDescriptor
from blaze.data import CSV
from blaze.data.csv import has_header
from blaze.utils import filetext
from dynd import nd


def sanitize(lines):
    return '\n'.join(line.strip() for line in lines.split('\n'))


class Test_Dialect(unittest.TestCase):

    buf = sanitize(
    u"""Name Amount
        Alice 100
        Bob 200
        Alice 50
    """)

    schema = "{ f0: string, f1: int }"

    def setUp(self):
        self.csv_file = tempfile.mktemp(".csv")
        with open(self.csv_file, "w") as f:
            f.write(self.buf)
        self.dd = CSV(self.csv_file, dialect='excel', schema=self.schema,
                            delimiter=' ', mode='r+')

    def tearDown(self):
        os.remove(self.csv_file)

    def test_has_header(self):
        assert has_header(self.buf)

    def test_overwrite_delimiter(self):
        self.assertEquals(self.dd.dialect['delimiter'], ' ')

    def test_content(self):
        s = str(list(self.dd))
        assert 'Alice' in s and 'Bob' in s

    def test_append(self):
        self.dd.extend([('Alice', 100)])
        with open(self.csv_file) as f:
            self.assertEqual(f.readlines()[-1].strip(), 'Alice 100')

    def test_append_dict(self):
        self.dd.extend([{'f0': 'Alice', 'f1': 100}])
        with open(self.csv_file) as f:
            self.assertEqual(f.readlines()[-1].strip(), 'Alice 100')

    def test_extend_structured(self):
        with filetext('1,1.0\n2,2.0\n') as fn:
            csv = CSV(fn, 'r+', schema='{x: int32, y: float32}',
                            delimiter=',')
            csv.extend([(3, 3)])
            assert (list(csv) == [[1, 1.0], [2, 2.0], [3, 3.0]]
                 or list(csv) == [{'x': 1, 'y': 1.0},
                                  {'x': 2, 'y': 2.0},
                                  {'x': 3, 'y': 3.0}])


class TestCSV_New_File(unittest.TestCase):

    data = [('Alice', 100),
            ('Bob', 200),
            ('Alice', 50)]

    schema = "{ f0: string, f1: int32 }"

    def setUp(self):
        self.filename = tempfile.mktemp(".csv")

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_errs_without_dshape(self):
        self.assertRaises(ValueError, lambda: CSV(self.filename, 'w'))

    def test_creation(self):
        dd = CSV(self.filename, 'w', schema=self.schema, delimiter=' ')

    def test_creation_rw(self):
        dd = CSV(self.filename, 'w+', schema=self.schema, delimiter=' ')

    def test_append(self):
        dd = CSV(self.filename, 'w', schema=self.schema, delimiter=' ')
        dd.extend([self.data[0]])
        with open(self.filename) as f:
            self.assertEqual(f.readlines()[0].strip(), 'Alice 100')

    def test_extend(self):
        dd = CSV(self.filename, 'w', schema=self.schema, delimiter=' ')
        dd.extend(self.data)
        with open(self.filename) as f:
            lines = f.readlines()
            self.assertEqual(lines[0].strip(), 'Alice 100')
            self.assertEqual(lines[1].strip(), 'Bob 200')
            self.assertEqual(lines[2].strip(), 'Alice 50')

        expected_dshape = datashape.DataShape(datashape.Var(), self.schema)
        # TODO: datashape comparison is broken
        self.assertEqual(str(dd.dshape).replace(' ', ''),
                         str(expected_dshape).replace(' ', ''))

class TestTransfer(unittest.TestCase):

    def test_re_dialect(self):
        dialect1 = {'delimiter': ',', 'lineterminator': '\n'}
        dialect2 = {'delimiter': ';', 'lineterminator': '--'}

        text = '1,1\n2,2\n'

        schema = '2 * int32'

        with filetext(text) as source_fn:
            with filetext('') as dest_fn:
                src = CSV(source_fn, schema=schema, **dialect1)
                dst = CSV(dest_fn, mode='w', schema=schema, **dialect2)

                # Perform copy
                dst.extend(src)

                with open(dest_fn) as f:
                    self.assertEquals(f.read(), '1;1--2;2--')


    def test_iter(self):
        with filetext('1,1\n2,2\n') as fn:
            dd = CSV(fn, schema='2 * int32')
            self.assertEquals(list(dd), [[1, 1], [2, 2]])


    def test_chunks(self):
        with filetext('1,1\n2,2\n3,3\n4,4\n') as fn:
            dd = CSV(fn, schema='2 * int32')
            assert all(isinstance(chunk, nd.array) for chunk in dd.chunks())
            self.assertEquals(len(list(dd.chunks(blen=2))), 2)
            self.assertEquals(len(list(dd.chunks(blen=3))), 2)


    def test_iter_structured(self):
        with filetext('1,2\n3,4\n') as fn:
            dd = CSV(fn, schema='{x: int, y: int}')
            self.assertEquals(list(dd), [{'x': 1, 'y': 2}, {'x': 3, 'y': 4}])


class TestCSV(unittest.TestCase):

    # A CSV toy example
    buf = sanitize(
    u"""k1,v1,1,False
        k2,v2,2,True
        k3,v3,3,False
    """)
    schema = "{ f0: string, f1: string, f2: int16, f3: bool }"

    def setUp(self):
        self.csv_file = tempfile.mktemp(".csv")
        with open(self.csv_file, "w") as f:
            f.write(self.buf)

    def tearDown(self):
        os.remove(self.csv_file)

    def test_has_header(self):
        assert not has_header(self.buf)

    def test_basic_object_type(self):
        dd = CSV(self.csv_file, schema=self.schema)
        self.assertTrue(isinstance(dd, DataDescriptor))
        self.assertTrue(isinstance(dd.dshape.shape[0], datashape.Var))
        self.assertEqual(list(dd), [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_iter(self):
        dd = CSV(self.csv_file, schema=self.schema)

        self.assertEqual(list(dd), [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_as_py(self):
        dd = CSV(self.csv_file, schema=self.schema)

        self.assertEqual(dd.as_py(), [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_chunks(self):
        dd = CSV(self.csv_file, schema=self.schema)

        vals = []
        for el in dd.chunks(blen=2):
            self.assertTrue(isinstance(el, nd.array))
            vals.extend(nd.as_py(el))
        self.assertEqual(vals, [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_append(self):
        # Get a private file so as to not mess the original one
        csv_file = tempfile.mktemp(".csv")
        with open(csv_file, "w") as f:
            f.write(self.buf)
        dd = CSV(csv_file, schema=self.schema, mode='r+')
        dd.extend([["k4", "v4", 4, True]])
        vals = [nd.as_py(v) for v in dd.chunks(blen=2)]
        self.assertEqual(vals, [
            [{u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
             {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True}],
            [{u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False},
             {u'f0': u'k4', u'f1': u'v4', u'f2': 4, u'f3': True}]])
        self.assertRaises(ValueError, lambda: dd.extend([3.3]))
        os.remove(csv_file)

    def test_getitem_start(self):
        dd = CSV(self.csv_file, schema=self.schema)
        self.assertEqual(dd[0],
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False})

    def test_getitem_stop(self):
        dd = CSV(self.csv_file, schema=self.schema)
        self.assertEqual(dd[:1], [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False}])

    def test_getitem_step(self):
        dd = CSV(self.csv_file, schema=self.schema)
        self.assertEqual(dd[::2], [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_getitem_start_step(self):
        dd = CSV(self.csv_file, schema=self.schema)
        self.assertEqual(dd[1::2], [
        {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True}])


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_dynd
from blaze.data.dynd import *

from dynd import nd

from unittest import TestCase

class TestDyND(TestCase):
    def test_basic(self):
        data = [[1, 1], [2, 2]]
        arr = nd.array(data, dtype='2 * 2 * int32')

        dd = DyND(arr)

        assert str(dd.dshape) == '2 * 2 * int32'
        assert str(dd.schema) == '2 * int32'

        assert list(dd) == [[1, 1], [2, 2]]
        chunks = list(dd.chunks())

        assert all(isinstance(chunk, nd.array) for chunk in chunks)
        assert nd.as_py(chunks[0]) == data

        assert isinstance(dd.as_dynd(), nd.array)

        self.assertRaises(TypeError, lambda: dd.extend([(3, 3)]))

########NEW FILE########
__FILENAME__ = test_filesystem
import os
from contextlib import contextmanager
from unittest import TestCase
from dynd import nd

from blaze.data import Files, CSV
from blaze.utils import filetexts


data = {'a.csv': '1,1\n2,2',
        'b.csv': '3,3\n4,4\n5,5',
        'c.csv': '6,6\n7,7'}


class Test_Files(TestCase):
    def test_filesystem(self):
        with filetexts(data) as filenames:
            dd = Files(sorted(filenames), CSV, subdshape='var * 2 * int32')

            self.assertEqual(dd.filenames, ['a.csv', 'b.csv', 'c.csv'])
            self.assertEqual(str(dd.schema), '2 * int32')
            self.assertEqual(str(dd.dshape), 'var * 2 * int32')

            expected = [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7]]

            self.assertEqual(dd.as_py(), expected)

            result = dd.as_dynd()
            expected2 = nd.array(expected, dtype='int32')
            self.assertEqual(nd.as_py(result),
                             nd.as_py(expected2))

            self.assertEqual(list(dd), expected)
            self.assertEqual(list(dd), expected)  # Not one use only

            chunks = list(dd.chunks(blen=3))
            expected = [nd.array([[1, 1], [2, 2], [3, 3]], dtype='int32'),
                        nd.array([[4, 4], [5, 5], [6, 6]], dtype='int32')]

            assert all(nd.as_py(a) == nd.as_py(b) for a, b in zip(chunks, expected))


########NEW FILE########
__FILENAME__ = test_hdf5
import unittest
import tempfile
import os
from dynd import nd
import h5py
import numpy as np
from sys import stdout
from blaze.py2help import skip

from blaze.data import HDF5
from blaze.utils import tmpfile

class SingleTestClass(unittest.TestCase):
    def setUp(self):
        self.filename = tempfile.mktemp('h5')

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    @skip("This runs fine in isolation, segfaults in full test")
    def test_creation(self):
        dd = HDF5(self.filename, 'data', 'w', dshape='2 * 2 * int32')

        with h5py.File(self.filename, 'r') as f:
            d = f['data']
            self.assertEquals(d.dtype.name, 'int32')

        self.assertRaises(ValueError, lambda: HDF5('bar.hdf5', 'foo'))

    def test_existing_array(self):
        stdout.flush()
        with h5py.File(self.filename, 'w') as f:
            d = f.create_dataset('data', (3, 3), dtype='i4',
                                 chunks=True, maxshape=(None, 3))
            d[:] = 1

        dd = HDF5(self.filename, '/data', mode='a')

        known = {'chunks': True,
                 'maxshape': (None, 3),
                 'compression': None}
        attrs = dd.attributes()
        assert attrs['chunks']
        self.assertEquals(attrs['maxshape'], (None, 3))
        assert not attrs['compression']

        self.assertEquals(str(dd.dshape), 'var * 3 * int32')

        print(dd.as_py())
        self.assertEqual(dd.as_py(), [[1, 1, 1], [1, 1, 1], [1, 1, 1]])

    def test_extend_chunks(self):
        stdout.flush()
        with h5py.File(self.filename, 'w') as f:
            d = f.create_dataset('data', (3, 3), dtype='i4',
                                 chunks=True, maxshape=(None, 3))
            d[:] = 1

        dd = HDF5(self.filename, '/data', mode='a')

        chunks = [nd.array([[1, 2, 3]], dtype='1 * 3 * int32'),
                  nd.array([[4, 5, 6]], dtype='1 * 3 * int32')]

        dd.extend_chunks(chunks)

        result = dd.as_dynd()[-2:, :]
        expected = nd.array([[1, 2, 3],
                             [4, 5, 6]], dtype='strided * strided * int32')

        self.assertEquals(nd.as_py(result), nd.as_py(expected))

    def test_chunks(self):
        stdout.flush()
        with h5py.File(self.filename, 'w') as f:
            d = f.create_dataset('data', (3, 3), dtype='i8')
            d[:] = 1
        dd = HDF5(self.filename, '/data')
        assert all(isinstance(chunk, nd.array) for chunk in dd.chunks())

    @skip("This runs fine in isolation, segfaults in full test")
    def test_extend(self):
        dd = HDF5(self.filename, '/data', 'a', schema='2 * int32')
        dd.extend([(1, 1), (2, 2)])

        results = list(dd)

        self.assertEquals(nd.as_py(results[0]), [1, 1])
        self.assertEquals(nd.as_py(results[1]), [2, 2])

    @skip("This runs fine in isolation, segfaults in full test")
    def test_schema(self):
        dd = HDF5(self.filename, '/data', 'a', schema='2 * int32')

        self.assertEquals(str(dd.schema), '2 * int32')
        self.assertEquals(str(dd.dshape), 'var * 2 * int32')

    @skip("This runs fine in isolation, segfaults in full test")
    def test_dshape(self):
        dd = HDF5(self.filename, '/data', 'a', dshape='var * 2 * int32')

        self.assertEquals(str(dd.schema), '2 * int32')
        self.assertEquals(str(dd.dshape), 'var * 2 * int32')

    @skip("This runs fine in isolation, segfaults in full test")
    def test_setitem(self):
        dd = HDF5(self.filename, 'data', 'a', dshape='2 * 2 * 2 * int')
        dd[:] = 1
        dd[0, 0, :] = 2
        self.assertEqual(nd.as_py(dd.as_dynd()), [[[2, 2], [1, 1]],
                                                  [[1, 1], [1, 1]]])

########NEW FILE########
__FILENAME__ = test_integrative
import gzip
import json
from functools import partial
from unittest import TestCase
from datashape import Var

from blaze.data import *
from blaze.utils import filetexts

data = {'a.json': {u'name': u'Alice', u'amount': 100},
        'b.json': {u'name': u'Bob', u'amount': 200},
        'c.json': {u'name': u'Charlie', u'amount': 50}}

texts = dict((fn, json.dumps(val)) for fn, val in data.items())

dshape = '{name: string, amount: int}'

class Test_Integrative(TestCase):
    def test_gzip_json_files(self):
        with filetexts(texts, open=gzip.open) as filenames:
            dd = Files(sorted(filenames),
                       JSON,
                       open=gzip.open,
                       subdshape=dshape)

            self.assertEqual(sorted(dd), sorted(data.values()))

            self.assertEqual(dd.dshape, Var() * dshape)

########NEW FILE########
__FILENAME__ = test_interactions
from blaze.data import CSV, JSON_Streaming, HDF5, SQL, copy
from blaze.utils import filetext, tmpfile
import json
import unittest
from blaze.py2help import skip
from sqlalchemy import create_engine


class SingleTestClass(unittest.TestCase):
    def test_csv_json(self):
        with filetext('1,1\n2,2\n') as csv_fn:
            with filetext('') as json_fn:
                schema = '2 * int'
                csv = CSV(csv_fn, schema=schema)
                json = JSON_Streaming(json_fn, mode='r+', schema=schema)

                json.extend(csv)

                self.assertEquals(list(json), [[1, 1], [2, 2]])


    def test_json_csv_structured(self):
        data = [{'x': 1, 'y': 1}, {'x': 2, 'y': 2}]
        text = '\n'.join(map(json.dumps, data))
        schema = '{x: int, y: int}'

        with filetext(text) as json_fn:
            with filetext('') as csv_fn:
                js = JSON_Streaming(json_fn, schema=schema)
                csv = CSV(csv_fn, mode='r+', schema=schema)

                csv.extend(js)

                self.assertEquals(list(csv),
                                  [{'x': 1, 'y': 1}, {'x': 2, 'y': 2}])


    def test_csv_json_chunked(self):
        with filetext('1,1\n2,2\n') as csv_fn:
            with filetext('') as json_fn:
                schema = '2 * int'
                csv = CSV(csv_fn, schema=schema)
                json = JSON_Streaming(json_fn, mode='r+', schema=schema)

                copy(csv, json)

                self.assertEquals(list(json), [[1, 1], [2, 2]])


    def test_json_csv_chunked(self):
        data = [{'x': 1, 'y': 1}, {'x': 2, 'y': 2}]
        text = '\n'.join(map(json.dumps, data))
        schema = '{x: int, y: int}'

        with filetext(text) as json_fn:
            with filetext('') as csv_fn:
                js = JSON_Streaming(json_fn, schema=schema)
                csv = CSV(csv_fn, mode='r+', schema=schema)

                copy(js, csv)

                self.assertEquals(list(csv), data)

    def test_hdf5_csv(self):
        import h5py
        with tmpfile('hdf5') as hdf5_fn:
            with filetext('') as csv_fn:
                with h5py.File(hdf5_fn, 'w') as f:
                    d = f.create_dataset('data', (3, 3), dtype='i8')
                    d[:] = 1

                csv = CSV(csv_fn, mode='r+', schema='3 * int')
                hdf5 = HDF5(hdf5_fn, '/data')

                copy(hdf5, csv)

                self.assertEquals(list(csv), [[1, 1, 1], [1, 1, 1], [1, 1, 1]])

    def test_csv_sql_json(self):
        data = [('Alice', 100), ('Bob', 200)]
        text = '\n'.join(','.join(map(str, row)) for row in data)
        schema = '{name: string, amount: int}'
        engine = create_engine('sqlite:///:memory:')
        with filetext(text) as csv_fn:
            with filetext('') as json_fn:

                csv = CSV(csv_fn, mode='r', schema=schema)
                sql = SQL(engine, 'testtable', schema=schema)
                json = JSON_Streaming(json_fn, mode='r+', schema=schema)

                copy(csv, sql)

                self.assertEqual(list(sql), data)

                copy(sql, json)

                with open(json_fn) as f:
                    assert 'Alice' in f.read()

    @skip("This runs fine in isolation, segfaults in full test")
    def test_csv_hdf5(self):
        import h5py
        from dynd import nd
        with tmpfile('hdf5') as hdf5_fn:
            with filetext('1,1\n2,2\n') as csv_fn:
                csv = CSV(csv_fn, schema='2 * int')
                hdf5 = HDF5(hdf5_fn, '/data', mode='a', schema='2 * int')

                copy(csv, hdf5)

                self.assertEquals(nd.as_py(hdf5.as_dynd()),
                                  [[1, 1], [2, 2]])

########NEW FILE########
__FILENAME__ = test_json
from __future__ import absolute_import, division, print_function

import unittest
import os
import tempfile
import json
from dynd import nd
import datashape
from blaze.datadescriptor.as_py import ddesc_as_py

from blaze.data import JSON, JSON_Streaming
from blaze.utils import filetext, raises

# TODO: This isn't actually being used!

class TestBigJSON(unittest.TestCase):
    maxDiff = None
    data = {
        "type": "ImageCollection",
        "images": [{
               "Width":  800,
                "Height": 600,
                "Title":  "View from 15th Floor",
                "Thumbnail": {
                    "Url":    "http://www.example.com/image/481989943",
                    "Height": 125,
                    "Width":  "100"
                },
                "IDs": [116, 943, 234, 38793]
            }]
    }

    dshape = """{
      type: string,
      images: var * {
            Width: int16,
            Height: int16,
            Title: string,
            Thumbnail: {
                Url: string,
                Height: int16,
                Width: int16,
            },
            IDs: var * int32,
        }
    }
    """

    def setUp(self):
        self.filename= tempfile.mktemp(".json")
        with open(self.filename, "w") as f:
            json.dump(self.data, f)

    def tearDown(self):
        os.remove(self.filename)

    def test_basic(self):
        dd = JSON(self.filename, 'r', dshape=self.dshape)
        self.assertEqual(list(dd),
                         [nd.as_py(nd.parse_json(self.dshape,
                             json.dumps(self.data)))])

    def test_as_py(self):
        dd = JSON(self.filename, 'r', dshape=self.dshape)
        self.assertEqual(dd.as_py(), self.data)


json_buf = u"[1, 2, 3, 4, 5]"
json_dshape = "var * int8"


class TestJSON(unittest.TestCase):

    def setUp(self):
        handle, self.json_file = tempfile.mkstemp(".json")
        with os.fdopen(handle, "w") as f:
            f.write(json_buf)

    def tearDown(self):
        os.remove(self.json_file)

    def test_raise_error_on_non_existent_file(self):
        self.assertRaises(ValueError,
                    lambda: JSON('does-not-exist23424.josn', 'r'))

    def test_basic_object_type(self):
        dd = JSON(self.json_file, dshape=json_dshape)
        self.assertEqual(list(dd), [1, 2, 3, 4, 5])

    def test_iter(self):
        dd = JSON(self.json_file, dshape=json_dshape)
        # This equality does not work yet
        # self.assertEqual(dd.dshape, datashape.dshape(
        #     'Var, %s' % json_schema))
        print(list(dd))
        self.assertEqual(list(dd), [1, 2, 3, 4, 5])

class Test_StreamingTransfer(unittest.TestCase):

    data = [{'name': 'Alice', 'amount': 100},
            {'name': 'Alice', 'amount': 50},
            {'name': 'Bob', 'amount': 10},
            {'name': 'Charlie', 'amount': 200},
            {'name': 'Bob', 'amount': 100}]

    text = '\n'.join(map(json.dumps, data))

    schema = '{name: string, amount: int32}'

    def test_init(self):
        with filetext(self.text) as fn:
            dd = JSON_Streaming(fn, schema=self.schema)
            self.assertEquals(list(dd), self.data)
            assert dd.dshape in set((
                datashape.dshape('var * {name: string, amount: int32}'),
                datashape.dshape('5 * {name: string, amount: int32}')))


    def test_chunks(self):
        with filetext(self.text) as fn:
            dd = JSON_Streaming(fn, schema=self.schema)
            chunks = list(dd.chunks(blen=2))
            assert isinstance(chunks[0], nd.array)
            self.assertEquals(len(chunks), 3)
            self.assertEquals(nd.as_py(chunks[0]), self.data[:2])


    def test_append(self):
        with filetext('') as fn:
            dd = JSON_Streaming(fn, mode='w', schema=self.schema)
            dd.extend([self.data[0]])
            with open(fn) as f:
                self.assertEquals(json.loads(f.read().strip()), self.data[0])

            self.assertRaises(ValueError, lambda : dd.extend([5.5]))
            self.assertRaises(ValueError,
                              lambda : dd.extend([{'name': 5, 'amount': 1.3}]))

    def test_extend(self):
        with filetext('') as fn:
            dd = JSON_Streaming(fn, mode='r+', schema=self.schema)
            dd.extend(self.data)

            self.assertEquals(list(dd), self.data)

    def test_getitem(self):
        with filetext(self.text) as fn:
            dd = JSON_Streaming(fn, mode='r', schema=self.schema)
            assert dd[0] == self.data[0]
            assert dd[2:4] == self.data[2:4]

    def test_as_dynd(self):
        with filetext(self.text) as fn:
            dd = JSON_Streaming(fn, mode='r', schema=self.schema)
            assert nd.as_py(dd.as_dynd()) == self.data

    def test_as_py(self):
        with filetext(self.text) as fn:
            dd = JSON_Streaming(fn, mode='r', schema=self.schema)
            assert dd.as_py() == self.data

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_open
from blaze.data import CSV, JSON

from blaze.utils import tmpfile, raises

import gzip

def test_gzopen_csv():
    with tmpfile('.csv.gz') as filename:
        with gzip.open(filename, 'w') as f:
            f.write('1,1\n2,2')

        # Not a valid CSV file
        assert raises(Exception, lambda: list(CSV(filename, schema='2 * int')))

        dd = CSV(filename, schema='2 * int', open=gzip.open)

        assert list(dd) == [[1, 1], [2, 2]]


def test_gzopen_json():
    with tmpfile('.json.gz') as filename:
        with gzip.open(filename, 'w') as f:
            f.write('[[1, 1], [2, 2]]')

        # Not a valid JSON file
        assert raises(Exception, lambda: list(JSON(filename, schema='2 * int')))

        dd = JSON(filename, schema='2 * int', open=gzip.open)

        assert list(dd) == [[1, 1], [2, 2]]

########NEW FILE########
__FILENAME__ = test_python
from blaze.data.python import *
from dynd import nd

def test_basic():
    data = [[1, 1], [2, 2]]
    dd = Python([], schema='2 * int32')

    dd.extend(data)

    assert str(dd.dshape) == 'var * 2 * int32'
    assert str(dd.schema) == '2 * int32'

    assert list(dd) == data
    assert dd.as_py() == data

    chunks = list(dd.chunks())

    assert all(isinstance(chunk, nd.array) for chunk in chunks)
    assert nd.as_py(chunks[0]) == data

    assert isinstance(dd.as_dynd(), nd.array)

########NEW FILE########
__FILENAME__ = test_sql
from sqlalchemy import create_engine
from dynd import nd
import unittest

from blaze.data import SQL
from blaze.utils import raises
from datashape import dshape


class SingleTestClass(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:', echo=True)

    def tearDown(self):
        pass
        # How do I clean up an engine?

    def test_setup_with_uri(self):
        dd = SQL('sqlite:///:memory:',
                 'accounts',
                 schema='{name: string, amount: int}')

    def test_can_connect(self):
        with self.engine.connect() as conn:
            assert not conn.closed
        assert conn.closed

    def test_table_creation(self):
        dd = SQL(self.engine, 'testtable',
                              schema='{name: string, amount: int}',
                              primary_key='name')
        assert self.engine.has_table('testtable')


        assert dd.table.columns.get('name').primary_key
        assert not dd.table.columns.get('amount').primary_key
        assert dd.dshape == dshape('var * {name: string, amount: int}')

        assert raises(ValueError, lambda: SQL(self.engine, 'testtable2'))


    def test_extension(self):
        dd = SQL(self.engine, 'testtable2',
                               schema='{name: string, amount: int32}',
                               primary_key='name')

        data_list = [('Alice', 100), ('Bob', 50)]
        data_dict = [{'name': name, 'amount': amount} for name, amount in data_list]

        dd.extend(data_dict)

        with self.engine.connect() as conn:
            results = conn.execute('select * from testtable2')
            self.assertEquals(list(results), data_list)


        assert list(iter(dd)) == data_list or list(iter(dd)) == data_dict
        assert dd.as_py() == data_list or dd.as_py() == data_dict


    def test_chunks(self):
        schema = '{name: string, amount: int32}'
        dd = SQL(self.engine, 'testtable3',
                              schema=schema,
                              primary_key='name')

        data_list = [('Alice', 100), ('Bob', 50), ('Charlie', 200)]
        data_dict = [{'name': name, 'amount': amount} for name, amount in data_list]
        chunk = nd.array(data_list, dtype=str(dd.dshape))

        dd.extend_chunks([chunk])

        assert list(iter(dd)) == data_list or list(iter(dd)) == data_dict

        self.assertEquals(len(list(dd.chunks(blen=2))), 2)

########NEW FILE########
__FILENAME__ = test_usability
from unittest import TestCase
import os
from tempfile import mktemp
import gzip

from blaze.utils import filetext, filetexts, tmpfile
from blaze.data import *
from blaze.py2help import skip

class TestResource(TestCase):
    def setUp(self):
        self.filename = mktemp()

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_resource_csv(self):
        with filetext('1,1\n2,2', extension='.csv') as fn:
            dd = resource(fn, schema='2 * int')
            assert isinstance(dd, CSV)
            self.assertEqual(list(dd), [[1, 1], [2, 2]])

    def test_resource_json(self):
        with filetext('[[1,1], [2,2]]', extension='.json') as fn:
            dd = resource(fn, schema='2 * int')
            assert isinstance(dd, JSON)
            self.assertEqual(list(dd), [[1, 1], [2, 2]])

    def test_resource_gz(self):
        with filetext('1,1\n2,2', extension='.csv.gz', open=gzip.open) as fn:
            dd = resource(fn, schema='2 * int')
            assert isinstance(dd, CSV)
            self.assertEqual(dd.open, gzip.open)
            self.assertEqual(list(dd), [[1, 1], [2, 2]])

    def test_filesystem(self):
        d = {'a.csv': '1,1\n2,2', 'b.csv': '1,1\n2,2'}
        with filetexts(d) as filenames:
            dd = resource('*.csv', schema='2 * int')
            assert isinstance(dd, Files)

    def test_sql(self):
        assert isinstance(resource('sqlite:///:memory:::tablename',
                                   schema='{x: int, y: int}'),
                          SQL)

    @skip("This runs fine in isolation, segfaults in full test")
    def test_hdf5(self):
        with tmpfile('.hdf5') as filename:
            assert isinstance(resource(filename + '::/path/to/data/',
                                        mode='w', schema='2 * int'),
                              HDF5)

class TestCopy(TestCase):
    def test_copy(self):
        with filetext('1,1\n2,2', extension='.csv') as a:
            with tmpfile(extension='.csv') as b:
                A = resource(a, schema='2 * int')
                B = resource(b, schema='2 * int', mode='a')
                copy(A, B)
                assert list(B) == [[1, 1], [2, 2]]

########NEW FILE########
__FILENAME__ = usability
from __future__ import absolute_import, division, print_function

from functools import partial
from .csv import *
from .json import *
from .hdf5 import *
from .filesystem import *
from .sql import *
from glob import glob
import gzip
from ..compatibility import urlopen
from ..py2help import _strtypes

__all__ = ['resource', 'copy']

filetypes = {'csv': CSV,
             'tsv': CSV,
             'json': JSON,
             'h5': HDF5,
             'hdf5': HDF5}

opens = {'http': urlopen,
         'https': urlopen,
        #'ssh': paramiko.open?
         }

def resource(uri, **kwargs):
    """ Get data resource from universal resource indicator

    Supports the following logic:

    *   Infer data format based on the file extension (.csv, .json. .hdf5)
    *   Use ``gzip.open`` if files end in ``.gz`` extension (csv, json only)
    *   Use ``urlopen`` if web protocols detected (http, https)
    *   Use SQL if text ``sql`` found in protocol string

    URI may be in any of the following forms

    >>> uri = '/path/to/data.csv'                     # csv, json, etc...
    >>> uri = '/path/to/data.json.gz'                 # handles gzip
    >>> uri = '/path/to/*/many*/data.*.json'          # glob string - many files
    >>> uri = '/path/to/data.hdf5::/path/within/hdf5' # HDF5 path :: datapath
    >>> uri = 'postgresql://sqlalchemy.uri::tablename'# SQLAlchemy :: tablename
    >>> uri = 'http://api.domain.com/data.json'       # Web requests

    Note that this follows standard ``protocol://path`` syntax.  In cases where
    more information is needed, such as an HDF5 datapath or a SQL table name
    the additional information follows two colons `::` as in the following

        /path/to/data.hdf5::/datapath
    """
    descriptor = None
    args = []

    if '::' in uri:
        uri, datapath = uri.rsplit('::')
        args.insert(0, datapath)

    extensions = uri.split('.')
    if extensions[-1] == 'gz':
        kwargs['open'] = kwargs.get('open', gzip.open)
        extensions.pop()
    descriptor = filetypes.get(extensions[-1], None)

    if '://' in uri:
        protocol, _ = uri.split('://')
        if protocol in opens:
            kwargs['open'] = kwargs.get('open', opens[protocol])
        if 'sql' in protocol:
            descriptor = SQL

    try:
        filenames = glob(uri)
    except:
        filenames = []
    if len(filenames) > 1:
        args = [partial(descriptor, *args)]  # pack sub descriptor into args
        descriptor = Files

    if descriptor:
        return descriptor(uri, *args, **kwargs)

    raise ValueError('Unknown resource type\n\t%s' % uri)


def copy(src, dest, **kwargs):
    """ Copy content from one data descriptor to another """
    dest.extend_chunks(src.chunks(**kwargs))

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import, division, print_function

from dynd import nd


def validate(schema, item):
    try:
        nd.array(item, dtype=str(schema))
        return True
    except:
        return False


def coerce(schema, item):
    return nd.as_py(nd.array(item, dtype=str(schema)))


def coerce_record_to_row(schema, rec):
    """

    >>> from datashape import dshape

    >>> schema = dshape('{x: int, y: int}')
    >>> coerce_record_to_row(schema, {'x': 1, 'y': 2})
    [1, 2]
    """
    return [rec[name] for name in schema[0].names]


def coerce_row_to_dict(schema, row):
    """

    >>> from datashape import dshape

    >>> schema = dshape('{x: int, y: int}')
    >>> coerce_row_to_dict(schema, (1, 2)) # doctest: +SKIP
    {'x': 1, 'y': 2}
    """
    return dict((name, item) for name, item in zip(schema[0].names, row))

########NEW FILE########
__FILENAME__ = as_py
from __future__ import absolute_import, division, print_function

from dynd import nd, ndt

from .data_descriptor import DDesc
from .blz_data_descriptor import BLZ_DDesc


def ddesc_as_py(ddesc):
    """
    Converts the data in a data descriptor into Python
    types. This uses the data_descriptor iteration methods,
    so is not expected to be fast. Its main initial purpose
    is to assist with writing unit tests.
    """
    # TODO: This function should probably be removed.
    if not isinstance(ddesc, DDesc):
        raise TypeError('expected DDesc instance, got %r' % type(ddesc))

    if isinstance(ddesc, BLZ_DDesc):
        return [ddesc_as_py(child_ddesc) for child_ddesc in ddesc]

    if ddesc.capabilities.deferred:
        from blaze import Array, eval
        ddesc = eval(Array(ddesc)).ddesc
    return nd.as_py(ddesc.dynd_arr())

########NEW FILE########
__FILENAME__ = blz_data_descriptor
from __future__ import absolute_import, division, print_function

import numpy as np
import blz
from dynd import nd
import datashape

from . import DDesc, Capabilities
from .dynd_data_descriptor import DyND_DDesc
from .stream_data_descriptor import Stream_DDesc
from shutil import rmtree


class BLZ_DDesc(DDesc):
    """
    A Blaze data descriptor which exposes a BLZ array.
    """
    def __init__(self, path=None, mode='r', **kwargs):
        self.path = path
        self.mode = mode
        self.kwargs = kwargs
        if isinstance(path, (blz.barray, blz.btable)):
            self.blzarr = path
            self.path = path.rootdir
        elif mode != 'w':
            self.blzarr = blz.open(rootdir=path, mode=mode, **kwargs)
        else:
            # This will be set in the constructor later on
            self.blzarr = None

    @property
    def dshape(self):
        # This cannot be cached because the BLZ can change the dshape
        obj = self.blzarr
        return datashape.from_numpy(obj.shape, obj.dtype)

    @property
    def capabilities(self):
        """The capabilities for the BLZ arrays."""
        if self.blzarr is None:
            persistent = False
        else:
            persistent = self.blzarr.rootdir is not None
        if isinstance(self.blzarr, blz.btable):
            queryable = True
        else:
            queryable = False
        return Capabilities(
            # BLZ arrays can be updated
            immutable = False,
            # BLZ arrays are concrete
            deferred = False,
            # BLZ arrays can be either persistent of in-memory
            persistent = persistent,
            # BLZ arrays can be appended efficiently
            appendable = True,
            # BLZ btables can be queried efficiently
            queryable = queryable,
            remote = False,
            )

    def __array__(self):
        return np.array(self.blzarr)

    def __len__(self):
        # BLZ arrays are never scalars
        return len(self.blzarr)

    def __getitem__(self, key):
        blzarr = self.blzarr
        # The returned arrays are temporary buffers,
        # so must be flagged as readonly.
        return DyND_DDesc(nd.asarray(blzarr[key], access='readonly'))

    def __setitem__(self, key, value):
        # We decided that BLZ should be read and append only
        raise NotImplementedError

    def __iter__(self):
        dset = self.blzarr
        # Get rid of the leading dimension on which we iterate
        dshape = datashape.from_numpy(dset.shape[1:], dset.dtype)
        for el in self.blzarr:
            yield DyND_DDesc(nd.array(el, type=str(dshape)))

    def where(self, condition, user_dict=None):
        """Iterate over values fulfilling a condition."""
        dset = self.blzarr
        # Get rid of the leading dimension on which we iterate
        dshape = datashape.from_numpy(dset.shape[1:], dset.dtype)
        for el in dset.where(condition):
            yield DyND_DDesc(nd.array(el, type=str(dshape)))

    def iterchunks(self, blen=None, start=None, stop=None):
        """Return chunks of size `blen` (in leading dimension).

        Parameters
        ----------
        blen : int
            The length, in rows, of the buffers that are returned.
        start : int
            Where the iterator starts.  The default is to start at the
            beginning.
        stop : int
            Where the iterator stops. The default is to stop at the end.

        Returns
        -------
        out : iterable
            This iterable returns buffers as NumPy arays of
            homogeneous or structured types, depending on whether
            `self.original` is a barray or a btable object.

        See Also
        --------
        wherechunks

        """
        # Return the iterable
        return blz.iterblocks(self.blzarr, blen, start, stop)

    def wherechunks(self, expression, blen=None, outfields=None, limit=None,
                    skip=0):
        """Return chunks fulfilling `expression`.

        Iterate over the rows that fullfill the `expression` condition
        on Table `self.original` in blocks of size `blen`.

        Parameters
        ----------
        expression : string or barray
            A boolean Numexpr expression or a boolean barray.
        blen : int
            The length of the block that is returned.  The default is the
            chunklen, or for a btable, the minimum of the different column
            chunklens.
        outfields : list of strings or string
            The list of column names that you want to get back in results.
            Alternatively, it can be specified as a string such as 'f0 f1' or
            'f0, f1'.  If None, all the columns are returned.
        limit : int
            A maximum number of elements to return.  The default is return
            everything.
        skip : int
            An initial number of elements to skip.  The default is 0.

        Returns
        -------
        out : iterable
            This iterable returns buffers as NumPy arrays made of
            structured types (or homogeneous ones in case `outfields` is a
            single field.

        See Also
        --------
        iterchunks

        """
        # Return the iterable
        return blz.whereblocks(self.blzarr, expression, blen, outfields,
                               limit, skip)


    def getattr(self, name):
        if isinstance(self.blzarr, blz.btable):
            return DyND_DDesc(nd.asarray(self.blzarr[name], access='readonly'))
        else:
            raise IndexError("not a btable BLZ dataset")

    # This is not part of the DDesc interface itself, but can
    # be handy for other situations not requering full compliance with
    # it.
    def append(self, values):
        """Append a list of values."""
        shape, dtype = datashape.to_numpy(self.dshape)
        values_arr = np.array(values, dtype=dtype)
        shape_vals = values_arr.shape
        if len(shape_vals) < len(shape):
            shape_vals = (1,) + shape_vals
        if len(shape_vals) != len(shape):
            raise ValueError("shape of values is not compatible")
        # Now, do the actual append
        self.blzarr.append(values_arr.reshape(shape_vals))
        self.blzarr.flush()

    def remove(self):
        """Remove the persistent storage."""
        if self.capabilities.persistent:
            rmtree(self.path)

########NEW FILE########
__FILENAME__ = cat_data_descriptor
from __future__ import absolute_import, division, print_function

import operator
import bisect

from . import DDesc, Capabilities


def cat_descriptor_iter(ddlist):
    for i, dd in enumerate(ddlist):
        for el in dd:
            yield el


class Cat_DDesc(DDesc):
    """
    A Blaze data descriptor which concatenates a list
    of data descriptors, all of which have the same
    dshape after the first dimension.

    This presently doesn't support leading dimensions
    whose size is unknown (i.e. streaming dimensions).
    """
    def __init__(self, ddlist):
        if len(ddlist) <= 1:
            raise ValueError('Need at least 2 data descriptors to concatenate')
        for dd in ddlist:
            if not isinstance(dd, DDesc):
                raise ValueError('Provided ddlist has an element '
                                'which is not a data descriptor')
        self._ddlist = ddlist
        self._dshape = ds.cat_dshapes([dd.dshape for dd in ddlist])
        self._ndim = len(self._dshape[:]) - 1
        # Create a list of boundary indices
        boundary_index = [0]
        for dd in ddlist:
            dim_size = operator.index(dd.dshape[0])
            boundary_index.append(dim_size + boundary_index[-1])
        self._boundary_index = boundary_index

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the cat data descriptor."""
        return Capabilities(
            immutable = True,
            deferred = True,
            # persistency is not supported yet
            persistent = False,
            appendable = False,
            remote = False,
            )

    def __len__(self):
        return self._boundary_index[-1]

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            key = (key,)
        # Just integer indices (no slices) for now
        boundary_index = self._boundary_index
        dim_size = boundary_index[-1]
        # TODO: Handle a slice in key[0] too!
        idx0 = operator.index(key[0])
        # Determine which data descriptor in the list to use
        if idx0 >= 0:
            if idx0 >= dim_size:
                raise IndexError(('Index %d is out of range '
                                'in dimension sized %d') % (idx0, dim_size))
        else:
            if idx0 < -dim_size:
                raise IndexError(('Index %d is out of range '
                                'in dimension sized %d') % (idx0, dim_size))
            idx0 += dim_size
        i = bisect.bisect_right(boundary_index, idx0) - 1
        # Call the i-th data descriptor to get the result
        return self._ddlist[i][(idx0 - boundary_index[i],) + key[1:]]

    def __iter__(self):
        return cat_descriptor_iter(self._ddlist)

########NEW FILE########
__FILENAME__ = csv_data_descriptor
from __future__ import absolute_import, division, print_function

import csv
import itertools as it
import os

import datashape
from dynd import nd

from .. import py2help
from .data_descriptor import DDesc, Capabilities
from .dynd_data_descriptor import DyND_DDesc


def open_file(path, mode, has_header):
    """Return a file handler positionated at the first valid line."""
    csvfile = open(path, mode=mode)
    if has_header:
        csvfile.readline()
    return csvfile


def csv_descriptor_iter(filename, mode, has_header, schema, dialect={}):
    with open_file(filename, mode, has_header) as csvfile:
        for row in csv.reader(csvfile, **dialect):
            yield DyND_DDesc(nd.array(row, dtype=schema))


def csv_descriptor_iterchunks(filename, mode, has_header, schema,
                              blen, dialect={}, start=None, stop=None):
    rows = []
    with open_file(filename, mode, has_header) as csvfile:
        for nrow, row in enumerate(csv.reader(csvfile, **dialect)):
            if start is not None and nrow < start:
                continue
            if stop is not None and nrow >= stop:
                if rows != []:
                    # Build the descriptor for the data we have and return
                    yield DyND_DDesc(nd.array(rows, dtype=schema))
                return
            rows.append(row)
            if nrow % blen == 0:
                print("rows:", rows, schema)
                yield DyND_DDesc(nd.array(rows, dtype=schema))
                rows = []


class CSV_DDesc(DDesc):
    """
    A Blaze data descriptor which exposes a CSV file.

    Parameters
    ----------
    path : string
        A path string for the CSV file.
    schema : string or datashape
        A datashape (or its string representation) of the schema
        in the CSV file.
    dialect : string or csv.Dialect instance
        The dialect as understood by the `csv` module in Python standard
        library.  If not specified, a value is guessed.
    has_header : boolean
        Whether the CSV file has a header or not.  If not specified a value
        is guessed.
    """

    def __init__(self, path, mode='r', schema=None, dialect=None,
            has_header=None, **kwargs):
        if os.path.isfile(path) is not True:
            raise ValueError('CSV file "%s" does not exist' % path)
        self.path = path
        self.mode = mode
        csvfile = open(path, mode=self.mode)

        # Handle Schema
        if isinstance(schema, py2help._strtypes):
            schema = datashape.dshape(schema)
        if isinstance(schema, datashape.DataShape) and len(schema) == 1:
            schema = schema[0]
        if not isinstance(schema, datashape.Record):
            raise TypeError(
                'schema cannot be converted into a blaze record dshape')
        self.schema = str(schema)

        # Handle Dialect
        if dialect is None:
            # Guess the dialect
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(csvfile.read(1024))
            except:
                # Cannot guess dialect.  Assume Excel.
                dialect = csv.get_dialect('excel')
            csvfile.seek(0)
        else:
            dialect = csv.get_dialect(dialect)
        self.dialect = dict((key, getattr(dialect, key))
                            for key in dir(dialect) if not key.startswith('_'))

        # Update dialect with any keyword arguments passed in
        # E.g. allow user to override with delimiter=','
        for k, v in kwargs.items():
            if k in self.dialect:
                self.dialect[k] = v

        # Handle Header
        if has_header is None:
            # Guess whether the file has a header or not
            sniffer = csv.Sniffer()
            csvfile.seek(0)
            sample = csvfile.read(1024)
            self.has_header = sniffer.has_header(sample)
        else:
            self.has_header = has_header

        csvfile.close()

    @property
    def dshape(self):
        return datashape.DataShape(datashape.Var(), self.schema)

    @property
    def capabilities(self):
        """The capabilities for the csv data descriptor."""
        return Capabilities(
            # csv datadescriptor cannot be updated
            immutable = False,
            # csv datadescriptors are concrete
            deferred = False,
            # csv datadescriptor is persistent
            persistent = True,
            # csv datadescriptor can be appended efficiently
            appendable = True,
            remote = False,
            )

    def dynd_arr(self):
        # Positionate at the beginning of the file
        with open_file(self.path, self.mode, self.has_header) as csvfile:
            return nd.array(csv.reader(csvfile, **self.dialect), dtype=self.schema)


    def __array__(self):
        return nd.as_numpy(self.dynd_arr())

    def __len__(self):
        # We don't know how many rows we have
        return None

    def __getitem__(self, key):
        with open_file(self.path, self.mode, self.has_header) as csvfile:
            if isinstance(key, py2help._inttypes):
                start, stop, step = key, key + 1, 1
            elif isinstance(key, slice):
                start, stop, step = key.start, key.stop, key.step
            else:
                raise IndexError("key '%r' is not valid" % key)
            read_iter = it.islice(csv.reader(csvfile, **self.dialect),
                                  start, stop, step)
            res = nd.array(read_iter, dtype=self.schema)
        return DyND_DDesc(res)

    def __setitem__(self, key, value):
        # CSV files cannot be updated (at least, not efficiently)
        raise NotImplementedError

    def __iter__(self):
        return csv_descriptor_iter(
            self.path, self.mode, self.has_header, self.schema, self.dialect)

    def append(self, row):
        """Append a row of values (in sequence form)."""
        values = nd.array(row, dtype=self.schema)  # validate row
        with open_file(self.path, self.mode, self.has_header) as csvfile:
            csvfile.seek(0, os.SEEK_END)  # go to the end of the file
            delimiter = self.dialect['delimiter']
            csvfile.write(delimiter.join(py2help.unicode(v) for v in row)+'\n')

    def iterchunks(self, blen=None, start=None, stop=None):
        """Return chunks of size `blen` (in leading dimension).

        Parameters
        ----------
        blen : int
            The length, in rows, of the buffers that are returned.
        start : int
            Where the iterator starts.  The default is to start at the
            beginning.
        stop : int
            Where the iterator stops. The default is to stop at the end.

        Returns
        -------
        out : iterable
            This iterable returns buffers as DyND arrays,

        """
        # Return the iterable
        return csv_descriptor_iterchunks(
            self.path, self.mode, self.has_header,
            self.schema, blen, self.dialect, start, stop)

    def remove(self):
        """Remove the persistent storage."""
        os.unlink(self.path)

########NEW FILE########
__FILENAME__ = data_descriptor
from __future__ import absolute_import, division, print_function

__all__ = ['DDesc', 'Capabilities']

import abc

from blaze.error import StreamingDimensionError
from blaze.compute.strategy import CKERNEL


class Capabilities:
    """
    A container for storing the different capabilities of the data descriptor.

    Parameters
    ----------
    immutable : bool
        True if the array cannot be updated/enlarged.
    deferred : bool
        True if the array is an expression of other arrays.
    stream : bool
        True if the array is just a wrapper over an iterator.
    persistent : bool
        True if the array persists on files between sessions.
    appendable : bool
        True if the array can be enlarged efficiently.
    queryable : bool
        True if the array can be queried efficiently.
    remote : bool
        True if the array is remote or distributed.

    """

    def __init__(self, immutable=False, deferred=False, stream=False,
                 persistent=False, appendable=False, queryable=False,
                 remote=False):
        self._caps = ['immutable', 'deferred', 'stream', 'persistent',
                      'appendable', 'queryable', 'remote']
        self.immutable = immutable
        self.deferred = deferred
        self.stream = stream
        self.persistent = persistent
        self.appendable = appendable
        self.queryable = queryable
        self.remote = remote

    def __str__(self):
        caps = [attr+': '+str(getattr(self, attr)) for attr in self._caps]
        return "capabilities:" + "\n".join(caps)


class DDesc:
    """
    The Blaze data descriptor is an interface which exposes
    data to Blaze. The data descriptor doesn't implement math
    or any other kind of functions, its sole purpose is providing
    single and multi-dimensional data to Blaze via a data shape,
    and the indexing/iteration interfaces.

    Indexing and python iteration must always return data descriptors,
    this is the python interface to the data. A summary of the
    data access patterns for a data descriptor dd, in the
    0.3 version of blaze are:

     - descriptor integer indexing
            child_dd = dd[i, j, k]
     - slice indexing
            child_dd = dd[i:j]
     - descriptor outer/leading dimension iteration
            for child_dd in dd: do_something(child_dd)
     - memory access via dynd array (either using dynd library
       to process, or directly depending on the ABI of the dynd
       array object, which will be stabilized prior to dynd 1.0)

    The descriptor-based indexing methods operate only through the
    Python interface, JIT-compiled access should be done through
    processing the dynd type and corresponding array metadata.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def dshape(self):
        """
        Returns the datashape for the data behind this datadescriptor.
        Every data descriptor implementation must provide a dshape.
        """
        # TODO: Does dshape make sense for a data descriptor? A data descriptor
        # may have a lower-level concept of a data type that corresponds to a
        # higher-level data shape. IMHO dshape should be on Array only
        raise NotImplementedError

    @abc.abstractproperty
    def capabilities(self):
        """A container for the different capabilities."""
        raise NotImplementedError

    def __len__(self):
        """
        The default implementation of __len__ is for the
        behavior of a streaming dimension, where the size
        of the dimension isn't known ahead of time.

        If a data descriptor knows its dimension size,
        it should implement __len__, and provide the size
        as an integer.
        """
        raise StreamingDimensionError('Cannot get the length of'
                                      ' a streaming dimension')


    @abc.abstractmethod
    def __iter__(self):
        """
        This returns an iterator/generator which iterates over
        the outermost/leading dimension of the data. If the
        dimension is not also a stream, __len__ should also
        be implemented. The iterator must return data
        descriptors.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def __getitem__(self, key):
        """
        This does integer/slice indexing, producing another
        data descriptor.
        """
        raise NotImplementedError

    #@abc.abstractmethod   # XXX should be there
    def append(self, values):
        """
        This allows appending values in the data descriptor.
        """
        return NotImplementedError

    def getattr(self, name):
        raise NotImplementedError('this data descriptor does not support attribute access')

    def dynd_arr(self):
        """Concrete data descriptors must provide their array data
           as a dynd array, accessible via this method.
        """
        if not self.capabilities.deferred:
            raise NotImplementedError((
                'Data descriptor of type %s claims '
                'claims to not being deferred, but did not '
                'override dynd_arr()') % type(self))
        else:
            raise TypeError((
                'Data descriptor of type %s is deferred') % type(self))

########NEW FILE########
__FILENAME__ = deferred_data_descriptor
"""
Deferred data descriptor for deferred expressions. This is backed up by an
actual deferred expression graph.
"""

from __future__ import absolute_import, division, print_function

import blaze

from . import DDesc, Capabilities

#------------------------------------------------------------------------
# Decorators
#------------------------------------------------------------------------

def force_evaluation(methname):
    """
    Wrap a method and make it force evaluation when called and dispatch the
    call to the resulting Array.
    """
    def method(self, *args, **kwargs):
        result = blaze.eval(blaze.Array(self))
        self._result = result
        method = getattr(result.ddesc, methname)
        return method(*args, **kwargs)

    return method

#------------------------------------------------------------------------
# Data Descriptor
#------------------------------------------------------------------------

# TODO: Re-purpose this to work for general deferred computations, not just
#       those backed up by the expression graph of Blaze kernels

class Deferred_DDesc(DDesc):
    """
    Data descriptor for arrays backed up by a deferred expression graph.

    Attributes:
    -----------
    dshape: DataShape
        Intermediate type resolved as far as it can be typed over the
        sub-expressions

    expr  : (Op, ExprContext)
        The expression graph along with the expression context, see blaze.expr
    """

    def __init__(self, dshape, expr):
        self._dshape = dshape
        self.expr = expr

        # Result of evaluation (cached)
        self._result = None

    @property
    def inputs(self):
        graph, ctx = self.expr
        return [term for term in ctx.terms.values()
                         if isinstance(term, blaze.Array)]

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the deferred data descriptor."""
        return Capabilities(
            immutable = True,
            deferred = True,
            # persistency is not supported yet
            persistent = False,
            appendable = False,
            remote = False,
            )

    __array__           = force_evaluation('__array__')
    __iter__            = force_evaluation('__iter__')
    __getitem__         = force_evaluation('__getitem__')
    __len__             = force_evaluation('__len__')

########NEW FILE########
__FILENAME__ = dynd_data_descriptor
from __future__ import absolute_import, division, print_function

from datashape import dshape
from dynd import nd

from . import Capabilities
from .data_descriptor import DDesc


def dynd_descriptor_iter(dyndarr):
    for el in dyndarr:
        yield DyND_DDesc(el)


class DyND_DDesc(DDesc):
    """
    A Blaze data descriptor which exposes a DyND array.
    """
    def __init__(self, dyndarr):
        if not isinstance(dyndarr, nd.array):
            raise TypeError('object is not a dynd array, has type %s' %
                            type(dyndarr))
        self._dyndarr = dyndarr
        self._dshape = dshape(nd.dshape_of(dyndarr))

    def dynd_arr(self):
        return self._dyndarr

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the dynd data descriptor."""
        return Capabilities(
            # whether dynd arrays can be updated
            immutable = self._dyndarr.access_flags == 'immutable',
            # dynd arrays are concrete
            deferred = False,
            # dynd arrays can be either persistent of in-memory
            persistent = False,
            # dynd arrays can be appended efficiently
            appendable = False,
            remote = False,
            )

    def __array__(self):
        return nd.as_numpy(self.dynd_arr())

    def __len__(self):
        return len(self._dyndarr)

    def __getitem__(self, key):
        return DyND_DDesc(self._dyndarr[key])

    def __setitem__(self, key, value):
        # TODO: This is a horrible hack, we need to specify item setting
        #       via well-defined interfaces, not punt to another system.
        self._dyndarr.__setitem__(key, value)

    def __iter__(self):
        return dynd_descriptor_iter(self._dyndarr)

    def getattr(self, name):
        return DyND_DDesc(getattr(self._dyndarr, name))

########NEW FILE########
__FILENAME__ = hdf5_data_descriptor
from __future__ import absolute_import, division, print_function

import os
import numpy as np
from dynd import nd
import datashape

from . import DDesc, Capabilities
from .dynd_data_descriptor import DyND_DDesc
from .stream_data_descriptor import Stream_DDesc
from ..optional_packages import tables_is_here
if tables_is_here:
    import tables as tb



class HDF5_DDesc(DDesc):
    """
    A Blaze data descriptor which exposes a HDF5 dataset.
    """

    def __init__(self, path, datapath, mode='r', filters=None):
        self.path = path
        self.datapath = datapath
        self.mode = mode
        self.filters = filters

    @property
    def dshape(self):
        # This cannot be cached because the Array can change the dshape
        with tb.open_file(self.path, mode='r') as f:
            dset = f.get_node(self.datapath)
            odshape = datashape.from_numpy(dset.shape, dset.dtype)
        return odshape

    @property
    def capabilities(self):
        """The capabilities for the HDF5 arrays."""
        with tb.open_file(self.path, mode='r') as f:
            dset = f.get_node(self.datapath)
            appendable = isinstance(dset, (tb.EArray, tb.Table))
            queryable = isinstance(dset, (tb.Table,))
        caps = Capabilities(
            # HDF5 arrays can be updated
            immutable = False,
            # HDF5 arrays are concrete
            deferred = False,
            # HDF5 arrays are persistent
            persistent = True,
            # HDF5 arrays can be appended efficiently (EArrays and Tables)
            appendable = appendable,
            # PyTables Tables can be queried efficiently
            queryable = queryable,
            remote = False,
            )
        return caps

    def dynd_arr(self):
        # Positionate at the beginning of the file
        with tb.open_file(self.path, mode='r') as f:
            dset = f.get_node(self.datapath)
            dset = nd.array(dset[:], dtype=dset.dtype)
        return dset

    def __array__(self):
        with tb.open_file(self.path, mode='r') as f:
            dset = f.get_node(self.datapath)
            dset = dset[:]
        return dset

    def __len__(self):
        with tb.open_file(self.path, mode='r') as f:
            dset = f.get_node(self.datapath)
            arrlen = len(dset)
        return arrlen

    def __getitem__(self, key):
        with tb.open_file(self.path, mode='r') as f:
            dset = f.get_node(self.datapath)
            # The returned arrays are temporary buffers,
            # so must be flagged as readonly.
            dyndarr = nd.asarray(dset[key], access='readonly')
        return DyND_DDesc(dyndarr)

    def __setitem__(self, key, value):
        # HDF5 arrays can be updated
        with tb.open_file(self.path, mode=self.mode) as f:
            dset = f.get_node(self.datapath)
            dset[key] = value

    def __iter__(self):
        f = tb.open_file(self.path, mode='r')
        dset = f.get_node(self.datapath)
        # Get rid of the leading dimension on which we iterate
        dshape = datashape.from_numpy(dset.shape[1:], dset.dtype)
        for el in dset:
            if hasattr(el, "nrow"):
                yield DyND_DDesc(nd.array(el[:], type=str(dshape)))
            else:
                yield DyND_DDesc(nd.array(el, type=str(dshape)))
        dset._v_file.close()

    def where(self, condition):
        """Iterate over values fulfilling a condition."""
        f = tb.open_file(self.path, mode='r')
        dset = f.get_node(self.datapath)
        # Get rid of the leading dimension on which we iterate
        dshape = datashape.from_numpy(dset.shape[1:], dset.dtype)
        for el in dset.where(condition):
            yield DyND_DDesc(nd.array(el[:], type=str(dshape)))
        dset._v_file.close()

    def getattr(self, name):
        with tb.open_file(self.path, mode=self.mode) as f:
            dset = f.get_node(self.datapath)
            if hasattr(dset, 'cols'):
                return DyND_DDesc(
                    nd.asarray(getattr(dset.cols, name)[:],
                               access='readonly'))
            else:
                raise IndexError("not an HDF5 compound dataset")

    def append(self, values):
        """Append a list of values."""
        shape, dtype = datashape.to_numpy(self.dshape)
        values_arr = np.array(values, dtype=dtype)
        shape_vals = values_arr.shape
        if len(shape_vals) < len(shape):
            shape_vals = (1,) + shape_vals
        if len(shape_vals) != len(shape):
            raise ValueError("shape of values is not compatible")
        # Now, do the actual append
        with tb.open_file(self.path, mode=self.mode) as f:
            dset = f.get_node(self.datapath)
            dset.append(values_arr.reshape(shape_vals))

    def remove(self):
        """Remove the persistent storage."""
        os.unlink(self.path)

########NEW FILE########
__FILENAME__ = json_data_descriptor
from __future__ import absolute_import, division, print_function

import os

import datashape

from .data_descriptor import DDesc
from .. import py2help
from dynd import nd
from .dynd_data_descriptor import DyND_DDesc, Capabilities


def json_descriptor_iter(array):
    for row in array:
        yield DyND_DDesc(row)


class JSON_DDesc(DDesc):
    """
    A Blaze data descriptor which exposes a JSON file.

    Parameters
    ----------
    path : string
        A path string for the JSON file.
    schema : string or datashape
        A datashape (or its string representation) of the schema
        in the JSON file.
    """
    def __init__(self, path, mode='r', **kwargs):
        if os.path.isfile(path) is not True:
            raise ValueError('JSON file "%s" does not exist' % path)
        self.path = path
        self.mode = mode
        schema = kwargs.get("schema", None)
        if type(schema) in py2help._strtypes:
            schema = datashape.dshape(schema)
        self.schema = str(schema)
        # Initially the array is not loaded (is this necessary?)
        self._cache_arr = None

    @property
    def dshape(self):
        return datashape.dshape(self.schema)

    @property
    def capabilities(self):
        """The capabilities for the json data descriptor."""
        return Capabilities(
            # json datadescriptor cannot be updated
            immutable = False,
            # json datadescriptors are concrete
            deferred = False,
            # json datadescriptor is persistent
            persistent = True,
            # json datadescriptor can be appended efficiently
            appendable = True,
            remote = False,
            )

    @property
    def _arr_cache(self):
        if self._cache_arr is not None:
            return self._cache_arr
        with open(self.path, mode=self.mode) as jsonfile:
            # This will read everything in-memory (but a memmap approach
            # is in the works)
            self._cache_arr = nd.parse_json(
                self.schema, jsonfile.read())
        return self._cache_arr

    def dynd_arr(self):
        return self._arr_cache

    def __array__(self):
        return nd.as_numpy(self.dynd_arr())

    def __len__(self):
        # Not clear to me what the length of a json object should be
        return None

    def __getitem__(self, key):
        return DyND_DDesc(self._arr_cache[key])

    def __setitem__(self, key, value):
        # JSON files cannot be updated (at least, not efficiently)
        raise NotImplementedError

    def __iter__(self):
        return json_descriptor_iter(self._arr_cache)

    def remove(self):
        """Remove the persistent storage."""
        os.unlink(self.path)

########NEW FILE########
__FILENAME__ = membuf_data_descriptor
from __future__ import absolute_import, division, print_function

import ctypes

from dynd import ndt, _lowlevel
import datashape

from .dynd_data_descriptor import DyND_DDesc


def data_descriptor_from_ctypes(cdata, writable):
    """
    Parameters
    ----------
    cdata : ctypes data instance
        The ctypes data object which owns the data.
    writable : bool
        Should be true if the data is writable, flase
        if it's read-only.
    """
    ds = datashape.from_ctypes(type(cdata))
    access = "readwrite" if writable else "readonly"
    dyndtp = ' * '.join(['cfixed[%d]' % int(x) for x in ds[:-1]] + [str(ds[-1])])
    dyndarr = _lowlevel.array_from_ptr(ndt.type(dyndtp),
                    ctypes.addressof(cdata), cdata,
                    access)
    return DyND_DDesc(dyndarr)


def data_descriptor_from_cffi(ffi, cdata, writable):
    """
    Parameters
    ----------
    ffi : cffi.FFI
        The cffi namespace which contains the cdata.
    cdata : cffi.CData
        The cffi data object which owns the data.
    writable : bool
        Should be true if the data is writable, flase
        if it's read-only.
    """
    if not isinstance(cdata, ffi.CData):
        raise TypeError('object is not a cffi.CData object, has type %s' %
                        type(cdata))
    owner = (ffi, cdata)
    # Get the raw pointer out of the cdata as an integer
    ptr = int(ffi.cast('uintptr_t', ffi.cast('char *', cdata)))
    ds = datashape.from_cffi(ffi, ffi.typeof(cdata))
    if (isinstance(ds, datashape.DataShape) and
            isinstance(ds[0], datashape.TypeVar)):
        # If the outermost dimension is an array without fixed
        # size, get its size from the data
        ds = datashape.DataShape(*(datashape.Fixed(len(cdata)),) + ds[1:])
    access = "readwrite" if writable else "readonly"
    dyndtp = ' * '.join(['cfixed[%d]' % int(x) for x in ds[:-1]] + [str(ds[-1])])
    dyndarr = _lowlevel.array_from_ptr(ndt.type(dyndtp), ptr, owner, access)
    return DyND_DDesc(dyndarr)


########NEW FILE########
__FILENAME__ = netcdf4_data_descriptor
from __future__ import absolute_import, division, print_function

import os
import numpy as np
from dynd import nd
import datashape

from . import DDesc, Capabilities
from .dynd_data_descriptor import DyND_DDesc
from .stream_data_descriptor import Stream_DDesc
from ..optional_packages import netCDF4_is_here
if netCDF4_is_here:
    import netCDF4


def get_node(f, dp):
    """Get a node in `f` file/group with a `dp` datapath (can be nested)."""
    if dp.startswith('/'): dp = dp[1:]
    idx = dp.find('/')
    if idx >= 0:
        group = f.groups[dp[:idx]]
        return get_node(group, dp[idx+1:])
    return f.variables[dp]

class netCDF4_DDesc(DDesc):
    """
    A Blaze data descriptor which exposes a netCDF4 dataset.
    """

    def __init__(self, path, datapath, mode='r'):
        self.path = path
        self.datapath = datapath
        self.mode = mode

    @property
    def dshape(self):
        # This cannot be cached because the Array can change the dshape
        with netCDF4.Dataset(self.path, mode='r') as f:
            dset = get_node(f, self.datapath)
            odshape = datashape.from_numpy(dset.shape, dset.dtype)
        return odshape

    @property
    def capabilities(self):
        """The capabilities for the netCDF4 arrays."""
        with netCDF4.Dataset(self.path, mode='r') as f:
            dset = get_node(f, self.datapath)
            appendable = isinstance(dset, netCDF4.Variable)
        caps = Capabilities(
            # netCDF4 arrays can be updated
            immutable = False,
            # netCDF4 arrays are concrete
            deferred = False,
            # netCDF4 arrays are persistent
            persistent = True,
            # netCDF4 arrays can be appended efficiently
            appendable = appendable,
            # netCDF4 arrays cannot be queried efficiently
            queryable = False,
            remote = False,
            )
        return caps

    def dynd_arr(self):
        # Positionate at the beginning of the file
        with netCDF4.Dataset(self.path, mode='r') as f:
            dset = get_node(f, self.datapath)
            dset = nd.array(dset[:], dtype=dset.dtype)
        return dset

    def __array__(self):
        with netCDF4.Dataset(self.path, mode='r') as f:
            dset = get_node(f, self.datapath)
            dset = dset[:]
        return dset

    def __len__(self):
        with netCDF4.Dataset(self.path, mode='r') as f:
            dset = get_node(f, self.datapath)
            arrlen = len(dset)
        return arrlen

    def __getitem__(self, key):
        with netCDF4.Dataset(self.path, mode='r') as f:
            dset = get_node(f, self.datapath)
            # The returned arrays are temporary buffers,
            # so must be flagged as readonly.
            dyndarr = nd.asarray(dset[key], access='readonly')
        return DyND_DDesc(dyndarr)

    def __setitem__(self, key, value):
        # netCDF4 arrays can be updated
        with netCDF4.Dataset(self.path, mode=self.mode) as f:
            dset = get_node(f, self.datapath)
            dset[key] = value

    def __iter__(self):
        f = netCDF4.Dataset(self.path, mode='r')
        dset = get_node(f, self.datapath)
        # Get rid of the leading dimension on which we iterate
        dshape = datashape.from_numpy(dset.shape[1:], dset.dtype)
        for el in dset:
            if hasattr(el, "nrow"):
                yield DyND_DDesc(nd.array(el[:], type=str(dshape)))
            else:
                yield DyND_DDesc(nd.array(el, type=str(dshape)))
        f.close()

    def getattr(self, name):
        with netCDF4.Dataset(self.path, mode=self.mode) as f:
            dset = get_node(f, self.datapath)
            if hasattr(dset, 'cols'):
                return DyND_DDesc(
                    nd.asarray(getattr(dset.cols, name)[:],
                               access='readonly'))
            else:
                raise IndexError("not an netCDF4 compound dataset")

    def append(self, values):
        """Append a list of values."""
        with netCDF4.Dataset(self.path, mode=self.mode) as f:
            dset = get_node(f, self.datapath)
            dset[len(dset):] = values

    def remove(self):
        """Remove the persistent storage."""
        os.unlink(self.path)

########NEW FILE########
__FILENAME__ = remote_data_descriptor
from __future__ import absolute_import, division, print_function

import datashape
from ..catalog.blaze_url import add_indexers_to_url
from .data_descriptor import DDesc, Capabilities
from dynd import nd, ndt


class Remote_DDesc(DDesc):
    """
    A Blaze data descriptor which exposes an array on another
    server.
    """

    def __init__(self, url, dshape=None):
        from ..io.client import requests
        self.url = url
        if dshape is None:
            self._dshape = datashape.dshape(requests.get_remote_datashape(url))
        else:
            self._dshape = datashape.dshape(dshape)

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the remote data descriptor."""
        return Capabilities(
            # treat remote arrays as immutable (maybe not?)
            immutable = True,
            # TODO: not sure what to say here
            deferred = False,
            # persistent on the remote server
            persistent = True,
            appendable = False,
            remote = True,
            )

    def __repr__(self):
        return 'Remote_DDesc(%r, dshape=%r)' % (self.url, self.dshape)

    def dynd_arr(self):
        from ..io.client import requests
        """Downloads the data and returns a local in-memory nd.array"""
        # TODO: Need binary serialization
        j = requests.get_remote_json(self.url)
        tp = ndt.type(str(self.dshape))
        return nd.parse_json(tp, j)

    def __len__(self):
        ds = self.dshape
        if isinstance(ds, datashape.DataShape):
            ds = ds[-1]
            if isinstance(ds, datashape.Fixed):
                return int(ds)
        raise AttributeError('the datashape (%s) of this data descriptor has no length' % ds)

    def __getitem__(self, key):
        return Remote_DDesc(add_indexers_to_url(self.url, (key,)))

    def getattr(self, name):
        ds = self.dshape
        if isinstance(ds, datashape.DataShape):
            ds = ds[-1]
        if isinstance(ds, datashape.Record) and name in ds.names:
            return Remote_DDesc(self.url + '.' + name)
        else:
            raise AttributeError(('Blaze remote array does not ' +
                                  'have attribute "%s"') % name)

    def __iter__(self):
        raise NotImplementedError('remote data descriptor iterator unimplemented')

########NEW FILE########
__FILENAME__ = stream_data_descriptor
"""
Deferred data descriptor for deferred expressions. This is backed up by an
actual deferred expression graph.
"""

from __future__ import absolute_import, division, print_function

import blaze
import datashape

from . import DDesc, Capabilities
from .dynd_data_descriptor import DyND_DDesc
from dynd import nd

#------------------------------------------------------------------------
# Data Descriptor
#------------------------------------------------------------------------

class Stream_DDesc(DDesc):
    """
    Data descriptor for arrays exposing mainly an iterator interface.

    Attributes:
    -----------
    dshape: datashape.dshape
        The datashape of the stream data descriptor.

    condition: string
        The condtion over the original array, in string form.
    """

    def __init__(self, iterator, dshape, condition):
        self._iterator = iterator
        # The length of the iterator is unknown, so we put 'var' here
        self._dshape = datashape.dshape("var * " + str(dshape.measure))
        #
        self.condition = condition

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the deferred data descriptor."""
        return Capabilities(
            immutable = True,
            deferred = False,
            stream = True,
            # persistency is not supported yet
            persistent = False,
            appendable = False,
            remote = False,
            )

    def __getitem__(self, key):
        """Streams do not support random seeks.
        """
        raise NotImplementedError

    def __iter__(self):
        return self._iterator

    def _printer(self):
        return "<Array(iter('%s'), '%s')>" % (self.condition, self.dshape,)

    def _printer_repr(self):
        return self._printer()

########NEW FILE########
__FILENAME__ = test_cffi_membuf_data_descriptor
from __future__ import absolute_import, division, print_function

import unittest

from blaze.py2help import skipIf
from blaze.datadescriptor import data_descriptor_from_cffi, ddesc_as_py

from datashape import dshape

try:
    import cffi
    ffi = cffi.FFI()
except ImportError:
    cffi = None


class TestCFFIMemBuf_DDesc(unittest.TestCase):
    @skipIf(cffi is None, 'cffi is not installed')
    def test_scalar(self):
        a = ffi.new('int *', 3)
        dd = data_descriptor_from_cffi(ffi, a, writable=True)
        self.assertEqual(dd.dshape, dshape('int32'))
        self.assertEqual(ddesc_as_py(dd), 3)
        self.assertTrue(isinstance(ddesc_as_py(dd), int))

        a = ffi.new('float *', 3.25)
        dd = data_descriptor_from_cffi(ffi, a, writable=True)
        self.assertEqual(dd.dshape, dshape('float32'))
        self.assertEqual(ddesc_as_py(dd), 3.25)
        self.assertTrue(isinstance(ddesc_as_py(dd), float))

    @skipIf(cffi is None, 'cffi is not installed')
    def test_1d_array(self):
        # An array where the size is in the type
        a = ffi.new('short[32]', [2*i for i in range(32)])
        dd = data_descriptor_from_cffi(ffi, a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * int16'))
        self.assertEqual(ddesc_as_py(dd), [2*i for i in range(32)])

        # An array where the size is not in the type
        a = ffi.new('double[]', [1.5*i for i in range(32)])
        dd = data_descriptor_from_cffi(ffi, a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * float64'))
        self.assertEqual(ddesc_as_py(dd), [1.5*i for i in range(32)])

    @skipIf(cffi is None, 'cffi is not installed')
    def test_2d_array(self):
        # An array where the leading array size is in the type
        vals = [[2**i + j for i in range(35)] for j in range(32)]
        a = ffi.new('long long[32][35]', vals)
        dd = data_descriptor_from_cffi(ffi, a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * 35 * int64'))
        self.assertEqual(ddesc_as_py(dd), vals)

        # An array where the leading array size is not in the type
        vals = [[a + b*2 for a in range(35)] for b in range(32)]
        a = ffi.new('unsigned char[][35]', vals)
        dd = data_descriptor_from_cffi(ffi, a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * 35 * uint8'))
        self.assertEqual(ddesc_as_py(dd), vals)

    @skipIf(cffi is None, 'cffi is not installed')
    def test_3d_array(self):
        # Simple 3D array
        vals = [[[(i + 2*j + 3*k)
                        for i in range(10)]
                        for j in range(12)]
                        for k in range(14)]
        a = ffi.new('unsigned int[14][12][10]', vals)
        dd = data_descriptor_from_cffi(ffi, a, writable=True)
        self.assertEqual(dd.dshape, dshape('14 * 12 * 10 * uint32'))
        self.assertEqual(ddesc_as_py(dd), vals)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_csv_data_descriptor
from __future__ import absolute_import, division, print_function

import unittest
import tempfile
import os
import csv

import datashape

from blaze.datadescriptor import (
    CSV_DDesc, DyND_DDesc, DDesc, ddesc_as_py)


def sanitize(lines):
    return '\n'.join(line.strip() for line in lines.split('\n'))


class TestCSV_DDesc_dialect(unittest.TestCase):

    buf = sanitize(
    u"""Name Amount
        Alice 100
        Bob 200
        Alice 50
    """)

    schema = "{ f0: string, f1: int }"

    def setUp(self):
        handle, self.csv_file = tempfile.mkstemp(".csv")
        with os.fdopen(handle, "w") as f:
            f.write(self.buf)

    def tearDown(self):
        os.remove(self.csv_file)

    def test_overwrite_delimiter(self):
        dd = CSV_DDesc(self.csv_file, dialect='excel', schema=self.schema,
                delimiter=' ')
        assert dd.dialect['delimiter'] == ' '

    def test_content(self):
        dd = CSV_DDesc(self.csv_file, dialect='excel', schema=self.schema,
                delimiter=' ')
        print(ddesc_as_py(dd))
        s = str(ddesc_as_py(dd))
        assert 'Alice' in s and 'Bob' in s


class TestCSV_DDesc(unittest.TestCase):

    # A CSV toy example
    buf = sanitize(
    u"""k1,v1,1,False
        k2,v2,2,True
        k3,v3,3,False
    """)
    schema = "{ f0: string, f1: string, f2: int16, f3: bool }"

    def setUp(self):
        handle, self.csv_file = tempfile.mkstemp(".csv")
        with os.fdopen(handle, "w") as f:
            f.write(self.buf)

    def tearDown(self):
        os.remove(self.csv_file)

    def test_basic_object_type(self):
        self.assertTrue(issubclass(CSV_DDesc, DDesc))
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        self.assertTrue(isinstance(dd, DDesc))
        self.assertTrue(isinstance(dd.dshape.shape[0], datashape.Var))
        self.assertEqual(ddesc_as_py(dd), [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_iter(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)

        # Iteration should produce DyND_DDesc instances
        vals = []
        for el in dd:
            self.assertTrue(isinstance(el, DyND_DDesc))
            self.assertTrue(isinstance(el, DDesc))
            vals.append(ddesc_as_py(el))
        self.assertEqual(vals, [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_iterchunks(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)

        # Iteration should produce DyND_DDesc instances
        vals = []
        for el in dd.iterchunks(blen=2):
            self.assertTrue(isinstance(el, DyND_DDesc))
            self.assertTrue(isinstance(el, DDesc))
            vals.extend(ddesc_as_py(el))
        self.assertEqual(vals, [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_iterchunks_start(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        vals = []
        for el in dd.iterchunks(blen=2, start=1):
            vals.extend(ddesc_as_py(el))
        self.assertEqual(vals, [
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_iterchunks_stop(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        vals = [ddesc_as_py(v) for v in dd.iterchunks(blen=1, stop=2)]
        self.assertEqual(vals, [
            [{u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False}],
            [{u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True}]])

    def test_iterchunks_start_stop(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        vals = [ddesc_as_py(v) for v in dd.iterchunks(blen=1, start=1, stop=2)]
        self.assertEqual(vals, [[
            {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True}]])

    def test_append(self):
        # Get a private file so as to not mess the original one
        handle, csv_file = tempfile.mkstemp(".csv")
        with os.fdopen(handle, "w") as f:
            f.write(self.buf)
        dd = CSV_DDesc(csv_file, schema=self.schema, mode='r+')
        dd.append(["k4", "v4", 4, True])
        vals = [ddesc_as_py(v) for v in dd.iterchunks(blen=1, start=3)]
        self.assertEqual(vals, [[
            {u'f0': u'k4', u'f1': u'v4', u'f2': 4, u'f3': True}]])
        os.remove(csv_file)

    def test_getitem_start(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        el = dd[0]
        self.assertTrue(isinstance(el, DyND_DDesc))
        vals = ddesc_as_py(el)
        self.assertEqual(vals, [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False}])

    def test_getitem_stop(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        el = dd[:1]
        self.assertTrue(isinstance(el, DyND_DDesc))
        vals = ddesc_as_py(el)
        self.assertEqual(vals, [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False}])

    def test_getitem_step(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        el = dd[::2]
        self.assertTrue(isinstance(el, DyND_DDesc))
        vals = ddesc_as_py(el)
        self.assertEqual(vals, [
            {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
            {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}])

    def test_getitem_start_step(self):
        dd = CSV_DDesc(self.csv_file, schema=self.schema)
        el = dd[1::2]
        self.assertTrue(isinstance(el, DyND_DDesc))
        vals = ddesc_as_py(el)
        self.assertEqual(vals, [
        {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True}])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_ctypes_membuf_data_descriptor
from __future__ import absolute_import, division, print_function

import unittest
import ctypes

from datashape import dshape

from blaze.datadescriptor import data_descriptor_from_ctypes, ddesc_as_py


class TestCTypesMemBuf_DDesc(unittest.TestCase):
    def test_scalar(self):
        a = ctypes.c_int(3)
        dd = data_descriptor_from_ctypes(a, writable=True)
        self.assertEqual(dd.dshape, dshape('int32'))
        self.assertEqual(ddesc_as_py(dd), 3)
        self.assertTrue(isinstance(ddesc_as_py(dd), int))

        a = ctypes.c_float(3.25)
        dd = data_descriptor_from_ctypes(a, writable=True)
        self.assertEqual(dd.dshape, dshape('float32'))
        self.assertEqual(ddesc_as_py(dd), 3.25)
        self.assertTrue(isinstance(ddesc_as_py(dd), float))

    def test_1d_array(self):
        a = (ctypes.c_short * 32)()
        for i in range(32):
            a[i] = 2*i
        dd = data_descriptor_from_ctypes(a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * int16'))
        self.assertEqual(ddesc_as_py(dd), [2*i for i in range(32)])

        a = (ctypes.c_double * 32)()
        for i in range(32):
            a[i] = 1.5*i
        dd = data_descriptor_from_ctypes(a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * float64'))
        self.assertEqual(ddesc_as_py(dd), [1.5*i for i in range(32)])

    def test_2d_array(self):
        a = (ctypes.c_double * 35 * 32)()
        vals = [[2**i + j for i in range(35)] for j in range(32)]
        for i in range(32):
            for j in range(35):
                a[i][j] = vals[i][j]
        dd = data_descriptor_from_ctypes(a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * 35 * float64'))
        self.assertEqual(ddesc_as_py(dd), vals)

        a = (ctypes.c_uint8 * 35 * 32)()
        vals = [[i + j*2 for i in range(35)] for j in range(32)]
        for i in range(32):
            for j in range(35):
                a[i][j] = vals[i][j]
        dd = data_descriptor_from_ctypes(a, writable=True)
        self.assertEqual(dd.dshape, dshape('32 * 35 * uint8'))
        self.assertEqual(ddesc_as_py(dd), vals)

    def test_3d_array(self):
        # Simple 3D array
        a = (ctypes.c_uint32 * 10 * 12 * 14)()
        vals = [[[(i + 2*j + 3*k)
                        for i in range(10)]
                        for j in range(12)]
                        for k in range(14)]
        for i in range(14):
            for j in range(12):
                for k in range(10):
                    a[i][j][k] = vals[i][j][k]
        dd = data_descriptor_from_ctypes(a, writable=True)
        self.assertEqual(dd.dshape, dshape('14 * 12 * 10 * uint32'))
        self.assertEqual(ddesc_as_py(dd), vals)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dynd_data_descriptor
from __future__ import absolute_import, division, print_function

import unittest

import datashape
from dynd import nd
from blaze.datadescriptor import DyND_DDesc, DDesc, ddesc_as_py


class TestDyND_DDesc(unittest.TestCase):
    def test_basic_object_type(self):
        self.assertTrue(issubclass(DyND_DDesc, DDesc))
        a = nd.array([[1, 2, 3], [4, 5, 6]])
        dd = DyND_DDesc(a)
        # Make sure the right type is returned
        self.assertTrue(isinstance(dd, DDesc))
        self.assertEqual(ddesc_as_py(dd), [[1, 2, 3], [4, 5, 6]])

    def test_descriptor_iter_types(self):
        a = nd.array([[1, 2, 3], [4, 5, 6]])
        dd = DyND_DDesc(a)

        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int32'))
        # Iteration should produce DyND_DDesc instances
        vals = []
        for el in dd:
            self.assertTrue(isinstance(el, DyND_DDesc))
            self.assertTrue(isinstance(el, DDesc))
            vals.append(ddesc_as_py(el))
        self.assertEqual(vals, [[1, 2, 3], [4, 5, 6]])

    def test_descriptor_getitem_types(self):
        a = nd.array([[1, 2, 3], [4, 5, 6]])
        dd = DyND_DDesc(a)

        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int32'))
        # Indexing should produce DyND_DDesc instances
        self.assertTrue(isinstance(dd[0], DyND_DDesc))
        self.assertEqual(ddesc_as_py(dd[0]), [1,2,3])
        self.assertTrue(isinstance(dd[1,2], DyND_DDesc))
        self.assertEqual(ddesc_as_py(dd[1,2]), 6)

    def test_var_dim(self):
        a = nd.array([[1, 2, 3], [4, 5], [6]])
        dd = DyND_DDesc(a)

        self.assertEqual(dd.dshape, datashape.dshape('3 * var * int32'))
        self.assertEqual(ddesc_as_py(dd), [[1, 2, 3], [4, 5], [6]])
        self.assertEqual(ddesc_as_py(dd[0]), [1, 2, 3])
        self.assertEqual(ddesc_as_py(dd[1]), [4, 5])
        self.assertEqual(ddesc_as_py(dd[2]), [6])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_hdf5_data_descriptor
from __future__ import absolute_import, division, print_function

import unittest
import tempfile
import os

import datashape
import numpy as np

from blaze.datadescriptor import (
    HDF5_DDesc, DyND_DDesc, DDesc, ddesc_as_py)
from blaze.py2help import skipIf

from blaze.optional_packages import tables_is_here
if tables_is_here:
    import tables as tb


class TestHDF5DDesc(unittest.TestCase):

    def setUp(self):
        handle, self.hdf5_file = tempfile.mkstemp(".h5")
        os.close(handle)  # close the non needed file handle
        self.a1 = np.array([[1, 2, 3], [4, 5, 6]], dtype="int32")
        self.a2 = np.array([[1, 2, 3], [3, 2, 1]], dtype="int64")
        self.t1 = np.array([(1, 2, 3), (3, 2, 1)], dtype="i4,i8,f8")
        with tb.open_file(self.hdf5_file, "w") as f:
            f.create_array(f.root, 'a1', self.a1)
            f.create_table(f.root, 't1', self.t1)
            f.create_group(f.root, 'g')
            f.create_array(f.root.g, 'a2', self.a2)

    def tearDown(self):
        os.remove(self.hdf5_file)

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_basic_object_type(self):
        self.assertTrue(issubclass(HDF5_DDesc, DDesc))
        dd = HDF5_DDesc(self.hdf5_file, '/a1')
        # Make sure the right type is returned
        self.assertTrue(isinstance(dd, DDesc))
        self.assertEqual(ddesc_as_py(dd), [[1, 2, 3], [4, 5, 6]])

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_descriptor_iter_types(self):
        dd = HDF5_DDesc(self.hdf5_file, '/a1')
        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int32'))
        # Iteration should produce DyND_DDesc instances
        vals = []
        for el in dd:
            self.assertTrue(isinstance(el, DyND_DDesc))
            self.assertTrue(isinstance(el, DDesc))
            vals.append(ddesc_as_py(el))
        self.assertEqual(vals, [[1, 2, 3], [4, 5, 6]])

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_descriptor_getitem_types(self):
        dd = HDF5_DDesc(self.hdf5_file, '/g/a2')
        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int64'))
        # Indexing should produce DyND_DDesc instances
        self.assertTrue(isinstance(dd[0], DyND_DDesc))
        self.assertEqual(ddesc_as_py(dd[0]), [1,2,3])
        self.assertTrue(isinstance(dd[1,2], DyND_DDesc))
        self.assertEqual(ddesc_as_py(dd[1,2]), 1)

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_descriptor_setitem(self):
        dd = HDF5_DDesc(self.hdf5_file, '/g/a2', mode='a')
        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int64'))
        dd[1,2] = 10
        self.assertEqual(ddesc_as_py(dd[1,2]), 10)
        dd[1] = [10, 11, 12]
        self.assertEqual(ddesc_as_py(dd[1]), [10, 11, 12])

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_descriptor_append(self):
        dd = HDF5_DDesc(self.hdf5_file, '/t1', mode='a')
        tshape = datashape.dshape(
            '2 * { f0 : int32, f1 : int64, f2 : float64 }')
        self.assertEqual(dd.dshape, tshape)
        dd.append([(10, 11, 12)])
        dvals = {'f0': 10, 'f1': 11, 'f2': 12.}
        rvals = ddesc_as_py(dd[2])
        is_equal = [(rvals[k] == dvals[k]) for k in dvals]
        self.assertEqual(is_equal, [True]*3)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_json_data_descriptor
from __future__ import absolute_import, division, print_function

import unittest
import os
import tempfile

from blaze.datadescriptor import (
    JSON_DDesc, DyND_DDesc, DDesc, ddesc_as_py)

# TODO: This isn't actually being used!
_json_buf = u"""{
    "type": "ImageCollection",
    "images": [
        "Image": {
            "Width":  800,
            "Height": 600,
            "Title":  "View from 15th Floor",
            "Thumbnail": {
                "Url":    "http://www.example.com/image/481989943",
                "Height": 125,
                "Width":  "100"
            },
            "IDs": [116, 943, 234, 38793]
        }
    ]
}
"""

# TODO: This isn't actually being used!
_json_schema = """{
  type: string,
  images: var * {
        Width: int16,
        Height: int16,
        Title: string,
        Thumbnail: {
            Url: string,
            Height: int16,
            Width: int16,
        },
        IDs: var * int32,
    };
}
"""

json_buf = u"[1, 2, 3, 4, 5]"
json_schema = "var * int8"


class TestJSON_DDesc(unittest.TestCase):

    def setUp(self):
        handle, self.json_file = tempfile.mkstemp(".json")
        with os.fdopen(handle, "w") as f:
            f.write(json_buf)

    def tearDown(self):
        os.remove(self.json_file)

    def test_basic_object_type(self):
        self.assertTrue(issubclass(JSON_DDesc, DDesc))
        dd = JSON_DDesc(self.json_file, schema=json_schema)
        self.assertTrue(isinstance(dd, DDesc))
        self.assertEqual(ddesc_as_py(dd), [1, 2, 3, 4, 5])

    def test_iter(self):
        dd = JSON_DDesc(self.json_file, schema=json_schema)
        # This equality does not work yet
        # self.assertEqual(dd.dshape, datashape.dshape(
        #     'Var, %s' % json_schema))

        # Iteration should produce DyND_DDesc instances
        vals = []
        for el in dd:
            self.assertTrue(isinstance(el, DyND_DDesc))
            self.assertTrue(isinstance(el, DDesc))
            vals.append(ddesc_as_py(el))
        self.assertEqual(vals, [1, 2, 3, 4, 5])

    def test_getitem(self):
        dd = JSON_DDesc(self.json_file, schema=json_schema)
        el = dd[1:3]
        self.assertTrue(isinstance(el, DyND_DDesc))
        vals = ddesc_as_py(el)
        self.assertEqual(vals, [2,3])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_netcdf4_data_descriptor
from __future__ import absolute_import, division, print_function

import unittest
import tempfile
import os

import datashape
import numpy as np

from blaze.datadescriptor import (
    DyND_DDesc, DDesc, ddesc_as_py)
from blaze.py2help import skipIf, skip

from blaze.optional_packages import netCDF4_is_here
if netCDF4_is_here:
    import netCDF4
    from blaze.datadescriptor import netCDF4_DDesc


class TestNetCDF4DDesc(unittest.TestCase):

    def setUp(self):
        if not netCDF4_is_here: return
        handle, self.nc4_file = tempfile.mkstemp(".nc")
        os.close(handle)  # close the non needed file handle
        self.a1 = np.array([[1, 2, 3], [4, 5, 6]], dtype="int32")
        self.a2 = np.array([[1, 2, 3], [3, 2, 1]], dtype="int64")
        self.t1 = np.array([(1, 2, 3), (3, 2, 1)], dtype="i4,i8,f8")
        with netCDF4.Dataset(self.nc4_file, "w") as f:
            lat = f.createDimension('lat', 2)
            lon = f.createDimension('lon', 3)
            a1 = f.createVariable('a1', 'i4', ('lat','lon'))
            a1[:] = self.a1
            cmpd_t = f.createCompoundType('i4,i8,f8', 'cmpd_t')
            time = f.createDimension('time', None)
            t1 = f.createVariable('t1', cmpd_t, ('time',))
            t1[:] = self.t1
            g = f.createGroup('g')
            a2 = g.createVariable('a2', 'i8', ('lat','lon'))
            a2[:] = self.a2

    def tearDown(self):
        if not netCDF4_is_here: return
        os.remove(self.nc4_file)

    #@skipIf(not netCDF4_is_here, 'netcdf4-python is not installed')
    def test_basic_object_type(self):
        # For reasons that I ignore, the above decorator is not working for
        # 2.6, so will disable the tests the hard way...
        if not netCDF4_is_here: return
        self.assertTrue(issubclass(netCDF4_DDesc, DDesc))
        dd = netCDF4_DDesc(self.nc4_file, '/a1')
        # Make sure the right type is returned
        self.assertTrue(isinstance(dd, DDesc))
        self.assertEqual(ddesc_as_py(dd), [[1, 2, 3], [4, 5, 6]])

    #@skipIf(not netCDF4_is_here, 'netcdf4-python is not installed')
    def test_descriptor_iter_types(self):
        if not netCDF4_is_here: return
        dd = netCDF4_DDesc(self.nc4_file, '/a1')
        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int32'))
        # Iteration should produce DyND_DDesc instances
        vals = []
        for el in dd:
            self.assertTrue(isinstance(el, DyND_DDesc))
            self.assertTrue(isinstance(el, DDesc))
            vals.append(ddesc_as_py(el))
        self.assertEqual(vals, [[1, 2, 3], [4, 5, 6]])

    #@skipIf(not netCDF4_is_here, 'netcdf4-python is not installed')
    def test_descriptor_getitem_types(self):
        if not netCDF4_is_here: return
        dd = netCDF4_DDesc(self.nc4_file, '/g/a2')
        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int64'))
        # Indexing should produce DyND_DDesc instances
        self.assertTrue(isinstance(dd[0], DyND_DDesc))
        self.assertEqual(ddesc_as_py(dd[0]), [1,2,3])
        self.assertTrue(isinstance(dd[1,2], DyND_DDesc))
        self.assertEqual(ddesc_as_py(dd[1,2]), 1)

    #@skipIf(not netCDF4_is_here, 'netcdf4-python is not installed')
    def test_descriptor_setitem(self):
        if not netCDF4_is_here: return
        dd = netCDF4_DDesc(self.nc4_file, '/g/a2', mode='a')
        self.assertEqual(dd.dshape, datashape.dshape('2 * 3 * int64'))
        dd[1,2] = 10
        self.assertEqual(ddesc_as_py(dd[1,2]), 10)
        dd[1] = [10, 11, 12]
        self.assertEqual(ddesc_as_py(dd[1]), [10, 11, 12])

    #@skipIf(not netCDF4_is_here, 'netcdf4-python is not installed')
    #@skip("The append segfaults sometimes")
    def test_descriptor_append(self):
        if True: return
        dd = netCDF4_DDesc(self.nc4_file, '/t1', mode='a')
        tshape = datashape.dshape(
            '2 * { f0 : int32, f1 : int64, f2 : float64 }')
        self.assertEqual(dd.dshape, tshape)
        dd.append([(10, 11, 12)])
        dvals = {'f0': 10, 'f1': 11, 'f2': 12.}
        rvals = ddesc_as_py(dd[2])
        is_equal = [(rvals[k] == dvals[k]) for k in dvals]
        self.assertEqual(is_equal, [True]*3)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = error
from __future__ import absolute_import, division, print_function

__all__ = [
    'CustomSyntaxError',
    'StreamingDimensionError',
    'BroadcastError',
    'ArrayWriteError'
]


class BlazeException(Exception):
    """Exception that all blaze exceptions derive from"""

#------------------------------------------------------------------------
# Generic Syntax Errors
#------------------------------------------------------------------------

syntax_error = """

  File {filename}, line {lineno}
    {line}
    {pointer}

{error}: {msg}
"""


class CustomSyntaxError(BlazeException):
    """
    Makes datashape parse errors look like Python SyntaxError.
    """
    def __init__(self, lexpos, filename, text, msg=None):
        self.lexpos = lexpos
        self.filename = filename
        self.text = text
        self.msg = msg or 'invalid syntax'
        self.lineno = text.count('\n', 0, lexpos) + 1
        # Get the extent of the line with the error
        linestart = text.rfind('\n', 0, lexpos)
        if linestart < 0:
            linestart = 0
        else:
            linestart += 1
        lineend = text.find('\n', lexpos)
        if lineend < 0:
            lineend = len(text)
        self.line = text[linestart:lineend]
        self.col_offset = lexpos - linestart

    def __str__(self):
        pointer = ' '*self.col_offset + '^'

        return syntax_error.format(
            filename=self.filename,
            lineno=self.lineno,
            line=self.line,
            pointer=pointer,
            msg=self.msg,
            error=self.__class__.__name__,
        )

    def __repr__(self):
        return str(self)

#------------------------------------------------------------------------
# Array-related errors
#------------------------------------------------------------------------


class StreamingDimensionError(BlazeException):
    """
    An error for when a streaming dimension is accessed
    like a dimension of known size.
    """
    pass


class BroadcastError(BlazeException):
    """
    An error for when arrays can't be broadcast together.
    """
    pass


class ArrayWriteError(BlazeException):
    """
    An error for when trying to write to an array which is read only.
    """
    pass

########NEW FILE########
__FILENAME__ = requests
from __future__ import absolute_import, division, print_function

import urllib
import json

from ... import py2help

if py2help.PY2:
    from urllib2 import urlopen
else:
    from urllib.request import urlopen

def get_remote_datashape(url):
    """Gets the datashape of a remote array URL."""
    response = urlopen(url + '?r=datashape')
    return response.read().decode('utf8')

def get_remote_json(url):
    """Gets the JSON data of a remote array URL."""
    response = urlopen(url + '?r=data.json')
    return response.read()

def create_remote_session(base_url):
    """Creates a compute session rooted on the remote array URL."""
    params = [('r', 'create_session')]
    response = urlopen(base_url, urllib.urlencode(params))
    return json.loads(response.read())

def close_remote_session(session_url):
    """Closes the remote compute session."""
    params = [('r', 'close_session')]
    response = urlopen(session_url, urllib.urlencode(params))
    return json.loads(response.read())

def add_computed_fields(session_url, url, fields, rm_fields, fnname):
    """Creates a new remote array with the added computed fields."""
    reqdata = {
            "input": str(url),
            "fields": [[str(name), str(dt), str(expr)]
                    for name, dt, expr in fields]
        }
    if len(rm_fields) > 0:
        reqdata['rm_fields'] = [str(name) for name in rm_fields]
    if fnname is not None:
        reqdata['fnname'] = str(fnname)
    params = [('r', 'add_computed_fields'),
              ('json', json.dumps(reqdata))]
    response = urlopen(session_url, urllib.urlencode(params))
    return json.loads(response.read())

def make_computed_fields(session_url, url, replace_undim, fields, fnname):
    """Creates a new remote array with the computed fields."""
    reqdata = {
            "input": str(url),
            "replace_undim": int(replace_undim),
            "fields": [[str(name), str(dt), str(expr)]
                    for name, dt, expr in fields]
        }
    if fnname is not None:
        reqdata['fnname'] = str(fnname)
    params = [('r', 'make_computed_fields'),
              ('json', json.dumps(reqdata))]
    response = urlopen(session_url, urllib.urlencode(params))
    return json.loads(response.read())

def sort(session_url, url, field):
    """Creates a new remote array which is sorted by field."""
    reqdata = {
        "input": str(url),
        "field": field
        }
    params = [('r', 'sort'),
              ('json', json.dumps(reqdata))]
    response = urlopen(session_url, urllib.urlencode(params))
    return json.loads(response.read())

def groupby(session_url, url, fields):
    reqdata = {
        "input": str(url),
        "fields": fields
        }
    params = [('r', 'groupby'),
              ('json', json.dumps(reqdata))]
    response = urlopen(session_url, urllib.urlencode(params))
    return json.loads(response.read())

########NEW FILE########
__FILENAME__ = session
from __future__ import absolute_import, division, print_function

from .requests import create_remote_session, close_remote_session, \
        add_computed_fields, make_computed_fields, sort, groupby
from .rarray import rarray


class session:
    def __init__(self, root_url):
        """
        Creates a remote Blaze compute session with the
        requested Blaze remote array as the root.
        """
        self.root_url = root_url
        j = create_remote_session(root_url)
        self.session_url = j['session']
        self.server_version = j['version']

        print('Remote Blaze session created at %s' % root_url)
        print('Remote DyND-Python version: %s' % j['dynd_python_version'])
        print('Remote DyND version: %s' % j['dynd_version'])

    def __repr__(self):
        return 'Blaze Remote Compute Session\n' + \
                        ' root url: ' + self.root_url + '\n' \
                        ' session url: ' + self.session_url + '\n' + \
                        ' server version: ' + self.server_version + '\n'

    def add_computed_fields(self, arr, fields, rm_fields=[], fnname=None):
        """
        Adds one or more new fields to a struct array.

        Each field_expr in 'fields' is a string/ast fragment
        which is called using eval, with the input fields
        in the locals and numpy/scipy in the globals.

        arr : rarray
            A remote array on the server.
        fields : list of (field_name, field_type, field_expr)
            These are the fields which are added to 'n'.
        rm_fields : list of string, optional
            For fields that are in the input, but have no expression,
            this removes them from the output struct instead of
            keeping the value.
        fnname : string, optional
            The function name, which affects how the resulting
            deferred expression dtype is printed.
        """
        j = add_computed_fields(self.session_url,
                                   arr.url, fields,
                                   rm_fields, fnname)
        return rarray(j['output'], j['dshape'])

    def make_computed_fields(self, arr, replace_undim, fields, fnname=None):
        """
        Creates an array with the requested computed fields.
        If replace_undim is positive, that many uniform dimensions
        are provided into the field expressions, so the
        result has fewer dimensions.

        arr : rarray
            A remote array on the server.
        replace_undim : integer
            The number of uniform dimensions to leave in the
            input going to the fields. For example if the
            input has shape (3,4,2) and replace_undim is 1,
            the result will have shape (3,4), and each operand
            provided to the field expression will have shape (2).
        fields : list of (field_name, field_type, field_expr)
            These are the fields which are added to 'n'.
        fnname : string, optional
            The function name, which affects how the resulting
            deferred expression dtype is printed.
        """
        j = make_computed_fields(self.session_url,
                                   arr.url, replace_undim, fields,
                                   fnname)
        return rarray(j['output'], j['dshape'])

    def sort(self, arr, field):
        j = sort(self.session_url, arr.url, field)
        return rarray(j['output'], j['dshape'])

    def groupby(self, arr, fields):
        """
        Applies a groupby to a struct array based on selected fields.

        arr : rarray
            A remote array on the server.
        fields : list of field names
            These are the fields which are used for grouping.

        Returns a tuple of the groupby result and the groups.
        """
        j = groupby(self.session_url, arr.url, fields)
        return (
            rarray(j['output_gb'], j['dshape_gb']),
            rarray(j['output_groups'], j['dshape_groups']))

    def close(self):
        close_remote_session(self.session_url)
        self.session_url = None

########NEW FILE########
__FILENAME__ = conn
"""
SciDB connection and naming interface.

TODO: instantiate this stuff from the catalog?
"""

from __future__ import absolute_import, division, print_function

#------------------------------------------------------------------------
# Connect
#------------------------------------------------------------------------

class SciDBConn(object):
    """
    Refer to an individual SciDB array.
    """

    def __init__(self, conn):
        self.conn = conn

    def query(self, query, persist=False):
        return self.conn.execute_query(query, persist=persist)

    def wrap(self, arrname):
        return self.conn.wrap_array(arrname)


def connect(uri):
    """Connect to a SciDB database"""
    from scidbpy import interface
    return SciDBConn(interface.SciDBShimInterface(uri))

########NEW FILE########
__FILENAME__ = constructors
"""
SciDB array constructors.
"""

from __future__ import absolute_import, division, print_function

import blaze
from datashape import from_numpy

from .query import Query, build
from .datatypes import scidb_dshape
from .datadescriptor import SciDB_DDesc


#------------------------------------------------------------------------
# Array creation
#------------------------------------------------------------------------
def _create(dshape, n, conn, chunk_size=1024, overlap=0):
    sdshape = scidb_dshape(dshape, chunk_size, overlap)
    query = build(sdshape, n)
    return blaze.Array(SciDB_DDesc(dshape, query, conn))


#------------------------------------------------------------------------
# Constructors
#------------------------------------------------------------------------
def empty(dshape, conn, chunk_size=1024, overlap=0):
    """Create an empty array"""
    return zeros(dshape, conn, chunk_size, overlap)


def zeros(dshape, conn, chunk_size=1024, overlap=0):
    """Create an array of zeros"""
    return _create(dshape, "0", conn, chunk_size, overlap)


def ones(dshape, conn, chunk_size=1024, overlap=0):
    """Create an array of ones"""
    return _create(dshape, "1", conn, chunk_size, overlap)


def handle(conn, arrname):
    """Obtain an array handle to an existing SciDB array"""
    scidbpy_arr = conn.wrap_array(arrname)
    dshape = from_numpy(scidbpy_arr.shape, scidbpy_arr.dtype)
    return SciDB_DDesc(dshape, Query(arrname, ()), conn)

########NEW FILE########
__FILENAME__ = datadescriptor
"""
SciDB data descriptor.
"""

from __future__ import absolute_import, division, print_function

from blaze.datadescriptor import DDesc, Capabilities


class SciDB_DDesc(DDesc):
    """
    SciDB data descriptor.
    """

    deferred = True

    def __init__(self, dshape, query, conn):
        """
        Parameters
        ----------

        query: Query
            Query object signalling the SciDB array to be referenced, or the
            (atomic) expression to construct an array.
        """
        self.query = query
        self._dshape = dshape
        self.conn = conn

    @property
    def strategy(self):
        return 'scidb'

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the scidb data descriptor."""
        return Capabilities(
            immutable = True,
            # scidb does not give us access to its temps right now
            deferred = False,
            persistent = True,
            # Not sure on whether scidb is appendable or not
            appendable = False,
            )

    # TODO: below

    def __iter__(self):
        raise NotImplementedError

    def __getitem__(self, item):
        raise NotImplementedError

    def dynd_arr(self):
        raise NotImplementedError

    def __repr__(self):
        return "SciDBDesc(%s)" % (str(self.query),)

    def __str__(self):
        arrname = str(self.query)
        sdb_array = self.conn.wrap_array(arrname)
        return str(sdb_array.toarray())

    _printer = __str__

########NEW FILE########
__FILENAME__ = datatypes
"""SciDB type conversions."""

from __future__ import absolute_import, division, print_function

from datashape import coretypes as T


def scidb_measure(measure):
    """Construct a SciDB type from a blaze measure (dtype)"""
    return measure.name  # TODO: HACK, set up a type map


def scidb_dshape(dshape, chunk_size=1024, overlap=0):
    """Construct a SciDB type from a DataShape"""
    import scidbpy
    # TODO: Validate shape regularity
    shape, dtype = T.to_numpy(dshape)
    sdshape = scidbpy.SciDBDataShape(shape, dtype,
                                     chunk_size=chunk_size,
                                     chunk_overlap=overlap)
    return sdshape.schema

########NEW FILE########
__FILENAME__ = error
"""
Errors raised by any scidb operation.
"""

from __future__ import absolute_import, division, print_function

from blaze import error

class scidberror(error.BlazeException):
    """Base exception for scidb backend related errors"""

class SciDBError(scidberror):
    """Raised when scidb complains about something."""

class InterfaceError(scidberror):
    """Raised when performing a query over different scidb interface handles"""
########NEW FILE########
__FILENAME__ = kernel
"""
Create scidb kernel implementations.
"""

from __future__ import absolute_import, division, print_function

AFL = 'AFL'
AQL = 'AQL'
SCIDB = 'scidb'

########NEW FILE########
__FILENAME__ = query
"""
SciDB query generation and execution. The query building themselves are
fairly low-level, since their only concern is whether to generate temporary
arrays or not.
"""

from __future__ import absolute_import, division, print_function

import uuid
from itertools import chain

#------------------------------------------------------------------------
# Query Interface
#------------------------------------------------------------------------

def temp_name():
    return 'arr_' + str(uuid.uuid4()).replace("-", "_")

class Query(object):
    """
    Holds an intermediate SciDB query. This builds up a little query graph
    to deal with expression reuse.

    For instance, consider the code:

        b = a * 2
        eval(b + b)

    This would generate the query "(a * 2) + (a * 2)". In this case the
    blaze expression graph itself knows about the duplication of the
    expression. However, scidb kernels may themselves reuse expressions
    multiple times, which can lead to exponential code generation.

    E.g. consider function `f(a) = a * a`. Now f(f(f(a))) has `a` 8 times.
    """

    temp_name = None

    def __init__(self, pattern, args, kwds, interpolate=str.format):
        self.pattern = pattern
        self.args = args
        self.kwds = kwds
        self.interpolate = interpolate
        self.uses = []

        for arg in chain(self.args, self.kwds.values()):
            if isinstance(arg, Query):
                arg.uses.append(self)

    def _result(self):
        """
        Format the expression.
        """
        return self.interpolate(self.pattern, *self.args, **self.kwds)

    def generate_code(self, code, cleanup, seen):
        """
        Generate a query to produce a temporary array for the expression.
        The temporary array can be referenced multiple times.
        """
        if self in seen:
            return
        seen.add(self)

        for arg in chain(self.args, self.kwds.values()):
            if isinstance(arg, Query):
                arg.generate_code(code, cleanup, seen)

        if len(self.uses) > 1:
            self.temp_name = temp_name()
            code.append("store({expr}, {temp})".format(expr=self._result(),
                                                       temp=self.temp_name))
            cleanup.append("remove({temp})".format(temp=self.temp_name))

    def result(self):
        """
        The result in the AFL expression we are building.
        """
        if len(self.uses) > 1:
            return self.temp_name
        return self._result()

    def __str__(self):
        if self.temp_name:
            return self.temp_name
        return self.result()


def qformat(s, *args, **kwds):
    return Query(s, args, kwds)

#------------------------------------------------------------------------
# Query Execution
#------------------------------------------------------------------------

def execute_query(conn, query, persist=False):
    return conn.query(query, persist=persist)

#------------------------------------------------------------------------
# Query Generation
#------------------------------------------------------------------------

def apply(name, *args):
    arglist = ["{%d}" % (i,) for i in range(len(args))]
    pattern = "{name}({arglist})".format(name=name, arglist=", ".join(arglist))
    return qformat(pattern, *args)

def expr(e):
    return qformat("({0})", expr)

def iff(expr, a, b):
    return apply("iff", expr, a, b)

def build(arr, expr):
    return apply("build", arr, expr)
########NEW FILE########
__FILENAME__ = scidb_interp
"""
SciDB query generation and execution from Blaze AIR.
"""

from __future__ import absolute_import, division, print_function


import blaze
from blaze.io.scidb import AFL
from blaze.compute.air import interp

from .error import InterfaceError
from .query import execute_query, temp_name, Query
from .datadescriptor import SciDB_DDesc


#------------------------------------------------------------------------
# Interpreter
#------------------------------------------------------------------------

def compile(func, env):
    # TODO: we can assemble a query at compile time, but we can't abstract
    # over scidb array names. Not sure this makes sense...
    return func, env

def interpret(func, env, args, persist=False, **kwds):
    # TODO: allow mixing scidb and non-scidb data...

    dshape = func.type.restype
    descs = [arg.ddesc for arg in args]
    inputs = [desc.query for desc in descs]
    conns = [desc.conn for desc in descs]

    if len(set(conns)) > 1:
        raise InterfaceError(
            "Can only perform query over one scidb interface, got multiple")

    # Assemble query
    env = {'interp.handlers' : handlers}
    query = interp.run(func, env, None, args=inputs)
    [conn] = set(conns)

    code = []
    cleanup = []
    query.generate_code(code, cleanup, set())
    expr = query.result()

    result = _execute(conn, code, cleanup, expr, persist)
    return blaze.array(SciDB_DDesc(dshape, result, conn))


def _execute(conn, code, cleanup, expr, persist):
    if code:
        for stmt in code:
            execute_query(conn, stmt, persist=False)

    temp = temp_name()
    query = "store({expr}, {temp})".format(expr=expr, temp=temp)
    execute_query(conn, query, persist)

    if cleanup:
        for stmt in cleanup:
            execute_query(conn, stmt, persist=False)

    return Query(temp, args=(), kwds={})

#------------------------------------------------------------------------
# Handlers
#------------------------------------------------------------------------

def op_kernel(interp, funcname, *args):
    op = interp.op

    function = op.metadata['kernel']
    overload = op.metadata['overload']

    py_func, signature = overload.func, overload.resolved_sig

    impl_overload = function.best_match(AFL, signature.argtypes)

    kernel = impl_overload.func
    sig    = impl_overload.resolved_sig
    assert sig == signature, (sig, signature)

    return kernel(*args)

def op_convert(interp, arg):
    raise TypeError("scidb type conversion not supported yet")

def op_ret(interp, arg):
    interp.halt()
    return arg

handlers = {
    'kernel':   op_kernel,
    'convert':  op_convert,
    'ret':      op_ret,
}

########NEW FILE########
__FILENAME__ = mock
# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

class MockedConn(object):

    def __init__(self):
        self.recorded = []

    def query(self, s, persist=False):
        self.recorded.append((s, persist))

    def wrap(self, arrname):
        raise NotImplementedError("Referencing remote scidb arrays")
########NEW FILE########
__FILENAME__ = test_scidb
from __future__ import print_function, division, absolute_import

import unittest
from datashape import dshape

from blaze import add, multiply, eval, py2help
from blaze.io.scidb import zeros, ones
from blaze.io.scidb.tests.mock import MockedConn

try:
    import scidbpy
    from scidbpy import interface, SciDBQueryError, SciDBArray
except ImportError:
    scidbpy = None


ds = dshape('10 * 10 * float64')


class TestSciDB(unittest.TestCase):

    def setUp(self):
        self.conn = MockedConn()

    @py2help.skipIf(scidbpy is None, 'scidbpy is not installed')
    def test_query(self):
        a = zeros(ds, self.conn)
        b = ones(ds, self.conn)

        expr = add(a, multiply(a, b))

        graph, ctx = expr.expr
        self.assertEqual(graph.dshape, dshape('10 * 10 * float64'))

        result = eval(expr)

        self.assertEqual(len(self.conn.recorded), 1)
        [(query, persist)] = self.conn.recorded

        query = str(query)

        self.assertIn("+", query)
        self.assertIn("*", query)
        self.assertIn("build", query)

    @py2help.skipIf(scidbpy is None, 'scidbpy is not installed')
    def test_query_exec(self):
        print("establishing connection...")
        conn = interface.SciDBShimInterface('http://192.168.56.101:8080/')
        print(conn)

        a = zeros(ds, conn)
        b = ones(ds, conn)

        expr = a + b

        graph, ctx = expr.expr
        self.assertEqual(graph.dshape, dshape('10 * 10 * float64'))

        result = eval(expr)
        print(result)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ufuncs
"""SciDB implementations element-wise ufuncs."""

from __future__ import absolute_import, division, print_function

from blaze.compute.ops import ufuncs
from blaze.compute.ops.ufuncs import not_equal, less, logical_not
from .kernel import SCIDB

from .query import apply, iff, qformat


def overload_unop_ufunc(signature, name, op):
    """Add a unary sql overload to a blaze ufunc"""
    def unop(x):
        return apply_expr(x, qformat('{op} {x}.f0', op=op, x=x))
    unop.__name__ = name
    bf = getattr(ufuncs, name)
    bf.add_plugin_overload(signature, unop, SCIDB)


def overload_binop_ufunc(signature, name, op):
    """Add a binary sql overload to a blaze ufunc"""
    def binop(a, b):
        arr = qformat("join({a}, {b})", a=a, b=b)
        expr = qformat("{a}.f0 {op} {b}.f0", a=a, op=op, b=b)
        return apply_expr(arr, expr)
    binop.__name__ = name
    bf = getattr(ufuncs, name)
    bf.add_plugin_overload(signature, binop, SCIDB)


#------------------------------------------------------------------------
# Arithmetic
#------------------------------------------------------------------------
overload_binop_ufunc("(T, T) -> T", "add", "+")
overload_binop_ufunc("(T, T) -> T", "multiply", "*")
#overload_binop_ufunc("(A : real, A) -> A", "subtract", "-")
overload_binop_ufunc("(T, T) -> T", "subtract", "-")
#overload_binop_ufunc("(A : real, A) -> A", "divide", "/")
overload_binop_ufunc("(T, T) -> T", "divide", "/")
#overload_binop_ufunc("(A : real, A) -> A", "mod", "%")
overload_binop_ufunc("(T, T) -> T", "mod", "%")

# overload_binop_ufunc("(A : real, A) -> A", "floordiv", "//")
# overload_binop_ufunc("(A : real, A) -> A", "truediv", "/")

overload_unop_ufunc("(T) -> T", "negative", "-")

#------------------------------------------------------------------------
# Compare
#------------------------------------------------------------------------
overload_binop_ufunc("(T, T) -> bool", "equal", "==")
overload_binop_ufunc("(T, T) -> bool", "not_equal", "!=")
overload_binop_ufunc("(T, T) -> bool", "less", "<")
overload_binop_ufunc("(T, T) -> bool", "greater", ">")
overload_binop_ufunc("(T, T) -> bool", "greater_equal", ">=")

#------------------------------------------------------------------------
# Logical
#------------------------------------------------------------------------
# TODO: We have to implement all combinations of types here for 'and' etc,
#       given the set {numeric, bool} for both arguments. Overloading at the
#       kernel level would reduce this. Can we decide between "kernels" and
#       "functions" depending on the inference process.

# TODO: numeric/bool and bool/numeric combinations


def logical_and(a, b):
    return iff(ibool(a). ibool(b), false)
ufuncs.logical_and.add_plugin_overload("(T, T) -> bool",
                                       logical_and, SCIDB)


def logical_and(a, b):
    return iff(a, b, false)
ufuncs.logical_and.add_plugin_overload("(bool, bool) -> bool",
                                       logical_and, SCIDB)


def logical_or(a, b):
    return iff(ibool(a), true, ibool(b))
ufuncs.logical_or.add_plugin_overload("(T, T) -> bool",
                                      logical_or, SCIDB)

def logical_or(a, b):
    return iff(a, true, b)
ufuncs.logical_or.add_plugin_overload("(bool, bool) -> bool",
                                      logical_or, SCIDB)


# Fixme: repeat of subexpression leads to exponential code generation !


def logical_xor(a, b):
    return iff(ibool(a), logical_not(ibool(b)), ibool(b))
ufuncs.logical_xor.add_plugin_overload("(T, T) -> bool",
                                       logical_xor, SCIDB)


def logical_xor(a, b):
    return iff(a, logical_not(b), b)
ufuncs.logical_xor.add_plugin_overload("(bool, bool) -> bool",
                                       logical_xor, SCIDB)


def logical_not(a):
    return apply("not", a)
ufuncs.logical_not.add_plugin_overload("(T) -> bool",
                                       logical_not, SCIDB)


#------------------------------------------------------------------------
# Math
#------------------------------------------------------------------------


def abs(x):
    # Fixme: again exponential codegen
    return iff(less(x, 0), ufuncs.negative(x), x)
ufuncs.abs.add_plugin_overload("(T) -> bool",
                                       abs, SCIDB)


#------------------------------------------------------------------------
# Helper functions
#------------------------------------------------------------------------
def ibool(x):
    return not_equal(x, "0")


def apply_expr(arr, expr):
    colname = '__blaze_col'
    query = qformat('apply({arr}, {colname}, {expr})',
                    arr=arr, colname=colname, expr=expr)
    return project(query, colname)


def project(arr, colname):
    return qformat('project({arr}, {colname})', arr=arr, colname=colname)

#------------------------------------------------------------------------
# Data types
#------------------------------------------------------------------------

true = "true"
false = "false"

########NEW FILE########
__FILENAME__ = app
from __future__ import absolute_import, division, print_function

import sys
import os

import flask
from flask import request, Response

import blaze
import datashape
from dynd import nd, ndt
from blaze.catalog.array_provider import json_array_provider
from blaze.catalog.blaze_url import (split_array_base, add_indexers_to_url,
                                     slice_as_string, index_tuple_as_string)
from blaze.py2help import _inttypes, _strtypes

from .datashape_html import render_datashape
from .compute_session import compute_session
from .crossdomain import crossdomain


app = flask.Flask('blaze.io.server')
app.sessions = {}


def indexers_navigation_html(base_url, array_name, indexers):
    base_url = base_url + array_name
    result = '<a href="' + base_url + '">' + array_name + '</a>'
    for i, idx in enumerate(indexers):
        if isinstance(idx, _strtypes):
            base_url = base_url + '.' + idx
            result += (' . <a href="' + base_url + '">' + idx + '</a>')
        elif isinstance(idx, _inttypes):
            new_base_url = base_url + '[' + str(idx) + ']'
            result += (' <a href="' + new_base_url + '">[' + str(idx) + ']</a>')
            # Links to increment/decrement this indexer
            #result += '<font style="size:7px"><table cellpadding="0" cellspacing="0" border="0">'
            #result += '<tr><td><a href="'
            #result += add_indexers_to_url(base_url, [idx + 1] + indexers[i+1:])
            #result += '">/\\</a></td></tr>'
            #result += '<tr><td><a href="'
            #result += add_indexers_to_url(base_url, [idx - 1] + indexers[i+1:])
            #result += '">\\/</a></td></tr>'
            #result += '</table></font>'
            base_url = new_base_url
        elif isinstance(idx, slice):
            s = slice_as_string(idx)
            base_url = base_url + s
            result += (' <a href="' + base_url + '">' + s + '</a>')
        elif isinstance(idx, tuple):
            s = index_tuple_as_string(idx)
            base_url = base_url + s
            result += (' <a href="' + base_url + '">' + s + '</a>')
        else:
            raise IndexError('Invalid indexer %r' % idx)
    return result


def get_array(array_name, indexers):
    arr = blaze.catalog.get(array_name)
    for i in indexers:
        if type(i) in [slice, int, tuple]:
            arr = arr[i]
        else:
            ds = arr.dshape
            if isinstance(ds, datashape.DataShape):
                ds = ds[-1]
            if isinstance(ds, datashape.Record) and i in ds.names:
                arr = getattr(arr, i)
            else:
                raise Exception('Blaze array does not have field ' + i)
    return arr


def html_array(arr, base_url, array_name, indexers):
    array_url = add_indexers_to_url(base_url + array_name, indexers)
    print(array_url)

    nav_html = indexers_navigation_html(base_url, array_name, indexers)
    datashape_html = render_datashape(array_url, arr.dshape)
    body = '<html><head><title>Blaze Array</title></head>\n' + \
        '<body>\n' + \
        'Blaze Array &gt; ' + nav_html + '\n<p />\n' + \
        '<a href="' + array_url + '?r=data.json">JSON</a>\n<p />\n' + \
        datashape_html + \
        '\n</body></html>'
    return body


@app.route("/favicon.ico")
def favicon():
    return 'no icon'


@app.route("/<path:path>", methods=['GET', 'POST', 'OPTIONS'])
@crossdomain(origin="*", automatic_options=False, automatic_headers=True)
def handle(path):
    if request.path in app.sessions:
        return handle_session_query()
    else:
        return handle_array_query()


def handle_session_query():
    session = app.sessions[request.path]
    q_req = request.values['r']
    if q_req == 'close_session':
        content_type, body = session.close()
        return Response(body, mimetype='application/json')
    elif q_req == 'add_computed_fields':
        j = request.values['json']
        content_type, body = session.add_computed_fields(j)
        return Response(body, mimetype='application/json')
    elif q_req == 'sort':
        j = request.values['json']
        content_type, body = session.sort(j)
        return Response(body, mimetype='application/json')
    elif q_req == 'groupby':
        j = request.values['json']
        content_type, body = session.groupby(j)
        return Response(body, mimetype='application/json')
    else:
        return 'something with session ' + session.session_name


def handle_array_query():
    array_name, indexers = split_array_base(request.path.rstrip('/'))
    arr = get_array(array_name, indexers)
    base_url = request.url_root[:-1]
    #no query params
    # NOTE: len(request.values) was failing within werkzeug
    if len(list(request.values)) == 0:
        return html_array(arr, base_url, array_name, indexers)
    q_req = request.values['r']
    if q_req == 'data.json':
        dat = arr.ddesc.dynd_arr()
        return Response(nd.as_py(nd.format_json(dat).view_scalars(ndt.bytes)),
                        mimetype='application/json')
    elif q_req == 'datashape':
        content_type = 'text/plain; charset=utf-8'
        return str(arr.dshape)
    elif q_req == 'dyndtype':
        content_type = 'application/json; charset=utf-8'
        body = str(arr.dtype)
        return Response(body, mimetype='application/json')
    elif q_req == 'dynddebug':
        return arr.debug_repr()
    elif q_req == 'create_session':
        session = compute_session(base_url,
                                  add_indexers_to_url(array_name, indexers))
        app.sessions[session.session_name] = session
        content_type, body = session.creation_response()
        return Response(body, mimetype='application/json')
    else:
        abort(400, "Unknown Blaze server request %s" % q_req)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = os.path.join(os.getcwdu(), 'arrays')
    array_provider = json_array_provider(root_path)
    app.array_provider = array_provider
    app.run(debug=True, port=8080, use_reloader=True)

########NEW FILE########
__FILENAME__ = compute_session
from __future__ import absolute_import, division, print_function

import json

from blaze.catalog.blaze_url import split_array_base
import dynd
from dynd import nd
from dynd.nd import as_numpy
from blaze import array


class compute_session:
    def __init__(self, base_url, array_name):
        session_name, root_dir = array_provider.create_session_dir()
        self.session_name = session_name
        self.root_dir = root_dir
        self.array_name = array_name
        self.base_url = base_url

    def get_session_array(self, array_name = None):
        if array_name is None:
            array_name = self.array_name
        array_root, indexers = split_array_base(array_name)
        arr = self.array_provider(array_root)
        if arr is None:
            raise Exception('No Blaze Array named ' + array_root)

        for i in indexers:
            if type(i) in [slice, int, tuple]:
                arr = arr[i]
            else:
                arr = getattr(arr, i)
        return arr

    def creation_response(self):
        content_type = 'application/json; charset=utf-8'
        body = json.dumps({
                'session' : self.base_url + self.session_name,
                'version' : 'prototype',
                'dynd_python_version': dynd.__version__,
                'dynd_version' : dynd.__libdynd_version__,
                'access' : 'no permission model yet'
            })
        return (content_type, body)

    def close(self):
        print('Deleting files for session %s' % self.session_name)
        self.array_provider.delete_session_dir(self.session_name)
        content_type = 'application/json; charset=utf-8'
        body = json.dumps({
                'session': self.base_url + self.session_name,
                'action': 'closed'
            })
        return (content_type, body)

    def sort(self, json_cmd):
        import numpy as np
        print ('sorting')
        cmd = json.loads(json_cmd)
        array_url = cmd.get('input', self.base_url + self.array_name)
        if not array_url.startswith(self.base_url):
            raise RuntimeError('Input array must start with the base url')
        array_name = array_url[len(self.base_url):]
        field = cmd['field']
        arr = self.get_session_array(array_name)
        nparr = as_numpy(arr)
        idxs = np.argsort(nparr[field])
        res = nd.ndobject(nparr[idxs])
        defarr = self.array_provider.create_deferred_array_filename(
                        self.session_name, 'sort_', res)
        dshape = nd.dshape_of(res)
        defarr[0].write(json.dumps({
                'dshape': dshape,
                'command': 'sort',
                'params': {
                    'field': field,
                }
            }))
        defarr[0].close()
        content_type = 'application/json; charset=utf-8'
        body = json.dumps({
                'session': self.base_url + self.session_name,
                'output': self.base_url + defarr[1],
                'dshape': dshape
            })
        return (content_type, body)

    def groupby(self, json_cmd):
        print('GroupBy operation')
        cmd = json.loads(json_cmd)
        array_url = cmd.get('input', self.base_url + self.array_name)
        if not array_url.startswith(self.base_url):
            raise RuntimeError('Input array must start with the base url')
        array_name = array_url[len(self.base_url):]
        fields = cmd['fields']

        arr = self.get_session_array(array_name)[...].ddesc.dynd_arr()

        # Do the groupby, get its groups, then
        # evaluate it because deferred operations
        # through the groupby won't work well yet.
        res = nd.groupby(arr, nd.fields(arr, *fields))
        groups = res.groups
        res = res.eval()

        # Write out the groupby result
        defarr_gb = self.array_provider.create_deferred_array_filename(
                        self.session_name, 'groupby_', array(res))
        dshape_gb = nd.dshape_of(res)
        defarr_gb[0].write(json.dumps({
                'dshape': dshape_gb,
                'command': 'groupby',
                'params': {
                    'fields': fields
                }
            }))
        defarr_gb[0].close()

        # Write out the groups
        defarr_groups = self.array_provider.create_deferred_array_filename(
                        self.session_name, 'groups_', groups)
        dshape_groups = nd.dshape_of(groups)
        defarr_groups[0].write(json.dumps({
                'dshape': dshape_groups,
                'command': 'groupby.groups',
                'params': {
                    'fields': fields
                }
            }))
        defarr_groups[0].close()

        content_type = 'application/json; charset=utf-8'
        body = json.dumps({
                'session': self.base_url + self.session_name,
                'output_gb': self.base_url + defarr_gb[1],
                'dshape_gb': dshape_gb,
                'output_groups': self.base_url + defarr_groups[1],
                'dshape_groups': dshape_groups
            })
        return (content_type, body)

    def add_computed_fields(self, json_cmd):
        print('Adding computed fields')
        cmd = json.loads(json_cmd)
        array_url = cmd.get('input', self.base_url + self.array_name)
        if not array_url.startswith(self.base_url):
            raise RuntimeError('Input array must start with the base url')
        array_name = array_url[len(self.base_url):]
        fields = cmd['fields']
        rm_fields = cmd.get('rm_fields', [])
        fnname = cmd.get('fnname', None)

        arr = self.get_session_array(array_name).ddesc.dynd_arr()

        res = nd.add_computed_fields(arr, fields, rm_fields, fnname)
        defarr = self.array_provider.create_deferred_array_filename(
                        self.session_name, 'computed_fields_', array(res))
        dshape = nd.dshape_of(res)
        defarr[0].write(json.dumps({
                'dshape': dshape,
                'command': 'add_computed_fields',
                'params': {
                    'fields': fields,
                    'rm_fields': rm_fields,
                    'fnname': fnname
                }
            }))
        defarr[0].close()
        content_type = 'application/json; charset=utf-8'
        body = json.dumps({
                'session': self.base_url + self.session_name,
                'output': self.base_url + defarr[1],
                'dshape': dshape
            })
        return (content_type, body)

    def make_computed_fields(self, json_cmd):
        print('Adding computed fields')
        cmd = json.loads(json_cmd)
        array_url = cmd.get('input', self.base_url + self.array_name)
        if not array_url.startswith(self.base_url):
            raise RuntimeError('Input array must start with the base url')
        array_name = array_url[len(self.base_url):]
        fields = cmd['fields']
        replace_undim = cmd.get('replace_undim', 0)
        fnname = cmd.get('fnname', None)

        arr = self.get_session_array(array_name).ddesc.dynd_arr()

        res = nd.make_computed_fields(arr, replace_undim, fields, fnname)
        defarr = self.array_provider.create_deferred_array_filename(
                        self.session_name, 'computed_fields_', array(res))
        dshape = nd.dshape_of(res)
        defarr[0].write(json.dumps({
                'dshape': dshape,
                'command': 'make_computed_fields',
                'params': {
                    'fields': fields,
                    'replace_undim': replace_undim,
                    'fnname': fnname
                }
            }))
        defarr[0].close()
        content_type = 'application/json; charset=utf-8'
        body = json.dumps({
                'session': self.base_url + self.session_name,
                'output': self.base_url + defarr[1],
                'dshape': dshape
            })
        return (content_type, body)

########NEW FILE########
__FILENAME__ = crossdomain
from __future__ import absolute_import, division, print_function

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper

from ... import py2help


def crossdomain(origin=None, methods=None, headers=None,
                automatic_headers=True,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, py2help.basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, py2help.basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        return methods
        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if automatic_headers and h.get('Access-Control-Request-Headers'):
                h['Access-Control-Allow-Headers'] = h['Access-Control-Request-Headers']
            return resp
        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

########NEW FILE########
__FILENAME__ = datashape_html
from __future__ import absolute_import, division, print_function

from datashape import DataShape, Record, Fixed, Var, CType, String, JSON
from jinja2 import Template


json_comment_templ = Template("""<font style="font-size:x-small"> # <a href="{{base_url}}?r=data.json">JSON</a></font>

""")

datashape_outer_templ = Template("""
<pre>
type <a href="{{base_url}}?r=datashape">BlazeDataShape</a> = {{ds_html}}
</pre>
""")


def render_datashape_recursive(base_url, ds, indent):
    result = ''

    if isinstance(ds, DataShape):
        for dim in ds[:-1]:
            if isinstance(dim, Fixed):
                result += ('%d * ' % dim)
            elif isinstance(dim, Var):
                result += 'var * '
            else:
                raise TypeError('Cannot render datashape with dimension %r' % dim)
        result += render_datashape_recursive(base_url, ds[-1], indent)
    elif isinstance(ds, Record):
        result += '{' + json_comment_templ.render(base_url=base_url)
        for fname, ftype in zip(ds.names, ds.types):
            child_url = base_url + '.' + fname
            child_result = render_datashape_recursive(child_url,
                            ftype, indent + '  ')
            result += (indent + '  ' +
                '<a href="' + child_url + '">' + str(fname) + '</a>'
                ': ' + child_result + ',')
            if isinstance(ftype, Record):
                result += '\n'
            else:
                result += json_comment_templ.render(base_url=child_url)
        result += (indent + '}')
    elif isinstance(ds, (CType, String, JSON)):
        result += str(ds)
    else:
        raise TypeError('Cannot render datashape %r' % ds)
    return result


def render_datashape(base_url, ds):
    ds_html = render_datashape_recursive(base_url, ds, '')
    return datashape_outer_templ.render(base_url=base_url, ds_html=ds_html)

########NEW FILE########
__FILENAME__ = start_simple_server
"""
Starts a Blaze server for tests.

$ start_test_server.py /path/to/catalog_config.yaml <portnumber>
"""

from __future__ import absolute_import, division, print_function

import sys
import os

if os.name == 'nt':
    old_excepthook = sys.excepthook

    # Exclude this from our autogenerated API docs.
    undoc = lambda func: func

    @undoc
    def gui_excepthook(exctype, value, tb):
        try:
            import ctypes, traceback
            MB_ICONERROR = 0x00000010
            title = u'Error starting test Blaze server'
            msg = u''.join(traceback.format_exception(exctype, value, tb))
            ctypes.windll.user32.MessageBoxW(0, msg, title, MB_ICONERROR)
        finally:
            # Also call the old exception hook to let it do
            # its thing too.
            old_excepthook(exctype, value, tb)

    sys.excepthook = gui_excepthook

import blaze
from blaze.io.server.app import app

blaze.catalog.load_config(sys.argv[1])
app.run(port=int(sys.argv[2]), use_reloader=False)

########NEW FILE########
__FILENAME__ = test_server
from __future__ import absolute_import, division, print_function

import os
import sys
import random
import subprocess
import socket
import time
import unittest

import datashape
import blaze
from blaze.catalog.tests.catalog_harness import CatalogHarness
from blaze.datadescriptor import ddesc_as_py, Remote_DDesc


class TestServer(unittest.TestCase):
    def startServer(self):
        # Start the server
        serverpy = os.path.join(os.path.dirname(__file__),
                                'start_simple_server.py')
        for attempt in range(2):
            self.port = 10000 + random.randrange(30000)
            cflags = 0
            exe = sys.executable
            if sys.platform == 'win32':
                if sys.version_info[:2] > (2, 6):
                    cflags |= subprocess.CREATE_NEW_PROCESS_GROUP

            self.proc = subprocess.Popen([sys.executable,
                                          serverpy,
                                          self.cat.catfile,
                                          str(self.port)],
                                         executable=exe,
                                         creationflags=cflags)
            for i in range(30):
                time.sleep(0.2)
                if self.proc.poll() is not None:
                    break
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if s.connect_ex(('127.0.0.1',self.port)) == 0:
                    s.close()
                    return
                s.close()
            print("Couldn't start Blaze test server attempt %d" % attempt)
            self.proc.terminate()
        raise RuntimeError('Failed to start the test Blaze server')

    def setUp(self):
        self.cat = CatalogHarness()
        # Load the test catalog for comparison with the server
        blaze.catalog.load_config(self.cat.catfile)
        self.startServer()
        self.baseurl = 'http://localhost:%d' % self.port

    def tearDown(self):
        self.proc.terminate()
        blaze.catalog.load_default()
        self.cat.close()

    def test_get_arr(self):
        ra = blaze.array(Remote_DDesc('%s/csv_arr' % self.baseurl))
        la = blaze.catalog.get('/csv_arr')
        self.assertEqual(la.dshape, ra.dshape)
        self.assertEqual(ddesc_as_py(la.ddesc), ddesc_as_py(blaze.eval(ra).ddesc))

    def test_compute(self):
        ra = blaze.array(Remote_DDesc('%s/py_arr' % self.baseurl))
        result = ra + 1
        result = blaze.eval(result)
        self.assertEqual(result.dshape, datashape.dshape('5 * int32'))
        self.assertEqual(ddesc_as_py(result.ddesc), [2, 3, 4, 5, 6])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = air
"""
Rewrite SQL operations in AIR. Generate SQL queries and execute them at roots.
"""

from __future__ import absolute_import, division, print_function

import datashape as ds
from blaze.compute.air.ir import Op

from . import db

from ... import Array
from .query import execute
from .syntax import reorder_select, emit, Table, Column
from .datadescriptor import SQLResult_DDesc
from ...datadescriptor import DyND_DDesc


def rewrite_sql(func, env):
    """
    Generate SQL queries for each SQL op and assemble them into one big query
    which we rewrite to python kernels.
    """
    strategies = env['strategies']      # op -> strategy (e.g. 'sql')
    impls = env['kernel.overloads']     # (op, strategy) -> Overload
    roots = env['roots']                # Backend boundaries: { Op }
    args = env['runtime.args']          # FuncArg -> blaze.Array
    conns = env['sql.conns']            # Op -> SQL Connection

    rewrite = set()                     # ops to rewrite to sql kernels
    delete  = set()                     # ops to delete
    queries = {}                        # op -> query (str)

    leafs = {}                          # op -> set of SQL leafs

    # Extract table names and insert in queries
    for arg in func.args:
        if strategies[arg] == 'sql':
            arr = args[arg]
            sql_ddesc = arr.ddesc

            if isinstance(sql_ddesc, DyND_DDesc):
                # Extract scalar value from blaze array
                assert not sql_ddesc.dshape.shape
                # Do something better here
                query = str(sql_ddesc.dynd_arr())
            else:
                table = Table(sql_ddesc.col.table_name)
                query = Column(table, sql_ddesc.col.col_name)

            queries[arg] = query
            leafs[arg] = [arg]

    # print(func)
    # print(strategies)

    # Generate SQL queries for each op
    for op in func.ops:
        if op.opcode == "kernel" and strategies[op] == 'sql':
            query_gen, signature = impls[op, 'sql']

            args = op.args[1:]
            inputs = [queries[arg] for arg in args]
            query = query_gen(*inputs)
            queries[op] = query
            if args[0] in conns:
                conns[op] = conns[args[0]]
            leafs[op] = [leaf for arg in args
                                  for leaf in leafs[arg]]

        elif op.opcode == 'convert':
            uses = func.uses[op]
            if all(strategies[use] == 'sql' for use in uses):
                arg = op.args[0]
                query = queries[arg]
                queries[op] = query

                if arg in conns:
                    conns[op] = conns[arg]
                leafs[op] = list(leafs[arg])
            else:
                continue

        else:
            continue

        if op in roots:
            rewrite.add(op)
        else:
            delete.add(op)

    # Rewrite sql kernels to python kernels
    for op in rewrite:
        query = queries[op]
        pykernel = sql_to_pykernel(query, op, env)
        newop = Op('pykernel', op.type, [pykernel, leafs[op]], op.result)
        op.replace(newop)

    # Delete remaining unnecessary ops
    func.delete_all(delete)


def sql_to_pykernel(expr, op, env):
    """
    Create an executable pykernel that executes the given query expression.
    """
    conns = env['sql.conns']
    conn = conns[op]
    dshape = op.type

    query = reorder_select(expr)
    select_query = emit(query)

    def sql_pykernel(*inputs):
        if isinstance(dshape.measure, ds.Record):
            assert len(dshape.measure.parameters) == 1, dshape
            assert dshape.measure.parameters[0], dshape

        try:
            # print("executing...", select_query)
            result = execute(conn, dshape, select_query, [])
        except db.OperationalError as e:
            raise db.OperationalError(
                "Error executing %s: %s" % (select_query, e))

        return Array(SQLResult_DDesc(result))

    return sql_pykernel

########NEW FILE########
__FILENAME__ = conn
"""
SQL connection and naming interface.

TODO: instantiate this stuff from the catalog?
"""

from __future__ import absolute_import, division, print_function

from . import db

#------------------------------------------------------------------------
# Connect
#------------------------------------------------------------------------

def connect(odbc_conn_str):
    """Connect to a SQL database using an ODBC connection string"""
    return db.connect(odbc_conn_str)

########NEW FILE########
__FILENAME__ = constructors
"""
SQL array constructors.
"""

from __future__ import absolute_import, division, print_function

from ... import Array
from .datadescriptor import SQL_DDesc

from datashape import dshape, Record, DataShape, coretypes


class TableSelection(object):
    """
    Table and column name

    Attributes
    ==========

    table: str
        table name

    colname: str
        column name
    """

    def __init__(self, table_name, colname):
        self.table_name = table_name
        self.col_name = colname

    def __repr__(self):
        return "TableSelection(%s)" % (self,)

    def __str__(self):
        return "%s.%s" % (self.table_name, self.col_name)


def sql_table(table_name, colnames, measures, conn):
    """
    Create a new blaze Array from an SQL table description. This returns
    a Record array.

    Parameters
    ==========

    table_name: str
        table name

    colnames: [str]
        column names

    measures: [DataShape]
        measure (element type) for each column

    conn: pyodbc/whatever Connection
    """
    dtype = Record(list(zip(colnames, measures)))
    record_dshape = DataShape(coretypes.Var(), dtype)
    table = TableSelection(table_name, '*')
    return Array(SQL_DDesc(record_dshape, table, conn))


def sql_column(table_name, colname, dshape, conn):
    """
    Create a new blaze Array from a single column description.

    Parameters
    ==========

    table_name: str
        table name

    colname: str
        column

    dshape: DataShape
        type for the column. This should include the dimension, which may be
        a TypeVar

    conn: pyodbc/whatever Connection
    """
    col = TableSelection(table_name, colname)
    return Array(SQL_DDesc(dshape, col, conn))

########NEW FILE########
__FILENAME__ = datadescriptor
"""
SQL data descriptor using pyodbc.
"""

from __future__ import absolute_import, division, print_function

from itertools import chain

from datashape import DataShape, Record
from dynd import nd

from ... import Array
from ...datadescriptor import DyND_DDesc
from ...datadescriptor import DDesc, Capabilities
from .query import execute, dynd_chunk_iterator


class SQL_DDesc(DDesc):
    """
    SQL data descriptor. This describes a column of some SQL table.
    """

    def __init__(self, dshape, col, conn):
        """
        Parameters
        ----------

        col: TableSelection
            Holds an SQL table name from which we can select data. This may also
            be some other valid query on which we can do further selection etc.
        """
        assert dshape
        assert col
        assert conn
        self._dshape = dshape
        self.col = col
        self.conn = conn

        # TODO: Validate query as a suitable expression to select from

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the SQL data descriptor."""
        return Capabilities(
            immutable = True,
            deferred = False,
            persistent = True,
            appendable = False,
            remote=True,
            )

    def describe_col(self):
        query_result = execute(self.conn, self.dshape,
                               "select %s from %s" % (self.col.col_name,
                                                      self.col.table_name), [])
        return SQLResult_DDesc(query_result)

    def __iter__(self):
        return iter(self.describe_col())

    def __getitem__(self, item):
        """
        Support my_sql_blaze_array['sql_column']
        """
        from .constructors import sql_table, sql_column

        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], str):
            if item[0] != slice(None):
                raise NotImplementedError("Currently only allowing slicing of whole sql array.")
            table = self.col
            colname = item[1]

            assert table.col_name == '*'
            dshape = column_dshape(self.dshape, colname)

            # Create blaze array for remote column
            arr = sql_column(table.table_name, colname, dshape, self.conn)

            # Array.__getitem__ will expect back a data descriptor!
            return arr.ddesc

        raise NotImplementedError

    def dynd_arr(self):
        return self.describe_col().dynd_arr()

    def __repr__(self):
        return "SQL_DDesc(%s)" % (self.col,)

    def __str__(self):
        return "<sql col %s with shape %s>" % (self.col, self.dshape)

    _printer = __str__
    _printer_repr = __repr__


class SQLResult_DDesc(DDesc):
    """
    SQL result data descriptor. This describes an query result and pulls it
    in lazily.
    """

    _dynd_result = None

    def __init__(self, query_result):
        assert query_result
        self._dshape = query_result.dshape
        self.query_result = _ResultIterable(query_result)

    @property
    def dshape(self):
        return self._dshape

    @property
    def capabilities(self):
        """The capabilities for the SQL result data descriptor."""
        return Capabilities(
            immutable = True,
            deferred = False,
            persistent = True,
            appendable = False,
            remote=True,
            )

    def __iter__(self):
        return (DyND_DDesc(x) for chunk in self.query_result for x in chunk)

    def __getitem__(self, item):
        """
        Support my_sql_blaze_array['sql_column']
        """
        # TODO: Lazy column description
        # return self.dynd_arr()[item]

        if isinstance(item, str):
            # Pull in data to determine length
            # TODO: this is bad
            return DyND_DDesc(getattr(self.dynd_arr(), item))

        raise NotImplementedError

    def dynd_arr(self):
        # TODO: This should really use blz
        if self._dynd_result is not None:
            return self._dynd_result

        # Allocate empty dynd array
        length = sum(len(chunk) for chunk in self.query_result)
        ds = DataShape(length, self.dshape.measure)
        result = nd.empty(str(ds))

        # Fill dynd array with chunks
        offset = 0
        for chunk in self.query_result:
            result[offset:offset + len(chunk)] = chunk
            offset += len(chunk)

        self._dynd_result = result
        return result

    def __repr__(self):
        return "SQLResult_DDesc()"

    def __str__(self):
        return str(Array(DyND_DDesc(self.dynd_arr())))

    _printer = __str__


class _ResultIterable(object):
    """
    Pull query results from cursor into dynd. Can be iterated over as many
    times as necessary (iterable).
    """

    def __init__(self, query_result):
        self.query_result = _ResultIterator(query_result)

    def __iter__(self):
        return chain(self.query_result.chunks, self.query_result)


class _ResultIterator(object):
    """
    Pull query results from cursor into dynd. Can be iterated over once
    (iterator), after which all chunks are loaded in `self.chunks`.
    """

    def __init__(self, query_result):
        self.query_result = dynd_chunk_iterator(query_result)

        # Accumulated dynd chunks
        self.chunks = []

    def __iter__(self):
        return self

    def next(self):
        next_chunk = next(self.query_result)
        self.chunks.append(next_chunk)
        return next_chunk

    __next__ = next


def column_dshape(dshape, colname):
    """
    Given a record dshape, project a column out
    """
    rec = dshape.measure

    if not isinstance(rec, Record):
        raise TypeError("Can only select fields from record type")
    if colname not in rec.fields:
        raise ValueError("No such field %r" % (colname,))

    measure = rec.fields[colname]
    params = list(dshape.shape) + [measure]
    dshape = DataShape(*params)

    return dshape

########NEW FILE########
__FILENAME__ = error
"""
Errors raised by any SQL operation.
"""

from __future__ import absolute_import, division, print_function

from blaze import error


class SQLError(error.BlazeException):
    """Base exception for SQL backend related errors"""

########NEW FILE########
__FILENAME__ = kernel
"""
Create SQL kernel implementations.
"""

from __future__ import absolute_import, division, print_function

SQL = 'sql'

########NEW FILE########
__FILENAME__ = ops
"""SQL implementations of element-wise ufuncs."""

from __future__ import absolute_import, division, print_function

from ...compute.function import BlazeFunc
from ...compute.ops import ufuncs
from .kernel import SQL
from .syntax import Call, Expr, QOrderBy, QWhere, And, Or, Not


def sqlfunction(signature):
    def decorator(f):
        bf = BlazeFunc('blaze', f.__name__)
        # FIXME: Adding a dummy CKERNEL overload to make things work for now
        bf.add_overload(signature, None)
        bf.add_plugin_overload(signature, f, SQL)
        return bf
    return decorator


def overload_unop_ufunc(signature, name, op):
    """Add a unary sql overload to a blaze ufunc"""
    def unop(x):
        return Expr([op, x])
    unop.__name__ = name
    bf = getattr(ufuncs, name)
    bf.add_plugin_overload(signature, unop, SQL)


def overload_binop_ufunc(signature, name, op):
    """Add a binary sql overload to a blaze ufunc"""
    def binop(a, b):
        return Expr([a, op, b])
    binop.__name__ = name
    bf = getattr(ufuncs, name)
    bf.add_plugin_overload(signature, binop, SQL)


# Arithmetic

overload_binop_ufunc("(T, T) -> T", "add", "+")
overload_binop_ufunc("(T, T) -> T", "multiply", "*")
overload_binop_ufunc("(T, T) -> T", "subtract", "-")
overload_binop_ufunc("(T, T) -> T", "floor_divide", "/")
overload_binop_ufunc("(T, T) -> T", "divide", "/")
overload_binop_ufunc("(T, T) -> T", "true_divide", "/")
overload_binop_ufunc("(T, T) -> T", "mod", "%")

overload_unop_ufunc("(T) -> T", "negative", "-")

# Compare

overload_binop_ufunc("(T, T) -> bool", "equal", "==")
overload_binop_ufunc("(T, T) -> bool", "not_equal", "!=")
overload_binop_ufunc("(T, T) -> bool", "less", "<")
overload_binop_ufunc("(T, T) -> bool", "less_equal", "<=")
overload_binop_ufunc("(T, T) -> bool", "greater", ">")
overload_binop_ufunc("(T, T) -> bool", "greater_equal", ">=")

# Logical

overload_binop_ufunc("(bool, bool) -> bool",
                     "logical_and", "AND")
overload_binop_ufunc("(bool, bool) -> bool",
                     "logical_or", "OR")
overload_unop_ufunc("(bool) -> bool", "logical_not", "NOT")


def logical_xor(a, b):
    # Potential exponential code generation...
    return And(Or(a, b), Not(And(a, b)))

ufuncs.logical_xor.add_plugin_overload("(bool, bool) -> bool",
                                       logical_xor, SQL)

# SQL Functions

@sqlfunction('(A * DType) -> DType')
def sum(col):
    return Call('SUM', [col])

@sqlfunction('(A * DType) -> DType')
def avg(col):
    return Call('AVG', [col])

@sqlfunction('(A * DType) -> DType')
def min(col):
    return Call('MIN', [col])

@sqlfunction('(A * DType) -> DType')
def max(col):
    return Call('MAX', [col])

# SQL Join, Where, Group by, Order by

def merge(left, right, how='left', on=None, left_on=None, right_on=None,
          left_index=False, right_index=False, sort=True):
    """
    Join two tables.
    """
    raise NotImplementedError


def index(col, index, order=None):
    """
    Index a table or column with a predicate.

        view = merge(table1, table2)
        result = view[table1.id == table2.id]

    or

        avg(table1.age[table1.state == 'TX'])
    """
    result = sqlindex(col, index)
    if order:
        result = sqlorder(result, order)
    return result


@sqlfunction('(A * S, A * B) -> var * S')
def sqlindex(col, where):
    return QWhere(col, where)

@sqlfunction('(A * S, A * B) -> A * S')
def sqlorder(col, by):
    if not isinstance(by, (tuple, list)):
        by = [by]
    return QOrderBy(col, by)

########NEW FILE########
__FILENAME__ = query
"""
SQL query execution.
"""

from __future__ import absolute_import, division, print_function

from . import db

from datashape import DataShape, Record
from dynd import nd


def execute(conn, dshape, query, params):
    """
    Execute a query on the given connection and return a Result that
    can be iterated over or consumed in DyNd chunks.
    """
    cursor = conn.cursor()
    cursor.execute(query, params)
    return Result(cursor, dshape)


class Result(object):
    """
    Result from executing a query
    """

    def __init__(self, cursor, dshape):
        self.cursor = cursor
        self.dshape = dshape

    # def __iter__(self):
    #     return iter_result(self.cursor, self.dshape)


def iter_result(result, dshape):
    if not isinstance(dshape.measure, Record):
        return iter(row[0] for row in result)
    return iter(result)


def dynd_chunk_iterator(result, chunk_size=1024):
    """
    Turn a query Result into a bunch of DyND arrays
    """
    cursor = result.cursor

    chunk_size = max(cursor.arraysize, chunk_size)
    while True:
        try:
            results = cursor.fetchmany(chunk_size)
        except db.Error:
            break

        if not results:
            break

        dshape = DataShape(len(results), result.dshape.measure)
        chunk = nd.empty(str(dshape))
        chunk[:] = list(iter_result(results, dshape))
        yield chunk

########NEW FILE########
__FILENAME__ = syntax
# -*- coding: utf-8 -*-

"""
SQL syntax building.
"""

from __future__ import absolute_import, division, print_function

from collections import namedtuple
from functools import reduce

#------------------------------------------------------------------------
# Syntax (declarative)
#------------------------------------------------------------------------

def qtuple(name, attrs):
    cls = namedtuple(name, attrs)
    cls.__str__ = lambda self: "Query(%s)" % (emit(self),)
    return cls

Table   = qtuple('Table',   ['tablename'])
Column  = qtuple('Column',  ['table', 'colname'])
Select  = qtuple('Select',  ['exprs', 'from_expr', 'where',
                                 'groupby', 'order'])
Where   = qtuple('Where',   ['expr'])
GroupBy = qtuple('GroupBy', ['cols'])
From    = qtuple('From',    ['exprs'])
OrderBy = qtuple('OrderBy', ['exprs', 'ascending'])
Call    = qtuple('Call',    ['name', 'args'])
Expr    = qtuple('Expr',    ['args'])
And     = lambda e1, e2: Expr([e1, 'AND', e2])
Or      = lambda e1, e2: Expr([e1, 'OR', e2])
Not     = lambda e1: Expr(['NOT', e1])


def qmap(f, q):
    """
    Apply `f` post-order to all sub-terms in query term `q`.
    """
    if hasattr(q, '_fields'):
        attrs = []
        for field in q._fields:
            attr = getattr(q, field)
            attrs.append(qmap(f, attr))

        cls = type(q)
        obj = cls(*attrs)
        return f(obj)

    elif isinstance(q, (list, tuple)):
        cls = type(q)
        return cls(qmap(f, x) for x in q)

    return f(q)

#------------------------------------------------------------------------
# Query expressions
#------------------------------------------------------------------------

# These may be nested in an expression-like fashion. These expressions may
# then be reordered to obtain declarative syntax above

QWhere      = namedtuple('QWhere', ['arr', 'expr'])
QGroupBy    = namedtuple('QGroupBy', ['arr', 'keys'])
QOrderBy    = namedtuple('QOrderBy', ['arr', 'exprs', 'ascending'])

def reorder_select(query):
    """
    Reorder SQL query to prepare for codegen.
    """
    ## Extract info ##
    selects = []
    wheres = []
    orders = []
    groupbys = []
    tables = set()

    def extract(expr):
        if isinstance(expr, QWhere):
            selects.append(expr.arr)
            wheres.append(expr.expr)
            return expr.arr

        elif isinstance(expr, QGroupBy):
            selects.append(expr.arr)
            groupbys.extend(expr.keys)
            return expr.arr

        elif isinstance(expr, QOrderBy):
            selects.append(expr.arr)
            orders.append(expr)
            return expr.arr

        elif isinstance(expr, Table):
            tables.add(expr)

        return expr

    expr = qmap(extract, query)

    ## Build SQL syntax ##
    if isinstance(expr, Table):
        expr = '*'

    if len(orders) > 1:
        raise ValueError("Only a single ordering may be specified")
    elif orders:
        [order] = orders

    return Select([expr],
                  From(list(tables)),
                  Where(reduce(And, wheres)) if wheres else None,
                  GroupBy(groupbys) if groupbys else None,
                  OrderBy(order.exprs, order.ascending) if orders else None,
                  )

#------------------------------------------------------------------------
# Query generation
#------------------------------------------------------------------------

def emit(q):
    """Emit SQL query from query object"""
    if isinstance(q, Table):
        return q.tablename
    if isinstance(q, Column):
        return "%s.%s" % (emit(q.table), emit(q.colname))
    elif isinstance(q, Select):
        return "SELECT %s %s %s %s %s" % (
                    ", ".join(emit(expr) for expr in q.exprs),
                    emit(q.from_expr),
                    emit(q.where),
                    emit(q.groupby),
                    emit(q.order))
    elif isinstance(q, From):
        return "FROM %s" % ", ".join(emit(expr) for expr in q.exprs)
    elif isinstance(q, Where):
        return "WHERE %s" % (emit(q.expr),)
    elif isinstance(q, OrderBy):
        order_clause = "ORDER BY %s" % " ".join(emit(expr) for expr in q.exprs)
        return "%s %s" % (order_clause, "ASC" if q.ascending else "DESC")
    elif isinstance(q, GroupBy):
        return "GROUP BY %s" % ", ".join(emit(col) for col in q.cols)
    elif isinstance(q, Expr):
        return "(%s)" % " ".join(emit(arg) for arg in q.args)
    elif isinstance(q, Call):
        return "%s(%s)" % (q.name, ", ".join(emit(arg) for arg in q.args))
    elif q is None:
        return ""
    else:
        return str(q)


if __name__ == '__main__':
    table = Table('Table')
    col1 = Column(table, 'attr1')
    col2 = Column(table, 'attr2')
    expr = Expr(Expr(col1, '+', col1), '-', col2)
    query = Select([expr], From(table), Where(Expr(col1, '=', col2)),
                   None, None)
    print(emit(query))

########NEW FILE########
__FILENAME__ = testutils
from __future__ import print_function, division, absolute_import

data = [
    (4,  "hello", 2.1),
    (8,  "world", 4.2),
    (16, "!",     8.4),
]


def create_sqlite_table():
    import sqlite3 as db

    conn = db.connect(":memory:")
    c = conn.cursor()
    c.execute('''create table testtable
    (i INTEGER, msg text, price real)''')
    c.executemany("""insert into testtable
                  values (?, ?, ?)""", data)
    conn.commit()
    c.close()

    return conn

#def create_sqlite_table():
#    import pyodbc as db
#    conn = db.connect("Driver=SQLite ODBC Driver "
#                      "NameDatabase=Database8;LongNames=0;Timeout=1000;"
#                      "NoTXN=0;SyncPragma=NORMAL;StepAPI=0;")
#    #conn = db.connect("Data Source=:memory:;Version=3;New=True;")
#    c = conn.cursor()
#    c.execute('''create table testtable
#    (i INTEGER, msg text, price real)''')
#    c.executemany("""insert into testtable
#                  values (?, ?, ?)""", data)
#    conn.commit()
#    c.close()
#
#    return conn

########NEW FILE########
__FILENAME__ = test_sql
from __future__ import print_function, division, absolute_import

import unittest

from nose.plugins.skip import SkipTest
import numpy as np

import blaze
from datashape import dshape, bool_

from blaze import add, multiply, eval
from blaze.io.sql import sql_table, sql_column, db
from blaze.io.sql import ops
from blaze.io.sql.tests.testutils import create_sqlite_table, data
from blaze.py2help import skip, skipIf


class TestSQL(unittest.TestCase):

    def setUp(self):
        self.conn = create_sqlite_table()

        self.table = sql_table(
            'testtable',
            ['i', 'msg', 'price'],
            [dshape('int32'), dshape('string'), dshape('float64')],
            self.conn)

        self.col_i = sql_column('testtable', 'i',
                                dshape('3 * int32'),
                                self.conn)
        self.col_msg = sql_column('testtable', 'msg',
                                  dshape('3 * string'),
                                  self.conn)
        self.col_price = sql_column('testtable', 'price',
                                    dshape('3 * float64'),
                                    self.conn)

        test_data = np.array(data, dtype=[('i', np.int32),
                                          ('msg', '|S5'),
                                          ('price', np.float64)])
        self.np_i = test_data['i']
        self.np_msg = test_data['msg']
        self.np_price = test_data['price']


class TestSQLOps(TestSQL):

    ## ufuncs

    @skipIf(db is None, 'pyodbc is not installed')
    def test_add_scalar(self):
        expr = self.col_i + 2
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [6, 10, 18])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_sub_scalar(self):
        expr = self.col_i - 2
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [2, 6, 14])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_mul_scalar(self):
        expr = self.col_i * 2
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [8, 16, 32])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_floordiv_scalar(self):
        expr = self.col_i // 2
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [2, 4, 8])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_truediv_scalar(self):
        expr = self.col_i / 2
        result = eval(expr)
        self.assertEqual([float(x) for x in result], [2., 4., 8.])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_mod_scalar(self):
        expr = self.col_i % 3
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [1, 2, 1])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_neg_scalar(self):
        expr = -self.col_i
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [-4, -8, -16])

    ## compare

    @skipIf(db is None, 'pyodbc is not installed')
    def test_eq_scalar(self):
        expr = self.col_i == 8
        result = eval(expr)
        self.assertEqual(result.dshape.measure, bool_)
        self.assertEqual([bool(x) for x in result], [False, True, False])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_ne_scalar(self):
        expr = self.col_i != 8
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [True, False, True])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_lt_scalar(self):
        expr = self.col_i < 5
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [True, False, False])


    @skipIf(db is None, 'pyodbc is not installed')
    def test_le_scalar(self):
        expr = self.col_i <= 8
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [True, True, False])


    @skipIf(db is None, 'pyodbc is not installed')
    def test_gt_scalar(self):
        expr = self.col_i > 9
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [False, False, True])


    @skipIf(db is None, 'pyodbc is not installed')
    def test_ge_scalar(self):
        expr = self.col_i >= 8
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [False, True, True])

    ## logical

    @skipIf(db is None, 'pyodbc is not installed')
    def test_and(self):
        expr = blaze.logical_and(5 < self.col_i, self.col_i < 10)
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [False, True, False])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_or(self):
        expr = blaze.logical_or(self.col_i < 5, self.col_i > 10)
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [True, False, True])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_xor(self):
        expr = blaze.logical_xor(self.col_i < 9, self.col_i > 6)
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [True, False, True])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_not(self):
        expr = blaze.logical_not(self.col_i < 5)
        result = eval(expr)
        self.assertEqual([bool(x) for x in result], [False, True, True])


class TestSQLUFuncExpressions(TestSQL):

    @skipIf(db is None, 'pyodbc is not installed')
    def test_select_expr(self):
        raise SkipTest("Correctly compose queries with aggregations")

        expr = ((ops.max(self.col_price) / ops.min(self.col_price)) *
                (self.col_i + 2) * 3.1 -
                ops.avg(self.col_i))
        result = eval(expr)

        np_result = ((np.max(self.np_price) / np.min(self.np_price)) *
                     (self.np_i + 2) * 3.1 -
                     np.average(self.np_i) / np.max(self.np_price))

        self.assertEqual([float(x) for x in result],
                         [float(x) for x in np_result])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_select_where(self):
        expr = ops.index(self.col_i + 2 * self.col_price,
                         blaze.logical_and(self.col_price > 5, self.col_price < 7))
        result = eval(expr)

        np_result = (self.np_i + 2 * self.np_price)[
            np.logical_and(self.np_price > 5, self.np_price < 7)]

        self.assertEqual([float(x) for x in result],
                         [float(x) for x in np_result])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_select_where2(self):
        expr = ops.index(self.col_i + 2 * self.col_price,
                         blaze.logical_or(
                             blaze.logical_and(self.col_price > 5,
                                               self.col_price < 7),
                             self.col_i > 6))
        result = eval(expr)

        np_result = (self.np_i + 2 * self.np_price)[
            np.logical_or(
                np.logical_and(self.np_price > 5,
                               self.np_price < 7),
                self.np_i > 6)]

        self.assertEqual([float(x) for x in result],
                         [float(x) for x in np_result])



class TestSQLDataTypes(TestSQL):

    @skipIf(db is None, 'pyodbc is not installed')
    def test_int(self):
        expr = self.col_i // 2
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [2, 4, 8])


class TestSQLColumns(TestSQL):

    @skipIf(db is None, 'pyodbc is not installed')
    def test_query(self):
        expr = add(self.col_i, self.col_i)
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [8, 16, 32])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_query_scalar(self):
        expr = add(self.col_i, 2)
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [6, 10, 18])

    @skipIf(db is None, 'pyodbc is not installed')
    def test_query_where(self):
        expr = ops.index(self.col_i + self.col_i, self.col_i > 5)
        result = eval(expr)
        self.assertEqual([int(x) for x in result], [16, 32])


class TestSQLTable(TestSQL):

    #@skipIf(db is None, 'pyodbc is not installed')
    @skip("there's an inconsistency between the table and column datashapes")
    def test_query_where(self):
        expr = ops.index(self.table, self.col_i > 5)
        result = eval(expr)
        row1, row2 = result
        self.assertEqual((int(row1[0]), str(row1[1]), float(row1[2])),
                         (8, "world", 4.2))
        self.assertEqual((int(row2[0]), str(row2[1]), float(row2[2])),
                         (16, "!", 8.4))

    @skipIf(db is None, 'pyodbc is not installed')
    def test_index_table(self):
        expr = self.table[:, 'i']
        self.assertEqual([int(i) for i in expr], [4, 8, 16])

    #@skipIf(db is None, 'pyodbc is not installed')
    @skip("there's an inconsistency between the table and column datashapes")
    def test_index_sql_result_table(self):
        expr = ops.index(self.table, self.col_i > 5)
        result = eval(expr)
        i_col = result[:, 'i']
        self.assertEqual([int(i_col[0]), int(i_col[1])], [8, 16])


class TestSQLStr(TestSQL):

    @skipIf(db is None, 'pyodbc is not installed')
    def test_str(self):
        repr(self.table)


if __name__ == '__main__':
    # TestSQLTable('test_query_where').debug()
    # TestSQLUFuncExpressions('test_select_where').debug()
    # TestSQLTable('test_index_sql_result_table').debug()
    # TestSQLStr('test_str').debug()
    unittest.main()

########NEW FILE########
__FILENAME__ = test_syntax
from __future__ import print_function, division, absolute_import

import unittest

from blaze.io.sql.syntax import (Table, Column, Select, Expr, Call, From, Where,
                                 GroupBy, OrderBy, qmap, emit,
                                 reorder_select, QWhere, QGroupBy, QOrderBy)


def assert_query(result, query):
    assert " ".join(result.split()) == " ".join(query.split()), (result, query)

table = Table('Table')
col1 = Column(table, 'attr1')
col2 = Column(table, 'attr2')


class TestSyntax(unittest.TestCase):

    def test_syntax_where(self):
        expr = Expr([Expr([col1, '+', col1]), '-', col2])
        query = Select([expr],
                       From([table]),
                       Where(Expr([col1, '=', col2])),
                       None, None)
        result = emit(query)
        assert_query(result, "SELECT ((Table.attr1 + Table.attr1) - Table.attr2) "
                             "FROM Table WHERE (Table.attr1 = Table.attr2)")

    def test_syntax_order(self):
        expr = Expr([col1, '+', col1])
        query = Select([expr],
                       From([table]),
                       Where(Expr([col1, '=', col2])),
                       None,
                       OrderBy([col1], True))
        result = emit(query)
        assert_query(result, "SELECT (Table.attr1 + Table.attr1) "
                             "FROM Table "
                             "WHERE (Table.attr1 = Table.attr2) "
                             "ORDER BY Table.attr1 ASC")

    def test_syntax_groupby(self):
        query = Select([col1, Call('SUM', [col2])],
                       From([table]),
                       Where(Expr([col1, '=', col2])),
                       GroupBy([col1]),
                       None)
        result = emit(query)
        assert_query(result, "SELECT Table.attr1, SUM(Table.attr2) "
                             "FROM Table "
                             "WHERE (Table.attr1 = Table.attr2) "
                             "GROUP BY Table.attr1")

    def test_qmap(self):
        query = Select([col1, Call('SUM', col2)],
                       From([table]),
                       Where(Expr([col1, '=', col2])),
                       GroupBy([col1]),
                       None)

        terms = []

        def f(q):
            terms.append(q)
            return q

        qmap(f, query)


class TestReorder(unittest.TestCase):

    def test_reorder_where(self):
        expr = QWhere(col1, Expr([col1, '<', col2]))
        query = reorder_select(expr)
        assert_query(emit(query),
                     "SELECT Table.attr1 FROM Table WHERE "
                     "(Table.attr1 < Table.attr2)")

    def test_reorder_groupby(self):
        expr = QGroupBy(QWhere(col1, Expr([col1, '<', col2])), [col2])
        query = reorder_select(expr)
        assert_query(emit(query),
                     "SELECT Table.attr1 "
                     "FROM Table "
                     "WHERE (Table.attr1 < Table.attr2) "
                     "GROUP BY Table.attr2 ")

    def test_reorder_orderby(self):
        expr = QOrderBy(
                    QGroupBy(
                        QWhere(col1,
                               Expr([col1, '<', col2])),
                        [col2]),
                    [Call('SUM', [col1])],
                    True)
        query = reorder_select(expr)
        assert_query(emit(query),
                     "SELECT Table.attr1 "
                     "FROM Table "
                     "WHERE (Table.attr1 < Table.attr2) "
                     "GROUP BY Table.attr2 "
                     "ORDER BY SUM(Table.attr1) ASC")



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = array_repr
from __future__ import absolute_import, division, print_function

from . import _arrayprint
from ...datadescriptor import Remote_DDesc


def array_repr(a):
    pre = 'array('
    post = ',\n' + ' '*len(pre) + "dshape='" + str(a.dshape) + "'" + ')'

    # TODO: create a mechanism for data descriptor to override
    #       printing.
    if isinstance(a.ddesc, Remote_DDesc):
        body = 'Remote_DDesc(%r)' % a.ddesc.url
    else:
        body = _arrayprint.array2string(a.ddesc,
                          separator=', ',
                          prefix=' '*len(pre))

    return pre + body + post

########NEW FILE########
__FILENAME__ = array_str
from __future__ import absolute_import, division, print_function

from . import _arrayprint


def array_str(a):
    return _arrayprint.array2string(a.ddesc)

########NEW FILE########
__FILENAME__ = _arrayprint
"""Array printing function

"""

from __future__ import absolute_import, division, print_function

from ...py2help import xrange

__all__ = ["array2string", "set_printoptions", "get_printoptions"]
__docformat__ = 'restructuredtext'


#
# Written by Konrad Hinsen <hinsenk@ere.umontreal.ca>
# last revision: 1996-3-13
# modified by Jim Hugunin 1997-3-3 for repr's and str's (and other details)
# and by Perry Greenfield 2000-4-1 for numarray
# and by Travis Oliphant  2005-8-22 for numpy
# and by Oscar Villellas 2013-4-30 for blaze
# and by Andy R. Terrel 2013-12-17 for blaze

import sys
import numpy as np
import numpy.core.umath as _um
import datashape
from datashape import Fixed, has_var_dim

from ...datadescriptor import DDesc, ddesc_as_py

# These are undesired dependencies:
from numpy import ravel, maximum, minimum, absolute

import inspect


def _dump_data_info(x, ident=None):
    ident = (ident if ident is not None
             else inspect.currentframe().f_back.f_lineno)
    if isinstance(x, DDesc):
        subclass = 'DATA DESCRIPTOR'
    elif isinstance(x, np.ndarray):
        subclass = 'NUMPY ARRAY'
    else:
        subclass = 'UNKNOWN'

    print('-> %s: %s: %s' % (ident, subclass, repr(x)))


def product(x, y):
    return x*y


def isnan(x):
    # hacks to remove when isnan/isinf are available for data descriptors
    if isinstance(x, DDesc):
        return _um.isnan(ddesc_as_py(x))
    else:
        return _um.isnan(x)


def isinf(x):
    if isinstance(x, DDesc):
        return _um.isinf(ddesc_as_py(x))
    else:
        return _um.isinf(x)


def not_equal(x, val):
    if isinstance(x, DDesc):
        return _um.not_equal(ddesc_as_py(x))
    else:
        return _um.not_equal(x, val)

# repr N leading and trailing items of each dimension
_summaryEdgeItems = 3

# total items > triggers array summarization
_summaryThreshold = 1000

_float_output_precision = 8
_float_output_suppress_small = False
_line_width = 75
_nan_str = 'nan'
_inf_str = 'inf'
_formatter = None  # formatting function for array elements

if sys.version_info[0] >= 3:
    from functools import reduce


def set_printoptions(precision=None, threshold=None, edgeitems=None,
                     linewidth=None, suppress=None,
                     nanstr=None, infstr=None,
                     formatter=None):
    """
    Set printing options.

    These options determine the way floating point numbers, arrays and
    other NumPy objects are displayed.

    Parameters
    ----------
    precision : int, optional
        Number of digits of precision for floating point output (default 8).
    threshold : int, optional
        Total number of array elements which trigger summarization
        rather than full repr (default 1000).
    edgeitems : int, optional
        Number of array items in summary at beginning and end of
        each dimension (default 3).
    linewidth : int, optional
        The number of characters per line for the purpose of inserting
        line breaks (default 75).
    suppress : bool, optional
        Whether or not suppress printing of small floating point values
        using scientific notation (default False).
    nanstr : str, optional
        String representation of floating point not-a-number (default nan).
    infstr : str, optional
        String representation of floating point infinity (default inf).
    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are::

            - 'bool'
            - 'int'
            - 'float'
            - 'complexfloat'
            - 'longcomplexfloat' : composed of two 128-bit floats
            - 'numpy_str' : types `numpy.string_` and `numpy.unicode_`
            - 'str' : all other strings

        Other keys that can be used to set a group of types at once are::

            - 'all' : sets all types
            - 'int_kind' : sets 'int'
            - 'float_kind' : sets 'float'
            - 'complex_kind' : sets 'complexfloat'
            - 'str_kind' : sets 'str' and 'numpystr'

    See Also
    --------
    get_printoptions, set_string_function, array2string

    Notes
    -----
    `formatter` is always reset with a call to `set_printoptions`.

    Examples
    --------
    Floating point precision can be set:

    >>> np.set_printoptions(precision=4)
    >>> print(np.array([1.123456789]))
    [ 1.1235]

    Long arrays can be summarised:

    >>> np.set_printoptions(threshold=5)
    >>> print(np.arange(10))
    [0 1 2 ..., 7 8 9]

    Small results can be suppressed:

    >>> eps = np.finfo(float).eps
    >>> x = np.arange(4.)
    >>> x**2 - (x + eps)**2
    array([ -4.9304e-32,  -4.4409e-16,   0.0000e+00,   0.0000e+00])
    >>> np.set_printoptions(suppress=True)
    >>> x**2 - (x + eps)**2
    array([-0., -0.,  0.,  0.])

    A custom formatter can be used to display array elements as desired:

    >>> np.set_printoptions(formatter={'all':lambda x: 'int: '+str(-x)})
    >>> x = np.arange(3)
    >>> x
    array([int: 0, int: -1, int: -2])
    >>> np.set_printoptions()  # formatter gets reset
    >>> x
    array([0, 1, 2])

    To put back the default options, you can use:

    >>> np.set_printoptions(edgeitems=3,infstr='inf',
    ... linewidth=75, nanstr='nan', precision=8,
    ... suppress=False, threshold=1000, formatter=None)
    """

    global _summaryThreshold, _summaryEdgeItems, _float_output_precision
    global _line_width, _float_output_suppress_small, _nan_str, _inf_str
    global _formatter

    if linewidth is not None:
        _line_width = linewidth
    if threshold is not None:
        _summaryThreshold = threshold
    if edgeitems is not None:
        _summaryEdgeItems = edgeitems
    if precision is not None:
        _float_output_precision = precision
    if suppress is not None:
        _float_output_suppress_small = not not suppress
    if nanstr is not None:
        _nan_str = nanstr
    if infstr is not None:
        _inf_str = infstr
    _formatter = formatter


def get_printoptions():
    """
    Return the current print options.

    Returns
    -------
    print_opts : dict
        Dictionary of current print options with keys

          - precision : int
          - threshold : int
          - edgeitems : int
          - linewidth : int
          - suppress : bool
          - nanstr : str
          - infstr : str
          - formatter : dict of callables

        For a full description of these options, see `set_printoptions`.

    See Also
    --------
    set_printoptions, set_string_function

    """
    d = dict(precision=_float_output_precision,
             threshold=_summaryThreshold,
             edgeitems=_summaryEdgeItems,
             linewidth=_line_width,
             suppress=_float_output_suppress_small,
             nanstr=_nan_str,
             infstr=_inf_str,
             formatter=_formatter)
    return d


def _extract_summary(a):
    return l


def _leading_trailing(a):
    import numpy.core.numeric as _nc
    if len(a.dshape.shape) == 1:
        if len(a) > 2*_summaryEdgeItems:
            b = [ddesc_as_py(a[i]) for i in range(_summaryEdgeItems)]
            b.extend([ddesc_as_py(a[i]) for i in range(-_summaryEdgeItems, 0)])
        else:
            b = ddesc_as_py(a)
    else:
        if len(a) > 2*_summaryEdgeItems:
            b = [_leading_trailing(a[i])
                 for i in range(_summaryEdgeItems)]
            b.extend([_leading_trailing(a[-i])
                      for i in range(-_summaryEdgeItems, 0)])
        else:
            b = [_leading_trailing(a[i]) for i in range(0, len(a))]
    return b


def _boolFormatter(x):
    if x:
        return ' True'
    else:
        return 'False'


def repr_format(x):
    return repr(x)


def _apply_formatter(format_dict, formatter):
    fkeys = [k for k in formatter.keys() if formatter[k] is not None]
    if 'all' in fkeys:
        for key in formatdict.keys():
            formatdict[key] = formatter['all']
    if 'int_kind' in fkeys:
        for key in ['int']:
            formatdict[key] = formatter['int_kind']
    if 'float_kind' in fkeys:
        for key in ['float']:
            formatdict[key] = formatter['float_kind']
    if 'complex_kind' in fkeys:
        for key in ['complexfloat', 'longcomplexfloat']:
            formatdict[key] = formatter['complex_kind']
    if 'str_kind' in fkeys:
        for key in ['numpystr', 'str']:
            formatdict[key] = formatter['str_kind']
    for key in formatdict.keys():
        if key in fkeys:
            formatdict[key] = formatter[key]


def _choose_format(formatdict, ds):
    if isinstance(ds, datashape.DataShape):
        ds = ds[-1]

    if ds == datashape.bool_:
        format_function = formatdict['bool']
    elif ds in [datashape.int8, datashape.int16,
                datashape.int32, datashape.int64,
                datashape.uint8, datashape.uint16,
                datashape.uint32, datashape.uint64]:
        format_function = formatdict['int']
    elif ds in [datashape.float32, datashape.float64]:
        format_function = formatdict['float']
    elif ds in [datashape.complex_float32, datashape.complex_float64]:
        format_function = formatdict['complexfloat']
    elif isinstance(ds, datashape.String):
        format_function = formatdict['numpystr']
    else:
        format_function = formatdict['numpystr']

    return format_function


def _array2string(a, shape, dtype, max_line_width, precision,
                  suppress_small, separator=' ', prefix="", formatter=None):

    if has_var_dim(shape):
        dim_size = -1
    else:
        dim_size = reduce(product, shape, 1)

    if max_line_width is None:
        max_line_width = _line_width

    if precision is None:
        precision = _float_output_precision

    if suppress_small is None:
        suppress_small = _float_output_suppress_small

    if formatter is None:
        formatter = _formatter

    if dim_size > _summaryThreshold:
        summary_insert = "..., "
        data = ravel(np.array(_leading_trailing(a)))
    else:
        summary_insert = ""
        data = ravel(np.array(ddesc_as_py(a)))

    formatdict = {'bool': _boolFormatter,
                  'int': IntegerFormat(data),
                  'float': FloatFormat(data, precision, suppress_small),
                  'complexfloat': ComplexFormat(data, precision,
                                                suppress_small),
                  'numpystr': repr_format,
                  'str': str}

    if formatter is not None:
        _apply_formatter(formatdict, formatter)

    assert(not hasattr(a, '_format'))

    # find the right formatting function for the array
    format_function = _choose_format(formatdict, dtype)

    # skip over "["
    next_line_prefix = " "
    # skip over array(
    next_line_prefix += " "*len(prefix)

    lst = _formatArray(a, format_function, len(shape), max_line_width,
                       next_line_prefix, separator,
                       _summaryEdgeItems, summary_insert).rstrip()
    return lst


def _convert_arrays(obj):
    import numpy.core.numeric as _nc
    newtup = []
    for k in obj:
        if isinstance(k, _nc.ndarray):
            k = k.tolist()
        elif isinstance(k, tuple):
            k = _convert_arrays(k)
        newtup.append(k)
    return tuple(newtup)


def array2string(a, max_line_width=None, precision=None,
                 suppress_small=None, separator=' ', prefix="",
                 style=repr, formatter=None):
    """
    Return a string representation of an array.

    Parameters
    ----------
    a : ndarray
        Input array.
    max_line_width : int, optional
        The maximum number of columns the string should span. Newline
        characters splits the string appropriately after array elements.
    precision : int, optional
        Floating point precision. Default is the current printing
        precision (usually 8), which can be altered using `set_printoptions`.
    suppress_small : bool, optional
        Represent very small numbers as zero. A number is "very small" if it
        is smaller than the current printing precision.
    separator : str, optional
        Inserted between elements.
    prefix : str, optional
        An array is typically printed as::

          'prefix(' + array2string(a) + ')'

        The length of the prefix string is used to align the
        output correctly.
    style : function, optional
        A function that accepts an ndarray and returns a string.  Used only
        when the shape of `a` is equal to ``()``, i.e. for 0-D arrays.
    formatter : dict of callables, optional
        If not None, the keys should indicate the type(s) that the respective
        formatting function applies to.  Callables should return a string.
        Types that are not specified (by their corresponding keys) are handled
        by the default formatters.  Individual types for which a formatter
        can be set are::

            - 'bool'
            - 'int'
            - 'float'
            - 'complexfloat'
            - 'longcomplexfloat' : composed of two 128-bit floats
            - 'numpy_str' : types `numpy.string_` and `numpy.unicode_`
            - 'str' : all other strings

        Other keys that can be used to set a group of types at once are::

            - 'all' : sets all types
            - 'int_kind' : sets 'int'
            - 'float_kind' : sets 'float'
            - 'complex_kind' : sets 'complexfloat' and 'longcomplexfloat'
            - 'str_kind' : sets 'str' and 'numpystr'

    Returns
    -------
    array_str : str
        String representation of the array.

    Raises
    ------
    TypeError : if a callable in `formatter` does not return a string.

    See Also
    --------
    array_str, array_repr, set_printoptions, get_printoptions

    Notes
    -----
    If a formatter is specified for a certain type, the `precision` keyword is
    ignored for that type.

    Examples
    --------
    >>> x = np.array([1e-16,1,2,3])
    >>> print(np.array2string(x, precision=2, separator=',',
    ...                       suppress_small=True))
    [ 0., 1., 2., 3.]

    >>> x  = np.arange(3.)
    >>> np.array2string(x, formatter={'float_kind':lambda x: "%.2f" % x})
    '[0.00 1.00 2.00]'

    >>> x  = np.arange(3)
    >>> np.array2string(x, formatter={'int':lambda x: hex(x)})
    '[0x0L 0x1L 0x2L]'

    """
    shape, dtype = (a.dshape[:-1], a.dshape[-1])
    shape = tuple(int(x) if isinstance(x, Fixed) else x for x in shape)

    lst = _array2string(a, shape, dtype, max_line_width,
                        precision, suppress_small,
                        separator, prefix, formatter=formatter)
    return lst


def _extendLine(s, line, word, max_line_len, next_line_prefix):
    if len(line.rstrip()) + len(word.rstrip()) >= max_line_len:
        s += line.rstrip() + "\n"
        line = next_line_prefix
    line += word
    return s, line


def _formatArray(a, format_function, rank, max_line_len,
                 next_line_prefix, separator, edge_items, summary_insert):
    """formatArray is designed for two modes of operation:

    1. Full output

    2. Summarized output

    """
    if rank == 0:
        return format_function(ddesc_as_py(a)).strip()

    if summary_insert and 2*edge_items < len(a):
        leading_items = edge_items
        trailing_items = edge_items
        summary_insert1 = summary_insert
    else:
        leading_items, trailing_items, summary_insert1 = 0, len(a), ""

    if rank == 1:
        s = ""
        line = next_line_prefix
        for i in xrange(leading_items):
            word = format_function(ddesc_as_py(a[i])) + separator
            s, line = _extendLine(s, line, word, max_line_len,
                                  next_line_prefix)

        if summary_insert1:
            s, line = _extendLine(s, line, summary_insert1,
                                  max_line_len, next_line_prefix)

        for i in xrange(trailing_items, 1, -1):
            word = format_function(ddesc_as_py(a[-i])) + separator
            s, line = _extendLine(s, line, word, max_line_len,
                                  next_line_prefix)

        if len(a) > 0:
            word = format_function(ddesc_as_py(a[-1]))
            s, line = _extendLine(s, line, word, max_line_len, next_line_prefix)

        s += line + "]\n"
        s = '[' + s[len(next_line_prefix):]
    else:
        s = '['
        sep = separator.rstrip()
        for i in xrange(leading_items):
            if i > 0:
                s += next_line_prefix
            s += _formatArray(a[i], format_function, rank-1, max_line_len,
                              " " + next_line_prefix, separator, edge_items,
                              summary_insert)
            s = s.rstrip() + sep.rstrip() + '\n'*max(rank-1, 1)

        if summary_insert1:
            s += next_line_prefix + summary_insert1 + "\n"

        for i in xrange(trailing_items, 1, -1):
            if leading_items or i != trailing_items:
                s += next_line_prefix
            s += _formatArray(a[-i], format_function, rank-1, max_line_len,
                              " " + next_line_prefix, separator, edge_items,
                              summary_insert)
            s = s.rstrip() + sep.rstrip() + '\n'*max(rank-1, 1)
        if leading_items or trailing_items > 1:
            s += next_line_prefix
        s += _formatArray(a[-1], format_function, rank-1, max_line_len,
                          " " + next_line_prefix, separator, edge_items,
                          summary_insert).rstrip()+']\n'
    return s


class FloatFormat(object):
    def __init__(self, data, precision, suppress_small, sign=False):
        self.precision = precision
        self.suppress_small = suppress_small
        self.sign = sign
        self.exp_format = False
        self.large_exponent = False
        self.max_str_len = 0
        if data.dtype.kind in ['f', 'i', 'u']:
            self.fillFormat(data)

    def fillFormat(self, data):
        import numpy.core.numeric as _nc
        errstate = _nc.seterr(all='ignore')
        try:
            special = isnan(data) | isinf(data)
            valid = not_equal(data, 0) & ~special
            non_zero = absolute(data.compress(valid))
            if len(non_zero) == 0:
                max_val = 0.
                min_val = 0.
            else:
                max_val = maximum.reduce(non_zero)
                min_val = minimum.reduce(non_zero)
                if max_val >= 1.e8:
                    self.exp_format = True
                if not self.suppress_small and (min_val < 0.0001
                                                or max_val/min_val > 1000.):
                    self.exp_format = True
        finally:
            _nc.seterr(**errstate)

        if self.exp_format:
            self.large_exponent = 0 < min_val < 1e-99 or max_val >= 1e100
            self.max_str_len = 8 + self.precision
            if self.large_exponent:
                self.max_str_len += 1
            if self.sign:
                format = '%+'
            else:
                format = '%'
            format = format + '%d.%de' % (self.max_str_len, self.precision)
        else:
            format = '%%.%df' % (self.precision,)
            if len(non_zero):
                precision = max([_digits(x, self.precision, format)
                                 for x in non_zero])
            else:
                precision = 0
            precision = min(self.precision, precision)
            self.max_str_len = len(str(int(max_val))) + precision + 2
            if _nc.any(special):
                self.max_str_len = max(self.max_str_len,
                                       len(_nan_str),
                                       len(_inf_str)+1)
            if self.sign:
                format = '%#+'
            else:
                format = '%#'
            format = format + '%d.%df' % (self.max_str_len, precision)

        self.special_fmt = '%%%ds' % (self.max_str_len,)
        self.format = format

    def __call__(self, x, strip_zeros=True):
        import numpy.core.numeric as _nc
        err = _nc.seterr(invalid='ignore')

        try:
            if isnan(x):
                if self.sign:
                    return self.special_fmt % ('+' + _nan_str,)
                else:
                    return self.special_fmt % (_nan_str,)
            elif isinf(x):
                if x > 0:
                    if self.sign:
                        return self.special_fmt % ('+' + _inf_str,)
                    else:
                        return self.special_fmt % (_inf_str,)
                else:
                    return self.special_fmt % ('-' + _inf_str,)
        finally:
            _nc.seterr(**err)

        s = self.format % x
        if self.large_exponent:
            # 3-digit exponent
            expsign = s[-3]
            if expsign == '+' or expsign == '-':
                s = s[1:-2] + '0' + s[-2:]
        elif self.exp_format:
            # 2-digit exponent
            if s[-3] == '0':
                s = ' ' + s[:-3] + s[-2:]
        elif strip_zeros:
            z = s.rstrip('0')
            s = z + ' '*(len(s)-len(z))
        return s


def _digits(x, precision, format):
    s = format % x
    z = s.rstrip('0')
    return precision - len(s) + len(z)


if sys.version_info >= (3, 0):
    _MAXINT = 2**32 - 1
    _MININT = -2**32
else:
    _MAXINT = sys.maxint
    _MININT = -sys.maxint-1


class IntegerFormat(object):
    def __init__(self, data):
        try:
            max_str_len = max(len(str(maximum.reduce(data))),
                              len(str(minimum.reduce(data))))
            self.format = '%' + str(max_str_len) + 'd'
        except (TypeError, NotImplementedError):
            # if reduce(data) fails, this instance will not be called, just
            # instantiated in formatdict.
            pass
        except ValueError:
            # this occurs when everything is NA
            pass

    def __call__(self, x):
        if _MININT < x < _MAXINT:
            return self.format % x
        else:
            return "%s" % x


class ComplexFormat(object):
    def __init__(self, x, precision, suppress_small):
        self.real_format = FloatFormat(x.real, precision, suppress_small)
        self.imag_format = FloatFormat(x.imag, precision, suppress_small,
                                       sign=True)

    def __call__(self, x):
        r = self.real_format(x.real, strip_zeros=False)
        i = self.imag_format(x.imag, strip_zeros=False)
        if not self.imag_format.exp_format:
            z = i.rstrip('0')
            i = z + 'j' + ' '*(len(i)-len(z))
        else:
            i = i + 'j'
        return r + i


def _test():
    import blaze

    arr = blaze.array([2, 3, 4.0])
    print(arr.dshape)

    print(array2string(arr.ddesc))

    arr = blaze.zeros('30, 30, 30, float32')
    print(arr.dshape)

    print(array2string(arr.ddesc))

########NEW FILE########
__FILENAME__ = array
"""This file defines the Concrete Array --- a leaf node in the expression graph

A concrete array is constructed from a Data Descriptor Object which handles the
 indexing and basic interpretation of bytes
"""

from __future__ import absolute_import, division, print_function

import datashape

from ..compute.ops import ufuncs
from .. import compute

from ..datadescriptor import (DDesc, Deferred_DDesc, Stream_DDesc, ddesc_as_py)
from ..io import _printing


class Array(object):
    """An Array contains:

        DDesc
        Sequence of Bytes (where are the bytes)
        Index Object (how do I get to them)
        Data Shape Object (what are the bytes? how do I interpret them)
        axis and dimension labels
        user-defined meta-data (whatever are needed --- provenance propagation)
    """
    def __init__(self, data, axes=None, labels=None, user={}):
        if not isinstance(data, DDesc):
            raise TypeError(('Constructing a blaze array directly '
                            'requires a data descriptor, not type '
                            '%r') % (type(data)))
        self.ddesc = data
        self.axes = axes or [''] * (len(self.ddesc.dshape) - 1)
        self.labels = labels or [None] * (len(self.ddesc.dshape) - 1)
        self.user = user
        self.expr = None

        if isinstance(data, Deferred_DDesc):
            # NOTE: we need 'expr' on the Array to perform dynamic programming:
            #       Two concrete arrays should have a single Op! We cannot
            #       store this in the data descriptor, since there are many
            self.expr = data.expr  # hurgh

        # Inject the record attributes.
        injected_props = {}
        # This is a hack to help get the blaze-web server onto blaze arrays.
        ds = data.dshape
        ms = ds[-1] if isinstance(ds, datashape.DataShape) else ds
        if isinstance(ms, datashape.Record):
            for name in ms.names:
                injected_props[name] = _named_property(name)

        # Need to inject attributes on the Array depending on dshape
        # attributes, in cases other than Record
        if data.dshape in [datashape.dshape('int32'),
                           datashape.dshape('int64')]:
            def __int__(self):
                # Evaluate to memory
                e = compute.eval.eval(self)
                return int(e.ddesc.dynd_arr())
            injected_props['__int__'] = __int__
        elif data.dshape in [datashape.dshape('float32'),
                             datashape.dshape('float64')]:
            def __float__(self):
                # Evaluate to memory
                e = compute.eval.eval(self)
                return float(e.ddesc.dynd_arr())
            injected_props['__float__'] = __float__
        elif ms in [datashape.complex_float32, datashape.complex_float64]:
            if len(data.dshape) == 1:
                def __complex__(self):
                    # Evaluate to memory
                    e = compute.eval.eval(self)
                    return complex(e.ddesc.dynd_arr())
                injected_props['__complex__'] = __complex__
            injected_props['real'] = _ufunc_to_property(ufuncs.real)
            injected_props['imag'] = _ufunc_to_property(ufuncs.imag)
        elif ms == datashape.date_:
            injected_props['year'] = _ufunc_to_property(ufuncs.year)
            injected_props['month'] = _ufunc_to_property(ufuncs.month)
            injected_props['day'] = _ufunc_to_property(ufuncs.day)
        elif ms == datashape.time_:
            injected_props['hour'] = _ufunc_to_property(ufuncs.hour)
            injected_props['minute'] = _ufunc_to_property(ufuncs.minute)
            injected_props['second'] = _ufunc_to_property(ufuncs.second)
            injected_props['microsecond'] = _ufunc_to_property(ufuncs.microsecond)
        elif ms == datashape.datetime_:
            injected_props['date'] = _ufunc_to_property(ufuncs.date)
            injected_props['time'] = _ufunc_to_property(ufuncs.time)
            injected_props['year'] = _ufunc_to_property(ufuncs.year)
            injected_props['month'] = _ufunc_to_property(ufuncs.month)
            injected_props['day'] = _ufunc_to_property(ufuncs.day)
            injected_props['hour'] = _ufunc_to_property(ufuncs.hour)
            injected_props['minute'] = _ufunc_to_property(ufuncs.minute)
            injected_props['second'] = _ufunc_to_property(ufuncs.second)
            injected_props['microsecond'] = _ufunc_to_property(ufuncs.microsecond)

        if injected_props:
            self.__class__ = type('Array', (Array,), injected_props)


    @property
    def dshape(self):
        return self.ddesc.dshape

    @property
    def deferred(self):
        return self.ddesc.capabilities.deferred


    def __array__(self):
        import numpy as np

        # TODO: Expose PEP-3118 buffer interface

        if hasattr(self.ddesc, "__array__"):
            return np.array(self.ddesc)

        return np.array(self.ddesc.dynd_arr())

    def __iter__(self):
        if len(self.dshape.shape) == 1:
            return (ddesc_as_py(dd) for dd in self.ddesc)
        return (Array(dd) for dd in self.ddesc)

    def __getitem__(self, key):
        dd = self.ddesc.__getitem__(key)

        # Single element?
        if not self.deferred and not dd.dshape.shape:
            return ddesc_as_py(dd)
        else:
            return Array(dd)

    def __setitem__(self, key, val):
        self.ddesc.__setitem__(key, val)

    def __len__(self):
        shape = self.dshape.shape
        if shape:
            return shape[0]
        raise IndexError('Scalar blaze arrays have no length')

    def __nonzero__(self):
        # For Python 2
        if len(self.dshape.shape) == 0:
            # Evaluate to memory
            e = compute.eval.eval(self)
            return bool(e.ddesc.dynd_arr())
        else:
            raise ValueError("The truth value of an array with more than one "
                             "element is ambiguous. Use a.any() or a.all()")

    def __bool__(self):
        # For Python 3
        if len(self.dshape.shape) == 0:
            # Evaluate to memory
            e = compute.eval.eval(self)
            return bool(e.ddesc.dynd_arr())
        else:
            raise ValueError("The truth value of an array with more than one "
                             "element is ambiguous. Use a.any() or a.all()")

    def __str__(self):
        if hasattr(self.ddesc, '_printer'):
            return self.ddesc._printer()
        return _printing.array_str(self)

    def __repr__(self):
        if hasattr(self.ddesc, "_printer_repr"):
            return self.ddesc._printer_repr()
        return _printing.array_repr(self)

    def where(self, condition):
        """Iterate over values fulfilling a condition."""
        if self.ddesc.capabilities.queryable:
            iterator = self.ddesc.where(condition)
            ddesc = Stream_DDesc(iterator, self.dshape, condition)
            return Array(ddesc)
        else:
            raise ValueError(
                'Data descriptor do not support efficient queries')


def _named_property(name):
    @property
    def getprop(self):
        return Array(self.ddesc.getattr(name))
    return getprop


def _ufunc_to_property(uf):
    @property
    def getprop(self):
        return uf(self)
    return getprop


def binding(f):
    def binder(self, *args):
        return f(self, *args)
    return binder


def __rufunc__(f):
    def __rop__(self, other):
        return f(other, self)
    return __rop__


def _inject_special_binary(names):
    for ufunc_name, special_name in names:
        ufunc = getattr(ufuncs, ufunc_name)
        setattr(Array, '__%s__' % special_name, binding(ufunc))
        setattr(Array, '__r%s__' % special_name, binding(__rufunc__(ufunc)))


def _inject_special(names):
    for ufunc_name, special_name in names:
        ufunc = getattr(ufuncs, ufunc_name)
        setattr(Array, '__%s__' % special_name, binding(ufunc))


_inject_special_binary([
    ('add', 'add'),
    ('subtract', 'sub'),
    ('multiply', 'mul'),
    ('true_divide', 'truediv'),
    ('mod', 'mod'),
    ('floor_divide', 'floordiv'),
    ('equal', 'eq'),
    ('not_equal', 'ne'),
    ('greater', 'gt'),
    ('greater_equal', 'ge'),
    ('less_equal', 'le'),
    ('less', 'lt'),
    ('divide', 'div'),
    ('bitwise_and', 'and'),
    ('bitwise_or', 'or'),
    ('bitwise_xor', 'xor'),
    ('power', 'pow'),
    ])
_inject_special([
    ('bitwise_not', 'invert'),
    ('negative', 'neg'),
    ])


"""
These should be functions

    @staticmethod
    def fromfiles(list_of_files, converters):
        raise NotImplementedError

    @staticmethod
    def fromfile(file, converter):
        raise NotImplementedError

    @staticmethod
    def frombuffers(list_of_buffers, converters):
        raise NotImplementedError

    @staticmethod
    def frombuffer(buffer, converter):
        raise NotImplementedError

    @staticmethod
    def fromobjects():
        raise NotImplementedError

    @staticmethod
    def fromiterator(buffer):
        raise NotImplementedError

"""


########NEW FILE########
__FILENAME__ = constructors
"""Constructors for the blaze array object.

Having them as external functions allows to more flexibility and helps keeping
the blaze array object compact, just showing the interface of the
array itself.

The blaze array __init__ method should be considered private and for
advanced users only. It will provide the tools supporting the rest
of the constructors, and will use low-level parameters, like
ByteProviders, that an end user may not even need to know about.
"""

from __future__ import absolute_import, division, print_function

import inspect

from dynd import nd, ndt
import numpy as np
import datashape
from datashape import to_numpy, to_numpy_dtype
import blz

from ..optional_packages import tables_is_here
if tables_is_here:
    import tables as tb

from .array import Array
from ..datadescriptor import (
    DDesc, DyND_DDesc, BLZ_DDesc, HDF5_DDesc)
from ..py2help import basestring


def split_path(dp):
    """Split a path in basedir path and end part for HDF5 purposes"""
    idx = dp.rfind('/')
    where = dp[:idx] if idx > 0 else '/'
    name = dp[idx+1:]
    return where, name


def _normalize_dshape(ds):
    """
    In the API, when a datashape is provided we want to support
    them in string form as well. This function will convert from any
    form we want to support in the API inputs into the internal
    datashape object, so the logic is centralized in a single
    place. Any API function that receives a dshape as a parameter
    should convert it using this function.
    """
    if isinstance(ds, basestring):
        return datashape.dshape(ds)
    else:
        return ds


def array(obj, dshape=None, ddesc=None):
    """Create a Blaze array.

    Parameters
    ----------
    obj : array_like
        Initial contents for the array.

    dshape : datashape
        The datashape for the resulting array. By default the
        datashape will be inferred from data. If an explicit dshape is
        provided, the input data will be coerced into the provided
        dshape.

    ddesc : data descriptor instance
        This comes with the necessary info for storing the data.  If
        None, a DyND_DDesc will be used.

    Returns
    -------
    out : a concrete blaze array.

    """
    dshape = _normalize_dshape(dshape)

    if ((obj is not None) and
        (not inspect.isgenerator(obj)) and
        (dshape is not None)):
        dt = ndt.type(str(dshape))
        if dt.ndim > 0:
            obj = nd.array(obj, type=dt, access='rw')
        else:
            obj = nd.array(obj, dtype=dt, access='rw')

    if obj is None and ddesc is None:
        raise ValueError('you need to specify at least `obj` or `ddesc`')

    if isinstance(obj, Array):
        return obj
    elif isinstance(obj, DDesc):
        if ddesc is None:
            ddesc = obj
            return Array(ddesc)
        else:
            raise ValueError(('you cannot specify `ddesc` when `obj` '
                              'is already a DDesc instance'))

    if ddesc is None:
        # Use a dynd ddesc by default
        try:
            array = nd.asarray(obj, access='rw')
        except:
            raise ValueError(('failed to construct a dynd array from '
                              'object %r') % obj)
        ddesc = DyND_DDesc(array)
        return Array(ddesc)

    # The DDesc has been specified
    if isinstance(ddesc, DyND_DDesc):
        if obj is not None:
            raise ValueError(('you cannot specify simultaneously '
                              '`obj` and a DyND `ddesc`'))
        return Array(ddesc)
    elif isinstance(ddesc, BLZ_DDesc):
        if inspect.isgenerator(obj):
            dt = None if dshape is None else to_numpy_dtype(dshape)
            # TODO: Generator logic could go inside barray
            ddesc.blzarr = blz.fromiter(obj, dtype=dt, count=-1,
                                        rootdir=ddesc.path, mode=ddesc.mode,
                                        **ddesc.kwargs)
        else:
            if isinstance(obj, nd.array):
                obj = nd.as_numpy(obj)
            if dshape and isinstance(dshape.measure, datashape.Record):
                ddesc.blzarr = blz.btable(
                    obj, rootdir=ddesc.path, mode=ddesc.mode, **ddesc.kwargs)
            else:
                ddesc.blzarr = blz.barray(
                    obj, rootdir=ddesc.path, mode=ddesc.mode, **ddesc.kwargs)
    elif isinstance(ddesc, HDF5_DDesc):
        if isinstance(obj, nd.array):
            obj = nd.as_numpy(obj)
        with tb.open_file(ddesc.path, mode=ddesc.mode) as f:
            where, name = split_path(ddesc.datapath)
            if dshape and isinstance(dshape.measure, datashape.Record):
                # Convert the structured array to unaligned dtype
                # We need that because PyTables only accepts unaligned types,
                # which are the default in NumPy
                obj = np.array(obj, datashape.to_numpy_dtype(dshape.measure))
                f.create_table(where, name, filters=ddesc.filters, obj=obj)
            else:
                f.create_earray(where, name, filters=ddesc.filters, obj=obj)
        ddesc.mode = 'a'  # change into 'a'ppend mode for further operations

    return Array(ddesc)


# TODO: Make overloaded constructors, taking dshape, **kwds. Overload
# on keywords

def empty(dshape, ddesc=None):
    """Create an array with uninitialized data.

    Parameters
    ----------
    dshape : datashape
        The datashape for the resulting array.

    ddesc : data descriptor instance
        This comes with the necessary info for storing the data.  If
        None, a DyND_DDesc will be used.

    Returns
    -------
    out : a concrete blaze array.

    """
    dshape = _normalize_dshape(dshape)

    if ddesc is None:
        ddesc = DyND_DDesc(nd.empty(str(dshape)))
        return Array(ddesc)
    if isinstance(ddesc, BLZ_DDesc):
        shape, dt = to_numpy(dshape)
        ddesc.blzarr = blz.zeros(shape, dt, rootdir=ddesc.path,
                                 mode=ddesc.mode, **ddesc.kwargs)
    elif isinstance(ddesc, HDF5_DDesc):
        obj = nd.as_numpy(nd.empty(str(dshape)))
        with tb.open_file(ddesc.path, mode=ddesc.mode) as f:
            where, name = split_path(ddesc.datapath)
            f.create_earray(where, name, filters=ddesc.filters, obj=obj)
        ddesc.mode = 'a'  # change into 'a'ppend mode for further operations
    return Array(ddesc)


def zeros(dshape, ddesc=None):
    """Create an array and fill it with zeros.

    Parameters
    ----------
    dshape : datashape
        The datashape for the resulting array.

    ddesc : data descriptor instance
        This comes with the necessary info for storing the data.  If
        None, a DyND_DDesc will be used.

    Returns
    -------
    out : a concrete blaze array.

    """
    dshape = _normalize_dshape(dshape)

    if ddesc is None:
        ddesc = DyND_DDesc(nd.zeros(str(dshape), access='rw'))
        return Array(ddesc)
    if isinstance(ddesc, BLZ_DDesc):
        shape, dt = to_numpy(dshape)
        ddesc.blzarr = blz.zeros(
            shape, dt, rootdir=ddesc.path, mode=ddesc.mode, **ddesc.kwargs)
    elif isinstance(ddesc, HDF5_DDesc):
        obj = nd.as_numpy(nd.zeros(str(dshape)))
        with tb.open_file(ddesc.path, mode=ddesc.mode) as f:
            where, name = split_path(ddesc.datapath)
            f.create_earray(where, name, filters=ddesc.filters, obj=obj)
        ddesc.mode = 'a'  # change into 'a'ppend mode for further operations
    return Array(ddesc)


def ones(dshape, ddesc=None):
    """Create an array and fill it with ones.

    Parameters
    ----------
    dshape : datashape
        The datashape for the resulting array.

    ddesc : data descriptor instance
        This comes with the necessary info for storing the data.  If
        None, a DyND_DDesc will be used.

    Returns
    -------
    out: a concrete blaze array.

    """
    dshape = _normalize_dshape(dshape)

    if ddesc is None:
        ddesc = DyND_DDesc(nd.ones(str(dshape), access='rw'))
        return Array(ddesc)
    if isinstance(ddesc, BLZ_DDesc):
        shape, dt = to_numpy(dshape)
        ddesc.blzarr = blz.ones(
            shape, dt, rootdir=ddesc.path, mode=ddesc.mode, **ddesc.kwargs)
    elif isinstance(ddesc, HDF5_DDesc):
        obj = nd.as_numpy(nd.empty(str(dshape)))
        with tb.open_file(ddesc.path, mode=ddesc.mode) as f:
            where, name = split_path(ddesc.datapath)
            f.create_earray(where, name, filters=ddesc.filters, obj=obj)
        ddesc.mode = 'a'  # change into 'a'ppend mode for further operations
    return Array(ddesc)

########NEW FILE########
__FILENAME__ = test_array
from blaze import array
import blaze

import unittest

class Test_1D_Array(unittest.TestCase):
    def setUp(self):
        self.a = array([1, 2, 3])

    def test_iter_1d(self):
        self.assertEqual(list(self.a), [1, 2, 3])

    def test_get_element(self):
        self.assertEqual(self.a[1], 2)

    def test_get_element(self):
        assert blaze.all(self.a[1:] == array([2, 3]))


class Test_2D_Array(unittest.TestCase):
    def setUp(self):
        self.a = array([[1, 2, 3],
                        [4, 5, 6],
                        [7, 8, 9]])

    def test_list_list(self):
        self.assertEqual(list(list(self.a)[0]), [1, 2, 3])

    def test_list_elements(self):
        assert blaze.all(list(self.a)[0] == array([1, 2, 3]))
        assert blaze.all(list(self.a)[1] == array([4, 5, 6]))

########NEW FILE########
__FILENAME__ = optional_packages
from __future__ import absolute_import, division, print_function

#######################################################################
# Checks and variables for optional libraries
#######################################################################

# Check for PyTables
try:
    import tables
    tables_is_here = True
except ImportError:
    tables_is_here = False

# Check for netcdf4-python
try:
    import netCDF4
    netCDF4_is_here = True
except ImportError:
    netCDF4_is_here = False

########NEW FILE########
__FILENAME__ = py2help
from __future__ import absolute_import, division, print_function

import sys
import itertools

# Portions of this taken from the six library, licensed as follows.
#
# Copyright (c) 2010-2013 Benjamin Peterson
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


PY2 = sys.version_info[0] == 2

if PY2:
    import __builtin__
    def dict_iteritems(d):
        return d.iteritems()
    xrange = __builtin__.xrange
    from itertools import izip
    unicode = __builtin__.unicode
    basestring = __builtin__.basestring
    reduce = __builtin__.reduce

    _strtypes = (str, unicode)

    _inttypes = (int, long)
    imap = itertools.imap
    import urlparse
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
else:
    def dict_iteritems(d):
        return d.items().__iter__()
    xrange = range
    izip = zip
    _inttypes = (int,)
    _strtypes = (str,)
    unicode = str
    imap = map
    basestring = str
    import urllib.parse as urlparse
    from functools import reduce
    import builtins
    exec_ = getattr(builtins, "exec")

if sys.version_info[:2] >= (2, 7):
    from ctypes import c_ssize_t
    from unittest import skip, skipIf
else:
    import ctypes
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        c_ssize_t = ctypes.c_int32
    else:
        c_ssize_t = ctypes.c_int64
    from nose.plugins.skip import SkipTest
    class skip(object):
        def __init__(self, reason):
            self.reason = reason

        def __call__(self, func):
            from nose.plugins.skip import SkipTest
            def wrapped(*args, **kwargs):
                raise SkipTest("Test %s is skipped because: %s" %
                                (func.__name__, self.reason))
            wrapped.__name__ = func.__name__
            return wrapped
    class skipIf(object):
        def __init__(self, condition, reason):
            self.condition = condition
            self.reason = reason

        def __call__(self, func):
            if self.condition:
                from nose.plugins.skip import SkipTest
                def wrapped(*args, **kwargs):
                    raise SkipTest("Test %s is skipped because: %s" %
                                    (func.__name__, self.reason))
                wrapped.__name__ = func.__name__
                return wrapped
            else:
                return func


########NEW FILE########
__FILENAME__ = common
"""Utilities for the high level Blaze test suite"""

from __future__ import absolute_import, division, print_function

import unittest
import tempfile
import os
import shutil
import glob


# Useful superclass for disk-based tests
class MayBePersistentTest():

    disk = False
    dir_ = False

    def setUp(self):
        if self.disk:
            if self.dir_:
                prefix = 'barray-' + self.__class__.__name__
                self.rootdir = tempfile.mkdtemp(prefix=prefix)
                os.rmdir(self.rootdir)  # tests needs this cleared
            else:
                handle, self.file = tempfile.mkstemp()
                os.close(handle)  # close the non needed file handle
        else:
            self.rootdir = None

    def tearDown(self):
        if self.disk:
            if self.dir_:
                # Remove every directory starting with rootdir
                for dir_ in glob.glob(self.rootdir+'*'):
                    shutil.rmtree(dir_)
            else:
                os.unlink(self.file)


class BTestCase(unittest.TestCase):
    """
    TestCase that provides some stuff missing in 2.6.
    """

    def assertIsInstance(self, obj, cls, msg=None):
        self.assertTrue(isinstance(obj, cls),
                        msg or "%s is not an instance of %s" % (obj, cls))

    def assertGreater(self, a, b, msg=None):
        self.assertTrue(a > b, msg or "%s is not greater than %s" % (a, b))

    def assertLess(self, a, b, msg=None):
        self.assertTrue(a < b, msg or "%s is not greater than %s" % (a, b))

########NEW FILE########
__FILENAME__ = test_array_creation
from __future__ import absolute_import, division, print_function

import unittest

import numpy as np
import datashape
import blaze
from blaze.tests.common import MayBePersistentTest
from blaze import (append,
    DyND_DDesc, BLZ_DDesc, HDF5_DDesc)


from blaze.py2help import skip, skipIf
import blz

from blaze.optional_packages import tables_is_here
if tables_is_here:
    import tables as tb


class TestEphemeral(unittest.TestCase):
    def test_create_scalar(self):
        a = blaze.array(True)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(a.dshape, datashape.dshape('bool'))
        self.assertEqual(bool(a), True)
        a = blaze.array(-123456)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(a.dshape, datashape.dshape('int32'))
        self.assertEqual(int(a), -123456)
        a = blaze.array(-1.25e-10)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(a.dshape, datashape.dshape('float64'))
        self.assertEqual(float(a), -1.25e-10)
        a = blaze.array(-1.25e-10+2.5j)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(a.dshape, datashape.dshape('complex[float64]'))
        self.assertEqual(complex(a), -1.25e-10+2.5j)

    def test_create_from_numpy(self):
        a = blaze.array(np.arange(3))
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(list(a), [0, 1, 2])

    def test_create(self):
        # A default array (backed by DyND)
        a = blaze.array([1,2,3])
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertTrue(str(a.dshape) == "3 * int32")
        self.assertEqual(list(a), [1, 2, 3])

    def test_create_dshape(self):
        # A default array (backed by DyND)
        a = blaze.array([1,2,3], 'float64')
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertTrue(str(a.dshape) == "3 * float64")
        self.assertEqual(list(a), [1, 2, 3])

    def test_create_append(self):
        # A default array (backed by DyND, append not supported yet)
        a = blaze.array([])
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertRaises(ValueError, append, a, [1,2,3])

    def test_create_compress(self):
        # A compressed array (backed by BLZ)
        ddesc = BLZ_DDesc(mode='w', bparams=blz.bparams(clevel=5))
        a = blaze.array(np.arange(1,4), ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(list(a), [1, 2, 3])

    def test_create_iter(self):
        # A simple 1D array
        a = blaze.array(i for i in range(10))
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(a.dshape, datashape.dshape('10 * int32'))
        self.assertEqual(list(a), list(range(10)))
        # A nested iter
        a = blaze.array((i for i in range(x)) for x in range(5))
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(a.dshape, datashape.dshape('5 * var * int32'))
        self.assertEqual([list(x) for x in a],
                         [[i for i in range(x)] for x in range(5)])
        # A list of iter
        a = blaze.array([range(3), (1.5*x for x in range(4)), iter([-1, 1])])
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(a.dshape, datashape.dshape('3 * var * float64'))
        self.assertEqual([list(x) for x in a],
                         [list(range(3)),
                          [1.5*x for x in range(4)],
                          [-1, 1]])

    def test_create_compress_iter(self):
        # A compressed array (backed by BLZ)
        ddesc = BLZ_DDesc(mode='w', bparams=blz.bparams(clevel=5))
        a = blaze.array((i for i in range(10)), ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(list(a), list(range(10)))

    def test_create_zeros(self):
        # A default array
        a = blaze.zeros('10 * int64')
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(list(a), [0]*10)

    def test_create_compress_zeros(self):
        # A compressed array (backed by BLZ)
        ddesc = BLZ_DDesc(mode='w', bparams=blz.bparams(clevel=5))
        a = blaze.zeros('10 * int64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(list(a), [0]*10)

    def test_create_ones(self):
        # A default array
        a = blaze.ones('10 * int64')
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(list(a), [1]*10)

    def test_create_compress_ones(self):
        # A compressed array (backed by BLZ)
        ddesc = BLZ_DDesc(mode='w', bparams=blz.bparams(clevel=5))
        a = blaze.ones('10 * int64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertEqual(list(a), [1]*10)

    def test_create_record(self):
        # A simple record array
        a = blaze.array([(10, 3.5), (15, 2.25)],
                        dshape="var * {val: int32, flt: float32}")
        self.assertEqual(list(a), [{'val': 10, 'flt': 3.5},
                        {'val': 15, 'flt': 2.25}])
        # Test field access via attributes
        aval = a.val
        self.assertEqual(list(aval), [10, 15])
        aflt = a.flt
        self.assertEqual(list(aflt), [3.5, 2.25])

    def test_create_record_compress(self):
        # A simple record array (backed by BLZ)
        ddesc = BLZ_DDesc(mode='w')
        a = blaze.array([(10, 3.5), (15, 2.25)],
                        dshape="var * {val: int32, flt: float32}",
                        ddesc=ddesc)
        self.assertEqual(list(a), [{'val': 10, 'flt': 3.5},
                                   {'val': 15, 'flt': 2.25}])
        # Test field access via attributes
        aval = a.val
        self.assertEqual(list(aval), [10, 15])
        aflt = a.flt
        self.assertEqual(list(aflt), [3.5, 2.25])


class TestBLZPersistent(MayBePersistentTest, unittest.TestCase):

    disk = True
    dir_ = True

    def test_create(self):
        ddesc = BLZ_DDesc(path=self.rootdir, mode='w')
        a = blaze.array([2], 'float64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertTrue(a.dshape.shape == (1,))
        self.assertEqual(list(a), [2])

    def test_create_record(self):
        ddesc = BLZ_DDesc(path=self.rootdir, mode='w')
        a = blaze.array([(1,2)], '{x: int, y: real}', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertTrue(a.dshape.shape == (1,))
        self.assertEqual(list(a), [{'x': 1, 'y': 2.0}])

    def test_append(self):
        ddesc = BLZ_DDesc(path=self.rootdir, mode='w')
        a = blaze.zeros('0 * float64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        append(a, list(range(10)))
        self.assertEqual(list(a), list(range(10)))

    # Using a 1-dim as the internal dimension
    def test_append2(self):
        ddesc = BLZ_DDesc(path=self.rootdir, mode='w')
        a = blaze.empty('0 * 2 * float64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        lvals = [[i,i*2] for i in range(10)]
        append(a, lvals)
        self.assertEqual([list(i) for i in a], lvals)


class TestHDF5Persistent(MayBePersistentTest, unittest.TestCase):

    disk = True

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_create(self):
        ddesc = HDF5_DDesc(path=self.file, datapath='/earray', mode='w')
        a = blaze.array([2], 'float64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertTrue(a.dshape.shape == (1,))
        self.assertEqual(list(a), [2])

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_create_record(self):
        ddesc = HDF5_DDesc(path=self.file, datapath='/table', mode='w')
        a = blaze.array([(10, 3.5), (15, 2.25)],
                        dshape="var * {val: int32, flt: float32}",
                        ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        self.assertTrue(a.dshape.shape == (2,))
        self.assertEqual(list(a),
                        [{u'flt': 3.5, u'val': 10},
                         {u'flt': 2.25, u'val': 15}] )
        # Test field access via attributes
        aval = a.val
        self.assertEqual(list(aval), [10, 15])
        aflt = a.flt
        self.assertEqual(list(aflt), [3.5, 2.25])

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_append(self):
        ddesc = HDF5_DDesc(path=self.file, datapath='/earray', mode='a')
        a = blaze.zeros('0 * float64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        append(a, list(range(10)))
        self.assertEqual(list(a), list(range(10)))

    # Using a 1-dim as the internal dimension
    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_append2(self):
        ddesc = HDF5_DDesc(path=self.file, datapath='/earray', mode='a')
        a = blaze.empty('0 * 2 * float64', ddesc=ddesc)
        self.assertTrue(isinstance(a, blaze.Array))
        lvals = [[i,i*2] for i in range(10)]
        append(a, lvals)
        self.assertEqual([list(i) for i in a], lvals)



if __name__ == '__main__':
    unittest.main(verbosity=2)

########NEW FILE########
__FILENAME__ = test_array_opening
from __future__ import absolute_import, division, print_function

import os
import tempfile
import unittest

import blaze
from blaze.py2help import skip, skipIf
from blaze.datadescriptor import ddesc_as_py
from blaze.tests.common import MayBePersistentTest
from blaze import (append,
    DyND_DDesc, BLZ_DDesc, HDF5_DDesc, CSV_DDesc, JSON_DDesc)

from blaze.optional_packages import tables_is_here
if tables_is_here:
    import tables as tb


# A CSV toy example
csv_buf = u"""k1,v1,1,False
k2,v2,2,True
k3,v3,3,False
"""
csv_schema = "{ f0: string, f1: string, f2: int16, f3: bool }"
csv_ldict =  [
    {u'f0': u'k1', u'f1': u'v1', u'f2': 1, u'f3': False},
    {u'f0': u'k2', u'f1': u'v2', u'f2': 2, u'f3': True},
    {u'f0': u'k3', u'f1': u'v3', u'f2': 3, u'f3': False}
    ]


class TestOpenCSV(unittest.TestCase):

    def setUp(self):
        handle, self.fname = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(handle, "w") as f:
            f.write(csv_buf)

    def tearDown(self):
        os.unlink(self.fname)

    def test_open(self):
        ddesc = CSV_DDesc(self.fname, mode='r', schema=csv_schema)
        a = blaze.array(ddesc)
        self.assert_(isinstance(a, blaze.Array))
        self.assertEqual(ddesc_as_py(a.ddesc), csv_ldict)

    def test_from_dialect(self):
        ddesc = CSV_DDesc(self.fname, mode='r',
                          schema=csv_schema, dialect='excel')
        a = blaze.array(ddesc)
        self.assert_(isinstance(a, blaze.Array))
        self.assertEqual(ddesc_as_py(a.ddesc), csv_ldict)

    def test_from_has_header(self):
        ddesc = CSV_DDesc(
            self.fname, mode='r', schema=csv_schema, has_header=False)
        a = blaze.array(ddesc)
        self.assert_(isinstance(a, blaze.Array))
        self.assertEqual(ddesc_as_py(a.ddesc), csv_ldict)

    def test_append(self):
        ddesc = CSV_DDesc(self.fname, mode='r+', schema=csv_schema)
        a = blaze.array(ddesc)
        blaze.append(a, ["k4", "v4", 4, True])
        self.assertEqual(ddesc_as_py(a.ddesc), csv_ldict + \
            [{u'f0': u'k4', u'f1': u'v4', u'f2': 4, u'f3': True}])


json_buf = u"[1, 2, 3, 4, 5]"
json_schema = "var * int8"


class TestOpenJSON(unittest.TestCase):

    def setUp(self):
        handle, self.fname = tempfile.mkstemp(suffix='.json')
        with os.fdopen(handle, "w") as f:
            f.write(json_buf)

    def tearDown(self):
        os.unlink(self.fname)

    def test_open(self):
        ddesc = JSON_DDesc(self.fname, mode='r', schema=json_schema)
        a = blaze.array(ddesc)
        self.assert_(isinstance(a, blaze.Array))
        self.assertEqual(ddesc_as_py(a.ddesc), [1, 2, 3, 4, 5])


class TestOpenBLZ(MayBePersistentTest, unittest.TestCase):

    disk = True
    dir_ = True

    def test_open(self):
        ddesc = BLZ_DDesc(path=self.rootdir, mode='w')
        self.assertTrue(ddesc.mode == 'w')
        a = blaze.ones('0 * float64', ddesc=ddesc)
        append(a,range(10))
        # Re-open the dataset
        ddesc = BLZ_DDesc(path=self.rootdir, mode='r')
        self.assertTrue(ddesc.mode == 'r')
        a2 = blaze.array(ddesc)
        self.assertTrue(isinstance(a2, blaze.Array))
        self.assertEqual(ddesc_as_py(a2.ddesc), list(range(10)))

    def test_wrong_open_mode(self):
        ddesc = BLZ_DDesc(path=self.rootdir, mode='w')
        a = blaze.ones('10 * float64', ddesc=ddesc)
        # Re-open the dataset
        ddesc = BLZ_DDesc(path=self.rootdir, mode='r')
        self.assertTrue(ddesc.mode == 'r')
        a2 = blaze.array(ddesc)
        self.assertRaises(IOError, append, a2, [1])


class TestOpenHDF5(MayBePersistentTest, unittest.TestCase):

    disk = True

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_open(self):
        ddesc = HDF5_DDesc(path=self.file, datapath='/earray', mode='a')
        self.assertTrue(ddesc.mode == 'a')
        a = blaze.ones('0 * float64', ddesc=ddesc)
        append(a,range(10))
        # Re-open the dataset in URI
        ddesc = HDF5_DDesc(path=self.file, datapath='/earray', mode='r')
        self.assertTrue(ddesc.mode == 'r')
        a2 = blaze.array(ddesc)
        self.assertTrue(isinstance(a2, blaze.Array))
        self.assertEqual(ddesc_as_py(a2.ddesc), list(range(10)))

    @skipIf(not tables_is_here, 'pytables is not installed')
    def test_wrong_open_mode(self):
        ddesc = HDF5_DDesc(path=self.file, datapath='/earray', mode='w')
        a = blaze.ones('10 * float64', ddesc=ddesc)
        # Re-open the dataset
        ddesc = HDF5_DDesc(path=self.file, datapath='/earray', mode='r')
        self.assertTrue(ddesc.mode == 'r')
        a2 = blaze.array(ddesc)
        self.assertRaises(tb.FileModeError, append, a2, [1])


if __name__ == '__main__':
   unittest.main(verbosity=2)

########NEW FILE########
__FILENAME__ = test_array_str
from __future__ import absolute_import, division, print_function

import unittest
import ctypes

import blaze
from blaze.datadescriptor import data_descriptor_from_ctypes


class TestArrayStr(unittest.TestCase):
    def test_scalar(self):
        self.assertEqual(str(blaze.array(100)), '100')
        self.assertEqual(str(blaze.array(-3.25)), '-3.25')
        self.assertEqual(str(blaze.array(True)), 'True')
        self.assertEqual(str(blaze.array(False)), 'False')

    def test_deferred_scalar(self):
        a = blaze.array(3) + blaze.array(5)
        self.assertEqual(str(a), '8')

    def test_ctypes_scalar(self):
        dd = data_descriptor_from_ctypes(ctypes.c_int32(1022), writable=True)
        a = blaze.array(dd)
        self.assertEqual(str(a), '1022')

    def test_1d_array(self):
        self.assertEqual(str(blaze.array([1,2,3])), '[1 2 3]')

    def test_ctypes_1d_array(self):
        cdat = (ctypes.c_int64 * 3)()
        cdat[0] = 3
        cdat[1] = 6
        cdat[2] = 10
        dd = data_descriptor_from_ctypes(cdat, writable=True)
        a = blaze.array(dd)
        self.assertEqual(str(a), '[ 3  6 10]')

    def test_ragged_array(self):
        a = blaze.array([[1,2,3],[4,5]])
        self.assertEqual(str(a),
            '[[        1         2         3]\n [        4         5]]')

    def test_empty_array(self):
        a = blaze.array([[], []])
        self.assertEqual(str(a), '[[]\n []]')
        a = blaze.array([[], [1, 2]])
        self.assertEqual(str(a), '[[]\n [     1      2]]')

    def test_str_array(self):
        # Basically check that it doesn't raise an exception to
        # get the string
        a = blaze.array(['this', 'is', 'a', 'test'])
        self.assertTrue(str(a) != '')
        self.assertTrue(repr(a) != '')

    def test_struct_array(self):
        # Basically check that it doesn't raise an exception to
        # get the string
        a = blaze.array([(1, 2), (3, 4), (5, 6)],
                dshape='{x: int32, y: float64}')
        self.assertTrue(str(a) != '')
        self.assertTrue(repr(a) != '')

if __name__ == '__main__':
    unittest.main(verbosity=2)

########NEW FILE########
__FILENAME__ = test_blaze_functions
from __future__ import absolute_import, division, print_function

import unittest

import numpy as np

from datashape import dshape
import blaze
from blaze.compute.function import ElementwiseBlazeFunc
from dynd import nd, _lowlevel


def create_overloaded_add():
    # Create an overloaded blaze func, populate it with
    # some ckernel implementations extracted from numpy,
    # and test some calls on it.
    myfunc = ElementwiseBlazeFunc('test', 'myfunc')

    # overload int32 -> np.add
    ckd = _lowlevel.arrfunc_from_ufunc(np.add, (np.int32, np.int32, np.int32),
                                       False)
    myfunc.add_overload("(int32, int32) -> int32", ckd)

    # overload int16 -> np.subtract (so we can see the difference)
    ckd = _lowlevel.arrfunc_from_ufunc(np.subtract,
                                       (np.int16, np.int16, np.int16), False)
    myfunc.add_overload("(int16, int16) -> int16", ckd)

    return myfunc


class TestBlazeFunctionFromUFunc(unittest.TestCase):
    def test_overload(self):
        myfunc = create_overloaded_add()

        # Test int32 overload -> add
        a = blaze.eval(myfunc(blaze.array([3, 4]), blaze.array([1, 2])))
        self.assertEqual(a.dshape, dshape('2 * int32'))
        self.assertEqual(nd.as_py(a.ddesc.dynd_arr()), [4, 6])
        # Test int16 overload -> subtract
        a = blaze.eval(myfunc(blaze.array([3, 4], dshape='int16'),
                       blaze.array([1, 2], dshape='int16')))
        self.assertEqual(a.dshape, dshape('2 * int16'))
        self.assertEqual(nd.as_py(a.ddesc.dynd_arr()), [2, 2])

    def test_overload_coercion(self):
        myfunc = create_overloaded_add()

        # Test type promotion to int32
        a = blaze.eval(myfunc(blaze.array([3, 4], dshape='int16'),
                       blaze.array([1, 2])))
        self.assertEqual(a.dshape, dshape('2 * int32'))
        self.assertEqual(nd.as_py(a.ddesc.dynd_arr()), [4, 6])
        a = blaze.eval(myfunc(blaze.array([3, 4]),
                       blaze.array([1, 2], dshape='int16')))
        self.assertEqual(a.dshape, dshape('2 * int32'))
        self.assertEqual(nd.as_py(a.ddesc.dynd_arr()), [4, 6])

        # Test type promotion to int16
        a = blaze.eval(myfunc(blaze.array([3, 4], dshape='int8'),
                       blaze.array([1, 2], dshape='int8')))
        self.assertEqual(a.dshape, dshape('2 * int16'))
        self.assertEqual(nd.as_py(a.ddesc.dynd_arr()), [2, 2])

    def test_nesting(self):
        myfunc = create_overloaded_add()

        # A little bit of nesting
        a = blaze.eval(myfunc(myfunc(blaze.array([3, 4]), blaze.array([1, 2])),
                              blaze.array([2, 10])))
        self.assertEqual(a.dshape, dshape('2 * int32'))
        self.assertEqual(nd.as_py(a.ddesc.dynd_arr()), [6, 16])

    def test_nesting_and_coercion(self):
        myfunc = create_overloaded_add()

        # More nesting, with conversions
        a = blaze.eval(myfunc(myfunc(blaze.array([1, 2]),
                                     blaze.array([-2, 10])),
                       myfunc(blaze.array([1, 5], dshape='int16'),
                              blaze.array(3, dshape='int16'))))
        self.assertEqual(a.dshape, dshape('2 * int32'))
        self.assertEqual(nd.as_py(a.ddesc.dynd_arr()), [-3, 14])

    def test_overload_different_argcount(self):
        myfunc = ElementwiseBlazeFunc('test', 'ovld')
        # Two parameter overload
        ckd = _lowlevel.arrfunc_from_ufunc(np.add, (np.int32,) * 3, False)
        myfunc.add_overload("(int32, int32) -> int32", ckd)

        # One parameter overload
        ckd = _lowlevel.arrfunc_from_ufunc(np.negative, (np.int32,) * 2, False)
        myfunc.add_overload("(int16, int16) -> int16", ckd)

        return myfunc


if __name__ == '__main__':
    # TestBlazeKernel('test_kernel').debug()
    unittest.main()

########NEW FILE########
__FILENAME__ = test_calc
from __future__ import absolute_import, division, print_function

import unittest
import math

import blaze
from blaze.datadescriptor import ddesc_as_py


class TestBasic(unittest.TestCase):

    def test_add(self):
        types = ['int8', 'int16', 'int32', 'int64']
        for type_ in types:
            a = blaze.array(range(3), dshape=type_)
            c = blaze.eval(a+a)
            self.assertEqual(ddesc_as_py(c.ddesc), [0, 2, 4])
            c = blaze.eval(((a+a)*a))
            self.assertEqual(ddesc_as_py(c.ddesc), [0, 2, 8])

    def test_add_with_pyobj(self):
        a = blaze.array(3) + 3
        self.assertEqual(ddesc_as_py(a.ddesc), 6)
        a = 3 + blaze.array(4)
        self.assertEqual(ddesc_as_py(a.ddesc), 7)
        a = blaze.array([1, 2]) + 4
        self.assertEqual(ddesc_as_py(a.ddesc), [5, 6])
        a = [1, 2] + blaze.array(5)
        self.assertEqual(ddesc_as_py(a.ddesc), [6, 7])

    #FIXME:  Need to convert uint8 from dshape to ctypes
    #        in _get_ctypes of blaze_kernel.py
    def test_mixed(self):
        types1 = ['int8', 'int16', 'int32', 'int64']
        types2 = ['int16', 'int32', 'float32', 'float64']
        for ty1, ty2 in zip(types1, types2):
            a = blaze.array(range(1,6), dshape=ty1)
            b = blaze.array(range(5), dshape=ty2)
            c = (a+b)*(a-b)
            c = blaze.eval(c)
            result = [a*a - b*b for (a,b) in zip(range(1,6),range(5))]
            self.assertEqual(ddesc_as_py(c.ddesc), result)

    def test_ragged(self):
        a = blaze.array([[1], [2, 3], [4, 5, 6]])
        b = blaze.array([[1, 2, 3], [4, 5], [6]])
        c = blaze.eval(a + b)
        self.assertEqual(ddesc_as_py(c.ddesc),
                    [[2, 3, 4], [6, 8], [10, 11, 12]])
        c = blaze.eval(2 * a - b)
        self.assertEqual(ddesc_as_py(c.ddesc),
                    [[1, 0, -1], [0, 1], [2, 4, 6]])


class TestReduction(unittest.TestCase):
    def test_min_zerosize(self):
        # Empty min operations should raise, because it has no
        # reduction identity
        self.assertRaises(ValueError, blaze.eval, blaze.min([]))
        self.assertRaises(ValueError, blaze.eval, blaze.min([], keepdims=True))
        self.assertRaises(ValueError, blaze.eval, blaze.min([[], []]))
        self.assertRaises(ValueError, blaze.eval, blaze.min([[], []],
                                                            keepdims=True))
        self.assertRaises(ValueError, blaze.eval, blaze.min([[], []], axis=-1))
        self.assertRaises(ValueError, blaze.eval, blaze.min([[], []],
                                                            axis=-1,
                                                            keepdims=True))
        # However, if we're only reducing on a non-empty dimension, it's ok
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[], []],
                                                       axis=0)).ddesc),
                         [])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[], []],
                                                       axis=0,
                                                       keepdims=True)).ddesc),
                         [[]])

    def test_min(self):
        # Min element of scalar case is the element itself
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min(10)).ddesc), 10)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min(-5.0)).ddesc), -5.0)
        # One-dimensional size one
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([10])).ddesc), 10)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([-5.0])).ddesc), -5.0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([-5.0],
                                                       axis=0)).ddesc), -5.0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([10],
                                                       keepdims=True)).ddesc),
                         [10])
        # One dimensional
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([1, 2])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([2, 1])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([0, 1, 0])).ddesc), 0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([0, 1, 0])).ddesc), 0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([1, 0, 2])).ddesc), 0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([2, 1, 0])).ddesc), 0)
        # Two dimensional, test with minimum at all possible positions
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 2, 3],
                                                        [4, 5, 6]])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[2, 1, 3],
                                                        [4, 5, 6]])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[3, 2, 1],
                                                        [4, 5, 6]])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[3, 2, 5],
                                                        [4, 1, 6]])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[3, 2, 5],
                                                        [4, 6, 1]])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[3, 2, 5],
                                                        [1, 6, 4]])).ddesc), 1)
        # Two dimensional, with axis= argument both positive and negative
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 5, 3],
                                                        [4, 2, 6]],
                                                       axis=0)).ddesc),
                         [1, 2, 3])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 5, 3],
                                                        [4, 2, 6]],
                                                       axis=-2)).ddesc),
                         [1, 2, 3])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 2, 3],
                                                        [4, 5, 6]],
                                                       axis=1)).ddesc),
                         [1, 4])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 2, 3],
                                                        [4, 5, 6]],
                                                       axis=-1)).ddesc),
                         [1, 4])
        # Two dimensional, with keepdims=True
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 2, 3],
                                                        [4, 5, 6]],
                                                       keepdims=True)).ddesc),
                         [[1]])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 2, 3],
                                                        [5, 4, 6]],
                                                       axis=0,
                                                       keepdims=True)).ddesc),
                         [[1, 2, 3]])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.min([[1, 5, 3],
                                                        [4, 2, 6]],
                                                       axis=1,
                                                       keepdims=True)).ddesc),
                         [[1], [2]])

    def test_sum_zerosize(self):
        # Empty sum operations should produce 0, the reduction identity
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([])).ddesc), 0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([],
                                                       keepdims=True)).ddesc),
                         [0])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[], []])).ddesc), 0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[], []],
                                                       keepdims=True)).ddesc),
                         [[0]])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[], []],
                                                       axis=-1)).ddesc),
                         [0, 0])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[], []],
                                                            axis=-1,
                                                            keepdims=True)).ddesc),
                         [[0], [0]])
        # If we're only reducing on a non-empty dimension, we might still
        # end up with zero-sized outputs
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[], []],
                                                       axis=0)).ddesc),
                         [])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[], []],
                                                       axis=0,
                                                       keepdims=True)).ddesc),
                         [[]])

    def test_sum(self):
        # Sum of scalar case is the element itself
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum(10)).ddesc), 10)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum(-5.0)).ddesc), -5.0)
        # One-dimensional size one
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([10])).ddesc), 10)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([-5.0])).ddesc), -5.0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([-5.0],
                                                       axis=0)).ddesc), -5.0)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([10],
                                                       keepdims=True)).ddesc),
                         [10])
        # One dimensional
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([1, 2])).ddesc), 3)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([0, 1, 2])).ddesc), 3)
        # Two dimensional
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 2, 3],
                                                        [4, 5, 6]])).ddesc), 21)
        # Two dimensional, with axis= argument both positive and negative
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 5, 3],
                                                        [4, 2, 6]],
                                                       axis=0)).ddesc),
                         [5, 7, 9])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 5, 3],
                                                        [4, 2, 6]],
                                                       axis=-2)).ddesc),
                         [5, 7, 9])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 2, 3],
                                                        [4, 5, 6]],
                                                       axis=1)).ddesc),
                         [6, 15])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 2, 3],
                                                        [4, 5, 6]],
                                                       axis=-1)).ddesc),
                         [6, 15])
        # Two dimensional, with keepdims=True
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 2, 3],
                                                        [4, 5, 6]],
                                                       keepdims=True)).ddesc),
                         [[21]])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 2, 3],
                                                        [5, 4, 6]],
                                                       axis=0,
                                                       keepdims=True)).ddesc),
                         [[6, 6, 9]])
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.sum([[1, 5, 3],
                                                        [4, 2, 6]],
                                                       axis=1,
                                                       keepdims=True)).ddesc),
                         [[9], [12]])

    def test_all(self):
        # Sanity check of reduction op
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.all(True)).ddesc), True)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.all(False)).ddesc), False)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.all(blaze.array([], dshape='0 * bool'))).ddesc), True)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.all([False, True])).ddesc),
                         False)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.all([True, True])).ddesc),
                         True)

    def test_any(self):
        # Sanity check of reduction op
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.any(True)).ddesc), True)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.any(False)).ddesc), False)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.any(blaze.array([], dshape='0 * bool'))).ddesc), False)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.any([False, True])).ddesc),
                         True)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.any([False, False])).ddesc),
                         False)

    def test_max(self):
        # Sanity check of reduction op
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.max(5)).ddesc), 5)
        self.assertRaises(ValueError, blaze.eval, blaze.max([]))
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.max([3, -2])).ddesc),
                         3)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.max([1.5, 2.0])).ddesc),
                         2.0)

    def test_product(self):
        # Sanity check of reduction op
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.product(5)).ddesc), 5)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.product([])).ddesc), 1)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.product([3, -2])).ddesc),
                         -6)
        self.assertEqual(ddesc_as_py(blaze.eval(blaze.product([1.5, 2.0])).ddesc),
                         3.0)


class TestRolling(unittest.TestCase):
    def test_rolling_mean(self):
        a = blaze.eval(blaze.rolling_mean([1., 3, 4, 2, 5], window=4))
        self.assertTrue(all(math.isnan(x) for x in a[:3]))
        self.assertEqual(list(a[3:]), [10./4, 14./4])

    def test_diff(self):
        a = blaze.eval(blaze.diff([1., 2, 4, 4, 2, 0]))
        self.assertTrue(math.isnan(a[0]))
        self.assertEqual(list(a[1:]), [1, 2, 0, -2, -2])


class TestTake(unittest.TestCase):
    def test_masked_take(self):
        a = blaze.take([1, 3, 5, 7], [True, False, True, False])
        self.assertEqual(list(a), [1, 5])
        x = blaze.array([(1, "test"), (2, "one"), (3, "two"), (4, "three")],
                        dshape="{x: int, y: string}")
        a = blaze.take(x, [True, True, True, True])
        self.assertEqual(list(a), list(x))
        a = blaze.take(x, [True, True, False, False])
        self.assertEqual(list(a), [x[0], x[1]])
        a = blaze.take(x, [False, False, True, True])
        self.assertEqual(list(a), [x[2], x[3]])
        a = blaze.take(x, [True, False, True, False])
        self.assertEqual(list(a), [x[0], x[2]])

    def test_indexed_take(self):
        a = blaze.take([1, 3, 5, 7], [-1, -2, -3, -4, 0, 1, 2, 3])
        self.assertEqual(list(a), [7, 5, 3, 1, 1, 3, 5, 7])
        x = blaze.array([(1, "test"), (2, "one"), (3, "two"), (4, "three")],
                        dshape="{x: int, y: string}")
        a = blaze.take(x, [2, -3])
        self.assertEqual(list(a), [x[2], x[-3]])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_datetime
from __future__ import absolute_import, division, print_function

import unittest
from datetime import date, time, datetime

import blaze
from datashape import dshape
from blaze.datadescriptor import ddesc_as_py


class TestDate(unittest.TestCase):
    def test_create(self):
        a = blaze.array(date(2000, 1, 1))
        self.assertEqual(a.dshape, dshape('date'))
        self.assertEqual(ddesc_as_py(a.ddesc), date(2000, 1, 1))
        a = blaze.array([date(1490, 3, 12), date(2020, 7, 15)])
        self.assertEqual(a.dshape, dshape('2 * date'))
        self.assertEqual(list(a), [date(1490, 3, 12), date(2020, 7, 15)])
        a = blaze.array(['1490-03-12', '2020-07-15'], dshape='date')
        self.assertEqual(a.dshape, dshape('2 * date'))
        self.assertEqual(list(a), [date(1490, 3, 12), date(2020, 7, 15)])

    def test_properties(self):
        a = blaze.array(['1490-03-12', '2020-07-15'], dshape='date')
        self.assertEqual(list(a.year), [1490, 2020])
        self.assertEqual(list(a.month), [3, 7])
        self.assertEqual(list(a.day), [12, 15])

class TestTime(unittest.TestCase):
    def test_create(self):
        a = blaze.array(time(14, 30))
        self.assertEqual(a.dshape, dshape('time'))
        self.assertEqual(ddesc_as_py(a.ddesc), time(14, 30))
        a = blaze.array([time(14, 30), time(12, 25, 39, 123456)])
        self.assertEqual(a.dshape, dshape('2 * time'))
        self.assertEqual(list(a), [time(14, 30), time(12, 25, 39, 123456)])
        a = blaze.array(['2:30 pm', '12:25:39.123456'], dshape='time')
        self.assertEqual(a.dshape, dshape('2 * time'))
        self.assertEqual(list(a), [time(14, 30), time(12, 25, 39, 123456)])

    def test_properties(self):
        a = blaze.array([time(14, 30), time(12, 25, 39, 123456)], dshape='time')
        self.assertEqual(list(a.hour), [14, 12])
        self.assertEqual(list(a.minute), [30, 25])
        self.assertEqual(list(a.second), [0, 39])
        self.assertEqual(list(a.microsecond), [0, 123456])

class TestDateTime(unittest.TestCase):
    def test_create(self):
        a = blaze.array(datetime(1490, 3, 12, 14, 30))
        self.assertEqual(a.dshape, dshape('datetime'))
        self.assertEqual(ddesc_as_py(a.ddesc), datetime(1490, 3, 12, 14, 30))
        a = blaze.array([datetime(1490, 3, 12, 14, 30),
                         datetime(2020, 7, 15, 12, 25, 39, 123456)])
        self.assertEqual(a.dshape, dshape('2 * datetime'))
        self.assertEqual(list(a), [datetime(1490, 3, 12, 14, 30),
                                   datetime(2020, 7, 15, 12, 25, 39, 123456)])
        a = blaze.array(['1490-mar-12 2:30 pm', '2020-07-15T12:25:39.123456'],
                        dshape='datetime')
        self.assertEqual(a.dshape, dshape('2 * datetime'))
        self.assertEqual(list(a), [datetime(1490, 3, 12, 14, 30),
                                   datetime(2020, 7, 15, 12, 25, 39, 123456)])

    def test_properties(self):
        a = blaze.array([datetime(1490, 3, 12, 14, 30),
                         datetime(2020, 7, 15, 12, 25, 39, 123456)],
                        dshape='datetime')
        self.assertEqual(list(a.date), [date(1490, 3, 12), date(2020, 7, 15)])
        self.assertEqual(list(a.time), [time(14, 30), time(12, 25, 39, 123456)])
        self.assertEqual(list(a.year), [1490, 2020])
        self.assertEqual(list(a.month), [3, 7])
        self.assertEqual(list(a.day), [12, 15])
        self.assertEqual(list(a.hour), [14, 12])
        self.assertEqual(list(a.minute), [30, 25])
        self.assertEqual(list(a.second), [0, 39])
        self.assertEqual(list(a.microsecond), [0, 123456])


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_eval
from __future__ import absolute_import, division, print_function

import os
import sys
import unittest
import tempfile
from itertools import product as it_product

import blaze
from blaze.datadescriptor import ddesc_as_py


import numpy as np
from numpy.testing import assert_allclose

def _clean_disk_arrays():
    try:
        from shutil import rmtree
        rmtree(tmpdir)
    except Exception as e:
        print('Error cleaning up temp dir %s:\n%s' % (tmpdir, e))

def _mk_dir():
    global tmpdir
    tmpdir = tempfile.mkdtemp(prefix='blztmp')

def _ddesc(name):
    path = os.path.join(tmpdir, name + '.blz')
    return blaze.BLZ_DDesc(path, mode='w')

def _addition(a,b):
    return (a+b)
def _expression(a, b):
    return (a+b)*(a+b)

#------------------------------------------------------------------------
# Test Generation
#------------------------------------------------------------------------

def _add_tests():
    _pair = ['mem', 'dsk']
    frame = sys._getframe(1)
    for expr, ltr in zip([_addition, _expression], ['R', 'Q']):
        for i in it_product(_pair, _pair, _pair):
            args = i + (ltr,)
            f = _build_tst(expr, *args)
            f.__name__ = 'test_{1}_{2}_to_{3}{0}'.format(f.__name__, *args)
            frame.f_locals[f.__name__] = f

def _build_tst(kernel, storage1, storage2, storage3, R):
    def function(self):
        A = getattr(self, storage1 + 'A')
        B = getattr(self, storage2 + 'B')

        Rd = kernel(A, B)
        self.assert_(isinstance(Rd, blaze.Array))
        self.assert_(Rd.ddesc.capabilities.deferred)
        p = _ddesc(storage3 + 'Rd') if storage3 == 'dsk' else None
        try:
            Rc = blaze.eval(Rd, ddesc=p)
            self.assert_(isinstance(Rc, blaze.Array))
            npy_data = getattr(self, 'npy' + R)
            assert_allclose(np.array(ddesc_as_py(Rc.ddesc)), npy_data)

            if storage3 == 'dsk':
                self.assert_(Rc.ddesc.capabilities.persistent)
            else:
                self.assert_(not Rc.ddesc.capabilities.persistent)

        finally:
            try:
                if p is not None:
                    p.remove()
            except:
                pass # show the real error...

    return function


#------------------------------------------------------------------------
# Tests
#------------------------------------------------------------------------

class TestEvalScalar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.npyA = np.array(10)
        cls.npyB = np.arange(0.0, 100.0)
        cls.npyR = _addition(cls.npyA, cls.npyB)
        cls.npyQ = _expression(cls.npyA, cls.npyB)
        cls.memA = blaze.array(cls.npyA)
        cls.memB = blaze.array(cls.npyB)

        _mk_dir()
        cls.dskA = blaze.array(cls.npyA, ddesc=_ddesc('dskA'))
        cls.dskB = blaze.array(cls.npyB, ddesc=_ddesc('dskB'))

    @classmethod
    def tearDownClass(cls):
        _clean_disk_arrays()
        del(cls.npyA)
        del(cls.npyB)
        del(cls.npyR)
        del(cls.memA)
        del(cls.memB)
        del(cls.dskA)
        del(cls.dskB)

    # add all tests for all permutations
    # TODO: Enable. Currently segfaults
    # _add_tests()


class TestEval1D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.npyA = np.arange(0.0, 100.0)
        cls.npyB = np.arange(0.0, 100.0)
        cls.npyR = _addition(cls.npyA, cls.npyB)
        cls.npyQ = _expression(cls.npyA, cls.npyB)
        cls.memA = blaze.array(cls.npyA)
        cls.memB = blaze.array(cls.npyB)

        _mk_dir()
        cls.dskA = blaze.array(cls.npyA, ddesc=_ddesc('dskA'))
        cls.dskB = blaze.array(cls.npyB, ddesc=_ddesc('dskB'))

    @classmethod
    def tearDownClass(cls):
        _clean_disk_arrays()
        del(cls.npyA)
        del(cls.npyB)
        del(cls.npyR)
        del(cls.memA)
        del(cls.memB)
        del(cls.dskA)
        del(cls.dskB)

    # add all tests for all permutations
    _add_tests()


class TestEval2D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.npyA = np.arange(0.0, 100.0).reshape(20, 5)
        cls.npyB = np.arange(0.0, 100.0).reshape(20, 5)
        cls.npyR = _addition(cls.npyA, cls.npyB)
        cls.npyQ = _expression(cls.npyA, cls.npyB)
        cls.memA = blaze.array(cls.npyA)
        cls.memB = blaze.array(cls.npyB)

        _mk_dir()
        cls.dskA = blaze.array(cls.npyA, ddesc=_ddesc('dskA'))
        cls.dskB = blaze.array(cls.npyB, ddesc=_ddesc('dskB'))

    @classmethod
    def tearDownClass(cls):
        _clean_disk_arrays()
        del(cls.npyA)
        del(cls.npyB)
        del(cls.npyR)
        del(cls.memA)
        del(cls.memB)
        del(cls.dskA)
        del(cls.dskB)

    # add all tests for all permutations
    _add_tests()

if __name__ == '__main__':
    #TestEval2D.setUpClass()
    #TestEval2D('test_dsk_mem_to_memfunction').debug()
    unittest.main(verbosity=2)


########NEW FILE########
__FILENAME__ = test_get_set
from __future__ import absolute_import, division, print_function

import unittest

import numpy as np

import blaze
from blaze import BLZ_DDesc
from blaze.datadescriptor import ddesc_as_py


class getitem(unittest.TestCase):
    ddesc = None

    def test_scalar(self):
        a = blaze.array(np.arange(3), ddesc=self.ddesc)
        self.assertEqual(a[0], 0)

    def test_1d(self):
        a = blaze.array(np.arange(3), ddesc=self.ddesc)
        # print("a:", a, self.caps)
        self.assertEqual(ddesc_as_py(a[0:2].ddesc), [0,1])

    def test_2d(self):
        a = blaze.array(np.arange(3*3).reshape(3,3), ddesc=self.ddesc)
        self.assertEqual(ddesc_as_py(a[1].ddesc), [3,4,5])

class getitem_blz(getitem):
    ddesc = BLZ_DDesc(mode='w')

class setitem(unittest.TestCase):
    ddesc = None

    def test_scalar(self):
        a = blaze.array(np.arange(3), ddesc=self.ddesc)
        a[0] = 1
        self.assertEqual(a[0], 1)

    def test_1d(self):
        a = blaze.array(np.arange(3), ddesc=self.ddesc)
        a[0:2] = 2
        self.assertEqual(ddesc_as_py(a[0:2].ddesc), [2,2])

    def test_2d(self):
        a = blaze.array(np.arange(3*3).reshape(3,3), ddesc=self.ddesc)
        a[1] = 2
        self.assertEqual(ddesc_as_py(a[1].ddesc), [2,2,2])

class setitem_blz(getitem):
    ddesc = BLZ_DDesc(mode='w')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_numpy_ufunc_compat
from __future__ import absolute_import, division, print_function

import math
import cmath
import unittest

import numpy as np
from numpy import testing
from numpy.testing import assert_

import blaze
import datashape
from blaze.datadescriptor import ddesc_as_py
from blaze.py2help import skip


def assert_almost_equal(actual, desired, **kwargs):
    return testing.assert_almost_equal(np.array(actual),
                                       np.array(desired), **kwargs)


def assert_allclose(actual, desired, **kwargs):
    return testing.assert_allclose(np.array(actual),
                                   np.array(desired), **kwargs)


def assert_equal(actual, desired, **kwargs):
    return testing.assert_equal(np.array(actual), np.array(desired), **kwargs)


def assert_array_equal(actual, desired, **kwargs):
    return testing.assert_array_equal(np.array(actual),
                                      np.array(desired), **kwargs)

# Many of these tests have been adapted from NumPy's test_umath.py test file


class TestBitwiseOps(unittest.TestCase):
    def test_bitwise_or_bool(self):
        t = blaze.array(True)
        f = blaze.array(False)
        self.assertEqual(ddesc_as_py((t | t).ddesc), True)
        self.assertEqual(ddesc_as_py((t | f).ddesc), True)
        self.assertEqual(ddesc_as_py((f | t).ddesc), True)
        self.assertEqual(ddesc_as_py((f | f).ddesc), False)

    def test_bitwise_or_uint64(self):
        x, y = 0x3192573469a2b3a1, 0x9274a2e219c27638
        a = blaze.array(x, 'uint64')
        b = blaze.array(y, 'uint64')
        self.assertEqual(ddesc_as_py((a | b).ddesc), x | y)
        self.assertEqual(ddesc_as_py(blaze.bitwise_or(a, b).ddesc), x | y)

    def test_bitwise_and_bool(self):
        t = blaze.array(True)
        f = blaze.array(False)
        self.assertEqual(ddesc_as_py((t & t).ddesc), True)
        self.assertEqual(ddesc_as_py((t & f).ddesc), False)
        self.assertEqual(ddesc_as_py((f & t).ddesc), False)
        self.assertEqual(ddesc_as_py((f & f).ddesc), False)

    def test_bitwise_and_uint64(self):
        x, y = 0x3192573469a2b3a1, 0x9274a2e219c27638
        a = blaze.array(x, 'uint64')
        b = blaze.array(y, 'uint64')
        self.assertEqual(ddesc_as_py((a & b).ddesc), x & y)
        self.assertEqual(ddesc_as_py(blaze.bitwise_and(a, b).ddesc), x & y)

    def test_bitwise_xor_bool(self):
        t = blaze.array(True)
        f = blaze.array(False)
        self.assertEqual(ddesc_as_py((t ^ t).ddesc), False)
        self.assertEqual(ddesc_as_py((t ^ f).ddesc), True)
        self.assertEqual(ddesc_as_py((f ^ t).ddesc), True)
        self.assertEqual(ddesc_as_py((f ^ f).ddesc), False)

    def test_bitwise_xor_uint64(self):
        x, y = 0x3192573469a2b3a1, 0x9274a2e219c27638
        a = blaze.array(x, 'uint64')
        b = blaze.array(y, 'uint64')
        self.assertEqual(ddesc_as_py((a ^ b).ddesc), x ^ y)
        self.assertEqual(ddesc_as_py(blaze.bitwise_xor(a, b).ddesc), x ^ y)

    def test_bitwise_not_bool(self):
        t = blaze.array(True)
        f = blaze.array(False)
        self.assertEqual(ddesc_as_py((~t).ddesc), False)
        self.assertEqual(ddesc_as_py((~f).ddesc), True)

    def test_bitwise_not_uint64(self):
        x = 0x3192573469a2b3a1
        a = blaze.array(x, 'uint64')
        self.assertEqual(ddesc_as_py((~a).ddesc), x ^ 0xffffffffffffffff)
        self.assertEqual(ddesc_as_py(blaze.bitwise_not(a).ddesc),
                         x ^ 0xffffffffffffffff)


class TestPower(unittest.TestCase):
    def test_power_float(self):
        x = blaze.array([1., 2., 3.])
        assert_equal(x**0, [1., 1., 1.])
        assert_equal(x**1, x)
        assert_equal(x**2, [1., 4., 9.])
        assert_almost_equal(x**(-1), [1., 0.5, 1./3])
        assert_almost_equal(x**(0.5), [1., math.sqrt(2), math.sqrt(3)])

    def test_power_complex(self):
        x = blaze.array([1+2j, 2+3j, 3+4j])
        assert_equal(x**0, [1., 1., 1.])
        assert_equal(x**1, x)
        assert_almost_equal(x**2, [-3+4j, -5+12j, -7+24j])
        assert_almost_equal(x**3, [(1+2j)**3, (2+3j)**3, (3+4j)**3])
        assert_almost_equal(x**4, [(1+2j)**4, (2+3j)**4, (3+4j)**4])
        assert_almost_equal(x**(-1), [1/(1+2j), 1/(2+3j), 1/(3+4j)])
        assert_almost_equal(x**(-2), [1/(1+2j)**2, 1/(2+3j)**2, 1/(3+4j)**2])
        assert_almost_equal(x**(-3), [(-11+2j)/125, (-46-9j)/2197,
                                      (-117-44j)/15625])
        assert_almost_equal(x**(0.5), [cmath.sqrt(1+2j), cmath.sqrt(2+3j),
                                       cmath.sqrt(3+4j)])
        norm = 1./((x**14)[0])
        assert_almost_equal(x**14 * norm,
                [i * norm for i in [-76443+16124j, 23161315+58317492j,
                                    5583548873 +  2465133864j]])

        def assert_complex_equal(x, y):
            assert_array_equal(x.real, y.real)
            assert_array_equal(x.imag, y.imag)

        for z in [complex(0, np.inf), complex(1, np.inf)]:
            z = blaze.array([z], dshape="complex[float64]")
            assert_complex_equal(z**1, z)
            assert_complex_equal(z**2, z*z)
            assert_complex_equal(z**3, z*z*z)

    def test_power_zero(self):
        zero = blaze.array([0j])
        one = blaze.array([1+0j])
        cnan = blaze.array([complex(np.nan, np.nan)])

        def assert_complex_equal(x, y):
            x, y = np.array(x), np.array(y)
            assert_array_equal(x.real, y.real)
            assert_array_equal(x.imag, y.imag)

        # positive powers
        for p in [0.33, 0.5, 1, 1.5, 2, 3, 4, 5, 6.6]:
            assert_complex_equal(blaze.power(zero, p), zero)

        # zero power
        assert_complex_equal(blaze.power(zero, 0), one)
        assert_complex_equal(blaze.power(zero, 0+1j), cnan)

        # negative power
        for p in [0.33, 0.5, 1, 1.5, 2, 3, 4, 5, 6.6]:
            assert_complex_equal(blaze.power(zero, -p), cnan)
        assert_complex_equal(blaze.power(zero, -1+0.2j), cnan)

    def test_fast_power(self):
        x = blaze.array([1, 2, 3], dshape="int16")
        self.assertEqual((x**2.00001).dshape, (x**2.0).dshape)


class TestLog(unittest.TestCase):
    def test_log_values(self):
        x = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
        y = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for ds in ['float32', 'float64']:
            log2_ = 0.69314718055994530943
            xf = blaze.array(x, dshape=ds)
            yf = blaze.array(y, dshape=ds)*log2_
            result = blaze.log(xf)
            assert_almost_equal(result, yf)


class TestExp(unittest.TestCase):
    def test_exp_values(self):
        x = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
        y = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for ds in ['float32', 'float64']:
            log2_ = 0.69314718055994530943
            xf = blaze.array(x, dshape=ds)
            yf = blaze.array(y, dshape=ds)*log2_
            result = blaze.exp(yf)
            assert_almost_equal(result, xf)


class TestLogAddExp(unittest.TestCase):
    def test_logaddexp_values(self):
        x = [1, 2, 3, 4, 5]
        y = [5, 4, 3, 2, 1]
        z = [6, 6, 6, 6, 6]
        for ds, dec in zip(['float32', 'float64'], [6, 15]):
            xf = blaze.log(blaze.array(x, dshape=ds))
            yf = blaze.log(blaze.array(y, dshape=ds))
            zf = blaze.log(blaze.array(z, dshape=ds))
            result = blaze.logaddexp(xf, yf)
            assert_almost_equal(result, zf, decimal=dec)

    def test_logaddexp_range(self):
        x = [1000000, -1000000, 1000200, -1000200]
        y = [1000200, -1000200, 1000000, -1000000]
        z = [1000200, -1000000, 1000200, -1000000]
        for ds in ['float32', 'float64']:
            logxf = blaze.array(x, dshape=ds)
            logyf = blaze.array(y, dshape=ds)
            logzf = blaze.array(z, dshape=ds)
            result = blaze.logaddexp(logxf, logyf)
            assert_almost_equal(result, logzf)

    def test_inf(self):
        inf = blaze.inf
        x = [inf, -inf,  inf, -inf, inf, 1,  -inf,  1]
        y = [inf,  inf, -inf, -inf, 1,   inf, 1,   -inf]
        z = [inf,  inf,  inf, -inf, inf, inf, 1,    1]
        for ds in ['float32', 'float64']:
            logxf = blaze.array(x, dshape=ds)
            logyf = blaze.array(y, dshape=ds)
            logzf = blaze.array(z, dshape=ds)
            result = blaze.logaddexp(logxf, logyf)
            assert_equal(result, logzf)

    def test_nan(self):
        self.assertTrue(blaze.isnan(blaze.logaddexp(blaze.nan, blaze.inf)))
        self.assertTrue(blaze.isnan(blaze.logaddexp(blaze.inf, blaze.nan)))
        self.assertTrue(blaze.isnan(blaze.logaddexp(blaze.nan, 0)))
        self.assertTrue(blaze.isnan(blaze.logaddexp(0, blaze.nan)))
        self.assertTrue(blaze.isnan(blaze.logaddexp(blaze.nan, blaze.nan)))


class TestLog2(unittest.TestCase):
    def test_log2_values(self):
        x = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
        y = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for ds in ['float32', 'float64']:
            xf = blaze.array(x, dshape=ds)
            yf = blaze.array(y, dshape=ds)
            result = blaze.log2(xf)
            assert_almost_equal(result, yf)


class TestLog10(unittest.TestCase):
    def test_log10_values(self):
        x = [1, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10]
        y = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for ds in ['float32', 'float64']:
            xf = blaze.array(x, dshape=ds)
            yf = blaze.array(y, dshape=ds)
            result = blaze.log10(xf)
            assert_almost_equal(result, yf)


class TestExp2(unittest.TestCase):
    def test_exp2_values(self):
        x = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
        y = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for ds in ['float32', 'float64']:
            xf = blaze.array(x, dshape=ds)
            yf = blaze.array(y, dshape=ds)
            result = blaze.exp2(yf)
            assert_almost_equal(result, xf)


class TestLogAddExp2(unittest.TestCase):
    # Need test for intermediate precisions
    def test_logaddexp2_values(self):
        x = [1, 2, 3, 4, 5]
        y = [5, 4, 3, 2, 1]
        z = [6, 6, 6, 6, 6]
        for ds, dec in zip(['float32', 'float64'], [6, 15, 15]):
            xf = blaze.log2(blaze.array(x, dshape=ds))
            yf = blaze.log2(blaze.array(y, dshape=ds))
            zf = blaze.log2(blaze.array(z, dshape=ds))
            result = blaze.logaddexp2(xf, yf)
            assert_almost_equal(result, zf, decimal=dec)

    def test_logaddexp2_range(self):
        x = [1000000, -1000000, 1000200, -1000200]
        y = [1000200, -1000200, 1000000, -1000000]
        z = [1000200, -1000000, 1000200, -1000000]
        for ds in ['float32', 'float64']:
            logxf = blaze.array(x, dshape=ds)
            logyf = blaze.array(y, dshape=ds)
            logzf = blaze.array(z, dshape=ds)
            result = blaze.logaddexp2(logxf, logyf)
            assert_almost_equal(result, logzf)

    def test_inf(self):
        inf = blaze.inf
        x = [inf, -inf,  inf, -inf, inf, 1,  -inf,  1]
        y = [inf,  inf, -inf, -inf, 1,   inf, 1,   -inf]
        z = [inf,  inf,  inf, -inf, inf, inf, 1,    1]
        for ds in ['float32', 'float64']:
            logxf = blaze.array(x, dshape=ds)
            logyf = blaze.array(y, dshape=ds)
            logzf = blaze.array(z, dshape=ds)
            result = blaze.logaddexp2(logxf, logyf)
            assert_equal(result, logzf)

    def test_nan(self):
        self.assertTrue(blaze.isnan(blaze.logaddexp2(blaze.nan, blaze.inf)))
        self.assertTrue(blaze.isnan(blaze.logaddexp2(blaze.inf, blaze.nan)))
        self.assertTrue(blaze.isnan(blaze.logaddexp2(blaze.nan, 0)))
        self.assertTrue(blaze.isnan(blaze.logaddexp2(0, blaze.nan)))
        self.assertTrue(blaze.isnan(blaze.logaddexp2(blaze.nan, blaze.nan)))


class TestRint(unittest.TestCase):
    def test_rint(self):
        a = blaze.array([-1.7, -1.5, -0.2, 0.2, 1.5, 1.7, 2.0])
        b = blaze.array([-2., -2., -0.,  0.,  2.,  2.,  2.])
        result = blaze.rint(a)
        assert_equal(result, b)


class TestSign(unittest.TestCase):
    def test_sign(self):
        a = blaze.array([blaze.inf, -blaze.inf, blaze.nan, 0.0, 3.0, -3.0])
        tgt = blaze.array([1., -1., blaze.nan, 0.0, 1.0, -1.0])

        result = blaze.sign(a)
        assert_equal(result, tgt)


class TestExpm1(unittest.TestCase):
    def test_expm1(self):
        assert_almost_equal(blaze.expm1(0.2), blaze.exp(0.2)-1)
        assert_almost_equal(blaze.expm1(1e-6), blaze.exp(1e-6)-1)


class TestLog1p(unittest.TestCase):
    def test_log1p(self):
        assert_almost_equal(blaze.log1p(0.2), blaze.log(1.2))
        assert_almost_equal(blaze.log1p(1e-6), blaze.log(1+1e-6))


class TestSqrt(unittest.TestCase):
    def test_sqrt(self):
        a = blaze.array([0., 9., 64., 1e20, 12345])
        b = blaze.array([0., 3., 8., 1e10, math.sqrt(12345)])
        result = blaze.sqrt(a)
        assert_almost_equal(result, b)


class TestSquare(unittest.TestCase):
    def test_square(self):
        a = blaze.array([0., 3., 8., 1e10, math.sqrt(12345)])
        b = blaze.array([0., 9., 64., 1e20, 12345])
        result = blaze.square(a)
        assert_almost_equal(result, b)
        result = blaze.square(-a)
        assert_almost_equal(result, b)


class TestReciprocal(unittest.TestCase):
    def test_reciprocal(self):
        a = blaze.array([1, 2., 3.33])
        b = blaze.array([1., 0.5, 0.3003003])
        result = blaze.reciprocal(a)
        assert_almost_equal(result, b)


class TestAngles(unittest.TestCase):
    def test_degrees(self):
        assert_almost_equal(blaze.degrees(math.pi), 180.0)
        assert_almost_equal(blaze.degrees(-0.5*math.pi), -90.0)
        assert_almost_equal(blaze.rad2deg(math.pi), 180.0)
        assert_almost_equal(blaze.rad2deg(-0.5*math.pi), -90.0)

    def test_radians(self):
        assert_almost_equal(blaze.radians(180.0), math.pi)
        assert_almost_equal(blaze.radians(-90.0), -0.5*math.pi)
        assert_almost_equal(blaze.deg2rad(180.0), math.pi)
        assert_almost_equal(blaze.deg2rad(-90.0), -0.5*math.pi)


class TestMod(unittest.TestCase):
    def test_remainder_mod_int(self):
        a = blaze.array([-3, -2, -1, 0, 1, 2, 3])
        a_mod_2 = blaze.array([1,  0, 1,  0, 1,  0,  1])
        a_mod_3 = blaze.array([0,  1, 2,  0, 1,  2,  0])
        assert_equal(blaze.remainder(a, 2), a_mod_2)
        assert_equal(blaze.mod(a, 2), a_mod_2)
        assert_equal(blaze.remainder(a, 3), a_mod_3)
        assert_equal(blaze.mod(a, 3), a_mod_3)

    def test_remainder_mod_float(self):
        a = blaze.array([-3, -2, -1, 0, 1, 2, 3], dshape='float32')
        a_mod_2 = blaze.array([1,  0, 1,  0, 1,  0,  1], dshape='float32')
        a_mod_3 = blaze.array([0,  1, 2,  0, 1,  2,  0], dshape='float32')
        assert_equal(blaze.remainder(a, 2), a_mod_2)
        assert_equal(blaze.mod(a, 2), a_mod_2)
        assert_equal(blaze.remainder(a, 3), a_mod_3)
        assert_equal(blaze.mod(a, 3), a_mod_3)

    def test_fmod_int(self):
        a = blaze.array([-3, -2, -1, 0, 1, 2, 3])
        a_fmod_2 = blaze.array([-1,  0, -1,  0, 1,  0,  1])
        a_fmod_3 = blaze.array([0,  -2, -1,  0, 1,  2,  0])
        assert_equal(blaze.fmod(a, 2), a_fmod_2)
        assert_equal(blaze.fmod(a, 3), a_fmod_3)

    def test_fmod_float(self):
        a = blaze.array([-3, -2, -1, 0, 1, 2, 3], dshape='float32')
        a_fmod_2 = blaze.array([-1,  0, -1,  0, 1,  0,  1], dshape='float32')
        a_fmod_3 = blaze.array([0,  -2, -1,  0, 1,  2,  0], dshape='float32')
        assert_equal(blaze.fmod(a, 2), a_fmod_2)
        assert_equal(blaze.fmod(a, 3), a_fmod_3)


class TestAbs(unittest.TestCase):
    def test_simple(self):
        x = blaze.array([1+1j, 0+2j, 1+2j, blaze.inf, blaze.nan])
        y_r = blaze.array([blaze.sqrt(2.), 2, blaze.sqrt(5),
                           blaze.inf, blaze.nan])
        y = blaze.abs(x)
        for i in range(len(x)):
            assert_almost_equal(y[i], y_r[i])

    def test_fabs(self):
        # Test that blaze.abs(x +- 0j) == blaze.abs(x)
        # (as mandated by C99 for cabs)
        x = blaze.array([1+0j], dshape="complex[float64]")
        assert_array_equal(blaze.abs(x), blaze.real(x))

        x = blaze.array([complex(1, -0.)], dshape="complex[float64]")
        assert_array_equal(blaze.abs(x), blaze.real(x))

        x = blaze.array([complex(blaze.inf, -0.)], dshape="complex[float64]")
        assert_array_equal(blaze.abs(x), blaze.real(x))

        x = blaze.array([complex(blaze.nan, -0.)], dshape="complex[float64]")
        assert_array_equal(blaze.abs(x), blaze.real(x))

    def test_cabs_inf_nan(self):
        # cabs(+-nan + nani) returns nan
        self.assertTrue(blaze.isnan(blaze.abs(complex(blaze.nan, blaze.nan))))
        self.assertTrue(blaze.isnan(blaze.abs(complex(-blaze.nan, blaze.nan))))
        self.assertTrue(blaze.isnan(blaze.abs(complex(blaze.nan, -blaze.nan))))
        self.assertTrue(blaze.isnan(blaze.abs(complex(-blaze.nan, -blaze.nan))))

        # According to C99 standard, if exactly one of the real/part is inf and
        # the other nan, then cabs should return inf
        assert_equal(blaze.abs(complex(blaze.inf, blaze.nan)), blaze.inf)
        assert_equal(blaze.abs(complex(blaze.nan, blaze.inf)), blaze.inf)
        assert_equal(blaze.abs(complex(-blaze.inf, blaze.nan)), blaze.inf)
        assert_equal(blaze.abs(complex(blaze.nan, -blaze.inf)), blaze.inf)

        values = [complex(blaze.nan, blaze.nan),
                  complex(-blaze.nan, blaze.nan),
                  complex(blaze.inf, blaze.nan),
                  complex(-blaze.inf, blaze.nan)]

        for z in values:
            abs_conj_z = blaze.abs(blaze.conj(z))
            conj_abs_z = blaze.conj(blaze.abs(z))
            abs_z = blaze.abs(z)
            assert_equal(abs_conj_z, conj_abs_z)
            assert_equal(abs_conj_z, abs_z)
            assert_equal(conj_abs_z, abs_z)


class TestTrig(unittest.TestCase):
    def test_sin(self):
        a = blaze.array([0, math.pi/6, math.pi/3, 0.5*math.pi,
                         math.pi, 1.5*math.pi, 2*math.pi])
        b = blaze.array([0, 0.5, 0.5*blaze.sqrt(3), 1, 0, -1, 0])
        assert_allclose(blaze.sin(a), b, rtol=1e-15, atol=1e-15)
        assert_allclose(blaze.sin(-a), -b, rtol=1e-15, atol=1e-15)

    def test_cos(self):
        a = blaze.array([0, math.pi/6, math.pi/3, 0.5*math.pi,
                         math.pi, 1.5*math.pi, 2*math.pi])
        b = blaze.array([1, 0.5*blaze.sqrt(3), 0.5, 0, -1, 0, 1])
        assert_allclose(blaze.cos(a), b, rtol=1e-15, atol=1e-15)
        assert_allclose(blaze.cos(-a), b, rtol=1e-15, atol=1e-15)


def _check_branch_cut(f, x0, dx, re_sign=1, im_sign=-1, sig_zero_ok=False,
                      dtype=np.complex):
    """
    Check for a branch cut in a function.

    Assert that `x0` lies on a branch cut of function `f` and `f` is
    continuous from the direction `dx`.

    Parameters
    ----------
    f : func
        Function to check
    x0 : array-like
        Point on branch cut
    dx : array-like
        Direction to check continuity in
    re_sign, im_sign : {1, -1}
        Change of sign of the real or imaginary part expected
    sig_zero_ok : bool
        Whether to check if the branch cut respects signed zero (if applicable)
    dtype : dtype
        Dtype to check (should be complex)

    """
    x0 = np.atleast_1d(x0).astype(dtype)
    dx = np.atleast_1d(dx).astype(dtype)

    scale = np.finfo(dtype).eps * 1e3
    atol  = 1e-4

    y0 = f(x0)
    yp = f(x0 + dx*scale*np.absolute(x0)/np.absolute(dx))
    ym = f(x0 - dx*scale*np.absolute(x0)/np.absolute(dx))

    assert_(np.all(np.absolute(y0.real - yp.real) < atol), (y0, yp))
    assert_(np.all(np.absolute(y0.imag - yp.imag) < atol), (y0, yp))
    assert_(np.all(np.absolute(y0.real - ym.real*re_sign) < atol), (y0, ym))
    assert_(np.all(np.absolute(y0.imag - ym.imag*im_sign) < atol), (y0, ym))

    if sig_zero_ok:
        # check that signed zeros also work as a displacement
        jr = (x0.real == 0) & (dx.real != 0)
        ji = (x0.imag == 0) & (dx.imag != 0)

        x = -x0
        x.real[jr] = 0.*dx.real
        x.imag[ji] = 0.*dx.imag
        x = -x
        ym = f(x)
        ym = ym[jr | ji]
        y0 = y0[jr | ji]
        assert_(np.all(np.absolute(y0.real - ym.real*re_sign) < atol), (y0, ym))
        assert_(np.all(np.absolute(y0.imag - ym.imag*im_sign) < atol), (y0, ym))


class TestComplexFunctions(unittest.TestCase):
    funcs = [blaze.arcsin, blaze.arccos,  blaze.arctan, blaze.arcsinh,
             blaze.arccosh, blaze.arctanh, blaze.sin, blaze.cos, blaze.tan,
             blaze.exp, blaze.exp2, blaze.log, blaze.sqrt, blaze.log10,
             blaze.log2, blaze.log1p]

    def test_it(self):
        for f in self.funcs:
            if f is blaze.arccosh:
                x = 1.5
            else:
                x = .5
            fr = f(x)
            fz = f(complex(x))
            assert_almost_equal(fz.real, fr, err_msg='real part %s' % f)
            assert_almost_equal(fz.imag, 0., err_msg='imag part %s' % f)

    def test_precisions_consistent(self):
        z = 1 + 1j
        for f in self.funcs:
            fcf = f(blaze.array(z, dshape='complex[float32]'))
            fcd = f(blaze.array(z, dshape='complex[float64]'))
            assert_almost_equal(fcf, fcd, decimal=6, err_msg='fch-fcd %s' % f)

    def test_branch_cuts(self):
        # check branch cuts and continuity on them
        _check_branch_cut(blaze.log,   -0.5, 1j, 1, -1)
        _check_branch_cut(blaze.log2,  -0.5, 1j, 1, -1)
        _check_branch_cut(blaze.log10, -0.5, 1j, 1, -1)
        _check_branch_cut(blaze.log1p, -1.5, 1j, 1, -1)
        _check_branch_cut(blaze.sqrt,  -0.5, 1j, 1, -1)

        _check_branch_cut(blaze.arcsin, [-2, 2],   [1j, -1j], 1, -1)
        _check_branch_cut(blaze.arccos, [-2, 2],   [1j, -1j], 1, -1)
        _check_branch_cut(blaze.arctan, [-2j, 2j],  [1,  -1], -1, 1)

        _check_branch_cut(blaze.arcsinh, [-2j,  2j], [-1,   1], -1, 1)
        _check_branch_cut(blaze.arccosh, [-1, 0.5], [1j,  1j], 1, -1)
        _check_branch_cut(blaze.arctanh, [-2,   2], [1j, -1j], 1, -1)

        # check against bogus branch cuts: assert continuity between quadrants
        _check_branch_cut(blaze.arcsin, [-2j, 2j], [1,  1], 1, 1)
        _check_branch_cut(blaze.arccos, [-2j, 2j], [1,  1], 1, 1)
        _check_branch_cut(blaze.arctan, [-2,  2], [1j, 1j], 1, 1)

        _check_branch_cut(blaze.arcsinh, [-2,  2, 0], [1j, 1j, 1], 1, 1)
        _check_branch_cut(blaze.arccosh, [-2j, 2j, 2], [1,  1,  1j], 1, 1)
        _check_branch_cut(blaze.arctanh, [-2j, 2j, 0], [1,  1,  1j], 1, 1)

    @skip("These branch cuts are known to fail")
    def test_branch_cuts_failing(self):
        # XXX: signed zero not OK with ICC on 64-bit platform for log, see
        # http://permalink.gmane.org/gmane.comp.python.numeric.general/25335
        _check_branch_cut(blaze.log,   -0.5, 1j, 1, -1, True)
        _check_branch_cut(blaze.log2,  -0.5, 1j, 1, -1, True)
        _check_branch_cut(blaze.log10, -0.5, 1j, 1, -1, True)
        _check_branch_cut(blaze.log1p, -1.5, 1j, 1, -1, True)
        # XXX: signed zeros are not OK for sqrt or for the arc* functions
        _check_branch_cut(blaze.sqrt,  -0.5, 1j, 1, -1, True)
        _check_branch_cut(blaze.arcsin, [-2, 2],   [1j, -1j], 1, -1, True)
        _check_branch_cut(blaze.arccos, [-2, 2],   [1j, -1j], 1, -1, True)
        _check_branch_cut(blaze.arctan, [-2j, 2j],  [1,  -1], -1, 1, True)
        _check_branch_cut(blaze.arcsinh, [-2j,  2j], [-1,   1], -1, 1, True)
        _check_branch_cut(blaze.arccosh, [-1, 0.5], [1j,  1j], 1, -1, True)
        _check_branch_cut(blaze.arctanh, [-2,   2], [1j, -1j], 1, -1, True)

    def test_against_cmath(self):
        import cmath

        points = [-1-1j, -1+1j, +1-1j, +1+1j]
        name_map = {'arcsin': 'asin', 'arccos': 'acos', 'arctan': 'atan',
                    'arcsinh': 'asinh', 'arccosh': 'acosh', 'arctanh': 'atanh'}
        atol = 4*np.finfo(np.complex).eps
        for func in self.funcs:
            fname = func.name
            cname = name_map.get(fname, fname)
            try:
                cfunc = getattr(cmath, cname)
            except AttributeError:
                continue
            for p in points:
                a = complex(func(complex(p)))
                b = cfunc(p)
                self.assertTrue(abs(a - b) < atol,
                                "%s %s: %s; cmath: %s" % (fname, p, a, b))


class TestMaximum(unittest.TestCase):
    def test_float_nans(self):
        nan = blaze.nan
        arg1 = blaze.array([0, nan, nan])
        arg2 = blaze.array([nan, 0, nan])
        out = blaze.array([nan, nan, nan])
        assert_equal(blaze.maximum(arg1, arg2), out)

    def test_complex_nans(self):
        nan = blaze.nan
        for cnan in [complex(nan, 0), complex(0, nan), complex(nan, nan)]:
            arg1 = blaze.array([0, cnan, cnan])
            arg2 = blaze.array([cnan, 0, cnan])
            out = blaze.array([nan, nan, nan],
                              dshape=datashape.complex_float64)
            assert_equal(blaze.maximum(arg1, arg2), out)


class TestMinimum(unittest.TestCase):
    def test_float_nans(self):
        nan = blaze.nan
        arg1 = blaze.array([0,   nan, nan])
        arg2 = blaze.array([nan, 0,   nan])
        out = blaze.array([nan, nan, nan])
        assert_equal(blaze.minimum(arg1, arg2), out)

    def test_complex_nans(self):
        nan = blaze.nan
        for cnan in [complex(nan, 0), complex(0, nan), complex(nan, nan)]:
            arg1 = blaze.array([0, cnan, cnan])
            arg2 = blaze.array([cnan, 0, cnan])
            out = blaze.array([nan, nan, nan],
                              dshape=datashape.complex_float64)
            assert_equal(blaze.minimum(arg1, arg2), out)


class TestFmax(unittest.TestCase):
    def test_float_nans(self):
        nan = blaze.nan
        arg1 = blaze.array([0, nan, nan])
        arg2 = blaze.array([nan, 0, nan])
        out = blaze.array([0, 0, nan])
        assert_equal(blaze.fmax(arg1, arg2), out)

    def test_complex_nans(self):
        nan = blaze.nan
        for cnan in [complex(nan, 0), complex(0, nan), complex(nan, nan)]:
            arg1 = blaze.array([0, cnan, cnan])
            arg2 = blaze.array([cnan, 0, cnan])
            out = blaze.array([0, 0, nan],
                              dshape=datashape.complex_float64)
            assert_equal(blaze.fmax(arg1, arg2), out)


class TestFmin(unittest.TestCase):
    def test_float_nans(self):
        nan = blaze.nan
        arg1 = blaze.array([0, nan, nan])
        arg2 = blaze.array([nan, 0, nan])
        out = blaze.array([0, 0, nan])
        assert_equal(blaze.fmin(arg1, arg2), out)

    def test_complex_nans(self):
        nan = blaze.nan
        for cnan in [complex(nan, 0), complex(0, nan), complex(nan, nan)]:
            arg1 = blaze.array([0, cnan, cnan])
            arg2 = blaze.array([cnan, 0, cnan])
            out = blaze.array([0, 0, nan], dshape=datashape.complex_float64)
            assert_equal(blaze.fmin(arg1, arg2), out)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_types
from __future__ import absolute_import, division, print_function

import unittest

import numpy as np
import blaze
from blaze.datadescriptor import ddesc_as_py
from datashape import to_numpy_dtype


class TestBasicTypes(unittest.TestCase):

    def test_ints(self):
        types = ['int8', 'int16', 'int32', 'int64']
        for type_ in types:
            a = blaze.array(np.arange(3), dshape=type_)
            dtype = to_numpy_dtype(a.dshape)
            self.assertEqual(dtype, np.dtype(type_))
            self.assertEqual(ddesc_as_py(a.ddesc), [0, 1, 2])

    def test_uints(self):
        types = ['uint8', 'uint16', 'uint32', 'uint64']
        for type_ in types:
            a = blaze.array(np.arange(3), dshape=type_)
            dtype = to_numpy_dtype(a.dshape)
            self.assertEqual(dtype, np.dtype(type_))
            self.assertEqual(ddesc_as_py(a.ddesc), [0, 1, 2])

    def test_floats(self):
        #types = ['float16', 'float32', 'float64']
        types = ['float32', 'float64']
        for type_ in types:
            a = blaze.array(np.arange(3), dshape=type_)
            dtype = to_numpy_dtype(a.dshape)
            self.assertEqual(dtype, np.dtype(type_))
            if type_ != 'float16':
                # ddesc_as_py does not support this yet
                self.assertEqual(ddesc_as_py(a.ddesc), [0, 1, 2])

    def test_complex(self):
        types = ['complex64', 'complex128']
        for type_ in types:
            a = blaze.array(np.arange(3), dshape=type_)
            dtype = to_numpy_dtype(a.dshape)
            self.assertEqual(dtype, np.dtype(type_))
            # ddesc_as_py does not support complexes yet..
            self.assertEqual(ddesc_as_py(a.ddesc), [0, 1, 2])

########NEW FILE########
__FILENAME__ = test_utils
from blaze.utils import *
from unittest import TestCase


class Test_tmpfile(TestCase):
    def test_tmpfile(self):
        with tmpfile() as f:
            with open(f, 'w') as a:
                a.write('')
            with tmpfile() as g:
                assert f != g

        assert not os.path.exists(f)
        assert not os.path.exists(f)

########NEW FILE########
__FILENAME__ = utils
from itertools import islice
from contextlib import contextmanager
import tempfile
import os


def partition_all(n, seq):
    """ Split sequence into subsequences of size ``n``

    >>> list(partition_all(3, [1, 2, 3, 4, 5, 6, 7, 8, 9]))
    [(1, 2, 3), (4, 5, 6), (7, 8, 9)]

    The last element of the list may have fewer than ``n`` elements

    >>> list(partition_all(3, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10,)]
    """
    seq = iter(seq)
    while True:
        result = tuple(islice(seq, 0, n))
        if result:
            yield result
        else:
            raise StopIteration()


def nth(n, seq):
    """

    >>> nth(1, 'Hello, world!')
    'e'
    >>> nth(4, 'Hello, world!')
    'o'
    """
    seq = iter(seq)
    i = 0
    while i < n:
        i += 1
        next(seq)
    return next(seq)


@contextmanager
def filetext(text, extension='', open=open):
    with tmpfile(extension=extension) as filename:
        with open(filename, "w") as f:
            f.write(text)

        yield filename


@contextmanager
def filetexts(d, open=open):
    """ Dumps a number of textfiles to disk

    d - dict
        a mapping from filename to text like {'a.csv': '1,1\n2,2'}
    """
    for filename, text in d.items():
        with open(filename, 'w') as f:
            f.write(text)

    yield list(d)

    for filename in d:
        if os.path.exists(filename):
            os.remove(filename)


@contextmanager
def tmpfile(extension=''):
    filename = tempfile.mktemp(extension)

    yield filename

    if os.path.exists(filename):
        os.remove(filename)


def raises(err, lamda):
    try:
        lamda()
        return False
    except err:
        return True

########NEW FILE########
__FILENAME__ = gh-pages
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to commit the doc build outputs into the github-pages repo.

Use:

  gh-pages.py [tag]

If no tag is given, the current output of 'git describe' is used.  If given,
that is how the resulting directory will be named.

In practice, you should use either actual clean tags from a current build or
something like 'current' as a stable URL for the most current version of the """
from __future__ import print_function, division, absolute_import

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import os
import re
import shutil
import sys
from os import chdir as cd
from os.path import join as pjoin

from subprocess import Popen, PIPE, CalledProcessError, check_call

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------

pages_dir = 'gh-pages'
html_dir = 'build/html'
pdf_dir = 'build/latex'
pages_repo = 'git@github.com:ContinuumIO/blaze-webpage.git'

#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------
def sh(cmd):
    """Execute command in a subshell, return status code."""
    return check_call(cmd, shell=True)


def sh2(cmd):
    """Execute command in a subshell, return stdout.

    Stderr is unbuffered from the subshell.x"""
    p = Popen(cmd, stdout=PIPE, shell=True)
    out = p.communicate()[0]
    retcode = p.returncode
    if retcode:
        raise CalledProcessError(retcode, cmd)
    else:
        return out.rstrip()


def sh3(cmd):
    """Execute command in a subshell, return stdout, stderr

    If anything appears in stderr, print it out to sys.stderr"""
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    retcode = p.returncode
    if retcode:
        raise CalledProcessError(retcode, cmd)
    else:
        return out.rstrip(), err.rstrip()


def init_repo(path):
    """clone the gh-pages repo if we haven't already."""
    sh("git clone %s %s"%(pages_repo, path))
    here = os.getcwdu()
    cd(path)
    sh('git checkout gh-pages')
    cd(here)

#-----------------------------------------------------------------------------
# Script starts
#-----------------------------------------------------------------------------
if __name__ == '__main__':
    # The tag can be given as a positional argument
    try:
        tag = sys.argv[1]
    except IndexError:
        try:
            tag = sh2('git describe --exact-match')
        except CalledProcessError:
            tag = "dev"   # Fallback
            print("Using dev")
    
    startdir = os.getcwdu()
    if not os.path.exists(pages_dir):
        # init the repo
        init_repo(pages_dir)
    else:
        # ensure up-to-date before operating
        cd(pages_dir)
        sh('git checkout gh-pages')
        sh('git pull')
        cd(startdir)

    dest = pjoin(pages_dir, tag)

    # don't `make html` here, because gh-pages already depends on html in Makefile
    # sh('make html')
    if tag != 'dev':
        # only build pdf for non-dev targets
        #sh2('make pdf')
        pass

    # This is pretty unforgiving: we unconditionally nuke the destination
    # directory, and then copy the html tree in there
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(html_dir, dest)
    if tag != 'dev':
        #shutil.copy(pjoin(pdf_dir, 'ipython.pdf'), pjoin(dest, 'ipython.pdf'))
        pass

    try:
        cd(pages_dir)
        status = sh2('git status | head -1')
        branch = re.match('\# On branch (.*)$', status).group(1)
        if branch != 'gh-pages':
            e = 'On %r, git branch is %r, MUST be "gh-pages"' % (pages_dir,
                                                                 branch)
            raise RuntimeError(e)

        sh('git add -A %s' % tag)
        sh('git commit -m"Updated doc release: %s"' % tag)
        print()
        print('Most recent 3 commits:')
        sys.stdout.flush()
        sh('git --no-pager log --oneline HEAD~3..')
    finally:
        cd(startdir)

    print()
    print('Now verify the build in: %r' % dest)
    print("If everything looks good, 'git push'")

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Blaze documentation build configuration file, created by
# sphinx-quickstart on Mon Oct  8 12:29:11 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os, subprocess

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'sphinx.ext.doctest', 'sphinx.ext.extlinks',

              # Optional
              'sphinx.ext.graphviz',
              ]

# -- Math ---------------------------------------------------------------------

try:
    subprocess.call(["pdflatex", "--version"])
    extensions += ['sphinx.ext.pngmath']
except OSError:
    extensions += ['sphinx.ext.mathjax']

# -- Docstrings ---------------------------------------------------------------

try:
    import numpydoc
    extensions += ['numpydoc']
except ImportError:
    pass

# -- Diagrams -----------------------------------------------------------------

# TODO: check about the legal requirements of putting this in the
# tree. sphinx-ditaa is BSD so should be fine...

#try:
    #sys.path.append(os.path.abspath('sphinxext'))
    #extensions += ['sphinxext.ditaa']
    #diagrams = True
#except ImportError:
    #diagrams = False

# -----------------------------------------------------------------------------

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Blaze'
copyright = u'2012, Continuum Analytics'

#------------------------------------------------------------------------
# Path Munging
#------------------------------------------------------------------------

# This is beautiful... yeah
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../..'))

import re
import blaze
from blaze import __version__ as release

if 'dev' in release:
    release = release[:release.find('dev') + 3]
if release == 'unknown':
    version = release
else:
    version = re.match(r'\d+\.\d+(?:\.\d+)?', release).group()
#------------------------------------------------------------------------

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = release

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
exclude_patterns = []

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
pygments_style = 'tango'
highlight_language = 'python'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'bootstrap'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['themes']

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
html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'blazedoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'blaze.tex', u'Blaze Documentation',
   u'Continuum', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'blaze', u'Blaze Documentation',
     [u'Continuum'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'blaze', u'Blaze Documentation',
   u'Continuum Analytics', 'blaze', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

intersphinx_mapping = {
    'http://docs.python.org/dev': None,
}

doctest_global_setup = "import blaze"

########NEW FILE########
__FILENAME__ = array_creation
'''Sample module showing the creation of blaze arrays'''

from __future__ import absolute_import, division, print_function

import blaze

def print_section(a_string, level=0):
    spacing = 2 if level == 0 else 1
    underline = ['=', '-', '~', ' '][min(level,3)]

    print ('%s%s\n%s' % ('\n'*spacing,
                         a_string,
                         underline*len(a_string)))


print_section('building basic arrays')
# It is possible to build arrays from python lists
a = blaze.array([ 2, 3, 4 ])

# Arrays can be printed
print(a)

# The array will have a datashape. A datashape is a combination of the
# shape and dtype concept found in numpy. Note that when creating from
# a Python iterable, a datashape will be inferred.
print(a.dshape)

b = blaze.array([1.2, 3.5, 5.1])
print(b)
print(b.dshape)

# Arrays can be bi-dimensional
print_section('going 2d', level=1)
c = blaze.array([ [1, 2], [3, 4] ])
print(c)
print(c.dshape)

# or as many dimensions as you like
print_section('going 3d', level=1)
d = blaze.array([ [ [1, 2], [3, 4] ], [ [5, 6], [7, 8] ] ])
print(d)
print(d.dshape)

# --------------------------------------------------------------------

print_section ('building compressed in-memory arrays')

# A compressed array (backed by BLZ):
import blz
datadesc = blaze.BLZ_DDesc(mode='w', bparams=blz.bparams(clevel=5))
arr = blaze.array([1,2,3])
print(arr)

# --------------------------------------------------------------------

print_section('Explicit types in construction')
# It is possible to force a type in a given array. This allows a
# broader selection of types on construction.
e =  blaze.array([1, 2, 3], dshape='3 * float32')
print(e)

# Note that the dimensions in the datashape when creating from a
# collection can be omitted. If that's the case, the dimensions will
# be inferred. The following is thus equivalent:

f = blaze.array([1, 2, 3], dshape='float32')
print(f)

# --------------------------------------------------------------------

print_section('Alternative  constructors')

# Arrays can be created to be all zeros:
g = blaze.zeros('10 * 10 * int32')
print(g)

# All ones
h = blaze.ones('10 * 10 * float64')
print(h)

# --------------------------------------------------------------------

print_section('Indexing')

print_section('Indexing for read', level=1)
print ('starting with a 4d array')
array4d = blaze.ones('10 * 10 * 10 * 10 * float32')

def describe_array(label, array):
    print(label)
    print('dshape: ', array.dshape)
    print(array)

describe_array('base', array4d)
describe_array('index once', array4d[3])
describe_array('index twice', array4d[3,2])
describe_array('index thrice', array4d[3,2,4])
describe_array('index four times', array4d[3,2,4,1])


print_section('Indexing for write', level=1)
array4d[3,2,4,1] = 16.0

describe_array('base', array4d)
describe_array('index once', array4d[3])
describe_array('index twice', array4d[3,2])
describe_array('index thrice', array4d[3,2,4])
describe_array('index four times', array4d[3,2,4,1])

array4d[3,2,1] = 3.0

describe_array('base', array4d)
describe_array('index once', array4d[3])
describe_array('index twice', array4d[3,2])
describe_array('index thrice', array4d[3,2,4])
describe_array('index four times', array4d[3,2,4,1])


del describe_array

# --------------------------------------------------------------------

print_section('Persisted arrays')

# Create an empty array on-disk
dname = 'persisted.blz'
datadesc = blaze.BLZ_DDesc(dname, mode='w')
p = blaze.zeros('0 * float64', ddesc=datadesc)
# Feed it with some data
blaze.append(p, range(10))

print(repr(datadesc))
print('Before re-opening:', p)

# Re-open the dataset in 'r'ead-only mode
datadesc = blaze.BLZ_DDesc(dname, mode='r')
p2 = blaze.array(datadesc)

print('After re-opening:', p2)

# Remove the dataset on-disk completely
datadesc.remove()

########NEW FILE########
__FILENAME__ = array_operations
'''Sample script showing off array basic operations'''

from __future__ import absolute_import, division, print_function
from random import randint

import blaze


def make_test_array(datashape):
    return blaze.ones(datashape) * randint(1, 10)


def test_operations(datashape):
    a = make_test_array(datashape)
    b = make_test_array(datashape)
    print('a:\n', a)
    print('b:\n', b)
    print('a + b:\n', a + b)
    print('a - b:\n', a - b)
    print('a * b:\n', a * b)
    print('a / b:\n', a / b)
    print('blaze.max(a):\n', blaze.max(a))
    print('blaze.min(a):\n', blaze.min(a))
    print('blaze.product(a):\n', blaze.product(a))
    print('blaze.sum(a):\n', blaze.sum(a))


if __name__ == '__main__':
    test_operations('10 * float32')
    test_operations('10 * int32')
    test_operations('10 * 10 * float64')

########NEW FILE########
__FILENAME__ = blaze_function
# NOTE: This is all subject to change
"""
This guide will hopefully shed some light to how blaze functions can be
defined and implemented.

The idea is that blaze has a reference implementation for each operation it
defines in Python. Of course, others are free to add operations specific
to their problem domain, and have them participate in the blaze deferred
execution strategy.

Our goal is open-ended extension, of existing and new functions blaze knows
nothing about. The way this is currently realized is by defining a blaze
function. This function contains:

    * a reference implementation, callable from Python

        This has a type signature and may implement the operation or simply
        raise an exception

            @function('A -> A -> A', elementwise=True)
            def add(a, b):
                return a + b # We add the scalar elements together

        Here we classified the function as `elementwise`, which gets scalar
        inputs. Generally, blaze functions can be regarded as generalized
        ufuncs, and their inputs are the array dimensions they matched
        according to their signature.

        The 'A -> A -> A' part is the signature, which indicates a function
        taking two arguments of a compatible type (`A` and `A`) and returning
        another `A`. This means that the
        argument types must be the compatible, and arguments are subject to
        promotion. For instance, if we put in an (int, float), the system will
        automatically promote the int to a float. Note that the types in the
        signature, in this case the type variable `A`, are identified by
        position.

    * a set of overloaded implementations of certain implementation "kinds"

        e.g. we may have for the blaze.add function the following
        implementations:

            ckernel:

                overloaded ckernel for each type, e.g.

                    int32 ckernel_add(int32 a, int32 b) { return a + b; }
                    float32 ckernel_add(float32 a, float32 b) { return a + b; }

            sql:

                 overloaded sql implementation, this can be generic for
                 all numeric input types, e.g.:

                 @impl(blaze.add, 'A : numeric -> A -> A')
                 def sql_add(a, b):
                    # using dumb string interpolation to generate an SQL
                    # query
                    return "(%s + %s)" % (a, b)

The expression graph is then converted to AIR (the Array Intermediate
Representation), which is processed in a number of passes to:

    1) handle coercions
    2) assign "implementation backends" to each operation, depending on

        * location of data (in-memory, on-disk, distributed, silo, etc)
        * availability of implementation "kernels" (e.g. ckernel, sql, etc)

    This is done in a straightforward, greedy, best-effort fashion. There is
    no cost model to guide this process, we only try to mimimize data transfer.


When blaze functions are applied, it build an expression graph automatically,
which refers to the blaze function that was applied and the arguments it was
applied with. It performs type unification on the signatures of the reference
(python) implementation. This specifies the semantics of the blaze function,
and under composition the semantics of the entire blaze execution system. The
added benefit of having a pure-python reference implementation is that we can
run the execution system in "debug" mode which uses python to evaluate a blaze
expression.
"""

from __future__ import absolute_import, division, print_function
from itertools import cycle

import blaze
from blaze.compute.function import function


def broadcast_zip(a, b):
    """broadcasting zip"""
    assert len(a) == len(b) or len(a) == 1 or len(b) == 1
    n = max(len(a), len(b))
    for _, x, y in zip(range(n), cycle(a), cycle(b)):
        yield x, y


@function('(Axes... * Axis * DType, Axes... * Axis * bool) -> Axes..., var, DType')
def filter(array, conditions):
    """
    Filter elements from `array` according to `conditions`.

    This is the reference function that dictates the semantics, input and
    output types of any filter operation. The function may be satisfied by
    subsequent (faster) implementations.

    Example
    =======

    >>> filter([[1, 2],        [3, 4],       [5, 6]],
    ...        [[True, False], [True, True], [False, False]])
    [[1], [3, 4], []]
    """
    return py_filter(array, conditions, array.ndim)


def py_filter(array, conditions, dim):
    """Reference filter implementation in Python"""
    if dim == 1:
        result = [item for item, cond in bzip(array, conditions) if cond]
    else:
        result = []
        for item_subarr, conditions_subarr in bzip(array, conditions):
            result.append(py_filter(item_subarr, conditions_subarr, dim - 1))

    return result


def ooc_filter(array, conditions):
    pass


if __name__ == '__main__':
    #import numpy as np
    from dynd import nd

    arr = nd.array([[1, 2], [3, 4], [5, 6]])
    conditions = nd.array([[True, False], [True, True], [False, False]])
    expr = filter(arr, conditions)

    result = blaze.eval(expr, strategy='py')
    print(">>> result = filter([[1, 2], [3, 4], [5, 6]],\n"
          "                    [[True, False], [True, True], [False, False]])")
    print(">>> result")
    print(result)
    print(">>> type(result)")
    print(type(result))

    expr = filter(arr + 10, conditions)
    result = blaze.eval(expr, strategy='py')
    print(">>> result = filter([[1, 2], [3, 4], [5, 6]] + 10,\n"
          "                    [[True, False], [True, True], [False, False]])")
    print(">>> result")
    print(result)
    print(">>> type(result)")
    print(type(result))

########NEW FILE########
__FILENAME__ = simple-blz
'''Sample script showing off some simple filter operations (BLZ version)'''

from __future__ import absolute_import, division, print_function

import blaze


def make_array(path):
    ddesc = blaze.BLZ_DDesc(path, mode='w')
    arr = blaze.array([(i, i*2.) for i in range(100)],
                      'var * {myint: int32, myflt: float64}',
                      ddesc=ddesc)
    return arr


if __name__ == '__main__':
    # Create a persitent array on disk
    arr = make_array("test-filtering.blz")
    # Do the query
    res = arr.where('(myint < 10) & (myflt > 8)')
    # Print out some results
    print("Resulting array:", res)
    # Materialize the iterator in array and print it
    print("\nResults of the filter:\n", list(res))
    # Remove the persitent array
    arr.ddesc.remove()

########NEW FILE########
__FILENAME__ = simple-hdf5
'''Sample script showing off some simple filter operations (HDF5 version)'''

from __future__ import absolute_import, division, print_function

import blaze


def make_array(path):
    ddesc = blaze.HDF5_DDesc(path, '/table', mode='w')
    arr = blaze.array([(i, i*2.) for i in range(100)],
                      'var * {myint: int32, myflt: float64}',
                      ddesc=ddesc)
    return arr


if __name__ == '__main__':
    # Create a persitent array on disk
    arr = make_array("test-filtering.h5")
    # Do the query
    res = arr.where('(myint < 10) & (myflt > 8)')
    # Print out some results
    print("Resulting array:", res)
    # Materialize the iterator in array and print it
    print("\nResults of the filter:\n", list(res))
    # Remove the persitent array
    arr.ddesc.remove()

########NEW FILE########
__FILENAME__ = open_read_dataset
'''Sample module showing the creation of blaze arrays'''

from __future__ import absolute_import, division, print_function

import sys

import numpy as np
import blaze

try:
    import tables as tb
except ImportError:
    print("This example requires PyTables to run.")
    sys.exit()


def print_section(a_string, level=0):
    spacing = 2 if level == 0 else 1
    underline = ['=', '-', '~', ' '][min(level,3)]

    print ('%s%s\n%s' % ('\n'*spacing,
                         a_string,
                         underline*len(a_string)))

fname = "sample.h5"
print_section('building basic hdf5 files')
# Create a simple HDF5 file
a1 = np.array([[1, 2, 3], [4, 5, 6]], dtype="int32")
a2 = np.array([[1, 2, 3], [3, 2, 1]], dtype="int64")
t1 = np.array([(1, 2, 3), (3, 2, 1)], dtype="i4,i8,f8")
with tb.open_file(fname, "w") as f:
    f.create_array(f.root, 'a1', a1)
    f.create_table(f.root, 't1', t1)
    f.create_group(f.root, 'g')
    f.create_array(f.root.g, 'a2', a2)
    print("Created HDF5 file with the next contents:\n%s" % str(f))

print_section('opening and handling datasets in hdf5 files')
# Open an homogeneous dataset there
ddesc = blaze.HDF5_DDesc(fname, datapath="/a1", mode="r")
a = blaze.array(ddesc)
# Print it
print("/a1 contents:", a)
# Print the datashape
print("datashape for /a1:", a.dshape)

# Open another homogeneous dataset there
ddesc = blaze.HDF5_DDesc(fname, datapath="/g/a2", mode="r")
a = blaze.array(ddesc)
# Print it
print("/g/a2 contents:", a)
# Print the datashape
print("datashape for /g/a2:", a.dshape)

# Now, get an heterogeneous dataset
ddesc = blaze.HDF5_DDesc(fname, datapath="/t1", mode="r")
t = blaze.array(ddesc)
# Print it
print("/t1 contents:", t)
# Print the datashape
print("datashape for /t1:", t.dshape)

# Finally, get rid of the sample file
ddesc.remove()

########NEW FILE########
__FILENAME__ = ooc-groupby
"""
This script performs an out of core groupby operation for different datasets.

The datasets to be processed are normally in CSV files and the key and
value to be used for the grouping are defined programatically via small
functions (see toy_stream() and statsmodel_stream() for examples).

Those datasets included in statsmodel will require this package
installed (it is available in Anaconda, so it should be an easy
dependency to solve).

Usage: $ `script` dataset_class dataset_filename

`dataset_class` can be either 'toy', 'randhie' or 'contributions'.

'toy' is a self-contained dataset and is meant for debugging mainly.

The 'randhie' implements suport for the dataset with the same name
included in the statsmodel package.

Finally 'contributions' is meant to compute aggregations on the
contributions to the different US campaigns.  This latter requires a
second argument (datatset_filename) which is a CSV file downloaded from:
http://data.influenceexplorer.com/bulk/

"""

import sys
from itertools import islice
import io
import csv

import numpy as np
from dynd import nd, ndt
import blz

# Number of lines to read per each iteration
LPC = 1000

# Max number of chars to map for a bytes or string in NumPy
MAXCHARS = 64


def get_nptype(dtype, val):
    """Convert the `val` field in dtype into a numpy dtype."""
    dytype = dtype[nd.as_py(dtype.field_names).index(val)]
    # strings and bytes cannot be natively represented in numpy
    if dytype == ndt.string:
        nptype = np.dtype("U%d" % MAXCHARS)
    elif dytype == ndt.bytes:
        nptype = np.dtype("S%d" % MAXCHARS)
    else:
        # There should be no problems with the rest
        nptype = dytype.as_numpy()
    return nptype


def groupby(sreader, key, val, dtype, path=None, lines_per_chunk=LPC):
    """Group the `val` field in `sreader` stream of lines by `key` index.

    Parameters
    ----------
    sreader : iterator
        Iterator over a stream of CSV lines.
    key : string
        The name of the field to be grouped by.
    val : string
        The field name with the values that have to be grouped.
    dtype : dynd dtype
        The DyND data type with all the fields of the CSV lines,
        including the `key` and `val` names.
    path : string
        The path of the file where the BLZ array with the final
        grouping will be stored.  If None (default), the BLZ will be
        stored in-memory (and hence non-persistent).
    lines_per_chunk : int
        The number of chunks that have to be read to be grouped by
        in-memory.  For optimal perfomance, some experimentation
        should be needed.  The default value should work reasonably
        well, though.

    Returns
    -------
    output : BLZ table
        Returns a BLZ table with column names that are the groups
        resulting from the groupby operation.  The columns are filled
        with the `val` field of the lines delivered by `sreader`.

    """

    try:
        nptype = get_nptype(dtype, val)
    except ValueError:
        raise ValueError("`val` should be a valid field")

    # Start reading chunks
    prev_keys = set()
    while True:
        ndbuf = nd.array(islice(sreader, lines_per_chunk), dtype)
        if len(ndbuf) == 0: break   # CSV data exhausted

        # Do the groupby for this chunk
        keys = getattr(ndbuf, key)
        if val is None:
            vals = ndbuf
        else:
            vals = getattr(ndbuf, val)
        sby = nd.groupby(vals, keys)
        lkeys = nd.as_py(sby.groups)
        skeys = set(lkeys)
        # BLZ does not understand dynd objects (yet)
        sby = nd.as_py(sby.eval())

        if len(prev_keys) == 0:
            # Add the initial keys to a BLZ table
            columns = [np.array(sby[i], nptype) for i in range(len(lkeys))]
            ssby = blz.btable(columns=columns, names=lkeys, rootdir=path,
                              mode='w')
        else:
            # Have we new keys?
            new_keys = skeys.difference(prev_keys)
            for new_key in new_keys:
                # Get the index of the new key
                idx = lkeys.index(new_key)
                # and add the values as a new columns
                ssby.addcol(sby[idx], new_key, dtype=nptype)
            # Now fill the pre-existing keys
            existing_keys = skeys.intersection(prev_keys)
            for existing_key in existing_keys:
                # Get the index of the existing key
                idx = lkeys.index(existing_key)
                # and append the values here
                ssby[existing_key].append(sby[idx])

        # Add the new keys to the existing ones
        prev_keys |= skeys

    # Before returning, flush all data into disk
    if path is not None:
        ssby.flush()
    return ssby


# A CSV toy example
csvbuf = u"""k1,v1,1,u1
k2,v2,2,u2
k3,v3,3,u3
k4,v4,4,u4
k5,v5,5,u5
k5,v6,6,u6
k4,v7,7,u7
k4,v8,8,u8
k4,v9,9,u9
k1,v10,10,u9
k5,v11,11,u11
"""


def toy_stream():
    sreader = csv.reader(io.StringIO(csvbuf))
    # The dynd dtype for the CSV file above
    dt = ndt.type('{key: string, val1: string, val2: int32, val3: bytes}')
    # The name of the persisted table where the groupby will be stored
    return sreader, dt


# This access different datasets in statsmodel package
def statsmodel_stream(stream):
    import statsmodels.api as sm
    data = getattr(sm.datasets, stream)
    f = open(data.PATH, 'rb')
    if stream == 'randhie':
        # For a description of this dataset, see:
        # http://statsmodels.sourceforge.net/devel/datasets/generated/randhie.html
        f.readline()   # read out the headers line
        dtypes = ('{mdvis: string, lncoins: float32, idp: int32,'
                  ' lpi:float32, fmde: float32, physlm: float32,'
                  ' disea: float32, hlthg: int32, hlthf: int32,'
                  ' hlthp: int32}')
    else:
        raise NotImplementedError(
            "Importing this dataset has not been implemented yet")

    sreader = csv.reader(f)
    dtype = ndt.type(dtypes)
    return sreader, dtype

# For contributions to state and federal US campaings.
# CSV files can be downloaded from:
# http://data.influenceexplorer.com/bulk/
def contributions_stream(stream_file):
    f = open(stream_file, 'rb')
    # Description of this dataset
    headers = f.readline().strip()   # read out the headers line
    headers = headers.split(',')
    # The types for the different fields
    htypes = [ ndt.int32, ndt.int16, ndt.int16] + \
             [ ndt.string ] * 4 + \
             [ ndt.bool, ndt.float64 ] + \
             [ ndt.string ] * 33
    # Build the DyND data type
    dtype = ndt.make_struct(htypes, headers)
    sreader = csv.reader(f)
    return sreader, dtype


if __name__ == "__main__":

    if len(sys.argv) == 1:
        print("Specify a dataset from: [toy, randhie, contributions]")
        sys.exit()

    # Which dataset do we want to group?
    which = sys.argv[1]

    if which == "toy":
        # Get the CSV iterator and dtype of fields
        sreader, dt = toy_stream()
        # Do the actual sortby
        ssby = groupby(sreader, 'key', 'val1', dtype=dt, path=None,
                       lines_per_chunk=2)
    elif which == "randhie":
        # Get the CSV iterator and dtype of fields
        sreader, dt = statsmodel_stream(which)
        # Do the actual sortby
        ssby = groupby(sreader, 'mdvis', 'lncoins', dtype=dt, path=None)
    elif which == "contributions":
        # Get the CSV iterator and dtype of fields
        if len(sys.argv) < 3:
            print("Please specify a contributions file downloaded from: "
                  "http://data.influenceexplorer.com/bulk/")
            sys.exit()
        stream_file = sys.argv[2]
        sreader, dt = contributions_stream(stream_file)
        # Do the actual sortby
        ssby = groupby(
            sreader, 'recipient_party', 'amount', dtype=dt, path='contribs.blz')
    else:
        raise NotImplementedError(
            "parsing for `%s` dataset not implemented" % which)

    # Retrieve the data in the BLZ structure
    #ssby = blz.from_blz(path)  # open from disk, if ssby is persistent
    for key in ssby.names:
        values = ssby[key]
        if which in ('toy', 'randhie'):
            print "key:", key, values
        elif which == 'contributions':
            print "Party: '%s'\tAmount: %13.2f\t#contribs: %8d" % \
                  (key, values.sum(), len(values))

########NEW FILE########
__FILENAME__ = custom_py
import blaze
from dynd import nd, ndt

# Available variables from the Blaze loader:
#  `catconf`   Catalog configuration object
#  `impdata`   Import data from the .array file
#  `catpath`   Catalog path of the array
#  `fspath`    Equivalent filesystem path of the array
#  `dshape`    The datashape expected
#
# The loaded array must be placed in `result`.

begin = impdata['begin']
end = impdata['end']
result = blaze.array(nd.range(begin, end))

########NEW FILE########
__FILENAME__ = start_server
import sys, os
import blaze
from blaze.io.server.app import app

if len(sys.argv) > 1:
    cat_path = sys.argv[1]
else:
    cat_path = os.path.join(os.getcwd(), 'sample_arrays.yaml')

# Load the sample catalog, or from the selected path
blaze.catalog.load_config(cat_path)
print('Starting Blaze Server')
app.run(debug=True, port=8080, use_reloader=True)

########NEW FILE########
__FILENAME__ = blaze_sql
"""
This example shows some examples of how to access data in SQL databases using
blaze. It walks through how blaze syntax corresponds to SQL queries.

Select Queries
--------------


"""

from __future__ import absolute_import, division, print_function

import sqlite3 as db

from datashape import dshape
import blaze
from blaze.io.sql import sql_table


def create_sqlite_table():
    data = [
        (4,  "Gilbrecht", 17),
        (8,  "Bertrand", 48),
        (16, "Janssen", 32),
    ]

    conn = db.connect(":memory:")
    c = conn.cursor()
    c.execute("""create table MyTable
                 (id INTEGER, name TEXT, age INTEGER)""")
    c.executemany("""insert into MyTable
                     values (?, ?, ?)""", data)
    conn.commit()
    c.close()

    return conn

conn = create_sqlite_table()

# Describe the columns. Note: typically you would describe column
# with variables for the column size, e.g. dshape('a * int32')
table = sql_table('MyTable',
                  ['id', 'name', 'age'],
                  [dshape('int32'), dshape('string'), dshape('float64')],
                  conn)

# Prints details about table
print(table)

# Eval to print values
print(blaze.eval(table[:, 'id']))

########NEW FILE########
