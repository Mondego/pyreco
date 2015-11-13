__FILENAME__ = fib
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


def slow_fib(n):
    if n <= 1:
        return 1
    else:
        return slow_fib(n-1) + slow_fib(n-2)

########NEW FILE########
__FILENAME__ = run_example
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import time

from rq import Connection, Queue

from fib import slow_fib


def main():
    # Range of Fibonacci numbers to compute
    fib_range = range(20, 34)

    # Kick off the tasks asynchronously
    async_results = {}
    q = Queue()
    for x in fib_range:
        async_results[x] = q.enqueue(slow_fib, x)

    start_time = time.time()
    done = False
    while not done:
        os.system('clear')
        print('Asynchronously: (now = %.2f)' % (time.time() - start_time,))
        done = True
        for x in fib_range:
            result = async_results[x].return_value
            if result is None:
                done = False
                result = '(calculating)'
            print('fib(%d) = %s' % (x, result))
        print('')
        print('To start the actual in the background, run a worker:')
        print('    python examples/run_worker.py')
        time.sleep(0.2)

    print('Done')


if __name__ == '__main__':
    # Tell RQ what Redis connection to use
    with Connection():
        main()

########NEW FILE########
__FILENAME__ = run_worker
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from rq import Connection, Queue, Worker

if __name__ == '__main__':
    # Tell rq what Redis connection to use
    with Connection():
        q = Queue()
        Worker(q).work()

########NEW FILE########
__FILENAME__ = connections
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from functools import partial

from redis import Redis, StrictRedis


def fix_return_type(func):
    # deliberately no functools.wraps() call here, since the function being
    # wrapped is a partial, which has no module
    def _inner(*args, **kwargs):
        value = func(*args, **kwargs)
        if value is None:
            value = -1
        return value
    return _inner


def patch_connection(connection):
    if not isinstance(connection, StrictRedis):
        raise ValueError('A StrictRedis or Redis connection is required.')

    # Don't patch already patches objects
    PATCHED_METHODS = ['_setex', '_lrem', '_zadd', '_pipeline', '_ttl']
    if all([hasattr(connection, attr) for attr in PATCHED_METHODS]):
        return connection

    if isinstance(connection, Redis):
        connection._setex = partial(StrictRedis.setex, connection)
        connection._lrem = partial(StrictRedis.lrem, connection)
        connection._zadd = partial(StrictRedis.zadd, connection)
        connection._pipeline = partial(StrictRedis.pipeline, connection)
        connection._ttl = fix_return_type(partial(StrictRedis.ttl, connection))
        if hasattr(connection, 'pttl'):
            connection._pttl = fix_return_type(partial(StrictRedis.pttl, connection))
    elif isinstance(connection, StrictRedis):
        connection._setex = connection.setex
        connection._lrem = connection.lrem
        connection._zadd = connection.zadd
        connection._pipeline = connection.pipeline
        connection._ttl = connection.ttl
        if hasattr(connection, 'pttl'):
            connection._pttl = connection.pttl
    else:
        raise ValueError('Unanticipated connection type: {}. Please report this.'.format(type(connection)))

    return connection

########NEW FILE########
__FILENAME__ = dictconfig
# This is a copy of the Python logging.config.dictconfig module.  It is
# provided here for backwards compatibility for Python versions prior to 2.7.
#
# Copyright 2009-2010 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import logging.handlers
import re
import sys
import types
from rq.compat import string_types

IDENTIFIER = re.compile('^[a-z_][a-z0-9_]*$', re.I)

def valid_ident(s):
    m = IDENTIFIER.match(s)
    if not m:
        raise ValueError('Not a valid Python identifier: %r' % s)
    return True

#
# This function is defined in logging only in recent versions of Python
#
try:
    from logging import _checkLevel
except ImportError:
    def _checkLevel(level):
        if isinstance(level, int):
            rv = level
        elif str(level) == level:
            if level not in logging._levelNames:
                raise ValueError('Unknown level: %r' % level)
            rv = logging._levelNames[level]
        else:
            raise TypeError('Level not an integer or a '
                            'valid string: %r' % level)
        return rv

# The ConvertingXXX classes are wrappers around standard Python containers,
# and they serve to convert any suitable values in the container. The
# conversion converts base dicts, lists and tuples to their wrapped
# equivalents, whereas strings which match a conversion format are converted
# appropriately.
#
# Each wrapper should have a configurator attribute holding the actual
# configurator to use for conversion.

class ConvertingDict(dict):
    """A converting dictionary wrapper."""

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    def get(self, key, default=None):
        value = dict.get(self, key, default)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

class ConvertingList(list):
    """A converting list wrapper."""
    def __getitem__(self, key):
        value = list.__getitem__(self, key)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    def pop(self, idx=-1):
        value = list.pop(self, idx)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
        return result

class ConvertingTuple(tuple):
    """A converting tuple wrapper."""
    def __getitem__(self, key):
        value = tuple.__getitem__(self, key)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

class BaseConfigurator(object):
    """
    The configurator base class which defines some useful defaults.
    """

    CONVERT_PATTERN = re.compile(r'^(?P<prefix>[a-z]+)://(?P<suffix>.*)$')

    WORD_PATTERN = re.compile(r'^\s*(\w+)\s*')
    DOT_PATTERN = re.compile(r'^\.\s*(\w+)\s*')
    INDEX_PATTERN = re.compile(r'^\[\s*(\w+)\s*\]\s*')
    DIGIT_PATTERN = re.compile(r'^\d+$')

    value_converters = {
        'ext' : 'ext_convert',
        'cfg' : 'cfg_convert',
    }

    # We might want to use a different one, e.g. importlib
    importer = __import__

    def __init__(self, config):
        self.config = ConvertingDict(config)
        self.config.configurator = self

    def resolve(self, s):
        """
        Resolve strings to objects using standard import and attribute
        syntax.
        """
        name = s.split('.')
        used = name.pop(0)
        try:
            found = self.importer(used)
            for frag in name:
                used += '.' + frag
                try:
                    found = getattr(found, frag)
                except AttributeError:
                    self.importer(used)
                    found = getattr(found, frag)
            return found
        except ImportError:
            e, tb = sys.exc_info()[1:]
            v = ValueError('Cannot resolve %r: %s' % (s, e))
            v.__cause__, v.__traceback__ = e, tb
            raise v

    def ext_convert(self, value):
        """Default converter for the ext:// protocol."""
        return self.resolve(value)

    def cfg_convert(self, value):
        """Default converter for the cfg:// protocol."""
        rest = value
        m = self.WORD_PATTERN.match(rest)
        if m is None:
            raise ValueError("Unable to convert %r" % value)
        else:
            rest = rest[m.end():]
            d = self.config[m.groups()[0]]
            #print d, rest
            while rest:
                m = self.DOT_PATTERN.match(rest)
                if m:
                    d = d[m.groups()[0]]
                else:
                    m = self.INDEX_PATTERN.match(rest)
                    if m:
                        idx = m.groups()[0]
                        if not self.DIGIT_PATTERN.match(idx):
                            d = d[idx]
                        else:
                            try:
                                n = int(idx) # try as number first (most likely)
                                d = d[n]
                            except TypeError:
                                d = d[idx]
                if m:
                    rest = rest[m.end():]
                else:
                    raise ValueError('Unable to convert '
                                     '%r at %r' % (value, rest))
        #rest should be empty
        return d

    def convert(self, value):
        """
        Convert values to an appropriate type. dicts, lists and tuples are
        replaced by their converting alternatives. Strings are checked to
        see if they have a conversion format and are converted if they do.
        """
        if not isinstance(value, ConvertingDict) and isinstance(value, dict):
            value = ConvertingDict(value)
            value.configurator = self
        elif not isinstance(value, ConvertingList) and isinstance(value, list):
            value = ConvertingList(value)
            value.configurator = self
        elif not isinstance(value, ConvertingTuple) and\
                 isinstance(value, tuple):
            value = ConvertingTuple(value)
            value.configurator = self
        elif isinstance(value, string_types): # str for py3k
            m = self.CONVERT_PATTERN.match(value)
            if m:
                d = m.groupdict()
                prefix = d['prefix']
                converter = self.value_converters.get(prefix, None)
                if converter:
                    suffix = d['suffix']
                    converter = getattr(self, converter)
                    value = converter(suffix)
        return value

    def configure_custom(self, config):
        """Configure an object with a user-supplied factory."""
        c = config.pop('()')
        if not hasattr(c, '__call__') and type(c) != type:
            c = self.resolve(c)
        props = config.pop('.', None)
        # Check for valid identifiers
        kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
        result = c(**kwargs)
        if props:
            for name, value in props.items():
                setattr(result, name, value)
        return result

    def as_tuple(self, value):
        """Utility function which converts lists to tuples."""
        if isinstance(value, list):
            value = tuple(value)
        return value

class DictConfigurator(BaseConfigurator):
    """
    Configure logging using a dictionary-like object to describe the
    configuration.
    """

    def configure(self):
        """Do the configuration."""

        config = self.config
        if 'version' not in config:
            raise ValueError("dictionary doesn't specify a version")
        if config['version'] != 1:
            raise ValueError("Unsupported version: %s" % config['version'])
        incremental = config.pop('incremental', False)
        EMPTY_DICT = {}
        logging._acquireLock()
        try:
            if incremental:
                handlers = config.get('handlers', EMPTY_DICT)
                # incremental handler config only if handler name
                # ties in to logging._handlers (Python 2.7)
                if sys.version_info[:2] == (2, 7):
                    for name in handlers:
                        if name not in logging._handlers:
                            raise ValueError('No handler found with '
                                             'name %r'  % name)
                        else:
                            try:
                                handler = logging._handlers[name]
                                handler_config = handlers[name]
                                level = handler_config.get('level', None)
                                if level:
                                    handler.setLevel(_checkLevel(level))
                            except Exception as e:
                                raise ValueError('Unable to configure handler '
                                                 '%r: %s' % (name, e))
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    try:
                        self.configure_logger(name, loggers[name], True)
                    except Exception as e:
                        raise ValueError('Unable to configure logger '
                                         '%r: %s' % (name, e))
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root, True)
                    except Exception as e:
                        raise ValueError('Unable to configure root '
                                         'logger: %s' % e)
            else:
                disable_existing = config.pop('disable_existing_loggers', True)

                logging._handlers.clear()
                del logging._handlerList[:]

                # Do formatters first - they don't refer to anything else
                formatters = config.get('formatters', EMPTY_DICT)
                for name in formatters:
                    try:
                        formatters[name] = self.configure_formatter(
                                                            formatters[name])
                    except Exception as e:
                        raise ValueError('Unable to configure '
                                         'formatter %r: %s' % (name, e))
                # Next, do filters - they don't refer to anything else, either
                filters = config.get('filters', EMPTY_DICT)
                for name in filters:
                    try:
                        filters[name] = self.configure_filter(filters[name])
                    except Exception as e:
                        raise ValueError('Unable to configure '
                                         'filter %r: %s' % (name, e))

                # Next, do handlers - they refer to formatters and filters
                # As handlers can refer to other handlers, sort the keys
                # to allow a deterministic order of configuration
                handlers = config.get('handlers', EMPTY_DICT)
                for name in sorted(handlers):
                    try:
                        handler = self.configure_handler(handlers[name])
                        handler.name = name
                        handlers[name] = handler
                    except Exception as e:
                        raise ValueError('Unable to configure handler '
                                         '%r: %s' % (name, e))
                # Next, do loggers - they refer to handlers and filters

                #we don't want to lose the existing loggers,
                #since other threads may have pointers to them.
                #existing is set to contain all existing loggers,
                #and as we go through the new configuration we
                #remove any which are configured. At the end,
                #what's left in existing is the set of loggers
                #which were in the previous configuration but
                #which are not in the new configuration.
                root = logging.root
                existing = root.manager.loggerDict.keys()
                #The list needs to be sorted so that we can
                #avoid disabling child loggers of explicitly
                #named loggers. With a sorted list it is easier
                #to find the child loggers.
                existing.sort()
                #We'll keep the list of existing loggers
                #which are children of named loggers here...
                child_loggers = []
                #now set up the new ones...
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    if name in existing:
                        i = existing.index(name)
                        prefixed = name + "."
                        pflen = len(prefixed)
                        num_existing = len(existing)
                        i = i + 1 # look at the entry after name
                        while (i < num_existing) and\
                              (existing[i][:pflen] == prefixed):
                            child_loggers.append(existing[i])
                            i = i + 1
                        existing.remove(name)
                    try:
                        self.configure_logger(name, loggers[name])
                    except Exception as e:
                        raise ValueError('Unable to configure logger '
                                         '%r: %s' % (name, e))

                #Disable any old loggers. There's no point deleting
                #them as other threads may continue to hold references
                #and by disabling them, you stop them doing any logging.
                #However, don't disable children of named loggers, as that's
                #probably not what was intended by the user.
                for log in existing:
                    logger = root.manager.loggerDict[log]
                    if log in child_loggers:
                        logger.level = logging.NOTSET
                        logger.handlers = []
                        logger.propagate = True
                    elif disable_existing:
                        logger.disabled = True

                # And finally, do the root logger
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root)
                    except Exception as e:
                        raise ValueError('Unable to configure root '
                                         'logger: %s' % e)
        finally:
            logging._releaseLock()

    def configure_formatter(self, config):
        """Configure a formatter from a dictionary."""
        if '()' in config:
            factory = config['()'] # for use in exception handler
            try:
                result = self.configure_custom(config)
            except TypeError as te:
                if "'format'" not in str(te):
                    raise
                #Name of parameter changed from fmt to format.
                #Retry with old name.
                #This is so that code can be used with older Python versions
                #(e.g. by Django)
                config['fmt'] = config.pop('format')
                config['()'] = factory
                result = self.configure_custom(config)
        else:
            fmt = config.get('format', None)
            dfmt = config.get('datefmt', None)
            result = logging.Formatter(fmt, dfmt)
        return result

    def configure_filter(self, config):
        """Configure a filter from a dictionary."""
        if '()' in config:
            result = self.configure_custom(config)
        else:
            name = config.get('name', '')
            result = logging.Filter(name)
        return result

    def add_filters(self, filterer, filters):
        """Add filters to a filterer from a list of names."""
        for f in filters:
            try:
                filterer.addFilter(self.config['filters'][f])
            except Exception as e:
                raise ValueError('Unable to add filter %r: %s' % (f, e))

    def configure_handler(self, config):
        """Configure a handler from a dictionary."""
        formatter = config.pop('formatter', None)
        if formatter:
            try:
                formatter = self.config['formatters'][formatter]
            except Exception as e:
                raise ValueError('Unable to set formatter '
                                 '%r: %s' % (formatter, e))
        level = config.pop('level', None)
        filters = config.pop('filters', None)
        if '()' in config:
            c = config.pop('()')
            if not hasattr(c, '__call__') and type(c) != type:
                c = self.resolve(c)
            factory = c
        else:
            klass = self.resolve(config.pop('class'))
            #Special case for handler which refers to another handler
            if issubclass(klass, logging.handlers.MemoryHandler) and\
                'target' in config:
                try:
                    config['target'] = self.config['handlers'][config['target']]
                except Exception as e:
                    raise ValueError('Unable to set target handler '
                                     '%r: %s' % (config['target'], e))
            elif issubclass(klass, logging.handlers.SMTPHandler) and\
                'mailhost' in config:
                config['mailhost'] = self.as_tuple(config['mailhost'])
            elif issubclass(klass, logging.handlers.SysLogHandler) and\
                'address' in config:
                config['address'] = self.as_tuple(config['address'])
            factory = klass
        kwargs = dict([(str(k), config[k]) for k in config if valid_ident(k)])
        try:
            result = factory(**kwargs)
        except TypeError as te:
            if "'stream'" not in str(te):
                raise
            #The argument name changed from strm to stream
            #Retry with old name.
            #This is so that code can be used with older Python versions
            #(e.g. by Django)
            kwargs['strm'] = kwargs.pop('stream')
            result = factory(**kwargs)
        if formatter:
            result.setFormatter(formatter)
        if level is not None:
            result.setLevel(_checkLevel(level))
        if filters:
            self.add_filters(result, filters)
        return result

    def add_handlers(self, logger, handlers):
        """Add handlers to a logger from a list of names."""
        for h in handlers:
            try:
                logger.addHandler(self.config['handlers'][h])
            except Exception as e:
                raise ValueError('Unable to add handler %r: %s' % (h, e))

    def common_logger_config(self, logger, config, incremental=False):
        """
        Perform configuration which is common to root and non-root loggers.
        """
        level = config.get('level', None)
        if level is not None:
            logger.setLevel(_checkLevel(level))
        if not incremental:
            #Remove any existing handlers
            for h in logger.handlers[:]:
                logger.removeHandler(h)
            handlers = config.get('handlers', None)
            if handlers:
                self.add_handlers(logger, handlers)
            filters = config.get('filters', None)
            if filters:
                self.add_filters(logger, filters)

    def configure_logger(self, name, config, incremental=False):
        """Configure a non-root logger from a dictionary."""
        logger = logging.getLogger(name)
        self.common_logger_config(logger, config, incremental)
        propagate = config.get('propagate', None)
        if propagate is not None:
            logger.propagate = propagate

    def configure_root(self, config, incremental=False):
        """Configure a root logger from a dictionary."""
        root = logging.getLogger()
        self.common_logger_config(root, config, incremental)

