__FILENAME__ = detect
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
Methods for detecting objects leading to pickling failures.
"""

from __future__ import absolute_import
from inspect import ismethod, isfunction, istraceback, isframe, iscode
from .pointers import parent, reference, at, parents, children

from .dill import _trace as trace
from .dill import PY3

def outermost(func): # is analogous to getsource(func,enclosing=True)
    """get outermost enclosing object (i.e. the outer function in a closure)

    NOTE: this is the object-equivalent of getsource(func, enclosing=True)
    """
    if PY3:
        if ismethod(func):
            _globals = func.__func__.__globals__ or {}
        elif isfunction(func):
            _globals = func.__globals__ or {}
        else:
            return #XXX: or raise? no matches
        _globals = _globals.items()
    else:
        if ismethod(func):
            _globals = func.im_func.func_globals or {}
        elif isfunction(func):
            _globals = func.func_globals or {}
        else:
            return #XXX: or raise? no matches
        _globals = _globals.iteritems()
    # get the enclosing source
    from .source import getsourcelines
    try: lines,lnum = getsourcelines(func, enclosing=True)
    except: #TypeError, IOError
        lines,lnum = [],None
    code = ''.join(lines)
    # get all possible names,objects that are named in the enclosing source
    _locals = ((name,obj) for (name,obj) in _globals if name in code)
    # now only save the objects that generate the enclosing block
    for name,obj in _locals: #XXX: don't really need 'name'
        try:
            if getsourcelines(obj) == (lines,lnum): return obj
        except: #TypeError, IOError
            pass
    return #XXX: or raise? no matches

def nestedcode(func): #XXX: or return dict of {co_name: co} ?
    """get the code objects for any nested functions (e.g. in a closure)"""
    func = code(func)
    if not iscode(func): return [] #XXX: or raise? no matches
    nested = []
    for co in func.co_consts:
        if co is None: continue
        co = code(co)
        if co: nested.append(co)
    return nested

def code(func):
    '''get the code object for the given function or method

    NOTE: use dill.source.getsource(CODEOBJ) to get the source code
    '''
    if PY3:
        im_func = '__func__'
        func_code = '__code__'
    else:
        im_func = 'im_func'
        func_code = 'func_code'
    if ismethod(func): func = getattr(func, im_func)
    if isfunction(func): func = getattr(func, func_code)
    if istraceback(func): func = func.tb_frame
    if isframe(func): func = func.f_code
    if iscode(func): return func
    return

def nested(func): #XXX: or return dict of {__name__: obj} ?
    """get any functions inside of func (e.g. inner functions in a closure)

    NOTE: results may differ if the function has been executed or not.
    If len(nestedcode(func)) > len(nested(func)), try calling func().
    If possible, python builds code objects, but delays building functions
    until func() is called.
    """
    if PY3:
        att1 = '__code__'
        att0 = '__func__'
    else:
        att1 = 'func_code' # functions
        att0 = 'im_func'   # methods

    import gc
    funcs = []
    # get the code objects, and try to track down by referrence
    for co in nestedcode(func):
        # look for function objects that refer to the code object
        for obj in gc.get_referrers(co):
            # get methods
            _ = getattr(obj, att0, None) # ismethod
            if getattr(_, att1, None) is co: funcs.append(obj)
            # get functions
            elif getattr(obj, att1, None) is co: funcs.append(obj)
            # get frame objects
            elif getattr(obj, 'f_code', None) is co: funcs.append(obj)
            # get code objects
            elif hasattr(obj, 'co_code') and obj is co: funcs.append(obj)
#     frameobjs => func.func_code.co_varnames not in func.func_code.co_cellvars
#     funcobjs => func.func_code.co_cellvars not in func.func_code.co_varnames
#     frameobjs are not found, however funcobjs are...
#     (see: test_mixins.quad ... and test_mixins.wtf)
#     after execution, code objects get compiled, and them may be found by gc
    return funcs


def freevars(func):
    """get objects defined in enclosing code that are referred to by func

    returns a dict of {name:object}"""
    if PY3:
        im_func = '__func__'
        func_code = '__code__'
        func_closure = '__closure__'
    else:
        im_func = 'im_func'
        func_code = 'func_code'
        func_closure = 'func_closure'
    if ismethod(func): func = getattr(func, im_func)
    if isfunction(func):
        closures = getattr(func, func_closure) or ()
        func = getattr(func, func_code).co_freevars # get freevars
    else:
        return {}
    return dict((name,c.cell_contents) for (name,c) in zip(func,closures))

def globalvars(func):
    """get objects defined in global scope that are referred to by func

    return a dict of {name:object}"""
    if PY3:
        im_func = '__func__'
        func_code = '__code__'
        func_globals = '__globals__'
    else:
        im_func = 'im_func'
        func_code = 'func_code'
        func_globals = 'func_globals'
    if ismethod(func): func = getattr(func, im_func)
    if isfunction(func):
        globs = getattr(func, func_globals) or {}
        func = getattr(func, func_code).co_names # get names
    else:
        return {}
    #NOTE: if name not in func_globals, then we skip it...
    return dict((name,globs[name]) for name in func if name in globs)

def varnames(func):
    """get names of variables defined by func

    returns a tuple (local vars, local vars referrenced by nested functions)"""
    func = code(func)
    if not iscode(func):
        return () #XXX: better ((),())? or None?
    return func.co_varnames, func.co_cellvars


def baditems(obj, exact=False, safe=False): #XXX: obj=globals() ?
    """get items in object that fail to pickle"""
    if not hasattr(obj,'__iter__'): # is not iterable
        return [j for j in (badobjects(obj,0,exact,safe),) if j is not None]
    obj = obj.values() if getattr(obj,'values',None) else obj
    _obj = [] # can't use a set, as items may be unhashable
    [_obj.append(badobjects(i,0,exact,safe)) for i in obj if i not in _obj]
    return [j for j in _obj if j is not None]


def badobjects(obj, depth=0, exact=False, safe=False):
    """get objects that fail to pickle"""
    from dill import pickles
    if not depth:
        if pickles(obj,exact,safe): return None
        return obj
    return dict(((attr, badobjects(getattr(obj,attr),depth-1,exact,safe)) \
           for attr in dir(obj) if not pickles(getattr(obj,attr),exact,safe)))

def badtypes(obj, depth=0, exact=False, safe=False):
    """get types for objects that fail to pickle"""
    from dill import pickles
    if not depth:
        if pickles(obj,exact,safe): return None
        return type(obj)
    return dict(((attr, badtypes(getattr(obj,attr),depth-1,exact,safe)) \
           for attr in dir(obj) if not pickles(getattr(obj,attr),exact,safe)))

def errors(obj, depth=0, exact=False, safe=False):
    """get errors for objects that fail to pickle"""
    from dill import pickles, copy
    if not depth:
        try:
            pik = copy(obj)
            if exact:
                assert pik == obj, \
                    "Unpickling produces %s instead of %s" % (pik,obj)
            assert type(pik) == type(obj), \
                "Unpickling produces %s instead of %s" % (type(pik),type(obj))
            return None
        except Exception:
            import sys
            return sys.exc_info()[1]
    return dict(((attr, errors(getattr(obj,attr),depth-1,exact,safe)) \
           for attr in dir(obj) if not pickles(getattr(obj,attr),exact,safe)))

del absolute_import


# EOF

########NEW FILE########
__FILENAME__ = dill
# -*- coding: utf-8 -*-
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
dill: a utility for serialization of python objects

Based on code written by Oren Tirosh and Armin Ronacher.
Extended to a (near) full set of the builtin types (in types module),
and coded to the pickle interface, by <mmckerns@caltech.edu>.
Initial port to python3 by Jonathan Dobson, continued by mmckerns.
Test against "all" python types (Std. Lib. CH 1-15 @ 2.7) by mmckerns.
Test against CH16+ Std. Lib. ... TBD.
"""
__all__ = ['dump','dumps','load','loads','dump_session','load_session',\
           'Pickler','Unpickler','register','copy','pickle','pickles',\
           'HIGHEST_PROTOCOL','DEFAULT_PROTOCOL',\
           'PicklingError','UnpicklingError']

import logging
log = logging.getLogger("dill")
log.addHandler(logging.StreamHandler())
def _trace(boolean):
    """print a trace through the stack when pickling; useful for debugging"""
    if boolean: log.setLevel(logging.INFO)
    else: log.setLevel(logging.WARN)
    return

import os
import sys
PY3 = (hex(sys.hexversion) >= '0x30000f0')
if PY3: #XXX: get types from dill.objtypes ?
    import builtins as __builtin__
    from pickle import _Pickler as StockPickler, _Unpickler as StockUnpickler
    from _thread import LockType
   #from io import IOBase
    from types import CodeType, FunctionType, MethodType, GeneratorType, \
        TracebackType, FrameType, ModuleType, BuiltinMethodType
    BufferType = memoryview #XXX: unregistered
    ClassType = type # no 'old-style' classes
    EllipsisType = type(Ellipsis)
   #FileType = IOBase
    NotImplementedType = type(NotImplemented)
    SliceType = slice
    TypeType = type # 'new-style' classes #XXX: unregistered
    XRangeType = range
    DictProxyType = type(object.__dict__)
else:
    import __builtin__
    from pickle import Pickler as StockPickler, Unpickler as StockUnpickler
    from thread import LockType
    from types import CodeType, FunctionType, ClassType, MethodType, \
         GeneratorType, DictProxyType, XRangeType, SliceType, TracebackType, \
         NotImplementedType, EllipsisType, FrameType, ModuleType, \
         BufferType, BuiltinMethodType, TypeType
from pickle import HIGHEST_PROTOCOL, PicklingError, UnpicklingError
try:
    from pickle import DEFAULT_PROTOCOL
except ImportError:
    DEFAULT_PROTOCOL = HIGHEST_PROTOCOL
import __main__ as _main_module
import marshal
import gc
# import zlib
from weakref import ReferenceType, ProxyType, CallableProxyType
from functools import partial
from operator import itemgetter, attrgetter
# new in python2.5
if hex(sys.hexversion) >= '0x20500f0':
    from types import MemberDescriptorType, GetSetDescriptorType
try:
    import ctypes
    HAS_CTYPES = True
except ImportError:
    HAS_CTYPES = False
try:
    from numpy import ufunc as NumpyUfuncType
except ImportError:
    NumpyUfuncType = None

# make sure to add these 'hand-built' types to _typemap
if PY3:
    CellType = type((lambda x: lambda y: x)(0).__closure__[0])
else:
    CellType = type((lambda x: lambda y: x)(0).func_closure[0])
WrapperDescriptorType = type(type.__repr__)
MethodDescriptorType = type(type.__dict__['mro'])
MethodWrapperType = type([].__repr__)
PartialType = type(partial(int,base=2))
SuperType = type(super(Exception, TypeError()))
ItemGetterType = type(itemgetter(0))
AttrGetterType = type(attrgetter('__repr__'))
FileType = type(open(os.devnull, 'rb', buffering=0))
TextWrapperType = type(open(os.devnull, 'r', buffering=-1))
BufferedRandomType = type(open(os.devnull, 'r+b', buffering=-1))
BufferedReaderType = type(open(os.devnull, 'rb', buffering=-1))
BufferedWriterType = type(open(os.devnull, 'wb', buffering=-1))
try:
    from _pyio import open as _open
    PyTextWrapperType = type(_open(os.devnull, 'r', buffering=-1))
    PyBufferedRandomType = type(_open(os.devnull, 'r+b', buffering=-1))
    PyBufferedReaderType = type(_open(os.devnull, 'rb', buffering=-1))
    PyBufferedWriterType = type(_open(os.devnull, 'wb', buffering=-1))
except ImportError:
    PyTextWrapperType = PyBufferedRandomType = PyBufferedReaderType = PyBufferedWriterType = None
try:
    from cStringIO import StringIO, InputType, OutputType
except ImportError:
    if PY3:
        from io import BytesIO as StringIO
    else:
        from StringIO import StringIO
    InputType = OutputType = None
try:
    __IPYTHON__ is True # is ipython
    ExitType = None     # IPython.core.autocall.ExitAutocall
    singletontypes = ['exit', 'quit', 'get_ipython']
except NameError:
    ExitType = type(exit)
    singletontypes = []

### Shorthands (modified from python2.5/lib/pickle.py)
def copy(obj, *args, **kwds):
    """use pickling to 'copy' an object"""
    return loads(dumps(obj, *args, **kwds))

def dump(obj, file, protocol=None, byref=False):
    """pickle an object to a file"""
    if protocol is None: protocol = DEFAULT_PROTOCOL
    pik = Pickler(file, protocol)
    pik._main_module = _main_module
    _byref = pik._byref
    pik._byref = bool(byref)
    pik.dump(obj)
    pik._byref = _byref
    return

def dumps(obj, protocol=None, byref=False):
    """pickle an object to a string"""
    file = StringIO()
    dump(obj, file, protocol, byref)
    return file.getvalue()

def load(file):
    """unpickle an object from a file"""
    pik = Unpickler(file)
    pik._main_module = _main_module
    obj = pik.load()
    if type(obj).__module__ == _main_module.__name__: # point obj class to main
        try: obj.__class__ == getattr(pik._main_module, type(obj).__name__)
        except AttributeError: pass # defined in a file
   #_main_module.__dict__.update(obj.__dict__) #XXX: should update globals ?
    return obj

def loads(str):
    """unpickle an object from a string"""
    file = StringIO(str)
    return load(file)

# def dumpzs(obj, protocol=None):
#     """pickle an object to a compressed string"""
#     return zlib.compress(dumps(obj, protocol))

# def loadzs(str):
#     """unpickle an object from a compressed string"""
#     return loads(zlib.decompress(str))

### End: Shorthands ###

### Pickle the Interpreter Session
def dump_session(filename='/tmp/session.pkl', main_module=_main_module):
    """pickle the current state of __main__ to a file"""
    f = open(filename, 'wb')
    try:
        pickler = Pickler(f, 2)
        pickler._main_module = main_module
        _byref = pickler._byref
        pickler._byref = False  # disable pickling by name reference
        pickler._session = True # is best indicator of when pickling a session
        pickler.dump(main_module)
        pickler._session = False
        pickler._byref = _byref
    finally:
        f.close()
    return

def load_session(filename='/tmp/session.pkl', main_module=_main_module):
    """update the __main__ module with the state from the session file"""
    f = open(filename, 'rb')
    try:
        unpickler = Unpickler(f)
        unpickler._main_module = main_module
        unpickler._session = True
        module = unpickler.load()
        unpickler._session = False
        main_module.__dict__.update(module.__dict__)
    finally:
        f.close()
    return

### End: Pickle the Interpreter

### Extend the Picklers
class Pickler(StockPickler):
    """python's Pickler extended to interpreter sessions"""
    dispatch = StockPickler.dispatch.copy()
    _main_module = None
    _session = False
    _byref = False
    pass

    def __init__(self, *args, **kwargs):
        StockPickler.__init__(self, *args, **kwargs)
        self._main_module = _main_module

class Unpickler(StockUnpickler):
    """python's Unpickler extended to interpreter sessions and more types"""
    _main_module = None
    _session = False

    def find_class(self, module, name):
        if (module, name) == ('__builtin__', '__main__'):
            return self._main_module.__dict__ #XXX: above set w/save_module_dict
        return StockUnpickler.find_class(self, module, name)
    pass

    def __init__(self, *args, **kwargs):
        StockUnpickler.__init__(self, *args, **kwargs)
        self._main_module = _main_module

'''
def dispatch_table():
    """get the dispatch table of registered types"""
    return Pickler.dispatch
'''

def pickle(t, func):
    """expose dispatch table for user-created extensions"""
    Pickler.dispatch[t] = func
    return

def register(t):
    def proxy(func):
        Pickler.dispatch[t] = func
        return func
    return proxy

def _create_typemap():
    import types
    if PY3:
        d = dict(list(__builtin__.__dict__.items()) + \
                 list(types.__dict__.items())).items()
        builtin = 'builtins'
    else:
        d = types.__dict__.iteritems()
        builtin = '__builtin__'
    for key, value in d:
        if getattr(value, '__module__', None) == builtin \
        and type(value) is type:
            yield key, value
    return
