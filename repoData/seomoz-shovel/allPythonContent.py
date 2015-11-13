__FILENAME__ = bar
from shovel import task

@task
def hello(name='Foo'):
    '''Prints "Hello, " followed by the provided name.
    
    Examples:
        shovel bar.hello
        shovel bar.hello --name=Erin
        http://localhost:3000/bar.hello?Erin'''
    print('Hello, %s' % name)

@task
def args(*args):
    '''Echos back all the args you give it.
    
    This exists mostly to demonstrate the fact that shovel
    is compatible with variable argument functions.
    
    Examples:
        shovel bar.args 1 2 3 4
        http://localhost:3000/bar.args?1&2&3&4'''
    for arg in args:
        print('You said "%s"' % arg)

@task
def kwargs(**kwargs):
    '''Echos back all the kwargs you give it.
    
    This exists mostly to demonstrate that shovel is
    compatible with the keyword argument functions.
    
    Examples:
        shovel bar.kwargs --foo=5 --bar 5 --howdy hey
        http://localhost:3000/bar.kwargs?foo=5&bar=5&howdy=hey'''
    for key, val in kwargs.items():
        print('You said "%s" => "%s"' % (key, val))
########NEW FILE########
__FILENAME__ = foo
from shovel import task

@task
def howdy(times=1):
    '''Just prints "Howdy" as many times as requests.
    
    Examples:
        shovel foo.howdy 10
        http://localhost:3000/foo.howdy?15'''
    print('\n'.join(['Howdy'] * int(times)))
########NEW FILE########
__FILENAME__ = bench
from shovel import task

@task
def data():
    '''This might run some test benchmark.
    
    Examples:
        shovel test.bench.data
        http://localhost:3000/test.bench.data'''
    return {
        'average': 5,
        'total'  : 7,
        'count'  : 100
    }

########NEW FILE########
__FILENAME__ = debug
from shovel import task

@task
def verbose():
    '''This just prints "Good news, everyone" 100 times.
    
    Examples:
    shovel test.debug.verbose
    http://localhost:3000/test.debug.verbose'''
    print('Good news, everyone!\n' * 100)

@task
def difference(a, b):
    '''Returns the difference between a and b, but only if a >= b.
    If a < b, then it raises an exception.
    
    Examples:
    shovel test.debug.difference 5 2
    shovel test.debug.difference 2 5
    http://localhost:3000/test.debug.difference?5&2 
    http://localhost:3000/test.debug.difference?a=2&b=5'''
    if int(a) < int(b):
        raise Exception('a must be greater than or equal to than b')
    else:
        return int(a) - int(b)

@task
def faily(*args, **kwargs):
    '''This always throws an exception, no matter what args you provide.
    
    Examples:
    shovel test.debug.faily
    http://localhost:3000/test.debug.faily'''
    raise Exception('I always fail!')
########NEW FILE########
__FILENAME__ = args
# Copyright (c) 2011-2014 Moz
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Argument -parsing and -evaluating tools'''

from __future__ import print_function

import inspect
from collections import namedtuple


ArgTuple = namedtuple('ArgTuple',
    ('required', 'overridden', 'defaulted', 'varargs', 'kwargs'))


class Args(object):
    '''Represents an argspec, and evaluates provided arguments to complete an
    invocation. It wraps an `argspec`, and provides some utility functionality
    around actually evaluating args and kwargs given that argspec.'''
    @classmethod
    def parse(cls, obj):
        '''Get the Args object associated with the argspec'''
        return cls(inspect.getargspec(obj))

    def __init__(self, spec):
        # We need to keep track of all our arguments and their defaults. Since
        # defaults are provided from the tail end of the positional args, we'll
        # reverse those and the defaults from the argspec and pair them. Then
        # we'll add the required positional arguments and get a list of all
        # args and whether or not they have defaults
        self._defaults = list(reversed(
            list(zip(reversed(spec.args or []), reversed(spec.defaults or [])))
        ))
        # Now, take all the args that don't have a default
        self._args = spec.args[:(len(spec.args) - len(self._defaults))]
        # Now our internal args is a list of tuples of variable
        # names and their corresponding default values
        self._varargs = spec.varargs
        self._kwargs = spec.keywords

    def __str__(self):
        results = []
        results.extend(self._args)
        results.extend('%s=%s' % (k, v) for k, v in self._defaults)
        if self._varargs:
            results.append('*%s' % self._varargs)
        if self._kwargs:
            results.append('**%s' % self._kwargs)
        return '(' + ', '.join(results) + ')'

    def explain(self, *args, **kwargs):
        '''Return a string that describes how these args are interpreted'''
        args = self.get(*args, **kwargs)
        results = ['%s = %s' % (name, value) for name, value in args.required]
        results.extend(['%s = %s (overridden)' % (
            name, value) for name, value in args.overridden])
        results.extend(['%s = %s (default)' % (
            name, value) for name, value in args.defaulted])
        if self._varargs:
            results.append('%s = %s' % (self._varargs, args.varargs))
        if self._kwargs:
            results.append('%s = %s' % (self._kwargs, args.kwargs))
        return '\n\t'.join(results)

    def get(self, *args, **kwargs):
        '''Evaluate this argspec with the provided arguments'''
        # We'll go through all of our required args and make sure they're
        # present
        required = [arg for arg in self._args if arg not in kwargs]
        if len(args) < len(required):
            raise TypeError('Missing arguments %s' % required[len(args):])
        required = list(zip(required, args))
        args = args[len(required):]

        # Now we'll look through our defaults, if there are any
        defaulted = [(name, default) for name, default in self._defaults
            if name not in kwargs]
        overridden = list(zip([d[0] for d in defaulted], args))
        args = args[len(overridden):]
        defaulted = defaulted[len(overridden):]

        # And anything left over is in varargs
        if args and not self._varargs:
            raise TypeError('Too many arguments provided')

        return ArgTuple(required, overridden, defaulted, args, kwargs)

########NEW FILE########
__FILENAME__ = help
# Copyright (c) 2011-2014 Moz
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Helpers for displaying help'''