dictConfigClass = DictConfigurator

def dictConfig(config):
    """Configure logging using a dictionary."""
    dictConfigClass(config).configure()

########NEW FILE########
__FILENAME__ = connections
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from contextlib import contextmanager

from redis import StrictRedis

from .compat.connections import patch_connection
from .local import LocalStack, release_local


class NoRedisConnectionException(Exception):
    pass


@contextmanager
def Connection(connection=None):
    if connection is None:
        connection = StrictRedis()
    push_connection(connection)
    try:
        yield
    finally:
        popped = pop_connection()
        assert popped == connection, \
            'Unexpected Redis connection was popped off the stack. ' \
            'Check your Redis connection setup.'


def push_connection(redis):
    """Pushes the given connection on the stack."""
    _connection_stack.push(patch_connection(redis))


def pop_connection():
    """Pops the topmost connection from the stack."""
    return _connection_stack.pop()


def use_connection(redis=None):
    """Clears the stack and uses the given connection.  Protects against mixed
    use of use_connection() and stacked connection contexts.
    """
    assert len(_connection_stack) <= 1, \
        'You should not mix Connection contexts with use_connection().'
    release_local(_connection_stack)

    if redis is None:
        redis = StrictRedis()
    push_connection(redis)


def get_current_connection():
    """Returns the current Redis connection (i.e. the topmost on the
    connection stack).
    """
    return _connection_stack.top


def resolve_connection(connection=None):
    """Convenience function to resolve the given or the current connection.
    Raises an exception if it cannot resolve a connection now.
    """
    if connection is not None:
        return patch_connection(connection)

    connection = get_current_connection()
    if connection is None:
        raise NoRedisConnectionException('Could not resolve a Redis connection.')
    return connection


_connection_stack = LocalStack()

__all__ = ['Connection', 'get_current_connection', 'push_connection',
           'pop_connection', 'use_connection']

########NEW FILE########
__FILENAME__ = legacy
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


import logging
from rq import get_current_connection
from rq import Worker


logger = logging.getLogger(__name__)


def cleanup_ghosts():
    """
    RQ versions < 0.3.6 suffered from a race condition where workers, when
    abruptly terminated, did not have a chance to clean up their worker
    registration, leading to reports of ghosted workers in `rqinfo`.  Since
    0.3.6, new worker registrations automatically expire, and the worker will
    make sure to refresh the registrations as long as it's alive.

    This function will clean up any of such legacy ghosted workers.
    """
    conn = get_current_connection()
    for worker in Worker.all():
        if conn._ttl(worker.key) == -1:
            ttl = worker.default_worker_ttl
            conn.expire(worker.key, ttl)
            logger.info('Marked ghosted worker {0} to expire in {1} seconds.'.format(worker.name, ttl))

########NEW FILE########
__FILENAME__ = sentry
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import warnings


def register_sentry(client, worker):
    """Given a Raven client and an RQ worker, registers exception handlers
    with the worker so exceptions are logged to Sentry.
    """
    def uses_supported_transport(url):
        supported_transports = set(['sync+', 'requests+'])
        return any(url.startswith(prefix) for prefix in supported_transports)

    if not any(uses_supported_transport(s) for s in client.servers):
        msg = ('Sentry error delivery is known to be unreliable when not '
               'delivered synchronously from RQ workers.  You are encouraged '
               'to change your DSN to use the sync+ or requests+ transport '
               'prefix.')
        warnings.warn(msg, UserWarning, stacklevel=2)

    def send_to_sentry(job, *exc_info):
        client.captureException(
            exc_info=exc_info,
            extra={
                'job_id': job.id,
                'func': job.func_name,
                'args': job.args,
                'kwargs': job.kwargs,
                'description': job.description,
            })

    worker.push_exc_handler(send_to_sentry)

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from functools import wraps

from rq.compat import string_types

from .queue import Queue
from .worker import DEFAULT_RESULT_TTL


class job(object):
    def __init__(self, queue, connection=None, timeout=None,
                 result_ttl=DEFAULT_RESULT_TTL):
        """A decorator that adds a ``delay`` method to the decorated function,
        which in turn creates a RQ job when called. Accepts a required
        ``queue`` argument that can be either a ``Queue`` instance or a string
        denoting the queue name.  For example:

            @job(queue='default')
            def simple_add(x, y):
                return x + y

            simple_add.delay(1, 2) # Puts simple_add function into queue
        """
        self.queue = queue
        self.connection = connection
        self.timeout = timeout
        self.result_ttl = result_ttl

    def __call__(self, f):
        @wraps(f)
        def delay(*args, **kwargs):
            if isinstance(self.queue, string_types):
                queue = Queue(name=self.queue, connection=self.connection)
            else:
                queue = self.queue
            if 'depends_on' in kwargs:
                depends_on = kwargs.pop('depends_on')
            else:
                depends_on = None
            return queue.enqueue_call(f, args=args, kwargs=kwargs,
                                      timeout=self.timeout, result_ttl=self.result_ttl, depends_on=depends_on)
        f.delay = delay
        return f

