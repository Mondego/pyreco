__FILENAME__ = execfile
from __future__ import with_statement
import sys
from sandbox import Sandbox, SandboxConfig
from optparse import OptionParser

def parseOptions():

    parser = OptionParser(usage="%prog [options] -- script.py [script options] [arg1 arg2 ...]")
    SandboxConfig.createOptparseOptions(parser)
    options, argv = parser.parse_args()
    if not argv:
        parser.print_help()
        exit(1)

    config = SandboxConfig.fromOptparseOptions(options)
    return config, argv

def main():
    config, argv = parseOptions()
    config.allowModule('sys', 'argv')

    with open(argv[0], "rb") as fp:
        content = fp.read()

    sys.argv = list(argv)
    sandbox = Sandbox(config)
    sandbox.execute(content)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = interpreter
from __future__ import with_statement
from code import InteractiveConsole
from sandbox import Sandbox, SandboxConfig, HAVE_PYPY
try:
    import readline
except ImportError:
    pass
from optparse import OptionParser
from sandbox.version import VERSION
import sys
from sys import version_info

def getEncoding():
    encoding = sys.stdin.encoding
    if encoding:
        return encoding
    # sys.stdin.encoding is None if stdin is not a tty

    # Emulate PYTHONIOENCODING on Python < 2.6
    import os
    env = os.getenv('PYTHONIOENCODING')
    if env:
        return env.split(':',1)[0]

    # Fallback to locales
    import locale
    return locale.getpreferredencoding()

ENCODING = getEncoding()

class SandboxConsole(InteractiveConsole):
    # Backport Python 2.6 fix for input encoding
    def raw_input(self, prompt):
        line = InteractiveConsole.raw_input(self, prompt)
        if not isinstance(line, unicode):
            line = line.decode(ENCODING)
        return line

class SandboxedInterpeter:
    def __init__(self):
        self.sandbox_locals = None
        self.options = self.parseOptions()
        self.config = self.createConfig()
        self.stdout = sys.stdout

    def parseOptions(self):
        parser = OptionParser(usage="%prog [options]")
        SandboxConfig.createOptparseOptions(parser, default_timeout=None)
        parser.add_option("--debug",
            help="Debug mode",
            action="store_true", default=False)
        parser.add_option("--verbose", "-v",
            help="Verbose mode",
            action="store_true", default=False)
        parser.add_option("--quiet", "-q",
            help="Quiet mode",
            action="store_true", default=False)
        options, argv = parser.parse_args()
        if argv:
            parser.print_help()
            exit(1)
        if options.quiet:
            options.verbose = False
        return options

    def createConfig(self):
        config = SandboxConfig.fromOptparseOptions(self.options)
        config.enable('traceback')
        config.enable('stdin')
        config.enable('stdout')
        config.enable('stderr')
        config.enable('exit')
        config.enable('site')
        config.enable('encodings')
        config._builtins_whitelist.add('compile')
        config.allowModuleSourceCode('code')
        config.allowModule('sys',
            'api_version', 'version', 'hexversion')
        config.allowSafeModule('sys', 'version_info')
        if HAVE_PYPY:
            config.enable('unicodedata')
            config.allowModule('os', 'write', 'waitpid')
            config.allowSafeModule('pyrepl', 'input')
            config.allowModule('pyrepl.keymap', 'compile_keymap', 'parse_keys')
        if self.options.debug:
            config.allowModule('sys', '_getframe')
            config.allowSafeModule('_sandbox', '_test_crash')
            config.allowModuleSourceCode('sandbox')
        if not config.cpython_restricted:
            config.allowPath(__file__)
        return config

    def dumpConfig(self):
        if self.options.debug:
            from pprint import pprint
            print "Sandbox config:"
            pprint(self.config.__dict__)
        else:
            features = ', '.join(sorted(self.config.features))
            print "Enabled features: %s" % features
            if self.config.cpython_restricted:
                print "CPython restricted mode enabled."
            if self.config.use_subprocess:
                text = "Run untrusted code in a subprocess"
                if self.options.debug:
                    from os import getpid
                    text += ": pid=%s" % getpid()
                print(text)
        if 'help' not in self.config.features:
            print "(use --features=help to enable the help function)"
        print

    def displayhook(self, result):
        if result is None:
            return
        self.sandbox_locals['_'] = result
        text = repr(result)
        if not self.options.quiet:
            print(text)
        else:
            self.stdout.write(text)

    def interact(self):
        console = SandboxConsole()
        self.sandbox_locals = console.locals
        if not self.options.quiet:
            banner = "Try to break the sandbox!"
        else:
            banner = ''
        console.interact(banner)

    def main(self):
        if not self.options.quiet:
            print("pysandbox %s" % VERSION)
            self.dumpConfig()
        if 'help' in self.config.features:
            # Import pydoc here because it uses a lot of modules
            # blocked by the sandbox
            import pydoc
        if self.config.cpython_restricted:
            # Import is blocked in restricted mode, so preload modules
            import codecs
            import encodings
            import encodings.utf_8
            import encodings.utf_16_be
            if version_info >= (2, 6):
                import encodings.utf_32_be
            if sys.stdout.encoding:
                codecs.lookup(sys.stdout.encoding)
            codecs.lookup(ENCODING)
        sys.ps1 = '\nsandbox>>> '
        sys.ps2 = '.......... '
        sys.displayhook = self.displayhook
        sandbox = Sandbox(self.config)
        sandbox.call(self.interact)

if __name__ == "__main__":
    SandboxedInterpeter().main()

########NEW FILE########
__FILENAME__ = attributes
from __future__ import absolute_import
from types import FunctionType, FrameType, GeneratorType
from sys import version_info
from sandbox import Protection
try:
    from sys import _clear_type_cache
except ImportError:
    # Python < 2.6 has no type cache, so we don't have to clear it
    def _clear_type_cache():
        pass

from .cpython import dictionary_of
from .restorable_dict import RestorableDict

builtin_function = type(len)

class HideAttributes(Protection):
    """
    Hide unsafe frame attributes from the Python space
    """
    def __init__(self):
        self.dict_dict = RestorableDict(dictionary_of(dict))
        self.function_dict = RestorableDict(dictionary_of(FunctionType))
        self.frame_dict = RestorableDict(dictionary_of(FrameType))
        self.type_dict = RestorableDict(dictionary_of(type))
        self.builtin_func_dict = RestorableDict(dictionary_of(builtin_function))
        self.generator_dict = RestorableDict(dictionary_of(GeneratorType))

    def enable(self, sandbox):
        if not sandbox.config.cpython_restricted:
            # Deny access to func.func_code to avoid an attacker to modify a
            # trusted function: replace the code of the function
            hide_func_code = True
        else:
            # CPython restricted mode already denies read and write access to
            # function attributes
            hide_func_code = False

        # Blacklist all dict methods able to modify a dict, to protect
        # ReadOnlyBuiltins
        for name in (
        '__init__', 'clear', '__delitem__', 'pop', 'popitem',
        'setdefault', '__setitem__', 'update'):
            del self.dict_dict[name]
        if version_info < (3, 0):
            # pysandbox stores trusted objects in closures: deny access to
            # closures to not leak these secrets
            del self.function_dict['func_closure']
            del self.function_dict['func_globals']
            if hide_func_code:
                del self.function_dict['func_code']
            del self.function_dict['func_defaults']
        if version_info >= (2, 6):
            del self.function_dict['__closure__']
            del self.function_dict['__globals__']
            if hide_func_code:
                del self.function_dict['__code__']
            del self.function_dict['__defaults__']
        del self.frame_dict['f_locals']

        # Hiding type.__bases__ crashs CPython 2.5 because of a infinite loop
        # in PyErr_ExceptionMatches(): it calls abstract_get_bases() but
        # abstract_get_bases() fails and call PyErr_ExceptionMatches() ...
        if version_info >= (2, 6):
            # Setting __bases__ crash Python < 3.3a2
            # http://bugs.python.org/issue14199
            del self.type_dict['__bases__']

        # object.__subclasses__ leaks the file type in Python 2
        # and (indirectly) the FileIO file in Python 3
        del self.type_dict['__subclasses__']
        del self.builtin_func_dict['__self__']
        _clear_type_cache()

    def disable(self, sandbox):
        self.dict_dict.restore()
        self.function_dict.restore()
        self.frame_dict.restore()
        self.type_dict.restore()
        self.builtin_func_dict.restore()
        self.generator_dict.restore()
        # Python 2.6+ uses a method cache: clear it to avoid errors
        _clear_type_cache()


########NEW FILE########
__FILENAME__ = blacklist_proxy
"""
Proxies using a blacklist policy.

Use a blacklist instead of a whitelist policy because __builtins__ HAVE TO
inherit from dict: Python/ceval.c uses PyDict_SetItem() and an inlined version
of PyDict_GetItem().
"""
from __future__ import absolute_import
from .proxy import readOnlyError

def createReadOnlyBuiltins(builtins):
    # If you update this class, update also HideAttributes.enable()
    class ReadOnlyBuiltins(dict):
        """
        Type used for a read only version of the __builtins__ dictionary.

        Don't proxy __getattr__ because we suppose that __builtins__ only
        contains safe functions (not mutable objects).
        """
        __slots__ = tuple()

        def clear(self):
            readOnlyError()

        def __delitem__(self, key):
            readOnlyError()

        def pop(self, key, default=None):
            readOnlyError()

        def popitem(self):
            readOnlyError()

        def setdefault(self, key, value):
            readOnlyError()

        def __setitem__(self, key, value):
            readOnlyError()

        def update(self, dict, **kw):
            readOnlyError()

    safe = ReadOnlyBuiltins(builtins)
    def __init__(*args, **kw):
        readOnlyError()
    ReadOnlyBuiltins.__init__ = __init__
    return safe


########NEW FILE########
__FILENAME__ = builtins
from __future__ import absolute_import
import __builtin__ as BUILTINS_MODULE
from types import FrameType
from sys import version_info
import sys

from sandbox import SandboxError, HAVE_CSANDBOX
from .safe_open import _safe_open
from .safe_import import _safe_import
from .restorable_dict import RestorableDict
from .proxy import createReadOnlyObject
from .blacklist_proxy import createReadOnlyBuiltins
if HAVE_CSANDBOX:
    from _sandbox import set_frame_builtins, set_interp_builtins

class CleanupBuiltins:
    """
    Deny unsafe builtins functions.
    """
    def __init__(self):
        self.get_frame_builtins = FrameType.f_builtins.__get__
        self.builtin_dict = RestorableDict(BUILTINS_MODULE.__dict__)

    def enable(self, sandbox):
        config = sandbox.config

        # Remove all symbols not in the whitelist
        whitelist = config.builtins_whitelist
        keys = set(self.builtin_dict.dict.iterkeys())
        for key in keys - whitelist:
            del self.builtin_dict[key]

        # Get frame builtins
        self.frame = sandbox.frame
        self.builtins_dict = self.get_frame_builtins(self.frame)

        # Get module list
        self.modules_dict = []
        for name, module in sys.modules.iteritems():
            if module is None:
                continue
            if '__builtins__' not in module.__dict__:
                # builtin modules have no __dict__ attribute
                continue
            if name == "__main__":
                 # __main__ is handled differently, see below
                continue
            self.modules_dict.append(module.__dict__)
        self.main_module = sys.modules['__main__']

        # Replace open and file functions
        if not config.cpython_restricted:
            open_whitelist = config.open_whitelist
            safe_open = _safe_open(open_whitelist)
            self.builtin_dict['open'] = safe_open
            if version_info < (3, 0):
                self.builtin_dict['file'] = safe_open

        # Replace __import__ function
        import_whitelist = config.import_whitelist
        self.builtin_dict['__import__'] = _safe_import(__import__, import_whitelist)

        # Replace exit function
        if 'exit' not in config.features:
            def safe_exit(code=0):
                raise SandboxError("exit() function blocked by the sandbox")
            self.builtin_dict['exit'] = safe_exit

        # Replace help function
        help_func = self.builtin_dict.dict.get('help')
        if help_func:
            if 'help' in config.features:
                self.builtin_dict['help'] = createReadOnlyObject(help_func)
            else:
                del self.builtin_dict['help']

        # Make builtins read only (enable restricted mode)
        safe_builtins = createReadOnlyBuiltins(self.builtin_dict.dict)
        if HAVE_CSANDBOX:
            set_frame_builtins(self.frame, safe_builtins)
            if not config.cpython_restricted:
                set_interp_builtins(safe_builtins)
        for module_dict in self.modules_dict:
            module_dict['__builtins__'] = safe_builtins
        self.main_module.__dict__['__builtins__'] = safe_builtins

    def disable(self, sandbox):
        # Restore builtin functions
        self.builtin_dict.restore()

        # Restore modifiable builtins
        if HAVE_CSANDBOX:
            set_frame_builtins(self.frame, self.builtins_dict)
            if not sandbox.config.cpython_restricted:
                set_interp_builtins(self.builtins_dict)
        for module_dict in self.modules_dict:
            module_dict['__builtins__'] = self.builtins_dict
        self.main_module.__dict__['__builtins__'] = BUILTINS_MODULE
        self.frame = None
        self.builtins_dict = None
        self.main_module = None
        self.modules_dict = None