import re
from shovel.tasks import Shovel


def heirarchical_helper(shovel, prefix, level=0):
    '''Return a list of tuples of (fullname, docstring, level) for all the
    tasks in the provided shovel'''
    result = []
    for key, value in sorted(shovel.map.items()):
        if prefix:
            key = prefix + '.' + key
        if isinstance(value, Shovel):
            result.append((key, None, level))
            result.extend(heirarchical_helper(value, key, level + 1))
        else:
            result.append((key, value.doc or '(No docstring)', level))
    return result


def heirarchical_help(shovel, prefix):
    '''Given a shovel of tasks, display a heirarchical list of the tasks'''
    result = []
    tuples = heirarchical_helper(shovel, prefix)
    if not tuples:
        return ''

    # We need to figure out the longest fullname length
    longest = max(len(name + '    ' * level) for name, _, level in tuples)
    fmt = '%%%is => %%-50s' % longest
    for name, docstring, level in tuples:
        if docstring == None:
            result.append('    ' * level + name + '/')
        else:
            docstring = re.sub(r'\s+', ' ', docstring).strip()
            if len(docstring) > 50:
                docstring = docstring[:47] + '...'
            result.append(fmt % (name, docstring))
    return '\n'.join(result)


def shovel_help(shovel, *names):
    '''Return a string about help with the tasks, or lists tasks available'''
    # If names are provided, and the name refers to a group of tasks, print out
    # the tasks and a brief docstring. Otherwise, just enumerate all the tasks
    # available
    if not len(names):
        return heirarchical_help(shovel, '')
    else:
        for name in names:
            task = shovel[name]
            if isinstance(task, Shovel):
                return heirarchical_help(task, name)
            else:
                return task.help()

