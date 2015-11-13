__FILENAME__ = chronic
"""
Chronic is a module designed to do simple profiling of your python code while
giving you full control of the granularity of measurement.  It maintains the
hierarchy of the call tree, but only at the levels you care about.  The timing
results can easily be captured as JSON and logged for analysis in postgres or
mongodb.

You may use the @time decorator or the Timer context manager:

>>> @time
>>> def func():
>>>     with Timer('bar'):
>>>         pass
>>> func()
>>> timings
{
    'func': {
        'total_elapsed': 38.5,
        'count': 1,
        'average_elapsed': 38.5
        'timings': {
            'bar': {
                'total_elapsed': 20.52,
                'count': 1
                'average_elapsed': 20.52
            }
        }
    }
}

"""

import sys
import time as systime
import threading
from functools import partial, wraps

from signals import Signal
from proxy import Proxy


_local = threading.local()
if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    _clock = systime.clock
else:
    # On most other platforms the best timer is time.time()
    _clock = systime.time
post_timing = Signal(name='post timing')


class Timer(object):
    '''A context manager for timing blocks of code.

    Use chronic.timings to obtain the results.

    Arguments:
    name -- A unique name for the timing.
    clock -- A function that returns the current time.  Mostly for testing,
             default is the system clock.
    '''
    def __init__(self, name, clock=None):
        self.name = name
        self._clock = clock if clock is not None else _clock

    def _push(self):
        if not hasattr(_local, 'stopwatch'):
            _local.stopwatch = {'current': {}, 'stack': []}
        current = _local.stopwatch['current']
        _local.stopwatch['stack'].append((self.name, current))
        current['timings'] = current.get('timings', {})
        current['timings'][self.name] = current['timings'].get(self.name, {})
        new = current['timings'][self.name]
        _local.stopwatch['current'] = new

    def _pop(self):
        _, last = _local.stopwatch['stack'].pop()
        _local.stopwatch['current'] = last

    def __enter__(self):
        self._push()
        self.start = self._clock()

    def __exit__(self, type, val, tb):
        elapsed = self._clock() - self.start
        current = _local.stopwatch['current']
        current['total_elapsed'] = elapsed + current.get('total_elapsed', 0)
        current['count'] = 1 + current.get('count', 0)
        current['average_elapsed'] = (current['total_elapsed'] /
                                      current['count'])
        current_stack = stack
        self._pop()
        post_timing.emit(elapsed, current, current_stack)


def time(func=None, name=None, clock=None):
    '''A decorator for timing function calls.

    Use chronic.timings to obtain the results.

    Arguments:
    name -- A unique name for the timing.  Defaults to the function name.
    clock -- A function that returns the current time.  Mostly for testing,
             default is the system clock.
    '''

    # When this decorator is used with optional parameters:
    #
    #   @time(name='timed_thing')
    #   def func():
    #       pass
    #
    # The result of this decorator should be a function which will receive
    # the function to wrap as an argument, and return the wrapped function.
    if func is None:
        return partial(time, name=name, clock=clock)

    @wraps(func)
    def _inner(*args, **kws):
        with Timer(name or func.__name__, clock=clock):
            result = func(*args, **kws)
        return result
    return _inner


def _get_timings():
    if hasattr(_local, 'stopwatch'):
        return _local.stopwatch['current'].get('timings', {})


def _get_stack():
    if hasattr(_local, 'stopwatch'):
        return tuple(name for name, _ in _local.stopwatch['stack'])


timings = Proxy(_get_timings, doc='''This variable always holds all completed
timing information for the current scope.  Information is available as a dict
with a key for each timing (the name of the timer).  The value of each timing
is a dict with three keys:
    * total_elapsed: the elapsed execution time of the code (including all
      subtimings) for all runs of this block.  The unit is seconds by default.
      If you pass in your own clock function, the unit is whatever the unit of
      the clock.
    * count: the number of times the timed block was run.
    * average_elapsed: the average elapsed time for each run of this block.
    * timings: a dict of all subtimings that were completed while inside this
      block
''')
stack = Proxy(_get_stack)