########NEW FILE########
__FILENAME__ = clear_import
from sandbox import Protection
import sys
from os.path import dirname
import os

class ClearImport(Protection):
    def __init__(self):
        # Only allow the standard library
        self.safe_path = (dirname(os.__file__),)

    def enable(self, sandbox):
        #self.modules = dict(sys.modules)
        self.path_importer_cache = dict(sys.path_importer_cache)
        self.path = list(sys.path)
        self.meta_path = list(sys.meta_path)
        self.path_hooks = list(sys.path_hooks)

        #sys.modules.clear()
        sys.path_importer_cache.clear()
        del sys.path[:]
        sys.path.extend(sandbox.config.sys_path)
        del sys.meta_path[:]
        del sys.path_hooks[:]

    def disable(self, sandbox):
        #sys.modules.clear()
        #sys.modules.update(self.modules)
        sys.path_importer_cache.clear()
        sys.path_importer_cache.update(self.path_importer_cache)

        del sys.path[:]
        sys.path.extend(self.path)
        del sys.meta_path[:]
        sys.meta_path.extend(self.meta_path)
        del sys.path_hooks[:]
        sys.path_hooks.extend(self.path_hooks)

        #self.modules = None
        self.path = None
        self.meta_path = None



########NEW FILE########
__FILENAME__ = code
from __future__ import absolute_import
from sandbox import Protection
from _sandbox import disable_code_new, restore_code_new

class DisableCode(Protection):
    def enable(self, sandbox):
        disable_code_new()

    def disable(self, sandbox):
        restore_code_new()


########NEW FILE########
__FILENAME__ = config
from __future__ import absolute_import
from os.path import realpath, sep as path_sep, dirname, join as path_join, exists, isdir
from sys import version_info
#import imp
import sys
from sandbox import (DEFAULT_TIMEOUT,
    HAVE_CSANDBOX, HAVE_CPYTHON_RESTRICTED, HAVE_PYPY)
try:
    # check if memory limit is supported
    import resource
except ImportError:
    resource = None

_UNSET = object()

# The os module is part of the Python standard library
# and it is implemented in Python
import os
PYTHON_STDLIB_DIR = dirname(os.__file__)
del os

def findLicenseFile():
    import os
    # Adapted from setcopyright() from site.py
    here = PYTHON_STDLIB_DIR
    for filename in ("LICENSE.txt", "LICENSE"):
        for directory in (path_join(here, os.pardir), here, os.curdir):
            fullname = path_join(directory, filename)
            if exists(fullname):
                return fullname
    return None

#def getModulePath(name):
#    """
#    Get the path of a module, as "import module; module.__file__".
#    """
#    parts = name.split('.')
#
#    search_path = None
#    for index, part in enumerate(parts[:-1]):
#        fileobj, pathname, description = imp.find_module(part, search_path)
#        module = imp.load_module(part, fileobj, pathname, description)
#        del sys.modules[part]
#        try:
#            search_path = module.__path__
#        except AttributeError:
#            raise ImportError("%s is not a package" % '.'.join(parts[:index+1]))
#        module = None
#
#    part = parts[-1]
#    fileobj, pathname, description = imp.find_module(part, search_path)
#    if fileobj is not None:
#        fileobj.close()
#    if part == pathname:
#        # builtin module
#        return None
#    if not pathname:
#        # special module?
#        return None
#    return pathname
#
def getModulePath(name):
    old_modules = sys.modules.copy()
    try:
        module = __import__(name)
        return getattr(module, '__file__', None)
    finally:
        sys.modules.clear()
        sys.modules.update(old_modules)