_reverse_typemap = dict(_create_typemap())
_reverse_typemap.update({
    'CellType': CellType,
    'WrapperDescriptorType': WrapperDescriptorType,
    'MethodDescriptorType': MethodDescriptorType,
    'MethodWrapperType': MethodWrapperType,
    'PartialType': PartialType,
    'SuperType': SuperType,
    'ItemGetterType': ItemGetterType,
    'AttrGetterType': AttrGetterType,
    'FileType': FileType,
    'BufferedRandomType': BufferedRandomType,
    'BufferedReaderType': BufferedReaderType,
    'BufferedWriterType': BufferedWriterType,
    'TextWrapperType': TextWrapperType,
    'PyBufferedRandomType': PyBufferedRandomType,
    'PyBufferedReaderType': PyBufferedReaderType,
    'PyBufferedWriterType': PyBufferedWriterType,
    'PyTextWrapperType': PyTextWrapperType,
})
if ExitType:
    _reverse_typemap['ExitType'] = ExitType
if InputType:
    _reverse_typemap['InputType'] = InputType
    _reverse_typemap['OutputType'] = OutputType
if PY3:
    _typemap = dict((v, k) for k, v in _reverse_typemap.items())
else:
    _typemap = dict((v, k) for k, v in _reverse_typemap.iteritems())

def _unmarshal(string):
    return marshal.loads(string)

def _load_type(name):
    return _reverse_typemap[name]

def _create_type(typeobj, *args):
    return typeobj(*args)

def _create_function(fcode, fglobals, fname=None, fdefaults=None, \
                                      fclosure=None, fdict=None):
    # same as FunctionType, but enable passing __dict__ to new function,
    # __dict__ is the storehouse for attributes added after function creation
    if fdict is None: fdict = dict()
    func = FunctionType(fcode, fglobals, fname, fdefaults, fclosure)
    func.__dict__.update(fdict) #XXX: better copy? option to copy?
    return func

def _create_ftype(ftypeobj, func, args, kwds):
    return ftypeobj(func, *args, **kwds)

def _create_lock(locked, *args):
    from threading import Lock
    lock = Lock()
    if locked:
        if not lock.acquire(False):
            raise UnpicklingError("Cannot acquire lock")
    return lock

def _create_filehandle(name, mode, position, closed, open=open): # buffering=0
    # only pickles the handle, not the file contents... good? or StringIO(data)?
    # (for file contents see: http://effbot.org/librarybook/copy-reg.htm)
    # NOTE: handle special cases first (are there more special cases?)
    names = {'<stdin>':sys.__stdin__, '<stdout>':sys.__stdout__,
             '<stderr>':sys.__stderr__} #XXX: better fileno=(0,1,2) ?
    if name in list(names.keys()): f = names[name] #XXX: safer "f=sys.stdin"
    elif name == '<tmpfile>': import os; f = os.tmpfile()
    elif name == '<fdopen>': import tempfile; f = tempfile.TemporaryFile(mode)
    else:
        try: # try to open the file by name   # NOTE: has different fileno
            f = open(name, mode)#FIXME: missing: *buffering*, encoding,softspace
        except IOError: 
            err = sys.exc_info()[1]
            try: # failing, then use /dev/null #XXX: better to just fail here?
                import os; f = open(os.devnull, mode)
            except IOError:
                raise UnpicklingError(err)
                #XXX: python default is closed '<uninitialized file>' file/mode
    if closed: f.close()
    elif position >= 0: f.seek(position)
    return f

def _create_stringi(value, position, closed):
    f = StringIO(value)
    if closed: f.close()
    else: f.seek(position)
    return f

def _create_stringo(value, position, closed):
    f = StringIO()
    if closed: f.close()
    else:
       f.write(value)
       f.seek(position)
    return f

class _itemgetter_helper(object):
    def __init__(self):
        self.items = []
    def __getitem__(self, item):
        self.items.append(item)
        return

class _attrgetter_helper(object):
    def __init__(self, attrs, index=None):
        self.attrs = attrs
        self.index = index
    def __getattribute__(self, attr):
        attrs = object.__getattribute__(self, "attrs")
        index = object.__getattribute__(self, "index")
        if index is None:
            index = len(attrs)
            attrs.append(attr)
        else:
            attrs[index] = ".".join([attrs[index], attr])
        return type(self)(attrs, index)

if HAS_CTYPES:
    ctypes.pythonapi.PyCell_New.restype = ctypes.py_object
    ctypes.pythonapi.PyCell_New.argtypes = [ctypes.py_object]
    # thanks to Paul Kienzle for cleaning the ctypes CellType logic
    def _create_cell(contents):
        return ctypes.pythonapi.PyCell_New(contents)

def _create_weakref(obj, *args):
    from weakref import ref
    if obj is None: # it's dead
        if PY3:
            from collections import UserDict
        else:
            from UserDict import UserDict
        return ref(UserDict(), *args)
    return ref(obj, *args)

def _create_weakproxy(obj, callable=False, *args):
    from weakref import proxy
    if obj is None: # it's dead
        if callable: return proxy(lambda x:x, *args)
        if PY3:
            from collections import UserDict
        else:
            from UserDict import UserDict
        return proxy(UserDict(), *args)
    return proxy(obj, *args)

def _eval_repr(repr_str):
    return eval(repr_str)

def _getattr(objclass, name, repr_str):
    # hack to grab the reference directly
    try: #XXX: works only for __builtin__ ?
        attr = repr_str.split("'")[3]
        return eval(attr+'.__dict__["'+name+'"]')
    except:
        attr = getattr(objclass,name)
        if name == '__dict__':
            attr = attr[name]
        return attr

def _get_attr(self, name):
    # stop recursive pickling
    return getattr(self, name)

def _dict_from_dictproxy(dictproxy):
    _dict = dictproxy.copy() # convert dictproxy to dict
    _dict.pop('__dict__', None)
    _dict.pop('__weakref__', None)
    return _dict

def _import_module(import_name, safe=False):
    try:
        if '.' in import_name:
            items = import_name.split('.')
            module = '.'.join(items[:-1])
            obj = items[-1]
        else:
            return __import__(import_name)
        return getattr(__import__(module, None, None, [obj]), obj)
    except (ImportError, AttributeError):
        if safe:
            return None
        raise

def _locate_function(obj, session=False):
    if obj.__module__ == '__main__': # and session:
        return False
    found = _import_module(obj.__module__ + '.' + obj.__name__, safe=True)
    return found is obj

@register(CodeType)
def save_code(pickler, obj):
    log.info("Co: %s" % obj)
    pickler.save_reduce(_unmarshal, (marshal.dumps(obj),), obj=obj)
    return

@register(FunctionType)
def save_function(pickler, obj):
    if not _locate_function(obj): #, pickler._session):
        log.info("F1: %s" % obj)
        if PY3:
            pickler.save_reduce(_create_function, (obj.__code__, 
                                obj.__globals__, obj.__name__,
                                obj.__defaults__, obj.__closure__,
                                obj.__dict__), obj=obj)
        else:
            pickler.save_reduce(_create_function, (obj.func_code,
                                obj.func_globals, obj.func_name,
                                obj.func_defaults, obj.func_closure,
                                obj.__dict__), obj=obj)
    else:
        log.info("F2: %s" % obj)
        StockPickler.save_global(pickler, obj) #NOTE: also takes name=...
    return

@register(dict)
def save_module_dict(pickler, obj):
    if is_dill(pickler) and obj == pickler._main_module.__dict__ and not pickler._session:
        log.info("D1: <dict%s" % str(obj.__repr__).split('dict')[-1]) # obj
        if PY3:
            pickler.write(bytes('c__builtin__\n__main__\n', 'UTF-8'))
        else:
            pickler.write('c__builtin__\n__main__\n')
    elif not is_dill(pickler) and obj == _main_module.__dict__:
        log.info("D3: <dict%s" % str(obj.__repr__).split('dict')[-1]) # obj
        if PY3:
            pickler.write(bytes('c__main__\n__dict__\n', 'UTF-8'))
        else:
            pickler.write('c__main__\n__dict__\n')   #XXX: works in general?
    elif '__name__' in obj and obj != _main_module.__dict__ \
    and obj is getattr(_import_module(obj['__name__'],True), '__dict__', None):
        log.info("D4: <dict%s" % str(obj.__repr__).split('dict')[-1]) # obj
        if PY3:
            pickler.write(bytes('c%s\n__dict__\n' % obj['__name__'], 'UTF-8'))
        else:
            pickler.write('c%s\n__dict__\n' % obj['__name__'])
    else:
        log.info("D2: <dict%s" % str(obj.__repr__).split('dict')[-1]) # obj
        if is_dill(pickler) and pickler._session:
            # we only care about session the first pass thru
            pickler._session = False 
        StockPickler.save_dict(pickler, obj)
    return

@register(ClassType)
def save_classobj(pickler, obj):
    if obj.__module__ == '__main__': #XXX: use _main_module.__name__ everywhere?
        log.info("C1: %s" % obj)
        pickler.save_reduce(ClassType, (obj.__name__, obj.__bases__,
                                        obj.__dict__), obj=obj)
                                       #XXX: or obj.__dict__.copy()), obj=obj) ?
    else:
        log.info("C2: %s" % obj)
        StockPickler.save_global(pickler, obj)
    return

@register(LockType)
def save_lock(pickler, obj):
    log.info("Lo: %s" % obj)
    pickler.save_reduce(_create_lock, (obj.locked(),), obj=obj)
    return

@register(ItemGetterType)
def save_itemgetter(pickler, obj):
    log.info("Ig: %s" % obj)
    helper = _itemgetter_helper()
    obj(helper)
    pickler.save_reduce(type(obj), tuple(helper.items), obj=obj)
    return

@register(AttrGetterType)
def save_attrgetter(pickler, obj):
    log.info("Ag: %s" % obj)
    attrs = []
    helper = _attrgetter_helper(attrs)
    obj(helper)
    pickler.save_reduce(type(obj), tuple(attrs), obj=obj)
    return

# __getstate__ explicitly added to raise TypeError when pickling:
# http://www.gossamer-threads.com/lists/python/bugs/871199
@register(FileType) #XXX: in 3.x has buffer=0, needs different _create?
@register(BufferedRandomType)
@register(BufferedReaderType)
@register(BufferedWriterType)
@register(TextWrapperType)
def save_file(pickler, obj):
    log.info("Fi: %s" % obj)
    if obj.closed:
        position = None
    else:
        if obj in (sys.__stdout__, sys.__stderr__, sys.__stdin__):
            position = -1
        else:
            position = obj.tell()
    pickler.save_reduce(_create_filehandle, (obj.name, obj.mode, position, \
                                             obj.closed), obj=obj)
    return

if PyTextWrapperType: #XXX: are stdout, stderr or stdin ever _pyio files?
    @register(PyBufferedRandomType)
    @register(PyBufferedReaderType)
    @register(PyBufferedWriterType)
    @register(PyTextWrapperType)
    def save_file(pickler, obj):
        log.info("Fi: %s" % obj)
        if obj.closed:
            position = None
        else:
            position = obj.tell()
        pickler.save_reduce(_create_filehandle, (obj.name, obj.mode, position, \
                                                 obj.closed, _open), obj=obj)
        return

# The following two functions are based on 'saveCStringIoInput'
# and 'saveCStringIoOutput' from spickle
# Copyright (c) 2011 by science+computing ag
# License: http://www.apache.org/licenses/LICENSE-2.0
if InputType:
    @register(InputType)
    def save_stringi(pickler, obj):
        log.info("Io: %s" % obj)
        if obj.closed:
            value = ''; position = None
        else:
            value = obj.getvalue(); position = obj.tell()
        pickler.save_reduce(_create_stringi, (value, position, \
                                              obj.closed), obj=obj)
        return

    @register(OutputType)
    def save_stringo(pickler, obj):
        log.info("Io: %s" % obj)
        if obj.closed:
            value = ''; position = None
        else:
            value = obj.getvalue(); position = obj.tell()
        pickler.save_reduce(_create_stringo, (value, position, \
                                              obj.closed), obj=obj)
        return

@register(PartialType)
def save_functor(pickler, obj):
    log.info("Fu: %s" % obj)
    pickler.save_reduce(_create_ftype, (type(obj), obj.func, obj.args,
                                        obj.keywords), obj=obj)
    return

@register(SuperType)
def save_functor(pickler, obj):
    log.info("Su: %s" % obj)
    pickler.save_reduce(super, (obj.__thisclass__, obj.__self__), obj=obj)
    return

@register(BuiltinMethodType)
def save_builtin_method(pickler, obj):
    if obj.__self__ is not None:
        log.info("B1: %s" % obj)
        pickler.save_reduce(_get_attr, (obj.__self__, obj.__name__), obj=obj)
    else:
        log.info("B2: %s" % obj)
        StockPickler.save_global(pickler, obj)
    return

@register(MethodType) #FIXME: fails for 'hidden' or 'name-mangled' classes
def save_instancemethod0(pickler, obj):# example: cStringIO.StringI
    log.info("Me: %s" % obj) #XXX: obj.__dict__ handled elsewhere?
    if PY3:
        pickler.save_reduce(MethodType, (obj.__func__, obj.__self__), obj=obj)
    else:
        pickler.save_reduce(MethodType, (obj.im_func, obj.im_self,
                                         obj.im_class), obj=obj)
    return

if hex(sys.hexversion) >= '0x20500f0':
    @register(MemberDescriptorType)
    @register(GetSetDescriptorType)
    @register(MethodDescriptorType)
    @register(WrapperDescriptorType)
    def save_wrapper_descriptor(pickler, obj):
        log.info("Wr: %s" % obj)
        pickler.save_reduce(_getattr, (obj.__objclass__, obj.__name__,
                                       obj.__repr__()), obj=obj)
        return

    @register(MethodWrapperType)
    def save_instancemethod(pickler, obj):
        log.info("Mw: %s" % obj)
        pickler.save_reduce(getattr, (obj.__self__, obj.__name__), obj=obj)
        return
else:
    @register(MethodDescriptorType)
    @register(WrapperDescriptorType)
    def save_wrapper_descriptor(pickler, obj):
        log.info("Wr: %s" % obj)
        pickler.save_reduce(_getattr, (obj.__objclass__, obj.__name__,
                                       obj.__repr__()), obj=obj)
        return

if HAS_CTYPES:
    @register(CellType)
    def save_cell(pickler, obj):
        log.info("Ce: %s" % obj)
        pickler.save_reduce(_create_cell, (obj.cell_contents,), obj=obj)
        return
 
# The following function is based on 'saveDictProxy' from spickle
# Copyright (c) 2011 by science+computing ag
# License: http://www.apache.org/licenses/LICENSE-2.0
@register(DictProxyType)
def save_dictproxy(pickler, obj):
    log.info("Dp: %s" % obj)
    attr = obj.get('__dict__')
   #pickler.save_reduce(_create_dictproxy, (attr,'nested'), obj=obj)
    if type(attr) == GetSetDescriptorType and attr.__name__ == "__dict__" \
    and getattr(attr.__objclass__, "__dict__", None) == obj:
        pickler.save_reduce(getattr, (attr.__objclass__, "__dict__"), obj=obj)
        return
    # all bad below... so throw ReferenceError or TypeError
    from weakref import ReferenceError
    raise ReferenceError("%s does not reference a class __dict__" % obj)

@register(SliceType)
def save_slice(pickler, obj):
    log.info("Sl: %s" % obj)
    pickler.save_reduce(slice, (obj.start, obj.stop, obj.step), obj=obj)
    return

@register(XRangeType)
@register(EllipsisType)
@register(NotImplementedType)
def save_singleton(pickler, obj):
    log.info("Si: %s" % obj)
    pickler.save_reduce(_eval_repr, (obj.__repr__(),), obj=obj)
    return

# thanks to Paul Kienzle for pointing out ufuncs didn't pickle
if NumpyUfuncType:
    @register(NumpyUfuncType)
    def save_numpy_ufunc(pickler, obj):
        log.info("Nu: %s" % obj)
        StockPickler.save_global(pickler, obj)
        return
# NOTE: the above 'save' performs like:
#   import copy_reg
#   def udump(f): return f.__name__
#   def uload(name): return getattr(numpy, name)
#   copy_reg.pickle(NumpyUfuncType, udump, uload)

def _proxy_helper(obj): # a dead proxy returns a reference to None
    """get memory address of proxy's reference object"""
    try: #FIXME: has to be a smarter way to identify if it's a proxy
        address = int(repr(obj).rstrip('>').split(' at ')[-1], base=16)
    except ValueError: # has a repr... is thus probably not a proxy
        address = id(obj)
    return address