def clear():
    _local.stopwatch = {'current': {}, 'stack': []}

########NEW FILE########
__FILENAME__ = proxy
'''
A proxy class, useful for making module level variables backed by getter
functions.

This is a slightly modified version of Werkzeug's LocalProxy class,
which is copyright (c) 2011 by the Werkzeug Team.  See LICENSE for details.
'''


class Proxy(object):
    """Forwards all operations to a proxied object.  The only operations not
    supported for forwarding are right handed operands and any kind of
    assignment.
    """
    def __init__(self, getter, doc=None):
        object.__setattr__(self, '_Proxy__getter', getter)
        object.__setattr__(self, '__doc__', doc)

    def _get_current_object(self):
        """Return the current object.  This is useful if you want the real
        object behind the proxy at a time for performance reasons or because
        you want to pass the object into a different context.
        """
        return self.__getter()

    def __call__(self):
        return self

    @property
    def __dict__(self):
        try:
            return self._get_current_object().__dict__
        except RuntimeError:
            raise AttributeError('__dict__')

    def __repr__(self):
        try:
            obj = self._get_current_object()
        except RuntimeError:
            return '<%s unbound>' % self.__class__.__name__
        return repr(obj)

    def __nonzero__(self):
        try:
            return bool(self._get_current_object())
        except RuntimeError:
            return False

    def __unicode__(self):
        try:
            return unicode(self._get_current_object())
        except RuntimeError:
            return repr(self)

    def __dir__(self):
        try:
            return dir(self._get_current_object())
        except RuntimeError:
            return []

    def __getattr__(self, name):
        if name == '__members__':
            return dir(self._get_current_object())
        return getattr(self._get_current_object(), name)

    def __setitem__(self, key, value):
        self._get_current_object()[key] = value

    def __delitem__(self, key):
        del self._get_current_object()[key]

    def __setslice__(self, i, j, seq):
        self._get_current_object()[i:j] = seq

    def __delslice__(self, i, j):
        del self._get_current_object()[i:j]

    __setattr__ = lambda x, n, v: setattr(x._get_current_object(), n, v)
    __delattr__ = lambda x, n: delattr(x._get_current_object(), n)
    __str__ = lambda x: str(x._get_current_object())
    __lt__ = lambda x, o: x._get_current_object() < o
    __le__ = lambda x, o: x._get_current_object() <= o
    __eq__ = lambda x, o: x._get_current_object() == o
    __ne__ = lambda x, o: x._get_current_object() != o
    __gt__ = lambda x, o: x._get_current_object() > o
    __ge__ = lambda x, o: x._get_current_object() >= o
    __cmp__ = lambda x, o: cmp(x._get_current_object(), o)
    __hash__ = lambda x: hash(x._get_current_object())
#    __call__ = lambda x, *a, **kw: x._get_current_object()(*a, **kw)
    __len__ = lambda x: len(x._get_current_object())
    __getitem__ = lambda x, i: x._get_current_object()[i]
    __iter__ = lambda x: iter(x._get_current_object())
    __contains__ = lambda x, i: i in x._get_current_object()
    __getslice__ = lambda x, i, j: x._get_current_object()[i:j]
    __add__ = lambda x, o: x._get_current_object() + o
    __sub__ = lambda x, o: x._get_current_object() - o
    __mul__ = lambda x, o: x._get_current_object() * o
    __floordiv__ = lambda x, o: x._get_current_object() // o
    __mod__ = lambda x, o: x._get_current_object() % o
    __divmod__ = lambda x, o: x._get_current_object().__divmod__(o)
    __pow__ = lambda x, o: x._get_current_object() ** o
    __lshift__ = lambda x, o: x._get_current_object() << o
    __rshift__ = lambda x, o: x._get_current_object() >> o
    __and__ = lambda x, o: x._get_current_object() & o
    __xor__ = lambda x, o: x._get_current_object() ^ o
    __or__ = lambda x, o: x._get_current_object() | o
    __div__ = lambda x, o: x._get_current_object().__div__(o)
    __truediv__ = lambda x, o: x._get_current_object().__truediv__(o)
    __neg__ = lambda x: -(x._get_current_object())
    __pos__ = lambda x: +(x._get_current_object())
    __abs__ = lambda x: abs(x._get_current_object())
    __invert__ = lambda x: ~(x._get_current_object())
    __complex__ = lambda x: complex(x._get_current_object())
    __int__ = lambda x: int(x._get_current_object())
    __long__ = lambda x: long(x._get_current_object())
    __float__ = lambda x: float(x._get_current_object())
    __oct__ = lambda x: oct(x._get_current_object())
    __hex__ = lambda x: hex(x._get_current_object())
    __index__ = lambda x: x._get_current_object().__index__()
    __coerce__ = lambda x, o: x.__coerce__(x, o)
    __enter__ = lambda x: x.__enter__()
    __exit__ = lambda x, *a, **kw: x.__exit__(*a, **kw)

