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
	ops = ".,;:+-*/%&=|(){}[]^<>"
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


import keyword
pykeywords = set(keyword.kwlist)

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

def set_linecache(filename, source):
	import linecache
	linecache.cache[filename] = None, None, [line+'\n' for line in source.splitlines()], filename

if "raw_input" not in globals():
	raw_input = input

def simple_debug_shell(globals, locals):
	try: import readline
	except: pass # ignore
	COMPILE_STRING_FN = "<simple_debug_shell input>"
	while True:
		try:
			s = raw_input("> ")
		except:
			print("breaked debug shell: " + sys.exc_info()[0].__name__)
			break
		try:
			c = compile(s, COMPILE_STRING_FN, "single")
		except Exception as e:
			print("%s : %s in %r" % (e.__class__.__name__, str(e), s))
		else:
			set_linecache(COMPILE_STRING_FN, s)
			try:
				ret = eval(c, globals, locals)
			except:
				print("Error executing %r" % s)
				better_exchook(*sys.exc_info(), autodebugshell=False)
			else:
				try:
					if ret is not None: print(ret)
				except:
					print("Error printing return value of %r" % s)
					better_exchook(*sys.exc_info(), autodebugshell=False)
		
def debug_shell(user_ns, user_global_ns):
	ipshell = None
	try:
		from IPython.Shell import IPShellEmbed,IPShell
		ipshell = IPShell(argv=[], user_ns=user_ns, user_global_ns=user_global_ns)
	except: pass
	if ipshell:
		#ipshell()
		ipshell.mainloop()
	else:
		simple_debug_shell(user_global_ns, user_ns)						

def output(s): print(s)

def output_limit():
	return 300

def pp_extra_info(obj, depthlimit = 3):
	s = []
	if hasattr(obj, "__len__"):
		try:
			if type(obj) in (str,unicode,list,tuple,dict) and len(obj) <= 5:
				pass # don't print len in this case
			else:
				s += ["len = " + str(obj.__len__())]
		except: pass
	if depthlimit > 0 and hasattr(obj, "__getitem__"):
		try:
			if type(obj) in (str,unicode):
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

def better_exchook(etype, value, tb, debugshell=False, autodebugshell=True):
	output("EXCEPTION")
	output('Traceback (most recent call last):')
	allLocals,allGlobals = {},{}
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
		def _trySet(old, prefix, func):
			if old is not None: return old
			try: return prefix + func()
			except KeyError: return old
			except Exception as e:
				return prefix + "!" + e.__class__.__name__ + ": " + str(e)
		while _tb is not None and (limit is None or n < limit):
			f = _tb.tb_frame
			allLocals.update(f.f_locals)
			allGlobals.update(f.f_globals)
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
						tokenvalue = _trySet(tokenvalue, "<local> ", lambda: pretty_print(_resolveIdentifier(f.f_locals, token)))
						tokenvalue = _trySet(tokenvalue, "<global> ", lambda: pretty_print(_resolveIdentifier(f.f_globals, token)))
						tokenvalue = _trySet(tokenvalue, "<builtin> ", lambda: pretty_print(_resolveIdentifier(f.f_builtins, token)))
						tokenvalue = tokenvalue or "<not found>"
						output('      ' + ".".join(token) + " = " + tokenvalue)
						alreadyPrintedLocals.add(token)
				if len(alreadyPrintedLocals) == 0: output("       no locals")
			else:
				output('    -- code not available --')
			_tb = _tb.tb_next
			n += 1

	except Exception as e:
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
		(hasattr(types, "InstanceType") and isinstance(etype, types.InstanceType)) or
		etype is None or type(etype) is str):
		output(_format_final_exc_line(etype, value))
	else:
		output(_format_final_exc_line(etype.__name__, value))

	if autodebugshell:
		try: debugshell = int(os.environ["DEBUG"]) != 0
		except: pass
	if debugshell:
		output("---------- DEBUG SHELL -----------")
		debug_shell(user_ns=allLocals, user_global_ns=allGlobals)
		
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
__FILENAME__ = caching
# PyCParser caching logic
# by Albert Zeyer, 2011
# code under LGPL

# idea:
#   for each parsed file:
#     keep list of which macros have been used, i.e.
#        the dependency list of macros.
#     keep list of all C-stuff which has been added.
#     check last change time of file and all other files we open from here
#        and also store this list.
#     save all.
#  when opening a new file, macro-dependencies, check the last change time
#     of all files and if everything matches, use the cache.

import sys
import os, os.path
if sys.version_info.major == 2:
	import cparser
	from cparser_utils import *
else:
	from . import cparser
	from .cparser_utils import *
import types

# Note: It might make sense to make this somehow configureable.
# However, for now, I'd like to keep things as simple as possible.
# Using /tmp or (a bit better) /var/tmp might have been another
# possibility. However, it makes sense to keep this more permanent
# because when compiling a lot, it can be very time-critical if
# we just remove all the data.
# If wasted space becomes an issue, it is easy to write a script
# which would remove all old/obsolete entries from the cache.
# It makes sense also to keep this global for the whole system
# because the caching system should be able to handle this
# and it should thus only improve the performance.
# It is saved though in the user directory because most probably
# we wouldn't have write permission otherwise.
CACHING_DIR = os.path.expanduser("~/.cparser_caching/")

def sha1(obj):
	import hashlib
	h = hashlib.sha1()
	if sys.version_info.major == 2:
		def h_update(s): h.update(s)
	else:
		def h_update(s):
			if isinstance(s, str): h.update(s.encode("utf-8"))
			else: h.update(s)
	if isinstance(obj, unicode):
		h_update(obj.encode("utf-8"))
	elif isinstance(obj, str):
		h_update(obj)
	elif isinstance(obj, dict):
		h_update("{")
		for k,v in sorted(obj.items()):
			h_update(sha1(k))
			h_update(":")
			h_update(sha1(v))
			h_update(",")
		h_update("}")
	elif isinstance(obj, (list,tuple)):
		h_update("[")
		for v in sorted(obj):
			h_update(sha1(v))
			h_update(",")
		h_update("]")
	else:
		h_update(str(obj))
	return h.hexdigest()

class MyDict(dict):
	def __setattr__(self, key, value):
		assert isinstance(key, (str,unicode))
		self[key] = value
	def __getattr__(self, key):
		try: return self[key]
		except KeyError: raise AttributeError
	def __repr__(self): return "MyDict(" + dict.__repr__(self) + ")"
	def __str__(self): return "MyDict(" + dict.__str__(self) + ")"
	
class DbObj:
	@classmethod
	def GetFilePath(cls, key):
		h = sha1(key)
		prefix = CACHING_DIR + cls.Namespace
		return prefix + "/" + h[:2] + "/" + h[2:]
	@classmethod
	def Load(cls, key, create=False):
		fn = cls.GetFilePath(key)
		try: f = open(fn, "b")
		except:
			if create:
				obj = cls()
				obj.__dict__["_key"] = key
				return obj
			else:
				return None
		import pickle
		obj = pickle.load(f)
		f.close()
		return obj
	@classmethod
	def Delete(cls, key):
		fn = cls.GetFilePath(key)
		os.remove(fn)
	def delete(self): self.Delete(self._key)
	def save(self):
		fn = self.GetFilePath(self._key)
		try: os.makedirs(os.path.dirname(fn))
		except: pass # ignore file-exists or other errors
		f = open(fn, "wb")
		import pickle
		pickle.dump(self, f)
		f.close()
	
def getLastChangeUnixTime(filename):
	import os.path
	return os.path.getmtime(filename)

class FileCacheRef(MyDict):
	@classmethod
	def FromCacheData(cls, cache_data):
		ref = cls()
		ref.filedepslist = map(lambda fn: (fn,getLastChangeUnixTime(fn)), cache_data.filenames)
		ref.macros = {}
		for m in cache_data.macroAccessSet:
			ref.macros[m] = cache_data.oldMacros[m]
		return ref
	def match(self, stateStruct):
		for macro in self.macros:
			if stateStruct.macros[macro] != self.macros[macro]:
				return False
		return True
	def checkFileDepListUpToDate(self):
		for fn,unixtime in self.filedepslist:
			if getLastChangeUnixTime(fn) > unixtime:
				return False
		return True		

class FileCacheRefs(DbObj, list):
	Namespace = "file-cache-refs"

class FileCache(DbObj, MyDict):
	Namespace = "file-cache"
	@classmethod
	def FromCacheData(cls, cache_data, key):
		obj = cls()
		obj.__dict__["_key"] = key
		obj.additions = cache_data.additions
		return obj
	def apply(self, stateStruct):
		for k,l in self.additions.items():
			a = getattr(stateStruct, k)
			if isinstance(a, (list,StateListWrapper)):
				a.extend(l)
			elif isinstance(a, (dict,StateDictWrapper)):
				for dk,dv in l:
					if dv is None:
						a.pop(dk)
					else:
						a[dk] = dv
			else:
				assert False, "unknown attribute " + k + ": " + str(a)

def check_cache(stateStruct, full_filename):	
	filecaches = FileCacheRefs.Load(full_filename)
	if filecaches is None: return None
	
	for filecacheref in filecaches:
		if not filecacheref.match(stateStruct):
			continue
		if not filecacheref.checkFileDepListUpToDate():
			FileCache.Delete(filecacheref)
			filecaches.remove(filecacheref)
			filecaches.save()
			return None
		filecache = FileCache.Load(filecacheref)
		assert filecache is not None, sha1(filecacheref) + " not found in " + FileCache.Namespace
		return filecache
	
	return None

def save_cache(cache_data, full_filename):
	filecaches = FileCacheRefs.Load(full_filename, create=True)
	filecacheref = FileCacheRef.FromCacheData(cache_data)
	filecaches.append(filecacheref)
	filecaches.save()
	filecache = FileCache.FromCacheData(cache_data, key=filecacheref)
	filecache.save()

# Note: This does more than State.preprocess. In case it hits a cache,
# it applies all effects up to cpre3 and ignores the preprocessing.
# Note also: This is a generator. In the cache hit case, it yields nothing.
# Otherwise, it doesn't do any further processing and it just yields the rest.
def State__cached_preprocess(stateStruct, reader, full_filename, filename):
	if not full_filename:
		# shortcut. we cannot use caching if we don't have the full filename.
		for c in generic_class_method(cparser.State.preprocess)(stateStruct, reader, full_filename, filename):
			yield c
		return
	
	if stateStruct._cpre3_atBaseLevel:
		try:
			cached_entry = check_cache(stateStruct, full_filename)
			if cached_entry is not None:
				cached_entry.apply(stateStruct)
				return
		except Exception as e:
			print("(Safe to ignore) Error while reading C parser cache for %s : %s" % (filename, str(e)))
			# Try to delete old references if possible. Otherwise we might always hit this.
			try: FileCacheRefs.Delete(full_filename)
			except: pass

	assert isinstance(stateStruct, StateWrapper)
	stateStruct.cache_pushLevel()
	stateStruct._filenames.add(full_filename)
	for c in generic_class_method(cparser.State.preprocess)(stateStruct, reader, full_filename, filename):
		yield c
	cache_data = stateStruct.cache_popLevel()
	
	save_cache(cache_data, full_filename)
	
class StateDictWrapper:
	def __init__(self, d, addList, addSet=None, accessSet=None):
		self._addList = addList
		self._addSet = addSet
		self._accessSet = accessSet
		self._dict = d
	def __getattr__(self, k):
		return getattr(self._dict, k)
	def __setitem__(self, k, v):
		assert v is not None
		self._dict[k] = v
		self._addList.append((k,v))
		if self._addSet is not None:
			self._addSet.add(k)
	def __getitem__(self, k):
		if self._accessSet is not None:
			assert self._addSet is not None
			if not k in self._addSet: # we only care about it if we didn't add it ourself
				self._accessSet.add(k)
		return self._dict[k]
	def __contains__(self, k): return self.has_key(k)
	def has_key(self, k):
		haskey = self._dict.__contains__(k)
		if haskey and self._accessSet is not None:
			assert self._addSet is not None
			if not k in self._addSet: # we only care about it if we didn't add it ourself
				self._accessSet.add(k)
		return haskey
	def pop(self, k):
		self._dict.pop(k)
		self._addList.append((k,None))
		if self._addSet is not None:
			self._addSet.discard(k)
	def __repr__(self): return "StateDictWrapper(" + repr(self._dict) + ")"
	def __str__(self): return "StateDictWrapper(" + str(self._dict) + ")"
		
class StateListWrapper:
	def __init__(self, l, addList):
		self._addList = addList
		self._list = l
	def __getattr__(self, k):
		return getattr(self._list, k)
	def __iadd__(self, l):
		self._list.extend(l)
		self._addList.extend(l)
		return self
	def append(self, v):
		self._list.append(v)
		self._addList.append(v)
	def extend(self, l):
		self._list.extend(l)
		self._addList.extend(l)
	def __repr__(self): return "StateListWrapper(" + repr(self._list) + ")"
	def __str__(self): return "StateListWrapper(" + str(self._list) + ")"

class StateWrapper:
	WrappedDicts = ("macros","typedefs","structs","unions","enums","funcs","vars","enumconsts")
	WrappedLists = ("contentlist",)
	LocalAttribs = ("_stateStruct", "_cache_stack", "_additions", "_macroAccessSet", "_macroAddSet", "_filenames", "_cpre3_atBaseLevel")
	def __init__(self, stateStruct):
		self._stateStruct = stateStruct
		self._cache_stack = []
	def __getattr__(self, k):
		if k in self.LocalAttribs: raise AttributeError # normally we shouldn't get here but just in case
		if len(self._cache_stack) > 0:
			if k in self.WrappedDicts:
				kwattr = {'d': getattr(self._stateStruct, k), 'addList': self._additions[k]}
				if k == "macros":
					kwattr["accessSet"] = self._macroAccessSet
					kwattr["addSet"] = self._macroAddSet
				return StateDictWrapper(**kwattr)
			if k in self.WrappedLists:
				return StateListWrapper(getattr(self._stateStruct, k), addList=self._additions[k])
		attr = getattr(self._stateStruct, k)
		if isinstance(attr, types.MethodType):
			attr = rebound_instance_method(attr, self)
		return attr
	def __repr__(self):
		return "<StateWrapper of " + repr(self._stateStruct) + ">"
	def __setattr__(self, k, v):
		if k in self.LocalAttribs:
			self.__dict__[k] = v
			return
		if k in self.WrappedLists and isinstance(v, StateListWrapper): return # ignore. probably iadd or so.
		setattr(self._stateStruct, k, v)
	def cache_pushLevel(self):
		self._additions = {} # dict/list attrib -> addition list
		for k in self.WrappedDicts + self.WrappedLists: self._additions[k] = []
		self._macroAccessSet = set()
		self._macroAddSet = set()
		self._filenames = set()
		self._cache_stack.append(
			MyDict(
				oldMacros = dict(self._stateStruct.macros),
				additions = self._additions,
				macroAccessSet = self._macroAccessSet,
				macroAddSet = self._macroAddSet,
				filenames = self._filenames
				))
	def cache_popLevel(self):
		cache_data = self._cache_stack.pop()
		if len(self._cache_stack) == 0:
			del self._additions
			del self._macroAccessSet
			del self._macroAddSet
			del self._filenames		
		else:
			# recover last
			last = self._cache_stack[-1]
			self._additions = last.additions
			self._macroAccessSet = last.macroAccessSet
			self._macroAddSet = last.macroAddSet
			self._filenames = last.filenames
			# merge with popped frame
			for k in self.WrappedDicts + self.WrappedLists:
				self._additions[k].extend(cache_data.additions[k])
			self._macroAddSet.update(cache_data.macroAddSet)
			for k in cache_data.macroAccessSet:
				if k not in self._macroAddSet:
					self._macroAccessSet.add(k)
			self._filenames.update(cache_data.filenames)
		return cache_data
	preprocess = State__cached_preprocess
	def __getstate__(self):
		# many C structure objects refer to this as their parent.
		# when we pickle those objects, it should be safe to ignore to safe this.
		# we also don't really have any other option because we don't want to
		# dump this whole object.
		return None
		
def parse(filename, state = None):
	if state is None:
		state = cparser.State()
		state.autoSetupSystemMacros()
	
	wrappedState = StateWrapper(state)
	preprocessed = wrappedState.preprocess_file(filename, local=True)
	tokens = cparser.cpre2_parse(wrappedState, preprocessed)
	cparser.cpre3_parse(wrappedState, tokens)
	
	return state

def test():
	import better_exchook
	better_exchook.install()
	
	state = parse("/Library/Frameworks/SDL.framework/Headers/SDL.h")
	
	return state

if __name__ == '__main__':
	print(test())

########NEW FILE########
__FILENAME__ = cparser
# PyCParser main file
# by Albert Zeyer, 2011
# code under LGPL

import ctypes, _ctypes

SpaceChars = " \t"
LowercaseLetterChars = "abcdefghijklmnopqrstuvwxyz"
LetterChars = LowercaseLetterChars + LowercaseLetterChars.upper()
NumberChars = "0123456789"
OpChars = "&|=!+-*/%<>^~?:,."
LongOps = [c+"=" for c in  "&|=+-*/%<>^~!"] + ["--","++","->","<<",">>","&&","||","<<=",">>=","::",".*","->*"]
OpeningBrackets = "[({"
ClosingBrackets = "})]"

# NOTE: most of the C++ stuff is not really supported yet
OpPrecedences = {
	"::": 1,
	"++": 2, # as postfix; 3 as prefix
	"--": 2, # as postfix; 3 as prefix
	".": 2,
	"->": 2,
	"typeid": 2,
	"const_cast": 2,
	"dynamic_cast": 2,
	"reinterpret_cast": 2,
	"static_cast": 2,
	"!": 3,
	"~": 3,
	"sizeof": 3,
	"new": 3,
	"delete": 3,
	".*": 4,
	"->*": 4,
	"*": 5, # as bin op; 3 as prefix
	"/": 5,
	"%": 5,
	"+": 6, # as bin op; 3 as prefix
	"-": 6, # as bin op; 3 as prefix
	"<<": 7,
	">>": 7,
	"<": 8,
	"<=": 8,
	">": 8,
	">=": 8,
	"==": 9,
	"!=": 9,
	"&": 10, # as bin op; 3 as prefix
	"^": 11,
	"|": 12,
	"&&": 13,
	"||": 14,
	"?": 15, # a ? b : c
	"?:": 15, # this is the internal op representation when we have got all three sub nodes
	"=": 16,
	"+=": 16,
	"-=": 16,
	"*=": 16,
	"/=": 16,
	"%=": 16,
	"<<=": 16,
	">>=": 16,
	"&=": 16,
	"^=": 16,
	"|=": 16,
	"throw": 17,
	",": 18
}

OpsRightToLeft = set([
	"=",
	"+=", "-=",
	"*=", "/=", "%=",
	"<<=", ">>=",
	"&=", "^=", "|="
])

OpPrefixFuncs = {
	"+": (lambda x: +x),
	"-": (lambda x: -x),
	"&": (lambda x: ctypes.pointer(x)),
	"*": (lambda x: x.content),
	"++": (lambda x: ++x),
	"--": (lambda x: --x),
	"!": (lambda x: not x),
	"~": (lambda x: ~x),
}

OpBinFuncs = {
	"+": (lambda a,b: a + b),
	"-": (lambda a,b: a - b),
	"*": (lambda a,b: a * b),
	"/": (lambda a,b: a / b),
	"%": (lambda a,b: a % b),
	"<<": (lambda a,b: a << b),
	">>": (lambda a,b: a >> b),
	"<": (lambda a,b: a < b),
	"<=": (lambda a,b: a <= b),
	">": (lambda a,b: a > b),
	">=": (lambda a,b: a >= b),
	"==": (lambda a,b: a == b),
	"!=": (lambda a,b: a != b),
	"&": (lambda a,b: a & b),
	"^": (lambda a,b: a ^ b),
	"|": (lambda a,b: a | b),
	"&&": (lambda a,b: a and b),
	"||": (lambda a,b: a or b),
	",": (lambda a,b: b),
	# NOTE: These assignment ops don't really behave like maybe expected
	# but they return the somewhat expected.
	"=": (lambda a,b: b),
	"+=": (lambda a,b: a + b),
	"-=": (lambda a,b: a - b),
	"*=": (lambda a,b: a * b),
	"/=": (lambda a,b: a / b),
	"%=": (lambda a,b: a % b),
	"<<=": (lambda a,b: a << b),
	">>=": (lambda a,b: a >> b),
	"&=": (lambda a,b: a & b),
	"^=": (lambda a,b: a ^ b),
	"|=": (lambda a,b: a | b),
}

# WARNING: this isn't really complete
def simple_escape_char(c):
	if c == "n": return "\n"
	elif c == "t": return "\t"
	elif c == "a": return "\a"
	elif c == "b": return "\b"
	elif c == "f": return "\f"
	elif c == "r": return "\r"
	elif c == "v": return "\v"
	elif c == "0": return "\0"
	elif c == "\n": return "\n"
	elif c == '"': return '"'
	elif c == "'": return "'"
	elif c == "\\": return "\\"
	else:
		# Just to be sure so that users don't run into trouble.
		assert False, "simple_escape_char: cannot handle " + repr(c) + " yet"
		return c

def escape_cstr(s):
	return s.replace('"', '\\"')

def parse_macro_def_rightside(stateStruct, argnames, input):
	assert input is not None
	if stateStruct is None:
		class Dummy:
			def error(self, s): pass
		stateStruct = Dummy()

	def f(*args):
		args = dict(map(lambda i: (argnames[i], args[i]), range(len(argnames or ()))))
		
		ret = ""
		state = 0
		lastidentifier = ""
		for c in input:
			if state == 0:
				if c in SpaceChars: ret += c
				elif c in LetterChars + "_":
					state = 1
					lastidentifier = c
				elif c in NumberChars:
					state = 2
					ret += c
				elif c == '"':
					state = 4
					ret += c
				elif c == "#": state = 6
				else: ret += c
			elif state == 1: # identifier
				if c in LetterChars + NumberChars + "_":
					lastidentifier += c
				else:
					if lastidentifier in args:
						ret += args[lastidentifier]
					else:
						ret += lastidentifier
					lastidentifier = ""
					ret += c
					state = 0
			elif state == 2: # number
				ret += c
				if c in NumberChars: pass
				elif c == "x": state = 3
				elif c in LetterChars + "_": pass # even if invalid, stay in this state
				else: state = 0
			elif state == 3: # hex number
				ret += c
				if c in NumberChars + LetterChars + "_": pass # also ignore invalids
				else: state = 0
			elif state == 4: # str
				ret += c
				if c == "\\": state = 5
				elif c == '"': state = 0
				else: pass
			elif state == 5: # escape in str
				state = 4
				ret += simple_escape_char(c)
			elif state == 6: # after "#"
				if c in SpaceChars + LetterChars + "_":
					lastidentifier = c.strip()
					state = 7
				elif c == "#":
					ret = ret.rstrip()
					state = 8
				else:
					# unexpected, just recover
					stateStruct.error("unfold macro: unexpected char '" + c + "' after #")
					state = 0
			elif state == 7: # after single "#"	with identifier
				if c in LetterChars + NumberChars + "_":
					lastidentifier += c
				else:
					if lastidentifier not in args:
						stateStruct.error("unfold macro: cannot stringify " + lastidentifier + ": not found")
					else:
						ret += '"' + escape_cstr(args[lastidentifier]) + '"'
					lastidentifier = ""
					state = 0
					ret += c
			elif state == 8: # after "##"
				if c in SpaceChars: pass
				else:
					lastidentifier = c
					state = 1

		if state == 1:
			if lastidentifier in args:
				ret += args[lastidentifier]
			else:
				ret += lastidentifier

		return ret

	return f

class Macro:
	def __init__(self, state=None, macroname=None, args=None, rightside=None):
		self.name = macroname
		self.args = args
		self.rightside = rightside if (rightside is not None) else ""
		self.defPos = state.curPosAsStr() if state else "<unknown>"
		self._tokens = None
	def __str__(self):
		if self.args is not None:
			return "(" + ", ".join(self.args) + ") -> " + self.rightside
		else:
			return "_ -> " + self.rightside
	def __repr__(self):
		return "<Macro: " + str(self) + ">"
	def eval(self, state, args):
		if len(args) != len(self.args or ()): raise TypeError("invalid number of args (" + str(args) + ") for " + repr(self))
		func = parse_macro_def_rightside(state, self.args, self.rightside)
		return func(*args)
	def __call__(self, *args):
		return self.eval(None, args)
	def __eq__(self, other):
		if not isinstance(other, Macro): return False
		return self.args == other.args and self.rightside == other.rightside
	def __ne__(self, other): return not self == other
	def _parseTokens(self, stateStruct):
		assert self.args is None
		if self._tokens is not None: return
		preprocessed = stateStruct.preprocess(self.rightside, None, repr(self))
		self._tokens = list(cpre2_parse(stateStruct, preprocessed))		
	def getSingleIdentifer(self, stateStruct):
		assert self._tokens is not None
		if len(self._tokens) == 1 and isinstance(self._tokens[0], CIdentifier):
			return self._tokens[0].content
		return None
	def getCValue(self, stateStruct):
		tokens = self._tokens
		assert tokens is not None
		
		if all([isinstance(t, (CIdentifier,COp)) for t in tokens]):
			t = tuple([t.content for t in tokens])
			if t in stateStruct.CBuiltinTypes:
				return stateStruct.CBuiltinTypes[t].getCType(stateStruct)
			
		valueStmnt = CStatement()
		input_iter = iter(tokens)
		for token in input_iter:
			if isinstance(token, COpeningBracket):
				valueStmnt._cpre3_parse_brackets(stateStruct, token, input_iter)
			else:
				valueStmnt._cpre3_handle_token(stateStruct, token)
		valueStmnt.finalize(stateStruct)
		
		return valueStmnt.getConstValue(stateStruct)

# either some basic type, another typedef or some complex like CStruct/CUnion/...
class CType:
	def __init__(self, **kwargs):
		for k,v in kwargs.items():
			setattr(self, k, v)
	def __repr__(self):
		return self.__class__.__name__ + " " + str(self.__dict__)
	def __eq__(self, other):
		if not hasattr(other, "__class__"): return False
		return self.__class__ is other.__class__ and self.__dict__ == other.__dict__
	def __ne__(self, other): return not self == other
	def __hash__(self): return hash(self.__class__) + 31 * hash(tuple(sorted(self.__dict__.items())))
	def getCType(self, stateStruct):
		raise NotImplementedError(str(self) + " getCType is not implemented")
	def asCCode(self, indent=""):
		raise NotImplementedError(str(self) + " asCCode not implemented")

class CUnknownType(CType):
	def asCCode(self, indent=""): return indent + "/* unknown */ int"
class CVoidType(CType):
	def __repr__(self): return "void"
	def getCType(self, stateStruct): return None
	def asCCode(self, indent=""): return indent + "void"
	
class CPointerType(CType):
	def __init__(self, ptr): self.pointerOf = ptr
	def getCType(self, stateStruct):
		try:
			t = getCType(self.pointerOf, stateStruct)
			ptrType = ctypes.POINTER(t)
			return ptrType
		except Exception as e:
			stateStruct.error(str(self) + ": error getting type (" + str(e) + "), falling back to void-ptr")
		return ctypes.c_void_p
	def asCCode(self, indent=""): return indent + asCCode(self.pointerOf) + "*"

class CBuiltinType(CType):
	def __init__(self, builtinType):
		assert isinstance(builtinType, tuple)
		self.builtinType = builtinType
	def getCType(self, stateStruct):
		t = stateStruct.CBuiltinTypes[self.builtinType]
		return getCType(t, stateStruct)
	def asCCode(self, indent=""): return indent + " ".join(self.builtinType)
	
class CStdIntType(CType):
	def __init__(self, name): self.name = name
	def getCType(self, stateStruct): return stateStruct.StdIntTypes[self.name]
	def asCCode(self, indent=""): return indent + self.name

class CTypedefType(CType):
	def __init__(self, name): self.name = name
	def getCType(self, stateStruct):
		return getCType(stateStruct.typedefs[self.name], stateStruct)
	def asCCode(self, indent=""): return indent + self.name
		