########NEW FILE########
__FILENAME__ = parser
# Copyright (c) 2011-2014 Moz
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Helping functions for parsing CLI interface stuff'''


def parse(tokens):
    '''Parse the provided string to produce *args and **kwargs'''
    args = []
    kwargs = {}
    last = None
    for token in tokens:
        if token.startswith('--'):
            # If this is a keyword flag, but we've already got one that we've
            # parsed, then we're going to interpret it as a bool
            if last:
                kwargs[last] = True
            # See if it is the --foo=5 style
            last, _, value = token.strip('-').partition('=')
            if value:
                kwargs[last] = value
                last = None
        elif last != None:
            kwargs[last] = token
            last = None
        else:
            args.append(token)

    # If there's a dangling last, set that bool
    if last:
        kwargs[last] = True

    return args, kwargs

########NEW FILE########
__FILENAME__ = runner
# Copyright (c) 2011-2014 Moz
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import print_function

import logging
from .tasks import Shovel, Task
from .parser import parse
from . import help, logger


def run(*args):
    '''Run the normal shovel functionality'''
    import os
    import sys
    import argparse
    import pkg_resources
    # First off, read the arguments
    parser = argparse.ArgumentParser(description='Rake, for Python')

    parser.add_argument('method', help='The task to run')
    parser.add_argument('--verbose', dest='verbose', action='store_true',
        help='Be extra talkative')
    parser.add_argument('--dry-run', dest='dryRun', action='store_true',
        help='Show the args that would be used')

    ver = pkg_resources.require('shovel')[0].version
    parser.add_argument('--version', action='version',
        version='Shovel v %s' % ver, help='print the version of Shovel.')

    # Parse our arguments
    if args:
        clargs, remaining = parser.parse_known_args(args=args)
    else:  # pragma: no cover
        clargs, remaining = parser.parse_known_args()

    if clargs.verbose:
        logger.setLevel(logging.DEBUG)

    args, kwargs = parse(remaining)

    # Import all of the files we want
    shovel = Shovel()

    # Read in any tasks that have already been defined
    shovel.extend(Task.clear())

    for path in [
        os.path.expanduser('~/.shovel.py'),
        os.path.expanduser('~/.shovel')]:
        if os.path.exists(path):  # pragma: no cover
            shovel.read(path, os.path.expanduser('~/'))

    for path in ['shovel.py', 'shovel']:
        if os.path.exists(path):
            shovel.read(path)

    # If it's help we're looking for, look no further
    if clargs.method == 'help':
        print(help.shovel_help(shovel, *args, **kwargs))
    elif clargs.method == 'tasks':
        tasks = list(v for _, v in shovel.items())
        if not tasks:
            print('No tasks found!')
        else:
            names = list(t.fullname for t in tasks)
            docs = list(t.doc for t in tasks)

            # The width of the screen
            width = 80
            import shutil
            try:
                width, _ = shutil.get_terminal_size(fallback=(0, width))
            except AttributeError:
                pass

            # Create the format with padding for the longest name, and to
            # accomodate the screen width
            format = '%%-%is # %%-%is' % (
                max(len(name) for name in names), width)
            for name, doc in zip(names, docs):
                print(format % (name, doc))
    elif clargs.method:
        # Try to get the first command provided
        try:
            tasks = shovel.tasks(clargs.method)
        except KeyError:
            print('Could not find task "%s"' % clargs.method, file=sys.stderr)
            exit(1)

        if len(tasks) > 1:
            print('Specifier "%s" matches multiple tasks:' % clargs.method, file=sys.stderr)
            for task in tasks:
                print('\t%s' % task.fullname, file=sys.stderr)
            exit(2)

        task = tasks[0]
        if clargs.dryRun:
            print(task.dry(*args, **kwargs))
        else:
            task(*args, **kwargs)

########NEW FILE########
__FILENAME__ = tasks
# Copyright (c) 2011-2014 Moz
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Task helper'''

import os
import imp
import sys
import inspect
from collections import defaultdict

# Internal imports
from shovel import logger
from shovel.args import Args


def task(func):
    '''Register this task with shovel, but return the original function'''
    Task.make(func)
    return func


class Shovel(object):
    '''A collection of tasks contained in a file or folder'''
    @classmethod
    def load(cls, path, base=None):
        '''Either load a path and return a shovel object or return None'''
        obj = cls()
        obj.read(path, base)
        return obj

    def __init__(self, tasks=None):
        self.overrides = None
        self._tasks = tasks or []
        self.map = defaultdict(Shovel)
        self.extend(tasks or [])

    def extend(self, tasks):
        '''Add tasks to this particular shovel'''
        self._tasks.extend(tasks)
        for task in tasks:
            # We'll now go through all of our tasks and group them into
            # sub-shovels
            current = self.map
            modules = task.fullname.split('.')
            for module in modules[:-1]:
                if not isinstance(current[module], Shovel):
                    logger.warn('Overriding task %s with a module' %
                        current[module].file)
                    shovel = Shovel()
                    shovel.overrides = current[module]
                    current[module] = shovel
                current = current[module].map

            # Now we'll put the task in this particular sub-shovel
            name = modules[-1]
            if name in current:
                logger.warn('Overriding %s with %s' % (
                    '.'.join(modules), task.file))
                task.overrides = current[name]
            current[name] = task

    def read(self, path, base=None):
        '''Import some tasks'''
        if base == None:
            base = os.getcwd()
        absolute = os.path.abspath(path)
        if os.path.isfile(absolute):
            # Load that particular file
            logger.info('Loading %s' % absolute)
            self.extend(Task.load(path, base))
        elif os.path.isdir(absolute):
            # Walk this directory looking for tasks
            tasks = []
            for root, _, files in os.walk(absolute):
                files = [f for f in files if f.endswith('.py')]
                for child in files:
                    absolute = os.path.join(root, child)
                    logger.info('Loading %s' % absolute)
                    tasks.extend(Task.load(absolute, base))
            self.extend(tasks)

    def __getitem__(self, key):
        '''Find a task with the provided name'''
        current = self.map
        split = key.split('.')
        for module in split[:-1]:
            if module not in current:
                raise KeyError('Module not found')
            current = current[module].map
        if split[-1] not in current:
            raise KeyError('Task not found')
        return current[split[-1]]

    def __contains__(self, key):
        try:
            return bool(self.__getitem__(key))
        except KeyError:
            return False

    def keys(self):
        '''Return all valid keys'''
        keys = []
        for key, value in self.map.items():
            if isinstance(value, Shovel):
                keys.extend([key + '.' + k for k in value.keys()])
            else:
                keys.append(key)
        return sorted(keys)

    def items(self):
        '''Return a list of tuples of all the keys and tasks'''
        pairs = []
        for key, value in self.map.items():
            if isinstance(value, Shovel):
                pairs.extend([(key + '.' + k, v) for k, v in value.items()])
            else:
                pairs.append((key, value))
        return sorted(pairs)

    def tasks(self, name):
        '''Get all the tasks that match a name'''
        found = self[name]
        if isinstance(found, Shovel):
            return [v for _, v in found.items()]
        return [found]