class SandboxConfig(object):
    def __init__(self, *features, **kw):
        """
        Usage:
         - SandboxConfig('stdout', 'stderr')
         - SandboxConfig('interpreter', cpython_restricted=True)

        Options:

         - use_subprocess=True (bool): if True, execute() run the code in
           a subprocess
         - cpython_restricted=False (bool): if True, use CPython restricted
           mode instead of the _sandbox module
        """
        self.recusion_limit = 50
        self._use_subprocess = kw.pop('use_subprocess', True)
        if self._use_subprocess:
            self._timeout = DEFAULT_TIMEOUT
            if resource is not None:
                self._max_memory = 250 * 1024 * 1024
            else:
                self._max_memory = None
            # size in bytes of all input objects serialized by pickle
            self._max_input_size = 64 * 1024
            # size in bytes of the result serialized by pickle
            self._max_output_size = 64 * 1024
        else:
            self._timeout = None
            self._max_memory = None
            self._max_input_size = None
            self._max_output_size = None

        # open() whitelist: see safe_open()
        self._open_whitelist = set()

        # import whitelist dict: name (str) => [attributes, safe_attributes]
        # where attributes and safe_attributes are set of names (str)
        self._import_whitelist = {}

        # list of enabled features
        self._features = set()

        try:
            self._cpython_restricted = kw.pop('cpython_restricted')
        except KeyError:
            if HAVE_CSANDBOX:
                # use _sandbox
                self._cpython_restricted = False
            elif HAVE_PYPY:
                self._cpython_restricted = False
            else:
                # _sandbox is missing: use restricted mode
                self._cpython_restricted = True
        else:
            if not self._cpython_restricted \
            and (not HAVE_CSANDBOX and not HAVE_PYPY):
                raise ValueError(
                    "unsafe configuration: the _sanbox module is missing "
                    "and the CPython restricted mode is disabled")

        if self._cpython_restricted and not HAVE_CPYTHON_RESTRICTED:
            raise ValueError(
                "Your Python version doesn't support the restricted mode")

        self._builtins_whitelist = set((
            # exceptions
            'ArithmeticError', 'AssertionError', 'AttributeError',
            'BufferError', 'BytesWarning', 'DeprecationWarning', 'EOFError',
            'EnvironmentError', 'Exception', 'FloatingPointError',
            'FutureWarning', 'GeneratorExit', 'IOError', 'ImportError',
            'ImportWarning', 'IndentationError', 'IndexError', 'KeyError',
            'LookupError', 'MemoryError', 'NameError', 'NotImplemented',
            'NotImplementedError', 'OSError', 'OverflowError',
            'PendingDeprecationWarning', 'ReferenceError', 'RuntimeError',
            'RuntimeWarning', 'StandardError', 'StopIteration', 'SyntaxError',
            'SyntaxWarning', 'SystemError', 'TabError', 'TypeError',
            'UnboundLocalError', 'UnicodeDecodeError', 'UnicodeEncodeError',
            'UnicodeError', 'UnicodeTranslateError', 'UnicodeWarning',
            'UserWarning', 'ValueError', 'Warning', 'ZeroDivisionError',
            # blocked: BaseException - KeyboardInterrupt - SystemExit (enabled
            #          by exit feature), Ellipsis,

            # constants
            'False', 'None', 'True',
            '__doc__', '__name__', '__package__', 'copyright', 'license', 'credits',
            # blocked: __debug__

            # types
            'basestring', 'bytearray', 'bytes', 'complex', 'dict', 'file',
            'float', 'frozenset', 'int', 'list', 'long', 'object', 'set',
            'str', 'tuple', 'unicode',
            # note: file is replaced by safe_open()

            # functions
            '__import__', 'abs', 'all', 'any', 'apply', 'bin', 'bool',
            'buffer', 'callable', 'chr', 'classmethod', 'cmp',
            'coerce', 'compile', 'delattr', 'dir', 'divmod', 'enumerate', 'eval', 'exit',
            'filter', 'format', 'getattr', 'globals', 'hasattr', 'hash', 'hex',
            'id', 'isinstance', 'issubclass', 'iter', 'len', 'locals',
            'map', 'max', 'min', 'next', 'oct', 'open', 'ord', 'pow', 'print',
            'property', 'range', 'reduce', 'repr',
            'reversed', 'round', 'setattr', 'slice', 'sorted', 'staticmethod',
            'sum', 'super', 'type', 'unichr', 'vars', 'xrange', 'zip',
            # blocked: execfile, input
            #          and raw_input (enabled by stdin feature), intern,
            #          help (from site module, enabled by help feature), quit
            #          (enabled by exit feature), reload
            # note: reload is useless because we don't have access to real
            #       module objects
            # note: exit is replaced by safe_exit() if exit feature is disabled
            # note: open is replaced by safe_open()
        ))
        if HAVE_PYPY:
            self._builtins_whitelist |= set((
                # functions
                'intern',
            ))
        if version_info >= (3, 0):
            self._builtins_whitelist |= set((
                # functions
                '__build_class__', 'ascii', 'exec',
            ))

        self.sys_path = (PYTHON_STDLIB_DIR,)

        for feature in features:
            self.enable(feature)

        if kw:
            raise TypeError("unexpected keywords: %s" % ', '.join(kw.keys()))

    def has_feature(self, feature):
        return (feature in self._features)

    @property
    def features(self):
        return self._features.copy()

    @property
    def use_subprocess(self):
        return self._use_subprocess

    def _get_timeout(self):
        return self._timeout
    def _set_timeout(self, timeout):
        if timeout:
            if not self._use_subprocess:
                raise NotImplementedError("Timeout requires the subprocess mode")
            self._timeout = timeout
        else:
            self._timeout = None
    timeout = property(_get_timeout, _set_timeout)

    def _get_max_memory(self):
        return self._max_memory
    def _set_max_memory(self, mb):
        if not self._use_subprocess:
            raise NotImplementedError("Max Memory requires the subprocess mode")
        self._max_memory = mb * 1024 * 1024
    max_memory = property(_get_max_memory, _set_max_memory)

    @property
    def max_input_size(self):
        return self._max_input_size

    @property
    def max_output_size(self):
        return self._max_output_size

    @property
    def import_whitelist(self):
        return dict((name, (tuple(value[0]), tuple(value[1])))
            for name, value in self._import_whitelist.iteritems())

    @property
    def open_whitelist(self):
        return self._open_whitelist.copy()

    @property
    def cpython_restricted(self):
        return self._cpython_restricted

    @property
    def builtins_whitelist(self):
        return self._builtins_whitelist.copy()

    def enable(self, feature):
        # If you add a new feature, update the README documentation
        if feature in self._features:
            return
        self._features.add(feature)

        if feature == 'regex':
            self.allowModule('re',
                'findall', 'split',
                'sub', 'subn', 'escape', 'I', 'IGNORECASE', 'L', 'LOCALE', 'M',
                'MULTILINE', 'S', 'DOTALL', 'X', 'VERBOSE',
            )
            self.allowSafeModule('re',
                'compile', 'finditer', 'match', 'search', '_subx', 'error')
            self.allowSafeModule('sre_parse', 'parse')
        elif feature == 'exit':
            self.allowModule('sys', 'exit')
            self._builtins_whitelist |= set((
                'BaseException',
                'KeyboardInterrupt',
                'SystemExit',
                # quit builtin is added by the site module
                'quit'))
        elif feature == 'traceback':
            # change allowModule() behaviour
            pass
        elif feature in ('stdout', 'stderr'):
            self.allowModule('sys', feature)
            # ProtectStdio.enable() use also these features
        elif feature == 'stdin':
            self.allowModule('sys', 'stdin')
            self._builtins_whitelist.add('input')
            self._builtins_whitelist.add('raw_input')
        elif feature == 'site':
            if 'traceback' in self._features \
            and (not self._cpython_restricted):
                license_filename = findLicenseFile()
                if license_filename:
                    self.allowPath(license_filename)
            self.allowModuleSourceCode('site')
        elif feature == 'help':
            self.enable('regex')
            self.allowModule('pydoc', 'help')
            self._builtins_whitelist.add('help')
        elif feature == 'future':
            self.allowModule('__future__',
                'all_feature_names',
                'absolute_import', 'braces', 'division', 'generators',
                'nested_scopes', 'print_function', 'unicode_literals',
                'with_statement')
        elif feature == 'unicodedata':
            self.allowModule('unicodedata',
                # C API is used for u'\N{ATOM SYMBOL}': Python have to be
                # allowed to import it because it cannot be used in the sandbox
                'ucnhash_CAPI',
                # other functions
                'bidirectional', 'category', 'combining', 'decimal',
                'decomposition', 'digit', 'east_asian_width', 'lookup',
                'mirrored', 'name', 'normalize', 'numeric',
                'unidata_version')
        elif feature == 'time':
            self.allowModule('time',
                'accept2dyear', 'altzone', 'asctime', 'clock', 'ctime',
                'daylight', 'mktime', 'strftime', 'time',
                'timezone', 'tzname')
            self.allowSafeModule('time',
               'gmtime', 'localtime', 'struct_time')
            # blocked: sleep(), strptime(), tzset()
        elif feature == 'datetime':
            self.allowModule('datetime',
                'MAXYEAR', 'MINYEAR')
            self.allowSafeModule('datetime',
                'date', 'datetime', 'time', 'timedelta', 'tzinfo')
        elif feature == 'math':
            self.allowModule('math',
                'acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh',
                'ceil', 'copysign', 'cos', 'cosh', 'degrees', 'e', 'exp',
                'fabs', 'factorial', 'floor', 'fmod', 'frexp', 'fsum', 'hypot',
                'isinf', 'isnan', 'ldexp', 'log', 'log10', 'log1p', 'modf',
                'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh',
                'trunc')
        elif feature == 'itertools':
            self.allowSafeModule('itertools',
                'chain', 'combinations', 'count', 'cycle', 'dropwhile',
                'groupby', 'ifilter', 'ifilterfalse', 'imap', 'islice', 'izip',
                'izip_longest', 'permutations', 'product', 'repeat', 'starmap',
                'takewhile', 'tee')
            # TODO, python 2.7/3.2: combinations_with_replacement, compress
        elif feature == 'random':
            self.enable('math')
            self.allowModule('__future__', 'division')
            self.allowModule('warnings', 'warn')
            self.allowModule('types', 'MethodType', 'BuiltinMethodType')
            self.allowModule('os', 'urandom')
            self.allowModule('binascii', 'hexlify')
            self.allowSafeModule('_random', 'Random')
            self.allowModule('random',
                # variate
                'betavariate', 'expovariate', 'gammavariate', 'lognormvariate',
                'normalvariate', 'paretovariate', 'vonmisesvariate',
                'weibullvariate',
                # others
                'choice', 'gauss', 'getrandbits', 'randint', 'random',
                'randrange', 'sample', 'shuffle', 'triangular', 'uniform')
                # blocked: getstate, jumpahead, seed, setstate
            self.enable('hashlib')
        elif feature == 'hashlib':
            self.allowSafeModule('hashlib',
                'md5',
                'sha1',
                'sha224',
                'sha256',
                'sha384',
                'sha512')
            self.allowSafeModule('_hashlib',
                'openssl_md5',
                'openssl_sha1',
                'openssl_sha224',
                'openssl_sha256',
                'openssl_sha384',
                'openssl_sha512')
        elif feature == 'codecs':
            self.allowModule('codecs',
                'lookup', 'CodecInfo',
                'utf_8_encode', 'utf_8_decode',
                'utf_16_be_encode', 'utf_16_be_decode',
                'charmap_encode', 'charmap_decode')
            if version_info >= (2, 6):
                self.allowModule('codecs',
                    'utf_32_be_encode', 'utf_32_be_decode')
            self.allowSafeModule('codecs',
                'ascii_encode', 'ascii_decode',
                'latin_1_encode', 'latin_1_decode',
                'Codec', 'BufferedIncrementalDecoder',
                'IncrementalEncoder', 'IncrementalDecoder',
                'StreamWriter', 'StreamReader',
                'make_identity_dict', 'make_encoding_map')
        elif feature == 'encodings':
            self.enable('codecs')
            self.allowModule('encodings', 'aliases')
            self.allowModule('encodings.ascii', 'getregentry')
            self.allowModule('encodings.latin_1', 'getregentry')
            self.allowModule('encodings.utf_8', 'getregentry')
            self.allowModule('encodings.utf_16_be', 'getregentry')
            if version_info >= (2, 6):
                self.allowModule('encodings.utf_32_be', 'getregentry')
            if version_info < (3, 0):
                self.allowModule('encodings.rot_13', 'getregentry')
        else:
            self._features.remove(feature)
            raise ValueError("Unknown feature: %s" % feature)

    def allowModule(self, name, *attributes):
        if name in self._import_whitelist:
            self._import_whitelist[name][0] |= set(attributes)
        else:
            self._import_whitelist[name] = [set(attributes), set()]
        self.allowModuleSourceCode(name)

    def allowSafeModule(self, name, *safe_attributes):
        if name in self._import_whitelist:
            self._import_whitelist[name][1] |= set(safe_attributes)
        else:
            self._import_whitelist[name] = [set(), set(safe_attributes)]
        self.allowModuleSourceCode(name)

    def allowPath(self, path):
        if self._cpython_restricted:
            raise ValueError("open_whitelist is incompatible with the CPython restricted mode")
        real = realpath(path)
        if path.endswith(path_sep) and not real.endswith(path_sep):
            # realpath() eats trailing separator
            # (eg. /sym/link/ -> /real/path).
            #
            # Restore the suffix (/real/path -> /real/path/) to avoid
            # matching unwanted path (eg. /real/path.evil.path).
            real += path_sep
        self._open_whitelist.add(real)

    def allowModuleSourceCode(self, name):
        """
        Allow reading the module source.
        Do nothing if traceback is disabled.
        """
        if ('traceback' not in self._features) or self._cpython_restricted:
            # restricted mode doesn't allow to open any file
            return

        filename = getModulePath(name)
        if not filename:
            return
        if filename.endswith('.pyc') or filename.endswith('.pyo'):
            # file.pyc / file.pyo => file.py
            filename = filename[:-1]
        if isdir(filename) and not filename.endswith(path_sep):
            # .../encodings => .../encodings/
            filename += path_sep
        self.allowPath(filename)

    @staticmethod
    def createOptparseOptions(parser, default_timeout=_UNSET):
        if default_timeout is _UNSET:
           default_timeout = DEFAULT_TIMEOUT
        parser.add_option("--features",
            help="List of enabled features separated by a comma",
            type="str")
        if HAVE_CPYTHON_RESTRICTED:
            parser.add_option("--restricted",
                help="Use CPython restricted mode (less secure) instead of _sandbox",
                action="store_true")
        parser.add_option("--disable-subprocess",
            help="Don't run untrusted code in a subprocess (less secure)",
            action="store_true")
        parser.add_option("--allow-path",
            help="Allow reading files from PATH",
            action="append", type="str")
        if default_timeout:
            text = "Timeout (default: %.1f sec)" % default_timeout
        else:
            text = "Timeout (default: no timeout)"
        parser.add_option("--timeout",
            help=text, metavar="SECONDS",
            action="store", type="float", default=default_timeout)

    @staticmethod
    def fromOptparseOptions(options):
        kw = {}
        if HAVE_CPYTHON_RESTRICTED and options.restricted:
            kw['cpython_restricted'] = True
        if options.disable_subprocess:
            kw['use_subprocess'] = False
        config = SandboxConfig(**kw)
        if options.features:
            for feature in options.features.split(","):
                feature = feature.strip()
                if not feature:
                    continue
                config.enable(feature)
        if options.allow_path:
            for path in options.allow_path:
                config.allowPath(path)
        if config.use_subprocess:
            config.timeout = options.timeout
        return config


########NEW FILE########
__FILENAME__ = cpython
from __future__ import absolute_import
from sandbox import HAVE_CSANDBOX
if HAVE_CSANDBOX:
    from _sandbox import dictionary_of
else:
    from ctypes import pythonapi, POINTER, py_object

    _get_dict = pythonapi._PyObject_GetDictPtr
    _get_dict.restype = POINTER(py_object)
    _get_dict.argtypes = [py_object]
    del pythonapi, POINTER, py_object

    def dictionary_of(ob):
        dptr = _get_dict(ob)
        return dptr.contents.value


########NEW FILE########
__FILENAME__ = proxy
"""
Proxies using a whitelist policy.
"""
from __future__ import absolute_import
from sys import version_info
if version_info < (3, 0):
    from types import NoneType, ClassType, InstanceType
    OBJECT_TYPES = (file, ClassType, InstanceType)
    BYTES_TYPE = str
    UNICODE_TYPE = unicode
else:
    # Python 3 has no NoneType
    NoneType = type(None)
    OBJECT_TYPES = tuple()
    # 2to3 script converts str to str instead of bytes
    BYTES_TYPE = bytes
    UNICODE_TYPE = str
    if version_info < (3, 2):
        def callable(obj):
            return any("__call__" in cls.__dict__ for cls in type(obj).__mro__)

from types import MethodType, FrameType
from sandbox import SandboxError

builtin_function_or_method = type(len)

SAFE_TYPES = (
    NoneType,
    bool, int, long, float,
    BYTES_TYPE, UNICODE_TYPE,
    FrameType,
)

def readOnlyError():
    raise SandboxError("Read only object")

def createMethodProxy(method_wrapper):
    # Use object with __slots__ to deny the modification of attributes
    # and the creation of new attributes
    class MethodProxy(object):
        __slots__ = ("__name__", "__doc__")
        __doc__ = method_wrapper.__doc__
        def __call__(self, *args, **kw):
            value = method_wrapper(*args, **kw)
            return proxy(value)
    func = MethodProxy()
    func.__name__ = method_wrapper.__name__
    return func

def copyProxyMethods(real_object, proxy_class):
    for name in (
    # Copy methods from the real object because the object type has default
    # implementations
    '__repr__', '__str__', '__hash__', '__call__',
    # Copy __enter__ and __exit__ because the WITH_STATEMENT bytecode uses
    # special_lookup() which reads type(obj).attr instead of obj.attr
    '__enter__', '__exit__',
    ):
        if not hasattr(real_object, name):
            continue
        func = getattr(real_object, name)
        if func is not None:
            func = createMethodProxy(func)
        setattr(proxy_class, name, func)

class ReadOnlySequence(object):
    __slots__ = tuple()

    # Child classes have to implement: __iter__, __getitem__, __len__

    def __delitem__(self, key):
        readOnlyError()

    def __setitem__(self, key, value):
        readOnlyError()