########NEW FILE########
__FILENAME__ = dummy
# -*- coding: utf-8 -*-
"""
Some dummy tasks that are well-suited for generating load for testing purposes.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import random
import time


def do_nothing():
    pass


def sleep(secs):
    time.sleep(secs)


def endless_loop():
    while True:
        time.sleep(1)


def div_by_zero():
    1 / 0


def fib(n):
    if n <= 1:
        return 1
    else:
        return fib(n - 2) + fib(n - 1)


def random_failure():
    if random.choice([True, False]):
        class RandomError(Exception):
            pass
        raise RandomError('Ouch!')
    return 'OK'

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class NoSuchJobError(Exception):
    pass


class InvalidJobOperationError(Exception):
    pass


class NoQueueError(Exception):
    pass


class UnpickleError(Exception):
    def __init__(self, message, raw_data, inner_exception=None):
        super(UnpickleError, self).__init__(message, inner_exception)
        self.raw_data = raw_data


class DequeueTimeout(Exception):
    pass

########NEW FILE########
__FILENAME__ = job
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import inspect
from uuid import uuid4

from rq.compat import as_text, decode_redis_hash, string_types, text_type

from .connections import resolve_connection
from .exceptions import NoSuchJobError, UnpickleError
from .local import LocalStack
from .utils import import_attribute, utcformat, utcnow, utcparse

try:
    from cPickle import loads, dumps, UnpicklingError
except ImportError:  # noqa
    from pickle import loads, dumps, UnpicklingError  # noqa


def enum(name, *sequential, **named):
    values = dict(zip(sequential, range(len(sequential))), **named)

    # NOTE: Yes, we *really* want to cast using str() here.
    # On Python 2 type() requires a byte string (which is str() on Python 2).
    # On Python 3 it does not matter, so we'll use str(), which acts as
    # a no-op.
    return type(str(name), (), values)

Status = enum('Status',
              QUEUED='queued', FINISHED='finished', FAILED='failed',
              STARTED='started')

# Sentinel value to mark that some of our lazily evaluated properties have not
# yet been evaluated.
UNEVALUATED = object()


def unpickle(pickled_string):
    """Unpickles a string, but raises a unified UnpickleError in case anything
    fails.

    This is a helper method to not have to deal with the fact that `loads()`
    potentially raises many types of exceptions (e.g. AttributeError,
    IndexError, TypeError, KeyError, etc.)
    """
    try:
        obj = loads(pickled_string)
    except (Exception, UnpicklingError) as e:
        raise UnpickleError('Could not unpickle.', pickled_string, e)
    return obj


def cancel_job(job_id, connection=None):
    """Cancels the job with the given job ID, preventing execution.  Discards
    any job info (i.e. it can't be requeued later).
    """
    Job(job_id, connection=connection).cancel()


def requeue_job(job_id, connection=None):
    """Requeues the job with the given job ID.  The job ID should refer to
    a failed job (i.e. it should be on the failed queue).  If no such (failed)
    job exists, a NoSuchJobError is raised.
    """
    from .queue import get_failed_queue
    fq = get_failed_queue(connection=connection)
    fq.requeue(job_id)


def get_current_job(connection=None):
    """Returns the Job instance that is currently being executed.  If this
    function is invoked from outside a job context, None is returned.
    """
    job_id = _job_stack.top
    if job_id is None:
        return None
    return Job.fetch(job_id, connection=connection)


class Job(object):
    """A Job is just a convenient datastructure to pass around job (meta) data.
    """

    # Job construction
    @classmethod
    def create(cls, func, args=None, kwargs=None, connection=None,
               result_ttl=None, status=None, description=None, depends_on=None, timeout=None):
        """Creates a new Job instance for the given function, arguments, and
        keyword arguments.
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        if not isinstance(args, (tuple, list)):
            raise TypeError('{0!r} is not a valid args list.'.format(args))
        if not isinstance(kwargs, dict):
            raise TypeError('{0!r} is not a valid kwargs dict.'.format(kwargs))

        job = cls(connection=connection)

        # Set the core job tuple properties
        job._instance = None
        if inspect.ismethod(func):
            job._instance = func.__self__
            job._func_name = func.__name__
        elif inspect.isfunction(func) or inspect.isbuiltin(func):
            job._func_name = '%s.%s' % (func.__module__, func.__name__)
        elif isinstance(func, string_types):
            job._func_name = as_text(func)
        else:
            raise TypeError('Expected a function/method/string, but got: {}'.format(func))
        job._args = args
        job._kwargs = kwargs

        # Extra meta data
        job.description = description or job.get_call_string()
        job.result_ttl = result_ttl
        job.timeout = timeout
        job._status = status

        # dependency could be job instance or id
        if depends_on is not None:
            job._dependency_id = depends_on.id if isinstance(depends_on, Job) else depends_on
        return job

    def get_status(self):
        self._status = as_text(self.connection.hget(self.key, 'status'))
        return self._status

    def _get_status(self):
        raise DeprecationWarning(
            "job.status is deprecated. Use job.get_status() instead"
        )
        return self.get_status()

    def set_status(self, status):
        self._status = status
        self.connection.hset(self.key, 'status', self._status)

    def _set_status(self, status):
        raise DeprecationWarning(
            "job.status is deprecated. Use job.set_status() instead"
        )
        self.set_status(status)

    status = property(_get_status, _set_status)

    @property
    def is_finished(self):
        return self.get_status() == Status.FINISHED

    @property
    def is_queued(self):
        return self.get_status() == Status.QUEUED

    @property
    def is_failed(self):
        return self.get_status() == Status.FAILED

    @property
    def is_started(self):
        return self.get_status() == Status.STARTED

    @property
    def dependency(self):
        """Returns a job's dependency. To avoid repeated Redis fetches, we cache
        job.dependency as job._dependency.
        """
        if self._dependency_id is None:
            return None
        if hasattr(self, '_dependency'):
            return self._dependency
        job = Job.fetch(self._dependency_id, connection=self.connection)
        job.refresh()
        self._dependency = job
        return job

    @property
    def func(self):
        func_name = self.func_name
        if func_name is None:
            return None

        if self.instance:
            return getattr(self.instance, func_name)

        return import_attribute(self.func_name)

    def _unpickle_data(self):
        self._func_name, self._instance, self._args, self._kwargs = unpickle(self.data)

    @property
    def data(self):
        if self._data is UNEVALUATED:
            if self._func_name is UNEVALUATED:
                raise ValueError('Cannot build the job data.')

            if self._instance is UNEVALUATED:
                self._instance = None

            if self._args is UNEVALUATED:
                self._args = ()

            if self._kwargs is UNEVALUATED:
                self._kwargs = {}

            job_tuple = self._func_name, self._instance, self._args, self._kwargs
            self._data = dumps(job_tuple)
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self._func_name = UNEVALUATED
        self._instance = UNEVALUATED
        self._args = UNEVALUATED
        self._kwargs = UNEVALUATED

    @property
    def func_name(self):
        if self._func_name is UNEVALUATED:
            self._unpickle_data()
        return self._func_name

    @func_name.setter
    def func_name(self, value):
        self._func_name = value
        self._data = UNEVALUATED

    @property
    def instance(self):
        if self._instance is UNEVALUATED:
            self._unpickle_data()
        return self._instance

    @instance.setter
    def instance(self, value):
        self._instance = value
        self._data = UNEVALUATED

    @property
    def args(self):
        if self._args is UNEVALUATED:
            self._unpickle_data()
        return self._args

    @args.setter
    def args(self, value):
        self._args = value
        self._data = UNEVALUATED

    @property
    def kwargs(self):
        if self._kwargs is UNEVALUATED:
            self._unpickle_data()
        return self._kwargs

    @kwargs.setter
    def kwargs(self, value):
        self._kwargs = value
        self._data = UNEVALUATED

    @classmethod
    def exists(cls, job_id, connection=None):
        """Returns whether a job hash exists for the given job ID."""
        conn = resolve_connection(connection)
        return conn.exists(cls.key_for(job_id))

    @classmethod
    def fetch(cls, id, connection=None):
        """Fetches a persisted job from its corresponding Redis key and
        instantiates it.
        """
        job = cls(id, connection=connection)
        job.refresh()
        return job

    def __init__(self, id=None, connection=None):
        self.connection = resolve_connection(connection)
        self._id = id
        self.created_at = utcnow()
        self._data = UNEVALUATED
        self._func_name = UNEVALUATED
        self._instance = UNEVALUATED
        self._args = UNEVALUATED
        self._kwargs = UNEVALUATED
        self.description = None
        self.origin = None
        self.enqueued_at = None
        self.ended_at = None
        self._result = None
        self.exc_info = None
        self.timeout = None
        self.result_ttl = None
        self._status = None
        self._dependency_id = None
        self.meta = {}

    def __repr__(self):  # noqa
        return 'Job(%r, enqueued_at=%r)' % (self._id, self.enqueued_at)

    # Data access
    def get_id(self):  # noqa
        """The job ID for this job instance. Generates an ID lazily the
        first time the ID is requested.
        """
        if self._id is None:
            self._id = text_type(uuid4())
        return self._id

    def set_id(self, value):
        """Sets a job ID for the given job."""
        self._id = value

    id = property(get_id, set_id)

    @classmethod
    def key_for(cls, job_id):
        """The Redis key that is used to store job hash under."""
        return b'rq:job:' + job_id.encode('utf-8')

    @classmethod
    def dependents_key_for(cls, job_id):
        """The Redis key that is used to store job hash under."""
        return 'rq:job:%s:dependents' % (job_id,)

    @property
    def key(self):
        """The Redis key that is used to store job hash under."""
        return self.key_for(self.id)

    @property
    def dependents_key(self):
        """The Redis key that is used to store job hash under."""
        return self.dependents_key_for(self.id)

    @property
    def result(self):
        """Returns the return value of the job.

        Initially, right after enqueueing a job, the return value will be
        None.  But when the job has been executed, and had a return value or
        exception, this will return that value or exception.

        Note that, when the job has no return value (i.e. returns None), the
        ReadOnlyJob object is useless, as the result won't be written back to
        Redis.

        Also note that you cannot draw the conclusion that a job has _not_
        been executed when its return value is None, since return values
        written back to Redis will expire after a given amount of time (500
        seconds by default).
        """
        if self._result is None:
            rv = self.connection.hget(self.key, 'result')
            if rv is not None:
                # cache the result
                self._result = loads(rv)
        return self._result

    """Backwards-compatibility accessor property `return_value`."""
    return_value = result

    # Persistence
    def refresh(self):  # noqa
        """Overwrite the current instance's properties with the values in the
        corresponding Redis key.

        Will raise a NoSuchJobError if no corresponding Redis key exists.
        """
        key = self.key
        obj = decode_redis_hash(self.connection.hgetall(key))
        if len(obj) == 0:
            raise NoSuchJobError('No such job: %s' % (key,))

        def to_date(date_str):
            if date_str is None:
                return
            else:
                return utcparse(as_text(date_str))

        try:
            self.data = obj['data']
        except KeyError:
            raise NoSuchJobError('Unexpected job format: {0}'.format(obj))

        self.created_at = to_date(as_text(obj.get('created_at')))
        self.origin = as_text(obj.get('origin'))
        self.description = as_text(obj.get('description'))
        self.enqueued_at = to_date(as_text(obj.get('enqueued_at')))
        self.ended_at = to_date(as_text(obj.get('ended_at')))
        self._result = unpickle(obj.get('result')) if obj.get('result') else None  # noqa
        self.exc_info = obj.get('exc_info')
        self.timeout = int(obj.get('timeout')) if obj.get('timeout') else None
        self.result_ttl = int(obj.get('result_ttl')) if obj.get('result_ttl') else None  # noqa
        self._status = as_text(obj.get('status') if obj.get('status') else None)
        self._dependency_id = as_text(obj.get('dependency_id', None))
        self.meta = unpickle(obj.get('meta')) if obj.get('meta') else {}

    def dump(self):
        """Returns a serialization of the current job instance"""
        obj = {}
        obj['created_at'] = utcformat(self.created_at or utcnow())
        obj['data'] = self.data

        if self.origin is not None:
            obj['origin'] = self.origin
        if self.description is not None:
            obj['description'] = self.description
        if self.enqueued_at is not None:
            obj['enqueued_at'] = utcformat(self.enqueued_at)
        if self.ended_at is not None:
            obj['ended_at'] = utcformat(self.ended_at)
        if self._result is not None:
            obj['result'] = dumps(self._result)
        if self.exc_info is not None:
            obj['exc_info'] = self.exc_info
        if self.timeout is not None:
            obj['timeout'] = self.timeout
        if self.result_ttl is not None:
            obj['result_ttl'] = self.result_ttl
        if self._status is not None:
            obj['status'] = self._status
        if self._dependency_id is not None:
            obj['dependency_id'] = self._dependency_id
        if self.meta:
            obj['meta'] = dumps(self.meta)

        return obj

    def save(self, pipeline=None):
        """Persists the current job instance to its corresponding Redis key."""
        key = self.key
        connection = pipeline if pipeline is not None else self.connection

        connection.hmset(key, self.dump())

    def cancel(self):
        """Cancels the given job, which will prevent the job from ever being
        ran (or inspected).

        This method merely exists as a high-level API call to cancel jobs
        without worrying about the internals required to implement job
        cancellation.  Technically, this call is (currently) the same as just
        deleting the job hash.
        """
        pipeline = self.connection._pipeline()
        self.delete(pipeline=pipeline)
        pipeline.delete(self.dependents_key)
        pipeline.execute()

    def delete(self, pipeline=None):
        """Deletes the job hash from Redis."""
        connection = pipeline if pipeline is not None else self.connection
        connection.delete(self.key)

    # Job execution
    def perform(self):  # noqa
        """Invokes the job function with the job arguments."""
        _job_stack.push(self.id)
        try:
            self.set_status(Status.STARTED)
            self._result = self.func(*self.args, **self.kwargs)
            self.set_status(Status.FINISHED)
            self.ended_at = utcnow()
        finally:
            assert self.id == _job_stack.pop()

        return self._result

    def get_ttl(self, default_ttl=None):
        """Returns ttl for a job that determines how long a job and its result
        will be persisted. In the future, this method will also be responsible
        for determining ttl for repeated jobs.
        """
        return default_ttl if self.result_ttl is None else self.result_ttl

    # Representation
    def get_call_string(self):  # noqa
        """Returns a string representation of the call, formatted as a regular
        Python function invocation statement.
        """
        if self.func_name is None:
            return None

        arg_list = [repr(arg) for arg in self.args]
        arg_list += ['%s=%r' % (k, v) for k, v in self.kwargs.items()]
        args = ', '.join(arg_list)
        return '%s(%s)' % (self.func_name, args)

    def cleanup(self, ttl=None, pipeline=None):
        """Prepare job for eventual deletion (if needed). This method is usually
        called after successful execution. How long we persist the job and its
        result depends on the value of result_ttl:
        - If result_ttl is 0, cleanup the job immediately.
        - If it's a positive number, set the job to expire in X seconds.
        - If result_ttl is negative, don't set an expiry to it (persist
          forever)
        """
        if ttl == 0:
            self.cancel()
        elif ttl > 0:
            connection = pipeline if pipeline is not None else self.connection
            connection.expire(self.key, ttl)

    def register_dependency(self):
        """Jobs may have dependencies. Jobs are enqueued only if the job they
        depend on is successfully performed. We record this relation as
        a reverse dependency (a Redis set), with a key that looks something
        like:

            rq:job:job_id:dependents = {'job_id_1', 'job_id_2'}

        This method adds the current job in its dependency's dependents set.
        """
        # TODO: This can probably be pipelined
        self.connection.sadd(Job.dependents_key_for(self._dependency_id), self.id)

    def __str__(self):
        return '<Job %s: %s>' % (self.id, self.description)

    # Job equality
    def __eq__(self, other):  # noqa
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

_job_stack = LocalStack()

########NEW FILE########
__FILENAME__ = local
# -*- coding: utf-8 -*-
"""
    werkzeug.local
    ~~~~~~~~~~~~~~

    This module implements context-local objects.

    :copyright: (c) 2011 by the Werkzeug Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
# Since each thread has its own greenlet we can just use those as identifiers
# for the context.  If greenlets are not available we fall back to the
# current thread ident.
try:
    from greenlet import getcurrent as get_ident
except ImportError:  # noqa
    try:
        from thread import get_ident  # noqa
    except ImportError:  # noqa
        try:
            from _thread import get_ident  # noqa
        except ImportError:  # noqa
            from dummy_thread import get_ident  # noqa


def release_local(local):
    """Releases the contents of the local for the current context.
    This makes it possible to use locals without a manager.

    Example::

        >>> loc = Local()
        >>> loc.foo = 42
        >>> release_local(loc)
        >>> hasattr(loc, 'foo')
        False

    With this function one can release :class:`Local` objects as well
    as :class:`StackLocal` objects.  However it is not possible to
    release data held by proxies that way, one always has to retain
    a reference to the underlying local object in order to be able
    to release it.

    .. versionadded:: 0.6.1
    """
    local.__release_local__()


class Local(object):
    __slots__ = ('__storage__', '__ident_func__')

    def __init__(self):
        object.__setattr__(self, '__storage__', {})
        object.__setattr__(self, '__ident_func__', get_ident)

    def __iter__(self):
        return iter(self.__storage__.items())

    def __call__(self, proxy):
        """Create a proxy for a name."""
        return LocalProxy(self, proxy)

    def __release_local__(self):
        self.__storage__.pop(self.__ident_func__(), None)

    def __getattr__(self, name):
        try:
            return self.__storage__[self.__ident_func__()][name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        ident = self.__ident_func__()
        storage = self.__storage__
        try:
            storage[ident][name] = value
        except KeyError:
            storage[ident] = {name: value}

    def __delattr__(self, name):
        try:
            del self.__storage__[self.__ident_func__()][name]
        except KeyError:
            raise AttributeError(name)


class LocalStack(object):
    """This class works similar to a :class:`Local` but keeps a stack
    of objects instead.  This is best explained with an example::

        >>> ls = LocalStack()
        >>> ls.push(42)
        >>> ls.top
        42
        >>> ls.push(23)
        >>> ls.top
        23
        >>> ls.pop()
        23
        >>> ls.top
        42

    They can be force released by using a :class:`LocalManager` or with
    the :func:`release_local` function but the correct way is to pop the
    item from the stack after using.  When the stack is empty it will
    no longer be bound to the current context (and as such released).

    By calling the stack without arguments it returns a proxy that resolves to
    the topmost item on the stack.

    .. versionadded:: 0.6.1
    """

    def __init__(self):
        self._local = Local()

    def __release_local__(self):
        self._local.__release_local__()

    def _get__ident_func__(self):
        return self._local.__ident_func__

    def _set__ident_func__(self, value):  # noqa
        object.__setattr__(self._local, '__ident_func__', value)
    __ident_func__ = property(_get__ident_func__, _set__ident_func__)
    del _get__ident_func__, _set__ident_func__

    def __call__(self):
        def _lookup():
            rv = self.top
            if rv is None:
                raise RuntimeError('object unbound')
            return rv
        return LocalProxy(_lookup)

    def push(self, obj):
        """Pushes a new item to the stack"""
        rv = getattr(self._local, 'stack', None)
        if rv is None:
            self._local.stack = rv = []
        rv.append(obj)
        return rv

    def pop(self):
        """Removes the topmost item from the stack, will return the
        old value or `None` if the stack was already empty.
        """
        stack = getattr(self._local, 'stack', None)
        if stack is None:
            return None
        elif len(stack) == 1:
            release_local(self._local)
            return stack[-1]
        else:
            return stack.pop()

    @property
    def top(self):
        """The topmost item on the stack.  If the stack is empty,
        `None` is returned.
        """
        try:
            return self._local.stack[-1]
        except (AttributeError, IndexError):
            return None

    def __len__(self):
        stack = getattr(self._local, 'stack', None)
        if stack is None:
            return 0
        return len(stack)


class LocalManager(object):
    """Local objects cannot manage themselves. For that you need a local
    manager.  You can pass a local manager multiple locals or add them later
    by appending them to `manager.locals`.  Everytime the manager cleans up
    it, will clean up all the data left in the locals for this context.

    The `ident_func` parameter can be added to override the default ident
    function for the wrapped locals.

    .. versionchanged:: 0.6.1
       Instead of a manager the :func:`release_local` function can be used
       as well.

    .. versionchanged:: 0.7
       `ident_func` was added.
    """

    def __init__(self, locals=None, ident_func=None):
        if locals is None:
            self.locals = []
        elif isinstance(locals, Local):
            self.locals = [locals]
        else:
            self.locals = list(locals)
        if ident_func is not None:
            self.ident_func = ident_func
            for local in self.locals:
                object.__setattr__(local, '__ident_func__', ident_func)
        else:
            self.ident_func = get_ident

    def get_ident(self):
        """Return the context identifier the local objects use internally for
        this context.  You cannot override this method to change the behavior
        but use it to link other context local objects (such as SQLAlchemy's
        scoped sessions) to the Werkzeug locals.

        .. versionchanged:: 0.7
           You can pass a different ident function to the local manager that
           will then be propagated to all the locals passed to the
           constructor.
        """
        return self.ident_func()

    def cleanup(self):
        """Manually clean up the data in the locals for this context.  Call
        this at the end of the request or use `make_middleware()`.
        """
        for local in self.locals:
            release_local(local)

    def __repr__(self):
        return '<%s storages: %d>' % (
            self.__class__.__name__,
            len(self.locals)
        )


class LocalProxy(object):
    """Acts as a proxy for a werkzeug local.  Forwards all operations to
    a proxied object.  The only operations not supported for forwarding
    are right handed operands and any kind of assignment.

    Example usage::

        from werkzeug.local import Local
        l = Local()

        # these are proxies
        request = l('request')
        user = l('user')


        from werkzeug.local import LocalStack
        _response_local = LocalStack()

        # this is a proxy
        response = _response_local()

    Whenever something is bound to l.user / l.request the proxy objects
    will forward all operations.  If no object is bound a :exc:`RuntimeError`
    will be raised.

    To create proxies to :class:`Local` or :class:`LocalStack` objects,
    call the object as shown above.  If you want to have a proxy to an
    object looked up by a function, you can (as of Werkzeug 0.6.1) pass
    a function to the :class:`LocalProxy` constructor::

        session = LocalProxy(lambda: get_current_request().session)

    .. versionchanged:: 0.6.1
       The class can be instanciated with a callable as well now.
    """
    __slots__ = ('__local', '__dict__', '__name__')

    def __init__(self, local, name=None):
        object.__setattr__(self, '_LocalProxy__local', local)
        object.__setattr__(self, '__name__', name)

    def _get_current_object(self):
        """Return the current object.  This is useful if you want the real
        object behind the proxy at a time for performance reasons or because
        you want to pass the object into a different context.
        """
        if not hasattr(self.__local, '__release_local__'):
            return self.__local()
        try:
            return getattr(self.__local, self.__name__)
        except AttributeError:
            raise RuntimeError('no object bound to %s' % self.__name__)

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
    __call__ = lambda x, *a, **kw: x._get_current_object()(*a, **kw)
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
    __coerce__ = lambda x, o: x._get_current_object().__coerce__(x, o)
    __enter__ = lambda x: x._get_current_object().__enter__()
    __exit__ = lambda x, *a, **kw: x._get_current_object().__exit__(*a, **kw)

########NEW FILE########
__FILENAME__ = logutils
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

# Make sure that dictConfig is available
# This was added in Python 2.7/3.2
try:
    from logging.config import dictConfig
except ImportError:
    from rq.compat.dictconfig import dictConfig  # noqa


def setup_loghandlers(level=None):
    if not logging._handlers:
        dictConfig({
            'version': 1,
            'disable_existing_loggers': False,

            'formatters': {
                'console': {
                    'format': '%(asctime)s %(message)s',
                    'datefmt': '%H:%M:%S',
                },
            },

            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    # 'class': 'logging.StreamHandler',
                    'class': 'rq.utils.ColorizingStreamHandler',
                    'formatter': 'console',
                    'exclude': ['%(asctime)s'],
                },
            },

            'root': {
                'handlers': ['console'],
                'level': level or 'INFO',
            }
        })

########NEW FILE########
__FILENAME__ = queue
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import uuid

from .connections import resolve_connection
from .job import Job, Status
from .utils import utcnow

from .exceptions import (DequeueTimeout, InvalidJobOperationError,
                         NoSuchJobError, UnpickleError)
from .compat import total_ordering, string_types, as_text

from redis import WatchError


def get_failed_queue(connection=None):
    """Returns a handle to the special failed queue."""
    return FailedQueue(connection=connection)


def compact(lst):
    return [item for item in lst if item is not None]


@total_ordering
class Queue(object):
    job_class = Job
    DEFAULT_TIMEOUT = 180  # Default timeout seconds.
    redis_queue_namespace_prefix = 'rq:queue:'
    redis_queues_keys = 'rq:queues'

    @classmethod
    def all(cls, connection=None):
        """Returns an iterable of all Queues.
        """
        connection = resolve_connection(connection)

        def to_queue(queue_key):
            return cls.from_queue_key(as_text(queue_key),
                                      connection=connection)
        return [to_queue(rq_key) for rq_key in connection.smembers(cls.redis_queues_keys) if rq_key]

    @classmethod
    def from_queue_key(cls, queue_key, connection=None):
        """Returns a Queue instance, based on the naming conventions for naming
        the internal Redis keys.  Can be used to reverse-lookup Queues by their
        Redis keys.
        """
        prefix = cls.redis_queue_namespace_prefix
        if not queue_key.startswith(prefix):
            raise ValueError('Not a valid RQ queue key: %s' % (queue_key,))
        name = queue_key[len(prefix):]
        return cls(name, connection=connection)

    def __init__(self, name='default', default_timeout=None, connection=None,
                 async=True):
        self.connection = resolve_connection(connection)
        prefix = self.redis_queue_namespace_prefix
        self.name = name
        self._key = '%s%s' % (prefix, name)
        self._default_timeout = default_timeout
        self._async = async

    @property
    def key(self):
        """Returns the Redis key for this Queue."""
        return self._key

    def empty(self):
        """Removes all messages on the queue."""
        script = b"""
            local prefix = "rq:job:"
            local q = KEYS[1]
            local count = 0
            while true do
                local job_id = redis.call("lpop", q)
                if job_id == false then
                    break
                end

                -- Delete the relevant keys
                redis.call("del", prefix..job_id)
                redis.call("del", prefix..job_id..":dependents")
                count = count + 1
            end
            return count
        """
        script = self.connection.register_script(script)
        return script(keys=[self.key])

    def is_empty(self):
        """Returns whether the current queue is empty."""
        return self.count == 0

    def fetch_job(self, job_id):
        try:
            return self.job_class.fetch(job_id, connection=self.connection)
        except NoSuchJobError:
            self.remove(job_id)

    def get_job_ids(self, offset=0, length=-1):
        """Returns a slice of job IDs in the queue."""
        start = offset
        if length >= 0:
            end = offset + (length - 1)
        else:
            end = length
        return [as_text(job_id) for job_id in
                self.connection.lrange(self.key, start, end)]

    def get_jobs(self, offset=0, length=-1):
        """Returns a slice of jobs in the queue."""
        job_ids = self.get_job_ids(offset, length)
        return compact([self.fetch_job(job_id) for job_id in job_ids])

    @property
    def job_ids(self):
        """Returns a list of all job IDS in the queue."""
        return self.get_job_ids()

    @property
    def jobs(self):
        """Returns a list of all (valid) jobs in the queue."""
        return self.get_jobs()

    @property
    def count(self):
        """Returns a count of all messages in the queue."""
        return self.connection.llen(self.key)

    def remove(self, job_or_id):
        """Removes Job from queue, accepts either a Job instance or ID."""
        job_id = job_or_id.id if isinstance(job_or_id, self.job_class) else job_or_id
        return self.connection._lrem(self.key, 0, job_id)

    def compact(self):
        """Removes all "dead" jobs from the queue by cycling through it, while
        guarantueeing FIFO semantics.
        """
        COMPACT_QUEUE = 'rq:queue:_compact:{0}'.format(uuid.uuid4())

        self.connection.rename(self.key, COMPACT_QUEUE)
        while True:
            job_id = as_text(self.connection.lpop(COMPACT_QUEUE))
            if job_id is None:
                break
            if self.job_class.exists(job_id, self.connection):
                self.connection.rpush(self.key, job_id)

    def push_job_id(self, job_id):
        """Pushes a job ID on the corresponding Redis queue."""
        self.connection.rpush(self.key, job_id)

    def enqueue_call(self, func, args=None, kwargs=None, timeout=None,
                     result_ttl=None, description=None, depends_on=None):
        """Creates a job to represent the delayed function call and enqueues
        it.

        It is much like `.enqueue()`, except that it takes the function's args
        and kwargs as explicit arguments.  Any kwargs passed to this function
        contain options for RQ itself.
        """
        timeout = timeout or self._default_timeout

        # TODO: job with dependency shouldn't have "queued" as status
        job = self.job_class.create(func, args, kwargs, connection=self.connection,
                                    result_ttl=result_ttl, status=Status.QUEUED,
                                    description=description, depends_on=depends_on, timeout=timeout)

        # If job depends on an unfinished job, register itself on it's
        # parent's dependents instead of enqueueing it.
        # If WatchError is raised in the process, that means something else is
        # modifying the dependency. In this case we simply retry
        if depends_on is not None:
            with self.connection.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch(depends_on.key)
                        if depends_on.get_status() != Status.FINISHED:
                            job.register_dependency()
                            job.save()
                            return job
                        break
                    except WatchError:
                        continue

        return self.enqueue_job(job)

    def enqueue(self, f, *args, **kwargs):
        """Creates a job to represent the delayed function call and enqueues
        it.

        Expects the function to call, along with the arguments and keyword
        arguments.

        The function argument `f` may be any of the following:

        * A reference to a function
        * A reference to an object's instance method
        * A string, representing the location of a function (must be
          meaningful to the import context of the workers)
        """
        if not isinstance(f, string_types) and f.__module__ == '__main__':
            raise ValueError('Functions from the __main__ module cannot be processed '
                             'by workers.')

        # Detect explicit invocations, i.e. of the form:
        #     q.enqueue(foo, args=(1, 2), kwargs={'a': 1}, timeout=30)
        timeout = kwargs.pop('timeout', None)
        description = kwargs.pop('description', None)
        result_ttl = kwargs.pop('result_ttl', None)
        depends_on = kwargs.pop('depends_on', None)

        if 'args' in kwargs or 'kwargs' in kwargs:
            assert args == (), 'Extra positional arguments cannot be used when using explicit args and kwargs.'  # noqa
            args = kwargs.pop('args', None)
            kwargs = kwargs.pop('kwargs', None)

        return self.enqueue_call(func=f, args=args, kwargs=kwargs,
                                 timeout=timeout, result_ttl=result_ttl,
                                 description=description, depends_on=depends_on)

    def enqueue_job(self, job, set_meta_data=True):
        """Enqueues a job for delayed execution.

        If the `set_meta_data` argument is `True` (default), it will update
        the properties `origin` and `enqueued_at`.

        If Queue is instantiated with async=False, job is executed immediately.
        """
        # Add Queue key set
        self.connection.sadd(self.redis_queues_keys, self.key)

        if set_meta_data:
            job.origin = self.name
            job.enqueued_at = utcnow()

        if job.timeout is None:
            job.timeout = self.DEFAULT_TIMEOUT
        job.save()

        if self._async:
            self.push_job_id(job.id)
        else:
            job.perform()
            job.save()
        return job

    def enqueue_dependents(self, job):
        """Enqueues all jobs in the given job's dependents set and clears it."""
        # TODO: can probably be pipelined
        while True:
            job_id = as_text(self.connection.spop(job.dependents_key))
            if job_id is None:
                break
            dependent = self.job_class.fetch(job_id, connection=self.connection)
            self.enqueue_job(dependent)

    def pop_job_id(self):
        """Pops a given job ID from this Redis queue."""
        return as_text(self.connection.lpop(self.key))

    @classmethod
    def lpop(cls, queue_keys, timeout, connection=None):
        """Helper method.  Intermediate method to abstract away from some
        Redis API details, where LPOP accepts only a single key, whereas BLPOP
        accepts multiple.  So if we want the non-blocking LPOP, we need to
        iterate over all queues, do individual LPOPs, and return the result.

        Until Redis receives a specific method for this, we'll have to wrap it
        this way.

        The timeout parameter is interpreted as follows:
            None - non-blocking (return immediately)
             > 0 - maximum number of seconds to block
        """
        connection = resolve_connection(connection)
        if timeout is not None:  # blocking variant
            if timeout == 0:
                raise ValueError('RQ does not support indefinite timeouts. Please pick a timeout value > 0.')
            result = connection.blpop(queue_keys, timeout)
            if result is None:
                raise DequeueTimeout(timeout, queue_keys)
            queue_key, job_id = result
            return queue_key, job_id
        else:  # non-blocking variant
            for queue_key in queue_keys:
                blob = connection.lpop(queue_key)
                if blob is not None:
                    return queue_key, blob
            return None

    def dequeue(self):
        """Dequeues the front-most job from this queue.

        Returns a job_class instance, which can be executed or inspected.
        """
        job_id = self.pop_job_id()
        if job_id is None:
            return None
        try:
            job = self.job_class.fetch(job_id, connection=self.connection)
        except NoSuchJobError as e:
            # Silently pass on jobs that don't exist (anymore),
            # and continue by reinvoking itself recursively
            return self.dequeue()
        except UnpickleError as e:
            # Attach queue information on the exception for improved error
            # reporting
            e.job_id = job_id
            e.queue = self
            raise e
        return job

    @classmethod
    def dequeue_any(cls, queues, timeout, connection=None):
        """Class method returning the job_class instance at the front of the given
        set of Queues, where the order of the queues is important.

        When all of the Queues are empty, depending on the `timeout` argument,
        either blocks execution of this function for the duration of the
        timeout or until new messages arrive on any of the queues, or returns
        None.

        See the documentation of cls.lpop for the interpretation of timeout.
        """
        queue_keys = [q.key for q in queues]
        result = cls.lpop(queue_keys, timeout, connection=connection)
        if result is None:
            return None
        queue_key, job_id = map(as_text, result)
        queue = cls.from_queue_key(queue_key, connection=connection)
        try:
            job = cls.job_class.fetch(job_id, connection=connection)
        except NoSuchJobError:
            # Silently pass on jobs that don't exist (anymore),
            # and continue by reinvoking the same function recursively
            return cls.dequeue_any(queues, timeout, connection=connection)
        except UnpickleError as e:
            # Attach queue information on the exception for improved error
            # reporting
            e.job_id = job_id
            e.queue = queue
            raise e
        return job, queue

    # Total ordering defition (the rest of the required Python methods are
    # auto-generated by the @total_ordering decorator)
    def __eq__(self, other):  # noqa
        if not isinstance(other, Queue):
            raise TypeError('Cannot compare queues to other objects.')
        return self.name == other.name

    def __lt__(self, other):
        if not isinstance(other, Queue):
            raise TypeError('Cannot compare queues to other objects.')
        return self.name < other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):  # noqa
        return 'Queue(%r)' % (self.name,)

    def __str__(self):
        return '<Queue \'%s\'>' % (self.name,)