class Task(object):
    '''An object representative of a task'''
    # There's an interesting problem associated with this process of loading
    # tasks from a file. We invoke it with a 'load', but then we get access to
    # the tasks through decorators. As such, the decorator just accumulates
    # the tasks that it has seen as it creates them, puts them in a cache, and
    # eventually that cache will be consumed as a usable object. This is that
    # cache. Put another way:
    #
    #   1. Clear cache
    #   2. Load module
    #   3. Fill cache with tasks created with @task
    #   4. Once loaded, organize the cached tasks
    _cache = []
    # This is to help find tasks given their path
    _tasks = {}

    @classmethod
    def make(cls, obj):
        '''Given a callable object, return a new callable object'''
        try:
            cls._cache.append(Task(obj))
        except Exception:
            logger.exception('Unable to make task for %s' % repr(obj))

    @classmethod
    def load(cls, path, base=None):
        '''Return a list of the tasks stored in a file'''
        base = base or os.getcwd()
        absolute = os.path.abspath(path)
        parent = os.path.dirname(absolute)
        name, _, _ = os.path.basename(absolute).rpartition('.py')
        fobj, path, description = imp.find_module(name, [parent])
        try:
            imp.load_module(name, fobj, path, description)
        finally:
            if fobj:
                fobj.close()
        # Manipulate the full names of the tasks to be relative to the provided
        # base
        relative, _, _ = os.path.relpath(path, base).rpartition('.py')
        for task in cls._cache:
            parts = relative.split(os.path.sep)
            parts.append(task.name)
            # If it's either in shovel.py, or folder/__init__.py, then we
            # should consider it as being at one level above that file
            parts = [part.strip('.') for part in parts if part not in
                ('shovel', '.shovel', '__init__', '.', '..', '')]
            task.fullname = '.'.join(parts)
            logger.debug('Found task %s in %s' % (task.fullname, task.module))
        return cls.clear()

    @classmethod
    def clear(cls):
        '''Clear and return the cache'''
        cached = cls._cache
        cls._cache = []
        return cached

    def __init__(self, obj):
        if not callable(obj):
            raise TypeError('Object not callable: %s' % obj)

        # Save some attributes about the task
        self.name = obj.__name__
        self.doc = inspect.getdoc(obj) or ''

        # If the provided object is a type (like a class), we'll treat
        # it a little differently from if it's a pure function. The
        # assumption is that the class will be instantiated wit no
        # arguments, and then called with the provided arguments
        if isinstance(obj, type):
            try:
                self._obj = obj()
            except:
                raise TypeError(
                    '%s => Task classes must take no arguments' % self.name)
            self.spec = inspect.getargspec(self._obj.__call__)
            self.doc = inspect.getdoc(self._obj.__call__) or self.doc
            self.line = 'Unknown line'
            self.file = 'Unknown file'
        else:
            self.spec = inspect.getargspec(obj)
            self._obj = obj
            self.line = obj.__code__.co_firstlineno
            self.file = obj.__code__.co_filename

        self.module = self._obj.__module__
        self.fullname = self.name

        # What module / etc. this overrides, if any
        self.overrides = None

    def __call__(self, *args, **kwargs):
        '''Invoke the task itself'''
        try:
            return self._obj(*args, **kwargs)
        except Exception as exc:
            logger.exception('Failed to run task %s' % self.name)
            raise(exc)

    def capture(self, *args, **kwargs):
        '''Run a task and return a dictionary with stderr, stdout and the
        return value. Also, the traceback from the exception if there was
        one'''
        import traceback
        try:
            from StringIO import StringIO
        except ImportError:
            from io import StringIO
        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout = out = StringIO()
        sys.stderr = err = StringIO()
        result = {
            'exception': None,
            'stderr': None,
            'stdout': None,
            'return': None
        }
        try:
            result['return'] = self.__call__(*args, **kwargs)
        except Exception:
            result['exception'] = traceback.format_exc()
        sys.stdout, sys.stderr = stdout, stderr
        result['stderr'] = err.getvalue()
        result['stdout'] = out.getvalue()
        return result

    def dry(self, *args, **kwargs):
        '''Perform a dry-run of the task'''
        return 'Would have executed:\n%s%s' % (
            self.name, Args(self.spec).explain(*args, **kwargs))

    def help(self):
        '''Return the help string of the task'''
        # This returns a help string for a given task of the form:
        #
        # ==================================================
        # <name>
        # ============================== (If supplied)
        # <docstring>
        # ============================== (If overrides other tasks)
        # Overrides <other task file>
        # ==============================
        # From <file> on <line>
        # ==============================
        # <name>(Argspec)
        result = [
            '=' * 50,
            self.name
        ]

        # And the doc, if it exists
        if self.doc:
            result.extend([
                '=' * 30,
                self.doc
            ])

        override = self.overrides
        while override:
            if isinstance(override, Shovel):
                result.append('Overrides module')
            else:
                result.append('Overrides %s' % override.file)
            override = override.overrides

        # Print where we read this function in from
        result.extend([
            '=' * 30,
            'From %s on line %i' % (self.file, self.line),
            '=' * 30,
            '%s%s' % (self.name, str(Args(self.spec)))
        ])
        return os.linesep.join(result)