def _locate_object(address, module=None):
    """get object located at the given memory address (inverse of id(obj))"""
    special = [None, True, False] #XXX: more...?
    for obj in special:
        if address == id(obj): return obj
    if module:
        if PY3:
            objects = iter(module.__dict__.values())
        else:
            objects = module.__dict__.itervalues()
    else: objects = iter(gc.get_objects())
    for obj in objects:
        if address == id(obj): return obj
    # all bad below... nothing found so throw ReferenceError or TypeError
    from weakref import ReferenceError
    try: address = hex(address)
    except TypeError:
        raise TypeError("'%s' is not a valid memory address" % str(address))
    raise ReferenceError("Cannot reference object at '%s'" % address)

@register(ReferenceType)
def save_weakref(pickler, obj):
    refobj = obj()
    log.info("Rf: %s" % obj)
   #refobj = ctypes.pythonapi.PyWeakref_GetObject(obj) # dead returns "None"
    pickler.save_reduce(_create_weakref, (refobj,), obj=obj)
    return

@register(ProxyType)
@register(CallableProxyType)
def save_weakproxy(pickler, obj):
    refobj = _locate_object(_proxy_helper(obj))
    try: log.info("Rf: %s" % obj)
    except ReferenceError: log.info("Rf: %s" % sys.exc_info()[1])
   #callable = bool(getattr(refobj, '__call__', None))
    if type(obj) is CallableProxyType: callable = True
    else: callable = False
    pickler.save_reduce(_create_weakproxy, (refobj, callable), obj=obj)
    return

@register(ModuleType)
def save_module(pickler, obj):
    # if a module file name starts with this, it should be a standard module,
    # so should be pickled as a reference
    prefix = sys.base_prefix if PY3 else sys.prefix
    std_mod = getattr(obj, "__file__", prefix).startswith(prefix)
    if obj.__name__ not in ("builtins", "dill") \
       and not std_mod or is_dill(pickler) and obj is pickler._main_module:
        log.info("M1: %s" % obj)
        _main_dict = obj.__dict__.copy() #XXX: better no copy? option to copy?
        [_main_dict.pop(item, None) for item in singletontypes
         + ["__builtins__", "__loader__"]]
        pickler.save_reduce(_import_module, (obj.__name__,), obj=obj,
                            state=_main_dict)
    else:
        log.info("M2: %s" % obj)
        pickler.save_reduce(_import_module, (obj.__name__,), obj=obj)
    return

@register(TypeType)
def save_type(pickler, obj):
    if obj in _typemap:
        log.info("T1: %s" % obj)
        pickler.save_reduce(_load_type, (_typemap[obj],), obj=obj)
    elif obj.__module__ == '__main__':
        try: # use StockPickler for special cases [namedtuple,]
            [getattr(obj, attr) for attr in ('_fields','_asdict',
                                             '_make','_replace')]
            log.info("T6: %s" % obj)
            StockPickler.save_global(pickler, obj)
            return
        except AttributeError: pass
        if type(obj) == type:
        #   try: # used when pickling the class as code (or the interpreter)
            if is_dill(pickler) and not pickler._byref:
                # thanks to Tom Stepleton pointing out pickler._session unneeded
                log.info("T2: %s" % obj)
                _dict = _dict_from_dictproxy(obj.__dict__)
        #   except: # punt to StockPickler (pickle by class reference)
            else:
                log.info("T5: %s" % obj)
                StockPickler.save_global(pickler, obj)
                return
        else:
            log.info("T3: %s" % obj)
            _dict = obj.__dict__
       #print (_dict)
       #print ("%s\n%s" % (type(obj), obj.__name__))
       #print ("%s\n%s" % (obj.__bases__, obj.__dict__))
        pickler.save_reduce(_create_type, (type(obj), obj.__name__,
                                           obj.__bases__, _dict), obj=obj)
    else:
        log.info("T4: %s" % obj)
       #print (obj.__dict__)
       #print ("%s\n%s" % (type(obj), obj.__name__))
       #print ("%s\n%s" % (obj.__bases__, obj.__dict__))
        StockPickler.save_global(pickler, obj)
    return

# quick sanity checking
def pickles(obj,exact=False,safe=False,**kwds):
    """quick check if object pickles with dill"""
    if safe: exceptions = (Exception,) # RuntimeError, ValueError
    else:
        exceptions = (TypeError, AssertionError, PicklingError, UnpicklingError)
    try:
        pik = copy(obj, **kwds)
        if exact:
            return pik == obj
        return type(pik) == type(obj)
    except exceptions:
        return False

# use to protect against missing attributes
def is_dill(pickler):
    "check the dill-ness of your pickler"
    return 'dill' in pickler.__module__
   #return hasattr(pickler,'_main_module')

def _extend():
    """extend pickle with all of dill's registered types"""
    # need to have pickle not choke on _main_module?  use is_dill(pickler)
    for t,func in Pickler.dispatch.items():
        try:
            StockPickler.dispatch[t] = func
        except: #TypeError, PicklingError, UnpicklingError
            log.info("skip: %s" % t)
        else: pass
    return

# EOF

########NEW FILE########
__FILENAME__ = objtypes
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
all Python Standard Library object types (currently: CH 1-15 @ 2.7)
and some other common object types (i.e. numpy.ndarray)

to load more objects and types, use dill.load_types()
"""

from __future__ import absolute_import

# non-local import of dill.objects
from dill import objects
for _type in objects.keys():
    exec("%s = type(objects['%s'])" % (_type,_type))
    
del objects
try:
    del _type
except NameError:
    pass

del absolute_import

########NEW FILE########
__FILENAME__ = pointers
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

from __future__ import absolute_import
__all__ = ['parent', 'reference', 'at', 'parents', 'children']

import gc
import sys

from .dill import _proxy_helper as reference
from .dill import _locate_object as at

def parent(obj, objtype, ignore=()):
    """
>>> listiter = iter([4,5,6,7])
>>> obj = parent(listiter, list)
>>> obj == [4,5,6,7]  # actually 'is', but don't have handle any longer
True

NOTE: objtype can be a single type (e.g. int or list) or a tuple of types.

WARNING: if obj is a sequence (e.g. list), may produce unexpected results.
Parent finds *one* parent (e.g. the last member of the sequence).
    """
    depth = 1 #XXX: always looking for the parent (only, right?)
    chain = parents(obj, objtype, depth, ignore)
    parent = chain.pop()
    if parent is obj:
        return None
    return parent


def parents(obj, objtype, depth=1, ignore=()): #XXX: objtype=object ?
    """Find the chain of referents for obj. Chain will end with obj.

    objtype: an object type or tuple of types to search for
    depth: search depth (e.g. depth=2 is 'grandparents')
    ignore: an object or tuple of objects to ignore in the search
    """
    edge_func = gc.get_referents # looking for refs, not back_refs
    predicate = lambda x: isinstance(x, objtype) # looking for parent type
   #if objtype is None: predicate = lambda x: True #XXX: in obj.mro() ?
    ignore = (ignore,) if not hasattr(ignore, '__len__') else ignore
    ignore = (id(obj) for obj in ignore)
    chain = find_chain(obj, predicate, edge_func, depth)[::-1]
    #XXX: should pop off obj... ?
    return chain


def children(obj, objtype, depth=1, ignore=()): #XXX: objtype=object ?
    """Find the chain of referrers for obj. Chain will start with obj.

    objtype: an object type or tuple of types to search for
    depth: search depth (e.g. depth=2 is 'grandparents')
    ignore: an object or tuple of objects to ignore in the search

    NOTE: a common thing to ignore is all globals, 'ignore=globals()'

    NOTE: repeated calls may yield different results, as python stores
    the last value in the special variable '_'; thus, it is often good
    to execute something to replace '_' (e.g. >>> 1+1).
    """
    edge_func = gc.get_referrers # looking for back_refs, not refs
    predicate = lambda x: isinstance(x, objtype) # looking for child type
   #if objtype is None: predicate = lambda x: True #XXX: in obj.mro() ?
    ignore = (ignore,) if not hasattr(ignore, '__len__') else ignore
    ignore = (id(obj) for obj in ignore)
    chain = find_chain(obj, predicate, edge_func, depth, ignore)
    #XXX: should pop off obj... ?
    return chain


# more generic helper function (cut-n-paste from objgraph)
# Source at http://mg.pov.lt/objgraph/
# Copyright (c) 2008-2010 Marius Gedminas <marius@pov.lt>
# Copyright (c) 2010 Stefano Rivera <stefano@rivera.za.net>
# Released under the MIT licence (see objgraph/objgrah.py)

def find_chain(obj, predicate, edge_func, max_depth=20, extra_ignore=()):
    queue = [obj]
    depth = {id(obj): 0}
    parent = {id(obj): None}
    ignore = set(extra_ignore)
    ignore.add(id(extra_ignore))
    ignore.add(id(queue))
    ignore.add(id(depth))
    ignore.add(id(parent))
    ignore.add(id(ignore))
    ignore.add(id(sys._getframe()))  # this function
    ignore.add(id(sys._getframe(1))) # find_chain/find_backref_chain, likely
    gc.collect()
    while queue:
        target = queue.pop(0)
        if predicate(target):
            chain = [target]
            while parent[id(target)] is not None:
                target = parent[id(target)]
                chain.append(target)
            return chain
        tdepth = depth[id(target)]
        if tdepth < max_depth:
            referrers = edge_func(target)
            ignore.add(id(referrers))
            for source in referrers:
                if id(source) in ignore:
                    continue
                if id(source) not in depth:
                    depth[id(source)] = tdepth + 1
                    parent[id(source)] = target
                    queue.append(source)
    return [obj] # not found


# backward compatability
refobject = at


# EOF

########NEW FILE########
__FILENAME__ = source
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
#
# inspired by inspect.py from Python-2.7.6
# inspect.py author: 'Ka-Ping Yee <ping@lfw.org>'
# inspect.py merged into original dill.source by Mike McKerns 4/13/14
"""
Extensions to python's 'inspect' module, which can be used
to retrieve information from live python objects. The methods
defined in this module are augmented to facilitate access to 
source code of interactively defined functions and classes,
as well as provide access to source code for objects defined
in a file.
"""

from __future__ import absolute_import
__all__ = ['findsource', 'getsourcelines', 'getsource', 'indent', 'outdent', \
           '_wrap', 'dumpsource', 'getname', '_namespace', 'getimport', \
           '_importable', 'importable']

import re
import linecache
from tokenize import TokenError
from inspect import ismodule, isclass, ismethod, isfunction, istraceback
from inspect import isframe, iscode, getfile, getmodule, getsourcefile
from inspect import getblock, indentsize, isbuiltin
from .dill import PY3


def _matchlambda(func, line):
    """check if lambda object 'func' matches raw line of code 'line'"""
    from dill.detect import code as getcode
    from dill.detect import freevars, globalvars, varnames
    dummy = lambda : '__this_is_a_big_dummy_function__'
    # process the line (removing leading whitespace, etc)
    lhs,rhs = line.split('lambda ',1)[-1].split(":", 1) #FIXME: if !1 inputs
    try: #FIXME: unsafe
        _ = eval("lambda %s : %s" % (lhs,rhs), globals(),locals())
    except: _ = dummy
    # get code objects, for comparison
    _, code = getcode(_).co_code, getcode(func).co_code
    # check if func is in closure
    _f = [line.count(i) for i in freevars(func).keys()]
    if not _f: # not in closure
        # check if code matches
        if _ == code: return True
        return False
    # weak check on freevars
    if not all(_f): return False  #XXX: VERY WEAK
    # weak check on varnames and globalvars
    _f = varnames(func)
    _f = [line.count(i) for i in _f[0]+_f[1]]
    if _f and not all(_f): return False  #XXX: VERY WEAK
    _f = [line.count(i) for i in globalvars(func).keys()]
    if _f and not all(_f): return False  #XXX: VERY WEAK
    # check if func is a double lambda
    if (line.count('lambda ') > 1) and (lhs in freevars(func).keys()):
        _lhs,_rhs = rhs.split('lambda ',1)[-1].split(":",1) #FIXME: if !1 inputs
        try: #FIXME: unsafe
            _f = eval("lambda %s : %s" % (_lhs,_rhs), globals(),locals())
        except: _f = dummy
        # get code objects, for comparison
        _, code = getcode(_f).co_code, getcode(func).co_code
        if len(_) != len(code): return False
        #NOTE: should be same code same order, but except for 't' and '\x88'
        _ = set((i,j) for (i,j) in zip(_,code) if i != j)
        if len(_) != 1: return False #('t','\x88')
        return True
    # check indentsize
    if not indentsize(line): return False #FIXME: is this a good check???
    # check if code 'pattern' matches
    #XXX: or pattern match against dis.dis(code)? (or use uncompyle2?)
    _ = _.split(_[0])  # 't' #XXX: remove matching values if starts the same?
    _f = code.split(code[0])  # '\x88'
    #NOTE: should be same code different order, with different first element
    _ = dict(re.match('([\W\D\S])(.*)', _[i]).groups() for i in range(1,len(_)))
    _f = dict(re.match('([\W\D\S])(.*)', _f[i]).groups() for i in range(1,len(_f)))
    if (_.keys() == _f.keys()) and (sorted(_.values()) == sorted(_f.values())):
        return True
    return False


def findsource(object):
    """Return the entire source file and starting line number for an object.
    For interactively-defined objects, the 'file' is the interpreter's history.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of all the lines
    in the file and the line number indexes a line in that list.  An IOError
    is raised if the source code cannot be retrieved, while a TypeError is
    raised for objects where the source code is unavailable (e.g. builtins)."""

    module = getmodule(object)
    try: file = getfile(module)
    except TypeError: file = None 
    # use readline when working in interpreter (i.e. __main__ and not file)
    if module and module.__name__ == '__main__' and not file:
        import readline
        lbuf = readline.get_current_history_length()
        lines = [readline.get_history_item(i)+'\n' for i in range(1,lbuf)]
    else:
        try: # special handling for class instances
            if not isclass(object) and isclass(type(object)): # __class__
                file = getfile(module)        
                sourcefile = getsourcefile(module)
            else: # builtins fail with a TypeError
                file = getfile(object)
                sourcefile = getsourcefile(object)
        except (TypeError, AttributeError): # fail with better error
            file = getfile(object)
            sourcefile = getsourcefile(object)
        if not sourcefile and file[:1] + file[-1:] != '<>':
            raise IOError('source code not available')
        file = sourcefile if sourcefile else file

        module = getmodule(object, file)
        if module:
            lines = linecache.getlines(file, module.__dict__)
        else:
            lines = linecache.getlines(file)

    if not lines:
        raise IOError('could not get source code')

    #FIXME: all below may fail if exec used (i.e. exec('f = lambda x:x') )
    if ismodule(object):
        return lines, 0

    name = pat1 = obj = ''
    pat2 = r'^(\s*@)'
#   pat1b = r'^(\s*%s\W*=)' % name #FIXME: finds 'f = decorate(f)', not exec
    if ismethod(object):
        name = object.__name__
        if name == '<lambda>': pat1 = r'(.*(?<!\w)lambda(:|\s))'
        else: pat1 = r'^(\s*def\s)'
        if PY3: object = object.__func__
        else: object = object.im_func
    if isfunction(object):
        name = object.__name__
        if name == '<lambda>':
            pat1 = r'(.*(?<!\w)lambda(:|\s))'
            obj = object #XXX: better a copy?
        else: pat1 = r'^(\s*def\s)'
        if PY3: object = object.__code__
        else: object = object.func_code
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        if not hasattr(object, 'co_firstlineno'):
            raise IOError('could not find function definition')
        stdin = object.co_filename == '<stdin>'
        if stdin:
            lnum = len(lines) - 1 # can't get lnum easily, so leverage pat
            if not pat1: pat1 = r'^(\s*def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)'
        else:
            lnum = object.co_firstlineno - 1
            pat1 = r'^(\s*def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)'
        pat1 = re.compile(pat1); pat2 = re.compile(pat2)
       #XXX: candidate_lnum = [n for n in range(lnum) if pat1.match(lines[n])]
        while lnum > 0: #XXX: won't find decorators in <stdin> ?
            line = lines[lnum]
            if pat1.match(line):
                if not stdin: break # co_firstlineno does the job
                if name == '<lambda>': # hackery needed to confirm a match
                    if _matchlambda(obj, line): break
                else: # not a lambda, just look for the name
                    if name in line: # need to check for decorator...
                        hats = 0
                        for _lnum in range(lnum-1,-1,-1):
                            if pat2.match(lines[_lnum]): hats += 1
                            else: break
                        lnum = lnum - hats
                        break
            lnum = lnum - 1
        return lines, lnum

    try: # turn instances into classes
        if not isclass(object) and isclass(type(object)): # __class__
            object = object.__class__ #XXX: sometimes type(class) is better?
            #XXX: we don't find how the instance was built
    except AttributeError: pass
    if isclass(object):
        name = object.__name__
        pat = re.compile(r'^(\s*)class\s*' + name + r'\b')
        # make some effort to find the best matching class definition:
        # use the one with the least indentation, which is the one
        # that's most probably not inside a function definition.
        candidates = []
        for i in range(len(lines)-1,-1,-1):
            match = pat.match(lines[i])
            if match:
                # if it's at toplevel, it's already the best one
                if lines[i][0] == 'c':
                    return lines, i
                # else add whitespace to candidate list
                candidates.append((match.group(1), i))
        if candidates:
            # this will sort by whitespace, and by line number,
            # less whitespace first  #XXX: should sort high lnum before low
            candidates.sort()
            return lines, candidates[0][1]
        else:
            raise IOError('could not find class definition')
    raise IOError('could not find code object')


def getblocks(object, lstrip=False, enclosing=False, locate=False):
    """Return a list of source lines and starting line number for an object.
    Interactively-defined objects refer to lines in the interpreter's history.

    If enclosing=True, then also return any enclosing code.
    If lstrip=True, ensure there is no indentation in the first line of code.
    If locate=True, then also return the line number for the block of code.

    DEPRECATED: use 'getsourcelines' instead
    """
    lines, lnum = findsource(object)

    if ismodule(object):
        if lstrip: lines = _outdent(lines)
        return ([lines], [0]) if locate is True else [lines]

    #XXX: 'enclosing' means: closures only? or classes and files?
    indent = indentsize(lines[lnum])
    block = getblock(lines[lnum:]) #XXX: catch any TokenError here?

    if not enclosing or not indent:
        if lstrip: block = _outdent(block)
        return ([block], [lnum]) if locate is True else [block]

    pat1 = r'^(\s*def\s)|(.*(?<!\w)lambda(:|\s))'; pat1 = re.compile(pat1)
    pat2 = r'^(\s*@)'; pat2 = re.compile(pat2)
   #pat3 = r'^(\s*class\s)'; pat3 = re.compile(pat3) #XXX: enclosing class?
    #FIXME: bound methods need enclosing class (and then instantiation)
    #       *or* somehow apply a partial using the instance

    skip = 0
    line = 0
    blocks = []; _lnum = []
    target = ''.join(block)
    while line <= lnum: #XXX: repeat lnum? or until line < lnum?
        # see if starts with ('def','lambda') and contains our target block
        if pat1.match(lines[line]):
            if not skip:
                try: code = getblock(lines[line:])
                except TokenError: code = [lines[line]]
            if indentsize(lines[line]) > indent: #XXX: should be >= ?
                line += len(code) - skip
            elif target in ''.join(code):
                blocks.append(code) # save code block as the potential winner
                _lnum.append(line - skip) # save the line number for the match
                line += len(code) - skip
            else:
                line += 1
            skip = 0
        # find skip: the number of consecutive decorators
        elif pat2.match(lines[line]):
            try: code = getblock(lines[line:])
            except TokenError: code = [lines[line]]
            skip = 1
            for _line in code[1:]: # skip lines that are decorators
                if not pat2.match(_line): break
                skip += 1
            line += skip
        # no match: reset skip and go to the next line
        else:
            line +=1
            skip = 0

    if not blocks:
        blocks = [block]
        _lnum = [lnum]
    if lstrip: blocks = [_outdent(block) for block in blocks]
    # return last match
    return (blocks, _lnum) if locate is True else blocks


def getsourcelines(object, lstrip=False, enclosing=False):
    """Return a list of source lines and starting line number for an object.
    Interactively-defined objects refer to lines in the interpreter's history.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of the lines
    corresponding to the object and the line number indicates where in the
    original source file the first line of code was found.  An IOError is
    raised if the source code cannot be retrieved, while a TypeError is
    raised for objects where the source code is unavailable (e.g. builtins).

    If lstrip=True, ensure there is no indentation in the first line of code.
    If enclosing=True, then also return any enclosing code."""
    code, n = getblocks(object, lstrip=lstrip, enclosing=enclosing, locate=True)
    return code[-1], n[-1]


#NOTE: broke backward compatibility 4/16/14 (was lstrip=True, force=True)
def getsource(object, alias='', lstrip=False, enclosing=False, \
                                              force=False, builtin=False):
    """Return the text of the source code for an object. The source code for
    interactively-defined objects are extracted from the interpreter's history.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a single string.  An
    IOError is raised if the source code cannot be retrieved, while a
    TypeError is raised for objects where the source code is unavailable
    (e.g. builtins).

    If alias is provided, then add a line of code that renames the object.
    If lstrip=True, ensure there is no indentation in the first line of code.
    If enclosing=True, then also return any enclosing code.
    If force=True, catch (TypeError,IOError) and try to use import hooks.
    If builtin=True, force an import for any builtins
    """
    # hascode denotes a callable
    hascode = _hascode(object)
    # is a class instance type (and not in builtins)
    instance = _isinstance(object)

    # get source lines; if fail, try to 'force' an import
    try: # fails for builtins, and other assorted object types
        lines, lnum = getsourcelines(object, enclosing=enclosing)
    except (TypeError, IOError): # failed to get source, resort to import hooks
        if not force: # don't try to get types that findsource can't get
            raise
        if not getmodule(object): # get things like 'None' and '1'
            if not instance: return getimport(object, alias, builtin=builtin)
            # special handling (numpy arrays, ...)
            _import = getimport(object, builtin=builtin)
            name = getname(object, force=True)
            _alias = "%s = " % alias if alias else ""
            if alias == name: _alias = ""
            return _import+_alias+"%s\n" % name
        else: #FIXME: could use a good bit of cleanup, since using getimport...
            if not instance: return getimport(object, alias, builtin=builtin)
            # now we are dealing with an instance...
            name = object.__class__.__name__
            module = object.__module__
            if module in ['builtins','__builtin__']:
                return getimport(object, alias, builtin=builtin)
            else: #FIXME: leverage getimport? use 'from module import name'?
                lines, lnum = ["%s = __import__('%s', fromlist=['%s']).%s\n" % (name,module,name,name)], 0
                obj = eval(lines[0].lstrip(name + ' = '))
                lines, lnum = getsourcelines(obj, enclosing=enclosing)

    # strip leading indent (helps ensure can be imported)
    if lstrip or alias:
        lines = _outdent(lines)

    # instantiate, if there's a nice repr  #XXX: BAD IDEA???
    if instance: #and force: #XXX: move into findsource or getsourcelines ?
        if '(' in repr(object): lines.append('%r\n' % object)
       #else: #XXX: better to somehow to leverage __reduce__ ?
       #    reconstructor,args = object.__reduce__()
       #    _ = reconstructor(*args)
        else: # fall back to serialization #XXX: bad idea?
            #XXX: better not duplicate work? #XXX: better new/enclose=True?
            lines = dumpsource(object, alias='', new=force, enclose=False)
            lines, lnum = [line+'\n' for line in lines.split('\n')][:-1], 0
       #else: object.__code__ # raise AttributeError

    # add an alias to the source code
    if alias:
        if hascode:
            skip = 0
            for line in lines: # skip lines that are decorators
                if not line.startswith('@'): break
                skip += 1
            #XXX: use regex from findsource / getsourcelines ?
            if lines[skip].lstrip().startswith('def '): # we have a function
                if alias != object.__name__:
                    lines.append('\n%s = %s\n' % (alias, object.__name__))
            elif 'lambda ' in lines[skip]: # we have a lambda
                if alias != lines[skip].split('=')[0].strip():
                    lines[skip] = '%s = %s' % (alias, lines[skip])
            else: # ...try to use the object's name
                if alias != object.__name__:
                    lines.append('\n%s = %s\n' % (alias, object.__name__))
        else: # class or class instance
            if instance:
                if alias != lines[-1].split('=')[0].strip():
                    lines[-1] = ('%s = ' % alias) + lines[-1]
            else:
                name = getname(object, force=True) or object.__name__
                if alias != name:
                    lines.append('\n%s = %s\n' % (alias, name))
    return ''.join(lines)


def _hascode(object):
    '''True if object has an attribute that stores it's __code__'''
    return getattr(object,'__code__',None) or getattr(object,'func_code',None)

def _isinstance(object):
    '''True if object is a class instance type (and is not a builtin)'''
    if _hascode(object) or isclass(object) or ismodule(object):
        return False
    if istraceback(object) or isframe(object) or iscode(object):
        return False
    # special handling (numpy arrays, ...)
    if not getmodule(object) and getmodule(type(object)).__name__ in ['numpy']:
        return True
    _types = ('<class ',"<type 'instance'>")
    if not repr(type(object)).startswith(_types): #FIXME: weak hack
        return False
    if not getmodule(object) or object.__module__ in ['builtins','__builtin__'] or getname(object, force=True) in ['array']:
        return False
    return True # by process of elimination... it's what we want


def _intypes(object):
    '''check if object is in the 'types' module'''
    import types
    # allow user to pass in object or object.__name__
    if type(object) is not type(''):
        object = getname(object, force=True)
    if object == 'ellipsis': object = 'EllipsisType'
    return True if hasattr(types, object) else False


def _isstring(object): #XXX: isstringlike better?
    '''check if object is a string-like type'''
    if PY3: return isinstance(object, (str, bytes))
    return isinstance(object, basestring)


def indent(code, spaces=4):
    '''indent a block of code with whitespace (default is 4 spaces)'''
    indent = indentsize(code) 
    if type(spaces) is int: spaces = ' '*spaces
    # if '\t' is provided, will indent with a tab
    nspaces = indentsize(spaces)
    # blank lines (etc) need to be ignored
    lines = code.split('\n')
##  stq = "'''"; dtq = '"""'
##  in_stq = in_dtq = False
    for i in range(len(lines)):
        #FIXME: works... but shouldn't indent 2nd+ lines of multiline doc
        _indent = indentsize(lines[i])
        if indent > _indent: continue
        lines[i] = spaces+lines[i]
