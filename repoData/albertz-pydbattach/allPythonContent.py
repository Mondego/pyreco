__FILENAME__ = better_exchook

# by Albert Zeyer, www.az2000.de
# code under GPLv3+
# 2011-04-15

# This is a simple replacement for the standard Python exception handler (sys.excepthook).
# In addition to what the standard handler does, it also prints all referenced variables
# (no matter if local, global or builtin) of the code line of each stack frame.
# See below for some examples and some example output.

# https://github.com/albertz/py_better_exchook

import sys, os, os.path

def parse_py_statement(line):
	state = 0
	curtoken = ""
	spaces = " \t\n"
	ops = ".,;:+-*/%&=(){}[]^<>"
	i = 0
	def _escape_char(c):
		if c == "n": return "\n"
		elif c == "t": return "\t"
		else: return c
	while i < len(line):
		c = line[i]
		i += 1
		if state == 0:
			if c in spaces: pass
			elif c in ops: yield ("op", c)
			elif c == "#": state = 6
			elif c == "\"": state = 1
			elif c == "'": state = 2
			else:
				curtoken = c
				state = 3
		elif state == 1: # string via "
			if c == "\\": state = 4
			elif c == "\"":
				yield ("str", curtoken)
				curtoken = ""
				state = 0
			else: curtoken += c
		elif state == 2: # string via '
			if c == "\\": state = 5
			elif c == "'":
				yield ("str", curtoken)
				curtoken = ""
				state = 0
			else: curtoken += c
		elif state == 3: # identifier
			if c in spaces + ops + "#\"'":
				yield ("id", curtoken)
				curtoken = ""
				state = 0
				i -= 1
			else: curtoken += c
		elif state == 4: # escape in "
			curtoken += _escape_char(c)
			state = 1
		elif state == 5: # escape in '
			curtoken += _escape_char(c)
			state = 2
		elif state == 6: # comment
			curtoken += c
	if state == 3: yield ("id", curtoken)
	elif state == 6: yield ("comment", curtoken)


pykeywords = set([
	"for","in","while","print","continue","break",
	"if","else","elif","yield","return","def","class",
	"raise","try","except","import","as","pass","lambda",
	])

def grep_full_py_identifiers(tokens):
	global pykeywords
	tokens = list(tokens)
	i = 0
	while i < len(tokens):
		tokentype, token = tokens[i]
		i += 1
		if tokentype != "id": continue
		while i+1 < len(tokens) and tokens[i] == ("op", ".") and tokens[i+1][0] == "id":
			token += "." + tokens[i+1][1]
			i += 2
		if token == "": continue
		if token in pykeywords: continue
		if token[0] in ".0123456789": continue
		yield token

	
def debug_shell(user_ns, user_global_ns):
	from IPython.Shell import IPShellEmbed,IPShell
	ipshell = IPShell(argv=[], user_ns=user_ns, user_global_ns=user_global_ns)
	#ipshell()
	ipshell.mainloop()

def output(s): print s

def output_limit():
	return 300

def pp_extra_info(obj, depthlimit = 3):
	s = []
	if hasattr(obj, "__len__"):
		try:
			if type(obj) in [str,list,tuple,dict] and len(obj) <= 5:
				pass # don't print len in this case
			else:
				s += ["len = " + str(obj.__len__())]
		except: pass
	if depthlimit > 0 and hasattr(obj, "__getitem__"):
		try:
			if type(obj) in [str]:
				pass # doesn't make sense to get subitems here
			else:
				subobj = obj.__getitem__(0)
				extra_info = pp_extra_info(subobj, depthlimit - 1)
				if extra_info != "":
					s += ["_[0]: {" + extra_info + "}"]
		except: pass
	return ", ".join(s)
	
def pretty_print(obj):
	s = repr(obj)
	limit = output_limit()
	if len(s) > limit:
		s = s[:limit - 3] + "..."
	extra_info = pp_extra_info(obj)
	if extra_info != "": s += ", " + extra_info
	return s

def fallback_findfile(filename):
	mods = [ m for m in sys.modules.values() if m and hasattr(m, "__file__") and filename in m.__file__ ]
	if len(mods) == 0: return None
	altfn = mods[0].__file__
	if altfn[-4:-1] == ".py": altfn = altfn[:-1] # *.pyc or whatever
	return altfn

def better_exchook(etype, value, tb):
	output("EXCEPTION")
	output('Traceback (most recent call last):')
	topFrameLocals,topFrameGlobals = None,None
	try:
		import linecache
		limit = None
		if hasattr(sys, 'tracebacklimit'):
			limit = sys.tracebacklimit
		n = 0
		_tb = tb
		def _resolveIdentifier(namespace, id):
			obj = namespace[id[0]]
			for part in id[1:]:
				obj = getattr(obj, part)
			return obj
		def _trySet(old, func):
			if old is not None: return old
			try: return func()
			except: return old
		while _tb is not None and (limit is None or n < limit):
			f = _tb.tb_frame
			topFrameLocals,topFrameGlobals = f.f_locals,f.f_globals
			lineno = _tb.tb_lineno
			co = f.f_code
			filename = co.co_filename
			name = co.co_name
			output('  File "%s", line %d, in %s' % (filename,lineno,name))
			if not os.path.isfile(filename):
				altfn = fallback_findfile(filename)
				if altfn:
					output("    -- couldn't find file, trying this instead: " + altfn)
					filename = altfn
			linecache.checkcache(filename)
			line = linecache.getline(filename, lineno, f.f_globals)
			if line:
				line = line.strip()
				output('    line: ' + line)
				output('    locals:')
				alreadyPrintedLocals = set()
				for tokenstr in grep_full_py_identifiers(parse_py_statement(line)):
					splittedtoken = tuple(tokenstr.split("."))
					for token in map(lambda i: splittedtoken[0:i], range(1, len(splittedtoken) + 1)):
						if token in alreadyPrintedLocals: continue
						tokenvalue = None
						tokenvalue = _trySet(tokenvalue, lambda: "<local> " + pretty_print(_resolveIdentifier(f.f_locals, token)))
						tokenvalue = _trySet(tokenvalue, lambda: "<global> " + pretty_print(_resolveIdentifier(f.f_globals, token)))
						tokenvalue = _trySet(tokenvalue, lambda: "<builtin> " + pretty_print(_resolveIdentifier(f.f_builtins, token)))
						tokenvalue = tokenvalue or "<not found>"
						output('      ' + ".".join(token) + " = " + tokenvalue)
						alreadyPrintedLocals.add(token)
				if len(alreadyPrintedLocals) == 0: output("       no locals")
			else:
				output('    -- code not available --')
			_tb = _tb.tb_next
			n += 1

	except Exception, e:
		output("ERROR: cannot get more detailed exception info because:")
		import traceback
		for l in traceback.format_exc().split("\n"): output("   " + l)
		output("simple traceback:")
		traceback.print_tb(tb)

	import types
	def _some_str(value):
		try: return str(value)
		except: return '<unprintable %s object>' % type(value).__name__
	def _format_final_exc_line(etype, value):
		valuestr = _some_str(value)
		if value is None or not valuestr:
			line = "%s" % etype
		else:
			line = "%s: %s" % (etype, valuestr)
		return line
	if (isinstance(etype, BaseException) or
		isinstance(etype, types.InstanceType) or
		etype is None or type(etype) is str):
		output(_format_final_exc_line(etype, value))
	else:
		output(_format_final_exc_line(etype.__name__, value))

	debug = False
	try: debug = int(os.environ["DEBUG"]) != 0
	except: pass
	if debug:
		output("---------- DEBUG SHELL -----------")
		debug_shell(user_ns=topFrameLocals, user_global_ns=topFrameGlobals)
		
def install():
	sys.excepthook = better_exchook
	
if __name__ == "__main__":
	# some examples
	# this code produces this output: https://gist.github.com/922622
	
	try:
		x = {1:2, "a":"b"}
		def f():
			y = "foo"
			x, 42, sys.stdin.__class__, sys.exc_info, y, z
		f()
	except:
		better_exchook(*sys.exc_info())

	try:
		f = lambda x: None
		f(x, y)
	except:
		better_exchook(*sys.exc_info())

	# use this to overwrite the global exception handler
	sys.excepthook = better_exchook
	# and fail
	finalfail(sys)

########NEW FILE########
__FILENAME__ = dummy-python-proc
#!/usr/bin/python

import time, ctypes

pid = ctypes.pythonapi.getpid()

i = 0
while True:
	print("<" + str(pid) + ">", i)
	time.sleep(1)
	i += 1

########NEW FILE########
__FILENAME__ = pyinjectcode
print "Hello from pyinjectcode:", __file__

import os, os.path, sys
mydir = os.path.dirname(__file__)
if mydir not in sys.path:
	sys.path += [mydir]

import sys, thread
threads = [t for t in sys._current_frames().keys() if t != thread.get_ident()]

print "pyinjectcode found threads:", threads
assert threads, "fatal, no threads found"

tid = max(threads) # well, stupid, just made up, but in my case this seems to be the main thread :P
print "attaching to thread", tid

import pythreadhacks
pythreadhacks.pdbIntoRunningThread(tid)

########NEW FILE########
__FILENAME__ = pythonhdr
# This code was contributed by Lenard Lindstrom, see
# http://sourceforge.net/tracker/?func=detail&aid=1619889&group_id=71702&atid=532156

# pythonhdr.py module
# Compatible with Python 2.3 and up, ctypes 1.0.1.

"""Python Application Programmer's Interface (Partial)

For information on functions and types in this module refer to the "Python/C
API Reference Manual" in the Python documentation.

Any exception raised by an API function is propagated. There is no need to
check the return type for an error. Where a PyObject * argument is expected
just pass in a Python object. Integer arguments will accept a Python int or
long. Other arguments require the correct ctypes type. The same relationships
apply to function return types. Py_ssize_t is available for Python 2.5 and up.
It defaults to c_int for earlier versions. Finally, a FILE_ptr type is defined
for FILE *.

Be aware that the Python file api funtions are an implementation detail that
may change.

It is safe to do an import * from this module.


An example where a Python string is copied to a ctypes character array:

>>> from pythonhdr import PyString_AsStringAndSize, Py_ssize_t
>>> from ctypes import c_char, byref, pointer, memmove, addressof
>>>
>>> char_array10 = (c_char * 10)()
>>> char_array10.raw
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
>>> py_str10 = "x" * 10
>>> py_str10
'xxxxxxxxxx'
>>>
>>> cp = pointer(c_char())
>>> sz = Py_ssize_t(0)
>>> PyString_AsStringAndSize(s, byref(cp), byref(sz))
0
>>> memmove(addressof(char_array10), cp, sz.value)
8111688
>>> del cp
>>> char_array10.raw
'xxxxxxxxxx'
"""

import ctypes


# Figure out Py_ssize_t (PEP 353).
#
# Py_ssize_t is only defined for Python 2.5 and above, so it defaults to
# ctypes.c_int for earlier versions.
#
if hasattr(ctypes.pythonapi, 'Py_InitModule4'):
    Py_ssize_t = ctypes.c_int
elif hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
    Py_ssize_t = ctypes.c_int64
else:
    raise TypeError("Cannot determine type of Py_ssize_t")

# Declare PyObject, allowing for additional Py_TRACE_REFS fields.
#
# By definition PyObject contains only PyObject_HEAD. Within Python it is
# accessible as the builtin 'object'. Whether or not the interpreter was built
# with Py_TRACE_REFS can be decided by checking object's size, its
# __basicsize__ attribute.
#
# Object references in Py_TRACE_REFS are not declared as ctypes.py_object to
# avoid reference counting. A PyObject pointer is used instead of a void
# pointer because technically the two types need not be the same size
# or alignment.
#
# To discourage access of the PyObject fields they are mangled into invalid
# Python identifiers. Only valid identifier characters are used in the
# unlikely event a future Python has a dictionary optimised for identifiers.
#
def make_PyObject(with_trace_refs=False):
    global PyObject
    class PyObject(ctypes.Structure):

        """This root object structure defines PyObject_HEAD.

        To declare other Python object structures simply subclass PyObject and
        provide a _fields_ attribute with the additional fields of the
        structure. Direct construction of PyObject instances is not supported.
        Instance are created with the from_address method instead. These
        instances should be deleted when finished.


        An usage example with the Python float type:

        >>> from pythonhdr import PyObject
        >>> from ctypes import c_double
        >>>
        >>> class PyFloatObject(PyObject):
        ...     _fields_ = [("ob_fval", c_double)]
        ...
        >>> d = 3.14
        >>> d
        3.1400000000000001
        >>>
        >>> e = PyFloatObject.from_address(id(d)).ob_fval
        >>> e
        3.1400000000000001
        """

        def __new__(cls, *args, **kwds):
            raise NotImplementedError(
                "Direct creation of %s instances is not supported" %
                cls.__name__)

    if with_trace_refs:
        optional_fields = [('9_ob_next', ctypes.POINTER(PyObject)),
                           ('9_ob_prev', ctypes.POINTER(PyObject))]
    else:
        optional_fields = []
    regular_fields = [('ob_refcnt', Py_ssize_t),
                      ('ob_type', ctypes.POINTER(PyObject))]
    PyObject._fields_ = optional_fields + regular_fields

make_PyObject()
if object.__basicsize__ > ctypes.sizeof(PyObject):
    make_PyObject(True)

assert ctypes.sizeof(PyObject) == object.__basicsize__, (
       "%s.%s declaration is inconsistent with actual PyObject size" %
       (__name__, PyObject.__name__))

# Buffer Protocol API.
#
PyObject_AsCharBuffer = ctypes.pythonapi.PyObject_AsCharBuffer
PyObject_AsCharBuffer.restype = ctypes.c_int
PyObject_AsCharBuffer.argtypes = [ctypes.py_object,
                                  ctypes.POINTER(
                                      ctypes.POINTER(ctypes.c_char)),
                                  ctypes.POINTER(Py_ssize_t)]

PyObject_AsReadBuffer = ctypes.pythonapi.PyObject_AsReadBuffer
PyObject_AsReadBuffer.restype = ctypes.c_int
PyObject_AsReadBuffer.argtypes = [ctypes.py_object,
                                  ctypes.POINTER(ctypes.c_void_p),
                                  ctypes.POINTER(Py_ssize_t)]

PyObject_CheckReadBuffer = ctypes.pythonapi.PyObject_CheckReadBuffer
PyObject_CheckReadBuffer.restype = ctypes.c_int
PyObject_CheckReadBuffer.argtypes = [ctypes.py_object]

PyObject_AsWriteBuffer = ctypes.pythonapi.PyObject_AsWriteBuffer
PyObject_AsWriteBuffer.restype = ctypes.c_int
PyObject_AsWriteBuffer.argtypes = [ctypes.py_object,
                                   ctypes.POINTER(ctypes.c_void_p),
                                   ctypes.POINTER(Py_ssize_t)]

# Buffer Object API.
#
Py_END_OF_BUFFER = -1

PyBuffer_FromReadWriteObject = ctypes.pythonapi.PyBuffer_FromReadWriteObject
PyBuffer_FromReadWriteObject.restype = ctypes.py_object
PyBuffer_FromReadWriteObject.argtypes = [ctypes.py_object,
                                         Py_ssize_t,
                                         Py_ssize_t]

PyBuffer_FromMemory = ctypes.pythonapi.PyBuffer_FromMemory
PyBuffer_FromMemory.restype = ctypes.py_object
PyBuffer_FromMemory.argtypes = [ctypes.c_void_p,
                                Py_ssize_t]

PyBuffer_FromReadWriteMemory = ctypes.pythonapi.PyBuffer_FromReadWriteMemory
PyBuffer_FromReadWriteMemory.restype = ctypes.py_object
PyBuffer_FromReadWriteMemory.argtypes = [ctypes.c_void_p,
                                         Py_ssize_t]

PyBuffer_New = ctypes.pythonapi.PyBuffer_New
PyBuffer_New.restype = ctypes.py_object
PyBuffer_New.argtypes = [Py_ssize_t]

# File API.
#
# A FILE_ptr type is used instead of c_void_p because technically a pointer
# to structure can have a different size or alignment to a void pointer.
#
# Note that the file api may change.
#
try:
    class FILE(ctypes.Structure):
        pass
    FILE_ptr = ctypes.POINTER(FILE)

    PyFile_FromFile = ctypes.pythonapi.PyFile_FromFile
    PyFile_FromFile.restype = ctypes.py_object
    PyFile_FromFile.argtypes = [FILE_ptr,
                                ctypes.c_char_p,
                                ctypes.c_char_p,
                                ctypes.CFUNCTYPE(ctypes.c_int, FILE_ptr)]

    PyFile_AsFile = ctypes.pythonapi.PyFile_AsFile
    PyFile_AsFile.restype = FILE_ptr
    PyFile_AsFile.argtypes = [ctypes.py_object]
except AttributeError:
    del FILE_ptr

# Cell API.
#
PyCell_New = ctypes.pythonapi.PyCell_New
PyCell_New.restype = ctypes.py_object
PyCell_New.argtypes = [ctypes.py_object]

PyCell_Get = ctypes.pythonapi.PyCell_Get
PyCell_Get.restype = ctypes.py_object
PyCell_Get.argtypes = [ctypes.py_object]

PyCell_Set = ctypes.pythonapi.PyCell_Set
PyCell_Set.restype = ctypes.c_int
PyCell_Set.argtypes = [ctypes.py_object,
                       ctypes.py_object]

# String API.
#
PyString_AsStringAndSize = ctypes.pythonapi.PyString_AsStringAndSize
PyString_AsStringAndSize.restype = ctypes.c_int
PyString_AsStringAndSize.argtypes = [ctypes.py_object,
                                     ctypes.POINTER(
                                         ctypes.POINTER(ctypes.c_char)),
                                     ctypes.POINTER(Py_ssize_t)]

# Thread State API.
#
PyThreadState_SetAsyncExc = ctypes.pythonapi.PyThreadState_SetAsyncExc
PyThreadState_SetAsyncExc.restype = ctypes.c_int
PyThreadState_SetAsyncExc.argtypes = [ctypes.c_long,
                                      ctypes.py_object]

# OS API.
#
PyOS_InputHook = ctypes.CFUNCTYPE(ctypes.c_int).in_dll(ctypes.pythonapi,
                                                       'PyOS_InputHook')

# Memory API.
#
PyMem_Malloc = ctypes.pythonapi.PyMem_Malloc
PyMem_Malloc.restype = ctypes.c_void_p
PyMem_Malloc.argtypes = [ctypes.c_size_t]

PyMem_Realloc = ctypes.pythonapi.PyMem_Realloc
PyMem_Realloc.restype = ctypes.c_void_p
PyMem_Realloc.argtypes = [ctypes.c_void_p,
                          ctypes.c_size_t]

PyMem_Free = ctypes.pythonapi.PyMem_Free
PyMem_Free.restype = None
PyMem_Free.argtypes = [ctypes.c_void_p]


# Clean up so dir(...) only shows what is exported.
#
del ctypes, make_PyObject, FILE

########NEW FILE########
__FILENAME__ = pythreadhacks
import ctypes
import _ctypes

pyapi = ctypes.pythonapi
PyObj_FromPtr = _ctypes.PyObj_FromPtr

import thread, time, sys


def find_thread(frame):
	for t,f in sys._current_frames().items():
		while f is not None:
			if f == frame: return t
			f = f.f_back
	return None


mainthread = thread.get_ident()

def tracefunc(frame,ev,arg):
	thread = find_thread(frame)
	if thread == mainthread: pass
	else:
		#print "trace", ev, "from thread", thread
		pass
	return tracefunc

def dummytracer(*args): return dummytracer


import pythonhdr
from pythonhdr import PyObject, Py_ssize_t
CO_MAXBLOCKS = 20 # from Python/Include/code.h
POINTER = ctypes.POINTER
PPyObject = POINTER(PyObject)
c_int, c_long = ctypes.c_int, ctypes.c_long

def Py_INCREF(pyobj): pyobj.contents.ob_refcnt += 1
def Py_DECREF(pyobj): pyobj.contents.ob_refcnt -= 1
def Py_XINCREF(pyobj):
	if pyobj: Py_INCREF(pyobj)
def Py_XDECREF(pyobj):
	if pyobj: Py_DECREF(pyobj)

# see frameobject.h for PyTryBlock and PyFrameObject

class PyTryBlock(ctypes.Structure):
	_fields_ = [
		("b_type", c_int),
		("b_handler", c_int),
		("b_level", c_int),
	]

class PyThreadState(ctypes.Structure): pass # predeclaration, see below

class PyFrameObject(PyObject):
	_fields_ = [
		("ob_size", Py_ssize_t), # from PyObject_VAR_HEAD
		# start of PyFrameObject
		("f_back", PPyObject),
		("f_code", PPyObject),
		("f_builtins", PPyObject),
		("f_globals", PPyObject),
		("f_locals", PPyObject),
		("f_valuestack", POINTER(PPyObject)),
		("f_stacktop", POINTER(PPyObject)),
		("f_trace", PPyObject),
		("f_exc_type", PPyObject),
		("f_exc_value", PPyObject),
		("f_exc_traceback", PPyObject),
		("f_tstate", POINTER(PyThreadState)),
		("f_lasti", c_int),
		("f_lineno", c_int),
		("f_iblock", c_int),
		("f_blockstack", PyTryBlock * 20),
		("f_localsplus", PPyObject),
	]

# see pystate.h for PyThreadState

# typedef int (*Py_tracefunc)(PyObject *, struct _frame *, int, PyObject *);
Py_tracefunc = ctypes.CFUNCTYPE(c_int, PPyObject, POINTER(PyFrameObject), c_int, PPyObject)

class PyInterpreterState(ctypes.Structure): pass # not yet needed

PyThreadState._fields_ = [
		("next", POINTER(PyThreadState)),
		("interp", POINTER(PyInterpreterState)),
		("frame", POINTER(PyFrameObject)),
		("recursion_depth", c_int),
		("tracing", c_int),
		("use_tracing", c_int),
		("c_profilefunc", Py_tracefunc),
		("c_tracefunc", Py_tracefunc),
		("c_profileobj", PPyObject),
		("c_traceobj", PPyObject),
		("curexc_type", PPyObject),
		("curexc_value", PPyObject),
		("curexc_traceback", PPyObject),
		("exc_type", PPyObject),
		("exc_value", PPyObject),
		("exc_traceback", PPyObject),
		("dict", PPyObject),
		("tick_counter", c_int),
		("gilstate_counter", c_int),
		("async_exc", PPyObject),
		("thread_id", c_long),
	]


def getPPyObjectPtr(pyobj):
	if not pyobj: return 0
	return _ctypes.addressof(pyobj.contents)

def PPyObject_FromObj(obj):
	return PPyObject(PyObject.from_address(id(obj)))
	
def getThreadStateP(frame):
	frame = PyFrameObject.from_address(id(frame))
	tstate = frame.f_tstate
	return tstate

def getThreadState(frame):
	return getThreadStateP(frame).contents

def getTickCounter(frame):
	return getThreadState(frame).tick_counter


c_tracefunc_trampoline = None
def initCTraceFuncTrampoline():
	global c_tracefunc_trampoline
	
	origtrace = sys.gettrace() # remember orig
	sys.settrace(dummytracer) # it doesn't really matter which tracer, we always get the same trampoline
	
	frame = sys._getframe()
	tstate = getThreadState(frame)
	
	c_tracefunc_trampoline = tstate.c_tracefunc
	
	sys.settrace(origtrace) # recover
initCTraceFuncTrampoline()	

	
def _setTraceOfThread(tstate, func, arg):
	tstate = tstate.contents
	assert type(tstate) is PyThreadState
	assert type(func) is Py_tracefunc
	assert type(arg) is PPyObject
	
	tstate.use_tracing = 0 # disable while we are in here. just for safety
	
	# we assume _Py_TracingPossible > 0 here. we cannot really change it anyway
	# this is basically copied from PyEval_SetTrace in ceval.c
	temp = tstate.c_traceobj # PPyObject
	Py_XINCREF(arg)
	tstate.c_tracefunc = Py_tracefunc()
	tstate.c_traceobj = PPyObject()
	# Must make sure that profiling is not ignored if 'temp' is freed
	tstate.use_tracing = int(bool(tstate.c_profilefunc))
	Py_XDECREF(temp)
	tstate.c_tracefunc = func
	tstate.c_traceobj = arg
	# Flag that tracing or profiling is turned on
	tstate.use_tracing = int(bool(func) or bool(tstate.c_profilefunc))

def _setTraceFuncOnFrames(frame, tracefunc):
	while frame is not None:
		frame.f_trace = tracefunc
		frame = frame.f_back

# NOTE: This only works if at least one tracefunc is currently installed via sys.settrace().
# This is because we need _Py_TracingPossible > 0.
def setTraceOfThread(tid, tracefunc):
	frame = sys._current_frames()[tid]
	_setTraceFuncOnFrames(frame, tracefunc)
	tstateP = getThreadStateP(frame)
	
	global _setTraceOfThread
	if not type(_setTraceOfThread) is ctypes.pythonapi._FuncPtr:
		try:
			settrace = ctypes.pythonapi.injected_PyEval_SetTraceEx
			settrace.argtypes = [POINTER(PyThreadState), Py_tracefunc, PPyObject]
			_setTraceOfThread = settrace
			print "successfully linked to injected_PyEval_SetTraceEx"
		except: pass
	
	if tracefunc is None:
		_setTraceOfThread(tstateP, Py_tracefunc(), PPyObject())
	else:
		_setTraceOfThread(tstateP, c_tracefunc_trampoline, PPyObject_FromObj(tracefunc))
		
def setGlobalTraceFunc(tracefunc):
	# ensures _Py_TracingPossible > 0
	# sets tstate.c_tracefunc = call_trampoline
	# see PyEval_SetTrace in ceval.c
	# see sys_settrace in sysmodule.c
	sys.settrace(tracefunc)

	myframe = sys._getframe()
	tstate = getThreadState(myframe)
	c_traceobj = tstate.c_traceobj
	assert getPPyObjectPtr(tstate.c_traceobj) == id(tracefunc)

	mythread = thread.get_ident()
	frames = sys._current_frames()
	for t,frame in frames.iteritems():
		if t == mythread: continue
		setTraceOfThread(t, tracefunc)

#setGlobalTraceFunc(tracefunc)

def pdbIntoRunningThread(tid):
	from pdb import Pdb
	#from IPython.Debugger import Pdb
	
	pdb = Pdb()
	pdb.reset()
	
	import threading
	injectEvent = threading.Event()
	
	def inject_tracefunc(frame,ev,arg):
		injectEvent.set()
		pdb.interaction(frame, None)
		return pdb.trace_dispatch
	
	sys.settrace(dummytracer) # set some dummy. required by setTraceOfThread

	# go into loop. in some cases, it doesn't seem to work for some reason...
	while not injectEvent.isSet():
		setTraceOfThread(tid, inject_tracefunc)
	
		# Wait until we got into the inject_tracefunc.
		# This may be important as there is a chance that some of these
		# objects will get freed before they are used. (Which is probably
		# some other refcounting bug somewhere.)
		injectEvent.wait(1)

def main():
	def threadfunc(i):
		while True:
			for i in xrange(1000): pass
			time.sleep(1)
	
	threads = map(lambda i: thread.start_new_thread(threadfunc, (i,)), range(1))
	while True:
		if all(t in sys._current_frames() for t in threads): break	
	print "threads:", threads

	pdbThread = threads[0]
	pdbIntoRunningThread(pdbThread)

	while True:
		if pdbThread not in sys._current_frames().keys():
			print "thread exited"
			break
		#frames = sys._current_frames()
		#for t in threads:
		#	frame = frames[t]
			#print "tick counter of top frame in thread", t, ":", getTickCounter(frame)			
			#print " and trace func:", frame.f_trace
		time.sleep(1)

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = test_pyinjectcode
print "injecting ..."
from ctypes import *
m = CDLL("pyinjectcode.dylib")
m.inject()

print "injecting done"

import time
time.sleep(1)

########NEW FILE########
__FILENAME__ = cluster

"""
Cobra's built in clustering framework
"""

import sys
import time
import cobra
import dcode
import Queue
import struct
import socket
import threading
import subprocess

cluster_port = 32123
cluster_ip = "224.69.69.69"

sub_cmd = """
import cobra.cluster
import cobra.dcode
import urllib2
if %s:
    x = urllib2.Request("%s")
    cobra.dcode.enableDcodeClient()
    cobra.dcode.addDcodeServer(x.get_host().split(":")[0])
cobra.cluster.getAndDoWork("%s")
"""

class ClusterWork(object):
    """
    Extend this object to create your own work units.  Do it in
    a proper module (and not __main__ to be able to use this
    in conjunction with cobra.dcode).
    """
    def __init__(self):
        object.__init__(self)

    def work(self):
        """
        Actually do the work associated with this work object.
        """
        print "OVERRIDE ME"

    def done(self):
        """
        This is called back on the server once a work unit
        is complete and returned.
        """
        print "OVERRIDE DONE"