class FailedQueue(Queue):
    def __init__(self, connection=None):
        super(FailedQueue, self).__init__(Status.FAILED, connection=connection)

    def quarantine(self, job, exc_info):
        """Puts the given Job in quarantine (i.e. put it on the failed
        queue).

        This is different from normal job enqueueing, since certain meta data
        must not be overridden (e.g. `origin` or `enqueued_at`) and other meta
        data must be inserted (`ended_at` and `exc_info`).
        """
        job.ended_at = utcnow()
        job.exc_info = exc_info
        return self.enqueue_job(job, set_meta_data=False)

    def requeue(self, job_id):
        """Requeues the job with the given job ID."""
        try:
            job = self.job_class.fetch(job_id, connection=self.connection)
        except NoSuchJobError:
            # Silently ignore/remove this job and return (i.e. do nothing)
            self.remove(job_id)
            return

        # Delete it from the failed queue (raise an error if that failed)
        if self.remove(job) == 0:
            raise InvalidJobOperationError('Cannot requeue non-failed jobs.')

        job.set_status(Status.QUEUED)
        job.exc_info = None
        q = Queue(job.origin, connection=self.connection)
        q.enqueue_job(job)

########NEW FILE########
__FILENAME__ = rqgenload
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import optparse

from rq import dummy, Queue, use_connection


def parse_args():
    parser = optparse.OptionParser()
    parser.add_option('-n', '--count', type='int', dest='count', default=1)
    opts, args = parser.parse_args()
    return (opts, args, parser)


def main():
    import sys
    sys.path.insert(0, '.')

    opts, args, parser = parse_args()

    use_connection()

    queues = ('default', 'high', 'low')

    sample_calls = [
        (dummy.do_nothing, [], {}),
        (dummy.sleep, [1], {}),
        (dummy.fib, [8], {}),              # normal result
        (dummy.fib, [24], {}),             # takes pretty long
        (dummy.div_by_zero, [], {}),       # 5 / 0 => div by zero exc
        (dummy.random_failure, [], {}),    # simulate random failure (handy for requeue testing)
    ]

    for i in range(opts.count):
        import random
        f, args, kwargs = random.choice(sample_calls)

        q = Queue(random.choice(queues))
        q.enqueue(f, *args, **kwargs)

        # q = Queue('foo')
        # q.enqueue(do_nothing)
        # q.enqueue(sleep, 3)
        # q = Queue('bar')
        # q.enqueue(yield_stuff)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)
        # q.enqueue(do_nothing)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rqinfo
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import os
import sys
import time

from redis.exceptions import ConnectionError
from rq import get_failed_queue, Queue, Worker
from rq.scripts import (add_standard_arguments, read_config_file,
                        setup_default_arguments, setup_redis)
from rq.utils import gettermsize, make_colorizer

red = make_colorizer('darkred')
green = make_colorizer('darkgreen')
yellow = make_colorizer('darkyellow')


def pad(s, pad_to_length):
    """Pads the given string to the given length."""
    return ('%-' + '%ds' % pad_to_length) % (s,)


def get_scale(x):
    """Finds the lowest scale where x <= scale."""
    scales = [20, 50, 100, 200, 400, 600, 800, 1000]
    for scale in scales:
        if x <= scale:
            return scale
    return x


def state_symbol(state):
    symbols = {
        'busy': red('busy'),
        'idle': green('idle'),
    }
    try:
        return symbols[state]
    except KeyError:
        return state


def show_queues(args):
    if len(args.queues):
        qs = list(map(Queue, args.queues))
    else:
        qs = Queue.all()

    num_jobs = 0
    termwidth, _ = gettermsize()
    chartwidth = min(20, termwidth - 20)

    max_count = 0
    counts = dict()
    for q in qs:
        count = q.count
        counts[q] = count
        max_count = max(max_count, count)
    scale = get_scale(max_count)
    ratio = chartwidth * 1.0 / scale

    for q in qs:
        count = counts[q]
        if not args.raw:
            chart = green('|' + '█' * int(ratio * count))
            line = '%-12s %s %d' % (q.name, chart, count)
        else:
            line = 'queue %s %d' % (q.name, count)
        print(line)

        num_jobs += count

    # Print summary when not in raw mode
    if not args.raw:
        print('%d queues, %d jobs total' % (len(qs), num_jobs))


def show_workers(args):
    if len(args.queues):
        qs = list(map(Queue, args.queues))

        def any_matching_queue(worker):
            def queue_matches(q):
                return q in qs
            return any(map(queue_matches, worker.queues))

        # Filter out workers that don't match the queue filter
        ws = [w for w in Worker.all() if any_matching_queue(w)]

        def filter_queues(queue_names):
            return [qname for qname in queue_names if Queue(qname) in qs]

    else:
        qs = Queue.all()
        ws = Worker.all()
        filter_queues = lambda x: x

    if not args.by_queue:
        for w in ws:
            worker_queues = filter_queues(w.queue_names())
            if not args.raw:
                print('%s %s: %s' % (w.name, state_symbol(w.get_state()), ', '.join(worker_queues)))
            else:
                print('worker %s %s %s' % (w.name, w.get_state(), ','.join(worker_queues)))
    else:
        # Create reverse lookup table
        queues = dict([(q, []) for q in qs])
        for w in ws:
            for q in w.queues:
                if q not in queues:
                    continue
                queues[q].append(w)

        max_qname = max(map(lambda q: len(q.name), queues.keys())) if queues else 0
        for q in queues:
            if queues[q]:
                queues_str = ", ".join(sorted(map(lambda w: '%s (%s)' % (w.name, state_symbol(w.get_state())), queues[q])))  # noqa
            else:
                queues_str = '–'
            print('%s %s' % (pad(q.name + ':', max_qname + 1), queues_str))

    if not args.raw:
        print('%d workers, %d queues' % (len(ws), len(qs)))


def show_both(args):
    show_queues(args)
    if not args.raw:
        print('')
    show_workers(args)
    if not args.raw:
        print('')
        import datetime
        print('Updated: %s' % datetime.datetime.now())


def parse_args():
    parser = argparse.ArgumentParser(description='RQ command-line monitor.')
    add_standard_arguments(parser)
    parser.add_argument('--path', '-P', default='.', help='Specify the import path.')
    parser.add_argument('--interval', '-i', metavar='N', type=float, default=2.5, help='Updates stats every N seconds (default: don\'t poll)')  # noqa
    parser.add_argument('--raw', '-r', action='store_true', default=False, help='Print only the raw numbers, no bar charts')  # noqa
    parser.add_argument('--only-queues', '-Q', dest='only_queues', default=False, action='store_true', help='Show only queue info')  # noqa
    parser.add_argument('--only-workers', '-W', dest='only_workers', default=False, action='store_true', help='Show only worker info')  # noqa
    parser.add_argument('--by-queue', '-R', dest='by_queue', default=False, action='store_true', help='Shows workers by queue')  # noqa
    parser.add_argument('--empty-failed-queue', '-X', dest='empty_failed_queue', default=False, action='store_true', help='Empties the failed queue, then quits')  # noqa
    parser.add_argument('queues', nargs='*', help='The queues to poll')
    return parser.parse_args()


def interval(val, func, args):
    while True:
        if val and sys.stdout.isatty():
            os.system('clear')
        func(args)
        if val and sys.stdout.isatty():
            time.sleep(val)
        else:
            break


def main():
    args = parse_args()

    if args.path:
        sys.path = args.path.split(':') + sys.path

    settings = {}
    if args.config:
        settings = read_config_file(args.config)

    setup_default_arguments(args, settings)

    setup_redis(args)

    try:
        if args.empty_failed_queue:
            num_jobs = get_failed_queue().empty()
            print('{} jobs removed from failed queue'.format(num_jobs))
        else:
            if args.only_queues:
                func = show_queues
            elif args.only_workers:
                func = show_workers
            else:
                func = show_both

            interval(args.interval, func, args)
    except ConnectionError as e:
        print(e)
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        sys.exit(0)

########NEW FILE########
__FILENAME__ = rqworker
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import logging
import logging.config
import os
import sys

from redis.exceptions import ConnectionError
from rq import Queue
from rq.contrib.legacy import cleanup_ghosts
from rq.logutils import setup_loghandlers
from rq.scripts import (add_standard_arguments, read_config_file,
                        setup_default_arguments, setup_redis)