##      #FIXME: may fail when stq and dtq in same line (depends on ordering)
##      nstq, ndtq = lines[i].count(stq), lines[i].count(dtq)
##      if not in_dtq and not in_stq:
##          lines[i] = spaces+lines[i] # we indent
##          # entering a comment block
##          if nstq%2: in_stq = not in_stq
##          if ndtq%2: in_dtq = not in_dtq
##      # leaving a comment block
##      elif in_dtq and ndtq%2: in_dtq = not in_dtq
##      elif in_stq and nstq%2: in_stq = not in_stq
##      else: pass
    if lines[-1].strip() == '': lines[-1] = ''
    return '\n'.join(lines)


def _outdent(lines, spaces=None, all=True):
    '''outdent lines of code, accounting for docs and line continuations'''
    indent = indentsize(lines[0]) 
    if spaces is None or spaces > indent or spaces < 0: spaces = indent
    for i in range(len(lines) if all else 1):
        #FIXME: works... but shouldn't outdent 2nd+ lines of multiline doc
        _indent = indentsize(lines[i])
        if spaces > _indent: _spaces = _indent
        else: _spaces = spaces
        lines[i] = lines[i][_spaces:]
    return lines

def outdent(code, spaces=None, all=True):
    '''outdent a block of code (default is to strip all leading whitespace)'''
    indent = indentsize(code) 
    if spaces is None or spaces > indent or spaces < 0: spaces = indent
    #XXX: will this delete '\n' in some cases?
    if not all: return code[spaces:]
    return '\n'.join(_outdent(code.split('\n'), spaces=spaces, all=all))


#XXX: not sure what the point of _wrap is...
#exec_ = lambda s, *a: eval(compile(s, '<string>', 'exec'), *a)
__globals__ = globals()
__locals__ = locals()
wrap2 = '''
def _wrap(f):
    """ encapsulate a function and it's __import__ """
    def func(*args, **kwds):
        try:
            #_ = eval(getsource(f, force=True)) #FIXME: safer, but not as robust
            exec getimportable(f, alias='_') in %s, %s
        except:
            raise ImportError('cannot import name ' + f.__name__)
        return _(*args, **kwds)
    func.__name__ = f.__name__
    func.__doc__ = f.__doc__
    return func
''' % ('__globals__', '__locals__')
wrap3 = '''
def _wrap(f):
    """ encapsulate a function and it's __import__ """
    def func(*args, **kwds):
        try:
            #_ = eval(getsource(f, force=True)) #FIXME: safer, but not as robust
            exec(getimportable(f, alias='_'), %s, %s)
        except:
            raise ImportError('cannot import name ' + f.__name__)
        return _(*args, **kwds)
    func.__name__ = f.__name__
    func.__doc__ = f.__doc__
    return func
''' % ('__globals__', '__locals__')
if PY3:
    exec(wrap3)
else:
    exec(wrap2)
del wrap2, wrap3


def _enclose(object, alias=''): #FIXME: needs alias to hold returned object
    """create a function enclosure around the source of some object"""
    #XXX: dummy and stub should append a random string
    dummy = '__this_is_a_big_dummy_enclosing_function__'
    stub = '__this_is_a_stub_variable__'
    code = 'def %s():\n' % dummy
    code += indent(getsource(object, alias=stub, lstrip=True, force=True))
    code += indent('return %s\n' % stub)
    if alias: code += '%s = ' % alias
    code += '%s(); del %s\n' % (dummy, dummy)
   #code += "globals().pop('%s',lambda :None)()\n" % dummy
    return code


def dumpsource(object, alias='', new=False, enclose=True):
    """'dump to source', where the code includes a pickled object.

    If new=True and object is a class instance, then create a new
    instance using the unpacked class source code. If enclose, then
    create the object inside a function enclosure (thus minimizing
    any global namespace pollution).
    """
    from dill import dumps
    pik = repr(dumps(object))
    code = 'import dill\n'
    if enclose:
        stub = '__this_is_a_stub_variable__' #XXX: *must* be same _enclose.stub
        pre = '%s = ' % stub
        new = False #FIXME: new=True doesn't work with enclose=True
    else:
        stub = alias
        pre = '%s = ' % stub if alias else alias
    
    # if a 'new' instance is not needed, then just dump and load
    if not new or not _isinstance(object):
        code += pre + 'dill.loads(%s)\n' % pik
    else: #XXX: other cases where source code is needed???
        code += getsource(object.__class__, alias='', lstrip=True, force=True)
        mod = repr(object.__module__) # should have a module (no builtins here)
        if PY3:
            code += pre + 'dill.loads(%s.replace(b%s,bytes(__name__,"UTF-8")))\n' % (pik,mod)
        else:
            code += pre + 'dill.loads(%s.replace(%s,__name__))\n' % (pik,mod)
       #code += 'del %s' % object.__class__.__name__ #NOTE: kills any existing!

    if enclose:
        # generation of the 'enclosure'
        dummy = '__this_is_a_big_dummy_object__'
        dummy = _enclose(dummy, alias=alias)
        # hack to replace the 'dummy' with the 'real' code
        dummy = dummy.split('\n')
        code = dummy[0]+'\n' + indent(code) + '\n'.join(dummy[-3:])

    return code #XXX: better 'dumpsourcelines', returning list of lines?


def getname(obj, force=False): #XXX: allow 'throw'(?) to raise error on fail?
    """get the name of the object. for lambdas, get the name of the pointer """
    module = getmodule(obj)
    if not module: # things like "None" and "1"
        if not force: return None
        return repr(obj)
    try:
        #XXX: 'wrong' for decorators and curried functions ?
        #       if obj.func_closure: ...use logic from getimportable, etc ?
        name = obj.__name__
        if name == '<lambda>':
            return getsource(obj).split('=',1)[0].strip()
        # handle some special cases
        if module.__name__ in ['builtins','__builtin__']:
            if name == 'ellipsis': name = 'EllipsisType'
        return name
    except AttributeError: #XXX: better to just throw AttributeError ?
        if not force: return None
        name = repr(obj)
        if name.startswith('<'): # or name.split('('):
            return None
        return name