def getCType(t, stateStruct):
	assert not isinstance(t, CUnknownType)
	try:
		if issubclass(t, _ctypes._SimpleCData): return t
	except: pass # e.g. typeerror or so
	if isinstance(t, (CStruct,CUnion,CEnum)):
		if t.body is None:
			# it probably is the pre-declaration. but we might find the real-one
			if isinstance(t, CStruct): D = "structs"
			elif isinstance(t, CUnion): D = "unions"
			elif isinstance(t, CEnum): D = "enums"
			t = getattr(stateStruct, D).get(t.name, t)
		return t.getCType(stateStruct)
	if isinstance(t, _CBaseWithOptBody):
		return t.getCType(stateStruct)
	if isinstance(t, CType):
		return t.getCType(stateStruct)
	raise Exception(str(t) + " cannot be converted to a C type")

def isSameType(stateStruct, type1, type2):
	ctype1 = getCType(type1, stateStruct)
	ctype2 = getCType(type2, stateStruct)
	return ctype1 == ctype2

def getSizeOf(t, stateStruct):
	t = getCType(t, stateStruct)
	return ctypes.sizeof(t)

class State:
	# See _getCTypeStruct for details.
	IndirectSimpleCTypes = False
	
	EmptyMacro = Macro(None, None, (), "")
	CBuiltinTypes = {
		("void",): CVoidType(),
		("void", "*"): ctypes.c_void_p,
		("char",): ctypes.c_byte,
		("unsigned", "char"): ctypes.c_ubyte,
		("short",): ctypes.c_short,
		("unsigned", "short"): ctypes.c_ushort,
		("int",): ctypes.c_int,
		("signed",): ctypes.c_int,
		("unsigned", "int"): ctypes.c_uint,
		("unsigned",): ctypes.c_uint,
		("long",): ctypes.c_long,
		("unsigned", "long"): ctypes.c_ulong,
		("long", "long"): ctypes.c_longlong,
		("unsigned", "long", "long"): ctypes.c_ulonglong,
		("float",): ctypes.c_float,
		("double",): ctypes.c_double,
		("long", "double"): ctypes.c_longdouble,
	}
	StdIntTypes = {
		"uint8_t": ctypes.c_uint8,
		"uint16_t": ctypes.c_uint16,
		"uint32_t": ctypes.c_uint32,
		"uint64_t": ctypes.c_uint64,
		"int8_t": ctypes.c_int8,
		"int16_t": ctypes.c_int16,
		"int32_t": ctypes.c_int32,
		"int64_t": ctypes.c_int64,
		"byte": ctypes.c_byte,
		"wchar_t": ctypes.c_wchar,
		"size_t": ctypes.c_size_t,
		"ptrdiff_t": ctypes.c_long,
		"intptr_t": ctypes.POINTER(ctypes.c_int),
		"FILE": ctypes.c_int, # NOTE: not really correct but shouldn't matter unless we directly access it
	}
	Attribs = [
		"const",
		"extern",
		"static",
		"register",
		"volatile",
		"__inline__",
		"inline",
	]
	
	def __init__(self):
		self.parent = None
		self.macros = {} # name -> Macro
		self.typedefs = {} # name -> type
		self.structs = {} # name -> CStruct
		self.unions = {} # name -> CUnion
		self.enums = {} # name -> CEnum
		self.funcs = {} # name -> CFunc
		self.vars = {} # name -> CVarDecl
		self.enumconsts = {} # name -> CEnumConst
		self.contentlist = []
		self._preprocessIfLevels = []
		self._preprocessIgnoreCurrent = False
		# 0->didnt got true yet, 1->in true part, 2->after true part. and that as a stack
		self._preprocessIncludeLevel = []
		self._errors = []
	
	def autoSetupSystemMacros(self):
		import sys
		self.macros["__attribute__"] = Macro(args=("x",), rightside="")
		self.macros["__GNUC__"] = Macro(rightside="4") # most headers just behave more sane with this :)
		self.macros["__GNUC_MINOR__"] = Macro(rightside="2")
		#self.macros["UINT64_C"] = Macro(args=("C"), rightside= "C##ui64") # or move to stdint.h handler?
		if sys.platform == "darwin":
			self.macros["__APPLE__"] = self.EmptyMacro
			self.macros["__MACH__"] = self.EmptyMacro
			self.macros["__MACOSX__"] = self.EmptyMacro
			self.macros["i386"] = self.EmptyMacro
			self.macros["MAC_OS_X_VERSION_MIN_REQUIRED"] = Macro(rightside="1030")
	
	def autoSetupGlobalIncludeWrappers(self):
		from globalincludewrappers import Wrapper
		Wrapper().install(self)
	
	def incIncludeLineChar(self, fullfilename=None, inc=None, line=None, char=None, charMod=None):
		CharStartIndex = 0
		LineStartIndex = 1
		if inc is not None:
			self._preprocessIncludeLevel += [[fullfilename, inc, LineStartIndex, CharStartIndex]]
		if len(self._preprocessIncludeLevel) == 0:
			self._preprocessIncludeLevel += [[None, "<input>", LineStartIndex, CharStartIndex]]
		if line is not None:
			self._preprocessIncludeLevel[-1][2] += line
			self._preprocessIncludeLevel[-1][3] = CharStartIndex
		if char is not None:
			c = self._preprocessIncludeLevel[-1][3]
			c += char
			if charMod is not None:
				c = c - (c - CharStartIndex) % charMod + CharStartIndex
			self._preprocessIncludeLevel[-1][3] = c
	
	def curPosAsStr(self):
		if len(self._preprocessIncludeLevel) == 0: return "<out-of-scope>"
		l = self._preprocessIncludeLevel[-1]
		return ":".join([l[1], str(l[2]), str(l[3])])
	
	def error(self, s):
		self._errors.append(self.curPosAsStr() + ": " + s)

	def findIncludeFullFilename(self, filename, local):
		if local:
			dir = ""
			if filename[0] != "/":
				if self._preprocessIncludeLevel and self._preprocessIncludeLevel[-1][0]:
					import os.path
					dir = os.path.dirname(self._preprocessIncludeLevel[-1][0])
				if not dir: dir = "."
				dir += "/"
		else:
			dir = ""

		fullfilename = dir + filename
		return fullfilename
	
	def readLocalInclude(self, filename):
		fullfilename = self.findIncludeFullFilename(filename, True)
		
		try:
			import codecs
			f = codecs.open(fullfilename, "r", "utf-8")
		except Exception as e:
			self.error("cannot open local include-file '" + filename + "': " + str(e))
			return "", None
		
		def reader():
			while True:
				c = f.read(1)
				if len(c) == 0: break
				yield c
		reader = reader()
		
		return reader, fullfilename

	def readGlobalInclude(self, filename):
		if filename == "inttypes.h": return "", None # we define those types as builtin-types
		elif filename == "stdint.h": return "", None
		else:
			self.error("no handler for global include-file '" + filename + "'")
			return "", None

	def preprocess_file(self, filename, local):
		if local:
			reader, fullfilename = self.readLocalInclude(filename)
		else:
			reader, fullfilename = self.readGlobalInclude(filename)

		for c in self.preprocess(reader, fullfilename, filename):
			yield c

	def preprocess(self, reader, fullfilename, filename):
		self.incIncludeLineChar(fullfilename=fullfilename, inc=filename)
		for c in cpreprocess_parse(self, reader):
			yield c		
		self._preprocessIncludeLevel = self._preprocessIncludeLevel[:-1]		

def is_valid_defname(defname):
	if not defname: return False
	gotValidPrefix = False
	for c in defname:
		if c in LetterChars + "_":
			gotValidPrefix = True
		elif c in NumberChars:
			if not gotValidPrefix: return False
		else:
			return False
	return True

def cpreprocess_evaluate_ifdef(state, arg):
	arg = arg.strip()
	if not is_valid_defname(arg):
		state.error("preprocessor: '" + arg + "' is not a valid macro name")
		return False
	return arg in state.macros

def cpreprocess_evaluate_single(state, arg):
	if arg == "": return None
	try: return int(arg) # is integer?
	except: pass
	try: return long(arg) # is long?
	except: pass
	try: return int(arg, 16) # is hex?
	except: pass
	if len(arg) >= 2 and arg[0] == '"' and arg[-1] == '"': return arg[1:-1] # is string?
	
	if not is_valid_defname(arg):
		state.error("preprocessor eval single: '" + arg + "' is not a valid macro name")
		return 0
	if arg not in state.macros:
		state.error("preprocessor eval single: '" + arg + "' is unknown")
		return 0
	try:
		resolved = state.macros[arg]()
	except Exception as e:
		state.error("preprocessor eval single error on '" + arg + "': " + str(e))
		return 0
	return cpreprocess_evaluate_cond(state, resolved)

def cpreprocess_evaluate_cond(stateStruct, condstr):
	state = 0
	bracketLevel = 0
	substr = ""
	laststr = ""
	lasteval = None
	op = None
	prefixOp = None
	opstr = ""
	args = []
	i = 0
	while i < len(condstr):
		c = condstr[i]
		i += 1
		breakLoop = False
		while not breakLoop:
			breakLoop = True
			
			if state == 0:
				if c == "(":
					if laststr == "":
						state = 1
						bracketLevel = 1
					else:
						state = 10
						breakLoop = False
				elif c == ")":
					stateStruct.error("preprocessor: runaway ')' in " + repr(condstr))
					return
				elif c in SpaceChars:
					if laststr == "defined": state = 5 
					elif laststr != "": state = 10
					else: pass
				elif c in OpChars:
					state = 10
					breakLoop = False
				elif c == '"':
					if laststr == "":
						state = 20
					else:
						stateStruct.error("preprocessor: '\"' not expected")
						return
				elif c == "'":
					if laststr == "":
						state = 22
					else:
						stateStruct.error("preprocessor: \"'\" not expected")
						return
				else:
					laststr += c
			elif state == 1: # in bracket
				if c == "(":
					bracketLevel += 1
				if c == ")":
					bracketLevel -= 1
					if bracketLevel == 0:
						neweval = cpreprocess_evaluate_cond(stateStruct, substr)
						state = 18
						if prefixOp is not None:
							neweval = prefixOp(neweval)
							prefixOp = None
						if op is not None: lasteval = op(lasteval, neweval)
						else: lasteval = neweval
						substr = ""
					else: # bracketLevel > 0
						substr += c
				elif c == '"':
					state = 2
					substr += c
				else:
					substr += c
			elif state == 2: # in str in bracket
				substr += c
				if c == "\\": state = 3
				elif c == '"': state = 1
				else: pass
			elif state == 3: # in escape in str in bracket
				substr += c
				state = 2
			elif state == 5: # after "defined" without brackets (yet)
				if c in SpaceChars: pass
				elif c == "(":
					state = 10
					breakLoop = False
				elif c == ")":
					stateStruct.error("preprocessor eval: 'defined' invalid in '" + condstr + "'")
					return
				else:
					laststr = c
					state = 6
			elif state == 6: # chars after "defined"
				if c in LetterChars + "_" + NumberChars:
					laststr += c
				else:
					macroname = laststr
					if not is_valid_defname(macroname):
						stateStruct.error("preprocessor eval defined-check: '" + macroname + "' is not a valid macro name")
						return
					neweval = macroname in stateStruct.macros
					if prefixOp is not None:
						neweval = prefixOp(neweval)
						prefixOp = None
					oldlast = lasteval
					if op is not None: lasteval = op(lasteval, neweval)
					else: lasteval = neweval
					opstr = ""
					laststr = ""
					state = 18
					breakLoop = False
			elif state == 10: # after identifier
				if c in SpaceChars: pass
				elif c in OpChars:
					if laststr != "":
						neweval = cpreprocess_evaluate_single(stateStruct, laststr)
						if prefixOp is not None:
							neweval = prefixOp(neweval)
							prefixOp = None
						if op is not None: lasteval = op(lasteval, neweval)
						else: lasteval = neweval
						laststr = ""
					opstr = ""
					state = 18
					breakLoop = False
				elif c == "(":
					state = 11
					bracketLevel = 1
					args = []
				else:
					stateStruct.error("preprocessor eval: '" + c + "' not expected after '" + laststr + "' in state 10 with '" + condstr + "'")
					return
			elif state == 11: # after "(" after identifier
				if c == "(":
					if len(args) == 0: args = [""]
					args[-1] += c
					bracketLevel += 1
					state = 12
				elif c == ")":
					macroname = laststr
					if macroname == "defined":
						if len(args) != 1:
							stateStruct.error("preprocessor eval defined-check args invalid: " + str(args))
							return
						else:
							macroname = args[0]
							if not is_valid_defname(macroname):
								stateStruct.error("preprocessor eval defined-check: '" + macroname + "' is not a valid macro name")
								return
							neweval = macroname in stateStruct.macros
					else:
						if not is_valid_defname(macroname):
							stateStruct.error("preprocessor eval call: '" + macroname + "' is not a valid macro name in " + repr(condstr))
							return
						if macroname not in stateStruct.macros:
							stateStruct.error("preprocessor eval call: '" + macroname + "' is unknown")
							return
						macro = stateStruct.macros[macroname]
						try:
							resolved = macro.eval(stateStruct, args)
						except Exception as e:
							stateStruct.error("preprocessor eval call on '" + macroname + "': error " + str(e))
							return
						neweval = cpreprocess_evaluate_cond(stateStruct, resolved)
					
					if prefixOp is not None:
						neweval = prefixOp(neweval)
						prefixOp = None
					oldlast = lasteval
					if op is not None: lasteval = op(lasteval, neweval)
					else: lasteval = neweval
					#print "after ):", laststr, args, neweval, op.func_code.co_firstlineno if op else "no-op", oldlast, "->", lasteval
					laststr = ""
					opstr = ""
					state = 18
				elif c == '"':
					if len(args) == 0: args = [""]
					args[-1] += c
					state = 13
				elif c == ",": args += [""]
				else:
					if len(args) == 0: args = [""]
					args[-1] += c
			elif state == 12: # in additional "(" after "(" after identifier
				args[-1] += c
				if c == "(": bracketLevel += 1
				elif c == ")":
					bracketLevel -= 1
					if bracketLevel == 1: state = 11
				elif c == '"': state = 13
				else: pass
			elif state == 13: # in str after "(" after identifier
				args[-1] += c
				if c == "\\": state = 14
				elif c == '"':
					if bracketLevel > 1: state = 12
					else: state = 11
				else: pass
			elif state == 14: # in escape in str after "(" after identifier
				args[-1] += c
				state = 13
			elif state == 18: # op after identifier/expression
				if c in OpChars: opstr += c
				else:
					if opstr == "":
						if c in SpaceChars: pass
						else:
							stateStruct.error("preprocessor eval: expected op but got '" + c + "' in '" + condstr + "' in state 18")
							return
					else:
						if opstr == "&&":
							op = lambda x,y: x and y
							# short path check
							if not lasteval: return lasteval
						elif opstr == "||":
							op = lambda x,y: x or y
							# short path check
							if lasteval: return lasteval
						elif opstr in OpBinFuncs:
							op = OpBinFuncs[opstr]
							if OpPrecedences[opstr] >= 6: # +,-,==, etc
								# WARNING/HACK: guess that the following has lower or equal precedence :)
								# HACK: add "()"
								j = i
								while j < len(condstr):
									if condstr[j] == "'":
										j += 1
										while j < len(condstr):
											if condstr[j] == "'": break
											if condstr[j] == "\\": j += 1
											j += 1
										continue
									if condstr[j] == '"':
										j += 1
										while j < len(condstr):
											if condstr[j] == '"': break
											if condstr[j] == "\\": j += 1
											j += 1
										continue
									if condstr[j] in OpChars:
										while j < len(condstr) and condstr[j] in OpChars:
											j += 1
										if j < len(condstr):
											condstr = condstr[:j] + "(" + condstr[j:] + ")"
										break
									j += 1
						elif opstr in OpPrefixFuncs:
							newprefixop = OpPrefixFuncs[opstr]
							if prefixOp: prefixOp = lambda x: prefixOp(newprefixop(x))
							else: prefixOp = newprefixop
						else:
							stateStruct.error("invalid op '" + opstr + "' with '" + c + "' following in '" + condstr + "'")
							return
						opstr = ""
						laststr = ""
						state = 0
						breakLoop = False
			elif state == 20: # in str
				if c == "\\": state = 21
				elif c == '"':
					state = 0
					neweval = laststr
					laststr = ""
					if prefixOp is not None:
						neweval = prefixOp(neweval)
						prefixOp = None
					if op is not None: lasteval = op(lasteval, neweval)
					else: lasteval = neweval
				else: laststr += c
			elif state == 21: # in escape in str
				laststr += simple_escape_char(c)
				state = 20
			elif state == 22: # in char
				if c == "\\": state = 23
				elif c == "'":
					state = 0
					neweval = laststr
					laststr = ""
					if prefixOp is not None:
						neweval = prefixOp(neweval)
						prefixOp = None
					if op is not None: lasteval = op(lasteval, neweval)
					else: lasteval = neweval
				else: laststr += c
			elif state == 23: # in escape in char
				laststr += simple_escape_char(c)
				state = 22
			else:
				stateStruct.error("internal error in preprocessor evaluation: state " + str(state))
				return
	
	if state in (0,10):
		if laststr != "":
			neweval = cpreprocess_evaluate_single(stateStruct, laststr)
			if prefixOp is not None:
				neweval = prefixOp(neweval)
				prefixOp = None
			if op is not None: lasteval = op(lasteval, neweval)
			else: lasteval = neweval
	elif state == 6:
		macroname = laststr
		if not is_valid_defname(macroname):
			stateStruct.error("preprocessor eval defined-check: '" + macroname + "' is not a valid macro name")
			return
		neweval = macroname in stateStruct.macros
		if prefixOp is not None:
			neweval = prefixOp(neweval)
			prefixOp = None
		oldlast = lasteval
		if op is not None: lasteval = op(lasteval, neweval)
		else: lasteval = neweval
	elif state == 18: # expected op
		if opstr != "":
			stateStruct.error("preprocessor eval: unfinished op: '" + opstr + "'")
		else: pass
	else:
		stateStruct.error("preprocessor eval: invalid argument: '" + condstr + "'. unfinished state " + str(state))
	
	#print "eval:", condstr, "->", lasteval
	return lasteval

def cpreprocess_handle_include(state, arg):
	arg = arg.strip()
	if len(arg) < 2:
		state.error("invalid include argument: '" + arg + "'")
		return
	if arg[0] == '"' and arg[-1] == '"':
		local = True
		filename = arg[1:-1]
	elif arg[0] == "<" and arg[-1] == ">":
		local = False
		filename = arg[1:-1]
	else:
		state.error("invalid include argument: '" + arg + "'")
		return
	for c in state.preprocess_file(filename=filename, local=local): yield c

def cpreprocess_handle_def(stateStruct, arg):
	state = 0
	macroname = ""
	args = None
	rightside = ""
	for c in arg:
		if state == 0:
			if c in SpaceChars:
				if macroname != "": state = 3
			elif c == "(":
				state = 2
				args = []
			else: macroname += c
		elif state == 2: # after "("
			if c in SpaceChars: pass
			elif c == ",": args += [""]
			elif c == ")": state = 3
			else:
				if not args: args = [""]
				args[-1] += c
		elif state == 3: # rightside
			rightside += c
	
	if not is_valid_defname(macroname):
		stateStruct.error("preprocessor define: '" + macroname + "' is not a valid macro name")
		return

	if macroname in stateStruct.macros:
		stateStruct.error("preprocessor define: '" + macroname + "' already defined." +
						  " previously defined at " + stateStruct.macros[macroname].defPos)
		# pass through to use new definition
	
	macro = Macro(stateStruct, macroname, args, rightside)
	stateStruct.macros[macroname] = macro
	return macro

def cpreprocess_handle_undef(state, arg):
	arg = arg.strip()
	if not is_valid_defname(arg):
		state.error("preprocessor: '" + arg + "' is not a valid macro name")
		return
	if not arg in state.macros:
		# This is not an error. Just ignore.
		return
	state.macros.pop(arg)
	
def handle_cpreprocess_cmd(state, cmd, arg):
	#if not state._preprocessIgnoreCurrent:
	#	print "cmd", cmd, arg

	if cmd == "ifdef":
		state._preprocessIfLevels += [0]
		if any(map(lambda x: x != 1, state._preprocessIfLevels[:-1])): return # we don't really care
		check = cpreprocess_evaluate_ifdef(state, arg)
		if check: state._preprocessIfLevels[-1] = 1
		
	elif cmd == "ifndef":
		state._preprocessIfLevels += [0]
		if any(map(lambda x: x != 1, state._preprocessIfLevels[:-1])): return # we don't really care
		check = not cpreprocess_evaluate_ifdef(state, arg)
		if check: state._preprocessIfLevels[-1] = 1

	elif cmd == "if":
		state._preprocessIfLevels += [0]
		if any(map(lambda x: x != 1, state._preprocessIfLevels[:-1])): return # we don't really care
		check = cpreprocess_evaluate_cond(state, arg)
		if check: state._preprocessIfLevels[-1] = 1
		
	elif cmd == "elif":
		if any(map(lambda x: x != 1, state._preprocessIfLevels[:-1])): return # we don't really care
		if len(state._preprocessIfLevels) == 0:
			state.error("preprocessor: elif without if")
			return
		if state._preprocessIfLevels[-1] >= 1:
			state._preprocessIfLevels[-1] = 2 # we already had True
		else:
			check = cpreprocess_evaluate_cond(state, arg)
			if check: state._preprocessIfLevels[-1] = 1

	elif cmd == "else":
		if any(map(lambda x: x != 1, state._preprocessIfLevels[:-1])): return # we don't really care
		if len(state._preprocessIfLevels) == 0:
			state.error("preprocessor: else without if")
			return
		if state._preprocessIfLevels[-1] >= 1:
			state._preprocessIfLevels[-1] = 2 # we already had True
		else:
			state._preprocessIfLevels[-1] = 1
	
	elif cmd == "endif":
		if len(state._preprocessIfLevels) == 0:
			state.error("preprocessor: endif without if")
			return
		state._preprocessIfLevels = state._preprocessIfLevels[0:-1]
	
	elif cmd == "include":
		if state._preprocessIgnoreCurrent: return
		for c in cpreprocess_handle_include(state, arg): yield c

	elif cmd == "define":
		if state._preprocessIgnoreCurrent: return
		cpreprocess_handle_def(state, arg)
	
	elif cmd == "undef":
		if state._preprocessIgnoreCurrent: return
		cpreprocess_handle_undef(state, arg)
				
	elif cmd == "pragma":
		pass # ignore at all right now
	
	elif cmd == "error":
		if state._preprocessIgnoreCurrent: return # we don't really care
		state.error("preprocessor error command: " + arg)

	elif cmd == "warning":
		if state._preprocessIgnoreCurrent: return # we don't really care
		state.error("preprocessor warning command: " + arg)

	else:
		if state._preprocessIgnoreCurrent: return # we don't really care
		state.error("preprocessor command " + cmd + " unknown")
		
	state._preprocessIgnoreCurrent = any(map(lambda x: x != 1, state._preprocessIfLevels))

def cpreprocess_parse(stateStruct, input):
	cmd = ""
	arg = ""
	state = 0
	statebeforecomment = None
	for c in input:		
		breakLoop = False
		while not breakLoop:
			breakLoop = True

			if state == 0:
				if c == "#":
					cmd = ""
					arg = None
					state = 1
				elif c == "/":
					statebeforecomment = 0
					state = 20
				elif c == '"':
					if not stateStruct._preprocessIgnoreCurrent: yield c
					state = 10
				elif c == "'":
					if not stateStruct._preprocessIgnoreCurrent: yield c
					state = 12
				else:
					if not stateStruct._preprocessIgnoreCurrent: yield c
			elif state == 1: # start of preprocessor command
				if c in SpaceChars: pass
				elif c == "\n": state = 0
				else:
					cmd = c
					state = 2
			elif state == 2: # in the middle of the command
				if c in SpaceChars:
					if arg is None: arg = ""
					else: arg += c
				elif c == "(":
					if arg is None: arg = c
					else: arg += c
				elif c == "/":
					state = 20
					statebeforecomment = 2
				elif c == '"':
					state = 3
					if arg is None: arg = ""
					arg += c
				elif c == "'":
					state = 4
					if arg is None: arg = ""
					arg += c
				elif c == "\\": state = 5 # escape next
				elif c == "\n":
					for c in handle_cpreprocess_cmd(stateStruct, cmd, arg): yield c
					state = 0
				else:
					if arg is None: cmd += c
					else: arg += c
			elif state == 3: # in '"' in arg in command
				arg += c
				if c == "\n":
					stateStruct.error("preproc parse: unfinished str")
					state = 0
				elif c == "\\": state = 35
				elif c == '"': state = 2
			elif state == 35: # in esp in '"' in arg in command
				arg += c
				state = 3
			elif state == 4: # in "'" in arg in command
				arg += c
				if c == "\n":
					stateStruct.error("preproc parse: unfinished char str")
					state = 0
				elif c == "\\": state = 45
				elif c == "'": state = 2
			elif state == 45: # in esp in "'" in arg in command
				arg += c
				state = 4
			elif state == 5: # after escape in arg in command
				if c == "\n": state = 2
				else: pass # ignore everything, wait for newline
			elif state == 10: # after '"'
				if not stateStruct._preprocessIgnoreCurrent: yield c
				if c == "\\": state = 11
				elif c == '"': state = 0
				else: pass
			elif state == 11: # escape in "str
				if not stateStruct._preprocessIgnoreCurrent: yield c
				state = 10
			elif state == 12: # after "'"
				if not stateStruct._preprocessIgnoreCurrent: yield c
				if c == "\\": state = 13
				elif c == "'": state = 0
				else: pass
			elif state == 13: # escape in 'str
				if not stateStruct._preprocessIgnoreCurrent: yield c
				state = 12
			elif state == 20: # after "/", possible start of comment
				if c == "*": state = 21 # C-style comment
				elif c == "/": state = 25 # C++-style comment
				else:
					state = statebeforecomment
					statebeforecomment = None
					if state == 0:
						if not stateStruct._preprocessIgnoreCurrent: yield "/"
					elif state == 2:
						if arg is None: arg = ""
						arg += "/"
						breakLoop = False
					else:
						stateStruct.error("preproc parse: internal error after possible comment. didn't expect state " + str(state))
						state = 0 # best we can do
			elif state == 21: # C-style comment
				if c == "*": state = 22
				else: pass
			elif state == 22: # C-style comment after "*"
				if c == "/":
					state = statebeforecomment
					statebeforecomment = None
				elif c == "*": pass
				else: state = 21
			elif state == 25: # C++-style comment
				if c == "\n":
					state = statebeforecomment
					statebeforecomment = None
					breakLoop = False # rehandle return
				else: pass
			else:
				stateStruct.error("internal error: invalid state " + str(state))
				state = 0 # reset. it's the best we can do

		if c == "\n": stateStruct.incIncludeLineChar(line=1)
		elif c == "\t": stateStruct.incIncludeLineChar(char=4, charMod=4)
		else: stateStruct.incIncludeLineChar(char=1)

class _CBase:
	def __init__(self, content=None, rawstr=None, **kwargs):
		self.content = content
		self.rawstr = rawstr
		for k,v in kwargs.items():
			setattr(self, k, v)
	def __repr__(self):
		if self.content is None: return "<" + self.__class__.__name__ + ">"
		return "<" + self.__class__.__name__ + " " + repr(self.content) + ">"
	def __eq__(self, other):
		return self.__class__ is other.__class__ and self.content == other.content
	def __ne__(self, other):
		return not self == other
	def __hash__(self): return hash(self.__class__) + 31 * hash(self.content)
	def asCCode(self, indent=""): return indent + self.content

class CStr(_CBase):
	def __repr__(self): return "<" + self.__class__.__name__ + " " + repr(self.content) + ">"
	def asCCode(self, indent=""): return indent + '"' + escape_cstr(self.content) + '"'
class CChar(_CBase):
	def __init__(self, content=None, rawstr=None, **kwargs):
		if isinstance(content, (unicode,str)): content = ord(content)
		assert isinstance(content, int), "CChar expects int, got " + repr(content)
		assert 0 <= content <= 255, "CChar expects number in range 0-255, got " + str(content)
		_CBase.__init__(self, content, rawstr, **kwargs)
	def __repr__(self): return "<" + self.__class__.__name__ + " " + repr(self.content) + ">"
	def asCCode(self, indent=""): return indent + "'" + escape_cstr(self.content) + '"'
class CNumber(_CBase):
	def asCCode(self, indent=""): return indent + self.rawstr
class CIdentifier(_CBase): pass
class COp(_CBase): pass
class CSemicolon(_CBase):
	def asCCode(self, indent=""): return indent + ";"	
class COpeningBracket(_CBase): pass
class CClosingBracket(_CBase): pass