from rq.utils import import_attribute

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='Starts an RQ worker.')
    add_standard_arguments(parser)

    parser.add_argument('--burst', '-b', action='store_true', default=False, help='Run in burst mode (quit after all work is done)')  # noqa
    parser.add_argument('--name', '-n', default=None, help='Specify a different name')
    parser.add_argument('--worker-class', '-w', action='store', default='rq.Worker', help='RQ Worker class to use')
    parser.add_argument('--path', '-P', default='.', help='Specify the import path.')
    parser.add_argument('--results-ttl', default=None, help='Default results timeout to be used')
    parser.add_argument('--worker-ttl', default=None, help='Default worker timeout to be used')
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help='Show more output')
    parser.add_argument('--quiet', '-q', action='store_true', default=False, help='Show less output')
    parser.add_argument('--sentry-dsn', action='store', default=None, metavar='URL', help='Report exceptions to this Sentry DSN')  # noqa
    parser.add_argument('--pid', action='store', default=None,
                        help='Write the process ID number to a file at the specified path')
    parser.add_argument('queues', nargs='*', help='The queues to listen on (default: \'default\')')

    return parser.parse_args()


def setup_loghandlers_from_args(args):
    if args.verbose and args.quiet:
        raise RuntimeError("Flags --verbose and --quiet are mutually exclusive.")

    if args.verbose:
        level = 'DEBUG'
    elif args.quiet:
        level = 'WARNING'
    else:
        level = 'INFO'
    setup_loghandlers(level)


def main():
    args = parse_args()

    if args.path:
        sys.path = args.path.split(':') + sys.path

    settings = {}
    if args.config:
        settings = read_config_file(args.config)

    setup_default_arguments(args, settings)

    # Worker specific default arguments
    if not args.queues:
        args.queues = settings.get('QUEUES', ['default'])

    if args.sentry_dsn is None:
        args.sentry_dsn = settings.get('SENTRY_DSN',
                                       os.environ.get('SENTRY_DSN', None))

    if args.pid:
        with open(os.path.expanduser(args.pid), "w") as fp:
            fp.write(str(os.getpid()))

    setup_loghandlers_from_args(args)
    setup_redis(args)

    cleanup_ghosts()
    worker_class = import_attribute(args.worker_class)

    try:
        queues = list(map(Queue, args.queues))
        w = worker_class(queues,
                         name=args.name,
                         default_worker_ttl=args.worker_ttl,
                         default_result_ttl=args.results_ttl)

        # Should we configure Sentry?
        if args.sentry_dsn:
            from raven import Client
            from rq.contrib.sentry import register_sentry
            client = Client(args.sentry_dsn)
            register_sentry(client, w)

        w.work(burst=args.burst)
    except ConnectionError as e:
        print(e)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = timeouts
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import signal


class JobTimeoutException(Exception):
    """Raised when a job takes longer to complete than the allowed maximum
    timeout value.
    """
    pass


class BaseDeathPenalty(object):
    """Base class to setup job timeouts."""

    def __init__(self, timeout):
        self._timeout = timeout

    def __enter__(self):
        self.setup_death_penalty()

    def __exit__(self, type, value, traceback):
        # Always cancel immediately, since we're done
        try:
            self.cancel_death_penalty()
        except JobTimeoutException:
            # Weird case: we're done with the with body, but now the alarm is
            # fired.  We may safely ignore this situation and consider the
            # body done.
            pass

        # __exit__ may return True to supress further exception handling.  We
        # don't want to suppress any exceptions here, since all errors should
        # just pass through, JobTimeoutException being handled normally to the
        # invoking context.
        return False

    def setup_death_penalty(self):
        raise NotImplementedError()

    def cancel_death_penalty(self):
        raise NotImplementedError()


class UnixSignalDeathPenalty(BaseDeathPenalty):

    def handle_death_penalty(self, signum, frame):
        raise JobTimeoutException('Job exceeded maximum timeout '
                                  'value (%d seconds).' % self._timeout)

    def setup_death_penalty(self):
        """Sets up an alarm signal and a signal handler that raises
        a JobTimeoutException after the timeout amount (expressed in
        seconds).
        """
        signal.signal(signal.SIGALRM, self.handle_death_penalty)
        signal.alarm(self._timeout)

    def cancel_death_penalty(self):
        """Removes the death penalty alarm and puts back the system into
        default signal handling.
        """
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
Miscellaneous helper functions.

The formatter for ANSI colored console output is heavily based on Pygments
terminal colorizing code, originally by Georg Brandl.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import importlib
import datetime
import logging
import os
import sys

from .compat import is_python_version


def gettermsize():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import struct
            import termios
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])


class _Colorizer(object):
    def __init__(self):
        esc = "\x1b["

        self.codes = {}
        self.codes[""] = ""
        self.codes["reset"] = esc + "39;49;00m"

        self.codes["bold"] = esc + "01m"
        self.codes["faint"] = esc + "02m"
        self.codes["standout"] = esc + "03m"
        self.codes["underline"] = esc + "04m"
        self.codes["blink"] = esc + "05m"
        self.codes["overline"] = esc + "06m"

        dark_colors = ["black", "darkred", "darkgreen", "brown", "darkblue",
                       "purple", "teal", "lightgray"]
        light_colors = ["darkgray", "red", "green", "yellow", "blue",
                        "fuchsia", "turquoise", "white"]

        x = 30
        for d, l in zip(dark_colors, light_colors):
            self.codes[d] = esc + "%im" % x
            self.codes[l] = esc + "%i;01m" % x
            x += 1

        del d, l, x

        self.codes["darkteal"] = self.codes["turquoise"]
        self.codes["darkyellow"] = self.codes["brown"]
        self.codes["fuscia"] = self.codes["fuchsia"]
        self.codes["white"] = self.codes["bold"]

        if hasattr(sys.stdout, "isatty"):
            self.notty = not sys.stdout.isatty()
        else:
            self.notty = True

    def reset_color(self):
        return self.codes["reset"]

    def colorize(self, color_key, text):
        if not sys.stdout.isatty():
            return text
        else:
            return self.codes[color_key] + text + self.codes["reset"]

    def ansiformat(self, attr, text):
        """
        Format ``text`` with a color and/or some attributes::

            color       normal color
            *color*     bold color
            _color_     underlined color
            +color+     blinking color
        """
        result = []
        if attr[:1] == attr[-1:] == '+':
            result.append(self.codes['blink'])
            attr = attr[1:-1]
        if attr[:1] == attr[-1:] == '*':
            result.append(self.codes['bold'])
            attr = attr[1:-1]
        if attr[:1] == attr[-1:] == '_':
            result.append(self.codes['underline'])
            attr = attr[1:-1]
        result.append(self.codes[attr])
        result.append(text)
        result.append(self.codes['reset'])
        return ''.join(result)


colorizer = _Colorizer()


def make_colorizer(color):
    """Creates a function that colorizes text with the given color.

    For example:

        green = make_colorizer('darkgreen')
        red = make_colorizer('red')

    Then, you can use:

        print "It's either " + green('OK') + ' or ' + red('Oops')
    """
    def inner(text):
        return colorizer.colorize(color, text)
    return inner


class ColorizingStreamHandler(logging.StreamHandler):

    levels = {
        logging.WARNING: make_colorizer('darkyellow'),
        logging.ERROR: make_colorizer('darkred'),
        logging.CRITICAL: make_colorizer('darkred'),
    }

    def __init__(self, exclude=None, *args, **kwargs):
        self.exclude = exclude
        if is_python_version((2, 6)):
            logging.StreamHandler.__init__(self, *args, **kwargs)
        else:
            super(ColorizingStreamHandler, self).__init__(*args, **kwargs)

    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if self.is_tty:
            colorize = self.levels.get(record.levelno, lambda x: x)

            # Don't colorize any traceback
            parts = message.split('\n', 1)
            parts[0] = " ".join([parts[0].split(" ", 1)[0], colorize(parts[0].split(" ", 1)[1])])

            message = '\n'.join(parts)

        return message


def import_attribute(name):
    """Return an attribute from a dotted path name (e.g. "path.to.func")."""
    module_name, attribute = name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def utcnow():
    return datetime.datetime.utcnow()


def utcformat(dt):
    return dt.strftime(u'%Y-%m-%dT%H:%M:%SZ')


def utcparse(string):
    try:
        return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        # This catches RQ < 0.4 datetime format
        return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%S.%f+00:00')


def first(iterable, default=None, key=None):
    """
    Return first element of `iterable` that evaluates true, else return None
    (or an optional default value).

    >>> first([0, False, None, [], (), 42])
    42

    >>> first([0, False, None, [], ()]) is None
    True

    >>> first([0, False, None, [], ()], default='ohai')
    'ohai'

    >>> import re
    >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
    >>> m.group(1)
    'bc'

    The optional `key` argument specifies a one-argument predicate function
    like that used for `filter()`.  The `key` argument, if supplied, must be
    in keyword form.  For example:

    >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
    4

    """
    if key is None:
        for el in iterable:
            if el:
                return el
    else:
        for el in iterable:
            if key(el):
                return el

    return default

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
VERSION = '0.4.6'

########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import errno
import logging
import os
import random
import signal
import socket
import sys
import time
import traceback

from rq.compat import as_text, text_type

from .connections import get_current_connection
from .exceptions import DequeueTimeout, NoQueueError
from .job import Job, Status
from .logutils import setup_loghandlers
from .queue import get_failed_queue, Queue
from .timeouts import UnixSignalDeathPenalty
from .utils import make_colorizer, utcformat, utcnow
from .version import VERSION

try:
    from procname import setprocname
except ImportError:
    def setprocname(*args, **kwargs):  # noqa
        pass

green = make_colorizer('darkgreen')
yellow = make_colorizer('darkyellow')
blue = make_colorizer('darkblue')

DEFAULT_WORKER_TTL = 420
DEFAULT_RESULT_TTL = 500
logger = logging.getLogger(__name__)


class StopRequested(Exception):
    pass


def iterable(x):
    return hasattr(x, '__iter__')


def compact(l):
    return [x for x in l if x is not None]

_signames = dict((getattr(signal, signame), signame)
                 for signame in dir(signal)
                 if signame.startswith('SIG') and '_' not in signame)


def signal_name(signum):
    # Hackety-hack-hack: is there really no better way to reverse lookup the
    # signal name?  If you read this and know a way: please provide a patch :)
    try:
        return _signames[signum]
    except KeyError:
        return 'SIG_UNKNOWN'