def _namespace(obj):
    """_namespace(obj); return namespace hierarchy (as a list of names)
    for the given object.  For an instance, find the class hierarchy.

    For example:

    >>> from functools import partial
    >>> p = partial(int, base=2)
    >>> _namespace(p)
    [\'functools\', \'partial\']
    """
    # mostly for functions and modules and such
    #FIXME: 'wrong' for decorators and curried functions
    try: #XXX: needs some work and testing on different types
        module = qual = str(getmodule(obj)).split()[1].strip('"').strip("'")
        qual = qual.split('.')
        if ismodule(obj):
            return qual
        # get name of a lambda, function, etc
        name = getname(obj) or obj.__name__ # failing, raise AttributeError
        # check special cases (NoneType, ...)
        if module in ['builtins','__builtin__']: # BuiltinFunctionType
            if _intypes(name): return ['types'] + [name]
        return qual + [name] #XXX: can be wrong for some aliased objects
    except: pass
    # special case: numpy.inf and numpy.nan (we don't want them as floats)
    if str(obj) in ['inf','nan','Inf','NaN']: # is more, but are they needed?
        return ['numpy'] + [str(obj)]
    # mostly for classes and class instances and such
    module = getattr(obj.__class__, '__module__', None)
    qual = str(obj.__class__)
    try: qual = qual[qual.index("'")+1:-2]
    except ValueError: pass # str(obj.__class__) made the 'try' unnecessary
    qual = qual.split(".")
    if module in ['builtins','__builtin__']:
        # check special cases (NoneType, Ellipsis, ...)
        if qual[-1] == 'ellipsis': qual[-1] = 'EllipsisType'
        if _intypes(qual[-1]): module = 'types' #XXX: BuiltinFunctionType
        qual = [module] + qual
    return qual


#NOTE: 05/25/14 broke backward compatability: added 'alias' as 3rd argument
def _getimport(head, tail, alias='', verify=True, builtin=False):
    """helper to build a likely import string from head and tail of namespace.
    ('head','tail') are used in the following context: "from head import tail"

    If verify=True, then test the import string before returning it.
    If builtin=True, then force an import for builtins where possible.
    If alias is provided, then rename the object on import.
    """
    # special handling for a few common types
    if tail in ['Ellipsis', 'NotImplemented'] and head in ['types']:
        head = len.__module__
    elif tail in ['None'] and head in ['types']:
        _alias = '%s = ' % alias if alias else ''
        if alias == tail: _alias = ''
        return _alias+'%s\n' % tail
    # we don't need to import from builtins, so return ''
#   elif tail in ['NoneType','int','float','long','complex']: return '' #XXX: ?
    if head in ['builtins','__builtin__']:
        # special cases (NoneType, Ellipsis, ...) #XXX: BuiltinFunctionType
        if tail == 'ellipsis': tail = 'EllipsisType'
        if _intypes(tail): head = 'types'
        elif not builtin:
            _alias = '%s = ' % alias if alias else ''
            if alias == tail: _alias = ''
            return _alias+'%s\n' % tail
        else: pass # handle builtins below
    # get likely import string
    if not head: _str = "import %s" % tail
    else: _str = "from %s import %s" % (head, tail)
    _alias = " as %s\n" % alias if alias else "\n"
    if alias == tail: _alias = "\n"
    _str += _alias
    # FIXME: fails on most decorators, currying, and such...
    #        (could look for magic __wrapped__ or __func__ attr)
    #        (could fix in 'namespace' to check obj for closure)
    if verify and not head.startswith('dill.'):# weird behavior for dill
       #print(_str)
        try: exec(_str) #XXX: check if == obj? (name collision)
        except ImportError: #XXX: better top-down or bottom-up recursion?
            _head = head.rsplit(".",1)[0] #(or get all, then compare == obj?)
            if not _head: raise
            if _head != head:
                _str = _getimport(_head, tail, alias, verify)
    return _str


#XXX: rename builtin to force? vice versa? verify to force? (as in getsource)
#NOTE: 05/25/14 broke backward compatability: added 'alias' as 2nd argument
def getimport(obj, alias='', verify=True, builtin=False, enclosing=False):
    """get the likely import string for the given object

    obj is the object to inspect
    If verify=True, then test the import string before returning it.
    If builtin=True, then force an import for builtins where possible.
    If enclosing=True, get the import for the outermost enclosing callable.
    If alias is provided, then rename the object on import.
    """
    if enclosing:
        from dill.detect import outermost
        _obj = outermost(obj)
        obj = _obj if _obj else obj
    # for named things... with a nice repr #XXX: move into _namespace?
    try: # look for '<...>' and be mindful it might be in lists, dicts, etc...
        name = repr(obj).split('<',1)[1].split('>',1)[1]
        name = None # we have a 'object'-style repr
    except: # it's probably something 'importable'
        name = repr(obj).split('(')[0]
   #if not repr(obj).startswith('<'): name = repr(obj).split('(')[0]
   #else: name = None
    # get the namespace
    qual = _namespace(obj)
    head = '.'.join(qual[:-1])
    tail = qual[-1]
    if name: # try using name instead of tail
        try: return _getimport(head, name, alias, verify, builtin)
        except ImportError: pass
        except SyntaxError:
            if head in ['builtins','__builtin__']:
                _alias = '%s = ' % alias if alias else ''
                if alias == name: _alias = ''
                return _alias+'%s\n' % name
            else: pass
    try:
       #if type(obj) is type(abs): _builtin = builtin # BuiltinFunctionType
       #else: _builtin = False
        return _getimport(head, tail, alias, verify, builtin)
    except ImportError:
        raise # could do some checking against obj
    except SyntaxError:
        if head in ['builtins','__builtin__']:
            _alias = '%s = ' % alias if alias else ''
            if alias == tail: _alias = ''
            return _alias+'%s\n' % tail
        raise # could do some checking against obj


def _importable(obj, alias='', source=True, enclosing=False, force=True, \
                                              builtin=True, lstrip=True):
    """get an import string (or the source code) for the given object

    For simple objects, this function will discover the name of the object, or
    the repr of the object, or the source code for the object. To attempt to force
    discovery of the source code, use source=True, otherwise an import will be
    sought. The intent is to build a string that can be imported from a python
    file. obj is the object to inspect. If alias is provided, then rename the
    object with the given alias.

    If source=True, use these options:
      If enclosing=True, then also return any enclosing code.
      If force=True, catch (TypeError,IOError) and try to use import hooks.
      If lstrip=True, ensure there is no indentation in the first line of code.

    If source=False, use these options:
      If enclosing=True, get the import for the outermost enclosing callable.
      If force=True, then don't test the import string before returning it.
      If builtin=True, then force an import for builtins where possible.
    """
    if source: # first try to get the source
        try:
            return getsource(obj, alias, enclosing=enclosing, \
                             force=force, lstrip=lstrip, builtin=builtin)
        except: pass
    try:
        if not _isinstance(obj):
            return getimport(obj, alias, enclosing=enclosing, \
                                  verify=(not force), builtin=builtin)
        # first 'get the import', then 'get the instance'
        _import = getimport(obj, enclosing=enclosing, \
                                 verify=(not force), builtin=builtin)
        name = getname(obj, force=True)
        if not name:
            raise AttributeError("object has no atribute '__name__'")
        _alias = "%s = " % alias if alias else ""
        if alias == name: _alias = ""
        return _import+_alias+"%s\n" % name

    except: pass
    if not source: # try getsource, only if it hasn't been tried yet
        try:
            return getsource(obj, alias, enclosing=enclosing, \
                             force=force, lstrip=lstrip, builtin=builtin)
        except: pass
    # get the name (of functions, lambdas, and classes)
    # or hope that obj can be built from the __repr__
    #XXX: what to do about class instances and such?
    obj = getname(obj, force=force)
    # we either have __repr__ or __name__ (or None)
    if not obj or obj.startswith('<'):
        raise AttributeError("object has no atribute '__name__'")
    _alias = '%s = ' % alias if alias else ''
    if alias == obj: _alias = ''
    return _alias+'%s\n' % obj
    #XXX: possible failsafe... (for example, for instances when source=False)
    #     "import dill; result = dill.loads(<pickled_object>); # repr(<object>)"

def _closuredimport(func, alias='', builtin=False):
    """get import for closured objects; return a dict of 'name' and 'import'"""
    import re
    from dill.detect import freevars, outermost
    free_vars = freevars(func)
    func_vars = {}
    # split into 'funcs' and 'non-funcs'
    for name,obj in list(free_vars.items()):
        if not isfunction(obj): continue
        # get import for 'funcs'
        fobj = free_vars.pop(name)
        src = getsource(fobj)
        if src.lstrip().startswith('@'): # we have a decorator
            src = getimport(fobj, alias=alias, builtin=builtin)
        else: # we have to "hack" a bit... and maybe be lucky
            encl = outermost(func)
            # pattern: 'func = enclosing(fobj'
            pat = '.*[\w\s]=\s*'+getname(encl)+'\('+getname(fobj)
            mod = getname(getmodule(encl))
            #HACK: get file containing 'outer' function; is func there?
            lines,_ = findsource(encl)
            candidate = [line for line in lines if getname(encl) in line and \
                         re.match(pat, line)]
            if not candidate:
                mod = getname(getmodule(fobj))
                #HACK: get file containing 'inner' function; is func there? 
                lines,_ = findsource(fobj)
                candidate = [line for line in lines \
                             if getname(fobj) in line and re.match(pat, line)]
            if not len(candidate): raise TypeError('import could not be found')
            candidate = candidate[-1]
            name = candidate.split('=',1)[0].split()[-1].strip()
            src = _getimport(mod, name, alias=alias, builtin=builtin)
        func_vars[name] = src
    if not func_vars:
        name = outermost(func)
        mod = getname(getmodule(name))
        if not mod or name is func: # then it can be handled by getimport
            name = getname(func, force=True) #XXX: better key?
            src = getimport(func, alias=alias, builtin=builtin)
        else:
            lines,_ = findsource(name)
            # pattern: 'func = enclosing('
            candidate = [line for line in lines if getname(name) in line and \
                         re.match('.*[\w\s]=\s*'+getname(name)+'\(', line)]
            if not len(candidate): raise TypeError('import could not be found')
            candidate = candidate[-1]
            name = candidate.split('=',1)[0].split()[-1].strip()
            src = _getimport(mod, name, alias=alias, builtin=builtin)
        func_vars[name] = src
    return func_vars

#XXX: should be able to use __qualname__
def _closuredsource(func, alias=''):
    """get source code for closured objects; return a dict of 'name'
    and 'code blocks'"""
    from dill.detect import freevars
    free_vars = freevars(func)
    func_vars = {}
    # split into 'funcs' and 'non-funcs'
    for name,obj in list(free_vars.items()):
        if not isfunction(obj):
            # get source for 'non-funcs'
            free_vars[name] = getsource(obj, force=True, alias=name)
            continue
        # get source for 'funcs'
        fobj = free_vars.pop(name)
        src = getsource(fobj, alias)
        # if source doesn't start with '@', use name as the alias
        if not src.lstrip().startswith('@'): #FIXME: 'enclose' in dummy;
            src = getsource(fobj, alias=name)#        wrong ref 'name'
            org = getsource(func, alias, enclosing=False, lstrip=True)
            src = (src, org) # undecorated first, then target
        else: #NOTE: reproduces the code!
            org = getsource(func, enclosing=True, lstrip=False)
            src = (org, src) # target first, then decorated
        func_vars[name] = src
    if not func_vars: #FIXME: 'enclose' in dummy; wrong ref 'name'
        src = ''.join(free_vars.values())
        org = getsource(func, alias, force=True, enclosing=False, lstrip=True)
        src = (src, org) # variables first, then target
        func_vars[None] = src
    return func_vars

def importable(obj, alias='', source=True, builtin=True):
    """get an importable string (i.e. source code or the import string)
    for the given object, including any required objects from the enclosing
    and global scope

    This function will attempt to discover the name of the object, or the repr
    of the object, or the source code for the object. To attempt to force
    discovery of the source code, use source=True, otherwise an import will be
    sought. The intent is to build a string that can be imported from a python
    file. obj is the object to inspect. If alias is provided, then rename the
    object with the given alias. If builtin=True, then force an import for
    builtins where possible.
    """
    #NOTE: we always 'force', and 'lstrip' as necessary
    #NOTE: for 'enclosing', use importable(outermost(obj))
    if builtin and isbuiltin(obj): source = False
    tried_source = tried_import = False
    while True:
        if not source: # we want an import
            try:
                if _isinstance(obj): # for instances, punt to _importable
                    return _importable(obj, alias, source=False, builtin=builtin)
                src = _closuredimport(obj, alias=alias, builtin=builtin)
                if len(src) == 0:
                    raise NotImplementedError('not implemented')
                if len(src) > 1:
                    raise NotImplementedError('not implemented')
                return list(src.values())[0]
            except:
                if tried_source: raise
                tried_import = True
        # we want the source
        try:
            src = _closuredsource(obj, alias=alias)
            if len(src) == 0:
                raise NotImplementedError('not implemented')
            if len(src) > 1:
                raise NotImplementedError('not implemented')
            src = list(src.values())[0]
            if src[0] and src[-1]: src = '\n'.join(src)
            elif src[0]: src = src[0]
            elif src[-1]: src = src[-1]
            else: src = ''
            # get source code of objects referred to by obj in global scope
            from dill.detect import globalvars
            obj = globalvars(obj) #XXX: don't worry about alias?
            obj = list(getsource(_obj,name,force=True) for (name,_obj) in obj.items())
            obj = '\n'.join(obj) if obj else ''
            # combine all referred-to source (global then enclosing)
            if not obj: return src
            if not src: return obj
            return obj + src
        except:
            if tried_import: raise
            tried_source = True
            source = not source
    # should never get here
    return


# backward compatability
def getimportable(obj, alias='', byname=True, explicit=False):
    return importable(obj,alias,source=(not byname),builtin=explicit)
   #return outdent(_importable(obj,alias,source=(not byname),builtin=explicit))
def likely_import(obj, passive=False, explicit=False):
    return getimport(obj, verify=(not passive), builtin=explicit)
def _likely_import(first, last, passive=False, explicit=True):
    return _getimport(first, last, verify=(not passive), builtin=explicit)
_get_name = getname
getblocks_from_history = getblocks



# EOF

########NEW FILE########
__FILENAME__ = temp
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
Methods for serialized objects (or source code) stored in temporary files
and file-like objects.
"""
#XXX: better instead to have functions write to any given file-like object ?
#XXX: currently, all file-like objects are created by the function...

from __future__ import absolute_import
__all__ = ['dump_source', 'dump', 'dumpIO_source', 'dumpIO',\
           'load_source', 'load', 'loadIO_source', 'loadIO']

from .dill import PY3

def b(x): # deal with b'foo' versus 'foo'
    import codecs
    return codecs.latin_1_encode(x)[0]

def load_source(file, **kwds):
    """load an object that was stored with dill.temp.dump_source

    file: filehandle
    alias: string name of stored object
    mode: mode to open the file, one of: {'r', 'rb'}

    >>> f = lambda x: x**2
    >>> pyfile = dill.temp.dump_source(f, alias='_f')
    >>> _f = dill.temp.load_source(pyfile)
    >>> _f(4)
    16
    """
    alias = kwds.pop('alias', None)
    mode = kwds.pop('mode', 'r')
    fname = getattr(file, 'name', file) # fname=file.name or fname=file (if str)
    source = open(fname, mode=mode, **kwds).read()
    if not alias:
        tag = source.strip().splitlines()[-1].split()
        if tag[0] != '#NAME:':
            stub = source.splitlines()[0]
            raise IOError("unknown name for code: %s" % stub)
        alias = tag[-1]
    local = {}
    exec(source, local)
    _ = eval("%s" % alias, local)
    return _

def dump_source(object, **kwds):
    """write object source to a NamedTemporaryFile (instead of dill.dump)
Loads with "import" or "dill.temp.load_source".  Returns the filehandle.

    >>> f = lambda x: x**2
    >>> pyfile = dill.temp.dump_source(f, alias='_f')
    >>> _f = dill.temp.load_source(pyfile)
    >>> _f(4)
    16

    >>> f = lambda x: x**2
    >>> pyfile = dill.temp.dump_source(f, dir='.')
    >>> modulename = os.path.basename(pyfile.name).split('.py')[0]
    >>> exec('from %s import f as _f' % modulename)
    >>> _f(4)
    16

Optional kwds:
    If 'alias' is specified, the object will be renamed to the given string.

    If 'prefix' is specified, the file name will begin with that prefix,
    otherwise a default prefix is used.
    
    If 'dir' is specified, the file will be created in that directory,
    otherwise a default directory is used.
    
    If 'text' is specified and true, the file is opened in text
    mode.  Else (the default) the file is opened in binary mode.  On
    some operating systems, this makes no difference.