def createReadOnlyDict(real_dict):
    class ReadOnlyDict(ReadOnlySequence):
        __slots__ = tuple()
        __doc__ = real_dict.__doc__

        # FIXME: fromkeys
        # FIXME: compare: __cmp__, __eq__', __ge__, __gt__, __le__, __lt__, __ne__,
        # FIXME: other __reduce__, __reduce_ex__

        def clear(self):
            readOnlyError()

        def __contains__(self, key):
            return (key in real_dict)

        def copy(self):
            return dict(item for item in self.iteritems())

        def get(self, key, default=None):
            if key not in real_dict:
                return default
            value = real_dict[key]
            return proxy(value)

        def __getitem__(self, index):
            value = real_dict.__getitem__(index)
            return proxy(value)

        if version_info < (3, 0):
            def has_key(self, key):
                return (key in real_dict)

        def items(self):
            return list(self.iteritems())

        def __iter__(self):
            return self.iterkeys()

        def iteritems(self):
            for item in real_dict.iteritems():
                key, value = item
                yield (proxy(key), proxy(value))

        def iterkeys(self):
            for key in real_dict.iterkeys():
                yield proxy(key)

        def itervalues(self):
            for value in real_dict.itervalues():
                yield proxy(value)

        def keys(self):
            return list(self.iterkeys())

        def __len__(self):
            return len(real_dict)

        def pop(self, key, default=None):
            readOnlyError()

        def popitem(self):
            readOnlyError()

        def setdefault(self, key, default=None):
            readOnlyError()

        def update(self, other, **items):
            readOnlyError()

        def values(self):
            return list(self.itervalues())

    copyProxyMethods(real_dict, ReadOnlyDict)
    return ReadOnlyDict()

def createReadOnlyList(real_list):
    class ReadOnlyList(ReadOnlySequence):
        __slots__ = tuple()
        __doc__ = real_list.__doc__

        # FIXME: operators: __add__, __iadd__, __imul__, __mul__, __rmul__
        # FIXME: compare: __eq__, __ge__, __gt__, __le__, __lt__, __ne__
        # FIXME: other: __reduce__, __reduce_ex__

        def append(self, value):
            readOnlyError()

        def __contains__(self, value):
            return (value in real_list)

        def count(self, value):
            return real_list.count(value)

        def __delslice__(self, start, end):
            readOnlyError()

        def extend(self, iterable):
            readOnlyError()

        def __getitem__(self, index):
            value = real_list.__getitem__(index)
            return proxy(value)

        def __getslice__(self, start, end):
            value = real_list.__getslice__(start, end)
            return proxy(value)

        def index(self, value):
            return real_list.index(value)

        def insert(self, index, object):
            readOnlyError()

        def __iter__(self):
            for value in real_list:
                yield proxy(value)

        def __len__(self):
            return len(real_list)

        def pop(self, index=None):
            readOnlyError()

        def remove(self, value):
            readOnlyError()

        def reverse(self, value):
            readOnlyError()

        def __reversed__(self):
            for value in real_list.__reversed__():
                yield proxy(value)

        def __setslice__(self, start, end, value):
            readOnlyError()

        def sort(self, cmp=None, key=None, reverse=False):
            readOnlyError()

    copyProxyMethods(real_list, ReadOnlyList)
    return ReadOnlyList()

def createReadOnlyObject(real_object, readOnlyError=readOnlyError,
isinstance=isinstance, MethodType=MethodType):
    # Use object with __slots__ to deny the modification of attributes
    # and the creation of new attributes
    class ReadOnlyObject(object):
        __slots__ = tuple()
        __doc__ = real_object.__doc__

        def __delattr__(self, name):
            readOnlyError()

        def __dir__(self):
            return dir(real_object)

        def __getattr__(self, name):
            value = getattr(real_object, name)
            if isinstance(value, MethodType):
                value = MethodType(value.im_func, self, self.__class__)
            return proxy(value)

        def __setattr__(self, name, value):
            readOnlyError()

    copyProxyMethods(real_object, ReadOnlyObject)
    return ReadOnlyObject()

def copy_callable_attributes(original, copy):
    for name in ('__name__', '__doc__'):
        try:
            value = getattr(original, name)
        except AttributeError:
            continue
        try:
            setattr(copy, name, value)
        except RuntimeError:
            # function attributes not accessible in restricted mode
            pass

def callback_proxy(proxy, callback):
    def _callback_proxy(*args, **kw):
        result = callback(*args, **kw)
        return proxy(result)
    copy_callable_attributes(callback, _callback_proxy)
    return _callback_proxy

def _proxy():
    def proxy(value):
        if isinstance(value, SAFE_TYPES):
            # Safe type, no need to create a proxy
            return value
        elif callable(value):
            return callback_proxy(proxy, value)
        elif isinstance(value, tuple):
            return tuple(
                proxy(item)
                for item in value)
        elif isinstance(value, list):
            return createReadOnlyList(value)
        elif isinstance(value, dict):
            return createReadOnlyDict(value)
        elif isinstance(value, OBJECT_TYPES):
            return createReadOnlyObject(value)
        else:
            raise SandboxError("Unable to proxy a value of type %s" % type(value))
    return proxy
proxy = _proxy()
del _proxy


########NEW FILE########
__FILENAME__ = recursion
from __future__ import absolute_import
from sandbox import Protection
import sys

class SetRecursionLimit(Protection):
    def enable(self, sandbox):
        self.old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(sandbox.config.recusion_limit)

    def disable(self, sandbox):
        sys.setrecursionlimit(self.old_limit)


########NEW FILE########
__FILENAME__ = restorable_dict
from __future__ import absolute_import

class RestorableDict(object):
    def __init__(self, dict):
        self.dict = dict
        self.original = {}
        self.delete = set()
        self.dict_update = dict.update
        self.dict_pop = dict.pop

    def __setitem__(self, key, value):
        if (key not in self.original) and (key not in self.delete):
            if key in self.dict:
                self.original[key] = self.dict[key]
            else:
                self.delete.add(key)
        self.dict[key] = value

    def __delitem__(self, key):
        self.original[key] = self.dict_pop(key)

    def copy(self):
        return self.dict.copy()

    def restore(self):
        for key in self.delete:
            del self.dict[key]
        self.dict_update(self.original)
        self.original.clear()


########NEW FILE########
__FILENAME__ = safe_import
from __future__ import absolute_import
from .proxy import proxy, readOnlyError

def createSafeModule(real_module, attributes, safe_attributes):
    attributes = set(attributes)
    attributes |= set(safe_attributes)

    name_repr = repr(real_module.__name__)
    try:
        module_file = real_module.__file__
    except AttributeError:
        name_repr += " (built-in)"
    else:
        name_repr += " from %r" % module_file
        attributes.add('__file__')

    all_attributes = tuple(attributes)
    attributes = frozenset(attributes)
    safe_attributes = frozenset(safe_attributes)

    class SafeModule(object):
        __doc__ = real_module.__doc__
        __name__ = real_module.__name__
        __all__ = all_attributes
        __slots__ = tuple()

        def __delattr__(self, name):
            readOnlyError()

        def __dir__(self):
            return list(sorted(attributes))

        def __getattr__(self, name):
            if type(name) is not str:
                raise TypeError("expect string, not %s" % type(name).__name__)
            if name not in attributes:
                raise AttributeError("SafeModule %r has no attribute %r" % (self.__name__, name))
            value = getattr(real_module, name)
            if name not in safe_attributes:
                value = proxy(value)
            return value

        def __setattr__(self, name, value):
            readOnlyError()

        def __repr__(self):
            return "<SafeModule %s>" % (name_repr,)

    return SafeModule()

def _safe_import(__import__, module_whitelist):
    """
    Import a module.
    """
    def safe_import(name, globals=None, locals=None, fromlist=None, level=-1):
        try:
            attributes, safe_attributes = module_whitelist[name]
        except KeyError:
            raise ImportError('Import "%s" blocked by the sandbox' % name)
        if globals is None:
            globals = {}
        if locals is None:
            locals = {}
        if fromlist is None:
            fromlist = []
        module = __import__(name, globals, locals, fromlist, level)
        return createSafeModule(module, attributes, safe_attributes)
    return safe_import


########NEW FILE########
__FILENAME__ = safe_open
from __future__ import absolute_import
from os.path import realpath
from .proxy import createReadOnlyObject
from errno import EACCES

def _safe_open(open_whitelist):
    open_file = open
    # Python3 has extra options like encoding and newline
    def safe_open(filename, mode='r', buffering=-1, **kw):
        """A secure file reader."""
        if type(mode) is not str:
            raise TypeError("mode have to be a string, not %s" % type(mode).__name__)
        if mode not in ['r', 'rb', 'rU']:
            raise ValueError("Only read modes are allowed.")

        realname = realpath(filename)
        if not any(realname.startswith(path) for path in open_whitelist):
            raise IOError(EACCES, "Sandbox deny access to the file %s" % repr(filename))

        fileobj = open_file(filename, mode, buffering, **kw)
        return createReadOnlyObject(fileobj)
    return safe_open


########NEW FILE########
__FILENAME__ = sandbox_class
from __future__ import with_statement, absolute_import
from .config import SandboxConfig
from .proxy import proxy
from sys import _getframe

def keywordsProxy(keywords):
    # Dont proxy keys because function keywords must be strings
    return dict(
        (key, proxy(value))
        for key, value in keywords.iteritems())

def _call_exec(code, globals, locals):
    exec code in globals, locals

def _dictProxy(data):
    items = data.items()
    data.clear()
    for key, value in items:
        data[proxy(key)] = proxy(value)

class Sandbox(object):
    PROTECTIONS = []

    def __init__(self, config=None):
        if config:
            self.config = config
        else:
            self.config = SandboxConfig()
        self.protections = [protection() for protection in self.PROTECTIONS]
        self.execute_subprocess = None
        self.call_fork = None
        # set during enable()
        self.frame = None

    def _call(self, func, args, kw):
        """
        Call a function in the sandbox.
        """
        args = proxy(args)
        kw = keywordsProxy(kw)
        self.frame = _getframe()
        for protection in self.protections:
            protection.enable(self)
        self.frame = None
        try:
            return func(*args, **kw)
        finally:
            for protection in reversed(self.protections):
                protection.disable(self)

    def call(self, func, *args, **kw):
        """
        Call a function in the sandbox.
        """
        if self.config.use_subprocess:
            if self.call_fork is None:
                from .subprocess_parent import call_fork
                self.call_fork = call_fork
            return self.call_fork(self, func, args, kw)
        else:
            return self._call(func, args, kw)

    def _execute(self, code, globals, locals):
        """
        Execute the code in the sandbox:

           exec code in globals, locals
        """
        if globals is None:
            globals = {}
        self.frame = _getframe()
        for protection in self.protections:
            protection.enable(self)
        self.frame = None
        try:
            _call_exec(code, globals, locals)
        finally:
            for protection in reversed(self.protections):
                protection.disable(self)

    def execute(self, code, globals=None, locals=None):
        """
        Execute the code in the sandbox:

           exec code in globals, locals

        Run the code in a subprocess except if it is disabled in the sandbox
        configuration.

        The method has no result. By default, use globals={} to get an empty
        namespace.
        """
        if self.config.use_subprocess:
            if self.execute_subprocess is None:
                from .subprocess_parent import execute_subprocess
                self.execute_subprocess = execute_subprocess
            return self.execute_subprocess(self, code, globals, locals)
        else:
            code = proxy(code)
            if globals is not None:
                _dictProxy(globals)
            if locals is not None:
                _dictProxy(locals)
            return self._execute(code, globals, locals)

    def createCallback(self, func, *args, **kw):
        """
        Create a callback: the function will be called in the sandbox.
        The callback takes no argument.
        """
        args = proxy(args)
        kw = keywordsProxy(kw)
        def callback():
            return self.call(func, *args, **kw)
        return callback