def cpre2_parse_number(stateStruct, s):
	if len(s) > 1 and s[0] == "0" and s[1] in NumberChars:
		try:
			s = s.rstrip("ULul")
			return long(s, 8)
		except Exception as e:
			stateStruct.error("cpre2_parse_number: " + s + " looks like octal but got error " + str(e))
			return 0
	if len(s) > 1 and s[0] == "0" and s[1] in "xX":
		try:
			s = s.rstrip("ULul")
			return long(s, 16)
		except Exception as e:
			stateStruct.error("cpre2_parse_number: " + s + " looks like hex but got error " + str(e))
			return 0
	try:
		s = s.rstrip("ULul")
		return long(s)
	except Exception as e:
		stateStruct.error("cpre2_parse_number: " + s + " cannot be parsed: " + str(e))
		return 0

def cpre2_parse(stateStruct, input, brackets = None):
	state = 0
	if brackets is None: brackets = []
	laststr = ""
	macroname = ""
	macroargs = []
	macrobrackets = []
	import itertools
	for c in itertools.chain(input, "\n"):
		breakLoop = False
		while not breakLoop:
			breakLoop = True
			if state == 0:
				if c in SpaceChars + "\n": pass
				elif c in NumberChars:
					laststr = c
					state = 10
				elif c == '"':
					laststr = ""
					state = 20
				elif c == "'":
					laststr = ""
					state = 25
				elif c in LetterChars + "_":
					laststr = c
					state = 30
				elif c in OpeningBrackets:
					yield COpeningBracket(c, brackets=list(brackets))
					brackets += [c]
				elif c in ClosingBrackets:
					if len(brackets) == 0 or ClosingBrackets[len(OpeningBrackets) - OpeningBrackets.index(brackets[-1]) - 1] != c:
						stateStruct.error("cpre2 parse: got '" + c + "' but bracket level was " + str(brackets))
					else:
						brackets[:] = brackets[:-1]
						yield CClosingBracket(c, brackets=list(brackets))
				elif c in OpChars:
					laststr = ""
					state = 40
					breakLoop = False
				elif c == ";": yield CSemicolon()
				else:
					stateStruct.error("cpre2 parse: didn't expected char '" + c + "'")
			elif state == 10: # number
				if c in NumberChars: laststr += c
				elif c in LetterChars + "_": laststr += c # error handling will be in number parsing, not here
				else:
					yield CNumber(cpre2_parse_number(stateStruct, laststr), laststr)
					laststr = ""
					state = 0
					breakLoop = False
			elif state == 20: # "str
				if c == '"':
					yield CStr(laststr)
					laststr = ""
					state = 0
				elif c == "\\": state = 21
				else: laststr += c
			elif state == 21: # escape in "str
				laststr += simple_escape_char(c)
				state = 20
			elif state == 25: # 'str
				if c == "'":
					yield CChar(laststr)
					laststr = ""
					state = 0
				elif c == "\\": state = 26
				else: laststr += c
			elif state == 26: # escape in 'str
				laststr += simple_escape_char(c)
				state = 25
			elif state == 30: # identifier
				if c in NumberChars + LetterChars + "_": laststr += c
				else:
					if laststr in stateStruct.macros:
						macroname = laststr
						macroargs = []
						macrobrackets = []
						state = 31
						if stateStruct.macros[macroname].args is None:
							state = 32 # finalize macro directly. there can't be any args
						breakLoop = False
					else:
						yield CIdentifier(laststr)
						laststr = ""
						state = 0
						breakLoop = False
			elif state == 31: # after macro identifier
				if not macrobrackets and c in SpaceChars + "\n": pass
				elif c in OpeningBrackets:
					if len(macrobrackets) == 0 and c != "(":
						state = 32
						breakLoop = False
					else:
						if macrobrackets:
							if len(macroargs) == 0: macroargs = [""]
							macroargs[-1] += c
						macrobrackets += [c]
				elif c in ClosingBrackets:
					if len(macrobrackets) == 0:
						state = 32
						breakLoop = False
					elif ClosingBrackets[len(OpeningBrackets) - OpeningBrackets.index(macrobrackets[-1]) - 1] != c:
						stateStruct.error("cpre2 parse: got '" + c + "' but macro-bracket level was " + str(macrobrackets))
						# ignore
					else:
						macrobrackets[:] = macrobrackets[:-1]
						if macrobrackets:
							if len(macroargs) == 0: macroargs = [""]
							macroargs[-1] += c
						else:
							state = 32
							# break loop, we consumed this char
				elif c == ",":
					if macrobrackets:
						if len(macrobrackets) == 1:
							if len(macroargs) == 0: macroargs = ["",""]
							else: macroargs += [""]
						else:
							if len(macroargs) == 0: macroargs = [""]
							macroargs[-1] += c
					else:
						state = 32
						breakLoop = False
				else:
					if macrobrackets:
						if len(macroargs) == 0: macroargs = [""]
						macroargs[-1] += c
						if c == "'": state = 311
						elif c == '"': state = 313
					else:
						state = 32
						breakLoop = False
			elif state == 311: # in 'str in macro
				macroargs[-1] += c
				if c == "'": state = 31
				elif c == "\\": state = 312
			elif state == 312: # in escape in 'str in macro
				macroargs[-1] += c
				state = 311
			elif state == 313: # in "str in macro
				macroargs[-1] += c
				if c == '"': state = 31
				elif c == "\\": state = 314
			elif state == 314: # in escape in "str in macro
				macroargs[-1] += c
				state = 313
			elif state == 32: # finalize macro
				try:
					resolved = stateStruct.macros[macroname].eval(stateStruct, macroargs)
					for t in cpre2_parse(stateStruct, resolved, brackets):
						yield t
				except Exception as e:
					stateStruct.error("cpre2 parse unfold macro " + macroname + " error: " + repr(e))
				state = 0
				breakLoop = False
			elif state == 40: # op
				if c in OpChars:
					if laststr != "" and laststr + c not in LongOps:
						yield COp(laststr)
						laststr = ""
					laststr += c
				else:
					yield COp(laststr)
					laststr = ""
					state = 0
					breakLoop = False
			else:
				stateStruct.error("cpre2 parse: internal error. didn't expected state " + str(state))

def cpre2_tokenstream_asCCode(input):
	needspace = False
	wantnewline = False
	indentLevel = ""
	needindent = False
	
	for token in input:
		if wantnewline:
			if isinstance(token, CSemicolon): pass
			else:
				yield "\n"
				needindent = True
			wantnewline = False
			needspace = False
		elif needspace:
			if isinstance(token, CSemicolon): pass
			elif token == COpeningBracket("("): pass
			elif token == CClosingBracket(")"): pass
			elif token == COpeningBracket("["): pass
			elif token == CClosingBracket("]"): pass
			elif token in [COp("++"), COp("--"), COp(",")]: pass
			else:
				yield " "
			needspace = False
		
		if token == CClosingBracket("}"): indentLevel = indentLevel[:-1]
		if needindent:
			yield indentLevel
			needindent = False
			
		yield token.asCCode()
		
		if token == COpeningBracket("{"): indentLevel += "\t"
		
		if token == CSemicolon(): wantnewline = True
		elif token == COpeningBracket("{"): wantnewline = True
		elif token == CClosingBracket("}"): wantnewline = True
		elif isinstance(token, COpeningBracket): pass
		elif isinstance(token, CClosingBracket): pass
		else: needspace = True

	
class CBody:
	def __init__(self, parent):
		self.parent = parent
		self._bracketlevel = []
		self.typedefs = {}
		self.structs = {}
		self.unions = {}
		self.enums = {}
		self.funcs = {}
		self.vars = {}
		self.enumconsts = {}
		self.contentlist = []
	def __str__(self): return str(self.contentlist)
	def __repr__(self): return "<CBody " + str(self) + ">"
	def asCCode(self, indent=""):
		s = indent + "{\n"
		for c in self.contentlist:
			s += asCCode(c, indent + "\t", fullDecl=True) + ";\n"
		s += indent + "}"
		return s
	
class CEnumBody(CBody):
	def asCCode(self, indent=""):
		s = indent + "{\n"
		for c in self.contentlist:
			s += asCCode(c, indent + "\t") + ",\n"
		s += indent + "}"
		return s
		
def findIdentifierInBody(body, name):
	if name in body.enumconsts:
		return body.enumconsts[name]
	if body.parent is not None:
		return findIdentifierInBody(body.parent, name)
	return None

def make_type_from_typetokens(stateStruct, type_tokens):
	if len(type_tokens) == 1 and isinstance(type_tokens[0], _CBaseWithOptBody):
		t = type_tokens[0]
	elif tuple(type_tokens) in stateStruct.CBuiltinTypes:
		t = CBuiltinType(tuple(type_tokens))
	elif len(type_tokens) > 1 and type_tokens[-1] == "*":
		t = CPointerType(make_type_from_typetokens(stateStruct, type_tokens[:-1]))
	elif len(type_tokens) == 1 and type_tokens[0] in stateStruct.StdIntTypes:
		t = CStdIntType(type_tokens[0])
	elif len(type_tokens) == 1 and type_tokens[0] in stateStruct.typedefs:
		t = CTypedefType(type_tokens[0])
	else:
		t = None
	return t

def asCCode(stmnt, indent="", fullDecl=False):
	if not fullDecl:
		if isinstance(stmnt, CFunc): return indent + stmnt.name
		if isinstance(stmnt, CStruct): return indent + "struct " + stmnt.name
		if isinstance(stmnt, CUnion): return indent + "union " + stmnt.name
		if isinstance(stmnt, CEnum): return indent + "enum " + stmnt.name
	if hasattr(stmnt, "asCCode"):
		return stmnt.asCCode(indent)
	assert False, "don't know how to handle " + str(stmnt)
	
class _CBaseWithOptBody:
	NameIsRelevant = True
	AutoAddToContent = True
	AlwaysNonZero = False
	StrOutAttribList = [
		("args", bool, None, str),
		("arrayargs", bool, None, str),
		("body", None, None, lambda x: "<...>"),
		("value", None, None, str),
		("defPos", None, "@", str),
	]
	
	def __init__(self, **kwargs):
		self._type_tokens = []
		self._bracketlevel = None
		self._finalized = False
		self.defPos = None
		self.type = None
		self.attribs = []
		self.name = None
		self.args = []
		self.arrayargs = []
		self.body = None
		self.value = None
		self.parent = None
		for k,v in kwargs.items():
			setattr(self, k, v)
			
	@classmethod
	def overtake(cls, obj):
		obj.__class__ = cls
		# no cls.__init__ because it would overwrite all our attribs!
		
	def isDerived(self):
		return self.__class__ != _CBaseWithOptBody

	def __str__(self):
		if self.NameIsRelevant:
			name = ("'" + self.name + "' ") if self.name else "<noname> "
		else:
			name = ("name: '" + self.name + "' ") if self.name else ""
		t = self.type or self._type_tokens
		l = []
		if self.attribs: l += [("attribs", self.attribs)]
		if t: l += [("type", t)]
		for attrName,addCheck,displayName,displayFunc in self.StrOutAttribList:
			a = getattr(self, attrName)
			if addCheck is None: addCheck = lambda x: x is not None
			if addCheck(a):
				if displayName is None: displayName = attrName
				l += [(displayName, displayFunc(a))]
		return \
			self.__class__.__name__ + " " + \
			name + \
			", ".join(map((lambda a: a[0] + ": " + str(a[1])), l))

	def __repr__(self): return "<" + str(self) + ">"

	def __nonzero__(self):
		return \
			self.AlwaysNonZero or \
			bool(self._type_tokens) or \
			bool(self.type) or \
			bool(self.name) or \
			bool(self.args) or \
			bool(self.arrayargs) or \
			bool(self.body)
	
	def finalize(self, stateStruct, addToContent = None):
		if self._finalized:
			stateStruct.error("internal error: " + str(self) + " finalized twice")
			return
		self._finalized = True
		if self.defPos is None:
			self.defPos = stateStruct.curPosAsStr()
		if not self: return
		
		if addToContent is None: addToContent = self.AutoAddToContent
		
		#print "finalize", self, "at", stateStruct.curPosAsStr()
		if addToContent and self.parent is not None and self.parent.body and hasattr(self.parent.body, "contentlist"):
			self.parent.body.contentlist.append(self)
	
	def copy(self):
		import copy
		return copy.deepcopy(self, memo={id(self.parent): self.parent})

	def getCType(self, stateStruct):
		raise Exception(str(self) + " cannot be converted to a C type")

	def findAttrib(self, stateStruct, attrib):
		if self.body is None:
			# it probably is the pre-declaration. but we might find the real-one
			if isinstance(self, CStruct): D = "structs"
			elif isinstance(self, CUnion): D = "unions"
			elif isinstance(self, CEnum): D = "enums"
			self = getattr(stateStruct, D).get(self.name, self)
		if self.body is None: return None
		for c in self.body.contentlist:
			if not isinstance(c, CVarDecl): continue
			if c.name == attrib: return c
		return None
	
	def asCCode(self, indent=""):
		raise NotImplementedError(str(self) + " asCCode not implemented")
	
class CTypedef(_CBaseWithOptBody):
	def finalize(self, stateStruct):
		if self._finalized:
			stateStruct.error("internal error: " + str(self) + " finalized twice")
			return
		
		self.type = make_type_from_typetokens(stateStruct, self._type_tokens)
		_CBaseWithOptBody.finalize(self, stateStruct)
		
		if self.type is None:
			stateStruct.error("finalize typedef " + str(self) + ": type is unknown")
			return
		if self.name is None:
			stateStruct.error("finalize typedef " + str(self) + ": name is unset")
			return

		self.parent.body.typedefs[self.name] = self.type
	def getCType(self, stateStruct): return getCType(self.type, stateStruct)
	def asCCode(self, indent=""):
		return indent + "typedef\n" + asCCode(self.type, indent, fullDecl=True) + " " + self.name
	
class CFuncPointerDecl(_CBaseWithOptBody):
	def finalize(self, stateStruct, addToContent=None):
		if self._finalized:
			stateStruct.error("internal error: " + str(self) + " finalized twice")
			return
		
		self.type = make_type_from_typetokens(stateStruct, self._type_tokens)
		_CBaseWithOptBody.finalize(self, stateStruct, addToContent)
		
		if self.type is None:
			stateStruct.error("finalize " + str(self) + ": type is unknown")
		# Name can be unset. It depends where this is declared.
	def getCType(self, stateStruct):
		restype = getCType(self.type, stateStruct)
		argtypes = map(lambda a: getCType(a, stateStruct), self.args)
		return ctypes.CFUNCTYPE(restype, *argtypes)
	def asCCode(self, indent=""):
		return indent + asCCode(self.type) + "(*" + self.name + ") (" + ", ".join(map(asCCode, self.args)) + ")"

def _finalizeBasicType(obj, stateStruct, dictName=None, listName=None, addToContent=None):
	if obj._finalized:
		stateStruct.error("internal error: " + str(obj) + " finalized twice")
		return
	
	if addToContent is None:
		addToContent = obj.name is not None

	if obj.type is None:
		obj.type = make_type_from_typetokens(stateStruct, obj._type_tokens)
	_CBaseWithOptBody.finalize(obj, stateStruct, addToContent=addToContent)
	
	if addToContent and hasattr(obj.parent, "body"):
		d = getattr(obj.parent.body, dictName or listName)
		if dictName:
			if obj.name is None:
				# might be part of a typedef, so don't error
				return
	
			# If the body is empty, it was a pre-declaration and it is ok to overwrite it now.
			# Otherwise however, it is an error.
			if obj.name in d and d[obj.name].body is not None:
				stateStruct.error("finalize " + str(obj) + ": a previous equally named declaration exists: " + str(d[obj.name]))
			else:
				d[obj.name] = obj
		else:
			assert listName is not None
			d.append(obj)

class CFunc(_CBaseWithOptBody):
	finalize = lambda *args, **kwargs: _finalizeBasicType(*args, dictName="funcs", **kwargs)
	def getCType(self, stateStruct):
		restype = getCType(self.type, stateStruct)
		argtypes = map(lambda a: getCType(a, stateStruct), self.args)
		return ctypes.CFUNCTYPE(restype, *argtypes)
	def asCCode(self, indent=""):
		s = indent + asCCode(self.type) + " " + self.name + "(" + ", ".join(map(asCCode, self.args)) + ")"
		if self.body is None: return s
		s += "\n"
		s += asCCode(self.body, indent)
		return s

class CVarDecl(_CBaseWithOptBody):
	finalize = lambda *args, **kwargs: _finalizeBasicType(*args, dictName="vars", **kwargs)
	def clearDeclForNextVar(self):
		if hasattr(self, "bitsize"): delattr(self, "bitsize")
		while self._type_tokens and self._type_tokens[-1] in ("*",):
			self._type_tokens.pop()
	def asCCode(self, indent=""):
		s = indent + asCCode(self.type) + " " + self.name
		if self.body is None: return s
		s += " = "
		s += asCCode(self.body)
		return s
	
def wrapCTypeClassIfNeeded(t):
	if t.__base__ is _ctypes._SimpleCData: return wrapCTypeClass(t)
	else: return t
	
def wrapCTypeClass(t):
	class WrappedType(t): pass
	WrappedType.__name__ = t.__name__
	return WrappedType

def _getCTypeStruct(baseClass, obj, stateStruct):
	if hasattr(obj, "_ctype"): return obj._ctype
	assert hasattr(obj, "body"), str(obj) + " must have the body attrib"
	assert obj.body is not None, str(obj) + ".body must not be None. maybe it was only forward-declarated?"
	class ctype(baseClass): pass
	obj._ctype = ctype
	fields = []
	for c in obj.body.contentlist:
		if not isinstance(c, CVarDecl): continue
		t = getCType(c.type, stateStruct)
		if c.arrayargs:
			if len(c.arrayargs) != 1: raise Exception(str(c) + " has too many array args")
			n = c.arrayargs[0].value
			t = t * n
		elif stateStruct.IndirectSimpleCTypes:
			# See http://stackoverflow.com/questions/6800827/python-ctypes-structure-how-to-access-attributes-as-if-they-were-ctypes-and-not/6801253#6801253
			t = wrapCTypeClassIfNeeded(t)
		if hasattr(c, "bitsize"):
			fields += [(str(c.name), t, c.bitsize)]
		else:
			fields += [(str(c.name), t)]	
	ctype._fields_ = fields
	return ctype
	
class CStruct(_CBaseWithOptBody):
	finalize = lambda *args, **kwargs: _finalizeBasicType(*args, dictName="structs", **kwargs)
	def getCType(self, stateStruct):
		return _getCTypeStruct(ctypes.Structure, self, stateStruct)
	def asCCode(self, indent=""):
		s = indent + "struct " + self.name
		if self.body is None: return s
		return s + "\n" + asCCode(self.body, indent)
		
class CUnion(_CBaseWithOptBody):
	finalize = lambda *args, **kwargs: _finalizeBasicType(*args, dictName="unions", **kwargs)
	def getCType(self, stateStruct):
		return _getCTypeStruct(ctypes.Union, self, stateStruct)
	def asCCode(self, indent=""):
		s = indent + "union " + self.name
		if self.body is None: return s
		return s + "\n" + asCCode(self.body, indent)

def minCIntTypeForNums(a, b=None, minBits=32, maxBits=64, useUnsignedTypes=True):
	if b is None: b = a
	bits = minBits
	while bits <= maxBits:
		if useUnsignedTypes and a >= 0 and b < (1<<bits): return "uint" + str(bits) + "_t"
		elif a >= -(1<<(bits-1)) and b < (1<<(bits-1)): return "int" + str(bits) + "_t"
		bits *= 2
	return None

class CEnum(_CBaseWithOptBody):
	finalize = lambda *args, **kwargs: _finalizeBasicType(*args, dictName="enums", **kwargs)
	def getNumRange(self):
		a,b = 0,0
		for c in self.body.contentlist:
			assert isinstance(c, CEnumConst)
			if c.value < a: a = c.value
			if c.value > b: b = c.value
		return a,b
	def getEnumConst(self, value):
		for c in self.body.contentlist:
			if not isinstance(c, CEnumConst): continue
			if c.value == value: return c
		return None
	def getCType(self, stateStruct):
		a,b = self.getNumRange()
		t = minCIntTypeForNums(a, b)
		if t is None:
			raise Exception(str(self) + " has a too high number range " + str((a,b)))
		t = stateStruct.StdIntTypes[t]
		class EnumType(t):
			_typeStruct = self
			def __repr__(self):
				v = self._typeStruct.getEnumConst(self.value)
				if v is None: v = self.value
				return "<EnumType " + str(v) + ">"
			def __cmp__(self, other):
				return cmp(self.value, other)
		for c in self.body.contentlist:
			if not c.name: continue
			if hasattr(EnumType, c.name): continue
			setattr(EnumType, c.name, c.value)
		return EnumType
	def asCCode(self, indent=""):
		s = indent + "enum " + self.name
		if self.body is None: return s
		return s + "\n" + asCCode(self.body, indent)
	
class CEnumConst(_CBaseWithOptBody):
	def finalize(self, stateStruct, addToContent=None):
		if self._finalized:
			stateStruct.error("internal error: " + str(self) + " finalized twice")
			return

		if self.value is None:
			if self.parent.body.contentlist:
				last = self.parent.body.contentlist[-1]
				if isinstance(last.value, (str,unicode)):
					self.value = unichr(ord(last.value) + 1)
				else:
					self.value = last.value + 1
			else:
				self.value = 0

		_CBaseWithOptBody.finalize(self, stateStruct, addToContent)

		if self.name:
			# self.parent.parent is the parent of the enum
			self.parent.parent.body.enumconsts[self.name] = self
	def getConstValue(self, stateStruct):
		return self.value
	def asCCode(self, indent=""):
		return indent + self.name + " = " + str(self.value)
	
class CFuncArgDecl(_CBaseWithOptBody):
	AutoAddToContent = False	
	def finalize(self, stateStruct, addToContent=False):
		if self._finalized:
			stateStruct.error("internal error: " + str(self) + " finalized twice")
			return
			
		self.type = make_type_from_typetokens(stateStruct, self._type_tokens)
		_CBaseWithOptBody.finalize(self, stateStruct, addToContent=False)
		
		if self.type != CBuiltinType(("void",)):
			self.parent.args += [self]
	def getCType(self, stateStruct):
		return getCType(self.type, stateStruct)
	def asCCode(self, indent=""):
		s = indent + asCCode(self.type)
		if self.name: s += " " + self.name
		return s
	
def _isBracketLevelOk(parentLevel, curLevel):
	if parentLevel is None: parentLevel = []
	if len(parentLevel) > len(curLevel): return False
	return curLevel[:len(parentLevel)] == parentLevel

def _body_parent_chain(stateStruct, parentCObj):
	yieldedStateStruct = False

	for cobj in _obj_parent_chain(stateStruct, parentCObj):
		body = cobj.body
		if isinstance(body, CBody):
			yieldedStateStruct |= body is stateStruct
			yield body

	if not yieldedStateStruct: yield stateStruct

def _obj_parent_chain(stateStruct, parentCObj):
	while parentCObj is not None:
		yield parentCObj
		parentCObj = parentCObj.parent
		
def getObjInBody(body, name):
	if name in body.funcs:
		return body.funcs[name]
	elif name in body.typedefs:
		return body.typedefs[name]
	elif name in body.vars:
		return body.vars[name]
	elif name in body.enumconsts:
		return body.enumconsts[name]
	elif (name,) in getattr(body, "CBuiltinTypes", {}):
		return body.CBuiltinTypes[(name,)]
	elif name in getattr(body, "StdIntTypes", {}):
		return body.StdIntTypes[name]
	return None

def findObjInNamespace(stateStruct, curCObj, name):
	for cobj in _obj_parent_chain(stateStruct, curCObj):
		if isinstance(cobj.body, (CBody,State)):
			obj = getObjInBody(cobj.body, name)
			if obj is not None: return obj
		if isinstance(cobj, CFunc):
			for arg in cobj.args:
				assert isinstance(arg, CFuncArgDecl)
				if arg.name is not None and arg.name == name:
					return arg
	return None

def findCObjTypeInNamespace(stateStruct, curCObj, DictName, name):
	for body in _body_parent_chain(stateStruct, curCObj):
		d = getattr(body, DictName)
		if name in d: return d[name]
	return None

class _CStatementCall(_CBaseWithOptBody):
	AutoAddToContent = False
	base = None
	def __nonzero__(self): return self.base is not None
	def __str__(self):
		s = self.__class__.__name__ + " " + repr(self.base)
		if self.name:
			s += " name: " + self.name
		else:
			s += " args: " + str(self.args)
		return s
	
class CFuncCall(_CStatementCall): # base(args) or (base)args; i.e. can also be a simple cast
	def asCCode(self, indent=""):
		return indent + asCCode(self.base) + "(" + ", ".join(map(asCCode, self.args)) + ")"
class CArrayIndexRef(_CStatementCall): # base[args]
	def asCCode(self, indent=""):
		return indent + asCCode(self.base) + "[" + ", ".join(map(asCCode, self.args)) + "]"
class CAttribAccessRef(_CStatementCall): # base.name
	def asCCode(self, indent=""):
		return indent + asCCode(self.base) + "." + self.name
class CPtrAccessRef(_CStatementCall): # base->name
	def asCCode(self, indent=""):
		return indent + asCCode(self.base) + "->" + self.name

def _create_cast_call(stateStruct, parent, base, token):
	funcCall = CFuncCall(parent=parent)
	funcCall.base = base
	arg = CStatement(parent=funcCall)
	funcCall.args = [arg]
	arg._cpre3_handle_token(stateStruct, token)
	funcCall.finalize(stateStruct)
	return funcCall

def opsDoLeftToRight(stateStruct, op1, op2):
	try: opprec1 = OpPrecedences[op1]
	except:
		stateStruct.error("internal error: statement parsing: op1 " + repr(op1) + " unknown")
		opprec1 = 100
	try: opprec2 = OpPrecedences[op2]
	except:
		stateStruct.error("internal error: statement parsing: op2 " + repr(op2) + " unknown")
		opprec2 = 100
	
	if opprec1 < opprec2:
		return True
	elif opprec1 > opprec2:
		return False
	if op1 in OpsRightToLeft:
		return False
	return True

def getConstValue(stateStruct, obj):
	if hasattr(obj, "getConstValue"): return obj.getConstValue(stateStruct)
	if isinstance(obj, (CNumber,CStr,CChar)):
		return obj.content
	stateStruct.error("don't know how to get const value from " + str(obj))
	return None

class CSizeofSymbol: pass

class CArrayArgs(_CBaseWithOptBody):
	# args is a list of CStatement
	NameIsRelevant = False
	def asCCode(self, indent=""):
		return indent + "{" + ", ".join(map(asCCode, self.args)) + "}"