NOTE: Keep the return value for as long as you want your file to exist !
    """ #XXX: write a "load_source"?
    from .source import getsource, getname
    import tempfile
    kwds.pop('suffix', '') # this is *always* '.py'
    alias = kwds.pop('alias', '') #XXX: include an alias so a name is known
    name = str(alias) or getname(object)
    name = "\n#NAME: %s\n" % name
    #XXX: assumes kwds['dir'] is writable and on $PYTHONPATH
    file = tempfile.NamedTemporaryFile(suffix='.py', **kwds)
    file.write(b(''.join([getsource(object, alias=alias),name])))
    file.flush()
    return file

def load(file, **kwds):
    """load an object that was stored with dill.temp.dump

    file: filehandle
    mode: mode to open the file, one of: {'r', 'rb'}

    >>> dumpfile = dill.temp.dump([1, 2, 3, 4, 5])
    >>> dill.temp.load(dumpfile)
    [1, 2, 3, 4, 5]
    """
    import dill as pickle
    mode = kwds.pop('mode', 'rb')
    name = getattr(file, 'name', file) # name=file.name or name=file (if str)
    return pickle.load(open(name, mode=mode, **kwds))

def dump(object, **kwds):
    """dill.dump of object to a NamedTemporaryFile.
Loads with "dill.temp.load".  Returns the filehandle.

    >>> dumpfile = dill.temp.dump([1, 2, 3, 4, 5])
    >>> dill.temp.load(dumpfile)
    [1, 2, 3, 4, 5]

Optional kwds:
    If 'suffix' is specified, the file name will end with that suffix,
    otherwise there will be no suffix.
    
    If 'prefix' is specified, the file name will begin with that prefix,
    otherwise a default prefix is used.
    
    If 'dir' is specified, the file will be created in that directory,
    otherwise a default directory is used.
    
    If 'text' is specified and true, the file is opened in text
    mode.  Else (the default) the file is opened in binary mode.  On
    some operating systems, this makes no difference.

NOTE: Keep the return value for as long as you want your file to exist !
    """
    import dill as pickle
    import tempfile
    file = tempfile.NamedTemporaryFile(**kwds)
    pickle.dump(object, file)
    file.flush()
    return file

def loadIO(buffer, **kwds):
    """load an object that was stored with dill.temp.dumpIO

    buffer: buffer object

    >>> dumpfile = dill.temp.dumpIO([1, 2, 3, 4, 5])
    >>> dill.temp.loadIO(dumpfile)
    [1, 2, 3, 4, 5]
    """
    import dill as pickle
    if PY3:
        from io import BytesIO as StringIO
    else:
        from StringIO import StringIO
    value = getattr(buffer, 'getvalue', buffer) # value or buffer.getvalue
    if value != buffer: value = value() # buffer.getvalue()
    return pickle.load(StringIO(value))

def dumpIO(object, **kwds):
    """dill.dump of object to a buffer.
Loads with "dill.temp.loadIO".  Returns the buffer object.

    >>> dumpfile = dill.temp.dumpIO([1, 2, 3, 4, 5])
    >>> dill.temp.loadIO(dumpfile)
    [1, 2, 3, 4, 5]
    """
    import dill as pickle
    if PY3:
        from io import BytesIO as StringIO
    else:
        from StringIO import StringIO
    file = StringIO()
    pickle.dump(object, file)
    file.flush()
    return file

def loadIO_source(buffer, **kwds):
    """load an object that was stored with dill.temp.dumpIO_source

    buffer: buffer object
    alias: string name of stored object

    >>> f = lambda x:x**2
    >>> pyfile = dill.temp.dumpIO_source(f, alias='_f')
    >>> _f = dill.temp.loadIO_source(pyfile)
    >>> _f(4)
    16
    """
    alias = kwds.pop('alias', None)
    source = getattr(buffer, 'getvalue', buffer) # source or buffer.getvalue
    if source != buffer: source = source() # buffer.getvalue()
    if PY3: source = source.decode() # buffer to string
    if not alias:
        tag = source.strip().splitlines()[-1].split()
        if tag[0] != '#NAME:':
            stub = source.splitlines()[0]
            raise IOError("unknown name for code: %s" % stub)
        alias = tag[-1]
    local = {}
    exec(source, local)
    _ = eval("%s" % alias, local)
    return _

def dumpIO_source(object, **kwds):
    """write object source to a buffer (instead of dill.dump)
Loads by with dill.temp.loadIO_source.  Returns the buffer object.

    >>> f = lambda x:x**2
    >>> pyfile = dill.temp.dumpIO_source(f, alias='_f')
    >>> _f = dill.temp.loadIO_source(pyfile)
    >>> _f(4)
    16

Optional kwds:
    If 'alias' is specified, the object will be renamed to the given string.
    """
    from .source import getsource, getname
    if PY3:
        from io import BytesIO as StringIO
    else:
        from StringIO import StringIO
    alias = kwds.pop('alias', '') #XXX: include an alias so a name is known
    name = str(alias) or getname(object)
    name = "\n#NAME: %s\n" % name
    #XXX: assumes kwds['dir'] is writable and on $PYTHONPATH
    file = StringIO()
    file.write(b(''.join([getsource(object, alias=alias),name])))
    file.flush()
    return file


del absolute_import


# EOF

########NEW FILE########
__FILENAME__ = _objects
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
all Python Standard Library objects (currently: CH 1-15 @ 2.7)
and some other common objects (i.e. numpy.ndarray)
"""

__all__ = ['registered','failures','succeeds']

# helper imports
import warnings; warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys
PY3 = (hex(sys.hexversion) >= '0x30000f0')
if PY3:
    import queue as Queue
    import dbm as anydbm
else:
    import Queue
    import anydbm
    import sets # deprecated/removed
    import mutex # removed
try:
    from cStringIO import StringIO # has StringI and StringO types
except ImportError: # only has StringIO type
    if PY3:
        from io import BytesIO as StringIO
    else:
        from StringIO import StringIO
import re
import array
import collections
import codecs
import struct
import datetime
import calendar
import weakref
import pprint
import decimal
import functools
import itertools
import operator
import tempfile
import shelve
import zlib
import gzip
import zipfile
import tarfile
import xdrlib
import csv
import hashlib
import hmac
import os
import logging
import optparse
import curses
#import __hello__
import threading
import socket
import contextlib
try:
    import bz2
    import sqlite3
    if PY3: import dbm.ndbm as dbm
    else: import dbm
    HAS_ALL = True
except ImportError: # Ubuntu
    HAS_ALL = False
try:
    import ctypes
    HAS_CTYPES = True
except ImportError: # MacPorts
    HAS_CTYPES = False
from curses import textpad, panel

# helper objects
class _class:
    def _method(self):
        pass
#   @classmethod
#   def _clsmethod(cls): #XXX: test me
#       pass
#   @staticmethod
#   def _static(self): #XXX: test me
#       pass
class _class2:
    def __call__(self):
        pass
_instance2 = _class2()
class _newclass(object):
    def _method(self):
        pass
#   @classmethod
#   def _clsmethod(cls): #XXX: test me
#       pass
#   @staticmethod
#   def _static(self): #XXX: test me
#       pass
def _function(x): yield x
def _function2():
    try: raise
    except:
        from sys import exc_info
        e, er, tb = exc_info()
        return er, tb
if HAS_CTYPES:
    class _Struct(ctypes.Structure):
        pass
    _Struct._fields_ = [("_field", ctypes.c_int),("next", ctypes.POINTER(_Struct))]
_filedescrip, _tempfile = tempfile.mkstemp('r') # deleted in cleanup
_tmpf = tempfile.TemporaryFile('w')

# put the objects in order, if possible
try:
    from collections import OrderedDict as odict
except ImportError:
    try:
        from ordereddict import OrderedDict as odict
    except ImportError:
        odict = dict
# objects used by dill for type declaration
registered = d = odict()
# objects dill fails to pickle
failures = x = odict()
# all other type objects
succeeds = a = odict()

# types module (part of CH 8)
a['BooleanType'] = bool(1)
a['BuiltinFunctionType'] = len
a['BuiltinMethodType'] = a['BuiltinFunctionType']
a['BytesType'] = _bytes = codecs.latin_1_encode('\x00')[0] # bytes(1)
a['ClassType'] = _class
a['ComplexType'] = complex(1)
a['DictType'] = _dict = {}
a['DictionaryType'] = a['DictType']
a['FloatType'] = float(1)
a['FunctionType'] = _function
a['InstanceType'] = _instance = _class()
a['IntType'] = _int = int(1)
a['ListType'] = _list = []
a['NoneType'] = None
a['ObjectType'] = object()
a['StringType'] = _str = str(1)
a['TupleType'] = _tuple = ()
a['TypeType'] = type
if PY3:
    a['LongType'] = _int
    a['UnicodeType'] = _str
else:
    a['LongType'] = long(1)
    a['UnicodeType'] = unicode(1)
# built-in constants (CH 4)
a['CopyrightType'] = copyright
# built-in types (CH 5)
a['ClassObjectType'] = _newclass # <type 'type'>
a['ClassInstanceType'] = _newclass() # <type 'class'>
a['SetType'] = _set = set()
a['FrozenSetType'] = frozenset()
# built-in exceptions (CH 6)
a['ExceptionType'] = _exception = _function2()[0]
# string services (CH 7)
a['SREPatternType'] = _srepattern = re.compile('')
# data types (CH 8)
a['ArrayType'] = array.array("f")
a['DequeType'] = collections.deque([0])
a['DefaultDictType'] = collections.defaultdict(_function, _dict)
a['TZInfoType'] = datetime.tzinfo()
a['DateTimeType'] = datetime.datetime.today()
a['CalendarType'] = calendar.Calendar()
if not PY3:
    a['SetsType'] = sets.Set()
    a['ImmutableSetType'] = sets.ImmutableSet()
    a['MutexType'] = mutex.mutex()
# numeric and mathematical types (CH 9)
a['DecimalType'] = decimal.Decimal(1)
a['CountType'] = itertools.count(0)
# data compression and archiving (CH 12)
a['TarInfoType'] = tarfile.TarInfo()
# generic operating system services (CH 15)
a['LoggerType'] = logging.getLogger()
a['FormatterType'] = logging.Formatter() # pickle ok
a['FilterType'] = logging.Filter() # pickle ok
a['LogRecordType'] = logging.makeLogRecord(_dict) # pickle ok
a['OptionParserType'] = _oparser = optparse.OptionParser() # pickle ok
a['OptionGroupType'] = optparse.OptionGroup(_oparser,"foo") # pickle ok
a['OptionType'] = optparse.Option('--foo') # pickle ok
if HAS_CTYPES:
    a['CCharType'] = _cchar = ctypes.c_char()
    a['CWCharType'] = ctypes.c_wchar() # fail == 2.6
    a['CByteType'] = ctypes.c_byte()
    a['CUByteType'] = ctypes.c_ubyte()
    a['CShortType'] = ctypes.c_short()
    a['CUShortType'] = ctypes.c_ushort()
    a['CIntType'] = ctypes.c_int()
    a['CUIntType'] = ctypes.c_uint()
    a['CLongType'] = ctypes.c_long()
    a['CULongType'] = ctypes.c_ulong()
    a['CLongLongType'] = ctypes.c_longlong()
    a['CULongLongType'] = ctypes.c_ulonglong()
    a['CFloatType'] = ctypes.c_float()
    a['CDoubleType'] = ctypes.c_double()
    a['CSizeTType'] = ctypes.c_size_t()
    a['CLibraryLoaderType'] = ctypes.cdll
    a['StructureType'] = _Struct
    a['BigEndianStructureType'] = ctypes.BigEndianStructure()
#NOTE: also LittleEndianStructureType and UnionType... abstract classes
#NOTE: remember for ctypesobj.contents creates a new python object
#NOTE: ctypes.c_int._objects is memberdescriptor for object's __dict__
#NOTE: base class of all ctypes data types is non-public _CData

try: # python 2.6
    import fractions
    import number
    import io
    from io import StringIO as TextIO
    # built-in functions (CH 2)
    a['ByteArrayType'] = bytearray([1])
    # numeric and mathematical types (CH 9)
    a['FractionType'] = fractions.Fraction()
    a['NumberType'] = numbers.Number()
    # generic operating system services (CH 15)
    a['IOBaseType'] = io.IOBase()
    a['RawIOBaseType'] = io.RawIOBase()
    a['TextIOBaseType'] = io.TextIOBase()
    a['BufferedIOBaseType'] = io.BufferedIOBase()
    a['UnicodeIOType'] = TextIO() # the new StringIO
    a['LoggingAdapterType'] = logging.LoggingAdapter(_logger,_dict) # pickle ok
    if HAS_CTYPES:
        a['CBoolType'] = ctypes.c_bool(1)
        a['CLongDoubleType'] = ctypes.c_longdouble()
except ImportError:
    pass
try: # python 2.7
    import argparse
    # data types (CH 8)
    a['OrderedDictType'] = collections.OrderedDict(_dict)
    a['CounterType'] = collections.Counter(_dict)
    if HAS_CTYPES:
        a['CSSizeTType'] = ctypes.c_ssize_t()
    # generic operating system services (CH 15)
    a['NullHandlerType'] = logging.NullHandler() # pickle ok  # new 2.7
    a['ArgParseFileType'] = argparse.FileType() # pickle ok
#except AttributeError:
except ImportError:
    pass

# -- pickle fails on all below here -----------------------------------------
# types module (part of CH 8)
a['CodeType'] = compile('','','exec')
a['DictProxyType'] = type.__dict__
a['DictProxyType2'] = _newclass.__dict__
a['EllipsisType'] = Ellipsis
a['ClosedFileType'] = open(os.devnull, 'wb', buffering=0).close()
a['GetSetDescriptorType'] = array.array.typecode
a['LambdaType'] = _lambda = lambda x: lambda y: x #XXX: works when not imported!
a['MemberDescriptorType'] = type.__dict__['__weakrefoffset__']
a['MemberDescriptorType2'] = datetime.timedelta.days
a['MethodType'] = _method = _class()._method #XXX: works when not imported!
a['ModuleType'] = datetime
a['NotImplementedType'] = NotImplemented
a['SliceType'] = slice(1)
a['UnboundMethodType'] = _class._method #XXX: works when not imported!
a['TextWrapperType'] = open(os.devnull, 'r') # same as mode='w','w+','r+'
a['BufferedRandomType'] = open(os.devnull, 'r+b') # same as mode='w+b'
a['BufferedReaderType'] = open(os.devnull, 'rb') # (default: buffering=-1)
a['BufferedWriterType'] = open(os.devnull, 'wb')
try: # oddities: deprecated
    from _pyio import open as _open
    a['PyTextWrapperType'] = _open(os.devnull, 'r', buffering=-1)
    a['PyBufferedRandomType'] = _open(os.devnull, 'r+b', buffering=-1)
    a['PyBufferedReaderType'] = _open(os.devnull, 'rb', buffering=-1)
    a['PyBufferedWriterType'] = _open(os.devnull, 'wb', buffering=-1)
except ImportError:
    pass
# other (concrete) object types
if PY3:
    d['CellType'] = (_lambda)(0).__closure__[0]
    a['XRangeType'] = _xrange = range(1)
else:
    d['CellType'] = (_lambda)(0).func_closure[0]
    a['XRangeType'] = _xrange = xrange(1)
d['MethodDescriptorType'] = type.__dict__['mro']
d['WrapperDescriptorType'] = type.__repr__
a['WrapperDescriptorType2'] = type.__dict__['__module__']
# built-in functions (CH 2)
if PY3: _methodwrap = (1).__lt__
else: _methodwrap = (1).__cmp__
d['MethodWrapperType'] = _methodwrap
a['StaticMethodType'] = staticmethod(_method)
a['ClassMethodType'] = classmethod(_method)
a['PropertyType'] = property()
d['SuperType'] = super(Exception, _exception)
# string services (CH 7)
if PY3: _in = _bytes
else: _in = _str
a['InputType'] = _cstrI = StringIO(_in)
a['OutputType'] = _cstrO = StringIO()
# data types (CH 8)
a['WeakKeyDictionaryType'] = weakref.WeakKeyDictionary()
a['WeakValueDictionaryType'] = weakref.WeakValueDictionary()
a['ReferenceType'] = weakref.ref(_instance)
a['DeadReferenceType'] = weakref.ref(_class())
a['ProxyType'] = weakref.proxy(_instance)
a['DeadProxyType'] = weakref.proxy(_class())
a['CallableProxyType'] = weakref.proxy(_instance2)
a['DeadCallableProxyType'] = weakref.proxy(_class2())
a['QueueType'] = Queue.Queue()
# numeric and mathematical types (CH 9)
d['PartialType'] = functools.partial(int,base=2)
if PY3:
    a['IzipType'] = zip('0','1')