########NEW FILE########
__FILENAME__ = stdio
from __future__ import absolute_import
import sys
from sandbox import SandboxError, Protection

def createNoAttribute(stream_name):
    def _blocked(name):
        raise SandboxError("Block access to sys.%s.%s" % (stream_name, name))

    # FIXME:
    #class NoAttribute(object):
    #    __slots__ = tuple()
    class NoAttribute:
        def __getattr__(self, name):
            _blocked(name)

        def __setattr__(self, name, value):
            _blocked(name)

        def __delattr__(self, name):
            _blocked(name)
    return NoAttribute()

class ProtectStdio(Protection):
    """
    If stdin / stdout / stderr feature is disable, replace sys.stdin /
    sys.stdout / sys.stderr by a dummy object with no attribute.
    """
    def __init__(self):
        self.sys = sys

    def enable(self, sandbox):
        features = sandbox.config.features

        self.stdin = self.sys.stdin
        if 'stdin' not in features:
            self.sys.stdin = createNoAttribute("stdin")

        self.stdout = self.sys.stdout
        if 'stdout' not in features:
            self.sys.stdout = createNoAttribute("stdout")

        self.stderr = self.sys.stderr
        if 'stderr' not in features:
            self.sys.stderr = createNoAttribute("stderr")

    def disable(self, sandbox):
        self.sys.stdin = self.stdin
        self.sys.stdout = self.stdout
        self.sys.stderr = self.stderr
        self.stdin = None
        self.stdout = None
        self.stderr = None


########NEW FILE########
__FILENAME__ = subprocess_child
from __future__ import with_statement
import sys
import os
import pickle
from sandbox import Sandbox

try:
    import resource
except ImportError:
    resource = None

PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

def set_process_limits(config):
    if resource is not None:
        # deny fork and thread
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))

    if not config.has_feature("stdin"):
        stdin_fd = sys.__stdin__.fileno()
        devnull = os.open(os.devnull, os.O_RDONLY)
        os.dup2(devnull, stdin_fd)

    if not config.has_feature("stdout") \
    or not config.has_feature("stderr"):
        devnull = os.open(os.devnull, os.O_WRONLY)
        if not config.has_feature("stdout"):
            stdout_fd = sys.__stdout__.fileno()
            os.dup2(devnull, stdout_fd)
        if not config.has_feature("stderr"):
            stderr_fd = sys.__stderr__.fileno()
            os.dup2(devnull, stderr_fd)

    if config.max_memory:
        if not resource:
            raise NotImplementedError("SandboxConfig.max_memory is not implemented on your platform")
        resource.setrlimit(resource.RLIMIT_AS, (config.max_memory, -1))

def execute_child():
    input_filename = sys.argv[1]
    output_filename = sys.argv[2]
    output = open(output_filename, "wb")
    base_exception = BaseException
    try:
        with open(input_filename, 'rb') as input_file:
            input_data = pickle.load(input_file)
        code = input_data['code']
        config = input_data['config']
        locals = input_data['locals']
        globals = input_data['globals']
        set_process_limits(config)

        sandbox = Sandbox(config)
        result = sandbox._execute(code, globals, locals)

        output_data = {'result': result}
        if input_data['globals'] is not None:
            del globals['__builtins__']
            output_data['globals'] = globals
        if 'locals' in input_data:
            output_data['locals'] = locals
    except base_exception, err:
        output_data = {'error': err}
    pickle.dump(output_data, output, PICKLE_PROTOCOL)
    output.flush()
    output.close()

def call_child(wpipe, sandbox, func, args, kw):
    config = sandbox.config
    try:
        set_process_limits(config)
        result = sandbox._call(func, args, kw)
        data = {'result': result}
    except BaseException, err:
        data = {'error': err}
    output = os.fdopen(wpipe, 'wb')
    pickle.dump(data, output, PICKLE_PROTOCOL)
    output.flush()
    output.close()
    if config.has_feature("stdout"):
        sys.stdout.flush()
        sys.stdout.close()
    if config.has_feature("stderr"):
        sys.stderr.flush()
        sys.stderr.close()
    os._exit(0)

if __name__ == "__main__":
    execute_child()


########NEW FILE########
__FILENAME__ = subprocess_parent
from __future__ import with_statement, absolute_import
from sandbox import SandboxError, Timeout
from sandbox.subprocess_child import call_child
import os
import pickle
import subprocess
import sys
import tempfile
import time
try:
    import fcntl
except ImportError:
    set_cloexec_flag = None
else:
    def set_cloexec_flag(fd):
        try:
            cloexec_flag = fcntl.FD_CLOEXEC
        except AttributeError:
            cloexec_flag = 1
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | cloexec_flag)
try:
    from time import monotonic as monotonic_time
except ImportError:
    # Python < 3.3
    from time import time as monotonic_time

def wait_child(config, pid, sigkill):
    if config.timeout:
        timeout = monotonic_time() + config.timeout
        kill = False
        status = os.waitpid(pid, os.WNOHANG)
        while status[0] == 0:
            dt = timeout - monotonic_time()
            if dt < 0:
                os.kill(pid, sigkill)
                status = os.waitpid(pid, 0)
                raise Timeout()

            if dt > 1.0:
                pause = 0.100
            else:
                pause = 0.010
            # TODO: handle SIGCHLD to avoid wasting time in polling
            time.sleep(pause)
            status = os.waitpid(pid, os.WNOHANG)
    else:
        status = os.waitpid(pid, 0)
    if status[0] != pid:
        raise Exception("got the status of the wrong process!")
    return status[1]

def call_parent(config, pid, rpipe):
    import signal
    sigkill = signal.SIGKILL
    try:
        status = wait_child(config, pid, sigkill)
    except:
        os.close(rpipe)
        raise
    if status != 0:
        if os.WIFSIGNALED(status):
            signum = os.WTERMSIG(status)
            text = "subprocess killed by signal %s" % signum
        elif os.WIFEXITED(status):
            exitcode = os.WEXITSTATUS(status)
            text = "subprocess failed with exit code %s" % exitcode
        else:
            text = "subprocess failed"
        raise SandboxError(text)
    rpipe_file = os.fdopen(rpipe, 'rb')
    try:
        data = pickle.load(rpipe_file)
    finally:
        rpipe_file.close()
    if 'error' in data:
        raise data['error']
    return data['result']

def call_fork(sandbox, func, args, kw):
    rpipe, wpipe = os.pipe()
    if set_cloexec_flag is not None:
        set_cloexec_flag(wpipe)
    pid = os.fork()
    if pid == 0:
        os.close(rpipe)
        try:
            call_child(wpipe, sandbox, func, args, kw)
        finally:
            # FIXME: handle error differently?
            os._exit(1)
    else:
        os.close(wpipe)
        return call_parent(sandbox.config, pid, rpipe)

def execute_subprocess(sandbox, code, globals, locals):
    config = sandbox.config
    input_filename = tempfile.mktemp()
    output_filename = tempfile.mktemp()
    args = (
        sys.executable,
        # FIXME: use '-S'
        '-E',
        '-m', 'sandbox.subprocess_child',
        input_filename, output_filename,
    )

    input_data = {
        'code': code,
        'config': config,
        'locals': locals,
        'globals': globals,
    }

    try:
        # serialize input data
        with open(input_filename, 'wb') as input_file:
            pickle.dump(input_data, input_file)
            if config.max_input_size:
                size = input_file.tell()
                if size > config.max_input_size:
                    raise SandboxError("Input data are too big: %s bytes (max=%s)"
                                       % (size, config.max_input_size))

        # create the subprocess
        process = subprocess.Popen(args, close_fds=True, shell=False)

        # wait process exit
        if config.timeout:
            timeout = monotonic_time() + config.timeout
            kill = False
            exitcode = process.poll()
            while exitcode is None:
                dt = timeout - monotonic_time()
                if dt < 0:
                    process.terminate()
                    exitcode = process.wait()
                    raise Timeout()

                if dt > 1.0:
                    pause = 0.5
                else:
                    pause = 0.1
                # TODO: handle SIGCHLD to avoid wasting time in polling
                time.sleep(pause)
                exitcode = process.poll()
        else:
            exitcode = process.wait()
        os.unlink(input_filename)
        input_filename = None

        # handle child process error
        if exitcode:
            if os.name != "nt" and exitcode < 0:
                signum = -exitcode
                text = "subprocess killed by signal %s" % signum
            else:
                text = "subprocess failed with exit code %s" % exitcode
            raise SandboxError(text)

        with open(output_filename, 'rb') as output_file:
            if config.max_output_size:
                output_file.seek(0, 2)
                size = output_file.tell()
                output_file.seek(0)
                if size > config.max_output_size:
                    raise SandboxError("Output data are too big: %s bytes (max=%s)"
                                       % (size, config.max_output_size))
            output_data = pickle.load(output_file)
        os.unlink(output_filename)
        output_filename = None
    finally:
        temp_filenames = []
        if input_filename is not None:
            temp_filenames.append(input_filename)
        if output_filename is not None:
            temp_filenames.append(output_filename)
        for filename in temp_filenames:
            try:
                os.unlink(filename)
            except OSError:
                pass

    if 'error' in output_data:
        raise output_data['error']
    if locals is not None:
        locals.clear()
        locals.update(output_data['locals'])
    if globals is not None:
        globals.clear()
        globals.update(output_data['globals'])
    return output_data['result']


########NEW FILE########
__FILENAME__ = test_attributes
from sandbox import HAVE_PYPY, SandboxError
from sandbox.test import createSandbox, SkipTest, unindent, execute_code

# FIXME: reenable these tests
if HAVE_PYPY:
    raise SkipTest("tests disabled on PyPy")

def test_closure():
    code = unindent('''
        def read_closure_secret():
            def createClosure(secret):
                def closure():
                    return secret
                return closure
            func = createClosure(42)
            try:
                cell = func.func_closure[0]
            except AttributeError:
                # Python 2.6+
                cell = func.__closure__[0]
            # Does Python < 2.5 have the cell_contents attribute?  See this recipe,
            # get_cell_value(), for version without the attribute:
            # http://code.activestate.com/recipes/439096/
            secret = cell.cell_contents
            assert secret == 42
    ''')

    # Begin by a test outside the sandbox to fill the type cache
    unsafe_code = code + unindent('''
        try:
            read_closure_secret()
        except AttributeError, err:
            assert str(err) == "'function' object has no attribute '__closure__'"
        else:
            assert False, "func_closure is present"
    ''')
    createSandbox().execute(unsafe_code)

    # Repeat the test to ensure that the attribute cache is cleared correctly
    safe_code = code + unindent('''
        read_closure_secret()
    ''')
    execute_code(safe_code)


def test_func_globals():
    code = unindent('''
        SECRET = 42

        def get_secret_from_func_globals():
            def mysum(a, b):
                return a+b
            try:
                func_globals = mysum.func_globals
            except AttributeError:
                # Python 2.6+
                func_globals = mysum.__globals__
            return func_globals['SECRET']
    ''')

    unsafe_code = code + unindent('''
        try:
            get_secret_from_func_globals()
        except AttributeError, err:
            assert str(err) == "'function' object has no attribute '__globals__'"
        else:
            assert False
    ''')
    createSandbox().execute(unsafe_code)

    safe_code = code + unindent("""
        assert get_secret_from_func_globals() == 42
    """)
    execute_code(safe_code)


