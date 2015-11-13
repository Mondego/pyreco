__FILENAME__ = forms

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views

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

site.addsitedir(path('apps'))
site.addsitedir(path('lib'))
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

os.environ['CELERY_LOADER'] = "django"

########NEW FILE########
__FILENAME__ = fabfile
#!/usr/bin/env python
"""Fabfile using only commands from buedafab (https://github.com/bueda/ops) to
deploy this app to remote servers.
"""

import os
from fabric.api import *

from buedafab.test import test, django_test_runner as _django_test_runner, lint
from buedafab.deploy.types import django_deploy as deploy
from buedafab.environments import (django_development as development,
        django_production as production, django_localhost as localhost,
        django_staging as staging)
from buedafab.tasks import (setup, restart_webserver, rollback, enable,
        disable, maintenancemode, rechef)

# For a description of these attributes, see https://github.com/bueda/ops

env.unit = "boilerplate"
env.path = "/var/webapps/%(unit)s" % env
env.scm = "git@github.com:bueda/%(unit)s.git" % env
env.scm_http_url = "http://github.com/bueda/%(unit)s" % env
env.root_dir = os.path.abspath(os.path.dirname(__file__))
env.test_runner = _django_test_runner

env.pip_requirements = ["requirements/common.txt",
        "vendor/allo/pip-requirements.txt",]
