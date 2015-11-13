__FILENAME__ = assname
# -*- coding: utf-8 -*-
"""
    assname
    ~~~~~~~

    Figures out the assigned name for an expression.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import dis


def assigned_name():
    frame = sys._getframe(2)
    code = frame.f_code.co_code[frame.f_lasti:]
    try:
        has_arg = ord(code[0]) >= dis.HAVE_ARGUMENT
        skip = 3 if has_arg else 1
        next_code = ord(code[skip])
        name_index = ord(code[skip + 1])
    except IndexError:
        return True
    if next_code in (dis.opmap['STORE_FAST'],
                     dis.opmap['STORE_GLOBAL'],
                     dis.opmap['STORE_NAME'],
                     dis.opmap['STORE_DEREF']):
        namelist = frame.f_code.co_names
        if next_code == dis.opmap['STORE_GLOBAL']:
            namelist = frame.f_code.co_names
        elif next_code == dis.opmap['STORE_DEREF']:
            namelist = frame.f_code.co_freevars
        return namelist[name_index]


if __name__ == '__main__':
    import collections
    def namedtuple(*names):
        rv = collections.namedtuple(assigned_name(), names)
        rv.__module__ = sys._getframe(1).f_globals['__name__']
        return rv

    Token = namedtuple('type', 'value', 'lineno')
    print Token, Token('int', 42, 1)

########NEW FILE########
__FILENAME__ = caseinsensitive
# -*- coding: utf-8 -*-
"""
    caseinsensitive
    ~~~~~~~~~~~~~~~

    An implementation of a case insensitive namespace.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from collections import MutableMapping


class Namespace(MutableMapping):

    def __init__(self):
        self.ns = {}

    def __getitem__(self, key):
        return self.ns[key.lower()]

    def __delitem__(self, key):
        del self.ns[key.lower()]

    def __setitem__(self, key, value):
        self.ns[key.lower()] = value

    def __len__(self):
        return len(self.ns)

    def __iter__(self):
        return iter(self.ns)


if __name__ == '__main__':
    ns = Namespace()
    exec '''if 1:
        foo = 42
        Bar = 23
        print (Foo, BAR)
    ''' in {}, ns

########NEW FILE########
__FILENAME__ = githubimporter
# -*- coding: utf-8 -*-
"""
    githubimporter
    ~~~~~~~~~~~~~~

    Imports code directly from github.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import imp
import urllib
import urlparse


class GithubImporter(object):
    url_template = 'https://raw.github.com/%(user)s/%(project)s/master/%(file)s'

    def __init__(self, path):
        url = urlparse.urlparse(path)
        if url.scheme != 'github':
            raise ImportError()
        self.user = url.netloc
        self.project = url.path.strip('/')
        if '/' in self.project:
            self.project, self.path = self.project.split('/', 1)
        else:
            self.path = ''
        self._cache = {}

    def get_source_and_filename(self, name):
        rv = self._cache.get(name)
        if rv is not None:
            return rv
        url_name = name.replace('.', '/')
        for filename in url_name + '.py', url_name + '/__init__.py':
            try:
                url = self.url_template % dict(
                    user=self.user,
                    project=self.project,
                    file=urlparse.urljoin(self.path, filename)
                )
                resp = urllib.urlopen(url)
                if resp.code == 404:
                    continue
                rv = resp.read(), 'github://%s/%s' % (
                    self.user,
                    filename
                )
                self._cache[name] = rv
                return rv
            except IOError:
                continue
        raise ImportError(name)

    def get_source(self, name):
        return self.get_source_and_filename(name)[0]

    def get_filename(self, name):
        return self.get_source_and_filename(name)[1]

    def find_module(self, name, path=None):
        try:
            self.get_source_and_filename(name)
        except ImportError:
            return None
        return self

    def load_module(self, name):
        source, filename = self.get_source_and_filename(name)
        sys.modules[name] = mod = imp.new_module(name)
        mod.__loader__ = self
        mod.__file__ = filename
        if filename.endswith('/__init__.py'):
            mod.__path__ = [filename.rsplit('/', 1)[0]]
        exec source in mod.__dict__
        return mod


def install_hook():
    sys.path_hooks.append(GithubImporter)


if __name__ == '__main__':
    install_hook()
    sys.path.append('github://mitsuhiko/markupsafe')

    import markupsafe
    print markupsafe.__file__
    print markupsafe.Markup.escape('<foo>')

########NEW FILE########
__FILENAME__ = implicitself
# -*- coding: utf-8 -*-
"""
    implicitself
    ~~~~~~~~~~~~

    Implements a bytecode hack and metaclass to make the self
    implicit in functions.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import opcode
