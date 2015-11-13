__FILENAME__ = smokesignal
"""
smokesignal.py - simple event signaling
"""
import sys

from collections import defaultdict
from functools import partial


__all__ = ['emit', 'emitting', 'signals', 'responds_to', 'on', 'once',
           'disconnect', 'disconnect_from', 'clear', 'clear_all']


# Collection of receivers/callbacks
_receivers = defaultdict(set)
_pyversion = sys.version_info[:2]


def emit(signal, *args, **kwargs):
    """
    Emits a single signal to call callbacks registered to respond to that signal.
    Optionally accepts args and kwargs that are passed directly to callbacks.

    :param signal: Signal to send
    """
    for callback in _receivers[signal]:
        _call(callback, args=args, kwargs=kwargs)


class emitting(object):
    """
    Context manager for emitting signals either on enter or on exit of a context.
    By default, if this context manager is created using a single arg-style argument,
    it will emit a signal on exit. Otherwise, keyword arguments indicate signal points
    """
    def __init__(self, exit, enter=None):
        self.exit = exit
        self.enter = enter

    def __enter__(self):
        if self.enter is not None:
            emit(self.enter)

    def __exit__(self, exc_type, exc_value, tb):
        emit(self.exit)


def _call(callback, args=[], kwargs={}):
    """
    Calls a callback with optional args and keyword args lists. This method exists so
    we can inspect the `_max_calls` attribute that's set by `_on`. If this value is None,
    the callback is considered to have no limit. Otherwise, an integer value is expected
    and decremented until there are no remaining calls
    """
    if not hasattr(callback, '_max_calls'):
        callback._max_calls = None

    if callback._max_calls is None or callback._max_calls > 0:
        if callback._max_calls is not None:
            callback._max_calls -= 1

        return callback(*args, **kwargs)


def signals(callback):
    """
    Returns a tuple of all signals for a particular callback

    :param callback: A callable registered with smokesignal
    :returns: Tuple of all signals callback responds to
    """
    return tuple(s for s in _receivers if responds_to(callback, s))


def responds_to(callback, signal):
    """
    Returns bool if callback will respond to a particular signal

    :param callback: A callable registered with smokesignal
    :param signal: A signal to check if callback responds
    :returns: True if callback responds to signal, False otherwise
    """
    return callback in _receivers[signal]


def on(signals, callback=None, max_calls=None):
    """
    Registers a single callback for receiving an event (or event list). Optionally,
    can specify a maximum number of times the callback should receive a signal. This
    method works as both a function and a decorator::

        smokesignal.on('foo', my_callback)

        @smokesignal.on('foo')
        def my_callback():
            pass

    :param signals: A single signal or list/tuple of signals that callback should respond to
    :param callback: A callable that should repond to supplied signal(s)
    :param max_calls: Integer maximum calls for callback. None for no limit.
    """
    if isinstance(callback, int) or callback is None:
        # Decorated
        if isinstance(callback, int):
            # Here the args were passed arg-style, not kwarg-style
            callback, max_calls = max_calls, callback
        return partial(_on, signals, max_calls=max_calls)
    else:
        # Function call
        return _on(signals, callback, max_calls=max_calls)


def _on(on_signals, callback, max_calls=None):
    """
    Proxy for `smokesignal.on`, which is compatible as both a function call and
    a decorator. This method cannot be used as a decorator

    :param signals: A single signal or list/tuple of signals that callback should respond to
    :param callback: A callable that should repond to supplied signal(s)
    :param max_calls: Integer maximum calls for callback. None for no limit.
    """
    assert callable(callback), 'Signal callbacks must be callable'

    # Support for lists of signals
    if not isinstance(on_signals, (list, tuple)):
        on_signals = [on_signals]

    callback._max_calls = max_calls

    # Register the callback
    for signal in on_signals:
        _receivers[signal].add(callback)

    # Setup responds_to partial for use later
    if not hasattr(callback, 'responds_to'):
        callback.responds_to = partial(responds_to, callback)

    # Setup signals partial for use later.
    if not hasattr(callback, 'signals'):
        callback.signals = partial(signals, callback)

    return callback


def once(signals, callback=None):
    """
    Registers a callback that will respond to an event at most one time

    :param signals: A single signal or list/tuple of signals that callback should respond to
    :param callback: A callable that should repond to supplied signal(s)
    """
    return on(signals, callback, max_calls=1)


def disconnect(callback):
    """
    Removes a callback from all signal registries and prevents it from responding
    to any emitted signal.

    :param callback: A callable registered with smokesignal
    """
    # This is basically what `disconnect_from` does, but that method guards against
    # callbacks not responding to signal arguments. We don't need that because we're
    # disconnecting all the valid ones here
    for signal in signals(callback):
        _receivers[signal].remove(callback)