def test_func_locals():
    # FIXME: rewrite test with a simpler trace, without safe_import
    def get_import_from_func_locals(safe_import, exc_info):
        try:
            safe_import("os")
        except ImportError:
            # import os always raise an error
            err_value, err_type, try_traceback = exc_info()
            safe_import_traceback = try_traceback.tb_next
            safe_import_frame = safe_import_traceback.tb_frame
            return safe_import_frame.f_locals['__import__']

    import sys

    def frame_locals_denied():
        try:
            get_import_from_func_locals(__import__, sys.exc_info)
        except AttributeError, err:
            assert str(err) == "'frame' object has no attribute 'f_locals'"
        else:
            assert False
    # FIXME: use sandbox.execute()
    createSandbox().call(frame_locals_denied)

    builtin_import = __import__
    from sandbox.safe_import import _safe_import
    safe_import = _safe_import(builtin_import, {})
    myimport = get_import_from_func_locals(safe_import, sys.exc_info)
    assert myimport is builtin_import


def test_func_defaults():
    from sys import version_info
    if version_info < (2, 6):
        raise SkipTest("tests disabled on Python < 2.6")

    unsafe_code = unindent('''
        try:
            open.__defaults__
        except AttributeError, err:
            assert str(err) in (
                # open is safe_open()
                "'function' object has no attribute '__defaults__'",
                # builtin open() in restricted mode
                "'builtin_function_or_method' object has no attribute '__defaults__'",
            )
        else:
            assert False
    ''')

    if version_info < (3, 0):
        unsafe_code += unindent('''
            try:
                open.func_defaults
            except AttributeError, err:
                assert str(err) in (
                    # open is safe_open()
                    "'function' object has no attribute 'func_defaults'",
                    # builtin open() in restricted mode
                    "'builtin_function_or_method' object has no attribute 'func_defaults'",
                )
            else:
                assert False
        ''')

    sandbox = createSandbox()
    sandbox.execute(unsafe_code)


def test_type_bases():
    from sys import version_info
    if version_info < (2, 6):
        raise SkipTest("tests disabled on Python < 2.6")

    code = unindent('''
    def test():
        class A(object):
            pass
        class B(object):
            pass
        class X(A):
            pass
        X.__bases__ = (B,)
        if not issubclass(X, B):
            raise AttributeError("__bases__ error")
    ''')

    unsafe_code = code + unindent('''
        try:
            test()
        except AttributeError, err:
            assert str(err) == "__bases__ error"
        else:
            assert False
    ''')
    createSandbox().execute(unsafe_code)

    safe_code = code + unindent('''
        test()
    ''')
    execute_code(safe_code)


########NEW FILE########
__FILENAME__ = test_builtins
from sandbox import Sandbox, SandboxError, HAVE_CSANDBOX, HAVE_PYPY
from sandbox.test import SkipTest, createSandbox, createSandboxConfig, unindent
from sys import version_info

def test_call_exec_builtins():
    code = unindent('''
        result = []
        exec "result.append(type(__builtins__))" in {'result': result}
        builtin_type = result[0]
        assert builtin_type != dict
    ''')
    config = createSandboxConfig()
    if HAVE_PYPY:
        # FIXME: is it really needed?
        config._builtins_whitelist.add('compile')
    Sandbox(config).execute(code)

def test_exec_builtins():
    config = createSandboxConfig()
    Sandbox(config).execute("""
assert type(__builtins__) != dict
    """.strip())

def test_builtins_setitem():
    code = unindent('''
        def builtins_superglobal():
            if isinstance(__builtins__, dict):
                __builtins__['SUPERGLOBAL'] = 42
                assert SUPERGLOBAL == 42
                del __builtins__['SUPERGLOBAL']
            else:
                __builtins__.SUPERGLOBAL = 42
                assert SUPERGLOBAL == 42
                del __builtins__.SUPERGLOBAL
    ''')

    unsafe_code = code + unindent('''
        try:
            builtins_superglobal()
        except SandboxError, err:
            assert str(err) == "Read only object"
        else:
            assert False
    ''')
    createSandbox().execute(unsafe_code)

    safe_code = code + unindent('''
        builtins_superglobal()
    ''')
    execute_code(safe_code)

def test_builtins_init():
    import warnings

    code = unindent('''
        def check_init():
            __builtins__.__init__({})

        def check_dict_init():
            try:
                dict.__init__(__builtins__, {})
            except ImportError, err:
                assert str(err) == 'Import "_warnings" blocked by the sandbox'
            except DeprecationWarning, err:
                assert str(err) == 'object.__init__() takes no parameters'
            else:
                assert False
    ''')

    unsafe_code = code + unindent('''
        check_init()
    ''')

    try:
        createSandbox().execute(unsafe_code)
    except SandboxError, err:
        assert str(err) == "Read only object", str(err)
    else:
        assert False

    # FIXME: is this test still needed?
    # if version_info >= (2, 6):
    #     original_filters = warnings.filters[:]
    #     try:
    #         warnings.filterwarnings('error', '', DeprecationWarning)

    #         config = createSandboxConfig()
    #         Sandbox(config).call(check_dict_init)
    #     finally:
    #         del warnings.filters[:]
    #         warnings.filters.extend(original_filters)

def test_modify_builtins_dict():
    code = unindent('''
        def builtins_dict_superglobal():
            __builtins__['SUPERGLOBAL'] = 42
            assert SUPERGLOBAL == 42
            del __builtins__['SUPERGLOBAL']
    ''')

    unsafe_code = code + unindent('''
        try:
            builtins_dict_superglobal()
        except AttributeError, err:
            assert str(err) == "type object 'dict' has no attribute '__setitem__'"
        else:
            assert False
    ''')
    try:
        createSandbox().execute(unsafe_code)
    except SandboxError, err:
        assert str(err) == "Read only object"

def test_del_builtin():
    code = unindent('''
        def del_builtin_import():
            import_func = __builtins__['__import__']
            dict.__delitem__(__builtins__, '__import__')
            try:
                try:
                    import sys
                except NameError, err:
                    assert str(err) == "type object 'dict' has no attribute '__setitem__'"
            finally:
                __builtins__['__import__'] = import_func
    ''')

    unsafe_code = code + unindent('''
        try:
            del_builtin_import()
        except AttributeError, err:
            assert str(err) == "type object 'dict' has no attribute '__delitem__'"
        except SandboxError, err:
            assert str(err) == "Read only object"
        else:
            assert False
    ''')

    config = createSandboxConfig()
    config.allowModule('sys')
    Sandbox(config).execute(unsafe_code)


########NEW FILE########
__FILENAME__ = test_code
from sys import version_info
from sandbox import Sandbox, SandboxError, HAVE_CSANDBOX, HAVE_PYPY
from sandbox.test import (createSandbox, createSandboxConfig,
    SkipTest, TestException, skipIf)

# code constructor arguments
def get_code_args():
    def somme(a, b):
        return a+b
    fcode = somme.func_code
    if version_info >= (3, 0):
        return (
            fcode.co_argcount,
            fcode.co_kwonlyargcount,
            fcode.co_nlocals,
            fcode.co_stacksize,
            fcode.co_flags,
            fcode.co_code,
            fcode.co_consts,
            fcode.co_names,
            fcode.co_varnames,
            fcode.co_filename,
            fcode.co_name,
            fcode.co_firstlineno,
            fcode.co_lnotab,
        )
    else:
        return (
            fcode.co_argcount,
            fcode.co_nlocals,
            fcode.co_stacksize,
            fcode.co_flags,
            fcode.co_code,
            fcode.co_consts,
            fcode.co_names,
            fcode.co_varnames,
            fcode.co_filename,
            fcode.co_name,
            fcode.co_firstlineno,
            fcode.co_lnotab,
        )

def get_code_objects():
    try:
        yield compile("1", "<string>", "eval")
    except NameError:
        pass

    # Function code
    def func():
        pass
    try:
        yield func.__code__
    except (AttributeError, RuntimeError):
        pass

    # Generator code
    def generator():
        yield
    gen = generator()
    try:
        yield gen.gi_code
    except AttributeError:
        pass

    # Frame code
    import sys
    frame = sys._getframe(0)
    try:
        yield frame.f_code
    except AttributeError:
        pass

def create_code_objects(args):
    for code_obj in get_code_objects():
        code_type = type(code_obj)
        try:
            return code_type(*args)
        except SandboxError, err:
            assert str(err) == 'code() blocked by the sandbox'
    raise TestException("Unable to get code type")

def exec_bytecode(code_args):
    def func():
        pass
    function_type = type(func)
    fcode = create_code_objects(code_args)
    new_func = function_type(fcode, {}, "new_func")
    return new_func(1, 2)

def test_bytecode():
    if not HAVE_CSANDBOX:
        # restricted mode doesn't block creation of arbitrary code object
        raise SkipTest("require _sandbox")

    code_args = get_code_args()

    config = createSandboxConfig()
    config.allowModule('sys', '_getframe')
    try:
        Sandbox(config).call(exec_bytecode, code_args)
    except TestException, err:
        assert str(err) == "Unable to get code type"
    else:
        assert False

    assert exec_bytecode(code_args) == 3

def replace_func_code():
    def add(x, y):
        return x + y
    def substract(x, y):
        return x - y
    try:
        add.func_code = substract.func_code
    except (AttributeError, RuntimeError):
        add.__code__ = substract.__code__
    return add(52, 10)

# FIXME: reenable this test on PyPy
@skipIf(HAVE_PYPY, "test disabled on PyPy")
def test_func_code():
    sandbox = createSandbox()
    try:
        sandbox.call(replace_func_code)
    except AttributeError, err:
        assert str(err) == "'function' object has no attribute '__code__'"
    except RuntimeError, err:
        assert str(err) == "function attributes not accessible in restricted mode"
    else:
        assert False

    assert replace_func_code() == 42


########NEW FILE########
__FILENAME__ = test_execute
from __future__ import with_statement
from sys import version_info
from sandbox import Sandbox, HAVE_PYPY
from sandbox.test import createSandbox, createSandboxConfig, SkipTest
from sandbox.test.tools import capture_stdout
import os

def test_execute():
    config = createSandboxConfig()
    if HAVE_PYPY:
        # FIXME: is it really needed?
        config._builtins_whitelist.add('compile')
    if config.use_subprocess:
        globals_builtins = set()
    else:
        globals_builtins = set(( '__builtins__',))

    def test(*lines, **kw):
        code = "; ".join(lines)
        Sandbox(config).execute(code, **kw)

    test(
        "assert globals() is locals(), 'test_execute #1a'",
        "assert list(globals().keys()) == list(locals().keys()) == ['__builtins__'], 'test_execute #1b'",
        "x=42")

    namespace = {'a': 1}
    test(
        "assert globals() is locals(), 'test_execute #2a'",
        "assert list(globals().keys()) == list(locals().keys()) == ['a', '__builtins__'], 'test_execute #2b'",
        "a=10",
        "x=42",
        globals=namespace)
    assert set(namespace.keys()) == (set(('a', 'x')) | globals_builtins)
    assert namespace['a'] == 10
    assert namespace['x'] == 42

    namespace = {'b': 2}
    test(
        "assert globals() is not locals(), 'test_execute #3a'",
        "assert list(globals().keys()) == ['__builtins__'], 'test_execute #3b'",
        "assert list(locals().keys()) == ['b'], 'test_execute #3c'",
        "b=20",
        "x=42",
        locals=namespace)
    assert namespace == {'b': 20, 'x': 42}

    my_globals = {'a': 1}
    namespace = {'b': 2}
    test(
        "assert globals() is not locals(), 'test_execute #4a'",
        "assert list(globals().keys()) == ['a', '__builtins__'], 'test_execute #4b'",
        "assert list(locals().keys()) == ['b'], 'test_execute #4c'",
        "x=42",
        "a=10",
        "b=20",
        globals=my_globals,
        locals=namespace)
    assert set(my_globals.keys()) == (set(('a',)) | globals_builtins)
    assert my_globals['a'] == 1
    assert namespace == {'a': 10, 'b': 20, 'x': 42}

    namespace = {}
    test('a=1', locals=namespace)
    assert namespace == {'a': 1}, namespace