class CStatement(_CBaseWithOptBody):
	NameIsRelevant = False
	_leftexpr = None
	_middleexpr = None
	_rightexpr = None
	_op = None
	def __nonzero__(self): return bool(self._leftexpr) or bool(self._rightexpr)
	def __repr__(self):
		s = self.__class__.__name__
		#s += " " + repr(self._tokens) # debug
		if self._leftexpr is not None: s += " " + repr(self._leftexpr)
		if self._op == COp("?:"):
			s += " ? " + repr(self._middleexpr)
			s += " : " + repr(self._rightexpr)
		elif self._op is not None or self._rightexpr is not None:
			s += " "
			s += str(self._op)
			if self._rightexpr is not None:
				s += " "
				s += repr(self._rightexpr)
		if self.defPos is not None: s += " @: " + self.defPos
		return "<" + s + ">"
	__str__ = __repr__
	def _initStatement(self):
		self._state = 0
		self._tokens = []
	def __init__(self, **kwargs):
		self._initStatement()
		_CBaseWithOptBody.__init__(self, **kwargs)
	@classmethod
	def overtake(cls, obj):
		obj.__class__ = cls
		obj._initStatement()
	def _handlePushedErrorForUnknown(self, stateStruct):
		if isinstance(self._leftexpr, CUnknownType):
			s = getattr(self, "_pushedErrorForUnknown", False)
			if not s:
				stateStruct.error("statement parsing: identifier '" + self._leftexpr.name + "' unknown")
				self._pushedErrorForUnknown = True
	def finalize(self, stateStruct, addToContent=None):
		self._handlePushedErrorForUnknown(stateStruct)
		_CBaseWithOptBody.finalize(self, stateStruct, addToContent)
	def _cpre3_handle_token(self, stateStruct, token):
		self._tokens += [token]
		
		if self._state == 5 and token == COp(":"):
			if isinstance(self._leftexpr, CUnknownType):
				CGotoLabel.overtake(self)
				self.name = self._leftexpr.name
				self._type_tokens[:] = []
			else:
				stateStruct.error("statement parsing: got ':' after " + repr(self._leftexpr) + "; looks like a goto-label but is not")
			self.finalize(stateStruct)
			return

		self._handlePushedErrorForUnknown(stateStruct)
		obj = None
		if self._state == 0:
			if isinstance(token, (CIdentifier,CNumber,CStr,CChar)):
				if isinstance(token, CIdentifier):
					if token.content == "struct":
						self._state = 1
						return
					elif token.content == "union":
						self._state = 2
						return
					elif token.content == "enum":
						self._state = 3
						return
					elif token.content == "sizeof":
						obj = CSizeofSymbol()
					else:
						obj = findObjInNamespace(stateStruct, self.parent, token.content)
						if obj is None:
							obj = CUnknownType(name=token.content)
							self._pushedErrorForUnknown = False
							# we print an error later. it still could be a goto-label.
				else:
					obj = token
				self._leftexpr = obj
				self._state = 5
			elif isinstance(token, COp):
				# prefix op
				self._op = token
				self._rightexpr = CStatement(parent=self)
				self._state = 8
			else:
				stateStruct.error("statement parsing: didn't expected token " + str(token))
		elif self._state in (1,2,3): # struct,union,enum
			TName = {1:"struct", 2:"union", 3:"enum"}[self._state]
			DictName = TName + "s"
			if isinstance(token, CIdentifier):
				obj = findCObjTypeInNamespace(stateStruct, self.parent, DictName, token.content)
				if obj is None:
					stateStruct.error("statement parsing: " + TName + " '" + token.content + "' unknown")
					obj = CUnknownType(name=token.content)
				self._leftexpr = obj
				self._state = 5
			else:
				stateStruct.error("statement parsing: didn't expected token " + str(token) + " after " + TName)
		elif self._state == 5: # after expr
			if token == COp("."):
				self._state = 20
				self._leftexpr = CAttribAccessRef(parent=self, base=self._leftexpr)
			elif token == COp("->"):
				self._state = 20
				self._leftexpr = CPtrAccessRef(parent=self, base=self._leftexpr)
			elif isinstance(token, COp):
				self._op = token
				self._state = 6
			elif isinstance(self._leftexpr, CStr) and isinstance(token, CStr):
				self._leftexpr = CStr(self._leftexpr.content + token.content)
			else:
				self._leftexpr = _create_cast_call(stateStruct, self, self._leftexpr, token)
				self._state = 40
		elif self._state == 6: # after expr + op
			if isinstance(token, CIdentifier):
				if token.content == "sizeof":
					obj = CSizeofSymbol()
				else:
					obj = findObjInNamespace(stateStruct, self.parent, token.content)
					if obj is None:
						stateStruct.error("statement parsing: identifier '" + token.content + "' unknown")
						obj = CUnknownType(name=token.content)
				self._state = 7
			elif isinstance(token, (CNumber,CStr,CChar)):
				obj = token
				self._state = 7
			else:
				obj = CStatement(parent=self)
				obj._cpre3_handle_token(stateStruct, token) # maybe a postfix op or whatever
				self._state = 8
			self._rightexpr = obj
		elif self._state == 7: # after expr + op + expr
			if token == COp("."):
				self._state = 22
				self._rightexpr = CAttribAccessRef(parent=self, base=self._rightexpr)
			elif token == COp("->"):
				self._state = 22
				self._rightexpr = CPtrAccessRef(parent=self, base=self._rightexpr)
			elif isinstance(token, COp):
				if token == COp(":"):
					if self._op != COp("?"):
						stateStruct.error("internal error: got ':' after " + repr(self) + " with " + repr(self._op))
						# TODO: any better way to fix/recover? right now, we just assume '?' anyway
					self._middleexpr = self._rightexpr
					self._rightexpr = None
					self._op = COp("?:")
					self._state = 6
				elif opsDoLeftToRight(stateStruct, self._op.content, token.content):
					import copy
					subStatement = copy.copy(self)
					self._leftexpr = subStatement
					self._rightexpr = None
					self._op = token
					self._state = 6
				else:
					self._rightexpr = CStatement(parent=self, _leftexpr=self._rightexpr, _state=6)
					self._rightexpr._op = token
					self._state = 8
			elif isinstance(self._rightexpr, CStr) and isinstance(token, CStr):
				self._rightexpr = CStr(self._rightexpr.content + token.content)
			else:
				self._rightexpr = _create_cast_call(stateStruct, self, self._rightexpr, token)
				self._state = 45
		elif self._state == 8: # right-to-left chain, pull down
			assert isinstance(self._rightexpr, CStatement)
			self._rightexpr._cpre3_handle_token(stateStruct, token)
			if self._rightexpr._state in (5,7,9):
				self._state = 9
		elif self._state == 9: # right-to-left chain after op + expr
			assert isinstance(self._rightexpr, CStatement)
			if token in (COp("."),COp("->")):
				self._rightexpr._cpre3_handle_token(stateStruct, token)
				self._state = 8
			elif not isinstance(token, COp):
				self._rightexpr._cpre3_handle_token(stateStruct, token)
			else: # is COp
				if token.content == ":":
					if self._op == COp("?"):
						self._middleexpr = self._rightexpr
						self._rightexpr = None
						self._op = COp("?:")
						self._state = 6
					else:
						self._rightexpr._cpre3_handle_token(stateStruct, token)
						self._state = 8
				elif opsDoLeftToRight(stateStruct, self._op.content, token.content):
					import copy
					subStatement = copy.copy(self)
					self._leftexpr = subStatement
					self._rightexpr = None
					self._op = token
					self._state = 6
				else:
					self._rightexpr._cpre3_handle_token(stateStruct, token)
					self._state = 8
		elif self._state == 20: # after attrib/ptr access
			if isinstance(token, CIdentifier):
				assert isinstance(self._leftexpr, (CAttribAccessRef,CPtrAccessRef))
				self._leftexpr.name = token.content
				self._state = 5
			else:
				stateStruct.error("statement parsing: didn't expected token " + str(token) + " after " + str(self._leftexpr) + " in state " + str(self._state))
		elif self._state == 40: # after cast_call((expr) x)
			if token in (COp("."),COp("->")):
				self._leftexpr.args[0]._cpre3_handle_token(stateStruct, token)
			else:
				self._leftexpr.args[0].finalize(stateStruct)
				self._state = 5
				self._cpre3_handle_token(stateStruct, token) # redo handling
		elif self._state == 45: # after expr + op + cast_call((expr) x)
			if token in (COp("."),COp("->")):
				self._rightexpr.args[0]._cpre3_handle_token(stateStruct, token)
			else:
				self._rightexpr.args[0].finalize(stateStruct)
				self._state = 7
				self._cpre3_handle_token(stateStruct, token) # redo handling
		elif self._state == 22: # after expr + op + expr with attrib/ptr access
			if isinstance(token, CIdentifier):
				assert isinstance(self._rightexpr, (CAttribAccessRef,CPtrAccessRef))
				self._rightexpr.name = token.content
				self._state = 7
			else:
				stateStruct.error("statement parsing: didn't expected token " + str(token) + " after " + str(self._leftexpr) + " in state " + str(self._state))
		else:
			stateStruct.error("internal error: statement parsing: token " + str(token) + " in invalid state " + str(self._state))

	def _cpre3_parse_brackets(self, stateStruct, openingBracketToken, input_iter):
		self._handlePushedErrorForUnknown(stateStruct)

		if self._state == 0 and openingBracketToken.content == "{": # array args
			arrayArgs = CArrayArgs(parent=self)
			arrayArgs._bracketlevel = list(openingBracketToken.brackets)
			cpre3_parse_statements_in_brackets(stateStruct, arrayArgs, COp(","), arrayArgs.args, input_iter)
			arrayArgs.finalize(stateStruct)
			self._state = 5
			return
		
		if self._state in (5,7): # after expr or expr + op + expr
			if self._state == 5:
				ref = self._leftexpr
			else:
				ref = self._rightexpr
			if openingBracketToken.content == "(":
				funcCall = CFuncCall(parent=self)
			elif openingBracketToken.content == "[":
				funcCall = CArrayIndexRef(parent=self)
			else:
				stateStruct.error("cpre3 statement parse brackets after expr: didn't expected opening bracket '" + openingBracketToken.content + "'")
				# fallback. handle just like '('
				funcCall = CStatement(parent=self.parent)
			funcCall.base = ref
			funcCall._bracketlevel = list(openingBracketToken.brackets)
			if self._state == 5:
				self._leftexpr = funcCall
			else:
				self._rightexpr = funcCall
			cpre3_parse_statements_in_brackets(stateStruct, funcCall, COp(","), funcCall.args, input_iter)
			funcCall.finalize(stateStruct)
			return

		if self._state in (8,9): # right-to-left chain
			self._rightexpr._cpre3_parse_brackets(stateStruct, openingBracketToken, input_iter)
			if self._rightexpr._state == 5:
				self._state = 9
			return

		if self._state in (40,45): # after .. cast_call + expr
			if self._state == 40:
				ref = self._leftexpr
			else:
				ref = self._rightexpr
			assert isinstance(ref, CFuncCall)
			ref.args[0]._cpre3_parse_brackets(stateStruct, openingBracketToken, input_iter)
			return

		if openingBracketToken.content == "(":
			subStatement = CStatement(parent=self.parent)
		elif openingBracketToken.content == "[":
			subStatement = CArrayStatement(parent=self.parent)
		else:
			# fallback. handle just like '('. we error this below
			subStatement = CStatement(parent=self.parent)

		if self._state == 0:
			self._leftexpr = subStatement
			if openingBracketToken.content != "(":
				stateStruct.error("cpre3 statement parse brackets: didn't expected opening bracket '" + openingBracketToken.content + "' in state 0")
			self._state = 5
		elif self._state == 6: # expr + op
			self._rightexpr = subStatement
			if openingBracketToken.content != "(":
				stateStruct.error("cpre3 statement parse brackets: didn't expected opening bracket '" + openingBracketToken.content + "' in state 6")
			self._state = 7
		else:
			stateStruct.error("cpre3 statement parse brackets: didn't expected opening bracket '" + openingBracketToken.content + "' in state " + str(self._state))
			
		for token in input_iter:
			if isinstance(token, COpeningBracket):
				subStatement._cpre3_parse_brackets(stateStruct, token, input_iter)
			elif isinstance(token, CClosingBracket):
				if token.brackets == openingBracketToken.brackets:
					subStatement.finalize(stateStruct, addToContent=False)
					self._tokens += [subStatement]
					return
				else:
					stateStruct.error("cpre3 statement parse brackets: internal error, closing brackets " + str(token.brackets) + " not expected")
			else:
				subStatement._cpre3_handle_token(stateStruct, token)
		stateStruct.error("cpre3 statement parse brackets: incomplete, missing closing bracket '" + openingBracketToken.content + "' at level " + str(openingBracketToken.brackets))
		
	def getConstValue(self, stateStruct):
		if self._leftexpr is None: # prefixed only
			func = OpPrefixFuncs[self._op.content]
			v = getConstValue(stateStruct, self._rightexpr)
			if v is None: return None
			return func(v)
		if self._op is None or self._rightexpr is None:
			return getConstValue(stateStruct, self._leftexpr)
		v1 = getConstValue(stateStruct, self._leftexpr)
		if v1 is None: return None
		v2 = getConstValue(stateStruct, self._rightexpr)
		if v2 is None: return None
		func = OpBinFuncs[self._op.content]
		if self._op == COp("?:"):
			v15 = getConstValue(stateStruct, self._middleexpr)
			if v15 is None: return None
			return func(v1, v15, v2)
		return func(v1, v2)
	
	def isCType(self):
		if self._leftexpr is None: return False # all prefixed stuff is not a type
		if self._rightexpr is not None: return False # same thing, prefixed stuff is not a type
		t = self._leftexpr
		try:
			if issubclass(t, _ctypes._SimpleCData): return True
		except: pass # e.g. typeerror or so
		if isinstance(t, (CType,CStruct,CUnion,CEnum)): return True
		return False
	
	def asType(self):
		assert self._leftexpr is not None
		assert self._rightexpr is None
		if isinstance(self._leftexpr, CStatement):
			t = self._leftexpr.asType()
		else:
			t = self._leftexpr
		if self._op is not None:
			if self._op.content in ("*","&"):
				t = CPointerType(t)
			else:
				raise Exception("postfix op " + str(self._op) + " unknown for pointer type " + str(self._leftexpr))
		return t
		
	def getCType(self, stateStruct):
		return getCType(self.asType(), stateStruct)

	def asCCode(self, indent=""):
		if self._leftexpr is None: # prefixed only
			return indent + "(" + self._op.content + asCCode(self._rightexpr) + ")"
		if self._op is None or self._rightexpr is None:
			return indent + asCCode(self._leftexpr) # no brackets. we do them outside
		if self._op == COp("?:"):
			return indent + "(" + asCCode(self._leftexpr) + " ? " + asCCode(self._middleexpr) + " : " + asCCode(self._rightexpr) + ")"
		return indent + "(" + asCCode(self._leftexpr) + " " + self._op.content + " " + asCCode(self._rightexpr) + ")"

# only real difference is that this is inside of '[]'
class CArrayStatement(CStatement):
	def asCCode(self, indent=""):
		return indent + "[" + CStatement.asCCode(self) + "]"
	
def cpre3_parse_struct(stateStruct, curCObj, input_iter):
	curCObj.body = CBody(parent=curCObj.parent.body)
	cpre3_parse_body(stateStruct, curCObj, input_iter)
	curCObj.finalize(stateStruct)

def cpre3_parse_union(stateStruct, curCObj, input_iter):
	curCObj.body = CBody(parent=curCObj.parent.body)
	cpre3_parse_body(stateStruct, curCObj, input_iter)
	curCObj.finalize(stateStruct)

def cpre3_parse_funcbody(stateStruct, curCObj, input_iter):
	curCObj.body = CBody(parent=curCObj.parent.body)
	cpre3_parse_body(stateStruct, curCObj, input_iter)
	curCObj.finalize(stateStruct)

def cpre3_parse_funcpointername(stateStruct, curCObj, input_iter):
	bracketLevel = list(curCObj._bracketlevel)
	state = 0
	for token in input_iter:
		if isinstance(token, CClosingBracket):
			if token.brackets == bracketLevel:
				return
			if not _isBracketLevelOk(bracketLevel, token.brackets):
				stateStruct.error("cpre3 parse func pointer name: internal error: bracket level messed up with closing bracket: " + str(token.brackets))

		if state == 0:
			if token == COp("*"):
				state = 1
				CFuncPointerDecl.overtake(curCObj)
				curCObj.ptrLevel = 1
			elif isinstance(token, CIdentifier):
				CFunc.overtake(curCObj)
				curCObj.name = token.content
				state = 4
			else:
				stateStruct.error("cpre3 parse func pointer name: token " + str(token) + " not expected; expected '*'")
		elif state == 1:
			if token == COp("*"):
				curCObj.ptrLevel += 1
			elif isinstance(token, CIdentifier):
				curCObj.name = token.content
				state = 2
			else:
				stateStruct.error("cpre3 parse func pointer name: token " + str(token) + " not expected; expected identifier")
		elif state == 2: # after identifier in func ptr
			if token == COpeningBracket("["):
				curCObj._bracketlevel = list(token.brackets)
				cpre3_parse_arrayargs(stateStruct, curCObj, input_iter)
				curCObj._bracketlevel = bracketLevel
			else:
				state = 3
		elif state == 4: # after identifier in func
			# we don't expect anything anymore
			state = 3
			
		if state == 3:
			stateStruct.error("cpre3 parse func pointer name: token " + str(token) + " not expected; expected ')'")

	stateStruct.error("cpre3 parse func pointer name: incomplete, missing ')' on level " + str(curCObj._bracketlevel))	

def cpre3_parse_enum(stateStruct, parentCObj, input_iter):
	parentCObj.body = CEnumBody(parent=parentCObj.parent.body)
	curCObj = CEnumConst(parent=parentCObj)
	valueStmnt = None
	state = 0
	
	for token in input_iter:
		if isinstance(token, CIdentifier):
			if state == 0:
				curCObj.name = token.content
				state = 1
			else:
				stateStruct.error("cpre3 parse enum: unexpected identifier " + token.content + " after " + str(curCObj) + " in state " + str(state))
		elif token == COp("="):
			if state == 1:
				valueStmnt = CStatement(parent=parentCObj)
				state = 2
			else:
				stateStruct.error("cpre3 parse enum: unexpected op '=' after " + str(curCObj) + " in state " + str(state))
		elif token == COp(","):
			if state in (1,2):
				if state == 2:
					valueStmnt.finalize(stateStruct, addToContent=False)
					curCObj.value = valueStmnt.getConstValue(stateStruct)
				curCObj.finalize(stateStruct)
				curCObj = CEnumConst(parent=parentCObj)
				valueStmnt = None
				state = 0
			else:
				stateStruct.error("cpre3 parse enum: unexpected op ',' after " + str(curCObj) + " in state " + str(state))
		elif isinstance(token, CClosingBracket):
			if token.brackets == parentCObj._bracketlevel:
				if curCObj:
					if state == 2:
						valueStmnt.finalize(stateStruct, addToContent=False)
						curCObj.value = valueStmnt.getConstValue(stateStruct)
					curCObj.finalize(stateStruct)
				parentCObj.finalize(stateStruct)
				return
			if not _isBracketLevelOk(parentCObj._bracketlevel, token.brackets):
				stateStruct.error("cpre3 parse enum: internal error: bracket level messed up with closing bracket: " + str(token.brackets))
		elif state == 2:
			if isinstance(token, COpeningBracket):
				valueStmnt._cpre3_parse_brackets(stateStruct, token, input_iter)
			else:
				valueStmnt._cpre3_handle_token(stateStruct, token)
		else:
			stateStruct.error("cpre3 parse enum: unexpected token " + str(token) + " in state " + str(state))
	stateStruct.error("cpre3 parse enum: incomplete, missing '}' on level " + str(parentCObj._bracketlevel))

def _cpre3_parse_skipbracketcontent(stateStruct, bracketlevel, input_iter):
	for token in input_iter:
		if isinstance(token, CClosingBracket):
			if token.brackets == bracketlevel:
				return
			if not _isBracketLevelOk(bracketlevel, token.brackets):
				stateStruct.error("cpre3 parse skip brackets: internal error: bracket level messed up with closing bracket: " + str(token.brackets))
	stateStruct.error("cpre3 parse: incomplete, missing closing bracket on level " + str(curCObj._bracketlevel))
	
def cpre3_parse_funcargs(stateStruct, parentCObj, input_iter):
	curCObj = CFuncArgDecl(parent=parentCObj)
	typeObj = None
	for token in input_iter:
		if isinstance(token, CIdentifier):
			if token.content == "typedef":
				stateStruct.error("cpre3 parse func args: typedef not expected")
			elif token.content in stateStruct.Attribs:
				curCObj.attribs += [token.content]
			elif token.content == "struct":
				typeObj = CStruct()
				curCObj._type_tokens += [typeObj]
			elif token.content == "union":
				typeObj = CUnion()
				curCObj._type_tokens += [typeObj]
			elif token.content == "enum":
				typeObj = CEnum()
				curCObj._type_tokens += [typeObj]
			elif typeObj is not None:
				if typeObj.name is None:
					typeObj.name = token.content
					typeObj = None
			elif (token.content,) in stateStruct.CBuiltinTypes:
				curCObj._type_tokens += [token.content]
			elif token.content in stateStruct.StdIntTypes:
				curCObj._type_tokens += [token.content]
			elif len(curCObj._type_tokens) == 0:
				curCObj._type_tokens += [token.content]
			else:
				if curCObj.name is None:
					curCObj.name = token.content
				else:
					stateStruct.error("cpre3 parse func args: second identifier name " + token.content + " for " + str(curCObj))
		elif isinstance(token, COp):
			if token.content == ",":
				curCObj.finalize(stateStruct)
				curCObj = CFuncArgDecl(parent=parentCObj)
				typeObj = None
			else:
				curCObj._type_tokens += [token.content]
		elif isinstance(token, COpeningBracket):
			curCObj._bracketlevel = list(token.brackets)
			if token.content == "(":
				if len(curCObj._type_tokens) == 1 and isinstance(curCObj._type_tokens[0], CFuncPointerDecl):
					typeObj = curCObj._type_tokens[0]
					cpre3_parse_funcargs(stateStruct, typeObj, input_iter)
					typeObj.finalize(stateStruct)
				elif curCObj.name is None:
					typeObj = CFuncPointerDecl(parent=curCObj.parent)
					typeObj._bracketlevel = curCObj._bracketlevel
					typeObj._type_tokens[:] = curCObj._type_tokens
					curCObj._type_tokens[:] = [typeObj]
					cpre3_parse_funcpointername(stateStruct, typeObj, input_iter)
					curCObj.name = typeObj.name
				else:
					stateStruct.error("cpre3 parse func args: got unexpected '(' in " + str(curCObj))
					_cpre3_parse_skipbracketcontent(stateStruct, curCObj._bracketlevel, input_iter)
			elif token.content == "[":
				cpre3_parse_arrayargs(stateStruct, curCObj, input_iter)
			else:
				stateStruct.error("cpre3 parse func args: unexpected opening bracket '" + token.content + "'")
				_cpre3_parse_skipbracketcontent(stateStruct, curCObj._bracketlevel, input_iter)
		elif isinstance(token, CClosingBracket):
			if token.brackets == parentCObj._bracketlevel:
				if curCObj:
					curCObj.finalize(stateStruct)
				return
			if not _isBracketLevelOk(parentCObj._bracketlevel, token.brackets):
				stateStruct.error("cpre3 parse func args: internal error: bracket level messed up with closing bracket: " + str(token.brackets))
			# no error. we already errored on the opening bracket. and the cpre2 parsing ensures the rest
		else:
			stateStruct.error("cpre3 parse func args: unexpected token " + str(token))

	stateStruct.error("cpre3 parse func args: incomplete, missing ')' on level " + str(parentCObj._bracketlevel))

def cpre3_parse_arrayargs(stateStruct, curCObj, input_iter):
	# TODO
	for token in input_iter:
		if isinstance(token, CClosingBracket):
			if token.brackets == curCObj._bracketlevel:
				return
			if not _isBracketLevelOk(curCObj._bracketlevel, token.brackets):
				stateStruct.error("cpre3 parse array args: internal error: bracket level messed up with closing bracket: " + str(token.brackets))
	stateStruct.error("cpre3 parse array args: incomplete, missing ']' on level " + str(curCObj._bracketlevel))

def cpre3_parse_typedef(stateStruct, curCObj, input_iter):
	state = 0
	typeObj = None
	
	for token in input_iter:
		if state == 0:
			if isinstance(token, CIdentifier):
				if token.content == "typedef":
					stateStruct.error("cpre3 parse typedef: typedef not expected twice")
				elif token.content in stateStruct.Attribs:
					curCObj.attribs += [token.content]
				elif token.content == "struct":
					typeObj = CStruct(parent=curCObj.parent)
					curCObj._type_tokens += [typeObj]
				elif token.content == "union":
					typeObj = CUnion(parent=curCObj.parent)
					curCObj._type_tokens += [typeObj]
				elif token.content == "enum":
					typeObj = CEnum(parent=curCObj.parent)
					curCObj._type_tokens += [typeObj]
				elif (token.content,) in stateStruct.CBuiltinTypes:
					curCObj._type_tokens += [token.content]
				elif token.content in stateStruct.StdIntTypes:
					curCObj._type_tokens += [token.content]
				elif token.content in stateStruct.typedefs:
					curCObj._type_tokens += [token.content]
				else:
					if typeObj is not None and not typeObj._finalized and typeObj.name is None:
						typeObj.name = token.content
					elif curCObj._type_tokens:
						if curCObj.name is None:
							curCObj.name = token.content
						else:
							stateStruct.error("cpre3 parse in typedef: got second identifier " + token.content + " after name " + curCObj.name)
					else:
						stateStruct.error("cpre3 parse in typedef: got unexpected identifier " + token.content)
			elif token == COp("*"):
				curCObj._type_tokens += ["*"]
			elif isinstance(token, COpeningBracket):
				curCObj._bracketlevel = list(token.brackets)
				if token.content == "(":
					if len(curCObj._type_tokens) == 0 or not isinstance(curCObj._type_tokens[0], CFuncPointerDecl):
						typeObj = CFuncPointerDecl(parent=curCObj.parent)
						typeObj._bracketlevel = curCObj._bracketlevel
						typeObj._type_tokens[:] = curCObj._type_tokens
						curCObj._type_tokens[:] = [typeObj]
						if curCObj.name is None: # eg.: typedef int (*Function)();
							cpre3_parse_funcpointername(stateStruct, typeObj, input_iter)
							curCObj.name = typeObj.name
						else: # eg.: typedef int Function();
							typeObj.name = curCObj.name
							cpre3_parse_funcargs(stateStruct, typeObj, input_iter)							
					else:
						cpre3_parse_funcargs(stateStruct, typeObj, input_iter)
				elif token.content == "[":
					cpre3_parse_arrayargs(stateStruct, curCObj, input_iter)
				elif token.content == "{":
					if typeObj is not None: # it must not be None. but error handling already below
						typeObj._bracketlevel = curCObj._bracketlevel
					if isinstance(typeObj, CStruct):
						cpre3_parse_struct(stateStruct, typeObj, input_iter)
					elif isinstance(typeObj, CUnion):
						cpre3_parse_union(stateStruct, typeObj, input_iter)
					elif isinstance(typeObj, CEnum):
						cpre3_parse_enum(stateStruct, typeObj, input_iter)
					else:
						stateStruct.error("cpre3 parse in typedef: got unexpected '{' after type " + str(typeObj))
						state = 11
				else:
					stateStruct.error("cpre3 parse in typedef: got unexpected opening bracket '" + token.content + "' after type " + str(typeObj))
					state = 11
			elif isinstance(token, CSemicolon):
				if typeObj is not None and not typeObj._finalized:
					typeObj.finalize(stateStruct, addToContent = typeObj.body is not None)
				curCObj.finalize(stateStruct)
				return
			else:
				stateStruct.error("cpre3 parse typedef: got unexpected token " + str(token))
		elif state == 11: # unexpected bracket
			# just ignore everything until we get the closing bracket
			if isinstance(token, CClosingBracket):
				if token.brackets == curCObj._bracketlevel:
					state = 0
				if not _isBracketLevelOk(curCObj._bracketlevel, token.brackets):
					stateStruct.error("cpre3 parse typedef: internal error: bracket level messed up with closing bracket: " + str(token.brackets))
		else:
			stateStruct.error("cpre3 parse typedef: internal error. unexpected state " + str(state))
	stateStruct.error("cpre3 parse typedef: incomplete, missing ';'")


class CCodeBlock(_CBaseWithOptBody):
	NameIsRelevant = False
	def asCCode(self, indent=""):
		return asCCode(self.body, indent)
class CGotoLabel(_CBaseWithOptBody):
	def asCCode(self, indent=""):
		return indent + self.name + ":"

def _getLastCBody(base):
	last = None
	while True:
		if isinstance(base.body, CBody):
			if not base.body.contentlist: break
			last = base.body.contentlist[-1]
		elif isinstance(base.body, _CControlStructure):
			last = base.body
		else:
			break
		if not isinstance(last, _CControlStructure): break
		if isinstance(last, CIfStatement):
			if last.elsePart is not None:
				base = last.elsePart
			else:
				base = last
		elif isinstance(last, (CForStatement,CWhileStatement)):
			base = last
		else:
			break
	return last

class _CControlStructure(_CBaseWithOptBody):
	NameIsRelevant = False
	StrOutAttribList = [
		("args", bool, None, str),
		("body", None, None, lambda x: "<...>"),
		("defPos", None, "@", str),
	]
	def asCCode(self, indent=""):
		s = indent + self.Keyword
		if self.args: s += "(" + "; ".join(map(asCCode, self.args)) + ")"
		if self.body: s += "\n" + asCCode(self.body, indent)
		if hasattr(self, "whilePart"): s += "\n" + asCCode(self.whilePart, indent)
		if hasattr(self, "elsePart"): s += "\n" + asCCode(self.elsePart, indent)
		return s
class CForStatement(_CControlStructure):
	Keyword = "for"
class CDoStatement(_CControlStructure):
	Keyword = "do"
	StrOutAttribList = [
		("body", None, None, lambda x: "<...>"),
		("whilePart", None, None, repr),
		("defPos", None, "@", str),
	]
	whilePart = None
