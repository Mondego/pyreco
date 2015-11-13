__FILENAME__ = test
from zodiac import monkeypatch
monkeypatch('test_orig', 'test_patch')

import test_orig as mod

assert mod.CONSTANT == 1

assert mod.req1() == 'old'

assert mod.Foo().val == 'new'
assert mod.Foo().req2() == 'old'
assert mod.Foo().req3() == 'old'

assert mod.new1() == 'old'
assert mod.new2() == 'new'

assert mod.Inheritor1().val == 'new'
assert mod.Inheritor2().val == 'new'
assert mod.Inheritor3().val == 'new'

assert mod.Slots().prop.val == 'new'

assert mod.user1() == 'new'
assert mod.user2() == 'new'

print('success!')

########NEW FILE########
__FILENAME__ = test_orig
import sys

CONSTANT = 1

#existing
def req1():
	return 'old'

def req2():
	def ret():
		return 'old'
	return ret()

class Requirement(object):
	def __init__(self):
		self.val = 'old'

class Foo(object):
	def __init__(self):
		self.val = 'old'
	
#inheritance
class Inheritor1(Foo):
	def __init__(self):
		super(Inheritor1, self).__init__()

class Inheritor2(Foo):
	def __init__(self):
		Foo.__init__(self)

if sys.version_info[0] >= 3:
	class Inheritor3(Foo):
		def __init__(self):
			super().__init__()
else:
	Inheritor3 = Inheritor2

class Slots:
	__slots__ = ('prop',)
	def __init__(self):
		self.prop = Foo()

#methods
def user1():
	return Foo().val

#closure
def user2():
	def ret():
		return Foo().val
	return ret()

########NEW FILE########
__FILENAME__ = test_patch
import test_orig as _real

class Foo(_real.Foo):

	def __init__(self):
		self.val = 'new'

	def req2(self):
		return _real.req1()

	def req3(self):
		return _real.Requirement().val

def new1():
	return _real.req1()

def new2():
	return Foo().val


########NEW FILE########
__FILENAME__ = zodiac
import sys
try:
	import builtins
except ImportError:
	builtins = __builtins__
import types
import imp

_get_default = object()
def _get(obj, name, default=_get_default):
	if isinstance(obj, dict):
		if default is _get_default:
			return obj[name]
		else:
			return obj.get(name, default)
	else:
		if default is _get_default:
			return getattr(obj, name)
		else:
			return getattr(obj, name, default)

def _set(obj, name, val):
	if isinstance(obj, dict):
		obj[name] = val
	else:
		return setattr(obj, name, val)

def _create_closure_cell(obj):
	def ret(): obj
	return ret.__closure__[0]

def rebase_function(f, target, new_name=None, ns=None):
	if not new_name:
		new_name = f.__name__
	ns = ns or dict()

	if f.__closure__:
		new_closure = []
		for c in f.__closure__:
			name = _get(c.cell_contents, '__name__', False)
			if name and name in ns:
				new_closure.append(_create_closure_cell(ns[name]))
			else:
				new_closure.append(c)
		new_closure = tuple(new_closure)
	else:
		new_closure = f.__closure__

	new_f = types.FunctionType(
		f.__code__,
		ns,
		new_name,
		f.__defaults__,
		new_closure
	)
	
	_set(target, new_name, new_f)

def rebase_class(cls, target, new_name=None, ns=None):
	if not new_name:
		new_name = cls.__name__
	ns = ns or dict()

	new_bases = []
	for base in cls.__bases__:
		new_base = _get(target, base.__name__, False)
		if new_base and isinstance(new_base, type):
			new_bases.append(new_base)
		else:
			new_bases.append(base)
	new_bases = tuple(new_bases)

	new_cls = type(new_name, new_bases, dict())
	ns[new_name] = new_cls
	new_cls._my_class = new_cls

	for name, item in cls.__dict__.items():
		if name in ('__dict__', '__slots__', '__bases__', '__weakref__', '__name__', '__module__', '__doc__'): continue
		if isinstance(item, types.MemberDescriptorType): continue
		rebase(item, new_cls, name, ns)

	_set(target, new_name, new_cls)

def rebase(obj, target, new_name=None, ns=None):

	if isinstance(obj, type):
		rebase_class(obj, target, new_name, ns)
	elif isinstance(obj, types.FunctionType):
		rebase_function(obj, target, new_name, ns)
	else:
		_set(target, new_name, obj) 

def build_patch(original_module, patch_module):
	original = __import__(original_module)
	patch = __import__(patch_module)

	mod = imp.new_module(patch_module)
	mod.__builtins__ = builtins

	for name in patch.__dict__:
		if name.startswith('__'): continue
		setattr(mod, name, getattr(patch, name))
	
	for name in original.__dict__:
		if name.startswith('__') or name in patch.__dict__:
			continue

		val = getattr(original, name)
		rebase(val, mod, name, mod.__dict__)
		
	return mod

hidden_modules = {}

def replace_module(name, replacement):
	real = sys.modules.get(name, False)
	if real:
		hidden_modules[name] = real

	sys.modules[name] = replacement

def restore_module(name):
	sys.modules[name] = hidden_modules[name]
	del hidden_modules[name]

def monkeypatch(dest, source):
	patch = build_patch(dest, source)
	replace_module(dest, patch)


########NEW FILE########