class ClusterServer:
    def __init__(self, name, maxsize=0, docode=False):
        self.added = False
        self.name = name
        self.inprog = 0
        self.maxsize = maxsize
        self.queue = Queue.Queue(maxsize)
        self.cobraname = cobra.shareObject(self)
        if docode: dcode.enableDcodeServer()

    def runServer(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while (self.added == False or
               self.queue.empty() == False or
               self.inprog > 0):
            buf = "cobra:%s:%s:%d" % (self.name, self.cobraname, cobra.COBRA_PORT)
            sock.sendto(buf, (cluster_ip, cluster_port))
            time.sleep(1)

    def addWork(self, work):
        """
        Add a work object to the ClusterServer.  This 
        """
        self.added = True # One time add detection
        if not isinstance(work, ClusterWork):
            raise Exception("%s is not a ClusterWork extension!")
        self.queue.put(work)

    def getWork(self):
        try:
            ret = self.queue.get_nowait()
            self.inprog += 1
            return ret
        except Queue.Empty, e:
            return None

    def doneWork(self, work):
        """
        Used by the clients to report work as done.
        """
        self.inprog -= 1
        work.done()

class ClusterClient:

    """
    Listen for our name (or any name if name=="*") on the cobra cluster
    multicast address and if we find a server in need, go help.

    maxwidth is the number of work units to do in parallel
    docode will enable code sharing with the server
    threaded == True will use threads, otherwise subprocess of the python interpreter (OMG CLUSTER)
    """

    def __init__(self, name, maxwidth=4, threaded=True, docode=False):
        self.go = True
        self.name = name
        self.width = 0
        self.maxwidth = maxwidth
        self.threaded = threaded
        self.verbose = False
        self.docode = docode

        if docode: dcode.enableDcodeClient()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("",cluster_port))
        mreq = struct.pack("4sL", socket.inet_aton(cluster_ip), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def processWork(self):
        """
        Runs handing out work up to maxwidth until self.go == False.
        """
        while self.go:
            
            buf, sockaddr = self.sock.recvfrom(4096)
            if self.width >= self.maxwidth:
                continue

            if not buf.startswith("cobra:") and not buf.startswith("cobrassl:"):
                continue

            info = buf.split(":")
            if len(info) != 4:
                continue

            server, svrport = sockaddr
            cc,name,cobject,portstr = info
            if (self.name != name) and (self.name != "*"):
                continue

            port = int(portstr)

            #FIXME this should fire a thread...
            if self.docode:
                dcode.addDcodeServer(server, port=port)

            uri = "%s://%s:%d/%s" % (cc,server,port,cobject)
            self.fireRunner(uri)

    def fireRunner(self, uri):
        if self.threaded:
            thr = threading.Thread(target=self.threadWorker, args=(uri,))
            thr.setDaemon(True)
            thr.start()
        else:
            thr = threading.Thread(target=self.threadForker, args=(uri,))
            thr.setDaemon(True)
            thr.start()

    def threadWorker(self, uri):
        self.width += 1
        try:
            return getAndDoWork(uri)
        finally:
            self.width -= 1

    def threadForker(self, uri):
        self.width += 1
        cmd = sub_cmd % (self.docode, uri, uri)
        try:
            sub = subprocess.Popen([sys.executable, '-c', cmd])
            sub.wait()
        finally:
            self.width -= 1

def getAndDoWork(uri):
    proxy = cobra.CobraProxy(uri)
    work = proxy.getWork()
    # If we got work, do it.
    if work != None:
        work.work()
        proxy.doneWork(work)


########NEW FILE########
__FILENAME__ = dcode
"""

Cobra's distributed code module capable of allowing
serialization of code from one system to another.

Particularly useful for clustering and workunit stuff.

"""
import os
import sys
import imp
import cobra

class DcodeFinder(object):

    def find_module(self, fullname, path=None):
        fobj, filename, typeinfo = imp.find_module(fullname, path)
        if os.path.isdir(filename):
            filename = os.path.join(filename, "__init__.py")

        if not os.path.exists(filename):
            return None

        fbytes = file(filename, "rb").read()
        fbytes = fbytes.replace("\r\n","\n")
        return DcodeLoader(fbytes, filename, typeinfo)

class DcodeLoader(object):

    def __init__(self, fbytes, filename, typeinfo):
        object.__init__(self)
        self.fbytes = fbytes
        self.filename = filename
        self.typeinfo = typeinfo

    def load_module(self, fullname):
        mod = sys.modules.get(fullname)
        if mod == None:
            mod = imp.new_module(fullname)
            sys.modules[fullname] = mod
            mod.__file__ = self.filename
            mod.__loader__ = self

            exec self.fbytes in mod.__dict__

        return mod

class DcodeImporter(object):

    def __init__(self, uri):
        object.__init__(self)
        if not cobra.isCobraUri(uri):
            raise ImportError
        try:
            self.cobra = cobra.CobraProxy(uri)
        except Exception, e:
            raise ImportError

    def find_module(self, fullname, path=None):
        return self.cobra.find_module(fullname, path)

def enableDcodeClient():
    """
    Once having called this, a client will be able to add cobra URIs
    to sys.path (one will be added automatically for the optional
    server parameter) and code will be imported via the distributed method.
    """
    if DcodeImporter not in sys.path_hooks:
        sys.path_hooks.append(DcodeImporter)

def addDcodeServer(server, port=None, override=False, ssl=False):
    scheme = "cobra"
    if ssl:
        scheme = "cobrassl"

    if port == None:
        port = cobra.COBRA_PORT

    uri = "%s://%s:%d/DcodeServer" % (scheme, server, port)
    if uri not in sys.path:
        if override:
            sys.path.insert(0, uri)
        else:
            sys.path.append(uri)

def enableDcodeServer():
    cobra.shareObject(DcodeFinder(), "DcodeServer")


########NEW FILE########
__FILENAME__ = elf_lookup
## EM enumeration definitions
EM_NONE = 0
EM_M32 = 1
EM_SPARC = 2
EM_386 = 3
EM_68K = 4
EM_88K = 5
EM_860 = 7
EM_MIPS = 8
EM_S370 = 9
EM_MIPS_RS3_LE = 10
EM_PARISC = 15
EM_VPP500 = 17
EM_SPARC32PLUS = 18
EM_960 = 19
EM_PPC = 20
EM_PPC64 = 21
EM_S390 = 22
EM_V800 = 36
EM_FR20 = 37
EM_RH32 = 38
EM_RCE = 39
EM_ARM = 40
EM_FAKE_ALPHA = 41
EM_SH = 42
EM_SPARCV9 = 43
EM_TRICORE = 44
EM_ARC = 45
EM_H8_300 = 46
EM_H8_300H = 47
EM_H8S = 48
EM_H8_500 = 49
EM_IA_64 = 50
EM_MIPS_X = 51
EM_COLDFIRE = 52
EM_68HC12 = 53
EM_MMA = 54
EM_PCP = 55
EM_NCPU = 56
EM_NDR1 = 57
EM_STARCORE = 58
EM_ME16 = 59
EM_ST100 = 60
EM_TINYJ = 61
EM_X86_64 = 62
EM_PDSP = 63
EM_FX66 = 66
EM_ST9PLUS = 67
EM_ST7 = 68
EM_68HC16 = 69
EM_68HC11 = 70
EM_68HC08 = 71
EM_68HC05 = 72
EM_SVX = 73
EM_ST19 = 74
EM_VAX = 75
EM_CRIS = 76
EM_JAVELIN = 77
EM_FIREPATH = 78
EM_ZSP = 79
EM_MMIX = 80
EM_HUANY = 81
EM_PRISM = 82
EM_AVR = 83
EM_FR30 = 84
EM_D10V = 85
EM_D30V = 86
EM_V850 = 87
EM_M32R = 88
EM_MN10300 = 89
EM_MN10200 = 90
EM_PJ = 91
EM_OPENRISC = 92
EM_ARC_A5 = 93
EM_XTENSA = 94
EM_NUM = 95
EM_ALPHA = 0x9026

# There are plenty more of these to
# fill in, but...  this is all I need
# for now...
e_machine_32 =  (
                EM_386,
                EM_PPC
                )
e_machine_64 =  (
                EM_PPC64,
                EM_SPARCV9,
                EM_X86_64
                )

e_machine_types = {
EM_NONE:"No machine",
EM_M32:"AT&T WE 32100",
EM_SPARC:"SUN SPARC",
EM_386:"Intel 80386",
EM_68K:"Motorola m68k family",
EM_88K:"Motorola m88k family",
EM_860:"Intel 80860",
EM_MIPS:"MIPS R3000 big-endian",
EM_S370:"IBM System/370",
EM_MIPS_RS3_LE:"MIPS R3000 little-endian",
EM_PARISC:"HPPA",
EM_VPP500:"Fujitsu VPP500",
EM_SPARC32PLUS:"Suns v8plus",
EM_960:"Intel 80960",
EM_PPC:"PowerPC",
EM_PPC64:"PowerPC 64-bit",
EM_S390:"IBM S390",
EM_V800:"NEC V800 series",
EM_FR20:"Fujitsu FR20",
EM_RH32:"TRW RH-32",
EM_RCE:"Motorola RCE",
EM_ARM:"ARM",
EM_FAKE_ALPHA:"Digital Alpha",
EM_SH:"Hitachi SH",
EM_SPARCV9:"SPARC v9 64-bit",
EM_TRICORE:"Siemens Tricore",
EM_ARC:"Argonaut RISC Core",
EM_H8_300:"Hitachi H8/300",
EM_H8_300H:"Hitachi H8/300H",
EM_H8S:"Hitachi H8S",
EM_H8_500:"Hitachi H8/500",
EM_IA_64:"Intel Merced",
EM_MIPS_X:"Stanford MIPS-X",
EM_COLDFIRE:"Motorola Coldfire",
EM_68HC12:"Motorola M68HC12",
EM_MMA:"Fujitsu MMA Multimedia",
EM_PCP:"Siemens PCP",
EM_NCPU:"Sony nCPU embeeded RISC",
EM_NDR1:"Denso NDR1 microprocessor",
EM_STARCORE:"Motorola Start*Core processor",
EM_ME16:"Toyota ME16 processor",
EM_ST100:"STMicroelectronic ST100 processor",
EM_TINYJ:"Advanced Logic Corp. Tinyj",
EM_X86_64:"AMD x86-64 architecture",
EM_PDSP:"Sony DSP Processor",
EM_FX66:"Siemens FX66 microcontroller",
EM_ST9PLUS:"STMicroelectronics ST9+ 8/16 mc",
EM_ST7:"STmicroelectronics ST7 8 bit mc",
EM_68HC16:"Motorola MC68HC16 microcontroller",
EM_68HC11:"Motorola MC68HC11 microcontroller",
EM_68HC08:"Motorola MC68HC08 microcontroller",
EM_68HC05:"Motorola MC68HC05 microcontroller",
EM_SVX:"Silicon Graphics SVx",
EM_ST19:"STMicroelectronics ST19 8 bit mc",
EM_VAX:"Digital VAX",
EM_CRIS:"Axis Communications 32-bit embedded processor",
EM_JAVELIN:"Infineon Technologies 32-bit embedded processor",
EM_FIREPATH:"Element 14 64-bit DSP Processor",
EM_ZSP:"LSI Logic 16-bit DSP Processor",
EM_MMIX:"Donald Knuths educational 64-bit processor",
EM_HUANY:"Harvard University machine-independent object files",
EM_PRISM:"SiTera Prism",
EM_AVR:"Atmel AVR 8-bit microcontroller",
EM_FR30:"Fujitsu FR30",
EM_D10V:"Mitsubishi D10V",
EM_D30V:"Mitsubishi D30V",
EM_V850:"NEC v850",
EM_M32R:"Mitsubishi M32R",
EM_MN10300:"Matsushita MN10300",
EM_MN10200:"Matsushita MN10200",
EM_PJ:"picoJava",
EM_OPENRISC:"OpenRISC 32-bit embedded processor",
EM_ARC_A5:"ARC Cores Tangent-A5",
EM_XTENSA:"Tensilica Xtensa Architecture",
EM_NUM:"",
EM_ALPHA:"",
}

ET_NONE = 0
ET_REL = 1
ET_EXEC = 2
ET_DYN = 3
ET_CORE = 4
ET_NUM = 5
ET_LOOS = 0xfe00
ET_HIOS = 0xfeff
ET_LOPROC = 0xff00
ET_HIPROC = 0xffff

e_types = {
ET_NONE:"No file type",
ET_REL:"Relocatable file",
ET_EXEC:"Executable file",
ET_DYN:"Shared object file",
ET_CORE:"Core file",
ET_NUM:"Number of defined types",
ET_LOOS:"OS-specific range start",
ET_HIOS:"OS-specific range end",
ET_LOPROC:"Processor-specific range start",
ET_HIPROC:"Processor-specific range end",
}

EV_NONE = 0
EV_CURRENT = 1
EV_NUM = 2

e_versions = {
EV_NONE:"Invalid ELF version",
EV_CURRENT:"Current version",
EV_NUM:"",
}
R_68K_NONE = 0
R_68K_32 = 1
R_68K_16 = 2
R_68K_8 = 3
R_68K_PC32 = 4
R_68K_PC16 = 5
R_68K_PC8 = 6
R_68K_GOT32 = 7
R_68K_GOT16 = 8
R_68K_GOT8 = 9
R_68K_GOT32O = 10
R_68K_GOT16O = 11
R_68K_GOT8O = 12
R_68K_PLT32 = 13
R_68K_PLT16 = 14
R_68K_PLT8 = 15
R_68K_PLT32O = 16
R_68K_PLT16O = 17
R_68K_PLT8O = 18
R_68K_COPY = 19
R_68K_GLOB_DAT = 20
R_68K_JMP_SLOT = 21
R_68K_RELATIVE = 22

e_flags_68k = {
R_68K_NONE:"No reloc",
R_68K_32:"Direct 32 bit",
R_68K_16:"Direct 16 bit",
R_68K_8:"Direct 8 bit",
R_68K_PC32:"PC relative 32 bit",
R_68K_PC16:"PC relative 16 bit",
R_68K_PC8:"PC relative 8 bit",
R_68K_GOT32:"32 bit PC relative GOT entry",
R_68K_GOT16:"16 bit PC relative GOT entry",
R_68K_GOT8:"8 bit PC relative GOT entry",
R_68K_GOT32O:"32 bit GOT offset",
R_68K_GOT16O:"16 bit GOT offset",
R_68K_GOT8O:"8 bit GOT offset",
R_68K_PLT32:"32 bit PC relative PLT address",
R_68K_PLT16:"16 bit PC relative PLT address",
R_68K_PLT8:"8 bit PC relative PLT address",
R_68K_PLT32O:"32 bit PLT offset",
R_68K_PLT16O:"16 bit PLT offset",
R_68K_PLT8O:"8 bit PLT offset",
R_68K_COPY:"Copy symbol at runtime",
R_68K_GLOB_DAT:"Create GOT entry",
R_68K_JMP_SLOT:"Create PLT entry",
R_68K_RELATIVE:"Adjust by program base",
}

R_386_NONE = 0
R_386_32 = 1
R_386_PC32 = 2
R_386_GOT32 = 3
R_386_PLT32 = 4
R_386_COPY = 5
R_386_GLOB_DAT = 6
R_386_JMP_SLOT = 7
R_386_RELATIVE = 8
R_386_GOTOFF = 9
R_386_GOTPC = 10
R_386_32PLT = 11
R_386_TLS_TPOFF = 14
R_386_TLS_IE = 15
R_386_TLS_GOTIE = 16
R_386_TLS_LE = 17
R_386_TLS_GD = 18
R_386_TLS_LDM = 19
R_386_16 = 20
R_386_PC16 = 21
R_386_8 = 22
R_386_PC8 = 23
R_386_TLS_GD_32 = 24
R_386_TLS_GD_PUSH = 25
R_386_TLS_GD_CALL = 26
R_386_TLS_GD_POP = 27
R_386_TLS_LDM_32 = 28
R_386_TLS_LDM_PUSH = 29
R_386_TLS_LDM_CALL = 30
R_386_TLS_LDM_POP = 31
R_386_TLS_LDO_32 = 32
R_386_TLS_IE_32 = 33
R_386_TLS_LE_32 = 34
R_386_TLS_DTPMOD32 = 35
R_386_TLS_DTPOFF32 = 36
R_386_TLS_TPOFF32 = 37

r_types_386 = {
R_386_NONE:"No reloc",
R_386_32:"Direct 32 bit",
R_386_PC32:"PC relative 32 bit",
R_386_GOT32:"32 bit GOT entry",
R_386_PLT32:"32 bit PLT address",
R_386_COPY:"Copy symbol at runtime",
R_386_GLOB_DAT:"Create GOT entry",
R_386_JMP_SLOT:"Create PLT entry",
R_386_RELATIVE:"Adjust by program base",
R_386_GOTOFF:"32 bit offset to GOT",
R_386_GOTPC:"32 bit PC relative offset to GOT",
R_386_32PLT:"",
R_386_TLS_TPOFF:"Offset in static TLS block",
R_386_TLS_IE:"Address of GOT entry for static",
R_386_TLS_GOTIE:"GOT entry for static TLS",
R_386_TLS_LE:"Offset relative to static",
R_386_TLS_GD:"Direct 32 bit for GNU version",
R_386_TLS_LDM:"Direct 32 bit for GNU version",
R_386_16:"",
R_386_PC16:"",
R_386_8:"",
R_386_PC8:"",
R_386_TLS_GD_32:"Direct 32 bit for general",
R_386_TLS_GD_PUSH:"Tag for pushl in GD TLS code",
R_386_TLS_GD_CALL:"Relocation for call",
R_386_TLS_GD_POP:"Tag for popl in GD TLS code",
R_386_TLS_LDM_32:"Direct 32 bit for local",
R_386_TLS_LDM_PUSH:"Tag for pushl in LDM TLS code",
R_386_TLS_LDM_CALL:"Relocation for call",
R_386_TLS_LDM_POP:"Tag for popl in LDM TLS code",
R_386_TLS_LDO_32:"Offset relative to TLS block",
R_386_TLS_IE_32:"GOT entry for negated static",
R_386_TLS_LE_32:"Negated offset relative to",
R_386_TLS_DTPMOD32:"ID of module containing symbol",
R_386_TLS_DTPOFF32:"Offset in TLS block",
R_386_TLS_TPOFF32:"Negated offset in static TLS block",
#R_386_NUM:"",
}

## Define e_flags to 386
r_types = r_types_386


SHT_NULL = 0
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_RELA = 4
SHT_HASH = 5
SHT_DYNAMIC = 6
SHT_NOTE = 7
SHT_NOBITS = 8
SHT_REL = 9
SHT_SHLIB = 10
SHT_DYNSYM = 11
SHT_INIT_ARRAY = 14
SHT_FINI_ARRAY = 15
SHT_PREINIT_ARRAY = 16
SHT_GROUP = 17
SHT_SYMTAB_SHNDX = 18
SHT_LOOS = 0x60000000
SHT_GNU_LIBLIST = 0x6ffffff7
SHT_CHECKSUM = 0x6ffffff8
SHT_LOSUNW = 0x6ffffffa
SHT_GNU_verdef = 0x6ffffffd
SHT_GNU_verneed = 0x6ffffffe
SHT_GNU_versym = 0x6fffffff
SHT_HISUNW = 0x6fffffff
SHT_HIOS = 0x6fffffff
SHT_LOPROC = 0x70000000
SHT_HIPROC = 0x7fffffff
SHT_LOUSER = 0x80000000
SHT_HIUSER = 0x8fffffff

sh_type = {
SHT_NULL:"Section header table entry unused",
SHT_PROGBITS:"Program data",
SHT_SYMTAB:"Symbol table",
SHT_STRTAB:"String table",
SHT_RELA:"Relocation entries with addends",
SHT_HASH:"Symbol hash table",
SHT_DYNAMIC:"Dynamic linking information",
SHT_NOTE:"Notes",
SHT_NOBITS:"Program space with no data (bss)",
SHT_REL:"Relocation entries, no addends",
SHT_SHLIB:"Reserved",
SHT_DYNSYM:"Dynamic linker symbol table",
SHT_INIT_ARRAY:"Array of constructors",
SHT_FINI_ARRAY:"Array of destructors",
SHT_PREINIT_ARRAY:"Array of pre-constructors",
SHT_GROUP:"Section group",
SHT_SYMTAB_SHNDX:"Extended section indeces",
SHT_LOOS:"Start OS-specific",
SHT_GNU_LIBLIST:"Prelink library list",
SHT_CHECKSUM:"Checksum for DSO content.",
SHT_LOSUNW:"Sun-specific low bound.",
SHT_GNU_verdef:"Version definition section.",
SHT_GNU_verneed:"Version needs section.",
SHT_GNU_versym:"Version symbol table.",
SHT_HISUNW:"Sun-specific high bound.",
SHT_HIOS:"End OS-specific type",
SHT_LOPROC:"Start of processor-specific",
SHT_HIPROC:"End of processor-specific",
SHT_LOUSER:"Start of application-specific",
SHT_HIUSER:"End of application-specific",
}

SHF_WRITE = 1
SHF_ALLOC = 2
SHF_EXECINSTR = 4
SHF_MERGE = 16
SHF_STRINGS = 32
SHF_INFO_LINK = 64
SHF_LINK_ORDER = 128
SHF_OS_NONCONFORMING = 256
SHF_GROUP = 512
SHF_TLS = 1024
SHF_ORDERED = 1073741824
SHF_EXCLUDE = 2147483648

sh_flags = {
SHF_WRITE:"Writable",
SHF_ALLOC:"Occupies memory during execution",
SHF_EXECINSTR:"Executable",
SHF_MERGE:"Might be merged",
SHF_STRINGS:"Contains nul-terminated strings",
SHF_INFO_LINK:"`sh_info' contains SHT index",
SHF_LINK_ORDER:"Preserve order after combining",
SHF_OS_NONCONFORMING:"Non-standard OS specific",
SHF_GROUP:"Section is member of a group.",
SHF_TLS:"Section hold thread-local data.",
SHF_ORDERED:"Special ordering",
SHF_EXCLUDE:"Section is excluded",
}

STB_LOCAL = 0
STB_GLOBAL = 1
STB_WEAK = 2
STB_LOOS = 10
STB_HIOS = 12
STB_LOPROC = 13
STB_HIPROC = 15

st_info_bind = {
STB_LOCAL:"Local symbol",
STB_GLOBAL:"Global symbol",
STB_WEAK:"Weak symbol",
STB_LOOS:"Start of OS-specific",
STB_HIOS:"End of OS-specific",
STB_LOPROC:"Start of processor-specific",
STB_HIPROC:"End of processor-specific",
}

STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC = 2
STT_SECTION = 3
STT_FILE = 4
STT_COMMON = 5
STT_TLS = 6
STT_LOOS = 10
STT_HIOS = 12
STT_LOPROC = 13
STT_HIPROC = 15

st_info_type = {
STT_NOTYPE:"Symbol type is unspecified",
STT_OBJECT:"Symbol is a data object",
STT_FUNC:"Symbol is a code object",
STT_SECTION:"Symbol associated with a section",
STT_FILE:"Symbol's name is file name",
STT_COMMON:"Symbol is a common data object",
STT_TLS:"Symbol is thread-local data",
STT_LOOS:"Start of OS-specific",
STT_HIOS:"End of OS-specific",
STT_LOPROC:"Start of processor-specific",
STT_HIPROC:"End of processor-specific",
}

DT_NULL     = 0
DT_NEEDED   = 1
DT_PLTRELSZ = 2
DT_PLTGOT   = 3
DT_HASH     = 4
DT_STRTAB   = 5
DT_SYMTAB   = 6
DT_RELA     = 7
DT_RELASZ   = 8
DT_RELAENT  = 9
DT_STRSZ    = 10
DT_SYMENT   = 11
DT_INIT     = 12
DT_FINI     = 13
DT_SONAME   = 14
DT_RPATH    = 15
DT_SYMBOLIC = 16
DT_REL      = 17
DT_RELSZ    = 18
DT_RELENT   = 19
DT_PLTREL   = 20
DT_DEBUG    = 21
DT_TEXTREL  = 22
DT_JMPREL   = 23
DT_BIND_NOW = 24
DT_INIT_ARRAY   = 25
DT_FINI_ARRAY   = 26
DT_INIT_ARRAYSZ = 27
DT_FINI_ARRAYSZ = 28
DT_RUNPATH  = 29
DT_FLAGS    = 30
DT_ENCODING = 32
DT_PREINIT_ARRAY = 32
DT_PREINIT_ARRAYSZ = 33
DT_NUM      = 34
DT_LOOS     = 0x6000000d
DT_HIOS     = 0x6ffff000
DT_LOPROC   = 0x70000000
DT_HIPROC   = 0x7fffffff
#DT_PROCNUM  = DT_MIPS_NUM

dt_types = {
DT_NULL     : "Marks end of dynamic section ",
DT_NEEDED   : "Name of needed library ",
DT_PLTRELSZ : "Size in bytes of PLT relocs ",
DT_PLTGOT   : "Processor defined value ",
DT_HASH     : "Address of symbol hash table ",
DT_STRTAB   : "Address of string table ",
DT_SYMTAB   : "Address of symbol table ",
DT_RELA     : "Address of Rela relocs ",
DT_RELASZ   : "Total size of Rela relocs ",
DT_RELAENT  : "Size of one Rela reloc ",
DT_STRSZ    : "Size of string table ",
DT_SYMENT   : "Size of one symbol table entry ",
DT_INIT     : "Address of init function ",
DT_FINI     : "Address of termination function ",
DT_SONAME   : "Name of shared object ",
DT_RPATH    : "Library search path (deprecated) ",
DT_SYMBOLIC : "Start symbol search here ",
DT_REL      : "Address of Rel relocs ",
DT_RELSZ    : "Total size of Rel relocs ",
DT_RELENT   : "Size of one Rel reloc ",
DT_PLTREL   : "Type of reloc in PLT ",
DT_DEBUG    : "For debugging; unspecified ",
DT_TEXTREL  : "Reloc might modify .text ",
DT_JMPREL   : "Address of PLT relocs ",
DT_BIND_NOW : "Process relocations of object ",
DT_INIT_ARRAY   : "Array with addresses of init fct ",
DT_FINI_ARRAY   : "Array with addresses of fini fct ",
DT_INIT_ARRAYSZ : "Size in bytes of DT_INIT_ARRAY ",
DT_FINI_ARRAYSZ : "Size in bytes of DT_FINI_ARRAY ",
DT_RUNPATH  : "Library search path ",
DT_FLAGS    : "Flags for the object being loaded ",
DT_ENCODING : "Start of encoded range ",
DT_PREINIT_ARRAY : "Array with addresses of preinit fct",
DT_PREINIT_ARRAYSZ : "size in bytes of DT_PREINIT_ARRAY ",
DT_NUM      : "Number used ",
DT_LOOS     : "Start of OS-specific ",
DT_HIOS     : "End of OS-specific ",
DT_LOPROC   : "Start of processor-specific ",
DT_HIPROC   : "End of processor-specific ",
#DT_PROCNUM  : "Most used by any processor ",
}


PT_NULL     = 0
PT_LOAD     = 1
PT_DYNAMIC  = 2
PT_INTERP   = 3
PT_NOTE     = 4
PT_SHLIB    = 5
PT_PHDR     = 6
PT_TLS      = 7
PT_NUM      = 8
PT_LOOS     = 0x60000000
PT_GNU_EH_FRAME  = 0x6474e550
PT_GNU_STACK  = 0x6474e551
PT_GNU_RELRO  = 0x6474e552
PT_LOSUNW   = 0x6ffffffa
PT_SUNWBSS  = 0x6ffffffa
PT_SUNWSTACK = 0x6ffffffb
PT_HISUNW =  0x6fffffff
PT_HIOS   =  0x6fffffff
PT_LOPROC =  0x70000000
PT_HIPROC =  0x7fffffff

ph_types = {
PT_NULL:"Program header table entry unused",
PT_LOAD:"Loadable program segment",
PT_DYNAMIC:"Dynamic linking information",
PT_INTERP:"Program interpreter",
PT_NOTE:"Auxiliary information",
PT_SHLIB:"Reserved",
PT_PHDR:"Entry for header table itself",
PT_TLS:"Thread-local storage segment",
PT_NUM:"Number of defined types",
PT_LOOS:"Start of OS-specific",
PT_GNU_EH_FRAME:"GCC .eh_frame_hdr segment",
PT_GNU_STACK:"Indicates stack executability",
PT_GNU_RELRO:"Read-only after relocation",
PT_SUNWBSS:"Sun Specific segment",
PT_SUNWSTACK:"Stack segment",
PT_HIOS:"End of OS-specific",
PT_LOPROC:"Start of processor-specific",
PT_HIPROC:"End of processor-specific"}

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/python

import better_exchook
better_exchook.install()

import sys	
import vtrace
vtrace.exc_handler = sys.excepthook
vtrace.interact(int(sys.argv[1]))


########NEW FILE########
__FILENAME__ = elf
"""
Elf structure definitions
"""

from vstruct import VStruct,VArray
from vstruct.primitives import *

class Elf32Symbol(VStruct):
    _fields_ =  [
        ("st_name", v_uint32),
        ("st_value", v_uint32),
        ("st_size", v_uint32),
        ("st_info", v_uint8),
        ("st_other", v_uint8),
        ("st_shndx", v_uint16)
    ]

class Elf32Reloc(VStruct):
    _fields_ = [
        ("r_offset", v_ptr),
        ("r_info", v_uint32),
    ]

    def getType(self):
        return int(self.r_info) & 0xff

    def getSymTabIndex(self):
        return int(self.r_info) >> 8

class Elf32Dynamic(VStruct):
    _fields_ = [
        ("d_tag", v_uint32),
        ("d_value", v_uint32),
    ]

class Elf64Symbol(VStruct):
    pass


########NEW FILE########
__FILENAME__ = pe
"""
Structures related to PE parsing.
"""

from vstruct.primitives import *
from vstruct import VStruct,VArray

USHORT = v_uint16
ULONG = v_uint32
UCHAR = v_uint8

class dos_reserved(VArray):
    _field_type_ = USHORT
    _field_count_ = 4

class dos_reserved2(VArray):
    _field_type_ = USHORT
    _field_count_ = 10

class IMAGE_DOS_HEADER(VStruct):
    _fields_ = (
        ("e_magic",USHORT),         # Magic number
        ("e_cblp",USHORT),          # Bytes on last page of file
        ("e_cp",USHORT),            # Pages in file
        ("e_crlc",USHORT),          # Relocations
        ("e_cparhdr",USHORT),       # Size of header in paragraphs
        ("e_minalloc",USHORT),      # Minimum extra paragraphs needed
        ("e_maxalloc",USHORT),      # Maximum extra paragraphs needed
        ("e_ss",USHORT),            # Initial (relative) SS value
        ("e_sp",USHORT),            # Initial SP value
        ("e_csum",USHORT),          # Checksum
        ("e_ip",USHORT),            # Initial IP value
        ("e_cs",USHORT),            # Initial (relative) CS value
        ("e_lfarlc",USHORT),        # File address of relocation table
        ("e_ovno",USHORT),          # Overlay number
        ("e_res",dos_reserved),        # Reserved words
        ("e_oemid",USHORT),         # OEM identifier (for e_oeminfo)
        ("e_oeminfo",USHORT),       # OEM information
        ("e_res2", dos_reserved2),  # Reserved words
        ("e_lfanew",ULONG),        # File address of new exe header
    )

class IMAGE_FILE_HEADER(VStruct):
    _fields_ = (
        ("Machine",USHORT),
        ("NumberOfSections", USHORT),
        ("TimeDateStamp", ULONG),
        ("PointerToSymbolTable", ULONG),
        ("NumberOfSymbols", ULONG),
        ("SizeOfOptionalHeader", USHORT),
        ("Ccharacteristics", USHORT),
    )

class IMAGE_DATA_DIRECTORY(VStruct):
    _fields_ = (("VirtualAddress", ULONG),("Size",ULONG))

class data_dir_array(VArray):
    _field_type_ = IMAGE_DATA_DIRECTORY
    _field_count_ = 16

class IMAGE_OPTIONAL_HEADER(VStruct):
    _fields_ = (
        ("Magic",USHORT),
        ("MajorLinkerVersion",UCHAR),
        ("MinorLinkerVersion",UCHAR),
        ("SizeOfCode", ULONG),
        ("SizeOfInitializedData", ULONG),
        ("SizeOfUninitializedData", ULONG),
        ("AddressOfEntryPoint", ULONG),
        ("BaseOfCode", ULONG),
        ("BaseOfData", ULONG),
        #FIXME from here down is the extended NT variant
        ("ImageBase", ULONG),
        ("SectionAlignment", ULONG),
        ("FileAlignment", ULONG),
        ("MajorOperatingSystemVersion", USHORT),
        ("MinorOperatingSystemVersion", USHORT),
        ("MajorImageVersion", USHORT),
        ("MinorImageVersion", USHORT),
        ("MajorSubsystemVersion", USHORT),
        ("MinorSubsystemVersion", USHORT),
        ("Win32VersionValue", ULONG),
        ("SizeOfImage", ULONG),
        ("SizeOfHeaders", ULONG),
        ("CheckSum", ULONG),
        ("Subsystem", USHORT),
        ("DllCharacteristics", USHORT),
        ("SizeOfStackReserve", ULONG),
        ("SizeOfStackCommit", ULONG),
        ("SizeOfHeapReserve", ULONG),
        ("SizeOfHeapCommit", ULONG),
        ("LoaderFlags", ULONG),
        ("NumberOfRvaAndSizes", ULONG),
        ("DataDirectory", data_dir_array),
    )

class IMAGE_NT_HEADERS(VStruct):
    _fields_ = (
        ("Signature", ULONG),
        ("FileHeader", IMAGE_FILE_HEADER),
        ("OptionalHeader", IMAGE_OPTIONAL_HEADER)
    )

class IMAGE_EXPORT_DIRECTORY(VStruct):
    _fields_ = (
        ("Characteristics", ULONG),
        ("TimeDateStamp", ULONG),
        ("MajorVersion", USHORT),
        ("MinorVersion", USHORT),
        ("Name", ULONG),
        ("Base", ULONG),
        ("NumberOfFunctions", ULONG),
        ("NumberOfNames", ULONG),
        ("AddressOfFunctions", ULONG),
        ("AddressOfNames", ULONG),
        ("AddressOfOrdinals", ULONG),
    )

class ImageName(v_base_t):
    _fmt_ = "8s"

class IMAGE_IMPORT_DIRECTORY(VStruct):
    _fields_ = (
        ("Characteristics", ULONG), # Also PIMAGE_THUNK_DATA union
        ("TimeDateStamp", ULONG),
        ("ForwarderChain", ULONG),
        ("Name", ULONG),
        ("FirstThunk", ULONG), # "pointer" is actually FIXME
    )

class IMAGE_THUNK_DATA(VStruct):
    _fields_ = ()

class IMAGE_SECTION_HEADER(VStruct):
    _fields_ = (
        ("Name", ImageName),
        ("VirtualSize", ULONG),
        ("VirtualAddress", ULONG),
        ("SizeOfRawData", ULONG),       # On disk size
        ("PointerToRawData", ULONG),    # On disk offset
        ("PointerToRelocations", ULONG),
        ("PointerToLineNumbers", ULONG),
        ("NumberOfRelocations", USHORT),
        ("NumberOfLineNumbers", USHORT),
        ("Characteristics", ULONG)
    )

class IMAGE_RESOURCE_DIRECTORY(VStruct):
    _fields_ = (
        ("Characteristics", ULONG),
        ("TimeDateStamp", ULONG),
        ("MajorVersion", USHORT),
        ("MinorVersion", USHORT),
        ("NumberOfNamedEntries", USHORT),
        ("NumberOfIdEntries", USHORT),
    )

########NEW FILE########
__FILENAME__ = primitives

class v_base_t(object):
    _fmt_ = ""

    def __init__(self, value=0):
        object.__init__(self)
        self.value = value

    def __repr__(self):
        return repr(self.value)

    def __int__(self):
        return int(self.value)

    def __long__(self):
        return long(self.value)

class v_int8(v_base_t):
    _fmt_ = "b"

class v_int16(v_base_t):
    _fmt_ = "h"

class v_int32(v_base_t):
    _fmt_ = "i"

class v_int64(v_base_t):
    _fmt_ = "q"

class v_uint8(v_base_t):
    _fmt_ = "B"

class v_uint16(v_base_t):
    _fmt_ = "H"

class v_uint32(v_base_t):
    _fmt_ = "I"

class v_uint64(v_base_t):
    _fmt_ = "Q"

class v_ptr(v_base_t):
    _fmt_ = "L"
    #FIXME this should be P with & 0xffffffffN
    def __repr__(self):
        return "0x%.8x" % self.value

class v_str(v_ptr):
    pass

class v_wstr(v_ptr):
    pass


########NEW FILE########
__FILENAME__ = win32

from vstruct.primitives import *
from vstruct import VStruct,VArray

DWORD = v_uint32

class NT_TIB(VStruct):
    _fields_ = [
        ("ExceptionList", v_ptr), # ExceptionRegistration structures.
        ("StackBase", v_ptr),
        ("StackLimit", v_ptr),
        ("SubSystemTib", v_ptr),
        ("FiberData", v_ptr),
        ("Version", v_ptr),
        ("ArbitraryUserPtr", v_ptr),
        ("Self", v_ptr)
    ]

class SEH3_SCOPETABLE(VStruct):
    _fields_ = [
        ("EnclosingLevel", v_int32),
        ("FilterFunction", v_ptr),
        ("HandlerFunction", v_ptr),
    ]

class SEH4_SCOPETABLE(VStruct):
    """
    Much like the SEH3 scopetable with the stack cookie additions
    """
    _fields_ = [
        ("GSCookieOffset", v_int32),
        ("GSCookieXOROffset", v_int32),
        ("EHCookieOffset", v_int32),
        ("EHCookieXOROffset", v_int32),
        ("EnclosingLevel", v_int32),
        ("FilterFunction", v_ptr),
        ("HandlerFunction", v_ptr),
    ]


class CLIENT_ID(VStruct):
    _fields_ = [
        ("UniqueProcess", v_ptr),
        ("UniqueThread", v_ptr)
    ]

class TebReserved32Array(VArray):
    _field_type_ = v_uint32
    _field_count_ = 26

class TebReservedArray(VArray):
    _field_type_ = v_uint32
    _field_count_ = 5

class TEB(VStruct):
    _fields_ = [
        ("TIB", NT_TIB),
        ("EnvironmentPointer", v_ptr),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", v_ptr),
        ("ThreadLocalStorage", v_ptr),
        ("ProcessEnvironmentBlock", v_ptr),
        ("LastErrorValue", v_uint32),
        ("CountOfOwnedCriticalSections", v_uint32),
        ("CsrClientThread", v_ptr),
        ("Win32ThreadInfo", v_ptr),
        ("User32Reserved", TebReserved32Array),
        ("UserReserved", TebReservedArray),
        ("WOW32Reserved", v_ptr),
        ("CurrentLocale", v_uint32),
        ("FpSoftwareStatusRegister", v_uint32)
        #FIXME not done!
    ]

# Some necissary arrays for the PEB
class TlsExpansionBitsArray(VArray):
    _field_type_ = v_uint32
    _field_count_ = 32
class GdiHandleBufferArray(VArray):
    _field_type_ = v_ptr
    _field_count_ = 34
class TlsBitMapArray(VArray):
    _field_type_ = v_uint32
    _field_count_ = 2

class PEB(VStruct):
    _fields_ = [
        ("InheritedAddressSpace", v_uint8),
        ("ReadImageFileExecOptions", v_uint8),
        ("BeingDebugged", v_uint8),
        ("SpareBool", v_uint8),
        ("Mutant", v_ptr),
        ("ImageBaseAddress", v_ptr),
        ("Ldr", v_ptr),
        ("ProcessParameters", v_ptr),
        ("SubSystemData", v_ptr),
        ("ProcessHeap", v_ptr),
        ("FastPebLock", v_ptr), 
        ("FastPebLockRoutine", v_ptr),
        ("FastPebUnlockRoutine", v_ptr),
        ("EnvironmentUpdateCount", v_uint32),
        ("KernelCallbackTable", v_ptr),
        ("SystemReserved", v_uint32),
        ("AtlThunkSListPtr32", v_ptr),
        ("FreeList", v_ptr),
        ("TlsExpansionCounter", v_uint32),
        ("TlsBitmap", v_ptr),
        ("TlsBitmapBits", TlsBitMapArray),
        ("ReadOnlySharedMemoryBase", v_ptr),
        ("ReadOnlySharedMemoryHeap", v_ptr),
        ("ReadOnlyStaticServerData", v_ptr),
        ("AnsiCodePageData", v_ptr),
        ("OemCodePageData", v_ptr),
        ("UnicodeCaseTableData", v_ptr),
        ("NumberOfProcessors", v_uint32),
        ("NtGlobalFlag", v_uint64),
        ("CriticalSectionTimeout",v_uint64),
        ("HeapSegmentReserve", v_uint32),
        ("HeapSegmentCommit", v_uint32),
        ("HeapDeCommitTotalFreeThreshold", v_uint32),
        ("HeapDeCommitFreeBlockThreshold", v_uint32), 
        ("NumberOfHeaps", v_uint32),
        ("MaximumNumberOfHeaps", v_uint32),
        ("ProcessHeaps", v_ptr),
        ("GdiSharedHandleTable", v_ptr),
        ("ProcessStarterHelper", v_ptr),
        ("GdiDCAttributeList", v_uint32),
        ("LoaderLock", v_ptr),
        ("OSMajorVersion", v_uint32),
        ("OSMinorVersion", v_uint32),
        ("OSBuildNumber", v_uint16),
        ("OSCSDVersion", v_uint16),
        ("OSPlatformId", v_uint32), 
        ("ImageSubsystem", v_uint32),
        ("ImageSubsystemMajorVersion", v_uint32),
        ("ImageSubsystemMinorVersion", v_uint32),
        ("ImageProcessAffinityMask", v_uint32),
        ("GdiHandleBuffer", GdiHandleBufferArray),
        ("PostProcessInitRoutine", v_ptr),
        ("TlsExpansionBitmap", v_ptr),
        ("TlsExpansionBitmapBits", TlsExpansionBitsArray),
        ("SessionId", v_uint32),
        ("AppCompatFlags", v_uint64),
        ("AppCompatFlagsUser", v_uint64),
        ("pShimData", v_ptr),
        ("AppCompatInfo", v_ptr),
        ("CSDVersion", v_ptr), # FIXME make wide char reader?
        ("UNKNOWN", v_uint32),
        ("ActivationContextData", v_ptr),
        ("ProcessAssemblyStorageMap", v_ptr),
        ("SystemDefaultActivationContextData", v_ptr),
        ("SystemAssemblyStorageMap", v_ptr),
        ("MinimumStackCommit", v_uint32),
    ]

class HEAP_ENTRY(VStruct):
    _fields_ = [
        ("Size", v_uint16),
        ("PrevSize", v_uint16),
        ("SegmentIndex", v_uint8),
        ("Flags", v_uint8),
        ("Unused", v_uint8),
        ("TagIndex", v_uint8)
    ]

class ListEntry(VStruct):
    _fields_ = [
        ("Flink", v_ptr),
        ("Blink", v_ptr)
    ]

class HeapSegmentArray(VArray):
    _field_type_ = v_uint32
    _field_count_ = 64
class HeapUnArray(VArray):
    _field_type_ = v_uint8
    _field_count_ = 16
class HeapUn2Array(VArray):
    _field_type_ = v_uint8
    _field_count_ = 2
class HeapFreeListArray(VArray):
    _field_type_ = ListEntry
    _field_count_ = 128

class HEAP(VStruct):
    _fields_ = [
        ("Entry", HEAP_ENTRY),
        ("Signature", v_uint32),
        ("Flags", v_uint32),
        ("ForceFlags", v_uint32),
        ("VirtualMemoryThreshold", v_uint32),
        ("SegmentReserve", v_uint32),
        ("SegmentCommit", v_uint32),
        ("DeCommitFreeBlockThreshold", v_uint32),
        ("DeCommitTotalFreeThreshold", v_uint32),
        ("TotalFreeSize", v_uint32),
        ("MaximumAllocationSize", v_uint32),
        ("ProcessHeapsListIndex", v_uint16),
        ("HeaderValidateLength", v_uint16),
        ("HeaderValidateCopy", v_ptr),
        ("NextAvailableTagIndex", v_uint16),
        ("MaximumTagIndex", v_uint16),
        ("TagEntries", v_ptr),
        ("UCRSegments", v_ptr),
        ("UnusedUnCommittedRanges", v_ptr),
        ("AlignRound", v_uint32),
        ("AlignMask", v_uint32),
        ("VirtualAllocBlocks", ListEntry),
        ("Segments", HeapSegmentArray),
        ("u", HeapUnArray),
        ("u2", HeapUn2Array),
        ("AllocatorBackTraceIndex",v_uint16),
        ("NonDedicatedListLength", v_uint32),
        ("LargeBlocksIndex", v_ptr),
        ("PseudoTagEntries", v_ptr),
        ("FreeLists", HeapFreeListArray),
        ("LockVariable", v_uint32),
        ("CommitRoutine", v_ptr),
        ("FrontEndHeap", v_ptr),
        ("FrontEndHeapLockCount", v_uint16),
        ("FrontEndHeapType", v_uint8),
        ("LastSegmentIndex", v_uint8)
    ]

class EXCEPTION_RECORD(VStruct):
    _fields_ = [
        ("ExceptionCode", DWORD),
        ("ExceptionFlags", DWORD),
        ("ExceptionRecord", v_ptr), # Pointer to the next
        ("ExceptionAddress", v_ptr),
        ("NumberParameters", DWORD),
        #("ExceptionInformation", DWORD[NumberParameters])
    ]

class EXCEPTION_REGISTRATION(VStruct):
    _fields_ = [
        ("prev", v_ptr),
        ("handler", v_ptr),
    ]


########NEW FILE########
__FILENAME__ = amd64
"""
Amd64 Support Module
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import struct

class Amd64Mixin:
    """
    Do what we need to for the lucious amd64
    """
    def getStackTrace(self):
        self.requireAttached()
        current = 0
        sanity = 1000
        frames = []
        rbp = self.getRegisterByName("rbp")
        rip = self.getRegisterByName("rip")
        frames.append((rip,rbp))

        while rbp != 0 and current < sanity:
            try:
                rbp,rip = self.readMemoryFormat(rbp, "=LL")
            except:
                break
            frames.append((rip,rbp))
            current += 1

        return frames

    def getBreakInstruction(self):
        return "\xcc"

    def archGetPcName(self):
        return "rip"

    def archGetSpName(self):
        return "rsp"


########NEW FILE########
__FILENAME__ = intel
"""
x86 Support Module
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import vtrace
import struct
import traceback
import types
import vtrace.breakpoints as breakpoints

class IntelMixin:
    def archAddWatchpoint(self, address):
        regs = self.getRegisters()
        if not regs.has_key("debug7"):
            raise Exception("ERROR: Intel debug status register not found!")
        status = regs["debug7"]
        for i in range(4):
            if regs["debug%d" % i] != 0:
                continue

            regs["debug%d" % i] = address

            status |= 1 << (2*i)
            mask = 3 # FIXME 3 for read/write
            status |= (mask << (16+(4*i)))

            print "ADDING 0x%.8x at index %d status 0x%.8x" % (address,i,status)

            regs["debug7"] = status
            self.setRegisters(regs)
            return
            
        raise Exception("ERROR: there...  are... 4... debug registers!")

    def archRemWatchpoint(self, address):
        regs = self.getRegisters()
        if not regs.has_key("debug7"):
            raise Exception("ERROR: Intel debug status register not found!")
        status = regs["debug7"]
        for i in range(4):
            if regs["debug%d"] == address:
                status &= ~(1 << 2*i)
                # Always use 3 to mask off both bits...
                status &= ~(3 << 16+(4*i))

                regs["debug%d" % i] = 0
                regs["debug7"] = status

                self.setRegisters(regs)
                return

    def archCheckWatchpoints(self):
        regs = self.getRegisters()
        if not regs.has_key("debug7"):
            return False
        debug6 = regs["debug6"]
        x = debug6 & 0x0f
        if not x:
            return False
        regs["debug6"] = debug6 & ~(0x0f)
        self.setRegisters(regs)
        for i in range(4):
            if x >> i == 1:
                return regs["debug%d" % i]

    def setEflagsTf(self, enabled=True):
        """
        A convenience function to flip the TF flag in the eflags
        register
        """
        eflags = self.getRegisterByName("eflags")
        if enabled:
            eflags |= 0x100 # TF flag
        else:
            eflags &= ~0x100 # TF flag
        self.setRegisterByName("eflags",eflags)

    def getStackTrace(self):
        self.requireAttached()
        current = 0
        sanity = 1000
        frames = []
        ebp = self.getRegisterByName("ebp")
        eip = self.getRegisterByName("eip")
        frames.append((eip,ebp))

        while ebp != 0 and current < sanity:
            try:
                buf = self.readMemory(ebp, 8)
                ebp,eip = struct.unpack("<LL",buf)
                frames.append((eip,ebp))
                current += 1
            except:
                break

        return frames

    def getBreakInstruction(self):
        return "\xcc"

    def archGetPcName(self):
        return "eip"

    def archGetSpName(self):
        return "esp"

    def platformCall(self, address, args, convention=None):
        buf = ""
        finalargs = []
        saved_regs = self.getRegisters()
        sp = self.getStackCounter()
        pc = self.getProgramCounter()

        for arg in args:
            if type(arg) == types.StringType: # Nicly map strings into mem
                buf = arg+"\x00\x00"+buf    # Pad with a null for convenience
                finalargs.append(sp - len(buf))
            else:
                finalargs.append(arg)

        m = len(buf) % 4
        if m:
            buf = ("\x00" * (4-m)) + buf

        # Args are 
        #finalargs.reverse()
        buf = struct.pack("<%dL" % len(finalargs), *finalargs) + buf

        # Saved EIP is target addr so when we hit the break...
        buf = struct.pack("<L", address) + buf
        # Calc the new stack pointer
        newsp = sp-len(buf)
        # Write the stack buffer in
        self.writeMemory(newsp, buf)
        # Setup the stack pointer
        self.setStackCounter(newsp)
        # Setup the instruction pointer
        self.setProgramCounter(address)
        # Add the magical call-break
        callbreak = breakpoints.CallBreak(address, saved_regs)
        self.addBreakpoint(callbreak)
        # Continue until the CallBreak has been hit
        while not callbreak.endregs:
            self.run()
        return callbreak.endregs


########NEW FILE########
__FILENAME__ = ppc
"""
PPC Support Module (not done)
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
class PpcMixin:
    def archAddWatchpoint(self, address):
        pass

    def archRemWatchpoint(self, address):
        pass

    def archCheckWatchpoint(self, address):
        pass

    def getStackTrace(self):
        self.requireAttached()
        return []

    def getBreakInstruction(self):
        # twi 0x14, r0, 0 
        # trap if r0 is (>=:unsigned) 0
        return "\x0e\x80\x00\x00"

    def archGetPcName(self):
        return "r0"

    def archGetSpName(self):
        return "r1"

    def platformCall(self, address, args, convention=None):
        pass

########NEW FILE########
__FILENAME__ = audit
"""
Test for platform functionality (for internal use).
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import vtrace
import vtrace.platforms.base as v_base

############################################
#
# FIXME this is dorked for now based on the new platforms/archs design
#
############################################

def auditTracer(trace):
    """
    Print out a list of platform requirements and weather
    a particular tracer meets them.  This is mostly a
    development tool to determin what's left to do on a 
    tracer implementation.
    """
    for mname in dir(v_base.BasePlatformMixin):
        if "__" in mname:
            continue
        if getattr(trace.__class__, mname) == getattr(v_base.BasePlatformMixin, mname):
            print "LACKS:",mname
        else:
            print "HAS:",mname

if __name__ == "__main__":
    trace = vtrace.getTrace()
    auditTracer(trace)

########NEW FILE########
__FILENAME__ = breakpoints

"""
Breakpoint Objects
"""

# Copyright (C) 2007 Invisigoth - See LICENSE file for details

import time

import vtrace

class Breakpoint:
    """
    Breakpoints in Vtrace are platform independant objects that
    use the underlying trace objects to get things like the
    program counter and the break instruction.  As long as
    platfforms are completely implemented, all breakpoint
    objects should be portable.


    """
    def __init__(self, address, enabled=True, expression=None):
        self.saved = None
        self.address = address
        self.enabled = enabled
        self.active = False
        self.id = -1
        self.vte = None
        self.bpcode = None
        self.bpcodeobj = None
        if expression:
            self.vte = vtrace.VtraceExpression(expression)

    def getAddress(self):
        """
        This will return the address for this breakpoint.  If the return'd
        address is None, this is a deferred breakpoint which needs to have
        resolveAddress() called to attempt to set the address.
        """
        return self.address

    def getId(self):
        return self.id

    def getName(self):
        if self.vte:
            return str(self.vte)
        return "0x%.8x" % self.address

    def __repr__(self):
        return "[%d] %s: %s" % (self.id, self.__class__.__name__, self.getName())

    def activate(self, trace):
        """
        Actually store off and replace memory for this process.  This
        is caried out by the trace object itself when it begins
        running or stops.  You probably never need to call this
        (see isEnabled() setEnabled() for boolean enable/disablle)
        """
        trace.requireAttached()
        if not self.active:
            if self.address != None:
                breakinst = trace.getBreakInstruction()
                self.saved = trace.readMemory(self.address, len(breakinst))
                trace.writeMemory(self.address, breakinst)
                self.active = True
        return self.active

    def deactivate(self, trace):
        """
        Repair the process for continued execution.  this does NOT
        make a breakpoint *inactive*, but removes it's "0xcc" from mem
        (see isEnabled() setEnabled() for boolean enable/dissable)
        """
        trace.requireAttached()
        if self.active:
            self.active = False
            trace.writeMemory(self.address, self.saved)
        return self.active

    def resolveAddress(self, trace):
        """
        Try to resolve the address for this break.  If this is a statically
        addressed break, just return the address.  If it has an "expression"
        use that to resolve the address...
        """
        if self.address == None and self.vte:
            self.address = self.vte.evaluate(trace,noraise=True)
        return self.address

    def isEnabled(self):
        """
        Is this breakpoint "enabled"?
        """
        return self.enabled

    def setEnabled(self, enabled=True):
        """
        Set this breakpoints "enabled" status
        """
        self.enabled = enabled

    def setBreakpointCode(self, pystr):
        """
        Use this method to set custom python code to run when this
        breakpoint gets hit.  The code will have the following objects
        mapped into it's namespace when run:
            trace - the tracer
            vtrace - the vtrace module
            bp - the breakpoint
        """
        self.bpcodeobj = None
        self.bpcode = pystr

    def getBreakpointCode(self):
        """
        Return the current python string that will be run when this break is hit.
        """
        return self.bpcode

    def notify(self, event, trace):
        """
        Breakpoints may also extend and implement "notify" which will be
        called whenever they are hit.  If you want to continue the ability
        for this breakpoint to have bpcode, you must call this method from
        your override.
        """
        if self.bpcode != None:
            if self.bpcodeobj == None:
                fname = "BP:%d (0x%.8x)" % (self.id, self.address)
                self.bpcodeobj = compile(self.bpcode, fname, "exec")

            d = {"vtrace":vtrace,"trace":trace,"bp":self}
            exec(self.bpcodeobj, d, d)

class TrackerBreak(Breakpoint):
    """
    A breakpoint which will record how many times it was hit
    (by the address it was at) as metadata for the tracer.
    """
    def notify(self, event, trace):
        tb = trace.getMeta("TrackerBreak", None)
        if tb == None:
            tb = {}
        trace.setMeta("TrackerBreak", tb)
        tb[self.address] = (tb.get(self.address,0) + 1)
        Breakpoint.notify(self, event, trace)

class OneTimeBreak(Breakpoint):
    """
    This type of breakpoint is exclusivly for marking
    and code-coverage stuff.  It removes itself.
    (most frequently used with a continued trace)
    """
    def notify(self, event, trace):
        trace.removeBreakpoint(self.id)
        Breakpoint.notify(self, event, trace)

class StopRunForeverBreak(Breakpoint):
    """
    This breakpoint will turn off RunForever mode
    on the tracer object when hit.  it's a good way
    to let things run on and on processing exceptions
    but stop when you get to this one thing.
    """
    def notify(self, event, trace):
        trace.setMode("RunForever", False)
        Breakpoint.notify(self, event, trace)

class StopAndRemoveBreak(Breakpoint):
    """
    When hit, take the tracer out of run-forever mode and
    remove this breakpoint.
    """
    def notify(self, event, trace):
        trace.setMode("RunForever", False)
        trace.removeBreakpoint(self.id)
        Breakpoint.notify(self, event, trace)

class CallBreak(Breakpoint):
    """
    A special breakpoint which will restore process
    state (registers in particular) when it gets hit.
    This is primarily used by the call method inside
    the trace object to restore original state
    after a successful "call" method call.

    Additionally, the endregs dict will be filled in
    with the regs at the time it was hit and kept until
    we get garbage collected...
    """
    def __init__(self, address, saved_regs):
        Breakpoint.__init__(self, address, True)
        self.endregs = None # Filled in when we get hit
        self.saved_regs = saved_regs
        self.onehitwonder = True

    def notify(self, event, trace):
        if self.onehitwonder:
            self.onehitwonder = False
            return
        self.endregs = trace.getRegisters()
        trace.removeBreakpoint(self.id)
        trace.setRegisters(self.saved_regs)
        trace.setMeta("PendingSignal", 0)

class SnapshotBreak(Breakpoint):
    """
    A special breakpoint type which will produce vtrace snapshots
    for the target process when hit.  The snapshots will be saved
    to a default name of <exename>-<timestamp>.vsnap.  This is not
    recommended for use in heavily hit breakpoints as taking a
    snapshot is processor intensive.
    """
    def notify(self, event, trace):
        exe = trace.getExe()
        snap = trace.takeSnapshot()
        snap.saveToFile("%s-%d.vsnap" % (exe,time.time()))
        Breakpoint.notify(self, event, trace)


########NEW FILE########
__FILENAME__ = envitools

"""
Some tools that require the envi framework to be installed
"""

import sys
import traceback

import envi
import envi.intel as e_intel # FIXME This should NOT have to be here

class RegisterException(Exception):
    pass

def cmpRegs(emu, trace):
    for idx,name in reg_map:
        er = emu.getRegister(idx)
        tr = trace.getRegisterByName(name)
        if er != tr:
            raise RegisterException("REGISTER MISMATCH: %s 0x%.8x 0x%.8x" % (name, tr, er))
    return True

reg_map = [
    (e_intel.REG_EAX, "eax"),
    (e_intel.REG_ECX, "ecx"),
    (e_intel.REG_EDX, "edx"),
    (e_intel.REG_EBX, "ebx"),
    (e_intel.REG_ESP, "esp"),
    (e_intel.REG_EBP, "ebp"),
    (e_intel.REG_ESI, "esi"),
    (e_intel.REG_EDI, "edi"),
    (e_intel.REG_EIP, "eip"),
    (e_intel.REG_FLAGS, "eflags")
    ]

#FIXME intel specific
def setRegs(emu, trace):
    for idx,name in reg_map:
        tr = trace.getRegisterByName(name)
        emu.setRegister(idx, tr)

def emulatorFromTraceSnapshot(tsnap):
    """
    Produce an envi emulator for this tracer object.  Use the trace's arch
    info to get the emulator so this can be done on the client side of a remote
    vtrace session.
    """
    arch = tsnap.getMeta("Architecture")
    amod = envi.getArchModule(arch)
    emu = amod.getEmulator()

    if tsnap.getMeta("Platform") == "Windows":
        emu.setSegmentInfo(e_intel.SEG_FS, tsnap.getThreads()[tsnap.getMeta("ThreadId")], 0xffffffff)

    emu.setMemoryObject(tsnap)
    setRegs(emu, tsnap)
    return emu

def lockStepEmulator(emu, trace):
    while True:
        print "Lockstep: 0x%.8x" % emu.getProgramCounter()
        try:
            pc = emu.getProgramCounter()
            op = emu.makeOpcode(pc)
            trace.stepi()
            emu.stepi()
            cmpRegs(emu, trace)
        except RegisterException, msg:
            print "Lockstep Error: %s: %s" % (repr(op),msg)
            setRegs(emu, trace)
            sys.stdin.readline()
        except Exception, msg:
            traceback.print_exc()
            print "Lockstep Error: %s" % msg
            return

def main():
    import vtrace
    sym = sys.argv[1]
    pid = int(sys.argv[2])
    t = vtrace.getTrace()
    t.attach(pid)
    symaddr = t.parseExpression(sym)
    t.addBreakpoint(vtrace.Breakpoint(symaddr))
    while t.getProgramCounter() != symaddr:
        t.run()
    snap = t.takeSnapshot()
    #snap.saveToFile("woot.snap") # You may open in vdb to follow along
    emu = emulatorFromTraceSnapshot(snap)
    lockStepEmulator(emu, t)

if __name__ == "__main__":
    # Copy this file out to the vtrace dir for testing and run as main
    main()


########NEW FILE########
__FILENAME__ = notifiers
"""
Vtrace notitifers base classes and examples

Vtrace supports the idea of callback notifiers which
get called whenever particular events occur in the target
process.  Notifiers may be registered to recieve a callback
on any of the vtrace.NOTIFY_FOO events from vtrace.  One notifier
*may* be registered with more than one trace, as the "notify"
method is passed a reference to the trace for which an event
has occured...

"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details

import vtrace
import traceback

class Notifier(object):
    """
    The top level example notifier...  Anything which registers
    itself for trace events or tracegroup events should implement
    the notify method as shown here.
    """

    def __init__(self):
        """
        All extenders *must* call this.  Mostly because all the
        goop necissary for the remote debugging stuff...
        (if notifier is instantiated on server, all is well, if it's
        on the client it needs a proxy...)
        """
        pass

    def handleEvent(self, event, trace):
        """
        An "internal" handler so if we need to do something
        from an API perspective before calling the notify method
        we can have a good "all at once" hook
        """
        self.notify(event, trace)

    def notify(self, event, trace):
        print "Got event: %d from pid %d" % (event, trace.getPid())

class VerboseNotifier(Notifier):
    def notify(self, event, trace):
        print "PID %d thread(%d) got" % (trace.getPid(), trace.getMeta("ThreadId")),
        if event == vtrace.NOTIFY_ALL:
            print "WTF, how did we get a vtrace.NOTIFY_ALL event?!?!"
        elif event == vtrace.NOTIFY_SIGNAL:
            print "vtrace.NOTIFY_SIGNAL"
            print "PendingSignal",trace.getMeta("PendingSignal")
            print "PendingException",trace.getMeta("PendingException")
            if trace.getMeta("Platform") == "Windows":
                print repr(trace.getMeta("Win32Event"))
        elif event == vtrace.NOTIFY_BREAK:
            print "vtrace.NOTIFY_BREAK"
        elif event == vtrace.NOTIFY_SYSCALL:
            print "vtrace.NOTIFY_SYSCALL"
        elif event == vtrace.NOTIFY_CONTINUE:
            print "vtrace.NOTIFY_CONTINUE"
        elif event == vtrace.NOTIFY_EXIT:
            print "vtrace.NOTIFY_EXIT"
            print "ExitCode",trace.getMeta("ExitCode")
        elif event == vtrace.NOTIFY_ATTACH:
            print "vtrace.NOTIFY_ATTACH"
        elif event == vtrace.NOTIFY_DETACH:
            print "vtrace.NOTIFY_DETACH"
        elif event == vtrace.NOTIFY_LOAD_LIBRARY:
            print "vtrace.NOTIFY_LOAD_LIBRARY"
        elif event == vtrace.NOTIFY_UNLOAD_LIBRARY:
            print "vtrace.NOTIFY_UNLOAD_LIBRARY"
        elif event == vtrace.NOTIFY_CREATE_THREAD:
            print "vtrace.NOTIFY_CREATE_THREAD"
        elif event == vtrace.NOTIFY_EXIT_THREAD:
            print "vtrace.NOTIFY_EXIT_THREAD"
            print "ExitThread",trace.getMeta("ExitThread", -1)
        elif event == vtrace.NOTIFY_STEP:
            print "vtrace.NOTIFY_STEP"
        else:
            print "vtrace.NOTIFY_WTF_HUH?"

class DistributedNotifier(Notifier):
    """
    A notifier which will distributed notifications out to
    locally registered notifiers so that remote tracer's notifier
    callbacks only require once across the wire.
    """
    # NOTE: once you turn on vtrace.NOTIFY_ALL it can't be turned back off yet.
    def __init__(self):
        Notifier.__init__(self)
        self.shared = False
        self.events = []
        self.notifiers = {}
        for i in range(vtrace.NOTIFY_MAX):
            self.notifiers[i] = []

    def getProxy(self, trace):
        host,nothing = cobra.getCobraSocket(trace).getLocalName()

    def notify(self, event, trace):
        self.fireNotifiers(event, trace)

    def fireNotifiers(self, event, trace):
        """
        Fire all our registerd local-notifiers
        """
        nlist = self.notifiers.get(vtrace.NOTIFY_ALL, [])
        for notifier in nlist:
            try:
                notifier.handleEvent(event, trace)
            except:
                print "ERROR - Exception in notifier:",traceback.format_exc()

        nlist = self.notifiers.get(event, [])
        for notifier in nlist:
            try:
                notifier.handleEvent(event, trace)
            except:
                print "ERROR - Exception in notifier:",traceback.format_exc()

    def registerNotifier(self, event, notif):
        """
        Register a sub-notifier to get the remote callback's via
        our local delivery.
        """
        nlist = self.notifiers.get(event)
        nlist.append(notif)

    def deregisterNotifier(self, event, notif):
        nlist = self.notifiers.get(event)
        nlist.remove(notif)


########NEW FILE########
__FILENAME__ = base
"""
Tracer Platform Base
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import os
import struct
import vtrace
import traceback
import inspect
import platform
from Queue import Queue
from threading import Thread,currentThread,Lock
import traceback

class BasePlatformMixin:
    """
    Mixin for all the platformDoFoo functions that throws an
    exception so you know your platform doesn't implement it.
    """

    def platformGetThreads(self):
        """
        Return a dictionary of <threadid>:<tinfo> pairs where tinfo is either
        the stack top, or the teb for win32
        """
        raise Exception("Platform must implement platformGetThreads()")

    def platformSelectThread(self, thrid):
        """
        Platform implementers are encouraged to use the metadata field "ThreadId"
        as the identifier (int) for which thread has "focus".  Additionally, the
        field "StoppedThreadId" should be used in instances (like win32) where you
        must specify the ORIGINALLY STOPPED thread-id in the continue.
        """
        self.setMeta("ThreadId",thrid)

    def platformKill(self):
        raise Exception("Platform must implement platformKill()")

    def platformExec(self, cmdline):
        """
        Platform exec will execute the process specified in cmdline
        and return the PID
        """
        raise Exception("Platmform must implement platformExec")

    def platformInjectSo(self, filename):
        raise Exception("Platform must implement injectso()")

    def platformGetFds(self):
        """
        Return what getFds() wants for this particular platform
        """
        raise Exception("Platform must implement platformGetFds()")

    def platformGetMaps(self):
        """
        Return a list of the memory maps where each element has
        the following structure:
        (address, length, perms, file="")
        NOTE: By Default this list is available as Trace.maps
        because the default implementation attempts to populate
        them on every break/stop/etc...
        """
        raise Exception("Platform must implement GetMaps")

    def platformPs(self):
        """
        Actually return a list of tuples in the format
        (pid, name) for this platform
        """
        raise Exception("Platform must implement Ps")

    def getBreakInstruction(self):
        """
        Give me the bytes for the "break" instruction
        for this architecture.
        """
        raise Exception("Architecture module must implement getBreakInstruction")

    def archAddWatchpoint(self, address):
        """
        Add a watchpoint for the given address.  Raise if the platform
        doesn't support, or too many are active...
        """
        raise Exception("Architecture doesn't implement watchpoints!")

    def archRemWatchpoint(self, address):
        raise Exception("Architecture doesn't implement watchpoints!")

    def archCheckWatchpoints(self):
        """
        If the current register state indicates that a watchpoint was hit, 
        return the address of the watchpoint and clear the event.  Otherwise
        return None
        """
        pass

    def archGetSpName(self):
        """
        Return the name of the stack pointer for this architecture
        """
        raise Exception("Architecture module must implement archGetSpName")

    def archGetPcName(self):
        """
        Return the name from the name of the register which represents
        the program counter for this architecture (ie. "eip" for intel)
        """
        raise Exception("Architecture module must implement archGetPcName")

    def getStackTrace(self):
        """
        Return a list of the stack frames for this process
        (currently Intel/ebp based only).  Each element of the
        "frames list" consists of another list which is (eip,ebp)
        """
        raise Exception("Platform must implement getStackTrace()")

    def getRegisterFormat(self):
        """
        Return a struct.unpack() style format string for
        parsing the bytes given back from PT_GETREGS so
        we can parse it into an array.
        """
        raise Exception("Platform must implement getRegisterFormat")

    def getRegisterNames(self):
        """
        Return a list of the register names which correspods
        (in order) with the format string specified for
        getRegisterFormat()
        """
        raise Exception("Platform must implement getRegisterNames")

    def getExe(self):
        """
        Get the full path to the main executable for this
        *attached* Trace
        """
        return self.getMeta("ExeName","Unknown")

    def platformAttach(self, pid):
        """
        Actually carry out attaching to a target process.  Like
        platformStepi this is expected to be ATOMIC and not return
        until a complete attach.
        """
        raise Exception("Platform must implement platformAttach()")

    def platformContinue(self):
        raise Exception("Platform must implement platformContinue()")

    def platformDetach(self):
        """
        Actually perform the detach for this type
        """
        raise Exception("Platform must implement platformDetach()")

    def platformStepi(self):
        """
        PlatformStepi should be ATOMIC, meaning it gets called, and
        by the time it returns, you're one step further.  This is completely
        regardless of blocking/nonblocking/whatever.
        """
        raise Exception("Platform must implement platformStepi!")

    def platformCall(self, address, args, convention=None):
        """
        Platform call takes an address, and an array of args
        (string types will be mapped and located for you)

        platformCall is expected to return a dicionary of the
        current register values at the point where the call
        has returned...
        """
        raise Exception("Platform must implement platformCall")

    def platformGetRegs(self):
        raise Exception("Platform must implement platformGetRegs!")

    def platformSetRegs(self, bytes):
        raise Exception("Platform must implement platformSetRegs!")

    def platformAllocateMemory(self, size, perms=vtrace.MM_RWX, suggestaddr=0):
        raise Exception("Plaform does not implement allocate memory")
        
    def platformReadMemory(self, address, size):
        raise Exception("Platform must implement platformReadMemory!")
        
    def platformWriteMemory(self, address, bytes):
        raise Exception("Platform must implement platformWriteMemory!")

    def platformWait(self):
        """
        Wait for something interesting to occur and return a
        *platform specific* representation of what happened.

        This will then be passed to the platformProcessEvent()
        method which will be responsible for doing things like
        firing notifiers.  Because the platformWait() method needs
        to be commonly ThreadWrapped and you can't fire notifiers
        from within a threadwrapped function...
        """
        raise Exception("Platform must implement platformWait!")

    def platformProcessEvent(self, event):
        """
        This method processes the event data provided by platformWait()

        This method is responsible for firing ALL notifiers *except*:

        vtrace.NOTIFY_CONTINUE - This is handled by the run api (and isn't the result of an event)
        """
        raise Exception("Platform must implement platformProcessEvent")

    def platformGetSymbolResolver(self, libname, address):
        """
        Platforms must return a class which inherits from the VSymbolResolver
        from vtrace.symbase.
        """
        raise Exception("Platform must implement platformGetSymbolResolver")

class TracerMethodProxy:
    def __init__(self, proxymeth, thread):
        self.thread = thread
        self.proxymeth = proxymeth

    def __call__(self, *args, **kwargs):
        if currentThread().__class__ == TracerThread:
            return self.proxymeth(*args, **kwargs)

        queue = Queue()
        self.thread.queue.put((self.proxymeth, args, kwargs, queue))
        ret = queue.get()

        if issubclass(ret.__class__, Exception):
            raise ret
        return ret

    def __repr__(self):
        return "<TracerMethodProxy of %s in %s>" % (self.proxymeth, self.thread)

class TracerThread(Thread):
    """
    Ok... so here's the catch... most debug APIs do *not* allow
    one thread to do the attach and another to do continue and another
    to do wait... they just dont.  So there.  I have to make a thread
    per-tracer (on most platforms) and proxy requests (for *some* trace
    API methods) to it for actual execution.  SUCK!

    However, this lets async things like GUIs and threaded things like
    cobra not have to be aware of which one is allowed and not allowed
    to make particular calls and on what platforms...  YAY!
    """
    def __init__(self):
        Thread.__init__(self)
        self.queue = Queue()
        self.setDaemon(True)
        self.go = True
        self.start()

    def run(self):
        """
        Run in a circle getting requests from our queue and
        executing them based on the thread.
        """
        while self.go:
            try:
                meth, args, kwargs, queue = self.queue.get()
                try:
                    queue.put(meth(*args, **kwargs))
                except Exception,e:
                    queue.put(e)
                    if vtrace.verbose:
                        traceback.print_exc()
                    # this deadlocks ?!
                    #if vtrace.exc_handler:
                    #    vtrace.exc_handler(*sys.exc_info())
                    continue
            except:
                if vtrace.verbose:
                    traceback.print_exc()


class UtilMixin:
    """
    This is all the essentially internal methods that platform implementors
    may use and the guts use directly.
    """

    def _initLocals(self):
        """
        The routine to initialize a tracer's initial internal state.  This
        is used by the initial creation routines, AND on attaches/executes
        to re-fresh the state of the tracer.
        WARNING: This will erase all metadata/symbols (modes/notifiers are kept)
        """
        self.pid = 0 # Attached pid (also used to know if attached)
        self.exited = False
        self.breakpoints = {}
        self.watchpoints = {}
        self.bpid = 0
        self.bplock = Lock()
        self.deferredwatch = []
        self.deferred = []
        self.running = False
        self.attached = False
        # A cache for memory maps and fd listings
        self.mapcache = None
        self.threadcache = None
        self.fds = None
        self.signal_ignores = []

        # For all transient data (if notifiers want
        # to track stuff per-trace
        self.metadata = {}

        # Set up some globally expected metadata
        self.setMeta("PendingSignal", 0)
        self.setMeta("IgnoredSignals",[])
        self.setMeta("AutoContinue", False)
        self.setMeta("LibraryBases", {}) # name -> base address mappings for binaries
        self.setMeta("ThreadId", -1) # If you *can* have a thread id put it here
        arch = platform.machine()
        plat = platform.system()
        rel  = platform.release()
        #FIXME windows hack...
        if plat == "Windows" and arch == '':
            arch = "i386"
        self.setMeta("Architecture", arch)
        self.setMeta("Platform", plat)
        self.setMeta("Release", rel)

        # Use this if we are *expecting* a break
        # which is caused by us (so we remove the
        # SIGBREAK from pending_signal
        self.setMeta("ShouldBreak", False)

        self.resbynorm = {} # VSymbolResolvers, indexed by "normalized" libname
        self.resbyfile = {} # VSymbolResolvers indexed by file basename
        self.resbyaddr = [] # VSymbolResolver order'd by load base, decending...

    def nextBpId(self):
        self.bplock.acquire()
        x = self.bpid
        self.bpid += 1
        self.bplock.release()
        return x

    def unpackRegisters(self, regbuf):
        regs = {}
        siz = struct.calcsize(self.fmt)
        reglist = struct.unpack(self.fmt, regbuf[:siz])
        for i in range(len(reglist)):
            regs[self.regnames[i]] = reglist[i]
        return regs

    def packRegisters(self, regdict):
        p = []
        for n in self.regnames:
            p.append(regdict.get(n))
        return struct.pack(self.fmt, *p)

    def justAttached(self, pid):
        """
        platformAttach() function should call this
        immediately after a successful attach.  This does
        any necessary initialization for a tracer to be
        back in a clean state.
        """
        self.pid = pid
        self.attached = True
        self.breakpoints = {}
        self.setMeta("PendingSignal", 0)
        self.setMeta("PendingException", None)
        self.setMeta("ExitCode", 0)
        self.exited = False

    def getResolverForFile(self, filename):
        res = self.resbynorm.get(filename, None)
        if res: return res
        res = self.resbyfile.get(filename, None)
        if res: return res
        return None

    def steploop(self):
        """
        Continue stepi'ing in a loop until shouldRunAgain()
        returns false (like RunForever mode or something)
        """
        if self.getMode("NonBlocking", False):
            thr = Thread(target=self.doStepLoop, args=(until,))
            thr.setDaemon(True)
            thr.start()
        else:
            self.doStepLoop(until)

    def doStepLoop(self):
        go = True
        while go:
            self.stepi()
            go = self.shouldRunAgain()

    def _doRun(self):
        # Exists to avoid recursion from loop in doWait
        self.requireAttached()
        self.requireNotRunning()
        self.requireNotExited()

        self.fireNotifiers(vtrace.NOTIFY_CONTINUE)

        # Step past a breakpoint if we are on one.
        self._checkForBreak()
        # Throw down and activate breakpoints...
        self._throwdownBreaks()

        self.running = True
        # Syncregs must happen *after* notifiers for CONTINUE
        # and checkForBreak.
        self.syncRegs()
        self.platformContinue()
        self.setMeta("PendingSignal", 0)

    def wait(self):
        """
        Wait for the trace target to have
        something happen...   If the trace is in
        NonBlocking mode, this will fire a thread
        to wait for you and return control immediately.
        """
        if self.getMode("NonBlocking"):
            thr = Thread(target=self._doWait)
            thr.setDaemon(True)
            thr.start()
        else:
            self._doWait()

    def _doWait(self):
        doit = True
        while doit:
        # A wrapper method for  wait() and the wait thread to use
            event = self.platformWait()
            self.running = False
            self.platformProcessEvent(event)
            doit = self.shouldRunAgain()
            if doit:
                self._doRun()

    def _throwdownBreaks(self):
        """
        Run through the breakpoints and setup
        the ones that are enabled.
        """
        if self.getMode("FastBreak"):
            if self.fb_bp_done:
                return

        for wp in self.deferredwatch:
            addr = wp.resolveAddress(self)
            if addr != None:
                self.deferredwatch.remove(wp)
                self.watchpoints[addr] = wp
                self.archAddWatchpoint(addr)

        # Resolve deferred breaks
        for bp in self.deferred:
            addr = bp.resolveAddress(self)
            if addr != None:
                self.deferred.remove(bp)
                self.breakpoints[addr] = bp

        for bp in self.breakpoints.values():
            if bp.isEnabled():
                try:
                    bp.activate(self)
                except:
                    print "WARNING - bp at",hex(bp.address),"invalid, disabling"
                    bp.setEnabled(False)

        if self.getMode("FastBreak"):
            self.fb_bp_done = True

    def syncRegs(self):
        """
        Sync the reg-cache into the target process
        """
        if self.regcachedirty:
            buf = self.packRegisters(self.regcache)
            self.platformSetRegs(buf)
            self.regcachedirty = False
        self.regcache = None

    def cacheRegs(self):
        """
        Make sure the reg-cache is populated
        """
        if self.regcache == None:
            regbuf = self.platformGetRegs()
            self.regcache = self.unpackRegisters(regbuf)

    def _checkForBreak(self):
        """
        Check to see if we've landed on a breakpoint, and if so
        deactivate and step us past it.

        WARNING: Unfortunatly, cause this is used immidiatly before
        a call to run/wait, we must block briefly even for the GUI
        """
        bp = self.breakpoints.get(self.getProgramCounter(), None)
        if bp:
            if bp.active:
                bp.deactivate(self)
                orig = self.getMode("FastStep")
                self.setMode("FastStep", True)
                self.stepi()
                self.setMode("FastStep", orig)
                bp.activate(self)
                return True
            else:
                self.stepi()
        return False

    def shouldRunAgain(self):
        """
        A unified place for the test as to weather this trace
        should be told to run again after reaching some stopping
        condition.
        """
        if not self.attached:
            return False

        if self.exited:
            return False

        if self.getMode("RunForever"):
            return True

        if self.getMeta("AutoContinue"):
            return True

        return False

    def saveRegisters(self, newregs):
        """
        This is used mostly by setRegisters.  Use with CAUTION: you must
        specify ALL the register values perfectly!
        """
        mylist = [self.fmt,]
        for i in range(len(self.regnames)):
            mylist.append(newregs[self.regnames[i]])
        bytes = struct.pack(*mylist)
        self.platformSetRegs(bytes)

    def __repr__(self):
        run = "stopped"
        exe = "None"
        if self.isRunning():
            run = "running"
        elif self.exited:
            run = "exited"
        exe = self.getMeta("ExeName")
        return "<%s pid: %d, exe: %s, state: %s>" % (self.__class__.__name__, self.pid, exe, run)

    def initMode(self, name, value, descr):
        """
        Initialize a mode, this should ONLY be called
        during setup routines for the trace!  It determines
        the available mode setings.
        """
        self.modes[name] = bool(value)
        self.modedocs[name] = descr

    def release(self):
        """
        Do cleanup when we're done.  This is mostly necissary
        because of the thread proxy holding a reference to this
        tracer...  We need to let him die off and try to get
        garbage collected.
        """
        if self.thread:
            self.thread.go = False

    def __del__(self):
        print "WOOT"
        if self.attached:
            self.detach()

        for cls in inspect.getmro(self.__class__):
            if cls.__name__ == "Trace":
                continue

            if hasattr(cls, "finiMixin"):
                cls.finiMixin(self)

        if self.thread:
            self.thread.go = False


    def fireTracerThread(self):
        self.thread = TracerThread()

    def fireNotifiers(self, event):
        """
        Fire the registered notifiers for the NOTIFY_* event.
        """
        if currentThread().__class__ == TracerThread:
            raise Exception("ERROR: you can't fireNotifiers from *inside* the TracerThread")

        # Skip out on notifiers for NOTIFY_BREAK when in
        # FastBreak mode
        if self.getMode("FastBreak", False) and event == vtrace.NOTIFY_BREAK:
            return

        if self.getMode("FastStep", False) and event == vtrace.NOTIFY_STEP:
            return

        if event == vtrace.NOTIFY_SIGNAL:
            win32 = self.getMeta("Win32Event", None)
            if win32:
                code = win32["ExceptionCode"]
            else:
                code = self.getMeta("PendingSignal", 0)

            if code in self.getMeta("IgnoredSignals", []):
                if vtrace.verbose: print "Ignoring",code
                self.setMeta("AutoContinue", True)
                return

        alllist = self.getNotifiers(vtrace.NOTIFY_ALL)
        nlist = self.getNotifiers(event)

        trace = self
        # if the trace has a proxy it's notifiers
        # need that, cause we can't be pickled ;)
        if self.proxy:
            trace = self.proxy

        # The "NOTIFY_ALL" guys get priority
        for notifier in alllist:
            try:
                if notifier == self:
                    notifier.handleEvent(event,self)
                else:
                    notifier.handleEvent(event,trace)
            except:
                print "WARNING: Notifier exception for",repr(notifier)
                traceback.print_exc()

        for notifier in nlist:
            try:
                if notifier == self:
                    notifier.handleEvent(event,self)
                else:
                    notifier.handleEvent(event,trace)
            except:
                print "WARNING: Notifier exception for",repr(notifier)
                traceback.print_exc()

    def cleanupBreakpoints(self):
        self.fb_bp_done = False
        for bp in self.breakpoints.itervalues():
            # No harm in calling deactivate on
            # an inactive bp
            bp.deactivate(self)

    def checkWatchpoints(self):
        addr = self.archCheckWatchpoints()
        if not addr:
            return False
        wp = self.watchpoints.get(addr, None)
        if not wp:
            return False

        wp.notify(vtrace.NOTIFY_BREAK, self)
        self.fireNotifiers(vtrace.NOTIFY_BREAK)
        return True

    def getCurrentBreakpoint(self):
        """
        Return the current breakpoint otherwise None
        """
        # NOTE: Check breakpoints below can't use this cause
        # it comes before we've stepped back
        return self.breakpoints.get(self.getProgramCounter(), None)

    def checkBreakpoints(self):
        """
        This is mostly for systems (like linux) where you can't tell
        the difference between some SIGSTOP/SIGBREAK conditions and
        an actual breakpoint instruction.
        This method will return true if either the breakpoint
        subsystem or the sendBreak (via ShouldBreak meta) is true
        """
        if self.checkWatchpoints():
            return True

        pc = self.getProgramCounter()
        bi = self.getBreakInstruction()
        bl = pc - len(bi)
        bp = self.breakpoints.get(bl, None)

        if bp:
            addr = bp.getAddress()
            # Step back one instruction to account break
            self.setProgramCounter(addr)
            self.fireNotifiers(vtrace.NOTIFY_BREAK)
            try:
                bp.notify(vtrace.NOTIFY_BREAK, self)
            except Exception, msg:
                print "Breakpoint Exception 0x%.8x : %s" % (addr,msg)
            return True

        elif self.getMeta("ShouldBreak"):
            self.setMeta("ShouldBreak", False)
            self.fireNotifiers(vtrace.NOTIFY_BREAK)
            return True

        return False

    def notify(self, event, trace):
        """
        We are frequently a notifier for ourselves, so we can do things
        like handle events on attach and on break in a unified fashion.
        """
        self.threadcache = None
        self.mapcache = None
        self.fds = None
        self.running = False

        if event in self.auto_continue:
            self.setMeta("AutoContinue", True)
        else:
            self.setMeta("AutoContinue", False)

        if event == vtrace.NOTIFY_ATTACH:
            pass

        elif event == vtrace.NOTIFY_DETACH:
            self.cleanupBreakpoints()

        elif event == vtrace.NOTIFY_EXIT:
            self.setMode("RunForever", False)
            self.exited = True
            self.attached = False

        elif event == vtrace.NOTIFY_CONTINUE:
            pass

        elif event == vtrace.NOTIFY_LOAD_LIBRARY:
            self.cleanupBreakpoints()

        else:
            if not self.getMode("FastBreak"):
                self.cleanupBreakpoints()


    def addLibraryBase(self, libname, address):
        """
        This should be used *at load time* to setup the library
        event metadata.  This will also instantiate a VSymbolResolver
        for this platform and setup the internal structures as necissary

        This returns True/False for whether or not the library is
        going to be parsed (False on duplicate or non-file).

        This *must* be called from a context where it's safe to
        fire notifiers, because it will fire a notifier to alert
        about a LOAD_LIBRARY. (This means *not* from inside another
        notifer)
        """
        basename = os.path.basename(libname)

        self.setMeta("LatestLibrary", None)
        self.setMeta("LatestLibraryNorm", None)

        # Only actually do library work
        if (os.path.exists(libname) and
            not self.getMeta("LibraryBases").has_key(basename)):

            resolver = self.platformGetSymbolResolver(libname, address)
            self.resbynorm[resolver.normname] = resolver
            self.resbyfile[resolver.basename] = resolver
            self.getMeta("LibraryBases")[resolver.normname] = address

            self.setMeta("LatestLibrary", libname)
            self.setMeta("LatestLibraryNorm", resolver.normname)

            # We keep a descending order'd list of the resolver's base's so we
            # Can find the best resolver for an address quickly
            #FIXME move this to inside the resolvers
            index = 0
            if len(self.resbyaddr) > 0:
                index = None
                for i in range(len(self.resbyaddr)):
                    if resolver.loadbase > self.resbyaddr[i].loadbase:
                        index = i
                        break
                if index != None:
                    self.resbyaddr.insert(index, resolver)
                else:
                    self.resbyaddr.append(resolver)
            else:
                self.resbyaddr.append(resolver)

        self.fireNotifiers(vtrace.NOTIFY_LOAD_LIBRARY)
        return True

    def threadWrap(self, name, meth):
        """
        Cause the method (given in value) to be wrapped
        by a single thread for carying out.
        (which allows us to only synchronize what *needs* to
        synchronized...)
        """
        wrapmeth = TracerMethodProxy(meth, self.thread)
        setattr(self, name, wrapmeth)


########NEW FILE########
__FILENAME__ = darwin
"""
Darwin Platform Module
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import os
import struct
import signal
import vtrace
import vtrace.platforms.posix as v_posix
import vtrace.symbase as symbase

class MachoSymbolResolver(symbase.VSymbolResolver):
    pass

class MachoMixin:
    def platformGetSymbolResolver(self, filename, baseaddr):
        return MachoSymbolResolver(filename, baseaddr)

class DarwinMixin:

    def initMixin(self):
        self.tdict = {}

    def platformExec(self, cmdline):
        import mach
        pid = v_posix.PtraceMixin.platformExec(self, cmdline)
        self.task = mach.task_for_pid(pid)
        return pid

    def platformProcessEvent(self, status):
        """
        This is *extreemly* similar to the posix one, but I'm tired
        of trying to make the same code handle linux/bsd/mach.  They
        have subtle differences (particularly in threading).
        """

        if os.WIFEXITED(status):
            self.setMeta("ExitCode", os.WEXITSTATUS(status))
            self.fireNotifiers(vtrace.NOTIFY_EXIT)

        elif os.WIFSIGNALED(status):
            self.setMeta("ExitCode", os.WTERMSIG(status))
            self.fireNotifiers(vtrace.NOTIFY_EXIT)

        elif os.WIFSTOPPED(status):
            sig = os.WSTOPSIG(status)
            if sig == signal.SIGTRAP:
                # Traps on posix systems are a little complicated
                if self.stepping:
                    self.stepping = False
                    self.fireNotifiers(vtrace.NOTIFY_STEP)

                elif self.checkBreakpoints():
                    # It was either a known BP or a sendBreak()
                    return

                elif self.execing:
                    self.execing = False
                    self.handleAttach()

                else:
                    self.setMeta("PendingSignal", sig)
                    self.fireNotifiers(vtrace.NOTIFY_SIGNAL)

            elif sig == signal.SIGSTOP:
                self.handleAttach()

            else:
                self.setMeta("PendingSignal", sig)
                self.fireNotifiers(vtrace.NOTIFY_SIGNAL)

        else:
            print "OMG WTF JUST HAPPENED??!?11/!?1?>!"

    def platformPs(self):
        import mach
        return mach.process_list()

    def platformGetFds(self):
        print "FIXME platformGetFds() no workie on darwin yet..."
        return []

    def platformGetMaps(self):
        return self.task.get_mmaps()

    def platformReadMemory(self, address, length):
        return self.task.vm_read(address, length)

    def platformWriteMemory(self, address, buffer):
        return self.task.vm_write(address, buffer)

    def currentMachThread(self):
        self.getThreads()
        return self.tdict[self.getMeta("ThreadId")]

    def platformGetRegs(self):
        """
        """
        thr = self.currentMachThread()
        regs = thr.get_state(self.thread_state)
        return regs + thr.get_state(self.debug_state)

    def platformSetRegs(self, regbuf):
        thr = self.currentMachThread()
        # XXX these 32 boundaries are wrong
        thr.set_state(self.thread_state, regbuf[:-32])
        thr.set_state(self.debug_state,  regbuf[-32:])

    def platformGetThreads(self):
        ret = {}
        self.tdict = {}
        spname = self.archGetSpName()
        for thread in self.task.threads():
            # We can't call platformGetRegs here... (loop, loop...)
            regbuf = thread.get_state(self.thread_state) + thread.get_state(self.debug_state)
            regdict = self.unpackRegisters(regbuf)
            sp = regdict.get(spname, 0)
            mapbase,maplen,mperm,mfile = self.getMap(sp)
            tid = mapbase + maplen # The TOP of the stack, so it doesn't grow down and change
            ret[tid] = tid
            self.tdict[tid] = thread
        self.setMeta("ThreadId", tid) #FIXME how can we know what thread caused an event?
        return ret

    def platformAttach(self, pid):
        import mach
        #FIXME setMeta("ExeName", stuff)
        self.task = mach.task_for_pid(pid)
        v_posix.PtraceMixin.platformAttach(self, pid)

class DarwinIntel32Registers:
    """
    Mixin for the register format of Darwin on Intel 32
    """
    thread_state = 1
    debug_state = 10

    def getRegisterFormat(self):
        return "24L"

    def getRegisterNames(self):
        return ("eax","ebx","ecx","edx","edi",
                "esi","ebp","esp","ss","eflags",
                "eip","cs","ds","es","fs","gs",
                "debug0","debug1","debug2","debug3",
                "debug4","debug5","debug6","debug7")

class DarwinPpc32Registers:
    """
    Mixin for the register format of Darwin on PPC 32
    """
    thread_state = 4
    debug_state = 11

    def getRegisterFormat(self):
        return "40L"

    def getRegisterNames(self):
        mylist = []
        for i in range(40):
            mylist.append("r%d" % i)
        return mylist


########NEW FILE########
__FILENAME__ = freebsd
"""
FreeBSD support...
"""

import os
import ctypes
import ctypes.util as cutil

import vtrace
import vtrace.platforms.posix as v_posix
import vtrace.util as v_util

libkvm = ctypes.CDLL(cutil.find_library("kvm"))

# kvm_getprocs cmds
KERN_PROC_ALL           = 0       # everything
KERN_PROC_PID           = 1       # by process id
KERN_PROC_PGRP          = 2       # by process group id
KERN_PROC_SESSION       = 3       # by session of pid
KERN_PROC_TTY           = 4       # by controlling tty
KERN_PROC_UID           = 5       # by effective uid
KERN_PROC_RUID          = 6       # by real uid
KERN_PROC_ARGS          = 7       # get/set arguments/proctitle
KERN_PROC_PROC          = 8       # only return procs
KERN_PROC_SV_NAME       = 9       # get syscall vector name
KERN_PROC_RGID          = 10      # by real group id
KERN_PROC_GID           = 11      # by effective group id
KERN_PROC_PATHNAME      = 12      # path to executable
KERN_PROC_INC_THREAD    = 0x10    # Include threads in filtered results

pid_t = ctypes.c_int32
lwpid_t = ctypes.c_int32
void_p = ctypes.c_void_p
dev_t = ctypes.c_uint32
sigset_t = ctypes.c_uint32*4
uid_t = ctypes.c_uint32
gid_t = ctypes.c_uint32
fixpt_t = ctypes.c_uint32

vm_size_t = ctypes.c_uint32 # FIXME this should maybe be 64 bit safe
segsz_t = ctypes.c_uint32 # FIXME this should maybe be 64 bit safe

# Could go crazy and grep headers for this stuff ;)
KI_NGROUPS = 16
OCOMMLEN = 16
WMESGLEN = 8
LOGNAMELEN = 17
LOCKNAMELEN = 8
COMMLEN = 19
KI_EMULNAMELEN = 16
KI_NSPARE_INT = 10
KI_NSPARE_PTR = 7
KI_NSPARE_LONG = 12


def c_buf(size):
    return ctypes.c_char * size

class PRIORITY(ctypes.Structure):
    _fields_ = (
        ("pri_class", ctypes.c_ubyte),
        ("pri_level", ctypes.c_ubyte),
        ("pri_native", ctypes.c_ubyte),
        ("pri_user", ctypes.c_ubyte)
    )

class TIMEVAL(ctypes.Structure):
    _fields_ = (
        ("tv_sec", ctypes.c_long),
        ("tv_usec", ctypes.c_long)
    )

class RUSAGE(ctypes.Structure):
    _fields_ = (
        ("ru_utime", TIMEVAL),          # user time used
        ("ru_stime", TIMEVAL),          # system time used
        ("ru_maxrss", ctypes.c_long),   #
        ("ru_ixrss", ctypes.c_long),    # (j) integral shared memory size
        ("ru_idrss", ctypes.c_long),    # (j) integral unshared data
        ("ru_isrss", ctypes.c_long),    # (j) integral unshared stack
        ("ru_minflt", ctypes.c_long),   # (c) page reclaims
        ("ru_majflt", ctypes.c_long),   # (c) page faults
        ("ru_nswap", ctypes.c_long),    # (c + j) swaps
        ("ru_inblock", ctypes.c_long),  # (n) block input operations
        ("ru_oublock", ctypes.c_long),  # (n) block output operations
        ("ru_msgsnd", ctypes.c_long),   # (n) messages sent
        ("ru_msgrcv", ctypes.c_long),   # (n) messages received
        ("ru_nsignals", ctypes.c_long), # (c) signals received
        ("ru_nvcsw", ctypes.c_long),    # (j) voluntary context switches
        ("ru_nivcsw", ctypes.c_long),   # (j) involuntary
    )


class KINFO_PROC(ctypes.Structure):
    _fields_ = (
        ("ki_structsize", ctypes.c_int),# size of this structure
        ("ki_layout", ctypes.c_int),    # reserved: layout identifier
        ("ki_args", void_p),            # address of command arguments (struct pargs*)
        ("ki_paddr", void_p),           # address of proc (struct proc*)
        ("ki_addr", void_p),            # kernel virtual addr of u-area (struct user*)
        ("ki_tracep", void_p),          # pointer to trace file (struct vnode *)
        ("ki_textvp", void_p),          # pointer to executable file (struct vnode *)
	("ki_fd", void_p),              # pointer to open file info (struct filedesc  *)
        ("ki_vmspace", void_p),         # pointer to kernel vmspace struct (struct vmspace *)
        ("ki_wchan", void_p),           # sleep address (void*)
	("ki_pid", pid_t),              # Process identifier
        ("ki_ppid", pid_t),             # parent process id
        ("ki_pgid", pid_t),             # process group id
        ("ki_tpgid", pid_t),            # tty process group id
        ("ki_sid", pid_t),              # Process session ID
        ("ki_tsid", pid_t),             # Terminal session ID
        ("ki_jobc", ctypes.c_short),    # job control counter
        ("ki_spare_short1", ctypes.c_short), #
        ("ki_tdev", dev_t),             # controlling tty dev
        ("ki_siglist", sigset_t),       # Signals arrived but not delivered
        ("ki_sigmask", sigset_t),       # Current signal mask
        ("ki_sigignore", sigset_t),     # Signals being ignored
        ("ki_sigcatch", sigset_t),      # Signals being caught by user
        ("ki_uid", uid_t),              # effective user id
        ("ki_ruid", uid_t),             # Real user id
        ("ki_svuid", uid_t),            # Saved effective user id
        ("ki_rgid", gid_t),             # Real group id
        ("ki_svgid", gid_t),            # Saved effective group id
        ("ki_ngroups", ctypes.c_short), # number of groups
        ("ki_spare_short2", ctypes.c_short),
        ("ki_groups", gid_t * KI_NGROUPS), # groups
        ("ki_size", vm_size_t),         # virtual size
        ("ki_rssize", segsz_t),         # current resident set size in pages
        ("ki_swrss", segsz_t),          # resident set size before last swap
        ("ki_tsize", segsz_t),          # text size (pages) XXX
        ("ki_dsize", segsz_t),          # data size (pages) XXX
        ("ki_ssize", segsz_t),          # stack size (pages)
        ("ki_xstat", ctypes.c_ushort),  # Exit status for wait and stop signal
        ("ki_acflag", ctypes.c_ushort), # Accounting flags
        ("ki_pctcpu", fixpt_t),         # %cpu for process during ki_swtime
        ("ki_estcpu", ctypes.c_uint),   # Time averaged value of ki_cpticks
        ("ki_slptime", ctypes.c_uint),  # Time since last blocked
        ("ki_swtime", ctypes.c_uint),   # Time swapped in or out
        ("ki_spareint1", ctypes.c_int), # unused (just here for alignment)
        ("ki_runtime", ctypes.c_uint64),# Real time in microsec
        ("ki_start", TIMEVAL),          # starting time
        ("ki_childtime", TIMEVAL),      # time used by process children
        ("ki_flag", ctypes.c_long),     # P_* flags
        ("ki_kiflag", ctypes.c_long),   # KI_* flags
        ("ki_traceflag", ctypes.c_int), # kernel trace points
        ("ki_stat", ctypes.c_char),     # S* process status
        ("ki_nice", ctypes.c_ubyte),    # Process "nice" value
        ("ki_lock", ctypes.c_char),     # Process lock (prevent swap) count
        ("ki_rqindex", ctypes.c_char),  # Run queue index
        ("ki_oncpu", ctypes.c_char),    # Which cpu we are on
        ("ki_lastcpu", ctypes.c_char),  # Last cpu we were on
        ("ki_ocomm", c_buf(OCOMMLEN+1)),      # command name
        ("ki_wmesg", c_buf(WMESGLEN+1)),      # wchan message
        ("ki_login", c_buf(LOGNAMELEN+1)),    # setlogin name
        ("ki_lockname", c_buf(LOCKNAMELEN+1)),# lock name
        ("ki_comm", c_buf(COMMLEN+1)),        # command name
        ("ki_emul", c_buf(KI_EMULNAMELEN+1)), # emulation name
        ("ki_sparestrings",c_buf(68)),   # spare string space
        ("ki_spareints", ctypes.c_int*KI_NSPARE_INT),
        ("ki_jid", ctypes.c_int),       # Process jail ID
        ("ki_numthreads", ctypes.c_int),# KSE number of total threads
        ("ki_tid", lwpid_t),            # thread id
        ("ki_pri", PRIORITY),           # process priority
        ("ki_rusage", RUSAGE),          # process rusage statistics
        # XXX - most fields in ki_rusage_ch are not (yet) filled in
        ("ki_rusage_ch", RUSAGE),       # rusage of children processes
        ("ki_pcb", void_p),             # kernel virtual addr of pcb
        ("ki_kstack", void_p),          # kernel virtual addr of stack
        ("ki_udata", void_p),           # User convenience pointer
        ("ki_spareptrs", void_p*KI_NSPARE_PTR),
        ("ki_sparelongs", ctypes.c_long*KI_NSPARE_LONG),
        ("ki_sflag", ctypes.c_long),    # PS_* flags
        ("ki_tdflags", ctypes.c_long),  # KSE kthread flag
    )

# All the FreeBSD ptrace defines
PT_TRACE_ME     = 0       #/* child declares it's being traced */
PT_READ_I       = 1       #/* read word in child's I space */
PT_READ_D       = 2       #/* read word in child's D space */
PT_WRITE_I      = 4       #/* write word in child's I space */
PT_WRITE_D      = 5       #/* write word in child's D space */
PT_CONTINUE     = 7       #/* continue the child */
PT_KILL         = 8       #/* kill the child process */
PT_STEP         = 9       #/* single step the child */
PT_ATTACH       = 10      #/* trace some running process */
PT_DETACH       = 11      #/* stop tracing a process */
PT_IO           = 12      #/* do I/O to/from stopped process. */
PT_LWPINFO      = 13      #/* Info about the LWP that stopped. */
PT_GETNUMLWPS   = 14      #/* get total number of threads */
PT_GETLWPLIST   = 15      #/* get thread list */
PT_CLEARSTEP    = 16      #/* turn off single step */
PT_SETSTEP      = 17      #/* turn on single step */
PT_SUSPEND      = 18      #/* suspend a thread */
PT_RESUME       = 19      #/* resume a thread */
PT_TO_SCE       = 20      # Stop on syscall entry
PT_TO_SCX       = 21      # Stop on syscall exit
PT_SYSCALL      = 22      # Stop on syscall entry and exit
PT_GETREGS      = 33      #/* get general-purpose registers */
PT_SETREGS      = 34      #/* set general-purpose registers */
PT_GETFPREGS    = 35      #/* get floating-point registers */
PT_SETFPREGS    = 36      #/* set floating-point registers */
PT_GETDBREGS    = 37      #/* get debugging registers */
PT_SETDBREGS    = 38      #/* set debugging registers */
#PT_FIRSTMACH    = 64      #/* for machine-specific requests */

# On PT_IO addr is a pointer to a struct

class PTRACE_IO_DESC(ctypes.Structure):
    _fields_ = [
        ("piod_op", ctypes.c_int),      # I/O operation
        ("piod_offs", ctypes.c_void_p), # Child offset
        ("piod_addr", ctypes.c_void_p), # Parent Offset
        ("piod_len", ctypes.c_uint)     # Size
    ]

# Operations in piod_op.
PIOD_READ_D     = 1       # Read from D space
PIOD_WRITE_D    = 2       # Write to D space
PIOD_READ_I     = 3       # Read from I space
PIOD_WRITE_I    = 4       # Write to I space

class PTRACE_LWPINFO(ctypes.Structure):
    _fields_ = (
        ("pl_lwpid", lwpid_t),
        ("pl_event", ctypes.c_int),
        ("pl_flags", ctypes.c_int),
        ("pl_sigmask", sigset_t),
        ("pl_siglist", sigset_t),
    )

PL_EVENT_NONE   = 0
PL_EVENT_SIGNAL = 1

PL_FLAGS_SA    = 0
PL_FLAGS_BOUND = 1

class FreeBSDMixin:

    def initMixin(self):
        self.initMode("Syscall", False, "Break on Syscalls")
        self.kvmh = libkvm.kvm_open(None, None, None, 0, "vtrace")

    def finiMixin(self):
        print "FIXME I DON'T THINK THIS IS BEING CALLED"
        if self.kvmh != None:
            libkvm.kvm_close(self.kvmh)

    def platformReadMemory(self, address, size):
        #FIXME optimize for speed!
        iod = PTRACE_IO_DESC()
        buf = ctypes.create_string_buffer(size)

        iod.piod_op = PIOD_READ_D
        iod.piod_addr = ctypes.addressof(buf)
        iod.piod_offs = address
        iod.piod_len = size

        if v_posix.ptrace(PT_IO, self.pid, ctypes.addressof(iod), 0) != 0:
            raise Exception("ptrace PT_IO failed to read 0x%.8x" % address)

        return buf.raw

    def platformWriteMemory(self, address, buf):
        #FIXME optimize for speed!
        iod = PTRACE_IO_DESC()

        cbuf = ctypes.create_string_buffer(buf)

        iod.piod_op = PIOD_WRITE_D
        iod.piod_addr = ctypes.addressof(cbuf)
        iod.piod_offs = address
        iod.piod_len = len(buf)

        if v_posix.ptrace(PT_IO, self.pid, ctypes.addressof(iod), 0) != 0:
            raise Exception("ptrace PT_IO failed to read 0x%.8x" % address)

    def platformAttach(self, pid):
        if v_posix.ptrace(PT_ATTACH, pid, 0, 0) != 0:
            raise Exception("Ptrace Attach Failed")

    def platformExec(self, cmdline):
        # Basically just like the one in the Ptrace mixin...
        self.execing = True
        cmdlist = v_util.splitargs(cmdline)
        os.stat(cmdlist[0])
        pid = os.fork()
        if pid == 0:
            v_posix.ptrace(PT_TRACE_ME, 0, 0, 0)
            os.execv(cmdlist[0], cmdlist)
            sys.exit(-1)
        return pid

    def platformWait(self):
        status = v_posix.PosixMixin.platformWait(self)
        # Get the thread id from the ptrace interface

        info = PTRACE_LWPINFO()
        size = ctypes.sizeof(info)
        if v_posix.ptrace(PT_LWPINFO, self.pid, ctypes.byref(info), size) == 0:
            self.setMeta("ThreadId", info.pl_lwpid)
        else:
            #FIXME this is because posix wait is linux specific and broke
            self.setMeta("ThreadId", self.pid)

        return status

    def platformStepi(self):
        self.stepping = True
        if v_posix.ptrace(PT_STEP, self.pid, 1, 0) != 0:
            raise Exception("ptrace PT_STEP failed!")

    def platformContinue(self):
        cmd = PT_CONTINUE
        if self.getMode("Syscall"):
            cmd = PT_SYSCALL

        sig = self.getMeta("PendingSignal", 0)
        # In freebsd address is the place to continue from
        # but 1 means use existing EIP
        if v_posix.ptrace(cmd, self.pid, 1, sig) != 0:
            raise Exception("ptrace PT_CONTINUE/PT_SYSCALL failed")

    #def platformExec(self, cmdline):

    def platformDetach(self):
        if v_posix.ptrace(PT_DETACH, self.pid, 1, 0) != 0:
            raise Exception("Ptrace Detach Failed")

    def platformGetThreads(self):
        ret = {}
        cnt = self._getThreadCount()
        buf = (ctypes.c_int * cnt)()
        if v_posix.ptrace(PT_GETLWPLIST, self.pid, buf, cnt) != cnt:
            raise Exception("ptrace PW_GETLWPLIST failed")
        for x in buf:
            ret[x] = x
        return ret

    def _getThreadCount(self):
        return v_posix.ptrace(PT_GETNUMLWPS, self.pid, 0, 0)

    def platformGetFds(self):
        return []

    def platformGetMaps(self):
        # FIXME make this not need proc
        ret = []
        mpath = "/proc/%d/map" % self.pid
        if not os.path.isfile(mpath):
            raise Exception("Memory map enumeration requires /proc on FreeBSD")

        mapfile = file(mpath, "rb")
        for line in mapfile:
            perms = 0
            fname = ""
            maptup = line.split(None, 12)
            base = int(maptup[0], 16)
            max  = int(maptup[1], 16)
            permstr = maptup[5]

            if maptup[11] == "vnode":
                fname = maptup[12].strip()

            if permstr[0] == 'r':
                perms |= vtrace.MM_READ

            if permstr[1] == 'w':
                perms |= vtrace.MM_WRITE

            if permstr[2] == 'x':
                perms |= vtrace.MM_EXEC

            ret.append((base, max-base, perms, fname))

        return ret

    def platformPs(self):
        ret = []
        cnt = ctypes.c_uint(0)
        kinfo = KINFO_PROC()
        ksize = ctypes.sizeof(kinfo)
        kaddr = ctypes.addressof(kinfo)

        p = libkvm.kvm_getprocs(self.kvmh, KERN_PROC_PROC, 0, ctypes.addressof(cnt))
        for i in xrange(cnt.value):
            ctypes.memmove(kaddr, p + (i*ksize), ksize)
            if kinfo.ki_structsize != ksize:
                print "WARNING: KINFO_PROC CHANGED SIZE, Trying to account for it... good luck"
                ksize = kinfo.ki_structsize
            ret.append((kinfo.ki_pid, kinfo.ki_comm))

        return ret

GEN_REG_CNT = 19
DBG_REG_CNT = 8
TOT_REG_CNT = GEN_REG_CNT + DBG_REG_CNT

class FreeBSDIntelRegisters:

    def platformGetRegs(self):
        buf = ctypes.create_string_buffer(TOT_REG_CNT*4)
        #FIXME thread specific
        if v_posix.ptrace(PT_GETREGS, self.pid, buf, 0) != 0:
            raise Exception("ptrace PT_GETREGS failed!")
        if v_posix.ptrace(PT_GETDBREGS, self.pid, ctypes.addressof(buf)+(GEN_REG_CNT*4), 0) != 0:
            raise Exception("ptrace PT_GETDBREGS failed!")
        return buf.raw

    def platformSetRegs(self, buf):
        #FIXME thread specific
        if v_posix.ptrace(PT_SETREGS, self.pid, buf, 0) != 0:
            raise Exception("ptrace PT_SETREGS failed!")
        if v_posix.ptrace(PT_SETDBREGS, self.pid, buf[(GEN_REG_CNT*4):], 0) != 0:
            raise Exception("ptrace PT_SETDBREGS failed!")

    def getRegisterFormat(self):
        return "<27L"

    def getRegisterNames(self):
        return ["fs","es","ds","edi","esi","ebp","isp",
                "ebx","edx","ecx","eax","trapno","err",
                "eip","cs","eflags","esp","ss","gs","debug0",
                "debug1","debug2","debug3","debug4","debug5",
                "debug6","debug7"]
                


########NEW FILE########
__FILENAME__ = linux
"""
Linux Platform Module
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import os
import struct
import signal
import traceback
import platform

import vtrace
import vtrace.breakpoints as breakpoints
import vtrace.platforms.posix as v_posix
from vtrace.platforms.base import UtilMixin

import types

from ctypes import *
import ctypes.util as cutil

libc = CDLL(cutil.find_library("c"))

O_RDWR = 2
O_LARGEFILE = 0x8000

MAP_ANONYMOUS = 0x20
MAP_PRIVATE = 0x02

# Linux specific ptrace extensions
PT_GETREGS = 12
PT_SETREGS = 13
PT_GETFPREGS = 14
PT_SETFPREGS = 15
PT_ATTACH = 16
PT_DETACH = 17
PT_GETFPXREGS = 18
PT_SETFPXREGS = 19
PT_SYSCALL = 24
PT_SETOPTIONS = 0x4200
PT_GETEVENTMSG = 0x4201
PT_GETSIGINFO = 0x4202
PT_SETSIGINFO = 0x4203
# PT set options stuff.  ONLY TRACESYSGOOD may be used in 2.4...
PT_O_TRACESYSGOOD   = 0x00000001 # add 0x80 to TRAP when generated by syscall
# For each of the options below, the stop signal is (TRAP | PT_EVENT_FOO << 8)
PT_O_TRACEFORK      = 0x00000002 # Cause a trap at fork
PT_O_TRACEVFORK     = 0x00000004 # Cause a trap at vfork
PT_O_TRACECLONE     = 0x00000008 # Cause a trap at clone
PT_O_TRACEEXEC      = 0x00000010 # Cause a trap at exec
PT_O_TRACEVFORKDONE = 0x00000020 # Cause a trap when vfork done
PT_O_TRACEEXIT      = 0x00000040 # Cause a trap on exit
PT_O_MASK           = 0x0000007f
# Ptrace event types (TRAP | PT_EVENT_FOO << 8) means that type
# when using GETEVENTMSG for most of these, the new pid is the data
PT_EVENT_FORK       = 1
PT_EVENT_VFORK      = 2
PT_EVENT_CLONE      = 3
PT_EVENT_EXEC       = 4
PT_EVENT_VFORK_DONE = 5
PT_EVENT_EXIT       = 6

# Used to tell some of the additional events apart
SIG_LINUX_SYSCALL = signal.SIGTRAP | 0x80
SIG_LINUX_CLONE = signal.SIGTRAP | (PT_EVENT_CLONE << 8)

class LinuxMixin:
    """
    The mixin to take care of linux specific platform traits.
    (mostly proc)
    """

    def initMixin(self):
        # Wrap reads from proc in our worker thread
        self.pthreads = [] # FIXME perhaps make this posix-wide not just linux eventually...
        self.threadWrap("platformAllocateMemory", self.platformAllocateMemory)
        self.threadWrap("getPtraceEvent", self.getPtraceEvent)
        self.threadWrap("platformReadMemory", self.platformReadMemory)
        if platform.release().startswith("2.4"):
            self.threadWrap("platformWait", self.platformWait)
        #self.threadWrap("platformWriteMemory", self.platformWriteMemory)
        self.threadWrap("doAttachThread", self.doAttachThread)
        self.nptlinit = False
        self.memfd = None

        self.initMode("Syscall", False, "Break On Syscalls")

    def platformExec(self, cmdline):
        pid = v_posix.PtraceMixin.platformExec(self, cmdline)
        self.pthreads = [pid,]
        self.setMeta("ExeName",self._findExe(pid))
        return pid

    def setupMemFile(self, offset):
        """
        A utility to open (if necissary) and seek the memfile
        """
        if self.memfd == None:
            self.memfd = libc.open("/proc/%d/mem" % self.pid, O_RDWR | O_LARGEFILE, 0755)

        addr = c_ulonglong(offset)
        x = libc.llseek(self.memfd, addr, 0)

    #FIXME this is intel specific and should probably go in with the regs
    def platformAllocateMemory(self, size, perms=vtrace.MM_RWX, suggestaddr=0):
        sp = self.getStackCounter()
        pc = self.getProgramCounter()

        # Xlate perms (mmap is backward)
        realperm = 0
        if perms & vtrace.MM_READ:
            realperm |= 1
        if perms & vtrace.MM_WRITE:
            realperm |= 2
        if perms & vtrace.MM_EXEC:
            realperm |= 4

        #mma is struct of mmap args for linux syscall
        mma = struct.pack("<6L", suggestaddr, size, realperm, MAP_ANONYMOUS|MAP_PRIVATE, 0, 0)

        regsave = self.getRegisters()

        stacksave = self.readMemory(sp, len(mma))
        ipsave = self.readMemory(pc, 2)

        SYS_mmap = 90

        self.writeMemory(sp, mma)
        self.writeMemory(pc, "\xcd\x80")
        self.setRegisterByName("eax", SYS_mmap)
        self.setRegisterByName("ebx", sp)
        self.syncRegs()

        try:
            # Step over our syscall instruction
            tid = self.getMeta("ThreadId", 0)
            self.platformStepi()
            os.waitpid(tid, 0)
            eax = self.getRegisterByName("eax")
            if eax & 0x80000000:
                raise Exception("Linux mmap syscall error: %d" % eax)
            return eax

        finally:
            # Clean up all our fux0ring
            self.writeMemory(sp, stacksave)
            self.writeMemory(pc, ipsave)
            self.setRegisters(regsave)

    def handleAttach(self):
        for tid in self.threadsForPid(self.pid):
            if tid == self.pid:
                continue
            self.attachThread(tid)
        v_posix.PosixMixin.handleAttach(self)

    def platformReadMemory(self, address, size):
        """
        A *much* faster way of reading memory that the 4 bytes
        per syscall allowed by ptrace
        """
        self.setupMemFile(address)
        # Use ctypes cause python implementation is teh ghey
        buf = create_string_buffer("\x00" * size)
        x = libc.read(self.memfd, addressof(buf), size)
        if x != size:
            raise Exception("reading from invalid memory %s (%d returned)" % (hex(address), x))
        # We have to slice cause ctypes "helps" us by adding a null byte...
        return buf.raw[:size]

    #def whynot_platformWriteMemory(self, address, data):
        """
        A *much* faster way of writting memory that the 4 bytes
        per syscall allowed by ptrace
        """
        self.setupMemFile(address)
        buf = create_string_buffer(data)
        size = len(data)
        x = libc.write(self.memfd, addressof(buf), size)
        if x != size:
            raise Exception("write memory failed: %d" % x)
        return x

    def _findExe(self, pid):
        exe = os.readlink("/proc/%d/exe" % pid)
        if "(deleted)" in exe:
            if "#prelink#" in exe:
                exe = exe.split(".#prelink#")[0]
            elif ";" in exe:
                exe = exe.split(";")[0]
            else:
                exe = exe.split("(deleted)")[0].strip()
        return exe

    def platformAttach(self, pid):
        self.pthreads = [pid,]
        self.setMeta("ThreadId", pid)
        if v_posix.ptrace(PT_ATTACH, pid, 0, 0) != 0:
            raise Exception("PT_ATTACH failed!")
        self.setupPtraceOptions(pid)
        self.setMeta("ExeName", self._findExe(pid))

    def platformPs(self):
        pslist = []
        for dname in os.listdir("/proc/"):
            try:
                if not dname.isdigit():
                    continue
                cmdline = file("/proc/%s/cmdline" % dname).read()
                cmdline = cmdline.replace("\x00"," ")
                if len(cmdline) > 0:
                    pslist.append((int(dname),cmdline))
            except:
                pass # Permissions...  quick process... whatev.
        return pslist

    def attachThread(self, tid, attached=False):
        self.doAttachThread(tid,attached=attached)
        self.setMeta("ThreadId", tid)
        self.fireNotifiers(vtrace.NOTIFY_CREATE_THREAD)

    def platformWait(self):
        # Blocking wait once...
        pid, status = os.waitpid(-1, 0x40000002)
        self.setMeta("ThreadId", pid)
        # Stop the rest of the threads... 
        # why is linux debugging so Ghetto?!?!
        if not self.stepping: # If we're stepping, only do the one
            for tid in self.pthreads:
                if tid == pid:
                    continue
                os.kill(tid, signal.SIGTRAP)
                os.waitpid(tid, 0x40000002)
        return status

    def platformContinue(self):
        cmd = v_posix.PT_CONTINUE
        if self.getMode("Syscall", False):
            cmd = PT_SYSCALL
        pid = self.getPid()
        sig = self.getMeta("PendingSignal", 0)
        # Only deliver signals to the main thread
        if v_posix.ptrace(cmd, pid, 0, sig) != 0:
            raise Exception("ERROR ptrace failed for tid %d" % pid)

        for tid in self.pthreads:
            if tid == pid:
                continue
            if v_posix.ptrace(cmd, tid, 0, 0) != 0:
                pass

    def platformStepi(self):
        self.stepping = True
        tid = self.getMeta("ThreadId", 0)
        if v_posix.ptrace(v_posix.PT_STEP, tid, 0, 0) != 0:
            raise Exception("ERROR ptrace failed!")

    def platformDetach(self):
        libc.close(self.memfd)
        for tid in self.pthreads:
            tid,v_posix.ptrace(PT_DETACH, tid, 0, 0)

    def doAttachThread(self, tid, attached=False):
        """
        Do the work for attaching a thread.  This must be *under*
        attachThread() so callers in notifiers may call it (because
        it's also gotta be thread wrapped).
        """
        if not attached:
            if v_posix.ptrace(PT_ATTACH, tid, 0, 0) != 0:
                raise Exception("ERROR ptrace attach failed for thread %d" % tid)
        os.waitpid(tid, 0x40000002)
        self.setupPtraceOptions(tid)
        self.pthreads.append(tid)

    def setupPtraceOptions(self, tid):
        """
        Called by doAttachThread to setup ptrace related options.
        """
        opts = PT_O_TRACESYSGOOD
        if platform.release().startswith("2.6"):
            opts |= PT_O_TRACECLONE
        x = v_posix.ptrace(PT_SETOPTIONS, tid, 0, opts)
        if x != 0:
            print "WARNING ptrace SETOPTIONS failed for thread %d (%d)" % (tid,x)

    def threadsForPid(self, pid):
        ret = []
        tpath = "/proc/%s/task" % pid
        if os.path.exists(tpath):
            for pidstr in os.listdir(tpath):
                ret.append(int(pidstr))
        return ret

    def platformProcessEvent(self, status):
        # Skim some linux specific events before passing to posix
        tid = self.getMeta("ThreadId", -1)
        if os.WIFSTOPPED(status):
            sig = status >> 8
            if sig == SIG_LINUX_SYSCALL:
                self.fireNotifiers(vtrace.NOTIFY_SYSCALL)

            elif sig == SIG_LINUX_CLONE:
                # Handle a new thread here!
                newtid = self.getPtraceEvent()
                self.attachThread(newtid, attached=True)

            #FIXME eventually implement child catching!
            else:
                self.handlePosixSignal(sig)

            return

        v_posix.PosixMixin.platformProcessEvent(self, status)

    def getPtraceEvent(self):
        """
        This *thread wrapped* function will get any pending GETEVENTMSG
        msgs.
        """
        p = c_ulong(0)
        tid = self.getMeta("ThreadId", -1)
        if v_posix.ptrace(PT_GETEVENTMSG, tid, 0, byref(p)) != 0:
            raise Exception("ptrace PT_GETEVENTMSG failed! %d" % x)
        return p.value

    def platformGetRegs(self):
        x = (c_char * 512)()
        tid = self.getMeta("ThreadId", self.getPid())
        if v_posix.ptrace(PT_GETREGS, tid, 0, addressof(x)) != 0:
            raise Exception("ERROR ptrace PT_GETREGS failed for TID %d" % tid)
        return x.raw

    def platformGetThreads(self):
        ret = {}
        for tid in self.pthreads:
            ret[tid] = tid #FIXME make this pthread struct or stackbase soon
        return ret

    def platformGetMaps(self):
        self.requireAttached()
        maps = []
        mapfile = file("/proc/%d/maps" % self.pid)
        for line in mapfile:

            perms = 0
            sline = line.split(" ")
            addrs = sline[0]
            permstr = sline[1]
            fname = sline[-1].strip()
            addrs = addrs.split("-")
            base = long(addrs[0],16)
            max = long(addrs[1],16)
            mlen = max-base

            if "r" in permstr:
                perms |= vtrace.MM_READ
            if "w" in permstr:
                perms |= vtrace.MM_WRITE
            if "x" in permstr:
                perms |= vtrace.MM_EXEC
            #if "p" in permstr:
                #pass

            maps.append((base,mlen,perms,fname))
        return maps

    def platformGetFds(self):
        fds = []
        for name in os.listdir("/proc/%d/fd/" % self.pid):
            try:
                fdnum = int(name)
                fdtype = vtrace.FD_UNKNOWN
                link = os.readlink("/proc/%d/fd/%s" % (self.pid,name))
                if "socket:" in link:
                    fdtype = vtrace.FD_SOCKET
                elif "pipe:" in link:
                    fdtype = vtrace.FD_PIPE
                elif "/" in link:
                    fdtype = vtrace.FD_FILE

                fds.append((fdnum,fdtype,link))
            except:
                traceback.print_exc()

        return fds

class LinuxIntelRegisters:
    """
    The actual trace object for IntelLinux, which inherits
    what it can from IntelMixin/LinuxMixin and implements
    what is must.

    The size of the linux user area struct is 284 bytes...

    """

    def initMixin(self):
        self.usize = 284

    def maybeCalcUserSize(self):
        """
        LOL... this works actually... but we're not using it...
        """
        if self.usize != 0:
            return
        tid = self.getMeta("ThreadId", self.getPid())
        val = -1
        off = 500
        while val == -1:
            off -= 4
            val = v_posix.ptrace(v_posix.PT_READ_U, tid, off, 0)
            if off == 0:
                return
        self.usize = off + 4

    def platformGetRegs(self):
        """
        Start with what's given by PT_GETREGS and pre-pend
        the debug registers
        """
        tid = self.getMeta("ThreadId", self.getPid())
        buf = LinuxMixin.platformGetRegs(self)
        dbgs = []
        off = self.usize - 32
        for i in range(8):
            r = v_posix.ptrace(v_posix.PT_READ_U, tid, off+(4*i), 0)
            dbgs.append(r & 0xffffffff)

        return struct.pack("8L", *dbgs) + buf

    def platformSetRegs(self, buf):
        """
        Reverse of above...
        """
        tid = self.getMeta("ThreadId", self.getPid())

        x = create_string_buffer(buf[32:])
        if v_posix.ptrace(PT_SETREGS, tid, 0, addressof(x)) != 0:
            raise Exception("ERROR ptrace PT_SETREGS failed!")

        dbgs = struct.unpack("8L", buf[:32])
        off = self.usize - 32
        for i in range(8):
            v_posix.ptrace(v_posix.PT_WRITE_U, tid, off+(4*i), dbgs[i])

    def getRegisterFormat(self):
        return "15L8H2L2H2L2H"

    def getRegisterNames(self):
        return (
            "debug0","debug1","debug2","debug3","debug4","debug5",
            "debug6","debug7",
            "ebx","ecx","edx","esi","edi","ebp","eax","ds","__ds",
            "es","__es","fs","__fs","gs","__gs","orig_eax","eip",
            "cs","__cs","eflags","esp","ss","__ss")

class LinuxAmd64Registers:
    """
    Mixin for the register format on Linux AMD64
    """
    def initMixin(self):
        pass

    def getRegisterFormat(self):
        return "27L"

    def getRegisterNames(self):
        return (
            "r15","r14","r13","r12","rbp","rbx","r11","r10",
            "r9","r8","rax","rcx","rdx","rsi","rdi","orig_rax",
            "rip","cs","eflags",
            "rsp","ss",
            "fs_base"," gs_base",
            "ds","es","fs","gs")


########NEW FILE########
__FILENAME__ = posix
"""
Posix Signaling Module
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import sys
import os
import struct
import signal
import platform

import vtrace
import vtrace.symbase as symbase
import vtrace.util as v_util
import Elf
from ctypes import *
import ctypes.util as cutil


libc = None

class PosixMixin:

    """
    A mixin for systems which use POSIX signals and
    things like wait()
    """

    def initMixin(self):
        """
        Setup for the fact that we support signal driven
        debugging on posix platforms
        """
        self.stepping = False # Set this on stepi to diff the TRAP
        self.execing  = False # Set this on exec to diff the TRAP
        self.pthreads = None  # Some platforms make a pthread list

    def platformKill(self):
        self.sendSignal(signal.SIGKILL)

    def sendSignal(self, signo):
        self.requireAttached()
        os.kill(self.pid, signo)

    def platformSendBreak(self):
        self.sendSignal(signal.SIGTRAP) # FIXME maybe change to SIGSTOP

    def posixLibraryLoadHack(self):
        """
        Posix systems don't have library load events, so
        fake it out here... (including pre-populating the
        entire known library bases metadata
        """
        # GHETTO: just look for magic based on binary
        magix = ["\x7fELF",]
        done = []
        for addr,size,perms,fname in self.getMaps():
            if fname in done:
                continue
            done.append(fname)
            if perms & vtrace.MM_READ:
                try:
                    buf = self.readMemory(addr, 20)
                    for m in magix:
                        if buf.find(m) == 0:
                            self.addLibraryBase(fname, addr)
                            break
                except: #FIXME why can't i read all maps?
                    pass

    def platformWait(self):
        pid, status = os.waitpid(self.pid,0)
        return status

    def handleAttach(self):
        self.fireNotifiers(vtrace.NOTIFY_ATTACH)
        self.posixLibraryLoadHack()
        # We'll emulate windows here and send an additional
        # break after our library load events to make things easy
        self.fireNotifiers(vtrace.NOTIFY_BREAK)

    def platformProcessEvent(self, status):

        if os.WIFEXITED(status):
            self.setMeta("ExitCode", os.WEXITSTATUS(status))
            tid = self.getMeta("ThreadId", -1)
            if tid != self.getPid():
                # Set the selected thread ID to the pid cause
                # the old one's invalid
                if self.pthreads != None:
                    self.pthreads.remove(tid)
                self.setMeta("ThreadId", self.getPid())
                self.setMeta("ExitThread", tid)
                self.fireNotifiers(vtrace.NOTIFY_EXIT_THREAD)
            else:
                self.fireNotifiers(vtrace.NOTIFY_EXIT)

        elif os.WIFSIGNALED(status):
            self.setMeta("ExitCode", os.WTERMSIG(status))
            self.fireNotifiers(vtrace.NOTIFY_EXIT)

        elif os.WIFSTOPPED(status):
            sig = os.WSTOPSIG(status)
            self.handlePosixSignal(sig)

        else:
            print "OMG WTF JUST HAPPENED??!?11/!?1?>!"

    def handlePosixSignal(self, sig):
        """
        Handle a basic posix signal for this trace.  This was seperated from
        platformProcessEvent so extenders could skim events and still use this logic.
        """
        if sig == signal.SIGTRAP:

            # Traps on posix systems are a little complicated
            if self.stepping:
                self.stepping = False
                self.fireNotifiers(vtrace.NOTIFY_STEP)

            elif self.checkBreakpoints():
                # It was either a known BP or a sendBreak()
                return

            elif self.execing:
                self.execing = False
                self.handleAttach()

            else:
                self.setMeta("PendingSignal", sig)
                self.fireNotifiers(vtrace.NOTIFY_SIGNAL)

        elif sig == signal.SIGSTOP:
            self.handleAttach()

        else:
            self.setMeta("PendingSignal", sig)
            self.fireNotifiers(vtrace.NOTIFY_SIGNAL)

class ElfSymbolResolver(symbase.VSymbolResolver):
    def parseBinary(self):
        typemap = {
            Elf.STT_FUNC:vtrace.SYM_FUNCTION,
            Elf.STT_SECTION:vtrace.SYM_SECTION,
            Elf.STT_OBJECT:vtrace.SYM_GLOBAL
        }

        elf = Elf.Elf(self.filename)
        base = self.loadbase

        # Quick pass to see if we need to assume prelink
        for sec in elf.sections:
            if sec.name != ".text":
                continue
            # Try to detect prelinked
            if sec.sh_addr != sec.sh_offset:
                base = 0
            break

        for sec in elf.sections:
            self.addSymbol(sec.name, sec.sh_addr+base, sec.sh_size, vtrace.SYM_SECTION)

        for sym in elf.symbols:
            self.addSymbol(sym.name, sym.st_value+base, sym.st_size, typemap.get((sym.st_info & 0xf),vtrace.SYM_MISC) )

        for sym in elf.dynamic_symbols:
            self.addSymbol(sym.name, sym.st_value+base, sym.st_size, typemap.get((sym.st_info & 0xf),vtrace.SYM_MISC) )


class ElfMixin:
    """
    A platform mixin to parse Elf binaries
    """
    def platformGetSymbolResolver(self, filename, baseaddr):
        return ElfSymbolResolver(filename, baseaddr)


# As much as I would *love* if all the ptrace defines were the same all the time,
# there seem to be small platform differences...
# These are the ones upon which most agree
PT_TRACE_ME     = 0   # child declares it's being traced */
PT_READ_I       = 1   # read word in child's I space */
PT_READ_D       = 2   # read word in child's D space */
PT_READ_U       = 3   # read word in child's user structure */
PT_WRITE_I      = 4   # write word in child's I space */
PT_WRITE_D      = 5   # write word in child's D space */
PT_WRITE_U      = 6   # write word in child's user structure */
PT_CONTINUE     = 7   # continue the child */
PT_KILL         = 8   # kill the child process */
PT_STEP         = 9   # single step the child */

platform = platform.system()
if platform == "Darwin":
    PT_ATTACH       = 10  # trace some running process */
    PT_DETACH       = 11  # stop tracing a process */
    PT_SIGEXC       = 12  # signals as exceptions for current_proc */
    PT_THUPDATE     = 13  # signal for thread# */
    PT_ATTACHEXC    = 14  # attach to running process with signal exception */
    PT_FORCEQUOTA   = 30  # Enforce quota for root */
    PT_DENY_ATTACH  = 31
    PT_FIRSTMACH    = 32  # for machine-specific requests */

def ptrace(code, pid, addr, data):
    """
    The contents of this call are basically cleanly
    passed to the libc implementation of ptrace.
    """
    global libc
    if not libc:
        cloc = cutil.find_library("c")
        if not cloc:
            raise Exception("ERROR: can't find C library on posix system!")
        libc = CDLL(cloc)
    return libc.ptrace(code, pid, addr, data)

#def waitpid(pid, status, options):
    #global libc
    #if not libc:
        #cloc = cutil.find_library("c")
        #if not cloc:
            #raise Exception("ERROR: can't find C library on posix system!")
        #libc = CDLL(cloc)
    #return libc.waitpid(pid, status, options)

class PtraceMixin:
    """
    A platform mixin for using the ptrace functions
    to attach/detach/continue/stepi etc. Many *nix systems
    will probably use this...

    NOTE: if you get a PT_FOO undefined, it *probably* means that
    the PT_FOO macro isn't defined for that platform (which means
    it need to be done another way like PT_GETREGS on darwin doesn't
    exist... but the darwin mixin over-rides platformGetRegs)
    """

    def initMixin(self):
        """
        Setup supported modes
        """

        self.conthack = 0
        if sys.platform == "darwin":
            self.conthack = 1

        # Make a worker thread do these for us...
        self.threadWrap("platformGetRegs", self.platformGetRegs)
        self.threadWrap("platformSetRegs", self.platformSetRegs)
        self.threadWrap("platformAttach", self.platformAttach)
        self.threadWrap("platformDetach", self.platformDetach)
        self.threadWrap("platformStepi", self.platformStepi)
        self.threadWrap("platformContinue", self.platformContinue)
        self.threadWrap("platformWriteMemory", self.platformWriteMemory)
        self.threadWrap("platformExec", self.platformExec)

    # copied from FreeBSDMixin
    def platformAttach(self, pid):
        if ptrace(PT_ATTACH, pid, 0, 0) != 0:
            raise Exception("Ptrace Attach Failed")

    def platformExec(self, cmdline):
        self.execing = True
        cmdlist = v_util.splitargs(cmdline)
        os.stat(cmdlist[0])
        pid = os.fork()
        if pid == 0:
            ptrace(PT_TRACE_ME, 0, 0, 0)
            os.execv(cmdlist[0], cmdlist)
            sys.exit(-1)
        return pid

    def platformWriteMemory(self, address, bytes):
        wordsize = len(struct.pack("P",0))
        remainder = len(bytes) % wordsize

        if remainder:
            pad = self.readMemory(address+(len(bytes)-remainder), wordsize)
            bytes += pad[remainder:]

        for i in range(len(bytes)/wordsize):
            offset = wordsize*i
            dword = struct.unpack("L",bytes[offset:offset+wordsize])[0]
            if ptrace(PT_WRITE_D, self.pid, long(address+offset), long(dword)) != 0:
                raise Exception("ERROR ptrace PT_WRITE_D failed!")



########NEW FILE########
__FILENAME__ = solaris
"""
Solaris Platform Module (Incomplete)
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import os
import struct
import array

# Control codes (long values) for messages written to ctl and lwpctl files.
PCNULL   = 0L# null request, advance to next message */
PCSTOP   = 1L# direct process or lwp to stop and wait for stop */
PCDSTOP  = 2L# direct process or lwp to stop */
PCWSTOP  = 3L# wait for process or lwp to stop, no timeout */
PCTWSTOP = 4L# wait for stop, with long millisecond timeout arg */
PCRUN    = 5L# make process/lwp runnable, w/ long flags argument */
PCCSIG   = 6L# clear current signal from lwp */
PCCFAULT = 7L# clear current fault from lwp */
PCSSIG   = 8L# set current signal from siginfo_t argument */
PCKILL   = 9L# post a signal to process/lwp, long argument */
PCUNKILL = 10L# delete a pending signal from process/lwp, long arg */
PCSHOLD  = 11L# set lwp signal mask from sigset_t argument */
PCSTRACE = 12L# set traced signal set from sigset_t argument */
PCSFAULT = 13L# set traced fault set from fltset_t argument */
PCSENTRY = 14L# set traced syscall entry set from sysset_t arg */
PCSEXIT  = 15L# set traced syscall exit set from sysset_t arg */
PCSET    = 16L# set modes from long argument */
PCUNSET  = 17L# unset modes from long argument */
PCSREG   = 18L# set lwp general registers from prgregset_t arg */
PCSFPREG = 19L# set lwp floating-point registers from prfpregset_t */
PCSXREG  = 20L# set lwp extra registers from prxregset_t arg */
PCNICE   = 21L# set nice priority from long argument */
PCSVADDR = 22L# set %pc virtual address from long argument */
PCWATCH  = 23L# set/unset watched memory area from prwatch_t arg */
PCAGENT  = 24L# create agent lwp with regs from prgregset_t arg */
PCREAD   = 25L# read from the address space via priovec_t arg */
PCWRITE  = 26L# write to the address space via priovec_t arg */
PCSCRED  = 27L# set process credentials from prcred_t argument */
PCSASRS  = 28L# set ancillary state registers from asrset_t arg */
PCSPRIV  = 29L# set process privileges from prpriv_t argument */
PCSZONE  = 30L# set zoneid from zoneid_t argument */
PCSCREDX = 31L# as PCSCRED but with supplemental groups */

# PCRUN long operand flags.
PRCSIG   = 0x01# clear current signal, if any */
PRCFAULT = 0x02# clear current fault, if any */
PRSTEP   = 0x04# direct the lwp to single-step */
PRSABORT = 0x08# abort syscall, if in syscall */
PRSTOP   = 0x10# set directed stop request */

# Status flags
PR_STOPPED  = 0x00000001# lwp is stopped */
PR_ISTOP    = 0x00000002# lwp is stopped on an event of interest */
PR_DSTOP    = 0x00000004# lwp has a stop directive in effect */
PR_STEP     = 0x00000008# lwp has a single-step directive in effect */
PR_ASLEEP   = 0x00000010# lwp is sleeping in a system call */
PR_PCINVAL  = 0x00000020# contents of pr_instr undefined */
PR_ASLWP    = 0x00000040# obsolete flag; never set */
PR_AGENT    = 0x00000080# this lwp is the /proc agent lwp */
PR_DETACH   = 0x00000100# this is a detached lwp */
PR_DAEMON   = 0x00000200# this is a daemon lwp */
# The following flags apply to the process, not to an individual lwp */
PR_ISSYS    = 0x00001000# this is a system process */
PR_VFORKP   = 0x00002000# process is the parent of a vfork()d child */
PR_ORPHAN   = 0x00004000# process's process group is orphaned */
# The following process flags are modes settable by PCSET/PCUNSET */
PR_FORK     = 0x00100000# inherit-on-fork is in effect */
PR_RLC      = 0x00200000# run-on-last-close is in effect */
PR_KLC      = 0x00400000# kill-on-last-close is in effect */
PR_ASYNC    = 0x00800000# asynchronous-stop is in effect */
PR_MSACCT   = 0x01000000# micro-state usage accounting is in effect */
PR_BPTADJ   = 0x02000000# breakpoint trap pc adjustment is in effect */
PR_PTRACE   = 0x04000000# ptrace-compatibility mode is in effect */
PR_MSFORK   = 0x08000000# micro-state accounting inherited on fork */
PR_IDLE     = 0x10000000# lwp is a cpu's idle thread */


# Permissions...
MA_READ    = 0x04# readable by the traced process */
MA_WRITE   = 0x02# writable by the traced process */
MA_EXEC    = 0x01# executable by the traced process */
MA_SHARED  = 0x08# changes are shared by mapped object */
MA_ANON    = 0x40# anonymous memory (e.g. /dev/zero) */
MA_ISM     = 0x80# intimate shared mem (shared MMU resources) */
MA_NORESERVE = 0x100# mapped with MAP_NORESERVE */
MA_SHM     = 0x200# System V shared memory */
MA_RESERVED1 = 0x400# reserved for future use */

class SolarisMixin:

    def initMixin(self):
        #import sunprocfs
        self.threadWrap("platformContinue", self.platformContinue)
        self.ctl = None

    def platformGetRegs(self):
        pid = self.getPid()

    #def platformGetThreads(self):
        #ret = []
        #for name in os.listdir("/proc/%d/lwp" % self.pid):
            #ret.append(int(name))
        #return ret

    def platformAttach(self, pid):
        self.ctl = file("/proc/%d/ctl" % pid, "ab")
        self.ctl.write(struct.pack("<L", PRSTOP))

    def platformContinue(self):
        """
        Tell the process to continue running
        """
        self.writeCtl(struct.pack("<LL", PCRUN, 0))

    def platformWait(self):
        """
        wait for the process to do someting "interesting"
        """
        self.writeCtl(struct.pack("<L", PCWSTOP))
        bytes = file("/proc/%d/psinfo" % self.pid, "rb").read()
        return bytes

    def writeCtl(self, bytes):
        os.write(self.ctl.fileno(), bytes)

    def platformDetach(self):
        print "SOLARIS DETACH"
        self.ctl.close()
        self.ctl = None

class SolarisIntelMixin:
    """
    Handle register formats for the intel solaris stuff
    """
    def getRegisterFormat(self):
        return ""

    def getRegisterNames(self):
        return []

    def platformReadMemory(self, addr, size):
        a = array.array('c',"\x00" * size)
        baddr, blen = a.buffer_info()
        priovec = struct.pack("<4L",PCREAD, baddr, blen, addr)
        print repr(priovec)
        self.writeCtl(priovec)
        return a.tostring()

    def platformWriteMemory(self, addr, bytes):
        a = array.array('c',bytes)
        baddr,blen = a.buffer_info()
        priovec = struct.pack("<LLLL", PCWRITE, baddr, blen, addr)
        self.writeCtl(priovec)

    def platformGetMaps(self):
        ret = []
        pid = self.getPid()
        mapdata = file("/proc/%d/map" % pid, "rb").read()
        while mapdata:
            addr,size = struct.unpack("<LL", mapdata[:8])
            perms, = struct.unpack("<L", mapdata[80:84])
            perms = perms & 0x7
            ret.append((addr,size, perms, ""))
            mapdata = mapdata[96:]
        return ret


########NEW FILE########
__FILENAME__ = win32
"""
Win32 Platform Module
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import os
import sys
import struct
import traceback
import platform

import PE

import vtrace
import vtrace.symbase as symbase

from ctypes import *
#from ctypes.wintypes import *

platdir = os.path.dirname(__file__)

kernel32 = None
dbghelp = None
psapi = None
ntdll = None
advapi32 = None

# All platforms must be able to import this module (for exceptions etc..)
if sys.platform == "win32":
    kernel32 = windll.kernel32
    ntdll = windll.ntdll
    psapi = windll.psapi
    dbghelp = windll.LoadLibrary(os.path.join(platdir, "dbghelp.dll"))
    advapi32 = windll.advapi32

INFINITE = 0xffffffff
EXCEPTION_MAXIMUM_PARAMETERS = 15

# Debug Event Types
EXCEPTION_DEBUG_EVENT       =1
CREATE_THREAD_DEBUG_EVENT   =2
CREATE_PROCESS_DEBUG_EVENT  =3
EXIT_THREAD_DEBUG_EVENT     =4
EXIT_PROCESS_DEBUG_EVENT    =5
LOAD_DLL_DEBUG_EVENT        =6
UNLOAD_DLL_DEBUG_EVENT      =7
OUTPUT_DEBUG_STRING_EVENT   =8
RIP_EVENT                   =9

# Symbol Flags
SYMFLAG_VALUEPRESENT     = 0x00000001
SYMFLAG_REGISTER         = 0x00000008
SYMFLAG_REGREL           = 0x00000010
SYMFLAG_FRAMEREL         = 0x00000020
SYMFLAG_PARAMETER        = 0x00000040
SYMFLAG_LOCAL            = 0x00000080
SYMFLAG_CONSTANT         = 0x00000100
SYMFLAG_EXPORT           = 0x00000200
SYMFLAG_FORWARDER        = 0x00000400
SYMFLAG_FUNCTION         = 0x00000800
SYMFLAG_VIRTUAL          = 0x00001000
SYMFLAG_THUNK            = 0x00002000
SYMFLAG_TLSREL           = 0x00004000



# Symbol Resolution Options
SYMOPT_CASE_INSENSITIVE         = 0x00000001
SYMOPT_UNDNAME                  = 0x00000002
SYMOPT_DEFERRED_LOADS           = 0x00000004
SYMOPT_NO_CPP                   = 0x00000008
SYMOPT_LOAD_LINES               = 0x00000010
SYMOPT_OMAP_FIND_NEAREST        = 0x00000020
SYMOPT_LOAD_ANYTHING            = 0x00000040
SYMOPT_IGNORE_CVREC             = 0x00000080
SYMOPT_NO_UNQUALIFIED_LOADS     = 0x00000100
SYMOPT_FAIL_CRITICAL_ERRORS     = 0x00000200
SYMOPT_EXACT_SYMBOLS            = 0x00000400
SYMOPT_ALLOW_ABSOLUTE_SYMBOLS   = 0x00000800
SYMOPT_IGNORE_NT_SYMPATH        = 0x00001000
SYMOPT_INCLUDE_32BIT_MODULES    = 0x00002000
SYMOPT_PUBLICS_ONLY             = 0x00004000
SYMOPT_NO_PUBLICS               = 0x00008000
SYMOPT_AUTO_PUBLICS             = 0x00010000
SYMOPT_NO_IMAGE_SEARCH          = 0x00020000
SYMOPT_SECURE                   = 0x00040000
SYMOPT_NO_PROMPTS               = 0x00080000
SYMOPT_DEBUG                    = 0x80000000

# Exception Types
EXCEPTION_WAIT_0                     = 0x00000000L    
EXCEPTION_ABANDONED_WAIT_0           = 0x00000080L    
EXCEPTION_USER_APC                   = 0x000000C0L    
EXCEPTION_TIMEOUT                    = 0x00000102L    
EXCEPTION_PENDING                    = 0x00000103L    
DBG_EXCEPTION_HANDLED             = 0x00010001L    
DBG_CONTINUE                      = 0x00010002L    
EXCEPTION_SEGMENT_NOTIFICATION       = 0x40000005L    
DBG_TERMINATE_THREAD              = 0x40010003L    
DBG_TERMINATE_PROCESS             = 0x40010004L    
DBG_CONTROL_C                     = 0x40010005L    
DBG_CONTROL_BREAK                 = 0x40010008L    
DBG_COMMAND_EXCEPTION             = 0x40010009L    
EXCEPTION_GUARD_PAGE_VIOLATION       = 0x80000001L    
EXCEPTION_DATATYPE_MISALIGNMENT      = 0x80000002L    
EXCEPTION_BREAKPOINT                 = 0x80000003L    
EXCEPTION_SINGLE_STEP                = 0x80000004L    
DBG_EXCEPTION_NOT_HANDLED         = 0x80010001L    
EXCEPTION_ACCESS_VIOLATION           = 0xC0000005L    
EXCEPTION_IN_PAGE_ERROR              = 0xC0000006L    
EXCEPTION_INVALID_HANDLE             = 0xC0000008L    
EXCEPTION_NO_MEMORY                  = 0xC0000017L    
EXCEPTION_ILLEGAL_INSTRUCTION        = 0xC000001DL    
EXCEPTION_NONCONTINUABLE_EXCEPTION   = 0xC0000025L    
EXCEPTION_INVALID_DISPOSITION        = 0xC0000026L    
EXCEPTION_ARRAY_BOUNDS_EXCEEDED      = 0xC000008CL    
EXCEPTION_FLOAT_DENORMAL_OPERAND     = 0xC000008DL    
EXCEPTION_FLOAT_DIVIDE_BY_ZERO       = 0xC000008EL    
EXCEPTION_FLOAT_INEXACT_RESULT       = 0xC000008FL    
EXCEPTION_FLOAT_INVALID_OPERATION    = 0xC0000090L    
EXCEPTION_FLOAT_OVERFLOW             = 0xC0000091L    
EXCEPTION_FLOAT_STACK_CHECK          = 0xC0000092L    
EXCEPTION_FLOAT_UNDERFLOW            = 0xC0000093L    
EXCEPTION_INTEGER_DIVIDE_BY_ZERO     = 0xC0000094L    
EXCEPTION_INTEGER_OVERFLOW           = 0xC0000095L    
EXCEPTION_PRIVILEGED_INSTRUCTION     = 0xC0000096L    
EXCEPTION_STACK_OVERFLOW             = 0xC00000FDL    
EXCEPTION_CONTROL_C_EXIT             = 0xC000013AL    
EXCEPTION_FLOAT_MULTIPLE_FAULTS      = 0xC00002B4L    
EXCEPTION_FLOAT_MULTIPLE_TRAPS       = 0xC00002B5L    
EXCEPTION_REG_NAT_CONSUMPTION        = 0xC00002C9L    

# Context Info
CONTEXT_i386    = 0x00010000    # this assumes that i386 and
CONTEXT_i486    = 0x00010000    # i486 have identical context records
CONTEXT_CONTROL         = (CONTEXT_i386 | 0x00000001L) # SS:SP, CS:IP, FLAGS, BP
CONTEXT_INTEGER         = (CONTEXT_i386 | 0x00000002L) # AX, BX, CX, DX, SI, DI
CONTEXT_SEGMENTS        = (CONTEXT_i386 | 0x00000004L) # DS, ES, FS, GS
CONTEXT_FLOATING_POINT  = (CONTEXT_i386 | 0x00000008L) # 387 state
CONTEXT_DEBUG_REGISTERS = (CONTEXT_i386 | 0x00000010L) # DB 0-3,6,7
CONTEXT_EXTENDED_REGISTERS  = (CONTEXT_i386 | 0x00000020L) # cpu specific extensions
CONTEXT_FULL = (CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS)
CONTEXT_ALL = (CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS | CONTEXT_FLOATING_POINT | CONTEXT_DEBUG_REGISTERS | CONTEXT_EXTENDED_REGISTERS)

# Thread Permissions
THREAD_ALL_ACCESS = 0x001f03ff
PROCESS_ALL_ACCESS = 0x001f0fff

# Memory Permissions
PAGE_NOACCESS = 0x01
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100
PAGE_NOCACHE = 0x200
PAGE_WRITECOMBINE = 0x400

# Memory States
MEM_COMMIT = 0x1000
MEM_FREE = 0x10000
MEM_RESERVE = 0x2000

# Memory Types
MEM_IMAGE = 0x1000000
MEM_MAPPED = 0x40000
MEM_PRIVATE = 0x20000

# Process Creation Flags
DEBUG_ONLY_THIS_PROCESS = 0x02

MAX_PATH=260

class EXCEPTION_RECORD(Structure):
    _fields_ = [
            ("ExceptionCode", c_ulong),
            ("ExceptionFlags", c_ulong),
            ("ExceptionRecord", c_ulong),
            ("ExceptionAddress", c_ulong), # Aparently c_void_p can be None
            ("NumberParameters", c_ulong),
            ("ExceptionInformation", c_ulong * EXCEPTION_MAXIMUM_PARAMETERS)
            ]

class EXCEPTION_DEBUG_INFO(Structure):
    _fields_ = [
            ("ExceptionRecord", EXCEPTION_RECORD),
            ("FirstChance", c_ulong)
            ]
class CREATE_THREAD_DEBUG_INFO(Structure):
    _fields_ = [
            ("Thread", c_ulong),
            ("ThreadLocalBase", c_ulong),
            ("StartAddress", c_ulong)
            ]
class CREATE_PROCESS_DEBUG_INFO(Structure):
    _fields_ = [
            ("File", c_ulong), # HANDLE 
            ("Process", c_ulong), # HANDLE
            ("Thread", c_ulong), # HANDLE
            ("BaseOfImage", c_ulong),
            ("DebugInfoFileOffset", c_ulong),
            ("DebugInfoSize", c_ulong),
            ("ThreadLocalBase", c_ulong),
            ("StartAddress", c_ulong),
            ("ImageName", c_ulong),
            ("Unicode", c_short),
            ]
class EXIT_THREAD_DEBUG_INFO(Structure):
    _fields_ = [("ExitCode", c_ulong),]
class EXIT_PROCESS_DEBUG_INFO(Structure):
    _fields_ = [("ExitCode", c_ulong),]
class LOAD_DLL_DEBUG_INFO(Structure):
    _fields_ = [
            ("File", c_ulong), #HANDLE
            ("BaseOfDll", c_ulong),
            ("DebugInfoFileOffset", c_ulong),
            ("DebugInfoSize", c_ulong),
            ("ImageName", c_ulong),
            ("Unicode", c_ushort),
            ]
class UNLOAD_DLL_DEBUG_INFO(Structure):
    _fields_ = [
            ("BaseOfDll", c_ulong),
            ]
class OUTPUT_DEBUG_STRING_INFO(Structure):
    _fields_ = [
            ("DebugStringData", c_ulong), #FIXME 64bit
            ("Unicode", c_ushort),
            ("DebugStringLength", c_ushort),
            ]
class RIP_INFO(Structure):
    _fields_ = [
            ("Error", c_ulong),
            ("Type", c_ulong),
            ]

class DBG_EVENT_UNION(Union):
    _fields_ = [ ("Exception",EXCEPTION_DEBUG_INFO),
                 ("CreateThread", CREATE_THREAD_DEBUG_INFO),
                 ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
                 ("ExitThread", EXIT_THREAD_DEBUG_INFO),
                 ("ExitProcess", EXIT_PROCESS_DEBUG_INFO),
                 ("LoadDll", LOAD_DLL_DEBUG_INFO),
                 ("UnloadDll", UNLOAD_DLL_DEBUG_INFO),
                 ("DebugString", OUTPUT_DEBUG_STRING_INFO),
                 ("RipInfo", RIP_INFO)]

class DEBUG_EVENT(Structure):
    _fields_ = [
            ("DebugEventCode", c_ulong),
            ("ProcessId", c_ulong),
            ("ThreadId", c_ulong),
            ("u", DBG_EVENT_UNION),
            ]

class FloatSavex86(Structure):
    _fields_ = [("ControlWord", c_ulong),
                  ("StatusWord", c_ulong),
                  ("TagWord", c_ulong),
                  ("ErrorOffset", c_ulong),
                  ("ErrorSelector", c_ulong),
                  ("DataOffset", c_ulong),
                  ("DataSelector", c_ulong),
                  ("RegisterSave", c_byte*80),
                  ("Cr0NpxState", c_ulong),
                  ]

class CONTEXTx86(Structure):
    _fields_ = [ ("ContextFlags", c_ulong),
                   ("Dr0", c_ulong),
                   ("Dr1", c_ulong),
                   ("Dr2", c_ulong),
                   ("Dr3", c_ulong),
                   ("Dr4", c_ulong),
                   ("Dr5", c_ulong),
                   ("Dr6", c_ulong),
                   ("Dr7", c_ulong),
                   ("FloatSave", FloatSavex86),
                   ("SegGs", c_ulong),
                   ("SegFs", c_ulong),
                   ("SegEs", c_ulong),
                   ("SegDs", c_ulong),
                   ("edi", c_ulong),
                   ("esi", c_ulong),
                   ("ebx", c_ulong),
                   ("edx", c_ulong),
                   ("ecx", c_ulong),
                   ("eax", c_ulong),
                   ("ebp", c_ulong),
                   ("eip", c_ulong),
                   ("SegCs", c_ulong),
                   ("eflags", c_ulong),
                   ("esp", c_ulong),
                   ("SegSs", c_ulong),
                   ("Extension", c_byte * 512),
                   ]

class MEMORY_BASIC_INFORMATION32(Structure):
    _fields_ = [
        ("BaseAddress", c_ulong),
        ("AllocationBase", c_ulong),
        ("AllocationProtect", c_ulong),
        ("RegionSize", c_ulong),
        ("State", c_ulong),
        ("Protect", c_ulong),
        ("Type", c_ulong),
        ]

class MEMORY_BASIC_INFORMATION64(Structure):
    _fields_ = [
        ("BaseAddress", c_ulonglong),
        ("AllocationBase", c_ulonglong),
        ("AllocationProtect", c_ulong),
        ("alignment1", c_ulong),
        ("RegionSize", c_ulonglong),
        ("State", c_ulong),
        ("Protect", c_ulong),
        ("Type", c_ulong),
        ("alignment2", c_ulong),
        ]

class STARTUPINFO(Structure):
    """
    Passed into CreateProcess
    """
    _fields_ = [
            ("db", c_ulong),
            ("Reserved", c_char_p),
            ("Desktop", c_char_p),
            ("Title", c_char_p),
            ("X", c_ulong),
            ("Y", c_ulong),
            ("XSize", c_ulong),
            ("YSize", c_ulong),
            ("XCountChars", c_ulong),
            ("YCountChars", c_ulong),
            ("FillAttribute", c_ulong),
            ("Flags", c_ulong),
            ("ShowWindow", c_ushort),
            ("Reserved2", c_ushort),
            ("Reserved3", c_void_p),
            ("StdInput", c_ulong),
            ("StdOutput", c_ulong),
            ("StdError", c_ulong),
            ]

class PROCESS_INFORMATION(Structure):
    _fields_ = [
            ("Process", c_ulong),
            ("Thread", c_ulong),
            ("ProcessId", c_ulong),
            ("ThreadId", c_ulong),
            ]

class SYMBOL_INFO(Structure):
    _fields_ = [
                ("SizeOfStruct", c_ulong),
                ("TypeIndex", c_ulong),
                ("Reserved1", c_ulonglong),
                ("Reserved2", c_ulonglong),
                ("Index", c_ulong),
                ("Size", c_ulong),
                ("ModBase", c_ulonglong),
                ("Flags", c_ulong),
                ("Value", c_ulonglong),
                ("Address", c_ulonglong),
                ("Register", c_ulong),
                ("Scope", c_ulong),
                ("Tag", c_ulong),
                ("NameLen", c_ulong),
                ("MaxNameLen", c_ulong),
                ("Name", c_char * 2000), # MAX_SYM_NAME
                ]

class IMAGEHLP_MODULE64(Structure):
    _fields_ = [
            ("SizeOfStruct", c_ulong),
            ("BaseOfImage", c_ulonglong),
            ("ImageSize", c_ulong),
            ("TimeDateStamp", c_ulong),
            ("CheckSum", c_ulong),
            ("NumSyms", c_ulong),
            ("SymType", c_ulong),
            ("ModuleName", c_char*32),
            ("ImageName", c_char*256),
            ("LoadedImageName", c_char*256),
            ("LoadedPdbName", c_char*256),
            ("CvSig", c_ulong),
            ("CvData", c_char*(MAX_PATH*3)),
            ("PdbSig", c_ulong),
            ("PdbSig70", c_char * 16), #GUID
            ("PdbAge", c_ulong),
            ("PdbUnmatched", c_ulong),
            ("DbgUnmatched", c_ulong),
            ("LineNumbers", c_ulong),
            ("GlobalSymbols", c_ulong),
            ("TypeInfo", c_ulong),
            ]


IMAGE_DIRECTORY_ENTRY_EXPORT          =0   # Export Directory
IMAGE_DIRECTORY_ENTRY_IMPORT          =1   # Import Directory
IMAGE_DIRECTORY_ENTRY_RESOURCE        =2   # Resource Directory
IMAGE_DIRECTORY_ENTRY_EXCEPTION       =3   # Exception Directory
IMAGE_DIRECTORY_ENTRY_SECURITY        =4   # Security Directory
IMAGE_DIRECTORY_ENTRY_BASERELOC       =5   # Base Relocation Table
IMAGE_DIRECTORY_ENTRY_DEBUG           =6   # Debug Directory
IMAGE_DIRECTORY_ENTRY_COPYRIGHT       =7   # (X86 usage)
IMAGE_DIRECTORY_ENTRY_ARCHITECTURE    =7   # Architecture Specific Data
IMAGE_DIRECTORY_ENTRY_GLOBALPTR       =8   # RVA of GP
IMAGE_DIRECTORY_ENTRY_TLS             =9   # TLS Directory
IMAGE_DIRECTORY_ENTRY_LOAD_CONFIG    =10   # Load Configuration Directory
IMAGE_DIRECTORY_ENTRY_BOUND_IMPORT   =11   # Bound Import Directory in headers
IMAGE_DIRECTORY_ENTRY_IAT            =12   # Import Address Table
IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT   =13   # Delay Load Import Descriptors
IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR =14   # COM Runtime descriptor

IMAGE_DEBUG_TYPE_UNKNOWN          =0
IMAGE_DEBUG_TYPE_COFF             =1
IMAGE_DEBUG_TYPE_CODEVIEW         =2
IMAGE_DEBUG_TYPE_FPO              =3
IMAGE_DEBUG_TYPE_MISC             =4
IMAGE_DEBUG_TYPE_EXCEPTION        =5
IMAGE_DEBUG_TYPE_FIXUP            =6
IMAGE_DEBUG_TYPE_OMAP_TO_SRC      =7
IMAGE_DEBUG_TYPE_OMAP_FROM_SRC    =8
IMAGE_DEBUG_TYPE_BORLAND          =9
IMAGE_DEBUG_TYPE_RESERVED10       =10
IMAGE_DEBUG_TYPE_CLSID            =11

SSRVOPT_CALLBACK            = 0x0001
SSRVOPT_DWORD               = 0x0002
SSRVOPT_DWORDPTR            = 0x0004
SSRVOPT_GUIDPTR             = 0x0008
SSRVOPT_OLDGUIDPTR          = 0x0010
SSRVOPT_UNATTENDED          = 0x0020
SSRVOPT_NOCOPY              = 0x0040
SSRVOPT_PARENTWIN           = 0x0080
SSRVOPT_PARAMTYPE           = 0x0100
SSRVOPT_SECURE              = 0x0200
SSRVOPT_TRACE               = 0x0400
SSRVOPT_SETCONTEXT          = 0x0800
SSRVOPT_PROXY               = 0x1000
SSRVOPT_DOWNSTREAM_STORE    = 0x2000

class IMAGE_DEBUG_DIRECTORY(Structure):
    _fields_ = [
            ("Characteristics", c_ulong),
            ("TimeDateStamp", c_ulong),
            ("MajorVersion", c_ushort),
            ("MinorVersion", c_ushort),
            ("Type", c_ulong),
            ("SizeOfData", c_ulong),
            ("AddressOfRawData", c_ulong),
            ("PointerToRawData", c_ulong),
            ]

NT_LIST_HANDLES = 16

class SYSTEM_HANDLE(Structure):
    _fields_ = [
    ('ProcessID'        , c_ulong),
    ('HandleType'       , c_byte),
    ('Flags'            , c_byte),
    ('HandleNumber' , c_ushort),
    ('KernelAddress'    , c_ulong), #FIXME maybe c_ptr?
    ('GrantedAccess'    , c_ulong),
    ]
PSYSTEM_HANDLE = POINTER(SYSTEM_HANDLE)

# OBJECT_INFORMATION_CLASS
ObjectBasicInformation      = 0
ObjectNameInformation       = 1
ObjectTypeInformation       = 2
ObjectAllTypesInformation   = 3
ObjectHandleInformation     = 4

class UNICODE_STRING(Structure):
    _fields_ = (
        ("Length",c_ushort),
        ("MaximumLength", c_ushort),
        ("Buffer", c_wchar_p)
    )
PUNICODE_STRING = POINTER(UNICODE_STRING)

class OBJECT_TYPE_INFORMATION(Structure):
    _fields_ = (
        ("String",UNICODE_STRING),
        ("reserved", c_uint * 22)
    )

object_type_map = {
    "File":vtrace.FD_FILE,
    "Directory":vtrace.FD_FILE,
    "Event":vtrace.FD_EVENT,
    "KeyedEvent":vtrace.FD_EVENT,
    "Mutant":vtrace.FD_LOCK,
    "Semaphore":vtrace.FD_LOCK,
    "Key":vtrace.FD_REGKEY,
    "Port":vtrace.FD_UNKNOWN,
    "Section":vtrace.FD_UNKNOWN,
    "IoCompletion":vtrace.FD_UNKNOWN,
    "Desktop":vtrace.FD_UNKNOWN,
    "WindowStation":vtrace.FD_UNKNOWN,
}

class LUID(Structure):
    _fields_ = (
        ("LowPart", c_ulong),
        ("HighPart", c_ulong)
    )

class TOKEN_PRIVILEGES(Structure):
    # This isn't really universal, more just for one priv use
    _fields_ = (
        ("PrivilegeCount", c_ulong), # Always one
        ("Privilege", LUID),
        ("PrivilegeAttribute", c_ulong)
    )

SE_PRIVILEGE_ENABLED    = 0x00000002
TOKEN_ADJUST_PRIVILEGES = 0x00000020
dbgprivdone = False

def getDebugPrivileges():
    tokprivs = TOKEN_PRIVILEGES()
    dbgluid = LUID()
    token = c_uint(0)

    if not advapi32.LookupPrivilegeValueA(0, "seDebugPrivilege", byref(dbgluid)):
        print "LookupPrivilegeValue Failed: %d" % kernel32.GetLastError()
        return False

    if not advapi32.OpenProcessToken(-1, TOKEN_ADJUST_PRIVILEGES, byref(token)):
        print "OpenProcessToken Failed: %d" % kernel32.GetLastError()
        return False

    tokprivs.PrivilegeCount = 1
    tokprivs.Privilege = dbgluid
    tokprivs.PrivilegeAttribute = SE_PRIVILEGE_ENABLED

    if not advapi32.AdjustTokenPrivileges(token, 0, byref(tokprivs), 0, 0, 0):
        kernel32.CloseHandle(token)
        print "OpenProcessToken Failed: %d" % kernel32.GetLastError()
        return False

def buildSystemHandleInformation(count):
    """
    Dynamically build the structure definition for the
    handle info list.
    """
    class SYSTEM_HANDLE_INFORMATION(Structure):
        _fields_ = [ ('Count', c_ulong), ('Handles', SYSTEM_HANDLE * count), ]
    return SYSTEM_HANDLE_INFORMATION()

def raiseWin32Error(name):
    raise vtrace.PlatformException("Win32 Error %s failed: %s" % (name,kernel32.GetLastError()))

def GetModuleFileNameEx(phandle, mhandle):

    buf = create_unicode_buffer(1024)
    psapi.GetModuleFileNameExW(phandle, mhandle, addressof(buf), 1024)
    return buf.value

class Win32Mixin:
    """
    The main mixin for calling the win32 api's via ctypes
    """

    def initMixin(self):
        self.phandle = None
        self.thandles = {}
        self.win32threads = {}
        self.dosdevs = []
        self.flushcache = False
        global dbgprivdone
        if not dbgprivdone:
            dbgprivdone = getDebugPrivileges()

        # Skip the attach event and plow through to the first
        # injected breakpoint (cause libs are loaded by then)
        self.enableAutoContinue(vtrace.NOTIFY_ATTACH)

        # We only set this when we intend to deliver it
        self.setMeta("PendingException", False)

        self.setupDosDeviceMaps()

        # Setup some win32_ver info in metadata
        rel,ver,csd,ptype = platform.win32_ver()
        self.setMeta("WindowsRelease",rel)
        self.setMeta("WindowsVersion", ver)
        self.setMeta("WindowsCsd", csd)
        self.setMeta("WindowsProcessorType", ptype)

        # These activities *must* all be carried out by the same
        # thread on windows.
        self.threadWrap("platformAttach", self.platformAttach)
        self.threadWrap("platformDetach", self.platformDetach)
        self.threadWrap("platformStepi", self.platformStepi)
        self.threadWrap("platformContinue", self.platformContinue)
        self.threadWrap("platformWait", self.platformWait)
        self.threadWrap("platformGetRegs", self.platformGetRegs)
        self.threadWrap("platformSetRegs", self.platformSetRegs)
        self.threadWrap("platformExec", self.platformExec)

    def platformGetFds(self):
        ret = []
        hinfo = self.getHandles()
        for x in range(hinfo.Count):
            if hinfo.Handles[x].ProcessID != self.pid:
                continue
            hand = hinfo.Handles[x].HandleNumber
            myhand = self.dupHandle(hand)
            typestr = self.getHandleInfo(myhand, ObjectTypeInformation)
            namestr = self.getHandleInfo(myhand, ObjectNameInformation)
            kernel32.CloseHandle(myhand)
            htype = object_type_map.get(typestr, vtrace.FD_UNKNOWN)
            ret.append( (hand, htype, "%s: %s" % (typestr,namestr)) )
        return ret

    def dupHandle(self, handle):
        """
        Duplicate the handle (who's id is in the currently attached
        target process) and return our own copy.
        """
        hret = c_uint(0)
        kernel32.DuplicateHandle(self.phandle, handle,
                                 kernel32.GetCurrentProcess(), byref(hret),
                                 0, False, 2) # DUPLICATE_SAME_ACCESS
        return hret.value

    def getHandleInfo(self, handle, itype=ObjectTypeInformation):

        retSiz = c_uint(0)
        buf = create_string_buffer(100)

        ntdll.NtQueryObject(handle, itype,
                buf, sizeof(buf), byref(retSiz))

        realbuf = create_string_buffer(retSiz.value)

        if ntdll.NtQueryObject(handle, itype,
                realbuf, sizeof(realbuf), byref(retSiz)) == 0:

            uString = cast(realbuf, PUNICODE_STRING).contents
            return uString.Buffer
        return "Unknown"

    def getHandles(self):
        hinfo = buildSystemHandleInformation(1)
        hsize = c_ulong(sizeof(hinfo))

        ntdll.NtQuerySystemInformation(NT_LIST_HANDLES, addressof(hinfo), hsize, addressof(hsize))

        count = (hsize.value-4) / sizeof(SYSTEM_HANDLE)
        hinfo = buildSystemHandleInformation(count)
        hsize = c_ulong(sizeof(hinfo))

        ntdll.NtQuerySystemInformation(NT_LIST_HANDLES, addressof(hinfo), hsize, None)

        return hinfo


    def setupDosDeviceMaps(self):
        self.dosdevs = []
        dname = (c_char * 512)()
        size = kernel32.GetLogicalDriveStringsA(512, addressof(dname))
        devs = dname.raw[:size-1].split("\x00")
        for dev in devs:
            dosname = "%s:" % dev[0]
            kernel32.QueryDosDeviceA("%s:" % dev[0], addressof(dname), 512)
            self.dosdevs.append( (dosname, dname.value) )

    def platformKill(self):
        kernel32.TerminateProcess(self.phandle, 0)

    def getRegisterFormat(self):
        return "51L"

    def getRegisterNames(self):
        return ("ContextFlags","debug0","debug1","debug2","debug3",
                "debug6","debug7","ControlWord","StatusWord","TagWord",
                "ErrorOffset","ErrorSelector","DataOffset","DataSelector",
                # A bunch of float stuff that I'm not parsing just yet..
                "fa0","fa1","fa2","fa3","fa4","fa5","fa6","fa7","fa8","fa9",
                "fa10","fa11","fa12","fa13","fa14","fa15","fa16","fa17","fa18","fa19",
                "Cr0NpxState","gs","fs","es","ds",
                "edi","esi","ebx","edx","ecx","eax","ebp","eip","cs","eflags",
                "esp","ss")

    def platformExec(self, cmdline):
        sinfo = STARTUPINFO()
        pinfo = PROCESS_INFORMATION()
        if not kernel32.CreateProcessA(0, cmdline, 0, 0, 0,
                DEBUG_ONLY_THIS_PROCESS, 0, 0, addressof(sinfo), addressof(pinfo)):
            raise Exception("CreateProcess failed!")

        # When launching an app, we're guaranteed to get a breakpoint
        # Unless we want to fail checkBreakpoints, we'll need to set ShouldBreak
        self.setMeta('ShouldBreak', True)

        return pinfo.ProcessId

    def platformInjectSo(self, filename):
        try:
            lla = self.parseExpression("kernel32.LoadLibraryA")
        except:
            raise Exception("ERROR: symbol kernel32.LoadLibraryA not found!")
        regs = self.platformCall(lla, [filename,])
        if regs == None:
            raise Exception("ERROR: platformCall for LoadLibraryA Failed!")
        return regs.get("eax", 0)
        
    def platformAttach(self, pid):
        if not kernel32.DebugActiveProcess(pid):
            raiseWin32Error("DebugActiveProcess")

    def platformDetach(self):
        # Do the crazy "can't supress exceptions from detach" dance.
        if ((not self.exited) and
            self.getCurrentBreakpoint() != None):
            self.cleanupBreakpoints()
            self.platformContinue()
            self.platformSendBreak()
            self.platformWait()
        if not kernel32.DebugActiveProcessStop(self.pid):
            raiseWin32Error("DebugActiveProcessStop")
        kernel32.CloseHandle(self.phandle)
        self.phandle = None

    def platformAllocateMemory(self, size, perms=vtrace.MM_RWX, suggestaddr=0):
        #FIXME handle permissions
        ret = kernel32.VirtualAllocEx(self.phandle,
                suggestaddr, size, MEM_COMMIT, PAGE_EXECUTE_READWRITE)
        if ret == 0:
            raiseWin32Error("VirtualAllocEx")
        return ret

    def platformReadMemory(self, address, size):
        btype = c_char * size
        buf = btype()
        ret = c_ulong(0)
        if not kernel32.ReadProcessMemory(self.phandle, address, addressof(buf), size, addressof(ret)):
            raiseWin32Error("ReadProcessMemory")
        return buf.raw

    def platformContinue(self):

        magic = DBG_CONTINUE

        if self.getMeta("PendingException"):
            magic = DBG_EXCEPTION_NOT_HANDLED

        self.setMeta("PendingException", False)
        if self.flushcache:
            self.flushcache = False
            kernel32.FlushInstructionCache(self.phandle, 0, 0)
        if not kernel32.ContinueDebugEvent(self.pid, self.getMeta("StoppedThreadId"), magic):
            raiseWin32Error("ContinueDebugEvent")

    def platformStepi(self):
        self.setEflagsTf()
        self.syncRegs()
        self.platformContinue()

    def platformWriteMemory(self, address, buf):
        ret = c_ulong(0)
        if not kernel32.WriteProcessMemory(self.phandle, address, buf, len(buf), addressof(ret)):
            raiseWin32Error("WriteProcessMemory")
        # If we wrote memory, flush the instruction cache...
        self.flushcache = True
        return ret.value

    def platformGetRegs(self):
        ctx = CONTEXTx86()
        ctx.ContextFlags = (CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS)
        thandle = self.thandles.get(self.getMeta("ThreadId", 0), None)
        if not thandle:
            raise Exception("Getting registers for unknown thread")
        if not kernel32.GetThreadContext(thandle, addressof(ctx)):
            raiseWin32Error("GetThreadContext")
        return string_at(addressof(ctx), sizeof(ctx))

    def platformSetRegs(self, bytes):
        buf = c_buffer(bytes)
        ctx = CONTEXTx86()
        thandle = self.thandles.get(self.getMeta("ThreadId", 0), None)
        if not thandle:
            raise Exception("Getting registers for unknown thread")
        if not kernel32.GetThreadContext(thandle, addressof(ctx)):
            raiseWin32Error("GetThreadContext")

        memmove(addressof(ctx), addressof(buf), len(bytes))
        ctx.ContextFlags = (CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS)

        if not kernel32.SetThreadContext(thandle, addressof(ctx)):
            raiseWin32Error("SetThreadContext")

    def platformSendBreak(self):
        #FIXME make this support windows 2000
        if not kernel32.DebugBreakProcess(self.phandle):
            raiseWin32Error("DebugBreakProcess")

    def platformPs(self):
        ret = []
        pcount = 128 # Hardcoded limit of 128 processes... oh well..
        pids = (c_int * pcount)()
        needed = c_int(0)
        hmodule = c_int(0)

        psapi.EnumProcesses(addressof(pids), 4*pcount, addressof(needed))
        for i in range(needed.value/4):
            fname = (c_wchar * 512)()
            phandle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, 0, pids[i])
            if not phandle: # If we get 0, we failed to open it (perms)
                continue
            psapi.EnumProcessModules(phandle, addressof(hmodule), 4, addressof(needed))
            psapi.GetModuleBaseNameW(phandle, hmodule, fname, 512)
            ret.append( (pids[i], fname.value))
            kernel32.CloseHandle(phandle)
            kernel32.CloseHandle(hmodule)
        return ret

    def platformWait(self):
        event = DEBUG_EVENT()
        if not kernel32.WaitForDebugEvent(addressof(event), INFINITE):
            raiseWin32Error("WaitForDebugEvent")
        return event

    def platformProcessEvent(self, event):

        if event.ProcessId != self.pid:
            raise Exception("ERROR - Win32 Edge Condition One")

        ThreadId = event.ThreadId
        eventdict = {} # Each handler fills this in
        self.setMeta("Win32Event", eventdict)
        self.setMeta("StoppedThreadId", ThreadId)
        self.setMeta("ThreadId", ThreadId)

        if event.DebugEventCode == CREATE_PROCESS_DEBUG_EVENT:
           self.phandle = event.u.CreateProcessInfo.Process
           baseaddr = event.u.CreateProcessInfo.BaseOfImage
           ImageName = GetModuleFileNameEx(self.phandle, 0)
           self.setMeta("ExeName", ImageName)

           teb = event.u.CreateProcessInfo.ThreadLocalBase
           self.win32threads[ThreadId] = teb
           self.thandles[ThreadId] = event.u.CreateProcessInfo.Thread

           peb, = self.readMemoryFormat(teb + 0x30, "L")
           self.setMeta("PEB", peb)

           eventdict["ImageName"] = ImageName
           eventdict["StartAddress"] = event.u.CreateProcessInfo.StartAddress
           eventdict["ThreadLocalBase"] = teb

           self.fireNotifiers(vtrace.NOTIFY_ATTACH)
           self.addLibraryBase(ImageName, baseaddr)

        elif event.DebugEventCode == CREATE_THREAD_DEBUG_EVENT:
            self.thandles[ThreadId] = event.u.CreateThread.Thread
            teb = event.u.CreateThread.ThreadLocalBase
            startaddr = event.u.CreateThread.StartAddress
            # Setup the event dictionary for notifiers
            eventdict["ThreadLocalBase"] = teb
            eventdict["StartAddress"] = startaddr
            self.win32threads[ThreadId] = teb
            self.fireNotifiers(vtrace.NOTIFY_CREATE_THREAD)

        elif event.DebugEventCode == EXCEPTION_DEBUG_EVENT:
            excode = event.u.Exception.ExceptionRecord.ExceptionCode
            exflags = event.u.Exception.ExceptionRecord.ExceptionFlags
            exaddr = event.u.Exception.ExceptionRecord.ExceptionAddress
            exparam = event.u.Exception.ExceptionRecord.NumberParameters
            firstChance = event.u.Exception.FirstChance

            plist = []
            for i in range(exparam):
                plist.append(event.u.Exception.ExceptionRecord.ExceptionInformation[i])

            eventdict["ExceptionCode"] = excode
            eventdict["ExceptionFlags"] = exflags
            eventdict["ExceptionAddress"] = exaddr
            eventdict["NumberParameters"] = exparam
            eventdict["FirstChance"] = bool(firstChance)
            eventdict["ExceptionInformation"] = plist

            if firstChance:

                if excode == EXCEPTION_BREAKPOINT:
                    self.setMeta("PendingException", False)
                    if not self.checkBreakpoints():
                        # On first attach, all the library load
                        # events occur, then we hit a CC.  So,
                        # if we don't find a breakpoint, notify
                        # break anyay....
                        self.fireNotifiers(vtrace.NOTIFY_BREAK)
                        # Don't eat the BP exception if we didn't make it...
                        # Actually, for win2k's sake, let's do eat the breaks
                        #self.setMeta("PendingException", True)

                elif excode == EXCEPTION_SINGLE_STEP:
                    self.setMeta("PendingException", False)
                    self.fireNotifiers(vtrace.NOTIFY_STEP)

                else:
                    self.setMeta("PendingException", True)
                    self.fireNotifiers(vtrace.NOTIFY_SIGNAL)

            else:
                self.setMeta("PendingException", True)
                self.fireNotifiers(vtrace.NOTIFY_SIGNAL)

        elif event.DebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
            ecode = event.u.ExitProcess.ExitCode
            eventdict["ExitCode"] = ecode
            self.setMeta("ExitCode", ecode)
            self.fireNotifiers(vtrace.NOTIFY_EXIT)
            self.platformDetach()

        elif event.DebugEventCode == EXIT_THREAD_DEBUG_EVENT:
            self.win32threads.pop(ThreadId, None)
            ecode = event.u.ExitThread.ExitCode
            eventdict["ExitCode"] = ecode
            self.setMeta("ExitCode", ecode)
            self.setMeta("ExitThread", ThreadId)
            self.fireNotifiers(vtrace.NOTIFY_EXIT_THREAD)

        elif event.DebugEventCode == LOAD_DLL_DEBUG_EVENT:
            baseaddr = event.u.LoadDll.BaseOfDll
            ImageName = GetModuleFileNameEx(self.phandle, baseaddr)
            if not ImageName:
                # If it fails, fall back on getMappedFileName
                ImageName = self.getMappedFileName(baseaddr)
            self.addLibraryBase(ImageName, baseaddr)
            kernel32.CloseHandle(event.u.LoadDll.File)

        elif event.DebugEventCode == UNLOAD_DLL_DEBUG_EVENT:
            eventdict["BaseOfDll"] = event.u.UnloadDll.BaseOfDll
            self.fireNotifiers(vtrace.NOTIFY_UNLOAD_LIBRARY)

        elif event.DebugEventCode == OUTPUT_DEBUG_STRING_EVENT:
            # Gotta have a way to continue these...
            d = event.u.DebugString
            sdata = d.DebugStringData
            ssize = d.DebugStringLength

            # FIXME possibly make a gofast option that
            # doesn't get the string
            mem = self.readMemory(sdata, ssize)
            if d.Unicode:
                mem = mem.decode("utf-16-le")
            eventdict["DebugString"] = mem
            self.fireNotifiers(vtrace.NOTIFY_DEBUG_PRINT)

        else:
            print "Currently unhandled event",code


    def getMappedFileName(self, address):
        self.requireAttached()
        fname = (c_wchar * 512)()
        x = psapi.GetMappedFileNameW(self.phandle, address, addressof(fname), 512)
        if not x:
            return ""
        name = fname.value
        for dosname, devname in self.dosdevs:
            if name.startswith(devname):
                return name.replace(devname, dosname)
        return name

    def platformGetMaps(self):
        ret = []
        base = 0
        mbi = MEMORY_BASIC_INFORMATION32()
        while kernel32.VirtualQueryEx(self.phandle, base, addressof(mbi), sizeof(mbi)) > 0:
            if mbi.State == MEM_COMMIT:
                prot = mbi.Protect & 0xff
                if prot == PAGE_READONLY:
                    perm = vtrace.MM_READ
                elif prot == PAGE_READWRITE:
                    perm = vtrace.MM_READ | vtrace.MM_WRITE
                elif prot == PAGE_WRITECOPY:
                    perm = vtrace.MM_READ | vtrace.MM_WRITE
                elif prot == PAGE_EXECUTE:
                    perm = vtrace.MM_EXEC
                elif prot == PAGE_EXECUTE_READ:
                    perm = vtrace.MM_EXEC | vtrace.MM_READ
                elif prot == PAGE_EXECUTE_READWRITE:
                    perm = vtrace.MM_EXEC | vtrace.MM_READ | vtrace.MM_WRITE
                elif prot == PAGE_EXECUTE_WRITECOPY:
                    perm = vtrace.MM_EXEC | vtrace.MM_READ | vtrace.MM_WRITE
                else:
                    perm = 0

                base = mbi.BaseAddress
                mname = self.getMappedFileName(base)
                # If it fails, fall back on getmodulefilename
                if mname == "":
                    mname = GetModuleFileNameEx(self.phandle, base)
                ret.append( (base, mbi.RegionSize, perm, mname) )

            base += mbi.RegionSize
        return ret

    def platformGetThreads(self):
        return self.win32threads

if sys.platform == "win32":
    SYMCALLBACK = WINFUNCTYPE(c_int, POINTER(SYMBOL_INFO), c_ulong, c_ulong)
    PDBCALLBACK = WINFUNCTYPE(c_int, c_char_p, c_void_p)

class Win32SymbolResolver(symbase.VSymbolResolver):
    def __init__(self, filename, baseaddr, handle):
        # All locals must be in constructor because of the
        # getattr over-ride..
        self.phandle = handle
        self.doff = 0
        self.file = None
        self.doshdr = None
        self.pehdr = None
        self.sections = []
        self.funcflags = (SYMFLAG_FUNCTION | SYMFLAG_EXPORT)
        self.dbghelp_symopts = (SYMOPT_UNDNAME | SYMOPT_NO_PROMPTS | SYMOPT_NO_CPP)
        symbase.VSymbolResolver.__init__(self, filename, baseaddr, casesens=False)

    def rvaToFileOffset(self, rva):
        ret = 0
        for sname,srva,svsiz,sroff,srsiz in self.sections:
            if (srva <= rva) and (srva+svsiz >= rva):
                ret = (sroff + (rva-srva))
                break
        return ret

    def printSymbolInfo(self, info):
        # Just a helper function for "reversing" how dbghelp works
        for n,t in info.__class__._fields_:
            print n,repr(getattr(info, n))

    def typeEnumCallback(self, psym, size, ctx):
        sym = psym.contents
        #self.printSymbolInfo(sym)
        #print "TYPE",sym.Name,hex(sym.Flags)
        return True

    def symEnumCallback(self, psym, size, ctx):
        sym = psym.contents
        #self.printSymbolInfo(sym)
        #FIXME ms doesn't mostly include flags, they are really all misc...
        if sym.Flags & self.funcflags:
            self.addSymbol(sym.Name, sym.Address, size, vtrace.SYM_FUNCTION)
        else:
            self.addSymbol(sym.Name, sym.Address, size, vtrace.SYM_MISC)
        return True

    def symFileCallback(self, filename, nothing):
        return 0

    def parseWithDbgHelp(self):
        try:

            dbghelp.SymInitialize(self.phandle, None, False)
            dbghelp.SymSetOptions(self.dbghelp_symopts)

            x = dbghelp.SymLoadModule64(self.phandle,
                        0, 
                        c_char_p(self.filename),
                        None,
                        c_ulonglong(self.loadbase),
                        None)

            # This is for debugging which pdb got loaded
            #imghlp = IMAGEHLP_MODULE64()
            #dbghelp.SymGetModuleInfo64(None, c_ulonglong(x), addressof(imghlp))
            #print "PDB",imghlp.LoadedPdbName

            dbghelp.SymEnumSymbols(self.phandle,
                        c_ulonglong(self.loadbase),
                        None,
                        SYMCALLBACK(self.symEnumCallback),
                        0)

            # This is how you enumerate type information
            #dbghelp.SymEnumTypes(self.phandle,
                        #c_ulonglong(self.loadbase),
                        #SYMCALLBACK(self.typeEnumCallback),
                        #0)

            dbghelp.SymCleanup(self.phandle)

        except Exception, e:
            traceback.print_exc()
            raise

    def readPeHeader(self):
        self.doff = 0
        dosfmt = "<30HI"
        pefmt = "<I2H3I2H"

        self.doshdr = self.readPeFmt(dosfmt, 0)
        #FIXME check mz

        # Last element in the dos header is the address
        # of the pe header...
        self.file.seek(self.doshdr[-1])
        self.pehdr = self.readPeFmt(pefmt, self.doshdr[-1])

        if self.pehdr[6] == 224: # optional header length
            #peheader + sizeof(pehdr) + offset to data dictionary
            self.doff = self.doshdr[-1] + 24 + 96

    def readPeFmt(self, fmt, offset=None):
        size = struct.calcsize(fmt)
        if offset != None:
            self.file.seek(offset)
        return struct.unpack(fmt, self.file.read(size))

    def readPeSections(self):
        """
        This assumes that readPeHeader has been called
        but doesn't assume any particular file offset
        """
        self.sections = []
        self.file.seek(self.doshdr[-1] + self.pehdr[6] + 24)  # Seek to pehdr + aoutsize
        for i in range(self.pehdr[2]): # seccnt
            (name, vsize, rva,
             rsize, roffset, RelOff,
             LineOff, RelSize, LineSize,
             Chars) = self.readPeFmt("<8s6I2HI")
            sname = name.strip("\x00")
            soff = self.loadbase + rva
            self.sections.append((sname, rva, vsize, roffset, rsize))
            self.addSymbol(sname, soff, vsize, vtrace.SYM_SECTION)

    def initialParse(self):
        self.file = file(self.filename, "rb")
        self.readPeHeader()
        self.readPeSections()

    def parseBinary(self):
        self.initialParse()
        self.parseWithDbgHelp()

class PEMixin:
    """
    A platform mixin to parse PE binaries
    """
    def platformGetSymbolResolver(self, filename, baseaddr):
        return Win32SymbolResolver(filename, baseaddr, self.phandle)


########NEW FILE########
__FILENAME__ = rmi
"""
Cobra integration for remote debugging
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import md5
import os
import socket

import vtrace
import cobra

callback_daemon = None

def getTracerFactory():
    """
    Return a TracerFactory proxy object from the remote server
    """
    return cobra.CobraProxy("cobra://%s:%d/TracerFactory" % (vtrace.remote, vtrace.port))

class TraceProxyFactory:
    """
    A "factory" object for creating tracers and
    wrapping them up in a proxy instance to the
    *local* server.  This object is shared out
    via the pyro server for vtrace clients.
    """
    def getTrace(self):
        trace = vtrace.getTrace()
        host,port = cobra.getLocalInfo()
        unique = md5.md5(os.urandom(20)).hexdigest()
        vtrace.cobra_daemon.shareObject(trace, unique)
        trace.proxy = cobra.CobraProxy("cobra://%s:%d/%s" % (host,port,unique))
        return unique

    def releaseTrace(self, proxy):
        """
        When a remote system is done with a trace
        and wants the server to clean him up, hand
        the proxy object to this.
        """
        vtrace.cobra_daemon.unshareObject(proxy.__dict__.get("__cobra_name", None))

class RemoteTrace(cobra.CobraProxy):

    def __init__(self, *args, **kwargs):
        cobra.CobraProxy.__init__(self, *args, **kwargs)

def getCallbackProxy(trace, notifier):
    """
    Get a proxy object to reference *notifier* from the
    perspective of *trace*.  The trace is specified so
    we may check on our side of the connected socket to
    give him the best possible ip address...
    """
    global callback_daemon
    port = getCallbackPort()
    host, nothing = cobra.getCobraSocket(trace).getSockName()
    unique = md5.md5(os.urandom(20)).hexdigest()
    callback_daemon.shareObject(notifier, unique)
    return cobra.CobraProxy("cobra://%s:%d/%s" % (host, port, unique))

def getCallbackPort():
    """
    If necissary, start a callback daemon.  Return the
    ephemeral port it was bound on.
    """
    global callback_daemon
    if callback_daemon == None:
        callback_daemon = cobra.CobraDaemon(port=0)
        callback_daemon.fireThread()
    return callback_daemon.port

def startCobraDaemon():
    if vtrace.cobra_daemon == None:
        vtrace.cobra_daemon = cobra.CobraDaemon(port=vtrace.port)
        vtrace.cobra_daemon.fireThread()

def getRemoteTrace():
    factory = getTracerFactory()
    unique = factory.getTrace()
    return RemoteTrace("cobra://%s:%d/%s" % (vtrace.remote, vtrace.port, unique))

def startVtraceServer():
    """
    Fire up the pyro server and share out our
    "trace factory"
    """
    startCobraDaemon()
    factory = TraceProxyFactory()
    vtrace.cobra_daemon.shareObject(factory, "TracerFactory")

########NEW FILE########
__FILENAME__ = symbase
"""
Symbol resolvers and VSymbol objects.
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import os
import vtrace
import types

class VSymbolResolverException(Exception):
    pass

class VSymbol:
    """
    VSymbol objects contain all the symbol information for
    a particular record.  Use them like a string, and they're
    the symbol name, use them like a number and they're the symbol
    value, call len() on them and you get the length of the symbol
    """
    def __init__(self, name, value, size, stype, fname):
        self.name = name
        self.value = value
        self.size = size
        self.fname = fname
        self.stype = stype

    def __coerce__(self, value):
        # OMG MAGIX
        t = type(value)
        if t == types.NoneType:
            return (True, False)
        return (value, t(self.value))

    def __long__(self):
        return self.value

    def __str__(self):
        return self.name

    def __repr__(self):
        if self.stype == vtrace.SYM_FUNCTION:
            return "%s.%s()" % (self.fname, self.name)
        elif self.stype == vtrace.SYM_SECTION:
            return "%s [%s]" % (self.fname, self.name)
        else:
            return "%s.%s" % (self.fname, self.name)

    def __len__(self):
        return int(self.size)

class VSymbolResolver:
    """
    This class will return symbol values and sizes for
    attribute requests and is mostly for mapping into
    the address space of the expression parser...

    A tracer will instantiate one of these for each file
    loaded, and will be capable of resolving addresses
    """
    def __init__(self, filename, loadbase=0, casesens=True):
        """
        The constructor for SymbolResolver and it's inheritors
        is responsible for either parsing or settting up the
        necissary context to parse when requested.
        """
        self.loaded = False
        self.loadbase = loadbase
        self.filename = filename
        self.casesens = casesens
        self.basename = os.path.basename(filename)
        self.normname = self.basename.split(".")[0].split("-")[0] # FIXME ghettoooooo
        # Make everything lower case if we're not case sensitive
        if not casesens:
            self.normname = self.normname.lower()

        self.symbyname = {}

    def loadUp(self):
        if not self.loaded:
            self.parseBinary()
            self.loaded = True

    def parseBinary(self):
        """
        Over-ride this!  (it wont't get called until a symbol is
        requested, so just load em all up and go.
        """
        self.addSymbol("woot", 0x300, 20, vtrace.SYM_FUNCTION)
        self.addSymbol("foo", 0x400, 20, vtrace.SYM_FUNCTION)

    def addSymbol(self, name, value, size, stype):
        """
        Add a symbol to this resolver.  The "value" field of the symbol
        is expected to be already "fixed up" for the base address in
        the case of relocatable libraries.
        """
        if not self.casesens:
            name = name.lower()
        sym = VSymbol(name, long(value), int(size), stype, self.normname)
        self.symbyname[name] = sym

    def symByName(self, name):
        self.loadUp()
        if not self.casesens:
            name = name.lower()
        x = self.symbyname.get(name, None)
        if x == None:
            raise VSymbolResolverException("ERROR: symbol %s not found in file %s" % (name, self.basename))
        return x

    def symByAddr(self, address):
        self.loadUp()
        #FIXME make this a tree or something
        match = None
        last = 0xffffffff
        for sym in self.symbyname.values():
            saddr = long(sym)
            slen = len(sym)
            # If it's past, skip it...
            if saddr > address:
                continue

            # Are we closer than the last?
            delta = address - saddr

            # Exact match (might be section)
            if address < (saddr + slen): #Exact match
                if sym.stype != vtrace.SYM_SECTION:
                    return sym
                match = sym
                last = delta
                continue

            if delta < last:
                match = sym
                last = delta

        return match

    def symList(self):
        self.loadUp()
        return self.symbyname.values()

    def __nonzero__(self):
        return True

    def __len__(self):
        return len(self.symbyname.keys())

    def __getattr__(self, name):
        """
        Override getattr so things like kernel32.malloc resolve
        """
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError()
        return self.symByName(name)


########NEW FILE########
__FILENAME__ = win32heap

import vstruct

HEAP_ENTRY_BUSY             = 0x01
HEAP_ENTRY_EXTRA_PRESENT    = 0x02
HEAP_ENTRY_FILL_PATTERN     = 0x04
HEAP_ENTRY_VIRTUAL_ALLOC    = 0x08
HEAP_ENTRY_LAST_ENTRY       = 0x10
HEAP_ENTRY_SETTABLE_FLAG1   = 0x20
HEAP_ENTRY_SETTABLE_FLAG2   = 0x40
HEAP_ENTRY_SETTABLE_FLAG3   = 0x80

def reprHeapFlags(flags):
    ret = []
    if flags & HEAP_ENTRY_BUSY:
        ret.append("BUSY")
    if flags & HEAP_ENTRY_FILL_PATTERN:
        ret.append("FILL")
    if flags & HEAP_ENTRY_LAST_ENTRY:
        ret.append("LAST")
    if len(ret):
        return "|".join(ret)
    return "NONE"

class HeapCorruptionException(Exception):
    def __init__(self, heap, segment, chunkaddr):
        Exception.__init__(self, "Heap: 0x%.8x Segment: 0x%.8x Chunk Address: 0x%.8x" % (
                                 heap.address, segment.address, chunkaddr))
        self.heap = heap
        self.segment = segment
        self.chunkaddr = chunkaddr

class FreeListCorruption(Exception):
    def __init__(self, heap, index):
        Exception.__init__(self, "Heap: 0x%.8x FreeList Index: %d" % (heap.address, index))
        self.heap = heap
        self.index = index

class ChunkNotFound(Exception):
    pass

def getHeapSegChunk(trace, address):
    """
    Find and return the heap, segment, and chunk for the given addres
    (or exception).
    """
    for heap in getHeaps(trace):
        for seg in heap.getSegments():
            base,size,perms,fname = trace.getMap(seg.address)
            if address < base or address > base+size:
                continue
            for chunk in seg.getChunks():
                a = chunk.address
                b = chunk.address + len(chunk)
                if (address >= a and address < b):
                    return heap,seg,chunk

    raise ChunkNotFound("No Chunk Found for 0x%.8x" % address)

def getHeaps(trace):
    """
    Get the win32 heaps (returns a list of Win32Heap objects)
    """
    ret = []
    pebaddr = trace.getMeta("PEB")
    peb = trace.getStruct("win32.PEB", pebaddr)
    heapcount = int(peb.NumberOfHeaps)
    # FIXME not 64bit ok
    hlist = trace.readMemoryFormat(long(peb.ProcessHeaps), "<"+("L"*heapcount))
    for haddr in hlist:
        ret.append(Win32Heap(trace, haddr))
    return ret

class Win32Heap:

    def __init__(self, trace, address):
        self.address = address
        self.trace = trace
        self.heap = trace.getStruct("win32.HEAP", address)
        self.seglist = None

    def getSegments(self):
        """
        Return a list of Win32Segment objects.
        """
        if self.seglist == None:
            self.seglist = []
            for i in range(long(self.heap.LastSegmentIndex)+1):
                sa = self.heap.Segments[i]
                self.seglist.append(Win32Segment(self.trace, self, long(sa)))
        return self.seglist

class Win32Segment:
    def __init__(self, trace, heap, address):
        self.trace = trace
        self.heap = heap
        self.address = address
        self.seg = trace.getStruct("win32.HEAP_ENTRY", address)
        #FIXME segments can specify chunk Size granularity
        self.chunks = None

    def getChunks(self):
        if self.chunks == None:
            self.chunks = []
            addr = self.address
            lastsize = None
            while True:
                chunk = Win32Chunk(self.trace, addr)
                addr += len(chunk)
                self.chunks.append(chunk)
                if lastsize != None:
                    if int(chunk.chunk.PrevSize) * 8 != lastsize:
                        raise HeapCorruptionException(self.heap, self, addr)
                if chunk.isLast():
                    break
                lastsize = len(chunk)
        return self.chunks

class Win32Chunk:
    def __init__(self, trace, address):
        self.trace = trace
        self.address = address
        self.chunk = trace.getStruct("win32.HEAP_ENTRY", address)

    def __len__(self):
        return int(self.chunk.Size) * 8

    def isLast(self):
        return bool(int(self.chunk.Flags) & HEAP_ENTRY_LAST_ENTRY)

    def isBusy(self):
        return bool(int(self.chunk.Flags) & HEAP_ENTRY_BUSY)

    def getDataAddress(self):
        return self.address + len(self.chunk)

    def getDataSize(self):
        return len(self) - len(self.chunk)

    def getDataBytes(self, maxsize=None):
        size = self.getDataSize()
        if maxsize != None:
            size = min(size, maxsize)
        return self.trace.readMemory(self.getDataAddress(), size)

    def reprFlags(self):
        return reprHeapFlags(int(self.chunk.Flags))


########NEW FILE########
__FILENAME__ = util
# Copyright (C) 2007 Invisigoth - See LICENSE file for details

import re                                                                                                          

import vtrace
import vtrace.notifiers as v_notifiers
import vtrace.rmi as v_rmi

def splitargs(cmdline):
    cmdline = cmdline.replace('\\\\"', '"').replace('\\"', '')
    patt = re.compile('\".+?\"|\S+')
    for item in cmdline.split('\n'):
        return [s.strip('"') for s in patt.findall(item)]

class TraceManager:
    """
    A trace-manager is a utility class to extend from when you may be dealing
    with multiple tracer objects.  It allows for persistant mode settings and
    persistent metadata as well as bundling a DistributedNotifier.  You may also
    extend from this to get auto-magic remote stuff for your managed traces.
    """
    def __init__(self, trace=None):
        self.trace = trace
        self.dnotif = v_notifiers.DistributedNotifier()
        self.modes = {} # See docs for trace modes
        self.metadata = {} # Like traces, but persistant

    def manageTrace(self, trace):
        """
        Set all the modes/meta/notifiers in this trace for management
        by this TraceManager.
        """
        self.trace = trace
        if vtrace.remote:
            trace.registerNotifier(vtrace.NOTIFY_ALL, v_rmi.getCallbackProxy(trace, self.dnotif))
        else:
            trace.registerNotifier(vtrace.NOTIFY_ALL, self.dnotif)

        for name,val in self.modes.items():
            trace.setMode(name, val)

        for name,val in self.metadata.items():
            trace.setMeta(name, val)

    def unManageTrace(self, trace):
        """
        Untie this trace manager from the trace.
        """
        if vtrace.remote:
            trace.deregisterNotifier(vtrace.NOTIFY_ALL, v_rmi.getCallbackProxy(trace, self.dnotif))
        else:
            trace.deregisterNotifier(vtrace.NOTIFY_ALL, self.dnotif)

    def setMode(self, name, value):
        if self.trace != None:
            self.trace.setMode(name, value)
        self.modes[name] = value

    def getMode(self, name, default=False):
        if self.trace != None:
            return self.trace.getMode(name, default)
        return self.modes.get(name, default)

    def setMeta(self, name, value):
        if self.trace != None:
            self.trace.setMeta(name, value)
        self.metadata[name] = value

    def getMeta(self, name, default=None):
        if self.trace != None:
            return self.trace.getMeta(name, default)
        return self.metadata.get(name, default)

    def registerNotifier(self, event, notif):
        self.dnotif.registerNotifier(event, notif)

    def deregisterNotifier(self, event, notif):
        self.dnotif.deregisterNotifier(event, notif)


########NEW FILE########
__FILENAME__ = watchpoints
"""
Watchpoint Objects
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
from vtrace import *
from vtrace.breakpoints import *

class Watchpoint(Breakpoint):
    """
    The basic "break on access" watchpoint.  Extended from 
    Breakpoints and handled almost exactly the same way...
    """
    pass


########NEW FILE########
