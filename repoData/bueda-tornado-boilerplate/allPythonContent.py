__FILENAME__ = app
#!/usr/bin/env python

import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import options

from settings import settings
from urls import url_patterns

class TornadoBoilerplate(tornado.web.Application):
    def __init__(self):
        tornado.web.Application.__init__(self, url_patterns, **settings)


def main():
    app = TornadoBoilerplate()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = environment
"""Add the boilerplate's directories to Python's site-packages path.
"""
import os
import site
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

prev_sys_path = list(sys.path)

site.addsitedir(path('handlers'))
if os.path.exists(path('vendor')):
    for directory in os.listdir(path('vendor')):
        full_path = path('vendor/%s' % directory)
        if os.path.isdir(full_path):
            site.addsitedir(full_path)

# Move the new items to the front of sys.path. (via virtualenv)
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

########NEW FILE########
__FILENAME__ = fabfile
#!/usr/bin/env python
"""Fabfile using only commands from buedafab (https://github.com/bueda/ops) to
deploy this app to remote servers.
"""

import os
from fabric.api import *

from buedafab.test import (test, tornado_test_runner as _tornado_test_runner,
        lint)
from buedafab.deploy.types import tornado_deploy as deploy
from buedafab.environments import development, staging, production, localhost
from buedafab.tasks import (setup, restart_webserver, rollback, enable,
        disable, maintenancemode, rechef)

# For a description of these attributes, see https://github.com/bueda/ops

env.unit = "boilerplate"
env.path = "/var/webapps/%(unit)s" % env
env.scm = "git@github.com:bueda/%(unit)s.git" % env
env.scm_http_url = "http://github.com/bueda/%(unit)s" % env
env.root_dir = os.path.abspath(os.path.dirname(__file__))
env.test_runner = _tornado_test_runner

env.pip_requirements = ["requirements/common.txt",
        "vendor/allo/pip-requirements.txt",]
env.pip_requirements_dev = ["requirements/dev.txt",]
env.pip_requirements_production = ["requirements/production.txt",]

########NEW FILE########
__FILENAME__ = base
import json
import tornado.web

import logging
logger = logging.getLogger('boilerplate.' + __name__)


class BaseHandler(tornado.web.RequestHandler):
    """A class to collect common handler methods - all other handlers should
    subclass this one.
    """

    def load_json(self):
        """Load JSON from the request body and store them in
        self.request.arguments, like Tornado does by default for POSTed form
        parameters.

        If JSON cannot be decoded, raises an HTTPError with status 400.
        """
        try:
            self.request.arguments = json.loads(self.request.body)
        except ValueError:
            msg = "Could not decode JSON: %s" % self.request.body
            logger.debug(msg)
            raise tornado.web.HTTPError(400, msg)

    def get_json_argument(self, name, default=None):
        """Find and return the argument with key 'name' from JSON request data.
        Similar to Tornado's get_argument() method.
        """
        if default is None:
            default = self._ARG_DEFAULT
        if not self.request.arguments:
            self.load_json()
        if name not in self.request.arguments:
            if default is self._ARG_DEFAULT:
                msg = "Missing argument '%s'" % name
                logger.debug(msg)
                raise tornado.web.HTTPError(400, msg)
            logger.debug("Returning default argument %s, as we couldn't find "
                    "'%s' in %s" % (default, name, self.request.arguments))
            return default
        arg = self.request.arguments[name]
        logger.debug("Found '%s': %s in JSON arguments" % (name, arg))
        return arg

########NEW FILE########
__FILENAME__ = foo
from handlers.base import BaseHandler

import logging
logger = logging.getLogger('boilerplate.' + __name__)


class FooHandler(BaseHandler):
    def get(self):
        self.render("base.html")