from types import FunctionType, CodeType


HAVE_ARGUMENT = opcode.HAVE_ARGUMENT
LOAD_FAST = opcode.opmap['LOAD_FAST']
STORE_FAST = opcode.opmap['STORE_FAST']
LOAD_GLOBAL = opcode.opmap['LOAD_GLOBAL']
STORE_GLOBAL = opcode.opmap['STORE_GLOBAL']
LOAD_ATTR = opcode.opmap['LOAD_ATTR']
STORE_ATTR = opcode.opmap['STORE_ATTR']
LOAD_NAME = opcode.opmap['LOAD_NAME']
STORE_NAME = opcode.opmap['STORE_NAME']


def disassemble(code):
    code = map(ord, code)
    i = 0
    n = len(code)
    while i < n:
        op = code[i]
        i += 1
        if op >= HAVE_ARGUMENT:
            oparg = code[i] | code[i + 1] << 8
            i += 2
        else:
            oparg = None
        yield op, oparg


def implicit_self(function):
    code = function.func_code
    bytecode, varnames, names = inject_self(code)
    function.func_code = CodeType(code.co_argcount + 1, code.co_nlocals + 1,
        code.co_stacksize, code.co_flags, bytecode, code.co_consts, names,
        varnames, code.co_filename, code.co_name, code.co_firstlineno,
        code.co_lnotab, code.co_freevars, code.co_cellvars)


def inject_self(code):
    varnames = ('self',) + tuple(n for i, n in enumerate(code.co_varnames))
    names = tuple(n for i, n in enumerate(code.co_names))
    bytecode = []

    for op, arg in disassemble(code.co_code):
        if op in (LOAD_FAST, STORE_FAST):
            arg = varnames.index(code.co_varnames[arg])
        elif op in (LOAD_GLOBAL, STORE_GLOBAL, LOAD_NAME, STORE_NAME):
            if code.co_names[arg] == 'self':
                op = LOAD_FAST if op in (LOAD_GLOBAL, LOAD_NAME) \
                               else STORE_FAST
                arg = 0
            else:
                arg = names.index(code.co_names[arg])
        elif op in (LOAD_ATTR, STORE_ATTR):
            arg = names.index(code.co_names[arg])
        bytecode.append(chr(op))
        if op >= opcode.HAVE_ARGUMENT:
            bytecode.append(chr(arg & 0xff))
            bytecode.append(chr(arg >> 8))

    return ''.join(bytecode), varnames, names


class ImplicitSelfType(type):

    def __new__(cls, name, bases, d):
        for key, value in d.iteritems():
            if isinstance(value, FunctionType):
                implicit_self(value)
        return type.__new__(cls, name, bases, d)


class ImplicitSelf(object):
    __metaclass__ = ImplicitSelfType


if __name__ == '__main__':
    import hashlib

    class User(ImplicitSelf):

        def __init__(username, password):
            self.username = username
            self.set_password(password)

        def set_password(password):
            self.hash = hashlib.sha1(password).hexdigest()

        def check_password(password):
            return hashlib.sha1(password).hexdigest() == self.hash

    u = User('mitsuhiko', 'default')
    print u.__dict__

########NEW FILE########
__FILENAME__ = interfaces
# -*- coding: utf-8 -*-
"""
    interfaces
    ~~~~~~~~~~

    Implements a ``implements()`` function that does interfaces.  It's
    a very simple implementation and does not handle multiple calls
    to implements() properly.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys


class BaseType(type):
    pass


class Base(object):
    __metaclass__ = BaseType


class Interface(object):
    __slots__ = ()


def find_real_type(explicit, bases):
    if explicit is not None:
        return explicit
    for base in bases:
        if type(base) is not type:
            return type(base)
    return type


def iter_interface_methods(interface):
    for key, value in interface.__dict__.iteritems():
        if callable(value):
            yield key


def implemented(class_, interface, method):
    return getattr(class_, method).im_func \
        is not getattr(interface, method).im_func


def make_meta_factory(metacls, interfaces):
    def __metaclass__(name, bases, d):
        real_type = find_real_type(metacls, bases)
        bases += interfaces
        rv = real_type(name, bases, d)
        for interface in interfaces:
            for method in iter_interface_methods(interface):
                if not implemented(rv, interface, method):
                    raise NotImplementedError('Missing method %r on %r '
                        'from interface %r' % (method, rv.__name__,
                                               interface.__name__))
        return rv
    return __metaclass__


def implements(*interfaces):
    cls_scope = sys._getframe(1).f_locals
    metacls = cls_scope.get('__metaclass__')
    metafactory = make_meta_factory(metacls, interfaces)
    cls_scope['__metaclass__'] = metafactory


if __name__ == '__main__':
    class IRenderable(Interface):

        def render(self):
            raise NotImplementedError()


    class User(Base):
        implements(IRenderable)

        def render(self):
            return self.username

    print User.__bases__

########NEW FILE########
__FILENAME__ = magicmodule
# -*- coding: utf-8 -*-
"""
    magicmodule
    ~~~~~~~~~~~

    Implements lazy attributes for modules.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