class Worker(object):
    redis_worker_namespace_prefix = 'rq:worker:'
    redis_workers_keys = 'rq:workers'
    death_penalty_class = UnixSignalDeathPenalty
    queue_class = Queue
    job_class = Job

    @classmethod
    def all(cls, connection=None):
        """Returns an iterable of all Workers.
        """
        if connection is None:
            connection = get_current_connection()
        reported_working = connection.smembers(cls.redis_workers_keys)
        workers = [cls.find_by_key(as_text(key), connection)
                   for key in reported_working]
        return compact(workers)

    @classmethod
    def find_by_key(cls, worker_key, connection=None):
        """Returns a Worker instance, based on the naming conventions for
        naming the internal Redis keys.  Can be used to reverse-lookup Workers
        by their Redis keys.
        """
        prefix = cls.redis_worker_namespace_prefix
        if not worker_key.startswith(prefix):
            raise ValueError('Not a valid RQ worker key: %s' % (worker_key,))

        if connection is None:
            connection = get_current_connection()
        if not connection.exists(worker_key):
            connection.srem(cls.redis_workers_keys, worker_key)
            return None

        name = worker_key[len(prefix):]
        worker = cls([], name, connection=connection)
        queues = as_text(connection.hget(worker.key, 'queues'))
        worker._state = connection.hget(worker.key, 'state') or '?'
        worker._job_id = connection.hget(worker.key, 'current_job') or None
        if queues:
            worker.queues = [cls.queue_class(queue, connection=connection)
                             for queue in queues.split(',')]
        return worker

    def __init__(self, queues, name=None,
                 default_result_ttl=None, connection=None,
                 exc_handler=None, default_worker_ttl=None):  # noqa
        if connection is None:
            connection = get_current_connection()
        self.connection = connection
        if isinstance(queues, self.queue_class):
            queues = [queues]
        self._name = name
        self.queues = queues
        self.validate_queues()
        self._exc_handlers = []

        if default_result_ttl is None:
            default_result_ttl = DEFAULT_RESULT_TTL
        self.default_result_ttl = default_result_ttl

        if default_worker_ttl is None:
            default_worker_ttl = DEFAULT_WORKER_TTL
        self.default_worker_ttl = default_worker_ttl

        self._state = 'starting'
        self._is_horse = False
        self._horse_pid = 0
        self._stopped = False
        self.log = logger
        self.failed_queue = get_failed_queue(connection=self.connection)

        # By default, push the "move-to-failed-queue" exception handler onto
        # the stack
        self.push_exc_handler(self.move_to_failed_queue)
        if exc_handler is not None:
            self.push_exc_handler(exc_handler)

    def validate_queues(self):
        """Sanity check for the given queues."""
        if not iterable(self.queues):
            raise ValueError('Argument queues not iterable.')
        for queue in self.queues:
            if not isinstance(queue, self.queue_class):
                raise NoQueueError('Give each worker at least one Queue.')

    def queue_names(self):
        """Returns the queue names of this worker's queues."""
        return map(lambda q: q.name, self.queues)

    def queue_keys(self):
        """Returns the Redis keys representing this worker's queues."""
        return map(lambda q: q.key, self.queues)

    @property
    def name(self):
        """Returns the name of the worker, under which it is registered to the
        monitoring system.

        By default, the name of the worker is constructed from the current
        (short) host name and the current PID.
        """
        if self._name is None:
            hostname = socket.gethostname()
            shortname, _, _ = hostname.partition('.')
            self._name = '%s.%s' % (shortname, self.pid)
        return self._name

    @property
    def key(self):
        """Returns the worker's Redis hash key."""
        return self.redis_worker_namespace_prefix + self.name

    @property
    def pid(self):
        """The current process ID."""
        return os.getpid()

    @property
    def horse_pid(self):
        """The horse's process ID.  Only available in the worker.  Will return
        0 in the horse part of the fork.
        """
        return self._horse_pid

    @property
    def is_horse(self):
        """Returns whether or not this is the worker or the work horse."""
        return self._is_horse

    def procline(self, message):
        """Changes the current procname for the process.

        This can be used to make `ps -ef` output more readable.
        """
        setprocname('rq: %s' % (message,))

    def register_birth(self):
        """Registers its own birth."""
        self.log.debug('Registering birth of worker %s' % (self.name,))
        if self.connection.exists(self.key) and \
                not self.connection.hexists(self.key, 'death'):
            raise ValueError('There exists an active worker named \'%s\' '
                             'already.' % (self.name,))
        key = self.key
        queues = ','.join(self.queue_names())
        with self.connection._pipeline() as p:
            p.delete(key)
            p.hset(key, 'birth', utcformat(utcnow()))
            p.hset(key, 'queues', queues)
            p.sadd(self.redis_workers_keys, key)
            p.expire(key, self.default_worker_ttl)
            p.execute()

    def register_death(self):
        """Registers its own death."""
        self.log.debug('Registering death')
        with self.connection._pipeline() as p:
            # We cannot use self.state = 'dead' here, because that would
            # rollback the pipeline
            p.srem(self.redis_workers_keys, self.key)
            p.hset(self.key, 'death', utcformat(utcnow()))
            p.expire(self.key, 60)
            p.execute()

    def set_state(self, state, pipeline=None):
        self._state = state
        connection = pipeline if pipeline is not None else self.connection
        connection.hset(self.key, 'state', state)

    def _set_state(self, state):
        """Raise a DeprecationWarning if ``worker.state = X`` is used"""
        raise DeprecationWarning(
            "worker.state is deprecated, use worker.set_state() instead."
        )
        self.set_state(state)

    def get_state(self):
        return self._state

    def _get_state(self):
        """Raise a DeprecationWarning if ``worker.state == X`` is used"""
        raise DeprecationWarning(
            "worker.state is deprecated, use worker.get_state() instead."
        )
        return self.get_state()

    state = property(_get_state, _set_state)

    def set_current_job_id(self, job_id, pipeline=None):
        connection = pipeline if pipeline is not None else self.connection

        if job_id is None:
            connection.hdel(self.key, 'current_job')
        else:
            connection.hset(self.key, 'current_job', job_id)

    def get_current_job_id(self, pipeline=None):
        connection = pipeline if pipeline is not None else self.connection
        return as_text(connection.hget(self.key, 'current_job'))

    def get_current_job(self):
        """Returns the job id of the currently executing job."""
        job_id = self.get_current_job_id()

        if job_id is None:
            return None

        return self.job_class.fetch(job_id, self.connection)

    @property
    def stopped(self):
        return self._stopped

    def _install_signal_handlers(self):
        """Installs signal handlers for handling SIGINT and SIGTERM
        gracefully.
        """

        def request_force_stop(signum, frame):
            """Terminates the application (cold shutdown).
            """
            self.log.warning('Cold shut down.')

            # Take down the horse with the worker
            if self.horse_pid:
                msg = 'Taking down horse %d with me.' % self.horse_pid
                self.log.debug(msg)
                try:
                    os.kill(self.horse_pid, signal.SIGKILL)
                except OSError as e:
                    # ESRCH ("No such process") is fine with us
                    if e.errno != errno.ESRCH:
                        self.log.debug('Horse already down.')
                        raise
            raise SystemExit()

        def request_stop(signum, frame):
            """Stops the current worker loop but waits for child processes to
            end gracefully (warm shutdown).
            """
            self.log.debug('Got signal %s.' % signal_name(signum))

            signal.signal(signal.SIGINT, request_force_stop)
            signal.signal(signal.SIGTERM, request_force_stop)

            msg = 'Warm shut down requested.'
            self.log.warning(msg)

            # If shutdown is requested in the middle of a job, wait until
            # finish before shutting down
            if self.get_state() == 'busy':
                self._stopped = True
                self.log.debug('Stopping after current horse is finished. '
                               'Press Ctrl+C again for a cold shutdown.')
            else:
                raise StopRequested()

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)

    def work(self, burst=False):
        """Starts the work loop.

        Pops and performs all jobs on the current list of queues.  When all
        queues are empty, block and wait for new jobs to arrive on any of the
        queues, unless `burst` mode is enabled.

        The return value indicates whether any jobs were processed.
        """
        setup_loghandlers()
        self._install_signal_handlers()

        did_perform_work = False
        self.register_birth()
        self.log.info('RQ worker started, version %s' % VERSION)
        self.set_state('starting')
        try:
            while True:
                if self.stopped:
                    self.log.info('Stopping on request.')
                    break

                timeout = None if burst else max(1, self.default_worker_ttl - 60)
                try:
                    result = self.dequeue_job_and_maintain_ttl(timeout)
                    if result is None:
                        break
                except StopRequested:
                    break

                job, queue = result
                self.execute_job(job)
                self.heartbeat()

                if job.get_status() == Status.FINISHED:
                    queue.enqueue_dependents(job)

                did_perform_work = True
        finally:
            if not self.is_horse:
                self.register_death()
        return did_perform_work

    def dequeue_job_and_maintain_ttl(self, timeout):
        result = None
        qnames = self.queue_names()

        self.set_state('idle')
        self.procline('Listening on %s' % ','.join(qnames))
        self.log.info('')
        self.log.info('*** Listening on %s...' %
                      green(', '.join(qnames)))

        while True:
            self.heartbeat()

            try:
                result = self.queue_class.dequeue_any(self.queues, timeout,
                                                      connection=self.connection)
                if result is not None:
                    job, queue = result
                    self.log.info('%s: %s (%s)' % (green(queue.name),
                                  blue(job.description), job.id))

                break
            except DequeueTimeout:
                pass

        self.heartbeat()
        return result

    def heartbeat(self, timeout=0):
        """Specifies a new worker timeout, typically by extending the
        expiration time of the worker, effectively making this a "heartbeat"
        to not expire the worker until the timeout passes.

        The next heartbeat should come before this time, or the worker will
        die (at least from the monitoring dashboards).

        The effective timeout can never be shorter than default_worker_ttl,
        only larger.
        """
        timeout = max(timeout, self.default_worker_ttl)
        self.connection.expire(self.key, timeout)
        self.log.debug('Sent heartbeat to prevent worker timeout. '
                       'Next one should arrive within {0} seconds.'.format(timeout))

    def execute_job(self, job):
        """Spawns a work horse to perform the actual work and passes it a job.
        The worker will wait for the work horse and make sure it executes
        within the given timeout bounds, or will end the work horse with
        SIGALRM.
        """
        child_pid = os.fork()
        if child_pid == 0:
            self.main_work_horse(job)
        else:
            self._horse_pid = child_pid
            self.procline('Forked %d at %d' % (child_pid, time.time()))
            while True:
                try:
                    os.waitpid(child_pid, 0)
                    break
                except OSError as e:
                    # In case we encountered an OSError due to EINTR (which is
                    # caused by a SIGINT or SIGTERM signal during
                    # os.waitpid()), we simply ignore it and enter the next
                    # iteration of the loop, waiting for the child to end.  In
                    # any other case, this is some other unexpected OS error,
                    # which we don't want to catch, so we re-raise those ones.
                    if e.errno != errno.EINTR:
                        raise

    def main_work_horse(self, job):
        """This is the entry point of the newly spawned work horse."""
        # After fork()'ing, always assure we are generating random sequences
        # that are different from the worker.
        random.seed()

        # Always ignore Ctrl+C in the work horse, as it might abort the
        # currently running job.
        # The main worker catches the Ctrl+C and requests graceful shutdown
        # after the current work is done.  When cold shutdown is requested, it
        # kills the current job anyway.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        self._is_horse = True
        self.log = logger

        success = self.perform_job(job)

        # os._exit() is the way to exit from childs after a fork(), in
        # constrast to the regular sys.exit()
        os._exit(int(not success))

    def perform_job(self, job):
        """Performs the actual work of a job.  Will/should only be called
        inside the work horse's process.
        """

        self.set_state('busy')
        self.set_current_job_id(job.id)
        self.heartbeat((job.timeout or 180) + 60)

        self.procline('Processing %s from %s since %s' % (
            job.func_name,
            job.origin, time.time()))

        with self.connection._pipeline() as pipeline:
            try:
                with self.death_penalty_class(job.timeout or self.queue_class.DEFAULT_TIMEOUT):
                    rv = job.perform()

                # Pickle the result in the same try-except block since we need to
                # use the same exc handling when pickling fails
                job._result = rv

                self.set_current_job_id(None, pipeline=pipeline)

                result_ttl = job.get_ttl(self.default_result_ttl)
                if result_ttl != 0:
                    job.save(pipeline=pipeline)
                job.cleanup(result_ttl, pipeline=pipeline)

                pipeline.execute()

            except Exception:
                # Use the public setter here, to immediately update Redis
                job.set_status(Status.FAILED)
                self.handle_exception(job, *sys.exc_info())
                return False

        if rv is None:
            self.log.info('Job OK')
        else:
            self.log.info('Job OK, result = %s' % (yellow(text_type(rv)),))

        if result_ttl == 0:
            self.log.info('Result discarded immediately.')
        elif result_ttl > 0:
            self.log.info('Result is kept for %d seconds.' % result_ttl)
        else:
            self.log.warning('Result will never expire, clean up result key manually.')

        return True

    def handle_exception(self, job, *exc_info):
        """Walks the exception handler stack to delegate exception handling."""
        exc_string = ''.join(traceback.format_exception_only(*exc_info[:2]) +
                             traceback.format_exception(*exc_info))
        self.log.error(exc_string)

        for handler in reversed(self._exc_handlers):
            self.log.debug('Invoking exception handler %s' % (handler,))
            fallthrough = handler(job, *exc_info)

            # Only handlers with explicit return values should disable further
            # exc handling, so interpret a None return value as True.
            if fallthrough is None:
                fallthrough = True

            if not fallthrough:
                break

    def move_to_failed_queue(self, job, *exc_info):
        """Default exception handler: move the job to the failed queue."""
        exc_string = ''.join(traceback.format_exception(*exc_info))
        self.log.warning('Moving job to %s queue.' % self.failed_queue.name)
        self.failed_queue.quarantine(job, exc_info=exc_string)

    def push_exc_handler(self, handler_func):
        """Pushes an exception handler onto the exc handler stack."""
        self._exc_handlers.append(handler_func)

    def pop_exc_handler(self):
        """Pops the latest exception handler off of the exc handler stack."""
        return self._exc_handlers.pop()

########NEW FILE########
__FILENAME__ = dummy_settings
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

REDIS_HOST = "testhost.example.com"