def disconnect_from(callback, signals):
    """
    Removes a callback from specified signal registries and prevents it from responding
    to any emitted signal.

    :param callback: A callable registered with smokesignal
    :param signals: A single signal or list/tuple of signals
    """
    # Support for lists of signals
    if not isinstance(signals, (list, tuple)):
        signals = [signals]

    # Remove callback from receiver list if it responds to the signal
    for signal in signals:
        if responds_to(callback, signal):
            _receivers[signal].remove(callback)


def clear(*signals):
    """
    Clears all callbacks for a particular signal or signals
    """
    signals = signals if signals else _receivers.keys()

    for signal in signals:
        _receivers[signal].clear()


def clear_all():
    """
    Clears all callbacks for all signals
    """
    for key in _receivers.keys():
        _receivers[key].clear()

########NEW FILE########
__FILENAME__ = tests
""" Unit tests """
from unittest import TestCase

from mock import Mock, patch

import smokesignal


class SmokesignalTestCase(TestCase):

    def setUp(self):
        self.callback = lambda x: x
        self.mock_callback = Mock()

    def tearDown(self):
        smokesignal.clear_all()

    def test_call_no_max_calls(self):
        def foo():
            foo.call_count += 1
        foo.call_count = 0

        for x in range(5):
            smokesignal._call(foo)

        assert foo.call_count == 5

    def test_call_with_max_calls(self):
        def foo():
            foo.call_count += 1
        foo.call_count = 0
        foo._max_calls = 1

        for x in range(5):
            smokesignal._call(foo)

        assert foo.call_count == 1

    def test_clear(self):
        smokesignal.on('foo', self.callback)
        assert len(smokesignal._receivers['foo']) == 1

        smokesignal.clear('foo')
        assert len(smokesignal._receivers['foo']) == 0

    def test_clear_no_args_clears_all(self):
        smokesignal.on(('foo', 'bar', 'baz'), self.callback)
        assert len(smokesignal._receivers['foo']) == 1
        assert len(smokesignal._receivers['bar']) == 1
        assert len(smokesignal._receivers['baz']) == 1

        smokesignal.clear()
        assert len(smokesignal._receivers['foo']) == 0
        assert len(smokesignal._receivers['bar']) == 0
        assert len(smokesignal._receivers['baz']) == 0


    def test_clear_many(self):
        smokesignal.on(('foo', 'bar', 'baz'), self.callback)
        assert len(smokesignal._receivers['foo']) == 1
        assert len(smokesignal._receivers['bar']) == 1
        assert len(smokesignal._receivers['baz']) == 1

        smokesignal.clear('foo', 'bar')
        assert len(smokesignal._receivers['foo']) == 0
        assert len(smokesignal._receivers['bar']) == 0
        assert len(smokesignal._receivers['baz']) == 1

    def test_clear_all(self):
        smokesignal.on(('foo', 'bar'), self.callback)
        assert len(smokesignal._receivers['foo']) == 1
        assert len(smokesignal._receivers['bar']) == 1

        smokesignal.clear_all()
        assert len(smokesignal._receivers['foo']) == 0
        assert len(smokesignal._receivers['bar']) == 0

    def test_emit_with_no_callbacks(self):
        smokesignal.emit('foo')

    def test_emit_with_callbacks(self):
        # Register first
        smokesignal.on('foo', self.mock_callback)
        assert smokesignal.responds_to(self.mock_callback, 'foo')

        smokesignal.emit('foo')
        assert self.mock_callback.called

    def test_emit_with_callback_args(self):
        # Register first
        smokesignal.on('foo', self.mock_callback)
        assert smokesignal.responds_to(self.mock_callback, 'foo')

        smokesignal.emit('foo', 1, 2, 3, foo='bar')
        assert self.mock_callback.called_with(1, 2, 3, foo='bar')

    def test_on_raises(self):
        self.assertRaises(AssertionError, smokesignal.on, 'foo', 'bar')

    def test_on_registers(self):
        assert len(smokesignal._receivers['foo']) == 0
        smokesignal.on('foo', self.callback)
        assert len(smokesignal._receivers['foo']) == 1

    def test_on_registers_many(self):
        assert len(smokesignal._receivers['foo']) == 0
        assert len(smokesignal._receivers['bar']) == 0

        smokesignal.on(('foo', 'bar'), self.callback)

        assert len(smokesignal._receivers['foo']) == 1
        assert len(smokesignal._receivers['bar']) == 1

    def test_on_max_calls(self):
        # Make a method that has a call count
        def cb():
            cb.call_count += 1
        cb.call_count = 0

        # Register first
        smokesignal.on('foo', cb, max_calls=3)
        assert len(smokesignal._receivers['foo']) == 1

        # Call a bunch of times
        for x in range(10):
            smokesignal.emit('foo')

        assert cb.call_count == 3

    def test_on_decorator_registers(self):
        assert len(smokesignal._receivers['foo']) == 0

        @smokesignal.on('foo')
        def my_callback():
            pass

        assert len(smokesignal._receivers['foo']) == 1

    def test_on_decorator_registers_many(self):
        assert len(smokesignal._receivers['foo']) == 0
        assert len(smokesignal._receivers['bar']) == 0

        @smokesignal.on(('foo', 'bar'))
        def my_callback():
            pass

        assert len(smokesignal._receivers['foo']) == 1
        assert len(smokesignal._receivers['bar']) == 1

    def test_on_decorator_max_calls(self):
        # Make a method that has a call count
        def cb():
            cb.call_count += 1
        cb.call_count = 0

        # Register first - like a cecorator
        smokesignal.on('foo', max_calls=3)(cb)
        assert len(smokesignal._receivers['foo']) == 1

        # Call a bunch of times
        for x in range(10):
            smokesignal.emit('foo')

        assert cb.call_count == 3

    def test_disconnect(self):
        # Register first
        smokesignal.on(('foo', 'bar'), self.callback)
        assert smokesignal.responds_to(self.callback, 'foo')
        assert smokesignal.responds_to(self.callback, 'bar')

        smokesignal.disconnect(self.callback)
        assert not smokesignal.responds_to(self.callback, 'foo')
        assert not smokesignal.responds_to(self.callback, 'bar')

    def test_disconnect_from_removes_only_one(self):
        # Register first
        smokesignal.on(('foo', 'bar'), self.callback)
        assert smokesignal.responds_to(self.callback, 'foo')
        assert smokesignal.responds_to(self.callback, 'bar')

        # Remove it
        smokesignal.disconnect_from(self.callback, 'foo')
        assert not smokesignal.responds_to(self.callback, 'foo')
        assert smokesignal.responds_to(self.callback, 'bar')

    def test_disconnect_from_removes_all(self):
        # Register first
        smokesignal.on(('foo', 'bar'), self.callback)
        assert smokesignal.responds_to(self.callback, 'foo')
        assert smokesignal.responds_to(self.callback, 'bar')

        # Remove it
        smokesignal.disconnect_from(self.callback, ('foo', 'bar'))
        assert not smokesignal.responds_to(self.callback, 'foo')
        assert not smokesignal.responds_to(self.callback, 'bar')

    def test_signals(self):
        # Register first
        smokesignal.on(('foo', 'bar'), self.callback)

        assert 'foo' in smokesignal.signals(self.callback)
        assert 'bar' in smokesignal.signals(self.callback)

    def test_responds_to_true(self):
        # Register first
        smokesignal.on('foo', self.callback)
        assert smokesignal.responds_to(self.callback, 'foo') is True

    def test_responds_to_false(self):
        # Register first
        smokesignal.on('foo', self.callback)
        assert smokesignal.responds_to(self.callback, 'bar') is False

    def test_once_raises(self):
        self.assertRaises(AssertionError, smokesignal.once, 'foo', 'bar')

    def test_once(self):
        # Make a method that has a call count
        def cb():
            cb.call_count += 1
        cb.call_count = 0

        # Register first
        smokesignal.once('foo', cb)
        assert len(smokesignal._receivers['foo']) == 1

        # Call twice
        smokesignal.emit('foo')
        smokesignal.emit('foo')

        assert cb.call_count == 1

    def test_once_decorator(self):
        # Make a method that has a call count
        def cb():
            cb.call_count += 1
        cb.call_count = 0

        # Register first like a decorator
        smokesignal.once('foo')(cb)
        assert len(smokesignal._receivers['foo']) == 1

        # Call twice
        smokesignal.emit('foo')
        smokesignal.emit('foo')

        assert cb.call_count == 1

    @patch('smokesignal.emit')
    def test_emitting_arg_style(self, emit):
        with smokesignal.emitting('foo'):
            pass

        assert emit.call_count == 1

    @patch('smokesignal.emit')
    def test_emitting_kwarg_style(self, emit):
        with smokesignal.emitting(enter='foo', exit='bar'):
            pass

        assert emit.call_count == 2

    def test_on_creates_responds_to_fn(self):
        # Registering a callback should create partials to smokesignal
        # methods for later user
        smokesignal.on('foo', self.callback)

        assert hasattr(self.callback, 'responds_to')
        assert self.callback.responds_to('foo')

    def test_on_creates_signals_fn(self):
        # Registering a callback should create partials to smokesignal
        # methods for later user
        smokesignal.on(('foo', 'bar'), self.callback)

        assert hasattr(self.callback, 'signals')
        assert 'foo' in self.callback.signals()
        assert 'bar' in self.callback.signals()

########NEW FILE########