from os.path import join, dirname
from types import ModuleType


class MagicModule(ModuleType):

    @property
    def git_hash(self):
        fn = join(dirname(__file__), '.git/refs/heads/master')
        with open(fn) as f:
            return f.read().strip()


old_mod = sys.modules[__name__]
sys.modules[__name__] = mod = MagicModule(__name__)
mod.__dict__.update(old_mod.__dict__)


if __name__ == '__main__':
    from magicmodule import git_hash
    print 'git hash:', git_hash

########NEW FILE########
__FILENAME__ = namefinder
# -*- coding: utf-8 -*-
"""
    namefinder
    ~~~~~~~~~~

    Finds all names for an object via the garbage collector graph.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import gc
import sys


def find_names(obj):
    frame = sys._getframe(1)
    while frame is not None:
        frame.f_locals
        frame = frame.f_back
    result = set()
    for referrer in gc.get_referrers(obj):
        if isinstance(referrer, dict):
            for k, v in referrer.iteritems():
                if v is obj:
                    result.add(k)
    return tuple(result)


if __name__ == '__main__':
    b = c = a = []
    print 'Name for %r: %s' % (a, find_names(a))

########NEW FILE########
__FILENAME__ = rvused
# -*- coding: utf-8 -*-
"""
    rvused
    ~~~~~~

    Is my return value used?  This function will tell you.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import dis


def return_value_used():
    frame = sys._getframe(2)
    code = frame.f_code.co_code[frame.f_lasti:]
    try:
        has_arg = ord(code[0]) >= dis.HAVE_ARGUMENT
        next_code = code[3 if has_arg else 1]
    except IndexError:
        return True
    return ord(next_code) != dis.opmap['POP_TOP']


if __name__ == '__main__':
    def foo():
        if return_value_used():
            print 'My return value is used'
        else:
            print 'My return value is discarded'
    foo()
    a = foo()

########NEW FILE########
__FILENAME__ = tbhacks
# -*- coding: utf-8 -*-
"""
    tbhacks
    ~~~~~~~

    Provides a function to rechain tracebacks.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import ctypes
from types import TracebackType


if hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
    _Py_ssize_t = ctypes.c_int64
else:
    _Py_ssize_t = ctypes.c_int


if hasattr(sys, 'getobjects'):
    class _PyObject(ctypes.Structure):
        pass
    _PyObject._fields_ = [
        ('_ob_next', ctypes.POINTER(_PyObject)),
        ('_ob_prev', ctypes.POINTER(_PyObject)),
        ('ob_refcnt', _Py_ssize_t),
        ('ob_type', ctypes.POINTER(_PyObject))
    ]
else:
    class _PyObject(ctypes.Structure):
        pass
    _PyObject._fields_ = [
        ('ob_refcnt', _Py_ssize_t),
        ('ob_type', ctypes.POINTER(_PyObject))
    ]


class _Traceback(_PyObject):
    pass
_Traceback._fields_ = [
    ('tb_next', ctypes.POINTER(_Traceback)),
    ('tb_frame', ctypes.POINTER(_PyObject)),
    ('tb_lasti', ctypes.c_int),
    ('tb_lineno', ctypes.c_int)
]


def tb_set_next(tb, next):
    if not (isinstance(tb, TracebackType) and
            (next is None or isinstance(next, TracebackType))):
        raise TypeError('tb_set_next arguments must be traceback objects')
    obj = _Traceback.from_address(id(tb))
    if tb.tb_next is not None:
        old = _Traceback.from_address(id(tb.tb_next))
        old.ob_refcnt -= 1
    if next is None:
        obj.tb_next = ctypes.POINTER(_Traceback)()
    else:
        next = _Traceback.from_address(id(next))
        next.ob_refcnt += 1
        obj.tb_next = ctypes.pointer(next)

########NEW FILE########