class CWhileStatement(_CControlStructure):
	Keyword = "while"
	def finalize(self, stateStruct, addToContent = None):
		if self._finalized:
			stateStruct.error("internal error: " + str(self) + " finalized twice")
			return
		assert self.parent is not None

		if isinstance(self.parent.body, CBody) and self.parent.body.contentlist:
			last = _getLastCBody(self.parent)
			if isinstance(last, CDoStatement):
				if self.body is not None:
					stateStruct.error("'while' " + str(self) + " as part of 'do' " + str(last) + " has another body")
				last.whilePart = self
				addToContent = False

		_CControlStructure.finalize(self, stateStruct, addToContent)			
class CContinueStatement(_CControlStructure):
	Keyword = "continue"
	AlwaysNonZero = True
class CBreakStatement(_CControlStructure):
	Keyword = "break"
	AlwaysNonZero = True
class CIfStatement(_CControlStructure):
	Keyword = "if"
	StrOutAttribList = [
		("args", bool, None, str),
		("body", None, None, lambda x: "<...>"),
		("elsePart", None, None, repr),
		("defPos", None, "@", str),
	]
	elsePart = None
class CElseStatement(_CControlStructure):
	Keyword = "else"
	def finalize(self, stateStruct, addToContent = False):
		if self._finalized:
			stateStruct.error("internal error: " + str(self) + " finalized twice")
			return
		assert self.parent is not None

		base = self.parent
		lastIf = None
		last = None
		while True:
			if isinstance(base.body, CBody):
				if not base.body.contentlist: break
				last = base.body.contentlist[-1]
			elif isinstance(base.body, CIfStatement):
				last = base.body
			else:
				break
			if not isinstance(last, CIfStatement): break
			if last.elsePart is not None:
				base = last.elsePart
			else:
				lastIf = last
				base = lastIf
	
		if lastIf is not None:
			lastIf.elsePart = self
		else:
			stateStruct.error("'else' " + str(self) + " without 'if', last was " + str(last))
		_CControlStructure.finalize(self, stateStruct, addToContent)
class CSwitchStatement(_CControlStructure):
	Keyword = "switch"
class CCaseStatement(_CControlStructure):
	Keyword = "case"
class CCaseDefaultStatement(_CControlStructure):
	Keyword = "default"
	AlwaysNonZero = True
class CGotoStatement(_CControlStructure):
	Keyword = "goto"
class CReturnStatement(_CControlStructure):
	Keyword = "return"
	AlwaysNonZero = True

CControlStructures = dict(map(lambda c: (c.Keyword, c), [
	CForStatement,
	CDoStatement,
	CWhileStatement,
	CContinueStatement,
	CBreakStatement,
	CIfStatement,
	CElseStatement,
	CSwitchStatement,
	CCaseStatement,
	CCaseDefaultStatement,
	CGotoStatement,
	CReturnStatement,
	]))

def cpre3_parse_statements_in_brackets(stateStruct, parentCObj, sepToken, addToList, input_iter):
	brackets = list(parentCObj._bracketlevel)
	curCObj = _CBaseWithOptBody(parent=parentCObj)
	def _finalizeCObj(o):
		if not o.isDerived():
			CStatement.overtake(o)
			for t in o._type_tokens:
				o._cpre3_handle_token(stateStruct, CIdentifier(t))
			o._type_tokens = []
		o.finalize(stateStruct, addToContent=False)
	for token in input_iter:
		if isinstance(token, CIdentifier):
			if isinstance(curCObj, CStatement):
				curCObj._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_handle_token(stateStruct, token)
			elif token.content in stateStruct.Attribs:
				curCObj.attribs += [token.content]
			elif token.content == "struct":
				CStruct.overtake(curCObj)
			elif token.content == "union":
				CUnion.overtake(curCObj)
			elif token.content == "enum":
				CEnum.overtake(curCObj)
			elif (token.content,) in stateStruct.CBuiltinTypes:
				curCObj._type_tokens += [token.content]
			elif token.content in stateStruct.StdIntTypes:
				curCObj._type_tokens += [token.content]
			elif token.content in stateStruct.typedefs:
				curCObj._type_tokens += [token.content]
			else:
				if curCObj._finalized:
					# e.g. like "struct {...} X" and we parse "X"
					oldObj = curCObj
					curCObj = CVarDecl(parent=parentCObj)
					curCObj._type_tokens[:] = [oldObj]

				if curCObj.name is None:
					curCObj.name = token.content
				else:
					stateStruct.error("cpre3 parse statements in brackets: second identifier name " + token.content + ", first was " + curCObj.name + ", first might be an unknwon type")
					# fallback recovery, guess vardecl with the first identifier being an unknown type
					curCObj._type_tokens += [CUnknownType(name=curCObj.name)]
					curCObj.name = token.content

				if not curCObj.isDerived():
					if len(curCObj._type_tokens) == 0:
						curCObj.name = None
						CStatement.overtake(curCObj)
						curCObj._cpre3_handle_token(stateStruct, token)
					else:
						CVarDecl.overtake(curCObj)
		elif isinstance(token, COpeningBracket):
			if isinstance(curCObj, CStatement):
				curCObj._cpre3_parse_brackets(stateStruct, token, input_iter)
			elif isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_parse_brackets(stateStruct, token, input_iter)
			elif not curCObj.isDerived():
				CStatement.overtake(curCObj)
				curCObj._cpre3_parse_brackets(stateStruct, token, input_iter)
			else:
				stateStruct.error("cpre3 parse statements in brackets: " + str(token) + " not expected after " + str(curCObj))
				# fallback
				CStatement.overtake(curCObj)
				curCObj._cpre3_parse_brackets(stateStruct, token, input_iter)				
		elif isinstance(token, CClosingBracket):
			if token.brackets == brackets:
				break
			stateStruct.error("cpre3 parse statements in brackets: unexpected closing bracket '" + token.content + "' after " + str(curCObj) + " at bracket level " + str(brackets))
		elif token == sepToken:
			_finalizeCObj(curCObj)
			addToList.append(curCObj)
			curCObj = _CBaseWithOptBody(parent=parentCObj)
		elif isinstance(token, CSemicolon): # if the sepToken is not the semicolon, we don't expect it at all
			stateStruct.error("cpre3 parse statements in brackets: ';' not expected, separator should be " + str(sepToken))
		elif isinstance(curCObj, CVarDecl) and token == COp("="):
			curCObj.body = CStatement(parent=curCObj)
		else:
			if not curCObj.isDerived():
				CStatement.overtake(curCObj)
			if isinstance(curCObj, CStatement):
				curCObj._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_handle_token(stateStruct, token)
			else:
				stateStruct.error("cpre3 parse statements in brackets: " + str(token) + " not expected after " + str(curCObj))
			
	# add also the last object
	if curCObj:
		_finalizeCObj(curCObj)
		addToList.append(curCObj)

def cpre3_parse_single_next_statement(stateStruct, parentCObj, input_iter):
	curCObj = None
	for token in input_iter:
		if isinstance(token, COpeningBracket):
			if token.content == "{":
				parentCObj._bracketlevel = list(token.brackets)
				cpre3_parse_body(stateStruct, parentCObj, input_iter)
				return
			if curCObj is None:
				curCObj = CStatement(parent=parentCObj)
			if isinstance(curCObj, CStatement):
				curCObj._cpre3_parse_brackets(stateStruct, token, input_iter)
			elif curCObj is not None and isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_parse_brackets(stateStruct, token, input_iter)
			elif isinstance(curCObj, _CControlStructure):
				curCObj._bracketlevel = list(token.brackets)
				if token.content == "(":
					cpre3_parse_statements_in_brackets(stateStruct, curCObj, sepToken=CSemicolon(), addToList=curCObj.args, input_iter=input_iter)
					curCObj._bracketlevel = list(parentCObj._bracketlevel)
					lasttoken = cpre3_parse_single_next_statement(stateStruct, curCObj, input_iter)
					curCObj.finalize(stateStruct)
					parentCObj.body = curCObj
					return lasttoken
				elif token.content == "[":
					stateStruct.error("cpre3 parse single after " + str(curCObj) + ": got unexpected '['")
					cpre3_parse_skipbracketcontent(stateStruct, list(token.brackets), input_iter)
					return
				elif token.content == "{":
					if curCObj.body is not None:
						stateStruct.error("cpre3 parse single after " + str(curCObj) + ": got multiple bodies")
					cpre3_parse_body(stateStruct, curCObj, input_iter)
					curCObj.finalize(stateStruct)
					parentCObj.body = curCObj
					return
				else:
					stateStruct.error("cpre3 parse single after " + str(curCObj) + ": got unexpected/unknown opening bracket '" + token.content + "'")
					cpre3_parse_skipbracketcontent(stateStruct, list(token.brackets), input_iter)
					return
			else:
				stateStruct.error("cpre3 parse single: unexpected opening bracket '" + token.content + "' after " + str(curCObj))
		elif isinstance(token, CClosingBracket):
			if token.brackets == parentCObj._bracketlevel:
				stateStruct.error("cpre3 parse single: closed brackets without expected statement")
				return token
			stateStruct.error("cpre3 parse single: unexpected closing bracket '" + token.content + "' after " + str(curCObj) + " at bracket level " + str(parentCObj._bracketlevel))
		elif isinstance(token, CSemicolon):
			if curCObj and not curCObj.isDerived():
				CVarDecl.overtake(curCObj)
			if curCObj is not None:
				curCObj.finalize(stateStruct)
				parentCObj.body = curCObj
			return token
		elif curCObj is None and isinstance(token, CIdentifier) and token.content in CControlStructures:
			curCObj = CControlStructures[token.content](parent=parentCObj)
			curCObj.defPos = stateStruct.curPosAsStr()
			if isinstance(curCObj, (CElseStatement,CDoStatement)):
				curCObj._bracketlevel = list(parentCObj._bracketlevel)
				lasttoken = cpre3_parse_single_next_statement(stateStruct, curCObj, input_iter)
				# We finalize in any way, also for 'do'. We don't do any semantic checks here
				# if there is a correct 'while' following or neither if the 'else' has a previous 'if'.
				curCObj.finalize(stateStruct)
				parentCObj.body = curCObj
				return lasttoken
			elif isinstance(curCObj, CReturnStatement):
				curCObj.body = CStatement(parent=curCObj)
		elif isinstance(curCObj, CGotoStatement):
			if curCObj.name is None:
				curCObj.name = token.content
			else:
				stateStruct.error("cpre3 parse single after " + str(curCObj) + ": got second identifier '" + token.content + "'")
		elif isinstance(curCObj, CStatement):
			curCObj._cpre3_handle_token(stateStruct, token)
		elif curCObj is not None and isinstance(curCObj.body, CStatement):
			curCObj.body._cpre3_handle_token(stateStruct, token)
		elif isinstance(curCObj, _CControlStructure):
			stateStruct.error("cpre3 parse after " + str(curCObj) + ": didn't expected identifier '" + token.content + "'")
		else:
			if curCObj is None:
				curCObj = CStatement(parent=parentCObj)
				curCObj._cpre3_handle_token(stateStruct, token)
			else:
				stateStruct.error("cpre3 parse single: got unexpected token " + str(token))
	stateStruct.error("cpre3 parse single: runaway")
	return

def cpre3_parse_body(stateStruct, parentCObj, input_iter):
	if parentCObj.body is None: parentCObj.body = CBody(parent=parentCObj.parent.body)

	curCObj = _CBaseWithOptBody(parent=parentCObj)

	while True:
		stateStruct._cpre3_atBaseLevel = False
		if parentCObj._bracketlevel is None:
			if not curCObj:
				stateStruct._cpre3_atBaseLevel = True

		try: token = next(input_iter)
		except StopIteration: break
		
		if isinstance(token, CIdentifier):
			if isinstance(curCObj, CStatement):
				curCObj._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, CGotoStatement):
				if curCObj.name is None:
					curCObj.name = token.content
				else:
					stateStruct.error("cpre3 parse after " + str(curCObj) + ": got second identifier '" + token.content + "'")
			elif isinstance(curCObj, CCaseStatement):
				if not curCObj.args or not isinstance(curCObj.args[-1], CStatement):
					curCObj.args.append(CStatement(parent=parentCObj))
				curCObj.args[-1]._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, _CControlStructure):
				stateStruct.error("cpre3 parse after " + str(curCObj) + ": didn't expected identifier '" + token.content + "'")
			elif token.content == "typedef":
				CTypedef.overtake(curCObj)
				curCObj.defPos = stateStruct.curPosAsStr()
				cpre3_parse_typedef(stateStruct, curCObj, input_iter)
				curCObj = _CBaseWithOptBody(parent=parentCObj)							
			elif token.content in stateStruct.Attribs:
				curCObj.attribs += [token.content]
			elif token.content == "struct":
				CStruct.overtake(curCObj)
				curCObj.defPos = stateStruct.curPosAsStr()
			elif token.content == "union":
				CUnion.overtake(curCObj)
				curCObj.defPos = stateStruct.curPosAsStr()
			elif token.content == "enum":
				CEnum.overtake(curCObj)
				curCObj.defPos = stateStruct.curPosAsStr()
			elif token.content in CControlStructures:
				if curCObj.isDerived() or curCObj:
					stateStruct.error("cpre3 parse: got '" + token.content + "' after " + str(curCObj))
					# try to finalize and reset
					curCObj.finalize(stateStruct)
					curCObj = _CBaseWithOptBody(parent=parentCObj)
				CControlStructures[token.content].overtake(curCObj)
				curCObj.defPos = stateStruct.curPosAsStr()
				if isinstance(curCObj, (CElseStatement,CDoStatement)):
					curCObj._bracketlevel = list(parentCObj._bracketlevel)
					lasttoken = cpre3_parse_single_next_statement(stateStruct, curCObj, input_iter)
					# We finalize in any way, also for 'do'. We don't do any semantic checks here
					# if there is a correct 'while' following or neither if the 'else' has a previous 'if'.
					curCObj.finalize(stateStruct)
					if isinstance(lasttoken, CClosingBracket) and lasttoken.brackets == parentCObj._bracketlevel:
						return
					curCObj = _CBaseWithOptBody(parent=parentCObj)
				elif isinstance(curCObj, CReturnStatement):
					curCObj.body = CStatement(parent=curCObj)
			elif (token.content,) in stateStruct.CBuiltinTypes:
				curCObj._type_tokens += [token.content]
			elif token.content in stateStruct.StdIntTypes:
				curCObj._type_tokens += [token.content]
			elif token.content in stateStruct.typedefs:
				curCObj._type_tokens += [token.content]
			else:
				if curCObj._finalized:
					# e.g. like "struct {...} X" and we parse "X"
					oldObj = curCObj
					curCObj = CVarDecl(parent=parentCObj)
					curCObj._type_tokens[:] = [oldObj]

				if curCObj.name is None:
					curCObj.name = token.content
					DictName = None
					if isinstance(curCObj, CStruct): DictName = "structs"
					elif isinstance(curCObj, CUnion): DictName = "unions"
					elif isinstance(curCObj, CEnum): DictName = "enums"
					if DictName is not None:
						typeObj = findCObjTypeInNamespace(stateStruct, parentCObj, DictName, curCObj.name)
						if typeObj is not None and typeObj.body is not None: # if body is None, we still wait for another decl
							curCObj = CVarDecl(parent=parentCObj)
							curCObj._type_tokens += [typeObj]
				else:
					stateStruct.error("cpre3 parse: second identifier name " + token.content + ", first was " + curCObj.name + ", first might be an unknwon type")
					typeObj = CUnknownType(name=curCObj.name)
					# fallback recovery, guess vardecl with the first identifier being an unknown type
					curCObj = CVarDecl(parent=parentCObj)
					curCObj._type_tokens += [typeObj]
					curCObj.name = token.content
				
				if not curCObj.isDerived():
					if len(curCObj._type_tokens) == 0:
						curCObj.name = None
						CStatement.overtake(curCObj)
						curCObj._cpre3_handle_token(stateStruct, token)
					else:
						CVarDecl.overtake(curCObj)					
		elif isinstance(token, COp):
			if (not curCObj.isDerived() or isinstance(curCObj, CVarDecl)) and len(curCObj._type_tokens) == 0:
				CStatement.overtake(curCObj)
			if isinstance(curCObj, CStatement):
				curCObj._cpre3_handle_token(stateStruct, token)
				if curCObj._finalized: # might have been finalized internally. e.g. in case it was a goto-loop
					curCObj = _CBaseWithOptBody(parent=parentCObj)					
			elif isinstance(curCObj.body, CStatement) and token.content != ",": # op(,) gets some extra handling. eg for CVarDecl
				curCObj.body._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, CCaseStatement):
				if token.content == ":":
					curCObj.finalize(stateStruct)
					curCObj = _CBaseWithOptBody(parent=parentCObj)
				else:
					if not curCObj.args or not isinstance(curCObj.args[-1], CStatement):
						curCObj.args.append(CStatement(parent=parentCObj))
					curCObj.args[-1]._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, CCaseDefaultStatement) and token.content == ":":
				curCObj.finalize(stateStruct)
				curCObj = _CBaseWithOptBody(parent=parentCObj)
			elif isinstance(curCObj, _CControlStructure):
				if isinstance(curCObj.body, CStatement): # for example, because of op(,), we might have missed that above
					curCObj.body._cpre3_handle_token(stateStruct, token)
				else:	
					stateStruct.error("cpre3 parse after " + str(curCObj) + ": didn't expected op '" + token.content + "'")
			else:
				if token.content == "*":
					if isinstance(curCObj, (CStruct,CUnion,CEnum)):
						curCObj.finalize(stateStruct)
						oldObj = curCObj
						curCObj = CVarDecl(parent=parentCObj)
						curCObj._type_tokens[:] = [oldObj, "*"]
					else:
						CVarDecl.overtake(curCObj)
						curCObj._type_tokens += [token.content]
				elif token.content == ",":
					CVarDecl.overtake(curCObj)
					oldObj = curCObj
					curCObj = curCObj.copy()
					oldObj.finalize(stateStruct)
					curCObj.clearDeclForNextVar()
					curCObj.name = None
					curCObj.body = None
				elif token.content == ":" and curCObj and curCObj._type_tokens and curCObj.name:
					CVarDecl.overtake(curCObj)
					curCObj.bitsize = None
				elif token.content == "=" and curCObj and (isinstance(curCObj, CVarDecl) or not curCObj.isDerived()):
					if not curCObj.isDerived():
						CVarDecl.overtake(curCObj)
					curCObj.body = CStatement(parent=curCObj)
				else:
					stateStruct.error("cpre3 parse: op '" + token.content + "' not expected in " + str(parentCObj) + " after " + str(curCObj))
		elif isinstance(token, CNumber):
			if isinstance(curCObj, CVarDecl) and hasattr(curCObj, "bitsize"):
				curCObj.bitsize = token.content
			elif isinstance(curCObj, CStatement):
				curCObj._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, CCaseStatement):
				if not curCObj.args or not isinstance(curCObj.args[-1], CStatement):
					curCObj.args.append(CStatement(parent=parentCObj))
				curCObj.args[-1]._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, _CControlStructure):
				stateStruct.error("cpre3 parse after " + str(curCObj) + ": didn't expected number '" + str(token.content) + "'")
			else:
				CStatement.overtake(curCObj)
				curCObj._cpre3_handle_token(stateStruct, token)
		elif isinstance(token, COpeningBracket):
			curCObj._bracketlevel = list(token.brackets)
			if not _isBracketLevelOk(parentCObj._bracketlevel, token.brackets):
				stateStruct.error("cpre3 parse body: internal error: bracket level messed up with opening bracket: " + str(token.brackets) + " on level " + str(parentCObj._bracketlevel) + " in " + str(parentCObj))
			if isinstance(curCObj, CStatement):
				if token.content == "{":
					cpre3_parse_body(stateStruct, curCObj, input_iter)
					curCObj.finalize(stateStruct)
					curCObj = _CBaseWithOptBody(parent=parentCObj)
				else:
					curCObj._cpre3_parse_brackets(stateStruct, token, input_iter)
			elif isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_parse_brackets(stateStruct, token, input_iter)
			elif isinstance(curCObj, CCaseStatement):
				if not curCObj.args or not isinstance(curCObj.args[-1], CStatement):
					curCObj.args.append(CStatement(parent=parentCObj))
				curCObj.args[-1]._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, _CControlStructure):
				if token.content == "(":
					cpre3_parse_statements_in_brackets(stateStruct, curCObj, sepToken=CSemicolon(), addToList=curCObj.args, input_iter=input_iter)
					curCObj._bracketlevel = list(parentCObj._bracketlevel)
					lasttoken = cpre3_parse_single_next_statement(stateStruct, curCObj, input_iter)
					curCObj.finalize(stateStruct)
					if isinstance(lasttoken, CClosingBracket) and lasttoken.brackets == parentCObj._bracketlevel:
						return
					curCObj = _CBaseWithOptBody(parent=parentCObj)
				elif token.content == "[":
					stateStruct.error("cpre3 parse after " + str(curCObj) + ": got unexpected '['")
					cpre3_parse_skipbracketcontent(stateStruct, list(token.brackets), input_iter)
				elif token.content == "{":
					if curCObj.body is not None:
						stateStruct.error("cpre3 parse after " + str(curCObj) + ": got multiple bodies")
					cpre3_parse_body(stateStruct, curCObj, input_iter)
					curCObj.finalize(stateStruct)
					curCObj = _CBaseWithOptBody(parent=parentCObj)
				else:
					stateStruct.error("cpre3 parse after " + str(curCObj) + ": got unexpected/unknown opening bracket '" + token.content + "'")
					cpre3_parse_skipbracketcontent(stateStruct, list(token.brackets), input_iter)					
			elif token.content == "(":
				if len(curCObj._type_tokens) == 0:
					CStatement.overtake(curCObj)
					curCObj._cpre3_parse_brackets(stateStruct, token, input_iter)
				elif curCObj.name is None:
					typeObj = CFuncPointerDecl(parent=curCObj.parent)
					typeObj._bracketlevel = curCObj._bracketlevel
					typeObj._type_tokens[:] = curCObj._type_tokens
					CVarDecl.overtake(curCObj)
					curCObj._type_tokens[:] = [typeObj]
					cpre3_parse_funcpointername(stateStruct, typeObj, input_iter)
					curCObj.name = typeObj.name
				elif len(curCObj._type_tokens) == 1 and isinstance(curCObj._type_tokens[0], CFuncPointerDecl):
					typeObj = curCObj._type_tokens[0]
					cpre3_parse_funcargs(stateStruct, typeObj, input_iter)
					typeObj.finalize(stateStruct)
				else:
					CFunc.overtake(curCObj)
					curCObj.defPos = stateStruct.curPosAsStr()
					cpre3_parse_funcargs(stateStruct, curCObj, input_iter)
			elif token.content == "[":
				CVarDecl.overtake(curCObj)
				cpre3_parse_arrayargs(stateStruct, curCObj, input_iter)
			elif token.content == "{":
				if curCObj.isDerived():
					if isinstance(curCObj, CStruct):
						cpre3_parse_struct(stateStruct, curCObj, input_iter)
					elif isinstance(curCObj, CUnion):
						cpre3_parse_union(stateStruct, curCObj, input_iter)
					elif isinstance(curCObj, CEnum):
						cpre3_parse_enum(stateStruct, curCObj, input_iter)
					elif isinstance(curCObj, CFunc):
						cpre3_parse_funcbody(stateStruct, curCObj, input_iter)
						curCObj = _CBaseWithOptBody(parent=parentCObj)
					else:
						stateStruct.error("cpre3 parse: unexpected '{' after " + str(curCObj))
						curCObj = _CBaseWithOptBody(parent=parentCObj)
				else:
					if not parentCObj.body is stateStruct: # not top level
						CCodeBlock.overtake(curCObj)
						curCObj.defPos = stateStruct.curPosAsStr()
						cpre3_parse_body(stateStruct, curCObj, input_iter)
						curCObj.finalize(stateStruct)
					curCObj = _CBaseWithOptBody(parent=parentCObj)
			else:
				stateStruct.error("cpre3 parse: unexpected opening bracket '" + token.content + "'")
		elif isinstance(token, CClosingBracket):
			if token.content == "}":
				curCObj.finalize(stateStruct)
				curCObj = _CBaseWithOptBody(parent=parentCObj)
			else:
				stateStruct.error("cpre3 parse: unexpected closing bracket '" + token.content + "' after " + str(curCObj))
			if token.brackets == parentCObj._bracketlevel:
				return
			if not _isBracketLevelOk(parentCObj._bracketlevel, token.brackets):
				stateStruct.error("cpre3 parse body: internal error: bracket level messed up with closing bracket: " + str(token.brackets) + " on level " + str(parentCObj._bracketlevel) + " in " + str(parentCObj))
		elif isinstance(token, CSemicolon):
			if not curCObj.isDerived() and curCObj:
				CVarDecl.overtake(curCObj)
			if not curCObj._finalized:
				curCObj.finalize(stateStruct)
			curCObj = _CBaseWithOptBody(parent=parentCObj)
		elif isinstance(token, (CStr,CChar)):
			if isinstance(curCObj, CStatement):
				curCObj._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj.body, CStatement):
				curCObj.body._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, CCaseStatement):
				if not curCObj.args or not isinstance(curCObj.args[-1], CStatement):
					curCObj.args.append(CStatement(parent=parentCObj))
				curCObj.args[-1]._cpre3_handle_token(stateStruct, token)
			elif isinstance(curCObj, _CControlStructure):
				stateStruct.error("cpre3 parse after " + str(curCObj) + ": didn't expected " + str(token))
			elif not curCObj:
				CStatement.overtake(curCObj)
				curCObj._cpre3_handle_token(stateStruct, token)
			else:
				stateStruct.error("cpre3 parse: unexpected str " + str(token) + " after " + str(curCObj))
		else:
			stateStruct.error("cpre3 parse: unexpected token " + str(token))

	if curCObj and not curCObj._finalized:
		stateStruct.error("cpre3 parse: unfinished " + str(curCObj) + " at end of " + str(parentCObj))

	if parentCObj._bracketlevel is not None:
		stateStruct.error("cpre3 parse: read until end without closing brackets " + str(parentCObj._bracketlevel) + " in " + str(parentCObj))

def cpre3_parse(stateStruct, input):
	input_iter = iter(input)
	parentObj = _CBaseWithOptBody()
	parentObj.body = stateStruct
	cpre3_parse_body(stateStruct, parentObj, input_iter)

def parse(filename, state = None):
	if state is None:
		state = State()
		state.autoSetupSystemMacros()

	preprocessed = state.preprocess_file(filename, local=True)
	tokens = cpre2_parse(state, preprocessed)
	cpre3_parse(state, tokens)
	
	return state
	
def test(*args):
	import better_exchook
	better_exchook.install()
	
	state = State()
	state.autoSetupSystemMacros()

	filename = args[0] if args else "/Library/Frameworks/SDL.framework/Headers/SDL.h"
	preprocessed = state.preprocess_file(filename, local=True)
	tokens = cpre2_parse(state, preprocessed)
	
	token_list = []
	def copy_hook(input, output):
		for x in input:
			output.append(x)
			yield x
	tokens = copy_hook(tokens, token_list)
	
	cpre3_parse(state, tokens)
	
	return state, token_list