########NEW FILE########
__FILENAME__ = fixtures
# -*- coding: utf-8 -*-
"""
This file contains all jobs that are used in tests.  Each of these test
fixtures has a slighty different characteristics.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import time

from rq import Connection, get_current_job
from rq.decorators import job


def say_hello(name=None):
    """A job with a single argument and a return value."""
    if name is None:
        name = 'Stranger'
    return 'Hi there, %s!' % (name,)


def do_nothing():
    """The best job in the world."""
    pass


def div_by_zero(x):
    """Prepare for a division-by-zero exception."""
    return x / 0


def some_calculation(x, y, z=1):
    """Some arbitrary calculation with three numbers.  Choose z smartly if you
    want a division by zero exception.
    """
    return x * y / z


def create_file(path):
    """Creates a file at the given path.  Actually, leaves evidence that the
    job ran."""
    with open(path, 'w') as f:
        f.write('Just a sentinel.')


def create_file_after_timeout(path, timeout):
    time.sleep(timeout)
    create_file(path)


def access_self():
    job = get_current_job()
    return job.id


def echo(*args, **kwargs):
    return (args, kwargs)


class Number(object):
    def __init__(self, value):
        self.value = value

    @classmethod
    def divide(cls, x, y):
        return x * y

    def div(self, y):
        return self.value / y


with Connection():
    @job(queue='default')
    def decorated_job(x, y):
        return x + y


def long_running_job():
    time.sleep(10)

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import timedelta


def strip_microseconds(date):
    return date - timedelta(microseconds=date.microsecond)

########NEW FILE########
__FILENAME__ = test_connection
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from rq import Connection, Queue

from tests import find_empty_redis_database, RQTestCase
from tests.fixtures import do_nothing


def new_connection():
    return find_empty_redis_database()


class TestConnectionInheritance(RQTestCase):
    def test_connection_detection(self):
        """Automatic detection of the connection."""
        q = Queue()
        self.assertEquals(q.connection, self.testconn)

    def test_connection_stacking(self):
        """Connection stacking."""
        conn1 = new_connection()
        conn2 = new_connection()

        with Connection(conn1):
            q1 = Queue()
            with Connection(conn2):
                q2 = Queue()
        self.assertNotEquals(q1.connection, q2.connection)

    def test_connection_pass_thru(self):
        """Connection passed through from queues to jobs."""
        q1 = Queue()
        with Connection(new_connection()):
            q2 = Queue()
        job1 = q1.enqueue(do_nothing)
        job2 = q2.enqueue(do_nothing)
        self.assertEquals(q1.connection, job1.connection)
        self.assertEquals(q2.connection, job2.connection)

########NEW FILE########
__FILENAME__ = test_decorator
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import mock
from redis import StrictRedis
from rq.decorators import job
from rq.job import Job
from rq.worker import DEFAULT_RESULT_TTL

from tests import RQTestCase
from tests.fixtures import decorated_job


class TestDecorator(RQTestCase):

    def setUp(self):
        super(TestDecorator, self).setUp()

    def test_decorator_preserves_functionality(self):
        """Ensure that a decorated function's functionality is still preserved.
        """
        self.assertEqual(decorated_job(1, 2), 3)

    def test_decorator_adds_delay_attr(self):
        """Ensure that decorator adds a delay attribute to function that returns
        a Job instance when called.
        """
        self.assertTrue(hasattr(decorated_job, 'delay'))
        result = decorated_job.delay(1, 2)
        self.assertTrue(isinstance(result, Job))
        # Ensure that job returns the right result when performed
        self.assertEqual(result.perform(), 3)

    def test_decorator_accepts_queue_name_as_argument(self):
        """Ensure that passing in queue name to the decorator puts the job in
        the right queue.
        """
        @job(queue='queue_name')
        def hello():
            return 'Hi'
        result = hello.delay()
        self.assertEqual(result.origin, 'queue_name')

    def test_decorator_accepts_result_ttl_as_argument(self):
        """Ensure that passing in result_ttl to the decorator sets the
        result_ttl on the job
        """
        # Ensure default
        result = decorated_job.delay(1, 2)
        self.assertEqual(result.result_ttl, DEFAULT_RESULT_TTL)

        @job('default', result_ttl=10)
        def hello():
            return 'Why hello'
        result = hello.delay()
        self.assertEqual(result.result_ttl, 10)

    def test_decorator_accepts_result_depends_on_as_argument(self):
        """Ensure that passing in depends_on to the decorator sets the
        correct dependency on the job
        """

        @job(queue='queue_name')
        def foo():
            return 'Firstly'

        @job(queue='queue_name')
        def bar():
            return 'Secondly'

        foo_job = foo.delay()
        bar_job = bar.delay(depends_on=foo_job)

        self.assertIsNone(foo_job._dependency_id)

        self.assertEqual(bar_job.dependency, foo_job)

        self.assertEqual(bar_job._dependency_id, foo_job.id)

    @mock.patch('rq.queue.resolve_connection')
    def test_decorator_connection_laziness(self, resolve_connection):
        """Ensure that job decorator resolve connection in `lazy` way """

        resolve_connection.return_value = StrictRedis()

        @job(queue='queue_name')
        def foo():
            return 'do something'

        self.assertEqual(resolve_connection.call_count, 0)

        foo()

        self.assertEqual(resolve_connection.call_count, 0)

        foo.delay()

        self.assertEqual(resolve_connection.call_count, 1)

########NEW FILE########
__FILENAME__ = test_job
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import datetime

from rq.compat import as_text, PY2
from rq.exceptions import NoSuchJobError, UnpickleError
from rq.job import get_current_job, Job
from rq.queue import Queue
from rq.utils import utcformat

from tests import RQTestCase
from tests.fixtures import access_self, Number, say_hello, some_calculation
from tests.helpers import strip_microseconds

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps


class TestJob(RQTestCase):
    def test_create_empty_job(self):
        """Creation of new empty jobs."""
        job = Job()

        # Jobs have a random UUID and a creation date
        self.assertIsNotNone(job.id)
        self.assertIsNotNone(job.created_at)

        # ...and nothing else
        self.assertIsNone(job.origin)
        self.assertIsNone(job.enqueued_at)
        self.assertIsNone(job.ended_at)
        self.assertIsNone(job.result)
        self.assertIsNone(job.exc_info)

        with self.assertRaises(ValueError):
            job.func
        with self.assertRaises(ValueError):
            job.instance
        with self.assertRaises(ValueError):
            job.args
        with self.assertRaises(ValueError):
            job.kwargs

    def test_create_typical_job(self):
        """Creation of jobs for function calls."""
        job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))

        # Jobs have a random UUID
        self.assertIsNotNone(job.id)
        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.description)
        self.assertIsNone(job.instance)

        # Job data is set...
        self.assertEquals(job.func, some_calculation)
        self.assertEquals(job.args, (3, 4))
        self.assertEquals(job.kwargs, {'z': 2})

        # ...but metadata is not
        self.assertIsNone(job.origin)
        self.assertIsNone(job.enqueued_at)
        self.assertIsNone(job.result)

    def test_create_instance_method_job(self):
        """Creation of jobs for instance methods."""
        n = Number(2)
        job = Job.create(func=n.div, args=(4,))

        # Job data is set
        self.assertEquals(job.func, n.div)
        self.assertEquals(job.instance, n)
        self.assertEquals(job.args, (4,))

    def test_create_job_from_string_function(self):
        """Creation of jobs using string specifier."""
        job = Job.create(func='tests.fixtures.say_hello', args=('World',))

        # Job data is set
        self.assertEquals(job.func, say_hello)
        self.assertIsNone(job.instance)
        self.assertEquals(job.args, ('World',))

    def test_job_properties_set_data_property(self):
        """Data property gets derived from the job tuple."""
        job = Job()
        job.func_name = 'foo'
        fname, instance, args, kwargs = loads(job.data)

        self.assertEquals(fname, job.func_name)
        self.assertEquals(instance, None)
        self.assertEquals(args, ())
        self.assertEquals(kwargs, {})

    def test_data_property_sets_job_properties(self):
        """Job tuple gets derived lazily from data property."""
        job = Job()
        job.data = dumps(('foo', None, (1, 2, 3), {'bar': 'qux'}))

        self.assertEquals(job.func_name, 'foo')
        self.assertEquals(job.instance, None)
        self.assertEquals(job.args, (1, 2, 3))
        self.assertEquals(job.kwargs, {'bar': 'qux'})

    def test_save(self):  # noqa
        """Storing jobs."""
        job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))

        # Saving creates a Redis hash
        self.assertEquals(self.testconn.exists(job.key), False)
        job.save()
        self.assertEquals(self.testconn.type(job.key), b'hash')

        # Saving writes pickled job data
        unpickled_data = loads(self.testconn.hget(job.key, 'data'))
        self.assertEquals(unpickled_data[0], 'tests.fixtures.some_calculation')

    def test_fetch(self):
        """Fetching jobs."""
        # Prepare test
        self.testconn.hset('rq:job:some_id', 'data',
                           "(S'tests.fixtures.some_calculation'\nN(I3\nI4\nt(dp1\nS'z'\nI2\nstp2\n.")
        self.testconn.hset('rq:job:some_id', 'created_at',
                           '2012-02-07T22:13:24Z')

        # Fetch returns a job
        job = Job.fetch('some_id')
        self.assertEquals(job.id, 'some_id')
        self.assertEquals(job.func_name, 'tests.fixtures.some_calculation')
        self.assertIsNone(job.instance)
        self.assertEquals(job.args, (3, 4))
        self.assertEquals(job.kwargs, dict(z=2))
        self.assertEquals(job.created_at, datetime(2012, 2, 7, 22, 13, 24))

    def test_persistence_of_empty_jobs(self):  # noqa
        """Storing empty jobs."""
        job = Job()
        with self.assertRaises(ValueError):
            job.save()

    def test_persistence_of_typical_jobs(self):
        """Storing typical jobs."""
        job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))
        job.save()

        expected_date = strip_microseconds(job.created_at)
        stored_date = self.testconn.hget(job.key, 'created_at').decode('utf-8')
        self.assertEquals(
            stored_date,
            utcformat(expected_date))

        # ... and no other keys are stored
        self.assertEqual(
            sorted(self.testconn.hkeys(job.key)),
            [b'created_at', b'data', b'description'])

    def test_persistence_of_parent_job(self):
        """Storing jobs with parent job, either instance or key."""
        parent_job = Job.create(func=some_calculation)
        parent_job.save()
        job = Job.create(func=some_calculation, depends_on=parent_job)
        job.save()
        stored_job = Job.fetch(job.id)
        self.assertEqual(stored_job._dependency_id, parent_job.id)
        self.assertEqual(stored_job.dependency, parent_job)

        job = Job.create(func=some_calculation, depends_on=parent_job.id)
        job.save()
        stored_job = Job.fetch(job.id)
        self.assertEqual(stored_job._dependency_id, parent_job.id)
        self.assertEqual(stored_job.dependency, parent_job)

    def test_store_then_fetch(self):
        """Store, then fetch."""
        job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))
        job.save()

        job2 = Job.fetch(job.id)
        self.assertEquals(job.func, job2.func)
        self.assertEquals(job.args, job2.args)
        self.assertEquals(job.kwargs, job2.kwargs)

        # Mathematical equation
        self.assertEquals(job, job2)

    def test_fetching_can_fail(self):
        """Fetching fails for non-existing jobs."""
        with self.assertRaises(NoSuchJobError):
            Job.fetch('b4a44d44-da16-4620-90a6-798e8cd72ca0')

    def test_fetching_unreadable_data(self):
        """Fetching succeeds on unreadable data, but lazy props fail."""
        # Set up
        job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))
        job.save()

        # Just replace the data hkey with some random noise
        self.testconn.hset(job.key, 'data', 'this is no pickle string')
        job.refresh()

        for attr in ('func_name', 'instance', 'args', 'kwargs'):
            with self.assertRaises(UnpickleError):
                getattr(job, attr)

    def test_job_is_unimportable(self):
        """Jobs that cannot be imported throw exception on access."""
        job = Job.create(func=say_hello, args=('Lionel',))
        job.save()

        # Now slightly modify the job to make it unimportable (this is
        # equivalent to a worker not having the most up-to-date source code
        # and unable to import the function)
        data = self.testconn.hget(job.key, 'data')
        unimportable_data = data.replace(b'say_hello', b'shut_up')
        self.testconn.hset(job.key, 'data', unimportable_data)

        job.refresh()
        with self.assertRaises(AttributeError):
            job.func  # accessing the func property should fail

    def test_custom_meta_is_persisted(self):
        """Additional meta data on jobs are stored persisted correctly."""
        job = Job.create(func=say_hello, args=('Lionel',))
        job.meta['foo'] = 'bar'
        job.save()

        raw_data = self.testconn.hget(job.key, 'meta')
        self.assertEqual(loads(raw_data)['foo'], 'bar')

        job2 = Job.fetch(job.id)
        self.assertEqual(job2.meta['foo'], 'bar')

    def test_result_ttl_is_persisted(self):
        """Ensure that job's result_ttl is set properly"""
        job = Job.create(func=say_hello, args=('Lionel',), result_ttl=10)
        job.save()
        Job.fetch(job.id, connection=self.testconn)
        self.assertEqual(job.result_ttl, 10)

        job = Job.create(func=say_hello, args=('Lionel',))
        job.save()
        Job.fetch(job.id, connection=self.testconn)
        self.assertEqual(job.result_ttl, None)

    def test_description_is_persisted(self):
        """Ensure that job's custom description is set properly"""
        job = Job.create(func=say_hello, args=('Lionel',), description='Say hello!')
        job.save()
        Job.fetch(job.id, connection=self.testconn)
        self.assertEqual(job.description, 'Say hello!')

        # Ensure job description is constructed from function call string
        job = Job.create(func=say_hello, args=('Lionel',))
        job.save()
        Job.fetch(job.id, connection=self.testconn)
        if PY2:
            self.assertEqual(job.description, "tests.fixtures.say_hello(u'Lionel')")
        else:
            self.assertEqual(job.description, "tests.fixtures.say_hello('Lionel')")

    def test_job_access_within_job_function(self):
        """The current job is accessible within the job function."""
        # Executing the job function from outside of RQ throws an exception
        self.assertIsNone(get_current_job())

        # Executing the job function from within the job works (and in
        # this case leads to the job ID being returned)
        job = Job.create(func=access_self)
        job.save()
        id = job.perform()
        self.assertEqual(job.id, id)
        self.assertEqual(job.func, access_self)

        # Ensure that get_current_job also works from within synchronous jobs
        queue = Queue(async=False)
        job = queue.enqueue(access_self)
        id = job.perform()
        self.assertEqual(job.id, id)
        self.assertEqual(job.func, access_self)

    def test_get_ttl(self):
        """Getting job TTL."""
        job_ttl = 1
        default_ttl = 2
        job = Job.create(func=say_hello, result_ttl=job_ttl)
        job.save()
        self.assertEqual(job.get_ttl(default_ttl=default_ttl), job_ttl)
        self.assertEqual(job.get_ttl(), job_ttl)
        job = Job.create(func=say_hello)
        job.save()
        self.assertEqual(job.get_ttl(default_ttl=default_ttl), default_ttl)
        self.assertEqual(job.get_ttl(), None)

    def test_cleanup(self):
        """Test that jobs and results are expired properly."""
        job = Job.create(func=say_hello)
        job.save()

        # Jobs with negative TTLs don't expire
        job.cleanup(ttl=-1)
        self.assertEqual(self.testconn.ttl(job.key), -1)

        # Jobs with positive TTLs are eventually deleted
        job.cleanup(ttl=100)
        self.assertEqual(self.testconn.ttl(job.key), 100)

        # Jobs with 0 TTL are immediately deleted
        job.cleanup(ttl=0)
        self.assertRaises(NoSuchJobError, Job.fetch, job.id, self.testconn)

    def test_register_dependency(self):
        """Test that jobs updates the correct job dependents."""
        job = Job.create(func=say_hello)
        job._dependency_id = 'id'
        job.save()
        job.register_dependency()
        self.assertEqual(as_text(self.testconn.spop('rq:job:id:dependents')), job.id)

    def test_cancel(self):
        """job.cancel() deletes itself & dependents mapping from Redis."""
        job = Job.create(func=say_hello)
        job2 = Job.create(func=say_hello, depends_on=job)
        job2.register_dependency()
        job.cancel()
        self.assertFalse(self.testconn.exists(job.key))
        self.assertFalse(self.testconn.exists(job.dependents_key))

########NEW FILE########
__FILENAME__ = test_queue
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from rq import get_failed_queue, Queue
from rq.exceptions import InvalidJobOperationError
from rq.job import Job, Status
from rq.worker import Worker

from tests import RQTestCase
from tests.fixtures import (div_by_zero, echo, Number, say_hello,
                            some_calculation)


class TestQueue(RQTestCase):
    def test_create_queue(self):
        """Creating queues."""
        q = Queue('my-queue')
        self.assertEquals(q.name, 'my-queue')

    def test_create_default_queue(self):
        """Instantiating the default queue."""
        q = Queue()
        self.assertEquals(q.name, 'default')

    def test_equality(self):
        """Mathematical equality of queues."""
        q1 = Queue('foo')
        q2 = Queue('foo')
        q3 = Queue('bar')

        self.assertEquals(q1, q2)
        self.assertEquals(q2, q1)
        self.assertNotEquals(q1, q3)
        self.assertNotEquals(q2, q3)

    def test_empty_queue(self):
        """Emptying queues."""
        q = Queue('example')

        self.testconn.rpush('rq:queue:example', 'foo')
        self.testconn.rpush('rq:queue:example', 'bar')
        self.assertEquals(q.is_empty(), False)

        q.empty()

        self.assertEquals(q.is_empty(), True)
        self.assertIsNone(self.testconn.lpop('rq:queue:example'))

    def test_empty_removes_jobs(self):
        """Emptying a queue deletes the associated job objects"""
        q = Queue('example')
        job = q.enqueue(say_hello)
        self.assertTrue(Job.exists(job.id))
        q.empty()
        self.assertFalse(Job.exists(job.id))

    def test_queue_is_empty(self):
        """Detecting empty queues."""
        q = Queue('example')
        self.assertEquals(q.is_empty(), True)

        self.testconn.rpush('rq:queue:example', 'sentinel message')
        self.assertEquals(q.is_empty(), False)

    def test_remove(self):
        """Ensure queue.remove properly removes Job from queue."""
        q = Queue('example')
        job = q.enqueue(say_hello)
        self.assertIn(job.id, q.job_ids)
        q.remove(job)
        self.assertNotIn(job.id, q.job_ids)

        job = q.enqueue(say_hello)
        self.assertIn(job.id, q.job_ids)
        q.remove(job.id)
        self.assertNotIn(job.id, q.job_ids)

    def test_jobs(self):
        """Getting jobs out of a queue."""
        q = Queue('example')
        self.assertEqual(q.jobs, [])
        job = q.enqueue(say_hello)
        self.assertEqual(q.jobs, [job])

        # Fetching a deleted removes it from queue
        job.delete()
        self.assertEqual(q.job_ids, [job.id])
        q.jobs
        self.assertEqual(q.job_ids, [])

    def test_compact(self):
        """Compacting queueus."""
        q = Queue()

        q.enqueue(say_hello, 'Alice')
        bob = q.enqueue(say_hello, 'Bob')
        q.enqueue(say_hello, 'Charlie')
        debrah = q.enqueue(say_hello, 'Debrah')

        bob.cancel()
        debrah.cancel()

        self.assertEquals(q.count, 4)

        q.compact()

        self.assertEquals(q.count, 2)

    def test_enqueue(self):
        """Enqueueing job onto queues."""
        q = Queue()
        self.assertEquals(q.is_empty(), True)

        # say_hello spec holds which queue this is sent to
        job = q.enqueue(say_hello, 'Nick', foo='bar')
        job_id = job.id

        # Inspect data inside Redis
        q_key = 'rq:queue:default'
        self.assertEquals(self.testconn.llen(q_key), 1)
        self.assertEquals(
            self.testconn.lrange(q_key, 0, -1)[0].decode('ascii'),
            job_id)

    def test_enqueue_sets_metadata(self):
        """Enqueueing job onto queues modifies meta data."""
        q = Queue()
        job = Job.create(func=say_hello, args=('Nick',), kwargs=dict(foo='bar'))

        # Preconditions
        self.assertIsNone(job.origin)
        self.assertIsNone(job.enqueued_at)

        # Action
        q.enqueue_job(job)

        # Postconditions
        self.assertEquals(job.origin, q.name)
        self.assertIsNotNone(job.enqueued_at)

    def test_pop_job_id(self):
        """Popping job IDs from queues."""
        # Set up
        q = Queue()
        uuid = '112188ae-4e9d-4a5b-a5b3-f26f2cb054da'
        q.push_job_id(uuid)

        # Pop it off the queue...
        self.assertEquals(q.count, 1)
        self.assertEquals(q.pop_job_id(), uuid)

        # ...and assert the queue count when down
        self.assertEquals(q.count, 0)

    def test_dequeue(self):
        """Dequeueing jobs from queues."""
        # Set up
        q = Queue()
        result = q.enqueue(say_hello, 'Rick', foo='bar')

        # Dequeue a job (not a job ID) off the queue
        self.assertEquals(q.count, 1)
        job = q.dequeue()
        self.assertEquals(job.id, result.id)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, q.name)
        self.assertEquals(job.args[0], 'Rick')
        self.assertEquals(job.kwargs['foo'], 'bar')

        # ...and assert the queue count when down
        self.assertEquals(q.count, 0)

    def test_dequeue_instance_method(self):
        """Dequeueing instance method jobs from queues."""
        q = Queue()
        n = Number(2)
        q.enqueue(n.div, 4)

        job = q.dequeue()

        # The instance has been pickled and unpickled, so it is now a separate
        # object. Test for equality using each object's __dict__ instead.
        self.assertEquals(job.instance.__dict__, n.__dict__)
        self.assertEquals(job.func.__name__, 'div')
        self.assertEquals(job.args, (4,))

    def test_dequeue_class_method(self):
        """Dequeueing class method jobs from queues."""
        q = Queue()
        q.enqueue(Number.divide, 3, 4)

        job = q.dequeue()

        self.assertEquals(job.instance.__dict__, Number.__dict__)
        self.assertEquals(job.func.__name__, 'divide')
        self.assertEquals(job.args, (3, 4))

    def test_dequeue_ignores_nonexisting_jobs(self):
        """Dequeuing silently ignores non-existing jobs."""

        q = Queue()
        uuid = '49f205ab-8ea3-47dd-a1b5-bfa186870fc8'
        q.push_job_id(uuid)
        q.push_job_id(uuid)
        result = q.enqueue(say_hello, 'Nick', foo='bar')
        q.push_job_id(uuid)

        # Dequeue simply ignores the missing job and returns None
        self.assertEquals(q.count, 4)
        self.assertEquals(q.dequeue().id, result.id)
        self.assertIsNone(q.dequeue())
        self.assertEquals(q.count, 0)

    def test_dequeue_any(self):
        """Fetching work from any given queue."""
        fooq = Queue('foo')
        barq = Queue('bar')

        self.assertEquals(Queue.dequeue_any([fooq, barq], None), None)

        # Enqueue a single item
        barq.enqueue(say_hello)
        job, queue = Queue.dequeue_any([fooq, barq], None)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(queue, barq)

        # Enqueue items on both queues
        barq.enqueue(say_hello, 'for Bar')
        fooq.enqueue(say_hello, 'for Foo')

        job, queue = Queue.dequeue_any([fooq, barq], None)
        self.assertEquals(queue, fooq)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, fooq.name)
        self.assertEquals(job.args[0], 'for Foo',
                          'Foo should be dequeued first.')

        job, queue = Queue.dequeue_any([fooq, barq], None)
        self.assertEquals(queue, barq)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, barq.name)
        self.assertEquals(job.args[0], 'for Bar',
                          'Bar should be dequeued second.')

    def test_dequeue_any_ignores_nonexisting_jobs(self):
        """Dequeuing (from any queue) silently ignores non-existing jobs."""

        q = Queue('low')
        uuid = '49f205ab-8ea3-47dd-a1b5-bfa186870fc8'
        q.push_job_id(uuid)

        # Dequeue simply ignores the missing job and returns None
        self.assertEquals(q.count, 1)
        self.assertEquals(Queue.dequeue_any([Queue(), Queue('low')], None),  # noqa
                None)
        self.assertEquals(q.count, 0)

    def test_enqueue_sets_status(self):
        """Enqueueing a job sets its status to "queued"."""
        q = Queue()
        job = q.enqueue(say_hello)
        self.assertEqual(job.get_status(), Status.QUEUED)

    def test_enqueue_explicit_args(self):
        """enqueue() works for both implicit/explicit args."""
        q = Queue()

        # Implicit args/kwargs mode
        job = q.enqueue(echo, 1, timeout=1, result_ttl=1, bar='baz')
        self.assertEqual(job.timeout, 1)
        self.assertEqual(job.result_ttl, 1)
        self.assertEqual(
            job.perform(),
            ((1,), {'bar': 'baz'})
        )

        # Explicit kwargs mode
        kwargs = {
            'timeout': 1,
            'result_ttl': 1,
        }
        job = q.enqueue(echo, timeout=2, result_ttl=2, args=[1], kwargs=kwargs)
        self.assertEqual(job.timeout, 2)
        self.assertEqual(job.result_ttl, 2)
        self.assertEqual(
            job.perform(),
            ((1,), {'timeout': 1, 'result_ttl': 1})
        )

    def test_all_queues(self):
        """All queues"""
        q1 = Queue('first-queue')
        q2 = Queue('second-queue')
        q3 = Queue('third-queue')

        # Ensure a queue is added only once a job is enqueued
        self.assertEquals(len(Queue.all()), 0)
        q1.enqueue(say_hello)
        self.assertEquals(len(Queue.all()), 1)

        # Ensure this holds true for multiple queues
        q2.enqueue(say_hello)
        q3.enqueue(say_hello)
        names = [q.name for q in Queue.all()]
        self.assertEquals(len(Queue.all()), 3)

        # Verify names
        self.assertTrue('first-queue' in names)
        self.assertTrue('second-queue' in names)
        self.assertTrue('third-queue' in names)

        # Now empty two queues
        w = Worker([q2, q3])
        w.work(burst=True)

        # Queue.all() should still report the empty queues
        self.assertEquals(len(Queue.all()), 3)

    def test_enqueue_dependents(self):
        """Enqueueing the dependent jobs pushes all jobs in the depends set to the queue."""
        q = Queue()
        parent_job = Job.create(func=say_hello)
        parent_job.save()
        job_1 = Job.create(func=say_hello, depends_on=parent_job)
        job_1.save()
        job_1.register_dependency()
        job_2 = Job.create(func=say_hello, depends_on=parent_job)
        job_2.save()
        job_2.register_dependency()

        # After dependents is enqueued, job_1 and job_2 should be in queue
        self.assertEqual(q.job_ids, [])
        q.enqueue_dependents(parent_job)
        self.assertEqual(set(q.job_ids), set([job_1.id, job_2.id]))
        self.assertFalse(self.testconn.exists(parent_job.dependents_key))

    def test_enqueue_job_with_dependency(self):
        """Jobs are enqueued only when their dependencies are finished."""
        # Job with unfinished dependency is not immediately enqueued
        parent_job = Job.create(func=say_hello)
        q = Queue()
        q.enqueue_call(say_hello, depends_on=parent_job)
        self.assertEqual(q.job_ids, [])

        # Jobs dependent on finished jobs are immediately enqueued
        parent_job.set_status(Status.FINISHED)
        parent_job.save()
        job = q.enqueue_call(say_hello, depends_on=parent_job)
        self.assertEqual(q.job_ids, [job.id])
        self.assertEqual(job.timeout, Queue.DEFAULT_TIMEOUT)

    def test_enqueue_job_with_dependency_and_timeout(self):
        """Jobs still know their specified timeout after being scheduled as a dependency."""
        # Job with unfinished dependency is not immediately enqueued
        parent_job = Job.create(func=say_hello)
        q = Queue()
        job = q.enqueue_call(say_hello, depends_on=parent_job, timeout=123)
        self.assertEqual(q.job_ids, [])
        self.assertEqual(job.timeout, 123)

        # Jobs dependent on finished jobs are immediately enqueued
        parent_job.set_status(Status.FINISHED)
        parent_job.save()
        job = q.enqueue_call(say_hello, depends_on=parent_job, timeout=123)
        self.assertEqual(q.job_ids, [job.id])
        self.assertEqual(job.timeout, 123)