########NEW FILE########
__FILENAME__ = dictconfig
# This is a copy of the Python logging.config.dictconfig module. It is provided
# here for backwards compatibility for Python versions prior to 2.7.
#
# Copyright 2009-2010 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted, provided that
# the above copyright notice appear in all copies and that both that copyright
# notice and this permission notice appear in supporting documentation, and that
# the name of Vinay Sajip not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL VINAY
# SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import logging.handlers
import re
import sys
import types

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
        found = self.importer(used)
        for frag in name:
            used += '.' + frag
            try:
                found = getattr(found, frag)
            except AttributeError:
                self.importer(used)
                found = getattr(found, frag)
        return found

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
        elif isinstance(value, basestring): # str for py3k
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
        if not hasattr(c, '__call__') and hasattr(types, 'ClassType') and type(c) != types.ClassType:
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
                            except StandardError, e:
                                raise ValueError('Unable to configure handler '
                                                 '%r: %s' % (name, e))
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    try:
                        self.configure_logger(name, loggers[name], True)
                    except StandardError, e:
                        raise ValueError('Unable to configure logger '
                                         '%r: %s' % (name, e))
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root, True)
                    except StandardError, e:
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
                    except StandardError, e:
                        raise ValueError('Unable to configure '
                                         'formatter %r: %s' % (name, e))
                # Next, do filters - they don't refer to anything else, either
                filters = config.get('filters', EMPTY_DICT)
                for name in filters:
                    try:
                        filters[name] = self.configure_filter(filters[name])
                    except StandardError, e:
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
                    except StandardError, e:
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
                    except StandardError, e:
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
                    except StandardError, e:
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
            except TypeError, te:
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
            except StandardError, e:
                raise ValueError('Unable to add filter %r: %s' % (f, e))

    def configure_handler(self, config):
        """Configure a handler from a dictionary."""
        formatter = config.pop('formatter', None)
        if formatter:
            try:
                formatter = self.config['formatters'][formatter]
            except StandardError, e:
                raise ValueError('Unable to set formatter '
                                 '%r: %s' % (formatter, e))
        level = config.pop('level', None)
        filters = config.pop('filters', None)
        if '()' in config:
            c = config.pop('()')
            if not hasattr(c, '__call__') and hasattr(types, 'ClassType') and type(c) != types.ClassType:
                c = self.resolve(c)
            factory = c
        else:
            klass = self.resolve(config.pop('class'))
            #Special case for handler which refers to another handler
            if issubclass(klass, logging.handlers.MemoryHandler) and\
                'target' in config:
                try:
                    config['target'] = self.config['handlers'][config['target']]
                except StandardError, e:
                    raise ValueError('Unable to set target handler '
                                     '%r: %s' % (config['target'], e))
            elif issubclass(klass, logging.handlers.SMTPHandler) and\
                'mailhost' in config:
                config['mailhost'] = self.as_tuple(config['mailhost'])
            elif issubclass(klass, logging.handlers.SysLogHandler) and\
                'address' in config:
                config['address'] = self.as_tuple(config['address'])
            factory = klass
        kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
        try:
            result = factory(**kwargs)
        except TypeError, te:
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
            except StandardError, e:
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
__FILENAME__ = logconfig
"""An extended version of the log_settings module from zamboni:
https://github.com/jbalogh/zamboni/blob/master/log_settings.py
"""
from tornado.log import LogFormatter as TornadoLogFormatter
import logging, logging.handlers
import os.path
import types

import dictconfig

# Pulled from commonware.log we don't have to import that, which drags with
# it Django dependencies.
class RemoteAddressFormatter(logging.Formatter):
    """Formatter that makes sure REMOTE_ADDR is available."""

    def format(self, record):
        if ('%(REMOTE_ADDR)' in self._fmt
                and 'REMOTE_ADDR' not in record.__dict__):
            record.__dict__['REMOTE_ADDR'] = None
        return logging.Formatter.format(self, record)

class UTF8SafeFormatter(RemoteAddressFormatter):
    def __init__(self, fmt=None, datefmt=None, encoding='utf-8'):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.encoding = encoding
    
    def formatException(self, e):
        r = logging.Formatter.formatException(self, e)
        if type(r) in [types.StringType]:
            r = r.decode(self.encoding, 'replace') # Convert to unicode
        return r
    
    def format(self, record):
        t = RemoteAddressFormatter.format(self, record)
        if type(t) in [types.UnicodeType]:
            t = t.encode(self.encoding, 'replace')
        return t

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