if __name__ == '__main__':
	import sys
	test(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = cparser_utils
import types
import sys

if sys.version_info.major == 2:
	def rebound_instance_method(f, newobj):
		return types.MethodType(f.im_func, newobj, newobj.__class__)
else:
	def rebound_instance_method(f, newobj):
		return lambda *args, **kwargs: f.__func__(newobj, *args, **kwargs)

if sys.version_info.major == 2:
	def generic_class_method(f):
		return f.im_func
else:
	def generic_class_method(f):
		return f

if sys.version_info.major >= 3:
	unicode = str

########NEW FILE########
__FILENAME__ = cwrapper
# PyCParser - C wrapper
# by Albert Zeyer, 2011
# code under LGPL

import cparser
import ctypes
import sys
if sys.version_info.major == 2:
	from cparser_utils import *
else:
	from .cparser_utils import *

class CStateDictWrapper:
	__doc__ = """generic dict wrapper
	This is a generic dict wrapper to merge multiple dicts to a single one.
	It is intended mostly to merge different dicts from different cparser.State."""
	
	def __init__(self, dicts):
		self._dicts = dicts
	def __setitem__(self, k, v):
		assert False, "read-only in C wrapped state"
	def __getitem__(self, k):
		found = []
		for d in self._dicts:
			try: found += [d[k]]
			except KeyError: pass
		for f in found:
			# prefer items with body set.
			if hasattr(f, "body") and f.body is not None: return f
		if found:
			# fallback, noone has body set.
			return found[0]
		raise KeyError(str(k) + " not found in C wrapped state " + str(self))
	def __contains__(self, k):
		for d in self._dicts:
			if k in d: return True
		return False
	def get(self, k, default = None):
		try: return self.__getitem__(k)
		except KeyError: return default
	def has_key(self, k):
		return self.__contains__(k)
	def __repr__(self): return "CStateDictWrapper(" + repr(self._dicts) + ")"
	def __str__(self): return "CStateDictWrapper(" + str(self._dicts) + ")"

class CStateWrapper:
	__doc__ = """cparser.State wrapper
	Merges multiple cparser.State into a single one."""

	WrappedDicts = ("macros","typedefs","structs","unions","enums","funcs","vars","enumconsts")
	LocalAttribs = ("_cwrapper")
	def __init__(self, cwrapper):
		self._cwrapper = cwrapper
	def __getattr__(self, k):
		if k in self.LocalAttribs: raise AttributeError # normally we shouldn't get here but just in case
		if k == "_errors": return getattr(self._cwrapper, k) # fallthrough to CWrapper to collect all errors there
		if k in self.WrappedDicts:
			return CStateDictWrapper(dicts = map(lambda s: getattr(s, k), self._cwrapper.stateStructs))

		# fallback to first stateStruct
		if len(self._cwrapper.stateStructs) == 0:
			raise AttributeError("CStateWrapper " + str(self) + " doesn't have any state structs set yet")
		stateStruct = self._cwrapper.stateStructs[0]
		attr = getattr(stateStruct, k)
		import types
		if isinstance(attr, types.MethodType):
			attr = rebound_instance_method(attr, self)
		return attr
	def __repr__(self):
		return "<CStateWrapper of " + repr(self._cwrapper) + ">"
	def __str__(self): return self.__repr__()
	def __setattr__(self, k, v):
		self.__dict__[k] = v
	def __getstate__(self):
		assert False, "this is not really prepared/intended to be pickled"

def _castArg(value):
	if isinstance(value, (str,unicode)):
		return ctypes.cast(ctypes.c_char_p(value), ctypes.POINTER(ctypes.c_byte))
	return value
	
class CWrapper:
	__doc__ = """Provides easy access to symbols to be used by Python.
	Wrapped functions are directly callable given the ctypes DLL.
	Use register() to register a new set of (parsed-header-state,dll).
	Use get() to get a symbol-ref (cparser type).
	Use getWrapped() to get a wrapped symbol. In case of a function, this is a
	callable object. In case of some other const, it is its value. In case
	of some type (struct, typedef, enum, ...), it is its ctypes type.
	Use wrapped as an object where its __getattrib__ basically wraps to get().
	"""

	def __init__(selfWrapper):
		selfWrapper._cache = {}
		selfWrapper.stateStructs = []
		class Wrapped(object):
			def __getattribute__(self, attrib):
				if attrib == "_cwrapper": return selfWrapper
				if attrib in ("__dict__","__class__"):
					return object.__getattribute__(self, attrib)
				return selfWrapper.getWrapped(attrib)
		selfWrapper.wrapped = Wrapped()
		selfWrapper._wrappedStateStruct = CStateWrapper(selfWrapper)
		selfWrapper._errors = []
		
	def register(self, stateStruct, clib):
		stateStruct.clib = clib
		self.stateStructs.append(stateStruct)
		def iterAllAttribs():
			for attrib in stateStruct.macros:
				if stateStruct.macros[attrib].args is not None: continue
				yield attrib
			for attrib in stateStruct.typedefs:
				yield attrib
			for attrib in stateStruct.enumconsts:
				yield attrib
			for attrib in stateStruct.funcs:
				yield attrib
		wrappedClass = self.wrapped.__class__
		for attrib in iterAllAttribs():
			if not hasattr(wrappedClass, attrib):
				setattr(wrappedClass, attrib, None)
	
	def resolveMacro(self, stateStruct, macro):
		macro._parseTokens(stateStruct)
		resolvedMacro = macro.getSingleIdentifer(self._wrappedStateStruct) # or just stateStruct?
		if resolvedMacro is not None: self.get(str(resolvedMacro))
		return macro
		
	def get(self, attrib, resolveMacros = True):
		for stateStruct in self.stateStructs:
			if attrib in stateStruct.macros and stateStruct.macros[attrib].args is None:
				if resolveMacros: return self.resolveMacro(stateStruct, stateStruct.macros[attrib])
				else: return stateStruct.macros[attrib]
			elif attrib in stateStruct.typedefs:
				return stateStruct.typedefs[attrib]
			elif attrib in stateStruct.enumconsts:
				return stateStruct.enumconsts[attrib]
			elif attrib in stateStruct.funcs:
				return stateStruct.funcs[attrib]		
		raise AttributeError(attrib + " not found in " + str(self))
		
	def getWrapped(self, attrib):
		cache = self._cache
		if attrib in cache: return cache[attrib]

		s = self.get(attrib)
		assert s
		wrappedStateStruct = self._wrappedStateStruct
		if isinstance(s, cparser.Macro):
			t = s.getCValue(wrappedStateStruct)
		elif isinstance(s, (cparser.CType,cparser.CTypedef,cparser.CStruct,cparser.CEnum)):
			t = s.getCType(wrappedStateStruct)
		elif isinstance(s, cparser.CEnumConst):
			t = s.value
		elif isinstance(s, cparser.CFunc):
			clib = s.parent.body.clib # s.parent.body is supposed to be the stateStruct
			t = s.getCType(wrappedStateStruct)
			f = t((attrib, clib))
			t = lambda *args: f(*map(_castArg, args))			
		else:
			raise AttributeError(attrib + " has unknown type " + repr(s))
		cache[attrib] = t
		return t
	
	def __repr__(self):
		return "<" + self.__class__.__name__  + " of " + repr(self.stateStructs) + ">"

########NEW FILE########
__FILENAME__ = interactive_test_parser
#!/usr/bin/python
# Test interpreter
# by Albert Zeyer, 2011
# code under GPL

import sys, os, os.path
if __name__ == '__main__':
	MyDir = os.path.dirname(sys.argv[0]) or "."
else:
	MyDir = "."

sys.path.append(MyDir + "/../..") # so that 'import cparser' works as expected
sys.path.append(MyDir + "/..") # so that 'import better_exchook' works

import better_exchook
better_exchook.install()

import cparser

input = sys.stdin

def input_reader_hanlder(state):
	oldErrNum = len(state._errors)
	oldContentListNum = len(state.contentlist)
	
	while True:
		c = input.read(1)
		if len(c) == 0: break
		if c == "\n":
			for m in state._errors[oldErrNum:]:
				print "Error:", m
			oldErrNum = len(state._errors)
			for m in state.contentlist[oldContentListNum:]:
				print "Parsed:", m
			oldContentListNum = len(state.contentlist)	
		yield c

def prepareState():
	state = cparser.State()
	state.autoSetupSystemMacros()	
	state.autoSetupGlobalIncludeWrappers()	
	def readInclude(fn):
		if fn == "<input>":
			reader = input_reader_hanlder(state)
			return reader, None
		return cparser.State.readLocalInclude(state, fn)
	state.readLocalInclude = readInclude
	return state

state = prepareState()

if __name__ == '__main__':
	cparser.parse("<input>", state)


########NEW FILE########
__FILENAME__ = test_interpreter
#!/usr/bin/python
# Test interpreter
# by Albert Zeyer, 2011
# code under GPL

import sys, os, os.path
if __name__ == '__main__':
	MyDir = os.path.dirname(sys.argv[0]) or "."
else:
	MyDir = "."

sys.path.append(MyDir + "/../..") # so that 'import cparser' works as expected
sys.path.append(MyDir + "/..") # so that 'import better_exchook' works

import better_exchook
better_exchook.install()

import cparser

def prepareState():
	state = cparser.State()
	state.autoSetupSystemMacros()	
	state.autoSetupGlobalIncludeWrappers()
	return state

state = prepareState()
cparser.parse(MyDir + "/test_interpreter.c", state)

import cparser.interpreter

interpreter = cparser.interpreter.Interpreter()
interpreter.register(state)
interpreter.registerFinalize()

if __name__ == '__main__':
	print "erros so far:"
	for m in state._errors:
		print m
	
	for f in state.contentlist:
		if not isinstance(f, cparser.CFunc): continue
		if not f.body: continue
		
		print
		print "parsed content of " + str(f) + ":"
		for c in f.body.contentlist:
			print c
	
	print
	print "PyAST of main:"
	interpreter.dumpFunc("main")
	
	print
	print
	interpreter.runFunc("main", len(sys.argv), sys.argv + [None])


########NEW FILE########
__FILENAME__ = globalincludewrappers
# PyCParser - global include wrappers
# by Albert Zeyer, 2011
# code under LGPL

from cparser import *
from interpreter import CWrapValue
import ctypes, _ctypes
import errno, os

def _fixCType(t, wrap=False):
	if t is ctypes.c_char_p: t = ctypes.POINTER(ctypes.c_byte)
	if t is ctypes.c_char: t = ctypes.c_byte
	if wrap: return wrapCTypeClassIfNeeded(t)
	return t

def wrapCFunc(state, funcname, restype=None, argtypes=None):
	f = getattr(ctypes.pythonapi, funcname)
	if restype is None: restype = ctypes.c_int
	if restype is CVoidType:
		f.restype = None
	elif restype is not None:
		f.restype = restype = _fixCType(restype, wrap=True)
	if argtypes is not None:
		f.argtypes = map(_fixCType, argtypes)
	state.funcs[funcname] = CWrapValue(f, funcname=funcname, returnType=restype)

def _fixCArg(a):
	if isinstance(a, unicode):
		a = a.encode("utf-8")
	if isinstance(a, str):
		a = ctypes.c_char_p(a)
	if isinstance(a, ctypes.c_char_p) or (isinstance(a, _ctypes._Pointer) and a._type_ is ctypes.c_char):
		return ctypes.cast(a, ctypes.POINTER(ctypes.c_byte))
	if isinstance(a, ctypes.c_char):
		return ctypes.c_byte(ord(a.value))
	return a

def callCFunc(funcname, *args):
	f = getattr(ctypes.pythonapi, funcname)
	args = map(_fixCArg, args)
	return f(*args)

class Wrapper:
	def handle_limits_h(self, state):
		state.macros["UCHAR_MAX"] = Macro(rightside="255")
		state.macros["INT_MAX"] = Macro(rightside=str(2 ** (ctypes.sizeof(ctypes.c_int) * 8 - 1)))
	def handle_stdio_h(self, state):
		state.macros["NULL"] = Macro(rightside="0")
		wrapCFunc(state, "printf", restype=ctypes.c_int, argtypes=(ctypes.c_char_p,))
		FileP = CPointerType(CStdIntType("FILE")).getCType(state)
		wrapCFunc(state, "fopen", restype=FileP, argtypes=(ctypes.c_char_p, ctypes.c_char_p))
		wrapCFunc(state, "fclose", restype=ctypes.c_int, argtypes=(FileP,))
		wrapCFunc(state, "fdopen", restype=FileP, argtypes=(ctypes.c_int, ctypes.c_char_p))
		state.vars["stdin"] = CWrapValue(callCFunc("fdopen", 0, "r"))
		state.vars["stdout"] = CWrapValue(callCFunc("fdopen", 1, "a"))
		state.vars["stderr"] = CWrapValue(callCFunc("fdopen", 2, "a"))
		wrapCFunc(state, "fprintf", restype=ctypes.c_int, argtypes=(FileP, ctypes.c_char_p))
		wrapCFunc(state, "fputs", restype=ctypes.c_int, argtypes=(ctypes.c_char_p, FileP))
		wrapCFunc(state, "fgets", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p, ctypes.c_int, FileP))
		wrapCFunc(state, "fread", restype=ctypes.c_size_t, argtypes=(ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t, FileP))		
		wrapCFunc(state, "fflush", restype=ctypes.c_int, argtypes=(FileP,))
		wrapCFunc(state, "ftell", restype=ctypes.c_long, argtypes=(FileP,))
		wrapCFunc(state, "rewind", restype=CVoidType, argtypes=(FileP,))
		wrapCFunc(state, "ferror", restype=ctypes.c_int, argtypes=(FileP,))
		state.vars["errno"] = CWrapValue(0) # TODO
		state.macros["EOF"] = Macro(rightside="-1") # TODO?
		wrapCFunc(state, "setbuf", restype=CVoidType, argtypes=(FileP, ctypes.c_char_p))
		wrapCFunc(state, "isatty", restype=ctypes.c_int, argtypes=(ctypes.c_int,))
		wrapCFunc(state, "fileno")
		wrapCFunc(state, "getc")
		wrapCFunc(state, "ungetc", restype=ctypes.c_int, argtypes=(ctypes.c_int,FileP))
		struct_stat = state.structs["stat"] = CStruct(name="stat") # TODO
		struct_stat.body = CBody(parent=struct_stat)
		CVarDecl(parent=struct_stat, name="st_mode", type=ctypes.c_int).finalize(state)
		state.funcs["fstat"] = CWrapValue(lambda *args: None, returnType=ctypes.c_int) # TODO
		state.macros["S_IFMT"] = Macro(rightside="0") # TODO
		state.macros["S_IFDIR"] = Macro(rightside="0") # TODO
	def handle_stdlib_h(self, state):
		state.macros["EXIT_SUCCESS"] = Macro(rightside="0")
		state.macros["EXIT_FAILURE"] = Macro(rightside="1")
		wrapCFunc(state, "abort", restype=CVoidType, argtypes=())
		wrapCFunc(state, "exit", restype=CVoidType, argtypes=(ctypes.c_int,))
		wrapCFunc(state, "malloc", restype=ctypes.c_void_p, argtypes=(ctypes.c_size_t,))
		wrapCFunc(state, "free", restype=CVoidType, argtypes=(ctypes.c_void_p,))
		state.funcs["atoi"] = CWrapValue(
			lambda x: ctypes.c_int(int(ctypes.cast(x, ctypes.c_char_p).value)),
			returnType=ctypes.c_int
		)
		state.funcs["getenv"] = CWrapValue(
			lambda x: _fixCArg(ctypes.c_char_p(os.getenv(ctypes.cast(x, ctypes.c_char_p).value))),
			returnType=CPointerType(ctypes.c_byte)
		)
	def handle_stdarg_h(self, state): pass
	def handle_stddef_h(self, state): pass
	def handle_math_h(self, state): pass
	def handle_string_h(self, state):
		wrapCFunc(state, "strlen", restype=ctypes.c_size_t, argtypes=(ctypes.c_char_p,))
		wrapCFunc(state, "strcpy", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,ctypes.c_char_p))
		wrapCFunc(state, "strncpy", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t))
		wrapCFunc(state, "strcat", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,ctypes.c_char_p))
		wrapCFunc(state, "strcmp", restype=ctypes.c_int, argtypes=(ctypes.c_char_p,ctypes.c_char_p))
		wrapCFunc(state, "strncmp", restype=ctypes.c_int, argtypes=(ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t))
		wrapCFunc(state, "strtok", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,ctypes.c_char_p))
		wrapCFunc(state, "strchr", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,ctypes.c_int))
		wrapCFunc(state, "strrchr", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,ctypes.c_int))
		wrapCFunc(state, "strstr", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,ctypes.c_char_p))
		wrapCFunc(state, "strdup", restype=ctypes.c_char_p, argtypes=(ctypes.c_char_p,))
		wrapCFunc(state, "strerror", restype=ctypes.c_char_p, argtypes=(ctypes.c_int,))
	def handle_time_h(self, state): pass
	def handle_ctype_h(self, state): pass
	def handle_wctype_h(self, state): pass
	def handle_assert_h(self, state):
		def assert_wrap(x): assert x
		state.funcs["assert"] = CWrapValue(assert_wrap)
	def handle_signal_h(self, state):
		wrapCFunc(state, "signal")
		state.macros["SIGINT"] = Macro(rightside="2")
		state.macros["SIG_DFL"] = Macro(rightside="(void (*)(int))0")
		state.macros["SIG_IGN"] = Macro(rightside="(void (*)(int))1")
		state.macros["SIG_ERR"] = Macro(rightside="((void (*)(int))-1)")
		
	def find_handler_func(self, filename):
		funcname = "handle_" + filename.replace("/", "__").replace(".", "_")
		return getattr(self, funcname, None)
		
	def readGlobalInclude(self, state, oldFunc, filename):
		f = self.find_handler_func(filename)
		if f is not None:
			def reader():
				f(state)
				return
				yield None # to make it a generator
			return reader(), None
		return oldFunc(filename) # fallback
	
	def install(self, state):
		oldFunc = state.readGlobalInclude
		state.readGlobalInclude = lambda fn: self.readGlobalInclude(state, oldFunc, fn)
		
########NEW FILE########
__FILENAME__ = interpreter
# PyCParser - interpreter
# by Albert Zeyer, 2011
# code under LGPL

from cparser import *
from cwrapper import CStateWrapper

import _ctypes
import ast
import sys
import inspect

class CWrapValue:
	def __init__(self, value, decl=None, **kwattr):
		self.value = value
		self.decl = decl
		for k,v in kwattr.iteritems():
			setattr(self, k, v)
	def __repr__(self):
		s = "<" + self.__class__.__name__ + " "
		if self.decl is not None: s += repr(self.decl) + " "
		s += repr(self.value)
		s += ">"
		return s
	def getCType(self):
		if self.decl is not None: return self.decl.type
		elif self.value is not None and hasattr(self.value, "__class__"):
			return self.value.__class__
			#if isinstance(self.value, (_ctypes._SimpleCData,ctypes.Structure,ctypes.Union)):
		return self	
			
def iterIdentifierNames():
	S = "abcdefghijklmnopqrstuvwxyz0123456789"
	n = 0
	while True:
		v = []
		x = n
		while x > 0 or len(v) == 0:
			v = [x % len(S)] + v
			x /= len(S)
		yield "".join(map(lambda x: S[x], v))
		n += 1

def iterIdWithPostfixes(name):
	if name is None:
		for postfix in iterIdentifierNames():
			yield "__dummy_" + postfix
		return
	yield name
	for postfix in iterIdentifierNames():
		yield name + "_" + postfix

import keyword
PyReservedNames = set(dir(sys.modules["__builtin__"]) + keyword.kwlist + ["ctypes", "helpers"])

def isValidVarName(name):
	return name not in PyReservedNames

class GlobalScope:
	StateScopeDicts = ["vars", "typedefs", "funcs"]
	
	def __init__(self, interpreter, stateStruct):
		self.interpreter = interpreter
		self.stateStruct = stateStruct
		self.identifiers = {} # name -> CVarDecl | ...
		self.names = {} # id(decl) -> name
		self.vars = {} # name -> value
		
	def _findId(self, name):
		for D in self.StateScopeDicts:
			d = getattr(self.stateStruct, D)
			o = d.get(name)
			if o is not None: return o
		return None
	
	def findIdentifier(self, name):
		o = self.identifiers.get(name, None)
		if o is not None: return o
		o = self._findId(name)
		if o is None: return None
		self.identifiers[name] = o
		self.names[id(o)] = name
		return o
	
	def findName(self, decl):
		name = self.names.get(id(decl), None)
		if name is not None: return name
		o = self.findIdentifier(decl.name)
		if o is None: return None
		# Note: `o` might be a different object than `decl`.
		# This can happen if `o` is the extern declaration and `decl`
		# is the actual variable. Anyway, this is fine.
		return o.name
	
	def registerExternVar(self, name_prefix, value=None):
		if not isinstance(value, CWrapValue):
			value = CWrapValue(value)
		for name in iterIdWithPostfixes(name_prefix):
			if self.findIdentifier(name) is not None: continue
			self.identifiers[name] = value
			return name

	def registerExterns(self):
		self.varname_ctypes = self.registerExternVar("ctypes", ctypes)
		self.varname_helpers = self.registerExternVar("helpers", Helpers)

	def getVar(self, name):
		if name in self.vars: return self.vars[name]
		decl = self.findIdentifier(name)
		assert isinstance(decl, CVarDecl)
		if decl.body is not None:
			bodyAst, t = astAndTypeForStatement(self, decl.body)
			if isPointerType(decl.type) and not isPointerType(t):
				v = decl.body.getConstValue(self.stateStruct)
				assert not v, "Global: Initializing pointer type " + str(decl.type) + " only supported with 0 value but we got " + str(v) + " from " + str(decl.body)
				valueAst = getAstNode_newTypeInstance(self.interpreter, decl.type)
			else:
				valueAst = getAstNode_newTypeInstance(self.interpreter, decl.type, bodyAst, t)
		else:	
			valueAst = getAstNode_newTypeInstance(self.interpreter, decl.type)
		v = evalValueAst(self, valueAst, "<PyCParser_globalvar_" + name + "_init>")
		self.vars[name] = v
		return v

def evalValueAst(funcEnv, valueAst, srccode_name=None):
	if srccode_name is None: srccode_name = "<PyCParser_dynamic_eval>"
	valueExprAst = ast.Expression(valueAst)
	ast.fix_missing_locations(valueExprAst)
	valueCode = compile(valueExprAst, "<PyCParser_globalvar_" + srccode_name + "_init>", "eval")
	v = eval(valueCode, funcEnv.interpreter.globalsDict)
	return v

class GlobalsWrapper:
	def __init__(self, globalScope):
		self.globalScope = globalScope
	
	def __setattr__(self, name, value):
		self.__dict__[name] = value
	
	def __getattr__(self, name):
		decl = self.globalScope.findIdentifier(name)
		if decl is None: raise KeyError
		if isinstance(decl, CVarDecl):
			v = self.globalScope.getVar(name)
		elif isinstance(decl, CWrapValue):
			v = decl.value
		elif isinstance(decl, CFunc):
			v = self.globalScope.interpreter.getFunc(name)
		elif isinstance(decl, (CTypedef,CStruct,CUnion,CEnum)):
			v = getCType(decl, self.globalScope.stateStruct)
		elif isinstance(decl, CFuncPointerDecl):
			v = getCType(decl, self.globalScope.stateStruct)
		else:
			assert False, "didn't expected " + str(decl)
		self.__dict__[name] = v
		return v
	
	def __repr__(self):
		return "<" + self.__class__.__name__ + " " + repr(self.__dict__) + ">"

class GlobalsStructWrapper:
	def __init__(self, globalScope):
		self.globalScope = globalScope
	
	def __setattr__(self, name, value):
		self.__dict__[name] = value
	
	def __getattr__(self, name):
		decl = self.globalScope.stateStruct.structs.get(name)
		if decl is None: raise AttributeError
		v = getCType(decl, self.globalScope.stateStruct)
		self.__dict__[name] = v
		return v
	
	def __repr__(self):
		return "<" + self.__class__.__name__ + " " + repr(self.__dict__) + ">"
	
class FuncEnv:
	def __init__(self, globalScope):
		self.globalScope = globalScope
		self.interpreter = globalScope.interpreter
		self.vars = {} # name -> varDecl
		self.varNames = {} # id(varDecl) -> name
		self.scopeStack = [] # FuncCodeblockScope
		self.astNode = ast.FunctionDef(
			args=ast.arguments(args=[], vararg=None, kwarg=None, defaults=[]),
			body=[], decorator_list=[])
	def __repr__(self):
		try: return "<" + self.__class__.__name__ + " of " + self.astNode.name + ">"
		except: return "<" + self.__class__.__name__ + " in invalid state>"			
	def _registerNewVar(self, varName, varDecl):
		if varDecl is not None:
			assert id(varDecl) not in self.varNames
		for name in iterIdWithPostfixes(varName):
			if not isValidVarName(name): continue
			if self.searchVarName(name) is None:
				self.vars[name] = varDecl
				if varDecl is not None:
					self.varNames[id(varDecl)] = name
				return name
	def searchVarName(self, varName):
		if varName in self.vars: return self.vars[varName]
		return self.globalScope.findIdentifier(varName)
	def registerNewVar(self, varName, varDecl=None):
		return self.scopeStack[-1].registerNewVar(varName, varDecl)
	def getAstNodeForVarDecl(self, varDecl):
		assert varDecl is not None
		if id(varDecl) in self.varNames:
			# local var
			name = self.varNames[id(varDecl)]
			assert name is not None
			return ast.Name(id=name, ctx=ast.Load())
		# we expect this is a global
		name = self.globalScope.findName(varDecl)
		assert name is not None, str(varDecl) + " is expected to be a global var"
		return getAstNodeAttrib("g", name)
	def _unregisterVar(self, varName):
		varDecl = self.vars[varName]
		if varDecl is not None:
			del self.varNames[id(varDecl)]
		del self.vars[varName]
	def pushScope(self, bodyStmntList):
		scope = FuncCodeblockScope(funcEnv=self, body=bodyStmntList)
		self.scopeStack += [scope]
		return scope
	def popScope(self):
		scope = self.scopeStack.pop()
		scope.finishMe()
	def getBody(self):
		return self.scopeStack[-1].body
		
NoneAstNode = ast.Name(id="None", ctx=ast.Load())

def getAstNodeAttrib(value, attrib, ctx=ast.Load()):
	a = ast.Attribute(ctx=ctx)
	if isinstance(value, (str,unicode)):
		a.value = ast.Name(id=str(value), ctx=ctx)
	elif isinstance(value, ast.AST):
		a.value = value
	else:
		assert False, str(value) + " has invalid type"
	assert attrib is not None
	a.attr = str(attrib)
	return a

def getAstNodeForCTypesBasicType(t):
	if t is None: return NoneAstNode
	if t is CVoidType: return NoneAstNode
	if not inspect.isclass(t) and isinstance(t, CVoidType): return NoneAstNode
	if inspect.isclass(t) and issubclass(t, CVoidType): return None
	assert issubclass(t, getattr(ctypes, t.__name__))
	return getAstNodeAttrib("ctypes", t.__name__)

def getAstNodeForVarType(interpreter, t):
	if isinstance(t, CBuiltinType):
		return getAstNodeForCTypesBasicType(State.CBuiltinTypes[t.builtinType])
	elif isinstance(t, CStdIntType):
		return getAstNodeForCTypesBasicType(State.StdIntTypes[t.name])
	elif isinstance(t, CPointerType):
		a = getAstNodeAttrib("ctypes", "POINTER")
		return makeAstNodeCall(a, getAstNodeForVarType(interpreter, t.pointerOf))
	elif isinstance(t, CTypedefType):
		return getAstNodeAttrib("g", t.name)
	elif isinstance(t, CStruct):
		if t.name is None:
			# We have a problem. Actually, I wonder how this can happen.
			# But we have an anonymous struct here.
			# Wrap it via CWrapValue
			v = getAstForWrapValue(interpreter, CWrapValue(t))
			return getAstNodeAttrib(v, "value")
		# TODO: this assumes the was previously declared globally.
		return getAstNodeAttrib("structs", t.name)
	else:
		try: return getAstNodeForCTypesBasicType(t)
		except: pass
	assert False, "cannot handle " + str(t)

def findHelperFunc(f):
	for k in dir(Helpers):
		v = getattr(Helpers, k)
		if v is f: return k
	return None

def makeAstNodeCall(func, *args):
	if not isinstance(func, ast.AST):
		name = findHelperFunc(func)
		assert name is not None, str(func) + " unknown"
		func = getAstNodeAttrib("helpers", name)
	return ast.Call(func=func, args=list(args), keywords=[], starargs=None, kwargs=None)

def isPointerType(t):
	if isinstance(t, CPointerType): return True
	if isinstance(t, CFuncPointerDecl): return True
	from inspect import isclass
	if isclass(t):
		if issubclass(t, _ctypes._Pointer): return True
		if issubclass(t, ctypes.c_void_p): return True
	return False

def isValueType(t):
	if isinstance(t, (CBuiltinType,CStdIntType)): return True
	from inspect import isclass
	if isclass(t):
		for c in State.StdIntTypes.values():
			if issubclass(t, c): return True
	return False

def getAstNode_valueFromObj(stateStruct, objAst, objType):
	if isPointerType(objType):
		from inspect import isclass
		if not isclass(objType) or not issubclass(objType, ctypes.c_void_p):
			astVoidPT = getAstNodeAttrib("ctypes", "c_void_p")
			astCast = getAstNodeAttrib("ctypes", "cast")
			astVoidP = makeAstNodeCall(astCast, objAst, astVoidPT)
		else:
			astVoidP = objAst
		astValue = getAstNodeAttrib(astVoidP, "value")
		return ast.BoolOp(op=ast.Or(), values=[astValue, ast.Num(0)])
	elif isValueType(objType):
		astValue = getAstNodeAttrib(objAst, "value")
		return astValue
	elif isinstance(objType, CTypedefType):
		t = stateStruct.typedefs[objType.name]
		return getAstNode_valueFromObj(stateStruct, objAst, t)
	else:
		assert False, "bad type: " + str(objType)
		