class TestFailedQueue(RQTestCase):
    def test_requeue_job(self):
        """Requeueing existing jobs."""
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.save()
        get_failed_queue().quarantine(job, Exception('Some fake error'))  # noqa

        self.assertEqual(Queue.all(), [get_failed_queue()])  # noqa
        self.assertEquals(get_failed_queue().count, 1)

        get_failed_queue().requeue(job.id)

        self.assertEquals(get_failed_queue().count, 0)
        self.assertEquals(Queue('fake').count, 1)

    def test_requeue_nonfailed_job_fails(self):
        """Requeueing non-failed jobs raises error."""
        q = Queue()
        job = q.enqueue(say_hello, 'Nick', foo='bar')

        # Assert that we cannot requeue a job that's not on the failed queue
        with self.assertRaises(InvalidJobOperationError):
            get_failed_queue().requeue(job.id)

    def test_quarantine_preserves_timeout(self):
        """Quarantine preserves job timeout."""
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.timeout = 200
        job.save()
        get_failed_queue().quarantine(job, Exception('Some fake error'))

        self.assertEquals(job.timeout, 200)

    def test_requeueing_preserves_timeout(self):
        """Requeueing preserves job timeout."""
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.timeout = 200
        job.save()
        get_failed_queue().quarantine(job, Exception('Some fake error'))
        get_failed_queue().requeue(job.id)

        job = Job.fetch(job.id)
        self.assertEquals(job.timeout, 200)

    def test_requeue_sets_status_to_queued(self):
        """Requeueing a job should set its status back to QUEUED."""
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.save()
        get_failed_queue().quarantine(job, Exception('Some fake error'))
        get_failed_queue().requeue(job.id)

        job = Job.fetch(job.id)
        self.assertEqual(job.get_status(), Status.QUEUED)

    def test_enqueue_preserves_result_ttl(self):
        """Enqueueing persists result_ttl."""
        q = Queue()
        job = q.enqueue(div_by_zero, args=(1, 2, 3), result_ttl=10)
        self.assertEqual(job.result_ttl, 10)
        job_from_queue = Job.fetch(job.id, connection=self.testconn)
        self.assertEqual(int(job_from_queue.result_ttl), 10)

    def test_async_false(self):
        """Executes a job immediately if async=False."""
        q = Queue(async=False)
        job = q.enqueue(some_calculation, args=(2, 3))
        self.assertEqual(job.return_value, 6)

########NEW FILE########
__FILENAME__ = test_scripts
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from rq.compat import is_python_version
from rq.scripts import read_config_file

if is_python_version((2, 7), (3, 2)):
    from unittest import TestCase
else:
    from unittest2 import TestCase  # noqa


class TestScripts(TestCase):
    def test_config_file(self):
        settings = read_config_file("tests.dummy_settings")
        self.assertIn("REDIS_HOST", settings)
        self.assertEqual(settings['REDIS_HOST'], "testhost.example.com")

########NEW FILE########
__FILENAME__ = test_sentry
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from rq import get_failed_queue, Queue, Worker
from rq.contrib.sentry import register_sentry

from tests import RQTestCase


class FakeSentry(object):
    servers = []

    def captureException(self, *args, **kwds):
        pass  # we cannot check this, because worker forks


class TestSentry(RQTestCase):

    def test_work_fails(self):
        """Non importable jobs should be put on the failed queue event with sentry"""
        q = Queue()
        failed_q = get_failed_queue()

        # Action
        q.enqueue('_non.importable.job')
        self.assertEquals(q.count, 1)

        w = Worker([q])
        register_sentry(FakeSentry(), w)

        w.work(burst=True)

        # Postconditions
        self.assertEquals(failed_q.count, 1)
        self.assertEquals(q.count, 0)

########NEW FILE########
__FILENAME__ = test_worker
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os

from rq import get_failed_queue, Queue, Worker
from rq.compat import as_text
from rq.job import Job, Status

from tests import RQTestCase, slow
from tests.fixtures import (create_file, create_file_after_timeout, div_by_zero,
                            say_hello)
from tests.helpers import strip_microseconds


class TestWorker(RQTestCase):
    def test_create_worker(self):
        """Worker creation."""
        fooq, barq = Queue('foo'), Queue('bar')
        w = Worker([fooq, barq])
        self.assertEquals(w.queues, [fooq, barq])

    def test_work_and_quit(self):
        """Worker processes work, then quits."""
        fooq, barq = Queue('foo'), Queue('bar')
        w = Worker([fooq, barq])
        self.assertEquals(w.work(burst=True), False,
                          'Did not expect any work on the queue.')

        fooq.enqueue(say_hello, name='Frank')
        self.assertEquals(w.work(burst=True), True,
                          'Expected at least some work done.')

    def test_worker_ttl(self):
        """Worker ttl."""
        w = Worker([])
        w.register_birth()  # ugly: our test should only call public APIs
        [worker_key] = self.testconn.smembers(Worker.redis_workers_keys)
        self.assertIsNotNone(self.testconn.ttl(worker_key))
        w.register_death()

    def test_work_via_string_argument(self):
        """Worker processes work fed via string arguments."""
        q = Queue('foo')
        w = Worker([q])
        job = q.enqueue('tests.fixtures.say_hello', name='Frank')
        self.assertEquals(w.work(burst=True), True,
                          'Expected at least some work done.')
        self.assertEquals(job.result, 'Hi there, Frank!')

    def test_work_is_unreadable(self):
        """Unreadable jobs are put on the failed queue."""
        q = Queue()
        failed_q = get_failed_queue()

        self.assertEquals(failed_q.count, 0)
        self.assertEquals(q.count, 0)

        # NOTE: We have to fake this enqueueing for this test case.
        # What we're simulating here is a call to a function that is not
        # importable from the worker process.
        job = Job.create(func=div_by_zero, args=(3,))
        job.save()
        data = self.testconn.hget(job.key, 'data')
        invalid_data = data.replace(b'div_by_zero', b'nonexisting')
        assert data != invalid_data
        self.testconn.hset(job.key, 'data', invalid_data)

        # We use the low-level internal function to enqueue any data (bypassing
        # validity checks)
        q.push_job_id(job.id)

        self.assertEquals(q.count, 1)

        # All set, we're going to process it
        w = Worker([q])
        w.work(burst=True)   # should silently pass
        self.assertEquals(q.count, 0)
        self.assertEquals(failed_q.count, 1)

    def test_work_fails(self):
        """Failing jobs are put on the failed queue."""
        q = Queue()
        failed_q = get_failed_queue()

        # Preconditions
        self.assertEquals(failed_q.count, 0)
        self.assertEquals(q.count, 0)

        # Action
        job = q.enqueue(div_by_zero)
        self.assertEquals(q.count, 1)

        # keep for later
        enqueued_at_date = strip_microseconds(job.enqueued_at)

        w = Worker([q])
        w.work(burst=True)  # should silently pass

        # Postconditions
        self.assertEquals(q.count, 0)
        self.assertEquals(failed_q.count, 1)

        # Check the job
        job = Job.fetch(job.id)
        self.assertEquals(job.origin, q.name)

        # Should be the original enqueued_at date, not the date of enqueueing
        # to the failed queue
        self.assertEquals(job.enqueued_at, enqueued_at_date)
        self.assertIsNotNone(job.exc_info)  # should contain exc_info

    def test_custom_exc_handling(self):
        """Custom exception handling."""
        def black_hole(job, *exc_info):
            # Don't fall through to default behaviour (moving to failed queue)
            return False

        q = Queue()
        failed_q = get_failed_queue()

        # Preconditions
        self.assertEquals(failed_q.count, 0)
        self.assertEquals(q.count, 0)

        # Action
        job = q.enqueue(div_by_zero)
        self.assertEquals(q.count, 1)

        w = Worker([q], exc_handler=black_hole)
        w.work(burst=True)  # should silently pass

        # Postconditions
        self.assertEquals(q.count, 0)
        self.assertEquals(failed_q.count, 0)

        # Check the job
        job = Job.fetch(job.id)
        self.assertEquals(job.is_failed, True)

    def test_cancelled_jobs_arent_executed(self):  # noqa
        """Cancelling jobs."""

        SENTINEL_FILE = '/tmp/rq-tests.txt'

        try:
            # Remove the sentinel if it is leftover from a previous test run
            os.remove(SENTINEL_FILE)
        except OSError as e:
            if e.errno != 2:
                raise

        q = Queue()
        job = q.enqueue(create_file, SENTINEL_FILE)

        # Here, we cancel the job, so the sentinel file may not be created
        assert q.count == 1
        job.cancel()
        assert q.count == 1

        w = Worker([q])
        w.work(burst=True)
        assert q.count == 0

        # Should not have created evidence of execution
        self.assertEquals(os.path.exists(SENTINEL_FILE), False)

    @slow  # noqa
    def test_timeouts(self):
        """Worker kills jobs after timeout."""
        sentinel_file = '/tmp/.rq_sentinel'

        q = Queue()
        w = Worker([q])

        # Put it on the queue with a timeout value
        res = q.enqueue(create_file_after_timeout,
                        args=(sentinel_file, 4),
                        timeout=1)

        try:
            os.unlink(sentinel_file)
        except OSError as e:
            if e.errno == 2:
                pass

        self.assertEquals(os.path.exists(sentinel_file), False)
        w.work(burst=True)
        self.assertEquals(os.path.exists(sentinel_file), False)

        # TODO: Having to do the manual refresh() here is really ugly!
        res.refresh()
        self.assertIn('JobTimeoutException', as_text(res.exc_info))

    def test_worker_sets_result_ttl(self):
        """Ensure that Worker properly sets result_ttl for individual jobs."""
        q = Queue()
        job = q.enqueue(say_hello, args=('Frank',), result_ttl=10)
        w = Worker([q])
        w.work(burst=True)
        self.assertNotEqual(self.testconn._ttl(job.key), 0)

        # Job with -1 result_ttl don't expire
        job = q.enqueue(say_hello, args=('Frank',), result_ttl=-1)
        w = Worker([q])
        w.work(burst=True)
        self.assertEqual(self.testconn._ttl(job.key), -1)

        # Job with result_ttl = 0 gets deleted immediately
        job = q.enqueue(say_hello, args=('Frank',), result_ttl=0)
        w = Worker([q])
        w.work(burst=True)
        self.assertEqual(self.testconn.get(job.key), None)

    def test_worker_sets_job_status(self):
        """Ensure that worker correctly sets job status."""
        q = Queue()
        w = Worker([q])

        job = q.enqueue(say_hello)
        self.assertEqual(job.get_status(), Status.QUEUED)
        self.assertEqual(job.is_queued, True)
        self.assertEqual(job.is_finished, False)
        self.assertEqual(job.is_failed, False)

        w.work(burst=True)
        job = Job.fetch(job.id)
        self.assertEqual(job.get_status(), Status.FINISHED)
        self.assertEqual(job.is_queued, False)
        self.assertEqual(job.is_finished, True)
        self.assertEqual(job.is_failed, False)

        # Failed jobs should set status to "failed"
        job = q.enqueue(div_by_zero, args=(1,))
        w.work(burst=True)
        job = Job.fetch(job.id)
        self.assertEqual(job.get_status(), Status.FAILED)
        self.assertEqual(job.is_queued, False)
        self.assertEqual(job.is_finished, False)
        self.assertEqual(job.is_failed, True)

    def test_job_dependency(self):
        """Enqueue dependent jobs only if their parents don't fail"""
        q = Queue()
        w = Worker([q])
        parent_job = q.enqueue(say_hello)
        job = q.enqueue_call(say_hello, depends_on=parent_job)
        w.work(burst=True)
        job = Job.fetch(job.id)
        self.assertEqual(job.get_status(), Status.FINISHED)

        parent_job = q.enqueue(div_by_zero)
        job = q.enqueue_call(say_hello, depends_on=parent_job)
        w.work(burst=True)
        job = Job.fetch(job.id)
        self.assertNotEqual(job.get_status(), Status.FINISHED)

    def test_get_current_job(self):
        """Ensure worker.get_current_job() works properly"""
        q = Queue()
        worker = Worker([q])
        job = q.enqueue_call(say_hello)

        self.assertEqual(self.testconn.hget(worker.key, 'current_job'), None)
        worker.set_current_job_id(job.id)
        self.assertEqual(
            worker.get_current_job_id(),
            as_text(self.testconn.hget(worker.key, 'current_job'))
        )
        self.assertEqual(worker.get_current_job(), job)

########NEW FILE########