########NEW FILE########
__FILENAME__ = shovel
from shovel import task

@task
def hello(name):
    '''Prints hello and the provided name'''
    print('Hello, %s!' % name)

@task
def sumnum(*args):
    '''Computes the sum of the provided numbers'''
    print('%s = %f' % (' + '.join(args), sum(float(arg) for arg in args)))

@task
def attributes(name, **kwargs):
    '''Prints a name, and all keyword attributes'''
    print('%s has attributes:' % name)
    for key, value in kwargs.items():
        print('\t%s => %s' % (key, value))

########NEW FILE########
__FILENAME__ = shovel
'''Shovel tasks strictly for tests'''

from shovel import task


@task
def widget(arg, whiz, bang):
    '''This is a dummy task'''
    return arg + whiz + bang

########NEW FILE########
__FILENAME__ = one
from shovel import task


# This task is intentionally missing a docstring
@task
def foo():
    pass

########NEW FILE########
__FILENAME__ = foo
'''Dummy shovel tasks for testing'''

from shovel import task


@task
def widget():
    '''A dummy function'''
    pass

########NEW FILE########
__FILENAME__ = one
'''Dummy shovel tasks for testing'''

from shovel import task


@task
def widget():
    '''A dummy function'''
    pass

########NEW FILE########
__FILENAME__ = two
'''Dummy shovel tasks for testing'''

from shovel import task


@task
def widget():
    '''long doc, long doc, long doc, long doc, long doc, long doc, long doc, '''
    pass

########NEW FILE########
__FILENAME__ = foo
from shovel import task


@task
def bar():
    '''Dummy function'''
    pass

########NEW FILE########
__FILENAME__ = shovel
'''Dummy shovel tasks for testing'''

from __future__ import print_function

from shovel import task


@task
def bar():
    '''Dummy function'''
    print('Hello from bar!')

########NEW FILE########
__FILENAME__ = whiz
'''Dummy shovel tasks for testing'''

from __future__ import print_function

from shovel import task


@task
def bar():
    '''Dummy function'''
    print('Hello from bar!')


@task
def foo():
    '''Dummy function'''
    print('Hello from foo!')

########NEW FILE########
__FILENAME__ = none

########NEW FILE########
__FILENAME__ = .shovel
from shovel import task

@task
def bar():
    pass

########NEW FILE########
__FILENAME__ = shovel
from shovel import task

@task
def foo():
    pass

########NEW FILE########
__FILENAME__ = test_args
#! /usr/bin/env python

'''Ensure our args utilities work'''

import unittest
from shovel.args import Args