def getAstNode_newTypeInstance(interpreter, objType, argAst=None, argType=None):
	typeAst = getAstNodeForVarType(interpreter, objType)

	if isPointerType(objType) and isPointerType(argType):
		# We can have it simpler. This is even important in some cases
		# were the pointer instance is temporary and the object
		# would get freed otherwise!
		astCast = getAstNodeAttrib("ctypes", "cast")
		return makeAstNodeCall(astCast, argAst, typeAst)		
		
	args = []
	if argAst is not None:
		if isinstance(argAst, (ast.Str, ast.Num)):
			args += [argAst]
		elif argType is not None:
			args += [getAstNode_valueFromObj(interpreter._cStateWrapper, argAst, argType)]
		else:
			# expect that it is the AST for the value.
			# there is no really way to 'assert' this.
			args += [argAst]

	if isPointerType(objType) and argAst is not None:
		assert False, "not supported because unsafe! " + str(argAst)
		return makeAstNodeCall(typeAst)		
		#astVoidPT = getAstNodeAttrib("ctypes", "c_void_p")
		#astCast = getAstNodeAttrib("ctypes", "cast")
		#astVoidP = makeAstNodeCall(astVoidPT, *args)
		#return makeAstNodeCall(astCast, astVoidP, typeAst)
	else:
		return makeAstNodeCall(typeAst, *args)

class FuncCodeblockScope:
	def __init__(self, funcEnv, body):
		self.varNames = set()
		self.funcEnv = funcEnv
		self.body = body
	def registerNewVar(self, varName, varDecl):
		varName = self.funcEnv._registerNewVar(varName, varDecl)
		assert varName is not None
		self.varNames.add(varName)
		a = ast.Assign()
		a.targets = [ast.Name(id=varName, ctx=ast.Store())]
		if varDecl is None:
			a.value = ast.Name(id="None", ctx=ast.Load())
		elif isinstance(varDecl, CFuncArgDecl):
			# Note: We just assume that the parameter has the correct/same type.
			a.value = getAstNode_newTypeInstance(self.funcEnv.interpreter, varDecl.type, ast.Name(id=varName, ctx=ast.Load()), varDecl.type)
		elif isinstance(varDecl, CVarDecl):
			if varDecl.body is not None:
				bodyAst, t = astAndTypeForStatement(self.funcEnv, varDecl.body)
				if isPointerType(varDecl.type) and not isPointerType(t):
					v = varDecl.body.getConstValue(self.funcEnv.globalScope.stateStruct)
					assert not v, "Initializing pointer type " + str(varDecl.type) + " only supported with 0 value but we got " + str(v) + " from " + str(varDecl.body)
					a.value = getAstNode_newTypeInstance(self.funcEnv.interpreter, varDecl.type)
				else:
					a.value = getAstNode_newTypeInstance(self.funcEnv.interpreter, varDecl.type, bodyAst, t)
			else:	
				a.value = getAstNode_newTypeInstance(self.funcEnv.interpreter, varDecl.type)
		elif isinstance(varDecl, CFunc):
			# TODO: register func, ...
			a.value = ast.Name(id="None", ctx=ast.Load())
		else:
			assert False, "didn't expected " + str(varDecl)
		self.body.append(a)
		return varName
	def _astForDeleteVar(self, varName):
		assert varName is not None
		return ast.Delete(targets=[ast.Name(id=varName, ctx=ast.Del())])
	def finishMe(self):
		astCmds = []
		for varName in self.varNames:
			astCmds += [self._astForDeleteVar(varName)]
			self.funcEnv._unregisterVar(varName)
		self.varNames.clear()
		self.body.extend(astCmds)

OpUnary = {
	"~": ast.Invert,
	"!": ast.Not,
	"+": ast.UAdd,
	"-": ast.USub,
}

OpBin = {
	"+": ast.Add,
	"-": ast.Sub,
	"*": ast.Mult,
	"/": ast.Div,
	"%": ast.Mod,
	"<<": ast.LShift,
	">>": ast.RShift,
	"|": ast.BitOr,
	"^": ast.BitXor,
	"&": ast.BitAnd,
}

OpBinBool = {
	"&&": ast.And,
	"||": ast.Or,
}

OpBinCmp = {
	"==": ast.Eq,
	"!=": ast.NotEq,
	"<": ast.Lt,
	"<=": ast.LtE,
	">": ast.Gt,
	">=": ast.GtE,
}

OpAugAssign = dict(map(lambda (k,v): (k + "=", v), OpBin.iteritems()))

def _astOpToFunc(op):
	if inspect.isclass(op): op = op()
	assert isinstance(op, ast.operator)
	l = ast.Lambda()
	a = l.args = ast.arguments()
	a.args = [
		ast.Name(id="a", ctx=ast.Param()),
		ast.Name(id="b", ctx=ast.Param())]
	a.vararg = None
	a.kwarg = None
	a.defaults = []
	t = l.body = ast.BinOp()
	t.left = ast.Name(id="a", ctx=ast.Load())
	t.right = ast.Name(id="b", ctx=ast.Load())
	t.op = op
	expr = ast.Expression(body=l)
	ast.fix_missing_locations(expr)
	code = compile(expr, "<_astOpToFunc>", "eval")
	f = eval(code)
	return f

OpBinFuncs = dict(map(lambda op: (op, _astOpToFunc(op)), OpBin.itervalues()))

class Helpers:
	@staticmethod
	def prefixInc(a):
		a.value += 1
		return a
	
	@staticmethod
	def prefixDec(a):
		a.value -= 1
		return a
	
	@staticmethod
	def postfixInc(a):
		b = Helpers.copy(a)
		a.value += 1
		return b
	
	@staticmethod
	def postfixDec(a):
		b = Helpers.copy(a)
		a.value -= 1
		return b
	
	@staticmethod
	def prefixIncPtr(a):
		aPtr = ctypes.cast(ctypes.pointer(a), ctypes.POINTER(ctypes.c_void_p))
		aPtr.contents.value += ctypes.sizeof(a._type_)
		return a

	@staticmethod
	def prefixDecPtr(a):
		aPtr = ctypes.cast(ctypes.pointer(a), ctypes.POINTER(ctypes.c_void_p))
		aPtr.contents.value -= ctypes.sizeof(a._type_)
		return a
	
	@staticmethod
	def postfixIncPtr(a):
		b = Helpers.copy(a)
		aPtr = ctypes.cast(ctypes.pointer(a), ctypes.POINTER(ctypes.c_void_p))
		aPtr.contents.value += ctypes.sizeof(a._type_)
		return b

	@staticmethod
	def postfixDecPtr(a):
		b = Helpers.copy(a)
		aPtr = ctypes.cast(ctypes.pointer(a), ctypes.POINTER(ctypes.c_void_p))
		aPtr.contents.value -= ctypes.sizeof(a._type_)
		return b

	@staticmethod
	def copy(a):
		if isinstance(a, _ctypes._SimpleCData):
			c = a.__class__()
			ctypes.pointer(c)[0] = a
			return c
		if isinstance(a, _ctypes._Pointer):
			return ctypes.cast(a, a.__class__)
		assert False, "cannot copy " + str(a)
	
	@staticmethod
	def assign(a, bValue):
		a.value = bValue
		return a
	
	@staticmethod
	def assignPtr(a, bValue):
		aPtr = ctypes.cast(ctypes.pointer(a), ctypes.POINTER(ctypes.c_void_p))
		aPtr.contents.value = bValue
		return a

	@staticmethod
	def augAssign(a, op, bValue):
		a.value = OpBinFuncs[op](a.value, bValue)
		return a

	@staticmethod
	def augAssignPtr(a, op, bValue):
		assert op in ("+","-")
		op = OpBin[op]
		bValue *= ctypes.sizeof(a._type_)
		aPtr = ctypes.cast(ctypes.pointer(a), ctypes.POINTER(ctypes.c_void_p))
		aPtr.contents.value = OpBinFuncs[op](aPtr.contents.value, bValue)
		return a

	@staticmethod
	def ptrArithmetic(a, op, bValue):
		return Helpers.augAssignPtr(Helpers.copy(a), op, bValue)

def astForHelperFunc(helperFuncName, *astArgs):
	helperFuncAst = getAstNodeAttrib("helpers", helperFuncName)
	a = ast.Call(keywords=[], starargs=None, kwargs=None)
	a.func = helperFuncAst
	a.args = list(astArgs)
	return a

def getAstNodeArrayIndex(base, index, ctx=ast.Load()):
	a = ast.Subscript(ctx=ctx)
	if isinstance(base, (str,unicode)):
		base = ast.Name(id=base, ctx=ctx)
	elif isinstance(base, ast.AST):
		pass # ok
	else:
		assert False, "base " + str(base) + " has invalid type"
	if isinstance(index, ast.AST):
		pass # ok
	elif isinstance(index, (int,long)):
		index = ast.Num(index)
	else:
		assert False, "index " + str(index) + " has invalid type"
	a.value = base
	a.slice = ast.Index(value=index)
	return a

def getAstForWrapValue(interpreter, wrapValue):
	interpreter.wrappedValuesDict[id(wrapValue)] = wrapValue
	v = getAstNodeArrayIndex("values", id(wrapValue))
	return v

def astAndTypeForStatement(funcEnv, stmnt):
	if isinstance(stmnt, (CVarDecl,CFuncArgDecl)):
		return funcEnv.getAstNodeForVarDecl(stmnt), stmnt.type
	elif isinstance(stmnt, CFunc):
		# TODO: specify type correctly
		return funcEnv.getAstNodeForVarDecl(stmnt), CFuncPointerDecl()
	elif isinstance(stmnt, CStatement):
		return astAndTypeForCStatement(funcEnv, stmnt)
	elif isinstance(stmnt, CAttribAccessRef):
		assert stmnt.name is not None
		a = ast.Attribute(ctx=ast.Load())
		a.value, t = astAndTypeForStatement(funcEnv, stmnt.base)
		a.attr = stmnt.name
		while isinstance(t, CTypedefType):
			t = funcEnv.globalScope.stateStruct.typedefs[t.name]
		assert isinstance(t, (CStruct,CUnion))
		attrDecl = t.findAttrib(funcEnv.globalScope.stateStruct, a.attr)
		assert attrDecl is not None, "attrib " + str(a.attr) + " not found"
		return a, attrDecl.type
	elif isinstance(stmnt, CPtrAccessRef):
		# build equivalent AttribAccess statement
		derefStmnt = CStatement()
		derefStmnt._op = COp("*")
		derefStmnt._rightexpr = stmnt.base
		attrStmnt = CAttribAccessRef()
		attrStmnt.base = derefStmnt
		attrStmnt.name = stmnt.name
		return astAndTypeForStatement(funcEnv, attrStmnt)		
	elif isinstance(stmnt, CNumber):
		t = minCIntTypeForNums(stmnt.content, useUnsignedTypes=False)
		if t is None: t = "int64_t" # it's an overflow; just take a big type
		t = CStdIntType(t)
		return getAstNode_newTypeInstance(funcEnv.interpreter, t, ast.Num(n=stmnt.content)), t
	elif isinstance(stmnt, CStr):
		t = CPointerType(ctypes.c_byte)
		v = makeAstNodeCall(getAstNodeAttrib("ctypes", "c_char_p"), ast.Str(s=str(stmnt.content)))
		return getAstNode_newTypeInstance(funcEnv.interpreter, t, v, t), t
	elif isinstance(stmnt, CChar):
		return makeAstNodeCall(getAstNodeAttrib("ctypes", "c_byte"), ast.Num(ord(str(stmnt.content)))), ctypes.c_byte
	elif isinstance(stmnt, CFuncCall):
		if isinstance(stmnt.base, CFunc):
			assert stmnt.base.name is not None
			a = ast.Call(keywords=[], starargs=None, kwargs=None)
			a.func = getAstNodeAttrib("g", stmnt.base.name)
			a.args = map(lambda arg: astAndTypeForStatement(funcEnv, arg)[0], stmnt.args)
			return a, stmnt.base.type
		elif isinstance(stmnt.base, CSizeofSymbol):
			assert len(stmnt.args) == 1
			t = getCType(stmnt.args[0], funcEnv.globalScope.stateStruct)
			assert t is not None
			s = ctypes.sizeof(t)
			return ast.Num(s), ctypes.c_size_t
		elif isinstance(stmnt.base, CStatement) and stmnt.base.isCType():
			# C static cast
			assert len(stmnt.args) == 1
			bAst, bType = astAndTypeForStatement(funcEnv, stmnt.args[0])
			bValueAst = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, bAst, bType)
			aType = stmnt.base.asType()
			aTypeAst = getAstNodeForVarType(funcEnv.globalScope.interpreter, aType)

			if isPointerType(aType):
				astVoidPT = getAstNodeAttrib("ctypes", "c_void_p")
				astCast = getAstNodeAttrib("ctypes", "cast")
				astVoidP = makeAstNodeCall(astVoidPT, bValueAst)
				return makeAstNodeCall(astCast, astVoidP, aTypeAst), aType
			else:
				return makeAstNodeCall(aTypeAst, bValueAst), aType
		elif isinstance(stmnt.base, CStatement):
			# func ptr call
			a = ast.Call(keywords=[], starargs=None, kwargs=None)
			pAst, pType = astAndTypeForStatement(funcEnv, stmnt.base)
			assert isinstance(pType, CFuncPointerDecl)
			a.func = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, pAst, pType)
			a.args = map(lambda arg: astAndTypeForStatement(funcEnv, arg)[0], stmnt.args)
			return a, pType.type
		elif isinstance(stmnt.base, CWrapValue):
			# expect that we just wrapped a callable function/object
			a = ast.Call(keywords=[], starargs=None, kwargs=None)
			a.func = getAstNodeAttrib(getAstForWrapValue(funcEnv.globalScope.interpreter, stmnt.base), "value")
			a.args = map(lambda arg: astAndTypeForStatement(funcEnv, arg)[0], stmnt.args)
			return a, stmnt.base.returnType			
		else:
			assert False, "cannot handle " + str(stmnt.base) + " call"
	elif isinstance(stmnt, CArrayIndexRef):
		aAst, aType = astAndTypeForStatement(funcEnv, stmnt.base)
		assert isinstance(aType, CPointerType)
		assert len(stmnt.args) == 1
		# kind of a hack: create equivalent ptr arithmetic expression
		ptrStmnt = CStatement()
		ptrStmnt._leftexpr = stmnt.base
		ptrStmnt._op = COp("+")
		ptrStmnt._rightexpr = stmnt.args[0]
		derefStmnt = CStatement()
		derefStmnt._op = COp("*")
		derefStmnt._rightexpr = ptrStmnt
		return astAndTypeForCStatement(funcEnv, derefStmnt)
		# TODO: support for real arrays.
		# the following code may be useful
		#bAst, bType = astAndTypeForStatement(funcEnv, stmnt.args[0])
		#bValueAst = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, bAst, bType)
		#return getAstNodeArrayIndex(aAst, bValueAst), aType.pointerOf
	elif isinstance(stmnt, CWrapValue):
		v = getAstForWrapValue(funcEnv.globalScope.interpreter, stmnt)
		return getAstNodeAttrib(v, "value"), stmnt.getCType()
	else:
		assert False, "cannot handle " + str(stmnt)

def getAstNode_assign(stateStruct, aAst, aType, bAst, bType):
	bValueAst = getAstNode_valueFromObj(stateStruct, bAst, bType)
	if isPointerType(aType):
		return makeAstNodeCall(Helpers.assignPtr, aAst, bValueAst)
	return makeAstNodeCall(Helpers.assign, aAst, bValueAst)

def getAstNode_augAssign(stateStruct, aAst, aType, opStr, bAst, bType):
	opAst = ast.Str(opStr)
	bValueAst = getAstNode_valueFromObj(stateStruct, bAst, bType)
	if isPointerType(aType):
		return makeAstNodeCall(Helpers.augAssignPtr, aAst, opAst, bValueAst)
	return makeAstNodeCall(Helpers.augAssign, aAst, opAst, bValueAst)

def getAstNode_prefixInc(aAst, aType):
	if isPointerType(aType):
		return makeAstNodeCall(Helpers.prefixIncPtr, aAst)
	return makeAstNodeCall(Helpers.prefixInc, aAst)

def getAstNode_prefixDec(aAst, aType):
	if isPointerType(aType):
		return makeAstNodeCall(Helpers.prefixDecPtr, aAst)
	return makeAstNodeCall(Helpers.prefixDec, aAst)

def getAstNode_postfixInc(aAst, aType):
	if isPointerType(aType):
		return makeAstNodeCall(Helpers.postfixIncPtr, aAst)
	return makeAstNodeCall(Helpers.postfixInc, aAst)

def getAstNode_postfixDec(aAst, aType):
	if isPointerType(aType):
		return makeAstNodeCall(Helpers.postfixDecPtr, aAst)
	return makeAstNodeCall(Helpers.postfixDec, aAst)

def getAstNode_ptrBinOpExpr(stateStruct, aAst, aType, opStr, bAst, bType):
	assert isPointerType(aType)
	opAst = ast.Str(opStr)
	bValueAst = getAstNode_valueFromObj(stateStruct, bAst, bType)
	return makeAstNodeCall(Helpers.ptrArithmetic, aAst, opAst, bValueAst)
	
def astAndTypeForCStatement(funcEnv, stmnt):
	assert isinstance(stmnt, CStatement)
	if stmnt._leftexpr is None: # prefixed only
		rightAstNode,rightType = astAndTypeForStatement(funcEnv, stmnt._rightexpr)
		if stmnt._op.content == "++":
			return getAstNode_prefixInc(rightAstNode, rightType), rightType
		elif stmnt._op.content == "--":
			return getAstNode_prefixDec(rightAstNode, rightType), rightType
		elif stmnt._op.content == "*":
			while isinstance(rightType, CTypedefType):
				rightType = funcEnv.globalScope.stateStruct.typedefs[rightType.name]
			if isinstance(rightType, CPointerType):
				return getAstNodeAttrib(rightAstNode, "contents"), rightType.pointerOf
			elif isinstance(rightType, CFuncPointerDecl):
				return rightAstNode, rightType # we cannot really dereference a funcptr with ctypes ...
			else:
				assert False, str(stmnt) + " has bad type " + str(rightType)
		elif stmnt._op.content == "&":
			return makeAstNodeCall(getAstNodeAttrib("ctypes", "pointer"), rightAstNode), CPointerType(rightType)
		elif stmnt._op.content in OpUnary:
			a = ast.UnaryOp()
			a.op = OpUnary[stmnt._op.content]()
			if isPointerType(rightType):
				assert stmnt._op.content == "!", "the only supported unary op for ptr types is '!'"
				a.operand = makeAstNodeCall(
					ast.Name(id="bool", ctx=ast.Load()),
					rightAstNode)
				rightType = ctypes.c_int
			else:
				a.operand = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, rightAstNode, rightType)
			return getAstNode_newTypeInstance(funcEnv.interpreter, rightType, a), rightType
		else:
			assert False, "unary prefix op " + str(stmnt._op) + " is unknown"
	if stmnt._op is None:
		return astAndTypeForStatement(funcEnv, stmnt._leftexpr)
	if stmnt._rightexpr is None:
		leftAstNode, leftType = astAndTypeForStatement(funcEnv, stmnt._leftexpr)
		if stmnt._op.content == "++":
			return getAstNode_postfixInc(leftAstNode, leftType), leftType
		elif stmnt._op.content == "--":
			return getAstNode_postfixDec(leftAstNode, leftType), leftType
		else:
			assert False, "unary postfix op " + str(stmnt._op) + " is unknown"
	leftAstNode, leftType = astAndTypeForStatement(funcEnv, stmnt._leftexpr)
	rightAstNode, rightType = astAndTypeForStatement(funcEnv, stmnt._rightexpr)
	if stmnt._op.content == "=":
		return getAstNode_assign(funcEnv.globalScope.stateStruct, leftAstNode, leftType, rightAstNode, rightType), leftType
	elif stmnt._op.content in OpAugAssign:
		return getAstNode_augAssign(funcEnv.globalScope.stateStruct, leftAstNode, leftType, stmnt._op.content, rightAstNode, rightType), leftType
	elif stmnt._op.content in OpBinBool:
		a = ast.BoolOp()
		a.op = OpBinBool[stmnt._op.content]()
		a.values = [
			getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, leftAstNode, leftType),
			getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, rightAstNode, rightType)]
		return getAstNode_newTypeInstance(funcEnv.interpreter, ctypes.c_int, a), ctypes.c_int
	elif stmnt._op.content in OpBinCmp:
		a = ast.Compare()
		a.ops = [OpBinCmp[stmnt._op.content]()]
		a.left = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, leftAstNode, leftType)
		a.comparators = [getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, rightAstNode, rightType)]
		return getAstNode_newTypeInstance(funcEnv.interpreter, ctypes.c_int, a), ctypes.c_int
	elif stmnt._op.content == "?:":
		middleAstNode, middleType = astAndTypeForStatement(funcEnv, stmnt._middleexpr)
		a = ast.IfExp()
		a.test = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, leftAstNode, leftType)
		a.body = middleAstNode
		a.orelse = rightAstNode
		# TODO: we take the type from middleType right now. not really correct...
		# So, cast the orelse part.
		a.orelse = getAstNode_newTypeInstance(funcEnv.interpreter, middleType, a.orelse, rightType)
		return a, middleType
	elif isPointerType(leftType):
		return getAstNode_ptrBinOpExpr(
			funcEnv.globalScope.stateStruct,
			leftAstNode, leftType,
			stmnt._op.content,
			rightAstNode, rightType), leftType
	elif stmnt._op.content in OpBin:
		a = ast.BinOp()
		a.op = OpBin[stmnt._op.content]()
		a.left = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, leftAstNode, leftType)
		a.right = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, rightAstNode, rightType)		
		return getAstNode_newTypeInstance(funcEnv.interpreter, leftType, a), leftType # TODO: not really correct. e.g. int + float -> float
	else:
		assert False, "binary op " + str(stmnt._op) + " is unknown"

PyAstNoOp = ast.Assert(test=ast.Name(id="True", ctx=ast.Load()), msg=None)

def astForCWhile(funcEnv, stmnt):
	assert isinstance(stmnt, CWhileStatement)
	assert len(stmnt.args) == 1
	assert isinstance(stmnt.args[0], CStatement)

	whileAst = ast.While(body=[], orelse=[])
	whileAst.test = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, *astAndTypeForCStatement(funcEnv, stmnt.args[0]))

	funcEnv.pushScope(whileAst.body)
	if stmnt.body is not None:
		cCodeToPyAstList(funcEnv, stmnt.body)
	if not whileAst.body: whileAst.body.append(ast.Pass())
	funcEnv.popScope()

	return whileAst

def astForCFor(funcEnv, stmnt):
	assert isinstance(stmnt, CForStatement)
	assert len(stmnt.args) == 3
	assert isinstance(stmnt.args[1], CStatement) # second arg is the check; we must be able to evaluate that

	# introduce dummy 'if' AST so that we have a scope for the for-loop (esp. the first statement)
	ifAst = ast.If(body=[], orelse=[], test=ast.Name(id="True", ctx=ast.Load()))
	funcEnv.pushScope(ifAst.body)
	cStatementToPyAst(funcEnv, stmnt.args[0])
	
	whileAst = ast.While(body=[], orelse=[], test=ast.Name(id="True", ctx=ast.Load()))
	ifAst.body.append(whileAst)

	ifTestAst = ast.If(body=[ast.Pass()], orelse=[ast.Break()])
	ifTestAst.test = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, *astAndTypeForCStatement(funcEnv, stmnt.args[1]))
	whileAst.body.append(ifTestAst)
	
	funcEnv.pushScope(whileAst.body)
	if stmnt.body is not None:
		cCodeToPyAstList(funcEnv, stmnt.body)
	cStatementToPyAst(funcEnv, stmnt.args[2])	
	funcEnv.popScope() # whileAst / main for-body
	
	funcEnv.popScope() # ifAst
	return ifAst

def astForCDoWhile(funcEnv, stmnt):
	assert isinstance(stmnt, CDoStatement)
	assert isinstance(stmnt.whilePart, CWhileStatement)
	assert stmnt.whilePart.body is None
	assert len(stmnt.args) == 0
	assert len(stmnt.whilePart.args) == 1
	assert isinstance(stmnt.whilePart.args[0], CStatement)
	whileAst = ast.While(body=[], orelse=[], test=ast.Name(id="True", ctx=ast.Load()))
	
	funcEnv.pushScope(whileAst.body)
	if stmnt.body is not None:
		cCodeToPyAstList(funcEnv, stmnt.body)
	funcEnv.popScope()

	ifAst = ast.If(body=[ast.Continue()], orelse=[ast.Break()])
	ifAst.test = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, *astAndTypeForCStatement(funcEnv, stmnt.whilePart.args[0]))
	whileAst.body.append(ifAst)
	
	return whileAst

def astForCIf(funcEnv, stmnt):
	assert isinstance(stmnt, CIfStatement)
	assert len(stmnt.args) == 1
	assert isinstance(stmnt.args[0], CStatement)

	ifAst = ast.If(body=[], orelse=[])
	ifAst.test = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, *astAndTypeForCStatement(funcEnv, stmnt.args[0]))

	funcEnv.pushScope(ifAst.body)
	if stmnt.body is not None:
		cCodeToPyAstList(funcEnv, stmnt.body)
	if not ifAst.body: ifAst.body.append(ast.Pass())
	funcEnv.popScope()
	
	if stmnt.elsePart is not None:
		assert stmnt.elsePart.body is not None
		funcEnv.pushScope(ifAst.orelse)
		cCodeToPyAstList(funcEnv, stmnt.elsePart.body)
		if not ifAst.orelse: ifAst.orelse.append(ast.Pass())
		funcEnv.popScope()

	return ifAst

def astForCSwitch(funcEnv, stmnt):
	assert isinstance(stmnt, CSwitchStatement)
	assert isinstance(stmnt.body, CBody)
	assert len(stmnt.args) == 1
	assert isinstance(stmnt.args[0], CStatement)

	# introduce dummy 'if' AST so that we can return a single AST node
	ifAst = ast.If(body=[], orelse=[], test=ast.Name(id="True", ctx=ast.Load()))
	funcEnv.pushScope(ifAst.body)

	switchVarName = funcEnv.registerNewVar("_switchvalue")	
	switchValueAst, switchValueType = astAndTypeForCStatement(funcEnv, stmnt.args[0])
	a = ast.Assign()
	a.targets = [ast.Name(id=switchVarName, ctx=ast.Store())]
	a.value = getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, switchValueAst, switchValueType)
	funcEnv.getBody().append(a)
	
	fallthroughVarName = funcEnv.registerNewVar("_switchfallthrough")
	a = ast.Assign()
	a.targets = [ast.Name(id=fallthroughVarName, ctx=ast.Store())]
	a.value = ast.Name(id="False", ctx=ast.Load())
	fallthroughVarAst = ast.Name(id=fallthroughVarName, ctx=ast.Load())
	funcEnv.getBody().append(a)

	# use 'while' AST so that we can just use 'break' as intended
	whileAst = ast.While(body=[], orelse=[], test=ast.Name(id="True", ctx=ast.Load()))
	funcEnv.getBody().append(whileAst)	
	funcEnv.pushScope(whileAst.body)
	
	curCase = None
	for c in stmnt.body.contentlist:
		if isinstance(c, CCaseStatement):
			if curCase is not None: funcEnv.popScope()
			assert len(c.args) == 1
			curCase = ast.If(body=[], orelse=[])
			curCase.test = ast.BoolOp(op=ast.Or(), values=[
				fallthroughVarAst,
				ast.Compare(
					left=ast.Name(id=switchVarName, ctx=ast.Load()),
					ops=[ast.Eq()],
					comparators=[getAstNode_valueFromObj(funcEnv.globalScope.stateStruct, *astAndTypeForCStatement(funcEnv, c.args[0]))]
					)
				])
			funcEnv.getBody().append(curCase)
			funcEnv.pushScope(curCase.body)
			a = ast.Assign()
			a.targets = [ast.Name(id=fallthroughVarName, ctx=ast.Store())]
			a.value = ast.Name(id="True", ctx=ast.Load())
			funcEnv.getBody().append(a)
			
		elif isinstance(c, CCaseDefaultStatement):
			if curCase is not None: funcEnv.popScope()
			curCase = ast.If(body=[], orelse=[])
			curCase.test = ast.UnaryOp(op=ast.Not(), operand=fallthroughVarAst)
			funcEnv.getBody().append(curCase)
			funcEnv.pushScope(curCase.body)

		else:
			assert curCase is not None
			cStatementToPyAst(funcEnv, c)
	if curCase is not None: funcEnv.popScope()
	
	# finish 'while'
	funcEnv.getBody().append(ast.Break())
	funcEnv.popScope()
	
	# finish 'if'
	funcEnv.popScope()
	return ifAst