else:
    a['IzipType'] = itertools.izip('0','1')
a['ChainType'] = itertools.chain('0','1')
d['ItemGetterType'] = operator.itemgetter(0)
d['AttrGetterType'] = operator.attrgetter('__repr__')
# file and directory access (CH 10)
if PY3: _fileW = _cstrO
else: _fileW = _tmpf
# data persistence (CH 11)
if HAS_ALL:
    a['ConnectionType'] = _conn = sqlite3.connect(':memory:')
    a['CursorType'] = _conn.cursor()
a['ShelveType'] = shelve.Shelf({})
# data compression and archiving (CH 12)
if HAS_ALL:
    a['BZ2FileType'] = bz2.BZ2File(os.devnull) #FIXME: fail >= 3.3
    a['BZ2CompressorType'] = bz2.BZ2Compressor()
    a['BZ2DecompressorType'] = bz2.BZ2Decompressor()
#a['ZipFileType'] = _zip = zipfile.ZipFile(os.devnull,'w') #FIXME: fail >= 3.2
#_zip.write(_tempfile,'x') [causes annoying warning/error printed on import]
#a['ZipInfoType'] = _zip.getinfo('x')
a['TarFileType'] = tarfile.open(fileobj=_fileW,mode='w')
# file formats (CH 13)
a['DialectType'] = csv.get_dialect('excel')
a['PackerType'] = xdrlib.Packer()
# optional operating system services (CH 16)
a['LockType'] = threading.Lock()
a['RLockType'] = threading.RLock()
# generic operating system services (CH 15) # also closed/open and r/w/etc...
a['NamedLoggerType'] = _logger = logging.getLogger(__name__) #FIXME: fail >= 3.2 and <= 2.6
#a['FrozenModuleType'] = __hello__ #FIXME: prints "Hello world..."
# interprocess communication (CH 17)
if PY3:
    a['SocketType'] = _socket = socket.socket() #FIXME: fail >= 3.3
    a['SocketPairType'] = socket.socketpair()[0] #FIXME: fail >= 3.3
else:
    a['SocketType'] = _socket = socket.socket()
    a['SocketPairType'] = _socket._sock
# python runtime services (CH 27)
if PY3:
    a['GeneratorContextManagerType'] = contextlib.contextmanager(max)([1])
else:
    a['GeneratorContextManagerType'] = contextlib.GeneratorContextManager(max)

try: # ipython
    __IPYTHON__ is True # is ipython
except NameError:
    # built-in constants (CH 4)
    a['QuitterType'] = quit
    d['ExitType'] = a['QuitterType']
try: # numpy
    from numpy import ufunc as _numpy_ufunc
    from numpy import array as _numpy_array
    from numpy import int32 as _numpy_int32
    a['NumpyUfuncType'] = _numpy_ufunc
    a['NumpyArrayType'] = _numpy_array
    a['NumpyInt32Type'] = _numpy_int32
except ImportError:
    pass
try: # python 2.6
    # numeric and mathematical types (CH 9)
    a['ProductType'] = itertools.product('0','1')
    # generic operating system services (CH 15)
    a['FileHandlerType'] = logging.FileHandler(os.devnull) #FIXME: fail >= 3.2 and <= 2.6
    a['RotatingFileHandlerType'] = logging.handlers.RotatingFileHandler(os.devnull)
    a['SocketHandlerType'] = logging.handlers.SocketHandler('localhost',514)
    a['MemoryHandlerType'] = logging.handlers.MemoryHandler(1)
except AttributeError:
    pass
try: # python 2.7
    # data types (CH 8)
    a['WeakSetType'] = weakref.WeakSet() # 2.7
#   # generic operating system services (CH 15) [errors when dill is imported]
#   a['ArgumentParserType'] = _parser = argparse.ArgumentParser('PROG')
#   a['NamespaceType'] = _parser.parse_args() # pickle ok
#   a['SubParsersActionType'] = _parser.add_subparsers()
#   a['MutuallyExclusiveGroupType'] = _parser.add_mutually_exclusive_group()
#   a['ArgumentGroupType'] = _parser.add_argument_group()
except AttributeError:
    pass

# -- dill fails in some versions below here ---------------------------------
# types module (part of CH 8)
a['FileType'] = open(os.devnull, 'rb', buffering=0) # same 'wb','wb+','rb+'
# FIXME: FileType fails >= 3.1
# built-in functions (CH 2)
a['ListIteratorType'] = iter(_list) # empty vs non-empty FIXME: fail < 3.2
a['TupleIteratorType']= iter(_tuple) # empty vs non-empty FIXME: fail < 3.2
a['XRangeIteratorType'] = iter(_xrange) # empty vs non-empty FIXME: fail < 3.2
# data types (CH 8)
a['PrettyPrinterType'] = pprint.PrettyPrinter() #FIXME: fail >= 3.2 and == 2.5
# numeric and mathematical types (CH 9)
a['CycleType'] = itertools.cycle('0') #FIXME: fail < 3.2
# file and directory access (CH 10)
a['TemporaryFileType'] = _tmpf #FIXME: fail >= 3.2 and == 2.5
# data compression and archiving (CH 12)
a['GzipFileType'] = gzip.GzipFile(fileobj=_fileW) #FIXME: fail > 3.2 and <= 2.6
# generic operating system services (CH 15)
a['StreamHandlerType'] = logging.StreamHandler() #FIXME: fail >= 3.2 and == 2.5
try: # python 2.6
    # numeric and mathematical types (CH 9)
    a['PermutationsType'] = itertools.permutations('0') #FIXME: fail < 3.2
    a['CombinationsType'] = itertools.combinations('0',1) #FIXME: fail < 3.2
except AttributeError:
    pass
try: # python 2.7
    # numeric and mathematical types (CH 9)
    a['RepeatType'] = itertools.repeat(0) #FIXME: fail < 3.2
    a['CompressType'] = itertools.compress('0',[1]) #FIXME: fail < 3.2
    #XXX: ...and etc
except AttributeError:
    pass

# -- dill fails on all below here -------------------------------------------
# types module (part of CH 8)
x['GeneratorType'] = _generator = _function(1) #XXX: priority
x['FrameType'] = _generator.gi_frame #XXX: inspect.currentframe()
x['TracebackType'] = _function2()[1] #(see: inspect.getouterframes,getframeinfo)
# other (concrete) object types
# (also: Capsule / CObject ?)
# built-in functions (CH 2)
x['SetIteratorType'] = iter(_set) #XXX: empty vs non-empty
# built-in types (CH 5)
if PY3:
    x['DictionaryItemIteratorType'] = iter(type.__dict__.items())
    x['DictionaryKeyIteratorType'] = iter(type.__dict__.keys())
    x['DictionaryValueIteratorType'] = iter(type.__dict__.values())
else:
    x['DictionaryItemIteratorType'] = type.__dict__.iteritems()
    x['DictionaryKeyIteratorType'] = type.__dict__.iterkeys()
    x['DictionaryValueIteratorType'] = type.__dict__.itervalues()
# string services (CH 7)
x['StructType'] = struct.Struct('c')
x['CallableIteratorType'] = _srepattern.finditer('')
x['SREMatchType'] = _srepattern.match('')
x['SREScannerType'] = _srepattern.scanner('')
x['StreamReader'] = codecs.StreamReader(_cstrI) #XXX: ... and etc
# python object persistence (CH 11)
# x['DbShelveType'] = shelve.open('foo','n')#,protocol=2) #XXX: delete foo
if HAS_ALL:
    x['DbmType'] = dbm.open(_tempfile,'n')
# x['DbCursorType'] = _dbcursor = anydbm.open('foo','n') #XXX: delete foo
# x['DbType'] = _dbcursor.db
# data compression and archiving (CH 12)
x['ZlibCompressType'] = zlib.compressobj()
x['ZlibDecompressType'] = zlib.decompressobj()
# file formats (CH 13)
x['CSVReaderType'] = csv.reader(_cstrI)
x['CSVWriterType'] = csv.writer(_cstrO)
x['CSVDictReaderType'] = csv.DictReader(_cstrI)
x['CSVDictWriterType'] = csv.DictWriter(_cstrO,{})
# cryptographic services (CH 14)
x['HashType'] = hashlib.md5()
x['HMACType'] = hmac.new(_in)
# generic operating system services (CH 15)
#x['CursesWindowType'] = _curwin = curses.initscr() #FIXME: messes up tty
#x['CursesTextPadType'] = textpad.Textbox(_curwin)
#x['CursesPanelType'] = panel.new_panel(_curwin)
if HAS_CTYPES:
    x['CCharPType'] = ctypes.c_char_p()
    x['CWCharPType'] = ctypes.c_wchar_p()
    x['CVoidPType'] = ctypes.c_void_p()
    x['CDLLType'] = _cdll = ctypes.CDLL(None)
    x['PyDLLType'] = _pydll = ctypes.pythonapi
    x['FuncPtrType'] = _cdll._FuncPtr()
    x['CCharArrayType'] = ctypes.create_string_buffer(1)
    x['CWCharArrayType'] = ctypes.create_unicode_buffer(1)
    x['CParamType'] = ctypes.byref(_cchar)
    x['LPCCharType'] = ctypes.pointer(_cchar)
    x['LPCCharObjType'] = _lpchar = ctypes.POINTER(ctypes.c_char)
    x['NullPtrType'] = _lpchar()
    x['NullPyObjectType'] = ctypes.py_object()
    x['PyObjectType'] = ctypes.py_object(1)
    x['FieldType'] = _field = _Struct._field
    x['CFUNCTYPEType'] = _cfunc = ctypes.CFUNCTYPE(ctypes.c_char)
    x['CFunctionType'] = _cfunc(str)
try: # python 2.6
    # numeric and mathematical types (CH 9)
    x['MethodCallerType'] = operator.methodcaller('mro') # 2.6
except AttributeError:
    pass
try: # python 2.7
    # built-in types (CH 5)
    x['MemoryType'] = memoryview(_in) # 2.7
    x['MemoryType2'] = memoryview(bytearray(_in)) # 2.7
    if PY3:
        x['DictItemsType'] = _dict.items() # 2.7
        x['DictKeysType'] = _dict.keys() # 2.7
        x['DictValuesType'] = _dict.values() # 2.7
    else:
        x['DictItemsType'] = _dict.viewitems() # 2.7
        x['DictKeysType'] = _dict.viewkeys() # 2.7
        x['DictValuesType'] = _dict.viewvalues() # 2.7
    # generic operating system services (CH 15)
    x['RawTextHelpFormatterType'] = argparse.RawTextHelpFormatter('PROG')
    x['RawDescriptionHelpFormatterType'] = argparse.RawDescriptionHelpFormatter('PROG')
    x['ArgDefaultsHelpFormatterType'] = argparse.ArgumentDefaultsHelpFormatter('PROG')
except NameError:
    pass
try: # python 2.7 (and not 3.1)
    x['CmpKeyType'] = _cmpkey = functools.cmp_to_key(_methodwrap) # 2.7, >=3.2
    x['CmpKeyObjType'] = _cmpkey('0') #2.7, >=3.2
except AttributeError:
    pass
if PY3: # oddities: removed, etc
    x['BufferType'] = x['MemoryType']
else:
    x['BufferType'] = buffer('')

# -- cleanup ----------------------------------------------------------------
a.update(d) # registered also succeed
os.remove(_tempfile)


# EOF

########NEW FILE########
__FILENAME__ = get_objgraph
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
use objgraph to plot the reference paths for types found in dill.types
"""
#XXX: useful if could read .pkl file and generate the graph... ?

import dill as pickle
#pickle.debug.trace(True)
#import pickle

# get all objects for testing
from dill import load_types
load_types(pickleable=True,unpickleable=True)
from dill import objects

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print ("Please provide exactly one type name (e.g. 'IntType')")
        msg = "\n"
        for objtype in list(objects.keys())[:40]:
            msg += objtype + ', '
        print (msg + "...")
    else:
        objtype = str(sys.argv[-1])
        obj = objects[objtype]
        try:
            import objgraph
            objgraph.show_refs(obj, filename=objtype+'.png')
        except ImportError:
            print ("Please install 'objgraph' to view object graphs")


# EOF

########NEW FILE########
__FILENAME__ = unpickle
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

if __name__ == '__main__':
  import sys
  import dill
  for file in sys.argv[1:]:
    print (dill.load(open(file,'r')))


########NEW FILE########
__FILENAME__ = dill_bugs

########NEW FILE########
__FILENAME__ = test_classdef
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

import dill as pickle
#import pickle

# test classdefs
class _class:
    def _method(self):
        pass
    def ok(self):
        return True

class _class2:
    def __call__(self):
        pass
    def ok(self):
        return True

class _newclass(object):
    def _method(self):
        pass
    def ok(self):
        return True

class _newclass2(object):
    def __call__(self):
        pass
    def ok(self):
        return True

o = _class()
oc = _class2()
n = _newclass()
nc = _newclass2()

clslist = [_class,_class2,_newclass,_newclass2]
objlist = [o,oc,n,nc]
_clslist = [pickle.dumps(obj) for obj in clslist]
_objlist = [pickle.dumps(obj) for obj in objlist]

for obj in clslist:
    globals().pop(obj.__name__)
del clslist
for obj in ['o','oc','n','nc']:
    globals().pop(obj)
del objlist
del obj

for obj,cls in zip(_objlist,_clslist):
    _cls = pickle.loads(cls)
    _obj = pickle.loads(obj)
    assert _obj.ok()
    assert _cls.ok(_cls())

# test namedtuple
import sys
if hex(sys.hexversion) >= '0x20600f0':
    from collections import namedtuple

    Z = namedtuple("Z", ['a','b'])
    Zi = Z(0,1)
    X = namedtuple("Y", ['a','b'])
    X.__name__ = "X" #XXX: name must 'match' or fails to pickle
    Xi = X(0,1)

    assert Z == pickle.loads(pickle.dumps(Z))
    assert Zi == pickle.loads(pickle.dumps(Zi))
    assert X == pickle.loads(pickle.dumps(X))
    assert Xi == pickle.loads(pickle.dumps(Xi))


# EOF

########NEW FILE########
__FILENAME__ = test_detect
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

from dill.detect import baditems, badobjects, badtypes, errors, parent, at

import inspect

f = inspect.currentframe()
assert baditems(f) == [f]
assert baditems(globals()) == [f]
assert badobjects(f) is f
assert badtypes(f) == type(f)
assert isinstance(errors(f), TypeError)
d = badtypes(f, 1)
assert isinstance(d, dict)
assert list(badobjects(f, 1).keys()) == list(d.keys())
assert list(errors(f, 1).keys()) == list(d.keys())
assert len(set([err.args[0] for err in list(errors(f, 1).values())])) is 1

x = [4,5,6,7]
listiter = iter(x)
obj = parent(listiter, list)
assert obj is x

assert parent(obj, int) is x[-1]
assert at(id(at)) is at


########NEW FILE########
__FILENAME__ = test_extendpickle
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

import dill as pickle
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

def my_fn(x):
    return x * 17

obj = lambda : my_fn(34)
assert obj() == 578

obj_io = StringIO()
pickler = pickle.Pickler(obj_io)
pickler.dump(obj)

obj_str = obj_io.getvalue()

obj2_io = StringIO(obj_str)
unpickler = pickle.Unpickler(obj2_io)
obj2 = unpickler.load()

assert obj2() == 578

########NEW FILE########
__FILENAME__ = test_mixins
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

import dill

def wtf(x,y,z):
  def zzz():
    return x
  def yyy():
    return y
  def xxx():
    return z
  return zzz,yyy

def quad(a=1, b=1, c=0):
  inverted = [False]
  def invert():
    inverted[0] = not inverted[0]
  def dec(f):
    def func(*args, **kwds):
      x = f(*args, **kwds)
      if inverted[0]: x = -x
      return a*x**2 + b*x + c
    func.__wrapped__ = f
    func.invert = invert
    return func
  return dec


@quad(a=0,b=2)
def double_add(*args):
  return sum(args)

fx = sum([1,2,3])

### to make it interesting...
def quad_factory(a=1,b=1,c=0):
  def dec(f):
    def func(*args,**kwds):
      fx = f(*args,**kwds)
      return a*fx**2 + b*fx + c
    return func
  return dec

@quad_factory(a=0,b=4,c=0)
def quadish(x):
  return x+1

quadratic = quad_factory()

def doubler(f):
  def inner(*args, **kwds):
    fx = f(*args, **kwds)
    return 2*fx
  return inner

@doubler
def quadruple(x):
  return 2*x


if __name__ == '__main__':

  # test mixins
  assert double_add(1,2,3) == 2*fx
  double_add.invert()
  assert double_add(1,2,3) == -2*fx

  _d = dill.copy(double_add)
  assert _d(1,2,3) == -2*fx
  _d.invert()
  assert _d(1,2,3) == 2*fx

  assert _d.__wrapped__(1,2,3) == fx

  # test some stuff from source and pointers
  ds = dill.source
  dd = dill.detect
  assert ds.getsource(dd.freevars(quadish)['f']) == '@quad_factory(a=0,b=4,c=0)\ndef quadish(x):\n  return x+1\n'
  assert ds.getsource(dd.freevars(quadruple)['f']) == '@doubler\ndef quadruple(x):\n  return 2*x\n'
  assert ds.importable(quadish, source=False) == 'from %s import quadish\n' % __name__
  assert ds.importable(quadruple, source=False) == 'from %s import quadruple\n' % __name__
  assert ds.importable(quadratic, source=False) == 'from %s import quadratic\n' % __name__
  assert ds.importable(double_add, source=False) == 'from %s import double_add\n' % __name__
  assert ds.importable(quadish, source=True) == 'def quad_factory(a=1,b=1,c=0):\n  def dec(f):\n    def func(*args,**kwds):\n      fx = f(*args,**kwds)\n      return a*fx**2 + b*fx + c\n    return func\n  return dec\n\n@quad_factory(a=0,b=4,c=0)\ndef quadish(x):\n  return x+1\n'
  assert ds.importable(quadruple, source=True) == 'def doubler(f):\n  def inner(*args, **kwds):\n    fx = f(*args, **kwds)\n    return 2*fx\n  return inner\n\n@doubler\ndef quadruple(x):\n  return 2*x\n'
  #***** #FIXME: this needs work
  result = ds.importable(quadratic, source=True)
  a,b,c,result = result.split('\n',3)
  assert result == '\ndef dec(f):\n  def func(*args,**kwds):\n    fx = f(*args,**kwds)\n    return a*fx**2 + b*fx + c\n  return func\n'
  assert set([a,b,c]) == set(['a = 1', 'c = 0', 'b = 1'])
  #*****
  assert ds.importable(double_add, source=True) == 'def quad(a=1, b=1, c=0):\n  inverted = [False]\n  def invert():\n    inverted[0] = not inverted[0]\n  def dec(f):\n    def func(*args, **kwds):\n      x = f(*args, **kwds)\n      if inverted[0]: x = -x\n      return a*x**2 + b*x + c\n    func.__wrapped__ = f\n    func.invert = invert\n    return func\n  return dec\n\n@quad(a=0,b=2)\ndef double_add(*args):\n  return sum(args)\n'


# EOF

########NEW FILE########
__FILENAME__ = test_module
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

import sys
import dill
import test_mixins as module

cached = (module.__cached__ if hasattr(module, "__cached__")
          else module.__file__ + "c")

module.a = 1234

pik_mod = dill.dumps(module)

module.a = 0

# remove module
del sys.modules[module.__name__]
del module

module = dill.loads(pik_mod)
assert hasattr(module, "a") and module.a == 1234
assert module.double_add(1, 2, 3) == 2 * module.fx

# clean up
import os
os.remove(cached)
if os.path.exists("__pycache__") and not os.listdir("__pycache__"):
    os.removedirs("__pycache__")

########NEW FILE########
__FILENAME__ = test_moduledict
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

import dill

def f(func):
  def w(*args):
    return f(*args)
  return w

@f
def f2(): pass

# check when __main__ and on import
assert dill.pickles(f2)


import doctest
import logging
logging.basicConfig(level=logging.DEBUG)

class SomeUnreferencedUnpicklableClass(object):
    def __reduce__(self):
        raise Exception

unpicklable = SomeUnreferencedUnpicklableClass()

# This works fine outside of Doctest:
serialized = dill.dumps(lambda x: x)

# should not try to pickle unpicklable object in __globals__
def tests():
    """
    >>> serialized = dill.dumps(lambda x: x)
    """
    return

#print("\n\nRunning Doctest:")
doctest.testmod()

########NEW FILE########
__FILENAME__ = test_nested
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
test dill's ability to handle nested functions
"""