class TestArgs(unittest.TestCase):
    '''Test our argspec wrapper'''
    def test_basic(self):
        '''Give it a low-ball function'''
        def foo(a, b, c):
            pass

        args = Args.parse(foo)
        self.assertEqual(args.get(1, 2, 3).required, [
            ('a', 1), ('b', 2), ('c', 3)])
        self.assertEqual(args.get(1, 2, c=3).required, [
            ('a', 1), ('b', 2)])

    def test_default(self):
        '''We should be able to figure out defaults and overrides'''
        def foo(a, b, c=3, d=6):
            pass

        args = Args.parse(foo)
        self.assertEqual(args.get(1, 2).defaulted, [
            ('c', 3), ('d', 6)])
        self.assertEqual(args.get(1, 2, 4).defaulted, [
            ('d', 6)])
        self.assertEqual(args.get(1, 2, 4).overridden, [
            ('c', 4)])
        self.assertEqual(args.get(1, 2, c=4).defaulted, [
            ('d', 6)])

    def test_varargs(self):
        '''Oh, and varargs'''
        def foo(a, b, c=3, *d):
            pass

        args = Args.parse(foo)
        self.assertEqual(args.get(1, 2).varargs, ())
        self.assertEqual(args.get(1, 2, 3).varargs, ())
        self.assertEqual(args.get(1, 2, 3, 4, 5).varargs, (4, 5))

    def test_kwargs(self):
        '''We should also be able to use kwargs'''
        def foo(a, b, c=3, *d, **kwargs):
            pass

        args = Args.parse(foo)
        self.assertEqual(args.get(1, 2).kwargs, {})
        self.assertEqual(args.get(1, 2, 3).kwargs, {})
        self.assertEqual(args.get(1, 2, 3, 4, 5).kwargs, {})
        self.assertEqual(args.get(1, 2, 3, 4, 5, c=3, g=4).kwargs, {
            'c': 3, 'g': 4
        })

    def test_error(self):
        '''Giving too many or too few args should raise an error'''
        def foo(a, b, c):
            pass

        args = Args.parse(foo)
        self.assertRaises(Exception, args.get, 1, 2)
        self.assertRaises(Exception, args.get, 1, 2, 3, 4)

    def test_str_basic(self):
        '''Gets a representation of a basic function'''
        def foo(a, b=2):
            pass

        self.assertEqual(str(Args.parse(foo)), '(a, b=2)')

    def test_str_complex(self):
        '''Gets a representation of a more complex function'''
        def foo(a, b=2, *args, **kwargs):
            pass

        self.assertEqual(str(Args.parse(foo)), '(a, b=2, *args, **kwargs)')

    def test_explain(self):
        '''Gets a description of how arguments are applied'''
        def foo(a, b=2, *args, **kwargs):
            pass

        actual = [line.strip() for line in
            Args.parse(foo).explain(5, 3, 15, bar=20).split('\n')]
        expected = [
            'a = 5',
            'b = 3 (overridden)',
            'args = (15,)',
            'kwargs = {\'bar\': 20}']
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_help
#! /usr/bin/env python

'''Ensure our help messages work'''

import unittest

import os
from shovel import help
from shovel.tasks import Shovel


class TestHelp(unittest.TestCase):
    '''Make sure our help messages work'''
    def setUp(self):
        self.shovel = Shovel.load(
            'test/examples/help/', 'test/examples/help/')

    def test_heirarchical_helper(self):
        '''Gets all the help tuples we'd expect'''
        expected = [
            ('one', None, 0),
            ('one.widget', 'A dummy function', 1),
            ('two', None, 0),
            ('two.widget', 'long doc, ' * 7, 1)]
        self.assertEqual(help.heirarchical_helper(self.shovel, ''), expected)

    def test_heirarchical_help(self):
        '''Gets the help message we'd expect from heirarchical_help'''
        actual = [line.strip() for line in
            help.heirarchical_help(self.shovel, '').split('\n')]
        expected = [
            'one/',
            'one.widget => A dummy function',
            'two/',
            'two.widget => long doc, long doc, long doc, long doc, long do...']
        self.assertEqual(actual, expected)

    def test_shovel_help_basic(self):
        '''Gets the help message we'd expect from shovel_help for all tasks'''
        actual = [line.strip() for line in
            help.shovel_help(self.shovel).split('\n')]
        expected = [
            'one/',
            'one.widget => A dummy function',
            'two/',
            'two.widget => long doc, long doc, long doc, long doc, long do...']
        self.assertEqual(actual, expected)

    def test_shovel_help_specific_tasks(self):
        '''Gets the help message we'd expect from shovel_help for tasks'''
        actual = [line.strip() for line in
            help.shovel_help(self.shovel, 'two').split('\n')]
        expected = [
            'two.widget => long doc, long doc, long doc, long doc, long do...']
        self.assertEqual(actual, expected)

    def test_shovel_help_specific_task(self):
        '''Gets the help message we'd expect from shovel_help for a task'''
        actual = [line.strip() for line in
            help.shovel_help(self.shovel, 'two.widget').split('\n')]
        # We need to replace absolute paths in the test
        actual = [line.replace(os.getcwd(), '') for line in actual]
        expected = [
            '==================================================',
            'widget',
            '==============================',
            ('long doc, ' * 7).strip(),
            '==============================',
            'From /test/examples/help/two.py on line 6',
            '==============================',
            'widget()']
        self.assertEqual(actual, expected)

    def test_help_missing_docstring(self):
        '''We should print '(No docstring)' for tasks missing a docstring'''
        shovel = Shovel.load(
            'test/examples/docstring/', 'test/examples/docstring/')
        actual = [line.strip() for line in help.shovel_help(shovel).split('\n')]
        expected = ['one/', 'one.foo => (No docstring)']
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_parse
#! /usr/bin/env python

'''Ensure our CLI parsing works'''

import unittest
from shovel.parser import parse