env.pip_requirements_dev = ["requirements/dev.txt",]
env.pip_requirements_production = ["requirements/production.txt",]

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
"""
An extended version of the log_settings module from zamboni:
https://github.com/jbalogh/zamboni/blob/master/log_settings.py
"""
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
        },
        'handlers': {
            'console': {
                '()': logging.StreamHandler,
                'formatter': 'debug'
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
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError, e:
    import sys
    sys.stderr.write(
        "Error: Can't find the file 'settings.py' in the directory"
        " containing %r. It appears you've customized things.\nYou'll have to"
        " run django-admin.py, passing it your settings module.\n(If the file"
        " settings.py does indeed exist, it's causing an ImportError somehow.)"
        "\nError was %s" % (__file__, e))
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os
import logging, logging.handlers

import environment
import logconfig

# If using a separate Python package (e.g. a submodule in vendor/) to share
# logic between applications, you can also share settings. Just create another
# settings file in your package and import it like so:
#
#     from comrade.core.settings import * 
#
# The top half of this settings.py file is copied from comrade for clarity. We
# use the import method in actual deployments.

# Make filepaths relative to settings.
path = lambda root,*a: os.path.join(root, *a)
ROOT = os.path.dirname(os.path.abspath(__file__))


# List of admin e-mails - we use Hoptoad to collect error notifications, so this
# is usually blank.
ADMINS = ()
MANAGERS = ADMINS

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

def is_solo():
    return DEPLOYMENT == DeploymentType.SOLO

SITE_ID = DeploymentType.dict[DEPLOYMENT]

DEBUG = DEPLOYMENT != DeploymentType.PRODUCTION
STATIC_MEDIA_SERVER = is_solo()
TEMPLATE_DEBUG = DEBUG
SSL_ENABLED = not DEBUG

INTERNAL_IPS = ('127.0.0.1',)

# Logging

if DEBUG:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO

# Only log to syslog if this is not a solo developer server.
USE_SYSLOG = not is_solo()

# Cache Backend

CACHE_TIMEOUT = 3600
MAX_CACHE_ENTRIES = 10000
CACHE_MIDDLEWARE_SECONDS = 3600
CACHE_MIDDLEWARE_KEY_PREFIX = ''

# Don't require developers to install memcached, and also make debugging easier
# because cache is automatically wiped when the server reloads.
if is_solo():
    CACHE_BACKEND = ('locmem://?timeout=%(CACHE_TIMEOUT)d'
            '&max_entries=%(MAX_CACHE_ENTRIES)d' % locals())
else:
    CACHE_BACKEND = ('memcached://127.0.0.1:11211/?timeout=%(CACHE_TIMEOUT)d'
            '&max_entries=%(MAX_CACHE_ENTRIES)d' % locals())

# E-mail Server

if is_solo():
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_HOST_USER = 'YOU@YOUR-SITE.com'
    EMAIL_HOST_PASSWORD = 'PASSWORD'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = "Bueda Support <support@bueda.com>"

CONTACT_EMAIL = 'support@bueda.com'

# Internationalization

TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
USE_I18N = False

# Testing & Coverage

# Use nosetests instead of unittest
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

COVERAGE_REPORT_HTML_OUTPUT_DIR = 'coverage'
COVERAGE_MODULE_EXCLUDES = ['tests$', 'settings$', 'urls$', 'vendor$',
        '__init__', 'migrations', 'templates', 'django', 'debug_toolbar',
        'core\.fixtures', 'users\.fixtures',]

try:
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
except ImportError:
    cpu_count = 1

NOSE_ARGS = ['--logging-clear-handlers', '--processes=%s' % cpu_count]

if is_solo():
    try:
        os.mkdir(COVERAGE_REPORT_HTML_OUTPUT_DIR)
    except OSError:
        pass

# Paths

MEDIA_ROOT = path(ROOT, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/media/admin'
ROOT_URLCONF = 'urls'

# Version Information

# Grab the current commit SHA from git - handy for confirming the version
# deployed on a remote server is the one you think it is.
import subprocess
GIT_COMMIT = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'],
    stdout=subprocess.PIPE).communicate()[0].strip()
del subprocess

# Database

DATABASES = {}

if DEPLOYMENT == DeploymentType.PRODUCTION:
    DATABASES['default'] = {
        'NAME': 'boilerplate',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'your-database.com',
        'PORT': '',
        'USER': 'boilerplate',
        'PASSWORD': 'your-password'
    }
elif DEPLOYMENT == DeploymentType.DEV:
    DATABASES['default'] = {
        'NAME': 'boilerplate_dev',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'your-database.com',
        'PORT': '',
        'USER': 'boilerplate',
        'PASSWORD': 'your-password'
    }
elif DEPLOYMENT == DeploymentType.STAGING:
    DATABASES['default'] = {
        'NAME': 'boilerplate_staging',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'your-database.com',
        'PORT': '',
        'USER': 'boilerplate',
        'PASSWORD': 'your-password'
    }
else:
    DATABASES['default'] = {
        'NAME': 'db',
        'ENGINE': 'django.db.backends.sqlite3',
        'HOST': '',
        'PORT': '',
        'USER': '',
        'PASSWORD': ''
    }

# Message Broker (for Celery)

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "boilerplate"
BROKER_PASSWORD = "boilerplate"
BROKER_VHOST = "boilerplate"
CELERY_RESULT_BACKEND = "amqp"

# Run tasks eagerly in development, so developers don't have to keep a celeryd
# processing running.
CELERY_ALWAYS_EAGER = is_solo()
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# South

# Speed up testing when you have lots of migrations.
SOUTH_TESTS_MIGRATE = False
SKIP_SOUTH_TESTS = True

# Logging

SYSLOG_FACILITY = logging.handlers.SysLogHandler.LOG_LOCAL0
SYSLOG_TAG = "boilerplate"

# See PEP 391 and logconfig.py for formatting help.  Each section of LOGGING
# will get merged into the corresponding section of log_settings.py.
# Handlers and log levels are set up automatically based on LOG_LEVEL and DEBUG
# unless you set them here.  Messages will not propagate through a logger
# unless propagate: True is set.
LOGGERS = {
    'loggers': {
        'boilerplate': {},
    },
}

logconfig.initialize_logging(SYSLOG_TAG, SYSLOG_FACILITY, LOGGERS, LOG_LEVEL,
        USE_SYSLOG)

# Debug Toolbar

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}

# Application Settings

SECRET_KEY = 'TODO-generate-a-new-secret-key'

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'

# Sessions

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Middleware

middleware_list = [
    'commonware.log.ThreadRequestMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'comrade.core.middleware.HttpMethodsMiddleware',
]

if is_solo():
    middleware_list += [
        'comrade.core.middleware.ArgumentLogMiddleware',
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ]
else:
    middleware_list += [
        'django.middleware.transaction.TransactionMiddleware',
        'commonware.middleware.SetRemoteAddrFromForwardedFor',
    ]

MIDDLEWARE_CLASSES = tuple(middleware_list)

# Templates

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)

if not is_solo():
    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', TEMPLATE_LOADERS),
    )

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.request',
    'django.core.context_processors.csrf',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',

    'comrade.core.context_processors.default',
    'django.core.context_processors.media',
)

TEMPLATE_DIRS = (
    path(ROOT, 'templates')
)

apps_list = [
        'django.contrib.auth',
        'django.contrib.admin',
        'django.contrib.contenttypes',
        'django.contrib.sites',
        'django.contrib.markup',
        'django.contrib.messages',

        #'your',
        #'apps',
        #'here',
        'foo',
]

if is_solo():
    apps_list += [
        'django_extensions',
        'debug_toolbar',
        'django_nose',
        'django_coverage',
    ]

INSTALLED_APPS = tuple(apps_list)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns += patterns('django.views.generic.simple',
    url(r'^$', 'direct_to_template', {'template': 'index.html'}, name='index'),
    url(r'^admin/', include(admin.site.urls)),
)

if settings.STATIC_MEDIA_SERVER:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', 
            {'document_root': 'media'}),
)

########NEW FILE########