def initialize_logging(syslog_tag, syslog_facility, loggers,
        log_level=logging.INFO, use_syslog=False):
    if os.path.exists('/dev/log'):
        syslog_device = '/dev/log'
    elif os.path.exists('/var/run/syslog'):
        syslog_device = '/var/run/syslog'

    base_fmt = ('%(name)s:%(levelname)s %(message)s:%(pathname)s:%(lineno)s')

    cfg = {
        'version': 1,
        'filters': {},
        'formatters': {
            'debug': {
                '()': UTF8SafeFormatter,
                'datefmt': '%H:%M:%s',
                'format': '%(asctime)s ' + base_fmt,
            },
            'prod': {
                '()': UTF8SafeFormatter,
                'datefmt': '%H:%M:%s',
                'format': '%s: [%%(REMOTE_ADDR)s] %s' % (syslog_tag, base_fmt),
            },
            'tornado': {
                '()': TornadoLogFormatter,
                'color': True
            },
        },
        'handlers': {
            'console': {
                '()': logging.StreamHandler,
                'formatter': 'tornado'
            },
            'null': {
                '()': NullHandler,
            },
            'syslog': {
                '()': logging.handlers.SysLogHandler,
                'facility': syslog_facility,
                'address': syslog_device,
                'formatter': 'prod',
            },
        },
        'loggers': {
        }
    }

    for key, value in loggers.items():
        cfg[key].update(value)

    # Set the level and handlers for all loggers.
    for logger in cfg['loggers'].values():
        if 'handlers' not in logger:
            logger['handlers'] = ['syslog' if use_syslog else 'console']
        if 'level' not in logger:
            logger['level'] = log_level
        if 'propagate' not in logger:
            logger['propagate'] = False

    dictconfig.dictConfig(cfg)

########NEW FILE########
__FILENAME__ = settings
import logging
import tornado
import tornado.template
import os
from tornado.options import define, options

import environment
import logconfig

# Make filepaths relative to settings.
path = lambda root,*a: os.path.join(root, *a)
ROOT = os.path.dirname(os.path.abspath(__file__))

define("port", default=8888, help="run on the given port", type=int)
define("config", default=None, help="tornado config file")
define("debug", default=False, help="debug mode")
tornado.options.parse_command_line()

MEDIA_ROOT = path(ROOT, 'media')
TEMPLATE_ROOT = path(ROOT, 'templates')

# Deployment Configuration

class DeploymentType:
    PRODUCTION = "PRODUCTION"
    DEV = "DEV"
    SOLO = "SOLO"
    STAGING = "STAGING"
    dict = {
        SOLO: 1,
        PRODUCTION: 2,
        DEV: 3,
        STAGING: 4
    }

if 'DEPLOYMENT_TYPE' in os.environ:
    DEPLOYMENT = os.environ['DEPLOYMENT_TYPE'].upper()
else:
    DEPLOYMENT = DeploymentType.SOLO

settings = {}
settings['debug'] = DEPLOYMENT != DeploymentType.PRODUCTION or options.debug
settings['static_path'] = MEDIA_ROOT
settings['cookie_secret'] = "your-cookie-secret"
settings['xsrf_cookies'] = True
settings['template_loader'] = tornado.template.Loader(TEMPLATE_ROOT)

SYSLOG_TAG = "boilerplate"
SYSLOG_FACILITY = logging.handlers.SysLogHandler.LOG_LOCAL2

# See PEP 391 and logconfig for formatting help.  Each section of LOGGERS
# will get merged into the corresponding section of log_settings.py.
# Handlers and log levels are set up automatically based on LOG_LEVEL and DEBUG
# unless you set them here.  Messages will not propagate through a logger
# unless propagate: True is set.
LOGGERS = {
   'loggers': {
        'boilerplate': {},
    },
}

if settings['debug']:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO
USE_SYSLOG = DEPLOYMENT != DeploymentType.SOLO

logconfig.initialize_logging(SYSLOG_TAG, SYSLOG_FACILITY, LOGGERS,
        LOG_LEVEL, USE_SYSLOG)

if options.config:
    tornado.options.parse_config_file(options.config)

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python
import unittest

TEST_MODULES = [
    'list',
    'your',
    'test',
    'modules',
    'test.test_something',
]

def all():
    try:
        return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
    except AttributeError, e:
        if "'module' object has no attribute 'test_" in str(e):
            # most likely because of an import error
            for m in TEST_MODULES:
                __import__(m, globals(), locals())
        raise

if __name__ == '__main__':
    import tornado.testing
    tornado.testing.main()

########NEW FILE########
__FILENAME__ = urls
from handlers.foo import FooHandler

url_patterns = [
    (r"/foo", FooHandler),
]

########NEW FILE########