import dill as pickle
import math
#import pickle

# the nested function: pickle should fail here, but dill is ok.
def adder(augend):
    zero = [0]

    def inner(addend):
        return addend + augend + zero[0]
    return inner

# rewrite the nested function using a class: standard pickle should work here.
class cadder(object):
    def __init__(self, augend):
        self.augend = augend
        self.zero = [0]

    def __call__(self, addend):
        return addend + self.augend + self.zero[0]

# rewrite again, but as an old-style class
class c2adder:
    def __init__(self, augend):
        self.augend = augend
        self.zero = [0]

    def __call__(self, addend):
        return addend + self.augend + self.zero[0]

# some basic stuff
a = [0, 1, 2]

# some basic class stuff
class basic(object):
    pass

class basic2:
    pass


if __name__ == '__main__':
    x = 5
    y = 1

    # pickled basic stuff
    pa = pickle.dumps(a)
    pmath = pickle.dumps(math) #XXX: FAILS in pickle
    pmap = pickle.dumps(map)
    # ...
    la = pickle.loads(pa)
    lmath = pickle.loads(pmath)
    lmap = pickle.loads(pmap)
    assert list(map(math.sin, a)) == list(lmap(lmath.sin, la))

    # pickled basic class stuff
    pbasic2 = pickle.dumps(basic2)
    _pbasic2 = pickle.loads(pbasic2)()
    pbasic = pickle.dumps(basic)
    _pbasic = pickle.loads(pbasic)()

    # pickled c2adder
    pc2adder = pickle.dumps(c2adder)
    pc2add5 = pickle.loads(pc2adder)(x)
    assert pc2add5(y) == x+y

    # pickled cadder
    pcadder = pickle.dumps(cadder)
    pcadd5 = pickle.loads(pcadder)(x)
    assert pcadd5(y) == x+y

    # raw adder and inner
    add5 = adder(x)
    assert add5(y) == x+y

    # pickled adder
    padder = pickle.dumps(adder)
    padd5 = pickle.loads(padder)(x)
    assert padd5(y) == x+y

    # pickled inner
    pinner = pickle.dumps(add5) #XXX: FAILS in pickle
    p5add = pickle.loads(pinner)
    assert p5add(y) == x+y

    # testing moduledict where not __main__
    try:
            import test_moduledict
            error = None
    except:
            import sys
            error = sys.exc_info()[1]
    assert error is None
    # clean up
    import os
    name = 'test_moduledict.py'
    if os.path.exists(name) and os.path.exists(name+'c'):
        os.remove(name+'c')

    if os.path.exists(name) and hasattr(test_moduledict, "__cached__") \
       and os.path.exists(test_moduledict.__cached__):
        os.remove(getattr(test_moduledict, "__cached__"))

    if os.path.exists("__pycache__") and not os.listdir("__pycache__"):
        os.removedirs("__pycache__")


# EOF

########NEW FILE########
__FILENAME__ = test_objects
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE
"""
demonstrate dill's ability to pickle different python types
test pickling of all Python Standard Library objects (currently: CH 1-14 @ 2.7)
"""

import dill as pickle
#pickle.debug.trace(True)
#import pickle

# get all objects for testing
from dill import load_types
load_types(pickleable=True,unpickleable=False)
#load_types(pickleable=True,unpickleable=True)
from dill import objects

# helper objects
class _class:
    def _method(self):
        pass
# objects that *fail* if imported
special = {}
special['LambdaType'] = _lambda = lambda x: lambda y: x
special['MethodType'] = _method = _class()._method
special['UnboundMethodType'] = _class._method
objects.update(special)

def pickles(name, exact=False):
    """quick check if object pickles with dill"""
    obj = objects[name]
    try:
        pik = pickle.loads(pickle.dumps(obj))
        if exact:
            try:
                assert pik == obj
            except AssertionError:
                assert type(obj) == type(pik)
                print ("weak: %s %s" % (name, type(obj)))
        else:
            assert type(obj) == type(pik)
    except Exception:
        print ("fails: %s %s" % (name, type(obj)))
    return


if __name__ == '__main__':

    for member in objects.keys():
       #pickles(member, exact=True)
        pickles(member, exact=False)


# EOF

########NEW FILE########
__FILENAME__ = test_source
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

from dill.source import getsource, getname, _wrap, likely_import
from dill.source import getimportable


import sys
PY3 = sys.version_info[0] >= 3

f = lambda x: x**2
def g(x): return f(x) - x

def h(x):
  def g(x): return x
  return g(x) - x 

class Foo(object):
  def bar(self, x):
    return x*x+x
_foo = Foo()

def add(x,y):
  return x+y

# yes, same as 'f', but things are tricky when it comes to pointers
squared = lambda x:x**2

class Bar:
  pass
_bar = Bar()

                       # inspect.getsourcelines # dill.source.getblocks
assert getsource(f) == 'f = lambda x: x**2\n'
assert getsource(g) == 'def g(x): return f(x) - x\n'
assert getsource(h) == 'def h(x):\n  def g(x): return x\n  return g(x) - x \n'
assert getname(f) == 'f'
assert getname(g) == 'g'
assert getname(h) == 'h'
assert _wrap(f)(4) == 16
assert _wrap(g)(4) == 12
assert _wrap(h)(4) == 0

assert getname(Foo) == 'Foo'
assert getname(Bar) == 'Bar'
assert getsource(Bar) == 'class Bar:\n  pass\n'
assert getsource(Foo) == 'class Foo(object):\n  def bar(self, x):\n    return x*x+x\n'
#XXX: add getsource for  _foo, _bar

assert getimportable(add) == 'from %s import add\n' % __name__
assert getimportable(squared) == 'from %s import squared\n' % __name__
assert getimportable(Foo) == 'from %s import Foo\n' % __name__
assert getimportable(Foo.bar) == 'from %s import bar\n' % __name__
assert getimportable(_foo.bar) == 'from %s import bar\n' % __name__
assert getimportable(None) == 'None\n'
assert getimportable(100) == '100\n'

assert getimportable(add, byname=False) == 'def add(x,y):\n  return x+y\n'
assert getimportable(squared, byname=False) == 'squared = lambda x:x**2\n'
assert getimportable(None, byname=False) == 'None\n'
assert getimportable(Bar, byname=False) == 'class Bar:\n  pass\n'
assert getimportable(Foo, byname=False) == 'class Foo(object):\n  def bar(self, x):\n    return x*x+x\n'
assert getimportable(Foo.bar, byname=False) == 'def bar(self, x):\n  return x*x+x\n'
assert getimportable(Foo.bar, byname=True) == 'from %s import bar\n' % __name__
assert getimportable(Foo.bar, alias='memo', byname=True) == 'from %s import bar as memo\n' % __name__
assert getimportable(_foo, byname=False).startswith("import dill\nclass Foo(object):\n  def bar(self, x):\n    return x*x+x\ndill.loads(")
assert getimportable(Foo, alias='memo', byname=True) == 'from %s import Foo as memo\n' % __name__
assert getimportable(squared, alias='memo', byname=True) == 'from %s import squared as memo\n' % __name__
assert getimportable(squared, alias='memo', byname=False) == 'memo = squared = lambda x:x**2\n'
assert getimportable(add, alias='memo', byname=False) == 'def add(x,y):\n  return x+y\n\nmemo = add\n'
assert getimportable(None, alias='memo', byname=False) == 'memo = None\n'
assert getimportable(100, alias='memo', byname=False) == 'memo = 100\n'
assert getimportable(add, explicit=True) == 'from %s import add\n' % __name__
assert getimportable(squared, explicit=True) == 'from %s import squared\n' % __name__
assert getimportable(Foo, explicit=True) == 'from %s import Foo\n' % __name__
assert getimportable(Foo.bar, explicit=True) == 'from %s import bar\n' % __name__
assert getimportable(_foo.bar, explicit=True) == 'from %s import bar\n' % __name__
assert getimportable(None, explicit=True) == 'None\n'
assert getimportable(100, explicit=True) == '100\n'


try:
    from numpy import array
    x = array([1,2,3])
    assert getimportable(x) == 'from numpy import array\narray([1, 2, 3])\n'
    assert getimportable(array) == 'from numpy.core.multiarray import array\n'
    assert getimportable(x, byname=False) == 'from numpy import array\narray([1, 2, 3])\n'
    assert getimportable(array, byname=False) == 'from numpy.core.multiarray import array\n'
except ImportError: pass

# test itself
assert likely_import(likely_import)=='from dill.source import likely_import\n'

# builtin functions and objects
if PY3: builtin = 'builtins'
else: builtin = '__builtin__'
assert likely_import(pow) == 'pow\n'
assert likely_import(100) == '100\n'
assert likely_import(True) == 'True\n'
assert likely_import(pow, explicit=True) == 'from %s import pow\n' % builtin
assert likely_import(100, explicit=True) == '100\n'
assert likely_import(True, explicit=True) == 'True\n' if PY3 else 'from %s import True\n' % builtin
# this is kinda BS... you can't import a None
assert likely_import(None) == 'None\n'
assert likely_import(None, explicit=True) == 'None\n'

# other imported functions
from math import sin
assert likely_import(sin) == 'from math import sin\n'

# interactively defined functions
assert likely_import(add) == 'from %s import add\n' % __name__

# interactive lambdas
assert likely_import(squared) == 'from %s import squared\n' % __name__

# classes and class instances
try: #XXX: should this be a 'special case'?
    from StringIO import StringIO
    x = "from StringIO import StringIO\n"
    y = x
except ImportError:
    from io import BytesIO as StringIO
    x = "from io import BytesIO\n"
    y = "from _io import BytesIO\n"
s = StringIO()
assert likely_import(StringIO) == x
assert likely_import(s) == y

# interactively defined classes and class instances
assert likely_import(Foo) == 'from %s import Foo\n' % __name__
assert likely_import(_foo) == 'from %s import Foo\n' % __name__


# EOF

########NEW FILE########
__FILENAME__ = test_temp
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

from dill.temp import dump, dump_source, dumpIO, dumpIO_source
from dill.temp import load, load_source, loadIO, loadIO_source


f = lambda x: x**2
x = [1,2,3,4,5]

# source code to tempfile
pyfile = dump_source(f, alias='_f')
_f = load_source(pyfile)
assert _f(4) == f(4)

# source code to stream
pyfile = dumpIO_source(f, alias='_f')
_f = loadIO_source(pyfile)
assert _f(4) == f(4)

# pickle to tempfile
dumpfile = dump(x)
_x = load(dumpfile)
assert _x == x

# pickle to stream
dumpfile = dumpIO(x)
_x = loadIO(dumpfile)
assert _x == x


########NEW FILE########
__FILENAME__ = test_weakref
#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @caltech and @uqfoundation)
# Copyright (c) 2008-2014 California Institute of Technology.
# License: 3-clause BSD.  The full license text is available at:
#  - http://trac.mystic.cacr.caltech.edu/project/pathos/browser/dill/LICENSE

import dill
import weakref

class _class:
    def _method(self):
        pass

class _class2:
    def __call__(self):
        pass

class _newclass(object):
    def _method(self):
        pass

class _newclass2(object):
    def __call__(self):
        pass

def _function():
    pass

o = _class()
oc = _class2()
n = _newclass()
nc = _newclass2()
f = _function
z = _class
x = _newclass

r = weakref.ref(o)
dr = weakref.ref(_class())
p = weakref.proxy(o)
dp = weakref.proxy(_class())
c = weakref.proxy(oc)
dc = weakref.proxy(_class2())

m = weakref.ref(n)
dm = weakref.ref(_newclass())
t = weakref.proxy(n)
dt = weakref.proxy(_newclass())
d = weakref.proxy(nc)
dd = weakref.proxy(_newclass2())

fr = weakref.ref(f)
fp = weakref.proxy(f)
#zr = weakref.ref(z) #XXX: weakrefs not allowed for classobj objects
#zp = weakref.proxy(z) #XXX: weakrefs not allowed for classobj objects
xr = weakref.ref(x)
xp = weakref.proxy(x)

objlist = [r,dr,m,dm,fr,xr, p,dp,t,dt, c,dc,d,dd, fp,xp]

for obj in objlist:
  res = dill.detect.errors(obj)
  if res:
    print ("%s:\n  %s" % (obj, res))
  assert not res

########NEW FILE########