########NEW FILE########
__FILENAME__ = signals
class Signal:
    def __init__(self, name):
        self.name = name
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def disconnect(self, callback):
        for index, cb in enumerate(self.callbacks):
            if callback == cb:
                del self.callbacks[index]
                break

    def emit(self, *args, **kws):
        for callback in self.callbacks[:]:
            callback(*args, **kws)

########NEW FILE########
__FILENAME__ = unit
import os
import sys
import threading
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from chronic import clear, time, Timer, timings, stack, post_timing


class MockClock(object):
    def __init__(self):
        self.time = 1000

    def add_seconds(self, seconds):
        self.time += seconds

    def get_time(self):
        return self.time


class BasicTest(unittest.TestCase):
    def setUp(self):
        clear()

    def test_stack(self):
        with Timer('a'):
            with Timer('b'):
                assert stack == ('a', 'b')

    def test_timings(self):
        clock = MockClock()
        with Timer('a', clock=clock.get_time):
            clock.add_seconds(10)

        with Timer('a', clock=clock.get_time):
            clock.add_seconds(5)

        self.assertIn('a', timings,
                      "Timings dict did not contain timing name")
        a = timings['a']
        self.assertIn('total_elapsed', a,
                      "Timing didn't include a total_elapsed")
        self.assertEquals(a['total_elapsed'], 15)

        self.assertIn('a', timings(),
                      "Timings dict could not be accessed as a function.")

    def test_time_decorator(self):
        clock = MockClock()

        @time(clock=clock.get_time)
        def timed_func():
            clock.add_seconds(10)

        timed_func()

        self.assertIn('timed_func', timings)
        a = timings['timed_func']
        self.assertIn('total_elapsed', a,
                      "Timing didn't include a total_elapsed")
        self.assertEquals(a['total_elapsed'], 10)

    def test_time_decorator_no_args(self):

        @time
        def timed_func():
            pass

        timed_func()
        self.assertIn('timed_func', timings)
        a = timings['timed_func']
        self.assertIn('total_elapsed', a,
                      "Timing didn't include a total_elapsed")

    def test_timings_are_emptied_between_tests(self):
        '''
        If not, a lot of the asserts in these tests may incorrectly pass.
        '''
        self.assertEquals({}, timings)

    def test_signals(self):
        d = {}

        def callback(*args, **kws):
            d['called'] = 1

        post_timing.connect(callback)
        with Timer('a'):
            pass

        assert d['called'] is 1


class ThreadingTest(unittest.TestCase):
    def test_timings_do_not_bleed(self):
        all_timings = []

        def time_stuff():
            clock = MockClock()
            for i in range(5):
                with Timer('test', clock=clock.get_time):
                    clock.add_seconds(1)
            all_timings.append(timings.copy())

        threads = []
        for i in range(4):
            t = threading.Thread(target=time_stuff)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        for ts in all_timings:
            self.assertIn('test', ts)
            self.assertEquals(ts['test']['count'], 5)

########NEW FILE########