class TestParse(unittest.TestCase):
    '''Test our argspec wrapper'''
    def test_basic(self):
        '''A few low-ball examples'''
        args, kwargs = parse('1 2 3 4 5'.split(' '))
        self.assertEqual(args, ['1', '2', '3', '4', '5'])
        self.assertEqual(kwargs, {})

        # Make sure we handle bool flags
        args, kwargs = parse('--foo --bar --whiz'.split(' '))
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {'foo': True, 'bar': True, 'whiz': True})

        # Make sure we can handle interleaved positional and keyword args
        args, kwargs = parse('1 --foo 5 2 3'.split(' '))
        self.assertEqual(args, ['1', '2', '3'])
        self.assertEqual(kwargs, {'foo': '5'})

        # Make sure we can handle '--foo=6'
        args, kwargs = parse('1 --foo=5'.split(' '))
        self.assertEqual(args, ['1'])
        self.assertEqual(kwargs, {'foo': '5'})


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_run
#! /usr/bin/env python

'''Ensure the `run` method works'''

import unittest

from contextlib import contextmanager
import logging
import os
from path import path
import shovel
import sys
try:
    from cStringIO import StringIO
except ImportError:  # pragma: no cover
    # Python 3 support
    from io import StringIO


@contextmanager
def capture(stream='stdout'):
    original = getattr(sys, stream)
    setattr(sys, stream, StringIO())
    yield(getattr(sys, stream))
    setattr(sys, stream, original)


@contextmanager
def logs():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    shovel.logger.addHandler(handler)
    yield(stream)
    handler.flush()
    shovel.logger.removeHandler(handler)


class TestRun(unittest.TestCase):
    '''Test our `run` method'''
    def stdout(self, pth, *args, **kwargs):
        with path(pth):
            with capture() as out:
                shovel.run(*args, **kwargs)
            return [line.strip() for line in
                out.getvalue().strip().split('\n')]

    def stderr(self, pth, *args, **kwargs):
        with path(pth):
            with capture('stderr') as out:
                shovel.run(*args, **kwargs)
            return [line.strip() for line in
                out.getvalue().strip().split('\n')]

    def logs(self, pth, *args, **kwargs):
        with path(pth):
            with logs() as out:
                shovel.run(*args, **kwargs)
            return [line.strip() for line in
                out.getvalue().strip().split('\n')]

    def test_basic(self):
        '''We should be able to run a command'''
        actual = self.stdout('test/examples/run/basic', 'bar')
        expected = [
            'Hello from bar!']
        self.assertEqual(actual, expected)

    def test_basic_help(self):
        '''Can run a basic example'''
        actual = self.stdout('test/examples/run/basic', 'help')
        expected = [
            'bar => Dummy function']
        self.assertEqual(actual, expected)

    def test_verbose(self):
        '''Can be run in verbose mode'''
        actual = self.logs('test/examples/run/basic', 'bar', '--verbose')
        # We have to replace absolue paths with relative ones
        actual = [line.replace(os.getcwd(), '') for line in actual]
        expected = [
            'Loading /test/examples/run/basic/shovel.py',
            'Found task bar in shovel']
        self.assertEqual(actual, expected)

    def test_task_missing(self):
        '''Exits if the task is missing'''
        self.assertRaises(
            SystemExit, self.stderr, 'test/examples/run/basic', 'whiz')

    def test_too_many_tasks(self):
        '''Exits if there are too many matching tasks'''
        self.assertRaisesRegexp(
            SystemExit, '2', self.stderr, 'test/examples/run/multiple', 'whiz')

    def test_dry_run(self):
        '''Honors the dry-run flag'''
        actual = self.stdout(
            'test/examples/run/basic', 'bar', '--dry-run')
        expected = ['Would have executed:', 'bar']
        self.assertEqual(actual, expected)

    def test_tasks(self):
        '''Make sure we can enumerate tasks'''
        actual = self.stdout(
            'test/examples/run/basic', 'tasks')
        expected = ['bar # Dummy function']
        self.assertEqual(actual, expected)

    def test_tasks_none_found(self):
        '''Display the correct thing when no tasks are found'''
        actual = self.stdout('test/examples/run/none', 'tasks')
        expected = ['No tasks found!']
        self.assertEqual(actual, expected)

########NEW FILE########
__FILENAME__ = test_task
#! /usr/bin/env python

'''Ensure that we can correctly find tasks'''

import unittest
from shovel.tasks import Shovel, Task