def astForCReturn(funcEnv, stmnt):
	assert isinstance(stmnt, CReturnStatement)
	if not stmnt.body:
		assert isSameType(funcEnv.globalScope.stateStruct, funcEnv.func.type, CVoidType())
		return ast.Return(value=None)
	assert isinstance(stmnt.body, CStatement)
	valueAst, valueType = astAndTypeForCStatement(funcEnv, stmnt.body)
	returnValueAst = getAstNode_newTypeInstance(funcEnv.interpreter, funcEnv.func.type, valueAst, valueType)
	return ast.Return(value=returnValueAst)

def cStatementToPyAst(funcEnv, c):
	body = funcEnv.getBody()
	if isinstance(c, (CVarDecl,CFunc)):
		funcEnv.registerNewVar(c.name, c)
	elif isinstance(c, CStatement):
		a, t = astAndTypeForCStatement(funcEnv, c)
		if isinstance(a, ast.expr):
			a = ast.Expr(value=a)
		body.append(a)
	elif isinstance(c, CWhileStatement):
		body.append(astForCWhile(funcEnv, c))
	elif isinstance(c, CForStatement):
		body.append(astForCFor(funcEnv, c))
	elif isinstance(c, CDoStatement):
		body.append(astForCDoWhile(funcEnv, c))
	elif isinstance(c, CIfStatement):
		body.append(astForCIf(funcEnv, c))
	elif isinstance(c, CSwitchStatement):
		body.append(astForCSwitch(funcEnv, c))
	elif isinstance(c, CReturnStatement):
		body.append(astForCReturn(funcEnv, c))
	elif isinstance(c, CBreakStatement):
		body.append(ast.Break())
	elif isinstance(c, CContinueStatement):
		body.append(ast.Continue())
	elif isinstance(c, CCodeBlock):
		funcEnv.pushScope(body)
		cCodeToPyAstList(funcEnv, c.body)
		funcEnv.popScope()
	else:
		assert False, "cannot handle " + str(c)

def cCodeToPyAstList(funcEnv, cBody):
	if isinstance(cBody, CBody):
		for c in cBody.contentlist:
			cStatementToPyAst(funcEnv, c)
	else:
		cStatementToPyAst(funcEnv, cBody)
		
class Interpreter:
	def __init__(self):
		self.stateStructs = []
		self._cStateWrapper = CStateWrapper(self)
		self._cStateWrapper.IndirectSimpleCTypes = True
		self._cStateWrapper.error = self._cStateWrapperError
		self.globalScope = GlobalScope(self, self._cStateWrapper)
		self._func_cache = {}
		self.globalsWrapper = GlobalsWrapper(self.globalScope)
		self.globalsStructWrapper = GlobalsStructWrapper(self.globalScope)
		self.wrappedValuesDict = {} # id(obj) -> obj
		self.globalsDict = {
			"ctypes": ctypes,
			"helpers": Helpers,
			"g": self.globalsWrapper,
			"structs": self.globalsStructWrapper,
			"values": self.wrappedValuesDict,
			"intp": self
			}
	
	def _cStateWrapperError(self, s):
		print "Error:", s
		
	def register(self, stateStruct):
		self.stateStructs += [stateStruct]
	
	def registerFinalize(self):
		self.globalScope.registerExterns()
	
	def getCType(self, obj):
		wrappedStateStruct = self._cStateWrapper
		for T,DictName in [(CStruct,"structs"), (CUnion,"unions"), (CEnum,"enums")]:
			if isinstance(obj, T):
				if obj.name is not None:
					return getattr(wrappedStateStruct, DictName)[obj.name].getCValue(wrappedStateStruct)
				else:
					return obj.getCValue(wrappedStateStruct)
		return obj.getCValue(wrappedStateStruct)
	
	def _translateFuncToPyAst(self, func):
		assert isinstance(func, CFunc)
		base = FuncEnv(globalScope=self.globalScope)
		assert func.name is not None
		base.func = func
		base.astNode.name = func.name
		base.pushScope(base.astNode.body)
		for arg in func.args:
			name = base.registerNewVar(arg.name, arg)
			assert name is not None
			base.astNode.args.args.append(ast.Name(id=name, ctx=ast.Param()))
		if func.body is None:
			# TODO: search in other C files
			# Hack for now: ignore :)
			print "XXX:", func.name, "is not loaded yet"
		else:
			cCodeToPyAstList(base, func.body)
		base.popScope()
		if isSameType(self._cStateWrapper, func.type, CVoidType()):
			returnValueAst = NoneAstNode
		else:
			returnTypeAst = getAstNodeForVarType(self, func.type)
			returnValueAst = makeAstNodeCall(returnTypeAst)
		base.astNode.body.append(ast.Return(value=returnValueAst))
		return base

	@staticmethod
	def _unparse(pyAst):
		from cStringIO import StringIO
		output = StringIO()
		from py_demo_unparse import Unparser
		Unparser(pyAst, output)
		output.write("\n")
		return output.getvalue()

	def _compile(self, pyAst):
		# We unparse + parse again for now for better debugging (so we get some code in a backtrace).
		def _set_linecache(filename, source):
			import linecache
			linecache.cache[filename] = None, None, [line+'\n' for line in source.splitlines()], filename
		SRC_FILENAME = "<PyCParser_" + pyAst.name + ">"
		def _unparseAndParse(pyAst):
			src = self._unparse(pyAst)
			_set_linecache(SRC_FILENAME, src)
			return compile(src, SRC_FILENAME, "single")
		def _justCompile(pyAst):
			exprAst = ast.Interactive(body=[pyAst])		
			ast.fix_missing_locations(exprAst)
			return compile(exprAst, SRC_FILENAME, "single")
		return _unparseAndParse(pyAst)
	
	def _translateFuncToPy(self, funcname):
		cfunc = self._cStateWrapper.funcs[funcname]
		funcEnv = self._translateFuncToPyAst(cfunc)
		pyAst = funcEnv.astNode
		compiled = self._compile(pyAst)
		d = {}
		exec compiled in self.globalsDict, d
		func = d[funcname]
		func.C_cFunc = cfunc
		func.C_pyAst = pyAst
		func.C_interpreter = self
		func.C_argTypes = map(lambda a: a.type, cfunc.args)
		func.C_unparse = lambda: self._unparse(pyAst)
		return func

	def getFunc(self, funcname):
		if funcname in self._func_cache:
			return self._func_cache[funcname]
		else:
			func = self._translateFuncToPy(funcname)
			self._func_cache[funcname] = func
			return func
	
	def dumpFunc(self, funcname, output=sys.stdout):
		f = self.getFunc(funcname)
		print >>output, f.C_unparse()
	
	def _castArgToCType(self, arg, typ):
		if isinstance(typ, CPointerType):
			ctyp = getCType(typ, self._cStateWrapper)
			if arg is None:
				return ctyp()
			elif isinstance(arg, (str,unicode)):
				return ctypes.cast(ctypes.c_char_p(arg), ctyp)
			assert isinstance(arg, (list,tuple))
			o = (ctyp._type_ * (len(arg) + 1))()
			for i in xrange(len(arg)):
				o[i] = self._castArgToCType(arg[i], typ.pointerOf)
			op = ctypes.pointer(o)
			op = ctypes.cast(op, ctyp)
			# TODO: what when 'o' goes out of scope and freed?
			return op
		elif isinstance(arg, (int,long)):
			t = minCIntTypeForNums(arg)
			if t is None: t = "int64_t" # it's an overflow; just take a big type
			return self._cStateWrapper.StdIntTypes[t](arg)			
		else:
			assert False, "cannot cast " + str(arg) + " to " + str(typ)
	
	def runFunc(self, funcname, *args):
		f = self.getFunc(funcname)
		assert len(args) == len(f.C_argTypes)
		args = map(lambda (arg,typ): self._castArgToCType(arg,typ), zip(args,f.C_argTypes))
		return f(*args)

########NEW FILE########
__FILENAME__ = py_demo_unparse
"Usage: unparse.py <path to source file>"
import sys
import ast
import cStringIO
import os

# Large float and imaginary literals get turned into infinities in the AST.
# We unparse those infinities to INFSTR.
INFSTR = "1e" + repr(sys.float_info.max_10_exp + 1)

def interleave(inter, f, seq):
    """Call f on each item in seq, calling inter() in between.
    """
    seq = iter(seq)
    try:
        f(next(seq))
    except StopIteration:
        pass
    else:
        for x in seq:
            inter()
            f(x)

class Unparser:
    """Methods in this class recursively traverse an AST and
    output source code for the abstract syntax; original formatting
    is disregarded. """

    def __init__(self, tree, file = sys.stdout):
        """Unparser(tree, file=sys.stdout) -> None.
         Print the source for tree to file."""
        self.f = file
        self.future_imports = []
        self._indent = 0
        self.dispatch(tree)
        self.f.write("")
        self.f.flush()

    def fill(self, text = ""):
        "Indent a piece of text, according to the current indentation level"
        self.f.write("\n"+"    "*self._indent + text)

    def write(self, text):
        "Append a piece of text to the current line."
        self.f.write(text)

    def enter(self):
        "Print ':', and increase the indentation."
        self.write(":")
        self._indent += 1

    def leave(self):
        "Decrease the indentation level."
        self._indent -= 1

    def dispatch(self, tree):
        "Dispatcher function, dispatching tree type T to method _T."
        if isinstance(tree, list):
            for t in tree:
                self.dispatch(t)
            return
        meth = getattr(self, "_"+tree.__class__.__name__)
        meth(tree)


    ############### Unparsing methods ######################
    # There should be one method per concrete grammar type #
    # Constructors should be grouped by sum type. Ideally, #
    # this would follow the order in the grammar, but      #
    # currently doesn't.                                   #
    ########################################################

    def _Module(self, tree):
        for stmt in tree.body:
            self.dispatch(stmt)

    # stmt
    def _Expr(self, tree):
        self.fill()
        self.dispatch(tree.value)

    def _Import(self, t):
        self.fill("import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)

    def _ImportFrom(self, t):
        # A from __future__ import may affect unparsing, so record it.
        if t.module and t.module == '__future__':
            self.future_imports.extend(n.name for n in t.names)

        self.fill("from ")
        self.write("." * t.level)
        if t.module:
            self.write(t.module)
        self.write(" import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)

    def _Assign(self, t):
        self.fill()
        for target in t.targets:
            self.dispatch(target)
            self.write(" = ")
        self.dispatch(t.value)

    def _AugAssign(self, t):
        self.fill()
        self.dispatch(t.target)
        self.write(" "+self.binop[t.op.__class__.__name__]+"= ")
        self.dispatch(t.value)

    def _Return(self, t):
        self.fill("return")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)

    def _Pass(self, t):
        self.fill("pass")

    def _Break(self, t):
        self.fill("break")

    def _Continue(self, t):
        self.fill("continue")

    def _Delete(self, t):
        self.fill("del ")
        interleave(lambda: self.write(", "), self.dispatch, t.targets)

    def _Assert(self, t):
        self.fill("assert ")
        self.dispatch(t.test)
        if t.msg:
            self.write(", ")
            self.dispatch(t.msg)

    def _Exec(self, t):
        self.fill("exec ")
        self.dispatch(t.body)
        if t.globals:
            self.write(" in ")
            self.dispatch(t.globals)
        if t.locals:
            self.write(", ")
            self.dispatch(t.locals)

    def _Print(self, t):
        self.fill("print ")
        do_comma = False
        if t.dest:
            self.write(">>")
            self.dispatch(t.dest)
            do_comma = True
        for e in t.values:
            if do_comma:self.write(", ")
            else:do_comma=True
            self.dispatch(e)
        if not t.nl:
            self.write(",")

    def _Global(self, t):
        self.fill("global ")
        interleave(lambda: self.write(", "), self.write, t.names)

    def _Yield(self, t):
        self.write("(")
        self.write("yield")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)
        self.write(")")

    def _Raise(self, t):
        self.fill('raise ')
        if t.type:
            self.dispatch(t.type)
        if t.inst:
            self.write(", ")
            self.dispatch(t.inst)
        if t.tback:
            self.write(", ")
            self.dispatch(t.tback)

    def _TryExcept(self, t):
        self.fill("try")
        self.enter()
        self.dispatch(t.body)
        self.leave()

        for ex in t.handlers:
            self.dispatch(ex)
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _TryFinally(self, t):
        if len(t.body) == 1 and isinstance(t.body[0], ast.TryExcept):
            # try-except-finally
            self.dispatch(t.body)
        else:
            self.fill("try")
            self.enter()
            self.dispatch(t.body)
            self.leave()

        self.fill("finally")
        self.enter()
        self.dispatch(t.finalbody)
        self.leave()

    def _ExceptHandler(self, t):
        self.fill("except")
        if t.type:
            self.write(" ")
            self.dispatch(t.type)
        if t.name:
            self.write(" as ")
            self.dispatch(t.name)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _ClassDef(self, t):
        self.write("\n")
        for deco in t.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        self.fill("class "+t.name)
        if t.bases:
            self.write("(")
            for a in t.bases:
                self.dispatch(a)
                self.write(", ")
            self.write(")")
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _FunctionDef(self, t):
        self.write("\n")
        for deco in t.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        self.fill("def "+t.name + "(")
        self.dispatch(t.args)
        self.write(")")
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _For(self, t):
        self.fill("for ")
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _If(self, t):
        self.fill("if ")
        self.dispatch(t.test)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        # collapse nested ifs into equivalent elifs.
        while (t.orelse and len(t.orelse) == 1 and
               isinstance(t.orelse[0], ast.If)):
            t = t.orelse[0]
            self.fill("elif ")
            self.dispatch(t.test)
            self.enter()
            self.dispatch(t.body)
            self.leave()
        # final else
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _While(self, t):
        self.fill("while ")
        self.dispatch(t.test)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _With(self, t):
        self.fill("with ")
        self.dispatch(t.context_expr)
        if t.optional_vars:
            self.write(" as ")
            self.dispatch(t.optional_vars)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    # expr
    def _Str(self, tree):
        # if from __future__ import unicode_literals is in effect,
        # then we want to output string literals using a 'b' prefix
        # and unicode literals with no prefix.
        if "unicode_literals" not in self.future_imports:
            self.write(repr(tree.s))
        elif isinstance(tree.s, str):
            self.write("b" + repr(tree.s))
        elif isinstance(tree.s, unicode):
            self.write(repr(tree.s).lstrip("u"))
        else:
            assert False, "shouldn't get here"

    def _Name(self, t):
        self.write(t.id)

    def _Repr(self, t):
        self.write("`")
        self.dispatch(t.value)
        self.write("`")

    def _Num(self, t):
        repr_n = repr(t.n)
        # Parenthesize negative numbers, to avoid turning (-1)**2 into -1**2.
        if repr_n.startswith("-"):
            self.write("(")
        # Substitute overflowing decimal literal for AST infinities.
        self.write(repr_n.replace("inf", INFSTR))
        if repr_n.startswith("-"):
            self.write(")")

    def _List(self, t):
        self.write("[")
        interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write("]")

    def _ListComp(self, t):
        self.write("[")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("]")

    def _GeneratorExp(self, t):
        self.write("(")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write(")")

    def _SetComp(self, t):
        self.write("{")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("}")

    def _DictComp(self, t):
        self.write("{")
        self.dispatch(t.key)
        self.write(": ")
        self.dispatch(t.value)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("}")

    def _comprehension(self, t):
        self.write(" for ")
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        for if_clause in t.ifs:
            self.write(" if ")
            self.dispatch(if_clause)

    def _IfExp(self, t):
        self.write("(")
        self.dispatch(t.body)
        self.write(" if ")
        self.dispatch(t.test)
        self.write(" else ")
        self.dispatch(t.orelse)
        self.write(")")

    def _Set(self, t):
        assert(t.elts) # should be at least one element
        self.write("{")
        interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write("}")

    def _Dict(self, t):
        self.write("{")
        def write_pair(pair):
            (k, v) = pair
            self.dispatch(k)
            self.write(": ")
            self.dispatch(v)
        interleave(lambda: self.write(", "), write_pair, zip(t.keys, t.values))
        self.write("}")

    def _Tuple(self, t):
        self.write("(")
        if len(t.elts) == 1:
            (elt,) = t.elts
            self.dispatch(elt)
            self.write(",")
        else:
            interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write(")")

    unop = {"Invert":"~", "Not": "not", "UAdd":"+", "USub":"-"}
    def _UnaryOp(self, t):
        self.write("(")
        self.write(self.unop[t.op.__class__.__name__])
        self.write(" ")
        # If we're applying unary minus to a number, parenthesize the number.
        # This is necessary: -2147483648 is different from -(2147483648) on
        # a 32-bit machine (the first is an int, the second a long), and
        # -7j is different from -(7j).  (The first has real part 0.0, the second
        # has real part -0.0.)
        if isinstance(t.op, ast.USub) and isinstance(t.operand, ast.Num):
            self.write("(")
            self.dispatch(t.operand)
            self.write(")")
        else:
            self.dispatch(t.operand)
        self.write(")")

    binop = { "Add":"+", "Sub":"-", "Mult":"*", "Div":"/", "Mod":"%",
                    "LShift":"<<", "RShift":">>", "BitOr":"|", "BitXor":"^", "BitAnd":"&",
                    "FloorDiv":"//", "Pow": "**"}
    def _BinOp(self, t):
        self.write("(")
        self.dispatch(t.left)
        self.write(" " + self.binop[t.op.__class__.__name__] + " ")
        self.dispatch(t.right)
        self.write(")")

    cmpops = {"Eq":"==", "NotEq":"!=", "Lt":"<", "LtE":"<=", "Gt":">", "GtE":">=",
                        "Is":"is", "IsNot":"is not", "In":"in", "NotIn":"not in"}
    def _Compare(self, t):
        self.write("(")
        self.dispatch(t.left)
        for o, e in zip(t.ops, t.comparators):
            self.write(" " + self.cmpops[o.__class__.__name__] + " ")
            self.dispatch(e)
        self.write(")")

    boolops = {ast.And: 'and', ast.Or: 'or'}
    def _BoolOp(self, t):
        self.write("(")
        s = " %s " % self.boolops[t.op.__class__]
        interleave(lambda: self.write(s), self.dispatch, t.values)
        self.write(")")

    def _Attribute(self,t):
        self.dispatch(t.value)
        # Special case: 3.__abs__() is a syntax error, so if t.value
        # is an integer literal then we need to either parenthesize
        # it or add an extra space to get 3 .__abs__().
        if isinstance(t.value, ast.Num) and isinstance(t.value.n, int):
            self.write(" ")
        self.write(".")
        self.write(t.attr)

    def _Call(self, t):
        self.dispatch(t.func)
        self.write("(")
        comma = False
        for e in t.args:
            if comma: self.write(", ")
            else: comma = True
            self.dispatch(e)
        for e in t.keywords:
            if comma: self.write(", ")
            else: comma = True
            self.dispatch(e)
        if t.starargs:
            if comma: self.write(", ")
            else: comma = True
            self.write("*")
            self.dispatch(t.starargs)
        if t.kwargs:
            if comma: self.write(", ")
            else: comma = True
            self.write("**")
            self.dispatch(t.kwargs)
        self.write(")")

    def _Subscript(self, t):
        self.dispatch(t.value)
        self.write("[")
        self.dispatch(t.slice)
        self.write("]")

    # slice
    def _Ellipsis(self, t):
        self.write("...")

    def _Index(self, t):
        self.dispatch(t.value)

    def _Slice(self, t):
        if t.lower:
            self.dispatch(t.lower)
        self.write(":")
        if t.upper:
            self.dispatch(t.upper)
        if t.step:
            self.write(":")
            self.dispatch(t.step)

    def _ExtSlice(self, t):
        interleave(lambda: self.write(', '), self.dispatch, t.dims)

    # others
    def _arguments(self, t):
        first = True
        # normal arguments
        defaults = [None] * (len(t.args) - len(t.defaults)) + t.defaults
        for a,d in zip(t.args, defaults):
            if first:first = False
            else: self.write(", ")
            self.dispatch(a),
            if d:
                self.write("=")
                self.dispatch(d)

        # varargs
        if t.vararg:
            if first:first = False
            else: self.write(", ")
            self.write("*")
            self.write(t.vararg)

        # kwargs
        if t.kwarg:
            if first:first = False
            else: self.write(", ")
            self.write("**"+t.kwarg)

    def _keyword(self, t):
        self.write(t.arg)
        self.write("=")
        self.dispatch(t.value)

    def _Lambda(self, t):
        self.write("(")
        self.write("lambda ")
        self.dispatch(t.args)
        self.write(": ")
        self.dispatch(t.body)
        self.write(")")

    def _alias(self, t):
        self.write(t.name)
        if t.asname:
            self.write(" as "+t.asname)

def roundtrip(filename, output=sys.stdout):
    with open(filename, "r") as pyfile:
        source = pyfile.read()
    tree = compile(source, filename, "exec", ast.PyCF_ONLY_AST)
    Unparser(tree, output)



def testdir(a):
    try:
        names = [n for n in os.listdir(a) if n.endswith('.py')]
    except OSError:
        sys.stderr.write("Directory not readable: %s" % a)
    else:
        for n in names:
            fullname = os.path.join(a, n)
            if os.path.isfile(fullname):
                output = cStringIO.StringIO()
                print 'Testing %s' % fullname
                try:
                    roundtrip(fullname, output)
                except Exception as e:
                    print '  Failed to compile, exception is %s' % repr(e)
            elif os.path.isdir(fullname):
                testdir(fullname)

def main(args):
    if args[0] == '--testdir':
        for a in args[1:]:
            testdir(a)
    else:
        for a in args:
            roundtrip(a)

if __name__=='__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/python

import sys, os
mydir = os.path.dirname(__file__)
sys.path += [mydir + "/.."]

import better_exchook
better_exchook.install()

import cparser
from pprint import pprint

def main():
	import types
	
	from glob import glob
	for f in glob(mydir + "/test_*.py"):
		c = compile(open(f).read(), os.path.basename(f), "exec")
		m = {}
		eval(c, m)

def newState(testcode, testfn = "test.c", withSystemMacros=True, withGlobalIncludeWrappers=False):
	state = cparser.State()
	if withSystemMacros: state.autoSetupSystemMacros()
	if withGlobalIncludeWrappers: state.autoSetupGlobalIncludeWrappers()
		
	origReadLocal = state.readLocalInclude
	def readLocalIncludeWrapper(fn):
		if fn == testfn:
			def reader():
				for c in testcode:
					yield c
			reader = reader()
			return reader, fn
		return origReadLocal(fn)
	state.readLocalInclude = readLocalIncludeWrapper
	
	return state

def parse(testcode, **kwargs):
	state = newState(testcode, **kwargs)
	cparser.parse("test.c", state)
	if state._errors:
		print "parsing errors:"
		pprint(state._errors)
		assert False, "there are parsing errors"
	return state

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = test_funcptrdecl
import sys
sys.path += [".."]
from pprint import pprint
from cparser import *
import test

testcode = """
	int16_t (*f)();
	int16_t (*g)(char a, void*);
	int (*h);
	
	// ISO/IEC 9899:TC3 : C99 standard
	int fx(void), *fip(), (*pfi)(); // example 1, page 120
	int (*apfi[3])(int *x, int *y); // example 2, page 120
	int (*fpfi(int (*)(long), int))(int, ...); // example 3, page 120
"""

state = test.parse(testcode)	

f = state.vars["f"]
g = state.vars["g"]

assert f.name == "f"
assert isinstance(f.type, CFuncPointerDecl)
assert f.type.type == CStdIntType("int16_t")
assert f.type.args == []

assert isinstance(g.type, CFuncPointerDecl)
gargs = g.type.args
assert isinstance(gargs, list)
assert len(gargs) == 2
assert isinstance(gargs[0], CFuncArgDecl)
assert gargs[0].name == "a"
assert gargs[0].type == CBuiltinType(("char",))
assert gargs[1].name is None
assert gargs[1].type == CBuiltinType(("void","*"))

h = state.vars["h"]
assert h.type == CPointerType(CBuiltinType(("int",)))

fx = state.funcs["fx"] # fx is a function `int (void)`
assert fx.type == CBuiltinType(("int",))
assert fx.args == []

fip = state.funcs["fip"] # fip is a function `int* (void)`
assert fip.type == CPointerType(CBuiltinType(("int",)))
assert fip.args == []

pfi = state.vars["pfi"] # pfi is a function-ptr to `int ()`
assert isinstance(pfi.type, CFuncPointerDecl)
assert pfi.type.type == CBuiltinType(("int",))
assert pfi.type.args == []

apfi = state.vars["apfi"] # apfi is an array of three function-ptrs `int (int*,int*)`
# ...

fpfi = state.funcs["fpfi"] # function which returns a func-ptr
# the function has the parameters `int(*)(long), int`
# the func-ptr func returns `int`
# the func-ptr func has the parameters `int, ...`

########NEW FILE########
__FILENAME__ = test_interpreter_helloworld
import sys
sys.path += [".."]
from pprint import pprint
import cparser, test

testcode = """
#include <stdio.h>

int main(int argc, char** argv) {
	printf("Hello %s\n", "world");
	printf("args: %i\n", argc);
	int i;
	for(i = 0; i < argc; ++i)
		printf("%s\n", argv[i]);
}
"""

state = test.parse(testcode, withGlobalIncludeWrappers=True)


import interpreter
interpreter = interpreter.Interpreter()
interpreter.register(state)
interpreter.registerFinalize()

def dump():
	for f in state.contentlist:
		if not isinstance(f, cparser.CFunc): continue
		if not f.body: continue
		
		print
		print "parsed content of " + str(f) + ":"
		for c in f.body.contentlist:
			print c
	
	print
	print "PyAST of main:"
	interpreter.dumpFunc("main")
	
#interpreter.runFunc("main", len(sys.argv), sys.argv + [None])

import os
# os.pipe() returns pipein,pipeout
pipes = os.pipe(), os.pipe() # for stdin/stdout+stderr

if os.fork() == 0: # child
	os.close(pipes[0][1])
	os.close(pipes[1][0])
	os.dup2(pipes[0][0], sys.stdin.fileno())
	os.dup2(pipes[1][1], sys.stdout.fileno())
	os.dup2(pipes[1][1], sys.stderr.fileno())
	
	interpreter.runFunc("main", 2, ["./test", "abc", None])
	
	sys.exit(0)
	
else: # parent
	os.close(pipes[0][0])
	os.close(pipes[1][1])
	child_stdout = os.fdopen(pipes[1][0])
	child_stdout = child_stdout.readlines()
	
expected_out = [
	"Hello world\n",
	"args: 2\n",
	"./test\n",
	"abc\n",
]

assert expected_out == child_stdout


########NEW FILE########
__FILENAME__ = test_ptrtoptrdecl
import sys
sys.path += [".."]
from pprint import pprint
import cparser, test

testcode = """
	int16_t (*motion_val[2])[2];
"""

state = test.parse(testcode)	

v = state.vars["motion_val"]

pprint((v, v.type))

########NEW FILE########
__FILENAME__ = test_simplevardecl
import sys
sys.path += [".."]
from pprint import pprint
import test

testcode = """
	int16_t a;
	int b = 42;
	void* c = &b;
	int* d = &b;
	char e, *f = "abc", g, **h = &f;
"""

state = test.parse(testcode)	

from cparser import *

for v in "abcdefgh":
	var = state.vars[v]
	globals()[v] = var
	assert var.name == v
	
assert a.type == CStdIntType("int16_t")
assert a.body is None
assert b.type == CBuiltinType(("int",))
assert b.body is not None
assert b.body.getConstValue(state) == 42
assert c.type == CBuiltinType(("void","*"))
#pprint(c.body) TODO: check <CStatement <COp '&'> <CStatement <CVarDecl 'b' ...
assert d.type == CPointerType(CBuiltinType(("int",)))
assert e.type == CBuiltinType(("char",))
assert f.type == CPointerType(e.type)
assert h.type == CPointerType(f.type)
assert f.body.getConstValue(state) == "abc"
#pprint(h.body)


########NEW FILE########