def test_execfile():
    import sys

    if version_info >= (3, 0):
        raise SkipTest("execfile() only exists in Python 2.x")

    def execfile_test(filename):
        execfile(filename)

    from tempfile import mktemp

    filename = mktemp()
    with open(filename, "w") as script:
        print >>script, "print('Hello World!')"
        script.flush()

    try:
        config = createSandboxConfig('stdout')
        try:
            Sandbox(config).call(execfile_test, filename)
        except NameError, err:
            assert str(err) == "global name 'execfile' is not defined"
        else:
            assert False

        with capture_stdout() as stdout:
            execfile_test(filename)
            sys.stdout.flush()
            stdout.seek(0)
            output = stdout.read()
            assert output.startswith('Hello World')
    finally:
        os.unlink(filename)

def test_compile():
    import sys

    orig_displayhook = sys.displayhook
    try:
        results = []
        def displayhook(value):
            results.append(value)

        sys.displayhook = displayhook

        def _test_compile():
            exec compile("1+1", "<string>", "single") in {}
            assert results == [2]
        config = createSandboxConfig()
        Sandbox(config).call(_test_compile)

        del results[:]
        _test_compile()
    finally:
        sys.displayhook = orig_displayhook



########NEW FILE########
__FILENAME__ = test_import
from sandbox import Sandbox, SandboxError
from sandbox.test import createSandbox, createSandboxConfig

def test_import():
    def import_blocked():
        try:
            import os
        except ImportError, err:
            assert str(err) == 'Import "os" blocked by the sandbox'
        else:
            assert False
    createSandbox().call(import_blocked)

    # import is allowed outside the sandbox
    import os

def test_import_whitelist():
    # sys.version is allowed by the sandbox
    import sys
    sys_version = sys.version
    del sys

    config = createSandboxConfig()
    config.allowModule('sys', 'version')
    def import_sys():
        import sys
        assert sys.__name__ == 'sys'
        assert sys.version == sys_version
    Sandbox(config).call(import_sys)

def test_readonly_import():
    config = createSandboxConfig()
    config.allowModule('sys', 'version')
    def readonly_module():
        import sys

        try:
            sys.version = '3000'
        except SandboxError, err:
            assert str(err) == "Read only object"
        else:
            assert False

        try:
            object.__setattr__(sys, 'version', '3000')
        except AttributeError, err:
            assert str(err) == "'SafeModule' object has no attribute 'version'"
        else:
            assert False
    Sandbox(config).call(readonly_module)


########NEW FILE########
__FILENAME__ = test_interpreter
from subprocess import Popen, PIPE, STDOUT
from sandbox.test import createSandboxConfig
from sandbox.test.tools import bytes_literal
import os
import sys
from sys import version_info
from locale import getpreferredencoding

def check_interpreter_stdout(code, expected, **kw):
    encoding = kw.get('encoding', 'utf-8')

    env = os.environ.copy()
    # Use dummy terminal type to avoid 8 bits mode
    # escape sequence ('\x1b[?1034h')
    env['TERM'] = 'dumb'
    env['PYTHONIOENCODING'] = encoding
    args = [sys.executable, 'interpreter.py', '-q']
    if not createSandboxConfig.use_subprocess:
        args.append('--disable-subprocess')
    process = Popen(
        args,
        stdin=PIPE, stdout=PIPE, stderr=STDOUT,
        env=env)
    code += u'\nexit()'
    code = code.encode(encoding)
    stdout, stderr = process.communicate(code)
    if process.returncode != 0:
        raise AssertionError(
            "Process error: exit code=%s, stdout=%r"
            % (process.returncode, stdout))
    assert process.returncode == 0
    stdout = stdout.splitlines()
    start = 0
    while not stdout[start]:
        start += 1
    stdout = stdout[start:]
    assert stdout == expected, "%s != %s" % (stdout, expected)

def test_interpreter():
    check_interpreter_stdout('1+1',
        [bytes_literal(r"sandbox>>> 2"),
         bytes_literal('sandbox>>> ')])

    if version_info >= (3, 0):
        code = u'print(ascii("\xe9"))'
        expected = u"'\\xe9'"
    else:
        code = u'print(repr(u"\xe9"))'
        expected = u"u'\\xe9'"
    for encoding in ('latin_1', 'utf_8'):
        check_interpreter_stdout(code,
            [bytes_literal(r"sandbox>>> " + expected),
             bytes_literal(''),
             bytes_literal('sandbox>>> ')],
            encoding=encoding)


########NEW FILE########
__FILENAME__ = test_misc
from __future__ import with_statement
from sandbox import Sandbox, SandboxError, SandboxConfig, Timeout
from sandbox.test import createSandbox, createSandboxConfig, SkipTest
from sandbox.test.tools import capture_stdout

def test_valid_code():
    def valid_code():
        assert 1+2 == 3
    createSandbox().call(valid_code)

def test_exit():
    def exit_noarg():
        try:
            exit()
        except SandboxError, err:
            assert str(err) == "exit() function blocked by the sandbox"
        else:
            assert False
    createSandbox().call(exit_noarg)

    config = createSandboxConfig("exit")
    def exit_1():
        try:
            exit(1)
        except SystemExit, err:
            assert err.args[0] == 1
        else:
            assert False

        import sys
        try:
            sys.exit("bye")
        except SystemExit, err:
            assert err.args[0] == "bye"
        else:
            assert False
    Sandbox(config).call(exit_1)

def test_sytem_exit():
    def system_exit_denied():
        try:
            raise SystemExit()
        except NameError, err:
            assert str(err) == "global name 'SystemExit' is not defined"
        except:
            assert False
    createSandbox().call(system_exit_denied)

    config = createSandboxConfig("exit")
    def system_exit_allowed():
        try:
            raise SystemExit()
        except SystemExit:
            pass
        else:
            assert False
    Sandbox(config).call(system_exit_allowed)

    try:
        raise SystemExit()
    except SystemExit:
        pass
    else:
        assert False

def test_stdout():
    import sys

    config = createSandboxConfig(disable_debug=True)
    with capture_stdout() as stdout:
        def print_denied():
            print "Hello Sandbox 1"
        try:
            Sandbox(config).call(print_denied)
        except SandboxError:
            pass
        else:
            assert False

        def print_allowed():
            print "Hello Sandbox 2"
        config2 = createSandboxConfig('stdout')
        Sandbox(config2).call(print_allowed)

        print "Hello Sandbox 3"

        sys.stdout.flush()
        stdout.seek(0)
        output = stdout.read()

    assert output == "Hello Sandbox 2\nHello Sandbox 3\n"

def test_traceback():
    def check_frame_filename():
        import sys
        frame = sys._getframe(1)
        frame_code = frame.f_code
        frame_filename = frame_code.co_filename
        # it may ends with .py or .pyc
        assert __file__.startswith(frame_filename)

    config = createSandboxConfig('traceback')
    config.allowModule('sys', '_getframe')
    Sandbox(config).call(check_frame_filename)

    check_frame_filename()

def test_regex():
    def check_regex():
        import re
        assert re.escape('+') == '\\+'
        assert re.match('a+', 'aaaa').group(0) == 'aaaa'
        # FIXME: Remove this workaround: list(...)
        assert list(re.findall('.', 'abc')) == ['a', 'b', 'c']
        assert re.search('a+', 'aaaa').group(0) == 'aaaa'
        # FIXME: Remove this workaround: list(...)
        assert list(re.split(' +', 'a b    c')) == ['a', 'b', 'c']
        assert re.sub('a+', '#', 'a b aa c') == '# b # c'

    sandbox = createSandbox('regex')
    sandbox.call(check_regex)

    check_regex()

def test_timeout_while_1():
    if not createSandboxConfig.use_subprocess:
        raise SkipTest("timeout is only supported with subprocess")

    def denial_of_service():
        while 1:
            pass

    config = createSandboxConfig()
    config.timeout = 0.1
    try:
        Sandbox(config).call(denial_of_service)
    except Timeout:
        pass
    else:
        assert False

def test_timeout_cpu_intensive():
    if not createSandboxConfig.use_subprocess:
        raise SkipTest("timeout is only supported with subprocess")

    def denial_of_service():
        sum(2**x for x in range(100000))

    config = createSandboxConfig()
    config.timeout = 0.1
    try:
        Sandbox(config).call(denial_of_service)
    except Timeout:
        pass
    else:
        assert False

def test_crash():
    if not createSandboxConfig.use_subprocess:
        raise SkipTest("catching a crash is only supported with subprocess")

    def crash():
        import _sandbox
        _sandbox._test_crash()

    config = createSandboxConfig()
    config.allowSafeModule("_sandbox", "_test_crash")
    sand = Sandbox(config)
    try:
        sand.call(crash)
    except SandboxError, err:
        assert str(err) == 'subprocess killed by signal 11', str(err)
    else:
        assert False


########NEW FILE########
__FILENAME__ = test_open
from __future__ import with_statement
from sandbox import Sandbox, SandboxError, HAVE_CSANDBOX, HAVE_PYPY
from sandbox.test import (createSandbox, createSandboxConfig,
    SkipTest, TestException, skipIf)
from sandbox.test.tools import read_first_line, READ_FILENAME
from sys import version_info
import os

def _get_file_type(obj):
    if version_info >= (3, 0):
        if hasattr(obj, "buffer"):
            # TextIOWrapper => BufferedXXX
            obj = obj.buffer
        if hasattr(obj, "raw"):
            # BufferedXXX => _FileIO
            obj = obj.raw
    return type(obj)

def test_open_denied():
    from errno import EACCES

    def access_denied():
        try:
            read_first_line(open)
        except IOError, err:
            if err.errno == EACCES:
                # safe_open() error
                assert err.args[1].startswith('Sandbox deny access to the file ')
            else:
                # restricted python error
                assert str(err) == 'file() constructor not accessible in restricted mode'
        else:
            assert False
    createSandbox().call(access_denied)

    read_first_line(open)

def test_open_whitelist():
    config = createSandboxConfig()
    if config.cpython_restricted:
        # the CPython restricted mode denies to open any file
        raise SkipTest("require _sandbox")
    config.allowPath(READ_FILENAME)
    Sandbox(config).call(read_first_line, open)

def test_write_file():
    from tempfile import mktemp

    def write_file(filename):
        with open(filename, "w") as fp:
            fp.write("test")

    filename = mktemp()
    def write_denied(filename):
        try:
            write_file(filename)
        except ValueError, err:
            assert str(err) == "Only read modes are allowed."
        except IOError, err:
            assert str(err) == "file() constructor not accessible in restricted mode"
        else:
            assert False, "writing to a file is not blocked"
    createSandbox().call(write_denied, filename)

    filename = mktemp()
    write_file(filename)
    os.unlink(filename)

def test_filetype_from_sys_stdout():
    def get_file_type_from_stdout():
        import sys
        return _get_file_type(sys.stdout)

    config = createSandboxConfig('stdout')
    def get_file_type_object():
        file_type = get_file_type_from_stdout()
        try:
            read_first_line(file_type)
        except TypeError, err:
            assert str(err) in ('object.__new__() takes no parameters', 'default __new__ takes no parameters')
        else:
            assert False
    Sandbox(config).call(get_file_type_object)

    file_type = get_file_type_from_stdout()
    read_first_line(file_type)

def test_filetype_from_open_file():
    def get_file_type_from_open_file(filename):
        try:
            with open(filename, 'rb') as fp:
                return _get_file_type(fp)
        except SandboxError:
            pass

        try:
            with open(filename, 'rb') as fp:
                return type(fp)
        except SandboxError:
            pass
        raise TestException("Unable to get file type")

    filename = READ_FILENAME

    config = createSandboxConfig()
    if config.cpython_restricted:
        # the CPython restricted mode denies to open any file
        raise SkipTest("require _sandbox")
    config.allowPath(filename)
    def get_file_type_object():
        file_type = get_file_type_from_open_file(filename)
        try:
            read_first_line(file_type)
        except TypeError, err:
            assert str(err) in ('object.__new__() takes no parameters', 'default __new__ takes no parameters')
        else:
            assert False

    Sandbox(config).call(get_file_type_object)

    file_type = get_file_type_from_open_file(filename)
    read_first_line(file_type)