class TestTask(unittest.TestCase):
    '''Test our ability to find and correctly reference tasks'''
    def test_basic(self):
        '''Ensure that we can get all the basic tasks in a shovel file'''
        shovel = Shovel.load('test/examples/basic/shovel.py',
            'test/examples/basic')
        self.assertNotEqual(shovel, None)
        self.assertTrue('widget' in shovel)

    def test_folder(self):
        '''Ensure we can import from a folder structure'''
        shovel = Shovel.load('test/examples/folder/', 'test/examples/folder/')
        self.assertNotEqual(shovel, None)
        self.assertTrue('foo.widget' in shovel)

    def test_init(self):
        '''Ensure we can recognize things in __init__ correctly'''
        shovel = Shovel.load('test/examples/init/', 'test/examples/init/')
        self.assertNotEqual(shovel, None)
        self.assertTrue('widget' in shovel)

    def test_nested(self):
        '''Ensure we can do nested loading'''
        shovel = Shovel.load('test/examples/nested/', 'test/examples/nested/')
        self.assertNotEqual(shovel, None)
        examples = [
            'foo.bar',
            'foo.whiz',
            'foo.baz.hello',
            'foo.baz.howdy.what'
        ]
        for example in examples:
            self.assertTrue(example in shovel)

    def test_override(self):
        '''Ensure we can track overrides from one file or another'''
        shovel = Shovel()
        for name in ['one', 'two']:
            pth = 'test/examples/overrides/%s' % name
            shovel.read(pth, pth)
        self.assertNotEqual(shovel, None)
        self.assertNotEqual(shovel['foo.bar'].overrides, None)

    def test_keys_items(self):
        '''Shovels should provide a list of all the tasks they know about'''
        shovel = Shovel.load('test/examples/nested/', 'test/examples/nested/')
        keys = [
            'foo.bar',
            'foo.whiz',
            'foo.baz.hello',
            'foo.baz.howdy.what'
        ]
        self.assertEqual(set(shovel.keys()), set(keys))
        for key, pair in zip(sorted(keys), sorted(shovel.items())):
            self.assertEqual(key, pair[0])
            self.assertEqual(key, pair[1].fullname)

    def test_multi_load(self):
        '''Load from multiple paths'''
        shovel = Shovel()
        shovel.read('test/examples/multiple/one/',
            'test/examples/multiple/one/')
        shovel.read('test/examples/multiple/two/',
            'test/examples/multiple/two/')
        keys = [
            'whiz', 'bar.bar'
        ]
        self.assertEqual(set(shovel.keys()), set(keys))

    def test_errors(self):
        '''Make sure getting non-existant tasks throws errors'''
        shovel = Shovel()
        self.assertRaises(KeyError, shovel.__getitem__, 'foo.bar.whiz')
        self.assertRaises(KeyError, shovel.__getitem__, 'foo')
        self.assertFalse('foo' in shovel)

        # We can't have functor classes that take arguments
        shovel.read('test/examples/errors/')
        self.assertFalse('Foo' in shovel)

        self.assertRaises(TypeError, Task, 'foo')

    def test_classes(self):
        '''We should be able to also use functor classes'''
        shovel = Shovel.load('test/examples/classes', 'test/examples/classes')
        self.assertTrue('Foo' in shovel)
        self.assertEqual(shovel['Foo'](5), 5)
        self.assertRaises(TypeError, shovel['Bar'], 5)

    def test_capture(self):
        '''Make sure we can capture output from a function'''
        shovel = Shovel.load('test/examples/capture/', 'test/examples/capture')
        self.assertEqual(shovel['foo'].capture(1, 2, 3), {
            'stderr': '',
            'stdout': 'foo\n',
            'return': 6,
            'exception': None
        })
        self.assertNotEqual(shovel['bar'].capture()['exception'], None)

    def test_atts(self):
        '''Make sure some of the attributes are what we expect'''
        shovel = Shovel.load('test/examples/capture/', 'test/examples/capture')
        task = shovel['foo']
        self.assertEqual(task.doc, 'Dummy function')

    def test_tasks(self):
        '''We should be able to get a list of all tasks that match a path'''
        shovel = Shovel.load('test/examples/tasks/', 'test/examples/tasks/')
        self.assertEqual(set(t.fullname for t in shovel.tasks('foo')),
            set(('foo.bar', 'foo.whiz')))

    def test_help(self):
        '''Just make sure that help doesn't blow up on us'''
        shovel = Shovel.load('test/examples/overrides/',
            'test/examples/overrides/')
        _, tasks = zip(*shovel.items())
        self.assertGreater(len(tasks), 0)
        for task in tasks:
            self.assertNotEqual(task.help(), '')

    def test_dry_run(self):
        '''Make sure that dry runs don't blow up on us'''
        shovel = Shovel.load('test/examples/multiple/',
            'test/examples/multiple/')
        _, tasks = zip(*shovel.items())
        self.assertGreater(len(tasks), 0)
        for task in tasks:
            self.assertNotEqual(task.dry(), '')

    def test_shovel(self):
        '''For shovel/*, shovel.py, .shovel/* and .shovel.py, tasks should be
        top-level'''
        shovel = Shovel.load('test/examples/toplevel/one',
            'test/examples/toplevel/one')
        _, tasks = zip(*shovel.items())
        # self.assertEqual(len(tasks), 4)
        self.assertEqual(set([t.fullname for t in tasks]),
            set(['whiz', 'bang']))

        shovel = Shovel.load('test/examples/toplevel/two',
            'test/examples/toplevel/two')
        _, tasks = zip(*shovel.items())
        self.assertEqual(set([t.fullname for t in tasks]),
            set(['foo', 'bar']))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