def test_method_proxy():
    def get_file_type_from_stdout_method():
        import sys
        return _get_file_type(sys.stdout.__enter__())

    config = createSandboxConfig('stdout')
    def get_file_type_object():
        file_type = get_file_type_from_stdout_method()
        try:
            read_first_line(file_type)
        except TypeError, err:
            assert str(err) in ('object.__new__() takes no parameters', 'default __new__ takes no parameters')
        else:
            assert False
    Sandbox(config).call(get_file_type_object)

    file_type = get_file_type_from_stdout_method()
    read_first_line(file_type)

# TODO: enable this test on PyPy
@skipIf(HAVE_PYPY, "test disabled on PyPy")
def test_subclasses():
    if version_info >= (3, 0):
        raise SkipTest("Python 3 has not file type")

    def get_file_type_from_subclasses():
        for subtype in object.__subclasses__():
            if subtype.__name__ == "file":
                return subtype
        raise ValueError("Unable to get file type")

    def subclasses_denied():
        try:
            get_file_type_from_subclasses()
        except AttributeError, err:
            assert str(err) == "type object 'object' has no attribute '__subclasses__'"
        else:
            assert False
    createSandbox().call(subclasses_denied)

    file_type = get_file_type_from_subclasses()
    read_first_line(file_type)


########NEW FILE########
__FILENAME__ = test_proxy
from sandbox import HAVE_CSANDBOX, Sandbox, SandboxError
from sandbox.test import createSandbox, createSandboxConfig, SkipTest

def test_object_proxy_read():
    class Person:
        __doc__ = 'Person doc'

        def __str__(self):
            "Convert to string"
            return "str"

        def __repr__(self):
            return "repr"

        def __hash__(self):
            return 42

    person = Person()

    def testPerson(person):
        assert person.__doc__ == 'Person doc'

        assert person.__str__() == "str"
        assert person.__repr__() == "repr"
        assert person.__hash__() == 42

        assert person.__str__.__name__ == "__str__"
        assert person.__str__.__doc__ == "Convert to string"

    testPerson(person)

    sandbox = createSandbox()
    sandbox.call(testPerson, person)

class Person:
    def __init__(self, name):
        self.name = name

def test_object_proxy_setattr():
    # Attribute
    def setAttr(person):
        person.name = "victor"

    person = Person("haypo")
    sandbox = createSandbox()
    try:
        sandbox.call(setAttr, person)
    except SandboxError, err:
        assert str(err) == 'Read only object'
    else:
        assert False

    setAttr(person)
    assert person.name == "victor"

def test_object_proxy_delattr():
    # Delete attribute
    def delAttr(person):
        del person.name

    person = Person("haypo")
    sandbox = createSandbox()
    try:
        sandbox.call(delAttr, person)
    except SandboxError, err:
        assert str(err) == 'Read only object'
    else:
        assert False

    delAttr(person)
    assert hasattr(person, 'name') == False

def test_object_proxy_dict():
    if not HAVE_CSANDBOX:
        # restricted python blocks access to instance.__dict__
        raise SkipTest("require _sandbox")

    # Dictionary
    def setDict(person):
        person.__dict__['name'] = "victor"

    person = Person("haypo")
    sandbox = createSandbox()
    try:
        sandbox.call(setDict, person)
    except SandboxError, err:
        assert str(err) == 'Read only object'
    except RuntimeError, err:
        assert str(err) == 'instance.__dict__ not accessible in restricted mode'
    else:
        assert False

    setDict(person)
    assert person.name == "victor"

def test_proxy_module():
    def check_proxy_module():
        from sys import modules
        try:
            modules['sys']
        except SandboxError, err:
            assert str(err) == "Unable to proxy a value of type <type 'module'>"
        else:
            assert False

    config = createSandboxConfig()
    config.allowModule('sys', 'modules')
    sandbox = Sandbox(config)
    sandbox.call(check_proxy_module)


########NEW FILE########
__FILENAME__ = test_random
from sandbox import Sandbox
from sandbox.test import createSandboxConfig, SkipTest

def test_random():
    config = createSandboxConfig('random')
    if config.cpython_restricted:
        raise SkipTest("deny importing modules")

    check_random = 'import random; random.randint(1, 6)'

    Sandbox(config).execute(check_random)


########NEW FILE########
__FILENAME__ = test_recursion
from sandbox import Sandbox
from sandbox.test import createSandboxConfig

def test_recusion():
    def factorial(n):
        if n >= 2:
            return n * factorial(n - 1)
        else:
            return 1

    config = createSandboxConfig()
    max_frames = config.recusion_limit + 1
    try:
        Sandbox(config).call(factorial, max_frames)
    except RuntimeError, err:
        assert str(err) == 'maximum recursion depth exceeded'
    else:
        assert False

    factorial(max_frames)


########NEW FILE########
__FILENAME__ = test_restricted
from sandbox import Sandbox, HAVE_CPYTHON_RESTRICTED, HAVE_CSANDBOX, HAVE_PYPY
from sandbox.test import SkipTest, createSandboxConfig
from ._test_restricted import _test_restricted

if not HAVE_CPYTHON_RESTRICTED:
    raise SkipTest("restricted mode is specific to Python 2.x")

# TODO: enable these tests on PyPy
if HAVE_PYPY:
    raise SkipTest("test disabled on PyPy")

def test_frame_restricted():
    from sys import _getframe

    config = createSandboxConfig(cpython_restricted=True)
    def check_frame_restricted():
        frame = _getframe()
        assert frame.f_restricted == True
    Sandbox(config).call(check_frame_restricted)

    if HAVE_CSANDBOX:
        config = createSandboxConfig(cpython_restricted=False)
        def check_frame_not_restricted():
            frame = _getframe()
            assert frame.f_restricted == False
        Sandbox(config).call(check_frame_not_restricted)

    frame = _getframe()
    assert frame.f_restricted == False

def test_module_frame_restricted():
    from sys import _getframe

    config = createSandboxConfig(cpython_restricted=True)
    def check_module_restricted():
        restricted = _test_restricted(_getframe)
        assert restricted == True
    Sandbox(config).call(check_module_restricted)

    if HAVE_CSANDBOX:
        config = createSandboxConfig(cpython_restricted=False)
        def check_module_not_restricted():
            restricted = _test_restricted(_getframe)
            assert restricted == False
        Sandbox(config).call(check_module_not_restricted)


########NEW FILE########
__FILENAME__ = tools
from __future__ import with_statement
from os.path import join as path_join, basename, realpath
from glob import glob
from sys import version_info
import contextlib
from sandbox.test import SkipTest
import os

READ_FILENAME = realpath(__file__)
with open(READ_FILENAME, 'rb') as f:
    FIRST_LINE = f.readline()

if version_info >= (3, 0):
    # function for python2/python3 compatibility: bytes literal string
    def bytes_literal(text):
        return text.encode('ascii')
else:
    def bytes_literal(text):
        return text

def _getTests(module_dict, all_tests, keyword):
    _locals = module_dict.items()
    for name, value in _locals:
        if not name.startswith("test"):
            continue
        if keyword and (keyword not in name[4:]):
            continue
        all_tests.append(value)

def getTests(main_dict, keyword=None):
    all_tests = []
    _getTests(main_dict, all_tests, keyword)
    for filename in glob(path_join("sandbox", "test", "test_*.py")):
        # sandbox/test/test_bla.py => sandbox.test.bla
        module_name = basename(filename)[:-3]
        full_module_name = "sandbox.test.%s" % module_name
        try:
            parent_module = __import__(full_module_name)
        except SkipTest, skip:
            print("Skip %s: %s" % (module_name, skip))
            continue
        module = getattr(parent_module.test, module_name)
        _getTests(module.__dict__, all_tests, keyword)
    all_tests.sort(key=lambda func: func.__name__)
    return all_tests

def read_first_line(open):
    with open(READ_FILENAME, 'rb') as fp:
        line = fp.readline()
    assert line == FIRST_LINE

@contextlib.contextmanager
def capture_stdout():
    import sys
    import tempfile
    stdout_fd = sys.stdout.fileno()
    with tempfile.TemporaryFile(mode='w+b') as tmp:
        stdout_copy = os.dup(stdout_fd)
        try:
            sys.stdout.flush()
            os.dup2(tmp.fileno(), stdout_fd)
            yield tmp
        finally:
            sys.stdout.flush()
            os.dup2(stdout_copy, stdout_fd)
            os.close(stdout_copy)


########NEW FILE########
__FILENAME__ = _test_restricted
# module used by sandbox.test.test_restricted

def _test_restricted(_getframe):
    frame =  _getframe()
    return frame.f_restricted


########NEW FILE########
__FILENAME__ = version
PACKAGE = "pysandbox"
VERSION = "1.6"
LICENSE = "BSD (2-clause)"
URL = "http://github.com/haypo/pysandbox/"

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
from sandbox import HAVE_CSANDBOX
from sys import version_info
from sandbox.test import SkipTest, createSandboxConfig
from sandbox.test.tools import getTests
from sandbox.version import VERSION

def parseOptions():
    from optparse import OptionParser

    parser = OptionParser(usage="%prog [options]")
    parser.add_option("--raise",
        help="Don't catch exception",
        dest="raise_exception",
        action="store_true")
    parser.add_option("--debug",
        help="Enable debug mode (enable stdout and stderr features)",
        action="store_true")
    parser.add_option("-k", "--keyword",
        help="Only execute tests with name containing KEYWORD",
        type='str')
    options, argv = parser.parse_args()
    if argv:
        parser.print_help()
        exit(1)
    return options

def run_tests(options, use_subprocess, cpython_restricted):
    print("Run tests with cpython_restricted=%s and use_subprocess=%s"
          % (cpython_restricted, use_subprocess))
    print("")
    createSandboxConfig.cpython_restricted = cpython_restricted
    createSandboxConfig.use_subprocess = use_subprocess

    # Get all tests
    all_tests = getTests(globals(), options.keyword)

    # Run tests
    nerror = 0
    nskipped = 0
    if version_info < (2, 6):
        base_exception = Exception
    else:
        base_exception = BaseException
    for func in all_tests:
        name = '%s.%s()' % (func.__module__.split('.')[-1], func.__name__)
        if options.debug:
            print(name)
        try:
            func()
        except SkipTest, skip:
            print("%s: skipped (%s)" % (name, skip))
            nskipped += 1
        except base_exception, err:
            nerror += 1
            print("%s: FAILED! %r" % (name, err))
            if options.raise_exception:
                raise
        else:
            print "%s: ok" % name
    print("")
    return nskipped, nerror, len(all_tests)

def main():
    options = parseOptions()
    createSandboxConfig.debug = options.debug

    print("Run the test suite on pysandbox %s with Python %s.%s"
          % (VERSION, version_info[0], version_info[1]))
    if not HAVE_CSANDBOX:
        print("WARNING: _sandbox module is missing")
    print

    nskipped, nerrors, ntests = 0, 0, 0
    for use_subprocess in (False, True):
        for cpython_restricted in (False, True):
            result = run_tests(options, use_subprocess, cpython_restricted)
            nskipped += result[0]
            nerrors += result[1]
            ntests += result[2]
            if options.raise_exception and nerrors:
                break

    # Exit
    from sys import exit
    if nerrors:
        print("%s ERRORS!" % nerrors)
        exit(1)
    else:
        print("%s tests succeed (%s skipped)" % (ntests, nskipped))
        exit(0)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = test_restricted
# Module used by test_module_frame_restricted() from tests.py

def _test_restricted(_getframe):
    frame =  _getframe()
    return frame.f_restricted


########NEW FILE########
